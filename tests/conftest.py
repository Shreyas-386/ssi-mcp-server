import os

import pytest

# Ensure predictable settings for every test regardless of local .env state.
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SSI_API_BASE_URL", "https://api.ssi.test")
os.environ.setdefault("SSI_API_KEY", "test-downstream-key")
os.environ.setdefault("MCP_AUTH_TOKEN", "test-client-token")
os.environ.setdefault("REQUIRE_CLIENT_AUTH", "true")
os.environ.setdefault("TRANSPORT", "stdio")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Settings are cached with lru_cache; clear between tests that tweak env vars."""
    from app.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
