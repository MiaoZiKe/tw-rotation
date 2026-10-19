"""功能介紹影片 04：產業地圖 2D／3D 供應鏈圖 —— 素材錄製（沿用 03 的 capture_cal.py 做法，快節奏、成片整支 1.5 倍速）。

沿用 docs/marketing/video_1010/capture.py 的逐格算圖錄影器（page.clock 暫停、每格推進 1/30 秒再截圖，不掉格）、
錄影游標＋點擊漣漪（錄進畫面，點擊中心＝錄影當下量到的元素中心）。一律「未登入訪客」的真實畫面（Andy 10-19），客服鈕照常顯示、鏡頭避開。

本檔另外記錄：
- 每一格的「鏡頭」：目前要介紹的那一塊（選擇器聯集＋留白）在影片像素的外框 → 成片只裁這一塊放大。
- 比比的台詞泡泡（一泡一句、≤14 字）：say() 記下出現秒數；下一句出現前，前一句至少停留 bubble_dur 秒（原片 ≥1.45 秒）。
- 點擊：capture.Act 量到的元素外框與點下座標（clicks）；label 一律由本檔指定（不讀畫面文字，報告裡不會出現個股名稱）。

法遵（growth_plan_1018.md 9-1 第 1 條）：產業鏈圖上的公司名雖屬「依本站族群分類的成分」，影片鏡頭會裁切放大，
為了「不放大、不標色單一家」，錄影的瀏覽器裡把關聯圖公司卡（SVG 文字）、右側清單的代號／名稱／漲跌、剖析圖與 3D 標籤的公司小籤、
零件卡的「做這個的台股」、手機零件抽屜的公司籤一律模糊（BLUR_CSS，只在錄影的瀏覽器裡，不改 site/）。環節、族群名稱照常顯示。

用法（repo 根目錄；site/data 已有 industry_map.json／supply_chain.json 即可，不必整套 build_payload）：
    python docs/marketing/videos/feature_series/04_industry_map/capture_ind.py --dev d [--shots open,guide]
    python docs/marketing/videos/feature_series/04_industry_map/capture_ind.py --dev m
輸出（大檔，放 scratchpad）：<out>/<dev>_<鏡頭>.mp4 ＋ <out>/<dev>_<鏡頭>.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs" / "marketing" / "video_1010"))
import capture as C  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat04"))
FPS = 30
DEVS = {
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=4, is_mobile=True, has_touch=True),
}
PACE = float(os.environ.get("FEAT_PACE", "1.0"))
CHAIN = "ai_server"


def bubble_dur(text: str) -> float:
    """泡泡停留秒數：每泡 ≤14 字；成片 1.5 倍速 → 原片 ≥1.45 秒（1.5 倍後 ≥0.97 秒）。"""
    n = len(text.replace(" ", ""))
    return min(1.9, max(1.45, 0.75 + 0.08 * n))


# 鏡頭：選擇器聯集（只算露在視窗內的部分）
CAM_JS = r"""([sels, pad]) => {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0; const vh = innerHeight, vw = innerWidth;
  const els = []; for (const s of sels) {
    if (s.startsWith('rect:')) { const [x, y, w, h] = s.slice(5).split(',').map(Number); els.push({ getClientRects: () => [1], getBoundingClientRect: () => ({ left: x, top: y, right: x + w, bottom: y + h, width: w, height: h }) }); }
    else if (s.startsWith('all:')) els.push(...document.querySelectorAll(s.slice(4))); else els.push(document.querySelector(s)); }
  for (const e of els) { if (!e || !e.getClientRects().length) continue;
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    const t = Math.max(r.top, 0), b = Math.min(r.bottom, vh), l = Math.max(r.left, 0), rr = Math.min(r.right, vw);
    if (b - t < 2 || rr - l < 2) continue;
    x0 = Math.min(x0, l); y0 = Math.min(y0, t); x1 = Math.max(x1, rr); y1 = Math.max(y1, b); n++; }
  if (!n) return null;
  // 右下角客服鈕：鏡頭避開它（不藏它）。區塊右緣碰到客服鈕那一欄時，下緣收到客服鈕上方，
  // 免得合成時為了避開客服鈕把區塊右側裁掉（寧可只拍到客服鈕以上那一段，介紹的區塊另外捲進來）。
  const fab = [...document.querySelectorAll('#supFab, .supfab, .bibiring')].find(e => e.getClientRects().length);
  if (fab) { const f = fab.getBoundingClientRect(); if (x1 + pad > f.left - 6 && y1 + pad > f.top - 6 && f.top - 14 - pad > y0 + 80) y1 = Math.min(y1, f.top - 14 - pad); }
  return [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad]; }"""

FAB_JS = r"""() => { const es = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring, #bibiStage, .bibiwrap')]
  .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && +getComputedStyle(e).opacity > 0.05);
  if (!es.length) return null; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  es.forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 2) return; x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
  return x1 > x0 ? [x0, y0, x1 - x0, y1 - y0] : null; }"""

# 公司名／代號／股價模糊（只在錄影的瀏覽器裡）
BLUR_CSS = (
    "#relSec .co text,#chainMap .co text{filter:blur(4.5px)!important}"
    ".rlco .cd,.rlco .nm,.rlco .chg,.rlfo{filter:blur(5px)!important;display:inline-block}"
    ".chips3d a,.chips3d span,.chips3d b,.chips3d i,.dgchips a,.dgchips span,.mchips a,.pc-co a,a.lk-stock,"
    "#v-industry a[href^='#stock/'],#mSheet a[href^='#stock/'],#coBox h3,.pc-co>b,.pc-none,.mpcco,.mpcnone{filter:blur(5px)!important}"
)
BLUR_JS = r"""
(() => { const css = %s;
  const go = () => { const st = document.createElement('style'); st.id = '__blurco'; st.textContent = css; (document.head || document.documentElement).appendChild(st); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(BLUR_CSS)


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框（影片像素）。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []
        self.fabs: list = []

    def frame(self):
        super().frame()
        if not self.on:
            return
        a = self.act
        spec = a.cam_spec
        r = None
        if spec and spec[0] == "sel":
            try:
                r = self.pg.evaluate(CAM_JS, [spec[1], spec[2]])
            except Exception:  # noqa: BLE001
                r = None
        if r is None:
            r = [0, 0, a.vw, a.vh]
        self.cams.append([a.cam_id] + [round(v * a.dsf, 1) for v in r])
        try:
            fb = self.pg.evaluate(FAB_JS)
        except Exception:  # noqa: BLE001
            fb = None
        self.fabs.append([round(v * a.dsf, 1) for v in fb] if fb else None)


class A(C.Act):
    def __init__(self, pg, mob, vw, vh):
        super().__init__(pg, mob)
        self.vw, self.vh = vw, vh
        self.cam_spec = None
        self.cam_id = 0
        self.says: list = []
        self.marks: list = []
        self.say_t = None
        self.say_need = 0.0

    def cam(self, sels, pad=12, label=""):
        self.settle()   # 前一句泡泡講完（最短停留）才換鏡頭，畫面與泡泡同步
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad)
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label or ",".join(sels)])

    def cam_view(self, label="viewport"):
        self.settle()
        self.cam_spec = None
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label])

    def idle(self, ms):
        """原地小幅移動游標（不停格），ms 毫秒。"""
        n = max(1, round(ms * FPS / 1000))
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            k = i / n
            self._put(x0 + 10 * math.sin(k * math.pi * 2) * (1 - k * 0.3), y0 + 6 * math.sin(k * math.pi * 4))
            self.frame()
        self._put(x0, y0)

    def settle(self):
        if self.say_t is not None:
            rest = self.say_need - (self.t - self.say_t)
            if rest > 0.02:
                self.idle(rest * 1000)

    def say(self, text, act="talk_explain_v2"):
        assert len(text.replace(" ", "")) <= 14, text
        self.settle()
        first = not self.says
        self.says.append({"t": round(self.t, 3), "text": text, "act": act})
        # 成片合成時：每段第一泡晚 0.25 秒出現（交叉淡化）、每泡提早 0.06 秒收 → 錄影這邊先補足，泡泡實際停留仍 ≥ bubble_dur
        self.say_t, self.say_need = self.t, bubble_dur(text) + 0.08 + (0.27 if first else 0.0)

    def click(self, sel, ms=380, pause=150, dx=0.5, dy=0.5, label=""):
        n0 = len(self.targets)
        ok = super().click(sel, ms, pause, dx, dy, label)
        if ok and len(self.targets) > n0:
            tg = self.targets[-1]
            if label:
                tg["label"] = label
            if tg.get("selector") in ("svg", "canvas") or (tg.get("selector") or "").startswith("svg"):
                # SVG 裡的環節標題：elementFromPoint 往上找會停在整張 <svg>；改量被點的那個 <g> 本身的外框（點下那一刻）
                r = self.pg.evaluate(C.RECT_JS, sel)
                if r:
                    tg["rect_center"] = self._vpt(r[0] + r[2] / 2, r[1] + r[3] / 2)
                    tg["measured_by"] = "被點元素外框（getBoundingClientRect）"
        return ok

    def click_now(self, sel, label, ms=380, pause=150, dx=0.5, dy=0.5):
        """不捲動、量當下位置點（3D 標籤每幾格就重排，box() 的「等穩定」會等不到）。"""
        r = self.pg.evaluate(C.RECT_JS, sel)
        if not r:
            self.note(f"點不到 {sel}")
            return False
        x, y = r[0] + r[2] * dx, r[1] + r[3] * dy
        self.move(x, y, ms)
        self.wait(pause)
        for _ in range(8):   # 標籤被游標滑過會展開（變高）、每幾格重排 → 跟著最新外框的中心走，連續兩次不動才點
            r2 = self.pg.evaluate(C.RECT_JS, sel)
            if not r2:
                break
            x2, y2 = r2[0] + r2[2] * dx, r2[1] + r2[3] * dy
            if abs(x2 - x) < 1 and abs(y2 - y) < 1:
                break
            x, y = x2, y2
            self.move(x, y, 130)
        self.note(f"點 {label}")
        self.click_xy(x, y, 1, 0, expect=sel)
        self.targets[-1]["label"] = label
        r3 = self.pg.evaluate(C.RECT_JS, sel)
        if r3 and r3[2] > 0:
            self.targets[-1]["rect_center"] = self._vpt(r3[0] + r3[2] / 2, r3[1] + r3[3] / 2)
            self.targets[-1]["measured_by"] = "被點元素外框（點下那一刻）"
        return True

    def hover(self, sel, ms=420, dx=0.5, dy=0.5):
        return super().hover(sel, ms, dx, dy)

    def wait(self, ms):
        return super().wait(ms * PACE)

    def note(self, s: str):
        super().note(s)
        if os.environ.get("FEAT_VERBOSE"):
            print(self.log[-1], flush=True)

    def mark(self, name):
        self.marks.append([round(self.t, 3), "mark", name])

    def hscroll(self, sel, to_x=None, by=None, ms=900):
        """橫向捲動容器（逐格）。"""
        x0, mx = self.pg.evaluate("(s) => { const e = document.querySelector(s); return e ? [e.scrollLeft, e.scrollWidth - e.clientWidth] : [0, 0]; }", sel)
        x1 = to_x if to_x is not None else x0 + (by or 0)
        x1 = max(0, min(mx, x1))
        n = max(1, round(ms * FPS / 1000))
        for i in range(1, n + 1):
            k = i / n
            e = 2 * k * k if k < .5 else 1 - (-2 * k + 2) ** 2 / 2
            self.pg.evaluate("([s, x]) => { const el = document.querySelector(s); if (el) el.scrollLeft = x; }", [sel, x0 + (x1 - x0) * e])
            self.frame()

    def finger_hscroll(self, sel, by, ms=900):
        """手機：手指在容器上往左滑（游標跟著走，容器跟著捲）。"""
        r = self.pg.evaluate(C.RECT_JS, sel)
        if not r:
            return
        cx, cy = r[0] + r[2] * 0.6, min(r[1] + r[3] * 0.5, self.vh * 0.7)
        self.move(cx, cy, 300)
        x0 = self.pg.evaluate("(s) => document.querySelector(s).scrollLeft", sel)
        n = max(1, round(ms * FPS / 1000))
        mx = self.pg.evaluate("(s) => { const e = document.querySelector(s); return e.scrollWidth - e.clientWidth; }", sel)
        x1 = max(0, min(mx, x0 + by))
        d = x1 - x0
        for i in range(1, n + 1):
            k = i / n
            e = 2 * k * k if k < .5 else 1 - (-2 * k + 2) ** 2 / 2
            self.pg.evaluate("([s, x]) => { const el = document.querySelector(s); if (el) el.scrollLeft = x; }", [sel, x0 + d * e])
            self._put(cx - d * e * 0.5, cy)
            self.frame()
        self.x, self.y = cx - d * 0.5, cy


