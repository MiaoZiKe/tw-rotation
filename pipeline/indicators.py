"""技術指標庫。

刻意不依賴 TA-Lib —— 它需要編譯 C 函式庫，在 GitHub Actions 上安裝很脆弱。
全部用 pandas/numpy 自己算，並附上單元測試對照已知值。

台股慣例的細節（跟很多國外套件的預設不同，弄錯會與看盤軟體對不起來）：
- KD 用 9 日 RSV，K 與 D 都是 1/3 平滑（等同 α=1/3 的 EMA），初始值 50
- RSI 用 Wilder 平滑（α=1/n），不是簡單移動平均
- MACD 慣稱 DIF / MACD / OSC，其中 OSC 才是柱狀體

--------------------------------------------------------------------------
2026-09-18 效能重構（答案不准變，只准變快）
--------------------------------------------------------------------------
`compute_all` 在部署時要跑 2,334 檔，而且 `mtf.py` 每個週期還會再呼叫一次，
所以它是整條 pipeline 最值得改的地方。這一輪的原則：

1. **算式一個字都不准動。** 所有浮點運算的「順序與型別」都保持原樣 ——
   包括看起來可以用 `ewm` 一行取代的 Wilder / KD 遞迴。實測 pandas 的 `ewm`
   與手寫遞迴差在 1e-15，雖然過得了 golden 的 1e-9 門檻，但 `k > d`、
   `rr >= 1.8` 這種臨界比較在 2,334 檔裡總會有人踩到，一翻就是判定變了。
   **所以遞迴一律保留手寫版**，只把「怎麼跑這個迴圈」改快。
2. **能向量化的才向量化。** 純粹逐列掃描（擺動點、FVG）改成 numpy 整批算；
   真正的狀態機（market_structure 的 last_sh/last_sl 會被突破清掉）留迴圈，
   但先 `.tolist()` 再跑 —— 元素存取從 numpy 純量裝箱變回 Python float，
   實測快 2–3 倍，而且是同一組 IEEE double 運算，位元級結果完全一樣。
3. **算過的不要再算一次。** 原本 `market_structure` 在 `compute_all` 裡被算兩遍
   （自己一次、`order_blocks` 內部又一次）；`ma_alignment` 與 `bias` 也各自把
   `moving_averages` 已經算好的 MA 重算。這些都改成共用。
4. **公開簽名與回傳結構完全不變** —— 別人（mtf.py / build_payload.py）正在改的
   程式會呼叫這些函式。需要共用中間結果的地方一律拆成 `_xxx_arrays` 私有函式，
   公開函式退化成薄包裝。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

# --------------------------------------------------------------- 移動平均

MA_PERIODS = (5, 10, 20, 60, 120, 240)


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def moving_averages(close: pd.Series, periods=MA_PERIODS) -> pd.DataFrame:
    return pd.DataFrame({f"ma{p}": sma(close, p) for p in periods}, index=close.index)


def _ma_align_arrays(mas: list[np.ndarray]) -> np.ndarray:
    """由「已依週期由小到大排好」的 MA 陣列判多空排列，回傳 int8。

    拆出來是為了讓 `compute_all` 直接餵它「已經算好的那組 MA」，
    不必為了排列判定再 rolling 一次（原本 ma5/ma20/ma60/ma120 等於算了兩遍）。
    """
    n = len(mas[0])
    bull = np.ones(n, dtype=bool)
    bear = np.ones(n, dtype=bool)
    for a, b in zip(mas[:-1], mas[1:]):
        # 與 NaN 比較恆為 False，所以有缺值的那幾根自然就不是多頭也不是空頭
        bull &= a > b
        bear &= a < b
    out = np.zeros(n, dtype="int8")
    out[bull] = 1
    out[bear] = -1
    # 只給一個週期時 bull/bear 會同時成立，這一行才有作用；多週期時是保險
    nan_any = np.zeros(n, dtype=bool)
    for a in mas:
        nan_any |= np.isnan(a)
    out[nan_any] = 0
    return out


def ma_alignment(close: pd.Series, periods=(5, 20, 60, 120)) -> pd.Series:
    """均線多頭排列判定：+1 完全多頭、-1 完全空頭、0 糾結。"""
    mas = [sma(close, p).to_numpy(dtype="float64") for p in sorted(periods)]
    return pd.Series(_ma_align_arrays(mas), index=close.index, dtype="int8")


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

def _wilder_rma_arr(arr: np.ndarray, period: int) -> np.ndarray:
    """Wilder 平滑的核心，輸入輸出都是 numpy 陣列。

    遞迴本身沒有動：`out[i] = (out[i-1]*(period-1) + arr[i]) / period`。
    唯一的改動是先 `.tolist()` 再跑迴圈 —— 原本每一圈都在對 numpy 陣列做
    純量索引（每次都要配一個 np.float64 物件），改成 Python float 之後
    實測 0.256ms → 0.092ms，而且兩者是同一組 IEEE double 運算，位元級相同。
    """
    n = len(arr)
    out = np.full(n, np.nan)
    if n < period:
        return out
    # 種子＝前 period 筆的簡單平均。全是 NaN 時 nanmean 回 NaN 並警告，
    # 之後的遞迴會一路 NaN 下去 —— 這是原本就有的行為，刻意保留。
    prev = float(np.nanmean(arr[:period]))
    src = arr.tolist()
    pm1 = period - 1
    res = [prev]
    for i in range(period, n):
        prev = (prev * pm1 + src[i]) / period
        res.append(prev)
    out[period - 1:] = res
    return out


def wilder_rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder 平滑（Pine Script 的 ta.rma）。

    關鍵細節：第一個值是前 period 筆的簡單平均，之後才遞迴。
    直接用 ewm(adjust=False) 會以第一筆當種子，算出來的數字與看盤軟體對不起來。
    """
    arr = series.to_numpy(dtype="float64")
    return pd.Series(_wilder_rma_arr(arr, period), index=series.index)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI，與 TradingView 的 ta.rsi 同一套種子規則。

    原本每一步（diff / clip / iloc / reindex / replace / where）都是一個 pandas
    Series 操作，700 根的資料量根本吃不到 pandas 的好處，全是物件建構成本。
    改成整段在 numpy 裡走完，運算順序與內容完全照舊：
      gain = clip(delta, 下限 0)  ≡ np.maximum(delta, 0)（NaN 一樣保留成 NaN）
      rs   = avg_gain / avg_loss（avg_loss 為 0 先換成 NaN）
      再用兩個 where 補上「全漲＝100 / 全跌＝0」的定義
    """
    c = close.to_numpy(dtype="float64")
    n = len(c)
    out = np.full(n, np.nan)
    if n > 1:
        delta = c[1:] - c[:-1]                       # 對應 close.diff() 的第 1..n-1 筆
        # np.maximum 對 NaN 會傳回 NaN，跟 Series.clip(lower=0) 的語意一致
        gain = np.maximum(delta, 0.0)
        loss = np.maximum(-delta, 0.0)
        avg_gain = np.full(n, np.nan)
        avg_loss = np.full(n, np.nan)
        # 原本是 wilder_rma(gain, period).reindex(close.index)：
        # gain 的 index 是 1..n-1，reindex 回來就是第 0 筆補 NaN，等同這裡的錯位擺放
        avg_gain[1:] = _wilder_rma_arr(gain, period)
        avg_loss[1:] = _wilder_rma_arr(loss, period)
        with np.errstate(divide="ignore", invalid="ignore"):
            safe_loss = np.where(avg_loss == 0, np.nan, avg_loss)
            rs = avg_gain / safe_loss
            out = 100 - (100 / (1 + rs))
        # 全期間都在漲（avg_loss 為 0）時 RSI 定義為 100
        out = np.where((avg_loss == 0) & (avg_gain > 0), 100.0, out)
        out = np.where((avg_gain == 0) & (avg_loss > 0), 0.0, out)
    return pd.Series(out, index=close.index)


# --------------------------------------------------------------- KD

def _kd_arrays(high: pd.Series, low: pd.Series, close: pd.Series,
               n: int, k_smooth: int, d_smooth: int
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """KD 的陣列版，回傳 (rsv, k, d)。

    K/D 的遞迴刻意不用 ewm 取代：數學上等價，但浮點結果差在 1e-15，
    而 `k > d` 是判定的分水嶺，臨界股票會翻面。這裡只把迴圈改成跑 Python list
    （元素存取不再裝箱），算式與順序完全沒動。
    """
    ln = low.rolling(n, min_periods=n).min()
    hn = high.rolling(n, min_periods=n).max()
    ln_arr = ln.to_numpy(dtype="float64")
    hn_arr = hn.to_numpy(dtype="float64")
    span = hn_arr - ln_arr
    # 平盤時 H==L，RSV 沒有定義，台股慣例用 50；先換掉分母再除，避免除零警告
    at_par = span == 0
    safe_span = np.where(at_par, np.nan, span)
    with np.errstate(divide="ignore", invalid="ignore"):
        rsv = (close.to_numpy(dtype="float64") - ln_arr) / safe_span * 100
    rsv = np.where(at_par, 50.0, rsv)
    # 原本是 .where(hn.notna())：H_n 還沒滿 n 根（或本身缺值）的位置不給 RSV
    rsv = np.where(np.isnan(hn_arr), np.nan, rsv)

    ka, da = 1.0 / k_smooth, 1.0 / d_smooth
    total = len(close)
    k_vals = np.full(total, np.nan)
    d_vals = np.full(total, np.nan)
    k_prev = d_prev = 50.0
    started = False

    rsv_list = rsv.tolist()
    k_out: list[float] = []
    d_out: list[float] = []
    idx_out: list[int] = []
    for i in range(total):
        x = rsv_list[i]
        if x != x:                      # NaN 判斷，比 np.isnan 快且不必裝箱
            continue
        if not started:
            k_prev = d_prev = 50.0
            started = True
        k_prev = k_prev * (1 - ka) + x * ka
        d_prev = d_prev * (1 - da) + k_prev * da
        idx_out.append(i)
        k_out.append(k_prev)
        d_out.append(d_prev)
    if idx_out:
        pos = np.asarray(idx_out)
        k_vals[pos] = k_out
        d_vals[pos] = d_out
    return rsv, k_vals, d_vals


def kd(high: pd.Series, low: pd.Series, close: pd.Series,
       n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
    """台股慣用的 KD（9,3,3）。

    RSV = (C - L_n) / (H_n - L_n) * 100
    K   = K_prev * (1 - 1/k_smooth) + RSV * (1/k_smooth)
    D   = D_prev * (1 - 1/d_smooth) + K   * (1/d_smooth)
    初始 K = D = 50，與國內看盤軟體一致。
    """
    rsv, k_vals, d_vals = _kd_arrays(high, low, close, n, k_smooth, d_smooth)
    return pd.DataFrame({"rsv": rsv, "k": k_vals, "d": d_vals}, index=close.index)


# --------------------------------------------------------------- ATR 與量能

def _true_range_arr(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """真實區間。原本用 pd.concat 疊三欄再 max(axis=1)，光是建那個 DataFrame
    就比算本身貴。`DataFrame.max(axis=1)` 預設會跳過 NaN，對應的 numpy 是
    `np.fmax`（不是 `np.maximum`，後者會把 NaN 傳染出去）。"""
    n = len(h)
    prev_close = np.empty(n)
    prev_close[0] = np.nan
    prev_close[1:] = c[:-1]
    tr = np.fmax(np.fmax(h - l, np.abs(h - prev_close)), np.abs(l - prev_close))
    tr[0] = h[0] - l[0]
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder ATR。停損距離、區間寬度、波動過濾都靠它，複用同一套 RMA 種子規則。"""
    tr = _true_range_arr(high.to_numpy(dtype="float64"), low.to_numpy(dtype="float64"),
                         close.to_numpy(dtype="float64"))
    return pd.Series(_wilder_rma_arr(tr, period), index=high.index)


