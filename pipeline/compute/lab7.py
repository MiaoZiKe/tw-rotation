"""第七輪：法人籌碼家族（＋新高動能與廣度濾網，單檔停損只由訓練期決定），證據協議同第六輪。

資料：inst_daily 2012 起已回補（2012～2015 約 400～460 檔、2016 起約 1600 檔以上）；營收／財報／資產負債表 2012～2015 仍在回補（只有約 110 檔），
所以營收品質家族本輪不跑，等補齊後補跑（見 README）。「外資持股比例」資料湖沒有，改用外資累積買超占成交量的變化當代理。
證據協議：訓練 2012-04～2018-12（家族內搜尋與選參數；2012-01～03 是 60 日暖機）；內部保留 2019～2022（入選者每池只跑一次）；
2023～2026-10 一併列出但**已被前幾輪看過**。試驗數累計：前六輪 858 組 + 本輪新增。
研究用，非買賣建議；不下單；純個股，不持有 0050 或任何 ETF。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import lab6 as L6  # noqa: E402
from pipeline.compute import swing_lab5 as S  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round7"
PRIOR_TRIALS = 858
TRAIN7 = ("2012-04-02", "2018-12-31")
NEW_FAMS = ("trust", "foreign", "instcombo", "instratio", "fchg", "nhinst")
_orig_pick6 = L6.pick6


def add_features7(P):
    idx, cols = P["idx"], P["cols"]
    idf = S._rd("inst_daily", ["date", "code", "foreign_total", "trust", "inst_total"])
    idf = idf[idf["code"].isin(P["ci"])]
    idf["date"] = pd.to_datetime(idf["date"])
    idf = idf.drop_duplicates(["date", "code"])
    has = idf.pivot(index="date", columns="code", values="trust").reindex(index=idx, columns=cols).notna().to_numpy()
    fo = idf.pivot(index="date", columns="code", values="foreign_total").reindex(index=idx, columns=cols).fillna(0)
    it = idf.pivot(index="date", columns="code", values="inst_total").reindex(index=idx, columns=cols).fillna(0)
    V = pd.DataFrame(P["V"], index=idx, columns=cols).fillna(0)
    v20 = V.rolling(20).sum().replace(0, np.nan); v60 = V.rolling(60).sum().replace(0, np.nan); v120 = V.rolling(120).sum().replace(0, np.nan)
    f6 = P["f6"]
    # 沒有法人資料的股票（資料湖只補了部分檔）一律 NaN，不當成 0
    cov = pd.DataFrame(has, index=idx, columns=cols).rolling(60, min_periods=1).max().to_numpy() > 0
    def nanmask(a):
        a = a.to_numpy() if hasattr(a, "to_numpy") else a
        return np.where(cov, a, np.nan)
    f6["it20"] = nanmask(it.rolling(20).sum() / v20)
    f6["fi60"] = nanmask(fo.rolling(60).sum() / v60)
    f6["fi120"] = nanmask(fo.rolling(120).sum() / v120)
    f6["fchg"] = nanmask(fo.rolling(60).sum() / v60 - (fo.rolling(60).sum() / v60).shift(20))
    tr = pd.DataFrame(f6["ti20"], index=idx, columns=cols)
    f6["ti20"] = nanmask(tr)
    f6["streak"] = np.where(cov, f6["streak"], np.nan)
    return P


def pick7(P, spec, t, pool, nret=None):
    fam = spec["fam"]
    if fam not in ("instratio", "fchg", "nhinst", "trust", "foreign", "instcombo"):
        return _orig_pick6(P, spec, t, pool, nret)
    f, f6 = P["f"], P["f6"]
    ok = P["elig"][pool][t].copy() & (P["Cf"][t] > f["ma200"][t])
    rk = L6.rk
    if fam == "instratio":
        ok &= np.isfinite(f6["it20"][t]) & np.isfinite(f["nh"][t])
        sc = rk(f6["it20"][t], ok) + rk(f["nh"][t], ok)
    elif fam == "fchg":
        ok &= np.isfinite(f6["fchg"][t]) & np.isfinite(f6["fi120"][t])
        sc = rk(f6["fchg"][t], ok) + rk(f6["fi120"][t], ok)
    elif fam == "nhinst":
        ok &= np.isfinite(f["nh"][t]) & np.isfinite(f["mom252"][t]) & np.isfinite(f6["ti20"][t]) & np.isfinite(f6["fi60"][t])
        sc = rk(f["nh"][t], ok) + rk(f["mom252"][t], ok) + rk(f6["ti20"][t], ok) + rk(f6["fi60"][t], ok)
    elif fam == "trust":
        ok &= np.isfinite(f6["ti20"][t]) & np.isfinite(f6["streak"][t])
        sc = rk(f6["streak"][t], ok) + rk(f6["ti20"][t], ok)
    elif fam == "foreign":
        ok &= np.isfinite(f6["fi60"][t]) & np.isfinite(f["nh"][t])
        sc = rk(f6["fi60"][t], ok) + rk(f["nh"][t], ok)
    else:   # instcombo
        ok &= np.isfinite(f6["fi60"][t]) & np.isfinite(f6["ti20"][t]) & np.isfinite(f["nh"][t])
        sc = rk(f6["ti20"][t], ok) + rk(f6["fi60"][t], ok) + rk(f["nh"][t], ok)
    ok &= np.isfinite(sc)
    cand = np.where(ok)[0]
    if len(cand) == 0:
        return [], {}
    top = cand[np.argsort(-sc[cand])[:nret or spec["N"]]]
    return list(top), {int(i): float(sc[i]) for i in top}


def batches7():
    B = {}
    names = {"trust": "G1 投信連買", "foreign": "G2 外資買超累積＋新高", "instcombo": "G3 法人組合＋新高", "instratio": "G4 法人買超占成交比＋新高",
             "fchg": "G5 外資持股變化（累積買超變化代理）", "nhinst": "G6 新高動能＋法人（四項排名相加）"}
    for fam, nm in names.items():
        sizes = ("equal", "invvol") if fam in ("instcombo", "nhinst") else ("equal",)
        B[nm] = [dict(fam=fam, N=N, rebal=rb, mf=m, sl=sl, size=sz) for N in (5, 10, 20) for rb in ("M", "Q") for m in ("br200", "faber")
                 for sl in (None, 0.12, 0.20) for sz in sizes]
    return B


def setup(train_lo=TRAIN7[0]):
    L6.pick6 = pick7
    L6.batches6 = batches7
    L6.OUT = OUT
    L6.LOG = OUT / "holdout_log.csv"
    L6.TRAIN = (train_lo, TRAIN7[1])
    L6.FAM_START = {f: train_lo for f in NEW_FAMS}
    L6.MIN_TRAIN_YEARS = 2.5
    OUT.mkdir(parents=True, exist_ok=True)


def main7(tag="", train_lo=TRAIN7[0]):
    """tag='' 為第一次（事先登記的 2012-04 起訓練窗）；tag='_pass2' 為第二次（只用資料覆蓋完整的 2016-04 起）。"""
    setup(train_lo)
    P = S.build_features(S.load5())
    P = add_features7(L6.add_features6(P))
    reg = L6.train_stage(P)
    reg.drop(columns=["yrets", "y0050"]).to_csv(OUT / f"registry_train{tag}.csv", index=False, encoding="utf-8-sig")
    # 全部組合依「離 0050 差幾個百分點」排序（訓練期，兩池取較差者）
    g = reg.pivot_table(index="spec", columns="pool", values="excess").rename(columns={200: "池200超額", 100: "池100超額"})
    g["較差池超額(pt)"] = g.min(axis=1) * 100
    meta = reg.drop_duplicates("spec").set_index("spec")[["batch", "有效濾網", "兩池通過訓練"]]
    rk_ = g.join(meta).sort_values("較差池超額(pt)", ascending=False)
    rk_["訓練期結果"] = np.where(rk_["較差池超額(pt)"] >= 0, "贏 0050（兩池）", "輸 0050，差 " + (-rk_["較差池超額(pt)"]).round(1).astype(str) + " 個百分點")
    rk_.reset_index().to_csv(OUT / f"ranking_train_all{tag}.csv", index=False, encoding="utf-8-sig")
    fin = L6.pick_finalists(reg)
    json.dump(fin, open(OUT / f"finalists{tag}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows = []
    for sp in fin:
        res = {"spec": sp}
        for window, lab in (("內部保留", "內部保留 2019-2022"), ("最終保留", "2023-2026（已被看過）")):
            ms = {pool: L6.holdout(P, sp, pool, window) for pool in (200, 100)}
            for pool, m in ms.items():
                res[f"{lab}_{pool}_年化"] = m["cagr"]; res[f"{lab}_{pool}_0050"] = m["bh"]; res[f"{lab}_{pool}_差pt"] = (m["cagr"] - m["bh"]) * 100
                res[f"{lab}_{pool}_回撤"] = m["mdd"]
            res[f"{lab}_兩池皆贏"] = all(m["cagr"] > m["bh"] for m in ms.values())
        res["冠軍"] = bool(res["內部保留 2019-2022_兩池皆贏"] and res["2023-2026（已被看過）_兩池皆贏"])
        rows.append(res)
    pd.DataFrame(rows).to_csv(OUT / f"finalists_holdout{tag}.csv", index=False, encoding="utf-8-sig")
    return P, reg, fin, rows


if __name__ == "__main__":
    main7()
    main7("_pass2", "2016-04-01")


def coverage_table(P):
    idx = P["idx"]; rows = []
    for pool in (200, 100):
        el = P["elig"][pool]; cov = np.isfinite(P["f6"]["fi60"])
        for y in range(2012, 2023):
            m = idx.year == y
            rows.append(dict(股票池=pool, 年=y, 池內有法人資料的比例=float((el[m] & cov[m]).sum() / el[m].sum())))
    return pd.DataFrame(rows)


def finish7():
    """覆蓋率診斷與入選者交易日誌（含檢討）。"""
    setup()
    P = add_features7(L6.add_features6(S.build_features(S.load5())))
    coverage_table(P).to_csv(OUT / "diagnostics_inst_coverage.csv", index=False, encoding="utf-8-sig")
    logs = []
    for tag in ("", "_pass2"):
        fin = json.load(open(OUT / f"finalists{tag}.json", encoding="utf-8"))
        for sp in fin:
            for pool in (200, 100):
                for window in ("內部保留", "最終保留"):
                    t = L6.trade_log(P, json.loads(sp), pool, window)
                    if len(t):
                        logs.append(t.assign(次=tag or "第一次"))
    pd.concat(logs).drop_duplicates(subset=["spec", "pool", "區間", "code", "entry", "exit"]).to_csv(OUT / "trades_finalists.csv", index=False, encoding="utf-8-sig")
    return P
