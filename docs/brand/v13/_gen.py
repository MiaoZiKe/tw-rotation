# 第十三輪：〈股立方〉六個面＋大盤的簡易圖示
# 兩套：① 線條圖示（24×24、currentColor，網站可直接用、自動跟深淺主題變色） ② 彩色徽章（96×96 霧面玻璃底，對外宣傳用）
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'line'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'badge'), exist_ok=True)

def arc_pts(cx, cy, r, a0, a1, k=16):
    return [(cx + r*math.cos(math.radians(a0 + (a1-a0)*i/k)), cy + r*math.sin(math.radians(a0 + (a1-a0)*i/k))) for i in range(k+1)]
def pl(p): return ' '.join(f'{x:.2f},{y:.2f}' for x, y in p)

# 配色鍵（第十五輪起）：每個面一點顏色。線條版（LINE）全部是 currentColor／none，維持單色、跟著網站主題變色；
# 徽章與立方面上的圖示才傳入下面這些鍵。沒傳的鍵一律退回原本的單色（c.get(鍵, 預設)）。
#   flowline 資金分流線  n1/n2/n3 三個族群終點  trend 走勢線  area 走勢面積  hot 橘色強調點（基本／事件／產業／大盤）
#   chip 籌碼本體填色  chipacc 籌碼頂面強調線  core 晶片內方塊填色

def flow(c):   # 資金面：分流圖（網站「資金去向」光纖分流的簡易版）—— 左邊一個來源，三條粗細不同的平滑曲線流到右邊三個族群
    o = []
    line = c.get('flowline')
    for y, w in ((5.2, 2.8), (12, 1.9), (18.8, 1.2)):   # 線越粗＝流過去的錢越多
        o.append(f'<path d="M4.2 12C11 12 11.5 {y} 17.6 {y}" stroke-width="{w}"' + (f' stroke="{line}"' if line else '') + '/>')
    for y, k in ((5.2, 'n1'), (12, 'n2'), (18.8, 'n3')):   # 右邊三個族群節點用實心點，避免跟「分享」那種空心圈圖示混淆
        o.append(f'<circle cx="19.9" cy="{y}" r="2.2" fill="{c.get(k, c["ink"])}" stroke="none"/>')
    o.append(f'<circle cx="4.2" cy="12" r="2.6" fill="{c["acc"]}" stroke="none"/>')
    return o

def chips(c):  # 籌碼面：一疊籌碼（第十三輪最早的版本，Andy 第十五輪要求改回）
    o = []   # 由下往上畫，上層的填色才不會蓋掉下層的弧線
    body = c.get('chip', c['fill'])
    for y in (14.1, 10.3, 6.5):
        o.append(f'<path d="M4.5 {y} v3.8 A7.5 2.6 0 0 0 19.5 {y+3.8:.1f} V{y}" fill="{body}"/>')
    o.append(f'<ellipse cx="12" cy="6.5" rx="7.5" ry="2.6" fill="{body}"/>')
    o.append(f'<path d="M9.5 6.5 h5" stroke="{c.get("chipacc", c["acc"])}"/>')
    return o

def chain(c):  # 產業面：IC 晶片（Andy 給的圖一）—— 方形外框、四邊針腳、中間內方塊，內方塊中心一個節點
    o = [f'<rect x="6" y="6" width="12" height="12" rx="2" fill="{c["fill"]}"/>']
    o.append('<path d="' + ''.join(f'M{t} 6V3M{t} 18V21M6 {t}H3M18 {t}H21' for t in (9, 12, 15)) + '"/>')
    o.append(f'<rect x="9.4" y="9.4" width="5.2" height="5.2" rx="1" fill="{c.get("core", "none")}"/>')
    o.append(f'<circle cx="12" cy="12" r=".95" fill="{c.get("hot", c["acc"])}" stroke="none"/>')
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
            f'<circle cx="19" cy="5.5" r="2.2" fill="{c.get("hot", c["acc"])}" stroke="none"/>']

def fund(c):   # 基本面：走勢圖（L 形座標軸＋走勢折線＋末端一點；徽章版加淡淡的面積）。不用紅綠，免得跟漲跌混淆
    o = []
    if c.get('area'):
        o.append(f'<polygon points="7,16.5 10.5,12.5 13.5,14.5 19,7 19,19.6 7,19.6" fill="{c["area"]}" fill-opacity="{c.get("area_op", .16)}" stroke="none"/>')
    trend = c.get('trend')
    o += ['<path d="M4 3.5V20H21.5"/>', '<polyline points="7,16.5 10.5,12.5 13.5,14.5 19,7"' + (f' stroke="{trend}"' if trend else '') + '/>',
          f'<circle cx="19" cy="7" r="2" fill="{c.get("hot", c["acc"])}" stroke="none"/>']
    return o

def gauge(c):  # 大盤儀表（不屬於六面，是外圈刻度）
    p = arc_pts(12, 14, 8.5, 180, 360)
    o = [f'<polyline points="{pl(p)}"/>']
    for a in (200, 240, 270, 300, 340):
        r = math.radians(a)
        o.append(f'<path d="M{12+8.5*math.cos(r):.2f} {14+8.5*math.sin(r):.2f}L{12+6.4*math.cos(r):.2f} {14+6.4*math.sin(r):.2f}"/>')
    hot = c.get('hot')
    o.append('<path d="M12 14L16.6 8.6"' + (f' stroke="{hot}"' if hot else '') + '/>')
    o.append(f'<circle cx="12" cy="14" r="2.2" fill="{c.get("hot", c["acc"])}" stroke="none"/>')
    o.append('<path d="M5 19.5h14"/>')
    return o

