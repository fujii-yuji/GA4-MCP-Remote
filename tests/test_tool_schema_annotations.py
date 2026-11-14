"""Client-facing schema hygiene: annotations and additionalProperties."""

from __future__ import annotations

from typing import Any

from mcp import types as mcp_types

from ga4_remote_mcp.ga import coordinator
from ga4_remote_mcp.ga.coordinator import (
    _normalize_input_schema,
    call_mcp_tool,
    list_tools,
    mcp_tools,
    sanitize_mcp_schema_properties,
)


def test_sanitize_walks_nested_objects_and_array_items() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "keep_false": {"additionalProperties": False},
            "keep_true": {"additionalProperties": True},
            "untouched": {"type": "string"},
            "nested": {
                "type": "object",
                "properties": {
                    "inner": {"additionalProperties": {"type": "string"}},
                },
            },
            "rows": {
                "type": "array",
                "items": {"additionalProperties": {"type": "integer"}},
            },
            "choices": {
                "anyOf": [
                    {"additionalProperties": {"type": "string"}},
                    {"type": "null"},
                ]
            },
        },
    }

    sanitize_mcp_schema_properties(schema)

    props = schema["properties"]
    assert props["keep_false"]["additionalProperties"] is False
    assert props["keep_true"]["additionalProperties"] is True
    assert "additionalProperties" not in props["untouched"]
    assert props["nested"]["properties"]["inner"]["additionalProperties"] is True
    assert props["rows"]["items"]["additionalProperties"] is True
    assert props["choices"]["anyOf"][0]["additionalProperties"] is True
    assert props["choices"]["anyOf"][1] == {"type": "null"}


def _assert_additional_properties_are_bools(node: object) -> None:
    if isinstance(node, dict):
        if "additionalProperties" in node:
            assert isinstance(node["additionalProperties"], bool)
        for child in node.values():
            _assert_additional_properties_are_bools(child)
    elif isinstance(node, list):
        for element in node:
            _assert_additional_properties_are_bools(element)


def test_published_tools_are_read_only_and_schemas_use_bool_additional_properties() -> None:
    for tool in mcp_tools:
        annotations = tool.annotations
        assert annotations is not None
        assert annotations.read_only_hint is True
        assert annotations.destructive_hint is False
        assert annotations.open_world_hint is True
        assert annotations.idempotent_hint is None
        assert annotations.title is None
        # Python 3.10's generator omits additionalProperties on funnel_breakdown.
        # 3.11+ emits a schema object, which sanitize turns into true. Either is
        # safe for Claude Desktop; a schema object is not.
        _assert_additional_properties_are_bools(tool.input_schema)

    funnel = next(tool for tool in mcp_tools if tool.name == "run_funnel_report")
    breakdown = funnel.input_schema["properties"]["funnel_breakdown"]
    assert breakdown.get("additionalProperties", True) is True
    property_id = funnel.input_schema["properties"]["property_id"]
    assert property_id.get("type") == "string"
    assert "anyOf" not in property_id


def test_explicit_required_survives_a_generator_that_omits_it() -> None:
    expected = {
        "run_report": {"property_id", "date_ranges", "dimensions", "metrics"},
        "run_realtime_report": {"property_id", "dimensions", "metrics"},
        "run_funnel_report": {"property_id", "funnel_steps", "date_ranges"},
        "list_key_events": {"property_id"},
    }
    for name, required in expected.items():
        tool = mcp_types.Tool(
            name=name,
            description="schema hygiene fixture",
            inputSchema={"type": "object", "properties": {}},
        )
        _normalize_input_schema(tool)
        assert set(tool.input_schema["required"]) == required

    summaries = mcp_types.Tool(
        name="get_account_summaries",
        description="schema hygiene fixture",
        inputSchema={"type": "object", "properties": {}},
    )
    _normalize_input_schema(summaries)
    assert "required" not in summaries.input_schema


async def test_list_tools_publishes_the_same_annotations() -> None:
    listed = await list_tools(None, None)  # type: ignore[arg-type]
    assert {tool.name for tool in listed.tools} == {tool.name for tool in mcp_tools}
    for tool in listed.tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.open_world_hint is True


async def test_missing_required_metric_is_a_schema_error() -> None:
    seen: list[dict[str, Any]] = []

    async def fake_run_async(
        *,
        args: dict[str, Any],
        tool_context: object = None,
    ) -> dict[str, Any]:
        seen.append(args)
        return {"ok": True}

    original = coordinator.tool_map["run_report"].run_async
    coordinator.tool_map["run_report"].run_async = fake_run_async
    try:
        result = await call_mcp_tool(
            None,  # type: ignore[arg-type]
            mcp_types.CallToolRequestParams(
                name="run_report",
                arguments={
                    "property_id": "111",
                    "date_ranges": [{"start_date": "2025-01-01", "end_date": "2025-01-01"}],
                    "dimensions": ["date"],
                },
            ),
        )
    finally:
        coordinator.tool_map["run_report"].run_async = original

    assert result.is_error is True
    assert isinstance(result.content[0].text, str)
    assert result.content[0].text.startswith("Input validation error:")
    assert seen == []
