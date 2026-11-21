"""2026-10-03 晚：回補排程稀疏、續補分配、FinMind 錯誤以資料集為範圍（DECISIONS #311）。

事故 1（續補分配）：#304 合併後第一輪（backfill run 172，2026-10-02 22:59 UTC）法人續補上限 ×2＝1,200 檔、
排在第一個，寫了 499 檔就把這一輪 FinMind 額度用完（「inst@fresh2026-10-02 還剩 {'inst': 661} 檔沒補」），
當沖／借券的續補一次都沒輪到。而 GitHub 排程一天實際只觸發約 4 輪，照舊順序當沖要排在法人後面好幾輪。
→ 順序改成當沖、借券、上櫃融資券、法人，且每輪先照 FRESH_SHARE 分額度，法人保底一份。

事故 2（錯誤殘留）：http._last_error 是全域變數。上一個資料集撞到的錯誤（例如 inst 的 402 限流）
會被下一個資料集（例如 holding 整組回空）撿去當封印理由。→ 錯誤以資料集為範圍，成功一次就清掉。
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
from pipeline.util import http, store  # noqa: E402


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


# ------------------------------------------------------------------ 1. 錯誤以資料集為範圍

class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)
        self.headers = {}

    def json(self):
        return self._payload


def _serve(monkeypatch, plan):
    """plan：dataset → (HTTP 狀態, payload)。每次 GET 依 params["dataset"] 回應。"""
    class _S:
        def get(self, url, params=None, **kw):
            st, payload = plan[params["dataset"]]
            return _Resp(st, payload)
    monkeypatch.setattr(http, "session", lambda: _S())


def test_別的資料集的錯誤不會變成這個資料集的錯誤(sandbox, monkeypatch):
    _serve(monkeypatch, {
        # 用 400（不是 402）：402 會把本機額度填滿、後面的請求根本不會送出
        "TaiwanStockInstitutionalInvestorsBuySell": (400, {"msg": "Bad parameter", "status": 400}),
        "TaiwanStockHoldingSharesPer": (200, {"status": 200, "data": []}),
    })
    assert http.finmind_get("TaiwanStockInstitutionalInvestorsBuySell", data_id="2330") is None
    assert http.finmind_get("TaiwanStockHoldingSharesPer", data_id="2330") == []
    assert http.finmind_last_error("TaiwanStockHoldingSharesPer") is None, \
        "holding 自己沒有任何錯誤；inst 的錯誤不准算到它頭上"
    assert http.finmind_last_error("TaiwanStockInstitutionalInvestorsBuySell")["status"] == 400
    # 不帶資料集的舊用法：仍然是整個程序最後一次的錯誤（只給診斷 log 用）
    assert http.finmind_last_error()["dataset"] == "TaiwanStockInstitutionalInvestorsBuySell"


def test_成功一次就清掉這個資料集的舊錯誤(sandbox, monkeypatch):
    plan = {"TaiwanStockDayTrading": (400, {"msg": "Your level is register", "status": 400})}
    _serve(monkeypatch, plan)
    http.finmind_get("TaiwanStockDayTrading", data_id="2330")
    assert http.finmind_last_error("TaiwanStockDayTrading")["status"] == 400
    plan["TaiwanStockDayTrading"] = (200, {"status": 200, "data": [{"date": "2026-10-02"}]})
    assert http.finmind_get("TaiwanStockDayTrading", data_id="2330")
    assert http.finmind_last_error("TaiwanStockDayTrading") is None, "成功過了，舊錯誤已經不代表現況"
    assert http.finmind_last_error() is None, "全域那一筆剛好是它的，也一起清"


def test_封印理由只看這個資料集自己的錯誤(sandbox, monkeypatch):
    """#304 留下的待處理：inst 剛撞到 402，接著 holding 整組回空（台積電也空）→ 理由要寫「整組回空」，不是「HTTP 402」。"""
    http._last_errors["TaiwanStockInstitutionalInvestorsBuySell"] = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": "1101",
        "status": 402, "msg": "Requests reach the upper limit"}
    monkeypatch.setattr(http, "_last_error", dict(http._last_errors["TaiwanStockInstitutionalInvestorsBuySell"]))
    monkeypatch.setattr(run_backfill.finmind, "holding_history", lambda c, s, wait=False: pd.DataFrame())
    run_backfill.run("holding", None, "2021-01-01", codes=["2454", "2317", "2382", "1101"])
    rec = json.loads(run_backfill.PROGRESS.read_text())["unavailable"]["holding"]
    assert rec["last_reason"] == "整組回空", f"封印理由撿到了別的資料集的錯誤：{rec['last_reason']}"


