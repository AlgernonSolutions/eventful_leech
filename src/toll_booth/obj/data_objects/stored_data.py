import re

import boto3

from algernon import ajson


class StoredData:
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


class S3StoredData(StoredData):
    def retrieve(self):
        compiled_pattern = re.compile(r's3://(?P<bucket>[^/]*)/(?P<key>.*)')
        results = compiled_pattern.search(self._storage_uri)
        bucket_name, object_key = results.group('bucket'), results.group('key')
        stored_object_data = boto3.resource('s3').Object(bucket_name, object_key).get()
        object_data = stored_object_data['Body'].read()
        return ajson.loads(object_data)

    @classmethod
    def store(cls, object_data, **kwargs):
        data_type = kwargs['data_type']
        bucket_name = kwargs['bucket_name']
        object_key = kwargs['object_key']
        bucket = boto3.resource('s3').Bucket(bucket_name)
        bucket.put_object(Key=object_key, Body=ajson.dumps(object_data))
        storage_uri = f's3://{bucket_name}/{object_key}'
        return cls(data_type, 's3', storage_uri)
