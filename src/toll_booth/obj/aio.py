import logging
from collections import deque
from copy import deepcopy
from queue import Queue
from threading import Thread

import boto3

from toll_booth.obj.index.index_manager import IndexManager
from toll_booth.obj.progress_tracking import Overseer
from toll_booth.obj.regulators import ObjectRegulator, EdgeRegulator
from toll_booth.obj.regulators.arbiter import RuleArbiter
from toll_booth.obj.schemata.schema import Schema


def _shutdown(queue, workers):
    for _ in workers:
        queue.put(None)
    for worker in workers:
        worker.join()


def _startup(target_fn, num_workers):
    workers = []
    for _ in range(num_workers):
        worker = Thread(target=target_fn)
        worker.start()
        workers.append(worker)
    return workers


def _lookup_resource(resource_name):
    client = boto3.client('ssm')
    response = client.get_parameter(
        Name=resource_name
    )
    parameter = response['Parameter']
    return parameter['Value']


class AioMaster:
    def __init__(self,
                 identifier: str,
                 id_value: int,
                 source_object_type: str,
                 extracted_data,
                 schema: Schema,
                 num_potential_workers: int,
                 num_identified_workers: int,
                 progress_table_name: str):
        self._schema = schema
        self._num_potential_workers = num_potential_workers
        self._num_identified_workers = num_identified_workers
        self._potential_queue = Queue()
        self._identified_queue = Queue()
        self._results = deque()
        self._source_vertex = None
        self._source_vertex_schema_entry = schema[source_object_type]
        self._extracted_data = extracted_data
        self._source_object_type = source_object_type
        self._overseer = Overseer(progress_table_name, identifier, id_value)

    def work(self):
        potential_workers = _startup(self._check_for_existing_vertexes, self._num_potential_workers)
        identified_workers = _startup(self._generate_potential_edge, self._num_identified_workers)
        self._generate_source_vertex()
        self._derive_potential_connections()
        self._potential_queue.join()
        self._identified_queue.join()
        _shutdown(self._potential_queue, potential_workers)
        _shutdown(self._identified_queue, identified_workers)
        results = [x for x in self._results]
        self._overseer.mark_stage_completed('leech', [{a: b.for_gql for a, b in x.items()} for x in results])
        return results

    def _generate_source_vertex(self):
        schema_entry = self._source_vertex_schema_entry
        regulator = ObjectRegulator(schema_entry)
        object_data = self._extracted_data['source']
        vertex_data = regulator.create_potential_vertex_data(object_data)
        if not vertex_data.is_schema_complete(schema_entry):
            raise RuntimeError(f'could not completely construct a source vertex from: {self._extracted_data}')
        self._source_vertex = vertex_data
        self._overseer.mark_stage_completed('generate_source_vertex', vertex_data.for_gql)

    def _derive_potential_connections(self):
        schema_entry = self._source_vertex_schema_entry
        arbiter = RuleArbiter(self._source_vertex, self._schema, schema_entry)
        potential_vertexes = arbiter.process_rules(self._extracted_data)
        stage_results = [{'potential_vertex': x[0].for_gql, 'rule_name': str(x[1])} for x in potential_vertexes]
        self._overseer.mark_stage_completed('derive_potential_connections', stage_results)
        for vertex_entry in potential_vertexes:
            vertex = vertex_entry[0]
            rule_entry = vertex_entry[1]
            self._potential_queue.put({'potential_vertex': vertex, 'rule_entry': rule_entry})

    def _check_for_existing_vertexes(self):
        index_manager = IndexManager()
        while True:
            potential_vertex_data = self._potential_queue.get()
            if potential_vertex_data is None:
                return
            potential_vertex = potential_vertex_data['potential_vertex']
            rule_entry = potential_vertex_data['rule_entry']
            results = self.__check_for_existing_vertexes(potential_vertex, rule_entry, index_manager)
            stage_name = f'check_for_existing_vertexes_{potential_vertex.internal_id}_{rule_entry.edge_type}'
            stage_results = {'status': results['status'], 'existing_vertexes': [x.for_gql for x in results['vertexes']]}
            self._overseer.mark_stage_completed(stage_name, stage_results)
            self._potential_queue.task_done()

    def __check_for_existing_vertexes(self, potential_vertex, rule_entry, index_manager: IndexManager):
        edge_type = rule_entry.edge_type
        edge_schema_entry = self._schema[edge_type]
        identified_kwargs = {
            'rule_entry': rule_entry,
            'edge_schema': edge_schema_entry
        }
        if potential_vertex.is_schema_complete(self._schema[potential_vertex.object_type]):
            logging.info(f'potential_vertex: {potential_vertex} is fully ready to graph')
            identified_kwargs['identified_vertex'] = potential_vertex
            self._identified_queue.put(identified_kwargs)
            return {'vertexes': [potential_vertex], 'status': 'fully_ready_to_graph'}
        found_vertexes = index_manager.find_potential_vertexes(
            potential_vertex.object_type, potential_vertex.vertex_properties, self._schema)
        if found_vertexes:
            results = []
            for identified_vertex in found_vertexes:
                logging.info(f'found an existing vertex which matches: {potential_vertex}, send it to graph')
                identified_kwargs['identified_vertex'] = identified_vertex
                self._identified_queue.put(identified_kwargs)
                results.append(identified_vertex)
            return {'vertexes': results, 'status': 'found_existing_vertexes'}
        if rule_entry.is_create:
            raise RuntimeError(f'could not satisfy rule for {rule_entry.edge_type}, unable to create vertex from data')

    def _generate_potential_edge(self):
        while True:
            identified_vertex_data = self._identified_queue.get()
            if identified_vertex_data is None:
                return
            edge_schema_entry = identified_vertex_data['edge_schema']
            rule_entry = identified_vertex_data['rule_entry']
            identified_vertex = identified_vertex_data['identified_vertex']
            potential_edge = self.__generate_potential_edge(edge_schema_entry, identified_vertex, rule_entry)
            result_package = {
                'source_vertex': deepcopy(self._source_vertex),
                'other_vertex': deepcopy(identified_vertex),
                'edge': potential_edge
            }
            self._results.append(result_package)
            stage_name = f'generate_potential_edge_{identified_vertex.internal_id}_{potential_edge.object_type}'
            self._overseer.mark_stage_completed(stage_name, potential_edge.for_gql)
            self._identified_queue.task_done()

    def __generate_potential_edge(self, edge_schema_entry, identified_vertex, rule_entry):
        edge_regulator = EdgeRegulator(edge_schema_entry)
        inbound = rule_entry.inbound
        edge_kwargs = {
            'source_vertex': self._source_vertex,
            'potential_other': identified_vertex,
            'extracted_data': self._extracted_data,
            'inbound': inbound
        }
        edge_data = edge_regulator.generate_potential_edge_data(**edge_kwargs)
        return edge_data
