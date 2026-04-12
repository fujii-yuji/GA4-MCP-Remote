"""Test defaults: development env before importing the app (get_settings cache)."""

from __future__ import annotations

import os

# Must run before ga4_remote_mcp.transport.app (build_app calls get_settings).
os.environ["GA4MCP_ENV"] = "development"
os.environ["GA4MCP_AUTH_MODE"] = "none"
os.environ["GA4MCP_ENABLE_DNS_REBINDING_PROTECTION"] = "false"
# リポジトリ直下の .env の 403 既定をテストで拾わない（HTTP ステータスのアサートを安定させる）
os.environ["GA4MCP_BEARER_FAILURE_HTTP_STATUS"] = "401"

import pytest

from ga4_remote_mcp.config.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    clear_settings_cache()
    yield
    clear_settings_cache()
