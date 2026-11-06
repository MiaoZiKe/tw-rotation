"""廣達封面標題第三輪（2026-11-06 Andy 手繪草圖：「先試試看橢圓，還有圓形的」）：整個標題＝放大版 LOGO。
藍色粗環裡放公司名；「透明說」縮成小橘膠囊（橘底深字）坐在環的右上缺口，取代 LOGO 橘點。版面其餘沿用原版（照片、頂列、副標、右下「右滑看透明圈」不動）。
用法：TITLE_EC=e|c [TC_CLOSED=1] [TC_COMPANY=廣達] TC_OUTNAME=title_e1 python render_quanta.py <ASSETS> <OUT>
e＝橢圓（外高 300、線粗 39＝0.13；寬依公司名字數自動加寬）；c＝正圓（外徑最大 380、線粗＝0.12×外徑；字多時縮字級，四字改 2×2 排）。
缺口：-45°（參數角）±27°＝54°（LOGO 為 72°；膠囊 224px 寬要蓋住兩端線頭，所以收窄）；TC_CLOSED=1 為封閉環。不用描邊加填色、漸層、發光、陰影。"""
import io, json, math, os
from pathlib import Path
from PIL import Image
import title_styles as T

PF = 56                       # 「透明說」字級（1080 畫布；389px 寬時 ≈ 20px）
PILL_W, PILL_H = 3 * PF + 56, 82


def shape(kind, company):
    n = len(company)
    if kind == "e":
        B, sw, f, lines = 150, 44, 108, [company]
        A = (n * f + 210) / 2                      # 圈外寬＝字寬＋210（2 字 426、3 字 534、4 字 642）
    else:
        D = 380; lines = [company]
        f = 108
        def need(f, lines):
            hw = max(len(l) for l in lines) * f / 2; hh = len(lines) * f / 2
            return math.hypot(hw, hh) * 1.1
        if n == 4: lines = [company[:2], company[2:]]
        sw = 50 if n == 2 else 45                    # 二字線粗 50；三四字內徑太緊，維持 45
        cap = 190 - sw                               # D=380 時的內半徑上限
        while need(f, lines) > cap and f > 60: f -= 1
        if n == 4: f = min(f, 90)                    # 四字 2×2：字級 90，字往下移 10px，讓膠囊下緣到字頂 ≥24px
        D = max(300, min(380, 2 * (need(f, lines) + sw)))
        A = B = D / 2
    return dict(A=A, B=B, sw=sw, f=f, lines=lines)


