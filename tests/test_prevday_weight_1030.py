"""2026-10-30 Andy 拍板（「直接改上線」）：族群漲跌與大盤基準改用「前一日成交值」加權。

為什麼：當天成交值加權＝前視偏差。當天漲的股票自然爆量，用當天成交值加權等於
「事後知道誰漲再加重它」，每天系統性偏多（近 32 天日均 +0.371%，改前日權重 −0.045%，
加權指數 −0.042%；docs/research/20261030_rrg_audit.md B 節）。

這裡釘住的事：
1. 「當天放量大漲」的股票，它當天的成交值**不進**權重 —— 不管當天放量多大，結果都一樣。
2. 權重真的是前一日成交值（手算對得上）。
3. 第一天（沒有前一日）→ 該股當天剔除；全部都沒有前一日 → 族群 NaN／大盤持平 0。
4. 前一日成交值 0／缺值 → 權重 0，不炸、不除以零。
5. 族群成交值（turnover）仍是當天實際值，不受影響。
6. 空資料。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pipeline.compute import flow, rrg

D = ["2026-10-27", "2026-10-28", "2026-10-29"]
_MEM = pd.DataFrame([{"code": c, "group_id": "g", "group_name": "G", "tier": "standalone", "chain": "x"}
                     for c in ("1101", "2330")])


def _company():
    return pd.DataFrame([{"code": "1101", "industry": "水泥工業"}, {"code": "2330", "industry": "半導體業"}])


def _price(spike_tv: float):
    """1101：每天成交值 100、平盤。2330：前兩天成交值 100、平盤；第三天漲 10% 且成交值 = spike_tv（放量）。"""
    rows = []
    for i, d in enumerate(D):
        rows.append({"date": d, "code": "1101", "name": "A", "close": 100.0, "change": 0.0, "turnover": 100.0})
        if i < 2:
            rows.append({"date": d, "code": "2330", "name": "B", "close": 100.0, "change": 0.0, "turnover": 100.0})
        else:
            rows.append({"date": d, "code": "2330", "name": "B", "close": 110.0, "change": 10.0,
                         "turnover": spike_tv})
    return pd.DataFrame(rows)


@pytest.fixture
def mem(monkeypatch):
    monkeypatch.setattr(flow.loader, "membership", lambda *a, **k: _MEM)


def _gchg(gh, d):
    return float(gh[(gh["group_id"] == "g") & (gh["date"].astype(str) == d)]["chg_pct"].iloc[0])


# ---------------------------------------------------------------- 族群（flow.group_daily）
def test_group_spike_volume_not_used(mem):
    """放量 1 倍與放量 50 倍，族群漲跌一模一樣 —— 當天成交值完全沒進權重。"""
    a = flow.group_daily(_price(100.0), _company())
    b = flow.group_daily(_price(5000.0), _company())
    # 前一日兩檔都是 100 → 等權 → (0 + 10) / 2 = 5%
    assert _gchg(a, D[2]) == pytest.approx(5.0)
    assert _gchg(b, D[2]) == pytest.approx(5.0)
    # 舊口徑（當天權重）在放量 50 倍時會是 10×5000/5100 ≈ 9.8%，這裡確認沒有回到那個值
    assert _gchg(b, D[2]) < 9.0


def test_group_weight_is_prev_day_turnover(mem):
    """前一日 1101=300、2330=100 → 族群漲跌 = 10 × 100/400 = 2.5%。"""
    px = _price(9999.0)
    px.loc[(px["code"] == "1101") & (px["date"] == D[1]), "turnover"] = 300.0
    gh = flow.group_daily(px, _company())
    assert _gchg(gh, D[2]) == pytest.approx(2.5)


def test_group_turnover_is_still_same_day(mem):
    """族群成交值（資金量）仍用當天實際值：100 + 5000。"""
    gh = flow.group_daily(_price(5000.0), _company())
    row = gh[(gh["group_id"] == "g") & (gh["date"].astype(str) == D[2])].iloc[0]
    assert row["turnover"] == pytest.approx(5100.0)


def test_group_first_day_excluded(mem):
    """資料第一天沒有前一日成交值 → 兩檔都剔除 → 族群漲跌 NaN（不是 0，也不退回當天權重）。"""
    gh = flow.group_daily(_price(100.0), _company())
    assert math.isnan(_gchg(gh, D[0]))


def test_group_new_listing_excluded_on_first_day(mem):
    """2330 第三天才上市（新股第一天大漲 10%）：當天不進權重 → 族群漲跌 = 1101 的 0%。"""
    px = _price(5000.0)
    px = px[~((px["code"] == "2330") & (px["date"] < D[2]))]
    gh = flow.group_daily(px, _company())
    assert _gchg(gh, D[2]) == pytest.approx(0.0)


def test_group_prev_turnover_zero_or_nan(mem):
    """前一日成交值 0 或缺值 → 權重 0；兩檔都這樣 → NaN，不除以零。"""
    px = _price(5000.0)
    px.loc[(px["code"] == "1101") & (px["date"] == D[1]), "turnover"] = 0.0
    px.loc[(px["code"] == "2330") & (px["date"] == D[1]), "turnover"] = np.nan
    gh = flow.group_daily(px, _company())
    assert math.isnan(_gchg(gh, D[2]))


def test_group_duplicate_index_ok(mem):
    """輸入索引重複（多來源 concat）也不能錯位。"""
    px = pd.concat([_price(5000.0).iloc[:3], _price(5000.0).iloc[3:]])   # 索引 0..2、3..5 → 改成重複
    px.index = [0] * len(px)
    gh = flow.group_daily(px, _company())
    assert _gchg(gh, D[2]) == pytest.approx(5.0)


def test_group_empty():
    assert flow.group_daily(pd.DataFrame(), _company()).empty


# ---------------------------------------------------------------- 大盤（rrg.market_index）
def test_market_spike_volume_not_used():
    a = rrg.market_index(_price(100.0))
    b = rrg.market_index(_price(5000.0))
    # 第一天全部沒有前一日 → 0；第二天平盤 → 0；第三天等權 5%
    assert list(a.round(10)) == pytest.approx([1.0, 1.0, 1.05])
    assert list(b.round(10)) == pytest.approx([1.0, 1.0, 1.05])


def test_market_compound_and_prev_weight():
    """兩天連續上漲要複利連乘，權重逐日用前一天成交值。"""
    rows = []
    for d, c1, tv1, c2, tv2 in [(D[0], 100, 100, 100, 100), (D[1], 110, 300, 100, 100),
                                (D[2], 121, 50, 100, 9999)]:
        rows += [{"date": d, "code": "1101", "close": float(c1), "change": float(c1 - (c1 / 1.1 if d != D[0] else c1)),
                  "turnover": float(tv1)},
                 {"date": d, "code": "2330", "close": float(c2), "change": 0.0, "turnover": float(tv2)}]
    idx = rrg.market_index(pd.DataFrame(rows))
    # 第二天：10% × 100/200 = 5%；第三天：10% × 300/400 = 7.5% → 1.05 × 1.075
    assert float(idx.iloc[1]) == pytest.approx(1.05)
    assert float(idx.iloc[2]) == pytest.approx(1.05 * 1.075)


def test_market_index_is_date_string():
    idx = rrg.market_index(_price(100.0))
    assert all(isinstance(k, str) for k in idx.index)
