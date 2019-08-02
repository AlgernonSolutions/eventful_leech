import datetime
import hashlib
import hmac
import json
import logging
import os
from typing import Dict, Any
import urllib.parse

import rapidjson
import requests
from algernon.aws import Opossum


class TridentNotary:
    _region = os.getenv('AWS_REGION', 'us-east-1')
    _service = 'neptune-db'

    def __init__(self, neptune_endpoint: str, session: requests.session = None):
        if neptune_endpoint is None:
            raise RuntimeError('must specify neptune endpoint when calling the trident_notary')
        if not session:
            session = requests.session()
        self._session = session
        self._neptune_endpoint = neptune_endpoint
        self._uri = '/gremlin/'
        self._method = 'POST'
        self._host = neptune_endpoint + ':8182'
        self._signed_headers = 'host;x-amz-date'
        self._algorithm = 'AWS4-HMAC-SHA256'
        access_key = os.getenv('AWS_ACCESS_KEY_ID', None)
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', None)
        self._session_token = os.getenv('AWS_SESSION_TOKEN', None)
        if access_key is None or secret_key is None:
            access_key, secret_key = Opossum.get_trident_user_key()
        self._access_key = access_key
        self._secret_key = secret_key
        self._credentials = f"Credentials={self._access_key}"
        self._request_url = f'https://{neptune_endpoint}:8182{self._uri}'

    @classmethod
    def get_for_writer(cls, **kwargs):
        endpoint = kwargs.get('graph_db_endpoint', os.getenv('GRAPH_DB_ENDPOINT', None))
        return cls(endpoint)

    @classmethod
    def get_for_reader(cls, **kwargs):
        endpoint = kwargs.get('graph_db_reader_endpoint', os.getenv('GRAPH_DB_READER_ENDPOINT', None))
        return cls(endpoint)

    def send(self, command: str) -> Dict[str, Any]:
        t = datetime.datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')
        canonical_request, request_parameters = self._generate_canonical_request(amz_date, command)
        credential_scope = self._generate_scope(date_stamp)
        string_to_sign = self._generate_string_to_sign(canonical_request, amz_date, credential_scope)
        signature = self._generate_signature(string_to_sign, date_stamp)
        headers = self._generate_headers(credential_scope, signature, amz_date)
        logging.debug(f'sending a command to the remote database: {command}')
        get_results = self._session.post(self._request_url, headers=headers, data=request_parameters)
        if get_results.status_code != 200:
            raise RuntimeError(f'error passing command to remote database: {get_results.text}, command: {command}')
        response_json = rapidjson.loads(get_results.text)
        results = response_json['result']['data']
        logging.debug(f'received a response from the graph database: {results}')
        logging.debug(f'after parsing and transforming the response from the graph database, results: {results}')
        return results

    def _generate_canonical_request(self, amz_date, command):
        payload = json.dumps({'gremlin': command})
        canonical_headers = f'host:{self._host}\nx-amz-date:{amz_date}\n'
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        canon_request = f"{self._method}\n{self._uri}\n\n{canonical_headers}\n{self._signed_headers}\n{payload_hash}"
        return canon_request, payload

    def _generate_string_to_sign(self, canonical_request, amz_date, scope):
        hash_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        return f"{self._algorithm}\n{amz_date}\n{scope}\n{hash_request}"

    def _generate_scope(self, date_stamp):
        return f"{date_stamp}/{self._region}/{self._service}/aws4_request"

    def _get_signature_key(self, date_stamp):
        k_date = self._sign(f'AWS4{self._secret_key}'.encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, self._region)
        k_service = self._sign(k_region, self._service)
        k_signing = self._sign(k_service, 'aws4_request')
        return k_signing

    def _generate_signature(self, string_to_sign, date_stamp):
        signing_key = self._get_signature_key(date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        return signature

    def _generate_headers(self, credential_scope, signature, amz_date):
        credentials_entry = f'Credential={self._access_key}/{credential_scope}'
        headers_entry = f'SignedHeaders={self._signed_headers}'
        signature_entry = f'Signature={signature}'
        authorization_header = f"{self._algorithm} {credentials_entry}, {headers_entry}, {signature_entry}"
        headers = {'x-amz-date': amz_date, 'Authorization': authorization_header}
        if self._session_token:
            headers['x-amz-security-token'] = self._session_token
        return headers

    @classmethod
    def _generate_request_parameters(cls, command):
        payload = {'gremlin': command}
        request_parameters = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
        payload_hash = hashlib.sha256(''.encode('utf-8')).hexdigest()
        return payload_hash, request_parameters

    @classmethod
    def _sign(cls, key, message):
        return hmac.new(key, message.encode('utf-8'), hashlib.sha256).digest()


class TridentDriver:
    def __init__(self, **kwargs):
        self._read_notary = kwargs.get('read_notary', TridentNotary.get_for_reader(**kwargs))
        self._write_notary = kwargs.get('write_notary', TridentNotary.get_for_writer(**kwargs))
        self._batch_mode = False

    def get(self, internal_id):
        command = "g.V('%s')" % internal_id
        return self.execute(command, True)

    def execute(self, query_text: str, read_only: bool = False):
        if self._batch_mode is True:
            self._batch_commands.append(query_text)
            return
        notary = self._write_notary
        if read_only:
            notary = self._read_notary
        results = notary.send(query_text)
        return results

    def __enter__(self):
        self._batch_commands = []
        self._batch_mode = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type and not exc_val:
            self._batch_mode = False
            if self._batch_commands:
                commands = ';'.join(self._batch_commands)
                self.execute(commands)
            self._batch_commands = []
            return True
        raise (exc_type(exc_val))
