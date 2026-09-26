"""展示用截圖：改完之後先給 Andy 看，不推上去。

為什麼有這支（Andy 2026-09-21）
--------------------------------
> 「我想要把效率的問題處理，我覺得跑東西太久，每次修改都要全部重新測試太花時間…
>   你改完之後可以先不用推上去，先在 Claude 這邊展示給我，
>   並且還沒驗證的部分先記錄下來…之後我說驗證，再全部一起執行。
>   初步功能我先人為測試，我確認後你再看細項」

以前的流程是「改完 → 跑關卡 → 推 → 等部署 → 他打開網頁看 → 不對 → 再來一輪」，
一輪至少 15 分鐘，而且**大部分的來回其實是在確認「長得對不對」**，
那根本不需要關卡、也不需要部署。

這支就是把那一段抽出來：起本機伺服器、用真的圖表庫畫出來、截圖，
Claude 直接把圖片傳給他看。**秒級，不跑關卡、不推、不部署。**

用法
----
    python scripts/_show.py --view flow                     # 單一頁
    python scripts/_show.py --view flow --width 1440,390    # 多寬度
    python scripts/_show.py --view industry/semiconductor --sel "#chainMap"
    python scripts/_show.py --view flow --click "#rotZoomBtn" --wait 1200
    python scripts/_show.py --view overview --zoom 3 --clip 0,0,700,500

輸出在 `docs/_show/`（gitignore），每次跑會先清空。
"""
from __future__ import annotations

import argparse
import os
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ★ 2026-09-26 覆蓋普查：要拍「修改前」的對照圖，得能指向另一份網站快照（例如舊版 commit 的 site/）；
#   輸出資料夾也要能分開，不然拍「修改後」時會把「修改前」清掉。兩個都沒設就跟以前一樣。
SITE = Path(os.environ.get("TW_SHOW_SITE") or (ROOT / "site"))
OUT = Path(os.environ.get("TW_SHOW_OUT") or (ROOT / "docs" / "_show"))
PORT = int(os.environ.get("TW_SHOW_PORT", "8767"))


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass



# ★ 2026-09-24 設計系統 v2 第 6 批（site/legal.js）：同意條款橫幅。
#   橫幅一旦啟用（site/legal_config.js 填完＋enabled:true），會固定在畫面最下方約 130～160px，
#   **擋住所有點畫面下緣的驗收步驟** —— 腳本沒改先上線，所有關卡會一起紅（docs/design_system_v2.md 4.1 最後一段）。
#   所以在這裡把 Playwright 的 Browser.new_page／new_context 包一層：每一個新開的頁面，
#   在頁面腳本執行前都先寫好 tw.consent（v:'*'＝這個瀏覽器不必再看橫幅）與 tw.tour。
#   · 只在「還沒有值」時才寫：有些段落會 localStorage.clear() 再重新整理，init script 會在下一次載入補回來。
#   · 包在類別上而不是某一個 page：驗收裡有幾十個地方各自 new_page，逐一加一定會漏。
#   · 「同意條款」那一段要刻意不寫，改用 Browser._tw_raw_new_context（原本那支）開乾淨的頁面。
CONSENT_PRESET = ("try{if(!localStorage.getItem('tw.consent'))localStorage.setItem('tw.consent',"
                  "JSON.stringify({v:'*',at:'test'}));"
                  "if(!localStorage.getItem('tw.tour'))localStorage.setItem('tw.tour','*');}catch(e){}")


