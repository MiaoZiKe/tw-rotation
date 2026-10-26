"""第二輪：由大到小（大盤環境 -> 族群資金 -> 個股技術進場）三層選股回測，附可解釋交易日誌。

只讀資料湖，不寫 data/。研究用，不是買賣建議、不下單。
紅線：訊號在「收盤後」算，成交在「隔日開盤」；所有指標只用當天以前的資料；
月營收用法定可用日（次月 10 日）；總經資料再延後一天。成本與第一輪相同。

【第一層 大盤環境分數 0~10】（權重事先定好，來源見 docs/strategy_lab/round2/README.md，沒有用樣本外調整）
  指數趨勢 3 + 三大法人 2 + 期貨 1.5 + 資券 0.5 + 量能廣度 2 + 國際總經 1，再扣「壓力」最多 1。
  持股水位：>=7 滿檔、4~7 半檔、<4 空手。
【第二層 族群資金分數 0~10】相對強度 3 + 法人買超/成交值 3 + 成交比重上升 2 + 營收動能 2。取前 K 名。
【第三層 個股進場】順勢冠軍(SuperTrend 7,3／均線 20,60／唐奇安 40,20)進場訊號 + 量價確認(量 > 1.2 倍 20 日均量)。
  出場：技術出場、ATR 3 倍移動停損、-8% 硬停損、大盤分數 < 4 全出、族群掉出前 10。
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline import indicators as ind  # noqa: E402
from pipeline.groups import loader  # noqa: E402
from pipeline.compute.strategy_lab import (  # noqa: E402
    Ctx, sig, FEE, TAX, SLIP, _fix_splits, set_calendar, to_weekly, stats)

OUT = ROOT / "docs" / "strategy_lab" / "round2"
T_START = "2021-04-01"       # 資料湖的法人／期貨／資券從 2021-01 開始，留 60 日暖機
SPLIT = "2024-01-01"         # 樣本內 2021-04~2023-12、樣本外 2024-01 起
N_SLOTS = 10
THR_HALF, THR_FULL = 4.0, 7.0
GROUP_TOPK, GROUP_KEEP = 5, 10
VOL_MULT = 1.2
HARD_STOP = 0.08
ATR_MULT = 3.0


# ------------------------------------------------------------------ 讀資料
def _rd(table, cols=None):
    out = []
    for f in glob.glob(str(ROOT / "data" / table / "**" / "*.parquet"), recursive=True):
        d = pd.read_parquet(f)
        if cols:
            d = d.reindex(columns=cols)
        out.append(d)
    return pd.concat(out, ignore_index=True)


def load_all(n_univ=200):
    p = _rd("price_daily", ["date", "code", "open", "high", "low", "close", "volume", "turnover"])
    p = p[p["code"].str.fullmatch(r"\d{4}") & (p["close"] > 0) & (p["date"] >= "2019-06-01")]
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["code", "date"]).drop_duplicates(["code", "date"])
    # 大盤環境用的廣度（全市場個股）
    C_all = p.pivot(index="date", columns="code", values="close")
    # 族群成分（現況 groups.yaml；有「用現在的分類看過去」的偏誤，報告會寫）
    mem = loader.membership()
    gnames = {gid: g.get("name", gid) for gid, g in (loader.load().get("groups") or {}).items()}
    grouped = sorted(set(mem["code"]))
    # pit 股票池：2020 年（回測前一年）成交值中位數，在「有族群的股票」中取前 n_univ
    w = p[(p["date"] >= "2020-01-01") & (p["date"] <= "2020-12-31") & p["code"].isin(grouped)]
    liq = w.groupby("code")["turnover"].median().sort_values(ascending=False)
    codes = [c for c in liq.index if not c.startswith("00")][:n_univ]
    frames = {}
    for c, g in p[p["code"].isin(codes + ["0050"])].groupby("code"):
        g = g.set_index("date")[["open", "high", "low", "close", "volume"]]
        frames[c] = _fix_splits(g)
    return p, C_all, frames, codes, mem, gnames


# ------------------------------------------------------------------ 第一層
def layer1(frames, C_all, p):
    """每天盤後一次，回傳每個子項的分數與總分。只用當日(含)以前的資料。"""
    idx = frames["0050"].index          # 以 0050 還原後價格當加權指數代理（index_daily 只有 2026-09 起）
    c = frames["0050"]["close"]
    ma20, ma60 = c.rolling(20).mean(), c.rolling(60).mean()
    f = pd.DataFrame(index=idx)
    f["趨勢_站上月線"] = (c > ma20).astype(float) * 1.0
    f["趨勢_月線在季線上"] = (ma20 > ma60).astype(float) * 1.0
    f["趨勢_季線上彎"] = (ma60 > ma60.shift(20)).astype(float) * 1.0
    # 三大法人現貨（全市場買賣金額）
    im = _rd("inst_market_daily").assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date").sort_index()
    im = im[~im.index.duplicated(keep="last")]
    fnet = (im["foreign_buy"] - im["foreign_sell"]).reindex(idx)
    tnet = ((im["foreign_buy"] - im["foreign_sell"]) + (im["trust_buy"] - im["trust_sell"]) +
            (im["dealer_buy"] - im["dealer_sell"])).reindex(idx)
    f["法人_外資5日買超"] = (fnet.rolling(5).sum() > 0).astype(float) * 0.5
    f["法人_三大5日買超"] = (tnet.rolling(5).sum() > 0).astype(float) * 0.5
    f["法人_三大20日買超"] = (tnet.rolling(20).sum() > 0).astype(float) * 1.0
    # 期貨：外資台指期(TX)未平倉淨額
    fi = _rd("fut_inst")
    fi = fi[(fi["futures_id"] == "TX") & (fi["who"] == "foreign")].assign(date=lambda d: pd.to_datetime(d["date"]))
    fi = fi.drop_duplicates("date", keep="last").set_index("date").sort_index()
    net = (fi["long_oi"] - fi["short_oi"]).reindex(idx)
    f["期貨_淨額高於60日中位"] = (net > net.rolling(60).median()).astype(float) * 0.5
    f["期貨_淨額5日增加"] = (net > net.shift(5)).astype(float) * 0.5
    f["期貨_與現貨同向"] = (((fnet.rolling(5).sum() > 0) & (net >= net.shift(5))) |
                         ((fnet.rolling(5).sum() <= 0) & (net < net.shift(5)))).astype(float) * 0.5
    # 資券：融資餘額 20 日增幅 < 5%（反指標觀點：融資急增代表散戶追價過熱）
    mt = _rd("margin_total").assign(date=lambda d: pd.to_datetime(d["date"]))
    mt = mt.drop_duplicates("date", keep="last").set_index("date").sort_index()["margin_lots"].reindex(idx)
    f["資券_融資未過熱"] = ((mt / mt.shift(20) - 1) < 0.05).astype(float) * 0.5
    # 量能廣度：全市場站上月線比例、10 日上漲家數比、成交值不萎縮
    ma20_all = C_all.rolling(20).mean()
    live = C_all.notna() & ma20_all.notna()
    pct_above = ((C_all > ma20_all) & live).sum(axis=1) / live.sum(axis=1)
    ret_all = C_all.pct_change()
    adv = (ret_all > 0).sum(axis=1)
    dec = (ret_all < 0).sum(axis=1)
    adr10 = adv.rolling(10).sum() / (adv.rolling(10).sum() + dec.rolling(10).sum())
    to = (p.assign(v=p["close"] * p["volume"]).pivot(index="date", columns="code", values="v")).sum(axis=1)
    f["廣度_站上月線比例過半"] = (pct_above.reindex(idx) > 0.5).astype(float) * 1.0
    f["廣度_10日漲家數比過半"] = (adr10.reindex(idx) > 0.5).astype(float) * 0.5
    f["廣度_成交值未萎縮"] = (to.rolling(5).mean().reindex(idx) >= 0.9 * to.rolling(60).mean().reindex(idx)).astype(float) * 0.5
    # 國際與總經（FRED，延後一天可用）：10Y-2Y 利差為正、10Y 殖利率 20 日升幅 < 0.25pp
    mc = _rd("macro")
    mc["date"] = pd.to_datetime(mc["date"]) + pd.Timedelta(days=1)
    t10 = mc[mc["series"] == "DGS10"].drop_duplicates("date", keep="last").set_index("date")["value"].sort_index()
    s21 = mc[mc["series"] == "T10Y2Y"].drop_duplicates("date", keep="last").set_index("date")["value"].sort_index()
    t10 = t10.reindex(t10.index.union(idx)).ffill().reindex(idx)
    s21 = s21.reindex(s21.index.union(idx)).ffill().reindex(idx)
    f["總經_利差為正"] = (s21 > 0).astype(float) * 0.5
    f["總經_10Y升幅溫和"] = ((t10 - t10.shift(20)) < 0.25).astype(float) * 0.5
    # 壓力扣分：20 日實現波動 > 自己過去 250 日的 80 百分位（沒有歷史 VIX／事件資料，用它替代）
    rv = c.pct_change().rolling(20).std()
    thr = rv.rolling(250, min_periods=120).quantile(0.8)
    f["壓力扣分"] = -((rv > thr).astype(float))
    cols = [x for x in f.columns]
    # 暖機期不足的日子（rolling 產生 NaN 被當 False）一律從 T_START 才開始用
    f["總分"] = f[cols].sum(axis=1).clip(0, 10)
    return f


def sub_groups(f):
    g = {"指數趨勢(3)": [c for c in f if c.startswith("趨勢")], "三大法人(2)": [c for c in f if c.startswith("法人")],
         "期貨(1.5)": [c for c in f if c.startswith("期貨")], "資券(0.5)": [c for c in f if c.startswith("資券")],
         "量能廣度(2)": [c for c in f if c.startswith("廣度")], "國際總經(1)": [c for c in f if c.startswith("總經")],
         "壓力扣分": ["壓力扣分"]}
    return pd.DataFrame({k: f[v].sum(axis=1) for k, v in g.items()})


# ------------------------------------------------------------------ 第二層
def layer2(frames, codes, mem, gnames, idx):
    gid_list, members = [], {}
    for gid, g in mem.groupby("group_id"):
        m = [c for c in g["code"] if c in codes]
        if len(m) >= 3:
            gid_list.append(gid)
            members[gid] = m
    T = len(idx)
    C = pd.DataFrame({c: frames[c]["close"] for c in codes}).reindex(idx).ffill()
    V = pd.DataFrame({c: frames[c]["volume"] for c in codes}).reindex(idx).fillna(0)
    ret = C.pct_change().fillna(0)
    val = C * V
    # 法人（外資+投信）每檔買超股數 * 收盤價
    idf = _rd("inst_daily", ["date", "code", "foreign_total", "trust"])
    idf = idf[idf["code"].isin(codes)]
    idf["date"] = pd.to_datetime(idf["date"])
    idf["net"] = idf["foreign_total"].fillna(0) + idf["trust"].fillna(0)
    NET = idf.drop_duplicates(["date", "code"]).pivot(index="date", columns="code", values="net").reindex(idx).fillna(0)
    NETV = NET.reindex(columns=codes, fill_value=0) * C
    # 月營收年增率，法定可用日（次月 10 日）
    rv = _rd("revenue_monthly", ["ym", "code", "revenue"])
    rv = rv[rv["code"].isin(codes)].dropna(subset=["revenue"])
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    YM = R / R.shift(12).where(R.shift(12) > 0) - 1          # 年增率（資料湖沒存 yoy，自己用去年同月算）
    YM.index = YM.index.to_timestamp() + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)   # 法定可用日：次月 10 日
    YOY = YM.reindex(YM.index.union(idx)).ffill().reindex(idx).reindex(columns=codes)
    mkt20 = ret.mean(axis=1).rolling(20).apply(lambda x: np.prod(1 + x) - 1, raw=True)
    tot_val = val.sum(axis=1)
    G = len(gid_list)
    rs = np.full((T, G), np.nan); inst = np.full((T, G), np.nan)
    share = np.full((T, G), np.nan); rev = np.full((T, G), np.nan)
    for j, gid in enumerate(gid_list):
        m = members[gid]
        g_ret = ret[m].mean(axis=1)
        rs[:, j] = (g_ret.rolling(20).apply(lambda x: np.prod(1 + x) - 1, raw=True) - mkt20).to_numpy()
        gv = val[m].sum(axis=1)
        inst[:, j] = (NETV[m].sum(axis=1).rolling(5).sum() / gv.rolling(5).sum().replace(0, np.nan)).to_numpy()
        sh = gv / tot_val.replace(0, np.nan)
        share[:, j] = (sh.rolling(5).mean() / sh.rolling(20).mean()).to_numpy()
        rev[:, j] = YOY[m].median(axis=1).to_numpy()

    def pr(a):   # 每天橫斷面百分位 0~1
        return pd.DataFrame(a).rank(axis=1, pct=True).to_numpy()
    score = 3 * pr(rs) + 3 * pr(inst) + 2 * pr(share) + 2 * np.clip(np.nan_to_num(rev) / 0.30, 0, 1)
    score[np.isnan(rs)] = np.nan
    return dict(gids=gid_list, names=[gnames.get(g, g) for g in gid_list], members=members,
                rs=rs, inst=inst, share=share, rev=rev, score=score)


# ------------------------------------------------------------------ 第三層訊號
def stock_signals(frames, codes, idx, entry):
    T = len(idx); N = len(codes)
    ent = np.zeros((T, N), bool); ex = np.zeros((T, N), bool); vc = np.zeros((T, N), bool)
    atr = np.full((T, N), np.nan)
    for j, c in enumerate(codes):
        df = frames[c]
        x = Ctx(df, "D")
        if entry == "ST":
            e, xx = sig("supertrend", dict(n=7, m=3.0), x)
        elif entry == "MA":
            e, xx = sig("ma_cross", dict(f=20, s=60), x)
        elif entry == "DC":
            e, xx = sig("donchian", dict(n_in=40, n_out=20), x)
        elif entry == "STW":     # 週K SuperTrend：只在週最後交易日收盤後換向才進，週K 轉空才出
            w = to_weekly(df)
            xw = Ctx(w, "W")
            e_w, x_w = sig("supertrend", dict(n=7, m=3.0), xw)
            e = np.zeros(len(df), bool); xx = np.zeros(len(df), bool)
            pos = df.index.get_indexer(w.index)
            ok = pos >= 0
            e[pos[ok]] = e_w[ok]; xx[pos[ok]] = x_w[ok]
        else:
            raise ValueError(entry)
        vma = pd.Series(x.v).rolling(20).mean().shift(1).to_numpy()
        with np.errstate(invalid="ignore"):
            v_ok = x.v > VOL_MULT * vma
        s = pd.DataFrame({"e": e, "x": xx, "v": v_ok, "a": x.atr(14)}, index=df.index).reindex(idx)
        ent[:, j] = s["e"].fillna(False).astype(bool).to_numpy()
        ex[:, j] = s["x"].fillna(False).astype(bool).to_numpy()
        vc[:, j] = s["v"].fillna(False).astype(bool).to_numpy()
        atr[:, j] = s["a"].to_numpy()
    return ent, ex, vc, atr


# ------------------------------------------------------------------ 組合模擬
def simulate(M, cfg):
    """M: 預先算好的矩陣包。cfg: use_l1/use_l2/entry/thr_half/thr_full/slots。回傳 (權益序列, 交易表)。"""
    idx, codes = M["idx"], M["codes"]
    O, H, L, C = M["O"], M["H"], M["L"], M["C"]
    Cf = M["Cf"]
    ent, ex, vc, atr = M["sig"][cfg["entry"]]
    score = M["score"].to_numpy()
    G = M["g"]
    T, N = C.shape
    t0 = idx.searchsorted(pd.Timestamp(T_START))
    use1, use2 = cfg.get("use_l1", True), cfg.get("use_l2", True)
    thr_h, thr_f = cfg.get("thr_half", THR_HALF), cfg.get("thr_full", THR_FULL)
    slots = cfg.get("slots", N_SLOTS)
    cash = 1.0
    eq = np.ones(T)
    shares = np.zeros(N); epx = np.zeros(N); trail = np.full(N, -1e18); mae = np.zeros(N)
    held = np.zeros(N, bool); eidx = np.zeros(N, int)
    pend_out = {}; pend_in = {}
    trades = []
    expo = np.zeros(T)
    mem = M["mem_mat"]       # N x G 0/1
    for t in range(t0, T):
        # 1) 開盤成交：先出後進
        for i, why in list(pend_out.items()):
            px = O[t, i]
            if not np.isfinite(px):
                continue
            px *= (1 - SLIP)
            cash += shares[i] * px * (1 - FEE - TAX)
            ret = px * (1 - FEE - TAX) / (epx[i] * (1 + FEE)) - 1
            trades.append(dict(code=codes[i], entry_i=eidx[i], exit_i=t, entry_px=epx[i], exit_px=px,
                               ret=ret, mae=mae[i], exit_reason=why, shares=shares[i]))
            held[i] = False; shares[i] = 0
            del pend_out[i]
        eq_prev = eq[t - 1] if t > t0 else 1.0
        for i, info in list(pend_in.items()):
            px = O[t, i]
            if not np.isfinite(px) or held[i]:
                continue
            px *= (1 + SLIP)
            amt = min(cash, eq_prev / slots)
            if amt <= 0:
                continue
            shares[i] = amt / (px * (1 + FEE)); cash -= amt
            epx[i] = px; held[i] = True; eidx[i] = t; trail[i] = -1e18; mae[i] = 0.0
            M["info"][(i, t)] = info
        pend_in = {}
        # 2) 收盤市值
        pv = 0.0
        for i in np.where(held)[0]:
            c = Cf[t, i]
            pv += shares[i] * c
            if np.isfinite(L[t, i]):
                mae[i] = min(mae[i], L[t, i] / epx[i] - 1)
        eq[t] = cash + pv
        expo[t] = pv / eq[t]
        # 3) 收盤後產生訊號（隔日開盤成交）
        s = score[t] if use1 else 10.0
        allowed = slots if s >= thr_f else (int(round(slots / 2)) if s >= thr_h else 0)
        if not use1:
            allowed = slots
        gs_t = G["score"][t]
        top = np.zeros(G["score"].shape[1], bool); keep = np.zeros_like(top)
        if use2 and np.isfinite(gs_t).any():
            order = np.argsort(-np.nan_to_num(gs_t, nan=-1))
            top[order[:cfg.get('topk', GROUP_TOPK)]] = True; keep[order[:cfg.get('keep', GROUP_KEEP)]] = True
        for i in np.where(held & ~np.isin(np.arange(N), list(pend_out.keys())))[0]:
            c = Cf[t, i]
            why = None
            if use1 and s < thr_h:
                why = "大盤分數跌破%.0f分（空手）" % thr_h
            elif use2 and not (mem[i] * keep).any():
                why = "族群掉出前%d名" % cfg.get("keep", GROUP_KEEP)
            else:
                a = atr[t, i]
                if np.isfinite(a):
                    trail[i] = max(trail[i], c - ATR_MULT * a)
                if c < epx[i] * (1 - HARD_STOP):
                    why = "硬停損-%d%%" % int(HARD_STOP * 100)
                elif c < trail[i]:
                    why = "ATR%.0f倍移動停損" % ATR_MULT
                elif ex[t, i]:
                    why = "技術出場(%s)" % cfg["entry"]
            if why:
                pend_out[i] = why
        n_hold = int((held & ~np.isin(np.arange(N), list(pend_out.keys()))).sum())
        room = allowed - n_hold
        if room > 0 and t + 1 < T:
            cand = np.where(ent[t] & vc[t] & ~held & np.isfinite(O[t + 1]))[0]
            if use2:
                sc = (mem[cand] * (top * np.nan_to_num(gs_t, nan=0))[None, :]).max(axis=1) if len(cand) else np.array([])
                ok = sc > 0
                cand, sc = cand[ok], sc[ok]
            else:
                sc = np.zeros(len(cand))
            rs20 = M["stock_rs"][t, cand] if len(cand) else np.array([])
            order = np.lexsort((-np.nan_to_num(rs20, nan=-9), -sc)) if len(cand) else []
            for k in order[:room]:
                i = cand[k]
                pend_in[i] = dict(sig_t=t, l1=s, grp_score=float(sc[k]) if use2 else np.nan,
                                  stock_rs20=float(rs20[k]) if np.isfinite(rs20[k]) else np.nan)
    eqs = pd.Series(eq, index=idx).iloc[t0:]
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["entry"] = idx[tr["entry_i"]]; tr["exit"] = idx[tr["exit_i"]]
        tr["hold_days"] = (tr["exit"] - tr["entry"]).dt.days
    return eqs, tr, pd.Series(expo, index=idx).iloc[t0:]


# ------------------------------------------------------------------ 組裝與統計
def build_matrices():
    p, C_all, frames, codes, mem, gnames = load_all()
    idx = frames["0050"].index[frames["0050"].index >= "2020-06-01"]
    set_calendar(idx)
    f = layer1(frames, C_all, p)
    f = f.reindex(idx)
    sub = sub_groups(f)
    G = layer2(frames, codes, mem, gnames, idx)
    def mat(col):
        return pd.DataFrame({c: frames[c][col] for c in codes}).reindex(idx)
    O, H, L, C = (mat(k) for k in ("open", "high", "low", "close"))
    Cf = C.ffill()
    mkt = Cf.pct_change().mean(axis=1)
    mkt20 = (1 + mkt).rolling(20).apply(np.prod, raw=True) - 1
    stock_rs = (Cf / Cf.shift(20) - 1).sub(mkt20, axis=0).to_numpy()
    mem_mat = np.zeros((len(codes), len(G["gids"])), bool)
    ci = {c: i for i, c in enumerate(codes)}
    for j, gid in enumerate(G["gids"]):
        for c in G["members"][gid]:
            mem_mat[ci[c], j] = True
    sigs = {e: stock_signals(frames, codes, idx, e) for e in ("ST", "MA", "DC", "STW")}
    return dict(idx=idx, codes=codes, O=O.to_numpy(), H=H.to_numpy(), L=L.to_numpy(), C=C.to_numpy(),
                Cf=Cf.to_numpy(), f=f, sub=sub, score=f["總分"], g=G, mem_mat=mem_mat, sig=sigs,
                stock_rs=stock_rs, info={}, frames=frames, gnames=gnames)


def metrics(eq: pd.Series, tr: pd.DataFrame, expo: pd.Series, a, b=None):
    seg = eq[(eq.index >= a) & ((eq.index < b) if b else True)]
    r = seg.pct_change().dropna()
    s = stats(r, 245)
    t = tr[(tr["entry"] >= a) & ((tr["entry"] < b) if b else True)] if len(tr) else tr
    n = len(t)
    win = (t["ret"] > 0).mean() if n else np.nan
    w = t.loc[t["ret"] > 0, "ret"].mean() if n else np.nan
    l = -t.loc[t["ret"] <= 0, "ret"].mean() if n else np.nan
    e = expo[(expo.index >= a) & ((expo.index < b) if b else True)]
    return dict(cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], n=n, win=win,
                payoff=(w / l if l and l > 0 else np.nan), avg_ret=t["ret"].mean() if n else np.nan,
                hold=t["hold_days"].mean() if n else np.nan, expo=e.mean())


def bh_series(M):
    Cf = pd.DataFrame(M["Cf"], index=M["idx"])
    ew = Cf.pct_change().mean(axis=1)
    p50 = M["frames"]["0050"]["close"].reindex(M["idx"]).pct_change()
    t0 = M["idx"].searchsorted(pd.Timestamp(T_START))
    return (1 + ew.iloc[t0:]).cumprod(), (1 + p50.iloc[t0:]).cumprod()


def build_log(tr, M, cfg):
    idx, codes, G, f, sub = M["idx"], M["codes"], M["g"], M["f"], M["sub"]
    rows = []
    for _, r in tr.iterrows():
        i = codes.index(r["code"])
        info = M["info"].get((i, int(r["entry_i"])), {})
        st = int(info.get("sig_t", r["entry_i"] - 1))
        gsc = G["score"][st]
        top = np.argsort(-np.nan_to_num(gsc, nan=-1))[:cfg.get('topk', GROUP_TOPK)]
        mine = [j for j in top if M["mem_mat"][i, j]] if cfg.get("use_l2", True) else []
        j = max(mine, key=lambda k: gsc[k]) if mine else None
        row = dict(代號=r["code"], 訊號日=idx[st].date(), 進場日=r["entry"].date(), 進場價=round(r["entry_px"], 2),
                   出場日=r["exit"].date(), 出場價=round(r["exit_px"], 2), 報酬率=round(r["ret"], 4),
                   持有天數=int(r["hold_days"]), 最大不利偏移=round(r["mae"], 4), 出場原因=r["exit_reason"],
                   進場時大盤總分=round(float(M["score"].iloc[st]), 2))
        for k in sub.columns:
            row["大盤_" + k] = round(float(sub[k].iloc[st]), 2)
        if j is not None:
            row.update(入選族群=M["g"]["names"][j], 族群分數=round(float(gsc[j]), 2),
                       族群_相對強度20日=round(float(G["rs"][st, j]), 4),
                       族群_法人買超佔成交值5日=round(float(G["inst"][st, j]), 4),
                       族群_成交比重5比20日=round(float(G["share"][st, j]), 3),
                       族群_營收年增中位數=round(float(G["rev"][st, j]), 3) if np.isfinite(G["rev"][st, j]) else np.nan)
        row["個股訊號"] = f"{cfg['entry']} 進場訊號 + 量>{VOL_MULT}倍20日均量"
        row["個股20日相對強度"] = round(info.get("stock_rs20", np.nan), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    M = build_matrices()
    idx = M["idx"]
    t0 = idx.searchsorted(pd.Timestamp(T_START))
    daily = pd.concat([M["sub"], M["score"].rename("總分"), M["f"].drop(columns=["總分"])], axis=1).iloc[t0:]
    daily["持股水位"] = np.where(daily["總分"] >= THR_FULL, "滿檔", np.where(daily["總分"] >= THR_HALF, "半檔", "空手"))
    daily.round(3).to_csv(OUT / "daily_score.csv", encoding="utf-8-sig", index_label="date")
    runs = {}
    def run(name, **cfg):
        cfg.setdefault("entry", "ST")
        M["info"].clear()
        eq, tr, ex = simulate(M, cfg)
        if len(tr):
            tr = tr.copy()
        log = build_log(tr, M, cfg) if len(tr) else pd.DataFrame()
        runs[name] = dict(eq=eq, tr=tr, ex=ex, log=log, cfg=cfg)
        return runs[name]
    abl = {"A 只用第三層": dict(use_l1=False, use_l2=False), "B 第三層+第二層": dict(use_l1=False, use_l2=True),
           "C 第三層+第一層": dict(use_l1=True, use_l2=False), "D 三層全開": dict(use_l1=True, use_l2=True)}
    rows = []
    for e in ("ST", "MA", "DC", "STW"):
        for nm, c in abl.items():
            if e != "ST" and nm[0] not in "AD":
                continue
            r = run(f"{nm}|{e}", entry=e, **c)
            for seg, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
                m = metrics(r["eq"], r["tr"], r["ex"], a, b)
                rows.append(dict(進場訊號=e, 組合=nm, 區間=seg, **m))
    # 切點敏感度（三層全開、SuperTrend）
    for lo, hi in ((3, 6), (4, 7), (5, 8), (4, 6), (5, 7), (4, 8)):
        r = run(f"D|ST|{lo}-{hi}", entry="ST", use_l1=True, use_l2=True, thr_half=lo, thr_full=hi)
        for seg, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
            m = metrics(r["eq"], r["tr"], r["ex"], a, b)
            rows.append(dict(進場訊號="ST", 組合=f"切點敏感度 半檔>={lo}/滿檔>={hi}", 區間=seg, **m))
    # 第二層參數敏感度（事先宣告的網格，全部列出，不挑）
    for tk, kp in ((5, 10), (5, 20), (10, 20), (10, 30), (20, 40)):
        r = run(f"D|ST|g{tk}-{kp}", entry="ST", use_l1=True, use_l2=True, topk=tk, keep=kp)
        for seg, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
            m = metrics(r["eq"], r["tr"], r["ex"], a, b)
            rows.append(dict(進場訊號="ST", 組合=f"族群敏感度 入選前{tk}/續抱前{kp}", 區間=seg, **m))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "ablation_results.csv", index=False, encoding="utf-8-sig")
    # 基準
    ew, p50 = bh_series(M)
    bm = []
    for nm, s in (("同池等權買進持有", ew), ("0050買進持有", p50)):
        for seg, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
            seg_s = s[(s.index >= a) & ((s.index < b) if b else True)]
            st = stats(seg_s.pct_change().dropna(), 245)
            bm.append(dict(基準=nm, 區間=seg, **st))
    pd.DataFrame(bm).to_csv(OUT / "benchmarks.csv", index=False, encoding="utf-8-sig")
    # 第一輪冠軍同窗
    try:
        c1 = pd.read_pickle(ROOT / "docs" / "strategy_lab" / "_cache_pit.pkl")["ret"]["supertrend(n=7,m=3.0)@D"]
        r1 = []
        for seg, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
            s = c1[(c1.index >= a) & ((c1.index < b) if b else True)]
            r1.append(dict(基準="第一輪冠軍 SuperTrend(7,3) 等權100檔", 區間=seg, **stats(s, 245)))
        pd.DataFrame(r1).to_csv(OUT / "round1_champion_samewindow.csv", index=False, encoding="utf-8-sig")
    except Exception as ex:
        print("第一輪快取不存在：", ex)
    # 交易日誌（主：三層全開 + SuperTrend）與第三層單獨的日誌
    main_run = runs["D 三層全開|ST"]
    main_run["log"].to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    runs["A 只用第三層|ST"]["log"].to_csv(OUT / "trades_L3_only.csv", index=False, encoding="utf-8-sig")
    # 依大盤分數分段：次日報酬（score 為收盤後已知，隔日才有報酬）
    sc = M["score"].iloc[t0:]
    band = pd.cut(sc, [-1, THR_HALF - 1e-9, THR_FULL - 1e-9, 11], labels=["空手區(<4)", "半檔區(4~7)", "滿檔區(>=7)"])
    bands = []
    ew_r = ew.pct_change().shift(-1); p_r = p50.pct_change().shift(-1)
    for nm in ("A 只用第三層|ST", "D 三層全開|ST"):
        s_r = runs[nm]["eq"].pct_change().shift(-1)
        for b in band.cat.categories:
            m = band == b
            bands.append(dict(組合=nm, 分段=b, 天數=int(m.sum()), 次日平均報酬=s_r[m].mean(), 同池等權次日平均=ew_r[m].mean(),
                              零五零次日平均=p_r[m].mean(), 策略平均持倉=runs[nm]["ex"][m].mean()))
    pd.DataFrame(bands).to_csv(OUT / "score_bands.csv", index=False, encoding="utf-8-sig")
    # 每月權益曲線
    pd.DataFrame({k.replace("|", "_"): v["eq"] for k, v in runs.items() if k.endswith("|ST")}
                 ).join(ew.rename("同池等權買進持有")).join(p50.rename("0050買進持有")).to_csv(
        OUT / "equity_curves.csv", encoding="utf-8-sig", index_label="date")
    pd.to_pickle({k: {"eq": v["eq"], "tr": v["tr"], "ex": v["ex"]} for k, v in runs.items()}, OUT / "_runs.pkl")
    print(res[res["區間"] == "樣本外"].round(3).to_string())
    print(pd.DataFrame(bm).round(3).to_string())
    print(pd.DataFrame(bands).round(4).to_string())


if __name__ == "__main__":
    main()
