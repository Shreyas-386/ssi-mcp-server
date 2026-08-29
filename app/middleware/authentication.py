"""
ASGI middleware enforcing bearer-token authentication on the HTTP transport.

Only relevant when the server runs with `transport=streamable-http` (see
app/main.py); the stdio transport is invoked directly by a locally trusted
process (e.g. an MCP client spawning this server as a subprocess) and does
not go through an HTTP layer at all.

Kept as a small, swappable unit: replacing the bearer-token scheme with
OAuth (per the HLD's still-open decision) means changing this file and
app/services/auth.py without touching tool or transport code.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.config.constants import AUTH_HEADER
from app.services.auth import extract_bearer_token, verify_client_token
from app.utils.exceptions import AuthenticationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Paths that must remain reachable without authentication (load balancer /
# container orchestrator health checks, per "Health endpoint for monitoring").
_UNAUTHENTICATED_PATHS = frozenset({"/health", "/healthz"})


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.url.path in _UNAUTHENTICATED_PATHS:
            return await call_next(request)

        token = extract_bearer_token(request.headers.get(AUTH_HEADER))
        try:
            verify_client_token(token)
        except AuthenticationError as exc:
            logger.warning("client_authentication_failed", path=request.url.path)
            return JSONResponse(status_code=exc.http_status, content=exc.to_dict())

        return await call_next(request)


def apply_authentication_middleware(app: Starlette) -> Starlette:
    app.add_middleware(BearerTokenAuthMiddleware)
    return app
