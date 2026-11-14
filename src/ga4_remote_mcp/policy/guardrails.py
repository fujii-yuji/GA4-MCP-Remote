"""Guardrails (prd §16, tech §9.3).

Date spans accept ``YYYY-MM-DD`` and the Data API forms ``today``,
``yesterday``, and ``NdaysAgo``. Relative ends are resolved against UTC
today. A property reporting timezone can move a mixed absolute/relative
span by one calendar day; a span with two relative ends does not depend
on that zone. One range over the cap, or a range that cannot be measured,
rejects the whole request.

The Data API returns 10,000 rows when ``limit`` is omitted, and at most
250,000. An omitted ``limit`` is set to ``min(10_000, max_row_limit)`` so
the server cap applies without raising the API default. ``limit`` below 1
is rejected: the report builders treat 0 as unset and would otherwise
fetch the API default.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ga4_remote_mcp.config.settings import Settings

# https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport
_DATA_API_DEFAULT_ROW_LIMIT = 10_000
_DATE_RANGE_TOOLS = frozenset({"run_report", "run_funnel_report"})
_ROW_LIMIT_TOOLS = frozenset({"run_report", "run_realtime_report"})
_DAYS_AGO = re.compile(r"^(\d+)daysAgo$")


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_ymd(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _resolve_date(value: object, today: date) -> date | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parsed = _parse_ymd(text)
    if parsed is not None:
        return parsed
    if text == "today":
        return today
    if text == "yesterday":
        return today - timedelta(days=1)
    match = _DAYS_AGO.fullmatch(text)
    if match is None:
        return None
    try:
        return today - timedelta(days=int(match.group(1)))
    except OverflowError:
        return None


def _range_endpoint(dr: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in dr and dr[key] is not None:
            return dr[key]
    return None


def _inclusive_span_days(start: date, end: date) -> int:
    return abs((end - start).days) + 1


def _max_span_days_in_ranges(
    date_ranges: list[dict[str, Any]],
    max_days: int,
    today: date,
) -> tuple[bool, str | None]:
    """Return (ok, error_message)."""
    for dr in date_ranges:
        if not isinstance(dr, dict):
            return False, "date_ranges entries must be objects"
        start = _resolve_date(_range_endpoint(dr, "start_date", "startDate"), today)
        end = _resolve_date(_range_endpoint(dr, "end_date", "endDate"), today)
        if start is None or end is None:
            return (
                False,
                "date range must use YYYY-MM-DD, today, yesterday, or NdaysAgo",
            )
        if _inclusive_span_days(start, end) > max_days:
            return False, f"date range exceeds GA4MCP_MAX_DATE_RANGE_DAYS ({max_days})"
    return True, None


def _parse_row_limit(limit: object) -> int | None:
    if isinstance(limit, bool):
        return None
    if isinstance(limit, int):
        return limit
    if isinstance(limit, float):
        if not limit.is_integer():
            return None
        return int(limit)
    if isinstance(limit, str) and re.fullmatch(r"-?\d+", limit.strip()):
        return int(limit.strip())
    return None


def _apply_row_limit(
    args: dict[str, Any],
    settings: Settings,
) -> tuple[bool, str | None]:
    """Write a capped limit into ``args``. Return (ok, error_message)."""
    if args.get("limit") is None:
        args["limit"] = min(_DATA_API_DEFAULT_ROW_LIMIT, settings.max_row_limit)
        return True, None
    lim = _parse_row_limit(args["limit"])
    if lim is None or lim < 1:
        return False, "limit must be a positive integer"
    if lim > settings.max_row_limit:
        return False, f"limit exceeds GA4MCP_MAX_ROW_LIMIT ({settings.max_row_limit})"
    args["limit"] = lim
    return True, None


def _validate_funnel_steps(steps: object) -> tuple[bool, str | None]:
    if not isinstance(steps, list) or not steps:
        return False, "funnel_steps must be a non-empty list"
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"funnel_steps[{index}] must be an object"
        has_filter = "filter_expression" in step
        has_event = "event" in step
        if not has_filter and not has_event:
            return (
                False,
                f"funnel_steps[{index}] must contain filter_expression or event",
            )
        if has_filter:
            if not isinstance(step.get("filter_expression"), dict):
                return False, f"funnel_steps[{index}].filter_expression must be an object"
            continue
        if not isinstance(step.get("event"), str) or not step["event"].strip():
            return False, f"funnel_steps[{index}].event must be a non-empty string"
    return True, None


def _apply_funnel_next_action_limit(
    args: dict[str, Any],
    settings: Settings,
) -> tuple[bool, str | None]:
    """Cap ``funnel_next_action.limit`` when the caller sets it."""
    action = args.get("funnel_next_action")
    if action is None:
        return True, None
    if not isinstance(action, dict):
        return False, "funnel_next_action must be an object"
    if action.get("limit") is None:
        return True, None
    lim = _parse_row_limit(action["limit"])
    if lim is None or lim < 1:
        return False, "funnel_next_action.limit must be a positive integer"
    if lim > settings.max_row_limit:
        return (
            False,
            f"funnel_next_action.limit exceeds GA4MCP_MAX_ROW_LIMIT ({settings.max_row_limit})",
        )
    updated = dict(action)
    updated["limit"] = lim
    args["funnel_next_action"] = updated
    return True, None


def _validate_minute_ranges(ranges: object) -> tuple[bool, str | None]:
    """Reject a realtime minute window that cannot be sent as MinuteRange."""
    if ranges is None:
        return True, None
    if not isinstance(ranges, list):
        return False, "minute_ranges must be a list"
    if len(ranges) > 2:
        return False, "minute_ranges accepts at most 2 items"
    for index, item in enumerate(ranges):
        if not isinstance(item, dict):
            return False, f"minute_ranges[{index}] must be an object"
    return True, None


def validate_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    settings: Settings,
) -> tuple[bool, str | None, dict[str, Any] | None, str | None]:
    """
    Return (ok, error_code, mutated_args, error_message).

    If ok, mutated_args is a copy of arguments with policy applied, or None
    when nothing changed. error_message is set only when ok is False.
    """
    args = dict(arguments)
    today = _utc_today()

    if tool_name == "run_realtime_report" and not settings.enable_realtime:
        return False, "tool_disabled", None, "run_realtime_report is disabled"

    if tool_name == "run_realtime_report":
        ok, msg = _validate_minute_ranges(args.get("minute_ranges"))
        if not ok:
            return False, "invalid_request", None, msg

    if tool_name in _DATE_RANGE_TOOLS:
        dr = args.get("date_ranges")
        if not isinstance(dr, list) or not dr:
            return False, "invalid_request", None, "date_ranges must be a non-empty list"
        ok, msg = _max_span_days_in_ranges(dr, settings.max_date_range_days, today)
        if not ok:
            return False, "invalid_request", None, msg

    if tool_name == "run_funnel_report":
        ok, msg = _validate_funnel_steps(args.get("funnel_steps"))
        if not ok:
            return False, "invalid_request", None, msg
        ok, msg = _apply_funnel_next_action_limit(args, settings)
        if not ok:
            return False, "invalid_request", None, msg

    if tool_name in _ROW_LIMIT_TOOLS:
        ok, msg = _apply_row_limit(args, settings)
        if not ok:
            return False, "invalid_request", None, msg

    if tool_name in _DATE_RANGE_TOOLS and not settings.return_property_quota_default:
        args["return_property_quota"] = False

    return True, None, args if args != arguments else None, None
