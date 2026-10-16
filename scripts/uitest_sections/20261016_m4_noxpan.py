# 驗收段落「手機不右滑1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone 實機）：「手機版本網頁打開右滑都會出現這樣的問題，請務必處理」
#   根因＝右側事件抽屜 aside#side 關著時 fixed＋translateX(100%) 停在視窗右外側 300px；iOS Safari／LINE 內建瀏覽器把它算進捲動範圍。
#   Chromium 不會因為它而真的捲動，所以「拖完 scrollX=0」單獨驗不出這個 bug —— 主要斷言是幾何：
#   沒有任何元素（含 fixed）伸出視窗左右、又沒有被祖先的 overflow 裁掉。改前這條在每一頁都紅（#side L=390 R=690）。
M4_XPAN_JS = """() => { const W = innerWidth; const out = [];
  const clipped = e => { for (let a = e.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
    const cs = getComputedStyle(a); if (cs.overflowX !== 'visible' || cs.contain.includes('paint')) return true; } return false; };
  for (const e of document.querySelectorAll('body *')) { const r = e.getBoundingClientRect(); if (!r.width) continue;
    if ((r.right > W + 1 || r.left < -1) && !clipped(e)) out.push((e.id ? '#' + e.id : e.tagName) + ' L=' + Math.round(r.left) + ' R=' + Math.round(r.right) + ' ' + getComputedStyle(e).position); }
  return { n: out.length, bad: out.slice(0, 6), sw: document.documentElement.scrollWidth, W }; }"""


def _m4_drag_left(c, pg, px=300, y=420):
    cdp = c.new_cdp_session(pg)
    tp = lambda t, x: cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": [] if t == "touchEnd" else [{"x": x, "y": y, "id": 1}]})
    x0 = pg.viewport_size["width"] - 30
    tp("touchStart", x0)
    for i in range(1, 11):
        tp("touchMove", x0 - px * i / 10)
    tp("touchEnd", 0)
    pg.wait_for_timeout(500)
    return pg.evaluate("() => ({ sx: scrollX, ol: visualViewport.offsetLeft, sc: visualViewport.scale })")


def t_m4_noxpan_1016(b, base):
    T = "手機不右滑1016"
    pages = ["overview", "flow", "heat", "industry", "stock/2330", "market", "etf", "watch"]
    for w in (360, 390, 430):
        c = b.new_context(viewport={"width": w, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page()
        for h in pages:
            pg.goto(base + "#" + h, wait_until="domcontentloaded")
            if not wait_until(pg, "() => document.documentElement.classList.contains('m4')", 20000):
                ok(f"【{T}】{w} #{h}：手機版就緒", False); continue
            pg.wait_for_timeout(2500)
            g = pg.evaluate(M4_XPAN_JS)
            ok(f"【{T}】{w} #{h}：沒有元素（含 fixed 抽屜）伸出視窗左右而沒被裁掉、scrollWidth={g['sw']}", g["n"] == 0 and g["sw"] <= w, g)
            d = _m4_drag_left(c, pg)
            ok(f"【{T}】{w} #{h}：手指往左拖 300px → scrollX 與 visualViewport.offsetLeft 都是 0", d["sx"] == 0 and d["ol"] == 0, d)
        # 抽屜真的打開、關上：打開時在視窗內；關上後又不伸出去
        pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        pg.evaluate("() => window.twSetSide(true)"); pg.wait_for_timeout(500)
        r = pg.evaluate("() => { const r = document.getElementById('side').getBoundingClientRect(); return { l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width) }; }")
        ok(f"【{T}】{w}：事件抽屜打開 → 寬 >250、貼右緣在視窗內", r["w"] > 250 and r["r"] <= w and r["l"] >= 0, r)
        pg.evaluate("() => window.twSetSide(false)"); pg.wait_for_timeout(600)
        g = pg.evaluate(M4_XPAN_JS)
        ok(f"【{T}】{w}：事件抽屜關上 → 不再伸出視窗", g["n"] == 0, g)
        # 比比玩球進行中也量
        pg.evaluate("() => window.Bibi && Bibi.act && Bibi.act('ball')")
        worst = 0
        for _ in range(5):
            pg.wait_for_timeout(450)
            worst = max(worst, pg.evaluate(M4_XPAN_JS)["n"])
        d = _m4_drag_left(c, pg)
        ok(f"【{T}】{w}：比比玩球中 → 伸出元素 0、往左拖 scrollX／offsetLeft=0", worst == 0 and d["sx"] == 0 and d["ol"] == 0, {"worst": worst, **d})
        c.close()


# ★ 2026-10-16 Andy（iPhone）：「手機版本網頁打開右滑都會出現這樣的問題」—— 8 頁 × 360／390／430：沒有元素伸出視窗、往左拖 300px scrollX＝0、抽屜開關、比比玩球中
register("手機不右滑1016", lambda pg, b, base, code: t_m4_noxpan_1016(b, base), after="桌機守門1008")
