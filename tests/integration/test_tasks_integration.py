import os
from unittest.mock import patch

import pytest

from toll_booth import handler
from toll_booth.tasks import leech, graph_handler, index_handler, s3_handler


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('integration_environment')
class TestTasks:
    @pytest.mark.handler
    def test_handler(self, push_event, mock_context):
        event = {'task_name': 'push_graph', 'task_kwargs': push_event}
        results = handler(event, mock_context)
        assert results

    @pytest.mark.aio
    def test_aio(self, aio_event):
        results = leech(**aio_event)
        assert results

    @pytest.mark.push_graph
    def test_graph_push(self, push_event):
        os.environ['GRAPH_DB_ENDPOINT'] = 'some_endpoint'
        os.environ['GRAPH_DB_READER_ENDPOINT'] = 'some_endpoint'
        for entry in push_event:
            results = graph_handler(**entry)
            assert results

    @pytest.mark.push_index
    def test_index_push(self, push_event):
        os.environ['INDEX_TABLE_NAME'] = 'Indexes'
        for entry in push_event:
            results = index_handler(**entry)
            assert results

    @pytest.mark.push_s3
    def test_s3_push(self, push_event):
        with patch('toll_booth.tasks.push_s3._check_for_object') as mock_check:
            mock_check.return_value = False
            os.environ['INDEX_TABLE_NAME'] = 'Indexes'
            push_kwargs = {
                'bucket_name': 'algernonsolutions-leech-dev',
                'base_file_key': 'bulk'
            }
            for entry in push_event:
                entry.update(push_kwargs)
                results = s3_handler(**entry)
                assert results
