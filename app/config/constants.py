"""
Static, non-environment-specific constants.

Anything that varies per-deployment (URLs, credentials, timeouts) lives in
`settings.py` instead. This module only holds values that are part of the
contract between this server and the downstream SSi REST APIs.
"""

# --- Downstream SSi REST endpoints ------------------------------------------------
# These map 1:1 to the "Scope and MCP Tools" table in the HLD. The MCP server
# never changes these paths at runtime; if SSi renames an endpoint, this is the
# single place to update it.
ENDPOINT_DAILY_GRAPHS = "/daily-graphs"
ENDPOINT_DAILY_GRAPHS_60_90_DAYS = "/daily-graphs-60-90-days"
ENDPOINT_STOCK_PRICE = "/daily-graphs-stockprice"

# --- MCP tool names -----------------------------------------------------------
# Names as published to MCP clients (must match the HLD's "Scope and MCP Tools").
TOOL_GET_DAILY_GRAPHS = "get_daily_graphs"
TOOL_GET_DAILY_GRAPHS_60_90_DAYS = "get_daily_graphs_60_90_days"
TOOL_GET_STOCK_PRICE = "get_stock_price"

# --- Validation rules -----------------------------------------------------------
# Tickers: 1-10 chars, uppercase letters/digits, optional single "." or "-"
# class share suffix (e.g. BRK.B, RDS-A). Kept permissive but bounded.
TICKER_MAX_LENGTH = 10
TICKER_PATTERN = r"^[A-Z]{1,10}([.\-][A-Z]{1,3})?$"

# Dates: ISO-8601 calendar date, e.g. 2026-07-22
DATE_FORMAT = "%Y-%m-%d"

# SSi platform did not publish market sentiment data before this date; used as
# a sanity lower bound so obviously-wrong input fails fast instead of hitting
# the downstream API.
EARLIEST_VALID_DATE = "2015-01-01"

# Historical sentiment lookback windows the /daily-graphs-60-90-days endpoint
# supports, per the HLD ("Retrieve 60-day and 90-day historical sentiment data").
VALID_HISTORICAL_PERIODS = (60, 90)

# Maximum span (in days) allowed for a single stock-price range request, to
# keep downstream calls bounded and predictable.
MAX_STOCK_PRICE_RANGE_DAYS = 365

# --- HTTP -----------------------------------------------------------------------
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
RETRY_BACKOFF_BASE_SECONDS = 0.5
RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})

AUTH_HEADER = "Authorization"
BEARER_PREFIX = "Bearer "
