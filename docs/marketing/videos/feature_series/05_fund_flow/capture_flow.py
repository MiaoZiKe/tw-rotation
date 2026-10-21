"""功能介紹影片 05 資金流向 v3 —— 一口氣錄完（單一鏡頭、不換頁、不拉遠推近）。

主線（一條因果線）：錢往哪個族群跑？→ 從總覽點進「資金流向」→ 輪盤看強弱、排行看流入 → 選產業鏈（輪盤排行一起篩）
→ 拉桿換天數（輪盤排行一起變）→ 一頁看懂。全部在同一張「資金輪動」卡內完成，不切子頁。

錄法：沿用 flowlib.py（v2 的逐格算圖錄影器與游標）。差別：
  · 畫面框固定（網頁＝整個視窗取一塊固定範圍、手機＝只往下捲），錄影端不再逐格量鏡頭；
  · 每一格另外記錄「浮層外框」（下拉清單、面板、圖表提示框、客服鈕）、「被介紹元素外框」（輪盤、排行、拉桿、篩選列、選單）、
    圖表上每一段標籤文字外框、游標外框 → 合成端做「遮擋檢查」；
  · 影格直接餵 ffmpeg（不存 PNG，省磁碟）；
  · 點擊後游標往右下偏移 40px，點擊點選在字以外的空白處，波紋只畫細圈不上色；圖表提示框一出現就把游標移開。
用法（repo 根目錄）：python capture_flow.py --dev d|m
輸出：<out>/<dev>_main.mp4 ＋ <out>/<dev>_main.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
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
import flowlib as F  # noqa: E402
from flowlib import C  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat05v3"))
FPS = 30
CFG = {
    "d": dict(viewport={"width": 1280, "height": 620}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
}
# 網站畫面框（css，視窗座標）：網頁＝整個視窗寬、從頂欄下緣到卡片底；手機＝視窗寬、頂欄起 624 高（只往下捲）
CROP = {"d": (0, 68, 1280, 548), "m": (0, 0, 390, 624)}

# 錄影專用：客服鈕移出畫面下緣（不入鏡）；細圈漣漪（只畫圈、不上色，不蓋字）
REC_CSS = "html body #supFab,html body .supfab,html body #bibiRing,html body .bibiring{bottom:-200px!important}"
RING_JS = r"""
(() => { const st = document.createElement('style'); st.textContent = '.__vr{background:transparent!important;border:2px solid rgba(37,99,235,.9)!important}'; document.head.appendChild(st);
  window.__vcRipple = (x, y) => { const r = document.createElement('div'); r.className = '__vr'; const s = 30; r.style.width = r.style.height = s + 'px';
    r.style.left = x + 'px'; r.style.top = y + 'px'; document.body.appendChild(r); setTimeout(() => r.remove(), 700); };
})();
"""

# 每格量：浮層、被介紹元素、圖表標籤文字（先夾到圖表元素範圍內）
META_JS = r"""() => {
  const vis = (e) => { if (!e || !e.getClientRects().length) return null; const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity < 0.05) return null;
    const r = e.getBoundingClientRect(); return (r.width < 2 || r.height < 2) ? null : [r.left, r.top, r.width, r.height]; };
  const ov = [];
  document.querySelectorAll('.ddpanel:not([hidden]), .hpanel:not([hidden]), [role=dialog], .toast, .howpop, #howPop, .qcov, .qcard').forEach(e => { const r = vis(e); if (r) ov.push(['面板' + (e.id ? '#' + e.id : '.' + String(e.className).split(' ')[0]), ...r]); });
  document.querySelectorAll('[_echarts_instance_] > div').forEach(e => { if (e.querySelector('canvas') || /rotbeam|rotquads/.test(e.className)) return; const r = vis(e); if (r && (e.textContent || '').trim()) ov.push(['圖表提示框', ...r]); });
  const el = {}; for (const [k, s] of [['clock', '#rotClock'], ['rank', '#rankFlow'], ['slider', '#rotBack'], ['filter', '#flowRotFilter'], ['card', '#flowRotCard'],
      ['navflow', '#tabs .tab[data-view="flow"]'], ['burger', '#m4Burger'], ['m4flow', '.m4item[data-v="flow"]'], ['chain', '#flowRotFilter .rotdd[data-dd="chain"] .ddbtn'], ['tabs', '#tabs'], ['daylab', '#rotBack output, #rotBack .dv, #rotBack b']]) {
    const r = vis(document.querySelector(s)); if (r) el[k] = r; }
  const zt = [];
  for (const [nm, sel] of [['clock', '#rotClock'], ['rank', '#rankFlow']]) { const h = document.querySelector(sel); const inst = h && window.echarts && echarts.getInstanceByDom(h); if (!inst) continue; const b = h.getBoundingClientRect();
    inst.getZr().storage.getDisplayList().forEach(d => { if (d.invisible || d.ignore || !(d.type === 'tspan' || d.type === 'text')) return; const t = d.style && d.style.text;
      if (!t || !String(t).trim() || (d.style.opacity ?? 1) < 0.05) return; const r = d.getBoundingRect().clone(); if (d.transform) r.applyTransform(d.transform);
      const l = Math.max(b.left, b.x + r.x), tp = Math.max(b.top, b.y + r.y), rr = Math.min(b.right, b.x + r.x + r.width), bb = Math.min(b.bottom, b.y + r.y + r.height);
      if (rr - l < 1 || bb - tp < 1) return; zt.push([nm === 'clock' ? 0 : 1, l, tp, rr - l, bb - tp]); }); }
  document.querySelectorAll('#rotClock .rotquads > *').forEach(e => { const r = vis(e); if (r) zt.push([0, ...r]); });
  const fab = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring')].map(vis).filter(Boolean);
  return { ov, el, zt, fab, sy: Math.round(scrollY) }; }"""


class Rec(F.Rec):
    def start(self, tmpdir):
        self.fm = []
        self.out_mp4 = None
        self.ff = None
        if not self.dry:
            self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
                                        "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                                        "-r", str(FPS), "-movflags", "+faststart", str(self.tmp_out)], stdin=subprocess.PIPE)
        return super().start(tmpdir)

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
            m = self.pg.evaluate(META_JS)
        except Exception:  # noqa: BLE001
            m = {"ov": [], "el": {}, "zt": [], "fab": [], "sy": 0}
        a = self.act
        m["cur"] = [round(a.x, 1), round(a.y, 1)] if getattr(a, "cur_on", True) else None
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


class A(F.A):
    PARK_D = (1100, 100)

    def __init__(self, pg, mob, vw, vh):
        super().__init__(pg, mob, vw, vh)
        self.stage = 0
        self.stages: list = []
        self.cur_on = True

    def set_stage(self, n, name):
        self.stage = n
        self.stages.append([round(self.t, 3), n, name])

    def cam(self, *a, **k):   # v3 不用錄影端鏡頭
        pass

    def cam_view(self, *a, **k):
        pass

    def say(self, text, act="talk_explain_v2", focus=()):
        assert len(text.replace(" ", "")) <= 14, text
        self.settle()
        self.says.append({"t": round(self.t, 3), "text": text, "act": act, "focus": list(focus)})
        self.say_t, self.say_need = self.t, F.bubble_dur(text) + 0.08

    def off_click(self, x, y, label, sel=None, dx=40, dy=40, hold=0.0):
        """點 (x,y)（呼叫端選在字以外的空白處）→ 游標移到右下 (+dx,+dy)（離開文字）。"""
        self.click_xy(x, y, 300, 90, expect=sel)
        self.targets[-1]["label"] = label
        if not self.mob:
            self.move(x + dx, y + dy, 220)

    def away(self, ms=260):
        """游標移到空白處（桌機）：圖表提示框消失用。"""
        if not self.mob:
            self.move(*self.PARK_D, ms)


def is_flow_sub(pg):
    return pg.evaluate("() => location.hash")


def day_label_value(pg):
    return pg.evaluate("() => +document.querySelector('#rotBack input').value")


def pick_chain(a, pg, c, lab):
    """產業鏈下拉：點按鈕右側箭頭（不壓字）→ 清單展開 0.5 秒 → 點該列中間空白 → 網站自動打開族群清單 → 按 Esc 立刻收起。"""
    btn = pg.evaluate(C.RECT_JS, F.CDD + " .ddbtn")
    a.off_click(btn[0] + btn[2] - 9, btn[1] + btn[3] / 2, "產業鏈下拉清單", F.CDD + " .ddbtn", dx=24, dy=24)
    a.wait(260)
    row = pg.evaluate(C.RECT_JS, f'{F.CDD} .ddopt[data-c="{c}"]')
    a.off_click(row[0] + row[2] * 0.52, row[1] + row[3] / 2, lab, f'{F.CDD} .ddopt[data-c="{c}"]', dx=12, dy=12)
    a.wait(60)
    pg.keyboard.press("Escape")   # 網站選完產業鏈會自動打開族群清單 → 立刻收起（不蓋住輪盤）
    a.wait(120)
    open_n = pg.evaluate("() => document.querySelectorAll('.rotdd .ddpanel:not([hidden])').length")
    if open_n:   # Esc 沒收掉就點空白處
        a.note("⚠ Esc 沒收起清單，改點空白處")
        pg.evaluate("() => document.body.click()")
        a.wait(120)


def run_d(pg, a, start):
    F.goto(pg, "#overview", 3500)
    a.x, a.y = 600, 330
    start()
    # 1 需求
    a.set_stage(1, "需求")
    a.say("錢往哪個族群跑？", "face_think_v2", ("nav",))
    tab = pg.evaluate(C.RECT_JS, '#tabs .tab[data-view="flow"]')
    a.move(tab[0] + tab[2] * 0.82, tab[1] + tab[3] / 2, 900)
    # 2 引導：點「資金流向」
    a.set_stage(2, "引導")
    a.say("點「資金流向」", "magnifier", ("navflow",))
    a.wait(500)
    a.off_click(tab[0] + tab[2] * 0.82, tab[1] + tab[3] / 2, "選單：資金流向", '#tabs .tab[data-view="flow"]', dx=30, dy=30)
    a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 8000)
    h = pg.evaluate("() => location.hash")
    if "rotation" not in h:
        sub = pg.evaluate(C.RECT_JS, '.l4subtab[data-l4sub="flow-rotation"]')
        a.off_click(sub[0] + sub[2] * 0.85, sub[1] + sub[3] / 2, "子分頁：資金輪動", '.l4subtab[data-l4sub="flow-rotation"]', dx=30, dy=30)
        a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 8000)
    a.wait(900)
    a.away(500)
    # 3 輪盤看強弱、排行看流入（不點、不 hover 圖）
    a.set_stage(3, "看強弱")
    a.say("輪盤看強弱，排行看流入", "magnifier", ("clock", "rank"))
    a.idle(1300)
    a.settle()
    # 4 選產業鏈（清單開著時泡泡只講清單）
    a.set_stage(4, "選產業鏈")
    a.say("選產業鏈，只看那一條", "spotlight", ("filter",))
    for c, lab in F.CHAINS[:2]:
        pick_chain(a, pg, c, lab)
        a.away(220)
        a.wait(1000)
    a.settle()
    # 5 拉桿換天數：連點 5、10、30
    a.set_stage(5, "選天數")
    a.say("拉桿換天數，兩圖同步變", "clock", ("slider", "clock", "rank"))
    for v in (5, 10, 30):
        F.slider_click(a, "#rotBack input", v, f"拉桿：{v} 天前")
        a.move(a.x + 40, a.y + 40, 200)
        a.wait(300)
        a.away(260)
        a.wait(900)
    a.settle()
    # 6 收尾
    a.set_stage(6, "一頁看懂")
    a.say("排行、輪盤一頁看懂", "proud_shine", ("clock", "rank"))
    a.idle(1400)
    a.settle()


def run_m(pg, a, start):
    F.goto(pg, "#overview", 3500)
    a.x, a.y = 360, 300
    start()
    a.set_stage(1, "需求")
    a.say("錢往哪個族群跑？", "face_think_v2", ("burger",))
    a.idle(500)
    a.set_stage(2, "引導")
    a.say("點左上角選單", "point_ur_v2", ("burger",))
    bg = pg.evaluate(C.RECT_JS, "#m4Burger")
    a.off_click(bg[0] + bg[2] / 2, bg[1] + bg[3] / 2, "選單", "#m4Burger", dx=0, dy=0)
    a.wait(800)
    a.say("點「資金流向」", "magnifier", ("m4flow",))
    it = pg.evaluate(C.RECT_JS, '.m4item[data-v="flow"]')
    a.off_click(it[0] + it[2] * 0.8, it[1] + it[3] / 2, "選單：資金流向", '.m4item[data-v="flow"]', dx=0, dy=0)
    a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 8000)
    a.wait(700)
    # 往下捲一次，讓篩選列～輪盤整塊落在畫面框內（之後只往下捲）
    a.set_stage(3, "看強弱")
    a.say("輪盤看強弱，排行看流入", "magnifier", ("clock",))
    y = pg.evaluate("() => document.querySelector('#flowRotFilter').getBoundingClientRect().top + scrollY - 60")
    a.scroll(to_y=y, ms=800)
    a.idle(900)
    a.settle()
    a.set_stage(4, "選產業鏈")
    a.say("選產業鏈，只看那一條", "spotlight", ("filter",))
    for c, lab in F.CHAINS[:2]:
        pick_chain(a, pg, c, lab)
        a.wait(1000)
    a.settle()
    a.set_stage(5, "選天數")
    a.say("拉桿換天數，兩圖同步變", "clock", ("slider", "clock"))
    for v in (5, 10, 30):
        F.slider_click(a, "#rotBack input", v, f"拉桿：{v} 天前")
        a.wait(1100)
    a.settle()
    a.set_stage(6, "一頁看懂")
    a.say("排行、輪盤一頁看懂", "proud_shine", ("rank",))
    rk = pg.evaluate("() => document.querySelector('#rankFlow').getBoundingClientRect().bottom + scrollY")
    a.scroll(to_y=rk - 600, ms=900)
    a.idle(1500)
    a.settle()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8815)
    ap.add_argument("--dry", action="store_true")
    g = ap.parse_args()
    dev = g.dev
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    if g.dry:
        os.environ["FEAT_DRY"] = "1"
    srv = ThreadingHTTPServer(("127.0.0.1", g.port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{g.port}/index.html"
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            cfg = dict(CFG[dev])
            W, H = int(cfg["viewport"]["width"] * cfg["device_scale_factor"]), int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
            ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
            tpe = _dt.timezone(_dt.timedelta(hours=8))
            now = _dt.datetime.now(tz=tpe)
            day = now.date() if now.hour >= 5 else now.date() - _dt.timedelta(days=1)
            ctx.clock.install(time=_dt.datetime(day.year, day.month, day.day, 14, 30, tzinfo=tpe))   # 錄影時鐘固定台北白天（亮色主題）
            F.route_fonts(ctx)
            ctx.add_init_script(F.FONT_JS)
            ctx.add_init_script(C.PRESET)
            ctx.add_init_script(C.HIDE_B_JS)
            ctx.add_init_script(F.BLUR_JS)
            ctx.add_init_script("try{['tw.rot.days','tw.sankey.day'].forEach(k=>localStorage.removeItem(k))}catch(e){}")
            ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = %s; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();" % json.dumps(REC_CSS))
            ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
            pg.goto(base + "#overview", wait_until="networkidle")
            pg.wait_for_timeout(2500)
            pg.evaluate("() => document.fonts.ready")
            pg.evaluate(RING_JS)
            a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
            a.dsf = cfg["device_scale_factor"]
            rec = Rec(pg, W, H, a)
            tmp = out / f".{dev}_main.mp4"
            rec.tmp_out = tmp

            def start(rec=rec, a=a):
                a.rec = rec
                if a.mob:
                    a.cursor(False)
                    pg.mouse.move(*A.PARK)
                else:
                    a._put(a.x, a.y)
                rec.start(out / f".tmp_{dev}")

            (run_d if dev == "d" else run_m)(pg, a, start)
            a.settle()
            a.idle(300)
            r = rec.stop(out / f"{dev}_main.mp4")
            if not g.dry:
                shutil.move(str(tmp), out / f"{dev}_main.mp4")
            shutil.rmtree(out / f".tmp_{dev}", ignore_errors=True)
            r.update(size=[W, H], dsf=a.dsf, crop=CROP[dev], says=a.says, stages=a.stages, clicks=a.targets, steps=a.log, errs=errs[:5], fm=rec.fm,
                     timer_errs=getattr(rec, "timer_errs", []), data_date=site_meta.get("data_date"))
            (out / f"{dev}_main.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            miss = [s for s in a.log if "找不到" in s or "點不到" in s or "⚠" in s]
            print(dev, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
            ctx.close()
            b.close()
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
