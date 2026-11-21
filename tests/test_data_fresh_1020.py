"""資料新鮮度把關＋整天全市場法人補抓（2026-10-20）。全部用假資料，不打真 API。

起因：10-19 個股三大法人只進 148～249 檔，管線卻全綠，頁面默默退回 10-16。
"""
from __future__ import annotations

import pandas as pd

from pipeline import inst_bulk
from pipeline.sources import finmind
from pipeline.util import freshness


def _s(d: dict) -> pd.Series:
    return pd.Series(d, dtype="int64")


def _days(n_last, base=1900, extra=None):
    d = {f"2026-10-{i:02d}": base for i in (5, 6, 7, 8, 9, 12, 13, 14, 15, 16)}
    d["2026-10-19"] = n_last
    return _s(d)


def test_最新日筆數太少_標warn():
    out = freshness.evaluate({"inst_daily": _days(249)}, "2026-10-19")
    t = out["tables"]["inst_daily"]
    assert t["status"] == "warn" and t["reason"] == "thin"
    assert "inst_daily" in out["warn"] and "個股三大法人" in out["warn_labels"]


def test_筆數正常_ok():
    out = freshness.evaluate({"inst_daily": _days(1850)}, "2026-10-19")
    assert out["tables"]["inst_daily"]["status"] == "ok"


def test_剛好八成算過_差一檔不過():
    assert freshness.evaluate({"inst_daily": _days(1520)}, "2026-10-19")["tables"]["inst_daily"]["status"] == "ok"
    assert freshness.evaluate({"inst_daily": _days(1519)}, "2026-10-19")["tables"]["inst_daily"]["status"] == "warn"


def test_表落後一天_和_整張沒進湖():
    behind = _s({"2026-10-15": 1, "2026-10-16": 1})
    out = freshness.evaluate({"margin_total": behind}, "2026-10-19")
    assert out["tables"]["margin_total"]["reason"] == "behind"
    assert out["tables"]["inst_market_daily"]["reason"] == "missing"       # 沒給 counts ＝ 湖裡沒有
    assert {"margin_total", "inst_market_daily"} <= set(out["warn"])


def test_當天傍晚前是pending_不亮警告():
    out = freshness.evaluate({"inst_daily": _days(10)}, "2026-10-19", pending=True)
    assert out["tables"]["inst_daily"]["status"] == "pending" and out["warn"] == []


def test_沒有歷史可比就只看有沒有到最新日():
    out = freshness.evaluate({"fut_oi": _s({"2026-10-19": 1})}, "2026-10-19")
    assert out["tables"]["fut_oi"]["status"] == "ok"


def test_thin_dates挑出缺口日():
    price = _s({f"2026-10-{i:02d}": 2300 for i in (13, 14, 15, 16, 19)})
    inst = _s({"2026-10-13": 1900, "2026-10-14": 1900, "2026-10-15": 1900, "2026-10-16": 1900, "2026-10-19": 249})
    assert inst_bulk.thin_dates(price, inst) == ["2026-10-19"]
    inst2 = inst.copy()
    inst2["2026-10-19"] = 1900
    assert inst_bulk.thin_dates(price, inst2) == []


def test_價量沒到齊的日子不拿去問():
    price = _s({"2026-10-15": 2300, "2026-10-16": 2300, "2026-10-19": 40})
    inst = _s({"2026-10-15": 1900, "2026-10-16": 1900})
    assert inst_bulk.thin_dates(price, inst) == []


def _long(day, codes):
    rows = []
    for c in codes:
        for name, buy, sell in (("Foreign_Investor", 300, 100), ("Investment_Trust", 50, 10),
                                ("Dealer_self", 20, 5), ("Dealer_Hedging", 7, 2)):
            rows.append({"date": day, "stock_id": c, "name": name, "buy": buy, "sell": sell})
    return rows


