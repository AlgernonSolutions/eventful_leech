from unittest.mock import patch, MagicMock

import pytest
from algernon import ajson

from toll_booth import handler


@pytest.mark.tasks
@pytest.mark.usefixtures('unit_environment')
class TestTasks:
    @pytest.mark.mark_push
    def test_mark_push_complete(self, mark_push_event, mock_context):
        with patch('toll_booth.tasks.mark_push.boto3.resource') as mock_dynamo:
            mock_resource = MagicMock()
            mock_table = MagicMock()
            mock_resource.Table = mock_table
            mock_dynamo.return_value = mock_resource
            event = {'task_name': 'mark_push_complete', 'task_kwargs': mark_push_event}
            results = handler(event, mock_context)
            assert results is None
            assert mock_table.update_item.called

    @pytest.mark.tasks_generate_source_vertex
    def test_generate_source_vertex(self, source_vertex_task_integration_event, mock_context, mocks):
        results = handler(source_vertex_task_integration_event, mock_context)
        assert results
        parsed_results = ajson.loads(results)
        expected_keys = ['source_vertex', 'schema', 'schema_entry', 'extracted_data']
        for key_value in expected_keys:
            assert key_value in parsed_results
        generated_vertex_data = parsed_results['source_vertex']
        assert generated_vertex_data.vertex_properties
        assert mocks['bullhorn'].called
        assert mocks['gql'].called

    @pytest.mark.tasks_generate_potential_connections
    def test_generate_potential_connections(self, potential_connections_unit_event, mock_context, mocks):
        results = handler(potential_connections_unit_event, mock_context)
        assert results
        assert mocks['bullhorn'].called

    @pytest.mark.tasks_check_for_existing_vertexes
    def test_check_for_existing_vertexes(self, find_existing_vertexes, mock_context, mocks):
        results = handler(find_existing_vertexes, mock_context)
        assert results
        assert mocks['bullhorn'].called

    @pytest.mark.tasks_generate_potential_edge
    def test_generate_potential_edge(self, generate_edge_integration_event, mock_context):
        results = handler(generate_edge_integration_event, mock_context)
        assert results
