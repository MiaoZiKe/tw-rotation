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


@pytest.fixture(autouse=True)
def _續補不打整天全市場法人(monkeypatch):
    """2026-10-20：refresh_stale_inst 開頭會先試 inst_bulk.fill_inst_bulk（讀真實資料湖＋打 FinMind）。
    續補的既有測試不測它，一律換成空的替身；inst_bulk 本身的測試（test_data_fresh_1020）直接呼叫真模組，不受影響。"""
    import types

    import pandas as pd

    from pipeline import run_backfill
    monkeypatch.setattr(run_backfill, "inst_bulk", types.SimpleNamespace(
        fill_inst_bulk=lambda *a, **k: pd.DataFrame(), site_codes=lambda: []))
    yield


@pytest.fixture(autouse=True)
def _官方法人來源不打網路(monkeypatch):
    """2026-10-20：inst_bulk.fill_inst_bulk 開頭會打官方法人端點（證交所／櫃買）。
    既有測試一律換成空替身；inst_official 自己的測試（test_inst_official）直接換 _get，不受影響。"""
    import pandas as pd

    from pipeline.sources import inst_official
    inst_official._cache.clear()
    monkeypatch.setattr(inst_official, "fetch_all", lambda *a, **k: pd.DataFrame())
    yield
