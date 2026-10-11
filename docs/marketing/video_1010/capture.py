"""宣傳片 video_1010 素材錄製（真實操作錄影，亮色主題）。

用法（repo 根目錄）：
    SKIP_INTRADAY=1 python -m pipeline.build_payload      # 先產 site/data
    python docs/marketing/video_1010/capture.py                       # 全部鏡頭、手機＋桌機
    python docs/marketing/video_1010/capture.py --shots S08 --dev d   # 只錄某幾鏡、某一種寬度
    python docs/marketing/video_1010/capture.py --out /path/to/raw

錄法：CDP Page.startScreencast（PNG，裝置像素原尺寸）把每一張實際畫出來的畫格連同時間戳存下，
錄完依時間戳重排成固定 30fps（每個 1/30 秒取當時最新的那一格），ffmpeg libx264 CRF 18 輸出。
游標＋點擊漣漪是錄影時才注入的 DOM（不改 site/）。手機寬是 390×844 @3x，桌機 1440×900 @1.5x。
彈窗：預先寫 tw.consent／tw.tour（同 scripts/_show.py）；主題寫 tw.theme=light。
權限：法遵（compliance_check.md 第一節 #8）不准用擁有者／管理員／預覽版（會繞過所有鎖）。
      這裡用 page.route 假一個會員伺服器（同 scripts/_uitest.py 的 _sub_ctx 做法）：/v1/me＝一般會員（非 admin、非 owner），
      /v1/perm/me＝site/plan_presets.js 裡「plus」範本的 feats／lims／dq —— 畫面＝Plus 會員實際拿到的東西。
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SITE = ROOT / "site"
PORT = int(os.environ.get("TW_CAP_PORT", "8791"))
DEF_OUT = Path(os.environ.get("TW_CAP_OUT", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/video1010/raw"))
FPS = 30

DEVS = {
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
    "d": dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5),
}

PRESET = ("try{localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'video'}));"
          "localStorage.setItem('tw.tour','*');localStorage.setItem('tw.theme','light');"
          "if(!localStorage.getItem('tw.notice.banner'))localStorage.setItem('tw.notice.banner','*');}catch(e){}")

FAKE_API = "https://acct.video.test"


def plus_tier() -> dict:
    src = (SITE / "plan_presets.js").read_text(encoding="utf-8")
    i = src.index("window.TW_PLAN_PRESETS")
    d = json.loads(src[src.index("=", i) + 1:].strip().rstrip(";"))
    return [t for t in d["tiers"] if t.get("key") == "plus"][0]


def fake_api(ctx):
    tier = plus_tier()
    me = {"email": "demo@example.com", "name": "Plus 會員", "admin": False}
    store: dict = {}   # 自選清單（/v1/lists/*）存在這個 context 的記憶體裡

    def handle(route):
        req = route.request
        path = req.url.split(FAKE_API, 1)[-1].split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        out = {}
        if path == "/v1/me":
            out = {"user": me}
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": "plus", "planName": tier.get("name", "Plus"), "feats": tier.get("feats", {}),
                   "lims": tier.get("lims", {}), "dq": tier.get("dq")}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path == "/v1/quota/hit":
            out = {"day": "x", "n": 0, "keys": []}
        elif path == "/v1/notices":
            out = {"notices": []}
        elif path == "/v1/lists/get":
            out = {"lists": store.get("lists", []), "rev": store.get("rev", 1)}
        elif path == "/v1/lists/put":
            try:
                body = json.loads(req.post_data or "{}")
            except Exception:  # noqa: BLE001
                body = {}
            store["lists"] = body.get("lists", []); store["rev"] = store.get("rev", 1) + 1
            out = {"ok": True, "rev": store["rev"]}
        elif path.startswith("/v1/watch") or path.startswith("/v1/prefs"):
            out = {}
        route.fulfill(status=200, body=json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})
    ctx.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": FAKE_API}) + ";try{localStorage.setItem('tw.acct.tok','tok-video');}catch(e){}")
    ctx.route(FAKE_API + "/**", handle)


# 法遵（compliance_check.md 第一節 #3）：B 類功能的名稱不准入鏡 —— 錄影時把側欄／手機抽屜裡的
# 「今日關注」「選股策略」與其子項（基本面／技術面／籌碼面／消息面）藏起來（只在錄影的瀏覽器裡，不改 site/）。
HIDE_B_JS = r"""
(() => {
  const B = new Set(['今日關注', '選股策略', '今日候選']);
  const sweep = () => {
    document.querySelectorAll('#tabs .tab[data-view="explore"], #tabs .l4subtab[data-parent="explore"], .m4item[data-v="explore"]').forEach(e => e.style.setProperty('display', 'none', 'important'));
    document.querySelectorAll('#tabs .l4subtab, .m4item, .m4sub, .m4body button, .m4body a').forEach(e => {
      if (B.has((e.textContent || '').trim())) e.style.setProperty('display', 'none', 'important'); });
    document.querySelectorAll('.m4body .m4grp').forEach(g => { const t = g.querySelector('.m4gt');
      if (t && B.has(t.textContent.trim())) g.style.setProperty('display', 'none', 'important'); });
  };
  const go = () => { sweep(); new MutationObserver(sweep).observe(document.body, { childList: true, subtree: true }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
"""

# 錄影專用游標：桌機＝箭頭、手機＝指尖圓點；按下時一圈漣漪。pointer-events:none，不擋任何操作。
CURSOR_JS = r"""
(() => {
  if (window.__vcur) return; window.__vcur = 1;
  const mob = %s;
  const mk = () => {
    if (!document.body) return requestAnimationFrame(mk);
    const st = document.createElement('style');
    st.textContent = `#__vc{position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transition:opacity .2s;will-change:transform}
      #__vc.hide{opacity:0}
      .__vr{position:fixed;z-index:2147483646;pointer-events:none;border-radius:50%%;border:3px solid rgba(37,99,235,.85);
        background:rgba(37,99,235,.18);transform:translate(-50%%,-50%%) scale(.2);animation:__vr .55s ease-out forwards}
      @keyframes __vr{to{transform:translate(-50%%,-50%%) scale(1);opacity:0}}`;
    document.head.appendChild(st);
    const c = document.createElement('div'); c.id = '__vc';
    c.innerHTML = mob
      ? '<div style="width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%%;background:rgba(30,41,59,.28);border:2px solid rgba(255,255,255,.95);box-shadow:0 2px 8px rgba(0,0,0,.25)"></div>'
      : '<svg width="26" height="30" viewBox="0 0 26 30" style="margin:-2px 0 0 -3px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))"><path d="M3 2 L3 24 L9 18.5 L13 27.5 L17 25.8 L13 17 L21 17 Z" fill="#111827" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>';
    c.style.transform = 'translate(-100px,-100px)';
    document.body.appendChild(c);
    window.__vcMove = (x, y) => { c.style.transform = `translate(${x}px,${y}px)`; };
    window.__vcHide = (h) => c.classList.toggle('hide', !!h);
    window.__vcRipple = (x, y) => { const r = document.createElement('div'); r.className = '__vr';
      const s = mob ? 70 : 54; r.style.width = r.style.height = s + 'px'; r.style.left = x + 'px'; r.style.top = y + 'px';
      document.body.appendChild(r); setTimeout(() => r.remove(), 700); };
  };
  mk();
})();
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


# ------------------------------------------------------------------ 錄影器（逐格算圖，不掉格）
# 做法：Playwright 的假時鐘（page.clock）在錄影開始時暫停頁面時間；之後每一格：
#   推進 1/30 秒（setTimeout／rAF／Date／performance.now 一起走）→ 把 CSS 動畫也推進同樣時間 → CDP 截一張。
# 所以頁面再重（3D、ECharts）也是穩定 30fps、沒有卡頓，代價是錄得比實際慢（離線算圖）。
ANIM_JS = """(dt) => { for (const a of document.getAnimations()) { try {
  if (!a.__v) { a.__v = 1; a.pause(); }
  const t = (a.currentTime || 0) + dt, e = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming().endTime : Infinity;
  if (isFinite(e) && t >= e) { a.finish(); } else { a.currentTime = t; }
} catch (err) {} } }"""


class Recorder:
    def __init__(self, pg, w, h, dry=False, realtime=False):
        self.pg, self.w, self.h, self.dry, self.realtime = pg, w, h, dry, realtime
        self.cdp = pg.context.new_cdp_session(pg)
        self.sc: list = []
        self.start_wall = 0.0
        if realtime:
            self.cdp.on("Page.screencastFrame", self._sc_frame)
        self.dir: Path | None = None
        self.n = 0
        self.on = False
        self.acc = 0.0

    def _sc_frame(self, f):
        if self.on and self.dir is not None:
            ts = f["metadata"].get("timestamp") or time.time()
            fn = self.dir / f"c{len(self.sc):06d}.jpg"
            fn.write_bytes(base64.b64decode(f["data"]))
            self.sc.append((ts, fn))
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})
        except Exception:  # noqa: BLE001
            pass

    def start_rt(self, tmpdir: Path):
        """真實時間錄影：不暫停時鐘、不逐格推進；CDP screencast（JPEG 95）收頁面實際畫出來的每一格，停止時依時間戳重採樣成 30fps。"""
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True)
        self.dir, self.n, self.on, self.sc = tmpdir, 0, True, []
        self.start_wall = time.time()
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 95, "everyNthFrame": 1,
                                               "maxWidth": self.w, "maxHeight": self.h})
        self.pg.evaluate("() => { document.body.style.outline = '0 solid transparent'; requestAnimationFrame(() => document.body.style.outline = ''); }")
        self.pg.wait_for_timeout(150)

    def stop_rt(self, out_mp4: Path) -> dict:
        t_end = time.time()
        self.pg.wait_for_timeout(120)
        self.on = False
        try:
            self.cdp.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001
            pass
        fr = sorted(self.sc)
        if not fr:
            return {"ok": False, "why": "沒有任何畫格"}
        base = self.start_wall
        dur = t_end - base
        n = int(dur * FPS)
        seq = self.dir / "seq"
        seq.mkdir()
        j = 0
        gaps = [b[0] - a[0] for a, b in zip(fr, fr[1:])]
        for i in range(n):
            t = base + i / FPS
            while j + 1 < len(fr) and fr[j + 1][0] <= t:
                j += 1
            os.link(fr[j][1], seq / f"s{i:06d}.jpg")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(seq / "s%06d.jpg"),
               "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
               "-r", str(FPS), "-movflags", "+faststart", str(out_mp4)]
        subprocess.run(cmd, check=True)
        shutil.rmtree(self.dir)
        return {"ok": True, "dur": round(n / FPS, 2), "frames": n, "src_frames": len(fr),
                "src_fps": round(len(fr) / max(dur, 0.01), 1), "src_max_gap_ms": round(max(gaps) * 1000) if gaps else 0}

    def start(self, tmpdir: Path):
        if self.realtime:
            return self.start_rt(tmpdir)
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True)
        self.dir, self.n, self.on, self.acc = tmpdir, 0, True, 0.0
        import datetime as _dt
        for margin in (1.5, 5, 15, 40):   # 頁面很重（3D）時，量時間到暫停之間可能已經過好幾秒 → 加大餘裕重試
            now = self.pg.evaluate("() => Date.now()")
            try:
                self.pg.clock.pause_at(_dt.datetime.fromtimestamp(now / 1000 + margin, tz=_dt.timezone.utc))
                break
            except Exception as exc:  # noqa: BLE001
                if "past" not in str(exc) or margin == 40:
                    raise
        self.frame()

    def frame(self):
        if self.realtime:
            if self.on:   # 真實時間：睡到下一個 1/30 秒的刻度（期間讓 playwright 事件迴圈處理 screencast 事件）
                el = time.time() - self.start_wall
                nxt = (int(el * FPS) + 1) / FPS
                self.pg.wait_for_timeout(max(1, int((nxt - el) * 1000)))
            return
        if not self.on:
            return
        self.acc += 1000 / FPS
        ms = int(self.acc)
        self.acc -= ms
        self.pg.clock.run_for(ms)
        self.pg.evaluate(ANIM_JS, ms)
        if self.dry:   # --log-only：只走時間、記座標，不截圖
            self.n += 1
            return
        r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True,
                                                     "captureBeyondViewport": False})
        (self.dir / f"s{self.n:06d}.png").write_bytes(base64.b64decode(r["data"]))
        self.n += 1

    def stop(self, out_mp4: Path) -> dict:
        if self.realtime:
            return self.stop_rt(out_mp4)
        self.on = False
        try:
            self.pg.clock.resume()
        except Exception:  # noqa: BLE001
            pass
        if not self.n:
            return {"ok": False, "why": "沒有任何畫格"}
        if self.dry:
            shutil.rmtree(self.dir)
            return {"ok": True, "dry": True, "dur": round(self.n / FPS, 2), "frames": self.n}
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(self.dir / "s%06d.png"),
               "-vf", f"scale={self.w}:{self.h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
               "-r", str(FPS), "-movflags", "+faststart", str(out_mp4)]
        subprocess.run(cmd, check=True)
        n = self.n
        shutil.rmtree(self.dir)
        return {"ok": True, "dur": round(n / FPS, 2), "frames": n}


