"""
Structured logging setup.

Per the HLD's "Logging" requirement: record tool name, request time, status,
latency and error category, and never log secrets. We use `structlog` so
every log line is a JSON object suitable for centralized log aggregation
("Centralized logs and basic metrics" under Deployment Characteristics).
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config.settings import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotently configure structlog + stdlib logging for the process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.environment == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger. Safe to call at import time."""
    configure_logging()
    return structlog.get_logger(name)
