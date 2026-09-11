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
MAX_RISK_PCT = 8.0
MIN_RISK_PCT = 2.0


@dataclass
class Zone:
    low: float
    high: float
    score: float
    sources: list[str] = field(default_factory=list)
    kind: str = ""          # demand / supply

    @property
    def mid(self) -> float:
        return (self.low + self.high) / 2


# ------------------------------------------------------------------ 支撐壓力

def _candidates(df: pd.DataFrame, atr_val: float, lookback: int = 120) -> list[dict]:
    """收集各來源的候選區間，每個帶 {low, high, kind, weight, age}。"""
    tail = df.tail(lookback)
    n = len(df)
    close = float(df["close"].iloc[-1])
    out = []

    # Order Block：只留尚未被收盤價穿透的
    for col_flag, col_lo, col_hi, side in (("ob_bull", "ob_bottom", "ob_top", "demand"),
                                            ("ob_bear", "ob_bottom", "ob_top", "supply")):
        if col_flag not in tail:
            continue
        for idx, r in tail[tail[col_flag].fillna(False)].iterrows():
            lo, hi = r[col_lo], r[col_hi]
            if pd.isna(lo) or pd.isna(hi):
                continue
            after = df.loc[idx:]["close"].iloc[1:]
            mitigated = (after < lo).any() if side == "demand" else (after > hi).any()
            if mitigated:
                continue
            out.append({"low": lo, "high": hi, "kind": "OB", "weight": 2.0,
                        "age": n - 1 - df.index.get_loc(idx)})

    # 前波擺動點 ±0.3 ATR
    for col, side in (("swing_low", "demand"), ("swing_high", "supply")):
        if col not in tail:
            continue
        for idx, r in tail[tail[col].fillna(False)].iterrows():
            px = r["low"] if side == "demand" else r["high"]
            out.append({"low": px - 0.3 * atr_val, "high": px + 0.3 * atr_val,
                        "kind": "前波" + ("低點" if side == "demand" else "高點"),
                        "weight": 1.5, "age": n - 1 - df.index.get_loc(idx)})

    # 成交量密集區
    if "volume" in df.columns:
        for vp in ind.volume_profile(df["high"], df["low"], df["volume"], lookback=lookback):
            out.append({"low": vp["low"], "high": vp["high"], "kind": "量能密集",
                        "weight": 1.5, "age": 0})

    # 均線動態帶
    for col in ("ma60", "ma120"):
        v = df[col].iloc[-1] if col in df else np.nan
        if pd.notna(v):
            out.append({"low": v - 0.25 * atr_val, "high": v + 0.25 * atr_val,
                        "kind": col.upper(), "weight": 1.0, "age": 0})

    # 未回補 FVG
    for col_flag, side in (("fvg_bull", "demand"), ("fvg_bear", "supply")):
        if col_flag not in tail:
            continue
        for idx, r in tail[tail[col_flag].fillna(False)].iterrows():
            lo, hi = r["fvg_bottom"], r["fvg_top"]
            if pd.isna(lo) or pd.isna(hi):
                continue
            after = df.loc[idx:]
            filled = (after["low"] <= lo).iloc[1:].any() if side == "demand" \
                else (after["high"] >= hi).iloc[1:].any()
            if filled:
                continue
            out.append({"low": lo, "high": hi, "kind": "FVG", "weight": 0.8,
                        "age": n - 1 - df.index.get_loc(idx)})

    # 整數關卡：現價上下 15% 內的 10/50/100 倍數
    step = 100 if close >= 500 else (50 if close >= 100 else 10)
    lo_bound, hi_bound = close * 0.85, close * 1.15
    k = int(lo_bound // step) * step
    while k <= hi_bound:
        if k > 0:
            out.append({"low": k * 0.997, "high": k * 1.003, "kind": "整數關卡",
                        "weight": 0.5, "age": 0})
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
    # 單一區間最寬 2×ATR：鄰接候選會一路鏈下去，不設上限會合併成一整段走勢
    max_width = 2.0 * atr_val
    for c in cands:
        if merged and c["low"] <= merged[-1]["high"] + tol and \
                (max(merged[-1]["high"], c["high"]) - min(merged[-1]["low"], c["low"])) <= max_width:
            m = merged[-1]
            m["low"], m["high"] = min(m["low"], c["low"]), max(m["high"], c["high"])
            m["score"] += c["weight"] * (decay ** c["age"])
            m["sources"].append(c["kind"])
        else:
            merged.append({"low": c["low"], "high": c["high"],
                           "score": c["weight"] * (decay ** c["age"]),
                           "sources": [c["kind"]]})
    zones = [Zone(m["low"], m["high"], m["score"], sorted(set(m["sources"])))
             for m in merged if m["score"] >= ZONE_MIN_SCORE and len(set(m["sources"])) >= 2]
    # 依「離現價的距離」排序，不是依分數：停損與目標都要用最近的那個區間。
    # 分數只負責決定要不要顯示（≥3 的門檻）。
    # 用區間中點分類：價格「在區間裡面」是最重要的情境（回檔承接就是這樣），
    # 若用上下緣判斷，跨越現價的區間會兩邊都被丟掉
    demand = sorted([z for z in zones if z.mid <= close], key=lambda z: -z.high)[:2]
    supply = sorted([z for z in zones if z.mid > close], key=lambda z: z.low)[:2]
    for z in demand:
        z.kind = "demand"
    for z in supply:
        z.kind = "supply"
    return demand, supply


# ------------------------------------------------------------------ 週線

def weekly_structure(df: pd.DataFrame) -> dict:
    """週線 resample 後用同一套結構判定，只取 trend / ma_align。"""
    if df.empty or len(df) < 60:
        return {"trend": 0, "ma_align": 0, "weeks": 0}
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    w = (d.set_index("date").resample("W-FRI")
          .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                **({"volume": "sum"} if "volume" in d else {})})
          .dropna(subset=["close"]).reset_index())
    if len(w) < 30:
        return {"trend": 0, "ma_align": 0, "weeks": int(len(w))}
    ms = ind.market_structure(w["high"], w["low"], w["close"], lookback=3)
    align = ind.ma_alignment(w["close"], periods=(5, 10, 20))
    return {"trend": int(ms["trend"].iloc[-1]), "ma_align": int(align.iloc[-1]),
            "weeks": int(len(w))}


