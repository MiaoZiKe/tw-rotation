"""廣達封面標題第四輪（2026-11-06 Andy：「都用正圓，並且『透明說』應該要夾在中間，不是傾向一邊」）。
正圓藍環＋公司名置中；橘膠囊「透明說」在 12 點鐘正上方、水平置中，缺口以 12 點鐘為中心左右對稱，兩端圓頭各縮進膠囊左右緣 30px 藏在膠囊下。
用法：TITLE_C2=1 [TC_COMPANY=廣達] [TC_LAYOUT=one|two] TC_OUTNAME=title_c2 python render_quanta.py <ASSETS> <OUT>
 one＝公司名一行排；two＝兩字一行、共兩行（四字中文 2×2）。字級由程式找「放得進圓」的最大值（上限 108），英文量實際字寬。
線粗一律 50（全系列統一）、膠囊 224×82、字級 56。不用描邊加填色、漸層、發光、陰影。"""
import io, json, math, os
from pathlib import Path
from PIL import Image
import title_styles as T

PF, PILL_W, PILL_H, SW = 56, 224, 82, 50
INSET = 30                      # 圓頭中心縮進膠囊左右緣
CAP_R = SW / 2


def is_cjk(s): return all(ord(c) > 0x2E80 for c in s)


def measure(pg, text):          # 每 1px 字級的字寬（900 字重）
    return pg.evaluate("""async t=>{await document.fonts.load("900 100px TCS");const c=document.createElement('canvas').getContext('2d');c.font="900 100px TCS";return c.measureText(t).width/100}""", text)


