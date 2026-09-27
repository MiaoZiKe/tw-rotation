"""把 measure.py 的 JSON 排成 Markdown 表格（改前單表、改前→改後對照表）。

用法：
    python docs/design_v4/tools/report.py before docs/design_v4/data/before.json
    python docs/design_v4/tools/report.py compare docs/design_v4/data/before.json docs/design_v4/data/after-hud-dark.json [...]
"""
from __future__ import annotations

import json
import sys


def load(p):
    return {(r["route"], r["w"]): r for r in json.load(open(p, encoding="utf-8"))}


def before(p):
    d = json.load(open(p, encoding="utf-8"))
    print("| 頁面 | 寬 | 第一屏繪圖區 % | 整頁繪圖區 % | 內容寬 px | 事件欄 px | 卡距 橫／直 | 卡片內距 | 標題負擔 px | 空白帶 % | 空白格 % | 頁高 px |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in d:
        g = f"{r['gapH'] if r['gapH'] is not None else '—'}／{r['gapV'] if r['gapV'] is not None else '—'}"
        print(f"| {r['name']} | {r['w']} | {r['plot1']} | {r['plotP']} | {r['mainW']} | {r['sideW'] or '—'} | {g} | {r['pad']} | "
              f"{r['head'] if r['head'] is not None else '—'} | {r['blank']} | {r['empty']} | {r['docH']} |")


def compare(pb, *pa):
    b = load(pb)
    afters = [(p.split("after-")[-1].replace(".json", ""), load(p)) for p in pa]
    hdr = "| 頁面 | 寬 | 指標 | 改前 | " + " | ".join(n for n, _ in afters) + " |"
    print(hdr)
    print("|---|---|---|---|" + "---|" * len(afters))
    keys = [("plot1", "第一屏繪圖區 %"), ("plotP", "整頁繪圖區 %"), ("mainW", "內容寬 px"), ("head", "標題負擔 px"),
            ("blank", "空白帶 %"), ("empty", "空白格 %"), ("docH", "頁高 px")]
    for k0 in sorted(b, key=lambda k: (["overview", "flow", "industry", "industry/semiconductor", "stock/2330", "heatmap",
                                       "heatmap/theme", "market", "season"].index(k[0]) if k[0] in
                                      ["overview", "flow", "industry", "industry/semiconductor", "stock/2330", "heatmap",
                                       "heatmap/theme", "market", "season"] else 99, -k[1])):
        if not all(k0 in a for _, a in afters):
            continue
        rb = b[k0]
        for i, (k, lab) in enumerate(keys):
            vals = [a[k0][k] for _, a in afters]
            name = rb["name"] if i == 0 else ""
            w = rb["w"] if i == 0 else ""
            print(f"| {name} | {w} | {lab} | {rb[k] if rb[k] is not None else '—'} | " +
                  " | ".join(str(v) if v is not None else "—" for v in vals) + " |")


if __name__ == "__main__":
    if sys.argv[1] == "before":
        before(sys.argv[2])
    else:
        compare(sys.argv[2], *sys.argv[3:])
