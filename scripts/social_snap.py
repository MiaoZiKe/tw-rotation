"""盤中／盤後社群貼文用的即時截圖＋排版＋manifest（Threads、IG 限動）。

Andy 2026-10-20：「我需要在盤中發布當下即時狀況在 Threads 上和 IG 限動：資金輪盤、分流樹即時截圖
（包含旁邊的長條圖）；熱力圖都需要具備即時功能、也是截圖發布的內容；盤後提供當天即時的法人買賣超狀況；
排版只需要提供當前狀況，大家需要看。」

流程
----
1. Playwright 開網站（預設正式站；--base 可換本機），亮色主題、桌機寬 1440，切到「即時」，等即時資料套上，截卡片。
2. 把每張截圖排成兩種版型（用瀏覽器渲染，才有真正的中文字型）：
   · IG 限動 1080×1920：改截「手機版面」（viewport 390、輸出 1080 寬），截圖區撐滿畫面（≥75% 高）。
     太長的卡拆成兩張（資金輪盤＝「輪盤」＋「族群資金排行長條圖」；分流樹＝「樹」＋「排名前 10」）。
   · Threads（桌機寬 1440 的截圖）：1080 寬，同樣標題列與底部一行；貼文文字 2～4 行（時間、重點一句、免責、網址）。
3. 排版後用程式量每個元素的框，兩兩不得相交（layout_report.json），有重疊就非 0 結束。
4. 寫 manifest.json 給 scripts/social_publish.py。

用法
----
    python scripts/social_snap.py --kind intraday --out snaps/20261020-0935
    python scripts/social_snap.py --kind close    --out snaps/20261020-close
    python scripts/social_snap.py --kind intraday --base http://127.0.0.1:8791/index.html --serve site --mock-live --out /tmp/demo

結束碼：0＝有產出；10＝今天不是交易日／不在盤中時段／法人資料還不是今天，刻意不發（不算失敗）；
        2＝一張都沒截成；3＝版面有重疊（不准發）；4＝畫面上還有「即時」字樣（不准發）。

誠實規則
--------
· 即時閘門（livegate.js 只給管理者）：不用任何登入權杖。--serve 用 checkout 的 site/ 在 127.0.0.1 起站，注入 TW_LIVE_OVERRIDE
  （只有 localhost 認的後門，正式站不受影響）；資料用 --data-url 從正式站下載；報價請求用 Playwright 補上正式站的 Origin。
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
# 連買賣排行：藏掉分頁列、「看全部」，每邊只留前 7 列（n+8）（字才放得夠大）；摘要與設定列保留
def STREAK_PIECE(name):
    return dict(name=name, hide=["#mktSeg2", ".srcol .srrow:nth-child(n+8)"], hide_text=[r"^看全部"], title="盤後法人")


# m：手機版（IG 限動）要截的片段；每片 dict(name, hide=[CSS], hide_text=[正規式], start, end, pre=JS)
#     start／end＝CSS 選擇器或 {"js": "回傳元素的函式內文"}，None＝整張卡的上緣／下緣
# 每個目標有兩份片段清單：d＝桌機寬（Threads 用）、m＝手機版面（IG 限動用）。片段欄位：
#   name 檔名；sel 只截這個元素（沒有 sel＝整張卡）；hide／hide_text 截圖前藏起來的元素；pre_m 手機版截圖前跑的 JS（傳入該元素）；
#   title 標題中間那段（「哩股哩股｜<title> MM/DD HH:MM」）；text＝輪盤上方四行（quad）或樹下方備註兩行（flows）
ROT_RANK_TALLER = ("(el) => { const h = 540; const ch = document.querySelector('#rankFlow');"
                   " [el, ch].forEach(e => e && e.style.setProperty('height', h + 'px', 'important'));"
                   " const c = window.echarts && ch && echarts.getInstanceByDom(ch); if (c) c.resize(); }")
BREADTH_TALL = ("(el) => { const h = 820; ['#chgDistBox', '#chgDist'].forEach(i => { const e = document.querySelector(i); if (e) e.style.setProperty('height', h + 'px', 'important'); });"
                " const ch = document.querySelector('#chgDist'); const c = window.echarts && ch && echarts.getInstanceByDom(ch); if (c) c.resize(); }")
HEAT_TALL = ("(el) => { const h = 660; const ch = document.querySelector('#indTree'); [document.querySelector('#indTreeWrap'), ch].forEach(e => e && e.style.setProperty('height', h + 'px', 'important'));"
             " const c = window.echarts && ch && echarts.getInstanceByDom(ch); if (c) c.resize(); }")
FILL_JS = """([el, a]) => {   // 把卡片拉到 a.want（css px）高：差額加在 a.charts 的圖表容器上，echarts／lightweight-charts 都重畫（不是拉伸點陣圖）
  const delta = a.want - el.getBoundingClientRect().height;
  a.charts.forEach(sel => { const e = el.querySelector(sel) || document.querySelector(sel); if (!e) return;
    const h = Math.max(120, Math.round(e.getBoundingClientRect().height + delta));
    e.style.setProperty('height', h + 'px', 'important'); e.style.setProperty('min-height', h + 'px', 'important'); });
  if (window.echarts) document.querySelectorAll('[_echarts_instance_]').forEach(e => { const c = echarts.getInstanceByDom(e); if (c) c.resize(); });
  window.dispatchEvent(new Event('resize'));
  return el.getBoundingClientRect().height;
}"""
STORY_HEAT_VW, STORY_HEAT_DSF = 700, 2.4     # 熱力圖限動版：窄桌機視窗（>640 仍是桌機版面），方塊變大、字放大後更清楚
STORY_RATIO = 1.6      # 限動截圖目標高寬比（1005×1608，剛好填滿卡片）
ROT_UNCHECK = """async (el) => {   // 把「顯示軌跡／顯示腳印／水波／掃描」全部取消勾選，只留點與標籤
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const find = () => [...document.querySelectorAll('input[type=checkbox]')].filter(i => /顯示軌跡|顯示腳印|水波|掃描/.test(((i.closest('label') || i.parentElement || {}).textContent) || ''));
  let cbs = find(), opened = false;
  if (cbs.length < 4) { const b = document.querySelector('#m4RotSet'); if (b) { b.click(); opened = true; await wait(700); cbs = find(); } }
  cbs.forEach(i => { if (i.checked) i.click(); });
  await wait(700);
  if (opened) { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await wait(400); }
  return cbs.length;
}"""
ROT_PIECES = [dict(name="rotation-wheel", sel="#rotClockWrap", title="資金輪盤", text="quad", pre=ROT_UNCHECK, trim_bottom_m=32, trim_bottom_d=17),   # 輪盤底下那行「⚡ 即時：灰虛線…」是畫布文字，只能裁掉
              dict(name="rotation-rank", sel="#rankFlowWrap", title="族群資金排行", pre_m=ROT_RANK_TALLER)]
SANKEY_STORY_VW, SANKEY_STORY_VH, SANKEY_STORY_DSF = 910, 1300, 1.3   # 限動版分流樹：窄桌機視窗（手機 390 版的樹高寬比 1.86，放進卡片只佔內寬約 70%；桌機版面槽位較矮，重畫後比較接近卡片內寬比）
SANKEY_SCRUB = [["即時板塊合計.*", ""], ["\\s*[—-]\\s*\\(真實\\)", ""], ["\\s*盤後\\s*$", ""]]   # 根節點只留「台股成交值」；去掉「盤後」尾巴
SANKEY_PIECES = [dict(name="sankey-tree", sel="#sankeyWrap", title="資金分流樹", text="flows", root_sel="body",
                      
                      hide=["#sankeyLive", "#sankeyMotionBtn", ".ftbtn"], hide_exact=["~即時", "~^動態"], scrub=SANKEY_SCRUB)]
TARGETS = [
    dict(name="rotation", snap="rot-wheel", kind="intraday", label="資金輪盤／族群資金排行", route="flow/rotation",
         card="#flowRotCard", live="#rotLiveBtn",
         live_ok="() => { const b = document.querySelector('#rotLiveBtn'); const t = document.querySelector('#rotLiveTag');"
                 " return !!b && b.getAttribute('aria-pressed') === 'true' && !!t && !t.hidden && !/抓取中|抓不到|失敗|逾時|連不到/.test(t.innerText); }",
         headline=r"資金[占佔]比\s*增加最多\s*[：:][^\n]*", d=ROT_PIECES, m=ROT_PIECES),
    dict(name="sankey", snap="flow-tree", kind="intraday", label="資金分流樹", route="flow/sankey",
         card="#flowSankeyCard", live="#sankeyLiveBtn",
         live_ok="() => { const b = document.querySelector('#sankeyLiveBtn');"
                 " return !!b && (b.getAttribute('aria-pressed') === 'true' || b.classList.contains('on')) && !/抓取中|抓不到|失敗|逾時|連不到/.test((document.querySelector('#sankeyLive') || {}).innerText || ''); }",
         headline=None, d=SANKEY_PIECES, m=SANKEY_PIECES),
    # 熱力圖：桌機網頁版（1440）上＝產業「整個台股一次看」、下＝題材資金熱力，合成一張（Threads 與限動共用這張）
    dict(name="heat", kind="intraday", label="資金熱力圖", route="heatmap/industry", card="#indTreeWrap",
         parts=[dict(name="heat-industry", route="heatmap/industry", card="#indTreeWrap", closest_card=True, live="auto", live_ok=None,
                     hide=[".howbtn"], fill=dict(frac=0.60, charts=["#indTreeWrap", "#indTree"])),
                dict(name="heat-theme", route="heatmap/theme", card="#themeMapCard", live="auto", live_ok=None, hide=[".howbtn"], fill=dict(frac=0.40, charts=["#themeMap"]))],
         live="auto", live_ok=None, headline=None, d=[dict(name="heat", title="資金熱力圖")], m=[]),
    dict(name="market-index", kind="intraday", label="大盤走勢", route="overview", card="#m3Frame",
         live=".livetg",
         live_ok="() => { const b = document.querySelector('.livetg'); const f = document.querySelector('#m3Frame');"
                 " return !!b && !!f && (b.classList.contains('on') || b.getAttribute('aria-pressed') === 'true') && !/連不到|抓不到|失敗|逾時/.test(f.innerText); }",
         headline=None, d=[dict(name="market-index", hide=[".howbtn"], hide_exact=["~即時"])],
         m=[dict(name="market-index", hide=[".howbtn"], hide_exact=["~即時"], fill=dict(frac=1.0, charts=[".m3-chart", ".tv-lightweight-charts"]))]),
    dict(name="market-breadth", kind="intraday", label="漲跌家數", route="market/updown", card=".mktdist", closest_card=True,
         live="#mktMode button[data-m=live]",
         live_ok="() => { const n = document.querySelector('#mktLive');"
                 " return !!n && !n.hidden && !/抓取中|抓不到|失敗|逾時|連不到/.test(n.innerText); }",
         headline=None, d=[dict(name="market-breadth", hide=[".howbtn"])], m=[dict(name="market-breadth", hide=[".howbtn", "#distFilter"], fill=dict(frac=1.0, charts=["#chgDistBox", "#chgDist"]))]),
    # 盤後（法人資料要收盤後證交所公布才有，沒有即時版，所以另一篇發，不放進盤中那篇）
    dict(name="streak-trust", kind="close", label="法人連續買賣超｜投信", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="trust",
         m=[STREAK_PIECE("streak-trust")]),
    dict(name="streak-foreign", kind="close", label="法人連續買賣超｜外資", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="foreign",
         m=[STREAK_PIECE("streak-foreign")]),
    dict(name="streak-total", kind="close", label="法人連續買賣超｜合計", route="market/streak",
         card="#mktBody", closest_card=True, live=None, live_ok=None, headline=None, streak_who="total",
         m=[STREAK_PIECE("streak-total")]),
    # 當日三大法人買賣超卡（另派人做，市場明細新增；data-snap="inst-today"）。卡片不存在就跳過。route 以 docs/social_snap_targets.md 為準。
    dict(name="inst-today", kind="close", label="當日三大法人買賣超", route="market/inst", card="[data-snap=inst-today]",
         attr_only=True, live=None, live_ok=None, headline=None, m=[dict(name="inst-today")]),
]

# 每張的標題＝功能名稱本身（Andy 10-20：「標題就是這功能」），副標是小字；全部畫面與貼文不出現「即時」字樣
PIECE_META = {
    "rotation-wheel": ("資金輪盤", "族群在哪個象限"),
    "rotation-rank": ("族群資金排行", "各族群資金占比變化（pp）"),
    "sankey-tree": ("資金分流樹", "成交值依產業鏈流向族群"),
    "heat": ("資金熱力圖", "產業一次看（上）、題材資金熱力（下）"),
    "market-index": ("大盤走勢", "加權指數、櫃買指數、台指期"),
    "market-breadth": ("漲跌家數", "全市場漲跌分佈"),
    "streak-trust": ("法人連續買賣超", "投信"),
    "streak-foreign": ("法人連續買賣超", "外資"),
    "streak-total": ("法人連續買賣超", "三大法人合計"),
    "inst-today": ("三大法人買賣超", "當日"),
}
# 版型配色：直接取自 site/index.html 的 CSS 變數（淺色 :root[data-theme=light]、深色 :root）
FRAME = {
    "light": dict(bg="#F4F3EF", panel="#ffffff", panel2="#FAF9F6", line="#E9E6DF", line2="#D6D2C8", ink="#1F1D19", ink2="#3E3A33",
                  ink3="#5F5A51", cyan="#0a6b8a", rise="#c81234", fall="#07794f", amber="#8f5600"),
    "dark": dict(bg="#070b16", panel="#0f172b", panel2="#141e36", line="#1e2a48", line2="#2a3860", ink="#e8eeff", ink2="#a9b6d6",
                 ink3="#8493b8", cyan="#3ee0ff", rise="#ff4d6d", fall="#2ee59d", amber="#ffb454"),
}
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


def sync_data(site_dir: Path, data_url: str) -> None:
    """把網站會讀的 JSON 從正式站抓到本機 site/data/（名稱從 site/*.js 的 load('名稱') 與 data/xxx.json 掃出來）。"""
    names = set()
    for f in site_dir.glob("*.js"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        names |= set(re.findall(r"load\(\s*'([a-z0-9_]+)'", txt))
        names |= {m for m in re.findall(r"data/([a-z0-9_]+)\.json", txt)}
    names.add("meta")
    dst = site_dir / "data"
    dst.mkdir(exist_ok=True)
    ok = 0
    for n in sorted(names):
        try:
            with urlopen(f"{data_url.rstrip('/')}/{n}.json?_={int(time.time())}", timeout=40) as r:
                (dst / f"{n}.json").write_bytes(r.read())
            ok += 1
        except Exception:  # noqa: BLE001
            pass     # 沒有的檔頁面本來就有 fallback
    log(f"下載網站資料 {ok}/{len(names)} 份 ← {data_url}")


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
CORS_HOSTS = re.compile(r"workers\.dev|deno\.net")


def spoof_origin_handler(route):
    """本機站打正式的報價代理時，補上正式站的 Origin（Worker 看 Origin 擋 localhost），並在回應補 CORS，瀏覽器才放行。"""
    req = route.request
    cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "GET,OPTIONS"}
    if req.method == "OPTIONS":
        return route.fulfill(status=204, headers=cors)
    try:
        hdr = {k: v for k, v in req.headers.items() if k.lower() not in ("origin", "referer")}
        hdr["origin"] = SITE_URL
        hdr["referer"] = SITE_URL + "/"
        resp = route.fetch(headers=hdr, timeout=15000)
        h = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-encoding", "content-length")}
        h.update(cors)
        route.fulfill(status=resp.status, headers=h, body=resp.body())
    except Exception:  # noqa: BLE001
        route.abort()


def flowtopo_patch(route):
    """只改截圖用瀏覽器載到的 flowtopo.js（不動網站本身）：分流樹根節點標籤只留「台股成交值」、拿掉節點尾巴的「盤後」。
    這兩段文字畫在畫布上，沒辦法用 DOM 改。"""
    try:
        resp = route.fetch()
        body = resp.text()
        body = body.replace("(S.opts.rootLines || ['台股成交值']).forEach", "['台股成交值'].forEach")
        body = body.replace("out.push({ t: ' 盤後', c: P.ink3, w: 500, fs: 12 }); return out;", "return out;")
        route.fulfill(response=resp, body=body)
    except Exception:  # noqa: BLE001
        route.continue_()


def open_ctx(browser, base: str, args, today_ymd: str, sniff: dict, mobile: bool, dsf: float):
    if mobile:
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=dsf, is_mobile=True,
                                  has_touch=True, locale="zh-TW", timezone_id="Asia/Taipei")
    else:
        ctx = browser.new_context(viewport={"width": args.width, "height": args.height}, device_scale_factor=args.scale,
                                  locale="zh-TW", timezone_id="Asia/Taipei")
    # 亮色主題＋同意橫幅／導覽先設定好；TW_THEME_LEGACY 讓 tw.theme 永久生效（不跟時鐘自動切）
    init = ("window.TW_THEME_LEGACY=1;try{localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'snap'}));"
            "localStorage.setItem('tw.tour','*');localStorage.setItem('tw.theme','light');}catch(e){}")
    if args.live_override:
        init += "window.TW_LIVE_OVERRIDE=true;"          # 只有 127.0.0.1／localhost 認；正式站不認
    if args.mock_live:
        init += "try{localStorage.setItem('tw.live.proxy','https://mock-quote.test');}catch(e){}"
    ctx.add_init_script(init)
    pg = ctx.new_page()
    pg.route("**/flowtopo.js*", flowtopo_patch)
    if args.mock_live:
        pg.route("**/quote?*", mock_quote_handler(today_ymd, now_tpe().strftime("%H:%M:%S")))
        pg.route("**/stream?*", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
    elif args.spoof_origin:
        pg.route(CORS_HOSTS, spoof_origin_handler)

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
        el = pg.query_selector(f'[data-snap="{t.get("snap", t["name"])}"]')
    if el is None and (use_attr == "only" or t.get("attr_only")):
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
        h = el.evaluate_handle("e => [...e.querySelectorAll('button')].find(b => /即時/.test(b.innerText)) || null")
        b = h.as_element()
        if not b:
            return False
    else:
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
            else:   # 沒有專屬判斷（熱力圖）：看 data-snap 卡片的 data-snap-live，或卡片內「即時」鈕亮著
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


def read_headline(el, t: dict) -> str:
    rx = t.get("headline")
    if not rx:
        return ""
    m = re.search(rx, el.inner_text())
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""


def read_streak(pg) -> dict:
    """讀連續買超前三（頁面上顯示的名稱與天數，原文照抄）與上方摘要。"""
    return pg.evaluate("""() => {
        const sub = (document.querySelector('#streakSub') || {}).innerText || '';
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


HIDE_JS = """([root, a]) => {   // a = {css, text, exact, scrub}；root＝卡片元素。即時模式會定期重畫，所以用 MutationObserver 持續套用
  const apply = () => {
    const hit = new Set();
    (a.css || []).forEach(s => root.querySelectorAll(s).forEach(e => hit.add(e)));
    (a.exact || []).forEach(t => root.querySelectorAll('*').forEach(e => { const tx = (e.textContent || '').trim(); if (e.children.length === 0 && (t[0] === '~' ? new RegExp(t.slice(1)).test(tx) : tx === t)) hit.add(e); }));
    (a.text || []).forEach(rx => {
      const re = new RegExp(rx);
      const c = [...root.querySelectorAll('*')].filter(e => re.test((e.innerText || '').trim()) && e.children.length < 4);
      if (c[0]) hit.add(c[0].closest('.row,.ddrow,.rotfilter,div') || c[0]);
    });
    hit.forEach(e => { if (!e.hasAttribute('data-snap-hid')) { e.setAttribute('data-snap-hid', e.style.display || ' '); e.style.setProperty('display', 'none', 'important'); } });
    if ((a.scrub || []).length) {   // 只改截圖用的頁面狀態（文字節點），不動網站程式
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let t;
      while ((t = w.nextNode())) { let v = t.nodeValue; for (const [rx, rep] of a.scrub) v = v.replace(new RegExp(rx), rep); if (v !== t.nodeValue) t.nodeValue = v; }
    }
    return hit.size;
  };
  if (window.__snapObs) window.__snapObs.disconnect();
  const n = apply();
  let busy = false;
  const ob = new MutationObserver(() => { if (busy) return; busy = true; ob.disconnect(); try { apply(); } finally { ob.observe(root, { subtree: true, childList: true, characterData: true }); busy = false; } });
  ob.observe(root, { subtree: true, childList: true, characterData: true });
  window.__snapObs = ob;
  return n;
}"""
SCAN_JS = """(root) => {   // 掃畫面上看得到的 DOM 文字有沒有「即時」（畫布內的字掃不到）
  const out = [], w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = w.nextNode())) {
    if (!/即時/.test(t.nodeValue)) continue;
    const e = t.parentElement;
    if (!e || getComputedStyle(e).display === 'none' || getComputedStyle(e).visibility === 'hidden' || !e.getClientRects().length) continue;
    out.push(t.nodeValue.trim().slice(0, 40) + ' @' + e.tagName + '.' + (e.className.baseVal ?? e.className) + ' < ' + (e.parentElement ? e.parentElement.tagName + '.' + (e.parentElement.className.baseVal ?? e.parentElement.className) : ''));
  }
  return out;
}"""
UNHIDE_JS = """() => { if (window.__snapObs) { window.__snapObs.disconnect(); window.__snapObs = null; } document.querySelectorAll('[data-snap-hid]').forEach(e => {
  const v = e.getAttribute('data-snap-hid'); e.style.removeProperty('display'); if (v.trim()) e.style.display = v; e.removeAttribute('data-snap-hid'); }); }"""

FIND_JS = """(spec) => { const f = new Function(spec); return f(); }"""
PIECE_RECT_JS = """([card, a]) => {
  const find = (sp) => !sp ? null : (typeof sp === 'string' ? document.querySelector(sp) : new Function(sp.js)());
  const cr = card.getBoundingClientRect();
  const s = find(a.start), e = find(a.end);
  const top = (s || card).getBoundingClientRect().top + scrollY;
  const bot = (e || card).getBoundingClientRect().bottom + scrollY;
  // 最小字級（只算這一片裡有文字的 DOM 元素；canvas 裡的字量不到）
  let minpx = 999;
  document.querySelectorAll('body *').forEach(x => {
    if (!x.childNodes) return;
    const own = [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) return;
    const r = x.getBoundingClientRect();
    if (r.width < 1 || r.top + scrollY < top - 1 || r.bottom + scrollY > bot + 1) return;
    const cs = getComputedStyle(x); if (cs.display === 'none' || cs.visibility === 'hidden') return;
    minpx = Math.min(minpx, parseFloat(cs.fontSize));
  });
  return { x: cr.left + scrollX, y: top, w: cr.width, h: bot - top, minpx };
}"""


READ_QUAD_JS = """async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const out = [];
  for (const b of document.querySelectorAll('#rotClock .rotquads .rq')) {
    const label = b.firstChild.textContent.trim();
    b.click(); await wait(500);
    const names = [...document.querySelectorAll('#stagePanel .ms li[data-gid] .g')].map(e => e.textContent.trim());
    out.push([label, names]);
    b.click(); await wait(300);
  }
  return out;
}"""
READ_FLOWS_JS = """async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const read = () => [...document.querySelectorAll('#sankeyRank .skr-r')].slice(0, 5).map(r => {
    const n = r.querySelector('.n b'), v = r.querySelector('.v b');
    return n ? n.textContent.trim() : ''; });
  const tabs = [...document.querySelectorAll('#sankeyRank .skr-tab button')];
  const res = { inflow: [], outflow: [] };
  if (tabs[0]) { tabs[0].click(); await wait(500); res.inflow = read(); }
  if (tabs[1]) { tabs[1].click(); await wait(500); res.outflow = read(); tabs[0] && tabs[0].click(); }
  return res;
}"""


READ_HEAT_JS = """() => {   // 產業熱力圖（echarts treemap）：每個族群的名稱與漲跌幅（頁面圖上顯示的那組資料）
  const e = document.getElementById('indTree'); const out = [];
  if (!e || !window.echarts) return out;
  const c = echarts.getInstanceByDom(e) || (e.firstElementChild && echarts.getInstanceByDom(e.firstElementChild));
  if (!c) return out;
  const walk = n => { if (n.children) n.children.forEach(walk); else if (typeof n.chg === 'number' && n.name) out.push([n.name, n.chg]); };
  (c.getOption().series[0].data || []).forEach(walk);
  return out;
}"""


def read_breadth(pg) -> dict:
    """市場明細「漲跌家數 N 漲／N 跌」原文。"""
    txt = pg.evaluate("() => document.body.innerText")
    m = re.search(r"(\d[\d,]*)\s*漲／\s*(\d[\d,]*)\s*跌", txt)
    return {"up": m.group(1), "down": m.group(2)} if m else {}


def quad_lines(data) -> list:
    """2×2 四塊（版面照輪盤四個角：改善、領先／落後、轉弱），每塊標題＋前 5 個族群（頁面原文，不寫「等 N 個」）。"""
    d = {k: v for k, v in data}
    return [[k, d[k][:5]] for k in ("改善", "領先", "落後", "轉弱") if k in d]


def flow_notes(res: dict) -> list:
    out = []
    if res.get("inflow"):
        out.append(["流入前五", res["inflow"][:5]])
    if res.get("outflow"):
        out.append(["流出前五", res["outflow"][:5]])
    return out


def shoot_piece(pg, card_el, pc: dict, raw_dir: Path, mode: str, dsf: float) -> dict:
    """截一片。mode＝'d'（桌機）或 'm'（手機）。有 sel 就只截那個元素；沒有 sel：桌機整張卡、手機依 start/end 切（連買賣、熱力圖）。"""
    pg.evaluate(UNHIDE_JS)
    tgt = pg.query_selector(pc["sel"]) if pc.get("sel") else card_el
    if tgt is None:
        raise RuntimeError(f"找不到 {pc.get('sel')}")
    if pc.get("pre"):
        pg.evaluate(pc["pre"], tgt)
        pg.wait_for_timeout(900)
    pg.evaluate(HIDE_JS, [pg.query_selector(pc["root_sel"]) if pc.get("root_sel") else tgt, {"css": pc.get("hide", []) + [".zbadge", ".echarts-tooltip"], "text": pc.get("hide_text", []), "exact": pc.get("hide_exact", []), "scrub": pc.get("scrub", [])}])
    pg.evaluate("() => { if (window.echarts) document.querySelectorAll('[_echarts_instance_]').forEach(e => { const c = echarts.getInstanceByDom(e); if (c) c.dispatchAction({ type: 'hideTip' }); }); }")
    if mode == "m" and pc.get("fill"):
        bb = tgt.bounding_box()
        pg.evaluate(FILL_JS, [tgt, {"want": bb["width"] * STORY_RATIO * pc["fill"]["frac"], "charts": pc["fill"]["charts"]}])
        pg.wait_for_timeout(1200)
    if mode == "m" and pc.get("pre_m"):
        pg.evaluate(pc["pre_m"], tgt)
        pg.wait_for_timeout(900)
    pg.wait_for_timeout(600)
    try:
        tgt.evaluate("e => e.scrollIntoView({block: 'center'})")
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(300)
    pg.mouse.move(2, 2)          # 滑鼠移開，免得截到 hover 的「滾輪放大」小標
    path = raw_dir / f"{mode}_{pc['name']}.png"
    if mode == "m" and not pc.get("sel") and (pc.get("start") or pc.get("end")):
        rect = pg.evaluate(PIECE_RECT_JS, [card_el, {"start": pc.get("start"), "end": pc.get("end")}])
        cb = card_el.bounding_box()
        pg.screenshot(path=str(path), clip={"x": cb["x"], "y": max(0, rect["y"]), "width": cb["width"], "height": rect["h"] + 6}, full_page=True)
    elif pc.get("trim_bottom_" + mode):
        r = pg.evaluate(PIECE_RECT_JS, [tgt, {"start": None, "end": None}])
        pg.screenshot(path=str(path), clip={"x": r["x"], "y": r["y"], "width": r["w"], "height": r["h"] - pc["trim_bottom_" + mode]}, full_page=True)
    else:
        tgt.screenshot(path=str(path))
    minpx = pg.evaluate(PIECE_RECT_JS, [tgt, {"start": None, "end": None}])["minpx"]
    jishi = pg.evaluate(SCAN_JS, tgt)
    return {"jishi": jishi, "name": pc["name"], "raw": str(path), "dsf": dsf, "min_css_font": minpx, "title": pc.get("title", ""), "text": pc.get("text")}


def snap_targets(args, base: str, out: Path, today_ymd: str) -> tuple[list[dict], dict]:
    """每個目標：桌機寬截片段（Threads 用）＋手機版面截片段（IG 限動用）。"""
    from playwright.sync_api import sync_playwright
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []
    sniff = {"quote_dates": set(), "errors": []}
    wanted = [t for t in TARGETS if t["kind"] == args.kind and (not args.only or t["name"] in args.only.split(","))]
    attr_mode = "only" if args.use_snap_attr else ("never" if args.no_snap_attr else "prefer")
    m_dsf = 1080 / 374.0          # 手機卡片寬 374 css px（390 − 左右各 8）→ 輸出剛好 1080 寬

    def prepare(pg, t, info):
        go_target(pg, base, t)
        el = resolve_target(pg, t, attr_mode)
        if el is None:
            info["why"] = "找不到目標元素（頁面上沒有）→ 跳過"
            return None
        if t.get("streak_who"):
            pg.evaluate("""(w) => { const v = document.querySelector('#streakView button[data-v=rank]'); if (v) v.click();
                                   const b = document.querySelector('#streakWho button[data-w=' + w + ']'); if (b) b.click(); }""",
                        t["streak_who"])
            pg.wait_for_timeout(1500)
            info.setdefault("streak", read_streak(pg))
        if args.kind == "intraday" and not (args.skip_live == "all" or t["name"] in args.skip_live.split(",")):
            if not click_live(pg, t, el):
                info["why"] = "沒有即時鈕（這張還不能即時）→ 不發"
                return None
            if not live_confirmed(pg, t, args):
                info["why"] = "即時沒套上（抓不到報價）→ 不發"
                return None
        if not wait_snap_ready(pg, t.get("snap", t["name"]), 20000):
            info["why"] = "TwSnapReady 逾時 → 不發"
            return None
        if args.kind == "intraday" and not (args.skip_live == "all" or t["name"] in args.skip_live.split(",")):
            st = pg.evaluate("""(n) => { const e = document.querySelector('[data-snap="' + n + '"]'); const h = e && (e.closest('[data-snap-live]') || e);
                                         return (h && h.getAttribute('data-snap-live')) || ''; }""", t.get("snap", t["name"]))
            if st == "err":   # 前端回報即時抓不到（或等超過 60 秒）→ 不拿舊圖冒充
                info["why"] = "data-snap-live=err（即時抓不到）→ 不發"
                return None
        pg.wait_for_timeout(1500)
        pg.evaluate(HIDE_FLOATING_JS, t["card"])
        pg.wait_for_timeout(300)
        return resolve_target(pg, t, attr_mode) or el

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
        # ---------- 桌機（Threads）
        ctx, pg = open_ctx(browser, base, args, today_ymd, sniff, False, args.scale)
        for t in wanted:
            info = {"name": t["name"], "label": t["label"], "ok": False, "why": "", "pieces_d": [], "pieces_m": []}
            try:
                if t.get("parts"):
                    recs = []
                    for part in t["parts"]:
                        pinfo = {}
                        pel = prepare(pg, part, pinfo)
                        if pel is None:
                            info["why"] = f"{part['name']}：{pinfo.get('why')}"
                            recs = []
                            break
                        recs.append(shoot_piece(pg, pel, dict(name=part["name"], hide=part.get("hide", [])), raw_dir, "d", args.scale))
                        if part["name"] == "heat-industry":
                            info["heat"] = pg.evaluate(READ_HEAT_JS)
                    if recs:
                        from PIL import Image
                        ims = [Image.open(r["raw"]).convert("RGB") for r in recs]
                        W = max(i.width for i in ims)
                        gap = 24
                        sheet = Image.new("RGB", (W, sum(i.height for i in ims) + gap * (len(ims) - 1)), (244, 243, 239))
                        y = 0
                        for im in ims:
                            sheet.paste(im, ((W - im.width) // 2, y))
                            y += im.height + gap
                        path = raw_dir / f"d_{t['name']}.png"
                        sheet.save(path)
                        rec = {"name": t["name"], "raw": str(path), "dsf": args.scale, "min_css_font": min(r["min_css_font"] for r in recs),
                               "title": t["label"], "text": None, "jishi": [x for r in recs for x in r["jishi"]]}
                        info["pieces_d"] = [rec]
                        info["pieces_m"] = [dict(rec)]       # 限動也用這張直式疊放的圖（等比放大填滿寬度）
                        info["ok"] = True
                        log("桌機截到", t["name"], "（產業＋題材合成）")
                    shots.append(info)
                    continue
                el = prepare(pg, t, info)
                if el is not None:
                    info["headline"] = read_headline(el, t)
                    for pc in (t.get("d") or [dict(name=t["name"], title=t["label"])]):
                        info["pieces_d"].append(shoot_piece(pg, el, pc, raw_dir, "d", args.scale))
                        log("桌機截到", pc["name"])
                    pg.evaluate(UNHIDE_JS)
                    if t["name"] == "market-breadth":
                        info["breadth"] = read_breadth(pg)
                    if any(pc.get("text") == "quad" for pc in t.get("d", [])):
                        info["lines"] = quad_lines(pg.evaluate(READ_QUAD_JS))
                    if any(pc.get("text") == "flows" for pc in t.get("d", [])):
                        info["notes"] = flow_notes(pg.evaluate(READ_FLOWS_JS))
                    info["ok"] = bool(info["pieces_d"])
            except Exception as exc:  # noqa: BLE001
                info["why"] = f"例外：{str(exc)[:100]}"
            shots.append(info)
        ctx.close()
        # ---------- 手機版面（IG 限動）
        ctx, pg = open_ctx(browser, base, args, today_ymd, sniff, True, m_dsf)
        for info in shots:
            if not info["ok"]:
                continue
            t = next(x for x in TARGETS if x["name"] == info["name"])
            if t.get("parts"):
                try:
                    story_args = argparse.Namespace(**{**vars(args), "width": STORY_HEAT_VW, "scale": STORY_HEAT_DSF})
                    sctx, spg = open_ctx(browser, base, story_args, today_ymd, sniff, False, STORY_HEAT_DSF)
                    pw = None
                    out_recs = []
                    for part in t["parts"]:          # 一張一張處理（換路由後前一張的元素就失效）
                        pinfo = {}
                        pel = prepare(spg, part, pinfo)
                        if pel is None:
                            raise RuntimeError(f"{part['name']}：{pinfo.get('why')}")
                        pw = pw or pel.bounding_box()["width"]
                        total = pw * STORY_RATIO - 12
                        pel.evaluate("e => e.scrollIntoView({block: 'start'})")
                        spg.evaluate(FILL_JS, [pel, {"want": total * part["fill"]["frac"], "charts": part["fill"]["charts"]}])
                        spg.wait_for_timeout(1500)
                        out_recs.append(shoot_piece(spg, pel, dict(name=part["name"], hide=part.get("hide", [])), raw_dir, "m", STORY_HEAT_DSF))
                    from PIL import Image
                    ims = [Image.open(r["raw"]).convert("RGB") for r in out_recs]
                    W = max(i.width for i in ims)
                    gap = int(12 * STORY_HEAT_DSF)
                    sheet = Image.new("RGB", (W, sum(i.height for i in ims) + gap * (len(ims) - 1)), (244, 243, 239))
                    y = 0
                    for im in ims:
                        sheet.paste(im, ((W - im.width) // 2, y))
                        y += im.height + gap
                    path = raw_dir / "m_heat.png"
                    sheet.save(path)
                    info["pieces_m"] = [{"name": "heat", "raw": str(path), "dsf": STORY_HEAT_DSF, "min_css_font": min(r["min_css_font"] for r in out_recs),
                                         "title": t["label"], "text": None, "jishi": [x for r in out_recs for x in r["jishi"]]}]
                    log("限動版截到 heat（窄視窗", STORY_HEAT_VW, "）")
                    sctx.close()
                except Exception as exc:  # noqa: BLE001
                    info["story_why"] = f"限動熱力圖例外：{str(exc)[:100]}"
                continue
            try:
                if t["name"] == "sankey":   # 限動版分流樹：換成窄桌機視窗重畫（重畫、非拉伸），樹本身變寬
                    sargs = argparse.Namespace(**{**vars(args), "width": SANKEY_STORY_VW, "height": SANKEY_STORY_VH, "scale": SANKEY_STORY_DSF})
                    sctx, spg = open_ctx(browser, base, sargs, today_ymd, sniff, False, SANKEY_STORY_DSF)
                    el = prepare(spg, t, {})
                    if el is None:
                        info["story_why"] = "限動分流樹沒截成"
                        sctx.close()
                        continue
                    for pc in t.get("m", []):
                        rec = shoot_piece(spg, el, pc, raw_dir, "m", SANKEY_STORY_DSF)
                        info["pieces_m"].append(rec)
                        log("限動版截到", pc["name"], "（窄桌機視窗", SANKEY_STORY_VW, "）")
                    sctx.close()
                    continue
                el = prepare(pg, t, {})
                if el is None:
                    info["story_why"] = "手機版沒截成"
                    continue
                for pc in t.get("m", []):
                    rec = shoot_piece(pg, el, pc, raw_dir, "m", m_dsf)
                    info["pieces_m"].append(rec)
                    log("手機截到", pc["name"], "最小字 css", rec["min_css_font"])
                pg.evaluate(UNHIDE_JS)
            except Exception as exc:  # noqa: BLE001
                info["story_why"] = f"手機例外：{str(exc)[:100]}"
        ctx.close()
        browser.close()
    return shots, sniff


# ---------------------------------------------------------------------------- 排版
def b64(path: str) -> str:
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f4f7fb;font-family:'Noto Sans CJK TC','Noto Sans TC','PingFang TC','Microsoft JhengHei','WenQuanYi Zen Hei',sans-serif;color:#17233a}
.title{font-weight:700;line-height:1.3;white-space:nowrap}
.foot{line-height:1.4;color:#4a5a73;white-space:nowrap}
.url{font-weight:700;color:#0b5fa5;white-space:nowrap}
"""


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _logo_uri() -> str:
    f = ROOT / "site" / "brand" / "icon-192.png"
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


