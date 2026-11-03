# 驗收段落「預覽專用失效1104」—— 正式站（非 /preview/ 路徑）上，預覽專用的東西必須不存在
# Andy 11-04：三樣功能合併上正式站；#promo-demo 路由、預覽強制跳公告／問卷只准在網址含 /preview/ 時生效。
# flake8: noqa


def t_preview_dead_1104(b, base, code):
    T = "預覽專用失效1104"
    errs: list[str] = []
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        ok(f"{T}（{W}）測試用網址不含 /preview/", "/preview/" not in base)
        pg.goto(base + "#promo-demo", wait_until="networkidle"); pg.wait_for_timeout(1500)
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(400)
        ok(f"{T}（{W}）正式站 #promo-demo 路由不存在（沒有展示頁）", not pg.evaluate("() => !!document.getElementById('v-promodemo')"))
        pg.goto(base + "#overview", wait_until="networkidle"); pg.wait_for_timeout(2500)
        ok(f"{T}（{W}）正式站首頁（未登入）不自動跳公告", not pg.evaluate("() => !!document.getElementById('pwOv')"))
        ok(f"{T}（{W}）正式站首頁（未登入）不自動跳問卷", not pg.evaluate("() => !!document.querySelector('#svOv')"))
        ok(f"{T}（{W}）正式站沒有 TwPromo 展示掛鉤的 demo 路由", not pg.evaluate("() => (window.TwSubRoutes||[]).some(f => { try { return !!f('promo-demo'); } catch (e) { return false; } })"))
        c.close()
    ok(f"{T}：無 JS 錯誤 {errs[:2]}", not errs)


register("預覽專用失效1104", lambda pg, b, base, code: t_preview_dead_1104(b, base, code))