# ------------------------------------------------------------------ 操作工具（每一步都以「格」為單位推進）
def _ease(k):
    return 0.5 - 0.5 * math.cos(math.pi * k)


class Act:
    def __init__(self, pg, mob: bool):
        self.pg, self.mob = pg, mob
        self.x, self.y = (195, 600) if mob else (900, 500)
        self.log: list[str] = []
        self.rec: Recorder | None = None
        self.dsf = 1.0

    @property
    def t(self):
        if self.rec and self.rec.on and self.rec.realtime:
            return time.time() - self.rec.start_wall
        return (self.rec.n / FPS) if (self.rec and self.rec.on) else 0.0

    def note(self, s: str):
        self.log.append(f"{self.t:5.1f}s {s}")

    def frame(self):
        if self.rec and self.rec.on:
            self.rec.frame()

    def wait(self, ms):
        if self.rec and self.rec.on and self.rec.realtime:
            self.pg.wait_for_timeout(ms)
        elif self.rec and self.rec.on:
            for _ in range(max(1, round(ms * FPS / 1000))):
                self.rec.frame()
        else:
            self.pg.wait_for_timeout(ms)

    def cursor(self, show=True):
        self.pg.evaluate("(h) => window.__vcHide && window.__vcHide(h)", not show)

    def _put(self, x, y):
        self.pg.mouse.move(x, y)
        self.pg.evaluate("([x,y]) => window.__vcMove && window.__vcMove(x,y)", [x, y])

    def move(self, x, y, ms=600):
        n = max(1, round(ms * FPS / 1000))
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            e = _ease(i / n)
            self._put(x0 + (x - x0) * e, y0 + (y - y0) * e)
            self.frame()
        self.x, self.y = x, y
        if getattr(self, "log_moves", False) and ms >= 500 and self.rec and self.rec.on:
            self.note(f"游標移到 ({x:.0f},{y:.0f})css → 影片({x * self.dsf:.0f},{y * self.dsf:.0f})px")

    def box(self, sel, scroll=True):
        loc = self.pg.locator(sel).first
        try:
            if not loc.count():
                return None
        except Exception:  # noqa: BLE001
            return None
        if scroll:
            vis = loc.evaluate("e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }")
            if not vis:
                y = loc.evaluate("e => e.getBoundingClientRect().top + scrollY - innerHeight * 0.35")
                self.scroll(to_y=y, ms=700)
        return loc.bounding_box()

    def hover(self, sel, ms=600, dx=0.5, dy=0.5):
        b = self.box(sel)
        if not b:
            self.note(f"找不到 {sel}")
            return False
        self.move(b["x"] + b["width"] * dx, b["y"] + b["height"] * dy, ms)
        return True

    def click_xy(self, x, y, ms=600, pause=400):
        self.move(x, y, ms)
        self.wait(pause)
        self.note(f"踩下 ({x:.0f},{y:.0f})css → 影片({x * self.dsf:.0f},{y * self.dsf:.0f})px")
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.pg.mouse.down()
        self.frame()
        self.pg.mouse.up()
        self.frame()

    def click(self, sel, ms=600, pause=400, dx=0.5, dy=0.5, label=""):
        b = self.box(sel)
        if not b:
            self.note(f"點不到 {sel}")
            return False
        x, y = b["x"] + b["width"] * dx, b["y"] + b["height"] * dy
        self.note(f"點 {label or sel}")
        self.click_xy(x, y, ms, pause)
        return True

    def drag(self, x0, y0, x1, y1, ms=900, button="left"):
        self.move(x0, y0, 350)
        self.wait(150)
        self.note(f"拖曳開始 ({x0:.0f},{y0:.0f})css → 影片({x0 * self.dsf:.0f},{y0 * self.dsf:.0f})px")
        self.pg.mouse.down(button=button)
        self.frame()
        n = max(1, round(ms * FPS / 1000))
        for i in range(1, n + 1):
            e = _ease(i / n)
            self._put(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)
            self.frame()
        self.pg.mouse.up(button=button)
        self.note(f"拖曳放開 ({x1:.0f},{y1:.0f})css → 影片({x1 * self.dsf:.0f},{y1 * self.dsf:.0f})px")
        self.frame()
        self.x, self.y = x1, y1

    def wheel(self, dy, steps=10, ms=600):
        n = max(steps, round(ms * FPS / 1000))
        for _ in range(n):
            self.pg.mouse.wheel(0, dy / n)
            self.frame()

    def scroll(self, to_y=None, by=None, ms=1500, el="auto"):
        """逐格平滑捲動（頁面或指定的捲動容器）。"""
        y0, mx = self.pg.evaluate("""(el) => { const sc = el === 'auto' ? document.scrollingElement : document.querySelector(el);
            return sc ? [sc.scrollTop, sc.scrollHeight - sc.clientHeight] : [0, 0]; }""", el)
        y1 = to_y if to_y is not None else y0 + (by or 0)
        y1 = max(0, min(mx, y1))
        if not (self.rec and self.rec.on):
            self.pg.evaluate("([el,y]) => { const sc = el === 'auto' ? document.scrollingElement : document.querySelector(el); if (sc) sc.scrollTop = y; }", [el, y1])
            return
        n = max(1, round(ms * FPS / 1000))
        for i in range(1, n + 1):
            k = i / n
            e = 2 * k * k if k < .5 else 1 - (-2 * k + 2) ** 2 / 2
            self.pg.evaluate("([el,y]) => { const sc = el === 'auto' ? document.scrollingElement : document.querySelector(el); if (sc) sc.scrollTop = y; }", [el, y0 + (y1 - y0) * e])
            self.frame()

    def scroll_to_el(self, sel, offset=80, ms=900):
        y = self.pg.evaluate("([s,o]) => { const e = document.querySelector(s); if (!e) return null; return e.getBoundingClientRect().top + scrollY - o; }", [sel, offset])
        if y is not None:
            self.scroll(to_y=y, ms=ms)
        return y is not None

    def until(self, js, max_ms=8000):
        """錄影中等條件成立（逐格推進，不用頁面的計時器輪詢）。"""
        for _ in range(max(1, round(max_ms * FPS / 1000))):
            if self.pg.evaluate(js):
                return True
            self.wait(1000 / FPS)
        return False


