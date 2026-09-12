from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
import os

def create_es():
    HOST = os.environ.get('PROD_ES_HOST')
    REGION = os.environ.get('AWS_REGION', 'ap-south-1')
    SERVICE = 'es'

    # Keep SAM/unit-test imports offline unless a connected test explicitly
    # supplies the production OpenSearch host.
    if not HOST:
        print('PROD_ES_HOST is not set - es will be None')
        return None

    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key, 
        credentials.secret_key,
        REGION, 
        SERVICE, 
        session_token=credentials.token
    )

    ES = Elasticsearch(
        hosts=[{'host': HOST, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=50, max_retries=10, retry_on_timeout=True
    )

    if ES.ping():
        print('Connected to ElasticSearch')
        return ES
    else:
        print('Failed to Connect to Elasticsearch')
    return None

es = create_es()
