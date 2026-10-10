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
權限：本機沒有會員系統（account_config 未設定）→ perm.js 走「全部照預設＝全開」，Plus 功能看得到，不必模擬登入。
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


# ------------------------------------------------------------------ 錄影器
class Recorder:
    def __init__(self, pg, w, h):
        self.pg, self.w, self.h = pg, w, h
        self.cdp = pg.context.new_cdp_session(pg)
        self.frames: list[tuple[float, str]] = []
        self.dir: Path | None = None
        self.on = False
        self.cdp.on("Page.screencastFrame", self._frame)

    def _frame(self, f):
        if self.on and self.dir is not None:
            ts = f["metadata"].get("timestamp") or time.time()
            fn = self.dir / f"f{len(self.frames):06d}.png"
            fn.write_bytes(base64.b64decode(f["data"]))
            self.frames.append((ts, str(fn)))
        try:
            self.cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})
        except Exception:  # noqa: BLE001
            pass

    def start(self, tmpdir: Path):
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
        tmpdir.mkdir(parents=True)
        self.dir, self.frames, self.on = tmpdir, [], True
        self.t0 = time.time()
        self.cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1,
                                               "maxWidth": self.w, "maxHeight": self.h})
        # 逼出第一格（畫面靜止時 screencast 不送格）
        self.pg.evaluate("() => { document.body.style.outline = '0 solid transparent'; requestAnimationFrame(() => document.body.style.outline = ''); }")
        self.pg.wait_for_timeout(120)

    def stop(self, out_mp4: Path) -> dict:
        t1 = time.time()
        self.pg.wait_for_timeout(80)
        self.on = False
        try:
            self.cdp.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001
            pass
        fr = sorted(self.frames)
        if not fr:
            return {"ok": False, "why": "沒有任何畫格"}
        t0 = fr[0][0]
        dur = max(t1 - self.t0 - 0.12, fr[-1][0] - t0 + 1 / FPS)
        n = int(dur * FPS)
        seq = self.dir / "seq"
        seq.mkdir()
        j = 0
        gaps = 0
        last_src = None
        for i in range(n):
            t = t0 + i / FPS
            while j + 1 < len(fr) and fr[j + 1][0] <= t:
                j += 1
            src = fr[j][1]
            os.link(src, seq / f"s{i:06d}.png")
            if src == last_src:
                gaps += 1
            last_src = src
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(seq / "s%06d.png"),
               "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_mp4)]
        subprocess.run(cmd, check=True)
        # 實際畫格率（不同畫格數 ÷ 秒數）—— 畫面靜止時本來就不會有新格，所以只是參考
        uniq = len(fr)
        shutil.rmtree(self.dir)
        return {"ok": True, "dur": round(n / FPS, 2), "frames_src": uniq, "src_fps": round(uniq / max(dur, 0.01), 1)}


# ------------------------------------------------------------------ 操作工具
class Act:
    def __init__(self, pg, mob: bool):
        self.pg, self.mob = pg, mob
        self.x, self.y = (195, 600) if mob else (900, 500)
        self.log: list[str] = []
        self.t0 = time.time()

    def note(self, s: str):
        self.log.append(f"{time.time() - self.t0:5.1f}s {s}")

    def wait(self, ms):
        self.pg.wait_for_timeout(ms)

    def cursor(self, show=True):
        self.pg.evaluate("(h) => window.__vcHide && window.__vcHide(h)", not show)

    def move(self, x, y, ms=600):
        n = max(2, int(ms / 16))
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            k = i / n
            e = 0.5 - 0.5 * math.cos(math.pi * k)  # 緩入緩出
            xx, yy = x0 + (x - x0) * e, y0 + (y - y0) * e
            self.pg.mouse.move(xx, yy)
            self.pg.evaluate("([x,y]) => window.__vcMove && window.__vcMove(x,y)", [xx, yy])
            self.pg.wait_for_timeout(8)
        self.x, self.y = x, y

    def box(self, sel, scroll=True):
        loc = self.pg.locator(sel).first
        if scroll:
            try:
                loc.scroll_into_view_if_needed(timeout=3000)
            except Exception:  # noqa: BLE001
                pass
        b = loc.bounding_box()
        return b

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
        self.pg.mouse.click(x, y)

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
        self.wait(200)
        self.pg.mouse.down(button=button)
        n = max(2, int(ms / 16))
        for i in range(1, n + 1):
            k = i / n
            e = 0.5 - 0.5 * math.cos(math.pi * k)
            xx, yy = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
            self.pg.mouse.move(xx, yy)
            self.pg.evaluate("([x,y]) => window.__vcMove && window.__vcMove(x,y)", [xx, yy])
            self.pg.wait_for_timeout(8)
        self.pg.mouse.up(button=button)
        self.x, self.y = x1, y1

    def wheel(self, dy, steps=10, ms=600):
        for _ in range(steps):
            self.pg.mouse.wheel(0, dy / steps)
            self.pg.wait_for_timeout(ms / steps)

    def scroll(self, to_y=None, by=None, ms=1500, el="auto"):
        """以 rAF 平滑捲動（頁面或指定的捲動容器）。"""
        self.pg.evaluate("""async ([to, by, ms, el]) => {
          const sc = el === 'auto' ? (document.scrollingElement || document.documentElement) : document.querySelector(el);
          const y0 = sc.scrollTop, max = sc.scrollHeight - sc.clientHeight;
          let y1 = to == null ? y0 + by : to; y1 = Math.max(0, Math.min(max, y1));
          const t0 = performance.now();
          await new Promise(res => { const f = () => { const k = Math.min(1, (performance.now() - t0) / ms);
            const e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2; sc.scrollTop = y0 + (y1 - y0) * e;
            k < 1 ? requestAnimationFrame(f) : res(); }; requestAnimationFrame(f); });
        }""", [to_y, by, ms, el])

    def scroll_to_el(self, sel, offset=80, ms=900):
        y = self.pg.evaluate("([s,o]) => { const e = document.querySelector(s); if (!e) return null; return e.getBoundingClientRect().top + scrollY - o; }", [sel, offset])
        if y is not None:
            self.scroll(to_y=y, ms=ms)
        return y is not None


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
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import shots_def  # noqa: F401  鏡頭腳本另放一支，方便調整

# ------------------------------------------------------------------ 主程式
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="")
    ap.add_argument("--dev", default="md")
    ap.add_argument("--out", default=str(DEF_OUT))
    args = ap.parse_args()
    _import_shots()
    out = Path(args.out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    want = [s.strip() for s in args.shots.split(",") if s.strip()] or list(SHOTS)
    meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8")) if (SITE / "data" / "meta.json").exists() else {}
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}/index.html"
    logf = out / "capture_log.json"
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
                    ctx.add_init_script(PRESET)
                    ctx.add_init_script(CURSOR_JS % ("true" if dev == "m" else "false"))
                    pg = ctx.new_page()
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                    pg.goto(base + "#overview", wait_until="networkidle")
                    pg.wait_for_timeout(2500)
                    act = Act(pg, dev == "m")
                    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                    rec = Recorder(pg, W, H)
                    name = f"{sid}_{'mobile' if dev == 'm' else 'desktop'}"
                    try:
                        # 每鏡自己決定何時開錄：fn(pg, act, rec_start) —— 先做準備（換頁、等圖畫完）再開錄
                        state = {}

                        def rec_start(state=state, rec=rec, act=act, name=name):
                            act.t0 = time.time()
                            act.log.clear()
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
                                 data_date=meta.get("date") or meta.get("asof") or meta.get("last_date"))
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
