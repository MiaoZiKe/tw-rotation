"""功能介紹影片 04 v4：產業地圖 2D／3D（Andy 10-21：不准遮擋、節奏更快、一條邏輯主線）—— 素材錄製。

v4 主線（網頁、手機同一條）：選單進產業地圖 → AI 伺服器剖析圖點編號（結尾點「電源櫃」）→ 切 3D 看同一個零件 → 點零件小卡的「環節：電源」→ 2D 供應鏈關聯圖看電源的上下游。
每一拍都記錄「被介紹元素」與「所有浮層」的外框（OCC_JS），錄完逐幀檢查相交面積（遮擋檢查）。

（以下為 v3 起沿用的說明）

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

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat04"))
FPS = 30
DEVS = {
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
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



# 點擊漣漪縮小（直徑 24px）：不壓在被點的字上（10-21 稽核：波紋不准壓在被點的字上）；手機另外把站內的底部面板遮罩（#mSheetBack 的半透明深色）在錄影裡設成透明，不把圖淡掉
RIPPLE_JS = r"""
(() => { const go = () => { const st = document.createElement('style'); st.id = '__vrcss';
  st.textContent = '.reltip{margin:18px 0 0 22px!important}.__vr{width:24px!important;height:24px!important;border-width:2px!important}#mSheetBack,.mshback,.msheet-back{background:transparent!important;backdrop-filter:none!important}#siteFoot{display:none!important}#prod3d .mnum[data-no="16"]{visibility:hidden!important}'; (document.head || document.documentElement).appendChild(st); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();
"""

# 字型：網站不載網路字型；錄影容器沒有 Noto Sans TC，圖表畫布會退回點陣字。錄影的瀏覽器裡補上本機 Noto Sans TC（只在錄影的瀏覽器，不改 site/）
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


# ------------------------------------------------------------------ v4：遮擋檢查（每一格量「被介紹元素」與「所有浮層」的外框）
# intros＝這一拍正在介紹的元素（選擇器聯集，rect:x,y,w,h 也算）；floats＝會蓋東西的浮層（網站提示框、說明卡、面板、3D 標籤、游標、漣漪…）；
# texts＝不准被模糊塊壓到的族群／環節／說明文字。浮層若「就是介紹區塊本身」或「包著介紹區塊（介紹的是它的內容）」不算蓋。
OCC_JS = r"""([intros, floats, texts, blurSel]) => {
  const vh = innerHeight, vw = innerWidth;
  const vis = (r) => r.width >= 2 && r.height >= 2 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
  const shown = (e) => { for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const cs = getComputedStyle(n); if (+cs.opacity < 0.05 || cs.visibility === 'hidden') return false; } return true; };
  const rectOf = (s) => { const [x, y, w, h] = s.slice(5).split(',').map(Number); return { left: x, top: y, right: x + w, bottom: y + h, width: w, height: h }; };
  const dgEls = () => { const sp = [...document.querySelectorAll('#prodDiagram .sel-part')]; const anc = sp.filter(e => e.tagName.toLowerCase() === 'g');
    const parts = [...document.querySelectorAll('#prodDiagram svg.dg g.sel[data-part]')].filter(g => anc.some(a => { const r = a.getBoundingClientRect(), q = g.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2; return cx >= q.left - 4 && cx <= q.right + 4 && cy >= q.top - 4 && cy <= q.bottom + 4; }));
    return sp.concat(parts); };
  const col = (list) => { const out = []; for (const s of list) {
      if (s.startsWith('rect:')) out.push({ el: null, r: rectOf(s), n: s });
      else if (s === 'dgsel') dgEls().forEach(e => out.push({ el: e, r: e.getBoundingClientRect(), n: s }));
      else if (s.startsWith('all:')) document.querySelectorAll(s.slice(4)).forEach(e => { if (e.getClientRects().length) out.push({ el: e, r: e.getBoundingClientRect(), n: s }); });
      else { const e = document.querySelector(s); if (e && e.getClientRects().length) out.push({ el: e, r: e.getBoundingClientRect(), n: s }); } }
    return out.filter(o => vis(o.r) && (!o.el || shown(o.el))); };
  const I = col(intros);
  let F = col(floats);
  F = F.filter(f => !I.some(i => i.el && f.el && (i.el === f.el || f.el.contains(i.el))));
  const rr = (o) => [o.n, o.r.left, o.r.top, o.r.width, o.r.height];
  const T = col(texts).filter(o => { if (!o.el) return true; const h = document.elementFromPoint(Math.min(vw - 1, Math.max(0, o.r.left + o.r.width / 2)), Math.min(vh - 1, Math.max(0, o.r.top + o.r.height / 2))); return !!h && (o.el === h || o.el.contains(h)); });   // 只算真的看得到（沒被浮層蓋住）的文字
  const B = []; if (blurSel) document.querySelectorAll(blurSel).forEach(e => { if (e.getClientRects().length) { const r = e.getBoundingClientRect(); if (vis(r)) B.push(['blur', r.left, r.top, r.width, r.height]); } });
  return { i: I.map(rr), f: F.map(rr), t: T.map(rr), b: B }; }"""

DEF_FLOATS = ["#relTip", "#relStick", "#mSheet", "all:.lbl3d", "all:#__vc > *", "all:.__vr", "all:#supFab, .supfab, #bibiRing, .bibiring"]
DEF_TEXTS = ["all:#relSec .segtitle", "all:#prodDiagram .dgc .bd b", "all:.lbl3d b", "all:#mSheet .mshcard b, #mSheet h3"]
BLUR_SEL = "#relSec .co text,#chainMap .co text,.rlco .cd,.rlco .nm,.rlco .chg,.rlfo,.chips3d a,.chips3d span,.dgchips a,.dgchips span,.mchips a,.pc-co a,a.lk-stock,#v-industry a[href^='#stock/'],#mSheet a[href^='#stock/'],#coBox h3,.pc-co>b,.pc-none,.mpcco,.mpcnone"


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框（影片像素）＋每格遮擋資料（介紹元素／浮層／模糊塊）。
    畫格不落地：PNG 直接串流給 ffmpeg（磁碟只剩不到 1GB，逐格存 PNG 會爆）。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []
        self.edges: list = []
        self.fabs: list = []
        self.occ: list = []
        self.ff = None
        self.tmp_mp4 = None
        self.timer_errs: list = []

    def start(self, tmpdir):
        self.tmp_mp4 = Path(str(tmpdir) + ".mp4")
        if not self.dry:
            self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
                                        "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-threads", "2", "-crf", "17",
                                        "-r", str(FPS), "-movflags", "+faststart", str(self.tmp_mp4)], stdin=subprocess.PIPE)
        self.bad = []
        self.n, self.on, self.acc = 0, True, 0.0
        import datetime as _dt
        for margin in (1.5, 5, 15, 40):
            now = self.pg.evaluate("() => Date.now()")
            try:
                self.pg.clock.pause_at(_dt.datetime.fromtimestamp(now / 1000 + margin, tz=_dt.timezone.utc))
                break
            except Exception as exc:  # noqa: BLE001
                if "past" not in str(exc) or margin == 40:
                    raise
        self.frame()

    def stop(self, out_mp4):
        self.on = False
        try:
            self.pg.clock.resume()
        except Exception:  # noqa: BLE001
            pass
        if not self.n:
            return {"ok": False, "why": "沒有任何畫格"}
        if self.dry:
            return {"ok": True, "dry": True, "dur": round(self.n / FPS, 2), "frames": self.n, "bad": self.bad}
        self.ff.stdin.close()
        self.ff.wait()
        shutil.move(str(self.tmp_mp4), str(out_mp4))
        return {"ok": True, "dur": round(self.n / FPS, 2), "frames": self.n, "bad": self.bad, "timer_errs": self.timer_errs[:6]}

    def frame(self):
        if not self.on:
            return
        self.acc += 1000 / FPS
        ms = int(self.acc)
        self.acc -= ms
        try:
            self.pg.clock.run_for(ms)
        except Exception as exc:  # noqa: BLE001
            self.timer_errs.append([self.n, str(exc).splitlines()[0][:160]])
        self.pg.evaluate(C.ANIM_JS, ms)
        if self.n % 6 == 0:
            self._watch()
        if self.dry:
            self.n += 1
        else:
            r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True, "captureBeyondViewport": False})
            self.ff.stdin.write(C.base64.b64decode(r["data"]))
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
            self.cams.append([a.cam_id, 0, 0, a.vw * k, a.vh * k, 0, None, 0])
            self.edges.append([])
        else:
            self.cams.append([a.cam_id] + sc(r["cam"]) + [round((spec[4] or 0) * k, 1), sc(r["focus"]), 1 if spec[6] else 0])
            self.edges.append([sc(e) for e in r["edges"]])
        try:
            fb = self.pg.evaluate(FAB_JS)
        except Exception:  # noqa: BLE001
            fb = None
        self.fabs.append([round(v * k, 1) for v in fb] if fb else None)
        oc = None
        if a.occ_spec is not None:
            try:
                oc = self.pg.evaluate(OCC_JS, [a.occ_spec[0], a.occ_spec[1], a.occ_spec[2], BLUR_SEL])
            except Exception:  # noqa: BLE001
                oc = None
        if oc is not None:
            sc5 = lambda L: [[x[0]] + [round(v * k, 1) for v in x[1:]] for x in L]   # noqa: E731
            self.occ.append([a.cam_id, sc5(oc["i"]), sc5(oc["f"]), sc5(oc["t"]), sc5(oc["b"])])
        else:
            self.occ.append(None)


def _inter(p, q):
    ix = min(p[1] + p[3], q[1] + q[3]) - max(p[1], q[1])
    iy = min(p[2] + p[4], q[2] + q[4]) - max(p[2], q[2])
    return ix * iy if ix > 0.5 and iy > 0.5 else 0.0


def occ_check(rec, clicks, labels):
    """逐幀：介紹元素 × 浮層（含游標、漣漪、其他 3D 標籤、客服鈕）相交面積 >0 記 1 筆；模糊塊 × 文字相交另記。
    游標／漣漪只在「被點目標」上可以重疊（目標本身就是該拍介紹元素）：點下前 1.0 秒（游標滑進來、等說明框）到點下後 0.45 秒；其他元素、其他時間不准。"""
    ck = [(c["t"], c["center"]) for c in clicks if c["kind"] in ("click", "dragstart") and c.get("center")]
    rows, blur_rows, frames = [], [], 0
    for fi, o in enumerate(rec.occ):
        if o is None:
            continue
        frames += 1
        t = fi / FPS
        _cid, I, F, T, B = o
        near = [pt for (ct, pt) in ck if -1.0 <= t - ct <= 0.6]
        rip = [pt for (ct, pt) in ck if -0.08 <= t - ct <= 0.7]   # 點擊漣漪（點下去才出現、0.55 秒內消失，直徑 24px）：版面規則例外 ① ≤0.8 秒
        for f in F:
            cur = f[0].startswith("all:#__vc")
            isrip = f[0].startswith("all:.__vr")
            if isrip and rip:
                continue
            for i in I:
                a = _inter(i, f)
                if a <= 0:
                    continue
                if cur and any(j[0] == i[0] and j[1] <= px <= j[1] + j[3] and j[2] <= py <= j[2] + j[4] for px, py in near for j in I):
                    continue
                if cur and any(math.hypot(f[1] + f[3] / 2 - px, f[2] + f[4] / 2 - py) <= 50 * rec.act.dsf for px, py in near):
                    continue   # 游標就在剛點下的那一點旁（點完版面重排、被點元素移位的瞬間）   # 被點目標在同一組介紹元素（例：關聯圖整排環節框）裡：手指按在這組元素上，指示圈碰到鄰框也算被點的那一組
                rows.append((round(t, 2), f[0], i[0], int(a), labels.get(_cid, "")))
        cm = rec.cams[fi] if fi < len(rec.cams) else None
        view = None
        if cm and cm[6]:   # 這一拍有取景框：只算取景框（外擴 20%）裡看得到的文字
            view = ["v", cm[1] - cm[3] * 0.1, cm[2] - cm[4] * 0.1, cm[3] * 1.2, cm[4] * 1.2]
        for b in B:
            for tx in T:
                if view and _inter(view, tx) <= 0:
                    continue
                a = _inter(b, tx)
                if a > 0:
                    blur_rows.append((round(t, 2), tx[0], int(a), labels.get(_cid, ""), [round(v) for v in b[1:]], [round(v) for v in tx[1:]]))
    return dict(frames=frames, occ=rows, blur=blur_rows)


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
        self.occ_spec = None
        self.cam_labels: dict = {}

    def cam(self, sels, pad=12, label="", frame=None, minw=None, edges=None, zoom=False, intro=None, floats=None, texts=None):
        """sels＝介紹的區塊；frame＝取景框（不給就是區塊本身）；minw＝取景最小寬（css，推近拍用）；edges＝不准被框邊切過的卡片；zoom＝推近拍（報告算佔畫面寬）。"""
        self.settle()   # 前一句泡泡講完（最短停留）才換鏡頭，畫面與泡泡同步
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad, frame, minw, list(edges or []), zoom)
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label or ",".join(sels)])
        self.cam_labels[self.cam_id] = label or ",".join(sels)
        it = list(intro) if intro is not None else [s for s in sels if not s.startswith("rect:")]
        self.occ_spec = (it, list(DEF_FLOATS if floats is None else floats), list(DEF_TEXTS if texts is None else texts))

    def cam_view(self, label="viewport"):
        self.settle()
        self.cam_spec = None
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label])
        self.cam_labels[self.cam_id] = label
        self.occ_spec = None   # 捲動轉場：沒有「被介紹」的元素

    def occ_now(self):
        if not self.occ_spec:
            return None
        return self.pg.evaluate(OCC_JS, [self.occ_spec[0], self.occ_spec[1], self.occ_spec[2], ""])

    def click_xy(self, x, y, ms=600, pause=400, expect=None):
        """按下與放開之間不推進時鐘（3D 畫布在 pointerup 選零件：中間隔一格，手機版選得到編號卻開不了說明面板）。"""
        self.move(x, y, ms)
        self.wait(pause)
        self.note(f"踩下 ({x:.0f},{y:.0f})css → 影片({x * self.dsf:.0f},{y * self.dsf:.0f})px")
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", expect=expect)
        self.pg.mouse.down()
        self.pg.mouse.up()
        self.frame()
        self.frame()

    def drag(self, *a, **kw):
        self.cursor(True)
        return super().drag(*a, **kw)

    def move(self, x, y, ms=600):
        """手機：手指直接按在目標上（不從遠處滑過來、不經過別的內容）。"""
        if self.mob:
            self._put(x, y)
            self.x, self.y = x, y
            self.frame()
            return
        super().move(x, y, ms)

    def wait_still3d(self, pg, max_ms=2500):
        """逐格等到 3D 圓點／標籤位置連續兩次取樣（每 5 格）不動為止。"""
        js = "() => [...document.querySelectorAll('#prod3d .mnum, .lbl3d')].map(e => { const r = e.getBoundingClientRect(); return [r.x, r.y]; })"
        prev = None
        for _ in range(max(1, int(max_ms / 1000 * FPS / 5))):
            cur = pg.evaluate(js)
            if prev and len(prev) == len(cur) and all(abs(p[0] - q[0]) < 0.6 and abs(p[1] - q[1]) < 0.6 for p, q in zip(prev, cur)):
                return True
            prev = cur
            for _ in range(5):
                self.frame()
        return False

    def lift(self, ms=160):
        """手機：手指點完就離開螢幕（觸控指示圈淡出），不留在被介紹的內容上。"""
        self.wait(ms)
        self.cursor(False)
        self.wait(220)

    HOVER_SEL = "#chainMap .segtitle, #chainMap .segnote, .lbl3d, #relStick, .dgc"

    def park(self, ms=260, pad=26, prefer=None, only_if_hit=False):
        """點完之後把游標移到「不壓任何介紹元素、不在會跳提示框的位置」的空白處（離現在位置最近的合格點）。only_if_hit：現在游標沒壓到（外擴 16px）就不動。"""
        oc = self.occ_now()
        if oc is None:
            return
        if only_if_hit:
            cur = [x for x in oc["f"] if x[0].startswith("all:#__vc")]
            hit = any(c[1] - 16 < i[1] + i[3] and c[1] + c[3] + 16 > i[1] and c[2] - 16 < i[2] + i[4] and c[2] + c[4] + 16 > i[2] for c in cur for i in oc["i"])
            if not hit:
                return
        vw, vh = self.vw, self.vh
        rects = [x[1:] for x in oc["i"]] + [x[1:] for x in oc["f"] if not x[0].startswith("all:#__vc") and not x[0].startswith("all:.__vr")]
        best = None
        camr = None
        sp = self.cam_spec
        if sp and sp[0] == "sel":
            try:
                camr = (self.pg.evaluate(CAM_JS, [sp[1], sp[2], sp[3], []]) or {}).get("cam")
            except Exception:  # noqa: BLE001
                camr = None
        if prefer is None:
            prefer = (self.x + 45, self.y + 45)   # 點完往右下偏 40px 以上，離開被點的字
        for gy in range(80, int(vh) - 40, 30):
            for gx in range(100, int(vw) - 40, 30):
                if any(gx > r[0] - pad and gx < r[0] + r[2] + pad and gy > r[1] - pad and gy < r[1] + r[3] + pad for r in rects):
                    continue
                if self.pg.evaluate("([x, y, s]) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest && e.closest(s)); }", [gx, gy, self.HOVER_SEL]):
                    continue
                d = math.hypot(gx - prefer[0], gy - prefer[1])
                if camr and not (camr[0] + 30 <= gx <= camr[0] + camr[2] - 30 and camr[1] + 30 <= gy <= camr[1] + camr[3] - 30):
                    d += 3000   # 盡量留在取景框內（游標不要被框邊切掉一半）
                if best is None or d < best[0]:
                    best = (d, gx, gy)
        if best:
            self.move(best[1], best[2], ms)

    def safe_move(self, x, y, ms=500, avoid=None):
        """直線移動若會滑過別的「會跳提示框／展開標籤」的元素（avoid 選擇器），先繞到上方／下方／左右的空白處再進場。"""
        avoid = avoid or self.HOVER_SEL

        def hits(px, py, qx, qy):
            return self.pg.evaluate("""([px, py, qx, qy, s, tx, ty]) => { const T = document.elementFromPoint(tx, ty); const tt = T && T.closest ? T.closest(s) : null;
              for (let i = 0; i <= 24; i++) { const x = px + (qx - px) * i / 24, y = py + (qy - py) * i / 24; const e = document.elementFromPoint(x, y);
                const c = e && e.closest ? e.closest(s) : null; if (c && c !== tt) return true; } return false; }""", [px, py, qx, qy, avoid, x, y])
        if not hits(self.x, self.y, x, y):
            self.move(x, y, ms)
            return
        for wx, wy in ((x, y - 90), (x, y + 90), (x - 120, y), (x + 120, y), (x, y - 160), (x - 200, y - 120)):
            if 0 < wx < self.vw and 0 < wy < self.vh and not hits(self.x, self.y, wx, wy) and not hits(wx, wy, x, y):
                self.move(wx, wy, int(ms * 0.55))
                self.move(x, y, int(ms * 0.55))
                return
        self.move(x, y, ms)

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
        self.cursor(True)
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
        self.cursor(True)
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
        pre = self.pg.evaluate(C.RECT_JS, sel)   # 按下前一刻量「被點的那個元素」本身（3D 標籤點的是標題 b，不是整張標籤）
        self.click_xy(x, y, 1, 0, expect=sel)
        self.targets[-1]["label"] = label
        if pre and pre[2] > 0:
            self.targets[-1]["rect_center"] = self._vpt(pre[0] + pre[2] / 2, pre[1] + pre[3] / 2)
            self.targets[-1]["measured_by"] = "被點元素外框（按下前一刻）"
        # 中心誤差以「按下前一刻」量到的外框為準；點下後標籤會展開說明而變高，不可事後再量
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


def anim_off(pg):
    """3D 工具列的「動畫：關」：機櫃不自己轉，編號圓點／標籤位置固定（自動轉動時圓點會互相蓋住、標籤會重排）。錄影前先按掉（不入鏡）。"""
    pg.evaluate("() => { const bs = [...document.querySelectorAll('#dgAnim, #dgAnim button')]; const b = bs.find(x => (x.textContent || '').trim() === '關') || bs.find(x => /動畫\\s*[:：]\\s*開/.test((x.textContent || '').trim())); if (b) b.click(); }")
    pg.wait_for_timeout(400)


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



M_EDGE = ["all:#relSec .segbox"]
DG_CAM = ["all:#prodDiagram .dgc", "#prodDiagram svg.dg"]   # 2D 剖析圖：所有編號卡＋中間圖（全圖；不用整欄容器，欄容器底邊會碰到客服鈕）
ZMIN = 440   # 桌機推近拍的最小取景寬（css）


def dgc(side, k):
    return f"#prodDiagram .dgcol.{side} .dgc:nth-child({k})"


def lbl(no):
    return f'.lbl3d[data-dgno="{no}"]'


def seg(s):
    return f'#relSec .segtitle[data-seg="{s}"]'


def segbox(s):
    return f'#relSec .segbox[data-seg="{s}"]'


def chain_btn(c):
    return f'#chainSwitch button[data-c="{c}"]'


def rect_css(pg, sel):
    return pg.evaluate(C.RECT_JS, sel)


# ------------------------------------------------------------------ 網頁版（1600×900 視窗）
def d_guide(pg, a, start):
    """導覽：總覽 → 左側選單「產業地圖」→ 選 AI 伺服器鏈（看得到剖析圖）。"""
    goto(pg, "#overview", 3500)
    tab = '#tabs .tab[data-view="industry"]'
    a.x, a.y = 1000, 400
    start()
    a.cam(["rect:14,520,310,200"], 0, "左側選單：產業地圖", minw=ZMIN, zoom=True, intro=[tab])
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2")
    a.move(330, 640, 600)
    a.click(tab, label="選單：產業地圖", ms=420)
    a.wait(120)
    a.park(ms=220)
    a.wait(1200)
    b1, b4 = rect_css(pg, "#chainSwitch button:nth-child(1)"), rect_css(pg, "#chainSwitch button:nth-child(4)")
    a.cam([f"rect:{b1[0] - 8:.0f},{b1[1] - 6:.0f},{b4[0] + b4[2] - b1[0] + 16:.0f},{b1[3] + 12:.0f}"], 0, "產業鏈分頁（前幾個）", minw=ZMIN, zoom=True, intro=[chain_btn(CHAIN)])
    a.say("選產業鏈，看剖析圖", "point_r_v2")
    a.safe_move(*[v for v in btn_pt(pg, chain_btn(CHAIN))], 500)
    a.click(chain_btn(CHAIN), label="產業鏈：AI 伺服器", ms=200, pause=120)
    a.wait(120)
    a.park(ms=220)
    a.wait(700)
    a.settle()


def btn_pt(pg, sel):
    r = rect_css(pg, sel)
    return (r[0] + r[2] / 2 - 90, r[1] + r[3] / 2 - 40)   # 從按鈕左上方進場（不滑過旁邊的按鈕）


def dg_card(a, k, label, hold=700):
    """2D 剖析圖左欄第 k 張編號卡：先推到「編號卡＋圖上對應零件」→ 從左側空白進場點它 → 游標移開，卡片展開的說明與對應零件完整入鏡。"""
    card = dgc("l", k)
    anc = a.pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.dataset.anc : null; }", card)
    a.cam([card, f"dgpre:{anc}"], 14, f"推近：{label}", minw=ZMIN, zoom=True)
    r = rect_css(a.pg, card)
    a.move(max(40, r[0] - 70), r[1] + r[3] / 2, 380)
    a.click(card, label=label, ms=260, pause=100, dx=0.94, dy=0.5)   # 點卡片右緣空白處，漣漪不壓在字上
    a.wait(90)
    a.cam(["dgsel"], 14, f"{label}＋對應零件", minw=ZMIN, zoom=True)
    a.park(ms=200)
    a.wait(hold // 2)
    a.park(ms=200, only_if_hit=True)
    a.wait(hold - hold // 2)


def d_dg2d(pg, a, start):
    """剖析圖：點 04 → 05 → 03（電源櫃）。"""
    goto(pg, f"#industry/{CHAIN}")
    scroll_to(pg, "#dgTools", 12)   # 整張圖在客服鈕上方（圖底約 773、客服鈕頂 804）
    hint = pg.evaluate("() => { const e = [...document.querySelectorAll('#prodDiagram span')].find(x => x.children.length === 0 && x.textContent.includes('每一張說明')); if (!e) return null; const r = e.getBoundingClientRect(); return `rect:${r.x},${r.y},${r.width},${r.height}`; }")
    full = DG_CAM + ([hint] if hint else [])
    a.x, a.y = 1585, 450
    start()
    a.cam(full, 8, "AI 伺服器 2D 剖析圖（全圖）", intro=DG_CAM)
    a.say("點編號，圖上零件跟著亮", "spotlight")
    a.idle(500)
    for k, lab in ((4, "編號卡 04 液冷"), (5, "編號卡 05 板上供電"), (3, "編號卡 03 電源櫃")):
        dg_card(a, k, lab, 650 if k != 3 else 800)
    a.settle()


def d_3d(pg, a, start):
    """同一個零件切 3D：拖曳旋轉 → 點 11 → 13 → 12（電源櫃）。3D 這一鏡用 1280×800、2 倍像素錄（WebGL 軟體算圖很慢，畫布不能太大）。"""
    goto(pg, f"#industry/{CHAIN}")
    warm3d(pg)
    anim_off(pg)
    pg.evaluate("() => document.querySelector('#prodDiagram .dgcol.l .dgc:nth-child(3) .bd b').click()")   # 接上一鏡：已選 03 電源櫃
    pg.wait_for_timeout(600)
    scroll_to(pg, "#dgTools", 76)
    a.x, a.y = 1000, 150
    start()
    t3 = rect_css(pg, "#dg3d")
    db = rect_css(pg, "#dgBody")
    top3 = t3[1] - 4
    fr3 = f"rect:{db[0]:.0f},{top3:.0f},{db[2]:.0f},{min(db[3], db[2] / 2.04 - 6):.0f}"   # 工具列＋3D 畫布，底邊在客服鈕（頂 708）上方
    a.cam([fr3], 0, "2D／3D 切換與 3D 圖", intro=["#dg3d"])
    a.say("同一個零件，切 3D 再看", "3dglasses")
    r = rect_css(pg, '#dg3d button[data-dm="3d"]')
    a.move(r[0] + r[2] / 2 + 60, r[1] - 40, 420)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D", ms=260, pause=100, dx=0.8, dy=0.5)
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.park(ms=240)
    a.wait(300)
    c = rect_css(pg, "#prod3d canvas")
    cx = c[0] + c[2] / 2
    rk = rack_rect(pg)
    band = f"rect:{c[0]:.0f},{c[1] + c[3] * 0.1:.0f},{c[2]:.0f},{min(c[3] * 0.8, c[2] / 2.04 - 8):.0f}"   # 畫布中央一條（畫框比例 2.04：整張畫布比這個高，會裝不進去）
    a.cam([band], 0, "3D：機櫃＋兩側零件標籤", zoom=True, intro=[rk])
    a.park(ms=300)
    a.drag(cx - 170, c[1] + 70, cx + 90, c[1] + 76, 1000)   # 在機櫃上方的空白處拖（不經過機櫃）
    a.wait(100)
    a.wait_still3d(pg)
    first = True
    # 點開會長高、會跟隔壁標籤短暫重疊（站內動畫）：只點同一欄「最下面」的 13 BBU 與 12 電源櫃（下面沒有鄰居），13 → 12 → 13 → 12
    for no in ("13", "12", "13", "12"):
        lab = f"零件：{no} {'電源櫃' if no == '12' else 'BBU 電池'}"
        rk = rack_rect(pg, lbl(no))
        a.cam([lbl(no), rk], 10, f"推近：{lab}", minw=ZMIN, zoom=True, intro=[lbl(no), rk])
        if first:
            a.say("點零件，說明跟著換", "magnifier")
            first = False
        outer = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return r.left + r.width / 2 > innerWidth / 2 ? 'right' : 'left'; }", lbl(no))
        lr = rect_css(pg, lbl(no))
        a.move(lr[0] + lr[2] + 40 if outer == "right" else lr[0] - 40, lr[1] + 18, 380)
        a.click_now(lbl(no), lab, ms=200, pause=90, dx=0.96, dy_px=14)   # 點標籤右上角空白處
        a.wait(30)
        rk = rack_rect(pg, lbl(no))
        a.cam([lbl(no), rk], 10, f"{lab}＋說明", minw=ZMIN, zoom=True, intro=[lbl(no), rk])
        lr2 = rect_css(pg, lbl(no))
        a.move(lr2[0] + lr2[2] * 0.96, c[1] + 44, 100)   # 先往上離開標籤（標籤點開會長高）
        a.move(cx, c[1] + 44, 140)                       # 再沿畫布上緣移到中間空白處（不經過機櫃）
        a.wait(500)
    a.settle()


def pick_label(pg, exclude=(), only=()):
    """挑「上下都有空位」的 3D 標籤（點開會長高，空位不夠會壓到隔壁標籤）；同一欄的鄰居距離最大的那個。"""
    cv = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    pg.mouse.move(cv[0] + cv[2] / 2, cv[1] + cv[3] * 0.9)   # 游標在畫布裡＝標籤展開狀態（不錄影，只為量空位）
    pg.wait_for_timeout(500)
    L = pg.evaluate("""() => [...document.querySelectorAll('.lbl3d')].map(e => { const r = e.getBoundingClientRect(); return [e.dataset.dgno, r.left, r.top, r.right, r.bottom]; })""")
    best = None
    for no, x0, y0, x1, y1 in L:
        if no in exclude or (only and no not in only):
            continue
        up = min([y0 - q[4] for q in L if q[0] != no and abs(q[1] - x0) < 60 and q[4] <= y0 + 2] or [400])
        dn = min([q[2] - y1 for q in L if q[0] != no and abs(q[1] - x0) < 60 and q[2] >= y1 - 2] or [400])
        if y0 < 150 or y1 > pg.evaluate("() => innerHeight") - 24:
            continue
        below = [q for q in L if q[0] != no and abs(q[1] - x0) < 60 and q[2] >= y1 - 2 and q[2] - y1 < 220]
        sc = 1000 if not below else min(up, 60) + min(dn, 120)   # 同一欄最下面一張：點開長高也不會壓到下一張，優先
        if best is None or sc > best[0]:
            best = (sc, no)
    return best[1] if best else "06"


def rack_rect(pg, near=None):
    """3D 機櫃本體在視窗座標的外框（畫布寬 21%、高 23%～82% 的中央區，1600×900 實測）。near：只取跟這個標籤同高度上下 130px 的那一段。"""
    r = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    w = r[2] * 0.21
    x0 = r[0] + r[2] / 2 + r[2] * 0.012 - w / 2
    y0, y1 = r[1] + r[3] * 0.23, r[1] + r[3] * 0.82
    if near:
        q = pg.evaluate(C.RECT_JS, near)
        y0, y1 = max(y0, q[1] - 130), min(y1, q[1] + q[3] + 130)
    return f"rect:{x0:.0f},{y0:.0f},{w:.0f},{max(40, y1 - y0):.0f}"


def tip_rect(pg, sel, dx=0.5):
    """滑到環節標題上時，說明框會出現的範圍（游標右下 +14,+16，錄影 CSS 再推 +22,+18；寬約 340、高約 105～150）。只框說明框本身（標題在框外），旁邊節點只是它底下的背景。"""
    r = rect_css(pg, sel)
    cx, cy = r[0] + r[2] * dx, r[1] + r[3] / 2
    return f"rect:{cx + 34:.0f},{cy + 32:.0f},350,150"


def rel_seg(a, pg, s, label, hold=750, first=False):
    """關聯圖點一個環節：先拍「滑到標題 → 說明框出現（停約 0.6 秒）」（介紹說明框；旁邊節點不是介紹對象），點下後游標馬上往右上移開、說明框消失，
    再拍「被點環節＋上下游節點、連線」（此時沒有任何浮層蓋住節點）。"""
    t = seg(s)
    r = rect_css(pg, t)
    dx = min(0.94, max(0.3, (1100 - r[0]) / r[2]))   # 游標落點 x ≤ 1100：說明框（寬約 340＋偏移 22）整個落在畫面內、不翻到游標左邊
    a.cam([tip_rect(pg, t, dx)], 0, f"推近：{label} 說明框", minw=ZMIN, zoom=True, intro=["#relTip"], floats=["#relTip", "all:#__vc > *", "all:.__vr"])
    a.safe_move(r[0] + r[2] * dx, r[1] + r[3] * 0.5, 480, avoid="#chainMap .segtitle, #chainMap .segnote")
    a.wait(600)   # 說明框出現、給觀眾看（上游／下游）
    a.click(t, label=label, ms=40, pause=40, dx=dx, dy=0.5)
    bb0 = rect_css(pg, segbox(s))
    a.park(ms=200, prefer=(min(1580, bb0[0] + bb0[2] + 240), r[1] - 40), pad=20)   # 往右移到下一拍取景框的右邊外面（不經過說明框）
    a.wait(160)
    b = rect_css(pg, segbox(s))
    st = pg.evaluate("() => { const e = document.querySelector('#relStick'); if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
    x0, x1 = b[0] - 200, min(b[0] + 560, 1585)
    if st and st[2] < b[0] + 60:
        x0 = max(x0, st[2] + 14)
    fr = f"rect:{x0:.0f},{b[1] - 60:.0f},{x1 - x0:.0f},{b[3] + 120:.0f}"
    a.cam([segbox(s), fr], 0, f"{label}：被點環節＋上下游節點", minw=ZMIN, zoom=True, intro=[segbox(s), fr])
    a.park(ms=200, prefer=(b[0] + b[2] + 420, b[1] - 40), only_if_hit=True)
    a.wait(hold)


def d_rel(pg, a, start):
    """零件小卡寫著「環節：電源」→ 往下捲到關聯圖 → 點電源（看說明框）→ 點上游「散熱」→ 點下游「系統組裝」。
    （不點小卡上的「環節：電源 →」：它會立刻跳出站內的清單卡，蓋住左邊的節點，捲動轉場的畫面裡會看到。）"""
    goto(pg, f"#industry/{CHAIN}")
    pg.evaluate("() => document.querySelector('#prodDiagram .dgcol.l .dgc:nth-child(3) .bd b').click()")
    pg.wait_for_timeout(900)
    pg.evaluate("() => { const e = document.querySelector('#partCard'); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 200); }")
    pg.wait_for_timeout(600)
    a.x, a.y = 1585, 300
    start()
    pcr = rect_css(pg, "#partCard")
    a.cam([f"rect:{pcr[0]:.0f},{pcr[1]:.0f},560,{min(pcr[3], 130):.0f}"], 0, "零件小卡：環節：電源", minw=ZMIN, zoom=True, intro=["rect:%d,%d,560,%d" % (pcr[0], pcr[1], min(pcr[3], 130))], floats=["all:#__vc > *", "all:.__vr"])
    a.say("電源櫃屬於「電源」環節", "point_r_v2")
    a.idle(1500)
    a.cam_view("捲動")
    a.scroll_to_el("#relSec", 64, 600)
    a.park(ms=200)
    rel_seg(a, pg, "power", "環節：電源", 650)
    a.say("上游是散熱，下游是系統組裝", "talk_explain_v2")
    rel_seg(a, pg, "thermal", "環節：散熱（上游）", 600)
    rel_seg(a, pg, "assembly", "環節：系統組裝（下游）", 700)
    a.settle()


TALL_D = {}
D_SHOTS = {"guide": d_guide, "dg2d": d_dg2d, "d3d": d_3d, "rel": d_rel}


# ------------------------------------------------------------------ 手機版（390 寬 m4 版面）
# 底部說明面板高約 253～276 css，會蓋住它上方的圖 → 錄影視窗拉高到「圖整張在面板上方」：
#   dg2d：390×640（圖 62～342、面板 387 起，取景 56～632 同時框住圖與面板）；dg3d：390×844（3D 181～541、面板 568 起）。
M_FRAME = "rect:0,56,390,576"   # 取景（390×576 ＝ 畫面框 1000×1478 的比例）


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    a.x, a.y = 300, 300
    start()
    a.cam(["#m4Burger"], 0, "左上角選單", frame="rect:0,0,390,576")
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2")
    a.click("#m4Burger", label="選單", ms=500, pause=100)
    a.lift(ms=90)
    a.wait(700)
    a.cam(['.m4item[data-v="industry"]', '.m4item[data-v="overview"]'], 10, "選單抽屜", intro=['.m4item[data-v="industry"]'], floats=["all:#__vc > *", "all:.__vr"])
    a.click('.m4item[data-v="industry"]', label="選單：產業地圖", ms=420, pause=100)
    a.lift(ms=90)
    a.wait(1200)
    a.cam(["#chainSwitch"], 0, "產業鏈分頁", frame="rect:0,60,390,576")
    a.say("選產業鏈，看剖析圖", "point_ur_v2")
    a.lift()
    a.click(chain_btn(CHAIN), label="產業鏈：AI 伺服器", ms=420, pause=100)
    a.lift(ms=90)
    a.wait(800)
    a.settle()


def m_dg2d(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    pg.evaluate("() => scrollTo(0, document.querySelector('#dgBody').getBoundingClientRect().top + scrollY - 62)")   # 圖頂 62、圖底 342 在面板頂（最高時 346）上方；取景 pad 0，圖頂離取景上緣 ≥4px
    pg.wait_for_timeout(500)
    a.x, a.y = 350, 380
    start()
    a.cam(["#dgBody"], 0, "AI 伺服器 2D 剖析圖＋說明面板", frame=M_FRAME, intro=["#dgBody"])
    a.say("點編號，看零件說明", "magic_frame")
    a.wait(500)
    a.click_now('#dgBody .mnum[data-no="05"]', "編號 05 板上供電", ms=450, pause=100)
    a.lift(ms=90)
    a.wait(700)
    a.say("說明、環節、台廠都列好", "pointer_r")
    for lab in ("抽屜「‹」：編號 04 液冷", "抽屜「‹」：編號 03 電源櫃"):
        a.click_now('#mSheet .mshnav button[data-d="-1"]', lab, ms=380, pause=100)
        a.lift(ms=90)
        a.wait(650)
    a.settle()


def rack_rect_m(pg):
    c = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    w = c[2] * 0.42
    return f"rect:{c[0] + c[2] * 0.5 - w / 2 + c[2] * 0.02:.0f},{c[1] + c[3] * 0.17:.0f},{w:.0f},{c[3] * 0.53:.0f}"


def m_dg3d(pg, a, start):
    goto(pg, f"#industry/{CHAIN}")
    warm3d(pg)
    anim_off(pg)
    pg.evaluate("() => scrollTo(0, document.querySelector('#dgTools').getBoundingClientRect().top + scrollY - 70)")   # 3D 畫布底 ≈553 在面板頂（≈568）上方
    pg.wait_for_timeout(500)
    a.x, a.y = 350, 300
    start()
    a.cam(["#dg3d"], 6, "2D／3D 切換", frame=M_FRAME, intro=["#dg3d"])
    a.say("同一個零件，切 3D 再看", "3dglasses")
    a.wait(300)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D", ms=450, pause=100)
    a.lift(ms=60)
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.wait(500)
    rk = rack_rect_m(pg)
    a.cam(["#prod3d"], 4, "3D：機櫃＋兩側編號", frame=M_FRAME, intro=[rk])
    a.lift()
    c = pg.evaluate(C.RECT_JS, "#prod3d canvas")
    a.drag(c[0] + 22, c[1] + 28, c[0] + 100, c[1] + 34, 1000)
    a.wait(150)
    a.say("點編號，說明跟著換", "magnifier")
    # 編號圓點偶爾會被隔壁圓點蓋住（3D 轉動時）：挑 9～15 號裡「周圍 36px 內沒有別的圓點」的先點，再用面板的「‹」「›」一格一格換到 12 電源櫃，再往 13 看一格、回到 12
    a.wait_still3d(pg)   # 拖曳放開後模型還有慣性在轉：等圓點位置不動了再挑、再點
    start_no = pick_badge(pg, ("11", "13", "10", "14", "09", "15", "12"))
    a.click_now(f'#prod3d .mnum[data-no="{start_no}"]', f"零件：編號 {start_no}", ms=450, pause=100)
    a.wait(450)
    a.cam(["#mSheet"], 4, "零件說明面板", frame="rect:0,268,390,576", intro=["#mSheet"])
    a.lift()
    a.wait(750)
    cur = int(start_no)
    path = []
    while cur != 12:
        d = 1 if cur < 12 else -1
        path.append(d)
        cur += d
    path += [1, -1]   # 到 12 電源櫃之後，往 13 BBU 看一格再回來
    cur = int(start_no)
    for d in path[:5]:
        cur += d
        a.click_now(f'#mSheet .mshnav button[data-d="{d}"]', f"抽屜「{'›' if d == 1 else '‹'}」：編號 {cur:02d}", ms=380, pause=100)
        a.lift(ms=90)
        a.wait(560)
    a.settle()


def pick_badge(pg, cands):
    """挑「圓點中心點下去真的是它自己（最上層）、而且周圍 36px 內沒有別的圓點」的編號。"""
    pg.wait_for_timeout(300)
    L = pg.evaluate("""() => [...document.querySelectorAll('#prod3d .mnum')].map(e => { const r = e.getBoundingClientRect(); const x = r.x + r.width / 2, y = r.y + r.height / 2;
      const h = document.elementFromPoint(x, y); const top = h && h.closest ? h.closest('.mnum') : null; return [e.dataset.no, x, y, !!top && top === e]; })""")
    best = None
    for no in cands:
        me = [q for q in L if q[0] == no]
        if not me or not me[0][3]:
            continue
        d = min([((me[0][1] - q[1]) ** 2 + (me[0][2] - q[2]) ** 2) ** 0.5 for q in L if q[0] != no] or [999])
        if d >= 36:
            return no
        if best is None or d > best[0]:
            best = (d, no)
    return best[1] if best else cands[0]


M_REL_SEGS = ("thermal", "power", "optical", "switch", "connector", "fpc", "assembly")


def m_rel_setup(pg):
    """關聯圖橫向捲到「中欄＋右欄」整欄露出；頁尾下方墊空白（視窗外，點環節展開／收起時捲動位置不被夾）。回傳取景框（畫面框比例 1000:1478）。"""
    pg.add_style_tag(content="body{padding-bottom:900px!important}#relSec{margin-bottom:360px!important}")   # 關聯圖下方墊空白：取景框底下不會露出頁尾字（頁尾推到框外）
    scroll_to(pg, "#relSec", 64)
    pg.evaluate("""() => { const m = document.querySelector('#chainMap'); const t = document.querySelector('#relSec .segbox[data-seg="thermal"]');
      m.scrollLeft += t.getBoundingClientRect().left - 42; }""")
    pg.wait_for_timeout(500)
    g = pg.evaluate("""() => { const q = s => document.querySelector(s).getBoundingClientRect();
      const t = q('#relSec .segbox[data-seg="thermal"]'), a = q('#relSec .segbox[data-seg="assembly"]'), m = q('#chainMap');
      return [t.left, a.right, m.top]; }""")
    x0, x1, mt = g[0] - 12, g[1] + 12, g[2]
    w = x1 - x0
    h = w / (1000 / 1478)
    return f"rect:{x0:.1f},{mt - 7:.1f},{w:.1f},{h:.1f}"


def m_rel(pg, a, start):
    goto(pg, f"#industry/{CHAIN}/overview")   # 族群總覽分頁：點環節後關聯圖不會被重畫、捲回原位（取景才能固定在中欄＋右欄）
    frame = m_rel_setup(pg)
    cols = "all:" + ", ".join(f'#relSec .segbox[data-seg="{x}"]' for x in M_REL_SEGS)
    a.x, a.y = 20, 500
    start()
    a.cam([cols], 0, "關聯圖：中欄＋右欄", frame=frame, minw=100, edges=M_EDGE, intro=[cols])
    a.say("電源櫃屬於「電源」環節", "talk_explain_v2")
    a.lift(ms=90)
    for s_, lab in (("power", "環節：電源"), ("thermal", "環節：散熱（上游）"), ("assembly", "環節：系統組裝（下游）")):
        a.click(seg(s_), label=lab, ms=420, pause=100, dx=0.9, dy=0.5)
        a.lift(ms=90)
        a.wait(800)
        if s_ == "power":
            a.say("上游是散熱，下游是系統組裝", "pointer_r")
    a.settle()


DSF_M = {"guide": 3, "dg2d": 3, "dg3d": 3, "rel": 3}
M_SHOTS = {"guide": m_guide, "dg2d": m_dg2d, "dg3d": m_dg3d, "rel": m_rel}


DSF_D = {"guide": 2, "dg2d": 2.5, "d3d": 2, "rel": 2.5}


def run(dev, shots, out, port):
    cfg = DEVS[dev]
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
                if dev == "d":
                    cfg["device_scale_factor"] = DSF_D.get(sid, 2)
                    if sid == "d3d":
                        cfg["viewport"] = {"width": 1280, "height": 900}
                else:
                    cfg["device_scale_factor"] = DSF_M.get(sid, 3)
                    cfg["viewport"] = {"width": 390, "height": 640 if sid == "dg2d" else 844}
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                _tpe = _dt.timezone(_dt.timedelta(hours=8))
                _now = _dt.datetime.now(tz=_tpe)
                _day = _now.date() if _now.hour >= 5 else _now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(_day.year, _day.month, _day.day, 14, 30, tzinfo=_tpe))   # 錄影時鐘固定台北下午 14:30 → 亮色主題
                route_fonts(ctx)
                ctx.add_init_script(FONT_JS)
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)
                ctx.add_init_script(BLUR_JS)
                ctx.add_init_script(RIPPLE_JS)
                ctx.add_init_script("try{localStorage.removeItem('tw.chainFold');localStorage.removeItem('tw.dg3d.exp')}catch(e){}")
                if sid in ("d3d", "dg3d"):   # 3D 不自己轉（圓點／標籤位置固定，不互相蓋住）；使用者仍可拖曳旋轉
                    ctx.add_init_script("try{localStorage.setItem('tw.dganim','0');localStorage.setItem('tw.m4.3danim','0')}catch(e){}")
                if dev == "d" and sid != "guide":   # 桌機左側導覽收成圖示列：內容區更寬（導覽段維持展開的文字選單，看得到「產業地圖」字樣）
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
                    a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]] if (sid == "guide" or dev == "m") else pg.evaluate("() => { const e = document.querySelector('#v-industry'); const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
                    occ = occ_check(rec, a.targets, a.cam_labels)
                    r.update(fabs=rec.fabs, edges=rec.edges, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"), occ=occ, occ_raw=rec.occ, cam_labels={str(k): v for k, v in a.cam_labels.items()})
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
                    print("  遮擋：檢查", occ["frames"], "幀，違規", len(occ["occ"]), "筆；模糊塊壓文字", len(occ["blur"]), "筆")
                    for row in occ["occ"][:14]:
                        print("   ", row)
                except Exception as exc:  # noqa: BLE001
                    rec.on = False
                    import traceback
                    traceback.print_exc()
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
    ap.add_argument("--out", default=str(SCR / "raw_v4"))
    ap.add_argument("--port", type=int, default=8814)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
