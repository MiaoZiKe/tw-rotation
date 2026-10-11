"""第 3 版合成核心（重疊修正版）：版面、錄影層、焦點框、比比操作員、鏡頭、逐幀檢查掛鉤。

規則（layout_rules.md）：任何元素外框不可重疊 → 每個元素登記外框（v3_check.reg），渲染時逐幀檢查。
- 網頁版：錄影縮在中央（上下左右留帶），標題／字幕／備註在上下帶內，比比站左右側帶；全部不壓網站畫面。
- 手機版：框寬 1000×高 1480 置中，標題在框上方，框下方窄帶放比比＋台詞＋備註；內容比框高就「慢慢往下滑」。
- 點擊：漣漪與比比落點一律由「來源座標 → 當下推近／平移矩陣」算出，並驗證落在目標元素 rect 內（click_check.md）。
- 焦點框：目標 rect 外擴 10px、圓角 10、線寬 4；外光與壓暗只在框外（focus_check.md）。
- 不遮蓋、不淡化網站任何畫面（Andy 10-11：「不用特別遮住」）。
"""
from __future__ import annotations

import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B  # noqa: E402
import render_v3 as R  # noqa: E402
import v3_check as C  # noqa: E402
from render_1010 import (CREAM, DEEP, INK, LEMON, SKY, WHITE, F_BOLD, F_MED, FPS, anim_frame, back_out, clamp,  # noqa: E402
                         ease_io, ease_out, font, lerp, logo_sized, piecewise, put_sprite, reader, rounded_mask,
                         text_w, wrap_lines)

THEME = R.THEME
RAW3 = B.SCR / "video1010" / "raw_v3"
ROLE = ["bibi"]                     # 目前比比的角色：bibi／bibi_tap（踩按鈕整段，與網站畫面重疊記為例外）
CLICKS: list = []                   # 點擊檢查紀錄
FOCUSES: list = []                  # 焦點框檢查紀錄
CROPS: list = []                    # 裁切／置中檢查紀錄
EXPAND_FOCUS = 10


# ───────────────────────── 比比外框登記 ─────────────────────────
SPR_DRAWN: list = []    # 這一幀畫過的比比素材：(名稱, 格, 腳底, 大小, 角色)——忙碌圖逐像素檢查用


def _sprite_hook(name, i, foot, size):
    info = B.bibi_index().get(name)
    if not info:
        return
    path = info["frames"][min(i, len(info["frames"]) - 1)]
    C.reg("bibi:" + name, C.sprite_rect(path, foot, size), role=ROLE[0], group="bibi")
    SPR_DRAWN.append((name, min(i, len(info["frames"]) - 1), tuple(foot), size, ROLE[0]))


B.SPRITE_HOOK = _sprite_hook


@lru_cache(maxsize=256)
def union512(name):
    """整段動畫所有格外框的聯集（512 座標）。"""
    info = B.bibi_index()[name]
    bs = [C._bbox512(p) for p in info["frames"]]
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def max_bbox_w(name):
    u = union512(name)
    return u[2] - u[0]


