"""
Fail-fast checks before the server binds a port or enters the MCP loop.

Catches misconfiguration at process start (container orchestrator restart
loops, CI smoke tests) instead of at the first authenticated request.
"""

from __future__ import annotations

import sys

from app.config.settings import Settings


def validate_settings(settings: Settings) -> None:
    errors: list[str] = []

    if (
        settings.transport == "streamable-http"
        and settings.require_client_auth
        and not settings.mcp_auth_token.strip()
    ):
        errors.append(
            "MCP_AUTH_TOKEN must be set when TRANSPORT=streamable-http and "
            "REQUIRE_CLIENT_AUTH=true."
        )

    if settings.environment in ("staging", "production"):
        if not settings.ssi_api_key.strip():
            errors.append(
                f"SSI_API_KEY is required when ENVIRONMENT={settings.environment}."
            )

    if errors:
        message = "Invalid configuration:\n  - " + "\n  - ".join(errors)
        print(message, file=sys.stderr)
        raise SystemExit(1)
