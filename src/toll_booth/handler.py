import logging
import os

import boto3
from algernon import rebuild_event
from algernon.aws import lambda_logged
from aws_xray_sdk.core import xray_recorder
from toll_booth import tasks

ENVIRON_VARIABLES = [
    'ALGERNON_BUCKET_NAME',
    'STORAGE_BUCKET_NAME',
    'ENCOUNTER_BUCKET_NAME',
    'GRAPH_GQL_ENDPOINT',
    'GRAPH_DB_ENDPOINT',
    'GRAPH_DB_READER_ENDPOINT',
    'INDEX_TABLE_NAME',
    'SENSITIVE_TABLE_NAME',
    'PROGRESS_TABLE_NAME',
    'FIRE_HOSE_NAME'
]


def _load_config(variable_names):
    client = boto3.client('ssm')
    response = client.get_parameters(Names=[x for x in variable_names])
    results = [(x['Name'], x['Value']) for x in response['Parameters']]
    for entry in results:
        os.environ[entry[0]] = entry[1]


@lambda_logged
@xray_recorder.capture()
def handler(event, context):
    logging.info(f'started a call for a leech task: {event}/{context}')
    _load_config(ENVIRON_VARIABLES)
    event = rebuild_event(event)
    task_name = event['task_name']
    task_kwargs = event['task_kwargs']
    task_fn = getattr(tasks, task_name)
    results = task_fn(**task_kwargs)
    logging.info(f'completed a call for a leech task: {event}/{results}')
    return results
