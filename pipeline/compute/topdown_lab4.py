"""第四輪：0050 當核心、強勢族群個股當衛星；5 ATR 或收盤確認停損；回檔進場；機械式（滾動殘差相關）分群。

與第三輪的差別
  1. 核心／衛星：0050 預設滿倉（含息價），衛星用 S 比例資金買強勢族群個股，其餘仍在 0050；
     只在大盤分數「極低」（< CUT）時，核心降到 50% 並停止新增衛星部位。目標是年化報酬超過 0050。
  2. 停損：5 ATR 盤中觸價（跳空用開盤價）或 3 ATR 收盤確認隔日開盤出；進場可選「回檔進場」。
  3. 族群：每月第一個交易日，用前 120 日「去除大盤後的日報酬」相關係數做階層式分群（只用過去資料）；
     對照法定產業別。兩者走同一套打分流程。
  4. 子項檢驗修正：第三輪的樣本內檢驗允許未來 h 日報酬跨過切點，輕微洩漏樣本外資料；
     本輪一律把檢驗窗結尾提早 30 個日曆日。
淘汰規則同第三輪：樣本外年化報酬 < 同窗含息含成本 0050 -> 淘汰，不使用。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import topdown_lab as T2  # noqa: E402
from pipeline.compute import topdown_lab3 as T3  # noqa: E402
from pipeline.compute.strategy_lab import FEE, TAX, SLIP, stats  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round4"
T_START, SPLIT = T3.T_START, T3.SPLIT
ETF_TAX = T3.ETF_TAX
K_CLUSTERS, LOOKBACK, MIN_SIZE = 20, 120, 3
CUT = 2.0                     # 大盤分數「極低」門檻（事先定）
CORE_CUT_W = 0.5              # 極低時核心降到 50%
BAND = 0.03                   # 核心再平衡容忍帶
TOPK = 5
SPAN = 5


# ------------------------------------------------------------------ 分群
def mech_labels(ret: pd.DataFrame, k=K_CLUSTERS, lookback=LOOKBACK):
    """回傳 (T,N) 整數標籤；每月第一個交易日用「截至前一個收盤」的 lookback 日殘差報酬相關做平均連結分群。"""
    idx = ret.index
    X = ret.sub(ret.mean(axis=1), axis=0)            # 去除等權大盤
    lab = np.full(ret.shape, -1, int)
    month = idx.to_period("M")
    starts = [np.where(month == m)[0][0] for m in month.unique()]
    cur = np.full(ret.shape[1], -1, int)
    for s in starts:
        if s >= lookback + 1:
            w = X.iloc[s - lookback:s]                 # 不含 s 當天
            ok = w.notna().sum() >= int(lookback * 0.8)
            cols = np.where(ok.to_numpy())[0]
            cur = np.full(ret.shape[1], -1, int)
            if len(cols) > k:
                cm = w.iloc[:, cols].corr().fillna(0).to_numpy()
                d = np.clip(1 - cm, 0, 2); np.fill_diagonal(d, 0)
                z = linkage(squareform((d + d.T) / 2, checks=False), method="average")
                cl = fcluster(z, k, criterion="maxclust")
                cnt = pd.Series(cl).value_counts()
                for j, c in zip(cols, cl):
                    cur[j] = c if cnt[c] >= MIN_SIZE else -1
        nxt = starts[starts.index(s) + 1] if starts.index(s) + 1 < len(starts) else len(idx)
        lab[s:nxt] = cur
    return lab


def industry_labels(codes, shape):
    ci = pd.concat([pd.read_parquet(f) for f in (ROOT / "data" / "company_info").glob("**/*.parquet")])
    ci = ci.drop_duplicates("code").set_index("code")["industry"]
    ind = pd.Series([ci.get(c) for c in codes])
    cnt = ind.value_counts()
    ids = {n: i for i, n in enumerate(cnt[cnt >= MIN_SIZE].index)}
    vec = np.array([ids.get(x, -1) for x in ind])
    return np.tile(vec, (shape[0], 1))


# ------------------------------------------------------------------ 族群成分打分（動態標籤）
COMPS = {"相對強度": 3.0, "法人買超": 3.0, "成交比重上升": 2.0, "營收動能": 2.0}


def flows(M3):
    """從第三輪的矩陣取價量，並讀法人、月營收（與第二輪同口徑，法定可用日次月 10 日）。"""
    idx, codes = M3["idx"], M3["codes"]
    C = pd.DataFrame(M3["Cf"], index=idx, columns=codes)
    V = pd.DataFrame({c: M3["frames"][c]["volume"] for c in codes}).reindex(idx).fillna(0)
    val = C * V
    idf = T2._rd("inst_daily", ["date", "code", "foreign_total", "trust"])
    idf = idf[idf["code"].isin(codes)]
    idf["date"] = pd.to_datetime(idf["date"])
    idf["net"] = idf["foreign_total"].fillna(0) + idf["trust"].fillna(0)
    NET = idf.drop_duplicates(["date", "code"]).pivot(index="date", columns="code", values="net").reindex(idx).fillna(0)
    NETV = NET.reindex(columns=codes, fill_value=0) * C
    rv = T2._rd("revenue_monthly", ["ym", "code", "revenue"])
    rv = rv[rv["code"].isin(codes)].dropna(subset=["revenue"])
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    YM = R / R.shift(12).where(R.shift(12) > 0) - 1
    YM.index = YM.index.to_timestamp() + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)
    YOY = YM.reindex(YM.index.union(idx)).ffill().reindex(idx).reindex(columns=codes)
    ret = C.pct_change()
    r20 = C / C.shift(20) - 1
    r20 = r20.sub(r20.mean(axis=1), axis=0)
    FR = {h: (C.shift(-h) / C - 1) for h in (5, 20)}
    DD = {}
    for h in (5, 20):
        mn = None
        for k in range(1, h + 1):
            p = C.shift(-k) / C - 1
            mn = p if mn is None else np.minimum(mn, p)
        DD[h] = mn
    return dict(C=C, val=val, v5=val.rolling(5).sum(), v20=val.rolling(20).sum(), n5=NETV.rolling(5).sum(),
                YOY=YOY.to_numpy(), r20=r20.to_numpy(), FR={h: FR[h].to_numpy() for h in FR}, DD={h: DD[h].to_numpy() for h in DD}, ret=ret)


def dyn_components(lab, F):
    """每天、每個分群的四個子項原始值與在群間的百分位排名；並算每日分群層級的前瞻 IC（供子項檢驗）。"""
    T, N = lab.shape
    names = list(COMPS)
    RAW = {n: np.full((T, N), np.nan) for n in names}
    PR = {n: np.full((T, N), np.nan) for n in names}
    ic = {(n, h, k): np.full(T, np.nan) for n in names for h in (5, 20) for k in ("報酬", "回撤")}
    v5, v20, n5 = F["v5"].to_numpy(), F["v20"].to_numpy(), F["n5"].to_numpy()
    r20, yoy = F["r20"], F["YOY"]
    for t in range(T):
        lb = lab[t]
        ks = np.unique(lb[lb >= 0])
        if len(ks) < 5:
            continue
        tv5, tv20 = np.nansum(v5[t]), np.nansum(v20[t])
        rows = {n: [] for n in names}
        for k in ks:
            m = lb == k
            rows["相對強度"].append(np.nanmean(r20[t, m]))
            s5 = np.nansum(v5[t, m]); s20 = np.nansum(v20[t, m])
            rows["法人買超"].append(np.nansum(n5[t, m]) / s5 if s5 > 0 else np.nan)
            rows["成交比重上升"].append((s5 / tv5) / (s20 / tv20) if s20 > 0 and tv5 > 0 else np.nan)
            y = yoy[t, m]
            rows["營收動能"].append(np.clip(np.nanmedian(y) / 0.30, 0, 1) if np.isfinite(y).any() else 0.0)
        for n in names:
            v = np.array(rows[n], float)
            pr = pd.Series(v).rank(pct=True).to_numpy() if n != "營收動能" else v
            for k, a, b in zip(ks, v, pr):
                m = lb == k
                RAW[n][t, m] = a; PR[n][t, m] = b
            for h in (5, 20):
                fr = np.array([np.nanmean(F["FR"][h][t, lb == k]) for k in ks])
                dd = np.array([np.nanmean(F["DD"][h][t, lb == k]) for k in ks])
                ex = fr - np.nanmean(F["FR"][h][t])
                if np.isfinite(ex).sum() >= 5 and np.isfinite(v).sum() >= 5:
                    ic[(n, h, "報酬")][t] = pd.Series(v).corr(pd.Series(ex), method="spearman")
                    ic[(n, h, "回撤")][t] = pd.Series(v).corr(pd.Series(dd), method="spearman")
    return RAW, PR, ic


def l2_tests(ic, idx, a, b):
    """用 [a, b-30 天) 的每日 IC 平均；t 值依重疊校正。"""
    b = pd.Timestamp(b) - pd.Timedelta(days=30)
    msk = (idx >= pd.Timestamp(a)) & (idx < b)
    rows = []
    for n, w in COMPS.items():
        row = dict(層="族群(機械分群)", 子項=n, 權重=w)
        for h in (5, 20):
            for k in ("報酬", "回撤"):
                s = pd.Series(ic[(n, h, k)][msk]).dropna()
                n_eff = max(len(s) / h, 3)
                row[f"IC{k}{h}"] = s.mean()
                row[f"t{k}{h}"] = s.mean() / (s.std() / np.sqrt(n_eff)) if s.std() > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def group_score(PR, RAW_keep, keep, lab):
    """保留子項加權（重縮放到 10）-> 對每檔股票 EMA(5) 平滑 -> 每天前 TOPK 個分群為合格。"""
    T, N = lab.shape
    tot = np.zeros((T, N)); ws = 0.0
    for n in keep:
        tot += COMPS[n] * np.nan_to_num(PR[n], nan=0.0); ws += COMPS[n]
    sc = tot * 10.0 / max(ws, 1e-9)
    sc[lab < 0] = np.nan
    sm = pd.DataFrame(sc).ewm(span=SPAN, adjust=False, ignore_na=True).mean().to_numpy().copy()
    sm[lab < 0] = np.nan
    elig = np.zeros((T, N), bool)
    for t in range(T):
        lb = lab[t]; ks = np.unique(lb[lb >= 0])
        if len(ks) < 5:
            continue
        mv = np.array([np.nanmean(sm[t, lb == k]) for k in ks])
        top = ks[np.argsort(-np.nan_to_num(mv, nan=-1))[:TOPK]]
        elig[t] = np.isin(lb, top)
    return sm, elig


# ------------------------------------------------------------------ 衛星進場訊號
def pullback_signals(M3):
    """回檔進場：多頭結構（20 日線 > 60 日線 且 收盤 > 60 日線）下，近 3 日最低價碰到 20 日線，
    且今天收回 20 日線之上並比昨天高。出場＝收盤跌破 60 日線（趨勢破壞）。"""
    idx, codes = M3["idx"], M3["codes"]
    T, N = M3["Cf"].shape
    ent = np.zeros((T, N), bool); ex = np.zeros((T, N), bool)
    for j, c in enumerate(codes):
        df = M3["frames"][c].reindex(idx)
        cl = df["close"].ffill()
        s20, s60 = cl.rolling(20).mean(), cl.rolling(60).mean()
        low3 = df["low"].rolling(3).min()
        e = (s20 > s60) & (cl > s60) & (low3 <= s20) & (cl > s20) & (cl > cl.shift(1))
        ent[:, j] = e.fillna(False).to_numpy()
        ex[:, j] = (cl < s60).fillna(False).to_numpy()
    ST = M3["sig"]["ST"]
    return {"PB": (ent, ex, np.ones((T, N), bool), ST[3]), "ST": ST}


# ------------------------------------------------------------------ 核心／衛星模擬
def simulate4(M, cfg, t_lo=None, t_hi=None):
    """核心 0050 + 衛星個股。cfg: entry(PB/ST), S(衛星總預算), slots, stop_k, stop_mode(intra/close),
    use_cut(大盤分數極低時核心降到 50% 並停新增衛星), use_group(合格分群限定)。"""
    idx, codes = M["idx"], M["codes"]
    O, L, Cf = M["O"], M["L"], M["Cf"]
    ent, ex, vc, atr = M["sig4"][cfg.get("entry", "PB")]
    score = M["score"].to_numpy()
    GS, ELIG = M["gs"], M["elig"]
    O50, C50 = M["O50"], M["C50"]
    T, N = Cf.shape
    t0 = idx.searchsorted(pd.Timestamp(T_START)) if t_lo is None else t_lo
    t1 = T - 1 if t_hi is None else t_hi
    S, slots = cfg.get("S", 0.3), cfg.get("slots", 6)
    k, smode = cfg.get("stop_k", 5.0), cfg.get("stop_mode", "intra")
    use_cut, use_group = cfg.get("use_cut", True), cfg.get("use_group", True)
    core_on = cfg.get("core", True)
    cash, sb = 1.0, 0.0
    shares = np.zeros(N); epx = np.zeros(N); stop = np.full(N, -1e18); mae = np.zeros(N)
    held = np.zeros(N, bool); eidx = np.zeros(N, int)
    pend_out, pend_in, info, trades = {}, {}, {}, []
    tgt_b = 1.0 if core_on else None
    eq = np.full(T, np.nan); stk = np.zeros(T); tot = np.zeros(T)

    def sell_core(amount, px):
        nonlocal cash, sb
        sh = min(sb, amount / (px * (1 - SLIP) * (1 - FEE - ETF_TAX)))
        cash += sh * px * (1 - SLIP) * (1 - FEE - ETF_TAX); sb -= sh

    def close_pos(i, px, t, why):
        nonlocal cash
        px = px * (1 - SLIP)
        cash += shares[i] * px * (1 - FEE - TAX)
        trades.append(dict(code=codes[i], entry_i=eidx[i], exit_i=t, entry_px=epx[i], exit_px=px,
                           ret=px * (1 - FEE - TAX) / (epx[i] * (1 + FEE)) - 1, mae=mae[i], exit_reason=why))
        held[i] = False; shares[i] = 0.0; stop[i] = -1e18

    for t in range(t0, t1 + 1):
        eq_prev = eq[t - 1] if t > t0 else 1.0
        for i in list(np.where(held)[0]):
            if i in pend_out and np.isfinite(O[t, i]):
                close_pos(i, O[t, i], t, pend_out.pop(i)); continue
            if smode == "intra" and stop[i] > 0 and np.isfinite(O[t, i]):
                if O[t, i] <= stop[i]:
                    close_pos(i, O[t, i], t, "ATR停損（開盤跳空，以開盤價出）")
                elif np.isfinite(L[t, i]) and L[t, i] <= stop[i]:
                    close_pos(i, stop[i], t, "ATR停損（盤中觸價，以停損價出）")
        pend_out = {i: w for i, w in pend_out.items() if held[i]}
        for i, inf in list(pend_in.items()):
            px = O[t, i]
            if not np.isfinite(px) or held[i] or px > Cf[t - 1, i] + 1.0 * inf["atr"]:
                continue
            amt = eq_prev * inf["w"]
            if cash < amt and sb > 0:
                sell_core(amt - cash, O50[t])
            amt = min(cash, amt)
            if amt <= 0:
                continue
            px *= (1 + SLIP)
            shares[i] = amt / (px * (1 + FEE)); cash -= amt
            epx[i] = px; held[i] = True; eidx[i] = t; mae[i] = 0.0; stop[i] = inf["stop"]; info[(i, t)] = inf
            if smode == "intra" and np.isfinite(L[t, i]) and L[t, i] <= stop[i]:
                close_pos(i, stop[i], t, "ATR停損（盤中觸價，以停損價出）")
        pend_in = {}
        if core_on and tgt_b is not None:
            val_s = sum(shares[i] * Cf[t - 1, i] for i in np.where(held)[0])
            cur = sb * C50[t - 1]
            eqo = cash + val_s + cur
            diff = tgt_b * eqo - cur
            if abs(diff) > BAND * eqo or t == t0:
                if diff > 0:
                    amt = min(diff, cash); px = O50[t] * (1 + SLIP)
                    sb += amt / (px * (1 + FEE)); cash -= amt
                else:
                    sell_core(-diff, O50[t])
            tgt_b = None
        vs = 0.0
        for i in np.where(held)[0]:
            vs += shares[i] * Cf[t, i]
            if np.isfinite(L[t, i]):
                mae[i] = min(mae[i], L[t, i] / epx[i] - 1)
        eq[t] = cash + vs + sb * C50[t]
        stk[t] = vs / eq[t]; tot[t] = (vs + sb * C50[t]) / eq[t]
        if t == t1:
            break
        low = use_cut and score[t] < CUT
        for i in np.where(held)[0]:
            if i in pend_out:
                continue
            c = Cf[t, i]; a = atr[t, i]
            if np.isfinite(a):
                stop[i] = max(stop[i], c - k * a)
            if smode == "close" and c < stop[i]:
                pend_out[i] = "ATR停損（收盤確認）"
            elif ex[t, i]:
                pend_out[i] = "技術出場(%s)" % cfg.get("entry", "PB")
        n_hold = int(sum(1 for i in np.where(held)[0] if i not in pend_out))
        planned = []
        room = slots - n_hold
        if room > 0 and not low and S > 0:
            ok = ent[t] & vc[t] & ~held & np.isfinite(O[t + 1]) & np.isfinite(atr[t])
            if use_group:
                ok &= ELIG[t]
            cand = np.where(ok)[0]
            if len(cand):
                g = np.nan_to_num(GS[t, cand], nan=0.0)
                rs = np.nan_to_num(M["stock_rs"][t, cand], nan=-9)
                order = np.lexsort((-rs, -g))[:room]
                for o in order:
                    i = cand[o]
                    pend_in[i] = dict(sig_t=t, l1=score[t], w=S / slots, atr=float(atr[t, i]),
                                      stop=float(Cf[t, i] - k * atr[t, i]), grp_score=float(g[o]), stock_rs20=float(rs[o]))
                    planned.append(S / slots)
        if core_on:
            lvl = CORE_CUT_W if low else 1.0
            keep_val = sum(shares[i] * Cf[t, i] for i in np.where(held)[0] if i not in pend_out)
            tgt_b = max(0.0, lvl - (keep_val / eq[t] + sum(planned)))
    e = pd.Series(eq, index=idx).iloc[t0:t1 + 1]
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["entry"] = idx[tr["entry_i"]]; tr["exit"] = idx[tr["exit_i"]]
        tr["hold_days"] = (tr["exit"] - tr["entry"]).dt.days
    M["_info4"] = info
    return e, tr, pd.Series(stk, index=idx).iloc[t0:t1 + 1], pd.Series(tot, index=idx).iloc[t0:t1 + 1]


def run4(M, cfg, t_lo=None, t_hi=None, liquidate=False):
    e, tr, sf, tf = simulate4(M, cfg, t_lo, t_hi)
    if liquidate:       # 窗尾全部賣出的成本，與 0050 基準（窗首買、窗尾賣）同一個公平基礎
        e = e.copy()
        core = max(tf.iloc[-1] - sf.iloc[-1], 0.0)
        e.iloc[-1] *= 1 - core * (FEE + ETF_TAX + SLIP) - sf.iloc[-1] * (FEE + TAX + SLIP)
    return dict(eq=e, tr=tr, stk=sf, tot=tf, cfg=cfg, info=dict(M.get("_info4", {})))


def _with_start(eq: pd.Series) -> pd.Series:
    return pd.concat([pd.Series([1.0], index=[eq.index[0] - pd.Timedelta(days=1)]), eq])


def seg_row4(name, r_full, r_oos, M, group, extra=None):
    """樣本內／全期用連續回測；樣本外用「從樣本外起點空手重新開始、窗尾清倉」的獨立回測，
    和 0050 基準（窗首買、窗尾賣、扣同樣成本）站在同一個基礎上比較。"""
    row = T3.seg_row(name, r_full, M, group, extra)
    bh = stats(T3.bh0050(M, SPLIT).dropna(), 245)
    m = T3.metrics3(r_oos, pd.Timestamp(SPLIT))
    st = stats(_with_start(r_oos["eq"]).pct_change().dropna(), 245)      # 補上「窗首買進當天」的報酬，與 0050 基準同一基礎
    m.update(cagr=st["cagr"], mdd=st["mdd"], sharpe=st["sharpe"])
    for k, v in m.items():
        row[f"樣本外_{k}"] = v
    row["樣本外_0050年化"], row["樣本外_0050回撤"], row["樣本外_0050夏普"] = bh["cagr"], bh["mdd"], bh["sharpe"]
    row["樣本外_差距"] = row["樣本外_cagr"] - bh["cagr"]
    row["判定"] = T3.verdict(row["樣本外_cagr"], bh["cagr"])
    if group == "對照":
        row["判定"] = "基準／對照（不是策略）"
    return row


# ------------------------------------------------------------------ 組裝／主流程
WF_FOLDS = T3.WF_FOLDS


def build4():
    M = T3.build3()
    F = flows(M)
    M["F"] = F
    M["sig4"] = pullback_signals(M)
    lab = {"mech": mech_labels(F["ret"]), "industry": industry_labels(M["codes"], M["Cf"].shape)}
    M["lab"] = lab
    M["dyn"] = {k: dyn_components(v, F) for k, v in lab.items()}
    return M


def fit4(M, lab_key, train_end):
    idx = M["idx"]
    b_eff = pd.Timestamp(train_end) - pd.Timedelta(days=30)        # 避免前瞻報酬跨過切點
    t1 = T3.l1_item_tests(M["f"], M["c50"], pd.Timestamp(T_START), b_eff)
    msk = (idx >= pd.Timestamp(T_START)) & (idx < b_eff)
    c1 = M["f"][[c for c in M["f"].columns if c != "總分"]][msk].corr(method="spearman")
    keep1, t1 = T3.decide_keep(t1, c1, "direction")
    _, _, ic = M["dyn"][lab_key]
    t2 = l2_tests(ic, idx, T_START, train_end)
    t2["通過"] = (t2["IC報酬5"] > 0) & (t2["IC報酬20"] > 0)
    t2["結論"] = np.where(t2["通過"], "保留", "預測力不足")
    keep2 = t2.loc[t2["通過"], "子項"].tolist()
    return keep1, keep2, pd.concat([t1, t2], ignore_index=True)


def apply4(M, lab_key, keep1, keep2):
    M["score"] = T3.l1_score(M["f"], keep1) if keep1 else pd.Series(10.0, index=M["idx"])
    RAW, PR, _ = M["dyn"][lab_key]
    lab = M["lab"][lab_key]
    if keep2:
        M["gs"], M["elig"] = group_score(PR, RAW, keep2, lab)
    else:
        M["gs"], M["elig"] = np.zeros(lab.shape), np.ones(lab.shape, bool)
    M["_lab_key"] = lab_key; M["_keep1"] = keep1; M["_keep2"] = keep2


def build_log4(r, M):
    idx, codes = M["idx"], M["codes"]
    RAW, _, _ = M["dyn"][M["_lab_key"]]
    rows = []
    for _, x in r["tr"].iterrows():
        i = codes.index(x["code"])
        inf = r["info"].get((i, int(x["entry_i"])), {})
        st = int(inf.get("sig_t", x["entry_i"] - 1))
        row = dict(代號=x["code"], 訊號日=idx[st].date(), 進場日=x["entry"].date(), 進場價=round(x["entry_px"], 2),
                   出場日=x["exit"].date(), 出場價=round(x["exit_px"], 2), 報酬率=round(x["ret"], 4), 持有天數=int(x["hold_days"]),
                   最大不利偏移=round(x["mae"], 4), 出場原因=x["exit_reason"], 衛星部位占權益=round(inf.get("w", np.nan), 3),
                   初始停損價=round(inf.get("stop", np.nan), 2), 進場時大盤分數=round(float(M["score"].iloc[st]), 2),
                   分群編號=int(M["lab"][M["_lab_key"]][st, i]), 分群平滑分數=round(float(inf.get("grp_score", np.nan)), 2))
        for n in COMPS:
            v = RAW[n][st, i]
            row["分群_" + n] = round(float(v), 4) if np.isfinite(v) else np.nan
        row["個股訊號"] = r["cfg"]["entry"]; row["個股20日相對強度"] = round(inf.get("stock_rs20", np.nan), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def main4():
    OUT.mkdir(parents=True, exist_ok=True)
    M = build4()
    idx = M["idx"]
    t_start = idx.searchsorted(pd.Timestamp(T_START))
    keeps, tests_all = {}, []
    for lk in ("mech", "industry"):
        k1, k2, tt = fit4(M, lk, SPLIT)
        keeps[lk] = (k1, k2)
        tt = tt.assign(分群方式=lk)
        tests_all.append(tt)
    pd.concat(tests_all).to_csv(OUT / "subitem_tests.csv", index=False, encoding="utf-8-sig")
    print("保留", keeps)
    rows, runs = [], {}

    def go(name, group, lk, cfg):
        apply4(M, lk, *keeps[lk])
        cfg = dict(cfg)
        if not keeps[lk][1]:
            cfg["use_group"] = False
        r = run4(M, cfg)
        if r["tr"].empty:
            r["tr"] = pd.DataFrame(columns=["code", "entry_i", "exit_i", "entry_px", "exit_px", "ret", "mae", "exit_reason", "entry", "exit", "hold_days"])
        runs[name] = r
        r_oos = run4(M, cfg, idx.searchsorted(pd.Timestamp(SPLIT)), None, liquidate=True)
        if r_oos["tr"].empty:
            r_oos["tr"] = r["tr"].iloc[0:0]
        rows.append(seg_row4(name, r, r_oos, M, group, dict(分群方式=lk, 設定=str({k: v for k, v in cfg.items()}))))
        return r

    go("純0050（含成本，驗證引擎）", "對照", "mech", dict(S=0.0, use_cut=False))
    go("0050 + 大盤分數極低降水位（無衛星）", "對照", "mech", dict(S=0.0, use_cut=True))
    for lk in ("mech", "industry"):
        if lk == "industry" and not keeps["mech"][1] and not keeps["industry"][1]:
            continue            # 兩種分群的子項在樣本內都沒通過 -> 第二層關閉，兩者結果完全相同，不重複列
        for entry in ("PB", "ST"):
            for S in (0.2, 0.4):
                for (k, sm, sl) in ((5.0, "intra", "5ATR觸價"), (3.0, "close", "3ATR收盤確認")):
                    for cut in (True, False):
                        nm = f"核心衛星 分群={lk} 進場={entry} 衛星{int(S*100)}% 停損={sl} {'極低降水位' if cut else '核心永遠滿倉'}"
                        go(nm, "核心衛星", lk, dict(entry=entry, S=S, slots=6, stop_k=k, stop_mode=sm, use_cut=cut))
    for lk in ("mech", "industry"):      # 強制使用族群層（四個子項等權），觀察兩種分群各自的效果；樣本內無預測力，僅供對照
        keeps[lk + "_forced"] = (keeps[lk][0], list(COMPS)); M["lab"][lk + "_forced"] = M["lab"][lk]; M["dyn"][lk + "_forced"] = M["dyn"][lk]
        go(f"強制使用族群層 分群={lk} PB 衛星40% 5ATR觸價 極低降水位", "族群對照", lk + "_forced",
           dict(entry="PB", S=0.4, slots=6, stop_k=5.0, stop_mode="intra", use_cut=True))
    go("衛星不限族群（對照）PB 40% 5ATR", "對照", "mech", dict(entry="PB", S=0.4, slots=6, stop_k=5.0, stop_mode="intra", use_cut=True, use_group=False))
    # ---- walk-forward：每段重估子項，並在 8 種組合中選「訓練期超額年化(對 0050)」最高者
    wf_rows, chain = [], []
    for ts, te in WF_FOLDS:
        k1, k2, _ = fit4(M, "mech", ts)
        apply4(M, "mech", k1, k2)
        t_tr = idx.searchsorted(pd.Timestamp(ts)) - 1
        bh_tr = stats(T3.bh0050(M, T_START, ts).dropna(), 245)["cagr"]
        best = None
        for entry in ("PB", "ST"):
            for S in (0.2, 0.4):
                for (k, sm) in ((5.0, "intra"), (3.0, "close")):
                    cfg = dict(entry=entry, S=S, slots=6, stop_k=k, stop_mode=sm, use_cut=True, use_group=bool(k2))
                    r = run4(M, cfg, t_start, t_tr)
                    ex = stats(r["eq"].pct_change().dropna(), 245)["cagr"] - bh_tr
                    if best is None or np.nan_to_num(ex, nan=-9) > best[0]:
                        best = (np.nan_to_num(ex, nan=-9), cfg)
        cfg = best[1]
        t_lo = idx.searchsorted(pd.Timestamp(ts))
        t_hi = (idx.searchsorted(pd.Timestamp(te), side="right") - 1) if te else len(idx) - 1
        r = run4(M, cfg, t_lo, t_hi, liquidate=True)
        a, b = idx[t_lo], idx[t_hi]
        sg = stats(_with_start(r["eq"]).pct_change().dropna(), 245)
        bhr = T3.bh0050(M, a, b + pd.Timedelta(days=1)).dropna()
        bh = stats(bhr, 245)
        tot = r["eq"].iloc[-1] - 1
        bht = (1 + bhr).prod() - 1
        wf_rows.append(dict(段=f"測試 {a.date()}~{b.date()}", 訓練止=ts, 保留大盤子項=",".join(k1), 保留族群子項=",".join(k2),
                            選到的設定=f"{cfg['entry']}／衛星{int(cfg['S']*100)}%／{'5ATR觸價' if cfg['stop_mode']=='intra' else '3ATR收盤確認'}",
                            訓練期超額年化=round(best[0], 3), 區間報酬=tot, 同窗0050區間報酬=bht, 年化=sg["cagr"], 同窗0050年化=bh["cagr"],
                            最大回撤=sg["mdd"], 同窗0050回撤=bh["mdd"], 夏普=sg["sharpe"], 贏大盤=bool(tot >= bht)))
        chain.append(r["eq"] / r["eq"].iloc[0] * (chain[-1].iloc[-1] if chain else 1.0))
    wf = pd.DataFrame(wf_rows)
    wf.to_csv(OUT / "wf_results.csv", index=False, encoding="utf-8-sig")
    wfeq = pd.concat(chain)
    wc = stats(_with_start(wfeq).pct_change().dropna(), 245)
    bw = stats(T3.bh0050(M, wfeq.index[0], wfeq.index[-1] + pd.Timedelta(days=1)).dropna(), 245)
    rows.append(dict(策略="Walk-forward（四段串接）", 類別="walk-forward", 樣本外_cagr=wc["cagr"], 樣本外_mdd=wc["mdd"], 樣本外_sharpe=wc["sharpe"],
                     樣本外_0050年化=bw["cagr"], 樣本外_差距=wc["cagr"] - bw["cagr"], 判定=T3.verdict(wc["cagr"], bw["cagr"]),
                     贏大盤段數=f"{int(wf['贏大盤'].sum())}/{len(wf)}"))
    # ---- 固定設定的候選（強制使用族群層）逐段與 0050 比較：看名義上通過的版本是否穩定
    fixed = []
    cfg_fixed = dict(entry="PB", S=0.4, slots=6, stop_k=5.0, stop_mode="intra", use_cut=True)
    for lk in ("mech", "industry"):
        apply4(M, lk + "_forced", *keeps[lk + "_forced"])
        for ts, te in [("2021-04-01", "2021-12-31"), ("2022-01-01", "2022-12-31")] + WF_FOLDS:
            t_lo = idx.searchsorted(pd.Timestamp(ts)); t_hi = (idx.searchsorted(pd.Timestamp(te), side="right") - 1) if te else len(idx) - 1
            r = run4(M, cfg_fixed, t_lo, t_hi, liquidate=True)
            a, b = idx[t_lo], idx[t_hi]
            bhr = T3.bh0050(M, a, b + pd.Timedelta(days=1)).dropna()
            tot, bht = r["eq"].iloc[-1] - 1, (1 + bhr).prod() - 1
            fixed.append(dict(分群=lk, 段=f"{a.date()}~{b.date()}", 區間報酬=tot, 同窗0050區間報酬=bht, 差=tot - bht,
                              最大回撤=stats(r["eq"].pct_change().dropna(), 245)["mdd"], 贏大盤=bool(tot >= bht)))
    fx = pd.DataFrame(fixed)
    fx.to_csv(OUT / "fixed_candidate_by_period.csv", index=False, encoding="utf-8-sig")
    print(fx.round(3).to_string())
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "ablation_results.csv", index=False, encoding="utf-8-sig")
    # ---- 日誌：預先指定的標題設定（PB、衛星 40%、5ATR 觸價、極低降水位、機械分群）
    head = "核心衛星 分群=mech 進場=PB 衛星40% 停損=5ATR觸價 極低降水位"
    apply4(M, "mech", *keeps["mech"])
    build_log4(runs[head], M).to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    nm_f = "強制使用族群層 分群=mech PB 衛星40% 5ATR觸價 極低降水位"
    apply4(M, "mech_forced", *keeps["mech_forced"])
    build_log4(runs[nm_f], M).to_csv(OUT / "trades_nominal_pass_forced_mech.csv", index=False, encoding="utf-8-sig")
    apply4(M, "mech", *keeps["mech"])
    pd.DataFrame({k: v["eq"] for k, v in runs.items() if k in (head, nm_f, "純0050（含成本，驗證引擎）")}).join(wfeq.rename("walk-forward")).to_csv(
        OUT / "equity_curves.csv", encoding="utf-8-sig", index_label="date")
    daily = pd.DataFrame({"大盤分數": M["score"]}).iloc[t_start:]
    daily.round(3).to_csv(OUT / "daily_score.csv", encoding="utf-8-sig", index_label="date")
    lab = M["lab"]["mech"]
    pd.DataFrame({"月份": [str(idx[t].to_period("M")) for t in range(t_start, len(idx)) if t == t_start or idx[t].month != idx[t - 1].month],
                  "分群數": [len(set(lab[t][lab[t] >= 0])) for t in range(t_start, len(idx)) if t == t_start or idx[t].month != idx[t - 1].month],
                  "有分群的股票數": [int((lab[t] >= 0).sum()) for t in range(t_start, len(idx)) if t == t_start or idx[t].month != idx[t - 1].month]}
                 ).to_csv(OUT / "cluster_summary.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print(res[["策略", "樣本內_cagr", "樣本外_cagr", "樣本外_0050年化", "樣本外_差距", "樣本外_mdd", "樣本外_sharpe", "樣本外_n", "樣本外_stock_expo", "樣本外_total_expo", "判定"]].round(3).to_string())
    print(wf.round(3).to_string())
    return M, res, wf


if __name__ == "__main__":
    main4()


def paper_signals4(name: str):
    """前向模擬盤：收盤後輸出「明天開盤」的核心／衛星目標。依淘汰規則先查 ablation_results.csv 的判定；
    只讀資料湖、不下單、不接排程。名義通過的策略仍須人工確認（見 README 的警語）。"""
    ok, why = T3.paper_gate(pd.read_csv(OUT / "ablation_results.csv"), name)
    if not ok:
        return dict(allowed=False, reason=why + "；依規則不出訊號。")
    M = build4()
    k1, k2, _ = fit4(M, "mech", SPLIT)
    apply4(M, "mech", k1, list(COMPS) if "強制使用族群層" in name else k2)
    t = len(M["idx"]) - 1
    ent, ex, vc, atr = M["sig4"]["PB"]
    s = float(M["score"].iloc[t])
    low = s < CUT
    cands = [dict(代號=M["codes"][i], 收盤=float(M["Cf"][t, i]), 初始停損=float(M["Cf"][t, i] - 5.0 * atr[t, i]))
             for i in np.where(ent[t] & M["elig"][t])[0]] if not low else []
    return dict(allowed=True, asof=str(M["idx"][t].date()), 大盤分數=round(s, 2), 核心0050目標=CORE_CUT_W if low else 1.0,
                衛星候選=cands, 備註="名義通過，須人工複核")
