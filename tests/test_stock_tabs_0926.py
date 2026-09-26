"""個股頁下方分頁 2026-09-26（Andy）：除權息年度圖、籌碼共用日期軸、股利公告回補被跳過。

口徑見 DECISIONS #266 與 pipeline/compute/stockpage.py 的 div_year_bars docstring。
每一條都附邊界：空資料、只有公告沒有結果、含權對不到公告、上市前／回補起點前的年份。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, run_backfill  # noqa: E402
from pipeline.compute import stockpage as S  # noqa: E402
from pipeline.util import http, store  # noqa: E402


def _ev(rows):
    cols = ["code", "period", "kind", "amount", "announce_date", "ex_date", "payment_date", "fiscal_year"]
    df = pd.DataFrame(rows, columns=cols)
    df["fiscal_year"] = df["fiscal_year"].astype("Int64")
    return df


def _rs(rows):
    return pd.DataFrame(rows, columns=["date", "code", "kind", "dividend", "before_price",
                                       "reference_price", "open_price"])


def _px(code, first="2010-01-04", last="2026-09-24"):
    return pd.DataFrame({"code": [code, code], "date": [first, last], "close": [100.0, 100.0]})


# ------------------------------------------------------------------ 年度股利長條

def test_year_bars_every_year_labelled_zero_when_no_dividend():
    """3026 的真實情形：每年一次除息、2016 起 —— 公告只有最近一筆。年度圖要每年一根，年份連續。
    中間故意拿掉 2021：那一年要有一根 0（x 軸照樣標年份），不能被跳過。"""
    rs = _rs([[f"{y}-07-15", "3026", "息", 5.0, 100.0, 95.0, 95.0] for y in range(2016, 2027) if y != 2021])
    ev = _ev([["3026", "114年", "cash", 5.8, "2026-05-28", "2026-07-15", "2026-08-10", 2025]])
    d = S.dividends(ev, rs, _px("3026"), "3026", 800.0, asof="2026-09-24")
    years = [b["year"] for b in d["by_year"]]
    assert years == list(range(2016, 2027)), "每年一根、連續、從回補起點 2016 到今年"
    y21 = next(b for b in d["by_year"] if b["year"] == 2021)
    assert y21["cash"] == 0 and y21["stock"] == 0 and y21["n"] == 0 and y21["items"] == []
    y26 = next(b for b in d["by_year"] if b["year"] == 2026)
    assert y26["cash"] == pytest.approx(5.8), "有公告的那一次用公告金額（不是價差）"
    assert y26["partial"] is True and d["by_year"][0]["partial"] is False
    # 紀錄表的年份 ＝ 年度圖裡 n>0 的年份（驗收：3026 年度數與紀錄表年份一致）
    rec_years = sorted({int(r["date"][:4]) for r in d["results"]})
    assert rec_years == sorted(b["year"] for b in d["by_year"] if b["n"] > 0)


def test_year_bars_quarterly_summed_and_listed():
    """季配息：同一個西元年多次除息要加總，items 逐次列出（提示框用）。"""
    ev = _ev([
        ["2330", "113年第3季", "cash", 4.5, "2025-03-03", "2025-03-18", "2025-04-10", 2024],
        ["2330", "113年第4季", "cash", 4.5, "2025-05-28", "2025-06-12", "2025-07-10", 2024],
        ["2330", "114年第1季", "cash", 5.0, "2025-09-01", "2025-09-16", "2025-10-09", 2025],
        ["2330", "114年第2季", "cash", 5.0, "2025-11-26", "2025-12-11", "2026-01-08", 2025],
    ])
    rs = _rs([[d, "2330", "息", a, 1000.0, 1000.0 - a, 995.0] for d, a in
              [("2025-03-18", 4.5), ("2025-06-12", 4.5), ("2025-09-16", 5.0), ("2025-12-11", 5.0)]])
    d = S.dividends(ev, rs, _px("2330"), "2330", 1000.0, asof="2026-09-24")
    y25 = next(b for b in d["by_year"] if b["year"] == 2025)
    assert y25["cash"] == pytest.approx(19.0) and y25["n"] == 4
    assert [i["date"] for i in y25["items"]] == ["2025-03-18", "2025-06-12", "2025-09-16", "2025-12-11"]
    assert y25["items"][0]["period"] == "113年第3季", "提示框要寫得出是哪一季的股利"
    assert next(b for b in d["by_year"] if b["year"] == 2026)["n"] == 0


def test_year_bars_cash_and_stock_split_and_unknown_when_no_announcement():
    """現金、股票分開；含權又對不到公告 → 金額留空不猜（unknown），不是寫成 0 也不是寫價差。"""
    ev = _ev([
        ["6669", "114年", "cash", 144.39, "2026-04-01", "2026-06-22", "2026-07-15", 2025],
        ["6669", "114年", "stock", 19.83, "2026-04-01", "2026-09-02", None, 2025],
    ])
    rs = _rs([
        ["2026-06-22", "6669", "息", 144.39, 3000.0, 2855.6, 2860.0],
        ["2026-09-02", "6669", "權", 1000.0, 2900.0, 1900.0, 1900.0],
        ["2023-07-20", "6669", "權息", 9.8, 106.5, 96.66, 96.7],          # 對不到公告
    ])
    d = S.dividends(ev, rs, _px("6669", first="2017-11-01"), "6669", 1000.0, asof="2026-09-24")
    y26 = next(b for b in d["by_year"] if b["year"] == 2026)
    assert y26["cash"] == pytest.approx(144.39) and y26["stock"] == pytest.approx(19.83) and y26["unknown"] == 0
    y23 = next(b for b in d["by_year"] if b["year"] == 2023)
    assert y23["n"] == 1 and y23["unknown"] == 1 and y23["cash"] == 0 and y23["stock"] == 0
    assert y23["items"][0]["cash"] is None and y23["items"][0]["stock"] is None
    # 上市前的年份不畫（2017 才有價量 → 從 2017 起，不從 2016）
    assert d["by_year"][0]["year"] == 2017


def test_year_bars_range_bounds():
    """年份範圍：至少近 10 年；不早於回補起點 2016；不早於價量第一年；end＝asof 年。"""
    rs = _rs([["2026-07-01", "9999", "息", 1.0, 10.0, 9.0, 9.0]])
    d = S.dividends(None, rs, _px("9999", first="2000-01-04"), "9999", 10.0, asof="2026-09-24")
    assert [b["year"] for b in d["by_year"]][0] == 2017, "近 10 年：2017～2026"
    assert d["by_year"][-1]["year"] == 2026 and len(d["by_year"]) == 10
    d2 = S.dividends(None, rs, _px("9999", first="2024-03-01"), "9999", 10.0, asof="2026-09-24")
    assert [b["year"] for b in d2["by_year"]] == [2024, 2025, 2026], "上市前不是「沒配」，不畫"
    # 年底那天不算 partial
    d3 = S.dividends(None, rs, None, "9999", 10.0, asof="2026-12-31")
    assert d3["by_year"][-1]["partial"] is False


def test_upcoming_not_in_bars_and_announcement_without_result_fills_in():
    """除權息日在 asof 之後／還沒訂的公告 → upcoming，不進長條；
    公告的除權息日已過、結果表卻還沒進湖 → 用公告補上那一次。"""
    ev = _ev([
        ["2330", "115年第1季", "cash", 7.0, "2026-09-01", "2026-09-16", "2026-10-08", 2026],
        ["2330", "115年第2季", "cash", 7.0, "2026-08-11", None, None, 2026],
        ["2330", "115年第3季", "cash", 7.5, "2026-09-20", "2026-12-17", None, 2026],
    ])
    d = S.dividends(ev, None, None, "2330", 1000.0, asof="2026-09-24")
    y26 = next(b for b in d["by_year"] if b["year"] == 2026)
    assert y26["n"] == 1 and y26["cash"] == pytest.approx(7.0), "9/16 那次沒有結果列也要算進去"
    assert [u["period"] for u in d["upcoming"]] == ["115年第3季", "115年第2季"], "有日期的在前、沒日期的在後"
    assert d["upcoming"][1]["ex_date"] is None


def test_dividends_empty_inputs_and_other_codes():
    """空資料、別檔的資料 → 全部空，不丟例外。"""
    assert S.dividends(None, None, None, "2330", None)["by_year"] == []
    e = _ev([["1101", "114年", "cash", 1.0, "2026-05-01", "2026-07-01", None, 2025]])
    out = S.dividends(e, _rs([]), None, "2330", 100.0, asof="2026-09-24")
    assert out["by_year"] == [] and out["events"] == [] and out["coverage"] == {}
    assert S.div_year_bars(pd.DataFrame(), pd.DataFrame(), None, "2330", None) == ([], [])


def test_results_and_events_not_truncated_and_coverage():
    """季配息十年：紀錄表不再只給 12 筆（以前只看得到 3 年）；coverage 寫明兩張表各自的起點與筆數。"""
    dates = [f"{y}-{m:02d}-15" for y in range(2016, 2027) for m in (3, 6, 9, 12) if f"{y}-{m:02d}-15" <= "2026-09-24"]
    rs = _rs([[d, "2330", "息", 2.5, 500.0, 497.5, 497.5] for d in dates])
    ev = _ev([["2330", "114年第4季", "cash", 6.0, "2026-05-27", "2026-06-15", "2026-07-09", 2025]])
    d = S.dividends(ev, rs, None, "2330", 1000.0, asof="2026-09-24")
    assert len(d["results"]) == len(dates) == 43
    assert d["coverage"] == {"events_n": 1, "events_first": "2026-05-27", "events_years": 1,
                             "results_n": 43, "results_first": "2016-03-15", "cover_from": 2016}


def test_existing_yield_contract_unchanged():
    """殖利率與紀錄表欄位的既有口徑（#261）不因這批改動而變。"""
    ev = _ev([["6669", "114年", "cash", 144.39, "2026-04-01", "2026-06-22", "2026-07-15", 2025]])
    out = S.dividends(ev, None, None, "6669", 1000.0)
    assert out["cash_ttm"] == pytest.approx(144.39) and out["yield_ttm"] == pytest.approx(14.44)


