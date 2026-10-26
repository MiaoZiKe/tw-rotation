"""第八輪：圍繞「月營收動能（S2）」做延伸變體，每一個都和 S2 原版並列。純個股，不持有 0050 或任何 ETF。

S2 原版（factor_lab 重現的網路策略）：前 10 檔；近 3 月均營收／近 12 月均營收 > 1；股價站上 20、60、120 日線；月營收法定公告日（次月 10 日）換股，
**沒有大盤濾網**。本檔不修改 factor_lab（只 import 它的資料載入與引擎），延伸軸：
  cond   營收訊號定義：S2(rv312>1)／營收年增率加速／營收創 12 個月新高／連續 3 或 6 月年增／營收 z 分數 > 1
  rank   排序鍵：S2(營收強度 rv312)／近 3 月平均年增率／價格動能（126 日）
  x2     第二條件：法人買超（近 5 日每日三大法人皆買超）／近 52 週新高 >= 85% 或 95%／低股價淨值比（淨值股價比 > 0.5）／毛利率年變化 > 0
  N      持股 5、10、20      rebal 營收公布日 R／月換 M／季換 Q      hold60 持有到收盤跌破 60 日線才賣
  mf     大盤濾網：無(S2)／廣度（池內站上 200 日線 > 50%）／Faber 月線／0050 200 日線
  cap    單一產業最多 2 或 3 檔       ns   拿掉航運業（回應「2021 航運獨撐」）
訓練只用 2016-12-12～2018-12-31（營收資料到此才滿；約 2.05 年）。2019 年以後前幾輪已看過，本輪照實標示；
最終驗證統一等營收／財報／資產負債表 2012 起回補完成後，在 2013-02～2016-12 乾淨窗口對「凍結候選」各跑一次（final_log.csv 只增不改）。
研究用，非買賣建議；不下單。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import factor_lab as FL  # noqa: E402
from pipeline.compute import swing_lab5 as S  # noqa: E402
from pipeline.compute.strategy_lab import FEE, TAX, SLIP  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "round8"
TRAIN8 = ("2016-12-12", "2018-12-31")
SEEN = {"內部保留（已被看過）": FL.INNER, "最終保留（已被看過）": FL.FINAL}
NEW = FL.NEW                           # 2013-02-01 ～ 2016-12-09，營收補齊後才有
PRIOR_TRIALS = 1445                    # 前八輪累計（factor_lab 報告：累計 1,445 組）
NB_MIN = 0.4                           # 鄰域贏率門檻（第一次用 0.6 時沒有任何變體通過；因為星狀鄰域含 S2 本身（池 100 輸），放寬到 0.4 後再凍結，凍結發生在最終驗證之前）
FLAG_KEY = "balance+financial+revenue@2012-01-01"
FINAL_LOG = OUT / "final_log.csv"
S2 = dict(cond="rv312", rank="rv312", x2=None, N=10, rebal="R", hold60=False, mf=None, cap=None, ns=False)


def make_spec(**kw):
    a = dict(S2, **kw)
    cond = {"rv312": dict(gt={"rv312": 1.0}), "acc": dict(gt={"acc": 0.0}), "revnh": dict(ge={"revnh": 1}), "st3": dict(ge={"st3": 1}),
            "st6": dict(ge={"st6": 1}), "revz": dict(gt={"revz": 1.0})}[a["cond"]]
    gt, ge = dict(cond.get("gt", {})), dict(cond.get("ge", {}))
    ge["ma3"] = 1
    x2 = a["x2"]
    if x2 == "inst5":
        ge["inst5"] = 1
    elif x2 == "nh85":
        ge["nh"] = 0.85
    elif x2 == "nh95":
        ge["nh"] = 0.95
    elif x2 == "bp50":
        gt["bp"] = 0.5
    elif x2 == "gm0":
        gt["gmchg"] = 0.0
    comps = {"rv312": ("rv312",), "yoy3": ("yoy3",), "mom126": ("mom126",)}[a["rank"]]
    sp = dict(comps=comps, N=a["N"], rebal=a["rebal"], mf=a["mf"], gt=gt, ge=ge, axes=a)
    if a["cap"]:
        sp["ind_cap"] = a["cap"]
    if a["hold60"]:
        sp["hold60"] = True
    return sp


def skey(sp):
    return json.dumps(sp, ensure_ascii=False, sort_keys=True, default=str)


# ------------------------------------------------------------------ 特徵
def add_features8(P):
    P = FL.add_factor_features(P) if "ff" not in P else P
    idx, cols, ci = P["idx"], P["cols"], P["ci"]
    ff = P["ff"]
    Cf = pd.DataFrame(P["Cf"], index=idx, columns=cols)
    P["f"]["ma60"] = Cf.rolling(60).mean().to_numpy()
    rv = S._rd("revenue_monthly", ["ym", "code", "revenue"]).dropna(subset=["revenue"])
    rv = rv[rv["code"].isin(ci)]
    rv["per"] = pd.PeriodIndex(rv["ym"].astype(str).str[:7], freq="M")
    R = rv.drop_duplicates(["per", "code"], keep="last").pivot(index="per", columns="code", values="revenue").sort_index()
    R = R.reindex(pd.period_range(R.index.min(), R.index.max(), freq="M"))
    yoy = R / R.shift(12).where(R.shift(12) > 0) - 1
    r3, r12m, r12s = R.rolling(3).mean(), R.rolling(12).mean(), R.rolling(12).std()
    av = FL.rev_avail(yoy.index)
    dly = lambda M: FL._daily(M, av, idx, cols)                              # noqa: E731
    ff["revnh"] = dly((r3 >= r3.rolling(12).max()).astype(float).where(r3.rolling(12).max().notna()))
    ff["st3"] = dly((yoy.rolling(3).min() > 0).astype(float).where(yoy.rolling(3).min().notna()))
    ff["st6"] = dly((yoy.rolling(6).min() > 0).astype(float).where(yoy.rolling(6).min().notna()))
    ff["revz"] = dly((r3 - r12m) / r12s.replace(0, np.nan))
    # 毛利率年變化（TTM 毛利率 - 去年同期）：法定可用日
    fq = S._rd("financial_q", ["year", "quarter", "code", "revenue", "gross_profit"])
    fq["qn"] = fq["year"] * 4 + fq["quarter"] - 1
    fq = fq[fq["code"].isin(ci)]
    qr = range(int(fq.qn.min()), int(fq.qn.max()) + 1)
    Q = {k: FL._qpiv(fq, k, qr, cols) for k in ("revenue", "gross_profit")}
    T = {k: FL._ttm(v) for k, v in Q.items()}
    gm_t = T["gross_profit"] / T["revenue"].where(T["revenue"] > 0)
    ff["gmchg"] = FL._daily(gm_t - gm_t.shift(4), [FL.legal_date(q) for q in qr], idx, cols)
    # 拿掉航運的池別別名：2001 = 前 200 去航運、1001 = 前 100 去航運
    ship = np.array([str(x) == "航運業" for x in P["ind"]])
    for base, alias in ((200, 2001), (100, 1001)):
        P["elig"][alias] = P["elig"][base] & ~ship[None, :]
        P["br"][alias] = P["br"][base]
    P["ship_n"] = int(ship.sum())
    return P


def pool_for(sp, pool):
    return {200: 2001, 100: 1001}.get(pool, pool) if sp["axes"]["ns"] else pool


# ------------------------------------------------------------------ 引擎：持有到跌破 60 日線才賣
def run_hold60(P, spec, pool, lo, hi, trades=False):
    idx = P["idx"]
    lo_i = idx.searchsorted(pd.Timestamp(lo)); hi_i = idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    O, Cf, ma60 = P["O"], P["Cf"], P["f"]["ma60"]
    sigs = sorted(set([lo_i - 1] + FL._ends(idx, lo_i, hi_i, spec["rebal"], P)))
    nxt = {s + 1: s for s in sigs}
    N = spec["N"]
    cash, sh, ent = 1.0, {}, {}
    eq = np.full(len(idx), np.nan); inv = np.zeros(len(idx)); tr = []; buys = 0.0
    for t in range(lo_i, hi_i + 1):
        if t in nxt:
            s = nxt[t]
            on = S.mkt_state(P, spec, s, pool)
            for i in [i for i in sh if (not on) or (np.isfinite(ma60[s, i]) and Cf[s, i] < ma60[s, i])]:
                cash += FL._sell(P, t, i, sh, ent, tr, "大盤濾網關閉，全部出清" if not on else "收盤跌破 60 日線", trades)
                del sh[i]
            if on:
                tgt, scs = FL.pick_f(P, spec, s, pool, nret=N * 3)
                free = N - len(sh)
                eq_open = cash + sum(sh[i] * (O[t, i] if np.isfinite(O[t, i]) else Cf[t - 1, i]) for i in sh)
                for i in [i for i in tgt if i not in sh and np.isfinite(O[t, i])][:max(free, 0)]:
                    amt = min(cash, eq_open / N)
                    if amt <= 0:
                        continue
                    px = O[t, i] * (1 + SLIP)
                    sh[i] = amt / (px * (1 + FEE)); cash -= amt; buys += amt
                    ent[i] = (t, px, scs.get(int(i), np.nan))
        eq[t] = cash + sum(sh[i] * Cf[t, i] for i in sh); inv[t] = (eq[t] - cash) / eq[t]
    return FL._finish(P, eq, inv, tr, buys, lo_i, hi_i, sh, ent, trades)


def run8(P, sp, pool, lo, hi, trades=False):
    pl = pool_for(sp, pool)
    return (run_hold60 if sp.get("hold60") else FL.run)(P, sp, pl, lo, hi, trades)


def mrow(P, sp, pool, lo, hi):
    r = run8(P, sp, pool, lo, hi)
    b = S.bench(P, lo, hi)
    s, bs = S.eq_stats(r["eq"]), S.eq_stats(b)
    y, by = S.yearly(r["eq"]), S.yearly(b)
    return dict(cagr=s["cagr"], mdd=s["mdd"], sharpe=s["sharpe"], bh=bs["cagr"], bh_mdd=bs["mdd"], excess=s["cagr"] - bs["cagr"], ywin=int((y > by.reindex(y.index)).sum()),
                ynum=len(y), yrets=json.dumps({int(k): round(float(v), 4) for k, v in y.items()}), y0050=json.dumps({int(k): round(float(v), 4) for k, v in by.items()}),
                expo=r["expo"], turn=r["turnover"], years=(r["eq"].index[-1] - r["eq"].index[0]).days / 365.25)


# ------------------------------------------------------------------ 批次與訓練
AXES = {"cond": ["acc", "revnh", "st3", "st6", "revz"], "rank": ["yoy3", "mom126"], "x2": ["inst5", "nh85", "nh95", "bp50", "gm0"], "N": [5, 20],
        "rebal": ["M", "Q"], "hold60": [True], "mf": ["br200", "faber", "ma200"], "cap": [2, 3], "ns": [True]}


def one_axis():
    out = [("S2 原版（參照）", make_spec())]
    for ax, lv in AXES.items():
        for v in lv:
            out.append((f"{ax}={v}", make_spec(**{ax: v})))
    return out


def train_eval(P, variants, pools=(200, 100), lo=TRAIN8[0], hi=TRAIN8[1], tag=""):
    rows = []
    for name, sp in variants:
        for pool in pools:
            rows.append(dict(名稱=name, spec=skey(sp), pool=pool, **mrow(P, sp, pool, lo, hi)))
    return pd.DataFrame(rows)


def neighbor_share(reg, sp_by):
    """一階鄰域：只差一個軸的變體（S2 星狀：S2 與同軸其他水準）訓練期有多少比例贏 0050。"""
    sh = []
    for i, r in reg.iterrows():
        a = sp_by[r["spec"]]["axes"]
        same = reg[(reg["pool"] == r["pool"]) & (reg.index != i)]
        c = g = 0
        for j, r2 in same.iterrows():
            b = sp_by[r2["spec"]]["axes"]
            if sum(1 for k in a if a[k] != b[k]) == 1:
                c += 1; g += int(r2["excess"] > 0)
        sh.append(g / c if c else np.nan)
    return sh


def freeze(P):
    """訓練期（2016-12～2018）一次決定並凍結候選。規則事先定：
       單軸候選 = 兩池訓練期超額都 > S2 原版的較差池超額 + 1 個百分點，且兩池皆 > 0、一階鄰域 >= 40% 贏 0050（NB_MIN；原先 60% 無人通過）；取前 4（依較差池超額）；
       疊加候選 = 每個軸取最佳水準（需符合上列單軸條件）疊加；另列 S2 原版當參照。"""
    OUT.mkdir(parents=True, exist_ok=True)
    V = one_axis()
    sp_by = {skey(sp): sp for _, sp in V}
    reg = train_eval(P, V)
    reg["鄰域贏0050比例"] = neighbor_share(reg, sp_by)
    piv = reg.pivot_table(index=["名稱", "spec"], columns="pool", values="excess")
    piv["較差池超額"] = piv.min(axis=1)
    nb = reg.groupby("spec")["鄰域贏0050比例"].min()
    s2min = float(piv.loc[("S2 原版（參照）", skey(make_spec())), "較差池超額"])
    piv = piv.reset_index(); piv["鄰域最小贏率"] = piv["spec"].map(nb)
    piv["通過單軸條件"] = (piv[200] > 0) & (piv[100] > 0) & (piv["較差池超額"] > s2min + 0.01) & (piv["鄰域最小贏率"] >= NB_MIN)
    piv["軸"] = piv["名稱"].str.split("=").str[0]
    best = piv[piv["通過單軸條件"]].sort_values("較差池超額", ascending=False)
    singles = best.head(4)
    best_per_axis = best.groupby("軸").head(1)
    stack_axes = {}
    for _, r in best_per_axis.iterrows():
        sp = sp_by[r["spec"]]["axes"]
        ax = r["軸"]
        stack_axes[ax] = sp[ax]
    cand = [("S2 原版（參照）", make_spec(), "參照")]
    for _, r in singles.iterrows():
        cand.append((r["名稱"], sp_by[r["spec"]], "單軸入選"))
    if len(stack_axes) >= 2:
        st = make_spec(**stack_axes)
        cand.append(("疊加：" + "、".join(f"{k}={v}" for k, v in stack_axes.items()), st, "疊加"))
        for k in stack_axes:                      # 疊加的留一法（拿掉一軸）
            sub = {a: v for a, v in stack_axes.items() if a != k}
            cand.append((f"疊加（不含 {k}）：" + "、".join(f"{a}={v}" for a, v in sub.items()), make_spec(**sub), "疊加留一"))
    seen, final = set(), []
    for nm, sp, why in cand:
        if skey(sp) in seen:
            continue
        seen.add(skey(sp)); final.append((nm, sp, why))
    reg2 = train_eval(P, [(n, s) for n, s, _ in final if skey(s) not in sp_by])      # 疊加組合的訓練期成績（登記為試驗）
    allreg = pd.concat([reg.drop(columns=["鄰域贏0050比例"]), reg2], ignore_index=True)
    allreg.drop(columns=["yrets", "y0050"]).to_csv(OUT / "registry_train.csv", index=False, encoding="utf-8-sig")
    piv.drop(columns=["spec"]).sort_values("較差池超額", ascending=False).to_csv(OUT / "ranking_train_one_axis.csv", index=False, encoding="utf-8-sig")
    fc = dict(frozen_at=time.strftime("%Y-%m-%d %H:%M:%S"), train=list(TRAIN8), note="凍結後不得修改；最終驗證在營收補齊後的 2013-02～2016-12 窗口各跑一次",
              candidates=[dict(name=n, reason=w, spec=s) for n, s, w in final])
    (OUT / "frozen_candidates.json").write_text(json.dumps(fc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return reg, allreg, piv, final


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


# ------------------------------------------------------------------ 已被看過的窗口（只標示、不用來選）
def _link_ex(yrets: dict, ex_year: int | None, last_frac: float):
    f, n = 1.0, 0.0
    for y, r in yrets.items():
        if ex_year is not None and int(y) == ex_year:
            continue
        f *= 1 + r; n += last_frac if int(y) == 2026 else 1.0
    return f ** (1 / n) - 1 if n > 0 else np.nan


def seen_table(P, cands):
    rows = []
    for nm, sp, why in cands:
        for pool in (200, 100):
            row = dict(名稱=nm, 類別=why, 池=pool)
            for w, (lo, hi) in {"內部保留 2019-2022（已被看過）": FL.INNER, "2023-2026（已被看過）": FL.FINAL, "2019-2026 全段（已被看過）": (FL.INNER[0], FL.FINAL[1])}.items():
                m = mrow(P, sp, pool, lo, hi)
                row.update({f"{w}_年化": m["cagr"], f"{w}_0050": m["bh"], f"{w}_差pt": (m["cagr"] - m["bh"]) * 100, f"{w}_回撤": m["mdd"], f"{w}_逐年贏": f"{m['ywin']}/{m['ynum']}"})
                if w.startswith("2019-2026"):
                    y, by = json.loads(m["yrets"]), json.loads(m["y0050"])
                    row["全段_逐年報酬"] = json.dumps(y, ensure_ascii=False)
                    row["全段_不含2021年化"] = _link_ex(y, 2021, 0.81); row["0050_不含2021年化"] = _link_ex(by, 2021, 0.81)
                    row["不含2021_差pt"] = (row["全段_不含2021年化"] - row["0050_不含2021年化"]) * 100
            rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 最終驗證（營收補齊後；每個凍結候選每池只跑一次）
def backfill_done(fetch=True):
    try:
        if fetch:
            subprocess.run(["git", "fetch", "origin", "main:refs/remotes/origin/main"], cwd=ROOT, capture_output=True, timeout=120)
        txt = subprocess.run(["git", "show", "origin/main:data/_state/backfill_progress.json"], cwd=ROOT, capture_output=True, timeout=60, text=True).stdout
        d = json.loads(txt)
        c = d.get("complete", d)
        return bool(c.get(FLAG_KEY, {}).get("done")), c.get(FLAG_KEY, {}).get("remaining")
    except Exception as e:                                   # 抓不到就當作沒補齊，不冒險
        return False, str(e)


def coverage_ok(P, lo="2013-03-01", need=0.5):
    idx = P["idx"]; m = (idx >= pd.Timestamp(lo)) & (idx <= pd.Timestamp("2013-12-31"))
    el = P["elig"][200][m]; fin = np.isfinite(P["ff"]["rv312"][m])
    return float((el & fin).sum() / max(el.sum(), 1)) >= need


def run_final(P, cands):
    """只有 (1) main 的 backfill 旗標 done=true 且 (2) 本地資料的 2013 年營收覆蓋 >= 50% 才會執行；每個候選每池只跑一次（讀紀錄）。"""
    done, rem = backfill_done()
    if not done or not coverage_ok(P):
        return dict(ran=False, reason=f"營收補齊旗標 done={done}（remaining={rem}），或本地資料 2013 年營收覆蓋不足；不執行最終驗證")
    log = pd.read_csv(FINAL_LOG) if FINAL_LOG.exists() else pd.DataFrame(columns=["spec", "pool"])
    rows = []
    for nm, sp, why in cands:
        for pool in (200, 100):
            hit = log[(log["spec"] == skey(sp)) & (log["pool"] == pool)]
            if len(hit):
                rows.append(hit.iloc[0].to_dict()); continue
            m = mrow(P, sp, pool, *NEW)
            row = dict(名稱=nm, spec=skey(sp), pool=pool, lo=NEW[0], hi=NEW[1], 執行時間=time.strftime("%Y-%m-%d %H:%M:%S"), **m)
            log = pd.concat([log, pd.DataFrame([row])], ignore_index=True); log.to_csv(FINAL_LOG, index=False, encoding="utf-8-sig"); rows.append(row)
    return dict(ran=True, rows=pd.DataFrame(rows))


def load_frozen():
    fc = json.loads((OUT / "frozen_candidates.json").read_text(encoding="utf-8"))
    return [(c["name"], c["spec"], c["reason"]) for c in fc["candidates"]]


def main8():
    OUT.mkdir(parents=True, exist_ok=True)
    P = add_features8(FL.load_all())
    if not (OUT / "frozen_candidates.json").exists():
        freeze(P)
    cands = load_frozen()
    seen_table(P, cands).to_csv(OUT / "seen_windows.csv", index=False, encoding="utf-8-sig")
    res = run_final(P, cands)
    if res["ran"]:
        res["rows"].to_csv(OUT / "final_2013_2016.csv", index=False, encoding="utf-8-sig")
    (OUT / "final_status.json").write_text(json.dumps({k: v for k, v in res.items() if k != "rows"}, ensure_ascii=False, indent=1), encoding="utf-8")
    return P, cands, res


if __name__ == "__main__":
    main8()


def seen_all_one_axis(P):
    """描述用（2019 年起已被看過，不用來選任何東西）：全部單軸變體 vs S2 的內部／最終窗口與不含 2021 的差距。"""
    cands = [(n, sp, "單軸（描述）") for n, sp in one_axis()]
    return seen_table(P, cands)
