"""功能介紹影片 06／07 共用錄影工具（沿用 05 資金流向 v3：一鏡到底、逐格算圖、每格記錄遮擋檢查要用的外框）。

與 05 的差別：
  · 05 的重點是 ECharts 圖，這裡的內容多是「網頁文字」（事件清單、文章卡、頁籤）→ 每格量「所有看得到的文字外框」（zt），
    合成端拿它檢查：游標／點擊波紋／浮層／清單／畫面框邊，有沒有壓到任何一個字。
  · 游標只會落在「不壓字的空白處」：點擊點由程式掃描元素範圍內「游標外框不碰任何文字」的位置挑出來；
    移動路徑若會掃過文字，就先淡出游標、在目標處淡入（不讓游標從字上滑過）。
  · 手機的手指只畫細圈（不畫灰圓）。
  · 圖表提示框（hover）在錄影的瀏覽器裡以 CSS 關掉（只在錄影時，不改 site/）；下拉清單一律畫在空白處（自繪，不蓋內容）。
輸出：<out>/<dev>_main.mp4 ＋ <out>/<dev>_main.json
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "05_fund_flow"))
import capture_flow as CF  # noqa: E402

F = CF.F
C = CF.C
FPS = 30
CFG_DEV = {
    "d": dict(viewport={"width": 1000, "height": 570}, device_scale_factor=2),
    "m": dict(viewport={"width": 540, "height": 880}, device_scale_factor=2.5, is_mobile=True, has_touch=True),
}
CROP0 = {"d": (0, 0, 1000, 570), "m": (0, 0, 540, 864)}

# ---------------------------------------------------------------- 頁面端工具
LIB_JS = r"""
window.__vclip = (pe, b) => { const c = { l: b.left, t: b.top, r: b.right, b: b.bottom };
  for (let a = pe; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
    const cs = getComputedStyle(a), own = a === pe;
    if (!own && cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
    const r = a.getBoundingClientRect();
    const pl = own ? parseFloat(cs.paddingLeft) || 0 : 0, pr = own ? parseFloat(cs.paddingRight) || 0 : 0;
    const bl = parseFloat(cs.borderLeftWidth) || 0, br = parseFloat(cs.borderRightWidth) || 0;
    c.l = Math.max(c.l, r.left + bl + pl); c.r = Math.min(c.r, r.right - br - pr);
    if (own || cs.overflowY !== 'visible') { c.t = Math.max(c.t, r.top); c.b = Math.min(c.b, r.bottom); } }
  return c; };
window.__vcharttexts = (zc) => { const zt = [];
  const list = (zc && zc.length) ? zc : [...document.querySelectorAll('[_echarts_instance_]')].map((e, i) => ['c' + i, e]);
  for (const [nm, sel] of list) { const h = typeof sel === 'string' ? document.querySelector(sel) : sel; const inst = h && window.echarts && echarts.getInstanceByDom(h); if (!inst) continue; const b = h.getBoundingClientRect();
    inst.getZr().storage.getDisplayList().forEach(d => { if (d.invisible || d.ignore || !(d.type === 'tspan' || d.type === 'text')) return; const t = d.style && d.style.text;
      if (!t || !String(t).trim() || (d.style.opacity ?? 1) < 0.05) return; const r = d.getBoundingRect().clone(); if (d.transform) r.applyTransform(d.transform);
      const l = Math.max(b.left, b.x + r.x), tp = Math.max(b.top, b.y + r.y), rr = Math.min(b.right, b.x + r.x + r.width), bb = Math.min(b.bottom, b.y + r.y + r.height);
      if (rr - l < 1 || bb - tp < 1) return;
      const hx = (l + rr) / 2, hy = (tp + bb) / 2; if (hx >= 0 && hy >= 0 && hx < innerWidth && hy < innerHeight) { const e2 = document.elementFromPoint(hx, hy); if (e2 && !h.contains(e2)) return; }   // 被抽屜／霧罩／浮層蓋住的圖表文字不算（看不到）
      zt.push([nm, l, tp, rr - l, bb - tp, 0, 0, 0]); }); }
  return zt; };
// 看得到的可操作元件外框（按鈕、輸入框、下拉、連結、頁籤）：游標停靠時也要避開（不蓋住任何控制項的圖示）
window.__vui = () => { const out = [];
  for (const e of document.querySelectorAll('input,select,textarea,button,a[href],[role=tab],canvas')) {
    if (e.closest('#__vc,.__vr,#__vsel')) continue;
    if (e.checkVisibility && !e.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
    const r = e.getBoundingClientRect(); if (r.width < 6 || r.height < 6 || r.right < 0 || r.bottom < 0 || r.left > innerWidth || r.top > innerHeight) continue;
    if (e.tagName === 'CANVAS') continue;
    const hx = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2)), hy = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
    const h = document.elementFromPoint(hx, hy); if (h && !(e.contains(h) || h.contains(e))) continue;
    out.push([r.left, r.top, r.width, r.height, 0, 0, 2]); }
  return out; };
