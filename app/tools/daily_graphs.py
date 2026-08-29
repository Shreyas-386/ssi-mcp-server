"""
`get_daily_graphs` MCP tool.

Maps directly to the existing GET /daily-graphs REST endpoint, per the HLD's
"Scope and MCP Tools" table and the worked example in "Example:
get_daily_graphs Request and Response".
"""

# NOTE: deliberately no `from __future__ import annotations` here. FastMCP
# inspects this module's tool function signatures at registration time with
# raw `inspect.signature()` (not `typing.get_type_hints()`), so postponed
# evaluation would turn annotations into strings and break its runtime
# `issubclass(annotation, Context)` check (verified against mcp==1.12.4).

from mcp.server.fastmcp import FastMCP

from app.config.constants import TOOL_GET_DAILY_GRAPHS
from app.middleware.error_handler import handle_tool_errors
from app.models.responses import DailyGraphsResponse
from app.services.api_client import SSIApiClient
from app.services.response_formatter import parse_daily_graphs_response
from app.validators.request_validator import validate_daily_graphs_request


def register(mcp: FastMCP, api_client: SSIApiClient) -> None:
    @mcp.tool(
        name=TOOL_GET_DAILY_GRAPHS,
        description=(
            "Retrieve SSi Daily Graphs data (sentiment/buzz metrics) for a "
            "single ticker on a single date."
        ),
    )
    @handle_tool_errors(TOOL_GET_DAILY_GRAPHS)
    async def get_daily_graphs(ticker: str, date: str) -> DailyGraphsResponse:
        """
        Args:
            ticker: Stock ticker symbol, e.g. "AAPL".
            date: ISO-8601 date (YYYY-MM-DD) to fetch data for.
        """
        # NOTE: the return type annotation above is load-bearing -- FastMCP
        # uses it to build the tool's structuredContent automatically. Do
        # not widen it to `dict`; see app/services/response_formatter.py.
        request = validate_daily_graphs_request(ticker=ticker, date=date)
        data = await api_client.get_daily_graphs(request.ticker, request.date)
        return parse_daily_graphs_response(data)
