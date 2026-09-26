"""本機預覽驗證 v3：起 http server，用真的 ECharts + Lightweight Charts 走過每個分頁與個股頁，
抓 JS 錯誤、偵測文字框重疊、截圖到 docs/。

用法：python scripts/_preview.py [--code 2330]
"""
from __future__ import annotations

import os
# 瀏覽器：Claude 的雲端容器有預裝的 Chromium（/opt/pw-browsers/chromium）；別的環境（例如 Codex、本機）
# 沒有這個路徑，就交給 Playwright 用它自己 `playwright install chromium` 裝的那一顆。
_CHROMIUM = '/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None
import argparse
import json
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
# 埠可以用環境變數蓋掉（TW_UITEST_PORT / TW_PREVIEW_PORT）。
# 2026-09-20 加的：同時派幾個 agent 各自驗自己那一段時，固定埠會互相搶，
# 第二個起來的直接 OSError: Address already in use，看起來像程式壞了。
PORT = int(os.environ.get('TW_PREVIEW_PORT', '8766'))

OVERLAP_JS = r"""
() => {
  // 找出可見的文字葉節點，兩兩比對外框；忽略祖先/後代與 canvas
  const els = Array.from(document.querySelectorAll('main *')).filter(e => {
    if (!(e instanceof HTMLElement)) return false;
    if (['SCRIPT','STYLE','CANVAS','SVG','INPUT','BUTTON'].includes(e.tagName)) return false;
    const hasText = Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!hasText) return false;
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 6 && r.height > 6 && cs.visibility !== 'hidden' && cs.display !== 'none' && r.bottom > 0 && r.top < document.documentElement.scrollHeight;
  });
  /* 在可捲動（或 overflow:hidden 的）容器裡，**使用者看得到的只有交集那一塊**。
     ★ 2026-09-22 改寫（visual-director）：原本只判「整個跑到框外面才不算」，
       那漏掉了**跨在框邊緣上**的那一列 —— 它有一半被裁掉、畫面上根本看不到，
       可是 getBoundingClientRect() 仍然回它完整的高度，於是跟框**下面**那段文字
       量出一個不存在的重疊。
       2026-09-22 產業鏈頁把成分股表關進 `.tw.memcap` 之後立刻踩到：
       報「觀望」跟「目前依漲跌排序…還有 68 檔收著」重疊 —— 截圖上兩者離得很遠。
       改成「一路跟每一個會裁切的祖先取交集」，交集空了就整個不算。
       這只會讓掃描更準，不會放過真的重疊：被裁掉的東西本來就不在畫面上。*/
  const clipRect = (e) => {
    let r = e.getBoundingClientRect();
    r = { top: r.top, left: r.left, bottom: r.bottom, right: r.right, width: r.width, height: r.height };
    for (let p = e.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (!/auto|scroll|hidden/.test(cs.overflowY + cs.overflowX)) continue;
      const pr = p.getBoundingClientRect();
      const top = Math.max(r.top, pr.top), left = Math.max(r.left, pr.left);
      const bottom = Math.min(r.bottom, pr.bottom), right = Math.min(r.right, pr.right);
      if (bottom <= top || right <= left) return null;     // 整個被裁掉，看不到
      r = { top, left, bottom, right, width: right - left, height: bottom - top };
    }
    return r;
  };
  /* ★ 2026-09-24（法律頁加進掃描時踩到）：**折行的行內元素**（段落裡的 <b>、<mark>）
     getBoundingClientRect() 回的是「第一行起點到最後一行終點」的大方框，
     會把同一段裡前後相鄰的另一個 <b> 整個框進去 —— 截圖上兩者是同一行裡一前一後，根本沒疊。
     所以只要有一邊是折成多行的行內元素，就改用 getClientRects() 逐行比，逐行都沒交集才算誤報。
     這只會讓掃描更準：真的疊字一定有某一行的方框彼此相交。*/
  const wrapOnly = (p, q) => {
    const multi = (e) => getComputedStyle(e).display === 'inline' && e.getClientRects().length > 1;
    if (!multi(p) && !multi(q)) return false;
    const P = [...p.getClientRects()], Q = [...q.getClientRects()];
    for (const a of P) for (const b of Q) {
      const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (x > 1 && y > 1) return false;
    }
    return true;
  };
  const rects = els.map(e => ({ e, r: clipRect(e) }))
                   .filter(x => x.r && x.r.width > 6 && x.r.height > 6);
  const bad = [];
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const x = Math.max(0, Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left));
    const y = Math.max(0, Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top));
    const inter = x * y; const small = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
    if (inter > 0.3 * small && inter > 40 && !wrapOnly(a.e, b.e)) bad.push([a.e.textContent.trim().slice(0, 30), b.e.textContent.trim().slice(0, 30)]);
  }
  return bad.slice(0, 12);
}
"""


