#!/usr/bin/env python3
"""談晴說礙 說明型貼文（3 張：封面＋2 內頁，晝版，1080×1350）。沿用首篇短版版型（gen_short.py）：
LOGO 左上、右下頁碼小太陽＋淡橘實心點 40%＋箭頭（最後一頁無箭頭）、圖上一行出處（data-o="src"）。
封面字 ≤20、內頁字 ≤50；不用「我／我們」；圖上不放叫人做事的話。
用法：python3 gen_posts.py <佇列資料夾名> [...] && node render_posts.js <同上> && python3 contrast_posts.py <同上>
輸出：docs/marketing/channels/healing/queue/<名>/1～3.png；HTML 在 src/html/posts/<名>/。"""
import json, os, sys, html
B = os.path.dirname(os.path.abspath(__file__))
_src = open(B + "/gen_short.py", encoding="utf-8").read().split("\nmf = []")[0]
exec(compile(_src, "gen_short.py", "exec"))
QUEUE = os.path.abspath(os.path.join(B, "..", "..", "queue"))
SVGTXT = "font-family:'Noto Sans CJK TC',sans-serif;letter-spacing:.02em"

# ───────── 插圖 ─────────
def sc_age_bars(vals, labs, vlabs, H=760):
    """分年齡長條（畫成遠方樓房）：最高那棟上方壓著雲（礙），最低那棟旁一顆小太陽（晴）。vals 單位 %。"""
    base, k = H - 110, 46.0
    o = glow(730, 160, 150)
    o += C(730, 160, 34, LP) + halo_rings(730, 160, 34) + rays(730, 160, 52, 92, 0, 360, 16, at("none", 1.6, "var(--w-lamp)", op=.5))
    o += cloud(350, 150, 250, 92, 31, "var(--w-face3)") + wisp(250, 40, 130, .35) + wisp(500, 200, 110, .3)
    xs = [40, 220, 400, 580]; w = 130
    for i, (v, lab, vl) in enumerate(zip(vals, labs, vlabs)):
        h = v * k; x = xs[i]
        o += R(x, base - h, w, h, 3, at("var(--w-face3)", SW))
        for r in range(int((h - 26) // 30)):
            for c in range(3):
                if (r * 2 + c + i) % 3 == 0: continue
                o += '<rect x="%.1f" y="%.1f" width="16" height="14" rx="2" fill="var(--w-line)" opacity=".28"/>' % (x + 22 + c * 36, base - h + 22 + r * 30)
        o += '<text x="%.1f" y="%.1f" text-anchor="middle" style="%s;font-size:40px;font-weight:700;color:var(--w-text)" fill="currentColor">%s</text>' % (x + w / 2, base - h - 20, SVGTXT, html.escape(vl))
        o += '<text x="%.1f" y="%.1f" text-anchor="middle" style="%s;font-size:30px;color:var(--w-sub)" fill="currentColor">%s</text>' % (x + w / 2, base + 50, SVGTXT, html.escape(lab))
    o += Ln(10, base, 878, base, at("none", SW)) + hatch(24, base + 2, 840, 14, 11, at("none", 1.1, op=.25))
    return o

def sc_board(H=560):
    """求職佈告欄：牆上一塊軟木板釘著幾張單子，其中一張被圈起來；下方桌上一台筆電、一杯熱飲。"""
    o = glow(640, 250, 160)
    bx, by, bw, bh = 150, 30, 588, 300
    o += R(bx, by, bw, bh, 8, DK) + R(bx + 12, by + 12, bw - 24, bh - 24, 4, at("var(--w-face)", 1.6, op=.6))
    notes = [(190, 70, 120, 100, -4), (330, 60, 110, 130, 3), (460, 80, 130, 96, -2), (610, 64, 96, 120, 5), (230, 196, 140, 100, 2), (410, 200, 120, 96, -3), (560, 206, 130, 92, 4)]
    for j, (x, y, w, h, a) in enumerate(notes):
        g = R(x, y, w, h, 2, F3) + ''.join(Ln(x + 14, y + 26 + q * 18, x + w - 14 - (q % 2) * 22, y + 26 + q * 18, at("none", 1.3, op=.45)) for q in range(int((h - 30) // 18)))
        g += C(x + w / 2, y + 6, 6, at("var(--w-lamp)", 0, op=.85))
        if j == 3: g += E(x + w / 2, y + h / 2 + 6, w / 2 + 10, h / 2 + 4, at("none", 2.6, "var(--w-lamp)"))
        o += '<g transform="rotate(%d %.1f %.1f)">%s</g>' % (a, x + w / 2, y + h / 2, g)
    dy = 470
    o += Ln(30, dy, 858, dy, at("none", SW)) + R(30, dy, 828, 18, 0, F1) + hatch(60, dy + 20, 770, 30, 12, at("none", 1.1, op=.24))
    o += P('M250 %d L280 %d H460 L490 %d Z' % (dy, dy - 10, dy), F1) + R(286, dy - 128, 168, 118, 6, F3) + R(298, dy - 116, 144, 94, 3, DK)
    o += Ln(318, dy - 92, 400, dy - 92, at("none", 1.4, op=.5)) + Ln(318, dy - 72, 380, dy - 72, at("none", 1.4, op=.5)) + Ln(318, dy - 52, 410, dy - 52, at("none", 1.4, op=.5))
    o += R(600, dy - 76, 64, 76, 8, F3) + P('M664 %d q 30 4 26 26 q -4 18 -26 18' % (dy - 60), at("none", 3)) + steam(612, dy - 92, 50, .55) + steam(640, dy - 96, 44, .5)
    return o

SC = {"bars": None, "board": (sc_board, 560), "dusk": (lambda: sc_dusk_tall(100), 580)}
def scene_x(svg, H, top):
    I._uid[0] = 0
    defs = '<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>'
    return ('<div data-o="illus" class="illus" style="top:%dpx;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g id="ink">%s</g></svg></div>' % (top, H, H, H, defs, svg))

def head(theme="晝版"):
    p = PAL[theme]; W, H = 1080, 1350
    return ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s .hintuse{font-weight:700}</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H),
            '<div data-o="logo" class="abs" style="left:96px;top:84px;line-height:0"><img src="file://%s" style="height:64px;display:block"></div>' % LOGO_TIGHT]

def src_line(t):
    return '<div data-o="src" class="abs" style="left:96px;top:1252px;font-size:30px;line-height:40px;color:var(--w-sub);white-space:nowrap">%s</div>' % html.escape(t)

def page(post, n):
    pg = post["pages"][n - 1]; o = head()
    o.append('<div data-o="pager" class="abs" style="right:96px;top:1250px;height:44px;display:flex;align-items:center;gap:14px">%s</div>' % pager("S", n, 3))
    o.append(src_line(post["src"]))
    svg, H = pg["scene"]()
    o.append(scene_x(svg, H, 180))
    y = 180 + H + 52
    M = 'class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx"'
    if n == 1:
        o.append('<div data-o="main" ' + M % (y, 80, 100) + '>%s</div>' % lines(pg["title"]))
    else:
        o.append('<div data-o="main" ' + M % (y, 72, 88) + '>%s</div>' % html.escape(pg["title"]))
        q = ('<div data-o="body2" style="%s;font-weight:700;color:var(--w-hint)">%s</div>' % (BODY, html.escape(pg["ask"]))) if pg.get("ask") else ""
        o.append('<div class="abs" style="left:96px;top:%dpx;width:888px;display:flex;flex-direction:column;align-items:flex-start;gap:32px"><div data-o="body1" style="%s">%s</div>%s</div>' % (y + 88 + 40, BODY, lines(pg["body"]), q))
    return "".join(o) + "</body></html>"

# ───────── 各篇內容 ─────────
POSTS = {
 "20261111_unemployment": {
  "src": "資料：主計總處2026/9人力資源調查（10/23）",
  "pages": [
   {"title": ["失業率26年同月最低", "15-24歲仍逾11%"],
    "scene": lambda: (sc_age_bars([11.59, 5.69, 3.40, 2.75], ["15–24歲", "25–29歲", "30–34歲", "35–64歲"], ["11.59%", "5.69%", "3.40%", "<3%"]), 760)},
   {"title": "分年齡看", "body": ["整體失業率 3.36%，", "15–24 歲 11.59%，", "25–29 歲 5.69%，", "35–64 歲都低於 3%。"],
    "scene": lambda: (sc_board(), 560)},
   {"title": "數字背後", "body": ["官方說明：多數是初次找工作，", "還在適應職場；", "15–24 歲這組也含在學學生。"], "ask": "第一份工作，找了多久？",
    "scene": lambda: (sc_dusk_tall(100), 580)},
  ]},
}

def count(post):
    import re
    out = []
    for i, pg in enumerate(post["pages"]):
        t = "".join(pg["title"]) if isinstance(pg["title"], list) else pg["title"]
        t += "".join(pg.get("body", [])) + pg.get("ask", "")
        t = re.sub(r"\s", "", t)   # 全形字算 1、半形英數符號算 0.5（中文排版慣例）
        out.append(sum(.5 if ord(ch) < 128 else 1 for ch in t))
    return out

if __name__ == "__main__":
    names = sys.argv[1:] or list(POSTS)
    mf = []
    for name in names:
        post = POSTS[name]; c = count(post)
        print(name, "字數（封面≤20、內頁≤50）", c)
        assert c[0] <= 20 and all(x <= 50 for x in c[1:]), "字數超標"
        hd = os.path.join(B, "html", "posts", name); os.makedirs(hd, exist_ok=True)
        od = os.path.join(QUEUE, name); os.makedirs(od, exist_ok=True)
        for n in (1, 2, 3):
            hp = os.path.join(hd, f"{n}.html"); open(hp, "w", encoding="utf-8").write(page(post, n))
            mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, f"{n}.png"), B), W=1080, H=1350, key=f"{name}/{n}", post=name, safe=None))
    json.dump(mf, open(B + "/manifest_posts.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
