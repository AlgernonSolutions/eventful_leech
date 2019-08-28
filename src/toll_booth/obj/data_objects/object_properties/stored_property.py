import re

import boto3

from algernon import ajson
from botocore.exceptions import ClientError

from toll_booth.obj.utils import set_property_data_type


def _check_for_object(bucket_name, object_key):
    s3_resource = boto3.resource('s3')
    s3_object = s3_resource.Object(bucket_name, object_key)
    try:
        s3_object.load()
        return True
    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise e
        return False


class StoredPropertyValue:
    """
        not all object_properties can easily fit into the graph. large objects such as web scrapings or extracted PDF
            files are easier to store elsewhere, and reference by pointer within the graph.
    """
    def __init__(self, data_type: str, storage_class: str, storage_uri: str):
        self._data_type = data_type
        self._storage_class = storage_class
        self._storage_uri = storage_uri

    @classmethod
    def store(cls, object_data, **kwargs):
        raise NotImplementedError()

    @property
    def storage_uri(self):
        return self._storage_uri

    def retrieve(self):
        raise NotImplementedError()


class S3StoredPropertyValue(StoredPropertyValue):
    """
        this class facilitates the storage of ObjectPropertyValues into the AWS S3 service
    """
    def retrieve(self):
        compiled_pattern = re.compile(r's3://(?P<bucket>[^/]*)/(?P<key>.*)')
        results = compiled_pattern.search(self._storage_uri)
        bucket_name, object_key = results.group('bucket'), results.group('key')
        stored_object_data = boto3.resource('s3').Object(bucket_name, object_key).get()
        object_data = stored_object_data['Body'].read()
        stored_data = ajson.loads(object_data)
        return set_property_data_type(self._data_type, stored_data)

    @classmethod
    def store(cls, object_data, **kwargs):
        data_type = kwargs['data_type']
        bucket_name = kwargs['bucket_name']
        object_key = kwargs['object_key']
        bucket = boto3.resource('s3').Bucket(bucket_name)
        if not _check_for_object(bucket_name, object_key):
            bucket.put_object(Key=object_key, Body=ajson.dumps(object_data))
        storage_uri = f's3://{bucket_name}/{object_key}'
        return cls(data_type, 's3', storage_uri)
