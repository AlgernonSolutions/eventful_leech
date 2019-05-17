import os
from os import path
from unittest.mock import patch

import pytest
import rapidjson
from algernon import ajson

from toll_booth.obj.schemata.schema import Schema


@pytest.fixture(params=[
    ('mock_encounter', 'surgeon_schema', 'Encounter'),
    ('mock_patient', 'surgeon_schema', 'Patient'),
    ('mock_provider', 'surgeon_schema', 'Provider')
])
def object_regulator_event(request):
    params = request.param
    schema = _read_schema(params[1], params[2])
    event = _read_test_event(params[0])
    return event, schema


@pytest.fixture(params=[
    ('mock_encounter', 'surgeon_schema', 'Encounter'),
    ('mock_patient', 'surgeon_schema', 'Patient'),
    ('mock_provider', 'surgeon_schema', 'Provider')
])
def source_vertex_task_integration_event(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    schema = _read_schema(params[1])
    extracted_data = _read_test_event(params[0])
    event = {
        'task_name': 'generate_source_vertex',
        'task_kwargs': {
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }
    }
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': rapidjson.dumps(message_object)}
    return {'Records': [body_object]}


@pytest.fixture(params=[
    ('mock_encounter', 'surgeon_schema', 'Encounter'),
    ('mock_patient', 'surgeon_schema', 'Patient'),
    ('mock_provider', 'surgeon_schema', 'Provider')
])
def source_vertex_task_deployment_event(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    schema = _read_schema(params[1])
    extracted_data = _read_test_event(params[0])
    event = {
        'task_name': 'generate_source_vertex',
        'task_kwargs': {
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }
    }
    event_string = ajson.dumps(event)
    return event_string


@pytest.fixture
def test_event():
    return _read_test_event


@pytest.fixture
def test_schema():
    return _read_schema


@pytest.fixture
def mock_generate_source_vertex_event():
    return _generate_leech_event('generate_source_vertex_event')


@pytest.fixture
def dev_dynamo():
    dynamo_patch = patch('toll_booth.obj.data_objects.sensitive_data.boto3.resource')
    mock_dynamo = dynamo_patch.start()
    import boto3
    mock_dynamo.return_value = boto3.Session(profile_name='dev').resource('dynamodb')
    yield mock_dynamo
    mock_dynamo.stop()


@pytest.fixture
def dev_s3_stored_data():
    boto_patch = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_boto = boto_patch.start()
    import boto3
    mock_boto.return_value = boto3.Session(profile_name='dev').resource('s3')
    yield mock_boto
    boto_patch.stop()


@pytest.fixture
def mock_bullhorn_boto():
    boto_patch = patch('toll_booth.tasks.leech.Bullhorn')
    mock_boto = boto_patch.start()
    yield mock_boto
    boto_patch.stop()


@pytest.fixture(autouse=True)
def silence_x_ray():
    x_ray_patch_all = 'algernon.aws.lambda_logging.patch_all'
    patch(x_ray_patch_all).start()
    yield
    patch.stopall()


@pytest.fixture
def environment():
    os.environ['LEECH_LISTENER_ARN'] = 'some_arn'


@pytest.fixture
def mock_context():
    from unittest.mock import MagicMock
    context = MagicMock(name='context')
    context.__reduce__ = cheap_mock
    context.function_name = 'test_function'
    context.invoked_function_arn = 'test_function_arn'
    context.aws_request_id = '12344_request_id'
    context.get_remaining_time_in_millis.side_effect = [1000001, 500001, 250000, 0]
    return context


def cheap_mock(*args):
    from unittest.mock import Mock
    return Mock, ()


def _read_test_event(event_name):
    with open(path.join('tests', 'test_events', f'{event_name}.json')) as json_file:
        event = rapidjson.load(json_file)
        return event


def _read_schema(schema_name=None, entry_name=None):
    if not schema_name:
        schema_name = 'schema'
    with open(path.join('tests', 'test_events', 'schema', f'{schema_name}.json')) as json_file:
        event = rapidjson.load(json_file)
        from toll_booth.obj.schemata.schema_parser import SchemaParer
        vertexes, edges = SchemaParer.parse(event)
        schema = Schema(vertexes, edges)
        if not entry_name:
            return schema
        return schema[entry_name]


def _generate_leech_event(event_name):
    event = _read_test_event(event_name)
    event_string = rapidjson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': rapidjson.dumps(message_object)}
    return {'Records': [body_object]}
