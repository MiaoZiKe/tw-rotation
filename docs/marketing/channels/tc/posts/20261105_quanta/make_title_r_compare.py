"""第二輪比較總覽：三款（上排全尺寸、中排 0.36 倍縮圖）＋同一款（R2）套鴻海／台積電／聯發科／鴻海精密。用法：python make_title_r_compare.py <出圖目錄>"""
import sys, base64
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); CW = 520; CH = round(CW * 1350 / 1080)
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
NAMES = {1: "R1　開口環＋深橘字", 2: "R2　開口環＋橘底深字膠囊", 3: "R3　藍實心膠囊白字＋深底橘字膠囊"}
WHY = {1: "公司名放進 LOGO 同款開口環（右上缺口＋橘點），透明說用加深橘 #C95F00（對淺底 3.8:1），不另加底。",
       2: "同一個開口環；透明說放進 LOGO 橘 #FF9F1C 的膠囊、深藍字（8.4:1）：圈＝被說的對象，橘塊＝我們打造的透明。",
       3: "兩個實心膠囊：藍底白字（公司）、深藍底橘字（透明說，橘字原色 #FF9F1C 對深底 8.4:1），最醒目、最像標籤。"}
TRY = [("鴻海", "foxconn"), ("台積電", "tsmc"), ("聯發科", "mediatek"), ("鴻海精密（4 字）", "four")]
for _, k in TRY: Image.open(O / f"title_try_{k}.png").resize((540, 675), Image.LANCZOS).save(O / f"title_try_{k}_s.png")
c1 = "".join(f'<div><div class="lb">{NAMES[i]}</div><img src="{b(O/f"title_r{i}.png")}" width="{CW}" height="{CH}"><div class="rs">{WHY[i]}</div></div>' for i in (1, 2, 3))
c2 = "".join(f'<div><div class="lb sm">0.36 倍（389 px 寬）</div><img src="{b(O/f"title_r{i}.png")}" width="389" height="486"></div>' for i in (1, 2, 3))
c3 = "".join(f'<div><div class="lb sm">R2 套「{n}」</div><img src="{b(O/f"title_try_{k}.png")}" width="260" height="325"></div>' for n, k in TRY)
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:{CW*3+160}px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}'
        f'.g{{display:flex;gap:40px;margin-bottom:36px}}.lb{{font-size:28px;font-weight:700;color:#6B7689;margin-bottom:10px}}.sm{{font-size:24px}}.rs{{font-size:23px;line-height:33px;color:#3C4659;margin-top:12px;width:{CW}px}}img{{display:block}}</style>'
        f'<div class="g">{c1}</div><div class="g">{c2}</div><div class="g">{c3}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": CW*3+160, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_r_compare.png"), full_page=True); br.close()
f.unlink()
