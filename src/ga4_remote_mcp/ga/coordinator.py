# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MCP server singleton: GA tools + Remote policy hooks."""

from __future__ import annotations

import asyncio
import json
import time

import jsonschema
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from mcp import types as mcp_types
from mcp.server import ServerRequestContext
from mcp.server.lowlevel import Server

from ga4_remote_mcp import __version__
from ga4_remote_mcp.config.settings import get_settings
from ga4_remote_mcp.context import client_identifier_var, request_id_var
from ga4_remote_mcp.errors.normalize import map_exception_to_code, tool_error_payload
from ga4_remote_mcp.ga.tools.admin.info import (
    get_account_summaries,
    get_property_details,
    list_google_ads_links,
    list_property_annotations,
)
from ga4_remote_mcp.ga.tools.reporting.core import (
    _run_report_description,
    run_report,
)
from ga4_remote_mcp.ga.tools.reporting.funnel import (
    _run_funnel_report_description,
    run_funnel_report,
)
from ga4_remote_mcp.ga.tools.reporting.metadata import get_custom_dimensions_and_metrics
from ga4_remote_mcp.ga.tools.reporting.realtime import (
    _run_realtime_report_description,
    run_realtime_report,
)
from ga4_remote_mcp.policy.allowlist import (
    TOOLS_REQUIRING_PROPERTY,
    normalize_property_id,
    property_allowed,
)
from ga4_remote_mcp.policy.guardrails import validate_tool_arguments
from ga4_remote_mcp.policy.semaphores_registry import get_property_semaphores
from ga4_remote_mcp.structured_log.jsonlog import log_line

run_report_with_description = FunctionTool(run_report)
run_report_with_description.description = _run_report_description()
run_funnel_report_with_description = FunctionTool(run_funnel_report)
run_funnel_report_with_description.description = _run_funnel_report_description()
run_realtime_report_with_description = FunctionTool(run_realtime_report)
run_realtime_report_with_description.description = _run_realtime_report_description()

tools = [
    FunctionTool(get_account_summaries),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(list_property_annotations),
    FunctionTool(get_custom_dimensions_and_metrics),
    run_report_with_description,
    run_funnel_report_with_description,
    run_realtime_report_with_description,
]

tool_map = {t.name: t for t in tools}

INSTRUCTIONS = (
    "Remote Streamable HTTP MCP server for Google Analytics 4, forked from "
    "google-analytics-mcp. Read-only GA4 access via official Data/Admin APIs."
)


def _normalize_input_schema(tool: mcp_types.Tool) -> None:
    schema = dict(tool.input_schema or {})
    if schema == {}:
        schema = {"type": "object", "properties": {}}
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for prop in properties.values():
            if isinstance(prop, dict) and "anyOf" in prop and prop.get("type") == "null":
                del prop["type"]
    tool.input_schema = schema


mcp_tools = [adk_to_mcp_tool_type(tool) for tool in tools]
for tool in mcp_tools:
    _normalize_input_schema(tool)


def _visible_tools() -> list[mcp_types.Tool]:
    settings = get_settings()
    if settings.enable_realtime:
        return mcp_tools
    return [t for t in mcp_tools if t.name != "run_realtime_report"]


def _text_result(text: str, *, is_error: bool = False) -> mcp_types.CallToolResult:
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=text)],
        is_error=is_error,
    )


async def list_tools(
    _ctx: ServerRequestContext,
    _params: mcp_types.PaginatedRequestParams | None,
) -> mcp_types.ListToolsResult:
    return mcp_types.ListToolsResult(tools=_visible_tools())


