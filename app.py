#!/usr/bin/env python3

import os

from aws_cdk import core
from batch_job_cdk.stack import BatchJobStack


def get_mandatory_env(name):
    """
    Reads the env variable, raises an exception if missing.
    """
    if name not in os.environ:
        raise Exception("Missing os enviroment variable '%s'" % name)
    return os.environ.get(name)


cdk_default_account = get_mandatory_env("CDK_DEPLOY_ACCOUNT")
cdk_default_region = get_mandatory_env("CDK_DEPLOY_REGION")

app = core.App()
env = core.Environment(account=cdk_default_account, region=cdk_default_region)

BatchJobStack(app, "automm-cv-bench-batch-job-stack", env=env)
app.synth()
