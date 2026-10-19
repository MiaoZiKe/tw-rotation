# 驗收段落「搜尋自選分頁1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 搜尋自選分頁1019（Andy 10-19：「只能有上下拉 Bar，並且上方應該要顯示可以選擇加入的自選分頁」）
# 1440／390：點搜尋框（空白＝近期＋熱門；打字＝結果）
#   ① 下拉最上方一列「加入到：自選1 …」，每一頁一顆、作用中那顆亮；捲動清單時它固定在頂端
#   ② 點另一頁 → TwWatch 作用分頁真的換、那顆變亮；按 ☆ → 加進「那一頁」（其他頁不變）、提示寫那一頁的名字
#   ③ 下拉沒有橫向捲軸（scrollWidth ≤ clientWidth），星號完整在下拉框內


def t_search_tabs_1019(b, base, code):
    T = "搜尋自選分頁1019"
    errs: list[str] = []
    shots = os.environ.get("TW_SGTABS_SHOT")
    for w in (1440, 390):
        c = b.new_context(viewport={"width": w, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => !!window.TwWatch && !!document.getElementById('q')", 10000)
        pg.wait_for_timeout(600)
        if pg.evaluate("() => TwWatch.tabs().length") < 2:
            pg.evaluate("() => TwWatch.newTab('自選2')")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        if not pg.is_visible("#q"):
            for sel in ("#m4Search", "#mSearchBtn"):
                if pg.locator(sel).count() and pg.is_visible(sel):
                    pg.click(sel); break
            wait_until(pg, "() => { const q = document.getElementById('q'); return !!q && q.getClientRects().length > 0; }", 4000)
        pg.click("#q")
        got = wait_until(pg, "() => { const t = document.querySelectorAll('#sugg #sgTabs .sgtab'); return t.length >= 1 ? t.length : 0; }", 6000)
        tabs = pg.evaluate("() => TwWatch.tabs().map(t => t.id)")
        ok(f"{T}（{w}）：下拉最上方有「加入到」一列，每頁自選一顆、作用中那顆亮",
           bool(got) and got == len(tabs) and pg.evaluate("() => { const s = document.getElementById('sugg'), t = document.getElementById('sgTabs'); return s.firstElementChild === t && t.querySelector('.sgtab.on').dataset.wtab === TwWatch.cur(); }"), [got, tabs])
        if len(tabs) >= 2:
            other = [t for t in tabs if t != pg.evaluate("() => TwWatch.cur()")][0]
            pg.click(f"#sgTabs .sgtab[data-wtab='{other}']")
            ok(f"{T}（{w}）：點另一頁 → 作用分頁真的換、那顆變亮、下拉沒關",
               bool(wait_until(pg, f"() => TwWatch.cur() === '{other}' && document.querySelector('#sgTabs .sgtab.on').dataset.wtab === '{other}' && getComputedStyle(document.getElementById('sugg')).display !== 'none'", 3000)))
            pg.locator("#q").fill("23")
            wait_until(pg, "() => document.querySelectorAll('#sugg .sgrow .sgstar').length > 0", 6000)
            c0 = pg.evaluate("() => document.querySelector('#sugg .sgrow').dataset.c")
            pg.evaluate(f"() => TwWatch.tabs().forEach(t => TwWatch.remove('{c0}', t.id))")
            pg.locator("#q").fill("2"); pg.locator("#q").fill("23"); pg.wait_for_timeout(300)
            before = pg.evaluate("() => TwWatch.tabs().map(t => [t.id, t.codes.length])")
            pg.locator(f"#sugg .sgstar[data-star='{c0}']").first.click()
            ok(f"{T}（{w}）：按 ☆ → 加進選中的那一頁、其他頁不變、提示寫那一頁",
               bool(wait_until(pg, f"() => TwWatch.codes('{other}').includes('{c0}')", 3000))
               and all(pg.evaluate(f"(id) => TwWatch.codes(id).includes('{c0}')", t) is False for t in tabs if t != other)
               and pg.evaluate(f"() => (document.getElementById('sgNote') || {{}}).textContent || ''").startswith("已加入〈"),
               [before, pg.evaluate("() => TwWatch.tabs().map(t => [t.id, t.codes.length])")])
            pg.evaluate(f"() => TwWatch.remove('{c0}', '{other}')")
            pg.evaluate(f"(id) => TwWatch.setCur(id)", tabs[0])
            pg.locator("#q").fill("")
        st = pg.evaluate("""() => { const s = document.getElementById('sugg'), r = s.getBoundingClientRect(); s.scrollTop = 400;
            const t = document.getElementById('sgTabs').getBoundingClientRect();
            const stars = [...s.querySelectorAll('.sgstar')].map(x => x.getBoundingClientRect()).filter(x => x.height);
            return { sx: s.scrollWidth - s.clientWidth, ox: getComputedStyle(s).overflowX, sticky: Math.abs(t.top - r.top) <= 2,
                     inbox: stars.every(x => x.left >= r.left - 1 && x.right <= r.right + 1), n: stars.length }; }""")
        ok(f"{T}（{w}）：下拉只有上下捲軸（沒有橫向）、星號完整在框內、捲動時「加入到」固定在頂端", st["sx"] <= 0 and st["ox"] == "hidden" and st["inbox"] and st["sticky"] and st["n"] > 0, st)
        if shots and w == 1440:
            pg.evaluate("() => { document.getElementById('sugg').scrollTop = 0; }")
            pg.locator("#sugg").screenshot(path=shots)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("搜尋自選分頁1019", lambda pg, b, base, code: t_search_tabs_1019(b, base, code))
