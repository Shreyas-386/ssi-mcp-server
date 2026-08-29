from datetime import date, timedelta

import pytest

from app.utils.exceptions import ValidationError
from app.validators.date_validator import validate_date, validate_date_range
from app.validators.request_validator import (
    validate_daily_graphs_request,
    validate_historical_graphs_request,
    validate_stock_price_request,
)
from app.validators.ticker_validator import validate_ticker


class TestTickerValidator:
    def test_valid_simple_ticker(self):
        assert validate_ticker("aapl") == "AAPL"

    def test_valid_ticker_with_class_suffix(self):
        assert validate_ticker("brk.b") == "BRK.B"

    def test_strips_whitespace(self):
        assert validate_ticker("  msft  ") == "MSFT"

    @pytest.mark.parametrize("bad_ticker", ["", "   ", "TOOLONGTICKER", "AA PL", "AA$PL", None])
    def test_rejects_invalid_tickers(self, bad_ticker):
        with pytest.raises(ValidationError):
            validate_ticker(bad_ticker)


class TestDateValidator:
    def test_valid_past_date(self):
        assert validate_date("2026-07-22") == date(2026, 7, 22)

    def test_rejects_malformed_date(self):
        with pytest.raises(ValidationError):
            validate_date("22-07-2026")

    def test_rejects_future_date(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        with pytest.raises(ValidationError):
            validate_date(future)

    def test_rejects_too_early_date(self):
        with pytest.raises(ValidationError):
            validate_date("1999-01-01")

    def test_valid_range(self):
        start, end = validate_date_range("2026-01-01", "2026-02-01")
        assert start < end

    def test_rejects_inverted_range(self):
        with pytest.raises(ValidationError):
            validate_date_range("2026-02-01", "2026-01-01")

    def test_rejects_range_exceeding_max_span(self):
        with pytest.raises(ValidationError):
            validate_date_range("2015-01-01", "2025-01-01")


class TestRequestValidators:
    def test_daily_graphs_request(self):
        req = validate_daily_graphs_request(ticker="aapl", date="2026-07-22")
        assert req.ticker == "AAPL"
        assert req.date == date(2026, 7, 22)

    @pytest.mark.parametrize("period", [60, 90])
    def test_historical_graphs_request_valid_periods(self, period):
        req = validate_historical_graphs_request(ticker="aapl", period=period)
        assert req.period == period

    @pytest.mark.parametrize("period", [30, 100, "60", None, True])
    def test_historical_graphs_request_rejects_invalid_periods(self, period):
        with pytest.raises(ValidationError):
            validate_historical_graphs_request(ticker="aapl", period=period)

    def test_stock_price_request(self):
        req = validate_stock_price_request(
            ticker="aapl", start_date="2026-01-01", end_date="2026-01-31"
        )
        assert req.ticker == "AAPL"
        assert req.start_date == date(2026, 1, 1)
        assert req.end_date == date(2026, 1, 31)