def fit_size(name, max_w, cap=240):
    """讓動畫所有格外框聯集寬度 ≤ max_w 的最大 size（≤cap）。"""
    return int(min(cap, max_w * 512 / max_bbox_w(name)) // 4 * 4)


def fit_box(name, max_w, max_h, cap=300):
    """動畫所有格外框聯集同時 ≤ max_w × max_h 的最大 size。"""
    u = union512(name)
    return int(min(cap, max_w * 512 / max(1, u[2] - u[0]), max_h * 512 / max(1, u[3] - u[1])) // 4 * 4)


def side_foot(name, size, cx, bottom):
    """把動畫外框聯集的水平中心放在 cx、底邊放在 bottom 的腳底座標。"""
    u = union512(name)
    s = size / 512
    return (cx - ((u[0] + u[2]) / 2 - 248) * s, bottom - (u[3] - 482) * s)


PRO_THINK = {"face_think", "talk_explain", "magnifier", "calc", "hourglass", "spotlight", "pointer_r", "pointer_l", "face_thinking_bulb", "bulb"}
PRO_NOD = {"face_nod", "face_proud", "talk_excited", "face_star", "face_love", "face_thumbs", "face_clap", "celebrate", "trophy", "growth", "star_save"}


def pro_idle(name):
    """專業版比比只用 3 種收斂表情。"""
    if name in PRO_THINK:
        return "face_think"
    if name in PRO_NOD:
        return "face_nod"
    return "talk_happy"


# ───────────────────────── 版面 ─────────────────────────
import os as _os
V4 = _os.environ.get("VIDEO_V") == "4"


class Lay:
    def __init__(self, fmt, theme="cute"):
        self.fmt, self.theme = fmt, theme
        self.full_bleed = False
        if fmt == "web":
            self.W, self.H = 1920, 1080
            self.box = (77, 66, 1766, 770)               # 網站畫面框：寬 92%（1766）×高 770，下方 244px 留給比比與泡泡
            self.frame_y = self.box[1]
            self.head_px = 36
            self.head_w = 900
            self.sub_px = 28
            self.sub_chars = 52
            self.pill_px = 18
            self.pill_xy = (77, 4)
            self.head_y = 6
            self.sub_y = 988
            self.foot_y = 1048
            self.host_x = 150
            self.host_foot = 1076
            self.host_w = 260
            self.host_h = 214
            self.host_size = 300
            if V4:
                # 第 4 版（Andy：「網站畫面約佔 92% 寬，比比放大…重點是圖表一定要都被看到」）：網站框 1766 寬滿高；
                # 比比與泡泡疊在網站左側導覽欄（不是重點內容），位置逐鏡避開重點框／內容框／點擊目標（site_overlay_check）
                self.box = (77, 58, 1766, 993)
                self.frame_y = 58
                self.host_x = 210
                self.host_foot = 1040
                self.host_w = 236
                self.host_h = 214
                self.foot_y = 1052
        else:
            self.W, self.H = 1080, 1920
            self.box = (40, 146, 1000, 1480)             # 網站畫面框（寬 1000×高 1480）
            self.frame_y, self.frame_h = 146, 1480
            self.head_px = 50
            self.head_w = 820
            self.pill_px = 22
            self.pill_xy = (40, 34)
            self.head_y = 30
            self.foot_y = 1874
            self.host_size = 300
            self.host_x = 136
            self.host_foot = 1862
            self.host_w = 236
            self.host_h = 222
            if V4:
                # 第 4 版（CEO 10-12）：Reels 底部約 320px、右側約 140px 是 App 介面區，泡泡與小字一律放上方安全區；
                # 版面由上而下＝標題（y 20～100）→ 小字（y 104～132）→ 比比＋泡泡（y 146～368）→ 網站框 1000×1480（y 424～1904）
                self.box = (40, 424, 1000, 1480)
                self.frame_y, self.frame_h = 424, 1480
                self.head_w = 700
                self.pill_xy = (40, 24)
                self.head_y = 18
                self.foot_y = 104
                self.host_x = 140
                self.host_foot = 368
                self.safe_x1 = 940

    @property
    def host(self):
        return (self.host_x, self.host_foot)

    @property
    def host_size_(self):
        return self.host_size if self.fmt == "mobile" else 230


# ───────────────────────── 目標載入（錄影端 JSON；沒有就用分鏡估值並標註） ─────────────────────────
@lru_cache(maxsize=1)
def load_all():
    """合併錄影端產出：coords_*.json（逐素材 targets／focus）、click_targets.json、focus_targets.json。"""
    out = {}
    for p in sorted(RAW3.glob("coords_*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        for clip, v in d.items():
            if isinstance(v, dict):
                e = out.setdefault(clip, {"targets": [], "focus": []})
                e["targets"] += v.get("targets") or []
                e["focus"] += v.get("focus") or []
    for nm, key in (("click_targets.json", "targets"), ("focus_targets.json", "focus")):
        p = RAW3 / nm
        if p.exists():
            try:
                d = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(d, dict):
                for clip, v in d.items():
                    if isinstance(v, dict) and key in v:
                        out.setdefault(clip, {"targets": [], "focus": []})[key] += v[key]
                    elif isinstance(v, list):
                        out.setdefault(clip, {"targets": [], "focus": []})[key] += v
    return out


def _xywh(r):
    return (r[0], r[1], r[0] + r[2], r[1] + r[3])


def _clip_keys(clip):
    base = clip.replace("_v3b", "").replace("_v3c", "")
    if "_nofab" in clip:          # 藏客服鈕重錄版：錄影端沒另外寫的資料就沿用原檔（流程與座標照舊）
        orig = clip.replace("_nofab", "")
        return [clip, orig, orig.replace("_v3b", "").replace("_v3c", "")]
    return [clip, base]


def click_target(clip, t_src, x, y):
    """(rect, label, 來源)：錄影端 DOM 量出的目標元素外框；沒有就以點擊座標 ±45px 當估值（並在報告標註）。"""
    allj = load_all()
    for key in _clip_keys(clip):
        best = None
        for it in (allj.get(key) or {}).get("targets", []):
            if it.get("kind", "click") != "click" or "video_rect" not in it:
                continue
            dt = abs(float(it["t"]) - t_src)
            if dt < 0.5 and (best is None or dt < best[0]):
                best = (dt, _xywh(it["video_rect"]), it.get("label", ""), it.get("hit_expected", None))
        if best:
            h = best[3]
            tag = "；hit_expected=True（最上層元素驗證過）" if h is True else ("；hit_expected=False（最上層不是目標）" if h is False else "；未驗 hit_expected（舊錄影，以 DOM rect 驗落點）")
            return best[1], best[2], "錄影端 DOM（click_targets）" + tag
    return (x - 45, y - 45, x + 45, y + 45), "", "座標估值±45px（錄影端尚未提供該素材）"


def click_info(clip, t_src, x, y):
    """點擊目標資訊：hit 矩形（有方塊就用方塊，否則元素外框）、中心（錄影端量到的點擊中心，沒有就用事件座標）、標籤、來源、hit_expected。"""
    allj = load_all()
    for key in _clip_keys(clip):
        best = None
        for it in (allj.get(key) or {}).get("targets", []):
            if it.get("kind", "click") != "click" or "video_rect" not in it:
                continue
            dt = abs(float(it["t"]) - t_src)
            if dt < 0.5 and (best is None or dt < best[0]):
                best = (dt, it)
        if best:
            it = best[1]
            rect = _xywh(it["block_video_rect"]) if it.get("block_video_rect") else _xywh(it["video_rect"])
            ctr = tuple(it["center"]) if it.get("center") else (x, y)
            h = it.get("hit_expected", None)
            tag = "hit_expected=True" if h is True else ("hit_expected=False" if h is False else "舊錄影（DOM rect 驗證）")
            return {"rect": rect, "center": ctr, "label": it.get("label", "") + (("・" + it["block"]) if it.get("block") else ""), "src": tag, "hit": h}
    return {"rect": (x - 45, y - 45, x + 45, y + 45), "center": (x, y), "label": "", "src": "座標估值±45px", "hit": None}


SITEOV: list = []       # site_overlay_check：(鏡, 秒, 疊加元素, 被壓到的重點, 相交面積)
ZOOMCHK: list = []      # (鏡, 素材, 輸出像素／來源像素；>1 ＝放大超過原解析度)
CONTENTCHK: list = []   # (鏡, 點擊目標, 內容區標籤, 入框%(點擊後 1.5 秒), 停留秒, 來源, 備註)


def post_click_content(clip, src_t, cy_src=None, desktop=False):
    """點擊後「被點出的內容區」：取錄影端 focus_targets 中、點擊之後 4.6 秒內最早出現的內容區（排除控制列）；沒標就推定為點擊目標下方（手機）。"""
    allj = load_all()
    best = None
    for key in _clip_keys(clip):
        for it in (allj.get(key) or {}).get("focus", []):
            if "video_rect" not in it or "t_start" not in it:
                continue
            ts = float(it["t_start"])
            lab = str(it.get("label", ""))
            if not (src_t - 0.05 <= ts <= src_t + 4.6):
                continue
            if any(k in lab for k in ("搜尋", "分頁列", "切換列", "結論一行", "指標選單")):
                continue
            r = _xywh(it["video_rect"])
            if r[1] < 0 or r[3] - r[1] < 60:
                continue
            if best is None or ts < best[0]:
                best = (ts, r, lab)
    if best:
        return best[1], best[2], "錄影端 focus_targets"
    if desktop or cy_src is None:
        return None, "", ""
    return (24, cy_src + 60, 1146, cy_src + 60 + 1500), "點擊目標下方內容", "推定（錄影端未標內容區）"


def plan_mobile(rec, op, D, L):
    """手機：點擊後把「被點出的內容區」放進視窗（點下→內容出現並入框→停留≥1.5 秒；內容比視窗高就慢慢滑到底並停 1.2 秒）。
    回傳 (pan_keys, 檢查列, 最短鏡長)。"""
    sw, sh = clip_size(rec.clip)
    rx, ry, rw, rh = L.box
    wh = rh * sw / rw
    maxy = max(0.0, sh - wh)
    SPEED = 700.0       # 手機可讀捲動速度（src px／秒）

    def cl(y):
        return min(max(y, 0.0), maxy)
    taps = [tp for tp in op.taps if not tp["hover"]]
    if not taps:
        return None, [], 0.0
    items = []
    meta_all = getattr(rec, "meta", {}) or {}
    for tp in taps:
        mt = meta_all.get(round(tp["src_t"], 2))
        if mt:
            rect, lab, src, arr = mt["rect"], mt["label"], "錄影端 click_targets.content_rect", mt["vis_local"]
        else:
            rect, lab, src = post_click_content(rec.clip, tp["src_t"], tp["cy"])
            arr = tp["t"] + 0.95
        rect = _clip_rect(rect, sw, sh)
        h = rect[3] - rect[1]
        w_c = cl(rect[1] - (160 if h <= wh - 200 else 100))
        cy = tp["cy"]
        w_t = None if (w_c + 40 <= cy <= w_c + wh - 40) else cl(cy - wh * 0.3)
        items.append({"c": tp["t"], "arr": arr, "rect": rect, "lab": lab, "src": src, "w_c": w_c, "w_t": w_t, "tp": tp})
    keys = []
    first = items[0]
    keys.append((0.0, first["w_t"] if first["w_t"] is not None else first["w_c"]))
    for k, it in enumerate(items):
        c, arr = it["c"], it["arr"]
        if it["w_t"] is not None:
            keys.append((c + 0.25, it["w_t"]))
        keys.append((arr, it["w_c"]))
        nxt = items[k + 1] if k + 1 < len(items) else None
        if nxt:
            tgt = nxt["w_t"] if nxt["w_t"] is not None else nxt["w_c"]
            if abs(tgt - it["w_c"]) > 1:
                keys.append((max(arr + 0.1, nxt["c"] - 0.7), it["w_c"]))
                keys.append((nxt["c"] - 0.1, tgt))
    last = items[-1]
    h = last["rect"][3] - last["rect"][1]
    dmin = last["arr"] + 1.5
    reached = True
    if h > wh - 200 and not getattr(rec, "top_only", False):
        y_end = cl(last["rect"][3] - wh + 40)
        dist = max(0.0, y_end - last["w_c"])
        tscroll = max(0.8, dist / SPEED)
        keys.append((last["arr"] + 0.8, last["w_c"]))
        keys.append((last["arr"] + 0.8 + tscroll, y_end))
        dmin = last["arr"] + 0.8 + tscroll + 1.2
    out = []
    for t_, y_ in sorted(keys, key=lambda x: x[0]):
        if out and t_ <= out[-1][0] + 1e-3:
            out[-1] = (out[-1][0], y_)
        else:
            out.append((t_, y_))

    def win_at(tt):
        if tt <= out[0][0]:
            return out[0][1]
        for (t0, y0), (t1, y1) in zip(out, out[1:]):
            if t0 <= tt <= t1:
                return y0 + (y1 - y0) * ease_io((tt - t0) / max(1e-3, t1 - t0))
        return out[-1][1]
    chk = []
    for k_, it in enumerate(items):
        c = it["c"]
        r = it["rect"]
        top = (r[0], r[1], r[2], min(r[3], r[1] + wh - 120))
        t_chk = it["arr"] + 0.1
        if k_ + 1 < len(items):
            t_chk = min(t_chk, max(c + 0.5, items[k_ + 1]["c"] - 0.75))
        w15 = win_at(t_chk)
        inc = _area(_inter_rect(top, (0, w15, sw, w15 + wh))) / max(1.0, _area(top))
        note = ("內容高於視窗：只看上段重點圖表（Andy 退件：每分頁一個重點，不再滑到底）" if getattr(rec, "top_only", False) else "內容高於視窗：取上段並慢滑到底") if r[3] - r[1] > wh - 200 else ""
        chk.append((it["lab"], round(inc * 100, 1), it["src"], note, it["tp"], r))
    return out, chk, dmin


def content_info(clip, t_src):
    """click_targets 裡錄影端量到的「點擊後內容區」：回傳 dict(rect, label, vis=(t0,t1)) 或 None。"""
    allj = load_all()
    for key in _clip_keys(clip):
        best = None
        for it in (allj.get(key) or {}).get("targets", []):
            if it.get("kind", "click") != "click" or not it.get("content_rect") or not it.get("content_visible_t"):
                continue
            dt = abs(float(it["t"]) - t_src)
            if dt < 0.6 and (best is None or dt < best[0]):
                best = (dt, it)
        if best:
            it = best[1]
            return {"rect": _xywh(it["content_rect"]), "label": it.get("content_label", ""), "vis": tuple(it["content_visible_t"])}
    return None


def auto_map(clip, win, hold=1.6, ff=3.0, lead=0.6, tail=0.6):
    """依錄影端的點擊內容資訊自動排素材時間軸：點下前 lead 秒原速 → 點下後 tail 秒原速 → 快轉（ff 倍）到內容完整入框 → 原速停 hold 秒。
    回傳 (srcmap, D, meta)；meta[src_t] = {"vis_local": 內容入框的鏡內秒, "rect", "label"}。"""
    evs = [e for e in events_for(clip) if e["kind"] == "tap" and win[0] <= e["t"] <= win[1]]
    pts = []
    state = {"loc": 0.0, "src": None}
    meta = {}

    def add(src_to, speed):
        if state["src"] is None:
            state["src"] = src_to
            pts.append((0.0, src_to))
            return
        dur = max(0.05, (src_to - state["src"]) / speed)
        state["loc"] += dur
        state["src"] = src_to
        pts.append((state["loc"], src_to))
    first = True
    for e in evs:
        a = e["t"] - (lead if first else 0.5)
        if first:
            add(max(0.0, a), 1.0)
            first = False
        elif a > state["src"] + 0.05:
            add(a, ff)
        add(e["t"] + tail, 1.0)
        info = content_info(clip, e["t"])
        if info:
            v0, v1 = info["vis"]
            if v0 > state["src"] + 0.1:
                add(v0, ff)
            meta[round(e["t"], 2)] = {"vis_local": state["loc"], "rect": info["rect"], "label": info["label"]}
            add(min(v0 + hold, clip_dur(clip) - 0.05), 1.0)
        else:
            add(min(e["t"] + tail + 1.0, clip_dur(clip) - 0.05), 1.0)
    return pts, state["loc"], meta


def seq_map(segs):
    """連續點擊序列的時間軸：segs＝[(src_a, src_b, speed), ...]；回傳 (srcmap, D)。"""
    pts = []
    loc = 0.0
    for (a, b, sp) in segs:
        if not pts:
            pts.append((0.0, a))
        elif abs(pts[-1][1] - a) > 1e-6:
            pts.append((loc + 1e-4, a))
        loc += (b - a) / sp
        pts.append((loc, b))
    return pts, loc


def plan_follow(rec, op, L):
    """手機連續點擊序列：視窗固定在能同時看到所有點擊目標（含其下方內容）的位置；目標分散太遠就跟著走。回傳 pan_keys。"""
    sw, sh = clip_size(rec.clip)
    wh = L.box[3] * sw / L.box[2]
    maxy = max(0.0, sh - wh)
    taps = [tp for tp in op.taps if not tp["hover"]]
    if not taps:
        return None
    ys = [tp["cy"] for tp in taps]
    lo, hi = min(ys), max(ys)
    if hi - lo <= wh - 500:
        y = min(max(lo - 260, 0), maxy)
        return [(0.0, y), (1.0, y)]
    keys = []
    for tp in taps:
        y = min(max(tp["cy"] - wh * 0.35, 0), maxy)
        keys.append((max(0.0, tp["t"] - 0.5), y))
    out = []
    for t_, y_ in keys:
        if out and t_ <= out[-1][0] + 1e-3:
            out[-1] = (out[-1][0], y_)
        else:
            out.append((t_, y_))
    return out


DWELLCHK: list = []   # (鏡, 內容量, 規定最短秒, 實際秒, 是否看完(底部入窗停≥1.2s), 備註)


def content_units(clip, s0, s1, tall_px=0):
    """內容量＝這一鏡看的區塊數：該時段錄影端標出的內容區（排除控制列與重複的「整區／頂端」）＋ 高內容每 900px 加 1。"""
    allj = load_all()
    labs = set()
    for key in _clip_keys(clip):
        for it in (allj.get(key) or {}).get("focus", []):
            ts = float(it.get("t_start", -1))
            if s0 - 0.2 <= ts <= s1 + 0.2:
                lab = str(it.get("label", ""))
                if any(k in lab for k in ("整區", "完整", "頂端", "底端", "捲到底", "搜尋", "分頁列", "切換列", "指標選單")):
                    continue
                labs.add(lab.split("（")[0])
    n = len(labs) + (int(math.ceil(tall_px / 900.0)) if tall_px else 0)
    return max(1, n)


def _extend_srcmap(srcmap, D_old, D_new, clip):
    if D_new <= D_old + 1e-6:
        return srcmap
    sm = list(srcmap)
    (t0, a0), (t1, a1) = sm[-2], sm[-1]
    slope = (a1 - a0) / (t1 - t0) if t1 - t0 > 1e-6 else 0.0
    cap = clip_dur(clip) - 0.05
    sm[-1] = (D_new, min(cap, a1 + slope * (D_new - D_old)))
    return sm


_CD: dict = {}


def clip_dur(clip):
    if clip not in _CD:
        import subprocess
        _CD[clip] = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(RAW3 / f"{clip}.mp4")], text=True))
    return _CD[clip]


def plan_dwell(rec, op, D, sub, L, pan_, chain=None, no_solve=False, cont=False, min_cap=None):
    """依內容量決定每鏡長度：最短停留＝2.0＋0.35×區塊數（≤7 秒）、字卡讀完（每秒 6.5 字）；長頁面必須滑到內容底部並停 1.2 秒；
    點擊後被點出的內容區要完整入窗並停 ≥1.5 秒。快節奏序列（Andy 指定）與播放鏡頭例外，並在檢查表標註。回傳 (D, dwell 資訊)。"""
    mobile = L.fmt == "mobile"
    s0 = rec.srcmap[0][1]
    s1 = max(a[1] for a in rec.srcmap)
    exempt = bool(chain)
    note = "快節奏序列（Andy 指定）" if chain else ""
    sw, sh = clip_size(rec.clip)
    wh = L.box[3] * sw / L.box[2] if mobile else 0
    units = content_units(rec.clip, s0, s1)
    min_req = min(7.0, 2.0 + 0.35 * units, min_cap or 99)
    reading = len(sub or "") / 6.5 + 0.3
    need = max(min_req, reading)
    reached, hold = True, 0.0
    taps = [tp for tp in op.taps if not tp["hover"]]
    if mobile:
        if taps and not no_solve and not chain:
            keys, chk, dmin = plan_mobile(rec, op, D, L)
            rec.pan, rec.pan_keys = None, keys
            rec._chk_raw = chk
            if not cont:
                need = max(need, dmin)
            units = max(units, 1 + sum(1 for c_ in chk if "高於" in c_[3]) * 2)
            min_req = min(7.0, 2.0 + 0.35 * units, min_cap or 99)
            need = max(need, min_req, reading)
            hold = D - (taps[-1]["t"] + 0.95)
        elif not chain:
            p2 = solve_pan(rec, op, D, pan_, L) if not no_solve else tuple(pan_ or (0, 0, 0.3, 0.3))
            ya, yb, t0, t1 = p2
            if abs(yb - ya) > 1:
                ts_ = max(0.6, abs(yb - ya) / 700.0)
                p2 = (ya, yb, t0, t0 + ts_)
                need = max(need, t0 + ts_ + 1.2)
            rec.pan = p2
            hold = D - p2[3]
        else:
            p3 = tuple(pan_ or (0, 0, 0.3, 0.3))
            if taps:
                ya_, yb_, a0, a1 = p3
                maxy_ = max(0.0, sh - wh)

                def y_at(tt):
                    ya2, yb2, q0, q1 = p3
                    u = 0 if q1 <= q0 else min(1, max(0, (tt - q0) / (q1 - q0)))
                    u = u * u * (3 - 2 * u)
                    return min(max(ya2 + (yb2 - ya2) * u, 0), maxy_)
                if not all(y_at(tp["t"]) + 40 <= tp["cy"] <= y_at(tp["t"]) + wh - 40 for tp in taps):
                    w_ = min(max(taps[0]["cy"] - wh * 0.55, 0), maxy_)
                    p3 = (w_, w_, 0.3, 0.9)
            rec.pan = p3
    else:
        if taps and not chain and not cont:
            need = max(need, taps[-1]["t"] + 0.95 + 1.5)
    D2 = D if exempt else max(D, math.ceil(need * 10) / 10.0)
    if D2 > D:
        rec.srcmap = _extend_srcmap(rec.srcmap, D, D2, rec.clip)
    if getattr(rec, "_chk_raw", None):
        rec._cchk = []
        for (lab, inc, src, nt, tp, r) in rec._chk_raw:
            tl = click_info(rec.clip, tp["src_t"], tp["x"], tp["y"])["label"]
            rec._cchk.append((0, tl, lab, inc, round(D2 - (tp["t"] + 0.95), 2), src, nt, {"_lab": tl}))
    if mobile and rec.pan and not rec.pan_keys and not chain:
        hold = D2 - rec.pan[3]
    if not mobile or not (rec.pan_keys):
        hold = hold if hold else max(0.0, D2 - (taps[-1]["t"] + 0.95 if taps else 0.0))
    if mobile and rec.pan_keys:
        hold = D2 - rec.pan_keys[-1][0]
    reached = exempt or hold >= 1.2 - 1e-6 or (not mobile) or (mobile and not rec.pan and not rec.pan_keys)
    if cont and not chain:
        note = (note + "；" if note else "") + "下一鏡同素材接續，點擊後內容在下一鏡停留"
        reached = True
    dw = {"units": units, "min_req": round(min_req, 2), "reading": round(reading, 2), "D": round(D2, 2), "reached": bool(reached), "hold": round(hold, 2), "note": note,
          "ok": bool(exempt or (D2 >= min(min_req, need) - 1e-6 and reached))}
    return D2, dw


def focus_target(clip, label, rect):
    allj = load_all()
    for key in _clip_keys(clip):
        for it in (allj.get(key) or {}).get("focus", []):
            if label and label in str(it.get("label", "")) and "video_rect" in it:
                return _xywh(it["video_rect"]), "錄影端 DOM（focus_targets）"
    return rect, "分鏡手估（錄影端尚未提供該區塊）"


# ───────────────────────── 錄影層 ─────────────────────────
def fit_aspect(win, ar, sw, sh, min_w=0.0):
    x0, y0, x1, y1 = win
    w, h = x1 - x0, y1 - y0
    if w / h < ar:
        w = h * ar
    else:
        h = w / ar
    w = max(w, min_w)
    h = w / ar
    if w > sw:
        w, h = sw, sw / ar
    if h > sh:
        h, w = sh, sh * ar
    cx = clamp((x0 + x1) / 2, w / 2, sw - w / 2)
    cy = clamp((y0 + y1) / 2, h / 2, sh - h / 2)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


MAINCHK: list = []   # (鏡, 主圖標籤, 入鏡%, 主圖面積佔視窗%, 視窗(src px), 備註)
AVAIL_W = (77, 66, 1766, 770)     # 網頁：網站畫面可用區（下方 244px 留給比比與泡泡）
AR_MIN, AR_MAX = 1.3, 2.3          # 視窗長寬比下限／上限（長條主圖補些上下文，維持可讀）


def _clip_rect(r, sw, sh):
    return (max(0, r[0]), max(0, r[1]), min(sw, r[2]), min(sh, r[3]))


def _area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _inter_rect(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def web_window(rects, sw, sh):
    """網頁視窗：包住所有主圖／點擊目標；長寬比在 [1.3, 2.3]（不夠就補上下文）；沒有目標＝整頁。"""
    if not rects:
        return (0.0, 0.0, float(sw), float(sh))
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    px, py = (x1 - x0) * 0.025 + 12, (y1 - y0) * 0.025 + 12
    x0, y0, x1, y1 = max(0, x0 - px), max(0, y0 - py), min(sw, x1 + px), min(sh, y1 + py)
    w, h = x1 - x0, y1 - y0
    if w < 1100:
        c = (x0 + x1) / 2
        x0, x1 = c - 550, c + 550
        w = 1100
    if h < 620:
        c = (y0 + y1) / 2
        y0, y1 = c - 310, c + 310
        h = 620
    ar = w / h
    if ar > AR_MAX:
        h2 = w / AR_MAX
        c = (y0 + y1) / 2
        y0, y1 = c - h2 / 2, c + h2 / 2
    elif ar < AR_MIN:
        w2 = h * AR_MIN
        c = (x0 + x1) / 2
        x0, x1 = c - w2 / 2, c + w2 / 2
    # 平移進素材範圍（不縮小視窗）
    dx = -x0 if x0 < 0 else (sw - x1 if x1 > sw else 0)
    dy = -y0 if y0 < 0 else (sh - y1 if y1 > sh else 0)
    x0, x1, y0, y1 = x0 + dx, x1 + dx, y0 + dy, y1 + dy
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(sw, x1), min(sh, y1)
    return (x0, y0, x1, y1)


def _drift(win, t, dur, k=0.015):
    """防停格（CEO 10-12：任何停格 ≤0.5 秒）：整鏡視窗以中心慢慢內縮 1.5%（推近極小、不超過原解析度）。"""
    if not V4:
        return win
    u = clamp(t / max(0.1, dur), 0, 1) * k
    x0, y0, x1, y1 = win
    dx, dy = (x1 - x0) * u / 2, (y1 - y0) * u / 2
    return (x0 + dx, y0 + dy, x1 - dx, y1 - dy)


class Rec4:
    """錄影層。web：每鏡視窗依「主圖＋點擊目標」決定、框依視窗長寬比縮放；mobile：寬度鋪滿框，內容比框高就垂直平移（pan）。"""

    def __init__(self, clip, srcmap, focus=None, pan=None, main=None):
        self.clip, self.srcmap, self.focus, self.pan = clip, srcmap, focus, pan   # pan=(y0, y1, t0, t1)
        self.main = list(main or [])      # 額外指定的主圖 rect（src px：x0,y0,x1,y1）
        self.win = self.rect = None
        self._wl = None
        self.pan_keys = None
        self._cchk = []

    def zoom_u(self, t):
        return 0.0 if self.focus is None or not self.focus.zoom else self.focus.zoom_u(t)

    def main_rects(self):
        rs = list(self.main)
        if self.focus and self.focus.frame:
            rs.append(tuple(self.focus.rect))
        return rs

    def _web_layout(self, L, shot, sw, sh):
        if self._wl is None:
            base_main = list(self.main)
            default_main = not base_main
            if default_main:
                f_ = sw / 3200.0
                base_main = [(480 * f_, 100 * f_, 3168 * f_, 1760 * f_)]      # 內容區（側欄與頁首以外）
            rs0 = base_main + ([tuple(self.focus.rect)] if self.focus and self.focus.frame else [])
            rs = [_clip_rect(r, sw, sh) for r in rs0]
            cont_rs = []
            if shot.op:
                for tp in shot.op.taps:
                    if tp["hover"]:
                        continue
                    cr, clab, csrc = post_click_content(self.clip, tp["src_t"], None, desktop=True)
                    if cr is not None:
                        tp = dict(tp)
                        tp["_lab"] = click_info(self.clip, tp["src_t"], tp["x"], tp["y"])["label"]
                        cont_rs.append((_clip_rect(cr, sw, sh), clab, csrc, tp))
            tap_rs = []
            if shot.op:
                for tp in shot.op.taps:
                    if tp["hover"]:
                        continue
                    r, _, _ = click_target(self.clip, tp["src_t"], tp["x"], tp["y"])
                    tap_rs.append(_clip_rect(r, sw, sh))
            win = web_window(rs + tap_rs + [c_[0] for c_ in cont_rs], sw, sh)
            wm = getattr(self, "win_max", None)      # 分鏡指定的裁切上限（例：自選清單右上「1／5 頁」裁在畫面外）
            if wm:
                win = (max(win[0], wm[0]), max(win[1], wm[1]), min(win[2], wm[2]), min(win[3], wm[3]))
            for (cr_, clab, csrc, tpx) in cont_rs:
                inc_ = _area(_inter_rect(cr_, win)) / max(1.0, _area(cr_))
                CONTENTCHK.append((shot.sid, tpx.get("_lab", ""), clab, round(inc_ * 100, 1), round(shot.dur - (tpx["t"] + 0.95), 2), csrc, ""))
            ww, wh = win[2] - win[0], win[3] - win[1]
            ax, ay, aw, ah = AVAIL_W
            sc = min(aw / ww, ah / wh)
            fw, fh = ww * sc, wh * sc
            ZOOMCHK.append((shot.sid, self.clip, round(sc, 3)))
            rect = (ax + (aw - fw) / 2, ay + (ah - fh) / 2, fw, fh)
            self._wl = (win, rect)
            # 主圖入鏡檢查
            if rs:
                mrs = [_clip_rect(r, sw, sh) for r in base_main]
                mb = (min(r[0] for r in mrs), min(r[1] for r in mrs), max(r[2] for r in mrs), max(r[3] for r in mrs))
                inc = _area(_inter_rect(mb, win)) / max(1.0, _area(mb))
                ratio = _area(mb) / max(1.0, _area(win))
                label = ("內容區（主圖整區）" if default_main else "指定主圖") + ("＋" + self.focus.label if self.focus and self.focus.frame else "")
            else:
                inc, ratio, label = 1.0, 1.0, "整頁（無單一主圖，整頁入鏡）"
                mb = win
            MAINCHK.append((shot.sid, label, round(inc * 100, 1), round(ratio * 100, 1), tuple(round(v) for v in win), "web"))
        return self._wl

    def draw(self, cv, t, shot):
        L = shot.L
        st = piecewise(self.srcmap, t)
        src = reader(self.clip).get(st)
        sw, sh = src.size
        rx, ry, rw, rh = L.box
        self.rect = (rx, ry, rw, rh)
        if L.fmt == "mobile":
            ww = sw
            wh = rh * sw / rw
            if self.pan_keys:
                ks = self.pan_keys
                y0 = ks[0][1] if t <= ks[0][0] else ks[-1][1]
                for (k0, v0), (k1, v1) in zip(ks, ks[1:]):
                    if k0 <= t <= k1:
                        y0 = lerp(v0, v1, ease_io((t - k0) / max(1e-3, k1 - k0)))
                        break
            elif self.pan:
                ya, yb, t0, t1 = self.pan
                y0 = lerp(ya, yb, ease_io((t - t0) / max(0.01, t1 - t0)))
            else:
                y0 = 0
            y0 = clamp(y0, 0, max(0, sh - wh))
            self.win = _drift((0, y0, ww, min(sh, y0 + wh)), t, shot.dur)
            if V4 and getattr(self, "win_keys", None):
                # 手機推近（content-editor 10-12）：win_keys＝[(鏡內秒, (x0, y0, x1, y1) 來源座標)]，寬高比固定為框的 1000:1480；
                # 視窗寬不得小於 1000 來源 px（輸出 1000px，倍率 ≤1.0，不超過原解析度）
                wk = self.win_keys[0][1]
                for (k, w_) in self.win_keys:
                    if t >= k - 1e-6:
                        wk = w_
                x0, y0_, x1, _ = wk
                cw = max(rw, min(sw, x1 - x0))
                ch = cw * rh / rw
                x0 = clamp(x0, 0, sw - cw)
                y0_ = clamp(y0_, 0, max(0, sh - ch))
                self.win = _drift((x0, y0_, x0 + cw, min(sh, y0_ + ch)), t, shot.dur)
            if not getattr(self, "_zdone", False):
                self._zdone = True
                ZOOMCHK.append((shot.sid, self.clip, round(rw / sw, 3)))
            if not getattr(self, "_cdone", False):
                self._cdone = True
                for (cl_, tlab, clab, inc, hold, csrc, note, tpx) in self._cchk:
                    CONTENTCHK.append((shot.sid, tpx.get("_lab", ""), clab, inc, hold, csrc, note))
            if not getattr(self, "_mchk", False):
                self._mchk = True
                f = self.focus
                if f and f.frame:
                    ts = f.t_draw + f.d_draw
                    if self.pan:
                        ya, yb, p0, p1 = self.pan
                        yy = lerp(ya, yb, ease_io((ts - p0) / max(0.01, p1 - p0)))
                    else:
                        yy = 0
                    yy = clamp(yy, 0, max(0, sh - wh))
                    win = (0, yy, sw, min(sh, yy + wh))
                    r = _clip_rect(tuple(f.rect), sw, sh)
                    inc = _area(_inter_rect(r, win)) / max(1.0, _area(r))
                    MAINCHK.append((shot.sid, f.label, round(inc * 100, 1), round(_area(_inter_rect(r, win)) / max(1.0, _area(win)) * 100, 1), tuple(round(v) for v in win), "mobile"))
                else:
                    MAINCHK.append((shot.sid, "（無單一主圖：分段下滑，逐區塊入鏡）", -1, -1, (0, round(y0), sw, round(y0 + wh)), "mobile"))
        elif V4:
            win, rect = self._v4_web(L, shot, sw, sh, t)
            self.win, self.rect = win, rect
        else:
            win, rect = self._web_layout(L, shot, sw, sh)
            self.win, self.rect = win, rect
        ix, iy, iw, ih = [int(round(v)) for v in self.rect]
        im = src.resize((iw, ih), Image.LANCZOS, box=self.win)
        tile = im.convert("RGBA")
        tile.putalpha(rounded_mask(iw, ih, 16))
        ImageDraw.Draw(tile).rounded_rectangle([1, 1, iw - 2, ih - 2], 16, outline=(DEEP if THEME["name"] == "cute" else R.NAVY) + (255,), width=2)
        cv.paste(tile, (ix, iy), tile)
        C.reg("site", (ix, iy, ix + iw, iy + ih), role="site")
        if t < 1.5 / FPS and not getattr(shot, "_cropped", False):
            shot._cropped = True
            if L.fmt == "mobile":
                full_w = abs((self.win[2] - self.win[0]) - sw) < 1.0
            else:
                full_w = MAINCHK[-1][2] >= 99.9 if MAINCHK else True
            left, right = ix, L.W - (ix + iw)
            CROPS.append((shot.sid, self.clip, left, right, full_w, abs(left - right) < 20 and full_w))
        if self.focus:
            self.focus.draw(cv, t, self, shot)

    def _v4_win(self, t, sw, sh):
        keys = getattr(self, "win_keys", None)
        if keys:
            w = keys[0][1]
            for (k, wk) in keys:
                if t >= k - 1e-6:
                    w = wk
            return tuple(w)
        return (0.0, 0.0, float(sw), float(sh))

    def _v4_web(self, L, shot, sw, sh, t):
        """第 4 版網頁：網站框固定 1766 寬（92%）、整頁入鏡（必要時依 win_keys 換裁切範圍），框貼上緣。"""
        win = self._v4_win(t, sw, sh)
        win = _drift(win, t, shot.dur)
        bx, by, bw, bh = getattr(self, "box4", None) or L.box
        ww, wh = win[2] - win[0], win[3] - win[1]
        sc = bw / ww
        fh = min(bh, wh * sc)
        if wh * sc > bh + 0.5:           # 太高：改以高度為準（寬度變窄、置中）
            sc = bh / wh
            fw = ww * sc
            rect = (bx + (bw - fw) / 2, by, fw, bh)
        else:
            rect = (bx, by, bw, fh)
        if not getattr(self, "_v4done", False):
            self._v4done = True
            ZOOMCHK.append((shot.sid, self.clip, round(sc, 3)))
            # 主圖入鏡：預設內容區 or 指定主圖（以最後一個裁切範圍為準）
            f_ = sw / 3200.0
            base = list(self.main) or [(480 * f_, 100 * f_, 3168 * f_, 1760 * f_)]
            wl = self._v4_win(1e9, sw, sh)
            mrs = [_clip_rect(r, sw, sh) for r in base]
            mb = (min(r[0] for r in mrs), min(r[1] for r in mrs), max(r[2] for r in mrs), max(r[3] for r in mrs))
            if getattr(self, "win_keys", None):
                mb = _clip_rect(_inter_rect(mb, wl) if _area(_inter_rect(mb, wl)) > 0 else mb, sw, sh)
            inc = _area(_inter_rect(mb, wl)) / max(1.0, _area(mb))
            MAINCHK.append((shot.sid, "內容區（主圖整區）" if not self.main else "指定主圖", round(inc * 100, 1), round(_area(_inter_rect(mb, wl)) / max(1.0, _area(wl)) * 100, 1), tuple(round(v) for v in wl), "web"))
            if shot.op:
                for tp in shot.op.taps:
                    if tp["hover"]:
                        continue
                    cr, clab, csrc = post_click_content(self.clip, tp["src_t"], None, desktop=True)
                    if cr is None:
                        continue
                    wt = self._v4_win(tp["t"] + 1.0, sw, sh)
                    cr = _clip_rect(cr, sw, sh)
                    inc_ = _area(_inter_rect(cr, wt)) / max(1.0, _area(cr))
                    lab = click_info(self.clip, tp["src_t"], tp["x"], tp["y"])["label"]
                    CONTENTCHK.append((shot.sid, lab, clab, round(inc_ * 100, 1), round(shot.dur - (tp["t"] + 0.95), 2), csrc, ""))
        return win, rect

    def map(self, sx, sy):
        x0, y0, x1, y1 = self.win
        rx, ry, rw, rh = self.rect
        return rx + (sx - x0) / (x1 - x0) * rw, ry + (sy - y0) / (y1 - y0) * rh


class Focus4:
    """焦點框：框＝目標 rect 外擴 10px、圓角 10、線寬 4；外光與壓暗只在框外，框內不動。"""

    def __init__(self, rect, label="", t_draw=0.7, d_draw=0.4, t_zoom=None, d_zoom=0.6, frame=True, zoom=True, max_up=1.0, dim=0.12, clip="", t_end=None):
        self.t_end = t_end
        self.src_rect = rect
        self.label = label
        self.rect, self.rect_src = focus_target(clip, label, rect) if clip else (rect, "分鏡手估")
        mob = "mobile" in (clip or "")
        mg = 16 if mob else 26
        SW, SH = (1170, None) if mob else (3200, 1800)
        x0, y0, x1, y1 = self.rect
        n = [max(x0, mg), max(y0, mg), min(x1, SW - mg), min(y1, SH - mg) if SH else y1]
        if [round(v) for v in n] != [round(v) for v in self.rect]:
            self.rect = tuple(n)
            self.rect_src += "（貼邊處內縮，框不超出畫面）"
        self.t_draw, self.d_draw, self.d_zoom = t_draw, d_draw, d_zoom
        self.t_zoom = t_draw + d_draw + 0.15 if t_zoom is None else t_zoom
        self.frame, self.zoom = frame, zoom
        self.max_up_inv = 1 / max_up
        self.dim = dim
        self._logged = False

    def zoom_u(self, t):
        return ease_io((t - self.t_zoom) / self.d_zoom) if self.zoom else 0.0

    def frame_rect(self, rec):
        x0, y0 = rec.map(self.rect[0], self.rect[1])
        x1, y1 = rec.map(self.rect[2], self.rect[3])
        e = EXPAND_FOCUS
        return (x0 - e, y0 - e, x1 + e, y1 + e), (x0, y0, x1, y1)

    def draw(self, cv, t, rec, shot):
        if not self.frame or t < self.t_draw or (self.t_end is not None and t >= self.t_end):
            return
        u = clamp((t - self.t_draw) / self.d_draw, 0, 1)
        fr, tg = self.frame_rect(rec)
        sx0, sy0, sx1, sy1 = rec.rect[0], rec.rect[1], rec.rect[0] + rec.rect[2], rec.rect[1] + rec.rect[3]
        # 可見度：目標若只有少部分在可見區就不畫（手機平移時）
        vis_h = max(0, min(tg[3], sy1) - max(tg[1], sy0)) / max(1, tg[3] - tg[1])
        vis_w = max(0, min(tg[2], sx1) - max(tg[0], sx0)) / max(1, tg[2] - tg[0])
        if vis_h < 0.3 or vis_w < 0.3:
            return
        W, H = cv.size
        x0, y0, x1, y1 = fr
        cx0, cy0, cx1, cy1 = max(x0, sx0 + 2), max(y0, sy0 + 2), min(x1, sx1 - 2), min(y1, sy1 - 2)   # 框貼著可見區邊緣時往內收 2px
        # 壓暗：只在框外（站內）
        a_dim = self.dim * ease_io(u) * (1 - self.zoom_u(t))
        col = THEME["glow"] if THEME["name"] == "cute" else (66, 140, 255)
        r = 10
        hole = Image.new("L", (W, H), 0)
        ImageDraw.Draw(hole).rounded_rectangle([cx0, cy0, cx1, cy1], r, fill=255)
        if a_dim > 0.004:
            dm = Image.new("L", (W, H), 0)
            ImageDraw.Draw(dm).rectangle([sx0, sy0, sx1, sy1], fill=int(255 * a_dim))
            dm = Image.fromarray(np.minimum(np.array(dm), 255 - np.array(hole)))
            dk = Image.new("RGBA", (W, H), (20, 30, 50, 255))
            dk.putalpha(dm)
            cv.paste(dk, (0, 0), dk)
        # 外光：只在框外
        g = ease_io((t - self.t_draw - self.d_draw * 0.7) / 0.3)
        if g > 0:
            ring = Image.new("L", (W, H), 0)
            ImageDraw.Draw(ring).rounded_rectangle([cx0, cy0, cx1, cy1], r, outline=int(255 * 0.55 * g), width=12)
            ring = ring.filter(ImageFilter.GaussianBlur(7))
            ring = Image.fromarray(np.minimum(np.array(ring), 255 - np.array(hole)))
            gl = Image.new("RGBA", (W, H), col + (255,))
            gl.putalpha(ring)
            cv.paste(gl, (0, 0), gl)
        # 框線（沿邊描出）
        path = R._rect_path(cx0, cy0, cx1, cy1, r)
        pts = R._partial(path, ease_io(u))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if len(pts) > 1:
            d = ImageDraw.Draw(lay)
            if THEME["name"] == "pro":
                d.line(pts, fill=col + (255,), width=4, joint="curve")
            else:
                d.line(pts, fill=col + (255,), width=4, joint="curve")
        cv.paste(lay, (0, 0), lay)
        # 驗證（畫完定格那一幀記錄）
        if u >= 1 and not self._logged:
            self._logged = True
            errs = (round(tg[0] - x0), round(tg[1] - y0), round(x1 - tg[2]), round(y1 - tg[3]))
            inside = (x0 >= sx0 - 1 and y0 >= sy0 - 1 and x1 <= sx1 + 1 and y1 <= sy1 + 1)
            ok = all(abs(e - EXPAND_FOCUS) <= 12 for e in errs) and inside
            FOCUSES.append((shot.sid, round(t, 2), self.label or "(未命名)", errs, inside, ok, self.rect_src))


# ───────────────────────── shots.md／點擊 ─────────────────────────
@lru_cache(maxsize=1)
def parse_events():
    md = (RAW3 / "shots.md").read_text()
    out = {}
    for blk in md.split("\n## ")[1:]:
        lines = blk.split("\n")
        name = lines[0].strip()
        ev = []
        for ln in lines[1:]:
            m = re.search(r"([\d.]+)s (踩下|拖曳開始|拖曳放開|游標移到) \((-?[\d.]+),(-?[\d.]+)\)css → 影片\((-?\d+),(-?\d+)\)px", ln)
            if m:
                kind = {"踩下": "tap", "拖曳開始": "drag_start", "拖曳放開": "drag_end", "游標移到": "hover"}[m.group(2)]
                ev.append({"t": float(m.group(1)), "kind": kind, "x": int(m.group(5)), "y": int(m.group(6))})
        out[name] = ev
    return out


def events_for(clip):
    ev = parse_events().get(clip, [])
    if any(e["kind"] == "tap" for e in ev):
        return ev
    allj = load_all()
    syn = []
    for it in (allj.get(clip) or {}).get("targets", []):
        if it.get("kind", "click") == "click" and it.get("center"):
            syn.append({"t": float(it["t"]), "kind": "tap", "x": int(round(it["center"][0])), "y": int(round(it["center"][1]))})
    return ev + sorted(syn, key=lambda e: e["t"]) if syn else ev


def inv_srcmap(srcmap, st, tol=1e-6):
    for (t0, s0), (t1, s1) in zip(srcmap, srcmap[1:]):
        if s1 - s0 > tol and (t1 - t0) > 1e-3 and s0 - tol <= st <= s1 + tol:
            return t0 + (st - s0) / (s1 - s0) * (t1 - t0)
    return None


def ripple(cv, xy, age, small=False):
    if age < 0 or age > 0.5:
        return
    u = ease_out(age / 0.5)
    r = (22 if small else 38) + (28 if small else 52) * u
    a = int(230 * (1 - u))
    col = SKY if THEME["name"] == "cute" else (66, 140, 255)
    lay = Image.new("RGBA", (int(r * 2 + 12), int(r * 2 + 12)), (0, 0, 0, 0))
    c = r + 6
    ImageDraw.Draw(lay).ellipse([c - r, c - r, c + r, c + r], outline=col + (a,), width=4 if small else 5, fill=col + (a // 6,))
    cv.paste(lay, (int(xy[0] - c), int(xy[1] - c)), lay)


# ───────────────────────── 比比操作員 ─────────────────────────
@lru_cache(maxsize=256)
def magic_sprite(i, size):
    info = B.bibi_index()["magic_frame"]
    im = Image.open(info["frames"][i]).convert("RGBA")
    a = np.array(im)
    a[:222, :, 3] = 0
    return Image.fromarray(a).resize((size, size), Image.LANCZOS)


def put_magic(cv, i, foot, size):
    size = int(round(size / 4) * 4)
    sp = magic_sprite(i, size)
    s = size / 512
    cv.paste(sp, (int(round(foot[0] - 248 * s)), int(round(foot[1] - 482 * s))), sp)
    ys, xs = np.nonzero(np.array(sp)[..., 3] > 28)
    if len(xs):
        x0 = foot[0] - 248 * s + xs.min()
        y0 = foot[1] - 482 * s + ys.min()
        C.reg("bibi:magic", (x0, y0, x0 + (xs.max() - xs.min()), y0 + (ys.max() - ys.min())), role=ROLE[0], group="bibi")


def sparkle_trail(cv, p0, p1, u):
    if u <= 0 or u >= 1.1:
        return
    d = ImageDraw.Draw(cv)
    col = THEME["glow"] if THEME["name"] == "cute" else (66, 140, 255)
    for k in range(6):
        v = clamp(u - k * 0.07, 0, 1)
        if v <= 0:
            continue
        x, y = lerp(p0[0], p1[0], ease_io(v)), lerp(p0[1], p1[1], ease_io(v)) - 30 * math.sin(math.pi * v)
        r = max(2, 8 - k)
        d.polygon([(x, y - r * 1.8), (x + r * 0.6, y - r * 0.6), (x + r * 1.8, y), (x + r * 0.6, y + r * 0.6), (x, y + r * 1.8),
                   (x - r * 0.6, y + r * 0.6), (x - r * 1.8, y), (x - r * 0.6, y - r * 0.6)], fill=col + (255,))


PAN_LOG: list = []
_SZ: dict = {}


def clip_size(clip):
    """用 ffprobe 取素材尺寸（不開解碼器，避免每個 worker 都開一堆 ffmpeg）。"""
    if clip not in _SZ:
        import subprocess
        o = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                     "-of", "csv=p=0", str(RAW3 / f"{clip}.mp4")], text=True).strip().split(",")
        _SZ[clip] = (int(o[0]), int(o[1]))
    return _SZ[clip]


def solve_pan(rec, op, D, pan_, L):
    """垂直視窗規劃（網頁、手機共用）：① 點擊目標在點下那一刻必須落在畫面框內；② 非推近的焦點框要完整在視窗內
    （框比視窗高就取可見上段並標註）；點完才慢慢滑。回傳 (ya, yb, t0, t1)。"""
    sw, sh = clip_size(rec.clip)
    rx, ry, rw, rh = L.box
    wh = rh * sw / rw
    maxy = max(0.0, sh - wh)
    ya, yb, t0, t1 = pan_ or (0, 0, 0.3, 0.3)
    ya, yb = min(max(ya, 0), maxy), min(max(yb, 0), maxy)
    taps = [(tp["t"], tp["y"]) for tp in op.taps if not tp["hover"]] if op else []

    def win(tt, p):
        a_, b_, s0, s1 = p
        u = 0 if s1 <= s0 else min(1, max(0, (tt - s0) / (s1 - s0)))
        u = u * u * (3 - 2 * u)
        return a_ + (b_ - a_) * u

    def ok_taps(p):
        return all(win(tt, p) + 40 <= y <= win(tt, p) + wh - 40 for tt, y in taps)
    cur = (ya, yb, t0, t1)
    if not ok_taps(cur):
        lo, hi = min(y for _, y in taps) - 70, max(y for _, y in taps) + 70
        if hi - lo > wh:
            lo, hi = taps[0][1] - 70, taps[0][1] + 70
        w0 = min(max(lo - max(0, (wh - (hi - lo)) / 2), 0), maxy)
        last = max(tt for tt, _ in taps)
        t0n = last + 0.55
        if t0n + 0.9 > D or yb <= w0:
            cur = (w0, w0, 0.3, 0.9)
            PAN_LOG.append((rec.clip, "靜止", (ya, yb, t0, t1), cur))
        else:
            cur = (w0, min(max(yb, 0), maxy), t0n, max(t0n + 0.9, D - 0.15))
            PAN_LOG.append((rec.clip, "調整", (ya, yb, t0, t1), cur))
    f = rec.focus
    if f and f.frame and f.zoom and (f.rect[3] - f.rect[1]) * 1.12 > wh:
        f.zoom = False     # 框比視窗高：改成平移視窗＋取可見上段，不推近
    if f and f.frame and not f.zoom:
        fy0, fy1 = f.rect[1], f.rect[3]
        mg = 16 * sw / rw
        need = (fy1 - fy0) + 2 * mg
        end_w = win(D, cur)

        def fits(w):
            return w + mg * 0.5 <= fy0 and fy1 <= w + wh - mg * 0.5
        if not (fits(win(f.t_draw + f.d_draw, cur)) and fits(end_w)):
            if need <= wh:
                w1 = min(max(fy0 - (wh - (fy1 - fy0)) / 2, 0), maxy)
            else:
                w1 = min(max(fy0 - mg, 0), maxy)
                f.rect = (f.rect[0], fy0, f.rect[2], min(fy1, w1 + wh - mg))
                f.rect_src += "（框高於畫面框，取可見上段）"
            last = max([tt for tt, _ in taps] + [0.0])
            ws = win(last + 0.5, cur) if taps else win(0, cur)
            ts0 = last + 0.5 if taps else 0.2
            if taps and ws + 40 <= (max(y for _, y in taps)) and False:
                pass
            # 先在點擊前的視窗不動，點完（或一開始）滑到 w1，滑完才畫框
            t_end = ts0 + 0.9
            f.t_draw = max(f.t_draw, t_end + 0.1)
            f.t_zoom = f.t_draw + f.d_draw + 0.15
            start = win(0, cur) if not taps else min(win(last, cur), maxy)
            cur = (start, w1, ts0, t_end)
            PAN_LOG.append((rec.clip, "焦點", pan_, cur))
    return cur


class Op:
    """比比操作員：待在側帶／窄帶；點擊只在「跳進去踩下」那段（≤0.9 秒）進入框內；框內操作用漣漪表示。"""

    FLY = 0.4        # 起跳到落地
    STAY = 0.25      # 踩著
    BACK = 0.3       # 彈回
    FLYC = 0.2       # 連續點擊：目標之間直接跳過去

    def __init__(self, rec, idle="talk_happy", extra=(), events=None, use_events=True, magic=True, soft_hover=False, tap_scale=0.8, chain=None):
        self.rec, self.magic = rec, magic
        self.chain, self.prev_op = chain, None
        self.idle = [(0, idle)] if isinstance(idle, str) else list(idle)
        self.extra = list(extra)
        self.tap_scale = tap_scale
        self.taps, self.drags = [], []
        evs = sorted(events if events is not None else (events_for(rec.clip) if use_events else []), key=lambda e: e["t"])
        end_src = max(sm[1] for sm in rec.srcmap)
        last_xy, last_t = None, -9
        for e in evs:
            if e["kind"] == "hover" and not soft_hover:
                continue
            lt = inv_srcmap(rec.srcmap, e["t"])
            if e["kind"] == "drag_end" and lt is None and e["t"] > end_src:
                lt = rec.srcmap[-1][0]
            if lt is None:
                continue
            if e["kind"] in ("tap", "hover"):
                if lt < (self.FLYC if chain in ('mid', 'end') else self.FLY) + 0.02:
                    continue
                near = (not chain) and last_xy and abs(e["x"] - last_xy[0]) < 70 and abs(e["y"] - last_xy[1]) < 70 and lt - last_t < 3.5
                if near:
                    continue
                dense = (lt - last_t) < 0.9
                inf = click_info(rec.clip, e["t"], e["x"], e["y"])
                self.taps.append({"t": lt, "x": e["x"], "y": e["y"], "cx": inf["center"][0], "cy": inf["center"][1], "dense": dense and not chain,
                                  "hover": e["kind"] == "hover", "src_t": e["t"]})
                last_xy, last_t = (e["x"], e["y"]), lt
            elif e["kind"] == "drag_start":
                self.drags.append({"s0": e["t"], "t0": lt, "x0": e["x"], "y0": e["y"]})
            elif e["kind"] == "drag_end" and self.drags and "t1" not in self.drags[-1]:
                self.drags[-1].update({"s1": e["t"], "t1": lt, "x1": e["x"], "y1": e["y"]})
        self.drags = [d for d in self.drags if "t1" in d and d["t1"] > d["t0"]]

    def home(self, L, name):
        hx, hf = getattr(self, "hx", None) or L.host_x, getattr(self, "hfoot", None) or L.host_foot
        sz = fit_box(name, L.host_w, getattr(self, "hh", None) or L.host_h, L.host_size)
        return side_foot(name, sz, hx, hf), sz

    def home_rect(self, L, t):
        """這一鏡所有待機／魔法棒／拖曳姿勢在 home 的外框聯集（整鏡固定，泡泡尾巴不跳動）。"""
        names = {n for _, n in self.idle}
        f = getattr(self.rec, "focus", None)
        if f and f.frame and self.magic:
            names.add("magic_frame")
        if self.drags:
            names |= {"hop_l", "hop_r"}
        if THEME["name"] == "pro":
            names = {pro_idle(n) for n in names}
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for nm in names:
            foot, sz = self.home(L, nm)
            u = union512(nm)
            sc = sz / 512
            w, h = (u[2] - u[0]) * sc, (u[3] - u[1]) * sc
            hx, hf = getattr(self, "hx", None) or L.host_x, getattr(self, "hfoot", None) or L.host_foot
            x0, y0 = min(x0, hx - w / 2), min(y0, hf - h)
            x1, y1 = max(x1, hx + w / 2), max(y1, hf)
        return None, (x0, y0, x1, y1)

    @staticmethod
    def land(L, p, ts, box=None):
        """比比落地點：漣漪維持在元素正中；比比本人只踩在畫面框內（上緣太近就站在目標下方，下緣太近就站在框內底）。"""
        bx = box or L.box
        top, bot = bx[1] + 4, bx[1] + bx[3] - 6
        y = p[1]
        if y - ts < top:
            y = p[1] + ts + 16
        y = min(y, bot)
        return (clamp(p[0], 30, L.W - 30), y)

    def tland(self, L, rec, tp, ts):
        """踩按鈕落點（第 4 版，CEO 10-12）：比比只讓腳碰到按鈕上緣，身體在按鈕上方，按鈕文字露出；上方放不下就站在按鈕正下方。"""
        try:
            r, _, _ = click_target(rec.clip, tp["src_t"], tp["x"], tp["y"])
        except Exception:
            r = None
        cx, cy = rec.map(tp["cx"], tp["cy"])
        if not r:
            return self.land(L, (cx, cy), ts, rec.rect)
        x0, y0 = rec.map(r[0], r[1])
        x1, y1 = rec.map(r[2], r[3])
        bx = rec.rect
        top, bot = bx[1] + 4, bx[1] + bx[3] - 6
        y = y0 - 6               # 比比的腳（素材底部含約 10px 陰影／壓扁）剛好碰到按鈕上緣
        if y - ts * 0.9 < top:
            y = y1 + ts * 0.95 + 2
        y = min(y, bot)
        return (clamp(cx, 30, L.W - 30), y)

    def _seq(self):
        return [tp for tp in self.taps if not tp["hover"] and not tp["dense"]]

    # ───── 第 4 版（CEO 10-12）：比比瞬移踩按鈕（不從內容上飛過）、腳只碰按鈕上緣、身體落在空白處 ─────
    TAP_IN, TAP_OUT = 0.25, 0.45          # 點下前 0.25 秒出現在按鈕上、點下後 0.45 秒消失（落下到彈回 ≤0.7 秒；踩著的時間 ≤0.6 秒）

    def _busy_at(self, shot, L, t):
        key = round(t, 2)
        cache = self.__dict__.setdefault("_bcache", {})
        if key not in cache:
            rec = self.rec
            saved = list(C.CUR)
            win, rect = rec.win, rec.rect
            cv = R.background(L.fmt).copy()
            rec.draw(cv, t, shot)
            b = busy_mask(cv, rec.rect)
            cache[key] = (b, main_mask(shot, b, color_mask(cv, rec.rect)))
            rec.win, rec.rect = win, rect
            C.CUR[:] = saved
        return cache[key]

    def _btn(self, rec, tp):
        r, lab, _ = click_target(rec.clip, tp["src_t"], tp["x"], tp["y"])
        x0, y0 = rec.map(r[0], r[1])
        x1, y1 = rec.map(r[2], r[3])
        return (x0, y0, x1, y1), lab

    def _tap_pose(self, shot, L, tp):
        """在按鈕附近找比比的站法：先試腳碰按鈕上緣；不行再試站在按鈕左右兩側（身體貼著按鈕邊）、頭頂碰按鈕下緣；
        比比由 150px 縮到 64px。身體不壓按鈕以外的受保護像素（≤1%）、按鈕露出 ≥80%。"""
        if "_pose" in tp:
            return tp["_pose"]
        rec = self.rec
        bs = [self._busy_at(shot, L, tt_) for tt_ in (max(0.0, tp["t"] - self.TAP_IN), tp["t"], min(shot.dur - 1 / FPS, tp["t"] + self.TAP_OUT))]
        busy = bs[0][0] | bs[1][0] | bs[2][0]
        mainm = bs[0][1] | bs[1][1] | bs[2][1]
        mm = mainm.copy()                 # 主角資料區再外擴 6px 當安全邊（逐幀檢查時畫面有 1.5% 慢推）
        for k in range(1, 7):
            mm[k:, :] |= mainm[:-k, :]
            mm[:-k, :] |= mainm[k:, :]
        mainm = mm.copy()
        for k in range(1, 7):
            mm[:, k:] |= mainm[:, :-k]
            mm[:, :-k] |= mainm[:, k:]
        mainm = mm
        (bx0, by0, bx1, by1), _ = self._btn(rec, tp)
        H, W = busy.shape
        bm = np.zeros_like(busy)
        bm[max(0, int(by0)):min(H, int(by1) + 1), max(0, int(bx0)):min(W, int(bx1) + 1)] = True
        barea = max(1, int(bm.sum()))
        rowb = _row_band(busy, (bx0, by0, bx1, by1))
        fr = rec.rect
        best = None
        for size in (150, 130, 110, 96, 84, 72, 64, 56, 48):
            r0 = C.sprite_rect(B.bibi_index()["tap"]["frames"][8], (0, 0), size)   # 相對腳底的外框
            cands = []
            for fx in (0.5, 0.3, 0.7, 0.1, 0.9):
                cands.append(("top", fx))
            for fy in (1.0, 0.5):
                cands.append(("left", fy))
                cands.append(("right", fy))
            for fx in (0.5, 0.2, 0.8):
                cands.append(("bottom", fx))
            for side, q in cands:
                if side == "top":
                    foot = (bx0 + q * (bx1 - bx0), by0 + 5)
                elif side == "bottom":
                    foot = (bx0 + q * (bx1 - bx0), by1 - r0[1] - 3)
                elif side == "left":
                    foot = (bx0 - r0[2] + 4, by0 + q * (by1 - by0))
                else:
                    foot = (bx1 - r0[0] - 4, by0 + q * (by1 - by0))
                sx, sy, m = _sprite_alpha("tap", 8, foot, size)
                tot = int(m.sum())
                if tot == 0:
                    continue
                if sx < fr[0] or sy < fr[1] - 2 or sx + m.shape[1] > fr[0] + fr[2] or sy + m.shape[0] > fr[1] + fr[3] + 2:
                    continue
                hit_out, _ = _mask_hits(busy & ~bm, sx, sy, m)
                hit_main, _ = _mask_hits(mainm & ~bm & ~rowb, sx, sy, m)
                cov, _ = _mask_hits(bm, sx, sy, m)
                # CEO 10-12（例外 1）：主角圖表資料區 0%、其他文字 ≤15%、按鈕露出 ≥80%；越乾淨越好、越大越好
                ok = hit_main == 0 and hit_out <= 0.12 * tot and cov <= 0.18 * barea      # 留安全邊（檢查上限 15％／20％）
                bad = hit_main / tot * 10 + hit_out / tot + max(0.0, cov / barea - 0.2) * 3
                pref = {"top": 0, "left": 1, "right": 1, "bottom": 2}[side]
                clean = hit_out <= 0.01 * tot
                score = (not ok, not clean, -size if ok else 0, pref, bad)
                if best is None or score < best[0]:
                    best = (score, (side, q, size), bad, ok)
            if best and best[3] and not best[0][1]:
                break
        tp["_pose"] = best[1] if best else ("top", 0.5, 96)
        tp["_pose_bad"] = (best[2], best[3]) if best else (1.0, False)
        return tp["_pose"]

    def _pose_foot(self, rec, tp, pose):
        side, q, size = pose
        (bx0, by0, bx1, by1), _ = self._btn(rec, tp)
        r0 = C.sprite_rect(B.bibi_index()["tap"]["frames"][8], (0, 0), size)
        if side == "top":
            return (bx0 + q * (bx1 - bx0), by0 + 5), size
        if side == "bottom":
            return (bx0 + q * (bx1 - bx0), by1 - r0[1] - 3), size
        if side == "left":
            return (bx0 - r0[2] + 4, by0 + q * (by1 - by0)), size
        return (bx1 - r0[0] - 4, by0 + q * (by1 - by0)), size

    def _drag_pose(self, shot, L, p, t):
        """3D 推轉：比比跟著拖曳點走，站在模型旁邊的空白處（不壓模型與其他內容）。"""
        tq = round(t * 2) / 2
        busy = self._busy_at(shot, L, tq)[0] | self._busy_at(shot, L, min(shot.dur - 1 / FPS, tq + 0.5))[0]
        fr = self.rec.rect
        best = None
        for size in (150, 130, 110, 96):
            for dy in (0.0, 0.5, 1.0, -0.5, 1.5, -1.0, 2.0, -1.5, 2.5):
                for dx in (0.0, -0.6, 0.6, -1.2, 1.2):
                    foot = (p[0] + dx * size, p[1] + dy * size)
                    sx, sy, m = _sprite_alpha("hop_r", 2, foot, size)
                    tot = int(m.sum())
                    if not tot or sx < fr[0] or sy < fr[1] or sx + m.shape[1] > fr[0] + fr[2] or sy + m.shape[0] > fr[1] + fr[3]:
                        continue
                    hit, _ = _mask_hits(busy, sx, sy, m)
                    sc = (hit / tot > 0.01, hit / tot, abs(dy) + abs(dx), -size)
                    if best is None or sc < best[0]:
                        best = (sc, (foot, size))
            if best and best[0][1] <= 0.01:
                break
        return best[1] if best else (p, 110)

    def _v4_draw(self, cv, t, shot, L, home, hs, iname):
        rec = self.rec
        for tp in self._seq():
            c = tp["t"]
            if c - self.TAP_IN <= t < c + self.TAP_OUT:
                pose = self._tap_pose(shot, L, tp)
                foot, size = self._pose_foot(rec, tp, pose)
                # 整段用同一個站姿（第 8 格），大小不變：找站位時算過的就是畫出來的（縮放進出場會改變壓到的範圍）
                ROLE[0] = "bibi_tap"
                put_sprite(cv, "tap", 8, foot, size)
                ROLE[0] = "bibi"
                return
        for d in self.drags:
            if d["t0"] - 0.1 <= t <= d["t1"] + 0.1:
                u = clamp((t - d["t0"]) / max(0.01, d["t1"] - d["t0"]), 0, 1)
                p = rec.map(lerp(d["x0"], d["x1"], u), lerp(d["y0"], d["y1"], u))
                foot, size = self._drag_pose(shot, L, p, t)
                nm = "hop_r" if d["x1"] >= d["x0"] else "hop_l"
                ROLE[0] = "bibi"
                put_sprite(cv, nm, anim_frame(nm, t - d["t0"]), foot, size)
                return
        ROLE[0] = "bibi"
        put_sprite(cv, iname, anim_frame(iname, t), home, hs)

    def bubble_mode(self, t):
        """'tail'＝比比在 home（泡泡帶尾巴）；'hide'＝比比飛行中（泡泡淡出）；'plain'＝連續點擊期間比比在框內（只留字卡，不帶尾巴）。"""
        taps = self._seq()
        if not taps:
            return "tail"
        if V4:
            for tp in taps:
                if tp["t"] - self.TAP_IN <= t < tp["t"] + self.TAP_OUT:
                    return "plain"           # 比比去踩按鈕時泡泡留著（不帶尾巴），不閃
            return "tail"
        if self.chain:
            c0, cl = taps[0]["t"], taps[-1]["t"]
            if self.chain in ("start", "solo"):
                if self.chain == "solo" and t >= cl + self.STAY - 0.05:
                    if t < cl + self.STAY + self.BACK + 0.1:
                        return "hide"
                    return "tail"
                if t < c0 - self.FLY - 0.08:
                    return "tail"
                if t < c0 + 0.05:
                    return "hide"
                return "plain"
            if self.chain == "mid":
                return "plain"
            # end
            if t < cl + self.STAY - 0.05:
                return "plain"
            if t < cl + self.STAY + self.BACK + 0.1:
                return "hide"
            return "tail"
        for tp in taps:
            if tp["t"] - self.FLY - 0.08 <= t <= tp["t"] + self.STAY + self.BACK + 0.08:
                return "hide"
        return "tail"

    def away(self, t):
        return self.bubble_mode(t) == "hide"

    def idle_name(self, t):
        name = self.idle[0][1]
        for t0, n in self.idle:
            if t >= t0:
                name = n
        return name

    def draw(self, cv, t, shot):
        L = shot.L
        rec = self.rec
        pro = THEME["name"] == "pro"
        iname = self.idle_name(t)
        if pro:
            iname = pro_idle(iname)
        home, hs = self.home(L, iname)
        ts = int(max(hs, 190) * self.tap_scale) if L.fmt == "web" else 190
        # 漣漪（點下那一幀起）＋ 點擊驗證（漣漪中心＝錄影端量到的點擊中心；落點須在目標 rect 內、離邊緣 ≥6px）
        for tp in self.taps:
            if rec.win and not tp["hover"]:
                cxy = rec.map(tp["cx"], tp["cy"])
                ripple(cv, cxy, t - tp["t"], tp["dense"])
                if abs(t - tp["t"]) < 0.5 / FPS and not tp.get("_chk"):
                    tp["_chk"] = True
                    inf = click_info(rec.clip, tp["src_t"], tp["x"], tp["y"])
                    r = inf["rect"]
                    a = rec.map(r[0], r[1])
                    b = rec.map(r[2], r[3])
                    mg = min(cxy[0] - a[0], b[0] - cxy[0], cxy[1] - a[1], b[1] - cxy[1])
                    need = min(6.0, max(0.5, min(b[0] - a[0], b[1] - a[1]) / 2 - 1))
                    inside_t = mg >= need
                    sx0, sy0, sw_, sh_ = rec.rect
                    inside_v = sx0 <= cxy[0] <= sx0 + sw_ and sy0 <= cxy[1] <= sy0 + sh_
                    okc = inside_t and inside_v and inf["hit"] is not False
                    CLICKS.append((shot.sid, round(t, 2), rec.clip, inf["label"] or "(座標)", (round(cxy[0]), round(cxy[1])),
                                   (round(a[0]), round(a[1]), round(b[0]), round(b[1])), okc, inf["src"],
                                   (round(inf["center"][0]), round(inf["center"][1])), round(mg, 1)))
        if V4 and rec.win:
            self._v4_draw(cv, t, shot, L, home, hs, iname)
            return
        if not pro:
            for t0, t1, name, foot, size, mode in self.extra:
                if t0 <= t < t1:
                    f = foot(rec) if callable(foot) else foot
                    nm = name
                    h2, s2 = self.home(L, nm)
                    ROLE[0] = "bibi"
                    put_sprite(cv, nm, anim_frame(nm, t - t0, mode), f or h2, size or s2)
                    return
        # 拖曳：比比在側帶／窄帶原地用小跳步表示推
        for d in self.drags:
            if d["t0"] - 0.1 <= t <= d["t1"] + 0.1:
                dx = 1 if d["x1"] >= d["x0"] else -1
                nm = "hop_r" if dx > 0 else "hop_l"
                h2, s2 = self.home(L, nm)
                ROLE[0] = "bibi"
                put_sprite(cv, nm, anim_frame(nm, t - d["t0"]), h2, s2)
                return
        # 連續點擊序列：比比從上一個目標直接跳到下一個（0.2 秒），只在序列開頭進場、結尾退場一次
        if self.chain and rec.win:
            tl = [(tp["t"], self.tland(L, rec, tp, 150)) for tp in self._seq()]
            if tl:
                pos_in = home
                if self.chain in ("mid", "end"):
                    pxy = getattr(self, "prev_xy", None)
                    if pxy:
                        pos_in = self.land(L, rec.map(pxy[0], pxy[1]), 150, rec.rect)
                tsz = 150
                for i, (c, tgt) in enumerate(tl):
                    first = i == 0
                    start = (home if self.chain in ("start", "solo") else pos_in) if first else tl[i - 1][1]
                    fly = self.FLY if (first and self.chain in ("start", "solo")) else self.FLYC
                    nxt_f0 = tl[i + 1][0] - self.FLYC if i + 1 < len(tl) else None
                    if first and self.chain in ("mid", "end") and t < c - fly:
                        ROLE[0] = "bibi_tap"
                        put_sprite(cv, "tap", 8 + int(t * 4) % 2, pos_in, tsz)
                        ROLE[0] = "bibi"
                        return
                    if c - fly <= t < c:
                        u = ease_io((t - (c - fly)) / fly)
                        arc = (110 if fly > 0.3 else 40) * THEME["bounce"] * math.sin(math.pi * u)
                        foot = (lerp(start[0], tgt[0], u), max(rec.rect[1] + tsz + 4, lerp(start[1], tgt[1], u) - arc))
                        ROLE[0] = "bibi_tap"
                        put_sprite(cv, "tap", 3 + int(clamp(u, 0, 0.999) * 5), foot, lerp(hs, tsz, u) if (first and self.chain in ("start", "solo")) else tsz)
                        ROLE[0] = "bibi"
                        return
                    if t >= c and (nxt_f0 is None or t < nxt_f0):
                        if nxt_f0 is None and self.chain in ("end", "solo"):
                            if t < c + self.STAY:
                                ROLE[0] = "bibi_tap"
                                put_sprite(cv, "tap", 8 + (1 if t - c > 0.1 else 0), tgt, tsz)
                                ROLE[0] = "bibi"
                                return
                            if t < c + self.STAY + self.BACK:
                                u = ease_io((t - c - self.STAY) / self.BACK)
                                foot = (lerp(tgt[0], home[0], u), max(rec.rect[1] + tsz + 4, lerp(tgt[1], home[1], u) - 70 * THEME["bounce"] * math.sin(math.pi * u)))
                                ROLE[0] = "bibi_tap"
                                put_sprite(cv, "hop_l" if home[0] < tgt[0] else "hop_r", 2 + int(u * 3.99), foot, lerp(tsz, hs, u))
                                ROLE[0] = "bibi"
                                return
                        else:
                            ROLE[0] = "bibi_tap"
                            if t - c < 0.25:
                                put_sprite(cv, "tap", 8 + (1 if t - c > 0.1 else 0), tgt, tsz)
                            else:
                                nm_ = self.idle_name(t)
                                put_sprite(cv, nm_, anim_frame(nm_, t), tgt, tsz)
                            ROLE[0] = "bibi"
                            return
        else:
            pass
        # 踩按鈕（單點）
        taps = [tp for tp in self.taps if not tp["dense"]] if not self.chain else []
        for i, tp in enumerate(taps):
            c = tp["t"]
            nxt = taps[i + 1]["t"] if i + 1 < len(taps) else 1e9
            tgt = self.tland(L, rec, tp, ts)
            chained = i > 0 and c - taps[i - 1]["t"] < self.FLY + self.STAY + self.BACK + 0.2
            if chained:
                start = self.tland(L, rec, taps[i - 1], ts)
                ssize = ts
            else:
                start, ssize = home, hs
            if c - self.FLY <= t < c:
                u = ease_io((t - (c - self.FLY)) / self.FLY)
                foot = (lerp(start[0], tgt[0], u), max(rec.rect[1] + ts + 4, lerp(start[1], tgt[1], u) - 120 * THEME["bounce"] * math.sin(math.pi * u)))
                size = lerp(ssize, ts, u)
                ROLE[0] = "bibi_tap"
                put_sprite(cv, "tap", 3 + int(clamp(u, 0, 0.999) * 5), foot, size)
                ROLE[0] = "bibi"
                return
            if c <= t < c + self.STAY:
                ROLE[0] = "bibi_tap"
                put_sprite(cv, "tap", 8 + (1 if t - c > 0.1 else 0), tgt, ts)
                ROLE[0] = "bibi"
                return
            if not (nxt - c < self.FLY + self.STAY + self.BACK + 0.2) and c + self.STAY <= t < c + self.STAY + self.BACK:
                u = ease_io((t - c - self.STAY) / self.BACK)
                foot = (lerp(tgt[0], home[0], u), max(rec.rect[1] + ts + 4, lerp(tgt[1], home[1], u) - 90 * THEME["bounce"] * math.sin(math.pi * u)))
                ROLE[0] = "bibi_tap"
                put_sprite(cv, "hop_l" if home[0] < tgt[0] else "hop_r", 2 + int(u * 3.99), foot, lerp(ts, hs, u))
                ROLE[0] = "bibi"
                return
        # 魔法棒畫框
        f = getattr(rec, "focus", None)
        if f and f.frame and self.magic and f.t_draw - 0.35 <= t < f.t_draw + f.d_draw + 0.15 and rec.win:
            i = int(clamp((t - (f.t_draw - 0.35)) / 0.95 * 12, 0, 11))
            mh, ms = self.home(L, "magic_frame")
            ROLE[0] = "bibi"
            put_magic(cv, i, mh, ms)
            fr, _ = f.frame_rect(rec)
            s = ms / 512
            hand = (mh[0] + (372 - 248) * s, mh[1] + (318 - 482) * s)
            sparkle_trail(cv, hand, (clamp(fr[0], 20, L.W - 20), clamp(fr[1], 20, L.H - 20)), (t - (f.t_draw - 0.25)) / 0.3)
            return
        ROLE[0] = "bibi"
        put_sprite(cv, iname, anim_frame(iname, t), home, hs)


# ───────────────────────── 鏡頭 ─────────────────────────
# ───────────────────────── 忙碌圖（CEO 10-12：不依賴錄影端重點框，畫面上有字、有線、有圖的像素都受保護） ─────────────────────────
BUSY_TH = 28          # 相鄰像素灰階差 >28 ＝ 有字／有線／有圖（網站底色格線約 ≤21，不算）
BUSY_DILATE = 4
BUSYCHK: list = []    # (鏡, 秒, 元素, 壓到受保護像素比例%, 說明)


def busy_mask(cv, rect):
    """畫布 cv 在 rect（x, y, w, h）範圍內的受保護像素（bool，全畫布大小）。"""
    W, H = cv.size
    x0, y0 = max(0, int(rect[0])), max(0, int(rect[1]))
    x1, y1 = min(W, int(rect[0] + rect[2])), min(H, int(rect[1] + rect[3]))
    out = np.zeros((H, W), dtype=bool)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return out
    a = np.asarray(cv.crop((x0, y0, x1, y1)).convert("L"), dtype=np.int16)
    gx = np.zeros_like(a)
    gy = np.zeros_like(a)
    gx[:, :-1] = np.abs(np.diff(a, axis=1))
    gy[:-1, :] = np.abs(np.diff(a, axis=0))
    m = np.maximum(gx, gy) > BUSY_TH
    # 框線（網站畫面框本身的描邊 2px）不算內容
    m[:3, :] = False
    m[-3:, :] = False
    m[:, :3] = False
    m[:, -3:] = False
    r = BUSY_DILATE
    d = m.copy()
    for k in range(1, r + 1):
        d[k:, :] |= m[:-k, :]
        d[:-k, :] |= m[k:, :]
    m = d.copy()
    for k in range(1, r + 1):
        d[:, k:] |= m[:, :-k]
        d[:, :-k] |= m[:, k:]
    out[y0:y1, x0:x1] = d
    return out


def color_mask(cv, rect):
    """有顏色的資料像素（K 線紅綠、熱力圖色塊、漲跌紅綠數字）：飽和度 >0.35、亮度 >60，外擴 4px。"""
    W, H = cv.size
    x0, y0 = max(0, int(rect[0])), max(0, int(rect[1]))
    x1, y1 = min(W, int(rect[0] + rect[2])), min(H, int(rect[1] + rect[3]))
    out = np.zeros((H, W), dtype=bool)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return out
    a = np.asarray(cv.crop((x0, y0, x1, y1)).convert("RGB"), dtype=np.int16)
    mx, mn = a.max(axis=2), a.min(axis=2)
    m = ((mx - mn) > 0.35 * np.maximum(mx, 1)) & (mx > 60)
    m[:3, :] = m[-3:, :] = False
    m[:, :3] = m[:, -3:] = False
    d = m.copy()
    for k in range(1, 5):
        d[k:, :] |= m[:-k, :]
        d[:-k, :] |= m[k:, :]
    m = d.copy()
    for k in range(1, 5):
        d[:, k:] |= m[:, :-k]
        d[:, :-k] |= m[:, k:]
    out[y0:y1, x0:x1] = d
    return out


def main_mask(shot, busy, colored):
    """主角圖表的資料區（CEO 10-12：踩按鈕那一下一律 0%）：有顏色的資料像素（K 線、熱力圖色塊、紅綠漲跌數字）。
    被點按鈕所在的那一列（按鈕上下各半個按鈕高，橫跨整個框）是篩選列／表頭／分頁列，不算資料區（另外 ≤15%）。"""
    return colored & busy


def _row_band(busy, b):
    bx0, by0, bx1, by1 = b
    h = max(8, by1 - by0)
    m = np.zeros_like(busy)
    H = busy.shape[0]
    m[max(0, int(by0 - 0.5 * h)):min(H, int(by1 + 0.5 * h) + 1), :] = True
    return m


def _sprite_alpha(name, i, foot, size):
    """(x, y, bool 遮罩)：這個比比素材在畫布上實際不透明的像素。"""
    size = int(round(size / 4) * 4)
    sp = B.sprite(name, i, size)
    s = size / 512
    x = int(round(foot[0] - 248 * s))
    y = int(round(foot[1] - 482 * s))
    return x, y, np.asarray(sp.getchannel("A")) > 40


def _mask_hits(mask, x, y, m):
    H, W = mask.shape
    h, w = m.shape
    xa, ya, xb, yb = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if xb <= xa or yb <= ya:
        return 0, int(m.sum())
    sub = m[ya - y:yb - y, xa - x:xb - x]
    return int((sub & mask[ya:yb, xa:xb]).sum()), int(m.sum())


def site_rect_canvas(shot):
    rec = shot.rec
    return rec.rect if rec is not None and rec.rect is not None else None


def busy_check(shot, t, busy, mainb=None):
    """逐幀：疊加元素和受保護像素的相交 ≤ 該元素面積 1%。比比踩按鈕那一下（落下到彈回 ≤0.6 秒）只准碰被點的按鈕、按鈕露出 ≥80%。"""
    if busy is None:
        return
    if not busy.any():
        BUSYCHK.append((shot.sid, round(t, 3), "（整鏡）", 100.0, "受保護區 0 個：忙碌圖算不出任何內容，不准空檢查也算通過"))
        return
    rec = shot.rec
    taps = [tp for tp in (shot.op.taps if shot.op else []) if not tp["hover"]]
    # 比比素材：逐像素
    for (name, i, foot, size, role) in SPR_DRAWN:
        x, y, m = _sprite_alpha(name, i, foot, size)
        hit, tot = _mask_hits(busy, x, y, m)
        if tot == 0:
            continue
        if role == "bibi_tap":
            tp = next((q for q in taps if q["t"] - 0.25 <= t <= q["t"] + 0.45), None)
            if tp is not None:
                r, lab, _ = click_target(rec.clip, tp["src_t"], tp["x"], tp["y"])
                bx0, by0 = rec.map(r[0], r[1])
                bx1, by1 = rec.map(r[2], r[3])
                bm = np.zeros_like(busy)
                H, W = busy.shape
                bm[max(0, int(by0)):min(H, int(by1) + 1), max(0, int(bx0)):min(W, int(bx1) + 1)] = True
                hit_out, _ = _mask_hits(busy & ~bm, x, y, m)
                hit_main, _ = _mask_hits(mainb & ~bm & ~_row_band(busy, (bx0, by0, bx1, by1)), x, y, m) if mainb is not None else (0, 0)
                cov, _ = _mask_hits(bm, x, y, m)
                barea = max(1, int(bm.sum()))
                if hit_main > 0:
                    BUSYCHK.append((shot.sid, round(t, 3), "bibi:" + name + "（踩按鈕）", round(hit_main * 100 / tot, 2), "踩按鈕時壓到主角圖表資料區（必須 0%）"))
                if hit_out > 0.15 * tot:
                    BUSYCHK.append((shot.sid, round(t, 3), "bibi:" + name + "（踩按鈕）", round(hit_out * 100 / tot, 2), "踩按鈕時壓到按鈕以外的文字 >15%"))
                if cov > 0.2 * barea:
                    BUSYCHK.append((shot.sid, round(t, 3), "bibi:" + name + "（踩按鈕）", round(cov * 100 / barea, 2), f"按鈕「{lab}」被蓋超過 20%（文字要露出 ≥80%）"))
                continue
        if hit > 0.01 * tot:
            BUSYCHK.append((shot.sid, round(t, 3), "bibi:" + name, round(hit * 100 / tot, 2), "比比壓到受保護像素（>1%）"))
    # 泡泡、字卡、小字、道具框：整個外框
    for (name, r, role, grp) in list(C.CUR):
        if role in ("site", "bibi", "bibi_tap") or name.startswith("ripple") or name.startswith("bibi:"):
            continue
        x0, y0, x1, y1 = [int(round(v)) for v in r]
        if x1 <= x0 or y1 <= y0:
            continue
        m = np.ones((y1 - y0, x1 - x0), dtype=bool)
        hit, tot = _mask_hits(busy, x0, y0, m)
        if hit > 0.01 * tot:
            BUSYCHK.append((shot.sid, round(t, 3), name, round(hit * 100 / tot, 2), "疊加元素壓到受保護像素（>1%）"))


_BUSY_CACHE = {}


def shot_busy_union(shot, L, n=6):
    """整鏡受保護像素的聯集（取實際播出的幾個時間點），給比比找空白處用。"""
    key = (shot.sid, L.fmt, getattr(shot.rec, "box4", None))
    if key in _BUSY_CACHE:
        return _BUSY_CACHE[key]
    rec = shot.rec
    saved = list(C.CUR)
    acc = None
    n = max(n, int(shot.dur * 5))          # 每 0.2 秒取一格（中途才出現的內容、播放動畫也算進去）
    ts = [shot.dur * k / max(1, n - 1) for k in range(n)]
    for tt in ts:
        cv = R.background(L.fmt).copy()
        rec.draw(cv, min(tt, shot.dur - 1 / FPS), shot)
        m = busy_mask(cv, rec.rect)
        acc = m if acc is None else (acc | m)
    C.CUR[:] = saved
    _BUSY_CACHE[key] = acc
    return acc


def forbidden_src(shot):
    """這一鏡不准被疊加元素壓到的區域（來源像素）：錄影端的重點框（focus_targets）、點擊後內容框（content_rect）、點擊目標。
    錄影端沒有重點框的鏡頭，整個內容區都當重點（保守：圖表一定要都被看到）。"""
    if getattr(shot, "_forb", None) is not None:
        return shot._forb
    rec = shot.rec
    out = []
    if rec is None:
        shot._forb = out
        return out
    pts = rec.srcmap
    lo, hi = min(p[1] for p in pts), max(p[1] for p in pts)
    allj = load_all()
    sw, sh = clip_size(rec.clip)
    for key in _clip_keys(rec.clip):
        e = allj.get(key) or {}
        for f in e.get("focus", []):
            vr = f.get("video_rect")
            ts_, te_ = f.get("t_start"), f.get("t_end")
            if not vr or ts_ is None:
                continue
            if ts_ <= hi + 0.5 and (te_ if te_ is not None else 1e9) >= lo - 0.5:
                out.append(("重點框：" + str(f.get("label", ""))[:16], _clip_rect((vr[0], vr[1], vr[0] + vr[2], vr[1] + vr[3]), sw, sh), None))
        for it in e.get("targets", []):
            cr, cv_ = it.get("content_rect"), it.get("content_visible_t")
            if cr and cv_ and cv_[0] <= hi + 0.5 and cv_[1] >= lo - 0.5:
                out.append(("內容框：" + str(it.get("label", ""))[:16], _clip_rect((cr[0], cr[1], cr[0] + cr[2], cr[1] + cr[3]), sw, sh), None))
        if out:
            break
    if not out:
        f_ = sw / 3200.0 if sw > 1500 else 1.0
        if sw > 1500:
            out.append(("內容區（錄影端無重點框，整區保護）", (480 * f_, 100 * f_, 3168 * f_, 1760 * f_), None))
    if shot.op:
        for tp in shot.op.taps:
            if tp["hover"]:
                continue
            r, lab, _ = click_target(rec.clip, tp["src_t"], tp["x"], tp["y"])
            out.append(("點擊目標：" + str(lab or "")[:16], tuple(r), tp["t"]))
    shot._forb = out
    return out


def _map_rect(rec, r):
    x0, y0 = rec.map(r[0], r[1])
    x1, y1 = rec.map(r[2], r[3])
    fr = (rec.rect[0], rec.rect[1], rec.rect[0] + rec.rect[2], rec.rect[1] + rec.rect[3])
    return _inter_rect((x0, y0, x1, y1), fr)


# 網站錄影內建的客服鈕（.supfab GIF 模式 76×76 CSS px、right/bottom 20px；.bibiring 同位置）
# CEO 10-12：當成永久的疊加元素檢查；素材是 _nofab（錄影時已藏）或在例外清單就不檢查
FAB_EXEMPT = {
    "V25_desktop": "客服在這段是主角（導覽／客服面板），CEO 10-12 決定不重錄",
    "V26_desktop": "客服在這段是主角（客服面板、願望清單），CEO 10-12 決定不重錄",
    "V25_mobile": "客服在這段是主角，CEO 10-12 決定不重錄",
    "V26_mobile": "客服在這段是主角，CEO 10-12 決定不重錄",
    "V16_desktop": "目視確認客服鈕落在空白底色（fab_hits.json，10-12）",
    "V17_desktop": "目視確認客服鈕落在空白底色（fab_hits.json，10-12）",
    "V18_desktop": "目視確認客服鈕只壓到頁尾「顯示詳細規範」鈕，非圖表（fab_hits.json，10-12）",
    "V23_desktop": "目視確認客服鈕落在空白底色（fab_hits.json，10-12）",
    "V04_mobile_v3c": "目視確認客服鈕落在兩張卡片之間的空白（fab_hits.json，10-12）",
}


def fab_rect_src(clip, sw, sh):
    if "mobile" in clip:          # 手機 @3 實測：右 35、下 30，含兩側晃動線
        return (sw - 240, sh - 170, sw - 35, sh - 30)
    dpr = sw / 1600.0             # 桌機 @2；_v3c 2400 寬 @1.5
    return (sw - 96 * dpr - 6, sh - 96 * dpr - 6, sw - 20 * dpr + 6, sh - 20 * dpr + 6)


def site_overlay_check(shot, t):
    """逐幀：疊加元素（比比、泡泡、字卡、小字、道具）與重點框／內容框／點擊目標相交面積必須是 0。
    踩按鈕那一下（bibi_tap）只准腳碰到按鈕邊緣：與被踩按鈕的重疊高度 ≤8px，按鈕文字要露出。"""
    rec = shot.rec
    if rec is None or rec.win is None:
        return
    forb = forbidden_src(shot)
    mapped = []
    for (lab, r, tt) in forb:
        mr = _map_rect(rec, r)
        if _area(mr) > 0:
            mapped.append((lab, mr, tt))
    items = []        # 疊加元素改由 busy_check（忙碌圖）逐像素檢查；這裡只留網站內建客服鈕的檢查
    clip = rec.clip
    if "_nofab" not in clip and clip not in FAB_EXEMPT:
        sw, sh = clip_size(clip)
        fr = _map_rect(rec, fab_rect_src(clip, sw, sh))
        if _area(fr) > 0:
            items.append(("網站客服鈕（錄影內建，需 _nofab 重錄）", fr, "fab", None))
            if not any(tt is None for _, _, tt in forb):   # 手機素材沒標重點框：客服鈕對整個內容區檢查（保守）
                mr = _map_rect(rec, (24, 174, 1146, sh))
                if _area(mr) > 0:
                    mapped.append(("內容區（錄影端無重點框，客服鈕檢查用）", mr, "fab_only"))
    for (name, r, role, grp) in items:
        if role == "site" or name.startswith("ripple"):
            continue
        for (lab, mr, tt) in mapped:
            if tt == "fab_only":
                if role != "fab":
                    continue
                tt = None
            ir = _inter_rect(r, mr)
            a = _area(ir)
            if a <= 0:
                continue
            if tt is not None and role in ("bibi", "bibi_tap"):
                # 點擊目標：比比站在按鈕上那段（踩下前後）只准腳碰到上緣，按鈕文字要露出；飛行途中掠過不算（例外①，≤0.8 秒）
                if not (tt - 0.05 <= t <= tt + 0.27):       # 站在按鈕上那 0.25 秒
                    continue
                if ir[3] - ir[1] <= 8:
                    continue
                SITEOV.append((shot.sid, round(t, 3), name, lab + "（按鈕文字被蓋）", round(a)))
                continue
            if role == "bibi_tap":
                continue              # 踩按鈕的飛行／停留 ≤0.8 秒例外（重點框、內容框）
            SITEOV.append((shot.sid, round(t, 3), name, lab, round(a)))


def _wrap(f, text, maxw):
    """泡泡斷行：不拆英數字詞、標點不放行首、優先在逗號／頓號後斷；最多 3 行。"""
    if text_w(f, text) <= maxw:
        return [text]
    import re
    toks = re.findall(r"[A-Za-z0-9.+\-／/%]+|.", text)
    lines, cur = [], ""
    for tk in toks:
        if text_w(f, cur + tk) > maxw and cur:
            # 回退到最近的逗號／頓號後面斷
            cut = max(cur.rfind("，"), cur.rfind("、"), cur.rfind("！"), cur.rfind("？"))
            if cut >= 2 and cut < len(cur) - 1:
                lines.append(cur[:cut + 1])
                cur = cur[cut + 1:] + tk
            else:
                lines.append(cur)
                cur = tk
            if cur and cur[0] in "，、。！？：；）」":
                lines[-1] += cur[0]
                cur = cur[1:]
        else:
            cur += tk
    if cur:
        lines.append(cur)
    return lines[:3]


def v4_place(shot, L):
    """第 4 版網頁：比比待在忙碌圖算出來的空白處（泡泡在比比正上方）。
    整鏡找不到：先把比比縮到 130px；還不夠，就把網站框縮到 87% 寬，右側讓出邊條放比比。不准壓內容。"""
    op, rec = shot.op, shot.rec
    if op is None or rec is None or getattr(op, "_placed", False):
        return
    op._placed = True
    sw, sh = clip_size(rec.clip)
    busy = shot_busy_union(shot, L)
    fr = rec.rect
    f = font(B.F_ROUND, 28)
    lines = _wrap(f, shot.sub or "", 300)
    bw_ = max(text_w(f, ln) for ln in lines) + 44
    bh_ = len(lines) * 36 + 26
    names = {n for _, n in op.idle}
    H, W = busy.shape
    integ = np.zeros((H + 1, W + 1), dtype=np.int32)
    integ[1:, 1:] = np.cumsum(np.cumsum(busy, axis=0), axis=1)

    def bsum(x0, y0, x1, y1):
        x0, y0, x1, y1 = int(max(0, x0)), int(max(0, y0)), int(min(W, x1)), int(min(H, y1))
        if x1 <= x0 or y1 <= y0:
            return 0
        return int(integ[y1, x1] - integ[y0, x1] - integ[y1, x0] + integ[y0, x0])

    def bib_rect(hx, foot, hh):
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for nm in names:
            sz = fit_box(nm, L.host_w, hh, L.host_size)
            u = union512(nm)
            s = sz / 512
            w, h = (u[2] - u[0]) * s, (u[3] - u[1]) * s
            x0, y0, x1, y1 = min(x0, hx - w / 2), min(y0, foot - h), max(x1, hx + w / 2), max(y1, foot)
        return (x0, y0, x1, y1)

    best = None
    for hh in (214, 180, 150, 130):
        for foot in range(int(fr[1] + fr[3] - 6), int(fr[1] + 300), -24):
            for hx in range(int(fr[0] + 130), int(fr[0] + fr[2] - 130), 24):
                br = bib_rect(hx, foot, hh)
                bub = (hx - bw_ / 2, br[1] - 26 - bh_, hx + bw_ / 2, br[1] - 26)
                if bub[1] < fr[1] + 4 or br[0] < fr[0] + 4 or br[2] > fr[0] + fr[2] - 4:
                    continue
                a1 = (br[2] - br[0]) * (br[3] - br[1])
                a2 = (bub[2] - bub[0]) * (bub[3] - bub[1])
                h1 = bsum(*br)
                h2 = bsum(bub[0] - 8, bub[1] - 8, bub[2] + 8, bub[3] + 8)
                if h1 <= 0.002 * a1 and h2 == 0:
                    # 偏好：越靠下、越靠左
                    sc = (-hh, -foot, hx)
                    if best is None or sc < best[0]:
                        best = (sc, (hx, foot, hh))
        if best:
            break
    if best:
        hx, foot, hh = best[1]
        op.hx, op.hfoot, op.hh, op.bside, op.bmaxw = hx, foot, hh, "T", 300
        op.place_note = f"網站框內空白處（比比 {hh}px）"
        return
    # 縮框讓出右側邊條（87% 寬），比比 130px＋泡泡在邊條內
    bw4 = 1660
    rec.box4 = (24, 58 + (993 - bw4 * 993 / 1766) / 2, bw4, bw4 * 993 / 1766)
    op.hx, op.hfoot, op.hh, op.bside, op.bmaxw = 1802, 1040, 130, "T", 150
    op.place_note = "整鏡找不到夠大的空白：網站框縮到 86.5% 寬（1660px），比比在右側邊條"
    _BUSY_CACHE.clear()


class Shot4:
    def __init__(self, sid, dur, layers=(), pill=None, head="", hl="", sub="", op=None, cues=(), kind="feature", foot=True, custom=None):
        self.sid, self.dur = sid, dur
        self.layers = list(layers)
        self.pill, self.head, self.hl, self.sub = pill, head, hl, sub
        self.op, self.cues, self.kind, self.foot, self.custom = op, list(cues), kind, foot, custom
        self.L = None
        self.dwell = None

    @property
    def rec(self):
        for ly in self.layers:
            if isinstance(ly, Rec4):
                return ly
        return None

    def auto_cues(self):
        c = list(self.cues)
        r = self.rec
        if self.op:
            for tp in self.op.taps:
                if not tp["hover"] and not tp["dense"]:
                    c.append((tp["t"], "tap"))
            for d in self.op.drags[:1]:
                c.append((max(0, d["t0"] - 0.2), "swish"))
        if r and r.focus:
            if r.focus.frame:
                c.append((r.focus.t_draw, "draw"))
            if r.focus.zoom:
                c.append((r.focus.t_zoom, "zoom"))
        return sorted(c)

    cont = False      # 與前一鏡同一句字卡：不重新淡入

    def render(self, t, L):
        self.L = L
        if self.dwell and t < 1.5 / FPS and not getattr(self, "_dw_done", False):
            self._dw_done = True
            d_ = self.dwell
            DWELLCHK.append((self.sid, d_["units"], d_["min_req"], d_["D"], d_["reached"], d_["hold"], d_["note"]))
        C.begin()
        C.SITE_OK = bool(V4 and L.fmt == "web" and self.kind == "feature")
        if V4 and L.fmt == "web" and self.kind == "feature":
            v4_place(self, L)
        ROLE[0] = "bibi"
        cv = R.background(L.fmt).copy()
        SPR_DRAWN.clear()
        for ly in self.layers:
            ly.draw(cv, t, self)
        busy = busy_mask(cv, self.rec.rect) if (V4 and self.kind == "feature" and self.rec is not None and self.rec.rect is not None) else None
        mainb = main_mask(self, busy, color_mask(cv, self.rec.rect)) if busy is not None else None
        if self.custom:
            self.custom(cv, t, self)
        if self.kind == "feature":
            self._overlays(cv, t + (1.0 if self.cont else 0.0), L)
        if self.op:
            self.op.draw(cv, t, self)
        if self.kind == "feature":
            host_bubble(cv, L, self, self.sub, t, t + (1.0 if self.cont else 0.0))
        if V4 and self.kind == "feature":
            site_overlay_check(self, t)
            busy_check(self, t, busy, mainb)
        return cv

    def _overlays(self, cv, t, L):
        if L.fmt == "web":
            ppx = L.pill_px * (0.85 if THEME["name"] == "pro" else 1)
            pw = (text_w(font(THEME["pill_font"], int(ppx)), self.pill) + 44) if self.pill else 0
            hw = text_w(font(THEME["head_font"], L.head_px), self.head)
            px = L.pill_xy[0]
            total = (pw + 36 if self.pill else 0) + hw
            # 頁首附近要踩的按鈕會讓比比頭部伸進上帶 → 標題改靠右，避開
            if self.op and self.rec and self.rec.rect and self.rec.win:
                for tp in self.op.taps:
                    if tp["hover"]:
                        continue
                    mx, my = self.rec.map(tp["x"], tp["y"])
                    if my < self.rec.rect[1] + 130 and px - 70 <= mx <= px + total + 70:
                        px = self.rec.rect[0] + self.rec.rect[2] - total
                        break
            hx = px
            if self.pill:
                R.pill(cv, self.pill, px, L.pill_xy[1], px=L.pill_px)
                hx = px + pw + 36
            L.head_xy = (hx, L.head_y)
            R.headline(cv, L, self.head, t, self.hl)
            footnote4(cv, L)
            _shot_note(cv, L, self, t)
        else:
            hx = L.pill_xy[0]
            if self.pill:
                pw = R.pill(cv, self.pill, L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
                hx = hx + pw + 30
            L.head_xy = (hx, L.head_y)
            R.headline(cv, L, self.head, t, self.hl)
            footnote4(cv, L)
            _shot_note(cv, L, self, t)


def _shot_note(cv, L, shot, t):
    """鏡頭附註小字（例：報酬比較的「過去表現不代表未來」，法遵要求）。分鏡端設定 shot.note＝文字。
    網頁：畫面右上（標題列右側，網站框上方）；手機：比比帶與網站框之間（y 384～410）。"""
    text = getattr(shot, "note", None)
    if not text:
        return
    f = font(F_MED, 22 if L.fmt == "web" else 24)
    tw = text_w(f, text)
    if L.fmt == "web":
        y = 16
        occ = [r for (n, r, ro, g) in C.CUR if n in ("headline",) or n.startswith("pill")]
        x = L.box[0] + L.box[2] - tw - 16
        for cand in [L.box[0] + L.box[2] - tw - 16] + [r[2] + 40 for r in occ] + [r[0] - tw - 40 for r in occ]:
            box = (cand - 10, y - 4, cand + tw + 10, y + 30)
            if cand >= 12 and cand + tw <= L.W - 12 and not any(C._inter((box[0] - 8, box[1], box[2] + 8, box[3]), r) > 0 for r in occ):
                x = cand
                break
    else:
        x, y = 40 + (900 - tw) / 2, 386
    R.float_panel(cv, (x - 10, y - 4, x + tw + 10, y + 30), 225, 10)
    ImageDraw.Draw(cv).text((x, y), text, font=f, fill=(60, 60, 60))
    C.reg("note", (x - 10, y - 4, x + tw + 10, y + 30))


def subtitle_web(cv, L, text, t):
    if not text:
        return
    f = font(F_BOLD, L.sub_px)
    wmax = text_w(f, text)
    a = clamp(t / 0.2, 0, 1)
    x, y = L.box[0] + 22, L.sub_y
    h = L.sub_px * 1.25 + 8
    lay = Image.new("RGBA", (int(wmax) + 60, int(h) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, wmax + 44, h], 12, fill=THEME["panel_fill"] + (235,), outline=THEME["panel_outline"], width=1)
    if THEME["name"] == "pro":
        d.rectangle([0, 3, 4, h - 3], fill=DEEP)
    d.text((22, 2), text, font=f, fill=THEME["ink"])
    if a < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    cv.paste(lay, (int(x - 22), int(y)), lay)
    C.reg("subtitle", (x - 22, y, x - 22 + wmax + 44, y + h))


def footnote4(cv, L):
    f = font(F_MED, 20 if L.fmt == "web" else 22)
    text = R.FOOTNOTE
    tw = text_w(f, text)
    d = ImageDraw.Draw(cv)
    x = L.W / 2 - tw / 2 + 60
    y = L.foot_y
    if L.fmt == "web":
        x = L.W / 2 - tw / 2
        R.float_panel(cv, (x - 12, y, x + tw + 12, y + 28), 215, 10)
        d.text((x, y + 1), text, font=f, fill=(80, 80, 80))
        C.reg("footnote", (x - 12, y, x + tw + 12, y + 28))
    else:
        if V4:
            x = 40 + (900 - tw) / 2
        d.text((x, y), text, font=f, fill=(90, 90, 90))
        C.reg("footnote", (x, y, x + tw, y + 28))


def host_bubble(cv, L, shot, text, t, t_alpha=None):
    """比比的台詞泡泡（網頁、手機共用）：單一路徑，尾巴尖端離比比 14px、只指向比比，文字離尾巴 ≥10px。"""
    if not text or not shot.op:
        return
    nm, br = shot.op.home_rect(L, t)
    if getattr(shot.op, "bside", "R") == "T":
        _bubble_top(cv, L, text, t if t_alpha is None else t_alpha, br, mode=shot.op.bubble_mode(t), maxw=getattr(shot.op, "bmaxw", 215))
        return
    _bubble_at(cv, L, text, t if t_alpha is None else t_alpha, br, mode=shot.op.bubble_mode(t))


def _bubble_top(cv, L, text, t, br, mode="tail", maxw=215, op=None):
    """泡泡在比比正上方（第 4 版網頁），尾巴朝下指向比比；寬度不超過 maxw，泡泡整個留在畫面內。"""
    a = clamp(t / 0.2, 0, 1)
    if mode == "hide":
        return
    f = font(B.F_ROUND, 28)
    lines = _wrap(f, text, maxw)
    tw = max(text_w(f, ln) for ln in lines)
    lh = 36
    w, h = tw + 44, len(lines) * lh + 26
    cx = clamp((br[0] + br[2]) / 2, 12 + w / 2, L.W - 12 - w / 2)
    tip = ((br[0] + br[2]) / 2, br[1] - 12)
    rect = (cx - w / 2, tip[1] - 14 - h, cx + w / 2, tip[1] - 14)
    ty = rect[1] + 13
    tr = (cx - tw / 2, ty, cx + tw / 2, ty + len(lines) * lh)
    draw_bubble(cv, rect, None if mode == "plain" else tip, alpha=a, ink=THEME["ink"], width=4, r=min(THEME["panel_r"], 20), text_rect=tr)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        d.text((cx - text_w(f, ln) / 2, ty + i * lh), ln, font=f, fill=THEME["ink"])
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    cv.paste(lay, (0, 0), lay)


def card_host(cv, L, nm, text, t, mode=None):
    """卡片鏡頭的比比（在下方帶，與一般鏡頭同位置同大小）＋泡泡。"""
    sz = fit_box(nm, L.host_w, L.host_h, L.host_size)
    foot = side_foot(nm, sz, L.host_x, L.host_foot)
    ROLE[0] = "bibi"
    put_sprite(cv, nm, anim_frame(nm, t) if mode is None else anim_frame(nm, t, mode), foot, sz)
    u = union512(nm)
    sc = sz / 512
    w, h = (u[2] - u[0]) * sc, (u[3] - u[1]) * sc
    _bubble_at(cv, L, text, t, (L.host_x - w / 2, L.host_foot - h, L.host_x + w / 2, L.host_foot))


def _bubble_at(cv, L, text, t, br, mode="tail"):
    a = clamp(t / 0.2, 0, 1)
    if mode == "hide":
        return
    web = L.fmt == "web"
    px = 32 if web else 38
    f = font(B.F_ROUND, px)
    cy = (br[1] + br[3]) / 2
    tip = (br[2] + 14, cy)
    x0 = tip[0] + 30
    x_max = (L.W - 40) if web else (940 if V4 else 1040)
    maxw = x_max - x0 - 56
    lines = _wrap(f, text, maxw)[:2]
    tw = max(text_w(f, ln) for ln in lines)
    lh = px * 1.3
    h = len(lines) * lh + 26
    x1 = x0 + tw + 56
    rect = (x0, cy - h / 2, x1, cy + h / 2)
    cx = (x0 + x1) / 2
    ty = rect[1] + 13
    tr = (cx - tw / 2, ty, cx + tw / 2, ty + len(lines) * lh)
    draw_bubble(cv, rect, None if mode == "plain" else tip, alpha=a, ink=THEME["ink"], width=4, r=min(THEME["panel_r"], 22), text_rect=tr)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        d.text((cx - text_w(f, ln) / 2, ty + i * lh), ln, font=f, fill=THEME["ink"])
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    cv.paste(lay, (0, 0), lay)


def _arc(cx, cy, r, a0, a1, n=8):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def bubble_polygon(rect, tip, r=24, base=None):
    """圓角矩形＋尾巴 ＝ 單一封閉路徑（尾巴根部直接嵌在邊上，無縫、無雙線）。回傳 (點列, 尾巴 bbox)。"""
    x0, y0, x1, y1 = rect
    h = y1 - y0
    base = base or max(26.0, 0.24 * h)
    r = min(r, h / 2 - 1, (x1 - x0) / 2 - 1)
    if tip is None:
        side = "N"
    elif tip[0] < x0:
        side = "L"
    elif tip[0] > x1:
        side = "R"
    elif tip[1] < y0:
        side = "T"
    else:
        side = "B"
    yc = clamp(tip[1], y0 + r + base / 2, y1 - r - base / 2) if tip else y0
    xc = clamp(tip[0], x0 + r + base / 2, x1 - r - base / 2) if tip else x0
    pts = [(x0 + r, y0)]
    if side == "T":
        pts += [(xc - base / 2, y0), tip, (xc + base / 2, y0)]
    pts += [(x1 - r, y0)] + _arc(x1 - r, y0 + r, r, -90, 0)
    if side == "R":
        pts += [(x1, yc - base / 2), tip, (x1, yc + base / 2)]
    pts += [(x1, y1 - r)] + _arc(x1 - r, y1 - r, r, 0, 90)
    if side == "B":
        pts += [(xc + base / 2, y1), tip, (xc - base / 2, y1)]
    pts += [(x0 + r, y1)] + _arc(x0 + r, y1 - r, r, 90, 180)
    if side == "L":
        pts += [(x0, yc + base / 2), tip, (x0, yc - base / 2)]
    pts += [(x0, y0 + r)] + _arc(x0 + r, y0 + r, r, 180, 270)
    if tip is None:
        return pts, None
    tb = {"L": (tip[0], yc - base / 2, x0, yc + base / 2), "R": (x1, yc - base / 2, tip[0], yc + base / 2),
          "T": (xc - base / 2, tip[1], xc + base / 2, y0), "B": (xc - base / 2, y1, xc + base / 2, tip[1])}[side]
    return pts, tb


def draw_bubble(cv, rect, tip, alpha=1.0, ink=(30, 30, 30), fill=(255, 255, 255), width=4, r=24, text_rect=None):
    """單一路徑台詞泡泡（同一填色、同一條連續描邊）；同時登記外框與檢查項。"""
    pts, tb = bubble_polygon(rect, tip, r)
    SS = 3
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bx0, by0 = int(min(xs)) - 8, int(min(ys)) - 8
    bx1, by1 = int(max(xs)) + 8, int(max(ys)) + 8
    w, h = bx1 - bx0, by1 - by0
    lay = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    sp = [((px - bx0) * SS, (py - by0) * SS) for px, py in pts]
    d.polygon(sp, fill=tuple(fill) + (255,))
    d.line(sp + [sp[0], sp[1]], fill=tuple(ink) + (255,), width=width * SS, joint="curve")
    lay = lay.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    cv.paste(lay, (bx0, by0), lay)
    C.reg("bubble", rect, group="bubble")
    if tb is not None:
        C.reg("bubble_tail", tb, group="bubble")
    if text_rect is not None:
        C.reg("bubble_text", text_rect, group="bubble")
        if tb is not None:
            C.BUBBLE_CHK.append((True, tb, text_rect))
    return tb


class Fn:
    def __init__(self, fn):
        self.fn = fn

    def draw(self, cv, t, shot):
        self.fn(cv, t, shot)