// 看得到的文字外框：roots（選擇器陣列）底下每個文字節點，夾到捲動容器範圍內；被「非浮層」元素蓋住（例如抽屜後面的霧罩下）的不算
window.__vtexts = (roots, ovSel) => {
  const out = [];
  for (const rs of roots) for (const root of document.querySelectorAll(rs)) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      const pe = n.parentElement; if (!pe || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(pe.tagName)) continue;
      if (pe.closest('#__vc,.__vr,[hidden],[aria-hidden="true"]')) continue;
      if (pe.checkVisibility && !pe.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
      const pb = pe.getBoundingClientRect(); if (pb.width < 1 || pb.height < 1) continue;
      const cl = window.__vclip(pe, pb);
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const q of rg.getClientRects()) {
        let l = Math.max(q.left, cl.l), t = Math.max(q.top, cl.t), r = Math.min(q.right, cl.r), b = Math.min(q.bottom, cl.b);
        if (r - l < 1 || b - t < 1) continue;
        { const fs = parseFloat(getComputedStyle(pe).fontSize) || 14, ih = Math.min(b - t, fs * 1.1), dt = ((b - t) - ih) / 2; t += dt; b = t + ih; }   // 字墨範圍（行高多出來的上下空白不算字）
        const hx = (l + r) / 2, hy = (t + b) / 2; let inov = ovSel && pe.closest(ovSel) ? 1 : 0, cov = 0;
        if (hx >= 0 && hy >= 0 && hx < innerWidth && hy < innerHeight) {
          const h = document.elementFromPoint(hx, hy);
          if (h && !(pe.contains(h) || h.contains(pe))) { if (ovSel && h.closest(ovSel)) cov = 1; else continue; } }
        const bl = pe.closest('.__vblur,.__vblurrow,a[href^="#stock/"],.scode') ? 1 : 0;
        out.push([l, t, r - l, b - t, inov, cov, bl]); } } }
  // 輸入框／下拉／日期欄的字（不是文字節點）：估一塊「字」的範圍
  for (const e of document.querySelectorAll('input,select')) {
    if (!e.getClientRects().length || e.type === 'range' || e.type === 'checkbox' || e.type === 'radio' || e.type === 'hidden') continue;
    if (e.checkVisibility && !e.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
    const r = e.getBoundingClientRect(); if (r.width < 8 || r.height < 8) continue;
    const cs = getComputedStyle(e), fs = parseFloat(cs.fontSize) || 14;
    let txt = e.tagName === 'SELECT' ? (e.selectedOptions[0] ? e.selectedOptions[0].text : '') : (e.value || e.placeholder || '');
    if (e.type === 'date') txt = '0000/00/0000';
    if (!txt) continue;
    const w = Math.min(r.width - 14, txt.length * fs * (/[\u4e00-\u9fff]/.test(txt) ? 1.0 : 0.62) + 4);
    out.push([r.left + 8, r.top + (r.height - fs * 1.3) / 2, w, fs * 1.3, 0, 0, 0]); }
  return out; };