# ---------------------------------------------------------------------------
# ★ 2026-09-20：圖表「裡面」的字的重疊掃描（多寬度）
#
# 為什麼要另外寫一支：上面那支 OVERLAP_JS 只看得到 HTML 元素，
# 而所有 ECharts 圖表線上版都是 **canvas** 畫的 —— 圖裡的每一個字在 DOM 上都不存在。
# 所以它永遠報「重疊 0 筆」，Andy 一換螢幕就看到壓字（2026-09-20 他的截圖：
# 市場寬度的儀表壓字、族群估值左上角兩個標籤糊成一團、法人連續買超的「玉山金」跑出框）。
# 這不是「測試沒寫好」，是**測試在物理上看不到那些字**。
#
# 做法：用 `index.html?svg=1` 載入（`site/app.js` 的 `chart()` 認這個參數，
# 會改用 SVG renderer），SVG renderer 會產生真的 <text> 節點，位置就量得出來。
# ★ 線上版一律維持 canvas（效能），只有這支驗收腳本會帶 ?svg=1。
# ⚠ SVG 與 canvas 的字寬量法略有差異，版面不保證 100% 相同 ——
#    量到的重疊要人工開截圖確認過才算數，不要照單全收。
#
# 為什麼只掃總覽與資金流向兩頁：五個寬度 × 每頁重新載入約 4 秒，全站八頁會多花 2 分半。
# Andy 回報的三張圖都在總覽，資金流向是圖最多的一頁，這兩頁的邊際效益最高；
# 其餘頁面維持原本的單一寬度（1500px）掃描。
WIDTHS = [1280, 1366, 1440, 1536, 1920]

CHART_TEXT_JS = r"""
() => {
  const out = { overlaps: [], outside: [], cards: [], nodes: 0 };
  // ECharts 會在容器上留 _echarts_instance_，拿它當「這是一張圖」的判準
  for (const host of document.querySelectorAll('main .view.on [_echarts_instance_]')) {
    const hr = host.getBoundingClientRect();
    if (hr.width < 20 || hr.height < 20) continue;
    const id = host.id || '(no-id)';
    const bs = [...host.querySelectorAll('svg text')]
      .filter(t => (t.textContent || '').trim().length)
      .map(t => ({ t: (t.textContent || '').trim().slice(0, 18), r: t.getBoundingClientRect() }))
      .filter(b => b.r.width > 1 && b.r.height > 1);
    out.nodes += bs.length;
    for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
      const a = bs[i].r, b = bs[j].r;
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox <= 1 || oy <= 1) continue;
      const inter = ox * oy, small = Math.min(a.width * a.height, b.width * b.height);
      // 蓋掉小的那一塊 1/4 以上才算重疊；純粹擦邊（描邊、字距）不算
      if (inter > 0.25 * small) out.overlaps.push([id, bs[i].t, bs[j].t, Math.round(ox), Math.round(oy)]);
    }
    for (const b of bs) {   // 字跑出自己那張圖的容器
      const r = b.r, pad = 1.5;
      const over = Math.max(hr.left - r.left, r.right - hr.right, hr.top - r.top, r.bottom - hr.bottom);
      if (over > pad) out.outside.push([id, b.t, Math.round(over)]);
    }
  }
  // 總覽「熱門題材 / 今日候選」那一列：兩張卡要等高，而且內容超出要能捲
  const pair = [...document.querySelectorAll('.grid.eqpair > .card')];
  out.cards = pair.map(e => Math.round(e.getBoundingClientRect().height));
  const pane = document.querySelector('.eqpair .pane');
  out.pane = pane ? { client: pane.clientHeight, scroll: pane.scrollHeight } : null;
  out.docW = document.documentElement.scrollWidth;
  out.winW = window.innerWidth;
  return out;
}
"""


