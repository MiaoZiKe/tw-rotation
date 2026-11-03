# 驗收段落「科技透明圈公開版1103」（官方薪資，site/tc/pub.js）
# 由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx() 直接可用。
# flake8: noqa
#
# 驗收的是「畫面真的因此改變了」：
#   ① 訪客（TW_TC_OVERRIDE=false）：#tc 畫出官方薪資排行；沒有網友樣本分頁、沒有管理者連結；打 #tc/foundry 被導回 #tc；頁面沒有 #stock/ 連結
#   ② 排序：點「中位數」第一列的數字真的變（降序→升序）、再點「公司」順序真的換
#   ③ 產業篩選：點 IC 設計 → 列數等於該鈕標的數字、全部列都是該產業；「全部」回到原本列數
#   ④ 公司卡：點公司名 → #tc/co/代號，KPI 與同產業排名在；「← 回官方薪資排行」真的回清單
#   ⑤ 頁底：「資料來源與免責聲明」固定在，含 GoodJob／Dcard／PTT 只作參考連結的字樣
#   ⑥ 管理者（TW_TC_OVERRIDE=true）：多出「網友樣本分頁」連結，點了進到原本的 #tc/foundry 公司卡
#   ⑦ 次數：訪客每日 5 次，第 6 次點公司沒有導頁；註冊會員 15 次（features.js／plan_presets.js 一致）
#   ⑧ 手機 390：不橫向捲動、整頁 ≤3 屏、字 ≥ 11px、產業鈕可橫向拖
# ⚠ 資料 tc/official_seed.json 是人工整理的種子；之後 pipeline 產出 data/tc_salary.json 會蓋過，列數會變，所以只驗關係不驗死數字。


