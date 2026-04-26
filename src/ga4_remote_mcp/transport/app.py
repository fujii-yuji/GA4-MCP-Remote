"""Starlette ASGI app: /health, /ready, Streamable HTTP /mcp."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
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


class McpHttpBridge:
    """Forward /mcp to StreamableHTTPSessionManager."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
            yield

    routes = [
        Route("/health", endpoint=health_endpoint, methods=["GET", "HEAD"]),
        Route("/ready", endpoint=ready_endpoint, methods=["GET", "HEAD"]),
        Route(
            "/mcp",
            endpoint=McpHttpBridge(),
            methods=["GET", "POST", "DELETE", "OPTIONS"],
        ),
    ]

    star = Starlette(routes=routes, lifespan=lifespan)
    return wrap_with_middleware(star)