"""

# 錄影專用樣式：客服鈕移出畫面；細圈漣漪；圖表提示框關掉；手機手指只畫細圈
REC_CSS_BASE = (
    "*,*::before,*::after{backdrop-filter:none!important;-webkit-backdrop-filter:none!important;filter:none!important}"
    "html body #supFab,html body .supfab,html body #bibiRing,html body .bibiring{bottom:-200px!important}"
    "[_echarts_instance_]>div:not(:first-child){display:none!important}body>div[style*=\"9999999\"]{display:none!important}.__vmob #__vc{transition:none!important}"
    "#__vc>div:not(svg){background:transparent!important;border:3px solid #2563eb!important;width:8px!important;height:8px!important;margin:-7px 0 0 -7px!important;box-shadow:0 0 0 2px #fff!important}"
)
RING_JS = r"""
(() => { const st = document.createElement('style'); st.textContent = '.__vr{background:transparent!important;border:2px solid rgba(37,99,235,.9)!important}'; document.head.appendChild(st);
  window.__vcRipple = (x, y) => { const r = document.createElement('div'); r.className = '__vr'; const s = 10; r.style.width = r.style.height = s + 'px';
    r.style.left = x + 'px'; r.style.top = y + 'px'; document.body.appendChild(r); setTimeout(() => r.remove(), 700); };
})();
"""

META_JS = r"""() => {
  const CFG = window.__CFG;
  const vis = (e) => { if (!e || !e.getClientRects().length) return null; const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) return null;
    const r = e.getBoundingClientRect(); return (r.width < 2 || r.height < 2) ? null : [r.left, r.top, r.width, r.height]; };
  const ov = [];
  for (const s of CFG.overlays) document.querySelectorAll(s).forEach(e => { const r = vis(e); if (r) ov.push(['浮層 ' + s, ...r]); });
  document.querySelectorAll('[_echarts_instance_] > div').forEach(e => { if (e.querySelector('canvas')) return; const r = vis(e); if (r && (e.textContent || '').trim() && e !== e.parentElement.firstElementChild) ov.push(['圖表提示框', ...r]); });
  const el = {}; for (const [k, s] of Object.entries(CFG.els)) { const r = vis(document.querySelector(s)); if (r) el[k] = r; }
  const zt = window.__vtexts(CFG.roots, CFG.ovsel).map(a => ['t', ...a]);
  zt.push(...window.__vcharttexts(CFG.zcharts));
  let blur = 0; for (const e of document.querySelectorAll('*')) { const cs = getComputedStyle(e); if ((cs.filter && cs.filter.indexOf('blur') >= 0) || (cs.backdropFilter && cs.backdropFilter.indexOf('blur') >= 0) || (cs.webkitBackdropFilter && cs.webkitBackdropFilter.indexOf('blur') >= 0)) blur++; }
  const ui = window.__vui();
  const fab = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring')].map(vis).filter(Boolean);
  const cv = document.getElementById('__vc'); const cop = cv ? +getComputedStyle(cv).opacity : 1;
  return { ov, el, zt, fab, ui, blur, sy: Math.round(scrollY), cop }; }"""

FIT_JS = r"""([sels, limit]) => { for (const s of sels) document.querySelectorAll(s).forEach(e => { const r = e.getBoundingClientRect(); if (r.height > 1 && r.bottom > limit) e.style.display = 'none'; }); }"""

SEL_STRIP_JS = r"""([opts, x, y, h]) => { const d = document.createElement('div'); d.id = '__vsel';
  d.style.cssText = `position:fixed;left:${x}px;top:${y}px;height:${h}px;display:flex;align-items:center;gap:4px;padding:0 5px;z-index:2147483600;background:#fff;border:1px solid #c9d3e0;border-radius:8px;box-shadow:0 4px 14px rgba(15,23,42,.18);font:13px/1 'Noto Sans TC',sans-serif;color:#1f2937;white-space:nowrap`;
  d.innerHTML = opts.map(o => `<div data-v="${o.v}" style="padding:6px 24px;border-radius:6px;${o.on ? 'background:#e8f0fb;color:#1d4ed8;font-weight:700' : ''}">${o.t}</div>`).join('');
  const st = document.createElement('style'); st.textContent = '#__vsel .hv{background:#2563eb!important;color:#fff!important}'; d.appendChild(st); document.body.appendChild(d); }"""


def _ov(a, b):
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return ix * iy if (ix > 0 and iy > 0) else 0.0


class Rec3(CF.Rec):
    def frame(self):
        if self.on and getattr(self.act, "fit", None):
            try:
                self.pg.evaluate(FIT_JS, self.act.fit)
            except Exception:  # noqa: BLE001
                pass
        super().frame()


class A3(CF.A):
    """游標只落在不壓字的空白處。"""
    PARK_FALLBACK = (600, 20)

    def __init__(self, pg, mob, vw, vh):
        super().__init__(pg, mob, vw, vh)
        self.fit = None
        self.crop = (0, 0, vw, vh)
        self.warns: list = []
        self.cur_hidden = False

    # ---- 文字外框與游標外框
    def texts(self, roots=("body",)):
        try:
            r = self.pg.evaluate("(r) => window.__vtexts(r, '#__vsel')", list(roots))
            z = self.pg.evaluate("() => window.__vcharttexts(window.__CFG.zcharts)")
            return r + [t[1:] for t in z]
        except Exception:  # noqa: BLE001
            return []

    def cring(self):
        return 7

    def hits(self, x, y, texts, pad=0):
        """游標外框壓到文字的程度：漣漪圈（圓）距離文字外框小於半徑的深度＋箭頭外框（網頁）與文字的相交面積。"""
        tot = 0.0
        for t in texts:
            tx, ty, tw, th = t[:4]
            r = self.cring() + (min(pad, 3) if t[6] == 2 else pad)
            dx = max(tx - x, 0, x - (tx + tw))
            dy = max(ty - y, 0, y - (ty + th))
            d = (dx * dx + dy * dy) ** 0.5
            if d < r - 1.5:
                tot += (r - 1.5 - d) * 8 + 1
            if not self.mob:
                pp = min(pad, 3) if t[6] == 2 else pad
                tot += _ov((x - pp, y - pp, 18 + 2 * pp, 26 + 2 * pp), t[:4])
        return tot

    def hit_many(self, sel, pts):
        """一次問一批點：這點（含上下左右各 2px）最上層元素是不是 sel 這個元素（圓角膠囊的角落不算）。"""
        if not sel:
            return [True] * len(pts)
        try:
            return self.pg.locator(sel).first.evaluate(
                "(e, ps) => ps.map(p => [[0,0],[1,0],[-1,0],[0,1],[0,-1]].every(d => { const h = document.elementFromPoint(p[0] + d[0], p[1] + d[1]); return !!h && (e === h || e.contains(h)); }))", pts)
        except Exception:  # noqa: BLE001
            return [True] * len(pts)

    def clear_point(self, rect, texts, hit_sel=None, step=None, pad=0, bias=None):
        """rect 內挑一點：游標外框不碰任何文字，且（含四周 2px）最上層元素是目標；偏好靠近中心。"""
        x0, y0, w, h = rect
        cx, cy = (x0 + w * bias[0], y0 + h * bias[1]) if bias else (x0 + w / 2, y0 + h / 2)
        step = step or (1 if w * h < 6000 else 3)
        pts = []
        nx, ny = max(1, int((w - 2) / step)), max(1, int((h - 2) / step))
        for i in range(nx + 1):
            for j in range(ny + 1):
                pts.append((x0 + 1 + (w - 2) * i / nx, y0 + 1 + (h - 2) * j / ny))
        ok = self.hit_many(hit_sel, [list(p) for p in pts])
        cands = [(self.hits(x, y, texts, pad), (x - cx) ** 2 + (y - cy) ** 2, x, y) for (x, y), o in zip(pts, ok) if o]
        if not cands:
            cands = [(self.hits(x, y, texts, pad), (x - cx) ** 2 + (y - cy) ** 2, x, y) for (x, y) in pts]
            self.warns.append(f"{self.t:.1f}s 找不到最上層是目標的落點，退回中心")
        cands.sort()
        return cands[0][2], cands[0][3], cands[0][0]

    def path_clear(self, x0, y0, x1, y1, texts):
        d = max(abs(x1 - x0), abs(y1 - y0))
        n = max(2, int(d / 3))
        return all(self.hits(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, texts) == 0 for i in range(n + 1))

    # ---- 游標移動：路徑不壓字就滑過去，否則淡出→目標淡入
    def glide(self, x, y, texts, ms=420):
        if self.mob:
            self.x, self.y = x, y
            return
        if self.path_clear(self.x, self.y, x, y, texts):
            self.move(x, y, ms)
            return
        self.cursor(False)
        self.wait(220)
        self._put(x, y)
        self.x, self.y = x, y
        self.cursor(True)
        self.wait(220)

    def park(self, region=None, texts=None, ms=300, prefer=None):
        """游標停到「附近最近」的空白處（外框外擴 14px 都不碰字），idle 小晃也不壓字。"""
        texts = texts if texts is not None else self.texts() + self.ui_boxes()
        rx, ry, rw, rh = region or (0, 0, self.vw, self.vh)
        best = None
        px, py = prefer or (self.x, self.y)
        for i in range(0, int(rw), 10):
            for j in range(0, int(rh), 10):
                x, y = rx + i + 5, ry + j + 5
                if y < 56 and not region:
                    continue   # 頂欄（日期時間、按鈕）不當停靠區
                if self.hits(x, y, texts, 14) > 0:
                    continue
                d = (x - px) ** 2 + (y - py) ** 2
                if best is None or d < best[0]:
                    best = (d, x, y)
        if best is None:
            self.warns.append(f"{self.t:.1f}s 找不到空白停靠點")
            return
        if self.mob:
            self.x, self.y = best[1], best[2]
            return
        self.glide(best[1], best[2], texts, ms)

    def ui_boxes(self):
        try:
            return self.pg.evaluate("() => window.__vui()")
        except Exception:  # noqa: BLE001
            return []

    def tap(self, sel, label, pause=140, region_pad=0, nth=None, texts=None, bias=None):
        """游標移到元素內「不壓字」的一點 → 點下（細圈漣漪）。回傳 True/False。"""
        b = self.box(sel, scroll=False)
        if not b:
            self.note(f"點不到 {sel}")
            return False
        texts = texts if texts is not None else self.texts()
        x, y, ov = self.clear_point([b["x"], b["y"], b["width"], b["height"]], texts, sel, pad=3, bias=bias)   # 先要求離字 3px 以上
        if ov > 0:
            x, y, ov = self.clear_point([b["x"], b["y"], b["width"], b["height"]], texts, sel, bias=bias)
        if ov > 0:
            self.warns.append(f"{self.t:.1f}s 點擊落點壓字（{label}）{ov:.0f}px²")
        self.glide(x, y, texts)
        self.wait(pause)
        self.note(f"點 {label}")
        self.click_xy(x, y, 1, 0, expect=sel)
        tg = self.targets[-1]
        tg["label"] = label
        tg["rect_center"] = self._vpt(x, y)
        tg["measured_by"] = "元素內不壓字的落點"
        tg["cur_overlap"] = round(ov, 1)
        return True

    def tap_rect(self, rect, label, expect=None, pause=140, texts=None):
        """rect（css）內挑不壓字的一點點下（圖表方塊等沒有獨立選擇器的目標）。"""
        texts = texts if texts is not None else self.texts()
        x, y, ov = self.clear_point(rect, texts, None)
        if ov > 0:
            self.warns.append(f"{self.t:.1f}s 點擊落點壓字（{label}）{ov:.0f}px²")
        self.glide(x, y, texts)
        self.wait(pause)
        self.note(f"點 {label}")
        self.click_xy(x, y, 1, 0, expect=expect)
        tg = self.targets[-1]
        tg["label"] = label
        tg["rect_center"] = self._vpt(x, y)
        tg["measured_by"] = "方塊內不壓字的落點"
        tg["cur_overlap"] = round(ov, 1)

    def type_text(self, sel, text, ms_per=170):
        self.pg.locator(sel).first.focus()
        for chx in text:
            self.pg.keyboard.type(chx)
            self.wait(ms_per)

    def strip_pick(self, sel, value, opts, rect, label, hold=420):
        """自繪下拉清單（橫排一列，畫在 rect＝空白處）：游標到選項 → 點下 → 收起 → 真的選值。opts＝[(value, 文字)]"""
        x, y, w, h = rect
        cur = self.pg.evaluate("(s) => document.querySelector(s).value", sel)
        self.pg.evaluate(SEL_STRIP_JS, [[{"v": v, "t": t, "on": v == cur} for v, t in opts], x, y, h])
        self.wait(hold)
        ob = self.pg.locator(f'#__vsel [data-v="{value}"]').first.bounding_box()
        texts = self.texts() + [[x - 300, y + h, w + 600, 45, 0, 0, 0]]   # 清單下方一整條當「會長出字的地方」：選完後圖重排，游標外框不能伸進去
        tx, ty, ov = self.clear_point([ob["x"], ob["y"], ob["width"], ob["height"]], texts, None)
        self.glide(tx, ty, texts)
        self.pg.evaluate("(v) => { const e = document.querySelector('#__vsel [data-v=\"' + v + '\"]'); if (e) e.classList.add('hv'); }", value)
        self.wait(220)
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [tx, ty])
        self.record_target(tx, ty, "click", expect=f'#__vsel [data-v="{value}"]')
        tg = self.targets[-1]
        tg["label"] = label
        tg["rect_center"] = self._vpt(tx, ty)
        tg["measured_by"] = "自繪清單選項內的落點"
        self.frame()
        self.pg.evaluate("() => { const e = document.getElementById('__vsel'); if (e) e.remove(); }")
        self.pg.locator(sel).first.select_option(value)
        self.frame()
        self.wait(120)

    def click_xy(self, x, y, ms=600, pause=400, expect=None):
        """手機：手指細圈只在點下前 0.2 秒到點下後 0.07 秒出現（立刻關掉，免得壓到點擊後換出來的新內容）。桌機沿用 05。"""
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
        self.cursor(False)   # 手指一放開就收（點擊後換出來的新內容不會被細圈壓到）
        self.pg.evaluate("() => document.querySelectorAll('.__vr').forEach(e => e.remove())")
        self.frame()
        self.pg.mouse.move(*self.PARK)
        self.x, self.y = self.PARK

    def away(self, ms=260):   # 沿用 05 的名字
        self.park(ms=ms)


# ---------------------------------------------------------------- 訪客假後端（正式站的「第一次來的訪客」）
API = "https://acct.video.test"


def guest_api(ctx):
    def handle(route):
        req = route.request
        path = req.url.split(API, 1)[-1].split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            body = json.loads(req.post_data or "{}")
        except Exception:  # noqa: BLE001
            body = {}
        out = {}
        if path == "/v1/perm/me":
            out = {"who": "guest", "plan": "guest", "planName": "訪客", "feats": {}}
        elif path == "/v1/total/use":
            out = {"ok": True, "limit": 5, "used": [body.get("key")], "g": "gvideo"}
        elif path == "/v1/articles/stats":
            out = {"views": {}}
        route.fulfill(status=200, body=json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})
    ctx.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": API}) + ";")
    ctx.route(API + "/**", handle)


# 法遵模糊＋會員額度字樣（只在錄影的瀏覽器裡；公司名單取自網站自己的 data/stocks.json）
def blur_js(css_extra: str, text_sel: str) -> str:
    css = ("#artQuota,#evQuota{display:none!important}.__vquota{visibility:hidden!important}.sitefoot,.sitefoot *{visibility:hidden!important}") + css_extra   # 2026-10-22：不再模糊任何東西
    return r"""
