import logging
import uuid

import boto3
import rapidjson
from algernon import queued, ajson, rebuild_event
from algernon.aws import lambda_logged, StoredData
from aws_xray_sdk.core import xray_recorder

from toll_booth import tasks


def _generate_stored_results(results):
    stored_results = rapidjson.loads(ajson.dumps(StoredData.from_object(uuid.uuid4(), results, True)))
    return stored_results


def _lookup_resource(resource_name):
    client = boto3.client('ssm')
    response = client.get_parameter(
        Name=resource_name
    )
    parameter = response['Parameter']
    return parameter['Value']


def _start_leech_machine(input_message, machine_arn):
    client = boto3.client('stepfunctions')
    message_body = rapidjson.loads(input_message['body'])
    original_payload = message_body['Message']
    response = client.start_execution(
        stateMachineArn=machine_arn,
        input=original_payload
    )
    return response['executionArn']


@lambda_logged
@xray_recorder.capture('leech')
def sfn_leech(event, context):
    from multiprocessing.pool import ThreadPool

    logging.info(f'started a call for a sfn_leech task, event: {event}, context: {context}')
    machine_arn = _lookup_resource('leech_sfn')
    batch = [(x, machine_arn) for x in event['Records']]
    pool = ThreadPool(len(batch))
    results = pool.starmap(_start_leech_machine, batch)
    pool.close()
    pool.join()
    if len(results) != len(batch):
        raise RuntimeError(f'it seems like one of the machines did not start correctly')


@lambda_logged
def leech_h(event, context):
    logging.info(f'started a call for a leech task, event: {event}, context: {context}')
    event = rebuild_event(event['payload'])
    results = tasks.leech(**event)
    logging.info(f'completed a call for leech task, event: {event}, results: {results}')
    stored_results = _generate_stored_results(results)
    return stored_results


@lambda_logged
def generate_source_vertex_h(event, context):
    logging.info(f'started a call for a generate_source_vertex task, event: {event}, context: {context}')
    event = rebuild_event(event['payload'])
    results = tasks.generate_source_vertex(**event)
    logging.info(f'completed a call for generate_source_vertex task, event: {event}, results: {results}')
    stored_results = _generate_stored_results(results)
    return {
        'results': stored_results,
        'graphing_vertex': results['source_vertex'].for_gql
    }


@lambda_logged
def derive_potential_connections_h(event, context):
    logging.info(f'started a call for a derive_potential_connections task, event: {event}, context: {context}')
    event = rebuild_event(event['payload'])
    results = tasks.derive_potential_connections(**event)
    logging.info(f'completed a call for derive_potential_connections task, event: {event}, results: {results}')
    stored_results = _generate_stored_results(results)
    return {
        'results': stored_results,
        'count': len(results)
    }


@lambda_logged
def check_for_existing_vertexes_h(event, context):
    logging.info(f'started a call for a check_for_existing_vertexes task, event: {event}, context: {context}')
    event = rebuild_event(event['payload'])
    results = tasks.check_for_existing_vertexes(**event)
    logging.info(f'completed a call for check_for_existing_vertexes task, event: {event}, results: {results}')
    stored_results = _generate_stored_results(results)
    return {
        'results': stored_results,
        'count': len(results)
    }


@lambda_logged
def generate_potential_edge_h(event, context):
    logging.info(f'started a call for a generate_potential_edge task, event: {event}, context: {context}')
    event = rebuild_event(event['payload'])
    results = tasks.generate_potential_edge(**event)
    logging.info(f'completed a call for generate_potential_edge task, event: {event}, results: {results}')
    stored_results = _generate_stored_results(results)
    return {
        'results': stored_results,
        'graphing_vertex': results['identified_vertex'].for_gql,
        'graphing_edge': results['edge'].for_gql
    }


@lambda_logged
def object_iterator(event, context):
    event = rebuild_event(event)
    logging.info(f'started a call for an iteration task, event: {event}, context: {context}')
    results = event['results']
    results_count = event['count']
    index = event.get('index', 0)
    stored_results = _generate_stored_results(results)

    try:
        indicated_object = results[index]
    except IndexError:
        index += 1
        response = {
            'index': index,
            'count': results_count,
            'more': False,
            'results': stored_results
        }
        return response
    stored_object = _generate_stored_results(indicated_object)
    index += 1
    more = index <= results_count
    response = {
        'index': index,
        'more': more,
        'count': results_count,
        'results': stored_results,
        'object': stored_object
    }
    return response
