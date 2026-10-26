"""第五輪：純個股波段（集中持股、強者恆強）。不持有 0050 或任何 ETF，部位只有個股或現金。

規則（Andy）：不能搭配 0050；沒找到就找到超過 0050 為止；低換手；大盤不適合就空手；
淘汰標準不變：樣本外年化報酬 < 含息、扣同樣成本的 0050 買進持有 -> 淘汰。
防過度擬合：每個變體都登記（registry）；冠軍必須同時滿足 (1) 逐年（walk-forward）多數年贏 0050
(2) 參數鄰域不崩 (3) 前 200 檔與前 100 檔兩個股票池都成立；**挑選只看樣本內（2012～2020，含 2018 與 2020 兩段空頭）**，
樣本外（2021 起）只用來驗證，不用來挑。

動能類（月／季換股，前 N 檔等權）：12-1／9-1／6-1 月相對強度、接近 52 週新高、雙動能（相對＋絕對）。
成長動能：月營收年增率加速（法定可用日＝次月 10 日）、營收創新高，搭配股價強勢。
波段：週K 趨勢向上（10 週線 > 30 週線 且收盤在 30 週線上）、日K 回檔碰 20 日線後收回才進，週K 趨勢轉弱才出。
大盤濾網：只用「0050 還原價在 200 日線上」這一條（0050 只當訊號，不持有）。

股票池：每個交易日用「過去 120 日成交值中位數」的排名取前 N 檔（pit，不用現在的名單）；不使用任何族群名單。
價格：還原權息（資料湖 dividend_results）＋分割調整。成本同前四輪：手續費 0.1425%x2、證交稅 0.3%、滑價 0.1%/邊。
研究用，不是買賣建議。
"""
from __future__ import annotations

import glob
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute.strategy_lab import FEE, TAX, SLIP, stats  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round5"
ETF_TAX = 0.001
IS_LO, IS_HI = "2012-01-02", "2020-12-31"
OOS_LO = "2021-01-04"
GROWTH_IS_LO = "2018-01-02"          # 月營收資料自 2015-12 起，算得出年增率加速要到 2017 年底


# ------------------------------------------------------------------ 資料
def _rd(table, cols=None):
    out = []
    for f in glob.glob(str(ROOT / "data" / table / "**" / "*.parquet"), recursive=True):
        d = pd.read_parquet(f)
        out.append(d.reindex(columns=cols) if cols else d)
    return pd.concat(out, ignore_index=True)


def load5():
    p = _rd("price_daily", ["date", "code", "open", "high", "low", "close", "volume"])
    p = p[p["code"].str.fullmatch(r"\d{4}") & (p["close"] > 0) & (p["date"] >= "2010-01-01")]
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["code", "date"]).drop_duplicates(["code", "date"])
    piv = {k: p.pivot(index="date", columns="code", values=k) for k in ("open", "high", "low", "close", "volume")}
    idx = piv["close"].index
    cols = list(piv["close"].columns)
    ci = {c: j for j, c in enumerate(cols)}
    # 還原係數：除權息（參考價/前收）＋明顯分割
    F = np.ones((len(idx), len(cols)))
    dv = _rd("dividend_results", ["date", "code", "before_price", "reference_price"]).dropna().drop_duplicates(["date", "code"])
    dv["ratio"] = dv["reference_price"] / dv["before_price"]
    dv = dv[(dv["ratio"] > 0.6) & (dv["ratio"] < 1.0) & dv["code"].isin(ci)]
    dv["date"] = pd.to_datetime(dv["date"])
    for d, c, r in zip(dv["date"], dv["code"], dv["ratio"]):
        i = idx.searchsorted(d)
        if 0 < i < len(idx):
            F[:i, ci[c]] *= r
    cff = piv["close"].ffill()
    jump = (cff / cff.shift(1)).to_numpy()
    for i, j in zip(*np.where((jump < 0.6) | (jump > 1.67))):
        F[:i, j] *= jump[i, j]
    O, H, L, C = (piv[k].to_numpy() * F for k in ("open", "high", "low", "close"))
    V = piv["volume"].to_numpy()
    rawC = piv["close"].to_numpy()
    P = dict(idx=idx, cols=cols, ci=ci, O=O, H=H, L=L, C=C, V=V, rawC=rawC)
    P["Cf"] = pd.DataFrame(C, index=idx, columns=cols).ffill().to_numpy()
    P["is_etf"] = np.array([c.startswith("00") for c in cols])
    return P


