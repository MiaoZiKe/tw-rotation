# 第十三輪：〈股立方〉六個面＋大盤的簡易圖示
# 兩套：① 線條圖示（24×24、currentColor，網站可直接用、自動跟深淺主題變色） ② 彩色徽章（96×96 霧面玻璃底，對外宣傳用）
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'line'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'badge'), exist_ok=True)

def arc_pts(cx, cy, r, a0, a1, k=16):
    return [(cx + r*math.cos(math.radians(a0 + (a1-a0)*i/k)), cy + r*math.sin(math.radians(a0 + (a1-a0)*i/k))) for i in range(k+1)]
def pl(p): return ' '.join(f'{x:.2f},{y:.2f}' for x, y in p)

def flow(c):   # 資金面：兩段輪動箭頭＋盤心
    o = []
    for a0, a1 in ((205, 335), (25, 155)):
        p = arc_pts(12, 12, 7.5, a0, a1)
        o.append(f'<polyline points="{pl(p)}"/>')
        a = math.radians(a1); tx, ty = -math.sin(a), math.cos(a); nx, ny = math.cos(a), math.sin(a)
        x, y = p[-1]
        o.append(f'<polyline points="{x-tx*3+nx*2.6:.2f},{y-ty*3+ny*2.6:.2f} {x:.2f},{y:.2f} {x-tx*3-nx*2.6:.2f},{y-ty*3-ny*2.6:.2f}"/>')
    o.append(f'<circle cx="12" cy="12" r="2.2" fill="{c["acc"]}" stroke="none"/>')
    return o

def chips(c):  # 籌碼面：一疊籌碼
    o = []   # 由下往上畫，上層的白底才不會蓋掉下層的弧線
    for y in (14.1, 10.3, 6.5):
        o.append(f'<path d="M4.5 {y} v3.8 A7.5 2.6 0 0 0 19.5 {y+3.8:.1f} V{y}" fill="{c["fill"]}"/>')
    o.append(f'<ellipse cx="12" cy="6.5" rx="7.5" ry="2.6" fill="{c["fill"]}"/>')
    o.append(f'<path d="M9.5 6.5 h5" stroke="{c["acc"]}"/>')
    return o

def chain(c):  # 產業面：上游 → 樞紐 → 下游
    N = [(4.5, 6.5), (4.5, 17.5), (19.5, 6.5), (19.5, 17.5)]
    o = [f'<path d="{"".join(f"M{x} {y}L12 12" for x, y in N)}"/>']
    o += [f'<circle cx="{x}" cy="{y}" r="2.2" fill="{c["fill"]}"/>' for x, y in N]
    o.append(f'<circle cx="12" cy="12" r="2.9" fill="{c["acc"]}" stroke="none"/>')
    return o

def candle(c): # 技術面：三根 K 棒（紅漲綠跌；線條版空心＝漲、實心＝跌）
    o = []
    for x, w0, w1, b0, b1, up in ((5.5, 9, 19, 12, 17, True), (12, 4, 15, 6.5, 12, False), (18.5, 5, 20, 8, 15.5, True)):
        col = c['rise'] if up else c['fall']
        o.append(f'<path d="M{x} {w0}V{w1}" stroke="{col}"/>')
        o.append(f'<rect x="{x-1.9}" y="{b0}" width="3.8" height="{b1-b0}" rx=".7" stroke="{col}" fill="{(c["fill"] if up else col)}"/>')
    return o

def event(c):  # 事件面：脈衝＋警示點
    return ['<polyline points="2,13 6.5,13 9,6 12.5,19 15,10 16.5,13 22,13"/>',
            f'<circle cx="19" cy="5.5" r="2.2" fill="{c["acc"]}" stroke="none"/>']

def fund(c):   # 基本面：財報（文件＋營收上升線）
    return [f'<rect x="4.5" y="2.8" width="15" height="18.4" rx="2.6" fill="{c["fill"]}"/>',
            '<path d="M8 7.2h5"/>', '<polyline points="8,16.5 10.8,13 13.2,14.6 16.2,10"/>',
            f'<circle cx="16.2" cy="10" r="1.5" fill="{c["acc"]}" stroke="none"/>']

def gauge(c):  # 大盤儀表（不屬於六面，是外圈刻度）
    p = arc_pts(12, 14, 8.5, 180, 360)
    o = [f'<polyline points="{pl(p)}"/>']
    for a in (200, 240, 270, 300, 340):
        r = math.radians(a)
        o.append(f'<path d="M{12+8.5*math.cos(r):.2f} {14+8.5*math.sin(r):.2f}L{12+6.4*math.cos(r):.2f} {14+6.4*math.sin(r):.2f}"/>')
    o.append('<path d="M12 14L16.6 8.6"/>')
    o.append(f'<circle cx="12" cy="14" r="2.2" fill="{c["acc"]}" stroke="none"/>')
    o.append('<path d="M5 19.5h14"/>')
    return o

ICONS = [('flow', '資金面', '錢往哪個族群跑', flow, ('#ffe3f1', '#e2daff', '#cfeeff')),
         ('chips', '籌碼面', '誰在買、誰在賣', chips, ('#d9f0ff', '#e4dcff', '#ffe0ee')),
         ('chain', '產業面', '上下游誰最強', chain, ('#b8ddff', '#d6c8ff', '#ffcde4')),
         ('tech', '技術面', '什麼時候進場', candle, ('#ffc4dc', '#dcc6ff', '#b9d4ff')),
         ('event', '事件面', '有沒有理由不進場', event, ('#e6dcff', '#ffd6e8', '#d2ecff')),
         ('fund', '基本面', '現在貴不貴', fund, ('#ffe9d6', '#f3dcff', '#d6e6ff')),
         ('market', '大盤儀表', '今天大環境如何（外圈）', gauge, ('#eef1f6', '#e3e8f2', '#f6efe6'))]

