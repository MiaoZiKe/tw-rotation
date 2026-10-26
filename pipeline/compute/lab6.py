"""第六輪：先用回測證明能贏 0050（純個股波段，不持有 0050 或任何 ETF，可空手，大盤不對就空手）。

證據標準（事先定，Andy 要求）
  訓練期   2012-01-02 ～ 2018-12-31   搜尋與選參數（所有變體只跑這一段）。資料不足的家族（品質／法人）從資料起點算，並標明。
  內部保留 2019-01-02 ～ 2022-12-30   選完參數後，**每個入選者每個池只跑一次**（holdout_log.csv 記錄，重跑只讀紀錄不重算）。
  最終保留 2023-01-02 ～ 2026-10-22   通過內部保留者才跑，**只跑一次**。
  註：前五輪已經看過 2021 年以後的資料，所以 2023 年起「不是未經窺視」；較乾淨的證據是 2019～2022 內部保留（前五輪的挑選也看過 2019～2020，
  但本輪的選擇只用 2012～2018 做，且選完才解鎖）。這點在 README 明講。
冠軍：(1) 內部保留年化 > 0050 (2) 最終保留年化 > 0050 (3) 訓練期參數鄰域不崩 (4) 前 200／前 100 兩池都成立 (5) 有效大盤濾網。
試驗總數 = 前五輪 612 組 + 本輪新增組數。
研究用，非買賣建議；不下單。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import swing_lab5 as S  # noqa: E402
from pipeline.compute.strategy_lab import FEE, TAX, SLIP, stats  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round6"
TRAIN = ("2012-01-02", "2018-12-31")
INNER = ("2019-01-02", "2022-12-30")
FINAL = ("2023-01-02", "2026-10-22")
FAM_START = {"qgm": "2017-07-03", "qrev": "2018-01-02", "trust": "2016-07-01", "foreign": "2016-07-01", "instcombo": "2016-07-01"}
MIN_TRAIN_YEARS = 2.5
PRIOR_TRIALS = 612


# ------------------------------------------------------------------ 新特徵
def _legal_date(year, q):
    return {1: pd.Timestamp(year=year, month=5, day=15), 2: pd.Timestamp(year=year, month=8, day=14),
            3: pd.Timestamp(year=year, month=11, day=14), 4: pd.Timestamp(year=year + 1, month=3, day=31)}[q]


def add_features6(P):
    idx, cols = P["idx"], P["cols"]
    Cf = pd.DataFrame(P["Cf"], index=idx, columns=cols)
    f6 = {}
    f6["vol"] = (Cf.pct_change().rolling(252, min_periods=200).std() * np.sqrt(252)).to_numpy()
    f6["r20"] = (Cf / Cf.shift(20) - 1).to_numpy()
    f6["r60"] = (Cf / Cf.shift(60) - 1).to_numpy()
    # 營收品質（法定可用日次月 10 日）
    rv = S._rd("revenue_monthly", ["ym", "code", "revenue"]).dropna(subset=["revenue"])
    rv = rv[rv["code"].isin(P["ci"])]
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    yoy = R / R.shift(12).where(R.shift(12) > 0) - 1
    y12, s12 = yoy.rolling(12).mean(), yoy.rolling(12).std()
    avail = yoy.index.to_timestamp() + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)

    def daily(df, av):
        df = df.copy(); df.index = av
        df = df[~df.index.duplicated(keep="last")]
        return df.reindex(df.index.union(idx)).ffill().reindex(idx).reindex(columns=cols).to_numpy()
    f6["yoy12"] = daily(y12, avail)
    f6["stab"] = daily(y12 / (s12 + 0.05), avail)
    # 毛利率（單季，法定公告日）
    fq = S._rd("financial_q", ["year", "quarter", "code", "revenue", "gross_profit"]).dropna()
    fq = fq[(fq["revenue"] > 0) & fq["code"].isin(P["ci"])].sort_values(["code", "year", "quarter"])
    fq["gm"] = fq["gross_profit"] / fq["revenue"]
    fq["gm_yoy"] = fq["gm"] - fq.groupby("code")["gm"].shift(4)
    fq["av"] = [_legal_date(int(y), int(q)) for y, q in zip(fq["year"], fq["quarter"])]
    for nm in ("gm", "gm_yoy"):
        pv = fq.pivot_table(index="av", columns="code", values=nm, aggfunc="last").sort_index()
        f6[nm] = daily(pv, pv.index)
    # 法人（投信連買、投信 20 日買超占成交量、外資 60 日買超占成交量）
    idf = S._rd("inst_daily", ["date", "code", "foreign_total", "trust"])
    idf = idf[idf["code"].isin(P["ci"])]
    idf["date"] = pd.to_datetime(idf["date"])
    tr = idf.drop_duplicates(["date", "code"]).pivot(index="date", columns="code", values="trust").reindex(index=idx, columns=cols).fillna(0)
    fo = idf.drop_duplicates(["date", "code"]).pivot(index="date", columns="code", values="foreign_total").reindex(index=idx, columns=cols).fillna(0)
    V = pd.DataFrame(P["V"], index=idx, columns=cols).fillna(0)
    pos = (tr.to_numpy() > 0)
    st = np.zeros(pos.shape)
    for t in range(1, len(idx)):
        st[t] = (st[t - 1] + 1) * pos[t]
    f6["streak"] = np.minimum(st, 20)
    f6["ti20"] = (tr.rolling(20).sum() / V.rolling(20).sum().replace(0, np.nan)).to_numpy()
    f6["fi60"] = (fo.rolling(60).sum() / V.rolling(60).sum().replace(0, np.nan)).to_numpy()
    f6["has_inst"] = (idx >= "2016-03-01")
    P["f6"] = f6
    return P


def add_clusters(P):
    """機械式分群（滾動殘差相關，只用過去 120 日，每月重分），只對曾進過前 200 檔池的股票分群。"""
    from pipeline.compute import topdown_lab4 as T4
    idx = P["idx"]
    ever = np.where(P["elig"][200].any(axis=0))[0]
    ret = pd.DataFrame(P["Cf"][:, ever], index=idx).pct_change()
    ret = ret.where(pd.DataFrame(P["rawC"][:, ever], index=idx).notna())
    lab_sel = T4.mech_labels(ret, k=25, lookback=120)
    lab = np.full(P["Cf"].shape, -1, int)
    lab[:, ever] = lab_sel
    P["lab"] = lab
    return P


# ------------------------------------------------------------------ 選股
def rk(a, ok):
    s = pd.Series(np.where(ok, a, np.nan)).rank(pct=True)
    return s.to_numpy()


def pick6(P, spec, t, pool, nret=None):
    f, f6 = P["f"], P["f6"]
    ok = P["elig"][pool][t].copy()
    fam = spec["fam"]
    above = P["Cf"][t] > f["ma200"][t]
    if spec.get("above200", True):
        ok &= above
    if fam == "lowvol":
        ok &= np.nan_to_num(f["mom252"][t], nan=-1) > 0
        sc = -f6["vol"][t]
    elif fam == "qrev":
        ok &= np.isfinite(f6["yoy12"][t]) & np.isfinite(f6["stab"][t]) & np.isfinite(f6["vol"][t]) & (f6["yoy12"][t] > 0)
        sc = rk(f6["yoy12"][t], ok) + rk(f6["stab"][t], ok) + rk(-f6["vol"][t], ok)
    elif fam == "qgm":
        ok &= np.isfinite(f6["gm"][t]) & np.isfinite(f6["gm_yoy"][t]) & np.isfinite(f6["stab"][t])
        sc = rk(f6["gm"][t], ok) + rk(f6["gm_yoy"][t], ok) + rk(f6["stab"][t], ok)
    elif fam == "trust":
        ok &= np.isfinite(f6["ti20"][t])
        sc = rk(f6["streak"][t], ok) + rk(f6["ti20"][t], ok)
    elif fam == "foreign":
        ok &= np.isfinite(f6["fi60"][t]) & np.isfinite(f["nh"][t])
        sc = rk(f6["fi60"][t], ok) + rk(f["nh"][t], ok)
    elif fam == "instcombo":
        ok &= np.isfinite(f6["fi60"][t]) & np.isfinite(f6["ti20"][t]) & np.isfinite(f["nh"][t])
        sc = rk(f6["ti20"][t], ok) + rk(f6["fi60"][t], ok) + rk(f["nh"][t], ok)
    elif fam == "lcrev":
        ok &= np.nan_to_num(f["mom252"][t], nan=-1) > 0
        sc = -f6["r20" if spec["rv"] == 20 else "r60"][t]
    elif fam == "cluster":
        mom = f[f"mom{spec['L']}"][t]
        lb = P["lab"][t]
        ok &= (lb >= 0) & np.isfinite(mom)
        cm = np.full(len(mom), np.nan)
        for k in np.unique(lb[ok]):
            m = ok & (lb == k)
            if m.sum() >= 3:
                cm[m] = np.nanmean(mom[m])
        ok &= np.isfinite(cm)
        ex = mom - cm
        sc = ex if spec["mode"] == "within" else rk(cm, ok) + rk(ex, ok)
    elif fam == "nh6":
        ok &= np.isfinite(f["nh"][t]) & np.isfinite(f["mom252"][t])
        sc = rk(f["nh"][t], ok) + rk(f["mom252"][t], ok)
    else:
        raise ValueError(fam)
    ok &= np.isfinite(sc)
    cand = np.where(ok)[0]
    if len(cand) == 0:
        return [], {}
    top = cand[np.argsort(-sc[cand])[:nret or spec["N"]]]
    return list(top), {int(i): float(sc[i]) for i in top}


def _ends(idx, lo_i, hi_i, rebal):
    s = pd.Series(np.arange(len(idx)), index=idx)
    key = {"M": idx.to_period("M"), "Q": idx.to_period("Q"), "H": idx.year * 2 + (idx.month > 6), "Y": idx.year}[rebal]
    last = s.groupby(key).max().to_numpy()
    return [i for i in last if lo_i <= i < hi_i]


# ------------------------------------------------------------------ 引擎（定期換股，含單檔停損與波動調整部位）
def run6(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf = P["O"], P["Cf"]
    sigs = sorted(set([lo_i - 1] + _ends(idx, lo_i, hi_i, spec["rebal"])))
    nxt = {s + 1: s for s in sigs}
    N = spec["N"]
    cash, sh, ent = 1.0, {}, {}
    eq = np.full(len(idx), np.nan); inv = np.zeros(len(idx)); tr = []; buys = 0.0
    pend_stop = {}
    sl = spec.get("sl")
    for t in range(lo_i, hi_i + 1):
        for i in [i for i in pend_stop if i in sh]:
            px = (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) * (1 - SLIP)
            cash += sh[i] * px * (1 - FEE - TAX)
            if trades:
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[t], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason=f"單檔停損（收盤較進場價跌逾 {int(sl*100)}%）", score=ent[i][2]))
            del sh[i]
        pend_stop = {}
        if t in nxt:
            s = nxt[t]
            on = S.mkt_state(P, spec, s, pool)
            if on and spec.get("buf"):
                ranked, scs = pick6(P, spec, s, pool, nret=2 * N)
                keep = [i for i in ranked if i in sh][:N]
                tgt = keep + [i for i in ranked if i not in keep][:N - len(keep)]
            else:
                tgt, scs = pick6(P, spec, s, pool) if on else ([], {})
            tset = set(tgt)
            for i in [i for i in sh if i not in tset]:
                px = (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) * (1 - SLIP)
                cash += sh[i] * px * (1 - FEE - TAX)
                if trades:
                    tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[t], exit_px=px,
                                   ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1,
                                   exit_reason=("大盤濾網關閉，全部出清" if not on else "換股：掉出目標名單"), score=ent[i][2]))
                del sh[i]
            eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
            new = [i for i in tgt if i not in sh and np.isfinite(O[t, i])]
            if spec.get("size") == "invvol" and tgt:
                raw = {i: 1.0 / max(P["f6"]["vol"][s, i], 0.05) for i in tgt if np.isfinite(P["f6"]["vol"][s, i])}
                tot = sum(raw.values()) or 1.0
                wts = {i: (len(tgt) / N) * raw.get(i, tot / len(tgt)) / tot for i in tgt}
            else:
                wts = {i: 1.0 / N for i in tgt}
            for i in new:
                amt = min(cash, eq_open * min(wts[i], 0.35))
                if amt <= 0:
                    continue
                px = O[t, i] * (1 + SLIP)
                sh[i] = amt / (px * (1 + FEE)); cash -= amt; buys += amt
                ent[i] = (t, px, scs.get(int(i), np.nan))
        pv = sum(sh[i] * Cf[t, i] for i in sh)
        eq[t] = cash + pv; inv[t] = pv / eq[t]
        if sl:
            for i in sh:
                if Cf[t, i] < ent[i][1] * (1 - sl):
                    pend_stop[i] = 1
    if sh:
        val = sum(sh[i] * Cf[hi_i, i] for i in sh)
        eq[hi_i] -= val * (SLIP + FEE + TAX)
        if trades:
            for i in sh:
                px = Cf[hi_i, i] * (1 - SLIP)
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[hi_i], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason="窗尾清倉（回測結束）", score=ent[i][2]))
    s_ = pd.Series(eq, index=idx).iloc[lo_i:hi_i + 1]
    yrs = max((s_.index[-1] - s_.index[0]).days / 365.25, 1e-9)
    return dict(eq=s_, trades=pd.DataFrame(tr), turnover=buys / yrs / max(s_.mean(), 1e-9), expo=float(inv[lo_i:hi_i + 1].mean()))


# ------------------------------------------------------------------ 引擎二：Weinstein 階段二突破（長波段）
def run_stage2(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf = P["O"], P["Cf"]
    key = ("s2", spec["slow"])
    cache = P.setdefault("_s2", {})
    if key not in cache:
        wk = idx.to_period("W-FRI")
        last = pd.Series(idx, index=idx).groupby(wk).max()
        wc = pd.DataFrame(Cf, index=idx).groupby(wk).last()
        wc.index = last.reindex(wc.index).values
        ma = wc.rolling(spec["slow"]).mean()
        rising = ma > ma.shift(4)
        stage2 = ((wc > ma) & rising).where(ma.notna()).reindex(idx).ffill()
        weak = (wc < ma).where(ma.notna()).reindex(idx).ffill()
        hh = pd.DataFrame(Cf, index=idx).rolling(150, min_periods=120).max().shift(1).to_numpy()
        vma = pd.DataFrame(P["V"], index=idx).rolling(20).mean().shift(1).to_numpy()
        brk = (np.nan_to_num(P["V"]) > 1.5 * vma) & (Cf > hh)
        cache[key] = ((stage2 == 1).to_numpy() & brk, (weak == 1).to_numpy())
    entm, weak = cache[key]
    K, sl = spec["K"], spec.get("sl")
    cash, sh, ent = 1.0, {}, {}
    eq = np.full(len(idx), np.nan); inv = np.zeros(len(idx)); tr = []; buys = 0.0
    hm = np.zeros(Cf.shape[1], bool); pend_in, pend_out = [], {}
    for t in range(lo_i, hi_i + 1):
        for i, why in list(pend_out.items()):
            px = (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) * (1 - SLIP)
            cash += sh[i] * px * (1 - FEE - TAX)
            if trades:
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[t], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason=why, score=ent[i][2]))
            del sh[i]; hm[i] = False
        pend_out = {}
        eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
        for i, scv in pend_in:
            if i in sh or not np.isfinite(O[t, i]):
                continue
            amt = min(cash, eq_open / K)
            if amt <= 0:
                continue
            px = O[t, i] * (1 + SLIP)
            sh[i] = amt / (px * (1 + FEE)); cash -= amt; ent[i] = (t, px, scv); hm[i] = True; buys += amt
        pend_in = []
        pv = sum(sh[i] * Cf[t, i] for i in sh)
        eq[t] = cash + pv; inv[t] = pv / eq[t]
        if t == hi_i:
            break
        if not S.mkt_state(P, spec, t, pool):
            for i in sh:
                pend_out[i] = "大盤濾網關閉，全部出清"
            continue
        for i in sh:
            if weak[t, i]:
                pend_out[i] = "週K 收盤跌破 30 週線（階段二結束）"
            elif sl and Cf[t, i] < ent[i][1] * (1 - sl):
                pend_out[i] = f"單檔停損（收盤較進場價跌逾 {int(sl*100)}%）"
        room = K - (len(sh) - len(pend_out))
        if room > 0:
            ok = entm[t] & P["elig"][pool][t] & ~hm & np.isfinite(P["f"]["mom252"][t])
            cand = np.where(ok)[0]
            if len(cand):
                top = cand[np.argsort(-P["f"]["mom252"][t][cand])[:room]]
                pend_in = [(int(i), float(P["f"]["mom252"][t][i])) for i in top]
    if sh:
        val = sum(sh[i] * Cf[hi_i, i] for i in sh)
        eq[hi_i] -= val * (SLIP + FEE + TAX)
        if trades:
            for i in sh:
                px = Cf[hi_i, i] * (1 - SLIP)
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[hi_i], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason="窗尾清倉（回測結束）", score=ent[i][2]))
    s_ = pd.Series(eq, index=idx).iloc[lo_i:hi_i + 1]
    yrs = max((s_.index[-1] - s_.index[0]).days / 365.25, 1e-9)
    return dict(eq=s_, trades=pd.DataFrame(tr), turnover=buys / yrs / max(s_.mean(), 1e-9), expo=float(inv[lo_i:hi_i + 1].mean()))


def run(P, spec, pool, lo, hi, trades=False):
    return (run_stage2 if spec["fam"] == "stage2" else run6)(P, spec, pool, lo, hi, trades)


# ------------------------------------------------------------------ 批次登記（新增變體；前五輪 612 組另計）
def batches6():
    B = {}
    B["A1 低波動＋趨勢"] = [dict(fam="lowvol", N=N, rebal=rb, mf=m) for N in (5, 10, 20) for rb in ("Q", "H") for m in ("ma200", "br200", "faber")]
    B["A2 品質（營收成長穩定）＋低波動"] = [dict(fam="qrev", N=N, rebal=rb, mf=m) for N in (5, 10, 20) for rb in ("Q", "H") for m in ("br200", "faber")]
    B["A3 品質（毛利率水準與改善）"] = [dict(fam="qgm", N=N, rebal=rb, mf=m) for N in (5, 10, 20) for rb in ("Q", "H") for m in ("br200", "faber")]
    for fam, nm in (("trust", "B1 投信連續買超"), ("foreign", "B2 外資買超累積＋新高"), ("instcombo", "B3 法人籌碼組合")):
        B[nm] = [dict(fam=fam, N=N, rebal=rb, mf=m) for N in (5, 10, 20) for rb in ("M", "Q") for m in ("br200", "faber")]
    B["C 產業內相對強度（機械分群）"] = [dict(fam="cluster", L=L, mode=md, N=N, rebal=rb, mf=m)
                              for L in (126, 252) for md in ("within", "both") for N in (5, 10, 20) for rb in ("M", "Q") for m in ("br200", "faber")]
    B["D 大型股短期反轉＋趨勢"] = [dict(fam="lcrev", rv=rv, N=N, rebal=rb, mf=m) for rv in (20, 60) for N in (5, 10, 20) for rb in ("M", "Q") for m in ("br200", "faber")]
    B["E1 新高動能 長持有（半年／一年換股）"] = [dict(fam="nh6", N=N, rebal=rb, mf=m, buf=b) for N in (5, 10, 15) for rb in ("H", "Y") for m in ("ma200", "br200", "faber") for b in (False, True)]
    B["E2 Weinstein 階段二突破"] = [dict(fam="stage2", K=K, slow=sw, sl=sl, mf=m) for K in (5, 10) for sw in (30, 40) for sl in (None, 0.15, 0.25) for m in ("br200", "faber")]
    B["F 集中持股風控（單檔停損＋波動調整部位）"] = [dict(fam="nh6", N=N, rebal="Q", mf=m, sl=sl, size=sz) for N in (5, 10, 15) for m in ("br200", "faber") for sl in (None, 0.15, 0.25) for sz in ("equal", "invvol")]
    return B


def skey(sp):
    return json.dumps({k: sp[k] for k in sorted(sp)}, ensure_ascii=False)


def window_for(sp):
    return (FAM_START.get(sp["fam"], TRAIN[0]), TRAIN[1])


def metrics_row(P, sp, pool, lo, hi):
    r = run(P, sp, pool, lo, hi)
    b = S.bench(P, lo, hi)
    s, bs = S.eq_stats(r["eq"]), S.eq_stats(b)
    y, by = S.yearly(r["eq"]), S.yearly(b)
    return dict(cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], bh=bs["cagr"], bh_mdd=bs["mdd"], excess=s["cagr"] - bs["cagr"],
                ywin=int((y > by.reindex(y.index)).sum()), ynum=len(y), yrets=json.dumps({int(k): round(float(v), 4) for k, v in y.items()}),
                y0050=json.dumps({int(k): round(float(v), 4) for k, v in by.items()}), expo=r["expo"], turn=r["turnover"],
                years=(r["eq"].index[-1] - r["eq"].index[0]).days / 365.25)


def train_stage(P):
    rows = []
    for name, specs in batches6().items():
        for sp in specs:
            lo, hi = window_for(sp)
            for pool in (200, 100):
                m = metrics_row(P, sp, pool, lo, hi)
                rows.append(dict(batch=name, spec=skey(sp), fam=sp["fam"], pool=pool, lo=lo, hi=hi, **m))
        print(name, len(specs), flush=True)
    reg = pd.DataFrame(rows)
    # 有效濾網：訓練窗內濾網關閉比例 >= 5%
    off_cache = {}
    def eff(r):
        d = json.loads(r["spec"]); fk = d.get("mf")
        key = (r["lo"], fk, r["pool"] if fk == "br200" else 0)
        if key not in off_cache:
            sh_ = S.filter_off_share(P, r["lo"], r["hi"])
            off_cache[key] = sh_.get("br200(200池)" if fk == "br200" else fk, 0.0) >= 0.05
        return off_cache[key]
    reg["有效濾網"] = reg.apply(eff, axis=1)
    reg["訓練年數足夠"] = reg["years"] >= MIN_TRAIN_YEARS
    reg["ymaj"] = reg["ywin"] > reg["ynum"] / 2
    specs = reg["spec"].map(json.loads)
    nbs = []
    for i, r in reg.iterrows():
        sp = specs[i]
        same = reg[(reg["batch"] == r["batch"]) & (reg["pool"] == r["pool"]) & (reg.index != i)]
        c = g = 0
        for j, r2 in same.iterrows():
            if sum(1 for k in set(sp) | set(specs[j]) if sp.get(k) != specs[j].get(k)) == 1:
                c += 1; g += int(r2["excess"] > 0)
        nbs.append(g / c if c else np.nan)
    reg["鄰域贏0050比例"] = nbs
    ok = (reg["excess"] > 0) & reg["ymaj"] & (reg["鄰域贏0050比例"] >= 0.6) & reg["有效濾網"] & reg["訓練年數足夠"]
    reg["單池通過訓練"] = ok
    both = reg.groupby("spec")["單池通過訓練"].transform("all") & (reg.groupby("spec")["pool"].transform("nunique") == 2)
    reg["兩池通過訓練"] = both
    return reg


def pick_finalists(reg, k=3):
    c = reg[reg["兩池通過訓練"]].groupby("spec")["excess"].min().sort_values(ascending=False)
    return list(c.index[:k])


# ------------------------------------------------------------------ 保留期（每個入選者每個池只跑一次）
LOG = OUT / "holdout_log.csv"


def holdout(P, spec_json, pool, window):
    OUT.mkdir(parents=True, exist_ok=True)
    log = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=["spec", "pool", "window"])
    hit = log[(log["spec"] == spec_json) & (log["pool"] == pool) & (log["window"] == window)]
    if len(hit):
        return hit.iloc[0].to_dict()          # 已經跑過：只讀紀錄，不重算（保證只看一次）
    lo, hi = {"內部保留": INNER, "最終保留": FINAL}[window]
    sp = json.loads(spec_json)
    m = metrics_row(P, sp, pool, lo, hi)
    row = dict(spec=spec_json, pool=pool, window=window, lo=lo, hi=hi, 執行時間=time.strftime("%Y-%m-%d %H:%M:%S"), **m)
    pd.concat([log, pd.DataFrame([row])], ignore_index=True).to_csv(LOG, index=False, encoding="utf-8-sig")
    return row


def diagnose_pools(P, lo=TRAIN[0], hi=TRAIN[1], fwd=63):
    """第 4 項：前 100 檔為什麼沒有優勢？逐月橫斷面 Spearman IC（只用訓練期）與五分位報酬價差，前 200 檔 vs 前 100 檔。"""
    idx = P["idx"]; f, f6 = P["f"], P["f6"]
    Cf = P["Cf"]
    fr = np.full(Cf.shape, np.nan); fr[:-fwd] = Cf[fwd:] / Cf[:-fwd] - 1
    feats = {"動能12-1": f["mom252"], "接近52週新高": f["nh"], "風險調整動能": f["rsmom"], "低波動(取負)": -f6["vol"], "20日反轉(取負)": -f6["r20"]}
    ends = [i for i in S._month_ends(idx, idx.searchsorted(pd.Timestamp(lo)), idx.searchsorted(pd.Timestamp(hi)) - fwd, False)]
    rows = []
    for pool in (200, 100):
        for nm, a in feats.items():
            ics, spreads = [], []
            for t in ends:
                ok = P["elig"][pool][t] & np.isfinite(a[t]) & np.isfinite(fr[t])
                if ok.sum() < 30:
                    continue
                x, y = pd.Series(a[t][ok]).rank(), pd.Series(fr[t][ok]).rank()
                ics.append(x.corr(y))
                q = pd.qcut(pd.Series(a[t][ok]).rank(method="first"), 5, labels=False)
                spreads.append(fr[t][ok][q.to_numpy() == 4].mean() - fr[t][ok][q.to_numpy() == 0].mean())
            ics, spreads = np.array(ics), np.array(spreads)
            rows.append(dict(股票池=pool, 特徵=nm, 月數=len(ics), IC平均=ics.mean(), IC_t值=ics.mean() / (ics.std() / np.sqrt(len(ics))),
                             五分位價差_63日=spreads.mean()))
        disp = [np.nanstd(fr[t][P["elig"][pool][t] & np.isfinite(fr[t])]) for t in ends]
        rows.append(dict(股票池=pool, 特徵="（參考）63日報酬橫斷面標準差", 月數=len(disp), IC平均=np.nan, IC_t值=np.nan, 五分位價差_63日=float(np.mean(disp))))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 交易日誌與檢討
REASON_NOTE = {
    "換股": "定期換股：不再符合排名條件，屬於正常輪替；檢討重點是『被換掉後該股是否繼續上漲』（名單換手太快會砍到贏家）。",
    "大盤濾網": "大盤濾網轉空，全部出清：保護性出場；若隨後大盤很快反彈，就是濾網的錯殺成本。",
    "單檔停損": "單檔停損：限制單筆虧損；代價是被洗出後該股可能反彈。",
    "階段二結束": "週K 跌破 30 週線，Weinstein 階段二結束：長波段的正常出場，通常已回吐部分獲利。",
    "窗尾清倉": "回測結束時強制清倉（只是計算用，不是策略訊號）。",
}


def critique(r, p50_ret):
    why = r["exit_reason"]
    note = next((v for k, v in REASON_NOTE.items() if k in why), "")
    out = "賺" if r["ret"] > 0.05 else ("小賺小賠" if r["ret"] > -0.05 else ("虧損" if r["ret"] > -0.2 else "大虧"))
    rel = "跑贏" if r["ret"] > p50_ret else "輸給"
    return f"{out}（{r['ret']*100:+.1f}%），{rel}同期 0050（{p50_ret*100:+.1f}%）。{note}"


def trade_log(P, sp, pool, window):
    lo, hi = {"訓練期": TRAIN, "內部保留": INNER, "最終保留": FINAL}[window]
    t = run(P, sp, pool, lo, hi, trades=True)["trades"]
    if t.empty:
        return t
    c50, o50 = P["c50"], P["o50"]
    p50 = []
    for _, r in t.iterrows():
        a = o50.loc[r["entry"]] if r["entry"] in o50.index else np.nan
        b = c50.loc[r["exit"]] if r["exit"] in c50.index else np.nan
        p50.append(b / a - 1 if a and a == a else np.nan)
    t["同期0050報酬"] = p50
    t["持有天數"] = (t["exit"] - t["entry"]).dt.days
    t["檢討"] = [critique(r, r["同期0050報酬"]) for _, r in t.iterrows()]
    return t.assign(spec=skey(sp), pool=pool, 區間=window)


def main6():
    OUT.mkdir(parents=True, exist_ok=True)
    P = S.build_features(S.load5())
    P = add_clusters(add_features6(P))
    reg = train_stage(P)
    reg.drop(columns=["yrets", "y0050"]).to_csv(OUT / "registry_train.csv", index=False, encoding="utf-8-sig")
    diagnose_pools(P).to_csv(OUT / "diagnostics_large_cap.csv", index=False, encoding="utf-8-sig")
    fin = pick_finalists(reg)
    json.dump(fin, open(OUT / "finalists.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows, logs = [], []
    for sp_json in fin:
        res = {"spec": sp_json}
        passed = True
        for window in ("內部保留", "最終保留"):
            if not passed:
                break
            ms = {pool: holdout(P, sp_json, pool, window) for pool in (200, 100)}
            for pool, m in ms.items():
                res[f"{window}_{pool}_年化"] = m["cagr"]; res[f"{window}_{pool}_0050"] = m["bh"]; res[f"{window}_{pool}_回撤"] = m["mdd"]
                res[f"{window}_{pool}_逐年贏"] = f"{int(m['ywin'])}/{int(m['ynum'])}"
            passed = all(m["cagr"] > m["bh"] for m in ms.values())
            res[f"{window}_兩池皆贏0050"] = bool(passed)
            for pool in (200, 100):
                logs.append(trade_log(P, json.loads(sp_json), pool, window))
        res["冠軍"] = bool(res.get("內部保留_兩池皆贏0050") and res.get("最終保留_兩池皆贏0050"))
        rows.append(res)
    pd.DataFrame(rows).to_csv(OUT / "finalists_holdout.csv", index=False, encoding="utf-8-sig")
    if logs:
        pd.concat(logs).to_csv(OUT / "trades_finalists.csv", index=False, encoding="utf-8-sig")
    return P, reg, fin, rows


if __name__ == "__main__":
    main6()
