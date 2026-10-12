"""Deployment configuration fail-fast checks."""

import pytest

from app.config.settings import Settings
from app.config.startup import validate_settings


def test_stdio_development_allows_empty_secrets():
    settings = Settings(
        environment="development",
        transport="stdio",
        ssi_api_key="",
        mcp_auth_token="",
        require_client_auth=True,
    )
    validate_settings(settings)


def test_http_without_mcp_token_fails():
    settings = Settings(
        environment="development",
        transport="streamable-http",
        ssi_api_key="downstream",
        mcp_auth_token="",
        require_client_auth=True,
    )
    with pytest.raises(SystemExit) as exc:
        validate_settings(settings)
    assert exc.value.code == 1


def test_production_without_downstream_key_fails():
    settings = Settings(
        environment="production",
        transport="streamable-http",
        ssi_api_key="",
        mcp_auth_token="client-token",
        require_client_auth=True,
    )
    with pytest.raises(SystemExit):
        validate_settings(settings)


def test_production_http_with_secrets_passes():
    settings = Settings(
        environment="production",
        transport="streamable-http",
        ssi_api_key="downstream-key",
        mcp_auth_token="client-token",
        require_client_auth=True,
    )
    validate_settings(settings)


def test_http_auth_disabled_allows_empty_mcp_token():
    settings = Settings(
        environment="production",
        transport="streamable-http",
        ssi_api_key="downstream-key",
        mcp_auth_token="",
        require_client_auth=False,
    )
    validate_settings(settings)