LABEL_COLOR = {"領先": "rise", "轉弱": "amber", "改善": "cyan", "落後": "fall", "流入前五": "rise", "流出前五": "fall"}


def _blocks(items: list, cls: str) -> str:
    """items＝[[標題, [名稱, ...]], ...]；每塊一個方格（等寬等高），標題＋一行一個名稱，顏色沿用象限色。"""
    out = []
    for label, names in items:
        col = LABEL_COLOR.get(label, "cyan")
        rows = "".join(f"<li>{_esc(n)}</li>" for n in names)
        out.append(f'<div class=q data-box=q style="--c:var(--{col})"><b>{_esc(label)}</b><ul>{rows}</ul></div>')
    return f'<div class="grid {cls}">{"".join(out)}</div>' if out else ""


def layout_html(mode: str, title: str, sub: str, img: str, top: list, bot: list, theme: str) -> str:
    """財經終端／券商 App 風版型：品牌列（比比＋哩股哩股）→ 圓角細框卡片（標題＋副標、2×2 文字塊、截圖、備註塊）→ 右下網址。
    邊距與內距壓到最小，空間全給內容；flex 直排，元素天生不重疊，之後仍用瀏覽器量框檢查。"""
    c = FRAME[theme]
    var = ":root{" + "".join(f"--{k}:{v};" for k, v in c.items()) + "}"
    story = mode == "story"
    css = var + """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;background:var(--bg);color:var(--ink);font-family:'Noto Sans CJK TC','Noto Sans TC','PingFang TC','Microsoft JhengHei','WenQuanYi Zen Hei',sans-serif;display:flex;flex-direction:column;padding:__PAD__}
.brand{display:flex;align-items:center;gap:12px;height:__BH__px;flex:none}
.brand img{width:__LG__px;height:__LG__px;border-radius:13px;display:block}
.brand .nm{font-size:__BN__px;font-weight:800;letter-spacing:1px;white-space:nowrap}
.card{flex:1;min-height:0;display:flex;flex-direction:column;margin-top:8px;background:var(--panel);border:1.5px solid var(--line-2);border-radius:24px;padding:__CPAD__}
.hd{flex:none;margin:0 6px 8px}
.hd .t{font-size:__TT__px;font-weight:800;line-height:1.2;white-space:nowrap}
.hd .s{font-size:22px;color:var(--ink3);margin-top:2px;white-space:nowrap}
.grid{flex:none;display:grid;grid-template-columns:1fr 1fr;gap:10px;font-variant-numeric:tabular-nums}
.grid.top{margin-bottom:10px}.grid.bot{margin-top:10px}
.q{border-radius:14px;border:1.5px solid color-mix(in srgb,var(--c) 45%,var(--panel));background:color-mix(in srgb,var(--c) 9%,var(--panel));padding:__QP__;text-align:left;min-width:0}
.q b{display:block;color:var(--c);font-size:__QT__px;font-weight:800;line-height:1.25;margin-bottom:4px}
.q ul{list-style:none}.q li{font-size:__QF__px;line-height:1.38;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:clip}
.imgbox{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}
.shot{max-width:100%;max-height:100%;display:block;border-radius:12px}
.src{flex:none;text-align:right;margin-top:6px;font-size:26px;font-weight:700;color:var(--cyan);white-space:nowrap}
"""
    if story:
        css = (css.replace("__PAD__", "24px 24px 18px").replace("__BH__", "62").replace("__LG__", "52").replace("__BN__", "36").replace("__CPAD__", "12px 12px 10px")
               .replace("__TT__", "44").replace("__QP__", "10px 14px 8px").replace("__QT__", "40").replace("__QF__", "36"))
        css += "body{height:1920px}"
    else:
        css = (css.replace("__PAD__", "20px 20px 14px").replace("__BH__", "56").replace("__LG__", "46").replace("__BN__", "32").replace("__CPAD__", "12px 12px 10px")
               .replace("__TT__", "40").replace("__QP__", "8px 12px 6px").replace("__QT__", "30").replace("__QF__", "28"))
        css += ".card{flex:none}.shot{width:100%;max-height:none}.imgbox{flex:none;display:block}"
    logo = _logo_uri()
    body = f"""<div class=brand>{'<img data-box=logo src="' + logo + '">' if logo else ''}<div class=nm data-box=brand>哩股哩股</div></div>
<div class=card>
<div class=hd><div class=t data-box=title>{_esc(title)}</div><div class=s data-box=sub>{_esc(sub)}</div></div>
{_blocks(top, "top")}<div class=imgbox><img class=shot data-box=shot src="{img}"></div>{_blocks(bot, "bot")}</div>
<div class=src data-box=url>{SITE_HOST}</div>"""
    return f"<!doctype html><html><head><meta charset=utf-8><style>{css}</style></head><body>{body}</body></html>"


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


