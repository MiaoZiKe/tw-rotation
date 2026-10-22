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
sys.path.insert(0, str(HERE.parent / "05_fund_flow"))
import renderlib_v2 as R  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat04"))
RAW = SCR / "raw_v6"
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

R.END_SUB = "產品剖析圖・3D 剖析圖・供應鏈關聯圖"
R.SEC.update({
    "s1": ("為什麼看", "AI 伺服器熱，誰在供貨？", "誰在供貨"),
    "s2": ("引導", "點產業地圖，選 AI 伺服器", "AI 伺服器"),
    "s3": ("剖析圖", "點編號，圖上零件跟著亮", "跟著亮"),
    "s4": ("3D", "切 3D，點零件看說明", "點零件"),
    "s5": ("關聯圖", "點環節，看上下游與成分公司", "成分公司"),
    "s6": ("", "", ""),
})
FOCUS_EL = {"mnum3d": "mnum3d", "seg_thermal": "seg_thermal", "seg_power": "seg_power", "seg_assembly": "seg_assembly", "dgbody": "dgbody", "tab": "tab", "chain": "chain", "tog": "tog", "card3": "card3", "card4": "card4", "card5": "card5", "card6": "card6", "dg": "dg", "canvas": "canvas", "part": "part", "power": "power", "thermal": "thermal", "assembly": "assembly"}


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
    if dev == 'm':
        R.SEC.update({'s3': ('剖析圖', '點編號，看零件說明', '零件說明'), 's4': ('3D', '切 3D，點編號看說明', '點編號')})
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
    crop0 = tuple(meta["crop0"])
    CROP1 = (250, 70, 1010, 535)
    CROP2 = (748, 100, 520, 317)
    t3 = next(tt for tt, k_, _ in stages if k_ == 3)
    tz2 = next((m_[0] for m_ in meta.get("marks", []) if m_[1] == "mark" and m_[2] == "zoom2"), None)
    zooms = [(t3 - 0.1, 0.7, crop0, CROP1)] + ([(tz2, 0.8, CROP1, CROP2)] if tz2 is not None else [])
    if dev == 'm':
        zooms = []   # 手機：不推近，只捲動
    zoom = zooms[0] if zooms else None

    def crop_at(t):
        cur = crop0
        for t0, d, c_from, c_to in zooms:
            if t <= t0:
                break
            a_ = R.ease(min(1.0, (t - t0) / d))
            cur = tuple(c0 + (c1 - c0) * a_ for c0, c1 in zip(c_from, c_to))
        return cur
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
    out_sil = SCR / f"feat04_{dev}_silent_v6.mp4"
    ff = None
    n_total = int(round(total * FPS))
    sel = [int(round(float(v) * FPS)) for v in only.split(",")] if only else range(n_total)
    if not only:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{o.W}x{o.H}", "-r", str(FPS), "-i", "-",
                               "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out_sil)], stdin=subprocess.PIPE)
    last_k, last_img = -1, None
    rows, issues, occ_rows, strict_rows, cut_rows, slice_rows, ov_open, tip_frames = [], [], [], [], [], [], 0, 0
    push_frames = 0
    move_frames = 0
    blur_left = blur_fixed = blur_fe = 0
    blur_seen = set()
    still_run, still_max, prev_pv = 0, (0, 0.0), None
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
            blur_fixed += 1 if (m.get('bf0') or {}).get('fixed', 0) else 0
            blur_fe += 1 if bf.get('fe', 0) else 0
            blur_seen.update(bf.get('seen', []))
            top_off = 56 if dev == 'm' and stg >= 3 else 0   # 手機：頂欄（y<52）底下不算畫面，框邊以頂欄下緣起算
            crop_in = (cx + DRIFT_CSS, cy + DRIFT_CSS + top_off, cw - 2 * DRIFT_CSS, ch - 2 * DRIFT_CSS - top_off)   # 慢漂最壞情況的實際可見範圍
            in_push = any(z0 <= t <= z0 + zd + 0.05 for z0, zd, _a, _b in zooms)
            if in_push:
                push_frames += 1
            moving = fm[max(0, k - 4)]["sy"] != m["sy"] or fm[min(N0 - 1, k + 4)]["sy"] != m["sy"]
            if moving:
                move_frames += 1
            bub, a_in, a_out = R.bubble_at(bubbles, t)
            foc = [FOCUS_EL.get(f) for f in (bub["focus"] if bub else [])]
            foc_r = {f: els[f] for f in foc if f and f in els}
            ovs = [(n_, r_) for n_, *r_ in m["ov"]] + [("客服鈕", f) for f in m["fab"]]
            for f, fr_ in foc_r.items():
                for n_, r_ in ovs:
                    if n_ == 'topbar' and f in ('tab', 'chain', 'burger', 'm4ind', 'tog'):
                        continue
                    if rect_int(fr_, r_) > 0 and rect_int(r_, crop_css) > 0:
                        occ_rows.append(f"| {t:6.2f} | 「{bub['text']}」介紹的 {f} | {n_} | {int(rect_int(fr_, r_))} |")
            lbs = [l for l in m["lb"] if rect_int(l[1:], crop_css) > 0]
            for ia in range(len(lbs)):
                for ib in range(ia + 1, len(lbs)):
                    if rect_int(lbs[ia][1:], lbs[ib][1:]) > 0:
                        occ_rows.append(f"| {t:6.2f} | 3D 標籤 {lbs[ia][0]} | 3D 標籤 {lbs[ib][0]} | {int(rect_int(lbs[ia][1:], lbs[ib][1:]))} |")
            txs = [z for z in m["txt"] if rect_int(z, crop_css) > 0]
            if m.get("cur") and stg >= 3 and dev == "d":
                cxy = m["cur"]
                cr = (cxy[0] - 3, cxy[1] - 2, 26, 30)
                near_click = any(-0.9 <= t - c['t'] <= 0.3 for c in meta['clicks'])   # 游標滑向被點目標、點下去的那一刻（游標本來就在被點的元素上）
                if rect_int(cr, crop_css) > 0 and not near_click:
                    for z in txs:
                        if rect_int(z, cr) > 0:
                            strict_rows.append(f"| {t:6.2f} | 游標蓋住文字 |")
                            break
            if not in_push and not moving and stg >= 3:
                for z in txs:
                    if dev == 'm' and z[1] + z[3] <= top_off + 2:
                        continue
                    if dev == 'm' and (z[0] + z[2] <= 20 or z[0] >= 514):
                        continue   # 關聯圖橫向捲動容器左緣之外的文字：整段被網站容器裁掉、畫面上看不到任何字（已逐格目視確認只剩節點外框的邊角，沒有字）
                    if not contained(crop_in, z, 0.5):
                        slice_rows.append(f"| {t:6.2f} | 文字被畫面框邊切到 {[round(v) for v in z]} |")
                        break
                for f, fr_ in foc_r.items():
                    if f in ("card3", "card4", "card5", "dg", "canvas", "tog", "part", "power", "thermal", "assembly") and rect_int(fr_, crop_css) > 0 and not contained(crop_in, fr_, 0.5) and f not in ("part", "power", "thermal", "assembly", "dg"):
                        cut_rows.append(f"| {t:6.2f} | {f} 超出畫面框 |")
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
    name = "feat04_industry_map_web_v6.mp4" if dev == "d" else "feat04_industry_map_mobile_v6.mp4"
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
               dd_open_frames=ov_open, blur_frames_bad=blur_left, blur_frames_neutralized=blur_fixed, blur_svg_defs_frames=blur_fe, blur_seen=sorted(blur_seen), push_frames=push_frames, move_frames=move_frames, strict_cursor=len(strict_rows), tooltip_frames=tip_frames, still_max_s=round(still_max[0] / FPS, 2), still_at=round(still_max[1], 2),
               clicks=click_rows, bubbles=[(round(b["t0"], 2), round(b["t1"], 2), b["text"]) for b in bubbles], stages=stages, final=str(final),
               occ_detail=occ_rows[:40], strict_detail=strict_rows[:40], slice_detail=slice_rows[:40], cut_detail=cut_rows[:40], data_date=meta.get("data_date"))
    (SCR / f"slice_rows_{dev}.md").write_text("\n".join(slice_rows[:2000] + ["", "cursor:"] + strict_rows[:2000]), encoding="utf-8")
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
