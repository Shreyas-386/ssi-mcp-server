"""
Thin async REST client for the existing SSi Daily Graph APIs.

Per the HLD's "Key Architectural Decision", this client does nothing but
translate a validated request into an HTTPS GET call and hand back the raw
JSON body -- no sentiment/price calculation, no reinterpretation of fields.
Retries, timeouts and error mapping live here so tool implementations
(app/tools/*.py) stay focused on MCP protocol concerns.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import httpx

from app.config.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ENDPOINT_DAILY_GRAPHS,
    ENDPOINT_DAILY_GRAPHS_60_90_DAYS,
    ENDPOINT_STOCK_PRICE,
    RETRY_BACKOFF_BASE_SECONDS,
    RETRYABLE_STATUS_CODES,
)
from app.config.settings import get_settings
from app.services.auth import get_downstream_auth_headers
from app.utils.exceptions import DownstreamAPIError, DownstreamTimeoutError, DownstreamUnavailableError
from app.utils.helpers import build_query_params
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SSIApiClient:
    """Async client for the existing SSi REST API surface used by this server."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._base_url = settings.ssi_api_base_url
        self._timeout = settings.request_timeout_seconds
        self._max_retries = settings.max_retries
        # Allow an httpx.AsyncClient to be injected for testing (respx) while
        # defaulting to a real client in production.
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "SSIApiClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # --- Public API, one method per MCP tool -----------------------------------

    async def get_daily_graphs(self, ticker: str, request_date: date) -> dict[str, Any]:
        params = build_query_params({"ticker": ticker, "date": request_date.isoformat()})
        return await self._get(ENDPOINT_DAILY_GRAPHS, params)

    async def get_daily_graphs_60_90_days(self, ticker: str, period: int) -> dict[str, Any]:
        params = build_query_params({"ticker": ticker, "period": period})
        return await self._get(ENDPOINT_DAILY_GRAPHS_60_90_DAYS, params)

    async def get_stock_price(
        self, ticker: str, start_date: date, end_date: date
    ) -> dict[str, Any]:
        params = build_query_params(
            {
                "ticker": ticker,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        )
        return await self._get(ENDPOINT_STOCK_PRICE, params)

    # --- Internal request/retry/error-mapping machinery -------------------------

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = get_downstream_auth_headers()
        last_exc: Exception | None = None

        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.get(path, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "downstream_timeout", path=path, attempt=attempt, max_attempts=attempts
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "downstream_network_error",
                    path=path,
                    attempt=attempt,
                    max_attempts=attempts,
                    error=str(exc),
                )
            else:
                if response.status_code == 200:
                    return response.json()

                if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts:
                    logger.warning(
                        "downstream_retryable_status",
                        path=path,
                        status_code=response.status_code,
                        attempt=attempt,
                        max_attempts=attempts,
                    )
                else:
                    raise DownstreamAPIError(
                        f"Downstream SSi API returned HTTP {response.status_code}.",
                        details={
                            "path": path,
                            "status_code": response.status_code,
                            "body": _safe_body(response),
                        },
                    )

            if attempt < attempts:
                await asyncio.sleep(RETRY_BACKOFF_BASE_SECONDS * attempt)

        if isinstance(last_exc, httpx.TimeoutException):
            raise DownstreamTimeoutError(
                f"Downstream SSi API timed out after {attempts} attempt(s).",
                details={"path": path},
            ) from last_exc

        raise DownstreamUnavailableError(
            f"Downstream SSi API was unreachable after {attempts} attempt(s).",
            details={"path": path},
        ) from last_exc


def _safe_body(response: httpx.Response, limit: int = 500) -> str:
    """Truncate response bodies before they end up in logs/error details."""
    try:
        text = response.text
    except Exception:  # pragma: no cover - defensive
        return "<unreadable body>"
    return text[:limit]
