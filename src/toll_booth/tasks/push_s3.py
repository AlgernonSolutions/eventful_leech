from decimal import Decimal

import boto3
import rapidjson
from aws_xray_sdk.core import xray_recorder
from botocore.exceptions import ClientError

from toll_booth.obj.data_objects import SensitivePropertyValue
from toll_booth.obj.data_objects.object_properties.stored_property import S3StoredPropertyValue
from toll_booth.obj.serializers import FireHoseEncoder
from toll_booth.obj.utils import set_property_data_type


def _reconstitute_object_property(property_type, object_property):
    if property_type == 'stored_properties':
        storage_class = object_property['storage_class']
        if storage_class == 's3':
            data_type = object_property['data_type']
            storage_uri = object_property['storage_uri']
            stored_data = S3StoredPropertyValue(data_type, storage_class, storage_uri)
            stored_property_value = stored_data.retrieve()
            return stored_property_value
        raise RuntimeError(f'do not know how to reconstitute for storage_class: {storage_class}')
    if property_type == 'sensitive_properties':
        pointer = object_property['pointer']
        sensitive_data = SensitivePropertyValue.from_insensitive_pointer(pointer)
        return sensitive_data
    if property_type == 'local_properties':
        data_type = object_property['data_type']
        property_value = object_property['property_value']
        return set_property_data_type(data_type, property_value)
    raise RuntimeError(f'do not know how to reconstitute property type: {property_type}')


def _format_object_properties_for_s3(scalar, is_edge=False):
    collected_properties = {}
    object_property_name = 'edge_properties' if is_edge else 'vertex_properties'
    object_properties = scalar[object_property_name]
    for property_type, type_properties in object_properties.items():
        for type_property in type_properties:
            property_name = type_property['property_name']
            if property_name not in collected_properties:
                indexed_property = _reconstitute_object_property(property_type, type_property)
                collected_properties[property_name] = indexed_property
    return collected_properties


def _format_object_for_s3(scalar, is_edge=False):
    object_type_property = 'edge_label' if is_edge else 'vertex_type'
    identifier_stem = scalar['identifier_stem']['property_value']
    id_value = scalar['id_value']['property_value']
    object_for_index = {
        'identifier_stem': str(identifier_stem),
        'internal_id': str(scalar['internal_id']),
        'id_value': id_value,
        'object_type': scalar[object_type_property],
        'object_class': 'Edge' if is_edge else 'Vertex'
    }
    if is_edge:
        object_for_index.update({
            'from_internal_id': scalar['source_vertex_internal_id'],
            'to_internal_id': scalar['target_vertex_internal_id']
        })
    if isinstance(id_value, int) or isinstance(id_value, Decimal):
        object_for_index['numeric_id_value'] = id_value
    object_properties = _format_object_properties_for_s3(scalar, is_edge)
    object_for_index.update(object_properties)
    return object_for_index


def _check_for_object(s3_object):
    try:
        s3_object.load()
        return True
    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise e
        return False


def _store_to_s3(bucket_name, base_file_key, scalar, is_edge=False):
    file_key = f'{base_file_key}/{scalar["internal_id"]}.json'
    s3_resource = boto3.resource('s3')
    s3_object = s3_resource.Object(bucket_name, file_key)
    if _check_for_object(s3_object):
        return {
            'status': 'failed',
            'operation': 'store_to_s3',
            'details': {
                'message': f'object at {file_key} already exists in {bucket_name}',
                'bucket_name': bucket_name,
                'file_key': file_key
            }
        }
    object_for_s3 = _format_object_for_s3(scalar, is_edge)
    s3_object.put(Body=rapidjson.dumps(object_for_s3, default=FireHoseEncoder.default))
    return {
            'status': 'succeeded',
            'operation': 'store_to_s3',
            'details': {
                'message': '',
                'bucket_name': bucket_name,
                'file_key': file_key,
                'stored_object': object_for_s3
            }
        }


@xray_recorder.capture()
def s3_handler(source_vertex, edge=None, other_vertex=None, **kwargs):
    s3_results = {}
    bucket_name = kwargs['bucket_name']
    base_file_key = kwargs['base_file_key']
    s3_results['source_vertex'] = _store_to_s3(bucket_name, base_file_key, source_vertex)
    if other_vertex:
        s3_results['other_vertex'] = _store_to_s3(bucket_name, base_file_key, other_vertex)
    if edge:
        s3_results['edge'] = _store_to_s3(bucket_name, base_file_key, edge, is_edge=True)
    return s3_results