def scan_widths(pg, base, problems, state, pages=(("overview", "總覽"), ("flow", "資金流向"))):
    """在多個常見螢幕寬度下，量圖表內文字的重疊／出框、橫向捲軸、成對卡片等高。"""
    res = {}
    for hash_, label in pages:
        for w in WIDTHS:
            pg.set_viewport_size({"width": w, "height": 1000})
            # 重新載入而不是只 resize：resize 只會叫 ECharts 重算尺寸，
            # 不會重跑我們自己的 render（例如依容器寬度決定的版面），量到的就不是真的。
            pg.goto(f"{base}?svg=1#{hash_}", wait_until="networkidle")
            pg.wait_for_timeout(2600)
            r = pg.evaluate(CHART_TEXT_JS)
            key = f"{label}@{w}"
            res[key] = {"overlaps": len(r["overlaps"]), "outside": len(r["outside"]),
                        "nodes": r["nodes"], "cards": r["cards"], "pane": r["pane"]}
            if r["overlaps"]:
                problems.append(f"[{w}px] {label} 圖內文字重疊 {len(r['overlaps'])} 組：{r['overlaps'][:4]}")
            if r["outside"]:
                problems.append(f"[{w}px] {label} 圖內文字跑出容器 {len(r['outside'])} 處：{r['outside'][:4]}")
            if r["docW"] > r["winW"] + 1:
                problems.append(f"[{w}px] {label} 出現橫向捲軸（內容 {r['docW']}px）")
            # 只有這一列真的顯示在畫面上時才比高度（切到別頁時整個 section 是 display:none，量到 0）
            if len(r["cards"]) == 2 and min(r["cards"]) > 0 and abs(r["cards"][0] - r["cards"][1]) > 2:
                problems.append(f"[{w}px] {label} 熱門題材／今日候選兩張卡不等高：{r['cards']}")
    state["width_scan"] = res
    return res


