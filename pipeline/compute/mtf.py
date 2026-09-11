"""多週期（MTF）SMC：把 15 分、60 分、4 小時、日、週、月 各算一次結構與支撐壓力區，
再統整成一段「大週期怎麼看、小週期怎麼進」的說明。

技術分析專家的規則：
- 大週期（週 > 日）決定方向，小週期（4H > 1H > 15m）只負責找進場點。
  小週期的多頭結構在大週期空頭裡只是反彈，不是趨勢。
- 每個週期的區間都要通過 technical.sr_zones 的多源交集門檻（score ≥ 3、≥ 2 來源）。
- 「關鍵價位」= 距現價最近的需求區與供給區，各標明來自哪個週期；
  大週期的區間權重高：同一價位若日線與 15 分都有，以日線標示。
- 分 K 只有 Yahoo 給的兩年（60 分）/ 60 天（15 分），樣本不足時該週期就留白，不硬算。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .. import indicators as ind
from . import technical

log = logging.getLogger(__name__)

TF_ORDER = ["15m", "60m", "240m", "1d", "1w", "1M"]
TF_LABEL = {"15m": "15 分", "60m": "1 小時", "240m": "4 小時", "1d": "日線", "1w": "週線", "1M": "月線"}
BIG_TFS = ("1M", "1w", "1d")
SMALL_TFS = ("240m", "60m", "15m")
MIN_BARS = {"15m": 80, "60m": 80, "240m": 60, "1d": 60, "1w": 40, "1M": 24}


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ resample

def resample_daily(daily: pd.DataFrame, rule: str) -> pd.DataFrame:
    """日 K → 週 K（W-FRI）或月 K（MS）。"""
    if daily is None or daily.empty:
        return pd.DataFrame()
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in d:
        agg["volume"] = "sum"
    out = d.set_index("date").resample(rule).agg(agg).dropna(subset=["close"]).reset_index()
    if rule.startswith("W"):
        # 週 K 的日期用該週最後一個交易日，前端才對得上
        last_day = d.set_index("date")["close"].resample(rule).apply(lambda s: s.index.max() if len(s) else pd.NaT)
        out["date"] = last_day.dropna().values[: len(out)]
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out


def resample_intraday(bars: pd.DataFrame, rule: str = "240min") -> pd.DataFrame:
    """60 分 K → 4 小時 K。台股 09:00–13:30，以 09:00 為錨：09:00–13:00 一根、13:00–13:30 一根。"""
    if bars is None or bars.empty:
        return pd.DataFrame()
    d = bars.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True).dt.tz_convert("Asia/Taipei")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = (d.set_index("ts").resample(rule, origin="start_day", offset="9h")
             .agg(agg).dropna(subset=["close"]).reset_index())
    out["ts"] = out["ts"].dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True)
    return out


# ------------------------------------------------------------------ 單一週期

def analyze_tf(bars: pd.DataFrame, tf: str) -> dict | None:
    """回傳該週期的結構、均線排列、需求/供給區。bars 需含 open/high/low/close（date 或 ts）。"""
    if bars is None or len(bars) < MIN_BARS.get(tf, 60):
        return None
    df = bars.copy()
    if "date" not in df.columns and "ts" in df.columns:
        df = df.rename(columns={"ts": "date"})
    cols = ["date", "open", "high", "low", "close"] + (["volume"] if "volume" in df else [])
    try:
        x = ind.compute_all(df[cols], structure_lookback=3 if tf in ("1w", "1M") else 2)
    except Exception as exc:  # noqa: BLE001
        log.debug("%s compute_all 失敗：%s", tf, exc)
        return None
    last = x.iloc[-1]
    close = float(last["close"])
    atr_val = float(last.get("atr14") or np.nan)
    if not np.isfinite(atr_val) or atr_val <= 0:
        atr_val = close * 0.02
    demand, supply = technical.sr_zones(x, atr_val)

    def _z(z):
        return {"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 1),
                "sources": z.sources, "kind": z.kind,
                "dist_pct": round((z.mid / close - 1) * 100, 2)}

    tail = x.tail(60)
    marks = {
        "bos": [str(r["date"]) for _, r in tail[tail["bos"].fillna(False)].iterrows()],
        "choch": [[str(r["date"]), int(r["trend"])] for _, r in tail[tail["choch"].fillna(False)].iterrows()],
        "sweep_low": [str(r["date"]) for _, r in tail[tail["sweep_low"].fillna(False)].iterrows()],
        "sweep_high": [str(r["date"]) for _, r in tail[tail["sweep_high"].fillna(False)].iterrows()],
    }
    return {
        "tf": tf, "label": TF_LABEL.get(tf, tf), "bars": int(len(x)),
        "close": close, "trend": int(last.get("trend") or 0),
        "ma_align": int(last.get("ma_align") or 0),
        "rsi": _f(last.get("rsi14")), "k": _f(last.get("k")), "d": _f(last.get("d")),
        "osc": _f(last.get("osc")), "atr": round(atr_val, 2),
        "demand": [_z(z) for z in demand], "supply": [_z(z) for z in supply],
        "marks": marks,
        "last_bar": str(x["date"].iloc[-1]),
    }


# ------------------------------------------------------------------ 統整

def _trend_word(t: int) -> str:
    return {1: "多頭", -1: "空頭"}.get(t, "盤整")


def synthesize(per_tf: dict[str, dict], close: float) -> dict:
    """把各週期結論合成：大週期方向、小週期狀態、關鍵價位、操作腳本。"""
    have = {tf: v for tf, v in per_tf.items() if v}
    if not have:
        return {"big_trend": 0, "small_trend": 0, "headline": "資料不足，無法做多週期判定",
                "script": [], "key_levels": {"support": [], "resistance": []}, "tf_used": []}

    def _first(tfs):
        for tf in tfs:
            if tf in have:
                return tf, have[tf]
        return None, None

    big_tf, big = _first(("1w", "1d", "1M"))
    small_tf, small = _first(("60m", "240m", "15m"))
    no_intraday = small is None
    if no_intraday and big_tf == "1w" and "1d" in have:
        # 還沒有分 K：用「週線 vs 日線」當大小週期，不要假裝有小週期
        small_tf, small = "1d", have["1d"]
    big_t = big["trend"] if big else 0
    small_t = small["trend"] if small else 0

    # 關鍵價位：各週期最近的需求/供給，依距離排序，大週期優先去重
    sup, res = [], []
    for tf in ("1M", "1w", "1d", "240m", "60m", "15m"):
        v = have.get(tf)
        if not v:
            continue
        for z in v["demand"][:1]:
            sup.append({**z, "tf": tf, "label": TF_LABEL[tf]})
        for z in v["supply"][:1]:
            res.append({**z, "tf": tf, "label": TF_LABEL[tf]})

    def _dedupe(items, key):
        out = []
        for it in sorted(items, key=key):
            if any(abs(it["low"] - o["low"]) / max(close, 1e-9) < 0.01 for o in out):
                continue
            out.append(it)
        return out[:4]

    sup = _dedupe(sup, key=lambda z: -z["high"])           # 最靠近現價的支撐在前
    res = _dedupe(res, key=lambda z: z["low"])             # 最靠近現價的壓力在前

    big_word, small_word = _trend_word(big_t), _trend_word(small_t)
    big_label = TF_LABEL.get(big_tf, "大週期") if big_tf else "大週期"
    small_label = TF_LABEL.get(small_tf, "小週期") if small_tf else "小週期"

    script = []
    if big_t > 0 and small_t > 0:
        headline = f"{big_label}{big_word}、{small_label}同步{small_word}：順勢，等小週期回測需求區再承接"
        if sup:
            script.append(f"進場：價格回到 {sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']}，"
                          f"且 15 分或 1 小時出現 CHoCH 翻多再進")
        if res:
            script.append(f"目標：先看 {res[0]['label']} 供給區 {res[0]['low']}–{res[0]['high']}")
        script.append("失效：小週期跌破最近需求區下緣且 4 小時結構轉空")
    elif big_t > 0 and small_t <= 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：大方向沒變，小週期在修正，不追高、等修正結束"
        if sup:
            script.append(f"觀察：{sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']} 是否守住")
        script.append("進場條件：小週期先出現 BOS 或 CHoCH 翻多，再回測不破才進")
        script.append("失效：日線需求區失守，改看空頭腳本")
    elif big_t < 0 and small_t > 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：只是反彈，接近大週期供給區要減碼"
        if res:
            script.append(f"反彈上限：{res[0]['label']} 供給區 {res[0]['low']}–{res[0]['high']}")
        script.append("除非日線或週線出現 CHoCH 翻多，否則不做趨勢單")
    elif big_t < 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：空頭，觀望"
        if sup:
            script.append(f"下方觀察：{sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']}，跌破後才有掃蕩反轉機會")
        script.append("轉多條件：週線或日線 CHoCH + 站回 MA20 且量能放大")
    else:
        headline = f"{big_label}盤整：區間操作，需求區進、供給區出，沒有趨勢單"
        if sup and res:
            script.append(f"區間：{sup[0]['low']}–{res[0]['high']}（{sup[0]['label']} 需求 / {res[0]['label']} 供給）")
        script.append("突破區間並在小週期回測確認後，再依突破方向操作")

    if no_intraday:
        script.append("分 K（15 分 / 1 小時 / 4 小時）尚未取得，小週期暫以日線代替；分 K 於每日盤後由 Yahoo 補入")
    return {
        "big_tf": big_tf, "small_tf": small_tf, "no_intraday": no_intraday,
        "big_trend": big_t, "small_trend": small_t,
        "headline": headline, "script": script,
        "key_levels": {"support": sup, "resistance": res},
        "tf_used": [tf for tf in TF_ORDER if tf in have],
        "per_tf": {tf: {"trend": v["trend"], "ma_align": v["ma_align"], "rsi": v["rsi"]}
                   for tf, v in have.items()},
    }


def build(daily: pd.DataFrame, m60: pd.DataFrame | None, m15: pd.DataFrame | None) -> dict:
    """輸入日 K 與（可選）60 分 / 15 分 K，輸出各週期分析 + 統整。"""
    per_tf: dict[str, dict | None] = {}
    per_tf["1d"] = analyze_tf(daily, "1d")
    per_tf["1w"] = analyze_tf(resample_daily(daily, "W-FRI"), "1w")
    per_tf["1M"] = analyze_tf(resample_daily(daily, "MS"), "1M")
    if m60 is not None and not m60.empty:
        per_tf["60m"] = analyze_tf(m60, "60m")
        per_tf["240m"] = analyze_tf(resample_intraday(m60, "240min"), "240m")
    if m15 is not None and not m15.empty:
        per_tf["15m"] = analyze_tf(m15, "15m")
    close = float(daily["close"].iloc[-1])
    return {"tf": {k: v for k, v in per_tf.items() if v}, "summary": synthesize(per_tf, close)}
