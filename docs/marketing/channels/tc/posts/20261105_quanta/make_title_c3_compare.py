"""第五輪比較總覽。用法：python make_title_c3_compare.py <出圖目錄> c3|sub"""
import sys, base64, json
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); mode = sys.argv[2]
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/(f+".png"))}" width="{w}" height="{round(w*1350/1080)}">'
fs = lambda k: json.load(open(O / f"overlap_{k}.json"))["font"]
CSSB = (f'{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:28px;margin-bottom:30px;align-items:flex-start}}'
        '.lb{font-size:28px;font-weight:700;color:#6B7689;margin-bottom:8px}.sm{font-size:21px}.rs{font-size:22px;line-height:32px;color:#3C4659;margin-top:10px}.rc{font-size:22px;line-height:32px;color:#B85400;font-weight:700;margin-top:6px}img{display:block}.cap{font-size:24px;color:#3C4659;margin:0 0 10px}')
if mode == "c3":
    svg = Path(sys.argv[3]).read_text(encoding="utf8")
    logo = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    top = (f'<div><div class="lb">LOGO 圖示（對照）</div><img src="{logo}" width="400" height="400"><div class="rs" style="width:400px">缺口在右上、橘點在缺口正中間</div></div>'
           f'<div><div class="lb">A　缺口加大、橫向膠囊 224×82</div>{img("title_c3A", 480)}</div><div><div class="lb">B　膠囊縮小 170×64、缺口較小</div>{img("title_c3B", 480)}</div>')
    mid = "".join(f'<div><div class="lb sm">{n}</div>{img(f, 389)}</div>' for f, n in [("title_c3A", "A 廣達 389px"), ("title_c3B", "B 廣達 389px"), ("try_c3A_tokyo_a", "A 東京威力(a) 一行"), ("try_c3A_tokyo_b", "A 東京威力(b) 2×2"), ("try_c3B_tokyo_a", "B 東京威力(a) 一行"), ("try_c3B_tokyo_b", "B 東京威力(b) 2×2")])
    tr = [("hon", "鴻海"), ("tsmc", "台積電"), ("tokyo_a", "東京威力(a)"), ("tokyo_b", "東京威力(b)"), ("asml", "ASML")]
    bot = "".join(f'<div><div class="lb sm">{v}　{n}　{fs(f"try_c3{v}_{k}")}px</div>{img(f"try_c3{v}_{k}", 250)}</div>' for v in "AB" for k, n in tr)
    html = f'<!doctype html><meta charset="utf-8"><style>{CSSB}body{{width:2560px}}</style><div class="g">{top}</div><div class="cap">↓ 389 px 寬實際縮圖</div><div class="g">{mid}</div><div class="cap">↓ 試套公司名（上排 A、下排 B）</div><div class="g">{"".join(bot.split("</div></div><div><div class=\"lb sm\">B")[0:1])}</div>'
    # 試套分兩排
    rowA = "".join(f'<div><div class="lb sm">A　{n}　{fs(f"try_c3A_{k}")}px</div>{img(f"try_c3A_{k}", 250)}</div>' for k, n in tr)
    rowB = "".join(f'<div><div class="lb sm">B　{n}　{fs(f"try_c3B_{k}")}px</div>{img(f"try_c3B_{k}", 250)}</div>' for k, n in tr)
    html = f'<!doctype html><meta charset="utf-8"><style>{CSSB}body{{width:2300px}}</style><div class="g">{top}</div><div class="cap">↓ 389 px 寬實際縮圖</div><div class="g">{mid}</div><div class="cap">↓ 試套公司名（上排 A 版、下排 B 版）</div><div class="g">{rowA}</div><div class="g">{rowB}</div>'
    out, W = "title_c3_compare.png", 2380
else:
    items = [(1, "右側兩行錯落", "「茶水間」放大、「常聊的那些」縮小縮排，像標題與註解，節奏有高低；字級 68／48。"),
             (2, "右側直排", "中文直書貼著圓右側，與圓同高，像書籤；佔橫向最少，字級 54。"),
             (3, "圓下方", "圓縮小到 330、副標在正下方靠圓左緣對齊（四周留白最多，右側空）；字級 56。"),
             (4, "旁白引號", "橘色「」加左側藍色細直線，像一句旁白；字級 52。"),
             (5, "沿下半弧", "副標沿圓環外側下半弧排，跟著圓走；字級 46，兩端字略傾斜，389px 下較吃力。")]
    rec = {1: "推薦第 2 名", 2: "", 3: "", 4: "推薦第 1 名：最像一句話、讀起來最順，又保留圓的主角地位", 5: "不推薦：兩端字傾斜、縮圖下字高僅約 17px"}
    cells = "".join(f'<div><div class="lb">{n}　{t}</div>{img(f"title_sub_{n}", 440)}<div class="rs" style="width:440px">{why}</div><div class="rc">{rec[n]}</div></div>' for n, t, why in items)
    thumbs = "".join(f'<div>{img(f"title_sub_{n}", 389)}</div>' for n, _, _ in items[:4])
    html = f'<!doctype html><meta charset="utf-8"><style>{CSSB}body{{width:2380px}}</style><div class="g">{cells}</div><div class="cap">↓ 389 px 寬實際縮圖（1～4）</div><div class="g">{thumbs}</div>'
    out, W = "title_sub_compare.png", 2460
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": W, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / out), full_page=True); br.close()
f.unlink()
