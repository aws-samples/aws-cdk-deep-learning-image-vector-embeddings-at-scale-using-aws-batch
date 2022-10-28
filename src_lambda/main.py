import os
from itertools import product

import boto3

aws_batch = boto3.client("batch")


def handler(event, context):
    """
    Execution entrypoint for AWS Lambda.
    Triggers batch jobs with each dataset and hpo combinations.
    ENV variables are set by the AWS CDK infra code.
    """

    batch_job_queue = os.environ.get("BATCH_JOB_QUEUE")
    batch_job_definition = os.environ.get("BATCH_JOB_DEFINITION")
    dynamo_db_name = os.environ.get("DYNAMODB_TABLE_NAME")
    dynamo_db_region = os.environ.get("DYNAMODB_TABLE_REGION")

    datasets = event["datasets"]
    max_epochs = event["max_epochs"]
    per_gpu_batch_size = event["per_gpu_batch_size"]

    for data, epoch, batch_size in product(datasets, max_epochs, per_gpu_batch_size):
        container_overrides = {
            "environment": [
                {"name": "DATASET_NAME", "value": data},
                {"name": "MAX_EPOCHS", "value": str(epoch)},
                {"name": "PER_GPU_BATCH_SIZE", "value": str(batch_size)},
                {"name": "DB_NAME", "value": dynamo_db_name},
                {"name": "DB_REGION", "value": dynamo_db_region},
            ]
        }

        batch_job_name = "automm-cv-bench-batch-job-%s-%s-%s" % (
            data,
            str(epoch),
            str(batch_size),
        )
        response = aws_batch.submit_job(
            jobName=batch_job_name,
            jobQueue=batch_job_queue,
            jobDefinition=batch_job_definition,
            containerOverrides=container_overrides,
        )
        print(response)

    return "Lambda execution finished"