def test_institutional_day_轉寬格式(monkeypatch):
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: _long("2026-10-19", ["2330", "2317"]))
    df = finmind.institutional_day("2026-10-19")
    assert sorted(df["code"]) == ["2317", "2330"]
    r = df[df["code"] == "2330"].iloc[0]
    assert r["foreign"] == 200 and r["trust"] == 40 and r["dealer"] == 20 and r["inst_total"] == 260


def test_institutional_day_沒權限回空(monkeypatch):
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: None)
    monkeypatch.setattr(finmind.http, "finmind_last_error", lambda d=None: {"status": 400, "msg": "level"})
    assert finmind.institutional_day("2026-10-19").empty


def test_institutional_day_欄位對不上回空(monkeypatch):
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: [{"date": "2026-10-19", "x": 1}])
    assert finmind.institutional_day("2026-10-19").empty


def test_fill_inst_bulk_只收那一天且濾掉權證(monkeypatch):
    price = pd.DataFrame({"date": ["2026-10-16"] * 600 + ["2026-10-19"] * 600, "code": list(range(600)) * 2})
    inst = pd.DataFrame({"date": ["2026-10-16"] * 600 + ["2026-10-19"] * 10, "code": list(range(600)) + list(range(10))})
    monkeypatch.setattr(inst_bulk.store, "read", lambda t, years=None: price if t == "price_daily" else inst)
    monkeypatch.setattr(inst_bulk.http, "finmind_budget_left", lambda: 50)
    got = pd.DataFrame({"date": ["2026-10-19", "2026-10-19", "2026-10-18"], "code": ["2330", "03001P", "2330"],
                        "inst_total": [1.0, 2.0, 3.0]})
    called = []
    monkeypatch.setattr(inst_bulk.finmind, "institutional_day", lambda d, wait=False: called.append(d) or got)
    out = inst_bulk.fill_inst_bulk()
    assert called == ["2026-10-19"]
    assert out["code"].tolist() == ["2330"] and set(out["date"]) == {"2026-10-19"}


def test_fill_inst_bulk_拿不到整天就停_不重複燒額度(monkeypatch):
    price = pd.DataFrame({"date": ["2026-10-15"] * 600 + ["2026-10-16"] * 600 + ["2026-10-19"] * 600, "code": list(range(600)) * 3})
    inst = pd.DataFrame({"date": ["2026-10-15"] * 600, "code": list(range(600))})
    monkeypatch.setattr(inst_bulk.store, "read", lambda t, years=None: price if t == "price_daily" else inst)
    monkeypatch.setattr(inst_bulk.http, "finmind_budget_left", lambda: 50)
    n = []
    monkeypatch.setattr(inst_bulk.finmind, "institutional_day", lambda d, wait=False: n.append(d) or pd.DataFrame())
    assert inst_bulk.fill_inst_bulk().empty and len(n) == 1


def test_fill_inst_bulk_額度用盡不呼叫(monkeypatch):
    price = pd.DataFrame({"date": ["2026-10-19"] * 600, "code": list(range(600))})
    monkeypatch.setattr(inst_bulk.store, "read", lambda t, years=None: price if t == "price_daily" else pd.DataFrame())
    monkeypatch.setattr(inst_bulk.http, "finmind_budget_left", lambda: 0)
    monkeypatch.setattr(inst_bulk.finmind, "institutional_day", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert inst_bulk.fill_inst_bulk().empty


def test_with_site_codes_去重保序(monkeypatch):
    monkeypatch.setattr(inst_bulk, "site_codes", lambda: ["2330", "9999", "1101"])
    assert inst_bulk.with_site_codes(["2330", "2317"]) == ["2330", "2317", "9999", "1101"]


def test_meta帶出過期清單(monkeypatch):
    import pipeline.build_payload as bp
    fake = freshness.evaluate({"inst_daily": _days(249)}, "2026-10-19")
    monkeypatch.setattr(bp.freshness, "check", lambda *a, **k: fake)
    m = bp.meta_payload("2026-10-19", 10)
    assert "個股三大法人" in m["freshness_warn"] and m["freshness"]["trade_date"] == "2026-10-19"
