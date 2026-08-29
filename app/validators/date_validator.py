"""Date and date-range validation.

All dates exchanged with MCP clients and with the downstream SSi REST APIs
use plain ISO-8601 calendar dates (YYYY-MM-DD), no time component.
"""

from __future__ import annotations

from datetime import date, datetime

from app.config.constants import (
    DATE_FORMAT,
    EARLIEST_VALID_DATE,
    MAX_STOCK_PRICE_RANGE_DAYS,
)
from app.utils.exceptions import ValidationError

_EARLIEST = datetime.strptime(EARLIEST_VALID_DATE, DATE_FORMAT).date()


def validate_date(value: str, *, field_name: str = "date") -> date:
    """Parse and sanity-check a single ISO-8601 date string.

    Rejects malformed strings, dates before EARLIEST_VALID_DATE, and dates in
    the future (SSi sentiment/price data is necessarily historical).
    """
    if value is None or not isinstance(value, str):
        raise ValidationError(f"Field '{field_name}' is required and must be a string.")

    try:
        parsed = datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValidationError(
            f"Field '{field_name}' must be an ISO-8601 date (YYYY-MM-DD).",
            details={field_name: value},
        ) from exc

    if parsed < _EARLIEST:
        raise ValidationError(
            f"Field '{field_name}' must not be earlier than {EARLIEST_VALID_DATE}.",
            details={field_name: value},
        )

    if parsed > date.today():
        raise ValidationError(
            f"Field '{field_name}' must not be in the future.",
            details={field_name: value},
        )

    return parsed


def validate_date_range(start_value: str, end_value: str) -> tuple[date, date]:
    """Validate a start/end date pair for range-based tools (e.g. stock price)."""
    start = validate_date(start_value, field_name="start_date")
    end = validate_date(end_value, field_name="end_date")

    if start > end:
        raise ValidationError(
            "Field 'start_date' must not be after 'end_date'.",
            details={"start_date": start_value, "end_date": end_value},
        )

    span_days = (end - start).days
    if span_days > MAX_STOCK_PRICE_RANGE_DAYS:
        raise ValidationError(
            f"Date range must not exceed {MAX_STOCK_PRICE_RANGE_DAYS} days "
            f"(requested {span_days} days).",
            details={"start_date": start_value, "end_date": end_value},
        )

    return start, end
