# SSi MCP Server — production image (HTTP / streamable-http transport).
# Python 3.12 matches MCP SDK support; pin the minor series for reproducible builds.
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app/ ./app/
COPY run.py .

RUN chown -R app:app /app

USER app

ENV TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8080 \
    ENVIRONMENT=production \
    REQUIRE_CLIENT_AUTH=true \
    LOG_LEVEL=INFO

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

CMD ["python", "run.py"]
