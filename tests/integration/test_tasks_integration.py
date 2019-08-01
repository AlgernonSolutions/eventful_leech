import os

import pytest
import rapidjson

from toll_booth import handler, aio_handler, audit_handler


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('integration_environment')
class TestTasks:
    @pytest.mark.audit
    def test_audit(self, mock_context):
        os.environ['MIGRATION_TABLE_NAME'] = 'Migratory'
        event = {
            'identifier': '#ICFS#Encounter#'
        }
        results = audit_handler(event, mock_context)
        assert results

    @pytest.mark.aio
    def test_aio(self, aio_event, mock_context):
        results = aio_handler(aio_event, mock_context)
        assert results

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
