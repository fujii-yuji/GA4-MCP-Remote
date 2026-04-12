"""Map exceptions to PRD §17.2-style error codes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from google.api_core import exceptions as google_exceptions

from ga4_remote_mcp.context import request_id_var


def map_exception_to_code(exc: BaseException) -> tuple[str, str]:
    """Return (error_code, message) for an upstream exception."""
    if isinstance(exc, google_exceptions.ResourceExhausted):
        return "quota_exceeded", str(exc)
    if isinstance(exc, google_exceptions.Unauthenticated):
        return "upstream_auth_failed", str(exc)
    if isinstance(exc, google_exceptions.PermissionDenied):
        return "upstream_auth_failed", str(exc)
    if isinstance(exc, google_exceptions.DeadlineExceeded):
        return "timeout", str(exc)
    if isinstance(exc, google_exceptions.ServiceUnavailable):
        return "upstream_unavailable", str(exc)
    if isinstance(exc, TimeoutError):
        return "timeout", str(exc)
    if isinstance(exc, asyncio.CancelledError):
        return "timeout", "cancelled"
    return "internal_error", str(exc)


def tool_error_payload(
    *,
    code: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> str:
    body: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "request_id": request_id_var.get(),
    }
    if extra:
        body.update(extra)
    return json.dumps(body, ensure_ascii=False)
