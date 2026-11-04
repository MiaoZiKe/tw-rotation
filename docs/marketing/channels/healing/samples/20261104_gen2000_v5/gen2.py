#!/usr/bin/env python3
"""v5 產圖：插圖佔上 2/3（y=168～940），文字壓在下 1/3（主句≥44px 粗體、小字≥30px）。
文字一律從 ../20261104_gen2000/範例N_*.txt 讀「主句：／小字：」（企劃精簡版，重跑即吃到最新）。
用法：python3 gen2.py && node render.js && python3 contrast.py && python3 finalize.py"""
import json, os, re, html, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from illus import scene_svg
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "..", "20261104_gen2000")
esc = html.escape
PAL = {
 "V": "--w-bg:#403A4A;--w-dark:#332E3C;--w-face:#6B6280;--w-face3:#8D82A6;--w-paper:#D6CEE2;--w-text:#FFFFFF;--w-sub:#EAE4F0;--w-hint:#FFE08A;--w-line:#D8CFE4;--w-lamp:#F8DC8E;--vig:rgba(0,0,0,.09);--g-op:.045;--w-glow:.5",
 "W": "--w-bg:#4A4046;--w-dark:#392F36;--w-face:#76686F;--w-face3:#978891;--w-paper:#DDD0D3;--w-text:#FFFFFF;--w-sub:#F1E6E4;--w-hint:#FFE08A;--w-line:#E4D6DA;--w-lamp:#F8DD92;--vig:rgba(0,0,0,.09);--g-op:.045;--w-glow:.55",
}
CSS = "".join("body[data-palette=%s]{%s}" % (k, v) for k, v in PAL.items()) + """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--w-bg);color:var(--w-text);font-family:'Noto Sans CJK TC',sans-serif;letter-spacing:.04em}
.grain{position:absolute;left:0;top:0;mix-blend-mode:overlay;opacity:var(--g-op);pointer-events:none}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 60%,var(--vig) 100%);pointer-events:none}
.abs{position:absolute}
.lab{font-size:30px;line-height:40px;color:var(--w-sub);white-space:nowrap}
.illus{position:absolute;left:96px;overflow:hidden}
.m{position:absolute;left:96px;width:864px;font-family:'Noto Serif CJK TC',serif;font-weight:700;white-space:nowrap;color:var(--w-text)}
.s{position:absolute;left:96px;width:864px;font-size:31px;line-height:44px;color:var(--w-sub);white-space:nowrap}
.k{color:var(--w-text)}
.hintuse{color:var(--w-hint)}
.h{font-family:'Noto Serif CJK TC',serif;font-weight:700;font-size:46px;line-height:1.5;white-space:nowrap}
.si{font-size:30px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict;color:var(--w-sub)}
.help{font-size:31px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict;color:var(--w-text)}
"""
GRAIN = ('<svg class="grain" width="1080" height="1350"><filter id="gn"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/><feColorMatrix type="saturate" values="0"/>'
         '<feComponentTransfer><feFuncR type="linear" slope="3" intercept="-1"/><feFuncG type="linear" slope="3" intercept="-1"/><feFuncB type="linear" slope="3" intercept="-1"/><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter><rect width="1080" height="1350" filter="url(#gn)"/></svg>')

def read_txt(name): return open(os.path.join(SRC, name), encoding="utf-8").read()
def parse_slides(txt):
    out = {}
    for m in re.finditer(r"^第 (\d) 張[^\n]*\n(.*?)(?:\n\n|\Z)", txt, re.S | re.M):
        d = {"raw": [l for l in m.group(2).split("\n") if l.strip()]}
        for l in d["raw"]:
            if l.startswith("主句："): d["main"] = l[3:].strip()
            if l.startswith("小字："): d["small"] = l[3:].strip()
        out[int(m.group(1))] = d
    return out
def parse_threads(txt):
    d = {}
    for l in txt.split("\n"):
        if l.startswith("主句："): d["main"] = l[3:].strip()
        if l.startswith("小字："): d["small"] = l[3:].strip()
    return d

def split2(s, maxc=11):
    """主句過長時，在逗號／頓號後斷成兩行（只換行不改字）。"""
    if len(s) <= maxc: return [s]
    cuts = [i + 1 for i, c in enumerate(s) if c in "，、：" and 0 < i < len(s) - 1]
    if not cuts: return [s]
    i = min(cuts, key=lambda c: abs(c - len(s) / 2))
    return [s[:i], s[i:]]