ICONS = [('flow', '資金面', '錢往哪個族群跑', flow, ('#ffe3f1', '#e2daff', '#cfeeff')),
         ('chips', '籌碼面', '誰在買、誰在賣', chips, ('#d9f0ff', '#e4dcff', '#ffe0ee')),
         ('chain', '產業面', '上下游誰最強', chain, ('#b8ddff', '#d6c8ff', '#ffcde4')),
         ('tech', '技術面', '什麼時候進場', candle, ('#ffc4dc', '#dcc6ff', '#b9d4ff')),
         ('event', '事件面', '有沒有理由不進場', event, ('#e6dcff', '#ffd6e8', '#d2ecff')),
         ('fund', '基本面', '現在貴不貴', fund, ('#ffe9d6', '#f3dcff', '#d6e6ff')),
         ('market', '大盤儀表', '今天大環境如何（外圈）', gauge, ('#eef1f6', '#e3e8f2', '#f6efe6'))]

LINE = dict(acc='currentColor', fill='none', rise='currentColor', fall='currentColor', ink='currentColor')
BADGE = dict(acc='#f08a4b', fill='#ffffff', rise='#e0526a', fall='#23a37a', ink='#4552a6', area='#4552a6',
             # 第十五輪：每個面一點配色（跟 v15 立方面上的圖示同一組）
             flowline='#1474d3', n1='#f08a4b', n2='#22a6a0', n3='#7b6cf0', trend='#1474d3', area_op=.22,
             hot='#f08a4b', chip='#e7b04a', chipacc='#e0526a', core='#22a6a0')

def main():
    for key, name, q, fn, (g0, g1, g2) in ICONS:
        body = '\n'.join(fn(LINE))
        # 線條版：技術面的跌 K 用實心＝currentColor
        open(os.path.join(HERE, 'line', f'{key}.svg'), 'w').write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><title>{name}</title>\n{body}\n</svg>\n')
        bb = '\n'.join(fn(BADGE))
        open(os.path.join(HERE, 'badge', f'{key}.svg'), 'w').write(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96"><title>{name}</title>\n'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{g0}"/><stop offset=".55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient></defs>\n'
            f'<rect x="3" y="3" width="90" height="90" rx="24" fill="url(#g)" stroke="#ffffff" stroke-width="4"/>\n'
            f'<rect x="11" y="11" width="74" height="74" rx="17" fill="#ffffff" fill-opacity=".2" stroke="#ffffff" stroke-opacity=".7" stroke-width="1.5"/>\n'
            f'<g transform="translate(19.2 19.2) scale(2.4)" fill="none" stroke="#4552a6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">\n'
            f'{bb}\n</g></svg>\n')

    # 一支 sprite：網站用 <svg><use href="faces.svg#face-flow"/></svg>
    sym = []
    for key, name, q, fn, _ in ICONS:
        sym.append(f'<symbol id="face-{key}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><title>{name}</title>{"".join(fn(LINE))}</symbol>')
    open(os.path.join(HERE, 'faces.svg'), 'w').write('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' + '\n'.join(sym) + '\n</svg>\n')

    # 總覽頁
    def ln(k):
        return open(os.path.join(HERE, 'line', k + '.svg')).read()
    def sizes(k):
        return ''.join(f'<span style="width:{s}px;height:{s}px">{ln(k)}</span>' for s in (48, 24, 16))
    rows = ''.join(f'<div class="it"><img class="bd" src="badge/{k}.svg"><div class="nm">{n}</div><div class="q">{q}</div>'
                   f'<div class="ln dk">{sizes(k)}</div><div class="ln lt">{sizes(k)}</div></div>'
                   for k, n, q, _, _ in ICONS)
    open(os.path.join(HERE, '_sheet.html'), 'w').write(f"""<!doctype html><html><head><meta charset="utf-8"><style>
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
<p class="sub">每個面一個圖：<b>資金</b>＝分流圖（網站「資金去向」的簡易版，線越粗錢越多）、<b>籌碼</b>＝一疊籌碼（字面意思）、<b>產業</b>＝晶片、<b>技術</b>＝K 棒、<b>事件</b>＝脈衝＋警示點、<b>基本</b>＝走勢圖（座標軸＋走勢線）。第七個虛線框的「大盤儀表」不屬於六面，是立方外圈的刻度。<br>
上排：彩色徽章（對外宣傳、介紹頁；每個面一點配色，技術面照台股慣例紅漲綠跌）。下兩排：線條圖示在深色／米色底的 48、24、16px —— 線條版只用一個顏色，放進網站會自動跟著深淺主題變色。</p>
<div class="g">{rows}</div>
<p class="foot">檔案：<code>line/*.svg</code>（線條、currentColor）、<code>badge/*.svg</code>（彩色徽章）、<code>faces.svg</code>（一支 sprite，網站用 <code>&lt;svg&gt;&lt;use href="faces.svg#face-flow"/&gt;&lt;/svg&gt;</code>）。產業面的檔名沿用 <code>chain</code>，圖已換成晶片。<br>
線條版的技術面用「空心＝漲、實心＝跌」區分；徽章版照台股慣例紅漲綠跌。</p></body></html>""")
    render_png()

def render_png():
    """用 Playwright 把總覽頁截成 六面圖示.png（容器沒有 Playwright 時略過）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('沒有 Playwright，略過 PNG'); return
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1596, 'height': 800})
        pg.goto('file://' + os.path.join(HERE, '_sheet.html')); pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(HERE, '六面圖示.png'), full_page=True); b.close()

if __name__ == '__main__':
    main()