def compose(browser, mode: str, rec: dict, top: list, bot: list, out_png: Path, report: list, theme: str) -> None:
    from PIL import Image
    with Image.open(rec["raw"]) as im:
        iw, ih = im.size
    title, sub = PIECE_META.get(rec["name"], (rec.get("title") or rec["name"], ""))
    html = layout_html(mode, title, sub, b64(rec["raw"]), top, bot, theme)
    pg = browser.new_page(viewport={"width": 1080, "height": 1920 if mode == "story" else 1200}, device_scale_factor=1)
    pg.set_content(html, wait_until="load")
    pg.wait_for_timeout(400)
    H = 1920 if mode == "story" else int(pg.evaluate("document.body.offsetHeight"))
    if mode != "story":
        pg.set_viewport_size({"width": 1080, "height": H})
        pg.wait_for_timeout(200)
    res = pg.evaluate(OVERLAP_JS)
    box = pg.evaluate("(() => { const r = document.querySelector('.shot').getBoundingClientRect(), c = document.querySelector('.card').getBoundingClientRect(); return [r.width, r.height, c.height]; })()")
    scale = box[0] / iw
    res.update(file=out_png.name, w=1080, h=H, scale=round(scale, 3), shot_ratio=box[1] / H, content_ratio=box[2] / H, shot_px=[round(box[0]), round(box[1])])
    if rec.get("min_css_font") and rec["min_css_font"] < 900:
        res["min_font_1080"] = round(rec["min_css_font"] * rec["dsf"] * scale, 1)
    report.append(res)
    pg.screenshot(path=str(out_png), full_page=False)
    pg.close()


