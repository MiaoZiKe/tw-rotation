"""廣達封面標題第二輪（2026-11-06 Andy：「太爛的，用原本的……公司名稱用圓圈（藍色），透明說用橘色，對應 LOGO」）。
版面沿用原版 1_cover（照片 1032x690 在上、下方一行標題＋副標、右下「右滑看透明圈」），只重做標題行。
用法：TITLE_R=1..3 [TC_COMPANY=廣達] [TC_OUTNAME=title_r1] python render_quanta.py <ASSETS> <OUT>
語彙取自 LOGO（icon_light.svg）：開口環 r=25、線粗 9（線粗＝直徑 0.18）、圓端點、缺口在右上（角度 -9°～-81°，中心 -45°）、橘點 r=6.6 落在缺口中心、同一條環線上。
公司名 2～4 字都放得進去 → 把圓環拉成膠囊（stadium），缺口與橘點仍在右上圓角處，線粗與點徑按 LOGO 比例縮放。
不用描邊加填色、漸層、發光、陰影。三款：
 R1 開口環＋深橘字（#C95F00，對淺底 3.8:1）；R2 開口環＋橘底深字膠囊（#FF9F1C 底、#0F1B33 字 8.4:1）；R3 藍實心膠囊白字（4.6:1）＋深底橘字膠囊（#FF9F1C 字 on #0F1B33 8.4:1）。"""
import io, json, math, os
from pathlib import Path
from PIL import Image
import title_styles as T

OUTER_H, SW, FS = 188, 22, 108          # 外框高、線粗（0.117×外高，較 LOGO 的 0.18 細，字才放得進）、字級
R = (OUTER_H - SW) / 2                  # 中心線半徑
DEEP = "#C95F00"


def ring_svg(n_chars, BLUE, ORG, solid=False):
    tw = n_chars * FS
    wr = tw + 2 * 58                    # 中心線寬（左右各留 46，含半個線粗）
    ow = wr + SW
    a = (wr - 2 * R) / 2                # 上緣直線半段
    x0, y0 = SW / 2, SW / 2             # 外框左上（中心線）
    cy = y0 + R; xl, xr = x0 + R, x0 + wr - R
    path = (f"M {(xl+xr)/2:.2f} {y0:.2f} H {xr:.2f} A {R:.2f} {R:.2f} 0 0 1 {xr:.2f} {y0+2*R:.2f} H {xl:.2f} "
            f"A {R:.2f} {R:.2f} 0 0 1 {xl:.2f} {y0:.2f} H {(xl+xr)/2:.2f}")
    Lp = 2 * (wr - 2 * R) + 2 * math.pi * R
    s = a + math.pi * R / 4             # 缺口中心：右圓角 -45° 處
    g = math.radians(72) * R            # LOGO 缺口 72°
    p0 = s + g / 2
    off = Lp - p0
    dx, dy = xr + R * math.cos(math.radians(-45)), cy + R * math.sin(math.radians(-45))
    dot = f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="{0.264*R:.2f}" fill="{ORG}"/>'
    if solid:
        body = f'<rect x="0" y="0" width="{ow:.1f}" height="{OUTER_H}" rx="{OUTER_H/2}" fill="{BLUE}"/>'
    else:
        body = (f'<path d="{path}" fill="none" stroke="{BLUE}" stroke-width="{SW}" stroke-linecap="round" stroke-dasharray="{Lp-g:.2f} {g:.2f}" stroke-dashoffset="{off:.2f}"/>' + dot)
    return ow, f'<svg data-k="ring" width="{ow:.1f}" height="{OUTER_H}" viewBox="0 0 {ow:.1f} {OUTER_H}" style="display:block">{body}</svg>'


