"""讀 strategy_lab 的結果，依「樣本外＋穩健性」收斂出各週期冠軍並產生 docs/strategy_lab/ 報告。

收斂規則（事先定好，不依結果調整）：
  1. 樣本內夏普 > 0 且樣本外夏普 > 0（兩段都要賺，不只挑樣本外）
  2. 樣本外交易筆數 >= 200（樣本太少不採信）
  3. 穩健性：同家族同週期的所有參數變體，樣本外夏普「中位數」> 0 且「最差」> -0.2
     （鄰域一動就崩的不要）
  4. 通過者依樣本外夏普排序，同家族只取一個，取前 3
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute.strategy_lab import OUT, SPLIT, ppy_of, stats  # noqa: E402

TFN = {"D": "日K", "W": "週K", "4H": "4H"}


def pct(x, d=1):
    return "-" if pd.isna(x) else f"{x*100:.{d}f}%"


def f2(x):
    return "-" if pd.isna(x) else f"{x:.2f}"


def champions(r: pd.DataFrame):
    out = {}
    for tf in ("4H", "D", "W"):
        x = r[r.tf == tf].copy()
        base = x[x.filt == ""]
        fam_med = base.groupby("fam")["oos_sharpe"].median()
        fam_min = base.groupby("fam")["oos_sharpe"].min()
        x["fam_med"] = x.fam.map(fam_med)
        x["fam_min"] = x.fam.map(fam_min)
        ok = x[(x.is_sharpe > 0) & (x.oos_sharpe > 0) & (x.oos_n >= 200) &
               (x.fam_med > 0) & (x.fam_min > -0.2)].sort_values("oos_sharpe", ascending=False)
        out[tf] = ok.drop_duplicates("fam").head(3), x
    return out


def row_md(s):
    return (f"| {s['name']} | {f2(s['is_sharpe'])} | {pct(s['oos_cagr'])} | {pct(s['oos_mdd'])} | {f2(s['oos_sharpe'])} | "
            f"{pct(s['oos_win'])} | {f2(s['oos_payoff'])} | {int(s['oos_n'])} | {pct(s['exposure'],0)} |")


HEAD = ("| 策略 | 樣本內夏普 | 樣本外年化 | 樣本外最大回撤 | 樣本外夏普 | 勝率 | 賺賠比 | 樣本外交易數 | 平均持倉 |\n"
        "|---|---|---|---|---|---|---|---|---|")


def worst5(trades: pd.DataFrame, split):
    t = trades[trades["entry"] >= pd.Timestamp(split)].nsmallest(5, "ret")
    return "\n".join(f"| {r.code} | {r.entry:%Y-%m-%d %H:%M} | {r.exit:%Y-%m-%d %H:%M} | {pct(r.ret)} | {pct(r.mae)} |"
                     for r in t.itertuples())


def yearly(ret: pd.Series, bh: pd.Series):
    a = (1 + ret).groupby(ret.index.year).prod() - 1
    b = (1 + bh.reindex(ret.index).fillna(0)).groupby(ret.index.year).prod() - 1
    return a, b


def main():
    L = []
    for mode, title in (("pit", "主結果（股票池只用樣本內流動性選，降低存活者偏誤）"),
                        ("cur", "對照（股票池＝近一年成交值前 100，存活者偏誤明顯，數字偏樂觀）")):
        r = pd.read_csv(OUT / f"all_results_{mode}.csv").fillna({"filt": ""})
        cache = pd.read_pickle(OUT / f"_cache_{mode}.pkl")
        ch = champions(r)
        L.append(f"\n## {title}\n")
        for tf in ("4H", "D", "W"):
            top, allx = ch[tf]
            b = allx.iloc[0]
            L.append(f"### {TFN[tf]}（樣本內／外切點 {SPLIT[tf]}；{cache['n_stocks'][tf]} 檔等權）\n")
            L.append(f"買進持有同池等權（樣本外）：年化 {pct(b.oos_bh_cagr)}、最大回撤 {pct(b.oos_bh_mdd)}、"
                     f"夏普 {f2(b.oos_bh_sharpe)}（樣本內夏普 {f2(b.is_bh_sharpe)}）。"
                     f"{len(allx)} 組中樣本外夏普贏過買進持有的有 {(allx.oos_sharpe > allx.oos_bh_sharpe).sum()} 組。\n")
            if len(top) == 0:
                L.append("**沒有任何策略通過收斂門檻。**\n")
                continue
            L.append("冠軍（通過收斂門檻、依樣本外夏普）：\n\n" + HEAD)
            for _, s in top.iterrows():
                L.append(row_md(s))
            L.append("")
            if mode == "pit":
                s = top.iloc[0]
                trd = cache["trades"][s["name"]]
                L.append(f"**{s['name']} 樣本外最慘五筆**（代號／進場／出場／報酬／持有中最大不利偏移）\n\n"
                         "| 代號 | 進場 | 出場 | 報酬 | 最大不利偏移 |\n|---|---|---|---|---|\n" + worst5(trd, SPLIT[tf]) + "\n")
                a, bb = yearly(cache["ret"][s["name"]], cache["bh"][tf])
                L.append("逐年報酬（策略 vs 買進持有）：" + "；".join(f"{y}: {pct(a[y],0)}/{pct(bb[y],0)}" for y in a.index) + "\n")
            fm = allx[allx.filt == ""].groupby("fam")["oos_sharpe"].agg(["median", "min", "max", "count"]).round(2)
            L.append("家族穩健性（同週期各參數變體的樣本外夏普：中位數／最差／最佳／組數）：\n\n| 家族 | 中位 | 最差 | 最佳 | 組數 |\n|---|---|---|---|---|")
            for fam, v in fm.sort_values("median", ascending=False).iterrows():
                L.append(f"| {fam} | {v['median']} | {v['min']} | {v['max']} | {int(v['count'])} |")
            L.append("")
        # 跨週期濾網
        m = r[r.filt != ""].copy()
        base = r[(r.filt == "") & (r.stop == 0)].set_index(["fam", "params", "tf"])
        rows = []
        for _, s in m.iterrows():
            k = (s.fam, s.params, s.tf)
            if k in base.index:
                bs = base.loc[k]
                rows.append((s["name"], bs.oos_sharpe, s.oos_sharpe, bs.oos_mdd, s.oos_mdd, bs.oos_cagr, s.oos_cagr, s.oos_n))
        d = pd.DataFrame(rows, columns=["name", "sh0", "sh1", "mdd0", "mdd1", "c0", "c1", "n"])
        L.append("### 跨週期濾網的效果（同策略加上高週期趨勢濾網前後，樣本外）\n\n"
                 "| 加濾網版本 | 夏普 前→後 | 最大回撤 前→後 | 年化 前→後 | 樣本外交易數 |\n|---|---|---|---|---|")
        for _, s in d.sort_values("sh1", ascending=False).iterrows():
            L.append(f"| {s['name']} | {f2(s.sh0)}→{f2(s.sh1)} | {pct(s.mdd0)}→{pct(s.mdd1)} | {pct(s.c0)}→{pct(s.c1)} | {int(s.n)} |")
        L.append(f"\n濾網讓夏普變好的有 {(d.sh1 > d.sh0).sum()} / {len(d)} 組，讓最大回撤變小的有 {(d.mdd1 > d.mdd0).sum()} / {len(d)} 組。\n")
    (OUT / "_report_body.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
