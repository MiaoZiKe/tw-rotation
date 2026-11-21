"""上櫃融資融券：2026-11-06 實測只有個股餘額端點，加總成整體張數；金額留空。"""
import math

import pandas as pd

from pipeline.sources import tpex_margin as tm


def _raw(n=120, date="1151106"):
    return [{"Date": date, "SecuritiesCompanyCode": str(1000 + i), "MarginPurchaseBalancePreviousDay": "10",
             "MarginPurchaseBalance": "12", "ShortSaleBalancePreviousDay": "1", "ShortSaleBalance": "2"} for i in range(n)]


def test_加總成整體一天一列_日期轉西元_金額留空():
    df = tm.parse_balance(_raw())
    r = df.iloc[0]
    assert len(df) == 1 and r["date"] == "2026-11-06"
    assert r["margin_lots"] == 1440 and r["margin_lots_prev"] == 1200 and r["short_lots"] == 240 and r["short_lots_prev"] == 120
    assert math.isnan(r["margin_money"])
    assert list(df.columns) == tm.COLS


def test_不完整或多日期或欄位改了都不收():
    assert tm.parse_balance(_raw(50)).empty
    assert tm.parse_balance(_raw(60) + _raw(60, "1151105")).empty
    assert tm.parse_balance([{"Date": "1151106", "X": 1}] * 150).empty
    assert tm.parse_balance(None).empty


def test_fetch_走餘額端點(monkeypatch):
    monkeypatch.setattr(tm, "_get", lambda url: (200, _raw()) if url.endswith(tm.BALANCE) else (404, None))
    out = tm.fetch()
    assert not out.empty and out.iloc[0]["date"] == "2026-11-06"


def test_餘額端點掛了_退回舊流程_也不炸(monkeypatch):
    monkeypatch.setattr(tm, "_get", lambda url: (None, None))
    assert tm.fetch().empty
