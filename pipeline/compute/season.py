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


def benchmark_monthly(price: pd.DataFrame, intl: pd.DataFrame | None,
                      need: "pd.PeriodIndex | None" = None) -> tuple[pd.Series, str]:
    """大盤月報酬，回傳 (序列, 來源說明)。

    ★ 2026-09-19（Andy 圖三「超額 & 絕對報酬沒變化」）：這裡本來只找 TAIEX / ^TWII，
      但資料湖裡**根本沒有那麼長的大盤歷史** —— `index_ohlc` 只有 2026-08 起的 32 天，
      而且代號是 TSE/OTC/FUT，不是 TAIEX；`^TWII` 也只有 12 個月。
      結果是超額報酬 312 格裡 **0 格算得出來**，前端發現全空就靜靜退回絕對報酬，
      使用者切換兩個指標看起來「完全沒變化」。

      所以加第三條路：**全市場等權月報酬**（拿 price 裡所有股票算）。
      這比硬湊加權指數更對 —— 族群月報酬本來就是**等權**算的，
      用等權市場當基準才是同口徑比較（拿等權族群去減市值加權指數，
      差出來的有一大塊是「大型股 vs 中小型股」而不是族群本身的強弱）。

    `need` 是「希望覆蓋到的月份」；指數來源覆蓋不到八成就改用全市場等權。
    """
    def _cover(m: pd.Series) -> float:
        if need is None or not len(need) or m.empty:
            return 1.0 if not m.empty else 0.0
        return float(len(set(m.index) & set(need))) / max(1, len(need))

    best, label = pd.Series(dtype=float), ""
    for code in BENCH_CODES:
        sub = price[price["code"] == code]
        if not sub.empty:
            m = _monthly_returns(sub)
            if not m.empty:
                best, label = m.set_index("ym")["ret"], f"大盤指數（{code}）"
                break
    if best.empty and intl is not None and not intl.empty and "symbol" in intl.columns:
        sub = intl[intl["symbol"] == "^TWII"][["date", "close"]].copy()
        if not sub.empty:
            sub["code"] = "^TWII"
            m = _monthly_returns(sub)
            if not m.empty:
                best, label = m.set_index("ym")["ret"], "大盤指數（^TWII）"
    if _cover(best) >= 0.8:
        return best, label
    # 指數歷史不夠長 → 用全市場等權月報酬，並且**明講**基準換了
    allm = _monthly_returns(price)
    if allm.empty:
        return best, label or "（沒有可用的大盤基準）"
    eq = allm.groupby("ym")["ret"].mean()
    short = f"（指數只有 {len(best)} 個月，不夠比）" if len(best) else "（資料湖沒有大盤指數歷史）"
    return eq, "全市場等權月報酬" + short


def span_months(first, last) -> int:
    """視窗涵蓋幾個月（頭尾都算）：2023-09～2026-08 → 36。

    用首尾月份相減，不數「有資料的月份」—— 中間哪個月整個族群剛好沒報酬時，
    數出來會少一個月，但使用者選的視窗長度並沒有變。空值回 0。
    """
    if first is None or last is None or pd.isna(first) or pd.isna(last):
        return 0
    f, l_ = pd.Period(first, freq="M"), pd.Period(last, freq="M")
    return max(0, (l_ - f).n + 1)


def span_years(first, last) -> int:
    """視窗長度換成「幾年」＝月數 ÷ 12，**四捨五入到整數、.5 進位**（不是銀行家捨入）。

    ★ 2026-09-24 審查員抓到：近 10／5／3 年顯示成「11 年／6 年／4 年」。
      舊寫法是 `year.nunique()`＝橫跨幾個**日曆年** —— 36 個月的滾動視窗
      2023-09～2026-08 碰到 2023、2024、2025、2026 四個年份，就被算成 4 年。
      改成月數 ÷ 12：36 → 3、120 → 10。

    捨入規則：用 floor(月數/12 + 0.5)，所以 6 個月＝1 年（半年進位）、5 個月＝0 年、
    137 個月（11.42）＝11 年、138 個月（11.5）＝12 年。
    Python 內建 round() 是銀行家捨入（round(0.5)=0、round(2.5)=2），
    同樣是「半年」卻有時進有時捨，所以刻意不用。
    滾動視窗本身一定是 12 的倍數（整年）；只有「全部」那一段才會出現零頭。
    """
    m = span_months(first, last)
    return int(np.floor(m / 12 + 0.5)) if m > 0 else 0


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

    need = pd.PeriodIndex(sorted(rets["ym"].unique()), freq="M") if len(rets) else None
    bench, bench_src = benchmark_monthly(price, intl, need)
    rets = rets.merge(m[["code", "group_id", "group_name"]], on="code", how="inner")
    # 族群等權月報酬
    grp = (rets.groupby(["group_id", "group_name", "ym"])["ret"]
               .agg(ret="mean", n="size").reset_index())
    grp["bench"] = grp["ym"].map(bench) if len(bench) else np.nan
    grp["excess"] = grp["ret"] - grp["bench"]
    grp["year"] = grp["ym"].dt.year
    grp["month"] = grp["ym"].dt.month

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
    last_ym = grp["ym"].max()
    for key, years in PERIODS.items():
        # ★ 2026-09-19（Andy「近三年就會只有到當前月份」）：
        #   以前用**日曆年**切（year > last_year - N），近三年＝2024/2025/2026，
        #   而 2026 的 9-12 月還沒發生 → 那四個月只有 2 個樣本，
        #   被下面 n>=3 的門檻擋掉 → 整排留白，看起來像資料壞了。
        #   改成「最近 12xN 個**完整月**」的滾動視窗：每一格剛好 N 個樣本，12 個月全滿。
        sub = grp if years is None else grp[grp["ym"] > last_ym - 12 * years]
        if sub.empty:
            continue
        periods[key] = {
            "from": str(sub["ym"].min()), "to": str(sub["ym"].max()),
            "years": span_years(sub["ym"].min(), sub["ym"].max()),
            "months": span_months(sub["ym"].min(), sub["ym"].max()),
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
        bdf = pd.DataFrame({"ret": b.values, "ym": b.index, "month": b.index.month, "year": b.index.year})
        for key, years in PERIODS.items():
            # ★ 2026-09-24：大盤對照也改成和族群同一個滾動視窗（最近 12×N 個完整月）。
            #   以前這裡還是日曆年切法，族群用 2023-09～2026-08、大盤卻用 2024-01～2026-08，
            #   兩邊不是同一段時間，「族群 vs 大盤」的對照就不成立。
            sub = bdf if years is None else bdf[bdf["ym"] > last_ym - 12 * years]
            for mo, s in sub.groupby("month")["ret"]:
                bench_rows.append({"period": key, "month": int(mo),
                                   "avg_return": round(float(s.mean()), 2),
                                   "win_rate": round(float((s > 0).mean() * 100), 1), "samples": int(len(s))})

    return {
        "periods": periods, "groups": groups, "detail": detail, "benchmark": bench_rows,
        "benchmark_months": int(len(bench)),
        "benchmark_source": bench_src,
        "data_from": str(grp["ym"].min()), "data_to": str(grp["ym"].max()),
        "note": f"族群報酬＝今日成分股等權平均（有生存者偏差）；超額報酬＝族群月報酬 − {bench_src}同月報酬；樣本 < 3 留白。",
    }
