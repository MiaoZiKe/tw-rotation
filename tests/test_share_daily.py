"""族群成交值佔比的逐日序列（給圖四資金流向排行的 1–30 天拉 Bar 用）。

Andy 2026-09-18 圖四：「資金流向排行需要跟資金輪動一樣以拉Bar 形式呈現，
並且一樣的設計，也是可以選時間週期拉Bar 1-30 天」。
原本排行只吃 `period_flows()` 給的**固定期間**（本週／上週／本月／近三月），
拉不出「最近 N 天」。

這裡守住的是四件會讓前端算出錯數字的事：

1. **逐日給出來、日期由舊到新、對齊同一組日期** —— 前端要靠索引切窗。
2. **缺值是 None 不是 0** —— 補 0 會把「那天沒資料」畫成「佔比掉到 0」，
   使用者看到的是一根假的斷崖。
3. **給 60 天不是 30** —— 拉 Bar 上限 30 天時，比較基準要再往前 30 天
   （「最近 30 天 vs 前 30 天」），只給 30 天的話比較基準是空的。
4. **chg 要一起給** —— 前端算區間複利報酬（連乘）用，不是拿日漲跌相加。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import flow


def _hist(rows):
    return pd.DataFrame([
        {"date": d, "group_id": g, "group_name": n, "chain": ch,
         "turnover_share": sh, "turnover": tv, "chg_pct": c}
        for d, g, n, ch, sh, tv, c in rows
    ])


def test_逐日給出來而且日期由舊到新():
    h = _hist([
        ("2026-09-16", "ai", "AI 伺服器", "ai_server", 10.0, 1e9, 1.0),
        ("2026-09-17", "ai", "AI 伺服器", "ai_server", 12.0, 1.2e9, 2.0),
        ("2026-09-18", "ai", "AI 伺服器", "ai_server", 11.0, 1.1e9, -0.5),
    ])
    got = flow.share_daily(h, 60)
    assert got["dates"] == ["2026-09-16", "2026-09-17", "2026-09-18"]
    g = got["groups"][0]
    assert g["group_id"] == "ai" and g["group_name"] == "AI 伺服器"
    assert g["chain"] == "ai_server"
    assert g["share"] == [10.0, 12.0, 11.0]
    assert g["turnover"] == [1e9, 1.2e9, 1.1e9]
    assert g["chg"] == [1.0, 2.0, -0.5]


def test_缺那天是None不是0():
    """「那天沒資料」和「那天佔比真的是 0」必須分得開。"""
    h = _hist([
        ("2026-09-16", "ai", "AI 伺服器", "ai_server", 10.0, 1e9, 1.0),
        ("2026-09-17", "ai", "AI 伺服器", "ai_server", 12.0, 1.2e9, 2.0),
        # ai 這天沒有，但另一個族群有 —— dates 會含 09-18
        ("2026-09-18", "pcb", "PCB", "pcb", 3.0, 3e8, 0.4),
    ])
    got = flow.share_daily(h, 60)
    assert got["dates"] == ["2026-09-16", "2026-09-17", "2026-09-18"]
    ai = [g for g in got["groups"] if g["group_id"] == "ai"][0]
    assert ai["share"] == [10.0, 12.0, None]
    assert ai["chg"] == [1.0, 2.0, None]
    pcb = [g for g in got["groups"] if g["group_id"] == "pcb"][0]
    assert pcb["share"] == [None, None, 3.0]


def test_只給最近N天():
    rows = [(f"2026-09-{d:02d}", "ai", "AI 伺服器", "ai_server", float(d), 1e9, 0.1)
            for d in range(1, 21)]
    got = flow.share_daily(_hist(rows), 5)
    assert len(got["dates"]) == 5
    assert got["dates"][0] == "2026-09-16" and got["dates"][-1] == "2026-09-20"
    assert got["groups"][0]["share"] == [16.0, 17.0, 18.0, 19.0, 20.0]


def test_預設給到60天讓前端算得出前30天的比較基準():
    rows = [(f"2026-{m:02d}-{d:02d}", "ai", "AI 伺服器", "ai_server", 1.0, 1e9, 0.1)
            for m in (7, 8, 9) for d in range(1, 29)]
    got = flow.share_daily(_hist(rows), 60)
    assert len(got["dates"]) == 60, "拉到 30 天時要能往前再取 30 天當比較基準"


def test_依最後一天的佔比由大到小():
    h = _hist([
        ("2026-09-18", "small", "小族群", "x", 1.0, 1e8, 0.1),
        ("2026-09-18", "big", "大族群", "y", 9.0, 9e8, 0.2),
        ("2026-09-18", "mid", "中族群", "z", 5.0, 5e8, 0.3),
    ])
    got = flow.share_daily(h, 60)
    assert [g["group_id"] for g in got["groups"]] == ["big", "mid", "small"]


def test_空資料不會爆():
    assert flow.share_daily(None, 60) == {"dates": [], "groups": []}
    assert flow.share_daily(pd.DataFrame(), 60) == {"dates": [], "groups": []}


def test_欄位缺了也給得出同長度的None陣列():
    """上游哪天少給一欄，前端仍然只做索引切窗，長度不能對不上。"""
    h = pd.DataFrame([
        {"date": "2026-09-17", "group_id": "ai", "group_name": "AI", "turnover_share": 1.0},
        {"date": "2026-09-18", "group_id": "ai", "group_name": "AI", "turnover_share": 2.0},
    ])
    got = flow.share_daily(h, 60)
    g = got["groups"][0]
    assert g["share"] == [1.0, 2.0]
    assert g["turnover"] == [None, None] and g["chg"] == [None, None]
    assert g["chain"] is None
