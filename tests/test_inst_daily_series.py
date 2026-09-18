"""族群 × 法人的逐日序列（給 0–30 天拉 Bar 用）。

Andy 2026-09-18：「族群 × 法人需要新增時間週期也是拉 Bar 式，0-30 天，
且需要新增占比 % 單位」。原本只有 `period_flows()` 給的**期間**彙總
（本週／上週／本月／近三月），那是固定區間，拉不出「最近 N 天」。

這裡守住的是：**逐日給出來、日期對齊、缺值是 None 不是 0**。
缺值變 0 會讓「那天沒資料」和「那天真的是平盤」混在一起，
前端加總的時候就會把沒資料當成沒買賣，數字是錯的。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import flow


def _hist(rows):
    return pd.DataFrame([
        {"date": d, "group_id": g, "group_name": n,
         "foreign_net": f, "trust_net": t, "dealer_net": dl}
        for d, g, n, f, t, dl in rows
    ])


def test_逐日給出來而且日期由舊到新():
    h = _hist([
        ("2026-09-16", "ai", "AI 伺服器", 100.0, 10.0, 1.0),
        ("2026-09-17", "ai", "AI 伺服器", 200.0, 20.0, 2.0),
        ("2026-09-18", "ai", "AI 伺服器", 300.0, 30.0, 3.0),
    ])
    got = flow.inst_daily_series(h, 30)
    assert got["dates"] == ["2026-09-16", "2026-09-17", "2026-09-18"]
    g = got["groups"][0]
    assert g["group_id"] == "ai" and g["group_name"] == "AI 伺服器"
    assert g["foreign"] == [100.0, 200.0, 300.0]
    assert g["trust"] == [10.0, 20.0, 30.0]


def test_只給最近N天():
    h = _hist([(f"2026-09-{d:02d}", "ai", "AI", 1.0, 1.0, 1.0) for d in range(1, 21)])
    got = flow.inst_daily_series(h, 5)
    assert len(got["dates"]) == 5
    assert got["dates"][0] == "2026-09-16" and got["dates"][-1] == "2026-09-20"
    assert len(got["groups"][0]["foreign"]) == 5


def test_某天沒資料要給None不是0():
    """0 代表「那天法人剛好買賣相抵」，None 代表「那天根本沒資料」——
    混在一起的話，前端把 N 天加起來的數字就是錯的。"""
    h = _hist([
        ("2026-09-17", "ai", "AI", 100.0, 10.0, 1.0),
        ("2026-09-18", "ai", "AI", 200.0, 20.0, 2.0),
        ("2026-09-18", "pcb", "PCB", 50.0, 5.0, 0.5),   # pcb 只有 09-18 有
    ])
    got = flow.inst_daily_series(h, 30)
    pcb = next(g for g in got["groups"] if g["group_id"] == "pcb")
    assert pcb["foreign"] == [None, 50.0], pcb["foreign"]


def test_每個族群的長度都跟日期一樣長():
    """長度對不上，前端照索引取值就會拿到別天的數字。"""
    h = _hist([
        ("2026-09-16", "ai", "AI", 1.0, 1.0, 1.0),
        ("2026-09-17", "ai", "AI", 2.0, 2.0, 2.0),
        ("2026-09-17", "pcb", "PCB", 3.0, 3.0, 3.0),
    ])
    got = flow.inst_daily_series(h, 30)
    n = len(got["dates"])
    for g in got["groups"]:
        for k in ("foreign", "trust", "dealer"):
            assert len(g[k]) == n, (g["group_id"], k, len(g[k]), n)


def test_沒有法人欄位就回空的而不是炸掉():
    h = pd.DataFrame([{"date": "2026-09-18", "group_id": "ai", "group_name": "AI"}])
    assert flow.inst_daily_series(h, 30) == {"dates": [], "groups": []}


def test_空的資料也不會炸():
    assert flow.inst_daily_series(pd.DataFrame(), 30) == {"dates": [], "groups": []}
    assert flow.inst_daily_series(None, 30) == {"dates": [], "groups": []}
