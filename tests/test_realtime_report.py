"""Realtime report request building, without calling Google."""

from __future__ import annotations

from google.analytics import data_v1beta

from ga4_remote_mcp.ga.coordinator import mcp_tools
from ga4_remote_mcp.ga.tools.reporting.realtime import run_realtime_report


class _FakeDataClient:
    def __init__(self) -> None:
        self.request: data_v1beta.RunRealtimeReportRequest | None = None

    async def run_realtime_report(
        self, request: data_v1beta.RunRealtimeReportRequest
    ) -> data_v1beta.RunRealtimeReportResponse:
        self.request = request
        return data_v1beta.RunRealtimeReportResponse()


def _patch_client(monkeypatch, client: _FakeDataClient) -> None:
    monkeypatch.setattr(
        "ga4_remote_mcp.ga.tools.reporting.realtime.create_data_api_client",
        lambda: client,
    )


async def test_omitted_minute_ranges_leave_the_field_empty(monkeypatch) -> None:
    client = _FakeDataClient()
    _patch_client(monkeypatch, client)

    result = await run_realtime_report(
        property_id="123456789",
        dimensions=["country"],
        metrics=["activeUsers"],
        limit=10,
    )

    assert isinstance(result, dict)
    request = client.request
    assert request is not None
    assert request.property == "properties/123456789"
    assert len(request.minute_ranges) == 0
    assert request.limit == 10
    assert [dimension.name for dimension in request.dimensions] == ["country"]


async def test_empty_minute_ranges_leave_the_field_empty(monkeypatch) -> None:
    client = _FakeDataClient()
    _patch_client(monkeypatch, client)

    await run_realtime_report(
        property_id="123456789",
        dimensions=["country"],
        metrics=["activeUsers"],
        minute_ranges=[],
    )

    request = client.request
    assert request is not None
    assert len(request.minute_ranges) == 0


async def test_one_minute_range_is_copied_onto_the_request(monkeypatch) -> None:
    client = _FakeDataClient()
    _patch_client(monkeypatch, client)

    await run_realtime_report(
        property_id="properties/123",
        dimensions=["country"],
        metrics=["activeUsers"],
        minute_ranges=[{"name": "last5", "start_minutes_ago": 4, "end_minutes_ago": 0}],
    )

    request = client.request
    assert request is not None
    assert request.property == "properties/123"
    assert len(request.minute_ranges) == 1
    window = request.minute_ranges[0]
    assert window.name == "last5"
    assert window.start_minutes_ago == 4
    assert window.end_minutes_ago == 0


async def test_two_minute_ranges_are_copied_onto_the_request(monkeypatch) -> None:
    client = _FakeDataClient()
    _patch_client(monkeypatch, client)

    await run_realtime_report(
        property_id="123",
        dimensions=["country"],
        metrics=["activeUsers"],
        minute_ranges=[
            {"name": "last5", "start_minutes_ago": 4, "end_minutes_ago": 0},
            {"name": "earlier", "start_minutes_ago": 29, "end_minutes_ago": 15},
        ],
    )

    request = client.request
    assert request is not None
    assert [window.name for window in request.minute_ranges] == ["last5", "earlier"]
    assert request.minute_ranges[1].start_minutes_ago == 29
    assert request.minute_ranges[1].end_minutes_ago == 15


def test_realtime_schema_keeps_minute_ranges_optional() -> None:
    tool = next(item for item in mcp_tools if item.name == "run_realtime_report")
    required = set(tool.input_schema.get("required") or [])
    assert required == {"property_id", "dimensions", "metrics"}
    minute_ranges = tool.input_schema["properties"]["minute_ranges"]
    assert minute_ranges.get("type") == "array"
    assert "minute_ranges" not in required
    property_id = tool.input_schema["properties"]["property_id"]
    assert property_id.get("type") == "string"
    assert "anyOf" not in property_id
    assert "At most 2" in (tool.description or "")
