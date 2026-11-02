"""科技透明圈 LOGO 第一輪：8 個方向（無 AI 圖，座標格＋一致圓角的向量符號）。
用法：python build.py <字型根目錄>  （字型根目錄內含 npm pack 解開的 fontsource-* 套件）
字型授權：全部 SIL OFL 1.1（可商用）；字型檔不進 repo。
"""
import sys, math, pathlib, json
from playwright.sync_api import sync_playwright

FONTS = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(__file__).resolve().parent.parent
PK = {
 'noto': ('fontsource-noto-sans-tc-5.3.1', [500, 700, 900]),
 'huninn': ('fontsource-huninn-5.3.1', [400]),
 'mplus': ('fontsource-m-plus-rounded-1c-5.3.0', [700]),
 'zen': ('fontsource-zen-maru-gothic-5.3.1', [700]),
 'lxgw': ('fontsource-lxgw-wenkai-tc-5.3.1', [700]),
}
FONT_CSS = ''.join(f'<link rel="stylesheet" href="file://{FONTS}/{d}/package/{w}.css">' for d, ws in PK.values() for w in ws)
FAM = {'noto': "'Noto Sans TC'", 'huninn': "'Huninn'", 'mplus': "'M PLUS Rounded 1c'", 'zen': "'Zen Maru Gothic'", 'lxgw': "'LXGW WenKai TC'"}
BASE_FONT = "'Noto Sans TC',sans-serif"

def pol(cx, cy, r, deg):
    a = math.radians(deg); return cx + r * math.cos(a), cy + r * math.sin(a)

