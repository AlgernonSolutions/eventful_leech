import logging
import os
import rapidjson
from multiprocessing.dummy import Pool as ThreadPool
from typing import Dict, List

import boto3
from algernon.serializers import ExplosionJson
from aws_xray_sdk.core import xray_recorder
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from toll_booth.obj.data_objects.graph_objects import VertexData
from toll_booth.obj.index.indexes import UniqueIndex
from toll_booth.obj.index.troubles import MissingIndexedPropertyException, UniqueIndexViolationException


def _generate_gql_property(property_name, record_entry):
    property_value = {
        '__typename': record_entry['__typename']
    }
    for property_name, property_entry in record_entry.items():
        if property_name == '__typename':
            continue
        property_value[property_name] = property_entry
    return {
        '__typename': 'ObjectProperty',
        'property_name': property_name,
        'property_value': property_value
    }


def _generate_gql_vertex(dynamo_record):
    excluded_entries = (
        'object_class', 'sid_value',
        'internal_id', 'object_type', 'numeric_id_value')
    vertex_dict = ExplosionJson.loads(rapidjson.dumps(dynamo_record))
    potential_vertex = {
        '__typename': 'Vertex',
        'internal_id': vertex_dict['internal_id'],
        'vertex_type': vertex_dict['object_type'],
        'vertex_properties': [],
        'object_type': vertex_dict['object_type']
    }
    for property_name, vertex_property in vertex_dict.items():
        if property_name in excluded_entries:
            continue
        if property_name == 'id_value':
            potential_vertex[property_name] = _generate_gql_property(property_name, vertex_property)
            continue
        if property_name == 'identifier':
            potential_vertex[property_name] = _generate_gql_property(property_name, {
                'data_type': 'S', '__typename': 'LocalPropertyValue', 'property_value': vertex_property
            })
            continue
        potential_vertex['vertex_properties'].append(_generate_gql_property(property_name, vertex_property))
    return VertexData.from_gql(potential_vertex)


class IndexManager:
    """Reads and writes values to the index

        the index manager interacts with the DynamoDB table to add and read indexed entries
    """
    def __init__(self, table_name: str = None):
        """

        Args:
            table_name:
        """
        if table_name is None:
            table_name = os.environ['INDEX_TABLE_NAME']
        object_index = UniqueIndex.for_object_index()
        internal_id_index = UniqueIndex.for_internal_id_index()
        identifier_stem_index = UniqueIndex.for_identifier_index()
        indexes = [object_index, internal_id_index, identifier_stem_index]
        self._table_name = table_name
        self._object_index = object_index
        self._internal_id_index = internal_id_index
        self._identifier_stem_index = identifier_stem_index
        session = boto3.session.Session()
        self._table = session.resource('dynamodb').Table(self._table_name)
        self._indexes = indexes

    @xray_recorder.capture()
    def index_object(self, scalar_object, is_edge=False):
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
        return self._index_object(scalar_object)

    #@xray_recorder.capture()
    def find_potential_vertexes(self,
                                object_type: str,
                                vertex_properties) -> [Dict]:
        """checks the index for objects that match on the given object type and vertex properties

        Args:
            object_type: the type of the object
            vertex_properties: a list containing the properties to check for in the index

        Returns:
            a list of all the potential vertexes that were found in the index

        """
        potential_vertexes = []
        num_scanners = range(os.getenv('num_index_scanners', 10))
        scanner_args = [
            {'object_type': object_type,
             'vertex_properties': vertex_properties,
             'segment': x,
             'total_segments': len(num_scanners)} for x in num_scanners]
        scan_pool = ThreadPool(len(num_scanners))
        scan_results = scan_pool.map(self._scan_vertexes, scanner_args)
        scan_pool.close()
        scan_pool.join()
        logging.info('completed a scan of the data space to find potential vertexes with properties: %s '
                     'returned the raw values of: %s' % (vertex_properties, potential_vertexes))
        for entry in scan_results:
            for vertex_data in entry:
                potential_vertex = _generate_gql_vertex(vertex_data)
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

    def _index_object(self, scalar_object):
        """Adds an object to the index per the schema

        Args:
            scalar_object:

        Returns: None

        Raises:
            UniqueIndexViolationException: The object to be graphed is already in the index

        """
        try:
            scalar_object.update({
                'from_internal_id': scalar_object.source_vertex_internal_id,
                'to_internal_id': scalar_object.target_vertex_internal_id,
                'object_class': 'Edge'
            })
        except AttributeError:
            scalar_object['object_class'] = 'Vertex'
        index_kwargs = {
            'Item': scalar_object,
            'ReturnValues': 'ALL_OLD',
            'ReturnConsumedCapacity': 'INDEXES',
            'ReturnItemCollectionMetrics': 'SIZE'

        }
        condition_expressions = set()
        unique_index_names = []
        for index in self._indexes:
            if index.is_unique:
                condition_expressions.update(index.conditional_statement)
                unique_index_names.append(index.index_name)
        if condition_expressions:
            index_kwargs['ConditionExpression'] = ' AND '.join(condition_expressions)
        self._push_to_index(index_kwargs, unique_index_names, scalar_object)
        return scalar_object

    def _push_to_index(self, index_kwargs, unique_index_names, scalar_object):
        try:
            results = self._table.put_item(**index_kwargs)
            return results
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise e
            raise UniqueIndexViolationException(', '.join(unique_index_names), scalar_object)

    def _scan_vertexes(self, scan_args: Dict) -> List[Dict]:
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
        found_vertexes = []
        object_type, vertex_properties = scan_args['object_type'], scan_args['vertex_properties']
        segment, total_segments = scan_args['segment'], scan_args['total_segments']
        paginator = boto3.client('dynamodb').get_paginator('scan')
        filter_properties = [f'(object_type = :ot OR begins_with(identifier, :stub))']
        expression_names = {}
        expression_values = {
            ':ot': {'S': f'{object_type}'},
            ':stub': {'S': '#vertex#stub#'},
        }
        if 'local_properties' in vertex_properties:
            vertex_properties = vertex_properties['local_properties']
        for pointer, vertex_property in enumerate(vertex_properties):
            filter_properties.append(f'#{pointer} = :property{pointer}')
            expression_names[f'#{pointer}'] = vertex_property['property_name']
            expression_values[f':property{pointer}'] = {
                'M': {
                    '__typename': {'S': 'LocalPropertyValue'},
                    'data_type': {'S': vertex_property['data_type']},
                    'property_value': {'S': vertex_property['property_value']}
                }
            }
        scan_kwargs = {
            'TableName': self._table_name,
            'FilterExpression': ' AND '.join(filter_properties),
            'ExpressionAttributeNames': expression_names,
            'ExpressionAttributeValues': expression_values,
            'Segment': segment,
            'TotalSegments': total_segments
        }
        iterator = paginator.paginate(**scan_kwargs)
        for entry in iterator:
            found_vertexes.extend(entry.get('Items', []))
        return found_vertexes
