"""台指期第三輪：補測 NHI 與 JA，並把美股消息面（S&P／Nasdaq／SOX／VIX／TSM ADR 溢價／美元指數）與外資期貨淨部位
當成濾網或出場加分，疊在階段 1、2 的指標上。主結果 1 倍曝險、只做多。

資料切法（Andy 指示，因為 2019 起已在前兩輪被看過、不再算乾淨證據）
  * 搜尋與選參：2008-01-02～2016-12-31。
  * 內部保留期：2017-01-01～2020-12-31，只准跑一次（final_holdout 寫鎖檔，再呼叫拒絕）。
  * 2021 起：同一次執行一併列出，但**標註「已被看過」，不當證據**。
  * 外資期貨 fut_inst 只有 2018-06 起，搜尋期完全沒有它——只能當一條事先固定的規則（5 日淨部位變化 >= 0）放進保留期一次驗，樣本短、另外標明。

美股時間線（已實測驗證）：美股日期 d 的收盤，在台灣時間 d+1 清晨，早於台指期 d+1 的開盤。
所以「訊號日 i（台灣日期 d）收盤後，隔日開盤進場」時，可以合法使用「美股日期 d 的收盤」——它在開盤前就已知。
實測：美股日期 d 的 S&P 漲跌與台指期隔日開盤跳空相關 0.60；錯置一天只剩 0.08。
出場版（XS／XV）同理：隔日開盤前就知道美股大跌或 VIX 暴衝，開盤出場。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402
from pipeline.compute import futures_lab2 as G  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "round3"
TRAIN = ("2008-01-02", "2017-01-01")
HOLD = ("2017-01-01", "2021-01-01")
SEEN = "2021-01-01"
WF_TEST = ["2011-01-01", "2013-01-01", "2015-01-01"]
WF_END = "2017-01-01"

ENTRY_FACTORS = {
    "S": "結算週不開新倉", "JA": "7～8 月（除權息旺季）不開新倉", "BA": "基差深度逆價差(<-0.3%)不開新倉",
    "RV": "已實現波動>25% 不開新倉", "BC": "只在基差<=0 時開新倉",
    "U_SPX": "前一晚 S&P 500 跌幅 >1% 不開新倉", "U_IXIC": "前一晚 Nasdaq 跌幅 >1% 不開新倉",
    "U_SOX": "前一晚費半 SOX 跌幅 >2% 不開新倉", "U_SPXT": "S&P 500 在 50 日均線之上才開新倉",
    "U_SOXT": "費半 SOX 在 50 日均線之上才開新倉", "U_VIXL": "VIX <= 25 才開新倉", "U_VIXC": "前一晚 VIX 單日漲幅 > 15% 不開新倉",
    "U_ADR": "TSM ADR 溢價 >= -0.5% 才開新倉", "U_DXY": "美元指數 5 日漲幅 > 1% 不開新倉",
}
EXIT_FACTORS = {"XS": "前一晚 S&P 500 跌幅 >= 2% -> 隔日開盤出場", "XV": "前一晚 VIX 單日漲幅 >= 25% -> 隔日開盤出場"}


def _rd(t, cols=None):
    import glob
    return pd.concat([pd.read_parquet(f, columns=cols) for f in glob.glob(str(ROOT / "data" / t / "**" / "*.parquet"), recursive=True)], ignore_index=True)


class Lab3(G.Lab2):
    def __init__(self):
        super().__init__()
        idx = self.idx
        u = _rd("intl_daily"); u["date"] = pd.to_datetime(u["date"])
        self.us_ok = True

        def asof(sym):
            s = u[u.symbol == sym].drop_duplicates("date").set_index("date").close.sort_index()
            return s.reindex(idx, method="ffill")
        self.us = {k: asof(v) for k, v in dict(spx="^GSPC", ixic="^IXIC", sox="^SOX", vix="^VIX", tsm="TSM", dxy="DX-Y.NYB", twd="TWD=X").items()}
        p = _rd("price_daily", ["date", "code", "close"]); p = p[p.code == "2330"].drop_duplicates("date")
        c2330 = p.assign(date=pd.to_datetime(p.date)).set_index("date").close.reindex(idx)
        us = self.us
        prem = us["tsm"] * us["twd"] / 5.0 / c2330 - 1.0
        r = lambda s: s.pct_change().to_numpy()
        nz = lambda a: np.where(np.isnan(a), True, a)                 # 缺值（2008 前）視為不濾
        g = self.gates
        g["U_SPX"] = nz(~(r(us["spx"]) < -0.01)); g["U_IXIC"] = nz(~(r(us["ixic"]) < -0.01)); g["U_SOX"] = nz(~(r(us["sox"]) < -0.02))
        for key, sym in (("U_SPXT", "spx"), ("U_SOXT", "sox")):
            ma = us[sym].rolling(50).mean()
            g[key] = np.where(ma.isna().to_numpy(), True, (us[sym] > ma).to_numpy())
        g["U_VIXL"] = nz(~(us["vix"].to_numpy() > 25)); g["U_VIXC"] = nz(~(r(us["vix"]) > 0.15))
        g["U_ADR"] = nz(~(prem.to_numpy() < -0.005)); g["U_DXY"] = nz(~(us["dxy"].pct_change(5).to_numpy() > 0.01))
        net = F.foreign_net_oi(idx); chg = (net - net.shift(5)).to_numpy()
        g["C_FOR"] = np.where(np.isnan(chg), True, chg >= 0)
        for k in list(g):
            g[k] = np.asarray(g[k], bool)
        self.xflags = {"XS": np.nan_to_num(r(us["spx"]), nan=0.0) <= -0.02, "XV": np.nan_to_num(r(us["vix"]), nan=0.0) >= 0.25}
        self.prem = prem
        self.us_night = {k: r(us[k]) for k in ("spx", "ixic", "sox", "vix")}

    def add_score_gate(self, names):
        """加減分：採用的進場濾網中，通過數 >= 總數 - 1 才開新倉。"""
        if len(names) >= 3:
            sc = sum(self.gates[n].astype(int) for n in names)
            self.gates["SCORE"] = sc >= len(names) - 1

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
        pnl, tr = F._sim(L.o, L.h, L.l, L.c, self.atr, s, z, el, z, gl, np.ones(len(s), bool),
                         float(spec.get("k", 99.0)), self.fee_pts, F.TAX, F.SLIP_PTS, F.ROLL_PTS, L.settle)
        prev = np.roll(L.c, 1); prev[0] = L.c[0]
        r = pd.Series(pnl / prev, index=self.idx)
        t = pd.DataFrame(tr, columns=["dir", "sig_i", "entry_i", "exit_i", "entry_px", "exit_px", "reason", "pnl_pts", "mae_pts", "mfe_pts"])
        res = (L.lev_ret(r, 1.0), t)
        self.rc[key] = res
        return res


def label3(sp):
    return G.spec_label(sp) + (f" | 美股出場{'+'.join(sp['xit'])}" if sp.get("xit") else "")


# ------------------------------------------------------------------ 階段 1（2008～2016）
def phase1(lab):
    a, b = TRAIN
    b50 = lab.b50(a, b); txh = F.stats(G.sl(lab.tx_hold(), a, b))
    rows = []
    for name, sp in G.SPEC.items():
        if name == "VOTE":
            continue
        for tf in ("D", "W"):
            if sp[tf] is None:
                continue
            spec = {tf: (name, sp[tf]), "k": 99.0}
            m = G.metrics(lab, spec, a, b)
            if m["n"] == 0:
                continue
            rows.append(dict(指標=G.NAMES[name], 代號=name, 週期="日K" if tf == "D" else "週K", 預設參數=",".join(f"{k}={v}" for k, v in sp[tf].items()),
                             年化=m["cagr"], 回撤=m["mdd"], 夏普=m["sharpe"], 勝率=m["win"], 賺賠比=m["payoff"], 交易數=m["n"], 持倉比=m["expo"],
                             贏0050=m["cagr"] >= b50["cagr"], _spec=spec, _tf=tf, _name=name))
    return pd.DataFrame(rows), b50, txh


def phase2(lab, bases, factors, exit_mode=False):
    a, b = TRAIN
    rows = []
    for fname, desc in factors.items():
        better = 0; dc = []; dd = []; dw = []
        for bs in bases:
            m0 = G.metrics(lab, bs["_spec"], a, b)
            sp = dict(bs["_spec"])
            if exit_mode:
                sp["xit"] = (fname,)
            else:
                sp["gates"] = (fname,)
            m1 = G.metrics(lab, sp, a, b)
            c0 = m0["cagr"] / max(abs(m0["mdd"]), 1e-6); c1 = m1["cagr"] / max(abs(m1["mdd"]), 1e-6)
            better += c1 > c0 + 1e-9
            dc.append(m1["cagr"] - m0["cagr"]); dd.append(m1["mdd"] - m0["mdd"]); dw.append((m1["win"] or 0) - (m0["win"] or 0))
        rows.append(dict(濾網=fname, 說明=desc, 變好比例=f"{better}/{len(bases)}", 平均年化變化=np.mean(dc), 平均回撤變化=np.mean(dd),
                         平均勝率變化=np.mean(dw), 採用=better > len(bases) / 2))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 階段 3
def build_space3(lab, wn, dn, gate_opts, xit_opts):
    wopts = [None] + [(n, p) for n in wn for p in G.grid_of(G.SPEC[n]["gW"])]
    dopts = [None] + [(n, p) for n in dn for p in G.grid_of(G.SPEC[n]["gD"])]
    out = []
    for w in wopts:
        for d in dopts:
            if w is None and d is None:
                continue
            for g in gate_opts:
                for x in xit_opts:
                    for k in (3.0, 5.0, 99.0):
                        out.append(dict(W=w, D=d, gates=tuple(g), xit=tuple(x), k=k))
    return out, wopts, dopts


def score3(lab, spec, t0, a):
    m = G.metrics(lab, spec, t0, a); bb = lab.b50(t0, a)
    return m["cagr"] if m["mdd"] >= bb["mdd"] else -1 + m["mdd"]


def select3(lab, space, t0, a):
    best, bs = None, -9
    for sp in space:
        sc = score3(lab, sp, t0, a)
        if sc > bs:
            best, bs = sp, sc
    return best, bs


def wf3(lab, space):
    ends = WF_TEST[1:] + [WF_END]
    rows, parts = [], []
    for a, b in zip(WF_TEST, ends):
        sp, tr = select3(lab, space, TRAIN[0], a)
        m = G.metrics(lab, sp, a, b); bb = lab.b50(a, b)
        rows.append(dict(a=a, b=b, spec=sp, train=tr, cagr=m["cagr"], mdd=m["mdd"], b50=bb["cagr"], b50mdd=bb["mdd"], beat=m["cagr"] >= bb["cagr"], n=m["n"]))
        parts.append(G.sl(lab.run(sp)[0], a, b))
    return rows, pd.concat(parts)


def neighbors3(sp, gate_opts, xit_opts):
    res = list(G.neighbors(sp, None, None, [tuple(g) for g in gate_opts]))
    xl = [tuple(x) for x in xit_opts]
    if tuple(sp.get("xit", ())) in xl:
        i = xl.index(tuple(sp.get("xit", ())))
        for j in (i - 1, i + 1):
            if 0 <= j < len(xl):
                q = dict(sp); q["xit"] = xl[j]; res.append(q)
    return res


def final_holdout(lab, specs):
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        raise RuntimeError("內部保留期已經跑過一次，依規則不得再跑：" + lock.read_text(encoding="utf-8")[:200])
    res = {"0050_保留期": lab.b50(*HOLD), "0050_已看過": lab.b50(SEEN), "TX持有_保留期": F.stats(G.sl(lab.tx_hold(), *HOLD)),
           "TX持有_已看過": F.stats(G.sl(lab.tx_hold(), SEEN)), "策略": {}}
    for nm, sp in specs.items():
        mh = G.metrics(lab, sp, *HOLD); ms = G.metrics(lab, sp, SEEN)
        r, t = lab.run(sp)
        yrs = {}
        for y in range(2017, 2027):
            x = G.sl(r, f"{y}-01-01", f"{y + 1}-01-01")
            if len(x) > 20:
                yrs[y] = float((1 + x).prod() - 1)
        res["策略"][nm] = dict(label=label3(sp), 保留期=mh, 已看過=ms, 年度=yrs,
                              通過=bool(mh["cagr"] > res["0050_保留期"]["cagr"] and mh["mdd"] >= res["0050_保留期"]["mdd"]))
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


# ------------------------------------------------------------------ 主流程
def fp(x, d=1):
    return F.fmt(x, True, d)


def fn(x, d=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def run_search(lab):
    reg = []
    df, b50, txh = phase1(lab)
    dw = df[df._tf == "D"].sort_values("夏普", ascending=False).head(5)
    ww = df[df._tf == "W"].sort_values("夏普", ascending=False).head(3)
    bases = [r for _, r in pd.concat([dw, ww]).iterrows()]
    for _, r in df.iterrows():
        reg.append(dict(階段="1 單一指標", 策略=f"{r.代號}[{r.週期}]", 年化=r.年化, 回撤=r.回撤, 交易數=r.交易數))
    p2e = phase2(lab, bases, ENTRY_FACTORS, False)
    p2x = phase2(lab, bases, EXIT_FACTORS, True)
    for t in (p2e, p2x):
        for _, r in t.iterrows():
            reg.append(dict(階段="2 濾網", 策略=r.濾網, 年化=r.平均年化變化, 回撤=r.平均回撤變化, 交易數=len(bases)))
    acc_e = [g for g, a in zip(p2e.濾網, p2e.採用) if a]; acc_x = [g for g, a in zip(p2x.濾網, p2x.採用) if a]
    lab.vote_names = list(dw.代號)
    lab.add_score_gate(acc_e)
    gate_opts = [()] + [(g,) for g in acc_e] + ([tuple(acc_e)] if len(acc_e) > 1 else []) + ([("SCORE",)] if "SCORE" in lab.gates and len(acc_e) >= 3 else [])
    xit_opts = [()] + ([tuple(acc_x)] if acc_x else [])
    space, wo, do = build_space3(lab, list(ww.代號), list(dw.代號) + ["VOTE"], gate_opts, xit_opts)
    rows, oos = wf3(lab, space)
    ch, sc = select3(lab, space, TRAIN[0], TRAIN[1])
    for sp in space:
        m = G.metrics(lab, sp, *TRAIN)
        reg.append(dict(階段="3 組合優化", 策略=label3(sp), 年化=m["cagr"], 回撤=m["mdd"], 交易數=m["n"]))
    # 鄰域
    bb = lab.b50(*TRAIN)
    nbs = [G.metrics(lab, q, *TRAIN) for q in neighbors3(ch, gate_opts, xit_opts)]
    nb = (float(np.mean([m["cagr"] >= bb["cagr"] for m in nbs])) if nbs else np.nan, len(nbs), float(np.median([m["cagr"] for m in nbs])) if nbs else np.nan)
    dv = G.default_version(ch)
    dv["xit"] = ch.get("xit", ())
    s1 = df.sort_values("夏普", ascending=False).iloc[0]
    sp1 = s1["_spec"]
    sp2 = dict(sp1); sp2["gates"] = tuple(acc_e); sp2["xit"] = tuple(acc_x)
    chip = dict(ch); chip["gates"] = tuple(ch.get("gates", ())) + ("C_FOR",)
    return dict(df=df, b50=b50, txh=txh, bases=bases, p2e=p2e, p2x=p2x, acc_e=acc_e, acc_x=acc_x, space_n=len(space), wf_rows=rows,
                wf_oos=oos, champ=ch, default=dv, nb=nb, s1=s1, sp1=sp1, sp2=sp2, chip=chip, registry=reg, dw=dw, ww=ww)


def main(do_holdout=False):
    OUT.mkdir(parents=True, exist_ok=True)
    lab = Lab3()
    R = run_search(lab)
    ch = R["champ"]; wins = sum(r["beat"] for r in R["wf_rows"])
    print("採用進場濾網", R["acc_e"], "出場", R["acc_x"], "| 組合空間", R["space_n"])
    print("WF 贏段", wins, "/", len(R["wf_rows"]), "鄰域", R["nb"], "冠軍", label3(ch))
    print("優化版搜尋期", G.metrics(lab, ch, *TRAIN)["cagr"], "預設版", G.metrics(lab, R["default"], *TRAIN)["cagr"], "0050", R["b50"]["cagr"])
    pd.DataFrame(R["registry"]).drop_duplicates(subset=["階段", "策略"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    if not do_holdout:
        return lab, R, None
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        H = json.loads(lock.read_text(encoding="utf-8"))
    else:
        specs = {"優化版": ch, "預設參數版": R["default"], "優化版＋外資期貨濾網": R["chip"], "階段1最佳單一指標": R["sp1"], "階段2最佳單一＋濾網": R["sp2"]}
        H = final_holdout(lab, specs)
    write_docs(lab, R, H)
    return lab, R, H


# ------------------------------------------------------------------ 文件
def write_docs(lab, R, H):
    hb, hs = H["0050_保留期"], H["0050_已看過"]
    S = H["策略"]
    b50 = R["b50"]
    ch, dv = R["champ"], R["default"]
    wins = sum(r["beat"] for r in R["wf_rows"]); nseg = len(R["wf_rows"])
    g1 = wins > nseg / 2; g2 = R["nb"][1] > 0 and R["nb"][0] >= 2 / 3
    g3 = S["優化版"]["通過"]
    champ_ok = g1 and g2 and g3
    L = ["# 台指期第三輪：補測 NHI／JA、美股消息面濾網、外資期貨（1 倍曝險、只做多）\n"]
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。淘汰規則：年化輸同期含息扣成本的 0050 -> 淘汰；另要求最大回撤不比 0050 差。\n")
    L.append("> **資料切法**（2019 起已在前兩輪被看過，不再算乾淨證據）：搜尋與選參只用 **2008～2016**；**2017～2020 是新的內部保留期，只跑了一次**（鎖檔 `_holdout_done.json`）；"
             "**2021 起一併列出，但已被看過，不當證據**（表中標『已看過』）。外資期貨 fut_inst 只有 2018-06 起，搜尋期沒有它，只能當一條事先固定的規則在保留期一次驗，樣本短（保留期內約 2.6 年）。\n")
    rows = []
    def add(label, nm, sp, in_search=True):
        s = S[nm]; m = s["保留期"]; ms = s["已看過"]
        sm = G.metrics(lab, sp, *TRAIN)
        rows.append({"候選": label, "搜尋期年化(2008-16)": fp(sm["cagr"]), "搜尋期0050": fp(b50["cagr"]),
                     "保留期年化(2017-20)": fp(m["cagr"]), "保留期0050": fp(hb["cagr"]), "差距": f"{(m['cagr'] - hb['cagr']) * 100:+.1f} 點",
                     "保留期回撤": fp(m["mdd"]), "0050回撤": fp(hb["mdd"]), "保留期勝率": fp(m["win"], 0), "保留期交易數": int(m["n"]),
                     "判定": "通過" if s["通過"] else "**淘汰**" + ("：年化輸 0050" if m["cagr"] <= hb["cagr"] else "：回撤比 0050 差"),
                     "已看過 2021 起年化（0050）": f"{fp(ms['cagr'])}（{fp(hs['cagr'])}）"})
    add("階段3 優化版（冠軍候選）", "優化版", ch); add("階段3 預設參數版", "預設參數版", dv)
    add("優化版＋外資期貨濾網（2018-06 起才有作用）", "優化版＋外資期貨濾網", R["chip"])
    add("階段2 最佳單一指標＋採用的濾網", "階段2最佳單一＋濾網", R["sp2"]); add("階段1 最佳單一指標", "階段1最佳單一指標", R["sp1"])
    L.append("## 〇、通過／淘汰清單\n")
    L.append(f"內部保留期（2017-01～2020-12）0050 含息扣成本：年化 {fp(hb['cagr'])}、最大回撤 {fp(hb['mdd'])}；台指期永遠持有 {fp(H['TX持有_保留期']['cagr'])}／{fp(H['TX持有_保留期']['mdd'])}。"
             f"搜尋期 2008～2016：0050 {fp(b50['cagr'])}／{fp(b50['mdd'])}、台指期持有 {fp(R['txh']['cagr'])}／{fp(R['txh']['mdd'])}。\n")
    L.append(md(pd.DataFrame(rows)))
    L.append(f"\n冠軍三關：關卡 1 搜尋期 walk-forward 多數段贏 0050 —— **{wins}/{nseg} 段**（{'過' if g1 else '未過'}）；關卡 2 參數鄰域 >= 2/3 贏 0050 年化 —— **{fp(R['nb'][0], 0)}**（{R['nb'][1]} 個鄰居；{'過' if g2 else '未過'}）；"
             f"關卡 3 內部保留期年化高於 0050 且回撤不輸 —— {'過' if g3 else '未過'}。**結論：{'有冠軍' if champ_ok else '沒有冠軍'}。**\n")
    # 1 補測
    nhi = R["df"][R["df"]["代號"] == "NHI"]
    ja = R["p2e"][R["p2e"]["濾網"] == "JA"].iloc[0]
    L.append("## 一、補測上一輪漏掉的兩項\n")
    L.append("上一輪的缺陷（VOTE 退化列佔掉名額、階段 2 分母多 1）已修正：普查排除零交易列，階段 2 分母是實際的 8 個基底。\n")
    t = nhi.copy()
    for c in ("年化", "回撤", "勝率", "持倉比"):
        t[c] = t[c].map(fp)
    t["夏普"] = t["夏普"].map(lambda x: f"{x:.2f}"); t["賺賠比"] = t["賺賠比"].map(lambda x: f"{x:.2f}")
    t["贏0050"] = t["贏0050"].map(lambda x: "是" if x else "否")
    L.append("**NHI（N 日新高）普查（2008～2016）**\n\n" + md(t.drop(columns=["代號", "_spec", "_tf", "_name"])))
    rk = R["df"].sort_values("夏普", ascending=False).reset_index(drop=True)
    rk_nhi = [f"{r['週期']}第 {i + 1} 名（共 {len(rk)}）" for i, r in rk.iterrows() if r["代號"] == "NHI"]
    L.append("NHI 夏普排名：" + "、".join(rk_nhi) + "；進階條件是日K 前 5／週K 前 3，因此" + ("進入" if any(b["代號"] == "NHI" for b in R["bases"]) else "沒有進入") + "階段 2 與 3。\n")
    L.append(f"**JA（7～8 月不開新倉）**：8 個基底中 {ja['變好比例']} 變好，平均年化 {ja['平均年化變化'] * 100:+.2f} 點、回撤 {ja['平均回撤變化'] * 100:+.2f} 點 -> {'**採用**' if ja['採用'] else '不採用'}。\n")
    # 2 US
    L.append("## 二、美股消息面（階段 2，搜尋期 2008～2016，疊在階段 1 的 8 個指標上）\n")
    gap = pd.Series(lab.lab.o[1:] / lab.lab.c[:-1] - 1, index=lab.idx[:-1])
    cr = []
    for k, nm in (("spx", "S&P 500"), ("ixic", "Nasdaq"), ("sox", "費半 SOX"), ("vix", "VIX")):
        r = pd.Series(lab.us_night[k], index=lab.idx)
        x = pd.concat([r, gap], axis=1).dropna(); x = x[x.index >= "2008-01-01"]
        y = pd.concat([r.shift(-1), gap], axis=1).dropna(); y = y[y.index >= "2008-01-01"]
        cr.append({"美股指標": nm, "與台指期隔日開盤跳空相關（美股日期＝訊號日）": f"{x.corr().iloc[0, 1]:.2f}", "錯置一天（對照）": f"{y.corr().iloc[0, 1]:.2f}"})
    L.append("**時間線驗證**：美股日期 d 的收盤在台灣 d+1 清晨，早於台指期 d+1 開盤；所以訊號日（台灣日期 d）收盤後、隔日開盤進場，可合法使用美股日期 d 的收盤。實測：\n\n" + md(pd.DataFrame(cr)))
    p = pd.concat([R["p2e"].assign(類型="進場濾網"), R["p2x"].assign(類型="出場（隔日開盤）")])
    for c in ("平均年化變化", "平均回撤變化", "平均勝率變化"):
        p[c] = p[c].map(lambda x: f"{x * 100:+.2f} 點")
    p["採用"] = p["採用"].map(lambda x: "採用" if x else "不採用")
    L.append("『變好比例』＝加了該濾網後 Calmar（年化／回撤）變高的指標數，過半才採用（事先定好）。每個濾網只有一條事先固定的規則，不調門檻。\n\n" + md(p[["類型", "濾網", "說明", "變好比例", "平均年化變化", "平均回撤變化", "平均勝率變化", "採用"]]))
    L.append("**資料狀況**：intl_daily 從 2008 年起（^GSPC ^IXIC ^SOX ^VIX DX-Y.NYB TSM ^DJI TWD=X）；TSM ADR 溢價＝TSM（美元）x 美元兌台幣 / 5 / 2330 台股收盤 - 1（ADR 一單位＝5 股）；"
             "**DGS10（美債殖利率）還沒補到**，本輪未測；fut_inst 從 2018-06 起（只有 TX 大台有 2018-06，MTX 2021、TMF 2024）。選擇權 P/C 比、三大法人（期貨以外）歷史、FOMC／CPI 事件日歷史資料湖都沒有，未測。\n")
    # 3 evo
    L.append("## 三、演進表（每階段加了什麼、為什麼、數字變多少）\n")
    ev = []
    prev = None
    items = [("階段1 最佳單一指標（預設參數、無停損）", R["sp1"], "階段1最佳單一指標", "普查 22 種指標 x 日K／週K，夏普最高者"),
             ("階段2 + 採用的消息面濾網", R["sp2"], "階段2最佳單一＋濾網", f"加了進場濾網 {'+'.join(R['acc_e']) or '無'}、出場 {'+'.join(R['acc_x']) or '無'}；為什麼：疊加台灣與美股消息面，過半基底變好才採用"),
             ("階段3 組合（預設參數）", dv, "預設參數版", "週K 方向＋日K 進場＋濾網＋3 ATR 停損，參數教科書預設；為什麼：驗證『組合』本身有沒有用"),
             ("階段3 組合（優化參數）", ch, "優化版", "2008～2016 網格優化指標參數、停損倍數、濾網組合；為什麼：接受過擬合探索，但只在搜尋期")]
    for nm, sp, hk, why in items:
        m = G.metrics(lab, sp, *TRAIN); hm = S[hk]["保留期"]
        ev.append({"階段": nm, "加了什麼／為什麼": why, "搜尋期年化": fp(m["cagr"]), "年化變化": "-" if prev is None else f"{(m['cagr'] - prev['cagr']) * 100:+.1f} 點",
                   "搜尋期回撤": fp(m["mdd"]), "回撤變化": "-" if prev is None else f"{(m['mdd'] - prev['mdd']) * 100:+.1f} 點", "勝率": fp(m["win"], 0),
                   "勝率變化": "-" if prev is None else f"{((m['win'] or 0) - (prev['win'] or 0)) * 100:+.1f} 點", "交易數": int(m["n"]),
                   "保留期年化": fp(hm["cagr"]), "保留期回撤": fp(hm["mdd"])})
        prev = m
    L.append(md(pd.DataFrame(ev)))
    L.append(f"優化版 = {label3(ch)}；預設版 = {label3(dv)}。\n")
    eo_s = G.metrics(lab, ch, *TRAIN)["cagr"] - b50["cagr"]; eo_h = S["優化版"]["保留期"]["cagr"] - hb["cagr"]
    ed_s = G.metrics(lab, dv, *TRAIN)["cagr"] - b50["cagr"]; ed_h = S["預設參數版"]["保留期"]["cagr"] - hb["cagr"]
    L.append(f"**過擬合程度**（看相對 0050 的差距）：優化版搜尋期 {eo_s * 100:+.1f} 點 -> 保留期 {eo_h * 100:+.1f} 點；預設版 {ed_s * 100:+.1f} 點 -> {ed_h * 100:+.1f} 點。\n")
    # 4 census
    L.append("## 四、階段 1 單一指標普查（2008～2016，1 倍、扣成本、無停損，依夏普排序）\n")
    t1 = R["df"].sort_values("夏普", ascending=False).copy()
    for c in ("年化", "回撤", "勝率", "持倉比"):
        t1[c] = t1[c].map(fp)
    t1["夏普"] = t1["夏普"].map(lambda x: f"{x:.2f}"); t1["賺賠比"] = t1["賺賠比"].map(lambda x: f"{x:.2f}")
    t1["贏0050"] = t1["贏0050"].map(lambda x: "是" if x else "否")
    L.append(md(t1.drop(columns=["代號", "_spec", "_tf", "_name"])))
    # 5 WF
    L.append("## 五、搜尋期 walk-forward（訓練窗 2008-01 起擴張；測試窗 2011–12、2013–14、2015–16）\n")
    w = pd.DataFrame([dict(測試窗=f"{r['a']}～{r['b']}", 選到的組合=label3(r["spec"]), 訓練年化=fp(r["train"]), 測試年化=fp(r["cagr"]), 同窗0050=fp(r["b50"]),
                          測試回撤=fp(r["mdd"]), **{"0050回撤": fp(r["b50mdd"])}, 交易數=r["n"], 勝負="贏" if r["beat"] else "輸") for r in R["wf_rows"]])
    L.append(md(w))
    L.append(f"參數鄰域：優化版只動一個維度、相鄰一格（{R['nb'][1]} 個），贏 0050 年化的比例 {fp(R['nb'][0], 0)}、鄰域中位年化 {fp(R['nb'][2])}。\n")
    # 6 yearly
    L.append("## 六、依年份績效（優化版；2017～2020 內部保留期，2021 起『已被看過』）\n")
    ys = S["優化版"]["年度"]; yd = S["預設參數版"]["年度"]
    yr = []
    for y in sorted(ys, key=int):
        x0 = lab.lab.bh_0050(f"{y}-01-01", f"{int(y) + 1}-01-01")
        yr.append({"年": y + ("（已看過）" if int(y) >= 2021 else "（保留期）"), "優化版": fp(ys[y]), "預設版": fp(yd[y]), "0050": fp((1 + x0).prod() - 1)})
    L.append(md(pd.DataFrame(yr)))
    # 7 notes
    L.append("## 七、逐筆交易筆記與檢討\n")
    notes = []
    for nm, sp in (("優化版", ch), ("預設參數版", dv)):
        for per, (a, z) in (("搜尋期2008-16", TRAIN), ("保留期2017-20", HOLD), ("已看過2021起", (SEEN, None))):
            notes.append(G.notes_table(lab, sp, a, z, tag=f"{nm}／{per}"))
    nt = pd.concat(notes)
    nt.to_csv(OUT / "trades_round3.csv", index=False, encoding="utf-8-sig")
    N = ["# 台指期第三輪交易筆記\n", "每筆含進場理由、出場原因、損益、最大不利偏移、事後檢討（規則式自動產生）。2021 起標『已看過』。\n"]
    for tag, g in nt.groupby("版本", sort=False):
        N.append(f"\n## {tag}（{len(g)} 筆）\n")
        for _, r in g.iterrows():
            N.append(f"- **{r['進場日']}** 進 {r['進場價']} -> {r['出場日']} 出 {r['出場價']}（{r['出場原因']}，持有 {r['持有天數']} 天）｜損益 {r['損益點']} 點（每口 {r['損益元每口']:,} 元，名義 {r['報酬率_名義']:.2%}）｜"
                     f"MAE {r['最大不利偏移點']} 點（{r['最大不利偏移_pct']:.2%}）｜進場理由：{r['進場理由']}；大格局 {r['大格局40週']}、基差 {r['基差5日pct']}%、外資期貨 {r['籌碼']}、結算週 {r['結算週']}｜**檢討**：{r['事後檢討']}")
    (OUT / "trades_notes_round3.md").write_text("\n".join(N), encoding="utf-8")
    base = nt[nt.版本.str.startswith("優化版")]
    worst = base.nsmallest(5, "損益點")[["版本", "進場日", "進場價", "出場日", "出場價", "出場原因", "損益點", "報酬率_名義", "持有天數", "事後檢討"]]
    L.append(f"完整逐筆見 `trades_notes_round3.md`、`trades_round3.csv`（共 {len(nt)} 筆）。優化版最慘五筆：\n\n" + md(worst))
    # 8 conclusion
    L.append("## 八、結論、優化空間與限制\n")
    o = S["優化版"]["保留期"]; d = S["預設參數版"]["保留期"]; c = S["優化版＋外資期貨濾網"]["保留期"]
    L.append(f"- 內部保留期：優化版 {fp(o['cagr'])}／{fp(o['mdd'])}，預設版 {fp(d['cagr'])}／{fp(d['mdd'])}，優化版＋外資期貨 {fp(c['cagr'])}／{fp(c['mdd'])}；0050 {fp(hb['cagr'])}／{fp(hb['mdd'])}。"
             + ("有冠軍。" if champ_ok else "沒有冠軍。") + f"已被看過的 2021 起僅供參考：優化版 {fp(S['優化版']['已看過']['cagr'])}、0050 {fp(hs['cagr'])}。\n"
             f"- 美股面：9 個進場濾網與 2 個出場規則中，只有 {'、'.join(f for f in R['acc_e'] if f.startswith('U_')) or '（無）'} 通過過半門檻；S&P、Nasdaq、SOX 的前一晚漲跌、VIX、ADR 溢價在『隔日開盤才進場』的框架下**沒有**讓指標變好——"
             "原因推測：美股前一晚資訊已大幅反映在隔日開盤跳空（相關 0.6），而本策略以隔日開盤價成交，等於已經吃到這個跳空；濾網只是少做了一些單。\n"
             "- 外資期貨（2018-06 起）：搜尋期沒有資料，只在內部保留期驗一次（2018-06～2020-12，約 2.6 年），樣本太短，不能當結論。\n"
             "- 補測結果：NHI 沒有進前段班；JA 與 BC 一起被採用（BC 8/8 基底變好，是目前最一致的濾網，但它只是『逆價差時才進場』，也讓交易數減少）。\n"
             "- 優化空間（由逐筆檢討彙整）：見第七節最慘五筆；趨勢轉折偵測落後、跳空越過停損是主要來源。與前兩輪一致：這類 1 倍多頭擇時的價值是回撤小，不是超額報酬。\n"
             "- 限制：搜尋期 2008～2016 只有 9 年且含 2008 單一大空頭，0050 在該期年化只有約 4%，容易『贏』；保留期 2017～2020 是 0050 大漲期；DGS10、P/C 比、事件日歷史缺；2021 起已被看過。\n")
    L.append(f"## 九、試了幾組\n- 階段 1 普查 {len(R['df'])} 組、階段 2 濾網 {len(ENTRY_FACTORS) + len(EXIT_FACTORS)} 個 x 8 基底、階段 3 組合空間 {R['space_n']} 組（含 WF 重選與鄰域，不重複回測更多）。登記於 `registry.csv`。多重比較未校正，所以冠軍必須過三關。\n")
    L.append("## 十、重現\n\n`python -m pipeline.compute.futures_lab3`（搜尋期，約 3 分鐘）；`--holdout` 才跑內部保留期（已跑過，鎖檔存在時直接讀鎖檔）。測試：`pytest tests/test_futures_lab3.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main(do_holdout="--holdout" in sys.argv)
