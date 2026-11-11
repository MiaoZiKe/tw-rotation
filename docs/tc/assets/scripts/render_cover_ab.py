"""年薪榜封面 A／B 兩版（2026-11-11）。用法：TC_COVER_PHOTO=<tsmc photo_20.jpg> TW_FONT_DIR=<fontsource css> python render_cover_ab.py <ASSETS> <輸出目錄>
標題兩行：「市值第一大的台積電」／「非主管年薪只排第 3」（無引號；「第 3」藍色粗體，不用特效）。
A＝沿用定案版型（藍圈＋透明說膠囊＋咖啡杯＋右滑鈕），標題盡量放大，標題下方放前三名小標籤；B＝照片裁短 550、標題橫跨整寬 70px、圓縮小 280、無咖啡杯、頂列 LOGO 與右滑鈕字放大 34px。"""
import os, re, sys, json, io, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
ASSETS_ARG, OUT = sys.argv[1], Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
sys.argv = [sys.argv[0], ASSETS_ARG, str(OUT / "_tmp")]
src = (HERE / "render_samples.py").read_text(encoding="utf8")
G = {"__file__": str(HERE / "render_samples.py"), "__name__": "rs_prefix"}
exec(compile(src[:src.index("# ---- A1 封面＝")], "render_samples_prefix", "exec"), G)
INK, BLUE, ORG, GREY, LINE, TINT = (G[k] for k in ("INK", "BLUE", "ORG", "GREY", "LINE", "TINT"))
for _k, _v in (("TC_VAR", "D6"), ("TC_SW", "46"), ("TC_PW", "176"), ("TC_PH", "66"), ("TC_PF", "48"), ("TC_LG", "18")): os.environ[_k] = os.environ.get(_k) or _v
sys.path.insert(0, str(HERE))
import title_d, title_styles as T
from playwright.sync_api import sync_playwright
from PIL import Image
import base64

PHOTO = os.environ["TC_COVER_PHOTO"]
LINES = ["市值第一大的台積電", "非主管年薪只排第 3"]


