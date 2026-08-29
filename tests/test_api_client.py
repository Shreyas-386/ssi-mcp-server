from datetime import date

import httpx
import pytest
import respx

from app.services.api_client import SSIApiClient
from app.utils.exceptions import DownstreamAPIError, DownstreamTimeoutError


@pytest.fixture
async def client():
    async_client = httpx.AsyncClient(base_url="https://api.ssi.test")
    api_client = SSIApiClient(client=async_client)
    yield api_client
    await async_client.aclose()


@pytest.mark.asyncio
async def test_get_daily_graphs_success(client):
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
        result = await client.get_daily_graphs("AAPL", date(2026, 7, 22))
        assert result["sentimentScore"] == 0.42
        assert result["narrativeTags"] == ["earnings", "guidance"]


@pytest.mark.asyncio
async def test_get_stock_price_maps_4xx_to_downstream_error(client):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs-stockprice").mock(
            return_value=httpx.Response(404, json={"message": "ticker not found"})
        )
        with pytest.raises(DownstreamAPIError):
            await client.get_stock_price("ZZZZ", date(2026, 1, 1), date(2026, 1, 31))


@pytest.mark.asyncio
async def test_retries_on_retryable_status_then_succeeds(client):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        route = mock.get("/daily-graphs-60-90-days").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json={"ticker": "AAPL", "period": 60, "points": []}),
            ]
        )
        result = await client.get_daily_graphs_60_90_days("AAPL", 60)
        assert result["ticker"] == "AAPL"
        assert route.call_count == 2


@pytest.mark.asyncio
async def test_timeout_raises_downstream_timeout_error(client):
    with respx.mock(base_url="https://api.ssi.test") as mock:
        mock.get("/daily-graphs").mock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(DownstreamTimeoutError):
            await client.get_daily_graphs("AAPL", date(2026, 7, 22))
