"""功能介紹影片 04 產業地圖 v5（網頁版）—— 一鏡到底（沿用 05 資金流向的做法）。

主線（一條因果線）：「AI 伺服器由哪些零件組成？」→ 左側選單進產業地圖、選 AI 伺服器鏈 → 2D 剖析圖連點編號（04 液冷、05 板上供電、03 電源櫃）
→ 切 3D 看同一批零件（連點三個零件標籤，最後點電源櫃）→ 零件小卡「環節：電源」→ 往下捲到 2D 供應鏈關聯圖，連點電源、散熱（上游）、系統組裝（下游）。
全程同一個視窗，鏡頭只做「一次單向推近」（引導段結束、進產業地圖那一刻，把左側選單推出畫面）與頁面往下捲；沒有換場、沒有淡化霧罩、沒有疊影。
每一格另外記錄：浮層外框（網站提示框、說明卡）、3D 標籤外框（互相壓到也算遮擋）、被介紹元素外框、所有看得到的文字外框（檢查框邊切字）、游標外框、客服鈕。
法遵：公司名稱、代號、股價在錄影瀏覽器裡一律模糊（BLUR_CSS，只在錄影的瀏覽器，不改 site/）。
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
import capture_ind as I  # noqa: E402  v4 的共用素材（模糊、字型、錄影器）
import flowlib as F  # noqa: E402
C = I.C

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat04"))
FPS = 30
VP = {"width": 1280, "height": 720}
DSF = 2
CROP0 = (0, 0, 1280, 678)
CROP1 = (250, 70, 1010, 535)        # 推近後取景（css，視窗座標）：只留內容區（側欄推出畫面）          # 開場取景（整個視窗寬，看得到左側選單）
CHAIN = "ai_server"

REC_CSS = ("#relTip,#relStick{display:none!important}#relSec .segnote{visibility:hidden!important}"
           ".lbl3d:not([data-dgno=\"12\"]):not([data-dgno=\"13\"]):not([data-dgno=\"16\"]):not([data-dgno=\"01\"]){visibility:hidden!important}"
           "html body #supFab,html body .supfab,html body #bibiRing,html body .bibiring{bottom:-300px!important}"
           ".__vr{width:24px!important;height:24px!important;border-width:2px!important;background:transparent!important}"
           ".reltip{margin:18px 0 0 22px!important}")
BLUR_SEL = I.BLUR_SEL

META_JS = r"""([blurSel, named]) => {
  const vh = innerHeight, vw = innerWidth;
  const vis = (e) => { if (!e || !e.getClientRects().length) return null; for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const cs = getComputedStyle(n); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) return null; }
    const r = e.getBoundingClientRect(); return (r.width < 2 || r.height < 2) ? null : [r.left, r.top, r.width, r.height]; };
  const el = {}; for (const k in named) { const e = document.querySelector(named[k]); const r = vis(e); if (r) el[k] = r; }
  const ov = []; for (const [n, s] of [['relTip', '#relTip'], ['relStick', '#relStick'], ['pop', '.howpop, #howPop, [role=dialog], .toast']]) { document.querySelectorAll(s).forEach(e => { const r = vis(e); if (r) ov.push([n, ...r]); }); }
  const lb = []; document.querySelectorAll('.lbl3d').forEach(e => { const r = vis(e); if (r) lb.push([e.dataset.dgno || '', ...r]); });
  const txt = [];
  const root = document.querySelector('#v-industry') || document.body;
  const blurEls = blurSel ? new Set(document.querySelectorAll(blurSel)) : new Set();
  const skip = (e) => { for (let n = e; n && n !== root; n = n.parentElement) { if (blurEls.has(n)) return true; } return false; };
  const wk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n, k = 0;
  while ((n = wk.nextNode()) && k < 6000) { k++; const t = n.nodeValue; if (!t || !t.trim()) continue; const e = n.parentElement; if (!e || e.closest('script,style')) continue;
    if (skip(e)) continue; const rg = document.createRange(); rg.selectNodeContents(n); const rs = rg.getClientRects();
    for (const r of rs) { if (r.width < 2 || r.height < 2) continue; if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue; if (e.closest('svg') === null && !vis(e)) continue; { const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) continue; } txt.push([r.left, r.top, r.width, r.height]); } }
  const fab = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring')].map(vis).filter(Boolean);
  return { el, ov, lb, txt, fab, sy: Math.round(scrollY) }; }"""

NAMED = {
    "tab": '#tabs .tab[data-view="industry"]',
    "chain": f'#chainSwitch button[data-c="{CHAIN}"]',
    "tog": "#dg3d",
    "card3": "#prodDiagram .dgcol.l .dgc:nth-child(3)",
    "card4": "#prodDiagram .dgcol.l .dgc:nth-child(4)",
    "card5": "#prodDiagram .dgcol.l .dgc:nth-child(5)",
    "dg": "#prodDiagram svg.dg",
    "canvas": "#prod3d canvas",
    "part": "#partCard",
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
        if not self.dry:
            r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True, "captureBeyondViewport": False})
            self.ff.stdin.write(C.base64.b64decode(r["data"]))
        self.n += 1
        try:
            m = self.pg.evaluate(META_JS, [BLUR_SEL, NAMED])
        except Exception:  # noqa: BLE001
            m = {"el": {}, "ov": [], "lb": [], "txt": [], "fab": [], "sy": 0}
        a = self.act
        m["cur"] = [round(getattr(a, "pcx", a.x), 1), round(getattr(a, "pcy", a.y), 1)]
        m["stage"] = a.stage
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
    def __init__(self, pg, vw, vh):
        super().__init__(pg, False, vw, vh)
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


def run(a, pg, start, snap=False):
    # ── 錄影前：預熱 3D（載入 three.js 與模型），再回總覽（不入鏡）──
    pg.evaluate("() => { location.hash = '#industry/%s'; }" % CHAIN)
    pg.wait_for_timeout(4500)
    I.warm3d(pg)
    I.anim_off(pg)
    pg.evaluate("() => { location.hash = '#overview'; scrollTo(0, 0); }")
    pg.wait_for_timeout(3500)
    a.x, a.y = 900, 24     # 開場游標停在頂欄空白處（不停在總覽圖表上，免得跳出圖表提示框）
    start()
    # 1 需求
    a.set_stage(1, "需求")
    a.say("AI 伺服器由哪些零件組成？", "face_think_v2", ("tab",))
    tx, ty = tab_pt(pg, NAMED["tab"], 0.82)
    a.move(tx, 24, 600)    # 先沿頂欄移到選單上方，再沿側欄往下（不從總覽圖表上掃過，免得跳出圖表提示框）
    a.move(tx, ty, 450)
    # 2 引導：點產業地圖、選 AI 伺服器鏈
    a.set_stage(2, "引導")
    a.say("點產業地圖，選 AI 伺服器", "point_r_v2", ("tab", "chain"))
    a.wait(300)
    a.off_click(tx, ty, "選單：產業地圖", NAMED["tab"], dx=30, dy=20)
    a.until(f"() => !!document.querySelector('#chainSwitch button[data-c=\"{CHAIN}\"]')", 8000)
    a.wait(900)
    bx, by = tab_pt(pg, NAMED["chain"], 0.5)
    a.move(bx + 5, by - 50, 420)
    a.off_click(bx, by, "產業鏈：AI 伺服器", NAMED["chain"], dx=60, dy=60, pause=90)
    a.until("() => !!document.querySelector('#prodDiagram .dgc')", 8000)
    a.move(1251, 150, 500)
    a.wait(500)
    a.snap("s2")
    # 3 2D 剖析圖：點編號 04 → 05 → 03（單向捲動到工具列貼近框上緣；同時鏡頭推近）
    a.set_stage(3, "剖析圖")
    a.say("點編號，圖上零件跟著亮", "spotlight", ("card4", "card5", "card3", "dg"))
    sy0 = pg.evaluate("() => scrollY")
    tgt = pg.evaluate("() => document.querySelector('#dg3d').getBoundingClientRect().top + scrollY") - 76
    sy_now = pg.evaluate("() => scrollY")
    tgt, cuts = best_scroll(pg, tgt, CROP1, -26, 26, 1)
    pg.evaluate("(y) => scrollTo(0, y)", sy_now)
    a.note(f"剖析圖捲動位置 {tgt}，框緣切字 {cuts}")
    a.scroll(to_y=tgt, ms=700)
    a.snap("s3a")
    PARK = (1251, 150)   # 內容區右緣外側的空白（游標矩形 26px 寬，大半在框外）：頁面捲動時不會有字從游標底下滑過、也不會碰到 3D 畫布而展開標籤
    a.move(*PARK, 300)
    for k, lab in ((4, "編號卡 04 液冷"), (5, "編號卡 05 板上供電"), (3, "編號卡 03 電源櫃")):
        sel = NAMED[f"card{k}"]
        r = css_rect(pg, sel)
        a.move(r[0] - 40, r[1] + r[3] / 2, 380)
        a.off_click(r[0] + r[2] * 0.94, r[1] + r[3] * 0.5, lab, sel, dx=0, dy=0, pause=90)
        a.move(*PARK, 260)
        a.wait(1100)
        a.snap(f"s3_{k}")
    a.settle()
    # 4 切 3D：連點三個零件標籤（最後點電源櫃）
    a.set_stage(4, "3D")
    a.say("切 3D，點零件看說明", "3dglasses", ("tog", "canvas"))
    r3 = css_rect(pg, '#dg3d button[data-dm="3d"]')
    a.move(r3[0] + r3[2] + 30, r3[1] + r3[3] / 2 + 30, 380)
    a.off_click(r3[0] + r3[2] * 0.8, r3[1] + r3[3] / 2, "切 3D", '#dg3d button[data-dm="3d"]', dx=0, dy=0, pause=80)
    a.move(r3[0] + r3[2] * 0.8, 36, 200)    # 先往上離開工具列（移到畫面框上緣外），再沿上緣移到右側空白，不掃過工具列上的字
    a.move(1251, 36, 240)
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 8000)
    a.move(*PARK, 120)
    a.wait_still3d(pg)
    a.snap("s4a")
    first = True
    for no, lab in (("13", "零件：13 BBU 電池"), ("12", "零件：12 電源櫃"), ("13", "零件：13 BBU 電池"), ("12", "零件：12 電源櫃")):
        sel = I.lbl(no)
        lr = css_rect(pg, sel)
        a.move(lr[0] + lr[2] + 40 if lr[0] > 640 else lr[0] - 40, lr[1] + 16, 380)
        a.click_now(sel, lab, ms=180, pause=80, dx=0.96, dy_px=14)
        a.wait(40)
        lr2 = css_rect(pg, sel)
        a.move(*PARK, 260)
        a.wait(1050)
        a.snap(f"s4_{no}")
    a.settle()
    # 5 零件小卡「環節：電源」→ 2D 關聯圖
    a.set_stage(5, "關聯圖")
    a.say("電源櫃屬「電源」環節", "point_r_v2", ("part",))
    y0 = pg.evaluate("() => document.querySelector('#partCard').getBoundingClientRect().top + scrollY") - 70
    sy_now = pg.evaluate("() => scrollY")
    y1, cuts = best_scroll(pg, y0, CROP1, -20, 20, 1)
    pg.evaluate("(y) => scrollTo(0, y)", sy_now)
    a.note(f"零件卡捲動位置 {y1}，框緣切字 {cuts}")
    a.scroll(to_y=y1, ms=800)
    a.snap("s5a")
    a.wait(900)
    a.clear_say()
    sy_now = pg.evaluate("() => scrollY")
    (ys, cuts), (u0, u1) = union_scroll(pg, CROP1, 8, -30, 20)
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", sy_now)
    a.note(f"關聯圖捲動位置 {ys}，框緣切字 {cuts}，三環節聯集高 {u1 - u0:.0f}")
    a.scroll(to_y=ys, ms=800)
    a.snap("s5b")
    a.say("上游散熱，下游系統組裝", "talk_explain_v2", ("power", "thermal", "assembly"))
    a.move(1251, 110, 400)   # 游標移到空白處（不壓節點）
    a.wait(1700)
    a.snap("s5_hold")
    a.settle()
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SCR / "raw_v5"))
    ap.add_argument("--port", type=int, default=8818)
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
            ctx.add_init_script(I.BLUR_JS)
            ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = %s; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();" % json.dumps(REC_CSS))
            ctx.add_init_script("try{localStorage.removeItem('tw.chainFold');localStorage.removeItem('tw.dg3d.exp');localStorage.setItem('tw.dganim','0')}catch(e){}")
            ctx.add_init_script(C.CURSOR_JS % "false")
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            pg.goto(base + "#overview", wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.evaluate("() => document.fonts.ready")
            a = A(pg, VP["width"], VP["height"])
            a.dsf = DSF
            if g.snap:
                a.snap_dir = out / "snap"
                a.snap_dir.mkdir(exist_ok=True)
            rec = Rec(pg, W, H, a)
            tmp = out / ".d_main.mp4"
            rec.tmp_out = tmp

            def start(rec=rec, a=a):
                a.rec = rec
                a._put(a.x, a.y)
                rec.start(out / ".tmp_d")

            run(a, pg, start, g.snap)
            a.settle()
            a.idle(300)
            r = rec.stop(out / "d_main.mp4")
            if not g.snap:
                shutil.move(str(tmp), out / "d_main.mp4")
            shutil.rmtree(out / ".tmp_d", ignore_errors=True)
            r.update(size=[W, H], dsf=DSF, crop0=CROP0, says=a.says, clears=a.clears, stages=a.stages, clicks=a.targets, steps=a.log, errs=errs[:5], fm=rec.fm,
                     timer_errs=getattr(rec, "timer_errs", []), data_date=site_meta.get("data_date"))
            (out / "d_main.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            miss = [s for s in a.log if "找不到" in s or "點不到" in s or "⚠" in s]
            print(r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
            ctx.close()
            b.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
