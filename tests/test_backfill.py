"""歷史回補的額度處理。

真實事故（2026-09-11）：前一個 Actions run 把同一小時的 FinMind 額度吃掉，
下一個 run 的本機計數器從 0 起算，伺服器回 402 被當成「這檔沒資料」，
迴圈把 400 檔全部跑完、什麼都沒抓到就宣告結束。
"""
from __future__ import annotations

import json
import sys
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