# ------------------------------------------------------------------ 每一鏡
def goto(pg, base, hash_, wait=2500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(300)


SHOTS: dict = {}


def shot(sid, devs="md", desc=""):
    def deco(fn):
        SHOTS[sid] = dict(fn=fn, devs=devs, desc=desc)
        return fn
    return deco


def _import_shots():
    pass  # 鏡頭定義在本檔下方（@shot）

def _vh(pg):
    return pg.evaluate("() => innerHeight")


def _maxy(pg):
    return pg.evaluate("() => document.scrollingElement.scrollHeight - innerHeight")


def _hide_tips(pg):
    """ECharts 提示框（會帶成分股名稱）在這一鏡藏起來。"""
    pg.add_style_tag(content="div[style*='z-index: 9999999']{opacity:0!important} .rotpop,.rp-ms{display:none!important}")


@shot("S01", "md", "總覽頁：載入後慢速往下捲過整頁")
def s01(pg, a, start, base):
    goto(pg, base, "#overview", 3500)
    a.cursor(False)
    start()
    a.wait(900)
    my = _maxy(pg)
    a.note(f"開始往下捲（全長 {my}px）")
    a.scroll(to_y=my, ms=7500 if a.mob else 6500)
    a.wait(800)
    a.note("到底，回頂")
    a.scroll(to_y=0, ms=1400)
    a.wait(500)


@shot("S02", "md", "導覽：側欄／手機抽屜掃過所有分頁名稱")
def s02(pg, a, start, base):
    goto(pg, base, "#overview", 2500)
    if a.mob:
        start()
        a.wait(500)
        a.click("#m4Burger", label="☰ 開抽屜")
        a.wait(900)
        sc = pg.evaluate("""() => { const b = document.querySelector('.m4body'); let e = b;
          while (e && e !== document.body) { const s = getComputedStyle(e); if (/(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 10) { e.id = e.id || '__drawerSc'; return '#' + e.id; } e = e.parentElement; }
          return null; }""")
        items = pg.locator(".m4body .m4item:visible")
        n = items.count()
        for i in range(n):
            b = items.nth(i).bounding_box()
            if b and 60 < b["y"] < 800:
                a.move(b["x"] + 80, b["y"] + b["height"] / 2, 160)
                a.wait(90)
        if sc:
            a.note("抽屜往下捲")
            a.scroll(to_y=99999, ms=1800, el=sc)
            a.wait(300)
            for i in range(n):
                b = items.nth(i).bounding_box()
                if b and b["y"] > 300 and b["y"] < 800:
                    a.move(b["x"] + 80, b["y"] + b["height"] / 2, 160)
                    a.wait(90)
        a.wait(600)
        a.note("Esc 收起抽屜")
        pg.keyboard.press("Escape")
        a.wait(700)
    else:
        start()
        a.wait(400)
        items = pg.locator("#tabs .tab:visible, #tabs .l4subtab:visible")
        n = items.count()
        a.note(f"游標由上往下滑過側欄 {n} 項")
        for i in range(n):
            b = items.nth(i).bounding_box()
            if b and b["y"] < 880:
                a.move(b["x"] + 60, b["y"] + b["height"] / 2, 170)
                a.wait(60)
        a.scroll(to_y=99999, ms=1200, el="#tabsWrap")
        a.wait(200)
        for i in range(n):
            b = items.nth(i).bounding_box()
            if b and 500 < b["y"] < 880:
                a.move(b["x"] + 60, b["y"] + b["height"] / 2, 170)
                a.wait(60)
        a.wait(500)


@shot("S03", "md", "財經日曆（財金日報）：切 FED 消息 → 點一則 → 展開說明")
def s03(pg, a, start, base):
    goto(pg, base, "#earnings", 3000)
    start()
    a.wait(700)
    a.click('#earnFilt button[data-v="fed"]', label="FED 消息分頁")
    a.wait(1300)
    chips = pg.locator("#v-earnings .chip:visible")
    a.note(f"月曆上 FED 事件 {chips.count()} 個")
    if chips.count():
        a.hover("#v-earnings .chip:visible >> nth=0", 700)
        a.wait(300)
        a.click("#v-earnings .chip:visible >> nth=0", label="第一則 FED 事件")
        a.wait(1200)
        a.scroll_to_el("#v-earnings .fcard", 120, 1200)
        a.wait(2200)
        a.scroll(by=260, ms=1200)
        a.wait(1500)
    if chips.count() > 1:
        a.scroll(to_y=0, ms=900)
        a.click("#v-earnings .chip:visible >> nth=1", label="第二則 FED 事件")
        a.wait(1000)
        a.scroll_to_el("#v-earnings .fcard", 120, 1000)
        a.wait(1800)


@shot("S04", "md", "資金輪動：按 ▶ 播放輪盤動畫")
def s04(pg, a, start, base):
    goto(pg, base, "#flow/rotation" if a.mob else "#flow", 3500)
    a.scroll_to_el("#rotBack", 70 if a.mob else 110, 10)
    a.wait(800)
    start()
    a.wait(600)
    btn = "#rotBack .pb.play, #rotBack button.play, #rotBack button:has-text('▶')"
    a.click(btn, label="▶ 播放")
    a.move(3, 440, 700)          # 游標移到左緣，不壓圖、不觸發提示框
    a.cursor(False)
    a.wait(9500)


@shot("S05", "md", "資金分流樹（資金流水）：按 ▶ 播放")
def s05(pg, a, start, base):
    goto(pg, base, "#flow/sankey", 3500)
    a.scroll_to_el("#sankeyDays", 70 if a.mob else 110, 10)
    a.wait(800)
    start()
    a.wait(600)
    a.click("#sankeyDays .pb.play, #sankeyDays button:has-text('▶')", label="▶ 播放")
    a.move(3, 440, 700)
    a.cursor(False)
    a.wait(8500)


@shot("S06", "md", "產業熱力圖：整體 → 點一個產業方塊進去")
def s06(pg, a, start, base):
    goto(pg, base, "#heatmap/industry", 3500)
    _hide_tips(pg)
    start()
    a.wait(1200)
    el = "#indHeat"
    b = a.box(el)
    if b:
        pts = [(0.15, 0.2), (0.45, 0.3), (0.75, 0.2), (0.85, 0.6), (0.5, 0.75), (0.25, 0.6)]
        for fx, fy in pts:
            a.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy, 420)
            a.wait(120)
        a.note("點左上第一大方塊（晶圓代工）")
        a.click_xy(b["x"] + b["width"] * 0.12, b["y"] + b["height"] * 0.22, 500)
        a.wait(3500)
        if not a.mob:
            a.scroll(by=320, ms=1600)
        a.wait(1500)


def _to_dg(pg, a, base, route="#industry/ai_server"):
    goto(pg, base, route, 4000)
    a.scroll_to_el("#dgTools", 70 if a.mob else 90, 10)
    a.wait(900)


@shot("S07", "md", "AI 伺服器 2D 剖析圖：滑過幾個環節")
def s07(pg, a, start, base):
    _to_dg(pg, a, base)
    start()
    a.wait(800)
    segs = pg.locator("#prodDiagram [data-seg]")
    n = segs.count()
    a.note(f"剖析圖環節 {n} 個，逐一滑過")
    seen = 0
    for i in range(n):
        bb = segs.nth(i).bounding_box()
        if not bb or bb["width"] < 8 or bb["y"] < 60 or bb["y"] > _vh(pg) - 40:
            continue
        if a.mob:   # 手機沒有滑過，改成點環節（會跳說明卡）
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 380, 200)
            a.wait(1100)
        else:
            a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 380)
            a.wait(550)
        seen += 1
        if seen >= (4 if a.mob else 8):
            break
    a.wait(600)


def _to_3d(pg, a, base, route="#industry/ai_server"):
    _to_dg(pg, a, base, route)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    for _ in range(40):   # 假時鐘下 wait_for_function（rAF 輪詢）會卡住，改由 Python 輪詢
        if pg.evaluate("() => document.querySelectorAll('#prod3d canvas').length > 0"):
            break
        pg.wait_for_timeout(500)
    a.wait(2500)
    a.scroll_to_el("#prod3d", 60 if a.mob else 70, 600)
    a.wait(600)
    return a.box("#prod3d canvas", scroll=False)


@shot("S08a", "md", "3D：從 2D 切 3D，載入後自動轉動")
def s08a(pg, a, start, base):
    _to_dg(pg, a, base)
    start()
    a.wait(600)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    a.until("() => document.querySelectorAll('#prod3d canvas').length > 0", 15000)
    a.wait(800)
    a.scroll_to_el("#prod3d", 60 if a.mob else 70, 900)
    a.move(a.x + 40, a.y + 120, 500)
    a.wait(6000)


@shot("S08b", "md", "3D：拖曳旋轉（左右、上下）")
def s08b(pg, a, start, base):
    b = _to_3d(pg, a, base)
    start()
    a.wait(500)
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    w = b["width"]
    a.note("向右拖")
    a.drag(cx - w * 0.25, cy, cx + w * 0.25, cy, 1800)
    a.wait(500)
    a.note("向下拖（俯視）")
    a.drag(cx, cy - 60, cx, cy + 90, 1300)
    a.wait(500)
    a.note("向左拖回")
    a.drag(cx + w * 0.25, cy, cx - w * 0.2, cy - 30, 1800)
    a.wait(1200)


@shot("S08c", "md", "3D：滾輪拉近、拉遠（零件結構特寫）")
def s08c(pg, a, start, base):
    b = _to_3d(pg, a, base)
    start()
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    a.move(cx, cy, 500)
    a.wait(400)
    if a.mob:
        a.note("點兩下以外改用滾輪拉近（手機錄影以滑鼠滾輪代替雙指）")
    a.note("拉近")
    a.wheel(-900, 24, 2200)
    a.wait(900)
    a.drag(cx - 60, cy, cx + 80, cy + 20, 1500)
    a.wait(700)
    a.note("拉遠")
    a.wheel(700, 20, 1800)
    a.wait(1000)


@shot("S08d", "md", "3D：點零件，看零件說明卡（供應商列需模糊）")
def s08d(pg, a, start, base):
    b = _to_3d(pg, a, base)
    start()
    a.wait(500)
    labels = pg.locator(".mnum:visible" if a.mob else ".lbl3d:visible")   # 手機版 3D 用左右兩排編號圓鈕
    n = labels.count()
    a.note(f"零件標籤 {n} 個")
    picked = 0
    for i in range(n):
        bb = labels.nth(i).bounding_box()
        if not bb or bb["y"] < 70 or bb["y"] > _vh(pg) - 40:
            continue
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 450)
        a.wait(500)
        picked += 1
        if picked == 2:
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 200)
            a.note("點零件標籤")
            a.wait(2200)
        if picked >= 4:
            break
    a.wait(1500)


@shot("S08e", "d", "3D：轉到側面再拉近（第二個角度，零件為主）")
def s08e(pg, a, start, base):
    b = _to_3d(pg, a, base)
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    start()
    a.wait(300)
    a.drag(cx + 200, cy, cx - 260, cy + 40, 2200)
    a.wait(300)
    a.move(cx - 80, cy - 40, 500)
    a.wheel(-700, 20, 1800)
    a.wait(600)
    a.drag(cx - 80, cy + 60, cx + 120, cy - 40, 2000)
    a.wait(1500)


@shot("S08f", "md", "3D：拉近到機櫃內部、慢速環繞（零件結構特寫，公司名不入焦）")
def s08f(pg, a, start, base):
    b = _to_3d(pg, a, base)
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    a.move(cx, cy, 10)
    a.wheel(-1400, 30, 300)        # 錄影前先拉近
    a.wait(800)
    start()
    a.wait(400)
    a.note("慢速向左環繞")
    a.drag(cx + b["width"] * 0.3, cy, cx - b["width"] * 0.3, cy - 20, 3500)
    a.wait(300)
    a.note("再拉近一點、向上俯視")
    a.wheel(-400, 15, 1000)
    a.drag(cx, cy - 40, cx + 40, cy + 70, 2200)
    a.wait(300)
    a.note("向右環繞回來")
    a.drag(cx - b["width"] * 0.25, cy, cx + b["width"] * 0.25, cy, 3000)
    a.wait(800)


def _rot_and_pick(pg, a, start, base, route):
    b = _to_3d(pg, a, base, route)
    if not b:
        raise RuntimeError(f"{route} 沒有 3D 畫布")
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    start()
    a.wait(400)
    a.note("拖曳旋轉")
    a.drag(cx + b["width"] * 0.25, cy, cx - b["width"] * 0.25, cy + 20, 2600)
    a.wait(300)
    a.move(cx, cy, 300)
    a.wheel(-500, 15, 900)
    a.wait(300)
    labels = pg.locator(".mnum:visible" if a.mob else ".lbl3d:visible")
    for i in range(labels.count()):
        bb = labels.nth(i).bounding_box()
        if bb and 70 < bb["y"] < _vh(pg) - 40:
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 500, 400)
            a.note("點一個零件")
            break
    a.wait(2200)


@shot("S08g", "md", "3D：HBM 記憶體剖析（旋轉＋點零件）")
def s08g(pg, a, start, base):
    _rot_and_pick(pg, a, start, base, "#industry/semiconductor/dg/hbm")


