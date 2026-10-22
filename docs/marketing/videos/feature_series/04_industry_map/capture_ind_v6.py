"""功能介紹影片 04 產業地圖 v6（網頁版）—— 一鏡到底、全片不准有任何模糊（Andy 10-22）。

主線（一條因果線）：「AI 伺服器由哪些零件組成？」→ 左側選單進產業地圖、選 AI 伺服器鏈 → 2D 剖析圖連點編號（04 液冷、05 板上供電、03 電源櫃）
→ 切 3D 看同一批零件（連點三個零件標籤，最後點電源櫃）→ 零件小卡「環節：電源」→ 往下捲到 2D 供應鏈關聯圖，連點電源、散熱（上游）、系統組裝（下游）。
全程同一個視窗，鏡頭只做「一次單向推近」（引導段結束、進產業地圖那一刻，把左側選單推出畫面）與頁面往下捲；沒有換場、沒有淡化霧罩、沒有疊影。
每一格另外記錄：浮層外框（網站提示框、說明卡）、3D 標籤外框（互相壓到也算遮擋）、被介紹元素外框、所有看得到的文字外框（檢查框邊切字）、游標外框、客服鈕。
10-22：公司名稱、代號、股價照網站原樣顯示（不再模糊），網站自己的毛玻璃（backdrop-filter）也關掉；每一幀查 DOM 的 computed filter／backdrop-filter 含 blur 的筆數（必須 0）。
用法：python capture_ind_v5.py [--out DIR] [--snap]  （--snap：不錄影，只在每個階段存一張截圖用來調取景）
輸出：<out>/d_main.mp4 ＋ <out>/d_main.json
"""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "05_fund_flow"))
import blurfree as BF  # noqa: E402
import capture_ind as I  # noqa: E402  v4 的共用素材（字型、錄影器；v6 不再用它的模糊 CSS）
import flowlib as F  # noqa: E402
C = I.C

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat04"))
FPS = 30
VP = {"width": 1280, "height": 720}
DSF = 3
VPM = {"width": 540, "height": 864}
DSFM = 2.5
CROPM = (0, 0, 540, 864)
CROP0 = (0, 0, 1280, 678)
CROP1 = (250, 70, 1010, 535)
CROP2 = (748, 100, 520, 317)        # 關聯圖連點環節時的第二次單向推近：只留「散熱／電源／系統組裝」那幾欄（其他欄的字不入鏡，框邊才不會切到字）        # 推近後取景（css，視窗座標）：只留內容區（側欄推出畫面）          # 開場取景（整個視窗寬，看得到左側選單）
CHAIN = "ai_server"

REC_CSS = ("#relTip,#relStick{display:none!important}"
           "html body #supFab,html body .supfab,html body #bibiRing,html body .bibiring{bottom:-300px!important}"
           ".__vr{width:24px!important;height:24px!important;border-width:2px!important;background:transparent!important}"
           ".reltip{margin:18px 0 0 22px!important}"
           "#relSec *,#chainMap *{transition:none!important}"          # 環節展開瞬間完成（不經過「長高中」的版面，框緣不會在展開途中切到字）
           ".lbl3d[data-hid],[data-edgehid]{visibility:hidden!important}"
           ".fxb-glow,.fxb-glow *{filter:none!important}")                # 剖析圖連線高亮的發光（SVG 濾鏡含高斯模糊）：整個關掉            # 被收起的 3D 標籤用屬性標記（網站每幀重設 style.visibility 蓋不掉屬性選擇器）
BLUR_SEL = ""

META_JS = r"""([blurSel, named]) => {
  const bf = window.__bfSweep ? window.__bfSweep() : { fixed: 0, left: -1, fe: 0, seen: [] };
  const vh = innerHeight, vw = innerWidth;
  const vis = (e) => { if (!e || !e.getClientRects().length) return null; for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const cs = getComputedStyle(n); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) return null; }
    const r = e.getBoundingClientRect(); return (r.width < 2 || r.height < 2) ? null : [r.left, r.top, r.width, r.height]; };
  const el = {}; for (const k in named) { const e = document.querySelector(named[k]); const r = vis(e); if (r) el[k] = r; }
  { const rs = [...document.querySelectorAll('#prod3d .mnum')].map(vis).filter(Boolean); if (rs.length) { const x0 = Math.min(...rs.map(r => r[0])), y0 = Math.min(...rs.map(r => r[1])), x1 = Math.max(...rs.map(r => r[0] + r[2])), y1 = Math.max(...rs.map(r => r[1] + r[3])); el.mnum3d = [x0, y0, x1 - x0, y1 - y0]; } }
  const ov = []; for (const [n, s] of [['relTip', '#relTip'], ['relStick', '#relStick'], ['pop', '.howpop, #howPop, [role=dialog], .toast'], ['sheet', '#mSheet'], ['topbar', innerWidth < 700 ? 'header.topbar' : '#__none']]) { document.querySelectorAll(s).forEach(e => { const r = vis(e); if (r) ov.push([n, ...r]); }); }
  const lb = []; document.querySelectorAll('.lbl3d').forEach(e => { const r = vis(e); if (r) lb.push([e.dataset.dgno || '', ...r]); });
  const txt = [];
  const root = document.querySelector('#v-industry') || document.body;
  const blurEls = blurSel ? new Set(document.querySelectorAll(blurSel)) : new Set();
  const skip = (e) => { for (let n = e; n && n !== root; n = n.parentElement) { if (blurEls.has(n)) return true; } return false; };
  const wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n, k = 0;
  while ((n = wk.nextNode()) && k < 6000) { k++; const t = n.nodeValue; if (!t || !t.trim()) continue; const e = n.parentElement; if (!e || e.closest('script,style')) continue;
    if (skip(e)) continue; const rg = document.createRange(); rg.selectNodeContents(n); const rs = rg.getClientRects();
    for (const r of rs) { if (r.width < 2 || r.height < 2) continue; if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue; if (e.closest('svg') === null && !vis(e)) continue; { const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) continue; } txt.push([r.left, r.top, r.width, r.height]); } }
  let cc = 0; { const cm = document.querySelector('#chainMap'); if (cm && cm.getClientRects().length) { const cr = cm.getBoundingClientRect();
    for (const t of txt) { const r = { l: t[0], t: t[1], r: t[0] + t[2], b: t[1] + t[3] }; if (r.b < cr.top || r.t > cr.bottom) continue; if ((r.l < cr.left - 0.5 && r.r > cr.left + 0.5) || (r.l < cr.right - 0.5 && r.r > cr.right + 0.5)) cc++; } } }
  const fab = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring')].map(vis).filter(Boolean);
  return { el, ov, lb, txt, fab, sy: Math.round(scrollY), bf, cc }; }"""

