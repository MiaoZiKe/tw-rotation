"""證交所季報是「年度累計數」、FinMind 是「單季數」，混在同一張表裡。

這支測試盯的是專家審查抓到的 P0：以前 ttm() 直接把四列相加，
走證交所那條路的股票 TTM EPS 被灌水、自算本益比系統性偏低約 20%。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import fundamental as F


def _twse(code, year, q, eps, rev=None, ni=None):
    """證交所路徑：累計數，沒有 announce_date。"""
    return {"code": code, "year": year, "quarter": q, "eps": eps,
            "revenue": rev, "net_income": ni, "announce_date": None}


def _finmind(code, year, q, eps, rev=None, ni=None):
    """FinMind 路徑：單季數，有 announce_date。"""
    return {"code": code, "year": year, "quarter": q, "eps": eps,
            "revenue": rev, "net_income": ni, "announce_date": f"{year}-05-15"}


def test_累計會被還原成單季():
    df = pd.DataFrame([_twse("A", 2026, 1, 1.22, 100, 10), _twse("A", 2026, 2, 2.42, 210, 21)])
    out = F._decumulate(df).set_index("quarter")
    assert out.loc[1, "eps"] == 1.22               # Q1 本來就是單季，不動
    assert round(float(out.loc[2, "eps"]), 4) == 1.20
    assert round(float(out.loc[2, "revenue"]), 4) == 110


def test_單季來源不可以被動到():
    df = pd.DataFrame([_finmind("B", 2026, 1, 13.0, 100), _finmind("B", 2026, 2, 14.0, 110)])
    out = F._decumulate(df).set_index("quarter")
    assert float(out.loc[2, "eps"]) == 14.0        # 不可以變成 1.0


def test_跨年度不會相減():
    df = pd.DataFrame([_twse("C", 2025, 4, 8.0), _twse("C", 2026, 1, 2.0)])
    out = F._decumulate(df)
    assert float(out[out["quarter"] == 1]["eps"].iloc[0]) == 2.0


def test_季別不連續就不減():
    """只有 Q1 和 Q3（缺 Q2）時不能拿 Q3 減 Q1，那樣是兩季合計不是一季。"""
    df = pd.DataFrame([_twse("D", 2026, 1, 1.0), _twse("D", 2026, 3, 3.6)])
    out = F._decumulate(df).set_index("quarter")
    assert float(out.loc[3, "eps"]) == 3.6


def test_ttm_用還原後的單季相加():
    rows = [_twse("E", 2025, 4, 8.0)]                       # 2025 全年累計 8.0
    rows += [_twse("E", 2026, q, v) for q, v in ((1, 1.0), (2, 2.2), (3, 3.6))]
    t = F.ttm(pd.DataFrame(rows)).set_index("code")
    # 單季還原後：2025Q4=8.0（前面沒有 Q3 可減，保留）、1.0、1.2、1.4 → 11.6
    assert round(float(t.loc["E", "ttm_eps"]), 4) == 11.6


def test_混合來源各走各的():
    rows = [_twse("F", 2026, 1, 1.0), _twse("F", 2026, 2, 2.2),
            _finmind("G", 2026, 1, 5.0), _finmind("G", 2026, 2, 6.0)]
    out = F._decumulate(pd.DataFrame(rows))
    f2 = float(out[(out["code"] == "F") & (out["quarter"] == 2)]["eps"].iloc[0])
    g2 = float(out[(out["code"] == "G") & (out["quarter"] == 2)]["eps"].iloc[0])
    assert round(f2, 4) == 1.2 and g2 == 6.0
