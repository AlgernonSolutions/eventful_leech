import os
from _pydecimal import Decimal
from datetime import datetime

import dateutil
import pytz

from toll_booth.obj.data_objects import SensitivePropertyValue, MissingObjectProperty
from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.data_objects.object_properties.stored_property import S3StoredPropertyValue
from toll_booth.obj.schemata.entry_property import SchemaPropertyEntry
from toll_booth.obj.schemata.schema import Schema
from toll_booth.tasks import aws_utils

data_type_map = {
    'Number': 'N',
    'DateTime': 'DT',
    'String': 'S',
    'Boolean': 'B'
}
type_map = {
    'local_properties': 'LocalPropertyValue',
    'sensitive_properties': 'SensitivePropertyValue',
    'stored_properties': 'StoredPropertyValue'
}


def _store_s3_property_value(entry_property, property_name, property_value, data_type, source_internal_id):
    bucket_name = _generate_s3_bucket_name(entry_property.stored['bucket_name_source'])
    object_key = f'{property_name}/{source_internal_id}_{property_name}.json'
    s3_args = {
        'data_type': data_type,
        'bucket_name': bucket_name,
        'object_key': object_key,
        'object_data': property_value
    }
    s3_data = S3StoredPropertyValue.store(**s3_args)
    gql_entry = {
        'data_type': data_type,
        'property_name': property_name,
        'storage_class': 's3',
        'storage_uri': s3_data.storage_uri
    }
    return gql_entry


def _generate_s3_bucket_name(bucket_name_source):
    """ generate the bucket_name used to hold StoredObjectProperty using the S3 storage_class

    when storing objects to S3, we have to specify a bucket_name. this name can be provided statically by the schema,
        or dynamically by a named environment_variable

    Args:
        bucket_name_source:

    Returns:

    """
    name_source = bucket_name_source['source']
    if name_source == 'environment':
        bucket_name = os.environ[bucket_name_source['environment_variable_name']]
        return bucket_name
    if name_source == 'static':
        return bucket_name_source['bucket_name']


def _rebuild_id_value(id_vertex_property):
    id_value_property = {'__typename': 'LocalPropertyValue', 'property_name': 'id_value'}
    data_type, property_value = derive_data_type(id_vertex_property)
    id_value_property.update({'data_type': data_type, 'property_value': property_value})
    return id_value_property


def _rebuild_identifier(identifier_vertex_property):
    return {
        'data_type': 'S', '__typename': 'LocalPropertyValue',
        'property_value': identifier_vertex_property, 'property_name': 'identifier'
    }


def _rebuild_sensitive_property(property_name, vertex_property, data_type, internal_id):
    sensitive_entry = SensitivePropertyValue(internal_id, property_name, vertex_property)
    pointer = sensitive_entry.store()
    gql_entry = {
        'data_type': data_type,
        'property_name': property_name,
        'pointer': pointer
    }
    return 'sensitive_properties', gql_entry


def _rebuild_stored_property(property_name, vertex_property, data_type, internal_id, property_schema):
    storage_class = property_schema.stored['storage_class']
    if storage_class == 's3':
        s3_args = (property_schema, property_name, vertex_property, data_type, internal_id)
        return 'stored_properties', _store_s3_property_value(*s3_args)
    raise NotImplementedError(f'can not store {vertex_property} per storage_class: {storage_class},'
                              f'this class is unknown to the system')


def build_vertex_property(property_name, vertex_property, property_schema: SchemaPropertyEntry, source_internal_id):
    if isinstance(vertex_property, MissingObjectProperty):
        return 'missing', None
    data_type = data_type_map[property_schema.property_data_type]
    if property_schema.sensitive:
        return _rebuild_sensitive_property(property_name, vertex_property, data_type, source_internal_id)
    if property_schema.stored:
        return _rebuild_stored_property(property_name, vertex_property, data_type, source_internal_id, property_schema)
    rebuilt_property = {'property_name': property_name}
    rebuilt_property.update({'data_type': data_type, 'property_value': str(vertex_property)})
    return 'local_properties', rebuilt_property


