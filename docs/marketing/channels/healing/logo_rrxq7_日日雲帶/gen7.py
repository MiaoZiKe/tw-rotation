# 「日日小晴」LOGO：B 日日雲帶 的 12 種變化（2026-11-05 Andy：「B 還可以但在多點變化」）
# 共同骨架：兩個「日」字＝日日；右邊（今天）中間露出小太陽＝小晴；左邊（昨天）中間是雲
# 重跑：python3 gen7.py && node render.js && python3 fit7.py && python3 gen7.py && node render.js && python3 post7.py
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq2'))
os.chdir(os.path.join(H, '..', 'logo_rrxq2')); import gen; os.chdir(H)
TONES, L = gen.TONES, gen.L
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq7'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
def blend(a, b, t):
    a = [int(a[i:i+2], 16) for i in (1, 3, 5)]; b = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x+(y-x)*t):02X}' for x, y in zip(a, b))
def SUN(P): return P['bg'] if P.get('mono') else P['S']
def sun(P, cx, cy, r):
    m = P.get('mono'); return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SUN(P)}" stroke="{P["ink"] if m else "none"}" stroke-width="10"/>'
def rays(P, cx, cy, r1, r2, n=8, w=12, a0=0, a1=360):
    col = P['ink'] if P.get('mono') else P['S']; return gen.rays(cx, cy, r1, r2, n, w, col, a0, a1)
def glyph(cx, cy, sc, col, mid, P, X=170, Y=250, sw=54, tops=True, bump=(-30, 30), scallop=False, fill_extra=''):
    """一個直立的「日」字：外框＋中橫。mid='cloud' 中橫是雲；'sun' 中橫斷開露出小太陽；回傳 (svg, 太陽座標或 None)"""
    g = f'<g transform="translate({cx} {cy}) scale({sc})" {fill_extra}>'
    g += f'<rect x="{-X}" y="{-Y}" width="{2*X}" height="70" rx="35" fill="{col}"/><rect x="{-X}" y="{Y-70}" width="{2*X}" height="70" rx="35" fill="{col}"/>'
    g += f'<rect x="{-X}" y="{-Y+20}" width="{sw}" height="{2*Y-40}" rx="{sw/2}" fill="{col}"/><rect x="{X-sw}" y="{-Y+20}" width="{sw}" height="{2*Y-40}" rx="{sw/2}" fill="{col}"/>'
    if scallop:
        n = 4
        for i in range(n): g += f'<circle cx="{-X+45+i*(2*X-90)/(n-1)}" cy="{-Y+18}" r="{44 if i%2==0 else 36}" fill="{col}"/>'
    elif tops:
        g += f'<circle cx="{bump[0]}" cy="{-Y+8}" r="44" fill="{col}"/><circle cx="{bump[0]+52}" cy="{-Y+20}" r="32" fill="{col}"/>'
    if mid == 'cloud':
        g += f'<rect x="{-X}" y="-32" width="{2*X}" height="64" rx="32" fill="{col}"/><circle cx="{bump[1]-20}" cy="-26" r="40" fill="{col}"/><circle cx="{bump[1]+34}" cy="-18" r="30" fill="{col}"/>'
        return g+'</g>', None
    w = X-80
    g += (f'<rect x="{-X}" y="-32" width="{w}" height="64" rx="32" fill="{col}"/><circle cx="{-X+w-30}" cy="-22" r="30" fill="{col}"/>'
          f'<rect x="80" y="-32" width="{w}" height="64" rx="32" fill="{col}"/><circle cx="110" cy="-22" r="30" fill="{col}"/>')
    return g+'</g>', (cx, cy, 52*sc)
