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
    def __init__(self, pg, w, h):
        self.pg, self.w, self.h = pg, w, h
        self.cdp = pg.context.new_cdp_session(pg)
        self.dir: Path | None = None
        self.n = 0
        self.on = False
        self.acc = 0.0

    def start(self, tmpdir: Path):
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True)
        self.dir, self.n, self.on, self.acc = tmpdir, 0, True, 0.0
        import datetime as _dt
        now = self.pg.evaluate("() => Date.now()")
        self.pg.clock.pause_at(_dt.datetime.fromtimestamp(now / 1000 + 0.02, tz=_dt.timezone.utc))
        self.frame()

    def frame(self):
        if not self.on:
            return
        self.acc += 1000 / FPS
        ms = int(self.acc)
        self.acc -= ms
        self.pg.clock.run_for(ms)
        self.pg.evaluate(ANIM_JS, ms)
        r = self.cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True,
                                                     "captureBeyondViewport": False})
        (self.dir / f"s{self.n:06d}.png").write_bytes(base64.b64decode(r["data"]))
        self.n += 1

    def stop(self, out_mp4: Path) -> dict:
        self.on = False
        try:
            self.pg.clock.resume()
        except Exception:  # noqa: BLE001
            pass
        if not self.n:
            return {"ok": False, "why": "沒有任何畫格"}
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

    @property
    def t(self):
        return (self.rec.n / FPS) if (self.rec and self.rec.on) else 0.0

    def note(self, s: str):
        self.log.append(f"{self.t:5.1f}s {s}")

    def frame(self):
        if self.rec and self.rec.on:
            self.rec.frame()

    def wait(self, ms):
        if self.rec and self.rec.on:
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
        self.pg.mouse.down(button=button)
        self.frame()
        n = max(1, round(ms * FPS / 1000))
        for i in range(1, n + 1):
            e = _ease(i / n)
            self._put(x0 + (x1 - x0) * e, y0 + (y1 - y0) * e)
            self.frame()
        self.pg.mouse.up(button=button)
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
        a.click("#m4Burger", label="收起抽屜") if pg.locator("#m4Burger").is_visible() else None
        a.wait(600)
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
    if a.mob:
        a.wait(300)
        a.move(330, 760, 600)
    else:
        a.move(1180, 600, 900)
    a.wait(9500)


@shot("S05", "md", "資金分流樹（資金流水）：按 ▶ 播放")
def s05(pg, a, start, base):
    goto(pg, base, "#flow/sankey", 3500)
    a.scroll_to_el("#sankeyDays", 70 if a.mob else 110, 10)
    a.wait(800)
    start()
    a.wait(600)
    a.click("#sankeyDays .pb.play, #sankeyDays button:has-text('▶')", label="▶ 播放")
    if a.mob:
        a.move(330, 760, 600)
    else:
        a.move(1180, 640, 900)
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
        a.scroll(by=320, ms=1600)
        a.wait(1500)


def _to_dg(pg, a, base):
    goto(pg, base, "#industry/ai_server", 4000)
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
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 380)
        a.wait(550)
        seen += 1
        if seen >= 8:
            break
    a.wait(600)


