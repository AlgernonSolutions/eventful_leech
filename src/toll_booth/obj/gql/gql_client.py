from typing import Dict, List, Any

import rapidjson
from algernon import ajson
from algernon.aws.gql import GqlNotary

from toll_booth.obj.data_objects import PotentialVertex, IdentifierStem
from toll_booth.obj.gql import gql_queries
from toll_booth.obj.gql.gql_serializers import GqlDecoder


class GqlSearchProperty:
    def __init__(self, property_name: str, data_type: str, property_value: str):
        self._property_name = property_name
        self._data_type = data_type
        self._property_value = property_value

    @property
    def property_name(self) -> str:
        return self._property_name

    @property
    def data_type(self) -> str:
        return self._data_type

    @property
    def property_value(self) -> str:
        return self._property_value

    @property
    def as_gql_variable(self) -> Dict[str, str]:
        return {
            'property_name': self._property_name,
            'data_type': self._data_type,
            'property_value': self._property_value
        }


class GqlClient:
    def __init__(self, api_endpoint: str):
        self._api_endpoint = api_endpoint
        self._connection = GqlNotary(api_endpoint)

    def check_for_existing_vertexes(self,
                                    object_type: str,
                                    vertex_properties: List[GqlSearchProperty]) -> List[PotentialVertex]:
        existing_vertexes = []
        query = gql_queries.SEARCH_FOR_EXISTING_VERTEXES
        variables = {'object_type': object_type, 'object_properties': [x.as_gql_variable for x in vertex_properties]}
        query_results = self._send_command(query, variables)
        existing_vertex_data = query_results['find_vertexes']
        vertexes = rapidjson.loads(rapidjson.dumps(existing_vertex_data), object_hook=GqlDecoder.object_hook)
        for entry in vertexes:
            existing_properties = {}
            for property_entry in entry['vertex_properties']:
                existing_properties.update(property_entry)
            identifier_stem = IdentifierStem.from_raw(entry['identifier_stem']['identifier_stem'])
            id_value = entry['id_value']['id_value']
            existing_vertex = PotentialVertex(
                entry['vertex_type'], entry['internal_id'], existing_properties, identifier_stem, id_value)
            existing_vertexes.append(existing_vertex)
        return existing_vertexes

    def graph_vertex(self, internal_id, object_type, id_value, identifier_stem, vertex_properties):
        gql_vertex = {
            'id_value': id_value,
            'identifier_stem': identifier_stem,
            'internal_id': internal_id,
            'vertex_type': object_type,
            'vertex_properties': vertex_properties
        }
        variables = {'input_vertex': gql_vertex}
        command = gql_queries.GRAPH_VERTEX
        return self._send_command(command, variables)

    def graph_cluster(self, source_vertex, identified_vertex, potential_edge):
        query = gql_queries.GRAPH_CLUSTER
        variables = {
            'source_vertex': source_vertex,
            'target_vertex': identified_vertex,
            'potential_edge': potential_edge
        }
        return self._send_command(query, variables)

    def _send_command(self, command: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        if not variables:
            variables = {}
        command_results = self._connection.send(command, variables)
        parsed_results = ajson.loads(command_results)
        return parsed_results['data']