def build_features(P):
    idx, cols = P["idx"], P["cols"]
    Cf = pd.DataFrame(P["Cf"], index=idx, columns=cols)
    f = {}
    for L_ in (126, 189, 252):
        f[f"mom{L_}"] = (Cf.shift(21) / Cf.shift(L_) - 1).to_numpy()
    f["nh"] = (Cf / Cf.rolling(252, min_periods=200).max()).to_numpy()
    f["ma200"] = Cf.rolling(200).mean().to_numpy()
    vol = Cf.pct_change().rolling(252, min_periods=200).std() * np.sqrt(252)
    f["rsmom"] = ((Cf.shift(21) / Cf.shift(252) - 1) / vol).to_numpy()          # 風險調整動能（12-1 報酬 / 年化波動）
    f["ma20"] = Cf.rolling(20).mean().to_numpy()
    # pit 流動性排名（過去 120 日成交值中位數）
    tv = pd.DataFrame(P["rawC"] * P["V"], index=idx, columns=cols).fillna(0)
    med = tv.rolling(120, min_periods=100).median()
    med.loc[:, P["is_etf"]] = np.nan
    rank = med.rank(axis=1, ascending=False).to_numpy()
    hist = (pd.DataFrame(P["rawC"], index=idx, columns=cols).notna().cumsum() >= 252).to_numpy()
    base = hist & (P["rawC"] >= 10) & np.isfinite(P["rawC"]) & ~P["is_etf"][None, :]
    P["elig"] = {200: base & (rank <= 200), 100: base & (rank <= 100)}
    above = np.where(np.isfinite(f["ma200"]), (P["Cf"] > f["ma200"]).astype(float), np.nan)
    P["br"] = {k: np.nanmean(np.where(P["elig"][k], above, np.nan), axis=1) for k in (200, 100)}   # 池內站上 200 日線的比例
    # 月營收特徵（法定可用日＝次月 10 日）
    rv = _rd("revenue_monthly", ["ym", "code", "revenue"]).dropna(subset=["revenue"])
    rv = rv[rv["code"].isin(P["ci"])]
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    yoy = R / R.shift(12).where(R.shift(12) > 0) - 1
    r3 = R.rolling(3).sum()
    feats = {"yoy3": yoy.rolling(3).mean(), "acc": yoy.rolling(3).mean() - yoy.rolling(3).mean().shift(3),
             "revnh": (r3 >= r3.rolling(12).max()).astype(float).where(r3.notna() & r3.rolling(12).max().notna())}
    avail = yoy.index.to_timestamp() + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)
    for k, df in feats.items():
        df = df.copy(); df.index = avail
        df = df.reindex(df.index.union(idx)).ffill().reindex(idx).reindex(columns=cols)
        f[k] = df.to_numpy()
    P["f"] = f
    # 大盤濾網：0050 還原價在 200 日線上
    c50 = Cf["0050"]
    P["mkt_on"] = (c50 > c50.rolling(200).mean()).to_numpy()
    mf = {"ma200": P["mkt_on"],
          "ma120": (c50 > c50.rolling(120).mean()).to_numpy(),
          "ma300": (c50 > c50.rolling(300).mean()).to_numpy(),
          "dd15": (c50 >= 0.85 * c50.rolling(252, min_periods=120).max()).to_numpy(),
          "dd10": (c50 >= 0.90 * c50.rolling(252, min_periods=120).max()).to_numpy(),
          "dd20": (c50 >= 0.80 * c50.rolling(252, min_periods=120).max()).to_numpy(),
          "dd25": (c50 >= 0.75 * c50.rolling(252, min_periods=120).max()).to_numpy(),
          "dd30": (c50 >= 0.70 * c50.rolling(252, min_periods=120).max()).to_numpy()}
    # Faber：月底收盤 > 月收盤 10 個月均線，之間沿用上個月底的狀態（只用已完成的月）
    me = c50.groupby(idx.to_period("M")).last()
    st = (me > me.rolling(10).mean())
    last_day = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max()
    st.index = last_day.reindex(st.index).values
    mf["faber"] = st.reindex(idx).ffill().fillna(False).astype(bool).to_numpy()
    P["mf"] = mf
    P["mkt_12m"] = (c50 / c50.shift(252) - 1).to_numpy()
    P["c50"] = c50
    P["o50"] = pd.Series(P["O"][:, P["ci"]["0050"]], index=idx).ffill()
    return P