RESOLVE_JS = """() => { const L = [...document.querySelectorAll('.lbl3d')].filter(e => getComputedStyle(e).visibility !== 'hidden').map(e => ({ e, r: e.getBoundingClientRect() }));
  for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const a = L[i].r, b = L[j].r;
    if (Math.min(a.right, b.right) + 2 > Math.max(a.left, b.left) && Math.min(a.bottom, b.bottom) + 2 > Math.max(a.top, b.top)) { const big = a.height >= b.height ? i : j; L[big].e.setAttribute('data-hid', '1'); } } }"""

EDGE_JS = """([x0, y0, x1, y1]) => { document.querySelectorAll('[data-edgehid="1"]').forEach(e => e.removeAttribute('data-edgehid'));
  const root = document.querySelector('#v-industry') || document.body; const wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n, k = 0, hid = 0;
  while ((n = wk.nextNode()) && k < 8000) { k++; if (!n.nodeValue || !n.nodeValue.trim()) continue; const e = n.parentElement; if (!e || e.closest('script,style')) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) { if (r.width < 2 || r.height < 2) continue;
      const inx = Math.min(r.right, x1) - Math.max(r.left, x0) > 0, iny = Math.min(r.bottom, y1) - Math.max(r.top, y0) > 0; if (!inx || !iny) continue;
      const cut = !(r.left >= x0 + 2.1 && r.right <= x1 - 2.1 && r.top >= y0 + 2.1 && r.bottom <= y1 - 2.1) && Math.min(r.right, x1) - Math.max(r.left, x0) > 0.5 && Math.min(r.bottom, y1) - Math.max(r.top, y0) > 0.5;   // 沒有完整落在「取景框內縮 2.6px」之內、卻有一部分探進取景框 → 隱藏
      if (cut) { e.setAttribute('data-edgehid', '1'); hid++; break; } } }
  return hid; }"""

EDGE_X_JS = """() => { document.querySelectorAll('[data-edgehid="1"]').forEach(e => e.removeAttribute('data-edgehid'));
  const cm = document.querySelector('#chainMap'); if (!cm || !cm.getClientRects().length) return 0; const cr = cm.getBoundingClientRect(); let hid = 0, n, k = 0;
  const wk = document.createTreeWalker(cm, NodeFilter.SHOW_TEXT);
  while ((n = wk.nextNode()) && k < 6000) { k++; if (!n.nodeValue || !n.nodeValue.trim()) continue; const e = n.parentElement; if (!e) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) { if (r.width < 2 || r.height < 2 || r.bottom < cr.top || r.top > cr.bottom) continue;
      if ((r.left < cr.left + 0.5 && r.right > cr.left + 0.5) || (r.left < cr.right - 0.5 && r.right > cr.right - 0.5) || (r.right <= cr.left + 0.5 && r.right > cr.left - 40)) { e.setAttribute('data-edgehid', '1'); hid++; break; } } }
  return hid; }"""

EDGE_V_JS = """() => { document.querySelectorAll('[data-edgehid="v"]').forEach(e => e.removeAttribute('data-edgehid'));
  const wk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, k = 0, hid = 0; const vw = innerWidth, vh = innerHeight;
  while ((n = wk.nextNode()) && k < 9000) { k++; if (!n.nodeValue || !n.nodeValue.trim()) continue; const e = n.parentElement; if (!e || e.closest('script,style,#mSheet,header.topbar,#m4Drawer,.m4drawer,canvas')) continue;
    const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) { if (r.width < 2 || r.height < 2 || r.bottom < 56 || r.top > vh) continue;
      if ((r.left < 3 && r.right > 3) || (r.left < vw - 3 && r.right > vw - 3) || (r.top < vh - 1 && r.bottom > vh - 1)) { e.setAttribute('data-edgehid', 'v'); hid++; break; } } }
  return hid; }"""

