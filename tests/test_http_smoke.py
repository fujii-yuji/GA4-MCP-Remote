"""HTTP smoke: health, ready, /mcp reachable."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ga4_remote_mcp.config.settings import clear_settings_cache
from ga4_remote_mcp.transport.app import build_app


def test_health_ok() -> None:
    with TestClient(build_app()) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.text == "ok"


def test_ready_ok() -> None:
    with TestClient(build_app()) as client:
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.json().get("ok") is True


def test_mcp_accepts_post() -> None:
    with TestClient(build_app()) as client:
        r = client.post("/mcp", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
        # Streamable HTTP returns JSON-RPC error or session response — not 404
        assert r.status_code != 404


def test_bearer_rejects_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "expected-secret")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        r = client.post("/mcp", json={})
        assert r.status_code == 401
        body = r.json()
        assert body.get("error_code") == "authentication_failed"


def test_bearer_allows_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "x")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        assert client.get("/health").status_code == 200


def test_bearer_rejects_with_configurable_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "expected-secret")
    monkeypatch.setenv("GA4MCP_BEARER_FAILURE_HTTP_STATUS", "403")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        r = client.post("/mcp", json={})
        assert r.status_code == 403
        assert r.json().get("error_code") == "authentication_failed"