NUM = re.compile(r"\d[\d,\.]*%?")
def mark(line, key, big):
    """把數字放大（key 另上提示色，每頁只有一處）。"""
    def f(m):
        t = m.group(0)
        if key and t == key: return '<span class="n hintuse" style="font-size:%.2fem">%s</span>' % (big * 1.1, esc(t))
        return esc(t)
    out, last = "", 0
    for m in NUM.finditer(line):
        out += esc(line[last:m.start()]) + f(m); last = m.end()
    return out + esc(line[last:])

def page(post, sl, total, d, lines=None):
    pal = sl["palette"]
    o = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s</style></head><body data-palette="%s">' % (CSS, pal), GRAIN, '<div class="vig"></div>',
         '<div data-o="lab" class="abs lab" style="left:96px;top:96px">%s</div>' % esc(post["series"])]
    if total > 1: o.append('<div data-o="pg" class="abs lab" style="right:96px;top:96px">%d／%d</div>' % (sl["n"], total))
    o.append('<div data-o="acct" class="abs lab" style="right:96px;top:1222px">%s</div>' % esc(post["channel"]))
    if sl["type"] != "sources":
        o.append('<div data-o="foot" class="abs lab" style="left:96px;top:1222px">%s</div>' % ("往右滑 →" if sl["type"] == "cover" and total > 1 else "公開數據整理，非投資建議"))
        o.append(scene_svg(sl["illus"]))
        main = d["main"]; small = d.get("small")
        key = sl.get("key")
        size = 52 if sl["type"] == "cover" else 52
        big = 1.3
        def wd(L, sz):
            w = 0
            for ch in L: w += (0.6 * big * 1.05 if ch in "0123456789,.%" else 0.35 if ch == " " else 1.0) * sz * 1.05
            return w
        ml = split2(main, 11) if sl["type"] == "cover" else [main]
        if sl["type"] != "cover" and wd(main, 44) > 864: ml = split2(main, 11)
        while max(wd(L, size) for L in ml) > 864 and size > 44: size -= 1
        assert max(wd(L, size) for L in ml) <= 864, ("主句過寬", ml)
        lh = round(size * (1.2 if sl['type']=='cover' else 1.28))
        top = 980 + (16 if NUM.search(main) else 0) - (4 if sl['type'] != 'cover' else 0)
        o.append('<div data-o="main" class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (top, size, lh, "<br>".join(mark(L, key if key and key in L else None, big) for L in ml)))
        if small:
            o.append('<div data-o="small" class="s" style="top:%dpx">%s</div>' % (top + lh * len(ml) + (40 if not NUM.search(main) else 56) + (12 if small and NUM.search(small) else 0), mark(small, key if key and key in small else None, 1.3)))
    else:
        o.append('<div class="abs" style="left:96px;top:184px;width:864px"><div data-o="sh" class="h">出處與求助資源</div>')
        items, helps, seen = [], [], False
        for l in lines:
            l = l.strip()
            if l == "出處：": continue
            l = l[3:] if l.startswith("出處：") else l
            if "安心專線" in l: seen = True
            (helps if seen else items).append(l)
        for j, it in enumerate(items): o.append('<div data-o="si%d" class="si" style="margin-top:34px">%s</div>' % (j, esc(it)))
        for j, it in enumerate(helps): o.append('<div data-o="help%d" class="help" style="margin-top:36px">%s</div>' % (j, esc(it)))
        o.append("</div>")
    o.append("</body></html>")
    return "".join(o)

def main():
    for p in sys.argv[1:] or ["post1", "post2", "post3", "post4"]:
        d = os.path.join(BASE, p)
        post = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
        txt = read_txt(post["txt"]); os.makedirs(os.path.join(d, "html"), exist_ok=True); mf = {}
        sls = parse_threads(txt) if post["mode"] == "threads" else parse_slides(txt)
        n = len(post["slides"])
        found = len(sls) if post["mode"] != "threads" else 1
        assert post["mode"] == "threads" or found == n, ("txt 張數與 data.json 不符", p, found, n)
        for sl in post["slides"]:
            dd = sls if post["mode"] == "threads" else sls[sl["n"]]
            lines = None
            if sl["type"] == "sources":
                lines = dd["raw"]
            else:
                assert "main" in dd, ("缺主句", p, sl["name"])
            open(os.path.join(d, "html", sl["name"] + ".html"), "w", encoding="utf-8").write(page(post, sl, n, dd, lines))
            mf[sl["name"]] = 1350
        json.dump(mf, open(os.path.join(d, "manifest.json"), "w")); print(p, "ok", n)
main()
