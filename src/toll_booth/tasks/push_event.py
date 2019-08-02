import logging
import boto3
import rapidjson

from toll_booth.obj.scalars.inputs import InputVertex
from toll_booth.obj.serializers import FireHoseEncoder


def _generate_new_object_event(new_object, is_edge=False):
    detail_type = 'vertex_added'
    if is_edge:
        detail_type = 'edge_added'
    event_entry = {
        'Source': 'algernon',
        'DetailType': detail_type,
        'Detail': rapidjson.dumps(new_object.for_index, default=FireHoseEncoder.default),
        'Resources': []
    }
    logging.debug(f'generated event for {new_object}: {event_entry}')
    return event_entry


def event_handler(source_vertex: InputVertex, **kwargs):
    logging.info(f'received a call to the event_handler: {source_vertex}, {kwargs}')
    session = boto3.session.Session()
    event_client = session.client('events')
    entries = [_generate_new_object_event(source_vertex)]
    if kwargs.get('edge'):
        entries.append(_generate_new_object_event(kwargs['edge'], is_edge=True))
    if kwargs.get('target_vertex'):
        entries.append(_generate_new_object_event(kwargs['target_vertex']))
    response = event_client.put_events(Entries=entries)
    failed = [x for x in response['Entries'] if 'ErrorCode' in x]
    if failed:
        raise RuntimeError(f'failed to publish some events to AWS: {failed}')
