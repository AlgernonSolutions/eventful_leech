import logging
import os
from typing import Dict, Any, Union

from algernon.aws import Bullhorn
from algernon import ajson

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.schemata import SchemaVertexEntry, SchemaEdgeEntry
from toll_booth.obj.schemata.rules import VertexLinkRuleEntry
from toll_booth.obj.schemata.schema import Schema


def _send_message(task_name: str, task_kwargs: Dict[str, Any]) -> str:
    bullhorn = Bullhorn.retrieve(profile=os.getenv('AWS_PROFILE'))
    listener_arn = bullhorn.find_task_arn(task_name)
    msg = {
        'task_name': task_name,
        'task_kwargs': task_kwargs
    }
    msg_body = ajson.dumps(msg)
    results = bullhorn.publish('new_event', listener_arn, msg_body)
    logging.info(f'published message: {msg_body}, publication_results: {results}')
    return results


def announce_generate_source_vertex(schema: Schema,
                                    schema_entry: SchemaVertexEntry,
                                    extracted_data: Dict[str, Any]) -> str:
    message = {
        'task_name': 'generate_source_vertex',
        'task_kwargs': {
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data,

        }
    }
    return _send_message(**message)


def announce_check_for_existing_vertexes(schema: Schema,
                                         source_vertex: VertexData,
                                         vertex: VertexData,
                                         rule_entry: VertexLinkRuleEntry,
                                         schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry],
                                         extracted_data: Dict[str, Any]) -> str:
    message = {
        'task_name': 'check_for_existing_vertexes',
        'task_kwargs': {
            'schema': schema,
            'source_vertex': source_vertex,
            'potential_vertex': vertex,
            'rule_entry': rule_entry,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data,

        }
    }
    return _send_message(**message)


def announce_derive_potential_connections(source_vertex: VertexData,
                                          schema: Schema,
                                          schema_entry: Union[SchemaVertexEntry, SchemaEdgeEntry],
                                          extracted_data: Dict[str, Any]) -> str:
    message = {
        'task_name': 'derive_potential_connections',
        'task_kwargs': {
            'source_vertex': source_vertex,
            'schema': schema,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }
    }
    return _send_message(**message)


def announce_generate_potential_edge(source_vertex: VertexData,
                                     identifier_vertex: VertexData,
                                     rule_entry: VertexLinkRuleEntry,
                                     schema_entry: SchemaEdgeEntry,
                                     extracted_data: Dict[str, Any]) -> str:
    message = {
        'task_name': 'generate_potential_edge',
        'task_kwargs': {
            'source_vertex': source_vertex,
            'identified_vertex': identifier_vertex,
            'rule_entry': rule_entry,
            'schema_entry': schema_entry,
            'extracted_data': extracted_data
        }
    }
    return _send_message(**message)