# ------------------------------------------------------------------ 籌碼共用日期軸

def test_chip_series_cover_one_year_of_trading_days():
    """「1 年」視窗要畫得滿：法人與融資券都給 CHIP_DAYS（≥ 245 個交易日）。"""
    assert S.CHIP_DAYS >= 245
    days = pd.bdate_range("2025-01-01", periods=400).strftime("%Y-%m-%d")
    inst = pd.DataFrame({"code": "2330", "date": days, "foreign_total": 1000.0, "trust": 0.0, "dealer": 0.0})
    mg = pd.DataFrame({"code": "2330", "date": days, "margin_balance": 1.0, "short_balance": 0.0})
    iv = S.inst_series(inst, "2330")
    assert len(iv["daily"]) == S.CHIP_DAYS and iv["daily"][-1][0] == days[-1]
    assert iv["sum20"] == pytest.approx(20000.0), "20 日合計不受視窗長度影響"
    assert len(S.margin_series(mg, "2330")) == S.CHIP_DAYS
    # 資料不夠一年就給全部，不補假資料
    assert len(S.inst_series(inst.head(30), "2330")["daily"]) == 30
    assert S.inst_series(pd.DataFrame(), "2330")["daily"] == []
    assert S.margin_series(None, "2330") == []


# ------------------------------------------------------------------ 股利公告回補不再被跳過

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


