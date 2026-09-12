import json
from constants import stock_list
from datetime import datetime, time, timedelta
from pytz import timezone

holidays = [
    {
        "name": "New Year's Day",
        "date": "2025-01-25",
        "status": "CLOSED"
    },
    {
        "name": "Martin Luther King, Jr. Day",
        "date": "2025-01-20",
        "status": "CLOSED"
    },
    {
        "name": "Presidents Day",
        "date": "2025-02-17",
        "status": "CLOSED"
    },
    {
        "name": "Good Friday",
        "date": "2025-04-18",
        "status": "CLOSED"
    },
    {
        "name": "Memorial Day",
        "date": "2025-05-26",
        "status": "CLOSED"
    },
    {
        "name": "Juneteenth Holiday",
        "date": "2025-06-19",
        "status": "CLOSED"
    },
    {
        "name": "Early Close",
        "date": "2025-07-03",
        "status": "HALF_DAY"
    },
    {
        "name": "Independence Day",
        "date": "2025-07-04",
        "status": "CLOSED"
    },
    {
        "name": "Labor Day",
        "date": "2025-09-01",
        "status": "CLOSED"
    },
    {
        "name": "Thanksgiving Day",
        "date": "2025-11-27",
        "status": "CLOSED"
    },
    {
        "name": "Early Close",
        "date": "2025-11-28",
        "status": "HALF_DAY"
    },
    {
        "name": "Early Close",
        "date": "2025-12-24",
        "status": "HALF_DAY"
    },
    {
        "name": "Christmas Day",
        "date": "2025-12-25",
        "status": "CLOSED"
    }
]

