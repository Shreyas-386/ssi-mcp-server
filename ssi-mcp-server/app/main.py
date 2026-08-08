"""
Application entry point.

Chooses a transport based on configuration:

- `stdio` (default): the server is spawned as a local subprocess by an MCP
  client and communicates over stdin/stdout. No network exposure, no bearer
  token needed by default -- appropriate for local development.
- `streamable-http`: the server is deployed as "an independent, stateless
  service behind a reverse proxy / load balancer" (per the HLD's Deployment
  Architecture) with "a publicly reachable HTTPS MCP endpoint" for ChatGPT
  Integration. In this mode we wrap the ASGI app with bearer-token auth
  middleware and serve it with uvicorn.
"""

from __future__ import annotations

import asyncio

from app.config.settings import get_settings
from app.middleware.authentication import apply_authentication_middleware
from app.server import create_server
from app.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)


async def _run_stdio() -> None:
    mcp, client = create_server()
    try:
        await mcp.run_stdio_async()
    finally:
        await client.aclose()


def _run_http() -> None:
    import uvicorn

    settings = get_settings()
    mcp, _client = create_server()

    app = mcp.streamable_http_app()
    if settings.require_client_auth:
        app = apply_authentication_middleware(app)
    else:
        logger.warning("client_auth_disabled", transport="streamable-http")

    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


def main() -> None:
    configure_logging()
    settings = get_settings()

    if settings.transport == "stdio":
        asyncio.run(_run_stdio())
    else:
        _run_http()


if __name__ == "__main__":
    main()
