"""功能介紹影片 05：資金流向 —— 素材錄製（沿用 04 的 capture_ind.py 做法，快節奏、成片整支 1.5 倍速）。

沿用 docs/marketing/video_1010/capture.py 的逐格算圖錄影器（page.clock 暫停、每格推進 1/30 秒再截圖，不掉格）、
錄影游標＋點擊漣漪（錄進畫面，點擊中心＝錄影當下量到的元素中心；拉桿＝依數值換算的拉桿位置）。
一律「未登入訪客」的真實畫面（Andy 10-19），客服鈕照常顯示、鏡頭避開；錄影時鐘固定台北下午 14:30（網站 00:00～05:00 自動深色）。

內容只講族群層級（法遵 growth_plan_1018.md 第九節：不放個股為主角、排行不推薦）：
資金輪盤＋族群資金排行（拉桿換天數、篩族群看軌跡）、資金分流樹（看哪一天、流入／流出排名）。
保險起見，錄影瀏覽器裡把任何個股連結／個股卡模糊（BLUR_CSS，只在錄影的瀏覽器裡，不改 site/）；本片不點會列出個股的面板。

用法（repo 根目錄；site/data 已有 flow_v3.json／sankey_daily.json／concentration.json 即可）：
    python docs/marketing/videos/feature_series/05_fund_flow/capture_flow.py --dev d [--shots open,guide]
    python docs/marketing/videos/feature_series/05_fund_flow/capture_flow.py --dev m
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

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat05"))
FPS = 30
DEVS = {
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=4, is_mobile=True, has_touch=True),
}
PACE = float(os.environ.get("FEAT_PACE", "1.0"))


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
    "a[href^='#stock/'],.dp .nm,.dp .cd,#stagePanel .ms,#rankPanel .ms,#sankeyPanel .ms,#concSide .ms{filter:blur(5px)!important}"
)
BLUR_JS = r"""
(() => { const css = %s;
  const go = () => { const st = document.createElement('style'); st.id = '__blurco'; st.textContent = css; (document.head || document.documentElement).appendChild(st); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(BLUR_CSS)


# 字型：網站不載網路字型、用系統的 Noto Sans TC／PingFang／微軟正黑體。錄影容器沒有這幾套，圖表畫布（ECharts）會退回點陣字（字糊、缺筆）。
# 錄影瀏覽器裡用本機的 Noto Sans TC（Medium／Bold／Black）補上同名字型（只在錄影的瀏覽器裡，不改 site/）＝一般使用者電腦上看到的樣子。
FONT_DIR = Path(os.environ.get("HBM_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font"))
FONT_JS = r"""
(() => { const css = `@font-face{font-family:"Noto Sans TC";src:url(/__vfont/NotoSansTC-Medium.ttf);font-weight:100 550}
@font-face{font-family:"Noto Sans TC";src:url(/__vfont/NotoSansTC-Bold.ttf);font-weight:551 750}
@font-face{font-family:"Noto Sans TC";src:url(/__vfont/NotoSansTC-Black.ttf);font-weight:751 1000}`;
  const go = () => { const st = document.createElement('style'); st.id = '__vfont'; st.textContent = css; (document.head || document.documentElement).appendChild(st);
    ['400', '700', '900'].forEach(w => { try { document.fonts.load(w + ' 12px "Noto Sans TC"'); } catch (e) {} }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
"""


def route_fonts(ctx):
    ctx.route("**/__vfont/*", lambda route: route.fulfill(path=str(FONT_DIR / route.request.url.rsplit("/", 1)[-1]), content_type="font/ttf"))


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框（影片像素）。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []
        self.edges: list = []
        self.fabs: list = []

    def frame(self):
        if not self.on:
            return
        # 同 C.Recorder.frame，但頁面計時器裡的例外（例：排行圖重畫時 echarts 丟錯）不中斷錄影：
        # playwright 的 clock.run_for 會先把這段時間的計時器全部跑完、最後才把第一個例外丟出來 → 記下來繼續下一格。
        self.acc += 1000 / FPS
        ms = int(self.acc)
        self.acc -= ms
        try:
            self.pg.clock.run_for(ms)
        except Exception as exc:  # noqa: BLE001
            self.timer_errs = getattr(self, "timer_errs", [])
            self.timer_errs.append([self.n, str(exc).splitlines()[0][:160]])
        self.pg.evaluate(C.ANIM_JS, ms)
        if self.n % 6 == 0:
            self._watch()
        if self.dry:
            self.n += 1
        else:
            r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True, "captureBeyondViewport": False})
            (self.dir / f"s{self.n:06d}.png").write_bytes(C.base64.b64decode(r["data"]))
            self.n += 1
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
        if self.mob:   # 手機：沒有游標可以晃（畫面裡的輪盤掃描、分流樹光點本身在動，成片另有鏡頭慢移）
            for _ in range(n):
                self.frame()
            return
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

    PARK = (2, 60)   # 手機：手指離開螢幕後，滑鼠停在左上角頂欄邊緣（不觸發圖表提示框）

    def click_xy(self, x, y, ms=600, pause=400, expect=None):
        """手機沒有游標：手指在點下那一刻才出現在目標上（點完 0.25 秒消失、滑鼠移開不觸發提示框）；桌機照舊滑過去。"""
        if not self.mob:
            return super().click_xy(x, y, ms, pause, expect)
        self.cursor(False)
        self._put(x, y)
        self.x, self.y = x, y
        self.cursor(True)
        self.wait(max(pause, 200))
        self.note(f"踩下 ({x:.0f},{y:.0f})css → 影片({x * self.dsf:.0f},{y * self.dsf:.0f})px")
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", expect=expect)
        self.pg.mouse.down()
        self.frame()
        self.pg.mouse.up()
        self.frame()
        self.wait(250)
        self.cursor(False)
        self.pg.mouse.move(*self.PARK)
        self.x, self.y = self.PARK

    def move(self, x, y, ms=600):
        if self.mob:   # 手機：手指不在螢幕上滑來滑去（點擊時才出現）
            self.pg.mouse.move(*self.PARK)
            self.x, self.y = x, y
            for _ in range(max(1, round(ms * FPS / 1000))):
                self.frame()
            return
        return super().move(x, y, ms)

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



def rect_of(pg, sel, fx0=0.0, fy0=0.0, fx1=1.0, fy1=1.0):
    """元素外框的一部分（比例），回傳 'rect:x,y,w,h'（視窗座標；這一拍內頁面不捲動）。"""
    r = pg.evaluate(C.RECT_JS, sel)
    x, y, w, h = r
    return f"rect:{x + w * fx0:.1f},{y + h * fy0:.1f},{w * (fx1 - fx0):.1f},{h * (fy1 - fy0):.1f}"


def union_rect(pg, specs):
    """多個 'rect:'／選擇器外框的聯集 → 'rect:'。"""
    xs0, ys0, xs1, ys1 = [], [], [], []
    for s in specs:
        if s.startswith("rect:"):
            x, y, w, h = map(float, s[5:].split(","))
        else:
            x, y, w, h = pg.evaluate(C.RECT_JS, s)
        xs0.append(x); ys0.append(y); xs1.append(x + w); ys1.append(y + h)
    return f"rect:{min(xs0):.1f},{min(ys0):.1f},{max(xs1) - min(xs0):.1f},{max(ys1) - min(ys0):.1f}"


THUMB = {"d": 16.0, "m": 16.0}   # 原生拉桿的圓鈕寬（css）：位置＝左緣＋圓鈕半寬＋（寬－圓鈕寬）×比例


def slider_click(a, sel, value, label, ms=420, pause=160):
    """點原生拉桿上「數值 value」那個位置（真的點下去，拉桿跳到那裡、onInput 觸發重畫）。
    點擊中心誤差以「依數值換算的拉桿位置」為準（拉桿本身是一整條，不是按鈕）。回傳點完後拉桿的實際數值。"""
    js = "(s) => { const e = document.querySelector(s); const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height, +e.min, +e.max]; }"
    tw = THUMB["m" if a.mob else "d"]

    def pt():
        x0, y0, w, h, lo, hi = a.pg.evaluate(js, sel)
        return x0 + tw / 2 + (w - tw) * (value - lo) / (hi - lo), y0 + h / 2
    x, y = pt()
    a.move(x, y, ms)
    for _ in range(10):   # 版面還在動（平滑捲動、上方區塊重排）→ 跟著最新位置走，連續兩次不動才點
        a.wait(40)
        x2, y2 = pt()
        if abs(x2 - x) < 0.6 and abs(y2 - y) < 0.6:
            break
        x, y = x2, y2
        a.move(x, y, 120)
    a.note(f"點拉桿 {label}")
    a.click_xy(x, y, 1, pause, expect=sel)
    tg = a.targets[-1]
    tg["label"] = label
    tg["rect_center"] = a._vpt(x, y)
    tg["measured_by"] = "依數值換算的拉桿位置"
    a.wait(60)
    got = a.pg.evaluate("(s) => +document.querySelector(s).value", sel)
    tg["slider_value"] = got
    tg["slider_want"] = value
    if got != value:
        a.note(f"⚠ 拉桿數值 {got}≠{value}（{label}）")
    return got


ZMIN = 440   # 桌機推近拍的最小取景寬（css）


# ------------------------------------------------------------------ 網頁版鏡頭（1600×900；左側導覽收成圖示列）
def clock_top(pg):
    return rect_of(pg, "#rotClock", 0, 0, 1, 0.5)          # 輪盤上半：改善／領先兩個象限（轉強的那一邊）


def rank_top(pg):
    """排行上方 6 名（標題列＋佔比增加最多的 6 個族群）。取景框上下緣落在「卡片上緣～標題」與「第 6、7 名之間」的空白、
    左緣落在左欄說明字的右邊（量 1800 寬版面：排行每列 47.4 css、第一列在排行區上緣下 35 css）。"""
    x, y, w, h = pg.evaluate(C.RECT_JS, "#rankFlowWrap")
    return f"rect:{x + 6:.1f},{y - 37:.1f},{w + 2:.1f},329"


def d_open(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    start()
    a.cam(["#flowRotCard"], 0, "資金輪動卡（全圖定位）")
    a.move(1000, 520, 400)
    a.say("錢往哪個族群跑？", "face_think_v2")
    a.idle(900)
    a.cam([rank_top(pg)], 10, "推近：族群資金排行（增加最多）", minw=ZMIN, zoom=True)
    b = a.box("#rankFlowWrap", scroll=False)
    a.move(b["x"] + b["width"] * 0.62, b["y"] + 60, 600)
    a.say("誰的資金佔比在增加？", "tilt")
    a.idle(500)
    a.move(b["x"] + b["width"] * 0.62, b["y"] + 230, 700)
    a.cam([clock_top(pg)], 10, "推近：輪盤上半（改善、領先）", minw=ZMIN, zoom=True)
    a.hover("#rotClock .rq:nth-child(2)", 500, dy=1.9)
    a.say("哪個族群正在轉強？", "magnifier")
    a.hover("#rotClock .rq:nth-child(1)", 600, dy=1.9)
    a.idle(600)
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam(["rect:22,180,300,300"], 0, "選單：資金流水", frame="rect:12,172,330,320", minw=ZMIN)
    a.say("左側「資金流水」", "point_r_v2")
    a.hover('#tabs .tab[data-view="overview"]', 450)
    a.say("點「資金流向」", "magnifier")
    a.click('#tabs .tab[data-view="flow"]', label="選單：資金流向")
    a.wait(1500)
    a.click('.l4subtab[data-l4sub="flow-rotation"]', label="子分頁：資金輪動")
    a.wait(1200)
    a.cam(["#flowRotCard"], 0, "進到資金流向：資金輪動")
    a.idle(500)
    a.settle()


def d_days(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    start()
    a.cam(["#flowRotCard"], 0, "資金輪動卡（全圖定位）")
    a.say("拉桿選要看幾天", "clock")
    a.idle(500)
    top = union_rect(pg, ["#flowRotTime", clock_top(pg)])
    first = True
    for v in (5, 10, 30):
        a.cam([top], 8, f"推近：拉桿＋輪盤上半（{v} 天前）", minw=ZMIN, zoom=True)
        if first:
            a.say("輪盤的軌跡跟著變", "point_r_v2")
        slider_click(a, "#rotBack input", v, f"拉桿：{v} 天前")
        a.wait(900)
        a.cam([rank_top(pg)], 10, f"推近：族群資金排行（{v} 天）", minw=ZMIN, zoom=True)
        if first:
            a.say("排行也換成這段期間", "talk_explain_v2")
        a.wait(1000)
        first = False
    a.settle()


CHAINS = (("semiconductor", "產業鏈：半導體"), ("ai_server", "產業鏈：AI 伺服器"), ("electronics", "產業鏈：一般電子"))
CDD = '#flowRotFilter .rotdd[data-dd="chain"]'
CLOSE_AT = '#flowRotFilter .rotdd[data-dd="group"] .ddbtn'   # 收起清單：選完產業鏈網站會自動打開族群清單，再點一次族群鈕就收起（鈕本身永遠露在外面）
# 2026-10-19：原本用「族群」下拉勾 3 個族群，但網站勾族群時會連帶打開該族群的成分股面板（pickGroup → 列出個股，
# 而且排行圖在只剩幾個族群時重畫會丟 echarts 例外、長條消失）→ 改用「產業鏈」下拉：輪盤與排行一起只留那條鏈的族群，全程族群層級。


def pick_chain(a, c, lab):
    a.click(f"{CDD} .ddbtn", label="產業鏈下拉清單")
    a.wait(450)
    a.click(f'{CDD} .ddopt[data-c="{c}"]', label=lab)


def d_pick(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    start()
    a.cam(["#flowRotCard"], 0, "資金輪動卡（全圖定位）")
    a.say("只看某一條產業鏈？", "face_curious")
    a.idle(500)
    fb = pg.evaluate(C.RECT_JS, f"{CDD} .ddbtn")
    pan = f"rect:{fb[0]:.1f},{fb[1]:.1f},420,{fb[3] + 300:.1f}"   # 產業鏈清單＋選完自動打開的族群清單
    top = union_rect(pg, ["#flowRotFilter", pan, clock_top(pg)])
    first = True
    for c, lab in CHAINS:
        a.cam([top], 8, f"推近：產業鏈清單＋輪盤上半（{lab[4:]}）", minw=ZMIN, zoom=True)
        if first:
            a.say("選一條鏈，輪盤只留它", "spotlight")
        pick_chain(a, c, lab)
        a.wait(900)
        a.cam([rank_top(pg)], 10, f"推近：族群資金排行（{lab[4:]}）", minw=ZMIN, zoom=True)
        if first:
            a.say("排行也跟著篩", "face_nod_v2")
        a.wait(1000)
        first = False
    a.cam(["#flowRotCard"], 0, "輪盤＋排行只留一般電子")
    a.click(CLOSE_AT, label="收起族群清單")
    a.idle(900)
    a.settle()


def sk_top(pg):
    return rect_of(pg, "#sankey", 0, 0, 0.86, 0.42)       # 分流樹上半：半導體這一枝（族群佔比與變化）


def d_tree(pg, a, start):
    goto(pg, "#flow/sankey", 5500)
    start()
    a.cam(["#flowSankeyCard"], 0, "資金分流樹（全圖定位）")
    a.say("錢從大盤分到哪些族群？", "folder")
    a.idle(700)
    n = pg.evaluate("() => +document.querySelector('#sankeyDays input').max")
    head = union_rect(pg, ["#sankeyDays", rect_of(pg, "#sankeyRank", 0, 0, 1, 0.42)])
    first = True
    for v, lab in ((n - 15, "15 天前"), (n - 5, "5 天前"), (n, "最新一天")):
        a.cam([head], 8, f"看哪一天＋排名（{lab}）")
        if first:
            a.say("拉桿換一天，樹跟著換", "clock")
        slider_click(a, "#sankeyDays input", v, f"看哪一天：{lab}")
        a.wait(700)
        a.cam([sk_top(pg)], 8, f"推近：分流樹上半（{lab}）", minw=ZMIN, zoom=True)
        if first:
            a.say("佔比與增減一眼看", "magnifier")
        a.wait(1000)
        first = False
    # 排名欄窄而高：推近到「流入／流出切換鈕＋前 2 名」那一段（寬高比接近畫面框，佔畫面寬 ≥70%）
    p = pg.evaluate(C.RECT_JS, "#sankeyRank")
    t = pg.evaluate(C.RECT_JS, '#sankeyRank button[data-t="in"]')
    r2 = pg.evaluate("() => { const e = document.querySelectorAll('#sankeyRank .skr-r')[1]; if (!e) return null; const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }") or [0, t[1] + 200, 0, 0]
    rk = f"rect:{p[0] + 4:.1f},{t[1] - 8:.1f},{p[2] - 8:.1f},{r2[1] + r2[3] - t[1] + 14:.1f}"
    a.cam([rk], 6, "推近：資金流向排名", minw=ZMIN * 0.8, zoom=True)
    a.say("流入、流出各排一次", "point_r_v2")
    a.click('#sankeyRank button[data-t="out"]', label="排名：流出最多")
    a.wait(1300)
    a.click('#sankeyRank button[data-t="in"]', label="排名：流入最多")
    a.wait(1100)
    a.settle()


def d_end(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    start()
    a.cam(["#flowRotCard"], 0, "總覽")
    a.say("錢往哪跑，一頁看懂", "proud_shine")
    a.move(700, 500, 900)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(1000, 600, 900)
    a.settle()


# ------------------------------------------------------------------ 手機版鏡頭（390 寬 m4 版面）
def m_open(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    scroll_to(pg, "#rotClockWrap", 150)
    a.x, a.y = 360, 130   # 手機沒有滑鼠停留：手指一律停在圖外的空白處（不觸發圖上的提示框）
    start()
    a.cam(["#rotClockWrap"], 6, "資金輪盤")
    a.say("錢往哪個族群跑？", "face_think_v2")
    a.idle(800)
    a.say("哪個族群正在轉強？", "magnifier")
    a.idle(800)
    a.cam_view("捲動")
    a.scroll_to_el("#rankFlow", 120, 700)
    a.cam(["#rankFlow"], 6, "族群資金排行")
    a.say("誰的資金佔比在增加？", "tilt")
    a.idle(900)
    a.settle()


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="flow"]', '.m4item[data-v="overview"]'], 10, "選單抽屜")
    a.say("點「資金流向」", "magnifier")
    a.click('.m4item[data-v="flow"]', label="選單：資金流向")
    a.wait(1700)
    a.cam(['button[data-sub="flow-rotation"]', 'button[data-sub="flow-conc"]', "#flowRotFilter"], 4, "進到資金流向：分頁列")
    a.idle(600)
    a.settle()


def m_days(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    scroll_to(pg, "#rotBack", 110)
    start()
    a.cam(["#rotBack", "#rotClockWrap"], 6, "拉桿＋資金輪盤")
    a.say("拉桿選要看幾天", "clock")
    first = True
    for v in (5, 10, 30):
        slider_click(a, "#rotBack input", v, f"拉桿：{v} 天前")
        a.wait(1100)
        if first:
            a.say("輪盤的軌跡跟著變", "point_dr_v2")
        first = False
    a.cam_view("捲動")
    a.scroll_to_el("#rankFlow", 120, 700)
    a.cam(["#rankFlow"], 6, "族群資金排行（30 天）")
    a.say("排行也換成這段期間", "talk_explain_v2")
    a.idle(900)
    a.settle()


def m_pick(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    scroll_to(pg, "#flowRotFilter", 100)
    # 取景固定：篩選列上緣～輪盤下緣再多 50 css（選了較長的產業鏈名稱，篩選列會折成兩行、輪盤往下移約 35 css，仍整塊在框內）
    f = pg.evaluate(C.RECT_JS, "#flowRotFilter")
    k = pg.evaluate(C.RECT_JS, "#rotClockWrap")
    fr = f"rect:12,{f[1] - 8:.1f},366,{k[1] + k[3] + 50 - (f[1] - 8):.1f}"
    start()
    a.cam([fr], 0, "產業鏈篩選＋資金輪盤", frame=fr)
    a.say("只看某一條產業鏈？", "face_curious")
    first = True
    for c, lab in CHAINS:
        pick_chain(a, c, lab)
        a.wait(300)
        a.click(CLOSE_AT, label="收起族群清單")
        a.wait(800)
        if first:
            a.say("選一條鏈，輪盤只留它", "spotlight")
        first = False
    a.cam_view("捲動")
    a.scroll_to_el("#rankFlow", 120, 700)
    a.cam(["#rankFlow"], 6, "族群資金排行（一般電子）")
    a.say("排行也跟著篩", "face_nod_v2")
    a.idle(900)
    a.settle()


def m_tree(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    start()
    a.cam(['button[data-sub="flow-rotation"]', 'button[data-sub="flow-conc"]', "#flowRotFilter"], 4, "分頁列")
    a.say("錢從大盤分到哪些族群？", "folder")
    a.click('button[data-sub="flow-sankey"]', label="分頁：資金分流樹")
    a.until("() => !!document.querySelector('#sankey canvas')", 8000)
    a.wait(900)
    a.cam_view("捲動")
    a.scroll_to_el("#sankeyDays", 100, 500)
    # 拉桿＋分流樹上 3/4（半導體、AI 伺服器、一般電子三枝）：整棵樹 646 css 高，連拉桿放不進 9:16 畫面框
    a.cam(["#sankeyDays", rect_of(pg, "#sankeyWrap", 0, 0, 1, 0.76)], 4, "看哪一天＋資金分流樹（上 3/4）")
    n = pg.evaluate("() => +document.querySelector('#sankeyDays input').max")
    first = True
    for v, lab in ((n - 15, "15 天前"), (n - 5, "5 天前"), (n, "最新一天")):
        slider_click(a, "#sankeyDays input", v, f"看哪一天：{lab}")
        a.wait(1100)
        if first:
            a.say("拉桿換一天，樹跟著換", "clock")
        first = False
    a.cam_view("捲動")
    a.scroll_to_el("#sankeyRank", 70, 700)
    a.cam([rect_of(pg, "#sankeyRank", 0, 0, 1, 0.62)], 4, "資金流向排名")
    a.say("流入、流出各排一次", "point_dr_v2")
    a.click('#sankeyRank button[data-t="out"]', label="排名：流出最多")
    a.wait(1300)
    a.click('#sankeyRank button[data-t="in"]', label="排名：流入最多")
    a.wait(1100)
    a.settle()


def m_end(pg, a, start):
    goto(pg, "#flow/rotation", 5000)
    scroll_to(pg, "#rotClockWrap", 150)
    a.x, a.y = 360, 130
    start()
    a.cam(["#rotClockWrap"], 6, "總覽")
    a.say("錢往哪跑，一頁看懂", "proud_shine")
    a.idle(1300)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.idle(1300)
    a.settle()


VP_D = {"guide": (1800, 1080, 2), "open": (1800, 1080, 3), "days": (1800, 1080, 3), "pick": (1800, 1080, 3), "tree": (2000, 1152, 2.5), "end": (1800, 1080, 3)}
D_SHOTS = {"open": d_open, "guide": d_guide, "days": d_days, "pick": d_pick, "tree": d_tree, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "days": m_days, "pick": m_pick, "tree": m_tree, "end": m_end}


def run(dev, shots, out, port):
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
                if dev == "d" and sid in VP_D:
                    # 全圖定位拍要把整張卡（資金輪動卡 821 css 高、資金分流樹卡 914 css 高）完整放進 1650×810 的畫面框（寬高比 2.04），
                    # 1600×900 的視窗寬度不夠 → 這幾鏡用較寬的視窗；卡片高度固定，客服鈕落在卡片下方、鏡頭外。
                    # 推近拍以 3 倍（分流樹 2.5 倍）像素錄，推近到 440～1000 css 寬仍不糊。
                    w_, h_, k_ = VP_D[sid]
                    cfg["viewport"] = {"width": w_, "height": h_}
                    cfg["device_scale_factor"] = k_
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                # 網站 00:00～05:00 自動切深色（DECISIONS #360）：錄影時鐘固定在台北下午 14:30（凌晨錄就用前一天），一律亮色主題
                _tpe = _dt.timezone(_dt.timedelta(hours=8))
                _now = _dt.datetime.now(tz=_tpe)
                _day = _now.date() if _now.hour >= 5 else _now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(_day.year, _day.month, _day.day, 14, 30, tzinfo=_tpe))
                route_fonts(ctx)
                ctx.add_init_script(FONT_JS)
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                ctx.add_init_script(BLUR_JS)       # 法遵：個股連結／個股卡模糊（保險）
                ctx.add_init_script("try{['tw.rot.days','tw.sankey.day'].forEach(k=>localStorage.removeItem(k))}catch(e){}")
                if dev == "d" and sid != "guide":   # 桌機左側導覽收成圖示列：內容區更寬
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                pg.evaluate("() => document.fonts.ready")
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (900, 500) if dev == "d" else (370, 160)
                a.dsf = cfg["device_scale_factor"]
                rec = Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    if a.mob:
                        a.cursor(False)
                        pg.mouse.move(*A.PARK)
                    else:
                        a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)   # 最後一泡：段尾交叉淡化 0.4 秒前仍要停滿
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]] if (sid == "guide" or dev == "m") else pg.evaluate("() => { const e = document.querySelector('#v-flow'); const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
                    r.update(timer_errs=getattr(rec, 'timer_errs', []), fabs=rec.fabs, edges=rec.edges, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
                except Exception as exc:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
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
    ap.add_argument("--port", type=int, default=8815)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