def _volume_stats_arrays(volume: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    v = pd.to_numeric(volume, errors="coerce")
    ma5 = v.rolling(5, min_periods=5).mean().to_numpy(dtype="float64")
    ma20 = v.rolling(20, min_periods=20).mean().to_numpy(dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        # 原本是 ma20.replace(0, np.nan) 再除 —— 量為 0 的那天量比沒有意義
        ratio = v.to_numpy(dtype="float64") / np.where(ma20 == 0, np.nan, ma20)
    return ma5, ma20, ratio


def volume_stats(volume: pd.Series) -> pd.DataFrame:
    """均量與量比。量比 ≥ 1.5 視為爆量（技術分析專家的門檻）。"""
    ma5, ma20, ratio = _volume_stats_arrays(volume)
    return pd.DataFrame({
        "vol_ma5": ma5,
        "vol_ma20": ma20,
        "vol_ratio": ratio,
    }, index=volume.index)


def _limit_arrays(c: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """漲跌停旗標的陣列版。

    pandas 的 pct_change 實作就是 `self / self.shift() - 1`，所以這裡照抄同樣的
    算式（不是 (a-b)/b，那兩個在浮點上不等價）。收盤為 0 會產生 inf，
    原本的 pandas 版也一樣是 inf，只是不會叫，所以這裡把警告關掉。
    """
    n = len(c)
    chg = np.full(n, np.nan)
    if n > 1:
        with np.errstate(divide="ignore", invalid="ignore"):
            chg[1:] = (c[1:] / c[:-1] - 1) * 100
    # 與 NaN 比較恆為 False，等同原本 fillna(False) 之後的結果
    return chg >= threshold, chg <= -threshold


def limit_flags(close: pd.Series, threshold: float = 9.8) -> pd.DataFrame:
    """漲跌停旗標。台股漲跌幅 10%，取 9.8% 以上視為觸及。

    鎖死漲停的 K 棒不能拿來算 FVG／OB（它不是市場自由成交的結果），
    也是「不要碰」的硬性排除條件之一。
    """
    up, down = _limit_arrays(close.to_numpy(dtype="float64"), threshold)
    return pd.DataFrame({"limit_up": up, "limit_down": down}, index=close.index)


def volume_profile(high: pd.Series, low: pd.Series, volume: pd.Series,
                   lookback: int = 120, bins: int = 40, top_n: int = 3) -> list[dict]:
    """成交量密集區（VPVR 的簡化版）。

    把近 lookback 根 K 的價格範圍分成 bins 桶，每根 K 的成交量平均攤到它覆蓋的桶，
    取量最大的 top_n 桶當「有大量籌碼換手」的價位帶 —— 支撐壓力的第三個來源。

    效能：原本每根 K 都呼叫兩次 `np.searchsorted`（純量版，呼叫成本遠大於運算），
    改成整批算完再跑分配迴圈。**分配迴圈刻意保留**：`vol[i]` 的加總順序若改成
    cumsum 之類的技巧，浮點誤差會讓量接近的兩個桶排名互換，
    最後 `argsort` 取的 top_n 就不一樣了 —— 那是答案變了，不是變快。
    """
    h = high.tail(lookback).to_numpy(dtype=float)
    l = low.tail(lookback).to_numpy(dtype=float)
    v = pd.to_numeric(volume.tail(lookback), errors="coerce").fillna(0).to_numpy(dtype=float)
    if len(h) < 20 or np.isnan(h).all():
        return []
    lo, hi = np.nanmin(l), np.nanmax(h)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return []
    edges = np.linspace(lo, hi, bins + 1)
    # 整批算出每根 K 覆蓋的桶區間；NaN 在 searchsorted 會被排到最後，
    # 但那幾根本來就被 valid 濾掉，不影響結果
    i0 = np.clip(np.searchsorted(edges, l, side="right") - 1, 0, bins - 1)
    i1 = np.clip(np.searchsorted(edges, h, side="right") - 1, 0, bins - 1)
    # 原本的條件是 isnan(hh) or isnan(ll) or vv <= 0 就 continue；
    # ~(v <= 0) 對 NaN 會得到 True，跟原本「NaN 量不會被 <= 0 擋掉」一致
    valid = ~np.isnan(h) & ~np.isnan(l) & ~(v <= 0)
    vol = [0.0] * bins
    a0, a1 = i0.tolist(), i1.tolist()
    vl = v.tolist()
    for k in np.flatnonzero(valid).tolist():
        s, e = a0[k], a1[k]
        share = vl[k] / (e - s + 1)
        for b in range(s, e + 1):
            vol[b] += share
    vol = np.asarray(vol)
    order = np.argsort(vol)[::-1][:top_n]
    total = vol.sum() or 1.0
    return [{"low": float(edges[i]), "high": float(edges[i + 1]),
             "volume_share": float(vol[i] / total)} for i in sorted(order)]


# --------------------------------------------------------------- SMC

def _swing_arrays(h: np.ndarray, l: np.ndarray, lookback: int) -> tuple[np.ndarray, np.ndarray]:
    """擺動高低點的陣列版，整批算完，不再逐根切窗。

    原本每一根都切一次 `h[i-lb:i+lb+1]` 再 max/sum，700 根就是 2,800 次 numpy 呼叫，
    是 compute_all 裡最貴的單一函式。`sliding_window_view` 只是同一塊記憶體的
    stride 視圖（不複製），一次 max/比較就把整條算完。

    判定條件原封不動：中心點要等於窗內最大值，**而且窗內只有它一個**（唯一最大），
    平高的雙峰不算擺動點。NaN 參與 max 會得到 NaN，與 NaN 比較恆為 False，
    所以有缺值的窗自動不成立 —— 跟原本逐根版的行為一樣。
    """
    n = len(h)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    w = 2 * lookback + 1
    if n < w:
        return sh, sl
    stop = n - lookback
    wh = sliding_window_view(h, w)
    wl = sliding_window_view(l, w)
    ch = h[lookback:stop][:, None]
    cl = l[lookback:stop][:, None]
    sh[lookback:stop] = (ch[:, 0] == wh.max(axis=1)) & ((wh == ch).sum(axis=1) == 1)
    sl[lookback:stop] = (cl[:, 0] == wl.min(axis=1)) & ((wl == cl).sum(axis=1) == 1)
    return sh, sl


def swing_points(high: pd.Series, low: pd.Series, lookback: int = 2) -> pd.DataFrame:
    """分形擺動高低點：某根 K 的高點高於左右各 lookback 根 -> 擺動高點。

    lookback=2 對應常見的 5 根分形。這是後面所有 SMC 結構判定的地基。
    """
    sh, sl = _swing_arrays(high.to_numpy(dtype="float64"),
                           low.to_numpy(dtype="float64"), lookback)
    return pd.DataFrame({"swing_high": sh, "swing_low": sl}, index=high.index)


def _market_structure_arrays(h: np.ndarray, l: np.ndarray, c: np.ndarray, lookback: int
                             ) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                        np.ndarray, np.ndarray]:
    """BOS / CHoCH 的陣列版，回傳 (trend, bos, choch, swing_high, swing_low)。

    這個迴圈**不能向量化**：last_sh / last_sl 被突破之後會被清成 None，
    要等下一個擺動點才復活，屬於前後相依的狀態機。
    能做的是讓每一圈便宜一點 —— 先 `.tolist()`，迴圈裡就都是 Python float/bool，
    不再對 numpy 陣列做純量索引（每次都會配一個新的 np 純量物件）。
    比較的語意完全相同（同一組 IEEE double，NaN 比較一律 False）。
    """
    sh_arr, sl_arr = _swing_arrays(h, l, lookback)
    n = len(c)
    bos = np.zeros(n, dtype=bool)
    choch = np.zeros(n, dtype=bool)

    cl, hl, ll = c.tolist(), h.tolist(), l.tolist()
    shl, sll = sh_arr.tolist(), sl_arr.tolist()
    trend_list = [0] * n
    bos_idx: list[int] = []
    choch_idx: list[int] = []

    last_sh: float | None = None   # 最近一個已確認的擺動高點
    last_sl: float | None = None
    cur_trend = 0

    for i in range(n):
        # 擺動點要等右側 lookback 根走完才算確認，所以延遲 lookback 根才納入
        j = i - lookback
        if j >= 0:
            if shl[j]:
                last_sh = hl[j]
            if sll[j]:
                last_sl = ll[j]

        ci = cl[i]
        if last_sh is not None and ci > last_sh:
            if cur_trend == -1:
                choch_idx.append(i)
            elif cur_trend == 1:
                bos_idx.append(i)
            cur_trend = 1
            last_sh = None          # 已被突破，等待新的擺動高點
        elif last_sl is not None and ci < last_sl:
            if cur_trend == 1:
                choch_idx.append(i)
            elif cur_trend == -1:
                bos_idx.append(i)
            cur_trend = -1
            last_sl = None

        trend_list[i] = cur_trend

    if bos_idx:
        bos[bos_idx] = True
    if choch_idx:
        choch[choch_idx] = True
    return np.asarray(trend_list, dtype="int8"), bos, choch, sh_arr, sl_arr


def market_structure(high: pd.Series, low: pd.Series, close: pd.Series,
                     lookback: int = 2) -> pd.DataFrame:
    """BOS / CHoCH 結構判定。

    BOS   (Break of Structure)     順著既有趨勢突破前一個擺動點 -> 趨勢延續
    CHoCH (Change of Character)    逆著既有趨勢跌破/突破 -> 趨勢可能反轉

    輸出 trend 欄位：1 多頭結構、-1 空頭結構、0 尚未定義。
    """
    trend, bos, choch, sh, sl = _market_structure_arrays(
        high.to_numpy(dtype="float64"), low.to_numpy(dtype="float64"),
        close.to_numpy(dtype="float64"), lookback)
    return pd.DataFrame({
        "trend": trend, "bos": bos, "choch": choch,
        "swing_high": sh, "swing_low": sl,
    }, index=close.index)


def _fvg_arrays(h: np.ndarray, l: np.ndarray, min_gap_pct: float, ex: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """FVG 的陣列版：三根一組的關係可以整條錯位相減，完全不需要迴圈。

    第 i 根對上的是 i-2（第 1 根）與 i（第 3 根），所以把陣列錯開兩格就是整批比較。
    原本的 `elif` 語意要保留：多方成立就不再看空方，所以空方要再 `& ~多方`。
    `np.maximum(l1, 1e-9)` 與 Python `max(l1, 1e-9)` 對 NaN 都會得到 NaN，
    除出來是 NaN、比較是 False，跟原本 short-circuit 的結果一致。
    """
    n = len(h)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    top = np.full(n, np.nan)
    bottom = np.full(n, np.nan)
    if n < 3:
        return bull, bear, bottom, top

    h1, l1 = h[:-2], l[:-2]          # 第 1 根
    h3, l3 = h[2:], l[2:]            # 第 3 根
    skip = ex[2:] | ex[1:-1] | ex[:-2]
    ref = np.maximum(l1, 1e-9)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = (l3 > h1) & ((l3 - h1) / ref * 100 >= min_gap_pct)
        s = (l1 > h3) & ((l1 - h3) / ref * 100 >= min_gap_pct)
    b &= ~skip
    s &= ~skip & ~b

    bull[2:] = b
    bear[2:] = s
    bottom[2:] = np.where(b, h1, np.where(s, h3, np.nan))
    top[2:] = np.where(b, l3, np.where(s, l1, np.nan))
    return bull, bear, bottom, top


def fair_value_gaps(high: pd.Series, low: pd.Series,
                    min_gap_pct: float = 0.0,
                    exclude: pd.Series | None = None) -> pd.DataFrame:
    """公允價值缺口（FVG）：三根 K 之間留下的未成交區間。

    多方 FVG：第 1 根的高點 < 第 3 根的低點（中間那根急拉留下缺口）
    空方 FVG：第 1 根的低點 > 第 3 根的高點

    缺口標記在第 3 根上，因為那時才確認成立。

    台股每天開盤都可能跳空，min_gap_pct 為 0 會產生大量無效缺口；
    compute_all 會用 max(0.6, 0.3×ATR%) 當門檻。exclude 標記的 K（漲跌停）不參與。
    """
    h, l = high.to_numpy(dtype="float64"), low.to_numpy(dtype="float64")
    ex = (exclude.to_numpy(dtype=bool) if exclude is not None
          else np.zeros(len(h), dtype=bool))
    bull, bear, bottom, top = _fvg_arrays(h, l, min_gap_pct, ex)
    return pd.DataFrame({
        "fvg_bull": bull, "fvg_bear": bear,
        "fvg_bottom": bottom, "fvg_top": top,
    }, index=high.index)


def _order_blocks_arrays(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                         trend: np.ndarray, bos: np.ndarray, choch: np.ndarray
                         ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """OB 的陣列版，而且**接受外面算好的結構**。

    原本 `order_blocks` 會自己再呼叫一次 `market_structure`，
    但 `compute_all` 上一行才剛算過同一組 —— 等於整個結構判定（含擺動點）算了兩遍。
    拆成這支之後，compute_all 算一次餵兩邊。

    掃描本身也只走「真的有突破」的那幾根（flatnonzero），不再整條 700 根跑一遍。
    向上與向下分成兩輪跑不影響結果：兩者互斥（trend 不會同時是 1 和 -1），
    而且同一根被重複標記時寫進去的是同樣的 l[j]/h[j]。
    """
    n = len(c)
    ob_bull = np.zeros(n, dtype=bool)
    ob_bear = np.zeros(n, dtype=bool)
    ob_top = np.full(n, np.nan)
    ob_bottom = np.full(n, np.nan)

    brk = bos | choch
    ol, cl, hl, ll = o.tolist(), c.tolist(), h.tolist(), l.tolist()

    for i in np.flatnonzero(brk & (trend == 1)).tolist():
        for j in range(i - 1, max(-1, i - 21), -1):
            if cl[j] < ol[j]:                       # 最後一根黑 K
                ob_bull[j] = True
                ob_bottom[j], ob_top[j] = ll[j], hl[j]
                break
    for i in np.flatnonzero(brk & (trend == -1)).tolist():
        for j in range(i - 1, max(-1, i - 21), -1):
            if cl[j] > ol[j]:                       # 最後一根紅 K
                ob_bear[j] = True
                ob_bottom[j], ob_top[j] = ll[j], hl[j]
                break
    return ob_bull, ob_bear, ob_top, ob_bottom


def order_blocks(open_: pd.Series, high: pd.Series, low: pd.Series,
                 close: pd.Series, lookback: int = 2) -> pd.DataFrame:
    """Order Block：造成結構突破之前的最後一根反向 K 棒。

    多方 OB = BOS/CHoCH 向上之前的最後一根黑 K
    空方 OB = 向下突破之前的最後一根紅 K
    """
    h = high.to_numpy(dtype="float64")
    l = low.to_numpy(dtype="float64")
    c = close.to_numpy(dtype="float64")
    trend, bos, choch, _, _ = _market_structure_arrays(h, l, c, lookback)
    ob_bull, ob_bear, ob_top, ob_bottom = _order_blocks_arrays(
        open_.to_numpy(dtype="float64"), h, l, c, trend, bos, choch)
    return pd.DataFrame({
        "ob_bull": ob_bull, "ob_bear": ob_bear,
        "ob_top": ob_top, "ob_bottom": ob_bottom,
    }, index=close.index)


def _sweep_arrays(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int
                  ) -> tuple[np.ndarray, np.ndarray]:
    """rolling 本身是 pandas 的 C 實作，夠快；貴的是後面那一堆 Series 比較與
    DataFrame 建構，所以只把比較搬到 numpy。"""
    prev_high = np.full(len(close), np.nan)
    prev_low = np.full(len(close), np.nan)
    rh = high.rolling(lookback, min_periods=lookback).max().to_numpy(dtype="float64")
    rl = low.rolling(lookback, min_periods=lookback).min().to_numpy(dtype="float64")
    prev_high[1:] = rh[:-1]          # 等同 .shift(1)
    prev_low[1:] = rl[:-1]
    h = high.to_numpy(dtype="float64")
    l = low.to_numpy(dtype="float64")
    c = close.to_numpy(dtype="float64")
    return ((h > prev_high) & (c < prev_high),
            (l < prev_low) & (c > prev_low))


def liquidity_sweep(high: pd.Series, low: pd.Series, close: pd.Series,
                    lookback: int = 20) -> pd.DataFrame:
    """流動性掃蕩：盤中破前高/前低但收盤收回來，典型的假突破誘多誘空。"""
    sweep_high, sweep_low = _sweep_arrays(high, low, close, lookback)
    return pd.DataFrame({"sweep_high": sweep_high, "sweep_low": sweep_low},
                        index=close.index)


# --------------------------------------------------------------- 整合

def compute_all(df: pd.DataFrame, structure_lookback: int = 2) -> pd.DataFrame:
    """輸入含 open/high/low/close 的個股日 K（依日期排序），輸出全部指標。

    structure_lookback：擺動點左右各看幾根；日線 2（5 根分形），週線/月線用 3 比較不會被單週雜訊翻來翻去，
    與 technical.weekly_structure 的口徑一致。

    效能重點（輸出欄位、順序、dtype 與數值都與重構前相同）：
    - 結構判定（market_structure）只算一次，OB 直接吃它的結果，不再重算一遍
    - 均線排列與乖離率直接用上面算好的那組 MA，不再為了它們 rolling 第二次
    - 中間不再組 MA／MACD／KD 三張只是用來轉手的 DataFrame，直接拿陣列
    - 最後只做「原始欄位 + 一個新欄位表」的單一次 concat，
      取代原本 9 個 DataFrame 的 concat 再加 5 次逐欄指派（每次都要重排 block）
    """
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要欄位：{sorted(missing)}")

    # 排序照舊無條件做。試過「已排好就跳過」，但守門檢查（要同時驗遞增與唯一，
    # 因為 sort_values 預設 quicksort 不穩定，日期有重複時會換位置）本身就要 0.13ms，
    # 跟 sort_values 一樣貴 —— 省不到東西，反而多一條要推敲的路徑。
    df = df.sort_values("date").reset_index(drop=True) if "date" in df.columns \
        else df.reset_index(drop=True)

    o = df["open"].to_numpy(dtype="float64")
    h = df["high"].to_numpy(dtype="float64")
    l = df["low"].to_numpy(dtype="float64")
    c_ser = df["close"]
    c = c_ser.to_numpy(dtype="float64")
    n = len(df)

    atr14 = _wilder_rma_arr(_true_range_arr(h, l, c), 14)
    limit_up, limit_down = _limit_arrays(c, 9.8)
    # FVG 門檻：max(0.6%, 0.3×ATR%)，避免每天的開盤跳空都變成缺口
    with np.errstate(divide="ignore", invalid="ignore"):
        atr_pct = atr14 / c * 100
    atr_pct = np.where(np.isnan(atr_pct), 0.0, atr_pct)
    gap_pct = float(max(0.6, 0.3 * float(atr_pct[-1]))) if n else 0.6

    # 直接要陣列就好：原本先組一張 MA 的 DataFrame、再一欄一欄 to_numpy 拆回來，
    # 那張表從頭到尾只是中轉站。sma() 還是同一支，rolling 的結果位元級相同。
    ma_arrays = {f"ma{p}": sma(c_ser, p).to_numpy(dtype="float64") for p in MA_PERIODS}
    dif_s = ema(c_ser, 12) - ema(c_ser, 26)          # 與 macd() 同一組算式
    macd_s = ema(dif_s, 9)
    rsv_a, k_a, d_a = _kd_arrays(df["high"], df["low"], c_ser, 9, 3, 3)
    trend, bos, choch, swing_high, swing_low = _market_structure_arrays(
        h, l, c, structure_lookback)
    fvg_bull, fvg_bear, fvg_bottom, fvg_top = _fvg_arrays(
        h, l, gap_pct, limit_up | limit_down)
    # 要和上面的結構用同一組 lookback —— 現在餵的就是同一份結果，不可能再對不上
    ob_bull, ob_bear, ob_top, ob_bottom = _order_blocks_arrays(
        o, h, l, c, trend, bos, choch)
    sweep_high, sweep_low = _sweep_arrays(df["high"], df["low"], c_ser, 20)
    ma20 = ma_arrays["ma20"]

    # 欄位順序刻意與重構前一字不差（前端 chart.js 與 build_payload 都照名字拿，
    # 但 mtf/測試有比對整張表，順序一起釘住比較安全）
    cols: dict[str, np.ndarray] = {}
    cols.update(ma_arrays)
    dif_a = dif_s.to_numpy(dtype="float64")
    macd_a = macd_s.to_numpy(dtype="float64")
    cols["dif"] = dif_a
    cols["macd"] = macd_a
    cols["osc"] = dif_a - macd_a
    cols["rsv"] = rsv_a
    cols["k"] = k_a
    cols["d"] = d_a
    cols["trend"] = trend
    cols["bos"] = bos
    cols["choch"] = choch
    cols["swing_high"] = swing_high
    cols["swing_low"] = swing_low
    cols["fvg_bull"] = fvg_bull
    cols["fvg_bear"] = fvg_bear
    cols["fvg_bottom"] = fvg_bottom
    cols["fvg_top"] = fvg_top
    cols["ob_bull"] = ob_bull
    cols["ob_bear"] = ob_bear
    cols["ob_top"] = ob_top
    cols["ob_bottom"] = ob_bottom
    cols["sweep_high"] = sweep_high
    cols["sweep_low"] = sweep_low
    cols["limit_up"] = limit_up
    cols["limit_down"] = limit_down
    cols["atr14"] = atr14
    cols["atr_pct"] = atr_pct
    cols["rsi14"] = rsi(c_ser, 14).to_numpy(dtype="float64")
    # 排列與乖離都吃上面那組 MA：同一支 sma()、同一份 rolling 平均，位元級相同
    cols["ma_align"] = _ma_align_arrays([ma_arrays["ma5"], ma20,
                                         ma_arrays["ma60"], ma_arrays["ma120"]])
    with np.errstate(divide="ignore", invalid="ignore"):
        cols["bias20"] = (c - ma20) / ma20 * 100
    if "volume" in df.columns:
        vol_ma5, vol_ma20, vol_ratio = _volume_stats_arrays(df["volume"])
        cols["vol_ma5"], cols["vol_ma20"], cols["vol_ratio"] = vol_ma5, vol_ma20, vol_ratio
    else:
        cols["vol_ma5"] = cols["vol_ma20"] = cols["vol_ratio"] = np.full(n, np.nan)

    return pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)


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
