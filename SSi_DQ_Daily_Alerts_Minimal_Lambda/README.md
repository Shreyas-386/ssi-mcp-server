# SSi DQ Daily Alerts — Minimal Lambda Package

This package contains the legacy `POST /alerts` Lambda and only the local layers it imports. It is intended for the Phase 1 News-DQ daily-alert enhancement.

## Scope boundary

- Change the daily/pre-market path in `Alerts/index.py` for both `price_enabled=false` (Sentiment-only) and `price_enabled=true` (Sentiment+).
- Produce paired non-DQ and DQ daily results for the same date/window.
- Keep sentiment values and thresholds unchanged.
- Preserve the raw suppression gate: raw News + raw r/WSB buzz `< 8`.
- Do not apply DQ to momentum/long-term momentum or graphs.

The complete `index.py` and `utils.py` are included because the current `/alerts` implementation is monolithic and the same classes also implement momentum responses. Those paths are supporting code, not enhancement scope.

## What was intentionally excluded

- Every unrelated Lambda in the repository.
- Front-end/server/email code.
- Repository deployment configuration, VPC identifiers, credentials, and `Alerts/config.py`.
- Old scripts that directly call live AWS dependencies.

The extracted `daily_graph.py` now reads `DAILY_GRAPHS_FUNCTION_NAME` from the environment instead of containing a deployed function ARN. The production OpenSearch host is likewise supplied as `PROD_ES_HOST`.

## Prerequisites

- AWS SAM CLI
- Docker Desktop (for `sam local invoke`)
- Python 3.9 for parity with the deployed runtime
- Python virtual environment and pytest for unit tests

## Build

```bash
sam validate --lint
sam build --use-container
```

The included template is for local build/test. It is not a production deployment template and deliberately contains no VPC IDs, IAM grants, endpoints, or credentials.

## Offline unit tests

```bash
python3.9 -m venv .venv
source .venv/bin/activate
pip install -r layers/light_lambda/requirements.txt -r requirements-dev.txt
pytest Alerts/tests
```

The tests mock the downstream DailyGraphs call. Add DQ fixtures covering multiplier bands, boundary scores, missing scores, zero previous buzz, raw suppression, paired outputs, and failure fallback.

## Connected SAM invocation

`sam local invoke` starts the Alerts Lambda locally, but the current application still invokes DailyGraphs and, for Sentiment+, may access S3/OpenSearch. A connected invocation therefore requires approved AWS credentials, network/VPC reachability where applicable, resource permissions, and non-secret environment values.

```bash
sam local invoke AlertsFunction \
  --event events/sentiment-only.json \
  --parameter-overrides DailyGraphsFunctionName=<approved-function-name>
```

Use `events/sentiment-plus.json` for the price-enabled path. Do not distribute AWS keys or passwords in this archive; use normal AWS profiles/SSO and locally managed environment values.

## Important implementation note

The existing `AlertUtils.get_alert_data(..., is_buzz=True)` behavior returns the sum of both sources, despite its callers treating it as the social-only value. The existing suppression metadata can therefore double-count News. Before implementing DQ, split extraction into explicit News and r/WSB source accessors and add a regression test proving the gate is exactly `raw_news + raw_wsb < 8`.
