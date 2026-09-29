"""設計 v4 第二批 2C：measure.py 改前／改後 JSON → 05 文件的 Markdown 表；另印「退步格」（第一屏繪圖區少 ≥0.3、頁高多 >4、空白帶變多）。

    python3 docs/design_v4/tools/report_2c.py <改前.json> <改後.json> [--regress-only]
"""
from __future__ import annotations

import json
import sys


def d(a, b, nd=1):
    if a is None or b is None:
        return f"{a} → {b}"
    diff = b - a
    s = f"{a} → **{b}**"
    if abs(diff) > 1e-9:
        s += f"（{diff:+.{nd}f}）" if isinstance(diff, float) else f"（{diff:+d}）"
    return s


def main() -> int:
    bef = {(r["route"], r["w"]): r for r in json.load(open(sys.argv[1]))}
    aft = {(r["route"], r["w"]): r for r in json.load(open(sys.argv[2]))}
    only = "--regress-only" in sys.argv
    routes = []
    for r, _ in bef:
        if r not in routes:
            routes.append(r)
    reg = []
    if not only:
        print("| 頁面 | 寬 | 第一屏繪圖區 % | 整頁繪圖區 % | 頁高 px | 空白帶 % | 卡頂→圖 px |")
        print("|---|---|---|---|---|---|---|")
    for r in routes:
        for w in (1440, 1100, 800, 390):
            if (r, w) not in bef or (r, w) not in aft:
                continue
            a, b = bef[(r, w)], aft[(r, w)]
            if b["plot1"] < a["plot1"] - 0.25 or b["docH"] > a["docH"] + 4 or b["blank"] > a["blank"] + 0.2:
                reg.append((a["name"], w, a["plot1"], b["plot1"], a["docH"], b["docH"], a["blank"], b["blank"]))
            if not only:
                print(f"| {a['name']} | {w} | {d(a['plot1'], b['plot1'])} | {d(a['plotP'], b['plotP'])} | {d(a['docH'], b['docH'])} | "
                      f"{d(a['blank'], b['blank'])} | {d(a.get('head'), b.get('head'))} |")
    print()
    print("退步格（第一屏 -0.3 以上／頁高 +5 以上／空白帶 +0.3 以上）：", len(reg))
    for x in reg:
        print("  ", x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
