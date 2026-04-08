"""
app.py – CDK entry point for the frut infrastructure.

Usage
-----
  cd infrastructure
  pip install -r requirements.txt
  cdk deploy
"""

import aws_cdk as cdk

from frut_stack import FrutStack

app = cdk.App()

FrutStack(
    app,
    "FrutStack",
    description="frut – Fun Route Optimizer (frontend + backend on AWS)",
    env=cdk.Environment(
        # Resolve account / region from the active AWS CLI profile or
        # the CDK_DEFAULT_* environment variables.
        account=app.node.try_get_context("account") or None,
        region=app.node.try_get_context("region") or "eu-central-1",
    ),
)

app.synth()
