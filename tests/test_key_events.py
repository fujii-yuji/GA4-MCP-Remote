"""Key event definition listing, without calling Google."""

from __future__ import annotations

from google.analytics import admin_v1beta

from ga4_remote_mcp.config.settings import clear_settings_cache, get_settings
from ga4_remote_mcp.ga.coordinator import mcp_tools
from ga4_remote_mcp.ga.tools.admin.info import list_key_events
from ga4_remote_mcp.policy.allowlist import TOOLS_REQUIRING_PROPERTY
from ga4_remote_mcp.policy.guardrails import validate_tool_arguments


class _Pager:
    def __init__(self, items: list[admin_v1beta.KeyEvent]) -> None:
        self._items = items

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for item in self._items:
            yield item


class _FakeAdminClient:
    def __init__(self) -> None:
        self.request: admin_v1beta.ListKeyEventsRequest | None = None

    async def list_key_events(
        self, request: admin_v1beta.ListKeyEventsRequest
    ) -> _Pager:
        self.request = request
        return _Pager(
            [
                admin_v1beta.KeyEvent(
                    name="properties/123/keyEvents/purchase",
                    event_name="purchase",
                    counting_method=admin_v1beta.KeyEvent.CountingMethod.ONCE_PER_EVENT,
                    custom=True,
                    deletable=True,
                )
            ]
        )


async def test_list_key_events_requests_property_definitions(monkeypatch) -> None:
    client = _FakeAdminClient()
    monkeypatch.setattr(
        "ga4_remote_mcp.ga.tools.admin.info.create_admin_api_client",
        lambda: client,
    )

    result = await list_key_events("properties/123")

    assert client.request is not None
    assert client.request.parent == "properties/123"
    assert result == [
        {
            "name": "properties/123/keyEvents/purchase",
            "event_name": "purchase",
            "counting_method": "ONCE_PER_EVENT",
            "custom": True,
            "deletable": True,
        }
    ]


def test_list_key_events_schema_is_property_id_string() -> None:
    tool = next(item for item in mcp_tools if item.name == "list_key_events")
    assert set(tool.input_schema.get("required") or []) == {"property_id"}
    property_schema = tool.input_schema["properties"]["property_id"]
    assert property_schema.get("type") == "string"
    assert "anyOf" not in property_schema
    assert "list_key_events" in TOOLS_REQUIRING_PROPERTY


def test_list_key_events_skips_report_caps(monkeypatch) -> None:
    monkeypatch.setenv("GA4MCP_MAX_ROW_LIMIT", "10")
    monkeypatch.setenv("GA4MCP_MAX_DATE_RANGE_DAYS", "1")
    clear_settings_cache()
    arguments = {"property_id": "123"}

    ok, code, mutated, message = validate_tool_arguments(
        "list_key_events", arguments, get_settings()
    )

    assert (ok, code, mutated, message) == (True, None, None, None)
    assert arguments == {"property_id": "123"}
