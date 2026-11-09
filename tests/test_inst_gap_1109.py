"""2026-11-09 上市個股法人只有 456 檔（近 10 日 1,145 檔）的兩個根因與修法。

根因 A：上市法人只有 FinMind 逐檔一個來源（openapi /fund/T86 回 HTML、整天全市場要 sponsor 等級），
        每日管線只補名單內的檔，名單外的靠歷史回補的 refresh_stale_inst 續補。
根因 B：續補的完成旗標只看台北日期；11-09 01:11 價量還停在 11-06 時寫下 {done, date=11-09, latest=11-06}，
        當天價量進湖後旗標仍擋住續補，整天沒人補。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from pipeline import run_backfill, run_daily


# ------------------------------------------------------------------ 根因 B：旗標要對得上價量日
def test_旗標日期對且價量日沒變_算數():
    flag = {"done": True, "date": "2026-11-09", "latest": "2026-11-09"}
    assert run_backfill.inst_fresh_is_current(flag, date(2026, 11, 9), "2026-11-09")


def test_凌晨做的旗標_價量日進湖後作廢():
    """11-09 事故原樣：旗標 latest=11-06，湖裡價量已到 11-09 → 不能再擋。"""
    flag = {"done": True, "date": "2026-11-09", "latest": "2026-11-06"}
    assert not run_backfill.inst_fresh_is_current(flag, date(2026, 11, 9), "2026-11-09")


def test_旗標日期不是今天或沒做完_不算數():
    assert not run_backfill.inst_fresh_is_current({"done": True, "date": "2026-11-08", "latest": "2026-11-06"},
                                                  date(2026, 11, 9), "2026-11-06")
    assert not run_backfill.inst_fresh_is_current({"done": False, "date": "2026-11-09", "latest": "2026-11-09"},
                                                  date(2026, 11, 9), "2026-11-09")
    assert not run_backfill.inst_fresh_is_current(None, date(2026, 11, 9), "2026-11-09")


def test_讀不到價量日_維持舊行為():
    assert run_backfill.inst_fresh_is_current({"done": True, "date": "2026-11-09", "latest": "x"},
                                              date(2026, 11, 9), None)


# ------------------------------------------------------------------ 根因 A：名單補完後繼續補上市缺口
def _px():
    return pd.DataFrame({
        "date": ["2026-11-09"] * 6,
        "code": ["2330", "2317", "1101", "6488", "2454", "030001"],
        "market": ["TWSE", "TWSE", "TWSE", "TPEX", "TWSE", "TWSE"],
        "turnover": [9e9, 5e9, 1e9, 8e9, 7e9, 1e8],
    })


def test_缺口只收上市普通股_成交值大的先補(monkeypatch):
    monkeypatch.setattr(run_daily.store, "read", lambda t, **k: _px())
    got = run_daily.market_gap_codes("2026-11-09", {"2317"})
    assert got == ["2330", "2454", "1101"]            # 2317 已在名單；6488 上櫃不逐檔；權證 030001 不收


def test_讀價量壞掉回空不丟例外(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("壞了")
    monkeypatch.setattr(run_daily.store, "read", boom)
    assert run_daily.market_gap_codes("2026-11-09", set()) == []


def test_逐檔補_名單之外的缺口也補_並替後面步驟留額度(monkeypatch):
    inst_have = pd.DataFrame({"date": ["2026-11-09"], "code": ["2317"]})
    px = _px()
    monkeypatch.setattr(run_daily.store, "read",
                        lambda t, **k: inst_have if t == "inst_daily" else px)
    monkeypatch.setattr(run_daily.http, "finmind_budget_left", lambda: run_daily.FINMIND_RESERVE + 2)
    asked = []

    def fake_inst(code, start, end=None, wait=True):
        asked.append(code)
        return pd.DataFrame({"date": ["2026-11-09"], "code": [code]})

    monkeypatch.setattr(run_daily.finmind, "institutional", fake_inst)
    out = run_daily.fetch_institutional(["2330"], "2026-11-09", 0)
    # 名單 1 檔 ＋ 缺口只放得下 (額度 − 名單 − 保留) = 1 檔，成交值最大的 2454 先
    assert asked == ["2330", "2454"]
    assert len(out) == 2


def test_額度只夠名單_就不補缺口(monkeypatch):
    monkeypatch.setattr(run_daily.store, "read",
                        lambda t, **k: pd.DataFrame() if t == "inst_daily" else _px())
    monkeypatch.setattr(run_daily.http, "finmind_budget_left", lambda: run_daily.FINMIND_RESERVE)
    asked = []
    monkeypatch.setattr(run_daily.finmind, "institutional",
                        lambda code, s, e=None, wait=True: asked.append(code) or pd.DataFrame())
    run_daily.fetch_institutional(["2330"], "2026-11-09", 0)
    assert asked == ["2330"]
