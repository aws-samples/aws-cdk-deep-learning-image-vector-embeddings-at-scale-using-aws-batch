import os
import json
from itertools import zip_longest

import boto3
from botocore.exceptions import ClientError

s3 = boto3.resource('s3')
aws_batch = boto3.client('batch')

# Output path for the txt split files
tmp_txt_batch_split_dir = "tmp"

# Number of images to process per job
image_batch_limit = 1000


def handler(event, context):
    """
    Execution entrypoint for AWS Lambda.

    Reads a S3 bucket and filters all matching files; Retrieves paths to those
    matched files, splits them, and writes them in txt files as batch job
    splits; Triggers batch jobs with each job having that txt as an input.

    ENV variables are set by the AWS CDK infra code.
    """

    batch_job_region = aws_batch.meta.region_name
    batch_job_queue = os.environ.get("BATCH_JOB_QUEUE")
    batch_job_definition = os.environ.get("BATCH_JOB_DEFINITION")
    dynamodb_table_name = os.environ.get("DYNAMODB_TABLE_NAME")
    bucket_name = os.environ.get("S3_BUCKET_NAME")

    txt_object_keys = []
    for path_prefix in event['Paths']:
        for (index, batch) in split(bucket_name, path_prefix, 'jpg', image_batch_limit):
            txt_object_key = os.path.join(
                tmp_txt_batch_split_dir,
                "batch-job-split-%s.txt" % str(index)
            )

            txt_object_content = "\n".join(batch)
            s3.Object(bucket_name, txt_object_key).put(Body=txt_object_content)
            txt_object_keys.append(txt_object_key)

    for index, txt_object_key in enumerate(txt_object_keys, 1):
        container_overrides = {
            "environment": [{
                "name": "S3_BUCKET_NAME",
                "value": bucket_name
            }, {
                "name": "S3_OBJECT_KEY",
                "value": txt_object_key
            }, {
                "name": "DYNAMODB_TABLE_REGION",
                "value": batch_job_region
            }, {
                "name": "DYNAMODB_TABLE_NAME",
                "value": dynamodb_table_name
            }]
        }

        batch_job_name = "aws-blog-batch-job-%s-%s" % (str(index), str(len(txt_object_keys)))
        response = aws_batch.submit_job(jobName=batch_job_name,
                                        jobQueue=batch_job_queue,
                                        jobDefinition=batch_job_definition,
                                        containerOverrides=container_overrides)
        print(response)
    return 'Lambda execution finished'


def split(bucket_name, prefix, suffix, batch_limit):
    """
    Splits all found files (which match the prefix and suffix)
    in a bucket into splits with a given batch limit.
    """
    bucket = s3.Bucket(name=bucket_name)

    objects = bucket.objects.filter(Prefix=prefix)
    keys = [obj.key for obj in objects]
    suffix_keys = list(filter(lambda key: key.endswith(suffix), keys))

    for (index,batch_keys) in enumerate(batch(suffix_keys, batch_limit, None)):
        batch_keys = filter(None.__ne__, batch_keys)
        yield (index,batch_keys)

def batch(iterable, batch_limit, fillvalue):
    """
    Batch a iterable into splits of size batch_limit
    """
    if batch_limit < 1:
        raise ValueError('Number of elements to bulk together cannot be smaller than 1')
    elements = batch_limit * [iter(iterable)]
    return zip_longest(fillvalue=fillvalue, *elements)
