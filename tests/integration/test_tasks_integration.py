import os
from unittest.mock import patch

import pytest
from algernon import rebuild_event

from toll_booth import handler
from toll_booth.tasks import leech, push_graph, push_index, push_s3, push_event


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('integration_environment')
class TestTasks:
    @pytest.mark.mark_push_i
    def test_mark_push_complete(self, mark_push_event, mock_context):
        event = {'task_name': 'mark_push_complete', 'task_kwargs': mark_push_event}
        results = handler(event, mock_context)
        assert results

    @pytest.mark.handler
    def test_handler(self, aio_event, mock_context):
        event = {'task_name': 'leech', 'task_kwargs': aio_event}
        results = handler(event, mock_context)
        assert results

    @pytest.mark.aio
    def test_aio(self, aio_event):
        os.environ['INDEX_TABLE_NAME'] = 'Indexes'
        aio_event = rebuild_event(aio_event)
        results = leech(**aio_event)
        assert results

    @pytest.mark.push_graph
    def test_graph_push(self, test_push_event):
        os.environ['GRAPH_DB_ENDPOINT'] = 'some_endpoint'
        os.environ['GRAPH_DB_READER_ENDPOINT'] = 'some_endpoint'
        for entry in test_push_event['leech']:
            results = push_graph(leech=entry)
            assert results

    @pytest.mark.push_index
    def test_index_push(self, test_push_event):
        os.environ['INDEX_TABLE_NAME'] = 'Indexes'
        os.environ['SENSITIVE_TABLE_NAME'] = 'Sensitives'
        os.environ['ELASTIC_HOST'] = 'vpc-algernon-test-ankmhqkcdnx2izwfkwys67wmiq.us-east-1.es.amazonaws.com'
        results = push_index(**test_push_event)
        assert results

    @pytest.mark.push_s3
    def test_s3_push(self, test_push_event):
        with patch('toll_booth.tasks.push_to_s3._check_for_object') as mock_check:
            mock_check.return_value = False
            os.environ['INDEX_TABLE_NAME'] = 'Indexes'
            push_kwargs = {
                'bucket_name': 'algernonsolutions-leech-prod',
                'base_file_key': 'bulk'
            }
            push_kwargs.update(test_push_event)
            results = push_s3(**push_kwargs)
            assert results

    @pytest.mark.push_events
    def test_events_push(self, test_push_event):
        test_push_event = test_push_event['leech']
        for entry in test_push_event:
            results = push_event(leech=entry)
            assert results is None
