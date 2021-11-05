#!/usr/bin/env python3

import os

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_lambda as aws_lambda,
    aws_dynamodb as dynamodb,
    aws_batch as batch,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ecr_assets,
    core
)

from batch_job_cdk.constructs.instance_profile import InstanceProfile
from batch_job_cdk.constructs.batch_lambda_function import BatchLambdaFunction

'''
Sample CDK code for creating the required infrastructure for running a AWS Batch job.

Creates a S3 bucket as a source for reading data, and a dynamodb table as a target.
AWS Batch as the compute enviroment in which a docker image with the DL model runs.
'''

job_definition_name = "aws-blog-batch-job-image-transform-job-definition"
job_queue_name = "aws-blog-batch-job-image-transform-job-queue"
db_table_name = "aws-blog-batch-job-image-transform-dynamodb-table"
stack_name = "aws-blog-batch-job-image-transform-stack"
lambda_function_name = "aws-blog-batch-job-image-transform-lambda"
compute_env_name = "aws-blog-batch-compute-environment"
batch_lambda_function_name = "aws-blog-batch-job-function"

# Relative path to the source code for the aws batch job, from the project root
docker_base_dir = "src_batch_job"

# Relative path to the source for the AWS lambda, from the project root
lambda_script_dir = "src_lambda"

class BatchJobStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        s3_bucket = s3.Bucket(self,
            'batch-job-bucket',
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        db_table = dynamodb.Table(self,
            'batch-job-dynamodb-table',
            table_name=db_table_name,
            partition_key=dynamodb.Attribute(
                name=f'ImageId',
                type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True
        )

        vpc = ec2.Vpc(self,
            "batch-job-vpc",
            max_azs=2
        )

        sg = ec2.SecurityGroup(self,
            "batch-job-security-group",
            vpc=vpc,
            security_group_name="aws-blog-batch-job-security-group",
        )

        docker_image_asset = aws_ecr_assets.DockerImageAsset(self,
            "ecr-docker-image-asset",
            directory=docker_base_dir
        )

        docker_container_image = ecs.ContainerImage.from_docker_image_asset(docker_image_asset)

        batch_job_definition = batch.JobDefinition(self,
            "job-definition",
            job_definition_name=job_definition_name,
            container=batch.JobDefinitionContainer(
                image=docker_container_image,
                gpu_count=0,
                vcpus=8,
                memory_limit_mib=8192),
            retry_attempts=5,
            timeout=core.Duration.minutes(30)
        )

        batch_instance_role = iam.Role(self,
            'batch-job-instance-role',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('ec2.amazonaws.com'),
                iam.ServicePrincipal('ecs.amazonaws.com'),
                iam.ServicePrincipal('ecs-tasks.amazonaws.com')
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
            ])

        db_table.grant_read_write_data(batch_instance_role)
        s3_bucket.grant_read(batch_instance_role)

        batch_instance_profile = InstanceProfile(self, 'batch-job-instance-profile')
        batch_instance_profile.attach_role(batch_instance_role)

        compute_environment = batch.ComputeEnvironment(self,
            "batch-compute-environment",
            compute_environment_name=compute_env_name,
            compute_resources=batch.ComputeResources(
                vpc=vpc,
                minv_cpus=0,
                desiredv_cpus=0,
                maxv_cpus=32,
                instance_role=batch_instance_profile.profile_arn,
                security_groups=[sg],
                type=batch.ComputeResourceType.ON_DEMAND,
            ))

        job_queue = batch.JobQueue(self,
            "job-queue",
            job_queue_name=job_queue_name,
            priority=1,
            compute_environments=[
                batch.JobQueueComputeEnvironment(
                    compute_environment=compute_environment,
                    order=1)
            ])

        batch_lambda_function = BatchLambdaFunction(self,
            'batch-lambda-function',
            function_name=batch_lambda_function_name,
            code_path=lambda_script_dir,
            environment={
                "BATCH_JOB_QUEUE": job_queue_name,
                "BATCH_JOB_DEFINITION": job_definition_name,
                "REGION": os.environ["CDK_DEFAULT_REGION"],
                "S3_BUCKET_NAME": s3_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": db_table_name
            })

        s3_bucket.grant_read_write(batch_lambda_function.function)