def t_tc_pub_1103(b, base, code):
    T = "科技透明圈公開版1103"
    errs: list[str] = []

    def ctx(adm, width=1440, plan=None):
        if plan:
            c = _p12_ctx(b, plan=plan, width=width)
            c.add_init_script(f"window.TW_TC_OVERRIDE={'true' if adm else 'false'};")
        else:
            c = b.new_context(viewport={"width": width, "height": 900})
            c.add_init_script(f"window.TW_TC_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('tw.tour','done')}}catch(e){{}}")
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        return c, pg

    rows = lambda pg: pg.evaluate("() => document.querySelectorAll('#v-tc .tcp-row').length")
    first = lambda pg: pg.evaluate("() => { const r = document.querySelector('#v-tc .tcp-row'); return r ? r.dataset.code + '|' + r.querySelector('td.strong').innerText : '' }")

    # ---------------------------------------------------------------- ① 訪客
    c, pg = ctx(False)
    pg.goto(base + "#tc", wait_until="load"); pg.wait_for_timeout(1500)
    wait_until(pg, "() => document.querySelectorAll('#v-tc .tcp-row').length > 0", 8000)
    n0 = rows(pg)
    ok(f"{T}：訪客打開 #tc 看到官方薪資排行（{n0} 家）", n0 >= 5, n0)
    ok(f"{T}：訪客看不到網友樣本分頁與管理者連結", pg.evaluate("() => !document.querySelector('#v-tc .tc-tabs, #v-tc .tc-co, #v-tc .tcp-adm')"))
    ok(f"{T}：整頁沒有任何連到個股頁（#stock/）的連結", pg.evaluate("() => !document.querySelector('#v-tc a[href*=\"#stock\"]')"))
    ok(f"{T}：側欄「科技透明圈」入口對訪客顯示", pg.evaluate("() => { const e = document.querySelector('.tab[data-view=\"tc\"]'); return !!e && e.getClientRects().length > 0; }"))
    # ⑤ 頁底
    lg = pg.inner_text("#v-tc .tcp-legal")
    ok(f"{T}：頁底固定「資料來源與免責聲明」＋網友平台僅作參考連結＋政府資料開放授權", "資料來源與免責聲明" in lg and "GoodJob、Dcard、PTT" in lg and "不代表任何單一職位" in lg and "政府資料開放授權條款" in lg, lg[:60])
    # ② 排序
    f0 = first(pg)
    pg.click("#v-tc th[data-sk=median] button"); pg.wait_for_timeout(250)
    f1 = first(pg)
    ok(f"{T}：點「中位數」→ 升序，第一列真的換（{f0} → {f1}）", f0 != f1 and f0 and f1, (f0, f1))
    mv = pg.evaluate("() => [...document.querySelectorAll('#v-tc .tcp-row td.strong')].map(e => parseFloat(e.innerText.replace(/,/g,''))).filter(x => !isNaN(x))")
    ok(f"{T}：升序後中位數由小到大排列", mv == sorted(mv), mv[:6])
    pg.click("#v-tc th[data-sk=name] button"); pg.wait_for_timeout(250)
    ok(f"{T}：點「公司」→ 第一列又換", first(pg) != f1, first(pg))
    # ③ 產業篩選
    pg.click("#v-tc .tcp-inds button[data-ind=icdesign]"); pg.wait_for_timeout(250)
    badge = pg.evaluate("() => +document.querySelector('#v-tc .tcp-inds button.on small').innerText")
    ok(f"{T}：點「IC 設計」→ 列數＝鈕上標的 {badge}、比全部少", rows(pg) == badge and badge < n0, (rows(pg), badge, n0))
    ok(f"{T}：篩選後每一列都是 IC 設計", pg.evaluate("() => [...document.querySelectorAll('#v-tc .tcp-row td:nth-child(2)')].every(e => e.innerText === 'IC 設計')"))
    ok(f"{T}：顯示數字（#tcpCount）跟著變", pg.evaluate("() => +document.querySelector('#tcpCount b').innerText") == badge)
    pg.click("#v-tc .tcp-inds button[data-ind='']"); pg.wait_for_timeout(250)
    ok(f"{T}：點「全部」→ 列數回到 {n0}", rows(pg) == n0, rows(pg))
    # 「?」
    pg.click("#v-tc .tcp-q"); pg.wait_for_timeout(150)
    ok(f"{T}：「?」點開有怎麼用說明、點背景關閉", pg.evaluate("() => !document.querySelector('.tcp-pop').hidden && /中位數/.test(document.querySelector('.tcp-pop').innerText)"))
    pg.click("#v-tc .tcp-sub"); pg.wait_for_timeout(150)
    ok(f"{T}：點旁邊後說明收起", pg.evaluate("() => document.querySelector('.tcp-pop').hidden"))
    # ④ 公司卡
    pg.click("#v-tc th[data-sk=median] button"); pg.wait_for_timeout(200)
    top = pg.evaluate("() => document.querySelector('#v-tc .tcp-row').dataset.code")
    pg.click(f"#v-tc .tcp-row[data-code='{top}'] a.tcp-go"); pg.wait_for_timeout(500)
    ok(f"{T}：點公司名 → 網址 #tc/co/{top}、畫出四格 KPI 與同產業排名", pg.evaluate("() => location.hash") == f"#tc/co/{top}" and pg.evaluate("() => document.querySelectorAll('#v-tc .tcp-kpis > div').length") == 4 and pg.evaluate("() => /排第/.test(document.querySelector('#v-tc .tcp-peerh').innerText)"))
    ok(f"{T}：公司卡自己的那一條標紅（.me）、頁底免責還在、沒有個股頁連結", pg.evaluate("() => !!document.querySelector('#v-tc .tcp-bar.me') && !!document.querySelector('#v-tc .tcp-legal') && !document.querySelector('#v-tc a[href*=\"#stock\"]')"))
    pg.click("#tcpBack"); pg.wait_for_timeout(500)
    ok(f"{T}：「← 回官方薪資排行」真的回到清單", pg.evaluate("() => location.hash") == "#tc" and rows(pg) >= 1)
    # 訪客打網友樣本路徑 → 被導回（等身分確定：tw:account 或 6 秒逾時）
    pg.evaluate("() => { location.hash = '#tc/foundry'; }")
    got = wait_until(pg, "() => location.hash === '#tc'", 9000)
    ok(f"{T}：訪客直接打 #tc/foundry → 被導回 #tc、仍看不到網友樣本", bool(got) and pg.evaluate("() => !document.querySelector('#v-tc .tc-co')"), pg.evaluate("() => location.hash"))
    c.close()

    # ---------------------------------------------------------------- ⑥ 管理者
    c, pg = ctx(True)
    pg.goto(base + "#tc", wait_until="load"); pg.wait_for_timeout(1500)
    wait_until(pg, "() => document.querySelectorAll('#v-tc .tcp-row').length > 0", 8000)
    ok(f"{T}（管理者）：同一頁多一條「網友樣本分頁」連結", pg.evaluate("() => !!document.querySelector('#v-tc .tcp-adm a[href=\"#tc/foundry\"]')"))
    pg.click("#v-tc .tcp-adm a"); pg.wait_for_timeout(1500)
    wait_until(pg, "() => document.querySelectorAll('#v-tc .tc-co').length > 0", 8000)
    ok(f"{T}（管理者）：點了進原本的網友樣本公司卡（#tc/foundry）", pg.evaluate("() => location.hash") == "#tc/foundry" and pg.evaluate("() => document.querySelectorAll('#v-tc .tc-co').length") >= 1)
    pg.click("#v-tc .tc-tabs a[data-ind=pub]"); pg.wait_for_timeout(800)
    ok(f"{T}（管理者）：網友樣本頁的「官方薪資（公開版）」分頁回得去", pg.evaluate("() => location.hash") == "#tc" and rows(pg) >= 1)
    c.close()

    # ---------------------------------------------------------------- ⑦ 次數
    for plan, lim in (("guest", 5), ("free", 15)):
        c, pg = ctx(False, plan=plan)
        pg.goto(base + "#tc", wait_until="domcontentloaded")
        wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        wait_until(pg, "() => document.querySelectorAll('#v-tc .tcp-row').length > 0", 8000)
        pg.wait_for_timeout(400)
        ok(f"{T}（{plan}）：tc.click 上限＝{lim}（範本沒寫也照 features.js）", pg.evaluate("() => TwPerm.lim('tc.click')") == lim, pg.evaluate("() => TwPerm.lim('tc.click')"))
        codes = pg.evaluate("() => [...document.querySelectorAll('#v-tc .tcp-row')].map(r => r.dataset.code)")
        n_ok = 0
        for cd in (codes * 3)[:lim]:
            pg.evaluate("() => { location.hash = '#tc'; }"); pg.wait_for_timeout(250)
            pg.locator(f"#v-tc .tcp-row[data-code='{cd}'] a.tcp-go").click(); pg.wait_for_timeout(250)
            if pg.evaluate("() => location.hash").startswith("#tc/co/"):
                n_ok += 1
        ok(f"{T}（{plan}）：前 {lim} 次點公司都進得了公司卡", n_ok == lim, n_ok)
        pg.evaluate("() => { location.hash = '#tc'; }"); pg.wait_for_timeout(300)
        ok(f"{T}（{plan}）：用完後公司連結反灰（aria-disabled）", pg.evaluate("() => document.querySelector('#v-tc .tcp-row a.tcp-go').getAttribute('aria-disabled') === 'true'"))
        pg.locator("#v-tc .tcp-row a.tcp-go").first.click(force=True); pg.wait_for_timeout(400)
        ok(f"{T}（{plan}）：第 {lim + 1} 次沒有導頁（用完被擋）", pg.evaluate("() => location.hash") == "#tc", pg.evaluate("() => location.hash"))
        ok(f"{T}（{plan}）：用完有一行小字提示", pg.evaluate("() => /已用完/.test((document.getElementById('v-tc')||{}).innerText || '')"))
        c.close()
    # 站主不受限：管理者連點 7 次都進得去
    c, pg = ctx(True)
    pg.goto(base + "#tc", wait_until="load"); wait_until(pg, "() => document.querySelectorAll('#v-tc .tcp-row').length > 0", 8000)
    cnt = 0
    for i in range(7):
        pg.evaluate("() => { location.hash = '#tc'; }"); pg.wait_for_timeout(200)
        pg.locator("#v-tc .tcp-row a.tcp-go").first.click(); pg.wait_for_timeout(200)
        cnt += pg.evaluate("() => location.hash").startswith("#tc/co/")
    ok(f"{T}（站主）：連點 7 次公司都進得去，不受次數限制", cnt == 7, cnt)
    c.close()

    # ---------------------------------------------------------------- ⑧ 手機 390
    c, pg = ctx(False, width=390)
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto(base + "#tc", wait_until="load"); wait_until(pg, "() => document.querySelectorAll('#v-tc .tcp-row').length > 0", 8000); pg.wait_for_timeout(600)
    ok(f"{T}（手機）：不橫向捲動", pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
    ok(f"{T}（手機）：整頁 ≤ 3 屏", pg.evaluate("() => document.documentElement.scrollHeight <= 844 * 3"), pg.evaluate("() => document.documentElement.scrollHeight"))
    small = pg.evaluate("() => [...document.querySelectorAll('#v-tc .tcp *')].filter(e => e.children.length === 0 && e.textContent.trim() && e.getClientRects().length && parseFloat(getComputedStyle(e).fontSize) < 11).map(e => e.textContent.trim().slice(0, 12))")
    ok(f"{T}（手機）：沒有小於 11px 的字", not small, small[:5])
    ok(f"{T}（手機）：隱藏欄位（產業／員工數／來源）收起、中位數與平均還在", pg.evaluate("() => { const h = [...document.querySelectorAll('#v-tc .tcp-tbl th')].filter(e => e.getClientRects().length).map(e => e.innerText.replace(/[▲▼]/g,'').trim()); return h.length <= 4 && h.some(x => /中位數/.test(x)); }"))
    ok(f"{T}（手機）：產業鈕列可橫向拖（捲動寬度大於可視寬度）", pg.evaluate("() => { const e = document.querySelector('#v-tc .tcp-inds'); return e.scrollWidth > e.clientWidth; }"))
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("科技透明圈公開版1103", lambda pg, b, base, code: t_tc_pub_1103(b, base, code))