# ---------- 符號（viewBox 100，安全區 22~78，圓形裁切不會被切到）----------
def s1(v):  # 開口圈
    ring, dot = ('#1F6FEB', '#FF9F1C') if v == 'L' else ('#7CB8FF', '#FFC266')
    gap = 36; c = -45
    x0, y0 = pol(50, 50, 25, c + gap); x1, y1 = pol(50, 50, 25, c - gap + 360)
    dx, dy = pol(50, 50, 25, c)
    return (f'<path d="M{x0:.2f} {y0:.2f} A25 25 0 1 1 {x1:.2f} {y1:.2f}" fill="none" stroke="{ring}" stroke-width="9" stroke-linecap="round"/>'
            f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="6.6" fill="{dot}"/>')

def s2(v):  # 對話圈
    b, inner = ('#12A594', '#FFFFFF') if v == 'L' else ('#3FD3BE', '#0E2A30')
    return (f'<circle cx="50" cy="47" r="28" fill="{b}"/>'
            f'<path d="M30 66 L24 80 L42 72 Z" fill="{b}" stroke="{b}" stroke-width="6" stroke-linejoin="round"/>'
            f'<circle cx="50" cy="47" r="12" fill="none" stroke="{inner}" stroke-width="6.5"/>')

def s3(v):  # 透明重疊圓
    cols = ['#3E9BFF', '#22D3A5', '#FFC531']
    mode = 'multiply' if v == 'L' else 'screen'
    op = .78 if v == 'L' else .85
    pts = [pol(50, 50, 13, a) for a in (-90, 30, 150)]
    return '<g style="isolation:isolate">' + ''.join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="21" fill="{c}" fill-opacity="{op}" style="mix-blend-mode:{mode}"/>' for (x, y), c in zip(pts, cols)) + '</g>'

def s4(v, uid=[0]):  # 柔和漸層球
    uid[0] += 1; g = f'g{uid[0]}'
    a, b, c = ('#7DE3F4', '#8091FF', '#D49BFF') if v == 'L' else ('#6AD8EE', '#7384F5', '#C487F5')
    return (f'<defs><linearGradient id="{g}" x1="0.15" y1="0.1" x2="0.85" y2="0.95"><stop offset="0" stop-color="{a}"/><stop offset=".55" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient></defs>'
            f'<circle cx="50" cy="50" r="29" fill="url(#{g})"/>'
            f'<circle cx="50" cy="50" r="14" fill="#fff" fill-opacity=".26" stroke="#fff" stroke-opacity=".75" stroke-width="2.6"/>'
            f'<path d="M30.5 40 A21.5 21.5 0 0 1 44 28.5" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="4" stroke-linecap="round"/>')

def s5(v):  # 手寫圈
    loop, ink = ('#FFB400', '#1D2B3A') if v == 'L' else ('#FFC32B', '#F5F1E4')
    return (f'<path d="M23 54 C19 32 41 20 60 23 C81 27 85 52 73 68 C61 85 31 85 24 66 C20 56 22 45 31 36" fill="none" stroke="{loop}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<text x="51" y="64" font-family="\'LXGW WenKai TC\'" font-weight="700" font-size="40" text-anchor="middle" fill="{ink}">透</text>')

def s6(v):  # 幾何積木
    k = '#14263B' if v == 'L' else '#E8EEF5'
    return ('<circle cx="39" cy="39" r="11" fill="#2F6BFF"/>'
            '<path d="M54 28 L76 28 A22 22 0 0 1 54 50 Z" fill="#14B8A6"/>'
            '<path d="M28 76 A11 11 0 0 1 50 76 Z" fill="#FFB020"/>'
            f'<rect x="54" y="54" width="22" height="22" rx="6" fill="{k}"/>')

def s7(v):  # 單色字標
    ink, dot = ('#111827', '#00A38D') if v == 'L' else ('#FFFFFF', '#2EE6C5')
    return (f'<text x="47" y="68" font-family="\'Noto Sans TC\'" font-weight="700" font-size="56" text-anchor="middle" fill="{ink}">圈</text>'
            f'<circle cx="75" cy="64" r="4.6" fill="{dot}"/>')

def s8(v):  # 點陣圈
    base, hi = ('#0E7C86', '#FF9F1C') if v == 'L' else ('#5ED0D6', '#FFC266')
    out = []; hit = None; best = 9
    cells = [(i, j) for i in range(-3, 4) for j in range(-3, 4) if 2.35 <= math.hypot(i, j) <= 3.2]
    for (i, j) in cells:
        ang = math.degrees(math.atan2(j, i)); d = abs((ang + 45 + 180) % 360 - 180)
        if d < best: best, hit = d, (i, j)
    for (i, j) in cells:
        col = hi if (i, j) == hit else base
        out.append(f'<circle cx="{50 + i * 9.4:.1f}" cy="{50 + j * 9.4:.1f}" r="3.9" fill="{col}"/>')
    return ''.join(out)

CANDS = [
 # id, 名稱, 一句理念, 符號, 淺底 tile, 深底 tile, 字型, 字重, 強調色(橫式「圈」)
 dict(id='c1', name='開口圈', idea='一條開口的圓環＝「圈」：圈子是開放的，缺口的小圓點是進來的你。', fn=s1, bgL='#F1F6FD', bgD='#12233A', font='noto', w=700, acc=('#1F6FEB', '#7CB8FF')),
 dict(id='c2', name='對話圈', idea='圓形對話泡泡，中間挖一個空心圈：同業交流、坦白透明。', fn=s2, bgL='#ECF8F5', bgD='#0F262B', font='huninn', w=400, acc=('#12A594', '#3FD3BE')),
 dict(id='c3', name='透明疊圓', idea='三個半透明圓互相疊出新顏色：「透明」的字面意思，也是圈子重疊。', fn=s3, bgL='#F7F8FA', bgD='#15192A', font='mplus', w=700, acc=('#3E9BFF', '#7CB8FF')),
 dict(id='c4', name='柔光球', idea='柔和漸層的玻璃球，裡面一圈亮環：像手機 App 圖示一樣讓人想點。', fn=s4, bgL='#F4F5FD', bgD='#12162B', font='zen', w=700, acc=('#7A86F5', '#A5AEFF')),
 dict(id='c5', name='手寫圈', idea='螢光筆隨手畫一個圈、圈住「透」：像朋友在你筆記上畫重點。', fn=s5, bgL='#FFFCF2', bgD='#1B2230', font='lxgw', w=700, acc=('#F2A900', '#FFC32B')),
 dict(id='c6', name='積木圓', idea='圓、四分之一圓、半圓、方塊，像一組積木：科技知識一塊塊拼起來。', fn=s6, bgL='#F4F7FB', bgD='#14263B', font='noto', w=900, acc=('#2F6BFF', '#6C97FF')),
 dict(id='c7', name='單字標', idea='只有「圈」一個字加一顆薄荷點，黑白極簡，像 Notion 那種安靜的品牌。', fn=s7, bgL='#FFFFFF', bgD='#111827', font='noto', w=700, acc=('#00A38D', '#2EE6C5')),
 dict(id='c8', name='點陣圈', idea='小圓點排成一圈，一顆暖色點亮著：晶片接腳與載入中的休閒版。', fn=s8, bgL='#F1F7F8', bgD='#0F2630', font='noto', w=500, acc=('#0E7C86', '#5ED0D6')),
]

def svg_tile(c, v, size, shape='sq'):
    bg = c['bgL'] if v == 'L' else c['bgD']
    rx = {'sq': 22, 'ci': 50}[shape]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}">'
            f'<rect width="100" height="100" rx="{rx}" fill="{bg}"/>{c["fn"](v)}</svg>')

