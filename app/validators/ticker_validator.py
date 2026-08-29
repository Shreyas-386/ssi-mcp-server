"""Ticker symbol validation.

Kept isolated from date/request validation so it can be reused (and unit
tested) independently, and so tightening the ticker rules later doesn't risk
touching unrelated validation logic.
"""

from __future__ import annotations

import re

from app.config.constants import TICKER_MAX_LENGTH, TICKER_PATTERN
from app.utils.exceptions import ValidationError

_TICKER_RE = re.compile(TICKER_PATTERN)


def validate_ticker(ticker: str) -> str:
    """Validate and normalize a ticker symbol.

    Returns the normalized (uppercased, trimmed) ticker on success.
    Raises ValidationError with a client-safe message on failure.
    """
    if ticker is None or not isinstance(ticker, str):
        raise ValidationError("Field 'ticker' is required and must be a string.")

    normalized = ticker.strip().upper()

    if not normalized:
        raise ValidationError("Field 'ticker' must not be empty.")

    if len(normalized) > TICKER_MAX_LENGTH:
        raise ValidationError(
            f"Field 'ticker' must be at most {TICKER_MAX_LENGTH} characters.",
            details={"ticker": ticker},
        )

    if not _TICKER_RE.match(normalized):
        raise ValidationError(
            "Field 'ticker' must be a valid ticker symbol, e.g. 'AAPL' or 'BRK.B'.",
            details={"ticker": ticker},
        )

    return normalized