# ------------------------------------------------------------------ 週K 趨勢（波段）
def weekly_state(P, fast=10, slow=30):
    idx = P["idx"]
    Cf = pd.DataFrame(P["Cf"], index=idx, columns=P["cols"])
    wk = idx.to_period("W-FRI")
    last = pd.Series(idx, index=idx).groupby(wk).max()
    wc = Cf.groupby(wk).last()
    wc.index = last.reindex(wc.index).values
    mf, ms = wc.rolling(fast).mean(), wc.rolling(slow).mean()
    up = ((wc > ms) & (mf > ms)).where(ms.notna())
    up = up.reindex(idx).ffill()
    return up.to_numpy()          # NaN=不足，True/False=趨勢向上/不向上（以「已完成的週」為準）


# ------------------------------------------------------------------ 基準與統計
def bench(P, lo, hi):
    """0050 還原含息價：窗首開盤買、窗尾收盤賣，扣手續費、ETF 稅、滑價。回傳權益曲線。"""
    idx = P["idx"]
    i0, i1 = idx.searchsorted(pd.Timestamp(lo)), idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    c = P["c50"].iloc[i0:i1 + 1]
    eq = c / P["o50"].iloc[i0] / (1 + SLIP) / (1 + FEE)
    eq.iloc[-1] *= (1 - SLIP) * (1 - FEE - ETF_TAX)
    return eq


def eq_stats(eq: pd.Series):
    e = pd.concat([pd.Series([1.0], index=[eq.index[0] - pd.Timedelta(days=1)]), eq])
    return stats(e.pct_change().dropna(), 245)


def yearly(eq: pd.Series):
    e = pd.concat([pd.Series([1.0], index=[eq.index[0] - pd.Timedelta(days=1)]), eq])
    y = e.groupby(e.index.year).last()
    prev = y.shift(1).fillna(1.0)
    return (y / prev - 1)


# ------------------------------------------------------------------ 引擎一：定期換股（動能／成長）
def _month_ends(idx, lo_i, hi_i, quarterly):
    s = pd.Series(np.arange(len(idx)), index=idx)
    key = idx.to_period("Q" if quarterly else "M")
    last = s.groupby(key).max().to_numpy()
    return [i for i in last if lo_i <= i < hi_i]


def mkt_state(P, spec, s, pool):
    fk = spec.get("mf") or ("ma200" if spec.get("mkt") else None)
    if fk is None:
        return True
    if fk == "br200":
        return bool(np.nan_to_num(P["br"][pool][s], nan=0) > 0.5)
    return bool(P["mf"][fk][s])


def pick(P, spec, t, pool, nret=None):
    """在 t 日收盤後依規格選出目標股票欄位（最多 N 檔）。"""
    f = P["f"]
    ok = P["elig"][pool][t].copy()
    fam = spec["fam"]
    if spec.get("absstock"):
        ok &= np.nan_to_num(f["mom252"][t], nan=-1) > 0
    if spec.get("above200"):
        ok &= P["Cf"][t] > f["ma200"][t]
    if fam == "mom":
        sc = f[f"mom{spec['L']}"][t]
    elif fam == "riskmom":
        sc = f["rsmom"][t].copy()
        if spec.get("withnh"):
            sc = pd.Series(sc).rank(pct=True).to_numpy() + pd.Series(f["nh"][t]).rank(pct=True).to_numpy()
    elif fam == "nh":
        sc = f["nh"][t].copy()
        ok &= np.nan_to_num(f["nh"][t], nan=0) >= spec.get("nhmin", 0.0)
        if spec.get("withmom"):
            sc = pd.Series(sc).rank(pct=True).to_numpy() + pd.Series(f["mom252"][t]).rank(pct=True).to_numpy()
    elif fam == "growth":
        ok &= P["Cf"][t] > f["ma200"][t]
        ok &= np.nan_to_num(f["nh"][t], nan=0) >= spec.get("nhmin", 0.8)
        kind = spec["kind"]
        if kind == "acc":
            ok &= np.nan_to_num(f["yoy3"][t], nan=-1) > 0.10
            sc = f["acc"][t]
        elif kind == "yoy":
            sc = f["yoy3"][t]
        else:   # 營收創新高 + 股價強勢，依動能排序
            ok &= np.nan_to_num(f["revnh"][t], nan=0) > 0
            sc = f["mom252"][t]
    elif fam == "composite":
        a = pd.Series(f["mom252"][t]).rank(pct=True).to_numpy()
        b = pd.Series(f["nh"][t]).rank(pct=True).to_numpy()
        c = pd.Series(f["acc"][t]).rank(pct=True).to_numpy()
        sc = a + b + np.nan_to_num(c, nan=0.5)
        ok &= P["Cf"][t] > f["ma200"][t]
    else:
        raise ValueError(fam)
    ok &= np.isfinite(sc)
    cand = np.where(ok)[0]
    if len(cand) == 0:
        return [], {}
    top = cand[np.argsort(-sc[cand])[:nret or spec["N"]]]
    return list(top), {int(i): float(sc[i]) for i in top}


