# 三款 LOGO 草圖：純向量／排版。輸出 SVG、PNG 512、IG 圓形頭像預覽。
F = "'Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
L = {
 'logo1_小喘息': ('#F4EEE2', f'''<g fill="none" stroke="#A23E2B" stroke-width="12" stroke-linecap="round"><path d="M176 190 A80 80 0 0 1 336 190"/><path d="M204 190 A52 52 0 0 1 308 190" opacity=".7"/><path d="M230 190 A26 26 0 0 1 282 190" opacity=".45"/></g>
<text x="256" y="330" text-anchor="middle" font-family="{F}" font-size="92" font-weight="900" letter-spacing="6" fill="#2B2622">小喘息</text>'''),
 'logo2_慢慢來': ('#2E2A57', f'''<circle cx="256" cy="196" r="62" fill="#D5CEE8"/><circle cx="286" cy="174" r="54" fill="#2E2A57"/>
<text x="256" y="350" text-anchor="middle" font-family="{F}" font-size="92" font-weight="900" letter-spacing="6" fill="#F4F1FB">慢慢來</text>'''),
 'logo3_晚安信箱': ('#FFE98A', f'''<g fill="none" stroke="#2E2A22" stroke-width="12" stroke-linejoin="round" stroke-linecap="round"><rect x="186" y="124" width="140" height="96" rx="10"/><path d="M190 132 L256 186 L322 132"/></g>
<text x="256" y="324" text-anchor="middle" font-family="{F}" font-size="68" font-weight="900" letter-spacing="4" fill="#2E2A22">晚安信箱</text>'''),
}
for n, (bg, g) in L.items():
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><rect width="512" height="512" fill="{bg}"/>{g}</svg>'
    open(f'{n}.svg', 'w', encoding='utf-8').write(svg)
    open(f'_{n}.html', 'w', encoding='utf-8').write(f'<!doctype html><meta charset=utf-8><style>body{{margin:0;background:#fff}}.c{{width:512px;height:512px;border-radius:50%;overflow:hidden}}</style><body><div id=s>{svg}</div></body>')
