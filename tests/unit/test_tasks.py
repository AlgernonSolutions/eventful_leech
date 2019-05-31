import pytest

from toll_booth.tasks.leech import task
from algernon import ajson


@pytest.mark.tasks
@pytest.mark.usefixtures('unit_environment')
class TestTasks:
    @pytest.mark.tasks_generate_source_vertex
    def test_generate_source_vertex(self, source_vertex_task_integration_event, mock_context, mocks):
        results = task(source_vertex_task_integration_event, mock_context)
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
    def test_generate_potential_connections(self, potential_connections_integration_event, mock_context, mocks):
        results = task(potential_connections_integration_event, mock_context)
        assert results
        assert mocks['bullhorn'].called

    @pytest.mark.tasks_generate_potential_edge
    def test_generate_potential_edge(self, generate_edge_integration_event, mock_context):
        results = task(generate_edge_integration_event, mock_context)
        assert results
