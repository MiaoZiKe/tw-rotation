"""2026-11-06 稽核 A／B：暫定價量要被官方值取代、FinMind 當沖佔位 0 不入湖。

A. 上市個股當天價量收盤當晚是 mis 暫定值（量與值是盤中口徑，偏低 2～20%），
   openapi 隔天上午就有官方值，但清晨與盤中三輪 news 不抓價量 → 暫定值掛到隔天 15:37。
B. FinMind 當沖當天先回 0 的佔位列，進湖後沒人補正（11-05 有 417 檔是 0，2330 顯示 0 張，實際 7,532 張）。
全部用假資料，不打真 API。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config, run_backfill, run_daily
from pipeline.sources import finmind
from pipeline.util import http, store


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir()
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "state" / "finmind_quota.json")
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "state" / "backfill_progress.json")
    run_backfill._cov_cache.clear()
    return tmp_path


def _mis_row(code="2330", turnover=8.2e10, volume=36_437_000, date="2026-11-05"):
    return {"date": date, "code": code, "market": "TWSE", "close": 2240.0, "volume": volume,
            "turnover": turnover, "px_source": "mis"}


def _official_row(code="2330", turnover=1.018e11, volume=45_000_000, date="2026-11-05"):
    return {"date": date, "code": code, "market": "TWSE", "close": 2245.0, "volume": volume,
            "turnover": turnover, "transactions": 99999}


# ------------------------------------------------------------------ A. 暫定值被官方覆蓋

def test_官方值覆蓋mis暫定列並清掉暫定標記(sandbox):
    store.append("price_daily", pd.DataFrame([_mis_row(), _mis_row("2317", 2e10)]))
    store.append("price_daily", pd.DataFrame([_official_row()]))        # 隔天上午 news 輪抓到的官方值
    df = store.read("price_daily")
    r = df[df["code"] == "2330"].iloc[0]
    assert len(df[df["code"] == "2330"]) == 1, "同一天同一檔不能變兩列"
    assert r["turnover"] == pytest.approx(1.018e11) and r["close"] == 2245.0
    assert pd.isna(r["px_source"]), "官方列沒有 px_source，覆蓋後暫定標記要消失"
    assert df[df["code"] == "2317"].iloc[0]["px_source"] == "mis", "官方還沒給的檔仍維持暫定"


def test_market_daily暫定值同樣被官方覆蓋(sandbox):
    store.append("market_daily", pd.DataFrame([{"date": "2026-11-05", "turnover": 9.26e11, "px_source": "mis"}]))
    store.append("market_daily", pd.DataFrame([{"date": "2026-11-05", "turnover": 9.871e11, "volume": 1}]))
    m = store.read("market_daily")
    assert len(m) == 1 and m.iloc[0]["turnover"] == pytest.approx(9.871e11)


def test_mis暫定列不會把湖裡已有的官方列降級(sandbox):
    store.append("price_daily", pd.DataFrame([_official_row(), _official_row("2317")]))
    filled = pd.DataFrame([_mis_row(), _mis_row("2454")])
    out = run_daily.drop_rows_already_official(filled)
    assert out["code"].tolist() == ["2454"], "官方已有的 2330 不可被 mis 暫定值蓋回去"


def test_mis暫定列蓋掉另一筆mis仍可通過(sandbox):
    store.append("price_daily", pd.DataFrame([_mis_row()]))
    out = run_daily.drop_rows_already_official(pd.DataFrame([_mis_row(turnover=9e10)]))
    assert len(out) == 1, "湖裡還是暫定值時，新的暫定值照常更新"


# ------------------------------------------------------------------ B. FinMind 佔位 0

def _dt_resp(rows):
    return [{"date": d, "stock_id": "2330", "BuyAfterSale": "", "Volume": v, "BuyAmount": b, "SellAmount": s}
            for d, v, b, s in rows]


def test_當沖最新日全0的佔位列不入湖(monkeypatch):
    monkeypatch.setattr(finmind, "_price_latest_date", lambda: "2026-11-05")
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: _dt_resp([
        ("2026-11-04", 7_000_000, 1.5e10, 1.4e10),
        ("2026-11-05", 0, 0, 0)]))
    out = finmind.day_trading("2330", "2026-11-01")
    assert out["date"].tolist() == ["2026-11-04"]


def test_當沖有正式數字的最新日保留_舊日期的0保留(monkeypatch):
    monkeypatch.setattr(finmind, "_price_latest_date", lambda: "2026-11-05")
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: _dt_resp([
        ("2026-11-03", 0, 0, 0), ("2026-11-05", 7_532_000, 2e10, 2e10)]))
    out = finmind.day_trading("2330", "2026-11-01")
    assert out["date"].tolist() == ["2026-11-03", "2026-11-05"]


def test_當沖日期晚於價量最新日的列丟掉(monkeypatch):
    monkeypatch.setattr(finmind, "_price_latest_date", lambda: "2026-11-05")
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: _dt_resp([
        ("2026-11-05", 100, 1, 1), ("2026-11-06", 100, 1, 1)]))
    assert finmind.day_trading("2330", "2026-11-01")["date"].tolist() == ["2026-11-05"]


def test_價量最新日讀不到時不過濾(monkeypatch):
    monkeypatch.setattr(finmind, "_price_latest_date", lambda: None)
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: _dt_resp([("2026-11-05", 0, 0, 0)]))
    assert len(finmind.day_trading("2330", "2026-11-01")) == 1


def test_借券不收日期晚於價量最新日的列(monkeypatch):
    monkeypatch.setattr(finmind, "_price_latest_date", lambda: "2026-11-05")
    rows = [{"date": d, "stock_id": "2330", "SBLShortSalesShortSales": 0, "SBLShortSalesReturns": 0,
             "SBLShortSalesAdjustments": 0, "SBLShortSalesCurrentDayBalance": 0, "SBLShortSalesQuota": 5,
             "MarginShortSalesShortSales": 0, "MarginShortSalesCurrentDayBalance": 0}
            for d in ("2026-11-05", "2026-11-06")]
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: rows)
    out = finmind.short_sale_balances("2330", "2026-11-01")
    assert out["date"].tolist() == ["2026-11-05"], "借券餘額 0 是真的，最新日不丟；只丟未來日期"


# ------------------------------------------------------------------ 續補：最近全 0 的列要重抓

def _seed(sandbox):
    dates = ["2026-11-03", "2026-11-04", "2026-11-05"]
    store.append("price_daily", pd.DataFrame([{"date": d, "code": c, "close": 1.0}
                                              for d in dates for c in ("2330", "2317", "1101")]))
    z = lambda d, c, v: {"date": d, "code": c, "daytrade_volume": v, "daytrade_buy_amount": v * 10,  # noqa: E731
                         "daytrade_sell_amount": v * 10}
    store.append("daytrade_daily", pd.DataFrame([
        z("2026-11-03", "2330", 5), z("2026-11-04", "2330", 6), z("2026-11-05", "2330", 0),   # 佔位 0
        z("2026-11-03", "2317", 0),                                                              # 太舊，不重抓
        z("2026-11-04", "2317", 3), z("2026-11-05", "2317", 4),
        z("2026-11-05", "1101", 8)]))


def test_最近兩個交易日全0的當沖列要重抓(sandbox):
    _seed(sandbox)
    codes, start = run_backfill.zero_daytrade_codes(store.read("daytrade_daily"), store.read("price_daily"))
    assert codes == ["2330"] and start == "2026-11-05"


def test_每日續補把全0的當沖排在名單最前面並抓回(sandbox, monkeypatch):
    _seed(sandbox)
    monkeypatch.setattr(run_backfill, "market_codes", lambda: ["2330", "2317", "1101"])
    run_backfill._save_progress({"done": {}, "complete": {}})
    asked = []

    def fake(code, start, **k):
        asked.append((code, start))
        return pd.DataFrame({"date": ["2026-11-05"], "code": [code], "daytrade_volume": [7_532_000.0],
                             "daytrade_buy_amount": [1e10], "daytrade_sell_amount": [1e10]})
    monkeypatch.setattr(run_backfill.finmind, "day_trading", fake)
    monkeypatch.setattr(run_backfill.finmind, "short_sale_balances", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(run_backfill.finmind, "margin_history", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(run_backfill.finmind, "institutional", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 500)
    run_backfill.refresh_stale_inst(run_backfill._progress())
    assert asked and asked[0][0] == "2330", asked
    df = store.read("daytrade_daily")
    r = df[(df["code"] == "2330") & (df["date"] == "2026-11-05")].iloc[0]
    assert r["daytrade_volume"] == 7_532_000.0, "佔位 0 要被正式值覆蓋"


def test_一次性回補只重抓全0的檔(sandbox, monkeypatch):
    _seed(sandbox)
    run_backfill._save_progress({"done": {}, "complete": {}})
    asked = []
    monkeypatch.setattr(run_backfill.finmind, "day_trading", lambda c, s, **k: asked.append(c) or pd.DataFrame())
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 500)
    run_backfill.fix_daytrade_zeros(3)
    assert sorted(asked) == ["2317", "2330"], "3 個交易日內有全 0 列的才重抓（含 11-03 的 2317）"
