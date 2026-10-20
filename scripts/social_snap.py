"""盤中／盤後社群貼文用的即時截圖＋排版＋manifest（Threads、IG 限動）。

Andy 2026-10-20：「我需要在盤中發布當下即時狀況在 Threads 上和 IG 限動：資金輪盤、分流樹即時截圖
（包含旁邊的長條圖）；熱力圖都需要具備即時功能、也是截圖發布的內容；盤後提供當天即時的法人買賣超狀況；
排版只需要提供當前狀況，大家需要看。」

流程
----
1. Playwright 開網站（預設正式站；--base 可換本機），亮色主題、桌機寬 1440，切到「即時」，等即時資料套上，截卡片。
2. 把每張截圖排成兩種版型（用瀏覽器渲染，才有真正的中文字型）：
   · IG 限動 1080×1920：上方標題、中間整張截圖（等比、不裁）、下方資料來源＋網址。一張截圖一張限動。
   · Threads：1080 寬，同樣標題列與底部一行；貼文文字 2～4 行（時間、重點一句、免責、網址）。
3. 排版後用程式量每個元素的框，兩兩不得相交（layout_report.json），有重疊就非 0 結束。
4. 寫 manifest.json 給 scripts/social_publish.py。

用法
----
    python scripts/social_snap.py --kind intraday --out snaps/20261020-0935
    python scripts/social_snap.py --kind close    --out snaps/20261020-close
    python scripts/social_snap.py --kind intraday --base http://127.0.0.1:8791/index.html --serve site --mock-live --out /tmp/demo

結束碼：0＝有產出；10＝今天不是交易日／不在盤中時段／法人資料還不是今天，刻意不發（不算失敗）；
        2＝一張都沒截成；3＝版面有重疊（不准發）。

誠實規則
--------
· 「即時」沒套上（抓不到報價、狀態字寫抓不到）的那張，**不發**（寧可少發，不拿盤後舊圖冒充即時）。
· 非交易日看**資料**判斷，不看執行當下的星期幾：盤中看即時報價回應裡的成交日 d；盤後看 meta.json 的 inst_date。
· 重點句一律從頁面上讀、原文照抄，不自己推論。

目標清單與切換
--------------
frontend-ui 會在各卡片加 data-snap 屬性與 window.TwSnapReady(name)（名稱見 docs/social_snap_targets.md）。
還沒上線前用 TARGETS 裡的現有選擇器；頁面上若出現 [data-snap="<name>"] 就改用它，TwSnapReady 存在就等它回 true。
--use-snap-attr 可強制只用新屬性；--no-snap-attr 強制只用舊選擇器。
"""
from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://liguligu-puipui.com"
SITE_HOST = "liguligu-puipui.com"
TPE = timezone(timedelta(hours=8))
DISCLAIMER = "資料：證交所／櫃買公開資料，僅供參考，不構成投資建議"
CHROMIUM = os.environ.get("TW_CHROMIUM") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None)