@shot("S08h", "md", "3D：液冷散熱剖析（旋轉＋點零件）")
def s08h(pg, a, start, base):
    _rot_and_pick(pg, a, start, base, "#industry/ai_server/dg/liquid_cooling")


@shot("S09", "md", "供應鏈關聯圖：滑過節點、連線高亮")
def s09(pg, a, start, base):
    goto(pg, base, "#industry/ai_server", 4000)
    a.scroll_to_el("#relHead", 60, 10)
    a.wait(1200)
    start()
    a.wait(600)
    nodes = pg.locator("#relHead ~ * [data-seg], #relHead ~ * .rnode, #relHead ~ * .relseg")
    n = nodes.count()
    a.note(f"關聯圖節點 {n}")
    vh = _vh(pg)
    seen = 0
    for i in range(n):
        bb = nodes.nth(i).bounding_box()
        if not bb or bb["y"] < 80 or bb["y"] > vh - 40 or bb["width"] < 10:
            continue
        a.move(bb["x"] + min(bb["width"] / 2, 60), bb["y"] + 10, 420)
        a.wait(700)
        seen += 1
        if seen >= 7:
            break
    if not seen:
        a.wheel(300, 6, 600)
    a.wait(600)


@shot("S10", "md", "ETF 配息行事曆：月曆 → 點一天")
def s10(pg, a, start, base):
    goto(pg, base, "#etf/cal", 3500)
    start()
    a.wait(800)
    cells = pg.locator("#etfCalGrid .cald.has, #etfCalGrid .cald:has(.cg), #etfCalGrid .cald:has(span.n)")
    if not cells.count():
        cells = pg.locator("#etfCalGrid .cald")
    n = cells.count()
    a.note(f"有事件的日子 {n}")
    pick = cells.nth(min(n - 1, max(0, n // 2)))
    bb = pick.bounding_box()
    if bb:
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 700)
        a.wait(300)
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 150)
        a.note("點一天")
        a.wait(1500)
        a.scroll_to_el("#etfCalList", 90, 1200)
        a.wait(2200)


@shot("S11", "md", "ETF 總覽：類型分頁一個個切")
def s11(pg, a, start, base):
    goto(pg, base, "#etf/list", 3500)
    start()
    a.wait(700)
    tabs = pg.locator("#etfCatSeg button:visible, #etfCatBar button:visible")
    n = tabs.count()
    a.note(f"分類分頁 {n} 個")
    for i in list(range(1, n)) + [0]:
        bb = tabs.nth(i).bounding_box()
        if not bb:
            continue
        if a.mob and (bb["x"] < 0 or bb["x"] + bb["width"] > 390):
            tabs.nth(i).evaluate("e => e.scrollIntoView({block: 'nearest', inline: 'center'})")
            a.wait(300)
            bb = tabs.nth(i).bounding_box()
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 380, 250)
        a.wait(900)


@shot("S12", "md", "ETF 報酬比較：加入幾檔、切期間")
def s12(pg, a, start, base):
    goto(pg, base, "#etf/list", 3500)
    a.scroll_to_el("#etfRetCard", 70, 10)
    a.wait(900)
    start()
    a.wait(600)
    if a.click("#etfCmpDD .ddbtn, #etfCmpDD button", label="加入比較下拉"):
        a.wait(800)
        boxes = pg.locator("#etfCmpDD input[type=checkbox]:visible")
        n = boxes.count()
        a.note(f"下拉選項 {n}")
        k = 0
        for i in range(n):
            if k >= 3:
                break
            if boxes.nth(i).is_checked():
                continue
            bb = boxes.nth(i).bounding_box()
            if not bb or bb["y"] > _vh(pg) - 30:
                continue
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 350, 200)
            a.note(f"勾第 {i + 1} 檔")
            a.wait(900)
            k += 1
        pg.keyboard.press("Escape")
        a.wait(300)
        if pg.locator("#etfCmpDD input[type=checkbox]:visible").count():
            a.click("#etfCmpDD .ddbtn", 400, 200, label="收起下拉")
        a.wait(1200)
    sel = pg.locator("#etfRetCtl select:visible").first
    if sel.count():
        bb = sel.bounding_box()
        vals = pg.evaluate("() => [...document.querySelector('#etfRetCtl select').options].map(o => o.value)")
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 600)
        a.wait(400)
        for v in vals[:3]:
            pg.evaluate("([x,y]) => window.__vcRipple(x,y)", [a.x, a.y])
            sel.select_option(v)
            a.note(f"期間切到 {v}")
            a.wait(1600)
    elif a.mob:
        a.note("手機沒有期間下拉，改拖圖下方的區間拉桿")
        sl = pg.locator("#etfRetCard canvas:visible").first
        bb = sl.bounding_box() if sl.count() else None
        if bb:
            a.drag(bb["x"] + 30, bb["y"] + bb["height"] - 14, bb["x"] + bb["width"] * 0.55, bb["y"] + bb["height"] - 14, 1400)
            a.wait(1500)
    a.wait(800)


@shot("S13", "md", "ETF 現金流試算：調金額／換組合 → 複利試算表")
def s13(pg, a, start, base):
    goto(pg, base, "#etf/inc", 4000)
    start()
    a.wait(700)
    if a.mob and a.click("#m4EtfSet-inc", 450, 250, label="手機參數列（年領・100萬…）"):
        a.wait(1000)
    for lab in ["50 萬", "200 萬", "20 萬", "100 萬"]:
        if a.click(f"button:visible:text-is('{lab}')", 450, 250, label=f"金額 {lab}"):
            a.wait(1100)
    for lab in ["月領", "年領"]:
        if a.click(f"button:visible:text-is('{lab}')", 450, 250, label=lab):
            a.wait(1000)
    if a.mob:
        pg.keyboard.press("Escape")
        a.wait(400)
        for sel in ["button:visible:text-is('完成')", "button:visible:text-is('確定')", "[aria-label='關閉']:visible"]:
            if pg.locator(sel).count():
                a.click(sel, 400, 200, label="收起參數")
                break
        a.wait(600)
    combos = pg.locator("#v-etf button:visible:has-text('組合')")
    for i in range(min(3, combos.count())):
        bb = combos.nth(i).bounding_box()
        if bb and 0 <= bb["x"] < pg.viewport_size["width"] - 20:
            a.click_xy(bb["x"] + min(bb["width"] / 2, 50), bb["y"] + bb["height"] / 2, 400, 250)
            a.note(f"組合第 {i + 1} 個")
            a.wait(1300)
    a.scroll(to_y=0, ms=600)
    if a.click("button:visible:has-text('複利試算'), a:visible:has-text('複利試算'), .l4subtab:visible:has-text('複利')", 500, 300, label="複利試算表"):
        a.wait(2500)
        a.scroll(by=300 if a.mob else 200, ms=1400)
        a.wait(2000)


@shot("S14", "md", "LOGO 點開大圖 ＋ 客服鈕比比")
def s14(pg, a, start, base):
    goto(pg, base, "#overview", 3000)
    start()
    a.wait(600)
    if a.mob:
        a.click("#m4Burger", label="☰")
        a.wait(900)
        a.click(".m4brand picture", label="抽屜裡的 LOGO")
    else:
        a.click(".brand .logo", label="左上 LOGO")
    a.wait(2600)
    a.click_xy(a.x + 20, a.y + 300 if a.mob else a.y + 200, 500, 200)
    a.note("收起大圖")
    a.wait(800)
    if a.mob and pg.locator(".m4drawer:visible, .m4draw:visible").count():
        pg.keyboard.press("Escape")
    a.wait(400)
    a.hover("#supFab", 900)
    a.note("游標停在客服鈕（比比）")
    a.wait(2500)


@shot("S15", "md", "導覽：開「本頁導覽」走幾步")
def s15(pg, a, start, base):
    goto(pg, base, "#overview", 3000)
    start()
    a.wait(600)
    a.click("#twPageTourBtn", label="導覽鈕")
    a.wait(1200)
    if not pg.locator("#twTourNext:visible").count():
        for sel in ["button:visible:has-text('本頁導覽')", "a:visible:has-text('本頁導覽')", "#mmTourPage"]:
            if pg.locator(sel).count():
                a.click(sel, 400, 200, label="本頁導覽")
                break
    a.wait(2000)
    for i in range(5):
        if not pg.locator("#twTourNext:visible").count():
            break
        a.click("#twTourNext", 500, 300, label=f"下一步 {i + 1}")
        a.wait(2200)
    a.wait(500)


@shot("S16", "md", "客服面板（比比・問題小助手）：常見問題 → 意見反饋／願望清單")
def s16(pg, a, start, base):
    goto(pg, base, "#overview", 3000)
    start()
    a.wait(600)
    a.click("#supFab", label="客服鈕")
    a.wait(1300)
    a.click("#supPanel .faq button >> nth=0", label="第一題常見問題")
    a.wait(1600)
    a.click('#supPanel .sptabs button[data-t="fb"]', label="意見反饋")
    pg.evaluate("() => document.querySelectorAll('#supPanel input[type=email]').forEach(e => e.value = '')")  # 不露 email
    a.wait(1300)
    a.click('#supPanel #fbKind button[data-fk="wish"]', label="願望清單")
    pg.evaluate("() => document.querySelectorAll('#supPanel input[type=email]').forEach(e => e.value = '')")
    a.wait(1600)
    a.click('#supPanel #fbKind button[data-fk="fb"]', label="意見回饋")
    pg.evaluate("() => document.querySelectorAll('#supPanel input[type=email]').forEach(e => e.value = '')")
    a.wait(1500)


# ======================================================================== 第 3 版素材（--set v3）
# Andy 10-11：全部資訊公開（不藏、不模糊）；每個功能先「完整入框」停 2 秒再操作；節奏放慢（動作間隔 1～1.5 秒）。
# 桌機 1600×900 @2（輸出 3200×1800，剪 1920×1080 不必放大）；手機 390×844 @3。
DEVS3 = {
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
}
SHOTS3: dict = {}
# v3b：手機版這些鏡頭的卡片比 844 高 → 加高 viewport（寬仍 390、DPR 3，版面仍是手機版）讓整張卡片入框；值＝卡片高＋頂欄＋餘裕
V3C = ["V04", "V06"]   # v3c＝真實時間錄影（播放類鏡頭：資金輪動 ▶、資金分流樹 ▶）
V3B_H = {"V01": 1250, "V03": 1420, "V04": 1300, "V05": 1650, "V06": 1650, "V10": 1000, "V13": 1150, "V19": 1320, "V21": 1250}
GAP = 1200
# Andy：影片不提會員層級與使用次數 → 錄影瀏覽器裡把頁首會員徽章、額度圓環「剩 N 次」、「本頁 N 項限制」、額度備註藏起來（不改 site/）
HIDE_TIER_JS = r"""
(() => { const css = 'html body #acctBtn,html.m4 body .m4tools #acctBtn,html body .abtn.ame,html body #twQRing,html body .twqr,html body #twQPage,html body .twqp,html body .qnote,html body .qnote-row,html body .qlkov{display:none!important} #supPanel input[type=email],#supPanel #fbMail{color:transparent!important;-webkit-text-fill-color:transparent!important;caret-color:transparent!important}';
  const go = () => { const st = document.createElement('style'); st.id = '__vhide'; st.textContent = css; document.head.appendChild(st); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();
"""   # 動作之間的間隔（毫秒）


