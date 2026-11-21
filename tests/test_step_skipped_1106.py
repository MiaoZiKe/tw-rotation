"""2026-11-06 資料維修：「本輪本來就不用抓」不能記成 ok:false（監工每天誤報 8 個步驟）。"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import run_daily
from pipeline.sources import news, optivx, sitca


@pytest.fixture(autouse=True)
def _clean():
    run_daily.RESULT.clear()
    run_daily.RESULT.update({"steps": {}, "errors": [], "empty": []})
    yield


def test_宣告skipped的空結果記成ok不進empty():
    run_daily.step("x", lambda: run_daily.skipped_df("已在湖裡"))
    s = run_daily.RESULT["steps"]["x"]
    assert s["ok"] is True and s["skipped"] == "已在湖裡" and s["rows"] == 0
    assert "x" not in run_daily.RESULT["empty"]


def test_沒宣告的空結果照舊算失敗():
    run_daily.step("y", lambda: pd.DataFrame())
    assert run_daily.RESULT["steps"]["y"]["ok"] is False
    assert "y" in run_daily.RESULT["empty"]


def test_有error的空結果即使宣告skipped也算失敗():
    def f():
        d = run_daily.skipped_df("x")
        d.attrs["error"] = "HTTP 500"
        return d
    run_daily.step("z", f)
    assert run_daily.RESULT["steps"]["z"]["ok"] is False
    assert "z" in run_daily.RESULT["empty"]


def test_有資料的步驟不受影響():
    run_daily.step("w", lambda: pd.DataFrame({"a": [1]}))
    assert run_daily.RESULT["steps"]["w"]["ok"] is True
    assert "skipped" not in run_daily.RESULT["steps"]["w"]


def test_公會前十大已在湖裡是skipped(monkeypatch):
    class R:
        text = "x"
        encoding = None
        apparent_encoding = "utf-8"

    class S:
        def get(self, *a, **k):
            return R()

    monkeypatch.setattr(sitca.http, "session", lambda: S())
    monkeypatch.setattr(sitca, "latest_ym", lambda t: "202609")
    out = sitca.top10({}, have_yms={"202609"})
    assert out.empty and out.attrs.get("skipped")


def test_券商引述_新聞有但沒目標價是skipped_沒新聞不是():
    n = pd.DataFrame([{"news_id": "1", "title": "今天天氣好", "summary": "", "codes": "", "date": "2026-11-06"}])
    out = news.extract_broker_views(n)
    assert out.empty and out.attrs.get("skipped")
    assert not news.extract_broker_views(pd.DataFrame()).attrs.get("skipped")


def test_恐慌指數_FinMind回空列表是skipped_回None是error_有列算不出是error():
    from datetime import date
    d = date(2026, 11, 6)
    a = optivx.daily_update(today=d, fetch=lambda s, e: [], last="2026-11-05")
    assert a.empty and a.attrs.get("skipped") and not a.attrs.get("error")
    b = optivx.daily_update(today=d, fetch=lambda s, e: None, last="2026-11-05")
    assert b.attrs.get("error") and not b.attrs.get("skipped")
    rows = [{"date": "2026-11-06", "option_id": "TXO", "contract_date": "202611", "strike_price": 100,
             "call_put": "call", "settlement_price": 1.0, "trading_session": "position"}]
    c = optivx.daily_update(today=d, fetch=lambda s, e: rows, last="2026-11-05")
    assert c.empty and c.attrs.get("error") and not c.attrs.get("skipped")


def test_60分K已在湖裡是skipped(monkeypatch):
    lake = pd.DataFrame([{"symbol": "FUT", "ts": "2026-11-05 09:00:00"}, {"symbol": "OTC", "ts": "2026-11-05 09:00:00"}])
    monkeypatch.setattr(run_daily.store, "read", lambda *a, **k: lake)
    assert run_daily.collect_futures_60m("2026-11-05").attrs.get("skipped")
    assert run_daily.collect_otc_60m("2026-11-05").attrs.get("skipped")


def test_交叉比對上櫃抓日行情用較多次重試(monkeypatch, tmp_path):
    from pipeline.compute import crosscheck as cc
    seen = {}
    monkeypatch.setattr(cc.twse, "price_daily", lambda: pd.DataFrame())
    monkeypatch.setattr(cc.tpex, "price_daily", lambda retries=None: seen.setdefault("r", retries) and pd.DataFrame())
    monkeypatch.setattr(cc, "_lake_by_market", lambda now: pd.DataFrame())
    cc.run(path=tmp_path / "h.json")
    assert seen["r"] == 6
