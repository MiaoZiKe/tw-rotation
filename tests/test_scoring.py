"""候選名單四面向評分（scoring.py）的測試。

重點不是分數的絕對值 —— 權重本來就是起始假設 —— 而是：
- 資料不足時回 None 而不是硬湊 50 分
- 理由一定帶得出實際數字
- 綜合分在某面向缺資料時會把權重讓給其他面向
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.compute import scoring


def _ind(n: int = 120, *, close: float = 100.0) -> pd.DataFrame:
    """做一段合成的指標表，欄位對齊 indicators.compute_all 的輸出。"""
    idx = pd.date_range("2025-01-01", periods=n, freq="B").strftime("%Y-%m-%d")
    px = np.linspace(close * 0.8, close, n)
    return pd.DataFrame({
        "date": idx, "open": px, "high": px * 1.01, "low": px * 0.99, "close": px,
        "volume": np.full(n, 5_000_000.0),
        "ma20": px * 0.97, "ma60": px * 0.94, "ma_align": 1,
        "rsi14": 58.0, "k": 45.0, "d": 40.0, "osc": 0.4, "trend": 1,
        "bias20": 3.0, "vol_ratio": 1.8, "atr14": px * 0.02,
        "sweep_low": False, "sweep_high": False, "bos": False, "choch": False,
        "limit_up": False,
    })


def _verdict(grade="A", rr=2.4):
    return {"grade": grade, "verdict": "可以分批進場（回檔承接）", "reasons": ["測試理由"],
            "stop": 92.0, "tp1": 115.0, "rr": rr}


def _inst(days: int = 30, *, trust: float = 500_000, foreign: float = 800_000):
    return pd.DataFrame({
        "date": pd.date_range("2025-06-02", periods=days, freq="B").strftime("%Y-%m-%d"),
        "code": "2330", "trust": np.full(days, trust),
        "foreign_total": np.full(days, foreign), "dealer": np.zeros(days),
    })


# ------------------------------------------------------------------ 技術面

def test_tech_score_a_grade_beats_watchlist():
    ind = _ind()
    last = ind.iloc[-1]
    a, _, _ = scoring.tech_score(last, ind, _verdict("A"), base=70)
    w, _, _ = scoring.tech_score(last, ind, _verdict(None), base=70)
    assert a > w


def test_tech_score_excluded_gets_penalised_and_explains_why():
    ind = _ind()
    v = {"grade": None, "verdict": "不要碰", "stop": 90.0, "tp1": 110.0, "rr": 1.0,
         "reasons": ["日均成交值不到 3,000 萬，流動性不足、出不掉"]}
    s, pros, cons = scoring.tech_score(ind.iloc[-1], ind, v, base=60)
    assert s < 50
    assert any("流動性" in c for c in cons)


def test_tech_score_stays_in_range():
    ind = _ind()
    for base in (0, 25, 50, 75, 100):
        for grade in ("A", "B", None):
            s, _, _ = scoring.tech_score(ind.iloc[-1], ind, _verdict(grade), base=base)
            assert 0 <= s <= 100


def test_tech_reason_mentions_real_numbers():
    ind = _ind()
    _, pros, _ = scoring.tech_score(ind.iloc[-1], ind, _verdict("A", rr=2.4), base=75)
    assert any("2.4" in p for p in pros), pros


# ------------------------------------------------------------------ 籌碼面

def test_chip_score_none_when_no_inst_data():
    s, pros, cons = scoring.chip_score(None, None, None, 1e8, 100.0)
    assert s is None and pros == [] and cons == []
    s2, _, _ = scoring.chip_score(pd.DataFrame(), None, None, 1e8, 100.0)
    assert s2 is None


def test_chip_score_rewards_continuous_buying():
    buy = scoring.chip_score(_inst(), None, None, 5e8, 100.0)[0]
    sell = scoring.chip_score(_inst(trust=-500_000, foreign=-800_000), None, None, 5e8, 100.0)[0]
    assert buy > sell


def test_chip_reason_reports_streak_and_lots():
    _, pros, _ = scoring.chip_score(_inst(), None, None, 5e8, 100.0)
    assert any("投信連買" in p and "張" in p for p in pros), pros


def test_chip_score_uses_holder_change():
    up = [{"date": f"2025-0{i}", "pct": 40 + i * 0.4} for i in range(1, 7)]
    down = [{"date": f"2025-0{i}", "pct": 45 - i * 0.4} for i in range(1, 7)]
    a = scoring.chip_score(_inst(), up, None, 5e8, 100.0)[0]
    b = scoring.chip_score(_inst(), down, None, 5e8, 100.0)[0]
    assert a > b


def test_chip_score_stays_in_range():
    for t in (-5e6, 0, 5e6):
        s, _, _ = scoring.chip_score(_inst(trust=t, foreign=t), None, None, 1e7, 100.0)
        assert 0 <= s <= 100


# ------------------------------------------------------------------ 基本面

def test_fund_score_none_when_nothing_to_go_on():
    assert scoring.fund_score(None)[0] is None
    assert scoring.fund_score({})[0] is None
    # 只有一個欄位也不給分（have < 2）
    assert scoring.fund_score({"roe": 12})[0] is None


def test_fund_score_growth_beats_shrink():
    good = {"rev_yoy": 35, "rev_streak": 6, "rev_yoy_3m": 28, "momentum_score": 80,
            "percentile": 25, "roe": 18, "group_n": 12, "metric": "pe", "rev_ym": "2026-08"}
    bad = {"rev_yoy": -22, "rev_streak": 0, "rev_yoy_3m": -18, "momentum_score": 20,
           "percentile": 88, "roe": 3, "group_n": 12, "metric": "pe", "rev_ym": "2026-08"}
    assert scoring.fund_score(good)[0] > scoring.fund_score(bad)[0]


def test_fund_reason_quotes_yoy_and_percentile():
    fx = {"rev_yoy": 35, "rev_streak": 6, "percentile": 20, "group_n": 12,
          "metric": "pe", "rev_ym": "2026-08", "momentum_score": 70}
    _, pros, _ = scoring.fund_score(fx)
    assert any("+35%" in p for p in pros), pros
    assert any("本益比" in p and "20" in p for p in pros), pros


def test_fund_score_flags_spike_as_caution_not_bonus():
    fx = {"rev_yoy": 180, "rev_flag_spike": True, "momentum_score": 60, "percentile": 40}
    _, _, cons = scoring.fund_score(fx)
    assert any("併購" in c or "一次性" in c for c in cons), cons


def test_fund_score_punishes_loss():
    base = {"rev_yoy": 5, "momentum_score": 50, "percentile": 50}
    assert scoring.fund_score(base)[0] > scoring.fund_score(dict(base, is_loss=True))[0]


# ------------------------------------------------------------------ 綜合

def test_blend_redistributes_missing_weight():
    assert scoring.blend(None, None, None) is None
    # 只有技術面 → 綜合 = 技術
    assert scoring.blend(80, None, None) == 80
    # 技術 80、籌碼 60，基本面缺 → 落在兩者之間，且偏向權重大的技術
    v = scoring.blend(80, 60, None)
    assert 60 < v < 80 and v > 70


def test_evaluate_returns_all_four_scores_and_reasons():
    ind = _ind()
    fx = {"rev_yoy": 30, "rev_streak": 5, "percentile": 22, "group_n": 10,
          "metric": "pe", "rev_ym": "2026-08", "momentum_score": 75, "roe": 16}
    out = scoring.evaluate(last=ind.iloc[-1], ind=ind, verdict=_verdict("A"), base_tech=72,
                           inst=_inst(), holders=None, broker=None, fx=fx, avg_turnover=5e8)
    for k in ("score_all", "score_chip", "score_tech", "score_fund"):
        assert out[k] is not None and 0 <= out[k] <= 100
    for facet in ("all", "chip", "tech", "fund"):
        assert facet in out["why"]
        assert isinstance(out["why"][facet]["pros"], list)
    assert out["why"]["all"]["pros"], "綜合面向一定要說得出至少一條理由"


def test_evaluate_survives_completely_missing_side_data():
    ind = _ind()
    out = scoring.evaluate(last=ind.iloc[-1], ind=ind, verdict=_verdict(None), base_tech=50,
                           inst=None, holders=None, broker=None, fx=None, avg_turnover=None)
    assert out["score_tech"] is not None
    assert out["score_chip"] is None and out["score_fund"] is None
    assert out["score_all"] == out["score_tech"]
    assert out["why"]["all"]["pros"], "沒有籌碼與基本面資料時，理由要退回技術面"


@pytest.mark.parametrize("facet", scoring.FACETS)
def test_facet_labels_are_chinese(facet):
    assert scoring.FACET_LABEL[facet]
