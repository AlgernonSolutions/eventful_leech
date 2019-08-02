import os
from typing import Union

from toll_booth.obj.data_objects.graph_objects import VertexData, EdgeData


class Index:
    """

    """
    def __init__(self, index_name, indexed_fields, index_type, indexed_object_types):
        self._index_name = index_name
        self._indexed_fields = indexed_fields
        self._index_type = index_type
        self._indexed_object_types = indexed_object_types

    @property
    def index_name(self):
        return self._index_name

    @property
    def indexed_fields(self):
        return self._indexed_fields

    @property
    def index_type(self):
        return self._index_type

    @property
    def indexed_object_types(self):
        return self._indexed_object_types

    @property
    def conditional_statement(self):
        return [f'attribute_not_exists({x})' for x in self._indexed_fields]

    @property
    def is_unique(self):
        return self._index_type == 'unique'

    def check_for_missing_object_properties(self, object_properties) -> Union[list, bool]:
        """

        Args:
            object_properties:

        Returns:

        """
        missing_properties = [x for x in self._indexed_fields if x not in object_properties]
        if missing_properties:
            return missing_properties
        return False

    def check_object_type(self, object_type: str) -> bool:
        if '*' in self._indexed_object_types:
            return True
        if object_type in self._indexed_object_types:
            return True
        return False


class UniqueIndex(Index):
    def __init__(self, index_name, indexed_fields, indexed_object_types):
        super().__init__(index_name, indexed_fields, 'unique', indexed_object_types)

    @classmethod
    def for_object_index(cls,
                         index_name: str = None,
                         partition_key_name: str = None,
                         hash_key_name: str = None):
        """

        Args:
            index_name:
            partition_key_name:
            hash_key_name:

        Returns:

        """
        if not index_name:
            index_name = os.getenv('OBJECT_INDEX_NAME', 'leech_index')
        if not partition_key_name:
            partition_key_name = os.getenv('OBJECT_INDEX_PARTITION_KEY_NAME', 'sid_value')
        if not hash_key_name:
            hash_key_name = os.getenv('OBJECT_INDEX_HASH_KEY_NAME', 'identifier_stem')
        return cls(index_name, [partition_key_name, hash_key_name], ['*'])

    @classmethod
    def for_internal_id_index(cls,
                              index_name: str = None,
                              internal_id_field_name: str = None):
        if not index_name:
            index_name = os.getenv('INTERNAL_ID_INDEX_NAME', 'internal_id_index')
        if not internal_id_field_name:
            internal_id_field_name = os.getenv('OBJECT_INTERNAL_ID_KEY_NAME', 'internal_id')
        return cls(index_name, [internal_id_field_name], ['*'])

    @classmethod
    def for_identifier_stem_index(cls,
                                  index_name: str = None):
        if not index_name:
            index_name = os.getenv('IDENTIFIER_STEM_INDEX_NAME', 'identifier_stem_index')
        return cls(index_name, ['identifier_stem', 'id_value'], ['*'])
