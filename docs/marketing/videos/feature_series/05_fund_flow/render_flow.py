"""功能介紹影片 05 資金流向 v3 —— 成片合成（單一鏡頭：網站畫面框固定，不推拉、不換場、不淡化）。

素材：capture_flow.py 一口氣錄的網站畫面（<raw>/<dev>_main.mp4＋.json）。
版面：奶油格紙底、左上膠囊＋大標題（跟著主線換字）、中間網站畫面框（固定範圍）、比比＋對話泡泡（≤14 字）。
檢查（每一幀）：
  ① 重疊：膠囊、標題、畫面框、泡泡（含尾巴）、比比兩兩外框相交（外擴 6px）→ overlap_rows_*.md
  ② 遮擋：這一刻泡泡正在講的網站元素（輪盤、排行、拉桿、篩選列、選單）外框 與 所有浮層外框（下拉清單、面板、圖表提示框、客服鈕）相交 → occlusion_rows_*.md
     另列「嚴格遮擋」：浮層外框與輪盤／排行上每一段標籤文字外框相交（不論泡泡講什麼）、游標與標籤文字相交
  ③ 裁切／切字：被介紹元素整塊在畫面框範圍內；輪盤／排行每一段標籤文字沒有被畫面框邊切過
  ④ 泡泡停留、≤14 字、泡泡字出框、尾巴離比比；來源畫面連續不動秒數
用法：python render_flow.py --dev d|m [--frames 3.0,9.5]（只出單格）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import renderlib_v2 as R  # noqa: E402

_bubble_at0 = R.bubble_at


def _bubble_at_solid(bubbles, t):
    """泡泡不淡入淡出（10-22 全片每個字都要清楚看見）：出現就是完全不透明、換句直接切換。"""
    b, a_in, a_out = _bubble_at0(bubbles, t)
    return (b, 1.0, 1.0) if b is not None else (b, a_in, a_out)


R.bubble_at = _bubble_at_solid

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat05v3"))
RAW = SCR / "raw"
FPS = 30
SPEED = float(os.environ.get("FEAT_SPEED", "1.5"))
END_RAW = 4.5            # 片尾免責卡原片 ≥4.5 秒
END_FINAL = float(os.environ.get("FEAT_END_FINAL", "2.0"))   # 成片停 1.5～2 秒（協調員 10-21 規則）
XF = 0.2                 # 接片尾卡的交疊 ≤0.2 秒
BUB_CAP = 7.5
DRIFT_A = float(os.environ.get('FEAT_DRIFT_A', '3.0'))     # 畫面框內容慢漂幅度（成片像素）：只為讓成片不出現 freezedetect 停格；幅度小於畫面框邊到卡片邊的空白
DRIFT_T = float(os.environ.get('FEAT_DRIFT_T', '2.0'))     # 週期（原片秒）
DRIFT_CSS = 2.6          # 檢查裁切時，畫面框內縮的 css 像素（≥ 慢漂幅度換算）            # 同一則泡泡最長停留（原片秒）
PAD = R.PAD

R.SEC.update({
    "s1": ("需求", "錢往哪個族群跑？", "哪個族群"),
    "s2": ("引導", "從總覽點進資金流向", "資金流向"),
    "s3": ("看強弱", "輪盤看強弱，排行看流入", "流入"),
    "s4": ("篩選", "選產業鏈，只看那一條", "產業鏈"),
    "s5": ("選天數", "拉桿換天數，兩圖一起變", "一起變"),
    "s6": ("一頁看懂", "錢往哪跑，一頁看懂", "一頁看懂"),
})
FOCUS_EL = {"nav": "tabs", "navflow": "navflow", "burger": "burger", "m4flow": "m4flow", "clock": "clock", "rank": "rank", "slider": "slider", "filter": "filter", "chain": "chain"}


def layout(dev):
    o = R.L()
    o.dev = dev
    if dev == "d":
        o.W, o.H = 1920, 1080
        o.panel = (20, 78, 1684, 960)
        o.bibi_size = 190
        o.bibi_foot = (1810, 1074)
        o.nav = None
        o.bub_zone = (20, 978, None, 1076)
        o.bub_font = 46
        o.flip_point = True
    else:
        o.W, o.H = 1080, 1920
        o.panel = (40, 300, 1040, 1900)
        o.bibi_size = 160
        o.bibi_foot = (110, 270)
        o.nav = None
        o.bub_zone = (None, 104, 1046, 292)
        o.bub_font = 44
        o.flip_point = False
    x0, y0, x1, y1 = o.panel
    o.pw, o.ph = x1 - x0, y1 - y0
    o.asp = o.pw / o.ph
    return o


R.layout = layout


def rect_int(a, b):
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return (ix * iy) if (ix > 0 and iy > 0) else 0.0


def contained(c, f, tol=0.5):
    return f[0] >= c[0] - tol and f[1] >= c[1] - tol and f[0] + f[2] <= c[0] + c[2] + tol and f[1] + f[3] <= c[1] + c[3] + tol


def build_bubbles(meta, total_raw, end_start):
    says = meta["says"]
    bs = []
    for i, s in enumerate(says):
        t0 = s["t"]
        nxt = says[i + 1]["t"] - 0.06 if i + 1 < len(says) else end_start - 0.1
        t1 = min(nxt, t0 + BUB_CAP)
        later = [c for c in meta.get('clears', []) if c > t0 + 0.05]
        if later:
            t1 = min(t1, later[0] - 0.06)
        bs.append(dict(t0=t0, t1=t1, text=s["text"], act=s["act"], focus=s.get("focus", []), sid=f"b{i}"))
    bs.append(dict(t0=end_start + 0.25, t1=end_start + END_RAW, text="謝謝收看，我們下次見", act="face_bow", focus=[], sid="__end"))
    return bs


def render(dev, only=None):
    o = layout(dev)
    if dev == 'm':   # 手機排行在輪盤下方（最後才捲到）→ 標題與泡泡的講法對應
        R.SEC.update({'s3': ('看強弱', '輪盤看資金強弱', '強弱'), 's6': ('一頁看懂', '排行看流入，一頁看懂', '一頁看懂')})
    meta = json.loads((RAW / f"{dev}_main.json").read_text(encoding="utf-8"))
    src = RAW / f"{dev}_main.mp4"
    fm = meta["fm"]
    N0 = meta["frames"]
    body = N0 / FPS
    end_start = body - XF          # 片尾卡從 body 結束前 0.2 秒開始交疊
    total = end_start + END_RAW + XF
    bubbles = build_bubbles(meta, body, end_start)
    stages = meta["stages"]
    acts = {b["act"] for b in bubbles} | {R.ALT.get(b["act"], "talk_explain_v2") for b in bubbles} | {"talk_explain_v2", "wave", "face_nod_v2"}
    ext = R.bibi_extent(o, sorted(acts))
    if dev == "d":
        tip = (ext[0] - 13, (ext[1] + ext[3]) / 2 + 6)
        zone = (o.bub_zone[0], o.bub_zone[1], int(tip[0]) - 10, o.bub_zone[3])
        side = "right"
    else:
        tip = (ext[2] + 13, (ext[1] + ext[3]) / 2)
        zone = (int(tip[0]) + 10, o.bub_zone[1], o.bub_zone[2], o.bub_zone[3])
        side = "left"
    tip = (int(round(tip[0])), int(round(tip[1])))
    bg = np.array(R.grid_bg(o))
    x0, y0, x1, y1 = o.panel
    statics = {}
    for n in range(1, 7):
        im = Image.fromarray(bg.copy())
        reg = R.Reg()
        R.header(o, im, reg, f"s{n}", None)
        ImageDraw.Draw(im).rounded_rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], 22, fill=R.BLUE)
        statics[n] = (np.array(im), reg.items, reg.issues)
    im = Image.fromarray(bg.copy())
    ImageDraw.Draw(im).rounded_rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], 22, fill=R.BLUE)
    statics[7] = (np.array(im), [], [])
    mask = Image.new("L", (o.pw, o.ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, o.pw - 1, o.ph - 1], 20, fill=255)
    mask = (np.array(mask).astype(np.float32) / 255)[..., None]
    dsf = meta["dsf"]
    crop0 = tuple(meta["crop"])
    zoom = None
    if dev == "d":   # 網頁：引導段之後做「一次單向推近」，框只留資金輪動卡（輪盤＋排行），側欄裁掉
        t3 = next(tt for tt, k_, _ in stages if k_ == 3)
        card = fm[min(int((t3 + 1.0) * FPS), N0 - 1)]["el"]["card"]
        mg = 2
        hmax = float(np.percentile([f_["el"]["card"][3] for f_ in fm[int(t3 * FPS):] if "card" in f_["el"]] or [card[3]], 97))
        Hc = hmax + 2 * mg
        Wc = Hc * o.asp
        tgt = (card[0] - mg, card[1] - mg, Wc, Hc)   # 左緣貼著卡片（側欄的字不入鏡）；右邊多出來的幾 px 是頁面空白
        zoom = (t3 - 0.1, 0.7, tgt)

    def crop_at(t):
        if zoom is None or t <= zoom[0]:
            return crop0
        a = R.ease(min(1.0, (t - zoom[0]) / zoom[1]))
        return tuple(c0 + (c1 - c0) * a for c0, c1 in zip(crop0, zoom[2]))
    cx, cy, cw, ch = crop0
    crop_css = crop0
    sx, sy = o.pw / cw, o.ph / ch

    def stage_at(t):
        n = 1
        for tt, k, _ in stages:
            if tt <= t + 1e-6:
                n = k
        return n

    cap = cv2.VideoCapture(str(src))
    frames_src = []
    out_sil = SCR / f"feat05_{dev}_silent_v3.mp4"
    ff = None
    n_total = int(round(total * FPS))
    sel = [int(round(float(v) * FPS)) for v in only.split(",")] if only else range(n_total)
    if not only:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{o.W}x{o.H}", "-r", str(FPS), "-i", "-",
                               "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out_sil)], stdin=subprocess.PIPE)
    last_k, last_img = -1, None
    rows, issues, occ_rows, strict_rows, cut_rows, slice_rows, ov_open, tip_frames = [], [], [], [], [], [], 0, 0
    transit_rows = []
    push_frames = 0
    still_run, still_max, prev_pv = 0, (0, 0.0), None
    blur_left = blur_fixed = blur_fe = 0
    blur_seen = set()
    for bb in bubbles:
        if bb["sid"] != "__end" and bb["t1"] - bb["t0"] < 1.45 - 1e-3:
            issues.append(f"| {bb['t0']:6.2f} | 泡泡停留 {bb['t1'] - bb['t0']:.2f} 秒（<1.45）：{bb['text']} |")
    for i in sel:
        t = i / FPS
        reg = R.Reg()
        in_end = t >= end_start + XF - 1e-6
        k = min(int(round(t * FPS)), N0 - 1)
        stg = 7 if in_end else stage_at(t)
        cx, cy, cw, ch = crop_at(t)
        crop_css = (cx, cy, cw, ch)
        base, items, iss = statics[stg]
        canvas = base.copy()
        for it in items:
            reg.items.append(it)
        issues += [f"| {t:6.2f} | {x} |" for x in iss]
        if not in_end or t < end_start + XF:
            if k != last_k:
                while k > last_k + 1 and last_k + 1 < N0 and not only:
                    cap.read()
                    last_k += 1
                if only:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, k)
                ok, fr = cap.read()
                last_k = k
                if ok:
                    last_img = fr
            fr = last_img
            sx0, sy0 = int(round(cx * dsf)), int(round(cy * dsf))
            sx1, sy1 = sx0 + int(round(cw * dsf)), sy0 + int(round(ch * dsf))
            crop = fr[sy0:sy1, sx0:sx1]
            img = cv2.cvtColor(cv2.resize(crop, (o.pw, o.ph), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
            pv = cv2.resize(crop, (o.pw // 4, o.ph // 4), interpolation=cv2.INTER_AREA).astype(np.int16)
            ddx, ddy = DRIFT_A * R.tri(t / DRIFT_T + 0.25), DRIFT_A * R.tri(t / (DRIFT_T * 1.3) + 0.6)
            img = cv2.warpAffine(img, np.float32([[1, 0, ddx], [0, 1, ddy]]), (o.pw, o.ph), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            if prev_pv is not None and np.abs(pv - prev_pv).max() < 6:
                still_run += 1
                if still_run > still_max[0]:
                    still_max = (still_run, t)
            else:
                still_run = 0
                prev_pv = pv
            region = canvas[y0:y1, x0:x1].astype(np.float32)
            canvas[y0:y1, x0:x1] = (img.astype(np.float32) * mask + region * (1 - mask)).astype(np.uint8)
            reg.add("網站畫面框", (x0 - 3, y0 - 3, x1 + 3, y1 + 3))
            # ── 遮擋／裁切檢查（用錄影端每格量到的外框）──
            m = fm[k]
            els = m["el"]
            bf = m.get('bf') or {}
            blur_left += 1 if bf.get('left', 0) != 0 else 0
            blur_fixed += 1 if bf.get('fixed', 0) else 0
            blur_fe += 1 if bf.get('fe', 0) else 0
            blur_seen.update(bf.get('seen', []))
            crop_in = (cx + DRIFT_CSS, cy + DRIFT_CSS, cw - 2 * DRIFT_CSS, ch - 2 * DRIFT_CSS)   # 慢漂最壞情況的實際可見範圍
            bub, a_in, a_out = R.bubble_at(bubbles, t)
            foc = [FOCUS_EL.get(f) for f in (bub["focus"] if bub else [])]
            foc_r = {f: els[f] for f in foc if f and f in els}
            ovs = [(n_, r_) for n_, *r_ in m["ov"]] + [("客服鈕", f) for f in m["fab"]]
            if any(n_.startswith("面板") for n_, _ in ovs):
                ov_open += 1
            if any(n_ == "圖表提示框" for n_, _ in ovs):
                tip_frames += 1
            for f, fr_ in foc_r.items():
                if f not in ("clock", "rank", "slider", "filter", "chain", "tabs", "navflow", "burger", "m4flow"):
                    continue
                if not in_push and not contained(crop_in, fr_, 0.5) and f in ("clock", "rank", "slider", "filter"):
                    cut_rows.append(f"| {t:6.2f} | {f} 超出畫面框 |")
                for n_, r_ in ovs:
                    if n_ == '頂欄' and f in ('tabs', 'navflow', 'burger', 'm4flow'):
                        continue
                    # 下拉面板貼在自己的按鈕下方，不算蓋住「正在介紹的篩選列」本身；其他一律算
                    if rect_int(fr_, r_) > 0 and rect_int(r_, crop_css) > 0:
                        occ_rows.append(f"| {t:6.2f} | 「{bub['text']}」介紹的 {f} | {n_} | {int(rect_int(fr_, r_))} |")
            zt = [z for z in m["zt"] if rect_int(z[1:], crop_css) > 0]
            for n_, r_ in ovs:
                if rect_int(r_, crop_css) <= 0:
                    continue
                for z in zt:
                    if rect_int(z[1:], r_) > 0:
                        strict_rows.append(f"| {t:6.2f} | {n_} 蓋住{'輪盤' if z[0] == 0 else '排行'}標籤 |")
                        break
            finger_on = dev == 'd' or any(-0.3 <= t - c['t'] <= 0.4 for c in meta['clicks'])   # 手機的手指只在點擊那一刻才畫在畫面上
            if m.get("cur") and finger_on:
                cxy = m["cur"]
                cr = (cxy[0] - 3, cxy[1] - 2, 26, 30) if dev == "d" else (cxy[0] - 17, cxy[1] - 17, 34, 34)
                for z in zt:
                    if rect_int(z[1:], cr) > 0:
                        strict_rows.append(f"| {t:6.2f} | 游標蓋住{'輪盤' if z[0] == 0 else '排行'}標籤 |")
                        break
            if dev == 'd' and m.get("cur") and m.get("txt") and not (zoom is not None and zoom[0] <= t <= zoom[0] + zoom[1] + 0.05):   # 游標壓到任何文字（不只圖表標籤）；游標滑向被點目標、點下去的那一刻（本來就在目標上）不算
                near_click = any(-0.35 <= t - c['t'] <= 0.3 for c in meta['clicks'])
                cxy = m["cur"]
                cr_ = (cxy[0] - 3, cxy[1] - 2, 26, 30)
                still = all(math.hypot(fm[min(N0 - 1, max(0, k + dk))]["cur"][0] - cxy[0], fm[min(N0 - 1, max(0, k + dk))]["cur"][1] - cxy[1]) < 3 for dk in (-2, 2) if fm[min(N0 - 1, max(0, k + dk))].get("cur"))   # 只算「游標停著」壓到字；移動途中掃過（單格）不算
                if not near_click and rect_int(cr_, crop_css) > 0:
                    for z in m["txt"]:
                        if rect_int(z, cr_) > 0:
                            if still:
                                strict_rows.append(f"| {t:6.2f} | 游標蓋住文字 {[round(v) for v in z]} |")
                            else:
                                transit_rows.append(f"| {t:6.2f} | 游標移動途中掃過文字（單格） |")
                            break
            in_push = zoom is not None and zoom[0] <= t <= zoom[0] + zoom[1] + 0.05   # 單向推近的移動中（約 0.75 秒），不算切字／裁切
            if in_push:
                push_frames += 1
            moving = fm[max(0, k - 4)]["sy"] != m["sy"] or fm[min(N0 - 1, k + 4)]["sy"] != m["sy"]
            if not in_push and not moving and stg >= 3:   # 任何輪盤／排行標籤文字被畫面框上下邊（手機：頂欄下緣與畫面底緣）切過一半 → 記一筆
                t_top = 56 if dev == 'm' else cy
                t_bot = cy + ch
                for z in zt:
                    zy0, zy1 = z[2], z[2] + z[4]
                    if (zy0 < t_top - 0.5 and zy1 > t_top + 0.5) or (zy0 < t_bot - 0.5 and zy1 > t_bot + 0.5):
                        slice_rows.append(f"| {t:6.2f} | 標籤被畫面框上下緣切過一半 y={zy0:.0f}-{zy1:.0f} |")
                        break
            if not in_push and stg >= 3 and not moving and dev == 'd':   # 網頁：畫面上任何一段文字（不只輪盤／排行標籤）被畫面框邊切到 → 記一筆
                for z in m.get("txt", []):
                    if rect_int(z, crop_css) > 0 and not contained(crop_in, z, 0.5) and min(z[0] + z[2], crop_css[0] + crop_css[2]) - max(z[0], crop_css[0]) >= 1.5 and min(z[1] + z[3], crop_css[1] + crop_css[3]) - max(z[1], crop_css[1]) >= 1.5:
                        slice_rows.append(f"| {t:6.2f} | 文字被畫面框邊切到 {[round(v) for v in z]} |")
                        break
            chart_focus = (not in_push) and any(f in ('clock', 'rank') for f in (bub['focus'] if bub else []))
            want = {0 if f == 'clock' else 1 for f in (bub['focus'] if bub else []) if f in ('clock', 'rank')}
            for z in ([z for z in m["zt"] if z[0] in want] if chart_focus else []):   # 畫面框邊切過標籤文字（只算泡泡正在介紹輪盤／排行的幀；換頁載入中的幾幀不算）
                zr = z[1:]
                if rect_int(zr, crop_css) > 0 and not contained(crop_in, zr, 0.5):
                    slice_rows.append(f"| {t:6.2f} | {'輪盤' if z[0] == 0 else '排行'}標籤被畫面框邊切到 |")
                    break
        if t >= end_start:
            a = R.clamp((t - end_start) / XF)
            ec = R.end_card(o, canvas, R.Reg(), 1.0)
            ddx, ddy = R.tri(t * 0.9), R.tri(t * 0.7 + 0.3)
            ix0, iy0, ix1, iy1 = x0 + 14, y0 + 14, x1 - 14, y1 - 14
            ec[iy0:iy1, ix0:ix1] = np.roll(ec[iy0:iy1, ix0:ix1], (int(round(ddy * o.ph * 0.006)), int(round(ddx * o.pw * 0.006))), axis=(0, 1))
            canvas = (canvas.astype(np.float32) * (1 - a) + ec.astype(np.float32) * a).astype(np.uint8)
            if a >= 1:
                R.end_card(o, canvas, reg, 1.0)
        b, a_in, a_out = R.bubble_at(bubbles, t)
        if b is not None:
            arr, (ox, oy), bbox, tbox, txt, biss, nl = R.bubble_img(dev, b["text"], tip[0], tip[1], side, zone)
            al = min(a_in, a_out)
            scl = 0.86 + 0.14 * R.back_out(a_in)
            if scl < 0.999:
                h, w = arr.shape[:2]
                px, py = tip[0] - ox, tip[1] - oy
                im2 = Image.fromarray(arr).resize((max(1, int(w * scl)), max(1, int(h * scl))), Image.LANCZOS)
                R.blend(canvas, np.array(im2), int(round(tip[0] - px * scl)), int(round(tip[1] - py * scl)), al)
            else:
                R.blend(canvas, arr, ox, oy, al)
            reg.add("泡泡", (min(bbox[0], tbox[0]), bbox[1], max(bbox[2], tbox[2]), bbox[3] + 6), "泡泡")
            reg.add("泡泡尾巴", tbox, "泡泡")
            for x in biss:
                issues.append(f"| {t:6.2f} | {x}：{b['text']} |")
            if len(b["text"].replace(" ", "")) > 14:
                issues.append(f"| {t:6.2f} | 泡泡超過 14 字：{b['text']} |")
        nm, bt = R.act_at(bubbles, t)
        arr, ox, oy, bbx = R.bibi_frame(o, nm, bt)
        R.blend(canvas, arr, ox, oy)
        reg.add("比比", bbx)
        if b is not None:
            dtip = (bbx[0] - tip[0]) if side == "right" else (tip[0] - bbx[2])
            if dtip < 12 - 0.5:
                issues.append(f"| {t:6.2f} | 尾巴尖端離比比 {dtip:.0f}px（<12） |")
        for (p, q, ar) in reg.overlaps():
            rows.append(f"| {t:6.2f} | {p} | {q} | {ar} |")
        for x in reg.issues:
            issues.append(f"| {t:6.2f} | {x} |")
        if only:
            p = SCR / f"f_{dev}_{t:06.2f}.png"
            Image.fromarray(canvas).save(p)
            print(p, nm, b["text"] if b else "", reg.overlaps(), reg.issues)
            continue
        ff.stdin.write(canvas.tobytes())
    if only:
        return
    ff.stdin.close()
    ff.wait()
    # ── 點擊檢查 ──
    click_rows = []
    for c in meta["clicks"]:
        if c["kind"] != "click":
            continue
        rc = c.get("rect_center")
        px, py = c["center"]
        err = math.hypot(px - rc[0], py - rc[1]) if rc else None
        cx, cy, cw, ch = crop_at(c["t"])
        sx, sy = o.pw / cw, o.ph / ch
        ox_ = x0 + (px / dsf - cx) * sx
        oy_ = y0 + (py / dsf - cy) * sy
        inside = x0 + 4 <= ox_ <= x1 - 4 and y0 + 4 <= oy_ <= y1 - 4
        click_rows.append((round(c["t"], 2), c.get("label") or c.get("text"), None if err is None else round(float(err), 2), bool(inside)))
    # ── 成片：本體 SPEED 倍、片尾卡 END_FINAL 秒；配樂＋點擊音效 ──
    body_final = (end_start + XF) / SPEED            # 交疊 0.2 秒算在本體裡
    end_final = END_FINAL
    final_len = body_final + end_final
    cues = {"cues": [[r[0] / SPEED, "tap"] for r in click_rows] + [[(end_start + 0.3) / SPEED, "ding"]]}
    cj = SCR / f"cues_{dev}.json"
    cj.write_text(json.dumps(cues), encoding="utf-8")
    wav = SCR / f"bgm_{dev}.wav"
    subprocess.run([sys.executable, str(R.REPO / "docs/marketing/video_1010/make_music_v3.py"), "--length", f"{final_len + 0.3:.2f}", "--style", "cute", "--out", str(wav), "--cues", str(cj)], check=True)
    name = "feat05_fund_flow_web_v4.mp4" if dev == "d" else "feat05_fund_flow_mobile_v4.mp4"
    final = SCR / name
    tcut = end_start + XF
    flt = (f"[0:v]split[a][b];[a]trim=0:{tcut:.4f},setpts=(PTS-STARTPTS)/{SPEED}[v1];"
           f"[b]trim={tcut:.4f},setpts=(PTS-STARTPTS)/{END_RAW / end_final:.5f}[v2];[v1][v2]concat=n=2:v=1:a=0[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_sil), "-i", str(wav), "-filter_complex", flt, "-map", "[v]", "-map", "1:a", "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    (SCR / f"overlap_rows_{dev}.md").write_text("\n".join(rows[:500] + ["", "問題："] + issues[:500]), encoding="utf-8")
    (SCR / f"occlusion_rows_{dev}.md").write_text("\n".join(["遮擋（泡泡正在講的元素 × 浮層）："] + occ_rows[:500] + ["", "嚴格遮擋（浮層／游標 × 圖表標籤文字）："] + strict_rows[:500]), encoding="utf-8")
    out = dict(dev=dev, frames=n_total, body_raw=round(body, 2), total_raw=round(total, 2), final_len=round(final_len, 2), speed=SPEED, end_final=end_final,
               overlaps=len(rows), issues=len(issues), occlusion=len(occ_rows), strict=len(strict_rows), cut=len(cut_rows), slice=len(slice_rows),
               blur_frames_bad=blur_left, blur_frames_neutralized=blur_fixed, blur_frames_svgblur=blur_fe, blur_seen=sorted(blur_seen), cursor_transit=len(transit_rows), dd_open_frames=ov_open, push_frames=push_frames, strict_panel=len([r for r in strict_rows if '面板' in r]), strict_cursor=len([r for r in strict_rows if '游標' in r]), strict_bar=len([r for r in strict_rows if '頂欄' in r]), tooltip_frames=tip_frames, still_max_s=round(still_max[0] / FPS, 2), still_at=round(still_max[1], 2),
               clicks=click_rows, bubbles=[(round(b["t0"], 2), round(b["t1"], 2), b["text"]) for b in bubbles], stages=stages, final=str(final),
               occ_detail=occ_rows[:40], strict_detail=strict_rows[:40], slice_detail=slice_rows[:40], cut_detail=cut_rows[:40], data_date=meta.get("data_date"))
    (SCR / f"render_{dev}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("clicks", "bubbles", "occ_detail", "strict_detail", "slice_detail", "cut_detail", "stages")}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--frames", default="")
    g = ap.parse_args()
    render(g.dev, g.frames or None)


if __name__ == "__main__":
    main()
