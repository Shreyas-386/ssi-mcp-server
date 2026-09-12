from s3_market import S3MarketData
from alphavantage import Alphavantage
from utils import AlertUtils
from constants import graph_types
from datetime import datetime
from dq import news_multiplier, reddit_dq_weight, DEFAULT_NEWS_DQ_SCORES


class Alerts:
    def __init__(self, price_enabled, only_faang, date, page, conditions, daily_graph_api_responses, es_env="prod"):
        self.price_enabled = price_enabled
        self.only_faang = only_faang
        self.date = date
        self.page = page
        self.conditions = conditions
        self.daily_graph_api_responses = daily_graph_api_responses
        self.es_env = es_env

    def create_alerts(self):
        if self.price_enabled:
            return SentimentPriceAlerts(self.only_faang, self.date, self.page, self.conditions, daily_graph_api_responses=self.daily_graph_api_responses, es_env=self.es_env)
        else:
            return SentimentAlerts(self.only_faang, self.date, self.page, self.conditions, daily_graph_api_responses=self.daily_graph_api_responses)

class SentimentAlerts():
    def __init__(self, only_faang, date, page, conditions, daily_graph_api_responses):
        self.alert_utils = AlertUtils()
        self.date = date
        self.page = page
        self.stock_list = self.alert_utils.get_stock_list(only_faang, page)
        self.only_faang = only_faang
        self.conditions = conditions
        self.daily_graph_api_responses = daily_graph_api_responses
        print(f"Sentiment Alerts Initiated - \n page -> {page} \n stock_list -> {self.stock_list}")

    def generate_pre_market_alerts(self):
        social_buzz_change = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[0]],
            "one_day_st_change_percent",
            "one_day_news_change_percent",
            self.only_faang,
            page=self.page
        )

        social_sentiment_change = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[1]],
            "one_day_st_change_percent",
            "one_day_news_change_percent",
            self.only_faang,
            page=self.page
        )

        # Get actual buzz values for suppression logic
        one_day_social_buzz = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page,
            is_buzz=True
        )

        one_day_news_buzz = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )

        pre_market_alerts = []
        pre_market_meta = []
        dq_pre_market_alerts = []
        dq_pre_market_meta = []

        for index, sentiment_change in enumerate(social_sentiment_change):
            buzz_change = social_buzz_change[index]
            stock = self.stock_list[index]
            
            # Get actual buzz values for this stock
            current_social_buzz = one_day_social_buzz[index] if one_day_social_buzz[index] is not None else 0
            current_news_buzz = one_day_news_buzz[index] if one_day_news_buzz[index] is not None else 0

            # Daily Alert Suppression: Suppress if combined buzz (news + social) < 8
            combined_buzz = current_news_buzz + current_social_buzz
            should_suppress = combined_buzz < 8
            
            # Get the first condition for meta data (assuming conditions exist)
            first_condition = self.conditions[0] if self.conditions else {"buzz_change": 0, "sentiment_change": 0}
            
            if should_suppress:
                print(f"[SUPPRESSION] Daily alert suppressed for {stock}: news_buzz={current_news_buzz}, social_buzz={current_social_buzz}, combined_buzz={combined_buzz}")
            else:
                for condition in self.conditions:
                    result = condition["result"]

                    if condition["sentiment_change"] > 0:
                        if sentiment_change > condition["sentiment_change"] and buzz_change > condition["buzz_change"]:
                            pre_market_alerts.append({"stock": stock, "result": result})
                            break
                    elif condition["sentiment_change"] < 0:
                        if sentiment_change < condition["sentiment_change"] and buzz_change > condition["buzz_change"]:
                            pre_market_alerts.append({"stock": stock, "result": result})
                            break
                    
            pre_market_meta.append({
                "stock": stock, 
                "sentiment_change": sentiment_change, 
                "buzz_change": buzz_change, 
                "current_news_buzz": current_news_buzz,
                "current_social_buzz": current_social_buzz,
                "combined_buzz": combined_buzz,
                "suppressed": should_suppress,
                "condition_buzz_change": first_condition["buzz_change"], 
                "condition_sentiment_change": first_condition["sentiment_change"]
            })

            # DQ Calculations for DQ-adjusted Daily Alerts
            news_dq_score = DEFAULT_NEWS_DQ_SCORES.get(stock, 0.8)
            wsb_dq_score = 0.8
            news_mult = news_multiplier(news_dq_score)
            wsb_mult = reddit_dq_weight(wsb_dq_score)

            dq_news_buzz = current_news_buzz * news_mult
            dq_wsb_buzz = current_social_buzz * wsb_mult
            dq_combined_buzz = dq_news_buzz + dq_wsb_buzz
            dq_suppressed = dq_combined_buzz < 8
            
            dq_buzz_change = buzz_change * ((news_mult + wsb_mult) / 2.0)

            if not dq_suppressed:
                for condition in self.conditions:
                    result = condition["result"]

                    if condition["sentiment_change"] > 0:
                        if sentiment_change > condition["sentiment_change"] and dq_buzz_change > condition["buzz_change"]:
                            dq_pre_market_alerts.append({"stock": stock, "result": result})
                            break
                    elif condition["sentiment_change"] < 0:
                        if sentiment_change < condition["sentiment_change"] and dq_buzz_change > condition["buzz_change"]:
                            dq_pre_market_alerts.append({"stock": stock, "result": result})
                            break

            dq_pre_market_meta.append({
                "stock": stock,
                "sentiment_change": sentiment_change,
                "dq_buzz_change": dq_buzz_change,
                "news_dq_score": news_dq_score,
                "wsb_dq_score": wsb_dq_score,
                "dq_news_buzz": dq_news_buzz,
                "dq_wsb_buzz": dq_wsb_buzz,
                "dq_combined_buzz": dq_combined_buzz,
                "dq_suppressed": dq_suppressed,
                "condition_buzz_change": first_condition["buzz_change"],
                "condition_sentiment_change": first_condition["sentiment_change"]
            })

        return {
            "alerts": pre_market_alerts,
            "meta": pre_market_meta,
            "dq_alerts": dq_pre_market_alerts,
            "dq_meta": dq_pre_market_meta
        }

    def generate_momentum_alerts(self):
        # Generate mapped sentiment data for each timeframe
        prev_day_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )
        prev_day_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )

        one_week_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )
        one_week_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )

        two_week_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "two_week_st",
            "two_week_news",
            self.only_faang,
            page=self.page
        )
        two_week_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "two_week_st",
            "two_week_news",
            self.only_faang,
            page=self.page
        )

        one_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_month_st",
            "one_month_news",
            self.only_faang,
            page=self.page
        )
        one_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_month_st",
            "one_month_news",
            self.only_faang,
            page=self.page
        )

        # Add 60 days (two_month) data fetching
        two_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "two_month_st",
            "two_month_news",
            self.only_faang,
            page=self.page
        )
        two_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "two_month_st",
            "two_month_news",
            self.only_faang,
            page=self.page
        )

        # Add 90 days (three_month) data fetching
        three_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "three_month_st",
            "three_month_news",
            self.only_faang,
            page=self.page
        )
        three_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "three_month_st",
            "three_month_news",
            self.only_faang,
            page=self.page
        )

        # Get separate buzz values for suppression logic
        one_day_social_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page,
            is_buzz=True
        )
        
        one_day_news_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st", 
            "one_day_news",
            self.only_faang,
            page=self.page
        )
        
        one_week_social_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news", 
            self.only_faang,
            page=self.page,
            is_buzz=True
        )
        
        one_week_news_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )

        momentum_meta = []
        momentum_alerts = []

        for index in range(len(self.stock_list)):
            prev_day_sentiment = prev_day_sentiments[index]
            prev_day_buzz = prev_day_buzzes[index]
            one_week_sentiment = one_week_sentiments[index]
            one_week_buzz = one_week_buzzes[index]
            two_week_sentiment = two_week_sentiments[index]
            two_week_buzz = two_week_buzzes[index]
            one_month_sentiment = one_month_sentiments[index]
            one_month_buzz = one_month_buzzes[index]
            two_month_sentiment = two_month_sentiments[index]
            two_month_buzz = two_month_buzzes[index]
            three_month_sentiment = three_month_sentiments[index]
            three_month_buzz = three_month_buzzes[index]
            stock = self.stock_list[index]
            
            # Get separate buzz values for suppression logic
            one_day_social = one_day_social_buzz_only[index] if one_day_social_buzz_only[index] is not None else 0
            one_day_news = one_day_news_buzz_only[index] if one_day_news_buzz_only[index] is not None else 0
            one_week_social = one_week_social_buzz_only[index] if one_week_social_buzz_only[index] is not None else 0
            one_week_news = one_week_news_buzz_only[index] if one_week_news_buzz_only[index] is not None else 0
            
            # Momentum Alert Suppression: Suppress if combined buzz is low for both 1-day and 7-day periods
            one_day_combined_buzz = one_day_news + one_day_social
            one_week_combined_buzz = one_week_news + one_week_social
            should_suppress = one_day_combined_buzz < 8 and one_week_combined_buzz < 8
            
            if should_suppress:
                print(f"[SUPPRESSION] Momentum alert suppressed for {stock}: 1d_news={one_day_news}, 1d_social={one_day_social}, 1d_combined={one_day_combined_buzz}, 7d_news={one_week_news}, 7d_social={one_week_social}, 7d_combined={one_week_combined_buzz}")

            momentum_meta.append({
                    "stock": stock,
                    "prev_day_sentiment": prev_day_sentiment, 
                    "prev_day_buzz": prev_day_buzz,
                    "one_week_sentiment": one_week_sentiment,
                    "one_week_buzz": one_week_buzz,
                    "two_week_sentiment": two_week_sentiment,
                    "two_week_buzz": two_week_buzz,
                    "one_month_sentiment": one_month_sentiment,
                    "one_month_buzz": one_month_buzz,
                    "two_month_sentiment": two_month_sentiment,
                    "two_month_buzz": two_month_buzz,
                    "three_month_sentiment": three_month_sentiment,
                    "three_month_buzz": three_month_buzz,
                    "one_day_social_buzz": one_day_social,
                    "one_day_news_buzz": one_day_news,
                    "one_day_combined_buzz": one_day_combined_buzz,
                    "one_week_social_buzz": one_week_social,
                    "one_week_news_buzz": one_week_news,
                    "one_week_combined_buzz": one_week_combined_buzz,
                    "suppressed": should_suppress
                })
            
            # Only generate alerts if not suppressed
            if not should_suppress:
                # Original momentum conditions (1/7/14/30 days)
                if (one_month_sentiment < two_week_sentiment < one_week_sentiment < prev_day_sentiment) \
                    and (one_month_buzz < two_week_buzz < one_week_buzz < prev_day_buzz):
                    momentum_alerts.append({"stock": stock, "result": "STRONG_BUY"})
                elif (one_month_sentiment > two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (one_month_buzz > two_week_buzz > one_week_buzz > prev_day_buzz):
                    momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})
                elif (two_week_sentiment < one_week_sentiment < prev_day_sentiment) \
                    and (two_week_buzz < one_week_buzz < prev_day_buzz):
                    momentum_alerts.append({"stock": stock, "result": "BUY"})
                elif (two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (two_week_buzz > one_week_buzz > prev_day_buzz):
                    momentum_alerts.append({"stock": stock, "result": "SELL"})
                elif (one_month_sentiment > two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (one_month_buzz < two_week_buzz < one_week_buzz < prev_day_buzz): 
                    momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})
                elif (two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (two_week_buzz < one_week_buzz < prev_day_buzz):
                    momentum_alerts.append({"stock": stock, "result": "SELL"})
                
        return {"alerts": momentum_alerts, "meta": momentum_meta}

    def generate_longterm_momentum_alerts(self):
        """
        Generate long-term momentum alerts based on consistent trends across 1, 30, 60, 90 days (RELAXED CONDITIONS).
        Criteria: Sentiment, Buzz, and Price must all show consistent increasing or decreasing trend.
        If trend extends to 90 days: STRONG BUY/SELL
        If trend doesn't extend to 90 days: BUY/SELL
        """
        # Generate mapped sentiment data for each timeframe
        prev_day_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )
        prev_day_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )

        one_week_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )
        one_week_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )

        two_week_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "two_week_st",
            "two_week_news",
            self.only_faang,
            page=self.page
        )
        two_week_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "two_week_st",
            "two_week_news",
            self.only_faang,
            page=self.page
        )

        one_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "one_month_st",
            "one_month_news",
            self.only_faang,
            page=self.page
        )
        one_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_month_st",
            "one_month_news",
            self.only_faang,
            page=self.page
        )

        two_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "two_month_st",
            "two_month_news",
            self.only_faang,
            page=self.page
        )
        two_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "two_month_st",
            "two_month_news",
            self.only_faang,
            page=self.page
        )

        three_month_sentiments = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[2]],
            "three_month_st",
            "three_month_news",
            self.only_faang,
            page=self.page
        )
        three_month_buzzes = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "three_month_st",
            "three_month_news",
            self.only_faang,
            page=self.page
        )

        longterm_momentum_meta = []
        longterm_momentum_alerts = []

        for index in range(len(self.stock_list)):
            prev_day_sentiment = prev_day_sentiments[index]
            prev_day_buzz = prev_day_buzzes[index]
            one_week_sentiment = one_week_sentiments[index]
            one_week_buzz = one_week_buzzes[index]
            two_week_sentiment = two_week_sentiments[index]
            two_week_buzz = two_week_buzzes[index]
            one_month_sentiment = one_month_sentiments[index]
            one_month_buzz = one_month_buzzes[index]
            two_month_sentiment = two_month_sentiments[index]
            two_month_buzz = two_month_buzzes[index]
            three_month_sentiment = three_month_sentiments[index]
            three_month_buzz = three_month_buzzes[index]
            stock = self.stock_list[index]
            
            # Get separate buzz values for suppression logic
            one_day_social_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            
            one_day_news_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st", 
                "one_day_news",
                self.only_faang,
                page=self.page
            )
            
            one_month_social_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news", 
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            
            one_month_news_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page
            )
            
            # Get separate buzz values for suppression logic
            one_day_social = one_day_social_buzz_only[index] if one_day_social_buzz_only[index] is not None else 0
            one_day_news = one_day_news_buzz_only[index] if one_day_news_buzz_only[index] is not None else 0
            one_month_social = one_month_social_buzz_only[index] if one_month_social_buzz_only[index] is not None else 0
            one_month_news = one_month_news_buzz_only[index] if one_month_news_buzz_only[index] is not None else 0
            
            # Long-term Momentum Alert Suppression: Suppress if combined buzz is low for both 1-day and 30-day periods
            one_day_combined_buzz = one_day_news + one_day_social
            one_month_combined_buzz = one_month_news + one_month_social
            should_suppress = one_day_combined_buzz < 8 and one_month_combined_buzz < 8
            
            if should_suppress:
                print(f"[SUPPRESSION] Long-term momentum alert suppressed for {stock}: 1d_news={one_day_news}, 1d_social={one_day_social}, 1d_combined={one_day_combined_buzz}, 30d_news={one_month_news}, 30d_social={one_month_social}, 30d_combined={one_month_combined_buzz}")

            longterm_momentum_meta.append({
                "stock": stock,
                "prev_day_sentiment": prev_day_sentiment, 
                "prev_day_buzz": prev_day_buzz,
                "one_week_sentiment": one_week_sentiment,
                "one_week_buzz": one_week_buzz,
                "two_week_sentiment": two_week_sentiment,
                "two_week_buzz": two_week_buzz,
                "one_month_sentiment": one_month_sentiment,
                "one_month_buzz": one_month_buzz,
                "two_month_sentiment": two_month_sentiment,
                "two_month_buzz": two_month_buzz,
                "three_month_sentiment": three_month_sentiment,
                "three_month_buzz": three_month_buzz,
                "one_day_social_buzz": one_day_social,
                "one_day_news_buzz": one_day_news,
                "one_day_combined_buzz": one_day_combined_buzz,
                "one_month_social_buzz": one_month_social,
                "one_month_news_buzz": one_month_news,
                "one_month_combined_buzz": one_month_combined_buzz,
                "suppressed": should_suppress
            })
            
            # Only generate alerts if not suppressed
            if not should_suppress:
                # Check for consistent positive trend across timeframes (1, 30, 60 days) - RELAXED CONDITIONS
                positive_trend_60_days = (
                    prev_day_sentiment > one_month_sentiment > two_month_sentiment
                    and prev_day_buzz > one_month_buzz > two_month_buzz
                )
                
                # Check if positive trend extends to 90 days
                positive_trend_90_days = (
                    positive_trend_60_days
                    and prev_day_sentiment > one_month_sentiment > two_month_sentiment > three_month_sentiment
                    and prev_day_buzz > one_month_buzz > two_month_buzz > three_month_buzz
                )
                
                # Check for consistent negative trend across timeframes (1, 30, 60 days) - RELAXED CONDITIONS
                negative_trend_60_days = (
                    prev_day_sentiment < one_month_sentiment < two_month_sentiment
                    and prev_day_buzz < one_month_buzz < two_month_buzz
                )
                
                # Check if negative trend extends to 90 days
                negative_trend_90_days = (
                    negative_trend_60_days
                    and prev_day_sentiment < one_month_sentiment < two_month_sentiment < three_month_sentiment
                    and prev_day_buzz < one_month_buzz < two_month_buzz < three_month_buzz
                )
                
                # Apply long-term momentum logic
                if positive_trend_90_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "STRONG_BUY"})
                elif positive_trend_60_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "BUY"})
                elif negative_trend_90_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})
                elif negative_trend_60_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "SELL"})

        return {"alerts": longterm_momentum_alerts, "meta": longterm_momentum_meta}

