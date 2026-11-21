# 驗收段落「法律上架1016」—— 2026-10-16 上架前打開同意橫幅（docs/launch_standard.md 第二節第 9 條）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_lg_page()、_lg_ls()、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# Andy 10-10：「上架再開」；10-16：「我準備明天上架了」→ legal_config.js enabled:true、effective_date '2026-10-17'。
# 打開前修 10-10 記下的兩個瑕疵：
#   ① 手機橫幅下方多空 114px：bottom 寫 calc(var(--mnav-h,102px)+12px)，底部導覽 10-08 已拿掉、--mnav-h 沒人定義 → 吃預設 102。
#      驗：390 橫幅底離視窗底 ≤ 13（12＋安全區）；整頁「document 高度 − 最後一個元素底」有橫幅與同意後一樣（橫幅不撐高頁面）。
#   ② 法律頁上橫幅蓋住「重點一覽」：法律頁改成內嵌（.lgban.inl，放在文件分頁下面）。
#      驗：四份法律頁 × 1440／390，橫幅與「重點一覽」、文件標題卡兩兩矩形不相交。
# 另外驗：這一段**不注入任何設定**（用的是 legal_config.js 本身）→ 判定啟用、版本＝2026-10-17、全文沒有【】；
#   第一次進站出現 → 按同意 → 消失、localStorage 真的寫入 → 關掉導覽（2026-10-17 起是 tour.js 的全站導覽）→ 重新整理不再出現；
#   1440 深色／淺色都畫得出、淺色橫幅是淺底；沒有橫向捲軸；橫幅字 ≥ 12px；客服鈕不跟橫幅疊（藏起來或不相交）；
#   平台導覽（tour.js）進行中橫幅讓開、結束回來（兩者不疊在一起）。
# 設 TW_LEGAL_SHOTS=<資料夾> 時順手存截圖。

LGL_RECT = """(s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null;
  const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null;
  const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; }"""

LGL_PAGE = """() => { const de = document.documentElement; let maxB = 0;
  for (const e of document.querySelectorAll('body *')) { const cs = getComputedStyle(e);
    if (cs.position === 'fixed' || cs.display === 'none' || !e.getClientRects().length) continue;
    if (e.closest('#side, #sideBack')) continue;
    const b = e.getBoundingClientRect().bottom + scrollY; if (b > maxB) maxB = b; }
  return { sh: de.scrollHeight, maxB: Math.round(maxB), tail: Math.round(de.scrollHeight - maxB),
           sw: de.scrollWidth - innerWidth, vh: innerHeight }; }"""

LGL_BAN = """() => { const b = document.getElementById('lgBanner'); if (!b) return null; const r = b.getBoundingClientRect(), cs = getComputedStyle(b);
  const fs = [...b.querySelectorAll('*')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
  const bg = cs.backgroundColor.match(/[\\d.]+/g).map(Number);
  return { pos: cs.position, inl: b.classList.contains('inl'), disp: cs.display, top: Math.round(r.top), bot: Math.round(r.bottom),
           gap: Math.round(innerHeight - r.bottom), l: Math.round(r.left), r: Math.round(r.right), w: innerWidth,
           minFs: fs.length ? Math.min(...fs) : 0, lum: (bg[0] * 299 + bg[1] * 587 + bg[2] * 114) / 1000,
           parent: b.parentElement ? (b.parentElement.id || b.parentElement.tagName) : '',
           afterTabs: !!(b.previousElementSibling && b.previousElementSibling.classList.contains('lgtabs')) }; }"""


def _lgl_hit(a, c):
    return bool(a and c and min(a[2], c[2]) - max(a[0], c[0]) > 0 and min(a[3], c[3]) - max(a[1], c[1]) > 0)


def _lgl_fab_ok(pg):
    """客服鈕（比比）跟固定的橫幅不疊：support.js 的避讓把它藏起來（supaway），或兩者矩形不相交。"""
    fab = pg.evaluate("() => { const f = document.getElementById('supFab'); if (!f || !f.getClientRects().length) return null;"
                      " const r = f.getBoundingClientRect(); return { away: f.classList.contains('supaway') || getComputedStyle(f).visibility === 'hidden',"
                      " r: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)] }; }")
    ban = pg.evaluate(LGL_RECT, "#lgBanner")
    return (fab is None or fab["away"] or not _lgl_hit(fab["r"], ban)), {"fab": fab, "ban": ban}


def _lgl_close_tour(pg, wait_ms=2500):
    """同意之後自動開的導覽關掉。2026-10-17 改前→改後（Andy 10-17：「在同意之後，不用額外跳視窗，直接開啟上方平台導覽功能」）：
    改前同意後跳舊的置中彈窗（#lgTour，按 #lgTourX 關）；改後開的是 tour.js 的全站導覽（#twTour，按「跳過導覽」#twTourSkip 關）。
    兩種都處理；導覽是同意後 0.2 秒才開，所以先等一下（最多 wait_ms）。在法律頁上同意不會開（不把讀條文的人拉走），那時直接略過。"""
    wait_until(pg, "() => !!document.getElementById('lgTour') || !!(window.TwTour && TwTour.state().active)", wait_ms)
    if pg.locator("#lgTourX").count():
        pg.click("#lgTourX"); pg.wait_for_timeout(300)
    if pg.locator("#twTourSkip").count():
        pg.click("#twTourSkip"); pg.wait_for_timeout(300)