def shot3(sid, devs="md", desc=""):
    def deco(fn):
        SHOTS3[sid] = dict(fn=fn, devs=devs, desc=desc)
        return fn
    return deco


TOPPAD_JS = """() => { let pad = 0; for (const e of document.querySelectorAll('body *')) { const cs = getComputedStyle(e);
  if (cs.position !== 'fixed' && cs.position !== 'sticky') continue; const r = e.getBoundingClientRect();
  if (r.top <= 2 && r.height > 20 && r.height < 170 && r.width > innerWidth * 0.5 && r.bottom > pad) pad = r.bottom; } return Math.round(pad); }"""

MARK_JS = """([txt, key, up]) => { const vis = e => e.offsetParent && e.getBoundingClientRect().width > 0;
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,b,strong,.ttl,.dgsectitle,summary,span')].filter(e => vis(e) && e.children.length < 4 && (e.textContent || '').trim().startsWith(txt));
  for (const h of hs) { const c = h.closest(up || '.card'); if (c && vis(c)) { c.setAttribute('data-vcap', key); return true; } }
  return false; }"""


def mark(a, txt, key, up=".card"):
    """把「標題文字是 txt」的那張卡片標成 [data-vcap=key]，回傳選擇器（找不到回 None）。"""
    return f'[data-vcap="{key}"]' if a.pg.evaluate(MARK_JS, [txt, key, up]) else None


def frame(a, sel, hold=2000, ms=1100, label=""):
    """把 sel 捲到「整張都在畫面內」（扣掉頂欄），停 hold 毫秒，記下入框的時間區間。"""
    pg = a.pg
    if not sel or not pg.evaluate("(s) => { const e = document.querySelector(s); return !!(e && e.getBoundingClientRect().height); }", sel):
        a.note(f"找不到要入框的 {label or sel}")
        return False
    pad = pg.evaluate(TOPPAD_JS)
    vh = _vh(pg)
    top, h = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.top + scrollY, r.height]; }", sel)
    avail = vh - pad - 10
    y = top - pad - max(4, (avail - h) / 2) if h <= avail else top - pad - 6
    a.scroll(to_y=y, ms=ms)
    r = pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.top, r.bottom]; }", sel)
    full = r[0] >= pad - 2 and r[1] <= vh + 2
    t0 = a.t
    a.wait(hold)
    a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：{label or sel}" + ("" if full else f"（卡片高 {h:.0f}px 超過畫面，只入框上段）"))
    return True


def tap(a, sel, label="", gap=GAP, ms=700):
    ok = a.click(sel, ms, 450, label=label)
    if ok:
        a.wait(gap)
    return ok


def tab_txt(a, txt, scope=""):
    """點文字完全相同的按鈕（可見的第一個）；手機橫向捲動的分頁先 scrollIntoView。"""
    sel = f"{scope} button:visible:text-is('{txt}')".strip()
    loc = a.pg.locator(sel).first
    if not loc.count():
        sel = f"{scope} :is(button,a,[role=tab]):visible:has-text('{txt}')".strip()
        loc = a.pg.locator(sel).first
        if not loc.count():
            a.note(f"找不到「{txt}」")
            return False
    loc.evaluate("e => e.scrollIntoView({block: 'nearest', inline: 'center'})")
    return tap(a, sel, txt)


def goto3(pg, a, base, h, wait=3500):
    goto(pg, base, h, wait)


# ---------------------------------------------------------------- 總覽 / 今日事件 / 財經日曆
@shot3("V01", "md", "總覽：四張摘要卡、大盤三圖、資金熱力圖、熱門題材、漲跌家數（逐張完整入框）")
def v01(pg, a, start, base):
    goto3(pg, a, base, "#overview")
    start()
    a.wait(2200)
    a.note("頁首（摘要卡＋大盤）完整入框 0.0–2.2s")
    if a.mob:
        car = a.box(".ovcards, #ovCards, [class*=ovsum]", scroll=False)
        tab_txt(a, "資金流向")
        tab_txt(a, "熱度")
        tab_txt(a, "大盤")
        for t, k in [("漲跌家數", "o1")]:
            frame(a, mark(a, t, k, ".card, section"), 2200, label=t)
    else:
        for t, k in [("資金熱力圖", "o1"), ("熱門題材", "o2"), ("漲跌家數", "o3")]:
            frame(a, mark(a, t, k), 2200, label=t)
            a.wait(400)
    a.scroll(to_y=0, ms=1400)
    a.wait(800)


@shot3("V02", "md", "今日事件：打開事件清單 → 切分類 → 點一則")
def v02(pg, a, start, base):
    goto3(pg, a, base, "#overview")
    start()
    a.wait(800)
    if a.mob:
        tap(a, "#m4Burger", "☰")
        tap(a, '.m4item[data-act="events"]', "事件")
    else:
        tap(a, "#evToggle", "事件")
    t0 = a.t
    a.wait(2000)
    a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：今日事件清單")
    for c in ["科技", "總經", "台股"]:
        if pg.locator(f"#evList ~ *, .evchips, body").locator(f"button:visible:text-is('{c}')").count():
            tap(a, f"button:visible:text-is('{c}')", f"分類 {c}")
    a.hover("#evList .ev > a >> nth=0", 700)
    a.wait(1200)
    a.hover("#evList .ev > a >> nth=1", 700)
    a.wait(1200)
    chip = "#evList .ev .m a:visible >> nth=0"
    if pg.locator("#evList .ev .m a:visible").count():
        tap(a, chip, "點新聞裡提到的個股 → 跳個股頁", 2500)


@shot3("V03", "md", "財經日曆：公司財報 → 點一家 → FED 消息 → 點一則看說明")
def v03(pg, a, start, base):
    goto3(pg, a, base, "#earnings")
    start()
    frame(a, "#v-earnings .card, #v-earnings > *", 2000, label="財經日曆月曆")
    chip = "#v-earnings .chip:visible >> nth=0"
    if pg.locator("#v-earnings .chip:visible").count():
        tap(a, chip, "公司財報第一格")
        a.wait(1500)
    tap(a, '#earnFilt button[data-v="conf"]', "公司法說")
    tap(a, '#earnFilt button[data-v="fed"]', "FED 消息")
    if pg.locator("#v-earnings .chip:visible").count():
        tap(a, chip, "FED 第一則", 1000)
        frame(a, "#v-earnings .fcard", 2500, label="FED 事件說明卡")


# ---------------------------------------------------------------- 資金流向
@shot3("V04", "md", "資金輪動：完整入框 → ▶ 播放")
def v04(pg, a, start, base):
    goto3(pg, a, base, "#flow/rotation" if a.mob else "#flow")
    start()
    frame(a, "#flowRotCard", 2000, label="資金輪動卡")
    tap(a, "#rotBack .pb.play, #rotBack button:has-text('▶')", "▶ 播放", 300)
    a.move(3, 440, 700)
    a.cursor(False)
    a.wait(11000)


@shot3("V05", "md", "資金分流樹：完整入框 → 滑過分支")
def v05(pg, a, start, base):
    goto3(pg, a, base, "#flow/sankey")
    start()
    frame(a, "#flowSankeyCard", 2000, label="資金分流樹卡")
    b = a.box("#sankey", scroll=False)
    if b:
        for fx, fy in [(0.5, 0.2), (0.5, 0.5), (0.5, 0.75), (0.85, 0.3)]:
            a.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy, 800)
            a.wait(1300)


@shot3("V06", "md", "資金流水：分流樹按 ▶ 逐日播放")
def v06(pg, a, start, base):
    goto3(pg, a, base, "#flow/sankey")
    start()
    frame(a, "#flowSankeyCard", 2000, label="資金分流樹卡")
    tap(a, "#sankeyDays .pb.play, #sankeyDays button:has-text('▶')", "▶ 播放", 300)
    a.move(3, 440, 700)
    a.cursor(False)
    a.wait(10000)


@shot3("V07", "md", "族群×法人、資金集中度：完整入框 → 切天數")
def v07(pg, a, start, base):
    goto3(pg, a, base, "#flow/inst")
    if a.mob and not pg.locator("#flowInstCard:visible").count():
        tab_txt(a, "族群×法人")
    start()
    frame(a, "#flowInstCard", 2200, label="族群×法人")
    bs = pg.locator("#instDays button:visible")
    if bs.count() > 1:
        tap(a, "#instDays button:visible >> nth=1", "切天數")
    if a.mob and not pg.locator("#flowConcCard:visible").count():
        if not tab_txt(a, "集中度"):
            goto(pg, base, "#flow/inst/conc", 2500)
    frame(a, "#flowConcCard", 2200, label="資金集中度")
    bs = pg.locator("#concSeg button:visible")
    if bs.count() > 1:
        tap(a, "#concSeg button:visible >> nth=1", "切口徑")


# ---------------------------------------------------------------- 熱力圖
@shot3("V08", "md", "熱力圖（市場／產業）：完整入框 → 停在方塊看提示 → 點方塊進產業鏈")
def v08(pg, a, start, base):
    goto3(pg, a, base, "#heatmap/industry")
    start()
    frame(a, "#indHeat", 2000, label="整個台股一次看")
    b = a.box("#indHeat", scroll=False)
    for fx, fy in [(0.12, 0.2), (0.4, 0.2), (0.75, 0.25), (0.3, 0.75)]:
        a.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy, 800)
        a.wait(1500)
    a.note("點晶圓代工方塊")
    a.click_xy(b["x"] + b["width"] * 0.12, b["y"] + b["height"] * 0.22, 600, 400)
    a.wait(3500)


@shot3("V09", "md", "題材資金熱力：完整入框 → 提示框 → 點題材看剖析 → 換配色")
def v09(pg, a, start, base):
    goto3(pg, a, base, "#heatmap/theme")
    start()
    frame(a, "#themeMapCard", 2000, label="題材資金熱力")
    b = a.box("#themeMap", scroll=False)
    for fx, fy in [(0.1, 0.4), (0.27, 0.2), (0.52, 0.2), (0.62, 0.55)]:
        a.move(b["x"] + b["width"] * fx, b["y"] + b["height"] * fy, 800)
        a.wait(1500)
    a.note("點最大的題材方塊（AI 伺服器）")
    a.click_xy(b["x"] + b["width"] * 0.1, b["y"] + b["height"] * 0.4, 600, 400)
    a.wait(2500)
    frame(a, "#themeDetail", 2500, label="題材細節／剖析圖")
    a.scroll(by=400, ms=1500)
    a.wait(1500)


