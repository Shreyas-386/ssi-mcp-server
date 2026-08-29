"""
Environment-driven configuration.

Per the HLD's "Secrets management" requirement, all secrets (API keys,
tokens) are sourced from environment variables / a `.env` file and are never
hard-coded. `Settings` is a singleton accessed via `get_settings()`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Environment -------------------------------------------------------
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment; drives logging verbosity and defaults.",
    )
    log_level: str = Field(default="INFO")

    # --- Downstream SSi REST API --------------------------------------------
    ssi_api_base_url: str = Field(
        default="https://dailygraphs.finsoftai.com",
        description="Base URL of the existing SSi REST API platform.",
    )
    ssi_api_key: str = Field(
        default="",
        description="Downstream service credential (internal API key / bearer token).",
    )
    request_timeout_seconds: float = Field(default=10.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=5)

    # --- MCP client authentication ------------------------------------------
    # Open decision per the HLD ("Bearer token or OAuth, to be finalized").
    # This implementation defaults to a static bearer token, which is the
    # simplest option compatible with both stdio and HTTP transports; swapping
    # in OAuth later only touches app/middleware/authentication.py and
    # app/services/auth.py.
    mcp_auth_token: str = Field(
        default="",
        description="Shared-secret bearer token MCP clients must present over HTTP transport.",
    )
    require_client_auth: bool = Field(
        default=True,
        description="If False, skips bearer-token enforcement (local/dev stdio use only).",
    )

    # --- Transport / hosting --------------------------------------------------
    transport: Literal["stdio", "streamable-http"] = Field(default="stdio")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)

    @field_validator("ssi_api_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def _uppercase_log_level(cls, value: str) -> str:
        return value.upper()


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use this everywhere instead of instantiating
    Settings() directly, so the whole process shares one parsed configuration."""
    return Settings()
