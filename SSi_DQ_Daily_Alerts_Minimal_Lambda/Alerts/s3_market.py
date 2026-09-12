import traceback
from datetime import datetime
import boto3
import json
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class S3MarketData:
    def __init__(self):
        """Initialize S3MarketData with S3 client."""
        self.s3_client = boto3.client('s3')
        self.bucket_name = "yfinance-cron"

    def _parse_date(self, date: Any) -> datetime:
        """Parse date input that could be either string or datetime object."""
        if isinstance(date, str):
            try:
                return datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Date string must be in 'YYYY-MM-DD' format, got: {date}")
        elif isinstance(date, datetime):
            return date
        else:
            raise TypeError(f"Date must be either string or datetime object, got: {type(date)}")

    def get_market_data(self, date: Any) -> Optional[Dict[str, Any]]:
        """
        Fetch market data from S3 for a specific date.
        
        Args:
            date: Either a string in 'YYYY-MM-DD' format or a datetime object
            
        Returns:
            Optional[Dict[str, Any]]: Market data dictionary for all stocks on that date, or None if not found
        """
        try:
            date_obj = self._parse_date(date)
            s3_key = f"market_data_{date_obj.strftime('%Y-%m-%d')}.json"
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"No data found in S3 for date {date_obj.strftime('%Y-%m-%d')}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data from S3: {str(e)}")
            traceback.print_exc()
            return None 