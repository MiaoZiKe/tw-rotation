#!/usr/bin/env python3
"""談晴說礙 v3：產出所有頁面的 HTML＋清單（manifest.json）。
用法：python3 gen.py && node render.js && python3 contrast.py && python3 sheets.py
全部文字在本檔 JOBS／TEXT 區；LOGO 看 logo.json；色票看 palette.json。"""
import json, os, html, re, sys
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from illus import scene_svg
B = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(B, "..")
PAL = json.load(open(B + "/palette.json", encoding="utf-8")); LOGO = json.load(open(B + "/logo.json", encoding="utf-8"))
esc = html.escape
SERIF_B = ImageFont.truetype("/root/.fonts/NotoSerifCJKtc-Bold.otf", 100)
THEME_KEY = {"夜版": "night", "晝版": "day"}

def css_vars(p):
    return ("--w-bg:{bg};--w-bg2:{bg2};--w-dark:{dark};--w-face:{face};--w-face3:{face3};--w-line:{line};--w-lamp:{lamp};--w-text:{text};--w-sub:{sub};"
            "--w-hint:{hint};--w-cloud:{cloudtxt};--w-glow:{glow};--w-glow2:{glow2};--g-op:{grain}").format(**p)
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:var(--W);height:var(--H);position:relative;overflow:hidden;color:var(--w-text);font-family:'Noto Sans CJK TC',sans-serif;letter-spacing:.04em;
 background:radial-gradient(ellipse 80% 60% at 50% 34%,var(--w-bg2) 0%,var(--w-bg) 78%)}