NAMED = {
    "burger": "#m4Burger",
    "m4ind": '.m4item[data-v="industry"]',
    "dgbody": "#dgBody",
    "sheet": "#mSheet",
    "tab": '#tabs .tab[data-view="industry"]',
    "chain": f'#chainSwitch button[data-c="{CHAIN}"]',
    "tog": "#dg3d",
    "card3": "#prodDiagram .dgcol.l .dgc:nth-child(3)",
    "card4": "#prodDiagram .dgcol.l .dgc:nth-child(4)",
    "card5": "#prodDiagram .dgcol.l .dgc:nth-child(5)",
    "card6": "#prodDiagram .dgcol.r .dgc:nth-child(1)",
    "lbl": ".lbl3d.on, .lbl3d.sel, .lbl3d.open",
    "dg": "#prodDiagram svg.dg",
    "canvas": "#prod3d canvas",
    "part": "#partCard",
    "seg_power": '#relSec .segbox[data-seg="power"]',
    "seg_thermal": '#relSec .segbox[data-seg="thermal"]',
    "seg_assembly": '#relSec .segbox[data-seg="assembly"]',
    "power": '#relSec .segbox[data-seg="power"]',
    "thermal": '#relSec .segbox[data-seg="thermal"]',
    "assembly": '#relSec .segbox[data-seg="assembly"]',
    "t_power": '#relSec .segtitle[data-seg="power"]',
    "t_thermal": '#relSec .segtitle[data-seg="thermal"]',
    "t_assembly": '#relSec .segtitle[data-seg="assembly"]',
}


class Rec(F.Rec):
    def start(self, tmpdir):
        self.fm = []
        self.ff = None
        if not self.dry:
            self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
                                        "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                                        "-r", str(FPS), "-movflags", "+faststart", str(self.tmp_out)], stdin=subprocess.PIPE)
        return super(F.Rec, self).start(tmpdir)

    def frame(self):
        if not self.on:
            return
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
        if self.act.stage >= 1 and not self.act.mob:
            try:   # 被畫面框邊切過一半的字整段先隱藏，不讓半截字入鏡（引導段框＝整個視窗 CROP0，剖析圖／3D／關聯圖段框＝推近後的 CROP1）
                cr_ = CROP0 if self.act.stage < 3 else CROP1
                self.edge_hid = self.pg.evaluate(EDGE_JS, [cr_[0], cr_[1], cr_[0] + cr_[2], cr_[1] + cr_[3]])
            except Exception:  # noqa: BLE001
                pass
        if self.act.stage >= 1 and self.act.mob:
            try:   # 手機：畫面左右緣、底緣切過一半的字整段隱藏（不讓半截字入鏡）
                self.pg.evaluate(EDGE_V_JS)
            except Exception:  # noqa: BLE001
                pass
        if self.act.stage == 5 and self.act.mob:
            try:   # 手機關聯圖：被橫向捲動容器左右邊切過一半的字整段隱藏（只剩節點外框的圓角邊，不留半截字）
                self.pg.evaluate(EDGE_X_JS)
            except Exception:  # noqa: BLE001
                pass
        if self.act.stage == 4 and not self.act.mob:
            try:   # 3D 標籤：任何兩張標籤只要相交，每一幀拍照前就把較高的那張收起（不相關的標籤隱藏）
                self.pg.evaluate(RESOLVE_JS)
            except Exception:  # noqa: BLE001
                pass
        try:
            bf0 = self.pg.evaluate("() => window.__bfSweep ? window.__bfSweep() : null")   # 截圖前先掃一次：任何含 blur 的 filter／backdrop-filter 先關掉，再拍
        except Exception:  # noqa: BLE001
            bf0 = None
        if not self.dry:
            r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True, "captureBeyondViewport": False})
            self.ff.stdin.write(C.base64.b64decode(r["data"]))
        self.n += 1
        try:
            m = self.pg.evaluate(META_JS, [BLUR_SEL, NAMED])
        except Exception:  # noqa: BLE001
            m = {"el": {}, "ov": [], "lb": [], "txt": [], "fab": [], "sy": 0, "bf": {"fixed": 0, "left": -1, "fe": 0, "seen": []}}
        a = self.act
        m["cur"] = [round(getattr(a, "pcx", a.x), 1), round(getattr(a, "pcy", a.y), 1)]
        m["stage"] = a.stage
        m["bf0"] = bf0
        self.fm.append(m)

    def stop(self, out_mp4):
        self.on = False
        try:
            self.pg.clock.resume()
        except Exception:  # noqa: BLE001
            pass
        if self.ff:
            self.ff.stdin.close()
            self.ff.wait()
        return {"ok": True, "dur": round(self.n / FPS, 2), "frames": self.n, "bad": self.bad}