(() => { const css = %s; let RX = null; const TEXT_SEL = %s;
  const sweep = () => {
    const root = document.getElementById('v-articles');
    if (root) { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const v = n.nodeValue;
      if (v.indexOf('不佔額度') >= 0) n.nodeValue = v.replace(/[・·]?\s*不佔額度/, '');
      else if (/全文需\s*Plus/.test(v) && n.parentElement) (n.parentElement.closest('.lk') || n.parentElement).classList.add('__vquota'); } }
  };
  const go = () => { const st = document.createElement('style'); st.id = '__blurco'; st.textContent = css; (document.head || document.documentElement).appendChild(st);
    new MutationObserver(sweep).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    fetch('data/stocks.json').then(r => r.json()).then(list => {
      const names = [...new Set(list.map(s => String(s.name || '').replace(/\*/g, '').trim()).filter(n => n.length >= 2))].sort((a, b) => b.length - a.length);
      RX = new RegExp(names.map(n => n.replace(/[.*+?^${}()|[\]\\-]/g, '\\$&')).join('|'));
      window.__vblurReady = true; sweep(); }).catch(() => { window.__vblurReady = true; }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % (json.dumps(css), json.dumps(text_sel))


def run(dev, flow, out, cfgx, port=8820):
    """cfgx：site（站台根）、scr、overlays、els、roots、zcharts、extra_css、blur_sel、blur_css、init（額外 init script 列表）、ls（localStorage 額外鍵）。"""
    C.SITE = Path(cfgx["site"])
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            cfg = dict(cfgx.get("dev", {}).get(dev) or CFG_DEV[dev])
            k = cfg["device_scale_factor"]
            W, H = int(cfg["viewport"]["width"] * k), int(cfg["viewport"]["height"] * k)
            ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
            tpe = _dt.timezone(_dt.timedelta(hours=8))
            now = _dt.datetime.now(tz=tpe)
            day = now.date() if now.hour >= 5 else now.date() - _dt.timedelta(days=1)
            ctx.clock.install(time=_dt.datetime(day.year, day.month, day.day, 14, 30, tzinfo=tpe))   # 錄影時鐘固定台北白天（亮色主題）
            F.route_fonts(ctx)
            guest_api(ctx)
            ctx.add_init_script(F.FONT_JS)
            ctx.add_init_script(C.PRESET)
            ctx.add_init_script(C.HIDE_B_JS)
            ctx.add_init_script(LIB_JS)
            ctx.add_init_script("window.__CFG = " + json.dumps(dict(overlays=cfgx["overlays"], els=cfgx["els"], roots=cfgx["roots"], zcharts=cfgx.get("zcharts", []), ovsel=cfgx.get("ovsel", "#__vsel"))) + ";")
            ctx.add_init_script(blur_js(cfgx.get("blur_css", ""), cfgx.get("blur_sel", "#evList .ev > a")))
            css = REC_CSS_BASE + cfgx.get("extra_css", "")
            ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = %s; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();" % json.dumps(css))
            for s in cfgx.get("init", []):
                ctx.add_init_script(s)
            if dev == "m":
                ctx.add_init_script("(function f() { if (document.documentElement) document.documentElement.classList.add('__vmob'); else setTimeout(f, 5); })();")
            ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            pg.goto(base + "#overview", wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.evaluate("() => document.fonts.ready")
            pg.wait_for_function("() => window.__vblurReady === true", timeout=15000)
            pg.evaluate(RING_JS)
            CF.META_JS = META_JS
            a = A3(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
            a.dsf = k
            rec = Rec3(pg, W, H, a)
            tmp = out / f".{dev}_main.mp4"
            rec.tmp_out = tmp

            def start(rec=rec, a=a):
                a.rec = rec
                if a.mob:
                    a.cursor(False)
                    pg.mouse.move(*A3.PARK)
                else:
                    a._put(a.x, a.y)
                rec.start(out / f".tmp_{dev}")

            flow(pg, a, start)
            a.settle()
            a.idle(300)
            r = rec.stop(out / f"{dev}_main.mp4")
            if not cfgx.get("dry"):
                shutil.move(str(tmp), out / f"{dev}_main.mp4")
            shutil.rmtree(out / f".tmp_{dev}", ignore_errors=True)
            r.update(size=[W, H], dsf=k, crop=cfgx.get("crop0", {}).get(dev) or CROP0[dev], says=a.says, clears=a.clears, stages=a.stages, clicks=a.targets, steps=a.log,
                     errs=errs[:5], fm=rec.fm, timer_errs=getattr(rec, "timer_errs", []), data_date=site_meta.get("data_date"), warns=a.warns, vp=cfg["viewport"])
            (out / f"{dev}_main.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            miss = [s for s in a.log if "找不到" in s or "點不到" in s or "⚠" in s]
            print(dev, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6], "警告:", a.warns[:8], flush=True)
            ctx.close()
            b.close()
    finally:
        srv.shutdown()
