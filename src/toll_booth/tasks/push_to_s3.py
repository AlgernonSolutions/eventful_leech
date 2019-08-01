import boto3
import rapidjson
from botocore.exceptions import ClientError


def push_to_s3_as_json(bucket_name, file_key, obj, overwrite=False):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    stored_object = bucket.Object(file_key)
    try:
        stored_object.load()
        if not overwrite:
            raise RuntimeError(f'can not overwrite file at key: {file_key}')
        stored_object.put(Body=rapidjson.dumps(obj))
    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise e
        stored_object.put(Body=rapidjson.dumps(obj))