def run_periodic(P, spec, pool, lo, hi, trades=False, liquidate=True):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf = P["O"], P["Cf"]
    sigs = [lo_i - 1] + _month_ends(idx, lo_i, hi_i, spec["rebal"] == "Q")
    sigs = sorted(set(sigs))
    N = spec["N"]
    cash, sh = 1.0, {}
    ent = {}
    eq = np.full(len(idx), np.nan)
    inv = np.zeros(len(idx))
    tr = []
    buys = 0.0
    nxt = {s + 1: s for s in sigs}
    peak, pend_stop = {}, set()
    for t in range(lo_i, hi_i + 1):
        for i in [i for i in pend_stop if i in sh]:
            px = (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) * (1 - SLIP)
            cash += sh[i] * px * (1 - FEE - TAX)
            if trades:
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[t], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason="移動停損（自高點回落）", score=ent[i][2]))
            del sh[i]
        pend_stop = set()
        if t in nxt:
            s = nxt[t]
            on = mkt_state(P, spec, s, pool)
            if on and spec.get("absidx") and not (P["mkt_12m"][s] > 0):
                on = False
            if on and spec.get("buf"):
                ranked, scs = pick(P, spec, s, pool, nret=2 * N)
                keep = [i for i in ranked if i in sh][:N]
                tgt = keep + [i for i in ranked if i not in keep][:N - len(keep)]
            else:
                tgt, scs = pick(P, spec, s, pool) if on else ([], {})
            tset = set(tgt)
            for i in [i for i in sh if i not in tset]:
                px = O[t, i]
                px = Cf[t - 1, i] if not np.isfinite(px) else px
                px *= (1 - SLIP)
                cash += sh[i] * px * (1 - FEE - TAX)
                if trades:
                    tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[t], exit_px=px,
                                   ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1,
                                   exit_reason=("大盤濾網轉空，全部出清" if not on else "掉出前N名，換股"), score=ent[i][2]))
                del sh[i]
            eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
            for i in tgt:
                if i in sh or not np.isfinite(O[t, i]):
                    continue
                amt = min(cash, eq_open / N)
                if amt <= 0:
                    continue
                px = O[t, i] * (1 + SLIP)
                sh[i] = amt / (px * (1 + FEE)); cash -= amt; buys += amt
                ent[i] = (t, px, scs.get(int(i), np.nan)); peak[i] = Cf[t, i]
        if spec.get("tstop"):
            for i in sh:
                peak[i] = max(peak.get(i, 0.0), Cf[t, i])
                if Cf[t, i] < peak[i] * (1 - spec["tstop"]):
                    pend_stop.add(i)
        pv = sum(sh[i] * Cf[t, i] for i in sh)
        eq[t] = cash + pv
        inv[t] = pv / eq[t]
    held_end = {P["cols"][i]: dict(shares=sh[i], entry=idx[ent[i][0]], entry_px=ent[i][1], last=Cf[hi_i, i]) for i in sh}
    if sh and liquidate:       # 窗尾清倉成本（紙上交易不清倉）
        val = sum(sh[i] * Cf[hi_i, i] for i in sh)
        eq[hi_i] -= val * (SLIP + FEE + TAX)
        if trades:
            for i in sh:
                px = Cf[hi_i, i] * (1 - SLIP)
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[hi_i], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason="窗尾清倉（回測結束）", score=ent[i][2]))
    s = pd.Series(eq, index=idx).iloc[lo_i:hi_i + 1]
    yrs = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    return dict(eq=s, trades=pd.DataFrame(tr), held=held_end, sh_idx={i: v for i, v in sh.items()}, turnover=buys / yrs / max(s.mean(), 1e-9),
                expo=float(inv[lo_i:hi_i + 1].mean()))


