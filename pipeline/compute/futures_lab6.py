"""台指期第六輪：縮小與 0050 的最後 0.4～1.9 個百分點。

現況（誠實揭露）：2003-07～2007、2008～2016、2017～2020、2021 起這四段資料，前五輪都已經被看過（第五輪的重跑與揭露也看過），
所以這一輪找到的任何冠軍都**只能標成「已窺視、待前向驗證」**——不是乾淨的樣本外證據。
本輪仍照規矩做：只用 2008～2016 選家族冠軍與參數（含 walk-forward、參數鄰域兩道關卡），再一次列出四段；
冠軍條件：2003-07～2007、2017～2020、2021 起三段年化都贏 0050，且每一段平均曝險 <= 1.2 倍。
找到候選後額外做：區塊重抽樣信賴區間（對 0050 的超額報酬）與參數鄰域（連同三段）。

縮小差距的新機制（都是規則調曝險，不是單純加槓桿）
  1. 多訊號投票：k 個危險旗標同時成立才出場（k = 1/2/3）。
  2. 分批減碼：旗標數 >= 1 但未達 k 時，曝險降到 s1 倍（0.5／0.75），達到 k 才全出。
  3. 回場加快：危險解除後不用等 m 天，只要週K 翻多（W）、或收盤站回 20 日線（MA20）、或兩者之一（either）就立刻回場。
  4. 動態曝險：趨勢強（站上 50 日線且 50 日線 > 200 日線且 VIX<20）= hi 倍，趨勢弱（跌破 50 日線）= lo 倍，其餘 1.0 倍；平均曝險受 <= 1.2 限制。
  5. 正價差／逆價差當曝險加減碼：5 日平均基差 <= -0.2%（逆價差，歷史上之後較容易反彈）曝險 +0.2；>= +0.4%（正價差過大）曝險 -0.2。
  6. 結算日換月時點：資料上無法觀察下個月合約在結算日的表現（連續序列只有近月），任何「提早一天換月」的好處都要靠假設，
     所以只做敏感度檢查（不進冠軍資格）：把結算日當天的報酬也換成現貨報酬，看這個假設最多值多少，見 README。
opt_pc（選擇權 P/C）資料目前還沒進 main（data/opt_pc 不存在），本輪不用。
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402
from pipeline.compute import futures_lab2 as G  # noqa: E402
from pipeline.compute import futures_lab4 as L4  # noqa: E402
from pipeline.compute import futures_lab5 as L5  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "round6"
CLEAN, SEARCH, W_C, W_D = L5.CLEAN, L5.SEARCH34, L5.W_C, L5.W_D
WF_TEST = L4.WF_TEST; WF_END = L4.WF_END
EXPO_MAX = 1.2
DYN = {"none": None, "1.3/1.0": (1.3, 1.0), "1.5/0.8": (1.5, 0.8), "1.2/0.8": (1.2, 0.8)}


@G.njit(cache=True)
def _state_fast(raw, m, clear):
    n = len(raw); out = np.zeros(n, np.bool_); s = False; clr = 0
    for i in range(n):
        if raw[i]:
            s = True; clr = 0
        elif s:
            if clear[i]:
                s = False
            else:
                clr += 1
                if clr >= m:
                    s = False
        out[i] = s
    return out


class Lab6(L5.Lab5):
    def __init__(self, both=False):
        super().__init__(both)
        self.ma20 = pd.Series(self.c).rolling(20).mean().to_numpy()
        self.wbull = self.reg == 1

    def target(self, p):
        key = "T6" + json.dumps(p, sort_keys=True, default=str)
        if key in self.tcache:
            return self.tcache[key]
        fl = self.flags(p)
        cnt = sum(v.astype(int) for v in fl.values())
        raw = cnt >= p["k"]
        c = self.c
        clear = {"none": np.zeros(len(c), bool), "W": self.wbull, "MA20": np.where(np.isnan(self.ma20), False, c > self.ma20),
                 "either": self.wbull | np.where(np.isnan(self.ma20), False, c > self.ma20)}[p["fast"]]
        st = _state_fast(raw, int(p["m"]), clear)
        vx = np.where(np.isnan(self.vix), 0.0, self.vix)
        strong = (c > self.ma[50]) & (self.ma[50] > self.ma[200]) & (vx < 20)
        weak = (c < self.ma[50]) & ~strong
        if p["dyn"] == "none":
            expo = np.full(len(c), float(p["b"]))
        else:
            hi, lo = DYN[p["dyn"]]
            expo = np.where(strong, hi, np.where(weak, lo, 1.0))
        if p["stage"] > 0:
            expo = np.where((cnt >= 1) & (cnt < p["k"]), expo * p["stage"], expo)
        if p["bmod"]:
            b = self.bas
            expo = expo + np.where(np.isnan(b), 0.0, np.where(b <= -0.002, 0.2, np.where(b >= 0.004, -0.2, 0.0)))
            expo = np.maximum(expo, 0.0)
        tgt = np.where(st, 0.0, expo)
        self.tcache[key] = tgt
        return tgt


SETS6 = [("W", "DD"), ("W", "V"), ("W",), ("T", "SM"), ("T", "V", "SM"), ("W", "DD", "V"), ("W", "T", "DD"), ("W", "DD", "B"), ("T", "DD"), ("W", "SM")]
AX6 = dict(n=[150, 200], vix=[30, 35], bas=[0.003], dd=[0.10, 0.15], m=[1, 3], fast=["none", "W", "MA20", "either"], stage=[0, 0.5, 0.75],
           dyn=list(DYN), b=[1.0, 1.2], bmod=[0, 1])


def grid6():
    out = []
    for st in SETS6:
        ks = [k for k in range(1, len(st) + 1) if not ("SM" in st and k < 2)]
        for k in ks:
            axes = {key: (v if (key not in ("n", "vix", "dd", "bas") or
                               (key == "n" and "T" in st) or (key == "vix" and "V" in st) or (key == "dd" and "DD" in st) or (key == "bas" and "B" in st)) else v[:1])
                    for key, v in AX6.items()}
            if k == 1:
                axes["stage"] = [0]
            for vals in itertools.product(*[axes[x] for x in axes]):
                p = dict(zip(axes, vals))
                if p["dyn"] != "none" and p["b"] != 1.0:
                    continue
                p["set"] = st; p["k"] = k; p["gap"] = 0; p["boost"] = 0
                out.append(p)
    return out


def pstr6(p):
    keys = [("n", "T"), ("vix", "V"), ("bas", "B"), ("dd", "DD")]
    s = f"{'+'.join(p['set'])}|k={p['k']}" + "".join(f"|{k}={p[k]}" for k, f in keys if f in p["set"])
    return s + f"|m={p['m']}|fast={p['fast']}|stage={p['stage']}|dyn={p['dyn']}|b={p['b']}|bmod={p['bmod']}"


def neighbors6(p):
    res = []
    for key, vals in AX6.items():
        if (key == "n" and "T" not in p["set"]) or (key == "vix" and "V" not in p["set"]) or (key == "dd" and "DD" not in p["set"]) or (key == "bas" and "B" not in p["set"]):
            continue
        if key == "b" and p["dyn"] != "none":
            continue
        i = vals.index(p[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p); q[key] = vals[j]
                if q["dyn"] != "none" and q["b"] != 1.0:
                    q["b"] = 1.0
                if q["k"] == 1:
                    q["stage"] = 0
                res.append(q)
    return res


def score(lab, p, a, b):
    r, e, l = lab.run_p(p)
    s = L4.window_stats(lab, r, e, a, b); bb = lab.b50(a, b)
    if s["avg_expo"] > EXPO_MAX or s["mdd"] < bb["mdd"]:
        return -1 + s["mdd"], s
    return s["cagr"], s


def select(lab, pool, a, b):
    best, bs = None, -9
    for p in pool:
        sc, _ = score(lab, p, a, b)
        if sc > bs:
            best, bs = p, sc
    return best, bs


def wf(lab, pool):
    ends = WF_TEST[1:] + [WF_END]
    rows = []
    for a, b in zip(WF_TEST, ends):
        p, tr = select(lab, pool, SEARCH[0], a)
        r, e, l = lab.run_p(p)
        s = L4.window_stats(lab, r, e, a, b); bb = lab.b50(a, b)
        rows.append(dict(a=a, b=b, p=p, cagr=s["cagr"], b50=bb["cagr"], beat=s["cagr"] >= bb["cagr"]))
    return rows


def run_search(lab):
    grid = grid6()
    a, b = SEARCH
    bb = lab.b50(a, b)
    reg = []
    for p in grid:
        r, e, l = lab.run_p(p)
        s = L4.window_stats(lab, r, e, a, b)
        reg.append(dict(策略=pstr6(p), 搜尋期年化=s["cagr"], 搜尋期回撤=s["mdd"], 平均曝險=s["avg_expo"]))
    rows = []
    for st in SETS6:
        pool = [g for g in grid if g["set"] == st]
        ch, sc = select(lab, pool, a, b)
        wrows = wf(lab, pool)
        wins = sum(x["beat"] for x in wrows)
        nbs = [score(lab, q, a, b)[1] for q in neighbors6(ch)]
        nbeat = float(np.mean([s["cagr"] >= bb["cagr"] and s["avg_expo"] <= EXPO_MAX for s in nbs])) if nbs else np.nan
        _, sch = score(lab, ch, a, b)
        rows.append(dict(危險訊號組合="+".join(st), 冠軍參數=pstr6(ch), 搜尋期年化=sch["cagr"], 搜尋期回撤=sch["mdd"], 平均曝險=sch["avg_expo"], WF贏段=f"{wins}/{len(wrows)}",
                         鄰域贏0050比例=nbeat, 鄰域數=len(nbs), 關卡1=wins > len(wrows) / 2, 關卡2=(nbeat >= 2 / 3) if nbs else False, _p=ch))
    return dict(grid_n=len(grid), reg=reg, fam=pd.DataFrame(rows), b50=bb)


# ------------------------------------------------------------------ 候選、揭露（四段一次列出；全部已被看過）
def old_ref(lab, p):
    """第四輪家族的原機制（用 Lab4 的 target），當對照。"""
    tgt = L4.Lab4.target(lab, p)
    r, e, l = lab.run_t(tgt)
    if p.get("gap"):
        gr, gf = lab.gap_series()
        r = (1 + r) * (1 + gr) - 1; e = e + gf.astype(float) * 0.5
    return r, e, l


REF4 = {
    "R4 W+DD（第五輪最接近）": dict(set=("W", "DD"), k=2, n=200, vix=30, bas=0.003, dd=0.10, m=1, base=1.2, boost=1, gap=1),
    "R4 W+V（第五輪第二接近）": dict(set=("W", "V"), k=2, n=200, vix=35, bas=0.003, dd=0.15, m=5, base=1.2, boost=0, gap=1),
}


def win_stats(lab, r, e, a, b):
    return L4.window_stats(lab, r, e, a, b)


def collect(lab, R):
    c = []
    for _, row in R["fam"].iterrows():
        p = row["_p"]
        r, e, l = lab.run_p(p)
        c.append(dict(name="R6 " + row["危險訊號組合"], r=r, e=e, p=p, label=pstr6(p), kind="r6", gates=(bool(row["關卡1"]), bool(row["關卡2"]))))
    for nm, p in REF4.items():
        r, e, l = old_ref(lab, p)
        c.append(dict(name=nm, r=r, e=e, p=p, label=L4.pstr(p), kind="r4", gates=None))
    for nm, lev in (("基準 持有1.0x", 1.0), ("基準 持有1.2x", 1.2)):
        r, e, l = lab.hold(lev)
        c.append(dict(name=nm, r=r, e=e, p=None, label=nm, kind="hold", gates=None))
    return c


def reveal(lab, cands):
    lock = OUT / "_reveal_done.json"
    if lock.exists():
        return json.loads(lock.read_text(encoding="utf-8"))
    wins = {"clean": CLEAN, "search": SEARCH, "C": W_C, "D": W_D}
    res = {"0050": {k: lab.b50(*v) for k, v in wins.items()}, "cands": {}}
    for c in cands:
        res["cands"][c["name"]] = dict(label=c["label"], kind=c["kind"], gates=c["gates"], wins={k: win_stats(lab, c["r"], c["e"], *v) for k, v in wins.items()})
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


def dist(V):
    b = V["0050"]; rows = []
    for nm, c in V["cands"].items():
        w = c["wins"]
        d = {k: w[k]["cagr"] - b[k]["cagr"] for k in ("clean", "search", "C", "D")}
        ex = {k: w[k]["avg_expo"] for k in ("clean", "search", "C", "D")}
        three = [d["clean"], d["C"], d["D"]]
        rows.append(dict(name=nm, label=c["label"], kind=c["kind"], gates=c["gates"], d=d, ex=ex, worst=min(three), mean=float(np.mean(three)),
                         champ=all(x > 0 for x in three) and all(ex[k] <= EXPO_MAX + 1e-9 for k in ("clean", "C", "D")) and c["kind"] != "hold",
                         win3=all(x > 0 for x in three), ok_expo=all(ex[k] <= EXPO_MAX + 1e-9 for k in ("clean", "C", "D"))))
    return rows


# ------------------------------------------------------------------ 穩健檢查
def boot_excess(rs, rb, L=21, n=2000, seed=7):
    rs = np.asarray(rs, float); rb = np.asarray(rb, float)
    T = len(rs); rng = np.random.default_rng(seed)
    idx = np.empty((n, T), np.int64); idx[:, 0] = rng.integers(0, T, n)
    new = rng.random((n, T)) < 1.0 / L; starts = rng.integers(0, T, (n, T))
    for t in range(1, T):
        idx[:, t] = np.where(new[:, t], starts[:, t], (idx[:, t - 1] + 1) % T)
    ls, lb = np.log1p(rs), np.log1p(rb)
    yrs = T / 252.0
    ex = np.exp(ls[idx].sum(1) / yrs) - np.exp(lb[idx].sum(1) / yrs)
    base = np.exp(ls.sum() / yrs) - np.exp(lb.sum() / yrs)
    return dict(point=float(base), lo=float(np.percentile(ex, 5)), hi=float(np.percentile(ex, 95)), p_pos=float((ex > 0).mean()), n=n, L=L)


def robustness(lab, cand):
    b50 = lab.lab.b50["ret"]
    wins = {"clean": CLEAN, "C": W_C, "D": W_D}
    r = cand["r"]; out = {}
    pool_s, pool_b = [], []
    for k, (a, z) in wins.items():
        m = (r.index >= pd.Timestamp(a)) & ((r.index < pd.Timestamp(z)) if z else True)
        out[k] = boot_excess(r[m].to_numpy(), b50[m].to_numpy())
        pool_s.append(r[m].to_numpy()); pool_b.append(b50[m].to_numpy())
    out["pooled"] = boot_excess(np.concatenate(pool_s), np.concatenate(pool_b))
    return out


def neighbor_table(lab, p):
    b = {k: lab.b50(*v) for k, v in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
    rows = []
    for q in neighbors6(p):
        r, e, l = lab.run_p(q)
        w = {k: win_stats(lab, r, e, *v) for k, v in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
        rows.append({k: w[k]["cagr"] - b[k]["cagr"] for k in w} | {"expo": max(w[k]["avg_expo"] for k in w), "p": pstr6(q)})
    return pd.DataFrame(rows)


def ablation(lab, p):
    """把各機制逐一關掉，看對三段距離的影響（事後分析，全部是已被看過的資料）。"""
    b = {k: lab.b50(*v) for k, v in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
    variants = {"完整": p}
    q = dict(p); q["stage"] = 0; variants["關掉分批減碼"] = q
    q = dict(p); q["fast"] = "none"; variants["關掉快速回場"] = q
    q = dict(p); q["dyn"] = "none"; q["b"] = 1.2; variants["關掉動態曝險（固定 1.2）"] = q
    q = dict(p); q["bmod"] = 0; variants["關掉正逆價差加減碼"] = q
    q = dict(p); q["k"] = 1; q["stage"] = 0; variants["票數降為 1（任一旗標就出場）"] = q
    rows = []
    for nm, v in variants.items():
        r, e, l = lab.run_p(v)
        w = {k: win_stats(lab, r, e, *x) for k, x in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
        rows.append({"變體": nm} | {k: w[k]["cagr"] - b[k]["cagr"] for k in w} | {"avg_expo": max(w[k]["avg_expo"] for k in w)})
    return pd.DataFrame(rows)


def additive_ablation(lab, p):
    """從『所有新機制都關掉』的底版（保留家族的旗標組合、k、m、基礎曝險 1.2）開始，一次只加一個機制，看各機制單獨的效果。"""
    b = {k: lab.b50(*v) for k, v in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
    base = dict(p); base.update(stage=0, fast="none", dyn="none", b=1.2, bmod=0)
    variants = {"底版（無新機制，固定 1.2 倍）": base}
    if base["k"] >= 2:
        q = dict(base); q["stage"] = 0.5; variants["+分批減碼 0.5"] = q
        q = dict(base); q["stage"] = 0.75; variants["+分批減碼 0.75"] = q
    for f in ("W", "MA20", "either"):
        q = dict(base); q["fast"] = f; variants[f"+快速回場 {f}"] = q
    for d in ("1.3/1.0", "1.5/0.8", "1.2/0.8"):
        q = dict(base); q["dyn"] = d; q["b"] = 1.0; variants[f"+動態曝險 {d}"] = q
    q = dict(base); q["bmod"] = 1; variants["+正逆價差加減碼"] = q
    rows = []
    for nm, v in variants.items():
        r, e, l = lab.run_p(v)
        w = {k: win_stats(lab, r, e, *x) for k, x in {"clean": CLEAN, "C": W_C, "D": W_D}.items()}
        rows.append({"變體": nm} | {k: w[k]["cagr"] - b[k]["cagr"] for k in w} | {"avg_expo": max(w[k]["avg_expo"] for k in w)})
    return pd.DataFrame(rows)


def _fmt_ab(ab):
    t = ab.copy()
    for c in ("clean", "C", "D"):
        t[c] = t[c].map(ppt)
    t["avg_expo"] = t["avg_expo"].map(lambda x: f"{x:.2f}")
    return t.rename(columns={"clean": "2003-07～2007 差距", "C": "2017～2020 差距", "D": "2021 起差距", "avg_expo": "最大平均曝險"})


# ------------------------------------------------------------------ 文件
def fp(x, d=1):
    return F.fmt(x, True, d)


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def ppt(x):
    return "-" if x is None else f"{x * 100:+.1f}"


def write_docs(lab, R, cands, V):
    b = V["0050"]
    rows = sorted(dist(V), key=lambda r: -r["worst"])
    champs = [r for r in rows if r["champ"]]
    L = ["# 台指期第六輪：縮小與 0050 的最後差距（分批減碼、快速回場、動態曝險、正逆價差加減碼、投票出場）\n"]
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。淘汰規則：年化輸同期含息扣成本的 0050 -> 淘汰；冠軍條件：2003-07～2007、2017～2020、2021 起三段年化都贏 0050，且每段平均曝險 <= 1.2 倍。\n")
    L.append("> **誠實揭露**：這四段資料前五輪都已被看過；本輪參數只用 2008～2016 選（walk-forward 與參數鄰域兩道關卡），但設計方向（哪些機制、哪些家族）是看過前幾輪的距離表才決定的。"
             "**所以本輪任何冠軍一律標成「已窺視、待前向驗證」**，不是乾淨的樣本外證據；真正的驗證要等新的資料（2027 之後）。\n")
    L.append("## 〇、結論與距離排序\n")
    L.append(f"0050 含息扣成本年化：2003-07～2007 {fp(b['clean']['cagr'])}、2008～2016 {fp(b['search']['cagr'])}、2017～2020 {fp(b['C']['cagr'])}、2021 起 {fp(b['D']['cagr'])}。\n")
    if champs:
        L.append(f"**有 {len(champs)} 個候選三段都贏 0050 且平均曝險 <= 1.2：{'、'.join(r['name'] for r in champs)}。全部標為「已窺視、待前向驗證」。**\n")
    else:
        L.append("**沒有候選三段都贏 0050（含平均曝險 <= 1.2 的條件）。**以下依『最差一段差距』排序，讓你看到還差多少。\n")
    t = []
    for r in rows:
        t.append({"候選": r["name"], "參數": (r["label"] or "").replace("|", "／"), "搜尋關卡": ("過/過" if r["gates"] and all(r["gates"]) else "未全過" if r["gates"] else "-"),
                  "2003-07～2007": ppt(r["d"]["clean"]), "2008～2016": ppt(r["d"]["search"]), "2017～2020": ppt(r["d"]["C"]), "2021 起": ppt(r["d"]["D"]),
                  "最差一段": ppt(r["worst"]), "平均": ppt(r["mean"]), "平均曝險 乾淨／C／D": "／".join(f"{r['ex'][k]:.2f}" for k in ("clean", "C", "D")),
                  "判定": ("**冠軍（已窺視、待前向驗證）**" if r["champ"] else ("三段贏但曝險 >1.2" if r["win3"] else "淘汰"))})
    L.append("（差距＝候選年化 - 0050 年化，單位百分點；R4 為上一輪候選、基準為永遠持有 1.0／1.2 倍，不是策略）\n\n" + md(pd.DataFrame(t)))
    elig = [r for r in rows if r["kind"] == "r6"]
    top = elig[0]
    top_c = next(c for c in cands if c["name"] == top["name"])
    # 1 機制
    L.append("## 一、本輪新機制與各機制的邊際效果（對本輪最接近的候選逐一關掉；事後分析）\n")
    ab = ablation(lab, top_c["p"])
    abt = _fmt_ab(ab)
    L.append(f"候選：**{top['name']}**（{pstr6(top_c['p']).replace('|', '／')}）\n\n" + md(abt))
    for nm in ("R6 T+SM", "R6 W+DD"):
        cc = next((c for c in cands if c["name"] == nm), None)
        if cc:
            L.append(f"**加法版（從所有新機制都關掉的底版開始，一次只加一個機制）— {nm}**\n\n" + md(_fmt_ab(additive_ablation(lab, cc["p"]))))
    L.append("機制說明：投票出場（k）、分批減碼（stage）、快速回場（fast：週K 翻多或站回 20 日線）、動態曝險（dyn：強趨勢加到 hi 倍、弱趨勢降到 lo 倍）、正逆價差加減碼（bmod：基差 <= -0.2% 曝險 +0.2、>= +0.4% 曝險 -0.2）。\n")
    # 2 家族
    L.append("## 二、各危險訊號家族的冠軍（搜尋 2008～2016；平均曝險 <= 1.2；兩道關卡）\n")
    ft = R["fam"].drop(columns=["_p"]).copy()
    for c in ("搜尋期年化", "搜尋期回撤", "鄰域贏0050比例"):
        ft[c] = ft[c].map(fp)
    ft["平均曝險"] = ft["平均曝險"].map(lambda x: f"{x:.2f}")
    ft["關卡1"] = ft["關卡1"].map(lambda x: "過" if x else "未過"); ft["關卡2"] = ft["關卡2"].map(lambda x: "過" if x else "未過")
    ft["冠軍參數"] = ft["冠軍參數"].str.replace("|", "／")
    L.append(md(ft))
    # 3 穩健
    L.append("## 三、穩健檢查（對最接近的候選與所有冠軍；全部是已被看過的資料）\n")
    chk = champs[:3] if champs else rows[:0]
    targets = [top] + [c for c in champs if c["name"] != top["name"]][:2]
    for tr in targets:
        cc = next(c for c in cands if c["name"] == tr["name"])
        if cc["kind"] != "r6":
            continue
        bo = robustness(lab, cc)
        bt = pd.DataFrame([{"視窗": nm, "超額年化（點估計）": ppt(v["point"]), "90% 區間": f"{ppt(v['lo'])} ～ {ppt(v['hi'])}", "超額 > 0 的比例": fp(v["p_pos"], 0)}
                           for nm, v in (("2003-07～2007", bo["clean"]), ("2017～2020", bo["C"]), ("2021 起", bo["D"]), ("三段合併", bo["pooled"]))])
        L.append(f"**{tr['name']} 區塊重抽樣（平穩 bootstrap，平均區塊 21 個交易日、{bo['pooled']['n']} 次；超額＝候選年化 - 0050 年化）**\n\n" + md(bt))
        nb = neighbor_table(lab, cc["p"])
        nbt = pd.DataFrame([{"視窗": nm, "鄰域數": len(nb), "贏 0050 的比例": fp((nb[k] > 0).mean(), 0), "差距中位數": ppt(nb[k].median()), "最差": ppt(nb[k].min())}
                            for nm, k in (("2003-07～2007", "clean"), ("2017～2020", "C"), ("2021 起", "D"))])
        L.append(f"**{tr['name']} 參數鄰域（只動一個維度、相鄰一格；{len(nb)} 個鄰居；最大平均曝險 {nb['expo'].max():.2f}）**\n\n" + md(nbt))
    # 4 換月時點
    L.append("## 四、結算日換月時點的敏感度（假設性上限，不進冠軍資格）\n")
    try:
        lab2 = Lab6(both=True)
        sens = []
        for nm, p in (("最接近候選", top_c["p"]),):
            r, e, l = lab2.run_p(p)
            for k, v in {"clean": CLEAN, "C": W_C, "D": W_D}.items():
                s = win_stats(lab2, r, e, *v)
                sens.append({"候選": nm, "視窗": k, "標準換月年化": fp(V["cands"][top["name"]]["wins"][k]["cagr"]), "提早一天換月（假設）年化": fp(s["cagr"]), "差": ppt(s["cagr"] - V["cands"][top["name"]]["wins"][k]["cagr"])})
        L.append("做法：連『結算日當天』的報酬也換成現貨報酬（假設下個月合約在結算日的表現等於現貨），等於提早一天換到下個月合約、避開結算日收斂。連續序列裡看不到下個月合約，所以這個好處**只能靠假設**；"
                 "結算日當天『期貨 - 現貨』平均 -18 bp（約 -2.2%／年）的來源也沒有拆解（可能是結算價與收盤價的差、也可能是殺尾盤）。\n\n" + md(pd.DataFrame(sens)))
    except Exception as exc:                    # noqa: BLE001
        L.append(f"敏感度檢查失敗：{exc}\n")
    # 5 累計試驗數
    cum = []
    reg = {2: "registry_r2.csv", 3: "registry_r3.csv", 4: "registry_r4.csv"}
    r5 = ROOT / "docs" / "futures_lab" / "round5"
    cum.append({"輪": "第一輪", "新增試驗（登記數）": 2 * len(F.build_grid()), "說明": f"{len(F.build_grid())} 組格點 x A／B 兩版（WF 重選另計；加跳空組合等不含）"})
    for k, f in reg.items():
        try:
            cum.append({"輪": f"第{ {2: '二', 3: '三', 4: '四'}[k] }輪", "新增試驗（登記數）": len(pd.read_csv(r5 / f)), "說明": f"round5/{f}（第五輪用修正引擎重跑時的登記）"})
        except Exception:                       # noqa: BLE001
            pass
    cum.append({"輪": "第五輪", "新增試驗（登記數）": 8, "說明": "跳空日內單組合實驗 8 組（其餘為重跑，不重複計）"})
    cum.append({"輪": "第六輪", "新增試驗（登記數）": R["grid_n"], "說明": "本輪格點（10 個危險訊號家族）；registry.csv"})
    ct = pd.DataFrame(cum)
    tot = int(ct["新增試驗（登記數）"].sum())
    L.append("## 五、累計試驗數（多重比較）\n")
    L.append(md(ct) + f"\n**累計約 {tot:,} 組。**冠軍判定只看三段，沒有做多重比較校正；所以即使出現冠軍，也只算『已窺視、待前向驗證』。\n")
    # 6 筆記
    L.append("## 六、逐段筆記\n")
    notes = []
    for per, (a, z) in (("乾淨2003-07～2007", CLEAN), ("搜尋期2008-16", SEARCH), ("2017-20", W_C), ("2021起", W_D)):
        notes.append(L4.episodes(lab, top_c["p"], a, z, tag=f"{top['name']}／{per}"))
    nt = pd.concat(notes)
    nt.to_csv(OUT / "trades_round6.csv", index=False, encoding="utf-8-sig")
    N = [f"# 台指期第六輪逐段筆記：{top['name']}\n"]
    for tag, g in nt.groupby("版本", sort=False):
        N.append(f"\n## {tag}（{len(g)} 段）\n")
        for _, x in g.iterrows():
            N.append(f"- **{x['類型']} {x['開始']} ～ {x['結束']}**（{x['天數']} 天）｜策略 {x['策略報酬']:.2%}｜指數 {x['指數報酬']:.2%}" + (f"｜觸發旗標 {x['觸發旗標']}" if x['觸發旗標'] else "") + f"｜**檢討**：{x['事後檢討']}")
    (OUT / "trades_notes_round6.md").write_text("\n".join(N), encoding="utf-8")
    sp = nt[nt.類型 == "空手"]
    L.append(f"完整逐段見 `trades_notes_round6.md`、`trades_round6.csv`（共 {len(nt)} 段）。空手期間：避開下跌 {int((sp.指數報酬 < -0.03).sum())} 段（平均指數 {sp[sp.指數報酬 < -0.03].指數報酬.mean():.1%}）、錯過反彈 {int((sp.指數報酬 > 0.03).sum())} 段（平均 +{sp[sp.指數報酬 > 0.03].指數報酬.mean():.1%}）。\n")
    L.append("## 七、限制\n")
    L.append("- 四段資料全部被看過，本輪冠軍（若有）只能是『已窺視』；選擇仍只用 2008～2016，但設計方向受前幾輪結果影響。\n"
             "- opt_pc（選擇權 P/C）尚未進 main（`data/opt_pc` 不存在），本輪未用。\n"
             "- 含 VIX（V）、動態曝險的『強趨勢』判斷在 2003-07～2007 沒有 VIX 資料：VIX 條件視為不成立（V 旗標不觸發；強趨勢條件的 VIX<20 視為成立）。\n"
             "- 換月修正用現貨日報酬近似；保證金與資金利息為假設（原始 10%／維持 8%、閒置資金年息 1%）。\n")
    L.append("## 八、重現\n\n`python -m pipeline.compute.futures_lab6`（約 8～10 分鐘）；揭露鎖檔存在時直接讀取。測試：`pytest tests/test_futures_lab6.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = Lab6()
    R = run_search(lab)
    pd.DataFrame(R["reg"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    print(R["fam"].drop(columns=["_p"]).round(3).to_string())
    cands = collect(lab, R)
    V = reveal(lab, cands)
    write_docs(lab, R, cands, V)
    return lab, R, cands, V


if __name__ == "__main__":
    main()
