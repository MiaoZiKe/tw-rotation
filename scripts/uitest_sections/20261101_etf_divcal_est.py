# 驗收段落「ETF行事曆預估1101」
# flake8: noqa
# Andy 11-01：「ETF 行事曆每個禮拜都要更新 到下個月」。投信還沒公告的下個月除息，依往年同期預估（etf.json 的 calendar_est）。
# 真的按「下月」鈕、真的點有預估的那一格，量畫面變了：
#   ① 月曆格內出現灰字預估（.ce.est）、狀態寫「含預估」；② 右側整月清單標題有「資料更新」；
#   ③ 點有預估的格 → 當天清單的列有 .est 與「預估」標籤；④ 手機同樣一輪、沒有橫向捲軸、沒有網頁錯誤。

def t_etf_divcal_est_1101(b, base, code):
    T = "ETF行事曆預估1101"
    errs: list[str] = []
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#etf/cal", wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, "() => !!document.querySelector('#etfCalNext')", 8000)
        ok(f"{T}（{W}）：行事曆畫出來", bool(ready))
        n_est = J("() => ((window.TwEtfPage.state.data || {}).calendar_est || []).length")
        ok(f"{T}（{W}）：etf.json 有預估清單（calendar_est）", n_est > 0, n_est)
        # 往後翻到「預估月份」：找第一筆預估的月份，按「下月」直到到那個月
        target = J("() => ((window.TwEtfPage.state.data || {}).calendar_est || [])[0].ex.slice(0, 7)")
        for _ in range(4):
            if J("() => document.querySelector('#etfCal').dataset.month") == target:
                break
            pg.click("#etfCalNext"); pg.wait_for_timeout(300)
        ok(f"{T}（{W}）：按「下月」翻到 {target}", J("() => document.querySelector('#etfCal').dataset.month") == target)
        ok(f"{T}（{W}）：月曆格內有灰字預估（.ce.est）", J("() => document.querySelectorAll('#etfCalGrid .ce.est').length") > 0)
        ok(f"{T}（{W}）：狀態列寫「含預估」", "含預估" in J("() => document.querySelector('#etfCalStatus').textContent"), J("() => document.querySelector('#etfCalStatus').textContent"))
        ok(f"{T}（{W}）：整月清單標題有「資料更新：」", "資料更新：" in J("() => document.querySelector('#etfCalList .lt').textContent"))
        ok(f"{T}（{W}）：整月清單有預估列且標「預估」", J("() => document.querySelectorAll('#etfCalList tr.est .estb').length") > 0)
        before = J("() => document.querySelector('#etfCalList').innerHTML.length")
        cell = pg.locator("#etfCalGrid .cald.has:has(.ce.est)").first
        cell.click(); pg.wait_for_timeout(400)
        ok(f"{T}（{W}）：點有預估的那格 → 右側換成當天清單、列上有「預估」", J("() => !!document.querySelector('#etfDayTbl') && document.querySelectorAll('#etfDayTbl tr.est .estb').length > 0")
           and J("() => document.querySelector('#etfCalList').innerHTML.length") != before)
        if W == 390:
            ok(f"{T}（390）：沒有橫向捲軸", J("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF行事曆預估1101", lambda pg, b, base, code: t_etf_divcal_est_1101(b, base, code))
