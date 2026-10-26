"""策略委員會第三回合：用同一套引擎（pipeline/compute/lev_lab.py）把所有最終候選並排重跑。

統一口徑（寫死，不隨候選改變）：
  * 讀檔：price_daily 等資料表一律「逐檔 read_parquet 再 concat」（lev_lab._rd）。2026 分區的欄位型別與前幾年不同
    （volume 變 double、多 name/px_source 欄），整個資料夾一次讀會炸，見 r2_futures 第 0 節。
  * 0050：還原 2025-06-18 一拆四；含息（除息日開盤加回）。股利資料 2009-10-23 才有 -> 2009 年以前的 0050 報酬沒有股利、
    年化被低估約 2.8%/年，A 段（2003-07~2014）的門檻因此偏鬆。本腳本同時跑「補股利」敏感度（2009-10 前每日加 2.8%/252，
    2.8% 為假設，不是資料）。
  * 00631L：2014-10-31 上市後用真實價格（2026-03 的一拆二十二已還原）；之前用「2 x 加權指數日報酬 - 內扣 1.04% - 融資 +
    校準殘差」的代理序列（lev_lab 第九節）。
  * 台指期：futures_lab5.adjusted_tx() 的換月修正序列（結算隔日用現貨報酬修正）。每次結算額外扣 4.5 點（滑價 4 點 + 手續費
    約 0.5 點，相對指數水位），建倉／調整成本 0.03%（手續費+滑價）+ 期交稅 0.002%。現金（含期貨保證金以外的權益）按
    lev_lab 的年度定存利率表計息（RF_BY_YEAR），這和 r2_futures 的 +0.83%、round5 的 1.0% 都不同，口徑差見 r3_final 第三節。
  * ETF 成本：手續費 0.1425%（不打折）、賣出證交稅 0.1%、滑價 0.05%（0050）／0.10%（正二），內扣已含在價格或代理序列。
  * 訊號：t 日收盤後產生，t+1 日開盤才換倉（lev_lab 引擎把日報酬拆成隔夜與盤中兩段，換倉發生在兩段之間）。
  * 門檻：搭配 0050／槓桿 ETF／overlay（持有 0050）＝同期含息 0050 的 1.5 倍；純台指期＝同期含息 0050（1.0 倍）。

執行：python docs/strategy_lab/council/scripts/r3_unified.py（在 repo 根目錄；約 3~6 分鐘）
產出：docs/strategy_lab/council/r3_final.md、r3_results.csv
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402
from pipeline.compute import futures_lab5 as L5  # noqa: E402
from pipeline.compute import lev_lab as L  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "council"
IX = L.IX
PRE2009_YIELD = 0.028          # 假設：2009-10 以前 0050 的股利殖利率（資料湖沒有這段股利）
DIV_START = pd.Timestamp("2009-10-23")
M_INIT, M_MAINT = 0.10, 0.08   # 與 futures_lab2 相同：原始／維持保證金占名目比例
ROLL_PTS = 4.5                 # 每次換月：滑價 4 點 + 手續費約 0.5 點
TX_COST = L.TX_FEE + L.SLIP["TX"] + 0.00002
FUT_BAND = 0.10                # 期貨曝險偏離目標超過 0.10 倍才在『月檢查日』調整（lev_lab TX 家族同值）


# ------------------------------------------------------------------ 期貨引擎（含保證金模擬）
@njit(cache=True)
def sim_fut(ONs, IDs, ONtx, IDtx, LOWR, rfd, rollc, Ws, xt, chk, band, dd_trig, dd_rest, x_low, buys, sells, txc, m_maint, start_i):
    """兩個股票部位（0050、正二）加台指期。權益 = 股票市值 + 現金；期貨只佔保證金，損益併入現金。
    返回 (日報酬, 日末曝險 = 期貨名目/權益, 最低維持率, 追繳次數)。維持率 = 盤中低點權益 / (維持保證金率 x 期貨名目)。"""
    T = ONs.shape[0]
    S = np.zeros(2)
    C = 1.0
    Nf = 0.0
    ret = np.zeros(T)
    expo = np.zeros(T)
    peak = 1.0
    prev_close = 1.0
    reduced = False
    prev_x = -1.0
    minratio = 1e9
    calls = 0
    for t in range(start_i, T):
        # 隔夜：股票報酬、現金利息、期貨隔夜損益、結算換月成本
        for k in range(2):
            S[k] *= 1.0 + ONs[t, k]
        C *= 1.0 + rfd[t]
        C += Nf * ONtx[t]
        Nf *= 1.0 + ONtx[t]
        C -= Nf * rollc[t]
        E = S[0] + S[1] + C
        if E <= 0.0:
            ret[t] = -1.0 if prev_close > 0 else 0.0
            S[0] = 0.0; S[1] = 0.0; C = 0.0; Nf = 0.0
            prev_close = 0.0
            continue
        x_t = xt[t]
        if reduced and x_t > x_low:
            x_t = x_low
        do = (t == start_i) or (x_t != prev_x)
        if (not do) and chk[t]:
            if abs(Nf / E - x_t) > band:
                do = True
            for k in range(2):
                if abs(S[k] / E - Ws[t, k]) > band:
                    do = True
        if do:
            cost = 0.0
            for k in range(2):
                d = Ws[t, k] * E - S[k]
                cost += d * buys[k] if d > 0 else -d * sells[k]
                S[k] = Ws[t, k] * E
            dn = x_t * E - Nf
            cost += abs(dn) * txc
            Nf = x_t * E
            C = E - S[0] - S[1] - cost
            E = E - cost
            prev_x = x_t
        # 盤中：保證金檢查（用盤中低點，股票部位同步下跌的保守假設）
        E_open = E
        lowr = LOWR[t]
        if Nf > 0:
            e_low = E_open + (Nf + S[0] + S[1]) * lowr
            mreq = m_maint * Nf * (1.0 + lowr)
            if mreq > 0:
                ratio = e_low / mreq
                if ratio < minratio:
                    minratio = ratio
                if ratio < 1.0:
                    calls += 1
                    C += Nf * lowr
                    Nf = 0.0
        for k in range(2):
            S[k] *= 1.0 + IDs[t, k]
        C += Nf * IDtx[t]
        Nf *= 1.0 + IDtx[t]
        E = S[0] + S[1] + C
        ret[t] = E / prev_close - 1.0
        prev_close = E
        expo[t] = Nf / E if E > 0 else 0.0
        if E > peak:
            peak = E
        if dd_trig > 0:
            dd = 1.0 - E / peak
            if (not reduced) and dd >= dd_trig:
                reduced = True
            elif reduced and E >= peak * (1.0 - dd_rest):
                reduced = False
    return ret, expo, minratio, calls


# ------------------------------------------------------------------ 資料
def build_world(div_sens: bool = False):
    w = L.World(with_mom=False)
    if div_sens:
        m = w.cal < DIV_START
        w.ON[m, IX["A50"]] += PRE2009_YIELD / 252
        w.on50 = w.on50 + np.where(m, PRE2009_YIELD / 252, 0.0)
        w.r50 = (1 + w.on50) * (1 + w.id50) - 1
    adj, _, _ = L5.adjusted_tx()
    adj = adj.reindex(w.cal)
    w.tx_lowr = (adj["low"] / adj["open"] - 1).fillna(0.0).clip(upper=0.0).to_numpy()
    cal = w.cal
    settle = F.settle_days(cal)
    w.rollc = np.where(settle, ROLL_PTS / w.tse.to_numpy(), 0.0)
    w.rfd = w.ON[:, IX["CASH"]].copy()
    w.s2_first = None
    return w


def s2_legs(w):
    """S2 月營收動能（chips 精簡版）的隔夜／盤中報酬。規則：每月 11 日起第一個交易日 d 的『開盤』換股；
    決策只用到 d 的前一個交易日收盤以前的資料（revenue_monthly 的法定公布日是次月 10 日）。
    池：前一日的 60 日平均成交值前 200 檔 4 碼股；條件：近 3 月營收均值 / 近 12 月均值 > 1 且前一日收盤 > 60 日均線；
    取比值最大 10 檔等權。價格未還原、|日報酬|>10.5% 視為除權息設 0（股利少算約 3%/年），存活者偏誤未量化。
    成本：換手 x 0.2425%，賣出另加 0.3%。"""
    cols = ["date", "code", "open", "close", "turnover"]
    fs = [f for f in sorted(glob.glob(str(ROOT / "data" / "price_daily" / "**" / "*.parquet"), recursive=True)) if int(f.split("year=")[1][:4]) >= 2015]
    px = pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)       # 逐檔讀再 concat
    px = px[px.code.str.fullmatch(r"\d{4}")]
    px["date"] = pd.to_datetime(px["date"])
    C = px.pivot_table(index="date", columns="code", values="close", aggfunc="last").sort_index()
    O = px.pivot_table(index="date", columns="code", values="open", aggfunc="last").reindex(C.index)
    TO = px.pivot_table(index="date", columns="code", values="turnover", aggfunc="last").reindex(C.index)
    C, O, TO = C.reindex(w.cal), O.reindex(w.cal), TO.reindex(w.cal)
    cprev = C.ffill(limit=5).shift(1)
    on = O / cprev - 1
    idr = C / O - 1
    bad = (on.abs() > 0.105) | (idr.abs() > 0.105) | ((C / cprev - 1).abs() > 0.105)
    on = on.where(~bad, 0.0).fillna(0.0).to_numpy(); idr = idr.where(~bad, 0.0).fillna(0.0).to_numpy()
    ma60 = C.rolling(60).mean()
    tv60 = TO.rolling(60, min_periods=40).mean()
    rv = pd.concat([pd.read_parquet(f, columns=["ym", "code", "revenue"]) for f in sorted(glob.glob(str(ROOT / "data" / "revenue_monthly" / "**" / "*.parquet"), recursive=True))])
    RV = rv.pivot_table(index="ym", columns="code", values="revenue").sort_index()
    ratio = RV.rolling(3).mean() / RV.rolling(12, min_periods=12).mean()
    cal = w.cal
    T = len(cal)
    Wt = np.zeros((T, C.shape[1]), dtype=np.float32)
    cur = np.zeros(C.shape[1], dtype=np.float32)
    cost_on = np.zeros(T)
    first = None
    for ym in ratio.index:
        y, m = map(int, ym.split("-"))
        m += 1
        if m == 13:
            y, m = y + 1, 1
        d = int(cal.searchsorted(pd.Timestamp(y, m, 11)))
        if d >= T or d < 1:
            continue
        s = ratio.loc[ym].dropna()
        pool = tv60.iloc[d - 1].dropna().nlargest(200).index
        s = s[s.index.isin(pool) & (s > 1.0)]
        above = (C.iloc[d - 1] > ma60.iloc[d - 1]).reindex(s.index).fillna(False).astype(bool)
        s = s[above]
        pick = s.nlargest(10).index
        new = np.zeros(C.shape[1], dtype=np.float32)
        if len(pick):
            new[C.columns.get_indexer(pick)] = 1.0 / len(pick)
        diff = new - cur
        cost_on[d] = float(np.abs(diff).sum()) * 0.002425 + float(np.clip(-diff, 0, None).sum()) * 0.003
        Wt[d:] = new
        cur = new
        if first is None and len(pick):
            first = d
    on_p = (Wt * on).sum(axis=1) - cost_on
    id_p = (Wt * idr).sum(axis=1)
    return on_p, id_p, first


# ------------------------------------------------------------------ 訊號
def weekly_disaster(w, ma_weeks=40, dd=0.20):
    """災難停損：週收盤（加權指數）< 40 週均線且距 52 週高點回落 > 20% -> 1；週收盤回到 40 週線上 -> 0。
    週五（該週最後一個交易日）收盤判斷，回傳已 shift 的日序列（下一個交易日開盤才生效）。"""
    s = w.tse_full
    wk = s.index.to_period("W-FRI")
    wc = s.groupby(wk).last()
    wdate = s.groupby(wk).apply(lambda x: x.index[-1])
    ma = wc.rolling(ma_weeks).mean()
    hi = wc.rolling(52, min_periods=26).max()
    st = np.zeros(len(wc), np.int8); cur = 0
    for i in range(len(wc)):
        if np.isnan(ma.iloc[i]):
            st[i] = cur; continue
        if cur == 0 and wc.iloc[i] < ma.iloc[i] and wc.iloc[i] <= hi.iloc[i] * (1 - dd):
            cur = 1
        elif cur == 1 and wc.iloc[i] > ma.iloc[i]:
            cur = 0
        st[i] = cur
    ser = pd.Series(st, index=pd.DatetimeIndex(wdate.to_numpy()))
    return L.shift1(ser.reindex(w.cal, method="ffill").fillna(0).to_numpy().astype(float))


def tr_signal_series(w):
    """E2b 的訊號序列：0050 還原含息總報酬指數。2003-06-30 以前用加權指數接續（只為了讓 200 日線有暖機資料）。"""
    tr = pd.Series(np.cumprod(1 + w.r50), index=w.cal)
    pre = w.tse_full[w.tse_full.index < w.cal[0]]
    scale = tr.iloc[0] / w.tse_full.loc[w.cal[0]] if w.cal[0] in w.tse_full.index else 1.0
    return pd.concat([pre * scale, tr])


# ------------------------------------------------------------------ 指標
def monthly(w, r):
    s = pd.Series(r[w.start_i:], index=w.cal[w.start_i:])
    return (1 + s).groupby(s.index.to_period("M")).prod() - 1


def nw_t(x, lag=6):
    x = np.asarray(x, float); n = len(x); xm = x - x.mean()
    g0 = (xm * xm).sum() / n
    v = g0
    for l in range(1, lag + 1):
        v += 2 * (1 - l / (lag + 1)) * (xm[l:] * xm[:-l]).sum() / n
    return float(x.mean() / np.sqrt(v / n))


def rolling_stats(w, r, rb, mult, H):
    """每 21 個交易日一個起點的滾動 H 日窗口：策略年化 >= mult x 同窗 0050 年化 的比例，與最差窗口差距（點）。"""
    s0 = w.start_i
    ls = np.log1p(np.clip(r[s0:], -0.9999, None)); lb = np.log1p(np.clip(rb[s0:], -0.9999, None))
    cs = np.r_[0, np.cumsum(ls)]; cb = np.r_[0, np.cumsum(lb)]
    st = np.arange(0, len(ls) - H + 1, 21)
    cagr_s = np.exp((cs[st + H] - cs[st]) * 252 / H) - 1
    cagr_b = np.exp((cb[st + H] - cb[st]) * 252 / H) - 1
    gap = cagr_s - mult * cagr_b
    j = int(np.argmin(gap))
    return dict(n=len(st), pass_frac=float((gap >= 0).mean()), worst_gap=float(gap[j] * 100),
                worst_start=str(w.cal[s0 + st[j]].date()), worst_end=str(w.cal[s0 + st[j] + H - 1].date()))


def yearly_win(w, r, rb):
    idx = w.cal[w.start_i:]
    yrs = idx.year
    a = (1 + pd.Series(r[w.start_i:], index=idx)).groupby(yrs).prod() - 1
    b = (1 + pd.Series(rb[w.start_i:], index=idx)).groupby(yrs).prod() - 1
    full = [y for y in a.index if 2004 <= y <= 2025]          # 只算完整日曆年（2003 下半年、2026 未滿年不算）
    return float((a[full] >= b[full]).mean()), int((a[full] >= b[full]).sum()), len(full)


def boot_paths(w, r, rb, mult, n_rep=2000, years=10, block=40, seed=5):
    """穩健區塊重抽樣（同步抽策略與 0050 的日報酬）10 年路徑：
    p_window＝隨機抽一個 3 年窗口未達門檻的機率；p_any＝10 年路徑裡出現過任何一個未達門檻的 3 年窗口的機率；
    p_mdd60＝路徑內最大回撤超過 -60% 的機率。"""
    rng = np.random.default_rng(seed)
    a = np.clip(r[w.start_i:], -0.9999, None); b = rb[w.start_i:]
    n = len(a); H = years * 252
    idx = np.empty((n_rep, H), np.int64)
    idx[:, 0] = rng.integers(0, n, n_rep)
    jump = rng.random((n_rep, H)) < 1.0 / block
    rnd = rng.integers(0, n, (n_rep, H))
    for t in range(1, H):
        idx[:, t] = np.where(jump[:, t], rnd[:, t], (idx[:, t - 1] + 1) % n)
    ls = np.log1p(a)[idx]; lb = np.log1p(np.clip(b, -0.9999, None))[idx]
    cs = np.concatenate([np.zeros((n_rep, 1)), np.cumsum(ls, axis=1)], axis=1)
    cb = np.concatenate([np.zeros((n_rep, 1)), np.cumsum(lb, axis=1)], axis=1)
    W3 = 756
    st = np.arange(0, H - W3 + 1, 21)
    gs = np.exp((cs[:, st + W3] - cs[:, st]) * 252 / W3) - 1
    gb = np.exp((cb[:, st + W3] - cb[:, st]) * 252 / W3) - 1
    fail = gs < mult * gb
    eq = np.exp(cs)
    dd = eq / np.maximum.accumulate(eq, axis=1) - 1
    return dict(p_window=float(fail.mean()), p_any=float(fail.any(axis=1).mean()), p_mdd60=float((dd.min(axis=1) < -0.60).mean()))


def evaluate(w, bench, r, mult, boot=True):
    rb = bench.r
    out = {}
    for nm, (a, b) in {"A": L.SEGS["A 2003-07~2014"], "B": L.SEGS["B 2015~2020"], "C": L.SEGS["C 2021~"], "17-20": L.OOS["樣本外 2017~2020"]}.items():
        out[f"gap_{nm}"] = (L.cagr(L.window(w, r, a, b)) - mult * bench.c50(a, b)) * 100
    out["cagr"] = L.cagr(r[w.start_i:])
    out["cagr_0050"] = L.cagr(rb[w.start_i:])
    out["mdd"] = L.mdd(r[w.start_i:])[0]
    out["mdd_0050"] = L.mdd(rb[w.start_i:])[0]
    out["mdd_09"] = L.mdd(L.window(w, r, "2009-01-01", None))[0]
    for H, nm in ((756, "3y"), (1260, "5y")):
        s = rolling_stats(w, r, rb, mult, H)
        out[f"roll{nm}_pass"] = s["pass_frac"]; out[f"roll{nm}_worst"] = s["worst_gap"]
        out[f"roll{nm}_when"] = f"{s['worst_start']}~{s['worst_end']}"; out[f"roll{nm}_n"] = s["n"]
    yw = yearly_win(w, r, rb)
    out["year_win"] = yw[0]; out["year_win_txt"] = f"{yw[1]}/{yw[2]}"
    mr, mb = monthly(w, r), monthly(w, rb)
    d = (mr - mult * mb).to_numpy()
    out["t"] = float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))); out["nw_t"] = nw_t(d)
    out["months"] = len(d); out["excess_ann"] = float(d.mean() * 12 * 100)
    if boot:
        out.update(boot_paths(w, r, rb, mult))
    return out


# ------------------------------------------------------------------ 候選
def eng(w, W, flag, band=0.0, ON=None, ID=None):
    ON = w.ON if ON is None else ON
    ID = w.ID if ID is None else ID
    r, turn = L.sim(ON, ID, w.borrow, W, flag, band, w.buyc, w.sellc, w.start_i, IX["CASH"])
    return r, turn


def fut(w, xt, Ws=None, chk=None, dd_trig=0.0, dd_rest=0.10, x_low=0.0, rfd=None, rollc=None):
    T = len(w.cal)
    if Ws is None:
        Ws = np.zeros((T, 2))
    if chk is None:
        chk = L.periodic_flag(w.cal, "M")
    buys = np.array([w.buyc[IX["A50"]], w.buyc[IX["L2"]]]); sells = np.array([w.sellc[IX["A50"]], w.sellc[IX["L2"]]])
    r, expo, minr, calls = sim_fut(w.ON[:, [IX["A50"], IX["L2"]]].copy(), w.ID[:, [IX["A50"], IX["L2"]]].copy(), w.ON[:, IX["TX"]].copy(), w.ID[:, IX["TX"]].copy(),
                                   w.tx_lowr, w.rfd if rfd is None else rfd, w.rollc if rollc is None else rollc, Ws, np.asarray(xt, float), chk, FUT_BAND,
                                   dd_trig, dd_rest, x_low, buys, sells, TX_COST, M_MAINT, w.start_i)
    return r, dict(min_ratio=float(minr), calls=int(calls), max_expo=float(expo[w.start_i:].max()), avg_expo=float(expo[w.start_i:].mean()))


def candidates(w, s2):
    T = len(w.cal)
    C = {}

    def E(id_, name, r, mult=1.5, extra=None, rule=""):
        C[id_] = dict(id=id_, name=name, r=r, mult=mult, extra=extra or {}, rule=rule)

    # --- 個股＋ETF
    W, fl, band = L.build(w, "HOLD", dict(w50=0.0, w2=1.0, reb="N"))
    E("E1", "直接持有 00631L", eng(w, W, fl, band)[0])
    W, fl, band = L.build(w, "MA", dict(n=200, h=0.02, m=1, on="L2", off="L2_30"))
    E("E2", "200 日線±2%（加權指數訊號）：線上 100% 正二，線下 30% 正二 + 70% 現金", eng(w, W, fl, band)[0])
    sig = tr_signal_series(w)
    st = L.shift1(L.ma_state(w, 200, 0.02, 1, series=sig))
    Wb = L.base_W(T); L.fill_W(Wb, st, L.ON_MODES["L2"], L.OFF_MODES["L2_30"])
    E("E2b", "同 E2，訊號改用還原含息 0050", eng(w, Wb, L.change_flag(Wb))[0])
    W, fl, band = L.build(w, "HOLD", dict(w50=0.3, w2=0.7, reb="Q"))
    E("E3", "70% 正二 + 30% 0050，每季再平衡", eng(w, W, fl, band)[0])
    W, fl, band = L.build(w, "HOLD", dict(w50=0.5, w2=0.5, reb="B5"))
    E("E4", "50% 正二 + 50% 0050，偏離 5 點再平衡", eng(w, W, fl, band)[0])
    dis = weekly_disaster(w)
    W5 = L.base_W(T)
    W5[:, IX["L2"]] = np.where(dis > 0, 0.5, 0.9); W5[:, IX["CASH"]] = 1 - W5[:, IX["L2"]]
    E("E5", "90% 正二；災難停損（週線跌破 40 週且自 52 週高點回落 >20%）降到 50%", eng(w, W5, L.change_flag(W5))[0])
    # E6：80% 正二 + 20% S2；S2 還沒有資料前（2016-12 以前），這 20% 也放正二
    on_s, id_s, first = s2
    w.ON[:, IX["MOM"]] = on_s; w.ID[:, IX["MOM"]] = id_s
    W6 = L.base_W(T)
    has = np.arange(T) >= (first if first is not None else T)
    W6[:, IX["L2"]] = np.where(has, 0.8, 1.0); W6[:, IX["MOM"]] = np.where(has, 0.2, 0.0)
    fl6 = L.change_flag(W6, L.periodic_flag(w.cal, "A"))
    r6, _ = eng(w, W6, fl6)
    E("E6", "80% 正二 + 20% S2 月營收動能（2016-12 前 S2 無資料，該 20% 也放正二）", r6, extra=dict(s2_first=str(w.cal[first].date()) if first else ""))
    # --- 台指期（純期貨：門檻 = 1.0 x 0050）
    xs = {"F0": 1.0, "F1": 1.2, "F2": 1.3, "F3": 1.5}
    for k, x in xs.items():
        r, ex = fut(w, np.full(T, x))
        E(k, f"台指期 {x} 倍持有", r, mult=1.0, extra=ex)
    on200 = L.shift1(L.ma_state(w, 200, 0.0, 1))
    r, ex = fut(w, np.where(on200 > 0, 1.5, 1.0))
    E("F4", "台指期 200 日線：線上 1.5 倍、線下 1.0 倍", r, mult=1.0, extra=ex)
    r, ex = fut(w, np.full(T, 1.3), dd_trig=0.25, dd_rest=0.10, x_low=0.7)
    E("F5", "台指期 1.3 倍；權益回撤 >=25% 降到 0.7 倍，回到前高 -10% 內恢復", r, mult=1.0, extra=ex)
    r, ex = fut(w, np.full(T, 1.5), dd_trig=0.30, dd_rest=0.10, x_low=1.0)
    E("F6", "台指期 1.5 倍；權益回撤 >=30% 降到 1.0 倍，回到前高 -10% 內恢復（恢復條件沿用 F5）", r, mult=1.0, extra=ex)
    # --- overlay：0050 x 0.8 + 期貨 0.7 倍（持有 0050 -> 歸類為搭配 0050，門檻 1.5 倍）
    Ws = np.zeros((T, 2)); Ws[:, 0] = 0.8
    r, ex = fut(w, np.full(T, 0.7), Ws=Ws)
    E("O1", "overlay：0050 x 0.8 + 台指期 0.7 倍 + 現金 0.2（總曝險約 1.5）", r, mult=1.5, extra=ex)
    return C


def diag_e2(w, bench):
    """裁決 200 日線 B 段 +2.9／-0.9／-7.5：同一條規則只換訊號來源與成交口徑。"""
    T = len(w.cal)
    rows = []
    src = {
        "加權指數": w.tse_full,
        "0050 還原含息": tr_signal_series(w),
        "0050 分割還原、不含息": (lambda c: pd.concat([w.tse_full[w.tse_full.index < c.index[0]] * (c.iloc[0] / w.tse_full.loc[c.index[0]]), c]))(pd.Series(w.c50, index=w.cal).dropna()),
    }
    ON0, ID0 = w.ON, w.ID
    full = (1 + ON0) * (1 + ID0) - 1
    fills = {"次日開盤成交（本專案口徑）": (ON0, ID0), "次日收盤成交": (full, np.zeros_like(full)), "同日收盤成交（前視，僅供對照）": (np.zeros_like(full), full)}
    for sn, series in src.items():
        st = L.shift1(L.ma_state(w, 200, 0.02, 1, series=series))
        W = L.base_W(T); L.fill_W(W, st, L.ON_MODES["L2"], L.OFF_MODES["L2_30"])
        for fn, (on, idr) in fills.items():
            r, _ = eng(w, W, L.change_flag(W), 0.0, on, idr)
            row = dict(訊號=sn, 成交=fn)
            for nm, (a, b) in {"A": L.SEGS["A 2003-07~2014"], "B": L.SEGS["B 2015~2020"], "C": L.SEGS["C 2021~"]}.items():
                row[nm] = (L.cagr(L.window(w, r, a, b)) - 1.5 * bench.c50(a, b)) * 100
            rows.append(row)
    return pd.DataFrame(rows)


def diag_f0(w, bench):
    """裁決『1 倍台指期在 2008~2016 比 0050 高 2.6 點』：同一個 1 倍持有，只換現金利率與換月成本。"""
    T = len(w.cal)
    a, b = "2008-01-01", "2016-12-31"
    c50 = L.cagr(L.window(w, bench.r, a, b))
    rows = []
    cfg = {
        "本專案：定存利率表 + 結算 4.5 點": dict(),
        "現金利率 0%": dict(rfd=np.zeros(T)),
        "現金利率 1.0%（round5）": dict(rfd=np.full(T, 0.01 / 252)),
        "現金利率 +0.83% 加成（r2_futures）": dict(rfd=w.rfd + 0.0083 / 252),
        "無換月成本": dict(rollc=np.zeros(T)),
        "現金 1% 且無換月成本": dict(rfd=np.full(T, 0.01 / 252), rollc=np.zeros(T)),
    }
    for nm, kw in cfg.items():
        r, _ = fut(w, np.full(T, 1.0), **kw)
        c = L.cagr(L.window(w, r, a, b))
        rows.append({"設定": nm, "1 倍台指期 2008~2016 年化": c * 100, "0050 含息 2008~2016": c50 * 100, "差距(點)": (c - c50) * 100})
    return pd.DataFrame(rows)


RULES = {
    "E1": "買進 00631L 100%，之後不動。每天、每週都不用做事；只有年度要確認它沒有下市或改規格。",
    "E2": "每天收盤後：看加權指數收盤價與 200 日簡單均線。收盤 > 均線 x 1.02 -> 狀態＝『多』；收盤 < 均線 x 0.98 -> 狀態＝『空』；落在 ±2% 帶內 -> 維持上一個狀態。"
          "狀態改變的隔天開盤：『多』＝100% 正二；『空』＝30% 正二 + 70% 現金（定存或貨幣基金）。每週不用額外做事。",
    "E2b": "同 E2，但看的是『還原含息的 0050』與它的 200 日均線（不是加權指數）。",
    "E3": "70% 正二 + 30% 0050。每季第一個交易日開盤把比例調回 70/30，平時不動。",
    "E4": "50% 正二 + 50% 0050。每天收盤檢查正二占比，偏離 50% 超過 5 個百分點，隔天開盤調回 50/50。",
    "E5": "平時 90% 正二 + 10% 現金。每週五收盤檢查：加權指數週收盤 < 40 週均線 且 比 52 週高點低 20% 以上 -> 下週一開盤降到 50% 正二 + 50% 現金；"
          "之後週五收盤回到 40 週線上方 -> 下週一開盤回 90%。",
    "E6": "80% 正二 + 20% S2 月營收動能。S2：每月 11 日後第一個交易日開盤，在『前一日 60 日均成交值前 200 檔 4 碼股』中，挑近 3 月均營收 / 近 12 月均營收 > 1 且前一日收盤 > 60 日均線者，"
          "取比值最大 10 檔等權，換股前先賣出不符者。每年 1 月第一個交易日把正二與 S2 調回 80/20。2016-12 以前 S2 沒有營收資料，那 20% 放正二。",
    "F0": "權益全部放現金（定存），期貨名目維持 1.0 x 權益。每月結算日後第一個交易日算口數 = 權益 x 1.0 /（指數 x 200）；實際曝險與目標差超過 0.10 倍才調口數。結算前一日換月。",
    "F1": "同 F0，目標改為 1.2 倍。", "F2": "同 F0，目標改為 1.3 倍。", "F3": "同 F0，目標改為 1.5 倍。",
    "F4": "每天收盤：加權指數 > 200 日均線 -> 目標 1.5 倍；否則 1.0 倍。狀態改變的隔天開盤調口數；其餘同 F0。",
    "F5": "目標 1.3 倍。每天收盤算權益距歷史高點的回撤：>= 25% -> 隔天開盤降到 0.7 倍；權益回到距前高 10% 以內 -> 隔天開盤回 1.3 倍。其餘同 F0。",
    "F6": "目標 1.5 倍。權益回撤 >= 30% -> 隔天開盤降到 1.0 倍；回到距前高 10% 以內 -> 回 1.5 倍（恢復條件委員沒寫，沿用 F5）。其餘同 F0。",
    "O1": "80% 0050 + 20% 現金，另開台指期 0.7 倍名目（現金當保證金與緩衝）。每月第一個交易日檢查，0050 占比或期貨曝險偏離超過 0.10 就調回；結算前一日換月。",
}


def pc(x, d=1):
    return f"{x * 100:.{d}f}%"


def write_md(w, bench, df, ref, d2, d0, gross):
    a = {nm: bench.c50(*seg) * 100 for nm, seg in {"A": L.SEGS["A 2003-07~2014"], "B": L.SEGS["B 2015~2020"], "C": L.SEGS["C 2021~"], "17-20": L.OOS["樣本外 2017~2020"]}.items()}
    d = df.sort_values("roll5y_pass", ascending=False).reset_index(drop=True)
    T1 = ["| 排名 | ID | 方案 | 門檻 | 全期年化 | 最大回撤（全期／2009 後） | 滾動 5 年達標 | 最差 5 年窗口（差距點，期間） | 滾動 3 年達標 | 逐年勝 0050 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in d.iterrows():
        T1.append(f"| {i + 1} | {r.id} | {r['name']} | {r.mult:g} x 0050 | {pc(r.cagr)} | {pc(r.mdd, 0)}／{pc(r.mdd_09, 0)} | {pc(r.roll5y_pass, 0)}（{int(round(r.roll5y_pass * r.roll5y_n))}/{int(r.roll5y_n)}） | {r.roll5y_worst:+.1f}，{r.roll5y_when} | {pc(r.roll3y_pass, 0)} | {r.year_win_txt} |")
    T2 = ["| ID | A 2003-07~2014 | B 2015~2020 | C 2021~ | 2017~2020 | A（補 2009 前股利） | NW t | 月超額年化 | P(隨機 3 年窗口未達標) | P(10 年內出現未達標 3 年窗口) | P(10 年內回撤 < -60%) | 保證金：最低維持率／追繳／平均曝險 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        mg = f"{r.x_min_ratio:.1f} 倍／{int(r.x_calls)} 次／{r.x_avg_expo:.2f}" if "x_min_ratio" in df and pd.notna(r.get("x_min_ratio")) else "（無期貨）"
        T2.append(f"| {r.id} | {r.gap_A:+.1f} | {r.gap_B:+.1f} | {r.gap_C:+.1f} | {r['gap_17-20']:+.1f} | {r.gap_A_div:+.1f} | {r.nw_t:.2f} | {r.excess_ann:+.1f}% | {pc(r.p_window, 0)} | {pc(r.p_any, 0)} | {pc(r.p_mdd60, 0)} | {mg} |")
    D2 = ["| 訊號來源 | 成交口徑 | A | B | C |", "|---|---|---|---|---|"] + [f"| {r.訊號} | {r.成交} | {r.A:+.1f} | {r.B:+.1f} | {r.C:+.1f} |" for _, r in d2.iterrows()]
    D0 = ["| 設定 | 1 倍台指期 2008~2016 年化 | 0050 含息 | 差距（點） |", "|---|---|---|---|"] + [f"| {r['設定']} | {r.iloc[1]:.2f}% | {r.iloc[2]:.2f}% | {r.iloc[3]:+.2f} |" for _, r in d0.iterrows()]

    def g(i, c):
        return float(df[df.id == i][c].iloc[0])

    def s(i, c):
        return str(df[df.id == i][c].iloc[0])

    M = []
    M.append("# 策略委員會第三回合：統一口徑定案（r3_final）\n")
    M.append("> 研究回測，非買賣建議、不下單。程式：`docs/strategy_lab/council/scripts/r3_unified.py`（引擎＝`pipeline/compute/lev_lab.py`，期貨部分另有保證金模擬）；逐候選數字：`r3_results.csv`。\n")
    M.append("## 一、統一口徑（全部候選同一套，這是各人數字對不起來的主因）\n")
    M.append("| 項目 | 設定 |\n|---|---|")
    for k, v in [
        ("讀檔", "price_daily 等逐檔 read_parquet 再 concat（2026 分區 volume 型別是 double、多 name／px_source 欄，整個資料夾一次讀會炸；見 r2_futures 第 0 節）"),
        ("0050", "還原 2025-06-18 一拆四；含息（除息日開盤加回）。**股利資料 2009-10-23 才有，2009 年以前的 0050 沒有股利、可信度較低**（年化被低估，A 段門檻偏鬆）；表 2 另列『補 2009 前股利』敏感度（假設殖利率 2.8%/年，是假設不是資料）"),
        ("00631L", "2014-10-31 起真實價格（2026-03 一拆二十二已還原）；之前用 2 x 加權指數日報酬 - 內扣 1.04% - 融資 + 校準殘差（lev_lab 第九節）的代理序列。**A 段的達標依賴這個代理假設**"),
        ("台指期", "futures_lab5.adjusted_tx() 換月修正序列；每次結算再扣 4.5 點（滑價 4 + 手續費 0.5）；調整成本 0.03% + 期交稅 0.002%；現金（權益）按定存利率表計息（RF_BY_YEAR，約 0.8%~2.4%，假設）；保證金率 原始 10%／維持 8%（futures_lab2）"),
        ("ETF 成本", "手續費 0.1425%（不打折）、賣出證交稅 0.1%、滑價 0.05%（0050）／0.10%（正二）；內扣已含在價格或代理序列"),
        ("成交", "訊號收盤後產生、隔日開盤成交（引擎把日報酬拆成隔夜＋盤中兩段，換倉在兩段之間）"),
        ("門檻", "搭配 0050／槓桿 ETF／overlay＝同期含息 0050 x 1.5；純台指期＝同期含息 0050 x 1.0（Andy 的規則；overlay 持有 0050 歸『搭配 0050』）"),
        ("窗口", f"固定段 A 2003-07~2014（0050 年化 {a['A']:.1f}%）、B 2015~2020（{a['B']:.1f}%）、C 2021 起（{a['C']:.1f}%）、2017~2020（{a['17-20']:.1f}%）；滾動窗口每 21 個交易日一個起點，達標＝窗口年化 >= 門檻倍數 x 同窗 0050 年化；逐年＝2004~2025 完整日曆年"),
        ("統計", "t 值用月報酬（策略 - 門檻倍數 x 0050），NW＝Newey-West 落後 6 期；bootstrap＝穩健區塊（平均 40 日）同步抽策略與 0050 日報酬，2000 條 10 年路徑"),
        ("0050 對帳", f"自建含息（未扣成本）年化：2008~2016 {gross['2008~2016']:.1f}%、2017~2020 {gross['2017~2020']:.1f}%、2021 起 {gross['2021~']:.1f}%（r2_futures 18.4／27.7、round6 18.3／27.6，本口徑高 0.6～1.3 點；已另用『收盤對收盤 + 除息金額』獨立重算得 18.97／29.03，與引擎一致，差異原因未查清，疑為資料截止日或股利處理不同）；2009 起 {gross['2009~']:.1f}%"),
    ]:
        M.append(f"| {k} | {v} |")
    M.append("\n## 二、第一張表：報酬對回撤的選單（依滾動 5 年達標比例排序）\n")
    M += T1
    M.append("\n最差 5 年窗口的差距＝窗口年化 - 門檻倍數 x 0050 年化，單位百分點；負數＝沒達標。2009 後回撤排除 2008 的代理序列崩盤，較接近真實 ETF 可能經歷的範圍。\n")
    M.append("### 表 2：固定段、統計顯著性、bootstrap、保證金\n")
    M += T2
    M.append("\n固定段欄位是『年化 - 門檻』的百分點差。NW t 對的是『策略月報酬 - 門檻倍數 x 0050 月報酬』，|t|>2 才算有統計證據；bootstrap 的 P 值是 10 年路徑上的機率（區塊重抽樣，保留 40 日內的連續性）。"
             "保證金欄＝盤中低點權益 / 維持保證金的最低倍數（<1 就是追繳）／追繳次數／平均期貨名目占權益。\n")
    M.append("## 三、委員分歧在統一口徑下的裁決\n")
    M.append("### 3.1 200 日線 B 段：+2.9（lev_lab）、-0.9（trend）、-7.5（alloc）\n")
    M += D2
    M.append("\n裁決：\n"
             "- **訊號來源才是主因，成交口徑只差 1～2 點。** 同一條規則（200 日線±2%、線下 30% 正二）：訊號用加權指數，B 段在三種成交口徑下都是正的（+1.8～+3.7）；訊號換成 0050 就變負（含息 -4.8／-2.6，不含息 -7.5／-6.2）。**lev_lab 的 +2.9 在本口徑重現，是對的。**\n"
             "- alloc 的 -7.5 與本表『0050 不含息、分割還原』逐位吻合；alloc 表裡標成『還原含息』那列（-7.5）與『未還原』那列數字完全相同，**實際上沒有把股利加進去**。含息還原後是 -4.8。\n"
             "- trend 的加權指數版 -0.9 在本表任何成交口徑都重現不出來（最低 +1.8），差異在他們引擎的狀態起點與開盤到開盤的計法（trend 自己也這樣說），我無法在不看他們引擎的情況下證實，**不採用**。\n"
             "- 結論：『濾網對訊號輸入極度敏感』成立（加權指數 vs 0050 含息差 7.7 點）；0050 在 2009 年前沒有股利，含息訊號等於價格訊號，A 段不受影響（A 兩者都 +2.8～+3.0）。E2b 在 B 與 2017～2020 都不過，所以 **E2 一定要用加權指數當訊號，不可改用 0050**。\n")
    M.append("### 3.2 1 倍台指期 2008~2016：futures 贏 0050 +2.1、與 round4 差 2.6 點\n")
    M += D0
    M.append("\n裁決：\n"
             f"- 本口徑 1 倍台指期 2008~2016 年化 {d0.iloc[0, 1]:.2f}%，贏 0050（{d0.iloc[0, 2]:.2f}%）{d0.iloc[0, 3]:+.2f} 點，落在 futures（+2.1）與 round4 舊數字（較低）之間。\n"
             "- 差距的來源可以直接量化：**現金利率每高 1% 約 +0.65 點**（r2_futures 加的 +0.83% 約 +0.5～+0.6 點）；**換月成本**不扣就 +1.2 點。futures 的 6.3%～6.9% 只有在『現金多給 0.83% 且換月成本偏低』時才重現。\n"
             "- round4 較低的數字，依 round5 README 是舊引擎把換月跳點當虧損（每年低估約一個股利殖利率），已被 round5 修正取代；本輪沒有重跑舊引擎驗證這一點。\n"
             f"- 所以：futures 的 +2.1 偏樂觀約 0.9 點，本口徑的 {d0.iloc[0, 3]:+.2f} 較保守。1 倍台指期在 2008~2016 贏 0050、2021 起輸（{g('F0', 'gap_C'):+.1f} 點），**不是穩定贏**（F0 逐年 {s('F0', 'year_win_txt')}、滾動 5 年達標 {pc(g('F0', 'roll5y_pass'), 0)}）。\n")
    M.append("### 3.3 其他分歧\n")
    M.append(f"- **『擇時層有沒有貢獻』**：skeptic 說擇時每年少 4.1 點。本口徑：E2（200 日線）全期 {pc(g('E2', 'cagr'))} 對 E1 持有 {pc(g('E1', 'cagr'))}，少 {100 * (g('E1', 'cagr') - g('E2', 'cagr')):.1f} 點／年，NW t 從 {g('E1', 'nw_t'):.2f} 掉到 {g('E2', 'nw_t'):.2f}，**同意**；擇時買到的是回撤（{pc(g('E1', 'mdd'), 0)} -> {pc(g('E2', 'mdd'), 0)}；10 年路徑回撤超過 -60% 的機率 {pc(g('E1', 'p_mdd60'), 0)} -> {pc(g('E2', 'p_mdd60'), 0)}），不是報酬。")
    M.append(f"- **災難停損 E5（skeptic）**：滾動 5 年達標只有 {pc(g('E5', 'roll5y_pass'), 0)}（E1 {pc(g('E1', 'roll5y_pass'), 0)}），B 段 {g('E5', 'gap_B'):+.1f}、最差 5 年 {g('E5', 'roll5y_worst'):+.1f}，回撤還有 {pc(g('E5', 'mdd'), 0)}。trend 預言它『低點賣、反彈才買回』，**trend 對**。")
    M.append(f"- **權益熔斷 F5／F6（futures）**：F5 滾動 5 年只有 {pc(g('F5', 'roll5y_pass'), 0)}、逐年勝 {s('F5', 'year_win_txt')}，比不加規則的 F2（{pc(g('F2', 'roll5y_pass'), 0)}）差很多；F6 {pc(g('F6', 'roll5y_pass'), 0)} 對 F3 {pc(g('F3', 'roll5y_pass'), 0)}。熔斷把回撤從 {pc(g('F2', 'mdd'), 0)} 壓到 {pc(g('F5', 'mdd'), 0)}，代價是報酬掉到比 0050 還低（F5 全期 {pc(g('F5', 'cagr'))} 對 0050 {pc(g('F5', 'cagr_0050'))}）。**熔斷在 2009 後的 V 轉盤是淨負債，不建議。**")
    M.append(f"- **固定比例 E3／E4（alloc／factor）**：E3 C 段 {g('E3', 'gap_C'):+.1f}、E4 B／C 段 {g('E4', 'gap_B'):+.1f}／{g('E4', 'gap_C'):+.1f}，固定段沒有全過；E3 的 NW t {g('E3', 'nw_t'):.2f} 勉強過 2。")
    M.append(f"- **S2 衛星 E6（chips）**：2016-12 前 S2 沒有資料，E6 的 A 段等於 E1；2017 起相對 E1 的增量：C 段 {g('E6', 'gap_C') - g('E1', 'gap_C'):+.1f} 點、NW t {g('E6', 'nw_t'):.2f}（E1 {g('E1', 'nw_t'):.2f}），回撤 2009 後 {pc(g('E6', 'mdd_09'), 0)}（E1 {pc(g('E1', 'mdd_09'), 0)}）。增量小、S2 本身不顯著（skeptic 的 t≈1.8～1.9），**不採用**。")
    M.append(f"- **overlay O1（0050 x 0.8 + 期貨 0.7）**：歸類『搭配 0050』門檻 1.5 倍，A／B／C 差 {g('O1', 'gap_A'):+.1f}／{g('O1', 'gap_B'):+.1f}／{g('O1', 'gap_C'):+.1f}，滾動 5 年達標 {pc(g('O1', 'roll5y_pass'), 0)}，**不過**（贏 0050 的逐年勝率 {s('O1', 'year_win_txt')} 很穩，但打不到 1.5 倍）。\n")
    M.append("## 四、每個方案的白話規則\n")
    for _, r in df.iterrows():
        M.append(f"- **{r.id}　{r['name']}**：{RULES[r.id]}")
    M.append("\n## 五、建議（各一套）\n")
    M.append("選擇規則（事先講好，避免看完才挑）：在『10 年路徑回撤超過 -60% 的機率 <= 20%』的風險預算內，取滾動 5 年達標比例最高者；同時要求固定段 A／B／C 與 2017～2020 全部 >= 0。\n")
    M.append(f"**個股＋ETF：E2（加權指數 200 日線±2%，線上 100% 正二，線下 30% 正二 + 70% 現金）。**\n"
             f"- 固定段 A／B／C／2017～2020 差距 {g('E2', 'gap_A'):+.1f}／{g('E2', 'gap_B'):+.1f}／{g('E2', 'gap_C'):+.1f}／{g('E2', 'gap_17-20'):+.1f}，四段全過；全期年化 {pc(g('E2', 'cagr'))}；最大回撤 {pc(g('E2', 'mdd'), 0)}（2009 後 {pc(g('E2', 'mdd_09'), 0)}），E1 是 {pc(g('E1', 'mdd'), 0)}／{pc(g('E1', 'mdd_09'), 0)}。\n"
             f"- 通過上面規則的只有 E2：10 年回撤超過 -60% 的機率 {pc(g('E2', 'p_mdd60'), 0)}（E1 {pc(g('E1', 'p_mdd60'), 0)}、E3 {pc(g('E3', 'p_mdd60'), 0)}、E6 {pc(g('E6', 'p_mdd60'), 0)}）。\n"
             f"- **弱點要講在前面**：滾動 5 年達標 {pc(g('E2', 'roll5y_pass'), 0)}（E1 {pc(g('E1', 'roll5y_pass'), 0)}），最差 5 年窗口 {g('E2', 'roll5y_worst'):+.1f} 點（{s('E2', 'roll5y_when')}）；NW t {g('E2', 'nw_t'):.2f}（對 1.5 x 0050 沒有統計顯著）；訊號必須用加權指數（E2b 不過）；A 段依賴代理序列，且補 2009 前股利後 A 段只剩 {g('E2', 'gap_A_div'):+.1f}（幾乎在門檻上）。\n"
             f"- **備選**：能接受 2009 後約 {pc(g('E1', 'mdd_09'), 0)}（模擬 2008 約 {pc(g('E1', 'mdd'), 0)}）的回撤，就用 **E1（持有 00631L）**：零參數、滾動 5 年達標 {pc(g('E1', 'roll5y_pass'), 0)}、NW t {g('E1', 'nw_t'):.2f}，統計證據最強，但 10 年內回撤超過 -60% 的機率約 {pc(g('E1', 'p_mdd60'), 0)}。\n")
    M.append(f"**台指期：F2（永遠持有名目 1.3 倍，不加熔斷、不加均線）。**\n"
             f"- 固定段 A／B／C／2017～2020 對 0050 的差距 {g('F2', 'gap_A'):+.1f}／{g('F2', 'gap_B'):+.1f}／{g('F2', 'gap_C'):+.1f}／{g('F2', 'gap_17-20'):+.1f}，全過；滾動 5 年達標 {pc(g('F2', 'roll5y_pass'), 0)}、最差 5 年 {g('F2', 'roll5y_worst'):+.1f}；NW t {g('F2', 'nw_t'):.2f}；10 年回撤超過 -60% 的機率 {pc(g('F2', 'p_mdd60'), 0)}（F3 1.5 倍是 {pc(g('F3', 'p_mdd60'), 0)}）。\n"
             f"- 保證金：最低維持率 {g('F2', 'x_min_ratio'):.1f} 倍、追繳 {int(g('F2', 'x_calls'))} 次（以 8% 維持保證金率計），風險不在被強平，而在帳面回撤 {pc(g('F2', 'mdd'), 0)}（2009 後 {pc(g('F2', 'mdd_09'), 0)}）。\n"
             f"- 理由：零參數（沒有均線、沒有熔斷可以被調）；F3 滾動 5 年達標更高（{pc(g('F3', 'roll5y_pass'), 0)}）但回撤機率 {pc(g('F3', 'p_mdd60'), 0)} 超出預算；F4（200 日線 1.5／1.0）回撤較小（{pc(g('F4', 'mdd'), 0)}）、滾動 3 年也相當，是可以考慮的次選（滾動 5 年 {pc(g('F4', 'roll5y_pass'), 0)} 達標、10 年回撤機率 {pc(g('F4', 'p_mdd60'), 0)}），但多一個會被訊號來源影響的參數；F0／F1 贏 0050 的把握不夠（F0 滾動 5 年 {pc(g('F0', 'roll5y_pass'), 0)}）。\n"
             f"- 弱點：2021 起 1.3 倍的優勢只有 {g('F2', 'gap_C'):+.1f} 點，若台積電行情消退會縮小；多重比較（7 個期貨候選、7 個 ETF 候選）沒有校正。\n")
    M.append("## 六、限制（不隱瞞）\n"
             "- 這次是在已被看過的資料上並排重跑，不是新的樣本外：2017 後兩段早被前幾輪看過，所以固定段只是『一致性檢查』，不是新證據。\n"
             "- A 段的 00631L 是代理序列（把上市後校準的殘差約 +9%/年外推到 2003～2014），0050 在 2009 前沒有股利；兩者對 A 段的影響見表 2 的『補股利』欄。\n"
             "- S2 價格沒還原除息、存活者偏誤未量化、2016-12 前無資料。\n"
             "- 期貨的保證金模擬只有『盤中低點 + 股票部位同步下跌』的保守近似，沒有模擬保證金率隨波動調高，也沒有模擬 0050 抵繳保證金（未查證）。\n"
             "- 現金與融資利率是年度近似表（假設），每差 1% 台指期方案的年化約差 0.65 點。\n")
    (OUT / "r3_final.md").write_text("\n".join(M), encoding="utf-8")


def main():
    w = build_world(False)
    bench = L.Bench(w)
    s2 = s2_legs(w)
    C = candidates(w, s2)
    res = []
    for k, c in C.items():
        ev = evaluate(w, bench, c["r"], c["mult"])
        ev.update(id=k, name=c["name"], mult=c["mult"], **{f"x_{a}": b for a, b in c["extra"].items()})
        res.append(ev)
    ref = evaluate(w, bench, bench.r, 1.5, boot=False)
    # 補股利敏感度（只看 A 段與全期）
    w2 = build_world(True); b2 = L.Bench(w2)
    s2b = s2_legs(w2)
    C2 = candidates(w2, s2b)
    sens = {}
    for k, c in C2.items():
        sens[k] = evaluate(w2, b2, c["r"], c["mult"], boot=False)
    d2 = diag_e2(w, bench); d0 = diag_f0(w, bench)
    df = pd.DataFrame(res)
    for k in df.id:
        df.loc[df.id == k, "gap_A_div"] = sens[k]["gap_A"]
        df.loc[df.id == k, "roll5y_pass_div"] = sens[k]["roll5y_pass"]
    df.to_csv(OUT / "r3_results.csv", index=False, encoding="utf-8-sig")
    json.dump(dict(ref=ref), open(OUT / "_r3_ref.json", "w"), ensure_ascii=False, default=float)
    d2.to_csv(OUT / "_r3_diag_e2.csv", index=False, encoding="utf-8-sig"); d0.to_csv(OUT / "_r3_diag_f0.csv", index=False, encoding="utf-8-sig")
    gross = {nm: L.cagr(L.window(w, w.r50, a, b)) * 100 for nm, (a, b) in {"2008~2016": ("2008-01-01", "2016-12-31"), "2017~2020": ("2017-01-01", "2020-12-31"), "2021~": ("2021-01-01", None), "2009~": ("2009-01-01", None)}.items()}
    write_md(w, bench, df, ref, d2, d0, gross)
    print(df[["id", "cagr", "gap_A", "gap_B", "gap_C", "gap_17-20", "roll5y_pass", "roll5y_worst", "roll3y_pass", "year_win_txt", "mdd", "mdd_09", "nw_t", "p_window", "p_any", "p_mdd60"]].round(3).to_string())
    print(d2.round(1).to_string()); print(d0.round(2).to_string())


if __name__ == "__main__":
    main()
