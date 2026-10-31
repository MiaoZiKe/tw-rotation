# 驗收段落「財經日曆下月預估1101」
# flake8: noqa
# Andy 11-01：「財經日曆也一樣每週更新」——下個月不准整月空白。真的按「下月」、真的切三個分類、真的點預估標籤：
#   ① 每個分類翻到下個月都有標籤（已公告、預估或期限）；② 公司法說翻到有預估的月份 → 灰字虛線標籤（.chip.est）含「預估」；
#   ③ 點預估標籤 → 右側面板徽章是「預估」；④ 頁底有「資料更新：日期」；⑤ 手機一樣、無橫向捲軸、無網頁錯誤。

def t_fin_calendar_next_month_1101(b, base, code):
    T = "財經日曆下月預估1101"
    errs: list[str] = []
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#earnings", wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, "() => !!document.querySelector('#earnNext') && !!document.querySelector('#earnGrid .chip, #earnGrid .ed')", 8000)
        ok(f"{T}（{W}）：財經日曆畫出來", bool(ready))
        ok(f"{T}（{W}）：頁底有「資料更新：」日期", "資料更新：" in J("() => document.querySelector('#earnDisc').textContent"), J("() => document.querySelector('#earnDisc').textContent"))
        nxt = J("() => { const c = (window.TwEarnings.state.data || {}).coverage || {}; return Object.keys(c).sort().pop(); }")
        ok(f"{T}（{W}）：earnings.json 有 coverage 且含下個月", bool(nxt), nxt)
        # 分頁 rep → conf → fed，各自翻到下個月，量標籤數
        for tab, lab in (("rep", "公司財報"), ("conf", "公司法說"), ("fed", "FED 消息")):
            pg.click(f"#earnFilt button[data-v={tab}]"); pg.wait_for_timeout(250)
            for _ in range(6):
                if J("() => document.querySelector('#earnCalCard').dataset.month") == nxt:
                    break
                pg.click("#earnNext"); pg.wait_for_timeout(250)
            n = J("() => +document.querySelector('#earnCalCard').dataset.n")
            ok(f"{T}（{W}）：{lab} 翻到 {nxt}，月曆有事件（不是整月空白）", n > 0, n)
            if tab == "conf":
                n_est = J("() => document.querySelectorAll('#earnGrid .chip.est').length")
                ok(f"{T}（{W}）：公司法說下月有灰字預估標籤（.chip.est）", n_est > 0, n_est)
                if n_est:
                    ok(f"{T}（{W}）：預估標籤上有「預估」字", "預估" in J("() => document.querySelector('#earnGrid .chip.est .eb').textContent"))
                    before = J("() => document.querySelector('#earnPanel').innerHTML.length")
                    pg.locator("#earnGrid .chip.est").first.click(); pg.wait_for_timeout(400)
                    ok(f"{T}（{W}）：點預估標籤 → 右側換成該公司、徽章寫「預估」",
                       J("() => document.querySelector('#earnPanel').innerHTML.length") != before
                       and "預估" in J("() => (document.querySelector('#earnPanel .badge')||{}).textContent||''"))
        if W == 390:
            ok(f"{T}（390）：沒有橫向捲軸", J("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("財經日曆下月預估1101", lambda pg, b, base, code: t_fin_calendar_next_month_1101(b, base, code))
