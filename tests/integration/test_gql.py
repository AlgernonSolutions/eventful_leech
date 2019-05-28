import pytest

from toll_booth.obj.gql.gql_client import GqlSearchProperty, GqlClient


@pytest.mark.gql_integration
@pytest.mark.usefixtures('integration_environment')
class TestGql:
    def test_query_for_existing_vertexes(self, integration_gql_url):
        gql_client = GqlClient(integration_gql_url)
        object_type = 'MockVertex'
        object_properties = [
            GqlSearchProperty('id_source', 'S', 'Algernon')
        ]
        results = gql_client.check_for_existing_vertexes(object_type, object_properties)
        assert results
