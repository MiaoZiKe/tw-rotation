"""週末的 phase=news：只更新新聞與國際盤，不去碰價量。

Andy 2026-09-14：「週六日有新增也必須更新上去」。
價量週末不會變（打了只會拿到週五的，而且會被 empty 記成「沒回資料」），
會變的是新聞、國際盤（美股週五夜盤、歐股）與總經。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import run_daily


@pytest.fixture(autouse=True)
def _clean():
    run_daily.RESULT.clear()
    run_daily.RESULT.update({"steps": {}, "errors": [], "empty": []})
    yield


def _run(monkeypatch, phase, tmp_path):
    """把所有來源換成記名字的假函式，跑一次 main()，回傳被呼叫過的來源名單。"""
    called: list[str] = []

    def rec(name, ret=None):
        def fn(*a, **k):
            called.append(name)
            return pd.DataFrame() if ret is None else ret
        return fn

    # 價量要回真的有日期的一列，否則 trade_date 是 None，融資券與法人會被 `if trade_date:` 擋掉
    px = pd.DataFrame([{"date": "2026-09-14", "code": "2330", "market": "TWSE", "close": 2380.0}])

    for mod, attrs in {
        "twse": ["valuation_daily", "index_daily", "market_daily",
                 "company_info", "margin_daily", "revenue_monthly", "financial_q",
                 "dividend", "dividend_events"],
        "tpex": ["price_daily"],
        "tdcc": ["shareholding_weekly"],
        "news": ["collect", "extract_broker_views"],
        "macro": ["intl_daily", "macro_all"],
        "finmind": ["stock_info"],
        "mis": ["price_snapshot"],
    }.items():
        target = getattr(run_daily, mod)
        for a in attrs:
            monkeypatch.setattr(target, a, rec(f"{mod}.{a}"), raising=False)
    # latest_date 回的是字串不是 DataFrame，不能用同一個假函式
    monkeypatch.setattr(run_daily.mis, "latest_date", rec("mis.latest_date", "2026-09-14"))
    monkeypatch.setattr(run_daily.store, "latest_date", lambda t: "2026-09-14")
    monkeypatch.setattr(run_daily, "universe_pairs", lambda: [("2330", "TWSE")])
    monkeypatch.setattr(run_daily, "universe", lambda n: ["2330"])

    monkeypatch.setattr(run_daily.twse, "price_daily", rec("twse.price_daily", px))
    monkeypatch.setattr(run_daily, "save", lambda *a, **k: 0)
    monkeypatch.setattr(run_daily, "fetch_institutional", rec("finmind.institutional"))
    monkeypatch.setattr(run_daily, "refresh_financials", rec("finmind.financial_refresh"))
    monkeypatch.setattr(run_daily.config, "STATE", tmp_path)
    monkeypatch.setattr(run_daily.store, "table_summary", lambda: pd.DataFrame())
    monkeypatch.setattr(run_daily.loader, "health", lambda: {})
    import pipeline.build_payload as bp
    monkeypatch.setattr(bp, "build", lambda: None)
    monkeypatch.setattr("sys.argv", ["run_daily", "--phase", phase])
    run_daily.main()
    return called


def test_news模式不碰價量(monkeypatch, tmp_path):
    called = _run(monkeypatch, "news", tmp_path)
    for name in ("twse.price_daily", "tpex.price_daily", "mis.price_snapshot",
                 "twse.valuation_daily", "twse.margin_daily"):
        assert name not in called, f"phase=news 不該呼叫 {name}"


def test_news模式有抓新聞與國際盤(monkeypatch, tmp_path):
    called = _run(monkeypatch, "news", tmp_path)
    assert "news.collect" in called
    assert "macro.intl_daily" in called


def test_news模式不動FinMind額度(monkeypatch, tmp_path):
    """週末把額度花在補法人沒有意義，那些資料週末不會變。"""
    called = _run(monkeypatch, "news", tmp_path)
    assert "finmind.institutional" not in called
    assert "finmind.financial_refresh" not in called


def test_price模式抓價量與新聞但不碰傍晚才落地的來源(monkeypatch, tmp_path):
    """15:30 那輪也要抓新聞（2026-09-15 起）：新聞整天都在更新，而且不吃 FinMind 額度。

    法人、融資券、財報那些傍晚才出的仍然不抓 —— 硬抓只會把「還沒出」記成「沒回資料」。
    """
    called = _run(monkeypatch, "price", tmp_path)
    assert "twse.price_daily" in called
    assert "news.collect" in called
    assert "finmind.institutional" not in called
    assert "tdcc.shareholding_weekly" not in called


def test_full模式該抓的都抓(monkeypatch, tmp_path):
    called = _run(monkeypatch, "full", tmp_path)
    for name in ("twse.price_daily", "twse.margin_daily", "tdcc.shareholding_weekly",
                 "news.collect", "macro.intl_daily"):
        assert name in called, f"phase=full 應該要呼叫 {name}"
