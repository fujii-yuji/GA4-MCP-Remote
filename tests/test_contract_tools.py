"""MCP tool name contract (prd §12.1): 7 tools, stable names."""

from __future__ import annotations

from ga4_remote_mcp.ga.coordinator import mcp_tools

EXPECTED = frozenset(
    {
        "get_account_summaries",
        "list_google_ads_links",
        "get_property_details",
        "list_property_annotations",
        "get_custom_dimensions_and_metrics",
        "run_report",
        "run_realtime_report",
    }
)


def test_tool_names_match_official_set() -> None:
    assert {t.name for t in mcp_tools} == EXPECTED