class A(I.A):
    def __init__(self, pg, vw, vh, mob=False):
        super().__init__(pg, mob, vw, vh)
        self.stage = 0
        self.stages = []
        self.pend = None
        self.clears = []
        self.snap_dir = None

    def _put(self, x, y):
        super()._put(x, y)
        self.pcx, self.pcy = x, y

    def set_stage(self, n, name):
        self.pend = (n, name)

    def clear_say(self):
        self.settle()
        self.clears.append(round(self.t, 3))

    def say(self, text, act="talk_explain_v2", focus=()):
        assert len(text.replace(" ", "")) <= 14, text
        self.settle()
        if self.pend:
            self.stage = self.pend[0]
            self.stages.append([round(self.t, 3), self.pend[0], self.pend[1]])
            self.pend = None
        self.says.append({"t": round(self.t, 3), "text": text, "act": act, "focus": list(focus)})
        self.say_t, self.say_need = self.t, I.bubble_dur(text) + 0.08

    def cam(self, *a, **k):
        pass

    def cam_view(self, *a, **k):
        pass

    def park(self, *a, **k):
        pass

    def occ_now(self):
        return None

    def move(self, x, y, ms=600):
        """桌機：游標走「避開所有文字外框」的路徑（外框＝畫面上看得到的文字＋3D 標籤）；找不到路才直走。手機照舊。"""
        if self.mob or ms < 120 or abs(x - self.x) + abs(y - self.y) < 40:
            return super().move(x, y, ms)
        try:
            m = self.pg.evaluate(META_JS, [BLUR_SEL, {}])
            rects = [tuple(z) for z in m["txt"]] + [tuple(z[1:]) for z in m["lb"]]
        except Exception:  # noqa: BLE001
            rects = []
        path = BF.safe_path(rects, (self.x, self.y), (x, y), W=VP["width"], H=VP["height"])
        if not path or len(path) < 2:
            return super().move(x, y, ms)
        tot = sum(math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1]) for i in range(len(path) - 1)) or 1.0
        for i in range(len(path) - 1):
            seg = math.hypot(path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            last = i == len(path) - 2
            super().move(x if last else path[i + 1][0], y if last else path[i + 1][1], max(40, int(ms * seg / tot)))

    def go(self, x, y, ms=420):
        self.move(x, y, ms)

    def snap(self, name):
        if self.snap_dir:
            self.pg.screenshot(path=str(self.snap_dir / f"{name}.png"))

    def off_click(self, x, y, label, sel=None, dx=0, dy=0, pause=100):
        self.click_xy(x, y, 300, pause, expect=sel)
        self.targets[-1]["label"] = label
        if dx or dy:
            self.move(x + dx, y + dy, 200)


def css_rect(pg, sel):
    return pg.evaluate(C.RECT_JS, sel)


def add_css(pg, css):
    pg.evaluate("(c) => { const s = document.createElement('style'); s.textContent = c; document.head.appendChild(s); }", css)


def best_scroll(pg, y0, crop, lo=-150, hi=150, step=3, focus=None):
    """在 y0 附近找「框上下緣不切過任何文字」的捲動位置（框＝視窗座標 (x,y,w,h)，文字取目前畫面上看得到的文字外框）。回傳 (scrollY, 切到的文字數)。"""
    best = None
    best_scroll.log = {}
    for d in range(lo, hi + 1, step):
        y = max(0, y0 + d)
        pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", y)
        pg.wait_for_timeout(30)
        m = pg.evaluate(META_JS, [BLUR_SEL, {}])
        cut = 0
        x, yy, w, h = crop
        for tx, ty, tw, th in m["txt"]:
            if tw < 2:
                continue
            ov_x = min(tx + tw, x + w) - max(tx, x)
            if ov_x <= 0:
                continue
            for edge in (yy, yy + h):
                if ty < edge + 3.4 and ty + th > edge - 3.4:
                    cut += 1
        best_scroll.log[d] = (cut, [[round(v) for v in z] for z in m['txt'] if z[2] >= 2 and min(z[0] + z[2], x + w) - max(z[0], x) > 0 and any(z[1] < e + 3.4 and z[1] + z[3] > e - 3.4 for e in (yy, yy + h))][:3])
        sc = cut * 1000 + abs(d)
        if best is None or sc < best[0]:
            best = (sc, y, cut)
    return best[1], best[2]


def union_scroll(pg, crop, pad=8, lo=-14, hi=14):
    """電源、散熱、系統組裝三個環節框的聯集放進框內（上緣留 pad）→ 回傳 (捲動位置, 框緣切字數)。"""
    js = "() => { const o = ['power', 'thermal', 'assembly'].map(s => document.querySelector('#relSec .segbox[data-seg=\"' + s + '\"]').getBoundingClientRect()); return [Math.min(...o.map(r => r.top)) + scrollY, Math.max(...o.map(r => r.bottom)) + scrollY]; }"
    y0, y1 = pg.evaluate(js)
    return best_scroll(pg, y0 - pad - crop[1], crop, lo, hi, 1), (y0, y1)


def tab_pt(pg, sel, dx=0.5):
    r = css_rect(pg, sel)
    return r[0] + r[2] * dx, r[1] + r[3] / 2


def set_labels_hidden(pg, nos):
    pg.evaluate("(nos) => { document.querySelectorAll('.lbl3d').forEach(e => { e.removeAttribute('data-hid'); }); nos.forEach(n => { const e = document.querySelector('.lbl3d[data-dgno=\"' + n + '\"]'); if (e) e.setAttribute('data-hid', '1'); }); }", nos)


def neighbors_below(pg, no, span=150):
    """同一欄、在這張標籤下面 span px 內的鄰居標籤編號（點開會長高，會壓到它們 → 先藏起來）。"""
    return pg.evaluate("""([no, span]) => { const L = [...document.querySelectorAll('.lbl3d')].map(e => { const r = e.getBoundingClientRect(); return [e.dataset.dgno, r.left, r.top, r.bottom]; });
      const me = L.find(q => q[0] === no); if (!me) return []; return L.filter(q => q[0] !== no && Math.abs(q[1] - me[1]) < 60 && q[2] >= me[2] - 130 && q[2] < me[2] + span).map(q => q[0]); }""", [no, span])


def resolve_label_overlaps(pg):
    """點開後：任何跟「已展開標籤」相交的其他可見標籤一律收起（互相壓到也算遮擋）。"""
    return pg.evaluate("""() => { const L = [...document.querySelectorAll('.lbl3d')].filter(e => getComputedStyle(e).visibility !== 'hidden').map(e => ({ e, r: e.getBoundingClientRect(), no: e.dataset.dgno }));
      let hid = 0; for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const a = L[i].r, b = L[j].r;
        if (Math.min(a.right, b.right) > Math.max(a.left, b.left) && Math.min(a.bottom, b.bottom) > Math.max(a.top, b.top)) { const big = a.height >= b.height ? j : i; L[big].e.setAttribute('data-hid', '1'); hid++; } }
      return hid; }""")


def seg_scroll(pg, seg, crop, margin=3):
    """把被點的環節框（展開後）整個放進取景框（上下各留 8px），在可行範圍內找「框邊不切到任何文字」的捲動位置。回傳 (scrollY, 切字數, 框是否放得下)。"""
    sel = NAMED["seg_" + seg]
    r = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.top + scrollY, r.height]; }", sel)
    top, h = r
    x, yy, w, hh = crop
    lo = top + h + margin - (yy + hh)   # 框底剛好放進去的捲動位置
    hi = top - margin - yy              # 框頂剛好放進去的捲動位置
    fits = lo <= hi
    best = None
    sy0 = pg.evaluate("() => scrollY")
    rng = range(int(lo), int(hi) + 1) if fits else [int((lo + hi) / 2)]
    cand = [v for v in rng]
    step = max(1, len(cand) // 60)
    for y in cand[::step] if len(cand) > 1 else cand:
        pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", y)
        pg.wait_for_timeout(25)
        m = pg.evaluate(META_JS, [BLUR_SEL, {}])
        cut = 0
        for tx, ty, tw, th in m["txt"]:
            if tw < 2 or min(tx + tw, x + w) - max(tx, x) <= 0:
                continue
            for edge in (yy, yy + hh):
                if ty < edge + 3.4 and ty + th > edge - 3.4:
                    cut += 1
        sc = cut * 1000 + abs(y - sy0) * 0.01
        if best is None or sc < best[0]:
            best = (sc, y, cut)
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", sy0)
    return best[1], best[2], fits


def run(a, pg, start, snap=False):
    # ── 錄影前：預熱 3D（載入 three.js 與模型），再回總覽（不入鏡）──
    pg.evaluate("() => { location.hash = '#industry/%s'; }" % CHAIN)
    pg.wait_for_timeout(4500)
    I.warm3d(pg)
    I.anim_off(pg)
    pg.evaluate("() => { location.hash = '#overview'; scrollTo(0, 0); }")
    pg.wait_for_timeout(3500)
    a.x, a.y = 600, 24     # 開場游標停在頂欄空白處（導覽鈕與日期之間，不壓字）
    start()
    # 1 需求：為什麼要看這個功能（2 則泡泡、約 3 秒）
    a.set_stage(1, "需求")
    a.say("AI 伺服器熱，誰在供貨？", "face_think_v2", ("tab",))
    a.idle(300)
    a.say("一張圖看懂零件、上下游", "magnifier", ("tab",))
    tx, ty = tab_pt(pg, NAMED["tab"], 0.82)
    a.move(tx, 24, 700)
    a.move(tx, ty, 450)
    # 2 引導：點產業地圖、選 AI 伺服器鏈
    a.set_stage(2, "引導")
    a.say("點產業地圖，選 AI 伺服器", "point_r_v2", ("tab", "chain"))
    a.wait(250)
    a.off_click(tx, ty, "選單：產業地圖", NAMED["tab"], dx=30, dy=20)
    a.until(f"() => !!document.querySelector('#chainSwitch button[data-c=\"{CHAIN}\"]')", 8000)
    a.wait(800)
    bx, by = tab_pt(pg, NAMED["chain"], 0.5)
    a.move(bx + 5, by - 50, 380)
    a.off_click(bx, by, "產業鏈：AI 伺服器", NAMED["chain"], dx=60, dy=60, pause=90)
    a.until("() => !!document.querySelector('#prodDiagram .dgc')", 8000)
    a.move(1251, 150, 450)
    a.wait(400)
    a.snap("s2")
    # 3 2D 剖析圖：連點編號 06 → 04 → 05 → 03（單向往下捲到工具列貼近框上緣）
    a.set_stage(3, "剖析圖")
    a.say("點編號，圖上零件跟著亮", "spotlight", ("card3", "card4", "card5", "card6", "dg"))
    tgt = pg.evaluate("() => document.querySelector('#dg3d').getBoundingClientRect().top + scrollY") - 76
    sy_now = pg.evaluate("() => scrollY")
    tgt, cuts = best_scroll(pg, tgt, CROP1, -26, 26, 1)
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", sy_now)
    a.note(f"剖析圖捲動位置 {tgt}，框緣切字 {cuts}")
    a.scroll(to_y=tgt, ms=650)
    a.snap("s3a")
    PARK = (1251, 150)
    a.move(*PARK, 260)
    for k, lab in ((6, "編號卡 06 液冷冷板"), (4, "編號卡 04 液冷"), (5, "編號卡 05 板上供電"), (3, "編號卡 03 電源櫃")):
        sel = NAMED[f"card{k}"]
        r = css_rect(pg, sel)
        a.move(r[0] - 40, r[1] + r[3] / 2, 340)
        a.off_click(r[0] + r[2] * 0.94, r[1] + r[3] * 0.5, lab, sel, dx=0, dy=0, pause=80)
        a.move(*PARK, 220)
        a.wait(1000)
        a.snap(f"s3_{k}")
    a.settle()
    # 4 切 3D：拖曳旋轉一次、連點 5 個不同環節的零件（04 運算托盤、06 HBM、09 液冷冷板、14 光模組、12 電源櫃）
    a.set_stage(4, "3D")
    a.say("切 3D，點零件看說明", "3dglasses", ("tog", "canvas"))
    r3 = css_rect(pg, '#dg3d button[data-dm="3d"]')
    a.move(r3[0] + r3[2] + 30, r3[1] + r3[3] / 2 + 30, 340)
    a.off_click(r3[0] + r3[2] * 0.8, r3[1] + r3[3] / 2, "切 3D", '#dg3d button[data-dm="3d"]', dx=0, dy=0, pause=70)
    a.move(r3[0] + r3[2] * 0.8, 36, 180)
    a.move(1251, 36, 220)
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.move(*PARK, 100)
    a.wait_still3d(pg)
    a.snap("s4a")
    cv = css_rect(pg, "#prod3d canvas")
    cxm = cv[0] + cv[2] / 2
    a.cursor(True)
    a.drag(cxm - 150, cv[1] + 44, cxm + 100, cv[1] + 50, 900)   # 在機櫃上方空白處拖曳旋轉一次（不經過機櫃與標籤）
    a.wait(80)
    a.move(*PARK, 220)
    a.wait_still3d(pg)
    for no, lab in (("04", "零件：04 運算托盤 GPU"), ("06", "零件：06 HBM 記憶體"), ("09", "零件：09 液冷冷板"), ("14", "零件：14 光模組 CPO"), ("12", "零件：12 電源櫃")):
        sel = I.lbl(no)
        set_labels_hidden(pg, neighbors_below(pg, no))   # 點開會長高：把它正下方的鄰居標籤先收起來（避免標籤互相壓到）
        a.wait(40)
        lr = css_rect(pg, sel)
        a.move(lr[0] + lr[2] + 40 if lr[0] > 640 else lr[0] - 40, lr[1] + 16, 340)
        a.click_now(sel, lab, ms=160, pause=70, dx=0.96, dy_px=14)
        resolve_label_overlaps(pg)
        a.wait(30)
        resolve_label_overlaps(pg)
        a.move(*PARK, 220)
        a.wait(1000)
        a.snap(f"s4_{no}")
    a.settle()
    # 5 零件小卡「環節：電源」→ 2D 關聯圖：連點 3 個環節（散熱、電源、系統組裝），每個展開、成分公司完整入鏡
    a.set_stage(5, "關聯圖")
    a.say("點環節，看上下游與成分公司", "talk_explain_v2", ("part",))
    y0 = pg.evaluate("() => document.querySelector('#partCard').getBoundingClientRect().top + scrollY") - 70
    sy_now = pg.evaluate("() => scrollY")
    y1, cuts = best_scroll(pg, y0, CROP1, -20, 20, 1)
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", sy_now)
    a.note(f"零件卡捲動位置 {y1}，框緣切字 {cuts}")
    a.scroll(to_y=y1, ms=700)
    a.snap("s5a")
    a.wait(900)
    set_labels_hidden(pg, [])
    PARK2 = (1275, 120)
    for sg, lab in (("thermal", "環節：散熱（上游）"), ("power", "環節：電源"), ("assembly", "環節：系統組裝（下游）")):
        y2, c2, fits = seg_scroll(pg, sg, CROP1)
        a.note(f"{sg} 點前捲到 {y2}（切字 {c2}，放得下 {fits}）")
        if abs(y2 - pg.evaluate("() => scrollY")) > 1:
            a.scroll(to_y=y2, ms=600)
        t = NAMED["t_" + sg]
        r = css_rect(pg, t)
        a.move(r[0] + r[2] + 30, r[1] - 24, 320)
        px = pg.evaluate("""([s, x0, x1, y]) => { for (let x = x1; x >= x0; x -= 2) { const e = document.elementFromPoint(x, y); if (e && e.closest && e.closest(s)) return x; } return null; }""", [t, r[0], r[0] + r[2], r[1] + r[3] / 2])
        a.off_click(px if px else r[0] + r[2] * 0.5, r[1] + r[3] * 0.5, lab, t, dx=0, dy=0, pause=70)
        y3, c3, fits3 = seg_scroll(pg, sg, CROP1)     # 展開是瞬間完成（關了 CSS 轉場）→ 馬上量、馬上捲，成分公司整塊入鏡
        a.note(f"{sg} 展開後捲到 {y3}（切字 {c3}，放得下 {fits3}）")
        a.move(*PARK2, 60)       # 游標先離開標題文字，再捲動（捲動中游標已不在字上）
        a.scroll(to_y=y3, ms=300)
        a.wait(1100)
        a.snap("s5_" + sg)
    a.settle()
    return a


def tap_blank(a, pg, x, y, label):
    a.click_xy(x, y, 1, 60)
    a.targets[-1]["label"] = label
    a.targets[-1]["blank"] = True
    a.lift(ms=100)


def run_m(a, pg, start, snap=False):
    pg.evaluate("() => { location.hash = '#industry/%s'; }" % CHAIN)
    pg.wait_for_timeout(4500)
    I.warm3d(pg)
    I.anim_off(pg)
    pg.add_style_tag(content="body{padding-bottom:900px!important}")
    pg.evaluate("() => { location.hash = '#overview'; scrollTo(0, 0); }")
    pg.wait_for_timeout(3500)
    a.x, a.y = 2, 60          # 滑鼠停在左上角（頂欄邊緣）：頁面捲動時圖表不會因為滑鼠停在上面而跳出提示框（start() 會把滑鼠放到 a.x,a.y）
    start()
    a.cursor(False)
    # 1 需求（2 則泡泡）
    a.set_stage(1, "需求")
    a.say("AI 伺服器熱，誰在供貨？", "face_think_v2", ("burger",))
    a.scroll(to_y=260, ms=1500)      # 開頭不靜止：總覽頁慢慢往下帶一段，再回頂（選單鈕在最上面）
    a.say("一張圖看懂零件、上下游", "magnifier", ("burger",))
    a.scroll(to_y=0, ms=1400)
    # 2 引導
    a.set_stage(2, "引導")
    a.say("點選單，選 AI 伺服器", "point_ur_v2", ("burger", "m4ind"))
    a.click("#m4Burger", label="選單", ms=200, pause=80)
    a.lift(ms=90)
    a.wait(600)
    a.click('.m4item[data-v="industry"]', label="選單：產業地圖", ms=200, pause=80)
    a.lift(ms=90)
    a.until(f"() => !!document.querySelector('#chainSwitch button[data-c=\"{CHAIN}\"]')", 8000)
    a.wait(700)
    a.click(f'#chainSwitch button[data-c="{CHAIN}"]', label="產業鏈：AI 伺服器", ms=200, pause=80)
    a.lift(ms=90)
    a.until("() => !!document.querySelector('a.segchip[data-dgtab]')", 8000)
    a.wait(700)
    a.click('.lv2.m4seg > :nth-child(2)', label="分頁：AI 伺服器（產品剖析圖）", ms=200, pause=80)   # 手機點產業鏈後先進「族群總覽」，再點第二個分頁進產品剖析圖
    a.lift(ms=90)
    a.until("() => !!document.querySelector('#dgBody .mnum')", 8000)
    a.wait(500)
    # 3 剖析圖：點編號 05，再用面板「‹」換 04、03、02
    add_css(pg, "#mSheet{box-shadow:none!important;border-top:2px solid #cbd5e1!important}")
    pg.evaluate("() => { const s = document.createElement('style'); s.id = '__hidemap'; s.textContent = '#chainMap{visibility:hidden!important}'; document.head.appendChild(s); }")   # 底部面板開著時，面板上緣不留被切掉的關聯圖文字
    a.set_stage(3, "剖析圖")
    a.say("點編號，看零件說明", "spotlight", ("dg",))
    a.scroll(to_y=pg.evaluate("() => document.querySelector('#dg3d').getBoundingClientRect().top + scrollY") - 60, ms=650)
    a.snap("m3a")
    a.click_now('#dgBody .mnum[data-no="05"]', "編號 05 板上供電", ms=120, pause=80)
    a.lift(ms=90)
    a.wait(900)
    for lab in ("抽屜「‹」：編號 04 液冷", "抽屜「‹」：編號 03 電源櫃", "抽屜「‹」：編號 02 整機櫃"):
        a.click_now('#mSheet .mshnav button[data-d="-1"]', lab, ms=120, pause=80)
        a.lift(ms=90)
        a.wait(850)
    a.snap("m3b")
    # 4 切 3D：拖曳旋轉、點編號後用「›」連換 5 個零件
    a.set_stage(4, "3D")
    a.say("切 3D，點編號看說明", "3dglasses", ("tog", "mnum3d"))
    tap_blank(a, pg, 270, 560, "點空白處收起說明面板")
    a.wait(300)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D", ms=160, pause=80)
    a.lift(ms=60)
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.wait(500)
    a.snap("m4a")
    c = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    a.drag(c[0] + 40, c[1] + 30, c[0] + 150, c[1] + 36, 900)
    a.lift(ms=60)
    a.wait_still3d(pg)
    start_no = I.pick_badge(pg, ("09", "11", "10", "14", "15", "13", "12"))
    a.click_now(f'#prod3d .mnum[data-no="{start_no}"]', f"零件：編號 {start_no}", ms=120, pause=80)
    a.lift(ms=90)
    a.wait(800)
    cur = int(start_no)
    for _ in range(4):
        d = 1 if cur < 13 else -1
        cur += d
        a.click_now(f'#mSheet .mshnav button[data-d="{d}"]', f"抽屜「{'›' if d == 1 else '‹'}」：編號 {cur:02d}", ms=120, pause=80)
        a.lift(ms=90)
        a.wait(800)
    a.snap("m4b")
    # 5 關聯圖
    a.set_stage(5, "關聯圖")
    tap_blank(a, pg, 270, 560, "點空白處收起說明面板")
    a.wait(500)
    pg.evaluate("() => { const s = document.getElementById('__hidemap'); if (s) s.remove(); }")
    a.say("點環節，看上下游與成分公司", "talk_explain_v2", ("seg_thermal", "seg_power", "seg_assembly"))
    pg.evaluate("""() => { const m = document.querySelector('#chainMap'); const t = document.querySelector('#relSec .segbox[data-seg="thermal"]'); m.style.scrollBehavior = 'auto'; m.scrollLeft += t.getBoundingClientRect().left - (m.getBoundingClientRect().left + 6); }""")
    a.wait(150)
    a.scroll(to_y=pg.evaluate("() => document.querySelector('#chainMap').getBoundingClientRect().top + scrollY") - 70, ms=700)
    a.snap("m5a")
    CM = (0, 56, 540, 808)
    for sg, lab in (("thermal", "環節：散熱（上游）"), ("power", "環節：電源"), ("assembly", "環節：系統組裝（下游）")):
        t = NAMED["t_" + sg]
        r = css_rect(pg, t)
        px = pg.evaluate("""([s, x0, x1, y]) => { for (let x = x1; x >= x0; x -= 2) { const e = document.elementFromPoint(x, y); if (e && e.closest && e.closest(s)) return x; } return null; }""", [t, r[0], r[0] + r[2], r[1] + r[3] / 2])
        a.click_xy(px if px else r[0] + r[2] / 2, r[1] + r[3] / 2, 1, 70, expect=t)
        a.targets[-1]["label"] = lab
        a.lift(ms=90)
        a.wait(250)
        y3, c3, fits3 = seg_scroll(pg, sg, CM)
        a.note(f"{sg} 展開後捲到 {y3}（切字 {c3}，放得下 {fits3}）")
        a.scroll(to_y=y3, ms=450)
        a.wait(1200)
        a.snap("m5_" + sg)
    a.settle()
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--out", default=str(SCR / "raw_v6"))
    ap.add_argument("--port", type=int, default=8822)
    ap.add_argument("--snap", action="store_true")
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    if g.snap:
        os.environ["FEAT_DRY"] = "1"
    srv = ThreadingHTTPServer(("127.0.0.1", g.port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{g.port}/index.html"
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            dev = g.dev
            if dev == "m":
                cfg = dict(viewport=VPM, device_scale_factor=DSFM, is_mobile=True, has_touch=True)
                W, H = int(VPM["width"] * DSFM), int(VPM["height"] * DSFM)
            else:
                cfg = dict(viewport=VP, device_scale_factor=DSF)
                W, H = VP["width"] * DSF, VP["height"] * DSF
            ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
            tpe = _dt.timezone(_dt.timedelta(hours=8))
            now = _dt.datetime.now(tz=tpe)
            day = now.date() if now.hour >= 5 else now.date() - _dt.timedelta(days=1)
            ctx.clock.install(time=_dt.datetime(day.year, day.month, day.day, 14, 30, tzinfo=tpe))
            I.route_fonts(ctx)
            ctx.add_init_script(I.FONT_JS)
            ctx.add_init_script(C.PRESET)
            ctx.add_init_script(C.HIDE_B_JS)
            ctx.add_init_script(BF.INIT_JS)
            ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = %s; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();" % json.dumps(REC_CSS))
            ctx.add_init_script("try{localStorage.removeItem('tw.chainFold');localStorage.removeItem('tw.dg3d.exp');localStorage.setItem('tw.dganim','0')}catch(e){}")
            if dev == "m":
                ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = '#mSheetBack,.mshback,.msheet-back{background:transparent!important}#siteFoot{display:none!important}'; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();")
                ctx.add_init_script("try{localStorage.setItem('tw.m4.3danim','0')}catch(e){}")
            ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            pg.goto(base + "#overview", wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.evaluate("() => document.fonts.ready")
            a = A(pg, cfg["viewport"]["width"], cfg["viewport"]["height"], dev == "m")
            a.dsf = cfg["device_scale_factor"]
            if g.snap:
                a.snap_dir = out / "snap"
                a.snap_dir.mkdir(exist_ok=True)
            rec = Rec(pg, W, H, a)
            tmp = out / f".{dev}_main.mp4"
            rec.tmp_out = tmp

            def start(rec=rec, a=a):
                a.rec = rec
                a._put(a.x, a.y)
                rec.start(out / f".tmp_{dev}")

            try:
                (run if dev == "d" else run_m)(a, pg, start, g.snap)
            except Exception:
                print("\n".join(a.log[-14:]))
                raise
            a.settle()
            a.idle(300)
            r = rec.stop(out / f"{dev}_main.mp4")
            if not g.snap:
                shutil.move(str(tmp), out / f"{dev}_main.mp4")
            shutil.rmtree(out / f".tmp_{dev}", ignore_errors=True)
            r.update(size=[W, H], dsf=cfg["device_scale_factor"], crop0=(CROP0 if dev == "d" else CROPM), says=a.says, marks=a.marks, clears=a.clears, stages=a.stages, clicks=a.targets, steps=a.log, errs=errs[:5], fm=rec.fm,
                     timer_errs=getattr(rec, "timer_errs", []), data_date=site_meta.get("data_date"))
            (out / f"{dev}_main.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            miss = [s for s in a.log if "找不到" in s or "點不到" in s or "⚠" in s]
            print(r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
            ctx.close()
            b.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
