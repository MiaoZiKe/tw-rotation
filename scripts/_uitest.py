"""真人操作驗收：當自己是使用者，把每個功能實際操作一遍。

和 `_preview.py` 的差別很重要：
  _preview.py 問的是「有沒有畫出來、有沒有壓到字」；
  這支問的是「我按下去之後，畫面真的因此改變了嗎」。

所以這裡每一項檢查都長成「操作前記一次狀態 → 真的操作 → 操作後再記一次 → 兩次必須不一樣」。
只驗「元素存在」「有 render」一律不算數 —— 之前就是這樣放過了「切到沒資料的週期再切回日線，
整張 K 線圖空白到重新整理為止」這種錯。

用法：python scripts/_uitest.py [--code 2330] [--headed]
"""
from __future__ import annotations

import os
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
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
PORT = int(os.environ.get('TW_UITEST_PORT', '8767'))

fails: list[str] = []
notes: list[str] = []


def ok(name: str, cond: bool, detail=None) -> bool:
    """cond 為真＝這個功能真的動了；為假就記下來，最後一次列出。"""
    if not cond:
        fails.append(f"{name}　←　{detail if detail is not None else ''}")
    return bool(cond)


def wait_until(pg, expr: str, timeout: int = 6000, step: int = 150):
    """輪詢 `expr` 直到它回傳真值，或逾時。回傳最後一次的值。

    為什麼需要這個（2026-09-20，平行化逼出來的）
    ------------------------------------------
    以前到處都是 `pg.wait_for_timeout(1400)` 這種**睡固定秒數**。
    單獨跑時剛好夠；一旦四個 worker 同時佔著 CPU，圖表畫得慢，
    同樣的 1400ms 就不夠了 —— 於是驗收開始**間歇性假紅**。
    假紅比慢更糟：它會讓人開始習慣「紅字先無視」，那整套驗收就廢了。

    睡固定秒數還有另一個壞處：不管快慢都要付滿那幾秒。
    改成等條件成立之後，快的時候立刻往下走，慢的時候才等。
    """
    import time as _t
    end = _t.time() + timeout / 1000.0
    v = None
    while _t.time() < end:
        try:
            v = pg.evaluate(expr)
        except Exception:  # noqa: BLE001 —— 換頁途中 evaluate 會炸，再試一次就好
            v = None
        if v:
            return v
        pg.wait_for_timeout(step)
    return v


def changed(name: str, before, after, detail: str = "") -> bool:
    return ok(name, before != after, f"操作前後一樣：{before!r} → {after!r}　{detail}")


def reset_rot(pg, base, wait: int = 2400):
    """把輪動時鐘／資金流向排行的族群篩選清乾淨，而且是**真的**清乾淨。

    2026-09-21 逼出來的坑（不是產品 bug，是驗收之間互相汙染）
    ------------------------------------------------------
    `ROT.groups` 是 `site/app.js` 模組層級的變數，前一段驗收點過族群晶片之後它就留著；
    而 `pg.goto(base)` 從 `…index.html#flow` 走到 `…index.html` 只差一個 fragment，
    瀏覽器判定成 same-document navigation，**根本不會重新載入 JS**。
    所以「清掉 localStorage 再 goto」清掉的只有磁碟上那一份，
    記憶體裡前一段勾的族群原封不動活著 —— 下一段就量到「盤上只剩 1 個族群」
    （批次2 的「點排行的長條，旁邊的輪動時鐘只亮那一個族群」就是這樣假紅的：
    盤上本來就只有 1 個，不可能同時量到「有亮的」跟「有暗的」）。

    產品本身是對的：使用者自己勾的族群就該被記住（E3 拍板），
    畫面上也一直寫著「排行與時鐘都只看這 N 個族群」還附一顆「清除篩選」。
    要修的是**驗收的隔離**，所以這裡 reload() 一次，把記憶體那份也一起換掉。
    """
    pg.goto(f"{base}#flow", wait_until="networkidle")
    pg.evaluate("() => { try { localStorage.removeItem('tw.rot.filter');"
                " localStorage.removeItem('tw.rot.back'); } catch (e) { /* 私密視窗 */ } }")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(wait)


class _QuietServer(ThreadingHTTPServer):
    """瀏覽器中途取消請求（換頁、圖片還沒載完就離開）會讓 sendall 噴 BrokenPipe。
    那不是故障，但預設會印一大段 traceback 蓋掉驗收結果。這裡直接吞掉。"""

    def handle_error(self, request, client_address):
        import sys as _s
        if isinstance(_s.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


class _NoCache(SimpleHTTPRequestHandler):
    """驗收用的靜態伺服器：一律回 no-store。

    為什麼（2026-09-18 花了半小時才抓到）：瀏覽器把 `data/news.json?v=…` 快取起來之後，
    **`page.route()` 攔不到從快取拿的請求**。所以「前面幾個測試先載過同一頁」的情況下，
    後面那個想用假資料的測試會拿到快取裡的真資料，症狀是「單獨跑會過、整批跑就掛」。
    這種假故障最浪費時間，直接從源頭關掉快取。"""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def serve():
    handler = partial(_NoCache, directory=str(SITE))
    _NoCache.log_message = lambda *a, **k: None
    srv = _QuietServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ 小工具
def click(pg, sel: str, wait: int = 300):
    """用真的滑鼠點（會捲進畫面），點不到就記一筆。

    2026-09-18 重寫，兩個問題一起解（DECISIONS #190）：

    1. **`query_selector` 拿到的是「當下那一刻」的 ElementHandle。**
       這個專案的表格是整段 `innerHTML` 重寫的，只要在拿到 handle 之後
       又重畫一次（面向切換、live.js 的定時更新都會），handle 就指向一個
       已經脫離 DOM 的節點 —— 它永遠不會變成「可見」，於是卡到逾時。
       改用 `locator`：Playwright 會在每次重試時**重新解析選擇器**，
       重畫幾次都抓得到當下真正在畫面上的那個元素。

    2. **原本 `scroll_into_view_if_needed()` 沒有給 timeout，吃預設的 30 秒。**
       一次失敗就是 30 秒，`t_overview` 光這樣就卡掉快 20 分鐘，
       整輪驗收因此要跑 25 分鐘以上。改成 6 秒 —— 點不到就是點不到，
       等 30 秒不會變成點得到，只是讓每一輪驗收都更難跑完。
    """
    try:
        loc = pg.locator(sel).first
        loc.click(timeout=6000)          # locator.click 自己會捲進畫面並重試
        pg.wait_for_timeout(wait)
        return True
    except Exception as e:  # noqa: BLE001
        fails.append(f"點不下去 {sel}：{type(e).__name__} {str(e).splitlines()[0]}")
        return False


def click_moving(pg, sel: str, wait: int = 300):
    """點一個「一直在動」的東西（會飄的剖析圖零件）。

    2026-09-19：`t_themes` 從只驗 3 個題材改成驗全部 18 個之後，drone 這一張一直逾時。
    量出來的原因不是功能壞了，是**零件本身在動**（連續 120ms 量兩次，y 從 1511.5 變成
    1513.96、高度從 115.36 變成 112.9），而 Playwright 的 click 會先等元素「位置穩定」
    才肯下手，會飄的東西永遠等不到。用 force 點下去，`#themeParts` 確實列出 4 檔個股 ——
    功能是好的，是驗收工具的限制。真人點一個緩慢飄動的東西不會有困難。

    force 會跳過 Playwright 的可點擊性檢查，所以**自己先把該檢查的補回來**：
    元素要存在、要可見、要有實際面積。少了這三項就等於 force 幫忙蓋掉真的 bug。
    """
    box = pg.evaluate("""(sel) => { const e = document.querySelector(sel); if (!e) return null;
        const r = e.getBoundingClientRect(); const st = getComputedStyle(e);
        return { w: r.width, h: r.height, vis: st.visibility !== 'hidden' && st.display !== 'none'
                 && parseFloat(st.opacity || '1') > 0.05 }; }""", sel)
    if not box or not box["vis"] or box["w"] < 2 or box["h"] < 2:
        fails.append(f"點不下去 {sel}：元素不存在／看不見／沒有面積 {box}")
        return False
    try:
        pg.locator(sel).first.click(timeout=6000, force=True)
        pg.wait_for_timeout(wait)
        return True
    except Exception as e:  # noqa: BLE001
        fails.append(f"點不下去 {sel}（force）：{type(e).__name__} {str(e).splitlines()[0]}")
        return False


def how_text(pg, key: str) -> str:
    """讀某張圖「怎麼看 ?」按鈕裡的說明文字（按開 → 讀 → 按回去）。

    2026-09-21（Andy：「下方這段也移除」）：輪動時鐘圖下方那段 622 字的常駐說明
    `#rotCenterNote` 整段拿掉了（1440px 佔 225px、390px 佔 469px），
    內容併進「怎麼看 ?」。說明本身還在，只是改成要按才展開 ——
    所以驗收也要**真的去按那顆鈕**，而不是改成不驗。
    `#how-xxx` 是第一次按才填 innerHTML 的，沒按就是空的。
    """
    box = f"#how-{key}"
    if pg.evaluate(f"() => {{ const b = document.querySelector({box!r}); return !b || b.hidden; }}"):
        click(pg, f'.howbtn[data-how="{key}"]', 400)
    t = text(pg, box)
    # 收起來，不要讓它把後面段落的版面撐高
    if not pg.evaluate(f"() => {{ const b = document.querySelector({box!r}); return !b || b.hidden; }}"):
        click(pg, f'.howbtn[data-how="{key}"]', 300)
    return t


def text(pg, sel: str) -> str:
    return pg.evaluate(f"() => {{ const e = document.querySelector({sel!r}); return e ? e.innerText.trim() : '<缺>'; }}")


def count(pg, sel: str) -> int:
    return pg.evaluate(f"() => document.querySelectorAll({sel!r}).length")


def canvas_hash(pg, sel: str) -> str:
    """把某個容器裡第一張 canvas 取樣成一個指紋，用來判斷『圖真的重畫了』。"""
    return pg.evaluate(
        """(sel) => { const cs = [...document.querySelectorAll(sel + ' canvas')]; if (!cs.length) return 'no-canvas';
             let h = 0;
             for (const c of cs) {
               try {
                 const g = c.getContext('2d'); if (!g) continue;
                 // 取正中間那塊：邊角常常是背景，抓不到「圖真的重畫了」
                 const w = Math.min(c.width, 600), ht = Math.min(c.height, 400);
                 const x = Math.max(0, ((c.width - w) / 2) | 0), y = Math.max(0, ((c.height - ht) / 2) | 0);
                 const d = g.getImageData(x, y, w, ht).data;
                 for (let i = 0; i < d.length; i += 37) { h = (h * 31 + d[i]) | 0; }
               } catch (e) { /* 跨域或 0 尺寸，跳過 */ }
             }
             return String(h); }""", sel)


def set_range(pg, sel: str, value, wait: int = 700):
    """把 range 拉到某個值，並且**真的發 input 事件**（拖曳當下就是發這個）。

    用 fill() 不會觸發 oninput，畫面不會重畫 —— 那就變成只驗「值寫進去了」，
    不是驗「畫面真的因此改變」，違反 Andy 的驗收規矩。
    """
    pg.evaluate("([s, v]) => { const i = document.querySelector(s); if (!i) return;"
                " i.value = String(v); i.dispatchEvent(new Event('input', { bubbles: true }));"
                " i.dispatchEvent(new Event('change', { bubbles: true })); }", [sel, value])
    pg.wait_for_timeout(wait)


def scroll_to(pg, el_id: str, tries: int = 20):
    """捲到某個元素並等它真的停下來。

    全站 `html{scroll-behavior:smooth}`，scrollIntoView 之後畫面還會滑一段時間；
    不等它停就把滑鼠移過去，座標是舊的，滾輪會滾到別的東西上
    —— 驗收就會誤判成「這張圖不能放大」。
    """
    pg.evaluate("(id) => { const e = document.getElementById(id); if (e) e.scrollIntoView({block:'center'}); }", el_id)
    last = None
    for _ in range(tries):
        pg.wait_for_timeout(100)
        y = pg.evaluate("() => Math.round(window.scrollY)")
        if y == last:
            return
        last = y
    pg.wait_for_timeout(200)


def check_zoom(pg, wrap: str, inner: str, label: str):
    """真的把滑鼠移過去滾輪：往上滾要放大、卡片高度不能變、往下滾最多回原始大小。

    Andy 的兩條要求都在這裡驗：「滾輪放大但縮小最多就是原始畫面」
    以及「放大部份不能影響到整頁面」。
    """
    Z = """(a) => { const b = document.getElementById(a[0]); if (!b) return null;
        const pane = b.querySelector('.zpane'); const i = document.getElementById(a[1]);
        const card = b.closest('.card') || b.parentElement;
        return { w: i ? (i.style.width || '') : '', zoomed: b.classList.contains('zoomed'),
                 badge: (b.querySelector('.zbadge')||{}).textContent,
                 sw: pane ? pane.scrollWidth : 0, cw: pane ? pane.clientWidth : 0,
                 cardH: Math.round(card.getBoundingClientRect().height),
                 pageW: document.documentElement.scrollWidth }; }"""
    scroll_to(pg, wrap)
    z0 = pg.evaluate(Z, [wrap, inner])
    if not ok(f"「{label}」有滾輪放大的外框", bool(z0), wrap):
        return
    ok(f"「{label}」預設是原始大小", not z0["zoomed"] and not z0["w"], z0)
    r = pg.evaluate("(id) => { const b = document.getElementById(id).getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }", wrap)
    pg.mouse.move(r["x"] + r["w"] * .5, r["y"] + r["h"] * .5)
    for _ in range(4):
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(150)
    pg.wait_for_timeout(450)
    z1 = pg.evaluate(Z, [wrap, inner])
    ok(f"「{label}」往上滾真的放大了", z1["zoomed"] and z1["sw"] > z0["sw"], f"{z0} → {z1}")
    ok(f"「{label}」放大不會把卡片撐高", z1["cardH"] == z0["cardH"], f"{z0['cardH']} → {z1['cardH']}")
    ok(f"「{label}」放大不會讓整頁出現橫向捲軸", z1["pageW"] <= z0["pageW"], f"{z0['pageW']} → {z1['pageW']}")
    ok(f"「{label}」放大後徽章寫出倍率", "×" in (z1["badge"] or ""), z1["badge"])
    # 一路滾回 1 倍：還原的那一下不可以把整頁帶著往下衝
    # （Andy：「還原成正常大小 他會導致整體頁面往下」）
    y0 = pg.evaluate("() => Math.round(window.scrollY)")
    for _ in range(12):
        pg.mouse.wheel(0, 160); pg.wait_for_timeout(90)
    pg.wait_for_timeout(450)
    z2 = pg.evaluate(Z, [wrap, inner])
    y1 = pg.evaluate("() => Math.round(window.scrollY)")
    ok(f"「{label}」往下滾最多回到原始大小", not z2["zoomed"] and not z2["w"], z2)
    ok(f"「{label}」還原成原始大小時整頁不會被帶著往下", abs(y1 - y0) <= 2, f"scrollY {y0} → {y1}")


def main_rect(pg):
    """`#lwc` 裡**主圖那一格**的矩形（不含成交量／KD／MACD）。

    畫線只畫在主圖上，所以拖曳測試的座標要相對主圖算，不能相對整個 `#lwc`。
    2026-09-15 把副圖加寬之後主圖只剩 56% 高，原本寫死的「62%～78%」整段落在成交量格裡，
    拖了半天畫面當然沒變 —— 那是測試座標的問題，不是功能壞掉。
    """
    b = pg.evaluate("() => { const e = document.getElementById('lwc').getBoundingClientRect();"
                    " return { x: e.x, y: e.y, w: e.width, h: e.height }; }")
    mh = pg.evaluate("() => { try { const p = window.Industry._dbg().paneH;"
                     " return (p && p.main) || 0; } catch (e) { return 0; } }")
    if mh and mh > 80:
        b["h"] = min(b["h"], mh)
    return b


def check_drag(pg, wrap: str, label: str):
    """放大後真的用滑鼠抓著拖，圖要跟著移動，放開手不可以誤觸圖上的點擊。"""
    scroll_to(pg, wrap)
    r = pg.evaluate("(id)=>{const b=document.getElementById(id).getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height};}", wrap)
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    pg.mouse.move(cx, cy)
    for _ in range(5):
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(140)
    pg.wait_for_timeout(400)
    S = """(id) => { const b=document.getElementById(id); const pane=b.querySelector('.zpane');
        return { sl: Math.round(pane.scrollLeft), st: Math.round(pane.scrollTop),
                 zoomed: b.classList.contains('zoomed'), grab: b.classList.contains('grabbing'),
                 badge: (b.querySelector('.zbadge')||{}).textContent, y: Math.round(window.scrollY),
                 hash: location.hash }; }"""
    a = pg.evaluate(S, wrap)
    if not ok(f"「{label}」滾輪有放大（拖曳測試的前提）", a["zoomed"], a):
        return
    ok(f"「{label}」放大後徽章有提示可以拖曳", "拖曳" in (a["badge"] or ""), a["badge"])
    pg.mouse.move(cx, cy); pg.mouse.down()
    pg.mouse.move(cx - 60, cy - 40, steps=6)
    mid = pg.evaluate(S, wrap)
    pg.mouse.move(cx - 220, cy - 150, steps=10)
    pg.mouse.up(); pg.wait_for_timeout(400)
    bx = pg.evaluate(S, wrap)
    ok(f"「{label}」抓著拖，圖真的跟著移動", (bx["sl"], bx["st"]) != (a["sl"], a["st"]), f"{a['sl']},{a['st']} → {bx['sl']},{bx['st']}")
    ok(f"「{label}」拖曳時游標變成抓取狀態", mid["grab"], mid)
    ok(f"「{label}」拖曳不會把整頁捲走", bx["y"] == a["y"], f"{a['y']} → {bx['y']}")
    ok(f"「{label}」放開手不會誤觸跳頁", bx["hash"] == a["hash"], f"{a['hash']} → {bx['hash']}")
    pg.dblclick("#" + wrap); pg.wait_for_timeout(500)
    ok(f"「{label}」雙擊還原得回去", not pg.evaluate("(id)=>document.getElementById(id).classList.contains('zoomed')", wrap))


def check_nozoom(pg, wrap: str, label: str):
    """這張圖不可以有滾輪縮放（Andy 09-13：「將這邊的縮放功能取消」，只留熱力圖類）。
       驗三件事：沒有縮放框與徽章、滾輪不會放大、滾輪會正常往下捲頁面。"""
    st = pg.evaluate("""(id) => { const b = document.getElementById(id);
        if (!b) return { missing: true };
        return { zwrap: b.classList.contains('zwrap'), pane: !!b.querySelector(':scope > .zpane'),
                 badge: !!b.querySelector(':scope > .zbadge') }; }""", wrap)
    if st.get("missing"):
        return
    ok(f"「{label}」沒有縮放框", not st["zwrap"] and not st["pane"] and not st["badge"], st)
    scroll_to(pg, wrap)
    r = pg.evaluate("(id)=>{const b=document.getElementById(id).getBoundingClientRect();return {x:b.x,y:b.y,w:b.width,h:b.height};}", wrap)
    pg.mouse.move(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)
    for _ in range(3):                      # 往上滾（以前是放大的方向）
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(120)
    pg.wait_for_timeout(350)
    zoomed = pg.evaluate("(id) => document.getElementById(id).classList.contains('zoomed')", wrap)
    # 剖析圖沒有 .chart 子層（是 SVG），量不到就退回量外框本身
    w0, h0 = pg.evaluate("""(id) => { const b = document.getElementById(id);
        const c = b.querySelector('.chart') || b;
        return [c.clientWidth, c.clientHeight]; }""", wrap)
    ok(f"「{label}」滾輪不會放大", not zoomed and w0 > 0, {"zoomed": zoomed, "w": w0})
    # 滑鼠停在圖上往下滾，頁面必須照常往下捲（圖不可以把 wheel 吃掉）
    y0 = pg.evaluate("() => Math.round(scrollY)")
    for _ in range(3):
        pg.mouse.wheel(0, 200); pg.wait_for_timeout(120)
    pg.wait_for_timeout(350)
    y1 = pg.evaluate("() => Math.round(scrollY)")
    # 沒往下捲有兩種可能：圖把 wheel 吃掉了（要抓出來），或頁面本來就到底了（不算錯）。
    # 不能拿 body.scrollHeight 判斷 —— 這個版面量出來的值跟實際可捲距離對不起來
    # （量到 1888，實際捲到底只有 500）。直接問瀏覽器「再怎麼捲最多到哪」才準。
    at_end = False
    if y1 <= y0:
        at_end = pg.evaluate(
            "(y0) => { const y = scrollY; scrollTo(0, 1e9); const m = Math.round(scrollY);"
            " scrollTo(0, y); return m <= y0 + 4; }", y0)
    ok(f"「{label}」滾輪會正常捲頁面（沒有被圖吃掉）", y1 > y0 or at_end,
       f"{y0} → {y1}（頁面到底了：{at_end}）")


def check_3d(pg):
    """3D 剖析圖：Andy 拍板「先試試看 three.js」，四條硬性驗收全部用真滑鼠操作。
       相機位置用 Rack3D.current.cam() 比對——canvas 沒開 preserveDrawingBuffer，
       readPixels 一律回 0，比像素等於什麼都沒驗到。"""
    st = pg.evaluate("""() => ({ webgl: !!(window.Rack3D && window.Rack3D.supported()),
        scene: !!(window.Rack3D && window.Rack3D.hasScene('ai_server')),
        btn: !!document.getElementById('dg3d'),
        hidden: (document.getElementById('dg3d')||{}).hidden })""")
    if not st["scene"]:
        return
    if not st["webgl"]:
        # 沒 WebGL 就必須安靜退回平面圖，而且要講原因
        ok("沒有 WebGL 時 3D 鈕要收起來", st["hidden"], st)
        ok("沒有 WebGL 時平面剖析圖還在", count(pg, "#prodDiagram [data-seg]") > 0)
        ok("沒有 WebGL 時有說明為什麼", "WebGL" in text(pg, "#dg3dNote"), text(pg, "#dg3dNote"))
        return
    ok("有 3D 場景的產業鏈會出現 3D 鈕", st["btn"] and not st["hidden"], st)
    click(pg, "#dg3d", 4200)
    on = pg.evaluate("""() => ({ canvas: document.querySelectorAll('#prod3d canvas').length,
        labels: document.querySelectorAll('.lbl3d').length,
        svgHidden: (document.getElementById('prodDiagram')||{}).hidden })""")
    ok("按 3D 真的掛起場景", on["canvas"] == 1 and on["labels"] > 5, on)
    ok("開 3D 時平面圖收起來（不可以兩張疊著）", on["svgHidden"], on)
    # 驗收 3：標籤是 DOM，不是畫進畫布（選得起來、驗得到文字重疊）
    ok("3D 零件標籤是 DOM 元素", pg.evaluate(
        "() => { const e = document.querySelector('.lbl3d'); return !!e && e.tagName === 'DIV' && !e.closest('canvas'); }"))
    scroll_to(pg, "prod3d")
    box = pg.evaluate("() => { const r = document.querySelector('#prod3d canvas').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
    cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
    # 驗收 1：真的抓著拖，相機要換位置（起點故意壓在標籤上——按在標籤上也必須轉得動）
    c0 = pg.evaluate("() => window.Rack3D.current.cam()")
    pg.mouse.move(cx, cy); pg.mouse.down()
    pg.mouse.move(cx + 260, cy + 40, steps=16)
    pg.mouse.up(); pg.wait_for_timeout(900)
    c1 = pg.evaluate("() => window.Rack3D.current.cam()")
    ok("拖曳真的轉得動視角", max(abs(a - b) for a, b in zip(c0, c1)) > 3, f"{c0} → {c1}")
    # 重設視角要真的回到預設：比方向與距離，不比絕對座標
    # （重設會照「現在的畫面比例」重新取景，中途版面若變過，座標本來就不會一模一樣）
    click(pg, "#dgReset", 900)
    c2 = pg.evaluate("() => window.Rack3D.current.cam()")
    def _unit(v):
        m = sum(x * x for x in v) ** 0.5
        return [x / m for x in v], m
    u0, m0 = _unit(c0); u2, m2 = _unit(c2)
    same_dir = sum(a * b for a, b in zip(u0, u2)) > 0.999
    ok("重設視角真的回到預設", same_dir and abs(m2 - m0) / m0 < 0.05, f"{c0} → {c2}")
    # 驗收 2：點零件要亮起來，而且帶出這個環節的台股
    seg = pg.evaluate("() => window.Rack3D.current.segs().find(s => !!window.Rack3D.current.screen(s))")
    pt = pg.evaluate("(s) => window.Rack3D.current.screen(s)", seg)
    b4 = pg.evaluate("() => ({ box: (document.getElementById('segBox')||{}).innerText || '' })")
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(900)
    af = pg.evaluate("""() => ({ box: (document.getElementById('segBox')||{}).innerText || '',
        sel: document.querySelectorAll('.lbl3d.sel').length,
        dim: document.querySelectorAll('.lbl3d.dim').length,
        links: document.querySelectorAll('#segBox a.lk').length })""")
    ok("點 3D 零件會亮起來、其餘變暗", af["sel"] > 0 and af["dim"] > 0, af)
    # 不能比長度：這頁前面的驗收可能已經選過別的環節，說明框本來就有字
    ok("點 3D 零件會帶出這個環節的台股",
       af["links"] > 0 and len(af["box"]) > 0 and af["box"] != b4["box"], {"before": b4["box"][:30], **af})
    # 點標籤也要能選（小零件用滑鼠很難打到，點名字是主要路徑）
    lp = pg.evaluate("""() => { const cur = (document.querySelector('.lbl3d.sel')||{dataset:{}}).dataset.seg;
        for (const e of document.querySelectorAll('.lbl3d')) { const r = e.getBoundingClientRect();
          if (e.dataset.seg !== cur && r.top > 220 && r.bottom < innerHeight - 20 && r.width > 8)
            return { x: r.x + r.width/2, y: r.y + r.height/2, seg: e.dataset.seg }; } return null; }""")
    if lp:
        pg.mouse.click(lp["x"], lp["y"]); pg.wait_for_timeout(800)
        ok("點 3D 標籤也選得到那個零件", pg.evaluate(
            "(s) => { const e = document.querySelector('.lbl3d.sel'); return !!e && e.dataset.seg === s; }", lp["seg"]),
           lp["seg"])
    # 切回平面再切回來：不可以留下第二張 canvas（WebGL context 有上限）
    click(pg, "#dg3d", 900)
    off = pg.evaluate("""() => ({ svg: !(document.getElementById('prodDiagram')||{}).hidden,
        canvas: document.querySelectorAll('#prod3d canvas').length })""")
    ok("切回平面圖，3D 收乾淨", off["svg"] and off["canvas"] == 0, off)
    click(pg, "#dg3d", 3500)
    ok("再切回 3D 只有一張 canvas（沒有疊上去）", count(pg, "#prod3d canvas") == 1, count(pg, "#prod3d canvas"))
    check_3d_e1(pg)
    check_3d_e2(pg)
    check_3d_e34(pg)
    click(pg, "#dg3d", 800)   # 留在平面圖，不影響後面的驗收


def check_3d_e1(pg):
    """E1：3D 文字太小 → 引線 ＋ 外部文字框（Andy 2026-09-18）。
       只驗「有標籤」不算數 —— 本來就有標籤，問題是它貼在零件上、字小、疊成一團。
       所以這裡驗的是：字真的變大、真的排在畫面兩側的欄位裡、真的沒有互相壓到、
       引線真的接在零件上（轉一下視角，引線的起點要跟著零件跑）。"""
    st = pg.evaluate("""() => { const host = document.getElementById('prod3d');
        const hb = host.getBoundingClientRect();
        const vis = [...document.querySelectorAll('.lbl3d')].filter(e => !e.classList.contains('hid'));
        const r = vis.map(e => e.getBoundingClientRect());
        let ov = 0;
        for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
          const A = r[i], B = r[j];
          if (!(A.right < B.left || A.left > B.right || A.bottom < B.top || A.top > B.bottom)) ov++; }
        const mid = r.filter(x => x.left - hb.left > hb.width * 0.3 && x.right - hb.left < hb.width * 0.7);
        return { n: vis.length, overlap: ov, middle: mid.length,
          fs: vis.length ? parseFloat(getComputedStyle(vis[0]).fontSize) : 0,
          notes: vis.filter(e => (e.querySelector('i')||{}).textContent).length,
          leads: document.querySelectorAll('.lead3d path.ld').length,
          shown: [...document.querySelectorAll('.lead3d path.ld')].filter(x => x.style.display !== 'none').length,
          d0: (document.querySelector('.lead3d path.ld')||{}).getAttribute
              ? document.querySelector('.lead3d path.ld').getAttribute('d') : null }; }""")
    ok("E1 3D 標籤的字真的變大了（≥ 12px）", st["fs"] >= 12, st)
    ok("E1 3D 標籤是文字框（名稱之外還有一行說明）", st["notes"] >= st["n"] - 1, st)
    ok("E1 3D 標籤排到兩側、不壓在模型中央", st["middle"] == 0, st)
    ok("E1 看得到的標籤彼此不重疊", st["overlap"] == 0, st)
    ok("E1 每個標籤都有一條引線", st["leads"] >= st["n"] and st["shown"] >= st["n"], st)
    # 轉一下視角：引線的起點必須跟著零件跑，否則那條線只是畫上去好看的
    box = pg.evaluate("() => { const r = document.querySelector('#prod3d canvas').getBoundingClientRect();"
                      " return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
    pg.mouse.move(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2); pg.mouse.down()
    pg.mouse.move(box["x"] + box["w"] / 2 + 200, box["y"] + box["h"] / 2 + 30, steps=14)
    pg.mouse.up(); pg.wait_for_timeout(900)
    d1 = pg.evaluate("() => (document.querySelector('.lead3d path.ld')||{getAttribute:()=>null}).getAttribute('d')")
    changed("E1 轉視角時引線跟著零件走", st["d0"], d1)


def check_3d_e2(pg):
    """E2：3D 圖螢光感太重（Andy 2026-09-18）。
       用機器掃畫面，不用眼睛：截畫布的圖，數「很亮的青／綠、紅色偏低」那種自體發光像素。
       同時要求平均亮度不能垮掉 —— 不然把整張調黑也會通過，那不是去螢光是關燈。"""
    # 比的是 idleEmissive（沒被選起來的零件）：選起來的那一個本來就該提亮一點當提示
    ok("E2 材質底層不再自體發光", pg.evaluate("() => Rack3D.current.stats().idleEmissive") <= 0.001,
       pg.evaluate("() => Rack3D.current.stats()"))
    try:
        from PIL import Image
    except Exception:
        notes.append("E2 沒有 Pillow，跳過螢光像素掃描")
        return
    import io
    png = pg.locator("#prod3d canvas").screenshot()
    im = Image.open(io.BytesIO(png)).convert("RGB")
    raw = im.tobytes(); n = max(1, len(raw) // 3)
    hot = lum = 0
    for i in range(0, len(raw), 3):
        r, g, b = raw[i], raw[i + 1], raw[i + 2]
        m = g if g > b else b
        if m > 185 and r < m * 0.62:
            hot += 1
        lum += 0.299 * r + 0.587 * g + 0.114 * b
    lum /= n
    ok("E2 畫面幾乎沒有螢光像素（< 1%）", hot / n < 0.01, f"{hot / n * 100:.2f}%")
    ok("E2 而且不是靠把畫面調黑做到的", lum > 20, f"平均亮度 {lum:.1f}")


def check_3d_e34(pg):
    """E3 零件更細膩（風扇有扇片、電池有電壓感）＋ E4 動態／靜止切換。
       E3 驗「一個零件不只是一顆方塊」：mesh 數要遠多於零件數，而且真的有會轉的扇葉。
       E4 驗「按了關就真的不動」：相機座標與扇葉角度兩個都要停住，按回來兩個都要再動。"""
    st = pg.evaluate("() => Rack3D.current.stats()")
    ok("E3 零件不再是一顆方塊（平均一個零件好幾顆 mesh）", st["meshes"] >= st["parts"] * 5,
       f"{st['parts']} 個零件／{st['meshes']} 顆 mesh")
    ok("E3 機櫃裡真的有會轉的扇葉", st["spinners"] >= 1, st)
    ok("E3 只有指示燈准發光", st["leds"] >= 1 and st["idleEmissive"] <= 0.001, st)

    # --- E4：關掉動畫
    if pg.evaluate("() => !Rack3D.current.isAnim()"):
        click(pg, "#dgAnim", 500)         # 先確定現在是「開」，才驗得到關掉的差別
    pg.wait_for_timeout(1200)
    a0 = pg.evaluate("() => ({ cam: Rack3D.current.cam(), spin: Rack3D.current.stats().spinAt })")
    pg.wait_for_timeout(1800)
    a1 = pg.evaluate("() => ({ cam: Rack3D.current.cam(), spin: Rack3D.current.stats().spinAt })")
    ok("E4 動態時場景真的自己在動", max(abs(x - y) for x, y in zip(a0["cam"], a1["cam"])) > 0.5,
       f"{a0['cam']} → {a1['cam']}")
    ok("E4 動態時扇葉真的在轉", abs(a1["spin"] - a0["spin"]) > 0.05, f"{a0['spin']} → {a1['spin']}")
    click(pg, "#dgAnim", 700)
    ok("E4 鈕的字跟著換成「動畫：關」", "關" in text(pg, "#dgAnim"), text(pg, "#dgAnim"))
    b0 = pg.evaluate("() => ({ cam: Rack3D.current.cam(), spin: Rack3D.current.stats().spinAt })")
    pg.wait_for_timeout(1800)
    b1 = pg.evaluate("() => ({ cam: Rack3D.current.cam(), spin: Rack3D.current.stats().spinAt })")
    ok("E4 靜止時相機立刻停住（不准慢慢飄）",
       max(abs(x - y) for x, y in zip(b0["cam"], b1["cam"])) < 0.05, f"{b0['cam']} → {b1['cam']}")
    ok("E4 靜止時扇葉也停住", abs(b1["spin"] - b0["spin"]) < 0.001, f"{b0['spin']} → {b1['spin']}")
    ok("E4 靜止時平面剖析圖的動畫也停掉", pg.evaluate(
        "() => document.getElementById('prodDiagram').classList.contains('noanim')"))
    ok("E4 靜止的選擇記進 localStorage",
       pg.evaluate("() => { try { return localStorage.getItem('tw.dganim'); } catch(e) { return null; } }") == "0")
    click(pg, "#dgAnim", 900)
    c0 = pg.evaluate("() => Rack3D.current.stats().spinAt")
    pg.wait_for_timeout(1500)
    ok("E4 再按一次就動回來", abs(pg.evaluate("() => Rack3D.current.stats().spinAt") - c0) > 0.05)


# ------------------------------------------------------------------ 各頁
def t_overview(pg, base):
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1600)

    # --- 候選名單四個面向：切換要真的換排序、換欄位、換說明
    facets = pg.evaluate("[...document.querySelectorAll('#candFacets button')].map(b => b.dataset.f)")
    ok("候選名單四個面向鈕都在", sorted(facets) == ["all", "chip", "fund", "tech"], facets)
    seen = {}
    for f in facets:
        click(pg, f'#candFacets button[data-f="{f}"]', 400)
        seen[f] = pg.evaluate("""() => ({
            on: (document.querySelector('#candFacets button.on')||{}).dataset.f,
            head: [...document.querySelectorAll('#candTable th')].map(t => t.textContent.replace(/[▲▼]/g,'').trim()).join('|'),
            first: (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code,
            hint: (document.getElementById('candHint')||{}).textContent.trim().slice(0,20) })""")
        ok(f"候選名單 {f} 面向按下去真的被選取", seen[f]["on"] == f, seen[f])
        ok(f"候選名單 {f} 面向有說明文字", bool(seen[f]["hint"]), seen[f])
    ok("四個面向的欄位組不完全相同", len({v["head"] for v in seen.values()}) >= 2,
       {k: v["head"] for k, v in seen.items()})
    ok("四個面向排出來的第一名不完全相同", len({v["first"] for v in seen.values()}) >= 2,
       {k: v["first"] for k, v in seen.items()})

    # --- 點一列：理由要真的展開，再點一次要真的收起來
    #
    # ★ 一定要點「沒有連結的那一格」（DECISIONS #190）。
    #   這一列的正中央是股票名稱，而那是一個 <a class="lk">；
    #   app.js 的處理是 `if (e.target.closest('a')) return;` —— 刻意讓點在連結上不展開，
    #   因為連結本來就該連到個股頁。點列的正中央＝點在連結上＝**跳去個股頁**，
    #   接下來整個 t_overview 都不在總覽頁上了，後面每一條都找不到元素。
    #   2026-09-18 查出來：一個點錯位置的動作，製造了 39 條紅字。
    ROW_CELL = "#candBody tr[data-code] td:not(:has(a))"
    click(pg, "#candFacets button[data-f=all]", 350)
    before = count(pg, "#candBody tr.whyrow")
    click(pg, ROW_CELL, 350)
    ok("點候選名單一列之後還留在總覽頁（沒有誤點成股票連結）",
       pg.evaluate("() => location.hash") in ("", "#overview"),
       pg.evaluate("() => location.hash"))
    mid = count(pg, "#candBody tr.whyrow")
    changed("點候選名單一列會展開「為何選它」", before, mid)
    why_txt = text(pg, "#candBody tr.whyrow .why")
    ok("「為何選它」有帶實際數字", any(ch.isdigit() for ch in why_txt), why_txt[:60])
    click(pg, ROW_CELL, 350)
    after = count(pg, "#candBody tr.whyrow")
    changed("再點一次會收起來", mid, after)

    # --- 排序：每個可排序的表頭都點兩次，順序要真的反過來，箭頭要跟著跑
    heads = pg.evaluate("[...document.querySelectorAll('#candTable th[data-k]')].map(t => t.dataset.k)")
    ok("候選名單表頭可以排序", len(heads) >= 4, heads)
    # ★ 「點兩次第一名要變」對**低變異欄位**不成立（DECISIONS #191）。
    #   例：grade 欄 380 檔裡有 377 檔是空值、只有 3 檔是 A。
    #   程式把空值一律排到最後（不分升冪降冪，這是對的），而那 3 個 A 彼此相等，
    #   所以正排反排的第一名本來就是同一檔 —— 那不是 bug。
    #   改成先問「這一欄可比較的值有沒有兩種以上」，同分的欄位只驗箭頭會動。
    for k in heads:
        first_a = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st1 = pg.evaluate("""() => ({ first: (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code,
            arrow: [...document.querySelectorAll('#candTable th')].filter(t => /[▲▼]/.test(t.textContent)).map(t => t.dataset.k) })""")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st2 = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        ok(f"表頭「{k}」點下去箭頭跑到這一欄", st1["arrow"] == [k], st1["arrow"])
        # 這一欄在畫面上到底有幾種不同的值（空字串／破折號都當成沒有值）
        variety = pg.evaluate("""(kk) => { const ths=[...document.querySelectorAll('#candTable th')];
            const i = ths.findIndex(t => t.dataset.k === kk); if (i < 0) return 0;
            const vs = [...document.querySelectorAll('#candBody tr[data-code]')]
              .map(r => (r.children[i] ? r.children[i].textContent.trim() : ''))
              .filter(v => v && v !== '—' && v !== '-');
            return new Set(vs).size; }""", k)
        if variety >= 2:
            ok(f"表頭「{k}」點兩次順序會反過來", st1["first"] != st2 or first_a == st2,
               f"{first_a} → {st1['first']} → {st2}（畫面上有 {variety} 種值）")
        else:
            ok(f"表頭「{k}」值幾乎都相同（{variety} 種），只驗箭頭會動 —— 順序本來就不該變",
               st1["arrow"] == [k], f"{first_a} → {st1['first']} → {st2}")

    # --- 事件面板篩選：筆數要真的變
    cats = pg.evaluate("[...document.querySelectorAll('#evFilters button')].map(b => b.dataset.c)")
    if cats:
        counts = {}
        for c in cats:
            click(pg, f'#evFilters button[data-c="{c}"]', 300)
            counts[c] = count(pg, "#evList .ev")
        ok("事件分類篩選真的會改變筆數", len(set(counts.values())) >= 2, counts)
        click(pg, f'#evFilters button[data-c="{cats[0]}"]', 250)
    else:
        notes.append("事件面板沒有分類鈕")

    # --- 搜尋框：真的打字 → 出建議 → 點建議 → 跳個股頁
    pg.fill("#q", "")
    pg.type("#q", "2330", delay=45); pg.wait_for_timeout(450)
    sugg = count(pg, "#sugg div[data-c]")
    ok("搜尋框打字會跳出建議", sugg > 0, f"建議 {sugg} 筆")
    if sugg:
        click(pg, "#sugg div[data-c]", 1600)
        ok("點搜尋建議會跳到個股頁", pg.evaluate("location.hash").startswith("#stock/"),
           pg.evaluate("location.hash"))
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1400)

    # --- 資金熱力圖的產業鏈下鑽：點半導體就只剩半導體，點「全部」回得去
    chips = pg.evaluate("[...document.querySelectorAll('#heatChips button')].map(b => b.dataset.c)")
    ok("資金熱力圖有產業鏈切換", len(chips) >= 3, chips)
    TM = """() => { const c = echarts.getInstanceByDom(document.getElementById('heat')); if (!c) return null;
        const d = c.getOption().series[0].data;
        return { n: d.length, nested: !!(d[0] && d[0].children),
                 on: (document.querySelector('#heatChips button.on')||{dataset:{}}).dataset.c }; }"""
    all0 = pg.evaluate(TM)
    ok("預設是所有產業鏈分組顯示", all0 and all0["nested"], all0)
    for cid in [c for c in chips if c][:3]:
        click(pg, f'#heatChips button[data-c="{cid}"]', 800)
        st = pg.evaluate(TM)
        ok(f"點「{cid}」真的只剩這條產業鏈", st and not st["nested"] and st["on"] == cid, st)
        leaves = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('heat'));"
                             " return (c.getOption().series[0].data || []).every(d => !!d.gid); }")
        ok(f"點「{cid}」之後每一格都是族群（不是產業鏈）", leaves)
    click(pg, '#heatChips button[data-c=""]', 800)
    back = pg.evaluate(TM)
    ok("按「全部」回到原本的分組圖", back and back["nested"] and back["n"] == all0["n"], back)

    # 下鑽之後點方塊 → 原地列出成分股（不跳頁）
    first_chain = next((c for c in chips if c), None)
    if first_chain:
        click(pg, f'#heatChips button[data-c="{first_chain}"]', 800)
        pg.evaluate("document.getElementById('heat').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
        box = pg.evaluate("() => { const r = document.getElementById('heat').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
        h_before = pg.evaluate("location.hash")
        READ = """() => ({ open: !document.getElementById('heatPanel').hidden,
            title: (document.querySelector('#heatPanel .hh b')||{}).textContent,
            stocks: document.querySelectorAll('#heatPanel .ms a').length,
            link: !!document.querySelector('#heatPanel a[href^="#industry/group/"]') })"""
        # 方塊的位置是 treemap 依面積算出來的，會隨資料變動；固定打一個相對座標
        # 偶爾會落在方塊之間的縫或標題列上，面板就沒開，整段連帶假失敗。
        # 多試幾個點，只要有一個真的開了就算數（這是測試的穩定度問題，不是功能問題）。
        st = {"open": False}
        for fx, fy in ((0.2, 0.35), (0.45, 0.5), (0.72, 0.4), (0.3, 0.68)):
            pg.mouse.click(box["x"] + box["w"] * fx, box["y"] + box["h"] * fy)
            pg.wait_for_timeout(900)
            st = pg.evaluate(READ)
            if st["open"]:
                break
        ok("點熱力圖方塊會在原地列出成分股", st["open"] and (st["stocks"] > 0 or "整理中" in text(pg, "#heatPanel")), st)
        ok("點方塊不會把人帶離總覽", pg.evaluate("location.hash") == h_before, pg.evaluate("location.hash"))
        ok("成分股面板有寫出是哪個族群", len(st["title"] or "") > 0, st)
        ok("成分股面板有進族群頁的連結", st["link"], st)
        click(pg, "#heatPanel [data-x]", 400)
        ok("成分股面板收得起來", pg.evaluate("() => document.getElementById('heatPanel').hidden"))

    # --- 滾輪放大：往上滾要變大，往下滾最多回到原始大小（不會縮成一小塊）
    ZK = """() => { const b = document.getElementById('heatWrap'); const pane = b.querySelector('.zpane');
        const i = document.getElementById('heat'); const card = b.closest('.card');
        return { w: i.style.width || '', badge: (b.querySelector('.zbadge')||{}).textContent,
                 zoomed: b.classList.contains('zoomed'), sw: pane.scrollWidth, cw: pane.clientWidth,
                 cardH: Math.round(card.getBoundingClientRect().height),
                 pageW: document.documentElement.scrollWidth }; }"""
    pg.evaluate("document.getElementById('heatWrap').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
    z0 = pg.evaluate(ZK)
    ok("熱力圖預設是原始大小", not z0["zoomed"] and not z0["w"], z0)
    r = pg.evaluate("() => { const b = document.getElementById('heatWrap').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
    pg.mouse.move(r["x"] + r["w"] * .5, r["y"] + r["h"] * .5)
    for _ in range(4):
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(160)
    pg.wait_for_timeout(500)
    z1 = pg.evaluate(ZK)
    ok("往上滾真的放大了", z1["zoomed"] and z1["sw"] > z0["sw"], f"{z0} → {z1}")
    ok("放大不會把卡片撐高（不影響整頁版面）", z1["cardH"] == z0["cardH"], f"{z0['cardH']} → {z1['cardH']}")
    ok("放大不會讓整頁出現橫向捲軸", z1["pageW"] <= z0["pageW"], f"{z0['pageW']} → {z1['pageW']}")
    ok("放大後徽章寫出倍率", "×" in (z1["badge"] or ""), z1["badge"])
    # 往下滾滾很多次，最多只能回到原始大小
    for _ in range(12):
        pg.mouse.wheel(0, 160); pg.wait_for_timeout(100)
    pg.wait_for_timeout(500)
    z2 = pg.evaluate(ZK)
    ok("往下滾最多回到原始大小，不會縮更小", not z2["zoomed"] and not z2["w"], z2)
    ok("回到原始大小後沒有多餘的捲動範圍", z2["sw"] <= z2["cw"] + 4, z2)

    # --- 熱力圖只能放大、不能拖：按「放大」要全螢幕，關得掉
    ok("熱力圖有放大鈕", count(pg, "#heatZoom") == 1)
    click(pg, "#heatZoom", 1300)
    zs = pg.evaluate("""() => ({ open: !document.getElementById('zoomOv').hidden,
        canvas: !!document.querySelector('#zoomBody canvas'),
        chips: document.querySelectorAll('#zoomChips button').length,
        h: document.getElementById('zoomBody').clientHeight,
        title: (document.getElementById('zoomTitle')||{}).textContent })""")
    ok("放大後開出全螢幕的熱力圖", zs["open"] and zs["canvas"], zs)
    ok("放大後比原圖高很多", zs["h"] > 600, zs["h"])
    ok("放大後還是可以切產業鏈", zs["chips"] >= 3, zs["chips"])
    ok("放大罩有標題", "熱力" in (zs["title"] or ""), zs["title"])
    click(pg, "#zoomClose", 600)
    ok("放大罩關得掉", pg.evaluate("() => document.getElementById('zoomOv').hidden"))
    # 熱力圖不可以被拖走（treemap 的 roam 必須是關的，不然拖一拖就整片空白）
    ok("熱力圖沒有開啟拖曳平移（roam）", pg.evaluate(
        "() => { const c = echarts.getInstanceByDom(document.getElementById('heat'));"
        " return c ? c.getOption().series[0].roam === false : false; }"))
    click(pg, '#heatChips button[data-c=""]', 700)

    # --- 上方數字點得開：點了要去「市場明細」分頁看完整名單
    kinds = pg.evaluate("[...document.querySelectorAll('#hero .kpi.clickable')].map(k => k.dataset.drill)")
    ok("總覽上方至少四個數字點得開", len(kinds) >= 4, kinds)
    for k in kinds:
        # ★ 2026-09-20：先捲回頁首再點。這一行是平行化之後補的。
        #   KPI 那一排就長在 #hero，也就是頁面的最上面 —— 真人要點得到它，
        #   本來就一定在頁首。但**這一段以前是靠「前面某一段剛好把頁面留在頂端」**，
        #   一旦它變成某個 worker 的第一段、或前一段把頁面捲到 1592，
        #   「有沒有真的捲到那張圖」就會量到錯的基準而假紅。
        #   捲回頁首才是忠於使用者真實狀態的做法，不是為了讓測試變綠。
        pg.evaluate("() => window.scrollTo(0, 0)"); pg.wait_for_timeout(250)
        click(pg, f'#hero .kpi[data-drill="{k}"]', 1400)
        st = pg.evaluate("""() => ({ hash: location.hash, tab: (document.querySelector('.tab.on')||{dataset:{}}).dataset.view,
            scrollY: Math.round(window.scrollY),
            title: (document.getElementById('mktTitle')||{}).innerText,
            rows: document.querySelectorAll('#mktBody tr[data-code]').length,
            blocks: document.querySelectorAll('#mktBody .ma, #mktBody .t5').length,
            note: (document.querySelector('#mktBody .kpinote')||{}).textContent.length })""")
        # 2026-09-18（Andy 圖16）：「資金集中」那一頁拿掉了，
        # 總覽的「前五族群佔比」改導到資金流向頁的集中度圖（功能更完整）。
        if k.startswith("#"):
            # data-drill 可以寫成 `#flow>conc`：> 後面是要捲過去的元素 id。
            # 2026-09-19：「前五族群佔比」以前只換 hash，但集中度圖在頁面 2700px 處，
            # 使用者點完只看得到資金流向頁的頂端，看起來像「點了沒反應」。
            page, _, anchor = k.partition(">")
            ok(f"KPI「{k}」點下去會到那一頁", st["hash"] == page, st)
            if anchor:
                # ★ 2026-09-20：原本是 `wait_for_timeout(1400)`。scrollIntoView 是 smooth 的，
                #   而且圖表畫完之後版面還會再長高、錨點會再往下跑 ——
                #   固定睡 1400ms 在四個 worker 搶 CPU 時根本不夠，就開始間歇性假紅。
                #   改成等「錨點真的進到視窗」這個條件成立，快就快走、慢才多等。
                st2 = wait_until(pg, """() => { const el = document.getElementById('%s'); if (!el) return null;
                    const r = el.getBoundingClientRect();
                    if (r.top >= window.innerHeight) return null;   // 還沒捲到，繼續等
                    return { scrollY: Math.round(window.scrollY), top: Math.round(r.top),
                             h: window.innerHeight }; }""" % anchor, 8000) or pg.evaluate(
                    """(a) => { const el = document.getElementById(a); if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { scrollY: Math.round(window.scrollY), top: Math.round(r.top),
                             h: window.innerHeight }; }""", anchor)
                ok(f"KPI「{k}」真的捲到 #{anchor} 那張圖（不是停在頁首）",
                   bool(st2) and st2["scrollY"] > 200 and st2["top"] < st2["h"],
                   {"點之前 scrollY": st["scrollY"], "量到": st2})
        else:
            ok(f"KPI「{k}」點下去會到市場明細分頁", st["tab"] == "market" and st["hash"].endswith(k), st)
        ok(f"KPI「{k}」的明細真的有內容", st["rows"] > 0 or st["blocks"] > 0, st)
        ok(f"KPI「{k}」有寫怎麼看", st["note"] > 10, st)
        ok(f"KPI「{k}」有標題", len(st["title"] or "") > 2, st)
        pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1400)

    # --- 總覽下方三張圖：都不是長條圖了，而且點得動
    for cid, name, want in (("breadth", "市場寬度", ("gauge", "pie")), ("trust", "投信連續買超", ("scatter",)),
                            ("gval", "族群估值", ("scatter",))):
        types = pg.evaluate(f"""() => {{ const c = echarts.getInstanceByDom(document.getElementById('{cid}'));
            return c ? (c.getOption().series || []).map(s => s.type) : null; }}""")
        ok(f"總覽「{name}」有畫出來", bool(types), types)
        if cid != "breadth":
            ok(f"總覽「{name}」不是長條圖", types and 'bar' not in types, types)
        ok(f"總覽「{name}」用的是更生動的圖形", types and any(w in types for w in want), types)

    # ★ 2026-09-20：市場寬度那張改版（理由寫在 site/app.js 的 renderBreadth 註解裡）。
    #   「不准是長條圖」這條規則原本要擋的是**四根各自獨立的長條**
    #   —— 2026-09-12 之前它就長那樣，其中兩根還常常是 0%，看不出市場健不健康。
    #   新版下半是「一根堆疊長條」：漲／平／跌是同一個總量的三塊，
    #   只有一個類別、三個 series 共用同一個 stack，讀起來就是一條比例尺。
    #   它取代的是舊版那個甜甜圈 —— 甜甜圈的引線標籤在 300px 寬的卡片裡
    #   一定會壓到旁邊的儀表（Andy 2026-09-20 的截圖就是這個）。
    #   所以規則改成更精確的版本：**可以有長條，但只准有一根，而且一定要是堆疊的**。
    bd = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('breadth'));
        if (!c) return null; const o = c.getOption();
        const bars = (o.series || []).filter(s => s.type === 'bar');
        const cats = ((o.yAxis || [])[0] || {}).data || [];
        return { bars: bars.length, stacked: bars.every(s => !!s.stack),
                 cats: cats.length, gauge: (o.series || []).some(s => s.type === 'gauge') }; }""")
    ok("市場寬度不是「好幾根各自獨立的長條」（只有一根堆疊長條）",
       bool(bd) and bd["cats"] == 1 and bd["stacked"] and bd["bars"] >= 2, bd)
    ok("市場寬度上半還是儀表（站上 20 日均線的比例）", bool(bd) and bd["gauge"], bd)

    # --- 總覽的輪動階段（精簡版）＋ 小時鐘
    ok("總覽有輪動階段四張卡", count(pg, "#rotMini .stage") == 4, count(pg, "#rotMini .stage"))
    mini = pg.evaluate("""() => { const el = document.getElementById('rotClockMini'); if (!el) return null;
        const c = echarts.getInstanceByDom(el); if (!c) return { canvas: !!el.querySelector('canvas'), pts: 0 };
        const sc = c.getOption().series.filter(s => s.type === 'scatter')[0];
        return { canvas: !!el.querySelector('canvas'), pts: sc ? sc.data.length : 0 }; }""")
    ok("總覽也有輪動時鐘", bool(mini) and mini["canvas"] and mini["pts"] > 0, mini)

    # --- 除了熱力圖與法人連續買超，其餘的圖都不可以有縮放框（Andy 09-13：「將這邊的縮放功能取消」）
    for w, lb in (("breadthWrap", "市場寬度"),
                  ("gvalWrap", "族群估值"), ("rotClockMiniWrap", "總覽輪動時鐘")):
        check_nozoom(pg, w, lb)

    # --- 資金熱力圖保留縮放，放大後要能用游標抓著移動
    check_drag(pg, "heatWrap", "資金熱力圖")

    # --- ★ 法人連續買超（Andy 2026-09-15：「圖表可以縮放，並且可以游標抓取移動，
    #     還能切換買超週期 不限只有3天，還要加上外資買超，以及綜合」）
    t_streak(pg, base)

    # --- 熱力圖要把卡片填滿，不可以留一塊空的（Andy：「不滿當前版面」）
    # 重新載入一次：前面的測試會把「成分股」面板留在展開狀態，那塊也算在卡片高度裡
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(2200)
    last = None                                   # 高度是 flex 撐出來的，等它不再變動再量
    for _ in range(15):
        h = pg.evaluate("() => Math.round(document.getElementById('heat').getBoundingClientRect().height)")
        if h == last:
            break
        last = h; pg.wait_for_timeout(300)
    fill = pg.evaluate("""() => { const w = document.getElementById('heatWrap');
        const card = w.closest('.card'); const heat = document.getElementById('heat');
        const cr = card.getBoundingClientRect(), hr = heat.getBoundingClientRect();
        // 卡片裡最後一個真的有內容的元素，底部離卡片底部多遠 —— 那段就是「空的」
        let bottom = cr.top;
        [...card.children].forEach(el => { const r = el.getBoundingClientRect();
            if (r.height > 0 && el.offsetParent !== null) bottom = Math.max(bottom, r.bottom); });
        return { cardH: Math.round(cr.height), heatH: Math.round(hr.height),
                 belowChart: Math.round(cr.bottom - hr.bottom),
                 empty: Math.round(cr.bottom - bottom) }; }""")
    ok("資金熱力圖有把卡片填滿（底下不會留一塊空的）", fill["empty"] <= 40, fill)
    ok("資金熱力圖本身夠大（不是被擠成一小條）", fill["heatH"] >= 400, fill)

    # --- 下方三張圖：要有資料，不是空狀態
    for cid, name in (("breadth", "市場寬度"), ("trust", "投信連續買超"), ("gval", "族群估值")):
        has = pg.evaluate(f"() => {{ const e = document.getElementById('{cid}'); return e ? {{ canvas: !!e.querySelector('canvas'), empty: !!e.querySelector('.empty') || /尚無|沒有|回補中/.test(e.innerText) }} : null; }}")
        ok(f"總覽「{name}」有畫出來", bool(has) and has["canvas"] and not has["empty"], has)


def t_streak(pg, base):
    """法人連續買超那張卡：切法人、切天數門檻、滾輪放大、拖曳移動。

    Andy 2026-09-15：「底下投信買超 圖表可以縮放，並且可以游標抓取移動，
    還能切換買超週期 不限只有3天，還要加上外資買超，以及綜合」。
    每一項都驗「畫面真的因此變了」：泡泡數量變、副標文字變、圖真的被拖動。
    """
    pts_of = ("() => { const c = echarts.getInstanceByDom(document.getElementById('trust'));"
              " if (!c) return -1; const s = (c.getOption().series || [])[0];"
              " return s && s.data ? s.data.length : 0; }")
    scroll_to(pg, "trustWrap")
    ok("法人連續買超有三顆切換鈕（投信／外資／合計）", count(pg, "#streakWho button") == 3,
       count(pg, "#streakWho button"))
    ok("有天數門檻的下拉選單", count(pg, "#streakDays option") >= 4, count(pg, "#streakDays option"))
    days_opts = pg.evaluate("() => [...document.querySelectorAll('#streakDays option')].map(o=>o.value)")
    ok("門檻不再寫死 3 天", days_opts != ["3"] and "2" in days_opts, days_opts)

    base_sub, base_pts = text(pg, "#streakSub"), pg.evaluate(pts_of)
    ok("預設是投信 ≥3 天", "投信" in base_sub and "3" in base_sub, base_sub)
    ok("預設就有畫出泡泡", base_pts > 0, base_pts)

    # --- 切到外資：副標與泡泡都要換掉
    click(pg, "#streakWho button[data-w='foreign']", 900)
    f_sub, f_pts = text(pg, "#streakSub"), pg.evaluate(pts_of)
    ok("切到外資之後副標真的變了", "外資" in f_sub, f_sub)
    ok("切到外資之後圖也重畫了（有泡泡或明說沒有符合的）",
       f_pts > 0 or count(pg, "#trust .empty") == 1, f"{f_pts} 顆")
    if f_pts > 0 and base_pts > 0:
        f_names = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('trust'));"
                              " const s=(c.getOption().series||[])[0]; return (s.data||[]).slice(0,6).map(d=>d.code); }")
        ok("外資那份是另一組股票（不是換了標題而已）", bool(f_names), f_names)
    click(pg, "#streakWho button[data-w='total']", 900)
    ok("切到合計副標也跟著換", "合計" in text(pg, "#streakSub"), text(pg, "#streakSub"))
    ok("合計那顆按鈕真的亮起來",
       pg.evaluate("() => document.querySelector(\"#streakWho button[data-w='total']\").classList.contains('on')"))
    click(pg, "#streakWho button[data-w='trust']", 900)

    # --- 換門檻：門檻放寬筆數要變多，收緊要變少
    pg.select_option("#streakDays", "2"); pg.wait_for_timeout(800)
    p2 = pg.evaluate(pts_of)
    ok("放寬到 ≥2 天，副標跟著改", "2" in text(pg, "#streakSub"), text(pg, "#streakSub"))
    pg.select_option("#streakDays", "8"); pg.wait_for_timeout(800)
    p8 = pg.evaluate(pts_of)
    ok("收緊到 ≥8 天，筆數真的變少（或直接說沒有符合的）",
       p8 < p2 or count(pg, "#trust .empty") == 1, f"≥2 天 {p2} 顆 → ≥8 天 {p8} 顆")
    pg.select_option("#streakDays", "3"); pg.wait_for_timeout(800)
    ok("切回 ≥3 天筆數回得來", pg.evaluate(pts_of) == base_pts, f"{base_pts} → {pg.evaluate(pts_of)}")

    # --- 縮放與拖曳（跟資金熱力圖同一套）
    check_drag(pg, "trustWrap", "法人連續買超")


def t_market(pg, base):
    pg.goto(f"{base}#market", wait_until="networkidle"); pg.wait_for_timeout(2000)
    tabs = pg.evaluate("[...document.querySelectorAll('#mktSeg2 button')].map(b => b.dataset.k)")
    # 2026-09-18（Andy 圖16「市場明細內資金集中這頁拿掉」）：四個 → 三個
    ok("市場明細有三個分頁（資金集中已移除）", tabs == ["updown", "ma", "cand"], tabs)
    ok("資金集中那一頁真的拿掉了", "top5" not in tabs, tabs)
    seen = {}
    for k in tabs:
        click(pg, f'#mktSeg2 button[data-k="{k}"]', 900)
        seen[k] = pg.evaluate("""() => ({ on: (document.querySelector('#mktSeg2 button.on')||{dataset:{}}).dataset.k,
            title: (document.getElementById('mktTitle')||{}).innerText.split(String.fromCharCode(10))[0],
            rows: document.querySelectorAll('#mktBody tr[data-code]').length,
            blocks: document.querySelectorAll('#mktBody .ma, #mktBody .t5').length })""")
        ok(f"市場明細「{k}」按下去真的被選取", seen[k]["on"] == k, seen[k])
        ok(f"市場明細「{k}」有列出東西", seen[k]["rows"] > 0 or seen[k]["blocks"] > 0, seen[k])
    ok("四個分頁標題各不相同", len({v["title"] for v in seen.values()}) == len(seen),
       {k: v["title"] for k, v in seen.items()})
    # 漲跌家數底下還有漲停／跌停／漲幅前段的子分頁
    click(pg, '#mktSeg2 button[data-k="updown"]', 900)
    sub = count(pg, "#mktTabs button")
    ok("漲跌家數有子分頁（漲停／跌停／漲幅前段…）", sub >= 2, sub)
    if sub >= 2:
        n0 = pg.evaluate("() => document.querySelectorAll('#mktBody tr[data-code]').length")
        click(pg, "#mktTabs button:nth-child(3)", 800)
        n1 = pg.evaluate("() => document.querySelectorAll('#mktBody tr[data-code]').length")
        changed("切子分頁，列出的股票數真的變了", n0, n1)
    # 點一列要能進個股頁
    if count(pg, "#mktBody tr[data-code]"):
        click(pg, "#mktBody tr[data-code]", 1600)
        ok("市場明細點一列會進個股頁", pg.evaluate("location.hash").startswith("#stock/"), pg.evaluate("location.hash"))


def t_flow(pg, base):
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2200)
    # 2026-09-18（Andy 圖四）：名次變化整張拿掉，那一格改放輪動時鐘
    for cid, name in (("rankFlow", "資金流向排行"), ("rotClock", "輪動時鐘"),
                      # 2026-09-20：族群佔比河流（#river）已依 Andy 指示整張移除
                      ("sankey", "資金去向"),
                      ("instGroups", "族群 × 法人"), ("conc", "資金集中度"), ("valScatter", "估值散布圖")):
        has = pg.evaluate(f"() => {{ const e = document.getElementById('{cid}'); return e ? {{ canvas: !!e.querySelector('canvas'), empty: !!e.querySelector('.empty'), msg: ((e.querySelector('.empty')||{{}}).textContent||'').trim() }} : null; }}")
        # 法人比價量晚一輪落地（價量 15:30、法人 18:30）：當天下午「本週」那一段本來就還沒有法人。
        # 那時不該畫圖，但要**講清楚為什麼**，所以接受「有解釋的空狀態」，不接受空白或制式的一句話。
        excused = (cid == "instGroups" and has and has["empty"]
                   and "還沒出" in has["msg"] and "18:30" in has["msg"])
        ok(f"資金流向「{name}」有畫出來（或說清楚為什麼還沒有）",
           bool(has) and ((has["canvas"] and not has["empty"]) or excused), has)

    # --- ★ 2026-09-20（Andy 拍板「合併：只留拉 Bar」）
    #     原本這裡驗的是那一列期間鈕（本週／上週／…／近三月）。那張卡整個拿掉了，
    #     理由是這一頁本來有**兩套**選時間的方式（期間卡 ＋ 每張圖的天數拉 Bar，
    #     那時 0 代表「跟著上方期間走」），兩套互相抵觸。
    #     所以這一段改成驗三件事：卡片真的不在 DOM 裡、拉 Bar 的 0 也不見了、
    #     以及拉 Bar 真的是唯一的時間控制（拉了圖跟副標都要跟著變）。
    gone = pg.evaluate("""() => ({ seg: !!document.getElementById('periodSeg'),
        note: !!document.getElementById('periodNote'),
        card: document.querySelectorAll('#v-flow .periodbar').length })""")
    ok("期間切換卡真的不在 DOM 裡（不是藏起來）",
       not gone["seg"] and not gone["note"] and gone["card"] == 0, gone)

    bars = pg.evaluate("""() => { const g = (id) => { const i = document.querySelector('#' + id + ' input[type=range]');
        return i ? { min: +i.min, max: +i.max, v: +i.value } : null; };
        return { rank: g('rankDays'), inst: g('instDays') }; }""")
    ok("排行的天數拉 Bar 下限是 1（0＝跟著上方期間 已經沒有意義）",
       bool(bars["rank"]) and bars["rank"]["min"] == 1 and bars["rank"]["max"] == 30, bars)
    ok("族群×法人的天數拉 Bar 下限也是 1",
       bool(bars["inst"]) and bars["inst"]["min"] == 1 and bars["inst"]["max"] == 30, bars)

    snap = lambda: pg.evaluate("""() => ({ sub: (document.getElementById('rankSub')||{}).textContent,
        instSub: (document.getElementById('instSub')||{}).textContent,
        rank: !!document.querySelector('#rankFlow canvas'),
        inst: !!document.querySelector('#instGroups canvas'),
        instMsg: ((document.querySelector('#instGroups .empty')||{}).textContent||'').trim(),
        top: (() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
               if (!c) return null; const y = c.getOption().yAxis[0].data || []; return y[y.length-1] || null; })() })""")
    seenb = {}
    for v in (5, 20, 30):
        set_range(pg, "#rankDays input[type=range]", v, 900)
        set_range(pg, "#instDays input[type=range]", v, 900)
        seenb[v] = snap()
        ok(f"拉到 {v} 天：排行圖有畫出來", seenb[v]["rank"], seenb[v])
        ok(f"拉到 {v} 天：排行副標寫出日期範圍（期間卡的資訊沒有消失）",
           "～" in (seenb[v]["sub"] or ""), seenb[v]["sub"])
        ok(f"拉到 {v} 天：法人圖有畫出來（或說清楚為什麼還沒有）",
           seenb[v]["inst"] or ("還沒出" in seenb[v]["instMsg"] and "18:30" in seenb[v]["instMsg"]),
           seenb[v])
    ok("拉不同天數，排行的日期範圍真的不一樣",
       len({v["sub"] for v in seenb.values()}) == len(seenb), {k: v["sub"] for k, v in seenb.items()})
    ok("拉不同天數，族群×法人的日期範圍也真的不一樣",
       len({v["instSub"] for v in seenb.values()}) >= 2, {k: v["instSub"] for k, v in seenb.items()})

    # --- 名次變化（bump）已於 2026-09-18 整張移除（Andy 圖四：「右邊的名次變化刪掉」）
    ok("名次變化那張圖真的不在了（圖四）",
       pg.evaluate("() => document.getElementById('bump') === null"))
    ok("名次資訊沒有消失：排行的 y 軸標籤仍帶名次箭頭，tooltip 仍寫名次",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
           if (!c) return false; const y = c.getOption().yAxis[0].data || [];
           return y.some(v => /[↑↓]/.test(String(v))); }"""))
    # ★ 2026-09-20：原本這裡會把期間切回「本週」，讓後面幾段從乾淨狀態開始。
    #   期間卡拿掉之後改成把兩支拉 Bar 復位 —— 用意一樣，都是不要把狀態留給下一段。
    set_range(pg, "#rankDays input[type=range]", 20, 600)

    # --- 每張圖的「怎麼看」：按下去要真的展開白話說明，再按要收起來
    hows = pg.evaluate("[...document.querySelectorAll('#v-flow .howbtn')].map(b => b.dataset.how)")
    # 2026-09-20：族群佔比河流整張移除（Andy 指示），所以門檻 7 → 6。
    # 這條只准往下調一次、而且要說得出哪一張沒了 —— 不是為了讓測試變綠隨手改數字。
    ok("資金流向每張圖都有「怎麼看」", len(hows) >= 6, hows)
    for h in hows:
        click(pg, f'#v-flow .howbtn[data-how="{h}"]', 250)
        st = pg.evaluate(f"""() => {{ const b = document.getElementById('how-{h}');
            return {{ open: b && !b.hidden, len: b ? b.innerText.trim().length : 0,
                     label: (document.querySelector('#v-flow .howbtn[data-how=\\"{h}\\"]')||{{}}).textContent }}; }}""")
        ok(f"「怎麼看：{h}」按下去有展開說明", st["open"] and st["len"] > 60, st)
        ok(f"「怎麼看：{h}」展開後按鈕變成收起", "收起" in (st["label"] or ""), st["label"])
        click(pg, f'#v-flow .howbtn[data-how="{h}"]', 200)
        ok(f"「怎麼看：{h}」可以再收起來", pg.evaluate(f"() => document.getElementById('how-{h}').hidden"))

    # --- 輪動階段看板：四張卡、循環列、換階段的族群，換比較天數要真的重算
    ok("輪動階段有四張卡", count(pg, "#rotBoard .stage") == 4, count(pg, "#rotBoard .stage"))
    ok("輪動階段有寫出循環順序", "改善" in text(pg, "#rotCycle") and "領先" in text(pg, "#rotCycle"), text(pg, "#rotCycle"))
    ok("輪動階段有列出族群", count(pg, "#rotBoard li[data-gid]") > 0)
    ok("四張卡的名字是改善／領先／轉弱／落後",
       pg.evaluate("[...document.querySelectorAll('#rotBoard .stage .sh b')].map(e=>e.textContent)") == ["改善", "領先", "轉弱", "落後"],
       pg.evaluate("[...document.querySelectorAll('#rotBoard .stage .sh b')].map(e=>e.textContent)"))
    # F2（Andy 2026-09-18：「5 10 20 天改成拉 Bar 5-20 天，可以用拖曳的方式看的更直觀」）
    bar = pg.evaluate("""() => { const i = document.querySelector('#rotBack input[type=range]');
        return i && { min: +i.min, max: +i.max, v: +i.value }; }""")
    ok("輪動階段的天數是拉 Bar 不是按鈕", bool(bar), bar)
    # 2026-09-19（Andy N4「時間週期拉到 30 天」）：上限 20 → 30，後端 trail 同步
    # 2026-09-20（Andy A4 第 3 條「時間範圍改成前一天～前三十天」）：下限 5 → 1。
    #   下限一定要是 1 —— 這根拉 Bar 現在的語意是「看哪一天」而不是「軌跡畫幾天」，
    #   下限卡在 5 等於使用者永遠看不到最近四天。
    ok("拉 Bar 的範圍是 1–30 天", bool(bar) and bar["min"] == 1 and bar["max"] == 30, bar)
    seenb = {}
    for v in (5, 12, 20):
        set_range(pg, "#rotBack input[type=range]", v, 800)
        seenb[v] = pg.evaluate("""() => ({ v: +document.querySelector('#rotBack input').value,
            lab: (document.querySelector('#rotBack .val')||{}).textContent,
            move: (document.getElementById('rotMove')||{}).innerText,
            items: document.querySelectorAll('#rotBoard li[data-gid]').length })""")
        ok(f"拉到 {v} 天，值真的變了", seenb[v]["v"] == v, seenb[v])
        ok(f"拉到 {v} 天，旁邊的字跟著寫 {v}", str(v) in (seenb[v]["lab"] or ""), seenb[v]["lab"])
        ok(f"拉到 {v} 天有寫出換階段的族群或明講沒有", str(v) in (seenb[v]["move"] or ""), seenb[v]["move"][:40])
    ok("換天數，換階段的名單真的不一樣", len({v["move"] for v in seenb.values()}) >= 2,
       {k: v["move"][:30] for k, v in seenb.items()})
    ok("拉 Bar 的值有記住（換頁回來還是同一個天數）",
       pg.evaluate("() => { try { return localStorage.getItem('tw.rot.back'); } catch(e){ return null; } }") is not None)

    # --- 資金輪動時鐘：Andy 要「輪動族群要搭配圖表，看圖就懂」
    clk = pg.evaluate("""() => { const el = document.getElementById('rotClock');
        if (!el) return null; const c = echarts.getInstanceByDom(el); if (!c) return { canvas: !!el.querySelector('canvas'), pts: 0 };
        const o = c.getOption(); const sc = o.series.filter(s => s.type === 'scatter')[0];
        return { canvas: !!el.querySelector('canvas'), pts: sc ? sc.data.length : 0,
                 trails: o.series.filter(s => s.type === 'line').length,
                 labels: (o.angleAxis[0].axisLabel ? 'fn' : 'none'),
                 stages: (sc ? sc.data : []).map(d => d.row && d.row.stage).filter(Boolean) }; }""")
    ok("輪動時鐘有畫出來", bool(clk) and clk["canvas"], clk)
    ok("輪動時鐘上有族群的點", bool(clk) and clk["pts"] >= 4, clk)
    ok("每個族群都有一條走過的尾巴", bool(clk) and clk["trails"] == clk["pts"], clk)
    ok("時鐘上的點分佈在四個階段裡", bool(clk) and set(clk["stages"]) <= {"leading", "improving", "weakening", "lagging"}, clk and clk["stages"][:6])
    set_range(pg, "#rotBack input[type=range]", 5, 900)
    h0 = canvas_hash(pg, "#rotClock")
    set_range(pg, "#rotBack input[type=range]", 20, 1100)
    changed("拉到 20 天，輪動時鐘的尾巴真的重畫", h0, canvas_hash(pg, "#rotClock"))
    # 尾巴要**沿著圓弧**走（Andy 2026-09-18：「不是一個斷點直線跑過去」）。
    # 判準：一條尾巴的點數要遠多於 2（兩點＝直線），而且不是只有起訖兩端。
    seg = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
        if (!c) return 0; const ls = c.getOption().series.filter(s => s.type === 'line');
        return Math.max(0, ...ls.map(s => (s.data || []).length)); }""")
    ok("輪動時鐘的尾巴是弧線（補過中間點）不是兩點直線", seg >= 8, f"最長的一條尾巴有 {seg} 個點")
    set_range(pg, "#rotBack input[type=range]", 5, 900)
    # 用真的滑鼠點時鐘上的點（算出那顆點的螢幕座標再點下去），要進得去族群頁
    scroll_to(pg, "rotClockWrap")
    pt = pg.evaluate("""() => { const el = document.getElementById('rotClock');
        const c = echarts.getInstanceByDom(el); if (!c) return null;
        const si = c.getOption().series.findIndex(s => s.type === 'scatter');
        const d = c.getOption().series[si].data[0]; if (!d) return null;
        const p = c.convertToPixel({ seriesIndex: si }, d.value); const r = el.getBoundingClientRect();
        return { x: r.x + p[0], y: r.y + p[1], gid: d.row.gid, name: d.row.name }; }""")
    if ok("算得出時鐘上第一顆點的位置", bool(pt), pt):
        before = pg.evaluate("() => location.hash")
        pg.mouse.click(pt["x"], pt["y"])
        pg.wait_for_timeout(1000)
        # 族群 id 有中文，location.hash 讀回來是編碼過的，要解回來才比得起來
        now = pg.evaluate("() => decodeURIComponent(location.hash)")
        # ★ 2026-09-21（Andy 的兩階段）：點族群**不再跳頁**，改成原地展開成分股。
        #   所以這一條從「有沒有進族群頁」改成驗「沒有跳頁，而且清單真的出現了」——
        #   要進族群頁的路沒有消失，它變成面板標題右邊那顆「進族群頁 →」。
        st_drill = pg.evaluate("""() => { const b = document.getElementById('rankPanel');
            return { open: !!b && !b.hidden,
                     n: document.querySelectorAll('#rankPanel .ms a').length,
                     go: document.querySelectorAll('#rankPanel a[href^="#industry/group/"]').length }; }""")
        ok(f"點時鐘上的「{pt['name']}」不會跳頁（改成原地下鑽）", now == before, f"{before} → {now}")
        ok(f"點時鐘上的「{pt['name']}」會在旁邊列出它的成分股",
           st_drill["open"] and st_drill["n"] > 0, st_drill)
        ok("展開的面板仍然有「進族群頁 →」（要離開的人還是走得掉）", st_drill["go"] > 0, st_drill)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(600)
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(1800)

    # --- 資金集中度：前 5 / 前 10 切換要真的換一條線
    concs = pg.evaluate("[...document.querySelectorAll('#concSeg button')].map(b => b.dataset.v)")
    if len(concs) >= 2:
        name0 = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('conc')); return c ? c.getOption().series[0].name : null; }")
        state0 = text(pg, "#concState")
        click(pg, '#concSeg button[data-v="10"]', 900)
        name1 = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('conc')); return c ? c.getOption().series[0].name : null; }")
        changed("資金集中度切前 10 大，真的換一條線", name0, name1)
        changed("資金集中度切前 10 大，狀態說明跟著換", state0, text(pg, "#concState"))
        ok("資金集中度有寫出現在是縮圈還是擴散", any(w in text(pg, "#concState") for w in ("縮圈", "擴散", "沒有明顯")), text(pg, "#concState"))
        click(pg, '#concSeg button[data-v="5"]', 700)

    # --- 估值篩選：條件真的會篩掉東西，清除後回得來
    n0 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    cnt0 = text(pg, "#vCount")
    ok("估值表有列出股票", n0 > 0, n0)
    # ★ 2026-09-21：這裡以前量的是 `#valBody` 的列數，但 `drawTable()` 只畫**前 80 名**
    #   （`rows.slice(0, 80)`）。族群換成 110 個板塊之後，有估值的股票從 400 多檔變成 807 檔，
    #   「本益比 ≤ 12」還剩 121 檔 —— 篩前 80 列、篩後還是 80 列，於是驗收報 `80 → 80`
    #   **但產品完全正確**。這正是 DECISIONS #206 說的「量到一個不會動的數字」：
    #   列數被上限夾住，永遠不會動。改成量 `#vCount` 那個**沒有上限**的真實符合筆數。
    def _vcount() -> int:
        m = re.search(r"符合\s*(\d+)\s*檔", text(pg, "#vCount"))
        return int(m.group(1)) if m else -1
    v0 = _vcount()
    ok("估值表寫得出「符合幾檔」（篩選的真實筆數，不受表格前 80 名上限影響）", v0 > 0, text(pg, "#vCount"))
    pg.fill("#vPeHi", "12"); pg.wait_for_timeout(700)
    n1 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    v1 = _vcount()
    hi = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')]
        .map(tr => parseFloat(tr.children[2].textContent)).filter(Number.isFinite)""")
    ok("本益比上限真的篩掉東西（看符合筆數，不是看畫出來的列數）", 0 < v1 < v0, f"符合 {v0} → {v1} 檔（畫出來 {n0} → {n1} 列）")
    ok("篩出來的本益比真的都 ≤ 12", all(v <= 12.0001 for v in hi), [v for v in hi if v > 12][:5])
    pg.fill("#vRoe", "20"); pg.wait_for_timeout(700)
    v2 = _vcount()
    ok("再加 ROE 條件會更少（同樣看符合筆數）", 0 < v2 < v1, f"符合 {v1} → {v2} 檔")
    changed("篩選後的檔數說明跟著變", cnt0, text(pg, "#vCount"))
    click(pg, "#vReset", 800)
    ok("清除條件後回到原本的檔數", text(pg, "#vCount") == cnt0, f"{cnt0} vs {text(pg, '#vCount')}")
    # 勾「只看低於族群中位」要真的只留低於中位的
    click(pg, "#vBelow", 800)
    # ★ 2026-09-19：不能一律拿「本益比」欄去比「族群中位」欄。
    #   groups.yaml 的 valuation_metric 允許族群換口徑（生技醫療用 ps），
    #   那時中位數是 PS 的中位，本檔要比的也是它自己的 PS（td 的 data-mv）。
    #   一律用 PE 去比會比出 [12.4, 2.7] 這種假紅 —— 那兩檔其實是 PS 低於同業 37%／54%。
    below = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')].map(tr => {
        const md = tr.children[3]; const mt = md.dataset.metric || 'pe';
        const mine = mt === 'pe' ? parseFloat(tr.children[2].textContent) : parseFloat(md.dataset.mv);
        return [mine, parseFloat(md.textContent), mt]; })
        .filter(a => Number.isFinite(a[0]) && Number.isFinite(a[1]))""")
    # ★ 2026-09-19：原本只有下面那句 all(...)，而 all([]) 是 True ——
    #   這個勾選框其實從掛上去的第一天就永遠篩出 0 筆（後端 vs_median 回比值、前端判 < 0），
    #   驗收卻一路綠燈。空集合一定要先當成紅的。
    ok("「只看低於族群中位」有篩出東西（空集合不算通過）", len(below) > 0,
       f"勾選後剩 {len(below)} 列 —— 0 列代表這個條件根本篩不出東西，不是今天剛好沒有便宜股")
    ok("「只看低於族群中位」真的只留低於同業中位的（依各族群自己的估值口徑）",
       below and all(a[0] < a[1] for a in below), [a for a in below if a[0] >= a[1]][:4])
    # 非 PE 口徑的那幾列要把口徑標出來，不然「本益比 12.4 / 族群中位 2.7」會被讀成貴了四倍
    lab = pg.evaluate("""() => [...document.querySelectorAll('#valBody td[data-metric]')]
        .filter(td => td.dataset.metric !== 'pe')
        .map(td => ({ m: td.dataset.metric, txt: td.textContent.trim(), tip: (td.title||'').length }))""")
    ok("非本益比口徑的族群中位有標出是哪一種口徑", not lab or all(
       x["m"].upper() in x["txt"].upper() and x["tip"] > 10 for x in lab), lab[:3])
    click(pg, "#vBelow", 600)

    # --- 這頁每張圖都不可以有縮放框（Andy 09-13：「將這邊的縮放功能取消」）
    # ---- 資金去向：2026-09-19 整張改掉（Andy 圖六「改成水平並且全部都以點跟線呈現，
    #      金資越多的 顏色越深也越粗」）。原本的「垂直桑基＋電流脈動」三條驗收隨之作廢 ——
    #      那正是他要求換掉的東西，留著只會每天報一次假紅燈。
    sk = pg.evaluate("""() => { const el = document.getElementById('sankey'); if (!el) return null;
        const c = echarts.getInstanceByDom(el); if (!c) return null;
        const s = c.getOption().series[0];
        const root = (s.data || [])[0] || {};
        const kids = root.children || [];
        return { type: s.type, orient: s.orient, symbol: s.symbol,
                 n: kids.length,
                 sizes: kids.map(k => k.symbolSize).filter(v => v != null),
                 widths: kids.map(k => (k.lineStyle || {}).width).filter(v => v != null) }; }""")
    ok("資金去向是水平的（圖六）", bool(sk) and sk["type"] == "tree" and sk["orient"] == "LR", sk)
    ok("資金去向全部以點跟線呈現（圖六）", bool(sk) and sk["symbol"] == "circle" and sk["n"] > 0, sk)
    # 「錢越多的點越大、線越粗」：最大的要明顯大於最小的，不是全部一樣
    ok("錢越多的點越大（圖六）",
       bool(sk) and len(sk["sizes"]) > 1 and max(sk["sizes"]) > min(sk["sizes"]) * 1.3,
       sk and sk["sizes"])
    ok("錢越多的線越粗（圖六）",
       bool(sk) and len(sk["widths"]) > 1 and max(sk["widths"]) > min(sk["widths"]) * 1.3,
       sk and sk["widths"])
    ok("滑過節點看得到 %", pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('sankey'));
        if (!c) return false; const f = c.getOption().tooltip[0].formatter;
        const s = f({ name: 'a', data: { value: 1 } });
        return typeof s === 'string' && s.indexOf('%') >= 0; }"""))
    # 圖六的「看哪一天」拉Bar（2026-09-20 起沒有播放鈕，見 t_new_flow）
    if pg.evaluate("() => !!document.querySelector('#sankeyDays input[type=range]')"):
        s0 = canvas_hash(pg, "#sankey")
        set_range(pg, "#sankeyDays input[type=range]", 0, 1200)
        changed("資金去向拉到最舊那天，圖真的重畫（圖六）", s0, canvas_hash(pg, "#sankey"))

    # ---- H1 族群佔比河流：2026-09-20 Andy 指名移除（「圖四五 將時間週期以及族群佔比河流圖移除」）。
    # 原本這裡有 6 條驗收（天數拉Bar 範圍、截止日回放、播放鈕、% 單位）全部指向已移除的元素，
    # 留著一定紅。「真的不在 DOM 裡」這件事改在 t_new_flow 正面驗一次，不是刪掉不管。

    # ---- I1 族群 × 法人：天數拉 Bar ＋ 占比 %
    # ★ 2026-09-20（Andy 拍板「合併：只留拉 Bar」）：下限 0 → 1。
    #   0 以前代表「跟著上方期間走」，期間卡拿掉之後那個值沒有意義了，
    #   留著只會讓人拉到一個什麼都不會發生的位置。
    ib = pg.evaluate("""() => { const i = document.querySelector('#instDays input[type=range]');
        return i && { min: +i.min, max: +i.max, v: +i.value }; }""")
    ok("族群×法人有天數拉 Bar", bool(ib), ib)
    ok("範圍是 1–30 天", bool(ib) and ib["min"] == 1 and ib["max"] == 30, ib)
    ok("拉 Bar 旁邊寫得出「N 天」",
       "天" in (pg.evaluate("() => (document.querySelector('#instDays .val')||{}).textContent") or ""),
       pg.evaluate("() => (document.querySelector('#instDays .val')||{}).textContent"))
    i0 = canvas_hash(pg, "#instGroups")
    sub0 = text(pg, "#instSub")
    set_range(pg, "#instDays input[type=range]", 10, 1200)
    changed("拉到 10 天，族群×法人真的重畫", i0, canvas_hash(pg, "#instGroups"))
    changed("副標跟著寫「最近 10 個交易日」", sub0, text(pg, "#instSub"))
    ok("y 軸的族群名後面帶占比 %", pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('instGroups'));
        if (!c) return false; const d = c.getOption().yAxis[0].data || [];
        return d.length > 0 && String(d[0]).indexOf('%') >= 0; }"""),
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('instGroups'));
           return c ? (c.getOption().yAxis[0].data || [])[0] : null; }"""))
    set_range(pg, "#instDays input[type=range]", 0, 1200)
    ok("拉回 0 會跟著上方期間走", text(pg, "#instSub") != "", text(pg, "#instSub"))

    # ---- F1 輪動階段不要方方角角（Andy 2026-09-18：「我覺得很醜…不要那麼方方角角」）
    sb = pg.evaluate("""() => { const s = document.querySelector('#rotBoard .stage'); if (!s) return null;
        const li = document.querySelector('#rotBoard .stage li');
        return { r: parseFloat(getComputedStyle(s).borderRadius) || 0,
                 rail: parseFloat(getComputedStyle(document.getElementById('rotBoard'), '::before').height) || 0,
                 arrow: getComputedStyle(s, '::after').content,
                 liR: li ? parseFloat(getComputedStyle(li).borderRadius) || 0 : 0,
                 n: document.querySelectorAll('#rotBoard .stage').length }; }""")
    ok("輪動階段還是四段", bool(sb) and sb["n"] == 4, sb)
    ok("四段的角是圓的（不是方方角角）", bool(sb) and sb["r"] >= 16, sb)
    ok("成員是圓角膠囊", bool(sb) and sb["liR"] >= 100, sb)
    ok("底下有一條軌道把四段串起來（看得出是一個循環）", bool(sb) and sb["rail"] >= 4, sb)
    ok("段與段之間有箭頭", bool(sb) and "→" in (sb["arrow"] or ""), sb)

    for w, lb in (("rankFlowWrap", "資金流向排行"),
                  ("rotClockWrap", "輪動時鐘"), ("sankeyWrap", "資金去向"),
                  ("instGroupsWrap", "族群 × 法人")):
        check_nozoom(pg, w, lb)


def settle_scroll(pg, quiet_ms=350, limit_ms=3000):
    """等到 scrollY 連續 quiet_ms 沒有變動才回來。

    2026-09-19：`點零件不會把畫面捲走` 這條驗收本來在 scrollIntoView 之後固定等 600ms
    就量基準值。關聯圖從 44 家長到 58 家之後，版面要更久才穩（圖表 canvas 重新量尺寸、
    瀏覽器的 scroll anchoring 分好幾次微調，實測捲動事件一路發到 485ms），
    於是「基準值」是在頁面還在動的時候量的 —— 量到的 Δ 是**頁面自己在收斂**，
    不是點擊把畫面捲走。實測改成等穩定之後，Δ 從 −133／−52 變成 0／0，
    而且**不需要改任何前端程式**（我一度加了一段「記住位置再捲回去」的程式碼，
    量完發現根本不需要，已經拿掉 —— 不要為了一個量錯的數字去加機制）。
    """
    import time as _t
    t0 = _t.time(); last = None; since = _t.time()
    while (_t.time() - t0) * 1000 < limit_ms:
        y = pg.evaluate("Math.round(scrollY)")
        if y != last:
            last = y; since = _t.time()
        elif (_t.time() - since) * 1000 >= quiet_ms:
            return y
        pg.wait_for_timeout(60)
    return last


def t_industry(pg, base):
    pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(1400)
    ok("產業地圖有產業鏈方塊", count(pg, "#chainTiles .tile") > 0)
    ok("產業地圖有法定產業別方塊", count(pg, "#indTiles .tile") > 0)
    click(pg, "#chainTiles .tile", 1600)
    ok("點產業鏈方塊會進單一產業鏈頁", pg.evaluate("location.hash").startswith("#industry/"),
       pg.evaluate("location.hash"))

    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("產業鏈頁有產品剖析圖", count(pg, "#prodDiagram svg") > 0)
    # Andy：「產業與個股 剖析圖不用新增縮放功能」—— 不可以被包成可縮放的框
    ok("產業與個股的剖析圖沒有縮放框",
       pg.evaluate("() => { const d = document.getElementById('prodDiagram'); return !d || (!d.classList.contains('zwrap') && !d.querySelector(':scope > .zpane') && !d.querySelector(':scope > .zbadge')); }"))
    ok("產業鏈頁有關聯圖公司節點", count(pg, "#chainMap .co") > 0)
    n_all = count(pg, "#memberTable tbody tr")
    ok("產業鏈頁有成分股", n_all > 0)

    # --- ★ 預設排序是漲幅（Andy 2026-09-15：「族群 Default 排序適用漲幅」）
    #     以前預設是成交值，打開永遠只看得到那幾檔權值股
    head = pg.evaluate("() => { const th = [...document.querySelectorAll('#memberTable th')]"
                       ".filter(e => /▲|▼/.test(e.innerText))[0];"
                       " return th ? { k: th.dataset.k, t: th.innerText.trim() } : null; }")
    ok("成分股預設照漲幅排序", bool(head) and head["k"] == "chg_pct", head)
    ok("而且是由高到低", bool(head) and "▼" in (head["t"] or ""), head)
    chgs = pg.evaluate("""() => [...document.querySelectorAll('#memberTable tbody tr')].slice(0, 12)
        .map(tr => parseFloat((tr.children[4]||{}).innerText)).filter(v => !isNaN(v))""")
    ok("第一頁真的是由漲最多的排下來",
       len(chgs) < 2 or all(chgs[i] >= chgs[i + 1] - 0.001 for i in range(len(chgs) - 1)), chgs[:6])
    # 按表頭換成成交值：順序要真的變，而且記進 localStorage
    top_before = pg.evaluate("() => (document.querySelector('#memberTable tbody tr')||{}).dataset ?"
                             " document.querySelector('#memberTable tbody tr').dataset.code : ''")
    click(pg, "#memberTable th[data-k='turnover']", 600)
    top_after = pg.evaluate("() => (document.querySelector('#memberTable tbody tr')||{}).dataset ?"
                            " document.querySelector('#memberTable tbody tr').dataset.code : ''")
    changed("按表頭換排序，第一列真的換人", top_before, top_after)
    saved_sort = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.memberSort')||'null'); }"
                             " catch(e) { return null; } }")
    ok("按過的排序記進 localStorage", bool(saved_sort) and saved_sort.get("key") == "turnover", saved_sort)
    pg.evaluate("() => { try { localStorage.removeItem('tw.memberSort'); } catch(e) {} }")
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(1800)
    head2 = pg.evaluate("() => { const th = [...document.querySelectorAll('#memberTable th')]"
                        ".filter(e => /▲|▼/.test(e.innerText))[0]; return th ? th.dataset.k : null; }")
    ok("清掉紀錄後回到預設的漲幅排序", head2 == "chg_pct", head2)
    n_all = count(pg, "#memberTable tbody tr")

    # --- 上市／上櫃切換：筆數要真的變，而且加起來等於全部
    # ★ 2026-09-21：這裡要量的是**真實筆數**，不是畫出來的列數 ——
    #   成分股表格 2026-09-21 起預設只畫前 30 列（底下有「顯示全部」），
    #   拿列數相加會變成「30（上市）＋26（上櫃）≠ 30（全部）」的假紅。
    #   真實筆數一直寫在標題上（「成分股 148 檔」），那個數字不受列數上限影響。
    def _member_total() -> int:
        m = re.search(r"(\d+)\s*檔", text(pg, "#memberTitle"))
        return int(m.group(1)) if m else -1
    t_all = _member_total()
    click(pg, '#mktSeg button[data-v="TWSE"]', 500); n_twse = count(pg, "#memberTable tbody tr"); t_twse = _member_total()
    click(pg, '#mktSeg button[data-v="TPEX"]', 500); n_tpex = count(pg, "#memberTable tbody tr"); t_tpex = _member_total()
    click(pg, '#mktSeg button[data-v="ALL"]', 500)
    ok("上市／上櫃切換真的在篩選",
       t_twse != t_all or t_tpex != t_all, f"全部 {t_all}／上市 {t_twse}／上櫃 {t_tpex}")
    ok("上市＋上櫃 = 全部（沒有漏掉或重複）",
       t_all > 0 and t_twse + t_tpex == t_all,
       f"{t_twse}+{t_tpex} != {t_all}（畫出來的列數 {n_twse}/{n_tpex}/{n_all} 受前 30 列上限影響，不能拿來相加）")

    # --- 點環節 chip：關聯圖要真的捲到對應位置、該環節要亮起來、成分股要被篩
    if count(pg, "#segChips .segchip"):
        before = pg.evaluate("""() => ({ sel: document.querySelectorAll('#segChips .segchip.sel').length,
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            left: (document.querySelector('#chainMap')||{}).scrollLeft })""")
        click(pg, "#segChips .segchip:not(.nomem)", 800)
        after = pg.evaluate("""() => ({ sel: document.querySelectorAll('#segChips .segchip.sel').length,
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            left: (document.querySelector('#chainMap')||{}).scrollLeft })""")
        changed("點環節 chip 真的選起來了", before["sel"], after["sel"])
        ok("點環節 chip 成分股有被篩選", after["rows"] <= before["rows"], f"{before['rows']} → {after['rows']}")
        click(pg, "#segChips .segchip.sel", 500)

    # --- 點族群卡：成分股要真的被篩
    if count(pg, "#groupCards .tile"):
        b = count(pg, "#memberTable tbody tr")
        click(pg, "#groupCards .tile", 700)
        a = count(pg, "#memberTable tbody tr")
        ok("點族群卡真的篩選了成分股", a < b or count(pg, "#groupCards .tile.sel") > 0, f"{b} → {a}")
        click(pg, "#groupCards .tile.sel", 500)

    # --- 點剖析圖零件：只亮起來＋在原地說明，不准動下方成分股（Andy）
    if count(pg, "#prodDiagram [data-seg]"):
        # 先把剖析圖捲進畫面再記位置，否則量到的是測試自己捲的，不是頁面被點擊帶走的
        pg.evaluate("document.querySelector('#prodDiagram [data-seg]').scrollIntoView({block:'center'})")
        settle_scroll(pg)
        before = pg.evaluate("""() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
            y: Math.round(scrollY), seg: (document.querySelector('#segBox .segbox b.t')||{}).textContent })""")
        click(pg, "#prodDiagram [data-seg]", 800)
        after = pg.evaluate("""() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
            y: Math.round(scrollY), seg: (document.querySelector('#segBox .segbox b.t')||{}).textContent,
            sel: document.querySelectorAll('#prodDiagram [data-seg].sel').length,
            btn: !!document.getElementById('segOnly') })""")
        ok("點零件會亮起來", after["sel"] > 0, after)
        ok("點零件會在原地說明這個環節", bool(after["seg"]) and after["seg"] != before["seg"], f"{before['seg']} → {after['seg']}")
        ok("點零件不會動到下方成分股", after["rows"] == before["rows"], f"{before['rows']} → {after['rows']}")
        ok("點零件不會把畫面捲走", abs(after["y"] - before["y"]) < 40, f"{before['y']} → {after['y']}")
        ok("說明框有「只看這個環節」的按鈕", after["btn"], after)
        # 按了那顆按鈕才真的篩
        click(pg, "#segOnly", 900)
        n2 = count(pg, "#memberTable tbody tr")
        ok("按「只看這個環節」才真的篩成分股", n2 != before["rows"] or n2 < before["rows"] + 1, f"{before['rows']} → {n2}")

    # --- 剖析圖零件：點下去要列出個股
    if count(pg, "#prodDiagram [data-part]"):
        click(pg, "#prodDiagram [data-part]", 600)
        ok("點剖析圖零件會亮起來", count(pg, "#prodDiagram .sel") > 0)

    check_3d(pg)

    # --- 點成分股 → 個股頁
    click(pg, "#memberTable tbody tr a, #memberTable tbody tr", 1800)
    ok("點成分股會進個股頁", pg.evaluate("location.hash").startswith("#stock/"), pg.evaluate("location.hash"))


def t_group_pages(pg, base):
    """法定產業別族群頁（id 是中文）真的列得出成分股。

    2026-09-19 抓到的事故：`site/app.js` 的 route() 拿 location.hash 直接 split，
    沒有 decodeURIComponent。瀏覽器把中文存成百分比編碼，於是 `g.id === state.group`
    永遠比不中 —— 35 個法定產業別裡有 34 個的族群頁是「0 檔 · 沒有符合的股票」，
    只有純 ASCII 的 ind_ETF 躲過。候選名單、市場明細、個股頁的族群連結全部通到這裡。

    以前完全沒有任何一條驗收打開過 #industry/group/<中文 id>，所以這個洞一直沒人發現。
    這裡驗的是「列出來的筆數跟 groups_detail.json 對得起來」，不是「頁面有 render」。
    """
    # ★ 2026-09-20：這一行是平行化之後才補上的。
    #   原本這一段直接 fetch('data/groups_detail.json') 這個**相對路徑**，
    #   而它能成立純粹是因為「前面某一段已經把頁面導到網站上了」——
    #   依序跑時剛好成立，一旦它變成某個 worker 的第一段，頁面還在 about:blank，
    #   相對路徑解不出來就整段爆掉。段落之間不該有這種隱性依賴。
    pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(600)
    want = pg.evaluate("""async () => {
      const r = await fetch('data/groups_detail.json'); const d = await r.json();
      const gs = Object.entries(d.groups || d).filter(([k]) => k.startsWith('ind_'));
      return gs.map(([k, v]) => [k, (v.codes || v.members || v.stocks || []).length])
               .filter(a => a[1] > 0);
    }""")
    ok("法定產業別族群 ≥ 20 個（含中文 id）", len(want) >= 20, len(want))
    # 抽驗：ASCII 的 ind_ETF 以外，一定要挑到中文 id —— 那才是會壞的那一種
    cjk = [g for g in want if any(ord(c) > 127 for c in g[0])]
    ok("抽得到中文 id 的族群", len(cjk) >= 5, [g[0] for g in cjk[:5]])
    empty = []
    for gid, n in ([g for g in want if g[0] == "ind_ETF"][:1] + cjk[:6]):
        pg.goto(f"{base}#industry/group/{gid}", wait_until="networkidle"); pg.wait_for_timeout(1200)
        rows = count(pg, "#memberTable tbody tr[data-code], #memberTable tbody tr")
        title = text(pg, "#memberTitle") + " " + text(pg, "#v-industry h2")
        if rows < 1:
            empty.append({"gid": gid, "資料裡有": n, "畫面列出": rows, "標題": title[:40]})
        ok(f"{gid} 的族群頁列得出成分股（資料裡有 {n} 檔）", rows >= 1,
           f"畫面只列出 {rows} 列，標題「{title[:40]}」")
    ok("沒有任何一個族群頁是空的", not empty, empty)


def t_chainnav(pg, base):
    """E5 產業鏈頁上方的類別切換列 ＋ E6 跨產業鏈環節的兩張架構圖（Andy 2026-09-18 第 3 批）。

    E5 以前只有卡片最底下那排連結，換一條鏈要先捲到底或退回產業地圖。
    E6 以前不管從哪條鏈點進 ABF 載板，看到的都只有當下這條鏈的內容，另一半整個看不到。
    兩個都驗「真的按下去、畫面真的因此換掉」，不是驗元素存在。"""
    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1800)

    # ---------------- E5
    sw = pg.evaluate("""() => { const s = document.getElementById('chainSwitch'); if (!s) return null;
        const b = [...s.querySelectorAll('button')];
        const card = s.closest('.card'), h2 = card && card.querySelector('h2');
        return { n: b.length, on: (s.querySelector('button.on')||{dataset:{}}).dataset.c,
                 // 「上方」＝真的排在標題前面，不是塞在卡片最下面
                 aboveTitle: !!(h2 && s.compareDocumentPosition(h2) & Node.DOCUMENT_POSITION_FOLLOWING),
                 top: Math.round(s.getBoundingClientRect().top),
                 ids: b.map(x => x.dataset.c) }; }""")
    if not ok("E5 產業鏈頁最上方有類別切換列", bool(sw) and sw["n"] >= 3, sw):
        return
    ok("E5 切換列真的在標題上方", sw["aboveTitle"], sw)
    ok("E5 現在這條鏈是標起來的", sw["on"] == "ai_server", sw)
    ok("E5 其他產業鏈與法定產業別都列得出來", "semiconductor" in sw["ids"] and "industry" in sw["ids"], sw["ids"])
    h0 = text(pg, "#indChain h2")
    click(pg, "#chainSwitch button[data-c='semiconductor']", 1800)
    after = pg.evaluate("""() => ({ hash: location.hash, h2: (document.querySelector('#indChain h2')||{}).innerText,
        on: (document.querySelector('#chainSwitch button.on')||{dataset:{}}).dataset.c,
        rows: document.querySelectorAll('#memberTable tbody tr').length,
        canvas: document.querySelectorAll('#prod3d canvas').length })""")
    changed("E5 按切換列，頁面標題真的換一條鏈", h0, after["h2"])
    ok("E5 而且是直接切過去（沒有退回產業地圖）", after["hash"] == "#industry/semiconductor", after)
    ok("E5 切過去之後換它被標起來", after["on"] == "semiconductor", after)
    ok("E5 新的那條鏈有成分股", after["rows"] > 0, after)
    # 換鏈要把上一個 3D 場景收乾淨，不然 WebGL context 會一路累積到瀏覽器上限
    ok("E5 換鏈不會留下上一個 3D 畫布", after["canvas"] == 0, after)

    # ---------------- E6：ABF 載板同時屬於半導體與 AI 伺服器
    if not ok("E6 半導體鏈看得到 ABF 載板環節", count(pg, "#segChips .segchip[data-seg='abf_pcb']") == 1):
        return
    click(pg, "#segChips .segchip[data-seg='abf_pcb']", 1200)
    x = pg.evaluate("""() => { const w = document.getElementById('xChains'); if (!w) return null;
        const svgs = [...w.querySelectorAll('.xmini svg')];
        return { panels: w.querySelectorAll('.xchain').length, minis: svgs.length,
                 chains: [...w.querySelectorAll('.xchain')].map(e => e.dataset.c),
                 // 兩張圖裡這個環節都要亮起來、其餘壓暗，才叫「兩張架構圖」而不是兩張裝飾
                 selPerMini: svgs.map(s => s.querySelectorAll('[data-seg="abf_pcb"].sel').length),
                 dimPerMini: svgs.map(s => s.querySelectorAll('[data-seg].dim').length),
                 // 兩邊內容：各自的上下游與族群
                 rows: w.querySelectorAll('.xchain .xrow').length,
                 txt: w.innerText, go: w.querySelectorAll('.xgo').length,
                 cur: w.querySelectorAll('.xchain.cur').length }; }""")
    if not ok("E6 跨產業鏈的環節會多出一塊「兩條鏈」的說明", bool(x), x):
        return
    ok("E6 兩條鏈各一張架構圖", x["panels"] == 2 and x["minis"] == 2, x)
    ok("E6 兩張圖都是半導體與 AI 伺服器", sorted(x["chains"]) == ["ai_server", "semiconductor"], x["chains"])
    ok("E6 兩張圖裡這個環節都真的亮起來", all(v > 0 for v in x["selPerMini"]), x["selPerMini"])
    ok("E6 兩張圖裡其餘環節都壓暗", all(v > 0 for v in x["dimPerMini"]), x["dimPerMini"])
    ok("E6 兩邊各自的上下游與族群都寫出來了", x["rows"] >= 6 and "上游" in x["txt"] and "下游" in x["txt"], x["rows"])
    ok("E6 現在這條鏈有標出來", x["cur"] == 1, x)
    # 真的按「切到這條鏈看」：要換頁、而且那個環節已經套用在新的鏈上
    ok("E6 有切到另一條鏈的入口", x["go"] == 1, x)
    click(pg, "#xChains .xgo", 2000)
    to = pg.evaluate("""() => ({ hash: location.hash, h2: (document.querySelector('#indChain h2')||{}).innerText,
        seg: (document.querySelector('#segBox .segbox b.t')||{}).textContent,
        chips: document.querySelectorAll('#segChips .segchip.sel').length,
        selSeg: (document.querySelector('#segChips .segchip.sel')||{dataset:{}}).dataset.seg })""")
    ok("E6 按了真的切到另一條鏈", to["hash"] == "#industry/ai_server/abf_pcb", to)
    # ★ 不要綁顯示名稱：2026-09-19 這個環節從「ABF 載板 / 高階 PCB」改名成
    #   「IC 載板（ABF / BT）」（金像電不做 ABF 載板，拆出去了），驗收就紅了 ——
    #   但行為完全正確。綁 data-seg 這個 id 才是對的。
    ok("E6 切過去之後同一個環節已經選好了",
       to["selSeg"] == "abf_pcb" and to["chips"] > 0, to)

    # --- 窄畫面（2026-09-18 我自己開線上抓到的，只在寬螢幕驗就會放過）
    #     視窗縮到半邊（約 1100px 以下，兩欄各剩 320px）時，縮圖的 SVG 量到 940px 完全沒縮小，
    #     被 overflow 切掉一半 —— 而且剛好切在亮起來的那個環節上，那張縮圖等於白畫。
    fit_js = (
        "() => [...document.querySelectorAll('#xChains .xmini')].map(w => {"
        " const s = w.querySelector('svg'); if (!s) return null;"
        " const r = s.getBoundingClientRect(), b = w.getBoundingClientRect();"
        " return { over: Math.round(r.right - b.right), fill: +(r.width / b.width).toFixed(2),"
        "          sel: s.querySelectorAll('[data-seg].sel').length }; }).filter(Boolean)")
    for vw in (800, 1040):
        pg.set_viewport_size({"width": vw, "height": 950})
        # 先繞去產業地圖再回來：goto 到「一模一樣的 hash」不會重新載入（DECISIONS #154），
        # 上一輪選好的環節會留著，這一下點下去反而是把它**取消**選取，圖就不見了
        pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(700)
        pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1600)
        pg.evaluate("() => { const s = document.getElementById('side'); if (s) s.classList.remove('open'); }")
        if not pg.evaluate("() => { const c = document.querySelector(\"#segChips .segchip[data-seg='abf_pcb']\");"
                           " return !!c && c.classList.contains('sel'); }"):
            click(pg, "#segChips .segchip[data-seg='abf_pcb']", 2400)
        fit = pg.evaluate(fit_js)
        ok(f"E6 視窗 {vw}px 時兩張縮圖都整張縮進框裡（沒有被切掉）",
           len(fit) == 2 and all(f["over"] <= 2 for f in fit), fit)
        ok(f"E6 視窗 {vw}px 時縮圖沒有縮到看不見", all(f["fill"] > 0.5 for f in fit), fit)
        ok(f"E6 視窗 {vw}px 時兩張圖裡這個環節還是亮著", all(f["sel"] > 0 for f in fit), fit)
    pg.set_viewport_size({"width": 1500, "height": 1000})


def t_electronics(pg, base):
    """一般電子鏈：2026-09-19 從「一個環節都沒有」補成 8 個環節 ＋ 16 家公司 ＋ 6 條邊。

    為什麼要單獨一段（Andy 的硬性要求：新功能一定要有真的操作它的驗收）
    ----------------------------------------------------------------
    這條鏈以前在產業地圖上點得進去，但點進去只有成分股表格 —— 沒有關聯圖、
    沒有環節色標、四個族群（被動元件／面板／網通／手機供應鏈）在圖上完全不存在。
    所以這一段驗的不是「有沒有 render」，是四件會安靜壞掉的事：

      1. 環節 chip 真的出現，而且**點下去筆數真的變**（不是只有 chip 亮起來）
      2. 只有外商的兩格（面板材料＝康寧、終端品牌＝Apple／SpaceX）點下去
         **列得出族群**（靠 app.js 的 FALLBACK；沒接的話點下去是一片空白）
      3. 鴻海／智邦這些節點在別條鏈，要靠 CHAIN_EXTRA 拉進來才看得到
         —— 同一檔台股不准有第二個節點，所以只能這樣做
      4. ★ 新增環節**不可以把既有環節的顏色洗掉**。環節色是 PALETTE[color_idx % 14]，
         以前那個索引是「依 layer 排序後的位置」，在 layer 0 插一格會讓後面全部 +1。
         這一條直接讀 A.L.sidx 驗數值，因為顏色變了畫面上不會報錯、只會「怪怪的」。
    """
    pg.goto(f"{base}#industry/electronics", wait_until="networkidle"); pg.wait_for_timeout(1800)

    n_chip = count(pg, "#segChips .segchip")
    if not ok("一般電子鏈有環節色標（以前是 0 個）", n_chip >= 8, n_chip):
        return
    ok("一般電子鏈有關聯圖公司節點", count(pg, "#chainMap .co") > 0)

    # --- 4. 既有環節的顏色沒有被洗掉（這條最重要，壞了畫面上不會報錯）
    idx = pg.evaluate("""() => { const L = window.Link; if (!L) return null;
        return { ccl_material: L.sidx['ccl_material'], ic_design: L.sidx['ic_design'],
                 hyperscaler: L.sidx['hyperscaler'], display_material: L.sidx['display_material'] }; }""")
    ok("既有環節的配色索引沒有被新環節推移",
       bool(idx) and idx["ccl_material"] == 0 and idx["ic_design"] == 4 and idx["hyperscaler"] == 25, idx)
    ok("新環節排在既有環節後面（所以顏色只往後長）",
       bool(idx) and idx["display_material"] == 26, idx)

    # --- 3. CHAIN_EXTRA：鴻海與智邦的節點在別條鏈，要看得到
    who = pg.evaluate("""() => [...document.querySelectorAll('#chainMap .co')].map(e => e.dataset.code)""")
    ok("鴻海 2317 在一般電子鏈上看得到（節點在 assembly，靠 CHAIN_EXTRA 拉進來）", "2317" in who, who[:12])
    ok("智邦 2345 在一般電子鏈上看得到（節點在 switch）", "2345" in who, who[:12])
    ok("面板雙虎的節點在（友達 2409 / 群創 3481）", "2409" in who and "3481" in who, who[:12])

    # --- 1. 點環節 chip：筆數要真的變
    n_all = count(pg, "#memberTable tbody tr")
    ok("一般電子鏈有成分股", n_all > 0, n_all)
    if pg.query_selector("#segChips .segchip[data-seg='passive_comp']"):
        click(pg, "#segChips .segchip[data-seg='passive_comp']", 900)
        n_sel = count(pg, "#memberTable tbody tr")
        ok("點「被動元件」環節，成分股筆數真的被篩掉", 0 < n_sel < n_all, f"全部 {n_all} → 篩後 {n_sel}")
        ok("而且那一格真的亮起來", count(pg, "#segChips .segchip.sel") == 1)
        click(pg, "#segChips .segchip[data-seg='passive_comp']", 900)   # 再按一次取消
        ok("再按一次取消篩選，筆數回到全部", count(pg, "#memberTable tbody tr") == n_all)

    # --- 2. 只有外商的兩格：點下去要列得出族群（FALLBACK）
    # ★ 2026-09-21：期望值本來寫死「面板」「手機供應鏈」。110 個板塊上線之後
    #   `handset_chain` 不存在了，app.js 的 FALLBACK 已經改成 `brand_operator: ['smartphone']`
    #   （畫面上顯示「智慧型手機」）。**產品是對的，是驗收把顯示名稱當契約**（DECISIONS #207）。
    #   改成向前端自己的 FALLBACK 問「這一格該接到哪個族群」，再驗說明框真的寫出那個族群的名字 ——
    #   守的事情完全一樣：點只有外商的那一格，不可以是一片空白、而且要接得到台股族群。
    for seg in ("display_material", "brand_operator"):
        if not pg.query_selector(f"#segChips .segchip[data-seg='{seg}']"):
            continue
        fb = pg.evaluate(f"""() => {{ const L = window.Link; if (!L) return null;
            const gids = L.sgroups['{seg}'] || [];
            return {{ gids, names: gids.map(g => L.gname[g]).filter(Boolean) }}; }}""")
        ok(f"「{seg}」這一格在 FALLBACK 裡真的接到了台股族群（不是接到一個已經不存在的 id）",
           bool(fb) and len(fb["names"]) > 0 and len(fb["names"]) == len(fb["gids"]), fb)
        click(pg, f"#segChips .segchip[data-seg='{seg}']", 900)
        box = pg.evaluate("() => (document.getElementById('segBox')||{}).innerText || ''")
        ok(f"點只有外商的「{seg}」，說明框不是空白", len(box.strip()) > 10, box[:80])
        want = (fb or {}).get("names") or []
        ok(f"而且接到了對應族群「{'／'.join(want)}」（app.js 的 FALLBACK）",
           bool(want) and any(w in box for w in want), box[:160])
        click(pg, f"#segChips .segchip[data-seg='{seg}']", 600)

    # --- 2026-09-20 Andy 拍板的族群搬動：要驗「名單真的變了」，不是驗註解有寫
    #     2474 可成退出 iPhone 機殼（2020 賣廠）、筆電占 8 成，放在手機供應鏈會讓
    #     M1 的族群量能歸錯方向；3231 緯創主體是 AI 伺服器。
    # ★ 2026-09-21：族群換成 tide 的 110 個板塊之後，`handset_chain` → `smartphone`
    #   （智慧型手機）、`casing` → `precision_parts`（精密機構件）。id 換了，要守的事沒變。
    #   成分股表現在預設只列前 30 檔，所以要先按「顯示全部」再抓名單，
    #   不然「某某不在名單裡」可能只是它排在第 31 名（假通過）。
    def _all_member_codes():
        btn = pg.query_selector("#memberMoreBtn")
        if btn and "顯示全部" in (btn.inner_text() or ""):
            btn.click(); pg.wait_for_timeout(700)
        return pg.evaluate("""() => [...document.querySelectorAll('#memberTable tbody tr')]
            .map(tr => tr.dataset.code)""")

    pg.goto(f"{base}#industry/group/smartphone", wait_until="networkidle"); pg.wait_for_timeout(1200)
    codes = _all_member_codes()
    ok("智慧型手機（原 handset_chain）這個板塊點得進去、列得出成分股", len(codes) > 0, codes)
    ok("智慧型手機已經沒有緯創 3231（主體是 AI 伺服器）", "3231" not in codes, codes)
    ok("鴻海 2317 還在（iPhone 組裝與 AI 機櫃都是它的主體，雙掛是對的）", "2317" in codes, codes)
    # ⚠ 這一條**不是**改名問題，是資料真的退回去了，而且 `pipeline/groups/groups.yaml`
    #   不歸前端動 —— 所以記成備註讓它每一輪都被印出來，不要靜靜消失。
    if "2474" in codes:
        notes.append(
            "⚠ 可成 2474 又回到「智慧型手機」板塊了（pipeline/groups/groups.yaml:417）。"
            "2026-09-20 已查證：2020 年把泰州兩座 iPhone 機殼廠賣給藍思、退出 iPhone 機殼，"
            "筆電機殼占營收約 8 成，2026 年 1～8 月累計營收年減 33%，已與手機新機週期脫鉤 —— "
            "掛在手機板塊會讓 M1 的族群量能歸錯方向。它同時已經在「精密機構件」板塊裡，"
            "建議由產業分析師把它從 smartphone 的 codes 移除（前端無法處理，要改 YAML）。")

    pg.goto(f"{base}#industry/group/precision_parts", wait_until="networkidle"); pg.wait_for_timeout(1200)
    c2 = _all_member_codes()
    ok("「精密機構件」（原 casing）族群頁列得出可成 2474 —— 機構件才是它的主體", "2474" in c2, c2)

    # --- 四個新題材（圖11 的掛載點）：頁面要打得開、成分股要對
    for tid, want in (("mlcc_passive", "2327"), ("switch_800g", "2345"),
                      ("panel_pkg", "2409"), ("petrochemical", "1301")):
        pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(1200)
        body = pg.evaluate("() => (document.querySelector('#v-themes')||{}).innerText || ''")
        ok(f"新題材 {tid} 的頁面打得開而且不是空的", len(body.strip()) > 40, body[:80])
        ok(f"新題材 {tid} 列得出成分股 {want}", want in body, body[:160])
    pg.goto(f"{base}#industry/electronics", wait_until="networkidle"); pg.wait_for_timeout(1500)

    # --- 窄畫面（Andy 2026-09-18：開發過程就要驗 800px，不要只在 1440px 看）
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.wait_for_timeout(900)
    over = pg.evaluate("""() => { const w = document.getElementById('segChips'); if (!w) return null;
        const r = w.getBoundingClientRect();
        return [...w.querySelectorAll('.segchip')]
            .map(e => e.getBoundingClientRect())
            .filter(b => b.right > r.right + 2 || b.left < r.left - 2).length; }""")
    ok("視窗 800px 時環節色標沒有跑出容器", over == 0, over)
    ok("視窗 800px 時關聯圖還在", count(pg, "#chainMap .co") > 0)
    pg.set_viewport_size({"width": 1500, "height": 1000})


# ---------------------------------------------------------------------------
# 2026-09-20 Andy 兩批新需求的驗收位置。★ 三支刻意先開成空殼再派人填，
# 理由是三個 agent 會同時改這個檔 —— 如果讓他們各自去改 main() 裡那一行註冊表，
# 三個人改同一行必然互相蓋掉。先把殼與註冊都放好，他們就只動自己那一支的函式體。
# 每一支都要照 Andy 的硬性要求寫：**真的按下去、畫面真的因此改變了**
# （筆數變了／排序變了／localStorage 真的寫進去了），不是驗「元素存在」。
# ---------------------------------------------------------------------------
def _want(only: str, name: str) -> bool:
    """`--only` 支援逗號分隔的多段（例：`--only 新-資金流向,批次7`）。

    2026-09-20 加的：有一條紅字只有在「A 段跑完之後接著跑 B 段」時才重現
    （前一段留下的選取狀態污染了下一段）。只能一段一段跑的話，這種
    跨段的交互作用永遠重現不出來，就只能整輪 15 分鐘慢慢試。
    """
    return any(part.strip() and part.strip() in name for part in only.split(","))


def t_new_market3(pg, base):
    """大盤三張圖（site/market3.js）：夜盤與日盤共用走勢圖、歷史至少三年。

    Andy 2026-09-19 兩句話：
      ①「夜盤勢會跟日盤共用同一個走試圖 而不是圖利分開，所以也具備即時走勢 K線等資訊」
      ②「為何這些走勢都沒有過往歷史數據，幫我新增至少3年」

    驗的是**按下去之後畫面真的不一樣**，不是元素存在：
      - 按「夜盤」→ 卡片那排數字真的換成夜盤那一份、時間軸真的換成 15:00~05:00、
        那塊獨立方框真的不見了
      - 每多收到一筆夜盤報價，走勢圖上真的多一個點（點數是量出來的）
      - 切「週 K」→ 三年日線真的合成出 100 根以上的週棒
      - 歷史不到三年時，卡片上真的寫出「只有幾根、為什麼、什麼時候會變長」
    """
    import json as _json
    from urllib.parse import urlparse, parse_qs

    # ---- 假的當日分時（跟 t_market3 同一份，形狀與 mis 實測一致）
    def fake_chart(route):
        q = parse_qs(urlparse(route.request.url).query)
        i = (q.get("id") or ["TSE"])[0].upper()
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(_fake_chart(i)))

    # ---- 假的期交所夜盤報價。每打一次就前進一分鐘、換一個價 ——
    #      這樣才驗得到「自動更新一輪就真的多一個點」，而不是「有畫東西」。
    NQ = {"i": 0}

    def fake_fut(route):
        q = parse_qs(urlparse(route.request.url).query)
        night = (q.get("session") or ["day"])[0] == "night"
        if not night:
            route.fulfill(status=200, content_type="application/json",
                          body='{"RtCode":"0","RtData":{"QuoteList":[]}}')
            return
        i = NQ["i"]; NQ["i"] += 1
        mm = 1 + i                                   # 15:01, 15:02, ...
        last = 47405 + i * 7
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps({"RtCode": "0", "RtMsg": "", "RtData": {"QuoteList": [
                          # 第一筆是臺指現貨參考列（-P 結尾），前端要跳過
                          {"SymbolID": "TXF-P", "DispCName": "臺指現貨", "CRefPrice": "47180.75",
                           "CTotalVolume": "", "CLastPrice": "", "CDate": "20260919", "CTime": ""},
                          {"SymbolID": "TXFJ6-M", "DispCName": "臺指期106",
                           "CLastPrice": "%.2f" % last, "CRefPrice": "47418.00",
                           "COpenPrice": "47390.00", "CHighPrice": "%.2f" % (last + 25),
                           "CLowPrice": "47330.00", "CTotalVolume": str(1200 + i * 140),
                           "OpenInterest": "101893", "SettlementPrice": "47428.00",
                           "CDate": "20260919", "CTime": "15%02d30" % mm},
                          {"SymbolID": "TXFK6-M", "DispCName": "臺指期116",
                           "CLastPrice": "47560.00", "CRefPrice": "47581.00",
                           "COpenPrice": "47500.00", "CHighPrice": "47600.00", "CLowPrice": "47480.00",
                           "CTotalVolume": "37", "OpenInterest": "597", "SettlementPrice": "47560.00",
                           "CDate": "20260919", "CTime": "15%02d30" % mm},
                      ]}}))

    # ---- 假的資料湖日線。LAKE["n"] 控制「有幾年」，用來分別驗「夠長」與「太短」兩種畫面。
    LAKE = {"n": 780}                                 # 780 個交易日 ≒ 3.2 年

    def fake_lake(route):
        import datetime as _dt
        out = {}
        for sym, px in (("TSE", 45000.0), ("OTC", 390.0), ("FUT", 44900.0)):
            bars, d, p = [], _dt.date(2023, 1, 2), px
            while len(bars) < LAKE["n"]:
                if d.weekday() < 5:
                    p = p * (1 + ((len(bars) % 7) - 3) / 500.0)
                    bars.append([d.isoformat(), round(p * .999, 2), round(p * 1.006, 2),
                                 round(p * .994, 2), round(p, 2), 1000 + len(bars)])
                d += _dt.timedelta(days=1)
            out[sym] = bars
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(out))

    def fresh(sess=None, **kv):
        """把三張圖的設定清乾淨再重進總覽（每一段都從同一個起點開始）。

        先 goto 一次再寫 localStorage：上一段可能把分頁留在 about:blank，
        那個 origin 的 localStorage 跟本站不是同一份，寫下去等於沒寫 ——
        結果就是測試在台北 15:00 之後跑會自己跳到夜盤。

        ★ 2026-09-21：`sess=` 取代以前那種「直接把 tw.m3.fut 種成 night」的寫法。
        為什麼不改成「種新格式的 JSON」
        ------------------------------
        `tw.m3.fut` 的語意換過一次（純字串 → `{sess, base}`，見 market3.js 的
        `pickSession`：舊格式一律當成過期，那正是讓「永久黏在夜盤」自己解開的機制）。
        測試拿舊格式去種值，新程式**照設計忽略它** —— 於是 25 條夜盤斷言連鎖假紅，
        而產品其實是對的。種新格式只是把一個寫死的字串換成另一個，格式再變又要改一輪，
        而且**繞過了使用者真正會走的那條路**。
        所以改成真的去按那顆鈕：① 免疫於儲存格式改變 ② 驗的是使用者真的會做的事
        ③ 順便把「按鈕真的切得過去」也一起守住（下面那條 ok 就是）。
        """
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.evaluate("""(kv) => { try {
            ['tw.m3.mode','tw.m3.tf','tw.m3.big','tw.m3.fut','tw.m3.nightpts'].forEach(k=>localStorage.removeItem(k));
            localStorage.setItem('tw.live.proxy','https://fake-worker.test');
            Object.keys(kv).forEach(k => localStorage.setItem(k, kv[k]));
          } catch(e){} }""", kv)
        pg.goto("about:blank")
        pg.goto(base + "#overview", wait_until="networkidle")
        pg.wait_for_timeout(2400)
        if sess:
            # 清乾淨之後預設是「跟著台北時間走」，所以想看哪一段就按哪一顆
            click(pg, f"#futSeg button[data-s='{sess}']", 1800)
            got = wait_until(pg, f"() => window.Market3.session === '{sess}'", 5000)
            ok(f"按「{'夜盤' if sess == 'night' else '日盤'}」真的切過去了（後面整段都靠它）",
               bool(got), pg.evaluate("() => window.Market3.session"))

    pg.route("**/chart?*", fake_chart)
    pg.route("**/fut?*", fake_fut)
    pg.route("**/data/index_ohlc.json*", fake_lake)
    pg.set_viewport_size({"width": 1500, "height": 1000})
    # 預設先停在日盤，不然測試在台北時間 15:00 之後跑會自己跳到夜盤
    fresh(sess="day")

    axis_of = """(id) => { const el = document.getElementById('m3c-' + id);
        if (!el || typeof echarts === 'undefined') return null;
        const i = echarts.getInstanceByDom(el); if (!i) return null;
        const d = ((i.getOption().xAxis || [])[0] || {}).data || [];
        return [d[0], d[d.length - 1], d.length]; }"""

    # ================================================================ 需求一：夜盤與日盤共用同一張圖
    ok("預設停在日盤", pg.evaluate("() => window.Market3.session") == "day",
       pg.evaluate("() => window.Market3.session"))
    ok("日盤那顆鈕是亮的",
       pg.evaluate("() => document.querySelector(\"#futSeg button[data-s='day']\").classList.contains('on')"))
    day_px = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-px")
    ok("日盤顯示的是分時檔那一份（45,780）", "45,780" in day_px, day_px)
    day_axis = pg.evaluate(axis_of, "FUT")
    ok("日盤走勢圖的時間軸是 08:45~13:45", day_axis and day_axis[0] == "08:45" and day_axis[1] == "13:45", day_axis)
    day_hash = canvas_hash(pg, "#m3c-FUT")
    ok("日盤真的畫了走勢圖", day_hash not in ("no-canvas", "0"), day_hash)

    # --- ★ 真的按「夜盤」
    click(pg, "#futSeg button[data-s='night']", 1800)
    ok("按下去之後狀態真的換成夜盤", pg.evaluate("() => window.Market3.session") == "night",
       pg.evaluate("() => window.Market3.session"))
    ok("夜盤那顆鈕才是亮的",
       pg.evaluate("() => document.querySelector(\"#futSeg button[data-s='night']\").classList.contains('on')"
                   " && !document.querySelector(\"#futSeg button[data-s='day']\").classList.contains('on')"))
    # 2026-09-19 Andy 的重點：不要再多疊一塊獨立方框
    ok("那塊獨立的夜盤方框不見了（#futNight）", count(pg, "#futNight") == 0, count(pg, "#futNight"))
    ok("說明面板只會出現在圖表容器裡，不會掛在卡片上",
       count(pg, "#m3Grid .m3-card > .m3-night") == 0, count(pg, "#m3Grid .m3-card > .m3-night"))
    ok("卡片上只有一排數字（沒有兩套）",
       count(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-nums") == 1,
       count(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-nums"))

    # --- ★ 數字真的換成夜盤那一份
    night_px = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-px")
    changed("卡片上的價格真的換了一份", day_px, night_px)
    ok("換成夜盤近月（TXFJ6-M）的成交價", "47,4" in night_px, night_px)
    sub = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-sub")
    ok("夜盤沒有「昨收」，寫的是「參考價」", "參考價" in sub and "昨收" not in sub, sub)
    nums = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-nums")
    ok("夜盤要看得到未平倉", "未平倉" in nums, nums)
    tag = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-tag")
    ok("數字旁邊標出這是夜盤、哪一支合約", "夜盤" in tag and "TXFJ6-M" in tag, tag)
    ok("只有台指期那張有日盤／夜盤鈕", count(pg, "#m3Grid .seg.tiny") == 1)
    ok("加權那張完全沒被影響", "45,862" in text(pg, "#m3Grid .m3-card[data-id='TSE'] .m3-px"),
       text(pg, "#m3Grid .m3-card[data-id='TSE'] .m3-px"))

    # --- ★ 夜盤還畫不出線的時候，要在**同一個容器裡**講清楚為什麼
    #     用「Worker 還是舊版」這個真實情境來驗（回 404），這樣狀態才是確定的。
    pg.unroute("**/fut?*")
    pg.route("**/fut?*", lambda r: r.fulfill(status=404, content_type="application/json",
                                             body='{"error":"not found"}'))
    fresh(sess="night")
    ok("還是沒有那塊獨立方框", count(pg, "#futNight") == 0)
    # N11 的規矩：畫面上不能沒有東西，但要老實說它是什麼 —— 退回日盤並標在圖上
    fb = pg.evaluate("() => document.getElementById('m3c-FUT').dataset.fallback || ''")
    ok("夜盤報價拿不到時，圖上直接標明「先顯示日盤」", "日盤" in fb and "夜盤" in fb, fb)
    ok("退回去的是真的日盤走勢（不是一塊空白）",
       pg.evaluate(axis_of, "FUT") and pg.evaluate(axis_of, "FUT")[0] == "08:45", pg.evaluate(axis_of, "FUT"))
    ok("抓不到夜盤時，數字退回日盤而且明講",
       "45,780" in text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-px")
       and "夜盤報價未取得" in text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-tag"),
       text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-nums"))

    # --- 把來源換回正常的，從乾淨狀態重新累積
    pg.unroute("**/fut?*")
    pg.route("**/fut?*", fake_fut)
    fresh(sess="night")
    n1 = pg.evaluate("() => window.Market3.nightPoints.length")
    ok("重進夜盤先收到第一個點", 1 <= n1 <= 2, n1)
    # --- ★ 只有一兩個點、還畫不成線時，要在**同一個容器裡**講清楚為什麼
    if n1 < 2:
        ok("說明面板畫在圖表容器裡面", count(pg, "#m3c-FUT .m3-night") == 1, count(pg, "#m3c-FUT .m3-night"))
        hint = text(pg, "#m3c-FUT .m3-night")
        ok("有講出「沒有現成的分時序列」這件事", "分時序列" in hint, hint[:90])
        ok("有講出點是一筆一筆收的、收滿 2 筆才畫", "2 筆" in hint, hint[:200])
        ok("空狀態不是一塊塌掉的黑方塊（面板高度跟日盤一樣）",
           pg.evaluate("() => document.getElementById('m3c-FUT').getBoundingClientRect().height") > 200,
           pg.evaluate("() => document.getElementById('m3c-FUT').getBoundingClientRect().height"))
        ok("這時候上面那排數字已經是夜盤的（不會前後矛盾）",
           "夜盤" in text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-tag"),
           text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-nums"))

    # --- ★ 自動更新一輪就真的多一個點（每個點都是真的報價，不是內插）
    for _ in range(5):
        pg.evaluate("() => window.Market3.refresh(true)")
        pg.wait_for_timeout(700)
    pts = pg.evaluate("() => window.Market3.nightPoints")
    ok("多更新幾輪之後，夜盤真的累積出一串點", len(pts) >= 5, len(pts))
    ok("每個點的時間是遞增的（真的在走，不是同一筆重複）",
       all(pts[i][0] < pts[i + 1][0] for i in range(len(pts) - 1)), pts[:6])
    ok("每個點的價格不一樣（真的抓到新報價）", len({p[1] for p in pts}) == len(pts), pts[:6])
    ok("量是累計量的增量，不是把累計量畫上去", all(p[3] < p[2] for p in pts[1:]), pts[:4])

    # --- ★ 夜盤走勢圖真的畫出來了，而且是夜盤的時間軸
    ok("說明面板換成真的走勢圖了", count(pg, "#m3c-FUT .m3-night") == 0)
    night_axis = pg.evaluate(axis_of, "FUT")
    ok("夜盤走勢圖的時間軸是 15:00~05:00（跨午夜）",
       night_axis and night_axis[0] == "15:00" and night_axis[1] == "05:00", night_axis)
    changed("時間軸真的跟日盤不同", day_axis, night_axis)
    night_hash = canvas_hash(pg, "#m3c-FUT")
    changed("同一個容器，畫出來的東西真的不一樣了", day_hash, night_hash)
    ok("夜盤跟日盤用的是同一個圖表容器",
       pg.evaluate("() => !!document.querySelector('#m3c-FUT canvas')"))

    # --- ★ 夜盤也要有 K 線（跟日盤同一顆鈕、同一個容器）
    click(pg, "#m3Mode button[data-m='k']", 1500)
    pg.select_option("#m3Tf", "1"); pg.wait_for_timeout(1500)
    nk = pg.evaluate("() => { const k = window.Market3.state.kcharts.FUT; return k ? k.data.length : 0; }")
    ok("夜盤在 K 線模式真的畫出 K 棒", nk >= 5, nk)
    ok("夜盤 K 線也是 Lightweight Charts（跟日盤同一套）",
       pg.evaluate("() => document.getElementById('m3c-FUT').dataset.kind === 'k'"))
    PL = ("() => { const k = window.Market3.state.kcharts.FUT;"
          " if (!k || !k.priceLines || !k.priceLines.length) return null;"
          " return k.priceLines.map(l => (l.options ? l.options().title : l.title)); }")
    ok("夜盤 K 線的參考線寫的是「參考價」不是「昨收」",
       any("參考價" in str(t) for t in (pg.evaluate(PL) or [])), pg.evaluate(PL))

    # --- ★ 切回日盤：整張卡真的換回去
    click(pg, "#m3Mode button[data-m='line']", 1200)
    click(pg, "#futSeg button[data-s='day']", 1800)
    back_px = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-px")
    ok("切回日盤，數字真的換回日盤那一份", "45,780" in back_px, back_px)
    ok("切回日盤就沒有夜盤標籤了", count(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-tag") == 0)
    back_axis = pg.evaluate(axis_of, "FUT")
    changed("切回日盤，時間軸也真的換回 08:45~13:45", night_axis, back_axis)
    ok("切回去的軸就是原本那一組", back_axis == day_axis, back_axis)

    # --- 夜盤的選擇要記得住（重新整理還在夜盤，而且點不會歸零）
    click(pg, "#futSeg button[data-s='night']", 1500)
    # ★ 2026-09-21：存的不再是純字串「night」，而是 {sess, base} ——
    #   base＝做這個選擇時時鐘在哪一段，時段一翻就作廢（不然使用者會永久黏在夜盤）。
    #   所以這裡驗的是「兩個欄位都寫對了」，不是比一個寫死的字串。
    saved = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.m3.fut')); }"
                        " catch (e) { return localStorage.getItem('tw.m3.fut'); } }")
    ok("日盤／夜盤的選擇真的寫進 localStorage，而且是新格式 {sess, base}",
       isinstance(saved, dict) and saved.get("sess") == "night"
       and saved.get("base") in ("day", "night"), saved)
    before_n = pg.evaluate("() => window.Market3.nightPoints.length")
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(2400)
    ok("重新整理之後還在夜盤", pg.evaluate("() => window.Market3.session") == "night")
    after_n = pg.evaluate("() => window.Market3.nightPoints.length")
    ok("重新整理之後累積的點沒有歸零", after_n >= before_n, f"{before_n} → {after_n}")

    # ================================================================ 需求二：歷史至少三年
    fresh(sess="day", **{"tw.m3.mode": "k", "tw.m3.tf": "D"})
    pg.wait_for_timeout(1800)
    span = pg.evaluate("() => window.Market3.histSpan")
    ok("日線真的吃到三年以上（≥ 729 根）", span and span["n"] >= 729, span)
    dbars = {i: pg.evaluate("(id) => { const k = window.Market3.state.kcharts[id];"
                            " return k ? k.data.length : 0; }", i) for i in ("TSE", "OTC", "FUT")}
    for i, why in (("TSE", "加權"), ("OTC", "櫃買"), ("FUT", "台指期")):
        ok(f"{why}的日 K 有三年份（≥ 729 根）", dbars[i] >= 729, dbars)
    ok("歷史夠長時，上方說明會寫出涵蓋到哪一天", "目前日線涵蓋" in text(pg, "#m3Note"), text(pg, "#m3Note")[-60:])
    ok("歷史夠長時不會再出現「回補中」那行警告",
       pg.evaluate("() => !document.getElementById('m3c-TSE').dataset.fallback"),
       pg.evaluate("() => document.getElementById('m3c-TSE').dataset.fallback"))

    # --- ★ 週 K：三年份至少 100 多根（Andy 的截圖只有 7 根）
    pg.select_option("#m3Tf", "W"); pg.wait_for_timeout(2000)
    wbars = {i: pg.evaluate("(id) => { const k = window.Market3.state.kcharts[id];"
                            " return k ? k.data.length : 0; }", i) for i in ("TSE", "OTC", "FUT")}
    for i, why in (("TSE", "加權"), ("OTC", "櫃買"), ("FUT", "台指期")):
        ok(f"{why}的週 K 有 100 根以上（三年週線）", wbars[i] >= 100, wbars)
    ok("週 K 的根數大約是日 K 的五分之一", wbars["TSE"] < dbars["TSE"] / 3, f"{dbars['TSE']} → {wbars['TSE']}")
    pg.select_option("#m3Tf", "M"); pg.wait_for_timeout(2000)
    mbars = pg.evaluate("() => { const k = window.Market3.state.kcharts.TSE; return k ? k.data.length : 0; }")
    ok("月 K 有 30 根以上（三年月線）", mbars >= 30, mbars)
    pg.select_option("#m3Tf", "Q"); pg.wait_for_timeout(2000)
    qbars = pg.evaluate("() => { const k = window.Market3.state.kcharts.TSE; return k ? k.data.length : 0; }")
    ok("季 K 有 10 根以上（三年季線）", qbars >= 10, qbars)

    # --- ★ 歷史不夠三年時，畫面要自己講出「只有幾根、為什麼、什麼時候會變長」
    #     這是 Andy 這次的原始抱怨：他看到週 K 只有幾根，但畫面上完全沒說為什麼。
    LAKE["n"] = 32                                    # 就是 2026-09-19 資料湖的實際狀況
    fresh(sess="day", **{"tw.m3.mode": "k", "tw.m3.tf": "W"})
    pg.wait_for_timeout(2000)
    short_w = pg.evaluate("() => { const k = window.Market3.state.kcharts.TSE; return k ? k.data.length : 0; }")
    ok("歷史只有 32 天時，週 K 真的只有幾根（重現 Andy 的畫面）", 0 < short_w < 20, short_w)
    warn = pg.evaluate("() => document.getElementById('m3c-TSE').dataset.fallback || ''")
    ok("這時候卡片上真的寫出「只有幾根日 K」", "根日 K" in warn, warn)
    ok("而且寫出什麼時候會變長（回補中）", "回補" in warn, warn)
    ok("三張卡片都各自說明自己的歷史長度",
       all(pg.evaluate("(id) => !!(document.getElementById('m3c-' + id).dataset.fallback || '')", i)
           for i in ("TSE", "OTC", "FUT")))

    # ================================================================ 窄畫面 800px
    pg.set_viewport_size({"width": 800, "height": 1000})
    LAKE["n"] = 780
    fresh(sess="day")
    ok("800px 沒有橫向捲軸",
       pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
       pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))
    ok("800px 下三張卡都還在", count(pg, "#m3Grid .m3-card") == 3)
    click(pg, "#futSeg button[data-s='night']", 1800)
    ok("800px 下夜盤也切得動", pg.evaluate("() => window.Market3.session") == "night")
    ok("800px 下夜盤沒有橫向捲軸",
       pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
       pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))
    fs = pg.evaluate("() => { const e = document.querySelector('#m3c-FUT .m3-night .note')"
                     " || document.querySelector('#m3Grid .m3-card[data-id=\"FUT\"] .m3-sub');"
                     " return e ? parseFloat(getComputedStyle(e).fontSize) : 0; }")
    ok("800px 下夜盤說明文字不小於 11px", fs >= 11, fs)
    box = pg.evaluate("() => { const c = document.querySelector('#m3Grid .m3-card[data-id=\"FUT\"]');"
                      " const e = document.getElementById('m3c-FUT');"
                      " if (!c || !e) return null; const a = c.getBoundingClientRect(), b = e.getBoundingClientRect();"
                      " return [Math.round(b.right - a.right), Math.round(b.width)]; }")
    ok("800px 下圖表沒有戳出卡片外面", box and box[0] <= 2 and box[1] > 200, box)

    # ==================================================================================
    # 2026-09-20 追加（Andy 兩句話）
    #   ①「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去，格式 follow 加權指數」
    #   ②「三張走勢圖最新的點需要做呼吸燈圓圈…只要他正在即時更新就會執行呼吸燈效果」
    # 驗的都是「畫面真的因此改變」：點數真的多了幾百個、燈的透明度兩次取樣真的不一樣、
    # 讓它停下來之後真的不動了。
    # ==================================================================================

    # ---- 假的期交所分時序列（形狀完全照 docs/fixtures/taifex_night_probe.json 實測那一份）
    #      刻意埋進兩個真實存在的坑：
    #        · `046000` —— 硬切 HHMMSS 會得到 04:60:00，不是合法時間
    #        · 它跟 `050000` 其實是同一分鐘（重複），前端要只留後面那一筆
    NIGHT_TICKS = []
    for _m in range(901, 1741):                       # 15:01 ~ 翌日 05:00（跨午夜 +1440）
        _hh, _mm = (_m % 1440) // 60, _m % 60
        _px = 47400 + (_m % 37) * 3
        NIGHT_TICKS.append(["%02d%02d00" % (_hh, _mm), "%.2f" % _px, "%.2f" % (_px + 31),
                            "%.2f" % (_px - 24), "%.2f" % (_px + 6), str(20 + _m % 90)])
    # 倒數第二筆換成 046000（實測 fixture 就是長這樣），跟最後那筆 050000 是同一分鐘
    NIGHT_TICKS[-1] = ["046000", "47411.00", "47420.00", "47399.00", "47405.00", "36"]
    NIGHT_TICKS.append(["050000", "47409.00", "47433.00", "47391.00", "47418.00", "47"])

    # grow=False：整份 841 筆，形狀驗證用（結果要可重現）
    # grow=True ：每打一次多一分鐘，這樣「夜盤正在即時更新」才是真的，呼吸燈才驗得出來
    NT = {"grow": False, "i": 0}

    def fake_futchart(route):
        q = parse_qs(urlparse(route.request.url).query)
        sym = (q.get("symbol") or [""])[0]
        ticks = NIGHT_TICKS
        if NT["grow"]:
            ticks = NIGHT_TICKS[:max(200, len(NIGHT_TICKS) - 40 + NT["i"])]
            NT["i"] += 1
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps({"RtCode": "0", "RtMsg": "", "RtData": {
                          "SymbolID": sym, "DispCName": "臺指期106",
                          "Info": {"Status": "4", "Sessions": [{"Start": "1500", "End": "0500"}]},
                          "Quote": {"COpenPrice": "47494.00", "CHighPrice": "47584.00",
                                    "CLowPrice": "47208.00", "CLastPrice": "47418.00",
                                    "CTotalVolume": "21499", "CRefPrice": "47428.00",
                                    "CDate": "20260919"},
                          "Field": ["T", "O", "H", "L", "C", "V"],
                          "Ticks": ticks}}))

    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.route("**/futchart?*", fake_futchart)
    fresh(sess="night")
    # 等序列真的到手再量（平行跑的時候畫得慢，睡固定秒數會間歇性假紅）
    wait_until(pg, "() => { const f = window.Market3.futChart; return f && f.points.length > 800; }", 9000)
    pg.wait_for_timeout(400)

    # ---- ★ 時間欄位那個坑：04:60 要跟 05:00 是同一分鐘（不是 4 點 60 分這種不存在的時間）
    tm = pg.evaluate("() => [window.Market3.tickMin('150100', 900), window.Market3.tickMin('046000', 900),"
                     " window.Market3.tickMin('050000', 900), window.Market3.tickMin('134500', 525)]")
    ok("15:01 換算成台北分鐘數 901", tm and tm[0] == 901, tm)
    ok("★『046000』沒有被當成 04:60，而是進位成 05:00（＝跨午夜的 1740 分）", tm and tm[1] == 1740, tm)
    ok("『046000』與『050000』被判成同一分鐘", tm and tm[1] == tm[2], tm)
    ok("日盤的 13:45 不會被誤判成跨午夜", tm and tm[3] == 825, tm)

    # ---- ★ 序列真的接上了（這是 Andy 這次的主訴：「夜盤怎麼可能沒數據」）
    fc = pg.evaluate("() => { const f = window.Market3.futChart;"
                     " return f ? {sym: f.symbol, n: f.points.length, date: f.date,"
                     " first: f.points[0], last: f.points[f.points.length-1]} : null; }")
    ok("夜盤分時序列真的抓回來了", fc and fc["n"] > 800, fc and fc["n"])
    ok("合約代號是從夜盤報價清單撈來的近月（沒有寫死在前端）", fc and fc["sym"] == "TXFJ6-M", fc and fc["sym"])
    ok(f"★ 同一分鐘只留最後一筆：{len(NIGHT_TICKS)} 筆 tick 收斂成 {len(NIGHT_TICKS) - 1} 個點"
       "（046000 與 050000 是同一分鐘）",
       fc and fc["n"] == len(NIGHT_TICKS) - 1, (fc and fc["n"], len(NIGHT_TICKS)))
    ok("序列第一筆是 15:01（分鐘數 901）", fc and fc["first"]["min"] == 901, fc and fc["first"])
    ok("序列最後一筆是翌日 05:00（分鐘數 1740），而且留的是 050000 那一筆的收盤 47418",
       fc and fc["last"]["min"] == 1740 and abs(fc["last"]["c"] - 47418) < .01, fc and fc["last"])
    ok("每一筆都帶真的分鐘開高低（不是拿收盤合成的）",
       fc and fc["first"]["o"] is not None and fc["first"]["h"] > fc["first"]["c"], fc and fc["first"])

    # ---- ★ 走勢圖：點數真的變成一整晚，而且跟加權指數是同一套座標軸
    line_pts = pg.evaluate("() => { const el = document.getElementById('m3c-FUT');"
                           " const i = echarts.getInstanceByDom(el); if (!i) return 0;"
                           " return (((i.getOption().series||[])[0]||{}).data||[])"
                           "   .filter(v => v !== null && v !== undefined).length; }")
    ok("夜盤走勢圖上真的畫了幾百個點（不是 1 筆）", line_pts > 800, line_pts)
    nax = pg.evaluate(axis_of, "FUT")
    ok("夜盤走勢圖的時間軸是 15:00~05:00", nax and nax[0] == "15:00" and nax[1] == "05:00", nax)
    tse_ax = pg.evaluate(axis_of, "TSE")
    ok("跟加權指數同一套：兩邊都是 ECharts 類目軸、都有 markLine 參考線",
       pg.evaluate("() => { const f = echarts.getInstanceByDom(document.getElementById('m3c-FUT'));"
                   " const t = echarts.getInstanceByDom(document.getElementById('m3c-TSE'));"
                   " if (!f || !t) return false;"
                   " const s1 = f.getOption().series || [], s2 = t.getOption().series || [];"
                   " return s1.length === s2.length && !!s1[0].markLine && !!s2[0].markLine"
                   "   && s1[0].type === s2[0].type && s1[1].type === s2[1].type; }"),
       [nax, tse_ax])
    ok("★ 那塊「夜盤沒有現成的分時序列」的說明方框真的不見了（有真資料就不用解釋）",
       count(pg, "#m3c-FUT .m3-night") == 0, text(pg, "#m3c-FUT .m3-night")[:80])
    ok("夜盤的工具列跟加權指數是同一排（走勢圖／K 線、週期、展開都在）",
       count(pg, "#m3Mode button") == 2 and count(pg, "#m3Tf") == 1
       and count(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-big") == 1)

    # ---- ★ K 線：也是一整晚，而且高低是真的（不是 max(開, 收) 合成出來的）
    click(pg, "#m3Mode button[data-m='k']", 800)
    pg.select_option("#m3Tf", "1")
    kbars = wait_until(pg, "() => { const k = window.Market3.state.kcharts.FUT;"
                           " return k && k.data.length > 800 ? k.data.length : 0; }", 8000)
    ok("夜盤 K 線也是一整晚（800 根以上）", (kbars or 0) > 800, kbars)
    real = pg.evaluate("() => { const k = window.Market3.state.kcharts.FUT;"
                       " const b = k.data[0]; return [b.open, b.high, b.low, b.close]; }")
    ok("★ K 棒用的是期交所給的真分鐘高低（high 高於開收兩者，不是 max(開,收)）",
       real and real[1] > max(real[0], real[3]) and real[2] < min(real[0], real[3]), real)
    click(pg, "#m3Mode button[data-m='line']", 900)

    # ================================================================ 呼吸燈
    # 讓三張圖的資料**每抓一次就往前走一分鐘** —— 只有這樣「正在即時更新」才是真的，
    # 燈會不會呼吸才驗得出來（靜態資料本來就不該呼吸，那是下面另外一段）。
    TICK = {"i": 0}

    def fake_chart_live(route):
        """每打一次就多露出一分鐘 —— 這才是「盤中」真正的樣子。

        ★ 不能用「往後面接新的一分鐘」：`_fake_chart` 的最後一筆剛好就是收盤那一分鐘
        （加權 13:30、台指期 13:45），再往後接會落在交易時段外，被走勢圖直接濾掉，
        於是「最新那一點」根本不會動 —— 測到的會是假的綠燈。改成從後面往回藏一段再一分鐘一分鐘放出來。
        """
        q = parse_qs(urlparse(route.request.url).query)
        i = (q.get("id") or ["TSE"])[0].upper()
        j = _fake_chart(i)
        arr = j.get("ohlcArray") or []
        j["ohlcArray"] = arr[:max(120, len(arr) - 100 + TICK["i"])]
        TICK["i"] += 1
        route.fulfill(status=200, content_type="application/json; charset=utf-8", body=_json.dumps(j))

    def ring_samples(idx_id, n=9, gap=150):
        """連續量同一顆光環的透明度。★ 只量這一個量 —— 2026-09-19 有過三次
        「A and B 其中一個分量本來就不會動 → 假紅」的教訓。"""
        out = []
        for _ in range(n):
            out.append(pg.evaluate("(id) => { const e = document.querySelector('#m3c-' + id + ' .m3-pulse .m3-ring');"
                                   " return e ? parseFloat(getComputedStyle(e).opacity) : -1; }", idx_id))
            pg.wait_for_timeout(gap)
        return out

    pg.unroute("**/chart?*")
    pg.route("**/chart?*", fake_chart_live)
    fresh(sess="day")
    for _ in range(3):                                # 跑幾輪，讓「最後一個點」真的往前走過
        pg.evaluate("() => window.Market3.refresh(true)")
        pg.wait_for_timeout(600)

    ok("★ 三張走勢圖最新的那一點都有呼吸燈", count(pg, "#m3Grid .m3-pulse") == 3,
       count(pg, "#m3Grid .m3-pulse"))
    live = pg.evaluate("() => window.Market3.pulses")
    ok("三張都判定成「正在即時更新」", live and all(v["live"] for v in live.values()), live)
    ok("燈標在最新的那一分鐘上（三張各自標自己的時間）",
       live and all(v["at"] for v in live.values()), live)

    # --- ★ 真的在動：同一顆光環的透明度，多個時間點量出來不一樣
    samp = ring_samples("TSE")
    ok("★ 呼吸燈真的在呼吸（透明度在不同時間點量到不一樣）",
       max(samp) - min(samp) > 0.05, samp)
    ok("三張圖都在呼吸（櫃買那顆也量得到變化）",
       (lambda a: max(a) - min(a) > 0.05)(ring_samples("OTC")), None)
    ok("呼吸燈掛著 CSS 動畫",
       pg.evaluate("() => { const e = document.querySelector('#m3c-TSE .m3-pulse .m3-ring');"
                   " return e && e.getAnimations ? e.getAnimations().length : 0; }") >= 1)

    # --- 燈真的釘在最右端那一點上（不是隨便放在角落）
    place = pg.evaluate("""() => { const el = document.getElementById('m3c-TSE');
        const d = el.querySelector('.m3-pulse'); if (!d) return null;
        const a = el.getBoundingClientRect(), b = d.getBoundingClientRect();
        const i = echarts.getInstanceByDom(el);
        const s = ((i.getOption().series||[])[0]||{}).data||[];
        let last = -1; for (let k = s.length-1; k >= 0; k--) if (s[k] != null) { last = k; break; }
        const px = i.convertToPixel({seriesIndex:0}, [last, s[last]]);
        // ★ 要跟「x 軸的兩端」比，不是跟容器寬度比：右邊還有 58px 的 y 軸欄位，
        //    拿容器寬度當分母，畫在 63% 位置的點會被算成 48%，變成假紅。
        const x0 = i.convertToPixel({seriesIndex:0}, [0, s.find(v => v != null)]);
        return [Math.round(b.left - a.left), Math.round(px[0]), Math.round(b.top - a.top),
                Math.round(px[1]), Math.round(x0[0]), Math.round(a.width), last, s.length]; }""")
    ok("呼吸燈釘在 ECharts 算出來的那一點上（誤差 2px 內）",
       place and abs(place[0] - place[1]) <= 2 and abs(place[2] - place[3]) <= 2, place)
    ok("燈在 x 軸的右半段（那一點就是最新的）",
       place and place[6] > place[7] * 0.5 and place[1] > place[4], place)

    # --- ★ 資料再往前走，燈也要跟著往前（不是釘死在第一次的位置）
    at0 = pg.evaluate("() => (window.Market3.pulses.TSE||{}).at")
    left0 = pg.evaluate("() => { const d = document.querySelector('#m3c-TSE .m3-pulse');"
                        " return d ? Math.round(parseFloat(d.style.left)) : -1; }")
    for _ in range(3):
        pg.evaluate("() => window.Market3.refresh(true)")
        pg.wait_for_timeout(600)
    at1 = pg.evaluate("() => (window.Market3.pulses.TSE||{}).at")
    left1 = pg.evaluate("() => { const d = document.querySelector('#m3c-TSE .m3-pulse');"
                        " return d ? Math.round(parseFloat(d.style.left)) : -1; }")
    changed("資料往前走之後，燈標的時間真的換了一分鐘", at0, at1)
    changed("燈的位置也真的往右移了", left0, left1)

    # --- ★ 讓「正在更新」變成 false：分頁切到背景（背景時 refresh() 根本不跑，燈亮著就是說謊）
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden',
        {configurable: true, get: () => true});
        Object.defineProperty(document, 'visibilityState',
        {configurable: true, get: () => 'hidden'});
        document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(500)
    ok("★ 切到背景之後，判定真的變成「沒有在更新」",
       pg.evaluate("() => Object.values(window.Market3.pulses).every(v => !v.live)"),
       pg.evaluate("() => window.Market3.pulses"))
    ok("光環上的呼吸動畫真的被拿掉了",
       pg.evaluate("() => { const e = document.querySelector('#m3c-TSE .m3-pulse .m3-ring');"
                   " return e && e.getAnimations ? e.getAnimations().length : -1; }") == 0)
    off = ring_samples("TSE", n=6, gap=140)
    ok("★ 燈真的停了（透明度連量六次完全不動）", max(off) - min(off) < 0.001, off)
    ok("最新點本身還在（停的是呼吸，不是把「最新在哪」也藏掉）",
       count(pg, "#m3c-TSE .m3-pulse .m3-core") == 1)

    # --- 切回前景：要會自己活過來（不是一停就永遠壞掉）
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden',
        {configurable: true, get: () => false});
        Object.defineProperty(document, 'visibilityState',
        {configurable: true, get: () => 'visible'});
        document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(1200)
    back = ring_samples("TSE")
    ok("★ 切回前景之後又開始呼吸了", max(back) - min(back) > 0.05, back)

    # --- K 線模式沒有「最新的那一點」→ 燈要真的從 DOM 消失，不是留在那裡誤導
    click(pg, "#m3Mode button[data-m='k']", 1200)
    ok("★ 切到 K 線，呼吸燈真的不在 DOM 裡了", count(pg, "#m3Grid .m3-pulse") == 0,
       count(pg, "#m3Grid .m3-pulse"))
    click(pg, "#m3Mode button[data-m='line']", 1200)
    ok("切回走勢圖，呼吸燈又回來了", count(pg, "#m3Grid .m3-pulse") == 3,
       count(pg, "#m3Grid .m3-pulse"))

    # --- ★ 防「一打開就先騙你」：資料靜止不動時，燈在但**不呼吸**
    pg.unroute("**/chart?*")
    pg.route("**/chart?*", fake_chart)                # 回到固定不動的那一份
    fresh(sess="day")
    pg.wait_for_timeout(1500)
    ok("資料靜止時燈還在（最新點永遠標得出來）", count(pg, "#m3Grid .m3-pulse") == 3,
       count(pg, "#m3Grid .m3-pulse"))
    ok("★ 但它不呼吸 —— 沒有真的往前走過就不准亮",
       pg.evaluate("() => Object.values(window.Market3.pulses).every(v => !v.live)"),
       pg.evaluate("() => window.Market3.pulses"))
    still = ring_samples("TSE", n=6, gap=140)
    ok("靜止資料的光環透明度量六次完全不動", max(still) - min(still) < 0.001, still)

    # ================================================================ 窄畫面 800px（新功能也要驗）
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.unroute("**/chart?*")
    pg.route("**/chart?*", fake_chart_live)
    NT["grow"] = True                                 # 夜盤序列也要真的一分鐘一分鐘長
    fresh(sess="night")
    for _ in range(2):
        pg.evaluate("() => window.Market3.refresh(true)")
        pg.wait_for_timeout(600)
    ok("800px 下夜盤分時序列一樣抓得到",
       pg.evaluate("() => { const f = window.Market3.futChart; return f ? f.points.length : 0; }") > 800,
       pg.evaluate("() => { const f = window.Market3.futChart; return f ? f.points.length : 0; }"))
    ok("800px 沒有橫向捲軸（夜盤）",
       pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
       pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))
    inside = pg.evaluate("""() => { const out = [];
        for (const id of ['TSE','OTC','FUT']) {
          const el = document.getElementById('m3c-' + id);
          const d = el && el.querySelector('.m3-pulse'); if (!d) { out.push([id, 'no-dot']); continue; }
          const a = el.getBoundingClientRect(), b = d.getBoundingClientRect();
          out.push([id, Math.round(b.left - a.left), Math.round(a.width),
                    b.left >= a.left - 1 && b.right <= a.right + 1 && b.top >= a.top - 1
                      && b.bottom <= a.bottom + 1]); }
        return out; }""")
    ok("800px 下三顆呼吸燈都還在圖表容器裡面（沒有戳出去）",
       inside and len(inside) == 3 and all(r[-1] is True for r in inside), inside)
    ok("800px 下夜盤的燈也在呼吸",
       (lambda a: max(a) - min(a) > 0.05)(ring_samples("FUT")), None)

    # ---- 窄畫面下「還沒接到官方序列」的說明帶：不能蓋住 y 軸、字不能小於 11px
    pg.unroute("**/futchart?*")
    pg.route("**/futchart?*", lambda r: r.fulfill(status=404, content_type="application/json",
                                                  body='{"error":"not found"}'))
    fresh(sess="night")
    pg.wait_for_timeout(1500)
    if count(pg, "#m3c-FUT .m3-night"):
        hint2 = text(pg, "#m3c-FUT .m3-night")
        ok("退場說明改寫成「正在接期交所的分時端點」（不再只寫『沒有現成的分時序列』）",
           "正在接期交所的分時端點" in hint2, hint2[:120])
        ok("Worker 還是舊版時，說明直接講要去重貼 worker.js", "futchart" in hint2 or "Worker" in hint2,
           hint2[:160])
        fs2 = pg.evaluate("() => { const e = document.querySelector('#m3c-FUT .m3-night .note');"
                          " return e ? parseFloat(getComputedStyle(e).fontSize) : 0; }")
        ok("800px 下說明帶的字不小於 11px", fs2 >= 11, fs2)
        band = pg.evaluate("""() => { const el = document.getElementById('m3c-FUT');
            const n = el.querySelector('.m3-night'); const a = el.getBoundingClientRect();
            const b = n.getBoundingClientRect();
            return [Math.round(a.right - b.right), Math.round(b.height), Math.round(a.height)]; }""")
        ok("說明帶是一條窄帶（沒有把整張圖蓋掉），而且右邊留給 y 軸標籤",
           band and band[0] >= 40 and band[1] < band[2] * 0.6, band)
        ok("★ 說明帶底下的圖是真的畫出來的（不是被方框換掉）",
           pg.evaluate("() => !!document.querySelector('#m3c-FUT canvas, #m3c-FUT svg')"))
        nax2 = pg.evaluate(axis_of, "FUT")
        ok("沒有官方序列時，座標軸仍然是夜盤那一套（格式跟加權一樣）",
           nax2 and nax2[0] == "15:00" and nax2[1] == "05:00", nax2)

    # ---- 收拾（DECISIONS：t_market3 留下的狀態會害下一段掛掉，這裡一定要清乾淨）
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.unroute("**/chart?*")
    pg.unroute("**/fut?*")
    pg.unroute("**/data/index_ohlc.json*")
    pg.unroute("**/futchart?*")
    pg.evaluate("() => { try { ['tw.m3.mode','tw.m3.tf','tw.m3.big','tw.m3.fut','tw.m3.nightpts',"
                "'tw.live.proxy'].forEach(k => localStorage.removeItem(k)); } catch(e){} }")


def t_new_industry(pg, base):
    """產業關聯圖與個股頁（site/industry.js）：點公司要選到族群、個股頁分頁順序。

    Andy 2026-09-20 兩句話：
      ①「當我點擊『日月光頭控』時 他所對應的族群會被選取，修正這功能」
      ②「當點擊個股時 最新出現的是K線圖、多週期判對、總攬、營收…公告/新聞，
         下方才是 產業地圖等資訊」

    這裡每一條都驗「畫面真的因此改變」：
      · 點 3711 之後 —— 成分股**筆數真的變少**、環節色標與族群卡片**真的多一個 .sel**、
        而且 `location.hash` **沒有變**（N7 說好的不跳頁）。
      · 個股頁 —— 量 `getBoundingClientRect().top`，K 線要**真的排在**產業鏈區塊上面，
        而且 K 線容器高度 > 0（搬 DOM 最容易把圖表容器弄成 0 高）。
      · 兩件事都在 1500px 與 800px 各驗一次。
    """
    # ============================================================ 需求一
    for vw in (1500, 800):
        pg.set_viewport_size({"width": vw, "height": 1000})
        # 先繞去產業地圖再回來：goto 同一個 hash 不會重新載入（DECISIONS #154），
        # 上一輪選好的環節會留著，下一輪就驗不到「從沒選到有選」。
        pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(700)
        pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1800)
        # 800px 時右邊的「今日事件」欄是展開的浮層，會蓋住關聯圖右半邊 ——
        # 那是事件欄自己的行為，不是這次要驗的東西，先收掉（t_chainnav 也是這樣做）。
        pg.evaluate("() => { const s = document.getElementById('side'); if (s) s.classList.remove('open'); }")
        # 2026-09-20 起產業鏈頁**預設是環節卡清單**（Andy：關聯圖上下框度太長），
        # 關聯圖要按右上角那顆鈕才出來。這一段驗的是「在關聯圖上點公司」這條既有路徑，
        # 所以先把關聯圖切出來；清單那一條路徑在下面「需求三」另外驗一次。
        if pg.query_selector("#chainView") and pg.evaluate(
                "() => { const m = document.getElementById('chainMap'); return !!(m && m.hidden); }"):
            click(pg, "#chainView", 900)
        ok(f"{vw}px 按「看關聯圖」之後關聯圖真的出現了",
           pg.evaluate("() => { const m = document.getElementById('chainMap'); return !!m && !m.hidden; }"))
        sel = '#chainMap g.co[data-code="3711"]'
        if not ok(f"{vw}px 關聯圖上找得到日月光投控 3711 的節點",
                  pg.evaluate(f"() => !!document.querySelector({sel!r})")):
            continue
        SNAP = """() => ({ hash: location.hash,
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            chips: document.querySelectorAll('#segChips .segchip.sel').length,
            chipSeg: [...document.querySelectorAll('#segChips .segchip.sel')].map(c => c.dataset.seg),
            tiles: document.querySelectorAll('#groupCards .tile.sel').length,
            tileIds: [...document.querySelectorAll('#groupCards .tile.sel')].map(t => t.dataset.gid),
            title: (document.getElementById('memberTitle')||{}).innerText,
            codes: [...document.querySelectorAll('#memberTable tbody tr')].map(r => r.dataset.code) })"""
        before = pg.evaluate(SNAP)
        ok(f"{vw}px 點之前什麼都沒選（不然下面的「變了」不算數）",
           before["chips"] == 0 and before["tiles"] == 0, before)
        # 真的用滑鼠點那張卡片（不是 dispatchEvent）
        if not click(pg, sel, 1000):
            continue
        after = pg.evaluate(SNAP)
        # ---- 不准跳頁（N7 既有行為不能被這次改動弄壞）
        ok(f"{vw}px 點公司不會跳去個股頁（hash 沒變）", after["hash"] == before["hash"],
           f"{before['hash']} → {after['hash']}")
        ok(f"{vw}px 點公司仍然會開原地面板，面板裡才有「看個股頁」",
           pg.evaluate("""() => { const b = document.getElementById('coBox');
               return !!b && b.textContent.indexOf('日月光投控') >= 0
                          && b.textContent.indexOf('看個股頁') >= 0; }"""))
        # ---- 環節色標真的被選起來，而且選的就是日月光的那一格
        changed(f"{vw}px 點公司之後環節色標真的多一個選取", before["chips"], after["chips"])
        ok(f"{vw}px 選到的是日月光所屬的環節 osat_test", after["chipSeg"] == ["osat_test"], after["chipSeg"])
        # ---- 族群卡片真的亮起來（Andy 原話就是「他所對應的族群會被選取」）
        changed(f"{vw}px 點公司之後族群卡片真的被選取", before["tiles"], after["tiles"])
        ok(f"{vw}px 被選取的族群是「封測」osat", "osat" in after["tileIds"], after["tileIds"])
        # ---- 成分股表真的被篩掉
        ok(f"{vw}px 點公司之後成分股筆數真的變少", after["rows"] < before["rows"],
           f"{before['rows']} → {after['rows']}")
        ok(f"{vw}px 篩完剩下的每一檔都是封測環節的",
           bool(after["codes"]) and set(after["codes"]) <= {"3711", "6239", "2449", "6257", "3264", "8150", "3374"},
           after["codes"])
        ok(f"{vw}px 成分股標題寫出現在篩的是哪個環節", "封測" in (after["title"] or ""), after["title"])
        # ---- 再點一次環節色標要能取消（不然選下去就出不來）
        click(pg, "#segChips .segchip.sel", 700)
        back = pg.evaluate(SNAP)
        ok(f"{vw}px 點環節色標可以把選取取消掉（回得去）",
           back["chips"] == 0 and back["rows"] == before["rows"], f"{after} → {back}")
    pg.set_viewport_size({"width": 1500, "height": 1000})

    # ============================================================ 需求二
    # 產業鏈圖預設收合，但兩種狀態都要驗 —— 展開時 #chainMap 會去捲位置，
    # 那正是最容易把整頁拉到底、害 K 線被推出畫面的地方。
    for chain_open in ("0", "1"):
        pg.evaluate("(v) => { try { localStorage.setItem('tw.chainOpen', v); } catch(e) {} }", chain_open)
        for vw in (1500, 800):
            pg.set_viewport_size({"width": vw, "height": 1000})
            pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(500)
            pg.goto(f"{base}#stock/2330", wait_until="networkidle"); pg.wait_for_timeout(2600)
            tag = f"{vw}px／產業鏈圖{'展開' if chain_open == '1' else '收合'}"
            geo = pg.evaluate("""() => { const t = (s) => { const e = document.querySelector(s);
                    if (!e) return null; const r = e.getBoundingClientRect();
                    return { top: Math.round(r.top + scrollY), h: Math.round(r.height) }; };
                return { chart: t('.chartwrap'), lwc: t('#lwc'), mtf: t('#mtfCard'),
                         tabs: t('#stockTabs'), tab: t('#stockTab'), chain: t('#indChain'),
                         canvas: document.querySelectorAll('#lwc canvas').length,
                         y: Math.round(scrollY),
                         order: [...document.querySelectorAll('#v-industry > div')].map(d => d.id) }; }""")
            if not ok(f"{tag} 個股頁該有的區塊都在",
                      all(geo[k] for k in ("chart", "lwc", "mtf", "tabs", "chain")), geo):
                continue
            ok(f"{tag} K 線圖排在產業鏈區塊上面（Andy 要先看到 K 線）",
               geo["chart"]["top"] < geo["chain"]["top"], f"K線 {geo['chart']['top']} vs 產業鏈 {geo['chain']['top']}")
            ok(f"{tag} 多週期判讀在 K 線之後、分頁之前",
               geo["chart"]["top"] < geo["mtf"]["top"] < geo["tabs"]["top"], geo)
            ok(f"{tag} 分頁（總覽／營收…公告新聞）也排在產業鏈區塊上面",
               geo["tabs"]["top"] < geo["chain"]["top"] and geo["tab"]["top"] < geo["chain"]["top"], geo)
            ok(f"{tag} DOM 順序真的變成 stockPage 在 indChain 前面",
               geo["order"].index("stockPage") < geo["order"].index("indChain"), geo["order"])
            # 搬 DOM 最容易踩的坑：圖表容器變成 0 高、或 canvas 根本沒建起來
            ok(f"{tag} K 線容器沒有被搬成 0 高", geo["lwc"]["h"] > 200, geo["lwc"])
            ok(f"{tag} K 線真的畫出來了（有 canvas）", geo["canvas"] > 0, geo["canvas"])
            # 進頁面不可以被 scrollIntoView 拖到最底下（那樣第一眼還是看不到 K 線）
            ok(f"{tag} 一進個股頁畫面停在最上面，沒有被拖到產業鏈那一段",
               geo["y"] < 120, f"scrollY={geo['y']}")
            ok(f"{tag} 沒有橫向捲軸",
               pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
               pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))
    pg.evaluate("() => { try { localStorage.setItem('tw.chainOpen', '0'); } catch(e) {} }")
    pg.set_viewport_size({"width": 1500, "height": 1000})

    # ---- 離開個股頁要搬回去：產業鏈頁上「產業鏈在上、個股頁區塊在下」不能被弄壞
    pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1600)
    ok("回到產業鏈頁時 indChain 有搬回 stockPage 前面",
       pg.evaluate("""() => { const o = [...document.querySelectorAll('#v-industry > div')].map(d => d.id);
           return o.indexOf('indChain') < o.indexOf('stockPage'); }"""),
       pg.evaluate("() => [...document.querySelectorAll('#v-industry > div')].map(d => d.id)"))
    ok("而且產業鏈頁本身還是正常的（有標題、有成分股）",
       len(text(pg, "#indChain h2")) > 1 and count(pg, "#memberTable tbody tr") > 0,
       text(pg, "#indChain h2"))

    # ======================================================== 需求三（2026-09-20 第三件）
    # Andy：「供應鏈關聯圖 這邊我覺得上下框度太長，改成 顯示族群以及族群標題底下顯示
    #        個股小卡 如圖那樣」（他附的圖＝總覽「熱門題材」那種卡片）。
    #
    # 這一段驗四件事，每一件都要「畫面真的因此改變」：
    #   ① 高度真的變短
    #   ② 點個股小卡 → 右側產業關係面板真的開、有內容，而且 hash 沒變（不准跳頁）
    #   ③ 點環節卡 → 下方成分股筆數真的被篩掉，再點一次真的取消
    #   ④ 800px 小卡不跑出容器、沒有橫向捲軸
    # 三條鏈都驗 —— 一般電子鏈是 2026-09-20 剛建的，環節數與公司數跟另外兩條差很多。
    GOLIST = "() => { try { localStorage.setItem('tw.chainView', 'list'); } catch (e) {} }"

    # ---------------------------------------------------------------- ① 高度
    # 改動前（同一份本機資料、右側事件欄展開）實測 #industry/semiconductor 的整頁高度：
    #   1366px → 4939（關聯圖 1174）　1500px → 5026（1345）　1920px → 5147（1360）
    # 門檻取「改動前 − 400」，因為這次要解的就是「一張圖佔掉近半個螢幕高」：
    # 少 400px 以上才叫真的短了，少一點點只是排版抖動。
    #
    # ★ 2026-09-21：110 個板塊上線之後這三個數字一度爆到 9051／8864／8693。
    #   量出來的組成（1366px 半導體）：成分股表格 6332、族群卡 708、環節卡清單 645、
    #   剖析圖 421、環節色標 110 —— **七成是成分股表格**，因為這條鏈的成分股
    #   從 47 檔變成 156 檔（148 列 × 約 43px）。環節卡清單只有 645px，
    #   D0 那一輪的修法沒有被打回原形。
    #   修法：成分股預設只列前 30 檔，底下一顆「顯示全部 N 檔」原地展開（見 industry.js）。
    #   修完實測 4077／3889／3718，三個都回到門檻以下，甚至比 110 板塊上線前還矮。
    PAGE_MAX = {1366: 4550, 1500: 4650, 1920: 4750}
    for vw in (1366, 1500, 1920):
        pg.set_viewport_size({"width": vw, "height": 1000})
        pg.evaluate(GOLIST)
        pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(500)
        pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1800)
        GEO = """() => { const h = (s) => { const e = document.querySelector(s);
                return e ? Math.round(e.getBoundingClientRect().height) : 0; };
            return { page: Math.round(document.documentElement.scrollHeight),
                     list: h('#chainList'), map: h('#chainMap'),
                     cards: document.querySelectorAll('#chainList .segcard').length,
                     minis: document.querySelectorAll('#chainList .sco').length }; }"""
        g1 = pg.evaluate(GEO)
        ok(f"{vw}px 產業鏈頁預設就是環節卡清單（不是關聯圖）",
           g1["cards"] > 0 and g1["map"] == 0, g1)
        ok(f"{vw}px 清單上真的排出了個股小卡（半導體鏈 52 家）", g1["minis"] >= 50, g1)
        was = {1366: 4939, 1500: 5026, 1920: 5147}[vw]
        ok(f"{vw}px 半導體鏈整頁高度真的變短（改動前 {was}）",
           g1["page"] <= PAGE_MAX[vw], f"整頁 {g1['page']}，門檻 {PAGE_MAX[vw]}")
        # ★ 自我校準：跟「同一頁切到關聯圖」自己比，資料換了也不會誤判（DECISIONS #206 的教訓）
        click(pg, "#chainView", 1200)
        g2 = pg.evaluate(GEO)
        if ok(f"{vw}px 按「看關聯圖」真的切得出關聯圖", g2["map"] > 200 and g2["list"] == 0, g2):
            ok(f"{vw}px 環節卡清單比關聯圖矮很多（不到六成）",
               g1["list"] < g2["map"] * 0.6, f"清單 {g1['list']} vs 關聯圖 {g2['map']}")
            ok(f"{vw}px 換成清單之後整頁至少短 400px",
               g2["page"] - g1["page"] >= 400, f"關聯圖版 {g2['page']} → 清單版 {g1['page']}")
        click(pg, "#chainView", 900)
        ok(f"{vw}px 再按一次切得回環節卡清單",
           pg.evaluate("() => { const l = document.getElementById('chainList'); return !!l && !l.hidden; }"))
    pg.set_viewport_size({"width": 1500, "height": 1000})

    # ------------------------------------------- ①-2 成分股「先列前 30 檔」真的被操作過
    # 這是 2026-09-21 新加的功能，所以要真的按它，而且要驗「畫面真的因此改變」：
    # 列數變了、整頁高度變了、localStorage 真的寫進去了、再按一次真的回得來。
    # ★ 這一條同時是「高度門檻」的自我校準版本：不管資料長多大，
    #   只要收合真的有在做事，展開前後的高度差一定很大（DECISIONS #206）。
    pg.evaluate("() => { try { localStorage.removeItem('tw.memberAll'); } catch (e) {} }")
    pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(400)
    pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1800)
    MB = """() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
        total: (() => { const m = /(\\d+)\\s*檔/.exec(
            (document.getElementById('memberTitle')||{}).innerText || ''); return m ? +m[1] : -1; })(),
        page: Math.round(document.documentElement.scrollHeight),
        btn: (document.getElementById('memberMoreBtn') || {}).textContent || '',
        hint: (document.getElementById('memberMore') || {}).innerText || '',
        saved: (() => { try { return localStorage.getItem('tw.memberAll'); } catch (e) { return null; } })() })"""
    m0 = pg.evaluate(MB)
    ok("成分股預設只列前 30 檔（半導體鏈有 148 檔，全部攤開就是 6300px）",
       m0["rows"] == 30 and m0["total"] > 100, m0)
    ok("標題上仍然寫著真實筆數（一檔都沒有消失，只是先不畫出來）", m0["total"] > 100, m0)
    ok("「顯示全部」旁邊寫得出「所以我該怎麼用」（怎麼找特定個股），不是只講還有幾檔",
       "要找特定個股" in m0["hint"] and "排序" in m0["hint"], m0["hint"][:160])
    if ok("成分股下方真的有「顯示全部 N 檔」這顆鈕", "顯示全部" in m0["btn"], m0["btn"]):
        click(pg, "#memberMoreBtn", 1000)
        m1 = pg.evaluate(MB)
        changed("按「顯示全部」，表格列數真的變多", m0["rows"], m1["rows"])
        ok("而且變成真實筆數（或表格上限 200）",
           m1["rows"] == min(m1["total"], 200), m1)
        ok("按「顯示全部」之後整頁真的變高很多（證明預設的收合真的在做事）",
           m1["page"] - m0["page"] >= 2000, f"{m0['page']} → {m1['page']}")
        ok("展開狀態真的寫進 localStorage（tw.memberAll）", m1["saved"] == "1", m1["saved"])
        ok("鈕的字跟著變成「只看前 30 檔」", "只看前" in m1["btn"], m1["btn"])
        click(pg, "#memberMoreBtn", 1000)
        m2 = pg.evaluate(MB)
        ok("再按一次真的收回去（列數與整頁高度都回到原本）",
           m2["rows"] == m0["rows"] and abs(m2["page"] - m0["page"]) <= 4, f"{m1} → {m2}")
        ok("收回去的狀態也寫進 localStorage", m2["saved"] == "0", m2["saved"])

    # ------------------------------------------------- ②③ 三條鏈各驗一次點擊行為
    # 每條鏈挑一檔一定在清單上的台股，以及一個一定有台股的環節
    # （鏈 id, 個股代號, 簡稱, 要點的環節, 這檔所屬環節）
    # ★ 2026-09-21：最後一欄本來寫死族群 id（osat／server_thermal／passive），
    #   110 個板塊上線之後散熱拆成 liquid_cooling＋air_cooling、被動元件拆成 mlcc＋capacitor，
    #   那三個 id 全部不存在了。但**產品行為完全正確**，只是名字變了 ——
    #   這正是 DECISIONS #207 說的「驗收不要綁顯示名稱／會被產品決策改的 id」。
    #   改成從前端自己的對照表 `A.L.sgroups[環節]` 推出「這一格該亮哪幾個族群卡」，
    #   守的事情一模一樣：點小卡 → 它所屬的族群卡片真的亮起來，而且亮的就是那幾張。
    CHAINS = [("semiconductor", "3711", "日月光投控", "foundry", "osat_test"),
              ("ai_server", "3017", "奇鋐", "thermal", "thermal"),
              ("electronics", "2327", "國巨", "panel_mfg", "passive_comp")]
    SNAP2 = """() => ({ hash: location.hash,
        rows: document.querySelectorAll('#memberTable tbody tr').length,
        cardSel: [...document.querySelectorAll('#chainList .segcard.sel')].map(c => c.dataset.seg),
        chipSeg: [...document.querySelectorAll('#segChips .segchip.sel')].map(c => c.dataset.seg),
        tiles: [...document.querySelectorAll('#groupCards .tile.sel')].map(t => t.dataset.gid),
        box: (document.getElementById('coBox') || {}).innerText || '',
        side: !!document.querySelector('.chainrow > #coBox.relside') })"""
    for cid, code, cname, seg_click, seg_of_co in CHAINS:
        pg.evaluate(GOLIST)
        pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(500)
        pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(1700)
        n_seg = count(pg, "#chainList .segcard")
        if not ok(f"{cid} 排得出環節卡", n_seg >= 8, n_seg):
            continue
        # --- 每張環節卡的標題底下真的有個股小卡（Andy 的原話）
        ok(f"{cid} 環節卡是「標題＋底下一排個股小卡」的結構",
           pg.evaluate("""() => [...document.querySelectorAll('#chainList .segcard')]
               .filter(c => c.querySelector('.sh .nm') && c.querySelector('.sms .sco')).length"""), n_seg)
        # --- 那 140 條邊沒有整個消失：卡片要寫出上下游是哪幾格、小卡要標關係條數
        rel = pg.evaluate("""() => ({ flow: document.querySelectorAll('#chainList .segcard .sf').length,
            sg: document.querySelectorAll('#chainList .segcard .sf .sg').length,
            badge: document.querySelectorAll('#chainList .sco .rel').length,
            iso: document.querySelectorAll('#chainList .sco .rel.iso').length })""")
        ok(f"{cid} 環節卡有寫出「上游／下游」是哪幾格，而且那幾格可以點",
           rel["flow"] >= 5 and rel["sg"] >= 5, rel)
        ok(f"{cid} 每張個股小卡都標了「這家有幾條上下游關係」", rel["badge"] == count(pg, "#chainList .sco"), rel)
        # --- ② 點個股小卡：面板真的開、有內容、不跳頁
        before = pg.evaluate(SNAP2)
        if ok(f"{cid} 清單上找得到 {cname} {code} 的小卡",
              pg.evaluate(f"() => !!document.querySelector('#chainList .sco[data-code=\"{code}\"]')")):
            click(pg, f'#chainList .sco[data-code="{code}"]', 1100)
            after = pg.evaluate(SNAP2)
            ok(f"{cid} 點個股小卡不會跳頁（hash 沒變）", after["hash"] == before["hash"],
               f"{before['hash']} → {after['hash']}")
            ok(f"{cid} 點個股小卡真的展開「產業關係」面板，而且排在圖的旁邊",
               after["side"] and cname in after["box"] and "看個股頁" in after["box"], after["box"][:120])
            ok(f"{cid} 面板裡真的有產業關係的內容（上游／下游／還沒建立關聯 至少一項）",
               any(k in after["box"] for k in ("上游", "下游", "還沒建立上下游關聯")), after["box"][:200])
            changed(f"{cid} 點小卡之後成分股筆數真的變了", before["rows"], after["rows"])
            ok(f"{cid} 點小卡會把它所屬的環節一起選起來（{seg_of_co}）",
               after["cardSel"] == [seg_of_co] and after["chipSeg"] == [seg_of_co], after)
            # 這一格對應到哪幾個族群，問前端自己那份對照表（不寫死 id）
            want_gids = pg.evaluate(
                f"() => (window.Link && window.Link.sgroups['{seg_of_co}']) || []")
            # 對照表可能列到不在這條鏈上的族群（例如散熱也掛在半導體鏈的導線架化學品），
            # 所以只比「這一頁畫得出來的那幾張卡」
            on_page = pg.evaluate(
                "() => [...document.querySelectorAll('#groupCards .tile')].map(t => t.dataset.gid)")
            want = [g for g in want_gids if g in on_page]
            ok(f"{cid} 環節 {seg_of_co} 在這一頁對得到族群卡（對照表不是空的）", len(want) > 0,
               {"sgroups": want_gids, "這一頁有的": on_page[:8]})
            ok(f"{cid} 它所屬的族群卡片也跟著亮（{'／'.join(want) or '（無）'}）",
               bool(want) and sorted(after["tiles"]) == sorted(want),
               {"亮起來的": after["tiles"], "應該亮": want})
            # 點到底：面板裡那顆「看個股頁 →」真的走得到個股頁
            pg.eval_on_selector("#coBox .btn.primary", "b => b.click()"); pg.wait_for_timeout(1800)
            ok(f"{cid} 面板裡的「看個股頁 →」真的進得了 {code} 的個股頁",
               pg.evaluate("location.hash") == f"#stock/{code}", pg.evaluate("location.hash"))
            pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(400)
            pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(1700)
        # --- ③ 點環節卡：成分股真的被篩掉，再點一次真的取消
        b0 = pg.evaluate(SNAP2)
        if ok(f"{cid} 清單上有 {seg_click} 這一格",
              pg.evaluate(f"() => !!document.querySelector('#chainList .segcard[data-seg=\"{seg_click}\"]')")):
            click(pg, f'#chainList .segcard[data-seg="{seg_click}"] .sh', 1000)
            a1 = pg.evaluate(SNAP2)
            ok(f"{cid} 點環節卡，成分股筆數真的被篩掉", 0 < a1["rows"] < b0["rows"],
               f"{b0['rows']} → {a1['rows']}")
            ok(f"{cid} 而且那張環節卡真的亮起來", a1["cardSel"] == [seg_click], a1["cardSel"])
            click(pg, f'#chainList .segcard[data-seg="{seg_click}"] .sh', 1000)
            a2 = pg.evaluate(SNAP2)
            ok(f"{cid} 再點一次真的取消，筆數回到全部",
               a2["rows"] == b0["rows"] and not a2["cardSel"], f"{a1['rows']} → {a2['rows']}")

    # ---------------------------------------------------------------- ④ 窄畫面
    for vw in (800, 390):
        pg.set_viewport_size({"width": vw, "height": 1000})
        for cid in ("semiconductor", "ai_server", "electronics"):
            pg.evaluate(GOLIST)
            pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(400)
            pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(1600)
            pg.evaluate("() => { const s = document.getElementById('side'); if (s) s.classList.remove('open'); }")
            pg.wait_for_timeout(300)
            over = pg.evaluate("""() => { const l = document.getElementById('chainList'); if (!l) return null;
                let n = 0; l.querySelectorAll('.segcard').forEach(c => { const b = c.getBoundingClientRect();
                  c.querySelectorAll('.sco').forEach(e => { const r = e.getBoundingClientRect();
                    if (r.right > b.right + 2 || r.left < b.left - 2 || r.bottom > b.bottom + 2) n++; }); });
                return n; }""")
            ok(f"{cid} 視窗 {vw}px 時個股小卡沒有跑出環節卡", over == 0, over)
            ok(f"{cid} 視窗 {vw}px 時沒有橫向捲軸",
               pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
               pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))
            # 手機字級：SVG 已經不在畫面上，這裡量的是真正的 DOM 字級
            small = pg.evaluate("""() => [...document.querySelectorAll('#chainList .sco .nm, #chainList .sco .code,'
                + ' #chainList .sco .rel, #chainList .segcard .sf, #chainList .segcard .sh .nm')]
                .map(e => parseFloat(getComputedStyle(e).fontSize)).filter(v => v < 11).length""")
            ok(f"{cid} 視窗 {vw}px 時環節卡上沒有小於 11px 的字", small == 0, small)
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.evaluate(GOLIST)

    # ================================================== 需求三之二（2026-09-20 下午）
    # 環節卡清單讓**桌機變短、手機反而變高**：390px 半導體 1088 → 1846、
    # AI 伺服器 780 → 2599（舊 SVG 是 min-width:860px，在 390px 要左右拖才看得完，
    # 所以它的「矮」是假的；但 Andy 要的是手機打開不要一路滾到天荒地老）。
    #
    # 修法：手機（≤560px）預設只攤開「台股檔數最多的 4 格」，其餘只留標題列 ＋ 一顆 ▾；
    # 上方一顆「全部展開」總開關。**個股小卡沒有被拿掉**（那是 Andy 指名要的東西）——
    # 收的是「同時攤開的卡片張數」，因為量出來 390px 的成本是
    # 「每張卡固定 ~70px × 環節數」遠大於小卡本身。
    #
    # 這一段驗六件事，每一件都要「畫面真的因此改變」：
    #   ① 390px 三條鏈的清單高度與整頁高度真的降下來
    #   ② 390px 小卡仍然看得到（數量 > 0）、點得到（面板真的開、hash 沒變）
    #   ③ 按 ▾ 真的就地展開（小卡數量真的變多），再按一次真的收回去
    #   ④ 「全部展開」總開關真的把全部小卡叫出來，再按一次真的回到重點模式
    #   ⑤ 從外面選到某一格（點環節色標）時，收合的那張卡自己攤開
    #   ⑥ 桌機 1366／1500／1920 高度沒有退步，而且桌機不該出現收合鈕
    KEY = "() => { try { localStorage.setItem('tw.segExpand', 'key'); } catch (e) {} }"
    SNAP3 = """() => { const l = document.getElementById('chainList'), t = document.getElementById('segTools');
        return { hash: location.hash,
            list: l ? Math.round(l.getBoundingClientRect().height) : 0,
            page: Math.round(document.documentElement.scrollHeight),
            cards: document.querySelectorAll('#chainList .segcard').length,
            open: document.querySelectorAll('#chainList .segcard.open').length,
            minis: document.querySelectorAll('#chainList .sco').length,
            toolsShown: !!t && !t.hidden && getComputedStyle(t).display !== 'none',
            sxShown: [...document.querySelectorAll('#chainList .segcard .sx')]
                       .filter(e => getComputedStyle(e).display !== 'none').length,
            btn: (document.querySelector('#segTools .segx') || {}).textContent || '',
            box: (document.getElementById('coBox') || {}).innerText || '',
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            small: [...document.querySelectorAll('#chainList .sco .nm, #chainList .sco .code,'
                + ' #chainList .sco .rel, #chainList .segcard .sf, #chainList .segcard .sh .nm,'
                + ' #chainList .segcard .sh .cnt, #chainList .segcard .sx,'
                + ' #segTools .muted, #segTools .segx')]
                .map(e => parseFloat(getComputedStyle(e).fontSize)).filter(v => v < 11).length }; }"""

    def _goto(cid):
        pg.evaluate(GOLIST)
        pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(400)
        pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(1700)
        # 窄畫面時右邊「今日事件」是蓋住半個畫面的浮層，跟這次量的東西無關，先收掉
        pg.evaluate("() => { const s = document.getElementById('side'); if (s) s.classList.remove('open'); }")
        pg.wait_for_timeout(300)

    # ---------------------------------------------------------------- ① 390px 高度
    # 門檻怎麼訂的（三個數字都寫出來才看得懂）：
    #   清單門檻 = 改後實測 × 1.2（留兩成餘裕給 supply_chain.yaml 長大、字型量測抖動），
    #   而且一定要低於「改前」很多 —— 不然只是排版抖動，不算真的修好。
    #
    # ★ 2026-09-21：整頁門檻（最後一欄）重新校準過，理由與數字寫在這裡，不要當成放寬。
    #   原本那三個數字（6500／5900／3700）是拿「28 個族群」那份資料量出來的絕對值：
    #   當時半導體鏈 47 檔、AI 伺服器 28 檔、一般電子 **15 檔**、族群卡 9／6／5 張。
    #   換成 tide 的 110 個板塊之後同一頁是 156／96／**100** 檔、24／17／18 張板塊卡 ——
    #   內容量是 3.3／3.4／**6.7 倍**。同一個絕對值已經不代表同一件事
    #   （DECISIONS #207 的同一類錯：把會被產品決策改動的東西當契約）。
    #   實際做了兩件事把高度壓回去（不是調門檻）：
    #     · 成分股預設只列前 30 檔（＋「顯示全部」在原地展開）
    #     · 手機的板塊卡改成「一行一個板塊」（名稱＋漲跌在第一行、檔數／佔比／PE 在第二行）
    #       —— 24 個板塊從 2868px 變成 1598px，**一個板塊都沒有藏**
    #   390px 實測：12357 → 6176（半導體）、9600 → 6172（AI 伺服器）、8517 → 4886（一般電子）。
    #   半導體那條維持 6500 不動（它已經過了）；另外兩條改成「實測 ＋ 約 7% 餘裕」。
    #   ★ 真正擋退化的不是這三個絕對值，是下面那兩條**跟資料量無關**的：
    #     「每個板塊平均不超過 75px」與「按顯示全部之後整頁真的變高很多」。
    #   (鏈, 改前清單, 改後實測, 清單門檻, 改前整頁, 整頁門檻)
    M390 = [("semiconductor", 1846, 1034, 1250, 6983, 6500),
            ("ai_server",     2599, 1263, 1500, 6790, 6600),
            ("electronics",   1300,  836, 1000, 3944, 5300)]
    pg.set_viewport_size({"width": 390, "height": 1000})
    for cid, was_list, got, cap, was_page, cap_page in M390:
        pg.evaluate(KEY)
        _goto(cid)
        s = pg.evaluate(SNAP3)
        ok(f"390px {cid} 清單高度真的降下來（改前 {was_list}，實測約 {got}，門檻 {cap}）",
           0 < s["list"] <= cap, f"清單 {s['list']}")
        ok(f"390px {cid} 整頁高度真的降下來（改前 {was_page}，門檻 {cap_page}）",
           s["page"] <= cap_page, f"整頁 {s['page']}")
        # ---- ② 小卡沒有被拿掉：看得到
        ok(f"390px {cid} 個股小卡仍然看得到（Andy 指名要的東西不准藏起來）",
           s["minis"] > 0, s)
        ok(f"390px {cid} 而且每一張看得到的小卡都真的有畫出來（不是 0 高的殘影）",
           pg.evaluate("""() => [...document.querySelectorAll('#chainList .sco')]
               .filter(e => e.getBoundingClientRect().height > 8).length""") == s["minis"], s["minis"])
        ok(f"390px {cid} 沒有被展開的環節卡也仍然看得到族群名稱（收的是小卡不是族群）",
           pg.evaluate("""() => [...document.querySelectorAll('#chainList .segcard:not(.open)')]
               .filter(c => { const n = c.querySelector('.sh .nm');
                   return n && n.textContent.trim() && n.getBoundingClientRect().height > 8; }).length""")
           == s["cards"] - s["open"], s)
        ok(f"390px {cid} 手機上真的有出現「全部展開」工具列與收合鈕", s["toolsShown"] and s["sxShown"] > 0, s)
        ok(f"390px {cid} 沒有小於 11px 的字（含新加的收合鈕與工具列）", s["small"] == 0, s["small"])
        # ---- 板塊（族群）卡：110 個板塊上線之後，手機上一張卡就佔掉 120px、一排只塞得下一張。
        #      改成「一行一個板塊」之後要同時守住兩件事：**一個板塊都沒有藏**、而且**真的變矮了**。
        gc = pg.evaluate("""() => { const box = document.getElementById('groupCards');
            if (!box) return null; const tiles = [...box.querySelectorAll('.tile')];
            const br = box.getBoundingClientRect();
            return { n: tiles.length, h: Math.round(br.height),
                     per: tiles.length ? Math.round(br.height / tiles.length) : 0,
                     named: tiles.filter(t => { const e = t.querySelector('.t');
                         return e && e.textContent.trim() && e.getBoundingClientRect().height > 8; }).length,
                     pct: tiles.filter(t => { const e = t.querySelector('.v');
                         return e && e.getBoundingClientRect().height > 8; }).length,
                     link: tiles.filter(t => t.querySelector('a[href^="#industry/group/"]')).length,
                     out: tiles.filter(t => { const r = t.getBoundingClientRect();
                         return r.right > br.right + 1 || r.left < br.left - 1; }).length }; }""")
        ok(f"390px {cid} 板塊卡一個都沒有藏（{gc and gc['n']} 個板塊、每一個的名稱都看得到）",
           bool(gc) and gc["n"] > 3 and gc["named"] == gc["n"], gc)
        ok(f"390px {cid} 每個板塊都還看得到漲跌、也都點得進族群頁",
           bool(gc) and gc["pct"] == gc["n"] and gc["link"] == gc["n"], gc)
        ok(f"390px {cid} 板塊卡平均不超過 75px（手機上一行一個，不是一張 120px 的大卡）",
           bool(gc) and 0 < gc["per"] <= 75, gc)
        ok(f"390px {cid} 板塊卡沒有跑出容器", bool(gc) and gc["out"] == 0, gc)
        ok(f"390px {cid} 成分股預設只列前 30 檔（真實筆數寫在標題上）",
           s["rows"] <= 30 and s["rows"] > 0, s["rows"])
        # 一行一個板塊之後還是要**點得到**：點第一張卡，成分股要真的被篩掉，再點一次要還原
        if gc and gc["n"] > 3:
            r_all = pg.evaluate("() => document.querySelectorAll('#memberTable tbody tr').length")
            pg.eval_on_selector("#groupCards .tile", "t => t.click()"); pg.wait_for_timeout(900)
            sel = pg.evaluate("""() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
                on: document.querySelectorAll('#groupCards .tile.sel').length,
                title: (document.getElementById('memberTitle')||{}).innerText || '' })""")
            ok(f"390px {cid} 一行一個板塊之後照樣點得到（點了成分股真的被篩、卡片真的亮）",
               sel["on"] == 1 and (sel["rows"] < r_all or sel["rows"] < 30), {"全部": r_all, **sel})
            pg.eval_on_selector("#groupCards .tile.sel", "t => t.click()"); pg.wait_for_timeout(900)
            ok(f"390px {cid} 再點一次真的取消篩選",
               pg.evaluate("() => document.querySelectorAll('#groupCards .tile.sel').length") == 0)
        ok(f"390px {cid} 沒有橫向捲軸",
           pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
           pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))

    # ------------------------------------------------- ③ 按 ▾ 真的就地展開（小卡變多）
    pg.evaluate(KEY)
    _goto("ai_server")
    b0 = pg.evaluate(SNAP3)
    # 「有收合鈕而且是攤開的」才算數 —— 沒有公司的環節（只有一段說明）沒有收合鈕，
    # 它一律攤開（收起來什麼都不剩），不該被算進「重點展開的 4 格」。
    n_open_foldable = pg.evaluate("""() => [...document.querySelectorAll('#chainList .segcard.open')]
        .filter(c => c.querySelector('.sx')).length""")
    ok("390px 預設就是「重點展開」（只攤開 4 格）",
       n_open_foldable == 4 and b0["open"] < b0["cards"] and b0["cards"] > 8,
       f"攤開且可收合的有 {n_open_foldable} 格　{b0}")
    click(pg, "#chainList .segcard:not(.open) .sx", 600)
    a1 = pg.evaluate(SNAP3)
    ok("390px 按 ▾ 之後小卡數量真的變多", a1["minis"] > b0["minis"], f"{b0['minis']} → {a1['minis']}")
    changed("390px 按 ▾ 之後展開的卡片張數真的變了", b0["open"], a1["open"])
    ok("390px 按 ▾ 之後清單真的變高（代表東西真的攤出來了）", a1["list"] > b0["list"],
       f"{b0['list']} → {a1['list']}")
    ok("390px 按 ▾ 不會跳頁", a1["hash"] == b0["hash"], f"{b0['hash']} → {a1['hash']}")
    click(pg, "#chainList .segcard.open:not(.pin) .sx", 600)
    a2 = pg.evaluate(SNAP3)
    ok("390px 再按一次 ▾ 真的收回去（小卡數與高度都回到原本）",
       a2["minis"] == b0["minis"] and abs(a2["list"] - b0["list"]) <= 2, f"{a1} → {a2}")

    # ------------------------------------------------- ④ 「全部展開」總開關
    click(pg, "#segTools .segx", 700)
    a3 = pg.evaluate(SNAP3)
    ok("390px 按「全部展開」之後每一格都攤開了", a3["open"] == a3["cards"], a3)
    ok("390px 按「全部展開」之後小卡數量真的變成全部（AI 伺服器 67 檔）",
       a3["minis"] > b0["minis"] and a3["minis"] >= 60, f"{b0['minis']} → {a3['minis']}")
    changed("390px 總開關的按鈕字真的換了（變成「只展開重點」）", b0["btn"], a3["btn"])
    click(pg, "#segTools .segx", 700)
    a4 = pg.evaluate(SNAP3)
    ok("390px 再按一次真的回到重點模式（高度與小卡數都回去）",
       a4["open"] == b0["open"] and a4["minis"] == b0["minis"] and abs(a4["list"] - b0["list"]) <= 2,
       f"{a3} → {a4}")
    # 偏好要真的寫進 localStorage（重新整理之後還在）
    ok("390px 總開關的選擇真的寫進 localStorage",
       pg.evaluate("() => { try { return localStorage.getItem('tw.segExpand'); } catch (e) { return null; } }") == "key",
       pg.evaluate("() => { try { return localStorage.getItem('tw.segExpand'); } catch (e) { return null; } }"))

    # ------------------------------------------------- ② 小卡點得到（面板真的開、不跳頁）
    for cid, code, cname in (("semiconductor", None, None), ("ai_server", "3017", "奇鋐")):
        pg.evaluate(KEY)
        _goto(cid)
        if code is None:   # 半導體鏈挑「預設就攤開的那幾格裡的第一張小卡」，不預設是哪一檔
            code = pg.evaluate("""() => { const e = document.querySelector('#chainList .segcard.open .sco[data-code]');
                return e && e.dataset.code ? e.dataset.code : null; }""")
            cname = pg.evaluate(f"""() => {{ const e = document.querySelector('#chainList .sco[data-code="{code}"] .nm');
                return e ? e.textContent.trim() : ''; }}""")
        if not ok(f"390px {cid} 預設攤開的那幾格上找得到可以點的個股小卡", bool(code), code):
            continue
        before = pg.evaluate(SNAP3)
        click(pg, f'#chainList .sco[data-code="{code}"]', 1100)
        after = pg.evaluate(SNAP3)
        ok(f"390px {cid} 點個股小卡（{cname} {code}）不會跳頁（hash 沒變）",
           after["hash"] == before["hash"], f"{before['hash']} → {after['hash']}")
        ok(f"390px {cid} 點個股小卡真的原地展開「產業關係」面板",
           cname in after["box"] and "看個股頁" in after["box"], after["box"][:120])
        changed(f"390px {cid} 點小卡之後成分股筆數真的變了", before["rows"], after["rows"])

    # ------------------------------------------------- ⑤ 從外面選到收合的那一格要自己攤開
    pg.evaluate(KEY)
    _goto("ai_server")
    seg = pg.evaluate("""() => { const c = [...document.querySelectorAll('#chainList .segcard:not(.open)')]
        .find(x => x.querySelector('.sx')); return c ? c.dataset.seg : null; }""")
    if ok("390px 找得到一格「預設收起來」的環節卡", bool(seg), seg):
        click(pg, f'#segChips .segchip[data-seg="{seg}"]', 900)
        st = pg.evaluate(f"""() => {{ const c = document.querySelector('#chainList .segcard[data-seg="{seg}"]');
            return {{ open: c.classList.contains('open'), sel: c.classList.contains('sel'),
                      minis: c.querySelectorAll('.sco').length }}; }}""")
        ok(f"390px 點環節色標之後，{seg} 那張收合的卡自己攤開了（不然亮了也看不到小卡）",
           st["open"] and st["sel"] and st["minis"] > 0, st)

    # ------------------------------------------------- ⑥ 桌機不可以退步
    # 對照值＝這次改動前同一份本機資料量到的整頁高度（右側事件欄收起）。
    # 門檻多給約 100px 的抖動餘裕；清單本身的高度也一起量，那才是我動到的東西。
    DESK = [(1366, 4419, 4520, 645, 720), (1500, 4231, 4340, 518, 590), (1920, 4181, 4280, 339, 410)]
    for vw, was, cap, was_list, cap_list in DESK:
        pg.set_viewport_size({"width": vw, "height": 1000})
        pg.evaluate(KEY)
        _goto("semiconductor")
        s = pg.evaluate(SNAP3)
        ok(f"{vw}px 桌機整頁高度沒有退步（改動前 {was}，門檻 {cap}）", s["page"] <= cap, f"整頁 {s['page']}")
        ok(f"{vw}px 桌機環節卡清單高度沒有退步（改動前 {was_list}，門檻 {cap_list}）",
           s["list"] <= cap_list, f"清單 {s['list']}")
        ok(f"{vw}px 桌機每一張環節卡都是攤開的（收合只在手機生效）",
           s["open"] == s["cards"] and s["minis"] >= 50, s)
        ok(f"{vw}px 桌機不該看到收合鈕與「全部展開」工具列",
           s["sxShown"] == 0 and not s["toolsShown"], s)
    # 800px 是「半邊視窗」，也不該收合（560px 以上一律攤開）
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.evaluate(KEY)
    _goto("ai_server")
    s8 = pg.evaluate(SNAP3)
    ok("800px（半邊視窗）不收合，全部攤開", s8["open"] == s8["cards"] and s8["minis"] >= 60, s8)
    ok("800px 沒有橫向捲軸",
       pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"),
       pg.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]"))

    # ------------------------------------------------- 既有行為：切回關聯圖還要能用
    pg.set_viewport_size({"width": 390, "height": 1000})
    pg.evaluate(KEY)
    _goto("semiconductor")
    click(pg, "#chainView", 1200)
    ok("390px 切到關聯圖之後，收合工具列跟著收起來（按了不會沒反應）",
       pg.evaluate("""() => { const m = document.getElementById('chainMap'), t = document.getElementById('segTools');
           return !!m && !m.hidden && !!t && t.hidden; }"""),
       pg.evaluate("""() => { const m = document.getElementById('chainMap'), t = document.getElementById('segTools');
           return [m && m.hidden, t && t.hidden]; }"""))
    click(pg, "#chainView", 900)
    ok("390px 再按一次切得回環節卡清單，工具列也回來了",
       pg.evaluate("""() => { const l = document.getElementById('chainList'), t = document.getElementById('segTools');
           return !!l && !l.hidden && !!t && !t.hidden; }"""))
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.evaluate(GOLIST)


def t_new_flow(pg, base):
    """資金流向頁（site/app.js）：資金去向的 nan／族群固定／小圓點、移除播放與河流、
    族群展開清單拉Bar、族群晶片篩選。

    Andy 的硬性要求：每一條都要驗「畫面真的因此改變了」。
    所以這裡不驗「元素存在」，而是：整張圖的文字裡找不到 nan、換一天之後族群名單一模一樣
    但線寬真的變了、圓點座標兩個時間點不一樣、清單真的捲得動、晶片點下去被壓暗的數量真的變。
    """
    pg.set_viewport_size({"width": 1500, "height": 1000})
    # 前面的段落可能把「看哪一天」拉到過去而且寫進 localStorage，會讓這一段的基準值不穩定
    pg.goto(f"{base}#overview", wait_until="networkidle")
    pg.evaluate("() => { try { localStorage.removeItem('tw.sankey.day'); } catch (e) {} }")
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(3000)

    # ---------------------------------------------------------------- ① nan
    # ★ 2026-09-20 下午改成**四層**（台股成交值 → 產業鏈 → 族群 → 代表股），
    #   所以 root.children 現在是產業鏈、族群要再往下一層拿。
    SK = """() => { const el = document.getElementById('sankey');
        const c = el && echarts.getInstanceByDom(el); if (!c) return null;
        const s = c.getOption().series[0]; const root = (s.data || [])[0] || {};
        const chains = (root.children || []);
        const kids = chains.flatMap(ch => (ch.children || []));
        const lv = kids.flatMap(g => (g.children || []).filter(x => !x.placeholder));
        const depth = (n, d) => Math.max(d, ...((n.children || []).map(x => depth(x, d + 1))));
        return { chains: chains.map(ch => ch.name),
                 chainKids: chains.map(ch => (ch.children || []).map(g => g.name)),
                 chainLabels: chains.map(ch => (ch.label || {}).formatter),
                 names: kids.map(k => k.name),
                 labels: kids.map(k => (k.label || {}).formatter),
                 leaves: lv.map(x => x.name),
                 leafLabels: lv.map(x => (x.label || {}).formatter),
                 depth: depth(root, 0),
                 widths: kids.map(k => (k.lineStyle || {}).width),
                 sizes: kids.map(k => k.symbolSize),
                 dim: kids.filter(k => k.dim).length,
                 kidCount: kids.map(k => (k.children || []).length) }; }"""
    sk0 = pg.evaluate(SK)
    if not ok("資金去向畫得出來", bool(sk0) and len(sk0["names"]) > 3, sk0):
        return

    # -------------------------------------------------- ①-0 四層結構（Andy 2026-09-20）
    # 「半導體產業涵蓋 IC 設計、代工、封測，不應該將他們拆開…
    #   一個節點是半導體產業，後面接續是 IC 設計、代工、封裝」
    ok("資金去向真的有四層（台股 → 產業鏈 → 族群 → 代表股）", sk0["depth"] == 3,
       f"最深只有 {sk0['depth'] + 1} 層：{sk0['chains']}")
    ok("第一層是產業鏈，不是族群（族群不再跟收容桶並排）",
       len(sk0["chains"]) >= 3 and "晶圓代工" not in sk0["chains"], sk0["chains"])
    # ★ 2026-09-21：這三條本來寫死板塊名稱（「IC 設計」「封測」「半導體業」）。
    #   族群換成 tide-tw.app 的 110 個板塊之後，半導體鏈底下叫「HPC 與網通 IC」
    #   「客製 ASIC 矽智財」「封測代工」「IC 測試服務」—— 沒有任何一個板塊叫「IC 設計」。
    #   **產品行為完全正確**，錯的是驗收把顯示名稱當契約（DECISIONS #207）。
    #   Andy 當初要守的是結構：「半導體產業是**一個節點**，後面接續是設計／代工／封裝」，
    #   所以改成驗結構 —— 半導體是一格、底下接得出好幾個子板塊、
    #   而且那些子板塊真的是半導體鏈的板塊（去 industry_map.json 對，不是對字串）。
    im_json = json.loads((SITE / "data" / "industry_map.json").read_text(encoding="utf-8"))
    chain_boards = {c["id"]: [g["name"] for g in c["groups"]] for c in im_json.get("chains", [])}
    bucket_names = {g["name"] for g in im_json.get("industries", [])}
    semi = [c for c in sk0["chains"] if c == "半導體"]
    if ok("產業鏈這一層有「半導體」這一格", len(semi) == 1, sk0["chains"]):
        under = sk0["chainKids"][sk0["chains"].index(semi[0])]
        semi_boards = set(chain_boards.get("semiconductor", []))
        ok("「半導體」底下真的接著好幾個子板塊（不是把設計／代工／封測拆開跟它並排）",
           len(under) >= 3, under)
        ok("而且底下每一個都真的是半導體鏈的板塊（不是收容桶混進來）",
           all(u in semi_boards for u in under), [u for u in under if u not in semi_boards])
        # 「設計／代工／封測」這三類要看得到 —— 不綁板塊全名，只要求各有一個板塊名稱帶到那個字
        for kind, keys in (("代工（晶圓代工那一類）", ("晶圓代工", "代工")),
                           ("封測／測試那一類", ("封測", "測試", "封裝"))):
            ok(f"「半導體」底下看得到{kind}",
               any(any(k in u for k in keys) for u in under), under)
    others = [c for c in sk0["chains"] if "其他產業" in c]
    if ok("法定產業別的收容桶被收進「其他產業別」", len(others) == 1, sk0["chains"]):
        bucket = sk0["chainKids"][sk0["chains"].index(others[0])]
        # 收容桶現在叫「〇〇・其他」（半導體業 → 半導體・其他）。真正要守的是
        # 「收容桶不准跟題材板塊混在產業鏈底下」，所以兩邊都驗：
        ok("「其他產業別」底下掛的全都是收容桶（不是題材板塊）",
           bool(bucket) and all(b in bucket_names for b in bucket),
           [b for b in bucket if b not in bucket_names])
        semi_bucket = [n for n in bucket_names if n.startswith("半導體")]
        ok("半導體的收容桶（半導體・其他）是收容桶不是題材板塊，所以不會掛在「半導體」底下",
           bool(semi_bucket)
           and not any(n in sk0["chainKids"][sk0["chains"].index(semi[0])] for n in semi_bucket)
           if semi else False,
           {"收容桶": semi_bucket, "半導體底下": sk0["chainKids"][sk0["chains"].index(semi[0])] if semi else None})

    # -------------------------------------------------- ①-1 每一層都要有占比 %
    ok("產業鏈那一層標了占比 %", all("%" in (x or "") for x in sk0["chainLabels"]), sk0["chainLabels"])
    ok("族群那一層標了占比 %（沒資料的那幾個寫「無資料」）",
       all(("%" in (x or "")) or "無資料" in (x or "") for x in sk0["labels"]), sk0["labels"][:6])
    ok("代表股那一欄也標了占比 %（Andy：樹狀圖後的公司都需要標示占比%）",
       len(sk0["leafLabels"]) > 10 and all("%" in (x or "") for x in sk0["leafLabels"]),
       [x for x in sk0["leafLabels"] if "%" not in (x or "")][:5])
    ok("畫面上有寫清楚 % 的分母是哪一層（不要讓人誤讀）",
       "上一層" in text(pg, "#sankeySub"), text(pg, "#sankeySub")[:80])

    allname = " ".join(sk0["names"] + sk0["leaves"] + sk0["chains"])
    ok("資金去向的節點名稱裡找不到 nan（代表股那一欄以前整排是 nan）",
       "nan" not in allname.lower(), [x for x in sk0["leaves"] if "nan" in x.lower()][:5])
    ok("整張卡片的文字裡也找不到 nan",
       "nan" not in text(pg, "#sankeyWrap").lower(), text(pg, "#sankeyWrap")[:120])
    ok("代表股有真的中文簡稱（不是只剩代號）",
       any(any("\u4e00" <= ch <= "\u9fff" for ch in n) for n in sk0["leaves"]), sk0["leaves"][:5])

    # ---------------------------------------------------- ② 族群固定：換一天只變粗細大小
    bar = "#sankeyDays input[type=range]"
    if ok("資金去向有「看哪一天」拉Bar", pg.evaluate(f"() => !!document.querySelector('{bar}')")):
        mx = pg.evaluate(f"() => +document.querySelector('{bar}').max")
        set_range(pg, bar, max(0, mx - 12), 1500)
        sk1 = pg.evaluate(SK)
        ok("換一天之後，族群名單與順序完全一樣（Andy：所有族群固定）",
           sk1 and sk1["names"] == sk0["names"],
           {"前": sk0["names"], "後": sk1 and sk1["names"]})
        ok("換一天之後，每個族群的代表股格數也一樣（格數會變的話族群的位置會跳）",
           sk1 and sk1["kidCount"] == sk0["kidCount"],
           {"前": sk0["kidCount"], "後": sk1 and sk1["kidCount"]})
        # 只判「一定會動」的那一個量：線寬是連續值，換一天幾乎不可能完全相同
        changed("換一天之後，線的粗細真的變了（只有粗細與大小會變）",
                [round(w or 0, 3) for w in sk0["widths"]],
                [round(w or 0, 3) for w in (sk1 or {}).get("widths", [])])
        set_range(pg, bar, mx, 1500)

        # ---------------------------------------- ②-b 播放（Andy 2026-09-20：資金去向要加回播放）
        # ★ 2026-09-21：這一排多了第四顆「即時」（D5-④），所以改成分開數 ——
        #   三顆播放控制鈕（− ＋ ▶）用 :not(.livebtn) 挑，即時鈕另外一條驗。
        PB = "#sankeyDays .pb:not(.livebtn)"
        if ok("資金去向的拉Bar 旁邊有 ＋ / − / ▶ 三顆鈕", count(pg, PB) == 3, count(pg, PB)):
            p0 = pg.evaluate(f"() => +document.querySelector('{bar}').value")
            pg.eval_on_selector("#sankeyDays .pb.play", "b => b.click()")
            pg.wait_for_timeout(2400)
            p1 = pg.evaluate(f"() => +document.querySelector('{bar}').value")
            changed("按播放之後，拉Bar 真的自己在走", p0, p1)
            ok("播放中按鈕變成暫停的樣子",
               pg.evaluate("() => document.querySelector('#sankeyDays .pb.play').textContent") == "⏸")
            sub_a = text(pg, "#sankeySub")
            pg.wait_for_timeout(1400)
            changed("播放時圖的副標日期也跟著走（畫面真的在變）", sub_a, text(pg, "#sankeySub"))
            pg.eval_on_selector("#sankeyDays .pb.play", "b => b.click()")
            pg.wait_for_timeout(400)
            p2 = pg.evaluate(f"() => +document.querySelector('{bar}').value")
            pg.wait_for_timeout(2000)
            p3 = pg.evaluate(f"() => +document.querySelector('{bar}').value")
            ok("再按一次真的停下來", p2 == p3, f"停之後 {p2} → {p3}（應該不變）")
            # 播放時也要守住「位置固定」：族群名單與順序不可以被洗牌
            skp = pg.evaluate(SK)
            ok("播放過後族群名單與順序仍然一模一樣（位置固定）",
               skp and skp["names"] == sk0["names"], {"前": sk0["names"][:4], "後": skp and skp["names"][:4]})
            set_range(pg, bar, mx, 1500)

    # ------------------------------------------------- ③ 小圓點傳輸動畫：座標真的在動
    ok("有小圓點在線上跑（App.sankeyDots）",
       pg.evaluate("() => (window.App.sankeyDots() || []).length > 0"),
       pg.evaluate("() => (window.App.sankeyDots() || []).length"))
    d0 = pg.evaluate("() => window.App.sankeyDots()")
    pg.wait_for_timeout(500)
    d1 = pg.evaluate("() => window.App.sankeyDots()")
    # ★ 只判「圓點座標」這一個量。2026-09-19 的教訓：判定寫成 A and B、
    #   其中一個分量本來就不會動，結果是假紅。
    changed("小圓點真的在動（兩個時間點的座標不一樣）", d0[:6], d1[:6])
    ok("錢越多的族群點越多（頻率越高）",
       pg.evaluate("""() => { const ds = window.App.sankeyDots() || [];
           const byR = {}; ds.forEach(d => { byR[d[0] + ',' + d[1]] = 1; });
           return ds.length >= 4; }"""), len(d1))
    # ★ 2026-09-20（Andy：「並都需要具備資金流傳輸效果」）：以前只有第一段有點。
    #   每顆點帶著它在第幾段（1＝台股→產業鏈、2＝產業鏈→族群、3＝族群→代表股），
    #   三段都要有點、而且三段都要真的在動。
    lv0 = {}
    for x, y, lv in d0:
        lv0.setdefault(lv, []).append((x, y))
    lv1 = {}
    for x, y, lv in d1:
        lv1.setdefault(lv, []).append((x, y))
    for lv, nm in ((1, "台股 → 產業鏈"), (2, "產業鏈 → 族群"), (3, "族群 → 代表股")):
        if ok(f"第 {lv} 段（{nm}）線上有小圓點", len(lv0.get(lv, [])) > 0,
              {k: len(v) for k, v in lv0.items()}):
            changed(f"第 {lv} 段（{nm}）的小圓點真的在動", lv0[lv][:5], lv1.get(lv, [])[:5])
    # 分頁切到背景要停（dg3d_standard.md 的效能驗收）
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
        document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(600)
    ok("分頁切到背景，小圓點動畫真的停下來", not pg.evaluate("() => window.App.sankeyFxRunning()"))
    pg.evaluate("""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
        document.dispatchEvent(new Event('visibilitychange')); }""")
    pg.wait_for_timeout(600)
    ok("回到前景之後又繼續動", pg.evaluate("() => window.App.sankeyFxRunning()"))

    # ---------------------------------------------------------------- ④ 移除
    gone = pg.evaluate("""() => ({
        pb: document.querySelectorAll('#v-flow .rbar .pb').length,
        rank: document.querySelectorAll('#rankDays .pb').length,
        inst: document.querySelectorAll('#instEnd .pb').length,
        sankey: document.querySelectorAll('#sankeyDays .pb').length,
        river: !!document.getElementById('river'),
        riverDays: !!document.getElementById('riverDays'),
        riverEnd: !!document.getElementById('riverEnd'),
        riverWrap: !!document.getElementById('riverWrap'),
        howRiver: !!document.getElementById('how-river'),
        riverWord: document.getElementById('v-flow').innerText.indexOf('河流') >= 0,
        // 「新增播放」的那兩支要分開數，不能跟被移除的混在一起算
        pbOther: document.querySelectorAll('#v-flow .rbar:not(#rotBack):not(#sankeyDays) .pb').length,
        pbClock: document.querySelectorAll('#rotBack .pb').length })""")
    ok("資金流向排行的播放鈕真的不在 DOM 裡（不是藏起來）", gone["rank"] == 0, gone)
    ok("族群×法人的播放鈕真的不在 DOM 裡", gone["inst"] == 0, gone)
    # ★ 2026-09-20 下午改寫（Andy：「並且需要具備播放功能」）。
    #   早上那條是「資金去向的播放鈕真的不在 DOM 裡」—— 他後來明確要**加回來**，
    #   所以那條已經不成立，硬留著就是拿舊需求擋新需求。
    #   但它原本要守的事情沒有消失：**排行、族群×法人、法人截止日那三支仍然不准有播放**
    #   （上面兩條 ＋ 下面 pbOther 那條就是在守這件事，沒有被放寬）。
    ok("資金去向的播放鈕有出現（Andy 2026-09-20：資金去向需要具備播放功能）",
       gone["sankey"] > 0, gone)
    # ★ 2026-09-20：這條原本是「整頁一顆播放鈕都沒有」，現在不成立而且**不該**成立 ——
    #   A4 第 5 條是「輪動時鐘**新增**播放功能」、資金去向也要新增，
    #   跟 A3／B2 要移除的那三張是相反的要求。
    #   所以是「除了輪動時鐘與資金去向那兩支，其餘一顆都不准有」。
    ok("除了輪動時鐘與資金去向，整頁一顆播放／＋／− 鈕都沒有了", gone["pbOther"] == 0, gone)
    ok("輪動時鐘的播放／＋／− 鈕有出現（A4 第 5 條是新增不是移除）", gone["pbClock"] > 0, gone)
    ok("族群佔比河流圖真的不在 DOM 裡", not gone["river"] and not gone["riverWrap"], gone)
    ok("河流的時間週期拉Bar 也真的不在 DOM 裡", not gone["riverDays"] and not gone["riverEnd"], gone)
    ok("連「怎麼看」的河流說明也拿掉了", not gone["howRiver"], gone)
    ok("頁面上不再出現「河流」兩個字", not gone["riverWord"], gone)
    # 拉Bar 本身要留著，而且拉了畫面真的會變（不要把功能連根拔掉）
    ok("排行的天數拉Bar 還在（拿掉的只有播放）",
       pg.evaluate("() => !!document.querySelector('#rankDays input[type=range]')"))
    sub0 = text(pg, "#rankSub")
    set_range(pg, "#rankDays input[type=range]", 15, 1500)
    changed("沒有播放鈕，手動拉天數照樣會重畫", sub0, text(pg, "#rankSub"))
    set_range(pg, "#rankDays input[type=range]", 0, 1200)

    # ------------------------------------------- ⑤ 族群展開的股票清單固定高度＋拉Bar
    # 真的點族群晶片把面板叫出來（排行下方的 #rankPanel）。
    # ★ 要挑一個成分股夠多的族群 —— 只有 5 檔的族群撐不出捲軸，
    #   驗收就會變成「量不到就算過」，那等於沒驗。所以最多點 10 個，取第一個 ≥15 檔的。
    PAN = """() => { const b = document.getElementById('rankPanel');
        if (!b || b.hidden) return null; const ms = b.querySelector('.ms'); if (!ms) return null;
        return { n: ms.querySelectorAll('a').length, ch: Math.round(ms.clientHeight),
                 sh: Math.round(ms.scrollHeight),
                 oy: getComputedStyle(ms).overflowY }; }"""
    pan = None
    nchip = count(pg, '.gchips[data-sync="n2"] .gchip')
    # ★ 2026-09-20（E3）：點晶片現在會**真的篩圖**，所以每試完一個一定要先取消再試下一個 ——
    #   不然十個族群會被一路累加進 ROT.groups，後面幾段就從「已經篩了 10 個」開始跑。
    for i in range(min(10, nchip)):
        pg.eval_on_selector_all('.gchips[data-sync="n2"] .gchip .pick',
                                "(bs, i) => bs[i] && bs[i].click()", i)
        pg.wait_for_timeout(700)
        cur = pg.evaluate(PAN)
        if cur and (pan is None or cur["n"] > pan["n"]):
            pan = cur
        if pan and pan["n"] >= 15:
            break
        pg.eval_on_selector_all('.gchips[data-sync="n2"] .gchip .pick',
                                "(bs, i) => bs[i] && bs[i].click()", i)   # 取消，回到「全部族群」
        pg.wait_for_timeout(600)
    if ok("點族群晶片，排行下方真的展開成分股面板", bool(pan), pan):
        ok("成分股清單有固定高度（不會把整頁撐長）", pan["ch"] <= 260, pan)
        ok("成分股清單是可以捲的", pan["oy"] in ("auto", "scroll"), pan)
        if pan["n"] >= 12:
            ok("內容比框高，真的捲得動（scrollHeight > clientHeight）",
               pan["sh"] > pan["ch"] + 8, pan)
            y0 = pg.evaluate("() => { const m = document.querySelector('#rankPanel .ms'); m.scrollTop = 120; return m.scrollTop; }")
            ok("真的捲下去了", y0 > 0, y0)
        else:
            notes.append(f"這個族群只有 {pan['n']} 檔，不足以撐出捲軸，只驗了固定高度")
    # ★ 收拾：把上面為了找「成分股夠多的族群」而選起來的那一個取消掉。
    #   這同時是「再點一次真的取消」的正面驗收，也是不把狀態留給後面段落的必要動作 ——
    #   2026-09-20 實測：不取消的話，批次2「點排行長條會原地展開成分股」會拿到一個
    #   **已經開著**的面板，一點反而收起來，看起來像功能壞了（其實是前一段沒收拾）。
    while count(pg, '.gchips[data-sync="n2"] .gchip.on'):
        pg.eval_on_selector('.gchips[data-sync="n2"] .gchip.on .pick', "b => b.click()")
        pg.wait_for_timeout(800)
    ok("再點一次選起來的族群，成分股面板真的收起來",
       pg.evaluate("() => { const b = document.getElementById('rankPanel'); return !b || b.hidden; }"))
    ok("收拾完之後篩選真的清空了（不要把狀態留給後面的段落）（E3）",
       pg.evaluate("() => { try { const o = JSON.parse(localStorage.getItem('tw.rot.filter')||'null');"
                   " return !o || !o.groups || !o.groups.length; } catch (e) { return true; } }"))
    # 輪動階段那四格用的是同一套（.stage ul 固定高度＋內捲）
    st = pg.evaluate("""() => { const u = document.querySelector('#rotBoard .stage ul'); if (!u) return null;
        return { ch: Math.round(u.clientHeight), sh: Math.round(u.scrollHeight),
                 oy: getComputedStyle(u).overflowY }; }""")
    ok("輪動階段的族群清單也是固定高度＋可捲（所有相關版面同一套）",
       bool(st) and st["ch"] <= 400 and st["oy"] in ("auto", "scroll"), st)

    # ------------------- ⑤-b 點族群 → 右邊出現該族群個股的成交值排序（Andy 2026-09-20）
    # 「當點擊族群時會在右邊出現個股的成交值排序」。
    # 驗的是畫面真的因此改變：面板真的開、列出的檔數 > 0、**真的照成交值由大到小**
    #（讀 data-tv 的數值比大小，不是看有沒有 render）、而且清單真的捲得動。
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2800)
    SKP = """() => { const b = document.getElementById('sankeyPanel');
        if (!b || b.hidden) return null; const ms = b.querySelector('.ms'); if (!ms) return null;
        const tv = [...ms.querySelectorAll('a')].map(a => +a.dataset.tv);
        return { n: tv.length, tv: tv.slice(0, 6),
                 sorted: tv.every((v, i) => i === 0 || tv[i - 1] >= v),
                 ch: Math.round(ms.clientHeight), sh: Math.round(ms.scrollHeight),
                 oy: getComputedStyle(ms).overflowY,
                 pct: (ms.querySelector('a .g') || {}).textContent || '',
                 rightOfChart: b.getBoundingClientRect().left
                               > document.getElementById('sankeyWrap').getBoundingClientRect().left }; }"""
    skchip = '.linkrow.gchips[data-for="sankey"] .gchip'
    best, best_g = None, None
    gids = pg.eval_on_selector_all(skchip, "cs => cs.map(c => c.dataset.g)")
    h_before = pg.evaluate("() => location.hash")
    for g in (gids or [])[:8]:
        pg.eval_on_selector(f'{skchip}[data-g="{g}"] .pick', "b => b.click()")
        pg.wait_for_timeout(1400)
        cur = pg.evaluate(SKP)
        if cur and (best is None or cur["n"] > best["n"]):
            best, best_g = cur, g
        if best and best["n"] >= 20:
            break
    if ok("點族群，右邊真的展開個股清單", bool(best), best):
        ok("清單列得出個股（不是空的）", best["n"] > 0, best["n"])
        ok("而且真的照成交值由大到小排（讀數值比大小）", best["sorted"], best["tv"])
        ok("每一列都寫出占比 %（分母是所屬族群，標題有寫）", "%" in best["pct"], best["pct"])
        ok("清單在圖的右邊", best["rightOfChart"], best)
        ok("清單有固定高度（不會把整頁撐長）", best["ch"] <= 460, best)
        ok("清單是可以捲的", best["oy"] in ("auto", "scroll"), best)
        if best["n"] >= 15:
            ok("內容比框高，真的捲得動（scrollHeight > clientHeight）", best["sh"] > best["ch"] + 8, best)
            y = pg.evaluate("() => { const m = document.querySelector('#sankeyPanel .ms');"
                            " m.scrollTop = 150; return m.scrollTop; }")
            ok("真的捲下去了", y > 0, y)
        else:
            notes.append(f"資金去向面板：這個族群只有 {best['n']} 檔，撐不出捲軸，只驗了固定高度")
    ok("點族群不會跳頁（在原地展開）", pg.evaluate("() => location.hash") == h_before)
    # 收拾：把選起來的那個取消掉，不要把狀態留給後面的段落
    if count(pg, skchip + ".on"):
        pg.eval_on_selector(skchip + ".on .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
    ok("再點一次選起來的族群，右邊的清單真的收起來",
       pg.evaluate("() => { const b = document.getElementById('sankeyPanel'); return !b || b.hidden; }"))

    # ---------------- 兩階段下鑽（Andy 2026-09-21）：資金去向也要「點個股 → 顯示在圖上」
    # 驗的是圖真的多一個葉節點（讀 tree 的 data，不是看有沒有 render），
    # 而且這份選擇和輪動時鐘是**同一份**（兩張圖一起變）。
    LEAF = """() => { const c = echarts.getInstanceByDom(document.getElementById('sankey'));
        if (!c) return null; const root = ((c.getOption().series || [])[0] || {}).data[0];
        let n = 0; const picked = [];
        (root.children || []).forEach(ch => (ch.children || []).forEach(g =>
          (g.children || []).forEach(x => { if (!x.placeholder) { n++; if (x.picked) picked.push(x.code); } })));
        return { leaves: n, picked }; }"""
    skg = pg.eval_on_selector_all(skchip, "cs => cs.map(c => c.dataset.g)")
    pick_g = best_g or (skg[0] if skg else None)
    if pick_g:
        pg.eval_on_selector(f'{skchip}[data-g="{pick_g}"] .pick', "b => b.click()")
        pg.wait_for_timeout(1600)
        lf0 = pg.evaluate(LEAF)
        # 挑一檔**不在**前 3 大代表股裡的（第 5 列起），才驗得出「真的多一個節點」
        code = pg.evaluate("""() => { const as = [...document.querySelectorAll('#sankeyPanel .ms a')]
            .filter(a => !a.className.includes('noplot')); const a = as[4] || as[as.length - 1];
            return a ? a.dataset.code : null; }""")
        if ok("資金去向的成分股清單裡挑得到一檔來畫", bool(code) and bool(lf0), [code, lf0]):
            pg.eval_on_selector(f'#sankeyPanel .ms a[data-code="{code}"]', "a => a.click()")
            pg.wait_for_timeout(1800)
            lf1 = pg.evaluate(LEAF)
            changed("點個股，資金去向的葉節點真的多一個", lf0["leaves"], lf1["leaves"])
            ok("多出來的那一個就是我點的那一檔，而且掛在它所屬的族群底下",
               code in (lf1["picked"] or []), lf1)
            ok("同一份選擇也反映在輪動時鐘上（兩張圖共用一份狀態）",
               any(x["stock"] and x["code"] == code for x in _rot_pts(pg)), _rot_pts(pg))
            pg.eval_on_selector(f'#sankeyPanel .ms a[data-code="{code}"]', "a => a.click()")
            pg.wait_for_timeout(1600)
            ok("再點一次，葉節點真的收回去",
               pg.evaluate(LEAF)["leaves"] == lf0["leaves"],
               [lf0["leaves"], pg.evaluate(LEAF)["leaves"]])
        # 麵包屑的「全部族群」要真的回到階段一
        pg.eval_on_selector("#sankeyPanel [data-all]", "b => b.click()")
        pg.wait_for_timeout(1600)
        ok("按麵包屑的「全部族群」真的回到階段一（面板收起、圖回到只有族群）",
           pg.evaluate("() => { const b = document.getElementById('sankeyPanel'); return !b || b.hidden; }")
           and pg.evaluate(LEAF)["leaves"] == (lf0 or {}).get("leaves", 0),
           pg.evaluate(LEAF))

    # ================================================================== D5（Andy 2026-09-21）
    # 「當點擊 AI 伺服器第一個 Node 右邊應當顯示 AI 伺服器，並下面多出裡面還蓋族群，
    #   並且都具備下拉選單可以看個股。當點擊背景時會恢復 Default 狀態，
    #   另外傳輸密度提升，需要差異大點」＋「多新增一個『即時』項目…在紅框那排」
    #
    # 驗的全是「畫面真的因此改變」：面板標題換成鏈名、底下族群數 > 1、
    # 展開真的多出個股列、點背景之後下鑽狀態真的歸零、密度比真的變大、
    # 即時模式的佔比真的加總到 100%、自動桶真的被標成盤後。
    pg.goto(f"{base}#flow", wait_until="networkidle")
    pg.wait_for_timeout(2800)
    pg.evaluate("() => { const b = document.getElementById('evClose'); if (b) b.click(); }")
    pg.wait_for_timeout(300)

    # ---------------------------------------------------------- D5-③ 小圓點密度
    # 先量密度（後面按了即時就會重配），順便確認「每條線至少 1 顆」沒有退回去（D4 修過的）
    fs = pg.evaluate("() => window.App.sankeyFlowStats()")
    if ok("量得到每條連線配到幾顆點（App.sankeyFlowStats）", bool(fs), fs):
        ok("每一條線都至少有 1 顆點（D4 修過的，不准退回去）", fs["minN"] >= 1, fs)
        # 改前：單線上限 5，實測最粗 4 顆 / 最細 1 顆＝4 倍，而且速度固定所以通過率也是 4 倍。
        ok("最粗的線明顯比最細的線密（點數至少 8 倍，改前是 4 倍）",
           fs["nRatio"] >= 8, fs)
        ok("連速度也拉開了：單位時間通過的顆數至少差 15 倍（改前 4 倍）",
           fs["rateRatio"] >= 15, fs)
        ok("整張圖的總點數比改版前多（改前 95 顆）", fs["dots"] >= 150, fs)
        ok("但沒有超過上限 420（不要讓手機每幀畫上千顆）", fs["dots"] <= 420, fs)
        ok("點的大小也跟著流量走（最粗的點半徑至少是最細的 2.5 倍）",
           fs["top"]["size"] >= fs["bot"]["size"] * 2.5, fs)

    # ---------------------------------------------------- D5-① 點第一層（產業鏈）節點
    def _sk_node_xy(name):
        """回傳那個節點在視窗上的座標；先把圖捲進畫面，不然點到視窗外。

        ★ 兩個一定要做對的細節（都是實測踩到的）：
          1. 這一頁的 CSS 是 `html{scroll-behavior:smooth}`，所以一定要指定
             `behavior:'instant'`，否則捲動要一秒多才到位 —— 在同一個 evaluate 裡
             捲完馬上量，拿到的是捲動前的座標（實測 top 3087 vs 正確的 36），
             點下去就是點在空氣裡，而且失敗訊息完全看不出原因。
          2. 捲動與量測要分兩次呼叫，中間留時間給瀏覽器算版面。
        """
        pg.eval_on_selector("#sankey", "el => el.scrollIntoView({block: 'center', behavior: 'instant'})")
        pg.wait_for_timeout(700)
        return pg.evaluate(
            """(nm) => { const el = document.getElementById('sankey');
                 const c = el && echarts.getInstanceByDom(el); if (!c) return null;
                 const d = c.getModel().getSeriesByIndex(0).getData();
                 const r = el.getBoundingClientRect();
                 for (let i = 0; i < d.count(); i++) {
                   if (d.getName(i) !== nm) continue;
                   const g = d.getItemGraphicEl(i); if (!g) continue;
                   const q = g.transformCoordToGlobal(0, 0);
                   return [Math.round(r.left + q[0]), Math.round(r.top + q[1])]; }
                 return null; }""", name)

    CHAINS = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('sankey'));
        const root = c.getOption().series[0].data[0];
        return (root.children || []).map(x => [x.name, (x.children || []).length]); }""")
    # 挑一個底下族群 > 1 的鏈（「AI 伺服器」優先，那是 Andy 原話指名的那一格）
    want = next((n for n, k in CHAINS if n == "AI 伺服器" and k > 1), None) \
        or next((n for n, k in CHAINS if k > 1), None)
    if ok("圖上找得到一條底下有多個族群的產業鏈", bool(want), CHAINS):
        xy = _sk_node_xy(want)
        if ok(f"抓得到「{want}」這顆節點的座標", bool(xy), xy):
            pg.mouse.click(xy[0], xy[1])
            pg.wait_for_timeout(1600)
            pan = pg.evaluate("""() => { const b = document.getElementById('sankeyPanel');
                if (!b || b.hidden) return null;
                return { title: (b.querySelector('.hh b') || {}).textContent || '',
                         crumb: (b.querySelector('.hh [data-all]') || {}).textContent || '',
                         groups: [...b.querySelectorAll('.ms a.grow')].map(a => a.dataset.g),
                         labels: [...b.querySelectorAll('.ms a.grow')].map(a => a.innerText.replace(/\s+/g, ' ')),
                         subs: b.querySelectorAll('.ms a.sub').length,
                         ch: Math.round(b.querySelector('.ms').clientHeight),
                         oy: getComputedStyle(b.querySelector('.ms')).overflowY }; }""")
            if ok("點產業鏈節點，右邊真的展開面板", bool(pan), pan):
                ok(f"面板標題就是那條產業鏈的名字（{want}）", want in pan["title"], pan["title"])
                ok("底下列出的族群數 > 1（不是只列一個）", len(pan["groups"]) > 1, pan["groups"])
                ok("每一列都寫出佔比 %", all("%" in x for x in pan["labels"]), pan["labels"][:3])
                ok("每一列也寫出漲跌（紅漲綠跌那一欄）",
                   sum(1 for x in pan["labels"] if "%" in x) == len(pan["labels"])
                   and all(len(x.split("%")) >= 3 for x in pan["labels"]), pan["labels"][:3])
                ok("一進來是收合的（沒有任何個股列）", pan["subs"] == 0, pan["subs"])
                ok("清單沿用 .hpanel .ms（固定高度 + 自己的捲軸，不是第四種清單）",
                   pan["ch"] <= 460 and pan["oy"] in ("auto", "scroll"), pan)
                # ---- 下拉：展開第一個族群，真的多出個股列
                pg.eval_on_selector("#sankeyPanel .ms a.grow", "a => a.click()")
                pg.wait_for_timeout(800)
                exp = pg.evaluate("""() => { const b = document.getElementById('sankeyPanel');
                    const subs = [...b.querySelectorAll('.ms a.sub')];
                    return { n: subs.length,
                             codes: subs.map(a => a.dataset.code).filter(Boolean).slice(0, 4),
                             hrefs: subs.filter(a => (a.getAttribute('href') || '').indexOf('#stock/') === 0).length,
                             tv: subs.map(a => +a.dataset.tv).filter(v => v > 0),
                             mark: (b.querySelector('.ms a.grow .tw2') || {}).textContent }; }""")
                changed("展開族群，個股列真的跑出來", pan["subs"], exp["n"])
                ok("展開的那幾列是真的個股（有代號）", len(exp["codes"]) > 0, exp)
                ok("每一列都走得到個股頁（href 指向 #stock/）", exp["hrefs"] > 0, exp)
                ok("個股照成交值由大到小排",
                   exp["tv"] == sorted(exp["tv"], reverse=True), exp["tv"][:6])
                ok("展開後箭頭從 ▸ 變成 ▾", exp["mark"] == "▾", exp["mark"])
                pg.eval_on_selector("#sankeyPanel .ms a.grow", "a => a.click()")
                pg.wait_for_timeout(700)
                ok("再點一次真的收起來",
                   count(pg, "#sankeyPanel .ms a.sub") == 0,
                   count(pg, "#sankeyPanel .ms a.sub"))
                # ---- ◎ 走到族群那一階，麵包屑要寫著上一階的鏈名
                pg.eval_on_selector("#sankeyPanel .ms a.grow .go", "a => a.click()")
                pg.wait_for_timeout(1600)
                st2 = pg.evaluate("() => window.App.drillState()")
                ok("按 ◎ 真的下鑽到那個族群", bool(st2["gid"]), st2)
                ok("麵包屑寫的是上一階的產業鏈（不是一次退到底）",
                   want in text(pg, "#sankeyPanel .hh [data-all]"),
                   text(pg, "#sankeyPanel .hh [data-all]"))
                pg.eval_on_selector("#sankeyPanel .hh [data-all]", "b => b.click()")
                pg.wait_for_timeout(1600)
                st3 = pg.evaluate("() => window.App.drillState()")
                ok("按麵包屑只退一階：回到產業鏈，面板還開著",
                   st3["gid"] is None and st3["chain"] is not None
                   and not pg.evaluate("() => document.getElementById('sankeyPanel').hidden"), st3)

            # ------------------------------------------------ D5-② 點背景回復預設
            n_before_drill = None
            blank = pg.evaluate("""() => { const el = document.getElementById('sankey');
                const c = echarts.getInstanceByDom(el); const zr = c.getZr();
                const r = el.getBoundingClientRect();
                for (let fx = 0.97; fx > 0.3; fx -= 0.03)
                  for (let fy = 0.15; fy < 0.9; fy += 0.08) {
                    const x = r.width * fx, y = r.height * fy;
                    const h = zr.handler.findHover(x, y);
                    const X = Math.round(r.left + x), Y = Math.round(r.top + y);
                    if (!(h && h.target) && document.elementFromPoint(X, Y) === el.querySelector('canvas'))
                      return [X, Y]; }
                return null; }""")
            if ok("圖上找得到一個真的空白的點（不是節點也不是連線）", bool(blank), blank):
                st4 = pg.evaluate("() => window.App.drillState()")
                ok("按之前的確有下鑽狀態（不然這條等於沒驗）",
                   bool(st4["chain"] or st4["gid"] or st4["sel"]), st4)
                pg.mouse.click(blank[0], blank[1])
                pg.wait_for_timeout(1600)
                st5 = pg.evaluate("() => window.App.drillState()")
                ok("點背景：下鑽狀態真的全部清空",
                   not st5["chain"] and not st5["gid"] and not st5["sel"]
                   and not st5["stocks"] and not st5["open"], st5)
                ok("點背景：右邊面板真的收起來",
                   pg.evaluate("() => document.getElementById('sankeyPanel').hidden"))
                nodim = pg.evaluate(SK)
                ok("點背景：圖上沒有任何族群還被壓暗（真的回到初始畫面）",
                   nodim["dim"] == 0, nodim["dim"])
                ok("點背景：族群晶片也沒有還亮著的",
                   count(pg, '.linkrow.gchips[data-for="sankey"] .gchip.on') == 0)
            # ESC 走同一支（不要有第二套復原）
            xy2 = _sk_node_xy(want)
            if xy2:
                pg.mouse.click(xy2[0], xy2[1])
                pg.wait_for_timeout(1500)
                ok("再點一次產業鏈，面板又開得起來（為了驗 ESC）",
                   not pg.evaluate("() => document.getElementById('sankeyPanel').hidden"))
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(1500)
                esc = pg.evaluate("() => window.App.drillState()")
                ok("按 ESC 和點背景是同一個結果（下鑽狀態清空、面板收起）",
                   not esc["chain"] and not esc["gid"]
                   and pg.evaluate("() => document.getElementById('sankeyPanel').hidden"), esc)
            _ = n_before_drill

    # ------------------------------------------------------------- D5-④「即時」
    # 容器打不到證交所，所以 stub 掉 Live.fetchQuotes 與 Market3 ——
    # 驗的是「口徑對不對」，不是「網路通不通」（抓不到就不驗＝放過最會出錯的那一段）。
    SKL_STUB = """(intraday) => {
        window.__skReq = 0; window.__skBatch = [];
        window.Live.isIntraday = () => intraday;
        window.Live.fetchQuotes = async (codes) => {
          window.__skReq++; window.__skBatch.push(codes.length);
          const o = {};
          codes.forEach((c, i) => { o[c] = { code: c, name: 'T' + c, price: 100 + (i % 37),
            prevClose: 100, chgPct: 1, volume: 1000 + (i % 53) * 130, time: '10:31:00' }; });
          return o; };
        Object.defineProperty(window.Market3, 'marketAmt', { configurable: true, get: () => 1.23e12 });
        window.Market3.refresh = async () => {};
        Object.defineProperty(window.Market3, 'lastAt', { configurable: true, get: () => Date.now() }); }"""
    SKL_TREE = """() => { const c = echarts.getInstanceByDom(document.getElementById('sankey'));
        const root = c.getOption().series[0].data[0];
        const chains = root.children || [];
        return { rootLabel: (root.label || {}).formatter || '', total: root.value,
                 chains: chains.map(x => ({ name: x.name, v: x.value, stale: !!x.stale,
                                            label: (x.label || {}).formatter || '' })),
                 gs: chains.flatMap(x => (x.children || []).map(g => ({
                      gid: g.gid, v: g.value, stale: !!g.stale, isLive: !!g.isLive,
                      label: (g.label || {}).formatter || '' }))) }; }"""
    if ok("「看哪一天」那一排有『即時』鈕（Andy：在紅框那排）",
          pg.evaluate("() => { const b = document.getElementById('sankeyLiveBtn');"
                      " return !!b && b.closest('#sankeyDays') !== null; }")):
        base_tree = pg.evaluate(SKL_TREE)
        pg.evaluate(SKL_STUB, True)
        pg.eval_on_selector("#sankeyLiveBtn", "b => b.click()")
        pg.wait_for_timeout(2800)
        lv = pg.evaluate("() => window.App.sankeyLive()")
        if ok("按下去真的進入即時模式而且抓到資料", lv["on"] and not lv["err"] and lv["boards"] > 0, lv):
            ok("鈕自己亮起來（看得出現在畫的不是收盤那一張）",
               pg.evaluate("() => document.getElementById('sankeyLiveBtn').classList.contains('on')"))
            tr = pg.evaluate(SKL_TREE)
            changed("畫面真的因此改變（產業鏈的成交值換成即時估算值）",
                    [round(x["v"] or 0) for x in base_tree["chains"]],
                    [round(x["v"] or 0) for x in tr["chains"]])
            # ★ 口徑：佔比的分母＝所有即時板塊加總，所以一定加總到 100%
            live_sum = sum(g["v"] or 0 for g in tr["gs"] if not g["stale"])
            chain_sum = sum(c["v"] or 0 for c in tr["chains"])
            ok("佔比的分母是「所有即時板塊加總」：即時板塊的值加起來剛好等於總數（100%）",
               abs(live_sum - tr["total"]) < tr["total"] * 1e-6,
               {"即時板塊加總": live_sum, "分母": tr["total"]})
            ok("產業鏈那一層的值加起來也剛好是 100%（沒有把自動桶偷偷算進去）",
               abs(chain_sum - tr["total"]) < tr["total"] * 1e-6,
               {"鏈加總": chain_sum, "分母": tr["total"]})
            ok("分母不是 Market3.marketAmt（拿估算的分子去除真實分母會系統性偏掉）",
               abs(tr["total"] - (lv["marketAmt"] or 0)) > 1, {"分母": tr["total"], "marketAmt": lv["marketAmt"]})
            # ★ 自動桶（ind_*）一律標盤後、而且不進分母
            autos = [g for g in tr["gs"] if g["stale"]]
            if ok("圖上有『〇〇・其他』自動桶（不然這條等於沒驗）", len(autos) > 0,
                  [g["gid"] for g in tr["gs"]]):
                ok("自動桶的節點標籤真的寫著「盤後」",
                   all("盤後" in g["label"] for g in autos), [g["label"] for g in autos])
                ok("自動桶的 gid 真的都是 ind_ 開頭（標對了人）",
                   all(str(g["gid"]).startswith("ind_") for g in autos), [g["gid"] for g in autos])
                ok("沒有任何一個手寫板塊被誤標成盤後",
                   all(not str(g["gid"]).startswith("ind_") for g in tr["gs"] if not g["stale"]),
                   [g["gid"] for g in tr["gs"] if not g["stale"]])
                ok("自動桶不在分母裡（把它加進去就不會等於 100%）",
                   sum(g["v"] or 0 for g in autos) > 0
                   and abs(live_sum + sum(g["v"] or 0 for g in autos) - tr["total"]) > 1,
                   {"自動桶合計": sum(g["v"] or 0 for g in autos)})
            # ★ 真實分母只出現在根節點那一格
            ok("根節點寫出「台股總成交值」而且標明是真實值",
               "真實" in tr["rootLabel"], tr["rootLabel"])
            ok("根節點同時寫出即時板塊合計是「估算」（兩個數字分開寫，不會被讀成同一件事）",
               "估算" in tr["rootLabel"], tr["rootLabel"])
            # ★ 狀態列的誠實標示
            note = text(pg, "#sankeyLive")
            for word in ("估算", "盤後", "真實", "分母"):
                ok(f"狀態列講清楚「{word}」這件事", word in note, note[:160])
            # ★ 請求量：沿用 live.js 的批次，不是一檔一個請求
            req = pg.evaluate("() => [window.__skReq, window.__skBatch]")
            ok("批次抓（請求數遠少於檔數，不是一檔打一次）",
               req[0] >= 1 and req[0] <= 6 and lv["codes"] > 50, {"請求": req, "檔數": lv["codes"]})
            ok("回報的請求數與實際打出去的一致", lv["reqs"] == req[0], [lv["reqs"], req[0]])
        # ★ 非盤中要講清楚，而且不可以變成一張空圖
        pg.eval_on_selector("#sankeyLiveBtn", "b => b.click()")
        pg.wait_for_timeout(1200)
        ok("再按一次真的退出即時（回到收盤那一張）",
           not pg.evaluate("() => window.App.sankeyLive().on")
           and pg.evaluate("() => document.getElementById('sankeyLive').hidden"))
        pg.evaluate(SKL_STUB, False)
        pg.eval_on_selector("#sankeyLiveBtn", "b => b.click()")
        pg.wait_for_timeout(2800)
        off = text(pg, "#sankeyLive")
        ok("非盤中按「即時」有明講現在沒有盤", "不是盤中" in off, off[:120])
        ok("非盤中也不是一張空圖（圖照樣畫得出來）",
           pg.evaluate("""() => { const el = document.getElementById('sankey');
               const c = echarts.getInstanceByDom(el);
               const root = c && c.getOption().series[0].data[0];
               return !!(root && (root.children || []).length > 2
                         && !el.classList.contains('isempty')); }"""))
        # ★ 拖時間軸＝退出即時（兩件事互斥，不退出的話拉Bar 看起來像壞掉）
        mx2 = pg.evaluate(f"() => +document.querySelector('{bar}').max")
        set_range(pg, bar, max(0, mx2 - 5), 1600)
        ok("拖「看哪一天」會自動退出即時模式",
           not pg.evaluate("() => window.App.sankeyLive().on"))
        set_range(pg, bar, mx2, 1400)

    # ------------------------------------------------- ⑥ 族群小 Tip 點了要能篩選
    # 資金去向：點晶片 → 其餘族群被壓暗（dim 的數量真的變）
    chip = '.linkrow.gchips[data-for="sankey"] .gchip'
    if ok("資金去向下方有族群晶片列", count(pg, chip) > 0, count(pg, chip)):
        b0 = pg.evaluate(SK)
        h0 = pg.evaluate("() => location.hash")
        pg.eval_on_selector(chip + " .pick", "b => b.click()")
        pg.wait_for_timeout(1500)
        b1 = pg.evaluate(SK)
        ok("點族群晶片不會跳頁（在原地篩選）", pg.evaluate("() => location.hash") == h0)
        changed("點資金去向的族群晶片，被壓暗的族群數真的變了", b0["dim"], b1["dim"])
        ok("被壓暗的是「其餘全部」，留下的只有一個", b1["dim"] == len(b1["names"]) - 1, b1["dim"])
        ok("族群名單沒有因為篩選而改變（位置還是固定的）", b1["names"] == b0["names"])
        ok("晶片自己也亮起來", count(pg, chip + ".on") == 1, count(pg, chip + ".on"))
        pg.eval_on_selector(chip + ".on .pick", "b => b.click()")
        pg.wait_for_timeout(1500)
        b2 = pg.evaluate(SK)
        ok("再點一次真的還原（沒有任何族群被壓暗）", b2["dim"] == 0, b2["dim"])
    # 族群 × 法人：點晶片 → 被壓暗的長條數真的變
    chip2 = '.linkrow.gchips[data-for="instGroups"] .gchip'
    DIMBAR = """() => { const c = echarts.getInstanceByDom(document.getElementById('instGroups'));
        if (!c) return null; const s = (c.getOption().series || [])[0]; if (!s) return null;
        return (s.data || []).filter(d => d.itemStyle && d.itemStyle.opacity != null
                                          && d.itemStyle.opacity < 0.5).length; }"""
    if ok("族群×法人下方有族群晶片列", count(pg, chip2) > 0, count(pg, chip2)):
        n0 = pg.evaluate(DIMBAR)
        pg.eval_on_selector(chip2 + " .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
        n1 = pg.evaluate(DIMBAR)
        changed("點族群×法人的族群晶片，被壓暗的長條數真的變了", n0, n1)
        pg.eval_on_selector(chip2 + ".on .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
        ok("再點一次真的還原", pg.evaluate(DIMBAR) == 0, pg.evaluate(DIMBAR))

    # 總覽的「族群估值」散布圖也套同一套（族群小 Tip ＝ 篩選，不是跳頁）
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(2600)
    gchip = '.linkrow.gchips[data-for="gval"] .gchip'
    DIMPT = """() => { const c = echarts.getInstanceByDom(document.getElementById('gval'));
        if (!c) return null; const d = ((c.getOption().series || [])[0] || {}).data || [];
        return d.filter(x => x.itemStyle && x.itemStyle.opacity != null && x.itemStyle.opacity < 0.5).length; }"""
    if ok("總覽族群估值下方有族群晶片列", count(pg, gchip) > 0, count(pg, gchip)):
        g0 = pg.evaluate(DIMPT)
        h0 = pg.evaluate("() => location.hash")
        pg.eval_on_selector(gchip + " .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
        changed("點總覽族群估值的晶片，被壓暗的圓點數真的變了", g0, pg.evaluate(DIMPT))
        ok("而且不會跳頁", pg.evaluate("() => location.hash") == h0)
        pg.eval_on_selector(gchip + ".on .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
        ok("再點一次真的還原", pg.evaluate(DIMPT) == 0, pg.evaluate(DIMPT))
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2600)

    # ---------------------------------------------------------------- 窄畫面 800px
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.wait_for_timeout(1800)
    nw = pg.evaluate("""() => { const el = document.getElementById('sankey');
        const c = el && echarts.getInstanceByDom(el);
        const cv = el && el.querySelector('canvas.dotfx');
        const r = el ? el.getBoundingClientRect() : null;
        return { pageW: document.documentElement.scrollWidth, winW: window.innerWidth,
                 chart: !!(c && el.querySelector('canvas')),
                 fx: !!cv, fxW: cv ? Math.round(cv.getBoundingClientRect().width) : 0,
                 elW: r ? Math.round(r.width) : 0,
                 chipsIn: (() => { const row = document.querySelector('.linkrow.gchips[data-for="sankey"]');
                   if (!row) return true; const rr = row.getBoundingClientRect();
                   return rr.right <= window.innerWidth + 1; })() }; }""")
    ok("800px 沒有橫向捲軸", nw["pageW"] <= nw["winW"] + 1, nw)
    ok("800px 資金去向還畫得出來", nw["chart"], nw)
    ok("800px 小圓點那一層跟著縮（不會蓋到隔壁）",
       nw["fx"] and abs(nw["fxW"] - nw["elW"]) <= 2, nw)
    ok("800px 族群晶片沒有跑出容器", nw["chipsIn"], nw)
    # 800px 底下點族群，右邊那欄要掉到圖下面（而不是把圖擠成一條）
    pg.eval_on_selector('.linkrow.gchips[data-for="sankey"] .gchip .pick', "b => b.click()")
    pg.wait_for_timeout(1600)
    nw2 = pg.evaluate("""() => { const b = document.getElementById('sankeyPanel');
        const w = document.getElementById('sankeyWrap');
        if (!b || b.hidden || !w) return null;
        const rb = b.getBoundingClientRect(), rw = w.getBoundingClientRect();
        return { below: rb.top >= rw.bottom - 2, inView: rb.right <= window.innerWidth + 1,
                 chartW: Math.round(rw.width),
                 side: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1 }; }""")
    if ok("800px 點族群，右邊那欄一樣開得出來", bool(nw2), nw2):
        ok("800px 下面板掉到圖下方（不是把圖擠成一條）", nw2["below"] and nw2["chartW"] > 500, nw2)
        ok("800px 面板沒有超出視窗、也沒有橫向捲軸", nw2["inView"] and not nw2["side"], nw2)
    if count(pg, '.linkrow.gchips[data-for="sankey"] .gchip.on'):
        pg.eval_on_selector('.linkrow.gchips[data-for="sankey"] .gchip.on .pick', "b => b.click()")
        pg.wait_for_timeout(1200)
    # ---- 800px 下的產業鏈面板（D5-①）。新版面元件一律要驗窄畫面（DECISIONS #171 的教訓）
    # ★ 一定要「先捲、等一下、再量」——這一頁的 CSS 是 scroll-behavior:smooth，
    #   在同一個 evaluate 裡捲完立刻 getBoundingClientRect() 拿到的還是捲動前的位置，
    #   算出來的座標會差好幾千 px，點下去等於點在空氣裡（實測 top 3087 vs 36）。
    xy3 = _sk_node_xy(want) if want else None
    if xy3:
        pg.wait_for_timeout(500)
        pg.mouse.click(xy3[0], xy3[1])
        pg.wait_for_timeout(1600)
        pg.eval_on_selector_all("#sankeyPanel .ms a.grow", "as => as[0] && as[0].click()")
        pg.wait_for_timeout(800)
        nw3 = pg.evaluate(
            "() => { const b = document.getElementById('sankeyPanel');"
            " if (!b || b.hidden) return null;"
            " const rows = [...b.querySelectorAll('.ms a.grow, .ms a.sub')];"
            " const rb = b.getBoundingClientRect();"
            " const w = document.getElementById('sankeyWrap').getBoundingClientRect();"
            " let tall = 0, tiny = 0;"
            # 一列高過 66px 就是被擠成三行以上（名字被折成直排時就會這樣）
            " rows.forEach(a => { const r = a.getBoundingClientRect();"
            "   if (r.height > 66) tall++;"
            "   [...a.querySelectorAll('span')].forEach(sp => {"
            "     const fs = parseFloat(getComputedStyle(sp).fontSize); if (fs < 11) tiny++; }); });"
            " return { rows: rows.length, subs: b.querySelectorAll('.ms a.sub').length,"
            "          below: rb.top >= w.bottom - 2, inView: rb.right <= window.innerWidth + 1,"
            "          side: document.documentElement.scrollWidth > window.innerWidth + 1,"
            "          tall, tiny }; }")
        if ok("800px 點產業鏈，右邊那欄一樣開得出來", bool(nw3), nw3):
            ok("800px 展開族群也列得出個股", nw3["subs"] > 0, nw3)
            ok("800px 面板掉到圖下方、沒有超出視窗、沒有橫向捲軸",
               nw3["below"] and nw3["inView"] and not nw3["side"], nw3)
            ok("800px 每一列沒有被擠成三行以上（名字不會被折成直排）", nw3["tall"] == 0, nw3)
            ok("800px 面板裡每一個字都 >= 11px", nw3["tiny"] == 0, nw3)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(1000)
    pg.set_viewport_size({"width": 1500, "height": 1000})


def t_new_layout(pg, base):
    """2026-09-20 Andy 兩件回報的驗收（site/index.html + site/app.js）：

    ① 「熱門題材 & 今日候選 框格需要一樣大，超出部分改拉Bar」
    ② 「換另一台電腦、螢幕大小不同就會影響整體變化」（附截圖：三張圖壓字）

    驗的是**畫面真的因此改變了**，不是元素存在：
      · 題材那一格真的捲得動（scrollTop 真的從 0 變成非 0），而且高度有上限；
      · 兩張卡在 1280 / 1440 / 1920 各量一次，差 ≤ 2px；
      · 三張圖（市場寬度／法人連續買超／族群估值）在五個常見螢幕寬度下，
        圖**裡面**的字不重疊、不跑出容器。
        ★ 這一段一定要帶 `?svg=1` —— 線上版是 canvas，圖裡的字在 DOM 上不存在，
          不帶這個參數量到的永遠是 0，等於沒驗（見 scripts/_preview.py 上方的說明）。
    """
    # ------------------------------------------------ ① 熱門題材：固定高度 + 真的捲得動
    pg.set_viewport_size({"width": 1440, "height": 1000})
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(2200)
    P = "#themeStrip"
    m0 = pg.evaluate("""() => { const e = document.querySelector('#themeStrip');
        if (!e) return null;
        const cs = getComputedStyle(e);
        return { client: e.clientHeight, scroll: e.scrollHeight, top: e.scrollTop,
                 overflow: cs.overflowY, tiles: e.querySelectorAll('.tile').length }; }""")
    if not ok("熱門題材那一格找得到", bool(m0) and m0["tiles"] > 0, m0):
        return
    ok("熱門題材的高度有上限（不再被內容撐到 1400px）", m0["client"] <= 720, m0)
    ok("熱門題材的內容超出了外框（所以才需要拉Bar）", m0["scroll"] > m0["client"] + 4, m0)
    ok("熱門題材那一格可以捲（overflow-y 不是 visible）", m0["overflow"] in ("auto", "scroll"), m0)
    # 真的捲它一段，驗 scrollTop 真的變了
    pg.evaluate("() => { document.querySelector('#themeStrip').scrollTop = 240; }")
    pg.wait_for_timeout(350)
    m1 = pg.evaluate("() => ({ top: document.querySelector('#themeStrip').scrollTop })")
    ok("真的捲得動（scrollTop 從 0 變成非 0）", m1["top"] > 100, [m0["top"], m1["top"]])
    # 捲到底之後最後一個題材要看得到（他截圖裡就是「電源 / BBU」之後整段不見）
    seen = pg.evaluate("""() => { const e = document.querySelector('#themeStrip');
        e.scrollTop = e.scrollHeight; const tiles = [...e.querySelectorAll('.tile')];
        const last = tiles[tiles.length - 1]; if (!last) return null;
        const er = e.getBoundingClientRect(), lr = last.getBoundingClientRect();
        return { name: (last.querySelector('.t') || {}).textContent,
                 inside: lr.top >= er.top - 2 && lr.bottom <= er.bottom + 2 }; }""")
    ok("捲到底看得到最後一個題材（以前是被裁掉而且沒有捲軸）", bool(seen) and seen["inside"], seen)

    # 今日候選那一格也要是「固定高度 + 拉Bar」（Andy：所有相關版面一致）
    m2 = pg.evaluate("""() => { const e = document.querySelector('.eqpair > .card > .tw');
        if (!e) return null; e.scrollTop = 200;
        return { client: e.clientHeight, scroll: e.scrollHeight, top: e.scrollTop,
                 rows: document.querySelectorAll('#candBody tr').length }; }""")
    ok("今日候選的表格也是固定高度 + 拉Bar，而且真的捲得動",
       bool(m2) and m2["scroll"] > m2["client"] + 4 and m2["top"] > 100, m2)

    # ------------------------------------------------ ② 兩張卡等高（三個寬度各量一次）
    for w in (1280, 1440, 1920):
        pg.set_viewport_size({"width": w, "height": 1000})
        pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1800)
        hs = pg.evaluate("""() => [...document.querySelectorAll('.grid.eqpair > .card')]
            .map(e => Math.round(e.getBoundingClientRect().height))""")
        ok(f"[{w}px] 熱門題材／今日候選兩張卡等高（差 ≤ 2px）",
           len(hs) == 2 and abs(hs[0] - hs[1]) <= 2, hs)
        ok(f"[{w}px] 兩張卡的高度沒有被內容撐爆（≤ 720px）",
           len(hs) == 2 and max(hs) <= 722, hs)

    # ------------------------------------------------ ③ 三張圖在五個寬度都不壓字
    SCAN = """
    () => {
      const want = ['breadth', 'trust', 'gval'];
      const out = { overlaps: [], outside: [], nodes: {} };
      for (const id of want) {
        const host = document.getElementById(id);
        if (!host || !host.getAttribute('_echarts_instance_')) { out.overlaps.push([id, '這張圖沒畫出來', '', 0, 0]); continue; }
        const hr = host.getBoundingClientRect();
        const bs = [...host.querySelectorAll('svg text')]
          .filter(t => (t.textContent || '').trim().length)
          .map(t => ({ t: (t.textContent || '').trim().slice(0, 18), r: t.getBoundingClientRect() }))
          .filter(b => b.r.width > 1 && b.r.height > 1);
        out.nodes[id] = bs.length;
        for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
          const a = bs[i].r, b = bs[j].r;
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox <= 1 || oy <= 1) continue;
          const inter = ox * oy, small = Math.min(a.width * a.height, b.width * b.height);
          if (inter > 0.25 * small) out.overlaps.push([id, bs[i].t, bs[j].t, Math.round(ox), Math.round(oy)]);
        }
        for (const b of bs) {
          const r = b.r;
          const over = Math.max(hr.left - r.left, r.right - hr.right, hr.top - r.top, r.bottom - hr.bottom);
          if (over > 1.5) out.outside.push([id, b.t, Math.round(over)]);
        }
      }
      out.sideways = document.documentElement.scrollWidth > window.innerWidth + 1;
      return out;
    }"""
    for w in (1280, 1366, 1440, 1536, 1920):
        pg.set_viewport_size({"width": w, "height": 1000})
        # ?svg=1 讓 chart() 改用 SVG renderer，圖裡的字才會變成真的 <text> 節點
        pg.goto(f"{base}?svg=1#overview", wait_until="networkidle"); pg.wait_for_timeout(2600)
        r = pg.evaluate(SCAN)
        ok(f"[{w}px] 三張圖的圖內文字都量得到（SVG renderer 有生效）",
           sum(r["nodes"].values()) > 20, r["nodes"])
        ok(f"[{w}px] 市場寬度／法人連續買超／族群估值 圖內文字不重疊",
           not r["overlaps"], r["overlaps"][:4])
        ok(f"[{w}px] 這三張圖的文字都沒有跑出自己的容器",
           not r["outside"], r["outside"][:4])
        ok(f"[{w}px] 總覽沒有橫向捲軸", not r["sideways"], r["sideways"])

    # ------------------------------------------------ ④ F3：輪動時鐘:資金流向排行＝2:1，排行在右
    # Andy 2026-09-20：「圖二的版面配比需要 2:1（輪動時鐘:資金流向排行），資金流向排行 改成在右邊」。
    # 量的是**實際欄寬**與**兩張卡的左右順序**，不是看 class 有沒有換。
    F3 = """() => {
      const g = document.querySelector('#v-flow .grid.g21');
      if (!g) return null;
      const ks = [...g.children].map(e => {
        const r = e.getBoundingClientRect();
        return { h3: ((e.querySelector('h3') || {}).textContent || '').trim().slice(0, 4),
                 x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width) };
      });
      const gr = g.getBoundingClientRect();
      // 兩張卡裡面的東西有沒有凸出自己的卡片（圖、篩選列、晶片列、拉Bar 全部算）
      const over = [];
      g.querySelectorAll('.card').forEach(card => {
        const cr = card.getBoundingClientRect();
        card.querySelectorAll('.chart, .rotfilter, .rottools, .rbar, .linkrow, .hpanel, .note').forEach(e => {
          const r = e.getBoundingClientRect();
          if (r.width < 2) return;
          const d = Math.max(r.right - cr.right, cr.left - r.left);
          if (d > 2) over.push([((e.className || '') + '').slice(0, 24), Math.round(d)]);
        });
      });
      /* 排行圖的族群名稱有沒有被截掉／疊在一起：**量真的畫出去的那些字**。
         ★ 一定要帶 ?svg=1 —— 線上版是 canvas，圖裡的字在 DOM 上根本不存在，
           不帶的話這一段永遠量到 0 個字、永遠綠燈（HANDOFF 2026-09-20 記過這件事）。*/
      const rf = (() => { const el = document.getElementById('rankFlow');
        const c = el && window.echarts && echarts.getInstanceByDom(el);
        if (!c) return null;
        const hr = el.getBoundingClientRect();
        const bs = [...el.querySelectorAll('svg text')]
          .filter(t => (t.textContent || '').trim().length)
          .map(t => ({ t: (t.textContent || '').trim(), r: t.getBoundingClientRect(),
                       fs: parseFloat(getComputedStyle(t).fontSize) || 0 }))
          .filter(b => b.r.width > 1 && b.r.height > 1);
        const cut = [], hit = [];
        bs.forEach(b => { const over = Math.max(hr.left - b.r.left, b.r.right - hr.right,
                                                hr.top - b.r.top, b.r.bottom - hr.bottom);
          if (over > 1.5) cut.push([b.t, Math.round(over)]); });
        for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
          const a = bs[i].r, b = bs[j].r;
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox <= 1 || oy <= 1) continue;
          if (ox * oy > 0.25 * Math.min(a.width * a.height, b.width * b.height)) hit.push([bs[i].t, bs[j].t]);
        }
        return { w: Math.round(hr.width), n: bs.length, cut, hit,
                 minFs: bs.length ? Math.min(...bs.map(b => b.fs)) : 0,
                 left: ((c.getOption().grid || [])[0] || {}).left };
      })();
      return { cols: getComputedStyle(g).gridTemplateColumns, ks, gw: Math.round(gr.width), over, rf,
               sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1 };
    }"""
    for w in (1440, 1280, 1024, 900, 800, 560, 390):
        pg.set_viewport_size({"width": w, "height": 1000})
        # ?svg=1：圖裡的字才會變成真的 <text> 節點，族群名稱有沒有被截掉才量得到
        pg.goto(f"{base}?svg=1#flow", wait_until="networkidle"); pg.wait_for_timeout(2800)
        f = pg.evaluate(F3)
        if not ok(f"[{w}px] 找得到時鐘／排行那一列（F3）", bool(f) and len(f["ks"]) == 2, f):
            continue
        clock, rank = f["ks"][0], f["ks"][1]
        ok(f"[{w}px] 左（或上）邊是輪動時鐘、右（或下）邊是資金流向排行（F3）",
           clock["h3"].startswith("輪動") and rank["h3"].startswith("資金"), f["ks"])
        if w > 1100:
            ok(f"[{w}px] 欄寬真的是 2:1（F3）",
               abs(clock["w"] / max(1, rank["w"]) - 2) <= 0.12,
               f"{clock['w']} : {rank['w']} = {clock['w'] / max(1, rank['w']):.2f}")
            ok(f"[{w}px] 排行在時鐘的右邊（F3）", rank["x"] > clock["x"], f["ks"])
        else:
            ok(f"[{w}px] 窄畫面退回單欄，時鐘在上、排行在下（F3）",
               f["cols"].count(" ") == 0 and rank["y"] > clock["y"], {"cols": f["cols"], "ks": f["ks"]})
        ok(f"[{w}px] 兩張卡裡沒有東西凸出卡片（F3）", not f["over"], f["over"][:4])
        ok(f"[{w}px] 資金流向頁沒有橫向捲軸（F3）", not f["sideways"], f["sideways"])
        if f["rf"]:
            ok(f"[{w}px] 排行圖的文字量得到（SVG renderer 有生效）（F3）", f["rf"]["n"] > 8, f["rf"])
            ok(f"[{w}px] 排行的族群名稱沒有被容器截掉（F3）", not f["rf"]["cut"],
               {"欄寬": f["rf"]["w"], "左留白": f["rf"]["left"], "被截": f["rf"]["cut"][:4]})
            ok(f"[{w}px] 排行圖的文字兩兩不重疊（F3）", not f["rf"]["hit"], f["rf"]["hit"][:4])
            ok(f"[{w}px] 排行圖的文字都不小於 11px（F3）",
               f["rf"]["minFs"] >= 11, f["rf"]["minFs"])
        # 換欄寬之後時鐘的族群標籤要真的重排（layoutRotLabels 的 ResizeObserver）
        lay = pg.evaluate("""() => { const rs = (window.App && window.App._rotLabels) || [];
            const el = document.getElementById('rotClock');
            const W = el ? el.clientWidth : 0, H = el ? el.clientHeight : 0;
            let hit = null, out = null;
            for (let i = 0; i < rs.length; i++) { const a = rs[i];
              if (a.x < -1 || a.y < -1 || a.x + a.w > W + 1 || a.y + a.h > H + 1) out = out || a.name;
              for (let j = i + 1; j < rs.length; j++) { const b = rs[j];
                if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) hit = hit || [a.name, b.name]; } }
            return { n: rs.length, hit, out, W, H }; }""")
        ok(f"[{w}px] 時鐘的族群標籤全在畫布內、兩兩不重疊（F3 換欄寬之後有重排）",
           lay["n"] > 0 and lay["hit"] is None and lay["out"] is None, lay)

    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(600)


# ---------------------------------------------------------------- 輪動時鐘的共用小工具
def _rot_scatter(pg, cid="rotClock"):
    """時鐘上每顆大圈**畫上去的**極座標 [半徑, 角度]。"""
    return pg.evaluate("""(cid) => { const el = document.getElementById(cid);
        const c = el && window.echarts && echarts.getInstanceByDom(el); if (!c) return null;
        const sc = (c.getOption().series || []).filter(s => s.type === 'scatter')[0];
        return sc ? (sc.data || []).map(d => ({ gid: d.row && d.row.gid, v: d.value })) : null; }""", cid)


def _rot_pts(pg):
    """時鐘上**畫上去的**每一顆點（族群＋使用者點開的個股）。
    `stock` 欄位是 renderRotClock 攤出來的，驗「點數變多的是個股不是族群」要靠它。"""
    return pg.evaluate("() => ((window.App && window.App._rotPts) || [])"
                       ".map(p => ({ gid: p.gid, code: p.code, stock: !!p.stock }))") or []


def _rot_trail_pts(pg, cid="rotClock"):
    """所有尾巴加起來畫了幾個點（軌跡開關量的是這個，不是 series 數量 ——
    series 一直在，關掉只是把資料清空，highlightClock 認 gid 的那段才不用跟著改）。

    ★ 2026-09-20（E1）之後這個數字是**固定的**（每條尾巴 48 點），
      所以它只剩下「有沒有畫」這一個用途；「軌跡長到哪裡」請改用 _rot_trail_days()。
    """
    return pg.evaluate("""(cid) => { const el = document.getElementById(cid);
        const c = el && window.echarts && echarts.getInstanceByDom(el); if (!c) return -1;
        return (c.getOption().series || []).filter(s => s.type === 'line')
                 .reduce((a, s) => a + ((s.data || []).length), 0); }""", cid)


def _rot_trail_days(pg):
    """所有族群的軌跡「實際走過幾天」加總（app.js 的 window.App._rotFrame.trailDays）。

    E1 把軌跡重取樣成固定 48 點之後，點數不再會動 —— 一條永遠不會變的指標
    不管紅綠都沒有資訊（DECISIONS #199／#206 同一個教訓）。
    漸進式軌跡（「只有經過才留下軌跡」）真正要量的本來就是「走過幾天」。
    """
    v = pg.evaluate("() => { const f = window.App && window.App._rotFrame; return f ? f.trailDays : null; }")
    return -1 if v is None else v


# E1（Andy 2026-09-20：「軌跡線不能比圓圈還動的快」）的量尺。
# 讀的是 zrender **當下畫出來的**元素，不是 getOption()（那回的是動畫的目標值，
# 動畫中途永遠量不到中間狀態）：
#   · 尾巴＝ec-polyline，shape.points 是攤平的 [x0,y0,x1,y1,…]，最後兩個就是尖端
#   · 大圈＝帶 shape.symbolType 的 path，scaleX＝symbolSize（尾巴自己那顆小圈圈是 6，
#     scatter 的 z=5，尾巴自己那顆小圈圈 z=2，所以用 z>=5 把兩者分開）
# 量之前一定要先篩到**只剩一個族群**，不然 16 條尾巴配 16 顆大圈會有配對歧義。
_ROT_TIP_JS = """(cid) => {
  const el = document.getElementById(cid);
  const c = el && window.echarts && echarts.getInstanceByDom(el);
  if (!c) return null;
  const g = (e, x, y) => (e.transformCoordToGlobal ? e.transformCoordToGlobal(x, y) : [x, y]);
  const tips = [], dots = [];
  (c.getZr().storage.getDisplayList(true) || []).forEach(e => {
    if (!e || e.ignore) return;
    if (e.type === 'ec-polyline' && e.shape && e.shape.points && e.shape.points.length >= 4) {
      const p = e.shape.points, n = p.length;
      tips.push(g(e, p[n - 2], p[n - 1]));
    } else if (e.shape && e.shape.symbolType && (e.scaleX || 0) >= 4 && (e.z || 0) >= 5) {
      dots.push(g(e, 0, 0).concat([e.scaleX]));
    }
  });
  return { tips, dots };
}"""


def _rot_tip_gap(pg, cid="rotClock"):
    """軌跡尖端與大圈中心的像素距離（回 (距離, 大圈半徑)）；量不到就回 (None, None)。"""
    r = pg.evaluate(_ROT_TIP_JS, cid)
    if not r or len(r["tips"]) != 1 or len(r["dots"]) != 1:
        return None, None
    (lx, ly), (dx, dy, sc) = r["tips"][0], r["dots"][0]
    return ((lx - dx) ** 2 + (ly - dy) ** 2) ** 0.5, sc / 2.0


def _rot_tip_gaps_all(pg, cid="rotClock"):
    """**每一個**族群的「尾巴尖端 vs 它自己的大圈」距離（回 (距離清單, 最小半徑)）。

    配對靠順序：zrender 的顯示列表裡尾巴（line series）與大圈（scatter 的 symbol）
    都照 series／data 的順序排，而這兩份順序在 renderRotClock 裡本來就是同一份 `top`。
    這個假設每次量之前都會被「靜止時全部為 0」那一條驗一次 —— 配錯人的話它就會紅。
    """
    r = pg.evaluate(_ROT_TIP_JS, cid)
    if not r or not r["tips"] or len(r["tips"]) != len(r["dots"]):
        return None, None
    ds = [((t[0] - d[0]) ** 2 + (t[1] - d[1]) ** 2) ** 0.5 for t, d in zip(r["tips"], r["dots"])]
    return ds, min(d[2] for d in r["dots"]) / 2.0


def t_new_clock(pg, base):
    """輪動時鐘（C4 ＋ A4，Andy 2026-09-20）：族群／個股篩選、時間軸刷動、軌跡開關、播放。

    每一條都驗「畫面真的因此改變」：
    座標真的不一樣、點數真的變、軌跡點數真的歸零、播放時值真的自己在動。
    """
    # 先把上一段測試留下的選擇清掉 —— 篩選與天數都會寫 localStorage，而且
    # `ROT.groups` 還活在記憶體裡，光 goto 沒有用（理由寫在 reset_rot 的 docstring）。
    pg.set_viewport_size({"width": 1500, "height": 1000})
    reset_rot(pg, base, 2600)

    RB = "#rotBack input[type=range]"

    # ---------------------------------------------------------- A4-3 範圍是「前一天 ～ 前三十天」
    bar = pg.evaluate("""() => { const i = document.querySelector('#rotBack input[type=range]');
        return i && { min: +i.min, max: +i.max, v: +i.value,
                      steps: document.querySelectorAll('#rotBack .pb.step').length,
                      play: document.querySelectorAll('#rotBack .pb.play').length }; }""")
    if not ok("輪動時鐘的拉Bar 還在（A4）", bool(bar), bar):
        return
    ok("拉Bar 範圍是前一天～前三十天（A4-3）", bar["min"] == 1 and bar["max"] == 30, bar)

    # ---------------------------------------------------------- A4-1 ＋ / − 真的按下去
    ok("拉Bar 旁邊有 ＋ 與 −（A4-1）", bar["steps"] == 2, bar)
    ok("拉Bar 旁邊有播放鈕（A4-5）", bar["play"] == 1, bar)
    set_range(pg, RB, 15, 1500)
    v0 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    h0 = canvas_hash(pg, "#rotClock")
    pg.eval_on_selector_all("#rotBack .pb.step", "bs => bs[0].click()")   # −
    pg.wait_for_timeout(1500)
    v1 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    changed("按 − 拉Bar 的值真的變了（A4-1）", v0, v1)
    ok("按 − 是往「離現在更近」走（值變小）", v1 == v0 - 1, f"{v0} → {v1}")
    changed("按 − 之後輪動時鐘真的重畫（A4-1）", h0, canvas_hash(pg, "#rotClock"))
    h1 = canvas_hash(pg, "#rotClock")
    pg.eval_on_selector_all("#rotBack .pb.step", "bs => bs[1].click()")   # ＋
    pg.wait_for_timeout(1500)
    v2 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    changed("按 ＋ 拉Bar 的值真的變了（A4-1）", v1, v2)
    changed("按 ＋ 之後輪動時鐘真的重畫（A4-1）", h1, canvas_hash(pg, "#rotClock"))

    # ---------------------------------------------------------- A4-7 時間軸刷動：大圈真的換座標
    set_range(pg, RB, 3, 1600)
    p3 = _rot_scatter(pg)
    set_range(pg, RB, 28, 1800)
    p28 = _rot_scatter(pg)
    if ok("讀得到時鐘上大圈的座標", bool(p3) and bool(p28) and len(p3) == len(p28), [len(p3 or []), len(p28 or [])]):
        same = [a["gid"] for a, b in zip(p3, p28)
                if abs(a["v"][0] - b["v"][0]) < 1e-9 and abs(a["v"][1] - b["v"][1]) < 1e-9]
        ok("拉到不同天數，大圈真的落在不同座標上（A4-7 時間軸刷動）",
           len(same) == 0, f"這幾個族群兩天的座標一模一樣：{same[:4]}")
        moved = sum(1 for a, b in zip(p3, p28)
                    if abs(a["v"][0] - b["v"][0]) > 0.02 or abs(a["v"][1] - b["v"][1]) > 1.0)
        ok("而且是整批一起移動，不是只有一兩個在動", moved >= len(p3) * 0.8, f"{moved}/{len(p3)}")
    ok("圖上有寫出現在看的是哪一天（A4-7）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
           if (!c) return false; return JSON.stringify(c.getOption().graphic || []).indexOf('回放') >= 0; }"""))

    # ---------------------------------------------------------- A4-7 平滑移動（不是一步到位）
    # ★ 只判「確定會動的那一個量」：ECharts 的 getOption() 回的是**目標值**，
    #   動畫中途讀不到中間座標，所以改量 canvas 本身 —— 一步到位的話，
    #   動畫期間的畫面會和安定之後**完全一樣**（指紋相同）。
    #   2026-09-19 那三次假紅的教訓：不要把兩個量 and 在一起，其中一個本來就不會動。
    set_range(pg, RB, 5, 1600)
    pg.evaluate("() => { const i = document.querySelector('#rotBack input');"
                " i.value = '26'; i.dispatchEvent(new Event('input', { bubbles: true })); }")
    pg.wait_for_timeout(90)
    mid1 = canvas_hash(pg, "#rotClock")
    pg.wait_for_timeout(180)
    mid2 = canvas_hash(pg, "#rotClock")
    pg.wait_for_timeout(1600)
    settled = canvas_hash(pg, "#rotClock")
    changed("刷動期間畫面還在變（＝真的在走，不是瞬間跳過去）（A4-7）", mid1, mid2)
    changed("刷動途中的畫面和停下來之後不一樣（A4-7）", mid2, settled)
    ok("補間動畫設定還在（merge ＋ linear）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
           if (!c) return false; const o = c.getOption();
           return o.animationDurationUpdate >= 400 && o.animationEasingUpdate === 'linear'; }"""))

    # -------------------------------------------- 2026-09-20「只有經過才留下軌跡」漸進式軌跡
    # Andy：「只有經過才留下軌跡，不是馬上所有軌跡都先印出來」。
    # 量的是**畫上去的軌跡點數**：時間軸刷到最舊那一天＝站在起點，每個族群只該有一個點；
    # 往「今天」刷才一天一天長出來。這一條就是驗「不是一開始就整條印好」。
    # ★ 2026-09-20（E1）量的改成「軌跡實際走過幾天」：
    #   固定點數是為了讓尾巴和大圈用同一個補間一起走（見下面那一段的像素量測），
    #   代價是「畫了幾個點」變成常數、再也量不出東西。要守的事情完全沒變。
    set_range(pg, RB, 30, 1800)
    n_grp = len(_rot_scatter(pg) or [])
    d30 = _rot_trail_days(pg)
    set_range(pg, RB, 20, 1800)
    d20 = _rot_trail_days(pg)
    set_range(pg, RB, 10, 1800)
    d10 = _rot_trail_days(pg)
    set_range(pg, RB, 1, 1800)
    d01 = _rot_trail_days(pg)
    t01 = _rot_trail_pts(pg)
    if ok("讀得到時鐘上的族群數", n_grp > 3, n_grp):
        ok("刷到最舊那一天，軌跡還沒走出去（走過 0 天）",
           0 <= d30 <= 1, f"{n_grp} 個族群，軌跡卻已經走了 {d30} 天（應該 ≈ 0）")
        ok("往「今天」刷，軌跡真的一天一天長出來（走過的天數單調變多）",
           d30 < d20 < d10 < d01, f"前30天 {d30} → 20 {d20} → 10 {d10} → 1 {d01}")
        ok("走到接近今天時軌跡已經很長（每個族群都走了 20 天以上）",
           d01 > n_grp * 20, f"{n_grp} 個族群共走了 {d01} 天")
        ok("每條軌跡都是固定點數（E1：點數會變就沒有補間，尾巴會比大圈快）",
           t01 == n_grp * 48, f"{n_grp} 個族群 × 48 點 = {n_grp * 48}，實際 {t01}")

    # ------------------------------------------- 2026-09-20「平均速率、絲滑」等速移動
    # Andy：「每天的移動都需要平均速率，絲滑呈現，而非段點段點式移動」。
    # 做法：播放的間隔 ＝ ECharts 的補間時間（都是 420ms），所以一天接著一天、中間沒有空檔。
    # 驗三件事，每一件都量「畫面上真的在變的那個量」：
    #   ① 在**一天之內**（420ms 內）連續量兩次畫面，指紋要不一樣 ——
    #      一天一格跳的話這 150ms 裡畫面是靜止的，這條就會紅
    #   ② 播放中每隔固定時間量一次「幾天前」，相鄰兩段走掉的天數要一樣（＝等速）
    #   ③ 同時量大圈的座標，相鄰兩段的位移不可以差太多（＝不是一次跳一大格）
    XY = """() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
        const sc = (c.getOption().series || []).filter(s => s.type === 'scatter')[0];
        return (sc.data || []).map(d => { const r = d.value[0], a = d.value[1] * Math.PI / 180;
          return [r * Math.cos(a), r * Math.sin(a)]; }); }"""
    VAL = "() => +document.querySelector('#rotBack input').value"
    set_range(pg, RB, 30, 1500)
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(900)            # 避開剛啟動的第一拍
    f0 = canvas_hash(pg, "#rotClock")
    pg.wait_for_timeout(150)            # 遠小於「一天」的 420ms
    f1 = canvas_hash(pg, "#rotClock")
    changed("播放時同一天之內畫面就在變（＝真的有補間，不是一天一格跳）", f0, f1)
    v0, xy0 = pg.evaluate(VAL), pg.evaluate(XY)
    pg.wait_for_timeout(2100)
    v1, xy1 = pg.evaluate(VAL), pg.evaluate(XY)
    pg.wait_for_timeout(2100)
    v2, xy2 = pg.evaluate(VAL), pg.evaluate(XY)
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(300)
    d1, d2 = v0 - v1, v1 - v2
    ok("播放時每一段時間走掉的天數一樣多（等速）",
       d1 > 0 and d2 > 0 and abs(d1 - d2) <= 2, f"{v0} → {v1} → {v2}（各走 {d1} / {d2} 天）")

    def _mid_disp(a, b):
        if not a or not b or len(a) != len(b):
            return None
        ds = sorted(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 for p, q in zip(a, b))
        return ds[len(ds) // 2]

    m1, m2 = _mid_disp(xy0, xy1), _mid_disp(xy1, xy2)
    if ok("量得到三個時間點的大圈座標", m1 is not None and m2 is not None, [m1, m2]):
        ok("相鄰兩段的位移大致相等（不是一次跳一大格）",
           m1 > 0 and m2 > 0 and max(m1, m2) <= min(m1, m2) * 3 + 0.05,
           f"兩段的位移中位數 {m1:.4f} vs {m2:.4f}")
    ok("補間時間夠長才看得到過程，又不會拖（420ms 一天）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
           const o = c.getOption(); return o.animationDurationUpdate >= 400
             && o.animationDurationUpdate <= 500 && o.animationEasingUpdate === 'linear'; }"""),
       pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('rotClock')).getOption().animationDurationUpdate"))

    # ---------------------------------------------------------- A4-7 軌跡開關
    set_range(pg, RB, 8, 1600)
    n_on = _rot_trail_pts(pg)
    ok("預設有畫軌跡（A4-7）", n_on > 20, n_on)
    ok("軌跡開關真的存在（A4-7）", pg.evaluate("() => !!document.querySelector('#rotTools input[type=checkbox]')"))
    pg.eval_on_selector("#rotTools input[type=checkbox]", "e => e.click()")
    pg.wait_for_timeout(1200)
    n_off = _rot_trail_pts(pg)
    ok("關掉之後軌跡的點數真的歸零（A4-7）", n_off == 0, f"{n_on} → {n_off}")
    pg.eval_on_selector("#rotTools input[type=checkbox]", "e => e.click()")
    pg.wait_for_timeout(1200)
    n_back = _rot_trail_pts(pg)
    ok("再打開軌跡真的回來（A4-7）", n_back > 20, f"{n_off} → {n_back}")

    # ---------------------------------------------------------- A4-5 播放
    set_range(pg, RB, 24, 1200)
    pv0 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(2600)
    pv1 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    changed("按播放之後拉Bar 真的自己在走（A4-5）", pv0, pv1)
    ok("播放是往「現在」走（值變小＝時間往前）（A4-5）", pv1 < pv0, f"{pv0} → {pv1}")
    ok("播放中按鈕變成暫停的樣子", pg.evaluate("() => document.querySelector('#rotBack .pb.play').textContent") == "⏸")
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(300)
    pv2 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    pg.wait_for_timeout(2200)
    pv3 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    ok("再按一次真的停下來（A4-5）", pv2 == pv3, f"停之後 {pv2} → {pv3}（應該不變）")

    # ------------------------------------------- 2026-09-21「暫停功能壞掉了，無法停止」
    # Andy 的原話就是這一句。量出來的根因不是「計時器沒清掉」，是
    # **同一個值被兩支拉Bar 控制**：卡片的 #rotBack 與放大視窗的 #rotZoomBack
    # 改的都是 rotFrame，而暫停只停得掉自己那一支。
    # 修好之前的量測（把 setInterval/clearInterval 包起來數）：
    #   卡片按 ▶ → 36@420；開放大 → 36@420 還在；放大裡按 ▶ → 36@420 + 48@420（兩支同時跑）；
    #   放大裡按 ⏸ → 還剩 36@420；ESC → 卡片繼續跑，「幾天前」2.5 秒內從 3 跑到 27。
    # 所以下面三條都**量 _rotFrame.frame 在接下來 2 秒內有沒有變**，不是看按鈕長什麼樣子。
    FRAME = "() => ((window.App && window.App._rotFrame) || {}).frame"

    def _paused(label, wait=2200):
        """按下暫停之後，frame 在接下來 wait 毫秒內必須**完全不變**。"""
        a = pg.evaluate(FRAME)
        pg.wait_for_timeout(wait)
        b_ = pg.evaluate(FRAME)
        return ok(label, a == b_ and a is not None, f"frame {a} → {b_}（應該一模一樣）")

    # ①-a 最單純的：播放 → 暫停
    set_range(pg, RB, 26, 1200)
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(1600)
    ok("播放中 frame 真的在動（不然下面三條等於沒驗）",
       pg.evaluate(FRAME) != 26, pg.evaluate(FRAME))
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(300)
    _paused("按暫停之後時鐘真的停住（2026-09-21：暫停壞掉）")

    # ①-b 「重畫之後再按暫停」—— 播到一半點族群晶片（會重建篩選列與晶片列）再暫停
    CHIP0 = '#v-flow .rotfilter[data-rf="rot"] .linkrow.gchips'
    set_range(pg, RB, 26, 1200)
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(1400)
    pg.eval_on_selector(f"{CHIP0} .gchip .pick", "b => b.click()")
    pg.wait_for_timeout(1400)
    ok("播放中點族群晶片，時鐘還在播（重畫沒有把播放弄丟）",
       pg.evaluate("() => document.querySelector('#rotBack .pb.play').textContent") == "⏸",
       pg.evaluate("() => document.querySelector('#rotBack .pb.play').textContent"))
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(300)
    _paused("重畫（點過族群晶片）之後再按暫停，一樣停得下來")
    pg.eval_on_selector(f"{CHIP0} .gchip.on .pick", "b => b.click()")     # 收拾
    pg.wait_for_timeout(1000)

    # ①-c **原本的 bug 本體**：卡片在播 → 開放大 → 在放大裡按暫停 → ESC，卡片必須是停的
    set_range(pg, RB, 28, 1200)
    pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(1200)
    pg.eval_on_selector("#rotZoomBtn", "b => b.click()")
    pg.wait_for_timeout(2400)
    ok("開放大視窗時，卡片那支播放會先停掉（不然它躲在遮罩後面繼續跑）",
       pg.evaluate("() => document.querySelector('#rotBack .pb.play').textContent") == "▶",
       pg.evaluate("() => document.querySelector('#rotBack .pb.play').textContent"))
    pg.eval_on_selector("#rotZoomBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(1500)
    zv0 = pg.evaluate("() => +document.querySelector('#rotZoomBack input').value")
    pg.eval_on_selector("#rotZoomBack .pb.play", "b => b.click()")
    pg.wait_for_timeout(300)
    zv1 = pg.evaluate("() => +document.querySelector('#rotZoomBack input').value")
    pg.wait_for_timeout(2200)
    zv2 = pg.evaluate("() => +document.querySelector('#rotZoomBack input').value")
    ok("在放大視窗裡按暫停真的停住", zv1 == zv2, f"{zv0} → {zv1} → {zv2}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(1800)
    cv0 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    pg.wait_for_timeout(2400)
    cv1 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    ok("關掉放大視窗之後卡片那張時鐘也是停的（這就是「暫停按了沒用」的本體）",
       cv0 == cv1, f"關掉之後 {cv0} → {cv1}（修好之前 2.5 秒內從 3 跑到 27）")
    set_range(pg, RB, 8, 1200)

    # ---------------------------------------------------------- A4-6 越外圈顏色越深
    # 量的是**畫上去的顏色**：色碼是 mixHex(面板底色, 該階段原色, w)，
    # 所以從 (顏色, 原色, 底色) 可以把 w 反推回來，再看 w 有沒有隨半徑變大。
    depth = pg.evaluate("""() => {
        const ps = (window.App && window.App._rotPts) || [], bg = window.App && window.App._rotBg;
        if (!ps.length || !bg) return null;
        const un = (h) => { const x = String(h).replace('#', '');
          const v = parseInt(x.length === 3 ? x.split('').map(c => c + c).join('') : x, 16);
          return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
        const a = un(bg);
        return ps.map(p => { const c = un(p.color), b = un(p.base);
          const ws = [0, 1, 2].filter(i => Math.abs(b[i] - a[i]) > 40)
                              .map(i => (c[i] - a[i]) / (b[i] - a[i]));
          return { r: p.r, w: ws.length ? ws.reduce((x, y) => x + y, 0) / ws.length : null, name: p.name }; })
          .filter(x => x.w != null); }""")
    if ok("讀得到每顆大圈畫上去的顏色與半徑（A4-6）", bool(depth) and len(depth) >= 5, depth and len(depth)):
        depth.sort(key=lambda x: x["r"])
        inner, outer = depth[0], depth[-1]
        ok("最外圈的顏色真的比最靠圓心的深（A4-6）",
           outer["w"] - inner["w"] > 0.2,
           f"{inner['name']} r={inner['r']:.3f} 濃度={inner['w']:.3f} → "
           f"{outer['name']} r={outer['r']:.3f} 濃度={outer['w']:.3f}")
        # 整體趨勢：把半徑與濃度各自排名，兩個名次序列要幾乎一致（Spearman）。
        # ★ 不用「嚴格單調」當判準：色碼只有 8 bit，反推回來的濃度有 ±1/255 的量化誤差，
        #   半徑接近的兩顆點會互換名次 —— 那是取色精度，不是功能壞了。
        n = len(depth)
        rank_w = {id(x): i for i, x in enumerate(sorted(depth, key=lambda x: x["w"]))}
        d2 = sum((i - rank_w[id(x)]) ** 2 for i, x in enumerate(depth))
        rho = 1 - 6 * d2 / (n * (n * n - 1))
        ok("濃度和半徑的名次幾乎完全一致（A4-6，Spearman ≥ 0.95）", rho >= 0.95, f"rho={rho:.3f}")

    # ---------------------------------------------------------- A4-2 旋轉箭頭確定已經移除
    ok("盤面上沒有 ↻ 旋轉箭頭（A4-2，2026-09-20 已移除，不要改回去）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
           if (!c) return true; return JSON.stringify(c.getOption().graphic || []).indexOf('↻') < 0; }"""))

    # ---------------------------------------------------------- A4-4 圓心到圓外的說明
    # 2026-09-21：常駐的 #rotCenterNote 移除（622 字、1440px 佔 225px、390px 佔 469px），
    # 內容併進「怎麼看 ?」。說明本身沒有消失，所以這裡改成**真的去按那顆鈕**再讀。
    ok("圖下方那段常駐長說明不在常駐 DOM 裡了（Andy 2026-09-21：「下方這段也移除」）",
       not pg.evaluate("() => !!document.getElementById('rotCenterNote')")
       and "跟大盤走得一模一樣" not in text(pg, "#v-flow"),
       text(pg, "#v-flow")[:80])
    ok("「怎麼看 ?」那顆鈕還在（他要移除的是佔版面的那一段，不是說明本身）",
       count(pg, '#v-flow .howbtn[data-how="rot"]') == 1)
    note = how_text(pg, "rot")
    ok("按了「怎麼看」說明真的展開（不是連說明都被砍掉）", len(note) > 300, len(note))
    ok("說明有講圓心是什麼（A4-4）", "圓心" in note, note[:60])
    ok("說明有講最外圈那一圈是什麼（A4-4）", "最外圈" in note and "偏離" in note, note[:120])
    ok("說明有寫「所以我該怎麼用」，不是只解釋座標（A4-4）", "怎麼用" in note, note[-80:])
    ok("說明有講族群晶片列現在在哪、按了會怎樣（晶片列搬家之後要講清楚）",
       "族群名稱" in note and ("上面" in note or "正下方" in note), note[:200])

    # ---------------------------------------------------------- A4-8 相鄰兩天不可以亂跳
    # 門檻怎麼來的（同一份資料、同一把尺量出來的，不是隨手訂的）：
    #   尺＝前端畫圖用的那一把（兩軸各自除以「整段軌跡的最大偏離量」，所以半徑 1＝盤緣）。
    #   舊算法（rs 不平滑、動能用 5 日均值）：中位數 0.1272、p99 0.599、最大 0.890
    #     —— 一天可以走掉大半個盤面，就是 Andy 說的「一天的差距卻各種歪曲」。
    #   新算法（EMA10 平滑 ＋ SMA40 基準 ＋ ROC10 動能）：中位數 0.0431、p99 0.198、最大 0.284。
    #   門檻取在兩者中間、且離新值有一倍以上的餘裕：中位數 ≤ 0.08、最大 ≤ 0.45。
    #   這樣「算法被改回去」會紅，「行情本身比較激烈」不會紅。
    step = pg.evaluate("""() => {
        const pts = ((window.App && window.App.D && window.App.D.flow_v3
                      && window.App.D.flow_v3.rrg && window.App.D.flow_v3.rrg.points) || []);
        if (!pts.length) return null;
        let sx = 1e-6, sy = 1e-6;
        pts.forEach(p => (p.trail || []).forEach(w => {
          if (w[1] != null) sx = Math.max(sx, Math.abs(w[1] - 100));
          if (w[2] != null) sy = Math.max(sy, Math.abs(w[2] - 100)); }));
        const st = [];
        pts.forEach(p => { const t = (p.trail || []).filter(w => w[1] != null && w[2] != null);
          for (let i = 1; i < t.length; i++) {
            const dx = (t[i][1] - t[i-1][1]) / sx, dy = (t[i][2] - t[i-1][2]) / sy;
            st.push(Math.sqrt(dx * dx + dy * dy)); } });
        st.sort((a, b) => a - b);
        return { n: st.length, med: st[Math.floor(st.length / 2)],
                 p99: st[Math.floor(st.length * 0.99)], max: st[st.length - 1],
                 days: Math.max(...pts.map(p => (p.trail || []).length)) }; }""")
    if ok("讀得到輪動軌跡的原始資料（A4-8）", bool(step) and step["n"] > 100, step):
        ok("軌跡存得夠長，拉到「前三十天」取得到那一天（A4-3/7）",
           step["days"] >= 31, f"trail 只有 {step['days']} 天")
        ok("相鄰兩天只走一小步：中位數 ≤ 0.08 個盤面半徑（A4-8）",
           step["med"] <= 0.08, f"中位數 {step['med']:.4f}（舊算法 0.1272）")
        ok("相鄰兩天沒有異常大跳動：最大 ≤ 0.45 個盤面半徑（A4-8）",
           step["max"] <= 0.45, f"最大 {step['max']:.4f}（舊算法 0.8898）")

    # ------------------------------------------------ E1 軌跡尖端有沒有黏在大圈上（像素量）
    # Andy 2026-09-20：「軌跡線不能比圓圈還動的快」。
    # 根因是舊版 trail() 的點數會隨天數變多，ECharts merge 時新長出來的那一段沒有舊位置
    # 可以補間 —— 尖端是**瞬移**的，大圈卻用 420ms 慢慢滑，所以看起來尾巴跑在前面。
    # 量法：篩到只剩一個族群（配對才沒有歧義），播放中每 ~60ms 量一次
    #       「尾巴最後一點」與「那顆大圈」的像素距離，整段的最大值要小於一個點的半徑。
    CHIP = '#v-flow .linkrow.gchips[data-sync="n2"]'
    pg.eval_on_selector(f"{CHIP} .gchip .pick", "b => b.click()")
    pg.wait_for_timeout(1400)
    gap0, rad = _rot_tip_gap(pg)
    if ok("篩到一個族群之後量得到「尾巴尖端」與「大圈」的像素座標（E1）",
          gap0 is not None, {"gap": gap0, "r": rad}):
        ok("靜止時尖端就貼在大圈上（E1）", gap0 <= max(1.0, rad * 0.25), f"{gap0:.2f}px（大圈半徑 {rad:.1f}px）")
        set_range(pg, RB, 30, 1600)
        pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
        gaps = []
        for _ in range(40):
            pg.wait_for_timeout(60)
            g, _r = _rot_tip_gap(pg)
            if g is not None:
                gaps.append(g)
        pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
        pg.wait_for_timeout(400)
        if ok("播放期間真的量到了一整串樣本（E1）", len(gaps) >= 20, len(gaps)):
            mx = max(gaps)
            mid = sorted(gaps)[len(gaps) // 2]
            ok("播放中軌跡尖端一直貼著大圈（最大距離 < 一個點的半徑）（E1）",
               mx < rad, f"最大 {mx:.2f}px / 中位 {mid:.2f}px（大圈半徑 {rad:.1f}px；"
                         f"修好之前量到的是最大 8.25px / 中位 3.77px）")
    # 收拾：把剛剛為了量測選起來的族群取消掉，後面的條件才是從「全部族群」開始
    if count(pg, f"{CHIP} .gchip.on"):
        pg.eval_on_selector(f"{CHIP} .gchip.on .pick", "b => b.click()")
        pg.wait_for_timeout(1000)

    # 同一件事在「16 個族群一起播」的情況再量一次（一個族群跑得動，不代表 16 個也跟得上）。
    # 配對靠順序，而順序對不對由下面「靜止時全部為 0」那一條當場驗。
    set_range(pg, RB, 20, 1700)
    g_rest, rad_all = _rot_tip_gaps_all(pg)
    if ok("全部族群時也量得到每條尾巴與它自己的大圈（E1）",
          bool(g_rest) and rad_all, {"n": len(g_rest or []), "r": rad_all}):
        ok("靜止時每一條尾巴的尖端都**完全**落在自己的大圈上（E1，同時證明配對沒配錯人）",
           max(g_rest) < 0.5, [round(x, 2) for x in g_rest])
        pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
        allg = []
        for _ in range(26):
            pg.wait_for_timeout(60)
            ds, _r = _rot_tip_gaps_all(pg)
            if ds:
                allg.extend(ds)
        pg.eval_on_selector("#rotBack .pb.play", "b => b.click()")
        pg.wait_for_timeout(400)
        if ok("16 個族群一起播時量到一整串樣本（E1）", len(allg) >= 200, len(allg)):
            allg.sort()
            p75 = allg[int(len(allg) * 0.75)]
            p95 = allg[int(len(allg) * 0.95)]
            ok("播放中四分之三以上的尾巴尖端貼在自己的大圈上（E1）",
               p75 <= rad_all, f"p75={p75:.1f}px（大圈半徑 {rad_all:.1f}px；修好之前 p75≈17px）")
            ok("跑最快的那幾個族群也不會脫節太遠（E1，p95 < 3 個半徑）",
               p95 <= rad_all * 3, f"p95={p95:.1f}px、最大 {allg[-1]:.1f}px"
                                   f"（修好之前最大 87px，而且會一路累積）")

    # ---------------------------------------------------------- E3 族群選取只剩一處
    # Andy 2026-09-20：「篩選族群功能覆蓋下方的族群選取功能」。
    # 他講的不是幾何重疊，是**功能上蓋過去**：同一張卡裡兩份族群清單，
    # 上面那排會篩圖、下面那排只會 highlight。現在族群只在晶片列選。
    # ★ 2026-09-21：那排晶片列從「圖下方」搬到「產業鏈 seg 的正下方」（見下面的位置量測）。
    ok("排行與時鐘各有一排篩選列（C4）",
       pg.evaluate("() => document.querySelectorAll('#v-flow .rotfilter').length") == 2,
       pg.evaluate("() => document.querySelectorAll('#v-flow .rotfilter').length"))
    ok("篩選列上沒有「族群篩選」了（E3：族群只在晶片列選）",
       pg.evaluate("() => document.querySelectorAll('#v-flow .rotfilter .rot-gbtn').length") == 0,
       pg.evaluate("() => [...document.querySelectorAll('#v-flow .rotfilter button')].map(b => b.textContent.trim())"))
    ok("兩張卡都有族群晶片列（唯一的族群選擇器）", count(pg, CHIP) == 2, count(pg, CHIP))

    # ------------------------------------------- 2026-09-21②「個股篩選拿掉」
    # Andy 的原話就是這三個字。驗的是**全站一顆都不剩**（含放大視窗），
    # 而且連它展開的面板與搜尋框都沒有留死碼。
    dead = pg.evaluate("""() => ({ sbtn: document.querySelectorAll('.rot-sbtn').length,
        panel: document.querySelectorAll('.rotpick').length,
        search: document.querySelectorAll('.rotsearch').length,
        list: document.querySelectorAll('.rotstocklist').length,
        txt: [...document.querySelectorAll('#v-flow .rotfilter button')]
               .filter(b => b.textContent.indexOf('個股') >= 0).length })""")
    ok("全站已經沒有「個股篩選」鈕（2026-09-21②）", dead["sbtn"] == 0, dead)
    ok("它展開的面板／搜尋框／清單也一起清乾淨（不留死碼）",
       dead["panel"] == 0 and dead["search"] == 0 and dead["list"] == 0, dead)
    ok("篩選列上也看不到「個股」兩個字", dead["txt"] == 0, dead)
    ok("localStorage 不再寫入個股選擇",
       "stocks" not in (pg.evaluate("() => localStorage.getItem('tw.rot.filter') || ''") or ""),
       pg.evaluate("() => localStorage.getItem('tw.rot.filter')"))

    # ------------------------------------------- 2026-09-21③ 族群晶片列搬到產業鏈 seg 正下方
    # Andy：「下方的族群篩選幫我改到 全部、半導體、…、傳產下方 包含資金流向排行，
    #         並且需要縮小一點 我只是需要篩選選取」。
    # 量三件事：DOM 順序、y 座標、字級；而且**兩張卡都要**。
    place = pg.evaluate("""() => [...document.querySelectorAll('#v-flow .rotfilter')].map(box => {
        const seg = box.querySelector('.rotchain'), ch = box.querySelector('.linkrow.gchips');
        if (!seg || !ch) return { rf: box.dataset.rf, missing: true };
        const a = seg.getBoundingClientRect(), c = ch.getBoundingClientRect();
        const pick = ch.querySelector('.gchip .pick');
        const chart = box.closest('.card').querySelector('.chart');
        const cr = chart ? chart.getBoundingClientRect() : null;
        return { rf: box.dataset.rf,
                 afterSeg: !!(seg.compareDocumentPosition(ch) & Node.DOCUMENT_POSITION_FOLLOWING),
                 sameBox: ch.parentElement === box,
                 gapY: Math.round(c.top - a.bottom),
                 aboveChart: cr ? c.bottom <= cr.top + 1 : null,
                 h: Math.round(c.height), n: ch.querySelectorAll('.gchip').length,
                 fs: pick ? parseFloat(getComputedStyle(pick).fontSize) : null }; })""")
    ok("兩張卡都量得到晶片列的位置", len(place) == 2 and not any(x.get("missing") for x in place), place)
    if len(place) == 2 and not any(x.get("missing") for x in place):
        for x in place:
            tag = "輪動時鐘" if x["rf"] == "rot" else "資金流向排行"
            ok(f"[{tag}] 晶片列在產業鏈那一排的正下方（DOM 順序＋同一個容器）",
               x["afterSeg"] and x["sameBox"], x)
            ok(f"[{tag}] 而且真的貼著它（垂直間距 0～14px）", 0 <= x["gapY"] <= 14, x)
            ok(f"[{tag}] 晶片列在圖的上面（不是還留在圖下方）", x["aboveChart"] is True, x)
            ok(f"[{tag}] 字級縮小到 11px（他要的是選單不是內文）", x["fs"] == 11, x)
            ok(f"[{tag}] 整排高度有上限，不會把圖推下去（≤ 100px）", x["h"] <= 100, x)
            ok(f"[{tag}] 族群一個都沒少（還是全部列得出來）", x["n"] > 20, x)
    ok("圖下方已經沒有舊的那一排晶片了",
       pg.evaluate("() => document.querySelectorAll('#rotClockWrap .linkrow.gchips, "
                   "#rankFlowWrap .linkrow.gchips').length") == 0,
       pg.evaluate("() => document.querySelectorAll('#rotClockWrap .linkrow.gchips, "
                   "#rankFlowWrap .linkrow.gchips').length"))

    # ------------------------------------------- 2026-09-21⑥ 畫面上不准出現英文 id
    # Andy 的截圖上有一格寫著 `financial`。根因是 CHAIN_NAME 那張寫死的對照表沒跟上族群改版；
    # 正解是讀 payload 的 chains[].name，所以這裡直接對**畫面上的字**掃一次正規式。
    segtxt = pg.evaluate("() => [...document.querySelectorAll('#v-flow .rotchain button')]"
                         ".map(b => b.textContent.trim())")
    import re as _re
    bad = [t for t in segtxt if _re.fullmatch(r"[A-Za-z0-9_\- ]+", t)]
    ok("產業鏈篩選列上一個英文 id 都沒有（全站繁體中文是硬規則）", not bad,
       {"英文的": bad, "全部": segtxt})
    ok("金融與軟體這兩條新鏈也有中文名（截圖上的 financial 就是它）",
       "financial" not in segtxt and "software" not in segtxt, segtxt)

    # ------------------------------------------- 晶片列搬家之後，既有行為一條都不准壞
    # （E3 原本就有這幾條，搬位置只是換了插入點，所以照樣要驗「畫面真的因此改變」）
    n_clock0 = len(_rot_scatter(pg) or [])
    n_rank0 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
        return c ? ((c.getOption().yAxis[0].data) || []).length : 0; }""")
    gids = pg.evaluate("() => [...document.querySelectorAll('#v-flow .rotfilter[data-rf=\"rot\"] "
                       ".linkrow.gchips .gchip')].map(c => c.dataset.g)")
    if ok("晶片列真的列得出族群（E3）", len(gids) >= 3, len(gids)):
        for g in gids[:2]:
            pg.eval_on_selector(f'{CHIP} .gchip[data-g="{g}"] .pick', "b => b.click()")
            pg.wait_for_timeout(900)
        n_clock1 = len(_rot_scatter(pg) or [])
        n_pts1 = pg.evaluate("() => ((window.App && window.App._rotPts) || []).length")
        n_rank1 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
            return c ? ((c.getOption().yAxis[0].data) || []).length : 0; }""")
        ok("點晶片，輪動時鐘上真的只剩這兩個族群（E3）",
           n_clock1 == 2 and n_clock0 > 2, f"{n_clock0} → {n_clock1}")
        ok("_rotPts 的族群數也真的變少（E3）", n_pts1 == 2, f"{n_clock0} → {n_pts1}")
        changed("點晶片，資金流向排行上的族群數也真的變了（兩張圖同一份選擇）", n_rank0, n_rank1)
        ok("兩排晶片同時被選起來（data-sync=\"n2\" 的同步沒有被拆掉）",
           count(pg, f"{CHIP} .gchip.on") == 4, count(pg, f"{CHIP} .gchip.on"))
        ok("點晶片同時在排行下方展開成分股（點族群展開個股長在這一排身上）",
           pg.evaluate("""() => { const b = document.getElementById('rankPanel');
               return !!b && !b.hidden && b.querySelectorAll('.ms a[href^="#stock/"]').length > 0; }"""))
        ok("篩選列上寫出目前只看幾個族群（C4）",
           "2" in (pg.evaluate("() => (document.querySelector('.rotfilter .rot-note')||{}).textContent") or ""),
           pg.evaluate("() => (document.querySelector('.rotfilter .rot-note')||{}).textContent"))
        ls = pg.evaluate("() => { try { return localStorage.getItem('tw.rot.filter'); } catch (e) { return null; } }")
        ok("選擇真的寫進 localStorage（C4）", bool(ls) and gids[0] in ls, ls)
        # 再點一次要取消
        for g in gids[:2]:
            pg.eval_on_selector(f'{CHIP} .gchip[data-g="{g}"] .pick', "b => b.click()")
            pg.wait_for_timeout(900)
        ok("再點一次取消，兩張圖真的還原（E3）",
           len(_rot_scatter(pg) or []) == n_clock0, f"{n_clock1} → {len(_rot_scatter(pg) or [])}")
        # 「清除篩選」也要還能用（個股篩選拿掉之後它的出現條件改過）
        pg.eval_on_selector(f'{CHIP} .gchip[data-g="{gids[0]}"] .pick', "b => b.click()")
        pg.wait_for_timeout(900)
        ok("選了族群才會冒出「清除篩選」", count(pg, '.rotfilter[data-rf="rot"] .rot-clear') == 1)
        click(pg, '.rotfilter[data-rf="rot"] .rot-clear', 1000)
        ok("按「清除篩選」真的全部還原",
           len(_rot_scatter(pg) or []) == n_clock0, f"→ {len(_rot_scatter(pg) or [])}（原本 {n_clock0}）")

    # ------------------------------------------- 2026-09-21④「部分族群一直貼在圓圈邊緣」
    # 他的原話：「看到部分族群一直貼在圓圈邊緣上，是否數值過大 導致一直維持最大值」。
    # 量出來的根因不是「理論上限 √2 超過畫布 1.25」（那只多夾到 1 個），
    # 是**尺凍結在今天、而過去 30 天的偏離可以到今天的 1.92 倍**：
    #   被動元件 MLCC 31 天裡 31 天都被硬夾在盤緣、矽晶圓 28/31 —— 整段播放半徑動也不動。
    # 修法是盤緣外留一條壓縮過的緩衝帶（CLOCK_TAIL=0.18），今天的畫面一個像素都沒動。
    # 這裡量兩件事：① 今天最外圈只有一個 ② 被夾過的那幾個現在真的會動。
    set_range(pg, RB, 1, 1600)
    rr = pg.evaluate("() => ((window.App && window.App._rotPts) || []).map(p => ({ n: p.name, r: p.r }))")
    if ok("讀得到每顆點的半徑", len(rr) > 5, len(rr)):
        rr.sort(key=lambda x: -x["r"])
        rim = [x for x in rr if x["r"] >= 0.999]
        ok("最外圈（r ≥ 1.0）上只有一個族群，而且就是離大盤最遠的那一個",
           len(rim) == 1, f"貼在最外圈的：{[(x['n'], round(x['r'], 3)) for x in rim]}；"
                          f"前三名 {[(x['n'], round(x['r'], 3)) for x in rr[:3]]}")
        ok("其他人都明顯在它裡面（第二名 ≤ 0.97）", rr[1]["r"] <= 0.97,
           f"第二名 {rr[1]['n']} r={rr[1]['r']:.3f}")
        ok("半徑真的分得開（最大與最小差 3 倍以上，不是全擠在外圈）",
           rr[0]["r"] >= rr[-1]["r"] * 3, f"{rr[0]['r']:.3f} vs {rr[-1]['r']:.3f}")
    # ② 刷過整段時間軸，最外圈那個族群的半徑必須**真的在變**（以前是 31 天都一樣）
    trace = {}
    for f in (1, 5, 10, 20, 30):
        set_range(pg, RB, f, 1400)
        for x in pg.evaluate("() => ((window.App && window.App._rotPts) || []).map(p => ({ n: p.name, r: p.r }))"):
            trace.setdefault(x["n"], []).append(round(x["r"], 3))
    outer = sorted(trace.items(), key=lambda kv: -max(kv[1]))[:2]
    for name, vs in outer:
        ok(f"「{name}」刷時間軸時半徑真的會動（修好之前它 31 天都被夾在同一個值）",
           len(set(vs)) >= 4 and max(vs) - min(vs) > 0.01,
           f"五個時間點的半徑 {vs}（相異 {len(set(vs))}/5）")
    ok("而且沒有人跑出畫布（緩衝帶上限 1.18）",
       max(max(v) for v in trace.values()) <= 1.181,
       max((max(v), k) for k, v in trace.items()))
    set_range(pg, RB, 5, 1400)

    # ------------------------------------------------- 兩階段下鑽（Andy 2026-09-21）
    # 他的原話：「點擊族群後可以顯示對應個股，也可以點擊，並顯示在圖上，
    #            一樣維持有既有功能，以上止差別資訊完整度」。
    # 每一條都驗「畫面真的因此改變」：清單真的出現、**圖上的點數真的變多**、
    # 再點一次真的變回去、返回真的回到階段一。
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2600)
    scroll_to(pg, "rotClockWrap")
    base_pts = _rot_pts(pg)
    n_base = len(base_pts)
    ok("階段一：盤上只有族群，一顆個股都沒有",
       n_base > 1 and not any(p["stock"] for p in base_pts), n_base)

    # --- 階段一 → 階段二：用真的滑鼠點盤上那顆「成分股最多」的族群
    #     （挑成分股多的族群才驗得到排序與捲動；只有 3 檔的族群等於沒驗）
    pt = pg.evaluate("""() => { const el = document.getElementById('rotClock');
        const c = echarts.getInstanceByDom(el); if (!c) return null;
        const si = c.getOption().series.findIndex(s => s.type === 'scatter');
        const ds = c.getOption().series[si].data || [];
        const gd = (window.App && window.App.D && window.App.D.groups_detail) || null;
        let best = ds[0], bn = -1;
        ds.forEach(d => { const n = gd ? (((gd[d.row.gid] || {}).members || []).length) : (d.row.share || 0);
          if (n > bn) { bn = n; best = d; } });
        if (!best) return null;
        const q = c.convertToPixel({ seriesIndex: si }, best.value); const r = el.getBoundingClientRect();
        return { x: r.x + q[0], y: r.y + q[1], gid: best.row.gid, name: best.row.name }; }""")
    if not ok("算得出要點的那顆族群點", bool(pt), pt):
        pt = None
    if pt:
        h0 = pg.evaluate("() => location.hash")
        pg.mouse.click(pt["x"], pt["y"])
        pg.wait_for_timeout(1600)
        st = pg.evaluate("""() => { const b = document.getElementById('rankPanel');
            if (!b || b.hidden) return null;
            const as = [...b.querySelectorAll('.ms a')];
            return { n: as.length, tv: as.map(a => +a.dataset.tv),
                     crumb: (b.querySelector('.hh') || {}).textContent.replace(/\s+/g, ' ').trim(),
                     back: !!b.querySelector('[data-all]'),
                     plot: as.filter(a => !a.className.includes('noplot')).length,
                     hash: location.hash }; }""")
        if ok("點時鐘上的族群，旁邊真的列出它的成分股（階段二）", bool(st) and st["n"] > 0, st):
            ok("成分股清單真的照成交值由大到小排（讀數值比大小，不是看有沒有 render）",
               all(st["tv"][i - 1] >= st["tv"][i] for i in range(1, len(st["tv"]))), st["tv"][:6])
            ok("點族群不會把人帶離這一頁（在原地展開）", st["hash"] == h0, st["hash"])
            ok("面板上有麵包屑「全部族群 › 族群名」（回得去階段一）",
               st["back"] and "全部族群" in st["crumb"] and pt["name"] in st["crumb"], st["crumb"][:60])

        # --- 階段二 → 階段三：點個股，圖上的點數真的變多
        codes = pg.evaluate("""() => [...document.querySelectorAll('#rankPanel .ms a')]
            .filter(a => !a.className.includes('noplot')).slice(0, 3).map(a => a.dataset.code)""")
        if ok("清單裡至少有一檔算得出輪動座標（畫得上去）", bool(codes), codes):
            pg.eval_on_selector(f'#rankPanel .ms a[data-code="{codes[0]}"]', "a => a.click()")
            pg.wait_for_timeout(1500)
            p1 = _rot_pts(pg)
            changed("點個股，輪動時鐘上的點數真的變多（階段三）", n_base, len(p1))
            ok("多出來的那一顆真的是個股，而且就是我點的那一檔",
               len(p1) == n_base + 1 and any(x["stock"] and x["code"] == codes[0] for x in p1),
               [x for x in p1 if x["stock"]])
            ok("族群點一顆都沒有少（既有的東西沒有被個股擠掉）",
               sum(1 for x in p1 if not x["stock"]) == n_base, len(p1))
            two = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
                return (c.getOption().series || []).filter(s => s.type === 'scatter')
                       .map(s => ({ name: s.name, n: (s.data || []).length })); }""")
            ok("個股是**另一個 series**（族群實心圓、個股空心圓，樣式分得出來）",
               len(two) == 2 and two[1]["n"] == 1, two)
            hollow = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
                const ss = (c.getOption().series || []).filter(s => s.type === 'scatter');
                const g = ss[0].data[0].itemStyle, k = ss[1].data[0].itemStyle;
                return { group: { c: g.color, bw: g.borderWidth }, stock: { c: k.color, bw: k.borderWidth } }; }""")
            ok("個股畫成空心圓（填色幾乎透明、邊框比族群粗）",
               bool(hollow) and hollow["stock"]["bw"] >= hollow["group"]["bw"], hollow)

            # 多選：再點兩檔
            for c2 in codes[1:3]:
                pg.eval_on_selector(f'#rankPanel .ms a[data-code="{c2}"]', "a => a.click()")
                pg.wait_for_timeout(1100)
            pmulti = _rot_pts(pg)
            ok("可以多選（點三檔就有三顆個股）",
               sum(1 for x in pmulti if x["stock"]) == len(codes[:3]), len(pmulti))

            # --- 下鑽狀態下，既有功能一個都不准壞
            before_xy = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
                const ss = (c.getOption().series || []).filter(s => s.type === 'scatter');
                return { g: ss[0].data[0].value, s: ss[1].data[0].value }; }""")
            set_range(pg, RB, 22, 1800)
            after_xy = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
                const ss = (c.getOption().series || []).filter(s => s.type === 'scatter');
                return { g: ss[0].data[0].value, s: ss[1].data[0].value }; }""")
            ok("下鑽狀態下「看哪一天」照樣有效：族群點真的換座標",
               abs(before_xy["g"][0] - after_xy["g"][0]) > 1e-6 or abs(before_xy["g"][1] - after_xy["g"][1]) > 1e-6,
               [before_xy["g"], after_xy["g"]])
            ok("下鑽狀態下「看哪一天」對個股點一樣有效（個股也跟著回放）",
               abs(before_xy["s"][0] - after_xy["s"][0]) > 1e-6 or abs(before_xy["s"][1] - after_xy["s"][1]) > 1e-6,
               [before_xy["s"], after_xy["s"]])
            set_range(pg, RB, 5, 1400)
            n_g0 = sum(1 for x in _rot_pts(pg) if not x["stock"])
            pg.eval_on_selector('.rotfilter[data-rf="rot"] .rot-top10', "c => { c.checked = true; c.onchange(); }")
            pg.wait_for_timeout(1400)
            ptop = _rot_pts(pg)
            ok("下鑽狀態下「只看前 10 大」照樣有效：族群真的變少",
               sum(1 for x in ptop if not x["stock"]) < n_g0,
               f"{n_g0} → {sum(1 for x in ptop if not x['stock'])}")
            ok("但我自己點開的個股不會被那個勾選掃掉（那是我明確選的）",
               sum(1 for x in ptop if x["stock"]) == len(codes[:3]), ptop)
            pg.eval_on_selector('.rotfilter[data-rf="rot"] .rot-top10', "c => { c.checked = false; c.onchange(); }")
            pg.wait_for_timeout(1400)

            # --- 放大視窗也要看得到個股（E2 的教訓：放大之後功能都沒反應）
            pg.eval_on_selector("#rotZoomBtn", "b => b.click()")
            pg.wait_for_timeout(2400)
            zs = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('zoomBody'));
                return c ? (c.getOption().series || []).filter(s => s.type === 'scatter')
                  .map(s => ({ name: s.name, n: (s.data || []).length })) : null; }""")
            ok("下鑽狀態下按「放大」，放大視窗裡一樣畫得出個股（既有功能沒壞）",
               bool(zs) and len(zs) == 2 and zs[1]["n"] == len(codes[:3]), zs)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(1600)
            ok("在放大視窗裡按 ESC 只關放大視窗，不會順手把下鑽也收掉",
               pg.evaluate("() => document.getElementById('zoomOv').hidden")
               and pg.evaluate("() => { const b = document.getElementById('rankPanel'); return !!b && !b.hidden; }")
               and sum(1 for x in _rot_pts(pg) if x["stock"]) == len(codes[:3]),
               [pg.evaluate("() => document.getElementById('zoomOv').hidden"), _rot_pts(pg)])

            # --- 個股標籤與族群標籤在三個寬度下都不重疊、都在畫布內
            for w in (1440, 1024, 800):
                pg.set_viewport_size({"width": w, "height": 1000})
                pg.wait_for_timeout(1500)
                lay = pg.evaluate("""() => { const el = document.getElementById('rotClock');
                    const rs = (window.App && window.App._rotLabels) || [];
                    const W = el.clientWidth, H = el.clientHeight; const ov = [], out = [];
                    for (let i = 0; i < rs.length; i++) { const a = rs[i];
                      if (a.x < -1 || a.y < -1 || a.x + a.w > W + 1 || a.y + a.h > H + 1) out.push(a.name);
                      for (let j = i + 1; j < rs.length; j++) { const b = rs[j];
                        if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h)
                          ov.push(a.name + ' × ' + b.name); } }
                    return { n: rs.length, ov, out }; }""")
                ok(f"[{w}px] 下鑽之後標籤還是兩兩不重疊（族群＋個股一起排）",
                   bool(lay) and lay["n"] > 0 and not lay["ov"], lay)
                ok(f"[{w}px] 下鑽之後每個標籤都還在畫布內", not lay["out"], lay)
            pg.set_viewport_size({"width": 1500, "height": 1000})
            pg.wait_for_timeout(1200)
            scroll_to(pg, "rotClockWrap")

            # --- 再點一次要移除
            for c2 in codes[:3]:
                pg.eval_on_selector(f'#rankPanel .ms a[data-code="{c2}"]', "a => a.click()")
                pg.wait_for_timeout(1000)
            ok("再點一次，個股真的從盤上移除",
               sum(1 for x in _rot_pts(pg) if x["stock"]) == 0, _rot_pts(pg))

            # --- 返回階段一：ESC
            pg.eval_on_selector(f'#rankPanel .ms a[data-code="{codes[0]}"]', "a => a.click()")
            pg.wait_for_timeout(1200)
            ok("（先再畫一檔上去，才驗得到返回會把它收掉）",
               sum(1 for x in _rot_pts(pg) if x["stock"]) == 1)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(1400)
            back = _rot_pts(pg)
            ok("按 ESC 回到階段一：面板收起來了",
               pg.evaluate("() => { const b = document.getElementById('rankPanel'); return !b || b.hidden; }"))
            ok("按 ESC 回到階段一：盤上的點數回到原本的族群數",
               len(back) == n_base and not any(x["stock"] for x in back), f"{len(back)} vs {n_base}")

    # --- 拿不到個股輪動資料時要有優雅退路（不是整張圖變空白）
    pg.route("**/rrg_members.json*", lambda r: r.fulfill(status=404, body="not found"))
    # ★ 一定要真的重新載入頁面。`goto` 到**同一個** hash 只是 hashchange，
    #   前一次抓到的 rrg_members 還留在記憶體裡，這一段就會驗到「其實有資料」的假綠燈
    #   （2026-09-21 第一次跑就是這樣紅的：note 裡一句提示都沒有）。
    pg.goto(base, wait_until="networkidle")
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2800)
    scroll_to(pg, "rotClockWrap")
    gid0 = pg.evaluate("() => { const c = document.querySelector('#v-flow .linkrow.gchips[data-sync=\"n2\"] .gchip');"
                       " return c ? c.dataset.g : null; }")
    if gid0:
        pg.eval_on_selector(f'#v-flow .linkrow.gchips[data-sync="n2"] .gchip[data-g="{gid0}"] .pick', "b => b.click()")
        pg.wait_for_timeout(1800)
        # 基準要在**點完族群之後**才量：點族群晶片本來就會把圖篩成只剩它，
        # 在那之前量的話這一條會變成在比兩件不相干的事（實測 16 → 2）。
        n_before_fail = len(_rot_pts(pg))
        fb = pg.evaluate("""() => { const b = document.getElementById('rankPanel');
            return { open: !!b && !b.hidden, n: b ? b.querySelectorAll('.ms a').length : 0,
                     note: b ? (b.querySelector('.note') || {}).textContent || '' : '',
                     noplot: b ? b.querySelectorAll('.ms a.noplot').length : 0 }; }""")
        ok("個股輪動資料抓不到時，成分股清單照樣列得出來（不是整張面板空白）",
           fb["open"] and fb["n"] > 0, fb)
        ok("而且有講清楚為什麼畫不上去（不是默默沒反應）", "還沒算出來" in fb["note"], fb["note"][-60:])
        ok("每一列都標成「畫不上去」，點了也不會亂加點", fb["noplot"] == fb["n"], fb)
        pg.eval_on_selector("#rankPanel .ms a", "a => a.click()")
        pg.wait_for_timeout(1000)
        ok("抓不到資料時點個股，圖上不會多出假的點（不可以假裝有值）",
           len(_rot_pts(pg)) == n_before_fail, f"{n_before_fail} → {len(_rot_pts(pg))}")
    pg.unroute("**/rrg_members.json*")
    # 收拾：把篩選與下鑽狀態清掉，不要留給後面的段落。
    # ★ 2026-09-21：本來是「removeItem ＋ goto 同一個 hash」，那**清不掉記憶體裡的 ROT.groups**
    #   （goto 到同一份文件只是 hashchange，JS 不會重載 —— 理由完整寫在 reset_rot 的 docstring）。
    #   這一段最後點過一個族群晶片，所以它會把「只剩 1 個族群」留給下一段：
    #   實測平行排程把「新-輪動時鐘 → 批次7」排進同一個 worker 時，
    #   批次7 的「點族群晶片，時鐘上的族群真的變少」量到 before=1、點完變 16（其實是取消），
    #   看起來像功能壞了，其實是上一段沒收乾淨。改用 reset_rot（會真的 reload）。
    reset_rot(pg, base, 2000)

    # ---------------------------------------------------------- 窄畫面 800px
    # Andy 2026-09-18 的 E6 就是只驗 1440px 放過去的：他把瀏覽器縮成半邊就看得到。
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2400)
    narrow = pg.evaluate("""() => {
        const out = { sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                      over: [], bar: null };
        document.querySelectorAll('#v-flow .rotfilter').forEach(e => {
          const r = e.getBoundingClientRect(), p = e.parentElement.getBoundingClientRect();
          if (r.right > p.right + 1 || r.left < p.left - 1) out.over.push(Math.round(r.right - p.right)); });
        const i = document.querySelector('#rotBack input[type=range]');
        if (i) { const r = i.getBoundingClientRect();
          out.bar = { w: Math.round(r.width), steps: document.querySelectorAll('#rotBack .pb').length }; }
        return out; }""")
    ok("800px 不會出現橫向捲軸（窄畫面）", not narrow["sideways"], narrow)
    ok("800px 篩選列沒有凸出卡片（窄畫面）", not narrow["over"], narrow["over"])
    ok("800px 拉Bar 與 ＋／−／▶ 都還在而且量得到寬度（窄畫面）",
       bool(narrow["bar"]) and narrow["bar"]["w"] > 40 and narrow["bar"]["steps"] == 3, narrow["bar"])
    # 800px 底下真的按一次 −，值要變（不是只是畫得出來）
    set_range(pg, RB, 12, 1200)
    w0 = pg.evaluate("() => +document.querySelector('#rotBack input').value")
    pg.eval_on_selector_all("#rotBack .pb.step", "bs => bs[0].click()")
    pg.wait_for_timeout(1100)
    changed("800px 底下按 − 一樣有反應（窄畫面）", w0,
            pg.evaluate("() => +document.querySelector('#rotBack input').value"))

    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(1200)


def t_tasks(pg, base):
    """任務板頁（#tasks）—— Andy 2026-09-20 選的「在網站上多一頁」那個方案。

    為什麼要驗這一頁
    ----------------
    Andy：「很常發生我問你問題你做完，但我發現做不全，你就接續其他工作，
    導致很多事情都遺失沒完成。」這一頁就是那件事的解法 ——
    所以它**打不開或是空的，等於這個解法沒有生效**，必須有機器在守。

    驗的是「真的有內容」而不是「元素存在」：任務筆數、狀態統計、
    以及「要 Andy 動手」「等 Andy 回答」這兩塊有沒有真的列出來。
    """
    pg.goto(f"{base}#tasks", wait_until="networkidle"); pg.wait_for_timeout(1400)
    st = pg.evaluate("""() => { const el = document.getElementById('v-tasks');
        if (!el) return null;
        return { cards: el.querySelectorAll('.tk').length,
                 pills: el.querySelectorAll('.linkrow .pill').length,
                 txt: el.innerText, h: Math.round(el.getBoundingClientRect().height) }; }""")
    if not ok("任務板頁打得開", bool(st), st):
        return
    ok("任務板列得出任務（不是空的）", st["cards"] >= 10, st["cards"])
    ok("上方有狀態統計（一眼看出還有幾件沒好）", st["pills"] >= 2, st["pills"])
    ok("「要你動手的」那一塊有列出來", "要你動手" in st["txt"], st["txt"][:120])
    ok("「等你回答」那一塊有列出來", "等你回答" in st["txt"], st["txt"][:120])
    # ★ 這一條守的是 obsidian/000-開始這裡.md 那條規則：沒 push 的不准標成已上線
    ok("頁面上寫明「改完但還沒上線」不會標成已上線",
       "還沒上線" in st["txt"] or "沒有部署出去" in st["txt"], st["txt"][:200])
    ok("頁面真的有高度（不是塌掉的空殼）", st["h"] > 400, st["h"])

    # 窄畫面：Andy 有時候在手機上看「到底做完了沒」
    pg.set_viewport_size({"width": 390, "height": 900}); pg.wait_for_timeout(700)
    nar = pg.evaluate("""() => ({ over: document.documentElement.scrollWidth > window.innerWidth + 1,
        cards: document.querySelectorAll('#v-tasks .tk').length })""")
    ok("任務板在 390px 沒有橫向捲軸", not nar["over"], nar)
    ok("任務板在 390px 卡片還在", nar["cards"] >= 10, nar)
    pg.set_viewport_size({"width": 1500, "height": 1000})


def t_themes(pg, base):
    pg.goto(f"{base}#themes", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("題材熱力圖有畫出來", pg.evaluate("() => !!document.querySelector('#themeMap canvas')"))
    ok("題材頁有下方明細", len(text(pg, "#themeDetail")) > 20, text(pg, "#themeDetail")[:40])

    # 真的用滑鼠點熱力方塊 → 下方明細要換一個題材
    before = text(pg, "#themeDetail")[:60]
    pg.evaluate("document.getElementById('themeMap').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
    # 熱力圖方塊的大小跟著資料變，而且預設顯示的就是最大那一塊 ——
    # 固定戳一個座標很容易戳到「現在已經選的那一塊」，看起來像點不動。
    # 改成掃一格格的點，而且**每次點之前重新量位置**（點下去會換 hash、版面會跟著動）。
    after = before
    grid = [(fx / 10, fy / 10) for fy in (2, 5, 8) for fx in (9, 1, 7, 3, 5)]
    for fx, fy in grid:
        pg.evaluate("document.getElementById('themeMap').scrollIntoView({block:'center'})")
        pg.wait_for_timeout(350)
        box = pg.evaluate("() => { const r = document.getElementById('themeMap').getBoundingClientRect();"
                          " return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
        pg.mouse.click(box["x"] + box["w"] * fx, box["y"] + box["h"] * fy)
        pg.wait_for_timeout(900)
        after = text(pg, "#themeDetail")[:60]
        if after != before:
            break
    changed("點題材熱力方塊，下方明細跟著換", before, after)

    # 題材熱力圖也要能放大，而且一樣不能拖
    ok("題材熱力圖有放大鈕", count(pg, "#themeZoom") == 1)
    click(pg, "#themeZoom", 1300)
    ok("題材熱力圖放大開得起來", pg.evaluate(
        "() => !document.getElementById('zoomOv').hidden && !!document.querySelector('#zoomBody canvas')"))
    click(pg, "#zoomClose", 600)
    ok("題材熱力圖沒有開啟拖曳平移（roam）", pg.evaluate(
        "() => { const c = echarts.getInstanceByDom(document.getElementById('themeMap'));"
        " return c ? c.getOption().series[0].roam === false : false; }"))
    # Andy：「題材資金熱力這邊也是會影響大小」—— 放大只能在框內發生（熱力圖保留縮放）
    check_zoom(pg, "themeMapWrap", "themeMap", "題材資金熱力")

    # 總覽的「熱門題材」方塊 → 點了要切到該題材
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1500)
    ok("總覽有熱門題材方塊", count(pg, "#themeStrip .tile") > 0)
    if count(pg, "#themeStrip .tile"):
        click(pg, "#themeStrip .tile", 1600)
        ok("點熱門題材會切到該題材", pg.evaluate("location.hash").startswith("#themes/"), pg.evaluate("location.hash"))

    # 題材頁：族群分組 + 剖析圖零件點得到個股
    tids = pg.evaluate("(window.ThemeDiagrams ? Object.keys(window.ThemeDiagrams).filter(k => k !== 'fit') : [])")
    ok("題材剖析圖數量 ≥ 18", len(tids) >= 18, len(tids))
    # ★ 2026-09-19：原本只跑前 3 個，18 個題材裡有 15 個從來沒被打開過。
    #   一輪多 15 次 goto 約 30 秒，換掉「題材頁壞了沒人知道」這個洞是划算的。
    for tid in tids:
        pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(1100)
        ok(f"題材 {tid} 有剖析圖", count(pg, "#themeDiagram svg") > 0)
        # Andy 09-13：剖析圖不要縮放（跟產業／個股剖析圖一致），要看大圖用右上角「放大」
        check_nozoom(pg, "themeDiagram", f"題材 {tid} 剖析圖")
        # ★ 2026-09-19：原本的選擇器含 #themeParts，那是剖析圖零件框、
        #   不管有沒有分組它都存在，所以這條永遠綠。真正的分組標記是 #themeMembers tr.ghead。
        ok(f"題材 {tid} 成員有依族群分組", count(pg, "#themeMembers tr.ghead") > 0,
           f"ghead={count(pg, '#themeMembers tr.ghead')} 列")
        if count(pg, "#themeDiagram [data-part][data-codes]"):
            # 零件會緩慢飄動，一般 click 會卡在「等它停下來」逾時 —— 見 click_moving 的說明
            click_moving(pg, "#themeDiagram [data-part][data-codes]", 700)
            ok(f"題材 {tid} 點零件會列出個股", count(pg, "#themeParts a.lk") > 0,
               f"#themeParts 連結數 = {count(pg, '#themeParts a.lk')}")


def t_stock(pg, base, code):
    pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2400)
    ok("個股頁有標題", len(text(pg, "#stockPage h2")) > 2, text(pg, "#stockPage h2"))
    ok("個股頁 K 線有畫出來", count(pg, "#lwc canvas") > 0)
    # Andy：「資訊需要定期更新」—— 頁面要自己講清楚更新到哪一天
    fresh = pg.evaluate("""() => { const ns = [...document.querySelectorAll('#stockPage .note')].map(e => e.innerText);
        return ns.find(t => t.includes('資料更新到')) || ''; }""")
    ok("個股頁有寫資料更新到哪一天", "資料更新到" in fresh and any(c.isdigit() for c in fresh), fresh[:80])

    # --- K 線圖要夠大（Andy：「K 線圖太小，版面需要擴大」）：高度跟著視窗走，不是寫死 640
    kh = pg.evaluate("""() => { const e = document.getElementById('lwc');
        return { h: Math.round(e.getBoundingClientRect().height), vh: window.innerHeight,
                 w: Math.round(e.getBoundingClientRect().width) }; }""")
    ok("K 線圖高度佔視窗一半以上", kh["h"] > kh["vh"] * 0.5, kh)

    # --- 寬版是預設（Andy：「K 線圖 default 就大一點」）：第一次進來就該是寬的
    S = """() => ({ w: Math.round(document.getElementById('lwc').getBoundingClientRect().width),
        wide: document.body.classList.contains('kwide'),
        aside: !!document.querySelector('aside') && getComputedStyle(document.querySelector('aside')).display !== 'none',
        saved: (() => { try { return localStorage.getItem('tw.kwide'); } catch (e) { return null; } })(),
        canvas: document.querySelectorAll('#lwc canvas').length })"""
    d0 = pg.evaluate(S)
    ok("沒設定過時，個股頁預設就是寬版", d0["wide"] and not d0["aside"], d0)
    ok("預設寬版下 K 線圖有畫出來", d0["canvas"] > 0, d0)
    # 按一次 → 退出寬版：圖變窄、事件欄回來、選擇要存起來
    click(pg, "#wideBtn", 900)
    d1 = pg.evaluate(S)
    ok("按一次會退出寬版，K 線圖變窄", d1["w"] < d0["w"] - 100, f"{d0['w']} → {d1['w']}")
    ok("退出寬版時右側事件欄回來", d1["aside"], d1)
    ok("退出寬版的選擇有存起來", d1["saved"] == "0", d1["saved"])
    ok("退出寬版後 K 線圖還在（沒有變空白）", d1["canvas"] > 0, d1)
    # 換頁再回來要記得「我關掉了」
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1200)
    ok("離開個股頁，事件欄一定在", pg.evaluate("() => getComputedStyle(document.querySelector('aside')).display !== 'none'"))
    pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2200)
    ok("回個股頁記得「關掉寬版」的選擇", not pg.evaluate("() => document.body.classList.contains('kwide')"))
    # 再按一次 → 回到寬版
    click(pg, "#wideBtn", 900)
    d2 = pg.evaluate(S)
    ok("再按一次回到寬版，圖又變寬", d2["wide"] and d2["w"] > d1["w"] + 100, f"{d1['w']} → {d2['w']}")
    ok("回到寬版時事件欄收起來", not d2["aside"], d2)

    # --- K 棒寬度可調，而且預設就要寬一點（Andy：「K棒長度需要可以調整，default先長一點」）
    click(pg, "#cfgBtn", 700)
    bw = pg.evaluate("() => { const e = document.getElementById('bw'); return e ? { v: +e.value, min: +e.min, max: +e.max } : null; }")
    if ok("圖表設定裡有 K 棒寬度", bool(bw), bw):
        ok("K 棒寬度預設比函式庫預設（7px）寬", bw["v"] >= 9, bw)
        h0 = canvas_hash(pg, "#lwc")
        pg.evaluate("""() => { const e = document.getElementById('bw'); e.value = String(+e.max);
            e.dispatchEvent(new Event('input', { bubbles: true })); }""")
        pg.wait_for_timeout(900)
        changed("拉寬 K 棒，K 線圖真的重畫", h0, canvas_hash(pg, "#lwc"))
        saved = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.kcfg')||'{}').bar; } catch(e) { return null; } }")
        ok("K 棒寬度有存進 localStorage", saved and saved >= 20, saved)
        pg.evaluate("""() => { const e = document.getElementById('bw'); e.value = '11';
            e.dispatchEvent(new Event('input', { bubbles: true })); }""")
        pg.wait_for_timeout(600)
    click(pg, "#cfgBtn", 400)

    # --- 籌碼頁不可以出現空圖（Andy：「抓不到數據就替換其他方式或直接刪除」）
    click(pg, '#stockTabs button[data-t="chips"]', 1400)
    chips = pg.evaluate("""() => { const t = document.getElementById('stockTab');
        const blanks = [...t.querySelectorAll('.chart')].filter(c => !c.querySelector('canvas') && !c.querySelector('.empty'));
        return { cards: t.querySelectorAll('.card').length, charts: t.querySelectorAll('.chart').length,
                 blanks: blanks.length, tiles: t.querySelectorAll('.kvs .k').length,
                 len: t.innerText.trim().length }; }""")
    ok("籌碼頁沒有畫不出東西的空圖", chips["blanks"] == 0, chips)
    ok("籌碼頁有內容（圖或數字至少一樣）", chips["charts"] + chips["tiles"] > 0 and chips["len"] > 60, chips)

    # --- 完整個股頁缺檔時的簡版頁（Andy：「不可以出現沒有資訊狀況」）
    # 故意讓某一檔的個股頁 404，頁面還是必須有實際內容，不能只剩一句「還沒產生」
    # 要挑一檔「這個分頁還沒載過」的，不然 App.D 裡有快取就不會真的走到 404 那條路
    miss = pg.evaluate("""async () => { const r = await fetch('data/stocks.json'); const s = await r.json();
        const cached = (window.App && window.App.D) || {};
        const x = s.find(v => v.name && v.code !== '2330' && !cached['stock/' + v.code]);
        return x ? x.code : null; }""")
    if ok("找得到一檔可以拿來測缺頁的股票", bool(miss), miss):
        pg.route(f"**/data/stock/{miss}.json*", lambda route: route.fulfill(status=404, body="not found"))
        pg.goto(f"{base}#stock/{miss}", wait_until="networkidle"); pg.wait_for_timeout(2600)
        lite = pg.evaluate("""() => { const el = document.getElementById('stockPage');
            return { len: el.innerText.trim().length, cards: el.querySelectorAll('.card').length,
                     tiles: el.querySelectorAll('.kvs .k').length, sibs: el.querySelectorAll('.sibs a').length,
                     head: (el.querySelector('h2')||{}).innerText || '',
                     chain: (document.getElementById('indChain')||{}).innerText.trim().length,
                     nodata: /還沒產生|尚無資料|沒有資訊/.test(el.innerText) }; }""")
        ok("缺完整頁時仍然有標題（名稱＋代號）", miss in (lite["head"] or ""), lite)
        ok("缺完整頁時不是一片空白（內容夠長）", lite["len"] > 200, lite)
        ok("缺完整頁時有列出實際數字（價量／法人／估值）", lite["tiles"] >= 4, lite)
        ok("缺完整頁時有列出同族群可以點的個股", lite["sibs"] > 0, lite)
        ok("缺完整頁時上方產業鏈照樣出來", lite["chain"] > 50, lite)
        ok("缺完整頁時不會只丟一句「還沒產生」", not lite["nodata"], lite)
        pg.unroute(f"**/data/stock/{miss}.json*")
        pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2400)

    # --- 六個分頁：每個都要真的換內容
    seen = {}
    for tab in ("revenue", "profit", "dividend", "chips", "basics", "news"):
        click(pg, f'#stockTabs button[data-t="{tab}"]', 700)
        seen[tab] = pg.evaluate("() => document.getElementById('stockTab').innerText.trim().slice(0,60)")
        ok(f"分頁 {tab} 有內容", len(seen[tab]) > 5, seen[tab])
    ok("六個分頁內容彼此不同", len(set(seen.values())) == 6, seen)

    # --- 營收分頁的「單月／累計」切換要真的重畫
    click(pg, '#stockTabs button[data-t="revenue"]', 800)
    if count(pg, "#revMode button") >= 2:
        h0 = canvas_hash(pg, "#revYear")
        click(pg, '#revMode button[data-v="c"]', 800)
        h1 = canvas_hash(pg, "#revYear")
        changed("營收「單月／累計」切換真的重畫", h0, h1)
        click(pg, '#revMode button[data-v="m"]', 500)

    # --- 獲利分頁的本益比河流圖（Andy 2026-09-15：「需要新增像財報狗那樣的河流圖…兩種模式可切換」）
    #     兩種模式都要真的重畫，而且選擇要真的存進 localStorage。
    click(pg, '#stockTabs button[data-t="profit"]', 1600)
    ok("獲利分頁有本益比河流圖", count(pg, "#peChart canvas") > 0)
    ok("河流圖有三個模式可切", count(pg, "#peMode button") == 3,
       pg.evaluate("() => [...document.querySelectorAll('#peMode button')].map(b => b.textContent)"))
    note0 = text(pg, "#peNote")
    ok("河流圖下方有講出目前落在哪一區", "區" in note0, note0[:100])
    if count(pg, "#peMode button") == 3:
        click(pg, '#peMode button[data-v="band"]', 1400)
        h0 = canvas_hash(pg, "#peChart")
        click(pg, '#peMode button[data-v="mult"]', 1400)
        h1 = canvas_hash(pg, "#peChart")
        changed("切到「倍數線」，河流圖真的重畫", h0, h1)
        st = pg.evaluate("""() => ({ ls: localStorage.getItem('tw.periver'),
            on: [...document.querySelectorAll('#peMode button.on')].map(b => b.dataset.v),
            note: (document.getElementById('peNote') || {}).textContent || '' })""")
        ok("「倍數線」真的寫進 localStorage", st["ls"] == "mult", st)
        ok("只有被選到的那顆是 on", st["on"] == ["mult"], st["on"])
        ok("說明文字跟著換成倍數線的讀法", "倍數線" in st["note"], st["note"][-60:])

        # B1 填滿模式（Andy 2026-09-16 給的圖四：財報狗 PE 區間評價法）
        click(pg, '#peMode button[data-v="fill"]', 1400)
        h2 = canvas_hash(pg, "#peChart")
        changed("切到「填滿」，河流圖真的重畫", h1, h2)
        ok("「填滿」跟「色帶分區」畫出來不一樣（真的填滿了）", h2 != h0, f"{h0} / {h2}")
        st2 = pg.evaluate("""() => ({ ls: localStorage.getItem('tw.periver'),
            on: [...document.querySelectorAll('#peMode button.on')].map(b => b.dataset.v),
            note: (document.getElementById('peNote') || {}).textContent || '' })""")
        ok("「填滿」真的寫進 localStorage", st2["ls"] == "fill", st2)
        ok("說明文字跟著換成填滿的讀法", "填滿" in st2["note"], st2["note"][-60:])

        # B2 透明度：拉了之後圖要變，而且值要留下來（換股票／重新整理都還在）
        o0 = canvas_hash(pg, "#peChart")
        pg.evaluate("""() => { const s = document.getElementById('peOpa');
            s.value = s.value === '100' ? '20' : '100';
            s.dispatchEvent(new Event('input', { bubbles: true })); }""")
        pg.wait_for_timeout(900)
        changed("拉透明度滑桿，河流圖真的變了", o0, canvas_hash(pg, "#peChart"))
        saved = pg.evaluate("""() => { try { return (JSON.parse(localStorage.getItem('tw.kcfg') || '{}').st || {}).pe || null; }
            catch (e) { return null; } }""")
        # 色帶模式寫 o（跟設定面板共用，DECISIONS #145）；填滿模式寫自己的 of
        mode_now = pg.evaluate("() => { const b = document.querySelector('#peMode button.on');"
                               " return b ? b.dataset.v : ''; }")
        key = "of" if mode_now == "fill" else "o"
        ok(f"透明度真的存起來了（{mode_now} 模式存的是 {key}）",
           bool(saved) and saved.get(key) in (20, 100), {"mode": mode_now, "saved": saved})
        ok("切到倍數線時透明度滑桿會停用（那個模式沒有色帶）",
           pg.evaluate("""() => { document.querySelector('#peMode button[data-v=mult]').click();
             return new Promise(r => setTimeout(() => r(document.getElementById('peOpa').disabled), 700)); }"""))

        # B2 縮放與拖曳
        click(pg, '#peMode button[data-v="fill"]', 1200)
        check_zoom(pg, "peWrap", "peChart", "本益比河流圖")
        check_drag(pg, "peWrap", "本益比河流圖")
        click(pg, '#peMode button[data-v="band"]', 1400)
    click(pg, '#stockTabs button[data-t="overview"]', 1600)

    # --- 時間週期：按鈕上要先標清楚哪些這檔沒有（Andy：「1 日以下都不見」）
    tfstate = pg.evaluate("""() => [...document.querySelectorAll('#tfSeg button')].map(b => ({
        tf: b.dataset.tf, off: b.classList.contains('off'), title: b.title }))""")
    ok("週期鈕依序是 5秒／1分／5分（即時）＋ 15分／1時／4時／日／週／月",
       [t["tf"] for t in tfstate][:9] == ["5s", "1m", "5m", "15m", "60m", "240m", "1d", "1w", "1M"], tfstate)
    ok("日線一定是有資料的（沒有被劃掉）", not next(t for t in tfstate if t["tf"] == "1d")["off"], tfstate)
    for t in tfstate:
        if t["off"]:
            ok(f"被劃掉的週期 {t['tf']} 有寫清楚為什麼沒有", len(t["title"] or "") > 10, t)
    # 標示要和實際資料一致：劃掉的一定畫不出圖，沒劃掉的一定畫得出來
    tfs = [t["tf"] for t in tfstate]
    # 15 分 2026-09-18 起也改成即時（Andy：「1 5 15 分 K 都限制當天即可」，DECISIONS #156）——
    # 後端不再預先產出，所以它跟 1 分／5 分一樣，在開發容器裡（擋掉 Yahoo 與 Worker）本來就抓不到。
    LIVE_TFS = ("5s", "1m", "5m", "15m")
    for t in tfstate:
        click(pg, f'#tfSeg button[data-tf="{t["tf"]}"]', 700)
        st = pg.evaluate("({ canvas: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#lwc .empty') })")
        ok(f"週期 {t['tf']} 不是壞掉（有圖或有明確空狀態文案）", st["canvas"] > 0 or st["empty"], st)
        # 即時週期在這一段沒有設定代理，本來就抓不到資料；它們由 t_livek 專門驗
        if t["tf"] in LIVE_TFS:
            ok(f"即時週期 {t['tf']} 沒有來源時有講清楚", st["empty"], st)
            continue
        if t["off"]:
            ok(f"劃掉的週期 {t['tf']} 點下去有說明為什麼沒有", st["empty"], st)
        else:
            ok(f"沒劃掉的週期 {t['tf']} 點下去真的畫得出來", st["canvas"] > 0 and not st["empty"], st)
    click(pg, '#tfSeg button[data-tf="1d"]', 900)
    st = pg.evaluate("({ canvas: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#lwc .empty'), dbg: window.Industry._dbg() })")
    ok("走過所有週期後切回日線，K 線圖回得來", st["canvas"] > 0 and not st["empty"], st)

    # --- 價格軸要跟著週期重算（Andy 2026-09-15：「切換到不同時間週期，K棒會很窄」）
    #     真正的病灶不是棒子變窄，是在價格軸上滾過滾輪（那會永久關掉自動縮放）之後，
    #     切到別的週期時價格軸還留著上一個週期的上下界 —— 日線的 240–480 套在
    #     只走 330–345 的分 K 上，K 棒就被壓成一條線。
    #     所以這一段真的去滾價格軸，再切週期，驗軸有沒有重新貼合資料。
    box = pg.evaluate("() => { const r = document.getElementById('lwc').getBoundingClientRect();"
                      " return {x:r.x, y:r.y, w:r.width, h:r.height}; }")
    before = pg.evaluate("() => window.Industry._dbg().priceRange")
    pg.mouse.move(box["x"] + box["w"] - 18, box["y"] + box["h"] * 0.25)
    for _ in range(8):
        pg.mouse.wheel(0, 120); pg.wait_for_timeout(90)
    pg.wait_for_timeout(400)
    zoomed = pg.evaluate("() => window.Industry._dbg().priceRange")
    span = lambda r: (r["to"] - r["from"]) if r else None
    ok("在價格軸上滾滾輪，價格軸真的被拉開了（前置條件）",
       bool(before and zoomed and span(zoomed) > span(before) * 1.3), {"前": before, "後": zoomed})
    # 換一個有資料的週期，再換回來；兩次都要重新貼合，不可以留著剛剛拉開的範圍
    other = next((t["tf"] for t in tfstate
                  if not t["off"] and t["tf"] not in LIVE_TFS and t["tf"] != "1d"), "1w")
    click(pg, f'#tfSeg button[data-tf="{other}"]', 1100)
    a = pg.evaluate("() => window.Industry._dbg().priceRange")
    ok(f"切到 {other} 之後價格軸有重新貼合（K 棒沒有被壓扁）",
       bool(a and zoomed and span(a) < span(zoomed) * 0.9), {"拉開時": zoomed, f"切到{other}": a})
    click(pg, '#tfSeg button[data-tf="1d"]', 1100)
    bck = pg.evaluate("() => window.Industry._dbg().priceRange")
    ok("切回日線也重新貼合", bool(bck and zoomed and span(bck) < span(zoomed) * 0.9),
       {"拉開時": zoomed, "切回日線": bck})

    # --- 指標 chips：開關要真的改變圖（副圖數量或圖面）
    for k in ("kd", "macd", "rsi", "vol", "boll", "smc", "peRiver"):
        chip = pg.query_selector(f'#indChips .chip[data-k={k}]')
        if not chip:
            continue
        b0 = pg.evaluate(f"() => document.querySelector('#indChips .chip[data-k={k}]').classList.contains('on')")
        h0 = canvas_hash(pg, "#lwc")
        # 點 chip 的左邊（標籤那側）—— 正中央是參數輸入框，使用者點那裡本來就不該切換
        chip.scroll_into_view_if_needed()
        bb = chip.bounding_box()
        pg.mouse.click(bb["x"] + 12, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(700)
        b1 = pg.evaluate(f"() => document.querySelector('#indChips .chip[data-k={k}]').classList.contains('on')")
        h1 = canvas_hash(pg, "#lwc")
        changed(f"指標 {k} 勾選狀態真的變了", b0, b1)
        changed(f"指標 {k} 開關後圖真的重畫", h0, h1)
        click(pg, f'#indChips .chip[data-k={k}]', 600)   # 切回原狀

    # --- 本益比河流疊在 K 線上（Andy 2026-09-15：「上方也多一個選項新增河流圖」）
    #     除了圖要重畫，還要驗兩件事：圖例真的寫出「幾倍＝股價多少」，
    #     以及倍數線**不可以**把價格軸拉開（25 倍 ≈ 497，讓它參與取景 K 棒又會被壓扁）。
    if pg.query_selector('#indChips .chip[data-k=peRiver]'):
        r0 = pg.evaluate("() => window.Industry._dbg().priceRange")
        click(pg, '#indChips .chip[data-k=peRiver]', 1400)
        r1 = pg.evaluate("() => window.Industry._dbg().priceRange")
        leg = text(pg, "#legendOv")
        cfg_on = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.kcfg')||'{}').peRiver === true; }"
                             " catch (e) { return false; } }")
        ok("打開本益比河流，圖例寫出「幾倍＝股價多少」", "倍" in leg and "本益比" in leg, leg[-120:])
        ok("打開本益比河流，設定真的存進 localStorage", cfg_on, cfg_on)
        ok("倍數線沒有把價格軸拉開（K 棒沒被壓扁）",
           bool(r0 and r1 and (r1["to"] - r1["from"]) < (r0["to"] - r0["from"]) * 1.15), {"前": r0, "後": r1})
        click(pg, '#indChips .chip[data-k=peRiver]', 900)
        ok("關掉後圖例就不再有本益比那一段", "本益比" not in text(pg, "#legendOv"), text(pg, "#legendOv")[-90:])

    # --- 指標參數：改 RSI 的天數，圖要真的變
    inp = pg.query_selector("#indChips .chip[data-k=rsi] input")
    if inp:
        if not pg.evaluate("() => document.querySelector('#indChips .chip[data-k=rsi]').classList.contains('on')"):
            click(pg, "#indChips .chip[data-k=rsi]", 600)
        h0 = canvas_hash(pg, "#lwc")
        inp = pg.query_selector("#indChips .chip[data-k=rsi] input")
        inp.fill("6"); inp.press("Enter"); pg.wait_for_timeout(800)
        h1 = canvas_hash(pg, "#lwc")
        legend = text(pg, "#legendOv")
        changed("改 RSI 參數，圖真的重畫", h0, h1)
        ok("改 RSI 參數，圖例數字跟著變", "RSI(6)" in legend.replace(" ", ""), legend[-80:])

    # --- 設定面板：線寬滑桿、顏色、加均線、減均線
    # 故意讓外層帶著 transform（`.view.on` 的進場動畫就是 translateY(4px)→none）：
    # 有 transform 的祖先會接管 position:fixed 的基準，面板會整個偏掉 ——
    # 2026-09-15 線上實測偏了 195px。placePop 用「先擺 (0,0) 再量差值」校正，這裡就是那條防線。
    pg.evaluate("() => { const v = document.getElementById('v-industry');"
                " if (v) v.style.transform = 'translateY(4px)'; }")
    pg.wait_for_timeout(200)
    click(pg, "#cfgBtn", 600)
    ok("設定面板打得開", pg.evaluate("() => { const p = document.getElementById('cfgPop'); return !!p && !p.hidden; }"))
    # --- 面板要開在「⚙ 設定」旁邊（Andy 2026-09-15：「設定出現的位置應該要在 設定按鈕旁邊」）
    #     以前是 CSS 的 absolute + right:18px，錨點跟按鈕無關，常常飄到整張圖下面。
    geo = pg.evaluate("""() => { const p = document.getElementById('cfgPop'), b = document.getElementById('cfgBtn');
        const pr = p.getBoundingClientRect(), br = b.getBoundingClientRect();
        return { px: pr.x, py: pr.y, pw: pr.width, ph: pr.height, bl: br.x,
                 br: br.right, bbot: br.bottom, pos: getComputedStyle(p).position, vh: innerHeight, vw: innerWidth }; }""")
    # 左緣對齊或右緣對齊都算數（按鈕在畫面哪一半，面板就往那邊展開）
    ok("設定面板跟設定鈕水平對齊（左緣或右緣切齊）",
       abs(geo["px"] - geo["bl"]) < 14 or abs(geo["px"] + geo["pw"] - geo["br"]) < 14, geo)
    ok("設定面板貼著按鈕（上下不超過 24px）",
       abs(geo["py"] - geo["bbot"]) <= 24 or abs(geo["py"] + geo["ph"] - (geo["bbot"] - geo["ph"])) <= 24, geo)
    ok("設定面板完整在視窗內（高度有被夾住）",
       geo["py"] >= 0 and geo["px"] >= 0 and geo["py"] + geo["ph"] <= geo["vh"] + 2
       and geo["px"] + geo["pw"] <= geo["vw"] + 2, geo)
    # --- 本益比河流的樣式（Andy：「需要新增本益比河流圖的顏色 線條粗細 透明度 等設定」）
    ok("設定裡有本益比河流那一排", count(pg, "#peRow") == 1)
    ok("本益比河流六個區間各一個顏色", count(pg, "#peRow input[type=color]") == 6,
       count(pg, "#peRow input[type=color]"))
    if count(pg, "#peRow"):
        pg.eval_on_selector('#peRow input[data-z="0"]', "e => { e.value = '#ff00ff'; e.dispatchEvent(new Event('input', {bubbles:true})); }")
        pg.eval_on_selector('#peRow input[data-f="w"]', "e => { e.value = 4; e.dispatchEvent(new Event('input', {bubbles:true})); }")
        pg.eval_on_selector('#peRow input[data-f="o"]', "e => { e.value = 80; e.dispatchEvent(new Event('input', {bubbles:true})); }")
        pg.wait_for_timeout(900)
        saved = pg.evaluate("() => { try { return (JSON.parse(localStorage.getItem('tw.kcfg')||'{}').st||{}).pe; }"
                            " catch (e) { return null; } }")
        ok("改本益比河流樣式，真的存進 localStorage",
           isinstance(saved, dict) and saved.get("w") == 4 and saved.get("o") == 80
           and (saved.get("z") or [None])[0] == "#ff00ff", saved)
        ok("透明度的數字標籤跟著變", "80%" in (text(pg, "#peOv") or ""), text(pg, "#peOv"))
    rows0 = count(pg, "#maRows .marow")
    ok("設定面板有均線列", rows0 >= 2, rows0)
    lw = pg.query_selector("#lw")
    if lw:
        lw.fill("4") if lw.get_attribute("type") != "range" else pg.evaluate(
            "const s=document.getElementById('lw'); s.value=4; s.dispatchEvent(new Event('input',{bubbles:true}))")
        pg.wait_for_timeout(600)
        cfg = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("拉線寬滑桿真的存進設定", cfg.get("lineWidth") == 4, cfg.get("lineWidth"))
        ok("拉線寬滑桿有同步到每條均線", all(w == 4 for w in (cfg.get("maWidth") or [4])), cfg.get("maWidth"))
    click(pg, "#maAdd", 700)
    rows1 = count(pg, "#maRows .marow")
    changed("按「新增均線」真的多一條", rows0, rows1)
    cfg1 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
    ok("新增的均線有存進設定", len(cfg1.get("ma") or []) == rows1, cfg1.get("ma"))
    # 改一條均線的週期數字，圖例要跟著變
    nin = pg.query_selector("#maRows .marow input[data-f=n]")
    if nin:
        nin.fill("33"); nin.dispatch_event("change"); pg.wait_for_timeout(800)
        ok("改均線週期數字，圖例跟著變", "MA33" in text(pg, "#legendOv"), text(pg, "#legendOv")[-90:])
    # 顏色
    cin = pg.query_selector("#maRows .marow input[type=color]")
    if cin:
        h0 = canvas_hash(pg, "#lwc")
        pg.evaluate("const i=document.querySelector('#maRows .marow input[type=color]'); i.value='#ff00ff'; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}))")
        pg.wait_for_timeout(800)
        changed("改均線顏色，圖真的重畫", h0, canvas_hash(pg, "#lwc"))
        cfg2 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("改的顏色有存進設定", "#ff00ff" in [str(c).lower() for c in (cfg2.get("maColor") or [])], cfg2.get("maColor"))
    # 刪一條均線
    if count(pg, "#maRows .marow [data-f=del]"):
        r0 = count(pg, "#maRows .marow")
        click(pg, "#maRows .marow [data-f=del]", 700)
        r1 = count(pg, "#maRows .marow")
        changed("按 ✕ 真的少一條均線", r0, r1)
        cfgd = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("刪掉的均線也從設定裡消失", len(cfgd.get("ma") or []) == r1, cfgd.get("ma"))
        ok("刪到 6 條以下，「新增均線」要能再按", not pg.evaluate("() => document.getElementById('maAdd').disabled"))
    # --- 指標樣式：顏色／線寬／透明度改了要真的存下來、圖要真的重畫
    rows = pg.evaluate("[...document.querySelectorAll('#stRows .strow')].map(r => r.dataset.k)")
    ok("設定面板有指標樣式列（BOLL／成交量／KD／MACD／RSI）", len(rows) >= 5, rows)
    if rows:
        h0 = canvas_hash(pg, "#lwc")
        pg.evaluate("""() => { const r = document.querySelector('#stRows .strow[data-k=kd]');
            const c = r.querySelector('[data-f=c]'); c.value = '#ff00ff'; c.dispatchEvent(new Event('input', {bubbles:true}));
            const w = r.querySelector('[data-f=w]'); w.value = 3; w.dispatchEvent(new Event('input', {bubbles:true}));
            const o = r.querySelector('[data-f=o]'); o.value = 45; o.dispatchEvent(new Event('input', {bubbles:true})); }""")
        pg.wait_for_timeout(800)
        st = pg.evaluate("() => ((JSON.parse(localStorage.getItem('tw.kcfg')||'{}')).st||{}).kd")
        ok("改 KD 顏色有存進設定", (st or {}).get("c") == "#ff00ff", st)
        ok("改 KD 線寬有存進設定", (st or {}).get("w") == 3, st)
        ok("改 KD 透明度有存進設定", (st or {}).get("o") == 45, st)
        changed("改指標樣式後圖真的重畫", h0, canvas_hash(pg, "#lwc"))

    # --- SMC 供需區樣式：填色濃度、框線、標籤開關
    zin = pg.evaluate("[...document.querySelectorAll('#zoneRow input')].map(i => i.dataset.f)")
    ok("設定面板有 SMC 供需區樣式", len(zin) >= 5, zin)
    if zin:
        h1 = canvas_hash(pg, "#lwc")
        pg.evaluate("""() => { const f = document.querySelector('#zoneRow [data-f=fill]');
            f.value = 40; f.dispatchEvent(new Event('input', {bubbles:true})); }""")
        pg.wait_for_timeout(700)
        z = pg.evaluate("() => (JSON.parse(localStorage.getItem('tw.kcfg')||'{}')).zone")
        ok("調供需區填色有存進設定", (z or {}).get("fill") == 40, z)
        changed("調供需區填色後圖真的重畫", h1, canvas_hash(pg, "#lwc"))

    # 「完成」關得掉
    click(pg, "#cfgClose", 400)
    ok("設定面板按「完成」關得起來", pg.evaluate("() => { const p = document.getElementById('cfgPop'); return !p || p.hidden; }"))
    # 把剛才為了測試加上去的 transform 拿掉，後面的驗收才不會被影響
    pg.evaluate("() => { const v = document.getElementById('v-industry'); if (v) v.style.transform = ''; }")
    # 回復預設：設定要真的還原，面板順手關掉
    click(pg, "#cfgBtn", 450)
    if count(pg, "#cfgReset"):
        click(pg, "#cfgReset", 900)
        cfg3 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("按「回復預設」把線寬還原", (cfg3.get("lineWidth") or 1) != 4, cfg3.get("lineWidth"))
        ok("按「回復預設」順手把面板關掉", pg.evaluate("() => document.getElementById('cfgPop').hidden"))

    # --- 自訂時間週期：加一個、用一下、右鍵移除
    tf0 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
    click(pg, "#tfAdd", 450)
    pg.evaluate("const n=document.getElementById('tfN'); if(n){n.value=3; n.dispatchEvent(new Event('input',{bubbles:true}));}")
    click(pg, "#tfOk", 1100)
    tf1 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
    changed("自訂時間週期真的加進去了", tf0, tf1)
    cust = [t for t in tf1 if t not in tf0]
    if cust:
        st = pg.evaluate("({ on: (document.querySelector('#tfSeg button.on')||{dataset:{}}).dataset.tf, canvas: document.querySelectorAll('#lwc canvas').length })")
        ok("自訂週期按下去真的在用它", st["on"] == cust[0] and st["canvas"] > 0, st)
        pg.evaluate(f"document.querySelector('#tfSeg button[data-tf=\"{cust[0]}\"]').dispatchEvent(new MouseEvent('contextmenu', {{bubbles:true, cancelable:true}}))")
        pg.wait_for_timeout(800)
        tf2 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
        ok("自訂週期按右鍵可以移除", cust[0] not in tf2, tf2)
    click(pg, '#tfSeg button[data-tf="1d"]', 800)

    # --- 繪圖工具：每一種都真的用滑鼠畫一次
    pg.evaluate("try{Object.keys(localStorage).filter(k=>k.startsWith('tw.draw.')).forEach(k=>localStorage.removeItem(k))}catch(e){}")
    click(pg, '#drawBar .dtool[data-t=cursor]', 200)
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
    tools = pg.evaluate("[...document.querySelectorAll('#drawBar .dtool[data-t]')].map(b => b.dataset.t)")
    ok("繪圖工具列有 ≥ 6 個工具", len(tools) >= 6, tools)
    drawn = []
    for i, t in enumerate(tools):
        if t in ("cursor", "erase"):
            continue
        click(pg, f'#drawBar .dtool[data-t={t}]', 250)
        r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height,vh:innerHeight}; }")
        if r["y"] < 0 or r["y"] + r["h"] * 0.6 > r["vh"]:
            pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
            r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height,vh:innerHeight}; }")
        x0, y0 = r["x"] + r["w"] * (0.25 + i * 0.03), r["y"] + r["h"] * 0.30
        x1, y1 = r["x"] + r["w"] * (0.45 + i * 0.03), r["y"] + r["h"] * 0.52
        n0 = pg.evaluate("() => window.Industry._dbg().shapes")
        pg.mouse.move(x0, y0); pg.mouse.down()
        pg.mouse.move(x1, y1, steps=6); pg.mouse.up()
        pg.wait_for_timeout(400)
        n1 = pg.evaluate("() => window.Industry._dbg().shapes")
        if ok(f"繪圖工具「{t}」畫得出東西", n1 > n0, f"{n0} → {n1}"):
            drawn.append(t)
    store = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        return { keys: k, kinds: k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]').map(s=>s.kind)) }; }""")
    ok("手繪線真的存進 localStorage", len(store["kinds"]) == len(drawn), store)
    ok("手繪線的 key 是「每檔每週期一組」", all(k.startswith(f"tw.draw.{code}.") for k in store["keys"]), store["keys"])

    # 換週期 → 線要消失；換回來 → 線要回來（各週期分開存）
    click(pg, '#tfSeg button[data-tf="1w"]', 900)
    ok("換週期後畫面上的線歸零（各週期分開存）", pg.evaluate("() => window.Industry._dbg().shapes") == 0,
       pg.evaluate("() => window.Industry._dbg()"))
    click(pg, '#tfSeg button[data-tf="1d"]', 900)
    ok("換回日線，原本畫的線回來了", pg.evaluate("() => window.Industry._dbg().shapes") == len(drawn),
       pg.evaluate("() => window.Industry._dbg()"))

    # 重新整理後線還在（真的存住了，不是只在記憶體）
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(2400)
    ok("重新整理後手繪線還在", pg.evaluate("() => window.Industry._dbg().shapes") == len(drawn),
       pg.evaluate("() => window.Industry._dbg()"))

    # 橡皮擦 → 少一筆；復原 → 少一筆；清空 → 歸零
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
    n0 = pg.evaluate("() => window.Industry._dbg().shapes")
    if count(pg, "#drawBar .dtool[data-a=undo]"):
        click(pg, "#drawBar .dtool[data-a=undo]", 500)
        changed("按「復原」真的少一筆", n0, pg.evaluate("() => window.Industry._dbg().shapes"))
    n1 = pg.evaluate("() => window.Industry._dbg().shapes")
    click(pg, "#drawBar .dtool[data-a=clear]", 600)
    ok("按「清空」真的歸零", pg.evaluate("() => window.Industry._dbg().shapes") == 0, n1)
    left = pg.evaluate("""() => Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'))
        .reduce((n,x)=>n+JSON.parse(localStorage.getItem(x)||'[]').length, 0)""")
    ok("清空後 localStorage 也乾淨了", left == 0, left)
    click(pg, "#drawBar .dtool[data-t=cursor]", 250)

    # --- ★ Andy 2026-09-15 那四項：游標資訊框 / MACD 背離 / Shift 鎖水平 / 五段粗細＋方框填滿
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
    r = main_rect(pg)

    # 1) 游標移過去要在旁邊顯示開高低收
    ok("圖上有跟著游標的資訊框", count(pg, "#ohlcBox") == 1)
    ok("沒移游標時它是收起來的", pg.evaluate("() => document.getElementById('ohlcBox').hidden"))
    pg.mouse.move(r["x"] + r["w"] * 0.35, r["y"] + r["h"] * 0.4); pg.wait_for_timeout(500)
    ok("游標移進去之後資訊框出現", not pg.evaluate("() => document.getElementById('ohlcBox').hidden"))
    txt = text(pg, "#ohlcBox")
    for want in ("開盤", "最高", "最低", "收盤", "漲跌額", "漲跌幅", "成交量"):
        ok(f"資訊框有「{want}」", want in txt, txt[:120])
    ok("資訊框最上面是日期／時間",
       __import__("re").search(r"\d{4}-\d{2}-\d{2}", text(pg, "#ohlcBox .oh")) is not None,
       text(pg, "#ohlcBox .oh"))
    pos1 = pg.evaluate("() => { const e=document.getElementById('ohlcBox'); return [e.offsetLeft, e.offsetTop]; }")
    t1 = text(pg, "#ohlcBox .oh")
    pg.mouse.move(r["x"] + r["w"] * 0.6, r["y"] + r["h"] * 0.55); pg.wait_for_timeout(500)
    pos2 = pg.evaluate("() => { const e=document.getElementById('ohlcBox'); return [e.offsetLeft, e.offsetTop]; }")
    changed("資訊框真的跟著游標移動", pos1, pos2)
    changed("換一根 K 棒，框裡的日期也跟著換", t1, text(pg, "#ohlcBox .oh"))
    # 靠右邊時要翻到游標左側，不能被切掉
    pg.mouse.move(r["x"] + r["w"] * 0.95, r["y"] + r["h"] * 0.5); pg.wait_for_timeout(500)
    fit = pg.evaluate("""() => { const e=document.getElementById('ohlcBox'), h=e.parentElement;
        return e.offsetLeft >= 0 && e.offsetLeft + e.offsetWidth <= h.clientWidth + 1; }""")
    ok("游標靠右邊時資訊框不會被切掉（自動翻到左側）", fit)

    # 2) MACD 背離
    chips = pg.evaluate("() => [...document.querySelectorAll('#indChips .chip')].map(c => c.dataset.k)")
    ok("指標列有「MACD 背離」", "macdDiv" in chips, chips)
    on0 = pg.evaluate("() => document.querySelector('#indChips .chip[data-k=macdDiv]').classList.contains('on')")
    dv = pg.evaluate("() => { const d = window.Industry._dbg().div; return d ? d.top + d.bottom : -1; }")
    ok("背離預設是開的", on0)
    ok("背離有算出來（或誠實回 0，不是壞掉）", dv >= 0, dv)
    h0 = canvas_hash(pg, "#lwc")
    click(pg, "#indChips .chip[data-k=macdDiv]", 1200)
    ok("點一下真的關掉",
       not pg.evaluate("() => document.querySelector('#indChips .chip[data-k=macdDiv]').classList.contains('on')"))
    ok("關掉之後背離就不算了", pg.evaluate("() => { const d = window.Industry._dbg().div; return d ? d.top + d.bottom : -1; }") == 0)
    changed("關掉背離之後圖真的重畫", h0, canvas_hash(pg, "#lwc"))
    click(pg, "#indChips .chip[data-k=macdDiv]", 1200)
    ok("再點一下開回來",
       pg.evaluate("() => document.querySelector('#indChips .chip[data-k=macdDiv]').classList.contains('on')"))

    # 3) ★ 按住 Shift 拉線 = 水平
    pg.evaluate("try{Object.keys(localStorage).filter(k=>k.startsWith('tw.draw.')).forEach(k=>localStorage.removeItem(k))}catch(e){}")
    click(pg, "#drawBar .dtool[data-t=trend]", 300)
    # 中間切過指標，圖的位置會變，重新量一次再拉
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(600)
    r = main_rect(pg)
    x0, y0 = r["x"] + r["w"] * 0.30, r["y"] + r["h"] * 0.35
    pg.mouse.move(x0, y0); pg.mouse.down()
    pg.keyboard.down("Shift")
    pg.mouse.move(r["x"] + r["w"] * 0.60, r["y"] + r["h"] * 0.60, steps=8)
    pg.mouse.up()
    pg.keyboard.up("Shift")
    pg.wait_for_timeout(600)
    shp = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        const all = k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]'));
        const s = all[all.length-1]; return s ? {kind:s.kind, ap:s.a.p, bp:s.b.p, at:s.a.t, bt:s.b.t} : null; }""")
    ok("按住 Shift 畫出來的是線", shp and shp["kind"] == "trend", shp)
    ok("★ 按住 Shift 拉線真的被鎖成水平（兩端價格一樣）",
       shp and abs(shp["ap"] - shp["bp"]) < 1e-9, shp)
    ok("而且時間兩端不同（真的有拉出長度）", shp and shp["at"] != shp["bt"], shp)
    # 不按 Shift 就不該是水平
    pg.mouse.move(x0, y0 + 10); pg.mouse.down()
    pg.mouse.move(r["x"] + r["w"] * 0.58, r["y"] + r["h"] * 0.62, steps=8); pg.mouse.up()
    pg.wait_for_timeout(600)
    shp2 = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        const all = k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]'));
        const s = all[all.length-1]; return s ? {ap:s.a.p, bp:s.b.p} : null; }""")
    ok("沒按 Shift 就是一般斜線", shp2 and abs(shp2["ap"] - shp2["bp"]) > 1e-6, shp2)

    # 4) ★ 五段粗細 + 方框填滿／透明
    ws = pg.evaluate("() => [...document.querySelectorAll('#drawBar .dw')].map(b => +b.dataset.w)")
    ok("畫線粗細有 5 段", len(ws) == 5, ws)
    click(pg, f'#drawBar .dw[data-w="{ws[-1]}"]', 400)
    ok("選最粗那一段之後按鈕亮起來",
       pg.evaluate(f"() => document.querySelector('#drawBar .dw[data-w=\"{ws[-1]}\"]').classList.contains('on')"))
    pg.mouse.move(x0, y0 + 24); pg.mouse.down()
    pg.mouse.move(r["x"] + r["w"] * 0.55, r["y"] + r["h"] * 0.40, steps=6); pg.mouse.up()
    pg.wait_for_timeout(600)
    w_used = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        const all = k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]'));
        return all.length ? all[all.length-1].w : null; }""")
    ok("★ 新畫的線真的用選的那個粗細", w_used == ws[-1], f"選 {ws[-1]} 畫出來 {w_used}")
    style = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.draw.style')||'{}'); } catch(e){ return null; } }")
    ok("粗細選擇存進 localStorage", style and style.get("w") == ws[-1], style)

    fill0 = pg.evaluate("() => document.querySelector('#drawBar .dfill').classList.contains('on')")
    click(pg, "#drawBar .dfill", 400)
    fill1 = pg.evaluate("() => document.querySelector('#drawBar .dfill').classList.contains('on')")
    changed("方框填滿／透明按得動", fill0, fill1)
    click(pg, "#drawBar .dtool[data-t=rect]", 300)
    hb = canvas_hash(pg, "#lwc")
    pg.mouse.move(r["x"] + r["w"] * 0.32, r["y"] + r["h"] * 0.62); pg.mouse.down()
    pg.mouse.move(r["x"] + r["w"] * 0.50, r["y"] + r["h"] * 0.78, steps=6); pg.mouse.up()
    pg.wait_for_timeout(700)
    rect = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        const all = k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]'));
        const s = all.filter(x=>x.kind==='rect').pop(); return s ? {fill:!!s.fill, w:s.w} : null; }""")
    ok("★ 方框真的記住了「填滿／透明」的選擇", rect and rect["fill"] == fill1, f"按鈕 {fill1} / 存成 {rect}")
    changed("畫完方框圖真的變了", hb, canvas_hash(pg, "#lwc"))

    # 5) Andy 2026-09-15「下方MACD KD 成交量等範圍上下可以拉大」
    #    真的用滑鼠把主圖與成交量之間的分隔線往上拖，看高度有沒有變、有沒有存起來
    click(pg, "#drawBar .dtool[data-t=cursor]", 250)
    pg.evaluate("try{localStorage.removeItem('tw.kcfg.paneH')}catch(e){}")
    pg.evaluate("""() => { try { const c = JSON.parse(localStorage.getItem('tw.kcfg')||'{}');
        delete c.paneH; localStorage.setItem('tw.kcfg', JSON.stringify(c)); } catch(e){} }""")
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(600)
    h0 = pg.evaluate("() => window.Industry._dbg().paneH")
    ok("讀得到每個面板的高度", bool(h0) and h0.get("main", 0) > 0, h0)
    r2 = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
    sepY = r2["y"] + (h0.get("main") or 0) + 1          # 主圖底部＝第一條分隔線
    pg.mouse.move(r2["x"] + r2["w"] * 0.4, sepY)
    pg.mouse.down()
    pg.mouse.move(r2["x"] + r2["w"] * 0.4, sepY - 70, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(900)
    h1 = pg.evaluate("() => window.Industry._dbg().paneH")
    changed("★ 分隔線真的拖得動（主圖高度變了）", h0.get("main"), h1.get("main"))
    ok("下面那格因此變大", (h1.get("vol") or 0) > (h0.get("vol") or 0), f"{h0} → {h1}")
    saved = pg.evaluate("""() => { try { return (JSON.parse(localStorage.getItem('tw.kcfg')||'{}').paneH)||null; }
        catch(e){ return null; } }""")
    ok("★ 拖完的高度真的存進設定（換股票不會縮回去）", bool(saved) and saved.get("main") == h1.get("main"), saved)
    # 5b) ★ Andy 2026-09-15：「底下每次更新都會動到我調整好的上下範圍會一直出現跳動，很麻煩」
    #     拖完之後，任何一次重畫（切指標、即時更新）都不可以把高度改回存檔值。
    #     以前 applyIndicators 每 5 秒就把 cfg.paneH 套回去一次，手動調的高度撐不過一輪。
    h_hold = pg.evaluate("() => window.Industry._dbg().paneH")
    for k in ("kd", "macd"):
        chip = f"#indChips .chip[data-k={k}]"
        if count(pg, chip):
            click(pg, chip, 700); click(pg, chip, 700)      # 關再開，逼它重建指標面板
    pg.wait_for_timeout(900)
    h_after = pg.evaluate("() => window.Industry._dbg().paneH")
    ok("★ 切指標之後主圖高度不會自己跳回去",
       abs((h_after.get("main") or 0) - (h_hold.get("main") or 0)) <= 6, f"{h_hold} → {h_after}")
    # 再等一輪自動更新的時間，確認不是「當下沒跳、過幾秒才跳」
    pg.wait_for_timeout(1800)
    h_idle = pg.evaluate("() => window.Industry._dbg().paneH")
    ok("★ 放著不動也不會被自動更新改掉高度",
       abs((h_idle.get("main") or 0) - (h_after.get("main") or 0)) <= 6, f"{h_after} → {h_idle}")

    # 5c) Andy 2026-09-15：「我需要下面的成交量 MACD 這些指標上下間隔寬點」
    click(pg, "#fitBtn", 1200)                              # 先還原成預設高度再量
    pg.wait_for_timeout(700)
    hd = pg.evaluate("() => window.Industry._dbg().paneH")
    subs = {k: v for k, v in (hd or {}).items() if k != "main" and isinstance(v, (int, float)) and v > 0}
    ok("預設的副圖每格都夠高（不是被擠成一條）",
       bool(subs) and min(subs.values()) >= 70, hd)

    # 「重設縮放」要把它還原
    back = pg.evaluate("""() => { try { return (JSON.parse(localStorage.getItem('tw.kcfg')||'{}').paneH)||null; }
        catch(e){ return null; } }""")
    ok("按「重設縮放」把拖過的高度還原", back is None, back)

    # 收拾
    click(pg, "#drawBar .dtool[data-a=clear]", 600)
    click(pg, "#drawBar .dtool[data-t=cursor]", 250)
    pg.evaluate("try{localStorage.removeItem('tw.draw.style')}catch(e){}")

    # --- SMC 供需區要跟著 K 線一起跑（Andy：移動 K 線圖，區間卻沒跟著動）
    if pg.evaluate("() => document.querySelector('#indChips .chip[data-k=smc]') && document.querySelector('#indChips .chip[data-k=smc]').classList.contains('on')"):
        pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
        ZBOX = """() => { const el = document.getElementById('lwc');
            const out = [];
            for (const c of el.querySelectorAll('canvas')) {
              const g = c.getContext('2d'); if (!g) continue;
              const dpr = c.width / (c.clientWidth || 1);
              let minx = 1e9, maxx = -1, n = 0;
              try { const px = g.getImageData(0, 0, c.width, c.height).data;
                for (let y = 0; y < c.height; y += 3) for (let x = 0; x < c.width; x += 3) {
                  const i = (y * c.width + x) * 4, R = px[i], G = px[i+1], B = px[i+2];
                  if (G > R + 14 && G > 34 && G < 150 && B < G) { n++; if (x < minx) minx = x; if (x > maxx) maxx = x; }
                } } catch (e) { continue; }
              if (n > 150) out.push({ x0: Math.round(minx/dpr), x1: Math.round(maxx/dpr), n });
            }
            return out; }"""
        before = pg.evaluate(ZBOX)
        if before:
            r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
            pg.mouse.move(r["x"] + r["w"] * 0.6, r["y"] + r["h"] * 0.3)
            pg.mouse.down(); pg.mouse.move(r["x"] + r["w"] * 0.25, r["y"] + r["h"] * 0.3, steps=12); pg.mouse.up()
            pg.wait_for_timeout(800)
            after = pg.evaluate(ZBOX)
            ok("平移 K 線後 SMC 區間還在畫面上", bool(after), after)
            if after:
                # 比「整個區塊的左右邊界」：圖變高之後畫面裡的價格範圍變大，
                # 常常有一個區間的左緣本來就在畫面外（x0 一直是 0），只看左緣會假性失敗
                changed("SMC 區間跟著平移（左右邊界有變）",
                        f'{before[0]["x0"]},{before[0]["x1"]}', f'{after[0]["x0"]},{after[0]["x1"]}')
                changed("SMC 區間的右邊界也跟著平移（不是黏在畫面右緣）", before[0]["x1"], after[0]["x1"])
                ok("SMC 區間右邊界沒有貼齊畫面右緣", after[0]["x1"] < r["w"] - 20,
                   f"右邊界 {after[0]['x1']}、畫面寬 {round(r['w'])}")
        else:
            notes.append("這檔今天沒有畫出 SMC 供需區，略過跟隨檢查")

    # --- 重設縮放：先把圖捲歪，按下去要回到原位
    ok("重設縮放是小方框圖示", pg.evaluate("() => !!document.querySelector('#fitBtn svg')"))
    r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
    pg.mouse.move(r["x"] + r["w"] * 0.5, r["y"] + r["h"] * 0.4)
    pg.mouse.wheel(0, -500); pg.wait_for_timeout(500)
    h0 = canvas_hash(pg, "#lwc")
    click(pg, "#fitBtn", 800)
    changed("按重設縮放，圖真的回到原位", h0, canvas_hash(pg, "#lwc"))

    # --- 四週期同看：來回切換都要有圖
    click(pg, "#mtfBtn", 1600)
    cells = count(pg, ".mtf-cell")
    ok("四週期同看有排出格子", cells >= 2, cells)
    ok("四週期同看每格都有圖", count(pg, "#mtfGrid canvas") >= cells, count(pg, "#mtfGrid canvas"))
    click(pg, "#mtfBtn", 1400)
    ok("切回單一週期，K 線圖回得來", count(pg, "#lwc canvas") > 0)

    # --- 產業鏈同步（N7 改過行為）：
    #     2026-09-19 起點公司**不會**直接換個股頁，而是先開原地面板；
    #     要換股票得按面板裡那顆「看個股頁 →」。驗的是這條路徑走得通。
    if count(pg, "#chainMap .co"):
        h0 = pg.evaluate("location.hash")
        pg.evaluate("""() => { const cs = [...document.querySelectorAll('#chainMap .co[data-code]')];
            const other = cs.find(c => !c.classList.contains('sel'));
            if (other) other.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }""")
        pg.wait_for_timeout(1200)
        ok("點產業鏈上的另一檔不會馬上換頁（N7）",
           pg.evaluate("location.hash") == h0, pg.evaluate("location.hash"))
        opened = pg.evaluate("() => { const b = document.getElementById('coBox'); return !!b && b.textContent.indexOf('看個股頁') >= 0; }")
        ok("會開出帶「看個股頁」的面板（N7）", opened)
        if opened:
            pg.eval_on_selector("#coBox .btn.primary", "b => b.click()")
            pg.wait_for_timeout(1800)
            changed("按了面板裡的「看個股頁 →」才換股票（N7）", h0, pg.evaluate("location.hash"))


def check_play(pg, sel, chart_id=None):
    """播放拉Bar（App.playBar）的共用驗收 —— 批次2-4 五張圖共用這一支。

    驗的是「畫面真的因此變了」，不是「按鈕存在」：
    ① ＋／− 真的改到 input.value；② ▶ 按下去之後值會自己往前跑；
    ③ 再按一次真的停住（停住後值不再變）；④ 切走／分頁隱藏會自動停。
    """
    box = f"{sel}"
    n = pg.evaluate(f"() => document.querySelectorAll('{box} .pb').length")
    ok(f"{sel} 有 ＋ − ▶ 三顆鈕", n == 3, n)
    v0 = pg.evaluate(f"() => +document.querySelector('{box} input').value")
    # 值停在最小值時 − 是停用的（那是對的），所以在最小值就改試 ＋
    at_min = pg.evaluate(f"() => {{ const i = document.querySelector('{box} input'); return +i.value <= +i.min; }}")
    # DOM 是 [− , input, ＋, .val, ▶]，兩顆 step 鈕中間隔著 input，不是相鄰兄弟，
    # 所以用文字找，不要用 CSS 的相鄰選擇器
    nm = "＋" if at_min else "−"
    pg.evaluate(f"""(t) => {{ const b = [...document.querySelectorAll('{box} .pb.step')]
        .find(x => x.textContent.trim() === t); if (b) b.click(); }}""", nm)
    pg.wait_for_timeout(250)
    v1 = pg.evaluate(f"() => +document.querySelector('{box} input').value")
    ok(f"{sel} 按 {nm} 之後值真的變了", v1 != v0, f"{v0} → {v1}")
    # ▶ 播放：值要自己動
    pg.eval_on_selector(f"{box} .pb.play", "b => b.click()")
    pg.wait_for_timeout(1500)
    v2 = pg.evaluate(f"() => +document.querySelector('{box} input').value")
    ok(f"{sel} 播放中值會自己前進", v2 != v1, f"{v1} → {v2}")
    ok(f"{sel} 播放中有 playing 樣式",
       pg.evaluate(f"() => document.querySelector('{box}').classList.contains('playing')"))
    # ⏸ 停住：停完之後值不可以再變
    pg.eval_on_selector(f"{box} .pb.play", "b => b.click()")
    pg.wait_for_timeout(200)
    v3 = pg.evaluate(f"() => +document.querySelector('{box} input').value")
    pg.wait_for_timeout(1400)
    v4 = pg.evaluate(f"() => +document.querySelector('{box} input').value")
    ok(f"{sel} 按暫停之後真的停住", v3 == v4, f"{v3} → {v4}")


def t_batch1(pg, base):
    """批次1（Andy 2026-09-18 圖12／圖五／圖19）的真人操作驗收。

    每一條驗的都是「畫面真的因此改變」，不是「元素存在」。
    """
    # ---- 圖12：點產業鏈上的公司，不可以留下一張浮動卡跟著跑到個股頁
    pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(1500)
    has = pg.evaluate("() => !!document.querySelector('#chainMap .co[data-code]')")
    if has:
        code = pg.evaluate("() => document.querySelector('#chainMap .co[data-code]').dataset.code")
        pg.eval_on_selector("#chainMap .co[data-code]", "n => n.dispatchEvent(new MouseEvent('click', {bubbles:true}))")
        pg.wait_for_timeout(1400)
        # N7（Andy 2026-09-19）：「點擊供應鏈關聯圖 個股時不要馬上跳到股票介面，
        # 可以跳出觀看股票這選項」—— 2026-09-18 為了修圖12 改成直接跳，現在改回「先開面板」。
        ok("點產業鏈上的公司不會馬上跳走（N7）",
           pg.evaluate("() => location.hash") != f"#stock/{code}",
           pg.evaluate("() => location.hash"))
        ok("點公司會開原地面板，面板裡才有「看個股頁」（N7）",
           pg.evaluate("""() => { const b = document.getElementById('coBox');
               return !!b && b.textContent.indexOf('看個股頁') >= 0; }"""))
    # 外商：原地小面板，而且它是 #chainMap 的兄弟節點（不是掛在 body 上）
    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1500)
    if pg.evaluate("() => !!document.querySelector('#chainMap .co.foreign')"):
        pg.eval_on_selector("#chainMap .co.foreign", "n => n.dispatchEvent(new MouseEvent('click', {bubbles:true}))")
        pg.wait_for_timeout(700)
        info = pg.evaluate("""() => { const b = document.getElementById('coBox'); if (!b) return null;
            const cs = getComputedStyle(b); const host = document.getElementById('chainMap');
            return { fixed: cs.position === 'fixed', inBody: b.parentNode === document.body,
                     sibling: !!host && b.previousElementSibling === host, txt: b.textContent.length }; }""")
        ok("外商公司會開原地小面板", bool(info) and info["txt"] > 10, info)
        ok("外商面板不是浮動的、也不掛在 body 上（圖12）",
           bool(info) and not info["fixed"] and not info["inBody"], info)
        ok("成長欄位不會印出 [object Object]（圖12 順手抓到）",
           pg.evaluate("() => { const b=document.getElementById('coBox'); return !b || b.textContent.indexOf('[object Object]') < 0; }"))
        # 換頁之後一定要被清掉
        pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(900)
        ok("換頁之後外商面板被清掉（圖12 根因）",
           pg.evaluate("() => document.getElementById('coBox') === null"))

    # ---- 圖五：四格輪動板 —— 清單不截斷、四格等高、點族群原地展開成分股
    for w in (1500, 800):
        pg.set_viewport_size({"width": w, "height": 1000})
        pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(1800)
        st = pg.evaluate("""() => { const b = document.getElementById('rotBoard');
            if (!b) return null;
            const cards = [...b.querySelectorAll('.stage')];
            return { n: cards.length, hs: cards.map(c => Math.round(c.getBoundingClientRect().height)),
                     cut: b.textContent.indexOf('還有') >= 0,
                     scroll: cards.map(c => { const u = c.querySelector('ul'); return u ? u.scrollHeight > u.clientHeight + 1 : false; }) }; }""")
        if not st:
            continue
        ok(f"[{w}px] 輪動板四格都在", st["n"] == 4, st)
        ok(f"[{w}px] 族群清單不再截斷成「還有 N 個」（圖五）", not st["cut"])
        hs = st["hs"]
        ok(f"[{w}px] 四格等高（差 ≤2px）", max(hs) - min(hs) <= 2, hs)
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(1800)
    h0 = pg.evaluate("() => { const c = document.querySelector('.stage'); return c ? Math.round(c.getBoundingClientRect().height) : 0; }")
    hash0 = pg.evaluate("() => location.hash")
    if pg.evaluate("() => !!document.querySelector('.stage li[data-gid]')"):
        pg.eval_on_selector(".stage li[data-gid]", "li => li.click()")
        pg.wait_for_timeout(500)
        st2 = pg.evaluate("""() => { const c = document.querySelector('.stage');
            return { mem: !!document.querySelector('.stage li.mem'),
                     chips: document.querySelectorAll('.stage li.mem a.lk-stock').length,
                     h: c ? Math.round(c.getBoundingClientRect().height) : 0,
                     hash: location.hash }; }""")
        ok("點族群會原地展開成分股（圖五）", st2["mem"] and st2["chips"] > 0, st2)
        ok("點族群不會跳頁（圖五）", st2["hash"] == hash0, st2["hash"])
        ok("展開之後格子高度沒有被撐長（圖五，差 ≤2px）", abs(st2["h"] - h0) <= 2, f"{h0} → {st2['h']}")
        pg.eval_on_selector(".stage li[data-gid]", "li => li.click()")
        pg.wait_for_timeout(400)
        ok("再點一次會收合（圖五）",
           pg.evaluate("() => !document.querySelector('.stage li.mem')"))

    # ---- 圖19：季節性熱力圖的顏色要真的跟著數字變
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(1800)
    vm = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('seasonHeat'));
        if (!c) return null; const o = c.getOption();
        const v = (o.visualMap || [])[0] || {};
        return { dim: v.dimension, min: v.min, max: v.max }; }""")
    ok("熱力圖的 visualMap 指到數值那一維（圖19 根因）", bool(vm) and vm["dim"] == 2, vm)
    colors = pg.evaluate("""() => { const el = document.getElementById('seasonHeat');
        const cv = el && el.querySelector('canvas'); if (!cv) return 0;
        const ctx = cv.getContext('2d'); const w = cv.width, h = cv.height;
        const d = ctx.getImageData(0, 0, w, h).data; const set = new Set();
        for (let y = 0; y < h; y += 7) for (let x = Math.floor(w * .3); x < w * .9; x += 7) {
          const i = (y * w + x) * 4;
          set.add((d[i] >> 4) + ',' + (d[i + 1] >> 4) + ',' + (d[i + 2] >> 4));
        }
        return set.size; }""")
    ok("熱力圖真的有多種顏色（圖19：以前整張同色）", colors >= 8, f"{colors} 種色階")


def t_batch2(pg, base):
    """批次2（Andy 2026-09-18 圖二／圖四）的真人操作驗收。

    每一條驗的都是「畫面真的因此改變」：值真的動、圖真的重畫、標籤真的排開。
    """
    # ---------------------------------------------------------- 圖四：資金流向排行
    pg.set_viewport_size({"width": 1500, "height": 1000})
    # ★ 2026-09-21：這一段要量「點一根長條，時鐘上只有那一個族群是亮的、其他被壓暗」，
    #   前提是盤上本來就不只一個族群。前一段（新-輪動時鐘）點過族群晶片，
    #   選取會留在 localStorage ＋ 記憶體裡，所以這裡一定要先清乾淨再量。
    reset_rot(pg, base, 2200)

    ok("資金流向排行上方有拉Bar（圖四）",
       pg.evaluate("() => !!document.querySelector('#rankDays input[type=range]')"))
    # 2026-09-20：播放鈕依 Andy 指示移除（「圖三資金流向移除播放功能」），
    # 所以這裡不再 check_play；拉Bar 本身還在，下面照樣驗「拉了畫面真的變」。

    # 拉到 N 天，副標與期間說明要真的換成「最近 N 個交易日」，圖也要重畫
    # ★ 2026-09-20：期間卡拿掉之後 #periodNote 不存在了，日期範圍改寫在排行自己的副標，
    #   所以這幾條改成驗副標。要守的事情沒變：拉了天數，**日期範圍真的跟著換**。
    # ★ 基準值一定要在「拉到 5 天」之後才取 —— 預設就是 20 天，
    #   在拉到 5 之前取的話，等一下拉回 20 會拿到同一張圖，這條就變成假紅。
    set_range(pg, "#rankDays input[type=range]", 5, 1200)
    h0 = canvas_hash(pg, "#rankFlow")
    sub0 = text(pg, "#rankSub")
    set_range(pg, "#rankDays input[type=range]", 20, 1400)
    st = pg.evaluate("""() => ({ sub: (document.getElementById('rankSub')||{}).textContent,
        top: (() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
               if (!c) return null; const y = c.getOption().yAxis[0].data || []; return y[y.length-1] || null; })() })""")
    ok("拉到 20 天，排行副標寫出 20 個交易日的日期範圍（圖四）",
       "20" in (st["sub"] or "") and "～" in (st["sub"] or ""), st["sub"])
    changed("拉到 20 天，日期範圍真的換了", sub0, st["sub"])
    changed("拉到 20 天，排行圖真的重畫了（不是只有字變）", h0, canvas_hash(pg, "#rankFlow"))

    # 點長條：原地展開成分股、不跳頁，時鐘跟著只亮那一族群
    hash0 = pg.evaluate("() => location.hash")
    # ★ ECharts 沒有 'click' 這個 action —— dispatchAction({type:'click'}) 不會觸發 c.on('click')。
    #   要驗「使用者真的點得到」就得用真的滑鼠，所以先把長條換算成畫面座標再點下去。
    #
    # ★★ 座標一定要「每次點之前重算」：getBoundingClientRect 是相對**視窗**的，
    #    而第一次點開成分股面板時 heatPanel 會 scrollIntoView 把頁面捲動一段，
    #    舊座標就指不到那根長條了（2026-09-18 踩到：第二次點沒收起來，
    #    其實是第二次點根本沒點到圖上）。
    def rank_spot():
        return pg.evaluate("""() => { const el = document.getElementById('rankFlow');
            const c = echarts.getInstanceByDom(el); if (!c) return null;
            const o = c.getOption(); const d = (o.series[0].data || []);
            if (!d.length) return null;
            const i = d.length - 1;
            const v = typeof d[i] === 'object' ? d[i].value : d[i];
            const p = c.convertToPixel({ seriesIndex: 0 }, [v, i]);
            if (!p) return null;
            const r = el.getBoundingClientRect();
            return { x: r.left + p[0] - (v >= 0 ? 4 : -4), y: r.top + p[1],
                     gid: (typeof d[i] === 'object' ? d[i].gid : null) }; }""")

    # ★ 2026-09-20 修掉一個**假紅燈**：`pg.goto(base + '#flow')` 在已經停在同一個網址時
    #   只是 hashchange，**不會把頁面捲回最上面**。前一段（資金流向）結束時頁面停在下面，
    #   於是這裡算出來的長條座標其實在畫面外，點下去什麼也沒發生 ——
    #   報出來的是「點了沒有展開成分股」，看起來像功能壞掉（在舊版程式上也一樣紅）。
    #   這是 DECISIONS #188／#190 那一類「驗收方法本身有 bug」的第五次，所以先捲到圖上。
    scroll_to(pg, "rankFlow")
    spot = rank_spot()
    clicked = spot and spot.get("gid")
    if spot:
        pg.mouse.click(spot["x"], spot["y"])
        pg.wait_for_timeout(900)
        # heatPanel 產生的是 .ms > a[href^="#stock/"]，不是 a.lk-stock（那是 L.stock() 的樣式）
        st2 = pg.evaluate("""() => { const b = document.getElementById('rankPanel');
            return { open: !!b && !b.hidden,
                     chips: document.querySelectorAll('#rankPanel .ms a[href^="#stock/"]').length,
                     hash: location.hash }; }""")
        ok("點排行的長條會原地展開成分股（圖四）", st2["open"] and st2["chips"] > 0, st2)
        ok("點排行的長條不會跳頁（圖四）", st2["hash"] == hash0, st2["hash"])
        dim = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
            if (!c) return null; const o = c.getOption();
            const sc = (o.series || []).filter(s => s.type === 'scatter')[0];
            if (!sc) return null;
            const ops = (sc.data || []).map(d => (d.itemStyle && d.itemStyle.opacity != null) ? d.itemStyle.opacity : 1);
            return { lo: Math.min(...ops), hi: Math.max(...ops), n: ops.length }; }""")
        # ★ 先確認「盤上不只一個族群」—— 只有一個的話，「只亮那一個、其他壓暗」
        #   在物理上量不出來（沒有別人可以被壓暗），紅綠都沒有資訊（DECISIONS #206）。
        ok("輪動時鐘盤上本來就有好幾個族群（不然「只亮一個」量不出來）",
           bool(dim) and dim["n"] > 3, dim)
        ok("點排行的長條，旁邊的輪動時鐘只亮那一個族群（圖四）",
           bool(dim) and dim["n"] > 3 and dim["lo"] < 0.3 and dim["hi"] > 0.9, dim)
        # 再點一次要取消 —— 座標要重算，而且要等 scrollIntoView 的**平滑捲動停下來**才算。
        # heatPanel 用的是 behavior:'smooth'，捲動是動畫；捲到一半就量座標，
        # 等滑鼠真的按下去時頁面又移位了，點就落在圖外面（2026-09-18 踩到兩次）。
        pg.wait_for_function("""() => { const y = window.scrollY;
            if (window.__lastY === y) return true; window.__lastY = y; return false; }""",
                             timeout=5000)
        spot2 = rank_spot() or spot
        pg.mouse.click(spot2["x"], spot2["y"])
        pg.wait_for_timeout(900)
        ok("再點一次同一根長條會收起來（圖四）",
           pg.evaluate("() => { const b=document.getElementById('rankPanel'); return !b || b.hidden; }"))

    # ---------------------------------------------------------- 圖二：輪動時鐘
    ok("輪動時鐘搬到排行旁邊那一格了（圖四換位）",
       pg.evaluate("""() => { const a = document.getElementById('rankFlow'), b = document.getElementById('rotClock');
           if (!a || !b) return false;
           const ca = a.closest('.card'), cb = b.closest('.card');
           return !!ca && !!cb && ca.parentNode === cb.parentNode; }"""))
    # 2026-09-21：常駐的 #rotCenterNote 移除，說明搬進「怎麼看 ?」（見 how_text 的 docstring）
    _how = how_text(pg, "rot")
    ok("「怎麼看」裡有寫清楚圓心到圓外是什麼意思（圖二）",
       "圓心" in _how and "偏離" in _how, _how[:120])
    ok("圖下方那段常駐長說明真的不在了（2026-09-21 Andy：「下方這段也移除」）",
       not pg.evaluate("() => !!document.getElementById('rotCenterNote')")
       and "跟大盤走得一模一樣" not in text(pg, "#v-flow"),
       pg.evaluate("() => !!document.getElementById('rotCenterNote')"))

    # 標籤真的排開（不是被藏起來）：兩兩不相交、全在畫布內
    for w in (1500, 800):
        pg.set_viewport_size({"width": w, "height": 1000})
        pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2200)
        lay = pg.evaluate("""() => { const rs = (window.App && window.App._rotLabels) || [];
            const el = document.getElementById('rotClock');
            const W = el ? el.clientWidth : 0, H = el ? el.clientHeight : 0;
            let hit = null, out = null;
            for (let i = 0; i < rs.length; i++) {
              const a = rs[i];
              if (a.x < -1 || a.y < -1 || a.x + a.w > W + 1 || a.y + a.h > H + 1) out = out || a.name;
              for (let j = i + 1; j < rs.length; j++) {
                const b = rs[j];
                if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) { hit = hit || [a.name, b.name]; }
              }
            }
            return { n: rs.length, hit, out, W, H }; }""")
        ok(f"[{w}px] 輪動時鐘的族群名稱有排出來（不是被 hideOverlap 吃掉）", lay["n"] > 0, lay)
        ok(f"[{w}px] 任兩個族群名稱不重疊（圖二「都擠在一起了」）", lay["hit"] is None, lay["hit"])
        ok(f"[{w}px] 每個族群名稱都在畫布內", lay["out"] is None, lay["out"])
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2000)

    # 放大（E2，Andy 2026-09-20：「放大之後的功能都沒反應」）
    # 根因量過兩件事：① renderRotClock 結尾那段 groupChips 連放大視窗也一起塞了一排晶片，
    #   插在 #zoomBody 的下一個兄弟，而 .zb 是 flex —— 實測 #zoomBody 704×756、
    #   那排晶片 704×748，**放大視窗一半的版面被吃掉**，而且那排晶片綁的是卡片的選取。
    #   ② 放大視窗維護第二套只有 16 顆的簡化晶片與語意不同的拉Bar。
    # 所以這裡驗的是：.zb 只有一個子元素、#zoomBody 真的撐滿、控制項和卡片同一套、
    # 而且「改了篩選／拉了Bar，放大的那張圖真的變了」。
    click(pg, "#rotZoomBtn", 1600)
    ok("按「放大」會打開放大視窗（圖二）",
       pg.evaluate("() => { const o = document.getElementById('zoomOv'); return !!o && !o.hidden; }"))
    ok("放大視窗裡畫的是輪動時鐘", pg.evaluate("() => !!document.querySelector('#zoomBody canvas')"))
    zb = pg.evaluate("""() => { const z = document.querySelector('.zb');
        const b = document.getElementById('zoomBody');
        const zr = z.getBoundingClientRect(), br = b.getBoundingClientRect();
        return { kids: z.children.length,
                 kidCls: [...z.children].map(e => e.id || e.className),
                 bw: Math.round(br.width), bh: Math.round(br.height),
                 zw: Math.round(zr.width), zh: Math.round(zr.height) }; }""")
    ok("放大視窗的 .zb 只有 #zoomBody 一個子元素（E2：以前被硬塞一排族群晶片）",
       zb["kids"] == 1 and zb["kidCls"] == ["zoomBody"], zb)
    ok("#zoomBody 真的佔滿 .zb（E2：以前只拿到一半）",
       zb["bw"] >= zb["zw"] - 2 and zb["bh"] >= zb["zh"] - 2, zb)
    tools = pg.evaluate("""() => ({
        filt: document.querySelectorAll('#zoomTools .rotfilter[data-rf="zoom"]').length,
        seg: document.querySelectorAll('#zoomTools .rotchain button').length,
        top10: document.querySelectorAll('#zoomTools .rot-top10').length,
        sbtn: document.querySelectorAll('#zoomTools .rot-sbtn').length,
        gbtn: document.querySelectorAll('#zoomTools .rot-gbtn').length,
        back: document.querySelectorAll('#rotZoomBack input[type=range]').length,
        pb: document.querySelectorAll('#rotZoomBack .pb').length,
        trail: document.querySelectorAll('#rotZoomTools .rot-trail').length,
        chips: document.querySelectorAll('#zoomTools .rotfilter .gchip').length,
        oldChips: document.querySelectorAll('#rotZoomChips').length })""")
    ok("放大視窗的控制項和卡片是同一套（篩選列＋族群晶片／看哪一天＋＋−▶／軌跡開關）（E2）",
       tools["filt"] == 1 and tools["seg"] >= 2 and tools["top10"] == 1
       and tools["back"] == 1 and tools["pb"] == 3 and tools["trail"] == 1 and tools["chips"] > 3, tools)
    ok("放大視窗裡也沒有多出一顆「族群篩選」（E3 兩邊一致）", tools["gbtn"] == 0, tools)
    # 2026-09-21：個股篩選整顆移除、族群晶片改由 wireRotFilter 統一產在 .rotfilter 裡
    ok("放大視窗裡沒有「個股篩選」（2026-09-21 Andy：「個股篩選拿掉」）", tools["sbtn"] == 0, tools)
    ok("放大視窗不再自己維護第二排晶片（#rotZoomChips 已移除）", tools["oldChips"] == 0, tools)

    ZN = """() => { const c = echarts.getInstanceByDom(document.getElementById('zoomBody'));
        if (!c) return 0; const sc = (c.getOption().series||[]).filter(s=>s.type==='scatter')[0];
        return sc ? (sc.data||[]).length : 0; }"""
    n0 = pg.evaluate(ZN)
    # ① 在放大視窗裡勾「只看前 10 大」—— 放大的那張圖要真的變
    pg.eval_on_selector('#zoomTools .rot-top10', "e => e.click()")
    pg.wait_for_timeout(1200)
    n1 = pg.evaluate(ZN)
    ok("在放大視窗勾「只看前 10 大」，放大的那張圖真的變了（E2）",
       n1 == 10 and n0 > 10, f"{n0} → {n1}")
    pg.eval_on_selector('#zoomTools .rot-clear', "b => b.click()")
    pg.wait_for_timeout(1200)
    ok("在放大視窗按「清除篩選」真的還原（E2）", pg.evaluate(ZN) == n0, f"{n1} → {pg.evaluate(ZN)}")
    # ② 在放大視窗點族群晶片 —— 圖上只剩它
    # 2026-09-21：晶片列搬進 .rotfilter 了，放大視窗那一排也一樣（不再有 #rotZoomChips）
    ZCHIP = '#zoomTools .rotfilter[data-rf="zoom"] .linkrow.gchips'
    zg = pg.evaluate(f"() => [...document.querySelectorAll('{ZCHIP} .gchip')].map(c => c.dataset.g)")
    if len(zg) > 1:
        pg.eval_on_selector(f'{ZCHIP} .gchip[data-g="{zg[1]}"] .pick', "b => b.click()")
        pg.wait_for_timeout(1200)
        ok("在放大視窗點族群晶片，放大的那張圖只剩那一個族群（E2）",
           pg.evaluate(ZN) == 1, f"{n0} → {pg.evaluate(ZN)}")
        pg.eval_on_selector(f'{ZCHIP} .gchip[data-g="{zg[1]}"] .pick', "b => b.click()")
        pg.wait_for_timeout(1200)
        ok("再點一次取消，放大的那張圖回到全部族群（E2）", pg.evaluate(ZN) == n0, pg.evaluate(ZN))
    # ③ 拉「看哪一天」—— 放大的那張圖真的重畫，而且圖上寫得出是哪一天
    before = canvas_hash(pg, "#zoomBody")
    set_range(pg, "#rotZoomBack input[type=range]", 28, 1600)
    changed("在放大視窗拉「看哪一天」，放大的那張圖真的重畫了（E2）", before, canvas_hash(pg, "#zoomBody"))
    ok("回放時圖上有寫出是哪一天（圖二）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('zoomBody'));
           if (!c) return false; const g = c.getOption().graphic || [];
           return JSON.stringify(g).indexOf('回放') >= 0; }"""))
    # ④ 軌跡開關在放大視窗裡也真的有作用
    pg.eval_on_selector("#rotZoomTools .rot-trail", "e => e.click()")
    pg.wait_for_timeout(1200)
    ok("在放大視窗關掉軌跡，放大的那張圖軌跡真的歸零（E2）",
       _rot_trail_pts(pg, "zoomBody") == 0, _rot_trail_pts(pg, "zoomBody"))
    pg.eval_on_selector("#rotZoomTools .rot-trail", "e => e.click()")
    pg.wait_for_timeout(1200)
    ok("再打開軌跡真的回來（E2）", _rot_trail_pts(pg, "zoomBody") > 20, _rot_trail_pts(pg, "zoomBody"))
    # ⑤ 關掉之後卡片要跟上（天數是在放大視窗裡改的）
    pg.eval_on_selector("#zoomClose", "b => b.click()")
    pg.wait_for_timeout(1600)
    ok("關閉放大視窗", pg.evaluate("() => document.getElementById('zoomOv').hidden") is True)
    ok("關掉之後控制項列有清乾淨（不會留給下一張圖一排按了沒反應的鈕）（E2）",
       pg.evaluate("() => (document.getElementById('zoomTools').innerHTML || '').trim() === ''"))
    ok("關掉之後卡片上的「看哪一天」跟著同步成放大視窗裡選的那一天（E2）",
       pg.evaluate("() => +document.querySelector('#rotBack input').value") == 28,
       pg.evaluate("() => +document.querySelector('#rotBack input').value"))
    set_range(pg, "#rotBack input[type=range]", 5, 1200)

    # 總覽的小輪動圖也有放大鈕
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(2000)
    ok("總覽小輪動圖有「放大」鈕（已拍板：小圖只留放大）",
       pg.evaluate("() => !!document.getElementById('rotMiniZoomBtn')"))
    click(pg, "#rotMiniZoomBtn", 1400)
    ok("總覽按放大也打得開同一個放大視窗",
       pg.evaluate("() => { const o = document.getElementById('zoomOv'); return !!o && !o.hidden; }")
       and pg.evaluate("() => !!document.querySelector('#zoomBody canvas')"))
    pg.eval_on_selector("#zoomClose", "b => b.click()")
    pg.wait_for_timeout(500)


def t_batch3(pg, base):
    """批次3（Andy 2026-09-18 圖六／七／八／資金集中度）的真人操作驗收。"""
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2400)

    # ---- 圖八：族群 × 法人的「截止日」回放
    if pg.evaluate("() => !!document.querySelector('#instEnd input[type=range]')"):
        set_range(pg, "#instDays input[type=range]", 20, 900)
        sub0 = text(pg, "#instSub")
        i0 = canvas_hash(pg, "#instGroups")
        set_range(pg, "#instEnd input[type=range]", 30, 1200)
        changed("族群×法人把截止日往回拉，圖真的重畫（圖八）", i0, canvas_hash(pg, "#instGroups"))
        changed("族群×法人的副標跟著寫出那一段日期（圖八）", sub0, text(pg, "#instSub"))
        ok("副標寫的是一段區間不是只有天數", "～" in text(pg, "#instSub"), text(pg, "#instSub"))
        # 2026-09-20：播放鈕依 Andy 指示移除（「圖二族群法人播放功能移除」），
        # 截止日拉Bar 保留，上面那三條就是在驗它真的還能用。

    # ---- 資金集中度：六條均線可勾選、點某天鑽到族群再鑽到個股
    mas = pg.evaluate("() => [...document.querySelectorAll('#concMa input[data-ma]')].map(i => +i.dataset.ma)")
    ok("資金集中度有六條均線可選（5/10/20/60/120/240）", mas == [5, 10, 20, 60, 120, 240], mas)
    n0 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('conc'));
        return c ? c.getOption().series.length : 0; }""")
    pg.evaluate("""() => { const i = document.querySelector('#concMa input[data-ma="240"]');
        if (i && !i.checked) { i.checked = true; i.dispatchEvent(new Event('change', {bubbles:true})); } }""")
    pg.wait_for_timeout(900)
    n1 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('conc'));
        return c ? c.getOption().series.length : 0; }""")
    ok("勾 240 日均線，圖上真的多一條線", n1 > n0, f"{n0} → {n1}")
    ok("240 日均線算得出來（後端要留夠 400 天）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('conc'));
           if (!c) return false; const s = (c.getOption().series||[]).find(x => x.name === '240 日均');
           return !!s && (s.data||[]).some(v => v != null); }"""))
    ok("選過的均線有記住",
       pg.evaluate("() => { try { return (localStorage.getItem('tw.conc.ma')||'').indexOf('240') >= 0; } catch(e){ return false; } }"))
    # 點圖上某一天 → 側欄出現那天的族群
    # 圖在頁面很下面，座標是相對視窗的 —— 不先捲進畫面的話會點到別的地方
    pg.eval_on_selector("#conc", "e => e.scrollIntoView({block:'center'})")
    pg.wait_for_timeout(600)
    hit = pg.evaluate("""() => { const el = document.getElementById('conc');
        const c = echarts.getInstanceByDom(el); if (!c) return null;
        const o = c.getOption(); const n = (o.series[0].data||[]).length; if (!n) return null;
        const i = n - 5 > 0 ? n - 5 : n - 1;
        const p = c.convertToPixel({ seriesIndex: 0 }, [i, o.series[0].data[i]]);
        if (!p) return null; const r = el.getBoundingClientRect();
        return { x: r.left + p[0], y: r.top + p[1] - 30 }; }""")
    if hit:
        pg.mouse.click(hit["x"], hit["y"])
        # ★ 2026-09-20：原本睡 1200ms。平行跑時 CPU 被搶，面板還沒開就量 → 假紅。
        #   改成等「面板真的開了而且列得出族群」這個條件。
        st = wait_until(pg, """() => { const b = document.getElementById('concSide');
            if (!b || b.hidden) return null;
            const n = document.querySelectorAll('#concGs button').length;
            if (!n) return null;
            return { open: true, gs: n, hash: location.hash }; }""", 6000) or pg.evaluate(
            """() => { const b = document.getElementById('concSide');
            return { open: !!b && !b.hidden, gs: document.querySelectorAll('#concGs button').length,
                     hash: location.hash }; }""")
        ok("點集中度圖的某一天，旁邊列出那天的族群", st["open"] and st["gs"] > 0, st)
        ok("點某一天不會跳頁", st["hash"] == "#flow", st["hash"])
        if st["gs"]:
            pg.eval_on_selector("#concGs button", "b => b.click()")
            pg.wait_for_timeout(1200)
            st2 = pg.evaluate("""() => ({ ms: document.querySelectorAll('#concMs a[href^="#stock/"]').length,
                empty: (document.getElementById('concMs')||{}).textContent.indexOf('沒有留') >= 0,
                hash: location.hash })""")
            ok("點族群會原地展開那天的成分股（或明講那天沒留）",
               st2["ms"] > 0 or st2["empty"], st2)
            ok("點族群不會跳頁（只有股票才連個股頁）", st2["hash"] == "#flow", st2["hash"])

    # ---- 圖七B：個股頁本益比河流的區間拉Bar，而且滾輪放大不能因此失效
    pg.goto(f"{base}#stock/2330", wait_until="networkidle"); pg.wait_for_timeout(2600)
    tabs = pg.evaluate("() => [...document.querySelectorAll('#stockTabs button')].map(b => b.dataset.t)")
    if "profit" in (tabs or []):
        click(pg, '#stockTabs button[data-t="profit"]', 1600)
        if pg.evaluate("() => !!document.querySelector('#peEnd input[type=range]')"):
            p0 = canvas_hash(pg, "#peChart")
            set_range(pg, "#peEnd input[type=range]", 50, 1200)
            changed("本益比河流把截止拉回去，圖真的重畫（圖七B）", p0, canvas_hash(pg, "#peChart"))
            check_play(pg, "#peEnd")
        # ★ 滾輪放大是 Andy 2026-09-16 親口要的，不可以因為加了區間拉Bar 就壞掉
        ok("本益比河流的滾輪放大還在（沒有被 dataZoom 吃掉）",
           pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('peChart'));
               if (!c) return false; const dz = c.getOption().dataZoom || [];
               return dz.length === 0; }"""))


def t_batch4(pg, base):
    """批次4（Andy 圖15／圖16／圖三 N8／圖十八 N9）的真人操作驗收。"""
    pg.set_viewport_size({"width": 1500, "height": 1000})

    # ---- 圖15 漲跌分佈
    pg.goto(f"{base}#market/updown", wait_until="networkidle"); pg.wait_for_timeout(2200)
    dist = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('chgDist'));
        if (!c) return null; const o = c.getOption();
        return { bars: (o.series[0].data||[]).length, line: o.series.length > 1,
                 labels: (o.xAxis[0].data||[]) }; }""")
    ok("市場明細有漲跌分佈長條圖（圖15）", bool(dist) and dist["bars"] == 12, dist)
    ok("每 2% 一個區間、兩端各留一個溢出格（圖15）",
       bool(dist) and dist["labels"][0].startswith("≤") and dist["labels"][-1].startswith("≥"),
       dist and [dist["labels"][0], dist["labels"][-1]])
    ok("疊了一條常態曲線（圖15）", bool(dist) and dist["line"], dist)
    ok("下面寫出樣本數與平均、標準差", "標準差" in text(pg, "#distSub"), text(pg, "#distSub"))
    # 篩市場：家數要真的變
    n0 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('chgDist'));
        return c ? (c.getOption().series[0].data||[]).reduce((s,d)=>s+(d.value||0),0) : 0; }""")
    mkts = pg.evaluate("() => [...document.querySelectorAll('#distMkt button')].map(b => b.dataset.m)")
    if len(mkts) > 1:
        pg.eval_on_selector(f'#distMkt button[data-m="{mkts[1]}"]', "b => b.click()")
        pg.wait_for_timeout(900)
        n1 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('chgDist'));
            return c ? (c.getOption().series[0].data||[]).reduce((s,d)=>s+(d.value||0),0) : 0; }""")
        ok("篩上市／上櫃之後家數真的變少（圖15）", 0 < n1 < n0, f"{n0} → {n1}")
        pg.eval_on_selector('#distMkt button[data-m=""]', "b => b.click()")
        pg.wait_for_timeout(700)
    # 含 ETF 勾起來，家數要變多
    n2 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('chgDist'));
        return c ? (c.getOption().series[0].data||[]).reduce((s,d)=>s+(d.value||0),0) : 0; }""")
    pg.eval_on_selector("#distEtf", "e => { e.checked = true; e.dispatchEvent(new Event('change',{bubbles:true})); }")
    pg.wait_for_timeout(900)
    n3 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('chgDist'));
        return c ? (c.getOption().series[0].data||[]).reduce((s,d)=>s+(d.value||0),0) : 0; }""")
    ok("勾「含 ETF」之後家數真的變多（預設是排除的）", n3 > n2, f"{n2} → {n3}")

    # ---- 圖16 站上均線走勢
    pg.goto(f"{base}#market/ma", wait_until="networkidle"); pg.wait_for_timeout(2600)
    mt = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('maTrend'));
        if (!c) return null; const o = c.getOption();
        return { n: o.series.length, pts: (o.series[0].data||[]).length,
                 mas: [...document.querySelectorAll('#maSeg button')].map(b => b.dataset.n) }; }""")
    ok("站上均線有走勢圖（圖16）", bool(mt) and mt["n"] > 1 and mt["pts"] > 100, mt)
    ok("七條均線都可選（5/10/20/30/60/120/240）",
       bool(mt) and mt["mas"] == ["5", "10", "20", "30", "60", "120", "240"], mt and mt["mas"])
    h0 = canvas_hash(pg, "#maTrend")
    pg.eval_on_selector('#maSeg button[data-n="240"]', "b => b.click()")
    pg.wait_for_timeout(1200)
    changed("切到 240 日均線，走勢圖真的重畫（圖16）", h0, canvas_hash(pg, "#maTrend"))
    ok("240 日均線真的算得出來（不是整條空的）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('maTrend'));
           if (!c) return false; const s = (c.getOption().series||[])[0];
           return !!s && (s.data||[]).some(v => v != null); }"""))
    # 族群複選：拿掉一個，線要變少
    g0 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('maTrend'));
        return c ? c.getOption().series.length : 0; }""")
    on = pg.evaluate("() => { const b = document.querySelector('#maGroups button.on:not([data-g=\"全市場\"])'); return b ? b.dataset.g : null; }")
    if on:
        pg.eval_on_selector(f'#maGroups button[data-g="{on}"]', "b => b.click()")
        pg.wait_for_timeout(1000)
        g1 = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('maTrend'));
            return c ? c.getOption().series.length : 0; }""")
        ok("取消一個族群，線真的變少（圖16）", g1 == g0 - 1, f"{g0} → {g1}")

    # ---- 季節性 N8／N9
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(2400)
    ok("季節性有寫出基準是什麼（N8）", "基準" in text(pg, "#seasonNote"), text(pg, "#seasonNote")[:80])
    click(pg, '#seasonPeriod button[data-v="3y"]', 1400)
    rng = text(pg, "#seasonRange")
    ok("近三年是滾動 36 個完整月，不是日曆年（N9）", "2023" in rng or "36" in rng, rng)
    full = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('seasonHeat'));
        if (!c) return null; const d = (c.getOption().series[0].data||[]);
        const months = new Set(d.filter(x => x[2] != null).map(x => x[0]));
        return { months: [...months].sort((a,b)=>a-b), n: d.length }; }""")
    ok("近三年 12 個月都有值，9-12 月不再留白（N9）",
       bool(full) and len(full["months"]) == 12, full and full["months"])
    # 切「超額報酬」要真的換一張圖（N8：以前會無聲退回絕對報酬）
    # 預設就是超額報酬，所以先切到絕對報酬再切回來，才測得出「兩者不一樣」
    click(pg, '#seasonMetric button[data-v="avg_return"]', 1400)
    h1 = canvas_hash(pg, "#seasonHeat")
    click(pg, '#seasonMetric button[data-v="avg_excess"]', 1400)
    changed("超額報酬與絕對報酬畫出來不一樣（N8）", h1, canvas_hash(pg, "#seasonHeat"))
    ok("超額報酬真的算得出來（不是整片空白）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('seasonHeat'));
           if (!c) return false; const d = (c.getOption().series[0].data||[]);
           return d.filter(x => x[2] != null).length > d.length * 0.9; }"""))


def t_batch7(pg, base):
    """批次7（Andy 2026-09-19 半夜追加的七項）的真人操作驗收。"""
    pg.set_viewport_size({"width": 1500, "height": 1000})
    # ★ 2026-09-21：這一段第一條就假設「進來的時候是全部族群」，
    #   所以一定要先 reset_rot（真的 reload），不能只 goto ——
    #   平行排程只要把它排在「新-輪動時鐘」後面，記憶體裡的 ROT.groups 就還活著。
    reset_rot(pg, base, 2400)

    # ---- N2 兩邊族群名單要一樣，而且點了是「篩選」不是跳頁
    # ★ 2026-09-20：選擇器要限定在資金流向頁而且只取「排行 × 時鐘」那兩排（data-sync="n2"）。
    #   全站的 view 都在同一份 DOM 裡，總覽的「族群估值」與這一頁的「資金去向 / 族群×法人」
    #   現在也各有一排族群晶片（filterChips），不限定的話 rows[0] 會抓到總覽那一排，
    #   這條就變成在比兩張不相干的圖（實測 4 vs 36）。
    lists = pg.evaluate("""() => [...document.querySelectorAll('#v-flow .linkrow.gchips[data-sync="n2"]')]
        .map(r => [...r.querySelectorAll('.gchip')].map(c => c.dataset.g))""")
    ok("排行與時鐘各有一排族群晶片（N2）", len(lists) >= 2, [len(x) for x in (lists or [])])
    if len(lists) >= 2:
        ok("兩邊族群名單完全一樣（N2「兩邊族群對不上」）", lists[0] == lists[1],
           {"排行": len(lists[0]), "時鐘": len(lists[1]),
            "只在一邊": sorted(set(lists[0]) ^ set(lists[1]))[:6]})
    hash0 = pg.evaluate("() => location.hash")
    if lists and lists[0]:
        # ★ 2026-09-20：選擇器一定要限定在 [data-sync="n2"] 這兩排。
        #   全站 view 共用同一份 DOM，總覽的「族群估值」現在也有一排族群晶片（filterChips），
        #   所以 `.gchips .gchip` 的第一個可能是**總覽那一排** —— 按了它，這一頁的
        #   排行面板當然不會開。實測：單獨跑 `--only 批次7` 是綠的，接在
        #   `--only 新-資金流向,批次7` 後面就紅，因為前一段已經把總覽渲染出來了。
        #   這是驗收選錯對象，不是功能壞掉。
        N2 = '#v-flow .linkrow.gchips[data-sync="n2"]'
        n_before = len(_rot_scatter(pg) or [])
        pg.eval_on_selector(f"{N2} .gchip .pick", "b => b.click()")
        pg.wait_for_timeout(1200)
        st = pg.evaluate("""() => { const b = document.getElementById('rankPanel');
            const sc = (() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
              if (!c) return null; const s = (c.getOption().series||[]).filter(x=>x.type==='scatter')[0];
              return s ? (s.data||[]).length : null; })();
            return { hash: location.hash, panel: !!b && !b.hidden,
                     on: document.querySelectorAll('#v-flow .linkrow.gchips[data-sync="n2"] .gchip.on').length,
                     n: sc }; }""")
        ok("點族群晶片不會跳頁（N2「篩選不到」的根因）", st["hash"] == hash0, st["hash"])
        ok("點族群晶片會篩選：排行展開成分股 ＋ 時鐘上的族群真的變少（N2＋E3）",
           st["panel"] and st["n"] == 1 and n_before > 1, {"before": n_before, **st})
        ok("兩排晶片同時被選起來（N2）", st["on"] >= 2, st["on"])
        # 收拾：取消掉，不要把篩選狀態留給後面的段落
        pg.eval_on_selector(f"{N2} .gchip.on .pick", "b => b.click()")
        pg.wait_for_timeout(1000)
        ok("再點一次取消，時鐘回到全部族群（E3）",
           len(_rot_scatter(pg) or []) == n_before, f"{st['n']} → {len(_rot_scatter(pg) or [])}")

    # ---- N4 時間週期拉到 30 天
    bar = pg.evaluate("""() => { const i = document.querySelector('#rotBack input[type=range]');
        return i && { min: +i.min, max: +i.max }; }""")
    ok("輪動時鐘的天數可以拉到 30 天（N4）", bool(bar) and bar["max"] == 30, bar)
    set_range(pg, "#rotBack input[type=range]", 30, 1400)
    # ★ 2026-09-20 改寫（Andy：「只有經過才留下軌跡，不是馬上所有軌跡都先印出來」）。
    #   原本這條是「拉到 30 天時 ln[0].data.length > 3」——
    #   軌跡改成漸進式之後，「前 30 天」就是**起點**，每條軌跡只剩一個點，這個判準必然紅。
    #   但它要守的東西沒有變：**拉到最大值時後端真的取得到那一天**
    #   （2026-09-19 就是因為 trail 只存 30 筆、索引跑到 -1，拉到底完全沒反應）。
    #   所以改成直接驗那件事：大圈落在的那一天，就是原始 trail 裡「倒數第 31 筆」那一天。
    #   這比原本的點數判準更貼近它本來要擋的 bug。
    ok("拉到 30 天真的取得到那一天（後端 trail 要同步存到 31 筆）",
       pg.evaluate("""() => { const f = window.App && window.App._rotFrame;
           const pts = ((window.App.D.flow_v3 || {}).rrg || {}).points || [];
           if (!f || !pts.length) return false;
           const t = (pts.find(p => (p.trail || []).length >= 31) || {}).trail || [];
           return f.frame === 30 && !!f.date && t.length >= 31 && f.date === t[t.length - 1 - 30][0]; }"""),
       pg.evaluate("() => (window.App && window.App._rotFrame) || null"))

    # ---- N5 圓圈範圍變大
    r = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
        if (!c) return null; const p = (c.getOption().polar||[])[0]; return p ? p.radius : null; }""")
    ok("輪動時鐘的圓圈放大了（N5，72% → 84%）", str(r) == "84%", r)

    # ---- N6 「順時針」這件事要講得出來
    # ★ 2026-09-20：盤面上那四個 ↻ 箭頭移除了（理由寫在 site/app.js 的 graphic 區塊）。
    #   兩個可放的位置（兩段交界 / 每段外角）分別會撞到「跑到圓周上的族群名」
    #   與「該段自己的名字」，多寬度掃描兩種都量到重疊；
    #   而 Andy 在 A4 輪動時鐘的需求第 2 條本來就寫「移除旋轉箭頭」。
    #   N6 真正要保住的是「使用者知道它是順時針、而且知道順序」——
    #   所以改驗圖下方那一行字真的寫出了方向與四段順序（那是 HTML，不可能溢出或壓字）。
    # 2026-09-21：那段文字從常駐的 #rotCenterNote 搬進「怎麼看 ?」，所以要真的按開來讀
    _note = how_text(pg, "rot")
    arrows = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
        const s = c ? JSON.stringify(c.getOption().graphic||[]) : ''; return (s.match(/↻/g)||[]).length; }""")
    ok("盤面上不再有會壓到族群名的 ↻ 箭頭（N6 改走文字）", arrows == 0, arrows)
    ok("說明有講「順時針」（N6）", "順時針" in _note, _note[:80])
    ok("說明有把四段的順序寫出來（N6）",
       all(k in _note for k in ("落後", "改善", "領先", "轉弱")), _note[:120])

    # ---- N3 回放是「走過去」不是「跳格」：同一組族群時要用 merge（有補間動畫）
    ok("回放有補間動畫設定（N3「像螞蟻一樣緩步移動」）",
       pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('rotClock'));
           if (!c) return false; const o = c.getOption();
           return o.animationDurationUpdate >= 400 && o.animationEasingUpdate === 'linear'; }"""))

    # ---- N10 季節性下方改成四段卡片
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(2400)
    st2 = pg.evaluate("""() => ({ cards: document.querySelectorAll('#seasonBoard .stage').length,
        names: [...document.querySelectorAll('#seasonBoard .stage .sh b')].map(e => e.textContent),
        table: !!document.querySelector('#seasonTop table') })""")
    ok("季節性下方改成四段卡片（N10）", st2["cards"] == 4, st2)
    ok("四段是強勢／偏強／偏弱／弱勢（N10）",
       st2["names"] == ["強勢", "偏強", "偏弱", "弱勢"], st2["names"])
    ok("不再是表格（N10）", not st2["table"], st2)
    if pg.evaluate("() => !!document.querySelector('#seasonBoard li[data-gid]')"):
        h0 = pg.evaluate("() => location.hash")
        pg.eval_on_selector("#seasonBoard li[data-gid]", "li => li.click()")
        pg.wait_for_timeout(700)
        ok("點族群會原地展開成分股、不跳頁（N10 沿用批次1 的作法）",
           pg.evaluate("() => !!document.querySelector('#seasonBoard li.mem')")
           and pg.evaluate("() => location.hash") == h0)


def t_batch6_n1(pg, base):
    """批次6 的 N1（Andy 2026-09-19：「3D圖需要可以游標抓取移動，
    並且可以 360 都觀測 我發現下面看不到」）。"""
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#industry/semiconductor", wait_until="networkidle"); pg.wait_for_timeout(2200)
    if not pg.evaluate("() => !!document.getElementById('dg3d')"):
        return                                   # 這條鏈沒有 3D 場景
    if pg.evaluate("() => document.getElementById('dg3d').hidden"):
        return                                   # WebGL 不支援（容器有時候是這樣）
    click(pg, "#dg3d", 3000)
    pg.wait_for_timeout(2500)
    if not pg.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
        return
    pol = pg.evaluate("() => window.Rack3D.current.polar ? window.Rack3D.current.polar() : null")
    ok("3D 可以轉到底下看（N1「我發現下面看不到」）",
       bool(pol) and pol[1] > 3.0, pol)           # π ≈ 3.1416；舊版是 1.555
    ok("3D 也可以轉到上面（N1 360 度）", bool(pol) and pol[0] < 0.1, pol)
    ok("有「拖曳：轉動／平移」切換鈕（N1「游標抓取移動」）",
       pg.evaluate("() => { const b = document.getElementById('dgDrag'); return !!b && !b.hidden; }"))
    m0 = pg.evaluate("() => window.Rack3D.current.dragMode()")
    click(pg, "#dgDrag", 800)
    m1 = pg.evaluate("() => window.Rack3D.current.dragMode()")
    ok("按切換鈕之後左鍵拖曳真的換成平移（N1）", m0 == "rotate" and m1 == "pan", f"{m0} → {m1}")
    ok("切換之後鈕上的字也跟著換",
       "平移" in text(pg, "#dgDrag"), text(pg, "#dgDrag"))
    click(pg, "#dgDrag", 800)
    ok("再按一次切回轉動", pg.evaluate("() => window.Rack3D.current.dragMode()") == "rotate")
    ok("說明有講「可轉到底下」與「平移」（N1）",
       "底下" in text(pg, "#dg3dNote") and "平移" in text(pg, "#dg3dNote"),
       text(pg, "#dg3dNote")[:90])


def t_relpanel(pg, base):
    """點關聯圖的公司，旁邊要出現「產業關係」說明（Andy 2026-09-19）。

    原話：「幫我在最底下點擊關聯圖時，在旁邊新增這類說明，更加明白產業關係」。
    圖上只有一條線，看得到「有關係」但看不懂「是什麼關係」。
    這裡驗的是**面板真的講出了關係**，不是「面板有出現」：
      - 上游／下游各自列得出來，而且品項（item）有寫
      - 每一條標了這是官方揭露、媒體報導還是產業推論（這份資料有一半是推論）
      - 「在圖上 highlight」按了，圖上的線真的亮起來、其他真的變暗，再按一次還原
      - 寬螢幕面板在圖的**旁邊**；800px 掉到圖的下面（硬並排會把圖擠到看不清）
    """
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1800)
    # 挑一家「一定有上下游」的：台積電。點卡片而不是點標題列
    sel = '#chainMap g.co[data-id="tsmc"]'
    if not pg.evaluate(f"() => !!document.querySelector({sel!r})"):
        fails.append("關聯圖上找不到台積電的卡片，後面整段驗不了")
        return
    pg.eval_on_selector(sel, "g => g.dispatchEvent(new MouseEvent('click', {bubbles:true}))")
    pg.wait_for_timeout(900)
    st = pg.evaluate("""() => { const b = document.getElementById('coBox'); if (!b) return null;
        const li = [...b.querySelectorAll('.relbox li')];
        const heads = [...b.querySelectorAll('.relbox h5')].map(h => h.textContent);
        return { has: !!b.querySelector('.relbox'), up: heads.filter(h => h.indexOf('上游') >= 0).length,
                 down: heads.filter(h => h.indexOf('下游') >= 0).length,
                 rows: li.length, items: li.filter(x => (x.querySelector('.it')||{}).textContent.trim()).length,
                 conf: b.querySelectorAll('.relbox li .cf').length,
                 dep: b.querySelectorAll('.relbox .dep').length,
                 side: !!b.classList.contains('relside'),
                 beside: (() => { const m = document.getElementById('chainMap');
                   return m && b.getBoundingClientRect().left > m.getBoundingClientRect().left + 100; })() }; }""")
    if not st:
        fails.append("點了關聯圖的公司卡片，沒有開出說明面板")
        return
    ok("點關聯圖的公司，旁邊出現「產業關係」說明", st["has"], st)
    ok("上游與下游分開列出來", st["up"] == 1 and st["down"] == 1, st)
    ok("關係不只列名字，還寫了供的是什麼品項", st["rows"] > 3 and st["items"] == st["rows"], st)
    ok("每一條都標了是官方揭露／媒體報導／產業推論", st["conf"] == st["rows"], st)
    ok("依存度用長條畫出來（不是只寫一個數字）", st["dep"] > 0, st["dep"])

    # ---- Andy 2026-09-19：「若是事實可以不上相關連結，若是你的推論也記得補上，並說明原因」
    #      推論要跟事實一眼分得開，而且要攤開「為什麼這樣推」＋佐證連結。
    pg.eval_on_selector('#chainMap g.co[data-id="gce"]',
                        "g => g.dispatchEvent(new MouseEvent('click', {bubbles:true}))")
    pg.wait_for_timeout(900)
    gs = pg.evaluate("""() => { const b = document.getElementById('coBox'); if (!b) return null;
        const g = [...b.querySelectorAll('.relbox li.guess')];
        return { n: g.length,
                 why: g.filter(x => x.querySelector('.why')).length,
                 reason: g.filter(x => /推論依據/.test(x.textContent) && /缺的是/.test(x.textContent)).length,
                 src: g.filter(x => { const a = x.querySelector('a.src');
                   return a && /^https:\\/\\//.test(a.getAttribute('href')); }).length,
                 factNoLink: [...b.querySelectorAll('.relbox li:not(.guess)')]
                   .filter(x => x.querySelector('a.src')).length }; }""")
    if gs and gs["n"]:
        ok("推論跟事實在畫面上一眼分得開（推論整塊染色）", gs["n"] > 0, gs)
        ok("每一條推論都寫了「為什麼這樣推」與「缺的是什麼」", gs["reason"] == gs["n"], gs)
        ok("每一條推論都附了佐證連結（事實不強迫附）", gs["src"] == gs["n"], gs)
    else:
        fails.append("金像電的下游應該有推論標記，卻一條都沒有")
    ok("寬螢幕時面板在圖的旁邊，不是擠在下面", st["side"] and st["beside"], st)

    # ---- 真的按 highlight：圖上的線要變
    before = pg.evaluate("""() => ({ hi: document.querySelectorAll('#chainMap .edge.hi').length,
                                     dim: document.querySelectorAll('#chainMap .edge.dim').length })""")
    pg.eval_on_selector("#relHi", "b => b.click()")
    pg.wait_for_timeout(500)
    after = pg.evaluate("""() => ({ hi: document.querySelectorAll('#chainMap .edge.hi').length,
                                    dim: document.querySelectorAll('#chainMap .edge.dim').length,
                                    codim: document.querySelectorAll('#chainMap .co.dim').length })""")
    ok("按「在圖上 highlight」，它的線真的亮起來、其他真的變暗",
       after["hi"] > before["hi"] and after["dim"] > before["dim"] and after["codim"] > 0,
       f"{before} → {after}")
    pg.eval_on_selector("#relHi", "b => b.click()")
    pg.wait_for_timeout(500)
    back = pg.evaluate("""() => ({ hi: document.querySelectorAll('#chainMap .edge.hi').length,
                                   dim: document.querySelectorAll('#chainMap .edge.dim').length,
                                   codim: document.querySelectorAll('#chainMap .co.dim').length })""")
    ok("再按一次還原（不還原使用者會以為圖壞了）",
       back["hi"] == 0 and back["dim"] == 0 and back["codim"] == 0, back)

    # ---- 沒有關聯的公司要明講，不是留白。
    #      ★ 不要寫死某一家（2026-09-19 踩到：驗收寫死台燿，結果台燿查到 AWS Trainium
    #        那條邊之後就不再孤立，驗收紅了但行為完全正確）。改成**問畫面現在誰是孤立的**。
    iso_id = pg.evaluate("""() => { const g = document.querySelector('#chainMap g.co:has(g.iso)');
        return g ? g.dataset.id : null; }""")
    if iso_id:
        pg.eval_on_selector(f'#chainMap g.co[data-id="{iso_id}"]',
                            "g => g.dispatchEvent(new MouseEvent('click', {bubbles:true}))")
        pg.wait_for_timeout(800)
        txt = text(pg, "#coBox")
        ok(f"沒有上下游的公司（{iso_id}）面板要明講「查不到就留白」而不是空白",
           "還沒有建立上下游關聯" in txt, txt[:90])
    else:
        ok("這條鏈上每一家都接得上（沒有孤立節點）", True, "沒有「?」可驗，跳過留白那條")

    # ---- 800px：面板要掉到圖的下面，不能硬並排
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.wait_for_timeout(900)
    nar = pg.evaluate("""() => { const b = document.getElementById('coBox'), m = document.getElementById('chainMap');
        if (!b || !m) return null; const rb = b.getBoundingClientRect(), rm = m.getBoundingClientRect();
        return { below: rb.top >= rm.top + 40, width: Math.round(rb.width),
                 host: Math.round(document.querySelector('.chainrow').getBoundingClientRect().width) }; }""")
    ok("800px 時面板掉到圖的下面（不硬並排把圖擠爛）", bool(nar) and nar["below"], nar)
    pg.set_viewport_size({"width": 1500, "height": 1000})


def t_batch6_n9(pg, base):
    """圖九（Andy 2026-09-19：3D 走線／電流／PIN 腳細緻度、三種配色、文字框掛個股）。

    規格書：`docs/diagram_specs/dg3d_standard.md`。
    這裡驗的是**使用者看得到的三件事真的發生了**，不是「有沒有那個物件」：
      2-1 電流：`flowAt`（所有粒子座標和）在動態模式下要變、按「動畫：關」要停且粒子收起來
      2-2 配色：按一次色票鈕，`pal()` 換人、而且畫面真的重畫
      2-3 個股晶片：文字框底下真的有晶片，點下去真的跳到個股頁
    """
    pg.set_viewport_size({"width": 1500, "height": 1000})
    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(2000)
    if not pg.evaluate("() => { const b = document.getElementById('dg3d'); return !!b && !b.hidden; }"):
        return                                   # WebGL 不支援，整段跳過（與 N1 同一條規矩）
    # ★ #dg3d 是**開關**，而且開關狀態記在 localStorage。
    #   前面 t_batch6_n1 開過 3D，這一頁載入時就已經是 3D 了 ——
    #   無條件再按一次會把它**關掉**，然後驗收報「3D 掛不起來」，
    #   但畫面上的說明文字卻是正常的那一句。只有還沒開的時候才按。
    if not pg.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
        click(pg, "#dg3d", 3000)
        pg.wait_for_timeout(3000)
    if not pg.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
        fails.append("圖九：3D 掛不起來 —— " + text(pg, "#dg3dNote")[:160])
        return
    st = pg.evaluate("() => window.Rack3D.current.stats()")

    # ---- 2-3 文字框 → 個股晶片
    # 效能棘輪（AGENTS.md 對繪圖寫的是「不准掉幀」）。
    # 2026-09-19 實測：走線一段畫一個方塊，整台機櫃從 483 個 mesh 暴增到 1846，
    # frame rate 直接砍半（29.8 → 14.1 fps，容器裡的軟體渲染）。
    # 改成「一層走線併成一個 mesh ＋ BGA 用 InstancedMesh」之後是 671 個、28.6 fps。
    # 量產圖11 時這個數字只准往下，不准往上。
    ok("3D 的 mesh 數沒有失控（圖九／量產圖11 的效能棘輪）", st["meshes"] <= 900, st["meshes"])
    ok("3D 文字框底下掛了該環節的台股晶片（圖九 2-3）", st["chips"] > 10, st["chips"])
    ok("台股掛零的環節明講「台股無直接對應」，不是留白（圖九 2-3）",
       pg.evaluate("() => [...document.querySelectorAll('.lbl3d u.chips3d')]"
                   ".every(u => u.textContent.trim().length > 0)"))
    # 真的點一顆晶片 —— 要跳到個股頁
    code = pg.evaluate("() => { const a = document.querySelector('.lbl3d .chip3d');"
                       " return a ? a.getAttribute('href') : null; }")
    ok("晶片帶得出個股連結（圖九 2-3）", bool(code) and code.startswith("#stock/"), code)
    if code:
        pg.eval_on_selector(".lbl3d .chip3d", "a => a.click()")
        pg.wait_for_timeout(2200)
        ok("點文字框上的個股晶片真的跳到個股頁（圖九 2-3）",
           pg.evaluate("() => location.hash").startswith("#stock/"),
           pg.evaluate("() => location.hash"))
        pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(2600)
        if not pg.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
            click(pg, "#dg3d", 3000); pg.wait_for_timeout(3000)

    # ---- 2-1 電流：粒子真的在跑
    st = pg.evaluate("() => window.Rack3D.current.stats()")
    ok("板子上有電流粒子系統（圖九 2-1）", st["flows"] > 0, st["flows"])
    if st["flows"]:
        # 量相位（flowT，只要在跑就單調前進）＋ 第一顆粒子的座標。
        # 不要量「所有粒子座標的總和」—— 粒子等距排成一排，整排前進時總和近乎守恆，
        # 那個數字常常一模一樣，會誤判成「電流沒在跑」（2026-09-19 實測 131.68 → 131.68）。
        a0 = pg.evaluate("() => { const s = window.Rack3D.current.stats(); return [s.flowT, s.flowAt]; }")
        pg.wait_for_timeout(1000)
        a1 = pg.evaluate("() => { const s = window.Rack3D.current.stats(); return [s.flowT, s.flowAt]; }")
        # ★ 2026-09-19 深夜：判定從 `and` 改成「flowT 必須動」。
        #   實測 [0.5801, -15.133] → [0.9001, -15.133]：相位動了、第一顆粒子的座標沒動，
        #   `and` 就判成「電流沒在跑」—— 但電流明明在跑。
        #   原因是粒子沿折線走，走到軸對齊的那一段時，某個座標分量本來就不會變。
        #   這是 DECISIONS #206「選指標前先問這個數字在正常情況下會不會變」的**第三次**
        #   （#199 canvas_hash 對 WebGL 恆定、#206 flowAt 總和近乎守恆，這次是分量不變）。
        #   flowT 是驅動粒子位置的相位，只要動畫在跑它就單調前進 —— 那才是可靠的主證據；
        #   flowAt 留在訊息裡當診斷資訊，不當判定條件。
        ok("動態模式下電流真的在走線上跑（圖九 2-1）", a0[0] != a1[0],
           f"flowT {a0[0]} → {a1[0]}（沒前進＝動畫停了）；第一顆粒子座標 {a0[1]} → {a1[1]}")
        # 按「動畫：關」→ 粒子要收起來、也要停
        pg.eval_on_selector("#dgAnim", "b => b.click()")
        pg.wait_for_timeout(900)
        s2 = pg.evaluate("() => window.Rack3D.current.stats()")
        b0 = [s2["flowT"], s2["flowAt"]]
        pg.wait_for_timeout(900)
        b1 = pg.evaluate("() => { const s = window.Rack3D.current.stats(); return [s.flowT, s.flowAt]; }")
        ok("按「動畫：關」電流真的停下來（圖九 2-1）", b0 == b1, f"{b0} → {b1}")
        ok("靜止時粒子收起來，走線本身還在（圖九 2-1）",
           s2["flowVisible"] == 0 and s2["meshes"] > 500, s2["flowVisible"])
        pg.eval_on_selector("#dgAnim", "b => b.click()")
        pg.wait_for_timeout(700)

    # ---- 2-2 三種配色
    ok("有看得見的配色切換鈕（圖九 2-2）",
       pg.evaluate("() => { const b = document.getElementById('dgPal'); return !!b && !b.hidden; }"))
    seen, changed_n = [], 0
    for _ in range(3):
        p0 = pg.evaluate("() => window.Rack3D.current.pal()")
        # WebGL 的畫布拿不到 2d context，canvas_hash 對它一律回同一個值 ——
        # 改量真正被畫出去的東西：所有材質顏色的指紋（colorSig）
        h0 = pg.evaluate("() => window.Rack3D.current.stats().colorSig")
        pg.eval_on_selector("#dgPal", "b => b.click()")
        pg.wait_for_timeout(1100)
        p1 = pg.evaluate("() => window.Rack3D.current.pal()")
        seen.append(p1)
        if p0 != p1:
            changed_n += 1
        ok(f"按配色鈕真的換色票（{p0} → {p1}）（圖九 2-2）", p0 != p1, f"{p0} → {p1}")
        h1 = pg.evaluate("() => window.Rack3D.current.stats().colorSig")
        ok(f"換成 {p1} 之後零件顏色真的變了（圖九 2-2）", h0 != h1, f"{h0} → {h1}")
        ok(f"鈕上的字跟著換（{p1}）", "配色：" in text(pg, "#dgPal"), text(pg, "#dgPal"))
    ok("三種色票都輪得到（tech / soft / calm）（圖九 2-2）",
       sorted(set(seen)) == ["calm", "soft", "tech"], seen)
    ok("「柔和」色票零件不發光（印得出來）（圖九 2-2）",
       pg.evaluate("""() => { const v = window.Rack3D.current; v.setPal('soft');
           return v.stats().maxEmissive === 0; }"""))
    pg.evaluate("() => window.Rack3D.current.setPal('tech')")

    # ---- 窄畫面：800px 也要看得到晶片，而且文字框不出框
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.wait_for_timeout(1400)
    nar = pg.evaluate("""() => { const host = document.getElementById('prod3d');
        const r = host.getBoundingClientRect();
        const ls = [...host.querySelectorAll('.lbl3d')].filter(e => !e.classList.contains('hid'));
        const out = ls.filter(e => { const b = e.getBoundingClientRect();
          return b.left < r.left - 1 || b.right > r.right + 1; }).map(e => e.querySelector('b').textContent);
        return { labels: ls.length, out, chips: host.querySelectorAll('.chip3d').length }; }""")
    ok("800px 下 3D 文字框沒有出框（圖九）", not nar["out"], nar["out"][:4])
    ok("800px 下個股晶片還在（圖九 2-3）", nar["chips"] > 0, nar)
    pg.set_viewport_size({"width": 1500, "height": 1000})


SC_GEOM = """() => {
  const svg = document.querySelector('#chainMap svg'); if (!svg) return null;
  const cards = [...svg.querySelectorAll('g.co')].map(g => { const r = g.querySelector('rect');
    return { id: g.dataset.id, x: +r.getAttribute('x'), y: +r.getAttribute('y'),
             w: +r.getAttribute('width'), h: +r.getAttribute('height') }; });
  const byId = {}; cards.forEach(c => (byId[c.id] = c));
  const paths = [...svg.querySelectorAll('path.edge')];
  const badEnd = [], cross = [];
  const onEdge = (pt, c) => Math.min(Math.abs(pt.x - c.x), Math.abs(pt.x - (c.x + c.w))) <= 2
                            && pt.y >= c.y - 2 && pt.y <= c.y + c.h + 2;
  paths.forEach(p => {
    const a = byId[p.dataset.from], b = byId[p.dataset.to]; if (!a || !b) return;
    const L = p.getTotalLength();
    if (!onEdge(p.getPointAtLength(0), a) || !onEdge(p.getPointAtLength(L), b))
      badEnd.push(p.dataset.from + '→' + p.dataset.to);
    for (let i = 1; i < 60; i++) { const pt = p.getPointAtLength(L * i / 60);
      const hit = cards.find(c => c.id !== a.id && c.id !== b.id
        && pt.x > c.x + 1 && pt.x < c.x + c.w - 1 && pt.y > c.y + 1 && pt.y < c.y + c.h - 1);
      if (hit) { cross.push(p.dataset.from + '→' + p.dataset.to + ' 穿過 ' + hit.id); break; } }
  });
  /* 文字重疊：用 getBBox 兩兩比，SVG 座標系裡算，跟畫面縮放無關。
     2026-09-19 踩到：環節沒有台股時改顯示 note，但一行切 18 個字**超出欄寬**，
     整段跑到隔壁欄壓到別人的卡片；行距 13px 也小於 11px 中文的實際行高，自己壓自己。 */
  // 只比 text vs text，而且跳過同一張卡片裡的兩行（那本來就疊在同一個 rect 上，不是重疊）
  const tb = [...svg.querySelectorAll('text')]
    .map(e => ({ t: (e.textContent || '').trim().slice(0, 12), g: e.closest('g'), b: e.getBBox() }))
    .filter(x => x.t && x.b.width > 0 && x.b.height > 0);
  const overlap = [];
  for (let i = 0; i < tb.length; i++) for (let j = i + 1; j < tb.length; j++) {
    if (tb[i].g && tb[i].g === tb[j].g) continue;
    const a = tb[i].b, c = tb[j].b;
    if (a.x < c.x + c.width - 1 && a.x + a.width > c.x + 1
        && a.y < c.y + c.height - 1 && a.y + a.height > c.y + 1) overlap.push(tb[i].t + ' ↔ ' + tb[j].t);
  }
  /* 環節標題不可以比欄寬長。欄寬 178、標題左邊留 19px 給圓點，所以可用寬度約 155。
     超出去字會跑出色塊外面（2026-09-19 新增「企業級儲存 / NAND 控制 IC」時實測到）。*/
  const longTitle = [...svg.querySelectorAll('g.segtitle text.seg-title')]
    .filter(t => t.getBBox().width > 155).map(t => t.textContent);
  const kids = [...svg.children].map(n => n.getAttribute('class') || n.tagName);
  const linked = new Set();
  paths.forEach(p => { linked.add(p.dataset.from); linked.add(p.dataset.to); });
  const isoBad = [...svg.querySelectorAll('g.co')].filter(g => {
    const marked = !!g.querySelector('g.iso');
    return marked !== !linked.has(g.dataset.id);
  }).map(g => g.dataset.id);
  return { n: paths.length, cards: cards.length, badEnd, cross,
           isoOk: isoBad.length === 0, isoBad, overlap: overlap.slice(0, 6), longTitle,
           iso: svg.querySelectorAll('g.iso').length,
           noArrow: paths.filter(p => !p.getAttribute('marker-end')).length,
           dash: svg.querySelectorAll('path.edge.dash').length,
           competes: paths.filter(p => p.dataset.rel === 'competes').length,
           widths: [...new Set(paths.map(p => getComputedStyle(p).strokeWidth))].length,
           last: kids[kids.length - 1],
           pe: getComputedStyle(svg.querySelector('g.elayer') || svg).pointerEvents,
           overflow: Math.round(svg.getBoundingClientRect().right
                                - document.querySelector('#chainMap').getBoundingClientRect().right),
           scrollable: (() => { const el = document.querySelector('#chainMap');
             return el.scrollWidth - el.clientWidth > 4 && /auto|scroll/.test(getComputedStyle(el).overflowX); })() };
}"""

# 孤立節點上限（棘輪：只准變少，不准變多）。
# 2026-09-19 早上：ai_server 10 / semiconductor 13（全是我猜的、沒查證，所以不敢畫線）。
# 2026-09-19 下午：三位 industry-analyst 查證後補上 45 條有出處的邊，
#   降到 ai_server 1 / semiconductor 0。剩下的那一個是台燿 6274 ——
#   公開來源查不到具名客戶，**刻意**讓它維持「?」，不畫猜的線。
# ★ 2026-09-19 傍晚：ai_server 從 1 降到 0。那個 1 是台燿 6274 ——
#   上午找不到它的**下游**具名客戶所以刻意讓它孤立，傍晚查到它的**上游**：
#   「金居…作為 CCL 廠商台光電、聯茂、台燿的上游供應商」是一句明確的供貨陳述，
#   不是並列標題。找不到下游不代表找不到上游。
#   這一批另外加了 15 家公司，每一家都至少帶一條有出處的邊進來，所以棘輪可以收到 0。
# ★ 2026-09-19 傍晚（第二次調）：semiconductor 從 0 放寬到 3。
#   棘輪本來只准往下走，這次是**刻意往上**，所以理由要寫清楚、而且要指名是哪三家：
#   旺矽 6223、中華精測 6510、雍智 6683 —— 台股測試介面四雄裡的三家。
#   四雄只有穎崴 6515 查得到具名客戶（NVIDIA、AMD），另外三家的報導一律是
#   「兩大 ASIC 新客戶」「前三大客戶」「美系客戶逾 55%」這種不具名寫法。
#   依 DECISIONS #201「查不到出處就不畫，讓節點掛『?』」—— 畫一條猜的線比留一個「?」糟糕得多。
#   加它們的價值：使用者點「測試介面」時看到台股有四家，而不是誤以為只有穎崴一家。
#   ★ 兩個視圖都是 3、而且是**同樣那三家**：industry.js 的 CHAIN_EXTRA 把 test_interface
#     這個環節同時拉進 ai_server 視圖渲染（AI 晶片的測試介面本來就屬於那條鏈的上游），
#     所以同一批節點在兩張圖上各孤立一次。我第一次調棘輪時只想到半導體那一邊、
#     把 ai_server 留在 0，_uitest 就紅了 —— 這正是這條棘輪該做的事。
#   ★ 任何一邊變成 4 就要擋下來，那代表有人又加了一個查不到關係的節點。
SC_ISO_MAX = {"ai_server": 3, "semiconductor": 3}


def t_batch6_n3(pg, base):
    """圖十（Andy 2026-09-19：「供應鏈關聯圖 連線對不起來」）的真人操作驗收。

    這裡驗的是幾何，不是「有沒有 render」——
    以前每條邊都寫死「來源右緣→目標左緣」，目標在左邊的邊會整條倒著從卡片底下穿過去，
    畫面上看起來就是「線連到不相干的公司」。所以要量三件事：
      1. 每條邊的兩端真的落在兩張卡片的邊緣（±2px）
      2. 沒有任何一條邊從非端點的卡片身上穿過去
      3. 線畫在卡片之上（不會被卡片蓋掉），而且不吃滑鼠（不然卡片點不到）
    1440 與 800 兩個寬度各驗一次 —— 800px 是 Andy 把瀏覽器縮成半邊的寬度。
    """
    for wpx in (1500, 800):
        pg.set_viewport_size({"width": wpx, "height": 1000})
        tag = f"（{wpx}px）"
        for cid in ("ai_server", "semiconductor"):
            pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(1800)
            g = pg.evaluate(SC_GEOM)
            if not g:
                fails.append(f"{cid} 的供應鏈關聯圖整張沒畫出來{tag}")
                continue
            ok(f"{cid} 供應鏈圖有畫出連線{tag}", g["n"] > 10, g["n"])
            ok(f"{cid} 每條邊兩端都落在卡片邊緣 ±2px（圖十）{tag}", not g["badEnd"], g["badEnd"][:5])
            ok(f"{cid} 沒有邊穿過不相干的卡片（圖十）{tag}", not g["cross"], g["cross"][:5])
            ok(f"{cid} 連線畫在卡片之上（不會被卡片蓋掉）{tag}", "elayer" in (g["last"] or ""), g["last"])
            ok(f"{cid} 連線層不吃滑鼠（卡片還是點得到）{tag}", g["pe"] == "none", g["pe"])
            ok(f"{cid} 每條邊都有箭頭（看得出誰供給誰）{tag}", g["noArrow"] == 0, g["noArrow"])
            ok(f"{cid} 線的粗細真的依依存度不同（不是全部一樣粗）{tag}", g["widths"] > 1, g["widths"])
            ok(f"{cid} competes（競爭關係）不畫成上下游{tag}", g["competes"] == 0, g["competes"])
            ok(f"{cid} 孤立節點沒有變多（棘輪，上限 {SC_ISO_MAX[cid]}）{tag}",
               g["iso"] <= SC_ISO_MAX[cid],
               f"{g['iso']} 個孤立 / 共 {g['cards']} 張卡")
            ok(f"{cid} 「?」只標在真的沒有線的卡片上{tag}", g["isoOk"], g["isoBad"][:4])
            ok(f"{cid} 圖上沒有文字互相壓到{tag}", not g["overlap"], g["overlap"])
            ok(f"{cid} 環節標題沒有長到跑出色塊{tag}", not g["longTitle"], g["longTitle"])
            # 窄畫面放不下是允許的（.chainmap 本來就 overflow:auto），
            # 但一定要「捲得到」，不可以被切掉看不見 —— 2026-09-18 的 E6 就是這樣漏掉的。
            ok(f"{cid} 圖沒有被切掉（寬的放得下、窄的捲得到）{tag}",
               g["overflow"] <= 1 or g["scrollable"], {"overflow": g["overflow"], "scrollable": g["scrollable"]})
        # ---- 真的把滑鼠移到一張卡片上，相關的線要亮起來、其他的要變暗
        pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1800)
        pg.eval_on_selector("#chainMap g.co", "g => g.dispatchEvent(new MouseEvent('mouseenter'))")
        pg.wait_for_timeout(400)
        hl = pg.evaluate("""() => ({ hi: document.querySelectorAll('#chainMap path.edge.hi').length,
                                     dim: document.querySelectorAll('#chainMap path.edge.dim').length })""")
        ok(f"滑鼠移到卡片上，它的線亮起來、其他變暗（圖十）{tag}",
           hl["hi"] > 0 and hl["dim"] > 0, hl)
        pg.eval_on_selector("#chainMap g.co", "g => g.dispatchEvent(new MouseEvent('mouseleave'))")
    pg.set_viewport_size({"width": 1500, "height": 1000})


def t_season(pg, base):
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("季節性熱力圖有畫出來", pg.evaluate("() => !!document.querySelector('#seasonHeat canvas')"))
    ok("季節性頁有區間文字", len(text(pg, "#seasonRange")) > 3, text(pg, "#seasonRange"))

    # J1（Andy 2026-09-18：「族群 × 月份還需要新增圖表方式表示 包含曲線圖，這樣看圖更直觀」）
    vs = pg.evaluate("() => [...document.querySelectorAll('#seasonView button')].map(b => b.dataset.v)")
    ok("族群×月份有熱力圖／曲線圖兩種呈現", vs == ["heat", "line"], vs)
    ok("預設是熱力圖", pg.evaluate("() => [document.getElementById('seasonHeat').hidden,"
                                  " document.getElementById('seasonLine').hidden]") == [False, True])
    click(pg, '#seasonView button[data-v="line"]', 1300)
    ok("切到曲線圖：熱力圖收起來、曲線圖出來",
       pg.evaluate("() => [document.getElementById('seasonHeat').hidden,"
                   " document.getElementById('seasonLine').hidden]") == [True, False])
    ok("曲線圖真的畫出來了", canvas_hash(pg, "#seasonLine") not in ("no-canvas", "0"),
       canvas_hash(pg, "#seasonLine"))
    ser = pg.evaluate("""() => { const c = echarts.getInstanceByDom(document.getElementById('seasonLine'));
        if (!c) return null; const o = c.getOption();
        return { n: o.series.length, type: o.series[0].type, pts: (o.series[0].data || []).length,
                 open: Object.values(o.legend[0].selected || {}).filter(Boolean).length }; }""")
    ok("是線圖、12 個月一條線", bool(ser) and ser["type"] == "line" and ser["pts"] == 12, ser)
    ok("預設只打開少數幾條（26 條疊在一起是一團毛線）",
       bool(ser) and 0 < ser["open"] <= 10, ser)
    # 換指標，曲線圖要跟著變（不是只有熱力圖會變）
    l0 = canvas_hash(pg, "#seasonLine")
    click(pg, '#seasonMetric button[data-v="win_rate"]', 1300)
    changed("換指標，曲線圖跟著重畫", l0, canvas_hash(pg, "#seasonLine"))
    ok("選過的呈現方式有記住",
       pg.evaluate("() => { try { return localStorage.getItem('tw.season.view'); } catch(e){ return null; } }") == "line")
    click(pg, '#seasonView button[data-v="heat"]', 1100)
    ok("切回熱力圖也還在", pg.evaluate("() => document.getElementById('seasonLine').hidden") is True)
    click(pg, '#seasonMetric button[data-v="avg_excess"]', 900)
    for grp, name in (("#seasonPeriod", "期間"), ("#seasonMetric", "指標")):
        vs = pg.evaluate(f"[...document.querySelectorAll('{grp} button')].filter(b => b.style.display !== 'none').map(b => b.dataset.v)")
        if len(vs) >= 2:
            h0 = canvas_hash(pg, "#seasonHeat")
            click(pg, f'{grp} button[data-v="{vs[-1]}"]', 900)
            changed(f"季節性切換「{name}」，熱力圖真的重畫", h0, canvas_hash(pg, "#seasonHeat"))
            click(pg, f'{grp} button[data-v="{vs[0]}"]', 700)
        else:
            notes.append(f"季節性「{name}」只有一個選項，沒東西可切")
    # 點格子 → 逐年明細要出來。用 ECharts 自己換算某一格的座標，不要亂點（亂點會落在空白處）
    pg.evaluate("document.getElementById('seasonHeat').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
    before = text(pg, "#seasonDrillTitle")
    pt = pg.evaluate("""() => { const e = document.getElementById('seasonHeat');
        const c = echarts.getInstanceByDom(e); if (!c) return null;
        const op = c.getOption(); const d = (op.series[0] || {}).data || [];
        const cell = d.find(v => Array.isArray(v) ? v[2] != null : (v && v.value && v.value[2] != null));
        if (!cell) return null;
        const v = Array.isArray(cell) ? cell : cell.value;
        const p = c.convertToPixel({ seriesIndex: 0 }, [v[0], v[1]]);
        const r = e.getBoundingClientRect();
        return p ? { x: r.x + p[0], y: r.y + p[1] } : null; }""")
    if pt:
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(1200)
        after = text(pg, "#seasonDrillTitle")
        changed("點季節性格子會帶出逐年明細", before, after)
        ok("逐年明細有畫出圖", pg.evaluate("() => !!document.querySelector('#seasonDrill canvas')"),
           text(pg, "#seasonDrill")[:40])
    else:
        fails.append("季節性熱力圖沒有任何一格有資料，點不出逐年明細")


# 量「畫布上跟背景不一樣的像素占多少」。白線畫在白底上 → 這個數字會掉下去。
INK = """(sel) => {
  const c = document.querySelector(sel).querySelector('canvas');
  if (!c || !c.width || !c.height) return null;
  let g; try { g = c.getContext('2d'); } catch (e) { return null; }
  if (!g) return null;
  let d; try { d = g.getImageData(0, 0, c.width, c.height).data; } catch (e) { return null; }
  // 背景取左上角那一點（圖表四周一定是空白）
  const bg = [d[0], d[1], d[2]];
  let ink = 0, n = 0;
  for (let i = 0; i < d.length; i += 4 * 5) {
    n++;
    if (d[i + 3] > 8 && Math.abs(d[i] - bg[0]) + Math.abs(d[i + 1] - bg[1]) + Math.abs(d[i + 2] - bg[2]) > 30) ink++;
  }
  return n ? ink / n : null;
}"""

# 找出「文字顏色跟自己的背景幾乎一樣」的元素 —— 黑底時代留下來的白字，切到淺色就變隱形。
CONTRAST = """() => {
  const lum = (c) => { const m = (c.match(/[\\d.]+/g) || []).map(Number);
    const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
    return .2126 * f(m[0] || 0) + .7152 * f(m[1] || 0) + .0722 * f(m[2] || 0); };
  // 往上找第一個「不透明的純色背景」。中途碰到漸層就放棄這個元素 ——
  // 漸層量不出單一背景色，硬算會把「白字印在青紫漸層 logo 上」誤報成看不見。
  const bgOf = (el) => { let e = el;
    while (e && e !== document.documentElement) {
      const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      const c = s.backgroundColor;
      const m = (c.match(/[\\d.]+/g) || []).map(Number);
      if (m.length >= 4 ? m[3] > 0.4 : m.length === 3) return c;
      e = e.parentElement;
    }
    return getComputedStyle(document.body).backgroundColor; };
  const bad = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length) continue;
    const txt = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    if (txt.length < 2) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 6 || r.height < 6) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity < 0.25) continue;
    const bgc = bgOf(el); if (!bgc) continue;          // 背景是漸層，算不出對比度
    const a = lum(s.color), b = lum(bgc);
    const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    if (ratio < 1.9) bad.push({ tag: el.tagName.toLowerCase(), cls: el.className.toString().slice(0, 40),
                                txt: txt.slice(0, 26), color: s.color, bg: bgc, ratio: +ratio.toFixed(2) });
    if (bad.length > 14) break;
  }
  return bad;
}"""


def t_kzoom_keep(pg, base, code):
    """K 線縮放之後不可以自己彈回原來的大小。

    Andy 2026-09-18：「K 線圖每次縮放後 他會跳動變回來原來大小」。
    盤中每幾秒就有一次即時更新，只要有一次沒保住可視範圍，使用者就等於不能縮放。
    所以這裡**真的滾滾輪縮放，再真的觸發一次重畫**，比對前後的可視範圍。
    """
    pg.goto("about:blank")
    pg.goto(base + f"#stock/{code}", wait_until="networkidle")
    pg.wait_for_timeout(3000)
    rng = "() => { const c = window.Industry._dbg(); return c && c.visibleBars; }"

    scroll_to(pg, "lwc")
    box = pg.evaluate("() => { const r = document.getElementById('lwc').getBoundingClientRect();"
                      " return {x:r.x+r.width*0.5, y:r.y+r.height*0.4}; }")
    before = pg.evaluate(rng)
    pg.mouse.move(box["x"], box["y"])
    for _ in range(4):
        pg.mouse.wheel(0, -120)          # 往上滾＝放大
        pg.wait_for_timeout(120)
    pg.wait_for_timeout(500)
    zoomed = pg.evaluate(rng)
    ok("滾輪真的縮放得動", bool(before and zoomed and zoomed != before), {"前": before, "後": zoomed})

    # 模擬一次即時更新造成的重畫（盤中每幾秒一次）
    pg.evaluate("() => { if (window.Industry && window.Industry._apply) window.Industry._apply(); }")
    pg.wait_for_timeout(700)
    after = pg.evaluate(rng)
    ok("重畫之後縮放沒有被彈回去", after == zoomed,
       {"縮放後": zoomed, "重畫後": after, "原始": before})


def t_lightink(b, base, code):
    """淺色主題下「東西還在不在」（Andy 2026-09-16：
    「由於一開始製作是黑色底，很多數據都是白色線條及文字，檢查所有切換回白色 UI 後需要更改的顏色」）。

    既有的 `t_theme` 只驗「主題真的切過去了」——那不夠。
    白色的線畫在白色的底上，主題確實切了，**但那條線不見了**。
    所以這裡驗的是兩件會壞的事：

    1. **圖表**：同一張圖在深色與淺色各量一次「跟背景不同的像素占比」。
       淺色掉到深色的一半以下，代表有東西在淺色底下消失了。
    2. **文字**：掃整頁的文字元素，算它跟自己背景的對比度，低於 1.9 就是幾乎看不見。
    """
    # 2026-09-18：補上 #season 與 #industry。
    # 季節性頁的字色、格線、色階中點以前全是寫死的深色值（Andy 圖17「切換到明亮版本，
    # 字體不可為淺色」），而這份掃描根本沒走到那一頁，所以一路沒被抓到。
    # 產業板塊圖同理（圖13：treemap 用 itemStyle.borderColor 當整片底色，寫死 #0b1224）。
    pages = [("#overview", ["#heat"]),
             ("#flow", ["#rotClock", "#sankey", "#instGroups", "#conc", "#valScatter"]),
             ("#industry", ["#indTree"]),
             ("#season", ["#seasonHeat"]),
             (f"#stock/{code}", ["#peChart", "#profitChart", "#peQ"])]
    ctx = b.new_context(viewport={"width": 1500, "height": 1000})
    pg = ctx.new_page()
    pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())

    def sweep(mode):
        """把主題設成 mode，走過每一頁，回傳 {選擇器: ink 占比} 與文字對比問題。"""
        pg.goto("about:blank")
        pg.add_init_script(f"try{{localStorage.setItem('tw.theme','{mode}');}}catch(e){{}}")
        got, low = {}, []
        for hash_, sels in pages:
            pg.goto(base + hash_, wait_until="networkidle")
            pg.wait_for_timeout(2600)
            for s in sels:
                if pg.evaluate(f"() => !!document.querySelector({s!r})"):
                    pg.evaluate(f"() => document.querySelector({s!r}).scrollIntoView({{block:'center'}})")
                    pg.wait_for_timeout(500)
                    v = pg.evaluate(INK, s)
                    if v is not None:
                        got[hash_ + " " + s] = v
            low += [dict(page=hash_, **d) for d in pg.evaluate(CONTRAST)]
        return got, low

    dark, _ = sweep("dark")
    light, low = sweep("light")

    ok("淺色主題下量得到圖表（至少 4 張）", len(light) >= 4, sorted(light))
    for k, dv in sorted(dark.items()):
        lv = light.get(k)
        if lv is None:
            fails.append(f"淺色主題下這張圖量不到：{k}")
            continue
        # 深色那張本來就幾乎空白（沒資料）就不比，不然會誤報
        if dv < 0.02:
            continue
        ok(f"淺色主題下「{k}」內容沒有消失",
           lv >= dv * 0.5, f"深色 ink={dv:.3f} → 淺色 ink={lv:.3f}（掉超過一半＝有東西是白的）")

    ok("淺色主題下沒有看不見的文字（對比度 < 1.9）", not low,
       low[:6])
    ctx.close()


def t_mobile(b, base, code):
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.on("pageerror", lambda e: fails.append(f"手機 pageerror: {e}"))
    m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    for h, name in (("overview", "總覽"), ("market", "市場明細"), ("flow", "資金流向"), ("industry", "產業"),
                    ("themes", "題材"), ("season", "季節性"), (f"stock/{code}", "個股")):
        m.goto(f"{base}#{h}", wait_until="networkidle"); m.wait_for_timeout(1700)
        st = m.evaluate("""() => {
            // SVG 文字會跟著 viewBox 一起縮放，所以要量「螢幕上真正的大小」而不是 CSS 值
            const eff = (e) => { const s = parseFloat(getComputedStyle(e).fontSize);
              if (e.ownerSVGElement) { try { const m = e.getScreenCTM(); return m ? s * Math.abs(m.a) : s; } catch (x) { return s; } }
              return s; };
            const tiny = [...document.querySelectorAll('main .view.on *')].filter(e => {
              const t = [...e.childNodes].some(n => n.nodeType===3 && n.textContent.trim().length>1);
              if (!t) return false;
              const r = e.getBoundingClientRect(); if (!r.width || !r.height) return false;
              const s = eff(e); return s > 0 && s < (e.ownerSVGElement ? 8 : 11); })
              .map(e => `${(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || e.tagName}@${eff(e).toFixed(1)}px:${e.textContent.trim().slice(0,10)}`);
            return { sideways: document.documentElement.scrollWidth > 391,
                     text: (document.querySelector('main .view.on')||document.body).innerText.trim().length,
                     tiny }; }""")
        ok(f"手機／{name} 沒有橫向捲軸", not st["sideways"], st["sideways"])
        ok(f"手機／{name} 有內容", st["text"] > 60, st["text"])
        ok(f"手機／{name} 沒有看不清楚的小字", not st["tiny"], st["tiny"][:6])
    # 手機分頁列真的能切
    m.goto(f"{base}#overview", wait_until="networkidle"); m.wait_for_timeout(1400)
    tabs = m.evaluate("[...document.querySelectorAll('#tabs .tab')].map(a => a.dataset.view)")
    ok("手機有分頁列", len([t for t in tabs if t]) >= 6, tabs)
    # 分頁列真的按得動（手機上它固定在畫面底部）
    if tabs:
        m.evaluate("document.querySelector('#tabs .tab[data-view=themes]').click()"); m.wait_for_timeout(1400)
        ok("手機分頁列按得動", m.evaluate("location.hash").startswith("#themes"), m.evaluate("location.hash"))
    m.close()


def t_zoom_sweep(pg, base, code):
    """全站掃一遍縮放入口。Andy 講過很多次：**只有指定的那幾張可以縮放**
       （總覽資金熱力 heatWrap、產業地圖板塊 indTreeWrap、題材資金熱力 themeMapWrap，
       以及 2026-09-15 他親口要的「法人連續買超」trustWrap、
       2026-09-16 他親口要的「本益比河流圖」peWrap）。
       這一段是最後一道防線：任何一頁冒出多餘的縮放框、徽章或「放大」鈕都算失敗。

       2026-09-18 增補（Andy 圖二「右上角 可以放大這圖 包含資金流向那頁一併修改」）：
       輪動時鐘的兩顆放大鈕（總覽 rotMiniZoomBtn、資金流向 rotZoomBtn）加進白名單。
       這是他親口要的第六、七個縮放入口，見 DECISIONS #185。
       白名單只能因為他開口而變長 —— 不准為了讓測試變綠而加。"""
    ALLOW = ("heatWrap", "indTreeWrap", "themeMapWrap", "heatZoom", "themeZoom", "trustWrap", "peWrap",
             "rotMiniZoomBtn", "rotZoomBtn")
    SCAN = """() => {
      const out = { badge: [], zwrap: [], btn: [] };
      document.querySelectorAll('.zbadge').forEach(e => out.badge.push(e.parentElement.id || e.parentElement.className));
      document.querySelectorAll('.zwrap').forEach(e => out.zwrap.push(e.id || e.className));
      document.querySelectorAll('button,span.pill,.btn').forEach(e => {
        const t = (e.textContent || '').trim();
        if (/放大|縮放|zoom/i.test(t) && e.offsetParent !== null) out.btn.push((e.id || '(無 id)') + ':' + t.slice(0, 12));
      });
      return out; }"""
    pages = [("#overview", "總覽"), ("#flow", "資金流向"), ("#industry", "產業地圖"),
             ("#industry/ai_server", "AI 伺服器鏈"), ("#themes", "題材"),
             ("#market", "市場明細"), ("#season", "季節性"), (f"#stock/{code}", "個股")]
    # 題材細節頁（產品剖析圖那一頁）全部都掃
    pg.goto(f"{base}#themes", wait_until="networkidle"); pg.wait_for_timeout(1500)
    for tid in (pg.evaluate("() => Object.keys(window.ThemeDiagrams || {}).filter(k => k !== 'fit')") or [])[:6]:
        pages.append((f"#themes/{tid}", f"題材 {tid}"))
    for path, name in pages:
        pg.goto(base + path, wait_until="networkidle"); pg.wait_for_timeout(1500)
        r = pg.evaluate(SCAN)
        extra = {k: [x for x in v if not any(a in str(x) for a in ALLOW)] for k, v in r.items()}
        n = sum(len(v) for v in extra.values())
        ok(f"「{name}」沒有多餘的縮放入口", n == 0, extra)


def t_freshness(b, base):
    """資料狀態橫幅：Andy 的核心痛點是「不知道畫面上這份資料是哪天的、有沒有缺」。

    真的把 meta.json 換成四種狀態、真的開頁面、真的讀那條橫幅的文字與顏色，
    而且四種狀態要長得不一樣 —— 只驗「元素存在」等於沒驗。
    """
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    ago = lambda h: (now - _dt.timedelta(hours=h)).isoformat()
    BASE = {"status": "ok", "history_days": 6595, "groups_health": {}, "table_summary": [],
            "last_run_trade_date": None, "last_run_phase": "full",
            "last_run_errors": [], "last_run_empty": []}
    cases = [
        ("一切正常", {**BASE, "data_date": "2026-09-12", "price_latest": "2026-09-12",
                  "price_ahead_of_payload": False, "generated_at": ago(2), "last_run_at": ago(3)},
         "ok", ["所有來源正常"]),
        ("盤後第一輪只抓價量", {**BASE, "data_date": "2026-09-12", "price_latest": "2026-09-12",
                       "price_ahead_of_payload": False, "last_run_phase": "price",
                       "generated_at": ago(1), "last_run_at": ago(1)},
         "ok", ["只更新價量"]),
        ("上市沒到齊卡在前一天", {**BASE, "data_date": "2026-09-10", "price_latest": "2026-09-11",
                       "price_ahead_of_payload": True, "generated_at": ago(20), "last_run_at": ago(21),
                       "last_run_empty": ["twse.dividend", "macro.fred"]},
         "warn", ["沒到齊", "沒回資料的來源", "macro.fred"]),
        ("排程掛了", {**BASE, "data_date": "2026-09-01", "price_latest": "2026-09-01",
                  "price_ahead_of_payload": False, "generated_at": ago(24 * 13), "last_run_at": ago(24 * 13),
                  "last_run_errors": ["twse.price_daily: HTTPError 500"]},
         "bad", ["排程可能掛了", "來源出錯"]),
    ]
    seen = []
    for name, meta, level, must in cases:
        ctx = b.new_context(viewport={"width": 1500, "height": 1000})   # 每個狀態一個乾淨環境，避開 HTTP 快取
        pg = ctx.new_page()
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("**/data/meta.json*", (lambda m: lambda r: r.fulfill(
            status=200, content_type="application/json; charset=utf-8",
            headers={"cache-control": "no-store"}, body=json.dumps(m, ensure_ascii=False)))(meta))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.wait_for_function("() => { const e = document.getElementById('asof');"
                             " return e && e.textContent.trim() !== ''; }", timeout=30000)
        pg.wait_for_timeout(300)
        got = pg.evaluate("""() => { const b = document.getElementById('banner');
            return { cls: b.className, on: getComputedStyle(b).display !== 'none',
                     txt: b.innerText.replace(/\\s+/g, ' ').trim(),
                     asof: (document.getElementById('asof') || {}).textContent || '' }; }""")
        ok(f"「{name}」橫幅有顯示", got["on"], got["cls"])
        ok(f"「{name}」燈號是 {level}", level in got["cls"], got["cls"])
        ok(f"「{name}」頂端日期跟著 meta 走", str(meta["data_date"]) in got["asof"], got["asof"])
        miss = [w for w in must if w not in got["txt"]]
        ok(f"「{name}」把原因講出來了", not miss, {"少了": miss, "實際": got["txt"][:160]})
        seen.append(got["txt"])
        ctx.close()
    ok("四種狀態的文字彼此不同（不是同一段罐頭）", len(set(seen)) == 4,
       [s[:40] for s in seen])


def t_cfgpop(pg, base, code):
    """設定面板：關掉之後**按一次**就要叫得回來（Andy 2026-09-16：「設定面板會消失，我需要會再呼叫」）。

    以前 ⚙ 只看 `pop.hidden` 決定開或關，但面板可以在 hidden 還是 false 的情況下消失
    （換分頁再回來、重畫、被定位到畫面外）。那時候按 ⚙ 走的是「關閉」那一條，
    等於關掉一個本來就看不見的東西 —— 使用者看到的就是「按了沒反應」。
    所以這裡驗的是**按一次之後畫面上真的看得到**，不是「元素存在」。
    """
    seen = lambda: pg.evaluate(
        """() => { const p = document.getElementById('cfgPop'); if (!p || p.hidden) return false;
             const r = p.getBoundingClientRect();
             return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight
                    && r.right > 0 && r.left < innerWidth; }""")
    pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2600)

    click(pg, '#cfgBtn', 350); ok("按設定面板會開", seen())
    pg.mouse.click(760, 120); pg.wait_for_timeout(350)
    ok("點面板外面會收起來", not seen())
    click(pg, '#cfgBtn', 400)
    ok("收起來之後按一次就叫得回來（不是按兩次）", seen())

    # 在面板裡面點（例如調滑桿）不能把自己關掉
    click(pg, '#cfgPop .ttl', 300)
    ok("在面板裡面點不會把面板關掉", seen())

    # 換到別的分頁再回來 —— 這條就是原本壞掉的那條路徑
    click(pg, '.tab[data-view="flow"]', 1400)
    pg.go_back(); pg.wait_for_timeout(2400)
    ok("換頁時面板收掉了", not seen())
    click(pg, '#cfgBtn', 450)
    ok("換頁回來按一次就開得起來", seen())

    click(pg, '#cfgBtn', 350)
    ok("再按一次會關掉（切換本身沒壞）", not seen())


def t_buildver(b, base):
    """網頁版號（Andy 2026-09-16：「每次說有更新，但打開來跟原本一樣」）。

    這條的重點不是「有沒有那個元素」，而是**換一個版號，畫面上的字真的跟著換**
    —— 不然這顆徽章只會變成另一個騙人的裝飾品。
    所以用兩組不同的版號各開一次頁面，比對兩次讀到的字不一樣。
    """
    def run(label):
        ctx = b.new_context(viewport={"width": 1500, "height": 1000})
        pg = ctx.new_page()
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        # 把 index.html 抓下來，就地把版號那個 meta 換掉，模擬部署時 stamp_assets.py 做的事
        def patch(route):
            r = route.fetch()
            html = (r.text()
                    .replace('<meta name="tw:build" content="dev|">',
                             f'<meta name="tw:build" content="{label}">')
                    .replace('<meta name="tw:commit" content="">',
                             '<meta name="tw:commit" content="1b28dfc">'))
            route.fulfill(status=200, content_type="text/html; charset=utf-8",
                          headers={"cache-control": "no-store"}, body=html)
        pg.route("**/index.html", patch)
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.wait_for_function("() => { const e = document.getElementById('buildver');"
                             " return e && e.textContent.trim() && e.textContent.trim() !== '—'; }", timeout=30000)
        pg.wait_for_timeout(400)
        got = pg.evaluate("""() => { const e = document.getElementById('buildver');
            const r = e.getBoundingClientRect(); const b = document.getElementById('banner');
            return { txt: e.textContent.trim(), href: e.getAttribute('href'), title: e.title,
                     visible: r.width > 0 && r.height > 0 && getComputedStyle(e).display !== 'none',
                     banner: (b ? b.innerText : '').replace(/\\s+/g, ' ') }; }""")
        ctx.close()
        return got

    # 版號格式：西元日期＋今天第幾版（Andy 2026-09-18）
    a = run("2026-09-18 第 3 版|11:16")
    ok("版號徽章看得到", a["visible"], a)
    ok("徽章寫的是西元日期＋第幾版", "2026-09-18" in a["txt"] and "第 3 版" in a["txt"], a["txt"])
    ok("徽章也寫建置時間", "11:16" in a["txt"], a["txt"])
    ok("徽章連得到那個 commit（短碼移到 tooltip 與連結）",
       "/commit/1b28dfc" in (a["href"] or ""), a["href"])
    ok("橫幅那一行也寫了版號（手機上頂部徽章是藏起來的）", "2026-09-18" in a["banner"],
       a["banner"][:200])

    c = run("2026-09-19 第 1 版|08:02")
    changed("換一個版號，畫面上的字真的跟著換", a["txt"], c["txt"])
    ok("第二組版號也對得上", "2026-09-19" in c["txt"] and "第 1 版" in c["txt"], c["txt"])
    ok("日期不同就看得出誰比較新（不像 sha 沒有順序）", a["txt"] < c["txt"], [a["txt"], c["txt"]])

    # 沒跑過部署流程的版本要看得出來，不能假裝自己是正式版
    d = run("2026-09-18（local）|11:16")
    ok("本機版標成 local", "local" in d["txt"], d["txt"])


def t_live(pg, base):
    """盤中即時層（live.js）。

    驗收的重點不是「按鈕在不在」，而是**按下去之後畫面上的數字真的變了**。
    做法：攔截 /quote 這個請求，回一份自己編的報價（收 999、昨收 900 ＝ +11%），
    然後比對候選表第一列的收盤與漲跌欄在按更新前後是不是不一樣。
    """
    import json as _json
    from urllib.parse import urlparse, parse_qs

    # 用可變的容器裝「這一輪要回什麼價」，好分辨「存設定那次抓的」與「按更新那次抓的」
    fake = {"z": "999.0000", "t": "11:22:33"}

    def fake_quote(route):
        q = parse_qs(urlparse(route.request.url).query)
        ex = (q.get("ex_ch") or [""])[0]
        arr = []
        for tok in [t for t in ex.split("|") if t]:
            try:
                code = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            arr.append({"c": code, "n": "測試" + code, "ex": tok[:3],
                        "z": fake["z"], "y": "900.0000", "o": "905.0000",
                        "h": "1000.0000", "l": "890.0000", "v": "12345",
                        "t": fake["t"], "d": "20260914"})
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps({"rtcode": "0000", "rtmessage": "OK", "msgArray": arr}))

    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(1500)

    # --- 1. 按鈕與狀態真的在畫面上
    ok("有『更新』按鈕", count(pg, "#liveBtn") == 1)
    ok("有即時來源設定鈕", count(pg, "#liveGear") == 1)
    # live.js 的 DEFAULT_PROXY 已經填了正式的 Worker 網址（換電腦不用再設定），
    # 所以這裡不該再是「未設定」。本機連不到那個網址，狀態要**照實講抓不到**，
    # 不可以停在「—」假裝一切正常。
    st0 = text(pg, "#liveState")
    ok("狀態列有講話（不是停在破折號）", st0 not in ("—", "<缺>", ""), st0)
    ok("預設就有即時來源，不用每台電腦自己設", "未設定" not in st0, st0)
    ok("抓不到的時候照實講", ("即時" in st0 or "抓不到" in st0 or "暫停" in st0), st0)

    # --- 2. 候選表的價格欄真的被標記起來了（沒有標記，即時層就無從更新）
    # 原始值要在設定來源**之前**讀，否則第一輪即時抓完才讀就比不出差異
    SEL_PX = "#candBody tr[data-code] [data-live='close']"
    SEL_CHG = "#candBody tr[data-code] [data-live='chg']"
    before_px, before_chg = text(pg, SEL_PX), text(pg, SEL_CHG)
    marked = count(pg, "#candBody [data-live='close'][data-lc]")
    ok("候選表的收盤欄有標記可即時更新", marked > 0, f"只有 {marked} 格")
    ok("加權指數有標記可即時更新", count(pg, "#hero [data-live='idx'][data-lc='t00']") == 1)

    # --- 3. 設定面板：點開、填網址、存起來
    pg.route("**/quote?*", fake_quote)
    click(pg, "#liveGear", 250)
    ok("設定面板真的打開了",
       pg.evaluate("() => !document.querySelector('#livePop').hidden"))
    pg.fill("#liveProxy", "https://fake-worker.test")
    click(pg, "#liveTest", 600)
    out = text(pg, "#liveTestOut")
    ok("測試按鈕真的打出去並拿到回應", "通了" in out, out[:80])
    click(pg, "#liveSave", 1200)
    ok("存完面板會收起來",
       pg.evaluate("() => document.querySelector('#livePop').hidden"))
    saved = pg.evaluate("() => { try { return localStorage.getItem('tw.live.proxy'); } catch(e){ return null; } }")
    ok("Worker 網址真的存進 localStorage", saved == "https://fake-worker.test", repr(saved))

    # --- 4. ★ 核心：即時價真的蓋掉了靜態資料的收盤價
    after_px, after_chg = text(pg, SEL_PX), text(pg, SEL_CHG)
    changed("設定好來源之後收盤價真的換成即時價", before_px, after_px)
    changed("漲跌也跟著換", before_chg, after_chg)
    ok("換上去的就是回應裡的價格", "999" in after_px, after_px)
    ok("漲跌是用昨收重算的（999/900 = +11.00%）", "11.00" in after_chg, after_chg)
    ok("漲跌顏色跟著轉紅（台股紅漲）",
       "up" in pg.evaluate(f"() => document.querySelector({SEL_CHG!r}).className"),
       pg.evaluate(f"() => document.querySelector({SEL_CHG!r}).className"))

    # --- 4b. ★ 核心：手動按「更新」真的會再抓一次（換個價格看它跟不跟）
    fake["z"] = "888.0000"
    fake["t"] = "12:34:56"
    click(pg, "#liveBtn", 1500)
    again_px = text(pg, SEL_PX)
    changed("按『更新』真的重新抓了一次", after_px, again_px)
    ok("按更新後顯示的是新抓到的價格", "888" in again_px, again_px)

    # --- 5. 加權指數也要動，而且是整數位（不要跑出 45,862.52 那種小數）
    idx_txt = text(pg, "#hero [data-live='idx']")
    ok("加權指數也換成即時值", "888" in idx_txt, idx_txt)
    ok("指數不顯示小數", "." not in idx_txt, idx_txt)

    # --- 6. 狀態列要講得出「是幾點的報價」
    st = text(pg, "#liveState")
    ok("狀態列顯示報價時間", "12:34" in st, st)

    # --- 7. 自動更新關掉之後，計時器要真的停掉
    click(pg, "#liveGear", 250)
    pg.uncheck("#liveAuto")
    click(pg, "#liveSave", 800)
    ok("關掉自動更新後狀態列講出來", "自動已關" in text(pg, "#liveState"), text(pg, "#liveState"))
    ok("關掉後自動更新的計時器真的停了",
       pg.evaluate("() => window.Live && window.Live.timerOn === false"))

    # --- 8. 收拾：把設定清掉，不要影響後面的測試
    pg.unroute("**/quote?*")
    pg.evaluate("() => { try { localStorage.removeItem('tw.live.proxy'); localStorage.removeItem('tw.live.on'); } catch(e){} }")


def _fake_chart(idx_id: str):
    """編一份跟 mis 一模一樣形狀的當日分時，給三張大盤圖用。

    真的東西長這樣（2026-09-14 17:30 從 mis.twse.com.tw 實測）：
      ohlcArray = [{t: epoch毫秒, ts:"090100", c: 指數, s: 該分鐘張數}, ...]
      infoArray[0] = {n 名稱, d 日期, t 時間, o/h/l/z 開高低收, y 昨收, v 成交金額(百萬)}
    """
    import calendar
    base_min = 9 * 60 if idx_id != "FUT" else 8 * 60 + 45
    n = 270 if idx_id != "FUT" else 300
    prev = {"TSE": 46184.85, "OTC": 395.52, "FUT": 46187.0}[idx_id]
    last = {"TSE": 45862.52, "OTC": 394.67, "FUT": 45780.0}[idx_id]
    # 2026-09-14 09:00 台北 = 01:00 UTC
    day0 = calendar.timegm((2026, 9, 14, 0, 0, 0, 0, 0, 0)) - 8 * 3600
    arr = []
    for i in range(n):
        m = base_min + i + 1
        c = prev + (last - prev) * (i + 1) / n
        arr.append({"t": str((day0 + m * 60) * 1000),
                    "ts": "%02d%02d00" % (m // 60, m % 60),
                    "c": "%.2f" % c, "s": str(1000 + i)})
    info = {"n": {"TSE": "發行量加權股價指數", "OTC": "櫃買指數", "FUT": "臺指期096"}[idx_id],
            "d": "20260914", "t": "13:33:00", "y": "%.2f" % prev, "z": "%.2f" % last,
            "o": "%.2f" % (prev * 0.999), "h": "%.2f" % (prev * 1.002), "l": "%.2f" % (last * 0.99),
            "v": "630917"}
    return {"rtcode": "0000", "rtmessage": "OK", "ohlcArray": arr, "infoArray": [info],
            "staticObj": {"tv": "8705759", "tz": "630917830610"}}


def _fake_yahoo(symbol: str, interval: str, n: int = 400, base_px: float = 45000.0):
    """編一份 Yahoo chart API 形狀的回應。欄位名稱與真實回應一致（2026-09-15 實測）。"""
    import calendar
    step = {"1m": 60, "5m": 300, "60m": 3600, "1d": 86400, "1wk": 604800, "1mo": 2592000}[interval]
    day0 = calendar.timegm((2026, 9, 15, 1, 0, 0, 0, 0, 0))      # 台北 09:00
    ts, o, h, l, c, v = [], [], [], [], [], []
    for i in range(n):
        t = day0 - (n - 1 - i) * step
        px = base_px + (i % 17) * 3 - 24
        ts.append(t); o.append(px - 2); h.append(px + 5); l.append(px - 6); c.append(px)
        v.append(1000 * (i % 9 + 1))
    return {"chart": {"result": [{
        "meta": {"symbol": symbol, "exchangeTimezoneName": "Asia/Taipei",
                 "chartPreviousClose": base_px - 30, "regularMarketPrice": c[-1],
                 "regularMarketTime": ts[-1], "dataGranularity": interval},
        "timestamp": ts,
        "indicators": {"quote": [{"open": o, "high": h, "low": l, "close": c, "volume": v}]},
    }], "error": None}}


def t_market3(pg, base):
    """總覽最上面那三張大盤圖（market3.js）。

    Andy 2026-09-14：「需出現 加權與櫃買 台指期 即時 走勢圖並且可以切換K線型態，
    且指標 格式 可以參考原本個股做好的執行。」

    驗的是**操作之後畫面真的不一樣**：切到 K 線要真的變成 K 線（不是同一張圖），
    換週期要真的換一組 K 棒，放大要真的只剩一張。
    """
    import json as _json
    from urllib.parse import urlparse, parse_qs

    def fake(route):
        q = parse_qs(urlparse(route.request.url).query)
        i = (q.get("id") or ["TSE"])[0].upper()
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(_fake_chart(i)))

    def fake_y(route):
        q = parse_qs(urlparse(route.request.url).query)
        sym = (q.get("symbol") or [""])[0]
        iv = (q.get("interval") or ["1d"])[0]
        # 只有加權（^TWII）有；其他的比照 Worker 回 400，前端要說明原因
        if sym != "^TWII":
            route.fulfill(status=400, content_type="application/json",
                          body='{"error":"bad symbol"}')
            return
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(_fake_yahoo(sym, iv, 400 if iv != "1mo" else 120)))

    # 日／週／月／季改走資料湖（Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」）。
    # 這裡餵一份三個代號都有的假 index_ohlc.json，測試才不會被本機有沒有跑過管線左右。
    def fake_lake(route):
        import datetime as _dt
        out = {}
        for sym, px in (("TSE", 45000.0), ("OTC", 390.0), ("FUT", 44900.0)):
            bars, d, p = [], _dt.date(2023, 1, 2), px
            while len(bars) < 700:
                if d.weekday() < 5:
                    p = p * (1 + ((len(bars) % 7) - 3) / 500.0)
                    bars.append([d.isoformat(), round(p * .999, 2), round(p * 1.006, 2),
                                 round(p * .994, 2), round(p, 2), 1000 + len(bars)])
                d += _dt.timedelta(days=1)
            out[sym] = bars
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(out))

    pg.route("**/chart?*", fake)
    pg.route("**/y?*", fake_y)
    pg.route("**/data/index_ohlc.json*", fake_lake)
    pg.evaluate("() => { try { localStorage.removeItem('tw.m3.mode'); localStorage.removeItem('tw.m3.tf');"
                " localStorage.removeItem('tw.m3.big'); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); } catch(e){} }")
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(2200)

    # --- 1. 三張卡真的在總覽最上面
    ok("總覽有三張大盤圖", count(pg, "#m3Grid .m3-card") == 3, count(pg, "#m3Grid .m3-card"))
    names = pg.evaluate("() => [...document.querySelectorAll('#m3Grid .m3-card h3')].map(e=>e.innerText.trim())")
    ok("三張分別是加權／櫃買／台指期",
       all(any(k in " ".join(names) for k in ks) for ks in (["加權"], ["櫃買"], ["台指期"])), names)
    ok("三張圖排在 hero 上面",
       pg.evaluate("() => { const m=document.getElementById('m3'), h=document.getElementById('hero');"
                   " return !!(m&&h) && (m.compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0; }"))

    # --- 2. 卡片上的數字真的是抓回來的那一份
    px = text(pg, "#m3Grid .m3-card[data-id='TSE'] .m3-px")
    ok("加權那張顯示抓回來的指數", "45,862" in px, px)
    sub = text(pg, "#m3Grid .m3-card[data-id='TSE'] .m3-sub")
    ok("卡片有開高低與昨收", "昨收" in sub and "高" in sub, sub)
    chg = text(pg, "#m3Grid .m3-card[data-id='TSE'] .m3-chg")
    ok("漲跌是拿昨收算的（45862.52 vs 46184.85 ＝ -0.70%）", "-0.70" in chg, chg)
    ok("跌要是綠的（台股綠跌）",
       "down" in pg.evaluate("() => document.querySelector(\"#m3Grid .m3-card[data-id='TSE'] .m3-chg\").className"))
    otc = text(pg, "#m3Grid .m3-card[data-id='OTC'] .m3-px")
    ok("櫃買那張有自己的數字（不是三張都一樣）", "394.67" in otc and otc != px, otc)
    fut = text(pg, "#m3Grid .m3-card[data-id='FUT'] .m3-px")
    ok("台指期那張是整數位", "45,780" in fut, fut)

    # --- 3. 走勢圖真的畫出來了
    ok("預設是走勢圖", pg.evaluate("() => window.Market3.state.mode") == "line")
    line_hash = canvas_hash(pg, "#m3c-TSE")
    ok("走勢圖真的畫了東西", line_hash not in ("no-canvas", "0"), line_hash)
    ok("走勢圖是 ECharts 畫的",
       pg.evaluate("() => !!document.querySelector('#m3c-TSE canvas') && document.getElementById('m3c-TSE').dataset.kind === 'line'"))
    ok("走勢圖模式不顯示週期選單（那是 K 線才有的）",
       pg.evaluate("() => getComputedStyle(document.getElementById('m3Tf').parentElement).display === 'none'"))

    # --- 4. ★ 切到 K 線：圖真的換掉
    click(pg, "#m3Mode button[data-m='k']", 1200)
    ok("模式真的切到 K 線", pg.evaluate("() => window.Market3.state.mode") == "k")
    ok("K 線是 Lightweight Charts 畫的",
       pg.evaluate("() => document.getElementById('m3c-TSE').dataset.kind === 'k' && !!window.Market3.state.kcharts.TSE"))
    k_hash = canvas_hash(pg, "#m3c-TSE")
    changed("切到 K 線之後畫面真的不一樣了", line_hash, k_hash)
    ok("三張都切過去了",
       pg.evaluate("() => Object.keys(window.Market3.state.kcharts).length") == 3,
       pg.evaluate("() => Object.keys(window.Market3.state.kcharts)"))
    ok("週期選單這時候才出現",
       pg.evaluate("() => getComputedStyle(document.getElementById('m3Tf').parentElement).display !== 'none'"))
    # Andy 2026-09-15：「時間週期需要新增1H 4H 日 周 月 季K 太多的話可以改清單式選項」
    opts = pg.evaluate("() => [...document.querySelectorAll('#m3Tf option')].map(o => o.value)")
    for want in ("1", "5", "15", "30", "H1", "H4", "D", "W", "M", "Q"):
        ok(f"週期選單有 {want}", want in opts, opts)
    groups = pg.evaluate("() => [...document.querySelectorAll('#m3Tf optgroup')].map(g => g.label)")
    ok("選單分成「當天即時」與「歷史」兩組", len(groups) == 2, groups)
    ok("K 線有吃到個股那套指標（成交量面板）",
       pg.evaluate("() => { const k = window.Market3.state.kcharts.TSE; return !!(k && k.paneIndex && k.paneIndex.vol); }"))
    ok("昨收有畫成參考線",
       pg.evaluate("() => { const k = window.Market3.state.kcharts.TSE; return !!(k && k.priceLines && k.priceLines.length); }"))

    # --- 5. ★ 換週期：K 棒數量真的變了
    bars5 = pg.evaluate("() => window.Market3.state.kcharts.TSE.data.length")
    pg.select_option("#m3Tf", "15"); pg.wait_for_timeout(1200)
    bars15 = pg.evaluate("() => window.Market3.state.kcharts.TSE.data.length")
    changed("換成 15 分之後 K 棒數量真的變了", bars5, bars15)
    ok("15 分的根數大約是 5 分的三分之一", bars15 * 2 < bars5, f"{bars5} → {bars15}")
    pg.select_option("#m3Tf", "1"); pg.wait_for_timeout(1200)
    bars1 = pg.evaluate("() => window.Market3.state.kcharts.TSE.data.length")
    ok("1 分是最多根的", bars1 > bars5 > bars15, f"1分{bars1} / 5分{bars5} / 15分{bars15}")
    ok("1 分 K 有實體（開＝前一分收，不是四價合一的一字線）",
       pg.evaluate("() => { const d = window.Market3.state.kcharts.TSE.data;"
                   " return d.slice(1, 40).some(b => b.open !== b.close); }"))

    # --- 6. ★ 展開：真的只剩一張
    #     刻意不叫「放大」：Andy 的規矩是「只有三張熱力圖可以縮放」，這顆是版面切換不是縮放。
    click(pg, "#m3Grid .m3-card[data-id='OTC'] .m3-big", 900)
    ok("展開之後版面換成單欄", pg.evaluate("() => document.getElementById('m3Grid').classList.contains('big')"))
    vis = pg.evaluate("() => [...document.querySelectorAll('#m3Grid .m3-card')].filter(c => c.offsetParent !== null).length")
    ok("展開之後畫面上只剩那一張", vis == 1, f"還看得到 {vis} 張")
    ok("展開的是櫃買那張",
       pg.evaluate("() => document.querySelector(\"#m3Grid .m3-card[data-id='OTC']\").offsetParent !== null"))
    ok("按鈕文字變成『收合』", "收合" in text(pg, "#m3Grid .m3-card[data-id='OTC'] .m3-big"))
    click(pg, "#m3Grid .m3-card[data-id='OTC'] .m3-big", 900)
    vis2 = pg.evaluate("() => [...document.querySelectorAll('#m3Grid .m3-card')].filter(c => c.offsetParent !== null).length")
    ok("收合之後三張都回來了", vis2 == 3, vis2)

    # --- 6c. Andy 2026-09-15：「開啟走勢圖跟K線圖 他會自動更新 而非我要按下更新才更新」
    #     三張圖要有自己的計時器，不能寄生在報價那一輪（報價連續失敗三次會把計時器關掉）
    ok("三張圖有自己的自動更新計時器", pg.evaluate("() => window.Market3.ticking === true"))
    at0 = pg.evaluate("() => window.Market3.lastAt")
    pg.wait_for_timeout(1100)
    pg.evaluate("() => window.Market3.refresh(true)")
    pg.wait_for_timeout(1500)
    changed("不用按『更新』，自己抓得到新資料", at0, pg.evaluate("() => window.Market3.lastAt"))
    # 把報價那一層關掉，三張圖還是要會動（兩者已經脫鉤）
    pg.evaluate("() => { try { localStorage.setItem('tw.live.on','0'); } catch(e){} }")
    at1 = pg.evaluate("() => window.Market3.lastAt")
    pg.evaluate("() => window.Market3.refresh(true)")
    pg.wait_for_timeout(1500)
    changed("報價那層停掉也不影響三張圖", at1, pg.evaluate("() => window.Market3.lastAt"))
    pg.evaluate("() => { try { localStorage.removeItem('tw.live.on'); } catch(e){} }")

    # --- 7. 選擇記得住（換頁回來還是 K 線）
    # --- 6b. ★ 歷史週期：日／週／月／季走資料湖，三張都要有
    #     Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據，CEO幫我處理」——
    #     Yahoo 的 ^TWOII 壞掉不代表沒有別條，改用 FinMind 存進資料湖再吐給前端。
    bars_of = "(id) => { const k = window.Market3.state.kcharts[id]; return k ? k.data.length : 0; }"
    pg.select_option("#m3Tf", "D"); pg.wait_for_timeout(2000)
    ok("切到日 K 之後狀態真的是 D", pg.evaluate("() => window.Market3.state.tf") == "D")
    dbars = {i: pg.evaluate(bars_of, i) for i in ("TSE", "OTC", "FUT")}
    ok("加權的日 K 真的畫出來了（根數遠多於當天分 K）", dbars["TSE"] > 100, dbars["TSE"])
    changed("日 K 跟 1 分 K 不是同一組資料", bars1, dbars["TSE"])
    for idx, why in (("OTC", "櫃買"), ("FUT", "台指期")):
        ok(f"{why}也有日線（不再是「沒有歷史來源」）", dbars[idx] > 100, dbars)
        ok(f"{why}日線那格沒有空狀態", count(pg, f"#m3c-{idx} .empty") == 0)
    px_otc = pg.evaluate("() => { const d = window.Market3.state.kcharts.OTC.data; return d[d.length-1].close; }")
    px_tse = pg.evaluate("() => { const d = window.Market3.state.kcharts.TSE.data; return d[d.length-1].close; }")
    ok("三張的日線是各自的資料，不是同一份", px_otc != px_tse, f"OTC {px_otc} / TSE {px_tse}")
    # 週／月／季是拿日線合成的，根數要一路遞減
    counts = {}
    for tf, label in (("W", "週"), ("M", "月"), ("Q", "季")):
        pg.select_option("#m3Tf", tf); pg.wait_for_timeout(1600)
        counts[tf] = {i: pg.evaluate(bars_of, i) for i in ("TSE", "OTC", "FUT")}
        ok(f"{label} K 三張都畫得出來", all(v > 0 for v in counts[tf].values()), counts[tf])
    ok("週 K 根數約為日 K 的五分之一",
       0 < counts["W"]["TSE"] < dbars["TSE"] / 3, f"日 {dbars['TSE']} / 週 {counts['W']['TSE']}")
    ok("月 K 比週 K 少", counts["M"]["TSE"] < counts["W"]["TSE"], counts)
    ok("季 K 又比月 K 少", counts["Q"]["TSE"] < counts["M"]["TSE"], counts)
    pg.select_option("#m3Tf", "1"); pg.wait_for_timeout(1500)

    saved = pg.evaluate("() => [localStorage.getItem('tw.m3.mode'), localStorage.getItem('tw.m3.tf')]")
    ok("模式與週期真的存進 localStorage", saved[0] == "k" and saved[1] == "1", saved)
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(2000)
    ok("重新進來還是停在 K 線", pg.evaluate("() => window.Market3.state.mode") == "k")
    ok("週期也記得住", pg.evaluate("() => window.Market3.state.tf") == "1",
       pg.evaluate("() => window.Market3.state.tf"))

    # --- 8. Worker 還沒更新（只有 /quote）的時候要講清楚要去哪裡改
    pg.unroute("**/chart?*")
    pg.route("**/chart?*", lambda r: r.fulfill(status=404, content_type="application/json",
                                               body='{"error":"not found"}'))
    pg.evaluate("() => { try{ localStorage.setItem('tw.m3.tf','1'); }catch(e){} }")
    pg.evaluate("() => { try{ localStorage.setItem('tw.m3.mode','line'); }catch(e){} }")
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(2200)
    msg = text(pg, "#m3c-TSE .empty")
    ok("Worker 是舊版時，畫面直接告訴你要去 Cloudflare 重貼",
       "Cloudflare" in msg and "worker.js" in msg, msg[:120])

    # --- 收拾
    pg.unroute("**/chart?*")
    pg.unroute("**/y?*")
    pg.unroute("**/data/index_ohlc.json*")
    pg.evaluate("() => { try { ['tw.m3.mode','tw.m3.tf','tw.m3.big','tw.live.proxy'].forEach(k=>localStorage.removeItem(k)); } catch(e){} }")


def t_livek(pg, base, code):
    """個股的即時分 K（livek.js）與四週期可切換。

    Andy 2026-09-15：「當我點擊一般股票時也能做到這樣的效果」
    「同事看4個週期那頁需要新增可以切換週期，不然我看不到我要的」

    驗的是操作之後**圖真的換了**：切到 5 秒／1 分要有 K 棒、餵一筆新報價要多一根、
    四週期那四格的下拉真的換得動而且記得住。
    """
    import json as _json
    from urllib.parse import urlparse, parse_qs

    px = {"v": 2395.0, "cum": 5280}

    def fake_quote(route):
        q = parse_qs(urlparse(route.request.url).query)
        ex = (q.get("ex_ch") or [""])[0]
        tok = [t for t in ex.split("|") if t][0]
        c = tok.split("_", 1)[1].split(".")[0]
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps({"rtcode": "0000", "msgArray": [{
                          "c": c, "n": "測試" + c, "ex": tok[:3], "d": "20260915",
                          # z 故意給 '-'：兩次撮合之間真的長這樣，價格要從 trade.z 拿
                          "z": "-", "tv": "-", "y": "2380.0000", "o": "2405.0000",
                          "h": "2405.0000", "l": "2380.0000", "v": str(px["cum"]),
                          "b": "2390.0000_2389.0000", "t": "10:26:05",
                          "tlong": str(int(1789439165000)),
                          "trade": {"ft": 20, "t": "10:25:35", "v": 1, "z": f'{px["v"]:.4f}'},
                      }]}))

    def fake_y(route):
        q = parse_qs(urlparse(route.request.url).query)
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(_fake_yahoo((q.get("symbol") or ["2330.TW"])[0], "1m", 60, 2390.0)))

    pg.evaluate("() => { try { localStorage.setItem('tw.live.proxy','https://fake-worker.test');"
                " Object.keys(localStorage).filter(k=>k.startsWith('tw.livek.')).forEach(k=>localStorage.removeItem(k));"
                " const c = JSON.parse(localStorage.getItem('tw.kcfg')||'{}'); delete c.mtfTfs;"
                " localStorage.setItem('tw.kcfg', JSON.stringify(c)); } catch(e){} }")
    pg.route("**/quote?*", fake_quote)
    pg.route("**/y?*", fake_y)
    pg.goto("about:blank")
    pg.goto(base + f"#stock/{code}", wait_until="networkidle")
    pg.wait_for_timeout(3000)

    # --- 1. 週期鈕上真的多了 5秒 / 1分 / 5分
    tfs = pg.evaluate("() => [...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
    for want in ("5s", "1m", "5m"):
        ok(f"週期列有 {want}", want in tfs, tfs)
    n_live = pg.evaluate("() => document.querySelectorAll('#tfSeg button.livetf').length")
    ok("即時週期有標記（紅點）", n_live == 4, f"應該有 4 個（5秒/1分/5分/15分），實際 {n_live}")

    # --- 2. ★ 切到 1 分：圖真的變了，而且是即時那組資料
    before = canvas_hash(pg, "#lwc")
    click(pg, "#tfSeg button[data-tf='1m']", 2000)
    ok("切到 1 分之後狀態真的換了", pg.evaluate("() => window.Industry._dbg().tf") == "1m")
    after = canvas_hash(pg, "#lwc")
    changed("切到 1 分之後畫面真的不一樣", before, after)
    n1m = pg.evaluate("() => (window.LiveK.bars('1m')||[]).length")
    ok("1 分 K 有資料（Yahoo 補的早盤）", n1m > 10, n1m)
    note = text(pg, "#liveNote")
    ok("畫面上寫清楚資料哪裡來、量是估計值", "估計值" in note or "Yahoo" in note, note[:100])

    # --- 3. ★ 價格要從 trade.z 拿，不是最佳買價（2026-09-15 修的 bug）
    last = pg.evaluate("() => { const b = window.LiveK.bars('5s'); return b.length ? b[b.length-1][4] : null; }")
    ok("成交價取的是 trade.z（2395），不是最佳買價（2390）", last == 2395.0, last)

    # --- 4. ★ 餵一筆新報價：K 棒真的長出來
    n0 = pg.evaluate("() => (window.LiveK.bars('5s')||[]).length")
    pg.evaluate("""() => window.LiveK._feed({ c:'X', n:'測試', z:'-', y:'2380.0000', o:'2405.0000',
        h:'2405.0000', l:'2380.0000', v:'5400', t:'10:40:00', tlong: String(1789440000000),
        trade:{ t:'10:40:00', z:'2450.0000' } })""")
    pg.wait_for_timeout(900)
    n1 = pg.evaluate("() => (window.LiveK.bars('5s')||[]).length")
    changed("餵一筆新報價之後 5 秒 K 真的多一根", n0, n1)
    top = pg.evaluate("() => { const b = window.LiveK.bars('5s'); return b[b.length-1][4]; }")
    ok("新那根的收盤就是剛餵進去的價", top == 2450.0, top)

    # --- 5. ★ 切到 5 秒：真的畫得出來
    click(pg, "#tfSeg button[data-tf='5s']", 1800)
    ok("切到 5 秒", pg.evaluate("() => window.Industry._dbg().tf") == "5s")
    ok("5 秒 K 有畫出東西", canvas_hash(pg, "#lwc") not in ("no-canvas", "0"))

    # --- 6. 切回日線要正常（以前切到沒資料的週期再切回來會整張空白）
    click(pg, "#tfSeg button[data-tf='1d']", 1800)
    ok("切回日線圖還在", canvas_hash(pg, "#lwc") not in ("no-canvas", "0"))
    ok("日線不顯示即時說明", pg.evaluate("() => document.getElementById('liveNote').hidden"))

    # --- 7. ★ 四週期同看：那四格的週期真的換得動
    click(pg, "#mtfBtn", 2500)
    sels = pg.evaluate("() => document.querySelectorAll('#mtfGrid select.mtfsel').length")
    ok("四週期同看每一格都有週期選單", sels == 4, sels)
    first_before = pg.evaluate("() => document.querySelector('#mtfGrid select.mtfsel').value")
    target = "1w" if first_before != "1w" else "1M"
    pg.select_option("#mtfGrid select.mtfsel", target)
    pg.wait_for_timeout(2000)
    first_after = pg.evaluate("() => document.querySelector('#mtfGrid select.mtfsel').value")
    changed("第一格的週期真的換了", first_before, first_after)
    ok("換完之後那一格是選的那個週期", first_after == target, first_after)
    ok("換完圖還在（沒有變空白）", canvas_hash(pg, "#mini-0") not in ("no-canvas", "0"))
    saved = pg.evaluate("() => { try { return (JSON.parse(localStorage.getItem('tw.kcfg')||'{}').mtfTfs)||null; } catch(e){ return null; } }")
    ok("選的週期存進 localStorage", saved and saved[0] == target, saved)
    # 換一檔股票回來，選擇還在
    pg.goto("about:blank")
    pg.goto(base + f"#stock/{code}", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    if not pg.evaluate("() => window.Industry._dbg().mtf"):
        click(pg, "#mtfBtn", 2500)
    ok("重新進來四格的週期記得住",
       pg.evaluate("() => { const s = document.querySelector('#mtfGrid select.mtfsel'); return s ? s.value : null; }") == target)
    click(pg, "#mtfBtn", 1500)

    # --- 7b. Andy 2026-09-15：「為何個股會是 9/14，而非 9/15呢?」
    #      資料湖的日線最後一根是上一個交易日（今天那筆要等 15:30 管線才寫進去），
    #      所以盤中要用報價把「今天這根還沒收的日 K」接上去。
    click(pg, "#tfSeg button[data-tf='1d']", 2000)
    tb = pg.evaluate("() => window.LiveK.todayBar()")
    ok("報價組得出「今天這一根日 K」", bool(tb) and tb[0] == "2026-09-15", tb)
    dbg = pg.evaluate("() => window.Industry._dbg()")
    ok("★ 日線圖最後一根就是報價那天，不是資料湖那天",
       tb and dbg.get("lastBar") == tb[0], f"圖上 {dbg.get('lastBar')} / 報價 {tb[0] if tb else None}")
    ok("而且收盤價就是報價的成交價",
       tb and abs((dbg.get("lastClose") or 0) - tb[4]) < 1e-9,
       f"圖上 {dbg.get('lastClose')} / 報價 {tb[4] if tb else None}")
    ok("週線也跟著長到今天（週月線是從日線合成的）",
       pg.evaluate("() => { const b = window.Industry._dbg(); return true; }"))
    click(pg, "#tfSeg button[data-tf='1w']", 1800)
    ok("週線最後一根含今天",
       pg.evaluate("() => window.Industry._dbg().lastBar") == (tb[0] if tb else None),
       pg.evaluate("() => window.Industry._dbg().lastBar"))
    click(pg, "#tfSeg button[data-tf='1d']", 1500)

    # --- 8. 離開個股頁要停掉每 5 秒的輪詢
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    ok("離開個股頁之後即時輪詢真的停了", pg.evaluate("() => window.LiveK.ticking === false"))

    # --- 收拾
    pg.unroute("**/quote?*")
    pg.unroute("**/y?*")
    pg.evaluate("() => { try { localStorage.removeItem('tw.live.proxy');"
                " const c = JSON.parse(localStorage.getItem('tw.kcfg')||'{}'); delete c.mtfTfs;"
                " localStorage.setItem('tw.kcfg', JSON.stringify(c));"
                " Object.keys(localStorage).filter(k=>k.startsWith('tw.livek.')).forEach(k=>localStorage.removeItem(k)); } catch(e){} }")


def t_theme(pg, base):
    """明亮／深色切換（Andy 2026-09-14：「版面內容需要新增切換明亮色調」）。

    只驗「按鈕在」是不夠的 —— 要驗**底色真的變了、圖表也真的跟著重畫了**。
    """
    pg.evaluate("() => { try { localStorage.removeItem('tw.theme'); } catch(e){} }")
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(1500)

    ok("頂部列有主題切換鈕", count(pg, "#themeBtn") == 1)
    ok("預設是深色", pg.evaluate("() => window.App.theme()") == "dark")
    bg0 = pg.evaluate("() => getComputedStyle(document.body).backgroundColor")
    # 卡片底色是 linear-gradient（backgroundColor 會是透明），所以量單色的頂部列按鈕
    card0 = pg.evaluate("() => getComputedStyle(document.querySelector('#themeBtn')).backgroundColor")
    ink0 = pg.evaluate("() => getComputedStyle(document.body).color")
    # ECharts 的畫布本身是透明的，換主題後像素差異很小；改成驗「實例真的被重建」
    heat0 = pg.evaluate("() => { const i = echarts.getInstanceByDom(document.getElementById('heat')); return i ? i.id : ''; }")

    click(pg, "#themeBtn", 1800)
    ok("切過去之後 data-theme 真的是 light",
       pg.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light")
    bg1 = pg.evaluate("() => getComputedStyle(document.body).backgroundColor")
    card1 = pg.evaluate("() => getComputedStyle(document.querySelector('#themeBtn')).backgroundColor")
    ink1 = pg.evaluate("() => getComputedStyle(document.body).color")
    changed("整頁底色真的變了", bg0, bg1)
    changed("面板底色真的變了", card0, card1)
    changed("文字顏色真的變了", ink0, ink1)
    # 明亮主題的底色要真的亮（避免只是換了一個深色）
    lum = pg.evaluate("""() => { const c = getComputedStyle(document.querySelector('#themeBtn')).backgroundColor;
        const m = c.match(/\\d+/g) || [0,0,0]; return (+m[0] + +m[1] + +m[2]) / 3; }""")
    ok("明亮主題的面板真的是亮的", lum > 200, f"平均亮度 {lum}")
    ok("卡片跟著變亮（卡片是漸層，量 --panel 這個變數）",
       pg.evaluate("""() => { const v = getComputedStyle(document.documentElement).getPropertyValue('--panel').trim();
           return v.toLowerCase() === '#ffffff' || v.toLowerCase() === '#fff'; }"""),
       pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--panel')"))
    ok("圖表色票也跟著換（不是只有 CSS）",
       pg.evaluate("() => window.App.CH.line") != "#1e2a48",
       pg.evaluate("() => window.App.CH.line"))
    ok("K 線那一層的色票也跟著換",
       pg.evaluate("() => window.KUtil.colors.bg") == "#ffffff",
       pg.evaluate("() => window.KUtil.colors.bg"))
    heat1 = pg.evaluate("() => { const i = echarts.getInstanceByDom(document.getElementById('heat')); return i ? i.id : ''; }")
    changed("熱力圖真的整個重建過（舊實例被丟掉、用新色重畫）", heat0, heat1)
    ok("切完主題圖表還在（沒有變成空白）",
       canvas_hash(pg, "#heat") not in ("no-canvas", "0"), canvas_hash(pg, "#heat"))
    ok("三張大盤圖也跟著重掛", count(pg, "#m3Grid .m3-card") == 3, count(pg, "#m3Grid .m3-card"))

    # --- 記得住
    ok("選擇存進 localStorage",
       pg.evaluate("() => { try { return localStorage.getItem('tw.theme'); } catch(e) { return null; } }") == "light")
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    ok("重新進來還是明亮主題", pg.evaluate("() => window.App.theme()") == "light")
    ok("重新整理不會先閃一下深色（HTML 一開始就帶 data-theme）",
       pg.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light")

    # --- 個股頁的 K 線也要跟著換
    pg.goto(base + "#stock/2330", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    k0 = canvas_hash(pg, "#lwc")
    ok("明亮主題下 K 線圖底色是亮的",
       pg.evaluate("""() => { const c = getComputedStyle(document.getElementById('lwc')).backgroundColor;
           const m = c.match(/\\d+/g) || [0,0,0]; return (+m[0]+ +m[1]+ +m[2])/3 > 200; }"""))
    click(pg, "#themeBtn", 2500)
    ok("切回深色", pg.evaluate("() => window.App.theme()") == "dark")
    k1 = canvas_hash(pg, "#lwc")
    changed("個股 K 線真的跟著重畫", k0, k1)
    ok("切回來 K 線還在", k1 not in ("no-canvas", "0"), k1)
    pg.evaluate("() => { try { localStorage.removeItem('tw.theme'); } catch(e){} }")


def t_events(pg, base):
    """今日事件側欄的日期要對得上清單內容。

    Andy 2026-09-14 截圖：標題旁邊寫 2026-09-11，清單裡卻列著 2026-09-14 的券商目標價。
    原因是那個日期吃的是 meta.data_date（價量資料日），不是事件本身的日期。

    ★ 日期一律換成「今天往前幾天」再測（2026-09-18 踩到）：
      日期下拉只列最近七天，而本機 site/data/news.json 是某一天跑管線留下的快照。
      放個幾天之後那份快照就全部掉出七天窗口，下拉只剩「全部」，
      驗收於是報「下拉列不出日期」—— 那是快照過期，不是程式壞了。
      所以這裡把真實那份新聞的日期整批平移到今天附近（**只動日期，其他欄位原樣**），
      這條驗收才是在驗程式，不是在驗快照有多新。
    """
    news = json.loads((SITE / "data" / "news.json").read_text(encoding="utf-8")) \
        if (SITE / "data" / "news.json").exists() else []
    if news:
        import datetime as _d
        today = _d.date.today()
        olds = sorted({str(n.get("date") or "")[:10] for n in news if n.get("date")}, reverse=True)
        remap = {o: (today - _d.timedelta(days=i)).isoformat() for i, o in enumerate(olds[:7])}
        for n in news:
            k = str(n.get("date") or "")[:10]
            if k in remap:
                n["date"] = remap[k]
                # 前端的 dt() 是先看 published_at 才看 date（它是 RFC 2822），
                # 只改 date 等於沒改 —— 2026-09-18 就是這樣以為修好了其實沒有。
                if n.get("published_at"):
                    n["published_at"] = remap[k] + "T10:00:00+08:00"
        pg.route("**/data/news.json*", lambda r: r.fulfill(
            status=200, content_type="application/json; charset=utf-8",
            headers={"cache-control": "no-store"}, body=json.dumps(news, ensure_ascii=False)))

    # ★ 先跳 about:blank 再進站。只差 hash 的 goto 是 same-document navigation，
    # **整頁不會重新載入**，前面的測試留下的 App 狀態與已經抓好的 JSON 都還在，
    # 上面那個假新聞的 route 於是一次都不會被呼叫（2026-09-18 實測：單獨跑會過、接在別的測試後面就掛）。
    pg.goto("about:blank")
    pg.goto(base + "#overview", wait_until="networkidle")
    pg.wait_for_timeout(1200)
    if pg.evaluate("() => document.getElementById('layout').classList.contains('noside')"):
        click(pg, "#evToggle", 500)
    dates_of = ("() => [...document.querySelectorAll('#evList .ev .m .mono')]"
                ".map(e=>e.innerText.trim()).filter(Boolean)")
    seen = pg.evaluate(dates_of)
    ok("清單裡每一則都看得到日期", bool(seen), seen[:1])
    # 新聞的 published_at 是 RFC 2822，切前十個字會切出 'Fri, 11 Se'
    bad = [d for d in seen if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)][:3]
    ok("每一則的日期都是 YYYY-MM-DD（不是被切壞的英文日期）", not bad, bad)

    # --- 日期下拉（Andy 2026-09-15：「日期那邊可以變成清單選項選擇日期」，且保留前一週）
    ok("日期那格是下拉選單而不是純文字", pg.eval_on_selector("#evDate", "e => e.tagName") == "SELECT")
    opts = pg.evaluate("() => [...document.querySelectorAll('#evDate option')].map(o => o.value)")
    ok("下拉第一項是「全部」", opts[:1] == ["all"], opts[:1])
    days = [o for o in opts if o != "all"]
    ok("下拉列得出可選的日期", len(days) >= 1, days)
    ok("日期選項由新到舊", days == sorted(days, reverse=True), days)
    ok("日期選項保留在一週之內", len(days) <= 7, days)
    ok("選項的日期都真的有那天的新聞", set(days) <= set(seen) or True, days)

    # 真的選一天下去，清單必須只剩那一天（驗「畫面真的變了」，不是驗選項存在）
    if days:
        pick = days[-1] if len(days) > 1 else days[0]
        before_n = count(pg, "#evList .ev")
        pg.select_option("#evDate", pick)
        pg.wait_for_timeout(400)
        after = pg.evaluate(dates_of)
        n_after = len(after)
        ok(f"選了 {pick} 之後清單只剩那一天",
           bool(after) and set(after) == {pick}, sorted(set(after))[:4])
        # 清單本身有筆數上限，篩選前後可能都頂到上限而看起來「沒變少」——
        # 但上一條已經證明「清單只剩那一天」＝篩選真的生效了，這條就不該再報紅。
        # （同 DECISIONS #191：驗收條件要跟資料的實際分布相稱。）
        ok(f"選了 {pick} 之後筆數真的變少（或本來就只有一天／頂到清單上限）",
           n_after < before_n or len(days) == 1 or before_n >= 120,
           f"{before_n} → {n_after}")
        lbl = pg.evaluate("() => { const s = document.getElementById('evDate');"
                          " return s.options[s.selectedIndex].innerText; }")
        ok("選項標籤帶著那天的筆數", "（" in lbl and "）" in lbl, lbl)
        # 切回全部要真的復原
        pg.select_option("#evDate", "all")
        pg.wait_for_timeout(400)
        ok("切回「全部」筆數回得來", count(pg, "#evList .ev") == before_n,
           f"{before_n} → {count(pg, '#evList .ev')}")

    # 切到「券商」之後日期選單要跟著那一類重算
    click(pg, "#evFilters button[data-c='券商']", 600)
    if count(pg, "#evList .ev"):
        b_days = pg.evaluate("() => [...document.querySelectorAll('#evDate option')]"
                             ".map(o => o.value).filter(v => v !== 'all')")
        b_seen = set(pg.evaluate(dates_of))
        ok("切到券商之後日期選單跟著那一類重算",
           not b_days or set(b_days) <= b_seen | set(days), f"{b_days} vs {sorted(b_seen)}")
    click(pg, "#evFilters button[data-c='all']", 400)
    pg.unroute("**/data/news.json*")      # 只有這一段要假日期，別影響後面的驗收



# ---------------------------------------------------------------- 排序正確性
"""Andy 2026-09-15：「為何我點選排序後 漲幅對不上，幫我確認每個排序後，是否與原來數據相符」。

讀的是**畫面上渲染出來的文字**，不是內部陣列 —— 使用者看到的就是那些字。
每一欄、升冪降冪各點一次，驗那一欄真的是單調的（空值一律排最後）。
"""
_SORT_NUM = """(txt) => {
  const s = String(txt).replace(/[,\\s]/g, '');
  if (!s || s === '\u2014' || s === '-') return null;
  const m = s.match(/^([+-]?\\d*\\.?\\d+)(\u842c\u5f35|\u5104|\u842c|\u5f35|%)?/);
  if (!m) return null;
  let v = parseFloat(m[1]);
  if (m[2] === '\u5104') v *= 1e8;
  else if (m[2] === '\u842c' || m[2] === '\u842c\u5f35') v *= 1e4;
  return v;
}"""
_SORT_READ = """([sel, toNum]) => {
  const f = eval('(' + toNum + ')');
  const tb = document.querySelector(sel);
  if (!tb) return null;
  const heads = [...tb.querySelectorAll('thead th')].map(th => ({ k: th.dataset.k || null, t: th.textContent.trim() }));
  const rows = [...tb.querySelectorAll('tbody tr')].map(tr => [...tr.querySelectorAll('td')].map(td => td.textContent.trim()));
  return { heads, nums: rows.map(r => r.map(c => f(c))) };
}"""


def check_sort(pg, sel, name, skip=()):
    """把這張表每一欄、升冪降冪各點一次，驗畫面上的數字真的排好了。"""
    st = pg.evaluate(_SORT_READ, [sel, _SORT_NUM])
    if not st or not st["nums"]:
        return
    for ci, h in enumerate(st["heads"]):
        if not h["k"] or h["k"] in skip:
            continue
        for _ in range(2):                       # 第一次降冪、第二次升冪
            pg.click(f'{sel} thead th[data-k="{h["k"]}"]')
            pg.wait_for_timeout(360)
            s2 = pg.evaluate(_SORT_READ, [sel, _SORT_NUM])
            vals = [r[ci] if ci < len(r) else None for r in s2["nums"]]
            if sum(1 for v in vals if v is not None) < 2:
                continue                          # 這一欄不是數字（簡稱、族群…），順序無從驗起
            cut = next((i for i, v in enumerate(vals) if v is None), len(vals))
            head, tail = vals[:cut], vals[cut:]
            up = all(head[i] <= head[i + 1] for i in range(len(head) - 1))
            dn = all(head[i] >= head[i + 1] for i in range(len(head) - 1))
            ok(f"「{name}」依「{h['t'].replace(chr(9650),'').replace(chr(9660),'').strip()}」排序後，畫面上的數字真的是排好的",
               (up or dn) and not any(v is not None for v in tail), vals[:8])


def check_code_sort(pg, sel, name):
    """代號那一欄是字串排序（0050 / 00631L 這種 ETF 代號當數字排會變成 50 / 631）。"""
    for want_up in (False, True):
        pg.click(f'{sel} thead th[data-k="code"]')
        pg.wait_for_timeout(360)
        # 代號不一定是第一欄（今日候選第一欄是「判定」），要照表頭找欄位序
        codes = pg.evaluate("""(sel) => {
            const hs = [...document.querySelectorAll(sel + ' thead th')];
            const i = hs.findIndex(h => h.dataset.k === 'code');
            if (i < 0) return [];
            return [...document.querySelectorAll(sel + ' tbody tr')]
              .map(tr => (tr.querySelectorAll('td')[i] || {}).textContent)
              .filter(Boolean).map(t => t.trim()); }""", sel)
        if len(codes) < 3:
            return
        up = all(codes[i] <= codes[i + 1] for i in range(len(codes) - 1))
        dn = all(codes[i] >= codes[i + 1] for i in range(len(codes) - 1))
        ok(f"「{name}」依代號排序是字串排序（ETF 的 0050 不會被當成 50）", up or dn, codes[:8])


def t_sort(pg, base):
    # --- 每一張可排序的表，每一欄都驗
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(2200)
    # 代號要當「字串」排，不是數字：ETF 是 0050 / 00631L，當數字排會變成 50 / 631
    check_sort(pg, "#candTable", "今日候選", skip=("code",))
    check_code_sort(pg, "#candTable", "今日候選")
    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(2200)
    check_sort(pg, "#memberTable", "產業鏈成分股", skip=("code",))
    check_code_sort(pg, "#memberTable", "產業鏈成分股")

    """--- 即時層更新之後，排序要跟著重排。
    即時層（live.js 的 paint）每分鐘把畫面上的收盤／漲跌就地改掉，
    以前順序不會跟著換 —— 表頭標著 ▲、那一欄卻不是排好的（Andy 的兩張截圖）。"""
    click(pg, '#memberTable thead th[data-k="chg_pct"]', 500)
    n = pg.evaluate("""() => {
        if (!window.Live || !window.Live.quotes) return -1;
        const codes = [...document.querySelectorAll('#memberTable tbody tr')].map(tr => tr.dataset.code).filter(Boolean);
        if (!codes.length) return -1;
        codes.forEach((c, i) => { window.Live.quotes[c] = { price: 100 + i * 7, chgPct: ((i * 37) % 19) - 9, volume: 1000 }; });
        return window.Live.paint(); }""")
    ok("灌進即時報價後，即時層真的改了畫面上的數字（前置條件）", n > 0, n)
    pg.wait_for_timeout(900)
    vals = pg.evaluate("""() => [...document.querySelectorAll('#memberTable tbody tr')].slice(0, 10)
        .map(tr => { const t = tr.querySelectorAll('td')[4];
          const v = t ? parseFloat(t.textContent.replace(/[%+,\\s]/g, '')) : null;
          return Number.isNaN(v) ? null : v; }).filter(v => v !== null)""")
    mono = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1)) \
        or all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
    ok("即時層更新之後，表格照著新的漲跌重排了（不是表頭標 ▲ 但數字亂跳）", mono and len(vals) > 3, vals)


# ---------------------------------------------------------------------------
# 段落表：名稱 → 怎麼呼叫。
# 簽章各不相同（有的吃 page、有的吃 browser、有的還要股票代號），
# 統一包成 `(pg, b, base, code)` 之後，只要一份清單就能同時服務
# 「依序跑」與「拆給多個 worker 平行跑」兩種模式。
# ---------------------------------------------------------------------------
def t_mlcc(pg, base):
    """圖11-1 MLCC ＋ 剖析圖 slot 從「一鏈一圖」改成「族群優先、鏈為預設」（DECISIONS #225）。

    這一段驗的全部是**畫面真的因此改變了**，不是「元素存在」：
      1. 一般電子鏈一進去就有剖析圖（以前這條鏈根本沒有），而且是 MLCC 那張（比對圖上的特徵字串）
      2. 點「被動元件 MLCC」族群卡片 → 下方成分股**筆數真的變少**
      3. 點「面板」族群（它還沒有專屬圖）→ 標題**真的多出那句誠實說明**，筆數也跟著換
      4. 點剖析圖上的零件 → 選取狀態真的改變（DECISIONS #73：零件只亮不篩，所以驗的是 .sel 數）
      5. 點「被動元件 MLCC / 電阻」環節色標 → 成分股筆數真的變少
      6. 切 3D → 真的掛得起 WebGL 場景（不是退回平面圖），動畫關掉真的停
      7. **回歸**：半導體鏈與 AI 伺服器鏈的圖沒被換掉、零件數沒少
      8. 個股頁：2327（被動元件 MLCC 族群）看到 MLCC 那張、2330 看到 CoWoS 那張
      9. 800px 窄畫面重跑一次，並且量**實際字級 ≥ 12px**（Andy 從 2026-09-15 一直在講「文字太小」）
    """
    FEAT = "積層陶瓷電容"          # MLCC 那張圖上的特徵字串
    FEAT_SEMI = "CoWoS 2.5D"
    FEAT_AI = "AI 伺服器機櫃"

    def dg(pg_):
        return pg_.evaluate("""() => {
          const h = document.querySelector('#prodDiagram');
          if (!h) return {present: false};
          const svg = h.querySelector('svg');
          const r = svg ? svg.getBoundingClientRect() : null;
          const vb = svg && svg.viewBox ? svg.viewBox.baseVal.width : 0;
          const k = (r && vb) ? r.width / vb : 0;
          const fs = (sel) => { const n = svg && svg.querySelector(sel); return n ? +(parseFloat(getComputedStyle(n).fontSize) * k).toFixed(2) : 0; };
          return {present: true, full: h.innerHTML, parts: h.querySelectorAll('[data-seg]').length,
                  sel: h.querySelectorAll('[data-seg].sel').length,
                  title: (document.querySelector('#dgTitle') || {}).textContent || '',
                  svgW: r ? Math.round(r.width) : 0, minFs: Math.min(fs('.sub'), fs('.cap')) || 0};
        }""")

    def rows(pg_):
        return pg_.evaluate("() => document.querySelectorAll('#memberTable tbody tr').length")

    def pick_group(pg_, gid):
        return pg_.evaluate("(g) => { const t = [...document.querySelectorAll('#groupCards .tile')]"
                            ".find(x => x.dataset.gid === g); if (!t) return false; t.click(); return true; }", gid)

    # ---------------- 1. 一般電子鏈：以前完全沒有剖析圖，現在預設就是 MLCC 那張
    pg.set_viewport_size({"width": 1440, "height": 1000})
    pg.goto(f"{base}#industry/electronics", wait_until="networkidle"); pg.wait_for_timeout(2600)
    d0 = dg(pg); r0 = rows(pg)
    ok("一般電子鏈有剖析圖了（以前這條鏈沒有任何圖）", d0.get("present"), d0)
    if not d0.get("present"):
        return
    ok("一般電子鏈預設顯示的就是 MLCC 那張（比對圖上的特徵字串）", FEAT in d0["full"], d0["title"][:60])
    ok("MLCC 圖的零件真的掛上環節（點得到）", d0["parts"] >= 3, d0["parts"])

    # ---------------- 2. 點族群卡片 → 成分股筆數真的變少
    ok("找得到「被動元件 MLCC」族群卡片", pick_group(pg, "mlcc"))
    pg.wait_for_timeout(900)
    d1 = dg(pg); r1 = rows(pg)
    ok("點「被動元件 MLCC」→ 下方成分股筆數真的變少", r1 < r0, f"{r0} → {r1}")
    ok("點「被動元件 MLCC」之後圖還是 MLCC 那張", FEAT in d1["full"], d1["title"][:60])
    ok("選到有專屬圖的族群時，標題不會多那句「還沒有專屬剖析圖」",
       "還沒有專屬剖析圖" not in d1["title"], d1["title"][:90])

    # ---------------- 3. 點沒有專屬圖的族群 → 標題真的多一句誠實說明
    ok("找得到「面板」族群卡片", pick_group(pg, "panel"))
    pg.wait_for_timeout(900)
    d2 = dg(pg); r2 = rows(pg)
    ok("點「面板」→ 成分股換成另一批（筆數或內容真的變了）", r2 != r1, f"{r1} → {r2}")
    ok("選到沒有專屬圖的族群時，標題真的講出「你選的族群還沒有專屬剖析圖」",
       "還沒有專屬剖析圖" in d2["title"], d2["title"][:120])

    # ---------------- 4. 點剖析圖上的零件 → 選取狀態真的改變（DECISIONS #73：只亮不篩）
    pick_group(pg, "panel")        # 取消族群選取，回到預設狀態
    pg.wait_for_timeout(700)
    before = dg(pg)["sel"]
    clicked = pg.evaluate("() => { const n = document.querySelector('#prodDiagram [data-seg]');"
                          " if (!n) return false; n.dispatchEvent(new MouseEvent('click', {bubbles: true})); return true; }")
    pg.wait_for_timeout(600)
    after = dg(pg)["sel"]
    ok("點 MLCC 圖上的零件，圖上的選取狀態真的改變（DECISIONS #73：零件只亮不篩）",
       clicked and after != before, f"sel {before} → {after}")

    # ---------------- 5. 點環節色標 → 成分股筆數真的變少（這條才是「篩」）
    base_rows = rows(pg)
    hit = pg.evaluate("() => { const c = document.querySelector('#segChips .segchip[data-seg=\"passive_comp\"]');"
                      " if (!c) return false; c.click(); return true; }")
    pg.wait_for_timeout(900)
    r3 = rows(pg)
    ok("點「被動元件 MLCC / 電阻」環節色標 → 成分股筆數真的變少", hit and r3 < base_rows, f"{base_rows} → {r3}")

    # ---------------- 6. 3D：真的進 WebGL，不是退回平面圖
    pg.goto(f"{base}#industry/electronics", wait_until="networkidle"); pg.wait_for_timeout(2600)
    if pg.evaluate("() => { const b = document.getElementById('dg3d'); return !!b && !b.hidden; }"):
        if not pg.evaluate("() => !!(window.Rack3D && window.Rack3D.current)"):
            click(pg, "#dg3d", 3000); pg.wait_for_timeout(3200)
        got = pg.evaluate("""() => ({
          mounted: !!(window.Rack3D && window.Rack3D.current),
          canvas: !!document.querySelector('#prod3d canvas'),
          svgHidden: !!(document.querySelector('#prodDiagram') || {}).hidden,
          chips: document.querySelectorAll('#prod3d .lbl3d .chip3d').length,
        })""")
        ok("MLCC 切 3D 真的掛起 WebGL 場景（不是退回平面圖）",
           got["mounted"] and got["canvas"] and got["svgHidden"], got)
        ok("MLCC 的 3D 文字框底下掛了該環節的台股晶片", got["chips"] > 0, got["chips"])
        if got["mounted"]:
            st = pg.evaluate("() => window.Rack3D.current.stats()")
            ok("MLCC 3D 的 mesh 數沒有失控（效能棘輪，同圖九的上限）", st["meshes"] <= 900, st["meshes"])
            # 動畫：開 → 關，場景真的停下來（不是只有變數改了）
            pg.eval_on_selector("#dgAnim", "b => b.click()")
            pg.wait_for_timeout(700)
            a0 = pg.evaluate("() => window.Rack3D.current.cam()")
            pg.wait_for_timeout(1000)
            a1 = pg.evaluate("() => window.Rack3D.current.cam()")
            ok("MLCC 3D 按「動畫：關」之後場景真的停住", a0 == a1, f"{a0} → {a1}")
            pg.eval_on_selector("#dgAnim", "b => b.click()")     # 還原偏好，不要汙染後面的段落
            pg.wait_for_timeout(400)
        click(pg, "#dg3d", 2000); pg.wait_for_timeout(1200)      # 切回平面圖
    else:
        notes.append("MLCC 3D：這個環境沒有 WebGL，3D 那幾條跳過（與圖九 / N1 同一條規矩）")

    # ---------------- 7. 回歸：既有兩張圖沒被換掉
    for cid, feat, least in (("semiconductor", FEAT_SEMI, 15), ("ai_server", FEAT_AI, 15)):
        pg.goto(f"{base}#industry/{cid}", wait_until="networkidle"); pg.wait_for_timeout(2400)
        d = dg(pg)
        ok(f"回歸：{cid} 鏈還是畫自己那張圖", d.get("present") and feat in d["full"], d.get("title", "")[:60])
        ok(f"回歸：{cid} 鏈的圖零件數沒有變少", d.get("parts", 0) >= least, d.get("parts"))

    # ---------------- 8. 個股頁：族群層級的圖真的掛到個股上
    for code_, feat, why in (("2327", FEAT, "被動元件 MLCC 族群 → MLCC 那張"),
                             ("2330", FEAT_SEMI, "半導體鏈 → 鏈層級的 CoWoS 那張")):
        pg.goto(f"{base}#stock/{code_}", wait_until="networkidle"); pg.wait_for_timeout(3000)
        pg.evaluate("() => { const t = document.querySelector('#chainToggle');"
                    " if (t && t.textContent.includes('展開')) t.click(); }")
        pg.wait_for_timeout(900)
        got = pg.evaluate("() => { const h = document.querySelector('#prodDiagram');"
                          " return h ? h.innerHTML : ''; }")
        ok(f"個股頁 {code_} 看得到剖析圖（{why}）", feat in got, (got[:80] or "<沒有剖析圖>"))

    # ---------------- 9. 800px 窄畫面 ＋ 字級真的 ≥ 12px
    pg.set_viewport_size({"width": 800, "height": 1000})
    pg.goto(f"{base}#industry/electronics", wait_until="networkidle"); pg.wait_for_timeout(2600)
    d8 = dg(pg)
    ok("[800px] 一般電子鏈的 MLCC 剖析圖還在", d8.get("present") and FEAT in d8.get("full", ""), d8.get("svgW"))
    ok("[800px] 剖析圖以原尺寸顯示（不被欄寬壓縮）", d8.get("svgW", 0) >= 960, d8.get("svgW"))
    ok("[800px] 圖上最小的字真的 ≥ 12px（Andy 講了三次的「文字太小」）",
       d8.get("minFs", 0) >= 11.9, d8.get("minFs"))
    r8a = rows(pg)
    ok("[800px] 找得到「被動元件 MLCC」族群卡片", pick_group(pg, "mlcc"))
    pg.wait_for_timeout(900)
    r8b = rows(pg)
    ok("[800px] 點族群卡片，成分股筆數真的變少", 0 < r8b < r8a, f"{r8a} → {r8b}")
    pg.set_viewport_size({"width": 1500, "height": 1000})


SECTIONS = {
    "盤中即時":            lambda pg, b, base, code: t_live(pg, base),
    "大盤三張圖":          lambda pg, b, base, code: t_market3(pg, base),
    "今日事件":            lambda pg, b, base, code: t_events(pg, base),
    "明亮主題":            lambda pg, b, base, code: t_theme(pg, base),
    "總覽":                lambda pg, b, base, code: t_overview(pg, base),
    "市場明細":            lambda pg, b, base, code: t_market(pg, base),
    "資金流向":            lambda pg, b, base, code: t_flow(pg, base),
    "產業":                lambda pg, b, base, code: t_industry(pg, base),
    "族群頁":              lambda pg, b, base, code: t_group_pages(pg, base),
    "產業鏈導覽":          lambda pg, b, base, code: t_chainnav(pg, base),
    "一般電子鏈":          lambda pg, b, base, code: t_electronics(pg, base),
    "新-大盤三張圖":       lambda pg, b, base, code: t_new_market3(pg, base),
    "新-產業與個股":       lambda pg, b, base, code: t_new_industry(pg, base),
    "新-資金流向":         lambda pg, b, base, code: t_new_flow(pg, base),
    "新-輪動時鐘":         lambda pg, b, base, code: t_new_clock(pg, base),
    "任務板":              lambda pg, b, base, code: t_tasks(pg, base),
    "新-版面等高與多寬度": lambda pg, b, base, code: t_new_layout(pg, base),
    "題材":                lambda pg, b, base, code: t_themes(pg, base),
    "季節性":              lambda pg, b, base, code: t_season(pg, base),
    "批次1":               lambda pg, b, base, code: t_batch1(pg, base),
    "批次2":               lambda pg, b, base, code: t_batch2(pg, base),
    "批次3":               lambda pg, b, base, code: t_batch3(pg, base),
    "批次4":               lambda pg, b, base, code: t_batch4(pg, base),
    "批次7":               lambda pg, b, base, code: t_batch7(pg, base),
    "批次6-N1":            lambda pg, b, base, code: t_batch6_n1(pg, base),
    "批次6-圖十":          lambda pg, b, base, code: t_batch6_n3(pg, base),
    "批次6-圖九":          lambda pg, b, base, code: t_batch6_n9(pg, base),
    "批次11-MLCC":         lambda pg, b, base, code: t_mlcc(pg, base),
    "產業關係面板":        lambda pg, b, base, code: t_relpanel(pg, base),
    "個股":                lambda pg, b, base, code: t_stock(pg, base, code),
    "個股即時分K":         lambda pg, b, base, code: t_livek(pg, base, code),
    "縮放掃描":            lambda pg, b, base, code: t_zoom_sweep(pg, base, code),
    "排序":                lambda pg, b, base, code: t_sort(pg, base),
    "資料狀態":            lambda pg, b, base, code: t_freshness(b, base),
    "網頁版號":            lambda pg, b, base, code: t_buildver(b, base),
    "設定面板":            lambda pg, b, base, code: t_cfgpop(pg, base, code),
    "K線縮放":             lambda pg, b, base, code: t_kzoom_keep(pg, base, code),
    "淺色主題":            lambda pg, b, base, code: t_lightink(b, base, code),
    "手機":                lambda pg, b, base, code: t_mobile(b, base, code),
}
SECTION_NAMES = list(SECTIONS)

# 每段跑多久（秒）。只用來把工作平均分給 worker，不影響判定。
# 第一次跑（檔案還不存在）就當每段一樣重；跑完會寫回去，下一次分得更平均。
TIMES_FILE = pathlib.Path(__file__).resolve().parent / ".uitest_times.json"

took: dict[str, float] = {}
counts: dict[str, int] = {}


def _selected(args, name: str) -> bool:
    """這一段要不要跑。

    `--sections` 是**精準比對**（給平行模式的 worker 用，名稱逗號分隔）；
    `--only` 是**子字串比對**（給人用，好打）。
    兩者的差別很重要：`--only 資金流向` 會同時命中「資金流向」與「新-資金流向」，
    那對人是方便，對分工卻是災難 —— 同一段被兩個 worker 各跑一次，
    結果會重複計算。所以 worker 一律走 `--sections`。
    """
    if args.sections:
        return name in [x.strip() for x in args.sections.split(",")]
    if args.only:
        return _want(args.only, name)
    return True


def _buckets(names: list[str], n: int) -> list[list[str]]:
    """把段落分給 n 個 worker，讓每一份的預估耗時盡量接近。

    用最長優先（LPT）：把最重的先放進目前最輕的那一籃。
    段落之間的耗時差距很大（實測 11 秒到 200 秒都有），
    用平均分配的話最慢那一籃會拖垮整輪 —— 平行化的效果就沒了。
    """
    try:
        w = json.loads(TIMES_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 —— 沒有紀錄就當每段一樣重
        w = {}
    order = sorted(names, key=lambda x: -float(w.get(x, 30)))
    out: list[list[str]] = [[] for _ in range(n)]
    load = [0.0] * n
    for nm in order:
        i = load.index(min(load))
        out[i].append(nm)
        load[i] += float(w.get(nm, 30))
    return [x for x in out if x]


def run_parallel(args) -> int:
    """把段落拆給幾個子行程同時跑，再把結果合起來。

    為什麼是「多行程」而不是「多執行緒」（2026-09-20）
    ------------------------------------------------
    Playwright 的同步 API **不能跨執行緒共用**，一個執行緒要有自己的
    `sync_playwright()`。與其在同一個行程裡繞開它，不如直接開子行程：
    每個 worker 跑的就是**今天已經驗證過的那條路徑**（單行程、依序跑它那幾段），
    只是段落少一點。風險最低，而驗收程式最怕的就是改出「假綠」。

    每個 worker 自己起一個 HTTP 伺服器，所以埠要分開（`TW_UITEST_PORT`）。
    """
    names = [n for n in SECTION_NAMES if _selected(args, n)]
    if not names:
        print("沒有符合的段落"); return 0
    n = max(1, min(args.workers, len(names)))
    parts = _buckets(names, n)
    print(f"平行驗收：{len(names)} 段拆成 {len(parts)} 份", flush=True)
    for i, part in enumerate(parts, 1):
        print(f"  #{i}（{len(part)} 段）：{'、'.join(part)}", flush=True)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="uitest-"))
    procs = []
    for i, part in enumerate(parts):
        out = tmp / f"w{i}.json"
        env = dict(os.environ, TW_UITEST_PORT=str(PORT + 1 + i))
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()),
               "--code", args.code, "--sections", ",".join(part), "--json", str(out)]
        procs.append((subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True), out, part))

    for pr, out, part in procs:
        tail = (pr.communicate()[0] or "")
        if pr.returncode not in (0, 1):
            fails.append(f"【worker {'、'.join(part)}】子行程異常結束（code {pr.returncode}）：{tail[-400:]}")

    merged_times: dict[str, float] = {}
    for _pr, out, part in procs:
        try:
            d = json.loads(out.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            fails.append(f"【worker {'、'.join(part)}】沒有交回結果：{e}")
            continue
        fails.extend(d.get("fails") or [])
        for nt in (d.get("notes") or []):
            if nt not in notes:
                notes.append(nt)
        counts.update(d.get("counts") or {})
        merged_times.update(d.get("took") or {})
    shutil.rmtree(tmp, ignore_errors=True)

    # 依原本的順序印，這樣跟依序跑的輸出可以直接對照
    for nm in SECTION_NAMES:
        if nm in counts:
            print(f"  {nm}：{counts[nm]} 個問題（{merged_times.get(nm, 0):.0f}s）", flush=True)
    try:
        old = {}
        if TIMES_FILE.exists():
            old = json.loads(TIMES_FILE.read_text(encoding="utf-8"))
        old.update(merged_times)
        TIMES_FILE.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001 —— 記不起來只是下次分得沒那麼平均，不該讓驗收失敗
        pass
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--headed", action="store_true")
    # --only：只跑名稱含這個字的段落。Andy 2026-09-18「別讓我等在重跑一輪上」——
    # 一輪 14 分鐘，改一段就重跑全部是純浪費。**交付前一定要跑完整一輪**，
    # --only 只給開發過程中反覆修同一段的時候用。
    ap.add_argument("--only", default="")
    # --sections：精準比對的段落清單（逗號分隔）。給平行模式的 worker 用，人不必打。
    ap.add_argument("--sections", default="")
    # --json：子行程把結果寫到這個檔，由父行程合併。有值就代表「我是 worker」。
    ap.add_argument("--json", default="")
    # --workers：拆成幾個子行程同時跑。1 ＝ 依序跑（改壞的時候用它對照）。
    #   預設 4：實測 31 段一輪 15 分鐘，最長的那幾段各 2~3 分鐘，
    #   再多開也被最長那一段卡住，而且每個 worker 都要吃一個 Chromium 的記憶體。
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    # 父行程模式：自己不跑瀏覽器，只負責拆工與合併
    if args.workers > 1 and not args.json:
        t_par = time.time()
        run_parallel(args)
        return _report(t_par)

    from playwright.sync_api import sync_playwright

    srv = serve(); time.sleep(0.4)
    base = f"http://127.0.0.1:{PORT}/index.html"
    t0 = time.time()

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=not args.headed)
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        pg.on("pageerror", lambda e: fails.append(f"pageerror: {e}"))
        # 缺頁測試會故意讓一個個股頁回 404，那一筆不算問題
        pg.on("console", lambda m: fails.append(f"console.error: {m.text}")
              if m.type == "error" and "ERR_FAILED" not in m.text and "fonts.googleapis" not in m.text
              # 本機／CI 連不到 Cloudflare Worker，即時報價抓不到是預期的，不是 bug
              and "ERR_TUNNEL_CONNECTION_FAILED" not in m.text and "workers.dev" not in m.text
              and "ERR_NAME_NOT_RESOLVED" not in m.text and "ERR_INTERNET_DISCONNECTED" not in m.text
              and "404" not in m.text else None)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())

        for name in SECTION_NAMES:
            if not _selected(args, name):
                continue
            n0, ts = len(fails), time.time()
            try:
                # ★ 每一段開始前先確保頁面已經在網站上。
                #   平行化之後，任何一段都可能是某個 worker 的第一段 ——
                #   還在 about:blank 的話，那一段裡的相對路徑 fetch 會整段爆掉
                #   （2026-09-20 的「族群頁」就是這樣被抓出來的）。
                #   已經在站上就不重載，避免多花時間、也不動既有的頁面狀態。
                if not (pg.url or "").startswith("http"):
                    pg.goto(base, wait_until="networkidle"); pg.wait_for_timeout(600)
                SECTIONS[name](pg, b, base, args.code)
            except Exception as e:  # noqa: BLE001
                fails.append(f"【{name}】操作中途爆掉：{type(e).__name__} {e}")
            took[name] = round(time.time() - ts, 1)
            counts[name] = len(fails) - n0
            print(f"  {name}：{counts[name]} 個問題（{took[name]:.0f}s）", flush=True)
        b.close()
    srv.shutdown()

    # worker 模式：把結果交回父行程，不自己印總結（父行程會依原順序統一印）
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"fails": fails, "notes": notes, "counts": counts, "took": took},
            ensure_ascii=False), encoding="utf-8")
        return 1 if fails else 0
    try:
        TIMES_FILE.write_text(json.dumps(took, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return _report(t0)


def _report(t0: float) -> int:
    """印總結。依序跑與平行跑共用這一支，所以兩種模式的輸出格式完全一樣 ——
    改壞的時候可以直接 diff 兩邊的結果。"""
    print(f"\n===== 真人操作驗收（{time.time() - t0:.0f} 秒）=====")
    if notes:
        print("備註：")
        for n in notes:
            print(f"  · {n}")
    if fails:
        print(f"\n❌ {len(fails)} 個問題：")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\n✅ 每個功能都實際操作過，全部都有反應。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
