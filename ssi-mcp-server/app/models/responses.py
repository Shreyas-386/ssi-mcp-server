"""
Response models.

The HLD is explicit that "Field names below are illustrative; the
authoritative schema will live in the Tool Definitions deliverable." Rather
than lock this server to a schema that may drift, these models validate only
the fields we know are stable (ticker, and for graphs endpoints, the date/
period echoed back) and pass everything else the downstream API returns
straight through via `extra="allow"`. This keeps the MCP layer thin, per the
HLD's "Key Architectural Decision": it must not reinterpret or recompute
SSi's data.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class DownstreamResponseBase(BaseModel):
    """Base for any payload passed through from a downstream SSi REST call."""

    model_config = ConfigDict(extra="allow")

    ticker: str


class DailyGraphsResponse(DownstreamResponseBase):
    """Passthrough model for GET /daily-graphs responses."""

    date: str | None = None


class HistoricalGraphsResponse(DownstreamResponseBase):
    """Passthrough model for GET /daily-graphs-60-90-days responses."""

    period: int | None = None


class StockPriceResponse(DownstreamResponseBase):
    """Passthrough model for GET /daily-graphs-stockprice responses."""

    start_date: str | None = None
    end_date: str | None = None


class ErrorResponse(BaseModel):
    """Structured error shape returned to MCP clients on failure."""

    error_code: str
    message: str
    details: dict[str, Any] | None = None
