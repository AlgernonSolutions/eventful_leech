import os
from typing import List

import boto3
from botocore.exceptions import ClientError


class PushResult:
    def __init__(self, leeched_object, operation_type, operation_results, push_time):
        self._leeched_object = leeched_object
        self._operation_type = operation_type
        self._operation_results = operation_results
        self._push_time = push_time

    @property
    def stage_name(self):
        other_type_name = 'edge_label' if 'edge_label' in self._leeched_object else 'vertex_type'
        return f'{self._leeched_object[other_type_name]}[{self._leeched_object["internal_id"]}]->{self._operation_type}'

    @property
    def stage_results(self):
        return self._operation_results

    @property
    def push_time(self):
        return self._push_time


class PushResults:
    def __init__(self, source_vertex=None, push_results: List[PushResult] = None):
        if not push_results:
            push_results = []
        self._source_vertex = source_vertex
        self._push_results = push_results

    @property
    def source_vertex(self):
        return self._source_vertex

    @property
    def is_source_vertex_set(self):
        return self._source_vertex is not None

    @property
    def key_value(self):
        return {'identifier': self.identifier, 'id_value': self.id_value}

    @property
    def identifier(self):
        return f'#{self.id_source}#{self._source_vertex["vertex_type"]}#'

    @property
    def id_source(self):
        return _extract_object_property(self._source_vertex['vertex_properties'], 'local_properties', 'id_source')

    @property
    def id_value(self):
        return int(self._source_vertex['id_value']['property_value'])

    @property
    def expression_attribute_values(self):
        attribute_values = {}

        def _replace_empty_strings(stage_results):
            for key, value in stage_results.items():
                if value == '':
                    stage_results[key] = None
                if isinstance(value, dict):
                    _replace_empty_strings(value)
            return stage_results

        for pointer, push_result in enumerate(self._push_results):
            attribute_values[f':{pointer}'] = {
                'stage_results': _replace_empty_strings(push_result.stage_results),
                'completed_at': push_result.push_time
            }
        return attribute_values

    @property
    def expression_attribute_names(self):
        attribute_names = {}
        for pointer, push_result in enumerate(self._push_results):
            attribute_names[f'#{pointer}'] = push_result.stage_name
        return attribute_names

    @property
    def update_expression(self):
        pieces = []
        for attribute_name_key in self.expression_attribute_names:
            attribute_value_key = attribute_name_key.replace('#', ':', 1)
            pieces.append(f'{attribute_name_key}={attribute_value_key}')
        return f"SET {','.join(pieces)}"

    @source_vertex.setter
    def source_vertex(self, source_vertex):
        self._source_vertex = source_vertex

    def add_push_result(self, push_result: PushResult):
        self._push_results.append(push_result)


def _extract_object_property(leeched_object_properties, property_type, target_property_name):
    for object_property in leeched_object_properties[property_type]:
        property_name = object_property['property_name']
        if property_name == target_property_name:
            return object_property['property_value']
    raise RuntimeError(f'could not find {target_property_name} in {leeched_object_properties}')


def _push_migration_update(table_resource, push_results: PushResults):
    try:
        table_resource.update_item(
            Key=push_results.key_value,
            UpdateExpression=push_results.update_expression,
            ExpressionAttributeNames=push_results.expression_attribute_names,
            ExpressionAttributeValues=push_results.expression_attribute_values
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise e


def mark_push_complete(push_results, leeched_objects, push_completed_time):
    table = boto3.resource('dynamodb').Table(os.environ['PROGRESS_TABLE_NAME'])
    collected_results = PushResults()
    for operation_results in push_results:
        source_vertex = leeched_objects['source_vertex']
        if not collected_results.is_source_vertex_set:
            collected_results.source_vertex = source_vertex
        for operated_object_name, object_operation in operation_results.items():
            leeched_object = leeched_objects[operated_object_name]
            operation_name = object_operation['operation']
            push_result = PushResult(leeched_object, operation_name, object_operation, push_completed_time)
            collected_results.add_push_result(push_result)
    _push_migration_update(table, collected_results)


