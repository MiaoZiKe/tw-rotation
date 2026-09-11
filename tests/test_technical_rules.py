"""M3 規則引擎測試：區間性質、硬性排除、A/B 型態能否觸發、停損目標的合理性。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import indicators as ind  # noqa: E402
from pipeline.compute import technical as T  # noqa: E402


def _frame(close, vol=None, noise=0.004, seed=0):
    rng = np.random.default_rng(seed)
    c = np.asarray(close, dtype=float)
    n = len(c)
    h = c * (1 + np.abs(rng.normal(0, noise, n)))
    l = c * (1 - np.abs(rng.normal(0, noise, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum.reduce([h, c, o]); l = np.minimum.reduce([l, c, o])
    v = np.asarray(vol if vol is not None else np.full(n, 1e7), dtype=float)
    return pd.DataFrame({"date": pd.bdate_range("2025-01-01", periods=n).astype(str),
                         "open": o, "high": h, "low": l, "close": c, "volume": v})


def _random_walk(n=300, drift=0.001, seed=3):
    rng = np.random.default_rng(seed)
    return _frame(100 * np.exp(np.cumsum(rng.normal(drift, 0.014, n))),
                  vol=rng.integers(2e6, 4e7, n), seed=seed)


# ------------------------------------------------------------------ 區間

def test_zones_are_bounded_and_multi_source():
    for seed in (3, 7, 21, 33):
        df = ind.compute_all(_random_walk(seed=seed))
        atr = float(df["atr14"].iloc[-1])
        r = T.evaluate(df, avg_turnover=5e8)
        for z in r["demand"] + r["supply"]:
            assert z["high"] - z["low"] <= 2.0 * atr + 1e-6, "區間不得寬於 2×ATR"
            assert len(z["sources"]) >= 2, "單一來源的區間不該出現"
            assert z["score"] >= T.ZONE_MIN_SCORE
        close = float(df["close"].iloc[-1])
        # 區間可以跨越現價（價格在區間裡），分類看的是中點
        for z in r["demand"]:
            assert (z["low"] + z["high"]) / 2 <= close + 1e-9
        for z in r["supply"]:
            assert (z["low"] + z["high"]) / 2 > close - 1e-9


def test_nearest_zone_used_for_stop_and_target():
    df = ind.compute_all(_random_walk(seed=3))
    r = T.evaluate(df, avg_turnover=5e8)
    close = float(df["close"].iloc[-1])
    assert r["stop"] < close < r["tp1"]
    assert T.MIN_RISK_PCT - 1e-6 <= r["risk_pct"]
    if r["demand"]:
        # 停損必須落在「最近」需求區的下方，而不是更遠的那個
        assert r["stop"] <= r["demand"][0]["low"] + 1e-6
        assert r["demand"][0]["high"] >= max(z["high"] for z in r["demand"])


# ------------------------------------------------------------------ 硬性排除

def test_low_liquidity_is_excluded():
    df = ind.compute_all(_random_walk(seed=5))
    r = T.evaluate(df, avg_turnover=1e7)
    assert r["verdict"] == "不要碰"
    assert any("流動性" in x for x in r["reasons"])


def test_limit_up_is_excluded():
    c = np.full(200, 100.0)
    c[-1] = 110.0        # 最後一根漲停
    df = ind.compute_all(_frame(c))
    r = T.evaluate(df, avg_turnover=5e8)
    assert bool(df["limit_up"].iloc[-1])
    assert r["verdict"] == "不要碰"
    assert any("漲停" in x for x in r["reasons"])


def test_overheated_bias_is_excluded():
    c = np.r_[np.full(180, 100.0), np.linspace(100, 140, 20)]   # 20 天噴 40%
    df = ind.compute_all(_frame(c))
    r = T.evaluate(df, avg_turnover=5e8)
    assert r["signals"]["bias20"] > 15
    assert r["verdict"] == "不要碰"


# ------------------------------------------------------------------ B 級突破

def test_breakout_grade_b_can_trigger():
    """盤整 240 天後帶 3 倍量突破前高，乖離仍小 → 應判 B 或至少突破訊號全亮。"""
    rng = np.random.default_rng(9)
    base = 100 + np.cumsum(rng.normal(0, 0.6, 240))
    base = 100 + (base - base.mean()) * 0.6               # 約 ±8 的箱型
    top = base.max()
    up = np.linspace(base[-1], top * 1.015, 4)[1:]          # 3 天剛站上箱頂 +1.5%（剛突破，測量目標還在）
    c = np.r_[base, up]
    vol = np.r_[np.full(240, 1e7), np.full(3, 3.2e7)]
    df = ind.compute_all(_frame(c, vol=vol, noise=0.003, seed=9))
    r = T.evaluate(df, avg_turnover=5e8)
    s = r["signals"]
    assert s["vol_ratio"] >= 1.5
    assert s["bias20"] <= 8
    assert s["trend"] == 1 and s["bos_recent"], "突破後應為多頭結構且近 5 根有 BOS/CHoCH"
    assert r["grade"] == "B", f"預期 B 級，實得 {r['verdict']} / {r['reasons']}"
    assert r["rr"] >= 2.0


# ------------------------------------------------------------------ A 級回檔

def test_pullback_grade_a_can_trigger():
    """有波段的多頭趨勢 → 回檔但沒跌破上一個擺動低點 → 反彈。
    結構必須維持多頭（trend=1），判定絕不能是「不要碰」，且腳下要有需求區。"""
    legs = []
    px = 100.0
    for _ in range(8):                                   # 8 個波段：漲 8%、回 3%
        up = np.linspace(px, px * 1.08, 15)[1:]
        legs.append(up); px = up[-1]
        dn = np.linspace(px, px * 0.97, 6)[1:]
        legs.append(dn); px = dn[-1]
    c = np.concatenate(legs)
    # 最後一個回檔：回到前一個波段的高點附近（沒破上一個擺動低點），然後反彈 3 根
    last_pull = np.linspace(c[-1], c[-1] * 0.965, 8)[1:]
    bounce = last_pull[-1] * np.array([0.998, 1.003, 1.007])   # 剛開始反彈，還在區間內
    c = np.r_[c, last_pull, bounce]
    vol = np.r_[np.full(len(c) - 3, 1.2e7), np.full(3, 1.7e7)]
    df = ind.compute_all(_frame(c, vol=vol, noise=0.003, seed=4))
    r = T.evaluate(df, avg_turnover=5e8)
    assert r["verdict"] != "不要碰", r["reasons"]
    assert r["signals"]["trend"] == 1, "有波段的多頭趨勢、回檔沒破前低，結構應維持多頭"
    assert r["weekly"]["trend"] != -1        # 33 週的乾淨鋸齒可能還沒形成週線分形，0 是合理的
    assert r["demand"], "回檔到前波高點附近應該找得到需求區"
    assert r["signals"]["in_demand"], "價格應落在需求區內"
    assert r["grade"] == "A", f"預期 A 級，實得 {r['verdict']} / {r['reasons']}"
    assert r["stop"] < float(df["close"].iloc[-1]) < r["tp1"]


# ------------------------------------------------------------------ 文字

def test_text_never_leaks_raw_indicator_dump():
    df = ind.compute_all(_random_walk(seed=12))
    r = T.evaluate(df, avg_turnover=5e8)
    joined = " ".join(r["reasons"]) + (r["risk_text"] or "")
    assert "RSI=" not in joined and "osc=" not in joined
    assert r["verdict"] in ("可以分批進場（回檔承接）", "突破可追，但要控量", "觀望",
                            "觀望（逆勢反彈，只能短打）", "不要碰")
    assert 1 <= len(r["reasons"]) <= 3


def test_weekly_conflict_downgrades():
    """日線給 B、週線空頭 → 必須降為觀望且 tp2 = tp1。"""
    rng = np.random.default_rng(9)
    base = 100 + np.cumsum(rng.normal(0, 0.6, 240)); base = 100 + (base - base.mean()) * 0.6
    up = np.linspace(base[-1], base.max() * 1.015, 4)[1:]
    df = ind.compute_all(_frame(np.r_[base, up], vol=np.r_[np.full(240, 1e7), np.full(3, 3.2e7)],
                                noise=0.003, seed=9))
    r = T.evaluate(df, avg_turnover=5e8)
    if r["grade"] == "B":
        # 人為把週線改成空頭，重跑降級邏輯
        import pipeline.compute.technical as tech
        orig = tech.weekly_structure
        tech.weekly_structure = lambda d: {"trend": -1, "ma_align": -1, "weeks": 50}
        try:
            r2 = tech.evaluate(df, avg_turnover=5e8)
        finally:
            tech.weekly_structure = orig
        assert r2["grade"] is None and "逆勢" in r2["verdict"]
        assert r2["tp2"] == r2["tp1"]
