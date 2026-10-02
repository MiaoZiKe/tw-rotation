"""2026-10-03 當沖／借券誤封印、上櫃融資券斷更（DECISIONS #304）。

事故：09-28 那輪每日續補挑「落後最久」的 72 檔去問當沖，而落後最久的正是早就不能當沖、
最後一筆停在 2025 年的股票 → 20 檔全空 → daytrade 被封印「整組回空」；sbl 同理（10 檔）。
之後每天的探測又拿名單最前面那 5 檔（同一批）去問 → 永遠探不通，09-25 之後全市場一筆都沒有。
（實際日誌：backfill run 36456219124，「daytrade 每日續補：72 檔落後於 2026-09-24（…從 2026-06-26 起抓）」
→「連續 20 檔回空且一次都沒成功」→「判定為該資料集不開放…上游回應：整組回空」。）

另外：上櫃的融資券沒有任何每日來源（證交所 MI_MARGN 只有上市），只靠計畫裡一次性的歷史步驟補到 09-23，
所以 margin_daily 從 09-24 起每天只剩上市的 1,298 檔。
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
from pipeline.compute import stockpage  # noqa: E402
from pipeline.util import http, store  # noqa: E402


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir()
    (tmp_path / "state").mkdir()
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "state" / "finmind_quota.json")
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "state" / "backfill_progress.json")
    # 上一支測試留下的「最後一次錯誤」是全域變數，會被誤當成這一輪的封印理由
    monkeypatch.setattr(http, "_last_error", None)
    run_backfill._cov_cache.clear()
    return tmp_path


def _dt(code, d="2026-09-24"):
    return pd.DataFrame({"date": [d], "code": [code], "daytrade_volume": [1000.0],
                         "daytrade_buy_amount": [1.0], "daytrade_sell_amount": [1.0],
                         "buy_after_sale": ["Y"]})


def _sealed(key, reason="整組回空"):
    return {"done": {}, "complete": {},
            "unavailable": {key: {"since": "2026-09-28T17:16:04+00:00",
                                  "last_probe": run_backfill._now().isoformat(),
                                  "probes": 3, "last_reason": reason}}}


def test_名單全是本來就沒資料的股票時台積電反證成立就不封印(sandbox, monkeypatch):
    dormant = [str(3000 + i) for i in range(25)]
    asked = []

    def fake(code, start, wait=False):
        asked.append(code)
        return _dt(code) if code == run_backfill.CANARY_CODE else pd.DataFrame()

    monkeypatch.setattr(run_backfill.finmind, "day_trading", fake)
    summary = run_backfill.run("daytrade", None, "2026-06-26", codes=dormant,
                               datasets_key="daytrade@fresh2026-09-24", tag="fresh2026-09-24",
                               respect_time=False)
    prog = json.loads(run_backfill.PROGRESS.read_text())

    assert "daytrade" not in (prog.get("unavailable") or {}), "台積電拿得到 → 資料集是通的，不准封印"
    assert not summary.get("unavailable")
    lim = run_backfill.EMPTY_STREAK_LIMIT
    assert asked == dormant[:lim] + [run_backfill.CANARY_CODE] + dormant[lim:], \
        "反證成立後要繼續把名單問完，不是收手"
    for c in dormant:
        assert prog["done"][f"daytrade@fresh2026-09-24:{c}"] == run_backfill.NO_DATA
    got = store.read("daytrade_daily")
    assert set(got["code"].astype(str)) == {run_backfill.CANARY_CODE}, "反證拿到的資料照樣進湖"


def test_台積電也空才封印(sandbox, monkeypatch):
    monkeypatch.setattr(run_backfill.finmind, "day_trading", lambda c, s, wait=False: pd.DataFrame())
    summary = run_backfill.run("daytrade", None, "2026-06-26", codes=["3001", "3002", "3003"])
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert summary.get("unavailable") == ["daytrade"]
    assert prog["unavailable"]["daytrade"]["last_reason"] == "整組回空"


def test_區間內沒有交易日不判定封印也不寫done(sandbox, monkeypatch):
    """連假：資料湖最新交易日 09-24，問 09-25 起 → 一定全空，不能拿來判定任何事。"""
    store.append("price_daily", pd.DataFrame({"date": ["2026-09-24"], "code": ["2330"], "close": [1.0]}))
    asked = []
    monkeypatch.setattr(run_backfill.finmind, "day_trading",
                        lambda c, s, wait=False: asked.append(c) or pd.DataFrame())
    summary = run_backfill.run("daytrade", None, "2026-09-25", codes=["2330", "2454", "2317"])
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert "daytrade" not in (prog.get("unavailable") or {})
    assert not [k for k in prog["done"] if k.startswith("daytrade")], "沒判定就不寫 done，下一輪重問"
    assert asked == ["2330", "2454", "2317"], "沒有交易日連反證都不必問"
    assert not summary.get("unavailable")


def test_先前以整組回空封印的會被台積電驗通後當場解封(sandbox, monkeypatch):
    """main 上現在的狀態：daytrade／sbl 封印中（last_reason＝整組回空、剛探過）。修完不必手改進度檔。"""
    asked = []

    def fake(code, start, wait=False):
        asked.append(code)
        return _dt(code, "2026-10-01")

    monkeypatch.setattr(run_backfill.finmind, "day_trading", fake)
    run_backfill.PROGRESS.write_text(json.dumps(_sealed("daytrade"), ensure_ascii=False))
    run_backfill.run("daytrade", None, "2026-09-10", codes=["2454", "2317"],
                     tag="fresh2026-10-01", respect_time=False)
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert "daytrade" not in prog.get("unavailable", {}), "誤封印要當場解除"
    assert asked == [run_backfill.CANARY_CODE, "2454", "2317"], "解封後這一輪就恢復全量"
    assert prog["done"]["daytrade@fresh2026-10-01:2317"] is True


def test_有明確錯誤原因的封印不走台積電驗證(sandbox, monkeypatch):
    asked = []
    monkeypatch.setattr(run_backfill.finmind, "holding_history",
                        lambda c, s, wait=False: asked.append(c) or pd.DataFrame())
    run_backfill.PROGRESS.write_text(json.dumps(
        _sealed("holding", "HTTP 400：Your level is register."), ensure_ascii=False))
    run_backfill.run("holding", None, "2021-01-01", codes=["2454", "2317", "2382"])
    assert asked == [], "等級不足是確定的原因，封印期內一次都不問"


def test_台積電驗不通時24小時內不重驗(sandbox, monkeypatch):
    asked = []
    monkeypatch.setattr(run_backfill.finmind, "day_trading",
                        lambda c, s, wait=False: asked.append(c) or pd.DataFrame())
    run_backfill.PROGRESS.write_text(json.dumps(_sealed("daytrade"), ensure_ascii=False))
    run_backfill.run("daytrade", None, "2026-09-10", codes=["2454"])
    run_backfill.run("daytrade", None, "2026-09-10", codes=["2454"])
    assert asked == [run_backfill.CANARY_CODE], "驗過一次不通，24 小時內不再花額度"
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["unavailable"]["daytrade"]["canary_at"]


def test_續補排序把早就沒資料的股票排到最後():
    price = pd.DataFrame({"code": ["OLD", "A", "B", "C"], "date": ["2026-10-01"] * 4})
    tbl = pd.DataFrame({"code": ["OLD", "A", "B", "C"],
                        "date": ["2025-04-01", "2026-09-24", "2026-09-22", "2026-09-24"]})
    latest, codes = run_backfill.stale_inst_codes(tbl, price, ["OLD", "A", "B", "C"], cap=3)
    assert latest == "2026-10-01"
    assert codes == ["B", "A", "C"], "還活著的照落後先後排；停在 2025 年的那檔降到最後（這裡被上限擠掉）"
    _, all_codes = run_backfill.stale_inst_codes(tbl, price, ["OLD", "A", "B", "C"], cap=10)
    assert all_codes[-1] == "OLD", "降級不是剔除，額度有剩照樣補"


def test_整張表一起落後時不會整批被降級():
    """上游停了兩週：大家的最後一天都很舊，但相對於這張表自己的最新日期都還是「活著」。"""
    price = pd.DataFrame({"code": ["A", "B"], "date": ["2026-10-20"] * 2})
    tbl = pd.DataFrame({"code": ["A", "B"], "date": ["2026-09-24", "2026-09-22"]})
    _, codes = run_backfill.stale_inst_codes(tbl, price, ["A", "B"], cap=2)
    assert codes == ["B", "A"]


def test_續補納入上櫃融資券且計畫補齊時上限加倍(sandbox, monkeypatch):
    keys = [k for k, _, _ in run_backfill.FRESH_TABLES]
    assert "margin" in keys, "上櫃融資券沒有每日來源，一定要在續補裡（margin_daily 09-24 起少 530 檔）"
    codes = ["6488", "5483", "8069"]
    store.append("price_daily", pd.DataFrame({"date": ["2026-10-01"] * 3, "code": codes,
                                              "close": [1.0] * 3, "turnover": [3.0, 2.0, 1.0]}))
    store.append("margin_daily", pd.DataFrame({"date": ["2026-09-23"] * 3, "code": codes,
                                               "margin_balance": [1.0] * 3}))
    monkeypatch.setattr(run_backfill, "FRESH_TABLES", (("margin", "margin_daily", 1),))
    monkeypatch.setattr(run_backfill, "market_codes", lambda: codes)
    asked = []

    def fake(code, start, wait=False):
        asked.append((code, start))
        return pd.DataFrame({"date": ["2026-10-01"], "code": [code], "margin_balance": [2.0],
                             "margin_change": [1.0], "short_balance": [0.0], "short_change": [0.0],
                             "margin_buy": [1.0], "margin_sell": [0.0], "short_sell": [0.0],
                             "short_cover": [0.0], "offset": [0.0]})
    monkeypatch.setattr(run_backfill.finmind, "margin_history", fake)
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-10"}}})
    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 2)) is True
    assert len(asked) == 1 * run_backfill.FRESH_BOOST, "計畫本月補齊 → 上限 ×FRESH_BOOST"
    assert {s for _, s in asked} == {"2026-09-17"}, "從 09-23 往回 14 天前的 09-17 起抓（取兩者較早）"
    m = store.read("margin_daily")
    assert (m["date"].astype(str) == "2026-10-01").sum() == len(asked)


def test_計畫沒補齊時續補上限不加倍(sandbox, monkeypatch):
    codes = ["6488", "5483", "8069"]
    store.append("price_daily", pd.DataFrame({"date": ["2026-10-01"] * 3, "code": codes, "close": [1.0] * 3}))
    store.append("margin_daily", pd.DataFrame({"date": ["2026-09-23"] * 3, "code": codes,
                                               "margin_balance": [1.0] * 3}))
    monkeypatch.setattr(run_backfill, "FRESH_TABLES", (("margin", "margin_daily", 1),))
    monkeypatch.setattr(run_backfill, "market_codes", lambda: codes)
    asked = []
    monkeypatch.setattr(run_backfill.finmind, "margin_history",
                        lambda c, s, wait=False: asked.append(c) or pd.DataFrame(
                            {"date": ["2026-10-01"], "code": [c], "margin_balance": [2.0]}))
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-09"}}})
    run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 2))
    assert len(asked) == 1, "上個月補齊的不算（這個月的計畫還沒跑完）"


# --------------------------------------------- 頁面：資料源更新到哪一天
def test_資券各來源的最新日期():
    mg = pd.DataFrame({"date": ["2026-10-01", "2026-09-30"], "code": ["2330", "2330"]})
    dt = pd.DataFrame({"date": ["2026-09-24"], "code": ["2330"]})
    asof = stockpage.margin_asof(mg, dt, pd.DataFrame())
    assert asof == {"margin": "2026-10-01", "daytrade": "2026-09-24", "sbl": None}
    assert stockpage.margin_asof(None, None, None) == {"margin": None, "daytrade": None, "sbl": None}
