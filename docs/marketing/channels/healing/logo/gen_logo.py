# 三款 LOGO 草圖（純向量／排版）。頭像只放符號；字標另做橫式版；各有單色三版。
# 用法：python3 gen_logo.py && node render_logo.js && python3 sheet.py
import json
SER = "'Noto Serif CJK TC',serif"
PAL = {'淺': dict(bg='#FBF4EA', ink='#3B2F2A', acc='#A34A30'), '深': dict(bg='#2B2622', ink='#F6EBDD', acc='#C8A58E'),
       '單色黑': dict(bg='#FFFFFF', ink='#000000', acc='#000000'), '單色白': dict(bg='#000000', ink='#FFFFFF', acc='#FFFFFF'),
       '單色主色': dict(bg='#FBF4EA', ink='#A34A30', acc='#A34A30')}
SW = 15   # 符號線寬（單位座標），頭像放大 1.6 倍後在 44px 下約 2px
def sym(n, c):  # 單位座標，以 (0,0) 為中心，半徑約 100
    a, k = c['acc'], c['ink']
    op = ' opacity=".8"' if c['bg'] in ('#FBF4EA','#2B2622') and c['acc'] != c['ink'] else ''
    if n == 1:  # 把燈留著：一點燈光＋兩道弧
        return f'<circle cx="0" cy="41" r="17" fill="{a}"/><path d="M-56 41 A56 56 0 0 1 56 41" fill="none" stroke="{a}" stroke-width="{SW}" stroke-linecap="round"/><path d="M-92 41 A92 92 0 0 1 92 41" fill="none" stroke="{a}" stroke-width="{SW}" stroke-linecap="round"{op}/>'
    if n == 2:  # 今天先這樣就好：一口氣的手繪弧線＋停頓的點
        return f'<circle cx="0" cy="-48" r="17" fill="{a}"/><path d="M-92 24 C-46 4, 8 48, 92 16" fill="none" stroke="{a}" stroke-width="{SW}" stroke-linecap="round"/>'
    # 3 沒關係的房間：圓章＋拱形十字窗（有窗格與窗台，不像手機）
    return f'<circle r="96" fill="none" stroke="{a}" stroke-width="14"/><path d="M-32 42 V-12 A32 32 0 0 1 32 -12 V42 Z" fill="none" stroke="{a}" stroke-width="14" stroke-linejoin="round"/><path d="M0 -42 V44 M-30 12 H30" stroke="{a}" stroke-width="14"/><path d="M-46 56 H46" stroke="{a}" stroke-width="14" stroke-linecap="round"/>'
NAMES = {1: ('把燈留著', 120), 2: ('今天先這樣就好', 96), 3: ('沒關係的房間', 110)}
FILES = {}
for n, (name, fs) in NAMES.items():
    for tag, c in PAL.items():
        av = f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" fill="{c["bg"]}"/><g transform="translate(256 256) scale(1.6)">{sym(n, c)}</g></svg>'
        wm = f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="400" viewBox="0 0 1400 400"><rect width="1400" height="400" fill="{c["bg"]}"/><g transform="translate(200 200) scale(1.3)">{sym(n, c)}</g><text x="400" y="{200+fs*0.36:.0f}" font-family="{SER}" font-size="{fs}" font-weight="700" letter-spacing="6" fill="{c["ink"]}">{name}</text></svg>'
        open(f'logo{n}_{name}_頭像_{tag}.svg', 'w', encoding='utf-8').write(av)
        open(f'logo{n}_{name}_橫式_{tag}.svg', 'w', encoding='utf-8').write(wm)
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
res = {t: dict(符號對底=cr(c['acc'], c['bg']), 字標對底=cr(c['ink'], c['bg'])) for t, c in PAL.items()}
json.dump(res, open('contrast.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(res)
