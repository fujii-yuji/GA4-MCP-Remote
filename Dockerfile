# Remote GA4 MCP — Uvicorn workers=1 (tech §16)
FROM python:3.12-slim-bookworm AS base
WORKDIR /app
RUN useradd -m -u 10001 appuser
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

FROM base AS builder
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/ga4-remote-mcp /usr/local/bin/ga4-remote-mcp
USER appuser
EXPOSE 8080
ENV GA4MCP_PORT=8080
CMD ["ga4-remote-mcp"]
