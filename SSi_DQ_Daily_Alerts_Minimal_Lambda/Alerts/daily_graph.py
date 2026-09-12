import json
import math
import traceback
import os
from constants import graph_types
import boto3

client = boto3.client("lambda")
DAILY_GRAPHS_FUNCTION_NAME = os.environ.get("DAILY_GRAPHS_FUNCTION_NAME", "")

class DailyGraphAPI:
    def __init__(self, date, es_env="prod"):
        self.date = date
        self.es_env = es_env

    def get_payload(self, graph_type, date=None, start_date=None, end_date=None):
        payload = {
            "graph_type": graph_type,
            "key": "prod",
            "es_env": self.es_env
        }
        
        if start_date and end_date:
            # Use custom date range for Monday/post-holiday scenarios
            payload["start_date"] = start_date
            payload["end_date"] = end_date
        else:
            # Use standard date parameter
            payload["date"] = date or self.date
            
        return payload

    def call_api_for_graph_type(self, graph_type, date=None, start_date=None, end_date=None):
        """Call DailyGraphs Lambda for a specific graph type with comprehensive error handling."""
        try:
            payload = self.get_payload(graph_type, date, start_date, end_date)
            formatted_payload = {"body": json.dumps(payload)}
            
            print(f"Calling DailyGraphs Lambda for graph_type={graph_type}, es_env={self.es_env}")
            print(f"Payload: {json.dumps(payload)}")
            
            if not DAILY_GRAPHS_FUNCTION_NAME:
                raise RuntimeError(
                    "DAILY_GRAPHS_FUNCTION_NAME is required for connected integration tests"
                )

            response = client.invoke(
                FunctionName=DAILY_GRAPHS_FUNCTION_NAME,
                InvocationType="RequestResponse",
                Payload=json.dumps(formatted_payload),
            )
            
            # Check for Lambda function errors
            if 'FunctionError' in response:
                print(f"Lambda function error for {graph_type}: {response.get('FunctionError')}")
                return None
                
        except client.exceptions.ClientError as e:
            print(f"AWS ClientError for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"Unexpected error during Lambda invocation for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None

        try:
            # Read and decode the response payload
            payload_bytes = response['Payload'].read()
            response_str = payload_bytes.decode("utf-8")
            print(f"[DEBUG] Raw response string for {graph_type}: {response_str[:1000]}")  # First 1000 chars
            
            response_payload = json.loads(response_str)
            print(f"[DEBUG] Parsed response_payload type: {type(response_payload)}, keys: {list(response_payload.keys()) if isinstance(response_payload, dict) else 'N/A'}")
            print(f"[DEBUG] Full response_payload for {graph_type}: {json.dumps(response_payload, default=str)[:2000]}")
            
            # Check for error status codes
            status_code = response_payload.get('statusCode', 200)
            print(f"[DEBUG] Status code for {graph_type}: {status_code}")
            
            if status_code != 200:
                error_body = response_payload.get('body', '{}')
                try:
                    error_data = json.loads(error_body) if isinstance(error_body, str) else error_body
                    print(f"DailyGraphs Lambda returned error {status_code} for {graph_type}: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"DailyGraphs Lambda returned error {status_code} for {graph_type}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None
        except KeyError as e:
            print(f"KeyError reading response payload for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"Unexpected error reading response payload for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None

        try:
            # Parse the response body - handle potential double encoding
            body = response_payload.get('body')
            print(f"[DEBUG] Body type for {graph_type}: {type(body)}")
            print(f"[DEBUG] Body content (first 500 chars) for {graph_type}: {str(body)[:500]}")
            
            if not body:
                print(f"Empty response body for {graph_type}")
                return None
            
            # Parse body - could be string or already parsed object    
            if isinstance(body, str):
                print(f"[DEBUG] Body is string, parsing JSON for {graph_type}")
                response_data = json.loads(body)
            else:
                print(f"[DEBUG] Body is already object (type: {type(body)}), using directly for {graph_type}")
                response_data = body
            
            print(f"[DEBUG] Parsed response_data type: {type(response_data)}, keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'} for {graph_type}")
            print(f"[DEBUG] Full response_data for {graph_type}: {json.dumps(response_data, default=str)[:2000]}")
            
            # Extract data from response
            data = response_data.get("data")
            print(f"[DEBUG] Data from response_data for {graph_type}: type={type(data)}, length={len(data) if isinstance(data, (list, dict)) else 'N/A'}")
            
            if data is None:
                print(f"No data field in response for {graph_type}. Response: {json.dumps(response_data)}")
                return None
                
            if not isinstance(data, list):
                print(f"Unexpected data format for {graph_type}: expected list, got {type(data)}. Data: {json.dumps(data)}")
                return None
            
            if len(data) == 0:
                print(f"[WARNING] Empty data array returned for {graph_type} - no entries in response")
                print(f"[DEBUG] Full response for {graph_type}: {json.dumps(response_data, default=str)}")
            else:
                print(f"✓ Successfully retrieved {len(data)} entries for {graph_type}")
                print(f"[DEBUG] First entry sample for {graph_type}: {json.dumps(data[0], default=str)[:500]}")
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON body for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"Unexpected error processing response data for {graph_type}: {str(e)}")
            traceback.print_exc()
            return None
    
    def get_all_responses(self, start_date=None, end_date=None):
        """
        Get all responses for all graph types with comprehensive error handling.
        If start_date and end_date are provided, use custom date ranges.
        Otherwise, use standard date-based calls.
        Returns a dictionary with all graph types, using empty lists for failures.
        """
        responses = {}
        failed_graph_types = []
        
        print(f"[DEBUG] get_all_responses called with start_date={start_date}, end_date={end_date}")
        
        for graph_type in graph_types:
            try:
                print(f"\n[DEBUG] Processing graph_type: {graph_type}")
                if start_date and end_date:
                    # Use custom date range for Monday/post-holiday scenarios
                    response = self.call_api_for_graph_type(graph_type, start_date=start_date, end_date=end_date)
                else:
                    # Use standard date-based call
                    response = self.call_api_for_graph_type(graph_type, self.date)
                
                print(f"[DEBUG] Response for {graph_type}: type={type(response)}, is_none={response is None}, is_list={isinstance(response, list)}, length={len(response) if isinstance(response, list) else 'N/A'}")
                    
                if response is not None and isinstance(response, list):
                    try:
                        # Replace `nan` values with 0 and handle invalid data
                        cleaned_response = []
                        for entry in response:
                            if isinstance(entry, dict):
                                cleaned_entry = {}
                                for k, v in entry.items():
                                    if isinstance(v, float) and math.isnan(v):
                                        cleaned_entry[k] = 0
                                    elif v is None:
                                        cleaned_entry[k] = 0
                                    else:
                                        cleaned_entry[k] = v
                                cleaned_response.append(cleaned_entry)
                            else:
                                print(f"Warning: Non-dict entry in {graph_type} response: {type(entry)}")
                        
                        responses[graph_type] = cleaned_response
                        print(f"[DEBUG] ✓ {graph_type}: Stored {len(cleaned_response)} cleaned entries")
                        
                        # Log data availability details
                        if len(cleaned_response) == 0:
                            print(f"WARNING: {graph_type} returned empty data - no entries found in ES for this date/environment")
                        else:
                            # Check if entries have actual data (non-zero values)
                            has_data = any(
                                any(v != 0 and v is not None for k, v in entry.items() if k != 'fields')
                                for entry in cleaned_response
                            )
                            if has_data:
                                print(f"✓ Successfully fetched {len(cleaned_response)} entries with data for {graph_type}")
                            else:
                                print(f"WARNING: {graph_type} returned {len(cleaned_response)} entries but all values are zero/null - likely no matching documents in ES")
                                
                    except Exception as e:
                        print(f"Error cleaning response data for {graph_type}: {str(e)}")
                        traceback.print_exc()
                        responses[graph_type] = []
                        failed_graph_types.append(graph_type)
                else:
                    print(f"Failed to fetch valid response for {graph_type}, using empty list. Response: {response}")
                    responses[graph_type] = []
                    failed_graph_types.append(graph_type)
                    
            except Exception as e:
                print(f"Unexpected error processing {graph_type}: {str(e)}")
                traceback.print_exc()
                responses[graph_type] = []
                failed_graph_types.append(graph_type)
        
        # Provide detailed summary
        print(f"\n[SUMMARY] get_all_responses completed")
        print(f"[SUMMARY] Responses dict keys: {list(responses.keys())}")
        for gtype, resp in responses.items():
            print(f"[SUMMARY] {gtype}: {len(resp)} entries")
        
        if failed_graph_types:
            print(f"[SUMMARY] Failed graph types: {failed_graph_types}")
        else:
            print(f"[SUMMARY] Successfully fetched data for all {len(graph_types)} graph types")
        
        # Check if we have any actual data
        total_entries = sum(len(resp) for resp in responses.values())
        print(f"[SUMMARY] Total entries across all graph types: {total_entries}")
        
        has_any_data = any(
            any(v != 0 and v is not None for k, v in entry.items() if k != 'fields')
            for resp in responses.values() if isinstance(resp, list)
            for entry in resp
        )
        
        if total_entries == 0:
            print(f"WARNING: No data entries returned for any graph type. The staging ES indices may be empty for this date range.")
        elif not has_any_data:
            print(f"WARNING: All returned data contains zero/null values. There may be no matching documents in ES for this date/ticker combination in es_env={self.es_env}.")
            
        return responses