def img_size(path: str) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.size


# ---------------------------------------------------------------------------- 貼文文字
# 文案（Threads 單則上限 500 字，含網址）。深連結用網站實際路由；hash 路由的 query 放在 # 前面
THREADS_MAX = 480          # Threads 單則上限 500 字（網址以實際字元數計），留 20 字餘裕
ROUTE_INST = "market/streak"      # 法人頁路由；日後改 market/inst 只改這個常數
HASHTAGS = {"intraday": "#台股 #資金流向 #熱力圖 #族群輪動", "close": "#台股 #法人買賣超 #投信 #外資"}
DISCLAIMER = "資料：證交所／櫃買公開資料整理，僅供參考，不構成投資建議"


def deep_link(route: str, kind: str, ymd: str) -> str:
    camp = ("intraday_" if kind == "intraday" else "close_") + ymd[4:8]
    return f"{SITE_URL}/?utm_source=threads&utm_campaign={camp}#{route}"


def _join(names: list, n: int) -> str:
    return "、".join(names[:n])


# 降級順序：(每行名稱數, 附網址的模式)；all＝每行都附、two＝只有前兩行（輪盤、分流樹）附、one＝只在第一行附一個
LADDER = [(3, "all"), (2, "all"), (2, "two"), (1, "two"), (1, "one")]


