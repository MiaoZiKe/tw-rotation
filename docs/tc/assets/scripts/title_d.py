"""廣達封面標題第六輪（2026-11-06 Andy 選 c3-B＋旁白引號，並要求：「透明說」跟藍線一樣粗、試圓形、茶水間旁加茶杯）。
D1：橘膠囊高度＝線粗（線粗 60、膠囊 160×60、字 44）；D2＝橘正圓（直徑 1.8×線粗＝108）內「透明說」品字形；D3＝橘圓點（直徑＝線粗）、「透明說」放在圓點右側缺口外。
三款都有：缺口 -45°、兩端線頭與橘點等距（空隙 14）、副標旁白引號＋自繪茶杯（藍色圓頭線條＋橘色熱氣，取代原本的藍細直線）。
用法：TITLE_D=1 TC_VAR=D1|D2|D3 [TC_COMPANY=廣達] [TC_LAYOUT=one|two] TC_OUTNAME=title_d1 python render_quanta.py <ASSETS> <OUT>"""
import json, math, os, io
from pathlib import Path
import title_styles as T

SW = 60; CAP_R = SW / 2; D = 380
GAP = 14
SPEC = {"D6": dict(kind="pill", PW=int(os.environ.get("TC_PW", 166)), PH=int(os.environ.get("TC_PH", 64)), PF=int(os.environ.get("TC_PF", 46))), "D4": dict(kind="pill", PW=160, PH=0, PF=44), "D1": dict(kind="pill", PW=160, PH=60, PF=44), "D2": dict(kind="disc", PW=108, PH=108, PF=40), "D3": dict(kind="dot", PW=60, PH=60, PF=44)}


def logo_measure(path):
    import re
    t = Path(path).read_text(encoding="utf8")
    m = re.search(r'M([\d.]+) ([\d.]+) A([\d.]+) [\d.]+ 0 1 1 ([\d.]+) ([\d.]+)" fill="none" stroke="#1F6FEB" stroke-width="([\d.]+)"', t)
    x0, y0, r, x1, y1, sw = map(float, m.groups())
    d = re.search(r'circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)" fill="#FF9F1C"', t)
    dx, dy, dr = map(float, d.groups())
    ang = lambda x, y: math.atan2(y - 50, x - 50)
    return dict(r=r, sw=sw, pts=[(x1, y1), (x0, y0)], dot=(dx, dy), dr=dr, t_top=ang(x1, y1), t_r=ang(x0, y0))


LOGO_SVG = os.environ.get("TC_LOGO_SVG", "/tmp/claude-0/-home-user-tw-rotation/1662701f-8abb-57a6-b66d-4e0b4e90dd73/scratchpad/brand/icon_light.svg")
LM = logo_measure(LOGO_SVG)
LOGO_T = (LM["t_top"], LM["t_r"]); LOGO_PTS = LM["pts"]; LOGO_DOT = LM["dot"]


def is_cjk(s): return all(ord(c) > 0x2E80 for c in s)


def measure(pg, text, w=900):
    return pg.evaluate("""async a=>{const [t,w]=a;await document.fonts.load(w+" 100px TCS");await document.fonts.load(w+" 100px 'Noto Sans TC'");const c=document.createElement('canvas').getContext('2d');c.font=w+" 100px TCS, 'Noto Sans TC'";return c.measureText(t).width/100}""", [text, w])


def sdist(x, y, cx, cy, PW, PH):                 # 點到 stadium 外緣距離
    half = (PW - PH) / 2
    qx = min(max(x, cx - half), cx + half)
    return math.hypot(x - qx, y - cy) - PH / 2


def solve_ends(ac, cx, cy, PW, PH, gap):
    f = lambda t: sdist(ac * math.cos(t), ac * math.sin(t), cx, cy, PW, PH) - CAP_R
    c = math.radians(-45); tt = tr = c
    for k in range(2400):
        t = c - math.radians(k * 0.05)
        if f(t) >= gap: tt = t; break
    for k in range(2400):
        t = c + math.radians(k * 0.05)
        if f(t) >= gap: tr = t; break
    return tt, tr


def rect_to_stadium(hw, hh, rcy, cx, cy, PW, PH):
    half = (PW - PH) / 2; best = 1e9
    for i in range(41):
        px = cx - half + (2 * half) * i / 40 if half > 0 else cx; py = cy
        dx = max(abs(px) - hw, 0); dy = max(abs(py - rcy) - hh, 0)
        best = min(best, math.hypot(dx, dy) - PH / 2)
    return best


