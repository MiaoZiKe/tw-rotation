"""功能介紹影片 06／07 共用成片合成（沿用 05 資金流向 v3：單一鏡頭，網站畫面框固定，只允許一次單向推近，不換場、不淡化）。

素材：vidlib3 一口氣錄的網站畫面（<raw>/<dev>_main.mp4＋.json，每格附所有文字外框、浮層外框、游標位置）。
版面：奶油格紙底、左上膠囊＋大標題（跟著主線換字）、中間網站畫面框、比比＋對話泡泡（≤14 字）。
逐幀檢查（成片的每一幀）：
  ① 重疊：膠囊、標題、畫面框、泡泡（含尾巴）、比比兩兩外框相交（外擴 6px）
  ② 遮擋（正在介紹的元素 × 浮層）、嚴格遮擋（浮層／清單／提示框／客服鈕 × 畫面內任何一個字；游標與點擊波紋 × 任何一個字）
  ③ 裁切／切字：被介紹元素整塊在畫面框內；畫面框邊沒有切過任何文字（全部文字一律檢查）
  ④ 泡泡停留、≤14 字、泡泡字出框、尾巴離比比；來源畫面連續不動秒數
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
import renderlib_v3 as R  # noqa: E402

FPS = 30
SPEED = float(os.environ.get("FEAT_SPEED", "1.5"))
END_RAW = 4.5
END_FINAL = float(os.environ.get("FEAT_END_FINAL", "2.0"))
XF = 0.2
BUB_CAP = 7.5
DRIFT_A = float(os.environ.get("FEAT_DRIFT_A", "3.0"))
DRIFT_T = float(os.environ.get("FEAT_DRIFT_T", "2.0"))
DRIFT_CSS = 2.6
PAD = R.PAD
MIN_BUB = float(os.environ.get("FEAT_MIN_BUB", "1.45"))


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


def shifted(a, b, n=6):
    """兩格之間有 n 個以上的文字外框位置改變（動畫中）。"""
    sa = {(round(z[1]), round(z[3])) for z in a}
    return sum(1 for z in b if (round(z[1]), round(z[3])) not in sa) >= n


def build_bubbles(meta, end_start, CFG):
    says = meta["says"]
    bs = []
    for i, s in enumerate(says):
        t0 = s["t"]
        nxt = says[i + 1]["t"] - 0.06 if i + 1 < len(says) else end_start - 0.1
        t1 = min(nxt, t0 + CFG.get('bub_cap', BUB_CAP))
        later = [c for c in meta.get("clears", []) if c > t0 + 0.05]
        if later:
            t1 = min(t1, later[0] - 0.06)
        bs.append(dict(t0=t0, t1=t1, text=s["text"], act=s["act"], focus=s.get("focus", []), sid=f"b{i}"))
    bs.append(dict(t0=end_start + 0.25, t1=end_start + END_RAW, text="謝謝收看，我們下次見", act="face_bow", focus=[], sid="__end"))
    return bs


def render(dev, CFG, only=None):
    SCR = Path(CFG["scr"])
    RAW = SCR / "raw"
    o = layout(dev)
    R.SEC.update(CFG["sec"])
    if dev == "m":
        R.SEC.update(CFG.get("sec_m", {}))
    R.END_SUB = CFG["end_sub"]
    FOCUS_EL = CFG["focus_el"]
    CUT = set(CFG.get("cut", []))
    OCC_SKIP = set(CFG.get("occ_skip", []))   # 容器型元素（整張卡）不拿來比浮層外框；浮層與卡內每個字的相交由「嚴格遮擋」檢查
    meta = json.loads((RAW / f"{dev}_main.json").read_text(encoding="utf-8"))
    src = RAW / f"{dev}_main.mp4"
    fm = meta["fm"]
    N0 = meta["frames"]
    body = N0 / FPS
    end_start = body - XF
    total = end_start + END_RAW + XF
    bubbles = build_bubbles(meta, end_start, CFG)
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
    zc = CFG.get("zoom", {}).get(dev)
    if zc:   # 單向推近：該段第一句泡泡出現前 0.1 秒開始、0.7 秒推完
        tz = next(tt for tt, k_, _ in stages if k_ == zc["stage"])
        zoom = (tz - 0.1, zc.get("dur", 0.7), tuple(zc["tgt"]))

    def crop_at(t):
        if zoom is None or t <= zoom[0]:
            return crop0
        a = R.ease(min(1.0, (t - zoom[0]) / zoom[1]))
        return tuple(c0 + (c1 - c0) * a for c0, c1 in zip(crop0, zoom[2]))

    def stage_at(t):
        n = 1
        for tt, k, _ in stages:
            if tt <= t + 1e-6:
                n = k
        return n

    cap = cv2.VideoCapture(str(src))
    out_sil = SCR / f"{CFG['name']}_{dev}_silent_v3.mp4"
    ff = None
    n_total = int(round(total * FPS))
    sel = [int(round(float(v) * FPS)) for v in only.split(",")] if only else range(n_total)
    if not only:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{o.W}x{o.H}", "-r", str(FPS), "-i", "-",
                               "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out_sil)], stdin=subprocess.PIPE)
    last_k, last_img = -1, None
    rows, issues, occ_rows, strict_rows, cut_rows, slice_rows, slicef_rows = [], [], [], [], [], [], []
    ov_open = tip_frames = push_frames = blur_frames = 0
    cur_rows = []
    still_run, still_max, prev_pv = 0, (0, 0.0), None
    for bb in bubbles:
        if bb["sid"] != "__end" and bb["t1"] - bb["t0"] < MIN_BUB - 1e-3:
            issues.append(f"| {bb['t0']:6.2f} | 泡泡停留 {bb['t1'] - bb['t0']:.2f} 秒（<{MIN_BUB}）：{bb['text']} |")
    click_ts = [c["t"] for c in meta["clicks"] if c["kind"] == "click"]
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
        in_push = zoom is not None and zoom[0] <= t <= zoom[0] + zoom[1] + 0.05
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
            # ── 遮擋／裁切／切字／游標檢查（錄影端每格量到的外框；畫面內＝與畫面框相交）──
            m = fm[k]
            els = m["el"]
            if m.get("blur", 0) > 0:
                blur_frames += 1
            crop_in = (cx + DRIFT_CSS, cy + DRIFT_CSS, cw - 2 * DRIFT_CSS, ch - 2 * DRIFT_CSS)
            bub, a_in, a_out = R.bubble_at(bubbles, t)
            foc = []
            for f in (bub["focus"] if bub else []):
                v = FOCUS_EL.get(f)
                foc += v if isinstance(v, list) else [v]
            foc_r = {f: els[f] for f in foc if f and f in els}
            ovs = [(n_, r_) for n_, *r_ in m["ov"]] + [("客服鈕", f) for f in m["fab"]]
            ovs = [(n_, r_) for n_, r_ in ovs if rect_int(r_, crop_css) > 0]
            if any(n_.startswith("浮層") for n_, _ in ovs):
                ov_open += 1
            if any(n_ == "圖表提示框" for n_, _ in ovs):
                tip_frames += 1
            moving = k > 0 and (fm[k - 1].get('sy') != m.get('sy') or fm[k - 1]['el'].get('drawer') != els.get('drawer') or shifted(fm[k - 1]['zt'], m['zt']) or any(k + j < N0 and (fm[k + j].get('sy') != m.get('sy') or shifted(m['zt'], fm[k + j]['zt'])) for j in (1, 2, 3, 4)))   # 頁面正在捲動、抽屜／選單正在滑動（多個字同時位移）的幀不算裁切／切字
            for f, fr_ in foc_r.items():
                if not in_push and not moving and not any(k + j < N0 and fm[k + j].get('sy') != m.get('sy') for j in range(1, 14)) and f in CUT and rect_int(fr_, crop_css) > 0 and not contained(crop_in, fr_, 0.5):
                    cut_rows.append(f"| {t:6.2f} | {f} 超出畫面框 |")
                for n_, r_ in ovs:
                    if f not in OCC_SKIP and rect_int(fr_, r_) > 0:
                        occ_rows.append(f"| {t:6.2f} | 「{bub['text']}」介紹的 {f} | {n_} | {int(rect_int(fr_, r_))} |")
            zt = [z for z in m["zt"] if rect_int(z[1:5], crop_css) > 0]
            for n_, r_ in ovs:
                for z in zt:
                    if z[5]:   # 浮層自己的字不算
                        continue
                    if rect_int(z[1:5], r_) > 0:
                        strict_rows.append(f"| {t:6.2f} | {n_} 蓋住文字 |")
                        break
            # 游標／點擊波紋：網頁＝游標可見時畫箭頭；手機＝手指只在點擊那一刻畫細圈
            cxy = m.get("cur")
            if dev == "m":   # 手機：手指細圈只在點擊那一刻畫在「點擊落點」上
                cl = [c_ for c_ in meta["clicks"] if c_["kind"] == "click" and -0.2 <= t - c_["t"] <= 0.12]
                cxy = cl[0]["css_point"] if cl else None
            if cxy and rect_int((cxy[0] - 12, cxy[1] - 12, 40, 44), crop_css) > 0:
                ring = any(-0.05 <= t - ct <= 0.65 for ct in click_ts)
                rr = 7
                arrow = dev == "d" and m.get("cop", 1) >= 0.25
                if dev == "m":
                    ring, rr = any(-0.17 <= t - ct <= 0.01 for ct in click_ts), 7
                for z in zt:
                    tx, ty, tw, th = z[1:5]
                    dx = max(tx - cxy[0], 0, cxy[0] - (tx + tw))
                    dy = max(ty - cxy[1], 0, cxy[1] - (ty + th))
                    if (ring and (dx * dx + dy * dy) ** 0.5 < rr - 1.5) or (arrow and rect_int((cxy[0], cxy[1], 18, 26), z[1:5]) > 0):
                        cur_rows.append(f"| {t:6.2f} | 游標／波紋壓字 |")
                        break
            # 游標（等候時）壓到可操作元件（按鈕／輸入框／下拉／連結）：點擊前後（-1.0～+0.4 秒）游標本來就在那個元件上，不算
            if cxy and not any(-1.0 <= t - ct <= 0.4 for ct in click_ts) and (dev == "d" and m.get("cop", 1) >= 0.25):
                for u in m.get("ui", []):
                    if rect_int(u[:4], crop_css) > 0 and rect_int((cxy[0], cxy[1], 18, 26), u[:4]) > 0:
                        cur_rows.append(f"| {t:6.2f} | 游標壓到控制項（x={u[0]:.0f},y={u[1]:.0f},w={u[2]:.0f}） |")
                        break
            # 畫面框邊切到文字：畫面內所有文字（嚴格）；另分「正在介紹的元素內的文字」
            if not in_push and not in_end and not moving:
                foc_rects = list(foc_r.values())
                dr = els.get("drawer")
                if dr:
                    foc_rects.append(dr)
                for z in zt:
                    zr = z[1:5]
                    if rect_int(zr, crop_css) > 0 and not contained(crop_in, zr, 0.5):
                        slice_rows.append(f"| {t:6.2f} | 畫面框邊切到文字（{z[0]}）x={zr[0]:.0f} y={zr[1]:.0f} w={zr[2]:.0f} |")
                        if any(rect_int(zr, fr2) > 0 for fr2 in foc_rects):
                            slicef_rows.append(slice_rows[-1])
                        break
            if in_push:
                push_frames += 1
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
        click_rows.append((round(c["t"], 2), c.get("label") or c.get("text"), None if err is None else round(float(err), 2), bool(inside), c.get("hit_expected"), c.get("cur_overlap")))
    body_final = (end_start + XF) / SPEED
    end_final = END_FINAL
    final_len = body_final + end_final
    cues = {"cues": [[r[0] / SPEED, "tap"] for r in click_rows] + [[(end_start + 0.3) / SPEED, "ding"]]}
    cj = SCR / f"cues_{dev}.json"
    cj.write_text(json.dumps(cues), encoding="utf-8")
    wav = SCR / f"bgm_{dev}.wav"
    subprocess.run([sys.executable, str(R.REPO / "docs/marketing/video_1010/make_music_v3.py"), "--length", f"{final_len + 0.3:.2f}", "--style", "cute", "--out", str(wav), "--cues", str(cj)], check=True)
    final = SCR / (CFG["out_web"] if dev == "d" else CFG["out_mobile"])
    tcut = end_start + XF
    flt = (f"[0:v]split[a][b];[a]trim=0:{tcut:.4f},setpts=(PTS-STARTPTS)/{SPEED}[v1];"
           f"[b]trim={tcut:.4f},setpts=(PTS-STARTPTS)/{END_RAW / end_final:.5f}[v2];[v1][v2]concat=n=2:v=1:a=0[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_sil), "-i", str(wav), "-filter_complex", flt, "-map", "[v]", "-map", "1:a", "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    (SCR / f"overlap_rows_{dev}.md").write_text("\n".join(rows[:500] + ["", "問題："] + issues[:500]), encoding="utf-8")
    (SCR / f"occlusion_rows_{dev}.md").write_text("\n".join(["遮擋（泡泡正在講的元素 × 浮層）："] + occ_rows[:500] + ["", "嚴格遮擋（浮層／清單／提示框／客服鈕 × 文字）："] + strict_rows[:500]
                                                          + ["", "游標／波紋 × 文字："] + cur_rows[:500] + ["", "畫面框邊切到文字（全部）："] + slice_rows[:500] + ["", "裁切（介紹的元素超出畫面框）："] + cut_rows[:200]), encoding="utf-8")
    out = dict(dev=dev, frames=n_total, body_raw=round(body, 2), total_raw=round(total, 2), final_len=round(final_len, 2), speed=SPEED, end_final=end_final,
               overlaps=len(rows), issues=len(issues), occlusion=len(occ_rows), strict=len(strict_rows), cursor_text=len(cur_rows), cut=len(cut_rows), slice=len(slice_rows), slice_focus=len(slicef_rows),
               blur_frames=blur_frames, dd_open_frames=ov_open, push_frames=push_frames, tooltip_frames=tip_frames, still_max_s=round(still_max[0] / FPS, 2), still_at=round(still_max[1], 2),
               clicks=click_rows, bubbles=[(round(b["t0"], 2), round(b["t1"], 2), b["text"]) for b in bubbles], stages=stages, final=str(final),
               occ_detail=occ_rows[:40], strict_detail=strict_rows[:40], cursor_detail=cur_rows[:40], slice_detail=slice_rows[:60], cut_detail=cut_rows[:40], data_date=meta.get("data_date"), warns=meta.get("warns"))
    (SCR / f"render_{dev}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("clicks", "bubbles", "occ_detail", "strict_detail", "slice_detail", "cut_detail", "cursor_detail", "stages")}, ensure_ascii=False))


def main(CFG):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--frames", default="")
    g = ap.parse_args()
    render(g.dev, CFG, g.frames or None)
