from datetime import datetime
import os

from source.image_processor import ImageProcessor


def get_mandatory_env(name):
    '''
    Reads the env variable, raises an exception if missing.
    '''
    if name not in os.environ:
        raise Exception("Missing mandatory ENV variable '%s'" % name)
    return os.environ.get(name)

def main():
    '''
    Batch job execution entry point script.
    Environemnt variables set by the AWS CDK infra code.
    '''
    bucket_name = get_mandatory_env("S3_BUCKET_NAME")
    s3_object_key = get_mandatory_env("S3_OBJECT_KEY")
    dynamodb_table_region = get_mandatory_env("DYNAMODB_TABLE_REGION")
    dynamodb_table_name = get_mandatory_env("DYNAMODB_TABLE_NAME")

    start_time = datetime.now()
    image_processor = ImageProcessor(bucket_name, dynamodb_table_name, dynamodb_table_region)
    num_success_resp, num_total_resp = image_processor.process(s3_object_key)

    end_time = datetime.now()
    execution_time = end_time - start_time
    print("Total execution time: %s" % execution_time)

    if num_success_resp == num_total_resp:
        print('All %s images processed successfully!' % num_success_resp)
    else:
        raise RuntimeError('ERROR: Out of `%s` elements, only `%s` were successfully processed' % (num_total_resp, num_success_resp))

if __name__ == '__main__':
   main()