# ---------------------------------------------------------------------------- 目標清單
# name：給 data-snap／TwSnapReady 用的名稱（跟 docs/social_snap_targets.md 對齊；還沒對齊的以這裡為準，改一處就好）
# route：hash 路由；card：要截的元素（closest_card=True 表示往上找最近的 .card，才會帶到標題）
# live：「即時」鈕的選擇器（None＝沒有鈕，頁面本身就是當下資料）；live_ok：判斷即時真的套上的 JS（回 true／false）
TARGETS = [
    dict(name="rotation", kind="intraday", label="資金輪盤＋族群資金排行", route="flow/rotation",
         card="#flowRotCard", live="#rotLiveBtn",
         live_ok="() => { const b = document.querySelector('#rotLiveBtn'); const t = document.querySelector('#rotLiveTag');"
                 " return !!b && b.getAttribute('aria-pressed') === 'true' && !!t && !t.hidden && !/抓取中|抓不到|失敗|逾時|連不到/.test(t.innerText); }",
         headline=r"資金[占佔]比\s*增加最多\s*[：:][^\n]*"),
    dict(name="sankey", kind="intraday", label="資金分流樹＋資金流向排名", route="flow/sankey",
         card="#flowSankeyCard", live="#sankeyLiveBtn",
         live_ok="() => { const b = document.querySelector('#sankeyLiveBtn');"
                 " return !!b && (b.getAttribute('aria-pressed') === 'true' || b.classList.contains('on')) && !/抓取中|抓不到|失敗|逾時|連不到/.test((document.querySelector('#sankeyLive') || {}).innerText || ''); }",
         headline=r"資金[占佔]比\s*增加最多\s*[：:][^\n]*"),
    dict(name="heat-industry", kind="intraday", label="產業熱力圖", route="heatmap/industry",
         card="#indTreeWrap", closest_card=True, live="auto", live_ok=None, headline=None),
    dict(name="heat-theme", kind="intraday", label="題材熱力圖", route="heatmap/theme",
         card="#themeMapCard", live="auto", live_ok=None, headline=None),
    # 盤後
    dict(name="streak-trust", kind="close", label="法人連續買賣超｜投信", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="trust"),
    dict(name="streak-foreign", kind="close", label="法人連續買賣超｜外資", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="foreign"),
    dict(name="streak-total", kind="close", label="法人連續買賣超｜合計", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="total"),
    dict(name="inst-groups", kind="close", label="族群×三大法人買賣超", route="flow/inst",
         card="#flowInstCard", live=None, live_ok=None, headline=None),
]

WHO_LABEL = {"trust": "投信", "foreign": "外資", "total": "合計"}

# 截圖前把所有「固定定位」的浮動元素（客服比比、同意橫幅、導覽、通知小視窗…）藏起來，不在目標卡片裡的才藏。
HIDE_FLOATING_JS = """(sel) => {
  const tgt = document.querySelector(sel);
  let n = 0;
  document.querySelectorAll('body *').forEach(e => {
    const cs = getComputedStyle(e);
    if ((cs.position === 'fixed' || cs.position === 'sticky') && !(tgt && (tgt.contains(e) || e.contains(tgt)))) {
      e.style.setProperty('visibility', 'hidden', 'important'); n++;
    }
  });
  document.querySelectorAll('.supfab,#supFab,.consent,#consentBar,.tourpop,.toast,.bibi').forEach(e => {
    if (!(tgt && tgt.contains(e))) e.style.setProperty('visibility', 'hidden', 'important');
  });
  return n;
}"""


# ---------------------------------------------------------------------------- 小工具
def now_tpe() -> datetime:
    return datetime.now(TPE)


def log(*a) -> None:
    print("[social_snap]", *a, flush=True)


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def serve_dir(directory: Path, port: int) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", port), functools.partial(_Quiet, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def fetch_meta(base: str) -> dict:
    """讀網站的 data/meta.json（資料日期、法人資料日期）。"""
    root = base.rsplit("/", 1)[0] if base.endswith(".html") else base.rstrip("/")
    try:
        with urlopen(f"{root}/data/meta.json?_={int(time.time())}", timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log("讀不到 meta.json：", exc)
        return {}


def mock_quote_handler(today_ymd: str, now_hms: str):
    """本機模擬即時報價（只給 --mock-live 用）：每檔以代號雜湊出 ±3% 內的漲跌，成交日＝今天。"""
    def handler(route):
        q = parse_qs(urlparse(route.request.url).query)
        out = []
        for tok in [x for x in (q.get("ex_ch") or [""])[0].split("|") if x]:
            try:
                code = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            h = int(hashlib.md5(code.encode()).hexdigest()[:6], 16)
            r = ((h % 1000) / 1000 - 0.5) * 0.06
            y = 100.0
            out.append({"c": code, "n": "模擬" + code, "ex": tok[:3], "z": f"{y * (1 + r):.4f}", "y": f"{y:.4f}",
                        "o": f"{y:.4f}", "h": f"{y * 1.03:.4f}", "l": f"{y * 0.97:.4f}",
                        "v": str(1000 + h % 9000), "tv": str(500 + h % 5000), "t": now_hms, "d": today_ymd})
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=json.dumps({"rtcode": "0000", "rtmessage": "OK", "msgArray": out}))
    return handler