def lockup(c, v, h=64):
    ink, acc = ('#13263B', c['acc'][0]) if v == 'L' else ('#F1F5F9', c['acc'][1])
    ff = FAM[c['font']]
    return (f'<div style="display:flex;align-items:center;gap:{h*.28:.0f}px">{svg_tile(c, v, h)}'
            f'<div style="font-family:{ff},{BASE_FONT};font-weight:{c["w"]};font-size:{h*.62:.0f}px;color:{ink};letter-spacing:.02em;line-height:1">科技透明<span style="color:{acc}">圈</span></div></div>')

def profile(c, v, w=380):
    dark = v == 'D'
    bg, fg, sub, ln = ('#000', '#F3F5F7', '#8A9099', '#2A2D31') if dark else ('#fff', '#101418', '#6B7280', '#E5E7EB')
    ff = FAM[c['font']]
    return (f'<div style="width:{w}px;box-sizing:border-box;background:{bg};color:{fg};border-radius:16px;padding:20px 20px 16px;border:1px solid {ln};font-family:{BASE_FONT}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px"><div>'
            f'<div style="font-size:23px;font-weight:700">科技透明圈</div><div style="font-size:14px;color:{sub};margin-top:3px">tech.transparent</div></div>'
            f'<div style="border-radius:50%;overflow:hidden;width:76px;height:76px;flex:none">{svg_tile(c, v, 76, "ci")}</div></div>'
            f'<div style="font-size:15px;line-height:1.6;margin-top:14px">科技業的薪水、面試、製程，用真實經驗講白話</div>'
            f'<div style="margin-top:14px;border:1px solid {ln};border-radius:10px;text-align:center;padding:8px;font-size:14px;font-weight:700">追蹤</div></div>')

def page(body, w):
    return (f'<!doctype html><meta charset="utf-8">{FONT_CSS}<body style="margin:0;background:#ECEFF4;width:{w}px;font-family:{BASE_FONT};color:#13263B">{body}</body>')

def shot(pw_page, html, path, w, sel=None, scale=1, h=800):
    pw_page.set_viewport_size({'width': w, 'height': h})
    pw_page.set_content(html); pw_page.goto('about:blank') if False else None
    pw_page.evaluate('document.fonts.ready'); pw_page.wait_for_timeout(500)
    (pw_page.locator(sel).first if sel else pw_page).screenshot(path=str(path)) if sel else pw_page.screenshot(path=str(path), full_page=True)

