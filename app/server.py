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
from app.validators.request_validator import (
    validate_daily_graphs_request,
    validate_historical_graphs_request,
    validate_stock_price_request,
)
from app.services.response_formatter import (
    parse_daily_graphs_response,
    parse_historical_graphs_response,
    parse_stock_price_response,
)
from app.utils.exceptions import SSIMCPError
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
        stateless_http=True,
    )

    client = api_client or SSIApiClient()

    daily_graphs.register(mcp, client)
    historical_graphs.register(mcp, client)
    stock_price.register(mcp, client)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        """Health endpoint for load balancer / orchestrator monitoring."""
        return JSONResponse({"status": "ok", "service": SERVER_NAME})

    @mcp.custom_route("/chatgpt", methods=["POST"])
    async def chatgpt(request: Request) -> JSONResponse:
        """Dedicated stateless REST endpoint for ChatGPT Custom Actions."""
        name: str | None = None
        try:
            try:
                body = await request.json()
            except ValueError:
                return JSONResponse(
                    {"error_code": "validation_error", "message": "Request body must be valid JSON."},
                    status_code=400,
                )
            if body.get("method") != "tools/call":
                return JSONResponse(
                    {"error_code": "validation_error", "message": "Only 'tools/call' is supported."},
                    status_code=400,
                )

            params = body.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "get_daily_graphs":
                req = validate_daily_graphs_request(ticker=args.get("ticker"), date=args.get("date"))
                data = await client.get_daily_graphs(req.ticker, req.date)
                resp = parse_daily_graphs_response(data)
                return JSONResponse(resp.model_dump())
            elif name == "get_daily_graphs_60_90_days":
                req = validate_historical_graphs_request(ticker=args.get("ticker"), period=args.get("period"))
                data = await client.get_daily_graphs_60_90_days(req.ticker, req.period)
                resp = parse_historical_graphs_response(data)
                return JSONResponse(resp.model_dump())
            elif name == "get_stock_price":
                req = validate_stock_price_request(ticker=args.get("ticker"), start_date=args.get("start_date"), end_date=args.get("end_date"))
                data = await client.get_stock_price(req.ticker, req.start_date, req.end_date)
                resp = parse_stock_price_response(data)
                return JSONResponse(resp.model_dump())
            else:
                return JSONResponse(
                    {"error_code": "unknown_tool", "message": f"Unknown tool: {name}"},
                    status_code=404,
                )
        except SSIMCPError as exc:
            # Every SSIMCPError subclass already carries the correct HTTP
            # status (400 validation, 401 auth, 502/503/504 downstream), so
            # the bridge returns real REST semantics instead of collapsing
            # every failure into a 500. The MCP path gets the equivalent
            # distinction from the SDK's isError handling.
            logger.warning(
                "chatgpt_endpoint_error",
                tool=name,
                error_code=exc.error_code,
                status_code=exc.http_status,
            )
            return JSONResponse(exc.to_dict(), status_code=exc.http_status)
        except Exception as exc:
            # Never leak internal exception text to the client -- the same
            # guarantee handle_tool_errors() provides on the MCP path.
            logger.error("chatgpt_endpoint_unexpected_error", tool=name, error=str(exc))
            return JSONResponse(
                {
                    "error_code": "internal_error",
                    "message": "An unexpected error occurred while processing this request.",
                },
                status_code=500,
            )

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