@shot3("V10", "md", "題材資金熱力（第二段）：點另一個題材、換顏色口徑")
def v10(pg, a, start, base):
    goto3(pg, a, base, "#heatmap/theme")
    start()
    frame(a, "#themeMapCard", 2000, label="題材資金熱力")
    b = a.box("#themeMap", scroll=False)
    a.click_xy(b["x"] + b["width"] * 0.27, b["y"] + b["height"] * 0.7, 700, 400)
    a.note("點「高階 PCB／CCL」")
    a.wait(2500)
    frame(a, "#themeDetail", 2500, label="題材細節")
    frame(a, "#themeMapCard", 1000, label="回到熱力圖")
    if pg.locator("#themeCtl .rotdd, #themeCtl button:visible").count():
        tap(a, "#themeCtl .rotdd >> nth=0, #themeCtl button:visible >> nth=0", "顏色口徑下拉")
        opt = pg.locator("#themeCtl [role=option]:visible, #themeCtl .ddlist button:visible, #themeCtl li:visible")
        if opt.count() > 1:
            tap(a, "#themeCtl [role=option]:visible >> nth=1, #themeCtl .ddlist button:visible >> nth=1, #themeCtl li:visible >> nth=1", "換口徑")
    a.wait(2000)


# ---------------------------------------------------------------- 產業地圖：2D → 4 個 3D → 關聯圖
@shot3("V11", "md", "產業地圖：全市場產業鏈 → 進 AI 伺服器 → 2D 剖析圖滑過環節")
def v11(pg, a, start, base):
    goto3(pg, a, base, "#industry", 4000)
    start()
    a.wait(2200)
    a.note("產業地圖首頁完整入框 0.0–2.2s")
    a.scroll(by=350, ms=1500)
    a.wait(1500)
    if not tap(a, "#v-industry :is(button,a,.tab,[role=tab]):visible:has-text('AI 伺服器')", "進 AI 伺服器產業鏈", 600):
        pg.evaluate("() => { location.hash = '#industry/ai_server'; }")
    a.wait(3000)
    if not pg.locator("#prodDiagram:visible").count():   # 進鏈之後預設在「族群總覽」→ 點「AI 伺服器」那一格剖析圖
        if not tap(a, 'a.segchip[href="#industry/ai_server/dg/ai_server"]', "AI 伺服器剖析圖", 2500):
            pg.evaluate("() => { location.hash = '#industry/ai_server/dg/ai_server'; }")
            a.wait(3000)
    sel = "#prodDiagram"
    host = pg.evaluate("() => { const e = document.querySelector('#prodDiagram'); const c = e && (e.closest('.dgsec') || e.parentElement); if (c) c.setAttribute('data-vcap', 'dg2d'); return !!c; }")
    frame(a, '[data-vcap="dg2d"]' if host else sel, 2200, label="2D 剖析圖")
    segs = pg.locator("#prodDiagram [data-seg]")
    seen = 0
    for i in range(segs.count()):
        bb = segs.nth(i).bounding_box()
        if not bb or bb["width"] < 8 or bb["y"] < 80 or bb["y"] > _vh(pg) - 40:
            continue
        if a.mob:
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 700, 300)
            a.wait(1500)
        else:
            a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 700)
            a.wait(1200)
        seen += 1
        if seen >= 5:
            break


def _3d_open(pg, a, base, route):
    _to_dg(pg, a, base, route)
    a.click('#dg3d button[data-dm="3d"]', label="切 3D")
    for _ in range(120):   # 機器忙時 3D 場景要很久才掛起來；最多等 60 秒，等不到就判這鏡失敗（不交假素材）
        if pg.evaluate("() => { const c = document.querySelector('#prod3d canvas'); return !!(c && c.getBoundingClientRect().height > 50); }"):
            break
        pg.wait_for_timeout(500)
    else:
        raise RuntimeError("3D 場景 60 秒內沒有掛起來")
    pg.wait_for_timeout(2500)


def spin(a, secs=5.5, turns=1.0, hide=False):
    """滑鼠拖曳旋轉一圈：等速水平拖曳（OrbitControls：拖畫布高度那麼長＝轉一圈）。
    分鏡定稿：比比跟著拖曳方向推 → 游標要看得到（hide=False）。"""
    b = a.box("#prod3d canvas", scroll=False)
    if not b:
        a.note("找不到 3D 畫布")
        a.wait(secs * 1000)
        return
    cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] * 0.55
    L = min(b["height"] * turns, b["width"] * 0.9)
    if a.mob:   # 手機：左右兩排編號鈕會吃掉拖曳 → 只在中間 64% 拖；OrbitControls 一圈＝拖「畫布高度」那麼長，所以依高度算要拖幾次
        L1 = b["width"] * 0.64
        x0 = b["x"] + b["width"] * 0.18
        k_drag = max(2, math.ceil(b["height"] * turns / L1 + 0.15))
        deg = k_drag * L1 / b["height"] * 360
        t0 = a.t
        for _ in range(k_drag):
            a.move(x0, cy, 350)
            a.wait(100)
            a.note(f"拖曳開始 ({x0:.0f},{cy:.0f})css → 影片({x0 * a.dsf:.0f},{cy * a.dsf:.0f})px")
            a.pg.mouse.down()
            n = round(secs / k_drag * FPS)
            for i in range(1, n + 1):
                k = i / n
                e = k if 0.08 < k < 0.92 else (0.5 - 0.5 * math.cos(math.pi * k))
                a._put(x0 + L1 * e, cy)
                a.frame()
            a.pg.mouse.up()
            a.x, a.y = x0 + L1, cy
            a.note(f"拖曳放開 ({x0 + L1:.0f},{cy:.0f})css → 影片({(x0 + L1) * a.dsf:.0f},{cy * a.dsf:.0f})px")
        a.note(f"手機分 {k_drag} 段拖曳，合計約轉 {deg:.0f}°，{t0:.1f}–{a.t:.1f}s")
        a.wait(300)
        return
    if False:   # （保留）CDP 觸控拖曳；實測手機頁滑鼠拖曳就轉得動，問題是起點落在左排編號鈕上：用 CDP 觸控事件拖（滑鼠拖在 has_touch 頁面上轉不動）
        cdp = a.rec.cdp
        tp = lambda t, x: cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": [] if t == "touchEnd" else [{"x": x, "y": cy}]})
        tp("touchStart", x0)
        a.frame()
        n = round(secs * FPS)
        t0 = a.t
        for i in range(1, n + 1):
            k = i / n
            e = k if 0.08 < k < 0.92 else (0.5 - 0.5 * math.cos(math.pi * k))
            tp("touchMove", x0 + L * e)
            a.frame()
        tp("touchEnd", 0)
        a.x, a.y = x0 + L, cy
        a.note(f"拖曳放開 ({x0 + L:.0f},{cy:.0f})css → 影片({(x0 + L) * a.dsf:.0f},{cy * a.dsf:.0f})px；手指左→右拖曳旋轉，{t0:.1f}–{a.t:.1f}s")
        a.wait(300)
        return
    a.pg.mouse.down()
    n = round(secs * FPS)
    t0 = a.t
    for i in range(1, n + 1):
        k = i / n
        e = k if 0.08 < k < 0.92 else (0.5 - 0.5 * math.cos(math.pi * k))   # 頭尾稍微緩一下，中間等速
        xx = x0 + L * e
        a._put(xx, cy)
        a.frame()
    a.pg.mouse.up()
    a.x, a.y = x0 + L, cy
    a.note(f"拖曳放開 ({x0 + L:.0f},{cy:.0f})css → 影片({(x0 + L) * a.dsf:.0f},{cy * a.dsf:.0f})px；左→右拖曳旋轉約 {L / b['height'] * 360:.0f}°，{t0:.1f}–{a.t:.1f}s")
    a.wait(300)
    a.cursor(True)


def _3d_show(pg, a, start, base, route, name):
    _3d_open(pg, a, base, route)
    start()
    frame(a, "#prod3d", 1500, label=f"{name} 3D 完整畫面")
    spin(a, 5.5, 1.0)
    t0 = a.t
    a.wait(1200)
    a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：{name} 3D 轉完停住")


@shot3("V12a", "md", "3D ①：AI 伺服器機櫃（完整入框自轉）")
def v12a(pg, a, start, base):
    _3d_show(pg, a, start, base, "#industry/ai_server", "AI 伺服器機櫃")


@shot3("V12b", "md", "3D ②：CoWoS-L 先進封裝（完整入框自轉）")
def v12b(pg, a, start, base):
    _3d_show(pg, a, start, base, "#industry/semiconductor/dg/ai_adv_packaging", "CoWoS-L 先進封裝")


@shot3("V12c", "md", "3D ③：HBM（完整入框自轉）")
def v12c(pg, a, start, base):
    _3d_show(pg, a, start, base, "#industry/semiconductor/dg/hbm", "HBM")


@shot3("V12d", "md", "3D ④：液冷（完整入框自轉）")
def v12d(pg, a, start, base):
    _3d_show(pg, a, start, base, "#industry/ai_server/dg/liquid_cooling", "液冷")


