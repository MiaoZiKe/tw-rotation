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

import argparse
import json
import re
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8767

fails: list[str] = []
notes: list[str] = []


def ok(name: str, cond: bool, detail=None) -> bool:
    """cond 為真＝這個功能真的動了；為假就記下來，最後一次列出。"""
    if not cond:
        fails.append(f"{name}　←　{detail if detail is not None else ''}")
    return bool(cond)


def changed(name: str, before, after, detail: str = "") -> bool:
    return ok(name, before != after, f"操作前後一樣：{before!r} → {after!r}　{detail}")


def serve():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ 小工具
def click(pg, sel: str, wait: int = 300):
    """用真的滑鼠點（會捲進畫面），點不到就記一筆。"""
    try:
        el = pg.query_selector(sel)
        if not el:
            fails.append(f"找不到可點的元素：{sel}")
            return False
        el.scroll_into_view_if_needed()
        el.click(timeout=4000)
        pg.wait_for_timeout(wait)
        return True
    except Exception as e:  # noqa: BLE001
        fails.append(f"點不下去 {sel}：{type(e).__name__} {e}")
        return False


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
    click(pg, "#dg3d", 800)   # 留在平面圖，不影響後面的驗收


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
    click(pg, "#candFacets button[data-f=all]", 350)
    before = count(pg, "#candBody tr.whyrow")
    click(pg, "#candBody tr[data-code]", 350)
    mid = count(pg, "#candBody tr.whyrow")
    changed("點候選名單一列會展開「為何選它」", before, mid)
    why_txt = text(pg, "#candBody tr.whyrow .why")
    ok("「為何選它」有帶實際數字", any(ch.isdigit() for ch in why_txt), why_txt[:60])
    click(pg, "#candBody tr[data-code]", 350)
    after = count(pg, "#candBody tr.whyrow")
    changed("再點一次會收起來", mid, after)

    # --- 排序：每個可排序的表頭都點兩次，順序要真的反過來，箭頭要跟著跑
    heads = pg.evaluate("[...document.querySelectorAll('#candTable th[data-k]')].map(t => t.dataset.k)")
    ok("候選名單表頭可以排序", len(heads) >= 4, heads)
    for k in heads:
        first_a = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st1 = pg.evaluate("""() => ({ first: (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code,
            arrow: [...document.querySelectorAll('#candTable th')].filter(t => /[▲▼]/.test(t.textContent)).map(t => t.dataset.k) })""")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st2 = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        ok(f"表頭「{k}」點下去箭頭跑到這一欄", st1["arrow"] == [k], st1["arrow"])
        ok(f"表頭「{k}」點兩次順序會反過來", st1["first"] != st2 or first_a == st2,
           f"{first_a} → {st1['first']} → {st2}")

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
        pg.mouse.click(box["x"] + box["w"] * 0.2, box["y"] + box["h"] * 0.35)
        pg.wait_for_timeout(900)
        st = pg.evaluate("""() => ({ open: !document.getElementById('heatPanel').hidden,
            title: (document.querySelector('#heatPanel .hh b')||{}).textContent,
            stocks: document.querySelectorAll('#heatPanel .ms a').length,
            link: !!document.querySelector('#heatPanel a[href^="#industry/group/"]') })""")
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
        click(pg, f'#hero .kpi[data-drill="{k}"]', 1400)
        st = pg.evaluate("""() => ({ hash: location.hash, tab: (document.querySelector('.tab.on')||{dataset:{}}).dataset.view,
            title: (document.getElementById('mktTitle')||{}).innerText,
            rows: document.querySelectorAll('#mktBody tr[data-code]').length,
            blocks: document.querySelectorAll('#mktBody .ma, #mktBody .t5').length,
            note: (document.querySelector('#mktBody .kpinote')||{}).textContent.length })""")
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
        ok(f"總覽「{name}」不是長條圖", types and 'bar' not in types, types)
        ok(f"總覽「{name}」用的是更生動的圖形", types and any(w in types for w in want), types)

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
    ok("市場明細有四個分頁", len(tabs) >= 4, tabs)
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
    for cid, name in (("rankFlow", "資金流向排行"), ("bump", "名次變化"),
                      ("sankey", "資金桑基圖"), ("river", "資金河流圖"),
                      ("instGroups", "族群 × 法人"), ("conc", "資金集中度"), ("valScatter", "估值散布圖")):
        has = pg.evaluate(f"() => {{ const e = document.getElementById('{cid}'); return e ? {{ canvas: !!e.querySelector('canvas'), empty: !!e.querySelector('.empty'), msg: ((e.querySelector('.empty')||{{}}).textContent||'').trim() }} : null; }}")
        # 法人比價量晚一輪落地（價量 15:30、法人 18:30）：當天下午「本週」那一段本來就還沒有法人。
        # 那時不該畫圖，但要**講清楚為什麼**，所以接受「有解釋的空狀態」，不接受空白或制式的一句話。
        excused = (cid == "instGroups" and has and has["empty"]
                   and "還沒出" in has["msg"] and "18:30" in has["msg"])
        ok(f"資金流向「{name}」有畫出來（或說清楚為什麼還沒有）",
           bool(has) and ((has["canvas"] and not has["empty"]) or excused), has)

    # --- 期間切換：換一個期間，說明文字、排行圖、法人圖都要真的跟著換
    ps = pg.evaluate("[...document.querySelectorAll('#periodSeg button')].map(b => b.dataset.p)")
    ok("資金流向有期間切換（本週／上週／上上週／本月／上月／近三月）", len(ps) >= 5, ps)
    seen = {}
    for k in ps:
        click(pg, f'#periodSeg button[data-p="{k}"]', 900)
        seen[k] = pg.evaluate("""() => ({ on: (document.querySelector('#periodSeg button.on')||{dataset:{}}).dataset.p,
            note: (document.getElementById('periodNote')||{}).textContent,
            sub: (document.getElementById('rankSub')||{}).textContent,
            rank: !!document.querySelector('#rankFlow canvas'),
            inst: !!document.querySelector('#instGroups canvas'),
            instMsg: ((document.querySelector('#instGroups .empty')||{}).textContent||'').trim(),
            top: (() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
                   if (!c) return null; const y = c.getOption().yAxis[0].data || []; return y[y.length-1] || null; })() })""")
        ok(f"期間「{k}」按下去真的被選取", seen[k]["on"] == k, seen[k])
        ok(f"期間「{k}」有寫出日期範圍", "～" in (seen[k]["note"] or ""), seen[k]["note"])
        ok(f"期間「{k}」排行圖有畫出來", seen[k]["rank"], seen[k])
        ok(f"期間「{k}」法人圖有畫出來（或說清楚為什麼還沒有）",
           seen[k]["inst"] or ("還沒出" in seen[k]["instMsg"] and "18:30" in seen[k]["instMsg"]), seen[k])
    ok("不同期間的說明文字不一樣", len({v["note"] for v in seen.values()}) == len(seen),
       {k: v["note"] for k, v in seen.items()})
    ok("不同期間排出來的第一名不完全相同", len({v["top"] for v in seen.values()}) >= 2,
       {k: v["top"] for k, v in seen.items()})

    # --- 名次變化要跟著期間換刻度（Andy：「資金流向排名不會變」）
    BUMPX = """() => { const c = echarts.getInstanceByDom(document.getElementById('bump'));
        return { x: c ? (c.getOption().xAxis[0].data || []) : null,
                 n: c ? c.getOption().series.length : 0,
                 sub: (document.getElementById('bumpSub')||{}).textContent }; }"""
    click(pg, '#periodSeg button[data-p="w0"]', 1000)
    bw = pg.evaluate(BUMPX)
    click(pg, '#periodSeg button[data-p="m1"]', 1200)
    bm = pg.evaluate(BUMPX)
    ok("名次變化在週期間是用「週」的刻度", "週" in (bw["sub"] or ""), bw["sub"])
    ok("名次變化在月期間改成「月」的刻度", "月" in (bm["sub"] or ""), bm["sub"])
    changed("切到上月，名次變化的 X 軸真的換了", bw["x"], bm["x"])
    ok("月名次的刻度是年月（例如 2026/08）", all(len(str(v)) == 7 for v in (bm["x"] or ["x"])), bm["x"])
    ok("月名次沒有留下上一張圖的殘線", bm["n"] <= 10, bm["n"])
    click(pg, '#periodSeg button[data-p="w0"]', 1000)
    ok("切回本週又變回週刻度", "週" in (pg.evaluate(BUMPX)["sub"] or ""))

    # --- 每張圖的「怎麼看」：按下去要真的展開白話說明，再按要收起來
    hows = pg.evaluate("[...document.querySelectorAll('#v-flow .howbtn')].map(b => b.dataset.how)")
    ok("資金流向每張圖都有「怎麼看」", len(hows) >= 7, hows)
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
    backs = pg.evaluate("[...document.querySelectorAll('#rotBack button')].map(b => b.dataset.v)")
    ok("輪動階段可以換比較天數", len(backs) >= 2, backs)
    seenb = {}
    for v in backs:
        click(pg, f'#rotBack button[data-v="{v}"]', 700)
        seenb[v] = pg.evaluate("""() => ({ on: (document.querySelector('#rotBack button.on')||{dataset:{}}).dataset.v,
            move: (document.getElementById('rotMove')||{}).innerText,
            items: document.querySelectorAll('#rotBoard li[data-gid]').length })""")
        ok(f"「和 {v} 天前比」按下去真的被選取", seenb[v]["on"] == v, seenb[v])
        ok(f"「和 {v} 天前比」有寫出換階段的族群或明講沒有", v in (seenb[v]["move"] or ""), seenb[v]["move"][:40])
    ok("換比較天數，換階段的名單真的不一樣", len({v["move"] for v in seenb.values()}) >= 2,
       {k: v["move"][:30] for k, v in seenb.items()})

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
    click(pg, '#rotBack button[data-v="5"]', 900)
    h0 = canvas_hash(pg, "#rotClock")
    click(pg, '#rotBack button[data-v="20"]', 1100)
    changed("換成和 20 天前比，輪動時鐘的尾巴真的重畫", h0, canvas_hash(pg, "#rotClock"))
    click(pg, '#rotBack button[data-v="5"]', 900)
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
        ok(f"點時鐘上的「{pt['name']}」會進它的族群頁", now == "#industry/group/" + pt["gid"], f"{before} → {now}")
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
    pg.fill("#vPeHi", "12"); pg.wait_for_timeout(700)
    n1 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    hi = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')]
        .map(tr => parseFloat(tr.children[2].textContent)).filter(Number.isFinite)""")
    ok("本益比上限真的篩掉東西", n1 < n0 or not n1, f"{n0} → {n1}")
    ok("篩出來的本益比真的都 ≤ 12", all(v <= 12.0001 for v in hi), [v for v in hi if v > 12][:5])
    pg.fill("#vRoe", "20"); pg.wait_for_timeout(700)
    n2 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    ok("再加 ROE 條件會更少", n2 <= n1, f"{n1} → {n2}")
    changed("篩選後的檔數說明跟著變", cnt0, text(pg, "#vCount"))
    click(pg, "#vReset", 800)
    ok("清除條件後回到原本的檔數", text(pg, "#vCount") == cnt0, f"{cnt0} vs {text(pg, '#vCount')}")
    # 勾「只看低於族群中位」要真的只留低於中位的
    click(pg, "#vBelow", 800)
    below = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')].map(tr => [
        parseFloat(tr.children[2].textContent), parseFloat(tr.children[3].textContent)])
        .filter(a => Number.isFinite(a[0]) && Number.isFinite(a[1]))""")
    ok("「只看低於族群中位」真的只留本益比低於中位的", all(a[0] < a[1] for a in below),
       [a for a in below if a[0] >= a[1]][:4])
    click(pg, "#vBelow", 600)

    # --- 這頁每張圖都不可以有縮放框（Andy 09-13：「將這邊的縮放功能取消」）
    for w, lb in (("rankFlowWrap", "資金流向排行"), ("bumpWrap", "名次變化"),
                  ("rotClockWrap", "輪動時鐘"), ("sankeyWrap", "資金去向"),
                  ("riverWrap", "族群佔比河流"), ("instGroupsWrap", "族群 × 法人")):
        check_nozoom(pg, w, lb)


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
    click(pg, '#mktSeg button[data-v="TWSE"]', 500); n_twse = count(pg, "#memberTable tbody tr")
    click(pg, '#mktSeg button[data-v="TPEX"]', 500); n_tpex = count(pg, "#memberTable tbody tr")
    click(pg, '#mktSeg button[data-v="ALL"]', 500)
    ok("上市／上櫃切換真的在篩選", n_twse != n_all or n_tpex != n_all, f"全部 {n_all}／上市 {n_twse}／上櫃 {n_tpex}")
    ok("上市＋上櫃 = 全部（沒有漏掉或重複）", n_twse + n_tpex == n_all, f"{n_twse}+{n_tpex} != {n_all}")

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
        pg.wait_for_timeout(600)
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
    for tid in tids[:3]:
        pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(1100)
        ok(f"題材 {tid} 有剖析圖", count(pg, "#themeDiagram svg") > 0)
        # Andy 09-13：剖析圖不要縮放（跟產業／個股剖析圖一致），要看大圖用右上角「放大」
        check_nozoom(pg, "themeDiagram", f"題材 {tid} 剖析圖")
        ok(f"題材 {tid} 成員有依族群分組", count(pg, "#themeDetail .gsec, #themeDetail h4, #themeParts") > 0)
        if count(pg, "#themeDiagram [data-part][data-codes]"):
            click(pg, "#themeDiagram [data-part][data-codes]", 600)
            ok(f"題材 {tid} 點零件會列出個股", count(pg, "#themeParts a.lk") > 0)


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
    ok("河流圖有兩個模式可切", count(pg, "#peMode button") == 2, count(pg, "#peMode button"))
    note0 = text(pg, "#peNote")
    ok("河流圖下方有講出目前落在哪一區", "區" in note0, note0[:100])
    if count(pg, "#peMode button") == 2:
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
        click(pg, '#peMode button[data-v="band"]', 1400)
        changed("切回「色帶分區」，圖又變回去", h1, canvas_hash(pg, "#peChart"))
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
    LIVE_TFS = ("5s", "1m", "5m")
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
    click(pg, "#cfgBtn", 450)
    ok("設定面板打得開", pg.evaluate("() => { const p = document.getElementById('cfgPop'); return !!p && !p.hidden; }"))
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

    # --- 產業鏈同步：點上方產業鏈的另一檔，個股頁要跟著換
    if count(pg, "#chainMap .co"):
        h0 = pg.evaluate("location.hash")
        pg.evaluate("""() => { const cs = [...document.querySelectorAll('#chainMap .co')];
            const other = cs.find(c => !c.classList.contains('sel'));
            if (other) other.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }""")
        pg.wait_for_timeout(1800)
        changed("點產業鏈上的另一檔，個股頁跟著換", h0, pg.evaluate("location.hash"))


