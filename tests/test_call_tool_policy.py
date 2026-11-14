"""Coordinator wiring: policy results must reach the tool call.

Unit tests of ``property_allowed`` and ``validate_tool_arguments`` stay green
if ``call_mcp_tool`` stops consulting them. These tests call the handler.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from mcp import types as mcp_types

from ga4_remote_mcp.config.settings import clear_settings_cache, get_settings
from ga4_remote_mcp.errors.normalize import INTERNAL_ERROR_MESSAGE
from ga4_remote_mcp.ga import coordinator
from ga4_remote_mcp.ga.coordinator import call_mcp_tool, list_tools
from ga4_remote_mcp.policy.semaphores_registry import init_property_semaphores


def _report(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "property_id": "111",
        "date_ranges": [{"start_date": "2025-01-01", "end_date": "2025-01-01"}],
        "dimensions": ["date"],
        "metrics": ["sessions"],
    }
    args.update(overrides)
    return args


async def _call(name: str, arguments: dict[str, Any]) -> mcp_types.CallToolResult:
    return await call_mcp_tool(
        None,  # type: ignore[arg-type]
        mcp_types.CallToolRequestParams(name=name, arguments=arguments),
    )


def _client_body(result: mcp_types.CallToolResult) -> dict[str, Any]:
    assert result.is_error is False
    text = result.content[0].text
    assert isinstance(text, str)
    return json.loads(text)


@pytest.fixture
def policy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GA4MCP_ENV", "development")
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "none")
    monkeypatch.setenv("GA4MCP_ALLOW_ALL_PROPERTIES", "false")
    monkeypatch.setenv("GA4MCP_ALLOWED_PROPERTY_IDS", "111")
    monkeypatch.setenv("GA4MCP_MAX_ROW_LIMIT", "50")
    monkeypatch.setenv("GA4MCP_ENABLE_REALTIME", "true")
    monkeypatch.setenv("GA4MCP_RETURN_PROPERTY_QUOTA_DEFAULT", "false")
    clear_settings_cache()
    init_property_semaphores(get_settings())


def _install_fake(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    *,
    error: BaseException | None = None,
) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    async def fake_run_async(
        *,
        args: dict[str, Any],
        tool_context: object = None,
    ) -> dict[str, Any]:
        seen.append(args)
        if error is not None:
            raise error
        return {"ok": True}

    monkeypatch.setattr(coordinator.tool_map[tool_name], "run_async", fake_run_async)
    return seen


async def test_property_policy_denials_skip_the_tool(
    policy_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _install_fake(monkeypatch, "run_report")

    denied = _client_body(await _call("run_report", _report(property_id="properties/999")))
    assert denied["error_code"] == "unauthorized_property"
    assert denied["property_id"] == "999"

    missing = _client_body(await _call("run_report", _report(property_id="   ")))
    assert missing["error_code"] == "invalid_property"

    assert seen == []


async def test_over_limit_skips_the_tool_and_accepted_call_uses_mutated_args(
    policy_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _install_fake(monkeypatch, "run_report")

    rejected = _client_body(await _call("run_report", _report(limit=51)))
    assert rejected["error_code"] == "invalid_request"
    assert seen == []

    result = await _call("run_report", _report(return_property_quota=True))
    assert result.is_error is False
    assert json.loads(result.content[0].text) == {"ok": True}
    assert seen == [
        {
            "property_id": "111",
            "date_ranges": [{"start_date": "2025-01-01", "end_date": "2025-01-01"}],
            "dimensions": ["date"],
            "metrics": ["sessions"],
            "return_property_quota": False,
            "limit": 50,
        }
    ]


async def test_unhandled_exception_stays_generic_for_the_client(
    policy_env: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "upstream-secret-detail"
    seen = _install_fake(monkeypatch, "run_report", error=RuntimeError(secret))

    body = _client_body(await _call("run_report", _report(limit=10)))
    assert body["error_code"] == "internal_error"
    assert body["message"] == INTERNAL_ERROR_MESSAGE
    assert secret not in json.dumps(body)
    assert seen

    logged = capsys.readouterr().out
    assert "unhandled_tool_exception" in logged
    assert secret in logged


async def test_disabled_realtime_is_hidden_and_not_called(
    policy_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GA4MCP_ENABLE_REALTIME", "false")
    clear_settings_cache()
    seen = _install_fake(monkeypatch, "run_realtime_report")

    listed = await list_tools(None, None)  # type: ignore[arg-type]
    names = {tool.name for tool in listed.tools}
    assert "run_realtime_report" not in names
    assert "run_report" in names

    body = _client_body(await _call("run_realtime_report", {}))
    assert body["error_code"] == "tool_disabled"
    assert seen == []


async def test_non_string_property_id_is_a_schema_error(
    policy_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _install_fake(monkeypatch, "run_report")
    result = await _call("run_report", _report(property_id=1))
    assert result.is_error is True
    assert isinstance(result.content[0].text, str)
    assert result.content[0].text.startswith("Input validation error:")
    assert seen == []
