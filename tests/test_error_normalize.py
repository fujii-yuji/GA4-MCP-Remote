"""Unit tests for `map_exception_to_code` — focuses on information disclosure."""

from __future__ import annotations

import asyncio

from google.api_core import exceptions as google_exceptions

from ga4_remote_mcp.errors.normalize import (
    INTERNAL_ERROR_MESSAGE,
    map_exception_to_code,
)


def test_unknown_exception_yields_generic_internal_error_message() -> None:
    code, message = map_exception_to_code(
        ValueError("GA4MCP_BEARER_TOKEN is required when GA4MCP_AUTH_MODE=bearer")
    )
    assert code == "internal_error"
    assert message == INTERNAL_ERROR_MESSAGE
    # Ensure the original exception message is not echoed back to clients.
    assert "GA4MCP_BEARER_TOKEN" not in message
    assert "GA4MCP_AUTH_MODE" not in message


def test_runtime_error_does_not_leak_internal_hostnames() -> None:
    code, message = map_exception_to_code(
        RuntimeError("Failed to reach DB host=db.internal:5432 user=admin")
    )
    assert code == "internal_error"
    assert message == INTERNAL_ERROR_MESSAGE
    assert "db.internal" not in message
    assert "admin" not in message


def test_known_upstream_exceptions_keep_their_messages() -> None:
    # Classified upstream errors deliberately surface the GA message so that
    # operators can act on quota / auth signals at the client layer.
    code, message = map_exception_to_code(
        google_exceptions.ResourceExhausted("daily request limit reached")
    )
    assert code == "quota_exceeded"
    assert "daily request limit reached" in message

    code, message = map_exception_to_code(google_exceptions.PermissionDenied("permission denied"))
    assert code == "upstream_auth_failed"
    assert "permission denied" in message

    code, message = map_exception_to_code(google_exceptions.DeadlineExceeded("deadline"))
    assert code == "timeout"
    assert "deadline" in message


def test_cancelled_error_returns_fixed_message() -> None:
    code, message = map_exception_to_code(asyncio.CancelledError())
    assert code == "timeout"
    assert message == "cancelled"