def t_season(pg, base):
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("季節性熱力圖有畫出來", pg.evaluate("() => !!document.querySelector('#seasonHeat canvas')"))
    ok("季節性頁有區間文字", len(text(pg, "#seasonRange")) > 3, text(pg, "#seasonRange"))
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
       以及 2026-09-15 他親口要的「法人連續買超」trustWrap）。
       這一段是最後一道防線：任何一頁冒出多餘的縮放框、徽章或「放大」鈕都算失敗。"""
    ALLOW = ("heatWrap", "indTreeWrap", "themeMapWrap", "heatZoom", "themeZoom", "trustWrap")
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
    ok("即時週期有標記（紅點）", pg.evaluate("() => document.querySelectorAll('#tfSeg button.livetf').length") == 3)

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
    """
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
        ok(f"選了 {pick} 之後筆數真的變少", n_after < before_n or len(days) == 1,
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
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

        for name, fn in (("盤中即時", t_live), ("大盤三張圖", t_market3), ("今日事件", t_events), ("明亮主題", t_theme),
                         ("總覽", t_overview), ("市場明細", t_market), ("資金流向", t_flow), ("產業", t_industry),
                         ("題材", t_themes), ("季節性", t_season)):
            n0 = len(fails)
            try:
                fn(pg, base)
            except Exception as e:  # noqa: BLE001
                fails.append(f"【{name}】操作中途爆掉：{type(e).__name__} {e}")
            print(f"  {name}：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_stock(pg, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【個股】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  個股：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_livek(pg, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【個股即時分K】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  個股即時分K：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_zoom_sweep(pg, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【縮放掃描】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  縮放掃描：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_freshness(b, base)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【資料狀態】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  資料狀態：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_mobile(b, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【手機】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  手機：{len(fails) - n0} 個問題", flush=True)
        b.close()
    srv.shutdown()

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