class AlertUtils:
    def get_stock_list(self, only_faang, page):
        stocks = []

        if only_faang:
            stocks = ["META", "AAPL", "AMZN", "NFLX", "GOOGL"]
        else:
            total_stocks = len(stock_list)
            chunk_size = total_stocks // 3
            start_index = (page - 1) * chunk_size
            end_index = start_index + chunk_size if page < 3 else total_stocks
            stocks = stock_list[start_index:end_index]

        return stocks

    def get_alert_data(self, data, key1, key2, only_faang, page=1, is_buzz=False):
        mapped_data = []
        stocks = self.get_stock_list(only_faang, page)
        
        # Debug logging
        print(f"[get_alert_data] Searching for fields: {key1}, {key2}")
        print(f"[get_alert_data] Data length: {len(data) if data else 'None'}")
        if data:
            fields_found = [entry.get("fields") for entry in data if isinstance(entry, dict)]
            print(f"[get_alert_data] Available fields in data: {set(fields_found)}")

        for stock in stocks:
            # Find entries in data where 'fields' matches key1 and key2
            # Filter out None values before checking
            buzz1 = next((buzz for buzz in data if buzz is not None and buzz.get("fields") == key1), None)
            buzz2 = next((buzz for buzz in data if buzz is not None and buzz.get("fields") == key2), None)

            if not buzz1 or not buzz2:
                print(f"[get_alert_data] Missing data for {stock}: buzz1={buzz1 is not None}, buzz2={buzz2 is not None}")
                mapped_data.append(None)
                continue

            divide_by = 1 if is_buzz else 2

            # Special case for "FB/META"
            if stock == "FB/META":
                mapped_data.append((buzz1.get("META", 0) + buzz2.get("META", 0)) / divide_by)
            else:
                mapped_data.append((buzz1.get(stock, 0) + buzz2.get(stock, 0)) / divide_by)

        return mapped_data
    
    # Write function to get current date
    def get_current_date(self, date=None):
        tz = timezone('America/New_York')

        if date:
            return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d")
        
        return datetime.now(tz).strftime("%Y-%m-%d")
    
    # Create function to open duMMYT API Response
    def open_duMMYT_response(self, file_path):
        with open(file_path) as f:
            return json.load(f)
    
    def is_holiday(self, current_date):
        for holiday in holidays:
            holiday_date = datetime.strptime(holiday['date'], "%Y-%m-%d")

            if holiday_date.date() == current_date.date() and holiday['status'] == 'CLOSED':
                return True

        return False
    
    def is_weekend(self, date):
        return date.weekday() == 5 or date.weekday() == 6
    
    def get_prev_trading_day(self, current_date):
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=1)
        if self.is_holiday(current_date_obj) or self.is_weekend(current_date_obj):
            return self.get_prev_trading_day((current_date_obj - timedelta(days=1)).strftime("%Y-%m-%d"))

        return current_date_obj.strftime("%Y-%m-%d")
    
    def is_trading_day(self, current_date):
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%dT%H:%M:%S%z")
        return not self.is_holiday(current_date_obj) and not self.is_weekend(current_date_obj)
    
    def get_date_n_days_ago(self, current_date, n):
        date_n_days_ago = datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=n)
        return datetime.combine(date_n_days_ago, time(16, 0)).strftime("%Y-%m-%dT%H:%M:%S%z")
    
    def get_last_closing_prices(self, data):
        if not data:
            print(f"No data found for date")
            return None

        # Dictionary to store the last data point for each date
        last_closing_prices = {}

        for point in data:
            # Convert timestamp from milliseconds to seconds and then to datetime
            timestamp = int(point["Timestamp"]) / 1000  # Convert to seconds
            date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            
            # Update the last data point for each date
            last_closing_prices[date_str] = float(point["Close"])
            
        # Return only the last closing price for each unique date
        return list(last_closing_prices.values())
    
    def get_pre_market_datetime(self, date):
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_date = datetime.combine(date_obj, time(4, 0))
        end_date = datetime.combine(date_obj, time(8, 0))

        return {"start_date": start_date, "end_date": end_date}

    def get_last_trading_day(self, current_date):
        """
        Get the last trading day (skipping weekends and holidays)
        This is crucial for Monday and post-holiday scenarios
        """
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        check_date = current_date_obj - timedelta(days=1)
        
        # Keep going back until we find a trading day
        while self.is_holiday(check_date) or self.is_weekend(check_date):
            check_date = check_date - timedelta(days=1)
        
        return check_date.strftime("%Y-%m-%d")
    
    def get_6am_to_6am_periods(self, current_date):
        """
        Get 6AM to 6AM periods for current day and previous trading day
        This fixes the Monday and post-holiday timing issues
        """
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        last_trading_day = self.get_last_trading_day(current_date)
        last_trading_day_obj = datetime.strptime(last_trading_day, "%Y-%m-%d")
        
        # Current period: 6AM today to 6AM tomorrow
        current_start = datetime.combine(current_date_obj, time(6, 0))
        current_end = datetime.combine(current_date_obj + timedelta(days=1), time(6, 0))
        
        # Previous period: 6AM last trading day to 6AM today
        prev_start = datetime.combine(last_trading_day_obj, time(6, 0))
        prev_end = datetime.combine(current_date_obj, time(6, 0))
        
        # Add timezone information
        tz = timezone('America/New_York')
        current_start = tz.localize(current_start)
        current_end = tz.localize(current_end)
        prev_start = tz.localize(prev_start)
        prev_end = tz.localize(prev_end)
        
        return {
            "current_period": {
                "start": current_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": current_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            "previous_period": {
                "start": prev_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": prev_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            "last_trading_day": last_trading_day
        }
    
    def is_monday_or_post_holiday(self, current_date):
        """
        Check if current date is Monday or the day after a holiday
        This helps identify when we need special timing logic
        """
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        
        # Check if it's Monday
        if current_date_obj.weekday() == 0:  # Monday
            return True
        
        # Check if previous day was a holiday
        prev_day = current_date_obj - timedelta(days=1)
        if self.is_holiday(prev_day):
            return True
        
        return False
    
    def get_monday_timing_periods(self, current_date):
        """
        Get timing periods for Monday alerts (48-hour periods)
        Returns periods for comparison: Saturday 6AM to Monday 6AM vs Friday 6AM to Saturday 6AM
        """
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        
        # Get Saturday (2 days before Monday)
        saturday = current_date_obj - timedelta(days=2)
        # Get Friday (3 days before Monday)
        friday = current_date_obj - timedelta(days=3)
        
        # Current period: Saturday 6AM to Monday 6AM
        current_start = datetime.combine(saturday, time(6, 0))
        current_end = datetime.combine(current_date_obj, time(6, 0))
        
        # Previous period: Friday 6AM to Saturday 6AM
        prev_start = datetime.combine(friday, time(6, 0))
        prev_end = datetime.combine(saturday, time(6, 0))
        
        # Add timezone information
        tz = timezone('America/New_York')
        current_start = tz.localize(current_start)
        current_end = tz.localize(current_end)
        prev_start = tz.localize(prev_start)
        prev_end = tz.localize(prev_end)
        
        return {
            "current_period": {
                "start": current_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": current_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            "previous_period": {
                "start": prev_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": prev_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            }
        }
    
    def get_post_holiday_timing_periods(self, current_date):
        """
        Get timing periods for post-holiday alerts (48-hour periods)
        Handles cases where there are consecutive holidays
        """
        current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        
        # Find the last trading day before the holiday(s)
        last_trading_day = self.get_last_trading_day(current_date)
        last_trading_day_obj = datetime.strptime(last_trading_day, "%Y-%m-%d")
        
        # Calculate the gap between current date and last trading day
        gap_days = (current_date_obj - last_trading_day_obj).days
        
        # For post-holiday scenarios, we need to adjust the periods based on the gap
        if gap_days == 1:
            # Single holiday (e.g., Friday holiday, Monday return)
            # Current period: Last trading day 6AM to current day 6AM
            current_start = datetime.combine(last_trading_day_obj, time(6, 0))
            current_end = datetime.combine(current_date_obj, time(6, 0))
            
            # Previous period: Day before last trading day 6AM to last trading day 6AM
            prev_trading_day = self.get_last_trading_day(last_trading_day)
            prev_trading_day_obj = datetime.strptime(prev_trading_day, "%Y-%m-%d")
            prev_start = datetime.combine(prev_trading_day_obj, time(6, 0))
            prev_end = datetime.combine(last_trading_day_obj, time(6, 0))
        else:
            # Multiple holidays (e.g., long weekend)
            # Current period: Last trading day 6AM to current day 6AM
            current_start = datetime.combine(last_trading_day_obj, time(6, 0))
            current_end = datetime.combine(current_date_obj, time(6, 0))
            
            # Previous period: Day before last trading day 6AM to last trading day 6AM
            prev_trading_day = self.get_last_trading_day(last_trading_day)
            prev_trading_day_obj = datetime.strptime(prev_trading_day, "%Y-%m-%d")
            prev_start = datetime.combine(prev_trading_day_obj, time(6, 0))
            prev_end = datetime.combine(last_trading_day_obj, time(6, 0))
        
        # Add timezone information
        tz = timezone('America/New_York')
        current_start = tz.localize(current_start)
        current_end = tz.localize(current_end)
        prev_start = tz.localize(prev_start)
        prev_end = tz.localize(prev_end)
        
        return {
            "current_period": {
                "start": current_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": current_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            },
            "previous_period": {
                "start": prev_start.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "end": prev_end.strftime("%Y-%m-%dT%H:%M:%S%z")
            }
        }
    
    def get_alert_timing_periods(self, current_date):
        """
        Get appropriate timing periods for alerts based on the current date
        Returns either standard 24-hour periods or 48-hour periods for Monday/post-holiday
        """
        # Handle both full datetime format and simple date format
        try:
            # Try parsing as full datetime with timezone
            current_date_str = datetime.strptime(current_date, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try parsing as simple date format
                current_date_str = datetime.strptime(current_date, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                # If both fail, assume it's already in the correct format
                current_date_str = current_date
        
        if self.is_monday_or_post_holiday(current_date_str):
            # Use 48-hour periods for Monday or post-holiday
            if datetime.strptime(current_date_str, "%Y-%m-%d").weekday() == 0:
                # Monday
                return self.get_monday_timing_periods(current_date_str)
            else:
                # Post-holiday
                return self.get_post_holiday_timing_periods(current_date_str)
        else:
            # Use standard 24-hour periods
            return self.get_6am_to_6am_periods(current_date_str)