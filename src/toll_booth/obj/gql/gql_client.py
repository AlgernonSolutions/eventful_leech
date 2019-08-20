from typing import Dict, List, Any

import rapidjson
from algernon import ajson
from algernon.aws.gql import GqlDriver

from toll_booth.obj.data_objects.graph_objects import VertexData, EdgeData
from toll_booth.obj.gql import gql_queries
from toll_booth.obj.gql.gql_serializers import GqlDecoder


def _generate_vertex_data(existing_vertexes: List[Dict]) -> List[VertexData]:
    generated_vertexes = []
    vertexes = rapidjson.loads(rapidjson.dumps(existing_vertexes), object_hook=GqlDecoder.object_hook)
    for entry in vertexes:
        existing_vertex = VertexData.from_gql(entry)
        generated_vertexes.append(existing_vertex)
    return generated_vertexes


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
        self._connection = GqlDriver(api_endpoint)

    def check_for_existing_vertexes(self, potential_vertex: VertexData) -> List[VertexData]:
        object_type = potential_vertex.object_type
        vertex_properties = [GqlSearchProperty(**x) for x in potential_vertex.local_properties]
        if potential_vertex.is_identifier_set:
            identifier_stem = potential_vertex.identifier
            existing_vertexes = self.list_vertexes(identifier_stem, object_type, vertex_properties)
            return _generate_vertex_data(existing_vertexes)
        existing_vertexes = self.find_vertexes(object_type, vertex_properties)
        return _generate_vertex_data(existing_vertexes)

    def list_vertexes(self,
                      identifier_stem: str,
                      object_type: str,
                      vertex_properties: List[GqlSearchProperty]) -> List[Dict]:
        existing_vertexes = []
        query = gql_queries.LIST_EXISTING_VERTEXES
        variables = {
            'identifier_stem': identifier_stem,
            'object_type': object_type,
            'object_properties': [x.as_gql_variable for x in vertex_properties]
        }
        search_name = 'list_vertexes'
        found_vertexes, token = self._paginate_vertex_command(search_name, query, variables)
        existing_vertexes.extend(found_vertexes)
        while token:
            found_vertexes, token = self._paginate_vertex_command(search_name, query, variables, token)
            existing_vertexes.extend(found_vertexes)
        return existing_vertexes

    def find_vertexes(self, object_type: str, vertex_properties: List[GqlSearchProperty]) -> List[Dict]:
        existing_vertexes = []
        query = gql_queries.SEARCH_FOR_EXISTING_VERTEXES
        search_name = 'find_vertexes'
        variables = {'object_type': object_type, 'object_properties': [x.as_gql_variable for x in vertex_properties]}
        found_vertexes, token = self._paginate_vertex_command(search_name, query, variables)
        existing_vertexes.extend(found_vertexes)
        while token:
            found_vertexes, token = self._paginate_vertex_command(search_name, query, variables, token)
            existing_vertexes.extend(found_vertexes)
        return existing_vertexes

    def _paginate_vertex_command(self, search_name, query, variables, token=None):
        if token:
            variables['token'] = token
        query_results = self._send_command(query, variables)
        if query_results is None:
            return [], None
        vertex_data = query_results[search_name]
        return vertex_data['vertexes'], vertex_data.get('token')

    def graph_vertex(self, vertex_data: VertexData):
        variables = {'input_vertex': vertex_data.for_gql}
        command = gql_queries.GRAPH_VERTEX
        results = self._send_command(command, variables)
        return results

    def graph_cluster(self,
                      source_vertex: VertexData,
                      identified_vertex: VertexData,
                      potential_edge: EdgeData):
        query = gql_queries.GRAPH_CLUSTER
        variables = {
            'source_vertex': source_vertex.for_gql,
            'target_vertex': identified_vertex.for_gql,
            'potential_edge': potential_edge.for_gql
        }
        results = self._send_command(query, variables)
        return results

    def _send_command(self, command: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        if not variables:
            variables = {}
        command_results = self._connection.send(command, variables)
        parsed_results = ajson.loads(command_results)
        return parsed_results['data']
