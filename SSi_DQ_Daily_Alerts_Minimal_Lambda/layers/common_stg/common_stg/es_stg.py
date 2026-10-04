from elasticsearch import Elasticsearch, RequestsHttpConnection
import os

def create_es():
    HOST = 'vpc-ssi-stg-sog3lhbiblkri6h6mqwun7jjde.ap-south-1.es.amazonaws.com'
    
    # Get credentials from environment variables
    username = os.environ.get('STG_ES_USERNAME')
    password = os.environ.get('STG_ES_PASSWORD')
    
    print(f"Creating Staging ES connection to: {HOST}")
    
    if not username or not password:
        print('STG_ES_USERNAME or STG_ES_PASSWORD environment variables not set - es_stg will be None')
        return None

    try:
        ES = Elasticsearch(
            hosts=[{'host': HOST, 'port': 443}],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=50, max_retries=10, retry_on_timeout=True
        )

        if ES.ping():
            print('Successfully connected to Staging ElasticSearch')
            return ES
        else:
            print('Failed to ping Staging Elasticsearch - but returning client anyway')
            return ES
    except Exception as e:
        print(f'Exception creating Staging ES client: {e}')
        return None

es_stg = create_es()
