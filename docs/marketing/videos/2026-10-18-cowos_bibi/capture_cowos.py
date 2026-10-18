"""短影片 cowos_bibi（CoWoS 為什麼缺貨，比比主持）的網站素材錄製（真實網站、亮色主題、手機寬 390×844 @3x）。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload 產 site/data）：
    python docs/marketing/videos/2026-10-17-cowos_bibi/capture_cpo.py --probe   # 整頁截圖，看哪裡有個股要遮
    python docs/marketing/videos/2026-10-17-cowos_bibi/capture_cpo.py           # 逐格捲動錄影（PNG 序列 → mp4）

做法：沿用 video_1010/capture.py 的預設（同意條款、導覽、亮色主題先寫進 localStorage），
不登入任何帳號（不會出現會員資料）；逐格 window.scrollTo → CDP 截圖，所以 30fps 不掉格。
法遵：畫面上任何個股代號／公司名（題材成分股、熱力圖方塊、文章清單裡的公司名）在錄影的瀏覽器裡
用 CSS 模糊（只在錄影時注入，不改 site/）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SITE = ROOT / "site"
OUT = Path(os.environ.get("COWOS_SCR", "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/video_cowos")) / "raw"
PORT = 8798
FPS = 30
PRESET = ("try{localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'video'}));"
          "localStorage.setItem('tw.tour','*');localStorage.setItem('tw.theme','light');"
          "localStorage.setItem('tw.notice.banner','*');}catch(e){}")

# 模糊：任何看起來像個股的文字（4～6 碼代號、或含代號的元素），以及成分股清單的容器
BLUR_JS = r"""
(() => {
  const st = document.createElement('style');
  st.textContent = `.__blur{filter:blur(7px)!important}
    .supfab,.bibiring,#supFab{display:none!important}`;
  const CODE = /(^|[^0-9.])[1-9][0-9]{3}[A-Z]?($|[^0-9.%])/;
  const NAMES = __NAMES__;
  const sweep = () => {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      const t = (n.nodeValue || '').trim();
      if (!t) continue;
      const e = n.parentElement;
      if (!e || e.closest('script,style')) continue;
      const hit = (CODE.test(t) && !/20[0-9]{2}[-\/年]|[0-9]{4}-[0-9]{2}|\d{1,2}:\d{2}/.test(t)) || NAMES.some(s => t.includes(s));
      if (hit) e.classList.add('__blur');
    }
  };
  const go = () => { document.head.appendChild(st); sweep(); new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true, characterData: true }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def company_names() -> list[str]:
    """site/data/stocks.json 裡全部個股名稱（build_payload 產出），出現在畫面上就模糊。"""
    p = SITE / "data" / "stocks.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return sorted({r["name"] for r in d if isinstance(r, dict) and isinstance(r.get("name"), str) and len(r["name"]) >= 2})


def serve():
    h = partial(_Quiet, directory=str(SITE))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def page(pw, blur=True):
    exe = "/opt/pw-browsers/chromium"
    br = pw.chromium.launch(executable_path=exe) if Path(exe).exists() else pw.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True,
                         locale="zh-TW", timezone_id="Asia/Taipei")
    ctx.add_init_script(PRESET)
    if blur:
        ctx.add_init_script(BLUR_JS.replace("__NAMES__", json.dumps(company_names(), ensure_ascii=False)))
    return br, ctx.new_page()


SHOTS = {
    # id: (hash, 捲動起點 px, 捲動終點 px, 秒數)
    "theme": ("#heatmap/theme/cowos", 240, 800, 7.0),
}


def probe(pw, base):
    OUT.mkdir(parents=True, exist_ok=True)
    br, pg = page(pw)
    for sid, (h, *_r) in SHOTS.items():
        pg.goto(base + h)
        pg.wait_for_timeout(4000)
        pg.screenshot(path=str(OUT / f"probe_{sid}.png"), full_page=True)
        print(sid, pg.evaluate("document.documentElement.scrollHeight"))
    br.close()


def record(pw, base, only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    br, pg = page(pw)
    for sid, (h, y0, y1, dur) in SHOTS.items():
        if only and sid not in only:
            continue
        pg.goto(base + h)
        pg.wait_for_timeout(4500)
        d = OUT / sid
        d.mkdir(exist_ok=True)
        n = int(round(dur * FPS))
        pg.evaluate(f"window.scrollTo(0, {y0})")      # 先捲到起點、等版面穩定再開錄（不然第一格會是頁首）
        pg.wait_for_timeout(1200)
        for i in range(n):
            u = i / max(1, n - 1)
            e = u * u * (3 - 2 * u)
            pg.evaluate(f"window.scrollTo(0, {y0 + (y1 - y0) * e:.2f})")
            pg.wait_for_timeout(15)
            pg.screenshot(path=str(d / f"{i:04d}.png"), animations="disabled", caret="hide")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(d / "%04d.png"),
                        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(OUT / f"{sid}.mp4")], check=True)
        print(sid, n, "格")
    br.close()
    meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    (OUT / "meta.json").write_text(json.dumps({"data_date": meta.get("data_date"), "crop": {"theme": 190}}), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    srv = serve()
    base = f"http://127.0.0.1:{PORT}/index.html"
    with sync_playwright() as pw:
        if a.probe:
            probe(pw, base)
        else:
            record(pw, base, set(filter(None, a.only.split(","))))
    srv.shutdown()


if __name__ == "__main__":
    main()