C = lambda P: P['C']
WARM = lambda P: P['ink'] if P.get('mono') else blend(P['C'], P['S'], .55)
# ---------- 12 種變化 ----------
def v1(P):  # 原版 B
    a, _ = glyph(-104, 0, .56, C(P), 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(104, 0, .56, C(P), 'sun', P)
    return L('a', a+b) + L('b', sun(P, x, y, r))
def v2(P):  # 冷暖兩日：昨天灰雲色，今天暖橘色
    a, _ = glyph(-104, 0, .56, C(P), 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(104, 0, .56, WARM(P), 'sun', P)
    return L('a', a+b) + L('b', sun(P, x, y, r))
def v3(P):  # 連筆日日：兩個「日」共用中間那一直筆，連成一個字
    c = C(P); X = 330; Y = 140; sw = 34
    s = (f'<rect x="{-X}" y="{-Y}" width="{2*X}" height="44" rx="22" fill="{c}"/><rect x="{-X}" y="{Y-44}" width="{2*X}" height="44" rx="22" fill="{c}"/>'
         + ''.join(f'<rect x="{x-sw/2}" y="{-Y+10}" width="{sw}" height="{2*Y-20}" rx="{sw/2}" fill="{c}"/>' for x in (-X+sw/2, 0, X-sw/2))
         + f'<circle cx="-200" cy="{-Y+4}" r="30" fill="{c}"/><circle cx="-166" cy="{-Y+12}" r="22" fill="{c}"/><circle cx="170" cy="{-Y+4}" r="30" fill="{c}"/>'
         + f'<rect x="{-X}" y="-20" width="{X}" height="40" rx="20" fill="{c}"/><circle cx="-160" cy="-16" r="28" fill="{c}"/><circle cx="-120" cy="-10" r="20" fill="{c}"/>'
         + f'<rect x="10" y="-20" width="72" height="40" rx="20" fill="{c}"/><rect x="{X-82}" y="-20" width="72" height="40" rx="20" fill="{c}"/>')
    return L('a', s) + L('b', sun(P, 165, 0, 36) + rays(P, 165, 0, 50, 64, 8, 9))
def v4(P):  # 太陽露臉：昨天雲遮住半顆太陽，今天整顆露出來
    a, _ = glyph(-104, 0, .56, C(P), 'sun', P); b, (x, y, r) = glyph(104, 0, .56, C(P), 'sun', P)
    cl = C(P); hide = (f'<circle cx="-104" cy="0" r="29" fill="{SUN(P)}" stroke="{P["ink"] if P.get("mono") else "none"}" stroke-width="10"/>'
                       f'<rect x="-150" y="0" width="92" height="34" rx="17" fill="{cl}"/><circle cx="-118" cy="2" r="22" fill="{cl}"/><circle cx="-88" cy="6" r="18" fill="{cl}"/>')
    return L('a', a+b) + L('b', sun(P, x, y, r) + rays(P, x, y, 40, 52, 8, 8)) + L('c', hide)
def v5(P):  # 一步一步：今天比昨天高一點點
    a, _ = glyph(-104, 34, .56, C(P), 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(104, -34, .56, C(P), 'sun', P)
    sp = ''.join(f'<path d="M {px} {py-16} L {px+5} {py-5} L {px+16} {py} L {px+5} {py+5} L {px} {py+16} L {px-5} {py+5} L {px-16} {py} L {px-5} {py-5} Z" fill="{SUN(P) if not P.get("mono") else P["ink"]}"/>' for px, py in ((212, -190), (236, -140)))
    return L('a', a+b) + L('b', sun(P, x, y, r)) + L('c', sp)
def v6(P):  # 雲邊日日：上緣做成蓬蓬的雲朵邊
    a, _ = glyph(-104, 10, .56, C(P), 'cloud', P, scallop=True, bump=(-30, -90)); b, (x, y, r) = glyph(104, 10, .56, C(P), 'sun', P, scallop=True)
    return L('a', a+b) + L('b', sun(P, x, y, r))
def v7(P):  # 光從今天溢出來：右邊的「日」上方灑出光芒
    a, _ = glyph(-104, 30, .56, C(P), 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(104, 30, .56, WARM(P), 'sun', P, tops=False)
    return L('a', a+b) + L('b', sun(P, x, y, r)) + L('c', rays(P, 104, -110, 52, 96, 5, 14, -160, -20))
def v8(P):  # 蠟筆手繪：同一個構圖，邊緣有手抖的筆觸
    s = v1(P); return f'<g filter="url(#rough)">{s}</g>'
def v9(P):  # 單線稿：細線勾出兩個「日」，只有小太陽是實心
    ink = P['ink']; mono = P.get('mono'); col = ink
    def g(cx, sunny):
        s = f'<g transform="translate({cx} 0)" fill="none" stroke="{col}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">'
        s += '<rect x="-92" y="-138" width="184" height="276" rx="26"/>'
        if sunny: s += '<path d="M -92 0 L -46 0 M 46 0 L 92 0"/></g>'
        else: s += '<path d="M -92 0 L -40 0 C -40 -26 -6 -34 4 -14 C 14 -30 44 -24 44 0 L 92 0"/></g>'
        return s
    return L('a', g(-112, False) + g(112, True)) + L('b', sun(P, 112, 0, 28) + ('' if mono else f'<circle cx="112" cy="0" r="40" fill="none" stroke="{P["S"]}" stroke-width="5" opacity=".6"/>'))
def v10(P):  # 印章：太陽橘的方印，日日留白
    mono = P.get('mono'); base = P['ink'] if mono else P['S']; cut = P['bg']
    s = f'<g filter="url(#rough)"><rect x="-250" y="-200" width="500" height="400" rx="46" fill="{base}"/></g>'
    a, _ = glyph(-104, 0, .5, cut, 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(104, 0, .5, cut, 'sun', P)
    return L('a', s + a + b) + L('b', f'<circle cx="{x}" cy="{y}" r="{r}" fill="{cut}"/><circle cx="{x}" cy="{y}" r="{r*.5}" fill="{base}"/>')
def v11(P):  # 黏土立體：圓潤厚實、帶陰影與高光
    c = C(P); hi = P['bg'] if P.get('mono') else blend(c, '#FFFFFF', .45)
    a, _ = glyph(-104, 0, .56, c, 'cloud', P, bump=(-30, -90), fill_extra='filter="url(#sh)"'); b, (x, y, r) = glyph(104, 0, .56, c, 'sun', P, fill_extra='filter="url(#sh)"')
    hl = ''.join(f'<rect x="{cx-76}" y="-128" width="60" height="10" rx="5" fill="{hi}" opacity=".9"/>' for cx in (-104, 104))
    sg = '' if P.get('mono') else f'<circle cx="{x-9}" cy="{y-9}" r="9" fill="#FFFFFF" opacity=".55"/>'
    return L('a', a+b+hl) + L('b', sun(P, x, y, r) + sg)
def v12(P):  # 一大一小：昨天是大大的雲天，今天是小小的晴
    a, _ = glyph(-80, 0, .66, C(P), 'cloud', P, bump=(-30, -90)); b, (x, y, r) = glyph(150, 46, .42, C(P), 'sun', P)
    return L('a', a+b) + L('b', sun(P, x, y, r*1.15))
VAR = [
 (1, '01_原版日日雲帶', '原版', '兩個「日」並排：左邊整天是雲，右邊中間露出小太陽。', v1),
 (2, '02_冷暖兩日', '冷暖兩日', '昨天是灰灰的雲色，今天的「日」換成暖暖的橘：日子慢慢回溫。', v2),
 (3, '03_連筆日日', '連筆日日', '兩個「日」共用中間那一筆，連成一整排：日子是連著的，晴在最後一格。', v3),
 (4, '04_太陽露臉', '太陽露臉', '昨天太陽被雲遮住半張臉，今天整顆露出來：等一下就晴了。', v4),
 (5, '05_一步一步', '一步一步', '今天的「日」比昨天高一點點，旁邊閃兩下：一天往上走一小步。', v5),
 (6, '06_雲邊日日', '雲邊日日', '兩個「日」的上緣做成蓬蓬的雲朵邊，雲感最重：雲還在，但光已經出來。', v6),
 (7, '07_光溢出來', '光溢出來', '今天的「日」是暖色，光從上面灑出來：一小段晴，藏不住。', v7),
 (8, '08_蠟筆手繪', '蠟筆手繪', '同一個構圖，邊緣有手畫的抖動：像每天在手帳上畫一格。', v8),
 (9, '09_單線稿', '單線稿', '細線勾出兩個「日」，左邊中橫拱成一朵小雲，右邊只有小太陽是實心的。', v9),
 (10, '10_日日印章', '日日印章', '一方太陽橘的印，蓋下「日日」：每天蓋一個章，今天這格是晴。', v10),
 (11, '11_黏土日日', '黏土日日', '圓潤厚實的黏土字，帶陰影和高光：軟軟的、摸得到的日子。', v11),
 (12, '12_一大一小', '一大一小', '昨天是大大的陰天，今天是小小的晴：晴不用很大，剛好就好。', v12),
]
WH = 420
def wm_svg(P, sym, k, sub, bg=True):
    ink = P['ink']; kind = 'sans'; ls = 14
    fs = 150 if not sub else 134; ty = 210 if not sub else 170; symsz = 372
    tw = gen.text_w(gen.NAME, kind, fs, ls); x0 = 60+symsz+54; W = int(x0+tw+70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    txt = gen.TX(gen.NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls)
    if not P.get('mono'):
        qx = x0 + gen.text_w('日日小', kind, fs, ls) + ls
        txt += (f'<clipPath id="qc"><rect x="{qx}" y="{ty-.7*fs}" width="{.355*fs}" height="{1.4*fs}"/></clipPath>'
                f'<g clip-path="url(#qc)">' + gen.TX('晴', kind, fs, qx, ty+.36*fs, P['S']) + '</g>')
    body += L('txt', txt)
    if sub: body += L('sub', gen.TX(gen.SUB, 'sans', 44, x0, 345, ink, ls=7))
    bgr = f'<rect width="{W}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{gen.defs(P)}</defs>{bgr}{body}</svg>', W
if __name__ == '__main__':
    jobs = []
    for n, fo, nm, mean, fn in VAR:
        os.makedirs(fo, exist_ok=True)
        far = FIT.get(str(n), 300); ka = min(420/far, 1.8); kw = min(172/far, 1.2)
        for tag, P in TONES.items():
            sym = fn(P)
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, sym, ka)); jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in (True, False):
                    if not bg and P.get('mono'): continue
                    sv, W = wm_svg(P, sym, kw, sub, bg); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=not bg))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/{n}fit.svg', 'w').write(gen.avatar_svg(P, sym, 1.0, bg=False)); jobs.append(dict(n=n, kind='fit', svg=f'{CHK}/{n}fit.svg', png=f'{CHK}/{n}fit.png', w=1080, h=1080, transparent=True))
        sv, W = wm_svg(P, sym, kw, True, bg=False); open(f'{CHK}/{n}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            jobs.append(dict(n=n, kind='chkwm', layer=lay, svg=f'{CHK}/{n}wm.svg', png=f'{CHK}/{n}wm_{lay}.png', w=W, h=WH, transparent=True, show=([lay, 'a', 'b', 'c'] if lay == 'sym' else [lay])))
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
