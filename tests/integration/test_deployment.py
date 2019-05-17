import boto3
import pytest


@pytest.mark.deployment
class TestDeployment:
    def test_generate_source_vertex(self, source_vertex_task_deployment_event):
        topic_arn = 'arn:aws:sns:us-east-1:726075243133:leech-dev-Listener-1EV4D8VOW7L37'
        client = boto3.Session(profile_name='dev').client('sns')
        response = client.publish(
            TopicArn=topic_arn,
            Message=source_vertex_task_deployment_event,
            Subject='new_event'
        )
        assert response
