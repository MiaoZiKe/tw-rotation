"""第九輪：大型股增強指數——以「前 50 大市值」代理 0050，按市值權重持有，再用營收動能／近 52 週新高做小幅傾斜。

為什麼這樣做：前八輪證明「挑少數股票」在大型股池（前 100）贏不了 0050。本輪改成不挑股、只傾斜：
追蹤誤差小，對多重比較與存活者偏誤比較不敏感。純個股，不持有 0050 或任何 ETF；0050 只當比較基準（含息還原價）。

0050 成分歷史不足（etf_holdings 只有 2026-10-07 之後），所以用「前 50 大市值」代理：
  市值 = 未還原收盤價 x 財報股數（factor_lab 的 mcap，財報法定可用日才生效，無前視）。
  2013-04-01 之前沒有股數資料（2012Q4 財報法定可用日 3/31），所以訓練窗從 2013-05-02 起（第一個訊號 2013-04-30），不是 2013-01。
  2013～2015 市值有值的只有約 374～406 檔（回補名單），前 50 大都在內，但名單本身有事後選股痕跡（見 README 限制）。
  2026-10-22 驗證：代理前 50 與 0050 實際成分重疊 45 檔，權重相關 0.999（台積電代理 51% vs 實際 57%）。

訊號收盤後產生、隔日開盤成交；每月最後一個交易日調整一次（營收法定可用日是次月 10 日，月底已可用）。
成本：手續費 0.1425% x 買賣、證交稅 0.3%（賣）、滑價 0.1%/邊，只對「實際成交的差額」收；窗尾平倉也收，與 0050 基準的進出成本對稱。
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

OUT = ROOT / "docs" / "strategy_lab" / "round9"
TRAIN = ("2013-05-02", "2018-12-31")
W_SEEN1 = ("2019-01-02", "2022-12-30")     # 前幾輪已看過（標示，不是乾淨證據）
W_SEEN2 = ("2023-01-02", "2026-10-22")     # 前幾輪已看過
PRIOR_TRIALS = 1766
TOPN = 50
NW_LAG = 10
ETF_TAX = 0.001
SIGNALS = ("both", "rev", "nh")
TILTS = ("m15_05", "m125_075", "ex10", "ex20", "ex20_up15", "lin3", "lin6", "bin_up15")
TSMC = ("actual", "cap20")
# 9b 家族：換成別的訊號來傾斜（名稱 -> (特徵表, 特徵鍵, 方向))；方向 -1 = 越小越好
SIG9B = {"mom": ("f", "mom126", 1), "rsmom": ("f", "rsmom", 1), "roe": ("ff", "roe", 1), "dy": ("ff", "dy3", 1), "ep": ("ff", "ep", 1),
         "bp": ("ff", "bp", 1), "lowvol": ("ff", "vol", -1), "sue": ("ff", "sue", 1)}
TILTS_9B = ("m15_05", "ex10", "lin3")
ALLSIG = dict(SIG9B, rev=("ff", "rv312", 1), nh=("f", "nh", 1))
PAIRS_9C = ("roe+nh", "roe+rev", "roe+lowvol", "roe+ep", "nh+lowvol", "ep+nh")


def load_P():
    """載入資料；環境變數 IL9_CACHE 指向 pickle 時可跳過 90 秒的特徵計算（只是開發加速，結果相同）。"""
    import os
    import pickle
    cp = os.environ.get("IL9_CACHE")
    if cp and Path(cp).exists():
        return pickle.load(open(cp, "rb"))
    from pipeline.compute import factor_lab as FL
    P = FL.load_all()
    P["is_etf"] = np.array([c.startswith("00") for c in P["cols"]])
    if cp:
        keep = {k: P[k] for k in ("idx", "cols", "ci", "O", "Cf", "rawC", "c50", "o50", "is_etf")}
        keep["ff"] = {k: P["ff"][k] for k in ("mcap", "rv312", "roe", "dy3", "ep", "bp", "vol", "sue")}
        keep["f"] = {k: P["f"][k] for k in ("nh", "mom126", "rsmom")}
        pickle.dump(keep, open(cp, "wb"))
        return keep
    return P


# ------------------------------------------------------------------ 權重
def _cap(w, c):
    """單檔上限 c：超出的部分按比例分給其他檔，迭代到收斂。"""
    w = w.copy()
    for _ in range(50):
        over = w > c + 1e-12
        if not over.any():
            break
        ex = (w[over] - c).sum()
        w[over] = c
        free = ~over & (w > 0)
        w[free] += ex * w[free] / w[free].sum()
    return w


def target_weights(P, s, cfg):
    """s 日收盤後的目標權重（欄位向量）。cfg = (signal, tilt, tsmc)；tilt=None 是純市值加權。"""
    sig, tilt, tsmc = cfg
    mc = P["ff"]["mcap"][s].copy()
    ok = np.isfinite(mc) & (mc > 0) & ~P["is_etf"] & np.isfinite(P["O"][s + 1])
    m = np.where(ok, mc, np.nan)
    top = np.argsort(-np.nan_to_num(m, nan=-1))[:TOPN]
    top = top[np.isfinite(m[top])]
    w0 = m[top] / m[top].sum()
    mult = np.ones(len(top))
    if tilt is not None:
        rv, nh = P["ff"]["rv312"][s][top], P["f"]["nh"][s][top]

        def pct(x):                                   # 池內百分位，缺值給中性 0.5
            r = pd.Series(x).rank(pct=True).to_numpy()
            return np.where(np.isfinite(x), r, 0.5)
        if "+" in sig:                                 # 9c：兩個訊號的百分位平均
            parts = []
            for nm in sig.split("+"):
                tb, key, sg = ALLSIG[nm]
                parts.append(pct(P[tb][key][s][top] * sg))
            sc = np.mean(parts, axis=0)
        elif sig in SIG9B:
            tb, key, sg = SIG9B[sig]
            x = P[tb][key][s][top] * sg
            sc = pct(x)
        else:
            sc = {"both": (pct(rv) + pct(nh)) / 2, "rev": pct(rv), "nh": pct(nh)}[sig]
        order = np.argsort(sc, kind="stable")          # 由弱到強
        n = len(top)
        k3 = n // 3
        if tilt in ("m15_05", "m125_075"):
            up, dn = (1.5, 0.5) if tilt == "m15_05" else (1.25, 0.75)
            mult[order[-k3:]] = up
            mult[order[:k3]] = dn
        elif tilt in ("ex10", "ex20", "ex20_up15"):
            kx = int(round(n * (0.10 if tilt == "ex10" else 0.20)))
            mult[order[:kx]] = 0.0
            if tilt == "ex20_up15":
                mult[order[-k3:]] = 1.5
        elif tilt in ("lin3", "lin6"):
            kk = 0.3 if tilt == "lin3" else 0.6
            mult = 1 + kk * (sc - 0.5) * 2
        elif tilt == "bin_up15":
            strong = {"both": (rv > 1) & (nh >= 0.85), "rev": rv > 1, "nh": nh >= 0.85}[sig]
            mult = np.where(strong, 1.5, 1.0)
    w = w0 * mult
    w = w / w.sum()
    if tsmc == "cap20":
        w = _cap(w, 0.20)
    out = np.zeros(len(mc))
    out[top] = w
    return out


# ------------------------------------------------------------------ 引擎
def month_ends(idx, lo_i, hi_i):
    s = pd.Series(np.arange(len(idx)), index=idx)
    last = s.groupby(idx.to_period("M")).max().to_numpy()
    return [i for i in last if lo_i <= i + 1 and i + 1 <= hi_i]


def run(P, cfg, lo, hi):
    """回傳日權益（收盤）、換手率。cfg=(signal,tilt,tsmc)；訊號 s 收盤 → s+1 開盤成交。"""
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo))
    hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O = np.where(np.isfinite(P["O"]) & (P["O"] > 0), P["O"], np.nan)
    Cf = np.where(np.isfinite(P["Cf"]) & (P["Cf"] > 0), P["Cf"], 0.0)       # 沒上市／無價 = 0，避免 0*NaN 污染
    sigs = [lo_i - 1] + [i for i in month_ends(idx, lo_i, hi_i) if i >= lo_i]
    sigs = sorted(set(sigs))
    sh = np.zeros(O.shape[1])
    eq = np.full(len(idx), np.nan)
    cash = 1.0
    turn = 0.0
    nxt = {s + 1: s for s in sigs if s + 1 <= hi_i}
    for t in range(lo_i, hi_i + 1):
        if t in nxt:
            s = nxt[t]
            tw = target_weights(P, s, cfg)
            px = np.where(np.isfinite(O[t]), O[t], Cf[t - 1])
            px = np.where(px > 0, px, 1.0)
            val = float((sh * px).sum()) + cash
            tgt = tw * val
            cur = sh * px
            d = tgt - cur
            buy, sell = d[d > 0].sum(), -d[d < 0].sum()
            cost = buy * (FEE + SLIP) + sell * (FEE + TAX + SLIP)
            turn += (buy + sell) / 2 / val
            scale = 1 - cost / val                       # 成本直接從總值扣，按比例縮小目標部位
            sh = tgt * scale / px
            cash = 0.0
        eq[t] = float((sh * Cf[t]).sum()) + cash
    e = pd.Series(eq[lo_i:hi_i + 1], index=idx[lo_i:hi_i + 1])
    e.iloc[-1] *= (1 - FEE - TAX - SLIP)                  # 窗尾平倉成本，與 0050 基準對稱
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return e, turn / max(yrs, 0.1)


def bench_eq(P, lo, hi):
    idx = P["idx"]
    i0, i1 = idx.searchsorted(pd.Timestamp(lo)), idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    c = P["c50"].iloc[i0:i1 + 1]
    eq = c / P["o50"].iloc[i0] / (1 + SLIP) / (1 + FEE)
    eq.iloc[-1] *= (1 - SLIP) * (1 - FEE - ETF_TAX)
    return eq


def nw_t(x, lag=NW_LAG):
    """Newey-West（Bartlett 核）修正的 t 值：檢定日主動報酬平均 = 0。"""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    xm = x - x.mean()
    g0 = (xm * xm).sum() / n
    v = g0
    for L in range(1, lag + 1):
        v += 2 * (1 - L / (lag + 1)) * (xm[L:] * xm[:-L]).sum() / n
    se = np.sqrt(max(v, 1e-30) / n)
    return float(x.mean() / se)


def metrics(P, cfg, lo, hi):
    e, turn = run(P, cfg, lo, hi)
    b = bench_eq(P, lo, hi)
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    bc = b.iloc[-1] ** (1 / yrs) - 1
    r = e.pct_change().dropna()
    rb = P["c50"].reindex(e.index).pct_change().dropna()          # 日主動報酬用不含進出成本的 0050 還原價
    act = (r - rb.reindex(r.index)).dropna()
    te = act.std() * np.sqrt(245)
    ir = act.mean() * 245 / te if te > 0 else np.nan
    mdd = (e / e.cummax() - 1).min()
    bmdd = (b / b.cummax() - 1).min()
    ye = e.groupby(e.index.year).last(); yb = b.groupby(b.index.year).last()
    yr_s = (ye / ye.shift(1).fillna(1.0) - 1); yr_b = (yb / yb.shift(1).fillna(1.0) - 1)
    return dict(cagr=cagr, bh=bc, excess=cagr - bc, mdd=mdd, bh_mdd=bmdd, te=te, ir=ir, nw_t=nw_t(act.to_numpy()),
                act_ann=act.mean() * 245, turn=turn, ywin=int((yr_s > yr_b).sum()), ynum=len(yr_s), years=yrs)


def cfg_name(cfg):
    sig, tilt, tsmc = cfg
    tag = "照實" if tsmc == "actual" else "上限20%"
    return f"純市值加權｜台積電{tag}" if tilt is None else f"{sig}｜{tilt}｜台積電{tag}"


def all_cfgs():
    out = [(("both", None, t)) for t in TSMC]
    out += [(s, tl, t) for s in SIGNALS for tl in TILTS for t in TSMC]
    return out


def jc(cfg):
    return json.dumps(list(cfg), ensure_ascii=False)


# ------------------------------------------------------------------ 階段
def stage_train(P):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for cfg in all_cfgs():
        rows.append(dict(名稱=cfg_name(cfg), cfg=jc(cfg), **metrics(P, cfg, *TRAIN)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "registry_train.csv", index=False)
    return df


def stage_freeze(df, k=6):
    """事先定的規則：訓練期超額 > 0 且 NW t > 0 的傾斜候選，取資訊比前 k；純市值加權兩個一律當對照一起凍結。"""
    frozen_path = OUT / "frozen_candidates.json"
    if frozen_path.exists():
        return json.loads(frozen_path.read_text())
    tl = df[~df["名稱"].str.startswith("純市值")]
    ok = tl[(tl.excess > 0) & (tl.nw_t > 0)].sort_values("ir", ascending=False).head(k)
    base = df[df["名稱"].str.startswith("純市值")]
    sel = pd.concat([ok, base])
    d = dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), rule=f"訓練期 excess>0 且 NW t>0，依資訊比取前{k}；純市值加權當對照",
             trials_total=PRIOR_TRIALS + len(df), cands=[dict(name=r["名稱"], cfg=json.loads(r["cfg"])) for _, r in sel.iterrows()])
    frozen_path.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return d


def stage_reveal(P, frozen):
    """凍結後一次揭露：兩個已被看過的窗口。只寫一次。"""
    path = OUT / "reveal_seen.csv"
    if path.exists():
        return pd.read_csv(path)
    rows = []
    for c in frozen["cands"]:
        cfg = tuple(c["cfg"])
        for wn, w in (("2019-2022（已看過）", W_SEEN1), ("2023-2026（已看過）", W_SEEN2)):
            rows.append(dict(名稱=c["name"], cfg=jc(cfg), 窗口=wn, **metrics(P, cfg, *w)))
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def cfgs_9b():
    return [(sg, tl, "actual") for sg in SIG9B for tl in TILTS_9B]


def cfgs_9c():
    return [(sg, tl, "actual") for sg in PAIRS_9C for tl in TILTS_9B]


def stage_9b(P, tag="9b"):
    """9b：換訊號傾斜。只用訓練期決定凍結；凍結後一次揭露兩個已被看過的窗口。"""
    reg_p, fr_p, rv_p = OUT / f"registry_train_{tag}.csv", OUT / f"frozen_{tag}.json", OUT / f"reveal_{tag}.csv"
    cfgs = cfgs_9b() if tag == "9b" else cfgs_9c()
    prior = PRIOR_TRIALS + len(all_cfgs()) + (0 if tag == "9b" else len(cfgs_9b()))
    if reg_p.exists():
        reg = pd.read_csv(reg_p)
    else:
        reg = pd.DataFrame([dict(名稱=cfg_name(c), cfg=jc(c), **metrics(P, c, *TRAIN)) for c in cfgs])
        reg.to_csv(reg_p, index=False)
    if not fr_p.exists():
        ok = reg[(reg.excess > 0) & (reg.nw_t > 0)].sort_values("ir", ascending=False).head(6)
        fr_p.write_text(json.dumps(dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), rule="訓練期 excess>0 且 NW t>0，依資訊比取前6",
                                        trials_total=prior + len(reg),
                                        cands=[dict(name=r["名稱"], cfg=json.loads(r["cfg"])) for _, r in ok.iterrows()]), ensure_ascii=False, indent=1))
    fr = json.loads(fr_p.read_text())
    if rv_p.exists():
        return reg, pd.read_csv(rv_p)
    rows = []
    for c in fr["cands"]:
        for wn, w in (("2019-2022（已看過）", W_SEEN1), ("2023-2026（已看過）", W_SEEN2)):
            rows.append(dict(名稱=c["name"], cfg=jc(c["cfg"]), 窗口=wn, **metrics(P, tuple(c["cfg"]), *w)))
    rv = pd.DataFrame(rows)
    rv.to_csv(rv_p, index=False)
    return reg, rv


if __name__ == "__main__":
    t0 = time.time()
    P = load_P()
    print("載入", round(time.time() - t0))
    stage = sys.argv[1] if len(sys.argv) > 1 else "train"
    if stage in ("9b", "9c"):
        reg, rv = stage_9b(P, stage)
        print(reg.sort_values("ir", ascending=False)[["名稱", "cagr", "bh", "excess", "te", "ir", "nw_t", "mdd"]].round(3).to_string())
        print(rv.round(3).to_string())
        sys.exit(0)
    tr = stage_train(P)
    print(tr.sort_values("ir", ascending=False)[["名稱", "cagr", "bh", "excess", "te", "ir", "nw_t", "mdd"]].round(3).head(60).to_string())
    if stage in ("freeze", "all"):
        fr = stage_freeze(tr)
        print(json.dumps(fr, ensure_ascii=False)[:600])
    if stage == "all":
        print(stage_reveal(P, fr).round(3).to_string())
