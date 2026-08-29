"""Per-tool request validation.

Each function validates the raw arguments an MCP client sends for one tool
and returns a validated Pydantic request model (see app/models/requests.py).
This is the single "boundary" validation step the HLD calls out under
Design Principles ("Validate at the boundary") -- nothing downstream of this
module should need to re-check ticker format, date format, etc.
"""

from __future__ import annotations

from app.config.constants import VALID_HISTORICAL_PERIODS
from app.models.requests import (
    DailyGraphsRequest,
    HistoricalGraphsRequest,
    StockPriceRequest,
)
from app.utils.exceptions import ValidationError
from app.validators.date_validator import validate_date, validate_date_range
from app.validators.ticker_validator import validate_ticker


def validate_daily_graphs_request(ticker: str, date: str) -> DailyGraphsRequest:
    normalized_ticker = validate_ticker(ticker)
    normalized_date = validate_date(date, field_name="date")
    return DailyGraphsRequest(ticker=normalized_ticker, date=normalized_date)


def validate_historical_graphs_request(
    ticker: str, period: int
) -> HistoricalGraphsRequest:
    normalized_ticker = validate_ticker(ticker)

    if period is None or not isinstance(period, int) or isinstance(period, bool):
        raise ValidationError(
            "Field 'period' is required and must be an integer "
            f"({' or '.join(str(p) for p in VALID_HISTORICAL_PERIODS)})."
        )

    if period not in VALID_HISTORICAL_PERIODS:
        raise ValidationError(
            "Field 'period' must be one of "
            f"{list(VALID_HISTORICAL_PERIODS)}.",
            details={"period": period},
        )

    return HistoricalGraphsRequest(ticker=normalized_ticker, period=period)


def validate_stock_price_request(
    ticker: str, start_date: str, end_date: str
) -> StockPriceRequest:
    normalized_ticker = validate_ticker(ticker)
    start, end = validate_date_range(start_date, end_date)
    return StockPriceRequest(ticker=normalized_ticker, start_date=start, end_date=end)
