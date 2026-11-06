"""比較總覽：每格上方灰字標編號與風格名，格外下方標設計理由；第六格放 0.36 倍縮圖（手機縮小可讀檢查）。用法：python make_title_compare.py <出圖目錄>"""
import sys, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); CW = 520; CH = round(CW * 1350 / 1080)
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
REASON2 = {2: "色塊把「透明」做成淡藍玻璃格，兩格加藍框、五格間距統一 6px；照片加高 50px 補滿方塊到標籤的空白。",
           5: "「廣達」900 深藍、「透明說」200 品牌藍：粗與細的對比就是透明感；透明說下緣離標籤 53px。"}
def cell(n):
    return (f'<div class="c"><div class="lb">{n}　{T.STYLES[n]}</div><div class="pr"><img src="{b(O/f"title_{n}.png")}" width="{CW}" height="{CH}">'
            f'<div><img src="{b(O/f"title_{n}.png")}" width="389" height="486"><div class="rs" style="width:389px">↑ 手機 0.36 倍</div></div></div><div class="rs" style="width:921px">{REASON2[n]}</div></div>')
cells = cell(2) + cell(5)
html = f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:{921*2+120}px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px;display:grid;grid-template-columns:repeat(2,921px);gap:36px 40px}}.lb{{font-size:30px;font-weight:700;color:#6B7689;margin-bottom:10px}}.rs{{font-size:24px;line-height:34px;color:#3C4659;margin-top:12px}}img{{display:block}}.pr{{display:flex;gap:12px;align-items:flex-start}}</style>{cells}'
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 921*2+120, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_compare.png"), full_page=True); br.close()
f.unlink()
