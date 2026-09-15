"""資料新鮮度：分階段抓取、空結果要留下紀錄、meta 要把狀態帶給前端。

會有這條測試，是因為 2026-09-11 出現過一個沒人看得見的失敗：
資料湖裡上櫃 982 檔、上市 0 檔，網站就停在前一天，但 last_run.json 的 errors
是空陣列，Actions 的摘要也是綠的 —— 「抓到 0 筆」被當成成功。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 傍晚才落地的來源。台北 15:30 那輪（--phase price）不該碰它們。
EVENING_ONLY = [
    "twse.margin", "twse.company_info", "finmind.stock_info", "twse.revenue",
    "twse.financial", "twse.dividend", "twse.dividend_events",
    "tdcc.shareholding", "macro.intl", "macro.fred",
    "finmind.institutional",
]
# 不管哪一輪都要抓的（這就是「當天資料當天到」的最低限度）。
# news.collect 在 2026-09-15 從 EVENING_ONLY 移過來：新聞整天都在更新、又不吃額度，
# 只在傍晚抓的話事件側欄要等到 18:30 才出現當天的新聞（Andy 回報「事件需要同步更新今天發生的」）。
ALWAYS = ["twse.price_daily", "twse.valuation", "twse.index",
          "twse.market", "tpex.price_daily", "news.collect"]


def _price(date: str = "2026-09-11") -> pd.DataFrame:
    return pd.DataFrame({"date": [date, date], "code": ["2330", "2317"],
                         "open": [1000.0, 200.0], "high": [1010.0, 202.0],
                         "low": [990.0, 198.0], "close": [1005.0, 201.0],
                         "volume": [30000, 12000], "turnover": [3.0e10, 2.4e9]})


@pytest.fixture()
def rd(tmp_path, monkeypatch):
    """把管線的所有外部來源換成假的，資料湖導到暫存目錄。"""
    from pipeline import config
    data = tmp_path / "data"
    (data / "_state").mkdir(parents=True)
    monkeypatch.setattr(config, "DATA", data)
    monkeypatch.setattr(config, "STATE", data / "_state")

    from pipeline.util import store
    monkeypatch.setattr(store, "DATA", data, raising=False)

    from pipeline import build_payload, run_daily
    monkeypatch.setattr(build_payload, "build", lambda: None)
    # 一次性的權證清理不在這條測試的範圍內
    (data / "_state" / "purged_warrants.flag").write_text("test")

    empty = pd.DataFrame()
    monkeypatch.setattr(run_daily.twse, "price_daily", lambda: _price())
    for name in ("valuation_daily", "index_daily", "market_daily", "company_info",
                 "revenue_monthly", "financial_q", "dividend", "dividend_events"):
        monkeypatch.setattr(run_daily.twse, name, lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.twse, "margin_daily", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.tpex, "price_daily", lambda: empty)
    monkeypatch.setattr(run_daily.tdcc, "shareholding_weekly", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.news, "collect", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.news, "extract_broker_views", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.macro, "intl_daily", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.macro, "macro_all", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily.finmind, "stock_info", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily, "fetch_institutional", lambda *a, **k: empty)
    monkeypatch.setattr(run_daily, "refresh_financials", lambda *a, **k: empty)

    run_daily.RESULT.clear()
    run_daily.RESULT.update({"steps": {}, "errors": [], "empty": []})
    return run_daily, data


def _run(run_daily, *argv):
    sys.argv = ["run_daily", *argv]
    rc = run_daily.main()
    return rc, json.loads((run_daily.config.STATE / "last_run.json").read_text())


def test_盤後第一輪只抓價量(rd):
    run_daily, _ = rd
    rc, state = _run(run_daily, "--phase", "price")
    assert rc == 0
    assert state["phase"] == "price"
    for name in ALWAYS:
        assert name in state["steps"], f"{name} 在 price 這輪也該抓"
    for name in EVENING_ONLY:
        assert name not in state["steps"], f"{name} 傍晚才出，price 這輪不該抓"


def test_完整那輪該抓的都抓(rd):
    run_daily, _ = rd
    rc, state = _run(run_daily, "--phase", "full")
    assert rc == 0
    assert state["phase"] == "full"
    for name in ALWAYS + EVENING_ONLY:
        assert name in state["steps"], f"{name} 在 full 這輪應該要跑"


def test_抓到零筆要留下紀錄而不是默默吞掉(rd):
    """這就是 09-11 的病灶：上市 0 筆，但 errors 是空的，網站上完全看不出來。"""
    run_daily, _ = rd
    _, state = _run(run_daily, "--phase", "price")
    # tpex 回空 → 必須出現在 empty 名單裡
    assert "tpex.price_daily" in state["empty"]
    # 有回資料的不該被誤記
    assert "twse.price_daily" not in state["empty"]


def test_狀態檔在產前端資料之前就寫好(rd, monkeypatch):
    """build_payload 讀 last_run.json 來產 meta；晚寫就會拿到上一輪的狀態。"""
    run_daily, data = rd
    seen = {}

    def fake_build():
        seen["state"] = json.loads((data / "_state" / "last_run.json").read_text())

    from pipeline import build_payload
    monkeypatch.setattr(build_payload, "build", fake_build)
    _run(run_daily, "--phase", "price")

    assert seen, "build 沒有被呼叫到"
    assert seen["state"]["trade_date"] == "2026-09-11"
    assert "tpex.price_daily" in seen["state"]["empty"]
    assert seen["state"]["complete"] is False        # 這份是中途快照


def test_meta_把資料落後與失敗來源帶給前端(tmp_path, monkeypatch):
    """price_daily 已經有更新的一天，但前端採用的是前一天 → 要能看出來。"""
    from pipeline import config
    data, site = tmp_path / "data", tmp_path / "site"
    (data / "_state").mkdir(parents=True)
    site.mkdir(parents=True)
    monkeypatch.setattr(config, "DATA", data)
    monkeypatch.setattr(config, "SITE_DATA", site)
    monkeypatch.setattr(config, "STATE", data / "_state")

    (data / "_state" / "last_run.json").write_text(json.dumps({
        "phase": "full", "trade_date": "2026-09-11",
        "finished_at": "2026-09-11T14:35:00+00:00",
        "errors": ["twse.dividend: HTTPError 500"],
        "empty": ["tdcc.shareholding", "macro.fred"],
    }, ensure_ascii=False))

    from pipeline import build_payload
    monkeypatch.setattr(build_payload.store, "table_summary",
                        lambda: pd.DataFrame([{"table": "price_daily", "rows": 10,
                                               "latest": "2026-09-11"}]))
    monkeypatch.setattr(build_payload.loader, "health", lambda: {})

    # 資料湖已經到 09-11，但上市那天 0 檔，所以前端只敢用 09-10
    meta = build_payload.meta_payload("2026-09-10", 250)

    assert meta["price_latest"] == "2026-09-11"
    assert meta["price_ahead_of_payload"] is True
    assert meta["last_run_empty"] == ["tdcc.shareholding", "macro.fred"]
    assert meta["last_run_errors"] == ["twse.dividend: HTTPError 500"]
    assert meta["last_run_phase"] == "full"
    assert meta["last_run_at"] == "2026-09-11T14:35:00+00:00"


def test_meta_資料到齊時不該亮黃燈(tmp_path, monkeypatch):
    from pipeline import build_payload, config
    data = tmp_path / "data"
    (data / "_state").mkdir(parents=True)
    monkeypatch.setattr(config, "STATE", data / "_state")
    (data / "_state" / "last_run.json").write_text(json.dumps(
        {"phase": "price", "trade_date": "2026-09-11", "errors": [], "empty": []}))
    monkeypatch.setattr(build_payload.store, "table_summary",
                        lambda: pd.DataFrame([{"table": "price_daily", "rows": 10,
                                               "latest": "2026-09-11"}]))
    monkeypatch.setattr(build_payload.loader, "health", lambda: {})

    meta = build_payload.meta_payload("2026-09-11", 250)
    assert meta["price_ahead_of_payload"] is False
    assert meta["last_run_empty"] == [] and meta["last_run_errors"] == []
    assert meta["last_run_phase"] == "price"
