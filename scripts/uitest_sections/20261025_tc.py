# 驗收段落「科技透明圈1025」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# ===================================================================== 科技透明圈1025
# 路由 #tc → #tc/<產業> → #tc/<產業>/<公司>。一律驗「畫面真的因此改變了」：
#   ① 公司卡篩選：每組篩選按下去，符合的公司數／職位數真的變；清除後回到全部
#   ② 公司頁：職位表筆數隨篩選變；點欄名排序後順序真的變；來源欄每列都有、頁尾有免責字樣
#   ③ 「?」點開有說明、點背景關閉；切產業後篩選回 Default
#   ④ 手機 390：不橫向捲動；篩選鈕收合、點了才展開；職位轉卡片
# ⚠ 資料檔 site/tc/json/foundry.json 由別人產出；還不存在時整段標「略過」不是紅燈。


def t_tc_1025(b, base, code):
    T = "科技透明圈1025"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#tc/foundry", wait_until="load"); pg.wait_for_timeout(1800)
    if not pg.evaluate("() => document.querySelectorAll('#v-tc .tc-co').length"):
        print(f"  ⏭ {T}：foundry.json 還沒有資料，略過"); c.close(); return
    cnt = lambda: pg.evaluate("() => document.querySelectorAll('#v-tc .tc-co').length")
    n0 = cnt()
    ok(f"{T}：#tc/foundry 畫出公司卡與五組篩選", n0 >= 1 and pg.evaluate("() => document.querySelectorAll('#v-tc .tc-fbar .seg').length") == 5, n0)
    ok(f"{T}：頁尾免責字樣在", "GoodJob、Dcard、PTT" in pg.inner_text("#v-tc .tc-foot"))
        # ⑤ 2026-10-25 公司卡新資訊：六格摘要＋福利／認股／風氣一行；缺值顯示「—」（不留空白）
    ok(f"{T}：公司卡有 底薪／分紅月數／年薪總月數／分紅發放／加班／出差 六格", pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-co')].every(c => { const t=[...c.querySelectorAll('.tc-kv span')].map(e=>e.innerText).join('|'); return ['底薪','分紅月數','年薪總月數','分紅發放','加班','出差'].every(k=>t.includes(k)); })"))
    ok(f"{T}：公司卡有 福利／認股／風氣 摘要且沒有空格子", pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-co')].every(c => c.querySelectorAll('.tc-sm').length===3 && [...c.querySelectorAll('.tc-kv b')].every(b=>b.innerText.trim()))"))
    # ① 每組篩選：點最嚴格那顆，數字必須 <= 原本，且至少有一組真的讓筆數變少；點完 .on 真的移動
    shrunk = 0
    for k in ["hours", "base", "bonus", "annual", "ot"]:
        last = pg.evaluate(f"() => document.querySelectorAll('#v-tc .seg[data-fk={k}] button').length") - 1
        pg.click(f"#v-tc .seg[data-fk={k}] button[data-i='{last}']"); pg.wait_for_timeout(250)
        on = pg.evaluate(f"() => document.querySelector('#v-tc .seg[data-fk={k}] button.on').dataset.i")
        n = cnt()
        ok(f"{T}：篩選「{k}」最後一顆 → 該鈕反白、公司數不增加", on == str(last) and n <= n0, (n0, n))
        if n < n0: shrunk += 1
        pg.click("#v-tc .tc-clear"); pg.wait_for_timeout(250)
        ok(f"{T}：清除篩選 → 公司數回到 {n0}", cnt() == n0, cnt())
    ok(f"{T}：至少一組篩選真的讓公司變少", shrunk >= 1, shrunk)
    # 組合：進公司頁看職位表
    pg.click("#v-tc .tc-co >> nth=0"); pg.wait_for_timeout(600)
    rows = lambda: pg.evaluate("() => document.querySelectorAll('#v-tc .tc-row').length")
    r0 = rows()
    ok(f"{T}：點公司卡 → 路由變 #tc/foundry/<公司>、出現職位表", "#tc/foundry/" in pg.url and r0 >= 1, (pg.url, r0))
    ok(f"{T}：每一列都有來源與信心度", pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row')].every(r => r.querySelector('.tc-src').innerText.trim().length > 2 && r.querySelector('.tc-conf').innerText.trim())"))
    ok(f"{T}：職位表有 學歷／年薪總月數／分紅發放／出差 欄", pg.evaluate("() => { const t=[...document.querySelectorAll('#v-tc .tc-tbl th')].map(e=>e.innerText).join('|'); return ['學歷','年薪總月數','分紅發放','出差'].every(k=>t.includes(k)); }"))
    ok(f"{T}：每一列的學歷欄有值（碩士或「—」）", pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row .tc-deg')].every(e => e.innerText.trim().length>0)"))
    pg.click("#v-tc .seg[data-fk=ot] button[data-i='3']"); pg.wait_for_timeout(250)
    r1 = rows()
    ok(f"{T}：公司頁篩選加班「經常」→ 職位數真的變少且每列都是經常", 0 <= r1 < r0 and pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row .tc-ot')].every(e => e.innerText.includes('經常'))"), (r0, r1))
    pg.click("#v-tc .tc-clear"); pg.wait_for_timeout(250)
    first = lambda: pg.evaluate("() => (document.querySelector('#v-tc .tc-row .tc-role b')||{}).innerText")
    f0 = first()
    pg.click("#v-tc th[data-sk=annual]"); pg.wait_for_timeout(200); a1 = pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row td.tc-big')].map(e => parseFloat(e.innerText))")
    pg.click("#v-tc th[data-sk=annual]"); pg.wait_for_timeout(200); a2 = pg.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row td.tc-big')].map(e => parseFloat(e.innerText))")
    ok(f"{T}：點「年薪」欄名兩次 → 排序方向真的反過來", a1 != a2 or len(set(a1)) <= 1, (a1, a2))
    # ③ ? 說明
    pg.click("#v-tc .tc-q"); pg.wait_for_timeout(200)
    ok(f"{T}：點「?」→ 說明出現", pg.is_visible("#v-tc .tc-pop"))
    pg.mouse.click(5, 450); pg.wait_for_timeout(200)
    ok(f"{T}：點背景 → 說明收起", not pg.is_visible("#v-tc .tc-pop"))
    pg.click("#tcBack"); pg.wait_for_timeout(500)
    ok(f"{T}：返回 → 回公司列表", cnt() == n0)
    # 切產業回 Default；空產業顯示尚無資料不留黑方塊
    pg.click("#v-tc .seg[data-fk=hours] button[data-i='1']"); pg.wait_for_timeout(200)
    pg.click("#v-tc .tc-tabs a[data-ind=memory]"); pg.wait_for_timeout(600)
    ok(f"{T}：切產業 → 篩選回 Default（沒有反白的非『全部』鈕）", pg.evaluate("() => document.querySelectorAll('#v-tc .seg button.on:not([data-i=\"0\"])').length") == 0 and "#tc/memory" in pg.url)
    errs_pg = list(errs)
    c.close()
    # ④ 手機
    c2 = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c2.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    p2 = c2.new_page(); p2.on("pageerror", lambda e: errs.append(str(e)))
    p2.goto(base + "#tc/foundry", wait_until="load"); p2.wait_for_timeout(2000)
    ok(f"{T}（390）：不橫向捲動", p2.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 1)
    ok(f"{T}（390）：篩選預設收起，點「篩選」才展開", (not p2.is_visible("#v-tc .tc-fgrp")) and p2.is_visible("#v-tc .tc-ftog"))
    p2.click("#v-tc .tc-ftog"); p2.wait_for_timeout(250)
    ok(f"{T}（390）：展開後五組篩選看得到", p2.is_visible("#v-tc .tc-fgrp") and p2.evaluate("() => document.querySelectorAll('#v-tc .tc-fgrp .seg').length") == 5)
    p2.click("#v-tc .tc-co >> nth=0"); p2.wait_for_timeout(600)
    ok(f"{T}（390）：公司頁職位轉卡片、無橫向捲動", p2.evaluate("() => getComputedStyle(document.querySelector('#v-tc .tc-row')).display") == "grid" and p2.evaluate("() => document.documentElement.scrollWidth - window.innerWidth") <= 1)
    ok(f"{T}（390）：字級不小於 11px", p2.evaluate("() => [...document.querySelectorAll('#v-tc .tc-row *, #v-tc .tc-foot')].every(e => !e.childElementCount && !e.innerText.trim() || parseFloat(getComputedStyle(e).fontSize) >= 11)"))
    c2.close()
    # ⑥ 只限管理者：非管理者（訪客／Free／Plus／Pro 都是 admin 不成立）看不到入口、#tc 被導回總覽
    for tag, vp, mob in [("桌機", {"width": 1440, "height": 900}, False), ("手機", {"width": 390, "height": 844}, True)]:
        c3 = b.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
        c3.add_init_script("window.TW_TC_OVERRIDE=false;try{localStorage.setItem('tw.tour','done')}catch(e){}")
        p3 = c3.new_page(); p3.on("pageerror", lambda e: errs.append(str(e)))
        p3.goto(base + "#tc/foundry", wait_until="load"); p3.wait_for_timeout(1800)
        ok(f"{T}（非管理者・{tag}）：#tc 被導回總覽", p3.evaluate("() => location.hash") == "#overview", p3.url)
        ok(f"{T}（非管理者・{tag}）：導覽列看不到「科技透明圈」", p3.evaluate("() => [...document.querySelectorAll('.tab[data-view=tc], a[href=\"#tc\"]')].every(e => e.offsetParent === null)"))
        ok(f"{T}（非管理者・{tag}）：頁面沒畫公司卡", p3.evaluate("() => document.querySelectorAll('#v-tc .tc-co').length") == 0)
        c3.close()
    c4 = b.new_context(viewport={"width": 1440, "height": 900})
    c4.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    p4 = c4.new_page(); p4.goto(base + "#overview", wait_until="load"); p4.wait_for_timeout(1500)
    ok(f"{T}（管理者）：導覽列看得到「科技透明圈」", p4.evaluate("() => [...document.querySelectorAll('.tab[data-view=tc]')].some(e => e.offsetParent !== null)"))
    c4.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:4])


register("科技透明圈1025", lambda pg, b, base, code: t_tc_1025(b, base, code))
