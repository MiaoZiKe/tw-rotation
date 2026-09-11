"""歷史回補的額度處理。

真實事故（2026-09-11）：前一個 Actions run 把同一小時的 FinMind 額度吃掉，
下一個 run 的本機計數器從 0 起算，伺服器回 402 被當成「這檔沒資料」，
迴圈把 400 檔全部跑完、什麼都沒抓到就宣告結束。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, run_backfill  # noqa: E402
from pipeline.util import http  # noqa: E402


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """資料湖、進度檔、額度檔全部指到暫存目錄。"""
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir()
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "state" / "finmind_quota.json")
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "state" / "backfill_progress.json")
    run_backfill._cov_cache.clear()
    return tmp_path


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_402_marks_quota_exhausted(sandbox, monkeypatch):
    """伺服器回 402 → 本機額度歸零，後續呼叫不再打 API。"""
    calls = []

    class _S:
        def get(self, url, **kw):
            calls.append(url)
            return _Resp(402, {"msg": "Requests exceed the limit. Please try again later", "status": 402})

    monkeypatch.setattr(http, "session", lambda: _S())
    assert http.finmind_budget_left() > 1
    assert http.finmind_get("TaiwanStockMonthRevenue", data_id="2330", start_date="2016-01-01") is None
    assert http.finmind_budget_left() == 0
    # 第二次呼叫直接被本機計數器擋下，不會再打到伺服器
    assert http.finmind_get("TaiwanStockMonthRevenue", data_id="2454", start_date="2016-01-01") is None
    assert len(calls) == 1


def test_backfill_stops_on_rate_limit_and_does_not_mark_done(sandbox, monkeypatch):
    codes = ["2330", "2454", "2317", "2308"]
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: codes)

    served = []

    def fake_revenue(code, start, wait=False):
        served.append(code)
        if len(served) <= 2:
            return pd.DataFrame({"ym": ["2016-01"], "code": [code], "revenue": [1.0]})
        http.finmind_mark_exhausted()          # 第三檔開始撞到伺服器限流
        return pd.DataFrame()

    monkeypatch.setattr(run_backfill.finmind, "month_revenue", fake_revenue)
    summary = run_backfill.run("revenue", None, "2016-01-01")

    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert summary["exhausted"] is True
    assert prog["done"].get("revenue:2330") and prog["done"].get("revenue:2454")
    assert "revenue:2317" not in prog["done"], "被限流的那檔不能記成做過"
    assert "revenue:2308" not in prog["done"], "限流後要立刻停，不能繼續燒剩下的檔"
    assert prog["complete"]["revenue"]["done"] is False


def test_backfill_marks_complete_and_skips_etf(sandbox, monkeypatch):
    codes = ["2330", "0050", "00878"]
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: codes)
    asked = []

    def fake_fin(code, start, wait=False):
        asked.append(code)
        return pd.DataFrame({"year": [2016], "quarter": [1], "period_end": ["2016-03-31"],
                             "code": [code], "type": ["EPS"], "value": [1.0]})

    monkeypatch.setattr(run_backfill.finmind, "financial_statements", fake_fin)
    summary = run_backfill.run("financial", None, "2016-01-01")

    assert asked == ["2330"], "ETF 沒有財報，不該去問 FinMind"
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["financial:0050"] and prog["done"]["financial:00878"]
    assert prog["complete"]["financial"]["done"] is True
    assert summary["exhausted"] is False

    # 再跑一次：全部跳過、旗標維持 done
    asked.clear()
    run_backfill._cov_cache.clear()
    summary2 = run_backfill.run("financial", None, "2016-01-01")
    assert asked == []
    assert summary2["skipped"] == 3


def test_no_data_is_marked_done_when_budget_remains(sandbox, monkeypatch):
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["9999"])
    monkeypatch.setattr(run_backfill.finmind, "balance_sheet", lambda c, s, wait=False: pd.DataFrame())
    summary = run_backfill.run("balance", None, "2016-01-01")
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert summary["no_data"] == 1
    assert prog["done"]["balance:9999"] is True


# ------------------------------------------------------------------ v3：done_key 帶起始日、新資料集、回補計畫

def _revenue_df(code):
    return pd.DataFrame({"ym": ["2016-01"], "code": [code], "revenue": [1.0]})


def test_done_key_keeps_legacy_format_for_default_start(sandbox, monkeypatch):
    """既有進度檔的 "price:2330" 在 start == BACKFILL_START 時仍算做過；
    其他起始日的鍵帶日期，不會跟舊鍵混在一起。"""
    monkeypatch.setattr(config, "BACKFILL_START", "2016-01-01")
    assert run_backfill.done_key_of("price", "2330", "2016-01-01") == "price:2330"
    assert run_backfill.done_key_of("price", "2330", "2000-01-01") == "price@2000-01-01:2330"
    assert run_backfill.done_key_of("dividend", "2330", "2026-01-01", tag="m2026-09") == "dividend@m2026-09:2330"
    assert run_backfill.datasets_key_of("revenue+financial+balance", "2016-01-01") == "balance+financial+revenue"
    assert run_backfill.datasets_key_of("price", "2000-01-01") == "price@2000-01-01"
    assert run_backfill.datasets_key_of("dividend+divresult", "2026-01-01", "m2026-09") == "dividend+divresult@m2026-09"

    # 舊格式的 done 鍵 → 預設起始日跳過、不打 API
    run_backfill.PROGRESS.write_text(json.dumps({"done": {"revenue:2330": True}}))
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["2330"])
    asked = []

    def fake_revenue(code, start, wait=False):
        asked.append((code, start))
        return _revenue_df(code)

    monkeypatch.setattr(run_backfill.finmind, "month_revenue", fake_revenue)
    s1 = run_backfill.run("revenue", None, "2016-01-01")
    assert asked == [] and s1["skipped"] == 1

    # 換一個起始日 → 舊鍵不算數，會重抓，並寫成帶日期的新鍵；complete 的鍵也帶日期
    run_backfill._cov_cache.clear()
    s2 = run_backfill.run("revenue", None, "2010-01-01")
    assert asked == [("2330", "2010-01-01")]
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["revenue@2010-01-01:2330"] is True
    assert prog["done"]["revenue:2330"] is True, "舊鍵要保留"
    assert prog["complete"]["revenue@2010-01-01"]["done"] is True
    assert s2["revenue"] == 1


def test_new_datasets_wired_and_etf_rules(sandbox, monkeypatch):
    """dividend / divresult 對 ETF 跳過；margin / holding 對 ETF 要抓。"""
    monkeypatch.setattr(config, "BACKFILL_START", "2016-01-01")
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["2330", "0050"])
    asked = {"dividend": [], "divresult": [], "margin": [], "holding": []}

    def mk(key, table_df):
        def fetch(code, start, wait=False):
            asked[key].append(code)
            return table_df(code)
        return fetch

    monkeypatch.setattr(run_backfill.finmind, "dividend_events", mk("dividend", lambda c: pd.DataFrame(
        {"code": [c], "period": ["114年"], "kind": ["cash"], "amount": [1.0], "fiscal_year": [2025],
         "announce_date": ["2026-03-01"], "ex_date": [None], "payment_date": [None]})))
    monkeypatch.setattr(run_backfill.finmind, "dividend_results", mk("divresult", lambda c: pd.DataFrame(
        {"date": ["2026-06-11"], "code": [c], "kind": ["息"], "dividend": [6.0],
         "before_price": [2255.0], "reference_price": [2249.0], "open_price": [2250.0]})))
    monkeypatch.setattr(run_backfill.finmind, "margin_history", mk("margin", lambda c: pd.DataFrame(
        {"date": ["2021-01-04"], "code": [c], "margin_balance": [1.0], "margin_change": [0.0],
         "short_balance": [0.0], "short_change": [0.0], "margin_buy": [0.0], "margin_sell": [0.0],
         "short_sell": [0.0], "short_cover": [0.0], "offset": [0.0]})))
    monkeypatch.setattr(run_backfill.finmind, "holding_history", mk("holding", lambda c: pd.DataFrame(
        {"date": ["2021-01-08"], "code": [c], "level": [15], "level_label": ["1,000,001以上"],
         "holders": [5], "shares": [9000.0], "pct": [60.0]})))

    s1 = run_backfill.run("dividend+divresult", None, "2016-01-01")
    assert asked["dividend"] == ["2330"] and asked["divresult"] == ["2330"], "ETF 不抓股利"
    assert s1["dividend"] == 1 and s1["divresult"] == 1
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["dividend:0050"] and prog["done"]["divresult:0050"]
    assert prog["complete"]["dividend+divresult"]["done"] is True

    s2 = run_backfill.run("margin+holding", None, "2021-01-01")
    assert asked["margin"] == ["2330", "0050"] and asked["holding"] == ["2330", "0050"], "ETF 有融資券與股權分散"
    assert s2["margin"] == 2 and s2["holding"] == 2
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["margin@2021-01-01:0050"] and prog["done"]["holding@2021-01-01:2330"]
    assert prog["complete"]["holding+margin@2021-01-01"]["done"] is True

    # 真的寫進了既有的表
    from pipeline.util import store
    assert set(store.read("margin_daily")["code"]) == {"2330", "0050"}
    assert set(store.read("shareholding_weekly")["code"]) == {"2330", "0050"}
    assert store.read("dividend_events").iloc[0]["kind"] == "cash"
    assert store.read("dividend_results").iloc[0]["date"] == "2026-06-11"


@pytest.fixture()
def two_step_plan(monkeypatch):
    """兩步驟計畫（+ 自動附加的月更新步驟）；scope 各一種。"""
    monkeypatch.setattr(config, "BACKFILL_START", "2016-01-01")
    steps = [
        {"datasets": "revenue", "start": "2016-01-01", "scope": "universe"},
        {"datasets": "price", "start": "2000-01-01", "scope": "groups"},
    ]
    monkeypatch.setattr(run_backfill, "PLANS", {"default": steps})
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["2330", "2454"])
    monkeypatch.setattr(run_backfill.loader, "membership",
                        lambda cfg=None: pd.DataFrame({"code": ["2330", "2330", "3034"], "group_id": ["a", "b", "a"]}))
    return steps


def test_plan_stops_when_a_step_is_exhausted(sandbox, monkeypatch, two_step_plan):
    served = {"revenue": [], "price": [], "dividend": [], "divresult": []}

    def fake_revenue(code, start, wait=False):
        served["revenue"].append(code)
        if len(served["revenue"]) == 1:
            return _revenue_df(code)
        http.finmind_mark_exhausted()          # 第二檔撞到限流
        return pd.DataFrame()

    def never(key):
        def fetch(code, start, wait=False):
            served[key].append(code)
            return pd.DataFrame()
        return fetch

    monkeypatch.setattr(run_backfill.finmind, "month_revenue", fake_revenue)
    monkeypatch.setattr(run_backfill.finmind, "price_history", never("price"))
    monkeypatch.setattr(run_backfill.finmind, "dividend_events", never("dividend"))
    monkeypatch.setattr(run_backfill.finmind, "dividend_results", never("divresult"))

    result = run_backfill.run_plan("default", None, today=date(2026, 9, 11))

    assert result["exhausted"] is True and result["done"] is False
    assert result["stopped_at"] == "revenue"
    assert served["price"] == [] and served["dividend"] == [], "第一步額度用盡，後面的步驟不能跑"
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["complete"]["revenue"]["done"] is False
    assert "price@2000-01-01" not in prog["complete"]
    plan = prog["complete"]["plan:default"]
    assert plan["done"] is False and plan["month"] == "2026-09"
    assert plan["steps"] == {"revenue": False}
    assert run_backfill.plan_is_done(prog, today=date(2026, 9, 11)) is False


def test_plan_marks_done_when_every_step_completes(sandbox, monkeypatch, two_step_plan):
    served = {"revenue": [], "price": [], "dividend": [], "divresult": []}

    def rec(key, df_of):
        def fetch(code, start, wait=False):
            served[key].append((code, start))
            return df_of(code)
        return fetch

    monkeypatch.setattr(run_backfill.finmind, "month_revenue", rec("revenue", _revenue_df))
    monkeypatch.setattr(run_backfill.finmind, "price_history", rec("price", lambda c: pd.DataFrame(
        {"date": ["2000-01-04"], "code": [c], "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
         "change": [0.0], "volume": [1.0], "turnover": [1.0], "transactions": [1.0], "market": ["FINMIND"]})))
    monkeypatch.setattr(run_backfill.finmind, "dividend_events", rec("dividend", lambda c: pd.DataFrame(
        {"code": [c], "period": ["114年"], "kind": ["cash"], "amount": [1.0], "fiscal_year": [2025],
         "announce_date": ["2026-03-01"], "ex_date": [None], "payment_date": [None]})))
    monkeypatch.setattr(run_backfill.finmind, "dividend_results", rec("divresult", lambda c: pd.DataFrame()))

    result = run_backfill.run_plan("default", None, today=date(2026, 9, 11))

    assert result["done"] is True and result["exhausted"] is False
    # universe 步驟用 target_codes、groups 步驟只跑成分股（去重）、月更新步驟只跑成分股且起始為今年 1/1
    assert served["revenue"] == [("2330", "2016-01-01"), ("2454", "2016-01-01")]
    assert served["price"] == [("2330", "2000-01-01"), ("3034", "2000-01-01")]
    assert served["dividend"] == [("2330", "2026-01-01"), ("3034", "2026-01-01")]

    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["revenue:2330"] is True, "預設起始日維持舊鍵格式"
    assert prog["done"]["price@2000-01-01:3034"] is True
    assert prog["done"]["dividend@m2026-09:2330"] is True, "月更新步驟的鍵帶年月"
    assert prog["done"]["divresult@m2026-09:3034"] is True
    plan = prog["complete"]["plan:default"]
    assert plan["done"] is True and plan["month"] == "2026-09" and plan["stopped_at"] is None
    assert plan["steps"] == {"revenue": True, "price@2000-01-01": True,
                             "dividend+divresult@m2026-09": True}
    assert prog["complete"]["dividend+divresult@m2026-09"]["done"] is True
    assert run_backfill.plan_is_done(prog, today=date(2026, 9, 30)) is True
    assert run_backfill.plan_is_done(prog, today=date(2026, 10, 1)) is False, "跨月後計畫要變成未完成"

    # 再跑一次同一個月：全部命中 done_key，一次 API 都不打
    for k in served:
        served[k].clear()
    run_backfill._cov_cache.clear()
    again = run_backfill.run_plan("default", None, today=date(2026, 9, 12))
    assert again["done"] is True and all(v == [] for v in served.values())

    # 下個月：只有月更新步驟會重抓（dividend_events 沒有時間欄位，靠 respect_time=False 才不會被誤判成已補過）
    run_backfill._cov_cache.clear()
    nxt = run_backfill.run_plan("default", None, today=date(2026, 10, 5))
    assert nxt["done"] is True
    assert served["revenue"] == [] and served["price"] == []
    assert served["dividend"] == [("2330", "2026-01-01"), ("3034", "2026-01-01")]
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["done"]["dividend@m2026-10:2330"] is True
    assert prog["complete"]["plan:default"]["month"] == "2026-10"


def test_already_covered_respect_time_false_ignores_data(sandbox, monkeypatch):
    from pipeline.util import store
    store.append("dividend_events", pd.DataFrame(
        {"code": ["2330"], "period": ["114年"], "kind": ["cash"], "amount": [1.0]}))
    run_backfill._cov_cache.clear()
    assert run_backfill.already_covered("dividend_events", "2330", "2026-01-01") is True, "沒有時間欄位 → 有資料就算補過"
    assert run_backfill.already_covered("dividend_events", "2330", "2026-01-01", respect_time=False) is False


def test_monthly_step_and_unknown_plan():
    step = run_backfill.monthly_step(date(2026, 2, 3))
    assert step == {"datasets": "dividend+divresult", "start": "2026-01-01",
                    "scope": "groups", "tag": "m2026-02"}
    assert run_backfill.plan_steps("default", date(2026, 2, 3))[-1] == step
    assert len(run_backfill.plan_steps("default")) == len(run_backfill.PLAN_DEFAULT) + 1
    with pytest.raises(KeyError):
        run_backfill.plan_steps("nope")
