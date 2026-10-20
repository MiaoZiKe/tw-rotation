"""功能介紹影片 06：今日事件＋精選文章 —— 素材錄製（沿用 05 的 capture_flow.py：逐格算圖錄影、鏡頭外框逐格紀錄、時鐘與字型）。

一律「未登入訪客」的真實畫面（Andy 10-19）。錄的是 origin/main 的 site/（本分支的 site/ 比 main 舊；FEAT_SITE 指到 main 的 worktree），
資料用該 worktree 本機 `python -m pipeline.build_payload` 重算。
正式站有會員系統（account_config 由部署寫入 API 網址），訪客的行為要靠伺服器回答：今日事件「訪客累計 5 次」由 /v1/total/use 計數、
文章只看得到標題。錄影時用假的會員 API（只在錄影瀏覽器裡，不改 site/）重現「第一次來的訪客」：不登入、/v1/total/use 回「算到、已用 1 次」、
其他端點回空 → 畫面＝正式站訪客實際看到的（文章列表只有標題、點進去是全文鎖卡；今日事件清單看得到，最上面一行「訪客預覽：已用 1／5 次」）。

法遵（growth_plan_1018.md 第九節）：
· 今日事件的「券商」列（券商目標價，9-1 第 2 條）整列模糊，也不點「券商」分類；
· 新聞標題、文章標題、最近更新清單裡出現上市櫃公司名稱或代號的，標題模糊（9-1 第 1 條：不點名個股當主角）；個股連結一律模糊。
  公司名稱清單取自網站自己的 data/stocks.json（錄影瀏覽器裡讀，只在錄影時套用）。

用法（repo 根目錄）：
    FEAT_SITE=<main worktree>/site python docs/marketing/videos/feature_series/06_events_articles/capture_ev.py --dev d [--shots open,guide]
輸出（大檔，放 scratchpad）：<out>/<dev>_<鏡頭>.mp4 ＋ <out>/<dev>_<鏡頭>.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
os.environ.setdefault("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06")
sys.path.insert(0, str(HERE.parent / "05_fund_flow"))
import capture_flow as F  # noqa: E402  （05 的錄影器：Rec、A、字型、時鐘、拉桿等）

F.CAM_JS = F.CAM_JS.replace(
    "const uni = (rs, p) => { if (!rs.length) return null;",
    "const uni = (rs, p0) => { if (!rs.length) return null; const p = Array.isArray(p0) ? p0[0] : p0, q = Array.isArray(p0) ? p0[1] : p0;").replace(
    "return [x0 - p, y0 - p, x1 - x0 + 2 * p, y1 - y0 + 2 * p]; };", "return [x0 - p, y0 - q, x1 - x0 + 2 * p, y1 - y0 + 2 * q]; };")
assert "p0[1]" in F.CAM_JS
C = F.C
SCR = Path(os.environ["FEAT_SCR"])
SITE = Path(os.environ.get("FEAT_SITE", str(SCR / "main_wt" / "site")))
C.SITE = SITE
FPS = F.FPS
DEVS = F.DEVS

# 鏡頭選擇器（在 05 的 CAM_JS 上加兩種）：firstn:N:sel ＝ 前 N 個「看得到」的元素；可選 opt:sel ＝ 有就算、沒有不算（例：自繪下拉清單）
F.CAM_JS = F.CAM_JS.replace(
    "      else if (s.startsWith('all:'))",
    "      else if (s.startsWith('firstn:')) { const i = s.indexOf(':', 7); const n = +s.slice(7, i);"
    " [...document.querySelectorAll(s.slice(i + 1))].filter(e => e.getClientRects().length && e.getBoundingClientRect().height > 2).slice(0, n).forEach(e => out.push(e.getBoundingClientRect())); }\n"
    "      else if (s.startsWith('txt:')) document.querySelectorAll(s.slice(4)).forEach(e => { if (!e.getClientRects().length) return; const b = e.getBoundingClientRect();"
    " const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { if (!n.textContent.trim()) continue;"
    " const pe = n.parentElement; if (pe && (getComputedStyle(pe).visibility === 'hidden' || pe.closest('[hidden]'))) continue;"
    " const cl = window.__vclip(pe, b);"
    " const rg = document.createRange(); rg.selectNodeContents(n); for (const q of rg.getClientRects()) {"
    " const l = Math.max(q.left, cl.l), t = Math.max(q.top, cl.t), r = Math.min(q.right, cl.r), bt = Math.min(q.bottom, cl.b);"
    " if (r - l > 1 && bt - t > 1) { const hx = (l + r) / 2, hy = (t + bt) / 2, h = (hx >= 0 && hy >= 0 && hx < innerWidth && hy < innerHeight) ? document.elementFromPoint(hx, hy) : null;"
    " if (h && !(e.contains(h) || h.contains(e))) continue;"
    " out.push({ left: l, top: t, right: r, bottom: bt, width: r - l, height: bt - t }); } } } });\n"
    "      else if (s.startsWith('all:'))")

API = "https://acct.video.test"
PROD_API = "https://tw-account.kcq01010909.workers.dev"   # 正式站會員後端（只用來讀公開那篇的全文）


_ART_CACHE: dict = {}


def guest_api(ctx):
    """正式站的訪客：不登入；今日事件的訪客額度回「算到」（第一次來的訪客，已用 1／5 次）；其他端點回空。"""
    def handle(route):
        req = route.request
        path = req.url.split(API, 1)[-1].split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            body = json.loads(req.post_data or "{}")
        except Exception:  # noqa: BLE001
            body = {}
        out = {}
        if path == "/v1/perm/me":
            # 訪客身分（沒權杖）：who=guest。feats 給空物件＝不另外加鎖（跟沒有回應時的預設一樣），只是讓權限狀態變成「伺服器已回覆」，
            # 文章頁不用空等 4 秒（articles.js permReady）才畫內容
            out = {"who": "guest", "plan": "guest", "planName": "訪客", "feats": {}}
        elif path == "/v1/total/use":
            out = {"ok": True, "limit": 5, "used": [body.get("key")], "g": "gvideo"}
        elif path == "/v1/articles/get" and (req.post_data or "") in _ART_CACHE:
            out = _ART_CACHE[req.post_data or ""]
        elif path == "/v1/articles/get":
            import urllib.request
            rq = urllib.request.Request(PROD_API + "/v1/articles/get", data=(req.post_data or "{}").encode(),
                                        headers={"content-type": "text/plain", "Origin": "https://miaozike.github.io", "User-Agent": "Mozilla/5.0"}, method="POST")
            try:
                out = json.loads(urllib.request.urlopen(rq, timeout=20).read())
                if out.get("ok"):
                    _ART_CACHE[req.post_data or ""] = out   # 同一次錄影只向正式站讀一次（之後點進去不用等網路，畫面不卡「載入中…」）
            except Exception as exc:  # noqa: BLE001
                out = {"error": "net", "why": str(exc)[:80]}
        elif path == "/v1/articles/stats":
            out = {"views": {}}
        route.fulfill(status=200, body=json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})
    ctx.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": API}) + ";")
    ctx.route(API + "/**", handle)


# 法遵模糊（只在錄影的瀏覽器裡）
CLIP_JS = r"""
window.__vclip = (pe, b) => { const c = { l: b.left, t: b.top, r: b.right, b: b.bottom };
  for (let a = pe; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
    const cs = getComputedStyle(a), own = a === pe;
    if (!own && cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
    const r = a.getBoundingClientRect();
    const pl = own ? parseFloat(cs.paddingLeft) || 0 : 0, pr = own ? parseFloat(cs.paddingRight) || 0 : 0;
    const bl = parseFloat(cs.borderLeftWidth) || 0, br = parseFloat(cs.borderRightWidth) || 0;
    c.l = Math.max(c.l, r.left + bl + pl); c.r = Math.min(c.r, r.right - br - pr);
    if (own || cs.overflowY !== 'visible') { c.t = Math.max(c.t, r.top); c.b = Math.min(c.b, r.bottom); } }
  return c; };
"""
BLUR_CSS = ("a[href^='#stock/'],.__vblur{filter:blur(7px)!important}.__vblurrow{filter:blur(6px)!important}"
            "#artQuota,#evQuota{display:none!important}.__vquota{visibility:hidden!important}")
BLUR_JS = r"""
(() => { const css = %s; let RX = null;
  const TEXT_SEL = '#evList .ev > a, .artc .tt, #artSide .rc a span, .artbc, #v-articles h1, #v-articles h2';
  const sweep = () => {
    // 會員額度字樣：「限時公開・不佔額度」只留「限時公開」；「全文需 Plus 以上」整段藏起來（版面不動）
    const root = document.getElementById('v-articles');
    if (root) { const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const v = n.nodeValue;
      if (v.indexOf('不佔額度') >= 0) n.nodeValue = v.replace(/[・·]?\s*不佔額度/, '');
      else if (/全文需\s*Plus/.test(v) && n.parentElement) (n.parentElement.closest('.lk') || n.parentElement).classList.add('__vquota'); } }
    document.querySelectorAll('#evList .ev').forEach(r => { const c = r.querySelector('.cat'); if (c && c.textContent.trim() === '券商') r.classList.add('__vblurrow'); });
    if (!RX) return;
    document.querySelectorAll(TEXT_SEL).forEach(e => { const t = e.textContent || ''; if (RX.test(t) || /[(（]\s*\d{4,6}\s*[)）]/.test(t)) e.classList.add('__vblur'); else e.classList.remove('__vblur'); });
  };
  window.__vblurSweep = sweep;
  const go = () => { const st = document.createElement('style'); st.id = '__blurco'; st.textContent = css; (document.head || document.documentElement).appendChild(st);
    new MutationObserver(sweep).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
    fetch('data/stocks.json').then(r => r.json()).then(list => {
      const names = [...new Set(list.map(s => String(s.name || '').replace(/\*/g, '').trim()).filter(n => n.length >= 2))].sort((a, b) => b.length - a.length);
      RX = new RegExp(names.map(n => n.replace(/[.*+?^${}()|[\]\\-]/g, '\\$&')).join('|'));
      window.__vblurReady = true; sweep(); }).catch(() => { window.__vblurReady = true; }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(BLUR_CSS)

SEL_OVERLAY_JS = r"""([s, v]) => { const e = document.querySelector(s); if (!e) return; const r = e.getBoundingClientRect();
  const d = document.createElement('div'); d.id = '__vsel';
  d.style.cssText = `position:fixed;left:${r.left}px;top:${r.bottom + 2}px;min-width:${r.width}px;max-height:162px;overflow:hidden;z-index:2147483600;background:#fff;border:1px solid #c9d3e0;border-radius:8px;box-shadow:0 8px 24px rgba(15,23,42,.18);padding:4px 0;font:14px/1.2 'Noto Sans TC',sans-serif;color:#1f2937`;
  d.innerHTML = [...e.options].map(o => `<div data-v="${o.value}" style="padding:7px 14px;white-space:nowrap;${o.value === e.value ? 'background:#e8f0fb;color:#1d4ed8;font-weight:600' : ''}">${o.text}</div>`).join('');
  const st = document.createElement('style'); st.textContent = '#__vsel .hv{background:#2563eb!important;color:#fff!important}'; d.appendChild(st);
  document.body.appendChild(d); }"""


class A(F.A):
    def select_show(self, sel, value, label="", ms=420):
        """原生下拉在截圖裡畫不出彈出清單：同位置蓋一張自繪的展開清單（仿網站樣式），游標移到選項、點下、收起，再真的選值（清單內容跟著換）。"""
        b = self.box(sel, scroll=False)
        if not b:
            self.note(f"找不到 {sel}")
            return False
        x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        self.move(x, y, ms)
        self.wait(120)
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", expect=sel)
        self.targets[-1]["label"] = "日期下拉"
        self.frame()
        self.pg.evaluate(SEL_OVERLAY_JS, [sel, value])
        self.wait(450)
        ob = self.pg.locator(f'#__vsel [data-v="{value}"]').first.bounding_box()
        ox, oy = ob["x"] + ob["width"] / 2, ob["y"] + ob["height"] / 2
        if not self.mob:
            self.move(ox, oy, 380)
        self.pg.evaluate("(v) => { const e = document.querySelector('#__vsel [data-v=\"' + v + '\"]'); if (e) e.classList.add('hv'); }", value)
        self.wait(260)
        if self.mob:
            self.cursor(False); self._put(ox, oy); self.cursor(True)
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [ox, oy])
        self.record_target(ox, oy, "click", expect=f'#__vsel [data-v="{value}"]')
        tg = self.targets[-1]
        tg["label"] = label
        tg["rect_center"] = self._vpt(ox, oy)
        tg["measured_by"] = "自繪展開清單的選項外框"
        self.frame()
        self.pg.evaluate("() => { const e = document.getElementById('__vsel'); if (e) e.remove(); }")
        self.pg.locator(sel).first.select_option(value)
        self.frame()
        if self.mob:
            self.wait(200); self.cursor(False); self.pg.mouse.move(*self.PARK)
        return True

    def type_text(self, sel, text, ms_per=140):
        self.pg.locator(sel).first.focus()
        for ch in text:
            self.pg.keyboard.type(ch)
            self.wait(ms_per)


# ------------------------------------------------------------------ 共用
def goto(pg, hash_, wait=4000):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(400)


EV_EDGES = ["txt:#evList .ev", "txt:#evFilters button", "#evDate", "txt:#evQuota", "txt:#side .side-h h3", "txt:#__vsel div"]
NAV_EDGES = ["txt:#evToggle", "txt:#tabs .tab", ".search input"]
TES_EDGES = ["txt:#artPost .artmeta", "txt:#artPost .artttl", "txt:#artHd", "txt:#artBody > figure", "txt:#artBody > p", "txt:#artBody > h4", "txt:#artBody > ul"]
ART_EDGES = ["txt:.artc", "txt:#artCats>button", "txt:#artSide .gps button", "#artQ", "txt:#artSide .cr", "txt:.artflt", "txt:#artSide h5"]
EV_HEAD = ["#side .side-h", "#evFilters"]


def ev_rows(n, d=False):
    head = ["#evDate", "#side .side-h h3", "#evFilters"] if d else EV_HEAD   # 桌機：抽屜上緣就是視窗上緣，取景上緣改落在標題列內
    return head + [f"firstn:{n}:#evList .ev", "#__vsel"]


def open_drawer_now(pg, mob):
    """錄影開始前就打開今日事件抽屜（開場直接看清單）。"""
    if mob:
        pg.locator("#m4Burger").first.click()
        pg.wait_for_timeout(900)
        pg.locator('.m4item[data-act="events"]').first.click()
    else:
        pg.locator("#evToggle").first.click()
    pg.wait_for_timeout(2500)


# ------------------------------------------------------------------ 網頁版（1600×900）
def d_open(pg, a, start):
    goto(pg, "#overview", 3500)
    open_drawer_now(pg, False)
    a.x, a.y = 1300, 600
    start()
    a.cam(ev_rows(2, True), [-12, 0], "今日事件清單", edges=EV_EDGES, zoom=True)
    a.say("新聞多到看不完？", "face_sweat")
    a.hover("#evList .ev > a >> nth=0", 500, dx=0.3)
    a.idle(500)
    a.say("哪些事件跟市場有關？", "globe")
    a.hover("#evList .ev > a >> nth=1", 600, dx=0.3)
    a.idle(600)
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    a.x, a.y = 600, 400
    start()
    # 左側選單上段（搜尋框、事件、今日市場、總覽）：以 4 倍像素錄，推近後選單佔畫面寬 ≥70%
    a.cam(["rect:4,84,218,148"], 0, "推近：左側選單「事件」", minw=200, edges=NAV_EDGES, zoom=True)
    a.say("左側選單「事件」", "point_r_v2")
    a.hover("#evToggle", 500)
    a.say("點一下就打開", "tap")
    a.click("#evToggle", label="選單：事件")
    a.wait(1600)
    a.cam(ev_rows(2, True), [-12, 0], "今日事件抽屜", edges=EV_EDGES, zoom=True)
    a.idle(700)
    a.settle()


def d_events(pg, a, start):
    goto(pg, "#overview", 3500)
    open_drawer_now(pg, False)
    a.x, a.y = 1300, 500
    start()
    a.cam(ev_rows(2, True), [-12, 0], "推近：分類＋清單", edges=EV_EDGES, zoom=True)
    a.say("依分類切換新聞", "news")
    first = True
    for c in ("台股", "科技", "總經"):
        a.click(f'#evFilters button[data-c="{c}"]', ms=380, pause=150, label=f"分類：{c}")
        a.wait(1000)
        if first:
            a.say("清單馬上換一批", "face_nod_v2")
        first = False
    # 日期這一拍：取景固定＝標題列＋分類＋2 則＋自繪展開清單會用到的高度（清單打開時鏡頭不跳）
    pg.evaluate(SEL_OVERLAY_JS, ["#evDate", "all"])   # 先量自繪展開清單實際的高度（量完就拿掉，不入鏡：錄影還沒推進這一格）
    ov = pg.evaluate(C.RECT_JS, "#__vsel")
    pg.evaluate("() => document.getElementById('__vsel').remove()")
    sb = pg.evaluate(C.RECT_JS, "#evDate")
    drop = f"rect:{min(sb[0], ov[0]):.1f},{sb[1]:.1f},{max(sb[2], ov[2]):.1f},{ov[1] + ov[3] - sb[1] + 8:.1f}"
    a.cam(ev_rows(2, True) + [drop], [-12, 0], "推近：日期下拉＋清單", edges=EV_EDGES, zoom=True)
    a.say("日期選最近一週", "calendar")
    opts = pg.evaluate("() => [...document.querySelector('#evDate').options].map(o => o.value).filter(v => v !== 'all')")
    for v in opts[:3]:
        a.select_show("#evDate", v, f"日期：{v[5:].replace('-', '/')}")
        a.wait(900)
    a.settle()


def warm_articles(pg):
    """錄影開始前先開一次文章頁（索引進快取）再回總覽：錄影時鐘是逐格推進的，第一次載入會在畫面上停 3 秒「載入中…」。"""
    goto(pg, "#articles", 3500)
    pg.wait_for_function("() => document.querySelectorAll('#v-articles .artc').length > 3", timeout=15000)


UNION_JS = r"""([sels, snapSel]) => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const s of sels) { let els; const m = /^firstn:(\d+):(.*)$/.exec(s);
    els = m ? [...document.querySelectorAll(m[2])].slice(0, +m[1]) : [document.querySelector(s)];
    for (const e of els) { if (!e) continue; const r = e.getBoundingClientRect(); x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); } }
  // 下緣吸附到「沒有任何文字外框橫跨」的水平線（從 y1 往下找），框邊才不會切過文字
  const boxes = []; const root = document.getElementById('v-articles'); const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { if (!n.textContent.trim()) continue; const pe = n.parentElement; if (!pe || pe.closest('[hidden]') || getComputedStyle(pe).visibility === 'hidden') continue;
    const rg = document.createRange(); rg.selectNodeContents(n); for (const q of rg.getClientRects()) if (q.right > x0 && q.left < x1 && q.height > 1) boxes.push([q.top, q.bottom]); }
  let y = y1; const inside = (v) => boxes.some(([t, b]) => t + 1 < v && v < b - 1);
  for (let k = 0; k < 800 && inside(y); k++) y += 0.5;
  return [x0, y0, x1 - x0, y - y0]; }"""


def fixed_rect(pg, sels):
    """一組元素外框的聯集 → 固定的 'rect:'（篩選時卡片數、族群鈕數會變，取景固定在「全部文章」那一刻的範圍，鏡頭不跟著內容伸縮）；
    下緣吸附到沒有文字橫跨的水平線。"""
    x, y, w, h = pg.evaluate(UNION_JS, [sels, None])
    return f"rect:{x:.1f},{y:.1f},{w:.1f},{h:.1f}"


def d_arts(pg, a, start):
    warm_articles(pg)
    goto(pg, "#overview", 3500)
    a.x, a.y = 600, 450
    start()
    a.cam(["rect:6,180,214,100"], 0, "推近：左側選單「精選文章」", minw=200, edges=NAV_EDGES, zoom=True)
    a.say("產業題材想一次看懂？", "face_curious")
    a.click('#tabs .tab[data-view="articles"]', label="選單：精選文章")
    a.wait(1800)
    a.cam(["#v-articles .artcard h3", "#artCats", ".artflt", "firstn:6:#v-articles .artc", "#artSide section:nth-of-type(1)", "#artSide section:nth-of-type(2)"], 6, "精選文章（全圖定位）", edges=ART_EDGES)
    a.say("文章分成三大類", "folder")
    a.idle(500)
    FX = fixed_rect(pg, ["#artCats", "firstn:6:#v-articles .artc", "#artSide section:nth-of-type(1)", "#artSide section:nth-of-type(2)"])
    a.cam([FX], 0, "推近：分類分頁＋文章卡", minw=F.ZMIN, edges=ART_EDGES, zoom=True)
    for c, lab in (("news", "分類：比比快訊"), ("intro", "分類：比比產業鏈"), ("know", "分類：比比知識")):
        a.click(f'#artCats>button[data-cat="{c}"]', ms=380, pause=150, label=lab)
        a.wait(1000)
    a.click('#artCats>button[data-cat="all"]', ms=380, pause=150, label="分類：全部文章")
    a.wait(700)
    a.cam([FX], 0, "推近：熱門族群＋篩選結果", minw=F.ZMIN, edges=ART_EDGES, zoom=True)
    a.say("點族群，只看相關文章", "magnifier")
    for g, lab in (("foundry", "族群：晶圓代工"), ("ai_adv_packaging", "族群：AI 先進封裝"), ("memory_module", "族群：記憶體模組")):
        a.click(f'#artSide .gps button[data-gid="{g}"]', ms=380, pause=150, label=lab)
        a.wait(1000)
    a.click('#artClr', ms=380, pause=150, label="清除篩選")
    a.wait(700)
    a.cam([FX], 0, "推近：關鍵字搜尋", minw=F.ZMIN, edges=ART_EDGES, zoom=True)
    a.say("關鍵字搜標題", "magnifier")
    a.click("#artQ", ms=380, pause=120, label="搜尋框")
    a.type_text("#artQ", "Roadster")
    a.wait(800)
    a.hover('.artc[data-id="2026-10-17-news-tesla"]', 500)
    a.say("特斯拉這篇就在這", "spotlight")
    a.idle(700)
    a.settle()


def d_end(pg, a, start):
    warm_articles(pg)
    goto(pg, "#articles", 2500)
    a.x, a.y = 900, 500
    start()
    a.cam(["#artCats", "firstn:6:#v-articles .artc", "#artSide section:nth-of-type(1)", "#artSide section:nth-of-type(2)"], 6, "精選文章", edges=ART_EDGES)
    a.say("事件＋文章，一站看懂", "proud_shine")
    a.move(700, 500, 900)
    a.cam(["#artCats", "firstn:3:#v-articles .artc"], 6, "推近：分類分頁＋第一排文章", minw=F.ZMIN, edges=ART_EDGES, zoom=True)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(1000, 600, 900)
    a.settle()


# ------------------------------------------------------------------ 手機版（390 寬 m4 版面）
M_EV = ["#side .side-h", "#evFilters"]


def m_open(pg, a, start):
    goto(pg, "#overview", 3500)
    open_drawer_now(pg, True)
    start()
    a.cam(ev_rows(4), -12, "今日事件清單", edges=EV_EDGES)
    a.say("新聞多到看不完？", "face_sweat")
    a.idle(900)
    a.cam(["firstn:2:#evList .ev"], -10, "推近：前兩則事件", edges=EV_EDGES)   # 第二拍推近到前兩則（鏡頭在動，畫面不停住）
    a.say("哪些事件跟市場有關？", "globe")
    a.idle(900)
    a.settle()


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-act="events"]', '.m4item[data-v="overview"]', '.m4item[data-v="articles"]'], 10, "選單抽屜", edges=[])
    a.say("點「事件」", "tap")
    a.click('.m4item[data-act="events"]', label="選單：事件")
    a.wait(1700)
    a.cam(ev_rows(3), -10, "今日事件抽屜", edges=EV_EDGES)
    a.idle(600)
    a.settle()


def m_events(pg, a, start):
    goto(pg, "#overview", 3500)
    open_drawer_now(pg, True)
    start()
    a.cam(ev_rows(3), -10, "分類＋清單", edges=EV_EDGES)
    a.say("依分類切換新聞", "news")
    first = True
    for c in ("台股", "科技", "總經"):
        a.click(f'#evFilters button[data-c="{c}"]', label=f"分類：{c}")
        a.wait(1000)
        if first:
            a.say("清單馬上換一批", "face_nod_v2")
        first = False
    a.say("日期選最近一週", "calendar")
    opts = pg.evaluate("() => [...document.querySelector('#evDate').options].map(o => o.value).filter(v => v !== 'all')")
    for v in opts[:3]:
        a.select_show("#evDate", v, f"日期：{v[5:].replace('-', '/')}")
        a.wait(900)
    a.settle()


def m_arts(pg, a, start):
    warm_articles(pg)
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("產業題材想一次看懂？", "face_curious")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="articles"]', '.m4item[data-v="overview"]', '.m4item[data-act="events"]'], 10, "選單抽屜", edges=[])
    a.click('.m4item[data-v="articles"]', label="選單：精選文章")
    a.wait(1700)
    a.cam_view("捲動")
    a.scroll_to_el("#artCats", 70, 500)
    a.cam(["#artCats", "firstn:1:#v-articles .artc"], 6, "分類分頁＋第一篇", edges=ART_EDGES)
    a.say("文章分成三大類", "folder")
    for c, lab in (("news", "分類：比比快訊"), ("intro", "分類：比比產業鏈"), ("know", "分類：比比知識")):
        a.click(f'#artCats>button[data-cat="{c}"]', label=lab)
        a.wait(1000)
    a.click('#artCats>button[data-cat="all"]', label="分類：全部文章")
    a.wait(600)
    a.cam_view("捲動")
    a.scroll_to_el("#artQ", 80, 500)
    a.cam(["#artGrp", ".artflt"], 6, "族群下拉", edges=ART_EDGES)
    a.say("點族群，只看相關文章", "magnifier")
    a.click("#artGrp .twms-btn", label="族群下拉")
    a.wait(500)
    a.cam(["#artGrp", ".twms-pan"], 4, "族群清單", edges=ART_EDGES + ["txt:.twms-pan .twms-o"])
    a.wait(300)
    for g, lab in (("foundry", "族群：晶圓代工"), ("ai_adv_packaging", "族群：AI 先進封裝"), ("memory_module", "族群：記憶體模組")):
        a.click(f'.twms-pan .twms-o[data-v="{g}"]', label=lab)
        a.wait(900)
    a.cam([".artflt", "firstn:1:#v-articles .artc", ".twms-pan"], 6, "篩選結果", edges=ART_EDGES + ["txt:.twms-pan .twms-o"])   # 先拉遠（清單還開著），收起後只剩篩選列＋文章
    a.click("#artGrp .twms-btn", label="收起族群清單")
    a.wait(700)
    a.say("篇數跟著變", "face_nod_v2")
    a.wait(900)
    a.click("#artClr", label="清除篩選")
    a.wait(600)
    a.cam(["#artQ", ".artflt", "firstn:1:#v-articles .artc"], 6, "關鍵字搜尋", edges=ART_EDGES)
    a.say("關鍵字搜標題", "magnifier")
    a.click("#artQ", label="搜尋框")
    a.type_text("#artQ", "Roadster")
    a.wait(900)
    a.say("特斯拉這篇就在這", "spotlight")
    a.idle(900)
    a.settle()


def m_end(pg, a, start):
    goto(pg, "#articles", 3500)
    scroll = pg.evaluate("() => document.querySelector('#artCats').getBoundingClientRect().top + scrollY - 70")
    pg.evaluate("(y) => scrollTo(0, y)", scroll)
    pg.wait_for_timeout(600)
    start()
    a.cam(["#artCats", "firstn:1:#v-articles .artc"], 6, "精選文章", edges=ART_EDGES)
    a.say("事件＋文章，一站看懂", "proud_shine")
    a.idle(1300)
    a.cam(["firstn:1:#v-articles .artc"], 6, "推近：第一篇文章", edges=ART_EDGES)   # 第二拍推近（鏡頭在動，畫面不停住）
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.idle(1300)
    a.settle()


BAR_JS = r"""([k, idx]) => { const f = [...document.querySelectorAll('#artBody .artchart')][k]; if (!f) return null;
  const el = f.querySelector('[_echarts_instance_]'); const c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const o = c.getOption(), s = o.series[0], v = s.data[idx], val = (v && v.value !== undefined) ? v.value : v;
  const horiz = !!(o.yAxis && o.yAxis[0] && o.yAxis[0].data);
  const cat = horiz ? o.yAxis[0].data[idx] : o.xAxis[0].data[idx];
  const p = horiz ? [c.convertToPixel({ xAxisIndex: 0 }, val / 2), c.convertToPixel({ yAxisIndex: 0 }, cat)]
                  : [c.convertToPixel({ xAxisIndex: 0 }, cat), c.convertToPixel({ yAxisIndex: 0 }, val / 2)];
  const r = el.getBoundingClientRect(); return [r.left + p[0], r.top + p[1], String(cat)]; }"""


def bar_click(a, k, idx, label):
    x, y, cat = a.pg.evaluate(BAR_JS, [k, idx])
    a.move(x, y, 380) if not a.mob else None
    x2, y2, _ = a.pg.evaluate(BAR_JS, [k, idx])
    a.note(f"點長條 {label}")
    a.click_xy(x2, y2, 1, 150, expect=f"#artBody .artchart >> nth={k}")
    tg = a.targets[-1]
    tg["label"] = label
    tg["rect_center"] = a._vpt(x2, y2)
    tg["measured_by"] = "依數值換算的長條位置（ECharts convertToPixel）"


def fig_sel(k):
    return f"#artBody > figure:nth-of-type({k + 1})"


def scroll_fig(a, k, off, ms=800):
    y = a.pg.evaluate("([k, o]) => { const f = [...document.querySelectorAll('#artBody > figure')][k]; return f.getBoundingClientRect().top + scrollY - o; }", [k, off])
    a.scroll(to_y=y, ms=ms)


def prep_tesla(pg):
    """錄影前：文章清單已搜尋「Roadster」（接續上一段結尾的畫面），只剩特斯拉那一篇。"""
    warm_articles(pg)
    goto(pg, "#article/2026-10-17-news-tesla", 4000)   # 先開一次那篇（全文進快取），再回清單
    pg.wait_for_function("() => !!document.querySelector('#artBody .artchart canvas')", timeout=20000)
    goto(pg, "#articles", 2500)
    pg.locator("#artQ").first.fill("Roadster")
    pg.wait_for_timeout(1200)


def d_tesla(pg, a, start):
    prep_tesla(pg)
    card = '.artc[data-id="2026-10-17-news-tesla"]'
    a.x, a.y = 1000, 600
    start()
    a.cam([".artflt", card, "#artSide section:nth-of-type(1)", "#artSide section:nth-of-type(2)"], 6, "推近：特斯拉那篇（限時公開）", minw=F.ZMIN, edges=ART_EDGES, zoom=True)
    a.say("限時公開，免登入看", "face_cool")
    a.click(card, ms=420, pause=200, label="點進特斯拉那篇")
    a.until("() => !!document.querySelector('#artBody .artchart canvas')", 8000)
    a.wait(500)
    a.cam(["#artPost .artmeta", "#artPost .artttl", "#artHd"], 8, "推近：標題、相關族群、摘要", minw=F.ZMIN, edges=TES_EDGES, zoom=True)
    a.say("發表會隔天，族群怎麼動", "surprise_jump")
    a.move(700, 400, 900)
    a.idle(500)
    a.cam_view("捲動")
    scroll_fig(a, 0, 90)
    a.cam([fig_sel(0)], 6, "推近：圖表 1 族群漲跌", minw=F.ZMIN, edges=TES_EDGES, zoom=True)
    a.say("點長條看數字", "magnifier")
    for i, lab in ((0, "類比與功率 IC"), (3, "加權指數"), (5, "第三代半導體")):
        bar_click(a, 0, i, f"圖表 1：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 1, 90)
    a.cam([fig_sel(1)], 6, "推近：圖表 2 加速規格", minw=F.ZMIN, edges=TES_EDGES, zoom=True)
    a.say("0.81 秒有多快？", "rocket")
    for i, lab in ((0, "Roadster 推進器版"), (3, "Model S Plaid")):
        bar_click(a, 1, i, f"圖表 2：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 2, 90)
    a.cam([fig_sel(2)], 6, "推近：圖表 3 季交車量", minw=F.ZMIN, edges=TES_EDGES, zoom=True)
    a.say("交車量逐季對照", "wow")
    for i, lab in ((2, "2026 Q1"), (4, "2026 Q3")):
        bar_click(a, 2, i, f"圖表 3：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 3, 200)
    a.cam([fig_sel(3)], 6, "推近：步驟圖 接下來看什麼", minw=F.ZMIN, edges=TES_EDGES, zoom=True)
    a.say("接下來看這三個日期", "calendar")
    for i in range(3):
        a.hover(f"{fig_sel(3)} .sti:nth-child({i + 1}) .stc", 520)
        a.wait(450)
    a.settle()


def m_tesla(pg, a, start):
    prep_tesla(pg)
    card = '.artc[data-id="2026-10-17-news-tesla"]'
    y = pg.evaluate("() => document.querySelector('#artQ').getBoundingClientRect().top + scrollY - 70")
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(500)
    start()
    a.cam(["#artQ", card], 6, "特斯拉那篇（限時公開）", edges=ART_EDGES)
    a.say("限時公開，免登入看", "face_cool")
    a.click(card, label="點進特斯拉那篇")
    a.until("() => !!document.querySelector('#artBody .artchart canvas')", 8000)
    a.wait(500)
    a.cam(["#artPost .artmeta", "#artPost .artttl", "#artHd"], 6, "標題、相關族群、摘要", edges=TES_EDGES)
    a.say("發表會隔天，族群怎麼動", "surprise_jump")
    a.idle(900)
    a.cam_view("捲動")
    scroll_fig(a, 0, 70)
    a.cam([fig_sel(0)], 4, "圖表 1 族群漲跌", edges=TES_EDGES)
    a.say("點長條看數字", "magnifier")
    for i, lab in ((0, "類比與功率 IC"), (3, "加權指數"), (5, "第三代半導體")):
        bar_click(a, 0, i, f"圖表 1：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 1, 70)
    a.cam([fig_sel(1)], 4, "圖表 2 加速規格", edges=TES_EDGES)
    a.say("0.81 秒有多快？", "rocket")
    for i, lab in ((0, "Roadster 推進器版"), (3, "Model S Plaid")):
        bar_click(a, 1, i, f"圖表 2：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 2, 70)
    a.cam([fig_sel(2)], 4, "圖表 3 季交車量", edges=TES_EDGES)
    a.say("交車量逐季對照", "wow")
    for i, lab in ((2, "2026 Q1"), (4, "2026 Q3")):
        bar_click(a, 2, i, f"圖表 3：{lab}")
        a.wait(800)
    a.cam_view("捲動")
    scroll_fig(a, 3, 120)
    a.cam([fig_sel(3)], 4, "步驟圖 接下來看什麼", edges=TES_EDGES)
    a.say("接下來看這三個日期", "calendar")
    a.scroll(by=40, ms=1300)   # 手指輕推一下（畫面不停住）
    a.settle()


VP_D = {"open": (1600, 900, 3), "guide": (1600, 900, 4), "events": (1600, 900, 3), "arts": (1600, 900, 4), "tesla": (1600, 900, 2.5), "end": (1600, 900, 2)}
D_SHOTS = {"open": d_open, "guide": d_guide, "events": d_events, "arts": d_arts, "tesla": d_tesla, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "events": m_events, "arts": m_arts, "tesla": m_tesla, "end": m_end}


def run(dev, shots, out, port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    reg = D_SHOTS if dev == "d" else M_SHOTS
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            for sid in shots or list(reg):
                cfg = dict(DEVS[dev])
                if dev == "d" and sid in VP_D:
                    w_, h_, k_ = VP_D[sid]
                    cfg["viewport"] = {"width": w_, "height": h_}
                    cfg["device_scale_factor"] = k_
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                # 網站 00:00～05:00 自動切深色：錄影時鐘固定在台北下午 14:30（凌晨錄就用前一天），一律亮色主題
                _tpe = _dt.timezone(_dt.timedelta(hours=8))
                _now = _dt.datetime.now(tz=_tpe)
                _day = _now.date() if _now.hour >= 5 else _now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(_day.year, _day.month, _day.day, 14, 30, tzinfo=_tpe))
                F.route_fonts(ctx)
                guest_api(ctx)
                ctx.add_init_script(F.FONT_JS)
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                ctx.add_init_script(CLIP_JS)
                if dev == "d":   # 網頁版：文章清單每組只露出前 6 張卡（兩排）、右欄只留前兩節 → 取景框下緣能落在乾淨的空白處（只在錄影的瀏覽器裡，不改 site/）
                    ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = '#artList .artc:nth-child(n+7){display:none!important}#artSide section:nth-of-type(n+3){display:none!important}'; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();")
                ctx.add_init_script(BLUR_JS)       # 法遵：券商列、含公司名的標題、個股連結模糊
                if dev == "d" and sid not in ("guide", "arts"):   # 桌機左側導覽收成圖示列：內容區更寬（引導段要看得到選單文字）
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                pg.evaluate("() => document.fonts.ready")
                pg.wait_for_function("() => window.__vblurReady === true", timeout=15000)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (900, 500) if dev == "d" else (370, 160)
                a.dsf = cfg["device_scale_factor"]
                rec = F.Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    if a.mob:
                        a.cursor(False)
                        pg.mouse.move(*A.PARK)
                    else:
                        a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]]
                    r.update(timer_errs=getattr(rec, 'timer_errs', []), fabs=rec.fabs, edges=rec.edges, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6], flush=True)
                except Exception as exc:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    rec.on = False
                    print(sid, "失敗", exc)
                    print("\n".join(a.log[-12:]))
                    shutil.rmtree(out / f".tmp_{dev}_{sid}", ignore_errors=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8816)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
