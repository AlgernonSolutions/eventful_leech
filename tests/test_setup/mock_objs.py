from unittest.mock import patch

import boto3


def dev_dynamo():
    patch_obj = patch('toll_booth.obj.data_objects.sensitive_data.boto3.resource')
    mock_resource = patch_obj.start()
    mock_resource.return_value = boto3.Session(profile_name='dev').resource('dynamodb')
    yield mock_resource
    patch_obj.stop()


def dev_s3_stored_data():
    patch_obj = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_resource = patch_obj.start()
    mock_resource.return_value = boto3.Session(profile_name='dev').resource('s3')
    yield mock_resource
    patch_obj.stop()


def mock_s3_stored_data():
    patch_obj = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_obj = patch_obj.start()
    yield mock_obj
    patch_obj.stop()


def tasks_bullhorn():
    patch_obj = patch('toll_booth.tasks.leech.Bullhorn')
    mock_obj = patch_obj.start()
    yield mock_obj
    patch_obj.stop()


def gql_client_notary():
    patch_obj = patch('toll_booth.obj.gql.gql_client.GqlNotary')
    mock_obj = patch_obj.start()
    yield mock_obj
    patch_obj.stop()
