import os
from datetime import datetime
from decimal import Decimal
from typing import Union, Dict, Any

import dateutil

from toll_booth.obj.data_objects import MissingObjectProperty, InternalId, IdentifierStem
from toll_booth.obj.data_objects.stored_data import S3StoredData
from toll_booth.obj.schemata.entry_property import SchemaPropertyEntry, EdgePropertyEntry
from toll_booth.obj.schemata.schema_entry import SchemaVertexEntry, SchemaEdgeEntry

type_map = {
    'Number': 'N',
    'DateTime': 'DT',
    'String': 'S',
    'Boolean': 'B'
}


def _convert_python_datetime_to_gremlin(python_datetime: datetime):
    from pytz import timezone
    gremlin_format = '%Y-%m-%dT%H:%M:%S%z'
    if isinstance(python_datetime, str):
        python_datetime = dateutil.parser.parse(python_datetime)
    if not python_datetime.tzinfo:
        naive_datetime = python_datetime.replace(tzinfo=None)
        utc_datetime = timezone('UTC').localize(naive_datetime)
        return utc_datetime.strftime(gremlin_format)
    return python_datetime.strftime(gremlin_format)


def _set_property_data_type(property_name: str,
                            entry_property: Union[SchemaPropertyEntry, EdgePropertyEntry],
                            test_property: Union[str, float, Decimal, int, datetime, None]):
    property_data_type = entry_property.property_data_type
    if not test_property:
        return None
    if test_property == '':
        return None
    if property_data_type == 'Number':
        try:
            return Decimal(test_property)
        except TypeError:
            return Decimal(test_property.timestamp())
    if property_data_type == 'String':
        return str(test_property)
    if property_data_type == 'DateTime':
        return _convert_python_datetime_to_gremlin(test_property)
    raise NotImplementedError(
        f'data type {property_data_type} for property named: {property_name} is unknown to the system')


def _generate_s3_bucket_name(bucket_name_source):
    name_source = bucket_name_source['source']
    if name_source == 'environment':
        bucket_name = os.environ[bucket_name_source['environment_variable_name']]
        return bucket_name
    if name_source == 'static':
        return bucket_name_source['bucket_name']


def _generate_object_property(property_name: str,
                              entry_property: Union[SchemaPropertyEntry, EdgePropertyEntry],
                              property_value: Union[str, float, Decimal, int, datetime, None],
                              source_internal_id: str = None):
    data_type = type_map[entry_property.property_data_type]
    if entry_property.sensitive:
        gql_entry = {
            'data_type': entry_property.property_data_type,
            'property_name': property_name,
            'property_value': property_value,
            'source_internal_id': source_internal_id
        }
        return 'sensitives_property', gql_entry
    if entry_property.is_stored:
        storage_class = entry_property.stored['storage_class']
        if storage_class == 's3':
            bucket_name = _generate_s3_bucket_name(entry_property.stored['bucket_name_source'])
            object_key = f'{source_internal_id}.{property_name}'
            s3_args = {
                'data_type': data_type,
                'bucket_name': bucket_name,
                'object_key': object_key,
                'object_data': property_value
            }
            s3_data = S3StoredData.store(**s3_args)
            gql_entry = {
                'data_type': data_type,
                'property_name': property_name,
                'storage_class': 's3',
                'storage_uri': s3_data.storage_uri
            }
            return 'stored_properties', gql_entry
        raise NotImplementedError(f'can not store {entry_property} per storage_class: {storage_class},'
                                  f'this class is unknown to the system')
    gql_entry = {
        'data_type': data_type,
        'property_name': property_name,
        'property_value': str(property_value)
    }
    return 'local_properties', gql_entry


