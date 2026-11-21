#!/usr/bin/env python3
"""第二版「無力感視覺語言」產圖腳本。
文字一律從 ../20261104_gen2000/範例N_*.txt 讀（法遵會小改，重跑即吃到最新）；
版面、插圖、色票、數字（柱長）由各 postN/data.json 指定。用法：python3 gen2.py && node render.js && python3 contrast.py"""
import json, os, re, html, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from illus import scene_svg
BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "..", "20261104_gen2000")
esc = html.escape

CSS = """
:root{--w-glow:.18;--w-glow2:.12;--w-glow3:.10}
body[data-palette=N]{--w-bg:#3B4553;--w-card:#46515F;--w-text:#EEF2F6;--w-sub:#C3CCD6;--w-hint:#E2CB98;--w-line:#9AA5B3;--w-lamp:#F2D88E;--vig:rgba(0,0,0,.16);--g-op:.10}
body[data-palette=V]{--w-bg:#4A4454;--w-card:#554E60;--w-text:#F3EFF5;--w-sub:#DAD2DF;--w-hint:#E9CF9E;--w-line:#ABA0B5;--w-lamp:#F2D88E;--vig:rgba(0,0,0,.16);--g-op:.10}
body[data-palette=C]{--w-bg:#56524D;--w-card:#615C56;--w-text:#F4F1EC;--w-sub:#D6D0C8;--w-hint:#EBD29E;--w-line:#B0A89E;--w-lamp:#F2D88E;--vig:rgba(0,0,0,.16);--g-op:.10}
body[data-palette=F]{--w-bg:#E3E7E1;--w-card:#F1F3EE;--w-text:#2A302C;--w-sub:#4F574F;--w-hint:#6B5B30;--w-line:#6A746D;--w-lamp:#C9B97A;--vig:rgba(40,50,45,.10);--g-op:.10;--w-glow:.22;--w-glow2:.14;--w-glow3:.12}
body[data-palette=W]{--w-bg:#52484F;--w-card:#5E525A;--w-text:#F6F0EE;--w-sub:#E3D6D4;--w-hint:#EDCF9E;--w-line:#B8A8AF;--w-lamp:#F5DC9A;--vig:rgba(0,0,0,.14);--g-op:.10;--w-glow:.30;--w-glow2:.22;--w-glow3:.18}
body[data-palette=M]{--w-bg:#323C4C;--w-card:#3D4859;--w-text:#ECF0F5;--w-sub:#BFC9D5;--w-hint:#E6D49A;--w-line:#94A0B2;--w-lamp:#F0DC96;--vig:rgba(0,0,0,.18);--g-op:.10;--w-glow:.16;--w-glow2:.10;--w-glow3:.08}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;position:relative;overflow:hidden;background:var(--w-bg);color:var(--w-text);
 font-family:'Noto Sans CJK TC',sans-serif;letter-spacing:.05em}
body[data-palette=F]::before{content:"";position:absolute;inset:0;background:rgba(120,140,120,.03)}
.grain{position:absolute;left:0;top:0;mix-blend-mode:overlay;opacity:var(--g-op);pointer-events:none}
.vig{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(0,0,0,0) 55%,var(--vig) 100%);pointer-events:none}
.abs{position:absolute}
.serif{font-family:'Noto Serif CJK TC',serif}
.lab{font-size:28px;line-height:40px;color:var(--w-sub);white-space:nowrap}
.illus{position:absolute;left:96px;overflow:hidden;-webkit-mask-image:linear-gradient(to right,transparent 0,#000 28px),linear-gradient(to bottom,transparent 0,#000 12px);-webkit-mask-composite:source-in;mask-composite:intersect}
.stack{position:absolute;left:96px;width:864px;display:flex;flex-direction:column;gap:44px}
.stack>div{width:fit-content;max-width:864px}.stack>.card,.stack>.strip{width:864px}
.h{font-family:'Noto Serif CJK TC',serif;font-size:44px;line-height:1.7;white-space:nowrap}
.b{font-size:34px;line-height:1.95;white-space:nowrap}
.q{font-family:'Noto Serif CJK TC',serif;font-size:40px;line-height:1.8;white-space:nowrap;margin-top:28px}
.hook{font-family:'Noto Serif CJK TC',serif;font-size:72px;line-height:1.5;white-space:nowrap}
.cvsub{font-size:34px;line-height:1.9;color:var(--w-sub);white-space:nowrap}
.num .n{font-family:'Noto Serif CJK TC',serif;font-size:64px;line-height:1.2;color:var(--w-hint);white-space:nowrap}
.num .u{font-size:32px;color:var(--w-sub)}
.num .c{font-size:30px;line-height:1.7;color:var(--w-sub);white-space:nowrap}
.card{background:var(--w-card);border-radius:12px;padding:26px 24px}
.card .ti{font-size:28px;line-height:1.5;color:var(--w-sub);margin-bottom:14px;white-space:nowrap}
.row{display:flex;align-items:center;margin-bottom:14px;height:44px}
.row .l{width:176px;flex:none;font-size:28px;white-space:nowrap}
.row .bar{height:38px;border-radius:6px;background:var(--w-line);flex:none}
.row .bar.now{background:var(--w-hint)}
.row .v{font-family:'Noto Serif CJK TC',serif;font-size:32px;margin-left:14px;white-space:nowrap}
.card .src{font-size:28px;line-height:1.5;color:var(--w-sub);white-space:nowrap}
.strip .tr{height:30px;border:3px solid var(--w-line);border-radius:6px;position:relative;margin-top:6px}
.strip .fl{position:absolute;left:0;top:0;bottom:0;background:var(--w-line)}
.strip .ax{display:flex;justify-content:space-between;font-size:28px;color:var(--w-sub);margin-top:8px;line-height:1.5}
.note{font-size:28px;line-height:1.6;color:var(--w-sub);white-space:nowrap}
.si{font-size:28px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict}
.help{font-size:30px;line-height:1.7;white-space:nowrap}
"""
GRAIN = ('<svg class="grain" width="1080" height="1350"><filter id="gn"><feTurbulence type="fractalNoise" baseFrequency="0.9" '
         'numOctaves="2" seed="7"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncR type="linear" slope="3" intercept="-1"/><feFuncG type="linear" slope="3" intercept="-1"/><feFuncB type="linear" slope="3" intercept="-1"/><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter><rect width="1080" height="1350" filter="url(#gn)"/></svg>')

