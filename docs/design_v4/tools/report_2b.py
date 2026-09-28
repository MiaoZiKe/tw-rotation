"""設計 v4 第二批 2B：把 stock_measure.py 的改前／改後兩份 JSON 排成 04 文件用的 Markdown 表。

    python3 docs/design_v4/tools/report_2b.py docs/design_v4/data/2b-before.json docs/design_v4/data/2b-after.json
"""
from __future__ import annotations

import json
import sys

NAMES = {
    "stock-overview": "個股・總覽", "stock-revenue": "個股・營收", "stock-profit": "個股・獲利", "stock-dividend": "個股・除權息",
    "stock-inst": "個股・法人", "stock-margin": "個股・資券", "stock-holders": "個股・大戶／散戶",
    "industry": "產業地圖", "chain-semi": "產業鏈・半導體", "chain-elec": "產業鏈・一般電子",
}


def d(a, b, nd=1, sign=True):
    if a is None or b is None:
        return f"{a} → {b}"
    diff = b - a
    s = f"{a} → **{b}**"
    if sign and abs(diff) > 1e-9:
        s += f"（{diff:+.{nd}f}）" if isinstance(diff, float) else f"（{diff:+d}）"
    return s


def main() -> int:
    bef = {(r["view"], r["w"]): r for r in json.load(open(sys.argv[1]))}
    aft = {(r["view"], r["w"]): r for r in json.load(open(sys.argv[2]))}
    keys = [k for k in bef if k in aft]
    views = []
    for v, _ in keys:
        if v not in views:
            views.append(v)
    print("| 頁面 | 寬 | 第一屏繪圖區 % | 整頁繪圖區 % | 頁高 px | 空白帶 % | 卡頂→圖 px | 分頁區頂 px | 分頁區繪圖 % | 分頁卡頂→圖 px |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for v in views:
        for w in (1440, 1100, 800, 390):
            if (v, w) not in bef or (v, w) not in aft:
                continue
            a, b = bef[(v, w)], aft[(v, w)]
            print(f"| {NAMES.get(v, v)} | {w} | {d(a['plot1'], b['plot1'])} | {d(a['plotP'], b['plotP'])} | {d(a['docH'], b['docH'])} | "
                  f"{d(a['blank'], b['blank'])} | {d(a.get('head'), b.get('head'))} | {d(a.get('tabTop'), b.get('tabTop'))} | "
                  f"{d(a.get('tabPlot'), b.get('tabPlot'))} | {d(a.get('tabHead'), b.get('tabHead'))} |")
    print()
    print("逐張圖（1440）：繪圖區頂 px／繪圖區佔容器 %／ECharts 圖例在容器裡／軸字最小")
    print()
    print("| 圖 | 分頁 | 繪圖區頂 | 繪圖區佔容器 % | 圖例在容器裡 | 軸字最小 |")
    print("|---|---|---|---|---|---|")
    for v in views:
        a, b = bef.get((v, 1440)), aft.get((v, 1440))
        if not a or not b:
            continue
        for cid, ca in a["charts"].items():
            cb = b["charts"].get(cid)
            if not cb:
                continue
            print(f"| {cid} | {NAMES.get(v, v)} | {d(ca['gridTop'], cb['gridTop'])} | {d(ca['plotPct'], cb['plotPct'])} | "
                  f"{'是' if ca['legendIn'] else '否'} → {'是' if cb['legendIn'] else '否'} | {d(ca['axisMin'], cb['axisMin'], sign=False)} |")
    print()
    print("K 線（1440，個股・總覽）：主圖高／副圖高／副圖標籤底 vs 資料區頂")
    a, b = bef.get(("stock-overview", 1440)), aft.get(("stock-overview", 1440))
    if a and b and a.get("lwc") and b.get("lwc"):
        for tag, r in (("改前", a), ("改後", b)):
            lw = r["lwc"]
            print(f"- {tag}：面板高 {[round(p['h']) for p in lw['panes']]}、資料區頂（離面板頂）{[p.get('dataTop') for p in lw['panes']]}，"
                  f"副圖標籤（字、離圖頂 y、高、字級）{[(l['t'], l['y'], l['h'], l['fs']) for l in lw['labels']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