def caption_lines(kind: str, stamp: str, shots: list[dict], data_date: str, ymd: str, n: int, links: str = "all") -> list[str]:
    ok = {s["name"]: s for s in shots if s.get("ok")}
    L = []

    def lk(route: str, idx: int) -> str:     # idx＝這是第幾個有內容的行（0 起算）
        return f" → {deep_link(route, kind, ymd)}" if links == "all" or (links == "two" and idx < 2) else ""
    if kind == "intraday":
        head = f"台股資金地圖｜{stamp}"
        L.append(head + (f" → {deep_link('flow/rotation', kind, ymd)}" if links == "one" else ""))
        idx = 0
        s = ok.get("rotation")
        if s:
            d = {k: v for k, v in s.get("lines", [])}
            if d.get("領先") and d.get("落後"):
                L.append(f"資金輪盤：領先 {_join(d['領先'], n)}；落後 {_join(d['落後'], n)}" + lk("flow/rotation", idx)); idx += 1
        s = ok.get("sankey")
        if s:
            d = {k: v for k, v in s.get("notes", [])}
            if d.get("流入前五") and d.get("流出前五"):
                L.append(f"資金分流樹：流入 {_join(d['流入前五'], n)}；流出 {_join(d['流出前五'], n)}" + lk("flow/sankey", idx)); idx += 1
        s = ok.get("heat")
        if s and s.get("heat"):
            h = sorted(s["heat"], key=lambda x: x[1])
            k = min(2, n)
            ups = "、".join(f"{a} {b:+.1f}%" for a, b in h[::-1][:k])
            dns = "、".join(f"{a} {b:+.1f}%" for a, b in h[:k])
            L.append(f"熱力圖：漲最多 {ups}；跌最多 {dns}" + lk("heatmap/industry", idx)); idx += 1
        s = ok.get("market-breadth")
        if s and s.get("breadth"):
            L.append(f"漲跌家數：上漲 {s['breadth']['up']} 家、下跌 {s['breadth']['down']} 家" + lk("market/updown", idx)); idx += 1
    else:
        L.append(f"台股法人買賣超｜{data_date[5:].replace('-', '/')}")
        parts = []
        for who in ("trust", "foreign"):
            buy = (ok.get(f"streak-{who}") or {}).get("streak", {}).get("buy") or []
            if buy:
                parts.append(f"{WHO_LABEL[who]}連買 " + _join(buy, n))
        if parts:
            L.append("；".join(parts) + f" → {deep_link(ROUTE_INST, kind, ymd)}")
    L.append(DISCLAIMER)
    L.append(HASHTAGS[kind])
    return L