def main():
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        # file:// 字型要從 file:// 頁面載入 → 先寫 html 檔
        def render(html, path, w, scale=1, sel=None):
            hp = OUT / 'src' / '_tmp.html'; hp.write_text(html, encoding='utf-8')
            ctx = br.new_context(viewport={'width': w, 'height': 800}, device_scale_factor=scale)
            pg = ctx.new_page(); pg.goto(f'file://{hp}'); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(700)
            if sel: pg.locator(sel).first.screenshot(path=str(path))
            else: pg.screenshot(path=str(path), full_page=True)
            ctx.close()
        for c in CANDS:
            d = OUT / f"{c['id']}_{c['name']}"; d.mkdir(exist_ok=True)
            for v, nm in (('L', 'light'), ('D', 'dark')):
                (d / f'icon_{nm}.svg').write_text(svg_tile(c, v, 512), encoding='utf-8')
                render(page(f'<div id="t" style="display:inline-block">{svg_tile(c, v, 1024)}</div>', 1024), d / f'icon_{nm}.png', 1024, 1, '#t')
                for s in (110, 40):
                    render(page(f'<div id="t" style="display:inline-block">{svg_tile(c, v, s, "ci")}</div>', 200), d / f'circle{s}_{nm}.png', 200, 1, '#t')
                bgc = '#fff' if v == 'L' else '#0E1726'
                render(page(f'<div id="t" style="display:inline-block;background:{bgc};padding:36px 56px;border-radius:0">{lockup(c, v, 96)}</div>', 900), d / f'horizontal_{nm}.png', 900, 2, '#t')
                render(page(f'<div id="t" style="display:inline-block">{profile(c, v)}</div>', 500), d / f'profile_{nm}.png', 500, 2, '#t')
        # 總覽
        cards = ''
        for i, c in enumerate(CANDS):
            cards += (f'<div style="background:#fff;border-radius:18px;padding:20px 22px;width:452px;box-sizing:border-box">'
                      f'<div style="display:flex;align-items:baseline;gap:10px"><b style="font-size:22px;color:#6B7A90">{i+1}</b><b style="font-size:26px">{c["name"]}</b></div>'
                      f'<div style="font-size:13px;color:#586879;line-height:1.55;margin:8px 0 14px;min-height:40px">{c["idea"]}</div>'
                      f'<div style="display:flex;gap:12px;align-items:flex-end">{svg_tile(c,"L",132)}{svg_tile(c,"D",132)}'
                      f'<div style="display:flex;flex-direction:column;gap:6px"><div style="display:flex;gap:8px;align-items:flex-end">{svg_tile(c,"L",110,"ci")}{svg_tile(c,"L",40,"ci")}</div>'
                      f'<div style="display:flex;gap:8px;align-items:flex-end">{svg_tile(c,"D",110,"ci")}{svg_tile(c,"D",40,"ci")}</div></div></div></div>')
        hdr = ('<div style="padding:30px 36px 6px"><div style="font-size:34px;font-weight:700">科技透明圈 LOGO：八個風格（2026-11-02）</div>'
               '<div style="font-size:15px;color:#586879;margin-top:8px">簡約休閒、不用吉祥物、無 AI 圖（座標格＋一致圓角的向量）；每張卡：方形圖示（淺／深）＋右側 IG 圓形 110／40px 實際像素（上淺下深，不放大）。字型 Noto Sans TC／粉圓 Huninn／M PLUS Rounded 1c／Zen Maru Gothic／霞鶩文楷 TC（皆 SIL OFL）。</div></div>')
        render(page(f'{hdr}<div style="display:flex;flex-wrap:wrap;gap:20px;padding:18px 36px 36px">{cards}</div>', 2000), OUT / 'overview.png', 2000, 1)
        # 細節
        rows = ''
        for i, c in enumerate(CANDS):
            rows += (f'<div style="background:#fff;border-radius:18px;padding:20px 24px;display:flex;gap:22px;align-items:center;margin-bottom:18px">'
                     f'<div style="width:150px"><b style="font-size:24px">{i+1}　{c["name"]}</b><div style="font-size:12.5px;color:#586879;margin-top:6px;line-height:1.5">{c["idea"]}</div></div>'
                     f'<div style="display:flex;flex-direction:column;gap:10px"><div style="padding:18px 24px;border:1px solid #E5E9F0;border-radius:12px">{lockup(c,"L",58)}</div>'
                     f'<div style="padding:18px 24px;border-radius:12px;background:#0E1726">{lockup(c,"D",58)}</div></div>'
                     f'{profile(c,"L",360)}{profile(c,"D",360)}</div>')
        hdr2 = '<div style="padding:30px 36px 10px"><div style="font-size:30px;font-weight:700">科技透明圈 LOGO：橫式 LOGO 與 Threads 個人頁模擬（淺／深）</div></div>'
        render(page(f'{hdr2}<div style="padding:10px 36px 30px">{rows}</div>', 1560), OUT / 'overview_detail.png', 1560, 1)
        br.close()
    (OUT / 'src' / '_tmp.html').unlink(missing_ok=True)

main()
