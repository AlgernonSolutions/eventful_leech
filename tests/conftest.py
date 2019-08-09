import json
import os
from os import path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from algernon import ajson

from toll_booth.obj.schemata.schema import Schema


@pytest.fixture
def fire_hose_event():
    return _read_test_event('fire_hose_event_2')


@pytest.fixture
def mocks(request):
    patches = []
    mocks = {}
    indicated_patches = {}
    test_name = request.node.originalname
    if test_name in [
        'test_generate_source_vertex',
        'test_generate_potential_connections',
        'test_check_for_existing_vertexes'
    ]:
        indicated_patches = {
            's3': mock_objs.mock_s3_stored_data,
            'gql': mock_objs.gql_client_notary,
            'bullhorn': mock_objs.tasks_bullhorn
        }

    for mock_name, mock_generator in indicated_patches.items():
        mock_obj, patch_obj = mock_generator()
        mocks[mock_name] = mock_obj
        patches.append(patch_obj)
    yield mocks
    for patch_obj in patches:
        patch_obj.stop()


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
    ('leech_event', 'surgeon_schema', 'Encounter'),
])
def leech_integration_event(request):
    params = request.param
    event = _read_test_event(params[0])
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


@pytest.fixture(params=[
    ('mock_generate_source_vertex', 'surgeon_schema', 'Encounter'),
    ('mock_patient', 'surgeon_schema', 'Patient'),
    ('mock_provider', 'surgeon_schema', 'Provider'),
    ('documentation_event', 'surgeon_schema', 'Documentation'),
    ('documentation_field_event', 'surgeon_schema', 'DocumentationField'),
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
    body_object = {'body': ajson.dumps(message_object)}
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


@pytest.fixture(params=[
    ('mock_derive_potential_connections', 'surgeon_schema', 'Documentation')
])
def potential_connections_unit_event(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    schema = _read_schema(params[1])
    test_event = _read_test_event(params[0])
    task_kwargs = ajson.loads(ajson.dumps(test_event))
    task_kwargs.update({'schema': schema, 'schema_entry': schema_entry})
    event = {
        'task_name': 'derive_potential_connections',
        'task_kwargs': task_kwargs
    }
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


@pytest.fixture(params=[
    ('mock_derive_potential_connections', 'surgeon_schema', 'Documentation')
])
def potential_connections_integration_event(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    schema = _read_schema(params[1])
    test_event = _read_test_event(params[0])
    task_kwargs = ajson.loads(ajson.dumps(test_event))
    task_kwargs.update({'schema': schema, 'schema_entry': schema_entry})
    event = {
        'task_name': 'derive_potential_connections',
        'task_kwargs': task_kwargs,
        'flow_id': 'some_flow_id'
    }
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


@pytest.fixture(params=[
    ('mock_check_for_existing_vertexes', 'surgeon_schema', 'Documentation', '_documentation_'),
    ('mock_check_for_existing_vertexes_2', 'surgeon_schema', 'Encounter', '_received_'),
])
def find_existing_vertexes(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    schema = _read_schema(params[1])
    test_event = _read_test_event(params[0])
    task_kwargs = ajson.loads(ajson.dumps(test_event))
    edge_type = params[3]
    rule_entry = _generate_linking_rule(schema_entry, edge_type)
    task_kwargs.update({'schema': schema, 'schema_entry': schema_entry, 'rule_entry': rule_entry})
    event = {
        'task_name': 'check_for_existing_vertexes',
        'task_kwargs': task_kwargs
    }
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


@pytest.fixture(params=[
    ('mock_generate_potential_edge', 'surgeon_schema', 'Documentation', '_documentation_')
])
def generate_edge_integration_event(request):
    params = request.param
    schema_entry = _read_schema(params[1], params[2])
    test_event = _read_test_event(params[0])
    edge_type = params[3]
    rule_entry = _generate_linking_rule(schema_entry, edge_type)
    edge_schema_entry = _read_schema(params[1], edge_type)
    task_kwargs = ajson.loads(ajson.dumps(test_event))
    task_kwargs.update({'schema_entry': edge_schema_entry, 'rule_entry': rule_entry})
    event = {
        'task_name': 'generate_potential_edge',
        'task_kwargs': task_kwargs,
        'flow_id': 'some_flow_id'
    }
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


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
def mock_s3_stored_data():
    boto_patch = patch('toll_booth.obj.data_objects.stored_data.boto3.resource')
    mock_boto = boto_patch.start()
    mock_boto.return_value = MagicMock()
    yield mock_boto
    boto_patch.stop()


@pytest.fixture
def mock_bullhorn_boto():
    boto_patch = patch('toll_booth.tasks.leech.Bullhorn')
    mock_boto = boto_patch.start()
    yield mock_boto
    boto_patch.stop()


@pytest.fixture
def mock_gql_client():
    boto_patch = patch('toll_booth.obj.gql.gql_client.GqlNotary')
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
    os.environ['LISTENER_ARN'] = 'some_arn'


@pytest.fixture
def unit_environment():
    os.environ['GRAPH_GQL_ENDPOINT'] = 'some_endpoint.com'
    os.environ['LISTENER_ARN'] = 'some_arn'
    os.environ['ENCOUNTER_BUCKET'] = 'algernonsolutions-leech-dev'
    os.environ['DEBUG'] = 'True'
    os.environ['GQL_API_KEY'] = 'some_key'
    os.environ['SENSITIVE_TABLE'] = 'some_table'


@pytest.fixture
def integration_environment():
    os.environ['GRAPH_GQL_ENDPOINT'] = 'jlgmowxwofe33pdekndakyzx4i.appsync-api.us-east-1.amazonaws.com'
    os.environ['ENCOUNTER_BUCKET'] = 'algernonsolutions-encounters-dev'
    os.environ['DEBUG'] = 'False'
    os.environ['SENSITIVE_TABLE'] = 'Sensitives'


@pytest.fixture
def mock_context():
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


def _read_schema(schema_name=None, entry_name=None):
    if not schema_name:
        schema_name = 'schema'
    with open(path.join('test_events', 'schema', f'{schema_name}.json')) as json_file:
        event = json.load(json_file)
        from toll_booth.obj.schemata.schema_parser import SchemaParer
        vertexes, edges = SchemaParer.parse(event)
        schema = Schema(vertexes, edges)
        if not entry_name:
            return schema
        return schema[entry_name]


def _generate_leech_event(event_name):
    event = _read_test_event(event_name)
    event_string = ajson.dumps(event)
    message_object = {'Message': event_string}
    body_object = {'body': ajson.dumps(message_object)}
    return {'Records': [body_object]}


def _generate_linking_rule(schema_entry, edge_type):
    linking_rules = schema_entry.rules.linking_rules
    for rule_set in linking_rules:
        rules = rule_set.rules
        for rule in rules:
            if str(rule) == edge_type:
                return rule


def _read_test_event(event_name):
    user_home = path.expanduser('~')
    with open(path.join(str(user_home), '.algernon', 'eventful_leech', f'{event_name}.json')) as json_file:
        event = json.load(json_file)
        return event


@pytest.fixture(params=['leech_start'])
def aio_event(request):
    return _read_test_event(request.param)


@pytest.fixture(params=['push_event'])
def test_push_event(request):
    return _read_test_event(request.param)