def fit(company, layout, widths, ob, Rr):
    lines = [company] if layout == "one" else (company.split("|") if "|" in company else ([company[:len(company)//2], company[len(company)//2:]] if len(company) == 4 else [company]))
    cjk = is_cjk(company)
    hwf = lambda f: max(widths[l] for l in lines) * f / 2
    hhf = lambda f: (len(lines) * f if cjk else len(lines) * 0.74 * f + (len(lines) - 1) * 0.3 * f) / 2
    cap = Rr - SW
    for f in range(108, 40, -1):
        hw, hh = hwf(f), hhf(f)
        for dy in range(0, 15):
            if math.hypot(hw, hh + dy) * 1.1 <= cap and rect_to_stadium(hw, hh, dy, *ob) >= 22: return lines, f, dy
    return lines, 40, 0


MIC = ('<svg data-k="cup" width="{w}" height="{h}" viewBox="0 0 64 64" style="position:absolute;left:{l:.1f}px;top:{t:.1f}px">'
       '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
       '<rect x="24" y="8" width="16" height="28" rx="8" stroke="{b}" stroke-width="5"/>'
       '<path d="M15 30 C15 46 49 46 49 30" stroke="{b}" stroke-width="5"/><path d="M32 45 V55" stroke="{b}" stroke-width="5"/><path d="M22 57 H42" stroke="{b}" stroke-width="5"/>'
       '<path d="M53 20 C57 25 57 31 53 36" stroke="{o}" stroke-width="4.5"/><path d="M59 15 C65 23 65 33 59 41" stroke="{o}" stroke-width="4.5"/></g></svg>')
BUBBLE = ('<svg data-k="cup" width="{w}" height="{h}" viewBox="0 0 64 64" style="position:absolute;left:{l:.1f}px;top:{t:.1f}px">'
          '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
          '<path d="M14 10 H50 C55 10 58 13 58 18 V36 C58 41 55 44 50 44 H34 L22 55 V44 H14 C9 44 6 41 6 36 V18 C6 13 9 10 14 10 Z" stroke="{b}" stroke-width="5"/>'
          '</g><circle cx="20" cy="27" r="3.6" fill="{o}"/><circle cx="32" cy="27" r="3.6" fill="{o}"/><circle cx="44" cy="27" r="3.6" fill="{o}"/></svg>')
CUP = ('<svg data-k="cup" width="{w}" height="{h}" viewBox="0 0 64 64" style="position:absolute;left:{l:.1f}px;top:{t:.1f}px">'
       '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
       '<path d="M12 28 H44 V36 C44 46 37 53 28 53 C19 53 12 46 12 36 Z" stroke="{b}" stroke-width="5"/>'
       '<path d="M44 31 H48 C55 31 55 43 47 43 H43.5" stroke="{b}" stroke-width="5"/>'
       '<path d="M10 59 H46" stroke="{b}" stroke-width="5"/>'
       '<path d="M22 9 C17 14 27 17 22 22" stroke="{o}" stroke-width="4.5"/><path d="M33 9 C28 14 38 17 33 22" stroke="{o}" stroke-width="4.5"/></g></svg>')


def build(g, company, layout, widths, var, dxy=(0, 0), cup_x=None, OVERLAY=False, subx=None):
    V = SPEC[var]; PW, PH, PF = V["PW"], V["PH"] or SW, V["PF"]
    INK, BLUE, ORG = (g[k] for k in ("INK", "BLUE", "ORG"))
    R = D / 2; ac = R - SW / 2; cx = cy = R + 6; W_ = H_ = D + 12
    if var in ("D4", "D6"):                            # 缺口角度＝LOGO 實測（-81°／-9°），徽章中心沿環微調到兩端等距
        PH = SW if var == "D4" else PH; t_top, t_r = LOGO_T[0], LOGO_T[1]
        gp = lambda dd: [sdist(ac * math.cos(a), ac * math.sin(a), ac * math.cos(math.radians(-45 + dd)), ac * math.sin(math.radians(-45 + dd)), PW, PH) - CAP_R for a in (t_top, t_r)]
        dbest = min(range(-150, 151), key=lambda i: abs(gp(i / 10)[0] - gp(i / 10)[1])) / 10
        pxr, pyr = ac * math.cos(math.radians(-45 + dbest)), ac * math.sin(math.radians(-45 + dbest))
    else:
        dbest = 0.0
        pxr, pyr = ac * math.cos(math.radians(-45)), ac * math.sin(math.radians(-45))
        t_top, t_r = solve_ends(ac, pxr, pyr, PW, PH, GAP)
    p_t = (cx + ac * math.cos(t_top), cy + ac * math.sin(t_top)); p_r = (cx + ac * math.cos(t_r), cy + ac * math.sin(t_r))
    path = f'<path d="M {p_r[0]:.2f} {p_r[1]:.2f} A {ac:.2f} {ac:.2f} 0 1 1 {p_t[0]:.2f} {p_t[1]:.2f}" fill="none" stroke="{BLUE}" stroke-width="{SW}" stroke-linecap="round"/>'
    ring = f'<svg data-k="ring" width="{W_}" height="{H_}" viewBox="0 0 {W_} {H_}" style="position:absolute;left:0;top:0">{path}</svg>'
    lines, f, dy = fit(company, layout, widths, (pxr, pyr, PW, PH), R)
    PB = g["PIC_TOP"] + g["PIC_H"]
    pill_top_rel = cy + pyr - PH / 2
    top_rel = min(6, pill_top_rel)
    grp_h = (cy + R) - top_rel
    y_top = max(PB + 34, PB + ((1290 - PB) - grp_h) / 2)
    oy = y_top - top_rel; ox = 54
    ccx, ccy = ox + cx, oy + cy
    n = len(lines)
    co = "".join(f'<div class="ecl">{l}</div>' for l in lines)
    pl = cx + pxr - PW / 2; pt_ = cy + pyr - PH / 2
    css = f"""
.ecw{{position:absolute;left:{ox}px;top:{oy:.1f}px;width:{W_}px;height:{H_}px}}
.ecc{{position:absolute;left:{dxy[0]:.1f}px;top:{cy-n*f/2+dy+dxy[1]:.1f}px;width:{W_}px;text-align:center;font-weight:900;font-size:{f}px;line-height:{f}px;color:{INK};white-space:nowrap}}
.ecp{{position:absolute;left:{pl:.1f}px;top:{pt_:.1f}px;width:{PW}px;height:{PH}px;border-radius:{PH/2}px;background:{ORG}}}
.ect{{position:absolute;left:{pl:.1f}px;top:{pt_:.1f}px;width:{PW}px;height:{PH}px;line-height:{PH}px;text-align:center;font-weight:900;font-size:{PF}px;color:{INK};white-space:nowrap}}
"""
    shuo = ""
    if V["kind"] == "pill":
        shuo = f'<div class="ect" data-k="shuo">{g.get("TD_PILL", "透明說")}</div>'
    elif V["kind"] == "disc":   # 品字形：透（上）、明 說（下）
        cxp, cyp = pl + PW / 2, pt_ + PH / 2
        pos = [("透", cxp, cyp - 21), ("明", cxp - 21, cyp + 20), ("說", cxp + 21, cyp + 20)]
        shuo = '<div data-k="shuo">' + "".join(f'<div style="position:absolute;left:{x-PF/2:.1f}px;top:{y-PF/2:.1f}px;width:{PF}px;height:{PF}px;line-height:{PF}px;text-align:center;font-weight:900;font-size:{PF}px;color:{INK}">{c}</div>' for c, x, y in pos) + '</div>'
    else:                       # 圓點旁：「透明說」放在圓點右側、缺口外側
        shuo = f'<div style="position:absolute;left:{pl+PW+16:.1f}px;top:{pt_+PH/2-26:.1f}px;line-height:52px;font-weight:900;font-size:{PF}px;color:{INK};white-space:nowrap" data-k="shuo">透明說</div>'
    circ_right = ccx + R
    if var == "D6" and g.get("TD_SUB_LINES"):   # 主題文：旁白可以多行、圖示可換（cup／mic）；字級由程式找「放得進右側」的最大值（上限 58）
        lines_s = g["TD_SUB_LINES"]; LG = 18; nL = len(lines_s)
        sw_ = g.get("TD_SUBW") or {}
        em = [sw_.get(l, len(l)) + (0.25 if g.get('TD_EMPH') else 0) for l in lines_s]
        if not g.get('TD_NOQUOTE'): em[0] += 0.7; em[-1] += 0.7         # 實測字寬（沒有就當全形）；前後小引號各約 0.7em
        text_l = circ_right + 2 * LG
        SUBF = min(g.get('TD_SUBCAP', 58), int((1034 - text_l - 20) / (max(em) + 0.84)))                    # 0.84em＝圖示可見寬（1.1×0.76）
        text_l = max(text_l, 1034 - max(max(em) * SUBF, em[-1] * SUBF + 20 + 0.84 * SUBF))   # 整組（文字＋圖示）靠右，圖示右緣離畫布右邊約 46px（Andy：旁白太靠左）
        LH = round(SUBF * 1.3); blk = nL * LH
        _ex, _eh = (g['TD_EXTRA_FN'](text_l, SUBF) if g.get('TD_EXTRA_FN') else ('', 0)); _tot = blk + (22 + _eh if _eh else 0); top0 = ccy - _tot / 2
        pill_bot = oy + pt_ + PH; pill_right = ox + pl + PW
        if text_l - LG < pill_right + 10 and top0 < pill_bot + 12: top0 = pill_bot + 12     # 多行旁白會頂到右上的膠囊時，整塊往下讓開
        _emph = g.get("TD_EMPH") or []
        def _em_(l):
            for e in _emph:
                if e in l: return l.replace(e, f"<b style='color:{BLUE};font-weight:900'>{e}</b>")
            return l
        _q0, _q1 = ("", "") if g.get("TD_NOQUOTE") else ("<span class=q>「</span>", "<span class=q>」</span>")
        htm = "".join(f"<div>{_q0 if i == 0 else ''}{_em_(l)}{_q1 if i == nL - 1 else ''}</div>" for i, l in enumerate(lines_s))
        sub = f'<div class="s4" data-k="sub"><i></i>{htm}</div>' + (f'<div data-k="extra" style="position:absolute;left:{text_l:.1f}px;top:{top0 + blk + 22:.1f}px">{_ex}</div>' if _ex else '')
        css += (f".s4{{position:absolute;left:{text_l:.1f}px;top:{top0:.1f}px;line-height:{LH}px;font-size:{SUBF}px;font-weight:{800 if g.get('TD_EMPH') else 700};letter-spacing:0;color:{INK};white-space:nowrap}}"
                f".s4 i{{position:absolute;left:-{LG}px;top:6px;width:5px;height:{blk-12:.1f}px;border-radius:3px;background:{BLUE}}}.s4 .q{{color:{ORG};font-weight:900;font-size:0.7em}}")
        cup_h = round(SUBF * 1.1)
        cup_l = text_l + em[-1] * SUBF + 20 - 0.172 * cup_h
        cup = ({"mic": MIC, "bubble": BUBBLE}.get(g.get("TD_ICON"), CUP)).format(w=cup_h, h=cup_h, l=cup_l, t=top0 + (nL - 0.5) * LH - 0.5 * cup_h + 2, b=BLUE, o=ORG)
        sub_font = SUBF
    elif var == "D6":   # 一行旁白：藍細直線＋橘色小「」＋文字＋茶杯，整組靠右，茶杯右緣離畫布右邊 48px
        LG = int(os.environ.get('TC_LG', 24)); SUBF = int((1040 - (circ_right + LG + LG) - 20) / 10.157)   # 10.157f＝字 8f＋引號 2×0.7f＋茶杯可見寬 0.757f
        LH = 80
        sub_l = circ_right + 2 * LG
        sub = (f'<div class="s4" data-k="sub"><i></i><span class="q">「</span>{T.SUB}<span class="q">」</span></div>')
        css += (f".s4{{position:absolute;left:{sub_l:.1f}px;top:{ccy-40:.1f}px;line-height:{LH}px;font-size:{SUBF}px;font-weight:700;letter-spacing:0;color:{INK};white-space:nowrap}}"
                f".s4 i{{position:absolute;left:-{LG}px;top:{(LH-SUBF*1.7)/2:.1f}px;width:5px;height:{SUBF*1.7:.1f}px;border-radius:3px;background:{BLUE}}}.s4 .q{{color:{ORG};font-weight:900;font-size:0.7em}}")
        cup = ""; cup_h = round(SUBF * 1.1); info_sf = SUBF
        cup_l = sub_l + 8 * SUBF + 1.4 * SUBF + 20 - 0.172 * cup_h
        cup = CUP.format(w=cup_h, h=cup_h, l=cup_l, t=ccy - 0.5 * cup_h + 2, b=BLUE, o=ORG)
        sub_font = SUBF
    elif var == "D4":   # 藍細直線＋旁白引號（兩行 62px：「茶水間／常聊的那些」）＋茶杯在右引號右邊，整組靠右
        sub_l = subx if subx is not None else circ_right + 90; SUBF = 62; LH = 72
        sub = (f'<div class="s4" data-k="sub"><i></i><div><span class="q">「</span>茶水間</div><div>常聊的那些<span class="q">」</span></div></div>')
        css += (f".s4{{position:absolute;left:{sub_l:.1f}px;top:{ccy-LH:.1f}px;line-height:{LH}px;font-size:{SUBF}px;font-weight:700;letter-spacing:.01em;color:{INK};white-space:nowrap}}"
                f".s4 i{{position:absolute;left:-28px;top:6px;width:6px;height:{2*LH-12}px;border-radius:3px;background:{BLUE}}}.s4 .q{{color:{ORG};font-weight:900}}")
        cup = ""
    else:
        cup_h = 66; cup_l = circ_right + 22
        cup = CUP.format(w=cup_h, h=cup_h, l=cup_l, t=ccy - cup_h / 2, b=BLUE, o=ORG)
        sub_l = cup_l + cup_h + 2
        sub = f'<div class="s4" data-k="sub"><span class="q">「</span>{T.SUB}<span class="q">」</span></div>'
        css += f".s4{{position:absolute;left:{sub_l:.1f}px;top:{ccy-40:.1f}px;line-height:80px;font-size:46px;font-weight:700;letter-spacing:.01em;color:{INK};white-space:nowrap}}.s4 .q{{color:{ORG};font-weight:900}}"
    if var == "D4" and cup_x is not None:
        cup_h = 72
        cup = CUP.format(w=cup_h, h=cup_h, l=cup_x, t=ccy + LH / 2 - 38, b=BLUE, o=ORG)   # 茶杯圖形視覺中心對齊第二行
    body = f'<div class="ecw">{ring}<div class="ecc" data-k="co">{co}</div><div class="ecp" data-k="pill"></div>{shuo}</div>' + cup + sub
    info_extra = dict(sub_font=SUBF if var == "D6" else None)
    if OVERLAY:       # 疊圖驗證：LOGO 環（洋紅，半透明）依同外徑縮放疊在圓上
        kk = R / 29.5; Lc = lambda x, y: (ccx + kk * (x - 50), ccy + kk * (y - 50))
        (a0, b0), (a1, b1) = Lc(*LOGO_PTS[0]), Lc(*LOGO_PTS[1]); dcx, dcy = Lc(*LOGO_DOT)
        body += (f'<svg style="position:absolute;left:0;top:0" width="1080" height="1350"><path d="M {a0:.2f} {b0:.2f} A {25*kk:.2f} {25*kk:.2f} 0 1 1 {a1:.2f} {b1:.2f}" fill="none" stroke="#E5004C" stroke-opacity=".5" stroke-width="{9*kk:.2f}" stroke-linecap="round"/>'
                 f'<circle cx="{dcx:.2f}" cy="{dcy:.2f}" r="{6.6*kk:.2f}" fill="#00A0FF" fill-opacity=".5"/></svg>')
    photo = None if g.get("TD_PIC_HTML") else g["TD_PHOTO"]() if g.get("TD_PHOTO") else g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    pic = g["TD_PIC_HTML"] if g.get("TD_PIC_HTML") else f'<div class="pic" data-k="photo" style="box-shadow:none;height:{g["PIC_H"]}px;background-image:url({photo});background-position:{g.get("TD_POS", "50% 50%")}"></div>'
    sw_ = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    info = dict(font=f, lines=lines, dy=dy, center=(ccx, ccy), R=R, gap_top=sdist(ac * math.cos(t_top), ac * math.sin(t_top), pxr, pyr, PW, PH) - CAP_R,
                gap_right=sdist(ac * math.cos(t_r), ac * math.sin(t_r), pxr, pyr, PW, PH) - CAP_R, gap_deg=math.degrees(t_r - t_top), pf=PF, bottom=oy + cy + R, pill_w=PW, pill_h=PH, offset_deg=dbest, sub_font=SUBF if var == 'D6' else None, cup_right=(cup_l + 0.86 * cup_h) if var == 'D6' else None)
    return f'<div class="cv">{hd}{pic}{body}{sw_}</div>', css, info


def main(g):
    from PIL import Image, ImageFilter, ImageChops
    company = os.environ.get("TC_COMPANY", "廣達"); layout = os.environ.get("TC_LAYOUT") or ("two" if (len(os.environ.get("TC_COMPANY", "廣達")) == 4 and is_cjk(os.environ.get("TC_COMPANY", "廣達"))) else "one"); name = os.environ["TC_OUTNAME"]; var = os.environ.get("TC_VAR", "D1")
    OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    global SW, CAP_R
    overlay = bool(os.environ.get("TC_OVERLAY"))
    if var == "D6":
        SW = int(os.environ.get("TC_SW", 44)); CAP_R = SW / 2
    if var == "D4":
        SW = round(LM["sw"] * 190 / (LM["r"] + LM["sw"] / 2)); CAP_R = SW / 2   # 57.97 取整數 58，膠囊高度＝線粗＝58px 完全相同      # LOGO：線粗 9、環中線半徑 25 → 外半徑 29.5；套到外徑 380
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        def render(dxy, cup_x=None, subx=None):
            html, css, info = build(g, company, layout, widths, var, dxy, cup_x, overlay, subx)
            doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{T.font_css()}</style><style>{g["CSS"]}{g["COVER_CSS"]}{g["SWIPE_CSS"]}'
                   f"body{{font-family:'TCS','Noto Sans TC',sans-serif}}{css}</style></head><body>{html}</body></html>")
            f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
            pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(700); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(250)
            f.unlink(); return info
        mf = OUT / f"_m_{name}.html"; mf.write_text("<meta charset='utf-8'><style>" + T.font_css() + "</style><span style='font-family:TCS;font-weight:900'>測ASML</span>", encoding="utf8")
        pg.goto(f"file://{mf}", wait_until="networkidle"); mf.unlink()
        lines_ = [company] if layout == "one" else (company.split("|") if "|" in company else [company[:2], company[2:]])
        widths = {l: (len(l) if is_cjk(l) else measure(pg, l)) for l in set(lines_ + [company])}
        if g.get("TD_SUB_LINES"): g["TD_SUBW"] = {l: measure(pg, l, 700) for l in g["TD_SUB_LINES"]}
        info = render((0, 0))
        keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
        bx = T.ink_boxes(pg, keys)
        co = bx["co"]; ccx, ccy = info["center"]; ccy += info["dy"]
        dxy2 = ((ccx - (co[0] + co[2]) / 2), (ccy - (co[1] + co[3]) / 2))
        info = render(dxy2)
        cup_x = None
        if var == "D4x":
            sb = T.ink_boxes(pg, ["sub"])["sub"]
            cup_x = sb[2] + 20 - 11                   # 右引號墨跡右緣 +20px（茶杯圖形在 72 格內左緣約 11px）
            vis_right = cup_x + 55 / 64 * 72          # 茶杯視覺右緣
            shift = 1035 - vis_right                  # 整組右移，讓茶杯右緣離畫布右邊 45px
            info = render(dxy2, cup_x + shift, subx=info["center"][0] + info["R"] + 90 + shift)
            keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
        shot = pg.screenshot(path=str(OUT / f"{name}.png"))
        if overlay:
            im = Image.open(OUT / f"{name}.png").crop((30, 810, 490, 1270)); im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS); im.save(OUT / f"{name}.png")
        boxes = T.ink_boxes(pg, keys)
        def mask(k):
            pg.evaluate("""k=>{let s=document.getElementById('iso');if(!s){s=document.createElement('style');s.id='iso';document.head.appendChild(s)}
              s.textContent=%r+'[data-k="'+k+'"],[data-k="'+k+'"] *{visibility:visible !important}'}""" % T.ISO, k)
            return Image.open(io.BytesIO(pg.screenshot())).convert("RGB").split()[1].point(lambda v: 255 if v > 12 else 0)
        M = {k: mask(k) for k in ("ring", "pill", "shuo", "sub", "cup", "co") + (("extra",) if "extra" in keys else ())}
        pg.evaluate("document.getElementById('iso').remove()")
        def pdist(a, c):
            ba, bc = M[a].getbbox(), M[c].getbbox()
            if not ba or not bc: return 40
            box = (max(0, min(ba[0], bc[0]) - 45), max(0, min(ba[1], bc[1]) - 45), min(1080, max(ba[2], bc[2]) + 45), min(1350, max(ba[3], bc[3]) + 45))
            A_, C_ = M[a].crop(box), M[c].crop(box)
            for N in range(1, 41):
                if ImageChops.multiply(A_.filter(ImageFilter.MaxFilter(2 * N + 1)), C_).getbbox(): return N - 1
            return 40
        pd = {f"{a}-{c}": pdist(a, c) for a, c in (("ring", "pill"), ("ring", "shuo"), ("ring", "sub"), ("ring", "cup"), ("pill", "co"), ("shuo", "co"), ("shuo", "sub"), ("cup", "sub"), ("pill", "sub")) + ((("ring", "extra"), ("pill", "extra"), ("extra", "sub"), ("cup", "extra"), ("extra", "co")) if "extra" in keys else ())}
        ph = boxes["photo"]; sign = (ph[0] + 430, ph[1] + 310, ph[0] + 925, ph[1] + 480)
        bad = [(k, v) for k, v in pd.items() if v <= 0 and k not in ("ring-pill",)]
        if pd["ring-pill"] <= 0 and var != "D0": bad.append(("ring-pill", 0))
        sign_hit = [k for k in keys if k != "photo" and boxes[k] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0 and min(boxes[k][3], sign[3]) - max(boxes[k][1], sign[1]) > 0]
        oob = [k for k in keys if boxes[k] and (boxes[k][0] < 0 or boxes[k][1] < 0 or boxes[k][2] > 1080 or boxes[k][3] > 1350)]
        swp = boxes["swipe"]
        for k in ("ring", "pill", "shuo", "sub", "cup", "extra"):
            if boxes.get(k) and min(boxes[k][2], swp[2]) - max(boxes[k][0], swp[0]) > 0 and min(boxes[k][3], swp[3]) - max(boxes[k][1], swp[1]) > 0: bad.append((k, "swipe"))
        right = max(boxes[k][2] for k in ("sub", "shuo", "ring") if boxes[k])
        # 像素實測：環線粗＝環在 9 點鐘列（圓心高度）的水平厚度；膠囊高＝橘膠囊墨跡高
        row = int(info["center"][1]); xs = [x for x in range(1080) if M["ring"].getpixel((x, row))]
        runs = []; st = None
        for x in range(1081):
            on = x < 1080 and M["ring"].getpixel((x, row))
            if on and st is None: st = x
            if not on and st is not None: runs.append(x - st); st = None
        ring_w_px = runs[0] if runs else None; pill_h_px = boxes["pill"][3] - boxes["pill"][1]
        res = dict(線粗實測px=ring_w_px, 膠囊高實測px=pill_h_px, name=name, var=var, company=company, layout=layout, font=info["font"], 徽章字級=info["pf"], 右側字級=info.get("sub_font"), 茶杯右緣=info.get("cup_right"), 線粗=SW, 重疊=bad, 壓到Quanta=sign_hit, 出界=oob, 像素距離=pd,
                   膠囊到照片=boxes["pill"][1] - ph[3], 圓頭到徽章_上端=info["gap_top"], 圓頭到徽章_右端=info["gap_right"], 缺口角度=info["gap_deg"], 最右=right,
                   徽章框=boxes["pill"], 字框=boxes["shuo"], 圈底=info["bottom"], boxes=boxes)
        json.dump(res, open(OUT / f"overlap_{name}.json", "w"), ensure_ascii=False, indent=1, default=str)
        print(f"線粗{ring_w_px} 膠囊高{pill_h_px} "+f"{name}[{var}]（{company}/{layout}）字級{info['font']} 徽章字{info['pf']}：重疊{len(bad)} 出界{len(oob)} 壓Quanta{len(sign_hit)} 膠囊到照片{res['膠囊到照片']} 上端空隙{info['gap_top']:.1f} 右端空隙{info['gap_right']:.1f} 缺口{info['gap_deg']:.0f}度 最右{right} 像素距{pd}", bad[:3])
        b.close()
