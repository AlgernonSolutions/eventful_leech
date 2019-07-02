import os
from typing import Dict

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.data_objects.graph_objects import VertexData, EdgeData
from toll_booth.obj.gql.gql_client import GqlClient
from toll_booth.obj.regulators import EdgeRegulator
from toll_booth.obj.schemata import SchemaEdgeEntry
from toll_booth.obj.schemata.rules import VertexLinkRuleEntry


def _graph_cluster(source_vertex: VertexData,
                   identified_vertex: VertexData,
                   potential_edge: EdgeData):
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    return gql_client.graph_cluster(source_vertex, identified_vertex, potential_edge)


@xray_recorder.capture()
def generate_potential_edge(schema_entry: SchemaEdgeEntry,
                            source_vertex: VertexData,
                            identified_vertex: VertexData,
                            rule_entry: VertexLinkRuleEntry,
                            extracted_data: Dict, **kwargs) -> EdgeData:
    """Generate a PotentialEdge object between a known source object and a potential vertex

    Args:
        schema_entry: the SchemaEntry which specifies how the data should be integrated
        source_vertex: the PotentialVertex generated from the extracted data
        identified_vertex: the vertex present in the data space to attach the source_vertex to
        rule_entry: the rule used to generate the expected link
        extracted_data: the data extracted from the remote source

    Returns:
        a PotentialEdge object for the potential connection between the source vertex and the potential other
    """
    edge_regulator = EdgeRegulator(schema_entry)
    inbound = rule_entry.inbound
    edge_data = edge_regulator.generate_potential_edge_data(
        source_vertex, identified_vertex, extracted_data, inbound)
    _graph_cluster(source_vertex, identified_vertex, edge_data)
    return edge_data
