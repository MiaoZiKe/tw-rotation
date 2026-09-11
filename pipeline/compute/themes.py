"""題材資金熱力：每個題材今天吃了多少成交值、佔比變化、法人態度、新聞提及量 → 熱度分數。

與族群（flow.py）刻意不同：題材成員的量能「不拆分」——台積電同時是 AI 伺服器、CoWoS、
矽光子，它的成交值三邊都算完整金額。題材熱度看的是「多少錢在追這個故事」，重複計算是設計。

熱度分數（0–100）：
  40% 成交值佔比 5 日均 相對 60 日均 的變化（z-score）
  25% 今日成交值佔比排名
  20% 三大法人 5 日淨買超（佔成交值）
  15% 近 7 天新聞提及量相對近 60 天的變化
每一項先做 rank 百分位再加權，避免某一項的離群值主導。
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .. import config

log = logging.getLogger(__name__)

THEMES_PATH = config.GROUPS_DIR / "themes.yaml"


def load(path: Path | None = None) -> dict:
    p = path or THEMES_PATH
    if not p.exists():
        return {"meta": {}, "themes": {}}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"meta": {}, "themes": {}}


def membership(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load()
    rows = []
    for tid, t in (cfg.get("themes") or {}).items():
        for code in dict.fromkeys(str(c).strip() for c in (t.get("codes") or [])):
            rows.append({"code": code, "theme_id": tid, "theme_name": t.get("name", tid)})
    return pd.DataFrame(rows)


def _pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True).fillna(0.5)


def build(price: pd.DataFrame, inst: pd.DataFrame | None, news: pd.DataFrame | None,
          names: dict, latest: str, days: int = 60) -> dict:
    cfg = load()
    m = membership(cfg)
    if price is None or price.empty or m.empty:
        return {"date": latest, "themes": [], "series": {}}

    cutoff = (pd.Timestamp(latest) - pd.Timedelta(days=days * 1.6)).date().isoformat()
    px = price[price["date"].astype(str) >= cutoff][["date", "code", "close", "change", "turnover"]].copy()
    px["turnover"] = pd.to_numeric(px["turnover"], errors="coerce").fillna(0)
    px["prev"] = px["close"] - px["change"].fillna(0)
    px["chg_pct"] = np.where(px["prev"] > 0, px["change"] / px["prev"] * 100, np.nan)
    market_total = px.groupby("date")["turnover"].sum()

    tm = px.merge(m, on="code", how="inner")
    if inst is not None and not inst.empty:
        i = inst[inst["date"].astype(str) >= cutoff][["date", "code", "foreign_total", "trust", "dealer"]].copy()
        i["inst_net"] = i[["foreign_total", "trust", "dealer"]].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
        tm = tm.merge(i[["date", "code", "inst_net"]], on=["date", "code"], how="left")
    else:
        tm["inst_net"] = np.nan

    daily = (tm.groupby(["theme_id", "theme_name", "date"])
               .agg(turnover=("turnover", "sum"), chg_pct=("chg_pct", "mean"),
                    inst_net=("inst_net", "sum"), n=("code", "size"))
               .reset_index())
    daily["share"] = daily["turnover"] / daily["date"].map(market_total) * 100
    daily = daily.sort_values(["theme_id", "date"])
    g = daily.groupby("theme_id")
    daily["share5"] = g["share"].transform(lambda s: s.rolling(5, min_periods=2).mean())
    daily["share60"] = g["share"].transform(lambda s: s.rolling(60, min_periods=10).mean())
    daily["share60_sd"] = g["share"].transform(lambda s: s.rolling(60, min_periods=10).std())
    daily["inst5"] = g["inst_net"].transform(lambda s: s.rolling(5, min_periods=1).sum())
    daily["tv5"] = g["turnover"].transform(lambda s: s.rolling(5, min_periods=1).sum())

    today = daily[daily["date"] == latest].copy()
    if today.empty:
        return {"date": latest, "themes": [], "series": {}}
    today["flow_z"] = (today["share5"] - today["share60"]) / today["share60_sd"].replace(0, np.nan)
    # 法人買超佔成交值（張×價 → 這裡 inst 是張數，用成交值近似：張數 × 收盤價 × 1000 太重，直接看張數排名）
    today["inst_ratio"] = today["inst5"]

    # 新聞提及：標題含關鍵字
    news_7, news_60 = {}, {}
    if news is not None and not news.empty:
        n = news.copy()
        n["date"] = n["date"].astype(str)
        d7 = (pd.Timestamp(latest) - pd.Timedelta(days=7)).date().isoformat()
        d60 = (pd.Timestamp(latest) - pd.Timedelta(days=60)).date().isoformat()
        titles = (n["title"].fillna("") + " " + n.get("keywords", pd.Series([""] * len(n))).fillna("").astype(str))
        for tid, t in (cfg.get("themes") or {}).items():
            kws = [k for k in (t.get("keywords") or []) if k]
            if not kws:
                continue
            hit = titles.str.contains("|".join(map(__import__("re").escape, kws)), regex=True)
            news_7[tid] = int((hit & (n["date"] >= d7)).sum())
            news_60[tid] = int((hit & (n["date"] >= d60)).sum())
    today["news7"] = today["theme_id"].map(news_7).fillna(0)
    today["news60"] = today["theme_id"].map(news_60).fillna(0)
    today["news_ratio"] = today["news7"] / (today["news60"] / 60 * 7).replace(0, np.nan)

    score = (0.40 * _pct_rank(today["flow_z"]) + 0.25 * _pct_rank(today["share"])
             + 0.20 * _pct_rank(today["inst_ratio"]) + 0.15 * _pct_rank(today["news_ratio"].fillna(1.0)))
    today["heat"] = (score * 100).round(0)

    # 成員（今日）
    day = tm[tm["date"] == latest]
    members = {}
    for tid, gg in day.groupby("theme_id"):
        gg = gg.sort_values("turnover", ascending=False)
        members[tid] = [{"code": r.code, "name": names.get(r.code, r.code),
                         "chg_pct": (round(float(r.chg_pct), 2) if pd.notna(r.chg_pct) else None),
                         "turnover": float(r.turnover),
                         "inst_net": (float(r.inst_net) if pd.notna(r.inst_net) else None)}
                        for r in gg.itertuples()]

    def _v(x, nd=2):
        try:
            v = float(x)
            return round(v, nd) if np.isfinite(v) else None
        except (TypeError, ValueError):
            return None

    out = []
    for r in today.sort_values("heat", ascending=False).itertuples():
        t = cfg["themes"].get(r.theme_id, {})
        out.append({
            "id": r.theme_id, "name": r.theme_name, "desc": t.get("desc"),
            "n": int(r.n), "turnover": float(r.turnover), "share": _v(r.share),
            "share5": _v(r.share5), "share60": _v(r.share60), "flow_z": _v(r.flow_z),
            "chg_pct": _v(r.chg_pct), "inst5": _v(r.inst5, 0), "news7": int(r.news7),
            "news60": int(r.news60), "heat": int(r.heat), "members": members.get(r.theme_id, []),
        })

    series = {}
    tail = daily[daily["date"] >= (pd.Timestamp(latest) - pd.Timedelta(days=days)).date().isoformat()]
    for tid, gg in tail.groupby("theme_id"):
        series[tid] = [[str(d), _v(s)] for d, s in zip(gg["date"], gg["share"])]

    return {"date": latest, "themes": out, "series": series,
            "reviewed": (cfg.get("meta") or {}).get("reviewed"),
            "note": "題材成員量能不拆分（一檔可屬多個題材）；熱度＝資金佔比變化、佔比排名、法人 5 日淨買、新聞提及量的加權百分位。"}