# ------------------------------------------------------------------ 共用
def goto(pg, hash_, wait=4500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(400)


def scroll_to(pg, sel, off=70):
    y = pg.evaluate("([s,o]) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - o : 0; }", [sel, off])
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(600)


def has3d(pg):
    return pg.evaluate("() => document.querySelectorAll('#prod3d canvas').length > 0")


def warm3d(pg):
    """先切一次 3D 把 three.js 與模型載好（不錄），再切回 2D；正式錄影時再按一次 3D 會立刻出來。"""
    pg.evaluate("() => document.querySelector('#dg3d button[data-dm=\"3d\"]').click()")
    for _ in range(60):
        if has3d(pg):
            break
        pg.wait_for_timeout(500)
    pg.wait_for_timeout(2500)
    pg.evaluate("() => document.querySelector('#dg3d button[data-dm=\"2d\"]').click()")
    pg.wait_for_timeout(1500)


DG_CAM = ["#prodDiagram .dgcol.l", "#prodDiagram .dgcol.r", "#prodDiagram svg.dg"]   # 2D 剖析圖：左右編號卡＋中間圖
REL_CAM = ["all:#relSec .segbox", "#relStick"]   # 關聯圖：所有環節框（＋右側選取清單）；整張連標題列比畫面框比例高，標題列不入框免得上下被裁


def dgc(side, k):
    """2D 剖析圖左（l）／右（r）欄第 k 張編號卡（data-anc 會隨重畫遞增，不能寫死）。"""
    return f"#prodDiagram .dgcol.{side} .dgc:nth-child({k})"


def lbl(no):
    return f'.lbl3d[data-dgno="{no}"]'


def seg(s):
    return f'#relSec .segtitle[data-seg="{s}"]'


def chain_btn(c):
    return f'#chainSwitch button[data-c="{c}"]'


# ------------------------------------------------------------------ 網頁版鏡頭
def d_open(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#prodDiagram .dgcanvas", 64)
    start()
    a.cam(DG_CAM, 40, "AI 伺服器 2D 剖析圖")
    a.move(800, 500, 400)
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2")
    a.hover(dgc('r', 1), 600)
    a.hover(dgc('r', 2), 600)
    a.say("從上游到下游，台廠在哪段？", "tilt")
    a.hover(dgc('r', 6), 600)
    a.idle(400)
    a.say("產業地圖，一張圖看懂", "folder")
    a.hover(dgc('r', 7), 600)
    a.idle(500)
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    # 左側選單「今日市場」標題到「市場明細」（上下緣都落在項目之間的空白，不切到字；座標為 1600×900 桌機版面實測）
    a.cam(["rect:12,172,330,508"], 0, "選單：族群與個股")
    a.say("看左側「族群與個股」", "point_r_v2")
    a.hover('#tabs .tab[data-view="overview"]', 500)
    a.hover('#tabs .tab[data-view="market"]', 500)
    a.say("點「產業地圖」", "magnifier")
    a.click('#tabs .tab[data-view="industry"]', label="選單：產業地圖")
    a.wait(1800)
    a.cam(["#chainSwitch", "#v-industry .card"], 6, "進到產業地圖")
    a.idle(600)
    a.settle()


def d_chain(pg, a, start):
    goto(pg, "#industry")
    start()
    a.cam(["#chainSwitch", "#v-industry .card"], 6, "產業鏈分頁")
    a.say("上方分頁，切換產業鏈", "point_r_v2")
    for c, lab in (("semiconductor", "產業鏈：半導體"), ("electronics", "產業鏈：一般電子"), (CHAIN, "產業鏈：AI 伺服器")):
        a.click(chain_btn(c), label=lab)
        a.wait(1100)
        if c == "semiconductor":
            a.say("每條鏈都有產品剖析圖", "talk_explain_v2")
    a.until("() => document.querySelectorAll('#prodDiagram .dgcol.r .dgc').length >= 4", 6000)
    a.wait(300)
    a.cam_view("捲動")
    a.scroll_to_el("#prodDiagram .dgcanvas", 64, 700)
    a.cam(DG_CAM, 40, "剖析圖編號卡")
    a.say("點編號卡，圖上零件跟著亮", "spotlight")
    for side, k, lab in (("l", 1, "編號卡 01"), ("l", 4, "編號卡 04"), ("r", 4, "編號卡 09")):
        a.click(dgc(side, k) + " .bd b", label=lab)
        a.wait(1000)
    a.idle(300)
    a.settle()


def fold_dg(pg):
    """桌機：先把上方剖析圖收起（不錄），關聯圖整張能捲到客服鈕上方。"""
    pg.evaluate("() => document.querySelector('#dgFold').click()")
    pg.wait_for_timeout(1000)


def d_rel(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    fold_dg(pg)
    scroll_to(pg, "#relSec", 64)
    start()
    a.cam(REL_CAM, 6, "供應鏈關聯圖")
    a.say("供應鏈關聯圖：誰供貨給誰", "talk_explain_v2")
    a.move(900, 450, 500)
    a.idle(300)
    a.say("點環節，上下游一起亮", "point_r_v2")
    for s, lab in (("foundry", "環節：晶圓代工"), ("abf_pcb", "環節：IC 載板"), ("optical", "環節：光通訊模組")):
        a.click(seg(s), label=lab)
        a.wait(1000)
        if s == "abf_pcb":
            a.say("右邊列出對應族群", "folder")
    a.say("滑過公司，看連線去向", "magnifier")
    for s in ("thermal", "power", "assembly"):
        a.hover(f'#relSec .co[data-segment="{s}"]', 450)
        a.wait(650)
    a.idle(300)
    a.settle()


def d_3d(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    warm3d(pg)
    scroll_to(pg, "#dgTools", 120)
    a.x, a.y = 1300, 160
    start()
    a.cam(["#dg3d", "#dgBody"], 6, "2D／3D 切換")
    a.say("切到 3D，立體剖析圖", "3dglasses")
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.wait(600)
    a.scroll_to_el("#prod3d", 90, 700)
    a.cam(["#prod3d"], 4, "3D 剖析圖")
    r = a.box("#prod3d canvas", scroll=False)
    cx, cy, w = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2, r["width"]
    a.say("拖曳就能 360 度旋轉", "hop_r")
    a.drag(cx - w * 0.14, cy, cx + w * 0.16, cy + 10, 1500)
    a.wait(300)
    a.drag(cx + w * 0.12, cy - 10, cx - w * 0.1, cy + 14, 1400)
    a.wait(300)
    a.say("移入展開、移出收攏", "reveal")
    a.move(cx, 64, 600)               # 游標移出圖框 → 收攏
    a.wait(900)
    a.move(cx - 40, cy, 600)          # 移回圖框 → 展開
    a.wait(1100)
    a.say("點零件，說明與環節連動", "magnifier")
    for no, lab in (("06", "零件：HBM 記憶體"), ("12", "零件：電源櫃"), ("15", "零件：ToR 交換器")):   # 最後點交換器：下方零件卡（進料／出貨）不含外商客戶名
        a.click_now(lbl(no), lab)
        a.wait(1300)
    a.cam_view("捲動")
    a.scroll_to_el("#partCard", 330, 700)
    a.cam(["#partCard"], 8, "零件卡：進料、出貨")
    a.say("進料、出貨一次看", "pointer_r")
    a.hover("#partCard .pc-row:nth-of-type(2)", 500, 0.3)
    a.hover("#pcSeg", 500)
    a.idle(500)
    a.settle()


def d_end(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    fold_dg(pg)
    scroll_to(pg, "#relSec", 64)
    start()
    a.cam(REL_CAM, 6, "總覽")
    a.say("上下游、台廠位置一次看", "proud_shine")
    a.move(700, 500, 900)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(1000, 600, 900)
    a.settle()


# ------------------------------------------------------------------ 手機版鏡頭（390 寬 m4 版面）
def m_open(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#dgBody", 70)
    start()
    a.cam(["#dgBody"], 6, "AI 伺服器 2D 剖析圖")
    a.move(200, 500, 400)
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2")
    a.idle(900)
    a.say("從上游到下游，台廠在哪段？", "tilt")
    a.idle(900)
    a.say("產業地圖，一張圖看懂", "folder")
    a.idle(900)
    a.settle()


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="industry"]', '.m4item[data-v="overview"]'], 10, "選單抽屜")
    a.say("點「產業地圖」", "magnifier")
    a.click('.m4item[data-v="industry"]', label="選單：產業地圖")
    a.wait(1700)
    a.cam(["#chainSwitch", "#v-industry .card"], 6, "進到產業地圖")
    a.idle(600)
    a.settle()


def m_chain(pg, a, start):
    goto(pg, "#industry")
    start()
    a.cam(["#chainSwitch", "#v-industry .card"], 6, "產業鏈分頁")
    a.say("上方分頁，切換產業鏈", "point_ur_v2")
    for c, lab in (("semiconductor", "產業鏈：半導體"), ("electronics", "產業鏈：一般電子"), (CHAIN, "產業鏈：AI 伺服器")):
        pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.scrollIntoView({inline: 'center', block: 'nearest', behavior: 'instant'}); }", chain_btn(c))
        a.click(chain_btn(c), label=lab)
        a.wait(1100)
        if c == "semiconductor":
            a.say("每條鏈都有產品剖析圖", "talk_explain_v2")
    a.until("() => !!document.querySelector('#dgBody .mnum')", 6000)
    a.cam_view("捲動")
    a.scroll_to_el("#dgBody", 70, 700)
    a.cam(["#dgBody"], 6, "剖析圖編號")
    a.say("點編號看零件說明", "magic_frame")
    for no in ("01", "07"):
        sel = f'#dgBody .mnum[data-no="{no}"]'
        a.click_now(sel, f"編號 {no}")
        a.wait(1300)
        pg.evaluate("() => { const b = document.getElementById('mSheetBack'); if (b) b.click(); }")
        a.wait(400)
    a.settle()


def m_rel(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#relSec", 64)
    start()
    a.cam(REL_CAM, 6, "供應鏈關聯圖")
    a.say("供應鏈關聯圖：誰供貨給誰", "talk_explain_v2")
    a.finger_hscroll("#chainMap", -260, 1100)
    a.wait(300)
    a.finger_hscroll("#chainMap", 260, 1100)
    a.say("點環節，展開台廠與連線", "point_dr_v2")
    for s, lab in (("optical", "環節：光通訊模組"), ("switch", "環節：交換器"), ("power", "環節：電源")):
        a.cam([seg(s), "#chainMap"], 6, lab)
        a.click(seg(s), label=lab)
        a.wait(1300)
        if s == "switch":
            a.say("上下游連線跟著亮", "magnifier")
    a.idle(300)
    a.settle()


def m_3d(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    warm3d(pg)
    scroll_to(pg, "#dgTools", 80)
    a.x, a.y = 200, 300
    start()
    a.cam(["#dg3d", "#dgBody"], 6, "2D／3D 切換")
    a.say("切到 3D，立體剖析圖", "3dglasses")
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.wait(600)
    a.scroll_to_el("#prod3d", 64, 700)
    a.cam(["#prod3d"], 4, "3D 剖析圖")
    r = a.box("#prod3d canvas", scroll=False)
    cx, cy, w = r["x"] + r["width"] / 2, r["y"] + min(r["height"], 520) / 2, r["width"]
    a.say("手指拖曳就能旋轉", "hop_r")
    a.drag(cx - w * 0.2, cy, cx + w * 0.22, cy + 6, 1400)
    a.wait(300)
    a.drag(cx + w * 0.15, cy - 30, cx - w * 0.15, cy + 40, 1300)
    a.wait(300)
    a.say("點空白處：展開／收攏", "reveal")
    a.click_xy(cx, r["y"] + 30, 400, 150)
    a.targets[-1].update(label="3D 空白處（展開）", blank=True)
    a.wait(1300)
    a.click_xy(cx, r["y"] + 30, 300, 150)
    a.targets[-1].update(label="3D 空白處（收攏）", blank=True)
    a.wait(1200)
    a.say("點編號，說明跟著換", "magnifier")
    for no, lab in (("06", "零件：HBM 記憶體"), ("12", "零件：電源櫃"), ("15", "零件：ToR 交換器")):
        a.cam(["#prod3d", "#mSheet"], 4, lab)
        a.click_now(f'#prod3d .mnum[data-no="{no}"]', lab)
        a.wait(1500)
        if no == "06":
            a.say("對應環節、台廠都列好", "pointer_r")
    a.settle()


def m_end(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#relSec", 64)
    start()
    a.cam(REL_CAM, 6, "總覽")
    a.say("上下游、台廠位置一次看", "proud_shine")
    a.scroll(by=120, ms=1400)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.scroll(by=-120, ms=1400)
    a.settle()


TALL_D = {"rel": 1000, "end": 1000}
D_SHOTS = {"open": d_open, "guide": d_guide, "chain": d_chain, "rel": d_rel, "3d": d_3d, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "chain": m_chain, "rel": m_rel, "3d": m_3d, "end": m_end}


def run(dev, shots, out, port):
    cfg = DEVS[dev]
    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    import datetime as _dt
    from playwright.sync_api import sync_playwright
    reg = D_SHOTS if dev == "d" else M_SHOTS
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            for sid in shots or list(reg):
                cfg = dict(DEVS[dev])
                if dev == "d" and sid in TALL_D:   # 關聯圖整張比 900 高：這幾鏡用較高的視窗，整張圖都在客服鈕上方
                    cfg["viewport"] = {"width": 1600, "height": TALL_D[sid]}
                if dev == "d" and sid == "3d":     # 3D 畫布在軟體算圖（swiftshader）下 2 倍像素一格要 2 秒以上：這一鏡用 1 倍（裁切區約 1430px 寬，放進 1650px 畫面框只放大 1.15 倍）
                    cfg["device_scale_factor"] = 1
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                ctx.clock.install(time=_dt.datetime.now(tz=_dt.timezone.utc))
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                ctx.add_init_script(BLUR_JS)       # 法遵：公司名／代號／股價模糊
                ctx.add_init_script("try{localStorage.removeItem('tw.chainFold');localStorage.removeItem('tw.dg3d.exp')}catch(e){}")
                if dev == "d" and sid != "guide":   # 桌機左側導覽收成圖示列：內容區更寬
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (900, 500) if dev == "d" else (370, 160)
                a.dsf = cfg["device_scale_factor"]
                rec = Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)   # 最後一泡：段尾交叉淡化 0.4 秒前仍要停滿
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]] if (sid == "guide" or dev == "m") else pg.evaluate("() => { const e = document.querySelector('#v-industry'); const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
                    r.update(fabs=rec.fabs, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
                except Exception as exc:  # noqa: BLE001
                    rec.on = False
                    print(sid, "失敗", exc)
                    print("\n".join(a.log[-12:]))
                    shutil.rmtree(out / f".tmp_{dev}_{sid}", ignore_errors=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8814)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
