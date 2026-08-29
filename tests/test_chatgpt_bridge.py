"""
Tests for the ChatGPT Custom Actions bridge (POST /chatgpt).

The bridge is a plain REST endpoint that does not go through FastMCP's
tool_manager or the @handle_tool_errors decorator, so its error mapping is
implemented in app/server.py directly and is verified here: each
SSIMCPError subclass must surface with its own HTTP status, and unexpected
exceptions must never leak internal detail to the caller.

Requests are driven through the Starlette app with auth disabled, so these
tests exercise routing + handler logic without the bearer middleware.
"""

import httpx
import pytest
import respx

from app.server import create_server


@pytest.fixture
async def http_client(monkeypatch):
    monkeypatch.setenv("REQUIRE_CLIENT_AUTH", "false")
    from app.config.settings import get_settings

    get_settings.cache_clear()

    mcp, api_client = create_server()
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await api_client.aclose()
    get_settings.cache_clear()


def _call(name, arguments):
    return {"method": "tools/call", "params": {"name": name, "arguments": arguments}}


@pytest.mark.asyncio
async def test_successful_call_returns_flat_json(http_client):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs").mock(
            return_value=httpx.Response(
                200, json={"ticker": "AAPL", "date": "2026-07-22", "sentimentScore": 0.42}
            )
        )
        response = await http_client.post(
            "/chatgpt", json=_call("get_daily_graphs", {"ticker": "AAPL", "date": "2026-07-22"})
        )

    assert response.status_code == 200
    body = response.json()
    # Flat object -- no MCP content/structuredContent envelope.
    assert body["ticker"] == "AAPL"
    assert body["sentimentScore"] == 0.42
    assert "structuredContent" not in body


@pytest.mark.asyncio
async def test_validation_error_returns_400_not_500(http_client):
    """A bad ticker is the caller's mistake, so it must not read as a server fault."""
    response = await http_client.post(
        "/chatgpt", json=_call("get_daily_graphs", {"ticker": "not a ticker!", "date": "2026-07-22"})
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.asyncio
async def test_downstream_error_returns_502(http_client):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs").mock(return_value=httpx.Response(500, text="boom"))
        response = await http_client.post(
            "/chatgpt", json=_call("get_daily_graphs", {"ticker": "AAPL", "date": "2026-07-22"})
        )

    assert response.status_code == 502
    assert response.json()["error_code"] == "downstream_api_error"


@pytest.mark.asyncio
async def test_unknown_tool_returns_404(http_client):
    response = await http_client.post("/chatgpt", json=_call("get_nonexistent", {}))

    assert response.status_code == 404
    assert response.json()["error_code"] == "unknown_tool"


@pytest.mark.asyncio
async def test_unsupported_method_returns_400(http_client):
    response = await http_client.post(
        "/chatgpt", json={"method": "tools/list", "params": {}}
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.asyncio
async def test_malformed_json_returns_400(http_client):
    response = await http_client.post(
        "/chatgpt", content=b"{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.asyncio
async def test_health_endpoint_is_unauthenticated(http_client):
    response = await http_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
