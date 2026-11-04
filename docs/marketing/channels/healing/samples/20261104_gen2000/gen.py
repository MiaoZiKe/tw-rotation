#!/usr/bin/env python3
"""讀 postN/data.json 產出 postN/html/*.html 與 manifest.json（尺寸 1080x1350）。
改數字只要改 data.json 的 facts（v、fmt、unit、src、year），重跑：python3 gen.py && node render.js
文字內可用 {fact鍵} 取數字（含單位）；色票 A 暖霧紙本，全部走 CSS 變數。"""
import json, os, html, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
CSS = """
:root{--bg:#FBF4EA;--card:#FFFFFF;--text:#3B2F2A;--sub:#6E5A4E;--accent:#A34A30;--glow:#F3D9C2;--bar:#D8BFA8}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--bg);color:var(--text);
 font-family:'Noto Sans CJK TC','Noto Sans TC',sans-serif}
.glow{position:absolute;left:140px;top:300px;width:800px;height:800px;border-radius:50%;
 background:radial-gradient(circle,var(--glow) 0%,rgba(243,217,194,0) 70%);opacity:.6}
.paper{position:absolute;inset:0;opacity:.05;pointer-events:none}
.abs{position:absolute}
.serif{font-family:'Noto Serif CJK TC','Noto Serif TC',serif}
.sans{font-family:'Noto Sans CJK TC',sans-serif}
.lab{font-size:30px;color:var(--sub);letter-spacing:.06em;white-space:nowrap}
.acct{font-size:30px;color:var(--sub);letter-spacing:.06em;text-align:right;white-space:nowrap}
.stack{position:absolute;left:88px;width:904px;display:flex;flex-direction:column;gap:52px}
.stack>div{width:100%}
.tag{display:inline-block;width:auto!important;font-size:34px;color:var(--text);font-weight:700;padding:10px 26px;
 background:var(--glow);border-radius:999px;align-self:flex-start;letter-spacing:.06em}
.acc{color:var(--accent)}
.bignum{margin:12px 0;display:flex;flex-direction:column;gap:6px}
.bignum .n{font-family:'Noto Serif CJK TC',serif;font-weight:700;font-size:150px;line-height:1.0;color:var(--accent);letter-spacing:.01em}
.bignum .c{font-size:38px;color:var(--sub);line-height:1.5}
.chart{background:var(--card);border-radius:20px;padding:40px 44px;box-shadow:0 2px 0 rgba(59,47,42,.06)}
.chart .ti{font-size:32px;color:var(--sub);line-height:1.5;margin-bottom:28px}
.row{display:flex;align-items:center;margin-bottom:22px}
.row .l{width:200px;font-size:34px;font-weight:700;flex:none}
.row .tr{flex:1;position:relative;height:60px}
.row .b{height:60px;border-radius:10px;background:var(--bar)}
.row .v{font-size:34px;font-weight:700;font-family:'Noto Serif CJK TC',serif;margin-left:0;white-space:nowrap}
.bwrap{display:flex;align-items:center;gap:16px}
.note{font-size:28px;color:var(--sub);margin:-10px 0 22px;line-height:1.5}
.chart .src{font-size:28px;color:var(--sub);margin-top:14px;line-height:1.5}
.cover-hook{font-family:'Noto Serif CJK TC',serif;font-weight:700;line-height:1.5;letter-spacing:.02em}
.hand{width:260px;height:6px}
.src-item{font-size:30px;line-height:1.5;color:var(--text)}
.src-item small{display:block;font-size:28px;color:var(--sub)}
"""
PAPER = ('<svg class="paper" width="1080" height="1350"><filter id="n"><feTurbulence type="fractalNoise" '
         'baseFrequency="0.8" numOctaves="2"/><feColorMatrix values="0 0 0 0 .24 0 0 0 0 .18 0 0 0 0 .16 0 0 0 1 0"/></filter>'
         '<rect width="1080" height="1350" filter="url(#n)"/></svg>')

def disp(f): return f["fmt"].format(f["v"]) + f.get("unit", "")
def sub(s, facts): return re.sub(r"\{(\w+)\}", lambda m: disp(facts[m.group(1)]), s)
def esc(s): return html.escape(s)
def src_line(f): return "資料來源：%s %s（自行重繪）" % (f["src"], f["year"])

