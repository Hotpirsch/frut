"""
frut_stack.py – AWS CDK stack for the frut application.

Architecture
------------
                    ┌──────────────┐
  Browser ─HTTPS──► │  CloudFront  │──► S3 (frontend static files)
                    │              │──► API Gateway ──► Lambda (FastAPI)
                    └──────────────┘

Resources created
-----------------
- S3 bucket          : hosts the compiled frontend (index.html, app.js, …)
- CloudFront distrib : CDN + HTTPS for both the frontend and the /api/* path
- Lambda function    : runs the FastAPI backend (via Mangum adapter)
- API Gateway (HTTP) : forwards /api/* to the Lambda function
"""

from __future__ import annotations

import os
from pathlib import Path

import aws_cdk as cdk
import aws_cdk.aws_apigatewayv2 as apigwv2
import aws_cdk.aws_apigatewayv2_integrations as apigwv2_integrations
import aws_cdk.aws_cloudfront as cf
import aws_cdk.aws_cloudfront_origins as cf_origins
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deploy
from constructs import Construct

BACKEND_DIR  = Path(__file__).parent.parent / "backend"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class FrutStack(cdk.Stack):
    """Main CDK stack for frut."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Lambda (FastAPI backend) ──────────────────────────────────────────
        backend_fn = _lambda.Function(
            self,
            "FrutBackend",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="app.handler",          # Mangum handler exposed in app.py
            code=_lambda.Code.from_asset(
                str(BACKEND_DIR),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                ),
            ),
            memory_size=256,
            timeout=cdk.Duration.seconds(29),
            environment={
                "OSRM_BASE_URL": os.getenv(
                    "OSRM_BASE_URL", "https://router.project-osrm.org"
                ),
            },
            description="frut Fun Route Optimizer – FastAPI backend",
        )

        # ── HTTP API Gateway ──────────────────────────────────────────────────
        http_api = apigwv2.HttpApi(
            self,
            "FrutHttpApi",
            default_integration=apigwv2_integrations.HttpLambdaIntegration(
                "FrutLambdaIntegration",
                backend_fn,
            ),
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigwv2.CorsHttpMethod.GET],
                allow_headers=["*"],
            ),
            description="frut Fun Route Optimizer – API Gateway",
        )

        # ── S3 bucket (frontend) ──────────────────────────────────────────────
        frontend_bucket = s3.Bucket(
            self,
            "FrutFrontend",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ── CloudFront distribution ───────────────────────────────────────────
        api_origin = cf_origins.HttpOrigin(
            f"{http_api.http_api_id}.execute-api.{self.region}.amazonaws.com",
            protocol_policy=cf.OriginProtocolPolicy.HTTPS_ONLY,
        )
        s3_origin = cf_origins.S3StaticWebsiteOrigin(frontend_bucket)

        distribution = cf.Distribution(
            self,
            "FrutDistribution",
            default_behavior=cf.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/api/*": cf.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    allowed_methods=cf.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                ),
                "/health": cf.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY,
                    cache_policy=cf.CachePolicy.CACHING_DISABLED,
                    allowed_methods=cf.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                ),
            },
            default_root_object="index.html",
            comment="frut Fun Route Optimizer",
        )

        # ── Deploy frontend to S3 ─────────────────────────────────────────────
        s3_deploy.BucketDeployment(
            self,
            "FrutFrontendDeployment",
            sources=[s3_deploy.Source.asset(str(FRONTEND_DIR))],
            destination_bucket=frontend_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront URL of the frut web application",
        )
        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=http_api.api_endpoint or "",
            description="Direct URL of the frut API Gateway endpoint",
        )
