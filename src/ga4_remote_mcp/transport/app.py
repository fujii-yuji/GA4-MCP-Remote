"""Starlette ASGI app: /health, /ready, Streamable HTTP /mcp."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecurityMiddleware, TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ga4_remote_mcp.config.settings import get_settings
from ga4_remote_mcp.errors.normalize import tool_error_payload
from ga4_remote_mcp.ga.coordinator import app as mcp_lowlevel_server
from ga4_remote_mcp.policy.semaphores_registry import init_property_semaphores
from ga4_remote_mcp.structured_log.jsonlog import log_line
from ga4_remote_mcp.transport.middleware import wrap_with_middleware


async def health_endpoint(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def ready_endpoint(_: Request) -> JSONResponse:
    try:
        get_settings()
    except Exception as e:
        # Settings validation messages can echo env-var names, file paths,
        # and other configuration internals. Keep the client-facing body
        # minimal and stash the detail in the server-side log only.
        log_line(
            {
                "event": "ready_check_failed",
                "level": "error",
                "error_class": type(e).__name__,
                "error_message": str(e),
            }
        )
        return JSONResponse({"ok": False}, status_code=503)
    return JSONResponse({"ok": True})


# JSON-RPC invalid request. Matches mcp.types.INVALID_REQUEST without importing it
# into the HTTP bridge.
_JSONRPC_INVALID_REQUEST = -32600

# Only POST completes on this stateless server. DELETE has no session to
# terminate, and the SDK rejects OPTIONS. Both already return 405.
_MCP_ALLOW_HEADER = "POST"


def _reject_get_without_sse() -> JSONResponse:
    """405 for ``GET /mcp``.

    This server runs ``StreamableHTTPSessionManager(stateless=True)`` and never
    issues ``Mcp-Session-Id`` or server-to-client notifications. The Streamable
    HTTP spec (2025-03-26) says an endpoint that does not offer an SSE stream
    returns 405 instead of holding the GET open. Leaving the GET to the SDK
    opens an empty ``text/event-stream`` and keeps the Cloud Run request until
    the platform timeout.
    """
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": "server-error",
            "error": {
                "code": _JSONRPC_INVALID_REQUEST,
                "message": (
                    "Method Not Allowed: this server does not offer a server-sent event stream"
                ),
            },
        },
        status_code=405,
        headers={"Allow": _MCP_ALLOW_HEADER},
    )


class McpHttpBridge:
    """Forward /mcp to StreamableHTTPSessionManager."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("method") == "GET":
            # Reject before StreamableHTTPSessionManager. Its GET handler opens
            # an empty SSE stream and does not return until the client or the
            # platform closes it. Host / Origin checks still run, so this
            # shortcut does not bypass DNS rebinding protection.
            application = scope.get("app")
            security = getattr(getattr(application, "state", None), "transport_security", None)
            if security is not None:
                error = await security.validate_request(Request(scope, receive), is_post=False)
                if error is not None:
                    await error(scope, receive, send)
                    return
            await _reject_get_without_sse()(scope, receive, send)
            return

        application = scope.get("app")
        if application is None:
            log_line(
                {
                    "event": "mcp_bridge_misconfigured",
                    "level": "error",
                    "error_message": "ASGI scope is missing the Starlette app reference",
                }
            )
            body = json.loads(
                tool_error_payload(
                    code="internal_error",
                    message="Internal server error",
                )
            )
            await JSONResponse(body, status_code=500)(scope, receive, send)
            return
        sm = application.state.session_manager
        await sm.handle_request(scope, receive, send)


def build_app() -> ASGIApp:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(starlette_app: Starlette):
        init_property_semaphores(settings)
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=settings.enable_dns_rebinding_protection,
            allowed_hosts=settings.parsed_allowed_hosts(),
            allowed_origins=settings.parsed_allowed_origins(),
        )
        session_manager = StreamableHTTPSessionManager(
            mcp_lowlevel_server,
            json_response=settings.json_response,
            stateless=True,
            security_settings=security,
        )
        async with session_manager.run():
            starlette_app.state.session_manager = session_manager
            starlette_app.state.transport_security = TransportSecurityMiddleware(security)
            yield

    routes = [
        Route("/health", endpoint=health_endpoint, methods=["GET", "HEAD"]),
        Route("/ready", endpoint=ready_endpoint, methods=["GET", "HEAD"]),
        Route(
            "/mcp",
            endpoint=McpHttpBridge(),
            # GET stays on the route so the bridge can return 405 itself.
            # Removing it would also 405, but Starlette's plain-text body
            # would skip the JSON-RPC error clients already parse.
            methods=["GET", "POST", "DELETE", "OPTIONS"],
        ),
    ]

    star = Starlette(routes=routes, lifespan=lifespan)
    return wrap_with_middleware(star)