def serve():
    """起一個只給本機用的靜態伺服器。

    ★ 埠要自己找，不可以寫死（2026-09-21 踩到）。
      原本寫死 8766，於是「同時在跑 `_uitest.py`」就會讓這支直接
      `OSError: [Errno 98] Address already in use` 整個死掉 ——
      而那個錯誤長得像「預覽關卡壞了」，實際上只是埠被佔走。
      `_uitest.py` 早就改成自動找埠了，這支漏掉，這次補上。
      回傳的 srv 身上帶著真正用到的埠（`srv.server_address[1]`），呼叫端要讀那個，
      不可以再讀模組層的 PORT。"""
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
    last = None
    for off in range(0, 40):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", PORT + off), handler)
            break
        except OSError as e:
            last = e
    else:
        raise RuntimeError(f"從 {PORT} 起連續 40 個埠都被佔走了：{last}")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv



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
    ap = argparse.ArgumentParser(); ap.add_argument("--code", default=None); args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    _preset_consent()
    srv = serve(); time.sleep(0.4)
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    problems: list[str] = []; state = {}

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=_CHROMIUM)
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        pg.on("console", lambda m: problems.append(f"console.error: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "fonts.googleapis" not in m.text
              # 本機／CI 連不到 Cloudflare Worker，即時報價抓不到是預期的，不是 bug
              and "ERR_TUNNEL_CONNECTION_FAILED" not in m.text and "workers.dev" not in m.text
              and "ERR_NAME_NOT_RESOLVED" not in m.text and "ERR_INTERNET_DISCONNECTED" not in m.text else None)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        base = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

        def visit(hash_, name, wait=1500):
            pg.goto(f"{base}#{hash_}", wait_until="networkidle"); pg.wait_for_timeout(wait)
            info = pg.evaluate("""() => ({ canvases: document.querySelectorAll('main canvas').length, empties: Array.from(document.querySelectorAll('main .view.on .empty')).map(e => e.textContent.trim().slice(0, 40)), text: document.querySelector('main .view.on').innerText.length })""")
            info["overlaps"] = pg.evaluate(OVERLAP_JS)
            state[name] = info
            pg.screenshot(path=str(out / f"v3_{name}.png"), full_page=True)
            return info

        visit("overview", "overview")
        # ★ 2026-09-24 總覽改版：「今日候選」表整張拿掉（Andy）→ 以前這裡切四個面向、點列展開理由的檢查一併移除
        #   （名單留在市場明細「今日候選」分頁，由 _uitest 的市場明細／排序段落負責）。改記這一版的關鍵版面數字。
        state["overview"]["hero"] = pg.evaluate("document.getElementById('hero').innerText.slice(0,80)")
        state["overview"]["layout"] = pg.evaluate("""() => ({
            heroH: Math.round(document.getElementById('hero').getBoundingClientRect().height),
            kpis: document.querySelectorAll('#hero .kpi').length,
            candGone: !document.getElementById('ovCandCard'),
            m3Cards: document.querySelectorAll('#m3Frame .m3-card').length,
            ud: !!document.querySelector('#breadth canvas'), theme: !!document.querySelector('#ovTheme canvas') })""")
        lay = state["overview"]["layout"]
        if lay["heroH"] > 64 or lay["kpis"] != 4:
            problems.append(f"總覽 KPI 橫條應該 4 格、高度 ≤ 64px：{lay}")
        if not lay["candGone"] or lay["m3Cards"] != 3 or not lay["ud"] or not lay["theme"]:
            problems.append(f"總覽改版後的版面不完整：{lay}")
        visit("flow", "flow")
        visit("industry", "industry_map")
        visit("industry/ai_server", "industry_chain")
        # ★ 2026-09-23（W3-2）：成分股表移除，這裡記的「這一頁有多少內容」改成量關聯圖的族群節點。
        # ★ 2026-09-23（技術債清理）：`#cgGraph .cgnode` 是**力導向星際圖**的節點，
        #   而那張圖已經在 `49d98a2`（批次 0923-I，關聯圖退版回分層圖）從產業鏈頁移除了 ——
        #   這一行從那天起永遠記成 0。它沒有斷言、不會變紅，所以壞了一週也沒人看得出來，
        #   但「永遠是 0 的狀態紀錄」比沒有紀錄更糟：它會讓下次看報告的人以為這一頁是空的。
        #   改量分層圖真正畫出來的族群節點 `#chainMap .co`（跟下一行的 diagram 同一個來源）。
        state["industry_chain"]["members"] = pg.evaluate("document.querySelectorAll('#chainMap .co').length")
        state["industry_chain"]["diagram"] = pg.evaluate("!!document.querySelector('#prodDiagram svg') && document.querySelectorAll('#chainMap .co').length")
        visit("industry/group/ind_ETF", "industry_etf")
        # ★ 2026-09-23（W3-2）：族群頁改用個股漲幅長條圖，量它畫了幾條
        state["industry_etf"]["members"] = pg.evaluate("() => { const g = window.Industry && window.Industry._gp ? window.Industry._gp() : null; return g ? g.rows : 0; }")
        visit("themes", "themes")
        # 每個題材都要有產品圖，而且圖上每個零件都要點得到個股（Andy 2026-09-12 的要求）
        # ★ 2026-09-23 修：`window.ThemeDiagrams.fit` 是版面用的工具函式（themes3d.js:1554 掛上去的），
        #   不是一個題材。直接掃 Object.keys 會把它當成題材去開 `#themes/fit`，
        #   然後回報「題材 fit 沒有產品圖」—— 那是掃描器自己的誤判，不是產品缺圖。
        #   判準用「值是不是可呼叫的題材建構式」不夠（fit 也是 function），所以照名字排除工具。
        tids = pg.evaluate(
            "(window.ThemeDiagrams ? Object.keys(window.ThemeDiagrams).filter(k => k !== 'fit') : [])")
        tstat = {}
        for tid in tids:
            pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(900)
            tstat[tid] = pg.evaluate("""() => {
              const r = document.querySelector('#themeDiagram svg'); if (!r) return { svg: false };
              const ns = Array.from(r.querySelectorAll('[data-part]'));
              const ids = [...new Set(ns.map(n => n.dataset.part).filter(Boolean))];
              const noCode = ids.filter(id => !ns.some(n => n.dataset.part === id && n.dataset.codes));
              const rows = ns.filter(n => n.classList.contains('lrow')).length;
              return { svg: true, parts: ids.length, rows, noCode, vb: r.getAttribute('viewBox') };
            }""")
            if tstat[tid].get("noCode"):
                problems.append(f"題材 {tid} 有零件點不到個股：{tstat[tid]['noCode']}")
            if not tstat[tid].get("svg"):
                problems.append(f"題材 {tid} 沒有產品圖")
            ov2 = pg.evaluate(OVERLAP_JS)
            if ov2:
                problems.append(f"題材 {tid} 文字重疊：{ov2[:3]}")
        # 點第一個零件，確認會列出個股
        if tids:
            pg.goto(f"{base}#themes/{tids[0]}", wait_until="networkidle"); pg.wait_for_timeout(900)
            pg.evaluate("document.querySelector('#themeDiagram [data-part][data-codes]').dispatchEvent(new MouseEvent('click', {bubbles:true}))")
            pg.wait_for_timeout(300)
            tstat["_click"] = pg.evaluate("({ links: document.querySelectorAll('#themeParts a.lk').length, sel: document.querySelectorAll('#themeDiagram .p3.sel').length })")
            if not tstat["_click"]["links"]:
                problems.append("點題材產品圖的零件沒有列出個股")
            pg.screenshot(path=str(out / "v3_theme_diagram.png"), full_page=True)
        state["theme_diagrams"] = tstat
        visit("season", "season")
        # ★ 2026-09-24 設計系統 v2 第 6 批：三個法律頁（site/legal.js）也走一次文字重疊掃描。
        #   這三頁是純文字長頁，最常出事的是表格與【】空格標示在窄欄裡疊字。
        for lg in ("terms", "privacy", "disclaimer"):
            info = visit(lg, "legal_" + lg, wait=900)
            if info["text"] < 300:
                problems.append(f"法律頁 #{lg} 幾乎沒有內容（{info['text']} 字）")
            if info["overlaps"]:
                problems.append(f"法律頁 #{lg} 文字重疊：{info['overlaps'][:3]}")

        code = args.code or "2330"          # 2026-09-24：總覽的候選表拿掉了，不再從它挑第一檔
        pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2200)
        st = pg.evaluate("""() => ({ title: (document.querySelector('#stockPage h2')||{}).innerText, lwc: !!document.querySelector('#lwc canvas'), lwcCanvases: document.querySelectorAll('#lwc canvas').length,
            indBtn: !!document.getElementById('indBtn'), /* 2026-09-26 指標晶片改成下拉 */ legend: (document.getElementById('legendOv')||{}).innerText, mtf: (document.getElementById('mtfCard')||{}).innerText.slice(0,120), chainCos: document.querySelectorAll('#chainMap .co').length, sel: document.querySelectorAll('#chainMap .co.sel').length })""")
        st["overlaps"] = pg.evaluate(OVERLAP_JS); state["stock"] = st
        pg.screenshot(path=str(out / "v3_stock.png"), full_page=True)
        # 切分頁與週期
        for tab in ("revenue", "profit", "dividend", "chips", "basics", "news"):
            pg.evaluate(f"document.querySelector('#stockTabs button[data-t=\"{tab}\"]').click()"); pg.wait_for_timeout(500)
            state["tab_" + tab] = pg.evaluate("({ canvases: document.querySelectorAll('#stockTab canvas').length, text: document.getElementById('stockTab').innerText.length, empties: Array.from(document.querySelectorAll('#stockTab .empty')).map(e => e.textContent.trim().slice(0,30)) })")
            pg.screenshot(path=str(out / f"v3_tab_{tab}.png"), full_page=False)
        for tf in ("1w", "1M", "60m"):
            pg.evaluate(f"document.querySelector('#tfSeg button[data-tf=\"{tf}\"]').click()"); pg.wait_for_timeout(500)
            state["tf_" + tf] = pg.evaluate("({ canvases: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#chartHost .empty'), legend: (document.getElementById('legendOv')||{}).innerText })")
        pg.evaluate("document.querySelector('#tfSeg button[data-tf=\"1d\"]').click()"); pg.wait_for_timeout(600)
        # 切到沒資料的週期再切回來，圖必須回得來（以前會整張空白到重新整理）
        state["tf_back_to_1d"] = pg.evaluate("({ canvases: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#lwc .empty'), dbg: window.Industry._dbg() })")
        if not state["tf_back_to_1d"]["canvases"] or state["tf_back_to_1d"]["empty"]:
            problems.append(f"切到沒資料的週期再切回日線，K 線沒回來：{state['tf_back_to_1d']}")
        pg.evaluate("document.getElementById('mtfBtn').click()"); pg.wait_for_timeout(1200)
        state["mtf_grid"] = pg.evaluate("({ cells: document.querySelectorAll('.mtf-cell').length, canvases: document.querySelectorAll('#mtfGrid canvas').length })")
        pg.screenshot(path=str(out / "v3_mtf.png"), full_page=False)
        # 指標參數
        pg.evaluate("document.getElementById('mtfBtn').click()"); pg.wait_for_timeout(600)
        # ★ 2026-09-26 改前：點工具列的 RSI 晶片、按「⚙ 設定」開圖表設定面板
        #   → 改後：打開「指標 ▾」下拉，點 RSI 那一列的開關；整體／均線兩列按 ▸ 展開（內容跟以前的面板同一套）
        pg.evaluate("document.getElementById('indBtn').click()"); pg.wait_for_timeout(350)
        pg.evaluate("document.querySelector('#cfgPop .indrow[data-k=rsi] input.ion').click()"); pg.wait_for_timeout(400)
        state["rsi_on"] = pg.evaluate("({ chipOn: document.querySelector('#cfgPop .indrow[data-k=rsi] input.ion').checked, legend: (document.getElementById('lwc')||{}).innerText.includes('RSI') })")
        if not state["rsi_on"]["chipOn"] or not state["rsi_on"]["legend"]:
            problems.append(f"指標下拉裡打開 RSI 沒生效：{state['rsi_on']}")

        # ---- K 線的基本設定與繪圖工具（Andy #43）：真的操作一遍，不是只看有沒有 render
        pg.evaluate("['base', 'ma'].forEach(k => { const r = document.querySelector('#cfgPop .indrow[data-k=' + k + ']');"
                    " if (r && r.querySelector('.ibody').hidden) r.querySelector('.iexp').click(); })"); pg.wait_for_timeout(350)
        state["kcfg_open"] = pg.evaluate("""() => ({ rows: document.querySelectorAll('#maRows .marow').length,
            lw: !!document.getElementById('lw'), color: !!document.querySelector('#maRows input[type=color]') })""")
        if state["kcfg_open"]["rows"] < 2 or not state["kcfg_open"]["lw"] or not state["kcfg_open"]["color"]:
            problems.append(f"K 線設定面板不完整：{state['kcfg_open']}")
        # 調線寬 → 均線真的變粗；改顏色 → 真的換色；新增一條均線 → 真的多一條
        pg.evaluate("const s=document.getElementById('lw'); s.value=3; s.dispatchEvent(new Event('input',{bubbles:true}))")
        pg.wait_for_timeout(400)
        pg.evaluate("document.getElementById('maAdd').click()"); pg.wait_for_timeout(500)
        state["kcfg_after"] = pg.evaluate("""() => { const c = JSON.parse(localStorage.getItem('tw.kcfg')||'{}');
            return { lineWidth: c.lineWidth, ma: c.ma, maWidth: c.maWidth, maColor: (c.maColor||[]).length,
                     legend: (document.getElementById('legendOv')||{}).innerText.split('\\n').pop() }; }""")
        if state["kcfg_after"].get("lineWidth") != 3:
            problems.append(f"線寬調了沒生效：{state['kcfg_after']}")
        if len(state["kcfg_after"].get("ma") or []) < 5:
            problems.append(f"新增均線沒生效：{state['kcfg_after']}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)      # 改前：按「完成」→ 改後：Esc 關下拉

        # 自訂時間週期：加一個 3 日
        pg.evaluate("document.getElementById('tfAdd').click()"); pg.wait_for_timeout(300)
        pg.evaluate("document.getElementById('tfOk').click()"); pg.wait_for_timeout(900)
        state["tf_custom"] = pg.evaluate("""() => ({ buttons: [...document.querySelectorAll('#tfSeg button')].map(b=>b.dataset.tf),
            on: (document.querySelector('#tfSeg button.on')||{}).dataset && document.querySelector('#tfSeg button.on').dataset.tf,
            canvases: document.querySelectorAll('#lwc canvas').length })""")
        if '3D' not in (state["tf_custom"]["buttons"] or []) or not state["tf_custom"]["canvases"]:
            problems.append(f"自訂時間週期失敗：{state['tf_custom']}")
        pg.evaluate("document.querySelector('#tfSeg button[data-tf=\"1d\"]').click()"); pg.wait_for_timeout(700)

        # 繪圖工具：畫一條趨勢線、一條水平線，確認存進 localStorage 且能清空
        state["draw_tools"] = pg.evaluate("document.querySelectorAll('#drawBar .dtool[data-t]').length")
        if state["draw_tools"] < 6:
            problems.append(f"繪圖工具列少了工具：{state['draw_tools']}")
        # 圖高 640，要先捲到畫面正中間，不然拖曳終點會落在視窗外、pointerup 收不到
        pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
        pg.evaluate("document.querySelector('#drawBar .dtool[data-t=trend]').click()"); pg.wait_for_timeout(200)
        box = pg.evaluate("() => { const r = document.getElementById('lwc').getBoundingClientRect(); return {x:r.x, y:r.y, w:r.width, h:r.height, vh:innerHeight}; }")
        if box["y"] < 0 or box["y"] + box["h"] * 0.6 > box["vh"]:
            problems.append(f"K 線圖沒完整進到畫面，繪圖測試不準：{box}")
        pg.mouse.move(box["x"] + box["w"] * 0.35, box["y"] + box["h"] * 0.35)
        pg.mouse.down(); pg.mouse.move(box["x"] + box["w"] * 0.62, box["y"] + box["h"] * 0.55, steps=6); pg.mouse.up()
        pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('#drawBar .dtool[data-t=hline]').click()"); pg.wait_for_timeout(150)
        pg.mouse.click(box["x"] + box["w"] * 0.5, box["y"] + box["h"] * 0.45)
        pg.wait_for_timeout(300)
        state["drawings"] = pg.evaluate("""() => { const ks = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
            const all = ks.flatMap(k => JSON.parse(localStorage.getItem(k)||'[]').map(s=>s.kind));
            return { keys: ks, shapes: all, tf: (document.querySelector('#tfSeg button.on')||{}).dataset.tf }; }""")
        if len(state["drawings"]["shapes"]) < 2:
            problems.append(f"繪圖沒存下來：{state['drawings']}")
        pg.screenshot(path=str(out / "v3_kchart_draw.png"), full_page=False)
        pg.evaluate("document.querySelector('#drawBar .dtool[data-a=clear]').click()"); pg.wait_for_timeout(250)
        left = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
            return k.reduce((n,x)=>n+JSON.parse(localStorage.getItem(x)||'[]').length, 0); }""")
        if left != 0:
            problems.append(f"清空繪圖沒生效，還剩 {left} 筆")
        pg.evaluate("document.querySelector('#drawBar .dtool[data-t=cursor]').click()")
        # 重設縮放的小圖示
        state["fit_icon"] = pg.evaluate("!!document.querySelector('#fitBtn svg')")
        if not state["fit_icon"]:
            problems.append("重設縮放沒有換成小方框圖示")
        pg.evaluate("document.getElementById('fitBtn').click()"); pg.wait_for_timeout(300)

        # ★ 多寬度掃描（見檔案上方 CHART_TEXT_JS 的說明）。
        #   放在最後跑，因為它會把視窗寬度改來改去、也會重新載入頁面，
        #   前面那些「照順序操作」的驗收不能被它打斷。
        pg.set_viewport_size({"width": 1500, "height": 1000})
        scan_widths(pg, base, problems, state)
        pg.set_viewport_size({"width": 1500, "height": 1000})

        # 手機
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.on("pageerror", lambda e: problems.append(f"mobile pageerror: {e}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(f"{base}#overview", wait_until="networkidle"); m.wait_for_timeout(1200)
        state["mobile"] = m.evaluate("({ sideways: document.documentElement.scrollWidth > 391, hero: document.querySelectorAll('#hero .kpi').length })")
        m.screenshot(path=str(out / "v3_mobile.png"), full_page=False)
        m.goto(f"{base}#stock/{code}", wait_until="networkidle"); m.wait_for_timeout(1800)
        state["mobile_stock"] = m.evaluate("({ sideways: document.documentElement.scrollWidth > 391, lwc: !!document.querySelector('#lwc canvas') })")
        m.screenshot(path=str(out / "v3_mobile_stock.png"), full_page=False)
        b.close()
    srv.shutdown()

    print(json.dumps(state, ensure_ascii=False, indent=1))
    ov = {k: v["overlaps"] for k, v in state.items() if isinstance(v, dict) and v.get("overlaps")}
    if ov:
        print("\n=== 文字重疊 ===")
        for k, v in ov.items():
            print(" ", k, v)
    if problems:
        print("\n=== 問題 ===")
        for x in problems:
            print(" -", x)
        return 1
    print("\n所有分頁與個股頁正常，截圖在 docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