LINE = dict(acc='currentColor', fill='none', rise='currentColor', fall='currentColor')
BADGE = dict(acc='#f08a4b', fill='#ffffff', rise='#e0526a', fall='#23a37a')

for key, name, q, fn, (g0, g1, g2) in ICONS:
    body = '\n'.join(fn(LINE))
    # 線條版：技術面的跌 K 用實心＝currentColor
    open(os.path.join(HERE, 'line', f'{key}.svg'), 'w').write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><title>{name}</title>\n{body}\n</svg>\n')
    bb = '\n'.join(fn(BADGE))
    open(os.path.join(HERE, 'badge', f'{key}.svg'), 'w').write(
        f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96"><title>{name}</title>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{g0}"/><stop offset=".55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient></defs>
<rect x="3" y="3" width="90" height="90" rx="24" fill="url(#g)" stroke="#ffffff" stroke-width="4"/>
<rect x="11" y="11" width="74" height="74" rx="17" fill="#ffffff" fill-opacity=".2" stroke="#ffffff" stroke-opacity=".7" stroke-width="1.5"/>
<g transform="translate(19.2 19.2) scale(2.4)" fill="none" stroke="#4552a6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
{bb}
</g></svg>
''')

# 一支 sprite：網站用 <svg><use href="faces.svg#face-flow"/></svg>
sym = []
for key, name, q, fn, _ in ICONS:
    sym.append(f'<symbol id="face-{key}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><title>{name}</title>{"".join(fn(LINE))}</symbol>')
open(os.path.join(HERE, 'faces.svg'), 'w').write('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' + '\n'.join(sym) + '\n</svg>\n')

# 總覽頁
rows = ''.join(f'''<div class="it"><img class="bd" src="badge/{k}.svg"><div class="nm">{n}</div><div class="q">{q}</div>
<div class="ln dk">{''.join(f'<span style="width:{s}px;height:{s}px">'+open(os.path.join(HERE,'line',k+'.svg')).read().split('?>')[-1]+'</span>' for s in (48,24,16))}</div>
<div class="ln lt">{''.join(f'<span style="width:{s}px;height:{s}px">'+open(os.path.join(HERE,'line',k+'.svg')).read()+'</span>' for s in (48,24,16))}</div></div>''' for k, n, q, _, _ in ICONS)
open(os.path.join(HERE, '_sheet.html'), 'w').write(f'''<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#141f38;color:#f6efe6;font-family:"WenQuanYi Zen Hei",sans-serif;padding:48px;width:1500px}}
h1{{margin:0;font-size:34px;font-weight:600;letter-spacing:.1em}} .mono{{font-family:"DejaVu Sans Mono";color:#f2b48c;letter-spacing:.3em;font-size:14px;margin:10px 0 16px}}
.sub{{color:#c9b9a8;font-size:16px;line-height:1.85;margin:0 0 28px}}
.g{{display:grid;grid-template-columns:repeat(7,1fr);gap:16px}}
.it{{background:#1a2744;border:1px solid #2d3f66;border-radius:18px;padding:22px 10px 16px;display:flex;flex-direction:column;align-items:center;gap:8px}}
.it:last-child{{border-style:dashed}}
.bd{{width:120px;height:120px}} .nm{{font-size:24px;font-weight:600;margin-top:6px}} .q{{font-size:14px;color:#f2b48c;text-align:center;min-height:20px}}
.ln{{display:flex;gap:14px;align-items:center;justify-content:center;width:100%;padding:12px 0;border-radius:12px;margin-top:4px}}
.ln.dk{{color:#e8eefc;background:#0f1830}} .ln.lt{{color:#2b3350;background:#fbf3e6}}
.ln span{{display:inline-flex}} .ln svg{{width:100%;height:100%}}
.foot{{margin-top:26px;color:#c9b9a8;font-size:15px;line-height:1.9}} code{{color:#f2b48c}}
</style></head><body><h1>股立方｜六個面的簡易圖示</h1><div class="mono">6 FACES + MARKET GAUGE // LINE 24px + GLASS BADGE</div>
<p class="sub">每個面一個圖：<b>資金</b>＝輪動箭頭、<b>籌碼</b>＝一疊籌碼（字面意思）、<b>產業</b>＝上游→樞紐→下游、<b>技術</b>＝K 棒、<b>事件</b>＝脈衝＋警示點、<b>基本</b>＝財報。第七個虛線框的「大盤儀表」不屬於六面，是立方外圈的刻度。<br>
上排：彩色徽章（對外宣傳、介紹頁）。下兩排：線條圖示在深色／米色底的 48、24、16px —— 線條版只用一個顏色，放進網站會自動跟著深淺主題變色。</p>
<div class="g">{rows}</div>
<p class="foot">檔案：<code>line/*.svg</code>（線條、currentColor）、<code>badge/*.svg</code>（彩色徽章）、<code>faces.svg</code>（一支 sprite，網站用 <code>&lt;svg&gt;&lt;use href="faces.svg#face-flow"/&gt;&lt;/svg&gt;</code>）。<br>
線條版的技術面用「空心＝漲、實心＝跌」區分；徽章版照台股慣例紅漲綠跌。</p></body></html>''')
