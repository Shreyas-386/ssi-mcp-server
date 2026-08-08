"""
FastMCP server construction.

This module wires together settings, the downstream API client, and the
three published tools. It intentionally contains no business logic of its
own -- per the HLD's "Key Architectural Decision", this whole server is an
adapter, and `create_server()` is where the adapter's parts get assembled.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import get_settings
from app.services.api_client import SSIApiClient
from app.tools import daily_graphs, historical_graphs, stock_price
from app.utils.logger import get_logger

logger = get_logger(__name__)

SERVER_NAME = "ssi-mcp-server"
SERVER_INSTRUCTIONS = (
    "Exposes SSi Social Sentiment Insights data (daily sentiment graphs, "
    "60/90-day historical sentiment, and historical stock price) as MCP "
    "tools. This server is a thin adapter over existing SSi REST APIs and "
    "performs no analytics of its own."
)


def create_server(api_client: SSIApiClient | None = None) -> tuple[FastMCP, SSIApiClient]:
    """Build a configured FastMCP instance with all tools registered.

    Returns the server plus the API client it owns, so callers (main.py,
    tests) can manage the client's lifecycle (e.g. closing it on shutdown).
    """
    settings = get_settings()
    mcp = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        host=settings.host,
        port=settings.port,
    )

    client = api_client or SSIApiClient()

    daily_graphs.register(mcp, client)
    historical_graphs.register(mcp, client)
    stock_price.register(mcp, client)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        """Health endpoint for load balancer / orchestrator monitoring."""
        return JSONResponse({"status": "ok", "service": SERVER_NAME})

    logger.info(
        "server_initialized",
        transport=settings.transport,
        environment=settings.environment,
        tools=[
            "get_daily_graphs",
            "get_daily_graphs_60_90_days",
            "get_stock_price",
        ],
    )

    return mcp, client
