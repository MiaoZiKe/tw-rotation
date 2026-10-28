# 驗收段落「交易練習室最終版1031」：台指期回測預設 5Y、切 All 後寫出「資金不足 1 口保證金，之後停止交易」、
# 歷史回測 All 的 K 線可視範圍涵蓋整段、損益圖工具列不被右下角比比客服鈕蓋住（桌機與手機）。 flake8: noqa


def t_lab_final(b, base, code):
    T = "交易練習室最終版1031"
    _ok = globals()["ok"]
    for w, h, mob in [(1440, 900, False), (390, 844, True)]:
        kw = dict(viewport={"width": w, "height": h})
        if mob:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        c = b.new_context(**kw)
        c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
        pg = c.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#lab/fut", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
        pg.click("#labFSub button[data-f='bt']"); pg.wait_for_timeout(3500)
        _ok(f"{T}（{w}）：台指期回測預設期間 5Y", pg.evaluate("() => window.TwLab.state().fut.range") == "5Y", None)
        n5 = pg.evaluate("() => window.TwLab.state().fut.res.stats.n")
        pg.evaluate("() => document.querySelector(\"#labRng button[data-r='All']\").click()"); pg.wait_for_timeout(2500)
        nA = pg.evaluate("() => window.TwLab.state().fut.res.stats.n")
        tx = pg.inner_text(".lab-calls") if pg.locator(".lab-calls").count() else ""
        _ok(f"{T}（{w}）：切 All 後交易筆數改變且寫出「起資金不足 1 口保證金，之後停止交易」", n5 != nA and "起資金不足 1 口保證金，之後停止交易" in tx, (n5, nA, tx))
        pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
        vr = pg.evaluate("() => { const t = window.TwLab.charts.k.timeScale().getVisibleLogicalRange(), S = window.TwLab.state().bt; return [t.from, t.to, S.res.from, S.B.n]; }")
        _ok(f"{T}（{w}）：All 的 K 線初始可視範圍涵蓋整段", vr[0] <= vr[2] + 1 and vr[1] >= vr[3] - 1, vr)
        pg.evaluate("() => document.getElementById('labBHw').scrollIntoView({block:'end'})"); pg.wait_for_timeout(500)
        hit = pg.evaluate("() => { const a = document.getElementById('labBHw').getBoundingClientRect(); return [...document.querySelectorAll('body *')].filter(e => getComputedStyle(e).position === 'fixed' && e.offsetWidth > 30 && e.offsetWidth < 150 && e.offsetParent !== null).some(e => { const r = e.getBoundingClientRect(); return !(r.right < a.left || r.left > a.right || r.bottom < a.top || r.top > a.bottom); }); }")
        _ok(f"{T}（{w}）：「疊上買進持有」捲到畫面底也不被固定的客服鈕蓋住", not hit, None)
        _ok(f"{T}（{w}）：無 JS 錯誤", not errs, errs[:3])
        c.close()


register("交易練習室最終版1031", lambda pg, b, base, code: t_lab_final(b, base, code))
