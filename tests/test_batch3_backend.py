"""批次3 的後端：集中度帶族群、集中度成分股、資金去向逐日。

Andy 2026-09-18 原話：
- 「資金集中度 前幾大當我游標點選那天時，會旁邊出現對應族群，
   且對應族群在點會出現對應股票，此時的股票點選才會連結到個股畫面」
- 圖六「一樣都具備相資金輪動的拉Bar 可以觀察並搭配播放功能」

這裡守住的是四件會讓前端算錯或畫錯的事：
1. **每一天都要帶當天的前 N 大是誰** —— 前端點哪天就讀哪天，不要再回頭問後端。
2. **一檔股票可以屬於多個族群** —— `loader.membership()` 是長格式，不是 dict，
   同一檔要同時算進它所屬的每一個族群。
3. **日期對齊** —— 逐日序列一律 reindex 到同一組日期，缺的是 None 不是 0。
4. **空資料不爆** —— 這幾支在管線裡是 try 包起來的，但回傳形狀仍要是對的，
   否則前端會拿到 undefined 而不是空陣列。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import flow, rrg


def _gh(rows):
    """group_hist：一列一個 (date, group)。"""
    return pd.DataFrame([
        {"date": d, "group_id": g, "group_name": n, "chain": ch,
         "turnover": tv, "turnover_share": sh}
        for d, g, n, ch, tv, sh in rows
    ])


def _px(rows):
    return pd.DataFrame([{"date": d, "code": c, "name": n, "turnover": tv}
                         for d, c, n, tv in rows])


def _mem(rows):
    """loader.membership() 的長格式：一列一個 code×group_id。"""
    return pd.DataFrame([{"code": c, "group_id": g, "group_name": g,
                          "tier": "standalone", "chain": "other"} for c, g in rows])


# ---------------------------------------------------------------- 集中度
def test_集中度每一天都帶當天的前幾大族群():
    h = _gh([
        ("2026-09-18", "ai", "AI 伺服器", "ai_server", 9e8, 45.0),
        ("2026-09-18", "pcb", "PCB", "pcb", 5e8, 25.0),
        ("2026-09-18", "sml", "小族群", "other", 1e8, 5.0),
    ])
    out = flow.concentration(h).to_dict("records")
    assert len(out) == 1
    top = out[0]["top"]
    assert [t["g"] for t in top] == ["ai", "pcb", "sml"], "要照成交值由大到小"
    assert top[0]["n"] == "AI 伺服器" and top[0]["share"] == 45.0


def test_集中度前5與前10分開算():
    rows = [("2026-09-18", f"g{i}", f"族群{i}", "other", (20 - i) * 1e7, float(20 - i))
            for i in range(12)]
    out = flow.concentration(_gh(rows)).to_dict("records")[0]
    assert out["top_share"] == sum(float(20 - i) for i in range(5))
    assert out["top10_share"] == sum(float(20 - i) for i in range(10))
    assert len(out["top"]) == 10, "top 只留前 10，不是全部"


# ---------------------------------------------------------------- 集中度成分股
def test_集中度成分股_一檔可以屬於多個族群():
    h = _gh([("2026-09-18", "ai", "AI", "ai_server", 9e8, 45.0),
             ("2026-09-18", "pcb", "PCB", "pcb", 5e8, 25.0)])
    px = _px([("2026-09-18", "2330", "台積電", 8e8),
              ("2026-09-18", "3231", "緯創", 3e8)])
    mem = _mem([("2330", "ai"), ("2330", "pcb"), ("3231", "ai")])
    out = flow.concentration_members(h, px, mem, 400)
    assert "2026-09-18" in out
    day = out["2026-09-18"]
    assert [m["code"] for m in day["ai"]] == ["2330", "3231"], "族群內照成交值排序"
    assert [m["code"] for m in day["pcb"]] == ["2330"], "同一檔要同時算進它所屬的每個族群"
    assert day["ai"][0]["name"] == "台積電"


def test_集中度成分股_只留最近N天():
    rows = [(f"2026-09-{d:02d}", "ai", "AI", "ai_server", 1e9, 50.0) for d in range(1, 11)]
    px = _px([(f"2026-09-{d:02d}", "2330", "台積電", 1e8) for d in range(1, 11)])
    out = flow.concentration_members(_gh(rows), px, _mem([("2330", "ai")]), days=3)
    assert sorted(out) == ["2026-09-08", "2026-09-09", "2026-09-10"]


def test_集中度成分股_沒有成分表就回空而不是爆掉():
    h = _gh([("2026-09-18", "ai", "AI", "ai_server", 9e8, 45.0)])
    px = _px([("2026-09-18", "2330", "台積電", 8e8)])
    assert flow.concentration_members(h, px, None, 400) == {}
    assert flow.concentration_members(h, px, pd.DataFrame(), 400) == {}
    assert flow.concentration_members(None, px, _mem([("2330", "ai")]), 400) == {}


# ---------------------------------------------------------------- 資金去向逐日
def test_資金去向逐日_日期對齊而且缺的是None():
    h = _gh([
        ("2026-09-17", "ai", "AI", "ai_server", 9e8, 45.0),
        ("2026-09-18", "ai", "AI", "ai_server", 8e8, 40.0),
        ("2026-09-18", "pcb", "PCB", "pcb", 5e8, 25.0),
    ])
    out = rrg.sankey_daily(h, pd.DataFrame(), None, 60)
    assert out["dates"] == ["2026-09-17", "2026-09-18"]
    pcb = [g for g in out["groups"] if g["gid"] == "pcb"][0]
    assert pcb["tv"] == [None, 5e8], "那天沒資料要是 None，不可以補 0"
    ai = [g for g in out["groups"] if g["gid"] == "ai"][0]
    assert ai["chain"] == "ai_server"


def test_資金去向逐日_每天每族群的前幾檔():
    h = _gh([("2026-09-18", "ai", "AI", "ai_server", 9e8, 45.0)])
    px = _px([("2026-09-18", "2330", "台積電", 8e8),
              ("2026-09-18", "3231", "緯創", 3e8),
              ("2026-09-18", "2317", "鴻海", 1e8)])
    mem = _mem([("2330", "ai"), ("3231", "ai"), ("2317", "ai")])
    out = rrg.sankey_daily(h, px, mem, 60, top_members=2)
    leaves = out["leaves"]["2026-09-18"]
    assert [x["code"] for x in leaves] == ["2330", "3231"], "每族群只留前 N 檔、照成交值"
    assert all(x["gid"] == "ai" for x in leaves)


def test_資金去向逐日_空資料形狀仍然是對的():
    empty = {"dates": [], "groups": [], "leaves": {}}
    assert rrg.sankey_daily(None, None, None) == empty
    assert rrg.sankey_daily(pd.DataFrame(), None, None) == empty


# ---------------------------------------------------------------- 河流圖天數
def test_河流圖預設給到250天():
    """圖七要「把截止日往前挪、一天一天回放」，60 天回放兩下就沒了。"""
    rows = [(f"2026-{m:02d}-{d:02d}", "ai", "AI", "ai_server", 1e9, 50.0)
            for m in range(1, 13) for d in range(1, 26)]
    out = rrg.share_series(_gh(rows))
    assert len(out["dates"]) == 250