def test_封印理由照樣寫得出這個資料集自己的400(sandbox, monkeypatch):
    http._last_errors["TaiwanStockHoldingSharesPer"] = {
        "dataset": "TaiwanStockHoldingSharesPer", "data_id": "2330", "status": 400, "msg": "Your level is register"}
    monkeypatch.setattr(run_backfill.finmind, "holding_history", lambda c, s, wait=False: pd.DataFrame())
    run_backfill.run("holding", None, "2021-01-01", codes=["2454", "2317", "2382", "1101"])
    rec = json.loads(run_backfill.PROGRESS.read_text())["unavailable"]["holding"]
    assert "400" in rec["last_reason"] and "register" in rec["last_reason"]


def test_每個回補資料集都對得到FinMind的dataset名稱():
    assert set(run_backfill.FINMIND_DATASET) == set(run_backfill.DATA_KEYS), \
        "新增回補資料集時要一起登記 FinMind 名稱，不然封印理由會退回「整組回空」"


# ------------------------------------------------------------------ 2. 續補：當沖借券先補、法人保底一份

CODES = [f"{9000 + i}" for i in range(30)]


def _seed_four_tables():
    store.append("price_daily", pd.DataFrame({"date": ["2026-10-02"] * len(CODES), "code": CODES,
                                              "close": [1.0] * len(CODES),
                                              "turnover": [float(100 - i) for i in range(len(CODES))]}))
    old = {"date": ["2026-09-24"] * len(CODES), "code": CODES}
    store.append("daytrade_daily", pd.DataFrame({**old, "daytrade_volume": [1.0] * len(CODES)}))
    store.append("sbl_daily", pd.DataFrame({**old, "sbl_sell": [1.0] * len(CODES)}))
    store.append("margin_daily", pd.DataFrame({**old, "margin_balance": [1.0] * len(CODES)}))
    store.append("inst_daily", pd.DataFrame({**old, "foreign": [1.0] * len(CODES)}))


def _fake_fetchers(monkeypatch, budget: dict, asked: list):
    """每問一次扣 1 次額度；回一筆 10-02 的資料。"""
    def mk(key, cols):
        def f(code, start, *a, **k):
            budget["left"] -= 1
            asked.append(key)
            return pd.DataFrame({"date": ["2026-10-02"], "code": [code], **{c: [1.0] for c in cols}})
        return f
    monkeypatch.setattr(run_backfill.finmind, "day_trading", mk("daytrade", ["daytrade_volume"]))
    monkeypatch.setattr(run_backfill.finmind, "short_sale_balances", mk("sbl", ["sbl_sell"]))
    monkeypatch.setattr(run_backfill.finmind, "margin_history", mk("margin", ["margin_balance"]))
    monkeypatch.setattr(run_backfill.finmind, "institutional", mk("inst", ["foreign"]))
    monkeypatch.setattr(http, "finmind_budget_left", lambda: budget["left"])