@shot3("V12e", "md", "3D：AI 伺服器點零件 → 看負責公司與環節")
def v12e(pg, a, start, base):
    _3d_open(pg, a, base, "#industry/ai_server")
    start()
    frame(a, "#prod3d", 1500, label="AI 伺服器 3D")
    labels = pg.locator(".mnum:visible" if a.mob else ".lbl3d:visible")
    # 挑一個「有台股公司」的零件（電源／PCB／CCL／散熱這類），避開「台股無直接對應」
    want = pg.evaluate("""(mob) => { const ls = [...document.querySelectorAll(mob ? '.mnum' : '.lbl3d')].filter(e => e.offsetParent);
      if (mob) return null;
      const i = ls.findIndex(e => /電源|PSU|PCB|CCL|液冷|散熱/.test(e.textContent) && e.querySelector('.chip3d'));
      return i; }""", a.mob)
    order = [want] if want not in (None, -1) else list(range(labels.count()))
    if a.mob:   # 手機：編號 07～09 一帶通常是電源／PCB；依序試，卡片沒寫「台股無直接對應」就停
        nums = pg.evaluate("() => [...document.querySelectorAll('.mnum')].filter(e => e.offsetParent).map(e => e.textContent.trim())")
        order = [nums.index(n) for n in ["10", "08", "07", "11", "12", "13", "09"] if n in nums]
    for i in order:
        bb = labels.nth(i).bounding_box()
        if not bb or bb["y"] < 90 or bb["y"] > _vh(pg) - 60:
            continue
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 800, 500)
        a.note("點零件 → 零件亮起、列出負責公司")
        a.wait(900)
        if a.mob and "台股無直接對應" in (pg.evaluate("() => document.body.innerText.slice(-4000)") or ""):
            a.note("這個零件沒有台股，換下一個")
            pg.keyboard.press("Escape")
            a.wait(600)
            continue
        break
    a.wait(2500)
    if not a.mob and 'i' in dir():   # 逐字抄下被點到的零件卡（剪輯要用）：標籤本體＋展開內容＋公司膠囊（含代號）＋說明卡
        try:
            txt = pg.evaluate("""(i) => { const L = [...document.querySelectorAll('.lbl3d')].filter(e => e.offsetParent)[i]; if (!L) return null;
              const o = { 標籤全文: L.innerText.trim(), 公司膠囊: [...L.querySelectorAll('.chip3d')].map(c => c.textContent.trim() + '（' + (c.title || '') + '）'),
                class: L.className };
              const pc = document.querySelector('#partCard'); if (pc && pc.offsetParent) o.說明卡 = pc.innerText.trim();
              const nt = document.querySelector('#dg3dNote'); if (nt && nt.offsetParent) o.圖下備註 = nt.innerText.trim();
              return o; }""", i)
            if txt:
                one = " ⏎ ".join(f"{k}：{v if isinstance(v, str) else '、'.join(v)}".replace("\n", " ⏎ ") for k, v in txt.items())
                a.note("零件卡逐字（點到的那一個）→ " + one.replace("\n", " ⏎ "))
                (DEF_OUT.parent / "raw_v3" / "part_card_ai_server_desktop.json").write_text(json.dumps(txt, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            a.note(f"零件卡文字抓取失敗：{exc}")
    if pg.locator("#partCard:visible").count():
        frame(a, "#partCard", 3000, label="零件說明卡（負責公司與環節）")
    else:
        t0 = a.t
        a.wait(2500)
        a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：零件標籤展開（負責公司）")


@shot3("V13", "md", "供應鏈關聯圖：完整入框 → 滑過節點連線變亮")
def v13(pg, a, start, base):
    goto3(pg, a, base, "#industry/ai_server", 4000)
    pg.evaluate("() => { const h = document.querySelector('#relHead'); let c = h && h.parentElement; while (c && c.parentElement && c.getBoundingClientRect().height < 250) c = c.parentElement; if (c) c.setAttribute('data-vcap', 'rel'); }")
    start()
    frame(a, '[data-vcap="rel"]', 2200, label="供應鏈關聯圖")
    nodes = pg.locator('[data-vcap="rel"] [data-seg], [data-vcap="rel"] .rnode, [data-vcap="rel"] .relseg')
    seen = 0
    for i in range(nodes.count()):
        bb = nodes.nth(i).bounding_box()
        if not bb or bb["y"] < 90 or bb["y"] > _vh(pg) - 40 or bb["width"] < 10:
            continue
        if a.mob:   # 手機沒有滑過 → 點節點（連線變亮）
            a.click_xy(bb["x"] + min(bb["width"] / 2, 60), bb["y"] + 10, 700, 300)
            a.wait(1600)
        else:
            a.move(bb["x"] + min(bb["width"] / 2, 60), bb["y"] + 10, 700)
            a.wait(1400)
        seen += 1
        if seen >= (3 if a.mob else 6):
            break


# ---------------------------------------------------------------- 個股
def _stock(pg, a, base):
    goto3(pg, a, base, "#stock/2330", 4500)


@shot3("V14", "md", "個股（台積電 2330）：K 線 → 切日／週 → 四週期同看")
def v14(pg, a, start, base):
    _stock(pg, a, base)
    start()
    frame(a, "#skChartCard", 2000, label="個股走勢卡")
    tab_txt(a, "日", "#skChartCard")
    a.wait(800)
    tab_txt(a, "週", "#skChartCard")
    tab_txt(a, "日", "#skChartCard")
    if pg.locator("#mtfBtn:visible").count():
        tap(a, "#mtfBtn", "四週期同看", 2500)
        frame(a, "#skChartCard", 1500, label="四週期同看")
        tap(a, "#mtfBtn", "收回")


@shot3("V15", "md", "個股：營收、法人、資券、大戶散戶分頁")
def v15(pg, a, start, base):
    _stock(pg, a, base)
    tabbar = pg.evaluate("""() => { const b = [...document.querySelectorAll('button')].find(x => x.offsetParent && x.textContent.trim() === '營收');
      const bar = b && b.parentElement; if (bar) bar.setAttribute('data-vcap', 'sktabs'); return !!bar; }""")
    start()
    a.wait(600)
    for t in ["營收", "法人", "資券", "大戶／散戶"]:
        if tab_txt(a, t):
            if tabbar:
                pg.evaluate("() => { const e = document.querySelector('[data-vcap=sktabs]'); }")
                y = pg.evaluate("() => document.querySelector('[data-vcap=sktabs]').getBoundingClientRect().top + scrollY") - pg.evaluate(TOPPAD_JS) - 6
                a.scroll(to_y=y, ms=900)
            t0 = a.t
            a.wait(2300)
            a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：{t} 分頁（分頁列置頂，內容在下方）")


# ---------------------------------------------------------------- 市場明細 / 選股策略 / 週期統計
def _sub(a, parent, txt):
    """桌機點側欄子分頁；手機點頁內分頁。"""
    if a.mob:
        return tab_txt(a, txt)
    return tap(a, f'#tabs .l4subtab[data-parent="{parent}"]:has-text("{txt}")', txt)


@shot3("V16", "md", "市場明細：漲跌家數 → 法人連買賣 → 站上均線 → 今日關注")
def v16(pg, a, start, base):
    goto3(pg, a, base, "#market")
    start()
    a.wait(2200)
    a.note("市場明細首頁完整入框 0.0–2.2s")
    for t in ["漲停", "成交值前段"]:
        if pg.locator(f"#v-market button:visible:has-text('{t}')").count():
            tap(a, f"#v-market button:visible:has-text('{t}')", t)
    for t in ["法人連買賣", "站上均線", "今日關注"]:
        if _sub(a, "market", t):
            a.scroll(to_y=0, ms=600)
            t0 = a.t
            a.wait(2200)
            a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：{t}")


@shot3("V17", "md", "選股策略：基本面列表 → 技術面 → 籌碼面 → 子標籤篩選")
def v17(pg, a, start, base):
    goto3(pg, a, base, "#explore")
    start()
    a.wait(2200)
    a.note("選股策略（基本面）完整入框 0.0–2.2s")
    a.scroll(by=300, ms=1300)
    a.wait(1000)
    a.scroll(to_y=0, ms=900)
    for t in ["技術面", "籌碼面"]:
        if _sub(a, "explore", t):
            t0 = a.t
            a.wait(1800)
            a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：{t}")
    if tap(a, "#slTagDd", "子標籤下拉"):
        opt = pg.locator("[role=option]:visible, .ddlist button:visible, .ddlist label:visible")
        if opt.count() > 1:
            bb = opt.nth(1).bounding_box()
            a.click_xy(bb["x"] + 20, bb["y"] + bb["height"] / 2, 600, 300)
            a.note("選一個子標籤")
            a.wait(1800)
            pg.keyboard.press("Escape")
            a.wait(1200)


@shot3("V18", "md", "週期統計：完整入框 → 切期間／勝率／長條圖")
def v18(pg, a, start, base):
    goto3(pg, a, base, "#season")
    start()
    frame(a, "#seasonHeatCard", 2200, label="週期統計熱力表")
    if a.mob:
        tap(a, "#mSeasonNum", "數字 開／關")
        tap(a, "#mSeasonNum", "數字 開／關")
        a.scroll(by=300, ms=1300)
        a.wait(1500)
    else:
        for t in ["近 5 年", "勝率", "長條圖", "熱力圖", "超額報酬", "全部"]:
            tab_txt(a, t, "#v-season")


# ---------------------------------------------------------------- ETF
@shot3("V19", "md", "ETF 配息行事曆：月曆 → 點一天 → 當日除息清單")
def v19(pg, a, start, base):
    goto3(pg, a, base, "#etf/cal")
    start()
    frame(a, "#etfCalCard", 2000, label="配息行事曆")
    cells = pg.locator("#etfCalGrid .cald")
    best = None
    for i in range(cells.count()):
        if cells.nth(i).evaluate("e => e.textContent.trim().length > 6"):
            best = i
            if i > 8:
                break
    if best is not None:
        bb = cells.nth(best).bounding_box()
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 700, 450)
        a.note("點有除息的那一天")
        a.wait(1500)
        frame(a, "#etfCalList", 2500, label="當日除息清單")


@shot3("V20", "md", "ETF 總覽：各類型分頁切換，看前五名")
def v20(pg, a, start, base):
    goto3(pg, a, base, "#etf/list")
    start()
    a.wait(2200)
    a.note("ETF 總覽（類型分頁＋三張前五名）完整入框 0.0–2.2s")
    tabs = pg.locator("#etfCatSeg button:visible, #etfCatBar button:visible")
    n = tabs.count()
    for i in list(range(1, n)) + [0]:
        tabs.nth(i).evaluate("e => e.scrollIntoView({block: 'nearest', inline: 'center'})")
        bb = tabs.nth(i).bounding_box()
        if not bb:
            continue
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 600, 300)
        a.note(f"類型分頁 {i + 1}")
        a.wait(1500)


@shot3("V21", "md", "ETF 報酬比較：完整入框 → 加入兩檔 → 切期間")
def v21(pg, a, start, base):
    goto3(pg, a, base, "#etf/list")
    start()
    frame(a, "#etfRetCard", 2000, label="報酬比較")
    if tap(a, "#etfCmpDD .ddbtn", "加入比較下拉", 800):
        boxes = pg.locator("#etfCmpDD input[type=checkbox]:visible")
        k = 0
        for i in range(boxes.count()):
            if k >= 2:
                break
            if boxes.nth(i).is_checked():
                continue
            bb = boxes.nth(i).bounding_box()
            if not bb or bb["y"] > _vh(pg) - 30:
                continue
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 600, 300)
            a.note(f"勾第 {i + 1} 檔")
            a.wait(1200)
            k += 1
        pg.keyboard.press("Escape")
        a.wait(300)
        if pg.locator("#etfCmpDD input[type=checkbox]:visible").count():
            tap(a, "#etfCmpDD .ddbtn", "收起下拉", 600)
        frame(a, "#etfRetCard", 2000, label="比較結果")
    sel = pg.locator("#etfRetCtl select:visible").first
    if sel.count():
        bb = sel.bounding_box()
        vals = pg.evaluate("() => [...document.querySelector('#etfRetCtl select').options].map(o => o.value)")
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 700)
        for v in vals[:3]:
            a.wait(500)
            pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [a.x, a.y])
            sel.select_option(v)
            a.note(f"期間切到 {v}（下拉選單 ({a.x:.0f},{a.y:.0f})css → 影片({a.x * a.dsf:.0f},{a.y * a.dsf:.0f})px）")
            a.wait(1500)


