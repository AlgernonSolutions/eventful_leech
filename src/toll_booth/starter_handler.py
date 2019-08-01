import logging
import re
import uuid

import boto3
import rapidjson
from algernon.aws import lambda_logged, ruffians, StoredData


def _retrieve_event_driven_payload(original_payload):
    logging.info(f'received a notice of a new s3_object: {original_payload}')
    pattern = re.compile(r'#!#')
    event_detail = original_payload['detail']
    request_params = event_detail['requestParameters']
    bucket_name = request_params['bucketName']
    file_key = request_params['key']
    stored_event_obj = boto3.resource('s3').Object(bucket_name, file_key)
    stored_event = stored_event_obj.get()['Body'].read().decode()
    un_joined_pattern = re.compile(r'}(\s*){')
    prepped_event = un_joined_pattern.sub('}#!#{', stored_event)
    pieces = pattern.split(prepped_event)
    return [rapidjson.loads(x) for x in pieces if x]


@lambda_logged
def starter_handler(event, context):
    stored_objects = _retrieve_event_driven_payload(event)
    for stored_object in stored_objects:
        logging.info(f'after parsing, the following object is ready for leeching: {stored_object}')
        stored_data = StoredData.from_object(uuid.uuid4(), stored_object, full_unpack=True)
        ruffians.start_machine('aio_sfn', stored_data)