def read_txt(name):
    return open(os.path.join(SRC, name), encoding="utf-8").read()

def split_slides(txt):
    out = {}
    for m in re.finditer(r"^第 (\d) 張[^\n]*\n(.*?)(?:\n\n|\Z)", txt, re.S | re.M):
        out[int(m.group(1))] = [l for l in m.group(2).split("\n") if l.strip()]
    return out

def split_paras(txt):
    return [[l for l in p.split("\n") if l.strip()] for p in re.split(r"\n\s*\n", txt.strip())]

def br(lines): return "<br>".join(esc(l) for l in lines)

def numparts(n):
    m = re.match(r"^([\d,\.]+)\s*(.*)$", n)
    return m.group(1), m.group(2)

def mk_num(lines, b, ctx):
    line = lines[b["l"]]
    n = b["n"]; assert n in line, (n, line)
    pre, post = line.split(n, 1)
    pre = pre.strip(); post = post.strip().rstrip("。")
    num, unit = numparts(n)
    cap = '<div class="c">%s</div>' % esc(pre) if pre else ""
    return ('<div data-o="num%d" class="num">%s<div class="n hintuse">%s<span class="u">%s%s</span></div></div>'
            % (ctx["i"], cap, esc(num), esc(unit), esc(post)))

def parse_row(line):
    m = re.match(r"^(\S+)\s+([\d,\.]+)\s*(\S*)$", line)
    return m.group(1), float(m.group(2).replace(",", "")), m.group(2) + (" " + m.group(3) if m.group(3) else "")

