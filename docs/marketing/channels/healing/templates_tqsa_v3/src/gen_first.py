#!/usr/bin/env python3
"""首篇自介 3 張：Andy 2026-11-06「單色黑 晝版 奶油 都還不錯 個別做給我 首張自介貼文範例」。
沿用 gen.py 的版面與插圖，換三套色系，LOGO 換成 logo_tqsa4_晴時多雲 02 三道光（圖片字標）。
用法：python3 gen_first.py && node render_first.js && python3 contrast_first.py"""
import json, os
B = os.path.dirname(os.path.abspath(__file__))
src = open(B + "/gen.py", encoding="utf-8").read().rsplit("\nmain()", 1)[0]
exec(compile(src, "gen.py", "exec"))
LOGO_N = os.environ.get("LOGO_DIR", "02_三道光")
LDIR = os.path.abspath(os.path.join(B, "..", "..", "logo_tqsa4_晴時多雲", LOGO_N))
PAL.clear(); PAL.update({
 "單色黑": {"bg": "#FFFFFF", "bg2": "#FFFFFF", "dark": "#E4E4E4", "face": "#F1F1F1", "face3": "#FFFFFF", "line": "#111111", "lamp": "#8A8A8A", "text": "#111111", "sub": "#3A3A3A", "hint": "#111111", "cloudtxt": "#111111", "glow": ".18", "glow2": ".28", "grain": ".03"},
 "晝版": {"bg": "#F6F1E8", "bg2": "#FBF8F1", "dark": "#E4DCCD", "face": "#EEE7DA", "face3": "#FBF8F1", "line": "#6E6A66", "lamp": "#D9822B", "text": "#2F2D2B", "sub": "#5C5753", "hint": "#9C530C", "cloudtxt": "#5F5B57", "glow": ".42", "glow2": ".6", "grain": ".08"},
 "奶油晨光": {"bg": "#FFF6E5", "bg2": "#FFFBF2", "dark": "#EFE1C6", "face": "#FAEFD8", "face3": "#FFFBF2", "line": "#7A746E", "lamp": "#D9822B", "text": "#3A3A3A", "sub": "#5C5753", "hint": "#9C530C", "cloudtxt": "#5F5B57", "glow": ".42", "glow2": ".6", "grain": ".07"},
})
def logo_html(theme, size=None):
    f = os.path.join(LDIR, f"字標_透明_{theme}.png")
    if not os.path.exists(f): f = os.path.join(LDIR, f"字標_{theme}.png")
    return '<img src="file://%s" style="height:72px;display:block">' % f
JOBS.clear()
S1 = "觀察者手記"
add("首篇_三色系", "1", dict(kind="std", series=S1, pg=(1, 3), illus="gap", main="談晴，也說礙", size=72, small="談著這一代的難，也說著晴天裡的光。", footL="往右滑 →"))
add("首篇_三色系", "2", dict(kind="std", series=S1, pg=(2, 3), illus="window", main="我們是觀察者", size=72, small="記錄這時代年輕人的生活。"))
add("首篇_三色系", "3", dict(kind="std", series=S1, pg=(3, 3), illus="sunrise", main="阻礙再多，也會等到放晴的一天", size=64, small="一個人走得快，一群人走得遠。", footL="傳給一個也在撐的朋友 →", footL_hint=True))
mf = []
for theme in PAL:
    for folder, name, spec in JOBS:
        hdir = os.path.join(B, "html", theme, folder); os.makedirs(hdir, exist_ok=True)
        h = page(spec, theme).replace('top:1222px;line-height:40px', 'top:1196px;line-height:72px')
        hp = os.path.join(hdir, name + ".html"); open(hp, "w", encoding="utf-8").write(h)
        od = os.path.join(OUT, folder, theme); os.makedirs(od, exist_ok=True)
        mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, name + ".png"), B), W=1080, H=1350, key=f"{folder}/{theme}/{name}", safe=None))
json.dump(mf, open(B + "/manifest_first.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