class ObjectRegulator:
    def __init__(self, schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry]):
        self._schema_entry = schema_entry
        self._internal_id_key = schema_entry.internal_id_key
        self._entry_properties_schema = schema_entry.entry_properties

    @property
    def schema_entry(self):
        return self._schema_entry

    def create_potential_vertex_data(self,
                                     object_data: dict,
                                     internal_id: InternalId = None,
                                     identifier_stem: IdentifierStem = None,
                                     id_value: Union[str, int, float, Decimal] = None):
        """

        Args:
            object_data:
            internal_id:
            identifier_stem:
            id_value:

        Returns:

        """
        object_properties = self._standardize_object_properties(object_data)
        if internal_id is None:
            internal_id = self._create_internal_id(object_properties)
        if identifier_stem is None:
            identifier_stem = self._create_identifier_stem(object_properties, object_data)
        if id_value is None:
            id_value = self._create_id_value(object_properties)
        object_properties = self._convert_object_properties(internal_id, object_properties)
        return {
            'object_type': self._schema_entry.object_type,
            'internal_id': internal_id,
            'identifier_stem': identifier_stem,
            'id_value': id_value,
            'object_properties': object_properties,
        }

    def _standardize_object_properties(self, object_data: Dict[str, Any]):
        returned_properties = {}
        for property_name, entry_property in self._entry_properties_schema.items():
            try:
                test_property = object_data[property_name]
            except KeyError:
                returned_properties[property_name] = MissingObjectProperty()
                continue

            test_property = _set_property_data_type(property_name, entry_property, test_property)
            returned_properties[property_name] = test_property
        return returned_properties

    def _convert_object_properties(self, internal_id: str, object_properties: Dict[str, Any]):
        converted_properties = {}
        for property_name, entry_property in self._entry_properties_schema.items():
            object_property = object_properties[property_name]
            property_type, property_value = _generate_object_property(
                property_name, entry_property, object_property, internal_id)
            if property_type not in converted_properties:
                converted_properties[property_type] = []
            converted_properties[property_type].append(property_value)
        return converted_properties

    def _create_internal_id(self, object_properties: Dict[str, Any], for_known: bool = False):
        static_key_fields = {
            'object_type': self._schema_entry.entry_name,
            'id_value_field': self._schema_entry.id_value_field
        }
        try:
            key_values = []
            internal_id_key = self._schema_entry.internal_id_key
            for field_name in internal_id_key:
                if field_name in static_key_fields:
                    key_values.append(str(static_key_fields[field_name]))
                    continue
                if hasattr(field_name, 'is_missing'):
                    key_values.append('MISSING_OBJECT_PROPERTY')
                key_value = object_properties[field_name]
                key_values.append(str(key_value))
            id_string = ''.join(key_values)
            internal_id = InternalId(id_string).id_value
            return internal_id
        except KeyError:
            if for_known:
                raise RuntimeError(
                    f'could not calculate internal id for a source/known object, this generally indicates that the '
                    f'extraction for that object was flawed. error for graph object: {object_properties}'
                )
            return self._internal_id_key

    def _create_identifier_stem(self, object_properties: Dict[str, Any], object_data: Dict[str, Any]):
        try:
            paired_identifiers = {}

            identifier_stem_key = self._schema_entry.identifier_stem
            object_type = self._schema_entry.object_type
            for field_name in identifier_stem_key:
                try:
                    key_value = object_properties[field_name]
                except KeyError:
                    key_value = object_data[field_name]
                if isinstance(key_value, MissingObjectProperty):
                    return self._schema_entry.identifier_stem
                if key_value is None and '::stub' not in object_type:
                    object_type = object_type + '::stub'
                paired_identifiers[field_name] = key_value
            identifier_stem = IdentifierStem('vertex', object_type, paired_identifiers)
            return {
                'data_type': 'S',
                'property_value': str(identifier_stem),
                'property_name': 'identifier_stem'
            }
        except KeyError:
            return self._schema_entry.identifier_stem

    def _create_id_value(self, object_properties: Dict[str, Any]):
        try:
            id_value = object_properties[self._schema_entry.id_value_field]
            vertex_properties = self._schema_entry.vertex_properties
            id_value_properties = vertex_properties[self._schema_entry.id_value_field]
            if id_value_properties.property_data_type == 'DateTime':
                remade_date_value = dateutil.parser.parse(id_value)
                id_value = Decimal(remade_date_value.timestamp())
            return {
                'data_type': type_map[id_value_properties.property_data_type],
                'property_name': 'id_value',
                'property_value': str(id_value)
            }
        except KeyError:
            return self._schema_entry.id_value_field
