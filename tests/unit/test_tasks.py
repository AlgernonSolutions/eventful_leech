import os

import pytest
import rapidjson

from toll_booth import handler, object_iterator, sfn_leech
from algernon import ajson


@pytest.mark.tasks
@pytest.mark.usefixtures('unit_environment')
class TestTasks:
    @pytest.mark.sfn_leech
    def test_iterator(self, mock_context):
        event = {'Records': [{'messageId': '813cb17f-72b8-4fb9-aab6-153770252ced', 'receiptHandle': 'AQEBVcO4/2se76nRT0GS/EtNTXS8yVVinD2J4eCRdoZJntd0x6f3TfueyEHL80qk2ES0MsgDtD9pTS3sRaQJXpHUhrVUhK4LpEyxA/lIHIkoAiLEb0H5PIyFPiyhpYybnpZIrVUIZg7MPv9jSfqW0KFf6CoRXc8b9Tix8L+PXmknQNEyf2Rs0qdvkCVOXWUi+kasFPhI7CA9OVLuHlitUulzJXf9Mtdss23PE1W2uzK2Z6rsQEOB52HL1SAOP+PQIhm5f4T7gRQWhok8mxDECrycY5IxHI1tjzxdEbC5fCicTJq8/oaAYtLViUUyCDdqpestEAYxAXy2MZeqbf73J5tMPTbNwuVwyKmo9p4tYVV15Ssita6O9M0yeYedTKXxwY0ET6Kfw9KId8A74CnsegzqguaTdP6mNGXItOVu7X6j+sFIDf5tZNwa8r/Kyq1qFs5k', 'body': '{\n "Type" : "Notification",\n "MessageId" : "6ada1fad-e73f-5029-8659-4a0a3ace82a7",\n "TopicArn" : "arn:aws:sns:us-east-1:726075243133:leech-dev-2-Leech-DJW3BI0LO10C-Listener-18KXU9RHWGYVV",\n "Message" : "{\\"extracted_data\\":{\\"_alg_class\\":\\"StoredData\\",\\"_alg_module\\":\\"algernon.aws.snakes\\",\\"value\\":{\\"pointer\\":\\"algernonsolutions-leech-dev#cache/e133ff7a-31c2-40c6-bb18-47d626b884a1!1563286447.834209.json\\"}},\\"identifier\\":\\"#PSI#Encounter#\\",\\"id_source\\":\\"PSI\\",\\"id_value\\":\\"3421784\\"}",\n "Timestamp" : "2019-07-16T14:14:09.221Z",\n "SignatureVersion" : "1",\n "Signature" : "VaDFqxhyaKbNtFB5qUPUtB/i3jophctHz1DpfSH2EYwRV+hm96TozcKRnnyizzBG/zhVpm9YvyUBMhmNSW08r+v7wlIsIoIuax8TMEUSYozBARQwJIdfPQn1HhGcXnxmLND8mv8hAhHkXg8QIf14CcbwXQgro+9MopVVfaoH4OQdRetE0WmIWraVRj865OeJqfaqxGN43s++NvJTBC9rDocuU9amSQlsM+yL2qF6P/KUod9DtQPIkcLeK4iZd7jLwLigSrYHQuBIo1UVc5JcjVtcIfKPC+hCi9V3xs7UrwPRtFgDmoj4D5J4th+YI30e3cZXCDRju53RHS3DFQ7Htw==",\n "SigningCertURL" : "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-6aad65c2f9911b05cd53efda11f913f9.pem",\n "UnsubscribeURL" : "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:726075243133:leech-dev-2-Leech-DJW3BI0LO10C-Listener-18KXU9RHWGYVV:b70b41e6-a59e-4e0c-8e54-4221bd2f51e3"\n}', 'attributes': {'ApproximateReceiveCount': '1', 'SentTimestamp': '1563286449373', 'SenderId': 'AIDAIT2UOQQY3AUEKVGXU', 'ApproximateFirstReceiveTimestamp': '1563286449406'}, 'messageAttributes': {}, 'md5OfBody': 'f0617fa823cc94dc9a3d35989798f733', 'eventSource': 'aws:sqs', 'eventSourceARN': 'arn:aws:sqs:us-east-1:726075243133:leech-dev-2-Leech-DJW3BI0LO10C-Queue-17NCY8J3BXJD2', 'awsRegion': 'us-east-1'}]}
        results = sfn_leech(event, mock_context)
        assert results

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