def test_daily_announcement_does_not_block_dividend_history_backfill(sandbox, monkeypatch):
    """真實事故（3026 禾伸堂）：每日管線先寫進一筆今年的公告，回補就把 2016 起的歷史整個跳過。
    修正後：公告日最早只到今年 → 算「還沒補到 2016」→ 照樣去抓。"""
    monkeypatch.setattr(config, "BACKFILL_START", "2016-01-01")
    store.append("dividend_events", _ev([["3026", "114年", "cash", 5.8, "2026-05-28", "2026-06-22", "2026-07-17", 2025]]))
    run_backfill._cov_cache.clear()
    assert run_backfill.already_covered("dividend_events", "3026", "2016-01-01") is False
    # 已經補到 2016 的照樣算補過（不白燒額度）
    store.append("dividend_events", _ev([["2330", "104年", "cash", 6.0, "2016-01-01", "2016-06-27", None, 2015]]))
    run_backfill._cov_cache.clear()
    assert run_backfill.already_covered("dividend_events", "2330", "2016-01-01") is True
    # 公告日全空 → 不知道補到哪 → 當作沒補（寧可多問一次）
    store.append("dividend_events", _ev([["1101", "114年", "cash", 1.0, None, None, None, 2025]]))
    run_backfill._cov_cache.clear()
    assert run_backfill.already_covered("dividend_events", "1101", "2016-01-01") is False

    asked = []

    def fetch(code, start, wait=False):
        asked.append(code)
        return _ev([[code, "105年", "cash", 2.5, "2016-06-01", "2016-08-12", None, 2016]])
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["3026"])
    monkeypatch.setattr(run_backfill.finmind, "dividend_events", fetch)
    run_backfill._cov_cache.clear()
    run_backfill.run("dividend", None, "2016-01-01")
    assert asked == ["3026"]
    got = store.read("dividend_events")
    assert sorted(got[got["code"] == "3026"]["period"]) == ["105年", "114年"], "只增不改：原本那筆還在"
    assert json.loads(run_backfill.PROGRESS.read_text())["done"]["dividend:3026"] is True
