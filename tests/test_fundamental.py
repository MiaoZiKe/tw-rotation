"""M2 基本面的規則測試。

金融專家定的規則每一條都有對應測試：算錯的本益比比沒有本益比更危險，
因為它看起來很像對的。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.compute import fundamental as F  # noqa: E402
from pipeline.sources import finmind, news  # noqa: E402


def _fq(code, quarters, eps=None, rev=None):
    """quarters: [(year, q), ...]"""
    rows = []
    for i, (y, q) in enumerate(quarters):
        rows.append({"year": y, "quarter": q, "code": code,
                     "period_end": f"{y}-{q*3:02d}-30",
                     "announce_date": finmind.announce_date(y, q),
                     "revenue": (rev[i] if rev else 1000.0),
                     "gross_profit": 400.0, "operating_income": 300.0,
                     "net_income": 250.0, "eps": (eps[i] if eps else 2.0)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ TTM

def test_ttm_sums_four_consecutive_quarters():
    fq = _fq("2330", [(2025, 3), (2025, 4), (2026, 1), (2026, 2)], eps=[10, 11, 12, 13])
    t = F.ttm(fq)
    assert t.loc[0, "ttm_eps"] == 46
    assert t.loc[0, "ttm_complete"] is True or bool(t.loc[0, "ttm_complete"])
    assert t.loc[0, "latest_period"] == "2026Q2"


def test_ttm_refuses_incomplete_quarters():
    """只有三季就不給 TTM，不用三季湊、也不用單季×4。"""
    fq = _fq("2330", [(2025, 4), (2026, 1), (2026, 2)], eps=[11, 12, 13])
    t = F.ttm(fq)
    assert np.isnan(t.loc[0, "ttm_eps"])
    assert not bool(t.loc[0, "ttm_complete"])


def test_ttm_refuses_gap_in_quarters():
    """四季但中間缺一季（例如 2025Q4 沒抓到）也不算完整。"""
    fq = _fq("2330", [(2025, 2), (2025, 3), (2026, 1), (2026, 2)], eps=[9, 10, 12, 13])
    t = F.ttm(fq)
    assert np.isnan(t.loc[0, "ttm_eps"])


def test_ttm_uses_latest_four_when_more_exist():
    fq = _fq("2330", [(2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2026, 1)],
             eps=[1, 2, 3, 4, 5, 6])
    t = F.ttm(fq)
    assert t.loc[0, "ttm_eps"] == 3 + 4 + 5 + 6


# ------------------------------------------------------------------ 估值

def test_loss_making_stock_has_nan_pe():
    """虧損股 PE 必須是 NaN，不能是負數。"""
    px = pd.DataFrame({"code": ["A", "B"], "close": [100.0, 50.0]})
    ttm = pd.DataFrame({"code": ["A", "B"], "ttm_eps": [5.0, -2.0],
                        "ttm_revenue": [1e9, 1e9], "ttm_net_income": [1e8, -1e7],
                        "gross_margin": [40.0, 10.0], "latest_period": ["2026Q2"] * 2,
                        "ttm_complete": [True, True]})
    v = F.valuation(px, ttm)
    assert v.loc[v["code"] == "A", "pe"].iloc[0] == 20.0
    assert np.isnan(v.loc[v["code"] == "B", "pe"].iloc[0])
    assert bool(v.loc[v["code"] == "B", "is_loss"].iloc[0])


def test_pb_ps_roe_computed():
    px = pd.DataFrame({"code": ["A"], "close": [100.0]})
    ttm = pd.DataFrame({"code": ["A"], "ttm_eps": [5.0], "ttm_revenue": [2e9],
                        "ttm_net_income": [2e8], "gross_margin": [40.0],
                        "latest_period": ["2026Q2"], "ttm_complete": [True]})
    bal = pd.DataFrame({"code": ["A"], "shares": [1e7], "equity_parent": [1e9],
                        "bps": [100.0], "total_assets": [2e9]})
    v = F.valuation(px, ttm, bal)
    assert v.loc[0, "pb"] == 1.0
    assert v.loc[0, "market_cap"] == 1e9
    assert v.loc[0, "ps"] == 0.5
    assert v.loc[0, "roe"] == 20.0


@pytest.fixture()
def fake_groups(monkeypatch):
    """用假的族群表：tech 走 PE、bank 走 PB+ROE、tiny 只有兩檔。"""
    cfg = {
        "groups": {
            "tech": {"name": "科技", "codes": ["T1", "T2", "T3", "T4", "T5", "T6"]},
            "bank": {"name": "銀行", "valuation_metric": "pb_roe",
                     "codes": ["B1", "B2", "B3", "B4", "B5"]},
            "tiny": {"name": "小族群", "codes": ["S1", "S2"]},
        }
    }
    from pipeline.groups import loader
    monkeypatch.setattr(loader, "load", lambda path=None: cfg)
    return cfg


def _val_frame(codes, pe=None, pb=None, loss=None):
    n = len(codes)
    return pd.DataFrame({
        "code": codes,
        "close": [100.0] * n,
        "pe": pe if pe is not None else [np.nan] * n,
        "pb": pb if pb is not None else [np.nan] * n,
        "ps": [np.nan] * n,
        "is_loss": loss if loss is not None else [False] * n,
    })


def test_group_percentile_within_group_only(fake_groups):
    """分位只在自己族群內算：科技股不會跟銀行股比。"""
    val = _val_frame(["T1", "T2", "T3", "T4", "T5", "T6", "B1", "B2", "B3", "B4", "B5"],
                     pe=[10, 20, 30, 40, 50, 60, 8, 9, 10, 11, 12],
                     pb=[np.nan] * 6 + [0.8, 1.0, 1.2, 1.4, 1.6])
    g = F.group_valuation(val)
    t3 = g[(g["code"] == "T3")].iloc[0]
    assert t3["metric"] == "pe"
    assert t3["group_n"] == 6
    assert abs(t3["percentile"] - (2 / 6 * 100)) < 1e-9   # 兩檔比它便宜
    assert t3["group_median"] == 35.0

    b3 = g[(g["code"] == "B3")].iloc[0]
    assert b3["metric"] == "pb_roe"
    assert b3["metric_value"] == 1.2
    assert abs(b3["percentile"] - 40.0) < 1e-9


def test_outlier_pe_excluded_from_group_stats(fake_groups):
    """PE 300 的離群值不能把族群中位數拉歪，也不能參與分位計算。"""
    val = _val_frame(["T1", "T2", "T3", "T4", "T5", "T6"], pe=[10, 20, 30, 40, 50, 300])
    g = F.group_valuation(val)
    t1 = g[g["code"] == "T1"].iloc[0]
    assert t1["group_n"] == 5
    assert t1["group_median"] == 30.0
    t6 = g[g["code"] == "T6"].iloc[0]
    assert np.isnan(t6["metric_value"])     # 被視為離群，沒有分位


def test_loss_stocks_excluded_and_ratio_reported(fake_groups):
    val = _val_frame(["T1", "T2", "T3", "T4", "T5", "T6"],
                     pe=[10, 20, 30, np.nan, np.nan, np.nan],
                     loss=[False, False, False, True, True, True])
    g = F.group_valuation(val)
    t1 = g[g["code"] == "T1"].iloc[0]
    assert t1["group_n"] == 3
    assert abs(t1["group_loss_ratio"] - 50.0) < 1e-9


def test_thin_group_is_blank(fake_groups):
    """兩檔的族群不給分位、不給中位數。"""
    val = _val_frame(["S1", "S2"], pe=[10, 20])
    g = F.group_valuation(val)
    assert g["percentile"].isna().all()
    assert g["group_median"].isna().all()
    assert g["thin_sample"].all()


def test_median_not_mean(fake_groups):
    """一檔 PE 150（未超過 200 門檻）不能把族群估值拉到 40 以上 —— 要用中位數。"""
    val = _val_frame(["T1", "T2", "T3", "T4", "T5", "T6"], pe=[10, 12, 14, 16, 18, 150])
    g = F.group_valuation(val)
    assert g.iloc[0]["group_median"] == 15.0


# ------------------------------------------------------------------ 月營收

def _rev(code, start_year, months, values):
    rows = []
    y, m = start_year, 1
    for v in values:
        rows.append({"ym": f"{y}-{m:02d}", "code": code, "revenue": v})
        m += 1
        if m > 12:
            m = 1; y += 1
    return pd.DataFrame(rows)


def test_revenue_yoy_and_streak():
    base = [100] * 12
    grow = [120] * 12          # 每個月都 +20%
    r = F.revenue_momentum(_rev("A", 2025, 24, base + grow))
    row = r.iloc[0]
    assert abs(row["yoy"] - 20.0) < 1e-9
    assert row["growth_streak"] == 12
    assert row["ym"] == "2026-12"


def test_jan_feb_merged_yoy():
    """去年農曆年在 1 月、今年在 2 月：單月 YoY 會爆，合併後才是真的。"""
    y2025 = [150, 50] + [100] * 10     # 去年 1 月旺、2 月淡
    y2026 = [60, 160] + [110] * 10     # 今年反過來，但 1+2 合計 220 vs 200 = +10%
    r = F.revenue_momentum(_rev("A", 2025, 14, y2025 + y2026[:2]))
    row = r.iloc[0]
    assert row["ym"] == "2026-02"
    assert abs(row["yoy"] - 220.0) < 1e-9          # 單月看起來 +220%，誤導
    assert abs(row["yoy_adj"] - 10.0) < 1e-9       # 合併後 +10%，這才是真的
    assert row["yoy_note"] == "1-2 月合併"


def test_revenue_spike_flagged():
    vals = [100] * 12 + [100] * 11 + [250]
    r = F.revenue_momentum(_rev("A", 2025, 24, vals))
    assert bool(r.iloc[0]["flag_spike"])
    assert F.momentum_score(r.iloc[0]) < F.momentum_score(
        F.revenue_momentum(_rev("A", 2025, 24, [100] * 12 + [130] * 12)).iloc[0])


def test_revenue_mom_vs_typical_needs_history():
    r = F.revenue_momentum(_rev("A", 2026, 3, [100, 110, 120]))
    assert np.isnan(r.iloc[0]["mom_typical"])


# ------------------------------------------------------------------ 公告日

def test_announce_dates_are_conservative():
    assert finmind.announce_date(2026, 1) == "2026-05-15"
    assert finmind.announce_date(2026, 4) == "2027-03-31"       # Q4 是隔年
    assert finmind.revenue_announce_date("2026-01") == "2026-02-10"
    assert finmind.revenue_announce_date("2026-12") == "2027-01-10"


# ------------------------------------------------------------------ 券商目標價

def test_broker_target_extraction():
    n = pd.DataFrame([
        {"news_id": "n1", "title": "高盛調升台積電目標價至 1,500 元 重申買進", "summary": "",
         "codes": "2330", "date": "2026-09-10", "url": "u", "source": "cnyes"},
        {"news_id": "n2", "title": "外資看好 AI 需求", "summary": "喊出目標價 880 元",
         "codes": "3017,2382", "date": "2026-09-10", "url": "u", "source": "cnyes"},
        {"news_id": "n3", "title": "沒有目標價的新聞", "summary": "只是講講",
         "codes": "2330", "date": "2026-09-10", "url": "u", "source": "cnyes"},
        {"news_id": "n4", "title": "目標價 999 元", "summary": "",
         "codes": "", "date": "2026-09-10", "url": "u", "source": "cnyes"},   # 沒代號不抽
    ])
    bv = news.extract_broker_views(n)
    assert len(bv) == 2
    r1 = bv[bv["news_id"] == "n1"].iloc[0]
    assert r1["code"] == "2330" and r1["target_price"] == 1500.0
    assert r1["broker"] == "高盛" and r1["action"] == "調升" and r1["rating"] == "買進"
    r2 = bv[bv["news_id"] == "n2"].iloc[0]
    assert r2["code"] == "3017" and r2["target_price"] == 880.0 and r2["broker"] == "外資"
