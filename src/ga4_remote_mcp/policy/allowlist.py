"""Property allowlist (tech §9.2)."""

from __future__ import annotations

from ga4_remote_mcp.config.settings import Settings

TOOLS_REQUIRING_PROPERTY = frozenset(
    {
        "list_google_ads_links",
        "get_property_details",
        "list_property_annotations",
        "get_custom_dimensions_and_metrics",
        "run_report",
        "run_realtime_report",
    }
)


def normalize_property_id(raw: object) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("properties/"):
        s = s.split("/", 1)[-1].strip()
    return s


def property_allowed(property_id: str, settings: Settings) -> bool:
    if settings.allow_all_properties:
        return True
    allowed = settings.parsed_allowed_property_ids()
    return property_id in allowed
