import os
from _pydecimal import Decimal
from typing import Dict, Any, Union

from aws_xray_sdk.core import xray_recorder

from toll_booth.obj.data_objects import InternalId, IdentifierStem
from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.gql.gql_client import GqlClient
from toll_booth.obj.regulators import ObjectRegulator
from toll_booth.obj.schemata import SchemaVertexEntry
from toll_booth.obj.schemata.schema import Schema
from toll_booth.tasks.announcer import announce_derive_potential_connections


def _graph_vertex(vertex_data: VertexData):
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    return gql_client.graph_vertex(vertex_data)


# @xray_recorder.capture()
def generate_source_vertex(schema: Schema,
                           schema_entry: SchemaVertexEntry,
                           extracted_data: Dict[str, Any],
                           internal_id: InternalId = None,
                           identifier_stem: IdentifierStem = None,
                           id_value: Union[str, int, float, Decimal] = None, **kwargs) -> Dict[str, Any]:
    """Generates a source vertex from data extracted from a remote source per a schema entry

    Args:
        schema:
        schema_entry: the SchemaEntry which specifies the integration of the data into the graph
        extracted_data: the data extracted from the
        internal_id: if the internal_id has been previously calculated, we can bypass it's creation
        identifier_stem: if the identifier_stem has been previously created, we can include it here
        id_value: if the id_value is already known, we can skip deriving it

    Returns:
        a PotentialVertex object which represents the data organized and parsed per the SchemaEntry
    """
    regulator = ObjectRegulator(schema_entry)
    object_data = extracted_data['source']
    vertex_data = regulator.create_potential_vertex_data(object_data, internal_id, identifier_stem, id_value)
    if not vertex_data.is_schema_complete(schema_entry):
        raise RuntimeError(f'could not completely construct a source vertex from: {extracted_data}')
    # _graph_vertex(vertex_data)
    # announce_derive_potential_connections(vertex_data, schema, schema_entry, extracted_data)
    return {
        'source_vertex': vertex_data,
        'schema': schema,
        'schema_entry': schema_entry,
        'extracted_data': extracted_data
    }
