# 驗收段落「流向驗證管理者限定」—— Andy 11-02：「流向驗證 推上去 但須要先隱藏 不給其他人看」。
# 做法同交易練習室：html 掛 .fc-adm 才顯示側欄／手機抽屜入口；非管理者直接開 #flowcheck 導回 #overview。
# 本機 127.0.0.1 用 window.TW_LAB_OVERRIDE（true／false）模擬管理者／一般人（lab.js、flowcheck.js 共用的覆寫）。
# flake8: noqa

def t_flowcheck_admin(b, base):
    import json as _json, re as _re, sys as _sys
    _sys.path.insert(0, str(SITE.parent / "scripts"))
    import _fc3_fake as FK
    T = "流向驗證管理者限定"
    FILES = FK.build(); FILES["next_wave.json"] = FK.next_wave()

    def route(r):
        m = _re.search(r"/data/flowcheck/(.+?\.json)", r.request.url)
        if m and m.group(1) in FILES:
            r.fulfill(status=200, content_type="application/json", body=_json.dumps(FILES[m.group(1)], ensure_ascii=False))
        elif m:
            r.fulfill(status=404, body="")
        else:
            r.continue_()

    def open_page(W, H, adm, h="#overview"):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script(f"window.TW_LAB_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('fc.tour4','1');localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}}catch(e){{}}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctx.route("**/data/flowcheck/**", route)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.goto(base + h, wait_until="load")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click()
        pg.wait_for_timeout(1500)
        return ctx, pg

    TAB = "() => { const t = document.querySelector('#tabs .tab[data-view=flowcheck], .tab[data-view=flowcheck]'); return !!t && t.getBoundingClientRect().width > 0 && getComputedStyle(t).display !== 'none'; }"
    # 站主（管理者）：桌機看得到側欄項目、點得進去、頁面有畫
    ctx, pg = open_page(1440, 900, True)
    ok(f"[{T}] 站主：html 有 fc-adm、桌機側欄看得到「流向驗證」", pg.evaluate("() => document.documentElement.classList.contains('fc-adm')") and pg.evaluate(TAB))
    pg.evaluate("() => { location.hash = '#flowcheck'; }"); wait_until(pg, "() => document.querySelectorAll('#fc4Cols .fc4-row').length >= 6", 15000); pg.wait_for_timeout(300)
    ok(f"[{T}] 站主：開 #flowcheck 停在流向驗證、第一屏三步驟有畫", pg.evaluate("() => location.hash.indexOf('#flowcheck') === 0") and pg.evaluate("() => document.querySelectorAll('#fc4Cols .fc4-row').length") == 6)
    ctx.close()
    # 站主：手機抽屜列得出來
    ctx, pg = open_page(390, 844, True)
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 站主：手機抽屜有「流向驗證」", pg.evaluate("() => [...document.querySelectorAll('#m4Drawer [data-v], .m4item')].some(e => e.dataset.v === 'flowcheck')"))
    ctx.close()
    # 一般人：桌機側欄看不到；直接開網址導回總覽
    ctx, pg = open_page(1440, 900, False)
    ok(f"[{T}] 一般人：html 沒有 fc-adm、桌機側欄看不到「流向驗證」", (not pg.evaluate("() => document.documentElement.classList.contains('fc-adm')")) and not pg.evaluate(TAB))
    pg.evaluate("() => { location.hash = '#flowcheck'; }"); pg.wait_for_timeout(500)
    pg.evaluate("() => window.dispatchEvent(new Event('tw:account'))"); pg.wait_for_timeout(1500)      # 帳號確認完成（不是管理者）
    ok(f"[{T}] 一般人：直接開 #flowcheck 被導回 #overview、沒有畫出流向驗證內容", pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => document.querySelectorAll('#fc4Cols .fc4-row').length") == 0, pg.evaluate("() => location.hash"))
    ctx.close()
    ctx, pg = open_page(1440, 900, False, h="#flowcheck")
    pg.wait_for_timeout(6500)                                                                           # 沒有帳號事件時 6 秒保底
    ok(f"[{T}] 一般人：網址一開始就是 #flowcheck（沒登入）6 秒內導回 #overview", pg.evaluate("() => location.hash") == "#overview", pg.evaluate("() => location.hash"))
    ctx.close()
    # 一般人：手機抽屜不列
    ctx, pg = open_page(390, 844, False)
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 一般人：手機抽屜沒有「流向驗證」（DOM 裡也沒有）", pg.evaluate("() => !document.querySelector('.m4item[data-v=flowcheck]') && ![...document.querySelectorAll('#m4Drawer *')].some(e => e.dataset && e.dataset.v === 'flowcheck' && e.getBoundingClientRect().width > 0)"))
    ctx.close()


register("流向驗證管理者限定", lambda pg, b, base, code: t_flowcheck_admin(b, base))
