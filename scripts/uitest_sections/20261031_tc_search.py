# 驗收段落「科技透明圈搜尋排序1031」：公司排行搜尋框、各產業公司卡排序鈕＋分紅月數。flake8: noqa
def t_tc_search(b, base, code):
    T = "科技透明圈搜尋排序1031"
    SP = "/tmp/claude-0/-home-user-tw-rotation/d35d4770-19c6-5ef0-b46f-3181b0b89ae3/scratchpad/"
    errs: list[str] = []
    for tag, vp, mob in [("桌機", {"width": 1440, "height": 900}, False), ("手機", {"width": 390, "height": 844}, True)]:
        c = b.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
        c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done');localStorage.removeItem('tw.tc.csort')}catch(e){}")
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#tc/stats", wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
        rows = lambda: pg.evaluate("() => [...document.querySelectorAll('#tcRank .tc-rkrow')].map(r => [r.querySelector('.tc-rkn').innerText, r.querySelector('.tc-rkt').childNodes[0].textContent])")
        cnt = lambda: pg.evaluate("() => +document.querySelector('#tcRkBody .tc-cnt b').innerText")
        ok(f"{T}（{tag}）：有搜尋框 placeholder「搜尋公司」", pg.evaluate("() => (document.getElementById('tcRkQ')||{}).placeholder") == "搜尋公司")
        n0 = cnt(); r0 = rows()
        pg.fill("#tcRkQ", "台"); pg.wait_for_timeout(300)
        r1 = rows(); n1 = cnt()
        ok(f"{T}（{tag}）：輸入「台」後家數變少且字樣跟著變", 0 < n1 < n0 and len(r1) == n1, (n0, n1))
        ok(f"{T}（{tag}）：每列公司名都含「台」", all("台" in x[1] for x in r1), r1[:3])
        if mob:
            ok(f"{T}（手機）：輸入框全寬", pg.evaluate("() => { const i=document.getElementById('tcRkQ').getBoundingClientRect(), p=document.querySelector('.tc-srch').parentElement.getBoundingClientRect(); return i.width > p.width*0.85 }"))
        full = {x[1]: x[0] for x in r0}
        ok(f"{T}（{tag}）：排名序號維持全體名次", all(full.get(x[1], x[0]) == x[0] or x[1] not in full for x in r1) and any(x[0] != str(i + 1) for i, x in enumerate(r1)), r1[:4])
        ok(f"{T}（{tag}）：出現清除鈕", pg.evaluate("() => { const x=document.querySelector('.tc-srch .scx'); return !!x && !x.hidden }"))
        try: pg.screenshot(path=SP + f"tc_search_{'m' if mob else 'd'}.png")
        except Exception as e: print("  截圖失敗", e)
        pg.fill("#tcRkQ", "zzzz不存在"); pg.wait_for_timeout(200)
        ok(f"{T}（{tag}）：無結果顯示「找不到符合的公司」", "找不到符合的公司" in pg.inner_text("#tcRkBody"))
        pg.fill("#tcRkQ", "台"); pg.wait_for_timeout(200)
        pg.click(".tc-srch .scx"); pg.wait_for_timeout(300)
        ok(f"{T}（{tag}）：清除後恢復全部", cnt() == n0 and pg.input_value("#tcRkQ") == "" and pg.evaluate("() => document.querySelector('.tc-srch .scx').hidden"))
        # 搭配產業篩選
        pg.fill("#tcRkQ", "台"); pg.wait_for_timeout(200)
        pg.evaluate("() => { const b=[...document.querySelectorAll('.seg[data-rk=ind] button')].find(x=>x.dataset.v==='foundry'); b.click(); }"); pg.wait_for_timeout(300)
        n2 = cnt()
        ok(f"{T}（{tag}）：搭配產業篩選後搜尋字仍在且家數 ≤ 單搜尋", pg.input_value("#tcRkQ") == "台" and n2 <= n1, (n1, n2))
        # 產業分頁排序
        pg.goto(base + "#tc/odm", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        vals = lambda k: pg.evaluate("""(k) => [...document.querySelectorAll('#v-tc .tc-co')].map(a => { const sp=[...a.querySelectorAll('.tc-cof span')].find(s => s.innerText.startsWith(k)); const t=sp? sp.querySelector('b').innerText : '—'; const m=t.match(/[\\d.]+/); return m? parseFloat(m[0]) : null; })""", k)
        ok(f"{T}（{tag}）：公司卡有「分紅 X 月」欄", pg.evaluate("() => document.querySelector('#v-tc .tc-co .tc-cof').innerText.includes('分紅')"))
        for key, lab in [("週工時", "週工時"), ("底薪", "底薪"), ("分紅", "分紅月數"), ("樣本", "樣本數")]:
            pg.evaluate("(l) => [...document.querySelectorAll('.seg[data-csort] button')].find(b => b.innerText.startsWith(l)).click()", lab); pg.wait_for_timeout(250)
            v = [x for x in vals(key) if x is not None]; allv = vals(key)
            ok(f"{T}（{tag}）：按「{lab}」高→低，第一張最大且缺值在最後", v == sorted(v, reverse=True) and (None not in allv[:len(v)]), allv[:6])
            if lab == "週工時":
                try: pg.screenshot(path=SP + f"tc_sort_hours_{'m' if mob else 'd'}.png")
                except Exception as e: print("  截圖失敗", e)
            pg.evaluate("(l) => [...document.querySelectorAll('.seg[data-csort] button')].find(b => b.innerText.startsWith(l)).click()", lab); pg.wait_for_timeout(250)
            v2 = [x for x in vals(key) if x is not None]
            ok(f"{T}（{tag}）：再按一次「{lab}」反轉成低→高", v2 == sorted(v2) and v2 == v[::-1], v2[:6])
            ok(f"{T}（{tag}）：按鈕顯示 ↑", "↑" in pg.evaluate("(l) => [...document.querySelectorAll('.seg[data-csort] button')].find(b => b.innerText.startsWith(l)).innerText", lab))
        ok(f"{T}（{tag}）：選擇記進 localStorage", pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.tc.csort')).k } catch(e) { return null } }") == "n")
        # 其他產業分頁也生效
        pg.goto(base + "#tc/foundry", wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
        ok(f"{T}（{tag}）：別的產業分頁也有排序鈕", pg.evaluate("() => document.querySelectorAll('.seg[data-csort] button').length") == 5)
        if mob:
            ok(f"{T}（手機）：排序鈕列不撐出橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])

register("科技透明圈搜尋排序1031", lambda pg, b, base, code: t_tc_search(b, base, code))
