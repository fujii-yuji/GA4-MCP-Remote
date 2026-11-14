"""Guardrail validation (prd §16)."""

from __future__ import annotations

from datetime import date

import pytest

from ga4_remote_mcp.config.settings import clear_settings_cache, get_settings
from ga4_remote_mcp.policy import guardrails
from ga4_remote_mcp.policy.guardrails import validate_tool_arguments

_ONE_DAY = [{"start_date": "2025-01-01", "end_date": "2025-01-01"}]


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    clear_settings_cache()
    return get_settings()


def test_run_report_limit_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100")
    ok, code, _, message = validate_tool_arguments(
        "run_report",
        {"limit": 101, "date_ranges": _ONE_DAY},
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "GA4MCP_MAX_ROW_LIMIT" in message


def test_run_report_date_span(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, code, _, message = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "2025-01-01", "end_date": "2025-01-10"},
            ],
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "GA4MCP_MAX_DATE_RANGE_DAYS" in message


def test_realtime_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_ENABLE_REALTIME="false")
    ok, code, _, _ = validate_tool_arguments(
        "run_realtime_report",
        {"limit": 10**9},
        s,
    )
    assert ok is False
    assert code == "tool_disabled"


def test_absolute_span_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "2025-01-01", "end_date": "2025-01-02"},
            ],
        },
        s,
    )
    assert ok is True
    assert code is None

    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "2025-01-01", "end_date": "2025-01-03"},
            ],
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"


def test_relative_span_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, _, mutated, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": " yesterday ", "end_date": "today"},
            ],
        },
        s,
    )
    assert ok is True
    assert mutated is not None

    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "30daysAgo", "end_date": "today"},
            ],
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"

    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="30")
    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "30daysAgo", "end_date": "yesterday"},
            ],
        },
        s,
    )
    assert ok is True
    assert code is None


def test_mixed_absolute_and_relative_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(guardrails, "_utc_today", lambda: date(2026, 11, 14))
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, _, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "2026-11-13", "end_date": "today"},
            ],
        },
        s,
    )
    assert ok is True

    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "2020-01-01", "end_date": "today"},
            ],
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"


def test_unparseable_date_range_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="366")
    for date_ranges in (
        [{"start_date": "lastWeek", "end_date": "today"}],
        [{"start_date": "Today", "end_date": "today"}],
        [{"start_date": "2025-01-01"}],
        [{"start_date": 20250101, "end_date": "2025-01-01"}],
        ["2025-01-01"],
        "2025-01-01",
    ):
        ok, code, _, message = validate_tool_arguments(
            "run_report",
            {"date_ranges": date_ranges},
            s,
        )
        assert ok is False
        assert code == "invalid_request"
        assert message


def test_one_over_cap_range_rejects_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="7")
    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"start_date": "yesterday", "end_date": "today"},
                {"startDate": "30daysAgo", "endDate": "today"},
            ],
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"


def test_camel_case_relative_range_within_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {
            "date_ranges": [
                {"startDate": "yesterday", "endDate": "today"},
            ],
        },
        s,
    )
    assert ok is True
    assert code is None


def test_omitted_limit_is_capped_below_api_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100")
    original = {"date_ranges": _ONE_DAY}
    ok, code, mutated, _ = validate_tool_arguments("run_report", original, s)
    assert ok is True
    assert code is None
    assert mutated is not None
    assert mutated["limit"] == 100
    assert "limit" not in original


def test_omitted_limit_keeps_api_default_when_cap_is_higher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100000")
    ok, _, mutated, _ = validate_tool_arguments(
        "run_report",
        {"date_ranges": _ONE_DAY},
        s,
    )
    assert ok is True
    assert mutated is not None
    assert mutated["limit"] == 10_000


def test_explicit_limit_within_cap_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100")
    ok, _, mutated, _ = validate_tool_arguments(
        "run_report",
        {"limit": "50", "date_ranges": _ONE_DAY, "return_property_quota": False},
        s,
    )
    assert ok is True
    assert mutated is not None
    assert mutated["limit"] == 50


