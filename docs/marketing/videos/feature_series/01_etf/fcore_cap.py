"""功能介紹影片 01～03（Andy 10-21 重作）共用的錄影引擎：一條主線、單一連續錄影、不准遮擋。

沿用 docs/marketing/video_1010/capture.py 的逐格算圖錄影器（page.clock 暫停、每格推進 1/30 秒再截圖，不掉格），一律「未登入訪客」真實畫面。
相對上一版的改動：
- 整支只錄一段連續畫面（需求 → 選單 → 功能頁 → 操作），不再每個功能各錄一段交叉淡化。
- 每一格記錄「被介紹元素」：每個元素各自的外框（items），並用 elementFromPoint 取樣檢查有沒有被別的東西（提示框、下拉清單、面板、
  頂欄、客服鈕…）蓋在上面 → occ（遮擋）。
- 游標：只在點擊窗口（點下前 0.25 秒～點下後 0.35 秒；連續快點合併）可以落在被介紹元素上，其餘時間點完就移出（away）；
  每格記錄游標外框，錄完比對 → cursor_occ。
- 提示框（ECharts 的浮動提示）一律不顯示（只在錄影的瀏覽器裡），避免蓋住圖表。
- 每一拍鏡頭另外量主要文字的字級（minfont），合成時算成片字高。
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs" / "marketing" / "video_1010"))
import capture as C  # noqa: E402

FPS = 30
SPEED = float(os.environ.get("FEAT_SPEED", "1.6"))   # 成片倍速（1.6～1.75）；泡泡成片上至少停 0.9 秒
DEVS = {
    "d": dict(viewport={"width": 1280, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=4, is_mobile=True, has_touch=True),
}
PACE = float(os.environ.get("FEAT_PACE", "1.0"))
BUBBLE_MIN = 0.9   # 成片泡泡最短停留（秒）
CFG: dict = {}      # 各支設定：scr（輸出資料夾）、blur_js（個股名稱模糊）、content（內容區選擇器）、init（額外 init script）…


def bubble_dur(text: str) -> float:
    """泡泡原片停留秒數：成片 ≥0.9 秒 ＋ 合成時出現／收掉的損耗 0.2。"""
    return BUBBLE_MIN * SPEED + 0.2


# ------------------------------------------------------------------ 每格量測
# focus＝介紹區塊（元素聯集＋留白，不裁到視窗）；cam＝取景框；items＝各元素外框；occ＝被別的東西蓋住的取樣點描述；
# 選擇器：一般 CSS；all:CSS＝全部可見元素；txt:CSS|文字＝文字完全相符的元素；rect:x,y,w,h＝固定矩形（不做遮擋檢查）。
FRAME_JS = r"""([sels, pad, frame, edges, also]) => {
  const vh = innerHeight, vw = innerWidth;
  const vis = (r) => r.width >= 2 && r.height >= 2 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
  const rectOf = (s) => { const [x, y, w, h] = s.slice(5).split(',').map(Number); return { e: null, left: x, top: y, right: x + w, bottom: y + h, width: w, height: h }; };
  const R = (e) => { const r = e.getBoundingClientRect(); const l = Math.max(0, r.left), tp = Math.max(0, r.top), rt = Math.min(vw, r.right), bt = Math.min(vh, r.bottom);   // 只取視窗內看得到的部分（網站下拉面板會超出視窗右緣幾 px）
    return { e, left: l, top: tp, right: rt, bottom: bt, width: rt - l, height: bt - tp }; };
  const pick = (s) => { if (!s.startsWith('txt:')) return document.querySelector(s);
    const [css, txt] = s.slice(4).split('|'); return [...document.querySelectorAll(css)].find((x) => x.getClientRects().length && (x.innerText || '').trim() === txt) || null; };
  const rects = (list) => { const out = []; for (const s of list) {
      if (s.startsWith('rect:')) out.push(rectOf(s));
      else if (s.startsWith('all:')) document.querySelectorAll(s.slice(4)).forEach(e => { if (e.getClientRects().length) out.push(R(e)); });
      else { const e = pick(s); if (e && e.getClientRects().length) out.push(R(e)); } }
    return out.filter(vis); };
  const uni = (rs, p) => { if (!rs.length) return null; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    rs.forEach(r => { x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
    return [x0 - p, y0 - p, x1 - x0 + 2 * p, y1 - y0 + 2 * p]; };
  const desc = (t) => t.tagName.toLowerCase() + (t.id ? '#' + t.id : '') + '.' + String(t.className && t.className.baseVal !== undefined ? t.className.baseVal : t.className).split(' ')[0];
  const covered = (r) => { const e = r.e; if (!e) return null;
    const x0 = Math.max(r.left, 0) + 3, x1 = Math.min(r.right, vw) - 3, y0 = Math.max(r.top, 0) + 3, y1 = Math.min(r.bottom, vh) - 3;
    if (x1 <= x0 || y1 <= y0) return null;
    const NX = 9, NY = 7; let bad = 0, who = null;
    for (let i = 0; i < NX; i++) for (let j = 0; j < NY; j++) {
      const x = x0 + (x1 - x0) * i / (NX - 1), y = y0 + (y1 - y0) * j / (NY - 1);
      const t = document.elementFromPoint(x, y); if (!t) continue;
      if (t === e || e.contains(t) || t.contains(e)) continue;
      if (t.closest && (t.closest('#__vc') || t.closest('.__vr'))) continue;
      bad++; who = who || desc(t); }
    return bad ? who + '×' + bad : null; };
  const rs0 = rects(sels);
  const rs = rs0.concat(rects(also || []));
  const focus = uni(rs0, pad);
  const cam = frame ? uni(rects([frame]), 0) : focus;
  const ed = (edges && edges.length) ? rects(edges).map(r => [r.left, r.top, r.width, r.height]) : [];
  const items = rs.filter(r => r.e).map(r => [r.left, r.top, r.width, r.height]);
  const occ = rs.map(covered).filter(Boolean);
  const fes = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring, #bibiStage, .bibiwrap')]
    .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && +getComputedStyle(e).opacity > 0.05);
  let fab = null; if (fes.length) { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    fes.forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 2) return; x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
    if (x1 > x0) fab = [x0, y0, x1 - x0, y1 - y0]; }
  return { focus, cam, edges: ed, items, occ, fab }; }"""

# 「卡片」外框：有邊框或陰影＋圓角、夠大的方塊（取景框的邊不准切過它；整頁級的大容器不算）
BLOCKS_JS = r"""() => { const vw = innerWidth, vh = innerHeight, out = [];
  const all = document.body.querySelectorAll('div,section,article,aside,nav,table,ul,form,main,header');
  for (const e of all) { const r = e.getBoundingClientRect();
    if (r.width < 180 || r.height < 30 || r.right < 0 || r.left > vw || r.bottom < 0 || r.top > vh) continue;
    if (r.width >= vw * 0.97 && r.height >= vh * 0.9) continue;
    const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const rad = parseFloat(cs.borderTopLeftRadius) || 0; const bw = parseFloat(cs.borderTopWidth) || 0;
    const sh = cs.boxShadow && cs.boxShadow !== 'none';
    if (!((rad >= 4 && (bw >= 1 || sh)) || (sh && r.width > 200))) continue;
    out.push([r.left, r.top, r.width, r.height]); if (out.length > 400) break; }
  return out; }"""

# 主要文字字級：被介紹元素內可見文字，依字數加權的第 25 百分位（忽略少數極小的註記）與最小值
FONT_JS = r"""(sels) => {
  const vh = innerHeight, vw = innerWidth; const arr = [];
  const pick = (s) => { if (!s.startsWith('txt:')) return s.startsWith('all:') ? [...document.querySelectorAll(s.slice(4))] : [document.querySelector(s)];
    const [css, txt] = s.slice(4).split('|'); return [[...document.querySelectorAll(css)].find((x) => x.getClientRects().length && (x.innerText || '').trim() === txt)]; };
  for (const s of sels) { if (s.startsWith('rect:')) continue; for (const e of pick(s)) { if (!e) continue;
    const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); let n, k = 0;
    while ((n = w.nextNode()) && k < 600) { k++; const t = (n.nodeValue || '').replace(/\s+/g, ''); if (t.length < 2) continue;
      const p = n.parentElement; if (!p || !p.getClientRects().length) continue; const r = p.getBoundingClientRect();
      if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
      const cs = getComputedStyle(p); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) continue;
      arr.push([parseFloat(cs.fontSize), t.length]); } } }
  if (!arr.length) return null; arr.sort((a, b) => a[0] - b[0]); const tot = arr.reduce((s, x) => s + x[1], 0); let acc = 0, p25 = arr[0][0];
  for (const [f, c] of arr) { acc += c; if (acc >= tot * 0.25) { p25 = f; break; } }
  return [p25, arr[0][0], tot]; }"""

# 錄影用：隱藏 ECharts 提示框（hover 浮出的方塊會蓋住圖）
NOTIP_CSS = ("div[style*='z-index: 9999999'],div[style*='z-index:9999999']{display:none!important;visibility:hidden!important}"
             "html,body,*{scroll-behavior:auto!important;overflow-anchor:none!important}"
             "i.m4thumb,.m4thumb,.m4rail,div.m4rail{display:none!important}")   # 手機頁面右緣的拖曳捲軸滑塊（半透明，會蓋住右欄內容）   # 逐格捲動：站上 html 有 scroll-behavior:smooth，設 scrollTop 會變成慢慢滑、跟不上每格的設定
NOTIP_JS = ("(() => { const go = () => { const st = document.createElement('style'); st.id = '__notip'; st.textContent = %s;"
            " (document.head || document.documentElement).appendChild(st); };"
            " document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();") % json.dumps(NOTIP_CSS)

# 點擊漣漪縮短到 0.35 秒（落在點擊窗口內）
CURSOR_JS = C.CURSOR_JS.replace(".55s", ".35s").replace("}, 700)", "}, 450)").replace("background:rgba(37,99,235,.18);", "background:transparent;")   # 漣漪只留外圈，不蓋住被點的字

# 網頁固定取景版（10-22）：錄影視窗較矮，客服鈕移到畫面下緣外（只動錄影瀏覽器的 CSS，不改 site/）
HIDE_FAB_JS = ("(() => { const go = () => { const st = document.createElement('style'); st.textContent = 'html body #supFab,html body .supfab,html body #bibiRing,html body .bibiring{bottom:-260px!important}';"
               " (document.head || document.documentElement).appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();")

CURSOR_BOX_D = (-3, -2, 26, 30)     # 桌機箭頭游標外框（相對於游標座標：dx, dy, w, h）
CURSOR_BOX_M = (-17, -17, 34, 34)   # 手機指尖圓點


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框、被介紹元素、遮擋、游標。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []
        self.edges: list = []
        self.fabs: list = []
        self.blocks_tbl: list = []
        self.blocks_idx: list = []
        self._blk = -1
        self.items: list = []
        self.occ: list = []
        self.cur: list = []
        self.snap = {int(x) for x in os.environ.get("FEAT_SNAP", "").split(",") if x}

    def _shot(self):
        """同 C.Recorder.frame，但截圖存 JPEG（品質 95）：PNG 每格 4～5MB、一支片要 5GB，磁碟不夠。"""
        if not self.on:
            return
        self.acc += 1000 / FPS
        ms = int(self.acc)
        self.acc -= ms
        self.pg.clock.run_for(ms)
        self.pg.evaluate(C.ANIM_JS, ms)
        if self.n % 6 == 0:
            self._watch()
        if self.dry:
            self.n += 1
            return
        r = self.cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 95, "optimizeForSpeed": True, "captureBeyondViewport": False})
        (self.dir / f"s{self.n:06d}.jpg").write_bytes(base64.b64decode(r["data"]))
        self.n += 1

    def stop(self, out_mp4):
        self.on = False
        try:
            self.pg.clock.resume()
        except Exception:  # noqa: BLE001
            pass
        if not self.n:
            return {"ok": False, "why": "沒有任何畫格"}
        if self.dry:
            shutil.rmtree(self.dir)
            return {"ok": True, "dry": True, "dur": round(self.n / FPS, 2), "frames": self.n, "bad": self.bad}
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(self.dir / "s%06d.jpg"),
               "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-threads", "2", "-crf", "17",
               "-r", str(FPS), "-movflags", "+faststart", str(out_mp4)]
        subprocess.run(cmd, check=True)
        n = self.n
        shutil.rmtree(self.dir)
        return {"ok": True, "dur": round(n / FPS, 2), "frames": n, "bad": self.bad}

    def frame(self):
        self._shot()
        if not self.on:
            return
        a = self.act
        spec = a.cam_spec
        r = None
        if spec and spec[0] == "sel":
            try:
                r = self.pg.evaluate(FRAME_JS, [spec[1], spec[2], spec[3], spec[5], spec[7]])
            except Exception:  # noqa: BLE001
                r = None
        else:
            try:
                r = self.pg.evaluate(FRAME_JS, [[], 0, None, [], []])
            except Exception:  # noqa: BLE001
                r = None
        k = a.dsf
        sc = lambda v: [round(x * k, 1) for x in v] if v else None   # noqa: E731
        if not spec or r is None or r.get("cam") is None:
            self.cams.append([a.cam_id, 0, 0, a.vw * k, a.vh * k, 0, None, 0])   # 整個視窗（捲動、轉場），不檢查裁切
            self.edges.append([])
            self.items.append([])
            self.occ.append([])
        else:
            self.cams.append([a.cam_id] + sc(r["cam"]) + [round((spec[4] or 0) * k, 1), sc(r["focus"]), 1 if spec[6] else 0, int(spec[8]) if len(spec) > 8 and spec[8] else 0])
            self.edges.append([sc(e) for e in r["edges"]])
            self.items.append([sc(e) for e in r["items"]])
            self.occ.append(r["occ"])
        self.fabs.append(sc(r["fab"]) if r and r.get("fab") else None)
        if self.n % 3 == 0 or self._blk < 0:
            try:
                self.blocks_tbl.append([sc(b) for b in self.pg.evaluate(BLOCKS_JS)])
                self._blk = len(self.blocks_tbl) - 1
            except Exception:  # noqa: BLE001
                pass
        self.blocks_idx.append(self._blk)
        self.cur.append([round(a._cx * k, 1), round(a._cy * k, 1), 1 if a._chide else 0])
        if self.n in self.snap:
            try:
                self.pg.screenshot(path=str(Path(CFG["scr"]) / f"snap_{a.dev}_{self.n:05d}.png"))
            except Exception:  # noqa: BLE001
                pass


class A(C.Act):
    def __init__(self, pg, mob, vw, vh, dev):
        super().__init__(pg, mob)
        self.vw, self.vh, self.dev = vw, vh, dev
        self.cam_spec = None
        self.cam_id = 0
        self.says: list = []
        self.marks: list = []
        self.say_t = None
        self.say_need = 0.0
        self._cx, self._cy, self._chide = -100.0, -100.0, 0
        self.fonts: dict = {}

    # ---- 鏡頭 ----
    def _probe_font(self):
        spec = self.cam_spec
        if not spec or spec[0] != "sel":
            return
        try:
            f = self.pg.evaluate(FONT_JS, spec[1])
        except Exception:  # noqa: BLE001
            f = None
        if f:
            lab = getattr(self, "_label", str(self.cam_id))
            cur = self.fonts.get(self.cam_id)
            if cur is None or f[0] < cur[1]:
                self.fonts[self.cam_id] = [lab, f[0], f[1], f[2]]

    def cam(self, sels, pad=12, label="", frame=None, minw=None, edges=None, zoom=False, also=None, settle=True, exact=False):
        """sels＝介紹的區塊（每個元素各自檢查遮擋）；frame＝取景框；minw＝取景最小寬（css）；edges＝不准被框邊切過的卡片；zoom＝推近拍。"""
        if settle:
            self.settle()
        self._probe_font()   # 上一拍結束時的畫面再量一次字級
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad, frame, minw, list(edges or []), zoom, list(also or []), exact)
        self.cam_id += 1
        self._label = label or ",".join(sels)
        self.marks.append([round(self.t, 3), "cam", self._label])
        self._probe_font()

    def cam_view(self, label="viewport", settle=True):
        if settle:
            self.settle()
        self._probe_font()
        self.cam_spec = None
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label])

    def step(self, name):
        """合成時右側導覽的目前步驟（網頁版）。"""
        self.marks.append([round(self.t, 3), "step", name])

    def mark(self, name):
        self.marks.append([round(self.t, 3), "mark", name])

    # ---- 游標 ----
    def _put(self, x, y):
        self._cx, self._cy = x, y
        super()._put(x, y)

    def show_cursor(self):
        if self._chide:
            self._chide = 0
            self.cursor(True)

    def hide_cursor(self):
        if not self._chide:
            self._chide = 1
            self.cursor(False)

    def idle(self, ms):
        """原地等待 ms 毫秒（游標不動；游標若隱藏就維持隱藏）。"""
        n = max(1, round(ms * FPS / 1000))
        for _ in range(n):
            self.frame()

    def settle(self):
        if self.say_t is not None:
            rest = self.say_need - (self.t - self.say_t)
            if rest > 0.02:
                self.idle(rest * 1000)

    def say(self, text, act="talk_explain_v2"):
        assert len(text.replace(" ", "")) <= 14, text
        self.settle()
        self.says.append({"t": round(self.t, 3), "text": text, "act": act})
        self.say_t, self.say_need = self.t, bubble_dur(text)

    def wait(self, ms):
        return super().wait(ms * PACE)

    def _free_point(self):
        """視窗邊緣最近的、不在任何被介紹元素上的位置；找不到回傳 None。"""
        spec = self.cam_spec
        items = []
        if spec and spec[0] == "sel":
            try:
                r = self.pg.evaluate(FRAME_JS, [spec[1], spec[2], spec[3], spec[5], spec[7]])
                items = (r or {}).get("items") or []
            except Exception:  # noqa: BLE001
                items = []
        cw, ch = (34, 34) if self.mob else (30, 34)

        def free(x, y):
            return not any(x - cw < it[0] + it[2] and x + cw > it[0] and y - ch < it[1] + it[3] and y + ch > it[1] for it in items)
        cands = []
        for xx in (self.vw - 14, 14, self.vw / 2):
            for yy in range(60, int(self.vh - 60), 40):
                cands.append((xx, yy))
        for yy in (self.vh - 12, 8):
            for xx in range(30, int(self.vw - 30), 60):
                cands.append((xx, yy))
        ok = [c for c in cands if free(*c)]
        if not ok:
            return None
        return min(ok, key=lambda c: (c[0] - self._cx) ** 2 + (c[1] - self._cy) ** 2)

    def away(self, ms=150):
        """把游標移出目前的介紹區塊（往視窗邊緣最近的、不在任何被介紹元素上的位置），移完隱藏。"""
        p = self._free_point()
        if p is None:
            self.hide_cursor()
            return
        self.move(p[0], p[1], ms)
        self.hide_cursor()

    def park_now(self):
        """游標隱藏中、瞬間放到目前取景下的空位（下一次點擊的起點；游標看不到，所以不算遮擋）。"""
        if not self._chide:
            return
        p = self._free_point()
        if p is not None:
            self._put(*p)
            self.x, self.y = p

    # ---- 動作 ----
    def click(self, sel, ms=150, pause=0, dx=0.5, dy=0.5, label="", keep=False, hold=100):
        """游標快速移到目標（≤0.25 秒，不從內容上慢飄）、點下、停 hold 毫秒、移出（keep=True 時留在原地，給連續快點）。"""
        b = self.box(sel)
        if not b:
            self.note(f"點不到 {sel}")
            return False
        x, y = b["x"] + b["width"] * dx, b["y"] + b["height"] * dy
        self.note(f"點 {label or sel}")
        self.park_now()
        self.show_cursor()
        self.move(x, y, ms)
        self.wait(pause)
        pre = self.pg.evaluate(C.RECT_JS, sel)   # 按下前一刻量被點元素本身的外框
        self.click_xy(x, y, 1, 0, expect=sel)
        tg = self.targets[-1]
        if label:
            tg["label"] = label
        if pre and pre[2] > 0:
            tg["rect_center"] = self._vpt(pre[0] + pre[2] / 2, pre[1] + pre[3] / 2)
            tg["measured_by"] = "被點元素外框（按下前一刻）"
        if not keep:
            self.wait(hold)
            self.away(150)
        return True

    def click_pt(self, x, y, label, expect=None, ms=150, pause=0, measured_by="", keep=False, hold=100):
        self.park_now()
        self.show_cursor()
        self.move(x, y, ms)
        self.wait(pause)
        self.click_xy(x, y, 1, 0, expect=expect)
        tg = self.targets[-1]
        tg["label"] = label
        if measured_by:
            tg.update(rect_center=list(tg["center"]), measured_by=measured_by)
        if not keep:
            self.wait(hold)
            self.away(150)

    def click_xy(self, x, y, ms=600, pause=400, expect=None):
        """同 C.Act.click_xy，另外在「按下去那一格」之前先呼叫 on_down（換取景用：按下瞬間網站會跳出面板／遮罩，取景要同一格就換）。"""
        self.move(x, y, ms)
        self.wait(pause)
        self.note(f"踩下 ({x:.0f},{y:.0f})css → 影片({x * self.dsf:.0f},{y * self.dsf:.0f})px")
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", expect=expect)
        self.pg.mouse.down()
        cb = getattr(self, "on_down", None)
        if cb:
            self.on_down = None
            cb()
        self.frame()
        self.pg.mouse.up()
        cb2 = getattr(self, "on_up", None)
        if cb2:   # 放開瞬間網站會收起／展開面板：取景在放開後的第一格就換
            self.on_up = None
            cb2()
        self.frame()

    SIDE_MID_JS = r"""([sel, frac]) => { const e = document.querySelector(sel); if (!e) return null;
      let p = e.parentElement; while (p && p !== document.body) { const cs = getComputedStyle(p); if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 2) break; p = p.parentElement; }
      if (!p || p === document.body) return null; const r = e.getBoundingClientRect(), pr = p.getBoundingClientRect();
      const want = pr.top + pr.height * frac; if (!p.id) p.id = '__vside'; return ['#' + p.id, Math.max(0, p.scrollTop + r.top + r.height / 2 - want)]; }"""

    def side_mid(self, sel, frac=0.4, ms=500):
        """左側選單捲到讓目標項目落在選單高度的 frac 處（取景下緣才不會切到選單被裁掉的半行字）。"""
        r = self.pg.evaluate(self.SIDE_MID_JS, [sel, frac])
        if r:
            self.scroll(to_y=r[1], ms=ms, el=r[0])

    def hscroll(self, sel, to_x=None, by=None, ms=900):
        x0, mx = self.pg.evaluate("(s) => { const e = document.querySelector(s); return e ? [e.scrollLeft, e.scrollWidth - e.clientWidth] : [0, 0]; }", sel)
        x1 = to_x if to_x is not None else x0 + (by or 0)
        x1 = max(0, min(mx, x1))
        n = max(1, round(ms * FPS / 1000))
        for i in range(1, n + 1):
            k = i / n
            e = 2 * k * k if k < .5 else 1 - (-2 * k + 2) ** 2 / 2
            self.pg.evaluate("([s, x]) => { const el = document.querySelector(s); if (el) el.scrollLeft = x; }", [sel, x0 + (x1 - x0) * e])
            self.frame()

    def type_text(self, text, ms_per=110):
        for ch in text:
            self.pg.keyboard.type(ch)
            self.wait(ms_per)

    def note(self, s: str):
        super().note(s)
        if os.environ.get("FEAT_VERBOSE"):
            print(self.log[-1], flush=True)


# ------------------------------------------------------------------ 共用
def goto(pg, hash_, wait=3500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(400)


def scroll_to(pg, sel, off=70):
    y = pg.evaluate("([s,o]) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - o : 0; }", [sel, off])
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(600)


def rel(a, sel, fx, fy):
    b = a.pg.locator(sel).first.bounding_box()
    return b["x"] + b["width"] * fx, b["y"] + b["height"] * fy


SLICE_JS = r"""([sel, i]) => { const host = document.querySelector(sel); if (!host || !window.echarts) return null;
  const ch = echarts.getInstanceByDom(host); if (!ch) return null;
  try { const L = ch.getModel().getSeriesByIndex(0).getData().getItemLayout(i); if (!L) return null;
    const a = (L.startAngle + L.endAngle) / 2, rr = (L.r + (L.r0 || 0)) / 2;
    const hr = host.getBoundingClientRect(); return [hr.left + L.cx + rr * Math.cos(a), hr.top + L.cy + rr * Math.sin(a)]; } catch (e) { return null; } }"""


def tap_slice(a, sel, i, label, keep=False):
    """點 ECharts 圓餅／時鐘的第 i 塊（中心取自 ECharts 量到的扇區中心）。"""
    pt = a.pg.evaluate(SLICE_JS, [sel, i])
    if not pt:
        a.note(f"量不到扇區 {sel} {i}")
        return False
    a.click_pt(pt[0], pt[1], label, measured_by="echarts 扇區中心", keep=keep)
    return True


LEGEND_JS = r"""([sel, i]) => { const host0 = document.querySelector(sel); if (!host0 || !window.echarts) return null;
  const host = host0.hasAttribute('_echarts_instance_') ? host0 : host0.querySelector('[_echarts_instance_]'); const ch = host && echarts.getInstanceByDom(host); if (!ch) return null;
  try { const lv = ch.getViewOfComponentModel(ch.getModel().getComponent('legend')); const hr = host.getBoundingClientRect(); const kids = []; lv._contentGroup.eachChild(c => kids.push(c));
    const c = kids[i]; if (!c) return null; const br = c.getBoundingRect(); const m = c.getComputedTransform ? c.getComputedTransform() : c.transform; let x = br.x + br.width / 2, y = br.y + br.height / 2;
    if (m) { const nx = m[0] * x + m[2] * y + m[4], ny = m[1] * x + m[3] * y + m[5]; x = nx; y = ny; } return [hr.left + x, hr.top + y]; } catch (e) { return null; } }"""


def legend_click(a, sel, i, label, keep=False):
    """點 ECharts 圖例第 i 項（開關那條線；中心取自 ECharts 量到的圖例項外框）。"""
    pt = a.pg.evaluate(LEGEND_JS, [sel, i])
    if not pt:
        a.note(f"量不到圖例 {sel} {i}")
        return False
    a.click_pt(pt[0], pt[1], label, measured_by="echarts 圖例項外框", keep=keep)
    return True


TEXT_RECT_JS = r"""(sel) => { const e = document.querySelector(sel); if (!e) return null; const r = document.createRange(); r.selectNodeContents(e);
  const rs = [...r.getClientRects()].filter(q => q.width > 1 && q.height > 1); if (!rs.length) return null;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; rs.forEach(q => { x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom); });
  return [x0, y0, x1 - x0, y1 - y0]; }"""


def text_rect(pg, sel, pad=4):
    """元素裡文字實際佔的外框（長段落只佔左半時，取景不必把整個空白欄位框進來）→ 'rect:x,y,w,h' 選擇器字串。"""
    r = pg.evaluate(TEXT_RECT_JS, sel)
    if not r:
        return None
    return f"rect:{r[0] - pad:.0f},{r[1] - pad:.0f},{r[2] + 2 * pad:.0f},{r[3] + 2 * pad:.0f}"


def analyze(r, dsf):
    """錄完後逐格比對：被介紹元素有沒有被網頁上的東西蓋住（occ）、游標有沒有落在被介紹元素上（點擊窗口以外）。"""
    n = len(r["cams"])
    occ_rows = []
    for k in range(n):
        if r["occ"][k]:
            occ_rows.append((round(k / FPS, 2), "；".join(r["occ"][k])))
    # 點擊窗口
    cl = sorted(c["t"] for c in r["clicks"] if c.get("kind") in ("click", "dragstart"))
    wins = []
    for t in cl:
        w0, w1 = t - 0.25, t + 0.35
        if wins and w0 <= wins[-1][1] + 0.75:
            wins[-1][1] = w1
        else:
            wins.append([w0, w1])
    cb = CURSOR_BOX_M if r["mob"] else CURSOR_BOX_D
    cur_rows = []
    for k in range(n):
        cx, cy, hid = r["cur"][k]
        if hid or not r["items"][k]:
            continue
        t = k / FPS
        if any(w0 <= t <= w1 for w0, w1 in wins):
            continue
        bx0, by0 = cx + cb[0] * dsf, cy + cb[1] * dsf
        bx1, by1 = bx0 + cb[2] * dsf, by0 + cb[3] * dsf
        for it in r["items"][k]:
            if bx0 < it[0] + it[2] and bx1 > it[0] and by0 < it[1] + it[3] and by1 > it[1]:
                cur_rows.append((round(t, 2), "游標在被介紹元素上"))
                break
    return occ_rows, cur_rows, wins


def run(dev, shots, out, port, reg, content_sel):
    cfg = dict(DEVS[dev])
    if CFG.get("vp_d") and dev == "d":
        cfg["viewport"] = dict(CFG["vp_d"])
    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
    site = Path(os.environ.get("FEAT_SITE", str(C.SITE)))
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((site / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            for sid in shots or list(reg):
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                # 網站 00:00～05:00 自動切深色（DECISIONS #360）：錄影時鐘固定在台北下午 14:30（凌晨錄就用前一天），一律亮色主題
                tpe = _dt.timezone(_dt.timedelta(hours=8))
                now = _dt.datetime.now(tz=tpe)
                day = now.date() if now.hour >= 5 else now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(day.year, day.month, day.day, 14, 30, tzinfo=tpe))
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                ctx.add_init_script(NOTIP_JS)
                if CFG.get("blur_js"):
                    ctx.add_init_script(CFG["blur_js"])
                for js in CFG.get("init", []):
                    ctx.add_init_script(js)
                ctx.add_init_script(CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"], dev)
                a.x, a.y = (700, 400) if dev == "d" else (370, 160)
                a._cx, a._cy = a.x, a.y
                a.dsf = cfg["device_scale_factor"]
                a.hide_cursor()   # 錄影一開始游標先藏起來（需求那一拍沒有要點的東西），第一次點擊前才現身
                rec = Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    a._put(a.x, a.y)
                    rec.start(Path(out) / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a._probe_font()
                    mp4 = Path(out) / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = pg.evaluate("(s) => { const e = document.querySelector(s); if (!e) return [0, innerWidth]; const r = e.getBoundingClientRect(); return [r.left, r.right]; }", content_sel)
                    r.update(fabs=rec.fabs, blocks_tbl=rec.blocks_tbl, blocks_idx=rec.blocks_idx, edges=rec.edges, items=rec.items, occ=rec.occ, cur=rec.cur, mob=(dev == "m"), size=[W, H], dsf=a.dsf,
                             content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             fonts=a.fonts, steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    occ_rows, cur_rows, wins = analyze(r, a.dsf)
                    r["occ_rows"], r["cursor_rows"], r["click_windows"] = occ_rows, cur_rows, wins
                    (Path(out) / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
                    print("  遮擋(網頁)", len(occ_rows), occ_rows[:6], "｜游標", len(cur_rows), cur_rows[:6])
                except Exception as exc:  # noqa: BLE001
                    rec.on = False
                    import traceback
                    traceback.print_exc()
                    print(sid, "失敗", exc)
                    print("\n".join(a.log[-12:]))
                    shutil.rmtree(Path(out) / f".tmp_{dev}_{sid}", ignore_errors=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()
