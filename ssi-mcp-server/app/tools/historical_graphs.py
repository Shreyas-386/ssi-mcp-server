"""
`get_daily_graphs_60_90_days` MCP tool.

Maps to the existing GET /daily-graphs-60-90-days REST endpoint, per the
HLD's "Scope and MCP Tools" table ("Retrieve 60-day and 90-day historical
sentiment data").
"""

# NOTE: deliberately no `from __future__ import annotations` here -- see the
# comment in app/tools/daily_graphs.py for why.

from mcp.server.fastmcp import FastMCP

from app.config.constants import TOOL_GET_DAILY_GRAPHS_60_90_DAYS, VALID_HISTORICAL_PERIODS
from app.middleware.error_handler import handle_tool_errors
from app.models.responses import HistoricalGraphsResponse
from app.services.api_client import SSIApiClient
from app.services.response_formatter import parse_historical_graphs_response
from app.validators.request_validator import validate_historical_graphs_request


def register(mcp: FastMCP, api_client: SSIApiClient) -> None:
    @mcp.tool(
        name=TOOL_GET_DAILY_GRAPHS_60_90_DAYS,
        description=(
            "Retrieve 60-day or 90-day historical SSi sentiment data for a "
            f"ticker. Valid periods: {list(VALID_HISTORICAL_PERIODS)}."
        ),
    )
    @handle_tool_errors(TOOL_GET_DAILY_GRAPHS_60_90_DAYS)
    async def get_daily_graphs_60_90_days(
        ticker: str, period: int
    ) -> HistoricalGraphsResponse:
        """
        Args:
            ticker: Stock ticker symbol, e.g. "AAPL".
            period: Lookback window in days -- 60 or 90.
        """
        request = validate_historical_graphs_request(ticker=ticker, period=period)
        data = await api_client.get_daily_graphs_60_90_days(request.ticker, request.period)
        return parse_historical_graphs_response(data)
