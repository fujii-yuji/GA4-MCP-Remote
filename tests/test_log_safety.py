"""Logs must not echo secrets (prd §18, §29)."""

from __future__ import annotations

from ga4_remote_mcp.context import request_id_var
from ga4_remote_mcp.errors.normalize import tool_error_payload


def test_tool_error_payload_shape() -> None:
    token = request_id_var.set("rid-test")
    try:
        raw = tool_error_payload(code="authentication_failed", message="bad")
    finally:
        request_id_var.reset(token)
    assert "authentication_failed" in raw
    assert "rid-test" in raw
    assert "Bearer" not in raw
    assert "secret" not in raw.lower()
