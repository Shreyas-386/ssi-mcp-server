"""
`get_stock_price` MCP tool.

Maps to the existing GET /daily-graphs-stockprice REST endpoint, per the
HLD's "Scope and MCP Tools" table ("Retrieve historical stock-price data").
"""

# NOTE: deliberately no `from __future__ import annotations` here -- see the
# comment in app/tools/daily_graphs.py for why.

from mcp.server.fastmcp import FastMCP

from app.config.constants import MAX_STOCK_PRICE_RANGE_DAYS, TOOL_GET_STOCK_PRICE
from app.middleware.error_handler import handle_tool_errors
from app.models.responses import StockPriceResponse
from app.services.api_client import SSIApiClient
from app.services.response_formatter import parse_stock_price_response
from app.validators.request_validator import validate_stock_price_request


def register(mcp: FastMCP, api_client: SSIApiClient) -> None:
    @mcp.tool(
        name=TOOL_GET_STOCK_PRICE,
        description=(
            "Retrieve historical SSi stock-price data for a ticker between "
            f"two dates (max {MAX_STOCK_PRICE_RANGE_DAYS}-day range)."
        ),
    )
    @handle_tool_errors(TOOL_GET_STOCK_PRICE)
    async def get_stock_price(
        ticker: str, start_date: str, end_date: str
    ) -> StockPriceResponse:
        """
        Args:
            ticker: Stock ticker symbol, e.g. "AAPL".
            start_date: ISO-8601 date (YYYY-MM-DD), inclusive range start.
            end_date: ISO-8601 date (YYYY-MM-DD), inclusive range end.
        """
        request = validate_stock_price_request(
            ticker=ticker, start_date=start_date, end_date=end_date
        )
        data = await api_client.get_stock_price(
            request.ticker, request.start_date, request.end_date
        )
        return parse_stock_price_response(data)
