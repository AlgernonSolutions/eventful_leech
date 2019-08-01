import os
from collections import deque
from queue import Queue
from threading import Thread

import boto3
import rapidjson
from algernon.aws import lambda_logged
from algernon.serializers import ExplosionJson
from algernon import ajson

from toll_booth.obj.progress_tracking import MigrationProgress


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


class Auditor:
    def __init__(self, table_name, identifier, num_checkers=5):
        self._table_name = table_name
        self._identifier = identifier
        self._num_checkers = num_checkers
        self._id_queue = Queue()
        self._results = deque()
        self._getters = []
        self._checkers = []

    def work(self):
        self._start_migration_pull()
        self._start_checkers()
        for worker in self._getters:
            worker.join()
        _shutdown(self._id_queue, self._checkers)
        return [x for x in self._results]

    def _start_migration_pull(self):
        worker = Thread(target=self._pull_migration)
        worker.start()
        self._getters.append(worker)

    def _start_checkers(self):
        for _ in range(self._num_checkers):
            worker = Thread(target=self._check_migration)
            worker.start()
            self._checkers.append(worker)

    def _pull_migration(self):
        session = boto3.session.Session()
        client = session.client('dynamodb')
        paginator = client.get_paginator('query')
        response_iterator = paginator.paginate(
            TableName=self._table_name,
            KeyConditionExpression='#i=:i',
            ExpressionAttributeNames={'#i': 'identifier'},
            ExpressionAttributeValues={':i': {'S': self._identifier}}
        )
        for page in response_iterator:
            items = ExplosionJson.loads(rapidjson.dumps(page['Items']))
            for entry in items:
                migration_progress = MigrationProgress.from_dynamo_entry(entry)
                self._id_queue.put(migration_progress)

    def _check_migration(self):
        while True:
            migration_status = self._id_queue.get()
            if migration_status is None:
                return
            if not migration_status.has_completed_step('leech'):
                self._results.append(migration_status)
            self._id_queue.task_done()


@lambda_logged
def audit_handler(event, context):
    table_name = os.environ['MIGRATION_TABLE_NAME']
    identifier = event['identifier']
    auditor = Auditor(table_name, identifier)
    results = auditor.work()
    return ajson.dumps(results)
