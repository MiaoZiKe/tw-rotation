"""三套主題 × 深淺兩種底色的對比驗算（WCAG 2.x 相對亮度公式）。

門檻：內文（ink／ink-2／ink-3／漲跌數字／主色當連結字）≥ 4.5；
     圖形與大字（格線以外的線、圖例色塊、主色按鈕底配白字）≥ 3.0。
每一個前景都對「最淺與最深的兩種卡片底」各算一次，取最差值。

用法：python docs/design_v4/tools/contrast.py  → 印出表格；有不及格就回傳 1。
數值來源＝site/theme4.css 的 token（改 CSS 要回來同步改這裡，或反過來）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parents[3] / "site" / "theme4.css"


def lum(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def cr(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def blocks():
    """從 theme4.css 抓出 `/* @tokens <主題> <模式> */` 後面那一個 { } 區塊的 hex token。"""
    txt = CSS.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"/\*\s*@tokens\s+(\w+)\s+(\w+)\s*\*/[^{]*\{([^}]*)\}", txt):
        name = f"{m.group(1)}-{m.group(2)}"
        toks = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\b", m.group(3)))
        out[name] = toks
    return out


TEXT = ["--ink", "--ink-2", "--ink-3", "--rise", "--fall", "--flat", "--cyan", "--amber", "--violet", "--lime"]
BGS = ["--bg", "--panel", "--panel-2", "--panel-3"]


def main() -> int:
    bad = 0
    for name, t in blocks().items():
        print(f"\n## {name}")
        print("| 前景 | 值 | " + " | ".join(f"對 {b}" for b in BGS) + " | 最差 | 判定 |")
        print("|---|---|" + "---|" * len(BGS) + "---|---|")
        for k in TEXT:
            if k not in t:
                continue
            vals = [cr(t[k], t[b]) for b in BGS if b in t]
            worst = min(vals)
            ok = worst >= 4.5
            bad += not ok
            print(f"| `{k}` | `{t[k]}` | " + " | ".join(f"{v:.2f}" for v in vals) + f" | **{worst:.2f}** | {'通過' if ok else '✗ 不及格'} |")
        if "--on-accent" in t and "--accent" in t:
            v = cr(t["--on-accent"], t["--accent"])
            ok = v >= 4.5
            bad += not ok
            print(f"| 主色按鈕字 `--on-accent` 對 `--accent` | `{t['--on-accent']}`/`{t['--accent']}` | {v:.2f} |" + " |" * (len(BGS) - 1) + f" **{v:.2f}** | {'通過' if ok else '✗'} |")
        if "--line-2" in t:
            v = cr(t["--line-2"], t["--panel"])
            print(f"| 邊框 `--line-2` 對 `--panel`（非文字，僅參考） | `{t['--line-2']}` | {v:.2f} |" + " |" * (len(BGS) - 1) + " — | 參考 |")
    print(f"\n不及格：{bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
