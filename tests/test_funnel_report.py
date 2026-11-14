"""Funnel report request building, without calling Google."""

from __future__ import annotations

from google.analytics import data_v1alpha

from ga4_remote_mcp.ga.coordinator import mcp_tools
from ga4_remote_mcp.ga.tools.reporting.funnel import run_funnel_report


class _FakeAlphaClient:
    def __init__(self) -> None:
        self.request: data_v1alpha.RunFunnelReportRequest | None = None

    async def run_funnel_report(
        self, request: data_v1alpha.RunFunnelReportRequest
    ) -> data_v1alpha.RunFunnelReportResponse:
        self.request = request
        return data_v1alpha.RunFunnelReportResponse()


async def test_run_funnel_report_builds_event_steps(monkeypatch) -> None:
    client = _FakeAlphaClient()
    monkeypatch.setattr(
        "ga4_remote_mcp.ga.tools.reporting.funnel.create_data_api_alpha_client",
        lambda: client,
    )

    result = await run_funnel_report(
        property_id="properties/123",
        funnel_steps=[
            {"name": "Session start", "event": "session_start"},
            {"event": "purchase"},
        ],
        date_ranges=[{"start_date": "2025-01-01", "end_date": "2025-01-07", "name": "week"}],
        funnel_breakdown={"breakdown_dimension": "deviceCategory"},
        funnel_next_action={"next_action_dimension": "eventName", "limit": 5},
    )

    assert isinstance(result, dict)
    request = client.request
    assert request is not None
    assert request.property == "properties/123"
    assert request.date_ranges[0].start_date == "2025-01-01"
    assert request.date_ranges[0].end_date == "2025-01-07"
    assert [step.name for step in request.funnel.steps] == ["Session start", "Step 2"]
    assert request.funnel.steps[0].filter_expression.funnel_event_filter.event_name == (
        "session_start"
    )
    assert request.funnel.steps[1].filter_expression.funnel_event_filter.event_name == "purchase"
    assert request.funnel_breakdown.breakdown_dimension.name == "deviceCategory"
    assert request.funnel_next_action.next_action_dimension.name == "eventName"
    assert request.funnel_next_action.limit == 5


def test_funnel_schema_requires_property_steps_and_dates() -> None:
    tool = next(item for item in mcp_tools if item.name == "run_funnel_report")
    required = set(tool.input_schema.get("required") or [])
    assert {"property_id", "funnel_steps", "date_ranges"} <= required
    property_schema = tool.input_schema["properties"]["property_id"]
    assert property_schema.get("type") == "string"