# ------------------------------------------------------------------ 引擎二：波段（週K 趨勢＋日K 回檔）
def run_swing(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, L, Cf = P["O"], P["L"], P["Cf"]
    key = (spec["fast"], spec["slow"])
    up = P.setdefault("_wk", {}).get(key)
    if up is None:
        up = P["_wk"][key] = weekly_state(P, *key)
    ma20, f = P["f"]["ma20"], P["f"]
    low3 = pd.DataFrame(L, index=idx).rolling(3).min().to_numpy()
    prev = np.roll(Cf, 1, axis=0)
    pull = (up == 1) & (low3 <= ma20) & (Cf > ma20) & (Cf > prev)
    if spec["pull"] == "hi":        # 突破型：收盤創 252 日新高且量 > 1.5 倍 20 日均量（前一日的 252 日高點才算突破）
        hh = pd.DataFrame(Cf, index=idx).rolling(252, min_periods=200).max().shift(1).to_numpy()
        vv = pd.DataFrame(P["V"], index=idx)
        vma = vv.rolling(20).mean().shift(1).to_numpy()
        pull = (up == 1) & (Cf > hh) & (np.nan_to_num(P["V"]) > 1.5 * vma)
    if spec["pull"] == "deep":      # 回檔較深：近 3 日最低價碰到 20 日線下 3%
        pull = (up == 1) & (low3 <= ma20 * 0.97) & (Cf > ma20) & (Cf > prev)
    down = (up == 0)               # 週K 趨勢轉弱
    if spec.get("exit") == "ma50":
        ma50 = pd.DataFrame(Cf, index=idx).rolling(50).mean().to_numpy()
        down = Cf < ma50
    K = spec["K"]
    cash, sh, ent = 1.0, {}, {}
    eq = np.full(len(idx), np.nan)
    pend_in, pend_out, tr = [], {}, []
    inv = np.zeros(len(idx)); buys = 0.0
    hm = np.zeros(Cf.shape[1], bool)
    for t in range(lo_i, hi_i + 1):
        for i, why in list(pend_out.items()):
            px = O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]
            px *= (1 - SLIP)
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
        eq[t] = cash + pv
        inv[t] = pv / eq[t]
        if t == hi_i:
            break
        on = mkt_state(P, dict(spec, mf=spec.get("mf", "ma200")), t, pool)
        if not on:
            for i in sh:
                pend_out[i] = "大盤濾網轉空（0050 跌破 200 日線），全部出清"
            continue
        for i in sh:
            if down[t, i]:
                pend_out[i] = "週K 趨勢轉弱"
        room = K - (len(sh) - len(pend_out))
        if room > 0:
            ok = pull[t] & P["elig"][pool][t]
            ok = ok & ~hm
            cand = np.where(ok & np.isfinite(f["mom252"][t]))[0]
            if len(cand):
                top = cand[np.argsort(-f["mom252"][t][cand])[:room]]
                pend_in = [(int(i), float(f["mom252"][t][i])) for i in top]
    if sh:
        val = sum(sh[i] * Cf[hi_i, i] for i in sh)
        eq[hi_i] -= val * (SLIP + FEE + TAX)
        if trades:
            for i in sh:
                px = Cf[hi_i, i] * (1 - SLIP)
                tr.append(dict(code=P["cols"][i], entry=idx[ent[i][0]], entry_px=ent[i][1], exit=idx[hi_i], exit_px=px,
                               ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason="窗尾清倉（回測結束）", score=ent[i][2]))
    s = pd.Series(eq, index=idx).iloc[lo_i:hi_i + 1]
    yrs = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    return dict(eq=s, trades=pd.DataFrame(tr), turnover=buys / yrs / max(s.mean(), 1e-9), expo=float(inv[lo_i:hi_i + 1].mean()))


def run(P, spec, pool, lo, hi, trades=False):
    return (run_swing if spec["fam"] == "swing" else run_periodic)(P, spec, pool, lo, hi, trades)


