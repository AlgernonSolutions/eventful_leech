import logging
import boto3
import rapidjson
from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.serializers import FireHoseEncoder


def _generate_new_object_event(new_object, is_edge=False):
    detail_type = 'vertex_added'
    if is_edge:
        detail_type = 'edge_added'
    event_entry = {
        'Source': 'algernon',
        'DetailType': detail_type,
        'Detail': rapidjson.dumps(new_object, default=FireHoseEncoder.default),
        'Resources': []
    }
    logging.debug(f'generated event for {new_object}: {event_entry}')
    return event_entry


@xray_recorder.capture()
def push_event(leech, **kwargs):
    logging.info(f'received a call to the event_handler: {leech}, {kwargs}')
    session = boto3.session.Session()
    event_client = session.client('events')
    source_vertex = leech['source_vertex']
    entries = [_generate_new_object_event(source_vertex)]
    if leech.get('edge'):
        entries.append(_generate_new_object_event(leech['edge'], is_edge=True))
    if leech.get('other_vertex'):
        entries.append(_generate_new_object_event(leech['other_vertex']))
    response = event_client.put_events(Entries=entries)
    failed = [x for x in response['Entries'] if 'ErrorCode' in x]
    if failed:
        raise RuntimeError(f'failed to publish some events to AWS: {failed}')
