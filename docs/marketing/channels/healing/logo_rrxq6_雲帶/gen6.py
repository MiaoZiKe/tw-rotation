# 「日日小晴」LOGO：以第二輪 07 雲帶缺口優化（2026-11-05 Andy：「用這張LOGO 優化 日日小晴 有對應到文字最好」）
# A 雲帶日字：雲帶排成一個「日」字，中間那一橫斷開，露出小太陽 → 日＋小晴
# B 日日雲帶：兩個雲帶「日」字並排，左邊整條是雲（昨天），右邊中間露出小太陽（今天）→ 日日＋小晴
# C 原版精修：保留原構圖，三層雲帶像一天一天疊上來，缺口裡的小太陽加短光芒
# 字標：「晴」的日字旁點成太陽橘，和圖示的小太陽呼應
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq2'))
os.chdir(os.path.join(H, '..', 'logo_rrxq2')); import gen; os.chdir(H)
TONES, L = gen.TONES, gen.L
def cloud_bar(x1, x2, y, bx, c, h=76, bump=1):
    s = f'<rect x="{x1}" y="{y}" width="{x2-x1}" height="{h}" rx="{h/2}" fill="{c}"/>'
    if bump: s += f'<circle cx="{bx}" cy="{y+h*.29}" r="{h*.6}" fill="{c}"/>'
    return s
def sun(P, cx, cy, r, rays=False):
    mono = P.get('mono'); ink = P['ink']
    s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{P["bg"] if mono else P["S"]}" stroke="{ink if mono else "none"}" stroke-width="12"/>'
    return s
def ri(P, cx, cy, sc=1, sunny=True, bumps=(-60, 70), X=170, Y=250, tops=False):
    """一個直立的雲帶「日」字（寬 ±X、高 ±Y）：外框是「日」字的筆畫，中間一橫是兩朵雲；sunny＝中橫斷開露出小太陽"""
    c = P['C']; g = f'<g transform="translate({cx} {cy}) scale({sc})">'
    def top(y, bx):
        r = f'<rect x="{-X}" y="{y}" width="{2*X}" height="70" rx="35" fill="{c}"/>'
        if tops and y < 0: r += f'<circle cx="{bx}" cy="{y+8}" r="44" fill="{c}"/><circle cx="{bx+52}" cy="{y+20}" r="32" fill="{c}"/>'
        return r
    g += top(-Y, bumps[0]) + top(Y-70, bumps[1])
    g += f'<rect x="{-X}" y="{-Y+20}" width="54" height="{2*Y-40}" rx="27" fill="{c}"/><rect x="{X-54}" y="{-Y+20}" width="54" height="{2*Y-40}" rx="27" fill="{c}"/>'
    if sunny:
        w = X-80
        g += (f'<rect x="{-X}" y="-32" width="{w}" height="64" rx="32" fill="{c}"/><circle cx="{-X+w-30}" cy="-22" r="30" fill="{c}"/>'
              f'<rect x="80" y="-32" width="{w}" height="64" rx="32" fill="{c}"/><circle cx="110" cy="-22" r="30" fill="{c}"/>')
        g += '</g>'
        return g, (cx, cy, 52*sc)
    g += f'<rect x="{-X}" y="-32" width="{2*X}" height="64" rx="32" fill="{c}"/><circle cx="-10" cy="-26" r="34" fill="{c}"/></g>'
    return g, None
def sA(P):
    a, (x, y, r) = ri(P, 0, 0, X=200, Y=230)
    return L('a', a) + L('b', sun(P, x, y, r))
def sB(P):
    a1, _ = ri(P, -104, 0, .56, sunny=False, bumps=(-30, -90), tops=True); a2, (x, y, r) = ri(P, 104, 0, .56, tops=True)
    return L('a', a1 + a2) + L('b', sun(P, x, y, r))
