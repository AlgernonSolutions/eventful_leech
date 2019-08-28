import logging

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.index.index_manager import IndexManager
from toll_booth.obj.index.mission import format_object_for_index
from toll_booth.obj.index.troubles import UniqueIndexViolationException


def _index_object(index_manager: IndexManager, scalar, is_edge=False):
    index_object = format_object_for_index(scalar, is_edge)
    try:
        index_manager.index_object(index_object, is_edge)
        return {
            'status': 'succeeded',
            'operation': 'index_object',
            'details': {
                'message': ''
            }
        }
    except UniqueIndexViolationException as e:
        logging.warning(f'attempted to index {scalar}, it seems it has already been indexed: {e.index_name}')
        return {
            'status': 'failed',
            'operation': 'index_object',
            'details': {
                'message': f'attempted to index {scalar}, it seems it has already been indexed: {e.index_name}'
            }
        }
    except Exception as e:
        return {
            'status': 'failed',
            'operation': 'index_object',
            'details': {
                'message': e.args
            }
        }


# @xray_recorder.capture()
def push_index(leech, **kwargs):
    logging.info(f'received a call to the index_handler: {leech}, {kwargs}')
    index_results = {}
    index_manager = IndexManager()
    source_vertex = leech['source_vertex']
    edge = leech.get('edge')
    other_vertex = leech.get('other_vertex')
    index_results['source_vertex'] = _index_object(index_manager, source_vertex)
    if other_vertex:
        index_results['other_vertex'] = _index_object(index_manager, other_vertex)
    if edge:
        index_results['edge'] = _index_object(index_manager, edge, is_edge=True)
    return index_results
