"""CLI entry: Uvicorn with workers=1 (tech §16)."""

from __future__ import annotations

import os

import uvicorn

from ga4_remote_mcp.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    # Cloud Run などが注入する PORT を優先し、なければ GA4MCP_PORT、最後に設定ファイル既定値
    raw_port = os.environ.get("PORT") or os.environ.get("GA4MCP_PORT")
    port = int(raw_port) if raw_port else settings.port
    uvicorn.run(
        "ga4_remote_mcp.transport.app:build_app",
        factory=True,
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level=settings.log_level.lower(),
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    main()
