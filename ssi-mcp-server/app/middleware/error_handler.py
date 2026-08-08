"""
Centralized logging + exception normalization for MCP tool functions.

Important: this decorator does **not** catch-and-convert errors into a
"successful" return value. The mcp SDK's own tool-call handling already
turns any exception raised out of a tool function into a proper
`CallToolResult(isError=True, ...)` (verified against mcp==1.12.4's
`Tool.run` / lowlevel `call_tool` handler) -- if this decorator instead
caught exceptions and returned a dict, that dict would be serialized as a
*successful* result, silently misreporting failures to the client. So the
job here is narrower:

1. Log every invocation (start, success, failure) with tool name, latency,
   and error category -- satisfying the HLD's "Logging" requirement.
2. Let `SSIMCPError` subclasses (validation, auth, downstream errors)
   propagate unchanged -- their `__str__` already emits structured JSON
   (see app/utils/exceptions.py).
3. Catch anything *unexpected* and re-raise it as a generic `SSIMCPError`,
   so a bug never leaks an internal stack trace or message to the client.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Awaitable, Callable, TypeVar

from app.utils.exceptions import SSIMCPError
from app.utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def handle_tool_errors(tool_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            logger.info("tool_invoked", tool=tool_name)

            try:
                result = await func(*args, **kwargs)
            except SSIMCPError as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.warning(
                    "tool_failed",
                    tool=tool_name,
                    error_category=exc.error_code,
                    latency_ms=latency_ms,
                )
                raise
            except Exception as exc:  # noqa: BLE001 - last-resort safety net
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.error(
                    "tool_unexpected_error",
                    tool=tool_name,
                    error_category="internal_error",
                    latency_ms=latency_ms,
                    error=str(exc),
                )
                raise SSIMCPError(
                    "An unexpected error occurred while processing this request."
                ) from exc
            else:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                logger.info(
                    "tool_succeeded", tool=tool_name, status="ok", latency_ms=latency_ms
                )
                return result

        return wrapper  # type: ignore[return-value]

    return decorator
