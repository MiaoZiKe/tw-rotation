# 驗收段落「通知點擊跳轉1027」（site/notices.js，鈴鐺下拉的通知卡）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-27：「這裡改點擊對應消息就連結過去」。用假的 features.json（page.route 攔截）真的操作鈴鐺：
# 點「有路由」那張卡的空白處（標題）→ location.hash 變成卡內路由、下拉關閉、該則變已讀、紅點少 1；
# 點「沒有路由」那張卡 → 不換頁、下拉仍開、該則變已讀；滑鼠移上去底色真的變。1440 與 390 各一次。
import json as _nc_json

_NC_FEATS = [
    {"id": "f-20261027-aaa", "date": "2026-10-27", "aud": "all", "title": "有路由的公告", "body": "說明文字\n去這裡看：[盤前消息](#articles/premarket)"},
    {"id": "f-20261027-bbb", "date": "2026-10-26", "aud": "all", "title": "沒路由的公告", "body": "只是一段說明，沒有任何連結。"},
]


def t_notice_click_1027(b, base, code):
    T = "通知點擊跳轉1027"
    errs = []
    for W in (1440, 390):
        mob = W <= 640
        c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_nc_json.dumps(_NC_FEATS)))
        pg = c.new_page(); pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        a = pg.get_by_role("button", name="同意並繼續")
        if a.count() and a.first.is_visible():
            a.first.click(); pg.wait_for_timeout(300)
        wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && !d.hidden && d.textContent === '2'; }", 10000)
        pg.click("#ntBell")
        wait_until(pg, "() => { const d = document.getElementById('ntDrop'); return d && !d.hidden && d.querySelectorAll('.ntitem').length === 2; }", 3000)
        ok(f"{T}（{W}）有路由的卡帶 data-route、沒路由的不帶",
           pg.evaluate("() => document.querySelector('.ntitem[data-id=f-20261027-aaa]').dataset.route") == "#articles/premarket"
           and pg.evaluate("() => document.querySelector('.ntitem[data-id=f-20261027-bbb]').dataset.route") is None)
        if not mob:
            bg0 = pg.evaluate("() => getComputedStyle(document.querySelector('.ntitem[data-id=f-20261027-bbb]')).backgroundColor")
            pg.hover(".ntitem[data-id=f-20261027-aaa] .ttl"); pg.wait_for_timeout(150)
            cur = pg.evaluate("() => getComputedStyle(document.querySelector('.ntitem[data-id=f-20261027-aaa]')).cursor")
            pg.hover(".ntitem[data-id=f-20261027-bbb] .ttl"); pg.wait_for_timeout(150)
            bg2 = pg.evaluate("() => getComputedStyle(document.querySelector('.ntitem[data-id=f-20261027-bbb]')).backgroundColor")
            ok(f"{T}（{W}）滑鼠移上去：游標手指、底色改變", cur == "pointer" and bg2 != bg0, [cur, bg0, bg2])
        # 沒路由那張：只標已讀、不換頁
        h0 = pg.evaluate("() => location.hash")
        pg.click(".ntitem[data-id=f-20261027-bbb] .ttl")
        got = wait_until(pg, "() => document.getElementById('ntDot').textContent === '1'", 3000)
        st = pg.evaluate("() => ({ hash: location.hash, open: !document.getElementById('ntDrop').hidden, unread: document.querySelector('.ntitem[data-id=f-20261027-bbb]').classList.contains('unread') })")
        ok(f"{T}（{W}）點沒路由的卡 → 不換頁、下拉還開、該則已讀、紅點 1", bool(got) and st["hash"] == h0 and st["open"] and not st["unread"], [h0, st])
        # 有路由那張：整張卡空白處也能點
        pg.click(".ntitem[data-id=f-20261027-aaa] .ttl")
        moved = wait_until(pg, "() => location.hash.startsWith('#articles/premarket')", 4000)
        st = pg.evaluate("""() => { const d = document.getElementById('ntDrop'), t = document.getElementById('ntDot');
          let r = []; try { r = JSON.parse(localStorage.getItem('tw.notice.read') || '[]'); } catch (e) {}
          return { shut: !d || d.hidden, dotHidden: t.hidden, read: r }; }""")
        ok(f"{T}（{W}）點有路由的卡 → hash 變 #articles/premarket、下拉關閉、兩則都已讀（紅點消失）",
           bool(moved) and st["shut"] and st["dotHidden"] and "f-20261027-aaa" in st["read"], [pg.evaluate("() => location.hash"), st])
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


register("通知點擊跳轉1027", lambda pg, b, base, code: t_notice_click_1027(b, base, code))