def build(kind, g, company, closed):
    BG, INK, BLUE, ORG = (g[k] for k in ("BG", "INK", "BLUE", "ORG"))
    sh = shape(kind, company); A, B, sw, f, lines = sh["A"], sh["B"], sh["sw"], sh["f"], sh["lines"]
    ac, bc = A - sw / 2, B - sw / 2                  # 中心線半軸
    X0, Y0 = 60, 0                                   # 外框左緣 x=60
    cx, cy = A + 6, B + 6                            # svg 內中心（預留 6px 邊）
    W_, H_ = 2 * A + 12, 2 * B + 12
    pt = lambda t: (cx + ac * math.cos(t), cy + bc * math.sin(t))
    px = cx + (A + 12) * math.cos(math.radians(-45)); py = cy + (B + 12) * math.sin(math.radians(-45))
    t1 = math.radians(-9)                                            # 右端點：LOGO 原值（3 點鐘上方 9°）
    xe = px - PILL_W / 2 + 30                                        # 上端圓頭 x＝膠囊左緣＋30，藏在膠囊下面
    t0 = -math.acos(max(-1, min(1, (xe - cx) / ac)))
    if closed:
        path = f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{ac:.1f}" ry="{bc:.1f}" fill="none" stroke="{BLUE}" stroke-width="{sw:.1f}"/>'
    else:
        (x0, y0), (x1, y1) = pt(t1), pt(t0)           # 從缺口下端（較接近右側）順時針繞一圈到缺口上端
        path = (f'<path d="M {x0:.2f} {y0:.2f} A {ac:.2f} {bc:.2f} 0 1 1 {x1:.2f} {y1:.2f}" fill="none" stroke="{BLUE}" stroke-width="{sw:.1f}" stroke-linecap="round"/>')
    ring = f'<svg data-k="ring" width="{W_:.1f}" height="{H_:.1f}" viewBox="0 0 {W_:.1f} {H_:.1f}" style="position:absolute;left:0;top:0">{path}</svg>'
    pill_top_rel = py - PILL_H / 2
    top_rel = min(0, pill_top_rel)                    # 群組最上緣（相對 svg 頂）
    PB = g["PIC_TOP"] + g["PIC_H"]
    SUB_H, GAP = 80, 18 if kind == "c" else 26
    block = (H_ - top_rel) + GAP + SUB_H
    y_top = PB + 34                                   # 膠囊頂／圈頂到照片下緣 34px
    oy = y_top - top_rel                              # svg 左上角在頁面的 y
    ox = X0 - 6
    sub_top = oy + H_ - 6 + GAP
    n = len(lines)
    co = "".join(f'<div class="ecl">{l}</div>' for l in lines)
    css = f"""
.ecw{{position:absolute;left:{ox:.1f}px;top:{oy:.1f}px;width:{W_:.1f}px;height:{H_:.1f}px}}
.ecc{{position:absolute;left:0;top:{cy-n*f/2-(-10 if (kind=="c" and len(lines)==2) else 0):.1f}px;width:{W_:.1f}px;text-align:center;font-weight:900;font-size:{f}px;line-height:{f}px;color:{INK};white-space:nowrap}}
.ecp{{position:absolute;left:{px-PILL_W/2:.1f}px;top:{pill_top_rel:.1f}px;width:{PILL_W}px;height:{PILL_H}px;border-radius:{PILL_H//2}px;background:{ORG}}}
.ect{{position:absolute;left:{px-PILL_W/2:.1f}px;top:{pill_top_rel:.1f}px;width:{PILL_W}px;height:{PILL_H}px;line-height:{PILL_H}px;text-align:center;font-weight:900;font-size:{PF}px;color:{INK};white-space:nowrap}}
.ecs{{position:absolute;left:60px;top:{sub_top:.1f}px;line-height:{SUB_H}px;font-weight:700;font-size:58px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
    body = (f'<div class="ecw">{ring}<div class="ecc" data-k="co">{co}</div><div class="ecp" data-k="pill"></div><div class="ect" data-k="shuo">透明說</div></div>'
            f'<div class="ecs" data-k="sub">{T.SUB}</div>')
    photo = g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    pic = f'<div class="pic" data-k="photo" style="box-shadow:none;background-image:url({photo});background-position:50% 50%"></div>'
    sw_ = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    allow = {("ring", "pill"), ("ring", "shuo"), ("ring", "co"), ("pill", "shuo")}
    # 距離實測（解析計算，頁面座標）：膠囊到照片、右端圓頭到膠囊（圓頭圓心到膠囊兩端圓心連線的距離－半徑）、上端圓頭到膠囊左緣
    pcx, pcy = ox + px, oy + py
    ex, ey = ox + pt(t1)[0], oy + pt(t1)[1]
    c0, c1 = pcx - PILL_W / 2 + PILL_H / 2, pcx + PILL_W / 2 - PILL_H / 2
    qx = min(max(ex, c0), c1); dist_end = math.hypot(ex - qx, ey - pcy) - PILL_H / 2 - sw / 2
    ux = ox + pt(t0)[0]
    info_d = dict(pill_to_photo=pcy - PILL_H / 2 - PB, ring_to_photo=oy + 6 - PB, end_to_pill=dist_end, upper_end_x_minus_pill_left=ux - (pcx - PILL_W / 2))
    info = dict(info_d, font=f, lines=lines, ring_w=2 * A, ring_h=2 * B, sw=sw, sw_ratio=sw / (2 * B), bottom=sub_top + SUB_H, ring_left=ox + 6)
    return f'<div class="cv">{hd}{pic}{body}{sw_}</div>', css, allow, info


def main(g):
    kind = os.environ["TITLE_EC"]; company = os.environ.get("TC_COMPANY", "廣達"); closed = bool(os.environ.get("TC_CLOSED"))
    name = os.environ["TC_OUTNAME"]; OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    html, css, allow, info = build(kind, g, company, closed)
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
                a, c = keys[i], keys[j]; A_, C_ = boxes[a], boxes[c]
                if not A_ or not C_: continue
                ox_ = min(A_[2], C_[2]) - max(A_[0], C_[0]); oy_ = min(A_[3], C_[3]) - max(A_[1], C_[1])
                if ox_ > 2 and oy_ > 2: (ok if ((a, c) in allow or (c, a) in allow) else bad).append((a, c, ox_, oy_))
        sign_hit = [k for k in keys if k != "photo" and boxes[k] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0 and min(boxes[k][3], sign[3]) - max(boxes[k][1], sign[1]) > 0]
        oob = [k for k in keys if boxes[k] and (boxes[k][0] < 0 or boxes[k][1] < 0 or boxes[k][2] > 1080 or boxes[k][3] > 1350)]
        right = max(boxes[k][2] for k in ("ring", "pill") if boxes[k])
        sw_box = boxes["swipe"]
        near_sw = [k for k in ("ring", "pill", "sub") if boxes[k] and min(boxes[k][2], sw_box[2]) - max(boxes[k][0], sw_box[0]) > -10 and min(boxes[k][3], sw_box[3]) - max(boxes[k][1], sw_box[1]) > -10]
        res = {"name": name, "company": company, "closed": closed, "boxes": boxes, "重疊": bad, "容器內(刻意)": ok, "壓到Quanta字": sign_hit, "出界": oob,
               "最右": right, "與photo最近距": boxes["ring"][1] - ph[3] if boxes["ring"][1] > ph[3] else "pill/ring 與照片重疊", "info": info, "靠近標籤(<10px)": near_sw,
               "co到pill最小間距": None}
        co, pl = boxes["co"], boxes["pill"]
        gx = max(co[0] - pl[2], pl[0] - co[2]); gy = max(co[1] - pl[3], pl[1] - co[3]); res["co到pill最小間距"] = max(gx, gy)
        json.dump(res, open(OUT / f"overlap_{name}.json", "w"), ensure_ascii=False, indent=1, default=str)
        print(f"{name}（{company}）：重疊 {len(bad)} 出界 {len(oob)} 壓到Quanta {len(sign_hit)} 最右 x={right} 字級 {info['font']} 線粗比 {info['sw_ratio']:.3f} 副標底 y={info['bottom']:.0f} 膠囊到照片 {info['pill_to_photo']:.0f} 圈到照片 {info['ring_to_photo']:.0f} 右端圓頭到膠囊 {info['end_to_pill']:.0f} 上端圓頭x-膠囊左緣 {info['upper_end_x_minus_pill_left']:.0f} 公司字到橘膠囊 {res['co到pill最小間距']}px 近標籤 {near_sw}", bad[:3])
        b.close()
    f.unlink()
