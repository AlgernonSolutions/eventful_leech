import json
from unittest.mock import patch

import boto3


def dev_dynamo():
    patch_obj = patch('toll_booth.obj.data_objects.sensitive_data.boto3.resource')
    mock_resource = patch_obj.start()
    mock_resource.return_value = boto3.Session(profile_name='dev').resource('dynamodb')
    return mock_resource, patch_obj


def dev_s3_stored_data():
    patch_obj = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_resource = patch_obj.start()
    mock_resource.return_value = boto3.Session(profile_name='dev').resource('s3')
    return mock_resource, patch_obj


def mock_s3_stored_data():
    patch_obj = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_obj = patch_obj.start()
    return mock_obj, patch_obj


def tasks_bullhorn():
    patch_obj = patch('toll_booth.tasks.leech.Bullhorn')
    mock_obj = patch_obj.start()
    return mock_obj, patch_obj


def gql_client_notary():
    patch_obj = patch('toll_booth.obj.gql.gql_client.GqlNotary.send')
    mock_obj = patch_obj.start()
    mock_obj.return_value = json.dumps({'data': {'some_result': 'some_value'}})
    return mock_obj, patch_obj
