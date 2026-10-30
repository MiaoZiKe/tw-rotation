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
    python scripts/social_snap.py --kind credit   --out snaps/20261020-credit   # 盤後融資：資料到齊那輪才發
    python scripts/social_snap.py --kind intraday --base http://127.0.0.1:8791/index.html --serve site --mock-live --out /tmp/demo

結束碼：0＝有產出；10＝今天不是交易日／不在盤中時段／法人資料還不是今天／融資資料還沒到齊／這一篇已發過，刻意不發（不算失敗）；
        2＝一張都沒截成；3＝版面有重疊（不准發）；4＝畫面上還有「即時」字樣（不准發）；
        5＝畫面上還有備註／來源／免責字樣（2026-10-26 Andy：圖上不放任何備註與來源，不准發）。

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_native as NAT  # noqa: E402  原生繪製的卡片（2026-10-26）
import social_gate as gate  # noqa: E402  資料日／交易日把關（2026-10-26）

DATE_LABEL = ""
PARTIAL: list = []    # 盤後保底：這一輪拿掉的過期卡（2026-10-29）
SUPPLEMENT = False    # 盤後法人補充貼文（--supplement，2026-10-29）
KIND = ""             # 本輪種類（intraday／close／credit），版型標題列的時段膠囊用
LOGO_MAP: dict = {}      # 代號→logo 網址（site/data/logos.json 的相對路徑，--data-url 時改成正式站的絕對網址）
DATA_SRC = ""            # sync_data 實際採用的資料來源網址（logo 圖檔不下載到本機，直接讀這裡）
DATE_BY: dict = {}       # 目標名稱→該張自己的資料日 MM/DD（取自資料檔本身，不借別的檔）
DATE_ISO: dict = {}      # 目標名稱→該張自己的資料日 YYYY-MM-DD（日期把關用；圖上日期、文案、manifest 都從這裡來）
NAME_MAP: dict = {}      # 代號→名稱（從網站資料 stocks.json 讀；頁面沒補到名稱的列用它補，不准只剩代號）
ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://liguligu-puipui.com"
# 文案最底下的連結（2026-10-26 Andy：「連結部分要改成：更多詳細資料可以點擊以下連結：https://liguligu-puipui.com/」——首頁網址，不帶追蹤參數與分頁）
LINK_LINES = ["👉 更多詳細資料可以點擊以下連結：", SITE_URL + "/"]      # 舊常數（不帶來源參數）：貼文改用 link_lines()，這個只留給沒有時段資訊的呼叫端
# 2026-10-26 Andy 核准 J-3（growth_command_1026.md）：貼文網址帶短參數 ?u=<平台>-<時段>-<yyyymmdd>，網站讀到後存成「第一次來源」，
# 才看得出哪一篇帶來進站／註冊（站內映射見 site/account.js 的 SRC_PLAT／SRC_SLOT；改代碼兩邊一起改，規則寫在 docs/marketing/social_unit/auto_post.md）。
# 平台代碼 th＝Threads、ig＝Instagram；時段 pm 盤前、id 盤中、cl 盤後、mg 融資融券。
SLOT_CODE = {"premarket": "pm", "intraday": "id", "close": "cl", "credit": "mg"}


# 2026-10-27 Andy 授權（docs/marketing/feature_funnel_1027.md 第四節 A＋C）：網址改成 ?u=<平台碼>-<功能碼>-<yyyymmdd>#<路由>，
# 落點依當天內容挑（領漲族群→產業鏈頁、事件→財經日曆），不再一律首頁。?u= 一定在 # 前面（站內 srcFromUrl 讀 location.search，放後面讀不到）。
# 功能碼預設是時段碼（pm/id/cl/mg）；功能推廣篇用 f2d f3d etfd etfi etfl earn ev* hot（站內對照見 site/account.js 的 SRC_SLOT）。
STATIC_ROUTES = {"flow/rotation", "flow/sankey", "flow/inst", "market/updown", "market/inst", "market/ma", "market/cand", "market/credit", "market/fut",
                 "heatmap/industry", "heatmap/theme", "season", "earnings", "articles", "etf/cal", "etf/list", "etf/inc"}   # 不含 #pricing（關卡 ⑥：貼文不得導價格頁）


