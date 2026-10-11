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
def _sprite_hook(name, i, foot, size):
    info = B.bibi_index().get(name)
    if not info:
        return
    path = info["frames"][min(i, len(info["frames"]) - 1)]
    C.reg("bibi:" + name, C.sprite_rect(path, foot, size), role=ROLE[0], group="bibi")


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
    if h > wh - 200:
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
        note = "內容高於視窗：取上段並慢滑到底" if r[3] - r[1] > wh - 200 else ""
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


def plan_dwell(rec, op, D, sub, L, pan_, chain=None, no_solve=False):
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
    min_req = min(7.0, 2.0 + 0.35 * units)
    reading = len(sub or "") / 6.5 + 0.3
    need = max(min_req, reading)
    reached, hold = True, 0.0
    taps = [tp for tp in op.taps if not tp["hover"]]
    if mobile:
        if taps and not no_solve and not chain:
            keys, chk, dmin = plan_mobile(rec, op, D, L)
            rec.pan, rec.pan_keys = None, keys
            rec._chk_raw = chk
            need = max(need, dmin)
            units = max(units, 1 + sum(1 for c_ in chk if "高於" in c_[3]) * 2)
            min_req = min(7.0, 2.0 + 0.35 * units)
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
        if taps and not chain:
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
            for (cr_, clab, csrc, tpx) in cont_rs:
                inc_ = _area(_inter_rect(cr_, win)) / max(1.0, _area(cr_))
                CONTENTCHK.append((shot.sid, tpx.get("_lab", ""), clab, round(inc_ * 100, 1), round(shot.dur - (tpx["t"] + 0.95), 2), csrc, ""))
            ww, wh = win[2] - win[0], win[3] - win[1]
            ax, ay, aw, ah = AVAIL_W
            sc = min(aw / ww, ah / wh)
            fw, fh = ww * sc, wh * sc
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
            self.win = (0, y0, ww, min(sh, y0 + wh))
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
        sz = fit_box(name, L.host_w, L.host_h, L.host_size)
        return side_foot(name, sz, L.host_x, L.host_foot), sz

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
            x0, y0 = min(x0, L.host_x - w / 2), min(y0, L.host_foot - h)
            x1, y1 = max(x1, L.host_x + w / 2), max(y1, L.host_foot)
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

    def _seq(self):
        return [tp for tp in self.taps if not tp["hover"] and not tp["dense"]]

    def bubble_mode(self, t):
        """'tail'＝比比在 home（泡泡帶尾巴）；'hide'＝比比飛行中（泡泡淡出）；'plain'＝連續點擊期間比比在框內（只留字卡，不帶尾巴）。"""
        taps = self._seq()
        if not taps:
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
            tl = [(tp["t"], self.land(L, rec.map(tp["cx"], tp["cy"]), 150, rec.rect)) for tp in self._seq()]
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
            tgt = rec.map(tp["cx"], tp["cy"])
            tgt = self.land(L, tgt, ts, rec.rect)
            chained = i > 0 and c - taps[i - 1]["t"] < self.FLY + self.STAY + self.BACK + 0.2
            if chained:
                p = rec.map(taps[i - 1]["cx"], taps[i - 1]["cy"])
                start = self.land(L, p, ts, rec.rect)
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
        ROLE[0] = "bibi"
        cv = R.background(L.fmt).copy()
        for ly in self.layers:
            ly.draw(cv, t, self)
        if self.custom:
            self.custom(cv, t, self)
        if self.kind == "feature":
            self._overlays(cv, t + (1.0 if self.cont else 0.0), L)
        if self.op:
            self.op.draw(cv, t, self)
        if self.kind == "feature":
            host_bubble(cv, L, self, self.sub, t, t + (1.0 if self.cont else 0.0))
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
        else:
            hx = L.pill_xy[0]
            if self.pill:
                pw = R.pill(cv, self.pill, L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
                hx = hx + pw + 30
            L.head_xy = (hx, L.head_y)
            R.headline(cv, L, self.head, t, self.hl)
            footnote4(cv, L)


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
        d.text((x, y), text, font=f, fill=(90, 90, 90))
        C.reg("footnote", (x, y, x + tw, y + 28))


def host_bubble(cv, L, shot, text, t, t_alpha=None):
    """比比的台詞泡泡（網頁、手機共用）：單一路徑，尾巴尖端離比比 14px、只指向比比，文字離尾巴 ≥10px。"""
    if not text or not shot.op:
        return
    nm, br = shot.op.home_rect(L, t)
    _bubble_at(cv, L, text, t if t_alpha is None else t_alpha, br, mode=shot.op.bubble_mode(t))


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
    x_max = (L.W - 40) if web else 1040
    maxw = x_max - x0 - 56
    lines, cur = [], ""
    for ch in text:
        if text_w(f, cur + ch) > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    lines = lines[:2]
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
