#!/usr/bin/env python3

import os

from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_lambda as aws_lambda,
    aws_batch as batch,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ecr_assets,
    core
)

from batch_job_cdk.constructs.instance_profile import InstanceProfile
from batch_job_cdk.constructs.batch_lambda_function import BatchLambdaFunction

'''
Sample CDK code for creating the required infrastructure for running a AWS Batch job.
AWS Batch as the compute enviroment in which a docker image runs the benchmarking script.
'''

job_definition_name = "automm-cv-bench-job-definition"
job_queue_name = "automm-cv-bench-job-queue"
stack_name = "automm-cv-bench-stack"
lambda_function_name = "automm-cv-bench-lambda"
compute_env_name = "automm-cv-bench-compute-environment"
batch_lambda_function_name = "automm-cv-bench-batch-job-function"
db_table_name = "automm-cv-bench-dynamodb-table"

# Relative path to the source code for the aws batch job, from the project root
docker_base_dir = "src_batch_job"

# Relative path to the source for the AWS lambda, from the project root
lambda_script_dir = "src_lambda"

class BatchJobStack(core.Stack):
    """Defines automm-cv-bench stack with:
        - New Compute Environment with
            - Batch Instance Role (read access to S3, read-write access to DynamoDB)
            - Launch Template
            - Security Group
            - VPC
            - Job Definition (with customized container)
            - Job Queue
        - New DynamoDB table
        - Existing S3 bucket (automl-mm-bench)
        - New Lambda function to run training
    """
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        s3_bucket = s3.Bucket.from_bucket_attributes(
            self, 
            "ImportedBucket",
            bucket_arn="arn:aws:s3:::automl-mm-bench"
        )

        db_table = dynamodb.Table(self,
            'automm-cv-bench-dynamodb-table',
            table_name=db_table_name,
            partition_key=dynamodb.Attribute(
                name='dataset',
                type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=core.RemovalPolicy.RETAIN
        )
        vpc = ec2.Vpc(self,
            "automm-cv-bench-batch-job-vpc",
            max_azs=2
        )

        sg = ec2.SecurityGroup(self,
            "automm-cv-bench-batch-job-security-group",
            vpc=vpc,
            security_group_name="automm-cv-bench-batch-job-security-group",
        )

        # Currently CDK can only push to the default repo aws-cdk/assets
        # https://github.com/aws/aws-cdk/issues/12597
        docker_image_asset = aws_ecr_assets.DockerImageAsset(self,
            "automm-cv-bench-ecr-docker-image-asset",
            directory=docker_base_dir,
            follow_symlinks=core.SymlinkFollowMode.ALWAYS,
            build_args={
                "GITLAB_TOKENID": os.environ["GITLAB_TOKENID"],
                "GITLAB_TOKEN": os.environ["GITLAB_TOKEN"],
            }
        )

        docker_container_image = ecs.ContainerImage.from_docker_image_asset(docker_image_asset)
        
        container = batch.JobDefinitionContainer(
            image=docker_container_image,
            gpu_count=1,
            vcpus=8,
            memory_limit_mib=25000,
            # Bug that this parameter is not rending in the CF stack under cdk.out
            # https://github.com/aws/aws-cdk/issues/13023
            linux_params=ecs.LinuxParameters(self, 
                                             "automm-cv-bench-linux_params",
                                             shared_memory_size=20000),
        )

        batch_job_definition = batch.JobDefinition(self,
            "job-definition",
            job_definition_name=job_definition_name,
            container=container,
            retry_attempts=3,
            timeout=core.Duration.minutes(1500)
        )
        
        launch_template = ec2.LaunchTemplate(self, "automm-cv-launch-template",
            launch_template_name="automm-cv-launch-template",
            block_devices=[ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(200)
            )]
        )

        batch_instance_role = iam.Role(self,
            'automm-cv-bench-batch-job-instance-role',
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

        batch_instance_profile = InstanceProfile(self, 'automm-cv-bench-batch-job-instance-profile')
        batch_instance_profile.attach_role(batch_instance_role)

        compute_environment = batch.ComputeEnvironment(self,
            "automm-cv-bench-batch-compute-environment",
            compute_environment_name=compute_env_name,
            compute_resources=batch.ComputeResources(
                vpc=vpc,
                minv_cpus=8,
                desiredv_cpus=8,
                maxv_cpus=20000,
                instance_role=batch_instance_profile.profile_arn,
                instance_types=[ec2.InstanceType("p3")],
                security_groups=[sg],
                type=batch.ComputeResourceType.ON_DEMAND,
                # ec2_key_pair="automm-cv-bench-perm-key", # set this if you need ssh access to instance
                launch_template=batch.LaunchTemplateSpecification(
                        launch_template_name="automm-cv-launch-template"
                ),
            ))

        job_queue = batch.JobQueue(self,
            "automm-cv-bench-job-queue",
            job_queue_name=job_queue_name,
            priority=1,
            compute_environments=[
                batch.JobQueueComputeEnvironment(
                    compute_environment=compute_environment,
                    order=1)
            ])

        batch_lambda_function = BatchLambdaFunction(self,
            'automm-cv-bench-batch-lambda-function',
            function_name=batch_lambda_function_name,
            code_path=lambda_script_dir,
            environment={
                "BATCH_JOB_QUEUE": job_queue_name,
                "BATCH_JOB_DEFINITION": job_definition_name,
                "DYNAMODB_TABLE_NAME": db_table_name,
                "DYNAMODB_TABLE_REGION": os.environ["CDK_DEFAULT_REGION"],
            })

