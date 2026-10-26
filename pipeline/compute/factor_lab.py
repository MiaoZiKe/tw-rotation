"""因子實驗室（第七輪之外的獨立方向）：價值／品質／組合因子／事件漂移／大型股反轉，純個股，可空手，不持有 ETF。

與前幾輪的關係：重用 swing_lab5（資料載入、還原價、pit 前 200／前 100 流動性池、大盤濾網、0050 含息基準）與
strategy_lab 的成本（手續費 0.1425%x2、證交稅 0.3%、滑價 0.1%/邊），**不改**它們；本檔只新增因子與引擎。

證據協議（與 round6 相同，事先定）
  訓練期   2012-01-02～2018-12-31  搜尋與選參數。基本面家族從「資料夠密的第一天」算起（程式依池內覆蓋率自動判定，並寫進登記表）。
  內部保留 2019-01-02～2022-12-30  入選者每池只跑一次（holdout_log.csv，重跑只讀紀錄）。
  最終保留 2023-01-02～2026-10-22  內部保留兩池都贏才開，只跑一次；註：2023 年起前幾輪已看過，不算乾淨。
  訓練年數 < 2.5 年的家族不能入選（資料不足，如實標示而非硬選）。
  試驗總數 = 前幾輪 858 組 + 本檔新增組數。
冠軍：兩段年化都贏含息 0050、參數鄰域穩、前 200／前 100 兩池都成立。

財報可用日一律「法定期限」：Q1 5/15、Q2 8/14、Q3 11/14、年報 3/31（隔年）、月營收次月 10 日；寧可晚不可偷看。
資料限制（誠實）：本地財報／資產負債表在 2016 年前只有約 130 檔（不含多數大型股），全市場覆蓋從 2016Q1 起；
TTM 在滿四季前以「已公布季數年化」近似（會有季節性雜訊）；資產負債表沒有有息負債與現金流量，
故 EV 以「市值＋總負債」近似、資本報酬率以「EBIT／總資產」近似、Piotroski 只用 7 項（缺 CFO 與流動比率）。
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
from pipeline.compute.strategy_lab import FEE, TAX, SLIP  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "factor_lab"
TRAIN = ("2012-01-02", "2018-12-31")
INNER = ("2019-01-02", "2022-12-30")
FINAL = ("2023-01-02", "2026-10-22")
MIN_TRAIN_YEARS = 2.5
PRIOR_TRIALS = 858
LOG = OUT / "holdout_log.csv"


# ------------------------------------------------------------------ 特徵
def legal_date(qn: int) -> pd.Timestamp:
    """季序號（year*4+quarter-1）的法定可用日：Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31。"""
    y, q = qn // 4, qn % 4 + 1
    return {1: pd.Timestamp(y, 5, 15), 2: pd.Timestamp(y, 8, 14), 3: pd.Timestamp(y, 11, 14), 4: pd.Timestamp(y + 1, 3, 31)}[q]


def rev_avail(per: pd.PeriodIndex) -> pd.DatetimeIndex:
    """月營收法定可用日＝次月 10 日。"""
    return per.to_timestamp() + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)


def _daily(df: pd.DataFrame, av, idx, cols):
    """把「公布日 → 數值」的表攤成每個交易日（只用已公布者，向後填補）。"""
    df = df.copy()
    df.index = pd.DatetimeIndex(av)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.reindex(df.index.union(idx)).ffill().reindex(idx).reindex(columns=cols).to_numpy()


def _qpiv(d, col, qn_range, cols):
    x = d.drop_duplicates(["code", "qn"], keep="last").pivot(index="qn", columns="code", values=col)
    return x.reindex(index=qn_range).reindex(columns=cols)


def _ttm(M: pd.DataFrame) -> pd.DataFrame:
    """近四季合計；不滿四季以已公布季數年化（只在當季有值時才算）。"""
    cnt = M.notna().rolling(4, min_periods=1).sum()
    s = M.rolling(4, min_periods=1).sum()
    return (s * 4 / cnt).where(M.notna())


def _fund(P, leak=False):
    """基本面與營收特徵。leak=True 只用來量化「前視偏誤有多大」：財報在期末當天就用、月營收在該月底隔天就用（錯誤做法，僅供對照）。"""
    idx, cols, ci = P["idx"], P["cols"], P["ci"]
    ff = {}
    px = pd.DataFrame(P["rawC"], index=idx, columns=cols).ffill()        # 未還原收盤價（估值用）
    fq = S._rd("financial_q", ["year", "quarter", "code", "revenue", "gross_profit", "operating_income", "net_income", "eps"])
    bq = S._rd("balance_q", ["year", "quarter", "code", "shares", "equity_parent", "total_assets", "bps"])
    for d in (fq, bq):
        d["qn"] = d["year"] * 4 + d["quarter"] - 1
    fq, bq = fq[fq["code"].isin(ci)], bq[bq["code"].isin(ci)]
    qr = range(int(min(fq.qn.min(), bq.qn.min())), int(max(fq.qn.max(), bq.qn.max())) + 1)
    if leak:
        av = [pd.Timestamp(q // 4, (q % 4 + 1) * 3, 1) + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1) for q in qr]
    else:
        av = [legal_date(q) for q in qr]
    Q = {k: _qpiv(fq, k, qr, cols) for k in ("revenue", "gross_profit", "operating_income", "net_income", "eps")}
    B = {k: _qpiv(bq, k, qr, cols) for k in ("shares", "equity_parent", "total_assets", "bps")}
    T = {k: _ttm(v) for k, v in Q.items()}
    A, E = B["total_assets"].where(B["total_assets"] > 0), B["equity_parent"]
    tl = (A - E).clip(lower=0)
    gm_t = T["gross_profit"] / T["revenue"].where(T["revenue"] > 0)
    roa = T["net_income"] / A
    lev = tl / A
    turn = T["revenue"] / A
    fs = ((roa > 0).astype(float) + ((roa - roa.shift(4)) > 0) + ((lev - lev.shift(4)) < 0) + (B["shares"] / B["shares"].shift(4) <= 1.03)
          + ((gm_t - gm_t.shift(4)) > 0) + ((turn - turn.shift(4)) > 0) + (T["operating_income"] > 0))
    fs = fs.where(roa.notna() & roa.shift(4).notna() & lev.shift(4).notna() & gm_t.shift(4).notna() & turn.shift(4).notna())
    gm_q = Q["gross_profit"] / Q["revenue"].where(Q["revenue"] > 0)
    qd = lambda M: _daily(M, av, idx, cols)                              # noqa: E731
    eps_ttm, ebit_ttm, ni_ttm = qd(T["eps"]), qd(T["operating_income"]), qd(T["net_income"])
    pxa = px.to_numpy()
    with np.errstate(all="ignore"):
        shares, eq, ta, bps = qd(B["shares"]), qd(E), qd(A), qd(B["bps"])
        tla = np.clip(ta - eq, 0, None)
        mcap = pxa * shares
        ff["ep"] = np.where(pxa > 0, eps_ttm / pxa, np.nan)
        ff["bp"] = np.where(bps > 0, bps / pxa, np.nan)
        ff["ey_ebit"] = ebit_ttm / (mcap + tla)
        ff["roe"] = np.where(eq > 0, ni_ttm / eq, np.nan)
        ff["roa_ebit"] = ebit_ttm / ta
        ff["gm"] = qd(gm_t)
        ff["gmstab"] = -qd(gm_q.rolling(8, min_periods=4).std())
        ff["fs"] = qd(fs)
        ff["eps_pos"] = np.where(np.isfinite(eps_ttm), (eps_ttm > 0).astype(float), np.nan)
        ff["sue"] = qd(Q["eps"] - Q["eps"].shift(4)) / pxa               # 財報驚喜代理：單季 EPS 年增額／股價
        ff["mcap"] = mcap
        ff["sr"] = qd(T["revenue"]) / mcap                               # 營收市值比（市值營收比的倒數，越高越便宜）
        ff["ebit_yoy"] = qd(T["operating_income"] / T["operating_income"].shift(4).where(T["operating_income"].shift(4) > 0) - 1)
    # 月營收（法定可用日次月 10 日；leak 版＝該月底隔天）
    rv = S._rd("revenue_monthly", ["ym", "code", "revenue"]).dropna(subset=["revenue"])
    rv = rv[rv["code"].isin(ci)]
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    yoy1 = R / R.shift(12).where(R.shift(12) > 0) - 1
    y3 = yoy1.rolling(3).mean()
    rav = (yoy1.index.to_timestamp(how="end").normalize() + pd.Timedelta(days=1)) if leak else rev_avail(yoy1.index)
    ff["yoy1"] = _daily(yoy1, rav, idx, cols)
    ff["yoy3"] = _daily(y3, rav, idx, cols)
    ff["acc"] = _daily(y3 - y3.shift(3), rav, idx, cols)
    ff["rv312"] = _daily(R.rolling(3).mean() / R.rolling(12).mean(), rav, idx, cols)   # 近 3 月均營收／近 12 月均營收
    ff["_rev_av"] = rav
    return ff


def add_factor_features(P):
    idx, cols, ci = P["idx"], P["cols"], P["ci"]
    Cf = pd.DataFrame(P["Cf"], index=idx, columns=cols)
    px = pd.DataFrame(P["rawC"], index=idx, columns=cols).ffill()
    pxa = px.to_numpy()
    ff = _fund(P, False)
    rav = ff.pop("_rev_av")
    ff["r5"] = (Cf / Cf.shift(5) - 1).to_numpy()
    ff["r20"] = (Cf / Cf.shift(20) - 1).to_numpy()
    ff["vol"] = (Cf.pct_change().rolling(252, min_periods=200).std() * np.sqrt(252)).to_numpy()
    ff["ma3"] = ((Cf > Cf.rolling(20).mean()) & (Cf > Cf.rolling(60).mean()) & (Cf > Cf.rolling(120).mean())).astype(float).to_numpy()
    # 殖利率：近 250 個交易日已除息的現金股利／當日股價；dy3＝近三個年度的平均
    dv = S._rd("dividend_events", ["code", "kind", "amount", "announce_date", "ex_date"])
    dv = dv[(dv["kind"] == "cash") & dv["ex_date"].notna() & (dv["amount"] > 0) & dv["code"].isin(ci)].drop_duplicates(["code", "ex_date", "amount"])
    dv["ex_i"] = idx.searchsorted(pd.to_datetime(dv["ex_date"]))
    D = np.zeros(P["Cf"].shape)
    dv = dv[dv["ex_i"] < len(idx)]
    for i, c, a in zip(dv["ex_i"], dv["code"], dv["amount"]):
        D[i, ci[c]] += a
    cs = np.cumsum(D, axis=0)
    sh = lambda k: np.vstack([np.zeros((k, cs.shape[1])), cs[:-k]])      # noqa: E731
    t0, t1, t2 = cs - sh(250), sh(250) - sh(500), sh(500) - sh(750)
    with np.errstate(all="ignore"):
        ff["dy"] = np.where(pxa > 0, t0 / pxa, np.nan)
        ff["dy3"] = np.where(pxa > 0, (t0 + t1 + t2) / 3 / pxa, np.nan)
    P["div_events"] = dv
    # 法人（投信／外資當日買賣超；三大法人合計）
    idf = S._rd("inst_daily", ["date", "code", "foreign_total", "trust", "inst_total"])
    idf = idf[idf["code"].isin(ci)].drop_duplicates(["date", "code"])
    idf["date"] = pd.to_datetime(idf["date"])
    pv = lambda c: idf.pivot(index="date", columns="code", values=c).reindex(index=idx, columns=cols)   # noqa: E731
    tr_, fo_, it_ = pv("trust"), pv("foreign_total"), pv("inst_total")
    V = pd.DataFrame(P["V"], index=idx, columns=cols).replace(0, np.nan)
    ff["trust_buy"] = (tr_ / V).to_numpy()                                # 投信買超占成交量
    ff["foreign_net"] = fo_.to_numpy()
    ff["inst5"] = (it_.gt(0).rolling(5).sum() == 5).astype(float).where(it_.notna().rolling(5).sum() == 5).to_numpy()   # 近 5 日每日三大法人皆買超
    ff["has_inst"] = it_.notna().to_numpy()
    P["ff"] = ff
    P["ffL"] = {**ff, **{k: v for k, v in _fund(P, True).items() if k != "_rev_av"}}
    P["ff"]["yoy3"] = ff["yoy3"]
    P["rev_events"] = [idx.searchsorted(a) for a in rav if idx[0] <= a <= idx[-1]]
    qr = range(2010 * 4, 2027 * 4)
    P["earn_events"] = [idx.searchsorted(legal_date(q)) for q in qr if idx[0] <= legal_date(q) <= idx[-1]]
    # 廣池：流動性前 600（FinLab 類回測的股票池較廣，重現時用）
    tv = pd.DataFrame(P["rawC"] * P["V"], index=idx, columns=cols).fillna(0)
    med = tv.rolling(120, min_periods=100).median()
    med.loc[:, P["is_etf"]] = np.nan
    rank = med.rank(axis=1, ascending=False).to_numpy()
    hist = (pd.DataFrame(P["rawC"], index=idx, columns=cols).notna().cumsum() >= 252).to_numpy()
    base = hist & (P["rawC"] >= 10) & np.isfinite(P["rawC"]) & ~P["is_etf"][None, :]
    P["elig"][600] = base & (rank <= 600)
    P["br"][600] = np.nanmean(np.where(P["elig"][600], np.where(np.isfinite(P["f"]["ma200"]), (P["Cf"] > P["f"]["ma200"]).astype(float), np.nan), np.nan), axis=1)
    info = pd.read_parquet(ROOT / "data" / "company_info" / "year=0" / "part.parquet")
    fin = set(info.loc[info["industry"].isin(["金融保險", "金融業"]), "code"])
    P["is_fin"] = np.array([c in fin for c in cols])
    ind = dict(zip(info["code"], info["industry"].fillna("")))
    P["ind"] = np.array([ind.get(c) or f"_{c}" for c in cols])
    return P


# ------------------------------------------------------------------ 家族覆蓋起點（資料夠密的第一天）
def family_start(P, keys, pool=200, need=0.5, lo=TRAIN[0]):
    """池內「所有指定特徵都有值」的比例首次 >= need 的日期（至少 lo）。資料不足的家族不假裝有整段訓練期。"""
    idx = P["idx"]
    ok = P["elig"][pool].copy()
    fin = np.ones_like(ok)
    for k in keys:
        fin &= np.isfinite(P["ff"].get(k, P["f"].get(k)))
    frac = (ok & fin).sum(1) / np.maximum(ok.sum(1), 1)
    i0 = idx.searchsorted(pd.Timestamp(lo))
    hit = np.where(frac[i0:] >= need)[0]
    if len(hit) == 0:
        return None
    return str(idx[i0 + hit[0]].date())


# ------------------------------------------------------------------ 選股
def _feat(P, k, leak=False):
    FF = P["ffL"] if leak else P["ff"]
    return FF[k] if k in FF else P["f"][k]


def pick_f(P, spec, t, pool, nret=None):
    ok = P["elig"][pool][t].copy()
    sc = np.zeros(len(ok))
    comps = spec["comps"]
    cols = []
    for c in comps:
        neg = c.startswith("-")
        a = _feat(P, c.lstrip("-"), spec.get("leak"))[t].astype(float)
        a = -a if neg else a
        ok &= np.isfinite(a)
        cols.append(a)
    flt = spec.get("flt")
    FF = P["ffL"] if spec.get("leak") else P["ff"]
    for k, lo_ in spec.get("gt", {}).items():          # 門檻條件：特徵 > 值（缺值視為不通過）
        ok &= np.nan_to_num(_feat(P, k, spec.get("leak"))[t], nan=-1e9) > lo_
    for k, lo_ in spec.get("ge", {}).items():
        ok &= np.nan_to_num(_feat(P, k, spec.get("leak"))[t], nan=-1e9) >= lo_
    if spec.get("nofin"):
        ok &= ~P["is_fin"]
    if flt in ("pos", "above200_pos"):
        ok &= np.nan_to_num(FF["eps_pos"][t], nan=0) > 0
    if flt in ("above200", "above200_pos"):
        ok &= np.nan_to_num(P["Cf"][t] - P["f"]["ma200"][t], nan=-1) > 0
    if flt == "roe10":
        ok &= np.nan_to_num(P["ff"]["roe"][t], nan=-1) > 0.10
    if spec.get("minpool_cap"):                       # 大型股：市值前 1/3（池內）
        mc = np.where(ok, P["ff"]["mcap"][t], np.nan)
        ok &= mc >= np.nanpercentile(mc[ok], 66) if ok.sum() > 10 else ok
    if ok.sum() == 0:
        return [], {}
    for a in cols:
        sc = sc + pd.Series(np.where(ok, a, np.nan)).rank(pct=True).to_numpy()
    sc = sc / len(cols)
    ok &= np.isfinite(sc)
    cand = np.where(ok)[0]
    if len(cand) == 0:
        return [], {}
    order = cand[np.argsort(-sc[cand])]
    n = nret or spec["N"]
    if spec.get("ind_cap"):                          # 單一產業最多 k 檔：依分數由高到低，超過上限的跳過
        cnt, pick = {}, []
        for i in order:
            g = P["ind"][i]
            if cnt.get(g, 0) < spec["ind_cap"]:
                pick.append(i); cnt[g] = cnt.get(g, 0) + 1
            if len(pick) >= n:
                break
        top = np.array(pick, int)
    else:
        top = order[:n]
    return list(top), {int(i): float(sc[i]) for i in top}


def _ends(idx, lo_i, hi_i, rebal, P=None):
    """換股訊號日（收盤後）。R＝月營收法定公告日（次月 10 日）、E＝財報法定公告日、J＝每年 6 月最後交易日（7 月初調倉）。"""
    if rebal == "R":
        return [t for t in P["rev_events"] if lo_i <= t < hi_i]
    if rebal == "E":
        return [t for t in P["earn_events"] if lo_i <= t < hi_i]
    s = pd.Series(np.arange(len(idx)), index=idx)
    if rebal == "J":
        m = s[idx.month == 6]
        return [i for i in m.groupby(m.index.year).max().to_numpy() if lo_i <= i < hi_i]
    key = {"M": idx.to_period("M"), "Q": idx.to_period("Q"), "H": idx.year * 2 + (idx.month > 6), "Y": idx.year}[rebal]
    return [i for i in s.groupby(key).max().to_numpy() if lo_i <= i < hi_i]


def _sell(P, t, i, sh, ent, tr, why, trades):
    O, Cf = P["O"], P["Cf"]
    px = (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) * (1 - SLIP)
    val = sh[i] * px * (1 - FEE - TAX)
    if trades:
        tr.append(dict(code=P["cols"][i], entry=P["idx"][ent[i][0]], entry_px=ent[i][1], exit=P["idx"][t], exit_px=px,
                       ret=px * (1 - FEE - TAX) / (ent[i][1] * (1 + FEE)) - 1, exit_reason=why, score=ent[i][2]))
    return val


def _finish(P, eq, inv, tr, buys, lo_i, hi_i, sh, ent, trades):
    Cf, idx = P["Cf"], P["idx"]
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


# ------------------------------------------------------------------ 引擎一：定期換股（收盤後選、隔日開盤成交）
def run_periodic(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf = P["O"], P["Cf"]
    sigs = sorted(set([lo_i - 1] + _ends(idx, lo_i, hi_i, spec["rebal"], P)))
    nxt = {s + 1: s for s in sigs}
    N = spec["N"]
    cash, sh, ent = 1.0, {}, {}
    eq = np.full(len(idx), np.nan); inv = np.zeros(len(idx)); tr = []; buys = 0.0
    for t in range(lo_i, hi_i + 1):
        if t in nxt:
            s = nxt[t]
            on = S.mkt_state(P, spec, s, pool)
            tgt, scs = pick_f(P, spec, s, pool) if on else ([], {})
            tset = set(tgt)
            for i in [i for i in sh if i not in tset]:
                cash += _sell(P, t, i, sh, ent, tr, "大盤濾網關閉，全部出清" if not on else "換股：掉出目標名單", trades)
                del sh[i]
            eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
            for i in [i for i in tgt if i not in sh and np.isfinite(O[t, i])]:
                amt = min(cash, eq_open / N)
                if amt <= 0:
                    continue
                px = O[t, i] * (1 + SLIP)
                sh[i] = amt / (px * (1 + FEE)); cash -= amt; buys += amt
                ent[i] = (t, px, scs.get(int(i), np.nan))
        eq[t] = cash + sum(sh[i] * Cf[t, i] for i in sh); inv[t] = (eq[t] - cash) / eq[t]
    return _finish(P, eq, inv, tr, buys, lo_i, hi_i, sh, ent, trades)


# ------------------------------------------------------------------ 引擎二：事件（固定持有天數、同時最多 K 檔）
def build_events(P, spec, pool):
    """回傳 {訊號日索引: [(欄位, 分數, 持有交易日數)]}。訊號日＝資訊公開日（收盤後），下一個交易日開盤成交。"""
    idx, ff = P["idx"], P["ff"]
    ev = {}
    kind = spec["ev"]
    if kind == "rev":                      # 月營收公布漂移：次月 10 日（法定日）收盤後，單月年增率達門檻者
        for t in P["rev_events"]:
            y = ff["yoy1"][t]
            ok = P["elig"][pool][t] & np.isfinite(y) & (y >= spec["thr"])
            if spec.get("acc"):
                ok &= np.nan_to_num(ff["acc"][t], nan=-9) > 0
            ev.setdefault(t, []).extend((int(i), float(y[i]), spec["hold"]) for i in np.where(ok)[0])
    elif kind == "earn":                   # 財報公布漂移：法定公告日收盤後，單季 EPS 年增額／股價最大者
        for t in P["earn_events"]:
            y = ff["sue"][t]
            ok = P["elig"][pool][t] & np.isfinite(y) & (y >= spec["thr"])
            ev.setdefault(t, []).extend((int(i), float(y[i]), spec["hold"]) for i in np.where(ok)[0])
    elif kind == "exdiv":                  # 除息前後：除息日前 d 個交易日訊號（須在公告日之後），持有到除息日後 m 日
        dv = P["div_events"]
        ci = P["ci"]
        for code, a, ex_i, ann in zip(dv["code"], dv["amount"], dv["ex_i"], dv["announce_date"]):
            i = ci[code]
            if ann is None or ann != ann:
                continue
            ai = idx.searchsorted(pd.Timestamp(ann)) + 1
            t = ex_i - spec["d"]
            if t < ai or t >= len(idx) or not P["elig"][pool][t, i]:      # 訊號日當天消息已公告才算（公告日隔天起）
                continue
            px = P["rawC"][t, i]
            if not np.isfinite(px) or a / px < spec["thr"]:
                continue
            ev.setdefault(t, []).append((int(i), float(a / px), spec["d"] + spec["m"] + 1))
    elif kind == "inst":                   # 投信買超＋營收成長（S3）：每日收盤後，投信買超占量達門檻、單月營收近三月年增>0（可選：外資當日賣超）
        for t in range(1, len(idx)):
            tb = ff["trust_buy"][t]
            ok = P["elig"][pool][t] & np.isfinite(tb) & (tb >= spec["thr"]) & (np.nan_to_num(ff["yoy3"][t], nan=-9) > 0)
            if spec.get("fsell"):
                ok &= np.nan_to_num(ff["foreign_net"][t], nan=0) < 0
            if ok.any():
                ev[t] = [(int(i), float(tb[i]), spec["hold"]) for i in np.where(ok)[0]]
    else:
        raise ValueError(kind)
    return ev


def run_event(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf = P["O"], P["Cf"]
    key = ("ev", json.dumps({k: spec[k] for k in sorted(spec) if k in ("ev", "thr", "hold", "acc", "d", "m", "fsell")}), pool)
    cache = P.setdefault("_ev", {})
    if key not in cache:
        cache[key] = build_events(P, spec, pool)
    ev = cache[key]
    K = spec["K"]
    cash, sh, ent, ex_at = 1.0, {}, {}, {}
    eq = np.full(len(idx), np.nan); inv = np.zeros(len(idx)); tr = []; buys = 0.0
    pend = []
    for t in range(lo_i, hi_i + 1):
        for i in [i for i, d in ex_at.items() if d <= t and i in sh]:
            cash += _sell(P, t, i, sh, ent, tr, f"事件持有期滿（{spec.get('hold', 'ex')}）", trades)
            del sh[i]; ex_at.pop(i)
        eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
        for i, sc_, h in pend:
            if i in sh or not np.isfinite(O[t, i]):
                continue
            amt = min(cash, eq_open / K)
            if amt <= 0:
                continue
            px = O[t, i] * (1 + SLIP)
            sh[i] = amt / (px * (1 + FEE)); cash -= amt; buys += amt
            ent[i] = (t, px, sc_); ex_at[i] = t + h
        pend = []
        eq[t] = cash + sum(sh[i] * Cf[t, i] for i in sh); inv[t] = (eq[t] - cash) / eq[t]
        if t >= hi_i:
            break
        if t in ev and S.mkt_state(P, spec, t, pool):
            room = K - len(sh)
            cand = sorted((e for e in ev[t] if e[0] not in sh), key=lambda e: -e[1])[:max(room, 0)]
            pend = cand
    return _finish(P, eq, inv, tr, buys, lo_i, hi_i, sh, ent, trades)


def run(P, spec, pool, lo, hi, trades=False):
    return (run_event if "ev" in spec else run_periodic)(P, spec, pool, lo, hi, trades)


# ------------------------------------------------------------------ 批次登記
def _grid(base, **axes):
    import itertools
    ks = list(axes)
    return [dict(base, **dict(zip(ks, v))) for v in itertools.product(*[axes[k] for k in ks])]


def batches():
    B = {}
    mfs = (None, "br200", "faber")
    B["A 價值單因子（本益比／淨值比／殖利率／EV÷EBIT）"] = _grid(dict(rebal="Q"), comps=[("ep",), ("bp",), ("dy",), ("ey_ebit",)], N=(10, 20, 30), mf=mfs, flt=(None, "above200"))
    B["B 價值複合（含 Magic Formula）"] = _grid(dict(rebal="Q"), comps=[("ep", "bp"), ("ep", "bp", "dy"), ("ey_ebit", "roa_ebit"), ("bp", "roe")], N=(10, 20, 30), mf=mfs)
    B["C 品質（ROE／毛利率穩定／Piotroski／資本報酬）"] = _grid(dict(rebal="Q"), comps=[("roe",), ("roa_ebit", "gm"), ("gm", "gmstab"), ("roe", "gm", "gmstab", "roa_ebit"), ("fs",), ("fs", "bp")], N=(10, 20, 30), mf=("br200", "faber"))
    B["D 價值＋動能"] = _grid(dict(), comps=[("ep", "bp", "nh"), ("bp", "mom252"), ("ep", "mom252"), ("dy", "nh"), ("ey_ebit", "roa_ebit", "nh")], N=(10, 20, 30), rebal=("M", "Q"), mf=("br200", "faber"))
    B["E 品質＋動能"] = _grid(dict(), comps=[("roe", "nh"), ("gm", "nh"), ("roe", "gm", "mom252"), ("roa_ebit", "nh", "mom252")], N=(10, 20, 30), rebal=("M", "Q"), mf=("br200", "faber"))
    B["F 低淨值比＋營收加速"] = _grid(dict(), comps=[("bp", "acc"), ("bp", "yoy3"), ("bp", "acc", "yoy3"), ("ep", "acc")], N=(10, 20, 30), rebal=("M", "Q"), mf=("br200", "faber"))
    B["G 多因子打分（價值＋品質＋動能＋成長）"] = _grid(dict(), comps=[("ep", "bp", "dy", "roe", "gm", "nh", "yoy3"), ("ep", "bp", "roe", "nh"), ("ey_ebit", "roa_ebit", "bp", "nh", "acc")], N=(10, 20, 30), rebal=("M", "Q"), mf=("br200", "faber"))
    B["H 大型股一個月反轉"] = _grid(dict(rebal="M"), comps=[("-r20",), ("-r5",), ("-r20", "bp"), ("-r20", "roe")], N=(10, 20, 30), mf=mfs, flt=(None, "above200"))
    B["I 事件：月營收公布漂移"] = _grid(dict(ev="rev"), thr=(0.3, 0.5), hold=(10, 20, 40), K=(10, 20, 30), mf=(None, "br200"))
    B["J 事件：財報公布漂移"] = _grid(dict(ev="earn"), thr=(0.005, 0.015), hold=(20, 40, 60), K=(10, 20), mf=(None, "br200"))
    B["K 事件：除息前後"] = _grid(dict(ev="exdiv"), thr=(0.03, 0.05), d=(3, 5, 8), m=(0, 3, 8), K=(10, 20), mf=(None,))
    return B


def skey(sp):
    return json.dumps({k: sp[k] for k in sorted(sp)}, ensure_ascii=False)


def feat_keys(sp):
    if "ev" in sp:
        return {"rev": ["yoy1"], "earn": ["sue"], "exdiv": []}[sp["ev"]]
    return [c.lstrip("-") for c in sp["comps"]] + (["eps_pos"] if sp.get("flt") in ("pos", "above200_pos") else [])


# ------------------------------------------------------------------ 評估
def metrics_row(P, sp, pool, lo, hi):
    r = run(P, sp, pool, lo, hi)
    b = S.bench(P, lo, hi)
    s, bs = S.eq_stats(r["eq"]), S.eq_stats(b)
    y, by = S.yearly(r["eq"]), S.yearly(b)
    return dict(cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], bh=bs["cagr"], bh_mdd=bs["mdd"], excess=s["cagr"] - bs["cagr"],
                ywin=int((y > by.reindex(y.index)).sum()), ynum=len(y), yrets=json.dumps({int(k): round(float(v), 4) for k, v in y.items()}),
                y0050=json.dumps({int(k): round(float(v), 4) for k, v in by.items()}), expo=r["expo"], turn=r["turnover"],
                years=(r["eq"].index[-1] - r["eq"].index[0]).days / 365.25)


def train_stage(P, batch_filter=None):
    rows = []
    fs_cache = {}
    for name, specs in batches().items():
        if batch_filter and not name.startswith(batch_filter):
            continue
        for sp in specs:
            fk = tuple(feat_keys(sp))
            if fk not in fs_cache:
                fs_cache[fk] = family_start(P, fk) if fk else TRAIN[0]
            st = fs_cache[fk]
            lo = max(TRAIN[0], st) if st else None
            for pool in (200, 100):
                if lo is None or pd.Timestamp(lo) > pd.Timestamp(TRAIN[1]) - pd.Timedelta(days=30):
                    rows.append(dict(batch=name, spec=skey(sp), fam=sp.get("ev", "factor"), pool=pool, lo=lo, hi=TRAIN[1], excess=np.nan, years=0.0))
                    continue
                m = metrics_row(P, sp, pool, lo, TRAIN[1])
                rows.append(dict(batch=name, spec=skey(sp), fam=sp.get("ev", "factor"), pool=pool, lo=lo, hi=TRAIN[1], **m))
        print(name, len(specs), flush=True)
    reg = pd.DataFrame(rows)
    return select(P, reg)


def select(P, reg):
    off = {}

    def eff(r):
        d = json.loads(r["spec"]); fk = d.get("mf")
        if fk is None:
            return True
        if r["lo"] is None:
            return False
        key = (r["lo"], fk, r["pool"] if fk == "br200" else 0)
        if key not in off:
            sh_ = S.filter_off_share(P, r["lo"], r["hi"])
            off[key] = sh_.get("br200(200池)" if fk == "br200" else fk, 0.0) >= 0.05
        return off[key]
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
    reg["兩池通過訓練"] = reg.groupby("spec")["單池通過訓練"].transform("all") & (reg.groupby("spec")["pool"].transform("nunique") == 2)
    return reg


def pick_finalists(reg, k=3):
    c = reg[reg["兩池通過訓練"]].groupby("spec")["excess"].min().sort_values(ascending=False)
    return list(c.index[:k])


def holdout(P, spec_json, pool, window):
    """保留期每個入選者每個池只跑一次；已跑過就只讀紀錄（保證只看一次）。"""
    OUT.mkdir(parents=True, exist_ok=True)
    log = pd.read_csv(LOG) if LOG.exists() else pd.DataFrame(columns=["spec", "pool", "window"])
    hit = log[(log["spec"] == spec_json) & (log["pool"] == pool) & (log["window"] == window)]
    if len(hit):
        return hit.iloc[0].to_dict()
    lo, hi = {"內部保留": INNER, "最終保留": FINAL}[window]
    m = metrics_row(P, json.loads(spec_json), pool, lo, hi)
    row = dict(spec=spec_json, pool=pool, window=window, lo=lo, hi=hi, 執行時間=time.strftime("%Y-%m-%d %H:%M:%S"), **m)
    pd.concat([log, pd.DataFrame([row])], ignore_index=True).to_csv(LOG, index=False, encoding="utf-8-sig")
    return row


def trade_log(P, sp, pool, window):
    lo, hi = {"訓練期": TRAIN, "內部保留": INNER, "最終保留": FINAL}[window]
    t = run(P, sp, pool, lo, hi, trades=True)["trades"]
    if t.empty:
        return t
    c50, o50 = P["c50"], P["o50"]
    t["同期0050報酬"] = [(c50.get(r["exit"], np.nan) / o50.get(r["entry"], np.nan) - 1) for _, r in t.iterrows()]
    t["持有天數"] = (t["exit"] - t["entry"]).dt.days
    return t.assign(spec=skey(sp), pool=pool, 區間=window)


def load_all():
    return add_factor_features(S.build_features(S.load5()))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    P = load_all()
    reg = train_stage(P)
    reg.drop(columns=["yrets", "y0050"], errors="ignore").to_csv(OUT / "registry_train.csv", index=False, encoding="utf-8-sig")
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
    main()


# ------------------------------------------------------------------ 網路宣稱策略的逐條重現（web_research.md；只診斷，不用來選參數）
REPL = {
    "S1 FinLab 複合動能優化版": dict(
        claim="年化 36.4%（2013-09～2026-06），MDD -40.1%，同期 0050 含息 20.9%",
        variants=[("法定公告日・流動性前600", dict(comps=("mom252",), N=10, rebal="Q", mf=None, gt={"roe": 0.10, "yoy1": 0.0}), 600, "2016-05-16"),
                  ("法定公告日・流動性前200", dict(comps=("mom252",), N=10, rebal="Q", mf=None, gt={"roe": 0.10, "yoy1": 0.0}), 200, "2016-05-16"),
                  ("【前視對照】期末即用財報・月底隔天用營收", dict(comps=("mom252",), N=10, rebal="Q", mf=None, gt={"roe": 0.10, "yoy1": 0.0}, leak=True), 600, "2016-05-16")]),
    "S2 FinLab 月營收動能": dict(
        claim="年化 50.0%（2015～2026），夏普 1.46，MDD -35.6%，0050 含息 21.3%（流動性濾網版 48.6%、20 檔版 43.1%）",
        variants=[("營收強度排序・前600・10檔", dict(comps=("rv312",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}), 600, "2015-01-02"),
                  ("營收強度排序・前200・10檔", dict(comps=("rv312",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}), 200, "2015-01-02"),
                  ("營收強度排序・前600・20檔", dict(comps=("rv312",), N=20, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}), 600, "2015-01-02"),
                  ("價格動能排序・前600・10檔", dict(comps=("mom126",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}), 600, "2015-01-02"),
                  ("【前視對照】月底隔天用營收", dict(comps=("rv312",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}, leak=True), 600, "2015-01-02")]),
    "S3 FinLab 投信買超＋營收動能": dict(
        claim="年化 33.9%（另一篇 30.1%；2015～2026），純投信 9.7%（7.4%），0050 含息 20.6%",
        variants=[(f"投信買超占量≥{thr:.0%}・持有{h}日・{'外資同日賣超・' if fs_ else ''}前600・K=10", dict(ev="inst", thr=thr, hold=h, fsell=fs_, K=10, mf=None), 600, "2015-01-02")
                  for thr in (0.01, 0.03) for h in (5, 20) for fs_ in (False, True)]),
    "S4 FinLab 低波動優化版": dict(
        claim="年化 33.3%（2013-09～2026-06），夏普 1.13，MDD -38.2%，0050 含息 20.9%",
        variants=[("風險調整動能x2＋ROE＋營收＋動能・前600・15檔", dict(comps=("rsmom", "rsmom", "roe", "yoy3", "mom126"), N=15, rebal="Q", mf=None, gt={"roe": 0.10, "yoy3": 0.0}), 600, "2016-05-16"),
                  ("【前視對照】", dict(comps=("rsmom", "rsmom", "roe", "yoy3", "mom126"), N=15, rebal="Q", mf=None, gt={"roe": 0.10, "yoy3": 0.0}, leak=True), 600, "2016-05-16")]),
    "S5 FinLab 四因子複合": dict(
        claim="日夏普 1.46 對 0050 的 1.22、MDD -24.8% 對 -33.96%（2018～2026）；教學版年化 29.45%；FinLab 自承年化沒贏 0050",
        variants=[("ROE＋動能＋低波＋營收・前600・25檔月換股", dict(comps=("roe", "mom252", "-vol", "yoy3"), N=25, rebal="M", mf=None), 600, "2016-05-16"),
                  ("ROE＋動能＋低波＋營收・前200・25檔月換股", dict(comps=("roe", "mom252", "-vol", "yoy3"), N=25, rebal="M", mf=None), 200, "2016-05-16"),
                  ("【前視對照】", dict(comps=("roe", "mom252", "-vol", "yoy3"), N=25, rebal="M", mf=None, leak=True), 600, "2016-05-16")]),
    "S6 鉅亨易策略 高殖利率低估": dict(
        claim="10 年年化 21.02%，大盤 12.06%（前 5 名、每年換股）",
        variants=[(f"殖利率3年均>5%・PB<1・近5日三大法人每日買超・前{n}名年換股・前600", dict(comps=("dy3",), N=n, rebal="Y", mf=None, gt={"dy3": 0.05, "bp": 1.0}, ge={"inst5": 1}), 600, "2016-05-16") for n in (5, 10, 20, 30)]
                 + [("【不含PB條件，2013 起】殖利率3年均>5%・近5日法人買超・前10名", dict(comps=("dy3",), N=10, rebal="Y", mf=None, gt={"dy3": 0.05}, ge={"inst5": 1}), 600, "2013-06-03")]),
    "S7 TEJ 基石價值（原文六道條件未取得，以公開描述近似）": dict(
        claim="年化 25.67%，大盤 17.79%（TEJ 量化月報第 25 期，約 2026-06 前；殖利率最高前 30 檔，每年 7 月初調倉）",
        variants=[("非金融・流動性前200・殖利率最高30檔（2012-07 起，無獲利條件）", dict(comps=("dy",), N=30, rebal="J", mf=None, nofin=True), 200, "2012-07-02"),
                  ("非金融・前200・近四季獲利為正＋ROE>0・殖利率最高30檔（2016-07 起）", dict(comps=("dy",), N=30, rebal="J", mf=None, nofin=True, gt={"eps_pos": 0.5, "roe": 0.0}), 200, "2016-07-01"),
                  ("非金融・前600・近四季獲利為正＋ROE>0・殖利率最高30檔（2016-07 起）", dict(comps=("dy",), N=30, rebal="J", mf=None, nofin=True, gt={"eps_pos": 0.5, "roe": 0.0}), 600, "2016-07-01")]),
    "S8 zaoldyeck 神奇公式＋F-score": dict(
        claim="2014-05～2019-04：原版 9.61%、加 F-score 20.62%、全加 25.09%（夏普 0.34）",
        variants=[("神奇公式原版（EV÷EBIT＋EBIT÷總資產代理）前10・非金融・前600", dict(comps=("ey_ebit", "roa_ebit"), N=10, rebal="E", mf=None, nofin=True), 600, "2016-05-16"),
                  ("＋F-score≥6／7（原文 ≥8／9）", dict(comps=("ey_ebit", "roa_ebit"), N=10, rebal="E", mf=None, nofin=True, ge={"fs": 6}), 600, "2017-05-16"),
                  ("＋F-score＋營收年增>0＋營業利益年增>0（缺現金流）", dict(comps=("ey_ebit", "roa_ebit"), N=10, rebal="E", mf=None, nofin=True, ge={"fs": 6}, gt={"yoy1": 0.0, "ebit_yoy": 0.0}), 600, "2017-05-16")]),
    "S9 學術：市值營收比價值＋反向規模": dict(
        claim="方向性：台股有價值溢酬與反向規模，市值營收比最好；無年化、無對 0050 數字",
        variants=[("營收市值比最高20檔・非金融・前600", dict(comps=("sr",), N=20, rebal="Q", mf=None, nofin=True), 600, "2016-05-16"),
                  ("營收市值比＋小市值・前600", dict(comps=("sr", "-mcap"), N=20, rebal="Q", mf=None, nofin=True), 600, "2016-05-16"),
                  ("營收市值比＋小市值・前200", dict(comps=("sr", "-mcap"), N=20, rebal="Q", mf=None, nofin=True), 200, "2016-05-16")]),
}
SPLITS = {"全段": (None, "2026-10-22"), "訓練期": (None, TRAIN[1]), "內部保留": INNER, "最終保留": FINAL}


def replicate(P, only=None):
    rows = []
    for sid, d in REPL.items():
        if only and not sid.startswith(only):
            continue
        for label, sp, pool, lo in d["variants"]:
            for wn, (a, b) in SPLITS.items():
                a = a or lo
                a = max(a, lo)
                if pd.Timestamp(a) >= pd.Timestamp(b) - pd.Timedelta(days=200):
                    continue
                m = metrics_row(P, sp, pool, a, b)
                rows.append(dict(策略=sid, 原宣稱=d["claim"], 變體=label, 池=pool, 窗口=wn, 起=a, 迄=b, 規格=skey(sp),
                                 年化=m["cagr"], 同窗0050=m["bh"], 差=m["cagr"] - m["bh"], 回撤=m["mdd"], 回撤0050=m["bh_mdd"], 夏普=m["sharpe"],
                                 逐年贏=f"{m['ywin']}/{m['ynum']}", 平均持股比=m["expo"], 年換手=m["turn"]))
        print(sid, flush=True)
    return pd.DataFrame(rows)
