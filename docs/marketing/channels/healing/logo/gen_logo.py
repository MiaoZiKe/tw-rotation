# 三款 LOGO 草圖（純向量／排版；名稱用 strategy.md 候選）。python3 gen_logo.py && node render_logo.js
F = "'Noto Serif TC','Source Han Serif TC','WenQuanYi Zen Hei',serif"
LI = dict(bg='#FBF4EA', ink='#3B2F2A', acc='#A34A30'); DK = dict(bg='#2B2622', ink='#F6EBDD', acc='#C8A58E')
def l1(c):  # 把燈留著：字標＋燈光弧
    return f'''<circle cx="256" cy="186" r="14" fill="{c['acc']}"/><path d="M214 186 A42 42 0 0 1 298 186" fill="none" stroke="{c['acc']}" stroke-width="8" stroke-linecap="round" opacity=".8"/>
<text x="256" y="300" text-anchor="middle" font-family="{F}" font-size="74" font-weight="900" letter-spacing="4" fill="{c['ink']}">把燈留著</text>'''
def l2(c):  # 今天先這樣就好：兩行字標＋手繪底線
    return f'''<text x="256" y="236" text-anchor="middle" font-family="{F}" font-size="66" font-weight="900" letter-spacing="4" fill="{c['ink']}">今天先</text>
<text x="256" y="318" text-anchor="middle" font-family="{F}" font-size="66" font-weight="900" letter-spacing="4" fill="{c['ink']}">這樣就好</text>
<path d="M170 342 C 215 330, 270 350, 342 336" fill="none" stroke="{c['acc']}" stroke-width="8" stroke-linecap="round"/>'''
def l3(c):  # 沒關係的房間：圓章＋窗
    return f'''<circle cx="256" cy="256" r="180" fill="none" stroke="{c['acc']}" stroke-width="8"/>
<rect x="238" y="148" width="36" height="46" rx="6" fill="none" stroke="{c['acc']}" stroke-width="7"/>
<text x="256" y="262" text-anchor="middle" font-family="{F}" font-size="58" font-weight="900" letter-spacing="3" fill="{c['ink']}">沒關係</text>
<text x="256" y="332" text-anchor="middle" font-family="{F}" font-size="58" font-weight="900" letter-spacing="3" fill="{c['ink']}">的房間</text>'''
for n, f in [('logo1_把燈留著', l1), ('logo2_今天先這樣就好', l2), ('logo3_沒關係的房間', l3)]:
    for tag, c in [('淺', LI), ('深', DK)]:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" fill="{c["bg"]}"/>{f(c)}</svg>'
        open(f'{n}_{tag}.svg', 'w', encoding='utf-8').write(svg)
