# Batch processing with AWS Batch and CDK

## Welcome

This repository demostrates provisioning the necessary infrastructure for running a job on AWS Batch using Cloud Development Kit (CDK).
The AWS Batch job reads images from an S3 bucket, runs inference over image-to-vector computer vision model, and stores the results in DynamoDB.
Code can be easily modified to fit other batch job transformations you might want to perform. 

This code repository is part of the [Deep learning image vector embeddings at scale using AWS Batch and CDK](https://aws.amazon.com/blogs/devops/deep-learning-image-vector-embeddings-at-scale-using-aws-batch-and-cdk/) AWS DevOps Blog post.

## Pre-requisites

1. Create and source a Python virtualenv on MacOS and Linux, and install python dependencies:

```
$ python3 -m venv .env
$ source .env/bin/activate
$ pip install -r requirements.txt
```

2. Install the latest version of the AWS CDK CLI:

```shell
$ npm i -g aws-cdk
```

## Usage

Current code creates a the AWS Batch infrastructure, S3 Bucket for reading the data from, a DynamoDB table to write te batch
operation results. Once the infrastructure is provisioned trough AWS CDK, you need to upload the images you want to process
to the created S3 bucket. Once you've done that, go to the created AWS Lambda and submit a job. This will trigger a
job execution on AWS Batch and you should see the results in the created DynamoDB table.

To deploy and run the batch inference, follow the following steps:

1. Make sure you have AWS CDK installed and working, all the dependencies of this project defiend in the requirements.txt file, as well as having an installed and configured Docker in your environment;
2. Set the `CDK_DEPLOY_ACCOUNT` ENV variable to the name of the AWS account you want to use (pre-defined with AWS CLI);
3. Set the `CDK_DEPLOY_REGION` ENV variable to the name of the region you want to deploy the infra in (e.g. 'us-west-2');
4. Run `cdk deploy` in the root of this project and wait for the deployment to finish successfully;
5. Upload the images you need to proccess to the newly created S3 bucket under a S3 bucket path (e.g. `/images`). Use this path in the next step;
6. Go to the created AWS Lambda and execute the lambda function with the following JSON:
```
{
"Paths": [
    "images"
   ]
}
```
7. In the AWS console, go to AWS batch and make sure the jobs are submitted and are running successfully;
8. Open the created DynamoDB table and validate the results are there;
9. You can now use a DynamoDB client to read and consume the results;

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