@shot3("V22", "md", "ETF 現金流試算：調目標金額 → 換組合 A／B")
def v22(pg, a, start, base):
    goto3(pg, a, base, "#etf/inc", 4000)
    start()
    a.wait(2200)
    a.note("現金流試算上半部完整入框 0.0–2.2s")
    if a.mob:
        if tap(a, "#m4EtfSet-inc", "參數列"):
            for lab in ["月領", "年領"]:
                tap(a, f"button:visible:text-is('{lab}')", lab)
            pg.keyboard.press("Escape")
            a.wait(800)
    else:
        for lab in ["50 萬", "200 萬", "100 萬"]:
            tap(a, f"button:visible:text-is('{lab}')", f"金額 {lab}")
    combos = pg.locator("#v-etf button:visible:has-text('組合')")
    for i in range(min(2, combos.count())):
        combos.nth(i).evaluate("e => e.scrollIntoView({block: 'nearest', inline: 'center'})")
        bb = combos.nth(i).bounding_box()
        if bb:
            a.click_xy(bb["x"] + min(bb["width"] / 2, 50), bb["y"] + bb["height"] / 2, 600, 300)
            a.note(f"組合 {'AB'[i]}")
            a.wait(1600)
    a.scroll(by=360 if a.mob else 260, ms=1400)
    a.wait(2000)


@shot3("V23", "md", "ETF 複利試算表：切到複利 → 完整入框 → 看曲線")
def v23(pg, a, start, base):
    goto3(pg, a, base, "#etf/inc", 4000)
    start()
    a.wait(800)
    tap(a, "button:visible:has-text('複利試算')", "複利試算表", 2200)
    a.scroll(by=200 if a.mob else 120, ms=1000)
    t0 = a.t
    a.wait(2200)
    a.note(f"完整入框 {t0:.1f}–{a.t:.1f}s：複利試算表")
    for lab in ["3 年", "1 年", "5 年"]:
        if pg.locator(f"#v-etf button:visible:text-is('{lab}')").count():
            tap(a, f"#v-etf button:visible:text-is('{lab}')", lab)
    a.scroll(by=400, ms=1500)
    a.wait(1800)


# ---------------------------------------------------------------- 自選 / 比比
@shot3("V24", "md", "自選清單：輸入代號加入三檔 → 清單存起來")
def v24(pg, a, start, base):
    goto3(pg, a, base, "#watch")
    start()
    frame(a, "#v-watch .card", 1800, label="自選清單（空）")
    inp = "#v-watch input:visible"
    for code in ["2330", "2454", "2317"]:
        if not a.click(inp, 700, 300, label="加入股票輸入框"):
            break
        for ch in code:
            pg.keyboard.type(ch)
            a.wait(160)
        a.wait(900)
        pg.keyboard.press("Enter")
        a.note(f"加入 {code}")
        a.wait(1400)
    frame(a, "#v-watch .card", 2500, label="自選清單（三檔）")


@shot3("V27", "md", "頂部搜尋：點搜尋框（熱門清單）→ 慢打「台積電」→ 下拉建議 → 進個股；再打代號「2454」")
def v27(pg, a, start, base):
    goto3(pg, a, base, "#overview")
    start()
    a.wait(1200)
    for word in ["台積電", "2454"]:
        if a.mob:
            tap(a, "#m4Search", "搜尋鈕", 300)
        tap(a, "#q", "搜尋框", 300)
        pg.evaluate("() => { const q = document.querySelector('#q'); if (q) { q.value = ''; q.dispatchEvent(new Event('input', {bubbles: true})); q.focus(); } }")
        a.wait(1300)
        a.note("搜尋框打開（熱門清單）")
        t0 = a.t
        for ch in word:
            pg.keyboard.type(ch)
            a.wait(500)
        a.note(f"打字「{word}」{t0:.1f}–{a.t:.1f}s")
        a.wait(1500)
        a.note("下拉建議停 1.5 秒")
        sug = pg.locator("#sugg :is(a,button,li,[role=option]):visible")
        if sug.count():
            bb = sug.first.bounding_box()
            a.click_xy(bb["x"] + min(bb["width"] / 2, 90), bb["y"] + bb["height"] / 2, 700, 400)
            a.note("點第一筆建議 → 進個股頁")
        else:
            pg.keyboard.press("Enter")
            a.note("沒有下拉建議，按 Enter")
        a.wait(3000)


@shot3("V25", "md", "比比導覽：開本頁導覽走四步")
def v25(pg, a, start, base):
    goto3(pg, a, base, "#overview")
    start()
    a.wait(800)
    tap(a, "#twPageTourBtn", "導覽鈕")
    if not pg.locator("#twTourNext:visible").count():
        for sel in ["button:visible:has-text('本頁導覽')", "a:visible:has-text('本頁導覽')"]:
            if pg.locator(sel).count():
                tap(a, sel, "本頁導覽")
                break
    a.wait(1200)
    for i in range(4):
        if not pg.locator("#twTourNext:visible").count():
            break
        tap(a, "#twTourNext", f"下一步 {i + 1}", 2200)


@shot3("V26", "md", "比比客服面板：常見問題 → 意見反饋 → 願望清單（輸入一則願望）")
def v26(pg, a, start, base):
    goto3(pg, a, base, "#overview")
    start()
    a.wait(800)
    tap(a, "#supFab", "比比客服鈕", 1500)
    tap(a, "#supPanel .faq button >> nth=0", "常見問題第一題", 1800)
    tap(a, "#supPanel .faq button >> nth=4", "常見問題第五題", 1800)
    tap(a, '#supPanel .sptabs button[data-t="fb"]', "意見反饋")
    pg.evaluate("() => document.querySelectorAll('#supPanel input[type=email]').forEach(e => e.value = '')")
    tap(a, '#supPanel #fbKind button[data-fk="wish"]', "願望清單")
    pg.evaluate("() => document.querySelectorAll('#supPanel input[type=email]').forEach(e => e.value = '')")
    if a.click("#wsWant", 600, 300, label="想要的功能"):
        for ch in "希望自選股可以設價格提醒":
            pg.keyboard.type(ch)
            a.wait(120)
    a.wait(2200)



# ------------------------------------------------------------------ 主程式
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="")
    ap.add_argument("--dev", default="md")
    ap.add_argument("--out", default="")
    ap.add_argument("--set", default="v2", choices=["v2", "v3", "v3b", "v3c"], help="v3＝第 3 版素材（桌機 1600×900@2、不藏 B 類、完整入框）")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--log-only", action="store_true", help="不截圖，只重跑一次操作記下點擊秒數與座標（已錄好的鏡頭補座標用）")
    args = ap.parse_args()
    _import_shots()
    v3 = args.set.startswith("v3")
    reg = SHOTS3 if v3 else SHOTS
    devs_cfg = DEVS3 if v3 else DEVS
    if args.set == "v3c" and not args.shots.strip():
        args.shots = ",".join(V3C)
    if args.set == "v3b":   # 手機版「卡片比畫面高」的鏡頭：用加高的 viewport 重錄，整張卡片完整入框
        if args.shots.strip() == "":
            args.shots = ",".join(V3B_H)
        args.dev = "m"
    if not args.out:
        args.out = str(DEF_OUT.parent / "raw_v3") if v3 else str(DEF_OUT)
    out = Path(args.out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    want = [s.strip() for s in args.shots.split(",") if s.strip()] or list(reg)
    meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8")) if (SITE / "data" / "meta.json").exists() else {}
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}/index.html"
    logf = out / (f"coords_{args.port}.json" if args.log_only else f"capture_log_{args.port}.json")   # 平行跑多支時各寫各的
    log = json.loads(logf.read_text(encoding="utf-8")) if logf.exists() else {}
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                                  args=["--disable-gpu", "--enable-unsafe-swiftshader"])  # CPU 點陣化：比 SwiftShader 合成快 10 倍以上；WebGL 仍走 SwiftShader
            for sid in want:
                spec = reg[sid]
                for dev in [d for d in args.dev if d in spec["devs"]]:
                    cfg = dict(devs_cfg[dev])
                    if args.set == "v3c" and dev == "d":
                        cfg["device_scale_factor"] = 1.5     # 真實時間錄影：桌機 DPR 1.5（2400×1350）換流暢
                    if args.set == "v3b":
                        cfg["viewport"] = {"width": 390, "height": V3B_H[sid]}
                    ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                    import datetime as _dt
                    if args.set != "v3c":
                        ctx.clock.install(time=_dt.datetime.now(tz=_dt.timezone.utc))
                    ctx.add_init_script(PRESET)
                    fake_api(ctx)
                    if not v3:   # v3：Andy「全部資訊公開」→ 不藏 B 類
                        ctx.add_init_script(HIDE_B_JS)
                    else:
                        ctx.add_init_script(HIDE_TIER_JS)
                    if not v3:   # v3：剪輯在後製畫比比的游標與漣漪 → 錄影不畫游標、不畫漣漪（座標照記）
                        ctx.add_init_script(CURSOR_JS % ("true" if dev == "m" else "false"))
                    pg = ctx.new_page()
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                    pg.goto(base + "#overview", wait_until="networkidle")
                    pg.wait_for_timeout(2500)
                    act = Act(pg, dev == "m")
                    act.x, act.y = cfg["viewport"]["width"] - 4, cfg["viewport"]["height"] * 0.55   # 起始游標放右緣，不壓到圖表提示框
                    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                    rec = Recorder(pg, W, H, dry=args.log_only, realtime=(args.set == "v3c"))
                    act.dsf = cfg["device_scale_factor"]
                    act.log_moves = v3   # v3 沒有錄進游標 → 游標路徑寫進 shots.md 給後製畫比比
                    name = f"{sid}_{'mobile' if dev == 'm' else 'desktop'}" + ("_v3b" if args.set == "v3b" else "_v3c" if args.set == "v3c" else "")
                    try:
                        # 每鏡自己決定何時開錄：fn(pg, act, rec_start) —— 先做準備（換頁、等圖畫完）再開錄
                        state = {}

                        def rec_start(state=state, rec=rec, act=act, name=name):
                            act.log.clear()
                            act.rec = rec
                            act._put(act.x, act.y)
                            rec.start(out / f".tmp_{name}")
                            state["on"] = True
                        spec["fn"](pg, act, rec_start, base)
                        if not state.get("on"):
                            raise RuntimeError("這一鏡沒有開錄")
                        mp4 = out / f"{name}.mp4"
                        r = rec.stop(mp4)
                        if r.get("ok") and not r.get("dry"):
                            mid = r["dur"] / 2
                            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{mid:.2f}", "-i", str(mp4),
                                            "-frames:v", "1", str(out / "thumbs" / f"{name}.png")], check=True)
                        r.update(size=f"{W}x{H}", steps=act.log, errs=errs[:5], desc=spec["desc"],
                                 data_date=meta.get("data_date"))
                        log[name] = r
                        print(name, json.dumps({k: r[k] for k in r if k not in ("steps",)}, ensure_ascii=False))
                    except Exception as exc:  # noqa: BLE001
                        log[name] = {"ok": False, "why": str(exc)[:300], "steps": act.log}
                        print(name, "失敗：", str(exc)[:300])
                        rec.on = False
                    logf.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
                    ctx.close()
            b.close()
    finally:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
