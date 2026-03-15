"""
CloudFront + S3 static hosting for the Next.js exported frontend.
For full SSR, swap the S3 origin for an ECS/Lambda origin.
"""
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3_deploy,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class FrontendStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── S3 bucket for static assets ───────────────────────────────────────
        bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ── Origin Access Control ─────────────────────────────────────────────
        oac = cf.S3OriginAccessControl(self, "OAC")

        # ── CloudFront Distribution ───────────────────────────────────────────
        distribution = cf.Distribution(
            self, "Distribution",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    bucket, origin_access_control=oac
                ),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            error_responses=[
                cf.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                )
            ],
        )

        # ── Deploy built Next.js output ───────────────────────────────────────
        s3_deploy.BucketDeployment(
            self, "Deploy",
            sources=[s3_deploy.Source.asset("../frontend/out")],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        cdk.CfnOutput(self, "CloudFrontUrl", value=f"https://{distribution.distribution_domain_name}")
