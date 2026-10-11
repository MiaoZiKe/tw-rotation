"""第 4 版自繪鏡頭（storyboard_v4_*.md 第 0、5-3、14、15 節）：痛點開場三格、LOGO、比比自我介紹、3D 四宮格、片尾、警語。
開場不放任何網站或別家 App 畫面（只畫空白小視窗、方塊、月曆格）。每個元素都登記外框（v3_check），互不重疊。
手機：所有文字放在 Reels 安全區內（不進底部 320px、右側 140px）。
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

import render_1010 as B
import render_v3 as R
import v3_check as C
from render_1010 import LEMON, WHITE, anim_frame, back_out, clamp, ease_io, ease_out, font, logo_sized, put_sprite, reader, rounded_mask, text_w
from v3_cards import bubble_box, center_head, sprite_union_rect, disclaimer_fn as _disc_v3
from v3_core import ROLE, card_host

THEME = R.THEME
SKY = (120, 190, 240)
PINK = (245, 160, 170)
MINT = (140, 210, 180)
INK = (60, 70, 90)


MCX = 540            # 手機卡片水平中心（畫面正中；內容寬 ≤800 → x 140～940，不進右側 140px 的 Reels 介面區）
MHEAD_Y = 250        # 手機卡片大字的 y（卡片內容整體在 y 250～1580，上下對稱）


def _push(fn, amt=0.03):
    """整張卡片慢推（3 秒內放大 3%）：動畫收尾後畫面也持續微動，不會被判成停格（freezedetect n=0.003 d=0.5）。"""
    def w(cv, t, shot):
        fn(cv, t, shot)
        k = 1 + amt * clamp(t / max(0.5, shot.dur), 0, 1)
        W, H = cv.size
        im = cv.resize((int(W * k) + 1, int(H * k) + 1), Image.BILINEAR)
        ox, oy = (im.width - W) // 2, (im.height - H) // 2
        cv.paste(im.crop((ox, oy, ox + W, oy + H)), (0, 0))
    return w


def _host(cv, L, nm, text, t, mode=None):
    """卡片鏡頭的比比＋泡泡。網頁用一般主持位；手機改放底部安全區上緣（比比在左、泡泡在右，整組水平置中）。"""
    if L.fmt == "web":
        return card_host(cv, L, nm, text, t, mode)
    old = (L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size)
    L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size = 320, 1570, 360, 340, 440
    try:
        card_host(cv, L, nm, text, t, mode)
    finally:
        L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size = old


def _zone(L):
    """內容區（避開標題、比比帶與手機 Reels 介面區）。"""
    if L.fmt == "web":
        return (360, 150, 1680, 800)
    return (140, 460, 940, 1190)


def _icon(d, kind, r):
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    if kind == "k":          # K 線圖示：幾根蠟燭
        n = 7
        for i in range(n):
            cx = x0 + w * (i + 0.5) / n
            top = y0 + h * (0.25 + 0.4 * abs(math.sin(i * 1.3)))
            bot = top + h * 0.3
            col = (230, 90, 90) if i % 2 == 0 else (70, 170, 120)
            d.line([cx, top - h * 0.1, cx, bot + h * 0.1], fill=col, width=3)
            d.rectangle([cx - w / n * 0.25, top, cx + w / n * 0.25, bot], fill=col)
    elif kind == "news":     # 新聞圖示：標題塊＋幾條橫線
        d.rounded_rectangle([x0, y0, x0 + w * 0.35, y0 + h * 0.45], 6, fill=SKY)
        for i in range(5):
            yy = y0 + h * (0.1 + 0.18 * i)
            xs = x0 + (w * 0.42 if i < 3 else 0)
            d.rounded_rectangle([xs, yy, x1 - (0 if i % 2 else w * 0.15), yy + h * 0.07], 4, fill=(200, 210, 225))
    else:                    # 表格圖示：格線
        for i in range(5):
            yy = y0 + h * i / 4
            d.line([x0, yy, x1, yy], fill=(190, 200, 215), width=2)
        for j in range(4):
            xx = x0 + w * j / 3
            d.line([xx, y0, xx, y1], fill=(190, 200, 215), width=2)
        d.rectangle([x0, y0, x1, y0 + h / 4], fill=(225, 235, 245))


def opening_fn(kind):
    """0-1～0-3 痛點開場：kind 1＝空白小視窗飛入、2＝產業鏈方塊亂成一團、3＝12 格月曆閃問號。"""
    cfg = {1: ("看盤資訊太多？", "太多", "alarm", "開好幾個 App，好累…"),
           2: ("產業怎麼看懂？", "看懂", "magnifier", "上下游一堆名字看不懂"),
           3: ("ETF 怎麼配現金流？", "現金流", "piggy", "每個月想領息怎麼排？")}[kind]

    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        center_head(cv, L, cfg[0], t, cfg[1], y=26 if web else MHEAD_Y, px=None if web else 72)
        zx0, zy0, zx1, zy1 = _zone(L)
        d = ImageDraw.Draw(cv)
        if kind == 1:
            if web:
                cells = [(zx0 + 20 + i * 470, zy0 + 30) for i in range(3)] + [(zx0 + 255 + i * 470, zy0 + 360) for i in range(2)]
                size = (430, 290)
            else:
                cells = [(zx0 + 20, zy0 + 0), (zx0 + 410, zy0 + 0), (zx0 + 20, zy0 + 250), (zx0 + 410, zy0 + 250), (zx0 + 215, zy0 + 500)]
                size = (370, 230)
            kinds = ["k", "news", "table", "k", "news"]
            for k, (cx, cy) in enumerate(cells):
                u = ease_out((t - 0.08 * k) / 0.4)
                if u <= 0:
                    continue
                side = [(-600, 0), (600, 0), (0, -500), (0, 600), (-600, 300)][k]
                ox, oy = side[0] * (1 - u), side[1] * (1 - u)
                x0, y0 = cx + ox, cy + oy
                r = (x0, y0, x0 + size[0], y0 + size[1])
                d.rounded_rectangle(r, 18, fill=WHITE, outline=(120, 140, 170), width=3)
                d.rounded_rectangle([r[0], r[1], r[2], r[1] + 34], 18, fill=(225, 232, 242))
                for j in range(3):
                    d.ellipse([r[0] + 16 + j * 24, r[1] + 11, r[0] + 30 + j * 24, r[1] + 25], fill=[(240, 120, 120), (240, 200, 90), (120, 200, 130)][j])
                _icon(d, kinds[k], (r[0] + 30, r[1] + 60, r[2] - 30, r[3] - 30))
                if u >= 1:
                    C.reg(f"win{k}", r)
        elif kind == 2:
            n = 8
            cols = 4 if web else 2
            cw = (zx1 - zx0) / cols
            ch = (zy1 - zy0) / (n // cols)
            pts = []
            for k in range(n):
                c, r_ = k % cols, k // cols
                jx = 18 * math.sin(t * 9 + k * 1.7)
                jy = 14 * math.cos(t * 8 + k * 2.3)
                bw, bh = cw * 0.55, ch * 0.42
                cx = zx0 + cw * (c + 0.5) + jx
                cy = zy0 + ch * (r_ + 0.5) + jy
                pts.append((cx, cy, bw, bh))
            order = [0, 5, 2, 7, 1, 6, 3, 4]
            for a_, b_ in zip(order, order[1:]):
                d.line([pts[a_][0], pts[a_][1], pts[b_][0], pts[b_][1]], fill=(170, 180, 200), width=4)
            for k, (cx, cy, bw, bh) in enumerate(pts):
                u = back_out((t - 0.06 * k) / 0.3)
                if u <= 0:
                    continue
                s = clamp(u, 0.1, 1.05)
                r = (cx - bw * s / 2, cy - bh * s / 2, cx + bw * s / 2, cy + bh * s / 2)
                d.rounded_rectangle(r, 16, fill=[SKY, PINK, MINT, LEMON][k % 4], outline=(110, 120, 140), width=3)
                C.reg(f"blk{k}", (cx - bw / 2 - 20, cy - bh / 2 - 16, cx + bw / 2 + 20, cy + bh / 2 + 16))
        else:
            cols, rows = (4, 3) if web else (3, 4)
            cw = (zx1 - zx0) / cols
            ch = (zy1 - zy0) / rows
            fq = font(B.F_ROUND, 72 if web else 80)
            for k in range(12):
                c, r_ = k % cols, k // cols
                r = (zx0 + c * cw + 10, zy0 + r_ * ch + 10, zx0 + (c + 1) * cw - 10, zy0 + (r_ + 1) * ch - 10)
                u = ease_out((t - 0.03 * k) / 0.3)
                if u <= 0:
                    continue
                d.rounded_rectangle(r, 14, fill=WHITE, outline=(140, 160, 190), width=3)
                d.rectangle([r[0] + 2, r[1] + 2, r[2] - 2, r[1] + 22], fill=(250, 200, 200))
                C.reg(f"cal{k}", r)
                if k % 2 == 0:
                    on = (t - 0.4 - 0.12 * (k // 2)) > 0 and int((t - 0.4) * 4 + k) % 2 == 0
                    if on:
                        tw = text_w(fq, "?")
                        d.text(((r[0] + r[2]) / 2 - tw / 2, (r[1] + r[3]) / 2 - fq.size * 0.55), "?", font=fq, fill=(220, 90, 110))
        _host(cv, L, cfg[2], cfg[3], t)
    return _push(fn)


def logo_fn():
    """0-4：LOGO 60%→105%→100%，比比用頭頂開布幕。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        cx, cy, lg_px = (960, 380, 380) if web else (MCX, 700, 420)
        if t < 0.35:
            s = 0.6 + (1.05 - 0.6) * ease_out(t / 0.35)
        else:
            s = 1.05 - 0.05 * ease_io((t - 0.35) / 0.25)
        px = max(8, int(lg_px * s))
        lg = logo_sized(px)
        cv.paste(lg, (int(cx - px / 2), int(cy - px / 2)), lg)
        C.reg("logo", (cx - lg_px * 0.53, cy - lg_px * 0.53, cx + lg_px * 0.53, cy + lg_px * 0.53))
        f = font(THEME["title_font"], 110 if web else 112)
        tw = text_w(f, "哩股哩股")
        ty = cy + lg_px * 0.55 + 20
        a = ease_out((t - 0.3) / 0.3)
        d = ImageDraw.Draw(cv)
        if a > 0:
            d.rounded_rectangle([cx - tw / 2 - 8, ty + f.size * 0.8, cx - tw / 2 + (tw + 16) * a, ty + f.size * 1.1], 12, fill=LEMON)
            d.text((cx - tw / 2, ty), "哩股哩股", font=f, fill=THEME["ink"])
        C.reg("title", (cx - tw / 2 - 8, ty, cx + tw / 2 + 8, ty + f.size * 1.15))
        _host(cv, L, "reveal", "這些我都整理好了！", t)
    return _push(fn)


