import pytest
import rapidjson

from toll_booth import handler


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('integration_environment')
class TestTasks:
    @pytest.mark.leech_i
    def test_leech_i(self, leech_integration_event, mock_context, mocks):
        results = handler(leech_integration_event, mock_context)
        assert results

    @pytest.mark.tasks_generate_source_vertex_i
    def test_generate_source_vertex_i(self, source_vertex_task_integration_event, mock_context, mocks):
        results = handler(source_vertex_task_integration_event, mock_context)
        assert results

    @pytest.mark.tasks_generate_potential_connections_i
    def test_generate_potential_connections_i(self, potential_connections_integration_event, mock_context, mocks):
        results = handler(potential_connections_integration_event, mock_context)
        parsed_results = rapidjson.loads(results)
        assert results

    @pytest.mark.tasks_check_for_existing_vertexes_i
    def test_check_for_existing_vertexes_i(self, find_existing_vertexes, mock_context, mocks):
        results = handler(find_existing_vertexes, mock_context)
        assert results

    @pytest.mark.tasks_generate_potential_edge_i
    def test_tasks_generate_potential_edge_i(self, generate_edge_integration_event, mock_context, mocks):
        results = handler(generate_edge_integration_event, mock_context)
        assert results
