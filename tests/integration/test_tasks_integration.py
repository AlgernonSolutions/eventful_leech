import os

import pytest

from toll_booth.tasks import leech


@pytest.mark.tasks_integration
@pytest.mark.usefixtures('dev_s3_stored_data', 'mock_bullhorn_boto', 'integration_environment')
class TestTasks:
    def test_generate_source_vertex(self, source_vertex_task_integration_event, mock_context):
        os.environ['LEECH_LISTENER_ARN'] = 'some_arn'
        os.environ['ENCOUNTER_BUCKET'] = 'algernonsolutions-gentlemen-dev'
        os.environ['GRAPH_GQL_ENDPOINT'] = 'yiawofjaffgrvlzyg2f6xnjzty.appsync-api.us-east-1.amazonaws.com'
        results = leech.task(source_vertex_task_integration_event, mock_context)
        assert results
