import json

import app


GRAPH_DATA = {name: [] for name in (
    "social_buzz_change", "sentiment_change", "sentiment", "social_buzz"
)}


class FakeDailyGraphAPI:
    def __init__(self, date, es_env):
        self.date = date
        self.es_env = es_env

    def get_all_responses(self, **kwargs):
        return GRAPH_DATA


class FakeAlertGenerator:
    def generate_pre_market_alerts(self):
        return {"alerts": [{"stock": "AAPL", "result": "BUY"}], "meta": []}

    def generate_momentum_alerts(self):
        return {"alerts": [], "meta": []}

    def generate_longterm_momentum_alerts(self):
        return {"alerts": [], "meta": []}


class FakeAlertsFactory:
    received_price_modes = []

    def __init__(self, price_enabled, *args, **kwargs):
        self.received_price_modes.append(price_enabled)

    def create_alerts(self):
        return FakeAlertGenerator()


def invoke(monkeypatch, price_enabled):
    monkeypatch.setattr(app, "DailyGraphAPI", FakeDailyGraphAPI)
    monkeypatch.setattr(app, "Alerts", FakeAlertsFactory)
    event = {
        "body": json.dumps({
            "date": "2025-06-17",
            "price_enabled": price_enabled,
            "is_dev": True,
            "page": 1,
        })
    }
    return app.lambda_handler(event, None)


def test_sentiment_only_contract(monkeypatch):
    response = invoke(monkeypatch, False)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["data"]["pre_market_alerts"]
    assert False in FakeAlertsFactory.received_price_modes


def test_sentiment_plus_contract(monkeypatch):
    response = invoke(monkeypatch, True)
    assert response["statusCode"] == 200
    assert True in FakeAlertsFactory.received_price_modes