# ------------------------------------------------------------------ 變體登記（registry）
def batches():
    B = {}
    B["B1 相對動能（12-1／9-1／6-1）"] = [dict(fam="mom", L=L, N=N, rebal=rb, mkt=m, absstock=a)
                                     for L in (126, 189, 252) for N in (5, 10, 20) for rb in ("M", "Q") for m in (False, True) for a in (False, True)]
    B["B2 接近 52 週新高"] = [dict(fam="nh", nhmin=nm, withmom=w, N=N, rebal=rb, mkt=m)
                          for nm in (0.0, 0.9) for w in (False, True) for N in (5, 10, 20) for rb in ("M", "Q") for m in (False, True)]
    B["B3 雙動能（相對＋個股絕對＋指數絕對）"] = [dict(fam="mom", L=L, N=N, rebal=rb, mkt=True, absstock=True, absidx=True)
                                      for L in (126, 189, 252) for N in (5, 10, 20) for rb in ("M", "Q")]
    B["B4 成長動能（營收）"] = [dict(fam="growth", kind=k, N=N, rebal=rb, mkt=m, nhmin=0.8)
                           for k in ("acc", "yoy", "revnh") for N in (5, 10) for rb in ("M", "Q") for m in (False, True)]
    B["B5 波段（週K 趨勢＋日K 回檔）"] = [dict(fam="swing", fast=f, slow=s, pull=pl, K=K)
                                 for (f, s) in ((10, 30), (13, 40)) for pl in ("ma20", "deep") for K in (5, 10)]
    B["B7 新高動能 x 大盤濾網種類（必須有濾網）"] = [dict(fam="nh", nhmin=nm, withmom=w, N=N, rebal=rb, mf=m)
                                          for nm in (0.0, 0.9) for w in (False, True) for N in (5, 10, 20) for rb in ("M", "Q")
                                          for m in ("ma120", "ma200", "ma300", "faber", "dd15")]
    B["B8 新高動能 + 緩衝帶 + 移動停損（低換手）"] = [dict(fam="nh", nhmin=0.0, withmom=True, N=N, rebal=rb, mf=m, buf=b, tstop=ts)
                                             for N in (5, 10) for rb in ("M", "Q") for m in ("ma200", "faber", "dd15", "br200")
                                             for b in (False, True) for ts in (0.0, 0.2, 0.3)]
    B["B9 風險調整動能（動能/波動）"] = [dict(fam="riskmom", withnh=w, N=N, rebal=rb, mf=m, buf=b)
                                 for w in (False, True) for N in (5, 10, 20) for rb in ("M", "Q") for m in ("ma200", "faber", "dd15", "br200") for b in (False, True)]
    B["B10 新高動能 放寬持股數（15/20/30 檔）"] = [dict(fam="nh", nhmin=0.0, withmom=True, N=N, rebal=rb, mf=m, buf=b)
                                         for N in (15, 20, 30) for rb in ("M", "Q") for m in ("ma200", "faber", "dd15", "br200") for b in (False, True)]
    B["B13 突破新高波段（量能確認，週K 趨勢向上才進）"] = [dict(fam="swing", fast=10, slow=30, pull="hi", K=K, exit=ex, mf=m)
                                             for K in (5, 10) for ex in ("wk", "ma50") for m in ("ma200", "faber", "br200")]
    B["B14 新高動能 + 個股需站上 200 日線"] = [dict(fam="nh", nhmin=0.0, withmom=True, N=N, rebal=rb, mf=m, buf=b, above200=True)
                                      for N in (5, 10, 15) for rb in ("M", "Q") for m in ("faber", "dd15", "br200") for b in (False, True)]
    B["B15 新高動能 x 回撤式大盤濾網（10/20/25%）"] = [dict(fam="nh", nhmin=0.0, withmom=True, N=N, rebal=rb, mf=m, buf=True)
                                         for N in (5, 10) for rb in ("M", "Q") for m in ("dd10", "dd20", "dd25")]
    B["B16 新高動能 + 個股站上 200 日線 + 寬鬆回撤濾網（最後一批）"] = [dict(fam="nh", nhmin=0.0, withmom=True, N=N, rebal=rb, mf=m, buf=True, above200=True)
                                                    for N in (5, 10, 15) for rb in ("M", "Q") for m in ("dd20", "dd25", "dd30", "faber", "br200")]
    B["B6 複合排名（動能＋新高＋營收加速）"] = [dict(fam="composite", N=N, rebal=rb, mkt=True) for N in (5, 10) for rb in ("M", "Q")]
    return B


def spec_key(sp):
    return json.dumps({k: sp[k] for k in sorted(sp)}, ensure_ascii=False)


def evaluate(P, sp, pool, end):
    growth = sp["fam"] in ("growth", "composite")
    is_lo = GROWTH_IS_LO if growth else IS_LO
    rI = run(P, sp, pool, is_lo, IS_HI); rO = run(P, sp, pool, OOS_LO, end)
    bI, bO = bench(P, is_lo, IS_HI), bench(P, OOS_LO, end)
    row = dict(spec=spec_key(sp), fam=sp["fam"], pool=pool, is_lo=is_lo)
    for tag, r, b in (("IS", rI, bI), ("OOS", rO, bO)):
        s, bs = eq_stats(r["eq"]), eq_stats(b)
        y, by = yearly(r["eq"]), yearly(b)
        row.update({f"{tag}_cagr": s["cagr"], f"{tag}_mdd": s["mdd"], f"{tag}_sharpe": s["sharpe"], f"{tag}_0050": bs["cagr"],
                    f"{tag}_0050_mdd": bs["mdd"], f"{tag}_excess": s["cagr"] - bs["cagr"],
                    f"{tag}_ywin": int((y > by.reindex(y.index)).sum()), f"{tag}_ynum": len(y),
                    f"{tag}_yrets": json.dumps({int(k): round(float(v), 4) for k, v in y.items()}),
                    f"{tag}_y0050": json.dumps({int(k): round(float(v), 4) for k, v in by.items()}),
                    f"{tag}_expo": r["expo"], f"{tag}_turn": r["turnover"]})
    row["verdict"] = "通過" if row["OOS_cagr"] >= row["OOS_0050"] else "淘汰，不使用"
    return row


