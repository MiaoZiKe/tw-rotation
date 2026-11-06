"""廣達封面標題第五輪（2026-11-06 Andy：「是擺在缺口中間，跟 LOGO 一樣」）：正圓藍環缺口在右上（-45° 為中心），橘膠囊「透明說」坐在缺口正中間，
膠囊中心落在環中線的 -45° 點，與兩端線頭各留一段看得見的空隙（左右相等），不蓋住線頭。副標在圓右側垂直置中，必要時為避開膠囊往右移。
用法：TITLE_C3=1 TC_VAR=A|B [TC_COMPANY=廣達] [TC_LAYOUT=one|two] TC_OUTNAME=title_c3A python render_quanta.py <ASSETS> <OUT>
 A＝缺口加大、橫向膠囊 224×82、字級 56、空隙 18；B＝膠囊縮小 170×64、字級 46（389px 寬下字高約 17px）、空隙 14，缺口較小較像 LOGO。
圓外徑固定 380、線粗 50。兩端線頭位置由程式解：各自往外找到「圓頭邊緣到膠囊的距離＝空隙」為止，所以左右空隙相等。"""
import json, math, os
from pathlib import Path
import title_styles as T

SW = 50; CAP_R = SW / 2; D = 380
VAR = {"A": dict(PF=56, PW=224, PH=82, GAP=18), "B": dict(PF=46, PW=170, PH=64, GAP=14)}


def is_cjk(s): return all(ord(c) > 0x2E80 for c in s)


def measure(pg, text):
    return pg.evaluate("""async t=>{await document.fonts.load("900 100px TCS");const c=document.createElement('canvas').getContext('2d');c.font="900 100px TCS";return c.measureText(t).width/100}""", text)


def pill_dist(x, y, cxp, cyp, PW, PH):            # 點到膠囊（stadium）邊緣的距離（點在外面為正）
    half = (PW - PH) / 2
    qx = min(max(x, cxp - half), cxp + half)
    return math.hypot(x - qx, y - cyp) - PH / 2


def solve_ends(ac, cxp, cyp, PW, PH, gap):
    """回傳 (上端角度, 右端角度)，單位弧度，y 向下座標（上方為負）。圓頭邊緣到膠囊的距離 = gap。"""
    f = lambda t: pill_dist(ac * math.cos(t), ac * math.sin(t), cxp, cyp, PW, PH) - CAP_R
    c = math.radians(-45)
    t_top = c
    for k in range(0, 2400):                        # 往 12 點鐘方向逆時針（角度減小）
        t = c - math.radians(k * 0.05)
        if f(t) >= gap: t_top = t; break
    t_r = c
    for k in range(0, 2400):                        # 往 3 點鐘方向順時針
        t = c + math.radians(k * 0.05)
        if f(t) >= gap: t_r = t; break
    return t_top, t_r


