import traceback
import sys
import os

# Add parent directory to Python path for Lambda compatibility
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from common.es import es
    from common_stg.es_stg import es_stg
except ImportError as e:
    print(f"[Alphavantage] Error importing common.es: {e}")
    # Try relative import as fallback
    try:
        from ..common.es import es
        from ..common_stg.es_stg import es_stg
    except ImportError as e2:
        print(f"[Alphavantage] Error with relative import: {e2}")
        raise ImportError(f"Cannot import common.es module: {e}, {e2}")

class Alphavantage:
    def __init__(self, ticker, es_env="prod"):
        self.ticker = ticker
        self.es_env = es_env
        # Select ES client based on environment
        self.es_client = es_stg if es_env == "staging" else es

    def _build_query(self, start_date=None, end_date=None, size=0, sort_order=None):
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "Stock": self.ticker
                            }
                        }
                    ]
                }
            }
        }
        if start_date or end_date:
            query["query"]["bool"]["must"].append({
                "range": {
                    "Timestamp": {
                        "gte": start_date if start_date else "now-100y",
                        "lte": end_date if end_date else "now"
                    }
                }
            })
        if sort_order:
            query["sort"] = [{"Timestamp": {"order": sort_order}}]
        if size:
            query["size"] = size
        return query

    def calculate_average_closing_price(self, start_date, end_date):
        try:
            query = self._build_query(start_date=start_date, end_date=end_date)
            query["aggs"] = {
                "avg_closing_price": {
                    "avg": {
                        "field": "Close"
                    }
                }
            }
            response = self.es_client.search(index="alphavantage", body=query)
            if response and 'aggregations' in response:
                return response['aggregations']['avg_closing_price']['value']
        except Exception:
            traceback.print_exc()
        return None

    def get_market_closing_price(self, date):
        try:
            query = self._build_query(end_date=date, size=1, sort_order="desc")
            response = self.es_client.search(index="alphavantage", body=query)
            if response and 'hits' in response and response['hits']['hits']:
                last_record = response['hits']['hits'][0]['_source']
                return last_record['Close']
        except Exception:
            traceback.print_exc()
        return None