def _to_3d(pg, a, base):
    _to_dg(pg, a, base)
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
    labels = pg.locator(".lbl3d:visible")
    n = labels.count()
    a.note(f"零件標籤 {n} 個")
    picked = 0
    for i in range(n):
        bb = labels.nth(i).bounding_box()
        if not bb or bb["y"] < b["y"] + 20 or bb["y"] > b["y"] + b["height"] - 20:
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
        opts = pg.locator("#etfCmpDD input[type=checkbox]:visible, #etfCmpDD .ddlist label:visible, #etfCmpDD li:visible")
        n = opts.count()
        a.note(f"下拉選項 {n}")
        k = 0
        for i in range(n):
            bb = opts.nth(i).bounding_box()
            if not bb or bb["y"] > _vh(pg) - 30:
                continue
            chk = pg.evaluate("(i) => { const e = [...document.querySelectorAll('#etfCmpDD input[type=checkbox]')].filter(x => x.offsetParent)[i]; return e ? e.checked : null; }", i)
            if chk:
                continue
            a.click_xy(bb["x"] + 14, bb["y"] + bb["height"] / 2, 300, 200)
            a.wait(700)
            k += 1
            if k >= 2:
                break
        pg.keyboard.press("Escape")
        a.click_xy(a.x, max(80, a.y - 200), 300, 100) if False else None
        a.wait(900)
    sel = pg.locator("#etfRetCtl select:visible").first
    if sel.count():
        bb = sel.bounding_box()
        vals = pg.evaluate("() => [...document.querySelector('#etfRetCtl select').options].map(o => o.value)")
        a.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 600)
        a.wait(400)
        for v in vals[:3]:
            a.pg.evaluate("([x,y]) => window.__vcRipple(x,y)", [a.x, a.y])
            sel.select_option(v)
            a.note(f"期間切到 {v}")
            a.wait(1600)
    a.wait(800)


@shot("S13", "md", "ETF 現金流試算：調金額／換組合 → 複利試算表")
def s13(pg, a, start, base):
    goto(pg, base, "#etf/inc", 4000)
    start()
    a.wait(700)
    for lab in ["50 萬", "200 萬", "20 萬", "100 萬"]:
        if a.click(f"#v-etf button:visible:text-is('{lab}')", 450, 250, label=f"金額 {lab}"):
            a.wait(1100)
    for lab in ["月領", "年領"]:
        if a.click(f"#v-etf button:visible:text-is('{lab}')", 450, 250, label=lab):
            a.wait(1000)
    combos = pg.locator("#v-etf button:visible:has-text('組合')")
    for i in range(min(3, combos.count())):
        bb = combos.nth(i).bounding_box()
        if bb:
            a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 400, 250)
            a.note(f"組合第 {i + 1} 個")
            a.wait(1300)
    a.scroll(to_y=0, ms=600)
    if a.click("#v-etf button:visible:has-text('複利試算表')", 500, 300, label="複利試算表"):
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
    if a.mob:
        a.click("#moreBtn", label="⋯")
        a.wait(700)
        a.click("#mmTourPage, #mmTourSite", label="本頁導覽")
    else:
        a.click("#twTourBtn", label="導覽")
    a.wait(2000)
    for i in range(4):
        nx = pg.locator(".twtour button:visible:has-text('下一步'), [class*=tour] button:visible:has-text('下一步')").first
        if not nx.count():
            break
        bb = nx.bounding_box()
        a.click_xy(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2, 500, 300)
        a.note(f"下一步 {i + 1}")
        a.wait(2000)
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
    a.wait(1300)
    a.click('#supPanel #fbKind button[data-fk="wish"]', label="願望清單")
    a.wait(1600)
    a.click('#supPanel #fbKind button[data-fk="fb"]', label="意見回饋")
    a.wait(1500)


# ------------------------------------------------------------------ 主程式
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="")
    ap.add_argument("--dev", default="md")
    ap.add_argument("--out", default=str(DEF_OUT))
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()
    _import_shots()
    out = Path(args.out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    want = [s.strip() for s in args.shots.split(",") if s.strip()] or list(SHOTS)
    meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8")) if (SITE / "data" / "meta.json").exists() else {}
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}/index.html"
    logf = out / f"capture_log_{args.port}.json"   # 平行跑多支時各寫各的
    log = json.loads(logf.read_text(encoding="utf-8")) if logf.exists() else {}
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                                  args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            for sid in want:
                spec = SHOTS[sid]
                for dev in [d for d in args.dev if d in spec["devs"]]:
                    cfg = DEVS[dev]
                    ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                    import datetime as _dt
                    ctx.clock.install(time=_dt.datetime.now(tz=_dt.timezone.utc))
                    ctx.add_init_script(PRESET)
                    fake_api(ctx)
                    ctx.add_init_script(HIDE_B_JS)
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
                    rec = Recorder(pg, W, H)
                    name = f"{sid}_{'mobile' if dev == 'm' else 'desktop'}"
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
                        if r.get("ok"):
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
