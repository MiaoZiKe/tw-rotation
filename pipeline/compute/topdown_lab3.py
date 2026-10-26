"""第三輪：在第二輪三層架構上做六件事，並加上「輸給 0050 就淘汰」規則。

  1. 子項預測力檢驗（只用樣本內）：每個大盤子項／族群子項對未來 5、20 日報酬與回撤的 IC 與分組報酬，
     依事先定好的規則保留或剔除，並去掉彼此高度相關（與均線重複）的子項。
  2. 族群分數 EMA(5) 平滑；族群降級只擋新進場，不強制出場。
  3. 資金使用率兩案：scale＝未滿檔放大單檔權重；base＝0050 當底倉（分數決定加減碼）；both＝兩者。
  4. 停損改 ATR 基準（收盤算出停損價，隔日用「開盤跳空→開盤價成交、盤中觸價→停損價成交」），
     進場若開盤跳空超過 1 個 ATR 就取消（不追跳空）。
  5. 族群成分改用 git 歷史最早版本（2026-09-10，26 個族群）；另跑法定產業別（無事後偏誤）與最新版（第二輪）對照。
  6. 滾動 walk-forward（擴展訓練窗，測試 2023／2024／2025／2026 年初至今，各自重估子項與進場訊號／部位法）。
淘汰規則（Andy 原話「只要那個策略低於大盤，就不要使用」）：樣本外年化報酬 < 同窗、同成本、含息的 0050 買進持有 -> 淘汰。

所有價格改為「還原權息」（用資料湖 dividend_results 的參考價／除權息前收盤），策略與 0050 同口徑，
所以和第二輪（未還原）的數字不能直接比，README 另附第二輪 D 在含息價上的重跑。
研究用，不是買賣建議。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import topdown_lab as T2  # noqa: E402
from pipeline.compute.strategy_lab import FEE, TAX, SLIP, _fix_splits, set_calendar, stats  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round3"
T_START, SPLIT = T2.T_START, T2.SPLIT
ETF_TAX = 0.001                  # ETF 證交稅 0.1%
STOP_ATR = 3.0                   # 停損 = 收盤 - 3 ATR（只上移）
GAP_SKIP_ATR = 1.0               # 開盤高於前收 1 ATR 以上就取消進場
WMAX = 0.25                      # scale 案單檔上限
SLOTS = 10
THR_HALF, THR_FULL = 4.0, 7.0
SMOOTH_SPAN = 5
MODES = {"first": "groups_49ef289.yaml"}     # git 歷史最早版本（2026-09-10）


# ------------------------------------------------------------------ 資料（含息還原）
def _rd(t, cols=None):
    return T2._rd(t, cols)


def dividend_adjust(frames: dict) -> dict:
    """依除權息前收盤／參考價把除息日以前的價格往下調，使價格＝總報酬（含息）。
    比值落在 [0.6,1.67] 之外視為分割／減資，已由 _fix_splits 處理，這裡跳過避免重複調整。"""
    dv = _rd("dividend_results", ["date", "code", "before_price", "reference_price"])
    dv = dv.dropna().drop_duplicates(["date", "code"])
    dv["ratio"] = dv["reference_price"] / dv["before_price"]
    dv = dv[(dv["ratio"] > 0.6) & (dv["ratio"] < 1.0)]
    dv["date"] = pd.to_datetime(dv["date"])
    out = {}
    for c, df in frames.items():
        d = dv[dv["code"] == c].sort_values("date")
        if len(d) == 0:
            out[c] = df
            continue
        f = pd.Series(1.0, index=df.index)
        for dt, r in zip(d["date"], d["ratio"]):
            f[f.index < dt] *= r
        df = df.copy()
        for k in ("open", "high", "low", "close"):
            df[k] = df[k] * f
        out[c] = df
    return out


def load3(n_univ=200):
    p = _rd("price_daily", ["date", "code", "open", "high", "low", "close", "volume", "turnover"])
    p = p[p["code"].str.fullmatch(r"\d{4}") & (p["close"] > 0) & (p["date"] >= "2019-06-01")]
    p["date"] = pd.to_datetime(p["date"])
    p = p.sort_values(["code", "date"]).drop_duplicates(["code", "date"])
    C_all = p.pivot(index="date", columns="code", values="close")
    w = p[(p["date"] >= "2020-01-01") & (p["date"] <= "2020-12-31")]
    liq = w.groupby("code")["turnover"].median().sort_values(ascending=False)
    codes = [c for c in liq.index if not c.startswith("00")][:n_univ]      # 與族群無關，避免用事後分類選股
    frames = {}
    for c, g in p[p["code"].isin(codes + ["0050"])].groupby("code"):
        g = g.set_index("date")[["open", "high", "low", "close", "volume"]]
        frames[c] = _fix_splits(g)
    frames = dividend_adjust(frames)
    return p, C_all, frames, codes


def membership_modes(codes):
    mem = {}
    from pipeline.groups import loader
    m = loader.membership()
    mem["latest"] = (m.rename(columns={"group_id": "group_id"})[["code", "group_id"]],
                     {g: v.get("name", g) for g, v in loader.load()["groups"].items()})
    y = yaml.safe_load(open(OUT / "groups_history" / MODES["first"], encoding="utf-8"))["groups"]
    rows = [(c, gid) for gid, g in y.items() for c in g.get("codes") or []]
    mem["first"] = (pd.DataFrame(rows, columns=["code", "group_id"]), {g: v.get("name", g) for g, v in y.items()})
    ci = pd.concat([pd.read_parquet(f) for f in (ROOT / "data" / "company_info").glob("**/*.parquet")])
    ci = ci[ci["code"].str.fullmatch(r"\d{4}") & ci["industry"].notna()]
    ci = ci.drop_duplicates("code")
    mem["industry"] = (pd.DataFrame({"code": ci["code"], "group_id": "ind_" + ci["industry"].astype(str)}),
                       {"ind_" + i: i for i in ci["industry"].unique()})
    return mem


# ------------------------------------------------------------------ 預測力檢驗
def _fwd(c: pd.Series, h: int):
    ret = c.shift(-h) / c - 1
    path = pd.concat([c.shift(-k) / c - 1 for k in range(1, h + 1)], axis=1)
    return ret, path.min(axis=1)


def _ic_row(x: pd.Series, y: pd.Series, h: int):
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 60 or d.iloc[:, 0].nunique() < 2:
        return np.nan, np.nan
    ic = d.iloc[:, 0].rank().corr(d.iloc[:, 1].rank())
    n_eff = max(len(d) / h, 3)
    t = ic * np.sqrt(n_eff - 2) / np.sqrt(max(1 - ic ** 2, 1e-9))
    return ic, t


def l1_item_tests(f: pd.DataFrame, c50: pd.Series, a, b):
    """f: 大盤子項（不含總分）。a,b: 判斷用的區間（樣本內）。以 0050 含息價的未來報酬／回撤為目標。"""
    rows = []
    cols = [x for x in f.columns if x != "總分"]
    fw = {h: _fwd(c50, h) for h in (5, 20)}
    for col in cols:
        x = f[col]
        row = dict(層="大盤", 子項=col, 權重=float(x.abs().max()))
        for h in (5, 20):
            r, dd = fw[h]
            msk = (x.index >= a) & (x.index < b)
            ic_r, t_r = _ic_row(x[msk], r[msk], h)
            ic_d, t_d = _ic_row(x[msk], dd[msk], h)        # 回撤是負值；訊號好 -> 回撤較淺 -> IC 為正
            on = x[msk] > (x[msk].min() if col == "壓力扣分" else 0)
            if col == "壓力扣分":
                on = x[msk] == 0
            row.update({f"IC報酬{h}": ic_r, f"t報酬{h}": t_r, f"IC回撤{h}": ic_d, f"t回撤{h}": t_d,
                        f"成立日平均報酬{h}": r[msk][on].mean(), f"不成立日平均報酬{h}": r[msk][~on].mean(),
                        f"成立日平均回撤{h}": dd[msk][on].mean(), f"不成立日平均回撤{h}": dd[msk][~on].mean()})
        rows.append(row)
    return pd.DataFrame(rows)


def l2_item_tests(G, idx, a, b):
    """族群子項：每天橫斷面 Spearman IC（對族群未來 5/20 日相對大盤報酬與回撤），再對時間平均。"""
    comps = {"相對強度": (G["rs"], 3.0), "法人買超": (G["inst"], 3.0), "成交比重上升": (G["share"], 2.0),
             "營收動能": (np.clip(np.nan_to_num(G["rev"]) / 0.30, 0, 1), 2.0)}
    gret = pd.DataFrame(G["gret"], index=idx)
    mk = pd.Series(G["mkt_ret"], index=idx)
    cum = (1 + gret).cumprod()
    rows = []
    msk = (idx >= a) & (idx < b)
    for name, (arr, w) in comps.items():
        X = pd.DataFrame(arr, index=idx)
        row = dict(層="族群", 子項=name, 權重=w)
        for h in (5, 20):
            fr = (cum.shift(-h) / cum - 1).sub((1 + mk).cumprod().shift(-h) / (1 + mk).cumprod() - 1, axis=0)
            dd = pd.concat([cum.shift(-k) / cum - 1 for k in range(1, h + 1)], axis=0, keys=range(h)).groupby(level=1).min() \
                if False else None
            # 回撤：逐日走 h 步，取路徑最小值（向量化）
            mn = None
            for k in range(1, h + 1):
                pth = cum.shift(-k) / cum - 1
                mn = pth if mn is None else np.minimum(mn, pth)
            ics_r, ics_d = [], []
            Xm, frm, mnm = X[msk], fr[msk], mn[msk]
            xr = Xm.rank(axis=1); rr = frm.rank(axis=1); dr = mnm.rank(axis=1)
            ok = Xm.notna().sum(axis=1) >= 5
            ic_r = xr[ok].corrwith(rr[ok], axis=1)
            ic_d = xr[ok].corrwith(dr[ok], axis=1)
            for lab, s in (("報酬", ic_r), ("回撤", ic_d)):
                s = s.dropna()
                n_eff = max(len(s) / h, 3)
                row[f"IC{lab}{h}"] = s.mean()
                row[f"t{lab}{h}"] = s.mean() / (s.std() / np.sqrt(n_eff)) if s.std() > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def decide_keep(tests: pd.DataFrame, corr: pd.DataFrame | None = None, rule: str = "direction"):
    """事先定好的保留規則（只看樣本內）：
       20 日報酬 IC > 0 且 t >= 1.0，且 20 日回撤 IC >= 0（訊號好時回撤不更深）；
       再依 t 由大到小去重：與已保留項目相關係數 >= 0.7 者剔除（與均線重複）。"""
    t = tests.copy()
    strict = (t["IC報酬20"] > 0) & (t["t報酬20"] >= 1.0) & (t["IC回撤20"] >= 0)
    # 方向一致規則（看到嚴格規則全軍覆沒之後才加的，標為「弱證據」；仍只用樣本內）：5 日與 20 日 IC 同為正
    direction = (t["IC報酬5"] > 0) & (t["IC報酬20"] > 0)
    t["嚴格規則通過"] = strict
    t["通過"] = strict if rule == "strict" else direction
    keep, why = [], {}
    for _, r in t.sort_values("t報酬20", ascending=False).iterrows():
        nm = r["子項"]
        if not r["通過"]:
            why[nm] = "預測力不足"
            continue
        if corr is not None and any(abs(corr.loc[nm, k]) >= 0.7 for k in keep if nm in corr.index and k in corr.columns):
            why[nm] = "與已保留子項高度相關（重複）"
            continue
        keep.append(nm)
        why[nm] = "保留"
    t["結論"] = t["子項"].map(why)
    return keep, t


# ------------------------------------------------------------------ 分數組合
def l1_score(f: pd.DataFrame, keep: list[str]) -> pd.Series:
    wmax = sum(float(f[c].abs().max()) for c in keep if c != "壓力扣分")
    if wmax <= 0:
        return pd.Series(0.0, index=f.index)
    s = f[keep].sum(axis=1) * 10.0 / wmax
    return s.clip(0, 10)


def l2_score(G, idx, keep: list[str]):
    from pandas import DataFrame as DF
    comps = {"相對強度": (G["rs"], 3.0, True), "法人買超": (G["inst"], 3.0, True),
             "成交比重上升": (G["share"], 2.0, True), "營收動能": (np.clip(np.nan_to_num(G["rev"]) / 0.30, 0, 1), 2.0, False)}
    tot = np.zeros_like(G["rs"]); wsum = 0.0
    for nm in keep:
        arr, w, rank = comps[nm]
        tot = tot + (w * DF(arr).rank(axis=1, pct=True).to_numpy() if rank else w * arr)
        wsum += w
    sc = tot * 10.0 / max(wsum, 1e-9)
    sc[np.isnan(G["rs"])] = np.nan
    sm = pd.DataFrame(sc, index=idx).ewm(span=SMOOTH_SPAN, adjust=False, ignore_na=True).mean().to_numpy().copy()
    sm[np.isnan(G["rs"])] = np.nan
    return sc, sm


# ------------------------------------------------------------------ 模擬
def simulate3(M, cfg, t_lo=None, t_hi=None):
    idx, codes = M["idx"], M["codes"]
    O, H, L, Cf = M["O"], M["H"], M["L"], M["Cf"]
    ent, ex, vc, atr = M["sig"][cfg["entry"]]
    score = M["score"].to_numpy() if cfg.get("use_l1", True) else np.full(len(idx), 10.0)
    gs = M["gscore"]
    mem = M["mem_mat"]
    O50, C50 = M["O50"], M["C50"]
    T, N = Cf.shape
    t0 = idx.searchsorted(pd.Timestamp(T_START)) if t_lo is None else t_lo
    t1 = T - 1 if t_hi is None else t_hi
    use1, use2 = cfg.get("use_l1", True), cfg.get("use_l2", True)
    thr_h, thr_f = cfg.get("thr_half", THR_HALF), cfg.get("thr_full", THR_FULL)
    sizing, base = cfg.get("sizing", "equal"), cfg.get("base", False)
    topk, keepk = cfg.get("topk", 5), cfg.get("keep", 10)
    force_g = cfg.get("group_force_exit", False)
    cash = 1.0
    shares = np.zeros(N); epx = np.zeros(N); stop = np.full(N, -1e18); mae = np.zeros(N)
    held = np.zeros(N, bool); eidx = np.zeros(N, int)
    sb = 0.0                      # 0050 底倉股數
    pend_out, pend_in = {}, {}
    tgt_b = None
    trades, info = [], {}
    eq = np.full(T, np.nan); stk_frac = np.zeros(T); tot_frac = np.zeros(T)

    def sell_sleeve(amount, px):
        nonlocal cash, sb
        sh = min(sb, amount / (px * (1 - SLIP) * (1 - FEE - ETF_TAX)))
        cash += sh * px * (1 - SLIP) * (1 - FEE - ETF_TAX); sb -= sh

    def close_pos(i, px, t, why):
        nonlocal cash
        px = px * (1 - SLIP)
        cash += shares[i] * px * (1 - FEE - TAX)
        ret = px * (1 - FEE - TAX) / (epx[i] * (1 + FEE)) - 1
        trades.append(dict(code=codes[i], entry_i=eidx[i], exit_i=t, entry_px=epx[i], exit_px=px, ret=ret,
                           mae=mae[i], exit_reason=why))
        held[i] = False; shares[i] = 0.0; stop[i] = -1e18

    for t in range(t0, t1 + 1):
        eq_prev = eq[t - 1] if t > t0 else 1.0
        # --- 開盤：先處理跳空停損與前一天決定的出場
        for i in list(np.where(held)[0]):
            if i in pend_out and np.isfinite(O[t, i]):
                close_pos(i, O[t, i], t, pend_out.pop(i)); continue
            if stop[i] > 0 and np.isfinite(O[t, i]):
                if O[t, i] <= stop[i]:
                    close_pos(i, O[t, i], t, "ATR停損（開盤跳空，以開盤價出）")
                elif np.isfinite(L[t, i]) and L[t, i] <= stop[i]:
                    close_pos(i, stop[i], t, "ATR停損（盤中觸價，以停損價出）")
        pend_out = {i: w for i, w in pend_out.items() if held[i]}
        # --- 開盤：進場
        for i, inf in list(pend_in.items()):
            px = O[t, i]
            if not np.isfinite(px) or held[i]:
                continue
            if px > Cf[t - 1, i] + GAP_SKIP_ATR * inf["atr"]:
                continue                                             # 開盤跳空追價，取消
            amt = min(eq_prev * inf["w"], eq_prev)
            if cash < amt and base and sb > 0:
                sell_sleeve(amt - cash, O50[t])
            amt = min(cash, amt)
            if amt <= 0:
                continue
            px *= (1 + SLIP)
            shares[i] = amt / (px * (1 + FEE)); cash -= amt
            epx[i] = px; held[i] = True; eidx[i] = t; mae[i] = 0.0
            stop[i] = inf["stop"]
            info[(i, t)] = inf
            if np.isfinite(L[t, i]) and L[t, i] <= stop[i]:
                close_pos(i, stop[i], t, "ATR停損（盤中觸價，以停損價出）")
        pend_in = {}
        # --- 開盤：0050 底倉調整
        if base and tgt_b is not None:
            val_s = sum(shares[i] * Cf[t - 1, i] for i in np.where(held)[0])
            cur_b = sb * C50[t - 1]
            eqo = cash + val_s + cur_b
            want = tgt_b * eqo
            diff = want - cur_b
            if abs(diff) > 0.05 * eqo:
                if diff > 0:
                    amt = min(diff, cash)
                    px = O50[t] * (1 + SLIP)
                    sb += amt / (px * (1 + FEE)); cash -= amt
                else:
                    sell_sleeve(-diff, O50[t])
            tgt_b = None
        # --- 收盤市值
        val_s = 0.0
        for i in np.where(held)[0]:
            val_s += shares[i] * Cf[t, i]
            if np.isfinite(L[t, i]):
                mae[i] = min(mae[i], L[t, i] / epx[i] - 1)
        eq[t] = cash + val_s + sb * C50[t]
        stk_frac[t] = val_s / eq[t]; tot_frac[t] = (val_s + sb * C50[t]) / eq[t]
        if t == t1:
            break
        # --- 收盤後：產生訊號（隔日開盤執行）
        s = score[t]
        Lw = 1.0 if s >= thr_f else (0.5 if s >= thr_h else 0.0)
        if not use1:
            Lw = 1.0
        allowed = SLOTS if Lw == 1.0 else (SLOTS // 2 if Lw == 0.5 else 0)
        g_t = gs[t]
        top = np.zeros(g_t.shape[0], bool); keepm = np.zeros_like(top)
        if use2 and np.isfinite(g_t).any():
            order = np.argsort(-np.nan_to_num(g_t, nan=-1))
            top[order[:topk]] = True; keepm[order[:keepk]] = True
        for i in np.where(held)[0]:
            if i in pend_out:
                continue
            c = Cf[t, i]; a = atr[t, i]
            if np.isfinite(a):
                stop[i] = max(stop[i], c - STOP_ATR * a)
            why = None
            if use1 and s < thr_h:
                why = "大盤分數跌破%.0f分（空手）" % thr_h
            elif use2 and force_g and not (mem[i] * keepm).any():
                why = "族群掉出前%d名" % keepk
            elif ex[t, i]:
                why = "技術出場(%s)" % cfg["entry"]
            if why:
                pend_out[i] = why
        n_hold = int(sum(1 for i in np.where(held)[0] if i not in pend_out))
        room = allowed - n_hold
        planned = []
        if room > 0:
            cand = np.where(ent[t] & vc[t] & ~held & np.isfinite(O[t + 1]) & np.isfinite(atr[t]))[0]
            if use2 and len(cand):
                sc = (mem[cand] * (top * np.nan_to_num(g_t, nan=0))[None, :]).max(axis=1)
                ok = sc > 0
                cand, sc = cand[ok], sc[ok]
            else:
                sc = np.zeros(len(cand))
            rs20 = M["stock_rs"][t, cand] if len(cand) else np.array([])
            order = np.lexsort((-np.nan_to_num(rs20, nan=-9), -sc)) if len(cand) else []
            sel = [cand[k] for k in order[:room]]
            n_after = n_hold + len(sel)
            for k, i in zip(order[:room], sel):
                if sizing == "scale":
                    w = min(WMAX, Lw / max(n_after, 4))
                else:
                    w = 1.0 / SLOTS
                pend_in[i] = dict(sig_t=t, l1=s, w=w, atr=float(atr[t, i]), stop=float(Cf[t, i] - STOP_ATR * atr[t, i]),
                                  grp_score=float(sc[k]) if use2 else np.nan,
                                  stock_rs20=float(rs20[k]) if np.isfinite(rs20[k]) else np.nan)
                planned.append(w)
        if base:
            keep_val = sum(shares[i] * Cf[t, i] for i in np.where(held)[0] if i not in pend_out)
            tgt_b = max(0.0, Lw - (keep_val / eq[t] + sum(planned)))
    e = pd.Series(eq, index=idx).iloc[t0:t1 + 1]
    tr = pd.DataFrame(trades)
    if len(tr):
        tr["entry"] = idx[tr["entry_i"]]; tr["exit"] = idx[tr["exit_i"]]
        tr["hold_days"] = (tr["exit"] - tr["entry"]).dt.days
    M["_info"] = info
    return e, tr, pd.Series(stk_frac, index=idx).iloc[t0:t1 + 1], pd.Series(tot_frac, index=idx).iloc[t0:t1 + 1]


# ------------------------------------------------------------------ 基準與淘汰
def bh0050(M, a, b=None):
    """同窗、同成本、含息的 0050 買進持有：窗首開盤買（手續費+滑價），窗尾收盤賣（手續費+ETF 稅+滑價）。"""
    idx = M["idx"]
    i0 = idx.searchsorted(pd.Timestamp(a)); i1 = (idx.searchsorted(pd.Timestamp(b)) - 1) if b else len(idx) - 1
    o, c = M["O50"], M["C50"]
    r = pd.Series(c[i0:i1 + 1], index=idx[i0:i1 + 1]).pct_change()
    r.iloc[0] = c[i0] / (o[i0] * (1 + SLIP)) / (1 + FEE) - 1
    r.iloc[-1] = (1 + r.iloc[-1]) * (1 - SLIP) * (1 - FEE - ETF_TAX) - 1
    return r


def seg_stats(eq: pd.Series, a, b=None):
    s = eq[(eq.index >= a) & ((eq.index < b) if b else True)]
    return stats(s.pct_change().dropna(), 245)


def verdict(strat_cagr, bench_cagr):
    return "通過" if strat_cagr >= bench_cagr else "淘汰，不使用"


# ------------------------------------------------------------------ 組裝
def build3():
    p, C_all, frames, codes = load3()
    idx = frames["0050"].index[frames["0050"].index >= "2020-06-01"]
    set_calendar(idx)
    f = T2.layer1(frames, C_all, p).reindex(idx)
    mems = membership_modes(codes)
    def mat(col):
        return pd.DataFrame({c: frames[c][col] for c in codes}).reindex(idx)
    O, H, L, C = (mat(k) for k in ("open", "high", "low", "close"))
    Cf = C.ffill()
    mkt = Cf.pct_change().mean(axis=1)
    mkt20 = (1 + mkt).rolling(20).apply(np.prod, raw=True) - 1
    stock_rs = (Cf / Cf.shift(20) - 1).sub(mkt20, axis=0).to_numpy()
    sigs = {e: T2.stock_signals(frames, codes, idx, e) for e in ("ST", "MA", "DC")}
    f50 = frames["0050"].reindex(idx)
    M = dict(idx=idx, codes=codes, O=O.to_numpy(), H=H.to_numpy(), L=L.to_numpy(), C=C.to_numpy(), Cf=Cf.to_numpy(),
             f=f, sig=sigs, stock_rs=stock_rs, O50=f50["open"].ffill().to_numpy(), C50=f50["close"].ffill().to_numpy(),
             c50=f50["close"].ffill(), modes={}, frames=frames)
    ci = {c: i for i, c in enumerate(codes)}
    for mode, (mdf, gnames) in mems.items():
        G = T2.layer2(frames, codes, mdf.rename(columns={"group_id": "group_id"}), gnames, idx)
        mm = np.zeros((len(codes), len(G["gids"])), bool)
        for j, gid in enumerate(G["gids"]):
            for c in G["members"][gid]:
                mm[ci[c], j] = True
        M["modes"][mode] = dict(G=G, mem_mat=mm)
    return M


def l2_corr(G, idx, a, b):
    from pandas import DataFrame as DF
    comps = {"相對強度": G["rs"], "法人買超": G["inst"], "成交比重上升": G["share"],
             "營收動能": np.clip(np.nan_to_num(G["rev"]) / 0.30, 0, 1)}
    msk = (idx >= a) & (idx < b)
    R = {k: DF(v, index=idx)[msk].rank(axis=1, pct=True) for k, v in comps.items()}
    ks = list(comps)
    out = pd.DataFrame(index=ks, columns=ks, dtype=float)
    for x in ks:
        for y in ks:
            out.loc[x, y] = R[x].corrwith(R[y], axis=1).mean()
    return out


def fit_items(M, mode, train_end, a=T_START, rule="direction"):
    """只用 [a, train_end) 的資料決定保留哪些子項（大盤與族群各一組），回傳 (L1 保留, L2 保留, 檢驗表)。"""
    idx = M["idx"]
    t1 = l1_item_tests(M["f"], M["c50"], pd.Timestamp(a), pd.Timestamp(train_end))
    msk = (idx >= pd.Timestamp(a)) & (idx < pd.Timestamp(train_end))
    c1 = M["f"][[c for c in M["f"].columns if c != "總分"]][msk].corr(method="spearman")
    keep1, t1 = decide_keep(t1, c1, rule)
    G = M["modes"][mode]["G"]
    t2 = l2_item_tests(G, idx, pd.Timestamp(a), pd.Timestamp(train_end))
    keep2, t2 = decide_keep(t2, l2_corr(G, idx, pd.Timestamp(a), pd.Timestamp(train_end)), rule)
    return keep1, keep2, pd.concat([t1, t2], ignore_index=True)


def apply_items(M, mode, keep1, keep2):
    M["score"] = l1_score(M["f"], keep1) if keep1 else pd.Series(0.0, index=M["idx"])
    G = M["modes"][mode]["G"]
    raw, sm = l2_score(G, M["idx"], keep2) if keep2 else (np.full_like(G["rs"], np.nan), np.full_like(G["rs"], np.nan))
    M["gscore"] = sm
    M["g_raw_score"] = raw
    M["mem_mat"] = M["modes"][mode]["mem_mat"]
    M["_G"] = G
    M["_gnames"] = G["names"]


def run_cfg(M, cfg, t_lo=None, t_hi=None):
    e, tr, sf, tf = simulate3(M, cfg, t_lo, t_hi)
    return dict(eq=e, tr=tr, stk=sf, tot=tf, cfg=cfg, info=dict(M.get("_info", {})))


def metrics3(r, a, b=None):
    eq, tr = r["eq"], r["tr"]
    seg = eq[(eq.index >= a) & ((eq.index < b) if b else True)]
    s = stats(seg.pct_change().dropna(), 245)
    t = tr[(tr["entry"] >= a) & ((tr["entry"] < b) if b else True)] if len(tr) else tr
    n = len(t)
    w = t.loc[t["ret"] > 0, "ret"].mean() if n else np.nan
    l = -t.loc[t["ret"] <= 0, "ret"].mean() if n else np.nan
    msk = (r["stk"].index >= a) & ((r["stk"].index < b) if b else True)
    return dict(cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], n=n, win=(t["ret"] > 0).mean() if n else np.nan,
                payoff=(w / l if l and l > 0 else np.nan), hold=t["hold_days"].mean() if n else np.nan,
                stock_expo=r["stk"][msk].mean(), total_expo=r["tot"][msk].mean())


def build_log3(r, M):
    tr, info, idx, codes = r["tr"], r["info"], M["idx"], M["codes"]
    G = M["_G"]; f = M["f"]
    rows = []
    for _, x in tr.iterrows():
        i = codes.index(x["code"])
        inf = info.get((i, int(x["entry_i"])), {})
        st = int(inf.get("sig_t", x["entry_i"] - 1))
        gs = M["gscore"][st]
        top = np.argsort(-np.nan_to_num(gs, nan=-1))[:r["cfg"].get("topk", 5)]
        mine = [j for j in top if M["mem_mat"][i, j]] if r["cfg"].get("use_l2", True) else []
        j = max(mine, key=lambda k: gs[k]) if mine else None
        row = dict(代號=x["code"], 訊號日=idx[st].date(), 進場日=x["entry"].date(), 進場價=round(x["entry_px"], 2),
                   出場日=x["exit"].date(), 出場價=round(x["exit_px"], 2), 報酬率=round(x["ret"], 4), 持有天數=int(x["hold_days"]),
                   最大不利偏移=round(x["mae"], 4), 出場原因=x["exit_reason"], 進場部位占權益=round(inf.get("w", np.nan), 3),
                   初始停損價=round(inf.get("stop", np.nan), 2), 進場時大盤總分=round(float(M["score"].iloc[st]), 2))
        for k in r["cfg"].get("_l1_keep", []):
            row["大盤子項_" + k] = round(float(f[k].iloc[st]), 2)
        if j is not None:
            row.update(入選族群=G["names"][j], 族群分數_平滑=round(float(gs[j]), 2),
                       族群_相對強度20日=round(float(G["rs"][st, j]), 4), 族群_法人買超佔成交值5日=round(float(G["inst"][st, j]), 4),
                       族群_成交比重5比20日=round(float(G["share"][st, j]), 3),
                       族群_營收年增中位數=round(float(G["rev"][st, j]), 3) if np.isfinite(G["rev"][st, j]) else np.nan)
        row["個股訊號"] = f"{r['cfg']['entry']} 進場 + 量>{T2.VOL_MULT}倍20日均量"
        row["個股20日相對強度"] = round(inf.get("stock_rs20", np.nan), 4)
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 主流程
WF_FOLDS = [("2023-01-01", "2023-12-31"), ("2024-01-01", "2024-12-31"),
            ("2025-01-01", "2025-12-31"), ("2026-01-01", None)]


def seg_row(name, r, M, group, extra=None):
    row = dict(策略=name, 類別=group)
    for lab, a, b in (("全期", T_START, None), ("樣本內", T_START, SPLIT), ("樣本外", SPLIT, None)):
        m = metrics3(r, pd.Timestamp(a), pd.Timestamp(b) if b else None)
        bh = stats(bh0050(M, a, b).dropna(), 245)
        for k, v in m.items():
            row[f"{lab}_{k}"] = v
        row[f"{lab}_0050年化"] = bh["cagr"]; row[f"{lab}_0050回撤"] = bh["mdd"]; row[f"{lab}_0050夏普"] = bh["sharpe"]
    row["樣本外_差距"] = row["樣本外_cagr"] - row["樣本外_0050年化"]
    row["判定"] = verdict(row["樣本外_cagr"], row["樣本外_0050年化"])
    if extra:
        row.update(extra)
    return row


def main3():
    OUT.mkdir(parents=True, exist_ok=True)
    M = build3()
    idx = M["idx"]
    t_start = idx.searchsorted(pd.Timestamp(T_START))
    # ---- 1. 子項預測力（樣本內）
    keep1, keep2, tests = fit_items(M, "first", SPLIT)
    tests.to_csv(OUT / "subitem_tests.csv", index=False, encoding="utf-8-sig")
    keeps = {"first": (keep1, keep2)}
    for md in ("industry", "latest"):
        k1, k2, _ = fit_items(M, md, SPLIT)
        keeps[md] = (k1, k2)
    print("保留 L1:", keep1, "L2(first):", keep2, "L2(industry):", keeps["industry"][1], "L2(latest):", keeps["latest"][1])
    rows, runs = [], {}

    def go(name, group, mode, cfg, extra=None):
        apply_items(M, mode, *keeps[mode])
        cfg = dict(cfg); cfg["_l1_keep"] = keeps[mode][0]
        note = ""
        if cfg.get("use_l2") and not keeps[mode][1]:
            cfg["use_l2"] = False; note = "該族群版本在樣本內沒有任何族群子項通過 -> 第二層關閉（等同無族群）"
        if cfg.get("use_l1") and not keeps[mode][0]:
            cfg["use_l1"] = False; note += "；大盤子項全未通過 -> 第一層關閉"
        extra = dict(extra or {}, 備註=note)
        r = run_cfg(M, cfg)
        r["log"] = None
        runs[name] = r
        rows.append(seg_row(name, r, M, group, dict(族群版本=mode, **extra)))
        return r

    base = dict(entry="ST", sizing="equal", base=False)
    # ---- 7. 消融（主：git 最早版族群）
    go("A 只用第三層", "消融", "first", dict(base, use_l1=False, use_l2=False))
    go("B 第三層+第二層", "消融", "first", dict(base, use_l1=False, use_l2=True))
    go("C 第三層+第一層", "消融", "first", dict(base, use_l1=True, use_l2=False))
    go("D 三層全開", "消融", "first", dict(base, use_l1=True, use_l2=True))
    # ---- 3. 資金使用率
    for nm, sz, bs in (("放大權重 scale", "scale", False), ("0050底倉 base", "equal", True), ("兩者 both", "scale", True)):
        go(f"D + {nm}", "資金使用率", "first", dict(base, use_l1=True, use_l2=True, sizing=sz, base=bs))
        go(f"C + {nm}", "資金使用率", "first", dict(base, use_l1=True, use_l2=False, sizing=sz, base=bs))
    go("B + 0050底倉（無大盤分數，永遠滿檔）", "資金使用率", "first", dict(base, use_l1=False, use_l2=True, base=True))
    # ---- 5. 族群版本
    for md in ("industry", "latest"):
        go(f"D（族群版本={md}）", "族群版本", md, dict(base, use_l1=True, use_l2=True))
        go(f"B（族群版本={md}）", "族群版本", md, dict(base, use_l1=False, use_l2=True))
    # ---- 進場訊號對照
    for e in ("MA", "DC"):
        go(f"D（進場訊號={e}）", "進場訊號", "first", dict(base, entry=e, use_l1=True, use_l2=True))
    # ---- 第二輪 D 在含息價上重跑（舊規則：舊分數、舊族群、-8% 硬停損、掉出前 10 強制出場）
    M2 = dict(M, g=M["modes"]["latest"]["G"], score=M["f"]["總分"], mem_mat=M["modes"]["latest"]["mem_mat"], info={}, C=M["C"])
    T2.GROUP_TOPK, T2.GROUP_KEEP = 5, 10
    e2, tr2, ex2 = T2.simulate(M2, dict(entry="ST", use_l1=True, use_l2=True))
    r2 = dict(eq=e2, tr=tr2, stk=ex2.reindex(e2.index), tot=ex2.reindex(e2.index), cfg=dict(entry="ST"))
    runs["第二輪D（含息價重跑）"] = r2
    rows.append(seg_row("第二輪D（含息價重跑）", r2, M, "對照", dict(族群版本="latest")))
    res = pd.DataFrame(rows)
    # ---- 6. walk-forward
    wf_rows, chain = [], []
    for k, (ts, te) in enumerate(WF_FOLDS):
        k1, k2, _ = fit_items(M, "first", ts)
        apply_items(M, "first", k1, k2)
        t_tr_end = idx.searchsorted(pd.Timestamp(ts)) - 1
        best = None
        for e in ("ST", "MA", "DC"):
            for sz, bs in (("equal", False), ("scale", False), ("equal", True)):
                cfg = dict(entry=e, sizing=sz, base=bs, use_l1=True, use_l2=True)
                r = run_cfg(M, cfg, t_start, t_tr_end)
                s = stats(r["eq"].pct_change().dropna(), 245)["sharpe"]
                if best is None or (np.nan_to_num(s, nan=-9) > best[0]):
                    best = (np.nan_to_num(s, nan=-9), cfg)
        cfg = best[1]
        t_lo = idx.searchsorted(pd.Timestamp(ts))
        t_hi = (idx.searchsorted(pd.Timestamp(te), side="right") - 1) if te else len(idx) - 1
        r = run_cfg(M, cfg, t_lo, t_hi)
        a = idx[t_lo]; b = idx[t_hi]
        yrs = max((b - a).days / 365.25, 1e-9)
        sg = stats(r["eq"].pct_change().dropna(), 245)
        bh = stats(bh0050(M, a, (b + pd.Timedelta(days=1))).dropna(), 245)
        # 區段太短時年化會失真，另列區間總報酬
        tot = r["eq"].iloc[-1] / 1.0 - 1
        bhtot = (1 + bh0050(M, a, (b + pd.Timedelta(days=1))).dropna()).prod() - 1
        wf_rows.append(dict(段=f"測試 {a.date()}~{b.date()}", 訓練止=ts, 保留大盤子項=",".join(k1), 保留族群子項=",".join(k2),
                            選到的進場=cfg["entry"], 選到的部位法=("0050底倉" if cfg["base"] else cfg["sizing"]),
                            訓練期夏普=round(best[0], 2), 區間報酬=tot, 同窗0050區間報酬=bhtot, 年化=sg["cagr"], 同窗0050年化=bh["cagr"],
                            最大回撤=sg["mdd"], 夏普=sg["sharpe"], 同窗0050回撤=bh["mdd"], 交易數=len(r["tr"]),
                            贏大盤=bool(tot >= bhtot)))
        chain.append(r["eq"] / r["eq"].iloc[0] * (chain[-1].iloc[-1] if chain else 1.0))
    wf = pd.DataFrame(wf_rows)
    wf.to_csv(OUT / "wf_results.csv", index=False, encoding="utf-8-sig")
    wfeq = pd.concat(chain)
    wins, tot_n = int(wf["贏大盤"].sum()), len(wf)
    wf_cagr = stats(wfeq.pct_change().dropna(), 245)
    bh_wf = stats(bh0050(M, wfeq.index[0], wfeq.index[-1] + pd.Timedelta(days=1)).dropna(), 245)
    wf_sum = dict(策略="Walk-forward（四段串接）", 類別="walk-forward", 樣本外_cagr=wf_cagr["cagr"], 樣本外_mdd=wf_cagr["mdd"],
                  樣本外_sharpe=wf_cagr["sharpe"], 樣本外_0050年化=bh_wf["cagr"], 樣本外_差距=wf_cagr["cagr"] - bh_wf["cagr"],
                  判定=verdict(wf_cagr["cagr"], bh_wf["cagr"]), 族群版本="first", 贏大盤段數=f"{wins}/{tot_n}")
    res = pd.concat([res, pd.DataFrame([wf_sum])], ignore_index=True)
    res.to_csv(OUT / "ablation_results.csv", index=False, encoding="utf-8-sig")
    # ---- 輸出：日誌、每日分數、權益曲線、基準
    apply_items(M, "first", *keeps["first"])
    main_r = runs["D 三層全開"]
    pd.DataFrame(build_log3(main_r, M)).to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    build_log3(runs["A 只用第三層"], M).to_csv(OUT / "trades_L3_only.csv", index=False, encoding="utf-8-sig")
    daily = M["f"].copy().iloc[t_start:]
    daily["新大盤分數"] = M["score"].iloc[t_start:]
    daily["舊大盤總分_第二輪"] = daily.pop("總分")
    daily["持股水位"] = np.where(daily["新大盤分數"] >= THR_FULL, "滿檔", np.where(daily["新大盤分數"] >= THR_HALF, "半檔", "空手"))
    daily.round(3).to_csv(OUT / "daily_score.csv", encoding="utf-8-sig", index_label="date")
    eqs = {k: v["eq"] for k, v in runs.items()}
    bh_full = (1 + bh0050(M, T_START)).cumprod()
    pd.DataFrame(eqs).join(bh_full.rename("0050買進持有(含息含成本)")).join(wfeq.rename("walk-forward")).to_csv(
        OUT / "equity_curves.csv", encoding="utf-8-sig", index_label="date")
    pd.to_pickle(dict(keeps=keeps, runs={k: {"eq": v["eq"], "tr": v["tr"]} for k, v in runs.items()}), OUT / "_runs.pkl")
    pd.set_option("display.width", 250)
    show = res[["策略", "類別", "樣本內_cagr", "樣本外_cagr", "樣本外_0050年化", "樣本外_差距", "樣本外_mdd", "樣本外_sharpe", "樣本外_n", "樣本外_stock_expo", "樣本外_total_expo", "判定"]]
    print(show.round(3).to_string())
    print(wf.round(3).to_string())
    return M, res, wf, tests, keeps


if __name__ == "__main__":
    main3()


# ------------------------------------------------------------------ 前向模擬盤：每日出訊號（不接排程、不下單）
def paper_gate(elim: pd.DataFrame, name: str):
    """淘汰規則的閘門：樣本外年化輸 0050 的策略一律不准進前向模擬盤。"""
    row = elim[elim["策略"] == name]
    if row.empty:
        return False, f"找不到策略 {name} 的回測判定，視同未通過"
    v = row.iloc[0]["判定"]
    return (v == "通過"), f"{name} 的判定為「{v}」"


def paper_signals(name: str = "D + 兩者 both", cfg: dict | None = None, mode: str = "first"):
    """用資料湖最新一天收盤後的資料，產生「明天開盤」的建議清單：大盤分數／水位、入選族群、進場候選（含停損價）。
    只讀資料湖、不記帳、不下單。若該策略在 ablation_results.csv 的判定是淘汰，直接回傳 allowed=False。"""
    elim = pd.read_csv(OUT / "ablation_results.csv")
    ok, why = paper_gate(elim, name)
    if not ok:
        return dict(allowed=False, reason=why + "；依 Andy 規則「低於大盤就不要使用」，不出訊號。")
    M = build3()
    keep1, keep2, _ = fit_items(M, mode, SPLIT)
    apply_items(M, mode, keep1, keep2)
    cfg = cfg or dict(entry="ST", sizing="scale", base=True, use_l1=True, use_l2=True)
    t = len(M["idx"]) - 1
    ent, ex, vc, atr = M["sig"][cfg["entry"]]
    s = float(M["score"].iloc[t])
    lvl = "滿檔" if s >= THR_FULL else ("半檔" if s >= THR_HALF else "空手")
    gs = M["gscore"][t]
    top = np.argsort(-np.nan_to_num(gs, nan=-1))[:cfg.get("topk", 5)]
    cands = []
    for i in np.where(ent[t] & vc[t])[0]:
        mine = [j for j in top if M["mem_mat"][i, j]]
        if mine or not cfg.get("use_l2", True):
            cands.append(dict(代號=M["codes"][i], 收盤=float(M["Cf"][t, i]),
                              初始停損=float(M["Cf"][t, i] - STOP_ATR * atr[t, i]),
                              族群=M["modes"][mode]["G"]["names"][max(mine, key=lambda k: gs[k])] if mine else ""))
    return dict(allowed=True, asof=str(M["idx"][t].date()), 大盤分數=round(s, 2), 水位=lvl,
                入選族群=[M["modes"][mode]["G"]["names"][j] for j in top], 進場候選=cands)
