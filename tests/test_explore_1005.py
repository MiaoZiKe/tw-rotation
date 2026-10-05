"""選股探索頁（#explore）預先計算欄位的口徑測試 —— pipeline/compute/explore.py。

每一條都對應 docs/explore_page_spec.md「條件口徑」那張表的一列；改口徑要兩邊一起改。
"""
import math

import pandas as pd

from pipeline.compute import explore


def test_volatility_annualized_and_needs_enough_bars():
    # 每天 +1%、-1% 交替：日報酬標準差約 1%，年化約 1%×√252 ≈ 15.9%
    px = [100.0]
    for i in range(70):
        px.append(px[-1] * (1.01 if i % 2 == 0 else 0.99))
    v = explore.volatility(pd.Series(px))
    assert 15 < v < 17
    # 不足 61 根不算（新股不能被當成「不穩」）
    assert explore.volatility(pd.Series(px[:40])) is None


def test_pe_position_uses_own_history_and_skips_loss():
    hist = [{"pe": p} for p in [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]]
    pct, n = explore.pe_position(11, hist)
    assert n == 10 and pct == 10           # 只比 10 高 → 第 10 百分位（歷史低檔）
    pct, _ = explore.pe_position(30, hist)
    assert pct == 100
    # 虧損（沒有本益比）不給位置，不能被排成「最便宜」
    assert explore.pe_position(None, hist)[0] is None
    assert explore.pe_position(-5, hist)[0] is None
    # 歷史少於 8 季不給位置
    assert explore.pe_position(11, hist[:5])[0] is None
    # 歷史裡的虧損季（pe 空或 ≤0）不算一季
    assert explore.pe_position(11, hist[:7] + [{"pe": None}, {"pe": -3}])[0] is None


def test_dividend_streak_excludes_this_year_and_stops_on_gap():
    by = [{"year": y, "cash": 1.0} for y in range(2018, 2026)] + [{"year": 2026, "cash": 0.0}]
    assert explore.dividend_streak(by, 2026) == 8         # 2018～2025，今年還沒過完不算
    by[3]["cash"] = 0                                     # 2021 沒配 → 只數 2022～2025
    assert explore.dividend_streak(by, 2026) == 4
    assert explore.dividend_streak([], 2026) == 0
    # 去年沒有資料（不知道）＝不算連續
    assert explore.dividend_streak([{"year": 2023, "cash": 2}], 2026) == 0


def test_buy_streak_counts_until_today_only():
    df = pd.DataFrame({"date": [f"2026-09-{d:02d}" for d in range(1, 8)],
                       "inst_total": [5000, -1, 2000, 3000, 1000, 4000, 1000]})
    n, net10 = explore.buy_streak(df)
    assert n == 5
    assert net10 == round((5000 - 1 + 2000 + 3000 + 1000 + 4000 + 1000) / 1000)
    df.loc[6, "inst_total"] = -10                          # 今天賣超 → 連買歸零
    assert explore.buy_streak(df)[0] == 0
    assert explore.buy_streak(None) == (0, None)


def test_stock_row_order_matches_cols_and_is_json_safe():
    close = pd.Series([100 + i * 0.5 for i in range(80)])
    row = explore.stock_row("1234", close=close, ma20=close.tail(20).mean(), ma60=close.tail(60).mean(),
                            turnover=pd.Series([2e8] * 80), pe_now=15,
                            pe_hist=[{"pe": 10 + i} for i in range(12)],
                            dividends={"yield_ttm": 4.2, "by_year": [{"year": y, "cash": 1} for y in range(2019, 2026)]},
                            inst=None, this_year=2026)
    assert len(row) == len(explore.COLS)
    d = dict(zip(explore.COLS, row))
    assert d["code"] == "1234" and d["above20"] == 1 and d["above60"] == 1
    assert d["dy"] == 4.2 and d["div_years"] == 7 and d["tv20"] == 200.0
    assert d["ret60"] > 0
    for v in row:
        assert not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
    p = explore.payload([row], "2026-10-02")
    assert p["cols"] == explore.COLS and p["asof"] == "2026-10-02"
