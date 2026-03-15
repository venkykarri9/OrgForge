#!/usr/bin/env python3
"""OrgForge CDK App — entry point."""
import aws_cdk as cdk
from stacks.network_stack import NetworkStack
from stacks.data_stack import DataStack
from stacks.app_stack import AppStack
from stacks.frontend_stack import FrontendStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

network = NetworkStack(app, "OrgForgeNetwork", env=env)
data = DataStack(app, "OrgForgeData", vpc=network.vpc, env=env)
app_stack = AppStack(
    app, "OrgForgeApp",
    vpc=network.vpc,
    db_secret=data.db_secret,
    redis_endpoint=data.redis_endpoint,
    metadata_bucket=data.metadata_bucket,
    env=env,
)
FrontendStack(app, "OrgForgeFrontend", env=env)

app.synth()
