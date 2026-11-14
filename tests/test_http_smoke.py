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


def test_ready_failure_does_not_leak_settings_detail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``/ready`` must return a generic body and log the detail server-side.

    We monkeypatch ``get_settings`` only for the ``ready_endpoint`` lookup so
    that the Starlette lifespan / Streamable HTTP machinery keeps using the
    real (already-cached) settings during teardown.
    """
    from ga4_remote_mcp.transport import app as app_module

    sentinel = "GA4MCP_BEARER_TOKEN-required-/etc/secrets/internal-detail"

    def boom() -> object:
        raise ValueError(sentinel)

    with TestClient(build_app()) as client:
        monkeypatch.setattr(app_module, "get_settings", boom)
        r = client.get("/ready")

        assert r.status_code == 503
        assert r.json() == {"ok": False}
        # Validation / configuration detail must not leak to clients.
        assert sentinel not in r.text
        assert "ValueError" not in r.text
        assert "ValidationError" not in r.text

        # But the original detail is preserved server-side for operators.
        captured = capsys.readouterr()
        assert "ready_check_failed" in captured.out
        assert sentinel in captured.out


def test_mcp_accepts_post() -> None:
    with TestClient(build_app()) as client:
        r = client.post("/mcp", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
        # Streamable HTTP returns JSON-RPC error or session response — not 404
        assert r.status_code != 404


def test_mcp_get_still_enforces_dns_rebinding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_ENV", "development")
    monkeypatch.setenv("GA4MCP_ENABLE_DNS_REBINDING_PROTECTION", "true")
    monkeypatch.setenv("GA4MCP_ALLOWED_HOSTS", "mcp.example.com")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        rejected = client.get(
            "/mcp",
            headers={"Host": "evil.example", "Accept": "text/event-stream"},
        )
        allowed = client.get(
            "/mcp",
            headers={"Host": "mcp.example.com", "Accept": "text/event-stream"},
        )
    assert rejected.status_code == 421
    assert allowed.status_code == 405


def test_mcp_get_returns_405_instead_of_holding_sse() -> None:
    """Stateless server must not open an empty SSE stream on GET /mcp.

    n8n's MCP Client issues GET while a workflow is Active. A 200 that never
    ends occupies a Cloud Run request until the platform timeout.
    """
    with TestClient(build_app()) as client:
        r = client.get(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert r.status_code == 405
    assert "text/event-stream" not in r.headers.get("content-type", "")
    allow = {part.strip() for part in r.headers.get("allow", "").split(",") if part.strip()}
    assert allow == {"POST"}
    body = r.json()
    assert body["jsonrpc"] == "2.0"
    assert body["error"]["code"] == -32600
    assert "server-sent event stream" in body["error"]["message"]


def test_bearer_get_with_token_is_405_not_held_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "expected-secret")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        r = client.get(
            "/mcp",
            headers={
                "Authorization": "Bearer expected-secret",
                "Accept": "application/json, text/event-stream",
            },
        )
    assert r.status_code == 405
    assert "text/event-stream" not in r.headers.get("content-type", "")


def test_bearer_rejects_get_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "expected-secret")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        r = client.get("/mcp", headers={"Accept": "text/event-stream"})
    assert r.status_code == 401
    assert r.json().get("error_code") == "authentication_failed"


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


def test_bearer_accepts_matching_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "bearer")
    monkeypatch.setenv("GA4MCP_BEARER_TOKEN", "expected-secret")
    clear_settings_cache()
    with TestClient(build_app()) as client:
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
            headers={"Authorization": "Bearer expected-secret"},
        )
        # Authorised requests must reach the MCP transport — never the auth
        # middleware's authentication_failed body.
        assert r.status_code != 401
        assert r.status_code != 403
        if r.headers.get("content-type", "").startswith("application/json"):
            assert r.json().get("error_code") != "authentication_failed"
