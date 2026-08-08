"""
Custom exception hierarchy.

The HLD requires "concise, structured errors for invalid input,
authentication failures, timeouts and downstream API failures". Each
exception carries a stable `error_code` (used in logs and in the MCP error
payload) and an `http_status` (used only if/when the server is fronted by an
HTTP transport / reverse proxy that inspects status codes).
"""

from __future__ import annotations

import json


class SSIMCPError(Exception):
    """Base class for all errors raised by this server.

    Note on how this surfaces to MCP clients: the mcp SDK's tool-call
    machinery catches *any* exception raised out of a tool function, wraps it
    as `ToolError(f"Error executing tool {name}: {e}")`, and returns it to
    the client as a single TextContent block with isError=True (verified
    against mcp==1.12.4). That wrapping is outside this server's control, so
    `__str__` is overridden to emit compact JSON -- the client-visible text
    ends up as `Error executing tool <name>: {"error_code": ..., "message":
    ...}`, which keeps the HLD's "concise, structured errors" requirement
    intact (the JSON is trivially extractable) despite the human-readable
    prefix the SDK adds.
    """

    error_code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        payload = {"error_code": self.error_code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload

    def __str__(self) -> str:  # noqa: D105
        return json.dumps(self.to_dict())


class ValidationError(SSIMCPError):
    """Raised when tool arguments fail validation before any downstream call."""

    error_code = "validation_error"
    http_status = 400


class AuthenticationError(SSIMCPError):
    """Raised when the MCP client fails to authenticate to this server."""

    error_code = "authentication_error"
    http_status = 401


class DownstreamAPIError(SSIMCPError):
    """Raised when the downstream SSi REST API returns an error response."""

    error_code = "downstream_api_error"
    http_status = 502


class DownstreamTimeoutError(SSIMCPError):
    """Raised when the downstream SSi REST API does not respond in time."""

    error_code = "downstream_timeout"
    http_status = 504


class DownstreamUnavailableError(SSIMCPError):
    """Raised when the downstream SSi REST API is unreachable (network error)."""

    error_code = "downstream_unavailable"
    http_status = 503
