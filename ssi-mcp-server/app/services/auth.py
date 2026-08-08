"""
Authentication helpers.

Two distinct concerns live here, matching the two arrows in the HLD's
component diagram:

1. `verify_client_token` -- authenticates the *inbound* MCP client
   (AI Client -> SSi MCP Server), per "Client authentication" in the HLD's
   Security table. The HLD leaves the exact mechanism as an open decision
   ("Bearer token or OAuth"); this implementation ships the bearer-token
   option since it works uniformly across stdio and HTTP transports, and
   isolates the check here so swapping in OAuth later is a localized change.

2. `get_downstream_auth_headers` -- attaches the *outbound* credential
   (SSi MCP Server -> Daily Graph APIs), per "Downstream authentication".
"""

from __future__ import annotations

import hmac

from app.config.constants import AUTH_HEADER, BEARER_PREFIX
from app.config.settings import get_settings
from app.utils.exceptions import AuthenticationError


def verify_client_token(token: str | None) -> None:
    """Verify a bearer token presented by an MCP client.

    Uses a constant-time comparison to avoid leaking token contents through
    timing side channels. Raises AuthenticationError on any failure; callers
    should not distinguish "missing" from "wrong" in the message returned to
    the client, to avoid helping an attacker enumerate valid state.
    """
    settings = get_settings()

    if not settings.require_client_auth:
        return

    if not settings.mcp_auth_token:
        # Misconfiguration: auth is required but no token is configured.
        # Fail closed rather than silently accepting every request.
        raise AuthenticationError("Server authentication is not configured.")

    if not token:
        raise AuthenticationError("Missing or invalid authentication credentials.")

    if not hmac.compare_digest(token, settings.mcp_auth_token):
        raise AuthenticationError("Missing or invalid authentication credentials.")


def extract_bearer_token(authorization_header: str | None) -> str | None:
    """Pull the token out of a raw 'Authorization: Bearer <token>' header."""
    if not authorization_header:
        return None
    if not authorization_header.startswith(BEARER_PREFIX):
        return None
    return authorization_header[len(BEARER_PREFIX):].strip() or None


def get_downstream_auth_headers() -> dict[str, str]:
    """Build the Authorization header used when calling the SSi REST API."""
    settings = get_settings()
    return {AUTH_HEADER: f"{BEARER_PREFIX}{settings.ssi_api_key}"}
