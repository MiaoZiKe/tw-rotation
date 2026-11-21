"""整天全市場法人補抓「回空」時，要說得出是哪一關壞了（2026-11-13）。

事故：11-12 那輪 source_health 只寫「回空（0 筆）」，沒有任何原因可以看。
Actions log 才查得到：證交所 T86 回 HTML、櫃買只回一部分、FinMind 整天額度用盡。
這份測試鎖的是「原因要掛在 attrs 上」；判定本身（進不進 empty、亮不亮燈）不在這裡改。
"""
from __future__ import annotations

import pandas as pd

from pipeline import inst_bulk
from pipeline.sources import inst_official
from pipeline.util import http, store


def _px_one_day(day: str, n: int = 600) -> pd.DataFrame:
    # thin_dates 要求價量當天至少 500 檔才會去判斷法人缺口
    return pd.DataFrame({"date": [day] * n, "code": [f"{i:04d}" for i in range(n)]})


def _patch(monkeypatch, *, official: pd.DataFrame, budget: int):
    monkeypatch.setattr(inst_official, "fetch_all", lambda use_cache=True: official)
    monkeypatch.setattr(http, "finmind_budget_left", lambda: budget)

    def fake_read(table, *, years=None):
        if table == "price_daily":
            return _px_one_day("2026-11-12")
        return pd.DataFrame()          # inst_daily 當天還沒有任何列

    monkeypatch.setattr(store, "read", fake_read)


def test_官方空且額度用盡_原因寫進attrs(monkeypatch):
    _patch(monkeypatch, official=pd.DataFrame(), budget=0)
    df = inst_bulk.fill_inst_bulk()
    assert df.empty
    err = df.attrs.get("error", "")
    assert "官方" in err and "FinMind 額度用盡" in err and "2026-11-12" in err


def test_官方有資料_不掛錯誤字樣(monkeypatch):
    official = pd.DataFrame({"date": ["2026-11-12"] * 3, "code": ["2330", "2317", "2454"]})
    _patch(monkeypatch, official=official, budget=0)
    df = inst_bulk.fill_inst_bulk()
    assert len(df) == 3
    assert "error" not in df.attrs
