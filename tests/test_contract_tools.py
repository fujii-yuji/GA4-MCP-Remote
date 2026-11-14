"""MCP tool name contract (prd §12.1): stable tool names."""

from __future__ import annotations

from ga4_remote_mcp.ga.coordinator import mcp_tools

EXPECTED = frozenset(
    {
        "get_account_summaries",
        "list_google_ads_links",
        "get_property_details",
        "list_property_annotations",
        "list_key_events",
        "get_custom_dimensions_and_metrics",
        "run_report",
        "run_funnel_report",
        "run_realtime_report",
    }
)


def test_tool_names_match_official_set() -> None:
    assert {t.name for t in mcp_tools} == EXPECTED


# Required argument names are a client contract. Descriptions and hint text are not.
EXPECTED_REQUIRED: dict[str, list[str]] = {
    "get_account_summaries": [],
    "list_google_ads_links": ["property_id"],
    "get_property_details": ["property_id"],
    "list_property_annotations": ["property_id"],
    "list_key_events": ["property_id"],
    "get_custom_dimensions_and_metrics": ["property_id"],
    "run_report": ["property_id", "date_ranges", "dimensions", "metrics"],
    "run_funnel_report": ["property_id", "funnel_steps", "date_ranges"],
    "run_realtime_report": ["property_id", "dimensions", "metrics"],
}


def test_tool_schemas_keep_required_names_and_string_property_id() -> None:
    by_name = {tool.name: tool.input_schema for tool in mcp_tools}
    assert set(by_name) == set(EXPECTED_REQUIRED)
    for name, required in EXPECTED_REQUIRED.items():
        schema = by_name[name]
        # `required` is a set for clients. Generator order is not part of the contract.
        assert set(schema.get("required") or []) == set(required)
        property_id = (schema.get("properties") or {}).get("property_id")
        if name == "get_account_summaries":
            assert property_id is None
            continue
        assert property_id is not None
        assert property_id.get("type") == "string"
        assert "anyOf" not in property_id
