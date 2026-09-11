"""季節性 v3：族群 × 月份 的歷史表現，多個觀察期、相對大盤的超額報酬、逐年明細。

金融專家的口徑：
- 族群月報酬 = 成分股「等權」月報酬平均（不是市值加權，避免被單一大股主導）；
  用今天的成分股回推歷史有生存者偏差，頁面要標示。
- 「超額報酬」= 族群月報酬 − 加權指數同月報酬。長期看台股一直往上，絕對報酬每個月都是正的、
  看不出淡旺季；扣掉大盤之後才看得到「這個族群相對強的月份」。
- 觀察期可切：2000 年起（有多少算多少）、近 10 年、近 5 年、近 3 年。
- 每個格子都給樣本數與勝率；樣本 < 3 留白。
- 當月（尚未結束）不納入統計。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..groups import loader

log = logging.getLogger(__name__)

PERIODS = {"all": None, "10y": 10, "5y": 5, "3y": 3}
BENCH_CODES = ("TAIEX", "^TWII")


def _monthly_returns(price: pd.DataFrame, codes: set[str] | None = None) -> pd.DataFrame:
    """每檔每月報酬（用月末收盤 / 上月末收盤，比月初到月末更接近真實持有）。"""
    df = price[["date", "code", "close"]].copy()
    if codes is not None:
        df = df[df["code"].isin(codes)]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"])
    if df.empty:
        return pd.DataFrame()
    df["ym"] = df["date"].dt.to_period("M")
    last = (df.sort_values("date").groupby(["code", "ym"])["close"].last().reset_index())
    last = last.sort_values(["code", "ym"])
    last["prev"] = last.groupby("code")["close"].shift(1)
    last["prev_ym"] = last.groupby("code")["ym"].shift(1)
    # 上一筆必須是「上個月」，中間停牌或缺資料就不算
    ok = (last["ym"] - 1) == last["prev_ym"]
    last = last[ok & last["prev"].gt(0)].copy()
    last["ret"] = (last["close"] / last["prev"] - 1) * 100
    return last[["code", "ym", "ret"]]


def benchmark_monthly(price: pd.DataFrame, intl: pd.DataFrame | None) -> pd.Series:
    """大盤月報酬：優先用資料湖裡的 TAIEX（FinMind 回補），其次 yfinance 的 ^TWII。"""
    for code in BENCH_CODES:
        sub = price[price["code"] == code]
        if not sub.empty:
            m = _monthly_returns(sub)
            if not m.empty:
                return m.set_index("ym")["ret"]
    if intl is not None and not intl.empty and "symbol" in intl.columns:
        sub = intl[intl["symbol"] == "^TWII"][["date", "close"]].copy()
        if not sub.empty:
            sub["code"] = "^TWII"
            m = _monthly_returns(sub)
            if not m.empty:
                return m.set_index("ym")["ret"]
    return pd.Series(dtype=float)


def build(price: pd.DataFrame, intl: pd.DataFrame | None = None) -> dict:
    if price is None or price.empty:
        return {"periods": {}, "groups": [], "benchmark_months": 0, "note": ""}
    m = loader.membership()
    if m.empty:
        return {"periods": {}, "groups": [], "benchmark_months": 0, "note": ""}
    member_codes = set(m["code"])
    rets = _monthly_returns(price, member_codes)
    if rets.empty:
        return {"periods": {}, "groups": [], "benchmark_months": 0, "note": ""}

    # 排除當月（還沒結束）
    this_month = pd.Timestamp.today().to_period("M")
    rets = rets[rets["ym"] < this_month]

    bench = benchmark_monthly(price, intl)
    rets = rets.merge(m[["code", "group_id", "group_name"]], on="code", how="inner")
    # 族群等權月報酬
    grp = (rets.groupby(["group_id", "group_name", "ym"])["ret"]
               .agg(ret="mean", n="size").reset_index())
    grp["bench"] = grp["ym"].map(bench) if len(bench) else np.nan
    grp["excess"] = grp["ret"] - grp["bench"]
    grp["year"] = grp["ym"].dt.year
    grp["month"] = grp["ym"].dt.month
    last_year = int(grp["year"].max())

    groups = (grp[["group_id", "group_name"]].drop_duplicates()
                 .sort_values("group_name").to_dict("records"))

    def _stats(sub: pd.DataFrame) -> list[dict]:
        rows = []
        for (gid, gname, month), gg in sub.groupby(["group_id", "group_name", "month"]):
            n = int(len(gg))
            ex = gg["excess"].dropna()
            row = {"group_id": gid, "group_name": gname, "month": int(month), "samples": n,
                   "avg_return": None, "median_return": None, "win_rate": None,
                   "avg_excess": None, "excess_win_rate": None, "excess_samples": int(len(ex))}
            if n >= 3:
                row.update({
                    "avg_return": round(float(gg["ret"].mean()), 2),
                    "median_return": round(float(gg["ret"].median()), 2),
                    "win_rate": round(float((gg["ret"] > 0).mean() * 100), 1),
                })
            if len(ex) >= 3:
                row.update({
                    "avg_excess": round(float(ex.mean()), 2),
                    "excess_win_rate": round(float((ex > 0).mean() * 100), 1),
                })
            rows.append(row)
        return rows

    periods = {}
    for key, years in PERIODS.items():
        sub = grp if years is None else grp[grp["year"] > last_year - years]
        if sub.empty:
            continue
        periods[key] = {
            "from": str(sub["ym"].min()), "to": str(sub["ym"].max()),
            "years": int(sub["year"].nunique()),
            "cells": _stats(sub),
        }

    # 逐年明細：每個族群 年×月 的超額報酬（前端點格子下鑽用）
    detail = {}
    for gid, gg in grp.groupby("group_id"):
        piv = gg.pivot_table(index="year", columns="month", values="excess", aggfunc="first")
        detail[gid] = {int(y): {int(mo): (round(float(v), 2) if pd.notna(v) else None)
                                for mo, v in row.items()}
                       for y, row in piv.iterrows()}
    # 大盤本身各月平均（給頁面對照）
    bench_rows = []
    if len(bench):
        b = bench[bench.index < this_month]
        bdf = pd.DataFrame({"ret": b.values, "month": b.index.month, "year": b.index.year})
        for key, years in PERIODS.items():
            sub = bdf if years is None else bdf[bdf["year"] > last_year - years]
            for mo, s in sub.groupby("month")["ret"]:
                bench_rows.append({"period": key, "month": int(mo),
                                   "avg_return": round(float(s.mean()), 2),
                                   "win_rate": round(float((s > 0).mean() * 100), 1), "samples": int(len(s))})

    return {
        "periods": periods, "groups": groups, "detail": detail, "benchmark": bench_rows,
        "benchmark_months": int(len(bench)),
        "data_from": str(grp["ym"].min()), "data_to": str(grp["ym"].max()),
        "note": "族群報酬＝今日成分股等權平均（有生存者偏差）；超額報酬＝族群月報酬 − 加權指數同月報酬；樣本 < 3 留白。",
    }
