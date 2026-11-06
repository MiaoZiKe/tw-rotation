"""R2 定稿比較：修改前、修改後並排＋389px 實際縮圖＋四張試套。用法：python make_title_r2_final.py <出圖目錄>（需有 title_r2_before.png）"""
import sys, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); CW = 520; CH = round(CW * 1350 / 1080)
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/f)}" width="{w}" height="{round(w*1350/1080)}">'
TRY = [("鴻海", "foxconn"), ("台積電", "tsmc"), ("聯發科", "mediatek"), ("鴻海精密（4 字）", "four")]
top = (f'<div><div class="lb">修改前</div>{img("title_r2_before.png", CW)}</div><div><div class="lb">修改後（定稿）</div>{img("title_r2.png", CW)}</div>'
       f'<div><div class="lb">修改後 0.36 倍（389 px 寬）</div>{img("title_r2.png", 389)}<div class="rs">環線粗 22；橘點 34 在環外緣線上；環內距 56、橘膠囊內距 40；橘膠囊高 168 與環置中；環與膠囊間距 27。</div></div>')
tr = "".join(f'<div><div class="lb sm">套「{n}」</div>{img(f"title_try_{k}.png", 380)}</div>' for n, k in TRY)
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:1700px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:40px;margin-bottom:36px;align-items:flex-start}}'
        f'.lb{{font-size:28px;font-weight:700;color:#6B7689;margin-bottom:10px}}.sm{{font-size:24px}}.rs{{font-size:23px;line-height:33px;color:#3C4659;margin-top:12px;width:389px}}img{{display:block}}</style><div class="g">{top}</div><div class="g">{tr}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 1780, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_r2_final_compare.png"), full_page=True); br.close()
f.unlink()
