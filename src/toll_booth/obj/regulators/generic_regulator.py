from decimal import Decimal
from typing import Union, Dict, Any

import dateutil

from toll_booth.obj.data_objects import MissingObjectProperty, InternalId, IdentifierStem
from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.index import mission
from toll_booth.obj.schemata.schema_entry import SchemaVertexEntry, SchemaEdgeEntry
from toll_booth.obj.utils import set_property_data_type

type_map = {
    'Number': 'N',
    'DateTime': 'DT',
    'String': 'S',
    'Boolean': 'B'
}


class ObjectRegulator:
    """ generates VertexData objects from the extracted_data per the Schema

        the ObjectRegulator performs several distinct steps to create a VertexData object
        1. since the data in the extracted_data may be of any type (strings, int, etc), we set the type per  the schema
        2. not all data is stored directly onto the graph (large data, HIPAA data, etc), so we create storage specific
            objects for data that is noted in the schema as needing special storage
        3. having normalized the properties of the object, we then create the internal_id, so uniquely reference it
            within the graph
        4. we create an identifier stem to associate it with sibling elements on the graph, and in the index
        5. we extract and set the id_value, which is the link back to the original data source (PK, extracted_time, etc)
    """
    def __init__(self, schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry]):
        self._schema_entry = schema_entry
        self._internal_id_key = schema_entry.internal_id_key
        self._entry_properties_schema = schema_entry.entry_properties

    @property
    def schema_entry(self):
        return self._schema_entry

    def create_potential_vertex_data(self,
                                     object_data: Dict,
                                     internal_id: InternalId = None,
                                     identifier_stem: IdentifierStem = None,
                                     id_value: Union[str, int, float, Decimal] = None) -> VertexData:
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
        vertex_data = VertexData.from_source_data({
            'object_type': self._schema_entry.object_type,
            'internal_id': internal_id,
            'identifier': identifier_stem,
            'id_value': id_value,
            'object_properties': object_properties,
        })
        return vertex_data

    def _standardize_object_properties(self, object_data: Dict[str, Any]):
        """ convert all object properties into their appropriate data types, as defined by the schema

        Args:
            object_data: a dictionary of object property values, keyed by the property name

        Returns:
            a dictionary of object property values, set by data type per the schema

        """
        returned_properties = {}
        for property_name, entry_property in self._entry_properties_schema.items():
            try:
                test_property = object_data[property_name]
            except KeyError:
                returned_properties[property_name] = MissingObjectProperty()
                continue
            data_type = type_map[entry_property.property_data_type]
            test_property = set_property_data_type(data_type, test_property)
            returned_properties[property_name] = test_property
        return returned_properties

    def _convert_object_properties(self, internal_id: str, object_properties: Dict[str, Any]):
        """ turns the standardized object property into the object specific to how it will be stored
        objects stored directly to the graph transform to LocalPropertyValue, sensitive values are
        obfuscated and turned to SensitivePropertyValue, and values too big to be conveniently stored
        on the graph are stored per the schema and replaced with StoredPropertyValue
        Args:
            internal_id:
            object_properties:

        Returns:
            a dictionary of purpose specific object properties

        """
        converted_properties = {}
        for property_name, entry_property in self._entry_properties_schema.items():
            object_property = object_properties[property_name]
            property_type, property_value = mission.build_vertex_property(
                property_name, object_property, entry_property, internal_id)
            if property_type == 'missing':
                continue
            if property_type not in converted_properties:
                converted_properties[property_type] = []
            converted_properties[property_type].append(property_value)
        return converted_properties

    def _create_internal_id(self, object_properties: Dict[str, Any], for_known: bool = False):
        """ generate the internal_id for an object

        Args:
            object_properties:
            for_known:

        Returns:

        """
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
        """ generate the identifier stem for an object per the schema

        Args:
            object_properties:
            object_data:

        Returns:

        """
        try:
            paired_identifiers = []

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
                paired_identifiers.append(key_value)
            identifier_stem = IdentifierStem('vertex', object_type, paired_identifiers)
            return {
                'data_type': 'S',
                'property_value': str(identifier_stem),
                'property_name': 'identifier_stem'
            }
        except KeyError:
            return self._schema_entry.identifier_stem

    def _create_id_value(self, object_properties: Dict[str, Any]):
        """ extract and standardize the id_value property per the schema

        Args:
            object_properties:

        Returns:

        """
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
