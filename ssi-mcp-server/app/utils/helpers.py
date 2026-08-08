"""Small, dependency-free helper functions shared across the codebase."""

from __future__ import annotations

import time
from typing import Any


def mask_secret(value: str | None, visible_chars: int = 4) -> str:
    """Mask a secret for safe logging, e.g. 'sk-live-abc123' -> '****c123'.

    Used to satisfy the HLD's "avoid logging secrets" requirement while still
    letting operators confirm *which* credential was used during debugging.
    """
    if not value:
        return "<empty>"
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def build_query_params(params: dict[str, Any]) -> dict[str, Any]:
    """Drop None values so they never leak into the downstream query string."""
    return {key: value for key, value in params.items() if value is not None}


def start_timer() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
