import os

import pytest
import rapidjson

from toll_booth.obj.gql.gql_client import GqlSearchProperty, GqlClient

gql_url = 'yiawofjaffgrvlzyg2f6xnjzty.appsync-api.us-east-1.amazonaws.com'
os.environ['DEBUG'] = 'True'
os.environ['GQL_API_KEY'] = 'da2-zcvdidxqqjelni6jaouejuuusm'
os.environ['SENSITIVE_TABLE'] = 'Sensitives'


@pytest.mark.gql
@pytest.mark.usefixtures('dev_dynamo')
class TestGql:
    def test_client_construction(self):
        gql_client = GqlClient(gql_url)
        assert gql_client

    def test_query_for_existing_vertexes(self):
        gql_client = GqlClient(gql_url)
        object_type = 'MockVertex'
        object_properties = [
            GqlSearchProperty('id_source', 'S', 'Algernon')
        ]
        results = gql_client.check_for_existing_vertexes(object_type, object_properties)
        parsed_results = rapidjson.loads(results)
        assert parsed_results