async def call_mcp_tool(
    _ctx: ServerRequestContext,
    params: mcp_types.CallToolRequestParams,
) -> mcp_types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}
    settings = get_settings()
    rid = request_id_var.get()
    t0 = time.perf_counter()

    logged_args = arguments

    listed = next((tool for tool in _visible_tools() if tool.name == name), None)
    if listed is not None:
        try:
            jsonschema.validate(instance=arguments, schema=listed.input_schema)
        except jsonschema.ValidationError as exc:
            # mcp 1 validated here, before the handler, and did not emit a tool log.
            return _text_result(f"Input validation error: {exc.message}", is_error=True)

    def emit(
        *,
        status: str,
        error_code: str | None = None,
        property_id: str | None = None,
    ) -> None:
        row_limit = None
        if isinstance(logged_args, dict):
            lim = logged_args.get("limit")
            if lim is not None:
                row_limit = lim
        log_line(
            {
                "request_id": rid,
                "client_identifier": client_identifier_var.get(),
                "tool_name": name,
                "property_id": property_id or "-",
                "status": status,
                "latency_ms": int((time.perf_counter() - t0) * 1000),
                **({"error_code": error_code} if error_code else {}),
                **({"row_limit": row_limit} if row_limit is not None else {}),
            }
        )

    if name not in tool_map:
        emit(status="error", error_code="invalid_request")
        return _text_result(
            tool_error_payload(
                code="invalid_request",
                message=f"Tool '{name}' not implemented by this server.",
            )
        )

    if name == "run_realtime_report" and not settings.enable_realtime:
        emit(status="error", error_code="tool_disabled")
        return _text_result(
            tool_error_payload(
                code="tool_disabled",
                message="run_realtime_report is disabled by GA4MCP_ENABLE_REALTIME",
            )
        )

    prop_norm: str | None = None
    if name in TOOLS_REQUIRING_PROPERTY:
        prop_norm = normalize_property_id(arguments.get("property_id"))
        if not prop_norm:
            emit(status="error", error_code="invalid_property")
            return _text_result(
                tool_error_payload(
                    code="invalid_property",
                    message="property_id is required",
                )
            )
        if not property_allowed(prop_norm, settings):
            emit(status="error", error_code="unauthorized_property", property_id=prop_norm)
            return _text_result(
                tool_error_payload(
                    code="unauthorized_property",
                    message="property_id is not allowed by server policy",
                    extra={"property_id": prop_norm},
                )
            )

    ok, err_code, mutated, detail = validate_tool_arguments(name, arguments, settings)
    if not ok:
        emit(status="error", error_code=err_code or "invalid_request", property_id=prop_norm)
        return _text_result(
            tool_error_payload(
                code=err_code or "invalid_request",
                message=detail or "Request failed guardrail validation",
            )
        )

    exec_args = mutated if mutated is not None else arguments
    logged_args = exec_args
    tool = tool_map[name]
    timeout_s = settings.request_timeout_ms / 1000.0

    async def _run() -> object:
        return await tool.run_async(args=exec_args, tool_context=None)

    try:
        if prop_norm is not None:
            sem = await get_property_semaphores().acquire(prop_norm)
            async with sem:
                adk_tool_response = await asyncio.wait_for(_run(), timeout=timeout_s)
        else:
            adk_tool_response = await asyncio.wait_for(_run(), timeout=timeout_s)
        response_text = json.dumps(adk_tool_response, indent=2)
        emit(status="ok", property_id=prop_norm)
        return _text_result(response_text)
    except TimeoutError:
        emit(status="error", error_code="timeout", property_id=prop_norm)
        return _text_result(tool_error_payload(code="timeout", message="Tool execution timed out"))
    except Exception as e:
        code, msg = map_exception_to_code(e)
        if code == "internal_error":
            # `msg` is intentionally generic for the client; preserve the real
            # exception detail in the server log so operators can still debug.
            log_line(
                {
                    "request_id": rid,
                    "client_identifier": client_identifier_var.get(),
                    "tool_name": name,
                    "property_id": prop_norm or "-",
                    "level": "error",
                    "event": "unhandled_tool_exception",
                    "error_class": type(e).__name__,
                    "error_message": str(e),
                }
            )
        emit(status="error", error_code=code, property_id=prop_norm)
        return _text_result(tool_error_payload(code=code, message=msg))


app = Server(
    name="ga4-remote-mcp",
    version=__version__,
    instructions=INSTRUCTIONS,
    on_list_tools=list_tools,
    on_call_tool=call_mcp_tool,
)
