"""台指期第五輪：用「修正換月跳點」的引擎，重跑第一～四輪的搜尋，並把所有結果放在同一張「離 0050 差幾個百分點」的表裡。

為什麼重跑（第四輪發現）：台指期近月連續序列在結算日隔天有向下的換月跳點（新合約已內含預期股利），但真實持倉換月不會因此虧損、
長期持有期貨反而賺到股利折價收斂。前三輪把跳點當虧損，每年低估約一個股利殖利率。這一輪把修正套進**所有**引擎：
  * 價格：結算日隔天的報酬改用現貨加權指數當天報酬，之前的價格比例往回調整（OHLC 全部、含 ATR、均線、週K、指標）。
  * 成本：手續費、滑價、換月成本是「原價格口徑」的點數；價格往回調整後（早期價格較低）要乘上調整係數 fac（<1），否則早期成本被高估。
    ⚠ 第四輪的 `_sim_lev_fx` 把這個係數用反了（乘 1/fac，早期成本被高估到約 3 倍，約 0.3～0.6%／年），本輪已改正並重跑第四輪。
  * 基差（期貨 - 現貨）改用**未調整**的期貨價計算（基差是真實價差，不能被調整係數扭曲）。

保留期一律不動：第一～四輪的鎖檔照舊；本輪重算的保留期結果只揭露一次（`_reveal_done.json`），並標註「已被看過」。
乾淨證據：2003-07～2007（從未用於第三、四輪的選參；第一、二輪的搜尋期含這段，所以第一、二輪的候選不能拿它當乾淨證據）。
注意：第四輪曾對 W、T+SM 兩個候選與持有基準揭露過一次這段（`_backcheck_done.json`），本輪新的候選仍是第一次。
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402
from pipeline.compute import futures_lab2 as G  # noqa: E402
from pipeline.compute import futures_lab3 as L3  # noqa: E402
from pipeline.compute import futures_lab4 as L4  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "round5"
CLEAN = ("2003-07-01", "2008-01-01")
SEARCH34 = L4.TRAIN                    # 2008-01-02 ~ 2016-12-31
W_C = L4.SEEN1                         # 2017-2020（已被看過）
W_D = L4.SEEN2                         # 2021 起（已被看過）


# ------------------------------------------------------------------ 帶成本換算的事件式引擎（逐字複製 futures_lab._sim，只把成本乘上 cm[i]）
def _make_sim_cm():
    src = inspect.getsource(F._sim.py_func)
    src = src[src.index("def _sim("):]
    head, body = src.split("\n", 1)
    head = head.replace("rollday):", "rollday, cm):")
    body = re.sub(r"\bslip\b", "(slip * cm[i])", body)
    body = re.sub(r"\bfee_pts\b", "(fee_pts * cm[i])", body)
    body = re.sub(r"\broll_pts\b", "(roll_pts * cm[i])", body)
    ns = {"np": np, "_put": F._put}
    exec(compile(head + "\n" + body, "<sim_cm>", "exec"), ns)
    return G.njit(ns["_sim"])


_sim_cm = _make_sim_cm()


# ------------------------------------------------------------------ 修正後的資料與 Lab
def adjusted_tx():
    raw = F.load_tx()
    d = F._rd("index_ohlc"); d["date"] = pd.to_datetime(d["date"])
    idx = raw.index
    tse = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date").close.reindex(idx).ffill()
    tr = tse.pct_change().to_numpy()
    c = raw["close"].to_numpy(); n = len(c)
    settle = F.settle_days(idx)
    k = np.ones(n)
    for i in np.where(settle)[0]:
        t = i + 1
        if t < n and np.isfinite(tr[t]):
            k[t] = (c[t] / c[t - 1]) / (1.0 + tr[t])
    fac = np.ones(n); acc = 1.0
    for j in range(n - 1, -1, -1):
        fac[j] = acc; acc *= k[j]
    adj = raw.copy()
    for col in ("open", "high", "low", "close"):
        adj[col] = raw[col].to_numpy() * fac
    return adj, raw, fac


_BASE_LAB = F.Lab
_load_tx_orig = F.load_tx


class FixedLab(_BASE_LAB):
    """F.Lab 的修正版：價格往回調整、成本按 fac 換算、基差用未調整價格。"""

    def __init__(self):
        super().__init__()
        raw = RAW["raw"]
        self.fac = RAW["fac"]
        self.raw_close = raw["close"].to_numpy()
        d = F._rd("index_ohlc"); d["date"] = pd.to_datetime(d["date"])
        tse = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date").close.reindex(self.idx).ffill()
        self.X["bas"] = ((raw["close"] - tse) / tse).rolling(5).mean().to_numpy()

    def run(self, p, allow_short, gl=None, gs=None, slip=F.SLIP_PTS):
        key = (tuple(sorted(p.items())), allow_short, None if gl is None else gl.tobytes(), None if gs is None else gs.tobytes(), slip)
        if key in self.cache:
            return self.cache[key]
        sl, ss, el, es = F.build_signals(p["fam"], p, self.X, allow_short)
        pnl, tr = _sim_cm(self.o, self.h, self.l, self.c, np.nan_to_num(self.atr, nan=1e9), sl, ss, el, es,
                          self.ones if gl is None else gl, self.ones if gs is None else gs, p["k"], self.fee_pts, F.TAX, slip,
                          F.ROLL_PTS, self.settle, self.fac)
        prev = np.roll(self.c, 1); prev[0] = self.c[0]
        r = pd.Series(pnl / prev, index=self.idx)
        tdf = pd.DataFrame(tr, columns=["dir", "sig_i", "entry_i", "exit_i", "entry_px", "exit_px", "reason", "pnl_pts", "mae_pts", "mfe_pts"])
        self.cache[key] = (r, tdf)
        return self.cache[key]


RAW = {}


@contextmanager
def fixed_world():
    adj, raw, fac = adjusted_tx()
    RAW.update(raw=raw, fac=fac)
    F.load_tx = lambda: adj
    F.Lab = FixedLab
    try:
        yield
    finally:
        F.load_tx = _load_tx_orig
        F.Lab = _BASE_LAB


class Lab5(L4.Lab4):
    """第四輪 Lab4 的修正版：事件式引擎與保證金引擎都用正確的成本換算。"""

    def __init__(self):
        with fixed_world():
            super().__init__()
        self.lab.fac = RAW["fac"]
        self.fixfac = RAW["fac"]
        self.rc = {}
        self.ao, self.ah, self.al = self.lab.o, self.lab.h, self.lab.l          # 已是調整後價格
        self.c = self.lab.c
        self.fac = np.ones(len(self.c))                                         # Lab4 內部的二次調整係數＝1（價格已經調整過）

    # 事件式（第二、三輪的 spec：W／D／gates／xit／k）
    def run(self, spec):
        key = json.dumps(spec, sort_keys=True, default=str)
        if key in self.rc:
            return self.rc[key]
        s = self.spec_state(spec) & self.atr_ok
        z = np.zeros(len(s), bool)
        gl = np.ones(len(s), bool)
        for gname in spec.get("gates", ()):
            gl &= self.gates[gname]
        el = ~s
        for xn in spec.get("xit", ()):
            el = el | self.xflags[xn]
        L = self.lab
        pnl, tr = _sim_cm(L.o, L.h, L.l, L.c, self.atr, s, z, el, z, gl, np.ones(len(s), bool), float(spec.get("k", 99.0)),
                          self.fee_pts, F.TAX, F.SLIP_PTS, F.ROLL_PTS, L.settle, self.fixfac)
        prev = np.roll(L.c, 1); prev[0] = L.c[0]
        r = pd.Series(pnl / prev, index=self.idx)
        t = pd.DataFrame(tr, columns=["dir", "sig_i", "entry_i", "exit_i", "entry_px", "exit_px", "reason", "pnl_pts", "mae_pts", "mfe_pts"])
        res = (L.lev_ret(r, 1.0), t)
        self.rc[key] = res
        return res

    # 保證金引擎（第四輪的 run_p 家族）：成本係數改成 fac（不是 1/fac）
    def run_t(self, tgt, fix=True):
        L = self.lab
        r, q, liq = L4._sim_lev_fx(L.o, L.h, L.l, L.c, tgt, L.settle, F.FEE_NTD, F.SLIP_PTS, F.TAX, F.ROLL_PTS,
                                   G.M_INIT, G.M_MAINT, L4.BAND, self.cash_d, G.E0, self.fixfac)
        r = pd.Series(r, index=self.idx)
        E = G.E0 * (1 + r).cumprod()
        expo = pd.Series(q * L.c * 200.0 / E.to_numpy(), index=self.idx)
        return r, expo, liq

    def gap_series(self, theta=0.015, w=0.5):
        L = self.lab
        sig = np.where(np.isnan(self.spx_night), False, self.spx_night <= -theta)
        r = np.zeros(len(L.c)); fl = np.zeros(len(L.c), bool)
        for i in np.where(sig)[0]:
            j = i + 1
            if j < len(L.c):
                cost = (2 * F.SLIP_PTS + 2 * F.FEE_NTD / 200.0) * self.fixfac[j] + 2 * F.TAX * L.o[j]
                r[j] = w * ((L.c[j] - L.o[j]) - cost) / L.c[i]
                fl[j] = True
        return pd.Series(r, index=self.idx), pd.Series(fl, index=self.idx)


# ------------------------------------------------------------------ 重跑第一～四輪（各輪各用一個新的 Lab，避免 VOTE 等快取互相污染）
def fp(x, d=1):
    return F.fmt(x, True, d)


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def rerun_r1():
    with fixed_world():
        fl = F.Lab()
    grid = F.build_grid()
    out = []
    for ver, sh in (("A只多", False), ("B多空", True)):
        for fam in [None] + list(F.GRIDS):
            segs = F.walk_forward(fl, grid, sh, [fam] if fam else None)
            nm = "全家族" if fam is None else fam
            row, rows, oos = F.row_for(fl, nm, ver, segs, grid, sh)
            out.append(dict(name=f"R1 {ver} {nm}", rnd=1, r=oos, expo=None, eligible=False, note="第一輪：訓練含 2001～2012、WF 測試 2013 起；搜尋期涵蓋 2003-07～2007，不是乾淨證據",
                            own=("2013 起 WF 樣本外", "2013-01-01", None), spec=None))
    return out


def rerun_r2():
    lab = Lab5()
    R = G.run_search(lab)
    out = []
    for nm, sp in (("優化版", R["champ"]), ("預設參數版", R["default"])):
        out.append(dict(name=f"R2 {nm}", rnd=2, r=lab.run(sp)[0], expo=None, eligible=False, note="第二輪：搜尋 2001～2018（含 2003-07～2007），保留期 2019 起",
                        own=("2019 起（第二輪原保留期）", "2019-01-01", None), spec=sp, label=G.spec_label(sp)))
    return out, lab, R


def rerun_r3():
    lab = Lab5()
    R = L3.run_search(lab)
    out = []
    for nm, sp in (("優化版", R["champ"]), ("預設參數版", R["default"])):
        out.append(dict(name=f"R3 {nm}", rnd=3, r=lab.run(sp)[0], expo=None, eligible=True, note="第三輪：搜尋 2008～2016，保留期 2017～2020",
                        own=("2017～2020（第三輪原保留期）", "2017-01-01", "2021-01-01"), spec=sp, label=L3.label3(sp),
                        gates=(sum(r["beat"] for r in R["wf_rows"]) > len(R["wf_rows"]) / 2, R["nb"][0] >= 2 / 3 if R["nb"][1] else False)))
    return out, lab, R


def rerun_r4():
    lab = Lab5()
    R = L4.run_search(lab)
    out = []
    for _, row in R["fam"].iterrows():
        p = row["_p"]
        r, e, l = lab.run_p(p)
        out.append(dict(name="R4 " + row["危險訊號組合"], rnd=4, r=r, expo=e, eligible=True, note="第四輪：搜尋 2008～2016，平均曝險 <= 1.2",
                        own=None, spec=p, label=L4.pstr(p), gates=(bool(row["關卡1"]), bool(row["關卡2"])), search_expo=row["平均曝險"]))
    return out, lab, R


def baselines(lab):
    out = []
    for nm, lev in (("基準 台指期持有1x(修正)", 1.0), ("基準 台指期持有1.2x(修正)", 1.2)):
        r, e, l = lab.hold(lev)
        out.append(dict(name=nm, rnd=0, r=r, expo=e, eligible=False, note="永遠持有，不是策略", own=None, spec=None, label=nm))
    return out


# ------------------------------------------------------------------ 揭露（只一次）：所有候選在各視窗的數字
def win_stats(c, a, b):
    r = c["r"]
    x = r[(r.index >= pd.Timestamp(a)) & ((r.index < pd.Timestamp(b)) if b else True)]
    if len(x) < 40:
        return None
    s = F.stats(x)
    s["avg_expo"] = None
    if c.get("expo") is not None:
        e = c["expo"][(c["expo"].index >= pd.Timestamp(a)) & ((c["expo"].index < pd.Timestamp(b)) if b else True)]
        s["avg_expo"] = float(e.mean())
    return s


def reveal(cands, lab, lab4):
    lock = OUT / "_reveal_done.json"
    if lock.exists():
        raise RuntimeError("第五輪的揭露已經做過一次，依規則不再重跑")
    wins = {"clean": CLEAN, "search": SEARCH34, "C": W_C, "D": W_D}
    res = {"0050": {k: lab.b50(*v) for k, v in wins.items()}, "cands": {}, "gap": {}}
    for c in cands:
        d = {k: win_stats(c, *v) for k, v in wins.items()}
        if c.get("own"):
            d["own"] = win_stats(c, c["own"][1], c["own"][2]); d["own_name"] = c["own"][0]
            d["own_b50"] = lab.b50(c["own"][1], c["own"][2])
        res["cands"][c["name"]] = dict(rnd=c["rnd"], eligible=c["eligible"], note=c["note"], label=c.get("label", ""), gates=c.get("gates"), wins=d)
    # 跳空回補日內單（美股前一晚 S&P 跌 >=1.5%，隔日開盤買、同日收盤賣）：單獨看每個視窗的每筆淨報酬與 t 值
    gr, gf = lab4.gap_series(0.015, 1.0)
    for k, (a, b) in {"clean": CLEAN, **{k: v for k, v in wins.items() if k != "clean"}}.items():
        m = (gr.index >= pd.Timestamp(a)) & ((gr.index < pd.Timestamp(b)) if b else True) & gf.to_numpy()
        x = gr[m]
        res["gap"][k] = dict(n=int(len(x)), mean=float(x.mean()) if len(x) else None,
                             t=float(x.mean() / x.std() * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else None, win=float((x > 0).mean()) if len(x) else None)
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


def collect_all():
    cands = rerun_r1()
    c2, lab2, R2 = rerun_r2(); cands += c2
    c3, lab3, R3 = rerun_r3(); cands += c3
    c4, lab4, R4 = rerun_r4(); cands += c4
    cands += baselines(lab4)
    # 跳空日內單的組合實驗：第四輪過關卡的家族＋T+SM，各自 gap=0／1 兩版（gap 以外參數相同）
    fam = R4["fam"]
    pick = [r for _, r in fam.iterrows() if (r["關卡1"] and r["關卡2"]) or r["危險訊號組合"] == "T+SM"]
    for r in pick:
        for g in (0, 1):
            p = dict(r["_p"]); p["gap"] = g
            rr, ee, ll = lab4.run_p(p)
            cands.append(dict(name=f"組合 {r['危險訊號組合']} gap={g}", rnd=4, r=rr, expo=ee, eligible=False, note="跳空日內單組合實驗（只改 gap 開關）", own=None, spec=p, label=L4.pstr(p)))
    return cands, dict(lab2=lab2, lab3=lab3, lab4=lab4, R2=R2, R3=R3, R4=R4)


def dist_rows(V):
    b = V["0050"]
    rows = []
    for nm, c in V["cands"].items():
        w = c["wins"]
        d = {}
        for k in ("clean", "search", "C", "D"):
            s = w.get(k)
            d[k] = None if s is None else s["cagr"] - b[k]["cagr"]
        avail = [d[k] for k in ("clean", "C", "D") if d[k] is not None]
        own = None
        if w.get("own") and w.get("own_b50"):
            own = w["own"]["cagr"] - w["own_b50"]["cagr"]
        rows.append(dict(name=nm, rnd=c["rnd"], eligible=c["eligible"], d=d, own=own, worst=min(avail) if avail else None,
                         mean=float(np.mean(avail)) if avail else None, wins_all=(d["clean"] is not None and all(x is not None and x > 0 for x in (d["clean"], d["C"], d["D"]))),
                         expo=[(w[k] or {}).get("avg_expo") for k in ("search", "C", "D")], gates=c.get("gates"), label=c.get("label")))
    return rows


def write_docs(cands, ctx, V):
    b = V["0050"]
    rows = dist_rows(V)
    ppt = lambda x: "-" if x is None else f"{x * 100:+.1f}"
    for r in rows:
        r["label"] = (r["label"] or "").replace("|", "／")
    L = ["# 台指期第五輪：修正換月跳點後，重跑第一～四輪並依「離 0050 差幾個百分點」排序\n"]
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。淘汰規則：年化輸同期含息扣成本的 0050 -> 淘汰。\n")
    L.append("> **修正**：第四輪發現的換月跳點偏誤已套用到所有引擎（第一～四輪全部重跑），成本換算係數方向也改正了（第四輪用反，早期成本被高估）。"
             "各輪的保留期鎖檔一律沒動；本輪重算後的保留期段只揭露一次（`_reveal_done.json`），**2017～2020 與 2021 起都已被看過**。\n")
    L.append("> **乾淨證據**：2003-07～2007 從未用於第三、四輪的選參（第一、二輪的搜尋期含這段，所以第一、二輪候選不算乾淨）。"
             "**揭露**：第四輪曾對 W、T+SM 兩個候選與持有基準看過這段一次（`round4/_backcheck_done.json`）；本輪重新選出的候選（含新家族冠軍）才算第一次看，W、T+SM 的這段數字已不是全新。\n")
    # 0 冠軍判定
    champs = [r for r in rows if r["eligible"] and r["wins_all"]]
    L.append("## 〇、冠軍判定（三段都要贏 0050：2003-07～2007、2017～2020、2021 起；候選須在 2008～2016 選出）\n")
    L.append(f"0050 含息扣成本年化：2003-07～2007 {fp(b['clean']['cagr'])}、2008～2016 {fp(b['search']['cagr'])}、2017～2020 {fp(b['C']['cagr'])}、2021 起 {fp(b['D']['cagr'])}。\n")
    L.append(f"**結論：{('有冠軍：' + '、'.join(r['name'] for r in champs)) if champs else '沒有冠軍'}。**共揭露 {len(rows)} 個候選（多重比較風險：這麼多候選裡即使有一個三段都贏，也要打折看待）。\n")
    elig = sorted([r for r in rows if r["eligible"]], key=lambda r: -(r["worst"] if r["worst"] is not None else -9))
    t = []
    for r in elig:
        t.append({"候選": r["name"], "參數": r["label"], "搜尋關卡(WF/鄰域)": ("過/過" if r["gates"] and r["gates"][0] and r["gates"][1] else "未全過" if r["gates"] else "-"),
                  "2003-07～2007 差距(點)": ppt(r["d"]["clean"]), "2017～2020 差距(點)": ppt(r["d"]["C"]), "2021 起 差距(點)": ppt(r["d"]["D"]),
                  "最差一段(點)": ppt(r["worst"]), "平均曝險 搜尋／C／D": "／".join("-" if x is None else f"{x:.2f}" for x in r["expo"]),
                  "判定": "**冠軍**" if r["wins_all"] else "淘汰"})
    L.append(md(pd.DataFrame(t)))
    if elig:
        n0 = elig[0]
        L.append(f"離 0050 最近的是 **{n0['name']}**：三段差距 {ppt(n0['d']['clean'])}／{ppt(n0['d']['C'])}／{ppt(n0['d']['D'])} 個百分點，最差一段 {ppt(n0['worst'])}；"
                 "它的搜尋期優勢（+8.7 點）在 2017 年後消失，2017 起兩段都小輸，原因沒有拆解（未驗證）。\n")
    # 1 全部距離
    L.append("## 一、所有候選離 0050 的距離（差距＝候選年化 - 0050 年化，單位百分點；依『最差一段』由近到遠排序）\n")
    L.append("包含第一、二輪的候選（其搜尋期含 2003-07～2007，不是乾淨證據；R1 只有 2013 起的 walk-forward 樣本外，R2 的原保留期是 2019 起）與基準對照。空白＝該視窗沒有資料或不適用。\n")
    t = []
    for r in sorted(rows, key=lambda r: -(r["worst"] if r["worst"] is not None else -9)):
        t.append({"候選": r["name"], "輪": r["rnd"] or "基準", "2003-07～2007": ppt(r["d"]["clean"]), "2008～2016": ppt(r["d"]["search"]), "2017～2020": ppt(r["d"]["C"]),
                  "2021 起": ppt(r["d"]["D"]), "各輪原保留／樣本外": ppt(r["own"]), "最差一段": ppt(r["worst"]), "平均": ppt(r["mean"])})
    L.append(md(pd.DataFrame(t)))
    # 2 修正影響
    L.append("## 二、修正的影響（永遠持有 1 倍；第四輪與本輪的差別是成本係數）\n")
    h = {r["name"]: r for r in rows}
    t = []
    for nm in ("基準 台指期持有1x(修正)", "基準 台指期持有1.2x(修正)"):
        w = V["cands"][nm]["wins"]
        t.append({"口徑": nm, "2003-07～2007": fp(w["clean"]["cagr"]), "2008～2016": fp(w["search"]["cagr"]), "2017～2020": fp(w["C"]["cagr"]), "2021 起": fp(w["D"]["cagr"])})
    t.append({"口徑": "0050（含息扣成本）", "2003-07～2007": fp(b["clean"]["cagr"]), "2008～2016": fp(b["search"]["cagr"]), "2017～2020": fp(b["C"]["cagr"]), "2021 起": fp(b["D"]["cagr"])})
    t.append({"口徑": "（對照）第四輪報告：持有 1x（成本係數用反）", "2003-07～2007": "12.5%", "2008～2016": "3.7%", "2017～2020": "18.0%", "2021 起": "23.2%"})
    t.append({"口徑": "（對照）第一～三輪口徑（未修正換月）", "2003-07～2007": "-", "2008～2016": "1.3%", "2017～2020": "12.3%", "2021 起": "21.8%"})
    L.append(md(pd.DataFrame(t)))
    # 3 gap
    g = V["gap"]
    L.append("## 三、跳空日內單（美股前一晚 S&P 跌 >= 1.5%，隔日開盤買、同日收盤賣；每筆淨報酬，已扣兩腳滑價／手續費／期交稅）\n")
    gt = [{"視窗": nm, "筆數": g[k]["n"], "每筆平均淨報酬": "-" if g[k]["mean"] is None else f"{g[k]['mean'] * 100:.2f}%", "t 值": "-" if g[k]["t"] is None else f"{g[k]['t']:.2f}",
           "勝率": "-" if g[k]["win"] is None else fp(g[k]["win"], 0)} for k, nm in (("clean", "2003-07～2007（無美股資料）"), ("search", "2008～2016（搜尋期）"), ("C", "2017～2020（已被看過）"), ("D", "2021 起（已被看過）"))]
    L.append(md(pd.DataFrame(gt)))
    if g["search"]["t"] and g["C"]["t"] is not None and g["D"]["t"] is not None:
        L.append(f"**這個訊號只在搜尋期有統計意義**：搜尋期 t 值 {g['search']['t']:.2f}，到 2017～2020 降成 {g['C']['t']:.2f}、2021 起降成 {g['D']['t']:.2f}（每筆淨報酬 {g['search']['mean'] * 100:.2f}% -> {g['C']['mean'] * 100:.2f}% -> {g['D']['mean'] * 100:.2f}%）。"
                 "搜尋期含 2008 金融海嘯的大跌後反彈，可能是特例；也可能是這類美股前一晚訊號已被廣泛利用而衰退。結論：**不能當穩定的加掛模組**。\n")
    L.append("**資料限制**：資料湖的美股資料（intl_daily）2008-01 才開始，**2003～2007 沒有任何美股前一晚的資料，無法用乾淨期驗證這個訊號**（本容器對 Yahoo／FRED／FinMind 出口被擋、也沒有其他美股來源）。"
             "所以它只能用 2017 起（已被看過）的樣本交叉驗證，不算乾淨證據。\n")
    L.append("**加掛模組的組合效果**（同一個策略，只改 gap 開關；2003-07～2007 因為沒有美股資料，兩者相同）：\n")
    t = []
    for nm in sorted(n for n in V["cands"] if n.startswith("組合")):
        w = V["cands"][nm]["wins"]
        t.append({"組合": nm, "2003-07～2007": ppt(w["clean"]["cagr"] - b["clean"]["cagr"]) if w["clean"] else "-", "2008～2016": ppt(w["search"]["cagr"] - b["search"]["cagr"]),
                  "2017～2020": ppt(w["C"]["cagr"] - b["C"]["cagr"]), "2021 起": ppt(w["D"]["cagr"] - b["D"]["cagr"])})
    L.append("（表中數字為『相對 0050 的差距，百分點』）\n\n" + md(pd.DataFrame(t)))
    inc = {k: [] for k in ("search", "C", "D")}
    for nm in V["cands"]:
        if nm.startswith("組合") and nm.endswith("gap=1"):
            n0 = nm[:-1] + "0"
            for k in inc:
                w1, w0 = V["cands"][nm]["wins"].get(k), V["cands"][n0]["wins"].get(k)
                if w1 and w0:
                    inc[k].append(w1["cagr"] - w0["cagr"])
    L.append("加掛跳空日內單的平均增益（組合數 %d，gap=1 減 gap=0，年化百分點）：2008～2016 %s、2017～2020 %s、2021 起 %s。\n" % (
        len(inc["search"]), ppt(np.mean(inc["search"])), ppt(np.mean(inc["C"])), ppt(np.mean(inc["D"]))))
    # 4 各輪摘要
    R2, R3, R4 = ctx["R2"], ctx["R3"], ctx["R4"]
    L.append("## 四、各輪重跑摘要（修正引擎）\n")
    L.append(f"- 第二輪（搜尋 2001～2018）：採用濾網 {'、'.join(R2['acc']) or '無'}；優化版 `{G.spec_label(R2['champ'])}`。\n"
             f"- 第三輪（搜尋 2008～2016）：採用進場濾網 {'、'.join(R3['acc_e']) or '無'}、出場 {'、'.join(R3['acc_x']) or '無'}；優化版 `{L3.label3(R3['champ'])}`；WF 贏 {sum(r['beat'] for r in R3['wf_rows'])}/{len(R3['wf_rows'])} 段、鄰域贏 0050 比例 {fp(R3['nb'][0], 0)}。\n")
    ft = R4["fam"].drop(columns=["_p", "_wf"]).copy()
    for c in ("搜尋期年化", "搜尋期回撤", "持倉日占比", "鄰域贏0050比例"):
        ft[c] = ft[c].map(fp)
    ft["平均曝險"] = ft["平均曝險"].map(lambda x: f"{x:.2f}"); ft["Calmar"] = ft["Calmar"].map(lambda x: f"{x:.2f}")
    ft["關卡1"] = ft["關卡1"].map(lambda x: "過" if x else "未過"); ft["關卡2"] = ft["關卡2"].map(lambda x: "過" if x else "未過")
    L.append("- 第四輪各家族冠軍（搜尋 2008～2016，平均曝險 <= 1.2）：\n\n" + md(ft))
    L.append("## 五、逐段筆記\n")
    notes = []
    top = [r for r in elig][:3]
    lab4 = ctx["lab4"]
    for r in top:
        c = next(x for x in cands if x["name"] == r["name"])
        if c["rnd"] == 4 and c["spec"] is not None:
            for per, (a, z) in (("乾淨2003-07～2007", CLEAN), ("搜尋期2008-16", SEARCH34), ("已看過2017-20", W_C), ("已看過2021起", W_D)):
                notes.append(L4.episodes(lab4, c["spec"], a, z, tag=f"{r['name']}／{per}"))
    if notes:
        nt = pd.concat(notes)
        nt.to_csv(OUT / "trades_round5.csv", index=False, encoding="utf-8-sig")
        N = ["# 台指期第五輪逐段筆記（離 0050 最近的前三個候選；持有與空手期間）\n"]
        for tag, gg in nt.groupby("版本", sort=False):
            N.append(f"\n## {tag}（{len(gg)} 段）\n")
            for _, x in gg.iterrows():
                N.append(f"- **{x['類型']} {x['開始']} ～ {x['結束']}**（{x['天數']} 天）｜策略 {x['策略報酬']:.2%}｜指數 {x['指數報酬']:.2%}" + (f"｜觸發旗標 {x['觸發旗標']}" if x['觸發旗標'] else "") + f"｜**檢討**：{x['事後檢討']}")
        (OUT / "trades_notes_round5.md").write_text("\n".join(N), encoding="utf-8")
        L.append(f"離 0050 最近的前三個候選（{'、'.join(r['name'] for r in top)}）的持有與空手段落筆記見 `trades_notes_round5.md`、`trades_round5.csv`（共 {len(nt)} 段）。\n")
    n2 = len(pd.read_csv(OUT / "registry_r2.csv")); n3 = len(pd.read_csv(OUT / "registry_r3.csv")); n4 = len(pd.read_csv(OUT / "registry_r4.csv"))
    L.append(f"**試了幾組（重跑）**：第一輪 {len(F.build_grid())} 組格點 x A／B 兩版 x 8 個家族選項（WF 重選另計）；第二輪登記 {n2} 組；第三輪 {n3} 組；第四輪 {n4} 組；跳空組合實驗 8 組；"
             "逐組登記在 `registry_r2.csv`、`registry_r3.csv`、`registry_r4.csv`（第一輪格點定義在 `futures_lab.py`）。\n")
    L.append("## 六、限制\n")
    L.append("- **含 V（VIX）、U（美股前一晚）、FN（外資現貨，2012 起）旗標的家族，在 2003-07～2007 這些旗標沒有資料、永遠不觸發**，該期等於另一種策略（例如 R4 V 在乾淨期＝永遠持有 1.2 倍，+3.6 與持有 1.2x 基準相同）；這類家族的乾淨期成績要打折。\n")
    L.append("- 揭露候選很多（第一～四輪重跑、四個窗口），即使有候選三段都贏，多重比較風險仍大；若出現冠軍，應再等新資料（2027 之後）做真正的樣本外。\n"
             "- 換月修正用現貨日報酬近似；結算日當天的差異保守保留；保證金與資金利息為假設；2003～2007 沒有美股／VIX 資料（相關旗標不觸發）。\n"
             "- 第一、二輪候選的搜尋期含 2003-07～2007，不能拿這段當乾淨證據；2017 起兩段在第二～四輪都被看過。\n"
             "- opt_pc（選擇權 P/C）本輪未用（由資料專家另外實測）。\n")
    L.append("## 七、重現\n\n`python -m pipeline.compute.futures_lab5`（約 8 分鐘，包含第一～四輪全部重跑）；揭露鎖檔存在時直接讀取。測試：`pytest tests/test_futures_lab5.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cands, ctx = collect_all()
    lock = OUT / "_reveal_done.json"
    V = json.loads(lock.read_text(encoding="utf-8")) if lock.exists() else reveal(cands, ctx["lab4"], ctx["lab4"])
    reg = []
    for c in cands:
        reg.append(dict(候選=c["name"], 輪=c["rnd"], 參數=c.get("label", "")))
    pd.DataFrame(reg).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ctx["lab2"].registry).drop_duplicates(subset=["階段", "策略"]).to_csv(OUT / "registry_r2.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ctx["R3"]["registry"]).drop_duplicates(subset=["階段", "策略"]).to_csv(OUT / "registry_r3.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ctx["R4"]["reg"]).to_csv(OUT / "registry_r4.csv", index=False, encoding="utf-8-sig")
    write_docs(cands, ctx, V)
    return cands, ctx, V


if __name__ == "__main__":
    main()
