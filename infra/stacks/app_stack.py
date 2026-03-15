"""
ECS Fargate services for the FastAPI backend and Celery worker.
Sits behind an Application Load Balancer.
"""
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_secretsmanager as sm,
    aws_s3 as s3,
)
from constructs import Construct


class AppStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        db_secret: sm.Secret,
        redis_endpoint: str,
        metadata_bucket: s3.Bucket,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        # ── Task Role ─────────────────────────────────────────────────────────
        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        metadata_bucket.grant_read_write(task_role)
        db_secret.grant_read(task_role)

        # ── Shared environment (non-secret) ──────────────────────────────────
        environment = {
            "REDIS_URL": f"redis://{redis_endpoint}/0",
            "S3_BUCKET": metadata_bucket.bucket_name,
            "AWS_REGION": self.region,
            "DEBUG": "false",
        }

        secrets = {
            "DATABASE_URL": ecs.Secret.from_secrets_manager(db_secret, "connection_string"),
        }

        # ── API Service ───────────────────────────────────────────────────────
        api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ApiService",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    "../backend",
                    file="Dockerfile",
                ),
                container_port=8000,
                environment=environment,
                secrets=secrets,
                task_role=task_role,
            ),
            public_load_balancer=True,
        )

        api_service.target_group.configure_health_check(path="/health")

        # ── Celery Worker ─────────────────────────────────────────────────────
        worker_task = ecs.FargateTaskDefinition(
            self, "WorkerTask",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
        )

        worker_task.add_container(
            "Worker",
            image=ecs.ContainerImage.from_asset("../backend", file="Dockerfile"),
            command=["celery", "-A", "backend.workers.celery_app", "worker", "--loglevel=info"],
            environment=environment,
            secrets=secrets,
            logging=ecs.LogDrivers.aws_logs(stream_prefix="orgforge-worker"),
        )

        ecs.FargateService(
            self, "WorkerService",
            cluster=cluster,
            task_definition=worker_task,
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        cdk.CfnOutput(self, "ApiUrl", value=api_service.load_balancer.load_balancer_dns_name)