def build(style, g, company):
    BG, INK, BLUE, ORG, GREY = (g[k] for k in ("BG", "INK", "BLUE", "ORG", "GREY"))
    global FS
    n = len(company); FS = min(108, (960 - 236) // (n + 3))   # 公司名越長字級越小（最小 96），確保整列不超過右邊界 1020
    ow, ring = ring_svg(n, BLUE, ORG, solid=(style == 3))
    photo = g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    PB = g["PIC_TOP"] + g["PIC_H"]
    SUB_H = 80
    GAP_ROW = 28
    low_h = g["H"] - PB - 40 - 72 - 16
    block = OUTER_H + GAP_ROW + SUB_H
    top = PB + (low_h - block) // 2
    co_color = "#fff" if style == 3 else INK
    if style == 1:
        sp = f'<div class="sp" data-k="shuo" style="color:{DEEP}">透明說</div>'; spw = 3 * FS
    elif style == 2:
        spw = 3 * FS + 72
        sp = f'<div class="pill" data-k="pill" style="width:{spw}px;background:{ORG}"></div><div class="sp" data-k="shuo" style="color:{INK};left:36px">透明說</div>'
    else:
        spw = 3 * FS + 72
        sp = f'<div class="pill" data-k="pill" style="width:{spw}px;background:{INK}"></div><div class="sp" data-k="shuo" style="color:{ORG};left:36px">透明說</div>'
    css = f"""
.trow{{position:absolute;left:60px;top:{top}px;height:{OUTER_H}px;display:flex;align-items:center;gap:26px}}
.rw{{position:relative;width:{ow:.1f}px;height:{OUTER_H}px;flex:none}}
.rw svg{{position:absolute;left:0;top:0}}
.cname{{position:absolute;left:0;top:0;width:{ow:.1f}px;height:{OUTER_H}px;line-height:{OUTER_H}px;text-align:center;font-weight:900;font-size:{FS}px;color:{co_color};white-space:nowrap}}
.sw5{{position:relative;width:{spw}px;height:{OUTER_H}px;flex:none}}
.pill{{position:absolute;left:0;top:0;height:{OUTER_H}px;border-radius:{OUTER_H//2}px}}
.sp{{position:absolute;left:0;top:0;line-height:{OUTER_H}px;font-weight:900;font-size:{FS}px;white-space:nowrap}}
.rsb{{position:absolute;left:60px;top:{top+OUTER_H+GAP_ROW}px;line-height:{SUB_H}px;font-weight:700;font-size:58px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
    body = (f'<div class="trow"><div class="rw">{ring}<div class="cname" data-k="co">{company}</div></div><div class="sw5">{sp}</div></div>'
            f'<div class="rsb" data-k="sub">{T.SUB}</div>')
    pic = f'<div class="pic" data-k="photo" style="box-shadow:none;background-image:url({photo});background-position:50% 50%"></div>'
    sw = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    base_hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    html = f'<div class="cv">{base_hd}{pic}{body}{sw}</div>'
    allow = {("ring", "co")} if style != 2 and style != 3 else {("ring", "co")}
    allow |= {("pill", "shuo")}
    return html, css, allow


def main(g):
    style = int(os.environ["TITLE_R"]); company = os.environ.get("TC_COMPANY", "廣達")
    name = os.environ.get("TC_OUTNAME", f"title_r{style}")
    OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    html, css, allow = build(style, g, company)
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{T.font_css()}</style><style>{g["CSS"]}{g["COVER_CSS"]}{g["SWIPE_CSS"]}'
           f"body{{font-family:'TCS','Noto Sans TC',sans-serif}}{css}</style></head><body>{html}</body></html>")
    f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(800)
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
        boxes = T.ink_boxes(pg, keys)
        ph = boxes["photo"]; sign = (ph[0] + 430, ph[1] + 310, ph[0] + 925, ph[1] + 480)
        bad, ok = [], []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, c = keys[i], keys[j]; A, C = boxes[a], boxes[c]
                if not A or not C: continue
                ox = min(A[2], C[2]) - max(A[0], C[0]); oy = min(A[3], C[3]) - max(A[1], C[1])
                if ox > 2 and oy > 2: (ok if ((a, c) in allow or (c, a) in allow) else bad).append((a, c, ox, oy))
        sign_hit = [k for k in keys if k != "photo" and boxes[k] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0 and min(boxes[k][3], sign[3]) - max(boxes[k][1], sign[1]) > 0]
        oob = [k for k in keys if boxes[k] and (boxes[k][0] < 0 or boxes[k][1] < 0 or boxes[k][2] > 1080 or boxes[k][3] > 1350)]
        right = max(boxes[k][2] for k in ("ring", "shuo", "pill") if k in boxes and boxes[k])
        res = {"style": style, "company": company, "boxes": boxes, "重疊": bad, "容器內(刻意)": ok, "壓到Quanta字": sign_hit, "出界": oob, "標題列最右": right,
               "與標籤垂直距": boxes["swipe"][1] - max(boxes[k][3] for k in ("ring", "sub"))}
        json.dump(res, open(OUT / f"overlap_{name}.json", "w"), ensure_ascii=False, indent=1)
        print(f"{name}（{company}）：重疊 {len(bad)} 出界 {len(oob)} 壓到Quanta {len(sign_hit)} 標題列最右 x={right}（上限 1020） 副標到標籤 {res['與標籤垂直距']}px", bad[:3])
        b.close()
    f.unlink()
