import logging

from algernon import queued, ajson
from algernon.aws import lambda_logged
from aws_xray_sdk.core import xray_recorder

from toll_booth import tasks


def _rebuild_event(original_event):
    return ajson.loads(ajson.dumps(original_event))


@lambda_logged
@queued
@xray_recorder.capture('leech')
def handler(event, context):
    logging.info(f'started a call for a borg task, event: {event}, context: {context}')
    event = _rebuild_event(event)
    task_name = event['task_name']
    task_kwargs = event.get('task_kwargs', {})
    if task_kwargs is None:
        task_kwargs = {}
    task_function = getattr(tasks, task_name)
    results = task_function(**task_kwargs)
    logging.info(f'completed a call for borg task, event: {event}, results: {results}')
    return ajson.dumps(results)
