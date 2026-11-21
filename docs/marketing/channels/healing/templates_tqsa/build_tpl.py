# 「談晴說礙」第一篇（版本 A）輪播模板 5 張，1080×1350（IG 直式 4:5）
# 依 eval_quote_accounts.md 改良公式：短句、圖佔約 2/3、結尾一個好回答的問題＋標記朋友
# 左上角 LOGO 暫用 logo_tqsa 06 雲朵對話框（Andy 定款後換掉 LOGO_N 即可）
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_tqsa'))
os.chdir(os.path.join(H, '..', 'logo_tqsa')); import gen_tq; os.chdir(H)
LOGO_N = int(os.environ.get('LOGO_N', 6))
TONE = os.environ.get('TONE', '奶油晨光')
P = gen_tq.TONES[TONE]; fn = dict((v[0], v[4]) for v in gen_tq.VAR)[LOGO_N]
INK, BG, S, C = P['ink'], P['bg'], P['S'], P['C']
G = gen_tq.blend(C, INK, .45); Q = gen_tq.blend(S, INK, .28)  # 文字用的「晴」橘，淺底上對比較夠
def logo():
    return f'<svg viewBox="-280 -280 560 560" width="92" height="92"><defs>{gen_tq.gen.defs(P)}</defs>{fn(P)}</svg>'
def cloud(cx, cy, s, col, op=1):
    return (f'<g transform="translate({cx} {cy}) scale({s})" fill="{col}" opacity="{op}"><circle cx="-60" cy="0" r="70"/><circle cx="20" cy="-30" r="90"/>'
            f'<circle cx="100" cy="10" r="60"/><rect x="-130" y="0" width="290" height="70" rx="35"/></g>')
def band(x, y, w, col, h=60):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{col}"/><circle cx="{x+w*.35}" cy="{y+h*.25}" r="{h*.62}" fill="{col}"/>'
def rays(cx, cy, r1, r2, n, w, a0=0, a1=360):
    return gen_tq.gen.rays(cx, cy, r1, r2, n, w, S, a0, a1)
# 各張插畫（畫布 960×820）
ILL = {
 1: band(110, 150, 520, C) + band(60, 400, 230, C) + band(670, 400, 230, C) + band(330, 640, 560, C)
    + f'<circle cx="480" cy="430" r="150" fill="{S}" opacity=".22"/><circle cx="480" cy="430" r="110" fill="{S}"/>',
 2: (f'<g transform="rotate(-4 480 420)"><rect x="200" y="110" width="560" height="620" rx="26" fill="#FFFFFF" stroke="{C}" stroke-width="10"/>'
     + ''.join(f'<line x1="260" y1="{y}" x2="700" y2="{y}" stroke="{C}" stroke-width="8" stroke-linecap="round" opacity=".7"/>' for y in (300, 380, 460, 540, 620))
     + ''.join(f'<circle cx="230" cy="{y}" r="12" fill="{C}"/>' for y in (170, 250, 330, 410, 490, 570, 650))
     + f'<circle cx="640" cy="200" r="48" fill="{S}"/>' + rays(640, 200, 62, 84, 8, 8) + '</g>'
     + f'<g transform="rotate(32 770 560)"><rect x="740" y="380" width="48" height="300" rx="14" fill="{G}"/><polygon points="740,680 788,680 764,730" fill="{S}"/></g>'),
 3: cloud(330, 260, 1.5, C, .55) + cloud(620, 380, 1.7, C, .8) + cloud(360, 560, 1.9, C),
 4: cloud(260, 520, 1.6, C) + cloud(720, 560, 1.5, C) + f'<circle cx="490" cy="330" r="160" fill="{S}" opacity=".2"/><circle cx="490" cy="330" r="118" fill="{S}"/>' + rays(490, 330, 150, 215, 10, 18, -200, 20),
 5: cloud(470, 330, 2.3, C) + f'<path d="M 330 470 L 230 690 L 450 480 Z" fill="{C}"/>'
    + f'<circle cx="500" cy="360" r="98" fill="{BG}"/><circle cx="500" cy="360" r="74" fill="{S}"/>',
}
SL = [
 (1, '談晴，也說礙', '說這一代的難，也說還在的光。'),
 (2, '我們是觀察者', '記錄這一代年輕人，怎麼過日子。'),
 (3, '有些難，說清楚了', '才知道，不是只有你不夠努力。'),
 (4, '但我們也看見晴', '再硬的日子，這一代還是很會在縫裡找光。'),
 (5, '每天說一點礙，也談一點晴', '你今天的一小段晴是什麼？'),
]
CSS = f"""*{{margin:0;padding:0;box-sizing:border-box}}body{{width:1080px;height:1350px;background:{BG};font-family:'Noto Sans CJK TC',sans-serif;color:{INK};position:relative;overflow:hidden}}
.hd{{position:absolute;left:56px;top:48px;display:flex;align-items:center;gap:18px}}
.nm{{font-size:40px;font-weight:700;letter-spacing:6px}}.nm .q{{color:{Q}}}.nm .a{{color:{G}}}
.ill{{position:absolute;left:60px;top:170px;width:960px;height:820px}}
.tt{{position:absolute;left:72px;right:72px;top:1010px;font-size:76px;font-weight:900;line-height:1.2;letter-spacing:2px}}
.sb{{position:absolute;left:72px;right:72px;top:1120px;font-size:44px;font-weight:500;line-height:1.45;color:{INK}}}
.pg{{position:absolute;right:56px;top:66px;font-size:30px;font-weight:700;color:{G}}}
.ft{{position:absolute;left:72px;bottom:46px;font-size:28px;color:{G};letter-spacing:2px}}"""
os.makedirs('out', exist_ok=True); jobs = []
for n, tt, sb in SL:
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'<div class="hd" data-k="logo">{logo()}<div class="nm">談<span class="q">晴</span>說<span class="a">礙</span></div></div>'
            f'<div class="pg" data-k="pg">{n}/5</div>'
            f'<svg class="ill" data-k="ill" viewBox="0 0 960 820">{ILL[n]}</svg>'
            f'<div class="tt" data-k="tt">{tt}</div><div class="sb" data-k="sb">{sb}</div>'
            + (f'<div class="ft" data-k="ft">標記一個也在撐的朋友 →</div>' if n == 5 else '') + '</body></html>')
    p = f'out/{n:02d}_{TONE}.html'; open(p, 'w').write(html); jobs.append(dict(html=p, png=f'out/{n:02d}_{TONE}.png'))
json.dump(jobs, open(f'jobs_{TONE}.json', 'w'), ensure_ascii=False); print(len(jobs))
