import logging
from decimal import Decimal

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.index.index_manager import IndexManager
from toll_booth.obj.index.troubles import UniqueIndexViolationException


def _format_object_property(property_type, object_property):
    if property_type == 'stored_properties':
        return {
            'data_type': object_property['data_type'],
            'storage_uri': object_property['storage_uri'],
            'storage_class': object_property['storage_class'],
            '__typename': 'StoredPropertyValue'
        }
    if property_type == 'sensitive_properties':
        return {
            'data_type': object_property['data_type'],
            'pointer': object_property['pointer'],
            '__typename': 'SensitivePropertyValue'
        }
    if property_type == 'local_properties':
        return {
            'data_type': object_property['data_type'],
            'property_value': object_property['property_value'],
            '__typename': 'LocalPropertyValue'
        }
    raise RuntimeError(f'do not know how to store object property type: {property_type}')


def _collect_object_properties(scalar, is_edge=False):
    collected_properties = {}
    object_property_name = 'edge_properties' if is_edge else 'vertex_properties'
    object_properties = scalar[object_property_name]
    for property_type, type_properties in object_properties.items():
        for type_property in type_properties:
            property_name = type_property['property_name']
            if property_name not in collected_properties:
                indexed_property = _format_object_property(property_type, type_property)
                collected_properties[property_name] = indexed_property
    return collected_properties


def _format_object_for_index(scalar, is_edge=False):
    object_type_property = 'edge_label' if is_edge else 'vertex_type'
    identifier = scalar['identifier']['property_value']
    id_value = scalar['id_value']
    object_for_index = {
        'sid_value': str(id_value),
        'identifier': str(identifier),
        'internal_id': str(scalar['internal_id']),
        'id_value': _format_object_property('local_properties', id_value),
        'object_type': scalar[object_type_property]
    }
    if isinstance(id_value, int) or isinstance(id_value, Decimal):
        object_for_index['numeric_id_value'] = id_value
    object_properties = _collect_object_properties(scalar, is_edge)
    object_for_index.update(object_properties)
    return object_for_index


def _index_object(index_manager: IndexManager, scalar, is_edge=False):
    index_object = _format_object_for_index(scalar, is_edge)
    try:
        result = index_manager.index_object(index_object)
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
