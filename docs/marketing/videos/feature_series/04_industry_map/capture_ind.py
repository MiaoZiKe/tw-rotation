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


# 鏡頭（v2）：回傳 {focus：介紹區塊＝選擇器聯集「不裁到視窗」的完整外框＋留白（量的是元素本身，露在視窗外的部分也算進去，
#   合成時拿它檢查有沒有被鏡頭裁到）、cam：取景框（有給 frame 就用 frame，否則＝focus）、edges：不准被框邊切過的卡片外框}。
# 特殊選擇器 dgsel：2D 剖析圖目前被點的編號卡＋它對應的那一個零件（.sel-part 與含錨點的 g.sel[data-part]）。
CAM_JS = r"""([sels, pad, frame, edges]) => {
  const vh = innerHeight, vw = innerWidth;
  const vis = (r) => r.width >= 2 && r.height >= 2 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
  const rectOf = (s) => { const [x, y, w, h] = s.slice(5).split(',').map(Number); return { left: x, top: y, right: x + w, bottom: y + h, width: w, height: h }; };
  const dgsel = () => { const sp = [...document.querySelectorAll('#prodDiagram .sel-part')]; const anc = sp.filter(e => e.tagName.toLowerCase() === 'g');
    const parts = [...document.querySelectorAll('#prodDiagram svg.dg g.sel[data-part]')].filter(g => anc.some(a => { const r = a.getBoundingClientRect(), q = g.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2; return cx >= q.left - 4 && cx <= q.right + 4 && cy >= q.top - 4 && cy <= q.bottom + 4; }));
    return sp.concat(parts).map(e => e.getBoundingClientRect()); };
  const dgpre = (anc) => { const a = document.querySelector(`#prodDiagram svg.dg g.anc[data-for="${anc}"]`); if (!a) return [];
    const r = a.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const parts = [...document.querySelectorAll('#prodDiagram svg.dg g[data-part]')].map(g => g.getBoundingClientRect())
      .filter(q => cx >= q.left - 4 && cx <= q.right + 4 && cy >= q.top - 4 && cy <= q.bottom + 4 && q.width < 600);
    parts.sort((p, q) => p.width * p.height - q.width * q.height);
    return [r].concat(parts.slice(0, 1)); };
  const rects = (list) => { const out = []; for (const s of list) {
      if (s.startsWith('rect:')) out.push(rectOf(s));
      else if (s === 'dgsel') out.push(...dgsel());
      else if (s.startsWith('dgpre:')) out.push(...dgpre(s.slice(6)));
      else if (s.startsWith('all:')) document.querySelectorAll(s.slice(4)).forEach(e => { if (e.getClientRects().length) out.push(e.getBoundingClientRect()); });
      else { const e = document.querySelector(s); if (e && e.getClientRects().length) out.push(e.getBoundingClientRect()); } }
    return out.filter(vis); };
  const uni = (rs, p) => { if (!rs.length) return null; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    rs.forEach(r => { x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
    return [x0 - p, y0 - p, x1 - x0 + 2 * p, y1 - y0 + 2 * p]; };
  const focus = uni(rects(sels), pad);
  const cam = frame ? uni(rects([frame]), 0) : focus;
  const ed = (edges && edges.length) ? rects(edges).map(r => [r.left, r.top, r.width, r.height]) : [];
  return { focus, cam, edges: ed }; }"""

