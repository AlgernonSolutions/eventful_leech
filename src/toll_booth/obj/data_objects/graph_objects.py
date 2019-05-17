from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Union

from algernon import AlgObject, ajson

from toll_booth.obj.data_objects.identifiers import IdentifierStem
from toll_booth.obj.schemata.schema_entry import SchemaVertexEntry


class GraphObjectProperty(AlgObject):
    def __init__(self, property_name: str, property_value: str, data_type: str):
        self._property_name = property_name
        self._property_value = property_value
        self._data_type = data_type

    @classmethod
    def parse_json(cls, json_dict: Dict[str, Any]):
        return cls(json_dict['property_name'], json_dict['property_value'], json_dict['data_type'])

    @property
    def property_name(self) -> str:
        return self._property_name

    @property
    def property_value(self) -> str:
        return self._property_value

    @property
    def data_type(self) -> str:
        type_map = {'Number': 'N', 'String': 'S', 'DateTime': 'DT', 'Boolean': 'B'}
        if self._data_type in type_map:
            return self._data_type
        return type_map[self._data_type]


class SensitiveObjectProperty(GraphObjectProperty):
    def __init__(self,
                 property_name: str,
                 property_value: str,
                 source_internal_id: str,
                 data_type: str):
        super().__init__(property_name, property_value, data_type)
        self._source_internal_id = source_internal_id

    @property
    def source_internal_id(self):
        return self._source_internal_id


class StoredObjectProperty(GraphObjectProperty):
    def __init__(self,
                 property_name: str,
                 data_type: str,
                 storage_uri: str,
                 storage_class: str):
        super().__init__(property_name, storage_uri, data_type)
        self._storage_class = storage_class

    @property
    def storage_class(self):
        return self._storage_class


class GraphObject(AlgObject):
    def __init__(self,
                 object_type: str,
                 object_properties: Dict[str, Union[str, Decimal, datetime]],
                 internal_id: str,
                 identifier_stem: IdentifierStem,
                 id_value: str):
        self._object_type = object_type
        self._object_properties = object_properties
        self._internal_id = internal_id
        self._identifier_stem = identifier_stem
        self._id_value = id_value
        self._graph_as_stub = False

    @classmethod
    def parse_json(cls, json_dict: Dict[str, Any]):
        return cls(
            json_dict['object_type'], json_dict['object_properties'], json_dict['internal_id'],
            json_dict['identifier_stem'], json_dict['id_value']
        )

    @property
    def object_type(self) -> str:
        return self._object_type

    @property
    def object_properties(self) -> Dict[str, Union[str, Decimal, datetime]]:
        return self._object_properties

    @property
    def internal_id(self) -> str:
        return self._internal_id

    @property
    def identifier_stem(self) -> IdentifierStem:
        return self._identifier_stem

    @property
    def id_value(self) -> str:
        return self._id_value

    @property
    def graph_as_stub(self) -> bool:
        return self._graph_as_stub

    @property
    def for_index(self) -> Dict[str, Any]:
        indexed_value = {
            'sid_value': str(self._id_value),
            'identifier_stem': str(self._identifier_stem),
            'internal_id': str(self._internal_id),
            'id_value': self._id_value,
            'object_type': self._object_type,
            'object_value': ajson.dumps(self),
            'object_properties': self._object_properties
        }
        if isinstance(self._id_value, int) or isinstance(self._id_value, Decimal):
            indexed_value['numeric_id_value'] = self._id_value
        for property_name, property_value in self._object_properties.items():
            indexed_value[property_name] = property_value
        return indexed_value

    @property
    def for_stub_index(self) -> str:
        return ajson.dumps(self)

    @property
    def is_edge(self) -> bool:
        return '#edge#' in str(self._identifier_stem)

    def is_identifiable(self, schema_entry: SchemaVertexEntry) -> bool:
        try:
            identifier_stem = IdentifierStem.from_raw(self._identifier_stem)
        except AttributeError:
            return False
        if not self.is_internal_id_set:
            return False
        if not isinstance(identifier_stem, IdentifierStem):
            return False
        if not self.is_id_value_set(schema_entry):
            return False
        return True

    @property
    def is_identifier_stem_set(self) -> bool:
        try:
            IdentifierStem.from_raw(self._identifier_stem)
            return True
        except AttributeError:
            return False

    @property
    def is_properties_complete(self) -> bool:
        for property_name, object_property in self._object_properties.items():
            if hasattr(object_property, 'is_missing'):
                return False
        return True

    def is_id_value_set(self, schema_entry: SchemaVertexEntry) -> bool:
        return self._id_value != schema_entry.id_value_field

    @property
    def is_internal_id_set(self) -> bool:
        return isinstance(self._internal_id, str)

    def __getitem__(self, item) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            return self._object_properties[item]


class PotentialVertex(GraphObject):
    def __init__(self,
                 object_type: str,
                 internal_id: str,
                 object_properties: Dict[str, Union[str, Decimal, datetime]],
                 identifier_stem: IdentifierStem,
                 id_value: str):
        super().__init__(object_type, object_properties, internal_id, identifier_stem, id_value)

    @classmethod
    def parse_json(cls, json_dict):
        return cls(
            json_dict['object_type'], json_dict.get('internal_id'),
            json_dict.get('object_properties', {}), json_dict['identifier_stem'],
            json_dict.get('id_value')
        )

    @property
    def graphed_object_type(self):
        return self._identifier_stem.object_type

    def __str__(self):
        return f'{self._object_type}-{self.id_value}'


class PotentialEdge(GraphObject):
    def __init__(self,
                 object_type: str,
                 internal_id: str,
                 object_properties: Dict[str, Union[str, Decimal, datetime]],
                 from_object: str,
                 to_object: str):
        identifier_stem = IdentifierStem.from_raw(f'#edge#{object_type}#')
        id_value = internal_id
        super().__init__(object_type, object_properties, internal_id, identifier_stem, id_value)
        self._from_object = from_object
        self._to_object = to_object

    @classmethod
    def parse_json(cls, json_dict: Dict[str, Any]):
        return cls(
            json_dict['object_type'], json_dict['internal_id'],
            json_dict['object_properties'], json_dict['from_object'], json_dict['to_object']
        )

    @property
    def edge_label(self) -> str:
        return self._object_type

    @property
    def graphed_object_type(self) -> str:
        return self.edge_label

    @property
    def edge_properties(self) -> Dict[str, Union[str, Decimal, datetime]]:
        return self._object_properties

    @property
    def from_object(self) -> str:
        return self._from_object

    @property
    def to_object(self) -> str:
        return self._to_object
