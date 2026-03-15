"""RDS PostgreSQL 15, ElastiCache Redis, and S3 metadata bucket."""
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_elasticache as elasticache,
    aws_s3 as s3,
    aws_secretsmanager as sm,
)
from constructs import Construct


class DataStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── Security Groups ───────────────────────────────────────────────────
        db_sg = ec2.SecurityGroup(self, "DbSG", vpc=vpc, description="RDS access")
        redis_sg = ec2.SecurityGroup(self, "RedisSG", vpc=vpc, description="Redis access")

        # ── RDS PostgreSQL 15 ─────────────────────────────────────────────────
        self.db_secret = rds.DatabaseSecret(self, "DbSecret", username="orgforge")

        db = rds.DatabaseInstance(
            self, "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_sg],
            credentials=rds.Credentials.from_secret(self.db_secret),
            database_name="orgforge",
            allocated_storage=20,
            backup_retention=cdk.Duration.days(7),
            deletion_protection=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # ── ElastiCache Redis (single node) ───────────────────────────────────
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnetGroup",
            description="OrgForge Redis subnet group",
            subnet_ids=[s.subnet_id for s in vpc.isolated_subnets],
        )

        redis = elasticache.CfnCacheCluster(
            self, "Redis",
            cache_node_type="cache.t3.micro",
            engine="redis",
            num_cache_nodes=1,
            vpc_security_group_ids=[redis_sg.security_group_id],
            cache_subnet_group_name=redis_subnet_group.ref,
        )

        self.redis_endpoint = f"{redis.attr_redis_endpoint_address}:{redis.attr_redis_endpoint_port}"

        # ── S3 Metadata Bucket ────────────────────────────────────────────────
        self.metadata_bucket = s3.Bucket(
            self, "MetadataBucket",
            bucket_name=f"orgforge-metadata-{self.account}",
            versioned=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        cdk.CfnOutput(self, "DbEndpoint", value=db.db_instance_endpoint_address)
        cdk.CfnOutput(self, "RedisEndpoint", value=self.redis_endpoint)
        cdk.CfnOutput(self, "MetadataBucket", value=self.metadata_bucket.bucket_name)