def run_batches(P, only=None, end="2026-10-22"):
    reg = []
    for name, specs in batches().items():
        if only and name not in only:
            continue
        for sp in specs:
            for pool in (200, 100):
                row = evaluate(P, sp, pool, end)
                row["batch"] = name
                reg.append(row)
        print(name, len(specs), "variants x 2 pools done", flush=True)
    return pd.DataFrame(reg)


# ------------------------------------------------------------------ 篩選（只看樣本內）與確認（樣本外）
def add_selection(reg: pd.DataFrame) -> pd.DataFrame:
    reg = reg.copy()
    reg["IS_ymaj"] = reg["IS_ywin"] > reg["IS_ynum"] / 2
    specs = reg["spec"].map(json.loads)
    reg["_p"] = specs
    nb_share, nb_n = [], []
    for i, r in reg.iterrows():
        sp = r["_p"]
        same = reg[(reg["batch"] == r["batch"]) & (reg["pool"] == r["pool"]) & (reg.index != i)]
        cnt, good = 0, 0
        for j, r2 in same.iterrows():
            diff = sum(1 for k in sp if sp[k] != r2["_p"].get(k))
            if diff == 1:
                cnt += 1
                good += int(r2["IS_excess"] > 0)
        nb_share.append(good / cnt if cnt else np.nan); nb_n.append(cnt)
    reg["鄰域數"], reg["鄰域樣本內贏0050比例"] = nb_n, nb_share
    other = {(r["spec"], r["pool"]): r for _, r in reg.iterrows()}
    ok_other = []
    for _, r in reg.iterrows():
        o = other.get((r["spec"], 100 if r["pool"] == 200 else 200))
        ok_other.append(bool(o is not None and o["IS_excess"] > 0 and o["IS_ymaj"]))
    reg["另一股票池樣本內也成立"] = ok_other
    reg["通過樣本內篩選"] = (reg["IS_excess"] > 0) & reg["IS_ymaj"] & (reg["鄰域樣本內贏0050比例"] >= 0.6) & reg["另一股票池樣本內也成立"]
    reg["OOS_ymaj"] = reg["OOS_ywin"] > reg["OOS_ynum"] / 2
    has_filter = specs.map(lambda d: bool(d.get("mf") or d.get("mkt") or d["fam"] == "swing"))
    reg["有大盤濾網"] = has_filter
    reg["最終冠軍"] = reg["通過樣本內篩選"] & (reg["verdict"] == "通過") & reg["OOS_ymaj"] & reg["有大盤濾網"]
    ok = reg.groupby("spec")["最終冠軍"].transform("all") & (reg.groupby("spec")["pool"].transform("nunique") == 2)
    reg["單池符合"] = reg["最終冠軍"]
    reg["最終冠軍"] = ok          # 必須兩個股票池都滿足所有條件才算冠軍
    return reg.drop(columns=["_p"])


def walk_forward_family(reg: pd.DataFrame, pool=200, lookback=5):
    """逐年 walk-forward：每年初用「過去 lookback 年超額報酬平均」在全部變體（含所有家族）中選一個，下一年持有並與 0050 比。
    報酬來自各變體樣本內／外兩次連續回測的逐年報酬；只用已知年份選。"""
    r = reg[reg["pool"] == pool]
    ys, y0 = {}, {}
    for _, x in r.iterrows():
        a = {**json.loads(x["IS_yrets"]), **json.loads(x["OOS_yrets"])}
        b = {**json.loads(x["IS_y0050"]), **json.loads(x["OOS_y0050"])}
        ys[x["spec"]] = {int(k): v for k, v in a.items()}; y0 = {**y0, **{int(k): v for k, v in b.items()}}
    out = []
    for Y in range(2021, 2027):
        best, bs = None, -9
        for sp, d in ys.items():
            past = [d[y] - y0[y] for y in range(Y - lookback, Y) if y in d and y in y0]
            if len(past) >= 3 and np.mean(past) > bs:
                best, bs = sp, np.mean(past)
        if best is not None and Y in ys[best]:
            out.append(dict(年=Y, 選到=best, 訓練期平均超額=bs, 報酬=ys[best][Y], **{"0050": y0[Y]}, 贏大盤=ys[best][Y] > y0[Y]))
    return pd.DataFrame(out)


