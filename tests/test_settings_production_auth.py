"""Settings: production env requires bearer authentication (item B).

Conftest sets the base test env to ``GA4MCP_ENV=development`` /
``GA4MCP_AUTH_MODE=none``. Each test overrides what it needs and then
constructs ``Settings()`` directly so the validators run on the supplied
environment without sharing the lru_cache.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ga4_remote_mcp.config.settings import Settings, clear_settings_cache


def _build_settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    clear_settings_cache()
    return Settings()


def test_production_with_auth_none_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError) as excinfo:
        _build_settings(
            monkeypatch,
            GA4MCP_ENV="production",
            GA4MCP_AUTH_MODE="none",
            GA4MCP_ALLOWED_PROPERTY_IDS="123456789",
        )
    err = str(excinfo.value)
    assert "GA4MCP_AUTH_MODE" in err
    assert "production" in err.lower()


def test_production_with_bearer_and_token_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _build_settings(
        monkeypatch,
        GA4MCP_ENV="production",
        GA4MCP_AUTH_MODE="bearer",
        GA4MCP_BEARER_TOKEN="example-secret-token",
        GA4MCP_ALLOWED_PROPERTY_IDS="123456789",
    )
    assert s.env == "production"
    assert s.auth_mode == "bearer"
    assert s.bearer_token == "example-secret-token"


def test_production_bearer_without_token_still_fails_with_token_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``validate_bearer`` continues to govern the bearer-without-token case."""
    with pytest.raises(ValidationError) as excinfo:
        _build_settings(
            monkeypatch,
            GA4MCP_ENV="production",
            GA4MCP_AUTH_MODE="bearer",
            GA4MCP_ALLOWED_PROPERTY_IDS="123456789",
        )
    assert "GA4MCP_BEARER_TOKEN" in str(excinfo.value)


def test_staging_with_auth_none_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _build_settings(
        monkeypatch,
        GA4MCP_ENV="staging",
        GA4MCP_AUTH_MODE="none",
    )
    assert s.env == "staging"
    assert s.auth_mode == "none"


def test_development_with_auth_none_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _build_settings(
        monkeypatch,
        GA4MCP_ENV="development",
        GA4MCP_AUTH_MODE="none",
    )
    assert s.env == "development"
    assert s.auth_mode == "none"


def test_production_combined_with_missing_allowlist_surfaces_at_least_one_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both ``validate_production_auth`` and ``validate_production_allowlist``
    are production-only gates. We do not assert which one wins (pydantic v2
    raises on the first failing model_validator in declaration order); we
    only assert that at least one of them blocks the misconfiguration.
    """
    with pytest.raises(ValidationError) as excinfo:
        _build_settings(
            monkeypatch,
            GA4MCP_ENV="production",
            GA4MCP_AUTH_MODE="none",
            GA4MCP_ALLOWED_PROPERTY_IDS="",
            GA4MCP_ALLOW_ALL_PROPERTIES="false",
        )
    err = str(excinfo.value)
    assert "GA4MCP_AUTH_MODE" in err or "GA4MCP_ALLOWED_PROPERTY_IDS" in err