.grain{position:absolute;left:0;top:0;mix-blend-mode:overlay;opacity:var(--g-op);pointer-events:none}
.abs{position:absolute}
.lab{font-size:30px;line-height:40px;color:var(--w-sub);white-space:nowrap}
.illus{position:absolute;left:96px;overflow:hidden}
.m{position:absolute;left:96px;width:888px;font-family:'Noto Serif CJK TC',serif;font-weight:700;white-space:nowrap;color:var(--w-text)}
.s{position:absolute;left:96px;width:888px;font-size:32px;line-height:44px;color:var(--w-sub);white-space:nowrap}
.hintuse{color:var(--w-hint)}
.cta{color:var(--w-hint)}
.h{font-family:'Noto Serif CJK TC',serif;font-weight:700;font-size:48px;line-height:72px;white-space:nowrap}
.si{font-size:32px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict;color:var(--w-sub)}
.help{font-size:34px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict;color:var(--w-text)}
.logo{font-family:'Noto Serif CJK TC',serif;font-weight:700;white-space:nowrap;color:var(--w-text)}
.logo .sun{color:var(--w-hint)} .logo .cl{color:var(--w-cloud)}
.logo img{display:block}
"""
GRAIN = ('<svg class="grain" width="%d" height="%d"><filter id="gn"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/><feColorMatrix type="saturate" values="0"/>'
         '<feComponentTransfer><feFuncR type="linear" slope="3" intercept="-1"/><feFuncG type="linear" slope="3" intercept="-1"/><feFuncB type="linear" slope="3" intercept="-1"/><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter><rect width="%d" height="%d" filter="url(#gn)"/></svg>')

def text_w(s, size, spacing=.04):
    w = SERIF_B.getlength(s) * size / 100 + len(s) * spacing * size
    return w
NUM = re.compile(r"\d[\d,\.]*%?")
def split2(s):
    cuts = [i + 1 for i, c in enumerate(s) if c in "，、：" and 0 < i < len(s) - 1]
    if not cuts: return [s]
    i = min(cuts, key=lambda c: abs(c - len(s) / 2)); return [s[:i], s[i:]]
def mark(line, key, big):
    out, last = "", 0
    for m in NUM.finditer(line):
        t = m.group(0)
        out += esc(line[last:m.start()])
        out += ('<span class="hintuse" style="font-size:%.2fem">%s</span>' % (big, esc(t))) if key and t == key else esc(t)
        last = m.end()
    return out + esc(line[last:])
def mwidth(line, size, key, big):
    w = 0
    for m in re.split(r"(\d[\d,\.]*%?)", line):
        if not m: continue
        sz = size * big if (key and m == key) else size
        w += text_w(m, sz)
    return w

def logo_html(theme, size=None):
    L = LOGO; sz = size or L["size"]
    if L["mode"] == "image":
        src = L["image_night" if theme == "夜版" else "image_day"]
        return '<img src="%s" style="height:%dpx">' % (src, L["image_height"])
    t = L["text"]; s = ""
    for ch in t: s += '<span class="%s">%s</span>' % ("sun" if ch == L["sun_char"] else "cl" if ch == L["cloud_char"] else "", ch)
    return '<span class="logo" style="font-size:%dpx;letter-spacing:%s;margin-right:-%s">%s</span>' % (sz, L["letter_spacing"], L["letter_spacing"], s)

def page(spec, theme):
    W, H = spec.get("W", 1080), spec.get("H", 1350); p = PAL[theme]; kind = spec["kind"]
    y_head = spec.get("y_head", 96); y_foot = spec.get("y_foot", 1222)
    o = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H)]
    o.append('<div data-o="lab" class="abs lab" style="left:96px;top:%dpx">%s</div>' % (y_head, esc(spec["series"])))
    if spec.get("pg"): o.append('<div data-o="pg" class="abs lab" style="right:96px;top:%dpx">%d／%d</div>' % (y_head, spec["pg"][0], spec["pg"][1]))
    if not spec.get("no_logo"):
        o.append('<div data-o="logo" class="abs" style="right:96px;top:%dpx;line-height:40px">%s</div>' % (y_foot, logo_html(theme)))
    if spec.get("footL"):
        cls = "cta" if spec.get("footL_hint") else ""
        o.append('<div data-o="foot" class="abs lab %s" style="left:96px;top:%dpx">%s</div>' % (cls, y_foot, esc(spec["footL"])))
    key = spec.get("key"); big = 1.3
    if kind == "sources":
        o.append('<div class="abs" style="left:96px;top:184px;width:888px"><div data-o="sh" class="h">出處與求助資源</div>')
        for j, it in enumerate(spec["items"]): o.append('<div data-o="si%d" class="si" style="margin-top:34px">%s</div>' % (j, esc(it)))
        for j, it in enumerate(spec["helps"]): o.append('<div data-o="help%d" class="help" style="margin-top:36px">%s</div>' % (j, esc(it)))
        o.append("</div>")
        if spec.get("deco"): o.append(scene_svg(spec["deco"], 184, 1000, anchor="xMinYMid"))
    else:
        main = spec["main"]; small = spec.get("small")
        size = spec.get("size", 60)
        if kind == "data":
            o.append(scene_svg(spec["illus"], 520, 176))
            o.append('<div data-o="main" class="m" style="top:748px;font-size:%dpx;line-height:78px">%s</div>' % (size, esc(main)))
            o.append('<div data-o="num" class="m hintuse" style="top:884px;font-size:150px;line-height:176px;letter-spacing:.02em">%s</div>' % esc(spec["num"]))
            if small: o.append('<div data-o="small" class="s" style="top:1124px">%s</div>' % esc(small))
        else:
            if kind == "threads":
                ml = [main]
                while text_w(ml[0], size) > 888 and size > 60: size -= 1
                if text_w(ml[0], size) > 888: ml = split2(main)
                lh = round(size * 1.3); mt = 176
                o.append('<div data-o="main" class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (mt, size, lh, "<br>".join(mark(L, key, big) for L in ml)))
                if small: o.append('<div data-o="small" class="s" style="top:%dpx">%s</div>' % (mt + lh * len(ml) + 40, esc(small)))
                o.append(scene_svg(spec["illus"], 720, 176 + lh * len(ml) + 40 + 44 + 40))
            else:
                ml = [main]
                while mwidth(main, size, key, big) > 888 and size > 60: size -= 1
                if mwidth(main, size, key, big) > 888: ml = split2(main)
                while max(mwidth(L, size, key, big) for L in ml) > 888 and size > 60: size -= 1
                assert max(mwidth(L, size, key, big) for L in ml) <= 888, ("主句過寬", ml)
                lh = round(size * 1.3)
                if kind == "reels":
                    o.append(scene_svg(spec["illus"], 800, 350))
                    mt = 1196
                else:
                    o.append(scene_svg(spec["illus"], 712, 176)); mt = 940
                o.append('<div data-o="main" class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (mt, size, lh, "<br>".join(mark(L, key, big) for L in ml)))
                if small: o.append('<div data-o="small" class="s" style="top:%dpx">%s</div>' % (mt + lh * len(ml) + 40 + (30 if key else 0), mark(small, None, 1)))
    o.append("</body></html>")
    return "".join(o)

HELP5 = ["累的時候，可以撥打：\n・安心專線 1925（24 小時、免付費）\n・生命線 1995\n・張老師 1980（非 24 小時）", "有立即危險請撥 119 或 110。", "這裡是分享與陪伴，不能取代專業協助。"]
JOBS = []   # (資料夾, 檔名, spec)
def add(folder, name, spec): JOBS.append((folder, name, spec))

# ── A 首篇自介 3 張 ──
S1 = "觀察者手記"
add("首篇_3張", "1", dict(kind="std", series=S1, pg=(1, 3), illus="gap", main="談晴，也說礙", size=72, small="談著這一代的難，也說著晴天裡的光。", footL="往右滑 →"))
add("首篇_3張", "2", dict(kind="std", series=S1, pg=(2, 3), illus="window", main="我們是觀察者", size=72, small="記錄這時代年輕人的生活。"))
add("首篇_3張", "3", dict(kind="std", series=S1, pg=(3, 3), illus="sunrise", main="阻礙再多，也會等到放晴的一天", size=64, small="一個人走得快，一群人走得遠。", footL="傳給一個也在撐的朋友 →", footL_hint=True))
# ── B 長輩的期待 5 張（v5 文案與構圖）──
S2 = "長輩的期待"
add("長輩的期待", "1", dict(kind="std", series=S2, pg=(1, 5), illus="qtable", main="過年飯桌上，被問的人正在算房租。", small="沒有馬上回答，不代表不孝。", footL="往右滑 →"))
add("長輩的期待", "2", dict(kind="std", series=S2, pg=(2, 5), illus="scale", main="全國房貸負擔率 43.12%", key="43.12%", small="家戶每月能用的錢，四成多給房貸。", footL="公開數據整理，非投資建議"))
add("長輩的期待", "3", dict(kind="std", series=S2, pg=(3, 5), illus="steamq", main="被問到心裡發悶，是很常見的。", small="算不過來，不代表做錯了什麼。", footL="公開數據整理，非投資建議"))
add("長輩的期待", "4", dict(kind="std", series=S2, pg=(4, 5), illus="ring", main="也許明年的飯桌，會輕一點點。", small="這樣算的人，不只一個。", footL="公開數據整理，非投資建議"))
add("長輩的期待", "5", dict(kind="sources", series=S2, pg=(5, 5), items=["內政部〈住宅價格負擔能力統計〉2025 年第 2 季全國房貸負擔率 43.12%（房貸月付÷家戶月可支配所得中位數；媒體轉述）；2026-11-04 取用"],
                          helps=HELP5 + ["非投資、保險或貸款建議。存起來，過年前再看一次。"]))
# ── C 版型模板 ──
ST = "系列名稱"
add("模板", "1_封面", dict(kind="std", series=ST, pg=(1, 5), illus="gap", main="有些難，說清楚了就輕一點", size=64, small="觀察者的第一手記錄。", footL="往右滑 →"))
add("模板", "2_內頁一句話", dict(kind="std", series=ST, pg=(2, 5), illus="window", main="日子很硬，這一代還是很會在縫裡找光。", small="下班路上的一段夕陽，也算。"))
add("模板", "3_數據頁", dict(kind="data", series=ST, pg=(3, 5), illus="scale", main="全國房貸負擔率", num="43.12%", small="家戶每月能用的錢，四成多給房貸。", footL="公開數據整理，非投資建議"))
add("模板", "4_出處與求助", dict(kind="sources", series=ST, pg=(5, 5), items=["資料來源：〈統計名稱〉期間（口徑說明）；取用日期"], helps=HELP5 + ["非投資、保險或貸款建議。"]))
add("模板", "5_Threads單張", dict(kind="threads", series=ST, illus="sunrise", main="說這一代的難，也說還在的光", small="觀察者的每日一句。", footL="公開數據整理，非投資建議"))
add("模板", "6_Reels封面", dict(kind="reels", W=1080, H=1920, y_head=270, y_foot=1500, series=ST, illus="gap", main="談晴，也說礙", size=84, small="這一代的難，和還在的光。"))

def main():
    mf = []
    for theme in PAL:
        for folder, name, spec in JOBS:
            hdir = os.path.join(B, "html", theme, folder); os.makedirs(hdir, exist_ok=True)
            hp = os.path.join(hdir, name + ".html"); open(hp, "w", encoding="utf-8").write(page(spec, theme))
            od = os.path.join(OUT, folder, theme); os.makedirs(od, exist_ok=True)
            mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, name + ".png"), B), W=spec.get("W", 1080), H=spec.get("H", 1350),
                           key=f"{folder}/{theme}/{name}", safe=[250, 1580] if spec["kind"] == "reels" else None))
    json.dump(mf, open(B + "/manifest.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
main()
