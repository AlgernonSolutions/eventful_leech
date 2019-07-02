import logging
import os
from typing import List, Dict

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.gql.gql_client import GqlClient
from toll_booth.obj.schemata import SchemaVertexEntry
from toll_booth.obj.schemata.rules import VertexLinkRuleEntry
from toll_booth.obj.schemata.schema import Schema
from toll_booth.tasks.announcer import announce_generate_potential_edge


def _find_existing_vertexes(potential_vertex: VertexData) -> List[VertexData]:
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    return gql_client.check_for_existing_vertexes(potential_vertex)


@xray_recorder.capture()
def check_for_existing_vertexes(schema: Schema,
                                schema_entry: SchemaVertexEntry,
                                source_vertex: VertexData,
                                potential_vertex: VertexData,
                                rule_entry: VertexLinkRuleEntry,
                                extracted_data: Dict, **kwargs) -> List[Dict]:
    """check to see if vertex specified by potential_vertex and rule_entry exists

    Args:
        schema:
        schema_entry:
        source_vertex:
        potential_vertex:
        rule_entry:
        extracted_data:
        **kwargs:

    Returns:

    """
    results = []
    edge_schema_entry = schema[rule_entry.edge_type]
    if potential_vertex.is_schema_complete(schema[potential_vertex.object_type]):
        logging.info(f'potential_vertex: {potential_vertex} is fully ready to graph')
        announce_generate_potential_edge(source_vertex, potential_vertex, rule_entry, edge_schema_entry, extracted_data)
        return [{
            'source_vertex': source_vertex,
            'identified_vertex': potential_vertex,
            'rule_entry': rule_entry,
            'schema_entry': edge_schema_entry,
            'extracted_data': extracted_data
        }]
    found_vertexes = _find_existing_vertexes(potential_vertex)
    if found_vertexes:
        for identified_vertex in found_vertexes:
            logging.info(f'found an existing vertex which matches: {potential_vertex}, send it to graph')
            announce_generate_potential_edge(
                source_vertex, identified_vertex, rule_entry, edge_schema_entry, extracted_data)
            results.append({
                'source_vertex': source_vertex,
                'identified_vertex': identified_vertex,
                'rule_entry': rule_entry,
                'schema_entry': edge_schema_entry,
                'extracted_data': extracted_data
            })
        return results
    if rule_entry.is_stub:
        logging.info(f'potential_vertex: {potential_vertex} is a stub, send it to graph')
        announce_generate_potential_edge(source_vertex, potential_vertex, rule_entry, edge_schema_entry, extracted_data)
        return [{
            'source_vertex': source_vertex,
            'identified_vertex': potential_vertex,
            'rule_entry': rule_entry,
            'schema_entry': edge_schema_entry,
            'extracted_data': extracted_data
        }]
    if rule_entry.is_create:
        raise RuntimeError(f'could not satisfy rule for {rule_entry.edge_type}, unable to create vertex from data')
    return []
