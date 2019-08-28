import os

from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3


class ElasticDriver:
    def __init__(self, es_host, aws_auth):
        self._es_host = es_host
        self._aws_auth = aws_auth

    @classmethod
    def generate(cls, es_host):
        credentials = boto3.Session().get_credentials()
        auth_args = {
            'access_key': credentials.access_key,
            'secret_key': credentials.secret_key,
            'region': os.environ.get('AWS_REGION', 'us-east-1'),
            'service': 'es'
        }
        if credentials.token:
            auth_args['session_token'] = credentials.token
        aws_auth = AWS4Auth(**auth_args)
        return cls(es_host, aws_auth)

    @property
    def es_client(self):
        return Elasticsearch(
            hosts=[{'host': self._es_host, 'port': 443}],
            http_auth=self._aws_auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )

    def index_document(self, index_name, document_type, document_id, document):
        return self.es_client.create(index=index_name, doc_type=document_type, id=document_id, body=document)

    def get_document(self, index_name, document_type, document_id):
        return self.es_client.get(index=index_name, doc_type=document_type, id=document_id)

    def search(self, index_name, query_body):
        return self.es_client.search(index_name, body={'query': query_body})
