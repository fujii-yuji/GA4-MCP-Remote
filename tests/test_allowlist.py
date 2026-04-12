"""Allowlist normalization (prd §13.2, tech §9.2)."""

from __future__ import annotations

import pytest

from ga4_remote_mcp.config.settings import clear_settings_cache, get_settings
from ga4_remote_mcp.policy.allowlist import normalize_property_id, property_allowed


def test_normalize_property_id() -> None:
    assert normalize_property_id("properties/123") == "123"
    assert normalize_property_id(456) == "456"
    assert normalize_property_id(None) is None


def test_property_allowed_explicit_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_ALLOW_ALL_PROPERTIES", "false")
    monkeypatch.setenv("GA4MCP_ALLOWED_PROPERTY_IDS", "111,properties/222")
    clear_settings_cache()
    s = get_settings()
    assert property_allowed("111", s)
    assert property_allowed("222", s)
    assert not property_allowed("333", s)


def test_property_allowed_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_ALLOW_ALL_PROPERTIES", "true")
    monkeypatch.setenv("GA4MCP_ALLOWED_PROPERTY_IDS", "")
    clear_settings_cache()
    s = get_settings()
    assert property_allowed("999999", s)
