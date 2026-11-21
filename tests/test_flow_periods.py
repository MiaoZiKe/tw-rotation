"""期間資金流向與資金集中度（資金流向頁的資料來源）。

重點不是「有沒有回東西」，而是口徑對不對：
佔比要加總 100、期間報酬要是複利、名次要照佔比排、前 10 大一定 ≥ 前 5 大。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.compute import flow


def _hist(days: int = 60, groups=("a", "b", "c", "d")) -> pd.DataFrame:
    """做一份假的族群日資料：日期是連續的工作日，量能與漲跌幅可預期。"""
    dates = pd.bdate_range("2026-06-01", periods=days).strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(dates):
        for j, g in enumerate(groups):
            rows.append({
                "date": d, "group_id": g, "group_name": g.upper(), "tier": "theme",
                "chain": "semiconductor",
                # a 的量能逐日變大，其他固定 —— 這樣「資金往 a 集中」是可以驗的
                "turnover": (100 + i * 10) if g == "a" else 100 + j,
                "chg_pct": 1.0 if g == "a" else -0.5,
                "foreign_net": 10 * (j + 1), "trust_net": 5, "dealer_net": -1,
            })
    out = pd.DataFrame(rows)
    total = out.groupby("date")["turnover"].transform("sum")
    out["turnover_share"] = out["turnover"] / total * 100
    return out


def test_期間有本週上週上上週本月上月近三月():
    r = flow.period_flows(_hist(90))
    keys = [p["key"] for p in r["periods"]]
    assert keys == list(flow.PERIOD_KEYS), keys
    for p in r["periods"]:
        assert p["from"] <= p["to"] and p["days"] >= 1
        assert p["label"] == flow.PERIOD_LABEL[p["key"]]


def test_每個期間的佔比加起來是一百():
    r = flow.period_flows(_hist(60))
    for p in r["periods"]:
        s = sum(g["share"] for g in p["groups"] if g["share"] is not None)
        assert s == pytest.approx(100, abs=0.05), (p["key"], s)


def test_名次照佔比排且第一名佔比最大():
    r = flow.period_flows(_hist(60))
    for p in r["periods"]:
        shares = [g["share"] for g in p["groups"]]
        assert shares == sorted(shares, reverse=True), p["key"]
        assert [g["rank"] for g in p["groups"]] == list(range(1, len(p["groups"]) + 1))


def test_量能越來越大的族群佔比一定是正成長():
    r = flow.period_flows(_hist(60))
    for p in r["periods"]:
        a = next(g for g in p["groups"] if g["group_id"] == "a")
        if a["share_chg"] is not None:
            assert a["share_chg"] > 0, (p["key"], a["share_chg"])


def test_期間報酬是複利不是相加():
    # a 每天 +1%，5 個交易日應該是 1.01**5 - 1 = 5.10%，不是 5.00%
    r = flow.period_flows(_hist(40))
    w0 = next(p for p in r["periods"] if p["key"] == "w0")
    a = next(g for g in w0["groups"] if g["group_id"] == "a")
    assert a["ret"] == pytest.approx((1.01 ** w0["days"] - 1) * 100, abs=0.01)


def test_法人是期間合計不是單日():
    r = flow.period_flows(_hist(40))
    w0 = next(p for p in r["periods"] if p["key"] == "w0")
    a = next(g for g in w0["groups"] if g["group_id"] == "a")
    assert a["foreign"] == pytest.approx(10 * w0["days"])
    assert a["trust"] == pytest.approx(5 * w0["days"])


def test_名次趨勢是舊到新且長度一致():
    r = flow.period_flows(_hist(90))
    bump = r["bump"]
    assert 2 <= len(bump["weeks"]) <= flow.BUMP_WEEKS
    assert bump["series"] and len(bump["series"]) <= flow.BUMP_TOP
    for s in bump["series"]:
        assert len(s["ranks"]) == len(bump["weeks"])
        assert len(s["shares"]) == len(bump["weeks"])
    # 最後一週的名次要對得上最新一週的實際名次
    last = [s["ranks"][-1] for s in bump["series"] if s["ranks"][-1] is not None]
    assert last == sorted(last)


def test_沒有資料不會爆掉():
    r = flow.period_flows(pd.DataFrame())
    assert r["periods"] == [] and r["bump"]["series"] == []
    assert r["bumps"]["week"]["series"] == [] and r["bumps"]["month"]["series"] == []
    r2 = flow.period_flows(None)
    assert r2["periods"] == []


# ---- 名次變化要跟著期間換刻度（Andy：「資金流向排名不會變」）
def test_名次變化有週和月兩份():
    r = flow.period_flows(_hist(180))
    assert set(r["bumps"]) == {"week", "month"}
    assert r["bumps"]["week"]["unit"] == "week"
    assert r["bumps"]["month"]["unit"] == "month"
    assert r["bump"] == r["bumps"]["week"]          # 舊欄位＝週，前端舊版不會壞


def test_月名次的刻度是月份而且和週的不一樣():
    r = flow.period_flows(_hist(180))
    wk, mo = r["bumps"]["week"], r["bumps"]["month"]
    assert all(len(x) == 5 for x in wk["weeks"]), wk["weeks"]     # MM/DD
    assert all(len(x) == 7 for x in mo["weeks"]), mo["weeks"]     # YYYY/MM
    assert wk["weeks"] != mo["weeks"]               # 兩張圖的 X 軸真的不一樣


def test_月名次也是舊到新而且每個族群長度一致():
    mo = flow.period_flows(_hist(180))["bumps"]["month"]
    assert mo["weeks"] == sorted(mo["weeks"])
    assert mo["series"], "至少要有一個族群"
    for s in mo["series"]:
        assert len(s["ranks"]) == len(mo["weeks"]) == len(s["shares"])


def test_資金往a集中時a的月名次會往前():
    """_hist 裡 a 的量能逐日變大，所以越晚的月份 a 的名次要越前面（數字越小）。"""
    mo = flow.period_flows(_hist(180))["bumps"]["month"]
    a = next(s for s in mo["series"] if s["group_id"] == "a")
    ranks = [r for r in a["ranks"] if r is not None]
    assert ranks[-1] <= ranks[0]


def test_資料只有幾天時只會有的期間才出現():
    r = flow.period_flows(_hist(3))
    keys = [p["key"] for p in r["periods"]]
    assert "w0" in keys                      # 本週一定有
    assert all(p["groups"] for p in r["periods"])


def test_集中度前十一定大於等於前五():
    c = flow.concentration(_hist(60))
    assert {"top_share", "top10_share", "top_share_ma20", "top10_share_ma20"} <= set(c.columns)
    assert (c["top10_share"] >= c["top_share"] - 1e-9).all()
    # 只有 4 個族群時，前 10 大就是全部 = 100%
    assert c["top10_share"].iloc[-1] == pytest.approx(100, abs=0.01)


def test_集中度是照日期排的():
    c = flow.concentration(_hist(30))
    assert list(c["date"]) == sorted(c["date"])
