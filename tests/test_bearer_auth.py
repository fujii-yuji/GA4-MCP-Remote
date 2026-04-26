"""Unit tests for the Bearer header matcher (constant-time comparison)."""

from __future__ import annotations

import pytest

from ga4_remote_mcp.transport.middleware import _bearer_matches_authorization_header


def test_matches_exact_token() -> None:
    assert _bearer_matches_authorization_header("Bearer secret-token", "secret-token") is True


def test_matches_case_insensitive_scheme() -> None:
    assert _bearer_matches_authorization_header("bearer secret-token", "secret-token") is True
    assert _bearer_matches_authorization_header("BEARER secret-token", "secret-token") is True


def test_matches_with_surrounding_whitespace() -> None:
    assert _bearer_matches_authorization_header("  Bearer  secret-token  ", "secret-token") is True
    assert _bearer_matches_authorization_header("Bearer secret-token", "  secret-token  ") is True


def test_rejects_wrong_token() -> None:
    assert _bearer_matches_authorization_header("Bearer wrong", "secret-token") is False


def test_rejects_token_that_is_a_prefix_of_secret() -> None:
    # Length differences must not authenticate even with shared prefixes.
    assert _bearer_matches_authorization_header("Bearer secret", "secret-token") is False
    assert _bearer_matches_authorization_header("Bearer secret-token-x", "secret-token") is False


def test_rejects_missing_scheme() -> None:
    assert _bearer_matches_authorization_header("secret-token", "secret-token") is False


def test_rejects_non_bearer_scheme() -> None:
    assert _bearer_matches_authorization_header("Basic secret-token", "secret-token") is False
    assert _bearer_matches_authorization_header("Token secret-token", "secret-token") is False


@pytest.mark.parametrize("header", ["", "   ", None])
def test_rejects_empty_header(header: str | None) -> None:
    assert _bearer_matches_authorization_header(header or "", "secret-token") is False


@pytest.mark.parametrize("secret", ["", "   ", None])
def test_rejects_empty_secret_even_with_matching_header(secret: str | None) -> None:
    # Settings validation already forbids empty secret in bearer mode, but the
    # matcher must still fail closed if it ever reaches this branch.
    assert _bearer_matches_authorization_header("Bearer ", secret or "") is False
    assert _bearer_matches_authorization_header("Bearer something", secret or "") is False


def test_rejects_unicode_normalisation_collisions() -> None:
    # Bytes comparison ensures visually similar strings do not match.
    assert _bearer_matches_authorization_header("Bearer caf\u00e9", "cafe\u0301") is False