def t_legal_launch_1016(b, base):
    T = "法律上架1016"
    shots = os.environ.get("TW_LEGAL_SHOTS", "")
    n0 = len(fails)

    # ---------------------------------------------------------------- 1440 深色／淺色：總覽浮動橫幅 → 同意 → 消失 → 重新整理不再出現
    for theme in ("dark", "light"):
        ctx, pg = _lg_page(b, 1440, 950, extra=f"try{{localStorage.setItem('tw.theme','{theme}')}}catch(e){{}}")
        pg.goto(base + "#overview", wait_until="networkidle"); pg.wait_for_timeout(2500)
        st = pg.evaluate("() => window.TwLegal.state()")
        if theme == "dark":
            ok(f"【{T}】legal_config.js 本身（不注入任何設定）→ 判定啟用、版本＝上架日 2026-10-17、必填齊、全文沒有【】",
               st["active"] is True and st["version"] == "2026-10-17" and not st["missing"]["fields"] and not st["missing"]["holes"], st)
        ok(f"【{T}】1440 {theme}：主題真的是 {theme}", pg.evaluate("() => document.documentElement.dataset.theme || 'dark'") == theme,
           pg.evaluate("() => document.documentElement.dataset.theme"))
        bn = pg.evaluate(LGL_BAN)
        ok(f"【{T}】1440 {theme}：第一次進站（沒有 tw.consent）→ 橫幅出現、固定在下方離底 16～32、字 ≥ 12px",
           bool(bn) and bn["pos"] == "fixed" and not bn["inl"] and 16 <= bn["gap"] <= 32 and bn["minFs"] >= 12, bn)
        ok(f"【{T}】1440 {theme}：橫幅底色跟著主題（深色＝暗底、淺色＝亮底）",
           bool(bn) and ((bn["lum"] < 100) if theme == "dark" else (bn["lum"] > 200)), bn)
        g = pg.evaluate(LGL_PAGE)
        ok(f"【{T}】1440 {theme}：沒有橫向捲軸", g["sw"] <= 1, g)
        good, info = _lgl_fab_ok(pg)
        ok(f"【{T}】1440 {theme}：客服鈕跟橫幅不疊", good, info)
        if shots:
            pg.screenshot(path=os.path.join(shots, f"1440_{theme}_banner.png"))
        pg.click("#lgAccept"); pg.wait_for_timeout(800)
        raw = _lg_ls(pg, "tw.consent")
        try:
            cv = json.loads(raw or "null")
        except Exception:  # noqa: BLE001
            cv = None
        ok(f"【{T}】1440 {theme}：按「同意並繼續」→ 橫幅消失、localStorage tw.consent 寫入 v=2026-10-17",
           pg.locator("#lgBanner").count() == 0 and bool(cv) and cv.get("v") == "2026-10-17" and bool(cv.get("at")), raw)
        _lgl_close_tour(pg)
        if shots and theme == "dark":
            pg.screenshot(path=os.path.join(shots, "1440_dark_after_accept.png"))
        pg.reload(wait_until="networkidle"); pg.wait_for_timeout(1800)
        ok(f"【{T}】1440 {theme}：重新整理 → 橫幅不再出現、導覽也不再自動開",
           pg.locator("#lgBanner").count() == 0 and pg.locator("#lgTour").count() == 0
           and not pg.evaluate("() => !!(window.TwTour && TwTour.state().active)"))
        ctx.close()

    # ---------------------------------------------------------------- 390：浮動橫幅貼底、不多空；同意前後頁面高度一樣
    ctx, pg = _lg_page(b, 390, 844, mobile=True)
    pg.goto(base + "#overview", wait_until="networkidle"); pg.wait_for_timeout(2800)
    bn = pg.evaluate(LGL_BAN)
    ok(f"【{T}】390：橫幅出現、固定、左右各留 12、離視窗底 ≤ 13px（改前 114：替已拿掉的底部導覽留的空）",
       bool(bn) and bn["pos"] == "fixed" and abs(bn["l"] - 12) <= 1 and abs(bn["w"] - bn["r"] - 12) <= 1 and 0 <= bn["gap"] <= 13, bn)
    ok(f"【{T}】390：橫幅字 ≥ 12px", bool(bn) and bn["minFs"] >= 12, bn)
    g1 = pg.evaluate(LGL_PAGE)
    ok(f"【{T}】390：沒有橫向捲軸", g1["sw"] <= 1, g1)
    good, info = _lgl_fab_ok(pg)
    ok(f"【{T}】390：客服鈕跟橫幅不疊（被固定元素蓋到就藏、橫幅收掉再回來）", good, info)
    if shots:
        pg.screenshot(path=os.path.join(shots, "390_banner.png"))
    # 平台導覽進行中 → 橫幅讓開；結束 → 回來
    has_tour = pg.evaluate("() => !!(window.TwTour && window.TwTour.start)")
    if ok(f"【{T}】390：頁面有平台導覽（tour.js）", has_tour):
        pg.evaluate("() => window.TwTour.start('site')"); pg.wait_for_timeout(900)
        on = pg.evaluate(LGL_BAN)
        pg.evaluate("() => window.TwTour.stop()"); pg.wait_for_timeout(600)
        off = pg.evaluate(LGL_BAN)
        ok(f"【{T}】390：平台導覽進行中橫幅讓開（不顯示）、導覽結束橫幅回來 —— 兩者不疊在一起",
           bool(on) and on["disp"] == "none" and bool(off) and off["disp"] != "none", {"導覽中": on, "結束後": off})
    pg.click("#lgAccept"); pg.wait_for_timeout(800)
    _lgl_close_tour(pg)
    pg.wait_for_timeout(600)
    g2 = pg.evaluate(LGL_PAGE)
    ok(f"【{T}】390：頁面底部沒有多出的空白 —— document 高度 − 最後一個元素底：有橫幅 {g1['tail']}、同意後 {g2['tail']}（相同且 ≤ 40）",
       abs(g1["tail"] - g2["tail"]) <= 2 and g2["tail"] <= 40 and abs(g1["sh"] - g2["sh"]) <= 2, {"有橫幅": g1, "同意後": g2})
    good, info = _lgl_fab_ok(pg)
    ok(f"【{T}】390：同意後客服鈕回到右下角（沒有被藏著）", pg.evaluate(
        "() => { const f = document.getElementById('supFab'); return !f || !f.classList.contains('supaway'); }"), info)
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok(f"【{T}】390：重新整理 → 不再出現", pg.locator("#lgBanner").count() == 0)
    ctx.close()

    # ---------------------------------------------------------------- 法律頁：內嵌、不蓋「重點一覽」
    for w, h, mob in ((1440, 950, False), (390, 844, True)):
        ctx, pg = _lg_page(b, w, h, mobile=mob)
        for doc in ("terms", "privacy", "refund", "disclaimer"):
            pg.goto(base + "#" + doc, wait_until="networkidle"); pg.wait_for_timeout(1500)
            bn = pg.evaluate(LGL_BAN)
            ban, summ, head = pg.evaluate(LGL_RECT, "#lgBanner"), pg.evaluate(LGL_RECT, ".lgsum"), pg.evaluate(LGL_RECT, ".lghead")
            ok(f"【{T}】{w} #{doc}：橫幅內嵌在文件分頁下面（不浮在內容上）",
               bool(bn) and bn["inl"] and bn["pos"] != "fixed" and bn["parent"] == "v-legal" and bn["afterTabs"], bn)
            ok(f"【{T}】{w} #{doc}：橫幅與「重點一覽」、文件標題卡矩形不相交",
               bool(ban) and bool(summ) and bool(head) and not _lgl_hit(ban, summ) and not _lgl_hit(ban, head),
               {"橫幅": ban, "重點一覽": summ, "標題卡": head})
            g = pg.evaluate(LGL_PAGE)
            ok(f"【{T}】{w} #{doc}：沒有橫向捲軸、橫幅字 ≥ 12px", g["sw"] <= 1 and bn and bn["minFs"] >= 12, {"g": g, "bn": bn})
            if shots and doc == "terms":
                pg.screenshot(path=os.path.join(shots, f"{w}_terms_banner.png"))
        # 在法律頁上按同意 → 內嵌橫幅消失、重點一覽往上補位；換到別份文件也不再出現
        pg.goto(base + "#terms", wait_until="networkidle"); pg.wait_for_timeout(1200)
        s0 = pg.evaluate(LGL_RECT, ".lgsum")
        pg.click("#lgAccept"); pg.wait_for_timeout(800)
        _lgl_close_tour(pg, 600)
        s1 = pg.evaluate(LGL_RECT, ".lgsum")
        ok(f"【{T}】{w} 法律頁按同意 → 橫幅消失、重點一覽往上補位（沒留空洞）",
           pg.locator("#lgBanner").count() == 0 and bool(s0) and bool(s1) and s1[1] < s0[1] - 50, {"前": s0, "後": s1})
        pg.click(".lgtabs a[href='#privacy']"); pg.wait_for_timeout(900)
        ok(f"【{T}】{w} 同意後換到隱私權政策 → 不再出現", pg.locator("#lgBanner").count() == 0 and pg.evaluate("() => location.hash") == "#privacy")
        ctx.close()

    ok(f"【{T}】整段沒有 pageerror", not [f for f in fails[n0:] if "pageerror" in f], fails[n0:])


register("法律上架1016", lambda pg, b, base, code: t_legal_launch_1016(b, base), after="同意條款與法律頁")
