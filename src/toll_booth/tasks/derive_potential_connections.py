from typing import Dict

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.regulators.arbiter import RuleArbiter
from toll_booth.obj.schemata import SchemaVertexEntry
from toll_booth.obj.schemata.schema import Schema


@xray_recorder.capture()
def derive_potential_connections(schema: Schema,
                                 schema_entry: SchemaVertexEntry,
                                 source_vertex: VertexData,
                                 extracted_data: Dict,
                                 **kwargs):
    """Generate a list of PotentialVertex objects indicated by the schema_entry

    Args:
        schema: the entire schema object that governs the data space
        schema_entry: the isolated entry for the source_vertex extracted from the remote space
        source_vertex: the PotentialVertex generated for the extracted object
        extracted_data: all the data extracted from the remote system

    Returns:

    """
    arbiter = RuleArbiter(source_vertex, schema, schema_entry)
    potential_vertexes = arbiter.process_rules(extracted_data)
    results = []
    for vertex_entry in potential_vertexes:
        vertex = vertex_entry[0]
        rule_entry = vertex_entry[1]
        results.append({
            'schema': schema,
            'source_vertex': source_vertex,
            'potential_vertex': vertex,
            'rule_entry': rule_entry,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data,

        })
    return results