def mk_bars(lines, b, ctx):
    rows = []
    for r in b["rows"]:
        if "l" in r:
            label, v, disp = parse_row(lines[r["l"]])
        else:
            label, v, disp = r["label"], r["v"], r["disp"]
            assert disp.split(" ")[0] in "\n".join(lines) or True
        rows.append((label, v, disp, r.get("now")))
    for _, _, disp, _ in rows:  # 圖上每個數字都要在 txt（本頁文字）出現
        assert disp.replace(" ", "") in "".join(lines).replace(" ", ""), ("數字不在 txt：", disp)
    mx = max(r[1] for r in rows); W = b.get("w", 440)
    out = []
    for label, v, disp, now in rows:
        out.append('<div class="row"><div class="l">%s</div><div class="bar%s" data-v="%s" style="width:%dpx"></div><div class="v">%s</div></div>'
                   % (esc(b.get("labels", {}).get(label, label)), " now" if now else "", v, round(W * v / mx), esc(disp)))
    ti = '<div class="ti">%s</div>' % esc(lines[b["title_l"]].rstrip("：")) if "title_l" in b else ('<div class="ti">%s</div>' % esc(b["title"]) if b.get("title") else "")
    src = "".join('<div class="src">%s</div>' % esc(s) for s in b["src"])
    return '<div data-o="card%d" class="card">%s%s%s</div>' % (ctx["i"], ti, "".join(out), src)

def mk_strip(lines, b, ctx):
    return ('<div data-o="strip%d" class="card strip"><div class="tr"><div class="fl" data-v="%s" style="width:%.2f%%"></div></div>'
            '<div class="ax"><span>0%%</span><span>100%%</span></div><div class="src">%s</div></div>'
            % (ctx["i"], b["v"], b["v"] / b["max"] * 100, esc(b["src"])))

def build_blocks(sl, lines, ctx):
    used, parts = set(), []
    for i, b in enumerate(sl["blocks"]):
        ctx["i"] = i; t = b["t"]
        for k in b.get("also", []): used.add(k)
        for k in (b.get("l") if isinstance(b.get("l"), list) else [b.get("l")] if b.get("l") is not None else []): used.add(k)
        if t == "h": parts.append('<div data-o="h%d" class="h">%s</div>' % (i, br([lines[k] for k in b["l"]])))
        elif t == "b": parts.append('<div data-o="b%d" class="b">%s</div>' % (i, br([lines[k] for k in b["l"]])))
        elif t == "q": parts.append('<div data-o="q%d" class="q" style="font-size:%dpx">%s</div>' % (i, b.get("size", 40), br([lines[k] for k in b["l"]])))
        elif t == "note": parts.append('<div data-o="n%d" class="note">%s</div>' % (i, br([b["text"]] if "text" in b else [lines[k] for k in b["l"]])))
        elif t == "num": parts.append(mk_num(lines, b, ctx))
        elif t == "bars":
            for r in b["rows"]:
                if "l" in r: used.add(r["l"])
            if "title_l" in b: used.add(b["title_l"])
            parts.append(mk_bars(lines, b, ctx))
        elif t == "strip": parts.append(mk_strip(lines, b, ctx))
    for k in sl.get("skip", []): used.add(k)
    assert used == set(range(len(lines))), ("未使用的 txt 行（請確認法遵是否改了文字）：", sorted(set(range(len(lines))) - used), lines)
    return parts

def sources_page(lines):
    items, help_, tail = [], [], None
    head = lines[0]; rest = lines[1:]
    k = 0
    while k < len(rest) and rest[k].startswith("・"):
        items.append(rest[k]); k += 1
    rest = rest[k:]
    tail = rest[-1]; help_ = rest[:-1]
    return head, items, help_, tail