@functools.lru_cache(maxsize=1)
def _group_maps() -> tuple[dict, dict, set]:
    """(族群顯示名→族群 id, 族群 id→產業鏈 id, 產業鏈 id 集合)；讀 pipeline/groups/groups.yaml，讀不到就全空（落點退回保底）。"""
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "pipeline" / "groups" / "groups.yaml").read_text("utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}, {}, set()
    gs = cfg.get("groups") or {}
    name2gid = {NAT.clean_name(v.get("name")): k for k, v in gs.items() if isinstance(v, dict) and v.get("name")}
    gid2chain = {k: v.get("chain") for k, v in gs.items() if isinstance(v, dict) and v.get("chain")}
    return name2gid, gid2chain, set((cfg.get("chains") or {}).keys())


def route_ok(route: str) -> bool:
    """落點白名單：靜態頁、#industry/<鏈 id>、#industry/group/<族群 id>；其餘（含 #pricing）一律不收，呼叫端退回保底。"""
    r = (route or "").lstrip("#")
    if r in STATIC_ROUTES:
        return True
    _, gid2chain, chains = _group_maps()
    m = re.fullmatch(r"industry/([a-z0-9_]+)", r)
    if m:
        return m.group(1) in chains
    m = re.fullmatch(r"industry/group/([a-z0-9_]+)", r)
    return bool(m and m.group(1) in gid2chain)


def group_of(name: str) -> str | None:
    """頁面上的族群名 → 族群 id（先全名、再互相包含）；自動桶（「半導體・其他」）沒有產業鏈，回 None。"""
    n2g, _, _ = _group_maps()
    nm = NAT.clean_name(name)
    if nm in n2g:
        return n2g[nm]
    for k, g in n2g.items():
        if len(nm) >= 3 and (nm in k or k in nm):
            return g
    return None


EVENT_ROUTES = (("除息", "etf/cal"), ("FOMC", "earnings"), ("利率決議", "earnings"), ("CPI", "earnings"), ("財報", "earnings"), ("非農", "earnings"), ("法說", "earnings"))
FALLBACK = {"intraday": "flow/rotation", "close": "market/inst", "credit": "market/credit", "premarket": ""}


def pick_landing(kind: str, ctx: dict | None = None, recent: list[str] | None = None) -> tuple[str, str]:
    """依當天內容挑貼文網址的落點，回 (路由不含 #，理由)。路由為空字串＝首頁。
    ctx：leaders＝當天領漲／資金流入的族群名（依強到弱）、events＝盤前近日事件名稱、reads＝盤前解讀句。
    盤中盤後：第一個對得到產業鏈的族群 → #industry/<鏈>；都對不到 → 保底（盤中 flow/rotation、盤後 market/inst）。
    盤前：事件（FOMC／CPI／財報／ETF 除息）優先 → 對應功能頁；否則解讀提到半導體／AI → #industry/semiconductor；否則首頁。
    recent：最近幾天用過的落點，同一落點已連續 2 天就改選下一個候選（避免天天導同一頁）。"""
    ctx = ctx or {}
    if recent is None:
        recent = RECENT.get(kind, [])      # 沒明講就用 --landing-json 載進來的近幾天落點（社群 state/landing_recent.json）
    cands: list[tuple[str, str]] = []
    if kind == "premarket":
        for e in ctx.get("events") or []:
            for kw, rt in EVENT_ROUTES:
                if kw in str(e):
                    cands.append((rt, f"事件「{e}」"))
                    break
        for e in ctx.get("etf_div") or []:      # 未來 7 天內有熱門 ETF 除息（資料湖 etf_dividend_events，只讀）→ ETF 配息行事曆
            cands.append(("etf/cal", f"ETF 除息：{e}"))
        txt = "".join(ctx.get("reads") or [])
        if re.search(r"半導體|費半|SOX|台積|輝達|AI", txt):
            cands.append(("industry/semiconductor", "美股解讀提到半導體／AI"))
    else:
        _, g2c, _ = _group_maps()
        for nm in ctx.get("leaders") or []:
            gid = group_of(nm)
            ch = g2c.get(gid) if gid else None
            if ch:
                cands.append((f"industry/{ch}", f"領漲族群「{NAT.clean_name(nm)}」屬 {ch} 鏈"))
    cands = [c for c in cands if route_ok(c[0])]
    seen = set()
    for rt, why in cands:
        if rt in seen:
            continue
        seen.add(rt)
        if recent[-2:] == [rt, rt]:
            continue
        return rt, why
    fb = FALLBACK.get(kind, "")
    return (fb if route_ok(fb) else ""), "沒有對應內容，用保底落點"


# ---- 近幾天落點記憶（2026-10-27）：讓 pick_landing 的「同一落點連續 2 天就換」真正生效 ----
# 檔案放 social-snaps 分支 state/landing_recent.json：{"intraday": [{"d": "20261027", "r": "industry/semiconductor"}, ...], ...}
# 工作流把檔案交給 --landing-json 讀；這一輪選了什麼寫進 <out>/landing_recent.json，真的發布（posted.json 有寫）才寫回分支，
# dry-run 與測試不會污染紀錄。每個時段只留最近 10 筆、同一天重跑只留最後一次。
RECENT: dict[str, list[str]] = {}        # kind → 落點路由（舊→新）
_RECENT_RAW: dict[str, list[dict]] = {}
CHOSEN: dict[str, tuple[str, str]] = {}  # kind → (ymd, route)：這一輪選的


def load_recent(path: str | Path | None) -> None:
    RECENT.clear()
    _RECENT_RAW.clear()
    if not path:
        return
    try:
        raw = json.loads(Path(path).read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return
    for k, v in (raw.items() if isinstance(raw, dict) else []):
        rows = [x for x in v if isinstance(x, dict) and isinstance(x.get("r"), str)] if isinstance(v, list) else []
        _RECENT_RAW[k] = rows
        RECENT[k] = [x["r"] for x in rows]


def landing_route(kind: str, ymd: str, ctx: dict | None = None) -> str:
    """挑落點並記下這一輪的選擇（寫檔用）；同一天重跑時，「近幾天」不含今天自己那一筆。"""
    recent = [x["r"] for x in _RECENT_RAW.get(kind, []) if x.get("d") != ymd] if _RECENT_RAW.get(kind) else RECENT.get(kind, [])
    rt = pick_landing(kind, ctx, recent)[0]
    CHOSEN[kind] = (ymd, rt)
    return rt


def save_recent(out: Path) -> None:
    """把近幾天紀錄＋這一輪的選擇寫到 <out>/landing_recent.json（沒選過就不寫）。"""
    if not CHOSEN:
        return
    data = {k: [dict(x) for x in v] for k, v in _RECENT_RAW.items()}
    for k, (d, r) in CHOSEN.items():
        data[k] = [x for x in data.get(k, []) if x.get("d") != d] + [{"d": d, "r": r}]
        data[k] = data[k][-10:]
    (out / "landing_recent.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")


def ctx_from_shots(ok: dict) -> dict:
    """從截圖讀到的資料抽出領漲族群：資金輪盤「領先」→ 資金分流樹「流入前五」→ 熱力圖漲最多。"""
    out: list = []
    d = {k: v for k, v in (ok.get("rotation") or {}).get("lines", [])}
    out += list(d.get("領先") or [])
    n = {k: v for k, v in (ok.get("sankey") or {}).get("notes", [])}
    out += list(n.get("流入前五") or [])
    h = sorted((ok.get("heat") or {}).get("heat") or [], key=lambda x: x[1], reverse=True)
    out += [a for a, _ in h[:3]]
    return {"leaders": out}


def link_url(kind: str, ymd: str, platform: str = "th", route: str = "", func: str = "") -> str:
    u = f"{SITE_URL}/?u={platform}-{func or SLOT_CODE.get(kind, 'xx')}-{ymd}"
    r = (route or "").lstrip("#")
    return u + (f"#{r}" if r and route_ok(r) else "")


def link_lines(kind: str, ymd: str, platform: str = "th", route: str = "", func: str = "") -> list[str]:
    """文案最底下兩行：「👉 …」＋帶來源參數與落點的網址（整篇只放這一個網址）。"""
    return [LINK_LINES[0], link_url(kind, ymd, platform, route, func)]
# 標題與段名前的表情符號（2026-10-26 Andy：「搭配些表情符號，除了個股」→ 只加在標題／段名，列股票名稱的「・」行不加）
EMOJI = {"盤面分析：": "🧭", "盤中3分鐘": "🕛", "盤後3分鐘": "🌙", "盤後3分鐘｜法人補充": "🌙", "盤後融資融券": "💳",
         "資金輪盤：": "🎡", "資金分流樹：": "🌳", "熱力圖：": "🔥",
         "台指期法人淨未平倉：": "📊", "散戶多空比：": "⚖️", "三大法人買賣超：": "🏦", "外資：": "🌏", "投信：": "🏢",
         "ETF 買超：": "📦", "融資維持率：": "🛡️", "融資：": "📈", "融券：": "📉"}


def _emo(L: list[str]) -> list[str]:
    def k(x):      # 「熱力圖（10/27 收盤）：」這種帶括號的段名，用括號前的段名找表情符號
        return re.sub(r"（[^）]*）：$", "：", x)
    return [f"{EMOJI[k(x)]} {x}" if k(x) in EMOJI else x for x in L]
SITE_HOST = "liguligu-puipui.com"
TPE = timezone(timedelta(hours=8))
DISCLAIMER = "資料：證交所／櫃買公開資料，僅供參考，不構成投資建議"
CHROMIUM = os.environ.get("TW_CHROMIUM") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None)

# ---------------------------------------------------------------------------- 目標清單
# name：給 data-snap／TwSnapReady 用的名稱（跟 docs/social_snap_targets.md 對齊；還沒對齊的以這裡為準，改一處就好）
# route：hash 路由；card：要截的元素（closest_card=True 表示往上找最近的 .card，才會帶到標題）
# live：「即時」鈕的選擇器（None＝沒有鈕，頁面本身就是當下資料）；live_ok：判斷即時真的套上的 JS（回 true／false）
# 連買賣排行：藏掉分頁列、「看全部」，每邊只留前 7 列（n+8）（字才放得夠大）；摘要與設定列保留
STREAK_CSS = (".mktstreakbar,#instView,#instMode,#instSw,#streakView,#streakWho,#streakGroupDD,#streakDays,.howbtn,.howtxt,.srmore,.itrow .dys,.itrow .px,.itdh,.srh small,.ithead{display:none!important}"
              ".itrow,.itrow.td,.itrow.td:has(.px.grp){grid-template-columns:var(--nmw,12em) minmax(0,1fr) var(--lw,5em)!important;gap:10px!important}"
              ".itrow .lots{text-align:right;white-space:nowrap}.itrow .sbar b{white-space:nowrap}"
              ".itrow .nm{display:flex!important;gap:8px;align-items:center}.itrow .nm b,.itrow .nm em{white-space:nowrap!important;overflow:visible!important;max-width:none!important}.itrow .nm em{font-size:.8em;opacity:.75}")
# 連買賣排行：控制列（日報／個股、當日／連續、投信／外資、族群、天數、?）全藏，只留圖本身；每邊前 7 列，只留「股票、連續天數、當日」三欄（截圖用頁面狀態，不改 site/）
STREAK_NAV = """(w) => { const c = (s) => { const b = document.querySelector(s); if (b) b.click(); };
  c('#instView button[data-v=streak]'); return new Promise(r => setTimeout(() => { c('#instMode button[data-m=today]');
    setTimeout(() => { c('#streakWho button[data-w=' + w + ']'); setTimeout(r, 900); }, 900); }, 900)); }"""
def STREAK_PIECE(name, story=False):
    return dict(name=name, title="盤後法人",
                css=STREAK_CSS + (".strank{display:grid!important;grid-template-columns:1fr!important;gap:14px!important}.itrow{padding-top:9px!important;padding-bottom:9px!important}" + STORY_Z(1.0) if story else ""),
                **({"fill_rows": ".itrow"} if story else {}))


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
  // a.split：多張獨立圖表，差額平分給每一張（不設＝每個選擇器都加滿，給「外框＋內層畫布」這種巢狀的用）
  // 卡片有 CSS zoom 或巢狀容器時，加 1px 不等於卡片長 1px → 量一次實際增量再修正（最多 3 輪），免得超高變成左右留白
  const found = a.charts.map(sel => el.querySelector(sel) || document.querySelector(sel)).filter(Boolean);
  const k = a.split ? Math.max(1, found.length) : 1;
  let gain = 1;
  for (let it = 0; it < 3; it++) {
    const h0 = el.getBoundingClientRect().height, need = a.want - h0;
    if (Math.abs(need) < 2) break;
    const step = need / gain / k;
    found.forEach(e => { const h = Math.max(120, Math.round((e.offsetHeight || e.getBoundingClientRect().height) + step));
      e.style.setProperty('height', h + 'px', 'important'); e.style.setProperty('min-height', h + 'px', 'important'); });
    const h1 = el.getBoundingClientRect().height;
    if (Math.abs(h1 - h0) > 1) gain = (h1 - h0) / (step * k); else break;
  }
  if (window.echarts) document.querySelectorAll('[_echarts_instance_]').forEach(e => { const c = echarts.getInstanceByDom(e); if (c) c.resize(); });
  window.dispatchEvent(new Event('resize'));
  return el.getBoundingClientRect().height;
}"""
STORY_HEAT_VW, STORY_HEAT_DSF = 700, 2.4     # 熱力圖限動版：窄桌機視窗（>640 仍是桌機版面），方塊變大、字放大後更清楚
# ★ 2026-10-28 盤中熱力圖被略過（data-snap-live=err）事故：
#   前端把熱力圖即時的「逾時」放寬到 150 秒且只在熱力圖看得到時計時；這裡等即時套上最多 LIVE_STATE_WAIT_S 秒（比前端多一點），
#   err 不再一看到就放棄（err 只代表「上一輪沒抓到」，下一輪抓到會自己變回 live）。
#   真的等不到即時：標了 close_fallback 的熱力圖退回「上一個交易日收盤」，圖上與文案都標日期，其他三張不受影響。
#   Andy 原話：「後續盤中 盤後也不能發生這樣的事情」。
LIVE_STATE_WAIT_S = 170


def live_state_step(state: str, elapsed_s: float, limit_s: float = LIVE_STATE_WAIT_S) -> str:
    """等即時套上的判斷（純函式，好測）：回 'ok'＝可以截、'wait'＝再等、'fail'＝等不到。
    live／close（非盤中或沒開即時，沿用舊行為）／空字串（這張卡沒有旗標，靠前面的 live_ok 判斷）＝ok；
    pending／err＝還沒好，等到期限才 fail（err 只代表上一輪沒抓到，下一輪抓到會自己變回 live）。"""
    if state in ("live", "close", ""):
        return "ok"
    return "fail" if elapsed_s >= limit_s else "wait"


def close_label(date_iso: str) -> str:
    """'2026-10-27' → '10/27 收盤'（熱力圖退回收盤時，圖上與文案的日期標示）。"""
    try:
        _, m, d = str(date_iso).split("-")
        return f"{int(m)}/{int(d)} 收盤"
    except Exception:  # noqa: BLE001
        return "上一個交易日收盤"


# 熱力圖退回收盤：把卡片的「即時」關掉（前端原地換回盤後資料、data-snap-live=close）。
# 日期標在合成圖標題列右側（compose 用 rec["close_label"] 取代「M/D 12:00」），不在卡片內插字（卡片換資料時會整塊重畫）。
CLOSE_FALLBACK_JS = """async (a) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const c = document.querySelector('[data-snap="' + a.n + '"]') || document.querySelector(a.card);
  if (!c) return false;
  if (window.Live && window.Live.setCard && window.Live.cardOn && window.Live.cardOn('heat')) window.Live.setCard('heat', false);
  await wait(1200);
  return true;
}"""
THREADS_HEAT_RATIO = 1.22   # Threads 熱力圖（產業＋題材）截圖高寬比：卡片內 1000×1220 左右
THREADS_MAX_H = 1350       # Threads 輪播圖高度上限（4:5）
STORY_RATIO = 1.40     # 限動截圖目標高寬比＝限動版型截圖區 1008×1776（2026-10-22 品牌列兼標題、拿掉右下網址後量的；舊值 1.6 會上下各空約 80px）
FILL_ROWS_JS = """([el, a]) => {   // 沒有圖表可拉高的片段（排行清單）：把差額平均加在每一列的上下內距，列距拉開到 a.want 高（不是拉伸點陣圖）
  for (let k = 0; k < 3; k++) {
    const rows = [...el.querySelectorAll(a.rows)].filter(e => e.offsetParent !== null);
    const delta = a.want - el.getBoundingClientRect().height;
    if (Math.abs(delta) < 2 || !rows.length) break;
    const z = (el.getBoundingClientRect().height / (el.offsetHeight || 1)) || 1;     // 卡片有 CSS zoom：內距是縮放前的 px
    // 兩欄並排時同一橫列只算一次
    const n = new Set(rows.map(e => Math.round(e.getBoundingClientRect().top))).size || rows.length;
    const add = delta / z / n / 2;
    rows.forEach(e => { const cs = getComputedStyle(e);
      e.style.setProperty('padding-top', Math.max(0, parseFloat(cs.paddingTop) + add) + 'px', 'important');
      e.style.setProperty('padding-bottom', Math.max(0, parseFloat(cs.paddingBottom) + add) + 'px', 'important'); });
  }
  return el.getBoundingClientRect().height;
}"""
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
SANKEY_STORY_VW, SANKEY_STORY_VH, SANKEY_STORY_DSF = 910, 1300, 1.3
SANKEY_STORY_COLS = [0.36, 0.70, 1.0]   # 限動版欄位比例（產業鏈／族群／代表股）：葉標籤右緣貼近卡片右內緣
SANKEY_STORY_SLOT_MAX = 46   # 限動版分流樹槽高上限（預設 42）：把樹拉高、節點間距變大（重畫），圖上下貼齊標題與下方兩塊   # 限動版分流樹：窄桌機視窗（手機 390 版的樹高寬比 1.86，放進卡片只佔內寬約 70%；桌機版面槽位較矮，重畫後比較接近卡片內寬比）
SANKEY_SCRUB = [["即時板塊合計.*", ""], ["\\s*[—-]\\s*\\(真實\\)", ""], ["\\s*盤後\\s*$", ""]]   # 根節點只留「台股成交值」；去掉「盤後」尾巴
SANKEY_PIECES = [dict(name="sankey-tree", sel="#sankeyWrap", title="資金分流樹", text="flows", root_sel="body",
                      
                      hide=["#sankeyLive", "#sankeyMotionBtn", ".ftbtn"], hide_exact=["~即時", "~^動態"], scrub=SANKEY_SCRUB)]
ENRICH_JS = """async ([logos, names]) => {   // 每列前面放公司 LOGO（沒有圖＝名稱首字的圓形字標），名稱＋代號完整不截斷；量出名稱欄與數字欄的實際寬度
  const COL = ['#3558c9', '#5b45c7', '#8a3fb0', '#1b6f99', '#9a5b12', '#4d5b73', '#7a5a3a', '#2f4f8f'];
  const color = (c) => { let h = 7; for (const ch of c) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return COL[h % COL.length]; };
  const SZ = 26, mk = (code, name) => { const w = document.createElement('span'); w.className = 'snaplg';
    w.style.cssText = 'display:inline-flex;flex:none;width:' + SZ + 'px;height:' + SZ + 'px;border-radius:50%;overflow:hidden;align-items:center;justify-content:center;background:' + color(code) + ';color:#fff;font:700 16px sans-serif';
    const letter = () => { w.textContent = Array.from((name || code).replace(/[\\s*＊\\-_.()（）]/g, ''))[0] || code[0]; w.style.background = color(code); };
    if (logos[code]) { const im = new Image(); im.width = SZ; im.height = SZ; im.style.cssText = 'width:100%;height:100%;object-fit:contain;background:#fff'; im.onerror = () => { im.remove(); letter(); }; im.src = logos[code]; w.appendChild(im); w._im = im; } else letter();
    return w; };
  const rows = [];
  document.querySelectorAll('.itrow[data-code]').forEach((r) => { const nm = r.querySelector('.nm'); if (!nm || nm.querySelector('.snaplg')) return; const code = r.dataset.code; const b = nm.querySelector('b');
    if (b && names[code] && (b.textContent.trim() === code || !b.textContent.trim())) b.textContent = names[code]; nm.insertBefore(mk(code, b ? b.textContent : ''), nm.firstChild); rows.push([r, nm, r.querySelector('.lots')]); });
  document.querySelectorAll('.mf-rk').forEach((r) => { const nm = r.querySelector('.mf-nm'); if (!nm || nm.querySelector('.snaplg')) return; const code = (/stock\\/(\\w+)/.exec(r.getAttribute('href') || '') || [])[1] || '';
    const m = /^(\\S+)\\s*(.*)$/.exec(nm.textContent.trim()) || []; const name = names[code] || m[2] || code; nm.innerHTML = ''; nm.appendChild(mk(code, name));
    const b = document.createElement('b'); b.textContent = name; const e = document.createElement('em'); e.textContent = code; nm.appendChild(b); nm.appendChild(e); rows.push([r, nm, r.querySelector('.mf-val')]); });
  await Promise.all(rows.map(([, nm]) => nm.querySelector('img') ? new Promise((ok) => { const im = nm.querySelector('img'); if (im.complete) ok(); else { im.addEventListener('load', ok); im.addEventListener('error', ok); setTimeout(ok, 8000); } }) : 0));
  rows.forEach(([, nm]) => { const im = nm.querySelector('.snaplg img'); if (im && !(im.complete && im.naturalWidth > 0)) im.dispatchEvent(new Event('error')); });   // 沒載到的圖一律退回字標，不留破圖示
  const zm = parseFloat(getComputedStyle(document.body).zoom) || 1;
  let nw = 0, lw = 0;
  rows.forEach(([r, nm, val]) => { const o = nm.style.cssText; nm.style.cssText += ';width:max-content!important;flex:none!important'; nw = Math.max(nw, nm.getBoundingClientRect().width / zm); nm.style.cssText = o;
    if (val) { const o2 = val.style.cssText; val.style.cssText += ';width:max-content!important;flex:none!important'; lw = Math.max(lw, val.getBoundingClientRect().width / zm); val.style.cssText = o2; } });
  const root = document.documentElement; root.style.setProperty('--nmw', Math.ceil(nw + 4) + 'px'); root.style.setProperty('--lw', Math.ceil(lw + 14) + 'px');
  return rows.length; }"""


CTRL_CSS = [".tlbar", "button:not(.hmcell)", "select", "input", "label:has(> input)", ".howbtn", ".seg", ".ovsum-nav", ".twms-btn", ".zreset", ".livetg", ".m4st", ":has(> select)", ".m3-bar"]
CTRL_TEXT = ["~^走勢$", "~^›$", "~^‹$", "~^\\d+\\s*/\\s*\\d+$"]
# 2026-10-26 Andy：「所有的備註都不要顯示、不包含來源」—— 社群圖上不准有資料來源、說明小字、註腳、免責小字；
# 免責與來源只放文案最後一行，估算用標題括號標（例：上市融資維持率（估））。每一片都套：
NOTE_CSS = [".howtxt", ".mf-part", ".mf-rd", ".mf-sub", ".mf-stale", ".stale-tag", ".fp-hint", ".fp-stale", ".fp-concl", ".disclaimer", ".disc", ".src-note", ".srcnote", ".note", ".foot", ".footnote", "small.muted", ".muted.small"]
NOTE_TEXT = ["~(資料來源|來源[：:]|^資料[：:]|僅供參考|不構成投資建議|免責|^註[：:]|^※|計算方式|怎麼看|部分估算|資料到這裡|資料自 ?\\d|資料日[：:])"]
NOTE_RE = r"資料來源|來源[：:]|^資料[：:]|僅供參考|不構成|投資建議|免責|^註[：:]|^※|計算方式|怎麼看|部分估算|估算|資料到這裡|資料日[：:]|資料未更新|更新於|截至\s*\d"
FIX_ECHARTS_JS = """(root) => { if (!window.echarts) return 0; let n = 0;   // 圖內畫布文字不含「即時」：軸名稱／標題裡的「・即時」拿掉（只改截圖瀏覽器）
  const fix = (v) => (typeof v === 'string' ? v.replace(/\\s*[・·]\\s*即時/g, '') : v);
  root.querySelectorAll('[_echarts_instance_]').forEach((e) => { const c = echarts.getInstanceByDom(e); if (!c) return; const o = c.getOption();
    const up = {}; ['xAxis', 'yAxis'].forEach((k) => { if (o[k]) up[k] = o[k].map((a) => (a.name && fix(a.name) !== a.name ? { name: fix(a.name) } : {})); });
    if (o.title) up.title = o.title.map((t) => ({ text: fix(t.text), subtext: fix(t.subtext) })); c.setOption(up); n++; });
  return n; }"""


def STORY_Z(z):
    return f"body{{zoom:{z}}}"


INST_CSS = (".mktstreakbar,.howtxt,.irgo,#instView,.howbtn,.irtri>.card:nth-child(n+2){display:none!important}.irtri{display:block!important}.irtop{margin-bottom:10px}")
INST_1M = "() => { const b = document.querySelector('#instPer button[data-p=\"1m\"]'); if (b && !b.disabled) b.click(); return new Promise(r => setTimeout(r, 1200)); }"
# 圖內 130% 線的說明字「130% 個別帳戶追繳線」只留「130%」（2026-10-26：圖上不放說明句；畫布內的字 DOM 掃不到，這裡直接改）
CREDIT_PRE = ("() => { const e = document.getElementById('mfChart'); const c = e && window.echarts && echarts.getInstanceByDom(e); if (!c) return 0;"
              " const o = c.getOption(); c.setOption({ series: o.series.map((x) => (x.markLine ? { markLine: Object.assign({}, x.markLine, { label: Object.assign({}, x.markLine.label || {}, { formatter: '130%' }) }) } : {})) }); return 1; }")
CREDIT_CSS = (".mf-bar,.mf-cseg,.mf-tiles,.mf-part,.mf-tblbox,.howbtn,.mf-big>.mf-l{display:none!important}.mf-split{display:block!important}.mf-cbox,.mf-cbox[data-c=bal],.mf-cbox[data-c=ratio]{display:block!important;width:100%!important}.mf-charts{width:100%!important}")
RANK_CSS = (".mf-bar,.mf-gsel,.howbtn,.howtxt,.mf-ranks>h4,.mf-rkhead{display:none!important}.mf-ranks{margin-top:0!important}.mf-rank,.mf-rk{min-width:0!important}.mf-rkgrid{grid-template-columns:minmax(0,1fr)!important}"
            ".mf-nm{display:flex!important;gap:8px;align-items:center;flex:0 0 var(--nmw,10em)!important;width:var(--nmw,10em)!important;overflow:visible!important}"
            ".mf-nm b,.mf-nm em{white-space:nowrap}.mf-nm em{font-size:.8em;opacity:.75;font-style:normal}.mf-rk{display:grid!important;grid-template-columns:22px var(--nmw,10em) minmax(0,1fr) max-content;gap:10px;align-items:center}.mf-sb{min-width:0!important}.mf-val{width:auto!important;white-space:nowrap;flex:none!important}.mf-nm{flex:none!important}")
FUT_CSS = ".fp-bar,.fp-per,.howbtn,.howtxt,.fp-tblcard,.fp-prodseg,.fp-hint,.fp-concl,.fp-top .sum{display:none!important}"
FUT_D = FUT_CSS + ".snapbar{order:2}.fp-split{display:block!important}.fp-main,.fp-split>.card{width:100%!important;max-width:none!important}"
RETAIL_CSS = (FUT_CSS + ".fp-hint,.fp-topgrid{display:none!important}.fp-hd{display:flex!important;flex-wrap:wrap;align-items:baseline;gap:4px 12px}"
              ".snapkpi{flex:1 1 100%}.snapkpi b{font:700 26px/1.3 'JetBrains Mono',monospace;margin-right:10px}.snapkpi small{font-size:15px;color:var(--ink-2)}"
              ".fp-split{display:block!important}.fp-main,.fp-split>.card{width:100%!important;max-width:none!important}")
RETAIL_D = RETAIL_CSS + ".fp-chart{height:230px!important;min-height:0!important}"
RETAIL_M = RETAIL_CSS + ".fp-chart{height:290px!important;min-height:0!important}"
_RET_INJECT = (" const T = (q) => document.querySelector(q); const tx = ((T('#fpTop .bignum') || {}).textContent || '').replace(/\\s+/g, ''); const m = /([+\\-\u2212])?([\\d.]+)%/.exec(tx);"
               " const dl = ((T('#fpTop .delta') || {}).textContent || '').replace(/\\s+/g, ' ').trim(); const sub = (T('#fpSub') || {}).textContent || '';"
               " const prod = (/(大台|小台|微台)（\\w+）/.exec(sub) || [''])[0]; const neg = !!m && m[1] && m[1] !== '+'; const val = m ? Number(m[2]) : 0;"
               " const old = T('.snapkpi'); if (old) old.remove(); const hd = T('.fp-main .fp-hd'); if (hd && m) { const e = document.createElement('div'); e.className = 'snapkpi';"
               " e.innerHTML = '<b style=\"color:' + (neg ? 'var(--fall)' : 'var(--rise)') + '\">' + (neg ? '\u2212' : '+') + m[2] + '%</b><small>' + prod + (dl ? '　' + dl.replace(/^最新一日散戶多空比/, '').replace(/較前一交易日/, '較前日').trim() : '') + '</small>';"
               " hd.appendChild(e); } window.__ret = { pct: m ? (neg ? '-' : '+') + m[2] + '%' : '', prod: (/(大台|小台|微台)/.exec(prod) || [''])[0] };")
RETAIL_VARIANTS = ["() => { const b = document.querySelector('#fpProdSeg button[data-p=%s]'); if (b) b.click(); return new Promise(r => setTimeout(r, 1500)).then(() => {" % k + _RET_INJECT + "}); }" for k in ("TX", "MTX", "TMF")]
def FUT_BARS(h):
    return ("async (el) => { const j = await (await fetch('data/fut_oi.json')).json(); const rev = j.order === 'desc'; const n = j.dates.length; const idx = [...Array(n).keys()]; if (rev) idx.reverse();"
            " const ds = idx.map(i => j.dates[i]).slice(-126); const mk = (k) => idx.map(i => { const o = j[k] || {}; return o.net && o.net[i] != null ? Number(o.net[i]) : (o.long && o.short ? o.long[i] - o.short[i] : null); }).slice(-126);"
            " const main = el.querySelector('.fp-main'); if (main) main.style.setProperty('display', 'none', 'important'); document.querySelectorAll('.snapbar').forEach(e => e.remove());"
            " const host = el.querySelector('.fp-split') || el;"
            " [['foreign', '外資'], ['trust', '投信'], ['dealer', '自營商']].forEach(([k, l]) => { const v = mk(k); const last = v[v.length - 1];"
            "  const c = document.createElement('div'); c.className = 'card snapbar'; c.style.cssText = 'padding:10px 12px;margin:0 0 10px;width:100%';"
            "  c.innerHTML = '<div style=\"display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px\"><b style=\"font-size:16px\">' + l + ' 每日淨未平倉（口）</b><b style=\"font:700 18px monospace;color:' + (last >= 0 ? '#c81234' : '#07794f') + '\">' + (last >= 0 ? '+' : '\u2212') + Math.abs(last).toLocaleString('en-US') + '</b></div><div class=\"snapch\" style=\"height:__H__px\"></div>';"
            "  host.appendChild(c); const ch = echarts.init(c.querySelector('.snapch'), null, { renderer: 'canvas' });"
            "  ch.setOption({ animation: false, grid: { left: 8, right: 8, top: 8, bottom: 22, containLabel: true }, xAxis: { type: 'category', data: ds, axisLabel: { color: '#5F5A51', fontSize: 11, hideOverlap: true, formatter: (x) => x.slice(5).replace('-', '/') }, axisTick: { show: false } },"
            "   yAxis: { type: 'value', axisLabel: { color: '#5F5A51', fontSize: 11, formatter: (x) => Math.abs(x) >= 10000 ? (x / 10000) + '萬' : x }, splitLine: { lineStyle: { color: '#E9E6DF' } } },"
            "   series: [{ type: 'bar', barMaxWidth: 8, data: v.map(x => ({ value: x, itemStyle: { color: x >= 0 ? '#c81234' : '#07794f' } })) }] }); }); return new Promise(r => setTimeout(r, 600)); }").replace('__H__', str(h))
READ_INST = "() => [...document.querySelectorAll('#instTiles .itile')].map(e => [(e.querySelector('.il') || {}).innerText || '', ((e.querySelector('.iv') || {}).innerText || '').replace(/\\s+/g, '')])"
READ_RANK = ("() => { const g = (s) => [...document.querySelectorAll('.srcol.' + s + ' .itrow[data-code] .nm b')].slice(0, 3).map(e => e.innerText.trim());"
             " return { buy: g('buy'), sell: g('sell') }; }")
READ_CREDIT = "() => { const t = document.querySelector('#mf-credit').innerText.replace(/\\s+/g, ' '); const a = /(\\d+\\.\\d+)\\s*%/.exec(t), b = /較前日\\s*([-+−]?\\s*[\\d.]+)\\s*pp/.exec(t); return { ratio: a && a[1], chg: b && b[1].replace(/\\s/g, '') }; }"
READ_RK = ("() => { const c = [...document.querySelectorAll('#mfRankBody > *')].map(e => [...e.querySelectorAll('.mf-rk, .mf-rkrow, li, tr')].slice(0, 3).map(r => r.innerText.replace(/\\s+/g, ' ').trim()));"
           " const nm = (k) => [...document.querySelectorAll('#mfRankBody .mf-rank:nth-child(' + k + ') a.mf-rk')].map(e => (e.getAttribute('href') || '').split('/').pop()).filter(Boolean);"
           " return { cols: c, up: nm(1), down: nm(2), raw: (document.querySelector('#mfRankBody') || {}).innerText || '' }; }")
READ_FUT = "() => ((document.querySelector('#fpBig3') || {}).innerText || '').replace(/\\s+/g, ' ').trim()"
READ_RET = "() => window.__ret || { pct: '', prod: '' }"
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
         parts=[dict(name="heat-industry", route="heatmap/industry", card="#indTreeWrap", closest_card=True, live="auto", live_ok=None, close_fallback=True,
                     hide=[".howbtn", ".livetg", ".tlbar"], fill=dict(frac=0.60, charts=["#indTreeWrap", "#indTree"])),
                dict(name="heat-theme", route="heatmap/theme", card="#themeMapCard", live="auto", live_ok=None, close_fallback=True, hide=[".howbtn", ".livetg", ".tlbar"], optional=True, fill=dict(frac=0.40, charts=["#themeMap"]))],
         live="auto", live_ok=None, headline=None, d=[dict(name="heat", title="資金熱力圖")], m=[]),
    # 2026-10-26 Andy：「大盤走勢 & 漲跌家數拿掉」→ kind="off"（保留設定，不發）
    dict(name="market-index", kind="off", label="大盤走勢（收盤全日）", route="overview", card="#m3Frame",
         live="#m3Frame .livetg-b",
         live_ok="() => { const b = document.querySelector('#m3Frame .livetg-b'); const f = document.querySelector('#m3Frame');"
                 " return !!b && !!f && (b.classList.contains('on') || b.getAttribute('aria-pressed') === 'true') && !/連不到|抓不到|失敗|逾時/.test(f.innerText); }",
         headline=None, d=[dict(name="market-index", hide=[".howbtn", ".mfilt", ".mpos", ".m4sico"], hide_exact=["~即時"])],
         m=[dict(name="market-index", hide=[".howbtn", ".mfilt", ".mpos", ".m4sico"], hide_exact=["~即時"], fill=dict(frac=1.0, charts=[".m3-chart", ".tv-lightweight-charts"]))]),
    dict(name="market-breadth", kind="off", label="漲跌家數", route="market/updown", card=".mktdist", closest_card=True,
         live="#mktMode button[data-m=live]",
         live_ok="() => { const n = document.querySelector('#mktLive');"
                 " return !!n && !n.hidden && !/抓取中|抓不到|失敗|逾時|連不到/.test(n.innerText); }",
         headline=None, d=[dict(name="market-breadth", hide=[".howbtn", "#distFilter", "#mktLive"], hide_exact=["~即時"])], m=[dict(name="market-breadth", hide=[".howbtn", "#distFilter", "#mktLive"], hide_exact=["~即時"], fill=dict(frac=1.0, charts=["#chgDistBox", "#chgDist"]))]),
    # 盤後（法人資料要收盤後證交所公布才有，沒有即時版，所以另一篇發，不放進盤中那篇）
    dict(name="inst-today", kind="close", label="三大法人買賣超", route="market/inst", card="[data-snap=inst-today]", attr_only=True,
         stale=".stale-tag", read=READ_INST, d=[dict(name="inst-today", sel="#instToday", css=INST_CSS, pre=INST_1M)],
         m=[dict(name="inst-today", sel="#instToday", css=INST_CSS + ".itile .iv{font-size:19px!important}", pre=INST_1M, fill=dict(frac=1.0, charts=["#instBars"]))], story_vw=720, story_dsf=2.0),
    dict(name="streak-foreign", kind="close", label="外資個股買賣超排名", route="market/inst", card="#mktBody", closest_card=True, nav=STREAK_NAV, nav_arg="foreign",
         stale=".stale-tag", read=READ_RANK, story_vw=720, story_dsf=2.0,
         d=[STREAK_PIECE("streak-foreign")], m=[STREAK_PIECE("streak-foreign", True)]),
    dict(name="streak-trust", kind="close", label="投信個股買賣超排名", route="market/inst", card="#mktBody", closest_card=True, nav=STREAK_NAV, nav_arg="trust",
         stale=".stale-tag", read=READ_RANK, story_vw=720, story_dsf=2.0,
         d=[STREAK_PIECE("streak-trust")], m=[STREAK_PIECE("streak-trust", True)]),
    # 盤後融資（kind=credit，2026-10-21 從盤後法人那篇拆出來）：融資資料比三大法人晚很多才到齊 ——
    # 整體市場融資（FinMind）約台北 21:30～22:00 才有當天、上市個股融資（證交所 openapi＋FinMind 逐檔）要到隔天清晨。
    # 跟法人綁同一篇時，法人一到（16:15～17:15）那篇就發掉、當天標成已發，融資卡永遠是「資料未更新」被略過。
    # 拆開後各自把關：這篇只在 market_fut.json 的融資資料日＝網站最新交易日、維持率算得出來、個股排行也是同一天時才發（credit_ready）。
    dict(name="credit-ratio", snap="margin", kind="credit", label="融資維持率", route="market/credit", card="#mf-credit", attr_only=True, stale=".mf-stale", read=READ_CREDIT,
         story_vw=720, story_dsf=2.0, d=[dict(name="credit-ratio", sel="#mf-credit", css=CREDIT_CSS, pre=CREDIT_PRE)],
         m=[dict(name="credit-ratio", sel="#mf-credit", css=CREDIT_CSS + STORY_Z(1.2), pre=CREDIT_PRE, fill=dict(frac=1.0, charts=["#mfChart", "#mfChart2"], split=True))]),
    dict(name="credit-rank", snap="margin", kind="credit", label="融資增減排行", route="market/credit", card="#mf-credit", attr_only=True, stale=".mf-stale", read=READ_RK,
         nav="() => { const b = document.querySelector('#mfTab button[data-k=rank]'); if (b) b.click(); return new Promise(r => setTimeout(r, 1200)); }",
         story_vw=720, story_dsf=2.0, d=[dict(name="credit-rank", sel="#mf-credit", css=RANK_CSS)], m=[dict(name="credit-rank", sel="#mf-credit", css=RANK_CSS + ".mf-rkgrid{grid-template-columns:minmax(0,1fr)!important;gap:26px!important}" + STORY_Z(1.3), fill_rows=".mf-rk")]),
    # 融券增減排行（2026-10-26 Andy：「需要新增一個融券的」）：同一頁「個股排行」分頁的「融券」分段，版面同融資增減排行
    dict(name="credit-short", snap="margin", kind="credit", label="融券增減排行", route="market/credit", card="#mf-credit", attr_only=True, stale=".mf-stale", read=READ_RK,
         nav="() => { const b = document.querySelector('#mfTab button[data-k=rank]'); if (b) b.click(); return new Promise(r => setTimeout(() => { const s = document.querySelector('#mfRkSeg button[data-k=short]:not([disabled])'); if (s) s.click(); setTimeout(() => r(!!s), 1000); }, 1000)); }",
         need_nav=True,
         story_vw=720, story_dsf=2.0, d=[dict(name="credit-short", sel="#mf-credit", css=RANK_CSS)], m=[dict(name="credit-short", sel="#mf-credit", css=RANK_CSS + ".mf-rkgrid{grid-template-columns:minmax(0,1fr)!important;gap:26px!important}" + STORY_Z(1.3), fill_rows=".mf-rk")]),
    dict(name="fut-oi", snap="fut-oi", kind="close", label="台指期三大法人未平倉", route="market/fut", card="[data-snap=fut-oi]", attr_only=True, stale=".fp-stale:not([hidden])", read=READ_FUT,
         story_vw=720, story_dsf=2.0, d=[dict(name="fut-oi", sel=".fp-block", css=FUT_D, pre=FUT_BARS(150))],
         m=[dict(name="fut-oi", sel=".fp-block", css=FUT_CSS + ".snapbar{order:2}.fp-split{display:block!important}", pre=FUT_BARS(260))]),
    dict(name="retail-ratio", snap="fut-oi", kind="close", label="台指散戶多空比", route="market/fut", card="[data-snap=fut-oi]", attr_only=True, stale=".fp-stale:not([hidden])",
         nav="() => { const b = document.querySelector('.fp-prod button[data-k=retail]'); if (b) b.click(); return new Promise(r => setTimeout(r, 1200)); }",
         story_vw=720, story_dsf=2.0, d=[dict(name="retail-ratio", sel=".fp-block", css=RETAIL_D, variants=RETAIL_VARIANTS, read=READ_RET)],
         m=[dict(name="retail-ratio", sel=".fp-block", css=RETAIL_M, variants=RETAIL_VARIANTS, read=READ_RET)]),
]

# 每張的標題＝功能名稱本身（Andy 10-20：「標題就是這功能」），副標是小字；全部畫面與貼文不出現「即時」字樣
PIECE_META = {
    "rotation-wheel": ("資金輪盤", "族群在哪個象限"),
    "rotation-rank": ("族群資金排行", "各族群資金占比變化（pp）"),
    "sankey-tree": ("資金分流樹", "成交值依產業鏈流向族群"),
    "heat": ("資金熱力圖", "產業一次看（上）、題材資金熱力（下）"),
    "market-index": ("大盤走勢", "加權指數、櫃買指數、台指期"),
    "market-breadth": ("漲跌家數", "全市場漲跌分佈"),
    "inst-today": ("三大法人買賣超 {d}", ""),
    "streak-foreign": ("外資個股買賣超排名 {d}", ""),
    "streak-trust": ("投信個股買賣超排名 {d}", ""),
    "credit-ratio": ("上市融資維持率（估） {d}", ""),      # 估算標在標題括號（2026-10-26：圖上不放說明句）
    "credit-rank": ("融資增減排行 {d}", ""),
    "credit-short": ("融券增減排行 {d}", ""),
    "fut-oi": ("台指期三大法人未平倉 {d}", ""),
    "retail-ratio": ("台指散戶多空比 {d}", ""),
}
PIECE_META = {k: (v[0], "") for k, v in PIECE_META.items()}      # 標題下的操作說明小字一律不放
# 版型配色：直接取自 site/index.html 的 CSS 變數（淺色 :root[data-theme=light]、深色 :root）
import social_theme as TH   # 2026-10-26：版型色票與標題列抽到 social_theme.py（亮色 HUD，規範 docs/marketing/social_unit/post_design_system.md）
FRAME = {
    "light": dict(TH.TOKENS),
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
        return json.loads(_get(f"{root}/data/meta.json?_={int(time.time())}", 20).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log("讀不到 meta.json：", exc)
        return {}


def fetch_json(base: str, name: str) -> dict:
    """讀網站的 data/<name>.json；讀不到回 {}。"""
    root = base.rsplit("/", 1)[0] if base.endswith(".html") else base.rstrip("/")
    try:
        return json.loads(_get(f"{root}/data/{name}.json?_={int(time.time())}", 30).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log(f"讀不到 {name}.json：", exc)
        return {}


# 2026-10-26 Andy：「盤後 Threads 7 張 & 融資融券 Threads 3 張應該是要一起的」→ 盤後一篇＝法人卡＋融資融券卡
KIND_SET = {"close": ("close",),      # 2026-10-27 Andy：融資維持率與融資融券排行移到隔天盤前（scripts/social_premarket.py）
             "credit": ("credit",), "intraday": ("intraday",)}


def credit_ready(meta: dict, mf: dict) -> tuple[bool, str, str]:
    """盤後融資那篇能不能發：回 (能不能, 融資資料日, 不能的原因)。

    四個條件都要成立（「資料到齊」的定義）：
      1. market_fut.json 的融資最後一天 d ＝ 網站最新交易日（meta.data_date）—— 不是就代表整體市場融資還沒更新到當天；
      2. 那天的維持率算得出來（ratio 不是空的）—— 上市個股融資還沒到，分子算不出來；
      3. 那天不是「部分估算」（partial）—— 個股融資只到一部分，數字還會變；
      4. 個股融資增減排行（rank.d）與融券增減排行（short_rank.d）也是同一天 —— 不然第二、三張圖是前一天的。
    另外 main() 再用 social_gate.credit_gate 卡時間：只在資料日收盤後、下一個交易日 09:00 開盤前發（過了就不發舊的）。
    用網站最新交易日比、不用「今天」：個股融資常到隔天清晨才齊，那時網站最新交易日仍是前一天，照樣可以發；
    等隔天 15:30 價量進來、最新交易日換天，前一天的融資就不再發（不拿舊資料冒充）。
    """
    m = (mf or {}).get("margin") or {}
    rows = m.get("rows") or []
    if not rows:
        return False, "", "market_fut.json 沒有融資資料"
    last = rows[-1]
    d = str(last.get("d") or "")[:10]
    latest = str(meta.get("data_date") or "")[:10]
    if not latest:
        return False, d, "meta.json 沒有 data_date"
    if d != latest:
        return False, d, f"融資資料日 {d} ≠ 網站最新交易日 {latest}（整體市場融資還沒更新）"
    if last.get("ratio") is None:
        return False, d, f"{d} 的融資維持率還算不出來（上市個股融資還沒到）"
    if last.get("partial"):
        return False, d, f"{d} 的個股融資只到一部分（部分估算）"
    rk = str((m.get("rank") or {}).get("d") or "")[:10]
    if rk != d:
        return False, d, f"融資增減排行的資料日 {rk or '—'} ≠ {d}"
    sr = str((m.get("short_rank") or {}).get("d") or "")[:10]
    if sr != d:      # 2026-10-26 第三張「融券增減排行」：也要同一天
        return False, d, f"融券增減排行的資料日 {sr or '—'} ≠ {d}"
    return True, d, ""


def slot_key_for(kind: str, data_date: str, taken_at: str, supplement: bool = False) -> str:
    """發布紀錄的時段鍵（跟 scripts/social_publish.py 的 slot_key 同一套規則）。"""
    if kind == "close" and supplement:      # 盤後保底後的法人補充貼文（2026-10-29）：另一個鍵，不會重發主貼文
        return f"close-inst-{(data_date or taken_at)[:10]}"
    if kind == "close":      # 合併後以資料日為鍵（可能隔天清晨才發）
        return f"close-{(data_date or taken_at)[:10]}"
    if kind == "credit":
        return f"credit-{data_date[:10]}"
    if kind == "intraday":      # 盤中一天一篇（台北 12:00），跟 social_publish.slot_key 一致
        return f"intraday-{taken_at[:10]}"
    return f"{kind}-{taken_at[:10]}-{taken_at[11:13]}"


def posted_ok(key: str, rec) -> bool:
    """發布紀錄算不算數（2026-10-27 事故：凌晨測試寫進 intraday-2026-10-27，12:00 正式盤中被當成已發過）。
    紀錄有 at（台北發布時間）時，盤中必須在當天 09:00～13:30、盤前必須在當天 05:00 之後才算；
    舊紀錄沒有 at 照舊算已發過（避免重發）。"""
    at = (rec or {}).get("at") if isinstance(rec, dict) else None
    if not at:
        return True
    day, hm = key.split("-", 1)[1][:10], at[11:16]
    if key.startswith("intraday-"):
        return at[:10] == day and "09:00" <= hm <= "13:30"
    if key.startswith("premarket-"):
        return at[:10] == day and hm >= "05:00"
    return True


def _get(url: str, timeout: int = 40) -> bytes:
    from urllib.request import Request
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (tw-rotation social_snap)", "Accept": "application/json,*/*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def sync_data(site_dir: Path, data_url: str) -> bool:
    """把網站會讀的 JSON 從正式站抓到本機 site/data/（名稱從 site/*.js 的 load('名稱') 與 data/xxx.json 掃出來）。
    data_url 可用逗號放多個候選網址（依序試，第一個抓得到 meta.json 的當來源）。
    meta.json 抓不到＝回 False（呼叫端要中止，不然後面全部逾時）。"""
    names = set()
    for f in site_dir.glob("*.js"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        names |= set(re.findall(r"load\(\s*'([a-z0-9_]+)'", txt))
        names |= {m for m in re.findall(r"data/([a-z0-9_]+)\.json", txt)}
    names.add("meta")
    dst = site_dir / "data"
    dst.mkdir(exist_ok=True)
    cands = [u.strip().rstrip("/") for u in data_url.split(",") if u.strip()]
    src = ""
    for c in cands:
        try:
            (dst / "meta.json").write_bytes(_get(f"{c}/meta.json?_={int(time.time())}", 20))
            src = c
            global DATA_SRC
            DATA_SRC = c
            log(f"資料來源採用 {c}")
            break
        except Exception as exc:  # noqa: BLE001
            log(f"資料來源 {c}/meta.json 失敗：{exc}")
    if not src:
        log("所有候選資料網址都讀不到 meta.json：", cands)
        return False
    ok, miss = 0, []
    for n in sorted(names):
        url = f"{src}/{n}.json?_={int(time.time())}"
        try:
            (dst / f"{n}.json").write_bytes(_get(url))
            ok += 1
        except Exception as exc:  # noqa: BLE001
            miss.append(n)
            log(f"  下載失敗 {n}.json ← {url.split('?')[0]}：{exc}")     # 沒有的檔頁面本來就有 fallback
    log(f"下載網站資料 {ok}/{len(names)} 份 ← {src}")
    return True


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


def diag(pg, t: dict) -> str:
    """略過某張時把頁面狀態印出來（雲端 log 才查得到為什麼）。"""
    try:
        return json.dumps(pg.evaluate("""(a) => { const c = document.querySelector(a.card) || document.querySelector('[data-snap="' + a.n + '"]');
            const lv = document.querySelector(a.live || '.livetg');
            return { card: !!c, snapLive: c && c.getAttribute('data-snap-live'), liveBtn: lv ? [lv.className, lv.getAttribute('aria-pressed'), (lv.innerText || '').trim()] : null,
                     text: c ? (c.innerText || '').replace(/\\s+/g, ' ').slice(0, 160) : '' }; }""", {"card": t["card"], "n": t.get("snap", t["name"]), "live": t.get("live") if t.get("live") != "auto" else None}), ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return f"diag 失敗 {exc}"


def go_target(pg, base: str, t: dict) -> None:
    if t.get("kind") in ("close", "credit"):      # 盤後各頁共用同一個單頁應用：先清空再進，免得上一張塞的樣式與頁內狀態帶過來
        pg.goto("about:blank")
    pg.goto(f"{base}#{t['route']}", wait_until="networkidle")
    pg.wait_for_timeout(2500)


SNAP_READY_ALIAS = {"rotation": "rot-wheel", "sankey": "flow-tree", "streak-trust": "market-streak",
                    "streak-foreign": "market-streak", "streak-total": "market-streak"}


def wait_snap_ready(pg, name: str, timeout_ms: int) -> bool:
    """若頁面有 window.TwSnapReady（frontend-ui 提供），等它回 true；沒有就當作 true。"""
    has = pg.evaluate("() => typeof window.TwSnapReady === 'function'")
    if not has:
        return True
    # 本程式的目標名稱 ≠ site/snap.js MAP 的名稱（例：streak-trust → market-streak）：先換成 snap.js 認得的名稱；
    # snap.js 沒有對應（或頁面上沒標出來）就不用它判斷，改靠截圖前的固定等待，免得永遠逾時
    name = SNAP_READY_ALIAS.get(name, name)
    known = pg.evaluate("() => (window.TwSnapList ? window.TwSnapList() : [])")
    if name not in known:
        log(f"  TwSnapReady 沒有「{name}」可判斷（頁面標記 {known}）→ 略過就緒判斷")
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
    # 站主即時預設已開：有的鈕用 aria-pressed、有的用 class「on」表示開著（熱力圖、大盤走勢）；已開就不要再按，免得被按成關
    already = (b.get_attribute("aria-pressed") or "") == "true" or "on" in (b.get_attribute("class") or "").split()
    if not already:
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
                    return !!b && (b.getAttribute('aria-pressed') === 'true' || b.classList.contains('on')) && !/抓不到|失敗|逾時/.test(c.innerText);
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
NOTE_SCAN_JS = """([root, rx]) => {   // 掃畫面上看得到的 DOM 文字有沒有備註／來源／免責（畫布內的字掃不到）
  const re = new RegExp(rx), out = [], w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = w.nextNode())) {
    const v = (t.nodeValue || '').trim();
    if (!v || !re.test(v)) continue;
    const e = t.parentElement;
    if (!e || !e.getClientRects().length || e.closest('[data-snap-hid]')) continue;
    const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    out.push(v.slice(0, 40) + ' @' + e.tagName + '.' + (e.className.baseVal ?? e.className));
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


def data_dates(serve: Path | None = None, reader=None) -> dict:
    """各張卡片自己的資料日（YYYY-MM-DD）：直接讀資料檔裡那份資料自己的最後一天，不借 meta 或執行日。

    serve＝本機 site 資料夾（讀 data/*.json）；reader＝讀不到本機時改用的函式 name -> dict（例如從網站抓）。
    圖上標題的日期、文案日期、manifest 的 data_date 都從這裡來，三者一致（2026-10-26：10/22 那篇文案寫 10/22、數字是 10/21）。
    """
    d = (serve / "data") if serve else None
    out = {}

    def rd(name):
        try:
            if d is not None and (d / name).exists():
                return json.loads((d / name).read_text("utf-8"))
            return reader(name[:-5]) if reader else None
        except Exception:  # noqa: BLE001
            return None

    def iso(x):
        return gate._iso(x)
    j = rd("inst_market.json")
    if j and j.get("rows"):
        out["inst-today"] = iso(j["rows"][-1].get("d"))
    j = rd("inst_today.json")
    if j and j.get("date"):
        out["streak-foreign"] = out["streak-trust"] = iso(j["date"])
    j = rd("market_fut.json")
    if j and (j.get("margin") or {}).get("rows"):
        # 維持率卡標的是「維持率有值的最後一天」（個股融資沒到齊的那天前端會退回前一個有值的日子）；排行卡標排行自己的日子
        rs = j["margin"]["rows"]
        out["credit-ratio"] = iso(next((r.get("d") for r in reversed(rs) if r.get("ratio") is not None), rs[-1].get("d")))
        out["credit-rank"] = iso((j["margin"].get("rank") or {}).get("d") or rs[-1].get("d"))
        if (j["margin"].get("short_rank") or {}).get("d"):
            out["credit-short"] = iso(j["margin"]["short_rank"]["d"])
    j = rd("index_intraday.json")      # 大盤走勢（收盤全日）：加權指數最後一根分 K 的日期
    try:
        if j and (j.get("TSE") or {}).get("M15"):
            from datetime import datetime as _dt
            out["market-index"] = _dt.fromtimestamp(j["TSE"]["M15"][-1][0], TPE).date().isoformat()
    except Exception:  # noqa: BLE001
        pass
    j = rd("meta.json")                # 漲跌家數：updown.json 沒帶日期，用 meta 的最新價量日
    if j and j.get("price_latest"):
        out["market-breadth"] = iso(j["price_latest"])
    j = rd("fut_oi.json")
    if j and j.get("dates"):
        out["fut-oi"] = iso(max(j["dates"]))
    j = rd("retail_ratio.json")
    if j:
        ds = [x for o in (j.get("products") or {}).values() for x in (o.get("dates") or [])] or (j.get("dates") or [])
        if ds:
            out["retail-ratio"] = iso(max(ds))
    return {k: v for k, v in out.items() if v}


def mmdd(x: str) -> str:
    return str(x)[5:10].replace("-", "/") if x else ""


def _shoot_one(pg, card_el, pc: dict, raw_dir: Path, mode: str, dsf: float) -> dict:
    """截一片。mode＝'d'（桌機）或 'm'（手機）。有 sel 就只截那個元素；沒有 sel：桌機整張卡、手機依 start/end 切（連買賣、熱力圖）。"""
    pg.evaluate(UNHIDE_JS)
    tgt = pg.query_selector(pc["sel"]) if pc.get("sel") else card_el
    if tgt is None:
        raise RuntimeError(f"找不到 {pc.get('sel')}")
    pg.evaluate("() => { const o = document.getElementById('snapcss'); if (o) o.remove(); if (!document.getElementById('snapbr')) { const e = document.createElement('style'); e.id = 'snapbr';"
                " e.textContent = '[data-theme4] .card,[data-theme4] .card::before,[data-theme4] .card::after{background-image:none!important}'; document.head.appendChild(e); } }")   # 網站卡片自帶的四角括角截圖時藏掉（貼文版型自己有括角，不要雙層）
    if pc.get("css"):     # 截圖用：只在這個瀏覽器分頁塞樣式藏控制列、調欄位，不改 site/
        pg.evaluate("(c) => { const e = document.createElement('style'); e.id = 'snapcss'; e.textContent = c; document.head.appendChild(e); window.dispatchEvent(new Event('resize'));"
                    " if (window.echarts) document.querySelectorAll('[_echarts_instance_]').forEach(x => { const i = echarts.getInstanceByDom(x); if (i) i.resize(); }); }", pc["css"])
        pg.wait_for_timeout(900)
    if tgt.query_selector(".itrow[data-code], .mf-rk"):
        pg.evaluate(ENRICH_JS, [LOGO_MAP, NAME_MAP])
        pg.wait_for_timeout(500)
    if pc.get("pre"):
        pg.evaluate(pc["pre"], tgt)
        pg.wait_for_timeout(900)
        if pc.get("sel"):      # pre 可能讓頁面重畫（換期間），舊的元素失效 → 重抓
            tgt = pg.query_selector(pc["sel"]) or tgt
    ctrl = [] if pc.get("css") else CTRL_CSS      # 盤中各卡：控制項（鈕、下拉、分段鈕、頁籤、分頁點、放大）一律不進圖；盤後各卡已用 css 自己處理
    pg.evaluate(FIX_ECHARTS_JS, tgt)
    pg.evaluate(HIDE_JS, [pg.query_selector(pc["root_sel"]) if pc.get("root_sel") else tgt, {"css": pc.get("hide", []) + ctrl + NOTE_CSS + [".zbadge", ".echarts-tooltip"], "text": pc.get("hide_text", []), "exact": pc.get("hide_exact", []) + NOTE_TEXT + ([] if pc.get("css") else CTRL_TEXT), "scrub": pc.get("scrub", [])}])
    pg.evaluate("() => { if (window.echarts) document.querySelectorAll('[_echarts_instance_]').forEach(e => { const c = echarts.getInstanceByDom(e); if (c) c.dispatchAction({ type: 'hideTip' }); }); }")
    if mode == "m" and pc.get("fill"):
        bb = tgt.bounding_box()
        pg.evaluate(FILL_JS, [tgt, {"want": bb["width"] * STORY_RATIO * pc["fill"]["frac"], "charts": pc["fill"]["charts"], "split": pc["fill"].get("split", False)}])
        pg.wait_for_timeout(1200)
    if mode == "m" and pc.get("fill_rows"):
        bb = tgt.bounding_box()
        pg.evaluate(FILL_ROWS_JS, [tgt, {"want": bb["width"] * STORY_RATIO, "rows": pc["fill_rows"]}])
        pg.wait_for_timeout(600)
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
    notes = pg.evaluate(NOTE_SCAN_JS, [tgt, NOTE_RE])      # 備註／來源／免責字樣（2026-10-26）：有就不准發
    texts = [x.strip() for x in (tgt.evaluate("e => e.innerText") or "").split("\n") if x.strip()]
    dump = {}
    if mode == "d" and pc["name"] in NAT.DUMP_JS:      # 原生繪製要的資料：在套上即時資料的頁面上讀（截圖之後才讀，免得點分頁改到截圖）
        try:
            dump = pg.evaluate(NAT.DUMP_JS[pc["name"]]) or {}
        except Exception as exc:  # noqa: BLE001
            log("  讀不到原生繪製資料", pc["name"], str(exc)[:80])
    return {"texts": texts, "jishi": jishi, "notes": notes, "name": pc["name"], "raw": str(path), "dsf": dsf, "min_css_font": minpx, "title": pc.get("title", ""), "text": pc.get("text"), "dump": dump}


def shoot_piece(pg, card_el, pc: dict, raw_dir: Path, mode: str, dsf: float) -> dict:
    """有 variants（例：大台／小台／微台）就每個變體各截一張再由上到下疊成一張。"""
    if not pc.get("variants"):
        return _shoot_one(pg, card_el, pc, raw_dir, mode, dsf)
    from PIL import Image
    recs, reads = [], []
    for i, js in enumerate(pc["variants"]):
        pg.evaluate(js)
        sub = dict(pc, name=f"{pc['name']}_v{i}", variants=None)
        recs.append(_shoot_one(pg, card_el, sub, raw_dir, mode, dsf))
        if pc.get("read"):
            reads.append(pg.evaluate(pc["read"]))
    ims = [Image.open(r["raw"]).convert("RGB") for r in recs]
    W = max(i.width for i in ims)
    gap = int(10 * dsf)
    sheet = Image.new("RGB", (W, sum(i.height for i in ims) + gap * (len(ims) - 1)), (255, 255, 255))
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height + gap
    path = raw_dir / f"{mode}_{pc['name']}.png"
    sheet.save(path)
    return {"texts": [x for r in recs for x in r.get("texts", [])], "jishi": [x for r in recs for x in r["jishi"]], "notes": [x for r in recs for x in r.get("notes", [])], "name": pc["name"], "raw": str(path), "dsf": dsf,
            "min_css_font": min(r["min_css_font"] for r in recs), "title": pc.get("title", ""), "text": None, "reads": reads}


def snap_targets(args, base: str, out: Path, today_ymd: str) -> tuple[list[dict], dict]:
    """每個目標：桌機寬截片段（Threads 用）＋手機版面截片段（IG 限動用）。"""
    from playwright.sync_api import sync_playwright
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []
    sniff = {"quote_dates": set(), "errors": []}
    wanted = [t for t in TARGETS if t["kind"] in KIND_SET[args.kind] and (not args.only or t["name"] in args.only.split(","))]
    attr_mode = "only" if args.use_snap_attr else ("never" if args.no_snap_attr else "prefer")
    m_dsf = 1080 / 374.0          # 手機卡片寬 374 css px（390 − 左右各 8）→ 輸出剛好 1080 寬

    def snap_live_state(pg, t):
        return pg.evaluate("""(n) => { const e = document.querySelector('[data-snap="' + n + '"]'); const h = e && (e.closest('[data-snap-live]') || e);
                                     return (h && h.getAttribute('data-snap-live')) || ''; }""", t.get("snap", t["name"]))

    def fallback_close(pg, t, info, el, why=""):
        """即時等不到 → 熱力圖退回上一個交易日收盤（圖上標日期）。回傳要截的元素；不能退就回 None。"""
        lbl = close_label(DATE_ISO.get("market-index") or DATE_ISO.get("inst-today") or "")
        ok_ = pg.evaluate(CLOSE_FALLBACK_JS, {"n": t.get("snap", t["name"]), "card": t["card"]})
        if not ok_:
            return None
        pg.wait_for_timeout(1500)
        info["close_label"] = lbl
        log("  ⚠", t["name"], (why or f"即時等了 {LIVE_STATE_WAIT_S} 秒仍沒套上") + f" → 退回 {lbl}（圖上標日期），其他張不受影響")
        pg.evaluate(HIDE_FLOATING_JS, t["card"])
        pg.wait_for_timeout(300)
        return resolve_target(pg, t, attr_mode) or el

    def prepare(pg, t, info, close_mode=False):
        go_target(pg, base, t)
        el = resolve_target(pg, t, attr_mode)
        if el is None:
            info["why"] = "找不到目標元素（頁面上沒有）→ 跳過"
            return None
        if t.get("nav"):
            nav_ok = pg.evaluate(t["nav"], t.get("nav_arg"))
            pg.wait_for_timeout(1200)
            if t.get("need_nav") and not nav_ok:
                info["why"] = "頁面上沒有這個分段（例如融券排行還沒產出）→ 跳過"
                return None
        if args.kind in ("close", "credit") and t.get("stale") and not args.force and pg.evaluate("(q) => [...document.querySelectorAll(q)].some(e => e.offsetParent !== null)", t["stale"]):
            info["why"] = "頁面標示「資料未更新」（資料日不是最近交易日）→ 不發"
            return None
        if close_mode:      # 同一張熱力圖前半已退回收盤：後半也用收盤（兩半口徑一致），不再切即時
            return fallback_close(pg, t, info, el, "同一張熱力圖已退回收盤，這半口徑一致")
        if args.kind == "intraday" and not (args.skip_live == "all" or t["name"] in args.skip_live.split(",")):
            if not click_live(pg, t, el):
                info["why"] = "沒有即時鈕（這張還不能即時）→ 不發"
                log("  ✗", t["name"], info["why"], diag(pg, t))
                return None
            if not live_confirmed(pg, t, args):
                if t.get("close_fallback") and not args.no_close_fallback:
                    return fallback_close(pg, t, info, el)
                info["why"] = "即時沒套上（抓不到報價）→ 不發"
                log("  ✗", t["name"], info["why"], diag(pg, t))
                return None
        live_t = args.kind == "intraday" and not (args.skip_live == "all" or t["name"] in args.skip_live.split(","))
        t0 = time.time()      # 等即時的總時間從這裡算（TwSnapReady 與下面 data-snap-live 等待合計，不重複累加）
        if not wait_snap_ready(pg, t.get("snap", t["name"]), 80000 if args.kind == "intraday" else 20000):
            if not (live_t and t.get("close_fallback")):      # 熱力圖：交給下面的 data-snap-live 等待（等滿 LIVE_STATE_WAIT_S 秒才退回收盤）
                info["why"] = "TwSnapReady 逾時 → 不發"
                log("  ✗", t["name"], info["why"], diag(pg, t))
                return None
        if live_t:
            # 2026-10-28：err 不再一看到就放棄 —— 等到 live（最多 LIVE_STATE_WAIT_S 秒）；等不到才退回收盤或略過，不拿舊圖冒充即時
            while True:
                st = snap_live_state(pg, t)
                step = live_state_step(st, time.time() - t0)
                if step != "wait":
                    break
                pg.wait_for_timeout(2000)
            if step == "fail":
                log("  ✗", t["name"], f"data-snap-live={st or '（無）'}，等了 {int(time.time() - t0)} 秒", diag(pg, t))
                if t.get("close_fallback") and not args.no_close_fallback:
                    return fallback_close(pg, t, info, el)
                info["why"] = f"data-snap-live={st or '（無）'}（即時抓不到）→ 不發"
                return None
            if st == "live" and int(time.time() - t0) > 3:
                log(f"  {t['name']} 即時套上（多等了 {int(time.time() - t0)} 秒）")
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
                        cm = bool(info.get("close_label"))
                        pel = prepare(pg, part, pinfo, cm) or prepare(pg, part, pinfo, cm)      # 即時偶爾第一次沒套上：重進一次
                        if pel is not None and pinfo.get("close_label"):
                            info["close_label"] = pinfo["close_label"]
                        if pel is None:
                            if part.get("optional") and recs:      # 題材那半抓不到即時就只發產業那半（不拿收盤圖冒充）
                                log("  ⚠", part["name"], "即時沒套上 → 這張只放產業熱力圖：", pinfo.get("why"))
                                continue
                            info["why"] = f"{part['name']}：{pinfo.get('why')}"
                            recs = []
                            break
                        info.setdefault("heat_parts", []).append(part["name"])
                        try:      # Threads 滿版：產業＋題材兩張合起來拉成 1000×1230 的比例（重畫圖表、非拉伸），跟限動同一招
                            bbw = pel.bounding_box()["width"]
                            pg.evaluate(FILL_JS, [pel, {"want": bbw * THREADS_HEAT_RATIO * part["fill"]["frac"] - 8, "charts": part["fill"]["charts"]}])
                            pg.wait_for_timeout(1200)
                        except Exception as exc_:  # noqa: BLE001
                            log("  熱力圖 Threads 版拉高失敗，用原高度：", str(exc_)[:80])
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
                               "title": t["label"], "text": None, "jishi": [x for r in recs for x in r["jishi"]], "texts": [x for r in recs for x in r.get("texts", [])]}
                        if info.get("close_label"):
                            rec["close_label"] = info["close_label"]      # 標題列右側改寫「M/D 收盤」，不寫「12:00」
                        info["pieces_d"] = [rec]
                        info["pieces_m"] = [dict(rec)]       # 限動也用這張直式疊放的圖（等比放大填滿寬度）
                        info["ok"] = True
                        log("桌機截到", t["name"], "（產業＋題材合成）")
                    shots.append(info)
                    continue
                el = prepare(pg, t, info) or prepare(pg, t, info)
                if el is not None:
                    info["headline"] = read_headline(el, t)
                    for pc in (t.get("d") or [dict(name=t["name"], title=t["label"])]):
                        info["pieces_d"].append(shoot_piece(pg, el, pc, raw_dir, "d", args.scale))
                        log("桌機截到", pc["name"])
                    pg.evaluate(UNHIDE_JS)
                    if t.get("read"):
                        info["read"] = pg.evaluate(t["read"])
                    for pc_ in info["pieces_d"]:
                        if pc_.get("reads"):
                            info["read"] = pc_["reads"]
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
                    act_parts = [x for x in t["parts"] if x["name"] in info.get("heat_parts", [x["name"] for x in t["parts"]])]
                    for part in act_parts:          # 一張一張處理（換路由後前一張的元素就失效）
                        pinfo = {}
                        cm = bool(info.get("close_label"))      # 桌機版退回收盤 → 限動版也用收盤（同一篇口徑一致）
                        pel = prepare(spg, part, pinfo, cm) or prepare(spg, part, pinfo, cm)
                        if pel is None:
                            raise RuntimeError(f"{part['name']}：{pinfo.get('why')}")
                        pw = pw or pel.bounding_box()["width"]
                        total = pw * STORY_RATIO - 12
                        pel.evaluate("e => e.scrollIntoView({block: 'start'})")
                        spg.evaluate(FILL_JS, [pel, {"want": total * (1.0 if len(act_parts) == 1 else part["fill"]["frac"]), "charts": part["fill"]["charts"]}])
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
                                         "title": t["label"], "text": None, "jishi": [x for r in out_recs for x in r["jishi"]], "texts": [x for r in out_recs for x in r.get("texts", [])]}]
                    if info.get("close_label"):
                        info["pieces_m"][0]["close_label"] = info["close_label"]
                    log("限動版截到 heat（窄視窗", STORY_HEAT_VW, "）")
                    sctx.close()
                except Exception as exc:  # noqa: BLE001
                    info["story_why"] = f"限動熱力圖例外：{str(exc)[:100]}"
                continue
            try:
                if t["name"] == "sankey" or t.get("story_vw"):   # 限動版分流樹／法人表：換窄桌機視窗重畫：換成窄桌機視窗重畫（重畫、非拉伸），樹本身變寬
                    s_vw, s_dsf = t.get("story_vw", SANKEY_STORY_VW), t.get("story_dsf", SANKEY_STORY_DSF)
                    sargs = argparse.Namespace(**{**vars(args), "width": s_vw, "height": t.get("story_vh", SANKEY_STORY_VH), "scale": s_dsf})
                    sctx, spg = open_ctx(browser, base, sargs, today_ymd, sniff, False, s_dsf)
                    if t["name"] == "sankey":
                        sctx.add_init_script(f"window.TW_SNAP_SLOT_MAX={SANKEY_STORY_SLOT_MAX};window.TW_SNAP_COLS={SANKEY_STORY_COLS};")
                    el = prepare(spg, t, {})
                    if el is None:
                        info["story_why"] = "限動版沒截成"
                        sctx.close()
                        continue
                    for pc in t.get("m", []):
                        rec = shoot_piece(spg, el, pc, raw_dir, "m", s_dsf)
                        info["pieces_m"].append(rec)
                        log("限動版截到", pc["name"], "（窄桌機視窗", s_vw, "）")
                    sctx.close()
                    continue
                el = prepare(pg, t, {}) or prepare(pg, t, {})
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


# ---------------------------------------------------------------------------- 純資料快速路徑（2026-10-26）
# 盤後各卡全部由 social_native 原生繪製，網站截圖最後都被原生圖覆蓋；以前仍對每張卡開網站截「桌機」與「限動版」各一次（16 次頁面載入、約 3 分 40 秒），
# 只為了拿文案要的幾個數字。這裡改成直接讀 site/data 的 JSON，照網站畫面上的寫法（futpages.js、app.js 三大法人日報、marketfut.js）組出同格式的 read。
# 啟用條件：本輪所有目標卡的每一片都在 NAT.NATIVE、不需要 DUMP_JS（頁面上才讀得到的資料）、沒有 parts，且不是 --no-native／--no-fast／--from-shots。
# 盤中（輪盤、熱力圖等網站截圖卡）不會符合條件，照舊截圖。原生繪製若失敗，main 會自動用 --no-fast 重跑一次舊流程（退回網站截圖）。
from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal  # noqa: E402


def _js_fixed(v: float, d: int, comma: bool = False) -> str:
    """模擬 JS toFixed／toLocaleString(minimumFractionDigits=d)：對 double 的精確十進位值四捨五入（不是銀行家捨入）。"""
    q = Decimal(abs(v)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return f"{q:,.{d}f}" if comma else f"{q:.{d}f}"


def _js_round(v: float) -> int:
    """JS Math.round（.5 往正無限大）。"""
    if v >= 0:
        return int(Decimal(v).to_integral_value(rounding=ROUND_HALF_UP))
    return -int(Decimal(-v).to_integral_value(rounding=ROUND_HALF_DOWN))


def fast_read_fut_oi(j: dict) -> str:
    """同 futpages.js paintNumbers 的 #fpBig3（最新一日）：「外資+1,234 多 x／空 y 投信… 自營商…」。"""
    ds = j.get("dates") or []
    if not ds:
        return ""
    i = 0 if j.get("order") == "desc" else len(ds) - 1
    at = lambda arr: (float(arr[i]) if arr and i < len(arr) and arr[i] is not None else None)
    nf = lambda v: "—" if v is None else f"{_js_round(v):,}"
    sg = lambda v: "—" if v is None else ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(_js_round(v)):,}"
    out = []
    for k, nm in (("foreign", "外資"), ("trust", "投信"), ("dealer", "自營商")):
        o = j.get(k) or {}
        lg, sh = at(o.get("long")), at(o.get("short"))
        n = at(o.get("net"))
        if n is None and lg is not None and sh is not None:
            n = lg - sh
        out.append(f"{nm}{sg(n)} 多 {nf(lg)}／空 {nf(sh)}")      # 網站 innerText 名稱與數字之間沒有空白
    return " ".join(out)


RETAIL_PROD = {"TX": "大台", "MTX": "小台", "TMF": "微台"}


def fast_read_retail(j: dict) -> list[dict]:
    """同 RETAIL_VARIANTS（大台、小台、微台各讀 #fpTop 的大數字）：[{pct: '+1.23%', prod: '大台'}, …]。"""
    prods = j.get("products") if isinstance(j.get("products"), dict) else None
    if prods is None and isinstance(j.get("dates"), list):       # 舊格式：頂層就是一個商品
        prods = {j.get("product") if j.get("product") in RETAIL_PROD else "TMF": j}
    out = []
    for k, nm in RETAIL_PROD.items():
        o = (prods or {}).get(k) or {}
        ds = o.get("dates") or []
        if not ds:
            continue
        i = 0 if (o.get("order") or j.get("order")) == "desc" else len(ds) - 1
        at = lambda key: (float(o[key][i]) if o.get(key) and i < len(o[key]) and o[key][i] is not None else None)
        p = at("ratio_pct")
        if p is None:
            tot, lg, sh, nn = at("total_oi"), at("retail_long"), at("retail_short"), at("retail_net")
            if nn is None and lg is not None and sh is not None:
                nn = lg - sh
            p = nn / tot * 100 if tot and nn is not None else None
        out.append({"pct": "" if p is None else ("-" if p < 0 else "+") + _js_fixed(p, 2) + "%", "prod": nm})
    return out


def fast_read_inst(j: dict) -> list[list[str]]:
    """同 READ_INST（app.js 三大法人日報的 #instTiles）：[[身分, '+123.4億'], …]，用最新一列的官方值（不是 rev）。"""
    rows = (j or {}).get("rows") or []
    if not rows:
        return []
    last = rows[-1]

    def yi(v):
        if v is None:
            return "—億"
        return ("+" if v > 0 else "−" if v < 0 else "") + _js_fixed(v, 1, comma=True) + "億"
    return [[lab, yi(last.get(k))] for k, lab in (("f", "外資"), ("t", "投信"), ("dl", "自營商"), ("tot", "三大法人合計"))]


def fast_read_credit(mf: dict) -> dict:
    """同 READ_CREDIT（marketfut.js 信用交易 hero）：{ratio: '172.34', chg: '+0.12'}；維持率取最近一個算得出來的日子。"""
    rows = ((mf or {}).get("margin") or {}).get("rows") or []
    idx = [i for i, r in enumerate(rows) if r.get("ratio") is not None]
    if not idx:
        return {"ratio": None, "chg": None}
    cur = rows[idx[-1]]["ratio"]
    prev = rows[idx[-2]]["ratio"] if len(idx) > 1 else None
    chg = None
    if prev is not None:
        dr = cur - prev
        chg = ("+" if dr > 0 else "-" if dr < 0 else "") + _js_fixed(dr, 2, comma=True)
    return {"ratio": _js_fixed(cur, 2, comma=True), "chg": chg}


def fast_eligible(wanted: list[dict], args) -> bool:
    if getattr(args, "no_native", False) or getattr(args, "no_fast", False) or getattr(args, "from_shots", ""):
        return False
    if not wanted:
        return False
    for t in wanted:
        if t.get("parts"):
            return False
        for pc in (t.get("d") or []) + (t.get("m") or []):
            if pc["name"] not in NAT.NATIVE or pc["name"] in NAT.DUMP_JS:
                return False
    return True


def fast_targets(args, jget) -> list[dict]:
    """不開網站，直接從 JSON 組出跟 snap_targets 同格式的 shots（name、label、ok、why、read、pieces_d／pieces_m）。"""
    wanted = [t for t in TARGETS if t["kind"] in KIND_SET[args.kind] and (not args.only or t["name"] in args.only.split(","))]
    cache: dict = {}

    def J(n):
        if n not in cache:
            cache[n] = jget(n) or {}
        return cache[n]
    shots = []
    for t in wanted:
        info = {"name": t["name"], "label": t["label"], "ok": False, "why": "", "pieces_d": [], "pieces_m": [], "fast": True}
        n = t["name"]
        has, read = False, None
        if n == "fut-oi":
            read = fast_read_fut_oi(J("fut_oi"))
            has = bool(read)
        elif n == "retail-ratio":
            read = fast_read_retail(J("retail_ratio"))
            has = bool(read)
        elif n == "inst-today":
            read = fast_read_inst(J("inst_market"))
            has = bool(read)
        elif n in ("streak-foreign", "streak-trust"):
            b_, s_ = NAT.inst_top(J("inst_today"), "foreign" if n == "streak-foreign" else "trust", 10, dict(NAME_MAP))
            has = bool(b_ or s_)
            read = {"buy": [r["name"] for r in b_], "sell": [r["name"] for r in s_]}
        elif n == "credit-ratio":
            read = fast_read_credit(J("market_fut"))
            has = bool(read.get("ratio"))
        elif n in ("credit-rank", "credit-short"):
            m = J("market_fut").get("margin") or {}
            rk = m.get("short_rank" if n == "credit-short" else "rank") or {}
            up_, dn_ = NAT.credit_top(m, "short" if n == "credit-short" else "rank")
            has = bool(rk.get("rows"))
            read = {"up": [r["code"] for r in up_], "down": [r["code"] for r in dn_]}
        if not has:
            info["why"] = "資料檔裡沒有這張卡的資料 → 跳過"
            shots.append(info)
            continue
        info["read"] = read
        for key, lst in (("d", info["pieces_d"]), ("m", info["pieces_m"])):
            for pc in t.get(key) or []:
                lst.append({"name": pc["name"], "raw": "", "dsf": args.scale, "min_css_font": None, "title": pc.get("title", ""), "text": pc.get("text"),
                            "jishi": [], "notes": [], "texts": [], "dump": {}, "fast": True})
        info["ok"] = True
        log("資料快速路徑：", n, "（不開網站，原生繪製）")
        shots.append(info)
    return shots


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


def layout_html(mode: str, title: str, sub: str, img: str, top: list, bot: list, theme: str, date: str = "") -> str:
    """亮色 HUD 版型（規範 docs/marketing/social_unit/post_design_system.md）：標題列（LOGO＋時段膠囊＋標題＋靠右日期）→ HUD 卡片（四角括角：
    2×2 文字塊、截圖、備註塊）。圖上不放備註、來源、網址；日期只在標題列。flex 直排，元素天生不重疊，之後仍用瀏覽器量框檢查。"""
    story = mode == "story"
    k = TH.CANVAS[mode]["s"]
    css = TH.base_css(mode)
    if theme == "dark":      # 舊深色配色（備用，不維護）
        css += ":root{" + "".join(f"--{k_}:{v};" for k_, v in FRAME["dark"].items()) + "}"
    css += f"""
.card{{flex:1;min-height:0;display:flex;flex-direction:column;padding:{'14px' if story else '12px'}}}
.hd2{{flex:none;margin:0 6px 8px}}
.hd2 .s{{font-size:26px;line-height:1.5;color:var(--ink3);white-space:nowrap}}
.grid{{flex:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;font-variant-numeric:tabular-nums}}
.grid.top{{margin-bottom:10px}}.grid.bot{{margin-top:10px}}
.q{{border-radius:10px;border:1.5px solid color-mix(in srgb,var(--c) 45%,var(--panel));background:color-mix(in srgb,var(--c) 9%,var(--panel));padding:{'10px 14px 8px' if story else '8px 12px 6px'};text-align:left;min-width:0}}
.q b{{display:block;color:var(--c);font-size:{round(30*k)}px;font-weight:800;line-height:1.4;margin-bottom:2px}}
.q ul{{list-style:none;display:flex;flex-wrap:wrap;gap:0 18px}}.q li::before{{content:'';display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--c);margin-right:8px;vertical-align:middle}}.q li{{font-size:{round(26*k) if not story else 30}px;line-height:1.4;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:clip}}
.imgbox{{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}}
.shot{{max-width:100%;max-height:100%;display:block;border-radius:6px}}
"""
    css += ".card{flex:1}.imgbox{flex:1;min-height:0;position:relative}.shot{position:absolute;inset:0;width:100%;height:100%;max-width:none;max-height:none;object-fit:contain}"      # 滿版：截圖吃滿卡片剩餘空間（contain，不變形）
    kind = "intraday" if KIND not in TH.SLOT else KIND
    body = f"""{TH.header_html(kind, _esc(title), _esc(date))}
<div class=card>
{("<div class=hd2><div class=s data-box=sub>" + _esc(sub) + "</div></div>") if sub else ""}
{_blocks(top, "top")}<div class=imgbox><img class=shot data-box=shot src="{img}"></div>{_blocks(bot, "bot")}</div>"""
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


def trim_margin(path: str, pad: int = 2, thr: int = 28) -> str:
    """把截圖四周的空白（跟角落同色的部分）裁掉，圓盤才放得大（2026-10-26：輪盤圓盤要佔卡片寬 80% 以上）。"""
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > thr else 0).getbbox()
    if not box:
        return path
    x0, y0, x1, y1 = max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)
    out = path[:-4] + "_t.png"
    im.crop((x0, y0, x1, y1)).save(out)
    return out


def compose(browser, mode: str, rec: dict, top: list, bot: list, out_png: Path, report: list, theme: str) -> None:
    from PIL import Image
    if rec["name"] == "rotation-wheel":
        rec["raw"] = trim_margin(rec["raw"])
    with Image.open(rec["raw"]) as im:
        iw, ih = im.size
    title, sub = PIECE_META.get(rec["name"], (rec.get("title") or rec["name"], ""))
    dlabel = DATE_BY.get(rec["name"]) or DATE_LABEL
    title = re.sub(r"\s*\{d\}", "", title)            # 日期只放標題列右側（規範 post_design_system.md 第五節）
    if rec.get("close_label"):
        dlabel = rec["close_label"]                 # 2026-10-28：熱力圖即時等不到、退回上一個交易日收盤 → 標題列寫「M/D 收盤」，不冒充 12:00
    elif KIND == "intraday":
        dlabel = f"{dlabel} 12:00".strip()          # 盤中固定中午 12:00（2026-10-26 Andy）
    html = layout_html(mode, title, sub, b64(rec["raw"]), top, bot, theme, dlabel)
    pg = browser.new_page(viewport={"width": 1080, "height": 1920 if mode == "story" else THREADS_MAX_H}, device_scale_factor=1)
    pg.set_content(html, wait_until="load")
    pg.wait_for_timeout(400)
    H = 1920 if mode == "story" else THREADS_MAX_H
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
ROUTE_INST = "market/inst"      # 法人頁路由；日後改 market/inst 只改這個常數
HASHTAGS = {"intraday": "#台股 #資金流向 #熱力圖 #族群輪動", "close": "#台股 #法人買賣超 #外資 #投信 #台指期",
            "credit": "#台股 #融資 #融券 #融資維持率 #信用交易"}
DISCLAIMER = "資料：證交所／櫃買公開資料整理，僅供參考，不構成投資建議"


def deep_link(route: str, kind: str, ymd: str) -> str:
    camp = f"{kind}_" + ymd[4:8]
    return f"{SITE_URL}/?utm_source=threads&utm_campaign={camp}#{route}"


def _join(names: list, n: int) -> str:
    return "、".join(NAT.clean_name(x) for x in names[:n])


# 降級順序：(每行名稱數, 附網址的模式)；all＝每行都附、two＝只有前兩行（輪盤、分流樹）附、one＝只在第一行附一個
LADDER = [(3, "all"), (2, "all"), (2, "two"), (1, "two"), (1, "one")]


# ---------------------------------------------------------------------------- 盤面分析（2026-10-26 Andy：「盤前盤中盤後都需要有專業的金融專家分析盤面」）
# 原則同盤前（docs/marketing/social_unit/premarket_read_rules.md）：只寫看得到的事實與對照，不寫預測、不給買賣建議（投信投顧法）。
# 盤中、盤後的判斷式寫在 docs/marketing/social_unit/market_read_rules.md。

def intraday_reads(ok: dict) -> list[str]:
    """盤中（12:00，還沒收盤，不寫「收黑」）：族群漲跌 → 成交比重增加且漲幅前段（同向）→ 背離 → 權值族群動向。
    2026-10-27 金融口徑審查：族群平均是簡單平均要寫明；1.5～2 倍寫「漲多跌少／跌多漲少」；「資金流入」＝資金分流樹的成交比重增加。"""
    out = []
    hs = ok.get("heat") or {}
    heat = {} if hs.get("close_label") else {a: b for a, b in (hs.get("heat") or [])}   # 熱力圖退回收盤：不拿昨天的族群漲跌寫今天盤中
    notes = {k: v for k, v in ((ok.get("sankey") or {}).get("notes") or [])}
    inflow, outflow = notes.get("流入前五") or [], notes.get("流出前五") or []
    if heat:
        up = sum(1 for v in heat.values() if v > 0)
        dn = sum(1 for v in heat.values() if v < 0)
        avg = sum(heat.values()) / len(heat)
        tag = ("族群普漲" if up >= dn * 2 else "族群漲多跌少" if up >= dn * 1.5 else
               "族群普跌" if dn >= up * 2 else "族群跌多漲少" if dn >= up * 1.5 else "族群漲跌互見")
        out.append(f"{tag}：{len(heat)} 個族群 {up} 漲 {dn} 跌，族群平均 {avg:+.2f}%")
        top = [a for a, _ in sorted(heat.items(), key=lambda x: -x[1])[:10]]
        same = [g for g in inflow if g in top]
        if same:
            out.append(f"成交比重增加且漲幅居前：{'、'.join(same[:3])}")
        lag = [f"{g} {heat[g]:+.1f}%" for g in inflow if g in heat and heat[g] < 0]
        if lag:
            out.append(f"成交比重增加但族群走低：{'、'.join(lag[:2])}")
        rev = [f"{g} {heat[g]:+.1f}%" for g in outflow if g in heat and heat[g] >= 1.0]
        if rev:
            out.append(f"漲幅逾 1% 但成交比重下降：{'、'.join(rev[:2])}")
        big = [f"{g} {heat[g]:+.1f}%" for g in ("晶圓代工", "AI 伺服器組裝") if g in outflow and g in heat]
        if big:
            out.append(f"權值族群成交比重下降：{'、'.join(big)}")
    return out


def _streak_sign(vals: list[float]) -> tuple[int, float]:
    """從最後一天往回數，同號（同買或同賣）的連續天數與累計。"""
    if not vals or vals[-1] == 0:
        return 0, 0.0
    sg = vals[-1] > 0
    n, tot = 0, 0.0
    for v in reversed(vals):
        if (v > 0) != sg or v == 0:
            break
        n += 1
        tot += v
    return n, tot


def close_reads(im: dict, fo: dict, it: dict, mh: dict, retail: list, credit: dict) -> list[str]:
    """盤後（2026-10-27 依金融口徑審查修正，規則見 docs/marketing/social_unit/market_read_rules.md）。只寫事實、媒體慣用語。"""
    out = []
    try:
        if mh.get("taiex") and mh.get("change") is not None:
            tw, ch = float(mh["taiex"]), float(mh["change"])
            pct = ch / (tw - ch) * 100
            s = f"加權指數{'漲' if ch >= 0 else '跌'} {abs(ch):,.0f} 點（{pct:+.2f}%）"
            a, d = mh.get("advancers"), mh.get("decliners")
            if a and d:      # 家數是上市櫃（含 ETF）合計，不是只有上市
                s += f"；上市櫃（含 ETF）上漲 {a:,} 家、下跌 {d:,} 家"
            out.append(s)
        br = mh.get("breadth") or {}
        if br.get("pct_above_ma20") is not None and br["pct_above_ma20"] < 30:
            out.append(f"僅 {br['pct_above_ma20']:.1f}% 個股站上月線")
        cnt = ((br.get("movers") or {}).get("counts") or {})
        if (cnt.get("limit_up") or 0) >= 10 or (cnt.get("limit_down") or 0) >= 10:
            out.append(f"漲停 {cnt.get('limit_up', 0)} 家、跌停 {cnt.get('limit_down', 0)} 家")
        if mh.get("turnover") and mh.get("turnover_ma20"):
            r = mh["turnover"] / mh["turnover_ma20"]
            if r < 0.85 or r > 1.2:
                out.append(f"成交 {mh['turnover'] / 1e8:,.0f} 億，較 20 日均量{'量縮' if r < 1 else '量增'} {abs(r - 1) * 100:.0f}%")
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    rows = im.get("rows") or []
    for k, nm in (("f", "外資"), ("t", "投信")):
        vals = [float(r.get(k) or 0) for r in rows]      # 首次公布值（15:00 新聞用的那個），不用晚間修訂 rev
        if not vals or vals[-1] == 0:
            continue
        today = vals[-1]
        act = "買超" if today > 0 else "賣超"
        n, tot = _streak_sign(vals)
        last10 = vals[-10:]
        same10 = sum(1 for v in last10 if (v > 0) == (today > 0) and v != 0)
        if n >= 2:
            out.append(f"{nm}{act} {abs(today):,.1f} 億，已連 {n} 日{act}，累計 {abs(tot):,.1f} 億")
        elif len(vals) >= 2 and (abs(vals[-2]) < 50 or same10 >= 8):      # 前一天只是小額反向 → 不寫「轉」，改寫近 10 日
            out.append(f"{nm}{act} {abs(today):,.1f} 億，近 10 日 {same10} 日{act}，累計 {sum(last10):+,.1f} 億")
        else:
            out.append(f"{nm}轉{act} {abs(today):,.1f} 億")
    sells = ((it.get("top") or {}).get("foreign") or {}).get("sell") or []
    fnet = float(rows[-1].get("f") or 0) if rows else 0
    if sells and fnet < 0:
        r0 = sells[0]
        share = abs(r0["amt"]) / 1e8 / abs(fnet) * 100
        if share >= 15:
            out.append(f"外資賣超以{NAT.clean_name(r0['name'])}最多（{r0['amt'] / 1e8:+,.1f} 億，占外資當日賣超 {share:.0f}%）")
    net = (fo.get("foreign") or {}).get("net") or []
    if len(net) >= 2 and net[-1] is not None and net[-2] is not None:
        a0, a1 = net[-2], net[-1]
        if (a0 < 0) != (a1 < 0):
            out.append(f"外資台指期由淨{'多' if a0 >= 0 else '空'}單轉為淨{'空' if a1 < 0 else '多'}單 {abs(a1):,.0f} 口")
        elif a1 < 0:
            d = abs(a1) - abs(a0)
            out.append(f"外資{'加空' if d > 0 else '空單回補'}台指期 {abs(d):,.0f} 口，未平倉淨空單{'升' if d > 0 else '降'}至 {abs(a1):,.0f} 口")
        else:
            d = a1 - a0
            out.append(f"外資{'加多' if d > 0 else '多單減碼'}台指期 {abs(d):,.0f} 口，未平倉淨多單{'升' if d > 0 else '降'}至 {a1:,.0f} 口")
    mtx = next((x for x in retail or [] if x.get("prod") == "小台"), None)
    if mtx and mtx.get("pct"):
        v = float(str(mtx["pct"]).replace("%", "").replace("−", "-").replace("+", ""))
        if abs(v) >= 20:
            out.append(f"小台散戶多空比 {mtx['pct']}（{'多方' if v > 0 else '空方'}部位較多）" + ("，與外資期貨淨空方向相反" if v > 0 and net and net[-1] < 0 else ""))
    if credit.get("ratio"):
        chg = str(credit.get("chg") or "").replace("−", "-")
        out.append(f"上市融資維持率（估算）{credit['ratio']}%" + (f"，單日{'下降' if chg.startswith('-') else '上升'} {chg.lstrip('+-')} 個百分點" if chg else ""))
    return out


def credit_lines(ok: dict, n: int) -> list[str]:
    """融資維持率／融資／融券三段（盤後那篇與單獨的融資篇共用）。"""
    yi = lambda x: x.replace("−", "-")
    nm = lambda xs: [NAME_MAP.get(str(x), x) for x in xs]      # 讀到的是代號（列上的名稱已被 LOGO 排版改寫），換成簡稱
    L = []
    r = (ok.get("credit-ratio") or {}).get("read") or {}
    if r.get("ratio"):
        L += ["融資維持率：", f"・上市（估算）{r['ratio']}%" + (f"，較前日 {yi(r['chg'])}pp" if r.get("chg") else "")]
    r = (ok.get("credit-rank") or {}).get("read") or {}
    if r.get("up") and r.get("down"):
        L += ["融資：", f"・增加 {_join(nm(r['up']), n)}；", f"・減少 {_join(nm(r['down']), n)}"]
    r = (ok.get("credit-short") or {}).get("read") or {}
    if r.get("up") and r.get("down"):
        L += ["融券：", f"・增加 {_join(nm(r['up']), n)}；", f"・減少 {_join(nm(r['down']), n)}"]
    return L


def caption_lines(kind: str, stamp: str, shots: list[dict], data_date: str, ymd: str, n: int, links: str = "all") -> list[str]:
    return _emo(_caption_lines(kind, stamp, shots, data_date, ymd, n, links))


def _caption_lines(kind: str, stamp: str, shots: list[dict], data_date: str, ymd: str, n: int, links: str = "all") -> list[str]:
    ok = {s["name"]: s for s in shots if s.get("ok")}
    L = []

    def lk(route: str, idx: int) -> str:     # idx＝這是第幾個有內容的行（0 起算）
        return f" → {deep_link(route, kind, ymd)}" if links == "all" or (links == "two" and idx < 2) else ""
    if kind == "intraday":
        # 2026-10-26 Andy 指定格式：標題「盤中消息」、每段標題一行＋「・」條列；Andy：「連結只需要附在最底下就好」→ 只在最後一行放一個網址；文案末不放資料來源／免責
        L.append("盤中3分鐘")      # 2026-10-27 Andy：「盤中也要改成盤中3分鐘」
        n = min(n, 2)      # Andy 範例每項列 2 個
        ar = intraday_reads(ok)
        if ar and links != "none":
            L += ["盤面分析："] + [f"・{x}" for x in ar[:4]]
        s = ok.get("rotation")
        if s:
            d = {k: v for k, v in s.get("lines", [])}
            if d.get("領先") and d.get("落後"):
                L += ["資金輪盤：", f"・領先 {_join(d['領先'], n)}；", f"・落後 {_join(d['落後'], n)}"]
        s = ok.get("sankey")
        if s:
            d = {k: v for k, v in s.get("notes", [])}
            if d.get("流入前五") and d.get("流出前五"):
                L += ["資金分流樹：", f"・流入 {_join(d['流入前五'], n)}；", f"・流出 {_join(d['流出前五'], n)}"]
        s = ok.get("heat")
        if s and s.get("heat"):
            h = sorted(s["heat"], key=lambda x: x[1])
            k = min(2, n)
            ups = "、".join(f"{a} {b:+.1f}%" for a, b in h[::-1][:k])
            dns = "、".join(f"{a} {b:+.1f}%" for a, b in h[:k])
            L += [f"熱力圖（{s['close_label']}）：" if s.get("close_label") else "熱力圖：", f"・漲最多 {ups}；", f"・跌最多 {dns}"]
        L.append(HASHTAGS[kind])
        if links != "none":
            L += link_lines(kind, ymd, route=landing_route(kind, ymd, ctx_from_shots(ok)))
        return L
    elif kind == "credit":
        # 2026-10-26 Andy：盤中格式確認 OK、「以後 Follow 這格式」→ 標題一行、每段「標題：」＋「・」條列、網址只放最底下一行、不放資料來源／免責
        n = min(n, 2)      # 2026-10-26 Andy：「統一兩個」
        L.append("盤後融資融券")
        L += credit_lines(ok, n)
        L.append(HASHTAGS[kind])
        if links != "none":
            L += link_lines(kind, ymd, route=landing_route(kind, ymd, ctx_from_shots(ok)))
        return L
    else:
        # 同上：Andy 盤中格式套到盤後
        n = min(n, 2)      # 2026-10-26 Andy：「統一兩個」
        L.append("盤後3分鐘｜法人補充" if SUPPLEMENT else "盤後3分鐘")      # 2026-10-26 Andy：標題「盤後3分鐘」；段落順序跟圖一樣：期貨法人未平倉 → 散戶多空比 → 三大法人 → 外資 → 投信 → 融資融券（2026-10-26 Andy）
        ar = ((ok.get("analysis") or {}).get("read") or [])
        if ar:
            L += ["盤面分析："] + [f"・{x}" for x in ar[:7]]
        yi = lambda x: x.replace("−", "-")
        r = (ok.get("fut-oi") or {}).get("read")
        if r:
            import re as _re
            it = [f"{a} {yi(b)} 口" for a, b in _re.findall(r"(外資|投信|自營商?)\s*([+\-−]?[\d,]{3,})", r)]
            if it:
                L += ["台指期法人淨未平倉："] + ([f"・{'、'.join(it[:2])}；", f"・{'、'.join(it[2:])}"] if len(it) > 2 else [f"・{'、'.join(it)}"])
        r = (ok.get("retail-ratio") or {}).get("read") or []
        if r:
            it = [f"{x.get('prod') or '?'} {yi(x.get('pct') or '—')}" for x in r]
            L += ["散戶多空比："] + ([f"・{'、'.join(it[:2])}；", f"・{'、'.join(it[2:])}"] if len(it) > 2 else [f"・{'、'.join(it)}"])
        r = (ok.get("inst-today") or {}).get("read") or []
        if r:
            nm_ = {"外資": "外資", "投信": "投信", "自營商": "自營", "三大法人合計": "合計"}
            it = [f"{nm_.get(a, a)} {yi(b)}" for a, b in r]
            L += ["三大法人買賣超："] + ([f"・{'、'.join(it[:2])}；", f"・{'、'.join(it[2:])}"] if len(it) > 2 else [f"・{'、'.join(it)}"])
        for key, lab in (("streak-foreign", "外資"), ("streak-trust", "投信")):
            r = (ok.get(key) or {}).get("read") or {}
            if r.get("buy") and r.get("sell"):
                L += [f"{lab}：", f"・買超 {_join(r['buy'], 5)}；", f"・賣超 {_join(r['sell'], 5)}"]      # 2026-10-27 Andy：「買賣超至少前五名要寫」
        r = (ok.get("etf-buy") or {}).get("read") or {}
        if r.get("foreign") or r.get("trust"):      # 2026-10-26 Andy：ETF 買超排名
            L += ["ETF 買超："] + [f"・{lab} {_join(r[k], n)}" + ("；" if k == "foreign" and r.get("trust") else "") for k, lab in (("foreign", "外資"), ("trust", "投信")) if r.get(k)]
        if PARTIAL and any(n in PARTIAL for n in gate.INST_CARDS):      # 保底（2026-10-29）：法人卡晚到 → 標明稍後補
            L += ["三大法人：", "・法人個股明細晚到，稍後補"]
        # 2026-10-27 Andy：融資融券移到隔天盤前，盤後不再列
        L.append(HASHTAGS[kind])
        if links != "none":
            L += link_lines(kind, ymd, route=landing_route(kind, ymd, ctx_from_shots(ok)))
        return L


# 文案太長時依序拿掉的段落（盤面分析與網址永遠保留；被拿掉的數字圖上都有）
DROP_ORDER = {"close": ["📦 ETF 買超：", "📉 融券：", "📈 融資：", "🛡️ 融資維持率：", "⚖️ 散戶多空比：", "📊 台指期法人淨未平倉：", "🏢 投信：", "🌏 外資："],
              "intraday": ["🔥 熱力圖：", "🌳 資金分流樹："]}


def build_text(kind: str, stamp: str, shots: list[dict], data_date: str, ymd: str = "") -> str:
    """Threads／IG 文案。一律用實際字元數 len(text) ≤ 480；超過就依 LADDER 降級（名稱 3→2→1，再來只有前兩行附網址，最後只留第一行一個網址）。"""
    ymd = ymd or data_date.replace("-", "")

    def fit(L: list[str]) -> str:
        """先依序拿掉次要段落（數字圖上都有），盤面分析與網址永遠保留。"""
        L = list(L)
        for head in DROP_ORDER.get(kind, []):
            if len("\n".join(L)) <= THREADS_MAX:
                break
            if head in L:
                i = L.index(head)
                j = i + 1
                while j < len(L) and L[j].startswith("・"):
                    j += 1
                del L[i:j]
        return "\n".join(L)
    txt = ""
    for n, links in LADDER:      # 每一級都先砍段落、再縮名稱數（2026-10-26：名稱保留 2 個優先於保留次要段落）
        txt = fit(caption_lines(kind, stamp, shots, data_date, ymd, n, links))
        if len(txt) <= THREADS_MAX:
            break
    if len(txt) > THREADS_MAX and kind != "intraday":      # 盤後連結多：先拿掉 utm_campaign
        txt = txt.replace(f"&utm_campaign={kind}_{ymd[4:8]}", "")
    if len(txt) > THREADS_MAX:
        log(f"⚠ 文案 {len(txt)} 字仍超過 {THREADS_MAX}")
    return txt


# ---------------------------------------------------------------------------- 發不發（資料日把關，2026-10-26）
MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0"   # CLAUDE.md 白名單內的即時報價端點（DECISIONS #108）


def fetch_last_trade() -> dict:
    """證交所 mis 即時報價（加權指數）的成交日 d ＝ 現在最新的交易日。颱風等臨時休市靜態表沒有，靠這個判斷（2026-10-26）。
    回 {"last_trade": "YYYY-MM-DD", "live": True}；查不到回 {"last_trade": None, "live": False}（之後只用休市日表、保守不發）。"""
    try:
        from urllib.request import Request
        req = Request(MIS_URL, headers={"User-Agent": "Mozilla/5.0 (tw-rotation social_snap)", "Referer": "https://mis.twse.com.tw/stock/index.jsp"})
        with urlopen(req, timeout=12) as r:
            j = json.loads(r.read().decode("utf-8"))
        d = gate._iso(str(((j.get("msgArray") or [{}])[0]).get("d") or ""))
        if d:
            return {"last_trade": d, "live": True}
    except Exception as exc:  # noqa: BLE001
        log("查不到即時成交日（mis）：", exc)
    return {"last_trade": None, "live": False}


def decide(kind: str, now: datetime, meta: dict, mf: dict, card_dates: dict, names: list, holidays: dict,
           ev: dict | None = None) -> tuple[bool, str, str]:
    """回 (發不發, 這一篇的資料日, 不發的原因)。資料日一律取卡片自己的資料日，不用執行日或 meta 的日期硬套。

    · close：names 裡每張卡的資料日都＝今天（台北）且今天是交易日；任何一張不是 → 不發，原因寫哪張是哪天。
    · credit：credit_ready（融資最後一天＝網站最新交易日、維持率算得出來、不是部分估算、兩個排行同一天）
              ＋ social_gate.credit_gate（資料日收盤後、下一個交易日 09:00 開盤前）。
    · intraday：交易日 09:00～13:30（截圖前先看時段與休市日表；報價成交日在截圖後再驗）。
    ev＝{"last_trade": 即時成交日, "live": 是否真的查到}（fetch_last_trade）；颱風等臨時休市靠它判斷。
    """
    today = now.astimezone(gate.TPE).date().isoformat()
    ev = ev or {}
    lt, live = ev.get("last_trade"), bool(ev.get("live"))
    if kind == "close":
        # 盤後：法人＋期貨＋散戶＋ETF（2026-10-27 起融資移到盤前）→ 每張卡都要是今天、今天是交易日；下午資料到齊那輪就發
        cd = {n: card_dates.get(n, "") for n in names}
        ok, why = gate.close_gate(today, cd, holidays, lt, live, now)
        log("盤後各張資料日：" + "、".join(f"{k}＝{v or '沒有日期'}" for k, v in cd.items()))
        return ok, today if ok else "", why
    if kind == "credit":
        ok, d, why = credit_ready(meta, mf)
        if not ok:
            return False, d, why
        cd = {n: card_dates.get(n, "") for n in names}
        bad = {k: v for k, v in cd.items() if v and v != d}
        if bad:
            return False, d, "這幾張的資料日跟融資資料日 " + d + " 不同：" + "、".join(f"{k}＝{v}" for k, v in bad.items())
        ok, why = gate.credit_gate(now, d, holidays, lt, live)
        if ok:
            log(f"盤後融資資料日 {d}：{why}")
        return ok, d, ("" if ok else why)
    ok, why = gate.intraday_gate(now, [], holidays, check_quotes=False)
    return ok, today, why


# ---------------------------------------------------------------------------- 主程式
def main() -> int:
    global DATE_LABEL, KIND, SUPPLEMENT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=["intraday", "close", "credit"], required=True, help="intraday＝盤中；close＝盤後法人；credit＝盤後融資（資料到齊那輪才發）")
    ap.add_argument("--out", required=True, help="輸出資料夾（manifest.json 與圖片都放這裡）")
    ap.add_argument("--base", default=SITE_URL + "/index.html", help="網站網址（本機例如 http://127.0.0.1:8791/index.html）")
    ap.add_argument("--serve", default="", help="給路徑就在本機起靜態伺服器（site 資料夾），--base 自動設成它")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--width", type=int, default=840, help="桌機截圖視窗寬（Threads 用）。2026-10-26 由 1440 改 840：截圖放進 1000px 卡片時內文放大約 1.25 倍（>820 才維持桌機版面）")
    ap.add_argument("--height", type=int, default=1000)
    ap.add_argument("--scale", type=float, default=2.0, help="截圖解析度倍率")
    ap.add_argument("--only", default="", help="只做這幾個目標（逗號分隔 name）")
    ap.add_argument("--live-wait", type=int, default=30, help="等即時套上的秒數")
    ap.add_argument("--no-close-fallback", action="store_true", help="熱力圖等不到即時就略過（不退回上一個交易日收盤）")
    ap.add_argument("--mock-live", action="store_true", help="模擬報價（本機示範用；正式站不要加）")
    ap.add_argument("--live-override", action="store_true", help="本機 TW_LIVE_OVERRIDE（只有 127.0.0.1 認）")
    ap.add_argument("--data-overlay", default="", help="下載網站資料後，再用這個資料夾裡的 JSON 蓋過去（pipeline/social_close_payload.py 的輸出）")
    ap.add_argument("--data-url", default="", help="先從這些網址（逗號分隔，依序試）下載網站要用的 JSON 到 --serve 的 data/，例如 https://miaozike.github.io/tw-rotation/data,https://tw-rotation.pages.dev/data")
    ap.add_argument("--spoof-origin", action="store_true", help="報價請求補上正式站 Origin（本機站打正式報價代理用）")
    ap.add_argument("--skip-live", nargs="?", const="all", default="", help="只測版面：不要求即時（all 或逗號分隔的目標名；會截到盤後畫面，絕不可用在發布）")
    ap.add_argument("--no-native", action="store_true", help="不用原生繪製，全部用網站截圖（除錯用）")
    ap.add_argument("--no-fast", action="store_true", help="不走純資料快速路徑：全部卡都原生繪製時也照舊開網站截圖（除錯／比對用）")
    ap.add_argument("--from-shots", default="", help="沿用另一個輸出資料夾已截好的圖（只換 --frame 配色，示範用）")
    ap.add_argument("--frame", choices=["light", "dark"], default="light", help="版型配色（預設淺色，跟截圖一致）")
    ap.add_argument("--use-snap-attr", action="store_true", help="只用 data-snap 屬性找目標")
    ap.add_argument("--no-snap-attr", action="store_true", help="不用 data-snap，只用現有選擇器")
    ap.add_argument("--force", action="store_true", help="略過「盤中時段／今天是不是交易日／法人資料是不是今天」的檢查（示範用）")
    ap.add_argument("--posted-json", default="", help="發布紀錄 posted.json（social-snaps 分支 state/）；這一篇的時段鍵已在裡面就不截（結束碼 10）")
    ap.add_argument("--landing-json", default="", help="近幾天落點紀錄 landing_recent.json（social-snaps 分支 state/）；讓「同一落點連續 2 天就換」生效")
    ap.add_argument("--today", default="", help="覆寫「今天」（YYYY-MM-DD，示範／測試用）")
    ap.add_argument("--no-mis", action="store_true", help="不查 mis 即時成交日（離線測試用；臨時休市就只能靠休市日表）")
    ap.add_argument("--now", default="", help="覆寫「現在」（台北，YYYY-MM-DDTHH:MM，測試日期把關用；會連帶覆寫 --today）")
    ap.add_argument("--supplement", action="store_true", help="盤後法人補充貼文：主貼文已用保底發出（拿掉法人卡），法人資料到了再補發法人那幾張（鍵 close-inst-<日期>）")
    ap.add_argument("--fallback-at", default=os.environ.get("CLOSE_FALLBACK_AT", ""), help="盤後保底時間（台北 HH:MM，預設 19:00）：過了還有卡不是今天 → 拿掉那幾張、其他照發")
    ap.add_argument("--fresh-news", action="store_true", help="新聞焦點除了資料湖 news，再當場抓一次鉅亨／科技新報／聯合（只併進記憶體，不寫湖；失敗就只用湖）")
    args = ap.parse_args()
    KIND = args.kind
    load_recent(args.landing_json)

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    now_ = datetime.fromisoformat(args.now).replace(tzinfo=TPE) if args.now else now_tpe()
    today = args.today or now_.strftime("%Y-%m-%d")
    today_ymd = today.replace("-", "")
    stamp_now = now_tpe().strftime("%H:%M")

    srv = None
    base = args.base
    if args.serve:
        if args.data_url:
            if not sync_data(Path(args.serve).resolve(), args.data_url):
                return 2
        if args.data_overlay:      # 2026-10-27：盤後貼文用資料湖直接算的那幾份蓋上去，不等整站重算＋部署
            import shutil
            for f_ in sorted(Path(args.data_overlay).glob("*.json")):
                shutil.copy(f_, Path(args.serve).resolve() / "data" / f_.name)
                log(f"  用最新資料湖算的 {f_.name} 蓋過網站版")
        try:
            for r_ in json.loads((Path(args.serve).resolve() / "data" / "stocks.json").read_text("utf-8")):
                if r_.get("code") and r_.get("name"):
                    NAME_MAP[str(r_["code"])] = r_["name"]
            DATE_ISO.update(data_dates(Path(args.serve).resolve()))
            log("各張資料日：", DATE_ISO)
            log(f"個股名稱對照 {len(NAME_MAP)} 檔")
            logos = json.loads((Path(args.serve).resolve() / "data" / "logos.json").read_text("utf-8"))
            # 10-21 破圖事故：sync_data 只抓 JSON、不抓 data/logos/*.png，相對路徑在本機伺服器全部 404 → 改讀正式站的圖檔
            LOGO_MAP.update({k: (f"{DATA_SRC}/{v[5:]}" if DATA_SRC and str(v).startswith("data/") else v) for k, v in logos.items()})
            log(f"logo {len(LOGO_MAP)} 檔")
        except Exception as exc:  # noqa: BLE001
            log("讀不到 stocks.json 名稱對照：", exc)
        srv = serve_dir(Path(args.serve).resolve(), args.port)
        base = f"http://127.0.0.1:{args.port}/index.html"
        args.live_override = True
    try:
        meta = fetch_meta(base)
        if not DATE_ISO:      # 沒有 --serve：從網站讀各張的資料檔
            DATE_ISO.update(data_dates(None, lambda n: fetch_json(base, n)))
        names_ = [t["name"] for t in TARGETS if t["kind"] in KIND_SET[args.kind] and (not args.only or t["name"] in args.only.split(","))]
        holidays_ = gate.load_holidays()
        mf_ = fetch_json(base, "market_fut") if args.kind == "credit" else {}
        ev_ = fetch_last_trade() if args.kind in ("close", "credit") and not args.no_mis else {}
        if ev_:
            log(f"即時成交日（mis 加權指數）：{ev_.get('last_trade') or '查不到'}")
        SUPPLEMENT = bool(args.supplement and args.kind == "close")
        if SUPPLEMENT:      # 補充貼文只做法人那幾張；把關一樣嚴格（那幾張都要是今天）
            names_ = [n for n in names_ if n in gate.INST_CARDS]
            args.only = ",".join(names_)
            log("盤後法人補充貼文：只做 " + "、".join(names_))
        go_, data_date, why_ = decide(args.kind, now_, meta, mf_, DATE_ISO, names_, holidays_, ev_)
        if not go_ and args.kind == "close" and not SUPPLEMENT and not args.force:
            # 2026-10-29 鐵則「沒有條件不符就不發」：過了保底時間 → 拿掉過期卡、當天的照發，寫 alert，法人晚到再補發
            cd_ = {n: DATE_ISO.get(n, "") for n in names_}
            fb_ok, fb_why, fb_drop = gate.close_fallback(now_.date().isoformat(), cd_, holidays_, ev_.get("last_trade"), bool(ev_.get("live")), now_, args.fallback_at)
            if fb_ok:
                log(f"close：{why_} → {fb_why}")
                PARTIAL[:] = fb_drop
                names_ = [n for n in names_ if n not in fb_drop]
                args.only = ",".join(names_)
                go_, data_date, why_ = True, now_.date().isoformat(), ""
                (out / "alert.txt").write_text(f"盤後主貼文走保底：{fb_why}；法人個股明細到了會自動補發一則（close-inst-{data_date}）。\n", "utf-8")
            else:
                log(f"close 保底也不成立：{fb_why}")
        if not go_:
            if not args.force:
                log(f"{args.kind}：{why_} → 不發")
                return 10
            log(f"⚠ --force：{why_}（照樣產出，只供測試，不可發布）")
        if not data_date:      # 只有 --force 才會走到這裡：拿各張實際資料日裡最新的一天，不拿執行日硬套
            data_date = max([DATE_ISO.get(n, "") for n in names_] + [""]) or today
        # 圖上日期一律＝該卡自己的資料日（close、credit 通過把關時本來就都＝data_date）
        DATE_BY.update({k: mmdd(v) for k, v in DATE_ISO.items()})
        DATE_LABEL = mmdd(data_date)
        if args.posted_json and not args.force:
            key_ = slot_key_for(args.kind, data_date, now_.isoformat(timespec="seconds"), SUPPLEMENT)
            try:
                done_ = json.loads(Path(args.posted_json).read_text("utf-8"))
            except Exception:  # noqa: BLE001
                done_ = {}
            if key_ in done_ and posted_ok(key_, done_[key_]):
                log(f"{key_} 已經發過（{args.posted_json}）→ 不重複")
                return 10
            if key_ in done_:
                log(f"⚠ {key_} 的發布紀錄時間 {done_[key_].get('at')} 不在正式時段（測試誤記）→ 不算，照發")
        if args.kind == "intraday" and not args.force and not args.now:      # 盤中固定中午 12:00：早到就等到 12:00，資料以那一刻的即時為準
            wait_s = (datetime.combine(now_tpe().date(), datetime.strptime("12:00", "%H:%M").time(), TPE) - now_tpe()).total_seconds()
            if 0 < wait_s <= 600:
                log(f"還沒到 12:00，等 {int(wait_s)} 秒再截圖")
                time.sleep(wait_s)
        if args.from_shots:      # 只換版型配色：沿用另一輪已截好的圖（示範用）
            shots = json.loads((Path(args.from_shots) / "shots.json").read_text("utf-8"))
            sniff = {"quote_dates": set(), "errors": []}
        else:
            wanted_ = [t for t in TARGETS if t["kind"] in KIND_SET[args.kind] and (not args.only or t["name"] in args.only.split(","))]
            if fast_eligible(wanted_, args):      # 全部原生繪製：不開網站截圖，直接讀 JSON（2026-10-26）
                log("本輪全部卡片都原生繪製 → 純資料快速路徑（不開網站截圖）")
                shots = fast_targets(args, lambda n: fetch_json(base, n))
                sniff = {"quote_dates": set(), "errors": []}
            else:
                shots, sniff = snap_targets(args, base, out, today_ymd)
        if args.kind == "intraday" and not args.force:
            ok_q, why_q = gate.intraday_gate(now_, sniff["quote_dates"], holidays_)
            if not ok_q:
                log(f"盤中：{why_q} → 不發")
                return 10
        ok = [s for s in shots if s.get("ok")]
        bad_words = [(rec["name"], rec["jishi"]) for s in ok for rec in s["pieces_d"] + s["pieces_m"] if rec.get("jishi")]
        log(f"「即時」字樣掃描：{sum(len(s['pieces_d']) + len(s['pieces_m']) for s in ok)} 片，{sum(len(h) for _, h in bad_words)} 筆")
        if bad_words:
            for n_, h_ in bad_words:
                log("  ✗", n_, h_)
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 4
        bad_notes = [(rec["name"], rec["notes"]) for s in ok for rec in s["pieces_d"] + s["pieces_m"] if rec.get("notes")]
        log(f"備註／來源字樣掃描：{sum(len(s['pieces_d']) + len(s['pieces_m']) for s in ok)} 片，{sum(len(h) for _, h in bad_notes)} 筆")
        if bad_notes:
            for n_, h_ in bad_notes:
                log("  ✗", n_, h_)
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 5
        for s in shots:
            if not s.get("ok"):
                log("略過", s["name"], "：", s.get("why"))
        if not ok:
            log("一張都沒截成")
            (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
            return 2

        stamp_full = now_tpe().strftime("%m/%d %H:%M") if args.kind != "intraday" else f"{now_tpe():%m/%d} 12:00"      # 盤中固定中午 12:00
        dd = data_date[5:].replace("-", "/")
        report: list[dict] = []
        stories: list[str] = []
        threads_imgs: list[str] = []
        fast_fail: list[str] = []      # 快速路徑原生繪製失敗的卡（沒有網站截圖可退）
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()

            def texts(s, rec):
                return (s.get("lines", []) if rec.get("text") == "quad" else []), (s.get("notes", []) if rec.get("text") == "flows" else [])

            def native(mode_, rec):
                """原生繪製（規範第十五節）：成功回 True；資料讀不到或畫失敗就退回網站截圖，並在 log 講明。"""
                if rec["name"] not in NAT.NATIVE or args.no_native:
                    return False
                drec = next((x for x in [x for s_ in ok for x in s_["pieces_d"]] if x["name"] == rec["name"]), rec)
                title_ = re.sub(r"\s*\{d\}", "", PIECE_META.get(rec["name"], (rec["name"], ""))[0])
                dlabel_ = DATE_BY.get(rec["name"]) or DATE_LABEL
                if KIND == "intraday":
                    dlabel_ = f"{dlabel_} 12:00".strip()
                ctx_ = dict(kind=KIND, title=title_, date=dlabel_, jget=lambda n: fetch_json(base, n), site=Path(args.serve).resolve() if args.serve else Path("."),
                            logos=LOGO_MAP, dump=drec.get("dump") or {})
                if rec["name"] in NAT.DUMP_JS and not ctx_["dump"]:
                    log("  ⚠ 原生繪製讀不到資料 → 退回網站截圖：", rec["name"])
                    return False
                try:
                    rep_ = NAT.render(browser, rec["name"], mode_, ctx_, out / f"{'story' if mode_ == 'story' else 'threads'}_{rec['name']}.png")
                except Exception as exc:  # noqa: BLE001
                    log("  ⚠ 原生繪製失敗 → 退回網站截圖：", rec["name"], str(exc)[:120])
                    return False
                report.append(rep_)
                return True

            ORDER = {"intraday": ["rotation-wheel", "sankey-tree", "rotation-rank", "heat"],
                     "close": ["fut-oi", "retail-ratio", "inst-today", "streak-foreign", "streak-trust"]}.get(args.kind, [])
            rk = lambda r: ORDER.index(r["name"]) if r["name"] in ORDER else len(ORDER)
            pd_ = sorted([(s, r) for s in ok for r in s["pieces_d"]], key=lambda t: rk(t[1]))      # Threads 輪播順序＝這裡的順序
            pm_ = sorted([(s, r) for s in ok for r in s["pieces_m"]], key=lambda t: rk(t[1]))
            for s, rec in pd_:
                if True:
                    tp, bt = texts(s, rec)
                    if native("threads", rec):
                        pass
                    elif rec.get("fast"):      # 快速路徑沒有網站截圖可退 → 記下來，整輪改用 --no-fast 重跑
                        fast_fail.append(rec["name"])
                    else:
                        compose(browser, "threads", rec, tp, bt, out / f"threads_{rec['name']}.png", report, args.frame)
                    threads_imgs.append(f"threads_{rec['name']}.png")
            for s, rec in pm_:
                if True:
                    if rec["name"] == "rotation-wheel":     # 手機版圓盤只佔卡片寬約 68%（標籤留白）；改用桌機窄視窗那張（約 96%），2026-10-26 Andy 要 ≥80%
                        rec = next((x for x in s["pieces_d"] if x["name"] == "rotation-wheel"), rec)
                    tp, bt = texts(s, rec)
                    if native("story", rec):
                        pass
                    elif rec.get("fast"):
                        fast_fail.append(rec["name"])
                    else:
                        compose(browser, "story", rec, tp, bt, out / f"story_{rec['name']}.png", report, args.frame)
                    stories.append(f"story_{rec['name']}.png")
            if KIND == "close" and not args.no_native and "streak-trust" in [r["name"] for _, r in pd_]:
                # ETF 買超排名（外資、投信上下兩張；原生繪製、沒有網站截圖），放在投信個股排行後面（2026-10-26 Andy）
                for mode_, lst_ in (("threads", threads_imgs), ("story", stories)):
                    try:
                        fn_ = f"{'story' if mode_ == 'story' else 'threads'}_etf-buy.png"
                        report.append(NAT.render(browser, "etf-buy", mode_, dict(kind=KIND, title="ETF 買超排名", date=DATE_BY.get("streak-trust") or DATE_LABEL,
                                                                             jget=lambda n: fetch_json(base, n)), out / fn_))
                        pos_ = next(i for i, f in enumerate(lst_) if "streak-trust" in f) + 1
                        lst_.insert(pos_, fn_)
                    except Exception as exc:  # noqa: BLE001
                        log("  ⚠ ETF 買超排名畫失敗（不擋發文）：", str(exc)[:120])
            # 2026-10-27 Andy：「IG 限時動態這頁都拿掉」→ 不再加結尾頁「完整資料在網站」（social_native.py 的 outro 保留不用）
            browser.close()
        if fast_fail:      # 快速路徑原生繪製失敗：退回舊流程（開網站截圖，失敗的卡用截圖排版），整輪重跑一次
            log("  ⚠ 快速路徑原生繪製失敗：", "、".join(sorted(set(fast_fail))), "→ 改用 --no-fast（網站截圖）重跑")
            if srv:
                srv.shutdown()
                srv.server_close()
                srv = None
            import subprocess
            return subprocess.call([sys.executable, str(Path(__file__).resolve())] + sys.argv[1:] + ["--no-fast"])
        for r in report:
            if r["file"].startswith("story_") and r["shot_ratio"] < 0.75 and r["h"] == 1920:
                log(f"  ⚠ {r['file']} 截圖佔畫布 {r['shot_ratio']:.0%}、內容卡片佔 {r['content_ratio']:.0%}")
        bad = [r for r in report if r["hits"] or r["out"] or r["cut"]]
        (out / "layout_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
        (out / "shots.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), "utf-8")
        lines_ = ["# 各張卡片上出現的文字（DOM 文字；圖表畫布內的軸字、圖例不在此列）", ""]
        for s_ in ok:
            for mode_, key_ in (("Threads 版", "pieces_d"), ("限動版", "pieces_m")):
                for rec_ in s_[key_]:
                    lines_ += [f"## {rec_['name']}（{mode_}）", ""] + [f"- {x}" for x in rec_.get("texts", [])] + [""]
        (out / "text_report.md").write_text("\n".join(lines_), "utf-8")
        log(f"重疊檢查：程式 {len(report)} 張版面（{sum(r['n'] for r in report)} 個框）{len(bad)} 張有問題")
        if bad:
            # 2026-10-28 Andy：「後續盤中 盤後也不能發生這樣的事情」→ 一張圖重疊不再擋下整篇：拿掉那張、其他照發，記進 alert.txt
            for r in bad:
                log("  ✗", r["file"], r["hits"], r["out"], r["cut"], "→ 這張不放進貼文")
            drop_ = {r["file"] for r in bad}
            threads_imgs = [f for f in threads_imgs if Path(f).name not in drop_]
            stories = [f for f in stories if Path(f).name not in drop_]
            if not threads_imgs and not stories:
                return 3
            (out / "alert.txt").write_text(f"{args.kind} 貼文有 {len(drop_)} 張圖版面重疊，已拿掉不發：{'、'.join(sorted(drop_))}。\n", "utf-8")

        if args.kind in ("close", "credit"):      # 融資／融券文案改讀資料檔、只列個股（跟圖同一份：social_native.credit_top），2026-10-26 Andy「排除ETF只列個股」
            mf_ = (fetch_json(base, "market_fut") or {}).get("margin") or {}
            it_ = fetch_json(base, "inst_today") if args.kind == "close" else {}
            stale_inst_ = args.kind == "close" and any(n in PARTIAL for n in ("streak-foreign", "streak-trust"))
            if stale_inst_:      # 保底：個股法人是舊的那天 → 文案不引用（不拿昨天的數字冒充今天）
                it_ = {}
            for s_ in ok:
                if s_["name"] in ("streak-foreign", "streak-trust") and it_:      # 法人排行也只列個股（2026-10-26 Andy「法人也排除ETF」）
                    b_, s2_ = NAT.inst_top(it_, "foreign" if s_["name"] == "streak-foreign" else "trust", 10, dict(NAME_MAP))
                    s_["read"] = {**(s_.get("read") or {}), "buy": [r["name"] for r in b_], "sell": [r["name"] for r in s2_]}
                if s_["name"] in ("credit-rank", "credit-short") and mf_:
                    up_, dn_ = NAT.credit_top(mf_, "short" if s_["name"] == "credit-short" else "rank")
                    s_["read"] = {**(s_.get("read") or {}), "up": [r["code"] for r in up_], "down": [r["code"] for r in dn_]}
            if args.kind == "close":
                try:
                    rr_ = next((x.get("read") for x in ok if x["name"] == "retail-ratio"), None) or []
                    cr_ = {}      # 融資移到盤前
                    im_ = {} if "inst-today" in PARTIAL else (fetch_json(base, "inst_market") or {})      # 市場總額法人不是今天 → 不寫
                    mh_ = fetch_json(base, "market_heat") or {}
                    if PARTIAL and DATE_ISO.get("market-breadth") and DATE_ISO["market-breadth"] != data_date:
                        mh_ = {}      # 保底時大盤／漲跌家數也要是今天才寫（不拿舊的冒充）
                    if SUPPLEMENT:      # 補充貼文只寫法人：不重複主貼文的指數、期貨、散戶
                        ok.append({"name": "analysis", "ok": True, "read": close_reads(im_, {}, it_ or {}, {}, [], cr_)})
                    else:
                        ok.append({"name": "analysis", "ok": True, "read": close_reads(im_, fetch_json(base, "fut_oi") or {},
                                                                                       it_ or {}, mh_, rr_, cr_)})
                except Exception as exc:  # noqa: BLE001
                    log("  ⚠ 盤面分析失敗（不擋發文）：", str(exc)[:120])
            if it_:
                ok.append({"name": "etf-buy", "ok": True, "read": {k_: [r["name"] for r in NAT.etf_buy(it_, k_, 10, dict(NAME_MAP))] for k_ in ("foreign", "trust")}})
        text_ = build_text(args.kind, stamp_full, ok, data_date, today_ymd)
        reply_ = ""
        if args.kind in ("intraday", "close"):
            # 2026-10-29 Andy：「盤前、盤中、盤後……除了基本的盤面解讀之外，還需要搭配當下的一些新聞消息，三到五個主題」
            # → 盤面解讀之後、hashtag 之前加「📰 新聞焦點」；主文放不下就改放回覆串。新聞不足或出錯只寫 alert，絕不擋整篇。
            try:
                import social_live_news as LN
                news_now_ = datetime.fromisoformat(args.now).replace(tzinfo=TPE) if args.now else now_tpe()
                nf_ = LN.for_post(args.kind, text_, news_now_, HASHTAGS[args.kind], THREADS_MAX, fresh=args.fresh_news, log=log)
                text_, reply_ = nf_["text"], nf_["reply"]
                if nf_["alert"]:
                    log("  ⚠", nf_["alert"])
                    with open(out / "alert.txt", "a", encoding="utf-8") as fa_:
                        fa_.write(nf_["alert"] + "\n")
            except Exception as exc:  # noqa: BLE001
                log("  ⚠ 新聞焦點失敗（不擋發文）：", str(exc)[:120])
                with open(out / "alert.txt", "a", encoding="utf-8") as fa_:
                    fa_.write(f"{args.kind} 貼文的新聞焦點失敗（{str(exc)[:100]}），這篇照發、少了新聞那段。\n")
        manifest = {
            "kind": args.kind,
            "taken_at": now_tpe().isoformat(timespec="seconds"),
            "data_date": data_date,
            "threads": {"text": text_, "images": threads_imgs, **({"reply": reply_} if reply_ else {})},
            "story": stories,
            **({"partial": list(PARTIAL)} if PARTIAL else {}),
            **({"supplement": True} if SUPPLEMENT else {}),
        }
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
        save_recent(out)
        (out / "caption.txt").write_text(manifest["threads"]["text"] + ("\n\n" + reply_ if reply_ else "") + "\n", "utf-8")   # 給 Andy 手動貼 IG（限動 API 不能附文字與連結貼紙）
        log("manifest：", out / "manifest.json", "；文案字數", len(manifest["threads"]["text"]))
        return 0
    finally:
        if srv:
            srv.shutdown()


if __name__ == "__main__":
    sys.exit(main())