def _preset_consent() -> None:
    from playwright.sync_api import Browser
    if getattr(Browser, "_tw_consent", False):
        return
    raw_page, raw_ctx = Browser.new_page, Browser.new_context

    def new_page(self, *a, **k):
        pg = raw_page(self, *a, **k)
        pg.add_init_script(CONSENT_PRESET)
        return pg

    def new_context(self, *a, **k):
        c = raw_ctx(self, *a, **k)
        c.add_init_script(CONSENT_PRESET)
        return c

    Browser._tw_raw_new_page, Browser._tw_raw_new_context = raw_page, raw_ctx
    Browser.new_page, Browser.new_context = new_page, new_context
    Browser._tw_consent = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default="overview", help="hash 路由，例如 flow、industry/semiconductor、stock/2330")
    ap.add_argument("--width", default="1440", help="逗號分隔的寬度，例如 1440,1024,390")
    ap.add_argument("--height", type=int, default=950)
    ap.add_argument("--sel", default="", help="只截這個選擇器（預設截整個可視範圍）")
    ap.add_argument("--clip", default="", help="x,y,w,h —— 只截這塊，和 --sel 二選一")
    ap.add_argument("--click", default="", help="截圖前先點這些選擇器（逗號分隔，依序點）")
    ap.add_argument("--wait", type=int, default=2500, help="進頁面之後等幾毫秒（圖表要時間畫）")
    ap.add_argument("--zoom", type=float, default=1, help="裝置縮放；要看細節就開 2~3")
    ap.add_argument("--full", action="store_true", help="整頁截圖（版面問題用這個）")
    ap.add_argument("--tag", default="", help="檔名前綴，方便一次比較好幾版")
    ap.add_argument("--expand-folds", action="store_true",
                    help="截圖前把剖析圖所有收合段落展開（覆蓋普查的前後對照要看展開後的段落）")
    ap.add_argument("--ls", default="",
                    help="進頁面前先寫好的 localStorage，逗號分隔的 key=value，"
                         "例如 tw.side=0,tw.theme=light。"
                         "★ 2026-09-21 加的：以前截圖沒辦法指定狀態，"
                         "所以 MLCC 那批的 800／390 截圖是在「今日事件抽屜開著、蓋住右半邊」的狀態下拍的，"
                         "等於那兩個寬度根本沒驗到。")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    _preset_consent()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}/index.html"

    made: list[str] = []
    errs: list[str] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for w in [int(x) for x in args.width.split(",") if x.strip()]:
                pg = b.new_page(viewport={"width": w, "height": args.height},
                                device_scale_factor=args.zoom)
                for kv in [s.strip() for s in args.ls.split(",") if s.strip()]:
                    k, _, v = kv.partition("=")
                    pg.add_init_script(
                        f"try{{localStorage.setItem({k.strip()!r},{v.strip()!r});}}catch(e){{}}")
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(f"{base}#{args.view.lstrip('#')}", wait_until="networkidle")
                pg.wait_for_timeout(args.wait)
                for sel in [s.strip() for s in args.click.split(",") if s.strip()]:
                    try:
                        pg.click(sel, timeout=5000)
                        pg.wait_for_timeout(900)
                    except Exception as exc:  # noqa: BLE001
                        errs.append(f"點不到 {sel}：{str(exc)[:80]}")
                if args.expand_folds:
                    pg.evaluate("() => document.querySelectorAll('#prodDiagram g.dgfold[data-fold], #themeDiagram g.dgfold[data-fold]')"
                                ".forEach(g => g.dispatchEvent(new MouseEvent('click', { bubbles: true })))")
                    pg.wait_for_timeout(900)
                name = f"{args.tag + '-' if args.tag else ''}{args.view.replace('/', '_')}-{w}.png"
                path = OUT / name
                if args.sel:
                    el = pg.query_selector(args.sel)
                    if not el:
                        errs.append(f"找不到 {args.sel}")
                        pg.close()
                        continue
                    el.screenshot(path=str(path))
                elif args.clip:
                    x, y, cw, chh = [float(v) for v in args.clip.split(",")]
                    pg.screenshot(path=str(path), clip={"x": x, "y": y, "width": cw, "height": chh})
                else:
                    pg.screenshot(path=str(path), full_page=args.full)
                made.append(str(path))
                pg.close()
            b.close()
    finally:
        srv.shutdown()

    for m in made:
        print(m)
    if errs:
        print("\n⚠ 過程中的問題：")
        for e in errs[:8]:
            print("  ·", e)
    # ★ 這支**不是關卡**。它只證明「長這樣」，不證明「對」。
    print("\n※ 這是展示用截圖，沒有跑任何驗收。還沒驗的項目記在 obsidian/unverified.yaml。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
