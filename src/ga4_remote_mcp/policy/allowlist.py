"""Property allowlist (tech §9.2)."""

from __future__ import annotations

from typing import Any

from ga4_remote_mcp.config.settings import Settings

TOOLS_REQUIRING_PROPERTY = frozenset(
    {
        "list_google_ads_links",
        "get_property_details",
        "list_property_annotations",
        "get_custom_dimensions_and_metrics",
        "run_report",
        "run_funnel_report",
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


# AccountSummary / PropertySummary fields from the Admin API. Anything else
# is dropped so an unexpected field cannot carry an unfiltered property name.
_ACCOUNT_KEYS = ("name", "account", "display_name")
_PROPERTY_KEYS = ("property", "display_name", "property_type", "parent")


def _pick(src: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: src[key] for key in keys if key in src}


def filter_account_summaries(
    summaries: list[dict[str, Any]],
    settings: Settings,
) -> list[dict[str, Any]]:
    """Keep only allowlisted properties in account-summary dicts.

    ``list_account_summaries`` yields ``AccountSummary`` messages, not
    response pages. ``GA4MCP_ALLOW_ALL_PROPERTIES`` returns ``summaries``
    unchanged. An empty allowlist returns ``[]``. Accounts with no remaining
    properties are omitted. Only known account and property fields are copied.
    A ``parent`` that names a property outside the allowlist is omitted.
    """
    if settings.allow_all_properties:
        return summaries
    allowed = settings.parsed_allowed_property_ids()
    if not allowed:
        return []

    kept_accounts: list[dict[str, Any]] = []
    for account in summaries:
        if not isinstance(account, dict):
            continue
        properties = account.get("property_summaries")
        if not isinstance(properties, list):
            properties = []
        kept_properties = [
            _public_property(prop, allowed)
            for prop in properties
            if isinstance(prop, dict) and _property_summary_allowed(prop, allowed)
        ]
        if not kept_properties:
            continue
        kept_account = _pick(account, _ACCOUNT_KEYS)
        kept_account["property_summaries"] = kept_properties
        kept_accounts.append(kept_account)
    return kept_accounts


def _property_summary_allowed(prop: dict[str, Any], allowed: frozenset[str]) -> bool:
    normalized = normalize_property_id(prop.get("property"))
    return normalized is not None and normalized in allowed


def _public_property(prop: dict[str, Any], allowed: frozenset[str]) -> dict[str, Any]:
    picked = _pick(prop, _PROPERTY_KEYS)
    parent = picked.get("parent")
    if not isinstance(parent, str) or not parent.startswith("properties/"):
        return picked
    parent_id = normalize_property_id(parent)
    if parent_id is None or parent_id not in allowed:
        picked.pop("parent", None)
    return picked
