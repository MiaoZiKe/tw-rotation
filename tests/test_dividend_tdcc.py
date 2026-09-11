"""每日管線兩個曾連續失敗的步驟：twse.dividend（欄位改版）與 tdcc.shareholding（編碼／BOM）。

t187ap45_L 的欄位是 2026-09-11 從線上端點抄下來的實際表頭；TDCC 用帶 BOM 的 CSV 模擬。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline.sources import tdcc, twse

TWSE_ROW = {
    "出表日期": "1150909", "公司代號": "2330", "公司名稱": "台積電", "決議（擬議）進度": "股東會確認",
    "股利年度": "115", "股利所屬年(季)度": "第1季", "股利所屬期間": "1150101~1150331", "期別": "1",
    "董事會（擬議）股利分派日": "1150512", "股東會日期": "1150603",
    "股東配發-盈餘分配之現金股利(元/股)": "6.00000000", "股東配發-法定盈餘公積發放之現金(元/股)": "0.0",
    "股東配發-資本公積發放之現金(元/股)": "0.0", "股東配發-股東配發之現金(股利)總金額(元)": "155585000000",
    "股東配發-盈餘轉增資配股(元/股)": "0.0", "股東配發-法定盈餘公積轉增資配股(元/股)": "0.0",
    "股東配發-資本公積轉增資配股(元/股)": "0.0", "股東配發-股東配股總股數(股)": "0",
    "摘錄公司章程-股利分派部分": "…", "備註": "",
}


def _row(**kw) -> dict:
    return {**TWSE_ROW, **kw}


@pytest.fixture
def fake_twse(monkeypatch):
    rows = [
        _row(),
        _row(**{"股利所屬年(季)度": "第2季", "股利所屬期間": "1150401~1150630",
                "股東配發-盈餘分配之現金股利(元/股)": "6.50000000"}),
        _row(**{"公司代號": "1101", "公司名稱": "台泥", "股利年度": "114", "股利所屬年(季)度": "年度",
                "股東配發-盈餘分配之現金股利(元/股)": "0.0",
                "股東配發-資本公積發放之現金(元/股)": "0.80000000",
                "股東配發-盈餘轉增資配股(元/股)": "0.20000000"}),
        _row(**{"公司代號": "1101B", "公司名稱": "台泥乙特"}),          # 特別股不進表
    ]
    monkeypatch.setattr(twse, "_fetch", lambda key: rows)
    monkeypatch.setattr(twse, "_dividend_cache", None)
    yield rows
    monkeypatch.setattr(twse, "_dividend_cache", None)


def test_dividend_annual_sums_quarters(fake_twse):
    df = twse.dividend()
    tsmc = df[df["code"] == "2330"].iloc[0]
    assert tsmc["year"] == 2026 and tsmc["cash_dividend"] == pytest.approx(12.5) and tsmc["periods"] == 2
    tcc = df[df["code"] == "1101"].iloc[0]
    assert tcc["year"] == 2025 and tcc["cash_dividend"] == pytest.approx(0.8)
    assert tcc["stock_dividend"] == pytest.approx(0.2)
    assert "1101B" not in set(df["code"])


def test_dividend_events_match_finmind_period_format(fake_twse):
    ev = twse.dividend_events()
    assert list(ev.columns) == ["code", "period", "kind", "amount", "announce_date",
                                "ex_date", "payment_date", "fiscal_year"]
    periods = set(ev[ev["code"] == "2330"]["period"])
    assert periods == {"115年第1季", "115年第2季"}          # 與 FinMind TaiwanStockDividend.year 同格式
    tcc = ev[ev["code"] == "1101"].set_index("kind")
    assert tcc.index.tolist() == ["cash", "stock"] and tcc.loc["cash", "period"] == "114年"
    assert tcc.loc["cash", "announce_date"] == "2026-05-12"
    assert int(tcc.loc["cash", "fiscal_year"]) == 2025 and tcc.loc["cash", "ex_date"] is None


def test_dividend_old_field_names_still_work(monkeypatch):
    rows = [{"公司代號": "2412", "股利所屬年度": "113", "現金股利": "4.5", "股票股利": "0", "除息交易日": "1140715"}]
    monkeypatch.setattr(twse, "_fetch", lambda key: rows)
    monkeypatch.setattr(twse, "_dividend_cache", None)
    df = twse.dividend()
    assert df.iloc[0]["year"] == 2024 and df.iloc[0]["cash_dividend"] == pytest.approx(4.5)
    assert df.iloc[0]["ex_date"] == "2025-07-15"
    monkeypatch.setattr(twse, "_dividend_cache", None)


TDCC_CSV = ("﻿資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
            "20260904,2330,1,1200000,500000000,1.93\n"
            "20260904,2330,15,1500,20000000000,77.10\n"
            "20260904,2330,17,1300000,25930000000,100.00\n")


def test_tdcc_parses_bom_csv(monkeypatch):
    monkeypatch.setattr(tdcc.http, "get", lambda url, **kw: TDCC_CSV)
    df = tdcc.shareholding_weekly()
    assert len(df) == 3 and set(df["date"]) == {"2026-09-04"}
    big = df[df["level"] == 15].iloc[0]
    assert big["holders"] == 1500 and big["pct"] == pytest.approx(77.10)
    assert big["level_label"] == "1,000,001以上"


def test_tdcc_html_or_garbage_returns_empty(monkeypatch):
    monkeypatch.setattr(tdcc.http, "get", lambda url, **kw: "<html><body>maintenance</body></html>")
    assert tdcc.shareholding_weekly().empty
    monkeypatch.setattr(tdcc.http, "get", lambda url, **kw: "a,b,c\n1,2,3\n")
    assert tdcc.shareholding_weekly().empty


def test_only_new_keys_keeps_finmind_rows(monkeypatch):
    from pipeline import run_daily
    old = pd.DataFrame([{"code": "2330", "period": "115年第1季", "kind": "cash", "amount": 6.0,
                         "announce_date": "2026-05-12", "ex_date": "2026-09-16",
                         "payment_date": "2026-10-08", "fiscal_year": 2026}])
    monkeypatch.setattr(run_daily.store, "read", lambda table: old)
    new = pd.DataFrame([
        {"code": "2330", "period": "115年第1季", "kind": "cash", "amount": 6.0},   # 已有 → 不覆蓋
        {"code": "2330", "period": "115年第2季", "kind": "cash", "amount": 6.5},   # 新的
    ])
    kept = run_daily.only_new_keys("dividend_events", new)
    assert kept["period"].tolist() == ["115年第2季"]
    assert run_daily.only_new_keys("dividend_events", pd.DataFrame()).empty
