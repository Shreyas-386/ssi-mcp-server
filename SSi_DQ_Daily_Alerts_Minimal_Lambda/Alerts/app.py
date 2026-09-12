import json
import traceback
from daily_graph import DailyGraphAPI
from index import Alerts
from utils import AlertUtils
from datetime import datetime

DEFAULT_ALERT_PARAMS = [
    {
        "sentiment_change": 25,
        "buzz_change": 100,
        "price_change": 2,
        "result": "STRONG_BUY"
    },
    {
        "sentiment_change": 25,
        "buzz_change": 50,
        "price_change": 1,
        "result": "BUY"
    },
    {
        "sentiment_change": -25,
        "buzz_change": 100,
        "price_change": -2,
        "result": "STRONG_SELL"
    },
    {
        "sentiment_change": -25,
        "buzz_change": 50,
        "price_change": -1,
        "result": "SELL"
    }
]

def lambda_handler(event, context):
    try:
        # Parse request body with validation
        try:
            body = json.loads(event["body"])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing request body: {str(e)}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "failed",
                    "error": "Invalid request body format"
                }),
            }
        
        # Extract and validate parameters
        date = body.get("date", None)
        if not date:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "failed",
                    "error": "Missing required parameter: date"
                }),
            }
            
        price_enabled = body.get("price_enabled", False)
        only_faang = body.get("only_faang", False)
        is_dev = body.get("is_dev", True)
        page = body.get("page", 1)
        conditions = body.get("conditions", DEFAULT_ALERT_PARAMS)
        es_env = body.get("es_env", "prod")
        
        print(f"Payload - date: {date}, price_enabled: {price_enabled}, only_faang: {only_faang}, es_env: {es_env}, page: {page}")
        
        # Initialize alert utils for timing logic
        alert_utils = AlertUtils()
        
        # Check if this is a Monday or post-holiday scenario
        # Handle both full datetime format and simple date format
        try:
            # Try parsing as full datetime with timezone
            date_str = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try parsing as simple date format
                date_str = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                # If both fail, assume it's already in the correct format
                date_str = date
        
        is_monday_or_post_holiday = alert_utils.is_monday_or_post_holiday(date_str)
        
        # Get standard daily graph responses for momentum and longterm momentum alerts
        print(f"Fetching standard daily graph responses for es_env={es_env}")
        try:
            daily_graph_api_standard = DailyGraphAPI(date, es_env)
            daily_graph_api_responses_standard = daily_graph_api_standard.get_all_responses()
            
            if not daily_graph_api_responses_standard:
                print("Warning: No standard daily graph responses received")
                
        except Exception as e:
            print(f"Error fetching standard daily graph responses: {str(e)}")
            traceback.print_exc()
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": "failed",
                    "error": f"Failed to fetch daily graph data: {str(e)}"
                }),
            }
        
        # Get custom timing responses for pre-market alerts (daily alerts) if it's Monday/post-holiday
        if is_monday_or_post_holiday:
            # Use custom timing periods for Monday/post-holiday for daily alerts only
            try:
                timing_periods = alert_utils.get_alert_timing_periods(date)
                print(f"Using custom timing for Monday/post-holiday for daily alerts: {timing_periods}")
                
                # Call Daily Graph Lambda with custom date ranges for daily alerts
                daily_graph_api_custom = DailyGraphAPI(date, es_env)
                daily_graph_api_responses_custom = daily_graph_api_custom.get_all_responses(
                    start_date=timing_periods["current_period"]["start"],
                    end_date=timing_periods["current_period"]["end"]
                )
            except Exception as e:
                print(f"Error fetching custom timing responses: {str(e)}")
                traceback.print_exc()
                # Fall back to standard responses
                daily_graph_api_responses_custom = daily_graph_api_responses_standard
        else:
            # Use standard timing for regular days
            daily_graph_api_responses_custom = daily_graph_api_responses_standard
        
        # Generate alerts with error handling
        pre_market_alerts = []
        dq_pre_market_alerts = []
        momentum_alerts = []
        longterm_momentum_alerts = []
        pre_market_meta = []
        dq_pre_market_meta = []
        momentum_meta = []
        longterm_momentum_meta = []
        
        try:
            # Create alerts factory with custom responses for daily alerts
            print("Generating pre-market alerts...")
            alerts_factory = Alerts(price_enabled, only_faang, date, page, conditions, daily_graph_api_responses_custom, es_env=es_env)
            alerts = alerts_factory.create_alerts()
            
            # Generate pre-market alerts (daily alerts) with custom timing if applicable
            pre_market_data = alerts.generate_pre_market_alerts()
            pre_market_alerts = pre_market_data.get("alerts", [])
            pre_market_meta = pre_market_data.get("meta", [])
            dq_pre_market_alerts = pre_market_data.get("dq_alerts", [])
            dq_pre_market_meta = pre_market_data.get("dq_meta", [])
            print(f"Generated {len(pre_market_alerts)} pre-market alerts and {len(dq_pre_market_alerts)} DQ pre-market alerts")
            
        except Exception as e:
            print(f"Error generating pre-market alerts: {str(e)}")
            traceback.print_exc()
            # Continue with empty pre-market alerts
        
        try:
            # Create a new alerts factory with standard responses for momentum alerts
            print("Generating momentum alerts...")
            alerts_factory_standard = Alerts(price_enabled, only_faang, date, page, conditions, daily_graph_api_responses_standard, es_env=es_env)
            alerts_standard = alerts_factory_standard.create_alerts()
            
            # Generate momentum and longterm momentum alerts with standard timing
            momentum_data = alerts_standard.generate_momentum_alerts()
            momentum_alerts = momentum_data.get("alerts", [])
            momentum_meta = momentum_data.get("meta", [])
            print(f"Generated {len(momentum_alerts)} momentum alerts")
            
        except Exception as e:
            print(f"Error generating momentum alerts: {str(e)}")
            traceback.print_exc()
            # Continue with empty momentum alerts
            
        try:
            print("Generating longterm momentum alerts...")
            longterm_momentum_data = alerts_standard.generate_longterm_momentum_alerts()
            longterm_momentum_alerts = longterm_momentum_data.get("alerts", [])
            longterm_momentum_meta = longterm_momentum_data.get("meta", [])
            print(f"Generated {len(longterm_momentum_alerts)} longterm momentum alerts")
            
        except Exception as e:
            print(f"Error generating longterm momentum alerts: {str(e)}")
            traceback.print_exc()
            # Continue with empty longterm momentum alerts

        response_body = {
            "message": "success",
            "date": date,
            "data": {
                "pre_market_alerts": pre_market_alerts,
                "dq_pre_market_alerts": dq_pre_market_alerts,
                "momentum_alerts": momentum_alerts,
                "longterm_momentum_alerts": longterm_momentum_alerts
            }
        }

        if is_dev:
            response_body["data"]["meta"] = [{
                "pre_market": pre_market_meta,
                "dq_pre_market": dq_pre_market_meta,
                "momentum": momentum_meta,
                "longterm_momentum": longterm_momentum_meta
            }]

        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "failed",
                "error": "Invalid JSON format in request"
            }),
        }
    except KeyError as e:
        print(f"Missing required field: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "failed",
                "error": f"Missing required field: {str(e)}"
            }),
        }
    except Exception as e:
        print(f"Unexpected error in lambda_handler: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "failed",
                "error": str(e)
            }),
        }
