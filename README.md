# SSi MCP Server

A thin, secure MCP (Model Context Protocol) adapter that exposes three
existing SSi REST APIs as MCP tools, per the SSi MCP Server HLD (v3.0).

This server performs **no analytics or business logic** of its own. It
validates input, calls the existing SSi REST APIs, and translates the
results into MCP-compliant tool responses. All sentiment/price calculation
continues to live in the SSi platform.

## Tools published

| MCP Tool | Existing REST Endpoint | Purpose |
| --- | --- | --- |
| `get_daily_graphs` | `GET /daily-graphs` | Daily sentiment/buzz data for one ticker + date. |
| `get_daily_graphs_60_90_days` | `GET /daily-graphs-60-90-days` | 60- or 90-day historical sentiment for one ticker. |
| `get_stock_price` | `GET /daily-graphs-stockprice` | Historical stock price for one ticker over a date range. |

## Project layout

```
ssi-mcp-server/
├── app/
│   ├── main.py                  # Entry point (chooses stdio vs HTTP transport)
│   ├── server.py                # FastMCP server construction + tool registration
│   ├── config/
│   │   ├── settings.py          # Environment-driven configuration (pydantic-settings)
│   │   └── constants.py         # Endpoint paths, validation rules, tool names
│   ├── tools/                   # One MCP tool per file
│   ├── services/
│   │   ├── api_client.py        # Async HTTP client for the downstream SSi REST APIs
│   │   ├── auth.py               # Client (inbound) and downstream (outbound) auth
│   │   └── response_formatter.py # Parses downstream JSON into typed response models
│   ├── validators/               # Ticker / date / per-tool request validation
│   ├── models/                   # Pydantic request + response models
│   ├── utils/                    # Exceptions, structured logging, small helpers
│   └── middleware/
│       ├── authentication.py     # Bearer-token ASGI middleware (HTTP transport only)
│       └── error_handler.py      # Per-tool logging + exception normalization
├── tests/
├── .env.example                  # Config template (copy to .env, git-ignored)
├── requirements.txt
├── run.py
└── README.md
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values
```

Set the required environment variables (see `.env.example` for the full
list and defaults):

| Variable | Required | Description |
| --- | --- | --- |
| `SSI_API_BASE_URL` | No (defaults to the SSi production host) | Base URL of the existing SSi REST API. |
| `SSI_API_KEY` | Yes | Downstream service credential sent to the SSi REST API. |
| `MCP_AUTH_TOKEN` | Yes (HTTP transport) | Bearer token MCP clients must present. |
| `REQUIRE_CLIENT_AUTH` | No (default `true`) | Set `false` to disable auth for local stdio dev. |
| `TRANSPORT` | No (default `stdio`) | `stdio` or `streamable-http`. |
| `HOST` / `PORT` | No | Bind address for `streamable-http`. |
| `LOG_LEVEL` | No (default `INFO`) | Standard Python log level name. |
| `ENVIRONMENT` | No (default `development`) | `development` \| `staging` \| `production`. |

Secrets are never hard-coded; see `app/config/settings.py`.

## Running

**Local development (stdio)** — the mode an MCP client typically spawns as a
subprocess:

```bash
python run.py
```

**Deployed / HTTP** — "a publicly reachable HTTPS MCP endpoint" per the
HLD's ChatGPT Integration section (put a reverse proxy / TLS terminator in
front of this in production):

```bash
TRANSPORT=streamable-http python run.py
```

The MCP endpoint is served at `/mcp`. A plain REST bridge for ChatGPT
Custom Actions (which cannot speak the MCP wire protocol) is served at
`POST /chatgpt`, behind the same bearer-token auth. A health check for load
balancers / orchestrators is served at `/health` (unauthenticated).

## Authentication

- **Client → this server**: bearer token, checked in
  `app/middleware/authentication.py` for the HTTP transport (stdio is
  invoked by a locally trusted process and is not authenticated the same
  way). The HLD leaves the client-auth mechanism as an open decision
  ("Bearer token or OAuth"); this implementation ships the bearer-token
  option and isolates it so OAuth can be swapped in later without touching
  tool or transport code.
- **This server → SSi REST API**: internal API key / service credential,
  attached in `app/services/auth.py`.

## Error handling

Tool functions raise typed exceptions from `app/utils/exceptions.py`
(`ValidationError`, `AuthenticationError`, `DownstreamAPIError`,
`DownstreamTimeoutError`, `DownstreamUnavailableError`). The MCP SDK
converts any exception raised out of a tool into a `CallToolResult(isError=
True, ...)` automatically; `app/middleware/error_handler.py` adds structured
logging around every call and ensures unexpected bugs never leak internal
details to the client. See the comments in `app/utils/exceptions.py` for the
exact text shape a client receives on failure.

## Testing

```bash
pytest
```

- `tests/test_validation.py` — ticker/date/request validators.
- `tests/test_api_client.py` — downstream HTTP client (success, retries,
  4xx/5xx mapping, timeouts), using `respx` to mock `httpx`.
- `tests/test_daily_graphs.py`, `tests/test_stock_price.py` — end-to-end
  tool tests via `mcp.call_tool(...)`, verifying both the `structuredContent`
  shape and error propagation.

## Notes on the MCP SDK version

This project pins `mcp==1.12.4`. `structuredContent` (used in every tool
response) requires `mcp>=1.10` — earlier 1.9.x builds do not include a
`structuredContent` field on `CallToolResult` at all. Tool functions return
typed Pydantic response models (not bare `dict`s) because FastMCP infers the
`structuredContent` shape from the function's return-type annotation: a
`BaseModel` subclass is used directly (flat structuredContent, matching the
HLD's worked example), whereas a bare `dict` return type gets silently
wrapped as `{"result": {...}}`.

## Out of scope (per the HLD)

Changes to SSi analytics or business rules, database changes, new
market-data calculations, trading/order-execution logic, and client-specific
UI design are explicitly out of scope for this server.
