"""第 3 版自繪鏡頭：痛點開場、整理好了、自我介紹、3D 單台介紹／四宮格／更多、好處總結、片尾、警語。
每個元素都登記外框（v3_check），位置依實際比比外框算（泡泡尾巴只指向比比、不壓名牌）。
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw

import render_1010 as B
import render_v3 as R
import v3_check as C
from render_1010 import FPS, LEMON, WHITE, anim_frame, back_out, clamp, ease_io, ease_out, font, lerp, logo_sized, put_sprite, reader, rounded_mask, text_w
from v3_core import Fn, Lay, ROLE, Shot4, fit_size, max_bbox_w

THEME = R.THEME


# ───────────────────────── 小工具 ─────────────────────────
def center_head(cv, L, text, t, hl="", y=30, px=None):
    f = font(THEME["head_font"], px or (84 if L.fmt == "web" else 76))
    tw = text_w(f, text)
    x0 = L.W / 2 - tw / 2
    h = f.size * 1.25
    a = clamp(t / 0.2, 0, 1)
    R.float_panel(cv, (x0 - 30, y - 10, x0 + tw + 30, y + h + 10), int(235 * a), 24)
    C.reg("headline", (x0 - 30, y - 10, x0 + tw + 30, y + h + 10))
    d = ImageDraw.Draw(cv)
    hl_i = text.index(hl) if hl and hl in text else -1
    x = x0
    for i, ch in enumerate(text):
        w = text_w(f, ch)
        if hl_i >= 0 and hl_i <= i < hl_i + len(hl):
            u = ease_out((t - 0.35 - 0.04 * (i - hl_i)) / 0.2)
            if u > 0:
                h0, h1 = THEME["hl_h"]
                d.rounded_rectangle([x - 2, y + f.size * h0, x + w * u + 2, y + f.size * h1], 6, fill=LEMON)
        u = ease_out((t - 0.04 * i) / 0.22)
        if u > 0:
            lay = Image.new("RGBA", (int(w) + 16, f.size + 40), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((6, 10), ch, font=f, fill=THEME["ink"] + (int(255 * u),))
            cv.paste(lay, (int(x) - 6, int(y + (1 - u) * 16) - 10), lay)
        x += w


def line_panel(cv, L, text, t, x, y, px=None, name="subtitle"):
    f = font(B.F_BOLD, px or (40 if L.fmt == "web" else 38))
    tw = text_w(f, text)
    h = f.size * 1.3 + 12
    a = clamp(t / 0.25, 0, 1)
    R.float_panel(cv, (x - 22, y, x + tw + 22, y + h), int(235 * a), 14)
    ImageDraw.Draw(cv).text((x, y + 5), text, font=f, fill=THEME["ink"])
    C.reg(name, (x - 22, y, x + tw + 22, y + h))
    return tw + 44, h


def sprite_union_rect(name, frames, foot, size):
    xs0 = ys0 = 1e9
    xs1 = ys1 = -1e9
    info = B.bibi_index()[name]
    for i in frames:
        r = C.sprite_rect(info["frames"][i], foot, size)
        xs0, ys0, xs1, ys1 = min(xs0, r[0]), min(ys0, r[1]), max(xs1, r[2]), max(ys1, r[3])
    return (xs0, ys0, xs1, ys1)


def mini(clip, st, box, size):
    src = reader(clip).get(st)
    im = src.crop(box).resize(size, Image.LANCZOS).convert("RGBA")
    im.putalpha(rounded_mask(size[0], size[1], 18))
    ImageDraw.Draw(im).rounded_rectangle([1, 1, size[0] - 2, size[1] - 2], 18, outline=(60, 80, 120, 255), width=2)
    return im


def bubble_box(cv, lines, rect, tail, t, px=40, t0=0.0):
    """對話泡泡：rect＝(x0,y0,x1,y1)，tail＝尾巴尖端（只指向比比，呼叫端保證離比比 ≥12px）。單一路徑、尾巴不蓋字。"""
    from v3_core import draw_bubble
    u = clamp((t - t0) / 0.2, 0, 1)
    if u <= 0:
        return
    x0, y0, x1, y1 = rect
    f = font(B.F_ROUND, px)
    lh = px * 1.3
    cy = (y0 + y1) / 2
    ty = cy - lh * len(lines) / 2 + 2
    tw = max(text_w(f, ln) for ln in lines)
    cx = (x0 + x1) / 2
    tr = (cx - tw / 2, ty, cx + tw / 2, ty + lh * len(lines))
    draw_bubble(cv, rect, tail, alpha=u, ink=THEME["ink"], width=4, r=THEME["panel_r"] + 4, text_rect=tr)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        d.text((cx - text_w(f, ln) / 2, ty + i * lh), ln, font=f, fill=THEME["ink"])
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * u)))
    cv.paste(lay, (0, 0), lay)


# ───────────────────────── 01 痛點開場（碎片就位彈出、不互相壓住） ─────────────────────────
DESK = [("V14_desktop", 17.0), ("V02_desktop", 4.8), ("V20_desktop", 1.0), ("V03_desktop", 2.5),
        ("V07_desktop", 2.5), ("V16_desktop", 1.0), ("V21_desktop", 2.5), ("V08_desktop", 2.5)]
MOB = [("V14_mobile", 2.5), ("V16_mobile", 1.0), ("V20_mobile", 1.0), ("V09_mobile", 2.5), ("V18_mobile", 2.5), ("V21_mobile_v3b", 2.5)]


def chaos_fn():
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        center_head(cv, L, "看盤資訊太多？", t, "太多", y=30 if web else 130)
        if web:
            size = (420, 236)
            cells = [(60 + (i % 4) * 465, 190 + (i // 4) * 276) for i in range(8)]
            frags = DESK
            box = (440, 60, 3040, 1522)
        else:
            size = (470, 280)
            cells = [(60 + (i % 2) * 520, 300 + (i // 2) * 310) for i in range(6)]
            frags = MOB
            box = (0, 420, 1170, 1250)
        for k, (cx, cy) in enumerate(cells):
            u = back_out((t - 0.15 - 0.17 * k) / 0.3)
            if t < 0.15 + 0.17 * k:
                continue
            clip, st = frags[k % len(frags)]
            im = mini(clip, st, box, size)
            sc = clamp(u, 0.1, 1.05)
            if sc != 1:
                im = im.resize((max(1, int(size[0] * sc)), max(1, int(size[1] * sc))), Image.BILINEAR)
            cv.paste(im, (int(cx + size[0] / 2 - im.width / 2), int(cy + size[1] / 2 - im.height / 2)), im)
            C.reg(f"frag{k}", (cx, cy, cx + size[0], cy + size[1]))
        # 比比 + 字幕列（窄帶）
        nm = "face_sweat"
        if web:
            hs = 300
            put_sprite(cv, nm, anim_frame(nm, t), (330, 1056), hs)
            line_panel(cv, L, "新聞、財報、資金、ETF…每天看到眼花", t, 560, 930)
        else:
            put_sprite(cv, nm, anim_frame(nm, t), (540, 1640), 330)
            line_panel(cv, L, "新聞、財報、資金、ETF…看到眼花", t, 90, 1680, px=36)
    return fn


# ───────────────────────── 02 這些我們整理好了（畫面由中間往兩側展開，無遮蓋物） ─────────────────────────
def tidy_fn(clip):
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        src = reader(clip).get(2.0 if web else 1.0)
        rx, ry, rw, rh = L.box
        u = ease_io(t / 0.7)
        if web:
            win = (0, 0, src.width, src.height)
        else:
            win = (0, 0, src.width, rh * src.width / rw)
        im = src.resize((int(rw), int(rh)), Image.LANCZOS, box=win).convert("RGBA")
        m = Image.new("L", im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([im.width * (0.5 - 0.5 * u), 0, im.width * (0.5 + 0.5 * u), im.height], 16, fill=255)
        im.putalpha(m)
        cv.paste(im, (rx, ry), im)
        C.reg("site", (rx, ry, rx + rw, ry + rh), role="site")
        if web:
            pw = R.pill(cv, "整理好了", L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
            L.head_xy = (L.pill_xy[0] + pw + 36, L.head_y)
            R.headline(cv, L, "這些我們整理好了", t, "整理好了")
            from v3_core import subtitle_web
            subtitle_web(cv, L, "別擔心，這些我們都幫你整理成圖了", t)
            put_sprite(cv, "talk_happy", anim_frame("talk_happy", t), L.host, fit_size("talk_happy", L.host_w))
        else:
            hx = L.pill_xy[0]
            pw = R.pill(cv, "整理好了", L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
            L.head_xy = (hx + pw + 30, L.head_y)
            R.headline(cv, L, "這些我們整理好了", t, "整理好了")
            from v3_core import bubble_mobile
            put_sprite(cv, "talk_happy", anim_frame("talk_happy", t), L.host, L.host_size)
            bubble_mobile(cv, L, shot, "別擔心，都幫你整理成圖了", t)
        from v3_core import footnote4
        footnote4(cv, L)
    return fn


# ───────────────────────── 03 自我介紹：名牌在比比頭上（素材內建）、泡泡在側邊且延後出現 ─────────────────────────
def intro_fn():
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        if web:
            lg_px, cx, cy = 360, 330, 450
            size, foot = 700, (1330, 1010)
        else:
            lg_px, cx, cy = 330, 540, 330
            size, foot = 600, (400, 1520)
        u = back_out((t - 0.1) / 0.5)
        px = int(lg_px * clamp(0.6 + 0.4 * u, 0.2, 1.1))
        lg = logo_sized(px)
        cv.paste(lg, (cx - px // 2, cy - px // 2), lg)
        C.reg("logo", (cx - lg_px / 2, cy - lg_px / 2, cx + lg_px / 2, cy + lg_px / 2))
        fnm = font(THEME["title_font"], 96 if web else 100)
        a = ease_out((t - 0.3) / 0.4)
        ty = cy + lg_px / 2 + 24
        tw = text_w(fnm, "哩股哩股")
        d = ImageDraw.Draw(cv)
        if a > 0:
            d.rounded_rectangle([cx - tw / 2 - 8, ty + fnm.size * 0.8, cx - tw / 2 + (tw + 16) * a, ty + fnm.size * 1.1], 10, fill=LEMON)
            d.text((cx - tw / 2, ty), "哩股哩股", font=fnm, fill=THEME["ink"])
        C.reg("title", (cx - tw / 2 - 8, ty, cx + tw / 2 + 8, ty + fnm.size * 1.15))
        ROLE[0] = "bibi"
        put_sprite(cv, "intro", anim_frame("intro", t, "hold"), foot, size)
        if t >= 1.3:
            ur = sprite_union_rect("intro", range(9, 16), foot, size)
            if web:
                lines = ["我是比比，", "問題解答小助手！", "看不懂就問我"]
                bw, bh = 420, 3 * 52 + 34
                tip = (ur[0] - 13, 700)
                x1 = tip[0] - 34
                rect = (x1 - bw, tip[1] - bh / 2, x1, tip[1] + bh / 2)
            else:
                lines = ["我是比比，", "問題解答小助手！", "看不懂就問我"]
                bw, bh = 400, 3 * 46 + 34
                tip = (ur[2] + 13, 1340)
                x0 = tip[0] + 34
                rect = (x0, tip[1] - bh / 2, x0 + bw, tip[1] + bh / 2)
            bubble_box(cv, lines, rect, tip, t, 40 if web else 36, t0=1.3)
    return fn


# ───────────────────────── 3D：四宮格、更多 ─────────────────────────
GRID_SRC_W = [("V12a_desktop", "AI 伺服器", (900, 523, 2600, 1437)), ("V12b_desktop", "CoWoS-L 先進封裝", (1030, 663, 2730, 1577)),
              ("V12c_desktop", "HBM 記憶體", (1030, 643, 2730, 1557)), ("V12d_desktop", "液冷散熱", (1050, 443, 2750, 1357))]
GRID_SRC_M = [("V12a_mobile", "AI 伺服器", (235, 900, 935, 1900)), ("V12b_mobile", "CoWoS-L 先進封裝", (235, 900, 935, 1900)),
              ("V12c_mobile", "HBM 記憶體", (235, 900, 935, 1900)), ("V12d_mobile", "液冷散熱", (235, 900, 935, 1900))]


def grid_fn(dur, speed=1.8):
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        srcs = GRID_SRC_W if web else GRID_SRC_M
        if web:
            cw, ch, gap, lab = 726, 390, 12, 46
            x0 = (L.W - (2 * cw + gap)) // 2
            y0 = 82
        else:
            cw, ch, gap, lab = 490, 690, 12, 46
            x0 = 40 + (1000 - (2 * cw + gap)) // 2
            y0 = 146
        for k, (clip, name, win) in enumerate(srcs):
            col, row = k % 2, k // 2
            cx = x0 + col * (cw + gap)
            cy = y0 + row * (ch + lab + gap)
            st = clamp(3.3 + t * speed, 0, 9.0)
            src = reader(clip).get(st)
            im = src.resize((cw, ch), Image.LANCZOS, box=win).convert("RGBA")
            im.putalpha(rounded_mask(cw, ch, 14))
            ImageDraw.Draw(im).rounded_rectangle([1, 1, cw - 2, ch - 2], 14, outline=(R.NAVY if THEME["name"] == "pro" else R.DEEP) + (255,), width=2)
            cv.paste(im, (cx, cy + lab), im)
            C.reg("site", (cx, cy + lab, cx + cw, cy + lab + ch), role="site")
            f = font(THEME["pill_font"], 24)
            lw = text_w(f, name) + 32
            lay = Image.new("RGBA", (int(lw) + 4, 30), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([0, 0, lw, 28], THEME["pill_radius"] or 14, fill=THEME["pill_bg"] + (255,))
            ld.text((16, 1), name, font=f, fill=THEME["pill_fg"])
            cv.paste(lay, (cx, cy + 1), lay)
            C.reg("label:" + name, (cx, cy + 1, cx + lw, cy + 29))
        TITLE = "還有更多 3D 圖可以看"
        SMALL = "AI 伺服器、先進封裝、HBM、液冷…只是其中幾個；站上共 20 種 3D 產品"
        sf = font(B.F_MED, 22 if web else 24)
        if web:
            pw = R.pill(cv, "3D", L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
            L.head_xy = (L.pill_xy[0] + pw + 36, L.head_y)
            R.headline(cv, L, TITLE, t, "更多")
            sw_ = text_w(sf, SMALL)
            sx = L.box[0] + 1616 - sw_ - 4
            ImageDraw.Draw(cv).text((sx, 14), SMALL, font=sf, fill=THEME["ink"])
            C.reg("small", (sx - 4, 12, sx + sw_ + 4, 44))
            from v3_core import subtitle_web, footnote4
            subtitle_web(cv, L, "點選產品，每一個都能自己轉著看", t)
            footnote4(cv, L)
            nm = "face_star" if THEME["name"] == "cute" else "talk_happy"
            put_sprite(cv, nm, anim_frame(nm, t), (1856, 1070), min(fit_size(nm, 100), 150))
        else:
            hx = L.pill_xy[0]
            L.head_y = 18
            pw = R.pill(cv, "3D", L.pill_xy[0], 18, px=L.pill_px)
            L.head_xy = (hx + pw + 30, 18)
            R.headline(cv, L, TITLE, t, "更多")
            ImageDraw.Draw(cv).text((L.box[0], 100), "AI 伺服器、先進封裝、HBM、液冷…只是其中幾個", font=sf, fill=THEME["ink"])
            C.reg("small", (L.box[0] - 2, 98, L.box[0] + text_w(sf, "AI 伺服器、先進封裝、HBM、液冷…只是其中幾個") + 2, 130))
            from v3_core import bubble_mobile, footnote4
            nm = "face_star" if THEME["name"] == "cute" else "talk_happy"
            put_sprite(cv, nm, anim_frame(nm, t), L.host, L.host_size)
            bubble_mobile(cv, L, shot, "點選產品，每一個都能自己轉著看", t)
            footnote4(cv, L)
    return fn


def more_fn():
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        cy = 360 if web else 600
        f = font(THEME["head_font"], 110 if web else 84)
        ln = "換一個產品看看"
        tw = text_w(f, ln)
        u = ease_out(t / 0.3)
        x0 = L.W / 2 - tw / 2
        if u > 0:
            R.float_panel(cv, (x0 - 30, cy - 8, x0 + tw + 30, cy + f.size * 1.25 + 8), int(235 * u), 24)
            ImageDraw.Draw(cv).text((x0, cy), ln, font=f, fill=THEME["ink"])
            C.reg("text", (x0 - 30, cy - 8, x0 + tw + 30, cy + f.size * 1.25 + 8))
        g = font(THEME["pill_font"], 40)
        label = "點選產品"
        gw = text_w(g, label) + 90
        gx, gy = L.W / 2 - (10 if web else 0), cy + f.size * 1.25 + (70 if web else 60)
        u2 = back_out((t - 0.5) / 0.3)
        if u2 > 0.05:
            lay = Image.new("RGBA", (int(gw) + 6, 70), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([0, 0, gw, 62], THEME["pill_radius"] or 31, fill=LEMON + (255,), outline=THEME["ink"] + (255,), width=3)
            ld.text((25, 8), label, font=g, fill=THEME["ink"])
            tx = gw - 52
            ld.polygon([(tx, 18), (tx, 44), (tx + 24, 31)], fill=THEME["ink"] + (255,))
            cv.paste(lay, (int(gx), int(gy)), lay)
            C.reg("badge", (gx, gy, gx + gw, gy + 62))
        # 比比在左邊，用手指向「點選產品」
        nm = "point_r" if THEME["name"] == "cute" else "talk_happy"
        if web:
            put_sprite(cv, nm, anim_frame(nm, t), (L.W / 2 - 200, gy + 150), 330)
        else:
            put_sprite(cv, nm, anim_frame(nm, t), (L.W / 2 - 180, gy + 190), 330)
    return fn


# ───────────────────────── 好處總結 ─────────────────────────
def benefits_fn():
    items_w = [("省時間", "V01_desktop", 1.8, (440, 60, 3040, 1522)), ("資訊整理好", "V08_desktop", 2.5, (440, 60, 3040, 1522)),
               ("產業看得懂", "V12a_desktop", 2.0, (440, 60, 3040, 1522)), ("持續進步", "V26_desktop", 4.0, (440, 60, 3040, 1522))]
    items_m = [("省時間", "V01_desktop", 1.8, (440, 60, 3040, 1522)), ("資訊整理好", "V08_desktop", 2.5, (440, 60, 3040, 1522)),
               ("產業看得懂", "V12a_desktop", 2.0, (440, 60, 3040, 1522)), ("持續進步", "V26_desktop", 4.0, (440, 60, 3040, 1522))]

    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        items = items_w if web else items_m
        center_head(cv, L, "一個網站串起來", t, "串起來", y=30 if web else 130)
        if web:
            cw, ch = 420, 340
            pos = [(70 + i * 455, 200) for i in range(4)]
        else:
            cw, ch = 470, 380
            pos = [(60 + (i % 2) * 520, 330 + (i // 2) * 440) for i in range(4)]
        for i, (lab, clip, st, box) in enumerate(items):
            land = 0.25 + i * 0.35
            if t < land:
                continue
            u = clamp(back_out((t - land) / 0.3), 0.1, 1.05)
            x, y = pos[i]
            th = int(ch * 0.74)
            card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle([0, 0, cw - 1, ch - 1], 22, fill=(255, 255, 255, 245), outline=THEME["panel_outline"], width=2)
            card.paste(mini(clip, st, box, (cw - 24, th - 8)), (12, 10), mini(clip, st, box, (cw - 24, th - 8)))
            f = font(THEME["head_font"], 40)
            tw = text_w(f, lab)
            cd.text((cw / 2 - tw / 2, th + 14), lab, font=f, fill=THEME["ink"])
            if u != 1:
                card = card.resize((int(cw * u), int(ch * u)), Image.BILINEAR)
            cv.paste(card, (int(x + cw / 2 - card.width / 2), int(y + ch / 2 - card.height / 2)), card)
            C.reg(f"card{i}", (x, y, x + cw, y + ch))
        if web:
            line_panel(cv, L, "省下翻資料的時間，看懂再自己判斷", t, 150, 640)
            nm = "celebrate" if THEME["name"] == "cute" else "talk_happy"
            put_sprite(cv, nm, anim_frame(nm, t), (1760, 1040), min(fit_size(nm, 300), 300))
        else:
            line_panel(cv, L, "省下翻資料的時間，看懂再自己判斷", t, 60, 1280, px=34)
            nm = "celebrate" if THEME["name"] == "cute" else "talk_happy"
            put_sprite(cv, nm, anim_frame(nm, t), (540, 1700), 360)
    return fn


# ───────────────────────── 片尾卡、警語卡（全部置中） ─────────────────────────
def end_fn():
    def fn(cv, t, shot):
        L = shot.L
        W, H = L.W, L.H
        web = L.fmt == "web"
        lg_px = 300 if web else 420
        cy = 230 if web else 470
        u = back_out(t / 0.45)
        px = max(8, int(lg_px * (0.85 + 0.15 * clamp(u, 0, 1.2))))
        lg = logo_sized(px)
        cv.paste(lg, (W // 2 - px // 2, cy - px // 2), lg)
        C.reg("logo", (W / 2 - lg_px / 2, cy - lg_px / 2, W / 2 + lg_px / 2, cy + lg_px / 2))
        f = font(THEME["title_font"], 96 if web else 112)
        title = "哩股哩股"
        tw = text_w(f, title)
        ty = cy + lg_px / 2 + 26
        a = ease_out((t - 0.2) / 0.3)
        d = ImageDraw.Draw(cv)
        if a > 0:
            d.rounded_rectangle([W / 2 - tw / 2 - 6, ty + f.size * 0.8, W / 2 - tw / 2 + (tw + 12) * a, ty + f.size * 1.1], 12, fill=LEMON)
            d.text((W / 2 - tw / 2, ty), title, font=f, fill=THEME["ink"])
        C.reg("title", (W / 2 - tw / 2 - 6, ty, W / 2 + tw / 2 + 6, ty + f.size * 1.15))
        b = ease_out((t - 0.45) / 0.3)
        py = ty + f.size * 1.5
        px1 = 40 if web else 46
        f2 = font(THEME["pill_font"], int(px1 * (0.85 if THEME["name"] == "pro" else 1)))
        w1 = text_w(f2, "搜尋 哩股哩股") + 44
        w2 = text_w(f2, "免費註冊") + 44
        gap = 40
        x = W / 2 - (w1 + gap + w2) / 2
        if b > 0:
            R.pill(cv, "搜尋 哩股哩股", x, py, bg=WHITE, fg=THEME["ink"], px=px1, stroke=False, alpha=b)
            R.pill(cv, "免費註冊", x + w1 + gap, py, bg=LEMON, fg=THEME["ink"], px=px1, stroke=False, alpha=b)
        size = 300 if web else 420
        foot = (W / 2 if web else 330, (1030 if web else 1640))
        ROLE[0] = "bibi"
        put_sprite(cv, "wave", anim_frame("wave", t), foot, size)
        if t > 0.6 and THEME["name"] == "cute":
            ur = sprite_union_rect("wave", range(12), foot, size)
            bw, bh = (380, 100) if web else (380, 150)
            x0 = ur[2] + 47
            rect = (x0, (ur[1] + ur[3]) / 2 - bh / 2, x0 + bw, (ur[1] + ur[3]) / 2 + bh / 2)
            lines = ["我們網站見，掰掰～"] if web else ["我們網站見，", "掰掰～"]
            bubble_box(cv, lines, rect, (ur[2] + 13, (ur[1] + ur[3]) / 2), t, 38, t0=0.6)
        elif t > 0.6:
            line_panel(cv, L, "我們網站見", t, W / 2 + 200 if web else 600, foot[1] - (60 if web else 100), px=34)
    return fn


def disclaimer_fn():
    def fn(cv, t, shot):
        L = shot.L
        W, H = L.W, L.H
        web = L.fmt == "web"
        a = ease_io(t / 0.3)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lg_px = 130 if web else 160
        top = 70 if web else 260
        lg = logo_sized(lg_px)
        lay.paste(lg, (W // 2 - lg_px // 2, top), lg)
        C.reg("logo", (W / 2 - lg_px / 2, top, W / 2 + lg_px / 2, top + lg_px))
        fs = font(B.F_MED, 28 if web else 30)
        tw = text_w(fs, B.SPONSOR_NOTE)
        ny = top + lg_px + 26
        d.text((W / 2 - tw / 2, ny), B.SPONSOR_NOTE, font=fs, fill=(80, 80, 80))
        C.reg("note", (W / 2 - tw / 2, ny, W / 2 + tw / 2, ny + 38))
        pw = 1400 if web else 960
        f = font(B.F_MED, 44 if web else 46)
        lines = []
        for para in B.DISCLAIMER:
            cur = ""
            for ch in para:
                if text_w(f, cur + ch) > pw - 120 and cur:
                    lines.append(cur); cur = ""
                cur += ch
            lines.append(cur)
            lines.append("")
        lines = lines[:-1]
        lh = f.size * 1.5
        ph = len(lines) * lh + 100
        py0 = ny + 80
        d.rounded_rectangle([W / 2 - pw / 2, py0, W / 2 + pw / 2, py0 + ph], 30, fill=WHITE, outline=R.DEEP, width=3)
        C.reg("panel", (W / 2 - pw / 2, py0, W / 2 + pw / 2, py0 + ph))
        y = py0 + 50
        for ln in lines:
            if ln:
                d.text((W / 2 - text_w(f, ln) / 2, y), ln, font=f, fill=INK2)
            y += lh if ln else lh * 0.45
        if a < 1:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        cv.paste(lay, (0, 0), lay)
    return fn


INK2 = (26, 26, 26)
