"""実 GA / 実トークンが必要なテスト用プレースホルダ。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="prd §25.5 の I* ケースは認証情報取得後に実装")
def test_integration_placeholder() -> None:
    """将来: list_tools / run_report を実プロパティで検証。"""
