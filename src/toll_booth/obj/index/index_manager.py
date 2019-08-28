import os
from typing import Dict

import rapidjson
from algernon.serializers import ExplosionJson
from aws_xray_sdk.core import xray_recorder
from boto3.dynamodb.conditions import Key
from elasticsearch import ConflictError

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.index import mission
from toll_booth.obj.index.elastic_driver import ElasticDriver
from toll_booth.obj.index.indexes import UniqueIndex
from toll_booth.obj.index.troubles import MissingIndexedPropertyException, UniqueIndexViolationException
from toll_booth.obj.schemata.schema import Schema


class IndexManager:
    """Reads and writes values to the index

        the index manager interacts with the DynamoDB table to add and read indexed entries
    """
    def __init__(self, elastic_host: str = None):
        """

        Args:
            elastic_host:
        """
        if elastic_host is None:
            elastic_host = os.environ['ELASTIC_HOST']
        object_index = UniqueIndex.for_object_index()
        internal_id_index = UniqueIndex.for_internal_id_index()
        identifier_stem_index = UniqueIndex.for_identifier_index()
        indexes = [object_index, internal_id_index, identifier_stem_index]
        self._elastic_host = elastic_host
        self._object_index = object_index
        self._internal_id_index = internal_id_index
        self._identifier_stem_index = identifier_stem_index
        self._elastic_driver = ElasticDriver.generate(elastic_host)
        self._indexes = indexes

    # @xray_recorder.capture()
    def index_object(self, scalar_object, is_edge):
        """

        Args:
            scalar_object:
            is_edge:

        Returns: nothing

        Raises:
            AttemptedStubIndexException: The object being indexed is missing key identifying information
            MissingIndexedPropertyException: The object was complete, but it does not have one or more properties
                specified by the index

        """
        for index in self._indexes:
            if index.check_object_type(scalar_object['object_type']):
                missing_properties = index.check_for_missing_object_properties(scalar_object)
                if missing_properties:
                    raise MissingIndexedPropertyException(index.index_name, index.indexed_fields, missing_properties)
        return self._index_object(scalar_object, is_edge)

    #@xray_recorder.capture()
    def find_potential_vertexes(self,
                                object_type: str,
                                vertex_properties,
                                schema: Schema) -> [Dict]:
        """checks the index for objects that match on the given object type and vertex properties

        Args:
            object_type: the type of the object
            vertex_properties: a list containing the properties to check for in the index
            schema:

        Returns:
            a list of all the potential vertexes that were found in the index

        """
        potential_vertexes = []
        search_results = self._search_vertexes(object_type, vertex_properties)
        for entry in search_results.get('hits', []):
            source_data = entry['_source']
            potential_vertex = mission.rebuild_vertex(source_data, schema)
            potential_vertexes.append(potential_vertex)
        return potential_vertexes

    def get_object_key(self, internal_id: str):
        response = self._table.query(
            IndexName=self._internal_id_index.index_name,
            KeyConditionExpression=Key('internal_id').eq(internal_id)
        )
        if response['Count'] > 1:
            raise RuntimeError(f'internal_id value: {internal_id} has some how been indexed multiple times, '
                               f'big problem: {response["Items"]}')
        for entry in response['Items']:
            return {'identifier_stem': entry['identifier_stem'], 'sid_value': entry['sid_value']}

    @xray_recorder.capture()
    def delete_object(self, internal_id: str):
        existing_object_key = self.get_object_key(internal_id)
        if existing_object_key:
            self._table.delete_item(Key=existing_object_key)

    def _index_object(self, scalar_object, is_edge):
        """Adds an object to the index per the schema

        Args:
            scalar_object:

        Returns: None

        Raises:
            UniqueIndexViolationException: The object to be graphed is already in the index

        """
        self._push_to_index(scalar_object, is_edge)
        return scalar_object

    def _push_to_index(self, scalar_object, is_edge):
        index_name = scalar_object['object_type'].lower()
        if is_edge:
            index_name = 'edge' + index_name
        document_id = scalar_object['internal_id']
        try:
            results = self._elastic_driver.index_document(index_name, '_doc', document_id, scalar_object)
            return results
        except ConflictError as e:
            if e.info['status'] != 409:
                raise e
            raise UniqueIndexViolationException('InternalIdIndex', scalar_object)

    def _search_vertexes(self, object_type, vertex_properties) -> Dict:
        """conducts a single paginated scan of the index space

        Args:
            scan_args: a dict keyed
                object_type: the type of the object being scanned for
                vertex_properties: a list containing the vertex properties to check for
                segment: the assigned segment for the scanner
                total_segments: the total number of scanners running

        Returns:
            a list of the items found in the index for the assigned segment
        """
        index_name = object_type.lower()
        filter_body = []
        if 'local_properties' in vertex_properties:
            vertex_properties = vertex_properties['local_properties']
        for vertex_property in vertex_properties:
            property_value = vertex_property['property_value']
            property_name = vertex_property['property_name']
            data_type = vertex_property['data_type']
            filter_entry = {
                "term": {property_name: mission.set_data_type(data_type, property_value, True)}
            }
            filter_body.append(filter_entry)
        response = self._elastic_driver.search(index_name, {'bool': {'filter': filter_body}})
        hit_response = response['hits']
        return hit_response
