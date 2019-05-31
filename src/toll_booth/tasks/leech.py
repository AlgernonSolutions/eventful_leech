import logging
import os
from decimal import Decimal
from typing import Union, List, Dict, Any

from algernon import ajson
from algernon.aws import lambda_logged, Bullhorn

from toll_booth.obj.data_objects import InternalId, IdentifierStem
from toll_booth.obj.data_objects.graph_objects import VertexData, EdgeData
from toll_booth.obj.gql.gql_client import GqlClient, GqlSearchProperty
from toll_booth.obj.regulators.arbiter import RuleArbiter
from toll_booth.obj.regulators.edge_regulator import EdgeRegulator
from toll_booth.obj.regulators.generic_regulator import ObjectRegulator
from toll_booth.obj.schemata.rules import VertexLinkRuleEntry
from toll_booth.obj.schemata.schema import Schema
from toll_booth.obj.schemata.schema_entry import SchemaEdgeEntry, SchemaVertexEntry


def _rebuild_event(original_event):
    return ajson.loads(ajson.dumps(original_event))


@lambda_logged
def task(event, context):
    logging.info(f'started a call for a borg task, event: {event}, context: {context}')
    event = _rebuild_event(event)
    task_name = event['task_name']
    task_kwargs = event.get('task_kwargs', {})
    if task_kwargs is None:
        task_kwargs = {}
    task_function = getattr(LeechTasks, f'_{task_name}')
    results = task_function(**task_kwargs, flow_id=event['flow_id'])
    logging.info(f'completed a call for borg task, event: {event}, results: {results}')
    return ajson.dumps(results)


def _find_existing_vertexes(object_type: str, vertex_properties: List[Dict[str, Any]]) -> List[VertexData]:
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    gql_properties = [GqlSearchProperty(**x) for x in vertex_properties]
    return gql_client.check_for_existing_vertexes(object_type, gql_properties)


def _graph_vertex(vertex_data: VertexData):
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    return gql_client.graph_vertex(vertex_data)


def _graph_cluster(source_vertex: VertexData,
                   identified_vertex: VertexData,
                   potential_edge: EdgeData):
    gql_client = GqlClient(os.environ['GRAPH_GQL_ENDPOINT'])
    return gql_client.graph_cluster(source_vertex, identified_vertex, potential_edge)


