"""指標庫驗證。

策略有兩層：
1. 對照公開的已知答案（Wilder RSI 的經典 33 筆測試序列）
2. 對照「一看就對」的樸素迴圈版實作 —— 向量化版本必須逐筆吻合

第二層才是真正防呆的部分：向量化寫法出錯時往往不會噴例外，只會安靜地
給出偏掉幾個百分點的數字，那種錯誤在盤面上看不出來。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import indicators as ind  # noqa: E402

# Wilder / StockCharts 的標準 RSI 測試序列
WILDER_CLOSE = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
    45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
    46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57,
    43.42, 42.66, 43.13,
]
# 由 Wilder 定義逐筆手算而得（見 test_rsi_matches_naive_wilder_loop 的參考實作）。
# 註：網路上流傳的對照表多半四捨五入到小數兩位後再遞迴，
# 從第 9 個值起會累積出 0.05 上下的偏差 —— 那是表格的誤差，不是公式的。
WILDER_RSI14_EXPECTED = [
    70.4641, 66.2496, 66.4809, 69.3469, 66.2947, 57.9150, 62.8807, 63.2088,
    56.0116, 62.3399, 54.6710, 50.3868, 40.0194, 41.4926, 41.9024, 45.4995,
    37.3228, 33.0905, 37.7888,
]


def _sample_ohlc(n: int = 260, seed: int = 42) -> pd.DataFrame:
    """合成一段有趨勢也有回檔的 OHLC，用來測結構類指標。"""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0015, 0.018, n)
    close = 100 * np.exp(np.cumsum(steps))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.003, n))
    high = np.maximum.reduce([high, close, open_])
    low = np.minimum.reduce([low, close, open_])
    return pd.DataFrame({
        "date": pd.bdate_range("2024-01-01", periods=n).astype(str),
        "open": open_, "high": high, "low": low, "close": close,
    })


# ------------------------------------------------------------------ RSI

def test_rsi_matches_published_values():
    s = pd.Series(WILDER_CLOSE)
    got = ind.rsi(s, 14).dropna().round(4).tolist()
    assert len(got) == len(WILDER_RSI14_EXPECTED), \
        f"RSI 應有 {len(WILDER_RSI14_EXPECTED)} 個值，實得 {len(got)}"
    for i, (g, e) in enumerate(zip(got, WILDER_RSI14_EXPECTED)):
        assert abs(g - e) <= 0.0001, f"第 {i} 個 RSI：預期 {e}，實得 {g}"


def test_rsi_matches_naive_wilder_loop():
    """對照 Wilder 原始定義的逐筆迴圈實作 —— 這是 RSI 正確性的真正依據。

    種子 = 前 14 筆變動的簡單平均，之後 avg = (avg*13 + 本筆) / 14。
    這也是 Pine Script ta.rma 的規則，所以算出來會跟 TradingView 對得起來。
    """
    c = np.array(WILDER_CLOSE)
    n = 14
    d = np.diff(c)
    gains, losses = np.clip(d, 0, None), np.clip(-d, 0, None)
    ag, al = gains[:n].mean(), losses[:n].mean()
    ref = [100 - 100 / (1 + ag / al)]
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        ref.append(100 - 100 / (1 + ag / al))

    got = ind.rsi(pd.Series(WILDER_CLOSE), n).dropna().to_numpy()
    assert np.allclose(got, np.array(ref), atol=1e-10)


def test_rsi_first_value_position():
    """RSI(14) 的第一個值必須落在第 15 根（index 14），早一根或晚一根都是錯的。"""
    s = pd.Series(WILDER_CLOSE)
    r = ind.rsi(s, 14)
    assert r.iloc[:14].isna().all(), "index 14 之前不該有 RSI 值"
    assert not np.isnan(r.iloc[14]), "index 14 應該要有 RSI 值"


def test_rsi_bounds():
    df = _sample_ohlc()
    r = ind.rsi(df["close"], 14).dropna()
    assert r.between(0, 100).all(), "RSI 必須落在 0–100"


# ------------------------------------------------------------------ Wilder RMA

def test_wilder_rma_seed_is_sma():
    s = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8])
    rma = ind.wilder_rma(s, 4)
    assert abs(rma.iloc[3] - 2.5) < 1e-12, "種子必須是前 4 筆的簡單平均 2.5"
    expected = (2.5 * 3 + 5.0) / 4
    assert abs(rma.iloc[4] - expected) < 1e-12


# ------------------------------------------------------------------ MACD

def test_macd_against_naive_loop():
    df = _sample_ohlc()
    c = df["close"].to_numpy()

    def naive_ema(arr, span):
        a = 2 / (span + 1)
        out = np.empty(len(arr))
        out[0] = arr[0]
        for i in range(1, len(arr)):
            out[i] = a * arr[i] + (1 - a) * out[i - 1]
        return out

    dif_ref = naive_ema(c, 12) - naive_ema(c, 26)
    macd_ref = naive_ema(dif_ref, 9)

    got = ind.macd(df["close"])
    assert np.allclose(got["dif"].to_numpy(), dif_ref, atol=1e-9)
    assert np.allclose(got["macd"].to_numpy(), macd_ref, atol=1e-9)
    assert np.allclose(got["osc"].to_numpy(), dif_ref - macd_ref, atol=1e-9)


# ------------------------------------------------------------------ KD

def test_kd_against_naive_loop():
    df = _sample_ohlc()
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    n = 9
    k_ref, d_ref = [], []
    k_prev = d_prev = 50.0
    for i in range(len(c)):
        if i < n - 1:
            k_ref.append(np.nan)
            d_ref.append(np.nan)
            continue
        hh, ll = h[i - n + 1:i + 1].max(), l[i - n + 1:i + 1].min()
        rsv = 50.0 if hh == ll else (c[i] - ll) / (hh - ll) * 100
        k_prev = k_prev * 2 / 3 + rsv / 3
        d_prev = d_prev * 2 / 3 + k_prev / 3
        k_ref.append(k_prev)
        d_ref.append(d_prev)

    got = ind.kd(df["high"], df["low"], df["close"])
    assert np.allclose(got["k"].to_numpy(), np.array(k_ref), atol=1e-9, equal_nan=True)
    assert np.allclose(got["d"].to_numpy(), np.array(d_ref), atol=1e-9, equal_nan=True)


def test_kd_bounds_and_start():
    df = _sample_ohlc()
    res = ind.kd(df["high"], df["low"], df["close"])
    assert res["k"].iloc[:8].isna().all(), "KD(9) 前 8 根不該有值"
    assert not np.isnan(res["k"].iloc[8])
    valid = res.dropna()
    assert valid["k"].between(0, 100).all() and valid["d"].between(0, 100).all()


def test_kd_flat_market_uses_50():
    """一路平盤時 H==L，RSV 沒有定義，必須用 50 而不是除以零。"""
    flat = pd.Series([100.0] * 30)
    res = ind.kd(flat, flat, flat)
    v = res.dropna()
    assert np.allclose(v["rsv"], 50.0)
    assert np.allclose(v["k"], 50.0)


# ------------------------------------------------------------------ 均線

def test_ma_alignment():
    up = pd.Series(np.linspace(100, 300, 200))
    assert ind.ma_alignment(up).iloc[-1] == 1, "單調上漲應為多頭排列"
    down = pd.Series(np.linspace(300, 100, 200))
    assert ind.ma_alignment(down).iloc[-1] == -1, "單調下跌應為空頭排列"


def test_ma_needs_full_window():
    s = pd.Series(np.linspace(100, 200, 100))
    assert ind.sma(s, 60).iloc[:59].isna().all(), "均線在資料不足時必須是 NaN"


# ------------------------------------------------------------------ SMC

def test_swing_points_on_known_shape():
    """人工造一個明確的 M 頭，擺動點必須落在該落的位置。"""
    high = pd.Series([1, 2, 5, 2, 1, 2, 6, 2, 1.0])
    low = pd.Series([1, 2, 5, 2, 1, 2, 6, 2, 1.0])
    sw = ind.swing_points(high, low, lookback=2)
    assert bool(sw["swing_high"].iloc[2]), "index 2 應為擺動高點"
    assert bool(sw["swing_high"].iloc[6]), "index 6 應為擺動高點"
    assert bool(sw["swing_low"].iloc[4]), "index 4 應為擺動低點"


def test_fvg_detection():
    """第 1 根高點 10、第 3 根低點 12 -> 中間留下 10–12 的多方缺口。"""
    high = pd.Series([10.0, 14.0, 15.0])
    low = pd.Series([8.0, 11.0, 12.0])
    fvg = ind.fair_value_gaps(high, low)
    assert bool(fvg["fvg_bull"].iloc[2])
    assert fvg["fvg_bottom"].iloc[2] == 10.0
    assert fvg["fvg_top"].iloc[2] == 12.0
    assert not fvg["fvg_bull"].iloc[:2].any(), "缺口只能標在第 3 根"


def test_market_structure_runs_and_flags():
    df = _sample_ohlc()
    ms = ind.market_structure(df["high"], df["low"], df["close"])
    assert set(ms["trend"].unique()) <= {-1, 0, 1}
    assert ms["bos"].any() or ms["choch"].any(), "260 根資料裡應該要有結構事件"
    # BOS 與 CHoCH 在同一根上互斥
    assert not (ms["bos"] & ms["choch"]).any()


def test_liquidity_sweep():
    """盤中破前高但收盤收回，應標記為上方流動性掃蕩。"""
    n = 25
    high = pd.Series([10.0] * (n - 1) + [12.0])
    low = pd.Series([9.0] * n)
    close = pd.Series([9.5] * n)
    sw = ind.liquidity_sweep(high, low, close, lookback=20)
    assert bool(sw["sweep_high"].iloc[-1])


# ------------------------------------------------------------------ 整合

def test_compute_all_shape_and_score():
    df = _sample_ohlc()
    out = ind.compute_all(df)
    for col in ("ma20", "dif", "osc", "k", "d", "rsi14", "trend",
                "fvg_bull", "ob_bull", "sweep_high", "ma_align", "bias20"):
        assert col in out.columns, f"缺少欄位 {col}"
    assert len(out) == len(df), "指標計算不應改變列數"

    score = ind.technical_score(out.iloc[-1])
    assert 0 <= score <= 100


def test_compute_all_rejects_missing_columns():
    bad = pd.DataFrame({"close": [1, 2, 3]})
    try:
        ind.compute_all(bad)
    except ValueError as exc:
        assert "缺少必要欄位" in str(exc)
    else:
        raise AssertionError("欄位不全時應該要拋出 ValueError")


def test_no_lookahead_in_moving_averages():
    """截斷資料後，已算過的歷史值必須完全不變 —— 有前視偏差就會在這裡爆。"""
    df = _sample_ohlc()
    full = ind.compute_all(df)
    truncated = ind.compute_all(df.iloc[:200].copy())
    for col in ("ma20", "ma60", "dif", "osc", "rsi14", "k", "d"):
        a = full[col].iloc[:200].to_numpy()
        b = truncated[col].to_numpy()
        assert np.allclose(a, b, atol=1e-9, equal_nan=True), f"{col} 有前視偏差"
