"""全體測試共用的隔離設定。

2026-10-03（DECISIONS #311）：`http` 的 FinMind 錯誤紀錄是模組層級狀態（全域最後一次＋每個資料集各一筆），
不清掉的話，上一支測試留下的錯誤會被下一支測試當成「這個資料集的封印理由」——
那正是 #311 要修的正式環境 bug 在測試裡的翻版。每支測試開始前一律清空。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.util import http  # noqa: E402


@pytest.fixture(autouse=True)
def _清空FinMind錯誤紀錄(monkeypatch):
    monkeypatch.setattr(http, "_last_error", None)
    monkeypatch.setattr(http, "_last_errors", {})
    yield
