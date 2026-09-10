"""技術指標庫。

刻意不依賴 TA-Lib —— 它需要編譯 C 函式庫，在 GitHub Actions 上安裝很脆弱。
全部用 pandas/numpy 自己算，並附上單元測試對照已知值。

台股慣例的細節（跟很多國外套件的預設不同，弄錯會與看盤軟體對不起來）：
- KD 用 9 日 RSV，K 與 D 都是 1/3 平滑（等同 α=1/3 的 EMA），初始值 50
- RSI 用 Wilder 平滑（α=1/n），不是簡單移動平均
- MACD 慣稱 DIF / MACD / OSC，其中 OSC 才是柱狀體
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --------------------------------------------------------------- 移動平均

MA_PERIODS = (5, 10, 20, 60, 120, 240)


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def moving_averages(close: pd.Series, periods=MA_PERIODS) -> pd.DataFrame:
    return pd.DataFrame({f"ma{p}": sma(close, p) for p in periods}, index=close.index)


def ma_alignment(close: pd.Series, periods=(5, 20, 60, 120)) -> pd.Series:
    """均線多頭排列判定：+1 完全多頭、-1 完全空頭、0 糾結。"""
    mas = pd.DataFrame({p: sma(close, p) for p in periods})
    bull = pd.Series(True, index=close.index)
    bear = pd.Series(True, index=close.index)
    ordered = sorted(periods)
    for a, b in zip(ordered[:-1], ordered[1:]):
        bull &= mas[a] > mas[b]
        bear &= mas[a] < mas[b]
    out = pd.Series(0, index=close.index, dtype="int8")
    out[bull.fillna(False)] = 1
    out[bear.fillna(False)] = -1
    out[mas.isna().any(axis=1)] = 0
    return out


def bias(close: pd.Series, period: int = 20) -> pd.Series:
    """乖離率 %。判斷是否漲過頭、跌過深。"""
    m = sma(close, period)
    return (close - m) / m * 100


# --------------------------------------------------------------- MACD

def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    dif = ema(close, fast) - ema(close, slow)
    macd_line = ema(dif, signal)
    return pd.DataFrame({
        "dif": dif,
        "macd": macd_line,
        "osc": dif - macd_line,
    }, index=close.index)


# --------------------------------------------------------------- RSI

def wilder_rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder 平滑（Pine Script 的 ta.rma）。

    關鍵細節：第一個值是前 period 筆的簡單平均，之後才遞迴。
    直接用 ewm(adjust=False) 會以第一筆當種子，算出來的數字與看盤軟體對不起來。
    """
    arr = series.to_numpy(dtype="float64")
    n = len(arr)
    out = np.full(n, np.nan)
    if n < period:
        return pd.Series(out, index=series.index)
    seed = np.nanmean(arr[:period])
    out[period - 1] = seed
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + arr[i]) / period
    return pd.Series(out, index=series.index)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI，與 TradingView 的 ta.rsi 同一套種子規則。"""
    delta = close.diff()
    gain = delta.clip(lower=0).iloc[1:]
    loss = (-delta).clip(lower=0).iloc[1:]
    avg_gain = wilder_rma(gain, period).reindex(close.index)
    avg_loss = wilder_rma(loss, period).reindex(close.index)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # 全期間都在漲（avg_loss 為 0）時 RSI 定義為 100
    out = out.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    out = out.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
    return out


# --------------------------------------------------------------- KD

def kd(high: pd.Series, low: pd.Series, close: pd.Series,
       n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
    """台股慣用的 KD（9,3,3）。

    RSV = (C - L_n) / (H_n - L_n) * 100
    K   = K_prev * (1 - 1/k_smooth) + RSV * (1/k_smooth)
    D   = D_prev * (1 - 1/d_smooth) + K   * (1/d_smooth)
    初始 K = D = 50，與國內看盤軟體一致。
    """
    ln = low.rolling(n, min_periods=n).min()
    hn = high.rolling(n, min_periods=n).max()
    span = (hn - ln).to_numpy()
    # 平盤時 H==L，RSV 沒有定義，台股慣例用 50；先換掉分母再除，避免除零警告
    safe_span = np.where(span == 0, np.nan, span)
    rsv = (close.to_numpy() - ln.to_numpy()) / safe_span * 100
    rsv = np.where(span == 0, 50.0, rsv)
    rsv = pd.Series(rsv, index=close.index).where(hn.notna())

    ka, da = 1.0 / k_smooth, 1.0 / d_smooth
    k_vals = np.full(len(close), np.nan)
    d_vals = np.full(len(close), np.nan)
    k_prev = d_prev = 50.0
    started = False

    rsv_arr = rsv.to_numpy()
    for i in range(len(close)):
        if np.isnan(rsv_arr[i]):
            continue
        if not started:
            k_prev = d_prev = 50.0
            started = True
        k_prev = k_prev * (1 - ka) + rsv_arr[i] * ka
        d_prev = d_prev * (1 - da) + k_prev * da
        k_vals[i] = k_prev
        d_vals[i] = d_prev

    return pd.DataFrame({"rsv": rsv, "k": k_vals, "d": d_vals}, index=close.index)


# --------------------------------------------------------------- SMC

def swing_points(high: pd.Series, low: pd.Series, lookback: int = 2) -> pd.DataFrame:
    """分形擺動高低點：某根 K 的高點高於左右各 lookback 根 -> 擺動高點。

    lookback=2 對應常見的 5 根分形。這是後面所有 SMC 結構判定的地基。
    """
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    h = high.to_numpy()
    l = low.to_numpy()
    for i in range(lookback, n - lookback):
        window_h = h[i - lookback:i + lookback + 1]
        window_l = l[i - lookback:i + lookback + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            sh[i] = True
        if l[i] == window_l.min() and (window_l == l[i]).sum() == 1:
            sl[i] = True
    return pd.DataFrame({"swing_high": sh, "swing_low": sl}, index=high.index)


def market_structure(high: pd.Series, low: pd.Series, close: pd.Series,
                     lookback: int = 2) -> pd.DataFrame:
    """BOS / CHoCH 結構判定。

    BOS   (Break of Structure)     順著既有趨勢突破前一個擺動點 -> 趨勢延續
    CHoCH (Change of Character)    逆著既有趨勢跌破/突破 -> 趨勢可能反轉

    輸出 trend 欄位：1 多頭結構、-1 空頭結構、0 尚未定義。
    """
    sw = swing_points(high, low, lookback)
    n = len(close)
    c = close.to_numpy()

    trend = np.zeros(n, dtype="int8")
    bos = np.zeros(n, dtype=bool)
    choch = np.zeros(n, dtype=bool)

    last_sh: float | None = None   # 最近一個已確認的擺動高點
    last_sl: float | None = None
    cur_trend = 0

    sh_arr = sw["swing_high"].to_numpy()
    sl_arr = sw["swing_low"].to_numpy()
    h = high.to_numpy()
    l = low.to_numpy()

    for i in range(n):
        # 擺動點要等右側 lookback 根走完才算確認，所以延遲 lookback 根才納入
        j = i - lookback
        if j >= 0:
            if sh_arr[j]:
                last_sh = h[j]
            if sl_arr[j]:
                last_sl = l[j]

        if last_sh is not None and c[i] > last_sh:
            if cur_trend == -1:
                choch[i] = True
            elif cur_trend == 1:
                bos[i] = True
            cur_trend = 1
            last_sh = None          # 已被突破，等待新的擺動高點
        elif last_sl is not None and c[i] < last_sl:
            if cur_trend == 1:
                choch[i] = True
            elif cur_trend == -1:
                bos[i] = True
            cur_trend = -1
            last_sl = None

        trend[i] = cur_trend

    return pd.DataFrame({
        "trend": trend, "bos": bos, "choch": choch,
        "swing_high": sw["swing_high"], "swing_low": sw["swing_low"],
    }, index=close.index)


def fair_value_gaps(high: pd.Series, low: pd.Series,
                    min_gap_pct: float = 0.0) -> pd.DataFrame:
    """公允價值缺口（FVG）：三根 K 之間留下的未成交區間。

    多方 FVG：第 1 根的高點 < 第 3 根的低點（中間那根急拉留下缺口）
    空方 FVG：第 1 根的低點 > 第 3 根的高點

    缺口標記在第 3 根上，因為那時才確認成立。
    """
    h, l = high.to_numpy(), low.to_numpy()
    n = len(h)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    top = np.full(n, np.nan)
    bottom = np.full(n, np.nan)

    for i in range(2, n):
        h1, l1 = h[i - 2], l[i - 2]
        h3, l3 = h[i], l[i]
        ref = max(l1, 1e-9)
        if l3 > h1 and (l3 - h1) / ref * 100 >= min_gap_pct:
            bull[i] = True
            bottom[i], top[i] = h1, l3
        elif l1 > h3 and (l1 - h3) / ref * 100 >= min_gap_pct:
            bear[i] = True
            bottom[i], top[i] = h3, l1

    return pd.DataFrame({
        "fvg_bull": bull, "fvg_bear": bear,
        "fvg_bottom": bottom, "fvg_top": top,
    }, index=high.index)


def order_blocks(open_: pd.Series, high: pd.Series, low: pd.Series,
                 close: pd.Series, lookback: int = 2) -> pd.DataFrame:
    """Order Block：造成結構突破之前的最後一根反向 K 棒。

    多方 OB = BOS/CHoCH 向上之前的最後一根黑 K
    空方 OB = 向下突破之前的最後一根紅 K
    """
    ms = market_structure(high, low, close, lookback)
    o, c = open_.to_numpy(), close.to_numpy()
    h, l = high.to_numpy(), low.to_numpy()
    n = len(c)

    ob_bull = np.zeros(n, dtype=bool)
    ob_bear = np.zeros(n, dtype=bool)
    ob_top = np.full(n, np.nan)
    ob_bottom = np.full(n, np.nan)

    breaks_up = (ms["bos"].to_numpy() | ms["choch"].to_numpy()) & (ms["trend"].to_numpy() == 1)
    breaks_dn = (ms["bos"].to_numpy() | ms["choch"].to_numpy()) & (ms["trend"].to_numpy() == -1)

    for i in range(n):
        if breaks_up[i]:
            for j in range(i - 1, max(-1, i - 21), -1):
                if c[j] < o[j]:                     # 最後一根黑 K
                    ob_bull[j] = True
                    ob_bottom[j], ob_top[j] = l[j], h[j]
                    break
        elif breaks_dn[i]:
            for j in range(i - 1, max(-1, i - 21), -1):
                if c[j] > o[j]:                     # 最後一根紅 K
                    ob_bear[j] = True
                    ob_bottom[j], ob_top[j] = l[j], h[j]
                    break

    return pd.DataFrame({
        "ob_bull": ob_bull, "ob_bear": ob_bear,
        "ob_top": ob_top, "ob_bottom": ob_bottom,
    }, index=close.index)


def liquidity_sweep(high: pd.Series, low: pd.Series, close: pd.Series,
                    lookback: int = 20) -> pd.DataFrame:
    """流動性掃蕩：盤中破前高/前低但收盤收回來，典型的假突破誘多誘空。"""
    prev_high = high.rolling(lookback, min_periods=lookback).max().shift(1)
    prev_low = low.rolling(lookback, min_periods=lookback).min().shift(1)
    return pd.DataFrame({
        "sweep_high": (high > prev_high) & (close < prev_high),
        "sweep_low": (low < prev_low) & (close > prev_low),
    }, index=close.index).fillna(False)


# --------------------------------------------------------------- 整合

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """輸入含 open/high/low/close 的個股日 K（依日期排序），輸出全部指標。"""
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要欄位：{sorted(missing)}")

    df = df.sort_values("date").reset_index(drop=True) if "date" in df.columns \
        else df.reset_index(drop=True)

    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    out = df.copy()
    out = pd.concat([
        out,
        moving_averages(c),
        macd(c),
        kd(h, l, c),
        market_structure(h, l, c),
        fair_value_gaps(h, l),
        order_blocks(o, h, l, c),
        liquidity_sweep(h, l, c),
    ], axis=1)
    out["rsi14"] = rsi(c, 14)
    out["ma_align"] = ma_alignment(c)
    out["bias20"] = bias(c, 20)
    return out


def technical_score(row: pd.Series) -> float:
    """把訊號加權成 0–100 的技術分。

    這組權重是起始假設，不是結論 —— 階段 4 的 walk-forward 檢驗會回頭調它。
    """
    score = 50.0
    if row.get("ma_align") == 1:
        score += 12
    elif row.get("ma_align") == -1:
        score -= 12

    osc = row.get("osc")
    if pd.notna(osc):
        score += 8 if osc > 0 else -8

    r = row.get("rsi14")
    if pd.notna(r):
        if 50 <= r < 70:
            score += 8
        elif r >= 80:
            score -= 6      # 過熱
        elif r < 30:
            score += 4      # 超賣反彈機會
        elif 30 <= r < 50:
            score -= 4

    k, d = row.get("k"), row.get("d")
    if pd.notna(k) and pd.notna(d):
        if k > d:
            score += 6
        else:
            score -= 6
        if k < 20 and d < 20:
            score += 4      # 低檔

    if row.get("trend") == 1:
        score += 8
    elif row.get("trend") == -1:
        score -= 8

    if row.get("choch") and row.get("trend") == 1:
        score += 6          # 剛轉多
    if row.get("fvg_bull"):
        score += 3
    if row.get("sweep_low"):
        score += 4          # 掃完下方流動性後收回
    if row.get("sweep_high"):
        score -= 4

    b = row.get("bias20")
    if pd.notna(b) and abs(b) > 15:
        score -= 5          # 乖離過大，追高風險

    return float(np.clip(score, 0, 100))
