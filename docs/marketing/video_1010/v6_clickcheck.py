"""第 6 版點擊精準度量測（Andy 10-17「點擊特效需要在精準點」）：用成片實際畫出來的像素量，不信任程式內部座標。

每一次點擊（比比踩下、漣漪出現的那一幀）：
  ① 漣漪中心：同一幀畫兩次（有漣漪／把漣漪關掉），兩張相減取出漣漪圓環，用最小平方法擬合圓心（被比比遮住一部分也擬得出來）。
  ② 元素中心：從錄影原始畫格（點下那一刻）切出被點元素（clicks.json 的外框），縮到成片倍率，在「只有網站畫面」那張圖上做樣板比對，取比對到的外框中心。
  ③ 誤差＝①與②的距離，換算成 1080 基準（網頁 ×1080/1080、手機 ×1080/1080 —— 兩種成片寬或高都是 1080，直接用成片像素）。
  python v6_clickcheck.py --fmt web --out DIR [--only a,b] [--max 0]
輸出：DIR/click_precision_<fmt>.md、.json；每一筆一張對照裁圖（左：成片含漣漪；右：網站畫面＋比對到的元素外框＋漣漪擬合圓心）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv2  # noqa: E402

import render_1010 as B  # noqa: E402
import render_v3 as R  # noqa: E402
import v3_build as VB  # noqa: E402
import v3_core as K  # noqa: E402

FPS = 30


def fit_circle(pts):
    x, y = pts[:, 0].astype(float), pts[:, 1].astype(float)
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0], c[1]
    r = math.sqrt(max(0.0, c[2] + cx * cx + cy * cy))
    return cx, cy, r


def ripple_center(im_on, im_off, guess, rad=150):
    a = np.asarray(im_on.convert("RGB"), dtype=np.int16)
    b = np.asarray(im_off.convert("RGB"), dtype=np.int16)
    d = np.abs(a - b).sum(axis=2)
    gx, gy = int(guess[0]), int(guess[1])
    x0, y0 = max(0, gx - rad), max(0, gy - rad)
    sub = d[y0:gy + rad, x0:gx + rad]
    ys, xs = np.nonzero(sub > 60)
    if len(xs) < 20:
        return None
    pts = np.c_[xs + x0, ys + y0]
    cx, cy, r = fit_circle(pts)
    # 內圈填色也算差異（fill 透明度 1/6）→ 只取外環：離擬合圓心 ≥0.75r 的點再擬一次
    dd = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    ring = pts[dd >= 0.75 * r]
    if len(ring) >= 20:
        cx, cy, r = fit_circle(ring)
    return cx, cy, r, len(pts)


def cursor_hot(im_on, im_off, guess, fmt, rad=140):
    """游標熱點：有游標／沒游標兩張相減。網頁箭頭＝最左上那一點（箭頭尖端）；手機指尖圓＝擬合圓心。"""
    a = np.asarray(im_on, dtype=np.int16)
    b = np.asarray(im_off, dtype=np.int16)
    d = np.abs(a - b).sum(axis=2)
    gx, gy = int(guess[0]), int(guess[1])
    x0, y0 = max(0, gx - rad), max(0, gy - rad)
    sub = d[y0:gy + rad, x0:gx + rad]
    ys, xs = np.nonzero(sub > 60)
    if len(xs) < 10:
        return None
    if fmt == "web":
        k = np.argmin(xs + ys)
        return float(xs[k] + x0), float(ys[k] + y0)
    cx, cy, r = fit_circle(np.c_[xs + x0, ys + y0])
    return cx, cy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    R.set_theme("cute")
    S = VB.shots_for(a.fmt)
    L = K.Lay(a.fmt, "cute")
    out = Path(a.out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    rows = []
    real_ripple, real_rb, real_cur = K.ripple, K.ripple_b, K.tap_cursor
    for s in S:
        if only and s.sid not in only:
            continue
        if not s.op or s.rec is None:
            continue
        taps = list(s.op.taps)
        for i, tp in enumerate(taps):
            t = tp["t"] + 2 / FPS            # 點下後第 2 幀：漣漪已經展開、還很清楚
            if t >= s.dur:
                continue
            hov = tp["hover"]
            on = s.render(t, L).convert("RGB")
            K.ripple_b = lambda *x, **y: None
            K.ripple = lambda *x, **y: None
            no_rip = s.render(t, L).convert("RGB")
            K.tap_cursor = lambda *x, **y: None
            bare = s.render(t, L).convert("RGB")
            K.ripple, K.ripple_b, K.tap_cursor = real_ripple, real_rb, real_cur
            rec = s.rec
            site = R.background(L.fmt).copy()
            rec.draw(site, t, s)
            site = site.convert("RGB")
            guess = rec.map(tp["cx"], tp["cy"])
            rc = None if hov else ripple_center(on, no_rip, guess)
            cur = cursor_hot(no_rip, bare, guess, L.fmt)
            inf = K.click_info(rec.clip, tp["src_t"], tp["x"], tp["y"])
            r = inf["rect"]                 # 來源像素 (x0,y0,x1,y1)
            if hov:
                pr = K._precise_all()
                for key in K._clip_keys(rec.clip):
                    cand = [q for q in pr.get(key, []) if abs(q["t"] - tp["src_t"]) < 0.5 and q.get("rect")]
                    if cand:
                        q = cand[0]["rect"]
                        r = (q[0], q[1], q[0] + q[2], q[1] + q[3])
                        break
            st = K.piecewise(rec.srcmap, t)
            src = B.reader(rec.clip).get(st).convert("RGB")
            ax, ay = rec.map(r[0], r[1])
            bx, by = rec.map(r[2], r[3])
            sc = (bx - ax) / max(1e-6, r[2] - r[0])
            tw, th = int(round(bx - ax)), int(round(by - ay))
            row = {"shot": s.sid, "t": round(t, 2), "kind": "滑過" if hov else "點擊", "clip": rec.clip, "src_t": tp["src_t"], "label": inf["label"] if not hov else "滑過",
                   "center_src": K.PRECISE_SRC.get((rec.clip, round(tp["src_t"], 2)), ""), "expected": [round(guess[0], 1), round(guess[1], 1)]}
            if cur is not None:
                row["cursor"] = [round(float(cur[0]), 1), round(float(cur[1]), 1)]
            if rc is None and cur is None:
                row["err"] = None
                row["why"] = "量不到漣漪與游標（在畫面外）"
                rows.append(row)
                continue
            if rc is None:
                rc = (cur[0], cur[1], 0, 0)
            if not hov:
                row["ripple"] = [round(float(rc[0]), 1), round(float(rc[1]), 1)]
            # 元素樣板比對（外框太大＝整張圖：改切點擊點周圍 80×80 來源像素）
            if (r[2] - r[0]) > 360 or (r[3] - r[1]) > 360:
                cxs, cys = tp["cx"], tp["cy"]
                r = (cxs - 40 / max(sc, 0.2), cys - 40 / max(sc, 0.2), cxs + 40 / max(sc, 0.2), cys + 40 / max(sc, 0.2))
                ax, ay = rec.map(r[0], r[1])
                bx, by = rec.map(r[2], r[3])
                tw, th = int(round(bx - ax)), int(round(by - ay))
                row["tmpl"] = "點擊點周圍"
            crop = src.crop(tuple(int(round(v)) for v in r))
            if tw < 6 or th < 6:
                row["err"] = None
                row["why"] = "元素太小"
                rows.append(row)
                continue
            tmpl = np.asarray(crop.resize((tw, th), Image.LANCZOS))
            pad = 60
            sx0, sy0 = max(0, int(ax) - pad), max(0, int(ay) - pad)
            sx1, sy1 = min(site.width, int(bx) + pad), min(site.height, int(by) + pad)
            area = np.asarray(site)[sy0:sy1, sx0:sx1]
            if area.shape[0] < th or area.shape[1] < tw:
                row["err"] = None
                row["why"] = "元素在畫面外"
                rows.append(row)
                continue
            res = cv2.matchTemplate(cv2.cvtColor(area, cv2.COLOR_RGB2GRAY), cv2.cvtColor(tmpl, cv2.COLOR_RGB2GRAY), cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
            mx0, my0 = sx0 + loc[0], sy0 + loc[1]
            ecx, ecy = mx0 + tw / 2, my0 + th / 2
            # 元素中心（樣板比對到的外框中心；樣板若是點擊點周圍，就是點擊點）
            row["element"] = [round(float(ecx), 1), round(float(ecy), 1)]
            row["match_score"] = round(float(score), 3)
            row["err"] = round(float(math.hypot(rc[0] - ecx, rc[1] - ecy)), 1)
            if cur is not None:
                row["cursor_err"] = round(float(math.hypot(cur[0] - ecx, cur[1] - ecy)), 1)
            row["map_vs_match"] = round(math.hypot(guess[0] - ecx, guess[1] - ecy), 1)
            rows.append(row)
            # 對照裁圖
            cx_, cy_ = int(rc[0]), int(rc[1])
            bb = (cx_ - 160, cy_ - 160, cx_ + 160, cy_ + 160)
            left = on.crop(bb)
            right = site.crop(bb)
            d = ImageDraw.Draw(right)
            d.rectangle([mx0 - bb[0], my0 - bb[1], mx0 - bb[0] + tw, my0 - bb[1] + th], outline=(0, 160, 255), width=2)
            d.line([rc[0] - bb[0] - 10, rc[1] - bb[1], rc[0] - bb[0] + 10, rc[1] - bb[1]], fill=(255, 0, 0), width=2)
            d.line([rc[0] - bb[0], rc[1] - bb[1] - 10, rc[0] - bb[0], rc[1] - bb[1] + 10], fill=(255, 0, 0), width=2)
            sheet = Image.new("RGB", (640, 344), (255, 255, 255))
            sheet.paste(left, (0, 24))
            sheet.paste(right, (320, 24))
            ImageDraw.Draw(sheet).text((4, 4), f"{s.sid} {t:.2f}s err {row['err']}px score {row['match_score']}", fill=(200, 0, 0), font=K.font(K.THEME["pill_font"], 16) if hasattr(K, "font") else None)
            sheet.save(out / "crops" / f"{a.fmt}_{s.sid}_{i}.png")
        for rr in list(B._READERS.values()):
            rr.close()
        B._READERS.clear()
    (out / f"click_precision_{a.fmt}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    ok = [r for r in rows if r.get("err") is not None]
    bad = [r for r in ok if r["err"] > 6 or (r.get("cursor_err") or 0) > 6]
    lines = [f"# 點擊精準度量測（{a.fmt}）", "", f"點擊 {len(rows)} 次；量得到 {len(ok)} 次；誤差 >6px：{len(bad)} 次；最大 {max([r['err'] for r in ok], default=0)}px", "",
             "| 鏡 | 成片秒 | 種類 | 目標 | 漣漪擬合圓心 | 游標熱點 | 元素中心（樣板比對） | 漣漪誤差 px | 游標誤差 px | 比對分數 | 中心來源 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['shot']} | {r['t']} | {r.get('kind', '')} | {str(r['label'])[:24]} | {r.get('ripple', '—')} | {r.get('cursor', '—')} | {r.get('element', '')} | {r.get('err') if r.get('err') is not None else r.get('why')} | {r.get('cursor_err', '—')} | {r.get('match_score', '')} | {r.get('center_src', '')} |")
    (out / f"click_precision_{a.fmt}.md").write_text("\n".join(lines))
    print("\n".join(lines[:4]))


if __name__ == "__main__":
    main()
