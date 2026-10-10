"""第 3 版網頁版（1920×1080 滿版）逐鏡規格，對照 storyboard_v3_web.md（38 鏡、157.2 秒）。

素材：raw_v3/Vxx_desktop.mp4（3200×1800）。focus 座標是來源像素；srcmap 是 [(本鏡秒, 來源秒)] 分段線性，
點擊秒數取自 raw_v3/shots.md，讓「比比腳落下那一格」＝錄影點擊那一格。
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

import render_1010 as B
import render_v3 as R
from v3_core import (CREAM, DEEP, FPS, INK, LEMON, SKY, WHITE, Fn, Focus4, Op, Rec4, Shot4, anim_frame, back_out, clamp, ease_io,
                     ease_out, font, lerp, logo_sized, put_sprite, reader, rounded_mask, text_w)

C = "_desktop"
EMAIL_SCRUB = (2400, 1436, 3140, 1580, 10.0, 19.3, (2412, 1446))


def hold(src_hold, h, ss_after, dur):
    """前 h 秒定格在 src_hold（完整畫面），之後從 ss_after 即時播放。"""
    return [(0, src_hold), (h, src_hold), (h + 1e-4, ss_after), (dur, ss_after + (dur - h))]


def rt(ss, dur):
    return [(0, ss), (dur, ss + dur)]


def feat(sid, dur, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), types=(), scrub=(), mascot=True, side=None,
         cues=(), use_events=True, tap_scale=0.8, soft_hover=False):
    rec = Rec4(clip + C, srcmap, focus=focus, scrub=scrub, mascot=mascot)
    op = Op(rec, idle=idle, extra=extra, types=types, use_events=use_events, tap_scale=tap_scale, soft_hover=soft_hover)
    return Shot4(sid, dur, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op, cues=cues, side=side)


def F(rect, t_draw=1.2, **kw):
    return Focus4(rect, t_draw=t_draw, **kw)


# ───────────────────────── 自繪鏡頭 ─────────────────────────
@__import__("functools").lru_cache(maxsize=32)
def frag_img(clip, t, box, size):
    src = reader(clip).get(t).copy()
    from v3_core import hide_mascot
    hide_mascot(src)
    im = src.crop(box).resize(size, Image.LANCZOS).convert("RGBA")
    im.putalpha(rounded_mask(size[0], size[1], 22))
    ImageDraw.Draw(im).rounded_rectangle([1, 1, size[0] - 2, size[1] - 2], 22, outline=(60, 80, 120, 255), width=3)
    return im


WEB_FRAGS = [("V14_desktop", 17.0, (520, 330, 2300, 1300)), ("V02_desktop", 4.8, (2360, 40, 3200, 1100)),
             ("V20_desktop", 1.0, (440, 100, 3150, 1100)), ("V03_desktop", 2.5, (440, 100, 3150, 1300)),
             ("V07_desktop", 2.5, (440, 100, 2000, 1200)), ("V16_desktop", 1.0, (440, 100, 3150, 1400)),
             ("V21_desktop", 2.5, (440, 400, 3150, 1500)), ("V08_desktop", 2.5, (440, 100, 3150, 1500))]


def chaos_state(t, L, n=8, reverse_from=None):
    rnd = random.Random(7)
    items = []
    W, H = L.W, L.H
    for i in range(n):
        ang = rnd.uniform(0, 2 * math.pi)
        fx, fy = W / 2 + math.cos(ang) * W * 0.9, H / 2 + math.sin(ang) * H * 0.9
        tx = W / 2 + rnd.uniform(-0.38, 0.38) * W * (0.95 if L.fmt == "web" else 0.7)
        ty = H / 2 + rnd.uniform(-0.3, 0.3) * H * (0.85 if L.fmt == "web" else 0.55)
        items.append((fx, fy, tx, ty, rnd.uniform(-9, 9), 0.2 + 0.28 * i))
    return items


def chaos_layer(mobile=False):
    def fn(cv, t, shot):
        L = shot.L
        items = chaos_state(t, L)
        frags = MOBILE_FRAGS if mobile else WEB_FRAGS
        size = (360, 260) if mobile else (560, 330)
        for k, (fx, fy, tx, ty, rot, t0) in enumerate(items):
            u = ease_out((t - t0) / 0.55)
            if u <= 0:
                continue
            clip, st, box = frags[k % len(frags)]
            im = frag_img(clip, st, box, size)
            if rot:
                im = im.rotate(rot * u, expand=True, resample=Image.BICUBIC)
            x, y = lerp(fx, tx, u), lerp(fy, ty, u)
            cv.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)
    return fn


MOBILE_FRAGS = []


def custom_chaos(dur, mobile=False):
    def fn(cv, t, shot):
        L = shot.L
        chaos_layer(mobile)(cv, t, shot)
        # 大字置中
        R.headline_center(cv, L, "看盤資訊太多？", t, "太多") if hasattr(R, "headline_center") else center_head(cv, L, "看盤資訊太多？", t, "太多")
        hs = (360 if L.fmt == "web" else 400)
        put_sprite(cv, "face_sweat", anim_frame("face_sweat", t), (L.W / 2, L.H / 2 + hs * 0.55), hs)
        sub_center(cv, L, "新聞、財報、資金、ETF…每天看到眼花", t)
    return fn


def center_head(cv, L, text, t, hl=None, y=None, px=None):
    f = font(R.THEME["head_font"], px or (110 if L.fmt == "web" else 96))
    tw = text_w(f, text)
    x0 = L.W / 2 - tw / 2
    y = y if y is not None else (170 if L.fmt == "web" else 330)
    d = ImageDraw.Draw(cv)
    R.float_panel(cv, (x0 - 34, y - 14, x0 + tw + 34, y + f.size * 1.32), int(230 * clamp(t / 0.2, 0, 1)), 28)
    k = 0
    x = x0
    hl_i = text.index(hl) if hl and hl in text else -1
    for i, ch in enumerate(text):
        w = text_w(f, ch)
        if hl_i >= 0 and hl_i <= i < hl_i + len(hl):
            u = ease_out((t - 0.4 - 0.04 * (i - hl_i)) / 0.2)
            if u > 0:
                h0, h1 = R.THEME["hl_h"]
                d.rounded_rectangle([x - 2, y + f.size * h0, x + w * u + 2, y + f.size * h1], 6, fill=LEMON)
        u = ease_out((t - 0.04 * i) / 0.22)
        if u > 0:
            lay = Image.new("RGBA", (int(w) + 16, f.size + 40), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((6, 10), ch, font=f, fill=R.THEME["ink"] + (int(255 * u),))
            cv.paste(lay, (int(x) - 6, int(y + (1 - u) * 20) - 10), lay)
        x += w


def sub_center(cv, L, text, t):
    f = font(B.F_BOLD, 44 if L.fmt == "web" else 40)
    tw = text_w(f, text)
    y = L.H - 140 if L.fmt == "web" else 1480
    R.float_panel(cv, (L.W / 2 - tw / 2 - 30, y - 8, L.W / 2 + tw / 2 + 30, y + 62), int(226 * clamp(t / 0.3, 0, 1)), 22)
    ImageDraw.Draw(cv).text((L.W / 2 - tw / 2, y), text, font=f, fill=R.THEME["ink"])


def reveal_shot(sid, dur, clip, st, mobile=False):
    """碎片收進整理好的總覽畫面（布幕拉開）。"""
    def fn(cv, t, shot):
        L = shot.L
        src = reader(clip).get(st)
        from v3_core import hide_mascot
        s2 = src.copy(); hide_mascot(s2)
        if mobile:
            k = min(L.small[2] / s2.width, L.small[3] / s2.height)
            w, h = int(s2.width * k), int(s2.height * k)
            x, y = int((L.W - w) / 2), 330
        else:
            w, h, x, y = L.W, L.H, 0, 0
        im = s2.resize((w, h), Image.LANCZOS).convert("RGBA")
        im.putalpha(rounded_mask(w, h, 28 if mobile else 1))
        u = ease_io((t - 0.3) / 1.0)
        cv.paste(im, (x, y), im)
        if t < 1.4:
            B.curtain(cv, u, (x, y, x + w, y + h))
        else:
            pass
    return fn


def logo_scene(L, t, shot):
    web = L.fmt == "web"
    u = back_out((t - 0.1) / 0.5)
    px = int((460 if web else 330) * clamp(0.6 + 0.4 * u, 0.2, 1.1))
    lg = logo_sized(px)
    cx, cy = (560, 560) if web else (540, 500)
    cv_ = shot._cv
    cv_.paste(lg, (cx - px // 2, cy - px // 2), lg)
    fnm = font(R.THEME["title_font"], 120 if web else 100)
    a = ease_out((t - 0.3) / 0.4)
    if a > 0:
        d = ImageDraw.Draw(cv_)
        tw = text_w(fnm, "哩股哩股")
        d.rounded_rectangle([cx - tw / 2 - 8, cy + px / 2 + 30 + fnm.size * 0.8, cx - tw / 2 + (tw + 16) * a, cy + px / 2 + 30 + fnm.size * 1.1], 10, fill=LEMON)
        d.text((cx - tw / 2, cy + px / 2 + 30), "哩股哩股", font=fnm, fill=R.THEME["ink"])


def multiline_bubble(cv, lines, box, tail, t, px=44):
    u = clamp(back_out(t / 0.25), 0, 1.1)
    if u <= 0.02:
        return
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0) + 80, int(y1 - y0) + 120
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = x0 - 40, y0 - 40
    tl = (tail[0] - ox, tail[1] - oy)
    bw, bh = x1 - x0, y1 - y0
    cx = clamp(tl[0], 120, bw - 80 + 40)
    d.polygon([(cx - 26, 40 + bh - 3), (cx + 26, 40 + bh - 3), tl], fill=WHITE, outline=R.THEME["ink"], width=4)
    d.rounded_rectangle([40, 40, 40 + bw, 40 + bh], R.THEME["panel_r"] + 8, fill=WHITE, outline=R.THEME["ink"], width=4)
    d.polygon([(cx - 22, 40 + bh - 2), (cx + 22, 40 + bh - 2), (lerp(cx, tl[0], 0.85), lerp(40 + bh, tl[1], 0.85))], fill=WHITE)
    f = font(B.F_ROUND, px)
    lh = px * 1.35
    y = 40 + bh / 2 - lh * len(lines) / 2 + 2
    for ln in lines:
        tw = text_w(f, ln)
        d.text((40 + bw / 2 - tw / 2, y), ln, font=f, fill=R.THEME["ink"])
        y += lh
    if u != 1:
        lay = lay.resize((max(1, int(w * u)), max(1, int(h * u))), Image.BILINEAR)
    cv.paste(lay, (int(ox), int(oy + h * (1 - u) / 2)), lay)


def intro_shot(dur, mobile=False):
    def fn(cv, t, shot):
        L = shot.L
        shot._cv = cv
        logo_scene(L, t, shot)
        web = L.fmt == "web"
        size = 760 if web else 640
        foot = (1330, 980) if web else (540, 1500)
        put_sprite(cv, "intro", anim_frame("intro", t, "hold"), foot, size)
        if t > 0.6:
            box = (980, 190, 1700, 400) if web else (60, 860, 1020, 1030)
            tail = (1320, 640) if web else (640, 1120)
            multiline_bubble(cv, ["我是比比，問題解答小助手！", "看不懂就問我"], box, tail, t - 0.6, 44 if web else 46)
    return fn


def benefits_shot(dur, mobile=False):
    items = [("省時間", "V01_desktop", 1.8, (440, 100, 3150, 1100)), ("資訊整理好", "V08_desktop", 2.5, (440, 100, 3150, 1500)),
             ("產業看得懂", "V12a_desktop", 2.0, (440, 150, 3150, 1400)), ("持續進步", "V26_desktop", 4.0, (2300, 100, 3200, 1500))]
    if mobile:
        items = [("省時間", "V01_mobile_v3b", 1.0, (0, 150, 1170, 1450)), ("資訊整理好", "V08_mobile", 2.5, (0, 300, 1170, 1600)),
                 ("產業看得懂", "V12a_mobile", 2.0, (0, 700, 1170, 2000)), ("持續進步", "V26_mobile", 4.0, (0, 200, 1170, 1500))]

    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        cw, ch = (400, 420) if web else (460, 360)
        pos = [(110 + i * 440, 330) for i in range(4)] if web else [(60 + (i % 2) * 500, 560 + (i // 2) * 470) for i in range(4)]
        d = ImageDraw.Draw(cv)
        for i, (lab, clip, st, box) in enumerate(items):
            land = 0.3 + i * 0.6
            u = back_out((t - land) / 0.35)
            if t < land:
                continue
            x, y = pos[i]
            thumb = frag_img(clip, st, box, (cw, int(ch * 0.72)))
            card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle([0, 0, cw - 1, ch - 1], R.THEME["panel_r"] + 6, fill=(255, 255, 255, 240), outline=R.THEME["panel_outline"], width=3)
            card.paste(thumb, (0, 0), thumb)
            f = font(R.THEME["head_font"], 44)
            tw = text_w(f, lab)
            cd.text((cw / 2 - tw / 2, int(ch * 0.72) + 14), lab, font=f, fill=R.THEME["ink"])
            sc = clamp(u, 0.05, 1.1)
            card = card.resize((int(cw * sc), int(ch * sc)), Image.BILINEAR)
            cv.paste(card, (int(x + cw / 2 - card.width / 2), int(y + ch / 2 - card.height / 2)), card)
        a = clamp(t / 0.3, 0, 1)
        center_head(cv, L, "一個網站串起來", t, "串起來", y=170 if web else 330)
        sub_center(cv, L, "省下翻資料的時間，看懂再自己判斷", t)
        put_sprite(cv, "celebrate", anim_frame("celebrate", t, "loop"), (L.W - 200 if web else L.W / 2 + 40, L.H - 150 if web else 1740), 300 if web else 420)
    return fn


# ───────────────────────── 38 鏡 ─────────────────────────
def build():
    S = []
    TEN = 3200

    # 01 痛點開場
    S.append(Shot4("01", 4.2, [], kind="card", foot=False, custom=custom_chaos(4.2), cues=[(0, "pop")]))
    # 02 這些我們整理好了（碎片收進整理好的總覽、布幕拉開）
    def fn02(cv, t, shot):
        reveal_shot("02", 3.6, "V01_desktop", 2.0)(cv, t, shot)
        center_head(cv, shot.L, "這些我們整理好了", max(0, t - 0.3), "整理好", y=110)
        sub_center(cv, shot.L, "別擔心，這些我們都幫你整理成圖了", max(0, t - 0.5))
        name = "reveal" if t < 1.7 else "talk_happy"
        put_sprite(cv, name, anim_frame(name, t, "hold" if name == "reveal" else "loop"), shot.L.host, 300)
    S.append(Shot4("02", 3.6, [], kind="card", foot=False, custom=fn02, cues=[(0, "swish"), (1.2, "ding")]))
    # 03 LOGO＋比比自我介紹
    S.append(Shot4("03", 4.2, [], kind="card", foot=False, custom=intro_shot(4.2), cues=[(0, "pop"), (1.6, "ding")]))

    # ① 總覽＋今日事件
    S.append(feat("04", 5.4, "V01", [(0, 0), (2.2, 2.2), (5.4, 2.2)], "① 一頁看完今天", "一頁看完", "早上不用開 5 個 App，這頁十秒看完今天", "總覽",
                  focus=F((440, 100, 3140, 410), 1.2), idle=[(0, "talk_happy"), (1.9, "face_nod")]))
    S.append(feat("05", 3.6, "V02", rt(1.2, 3.6), "今日事件不漏看", "不漏看", "國際、科技、總經消息，按時間排好", "總覽",
                  focus=F((2360, 60, 3200, 1500), 1.5), idle=[(0, "talk_happy"), (1.3, "news")]))
    # 搜尋
    S.append(feat("06", 3.6, "V27", [(0, 1.9), (0.8, 2.4), (1.3, 4.1), (3.6, 6.4)], "想看什麼，打幾個字就到", "打幾個字", "點搜尋，熱門股票和最近看過的先列給你", "搜尋",
                  focus=F((20, 150, 800, 1300), 1.6), idle=[(0, "face_wink")]))
    S.append(feat("07", 3.6, "V27", [(0, 3.9), (1.6, 5.7), (2.5, 7.4), (3.0, 8.2), (3.6, 8.9)], "打代號或名稱", "代號", "打代號或名稱，點一下直接到那一頁", "搜尋",
                  focus=F((20, 150, 900, 440), 1.7, zoom=False), idle=[(0, "face_wink"), (2.0, "talk_excited")], types=[(0.15, 1.5, (224, 204))]))
    # ② 財經日曆
    S.append(feat("08", 4.8, "V03", hold(3.1, 1.0, 9.5, 4.8), "② 大日子排一起", "大日子", "財報、法說、FED 公布日，一張月曆全排好", "財經日曆",
                  focus=F((2300, 300, 3150, 1720), 1.1), idle=[(0, "calendar")]))

    # ③ 資金流向
    wheel = (600, 480, 1960, 1640)
    S.append(feat("09", 5.4, "V04", [(0, 1.1), (2.0, 3.1), (5.4, 3.1)], "③ 錢往哪裡跑", "錢", "每個族群在領先、改善、轉弱、落後哪一區，一看就知道", "資金流向",
                  focus=F(wheel, 1.2), idle=[(0, "face_think"), (2.0, "talk_explain")]))
    S.append(feat("10", 4.2, "V04", rt(3.5, 4.2), "按播放看輪動", "播放", "我踩一下播放，20 天怎麼輪一路播給你看", "資金流向",
                  focus=F(wheel, 1.6, frame=False, t_zoom=1.6), idle=[(0, "face_shock"), (1.6, "coins")]))
    S.append(feat("11", 4.2, "V06", rt(1.3, 4.2), "大盤的錢分去哪", "分去哪", "從大盤分到產業鏈、族群，再到代表股", "資金流向",
                  focus=F((440, 520, 2150, 1250), 1.2), idle=[(0, "spotlight")]))
    S.append(feat("12", 3.0, "V07", [(0, 1.1), (2.2, 3.3), (3.0, 3.3)], "法人資金在哪", "法人", "法人的錢集中在哪幾個族群，也整理好了", "資金流向",
                  focus=F((480, 100, 1820, 1290), 0.8), idle=[(0, "magnifier")]))
    # ④ 熱力圖
    S.append(feat("13", 4.8, "V08", [(0, 1.1), (2.0, 3.1), (4.8, 3.1)], "④ 哪裡熱一眼看", "一眼看", "整個台股一張圖：越大成交越多，紅漲綠跌", "熱力圖",
                  focus=F((480, 200, 2260, 1120), 1.2), idle=[(0, "magnifier"), (2.0, "face_star")]))
    S.append(feat("14", 5.4, "V09", [(0, 1.1), (2.0, 3.1), (2.0001, 12.2), (5.4, 15.6)], "題材資金熱力", "題材", "題材有多熱？資金、法人、新聞合成 0～100 分", "熱力圖",
                  focus=F((440, 110, 3140, 1480), 1.2), idle=[(0, "fire"), (3.5, "face_love")]))
    S.append(feat("15", 3.0, "V08", rt(12.5, 3.0), "點進產業鏈", "產業鏈", "看到熱的，點下去就進產業鏈", "熱力圖",
                  idle=[(0, "face_star"), (1.5, "talk_excited")]))
    # ⑤ 產業地圖
    S.append(feat("16", 3.6, "V11", [(0, 0), (2.2, 2.2), (3.6, 2.2)], "⑤ 產業鏈地圖", "產業鏈", "半導體、AI 伺服器…每條產業鏈都拆好了", "產業地圖",
                  focus=F((440, 70, 3130, 250), 1.0), idle=[(0, "talk_explain")]))
    S.append(feat("17", 4.8, "V11", [(0, 14.3), (2.2, 16.4), (4.8, 16.4)], "2D 看懂產業鏈", "2D", "圓圈編號對到說明卡，每段在做什麼都寫好", "產業地圖",
                  focus=F((440, 360, 3150, 1500), 1.2), idle=[(0, "talk_explain"), (2.0, "face_nod")]))
    d3 = [("18", "V12a", (1450, 430, 2200, 1150), "3D：AI 伺服器", "AI 伺服器", "運算托盤、銅背板、電源、液冷，一層一層看", "3dglasses"),
          ("19", "V12b", (1050, 640, 2150, 1400), "3D：先進封裝", "先進封裝", "晶片、中介層、載板，原來是這樣疊的", "face_surprise_happy"),
          ("20", "V12c", (1200, 820, 2350, 1320), "3D：HBM", "HBM", "記憶體一層層疊起來，站在運算晶片旁邊", "magnifier"),
          ("21", "V12d", (1250, 600, 2400, 1380), "3D：液冷", "液冷", "從晶片冷板一路到 CDU，熱是這樣帶走的", "boba")]
    for sid, clip, rect, head, hl, sub, idle in d3:
        S.append(feat(sid, 4.2, clip, [(0, 1.5), (4.2, 7.0)], head, hl, sub, "產業地圖", focus=F(rect, 3.0, zoom=False), idle=idle))
    S.append(feat("22", 6.0, "V12e", [(0, 3.1), (1.5, 4.6), (2.5, 8.0), (6.0, 11.4)], "零件是誰做的", "誰做的", "點零件，就知道哪家公司負責、在產業鏈哪個位置", "產業地圖",
                  focus=F((520, 740, 3120, 1130), 3.4, t_zoom=4.1), idle=[(0, "face_proud")]))
    S.append(feat("23", 4.8, "V13", rt(2.2, 4.8), "上下游一張連", "一張連", "誰供貨給誰，一張圖串起來", "產業地圖",
                  focus=F((560, 540, 3000, 1620), 1.2), idle=[(0, "pointer_r")], soft_hover=True))
    # ⑥～⑨
    S.append(feat("24", 4.2, "V14", [(0, 1.1), (1.0, 3.1), (2.4, 4.3), (4.2, 7.6)], "⑥ 個股一頁全有", "一頁全有", "K 線、營收、獲利、籌碼，一頁全看得到", "個股",
                  focus=F((480, 380, 3150, 1000), 1.0, zoom=False), idle="face_nod"))
    S.append(feat("25", 3.0, "V16", [(0, 0.8), (0.6, 2.2), (1.6, 3.4), (3.0, 4.8)], "⑦ 完整名單", "完整名單", "漲跌分佈、法人連買賣、排行，完整名單都能排序", "市場明細",
                  focus=F((1880, 230, 3140, 340), 0.8, zoom=False), idle="face_nod"))
    S.append(feat("26", 3.0, "V17", [(0, 1.0), (0.8, 2.2), (1.6, 6.0), (3.0, 8.0)], "⑧ 公開條件篩", "條件篩", "用公開條件篩一遍，省下自己翻的時間", "選股策略",
                  focus=F((440, 330, 3150, 1500), 0.8, zoom=False), idle="face_think"))
    S.append(feat("27", 3.6, "V18", [(0, 1.1), (2.2, 3.3), (3.6, 3.3)], "⑨ 週期統計", "週期", "每個族群過去在各月份的表現，一張表看完", "週期統計",
                  focus=F((2500, 230, 2790, 1320), 1.0), idle=[(0, "hourglass")]))
    # ⑩ ETF
    S.append(feat("28", 4.2, "V19", [(0, 3.1), (1.2, 3.1), (1.2001, 3.1), (4.2, 6.1)], "⑩ ETF 配息日曆", "配息日曆", "哪天除息、配多少、多久填息，月曆全寫好", "ETF",
                  focus=F((1150, 540, 3150, 1300), 1.0, zoom=False), idle="piggy"))
    S.append(feat("29", 4.8, "V20", [(0, 2.2), (1.2, 2.2), (1.2001, 2.2), (4.8, 5.8)], "各類前五名", "前五名", "每一類最受歡迎、報酬、殖利率前五名，一目了然", "ETF",
                  focus=F((440, 180, 3150, 900), 0.6, zoom=False), idle=[(0, "trophy")]))
    S.append(feat("30", 3.6, "V21", [(0, 3.1), (0.8, 3.1), (0.8001, 3.55), (3.6, 6.35)], "報酬放一起比", "一起比", "幾檔一起比，含息不含息分開算", "ETF",
                  focus=F((460, 540, 2050, 1230), 0.3, zoom=False), idle="face_think"))
    S.append(feat("31", 3.6, "V22", [(0, 2.2), (0.8, 2.2), (0.8001, 9.0), (3.6, 11.8)], "現金流試算", "現金流", "想每月都有配息？組合幫你排好", "ETF",
                  focus=F((440, 500, 3150, 1500), 2.4, zoom=False), idle="calc"))
    S.append(feat("32", 3.0, "V23", [(0, 1.2), (0.8, 2.0), (1.6, 5.0), (3.0, 6.8)], "複利看得到", "複利", "配息再投入差多少，三條線並排看", "ETF",
                  focus=F((460, 400, 2150, 1330), 2.0, zoom=False), idle="growth"))
    # ⑪ 自選 ⑫ 導覽與持續進步
    S.append(feat("33", 3.6, "V24", [(0, 2.3), (0.8, 3.9), (1.8, 5.5), (3.6, 7.6)], "⑪ 存自己的股", "存自己", "想追蹤的股票存起來，每天打開就看到", "自選清單",
                  focus=F((440, 420, 3150, 1000), 2.3, zoom=False), idle=[(0, "face_wink"), (2.2, "star_save")]))
    S.append(feat("34", 4.2, "V25", rt(1.2, 4.2), "看不懂？問比比", "問比比", "每一頁都有導覽，常見問題右下角點我", "導覽",
                  focus=F((1400, 1100, 2250, 1620), 1.8, zoom=False), idle="face_wink"))
    S.append(feat("35", 3.6, "V26", rt(12.3, 3.6), "一直在進步", "進步", "功能持續新增，想要什麼跟我說！", "願望清單",
                  focus=F((2300, 150, 3200, 1750), 1.6, zoom=False), idle="heart_wish"))
    # 36 總結
    S.append(Shot4("36", 3.0, [], kind="card", foot=False, custom=benefits_shot(3.0), cues=[(0.3, "pop"), (0.9, "pop"), (1.5, "pop"), (2.1, "pop")]))
    # 37 片尾、38 警語
    ec = R.end_card(4.8)
    S.append(Shot4("37", 4.8, [], kind="card", foot=False, custom=ec.layers[0].fn, cues=[(0, "pop"), (1.2, "ding")]))
    dc = R.disclaimer_card(6.0, prev=S[-1])
    S.append(Shot4("38", 6.0, [], kind="card", foot=False, custom=dc.layers[0].fn))
    for a, b in zip(S, S[1:]):
        b.prev = a
    return S