FAB_JS = r"""() => { const es = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring, #bibiStage, .bibiwrap')]
  .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && +getComputedStyle(e).opacity > 0.05)
  .filter(e => { const r = e.getBoundingClientRect(); const h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !h || h === e || e.contains(h) || h.contains(e) || h.id === '__vc' || (h.closest && h.closest('#__vc')); });   // 被抽屜蓋住（看不到）的客服鈕不算入鏡
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
        self.edges: list = []
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
                r = self.pg.evaluate(CAM_JS, [spec[1], spec[2], spec[3], spec[5]])
            except Exception:  # noqa: BLE001
                r = None
        k = a.dsf
        sc = lambda v: [round(x * k, 1) for x in v] if v else None   # noqa: E731
        if r is None or r.get("cam") is None:
            self.cams.append([a.cam_id, 0, 0, a.vw * k, a.vh * k, 0, None, 0])   # 整個視窗（捲動、抽屜轉場），不檢查裁切
            self.edges.append([])
        else:
            self.cams.append([a.cam_id] + sc(r["cam"]) + [round((spec[4] or 0) * k, 1), sc(r["focus"]), 1 if spec[6] else 0])
            self.edges.append([sc(e) for e in r["edges"]])
        try:
            fb = self.pg.evaluate(FAB_JS)
        except Exception:  # noqa: BLE001
            fb = None
        self.fabs.append([round(v * k, 1) for v in fb] if fb else None)


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

    def cam(self, sels, pad=12, label="", frame=None, minw=None, edges=None, zoom=False):
        """sels＝介紹的區塊；frame＝取景框（不給就是區塊本身）；minw＝取景最小寬（css，推近拍用）；edges＝不准被框邊切過的卡片；zoom＝推近拍（報告算佔畫面寬）。"""
        self.settle()   # 前一句泡泡講完（最短停留）才換鏡頭，畫面與泡泡同步
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad, frame, minw, list(edges or []), zoom)
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
        b = self.box(sel)
        if not b:
            self.note(f"點不到 {sel}")
            return False
        x, y = b["x"] + b["width"] * dx, b["y"] + b["height"] * dy
        self.note(f"點 {label or sel}")
        self.move(x, y, ms)
        self.wait(pause)
        pre = self.pg.evaluate(C.RECT_JS, sel)   # 按下前一刻量被點元素本身的外框（SVG 環節標題點了會展開、位置會變）
        self.click_xy(x, y, 1, 0, expect=sel)
        tg = self.targets[-1]
        if label:
            tg["label"] = label
        if pre and pre[2] > 0:
            tg["rect_center"] = self._vpt(pre[0] + pre[2] / 2, pre[1] + pre[3] / 2)
            tg["measured_by"] = "被點元素外框（按下前一刻）"
        return True

    def click_now(self, sel, label, ms=380, pause=150, dx=0.5, dy=0.5, dy_px=None, approach=None):
        """不捲動、量當下位置點（3D 標籤每幾格就重排，box() 的「等穩定」會等不到）。dy_px：從元素上緣往下幾 px（標題列）。"""
        r = self.pg.evaluate(C.RECT_JS, sel)
        if not r:
            self.note(f"點不到 {sel}")
            return False
        if dy_px is not None:
            dy = min(0.5, dy_px / max(r[3], 1))
        x, y = r[0] + r[2] * dx, r[1] + r[3] * dy
        if approach:   # 先水平移到元素旁邊（3D 標籤會在游標滑過時展開、蓋住隔壁標籤 → 只從畫布那一側水平進場）
            self.move(r[0] - 60 if approach == "left" else r[0] + r[2] + 60, y, int(ms * 0.7))
            ms = int(ms * 0.6)
        self.move(x, y, ms)
        self.wait(pause)
        for _ in range(14):   # 標籤被游標滑過會展開（變高）、每幾格重排 → 跟著最新外框走；位置不動、而且最上層確實是目標才點
            r2 = self.pg.evaluate(C.RECT_JS, sel)
            if not r2:
                break
            if dy_px is not None:
                dy = min(0.5, dy_px / max(r2[3], 1))
            x2, y2 = r2[0] + r2[2] * dx, r2[1] + r2[3] * dy
            if abs(x2 - x) >= 1 or abs(y2 - y) >= 1:
                x, y = x2, y2
                self.move(x, y, 130)
                continue
            hit = self.pg.evaluate("([s, x, y]) => { const e = document.elementFromPoint(x, y); const t = document.querySelector(s); return !!(e && t && (e === t || t.contains(e))); }", [sel, x, y])
            if hit:
                break
            self.idle(120)   # 最上層不是目標（被隔壁展開的標籤蓋住）：等一下再量
        self.note(f"點 {label}")
        self.click_xy(x, y, 1, 0, expect=sel)
        self.targets[-1]["label"] = label
        # 中心誤差以「按下前一刻」量到的外框為準（capture.record_target）；點下後標籤會展開說明而變高，不可事後再量
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


M_EDGE = ["all:#relSec .segbox"]   # 手機關聯圖：環節卡不准被框邊切過（合成時逐格檢查）
DG_CAM = ["#prodDiagram .dgcol.l", "#prodDiagram .dgcol.r", "#prodDiagram svg.dg"]   # 2D 剖析圖：左右編號卡＋中間圖（全圖定位用）
REL_CAM = ["all:#relSec .segbox", "#relStick"]   # 關聯圖：所有環節框（全圖定位用）
M_TOP_FRAME = "rect:0,66,390,560"   # 手機產業地圖頂部：產業鏈分頁列＋圖表上半（取景固定，切產業鏈時鏡頭不晃）
ZMIN = 440   # 桌機推近拍的最小取景寬（css）：錄影 3 倍像素 → 1320px 放進 1650px 畫面框只放大 1.25 倍，字仍清楚


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
def dg_card(a, side, k, label, hold=1100):
    """2D 剖析圖：鏡頭先推到這張編號卡 → 點它 → 鏡頭對到「編號卡＋它對應的零件」（推近拍，至少佔畫面寬 70%）。"""
    card = dgc(side, k)
    anc = a.pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.dataset.anc : null; }", card)
    a.cam([card, f"dgpre:{anc}"], 16, f"推近：{label}", minw=ZMIN, zoom=True)   # 點之前就對到「編號卡＋它在圖上的零件」
    a.click(card + " .bd b", label=label)
    a.wait(250)
    a.cam(["dgsel"], 16, f"{label}＋對應零件", minw=ZMIN, zoom=True)
    a.wait(hold)


def d_open(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#prodDiagram .dgcanvas", 96)
    start()
    a.cam(DG_CAM, 8, "AI 伺服器 2D 剖析圖（全圖定位）")
    a.move(1200, 520, 400)
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2")
    a.idle(1100)
    a.say("從上游到下游，台廠在哪段？", "tilt")
    dg_card(a, "r", 8, "編號卡 13 雲端業者")
    a.say("產業地圖，一張圖看懂", "folder")
    dg_card(a, "l", 5, "編號卡 05 板上供電")
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    # 左側選單「今日市場」標題到「市場明細」（上下緣都落在項目之間的空白，不切到字；座標為 1600×900 桌機版面實測）
    a.cam(["rect:22,182,310,488"], 0, "選單：族群與個股", frame="rect:12,172,330,508")
    a.say("看左側「族群與個股」", "point_r_v2")
    a.hover('#tabs .tab[data-view="overview"]', 500)
    a.hover('#tabs .tab[data-view="market"]', 500)
    a.say("點「產業地圖」", "magnifier")
    a.click('#tabs .tab[data-view="industry"]', label="選單：產業地圖")
    a.wait(1800)
    a.cam(["all:#chainSwitch button"], 4, "進到產業地圖")
    a.idle(600)
    a.settle()


def d_chain(pg, a, start):
    goto(pg, "#industry")
    start()
    a.cam(["all:#chainSwitch button"], 4, "產業鏈分頁（全圖定位）")
    a.say("上方分頁，切換產業鏈", "point_r_v2")
    a.idle(900)
    # 推近：分頁列左半（被點的三個分頁）＋下方圖表上半（切產業鏈時跟著換）；取景固定不跟版面晃
    a.cam(["rect:88,84,700,330"], 0, "推近：產業鏈分頁＋圖表", minw=ZMIN, zoom=True)
    for c, lab in (("semiconductor", "產業鏈：半導體"), ("electronics", "產業鏈：一般電子"), (CHAIN, "產業鏈：AI 伺服器")):
        a.click(chain_btn(c), label=lab)
        a.wait(1100)
        if c == "semiconductor":
            a.say("每條鏈都有產品剖析圖", "talk_explain_v2")
    a.until("() => document.querySelectorAll('#prodDiagram .dgcol.r .dgc').length >= 4", 6000)
    a.wait(300)
    a.cam_view("捲動")
    a.scroll_to_el("#prodDiagram .dgcanvas", 96, 700)
    a.cam(DG_CAM, 8, "剖析圖（全圖定位）")
    a.say("點編號卡，圖上零件跟著亮", "spotlight")
    a.idle(1000)
    for side, k, lab in (("l", 1, "編號卡 01 ToR 交換器"), ("l", 3, "編號卡 03 電源櫃"), ("r", 5, "編號卡 10 光通訊")):
        dg_card(a, side, k, lab, 1000)
    a.idle(200)
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
    a.cam(REL_CAM, 6, "供應鏈關聯圖（全圖定位）")
    a.say("供應鏈關聯圖：誰供貨給誰", "talk_explain_v2")
    a.move(900, 450, 500)
    a.idle(700)
    first = True
    for s, lab in (("abf_pcb", "環節：IC 載板"), ("power", "環節：電源"), ("switch", "環節：交換器")):   # v3：第一環換成有台廠的 IC 載板（對應族群清單有內容）
        box = f'#relSec .segbox[data-seg="{s}"]'
        b = pg.evaluate(C.RECT_JS, box)
        tip_area = f"rect:{b[0]:.0f},{b[1]:.0f},{min(480, 1580 - b[0]):.0f},{b[3] + 130:.0f}"   # 環節框＋右下方即將浮出上下游說明的位置
        a.cam([box, tip_area], 14, f"推近：{lab}", minw=ZMIN, zoom=True)
        if first:
            a.say("點環節，看上下游是誰", "point_r_v2")
        a.click(seg(s), label=lab)
        a.wait(250)
        a.cam([box, "#relTip"], 14, f"{lab}＋上下游說明", minw=ZMIN, zoom=True)   # 被點環節＋浮出的上游／下游說明
        a.wait(1000)
        if first:
            a.say("旁邊列出對應族群", "folder")
        a.cam(["#relStick"], 14, f"{lab}：對應族群清單", minw=ZMIN, zoom=True)   # 選取清單（對應族群）
        a.wait(1000)
        first = False
    a.idle(200)
    a.settle()


D3_VIEW = {"width": 1280, "height": 800}   # v3：3D 這一鏡用 1280×800、2 倍像素錄 —— 機櫃與兩側標籤靠得比較近，推近後字仍清楚


def rack_rect(pg, near=None):
    """3D 機櫃本體（畫布正中央那一塊）在視窗座標的外框：畫布寬 22%、高 62% 的中央區（1280×800 實測機櫃約佔這麼大）。
    near＝零件標籤的選擇器：只取機櫃上與這個標籤同高度上下 120px 的那一段（標籤的引線連到那裡），推近時不必把整座機櫃的高度都框進來。"""
    r = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    w = r[2] * 0.22
    y0, y1 = r[1] + r[3] * 0.2, r[1] + r[3] * 0.82
    if near:
        q = pg.evaluate(C.RECT_JS, near)
        y0, y1 = max(y0, q[1] - 120), min(y1, q[1] + q[3] + 120)
    return f"rect:{r[0] + r[2] / 2 - w / 2:.0f},{y0:.0f},{w:.0f},{max(40, y1 - y0):.0f}"


def d_3d(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    warm3d(pg)
    scroll_to(pg, "#dgTools", 76)   # 切 3D 之後 3D 圖剛好在頂欄下方、客服鈕上方，切完不必再捲
    a.x, a.y = 1000, 160
    start()
    a.cam(["#dg3d"], 2, "2D／3D 切換")
    a.say("切到 3D，立體剖析圖", "3dglasses")
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.wait(600)
    # 推近：機櫃本體＋兩側零件標籤（工具列、圖說不入框）
    a.cam(["#prod3d canvas"], 4, "推近：機櫃＋兩側零件標籤", zoom=True)   # 兩側標籤疊在畫布內，畫布外框＝機櫃＋標籤
    r = a.box("#prod3d canvas", scroll=False)
    cx, cy, w = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2, r["width"]
    a.idle(500)
    # 先點零件（機櫃還沒轉，標籤位置穩定，不會點到旁邊標籤的公司小籤），再示範拖曳旋轉、展開收攏
    rack = rack_rect(pg)
    first = True
    for no, lab in (("06", "零件：HBM 記憶體"), ("12", "零件：電源櫃"), ("15", "零件：ToR 交換器")):   # 最後點交換器：下方零件卡（進料／出貨）不含外商客戶名
        rack = rack_rect(pg, lbl(no))   # 機櫃上跟這個標籤同高度的那一段
        a.cam([lbl(no), rack], 10, f"推近：{lab}", minw=ZMIN, zoom=True)   # 被點的標籤＋它連到的機櫃本體
        if first:
            a.say("點零件，說明與環節連動", "magnifier")
            first = False
        side = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return r.left + r.width / 2 > innerWidth / 2 ? 'left' : 'right'; }", lbl(no))
        a.click_now(lbl(no) + " b", lab, approach=side)   # 點標籤的標題（下半部是公司小籤連結）；從畫布那一側水平進場
        a.wait(300)
        a.cam([lbl(no), rack], 10, f"{lab}＋說明", minw=ZMIN, zoom=True)   # 標籤點開後變高（多出說明），取景跟著重量
        a.wait(1100)
    a.cam(["#prod3d canvas"], 4, "推近：機櫃＋兩側零件標籤（旋轉）", zoom=True)
    a.say("拖曳就能 360 度旋轉", "hop_r")
    a.drag(cx - w * 0.14, cy, cx + w * 0.16, cy + 10, 1500)
    a.wait(300)
    a.drag(cx + w * 0.12, cy - 10, cx - w * 0.1, cy + 14, 1400)
    a.wait(300)
    a.say("移入展開、移出收攏", "reveal")
    a.move(cx, r["y"] - 14, 600)      # 游標移出圖框 → 收攏
    a.wait(900)
    a.move(cx - 40, cy, 600)          # 移回圖框 → 展開
    a.wait(1100)
    a.cam_view("捲動")
    a.scroll_to_el("#partCard", 300, 700)
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
    scroll_to(pg, "#dgBody", 96)
    start()
    a.cam(["#dgBody"], 6, "AI 伺服器 2D 剖析圖")
    a.move(200, 240, 400)
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
    a.cam(["#chainSwitch", "#v-industry .gphead"], 4, "進到產業地圖：分頁列", frame=M_TOP_FRAME)
    a.idle(600)
    a.settle()


def m_chain(pg, a, start):
    goto(pg, "#industry")
    start()
    # 分頁列（整條，含它自己左右捲的範圍）＋下方圖表上半；取景固定（切產業鏈時分頁列會自己捲、版面會變，鏡頭不跟著晃）
    a.cam(["#chainSwitch", "rect:21,140,348,470"], 4, "產業鏈分頁＋圖表", frame=M_TOP_FRAME)
    a.say("上方分頁，切換產業鏈", "point_ur_v2")
    for c, lab in (("semiconductor", "產業鏈：半導體"), ("electronics", "產業鏈：一般電子"), (CHAIN, "產業鏈：AI 伺服器")):
        x = pg.evaluate("(s) => { const e = document.querySelector(s), m = document.querySelector('#chainSwitch'); const r = e.getBoundingClientRect();"
                        " return (r.left < 8 || r.right > innerWidth - 8) ? m.scrollLeft + r.left + r.width / 2 - innerWidth / 2 : null; }", chain_btn(c))
        if x is not None:   # 分頁在畫面外：手指把分頁列滑過來（逐格捲動，看得到）
            a.hscroll("#chainSwitch", to_x=x, ms=420)
        a.click(chain_btn(c), label=lab)
        a.wait(1100)
        if c == "semiconductor":
            a.say("每條鏈都有產品剖析圖", "talk_explain_v2")
    # 手機：切產業鏈後先停在「族群總覽」小分頁 → 點「AI 伺服器」小分頁才是產品剖析圖
    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) e.scrollIntoView({inline: 'nearest', block: 'nearest', behavior: 'instant'}); }", f'#dgPick a[data-dgid="{CHAIN}"]')
    a.click(f'#dgPick a[data-dgid="{CHAIN}"]', label="小分頁：AI 伺服器剖析圖")
    a.until("() => !!document.querySelector('#dgBody .mnum')", 6000)
    a.wait(400)
    a.cam_view("捲動")
    a.scroll_to_el("#dgBody", 268, 700)   # 剖析圖放在畫面中段：點編號後下方彈出的零件抽屜與剖析圖同一個鏡頭
    a.cam(["#dgBody"], 6, "剖析圖")
    a.say("點編號看零件說明", "magic_frame")
    a.click_now('#dgBody .mnum[data-no="05"]', "編號 05")
    a.wait(350)
    a.cam(["#dgBody", "#mSheet .mshcard, #mSheet"], 4, "剖析圖＋零件抽屜")
    a.wait(950)
    a.click_now('#mSheet .mshnav button[data-d="1"]', "抽屜「›」：下一個編號")
    a.wait(1300)
    a.settle()


M_REL_SEGS = ("thermal", "power", "optical", "switch", "connector", "fpc", "assembly")   # 中欄（散熱～軟板）＋右欄（系統組裝）


def m_rel_setup(pg):
    """手機關聯圖：錄影前把關聯圖橫向捲到「中欄＋右欄」整欄露出（中欄左緣在 x=42），
    取景框左右邊落在欄與欄之間的空隙，不切過任何環節卡；頁尾下方墊空白（視窗外，不入鏡），點環節展開／收起時捲動位置不被夾。"""
    pg.add_style_tag(content="body{padding-bottom:900px!important}")
    scroll_to(pg, "#relSec", 64)
    pg.evaluate("""() => { const m = document.querySelector('#chainMap'); const t = document.querySelector('#relSec .segbox[data-seg="thermal"]');
      m.scrollLeft += t.getBoundingClientRect().left - 42; }""")
    pg.wait_for_timeout(500)
    g = pg.evaluate("""() => { const q = s => document.querySelector(s).getBoundingClientRect();
      const t = q('#relSec .segbox[data-seg="thermal"]'), a = q('#relSec .segbox[data-seg="assembly"]'), m = q('#chainMap');
      return [t.left, a.right, m.top]; }""")
    x0, x1, mt = g[0] - 20, g[1] + 20, g[2]
    w = x1 - x0
    h = w / (1000 / 1478)
    return f"rect:{x0:.1f},{mt - 7:.1f},{w:.1f},{h:.1f}"


def m_rel(pg, a, start):
    goto(pg, f"#industry/{CHAIN}/overview")   # 族群總覽分頁：關聯圖不會在每次點環節後自動捲回剖析圖反亮的範圍（取景才能固定在中欄＋右欄）
    frame = m_rel_setup(pg)
    cols = "all:" + ", ".join(f'#relSec .segbox[data-seg="{x}"]' for x in M_REL_SEGS)
    start()
    a.cam([cols], 4, "關聯圖：中欄＋右欄", frame=frame, edges=M_EDGE)
    a.say("供應鏈關聯圖：誰供貨給誰", "talk_explain_v2")
    a.move(250, 300, 600)
    a.idle(700)
    a.say("點環節，展開台廠與連線", "point_dr_v2")
    # 由下往上點（軟板 → 交換器 → 電源）：上一格收起時被點的那一格在它上方，位置不會被推動
    for s, lab in (("fpc", "環節：軟板 FPC"), ("switch", "環節：交換器"), ("power", "環節：電源")):
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
    a.cam(["#prod3d"], 4, "3D 剖析圖：機櫃＋兩側編號", zoom=True)
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
    a.cam_view("捲動")
    a.scroll(by=-150, ms=600)   # 3D 往畫面中下段移：點編號後彈出的抽屜與模型、被點的編號同一個鏡頭
    a.cam(["#prod3d"], 4, "3D 剖析圖（點編號前）")
    a.say("點編號，說明跟著換", "magnifier")
    # 抽屜開著時整個畫面鋪了一層背景（點了會收抽屜），所以第 2、3 個零件用抽屜底部的「›」下一個編號切換
    a.click_now('#prod3d .mnum[data-no="11"]', "零件：編號 11 後門風扇模組")
    a.wait(350)   # 抽屜滑上來（動畫結束）才把它算進介紹區塊
    a.cam(["#prod3d .mnum.on", "#mSheet"], 4, "3D＋零件抽屜（編號＋說明）", frame="rect:0,250,390,594", zoom=True)
    a.wait(1150)
    a.say("對應環節、台廠都列好", "pointer_r")
    for lab in ("抽屜「›」：編號 12 電源櫃", "抽屜「›」：編號 13 BBU 電池"):
        a.click_now('#mSheet .mshnav button[data-d="1"]', lab)
        a.wait(1500)
    a.settle()


def m_end(pg, a, start):
    goto(pg, f"#industry/{CHAIN}/overview")
    frame = m_rel_setup(pg)
    cols = "all:" + ", ".join(f'#relSec .segbox[data-seg="{x}"]' for x in M_REL_SEGS)
    start()
    a.cam([cols], 4, "總覽", frame=frame, edges=M_EDGE)
    a.say("上下游、台廠位置一次看", "proud_shine")
    a.move(200, 260, 1300)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(300, 400, 1300)
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
                if dev == "d" and sid in ("open", "chain", "rel"):   # v2 推近拍：3 倍像素錄，推近到 440～700 css 寬仍不糊
                    cfg["device_scale_factor"] = 3
                if dev == "d" and sid == "3d":     # v3：3D 推近 → 1280×800、2 倍像素（軟體算圖較慢，換字清楚）
                    cfg["viewport"] = dict(D3_VIEW)
                    cfg["device_scale_factor"] = 2
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                # 網站 00:00～05:00 自動切深色（DECISIONS #360）：錄影時鐘固定在台北下午 14:30（凌晨錄就用前一天），一律亮色主題
                _tpe = _dt.timezone(_dt.timedelta(hours=8))
                _now = _dt.datetime.now(tz=_tpe)
                _day = _now.date() if _now.hour >= 5 else _now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(_day.year, _day.month, _day.day, 14, 30, tzinfo=_tpe))
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
                    r.update(fabs=rec.fabs, edges=rec.edges, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
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
    ap.add_argument("--out", default=str(SCR / "raw_v2"))
    ap.add_argument("--port", type=int, default=8814)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
