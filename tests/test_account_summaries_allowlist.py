"""get_account_summaries is limited to the property allowlist.

The Admin API pager yields AccountSummary messages, not response pages.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from google.analytics import admin_v1beta

from ga4_remote_mcp.config.settings import Settings, clear_settings_cache, get_settings
from ga4_remote_mcp.ga.tools.admin import info
from ga4_remote_mcp.ga.tools.utils import proto_to_dict
from ga4_remote_mcp.policy.allowlist import filter_account_summaries

ALLOWED_ID = "111001"
SECOND_ALLOWED_ID = "222002"
SECRET_ID = "999001"
HIDDEN_PROPERTY_ID = "888001"
SECRET_NAME = "Secret Property North"
HIDDEN_ACCOUNT = "Hidden Account Only"
OTHER_SECRET = "Other Secret Property"
NAMELESS_SECRET = "Nameless Secret"
LATER_ACCOUNT = "Later Allowed Account"


def _settings(monkeypatch: pytest.MonkeyPatch, *, allow_all: str, ids: str) -> Settings:
    monkeypatch.setenv("GA4MCP_ENV", "development")
    monkeypatch.setenv("GA4MCP_AUTH_MODE", "none")
    monkeypatch.setenv("GA4MCP_ALLOW_ALL_PROPERTIES", allow_all)
    monkeypatch.setenv("GA4MCP_ALLOWED_PROPERTY_IDS", ids)
    clear_settings_cache()
    return get_settings()


def _summaries() -> list[dict[str, Any]]:
    return [
        {
            "name": "accountSummaries/1",
            "account": "accounts/1",
            "display_name": "Mixed Account",
            "unexpected_roster": [f"properties/{SECRET_ID}", SECRET_NAME],
            "property_summaries": [
                {
                    "property": f"properties/{ALLOWED_ID}",
                    "display_name": "Public Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": "accounts/1",
                    "unexpected_note": SECRET_NAME,
                },
                {
                    "property": f"properties/{SECRET_ID}",
                    "display_name": SECRET_NAME,
                    "parent": "accounts/1",
                },
                {"display_name": NAMELESS_SECRET},
                {
                    "property": f"properties/{SECOND_ALLOWED_ID}",
                    "display_name": "Subproperty",
                    "property_type": "PROPERTY_TYPE_SUBPROPERTY",
                    "parent": f"properties/{SECRET_ID}",
                },
            ],
        },
        {
            "name": "accountSummaries/2",
            "account": "accounts/2",
            "display_name": HIDDEN_ACCOUNT,
            "property_summaries": [
                {
                    "property": f"properties/{HIDDEN_PROPERTY_ID}",
                    "display_name": OTHER_SECRET,
                    "parent": "accounts/2",
                }
            ],
        },
        {
            "name": "accountSummaries/3",
            "account": "accounts/3",
            "display_name": LATER_ACCOUNT,
            "property_summaries": [
                {
                    "property": f"properties/{ALLOWED_ID}",
                    "display_name": "Later Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": "accounts/3",
                }
            ],
        },
    ]


def test_filter_keeps_only_allowlisted_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        monkeypatch,
        allow_all="false",
        ids=f"{ALLOWED_ID},properties/{SECOND_ALLOWED_ID}",
    )
    summaries = _summaries()
    original = json.loads(json.dumps(summaries))

    filtered = filter_account_summaries(summaries, settings)

    assert summaries == original
    assert filtered == [
        {
            "name": "accountSummaries/1",
            "account": "accounts/1",
            "display_name": "Mixed Account",
            "property_summaries": [
                {
                    "property": f"properties/{ALLOWED_ID}",
                    "display_name": "Public Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": "accounts/1",
                },
                {
                    "property": f"properties/{SECOND_ALLOWED_ID}",
                    "display_name": "Subproperty",
                    "property_type": "PROPERTY_TYPE_SUBPROPERTY",
                },
            ],
        },
        {
            "name": "accountSummaries/3",
            "account": "accounts/3",
            "display_name": LATER_ACCOUNT,
            "property_summaries": [
                {
                    "property": f"properties/{ALLOWED_ID}",
                    "display_name": "Later Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": "accounts/3",
                }
            ],
        },
    ]
    rendered = json.dumps(filtered)
    for secret in (
        SECRET_ID,
        SECRET_NAME,
        HIDDEN_PROPERTY_ID,
        HIDDEN_ACCOUNT,
        OTHER_SECRET,
        NAMELESS_SECRET,
        "accounts/2",
        "unexpected_roster",
        "unexpected_note",
    ):
        assert secret not in rendered


def test_filter_allow_all_keeps_every_property(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, allow_all="true", ids="")
    summaries = _summaries()

    filtered = filter_account_summaries(summaries, settings)

    assert filtered is summaries
    rendered = json.dumps(filtered)
    assert SECRET_NAME in rendered
    assert SECRET_ID in rendered
    assert HIDDEN_ACCOUNT in rendered


def test_filter_empty_allowlist_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, allow_all="false", ids="")
    filtered = filter_account_summaries(_summaries(), settings)
    assert filtered == []
    assert SECRET_NAME not in json.dumps(filtered)
    assert SECRET_ID not in json.dumps(filtered)


def _protos() -> list[admin_v1beta.AccountSummary]:
    return [
        admin_v1beta.AccountSummary(
            name="accountSummaries/1",
            account="accounts/1",
            display_name="Mixed Account",
            property_summaries=[
                admin_v1beta.PropertySummary(
                    property=f"properties/{ALLOWED_ID}",
                    display_name="Public Blog",
                    property_type=admin_v1beta.PropertyType.PROPERTY_TYPE_ORDINARY,
                    parent="accounts/1",
                ),
                admin_v1beta.PropertySummary(
                    property=f"properties/{SECRET_ID}",
                    display_name=SECRET_NAME,
                    parent="accounts/1",
                ),
            ],
        ),
        admin_v1beta.AccountSummary(
            name="accountSummaries/2",
            account="accounts/2",
            display_name=HIDDEN_ACCOUNT,
            property_summaries=[
                admin_v1beta.PropertySummary(
                    property=f"properties/{HIDDEN_PROPERTY_ID}",
                    display_name=OTHER_SECRET,
                    parent="accounts/2",
                )
            ],
        ),
        admin_v1beta.AccountSummary(
            name="accountSummaries/3",
            account="accounts/3",
            display_name=LATER_ACCOUNT,
            property_summaries=[
                admin_v1beta.PropertySummary(
                    property=f"properties/{SECOND_ALLOWED_ID}",
                    display_name="Later Blog",
                    property_type=admin_v1beta.PropertyType.PROPERTY_TYPE_ORDINARY,
                    parent=f"properties/{ALLOWED_ID}",
                )
            ],
        ),
    ]


class _Pager:
    def __init__(self, items: list[object]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _Pager:
        return self

    async def __anext__(self) -> object:
        try:
            return next(self._items)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _install_admin_client(
    monkeypatch: pytest.MonkeyPatch,
    items: list[object],
    calls: list[str],
) -> None:
    class _Client:
        async def list_account_summaries(self) -> _Pager:
            calls.append("list_account_summaries")
            return _Pager(items)

    monkeypatch.setattr(info, "create_admin_api_client", lambda: _Client())


@pytest.mark.asyncio
async def test_tool_empty_allowlist_does_not_call_admin_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, allow_all="false", ids="")
    calls: list[str] = []
    _install_admin_client(monkeypatch, _protos(), calls)

    result = await info.get_account_summaries()

    assert result == []
    assert calls == []


@pytest.mark.asyncio
async def test_tool_filters_account_summaries_from_protos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(
        monkeypatch,
        allow_all="false",
        ids=f"{ALLOWED_ID},properties/{SECOND_ALLOWED_ID}",
    )
    calls: list[str] = []
    protos = _protos()
    _install_admin_client(monkeypatch, protos, calls)

    result = await info.get_account_summaries()

    assert calls == ["list_account_summaries"]
    assert result == [
        {
            "name": "accountSummaries/1",
            "account": "accounts/1",
            "display_name": "Mixed Account",
            "property_summaries": [
                {
                    "property": f"properties/{ALLOWED_ID}",
                    "display_name": "Public Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": "accounts/1",
                }
            ],
        },
        {
            "name": "accountSummaries/3",
            "account": "accounts/3",
            "display_name": LATER_ACCOUNT,
            "property_summaries": [
                {
                    "property": f"properties/{SECOND_ALLOWED_ID}",
                    "display_name": "Later Blog",
                    "property_type": "PROPERTY_TYPE_ORDINARY",
                    "parent": f"properties/{ALLOWED_ID}",
                }
            ],
        },
    ]
    rendered = json.dumps(result)
    assert SECRET_NAME not in rendered
    assert SECRET_ID not in rendered
    assert HIDDEN_ACCOUNT not in rendered
    assert proto_to_dict(protos[0])["property_summaries"][1]["display_name"] == SECRET_NAME


@pytest.mark.asyncio
async def test_tool_allow_all_returns_unfiltered_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch, allow_all="true", ids="")
    calls: list[str] = []
    protos = _protos()
    _install_admin_client(monkeypatch, protos, calls)

    result = await info.get_account_summaries()

    assert calls == ["list_account_summaries"]
    assert result == [proto_to_dict(summary) for summary in protos]
    assert SECRET_NAME in json.dumps(result)