# ------------------------------------------------------------------ 規則引擎

def evaluate(df: pd.DataFrame, avg_turnover: float | None = None) -> dict:
    """輸入含指標的日線（compute_all 的輸出），回傳判定結果。"""
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
    if avg_turnover is not None and avg_turnover < MIN_TURNOVER:
        exclusions.append("日均成交值不到 3,000 萬，流動性不足、出不掉")
    if bool(last.get("limit_up")):
        exclusions.append("今天漲停鎖死，不是自由成交的價格")
    if last.get("trend") == -1 and last.get("ma_align") == -1 and \
            pd.notna(last.get("ma60")) and close < last["ma60"]:
        exclusions.append("空頭結構、均線空頭排列、又在季線之下 —— 三個都在，不要接")
    b20 = last.get("bias20")
    if pd.notna(b20) and b20 > 15:
        exclusions.append(f"20 日乖離 {b20:.0f}%，短線過熱，追進去是幫別人抬轎")
    ap = last.get("atr_pct")
    if pd.notna(ap) and ap > 8:
        exclusions.append(f"日波動 {ap:.1f}% 太大，合理的停損放不下")
    if bool(last.get("sweep_high")) and pd.notna(last.get("osc")) and last["osc"] < 0:
        exclusions.append("剛掃過上方流動性又收回來、動能轉弱，典型誘多")

    # ---------------- 停損 / 目標（先算，A/B 判定要用 RR）
    stop_candidates = []
    if demand:
        stop_candidates.append(demand[0].low)
    sl = df.tail(60)
    sw = sl[sl["swing_low"].fillna(False)]["low"]
    if len(sw):
        stop_candidates.append(float(sw.iloc[-1]))
    ob = sl[sl["ob_bull"].fillna(False)]["ob_bottom"].dropna()
    if len(ob):
        stop_candidates.append(float(ob.iloc[-1]))
    stop_raw = min(stop_candidates) if stop_candidates else close - 2 * atr_val
    stop = stop_raw - 0.5 * atr_val

    # 突破型態另算一個停損：放在被突破的前高下方（允許小幅回測），
    # 而不是箱型底 —— 突破失敗的定義是「跌回箱型裡」，不是「跌到箱型底」
    sw_hi = df.tail(60)[df.tail(60)["swing_high"].fillna(False)]["high"]
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
    prev_high = float(df.tail(60)[df.tail(60)["swing_high"].fillna(False)]["high"].max()) \
        if df.tail(60)["swing_high"].fillna(False).any() else np.nan
    breakout = pd.notna(prev_high) and close > prev_high
    bias_ok_b = pd.notna(b20) and b20 <= 8

    rr_b, risk_b = rr, risk_pct
    if stop_breakout is not None and stop_breakout < close:
        risk_b = (close - stop_breakout) / close * 100
        rr_b = (tp1 - close) / (close - stop_breakout)

    a_conditions = [trend_up, above_ma60, in_demand, zone_ok, trigger, rr >= 1.8]
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

    return {
        "verdict": verdict, "grade": grade, "reasons": reasons[:3],
        "risk_text": risk_text, "invalidation": invalid, "weekly_note": weekly_note,
        "stop": round(float(stop), 2), "tp1": round(float(tp1), 2), "tp2": round(float(tp2), 2),
        "rr": round(float(rr), 2) if np.isfinite(rr) else None,
        "risk_pct": round(float(risk_pct), 2) if np.isfinite(risk_pct) else None,
        "demand": [{"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 2),
                    "sources": z.sources} for z in demand],
        "supply": [{"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 2),
                    "sources": z.sources} for z in supply],
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
