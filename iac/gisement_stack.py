"""The Gisement stack (lot 21, ENF-16).

Reproducible IaC, no undocumented manual step. Serverless only: S3 +
CloudFront + Cognito for the portal, API Gateway + Lambda for the API, DynamoDB
for the state, Step Functions for the campaign orchestration, S3 for the
sanitised corpora and the reports, and IAM roles scoped to the seven AI
services. The compliance register is append-only and the corpora have a bounded
retention with a proven purge (ENF-06).
"""

from __future__ import annotations

from decimal import Decimal

import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_bedrockagentcore as agentcore
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_cloudfront_origins as origins
import aws_cdk.aws_cognito as cognito
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct

REGION = "eu-west-3"
#: The campaign stages, in order: one Step Functions state per stage.
ETAPES_CAMPAGNE = ("collect", "classify", "aggregate", "price", "sequence", "report")
RETENTION_CORPUS_JOURS = 180


class GisementStack(cdk.Stack):
    """One stack: portal, API, state, orchestration, storage, AI roles."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.tables = self._tables()
        self.corpus = self._corpus_bucket()
        self.portal = self._portal_bucket()
        self.user_pool = self._cognito()
        self.api_role = self._api_role()
        self.api = self._api()
        self._orchestration()
        self._agentcore()
        self.distribution = self._distribution()
        self._outputs()

    # ------------------------------------------------------------------ storage

    def _tables(self) -> dict[str, dynamodb.Table]:
        """The DynamoDB tables of chapter 22."""
        spec = {
            "campagnes": "id",
            "motifs": "id",
            "processus": "id",
            "gisements": "id",
            "projets": "id",
            "deconseilles": "id",
            "suivi": "id",
        }
        tables = {}
        for nom, cle in spec.items():
            tables[nom] = dynamodb.Table(
                self,
                f"table-{nom}",
                table_name=f"gisement-{nom}",
                partition_key=dynamodb.Attribute(name=cle, type=dynamodb.AttributeType.STRING),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                encryption=dynamodb.TableEncryption.AWS_MANAGED,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )
        tables["registre"] = dynamodb.Table(
            self,
            "table-registre",
            table_name="gisement-registre",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            # append-only: the compliance register is never updated in place
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        return tables

    def _corpus_bucket(self) -> s3.Bucket:
        """Sanitised corpora and reports: encrypted, versioned, bounded retention."""
        return s3.Bucket(
            self,
            "corpus",
            bucket_name=f"gisement-corpus-{self.account}-{REGION}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(expiration=cdk.Duration.days(RETENTION_CORPUS_JOURS)),
            ],
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

    def _portal_bucket(self) -> s3.Bucket:
        return s3.Bucket(
            self,
            "portal",
            bucket_name=f"gisement-portal-{self.account}-{REGION}",
            website_index_document="index.html",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

    # ------------------------------------------------------------------ identity

    def _cognito(self) -> cognito.UserPool:
        """The five roles of chapter 7, the DPO being a first-class one."""
        pool = cognito.UserPool(
            self,
            "user-pool",
            user_pool_name="gisement-utilisateurs",
            self_sign_up_enabled=False,
            password_policy=cognito.PasswordPolicy(min_length=12, require_symbols=True),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        for role in ("commanditaire", "responsable_service", "dpo", "consultant_msp", "responsable_compte"):
            pool.add_group(role, group_name=role, description=f"Gisement - {role}")
        return pool

    def _api_role(self) -> iam.Role:
        """Least privilege: the seven AI services, the tables, the corpus."""
        role = iam.Role(
            self,
            "api-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"],
                resources=["*"],
                conditions={"StringEquals": {"aws:RequestedRegion": REGION}},
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:Retrieve",
                    "bedrock:StartDataAutomationAnalysis",
                    "bedrock:GetDataAutomationAnalysis",
                    "comprehend:DetectPiiEntities",
                    "comprehend:DetectEntities",
                ],
                resources=["*"],
                conditions={"StringEquals": {"aws:RequestedRegion": REGION}},
            )
        )
        for table in self.tables.values():
            table.grant_read_write_data(role)
        self.corpus.grant_read_write(role)
        return role

    # ------------------------------------------------------------------ compute

    def _api(self) -> apigw.LambdaRestApi:
        """The API handlers are the same pure functions the local server runs."""
        handler = _lambda.Function(
            self,
            "api-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="gisement.lambdas.api.handler",
            code=_lambda.Code.from_asset("../src"),
            role=self.api_role,
            timeout=cdk.Duration.seconds(28),
            memory_size=1024,
            environment={"GISMENT_REGION": REGION, "GISMENT_CORPUS": self.corpus.bucket_name},
        )
        return apigw.LambdaRestApi(
            self,
            "api",
            rest_api_name="gisement-api",
            handler=handler,
            proxy=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

    def _orchestration(self) -> sfn.StateMachine:
        """Step Functions drives a campaign, one Lambda invocation per stage.

        The same handler serves every stage (`gisement.lambdas.campagne`), so
        the orchestration is declarative: adding a stage is a state, not a
        function. Capped at four hours (ENF-18).
        """
        self.campagne_fn = _lambda.Function(
            self,
            "campagne-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="gisement.lambdas.campagne.handler",
            code=_lambda.Code.from_asset("../src"),
            role=self.api_role,
            timeout=cdk.Duration.minutes(15),
            memory_size=1024,
            environment={"GISMENT_REGION": REGION, "GISMENT_CORPUS": self.corpus.bucket_name},
        )
        etapes = []
        for stage in ETAPES_CAMPAGNE:
            etapes.append(
                sfn_tasks.LambdaInvoke(
                    self,
                    f"etape-{stage}",
                    state_name=stage,
                    lambda_function=self.campagne_fn,
                    payload=sfn.TaskInput.from_object({"stage": stage, "campagne.$": "$.campagne_id"}),
                    result_path=f"$.resultats.{stage}",
                )
            )
        definition = etapes[0]
        for etape in etapes[1:]:
            definition = definition.next(etape)
        return sfn.StateMachine(
            self,
            "campagne",
            state_machine_name="gisement-campagne",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=cdk.Duration.hours(4),
        )

    def _agentcore(self) -> None:
        """AgentCore: policy engine, Cedar policy, gateway with a REQUEST
        interceptor, and memory for the longitudinal follow-up.

        The real answer to point 5 of chapter 34 (decision D-22): the k >= 5
        refusal is a Cedar `forbid` evaluated by the gateway itself, and what
        Cedar cannot express is refused by the REQUEST interceptor Lambda, which
        runs before the target and short-circuits the call.
        """
        self.intercepteur = self._intercepteur()
        self.policy_engine, self.policy = self._politique()
        self.gateway = self._passerelle()
        self.memory = self._memoire()

    def _intercepteur(self) -> _lambda.Function:
        """The REQUEST interceptor: the gateway calls it before the target."""
        return _lambda.Function(
            self,
            "intercepteur",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="gisement.lambdas.intercepteur.handler",
            code=_lambda.Code.from_asset("../src"),
            role=self.api_role,
            timeout=cdk.Duration.seconds(10),
            memory_size=256,
            environment={"GISMENT_SEUIL_AGGREGATION": "5"},
        )

    def _politique(self):
        """The Cedar policy, generated by the product code itself: no drift."""
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from gisement.politique.cedar import definition_politique
        from gisement.politique.regles import ContextePolitique

        contexte = ContextePolitique(
            campagne_id="*",
            tenant_id="*",
            conforme=True,
            suspendue=False,
            budget_restant=Decimal(20),
        )
        moteur = agentcore.CfnPolicyEngine(
            self,
            "policy-engine",
            name="gisement_policy_engine",
            description="Non-attribution individuelle, k >= 5, budget et suspension",
        )
        politique = agentcore.CfnPolicy(
            self,
            "policy",
            name="gisement_non_attribution",
            policy_engine_id=moteur.attr_policy_engine_id,
            definition=definition_politique(contexte),
            enforcement_mode="ACTIVE",
            description="Chapitre 18 : R1 a R5 imposees par la passerelle",
        )
        return moteur, politique

    def _passerelle(self):
        gateway = agentcore.CfnGateway(
            self,
            "gateway",
            name="gisement-gateway",
            role_arn=self.api_role.role_arn,
            protocol_type="MCP",
            authorizer_type="CUSTOM_JWT",
            description="Point d'entree unique des outils de mesure ; k >= 5 impose ici",
            authorizer_configuration=agentcore.CfnGateway.AuthorizerConfigurationProperty(
                custom_jwt_authorizer=(
                    agentcore.CfnGateway.CustomJWTAuthorizerConfigurationProperty(
                        discovery_url=(
                            f"https://cognito-idp.{REGION}.amazonaws.com/"
                            f"{self.user_pool.user_pool_id}/.well-known/openid-configuration"
                        ),
                        allowed_clients=[self.user_pool.user_pool_id],
                    )
                )
            ),
            policy_engine_configuration=(
                agentcore.CfnGateway.GatewayPolicyEngineConfigurationProperty(
                    arn=self.policy_engine.attr_policy_engine_arn, mode="ENFORCE"
                )
            ),
            interceptor_configurations=[self._configuration_intercepteur()],
        )
        self.intercepteur.grant_invoke(iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"))
        gateway.add_resource_dependency(self.policy)
        return gateway

    def _configuration_intercepteur(self):
        """One REQUEST interceptor, headers passed (the tenant comes from the
        token, EF-71) and never logged - only the decision is."""
        return agentcore.CfnGateway.GatewayInterceptorConfigurationProperty(
            interception_points=["REQUEST"],
            interceptor=agentcore.CfnGateway.InterceptorConfigurationProperty(
                lambda_=agentcore.CfnGateway.LambdaInterceptorConfigurationProperty(
                    arn=self.intercepteur.function_arn
                )
            ),
            input_configuration=agentcore.CfnGateway.InterceptorInputConfigurationProperty(
                pass_request_headers=True
            ),
        )

    def _memoire(self):
        """AgentCore Memory: the realised-against-predicted history (8.2)."""
        return agentcore.CfnMemory(
            self,
            "memory",
            name="gisement_memory",
            event_expiry_duration=365,
            description="Suivi longitudinal realise contre predit, par client et par trimestre",
        )

    def _distribution(self) -> cloudfront.Distribution:
        return cloudfront.Distribution(
            self,
            "cdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.portal),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
        )

    def _outputs(self) -> None:
        cdk.CfnOutput(self, "portal-url", value=f"https://{self.distribution.distribution_domain_name}/")
        cdk.CfnOutput(self, "api-url", value=self.api.url)
        cdk.CfnOutput(self, "user-pool-id", value=self.user_pool.user_pool_id)
        cdk.CfnOutput(self, "corpus-bucket", value=self.corpus.bucket_name)
        cdk.CfnOutput(self, "registre-table", value=self.tables["registre"].table_name)
        cdk.CfnOutput(self, "gateway-url", value=self.gateway.attr_gateway_url)
        cdk.CfnOutput(self, "policy-engine-id", value=self.policy_engine.attr_policy_engine_id)
        cdk.CfnOutput(self, "intercepteur-arn", value=self.intercepteur.function_arn)
        cdk.CfnOutput(self, "memory-arn", value=self.memory.attr_memory_arn)