def _body_rect(name, idx, foot, size):
    """比比本體的外框（不含頭上的名牌）：名牌與身體之間有一排全透明列，取那排以下。"""
    import numpy as np
    info = B.bibi_index()[name]
    al = np.array(Image.open(info["frames"][idx]).convert("RGBA"))[..., 3] > 40
    rows = al.sum(1)
    ys = np.where(rows > 0)[0]
    top = int(ys[0])
    gaps = [y for y in range(int(ys[0]), int(ys[-1])) if rows[y] == 0]
    if gaps:
        top = next(y for y in range(gaps[-1], int(ys[-1]) + 1) if rows[y] > 0)
    xs = np.where(al[top:].sum(0) > 0)[0]
    sz = int(round(size / 4) * 4)
    s = sz / 512
    return (foot[0] + (int(xs[0]) - 248) * s, foot[1] + (top - 482) * s, foot[0] + (int(xs[-1]) - 248) * s, foot[1] + (int(ys[-1]) - 482) * s)


def intro4_fn():
    """0-5：比比自我介紹（名牌是素材內建）；泡泡在比比旁邊、尾巴指向比比身體（不指名牌），不壓名牌。
    素材 intro 第 8～11 格（0.6～1.2 秒）右前掌舉起揮動，違反四腳原則，改用第 12 格（掌放下）頂替。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        center_head(cv, L, "認識比比", t, "比比", y=26 if web else MHEAD_Y, px=None if web else 72)
        fi = anim_frame("intro", t, "hold")
        if 7 <= fi <= 10:
            fi = 11
        nfr = len(B.bibi_index()["intro"]["frames"])
        if web:
            size, foot = 640, (760, 1040)
        else:
            size = 700
            ur0 = sprite_union_rect("intro", range(nfr), (0, 1280), size)
            gw = (ur0[2] - ur0[0]) + 13 + 34 + 330
            foot = (MCX - gw / 2 - ur0[0], 1280)
        ROLE[0] = "bibi"
        put_sprite(cv, "intro", fi, foot, size)
        if t >= 0.6:
            ur = sprite_union_rect("intro", range(nfr), foot, size)
            lines = ["我是比比，", "帶你逛一圈！"]
            if web:
                bw, bh = 420, 2 * 52 + 40
                tip = (ur[2] + 13, (ur[1] + ur[3]) / 2 - 60)
                x0 = tip[0] + 34
                rect = (x0, tip[1] - bh / 2, x0 + bw, tip[1] + bh / 2)
                bubble_box(cv, lines, rect, tip, t, 42, t0=0.6)
            else:
                br = _body_rect("intro", 15, foot, size)
                bw, bh = 330, 2 * 52 + 40
                tip = (max(ur[2], br[2]) + 13, (br[1] + br[3]) / 2)
                x0 = tip[0] + 34
                rect = (x0, tip[1] - bh / 2, x0 + bw, tip[1] + bh / 2)
                bubble_box(cv, lines, rect, tip, t, 42, t0=0.6)
    return _push(fn)


def grid4_fn(srcs_w, srcs_m):
    """5-3：3D 四宮格（每格只裁 3D 畫布，素材從分鏡指定的來源秒往後播）；比比在四宮格外側，不壓任何一格畫布。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        srcs = srcs_w if web else srcs_m
        if web:
            cw, ch, gap, lab = 646, 347, 12, 46
            x0 = 380
            y0 = 66
        else:
            # 每格＝整張 3D 畫布（1142×1076 → 寬高比 1.06），左右編號圓點與整個模型都入格；四格整組水平置中、垂直置中於安全區
            gap, lab = 12, 46
            cw = 394
            ch = 371
            x0 = MCX - (2 * cw + gap) // 2
            y0 = 290
        for k, (clip, name, win, st0) in enumerate(srcs):
            col, row = k % 2, k // 2
            cx = x0 + col * (cw + gap)
            cy = y0 + row * (ch + lab + gap)
            src = reader(clip).get(st0 + t)
            ww, wh = win[2] - win[0], win[3] - win[1]
            ar = cw / ch
            if ww / wh > ar:
                nh = ww / ar
                win2 = (win[0], (win[1] + win[3]) / 2 - nh / 2, win[2], (win[1] + win[3]) / 2 + nh / 2)
            else:
                nw = wh * ar
                win2 = ((win[0] + win[2]) / 2 - nw / 2, win[1], (win[0] + win[2]) / 2 + nw / 2, win[3])
            u = ease_out(t / 0.35)
            im = src.resize((cw, ch), Image.LANCZOS, box=win2).convert("RGBA")
            im.putalpha(rounded_mask(cw, ch, 14))
            ImageDraw.Draw(im).rounded_rectangle([1, 1, cw - 2, ch - 2], 14, outline=R.DEEP + (255,), width=2)
            ox = (cx + cw / 2 - (x0 + cw + gap / 2)) * (1 - u) * -0.0
            cv.paste(im, (int(cx + ox), cy + lab), im)
            C.reg("site", (cx, cy + lab, cx + cw, cy + lab + ch), role="site")
            f = font(THEME["pill_font"], 24)
            lw = text_w(f, name) + 32
            lay = Image.new("RGBA", (int(lw) + 4, 30), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([0, 0, lw, 28], THEME["pill_radius"] or 14, fill=THEME["pill_bg"] + (255,))
            ld.text((16, 1), name, font=f, fill=THEME["pill_fg"])
            cv.paste(lay, (cx, cy + 2), lay)
            C.reg("label:" + name, (cx, cy + 2, cx + lw, cy + 30))
        from v3_core import footnote4
        pw = R.pill(cv, "產業地圖", L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
        L.head_xy = (L.pill_xy[0] + pw + (36 if web else 30), L.head_y)
        R.headline(cv, L, "還有更多 3D", t, "更多")
        _host(cv, L, "face_surprise_happy", "封裝、HBM、液冷都能轉", t)
        footnote4(cv, L)
    return _push(fn, 0.02)


def end4_fn():
    """14-1 片尾：LOGO → 兩行大字 → 膠囊「搜尋 哩股哩股」；不放網址、信箱。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        W = L.W
        cx = W / 2 if web else MCX
        lg_px = 260 if web else 380
        cy = 200 if web else 560
        s = 1.0 + 0.03 * ease_io(t / 3.0)
        px = int(lg_px * s)
        lg = logo_sized(px)
        cv.paste(lg, (int(cx - px / 2), int(cy - px / 2)), lg)
        C.reg("logo", (cx - lg_px * 0.52, cy - lg_px * 0.52, cx + lg_px * 0.52, cy + lg_px * 0.52))
        f = font(THEME["head_font"], 76 if web else 80)
        y = cy + lg_px * 0.55 + 30
        for i, ln in enumerate(["產業看得懂", "現金流排得出來"]):
            a = ease_out((t - 0.2 - 0.2 * i) / 0.3)
            tw = text_w(f, ln)
            if a > 0:
                R.float_panel(cv, (cx - tw / 2 - 24, y, cx + tw / 2 + 24, y + f.size * 1.3 + 6), int(235 * a), 18)
                ImageDraw.Draw(cv).text((cx - tw / 2, y + 2), ln, font=f, fill=THEME["ink"])
            C.reg(f"echo{i}", (cx - tw / 2 - 24, y, cx + tw / 2 + 24, y + f.size * 1.3 + 6))
            y += f.size * 1.3 + 22
        b = ease_out((t - 0.7) / 0.3)
        pxp = 40 if web else 46
        f2 = font(THEME["pill_font"], pxp)
        w1 = text_w(f2, "搜尋 哩股哩股") + 44
        if b > 0:
            R.pill(cv, "搜尋 哩股哩股", cx - w1 / 2, y + 10, bg=WHITE, fg=THEME["ink"], px=pxp, stroke=False, alpha=b)
        _host(cv, L, "celebrate", "我們網站見！", t)
    return _push(fn)


def disclaimer4_fn():
    """15-1 警語：網頁、手機都改成「整塊內容垂直置中」；手機面板寬 800（x 140～940，水平置中且不進右側 Reels 介面區），原文一字不改。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        W, H = L.W, L.H
        cx = W / 2 if web else MCX
        a = ease_io(t / 0.3)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lg_px = 130 if web else 150
        fs = font(B.F_MED, 28 if web else 26)
        note = B.SPONSOR_NOTE
        maxw = 1500 if web else 800
        nl = [note] if text_w(fs, note) <= maxw else [note[:len(note) // 2 + 1], note[len(note) // 2 + 1:]]
        pw = 1400 if web else 800
        f = font(B.F_MED, 44 if web else 42)
        lines = []
        for para in B.DISCLAIMER:
            cur = ""
            for ch in para:
                if text_w(f, cur + ch) > pw - 100 and cur:
                    lines.append(cur)
                    cur = ""
                cur += ch
            lines.append(cur)
            lines.append("")
        lines = lines[:-1]
        lh = f.size * 1.5
        ph = len(lines) * lh + 90
        nh = 36 * len(nl)
        total = lg_px + 24 + nh + 40 + ph
        zone_h = H if web else 1600          # 手機底部 320px 是 Reels 介面區，垂直置中算到 y=1600
        top = max(24, (zone_h - total) / 2)
        lg = logo_sized(lg_px)
        lay.paste(lg, (int(cx - lg_px / 2), int(top)), lg)
        C.reg("logo", (cx - lg_px / 2, top, cx + lg_px / 2, top + lg_px))
        ny = top + lg_px + 24
        for i, ln in enumerate(nl):
            tw = text_w(fs, ln)
            d.text((cx - tw / 2, ny + i * 36), ln, font=fs, fill=(80, 80, 80))
        C.reg("note", (cx - maxw / 2, ny, cx + maxw / 2, ny + nh))
        py0 = ny + nh + 40
        d.rounded_rectangle([cx - pw / 2, py0, cx + pw / 2, py0 + ph], 30, fill=WHITE, outline=R.DEEP, width=3)
        C.reg("panel", (cx - pw / 2, py0, cx + pw / 2, py0 + ph))
        y = py0 + 45
        for ln in lines:
            if ln:
                d.text((cx - text_w(f, ln) / 2, y), ln, font=f, fill=(26, 26, 26))
            y += lh if ln else lh * 0.45
        if a < 1:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        cv.paste(lay, (0, 0), lay)
    return _push(fn, 0.02)