def test_額度不夠時當沖先做_法人與上櫃融資券有保底(sandbox, monkeypatch):
    _seed_four_tables()
    monkeypatch.setattr(run_backfill, "market_codes", lambda: CODES)
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-10"}}})
    budget, asked = {"left": 42}, []
    _fake_fetchers(monkeypatch, budget, asked)

    ok = run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 3))

    assert ok is False, "名單 120 檔、額度 42 次，不可能今天做完"
    n = {k: asked.count(k) for k in ("daytrade", "sbl", "margin", "inst")}
    share = {k: int(42 * run_backfill.FRESH_SHARE.get(k, 0)) for k in n}
    assert n["margin"] == share["margin"] >= 1 and n["inst"] == share["inst"] >= 1, \
        f"法人與上櫃融資券要有保底份額，不能被前面吃光：{n}"
    # 保底做完，剩下的照順序：當沖 30 檔整份做完，最後一點額度才輪到借券
    assert asked[share["margin"] + share["inst"]:] == ["daytrade"] * 30 + ["sbl"] * n["sbl"], asked
    assert 1 <= n["sbl"] <= 2, n
    # 舊行為（法人第一、照順序吃光）會是 {'inst': 40, 其他 0}
    prog = json.loads(run_backfill.PROGRESS.read_text())
    for key in n:
        rec = prog["complete"][f"{key}@fresh2026-10-02"]
        assert rec["codes"] == len(CODES), "完成旗標要記整份名單（不是第一段那一小段）"
        # 撞到限流那一筆會被丟掉（不算補到），所以剩下的介於「名單 − 問過的」與再多 1 之間
        assert len(CODES) - asked.count(key) <= rec["remaining"][key] <= len(CODES) - asked.count(key) + 1, rec


def test_有保底的表名單比份額短時在第一段就整份做完(sandbox, monkeypatch):
    """法人只剩 3 檔落後、份額有 15 檔：要在第一段做完，不能留到第二段排在當沖借券後面被吃光。"""
    _seed_four_tables()
    store.append("inst_daily", pd.DataFrame({"date": ["2026-10-02"] * 27, "code": CODES[3:], "foreign": [1.0] * 27}))
    monkeypatch.setattr(run_backfill, "market_codes", lambda: CODES)
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-10"}}})
    budget, asked = {"left": 100}, []
    _fake_fetchers(monkeypatch, budget, asked)
    run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 3))
    assert asked.count("inst") == 3, asked


def test_額度夠時照順序全部做完(sandbox, monkeypatch):
    _seed_four_tables()
    monkeypatch.setattr(run_backfill, "market_codes", lambda: CODES)
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-10"}}})
    budget, asked = {"left": 10_000}, []
    _fake_fetchers(monkeypatch, budget, asked)

    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 3)) is True
    assert asked == ["daytrade"] * 30 + ["sbl"] * 30 + ["margin"] * 30 + ["inst"] * 30, \
        "額度夠就不分段，照 FRESH_TABLES 的順序一張一張做完"
    for t in ("daytrade_daily", "sbl_daily", "margin_daily", "inst_daily"):
        assert (store.read(t)["date"].astype(str) == "2026-10-02").sum() == len(CODES)


def test_第二輪接著做而且不重問第一段補過的(sandbox, monkeypatch):
    _seed_four_tables()
    monkeypatch.setattr(run_backfill, "market_codes", lambda: CODES)
    run_backfill._save_progress({"done": {}, "complete": {"plan:default": {"done": True, "month": "2026-10"}}})
    budget, asked = {"left": 42}, []
    _fake_fetchers(monkeypatch, budget, asked)
    run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 3))
    first = len(asked)
    run_backfill._cov_cache.clear()

    budget["left"] = 10_000                          # 下一個小時，額度回來了
    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 10, 3)) is True
    total = {k: asked.count(k) for k in ("daytrade", "sbl", "margin", "inst")}
    # 被當成限流丟掉的那一筆（第一輪最後一次）會重問一次，其餘一檔只問一次
    assert sum(total.values()) - first <= 120 - (first - 1)
    for t in ("daytrade_daily", "sbl_daily", "margin_daily", "inst_daily"):
        assert (store.read(t)["date"].astype(str) == "2026-10-02").sum() == len(CODES)


def test_上限與份額的設定():
    keys = [k for k, _, _ in run_backfill.FRESH_TABLES]
    assert keys == ["daytrade", "sbl", "margin", "inst"]
    assert sum(run_backfill.FRESH_SHARE.values()) < 0.5, "保底只是保底，大部分額度要留給當沖、借券"
    assert set(run_backfill.FRESH_SHARE) <= set(keys)
    assert run_backfill.FRESH_SHARE["inst"] > 0 and run_backfill.FRESH_SHARE["margin"] > 0, \
        "排在後面的法人與上櫃融資券要有保底，不然平日整週輪不到"