def page(post, sl, idx, total, lines, person_on=False):
    pal = sl["palette"]
    out = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s</style></head><body data-palette="%s"%s>' % (CSS, pal, ' style="--w-glow:.32;--w-glow2:.24;--w-glow3:.2"' if sl.get("hope") else ""), GRAIN, '<div class="vig"></div>',
           '<div data-o="lab" class="abs lab" style="left:96px;top:96px">%s</div>' % esc(post["series"])]
    if total > 1:
        out.append('<div data-o="pg" class="abs lab" style="right:96px;top:96px">%d／%d</div>' % (idx, total))
    out.append('<div data-o="acct" class="abs lab" style="right:96px;top:1222px">%s</div>' % esc(post["channel"]))
    left = "往右滑 →" if sl["type"] == "cover" and total > 1 else sl.get("foot", "公開數據整理，非投資建議")
    if sl["type"] != "sources":
        out.append('<div data-o="foot" class="abs lab" style="left:96px;top:1222px">%s</div>' % esc(left))
    top = 168
    if sl.get("illus"):
        ih = sl["ih"]
        out.append(scene_svg(sl["illus"], ih, bool(sl.get("hope") or pal == "W")))
        top = 176 + ih + 72
    if sl["type"] == "cover":
        hook = [l for l in lines if not l.startswith("副標：")]
        for k0, parts in sl.get("split", {}).items():   # 只換行不改字：拆開後串回必須等於原句
            assert "".join(parts) == k0, k0
            i0 = hook.index(k0); hook[i0:i0 + 1] = parts
        sub = [l[3:] for l in lines if l.startswith("副標：")]
        assert len(hook) <= 5 and all(len(l) <= 11 for l in hook), hook
        out.append('<div class="stack" style="top:%dpx"><div data-o="hook" class="hook" style="font-size:%dpx">%s</div>%s</div>' %
                   (top, sl.get("hook_size", 72), br(hook), '<div data-o="sub" class="cvsub" style="margin-top:20px">%s</div>' % esc(sub[0]) if sub else ""))
    elif sl["type"] == "sources":
        head, items, help_, tail = sources_page(lines)
        out.append('<div class="stack" style="top:168px;gap:36px"><div data-o="sh" class="h">%s</div>' % esc(head))
        for j, it in enumerate(items): out.append('<div data-o="si%d" class="si">%s</div>' % (j, esc(it)))
        out.append('<div data-o="help" class="help" style="margin-top:20px">%s</div>' % br(help_))
        out.append('<div data-o="tail" class="q" style="font-size:36px;margin-top:12px">%s</div></div>' % esc(tail))
    else:
        out.append('<div class="stack" style="top:%dpx">%s</div>' % (top, "".join(build_blocks(sl, lines, {}))))
    out.append("</body></html>")
    return "".join(out)

def main():
    for p in sys.argv[1:] or ["post1", "post2", "post3", "post4"]:
        d = os.path.join(BASE, p)
        post = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
        txt = read_txt(post["txt"])
        os.makedirs(os.path.join(d, "html"), exist_ok=True)
        mf = {}
        n = len(post["slides"])
        if post["mode"] == "paras":
            paras = split_paras(txt)
            def find(prefix):
                for q in paras:
                    if q[0].startswith(prefix): return q
                raise SystemExit("找不到段落：" + prefix)
        else:
            sls = split_slides(txt)
        for i, sl in enumerate(post["slides"], 1):
            if post["mode"] == "paras":
                # 單張圖：各 block 的 "para" 指到 txt 段落（以開頭字串找），lines 併成連續行，l 為段內索引
                lines = []
                def sh(x, base): return [k + base for k in x] if isinstance(x, list) else x + base
                for b in sl["blocks"]:
                    if "para" in b:
                        q = find(b["para"]); base = len(lines); lines += q
                        if "l" in b: b["l"] = sh(b["l"], base)
                        if "title_l" in b: b["title_l"] += base
                        if "also" in b: b["also"] = sh(b["also"], base)
                        for r in b.get("rows", []):
                            if "l" in r: r["l"] += base
                        b.pop("para")
                sl.setdefault("skip", [])
                for sp in sl.get("skip_paras", []):
                    q = find(sp); sl["skip"] += list(range(len(lines), len(lines) + len(q))); lines += q
            else:
                lines = sls[sl["n"]]
            for pon in (False,):
                nm = sl["name"]
                open(os.path.join(d, "html", nm + ".html"), "w", encoding="utf-8").write(page(post, sl, i, n, lines, pon))
                mf[nm] = 1350
        json.dump(mf, open(os.path.join(d, "manifest.json"), "w"))
        print(p, "ok", n)
main()
