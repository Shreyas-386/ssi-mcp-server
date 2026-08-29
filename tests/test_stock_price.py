"""End-to-end tests for the `get_stock_price` tool (see test_daily_graphs.py
for notes on why these go through `mcp.call_tool`)."""

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from app.server import create_server


@pytest.fixture
async def server():
    mcp, client = create_server()
    yield mcp
    await client.aclose()


@pytest.mark.asyncio
async def test_get_stock_price_returns_structured_content(server):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get(
            "/daily-graphs-stockprice",
            params={"ticker": "AAPL", "start_date": "2026-01-01", "end_date": "2026-01-31"},
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "ticker": "AAPL",
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "prices": [{"date": "2026-01-02", "close": 191.23}],
                },
            )
        )
        content, structured = await server.call_tool(
            "get_stock_price",
            {"ticker": "aapl", "start_date": "2026-01-01", "end_date": "2026-01-31"},
        )

        assert structured["ticker"] == "AAPL"
        assert structured["prices"][0]["close"] == 191.23
        assert content[0].type == "text"


@pytest.mark.asyncio
async def test_get_stock_price_rejects_inverted_range(server):
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(
            "get_stock_price",
            {"ticker": "AAPL", "start_date": "2026-02-01", "end_date": "2026-01-01"},
        )

    assert "validation_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_stock_price_rejects_range_exceeding_max_span(server):
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(
            "get_stock_price",
            {"ticker": "AAPL", "start_date": "2015-01-01", "end_date": "2025-01-01"},
        )

    assert "validation_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_stock_price_surfaces_downstream_timeout(server):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs-stockprice").mock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "get_stock_price",
                {"ticker": "AAPL", "start_date": "2026-01-01", "end_date": "2026-01-31"},
            )

    assert "downstream_timeout" in str(exc_info.value)
