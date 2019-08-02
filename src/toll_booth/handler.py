import logging

from algernon import rebuild_event
from algernon.aws import lambda_logged
from aws_xray_sdk.core import xray_recorder
from toll_booth import tasks


@lambda_logged
@xray_recorder.capture()
def handler(event, context):
    logging.info(f'started a call for a leech task: {event}/{context}')
    event = rebuild_event(event)
    task_name = event['task_name']
    task_kwargs = event['task_kwargs']
    task_fn = getattr(tasks, task_name)
    results = task_fn(**task_kwargs)
    logging.info(f'completed a call for a leech task: {event}/{results}')
    return results
