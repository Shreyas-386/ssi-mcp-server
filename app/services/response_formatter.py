"""
Parses raw downstream JSON into typed response models.

Earlier revisions of this module manually built the MCP
`content` / `structuredContent` envelope shown in the HLD's worked example.
That is no longer necessary: mcp>=1.10's FastMCP builds both automatically
from a tool function's return value, *provided* the function's return type
is annotated with a concrete model (see app/models/responses.py) rather than
a bare `dict`. Verified behavior (mcp==1.12.4): a tool returning a
`BaseModel` instance produces `structuredContent` equal to the model's own
fields, un-wrapped -- exactly the flat shape the HLD illustrates. Returning
a bare `dict[str, Any]` instead would get silently wrapped as
`{"result": {...}}`, which does *not* match the HLD.

This module's remaining job is simply: take the raw dict the downstream SSi
REST API returned, and validate/coerce it into the right response model so
the tool function can return that model directly.
"""

from __future__ import annotations

from typing import Any

from app.models.responses import (
    DailyGraphsResponse,
    HistoricalGraphsResponse,
    StockPriceResponse,
)


def parse_daily_graphs_response(data: dict[str, Any]) -> DailyGraphsResponse:
    return DailyGraphsResponse.model_validate(data)


def parse_historical_graphs_response(data: dict[str, Any]) -> HistoricalGraphsResponse:
    return HistoricalGraphsResponse.model_validate(data)


def parse_stock_price_response(data: dict[str, Any]) -> StockPriceResponse:
    return StockPriceResponse.model_validate(data)
