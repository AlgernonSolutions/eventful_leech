from datetime import datetime
from decimal import Decimal
from typing import Dict, Union, List, Tuple

from algernon import AlgObject

from toll_booth.obj.data_objects.identifiers import IdentifierStem
from toll_booth.obj.schemata.schema_entry import SchemaVertexEntry
from toll_booth.obj.utils import set_property_data_type


def _parse_gql_property(gql_property_data: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    property_type = gql_property_data['__typename']
    del(gql_property_data['__typename'])
    if property_type == 'LocalPropertyValue':
        return 'local_properties', gql_property_data
    if property_type == 'SensitivePropertyValue':
        gql_property_data['data_type'] = gql_property_data['sensitive_data_type']
        del(gql_property_data['sensitive_data_type'])
        return 'sensitive_properties', gql_property_data
    if property_type == 'StoredPropertyValue':
        gql_property_data['data_type'] = gql_property_data['stored_data_type']
        del(gql_property_data['stored_data_type'])
        return 'stored_properties', gql_property_data
    return property_type, gql_property_data


class VertexData(AlgObject):
    def __init__(self,
                 object_type: str,
                 internal_id: str,
                 identifier_stem: Dict[str, str],
                 id_value: Dict[str, str],
                 local_properties: List[Dict[str, str]] = None,
                 stored_properties: List[Dict[str, str]] = None,
                 sensitive_properties: List[Dict[str, str]] = None):
        if not local_properties:
            local_properties = []
        if not stored_properties:
            stored_properties = []
        if not sensitive_properties:
            sensitive_properties = []
        self._object_type = object_type
        self._internal_id = internal_id
        self._identifier_stem = identifier_stem
        self._id_value = id_value
        self._local_properties = local_properties
        self._stored_properties = stored_properties
        self._sensitive_properties = sensitive_properties

    @classmethod
    def from_source_data(cls, source_dict):
        object_properties = source_dict['object_properties']
        source_dict['local_properties'] = object_properties.get('local_properties')
        source_dict['stored_properties'] = object_properties.get('stored_properties')
        source_dict['sensitive_properties'] = object_properties.get('sensitive_properties')
        return cls.parse_json(source_dict)

    @classmethod
    def from_gql(cls, gql_dict):
        json_dict = {
            'internal_id': gql_dict['internal_id'],
            'object_type': gql_dict['vertex_type']
        }
        id_value = gql_dict['id_value']
        del(id_value['__typename'])
        json_dict['id_value'] = id_value
        identifier_stem = gql_dict['identifier_stem']
        del(identifier_stem['__typename'])
        json_dict['identifier'] = identifier_stem
        object_properties_data = gql_dict['vertex_properties']
        for entry in object_properties_data:
            property_class, object_property = _parse_gql_property(entry)
            if property_class not in json_dict:
                json_dict[property_class] = []
            json_dict[property_class].append(object_property)
        return cls.parse_json(json_dict)

    @classmethod
    def parse_json(cls, json_dict):
        return cls(
            json_dict['object_type'], json_dict['internal_id'], json_dict['identifier'],
            json_dict['id_value'], json_dict.get('local_properties'),
            json_dict.get('stored_properties'), json_dict.get('sensitive_properties')
        )

    @property
    def local_properties(self):
        return self._local_properties

    @property
    def object_type(self) -> str:
        return self._object_type

    @property
    def internal_id(self) -> str:
        return self._internal_id

    @property
    def id_value(self) -> Union[str, Decimal, datetime]:
        return set_property_data_type(**self._id_value)

    @property
    def identifier_stem(self) -> str:
        return set_property_data_type(**self._identifier_stem)

    @property
    def vertex_properties(self):
        vertex_properties = {}
        if self._local_properties:
            vertex_properties['local_properties'] = self._local_properties
        if self._sensitive_properties:
            vertex_properties['sensitive_properties'] = self._sensitive_properties
        if self._stored_properties:
            vertex_properties['stored_properties'] = self._stored_properties
        return vertex_properties

    @property
    def for_gql(self):
        return {
            'id_value': self._id_value,
            'identifier_stem': self._identifier_stem,
            'internal_id': self.internal_id,
            'vertex_type': self._object_type,
            'vertex_properties': self.vertex_properties
        }

    @property
    def is_identifier_stem_set(self):
        try:
            identifier_stem = IdentifierStem.from_raw(self.identifier_stem)
            if not isinstance(identifier_stem, IdentifierStem):
                return False
            return True
        except AttributeError:
            return False

    def get_vertex_property(self, property_type, property_name) -> Dict[str, str]:
        object_properties = getattr(self, f'_{property_type}')
        for object_property in object_properties:
            if object_property['property_name'] == property_name:
                return object_property
        raise KeyError(property_name)

    def contains_vertex_property(self, property_type, property_name) -> bool:
        object_properties = getattr(self, f'_{property_type}')
        for object_property in object_properties:
            if object_property['property_name'] == property_name:
                return True
        return False

    def __getitem__(self, item):
        if item == 'object_type':
            return self._object_type
        if item == 'internal_id':
            return self._internal_id
        if item == 'id_value':
            return self.id_value
        if item == 'identifier':
            return self.identifier_stem
        return set_property_data_type(**self.get_vertex_property('local_properties', item))

    def is_schema_complete(self, schema_entry: SchemaVertexEntry):
        return self.is_identifiable(schema_entry) and self.is_properties_complete(schema_entry)

    def is_properties_complete(self, schema_entry: SchemaVertexEntry):
        for property_name, property_schema in schema_entry.vertex_properties.items():
            if property_schema.sensitive:
                if not self.contains_vertex_property('sensitive_properties', property_name):
                    return False
                continue
            if property_schema.is_stored:
                if not self.contains_vertex_property('stored_properties', property_name):
                    return False
                continue
            if not self.contains_vertex_property('local_properties', property_name):
                return False
        return True

    def is_identifiable(self, schema_entry: SchemaVertexEntry):
        try:
            identifier_stem = IdentifierStem.from_raw(self.identifier_stem)
        except AttributeError:
            return False
        if not isinstance(self._internal_id, str):
            return False
        if not isinstance(identifier_stem, IdentifierStem):
            return False
        if not self._id_value != schema_entry.id_value_field:
            return False
        return True

    def __str__(self):
        return f'{self._object_type}-{self._internal_id}'


class EdgeData(VertexData):
    def __init__(self,
                 object_type: str,
                 internal_id: str,
                 source_vertex_internal_id: str,
                 target_vertex_internal_id: str,
                 local_properties: List[Dict[str, str]] = None,
                 stored_properties: List[Dict[str, str]] = None,
                 sensitive_properties: List[Dict[str, str]] = None):
        identifier_stem = {
            'data_type': 'S',
            'property_name': 'identifier_stem',
            'property_value': str(IdentifierStem.from_raw(f'#edge#{object_type}#'))
        }
        id_value = {
            'data_type': 'S',
            'property_name': 'id_value',
            'property_value': internal_id
        }
        vertex_kwargs = {
            'object_type': object_type, 'internal_id': internal_id, 'identifier': identifier_stem,
            'id_value': id_value, 'local_properties': local_properties,
            'stored_properties': stored_properties, 'sensitive_properties': sensitive_properties}
        super().__init__(**vertex_kwargs)
        self._source_vertex_internal_id = source_vertex_internal_id
        self._target_vertex_internal_id = target_vertex_internal_id

    @classmethod
    def parse_json(cls, json_dict):
        return cls(
            json_dict['object_type'], json_dict['internal_id'],
            json_dict['source_vertex_internal_id'],
            json_dict['target_vertex_internal_id'],
            json_dict.get('local_properties'),
            json_dict.get('stored_properties'),
            json_dict.get('sensitive_properties')
        )

    @classmethod
    def from_source_data(cls, source_dict):
        edge_properties = source_dict['edge_properties']
        del(source_dict['edge_properties'])
        source_dict['local_properties'] = edge_properties.get('local_properties')
        source_dict['sensitive_properties'] = edge_properties.get('sensitive_properties')
        source_dict['stored_properties'] = edge_properties.get('stored_properties')
        return cls.parse_json(source_dict)

    @classmethod
    def from_gql(cls, gql_dict):
        raise NotImplementedError()

    @property
    def source_vertex_internal_id(self) -> str:
        return self._source_vertex_internal_id

    @property
    def target_vertex_internal_id(self) -> str:
        return self._target_vertex_internal_id

    @property
    def edge_properties(self):
        return self.vertex_properties

    @property
    def for_gql(self):
        return {
            'edge_label': self.object_type,
            'internal_id': self.internal_id,
            'id_value': self._id_value,
            'identifier': self._identifier_stem,
            'source_vertex_internal_id': self._source_vertex_internal_id,
            'target_vertex_internal_id': self._target_vertex_internal_id,
            'edge_properties': self.edge_properties
        }

    def __str__(self):
        return f"{self._source_vertex_internal_id}-{self.object_type}->{self._target_vertex_internal_id}"
