"""M3 技術面規則引擎：支撐壓力區間、進出場判定、停損目標、文字說明、週線燈號。

技術分析專家定的契約：
- 支撐壓力是「多源交集」：Order Block、前波擺動點、成交量密集區、MA60/120、
  未回補 FVG、整數關卡。各自帶權重，合併後 score ≥ 3.0 才顯示 —— 等同至少兩個
  獨立來源交集。單一來源的區間不畫，否則圖上到處都是支撐。
- 進場分 A（回檔承接）/ B（突破追進）/ 觀望 / 不要碰，先跑硬性排除。
- 停損 = min(有效 OB 下緣, 最近擺動低點, 需求區下緣) − 0.5×ATR；風險 > 8% 降級為觀望，
  絕不縮停損去湊風報比。
- 文字說明三段式：結論 → 理由（最多 3 條）→ 風險與失效條件。禁止輸出裸指標值。
- SMC 在台股的限制：全部區間都要與傳統量價交集後才呈現（score 門檻就是為此）。

--------------------------------------------------------------------------
2026-09-18 效能重構（判定結果一個字都不准變）
--------------------------------------------------------------------------
量出來這支一檔要 30ms，全市場 70 秒，其中八成集中在兩個地方：

1. `_candidates` 的「這個區間有沒有被吃掉」判斷。原本每一個 OB／FVG 候選都要
   `df.loc[idx:]` 切一份尾段再整段掃一次，候選一多就是 O(n × 候選數)；
   同一支還把整欄 700 列的日期 `astype(str)`，但真正用得到的只有最後 120 列。
   改法：先算好「從第 i 根之後的收盤最低／最高」前綴表，每個候選查表即可（O(1)）。
2. `weekly_structure` 的 `df.copy()`。它只需要 OHLCV 五欄，卻複製了整張
   四十幾欄的指標表。改成只取要用的欄位再 resample。

另外 `evaluate` 裡 `df.tail(60)` 被重算五次、`swing_high` 的遮罩被算三次，
一併收斂成算一次。**所有會影響判定的運算式都原封不動** —— 包含那些看起來
可以換成 numpy 的比較：`signals` 裡的 kd_cross_low / osc_turn 目前是 np.bool_，
換成 Python bool 會讓序列化結果從 "False" 變成 false，那就是答案變了。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import indicators as ind

log = logging.getLogger(__name__)

MIN_TURNOVER = 3e7          # 日均成交值 < 3000 萬：出不掉，不要碰
ZONE_MIN_SCORE = 3.0
MAX_ZONE_PCT = 4.0          # 單一支撐壓力區間最寬 = 價格的 4%（再寬就不是「區間」是「一段走勢」）
MIN_ZONE_PCT = 1.2          # 低價股的下限，不然 4% 太窄合不出東西
MAX_RISK_PCT = 8.0
MIN_RISK_PCT = 2.0


@dataclass
class Zone:
    low: float
    high: float
    score: float
    sources: list[str] = field(default_factory=list)
    kind: str = ""          # demand / supply
    since: str | None = None    # 這個區間從哪一根開始成立（前端從那裡往右畫）

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2

    @property
    def width_pct(self) -> float:
        return (self.high - self.low) / self.mid * 100 if self.mid else 0.0


# ------------------------------------------------------------------ 支撐壓力

def _suffix_min_after(a: np.ndarray) -> np.ndarray:
    """s[i] = min(a[i+1:])，也就是「第 i 根**之後**的最小值」；沒有後續就給 +inf。

    用來取代 `(df.loc[idx:]["close"].iloc[1:] < lo).any()` 這種逐候選的整段掃描。
    NaN 先換成 +inf 再累積，等同原本 pandas 比較時「NaN 一律 False」的語意
    （NaN 不會讓條件成立，也不該讓最小值變成 NaN 而污染整條）。
    """
    n = len(a)
    s = np.full(n, np.inf)
    if n > 1:
        filled = np.where(np.isnan(a), np.inf, a)
        s[:n - 1] = np.minimum.accumulate(filled[:0:-1])[::-1]
    return s


def _suffix_max_after(a: np.ndarray) -> np.ndarray:
    """s[i] = max(a[i+1:])；沒有後續就給 -inf。理由同 _suffix_min_after。"""
    n = len(a)
    s = np.full(n, -np.inf)
    if n > 1:
        filled = np.where(np.isnan(a), -np.inf, a)
        s[:n - 1] = np.maximum.accumulate(filled[:0:-1])[::-1]
    return s


def _flags_after(df: pd.DataFrame, col: str, base: int) -> list[int]:
    """回傳 base 之後（含）旗標為真的「位置」清單，取代 tail[...].iterrows()。

    原本要先切一張子表、再逐列建一個 object Series（iterrows 對混欄位型別的表
    每一列都要重新裝箱），實測比 to_numpy 慢一個量級。
    這裡回傳的是位置（0-based），與 `df.index.get_loc(idx)` 等價 ——
    `compute_all` 出來的表一定是 reset_index 過的 RangeIndex，
    而用位置反而比用標籤更不怕重複索引。
    """
    mask = df[col].iloc[base:].fillna(False).to_numpy(dtype=bool)
    return (np.flatnonzero(mask) + base).tolist()


def _candidates(df: pd.DataFrame, atr_val: float, lookback: int = 120) -> list[dict]:
    """收集各來源的候選區間，每個帶 {low, high, kind, weight, age, at}。

    `at` 是這個來源形成的那一根的日期，前端用它決定區間從哪裡開始畫 ——
    支撐壓力是「從那根之後才存在」，不是憑空浮在圖右邊（Andy 2026-09-12 回報）。

    候選的「附加順序」有意義：sr_zones 會 `sorted(key=low)`，而 Python 的排序是
    穩定的，low 相同時誰先誰後會影響合併結果。所以下面每一段的順序、以及每一段
    內部由舊到新的順序，都與重構前一致。
    """
    n = len(df)
    base = max(0, n - lookback)          # tail(lookback) 的起始位置
    cols = df.columns
    close = float(df["close"].iloc[-1])
    # 只有 tail 那一段的日期會被查到（候選全部來自 tail，量能密集區用的也是 base），
    # 原本整欄 700 列 astype(str) 是這支裡最貴的單一動作之一。
    dates = df["date"].iloc[base:].astype(str).tolist() if "date" in df else []

    def at_of(i: int) -> str | None:
        k = i - base
        return dates[k] if 0 <= k < len(dates) else None

    close_a = df["close"].to_numpy(dtype="float64")
    low_a = df["low"].to_numpy(dtype="float64")
    high_a = df["high"].to_numpy(dtype="float64")
    out = []

    # Order Block：只留尚未被收盤價穿透的
    if "ob_bull" in cols or "ob_bear" in cols:
        # 一次算好「之後的收盤最低／最高」，每個候選就只是查表比大小
        min_close_after = _suffix_min_after(close_a)
        max_close_after = _suffix_max_after(close_a)
        ob_bottom_a = df["ob_bottom"].to_numpy(dtype="float64")
        ob_top_a = df["ob_top"].to_numpy(dtype="float64")
        for col_flag, side in (("ob_bull", "demand"), ("ob_bear", "supply")):
            if col_flag not in cols:
                continue
            for pos in _flags_after(df, col_flag, base):
                lo, hi = ob_bottom_a[pos], ob_top_a[pos]
                if np.isnan(lo) or np.isnan(hi):
                    continue
                mitigated = (min_close_after[pos] < lo) if side == "demand" \
                    else (max_close_after[pos] > hi)
                if mitigated:
                    continue
                # iterrows 取出來的是 Python float（混欄位型別的表會轉 object），
                # 這裡補上 float() 讓型別與重構前一致
                out.append({"low": float(lo), "high": float(hi), "kind": "OB", "weight": 2.0,
                            "age": n - 1 - pos, "at": at_of(pos)})

    # 前波擺動點 ±0.3 ATR
    for col, side in (("swing_low", "demand"), ("swing_high", "supply")):
        if col not in cols:
            continue
        px_a = low_a if side == "demand" else high_a
        kind = "前波" + ("低點" if side == "demand" else "高點")
        for pos in _flags_after(df, col, base):
            px = float(px_a[pos])
            out.append({"low": px - 0.3 * atr_val, "high": px + 0.3 * atr_val,
                        "kind": kind,
                        "weight": 1.5, "age": n - 1 - pos, "at": at_of(pos)})

    # 成交量密集區
    if "volume" in df.columns:
        for vp in ind.volume_profile(df["high"], df["low"], df["volume"], lookback=lookback):
            out.append({"low": vp["low"], "high": vp["high"], "kind": "量能密集",
                        "weight": 1.5, "age": 0, "at": at_of(max(0, n - lookback))})

    # 均線動態帶（v 刻意保留 .iloc[-1] 的 np.float64，不要轉 float —— 型別跟著
    # 進 Zone.low，重構前就是這個型別）
    for col in ("ma60", "ma120"):
        v = df[col].iloc[-1] if col in df else np.nan
        if pd.notna(v):
            out.append({"low": v - 0.25 * atr_val, "high": v + 0.25 * atr_val,
                        "kind": col.upper(), "weight": 1.0, "age": 0, "at": None})

    # 未回補 FVG
    if "fvg_bull" in cols or "fvg_bear" in cols:
        min_low_after = _suffix_min_after(low_a)
        max_high_after = _suffix_max_after(high_a)
        fvg_bottom_a = df["fvg_bottom"].to_numpy(dtype="float64")
        fvg_top_a = df["fvg_top"].to_numpy(dtype="float64")
        for col_flag, side in (("fvg_bull", "demand"), ("fvg_bear", "supply")):
            if col_flag not in cols:
                continue
            for pos in _flags_after(df, col_flag, base):
                lo, hi = fvg_bottom_a[pos], fvg_top_a[pos]
                if np.isnan(lo) or np.isnan(hi):
                    continue
                # 原本是 (after["low"] <= lo).iloc[1:].any()：缺口被摸到就算回補
                filled = (min_low_after[pos] <= lo) if side == "demand" \
                    else (max_high_after[pos] >= hi)
                if filled:
                    continue
                out.append({"low": float(lo), "high": float(hi), "kind": "FVG", "weight": 0.8,
                            "age": n - 1 - pos, "at": at_of(pos)})

    # 整數關卡：現價上下 15% 內的 10/50/100 倍數
    step = 100 if close >= 500 else (50 if close >= 100 else 10)
    lo_bound, hi_bound = close * 0.85, close * 1.15
    k = int(lo_bound // step) * step
    while k <= hi_bound:
        if k > 0:
            out.append({"low": k * 0.997, "high": k * 1.003, "kind": "整數關卡",
                        "weight": 0.5, "age": 0, "at": None})
        k += step
    return out


def sr_zones(df: pd.DataFrame, atr_val: float, lookback: int = 120,
             decay: float = 0.97) -> tuple[list[Zone], list[Zone]]:
    """合併候選區間，回傳 (需求區, 供給區)，各最多 2 個，依 score 排序。"""
    if df.empty or not np.isfinite(atr_val) or atr_val <= 0:
        return [], []
    close = float(df["close"].iloc[-1])
    cands = sorted(_candidates(df, atr_val, lookback), key=lambda c: c["low"])
    merged: list[dict] = []
    tol = 0.5 * atr_val
    # 單一區間的最大寬度。原本只用 2×ATR，但 ATR 是絕對值 ——
    # 1,675 元、ATR 90 的台達電會合出 1627–1807 這種 11% 寬的「區間」，
    # 畫在圖上就是一大片紅，看不出支撐壓力在哪（Andy 2026-09-12 回報「SMC 圖太奇怪」）。
    # 改成同時受 ATR 與「佔價格的百分比」約束，並給低價股一個下限。
    max_width = max(close * MIN_ZONE_PCT / 100, min(2.0 * atr_val, close * MAX_ZONE_PCT / 100))
    for c in cands:
        if merged and c["low"] <= merged[-1]["high"] + tol and \
                (max(merged[-1]["high"], c["high"]) - min(merged[-1]["low"], c["low"])) <= max_width:
            m = merged[-1]
            m["low"], m["high"] = min(m["low"], c["low"]), max(m["high"], c["high"])
            m["score"] += c["weight"] * (decay ** c["age"])
            m["sources"].append(c["kind"])
            if c.get("at") and (m["at"] is None or c["at"] < m["at"]):
                m["at"] = c["at"]
        else:
            merged.append({"low": c["low"], "high": c["high"],
                           "score": c["weight"] * (decay ** c["age"]),
                           "sources": [c["kind"]], "at": c.get("at")})
    zones = [Zone(m["low"], m["high"], m["score"], sorted(set(m["sources"])), since=m["at"])
             for m in merged if m["score"] >= ZONE_MIN_SCORE and len(set(m["sources"])) >= 2]
    # 依「離現價的距離」排序，不是依分數：停損與目標都要用最近的那個區間。
    # 分數只負責決定要不要顯示（≥3 的門檻）。
    # 用區間中點分類：價格「在區間裡面」是最重要的情境（回檔承接就是這樣），
    # 若用上下緣判斷，跨越現價的區間會兩邊都被丟掉
    demand = _dedup(sorted([z for z in zones if z.mid <= close], key=lambda z: -z.high))
    supply = _dedup(sorted([z for z in zones if z.mid > close], key=lambda z: z.low))
    for z in demand:
        z.kind = "demand"
    for z in supply:
        z.kind = "supply"
    return demand, supply


def _dedup(zones: list[Zone], limit: int = 2) -> list[Zone]:
    """同一側的區間不可以互相重疊 —— 疊在一起畫出來就是一大片色塊。

    合併迴圈只跟「上一個」比，被 max_width 擋下來後開新區間時，
    新區間仍可能跟上一個重疊（1627–1807 與 1762–1935 就是這樣來的）。
    這裡照排序把重疊的後者丟掉，只留離現價較近的那個。
    """
    out: list[Zone] = []
    for z in zones:
        if any(z.low < k.high and z.high > k.low for k in out):
            continue
        out.append(z)
        if len(out) >= limit:
            break
    return out


# ------------------------------------------------------------------ 週線

def weekly_structure(df: pd.DataFrame) -> dict:
    """週線 resample 後用同一套結構判定，只取 trend / ma_align。

    效能：原本第一行是 `df.copy()` —— 為了五個欄位，把整張四十幾欄、
    七百列的指標表整份複製一遍。resample 的 agg 本來就只讀那幾欄，
    所以先挑欄位再 resample 的結果完全相同，只是不用付那份複製的錢。

    `resample("W-FRI")` 本身（約 2.9ms）刻意留著沒換掉：自己算週五分箱標籤再
    groupby 只快 25%，卻等於把 pandas 的分箱語意（closed/label、空箱、時間部分）
    重寫一遍 —— 拿週線多空判定去換這點時間不划算。
    """
    if df.empty or len(df) < 60:
        return {"trend": 0, "ma_align": 0, "weeks": 0}
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    # 直接用 numpy 陣列重建這五欄（比從原表切欄快一倍）：agg 出來的值一樣，
    # 而且後面 market_structure / ma_alignment 本來就會轉成 float64
    idx = pd.DatetimeIndex(pd.to_datetime(df["date"]))
    d = pd.DataFrame({k: df[k].to_numpy(dtype="float64") for k in agg}, index=idx)
    w = d.resample("W-FRI").agg(agg)
    # 等同 dropna(subset=["close"])（丟掉沒有交易的空週），但布林遮罩快四倍。
    # 後面只拿 w 的三個欄位與列數，index 長相無關，所以不再 reset_index()
    w = w[w["close"].notna()]
    if len(w) < 30:
        return {"trend": 0, "ma_align": 0, "weeks": int(len(w))}
    ms = ind.market_structure(w["high"], w["low"], w["close"], lookback=3)
    align = ind.ma_alignment(w["close"], periods=(5, 10, 20))
    return {"trend": int(ms["trend"].iloc[-1]), "ma_align": int(align.iloc[-1]),
            "weeks": int(len(w))}


# ------------------------------------------------------------------ 規則引擎

def evaluate(df: pd.DataFrame, avg_turnover: float | None = None, *, with_checks: bool = False) -> dict:
    """輸入含指標的日線（compute_all 的輸出），回傳判定結果。

    `with_checks=True` 時多回一個 `checks`：A／B 兩套條件**逐條**的成立與否＋實際數字
    （見 `_checks` 的說明）。預設關著，是因為 tests/test_perf_golden.py 釘住了整包輸出，
    多一個鍵就會亮 —— 而這個鍵只是把「本來就算好的中間值」攤開，不影響任何一個判定。
    """
    if df.empty or len(df) < 60:
        return {"verdict": "資料不足", "grade": None, "reasons": ["歷史不足 60 根，無法判定"],
                "stop": None, "tp1": None, "tp2": None, "rr": None, "risk_pct": None,
                "demand": [], "supply": [], "weekly": {"trend": 0}, "exclusions": []}

    last = df.iloc[-1]
    recent = df.tail(20)
    close = float(last["close"])
    atr_val = float(last.get("atr14") or np.nan)
    if not np.isfinite(atr_val) or atr_val <= 0:
        atr_val = close * 0.02
    demand, supply = sr_zones(df, atr_val)
    weekly = weekly_structure(df)

    # ---------------- Step 0 硬性排除
    exclusions = []
    # excl_desc：同一條排除條件的「描述式」版本（帶數字、不用「不要接」這類指示語），
    # 只給 with_checks 的 AI 分析卡用；exclusions 本身的文字被 golden 釘住，不改。
    excl_desc: list[str] = []
    if avg_turnover is not None and avg_turnover < MIN_TURNOVER:
        exclusions.append("日均成交值不到 3,000 萬，流動性不足、出不掉")
        excl_desc.append(f"近 20 日均成交值 {avg_turnover / 1e4:,.0f} 萬，低於 3,000 萬流動性門檻")
    if bool(last.get("limit_up")):
        exclusions.append("今天漲停鎖死，不是自由成交的價格")
        excl_desc.append("今日漲停鎖住，收盤價不是自由成交的價格")
    if last.get("trend") == -1 and last.get("ma_align") == -1 and \
            pd.notna(last.get("ma60")) and close < last["ma60"]:
        exclusions.append("空頭結構、均線空頭排列、又在季線之下 —— 三個都在，不要接")
        excl_desc.append(f"日線空頭結構、均線空頭排列、收盤 {close:,.2f} 低於 MA60 {float(last['ma60']):,.2f}，三項同時成立")
    b20 = last.get("bias20")
    if pd.notna(b20) and b20 > 15:
        exclusions.append(f"20 日乖離 {b20:.0f}%，短線過熱，追進去是幫別人抬轎")
        excl_desc.append(f"20 日乖離 {b20:.1f}%，高於 15% 過熱門檻")
    ap = last.get("atr_pct")
    if pd.notna(ap) and ap > 8:
        exclusions.append(f"日波動 {ap:.1f}% 太大，合理的停損放不下")
        excl_desc.append(f"日波動（ATR／價）{ap:.1f}%，高於 8%，合理停損距離放不下")
    if bool(last.get("sweep_high")) and pd.notna(last.get("osc")) and last["osc"] < 0:
        exclusions.append("剛掃過上方流動性又收回來、動能轉弱，典型誘多")
        excl_desc.append(f"剛掃過前高又收回、MACD 柱 {float(last['osc']):.2f} 為負（誘多型態）")

    # ---------------- 停損 / 目標（先算，A/B 判定要用 RR）
    stop_candidates = []
    if demand:
        stop_candidates.append(demand[0].low)
    # df.tail(60) 原本在這支裡被重算五次、swing_high 的遮罩被算三次，
    # 全部收斂成算一次（切片與遮罩都是純讀取，結果完全相同）
    sl = df.tail(60)
    sl_swing_low = sl["swing_low"].fillna(False)
    sl_swing_high = sl["swing_high"].fillna(False)
    sw = sl["low"][sl_swing_low]
    if len(sw):
        stop_candidates.append(float(sw.iloc[-1]))
    ob = sl["ob_bottom"][sl["ob_bull"].fillna(False)].dropna()
    if len(ob):
        stop_candidates.append(float(ob.iloc[-1]))
    stop_raw = min(stop_candidates) if stop_candidates else close - 2 * atr_val
    stop = stop_raw - 0.5 * atr_val

    # 突破型態另算一個停損：放在被突破的前高下方（允許小幅回測），
    # 而不是箱型底 —— 突破失敗的定義是「跌回箱型裡」，不是「跌到箱型底」
    sw_hi = sl["high"][sl_swing_high]
    prev_high_pre = float(sw_hi.max()) if len(sw_hi) else np.nan
    stop_breakout = (prev_high_pre - 0.75 * atr_val) if (np.isfinite(prev_high_pre) and close > prev_high_pre) else None
    risk_pct = (close - stop) / close * 100 if close else np.nan
    if risk_pct < MIN_RISK_PCT:
        stop = close * (1 - MIN_RISK_PCT / 100)
        risk_pct = MIN_RISK_PCT
    if supply:
        tp1 = supply[0].low
    else:
        # 上方沒有供給區 = 正在創高。用測量目標：突破前 60 根的箱型高度往上投射；
        # 箱型算不出來就退回 3×ATR
        # 箱型高度看突破前 120 根：只看 60 根常常只涵蓋盤整的一半，目標會低估
        pre = df.iloc[-125:-5] if len(df) > 125 else df.iloc[:-5]
        box_h = float(pre["high"].max() - pre["low"].min()) if len(pre) >= 20 else np.nan
        base_lvl = float(df.tail(120)["high"].iloc[:-5].max()) if len(df) > 5 else close
        tp1 = (max(base_lvl, close) + box_h) if (np.isfinite(box_h) and box_h > 0) \
            else close + 3 * atr_val
    if tp1 <= close:
        tp1 = close + 3 * atr_val
    tp2 = close + 2.5 * (close - stop)
    rr = (tp1 - close) / (close - stop) if close > stop else np.nan

    # ---------------- Step 1 型態
    in_demand = bool(demand) and (demand[0].low <= close <= demand[0].high + 0.5 * atr_val)
    choch_up = bool(((recent["choch"].fillna(False)) & (recent["trend"] == 1)).any())
    trend_up = last.get("trend") == 1 or choch_up
    above_ma60 = pd.notna(last.get("ma60")) and pd.notna(last.get("ma20")) and \
        close > last["ma60"] and last["ma20"] > last["ma60"]
    k, d = last.get("k"), last.get("d")
    kd_cross_low = pd.notna(k) and pd.notna(d) and k > d and k < 50
    osc_turn = len(df) > 1 and pd.notna(last.get("osc")) and pd.notna(df["osc"].iloc[-2]) \
        and df["osc"].iloc[-2] <= 0 < last["osc"]
    sweep_low = bool(last.get("sweep_low"))
    trigger = kd_cross_low or osc_turn or sweep_low
    zone_ok = bool(demand) and demand[0].score >= ZONE_MIN_SCORE

    # 專家規格寫 3 根；實測突破後續漲幾天、乖離仍小的情況很常見，放寬到 5 根，
    # 追高的風險交給 bias20 ≤ 8 那條去擋
    t5 = df.tail(5)
    # 從箱型或空頭結構直接向上突破，SMC 記成 CHoCH 而非 BOS —— 兩種都是突破，都收
    bos_up = bool(((t5["bos"].fillna(False) | t5["choch"].fillna(False)) & (t5["trend"] == 1)).any())
    vol_ratio = last.get("vol_ratio")
    vol_ok = pd.notna(vol_ratio) and vol_ratio >= 1.5
    # 這裡原本寫成「有擺動高點就取 tail(60) 的擺動高點最大值」，
    # 跟上面 prev_high_pre 是字面上同一個算式（len(sw_hi) > 0 ⟺ 遮罩 .any()），
    # 所以直接沿用，不必再切一次表
    prev_high = prev_high_pre
    breakout = pd.notna(prev_high) and close > prev_high
    bias_ok_b = pd.notna(b20) and b20 <= 8

    rr_b, risk_b = rr, risk_pct
    if stop_breakout is not None and stop_breakout < close:
        risk_b = (close - stop_breakout) / close * 100
        rr_b = (tp1 - close) / (close - stop_breakout)

    a_conditions = [trend_up, above_ma60, in_demand, zone_ok, trigger, rr >= 1.8]
    a_rr, a_risk, a_stop = rr, risk_pct, stop          # 給 _checks 用：B 級成立時下面會改寫這三個
    b_conditions = [bos_up, vol_ok, breakout, bias_ok_b, rr_b >= 2.0]

    reasons: list[str] = []
    if exclusions:
        grade, verdict = None, "不要碰"
        reasons = exclusions[:3]
    elif all(a_conditions) and risk_pct <= MAX_RISK_PCT:
        grade, verdict = "A", "可以分批進場（回檔承接）"
        z = demand[0]
        reasons.append(f"價格回到 {z.low:.1f}–{z.high:.1f} 的需求區，這個區間同時是"
                       f"{'、'.join(z.sources[:3])}，不是單一來源")
        if choch_up:
            reasons.append("近 20 根內出現 CHoCH，空方結構已被破壞、轉為多頭結構")
        elif trend_up:
            reasons.append("多頭結構未被破壞，這是趨勢中的回檔而不是反轉")
        if sweep_low:
            reasons.append("昨天盤中破了前低但收盤收回，是洗掉停損的假跌破")
        elif kd_cross_low:
            reasons.append(f"KD 在低檔剛黃金交叉（K={k:.0f}），還沒漲多")
        elif osc_turn:
            reasons.append("MACD 柱由負轉正，動能剛翻多")
    elif all(b_conditions) and risk_b <= MAX_RISK_PCT:
        grade, verdict = "B", "突破可追，但要控量"
        stop, risk_pct, rr = stop_breakout, risk_b, rr_b
        tp2 = close + 2.5 * (close - stop)
        reasons.append(f"近 5 根內收盤突破前波高點 {prev_high:.1f}，結構向上突破（BOS）")
        reasons.append(f"量比 {vol_ratio:.1f} 倍，是帶量突破不是無量假突破")
        reasons.append(f"20 日乖離 {b20:.1f}%，還沒漲過頭")
    elif last.get("trend") == -1 and pd.notna(last.get("osc")) and last["osc"] < 0 \
            and pd.notna(k) and pd.notna(d) and k < d:
        grade, verdict = None, "不要碰"
        reasons.append("空頭結構、MACD 柱為負、KD 死叉，三個方向都向下")
    else:
        grade, verdict = None, "觀望"
        met_a = sum(bool(x) for x in a_conditions)
        met_b = sum(bool(x) for x in b_conditions)
        if met_a >= 4:
            missing = []
            if not in_demand:
                missing.append("價格還沒回到需求區")
            if not trigger:
                missing.append("還沒出現確認訊號（KD 低檔金叉 / MACD 翻正 / 假跌破）")
            if rr < 1.8:
                missing.append(f"風報比只有 {rr:.1f}，不划算")
            reasons.append("回檔承接的條件快齊了，缺：" + "；".join(missing[:2]))
        elif met_b >= 3:
            reasons.append("有突破跡象但量能或位置不夠乾淨，等回測確認")
        else:
            reasons.append("多空條件都不完整，沒有明確的優勢，先看")
        if risk_pct > MAX_RISK_PCT:
            reasons.append(f"合理停損要放到 {risk_pct:.0f}% 之外，風險太大 —— 不縮停損去湊")

    # ---------------- 週線衝突
    weekly_note = None
    if grade in ("A", "B"):
        if weekly["trend"] == -1:
            grade, verdict = None, "觀望（逆勢反彈，只能短打）"
            weekly_note = "週線仍是空頭結構，日線的多頭訊號只能當反彈看，目標只取 TP1"
            tp2 = tp1
        elif weekly["trend"] == 1:
            weekly_note = "週線同向多頭，日線訊號可信度較高"
    elif verdict == "觀望" and weekly["trend"] == 1 and last.get("trend") != -1:
        weekly_note = "週線多頭未變，回檔中 —— 等日線回到週線需求區再看"

    risk_text = (f"停損 {stop:.1f}（跌破代表這個區間失守），風險 {risk_pct:.1f}%，"
                 f"到 {tp1:.1f} 約 {rr:.1f} 倍風報比") if np.isfinite(rr) else None
    invalid = "跌破停損" if grade else None

    checks = None
    if with_checks:
        # ⚠ 這裡用的 rr_a／risk_a 是「回檔承接」那一套的原值：上面 B 級成立時會把
        #   stop／risk_pct／rr 換成突破停損的版本，所以要在換之前另外留一份（見下方 a_rr）。
        checks = _checks(
            close=close, last=last, demand=demand, atr_val=atr_val,
            trend_up=trend_up, choch_up=choch_up, above_ma60=above_ma60, in_demand=in_demand,
            zone_ok=zone_ok, kd_cross_low=kd_cross_low, osc_turn=osc_turn, sweep_low=sweep_low,
            prev_osc=(float(df["osc"].iloc[-2]) if len(df) > 1 and pd.notna(df["osc"].iloc[-2]) else None),
            rr_a=a_rr, risk_a=a_risk, stop_a=a_stop, bos_up=bos_up, vol_ratio=vol_ratio,
            breakout=breakout, prev_high=prev_high, b20=b20, rr_b=rr_b, risk_b=risk_b,
            stop_b=stop_breakout, excl_desc=excl_desc, ap=ap,
            met_a=sum(bool(x) for x in a_conditions), met_b=sum(bool(x) for x in b_conditions))

    out = {
        "verdict": verdict, "grade": grade, "reasons": reasons[:3],
        "risk_text": risk_text, "invalidation": invalid, "weekly_note": weekly_note,
        "stop": round(float(stop), 2), "tp1": round(float(tp1), 2), "tp2": round(float(tp2), 2),
        "rr": round(float(rr), 2) if np.isfinite(rr) else None,
        "risk_pct": round(float(risk_pct), 2) if np.isfinite(risk_pct) else None,
        "demand": [{"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 2),
                    "sources": z.sources, "since": z.since,
                    "width_pct": round(z.width_pct, 2)} for z in demand],
        "supply": [{"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 2),
                    "sources": z.sources, "since": z.since,
                    "width_pct": round(z.width_pct, 2)} for z in supply],
        "weekly": weekly, "exclusions": exclusions,
        "signals": {
            "trend": int(last.get("trend") or 0), "ma_align": int(last.get("ma_align") or 0),
            "choch_recent": choch_up, "bos_recent": bos_up, "in_demand": in_demand,
            "kd_cross_low": kd_cross_low, "osc_turn": osc_turn, "sweep_low": sweep_low,
            "vol_ratio": (round(float(vol_ratio), 2) if pd.notna(vol_ratio) else None),
            "bias20": (round(float(b20), 2) if pd.notna(b20) else None),
            "atr_pct": (round(float(ap), 2) if pd.notna(ap) else None),
        },
    }
    if checks is not None:
        out["checks"] = checks
    return out


# ------------------------------------------------------------------ 逐條條件（給「AI 分析」卡）

def _num(x, nd: int = 1) -> str:
    """數字 → 字串（千分位、固定小數）。NaN／None 回「—」，不讓判讀文字出現 nan。"""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    return f"{v:,.{nd}f}" if np.isfinite(v) else "—"


def _px(x) -> str:
    """價格 → 字串：最多兩位小數、去掉尾巴的 0（810.0 → 810、687.85 → 687.85）。
    停損 687.85 用一位小數會印成 687.8／687.9（看浮點誤差），跟卡片上的停損價對不上。"""
    s = _num(x, 2)
    return s.rstrip("0").rstrip(".") if "." in s else s


def _f2(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, 2) if np.isfinite(v) else None


def _checks(*, close, last, demand, atr_val, trend_up, choch_up, above_ma60, in_demand, zone_ok,
            kd_cross_low, osc_turn, sweep_low, prev_osc, rr_a, risk_a, stop_a, bos_up, vol_ratio,
            breakout, prev_high, b20, rr_b, risk_b, stop_b, excl_desc, ap, met_a, met_b) -> dict:
    """把 evaluate 的 A／B 兩套條件逐條攤開：每條 {key, name, ok, text}，text 一定帶實際數字。

    為什麼要有這個（Andy 2026-09-26：「觀望部分需要說明原因」）：
    以前觀望只寫「多空條件都不完整、沒有明顯優勢」—— 到底是哪幾條不完整、差多少，看的人無從得知。
    這裡**不另外判定任何東西**：每一條的 ok 就是 evaluate 裡那個布林值本身（同一個變數傳進來），
    只是補上「為什麼是這個結果」的數字。所以這份清單跟判定結果不可能對不上 ——
    tests/test_technical_rules.py 有一條在驗「ok 的條數＝met_a／met_b」。

    文字一律描述式（「目前…」「需…」），不寫買進／賣出這類指示用語（證券投顧法風險）。
    """
    ma20, ma60 = last.get("ma20"), last.get("ma60")
    k, d = last.get("k"), last.get("d")
    z = demand[0] if demand else None
    trig = bool(kd_cross_low or osc_turn or sweep_low)

    def item(key, name, ok, text):
        return {"key": key, "name": name, "ok": bool(ok), "text": text}

    trend_now = int(last.get("trend") or 0)
    trend_word = {1: "多頭", -1: "空頭"}.get(trend_now, "盤整")
    if choch_up:
        trend_tail = "，近 20 根出現 CHoCH 翻多"
    elif trend_now == 1:
        trend_tail = ""
    else:
        trend_tail = "，近 20 根沒有 CHoCH 翻多"
    if sweep_low:
        trig_text = "假跌破後收回"
    elif kd_cross_low:
        trig_text = f"KD 低檔金叉（K {_num(k)}／D {_num(d)}）"
    elif osc_turn:
        trig_text = f"MACD 柱由 {_num(prev_osc, 2)} 翻正為 {_num(last.get('osc'), 2)}"
    else:
        trig_text = (f"KD K {_num(k)}／D {_num(d)}（需 K＞D 且 K＜50）；"
                     f"MACD 柱 {_num(last.get('osc'), 2)}（前一根 {_num(prev_osc, 2)}，需由負翻正）；沒有假跌破")
    a = [
        item("trend", "日線多頭結構", trend_up, f"日線結構{trend_word}{trend_tail}"),
        item("ma60", "站上季線且 MA20＞MA60", above_ma60,
             f"收盤 {_px(close)}、MA20 {_px(ma20)}、MA60 {_px(ma60)}"
             + ("" if above_ma60 else "（需收盤＞MA60 且 MA20＞MA60）")),
        item("in_demand", "價格回到需求區", in_demand,
             (f"最近需求區 {_px(z.low)}–{_px(z.high)}，現價 {_px(close)}"
              f"（距區間上緣 {_num((close / z.high - 1) * 100)}%）") if z else
             "日線下方沒有通過門檻（≥2 個來源交集）的需求區"),
        item("zone", "需求區多源交集", zone_ok,
             f"需求區分數 {_num(z.score)}（門檻 {ZONE_MIN_SCORE:.1f}），來源 {'、'.join(z.sources[:3])}"
             if z else "沒有可用的需求區"),
        item("trigger", "出現確認訊號", trig, trig_text),
        item("rr", "風報比 ≥ 1.8", np.isfinite(rr_a) and rr_a >= 1.8,
             f"風報比 {_num(rr_a)}（停損 {_px(stop_a)}，門檻 1.8）"),
    ]
    b = [
        item("bos", "近 5 根向上突破結構", bos_up,
             "近 5 根出現向上 BOS／CHoCH" if bos_up else "近 5 根沒有向上 BOS／CHoCH"),
        item("vol", "量比 ≥ 1.5", pd.notna(vol_ratio) and vol_ratio >= 1.5,
             f"量比 {_num(vol_ratio, 2)}（需 ≥ 1.5）"),
        item("breakout", "收盤站上前波高點", breakout,
             f"收盤 {_px(close)}，近 60 根前波高點 {_px(prev_high)}"),
        item("bias", "20 日乖離 ≤ 8%", pd.notna(b20) and b20 <= 8,
             f"20 日乖離 {_num(b20, 2)}%（需 ≤ 8%）"),
        item("rr_b", "突破停損下風報比 ≥ 2", np.isfinite(rr_b) and rr_b >= 2.0,
             f"風報比 {_num(rr_b)}（門檻 2.0）"),
    ]
    risk = {
        "a": {"ok": bool(np.isfinite(risk_a) and risk_a <= MAX_RISK_PCT), "pct": _f2(risk_a),
              "stop": _f2(stop_a), "max": MAX_RISK_PCT,
              "text": f"回檔承接的停損 {_px(stop_a)}，距現價 {_num(risk_a)}%（上限 {MAX_RISK_PCT:.0f}%）"
                      + (f"；日波動 {_num(ap)}%" if pd.notna(ap) else "")},
        "b": {"ok": bool(np.isfinite(risk_b) and risk_b <= MAX_RISK_PCT), "pct": _f2(risk_b),
              "stop": _f2(stop_b), "max": MAX_RISK_PCT,
              "text": (f"突破停損 {_px(stop_b)}，距現價 {_num(risk_b)}%（上限 {MAX_RISK_PCT:.0f}%）"
                       if stop_b is not None else
                       f"沒有被突破的前高可放停損，沿用 {_num(risk_b)}%（上限 {MAX_RISK_PCT:.0f}%）")},
    }
    # 「三個方向都向下」那一條（evaluate 裡 elif 的同一個算式，只用在說明文字，不參與判定）
    osc = last.get("osc")
    bear_ok = bool(trend_now == -1 and pd.notna(osc) and osc < 0 and pd.notna(k) and pd.notna(d) and k < d)
    bear = {"ok": bear_ok,
            "text": f"日線結構{trend_word}、MACD 柱 {_num(osc, 2)}、K {_num(k)}／D {_num(d)}"
                    + ("（三項同時向下）" if bear_ok else "")}
    return {"a": a, "b": b, "risk": risk, "bear": bear, "met_a": int(met_a), "met_b": int(met_b),
            "n_a": len(a), "n_b": len(b), "exclusions": list(excl_desc), "atr": _f2(atr_val)}
