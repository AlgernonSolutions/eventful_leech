import json
import os
from datetime import datetime
from decimal import Decimal

import boto3
import rapidjson
from algernon import rebuild_event
from algernon.aws import lambda_logged


class FireHoseEncoder(json.JSONEncoder):
    @classmethod
    def default(cls, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super(FireHoseEncoder, cls()).default(obj)


def _send_to_fire_hose(stream_name, records):
    client = boto3.client('firehose')
    batch = [{'Data': rapidjson.dumps(x, default=FireHoseEncoder.default).encode()} for x in records]
    response = client.put_record_batch(
        DeliveryStreamName=stream_name,
        Records=batch
    )
    if response['FailedPutCount']:
        failed_records = [x for x in response['RequestResponses'] if 'ErrorCode' in x]
        raise RuntimeError(f'could not fire_hose these records: {failed_records}')


@lambda_logged
def fire_hose_handler(event, context):
    stream_name = os.environ['S3_FIRE_HOSE_NAME']
    if 'Records' in event:
        batch = []
        for entry in event['Records']:
            entry_body = rapidjson.loads(entry['body'])
            original_payload = rapidjson.loads(entry_body['Message'])
            payload = rebuild_event(original_payload)
            batch.append(payload)
        _send_to_fire_hose(stream_name, batch)
        return
    event = rebuild_event(event)
    _send_to_fire_hose(stream_name, [event])