def photo_uri(h):
    im = Image.open(PHOTO).convert("RGB"); w0, h0 = im.size
    if h == 690:
        cw = round(h0 * 1032 / 690); x = (w0 - cw) // 2; im = im.crop((x, 0, x + cw, h0))
    else:   # 裁短：保留上方（大樓＋tsmc 標誌），裁掉下方路面
        ch = round(w0 * h / 1032); im = im.crop((0, 0, w0, ch))
    im = im.resize((1032, h), Image.LANCZOS); b = io.BytesIO(); im.save(b, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def chips(text_l, subf):
    rows = [(1, "聯發科", "446.5", False), (2, "祥碩", "428.1", False), (3, "台積電", "407.2", True)]
    h = ""
    for n, name, v, hi in rows:
        bg = f"background:{TINT};border:2px solid {BLUE};" if hi else f"background:#fff;border:2px solid {LINE};"
        h += (f"<div style='{bg}border-radius:26px;padding:6px 16px 6px 10px;display:flex;align-items:center;gap:10px;white-space:nowrap'>"
              f"<div style='width:34px;height:34px;border-radius:17px;background:{BLUE if hi else '#9DBFF7'};color:#fff;font-size:22px;font-weight:900;display:flex;align-items:center;justify-content:center'>{n}</div>"
              f"<div><div style='font-size:24px;font-weight:800;line-height:28px;color:{INK}'>{name}</div><div style='font-size:26px;font-weight:900;line-height:30px;color:{INK}'>{v}<span style='font-size:18px'>萬</span></div></div></div>")
    return f"<div style='display:flex;gap:10px'>{h}</div>", 66


def run_A(pg):
    """A 版（2026-11-11 Andy：「調整位置，幫我調整適當」）：右側標題、小卡列、右滑鈕左右緣對齊；間距一致 36px；圈心對齊標題＋小卡垂直中心；咖啡杯在第一行右側。"""
    DA, SWA, PWA, PHA, PFA, GAPA = 380, 46, 176, 66, 48, 22
    RA = DA / 2; ac = RA - SWA / 2
    title_d.CAP_R = SWA / 2
    pxr, pyr = ac * math.cos(math.radians(-45)), ac * math.sin(math.radians(-45))
    t_top, t_r = title_d.solve_ends(ac, pxr, pyr, PWA, PHA, GAPA)
    PB = 102 + 690; TOPGAP = 68   # 上下留白相等：ring 頂到照片 = 右滑鈕底到畫布底
    cy = PB + TOPGAP + RA; cx = 60 + RA; ox = 54; oy = cy - RA - 6; W_ = DA + 12
    cxl = cyl = RA + 6
    p_t = (cxl + ac * math.cos(t_top), cyl + ac * math.sin(t_top)); p_r = (cxl + ac * math.cos(t_r), cyl + ac * math.sin(t_r))
    ring = (f'<svg data-k="ring" width="{W_}" height="{W_}" viewBox="0 0 {W_} {W_}" style="position:absolute;left:{ox}px;top:{oy}px"><path d="M {p_r[0]:.2f} {p_r[1]:.2f} A {ac:.2f} {ac:.2f} 0 1 1 {p_t[0]:.2f} {p_t[1]:.2f}" fill="none" stroke="{BLUE}" stroke-width="{SWA}" stroke-linecap="round"/></svg>')
    pl = cx + pxr - PWA / 2; pt = cy + pyr - PHA / 2
    pill = (f'<div data-k="pill" style="position:absolute;left:{pl:.1f}px;top:{pt:.1f}px;width:{PWA}px;height:{PHA}px;border-radius:{PHA//2}px;background:{ORG}"></div>'
            f'<div data-k="shuo" style="position:absolute;left:{pl:.1f}px;top:{pt:.1f}px;width:{PWA}px;height:{PHA}px;line-height:{PHA}px;text-align:center;font-weight:900;font-size:{PFA}px;color:{INK};white-space:nowrap">透明說</div>')
    co = f'<div data-k="co" style="position:absolute;left:{cx-RA+SWA:.1f}px;width:{DA-2*SWA}px;top:{cy-41+6:.1f}px;text-align:center;font-weight:900;font-size:82px;line-height:82px;color:{INK};white-space:nowrap">台積電</div>'
    LX = 496; GAP = 36; CH = 72; BH = 72; RIGHT = 1048
    chips_rows = [(1, "聯發科", "446.5", False), (2, "祥碩", "428.1", False), (3, "台積電", "407.2", True)]
    def build(fs):
        LH = round(fs * 1.3); T0 = cy - (2 * LH + GAP + CH) / 2
        t = (f'<div data-k="title" style="position:absolute;left:{LX}px;top:{T0:.1f}px;font-size:{fs}px;font-weight:800;line-height:{LH}px;color:{INK};white-space:nowrap">'
             f'<div id="l1">市值第一大的台積電</div><div id="l2">非主管年薪只排<b style="color:{BLUE};font-weight:900">第 3</b></div></div>')
        return t, LH, T0
    # 找最大字級：第一行右緣 + 24 + 咖啡杯可見寬 ≤ 1048，第二行右緣 ≤ 1048
    best = None
    mf = OUT / "_measure.html"; mf.write_text("<meta charset='utf-8'><style>" + T.font_css() + "body{margin:0;font-family:TCS}</style><span style='font-family:TCS;font-weight:900'>測</span><div id='box'></div>", encoding="utf8")
    pg.goto(f"file://{mf}", wait_until="networkidle"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
    for fs in range(60, 40, -1):
        t, LH, T0 = build(fs)
        pg.evaluate("h=>{document.getElementById('box').innerHTML=h}", t); pg.wait_for_timeout(30)
        w1, w2 = pg.evaluate("[document.getElementById('l1').getBoundingClientRect().width, document.getElementById('l2').getBoundingClientRect().width]")
        cupw = round(fs * 0.95); vis = cupw * 0.69
        if LX + w1 + 24 + vis <= RIGHT and LX + w2 <= RIGHT: best = (fs, w1, w2, cupw, vis); break
    fs, w1, w2, cupw, vis = best; Wt = max(w1, w2); t, LH, T0 = build(fs)
    bar = f'<div style="position:absolute;left:{LX-20}px;top:{T0+6:.1f}px;width:5px;height:{2*LH-12}px;border-radius:3px;background:{BLUE}"></div>'
    cup_l = LX + w1 + 24 - 0.172 * cupw; cup_t = T0 + 4
    cup = title_d.CUP.format(w=cupw, h=cupw, l=cup_l, t=cup_t, b=BLUE, o=ORG)
    # 小卡列：總寬 = 標題寬
    cw = (Wt - 2 * 10) / 3; chips = ""
    for n, name, v, hi in chips_rows:
        bg = f"background:{TINT};border:2px solid {BLUE};" if hi else f"background:#fff;border:2px solid {LINE};"
        chips += (f"<div style='{bg}width:{cw:.1f}px;height:{CH}px;box-sizing:border-box;border-radius:{CH//2}px;padding:0 16px;display:flex;align-items:center;justify-content:center;gap:8px;white-space:nowrap'>"
                  f"<div style='flex:none;width:30px;height:30px;border-radius:15px;background:{BLUE if hi else '#9DBFF7'};color:#fff;font-size:20px;font-weight:900;display:flex;align-items:center;justify-content:center'>{n}</div>"
                  f"<div><div style='font-size:22px;font-weight:800;line-height:26px;color:{INK}'>{name}</div><div style='font-size:24px;font-weight:900;line-height:28px;color:{INK}'>{v}<span style='font-size:16px'>萬</span></div></div></div>")
    chips_top = T0 + 2 * LH + GAP
    chips = f"<div data-k='chips' style='position:absolute;left:{LX}px;top:{chips_top:.1f}px;width:{Wt:.1f}px;display:flex;gap:10px'>{chips}</div>"
    btn_top = chips_top + CH + GAP
    extra = (f".cv .sw{{right:auto;bottom:auto;left:{LX}px;top:{btn_top:.1f}px;width:{Wt:.1f}px;height:{BH}px;justify-content:center;box-sizing:border-box}}")
    swipe = G["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    photo = photo_uri(690)
    html = (f'<div class="cv"><div class="hd"></div><div class="strip"><i></i></div><div class="lg">{G["OPEN_RING"]}</div>'
            f'<div class="pic" data-k="photo" style="box-shadow:none;height:690px;background-image:url({photo});background-position:50% 50%"></div>{ring}{pill}{co}{bar}{t}{chips}{cup}{swipe}</div>')
    shoot("cover_A", html, extra, pg)
    return check(pg, "A", dict(fs=fs, w1=w1, w2=w2, Wt=Wt, LX=LX, cy=cy, T0=T0, chips_top=chips_top, btn_top=btn_top, cup_vis_right=cup_l + 0.86 * cupw, photo_to_ring=TOPGAP, bottom_gap=1350 - (btn_top + BH),
                               ends=[title_d.sdist(ac * math.cos(t_), ac * math.sin(t_), pxr, pyr, PWA, PHA) - SWA / 2 for t_ in (t_top, t_r)]))


def check(pg, tag, info):
    from PIL import ImageChops, ImageFilter
    keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
    boxes = T.ink_boxes(pg, keys)
    def mask(k):
        pg.evaluate("""k=>{let s=document.getElementById('iso');if(!s){s=document.createElement('style');s.id='iso';document.head.appendChild(s)}
          s.textContent=%r+'[data-k="'+k+'"],[data-k="'+k+'"] *{visibility:visible !important}'}""" % T.ISO, k)
        return Image.open(io.BytesIO(pg.screenshot())).convert("RGB").split()[1].point(lambda v: 255 if v > 12 else 0)
    ks = [k for k in ("ring", "pill", "shuo", "co", "title", "chips", "cup", "swipe", "list") if k in keys]
    M = {k: mask(k) for k in ks}
    pg.evaluate("document.getElementById('iso').remove()")
    def pd(a, c):
        ba, bc = M[a].getbbox(), M[c].getbbox()
        if not ba or not bc: return 99
        if max(ba[0] - bc[2], bc[0] - ba[2], ba[1] - bc[3], bc[1] - ba[3]) > 40: return 40   # 外框相距 > 40px 不必逐像素量
        box = (max(0, min(ba[0], bc[0]) - 45), max(0, min(ba[1], bc[1]) - 45), min(1080, max(ba[2], bc[2]) + 45), min(1350, max(ba[3], bc[3]) + 45))
        A_, C_ = M[a].crop(box), M[c].crop(box)
        for N in range(1, 41, 1):
            if ImageChops.multiply(A_.filter(ImageFilter.MaxFilter(2 * N + 1)), C_).getbbox(): return N - 1
        return 40
    import itertools
    d = {f"{a}-{c}": pd(a, c) for a, c in itertools.combinations([k for k in ks if k not in ("shuo",)], 2) if not (a == "co" and c == "ring") and not (c == "co" and a == "ring")}
    bad = [k for k, v in d.items() if v <= 0]
    oob = [k for k in keys if boxes.get(k) and (boxes[k][0] < 0 or boxes[k][1] < 0 or boxes[k][2] > 1080 or boxes[k][3] > 1350)]
    # tsmc 標誌
    im = Image.open(PHOTO); w0, h0 = im.size
    if tag == "A": cw_ = round(h0 * 1032 / 690); x0_ = (w0 - cw_) // 2; sc = 1032 / cw_; lg = ((1440 - x0_) * sc + 24, 540 * sc + 102, (1545 - x0_) * sc + 24, 625 * sc + 102)
    else: sc = 1032 / w0; lg = (1440 * sc + 24, 540 * sc + 102, 1545 * sc + 24, 625 * sc + 102)
    hit = [k for k in ks if boxes.get(k) and min(boxes[k][2], lg[2]) - max(boxes[k][0], lg[0]) > 0 and min(boxes[k][3], lg[3]) - max(boxes[k][1], lg[1]) > 0]
    res = dict(info, 重疊=bad, 出界=oob, 像素距=d, 擋到標誌=hit, boxes={k: boxes.get(k) for k in ks})
    json.dump(res, open(OUT / f"overlap_cover_{tag}.json", "w"), ensure_ascii=False, indent=1, default=str)
    b = res["boxes"]
    print(tag, "重疊", len(bad), bad, "出界", oob, "擋標誌", hit, "info", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in info.items() if k != "ends"}, "端點到膠囊", [round(x, 1) for x in info.get("ends", [])])
    print(tag, "左緣", {k: b[k][0] for k in ("title", "chips", "swipe") if b.get(k)}, "右緣", {k: b[k][2] for k in ("title", "chips", "swipe") if b.get(k)}, "cup", b.get("cup"), "像素距", d)
    return res


# ---------------- B ----------------
def run_B():
    SWB = 34; DB = 310; PWB, PHB, PFB = 130, 49, 36; GAPB = 16; RB = DB / 2; ac = RB - SWB / 2
    title_d.CAP_R = SWB / 2
    pxr, pyr = ac * math.cos(math.radians(-45)), ac * math.sin(math.radians(-45))
    t_top, t_r = title_d.solve_ends(ac, pxr, pyr, PWB, PHB, GAPB)
    PIC_TOP, PIC_H = 102, 550
    TT_TOP = PIC_TOP + PIC_H + 28; TFS = 72; TLH = 92
    title_bot = TT_TOP + 2 * TLH; swipe_top = 1350 - 40 - 76
    LIST_H = 3 * 68 + 2 * 12; list_top = title_bot + ((swipe_top - title_bot) - LIST_H) / 2   # 小卡列在標題底與右滑鈕頂之間等距
    cy = list_top + LIST_H / 2; ring_top = cy - RB; cx = 60 + RB
    W_ = DB + 12; ox = 60 - 6; oy = ring_top - 6; cxl = cx - ox; cyl = cy - oy   # svg 內中心
    p_t = (cxl + ac * math.cos(t_top), cyl + ac * math.sin(t_top)); p_r = (cxl + ac * math.cos(t_r), cyl + ac * math.sin(t_r))
    ring = (f'<svg data-k="ring" width="{W_}" height="{W_}" viewBox="0 0 {W_} {W_}" style="position:absolute;left:{ox}px;top:{oy}px"><path d="M {p_r[0]:.2f} {p_r[1]:.2f} A {ac:.2f} {ac:.2f} 0 1 1 {p_t[0]:.2f} {p_t[1]:.2f}" fill="none" stroke="{BLUE}" stroke-width="{SWB}" stroke-linecap="round"/></svg>')
    pill_l = cx + pxr - PWB / 2; pill_t = cy + pyr - PHB / 2
    pill = (f'<div data-k="pill" style="position:absolute;left:{pill_l:.1f}px;top:{pill_t:.1f}px;width:{PWB}px;height:{PHB}px;border-radius:{PHB/2}px;background:{ORG}"></div>'
            f'<div data-k="shuo" style="position:absolute;left:{pill_l:.1f}px;top:{pill_t:.1f}px;width:{PWB}px;height:{PHB}px;line-height:{PHB}px;text-align:center;font-weight:900;font-size:{PFB}px;color:{INK};white-space:nowrap">透明說</div>')
    co = f'<div data-k="co" style="position:absolute;left:{cx-RB+SWB:.1f}px;width:{DB-2*SWB}px;top:{cy-32+12:.1f}px;text-align:center;font-weight:900;font-size:64px;line-height:64px;color:{INK};white-space:nowrap">台積電</div>'
    title = (f'<div data-k="title" style="position:absolute;left:60px;top:{TT_TOP}px;font-size:{TFS}px;font-weight:800;line-height:{TLH}px;color:{INK};white-space:nowrap">市值第一大的台積電<br>非主管年薪只排第 <b style="color:{BLUE};font-weight:900">3</b></div>')
    # 右側：前三名小標籤（直排）
    rows = [(1, "聯發科", "446.5", False), (2, "祥碩", "428.1", False), (3, "台積電", "407.2", True)]
    lx = 60 + DB + 36; ly = list_top
    lst = ""
    for k, (n, name, v, hi) in enumerate(rows):
        bg = f"background:{TINT};border:2px solid {BLUE};" if hi else f"background:#fff;border:2px solid {LINE};"
        lst += (f"<div style='{bg}border-radius:34px;height:68px;width:500px;display:flex;align-items:center;gap:16px;padding:0 24px 0 14px;white-space:nowrap;box-sizing:border-box'>"
                f"<div style='width:40px;height:40px;border-radius:20px;background:{BLUE if hi else '#9DBFF7'};color:#fff;font-size:26px;font-weight:900;display:flex;align-items:center;justify-content:center'>{n}</div>"
                f"<div style='font-size:32px;font-weight:800;width:140px'>{name}</div><div style='font-size:34px;font-weight:900;margin-left:auto'>{v}<span style='font-size:22px'>萬</span></div></div>")
    lst = f"<div data-k='list' style='position:absolute;left:{lx}px;top:{ly}px;display:flex;flex-direction:column;gap:12px'>{lst}</div>"
    css_extra = f"""
.cv .lg{{height:60px;top:{14+8}px}}
.cv .hd{{height:{PIC_TOP}px}}
.cv .sw{{font-size:34px;height:76px}}
.cv .pic{{height:{PIC_H}px;box-shadow:none}}
"""
    swipe = G["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">').replace('stroke-opacity=".3"', 'stroke-opacity=".55"').replace('stroke-opacity=".6"', 'stroke-opacity=".8"')
    logo = G["OPEN_RING"].replace(f'height="{G["LOGO_H"]}"', 'height="60"').replace(f'width="{G["LOGO_W"]}"', f'width="{round(G["LOGO_W"]*60/G["LOGO_H"])}"')
    html = (f'<div class="cv"><div class="hd"></div><div class="strip"><i></i></div><div class="lg">{logo}</div>'
            f'<div class="pic" data-k="photo" style="background-image:url({photo_uri(PIC_H)});background-position:50% 0%"></div>{title}{ring}{pill}{co}{lst}{swipe}</div>')
    return html, css_extra


def shoot(name, html, extra_css, pg):
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{T.font_css()}</style><style>{G["CSS"]}{G["COVER_CSS"]}{G["SWIPE_CSS"]}body{{font-family:\'TCS\',\'Noto Sans TC\',sans-serif}}{extra_css}</style></head><body>{html}</body></html>')
    f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(700); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(250)
    pg.screenshot(path=str(OUT / f"{name}.png")); f.unlink()


mode = os.environ.get("TC_AB", "AB")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
    if "A" in mode: run_A(pg)
    if "B" in mode:
        html, css = run_B(); shoot("cover_B", html, css, pg); check(pg, "B", {})
    b.close()