def test_non_positive_limit_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100")
    for limit in (0, -1, "0", 1.5, True, "many"):
        ok, code, _, message = validate_tool_arguments(
            "run_report",
            {"limit": limit, "date_ranges": _ONE_DAY},
            s,
        )
        assert ok is False, limit
        assert code == "invalid_request"
        assert message is not None
        assert "positive integer" in message


def test_realtime_row_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="100")
    ok, code, _, _ = validate_tool_arguments(
        "run_realtime_report",
        {"limit": 101},
        s,
    )
    assert ok is False
    assert code == "invalid_request"

    ok, _, mutated, _ = validate_tool_arguments("run_realtime_report", {}, s)
    assert ok is True
    assert mutated is not None
    assert mutated["limit"] == 100
    assert "return_property_quota" not in mutated

    ok, _, mutated, _ = validate_tool_arguments(
        "run_realtime_report",
        {"limit": 10},
        s,
    )
    assert ok is True
    assert mutated is None


def test_empty_or_missing_date_ranges_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="366")
    for arguments in ({"date_ranges": []}, {"date_ranges": None}, {}):
        ok, code, _, message = validate_tool_arguments("run_report", arguments, s)
        assert ok is False
        assert code == "invalid_request"
        assert message is not None
        assert "date_ranges" in message


def test_zero_days_ago_and_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardrails, "_utc_today", lambda: date(2026, 11, 14))
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="1")
    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {"date_ranges": [{"start_date": "0daysAgo", "end_date": "today"}]},
        s,
    )
    assert ok is True
    assert code is None

    ok, code, _, _ = validate_tool_arguments(
        "run_report",
        {"date_ranges": [{"start_date": "999999999daysAgo", "end_date": "today"}]},
        s,
    )
    assert ok is False
    assert code == "invalid_request"


_FUNNEL_STEPS = [{"name": "Session start", "event": "session_start"}]


def test_funnel_rejects_wide_date_range(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_DATE_RANGE_DAYS="2")
    ok, code, _, message = validate_tool_arguments(
        "run_funnel_report",
        {
            "date_ranges": [{"start_date": "2025-01-01", "end_date": "2025-01-10"}],
            "funnel_steps": _FUNNEL_STEPS,
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "GA4MCP_MAX_DATE_RANGE_DAYS" in message


def test_funnel_ignores_event_when_filter_expression_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = _settings(monkeypatch)
    ok, code, _, _ = validate_tool_arguments(
        "run_funnel_report",
        {
            "date_ranges": _ONE_DAY,
            "funnel_steps": [
                {"name": "Visit", "event": "", "filter_expression": {"funnel_event_filter": {}}}
            ],
        },
        s,
    )
    assert ok is True
    assert code is None


def test_funnel_rejects_empty_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch)
    ok, code, _, message = validate_tool_arguments(
        "run_funnel_report",
        {"date_ranges": _ONE_DAY, "funnel_steps": []},
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "funnel_steps" in message

    ok, code, _, message = validate_tool_arguments(
        "run_funnel_report",
        {"date_ranges": _ONE_DAY, "funnel_steps": [{"event": ""}]},
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "event" in message


def test_funnel_caps_next_action_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _settings(monkeypatch, GA4MCP_MAX_ROW_LIMIT="10")
    ok, code, mutated, _ = validate_tool_arguments(
        "run_funnel_report",
        {
            "date_ranges": _ONE_DAY,
            "funnel_steps": _FUNNEL_STEPS,
            "funnel_next_action": {"next_action_dimension": "eventName", "limit": 4},
        },
        s,
    )
    assert ok is True
    assert code is None
    assert mutated is not None
    assert mutated["funnel_next_action"]["limit"] == 4
    assert mutated["return_property_quota"] is False

    ok, code, _, message = validate_tool_arguments(
        "run_funnel_report",
        {
            "date_ranges": _ONE_DAY,
            "funnel_steps": _FUNNEL_STEPS,
            "funnel_next_action": {"next_action_dimension": "eventName", "limit": 11},
        },
        s,
    )
    assert ok is False
    assert code == "invalid_request"
    assert message is not None
    assert "GA4MCP_MAX_ROW_LIMIT" in message