def rebuild_vertex(elastic_hit, schema: Schema):
    excluded_entries = (
        'object_class', 'sid_value',
        'internal_id', 'object_type', 'numeric_id_value')
    object_type = elastic_hit['object_type']
    potential_vertex = {
        '__typename': 'Vertex',
        'internal_id': elastic_hit['internal_id'],
        'vertex_type': object_type,
        'vertex_properties': [],
        'object_type': object_type
    }
    for property_name, vertex_property in elastic_hit.items():
        if property_name in excluded_entries:
            continue
        if property_name == 'id_value':
            potential_vertex[property_name] = _rebuild_id_value(vertex_property)
            continue
        if property_name == 'identifier':
            potential_vertex[property_name] = _rebuild_identifier(vertex_property)
            continue
        vertex_property_entry = schema.vertex_entries[object_type].vertex_properties[property_name]
        source_internal_id = elastic_hit['internal_id']
        build_args = (property_name, vertex_property, vertex_property_entry, source_internal_id)
        property_class, rebuilt_property = build_vertex_property(*build_args)
        rebuilt_property['__typename'] = type_map[property_class]
        potential_vertex['vertex_properties'].append(rebuilt_property)
    return VertexData.from_gql(potential_vertex)


def derive_data_type(property_value):
    if isinstance(property_value, str):
        return 'S', str(property_value)
    if isinstance(property_value, int):
        return 'N', str(property_value)
    if isinstance(property_value, float):
        return 'N', str(property_value)
    if isinstance(property_value, bool):
        return 'B', str(property_value)
    try:
        datetime.fromisoformat(property_value)
        return 'DT', property_value
    except (TypeError, ValueError):
        raise RuntimeError(f'could not derive the data type for: {property_value}')


def set_data_type(data_type, property_value, for_search=False):
    if data_type == 'N':
        if for_search:
            return float(property_value)
        return Decimal(property_value)
    if data_type == 'DT':
        date_time_property = dateutil.parser.parse(property_value)
        if date_time_property.tzinfo is None:
            date_time_property = pytz.utc.localize(date_time_property)
        return date_time_property.isoformat()
    if data_type == 'S':
        return str(property_value)
    if data_type == 'B':
        return property_value.lower() == 'true'
    raise RuntimeError(f'system is not equipped to handle property: {property_value} with data type: {data_type}')


def format_object_property(property_type, object_property, for_index=False):
    data_type = object_property['data_type']
    if property_type == 'stored_properties':
        storage_class = object_property['storage_class']
        storage_uri = object_property['storage_uri']
        if storage_class == 's3':
            property_value = aws_utils.retrieve_s3_property(storage_uri)
            return set_data_type(data_type, property_value, for_search=for_index)
        raise RuntimeError(f'do not know how to retrieve for stored property class: {storage_class}')
    if property_type == 'sensitive_properties':
        property_value = aws_utils.retrieve_sensitive_property(object_property['pointer'])
        return set_data_type(data_type, property_value, for_search=for_index)
    if property_type == 'local_properties':
        property_value = object_property['property_value']
        return set_data_type(data_type, property_value, for_search=for_index)
    raise RuntimeError(f'do not know how to store object property type: {property_type}')


def collect_object_properties(scalar, is_edge=False, for_index=False):
    collected_properties = {}
    object_property_name = 'edge_properties' if is_edge else 'vertex_properties'
    object_properties = scalar[object_property_name]
    for property_type, type_properties in object_properties.items():
        for type_property in type_properties:
            property_name = type_property['property_name']
            if property_name not in collected_properties:
                indexed_property = format_object_property(property_type, type_property, for_index=for_index)
                collected_properties[property_name] = indexed_property
    return collected_properties


def format_object_for_index(scalar, is_edge=False):
    object_type_property = 'edge_label' if is_edge else 'vertex_type'
    identifier = scalar['identifier']['property_value']
    id_value = scalar['id_value']
    object_for_index = {
        'identifier': str(identifier),
        'internal_id': str(scalar['internal_id']),
        'id_value': format_object_property('local_properties', id_value, for_index=True),
        'object_type': scalar[object_type_property],
        'object_class': 'Edge' if is_edge else 'Vertex'
    }
    if is_edge:
        object_for_index['from_internal_id'] = scalar['source_vertex_internal_id']
        object_for_index['to_internal_id'] = scalar['target_vertex_internal_id']
    object_properties = collect_object_properties(scalar, is_edge, for_index=True)
    object_for_index.update(object_properties)
    return object_for_index