def block(b, facts, has_big):
    t = b["t"]
    if t == "text":
        w = "700" if b.get("bold") else "400"
        ls = ".03em" if b["font"] == "serif" else ".02em"
        col = "var(--text)" if b["font"] == "serif" or b.get("main") else "var(--sub)"
        lines = "<br>".join(esc(sub(l, facts)) for l in b["lines"])
        return ('<div data-o=t%d class="%s" style="font-size:%dpx;font-weight:%s;line-height:1.55;letter-spacing:%s;color:%s">%s</div>'
                % (b["_i"], b["font"], b["size"], w, ls, col, lines))
    if t == "big":
        f = facts[b["fact"]]
        return ('<div data-o=b%d class="bignum"><div class="n">%s</div><div class="c">%s</div></div>'
                % (b["_i"], esc(disp(f)), esc(sub(b["cap"], facts))))
    if t == "bars":
        vals = [facts[i["fact"]]["v"] for i in b["items"]]
        mx = max(vals); W = 440  # 軌道最大寬度（含數字標籤要留空間）
        rows = []
        for it in b["items"]:
            f = facts[it["fact"]]
            bw = max(8, round(W * f["v"] / mx))
            col = "var(--bar)"
            if it.get("hl"): col = "var(--sub)" if has_big else "var(--accent)"
            rows.append('<div class="row"><div class="l">%s</div><div class="bwrap"><div class="b" style="width:%dpx;background:%s"></div>'
                        '<div class="v">%s</div></div></div>' % (esc(it["label"]), bw, col, esc(disp(f)))
                        + ('<div class="note">%s</div>' % esc(it["note"]) if it.get("note") else ""))
        srcs = "<br>".join(esc(l) for l in dict.fromkeys(src_line(facts[k]) for k in b["source_facts"]))
        return ('<div data-o=c%d class="chart"><div class="ti">%s</div>%s<div class="src">%s</div></div>'
                % (b["_i"], esc(b["title"]), "".join(rows), srcs))
    raise ValueError(t)

def page(post, s, idx, total):
    facts, ch = post["facts"], post["channel"]
    out = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s</style></head><body>' % CSS,
           '<div class="glow"></div>', PAPER,
           '<div data-o=lab class="abs lab sans" style="left:88px;top:96px">%s</div>' % esc(post["series"]),
           '<div data-o=pg class="abs lab sans" style="right:88px;top:96px">%d／%d</div>' % (idx, total) if total > 1 else "",
           '<div data-o=acct class="abs acct sans" style="right:88px;top:1214px">%s</div>' % esc(ch)]
    if s["type"] == "cover":
        sz = 76
        hook = "<br>".join(esc(l) for l in s["hook"])
        out.append('<div data-o=hook class="abs cover-hook" style="left:88px;top:290px;width:904px;font-size:%dpx">%s</div>' % (sz, hook))
        out.append('<div data-o=sub class="abs sans" style="left:88px;top:800px;width:904px;font-size:40px;color:var(--sub);line-height:1.6">%s</div>' % esc(s["sub"]))
        out.append('<div data-o=swipe class="abs lab sans" style="left:88px;top:1214px">往右滑 →</div>')
    elif s["type"] == "inner":
        blocks = s["blocks"]
        for i, b in enumerate(blocks): b["_i"] = i
        has_big = any(b["t"] == "big" for b in blocks)
        parts = []
        if s.get("tag"): parts.append('<div data-o=tag class="tag sans">%s</div>' % esc(s["tag"]))
        parts += [block(b, facts, has_big) for b in blocks]
        out.append('<div class="stack" style="top:%dpx">%s</div>' % (190 if not s.get("tag") else 190, "".join(parts)))
    elif s["type"] == "sources":
        items = []
        for k in s["facts"]:
            f = facts[k]
            items.append('<div data-o=s%s class="src-item sans">・%s，%s %s</div>' %
                         (k, esc(f["src"]), esc(f["year"]), esc(disp(f))))
        out.append('<div class="stack" style="top:190px;gap:36px"><div data-o=tag class="tag sans">出處</div>%s'
                   '<div data-o=close class="serif" style="font-size:52px;font-weight:700;line-height:1.5;margin-top:8px">%s</div></div>'
                   % ("".join(items), esc(s["closing"])))
    out.append("</body></html>")
    return "".join(out)

def main():
    for p in sys.argv[1:] or ["post1", "post2", "post3"]:
        d = os.path.join(BASE, p)
        post = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
        os.makedirs(os.path.join(d, "html"), exist_ok=True)
        mf = {}
        n = len(post["slides"])
        for i, s in enumerate(post["slides"], 1):
            open(os.path.join(d, "html", s["name"] + ".html"), "w", encoding="utf-8").write(page(post, s, i, n))
            mf[s["name"]] = 1350
        json.dump(mf, open(os.path.join(d, "manifest.json"), "w"))
main()
