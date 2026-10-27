"""第七輪 b：用修正後的「當時流動性前 500 檔」法人資料（inst_daily@pit，main 已補齊）重驗法人籌碼家族，
並測「法人當第二條件」（營收動能＋近 52 週新高 >= 85%＋法人）。

規則：lab7 的六個家族與網格一字不改，只換資料；訓練窗、入選規則、保留窗都照第七輪原協議。
2019～2022 與 2023 年起第七輪已經跑過（保留窗已被看過），本輪再跑一次只能當描述，不是乾淨證據。
法人第二條件的訓練期只用 2016-12-12～2018-12-31（第八輪協議）。研究用，非買賣建議；不下單。
試驗數：第八輪累計 1,474 組；本輪重跑 lab7 的 288 組（新資料上的再評估，保守地全部再計一次）＋ 4 組新增變體。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import factor_lab as FL  # noqa: E402
from pipeline.compute import lab7 as L7  # noqa: E402
from pipeline.compute import rev_lab8 as R8  # noqa: E402
from pipeline.compute import swing_lab5 as S  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round7b"
PRIOR_TRIALS = 1474
NEW_TRIALS = 288 + 4
INST_VARIANTS = {            # 法人第二條件（全部疊在 rv312>1、站上 20/60/120 日線、近 52 週新高 >= 85% 之上）
    "nh85（參照，無法人）": {},
    "nh85＋inst5（近5日每日三大法人皆買超）": {"ge": {"inst5": 1}},
    "nh85＋it20>0（近20日三大法人淨買超）": {"gt": {"it20": 0.0}},
    "nh85＋fi60>0（近60日外資淨買超）": {"gt": {"fi60": 0.0}},
    "nh85＋ti20>0（近20日投信淨買超）": {"gt": {"ti20": 0.0}},
}


def part_a_b():
    """第七輪原協議，只換資料。"""
    L7.OUT = OUT
    P, reg, fin, rows = L7.main7()                       # 訓練 2012-04～2018-12；入選者各池開一次保留窗
    L7.coverage_table(P).to_csv(OUT / "coverage_after.csv", index=False, encoding="utf-8-sig")
    return P, reg, fin, rows


def add_inst_feats(P):
    idx, cols, ci = P["idx"], P["cols"], P["ci"]
    idf = S._rd("inst_daily", ["date", "code", "foreign_total", "trust", "inst_total"])
    idf = idf[idf["code"].isin(ci)].drop_duplicates(["date", "code"])
    idf["date"] = pd.to_datetime(idf["date"])
    pv = lambda c: idf.pivot(index="date", columns="code", values=c).reindex(index=idx, columns=cols)   # noqa: E731
    tr_, fo_, it_ = pv("trust"), pv("foreign_total"), pv("inst_total")
    V = pd.DataFrame(P["V"], index=idx, columns=cols).fillna(0)
    v20, v60 = V.rolling(20).sum().replace(0, np.nan), V.rolling(60).sum().replace(0, np.nan)
    has = (it_.notna().rolling(60, min_periods=1).max() > 0).to_numpy()          # 沒資料的股票是缺值，不當 0
    f = lambda a: np.where(has, a.to_numpy(), np.nan)                           # noqa: E731
    P["ff"]["it20"] = f(it_.fillna(0).rolling(20).sum() / v20)
    P["ff"]["fi60"] = f(fo_.fillna(0).rolling(60).sum() / v60)
    P["ff"]["ti20"] = f(tr_.fillna(0).rolling(20).sum() / v20)
    return P


def inst_spec(extra):
    sp = R8.make_spec(x2="nh85")
    for k, v in extra.items():
        sp[k] = dict(sp.get(k, {}), **v)
    sp["axes"] = dict(sp["axes"], x2="nh85+" + ",".join(a for d in extra.values() for a in d))
    return sp


def part_c():
    P = add_inst_feats(R8.add_features8(FL.load_all()))
    rows = []
    for nm, ex in INST_VARIANTS.items():
        sp = inst_spec(ex)
        for pool in (200, 100):
            for win, (lo, hi) in (("訓練 2016-12～2018", R8.TRAIN8), ("2019-2022（已被看過）", FL.INNER), ("2023-2026（已被看過）", FL.FINAL)):
                m = R8.mrow(P, sp, pool, lo, hi)
                rows.append(dict(變體=nm, 池=pool, 窗=win, 年化=m["cagr"], 年化0050=m["bh"], 超額pt=m["excess"] * 100, 最大回撤=m["mdd"],
                                 逐年贏=f"{m['ywin']}/{m['ynum']}", 平均曝險=m["expo"], 換手=m["turn"]))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "inst_second_condition.csv", index=False, encoding="utf-8-sig")
    return P, df


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("ab", "all"):
        part_a_b()
    if which in ("c", "all"):
        part_c()