def fit(company, layout, widths):
    lines = [company] if layout == "one" else ([company[:len(company)//2], company[len(company)//2:]] if len(company) == 4 else [company])
    cjk = is_cjk(company)
    def need(f):
        hw = max(widths[l] for l in lines) * f / 2
        hh = (len(lines) * f if cjk else len(lines) * 0.74 * f + (len(lines) - 1) * 0.3 * f) / 2   # 英文只算大寫字高
        return math.hypot(hw, hh) * 1.1
    cap = 190 - SW
    f = 108
    while need(f) > cap and f > 40: f -= 1
    D = max(300, min(380, 2 * (need(f) + SW)))
    return lines, f, D


def build(g, company, layout, widths, dxy=(0, 0)):
    BG, INK, BLUE, ORG = (g[k] for k in ("BG", "INK", "BLUE", "ORG"))
    lines, f, D = fit(company, layout, widths)
    R = D / 2; ac = R - SW / 2
    cx = cy = R + 6; W_ = H_ = D + 12
    hx = PILL_W / 2 - INSET                           # 圓頭中心離 12 點鐘軸 82px
    yc = -math.sqrt(ac ** 2 - hx ** 2)                # 圓頭中心 y（相對圓心）
    pill_cy = yc - 13                                 # 膠囊底 = 圓頭底 +3，確保圓頭藏住
    p_r = (cx + hx, cy + yc); p_l = (cx - hx, cy + yc)
    path = f'<path d="M {p_r[0]:.2f} {p_r[1]:.2f} A {ac:.2f} {ac:.2f} 0 1 1 {p_l[0]:.2f} {p_l[1]:.2f}" fill="none" stroke="{BLUE}" stroke-width="{SW}" stroke-linecap="round"/>'
    ring = f'<svg data-k="ring" width="{W_:.1f}" height="{H_:.1f}" viewBox="0 0 {W_:.1f} {H_:.1f}" style="position:absolute;left:0;top:0">{path}</svg>'
    PB = g["PIC_TOP"] + g["PIC_H"]
    pill_top_rel = cy + pill_cy - PILL_H / 2
    top_rel = min(6, pill_top_rel)
    grp_h = (cy + R) - top_rel                           # 膠囊頂（或圈頂）到圈底
    y_top = max(PB + 34, PB + ((1290 - PB) - grp_h) / 2)  # 在照片下緣與 y=1290 之間垂直置中，上方至少 34px
    oy = y_top - top_rel; ox = 60 - 6
    SUB_F = 56
    sub_left = 60 + D + 50                                # 圓右緣 + 50px，靠左對齊
    sub_top = oy + cy - 40                                # 與圓心（＝公司名中線）垂直置中
    n = len(lines); lh = f if is_cjk(company) else f
    co = "".join(f'<div class="ecl">{l}</div>' for l in lines)
    css = f"""
.ecw{{position:absolute;left:{ox}px;top:{oy:.1f}px;width:{W_:.1f}px;height:{H_:.1f}px}}
.ecc{{position:absolute;left:{dxy[0]:.1f}px;top:{cy-n*lh/2+dxy[1]:.1f}px;width:{W_:.1f}px;text-align:center;font-weight:900;font-size:{f}px;line-height:{lh}px;color:{INK};white-space:nowrap}}
.ecp{{position:absolute;left:{cx-PILL_W/2:.1f}px;top:{pill_top_rel:.1f}px;width:{PILL_W}px;height:{PILL_H}px;border-radius:{PILL_H//2}px;background:{ORG}}}
.ect{{position:absolute;left:{cx-PILL_W/2:.1f}px;top:{pill_top_rel:.1f}px;width:{PILL_W}px;height:{PILL_H}px;line-height:{PILL_H}px;text-align:center;font-weight:900;font-size:{PF}px;color:{INK};white-space:nowrap}}
.ecs{{position:absolute;left:{sub_left:.1f}px;top:{sub_top:.1f}px;line-height:80px;font-weight:700;font-size:{SUB_F}px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
    body = (f'<div class="ecw">{ring}<div class="ecc" data-k="co">{co}</div><div class="ecp" data-k="pill"></div><div class="ect" data-k="shuo">透明說</div></div>'
            f'<div class="ecs" data-k="sub">{T.SUB}</div>')
    photo = g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    pic = f'<div class="pic" data-k="photo" style="box-shadow:none;background-image:url({photo});background-position:50% 50%"></div>'
    sw_ = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    info = dict(font=f, lines=lines, D=D, bottom=oy + cy + R, center=(ox + cx, oy + cy), R=R,
                sub_left=sub_left, pill_to_photo=oy + pill_top_rel - PB, ring_to_photo=oy + 6 - PB, pill_bottom=oy + pill_cy + cy + PILL_H / 2,
                cap_in_left=INSET, cap_in_right=INSET, cap_tip_clear=PILL_W / 2 - hx - CAP_R, pill_axis_off=0.0)
    return f'<div class="cv">{hd}{pic}{body}{sw_}</div>', css, info


def main(g):
    company = os.environ.get("TC_COMPANY", "廣達"); layout = os.environ.get("TC_LAYOUT", "one"); name = os.environ["TC_OUTNAME"]
    OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        def render(dxy):
            html, css, info = build(g, company, layout, widths, dxy)
            doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{T.font_css()}</style><style>{g["CSS"]}{g["COVER_CSS"]}{g["SWIPE_CSS"]}'
                   f"body{{font-family:'TCS','Noto Sans TC',sans-serif}}{css}</style></head><body>{html}</body></html>")
            f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
            pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(700); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(250)
            f.unlink()
            return info
        mf = OUT / f"_m_{name}.html"; mf.write_text("<meta charset='utf-8'><style>" + T.font_css() + "</style><span style='font-family:TCS;font-weight:900'>測ASML</span>", encoding="utf8")
        pg.goto(f"file://{mf}", wait_until="networkidle"); mf.unlink()
        lines_ = [company] if layout == "one" else [company[:2], company[2:]]
        widths = {l: (len(l) if is_cjk(l) else measure(pg, l)) for l in set(lines_ + [company])}
        info = render((0, 0))
        keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
        bx = T.ink_boxes(pg, keys)
        co = bx["co"]; ccx, ccy = info["center"]
        dx, dy = ccx - (co[0] + co[2]) / 2, ccy - (co[1] + co[3]) / 2     # 把公司名墨跡中心推到圓心
        info = render((dx, dy)); info["pill_axis_off"] = 0.0
        pg.screenshot(path=str(OUT / f"{name}.png"))
        boxes = T.ink_boxes(pg, keys)
        allow = {("ring", "pill"), ("ring", "shuo"), ("ring", "co"), ("pill", "shuo")}
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
        co, pl, sw_b = boxes["co"], boxes["pill"], boxes["swipe"]
        co_center = ((co[0] + co[2]) / 2, (co[1] + co[3]) / 2)
        pill_cx = (pl[0] + pl[2]) / 2
        # 公司名到內圈餘裕：墨跡外框四角到圓心的最大距離 vs 內半徑
        corner = max(math.hypot(x - ccx, y - ccy) for x in (co[0], co[2]) for y in (co[1], co[3]))
        res = dict(name=name, company=company, layout=layout, font=info["font"], lines=info["lines"], D=info["D"], 重疊=bad, 容器內=ok, 壓到Quanta=sign_hit, 出界=oob,
                   膠囊到照片=pl[1] - ph[3], 圈到照片=boxes["ring"][1] - ph[3], 膠囊到公司名=co[1] - pl[3], 公司名中心偏差=(co_center[0] - ccx, co_center[1] - ccy),
                   膠囊水平置中偏差=pill_cx - ccx, 圓頭中心縮進_左右=(INSET, INSET), 圓頭外緣離膠囊邊=info["cap_tip_clear"], 字到內圈餘裕=(info["R"] - SW) - corner,
                   圈底=info["bottom"], 副標左緣到圓右緣=boxes["sub"][0] - boxes["ring"][2], 副標最右=boxes["sub"][2], 副標到標籤垂直=sw_b[1] - boxes["sub"][3], 圈底到標籤=sw_b[1] - boxes["ring"][3], boxes=boxes)
        json.dump(res, open(OUT / f"overlap_{name}.json", "w"), ensure_ascii=False, indent=1, default=str)
        print(f"{name}（{company}/{layout}）字級{info['font']} D={info['D']:.0f}：重疊{len(bad)} 出界{len(oob)} 壓Quanta{len(sign_hit)} 膠囊到照片{res['膠囊到照片']} 膠囊到公司名{res['膠囊到公司名']} 公司名中心偏差({res['公司名中心偏差'][0]:.1f},{res['公司名中心偏差'][1]:.1f}) 膠囊置中偏差{res['膠囊水平置中偏差']:.1f} 字到內圈餘裕{res['字到內圈餘裕']:.0f} 圈底{res['圈底']:.0f} 副標左到圓右{res['副標左緣到圓右緣']} 副標最右{res['副標最右']}", bad[:3])
        b.close()
