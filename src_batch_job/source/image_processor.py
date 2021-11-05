from io import BytesIO
from datetime import datetime
import os
from pathlib import Path

import boto3
from PIL import Image

from source.model import Image2Vec


class ImageProcessor:
    '''
    Provided an existing S3 bucket and a Dynamo DB table, is used to read a
    txt file in the S3 bucket (formated as paths to objects in the same S3 bucket),
    load the object one-by-one, vectorize the content, and upload the results to
    the Dynamo DB table.
    '''
    def __init__(self, s3_bucket_name, dynamodb_table_name, dynamodb_region):
        self._s3 = boto3.resource('s3')
        self._bucket_name = s3_bucket_name
        self._dynamodb = boto3.resource('dynamodb',
                                        region_name=dynamodb_region)
        self._dynamodb_table = self._dynamodb.Table(dynamodb_table_name)
        self._img2vec_model = Image2Vec()

    def _s3_read_object(self, key):
        s3_object = self._s3.Object(self._bucket_name, key)
        return s3_object.get()['Body'].read()

    def _s3_read_image_file(self, key):
        return Image.open(BytesIO(self._s3_read_object(key)))

    def _s3_read_textual_file(self, key):
        return self._s3_read_object(key).decode('utf-8')

    def _read_paths_from_source(self, s3_source_file_path):
        return self._s3_read_textual_file(s3_source_file_path).splitlines()

    def _dynamodb_itemize(self, key, vector):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        vector_string = vector.tostring()
        vector_dimension = len(vector)
        vector_data_type = str(vector.dtype)
        return {
            'ImageId': key,
            'Created': time,
            'Vector': vector_string,
            'Dimension': vector_dimension,
            'DataType': vector_data_type
        }

    def _dynamodb_put(self, item):
        return self._dynamodb_table.put_item(Item=item)

    def _vectorize(self, image):
        image = image.convert('RGB')
        return self._img2vec_model.to_vector(image)

    def process(self, s3_source_file_path, early_stop=False):
        '''
        Read a s3 txt file with paths to images in the s3 bucket,
        process images and store the results to a Dynamo DB table.

        Method returns tuple consisting of: number of succefully
        processed images, and total number of images to be processed
        '''
        image_paths = self._read_paths_from_source(s3_source_file_path)
        image_keys = map(lambda path: Path(path).stem, image_paths)

        images = map(self._s3_read_image_file, image_paths)
        vectors = map(self._vectorize, images)

        results = zip(image_keys, vectors)
        dynamodb_items = map(
            lambda pair: self._dynamodb_itemize(pair[0], pair[1]), results)
        responses = map(self._dynamodb_put, dynamodb_items)

        status_codes = map(
            lambda response: response['ResponseMetadata']['HTTPStatusCode'], responses)

        for count, status_code in enumerate(status_codes):
            if status_code is not 200 and early_stop is True:
                return count, len(image_paths)

        return len(image_paths), len(image_paths)