def fit(company, layout, widths, ac, pill_bottom_rel, Rr=190):
    lines = [company] if layout == "one" else ([company[:len(company)//2], company[len(company)//2:]] if len(company) == 4 else [company])
    cjk = is_cjk(company)
    hwf = lambda f: max(widths[l] for l in lines) * f / 2
    hhf = lambda f: (len(lines) * f if cjk else len(lines) * 0.74 * f + (len(lines) - 1) * 0.3 * f) / 2
    cap = Rr - SW
    f = 108; dy = 0
    while f > 40:
        hh = hhf(f)
        shift = max(0, hh + pill_bottom_rel + 24)           # 文字頂到膠囊底至少 24：不夠就整塊往下推（最多 14px）
        if math.hypot(hwf(f), hh + shift) * 1.1 <= cap and shift <= 14: dy = shift; break
        f -= 1
    return lines, f, dy


def build(g, company, layout, widths, var, dxy=(0, 0)):
    V = VAR[var]; PF, PW, PH, GAP = V["PF"], V["PW"], V["PH"], V["GAP"]
    INK, BLUE, ORG = (g[k] for k in ("INK", "BLUE", "ORG"))
    SUBV = int(os.environ.get('TC_SUB', 0)); Dd = float(os.environ.get('TC_D', D))
    R = Dd / 2; ac = R - SW / 2
    cx = cy = R + 6; W_ = H_ = Dd + 12
    pxr, pyr = ac * math.cos(math.radians(-45)), ac * math.sin(math.radians(-45))     # 膠囊中心（相對圓心）＝中線 -45° 點
    t_top, t_r = solve_ends(ac, pxr, pyr, PW, PH, GAP)
    p_t = (cx + ac * math.cos(t_top), cy + ac * math.sin(t_top)); p_r = (cx + ac * math.cos(t_r), cy + ac * math.sin(t_r))
    path = f'<path d="M {p_r[0]:.2f} {p_r[1]:.2f} A {ac:.2f} {ac:.2f} 0 1 1 {p_t[0]:.2f} {p_t[1]:.2f}" fill="none" stroke="{BLUE}" stroke-width="{SW}" stroke-linecap="round"/>'
    ring = f'<svg data-k="ring" width="{W_:.1f}" height="{H_:.1f}" viewBox="0 0 {W_:.1f} {H_:.1f}" style="position:absolute;left:0;top:0">{path}</svg>'
    lines, f, dy = fit(company, layout, widths, ac, pyr + PH / 2, R)
    PB = g["PIC_TOP"] + g["PIC_H"]
    pill_top_rel = cy + pyr - PH / 2
    top_rel = min(6, pill_top_rel)
    grp_h = (cy + R) - top_rel
    y_top = max(PB + 34, PB + ((1290 - PB) - grp_h) / 2)
    if SUBV == 5: y_top = PB + 34                      # 弧形字在圓下方，整組靠上
    if SUBV == 3: y_top = PB + 34
    oy = y_top - top_rel; ox = 60 - 6
    pill_right_page = ox + cx + pxr + PW / 2
    sub_left = max(60 + Dd + 50, pill_right_page + 40)
    sub_top = oy + cy - 40
    n = len(lines)
    co = "".join(f'<div class="ecl">{l}</div>' for l in lines)
    pl = cx + pxr - PW / 2
    css = f"""
.ecw{{position:absolute;left:{ox}px;top:{oy:.1f}px;width:{W_:.1f}px;height:{H_:.1f}px}}
.ecc{{position:absolute;left:{dxy[0]:.1f}px;top:{cy-n*f/2+dy+dxy[1]:.1f}px;width:{W_:.1f}px;text-align:center;font-weight:900;font-size:{f}px;line-height:{f}px;color:{INK};white-space:nowrap}}
.ecp{{position:absolute;left:{pl:.1f}px;top:{pill_top_rel:.1f}px;width:{PW}px;height:{PH}px;border-radius:{PH//2}px;background:{ORG}}}
.ect{{position:absolute;left:{pl:.1f}px;top:{pill_top_rel:.1f}px;width:{PW}px;height:{PH}px;line-height:{PH}px;text-align:center;font-weight:900;font-size:{PF}px;color:{INK};white-space:nowrap}}
.ecs{{position:absolute;left:{sub_left:.1f}px;top:{sub_top:.1f}px;line-height:80px;font-weight:700;font-size:56px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
    GREY = g["GREY"]
    ccx_p, ccy_p = ox + cx, oy + cy                      # 圓心（頁面座標）
    circ_right = ccx_p + R
    sub_css = ""; sub_html = f'<div class="ecs" data-k="sub">{T.SUB}</div>'
    if SUBV == 1:   # 右側兩行錯落：茶水間（大）／常聊的那些（小，縮排）
        L = circ_right + 62
        sub_html = '<div class="s1" data-k="sub"><div class="a">茶水間</div><div class="b">常聊的那些</div></div>'
        sub_css = f".s1{{position:absolute;left:{L:.1f}px;top:{ccy_p-70:.1f}px;color:{INK};white-space:nowrap}}.s1 .a{{font-size:68px;line-height:76px;font-weight:900;letter-spacing:.04em}}.s1 .b{{font-size:48px;line-height:64px;font-weight:700;margin-left:44px;letter-spacing:.04em}}"
    elif SUBV == 2:  # 直排
        L = circ_right + 46
        sub_html = f'<div class="s2" data-k="sub">{T.SUB}</div>'
        sub_css = f".s2{{position:absolute;left:{L:.1f}px;top:{ccy_p-222:.1f}px;writing-mode:vertical-rl;text-orientation:upright;font-size:54px;line-height:60px;font-weight:700;letter-spacing:.04em;color:{INK};white-space:nowrap}}"
    elif SUBV == 3:  # 圓正下方（靠圓左緣對齊，圓縮小到 330）
        sub_html = f'<div class="s3" data-k="sub">{T.SUB}</div>'
        sub_css = f".s3{{position:absolute;left:60px;top:{oy+cy+R+14:.1f}px;font-size:56px;line-height:80px;font-weight:700;letter-spacing:.04em;color:{INK};white-space:nowrap}}"
    elif SUBV == 4:  # 旁白感：橘色「」＋左側藍色細直線
        L = circ_right + 70
        sub_html = f'<div class="s4" data-k="sub"><i></i><span class="q">「</span>{T.SUB}<span class="q">」</span></div>'
        sub_css = (f".s4{{position:absolute;left:{L:.1f}px;top:{ccy_p-40:.1f}px;line-height:80px;font-size:52px;font-weight:700;letter-spacing:.02em;color:{INK};white-space:nowrap}}"
                   f".s4 i{{position:absolute;left:-26px;top:-10px;width:5px;height:100px;border-radius:3px;background:{BLUE}}}.s4 .q{{color:{ORG};font-weight:900}}")
    elif SUBV == 5:  # 沿圓環外側下半弧排字
        rb = R + 62; fs = 46
        a0, a1 = math.radians(90 + 52), math.radians(90 - 52)
        pts = lambda a: (rb * math.cos(a), rb * math.sin(a))
        (x0, y0), (x1, y1) = pts(a0), pts(a1)
        sub_html = (f'<svg class="s5" data-k="sub" width="{2*rb+40:.0f}" height="{rb+60:.0f}" viewBox="{-rb-20:.0f} {-20:.0f} {2*rb+40:.0f} {rb+60:.0f}" '
                    f'style="position:absolute;left:{ccx_p-rb-20:.1f}px;top:{ccy_p-20:.1f}px"><defs><path id="arc" d="M {x0:.2f} {y0:.2f} A {rb:.2f} {rb:.2f} 0 0 0 {x1:.2f} {y1:.2f}"/></defs>'
                    f'<text font-family="TCS" font-weight="700" font-size="{fs}" fill="{INK}" text-anchor="middle" letter-spacing="3"><textPath href="#arc" startOffset="50%">{T.SUB}</textPath></text></svg>')
    body = (f'<div class="ecw">{ring}<div class="ecc" data-k="co">{co}</div><div class="ecp" data-k="pill"></div><div class="ect" data-k="shuo">透明說</div></div>'
            + sub_html)
    css = css + sub_css
    photo = g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    pic = f'<div class="pic" data-k="photo" style="box-shadow:none;background-image:url({photo});background-position:50% 50%"></div>'
    sw_ = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    # 圓頭圓心到膠囊的邊緣距離（解析值，扣掉圓頭半徑）
    d_top = pill_dist(ac * math.cos(t_top), ac * math.sin(t_top), pxr, pyr, PW, PH) - CAP_R
    d_r = pill_dist(ac * math.cos(t_r), ac * math.sin(t_r), pxr, pyr, PW, PH) - CAP_R
    info = dict(font=f, lines=lines, dy=dy, center=(ox + cx, oy + cy + 0), R=R, gap_top=d_top, gap_right=d_r, gap_deg=math.degrees(t_r - t_top + 0) if False else math.degrees((t_top + 2 * math.pi) - t_r) if False else math.degrees(t_r - t_top),
                pill_to_photo=oy + pill_top_rel - PB, bottom=oy + cy + R, sub_left=sub_left, dy_shift=dy)
    return f'<div class="cv">{hd}{pic}{body}{sw_}</div>', css, info


def main(g):
    company = os.environ.get("TC_COMPANY", "廣達"); layout = os.environ.get("TC_LAYOUT", "one"); name = os.environ["TC_OUTNAME"]; var = os.environ.get("TC_VAR", "A")
    OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        def render(dxy):
            html, css, info = build(g, company, layout, widths, var, dxy)
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
        co = bx["co"]; ccx, ccy = info["center"]; ccy += info["dy"]
        dx, dy = ccx - (co[0] + co[2]) / 2, ccy - (co[1] + co[3]) / 2
        info = render((dx, dy))
        pg.screenshot(path=str(OUT / f"{name}.png"))
        boxes = T.ink_boxes(pg, keys)
        # 圓環與膠囊逐像素距離（像素實測）：環遮罩膨脹 N px 後與膠囊相交 → 距離 < N
        from PIL import Image, ImageFilter, ImageChops
        import io
        def mask(k):
            pg.evaluate("""k=>{let s=document.getElementById('iso');if(!s){s=document.createElement('style');s.id='iso';document.head.appendChild(s)}
              s.textContent=%r+'[data-k="'+k+'"],[data-k="'+k+'"] *{visibility:visible !important}'}""" % T.ISO, k)
            return Image.open(io.BytesIO(pg.screenshot())).convert("RGB").split()[1].point(lambda v: 255 if v > 12 else 0)
        mr, mp = mask("ring"), mask("pill")
        ms = mask("sub")
        pg.evaluate("document.getElementById('iso').remove()")
        sub_hit_ring = bool(ImageChops.multiply(mr, ms).getbbox()); sub_hit_pill = bool(ImageChops.multiply(mp, ms).getbbox())
        sub_ring_d = 40
        for N in range(1, 40):
            if ImageChops.multiply(mr.filter(ImageFilter.MaxFilter(2 * N + 1)), ms).getbbox(): sub_ring_d = N - 1; break
        pxdist = None
        for N in range(1, 40):
            if ImageChops.multiply(mr.filter(ImageFilter.MaxFilter(2 * N + 1)), mp).getbbox(): pxdist = N - 1; break
        pxdist = pxdist if pxdist is not None else 40
        allow = {("ring", "co")}
        ph = boxes["photo"]; sign = (ph[0] + 430, ph[1] + 310, ph[0] + 925, ph[1] + 480)
        bad, ok = [], []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, c = keys[i], keys[j]; A_, C_ = boxes[a], boxes[c]
                if not A_ or not C_: continue
                if (a, c) in {("pill", "shuo")} or (c, a) in {("pill", "shuo")}: continue
                ox_ = min(A_[2], C_[2]) - max(A_[0], C_[0]); oy_ = min(A_[3], C_[3]) - max(A_[1], C_[1])
                if ox_ > 2 and oy_ > 2: (ok if ((a, c) in allow or (c, a) in allow) else bad).append((a, c, ox_, oy_))
        # ring 與 pill 的外框相交是正常的（pill 在缺口裡），以逐像素距離為準：必須 > 0
        bad = [x for x in bad if not ({x[0], x[1]} == {"ring", "pill"} or {x[0], x[1]} == {"ring", "shuo"} or {x[0], x[1]} == {"ring", "sub"} or {x[0], x[1]} == {"pill", "sub"} or {x[0], x[1]} == {"shuo", "sub"})]
        if sub_hit_ring: bad.append(("ring", "sub", "pixel", 0))
        if sub_hit_pill: bad.append(("pill", "sub", "pixel", 0))
        if pxdist <= 0: bad.append(("ring", "pill", 0, 0))
        sign_hit = [k for k in keys if k != "photo" and boxes[k] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0 and min(boxes[k][3], sign[3]) - max(boxes[k][1], sign[1]) > 0]
        oob = [k for k in keys if boxes[k] and (boxes[k][0] < 0 or boxes[k][1] < 0 or boxes[k][2] > 1080 or boxes[k][3] > 1350)]
        co, pl_, sw_b, sb = boxes["co"], boxes["pill"], boxes["swipe"], boxes["sub"]
        co_pill_gap = max(co[0] - pl_[2], pl_[0] - co[2], co[1] - pl_[3], pl_[1] - co[3])
        corner = max(math.hypot(x - ccx, y - (ccy)) for x in (co[0], co[2]) for y in (co[1], co[3]))
        res = dict(name=name, var=var, company=company, layout=layout, font=info["font"], lines=info["lines"], 重疊=bad, 壓到Quanta=sign_hit, 出界=oob,
                   膠囊到照片=pl_[1] - ph[3], 膠囊到公司名=co_pill_gap, 公司名下推=info["dy"], 圓頭到膠囊_上端=info["gap_top"], 圓頭到膠囊_右端=info["gap_right"], 像素實測最近距=pxdist,
                   缺口角度=info["gap_deg"], 字到內圈餘裕=(info["R"] - SW) - corner, 副標左緣=sb[0], 副標最右=sb[2], 副標到膠囊=sb[0] - pl_[2], 副標到圓環像素距=sub_ring_d, 圈底=info["bottom"], boxes=boxes)
        json.dump(res, open(OUT / f"overlap_{name}.json", "w"), ensure_ascii=False, indent=1, default=str)
        print(f"{name}[{var}]（{company}/{layout}）字級{info['font']}：重疊{len(bad)} 出界{len(oob)} 壓Quanta{len(sign_hit)} 膠囊到照片{res['膠囊到照片']} 膠囊到公司名{co_pill_gap} 上端空隙{info['gap_top']:.1f} 右端空隙{info['gap_right']:.1f} 像素最近距{pxdist} 缺口{info['gap_deg']:.0f}度 副標左{sb[0]} 副標到圓環{sub_ring_d}px 副標到膠囊{res['副標到膠囊']} 圈底{info['bottom']:.0f}", bad[:3])
        b.close()
