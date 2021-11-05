#!/usr/bin/env python3

from aws_cdk import (
    aws_lambda as _lambda,
    aws_iam as iam,
    core
)

class BatchLambdaFunction(core.Construct):
    '''
    Custom CDK construct class for a Lambda function with invocation
    rights for AWS Batch.
    '''

    @property
    def function(self):
        return self._lambda_function

    def __init__(self, scope: core.Construct, id: str, function_name: str, code_path: str, environment, timeout=600):
        super().__init__(scope, id)

        self._lambda_function_role = iam.Role(self,
            'lambda-function-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSBatchFullAccess")
            ])

        self._lambda_function = _lambda.Function(self,
            "lambda-function",
            function_name=function_name,
            code=_lambda.Code.from_asset(code_path),
            handler="main.handler",
            timeout=core.Duration.seconds(timeout),
            runtime=_lambda.Runtime.PYTHON_3_6,
            role = self._lambda_function_role,
            environment=environment
        )

