"""比較總覽：每格上方灰字標編號與風格名，格外下方標設計理由；第六格放 0.36 倍縮圖（手機縮小可讀檢查）。用法：python make_title_compare.py <出圖目錄>"""
import sys, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); CW = 520; CH = round(CW * 1350 / 1080)
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
cells = "".join(f'<div class="c"><div class="lb">{n}　{T.STYLES[n]}</div><img src="{b(O/f"title_{n}.png")}" width="{CW}" height="{CH}"><div class="rs">{T.REASON[n]}</div></div>' for n in range(1, 6))
thumbs = f'<img src="{b(O/"title_5.png")}" width="389" height="486">'
cells += f'<div class="c"><div class="lb">手機 0.36 倍（以字最細的第 5 款為例）</div><div class="th">{thumbs}</div><div class="rs">縮到 389 px 寬：極細的「透明說」與副標仍可讀；其餘四款字重較粗，同樣可讀。</div></div>'
html = f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:{CW*3+4*40}px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px;display:grid;grid-template-columns:repeat(3,{CW}px);gap:36px 40px}}.lb{{font-size:30px;font-weight:700;color:#6B7689;margin-bottom:10px}}.rs{{font-size:24px;line-height:34px;color:#3C4659;margin-top:12px;width:{CW}px}}.th{{display:flex;flex-wrap:wrap;gap:12px;width:{CW}px}}img{{display:block}}</style>{cells}'
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": CW*3+160, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_compare.png"), full_page=True); br.close()
f.unlink()