def sC(P):
    c = P['C']; ink = P['ink']; mono = P.get('mono')
    bars = cloud_bar(-250, 110, -200, -60, c) + cloud_bar(-280, -130, -40, -200, c) + cloud_bar(130, 280, -40, 205, c) + cloud_bar(-100, 270, 120, 150, c)
    s = sun(P, 0, 0, 72)
    col = ink if mono else P['S']
    glow = '' if mono else f'<circle cx="0" cy="0" r="100" fill="{P["S"]}" opacity=".22"/>'
    return L('a', bars) + L('b', glow + s)
VAR = [('A', 'A_雲帶日字', '雲帶日字', '雲帶排成一個「日」字，中間那一橫斷開，露出一顆小太陽：日子裡的一小段晴。', '日→雲帶排成的「日」字', '小晴→中間斷開處的小太陽', sA),
       ('B', 'B_日日雲帶', '日日雲帶', '兩個雲帶「日」字並排：左邊整天都是雲，右邊中間露出小太陽。一天接一天，總會等到一小段晴。', '日日→並排的兩個雲帶「日」字', '小晴→右邊那個「日」中間的小太陽', sB),
       ('C', 'C_原版精修', '原版精修', '保留原本的雲帶缺口：三層雲帶像一天一天疊上來，缺口裡的小太陽多了一圈柔和的光暈。', '日日→一層一層疊上來的雲帶', '小晴→缺口裡的小太陽', sC)]
WH = 420
def wm_svg(P, sym, k, sub, bg=True):
    ink = P['ink']; kind = 'sans'; ls = 14
    fs = 150 if not sub else 134; ty = 210 if not sub else 170; symsz = 372
    tw = gen.text_w(gen.NAME, kind, fs, ls); x0 = 60+symsz+54; W = int(x0+tw+70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    txt = gen.TX(gen.NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls)
    if not P.get('mono'):  # 「晴」的日字旁點成太陽橘
        qx = x0 + gen.text_w('日日小', kind, fs, ls) + ls
        txt += (f'<clipPath id="qc"><rect x="{qx}" y="{ty-.7*fs}" width="{.355*fs}" height="{1.4*fs}"/></clipPath>'
                f'<g clip-path="url(#qc)">' + gen.TX('晴', kind, fs, qx, ty+.36*fs, P['S']) + '</g>')
    body += L('txt', txt)
    if sub: body += L('sub', gen.TX(gen.SUB, 'sans', 44, x0, 345, ink, ls=7))
    bgr = f'<rect width="{W}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{gen.defs(P)}</defs>{bgr}{body}</svg>', W
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq6'
os.makedirs(CHK, exist_ok=True)
if __name__ == '__main__':
    K = {'A': (1.46, .6), 'B': (1.5, .6), 'C': (1.33, .55)}
    jobs = []
    for v, fo, nm, mean, m1, m2, fn in VAR:
        os.makedirs(fo, exist_ok=True); ka, kw = K[v]
        for tag, P in TONES.items():
            sym = fn(P)
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, sym, ka)); jobs.append(dict(v=v, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in (True, False):
                    if not bg and P.get('mono'): continue
                    sv, W = wm_svg(P, sym, kw, sub, bg); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(v=v, kind='wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=not bg))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/{v}av.svg', 'w').write(gen.avatar_svg(P, sym, ka, bg=False))
        for lay in ('a', 'b'):
            jobs.append(dict(v=v, kind='chkav', layer=lay, svg=f'{CHK}/{v}av.svg', png=f'{CHK}/{v}av_{lay}.png', w=1080, h=1080, transparent=True, show=[lay]))
        sv, W = wm_svg(P, sym, kw, True, bg=False); open(f'{CHK}/{v}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            jobs.append(dict(v=v, kind='chkwm', layer=lay, svg=f'{CHK}/{v}wm.svg', png=f'{CHK}/{v}wm_{lay}.png', w=W, h=WH, transparent=True, show=([lay, 'a', 'b'] if lay == 'sym' else [lay])))
    json.dump(dict(jobs=jobs, var=[v[:6] for v in VAR]), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