class SentimentPriceAlerts():
    def __init__(self, only_faang, date, page, conditions, daily_graph_api_responses, es_env="prod"):
        self.alert_utils = AlertUtils()
        self.page = page
        self.stock_list = self.alert_utils.get_stock_list(only_faang, page)
        self.only_faang = only_faang
        self.conditions = conditions
        self.daily_graph_api_responses = daily_graph_api_responses
        self.date = self.alert_utils.get_current_date(date)
        self.is_trading_day = self.alert_utils.is_trading_day(date)
        self.es_env = es_env
        print(f"Sentiment Price Alerts Initiated - \n page -> {page} \n stock_list -> {self.stock_list} \n es_env -> {es_env}")

    def calculate_price_change(self, current_date_avg_price, market_closing_price_prev_day):
        if market_closing_price_prev_day == 0:
            return 0
        return ((current_date_avg_price - market_closing_price_prev_day) / market_closing_price_prev_day) * 100

    def generate_pre_market_alerts(self):
        pre_market_meta = []
        pre_market_alerts = []
        dq_pre_market_alerts = []
        dq_pre_market_meta = []
        
        if self.is_trading_day is False:
            return {
                "alerts": pre_market_alerts,
                "meta": pre_market_meta,
                "dq_alerts": dq_pre_market_alerts,
                "dq_meta": dq_pre_market_meta
            }

        social_buzz_change = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[0]],
            "one_day_st_change_percent",
            "one_day_news_change_percent",
            self.only_faang,
            page=self.page
        )

        social_sentiment_change = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[1]],
            "one_day_st_change_percent",
            "one_day_news_change_percent",
            self.only_faang,
            page=self.page
        )

        # Get actual buzz values for suppression logic
        one_day_social_buzz = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page,
            is_buzz=True
        )

        one_day_news_buzz = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page
        )

        # Check if this is Monday or post-holiday scenario
        # Handle both full datetime format and simple date format
        try:
            # Try parsing as full datetime with timezone
            current_date_str = datetime.strptime(self.date, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try parsing as simple date format
                current_date_str = datetime.strptime(self.date, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                # If both fail, assume it's already in the correct format
                current_date_str = self.date
        
        is_monday_or_post_holiday = self.alert_utils.is_monday_or_post_holiday(current_date_str)
        
        if is_monday_or_post_holiday:
            # Use custom timing periods for Monday/post-holiday
            timing_periods = self.alert_utils.get_alert_timing_periods(self.date)
            print(f"Using custom timing for Monday/post-holiday price calculation: {timing_periods}")
            
            # For Monday/post-holiday, compare pre-market average price with Friday closing price
            # Current period: Use the custom timing period
            current_start = timing_periods["current_period"]["start"]
            current_end = timing_periods["current_period"]["end"]
            
            # Previous trading day: Get the last trading day before the holiday period
            prev_trading_day = self.alert_utils.get_last_trading_day(current_date_str)
        else:
            # Use standard pre-market timing (4AM to 8AM)
            date = self.alert_utils.get_pre_market_datetime(self.date)
            current_start = date.get("start_date")
            current_end = date.get("end_date")
            
            # Get the previous trading day
            prev_trading_day = self.alert_utils.get_prev_trading_day(self.date)

        s3_market_data = S3MarketData()

        market_data = s3_market_data.get_market_data(prev_trading_day)
        print("HERE", market_data)

        # Loop over each stock in the stock list
        for index, stock in enumerate(self.stock_list):
            alphavantage = Alphavantage(stock, es_env=self.es_env)

            buzz_change = social_buzz_change[index]
            sentiment_change = social_sentiment_change[index]
            
            # Get actual buzz values for this stock
            current_social_buzz = one_day_social_buzz[index] if one_day_social_buzz[index] is not None else 0
            current_news_buzz = one_day_news_buzz[index] if one_day_news_buzz[index] is not None else 0

            # Daily Alert Suppression: Suppress if combined buzz (news + social) < 8
            combined_buzz = current_news_buzz + current_social_buzz
            should_suppress = combined_buzz < 8

            # Fetch the market closing price for the previous trading day
            market_closing_price_prev_day = market_data.get(stock, None)
            print("HERE", market_closing_price_prev_day, prev_trading_day, stock)
            
            # Calculate the average closing price for the current date using custom timing if needed
            current_date_avg_price = alphavantage.calculate_average_closing_price(current_start, current_end)

            # DQ Calculations for DQ-adjusted Daily Alerts
            news_dq_score = DEFAULT_NEWS_DQ_SCORES.get(stock, 0.8)
            wsb_dq_score = 0.8
            news_mult = news_multiplier(news_dq_score)
            wsb_mult = reddit_dq_weight(wsb_dq_score)

            dq_news_buzz = current_news_buzz * news_mult
            dq_wsb_buzz = current_social_buzz * wsb_mult
            dq_combined_buzz = dq_news_buzz + dq_wsb_buzz
            dq_suppressed = dq_combined_buzz < 8
            
            dq_buzz_change = buzz_change * ((news_mult + wsb_mult) / 2.0)

            if market_closing_price_prev_day is None:
                pre_market_meta.append({
                    "stock": stock, 
                    "sentiment_change": round(sentiment_change, 2), 
                    "buzz_change": round(buzz_change, 2),
                    "price_change": "NA",
                    "current_date_avg_price": "NA",
                    "market_closing_price_prev_day": "NA",
                    "current_news_buzz": current_news_buzz,
                    "current_social_buzz": current_social_buzz,
                    "combined_buzz": combined_buzz,
                    "suppressed": should_suppress
                })
                dq_pre_market_meta.append({
                    "stock": stock,
                    "sentiment_change": round(sentiment_change, 2),
                    "dq_buzz_change": round(dq_buzz_change, 2),
                    "price_change": "NA",
                    "news_dq_score": news_dq_score,
                    "wsb_dq_score": wsb_dq_score,
                    "dq_news_buzz": round(dq_news_buzz, 2),
                    "dq_wsb_buzz": round(dq_wsb_buzz, 2),
                    "dq_combined_buzz": round(dq_combined_buzz, 2),
                    "dq_suppressed": dq_suppressed
                })
                continue

            # If no closing prices are available, Send only sentiment alerts
            print(f"PRE_MARKET Fetched AVG Price Data {stock} {current_date_avg_price}")
            if not current_date_avg_price:
                pre_market_meta.append({
                    "stock": stock,
                    "sentiment_change": round(sentiment_change, 2), 
                    "buzz_change": round(buzz_change, 2),
                    "price_change": "NA",
                    "current_date_avg_price": "NA",
                    "market_closing_price_prev_day": round(market_closing_price_prev_day, 2),
                    "current_news_buzz": current_news_buzz,
                    "current_social_buzz": current_social_buzz,
                    "combined_buzz": combined_buzz,
                    "suppressed": should_suppress
                })
                dq_pre_market_meta.append({
                    "stock": stock,
                    "sentiment_change": round(sentiment_change, 2),
                    "dq_buzz_change": round(dq_buzz_change, 2),
                    "price_change": "NA",
                    "news_dq_score": news_dq_score,
                    "wsb_dq_score": wsb_dq_score,
                    "dq_news_buzz": round(dq_news_buzz, 2),
                    "dq_wsb_buzz": round(dq_wsb_buzz, 2),
                    "dq_combined_buzz": round(dq_combined_buzz, 2),
                    "dq_suppressed": dq_suppressed
                })
                continue

            price_change = self.calculate_price_change(current_date_avg_price, market_closing_price_prev_day)
            
            pre_market_meta.append({
                "stock": stock, 
                "sentiment_change": round(sentiment_change, 2), 
                "buzz_change": round(buzz_change, 2),
                "price_change": round(price_change, 2),
                "current_date_avg_price": round(current_date_avg_price, 2), 
                "market_closing_price_prev_day": round(market_closing_price_prev_day, 2),
                "current_news_buzz": current_news_buzz,
                "current_social_buzz": current_social_buzz,
                "combined_buzz": combined_buzz,
                "suppressed": should_suppress
            })

            dq_pre_market_meta.append({
                "stock": stock,
                "sentiment_change": round(sentiment_change, 2),
                "dq_buzz_change": round(dq_buzz_change, 2),
                "price_change": round(price_change, 2),
                "news_dq_score": news_dq_score,
                "wsb_dq_score": wsb_dq_score,
                "dq_news_buzz": round(dq_news_buzz, 2),
                "dq_wsb_buzz": round(dq_wsb_buzz, 2),
                "dq_combined_buzz": round(dq_combined_buzz, 2),
                "dq_suppressed": dq_suppressed
            })

            if should_suppress:
                print(f"[SUPPRESSION] Daily price alert suppressed for {stock}: news_buzz={current_news_buzz}, social_buzz={current_social_buzz}, combined_buzz={combined_buzz}")
            else:
                for condition in self.conditions:
                    result = condition["result"]

                    if condition["sentiment_change"] > 0:
                        if sentiment_change > condition["sentiment_change"] and buzz_change > condition["buzz_change"] and price_change > condition["price_change"]:
                            pre_market_alerts.append({"stock": stock, "result": result})
                            break
                    elif condition["sentiment_change"] < 0:
                        if sentiment_change < condition["sentiment_change"] and buzz_change > condition["buzz_change"] and price_change < condition["price_change"]:
                            pre_market_alerts.append({"stock": stock, "result": result})
                            break

            if not dq_suppressed:
                for condition in self.conditions:
                    result = condition["result"]

                    if condition["sentiment_change"] > 0:
                        if sentiment_change > condition["sentiment_change"] and dq_buzz_change > condition["buzz_change"] and price_change > condition["price_change"]:
                            dq_pre_market_alerts.append({"stock": stock, "result": result})
                            break
                    elif condition["sentiment_change"] < 0:
                        if sentiment_change < condition["sentiment_change"] and dq_buzz_change > condition["buzz_change"] and price_change < condition["price_change"]:
                            dq_pre_market_alerts.append({"stock": stock, "result": result})
                            break

        return {
            "alerts": pre_market_alerts,
            "meta": pre_market_meta,
            "dq_alerts": dq_pre_market_alerts,
            "dq_meta": dq_pre_market_meta
        }
        
    def generate_momentum_alerts(self):
        if self.is_trading_day is False:
            return {"alerts": [], "meta": []}
        
        # For Momentum alerts, We'll take 7 Days, 14 Days, 30 Days avg price.
        # First get me 7, 14 & 30 Days from given date
        # Create function that gets 7, 14, 30 days in dates
        date_top_day = self.alert_utils.get_date_n_days_ago(self.date, 0)
        date_1_days = self.alert_utils.get_date_n_days_ago(self.date, 1)
        date_7_days = self.alert_utils.get_date_n_days_ago(self.date, 7)
        date_14_days = self.alert_utils.get_date_n_days_ago(self.date, 14)
        date_30_days = self.alert_utils.get_date_n_days_ago(self.date, 30)
        date_60_days = self.alert_utils.get_date_n_days_ago(self.date, 60)
        date_90_days = self.alert_utils.get_date_n_days_ago(self.date, 90)

        # Get separate buzz values for suppression logic
        one_day_social_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st",
            "one_day_news",
            self.only_faang,
            page=self.page,
            is_buzz=True
        )
        
        one_day_news_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_day_st", 
            "one_day_news",
            self.only_faang,
            page=self.page
        )
        
        one_week_social_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news", 
            self.only_faang,
            page=self.page,
            is_buzz=True
        )
        
        one_week_news_buzz_only = self.alert_utils.get_alert_data(
            self.daily_graph_api_responses[graph_types[3]],
            "one_week_st",
            "one_week_news",
            self.only_faang,
            page=self.page
        )

        momentum_alerts = []
        momentum_meta = []

        # Loop over each stock in the stock list
        for index, stock in enumerate(self.stock_list):        
            alphavantage = Alphavantage(stock, es_env=self.es_env)

            days_1_avg_price = alphavantage.calculate_average_closing_price(date_1_days, date_top_day) or 0
            days_7_avg_price = alphavantage.calculate_average_closing_price(date_7_days, date_top_day) or 0
            days_14_avg_price = alphavantage.calculate_average_closing_price(date_14_days, date_top_day) or 0
            days_30_avg_price = alphavantage.calculate_average_closing_price(date_30_days, date_top_day) or 0
            days_60_avg_price = alphavantage.calculate_average_closing_price(date_60_days, date_top_day) or 0
            days_90_avg_price = alphavantage.calculate_average_closing_price(date_90_days, date_top_day) or 0
            print(f"MOMENTUM Fetched AVG Price Data {stock}")
            
            # Get separate buzz values for suppression logic
            one_day_social = one_day_social_buzz_only[index] if one_day_social_buzz_only[index] is not None else 0
            one_day_news = one_day_news_buzz_only[index] if one_day_news_buzz_only[index] is not None else 0
            one_week_social = one_week_social_buzz_only[index] if one_week_social_buzz_only[index] is not None else 0
            one_week_news = one_week_news_buzz_only[index] if one_week_news_buzz_only[index] is not None else 0
            
            # Momentum Alert Suppression: Suppress if combined buzz is low for both 1-day and 7-day periods
            one_day_combined_buzz = one_day_news + one_day_social
            one_week_combined_buzz = one_week_news + one_week_social
            should_suppress = one_day_combined_buzz < 8 and one_week_combined_buzz < 8
            
            if should_suppress:
                print(f"[SUPPRESSION] Momentum price alert suppressed for {stock}: 1d_news={one_day_news}, 1d_social={one_day_social}, 1d_combined={one_day_combined_buzz}, 7d_news={one_week_news}, 7d_social={one_week_social}, 7d_combined={one_week_combined_buzz}")

            prev_day_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page
            )
            prev_day_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            one_week_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_week_st",
                "one_week_news",
                self.only_faang,
                page=self.page
            )
            one_week_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_week_st",
                "one_week_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            two_week_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "two_week_st",
                "two_week_news",
                self.only_faang,
                page=self.page
            )
            two_week_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "two_week_st",
                "two_week_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            one_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page
            )
            one_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            two_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "two_month_st",
                "two_month_news",
                self.only_faang,
                page=self.page
            )
            two_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "two_month_st",
                "two_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )

            # Add 90 days (three_month) data fetching
            three_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "three_month_st",
                "three_month_news",
                self.only_faang,
                page=self.page
            )
            three_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "three_month_st",
                "three_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )

            prev_day_sentiment = prev_day_sentiments[index]
            prev_day_buzz = prev_day_buzzes[index]
            one_week_sentiment = one_week_sentiments[index]
            one_week_buzz = one_week_buzzes[index]
            two_week_sentiment = two_week_sentiments[index]
            two_week_buzz = two_week_buzzes[index]
            one_month_sentiment = one_month_sentiments[index]
            one_month_buzz = one_month_buzzes[index]
            two_month_sentiment = two_month_sentiments[index]
            two_month_buzz = two_month_buzzes[index]
            three_month_sentiment = three_month_sentiments[index]
            three_month_buzz = three_month_buzzes[index]

            momentum_meta.append({
                "stock": stock,
                "prev_day_buzz": prev_day_buzz,
                "one_week_buzz": one_week_buzz,
                "two_week_buzz": two_week_buzz,
                "one_month_buzz": one_month_buzz,
                "two_month_buzz": two_month_buzz,
                "three_month_buzz": three_month_buzz,
                "prev_day_sentiment": prev_day_sentiment,
                "one_week_sentiment": one_week_sentiment,
                "two_week_sentiment": two_week_sentiment,
                "one_month_sentiment": one_month_sentiment,
                "two_month_sentiment": two_month_sentiment,
                "three_month_sentiment": three_month_sentiment,
                "prev_day_avg_price": days_1_avg_price,
                "one_week_avg_price": days_7_avg_price,
                "two_week_avg_price": days_14_avg_price,
                "one_month_avg_price": days_30_avg_price,
                "two_month_avg_price": days_60_avg_price,
                "three_month_avg_price": days_90_avg_price,
                "one_day_social_buzz": one_day_social,
                "one_day_news_buzz": one_day_news,
                "one_day_combined_buzz": one_day_combined_buzz,
                "one_week_social_buzz": one_week_social,
                "one_week_news_buzz": one_week_news,
                "one_week_combined_buzz": one_week_combined_buzz,
                "suppressed": should_suppress
            })

            # Only generate alerts if not suppressed
            if not should_suppress:
                # Original momentum conditions (1/7/14/30 days)
                if (one_month_sentiment < two_week_sentiment < one_week_sentiment < prev_day_sentiment) \
                    and (days_30_avg_price < days_14_avg_price < days_7_avg_price < days_1_avg_price) \
                    and (one_month_buzz < two_week_buzz < one_week_buzz < prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "STRONG_BUY"})

                elif (one_month_sentiment > two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (days_30_avg_price > days_14_avg_price > days_7_avg_price > days_1_avg_price) \
                    and (one_month_buzz > two_week_buzz > one_week_buzz > prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})

                elif (two_week_sentiment < one_week_sentiment < prev_day_sentiment) \
                    and (days_14_avg_price < days_7_avg_price < days_1_avg_price) \
                    and (two_week_buzz < one_week_buzz < prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "BUY"})

                elif (two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (days_14_avg_price > days_7_avg_price > days_1_avg_price) \
                    and (two_week_buzz > one_week_buzz > prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "SELL"})

                elif (one_month_sentiment > two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (days_30_avg_price > days_14_avg_price > days_7_avg_price > days_1_avg_price) \
                    and (one_month_buzz < two_week_buzz < one_week_buzz < prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})

                elif (two_week_sentiment > one_week_sentiment > prev_day_sentiment) \
                    and (days_14_avg_price > days_7_avg_price > days_1_avg_price) \
                    and (two_week_buzz < one_week_buzz < prev_day_buzz):
                        momentum_alerts.append({"stock": stock, "result": "SELL"})
            
        return {"alerts": momentum_alerts, "meta": momentum_meta}
        
    def generate_longterm_momentum_alerts(self):
        """
        Generate long-term momentum alerts based on consistent trends across 1, 30, 60, 90 days (RELAXED CONDITIONS).
        Criteria: Sentiment, Buzz, and Price must all show consistent increasing or decreasing trend.
        If trend extends to 90 days: STRONG BUY/SELL
        If trend doesn't extend to 90 days: BUY/SELL
        """
        if self.is_trading_day is False:
            return {"alerts": [], "meta": []}
        
        # Get date ranges for price calculations (RELAXED - only 1, 30, 60, 90 days)
        date_top_day = self.alert_utils.get_date_n_days_ago(self.date, 0)
        date_1_days = self.alert_utils.get_date_n_days_ago(self.date, 1)
        date_30_days = self.alert_utils.get_date_n_days_ago(self.date, 30)
        date_60_days = self.alert_utils.get_date_n_days_ago(self.date, 60)
        date_90_days = self.alert_utils.get_date_n_days_ago(self.date, 90)

        longterm_momentum_alerts = []
        longterm_momentum_meta = []

        # Loop over each stock in the stock list
        for index, stock in enumerate(self.stock_list):        
            alphavantage = Alphavantage(stock, es_env=self.es_env)

            days_1_avg_price = alphavantage.calculate_average_closing_price(date_1_days, date_top_day) or 0
            days_30_avg_price = alphavantage.calculate_average_closing_price(date_30_days, date_top_day) or 0
            days_60_avg_price = alphavantage.calculate_average_closing_price(date_60_days, date_top_day) or 0
            days_90_avg_price = alphavantage.calculate_average_closing_price(date_90_days, date_top_day) or 0
            print(f"LONGTERM MOMENTUM Fetched AVG Price Data {stock}")
            
            # Get separate buzz values for suppression logic
            one_day_social_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            
            one_day_news_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st", 
                "one_day_news",
                self.only_faang,
                page=self.page
            )
            
            one_month_social_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news", 
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            
            one_month_news_buzz_only = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page
            )

            prev_day_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page
            )
            prev_day_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_day_st",
                "one_day_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            one_week_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_week_st",
                "one_week_news",
                self.only_faang,
                page=self.page
            )
            one_week_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_week_st",
                "one_week_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            two_week_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "two_week_st",
                "two_week_news",
                self.only_faang,
                page=self.page
            )
            two_week_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "two_week_st",
                "two_week_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            one_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page
            )
            one_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "one_month_st",
                "one_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )
            two_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "two_month_st",
                "two_month_news",
                self.only_faang,
                page=self.page
            )
            two_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "two_month_st",
                "two_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )

            three_month_sentiments = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[2]],
                "three_month_st",
                "three_month_news",
                self.only_faang,
                page=self.page
            )
            three_month_buzzes = self.alert_utils.get_alert_data(
                self.daily_graph_api_responses[graph_types[3]],
                "three_month_st",
                "three_month_news",
                self.only_faang,
                page=self.page,
                is_buzz=True
            )

            prev_day_sentiment = prev_day_sentiments[index]
            prev_day_buzz = prev_day_buzzes[index]
            one_week_sentiment = one_week_sentiments[index]
            one_week_buzz = one_week_buzzes[index]
            two_week_sentiment = two_week_sentiments[index]
            two_week_buzz = two_week_buzzes[index]
            one_month_sentiment = one_month_sentiments[index]
            one_month_buzz = one_month_buzzes[index]
            two_month_sentiment = two_month_sentiments[index]
            two_month_buzz = two_month_buzzes[index]
            three_month_sentiment = three_month_sentiments[index]
            three_month_buzz = three_month_buzzes[index]
            
            # Get separate buzz values for suppression logic
            one_day_social = one_day_social_buzz_only[index] if one_day_social_buzz_only[index] is not None else 0
            one_day_news = one_day_news_buzz_only[index] if one_day_news_buzz_only[index] is not None else 0
            one_month_social = one_month_social_buzz_only[index] if one_month_social_buzz_only[index] is not None else 0
            one_month_news = one_month_news_buzz_only[index] if one_month_news_buzz_only[index] is not None else 0
            
            # Long-term Momentum Alert Suppression: Suppress if combined buzz is low for both 1-day and 30-day periods
            one_day_combined_buzz = one_day_news + one_day_social
            one_month_combined_buzz = one_month_news + one_month_social
            should_suppress = one_day_combined_buzz < 8 and one_month_combined_buzz < 8
            
            if should_suppress:
                print(f"[SUPPRESSION] Long-term momentum alert suppressed for {stock}: 1d_news={one_day_news}, 1d_social={one_day_social}, 1d_combined={one_day_combined_buzz}, 30d_news={one_month_news}, 30d_social={one_month_social}, 30d_combined={one_month_combined_buzz}")

            longterm_momentum_meta.append({
                "stock": stock,
                "prev_day_sentiment": prev_day_sentiment, 
                "prev_day_buzz": prev_day_buzz,
                "one_week_sentiment": one_week_sentiment,
                "one_week_buzz": one_week_buzz,
                "two_week_sentiment": two_week_sentiment,
                "two_week_buzz": two_week_buzz,
                "one_month_sentiment": one_month_sentiment,
                "one_month_buzz": one_month_buzz,
                "two_month_sentiment": two_month_sentiment,
                "two_month_buzz": two_month_buzz,
                "three_month_sentiment": three_month_sentiment,
                "three_month_buzz": three_month_buzz,
                "one_day_social_buzz": one_day_social,
                "one_day_news_buzz": one_day_news,
                "one_day_combined_buzz": one_day_combined_buzz,
                "one_month_social_buzz": one_month_social,
                "one_month_news_buzz": one_month_news,
                "one_month_combined_buzz": one_month_combined_buzz,
                "suppressed": should_suppress
            })
            
            # Only generate alerts if not suppressed
            if not should_suppress:
                # Check for consistent positive trend across timeframes (1, 30, 60 days) - RELAXED CONDITIONS
                positive_trend_60_days = (
                    prev_day_sentiment > one_month_sentiment > two_month_sentiment
                    and prev_day_buzz > one_month_buzz > two_month_buzz
                    and days_1_avg_price > days_30_avg_price > days_60_avg_price
                )
                
                # Check if positive trend extends to 90 days
                positive_trend_90_days = (
                    positive_trend_60_days
                    and prev_day_sentiment > one_month_sentiment > two_month_sentiment > three_month_sentiment
                    and prev_day_buzz > one_month_buzz > two_month_buzz > three_month_buzz
                    and days_1_avg_price > days_30_avg_price > days_60_avg_price > days_90_avg_price
                )
                
                # Check for consistent negative trend across timeframes (1, 30, 60 days) - RELAXED CONDITIONS
                negative_trend_60_days = (
                    prev_day_sentiment < one_month_sentiment < two_month_sentiment
                    and prev_day_buzz < one_month_buzz < two_month_buzz
                    and days_1_avg_price < days_30_avg_price < days_60_avg_price
                )
                
                # Check if negative trend extends to 90 days
                negative_trend_90_days = (
                    negative_trend_60_days
                    and prev_day_sentiment < one_month_sentiment < two_month_sentiment < three_month_sentiment
                    and prev_day_buzz < one_month_buzz < two_month_buzz < three_month_buzz
                    and days_1_avg_price < days_30_avg_price < days_60_avg_price < days_90_avg_price
                )
                
                # Apply long-term momentum logic
                if positive_trend_90_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "STRONG_BUY"})
                elif positive_trend_60_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "BUY"})
                elif negative_trend_90_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "STRONG_SELL"})
                elif negative_trend_60_days:
                    longterm_momentum_alerts.append({"stock": stock, "result": "SELL"})

        return {"alerts": longterm_momentum_alerts, "meta": longterm_momentum_meta}