# ---------------------------------------------------------------------------- 截圖
def open_page(browser, base: str, args, today_ymd: str, sniff: dict):
    ctx = browser.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=args.scale,
                              locale="zh-TW", timezone_id="Asia/Taipei")
    # 亮色主題＋同意橫幅／導覽先設定好；TW_THEME_LEGACY 讓 tw.theme 永久生效（不跟時鐘自動切）
    init = ("window.TW_THEME_LEGACY=1;try{localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'snap'}));"
            "localStorage.setItem('tw.tour','*');localStorage.setItem('tw.theme','light');}catch(e){}")
    if args.live_override:
        init += "window.TW_LIVE_OVERRIDE=true;"          # 只有 127.0.0.1／localhost 認
    tok = os.environ.get("SNAP_ACCT_TOKEN", "")
    user = os.environ.get("SNAP_ACCT_USER_JSON", "")
    if tok:   # 正式站即時是管理者功能：用管理者登入快取（Secrets 注入，不進 repo）
        init += (f"try{{localStorage.setItem('tw.acct.tok',{json.dumps(tok)});"
                 f"localStorage.setItem('tw.acct.user',{json.dumps(user or json.dumps({'owner': True, 'admin': True}))});}}catch(e){{}}")
    ctx.add_init_script(init)
    pg = ctx.new_page()
    if args.mock_live:
        pg.route("**/quote?*", mock_quote_handler(today_ymd, now_tpe().strftime("%H:%M:%S")))
        pg.route("**/stream?*", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
        ctx.add_init_script("try{localStorage.setItem('tw.live.proxy','https://mock-quote.test');}catch(e){}")

    def on_resp(resp):
        try:
            if "/quote" in resp.url and resp.status == 200:
                j = resp.json()
                for m in (j.get("msgArray") or [])[:3]:
                    if m.get("d"):
                        sniff["quote_dates"].add(str(m["d"]))
        except Exception:  # noqa: BLE001
            pass
    pg.on("response", on_resp)
    pg.on("pageerror", lambda e: sniff["errors"].append(str(e)[:120]))
    return ctx, pg


def resolve_target(pg, t: dict, use_attr: str):
    """回傳要截的元素 handle（優先 data-snap，其次舊選擇器）。"""
    el = None
    if use_attr != "never":
        el = pg.query_selector(f'[data-snap="{t["name"]}"]')
    if el is None and use_attr == "only":
        return None
    if el is None:
        el = pg.query_selector(t["card"])
        if el is not None and t.get("closest_card"):
            up = el.evaluate_handle("e => e.closest('.card') || e")
            el = up.as_element() or el
    return el


def go_target(pg, base: str, t: dict) -> None:
    pg.goto(f"{base}#{t['route']}", wait_until="networkidle")
    pg.wait_for_timeout(2500)


def wait_snap_ready(pg, name: str, timeout_ms: int) -> bool:
    """若頁面有 window.TwSnapReady（frontend-ui 提供），等它回 true；沒有就當作 true。"""
    has = pg.evaluate("() => typeof window.TwSnapReady === 'function'")
    if not has:
        return True
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        try:
            ok = pg.evaluate("(n) => Promise.resolve(window.TwSnapReady(n)).then(v => !!v)", name)
        except Exception:  # noqa: BLE001
            ok = False
        if ok:
            return True
        pg.wait_for_timeout(700)
    return False


def click_live(pg, t: dict, el) -> bool:
    """切到即時。回傳有沒有按到鈕（沒有鈕＝這張不用切）。"""
    sel = t.get("live")
    if not sel:
        return False
    if sel == "auto":
        # frontend-ui 還沒把熱力圖改即時前：在卡片內找文字含「即時」的按鈕；找不到＝這張沒有即時（會被判定為非即時而跳過）
        h = el.evaluate_handle("e => [...e.querySelectorAll('button')].find(b => /即時/.test(b.innerText)) || null")
        b = h.as_element()
        if not b:
            return False
        if (b.get_attribute("aria-pressed") or "") != "true":
            b.click()
        return True
    b = pg.query_selector(sel)
    if not b:
        return False
    if (b.get_attribute("aria-pressed") or "") != "true":
        b.click()
    pg.wait_for_timeout(1500)      # 讓「抓取中」狀態先出現，免得一開始就誤判成已套上
    return True


def live_confirmed(pg, t: dict, args) -> bool:
    deadline = time.time() + args.live_wait
    pred = t.get("live_ok")
    while time.time() < deadline:
        try:
            if pred:
                if pg.evaluate(pred):
                    return True
            else:   # 沒有專屬判斷（熱力圖）：看 data-snap 卡片的 data-live 狀態，或卡片內「即時」鈕亮著
                ok = pg.evaluate("""(n) => {
                    const c = document.querySelector('[data-snap="' + n + '"]');
                    if (c && c.getAttribute('data-snap-live') === '1') return true;
                    const b = c && [...c.querySelectorAll('button')].find(x => /即時/.test(x.innerText));
                    return !!b && b.getAttribute('aria-pressed') === 'true' && !/抓不到|失敗|逾時/.test(c.innerText);
                }""", t["name"])
                if ok:
                    return True
        except Exception:  # noqa: BLE001
            pass
        pg.wait_for_timeout(1000)
    return False


def read_headline(pg, el, t: dict) -> str:
    rx = t.get("headline")
    if not rx:
        return ""
    txt = el.inner_text()
    m = re.search(rx, txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""


def read_streak(pg, who: str) -> dict:
    """讀連續買超前三（頁面上顯示的名稱與天數，原文照抄）與上方摘要。"""
    return pg.evaluate("""() => {
        const sub = (document.querySelector('#streakSub') || {}).innerText || '';
        const rows = [...document.querySelectorAll('#mktBody .card, #mktBody table, #mktBody [class*=strk]')];
        const buy = [];
        const cardEl = [...document.querySelectorAll('#mktBody *')].find(e => /^連續買超/.test((e.innerText || '').trim()) && e.children.length < 4);
        const box = cardEl ? cardEl.parentElement : null;
        if (box) {
          const lines = box.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
          for (let i = 0; i < lines.length && buy.length < 3; i++) {
            const m = lines[i + 2] && /^(\\d+)\\s*天$/.exec(lines[i + 2]);
            if (/^[^\\d\\s]/.test(lines[i]) && /^\\d{4,6}$/.test(lines[i + 1] || '') && m) { buy.push(lines[i] + ' ' + m[1] + ' 天'); i += 2; }
          }
        }
        return { sub: sub.replace(/\\s+/g, ' ').trim(), buy };
    }""")


def snap_targets(args, base: str, out: Path, today_ymd: str) -> tuple[list[dict], dict]:
    from playwright.sync_api import sync_playwright
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []
    sniff = {"quote_dates": set(), "errors": []}
    wanted = [t for t in TARGETS if t["kind"] == args.kind and (not args.only or t["name"] in args.only.split(","))]
    attr_mode = "only" if args.use_snap_attr else ("never" if args.no_snap_attr else "prefer")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
        ctx, pg = open_page(browser, base, args, today_ymd, sniff)
        for t in wanted:
            info = {"name": t["name"], "label": t["label"], "ok": False, "why": ""}
            try:
                go_target(pg, base, t)
                el = resolve_target(pg, t, attr_mode)
                if el is None:
                    info["why"] = "找不到目標元素"
                    shots.append(info)
                    continue
                if t.get("streak_who"):
                    pg.click(f'#streakWho button[data-w="{t["streak_who"]}"]')
                    pg.wait_for_timeout(1200)
                    st = read_streak(pg, t["streak_who"])
                    info["streak"] = st
                if args.kind == "intraday":
                    pressed = click_live(pg, t, el)
                    if not pressed:
                        info["why"] = "沒有即時鈕（這張還不能即時）→ 不發"
                        shots.append(info)
                        continue
                    if not live_confirmed(pg, t, args):
                        info["why"] = "即時沒套上（抓不到報價）→ 不發"
                        shots.append(info)
                        continue
                if not wait_snap_ready(pg, t["name"], 20000):
                    info["why"] = "TwSnapReady 逾時 → 不發"
                    shots.append(info)
                    continue
                pg.wait_for_timeout(1500)
                pg.evaluate(HIDE_FLOATING_JS, t["card"])
                pg.wait_for_timeout(300)
                el = resolve_target(pg, t, attr_mode) or el
                el.scroll_into_view_if_needed()
                path = raw_dir / f"{t['name']}.png"
                el.screenshot(path=str(path))
                info.update(ok=True, raw=str(path), headline=read_headline(pg, el, t))
                box = el.bounding_box()
                info["w"], info["h"] = round(box["width"]), round(box["height"])
                log("截到", t["name"], info["w"], "x", info["h"])
            except Exception as exc:  # noqa: BLE001
                info["why"] = f"例外：{str(exc)[:100]}"
            shots.append(info)
        ctx.close()
        browser.close()
    return shots, sniff


# ---------------------------------------------------------------------------- 排版
def b64(path: str) -> str:
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;background:#f4f7fb;font-family:'Noto Sans CJK TC','Noto Sans TC','PingFang TC','Microsoft JhengHei','WenQuanYi Zen Hei',sans-serif;color:#17233a}
.title{font-weight:700;font-size:44px;line-height:1.3;white-space:nowrap}
.foot{font-size:24px;line-height:1.4;color:#4a5a73;white-space:nowrap}
.url{font-size:28px;font-weight:700;color:#0b5fa5;white-space:nowrap}
.shot{display:block;border-radius:14px;box-shadow:0 2px 10px rgba(20,40,80,.18);background:#fff}
"""


def story_html(title: str, img: str, iw: int, ih: int) -> tuple[str, int, int]:
    """IG 限動 1080×1920。上下各留約 250px 安全區（IG 介面會蓋）。"""
    W, H = 1080, 1920
    top, bot = 250, 250
    box_w = 1000
    title_h, gap = 60, 40
    foot_h = 110
    box_h = H - top - bot - title_h - gap - foot_h - 40
    sc = min(box_w / iw, box_h / ih)
    dw, dh = round(iw * sc), round(ih * sc)
    avail = H - top - bot - foot_h
    y_title = top + (avail - (title_h + gap + dh)) // 2
    y_img = y_title + title_h + gap
    html = f"""<html><head><meta charset=utf-8><style>{BASE_CSS}
body{{height:{H}px;position:relative}}
.title{{position:absolute;left:40px;top:{y_title}px;width:1000px;text-align:center}}
.shot{{position:absolute;left:{(W - dw) // 2}px;top:{y_img}px;width:{dw}px;height:{dh}px}}
.foot{{position:absolute;left:40px;top:{H - bot - foot_h}px;width:1000px;text-align:center;font-size:22px}}
.url{{position:absolute;left:40px;top:{H - bot - foot_h + 50}px;width:1000px;text-align:center}}
</style></head><body>
<div class=title data-box=title>{title}</div>
<img class=shot data-box=shot src="{img}">
<div class=foot data-box=foot>{DISCLAIMER}</div>
<div class=url data-box=url>{SITE_HOST}</div>
</body></html>"""
    return html, W, H


def threads_html(title: str, img: str, iw: int, ih: int) -> tuple[str, int, int]:
    """Threads 寬圖：1080 寬，標題列＋整張截圖（左右各留 24）＋頁尾一行。"""
    W = 1080
    dw = W - 48
    dh = round(ih * dw / iw)
    head, gap, foot = 110, 20, 96
    H = head + dh + gap + foot
    html = f"""<html><head><meta charset=utf-8><style>{BASE_CSS}
body{{height:{H}px;position:relative}}
.title{{position:absolute;left:24px;top:28px;width:1032px;font-size:40px}}
.shot{{position:absolute;left:24px;top:{head}px;width:{dw}px;height:{dh}px}}
.foot{{position:absolute;left:24px;top:{head + dh + gap + 4}px;width:760px;font-size:21px}}
.url{{position:absolute;left:792px;top:{head + dh + gap}px;width:264px;text-align:right;font-size:24px}}
</style></head><body>
<div class=title data-box=title>{title}</div>
<img class=shot data-box=shot src="{img}">
<div class=foot data-box=foot>{DISCLAIMER}</div>
<div class=url data-box=url>{SITE_HOST}</div>
</body></html>"""
    return html, W, H


OVERLAP_JS = """() => {
  const els = [...document.querySelectorAll('[data-box]')];
  const R = els.map(e => { const r = e.getBoundingClientRect(); return { n: e.dataset.box, x: r.x, y: r.y, w: r.width, h: r.height, ov: e.scrollWidth > e.clientWidth + 1 && e.tagName !== 'IMG' }; });
  // 文字的實際寬度（white-space:nowrap 下用 Range 量）
  els.forEach((e, i) => { if (e.tagName !== 'IMG') { const rg = document.createRange(); rg.selectNodeContents(e); const b = rg.getBoundingClientRect(); R[i].tx = b.x; R[i].tw = b.width; R[i].ty = b.y; R[i].th = b.height; } });
  const hits = [];
  const box = r => r.tw !== undefined ? { x: r.tx, y: r.ty, w: r.tw, h: r.th } : r;
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) {
    const a = box(R[i]), b = box(R[j]);
    if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) hits.push(R[i].n + '×' + R[j].n);
  }
  const W = document.documentElement.clientWidth, H = document.body.scrollHeight;
  const out = R.filter(r => { const b = box(r); return b.x < -0.5 || b.y < -0.5 || b.x + b.w > W + 0.5 || b.y + b.h > H + 0.5; }).map(r => r.n);
  const cut = R.filter(r => r.ov).map(r => r.n);
  return { hits, out, cut, n: R.length };
}"""


def compose(browser, kind_name: str, title: str, raw: str, iw: int, ih: int, out_png: Path, report: list) -> None:
    img = b64(raw)
    html, W, H = (story_html if kind_name == "story" else threads_html)(title, img, iw, ih)
    pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.set_content(html, wait_until="load")
    pg.wait_for_timeout(300)
    res = pg.evaluate(OVERLAP_JS)
    res.update(file=out_png.name, w=W, h=H)
    report.append(res)
    pg.screenshot(path=str(out_png), full_page=False)
    pg.close()


def img_size(path: str) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.size


# ---------------------------------------------------------------------------- 貼文文字
def build_text(kind: str, stamp: str, shots: list[dict], data_date: str) -> str:
    ok = [s for s in shots if s.get("ok")]
    if kind == "intraday":
        head = next((s["headline"] for s in ok if s.get("headline")), "")
        l1 = f"盤中即時 {stamp}｜台股資金輪動"
        l2 = head or "資金輪盤、資金分流樹與熱力圖即時狀況如圖"
    else:
        l1 = f"盤後法人 {data_date[5:].replace('-', '/')}｜投信、外資、合計連續買賣超"
        parts = []
        for who in ("trust", "foreign"):
            s = next((x for x in ok if x["name"] == f"streak-{who}"), None)
            buy = (s or {}).get("streak", {}).get("buy") or []
            if buy:
                parts.append(f"{WHO_LABEL[who]}連買 " + "、".join(buy))
        l2 = "｜".join(parts) or "投信、外資、合計連續買賣超如圖"
    return "\n".join([l1, l2, "資料來自證交所／櫃買公開資料，僅供參考，不構成投資建議。", SITE_URL])


# ---------------------------------------------------------------------------- 主程式
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=["intraday", "close"], required=True)
    ap.add_argument("--out", required=True, help="輸出資料夾（manifest.json 與圖片都放這裡）")
    ap.add_argument("--base", default=SITE_URL + "/index.html", help="網站網址（本機例如 http://127.0.0.1:8791/index.html）")
    ap.add_argument("--serve", default="", help="給路徑就在本機起靜態伺服器（site 資料夾），--base 自動設成它")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--scale", type=float, default=2.0, help="截圖解析度倍率")
    ap.add_argument("--only", default="", help="只做這幾個目標（逗號分隔 name）")
    ap.add_argument("--live-wait", type=int, default=30, help="等即時套上的秒數")
    ap.add_argument("--mock-live", action="store_true", help="模擬報價（本機示範用；正式站不要加）")
    ap.add_argument("--live-override", action="store_true", help="本機 TW_LIVE_OVERRIDE（只有 127.0.0.1 認）")
    ap.add_argument("--use-snap-attr", action="store_true", help="只用 data-snap 屬性找目標")
    ap.add_argument("--no-snap-attr", action="store_true", help="不用 data-snap，只用現有選擇器")
    ap.add_argument("--force", action="store_true", help="略過「盤中時段／今天是不是交易日／法人資料是不是今天」的檢查（示範用）")
    ap.add_argument("--today", default="", help="覆寫「今天」（YYYY-MM-DD，示範／測試用）")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    today = args.today or now_tpe().strftime("%Y-%m-%d")
    today_ymd = today.replace("-", "")
    stamp_now = now_tpe().strftime("%H:%M")

    srv = None
    base = args.base
    if args.serve:
        srv = serve_dir(Path(args.serve).resolve(), args.port)
        base = f"http://127.0.0.1:{args.port}/index.html"
        args.live_override = True
    try:
        meta = fetch_meta(base)
        data_date = meta.get("inst_date") or meta.get("data_date") or today
        if args.kind == "close" and not args.force:
            if data_date != today:
                log(f"盤後法人資料日 {data_date} ≠ 今天 {today}（非交易日或法人資料還沒更新）→ 不發")
                return 10
        if args.kind == "intraday" and not args.force:
            hhmm = now_tpe().strftime("%H:%M")
            if not ("09:00" <= hhmm <= "13:35"):
                log(f"現在台北 {hhmm} 不在盤中時段（09:00～13:35；排程被 GitHub 延遲到收盤後會走這裡）→ 不發")
                return 10
        shots, sniff = snap_targets(args, base, out, today_ymd)
        if args.kind == "intraday" and not args.force:
            qd = sniff["quote_dates"]
            if qd and today_ymd not in qd:
                log(f"即時報價的成交日 {sorted(qd)} 不是今天 {today_ymd}（休市日）→ 不發")
                return 10
        ok = [s for s in shots if s.get("ok")]
        for s in shots:
            if not s.get("ok"):
                log("略過", s["name"], "：", s.get("why"))
        if not ok:
            log("一張都沒截成")
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 2

        title = (f"哩股哩股｜盤中即時 {stamp_now}" if args.kind == "intraday"
                 else f"哩股哩股｜盤後法人 {data_date[5:].replace('-', '/')}")
        report: list[dict] = []
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
            for s in ok:
                iw, ih = img_size(s["raw"])
                compose(browser, "story", title, s["raw"], iw, ih, out / f"story_{s['name']}.png", report)
                compose(browser, "threads", title, s["raw"], iw, ih, out / f"threads_{s['name']}.png", report)
            browser.close()
        bad = [r for r in report if r["hits"] or r["out"] or r["cut"]]
        (out / "layout_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
        (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
        log(f"重疊檢查：程式 {len(report)} 張版面（{sum(r['n'] for r in report)} 個框）{len(bad)} 張有問題")
        if bad:
            for r in bad:
                log("  ✗", r["file"], r["hits"], r["out"], r["cut"])
            return 3

        manifest = {
            "kind": args.kind,
            "taken_at": now_tpe().isoformat(timespec="seconds"),
            "data_date": data_date,
            "threads": {"text": build_text(args.kind, stamp_now, ok, data_date),
                        "images": [f"threads_{s['name']}.png" for s in ok]},
            "story": [f"story_{s['name']}.png" for s in ok],
        }
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
        log("manifest：", out / "manifest.json")
        return 0
    finally:
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
