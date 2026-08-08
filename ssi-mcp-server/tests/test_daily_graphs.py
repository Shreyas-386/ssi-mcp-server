"""
End-to-end tests for the `get_daily_graphs` tool.

These go through `mcp.call_tool(...)`, the same path a real MCP client
invokes, so they also verify the return-type-annotation -> structuredContent
wiring described in app/services/response_formatter.py, and that validation/
downstream errors surface as `ToolError` with structured JSON text (see
app/utils/exceptions.py).
"""

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
async def test_get_daily_graphs_returns_structured_content(server):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs", params={"ticker": "AAPL", "date": "2026-07-22"}).mock(
            return_value=httpx.Response(
                200,
                json={
                    "ticker": "AAPL",
                    "date": "2026-07-22",
                    "sentimentScore": 0.42,
                    "buzzScore": 0.71,
                    "narrativeTags": ["earnings", "guidance"],
                },
            )
        )
        content, structured = await server.call_tool(
            "get_daily_graphs", {"ticker": "aapl", "date": "2026-07-22"}
        )

        assert structured["ticker"] == "AAPL"
        assert structured["sentimentScore"] == 0.42
        assert structured["narrativeTags"] == ["earnings", "guidance"]
        assert content[0].type == "text"
        assert "sentimentScore" in content[0].text


@pytest.mark.asyncio
async def test_get_daily_graphs_rejects_invalid_ticker(server):
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("get_daily_graphs", {"ticker": "$$$", "date": "2026-07-22"})

    assert "validation_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_daily_graphs_rejects_malformed_date(server):
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("get_daily_graphs", {"ticker": "AAPL", "date": "07/22/2026"})

    assert "validation_error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_daily_graphs_surfaces_downstream_error(server):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs").mock(return_value=httpx.Response(500))
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "get_daily_graphs", {"ticker": "AAPL", "date": "2026-07-22"}
            )

    assert "downstream_api_error" in str(exc_info.value)
