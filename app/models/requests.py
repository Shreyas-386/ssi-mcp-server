"""
Validated request models, one per MCP tool.

These are constructed only by app/validators/request_validator.py, *after*
raw arguments have passed format/range checks -- they represent trusted,
normalized input on its way to app/services/api_client.py.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class DailyGraphsRequest(BaseModel):
    """Maps to GET /daily-graphs?ticker=...&date=..."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    date: date


class HistoricalGraphsRequest(BaseModel):
    """Maps to GET /daily-graphs-60-90-days?ticker=...&period=..."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    period: int  # one of app.config.constants.VALID_HISTORICAL_PERIODS


class StockPriceRequest(BaseModel):
    """Maps to GET /daily-graphs-stockprice?ticker=...&start_date=...&end_date=..."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    start_date: date
    end_date: date
