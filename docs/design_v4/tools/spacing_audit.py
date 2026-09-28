"""設計 v4 第二批 2C：全站間距普查（靜態，讀 CSS 原始碼）。

列出 site/index.html 的 <style> 與 site/theme4.css 裡所有 margin／padding／gap 宣告，
把 px 值跟 v4 尺度（0／4／8／12／16／24）比對，找出「尺度外」的值與位置。

分類（每一個數值各自判斷，一條宣告可能有好幾個值）：
  in       在尺度內：0、4、8、12、16、24
  hair     細調：1～3px（邊框對齊、晶片內距之類，刻意保留，不收）
  off      尺度外：5～23 之間不在尺度裡的值（6、10、14、18、20……）—— 這一批要收的
  big      大於 24 的版面值（28、32、40、80……）—— 多半是「讓位給某個固定元件」，逐條判斷
  var      用變數寫的：var(--s2) 之類會換算成 px 再歸類；換算不了的列 var-?

情境（這條規則在哪些寬度生效）：
  all      沒有 @media（所有寬度）
  desk     只在 ≥641（含 min-width:641／821／1101…）
  mob      只在 ≤640，或選擇器含 body.m3on（手機一屏版，這一批不動）
  mid      max-width 介於 641～1100（會影響窄桌機，也會影響手機）
  other    其他（print、hover、prefers-reduced-motion 之類）

用法：
    python docs/design_v4/tools/spacing_audit.py --json out.json --md out.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import tinycss2

ROOT = Path(__file__).resolve().parents[3]
SCALE = {0, 4, 8, 12, 16, 24}
PROPS = re.compile(r"^(margin|padding)(-(top|right|bottom|left|inline|block|inline-start|inline-end|block-start|block-end))?$|^(row-|column-)?gap$|^grid-(row-|column-)?gap$")
# v2／v4 變數換算（index.html :root 與 theme4.css 骨架裡定義的）
VARS = {"--s1": 4, "--s2": 6, "--s3": 8, "--s4": 12, "--s5": 16, "--s5h": 20, "--s6": 24, "--s7": 32, "--s8": 48,
        "--sp-1": 4, "--sp-2": 8, "--sp-3": 12, "--sp-4": 16, "--sp-5": 24, "--gap-card": 12}


def css_sources():
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
        start_line = html[:m.start(1)].count("\n") + 1
        out.append(("site/index.html", m.group(1), start_line))
    t4 = (ROOT / "site/theme4.css").read_text(encoding="utf-8")
    out.append(("site/theme4.css", t4, 1))
    return out


def media_ctx(prelude: str) -> str:
    p = prelude.lower()
    if "print" in p:
        return "other"
    mins = [float(x) for x in re.findall(r"min-width\s*:\s*([\d.]+)px", p)]
    maxs = [float(x) for x in re.findall(r"max-width\s*:\s*([\d.]+)px", p)]
    if maxs and max(maxs) <= 640:
        return "mob"
    if mins and min(mins) >= 641 and not maxs:
        return "desk"
    if mins and min(mins) >= 641 and maxs:
        return "desk"
    if maxs:
        return "mid"
    if mins:
        return "all"   # min-width < 641（例如 min-width:400）幾乎等於全部寬度
    if "hover" in p or "reduced-motion" in p or "pointer" in p or "orientation" in p:
        return "other"
    return "all"


def combine(ctxs):
    """巢狀 @media：取最窄的那個"""
    order = ["mob", "desk", "mid", "other", "all"]
    for o in order:
        if o in ctxs:
            return o
    return "all"


def classify(v: float) -> str:
    a = abs(v)
    if a in SCALE:
        return "in"
    if a < 4:
        return "hair"
    if a > 24:
        return "big"
    return "off"


def values_of(decl_value: str):
    """回傳 [(數值 px 或 None, 原字串)]；只取 px 與 var(--sX)；em／%／auto／calc 以外的略過"""
    vals = []
    s = decl_value
    # 先把 calc(...) 整段拿掉（算不出來），記一筆 calc
    for m in re.finditer(r"var\((--[\w-]+)(?:,\s*([^)]+))?\)", s):
        name = m.group(1)
        if name in VARS:
            vals.append((float(VARS[name]), m.group(0)))
        else:
            vals.append((None, m.group(0)))
    s2 = re.sub(r"var\([^)]*\)", " ", s)
    s2 = re.sub(r"calc\([^)]*\)", " ", s2)
    for m in re.finditer(r"(-?\d*\.?\d+)px", s2):
        vals.append((float(m.group(1)), m.group(0)))
    return vals


def walk(rules, src, base_line, ctx_stack, out):
    for r in rules:
        if r.type == "at-rule":
            kw = r.lower_at_keyword
            if r.content is None:
                continue
            prelude = tinycss2.serialize(r.prelude).strip()
            if kw in ("media", "supports", "container", "layer"):
                sub = tinycss2.parse_rule_list(r.content, skip_comments=True, skip_whitespace=True)
                c = media_ctx(prelude) if kw == "media" else "all"
                walk(sub, src, base_line, ctx_stack + [(c, "@" + kw + " " + prelude)], out)
            continue
        if r.type != "qualified-rule":
            continue
        sel = " ".join(tinycss2.serialize(r.prelude).split())
        decls = tinycss2.parse_declaration_list(r.content, skip_comments=True, skip_whitespace=True)
        for d in decls:
            if d.type != "declaration":
                continue
            name = d.lower_name
            if not PROPS.match(name):
                continue
            val = tinycss2.serialize(d.value).strip()
            vs = values_of(val)
            ctx = combine([c for c, _ in ctx_stack]) if ctx_stack else "all"
            if "m3on" in sel or ".m3 " in sel:
                ctx = "mob"
            line = base_line + d.source_line - 1
            for num, raw in vs:
                cls = classify(num) if num is not None else "var-?"
                out.append({"file": src, "line": line, "sel": sel, "prop": name, "value": val + (" !important" if d.important else ""),
                            "raw": raw, "px": num, "cls": cls, "ctx": ctx,
                            "media": " / ".join(m for _, m in ctx_stack)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--md", default="")
    a = ap.parse_args()
    out = []
    for src, css, line in css_sources():
        rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
        walk(rules, src, line, [], out)
    # 統計
    by = Counter((o["file"], o["ctx"], o["cls"]) for o in out)
    offv = Counter(abs(o["px"]) for o in out if o["cls"] == "off")
    print("宣告值總數", len(out))
    for k in sorted(by):
        print(k, by[k])
    print("尺度外數值分佈", sorted(offv.items(), key=lambda kv: -kv[1]))
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    if a.md:
        lines = []
        g = defaultdict(list)
        for o in out:
            if o["cls"] in ("off", "big", "var-?"):
                g[(o["file"], o["line"], o["sel"], o["prop"], o["value"], o["ctx"])].append(o["raw"])
        lines.append("| 檔案:行 | 情境 | 選擇器 | 屬性 | 值 | 尺度外的值 |")
        lines.append("|---|---|---|---|---|---|")
        for (f, ln, sel, p, v, c), raws in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            s = sel if len(sel) <= 70 else sel[:67] + "…"
            lines.append(f"| {f.split('/')[-1]}:{ln} | {c} | `{s.replace('|', '¦')}` | {p} | `{v.replace('|', '¦')}` | {' '.join(raws)} |")
        Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