def effective_filter(spec_json: str, off: dict, min_share=0.05) -> bool:
    """濾網要「真的會空手」才算數：樣本內至少 5% 的交易日是關閉狀態（例如回撤 30% 的濾網在 2012～2020 只有 0%，等於沒有濾網）。"""
    d = json.loads(spec_json)
    fk = d.get("mf") or ("ma200" if (d.get("mkt") or d["fam"] == "swing") else None)
    if fk is None:
        return False
    key = "br200(200池)" if fk == "br200" else fk
    return off["樣本內"].get(key, 0.0) >= min_share


def finalize(reg: pd.DataFrame, off: dict):
    reg = reg.copy()
    reg["有效濾網"] = reg["spec"].map(lambda x: effective_filter(x, off))
    reg["單池符合"] = reg["單池符合"] & reg["有效濾網"]
    both = reg.groupby("spec")["單池符合"].transform("all") & (reg.groupby("spec")["pool"].transform("nunique") == 2)
    reg["最終冠軍"] = both
    return reg


def filter_off_share(P, lo, hi):
    idx = P["idx"]; a, b = idx.searchsorted(pd.Timestamp(lo)), idx.searchsorted(pd.Timestamp(hi), side="right")
    return {k: float(1 - np.mean(v[a:b])) for k, v in P["mf"].items()} | {"br200(200池)": float(1 - np.nanmean(P["br"][200][a:b] > 0.5))}


def outputs(P, reg, end="2026-10-22"):
    """最接近冠軍者（僅中型股池 200 成立）的逐年表與交易日誌，以及各批次摘要。"""
    p200 = reg[(reg["pool"] == 200) & reg["有效濾網"] & (reg["IS_excess"] > 0) & reg["IS_ymaj"] & (reg["鄰域樣本內贏0050比例"] >= 0.6)]
    near = p200.sort_values("OOS_excess", ascending=False).head(3)
    near[["batch", "spec", "IS_cagr", "IS_0050", "IS_ywin", "IS_ynum", "鄰域樣本內贏0050比例", "OOS_cagr", "OOS_0050", "OOS_mdd", "OOS_sharpe",
          "OOS_ywin", "OOS_ynum", "verdict"]].to_csv(OUT / "near_champions_pool200_only.csv", index=False, encoding="utf-8-sig")
    rows, logs = [], []
    for _, r in near.iterrows():
        d = json.loads(r["spec"])
        for pool in (200, 100):
            x = reg[(reg["spec"] == r["spec"]) & (reg["pool"] == pool)].iloc[0]
            ys = {**json.loads(x["IS_yrets"]), **json.loads(x["OOS_yrets"])}
            y0 = {**json.loads(x["IS_y0050"]), **json.loads(x["OOS_y0050"])}
            for y in ys:
                rows.append(dict(spec=r["spec"], pool=pool, 年=int(y), 策略=ys[y], **{"0050": y0.get(y)}, 贏=ys[y] > y0.get(y, 9)))
            for tag, (lo, hi) in (("樣本內", (IS_LO, IS_HI)), ("樣本外", (OOS_LO, end))):
                t = run(P, d, pool, lo, hi, trades=True)["trades"]
                if len(t):
                    t = t.assign(spec=r["spec"], pool=pool, 區間=tag, 持有天數=(t["exit"] - t["entry"]).dt.days)
                    logs.append(t)
    pd.DataFrame(rows).to_csv(OUT / "near_champions_yearly.csv", index=False, encoding="utf-8-sig")
    pd.concat(logs).to_csv(OUT / "trades_near_champions.csv", index=False, encoding="utf-8-sig")


def main5(end="2026-10-22"):
    OUT.mkdir(parents=True, exist_ok=True)
    P = build_features(load5())
    reg = add_selection(run_batches(P, end=end))
    off = {w: filter_off_share(P, a, b) for w, (a, b) in {"樣本內": (IS_LO, IS_HI), "樣本外": (OOS_LO, end)}.items()}
    pd.DataFrame(off).to_csv(OUT / "filter_off_share.csv", encoding="utf-8-sig", index_label="濾網")
    reg = finalize(reg, off)
    reg.drop(columns=["IS_yrets", "IS_y0050", "OOS_yrets", "OOS_y0050"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    reg.to_pickle(OUT / "_registry.pkl")
    wf = walk_forward_family(reg[reg["有效濾網"]])
    wf.to_csv(OUT / "walk_forward_selection.csv", index=False, encoding="utf-8-sig")
    outputs(P, reg, end)
    return P, reg, wf, off


if __name__ == "__main__":
    main5()