class LeechTasks:
    @classmethod
    def _leech(cls,
               flow_id: str,
               object_type: str,
               extracted_data: Dict[str, Any],
               **kwargs) -> Dict[str, Union[str, Any]]:
        """Entry method for this block, formats data and redirects to generate_source_vertex

        Args:
            object_type:
            extracted_data:
            kwargs:
        Returns:

        """
        schema = Schema.retrieve()
        schema_entry = schema[object_type]
        Announcer.announce_generate_source_vertex(flow_id, schema, schema_entry, extracted_data)
        return {
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }

    @classmethod
    def _generate_source_vertex(cls,
                                flow_id: str,
                                schema: Schema,
                                schema_entry: SchemaVertexEntry,
                                extracted_data: Dict[str, Any],
                                internal_id: InternalId = None,
                                identifier_stem: IdentifierStem = None,
                                id_value: Union[str, int, float, Decimal] = None, **kwargs) -> Dict[str, Any]:
        """Generates a source vertex from data extracted from a remote source per a schema entry

        Args:
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
        _graph_vertex(vertex_data)
        Announcer.announce_derive_potential_connections(flow_id, vertex_data, schema, schema_entry, extracted_data)
        return {
            'source_vertex': vertex_data,
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }

    @classmethod
    def _derive_potential_connections(cls,
                                      flow_id: str,
                                      schema: Schema,
                                      schema_entry: SchemaVertexEntry,
                                      source_vertex: VertexData,
                                      extracted_data: Dict,
                                      **kwargs) -> List[Dict[str, Union[VertexData, VertexLinkRuleEntry]]]:
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
            Announcer.announce_check_for_existing_vertexes(
                flow_id, schema, source_vertex, vertex, rule_entry, schema_entry, extracted_data)
            results.append({
                'schema': schema,
                'source_vertex': source_vertex,
                'potential_vertex': vertex,
                'rule_entry': rule_entry,
                'schema_entry': schema_entry,
                'extracted_data': extracted_data,

            })
        return results

    @classmethod
    def _check_for_existing_vertexes(cls,
                                     flow_id: str,
                                     schema: Schema,
                                     schema_entry: SchemaVertexEntry,
                                     source_vertex: VertexData,
                                     potential_vertex: VertexData,
                                     rule_entry: VertexLinkRuleEntry,
                                     extracted_data: Dict, **kwargs) -> List[Dict]:
        """check to see if vertex specified by potential_vertex and rule_entry exists

        Args:
            rule_entry: the vertex_link_rule that specified the potential connection
            potential_vertex: the potential vertex that is being checked against the index

        Returns:
            a tuple containing a list of vertexes to connect the source_vertex to

        """
        results = []
        edge_schema_entry = schema[rule_entry.edge_type]
        if potential_vertex.is_schema_complete(schema_entry):
            Announcer.announce_generate_potential_edge(
                flow_id, source_vertex, potential_vertex, rule_entry, edge_schema_entry, extracted_data)
            return [{
                'source_vertex': source_vertex,
                'identified_vertex': potential_vertex,
                'rule_entry': rule_entry,
                'schema_entry': edge_schema_entry,
                'extracted_data': extracted_data
            }]
        found_vertexes = _find_existing_vertexes(potential_vertex.object_type, potential_vertex.local_properties)
        if found_vertexes:
            for identified_vertex in found_vertexes:
                Announcer.announce_generate_potential_edge(
                    flow_id, source_vertex, identified_vertex, rule_entry, edge_schema_entry, extracted_data)
                results.append({
                    'source_vertex': source_vertex,
                    'identified_vertex': identified_vertex,
                    'rule_entry': rule_entry,
                    'schema_entry': edge_schema_entry,
                    'extracted_data': extracted_data
                })
            return results
        if rule_entry.is_stub:
            Announcer.announce_generate_potential_edge(
                flow_id, source_vertex, potential_vertex, rule_entry, edge_schema_entry, extracted_data)
            return [{
                'source_vertex': source_vertex,
                'identified_vertex': potential_vertex,
                'rule_entry': rule_entry,
                'schema_entry': edge_schema_entry,
                'extracted_data': extracted_data
            }]
        return []

    @classmethod
    def _generate_potential_edge(cls,
                                 schema_entry: SchemaEdgeEntry,
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


class Announcer:
    @classmethod
    def _send_message(cls, message: Dict[str, Any]) -> None:
        bullhorn = Bullhorn()
        topic_arn = os.environ['LISTENER_ARN']
        bullhorn.publish('new_event', topic_arn, ajson.dumps(message))

    @classmethod
    def announce_generate_source_vertex(cls,
                                        flow_id: str,
                                        schema: Schema,
                                        schema_entry: SchemaVertexEntry,
                                        extracted_data: Dict[str, Any]) -> None:
        message = {
            'task_name': 'generate_source_vertex',
            'flow_id': f'{flow_id}#generate_source_vertex',
            'task_kwargs': {
                'schema': schema,
                'schema_entry': schema_entry,
                'extracted_data': extracted_data,

            }
        }
        cls._send_message(message)

    @classmethod
    def announce_check_for_existing_vertexes(cls,
                                             flow_id: str,
                                             schema: Schema,
                                             source_vertex: VertexData,
                                             vertex: VertexData,
                                             rule_entry: VertexLinkRuleEntry,
                                             schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry],
                                             extracted_data: Dict[str, Any]) -> None:
        message = {
            'task_name': 'check_for_existing_vertexes',
            'flow_id': f'{flow_id}#check_for_existing_vertexes-{source_vertex}-{rule_entry}',
            'task_kwargs': {
                'schema': schema,
                'source_vertex': source_vertex,
                'potential_vertex': vertex,
                'rule_entry': rule_entry,
                'schema_entry': schema_entry,
                'extracted_data': extracted_data,

            }
        }
        cls._send_message(message)

    @classmethod
    def announce_derive_potential_connections(cls,
                                              flow_id: str,
                                              source_vertex: VertexData,
                                              schema: Schema,
                                              schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry],
                                              extracted_data: Dict[str, Any]) -> None:
        message = {
            'task_name': 'derive_potential_connections',
            'flow_id': f'{flow_id}#derive_potential_connections',
            'task_kwargs': {
                'source_vertex': source_vertex,
                'schema': schema,
                'schema_entry': schema_entry,
                'extracted_data': extracted_data
            }
        }
        cls._send_message(message)

    @classmethod
    def announce_generate_potential_edge(cls,
                                         flow_id: str,
                                         source_vertex: VertexData,
                                         identifier_vertex: VertexData,
                                         rule_entry: VertexLinkRuleEntry,
                                         schema_entry: SchemaEdgeEntry,
                                         extracted_data: Dict[str, Any]) -> None:
        message = {
            'task_name': 'generate_potential_edge',
            'flow_id': f'{flow_id}#generate_potential_edge-{source_vertex}-{identifier_vertex}',
            'task_kwargs': {
                'source_vertex': source_vertex,
                'identified_vertex': identifier_vertex,
                'rule_entry': rule_entry,
                'schema_entry': schema_entry,
                'extracted_data': extracted_data
            }
        }
        cls._send_message(message)
