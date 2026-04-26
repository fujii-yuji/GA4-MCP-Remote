"""Smoke tests for ``scripts/deploy-cloud-run.sh``'s production-auth guard.

These tests run the script in a subprocess with a hand-built environment
and a ``PATH`` that intentionally excludes ``gcloud``. The goal is to
exercise *only* the early guard logic; the gcloud invocations further
down are expected to fail (or simply not be reached) and that is fine.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "deploy-cloud-run.sh"


def _safe_path() -> str:
    """Return a PATH that has core shell utilities but never resolves ``gcloud``."""
    candidate_dirs = ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    return ":".join(d for d in candidate_dirs if pathlib.Path(d).exists())


pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="bash is required for shell-script smoke tests",
)


def test_script_passes_static_syntax_check() -> None:
    """Regression net: ``bash -n`` catches accidental shell-syntax mistakes."""
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_script_blocks_when_bearer_secret_unset() -> None:
    env = {
        "PATH": _safe_path(),
        "GCP_PROJECT_ID": "dummy-project",
        "GA4MCP_ALLOWED_PROPERTY_IDS": "123456789",
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "GA4MCP_BEARER_SECRET_NAME" in result.stderr
    # The guard must fire before any gcloud invocation.
    combined = result.stdout + result.stderr
    assert "Project=" not in combined  # the echo line that runs after the guard


def test_script_passes_guard_when_bearer_secret_set() -> None:
    env = {
        "PATH": _safe_path(),
        "GCP_PROJECT_ID": "dummy-project",
        "GA4MCP_ALLOWED_PROPERTY_IDS": "123456789",
        "GA4MCP_BEARER_SECRET_NAME": "ga4-remote-mcp-bearer",
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    # The script may still fail later (gcloud not on PATH) but our guard
    # must NOT be the cause.
    combined = result.stdout + result.stderr
    assert "GA4MCP_BEARER_SECRET_NAME is not set" not in combined
