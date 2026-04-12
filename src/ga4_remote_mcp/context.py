"""Request-scoped context (ASGI → MCP tool handlers)."""

from __future__ import annotations

import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "ga4mcp_request_id",
    default="-",
)

client_identifier_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "ga4mcp_client_identifier",
    default="unknown",
)