def build_text(kind: str, stamp: str, shots: list[dict], data_date: str, ymd: str = "") -> str:
    """Threads／IG 文案。一律用實際字元數 len(text) ≤ 480；超過就依 LADDER 降級（名稱 3→2→1，再來只有前兩行附網址，最後只留第一行一個網址）。"""
    ymd = ymd or data_date.replace("-", "")
    txt = ""
    for n, links in LADDER:
        txt = "\n".join(caption_lines(kind, stamp, shots, data_date, ymd, n, links))
        if len(txt) <= THREADS_MAX:
            break
    if len(txt) > THREADS_MAX:
        log(f"⚠ 文案 {len(txt)} 字仍超過 {THREADS_MAX}")
    return txt


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
    ap.add_argument("--data-url", default="", help="先從這個網址下載網站要用的 JSON 到 --serve 的 data/（例如 https://liguligu-puipui.com/data）")
    ap.add_argument("--spoof-origin", action="store_true", help="報價請求補上正式站 Origin（本機站打正式報價代理用）")
    ap.add_argument("--skip-live", nargs="?", const="all", default="", help="只測版面：不要求即時（all 或逗號分隔的目標名；會截到盤後畫面，絕不可用在發布）")
    ap.add_argument("--from-shots", default="", help="沿用另一個輸出資料夾已截好的圖（只換 --frame 配色，示範用）")
    ap.add_argument("--frame", choices=["light", "dark"], default="light", help="版型配色（預設淺色，跟截圖一致）")
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
        if args.data_url:
            sync_data(Path(args.serve).resolve(), args.data_url)
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
        if args.from_shots:      # 只換版型配色：沿用另一輪已截好的圖（示範用）
            shots = json.loads((Path(args.from_shots) / "shots.json").read_text("utf-8"))
            sniff = {"quote_dates": set(), "errors": []}
        else:
            shots, sniff = snap_targets(args, base, out, today_ymd)
        if args.kind == "intraday" and not args.force:
            qd = sniff["quote_dates"]
            if qd and today_ymd not in qd:
                log(f"即時報價的成交日 {sorted(qd)} 不是今天 {today_ymd}（休市日）→ 不發")
                return 10
        ok = [s for s in shots if s.get("ok")]
        bad_words = [(rec["name"], rec["jishi"]) for s in ok for rec in s["pieces_d"] + s["pieces_m"] if rec.get("jishi")]
        log(f"「即時」字樣掃描：{sum(len(s['pieces_d']) + len(s['pieces_m']) for s in ok)} 片，{sum(len(h) for _, h in bad_words)} 筆")
        if bad_words:
            for n_, h_ in bad_words:
                log("  ✗", n_, h_)
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 4
        for s in shots:
            if not s.get("ok"):
                log("略過", s["name"], "：", s.get("why"))
        if not ok:
            log("一張都沒截成")
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 2

        stamp_full = now_tpe().strftime("%m/%d %H:%M")
        dd = data_date[5:].replace("-", "/")
        report: list[dict] = []
        stories: list[str] = []
        threads_imgs: list[str] = []
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()

            def texts(s, rec):
                return (s.get("lines", []) if rec.get("text") == "quad" else []), (s.get("notes", []) if rec.get("text") == "flows" else [])

            for s in ok:
                for rec in s["pieces_d"]:
                    tp, bt = texts(s, rec)
                    compose(browser, "threads", rec, tp, bt, out / f"threads_{rec['name']}.png", report, args.frame)
                    threads_imgs.append(f"threads_{rec['name']}.png")
                for rec in s["pieces_m"]:
                    tp, bt = texts(s, rec)
                    compose(browser, "story", rec, tp, bt, out / f"story_{rec['name']}.png", report, args.frame)
                    stories.append(f"story_{rec['name']}.png")
            browser.close()
        for r in report:
            if r["file"].startswith("story_") and r["shot_ratio"] < 0.75 and r["h"] == 1920:
                log(f"  ⚠ {r['file']} 截圖佔畫布 {r['shot_ratio']:.0%}、內容卡片佔 {r['content_ratio']:.0%}")
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
            "threads": {"text": build_text(args.kind, stamp_full, ok, data_date, today_ymd),
                        "images": threads_imgs},
            "story": stories,
        }
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
        (out / "caption.txt").write_text(manifest["threads"]["text"] + "\n", "utf-8")   # 給 Andy 手動貼 IG（限動 API 不能附文字與連結貼紙）
        log("manifest：", out / "manifest.json", "；文案字數", len(manifest["threads"]["text"]))
        return 0
    finally:
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
