"""設計 v4 第二批 2C：把尺度外的 margin／padding／gap 收進 4／8／12／16／24（機械轉換，可重跑）。

做法（為什麼這樣做寫在 docs/design_v4/05_第二批2C.md §2）：
  · **就地改值**，不在 theme4.css 另寫一份覆寫 —— 覆寫要複製選擇器、又會打亂原本的層疊順序
    （同特異度、後寫的規則本來會贏，覆寫一律寫在最後就會蓋掉它）。就地改值層疊結構一個都不動。
  · 改成 theme4.css 的尺度變數：4→var(--sp-1)、8→--sp-2、12→--sp-3、16→--sp-4、24→--sp-5。
  · **手機一屏版（≤640）不動**：沒有 @media 的規則、或 max-width 會涵蓋到 ≤640 的規則，改完之後**緊接在那條規則後面**
    補一段 `@media (max-width:640px){ 同一個選擇器{ 原值 } }`。緊接在後面＝層疊順序跟原本一樣，手機算出來的值逐字相同。
  · 只在 ≥641 生效的規則（min-width:641／821／1101…）直接改，不用補。
  · 1～3px 的細調、> 24 的版面讓位值（main 底部 80、搜尋框左內距 34…）、calc() 不動。

對應規則（每個值各自判斷；平手一律往密的方向，Andy 的痛點是「間隔太大導致圖被壓縮」）：
  4.5／5 → 4　　7／9 → 8　　11／13 → 12　　15 → 16　　22 → 24
  6 → 4（padding／margin／row-gap）；gap／column-gap 的 6 → 8（01 §2.1「控制項之間 8」）；
      gap 簡寫兩個值時第一個是列距 → 4、第二個是欄距 → 8
  10 → 8　　14 → 12　　18 → 16　　20 → 16

用法：
    python docs/design_v4/tools/spacing_apply.py --src <改前 site> --dst site --values 5,7,9,11,13,15,4.5 [--skip-lines index.html:123,...]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import tinycss2

PROPS = re.compile(r"^(margin|padding)(-(top|right|bottom|left|inline|block|inline-start|inline-end|block-start|block-end))?$"
                   r"|^(row-|column-)?gap$|^grid-(row-|column-)?gap$")
SCALE = {0, 4, 8, 12, 16, 24}
VARN = {4: 1, 8: 2, 12: 3, 16: 4, 24: 5}
BASIC = {4.5: 4, 5: 4, 7: 8, 9: 8, 11: 12, 13: 12, 15: 16, 22: 24, 10: 8, 14: 12, 18: 16, 20: 16}


def target(prop: str, idx: int, n: int, a: float) -> float:
    if a == 6:
        if prop in ("column-gap", "grid-column-gap"):
            return 8
        if prop in ("gap", "grid-gap"):
            return 4 if (n == 2 and idx == 0) else 8
        return 4
    return BASIC[a]


def media_ctx(prelude: str) -> str:
    p = prelude.lower()
    if "print" in p or "hover" in p or "reduced-motion" in p or "pointer" in p:
        return "other"
    mins = [float(x) for x in re.findall(r"min-width\s*:\s*([\d.]+)px", p)]
    maxs = [float(x) for x in re.findall(r"max-width\s*:\s*([\d.]+)px", p)]
    if maxs and max(maxs) <= 640:
        return "mob"
    if mins and min(mins) >= 641:
        return "desk"
    if maxs:
        return "mid"
    return "all"


def combine(cs):
    for o in ("mob", "other", "desk", "mid", "all"):
        if o in cs:
            return o
    return "all"


class Chunk:
    def __init__(self, text: str):
        self.text = text
        self.ls = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                self.ls.append(i + 1)

    def off(self, line, col):
        return self.ls[line - 1] + col - 1


def skip_ws_comments(t: str, i: int) -> int:
    return i


def block_end(t: str, i: int) -> int:
    """從 i 開始找第一個 '{'，回傳對應 '}' 的位置（略過註解與字串）"""
    n = len(t)
    depth = 0
    started = False
    while i < n:
        c = t[i]
        if c == "/" and t.startswith("/*", i):
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            q = c
            i += 1
            while i < n and t[i] != q:
                i += 2 if t[i] == "\\" else 1
            i += 1
            continue
        if c == "{":
            depth += 1
            started = True
        elif c == "}":
            depth -= 1
            if started and depth == 0:
                return i
        i += 1
    raise ValueError("找不到規則結尾")


def fmt(v: float) -> str:
    a = abs(v)
    if a == 0:
        return "0"
    if a in VARN:
        s = f"var(--sp-{VARN[a]})"
        return s if v > 0 else f"calc(-1 * {s})"
    return (str(int(v)) if v == int(v) else str(v)) + "px"


def rewrite_value(prop: str, val: str, values: set):
    """回傳 (新值, 有沒有改)。只改 px（不動 var()／calc()／em／%）。"""
    # 切出最上層的空白分隔片段（calc/var 括號裡的不切）
    parts, depth, cur = [], 0, ""
    for ch in val:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        parts.append(cur)
    changed = False
    out = []
    n = len(parts)
    for idx, p in enumerate(parts):
        m = re.fullmatch(r"(-?)(\d*\.?\d+)px", p)
        if not m:
            out.append(p)
            continue
        a = float(m.group(2))
        sign = -1 if m.group(1) else 1
        if a in values and a not in SCALE and 4 <= a <= 24:
            out.append(fmt(sign * target(prop, idx, n, a)))
            changed = True
        else:
            out.append(p)
    if not changed:
        return val, False
    # 同一條宣告裡原本就在尺度內的 px 一起寫成變數（讀的時候一眼看得出是同一套尺度）
    out2 = []
    for p in out:
        m = re.fullmatch(r"(-?)(\d*\.?\d+)px", p)
        if m and float(m.group(2)) in VARN:
            out2.append(fmt((-1 if m.group(1) else 1) * float(m.group(2))))
        else:
            out2.append(p)
    return " ".join(out2), True


def transform(css: str, values: set, skip: set, fname: str, base_line: int, log: list):
    ch = Chunk(css)
    edits = []      # (start, end, 新字串)
    inserts = []    # (位置, 字串)

    def walk(rules, stack):
        for r in rules:
            if r.type == "at-rule":
                if r.content is None:
                    continue
                kw = r.lower_at_keyword
                pre = tinycss2.serialize(r.prelude).strip()
                if kw == "media":
                    c = media_ctx(pre)
                elif kw in ("supports", "layer"):
                    c = "all"
                else:
                    continue  # @container、@keyframes、@font-face 不動
                sub = tinycss2.parse_rule_list(r.content, skip_comments=True, skip_whitespace=True)
                walk(sub, stack + [c])
                continue
            if r.type != "qualified-rule":
                continue
            sel = " ".join(tinycss2.serialize(r.prelude).split())
            ctx = combine(stack) if stack else "all"
            if "m3on" in sel:
                ctx = "mob"
            if ctx in ("mob", "other"):
                continue
            decls = tinycss2.parse_declaration_list(r.content, skip_comments=True, skip_whitespace=True)
            keep = []
            for d in decls:
                if d.type != "declaration" or not PROPS.match(d.lower_name):
                    continue
                gline = base_line + d.source_line - 1
                if f"{fname}:{gline}" in skip:
                    continue
                o = ch.off(d.source_line, d.source_column)
                m = re.compile(re.escape(d.name) + r"\s*:\s*([^;}]*?)(\s*!important)?\s*(?=;|\}|$)", re.I).match(css, o)
                if not m:
                    raise ValueError(f"對不到宣告 {fname}:{gline} {d.name}")
                val = m.group(1)
                new, changed = rewrite_value(d.lower_name, val, values)
                if not changed:
                    continue
                edits.append((m.start(1), m.end(1), new))
                log.append((fname, gline, ctx, sel, d.lower_name, val, new))
                if ctx in ("all", "mid"):
                    keep.append(f"{d.name}:{val}{m.group(2) or ''}")
            if keep:
                ro = ch.off(r.source_line, r.source_column)
                e = block_end(css, ro)
                inserts.append((e + 1, "\n@media (max-width:640px){" + sel + "{" + ";".join(keep) + "}}"))

    walk(tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True), [])
    ops = [(s, e, t) for s, e, t in edits] + [(p, p, t) for p, t in inserts]
    # 從後往前套（插入點＝規則的 '}' 後面，不會落在任何一段值的中間）
    ops.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = css
    for s, e, t in ops:
        out = out[:s] + t + out[e:]
    return out


ROOT_VARS = ("  /* ★ 2026-09-29 設計 v4 第二批 2C：v4 間距尺度也寫在這裡一份（值跟 theme4.css 骨架段一樣），\n"
             "     index.html 這份舊樣式段改用 var(--sp-N) 之後，就算 <html> 沒掛 data-theme4 也解得出值。 */\n"
             "  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:24px;\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--values", required=True)
    ap.add_argument("--skip-lines", default="")
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    values = {float(x) for x in a.values.split(",") if x}
    skip = {x.strip() for x in a.skip_lines.split(",") if x.strip()}
    src, dst = Path(a.src), Path(a.dst)
    log = []
    html = (src / "index.html").read_text(encoding="utf-8")
    m = re.search(r"(<style[^>]*>)(.*?)(</style>)", html, re.S)
    base_line = html[:m.start(2)].count("\n") + 1
    css = transform(m.group(2), values, skip, "index.html", base_line, log)
    css = css.replace("  --s1:4px; --s2:6px;", ROOT_VARS + "  --s1:4px; --s2:6px;", 1)
    html = html[:m.start(2)] + css + html[m.end(2):]
    (dst / "index.html").write_text(html, encoding="utf-8")
    t4 = (src / "theme4.css").read_text(encoding="utf-8")
    (dst / "theme4.css").write_text(transform(t4, values, skip, "theme4.css", 1, log), encoding="utf-8")
    print("改了", len(log), "條宣告；其中要補手機原值的", sum(1 for x in log if x[2] in ("all", "mid")))
    if a.log:
        Path(a.log).write_text("\n".join("\t".join(str(y) for y in x) for x in log) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
