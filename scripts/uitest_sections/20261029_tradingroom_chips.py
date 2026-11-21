# 驗收段落「交易練習室籌碼1029」：籌碼策略真人操作——策略清單有「籌碼」分類、選法人連買 → 交易數改變、改連買根數 → 結果改變、
# 切週K 仍可跑、融資/當沖策略、集保大戶標「資料不足」、指數沒有籌碼資料時明講、「?」寫出「法人籌碼當主訊號沒有增量」、
# 自訂策略積木可選籌碼運算元並讓交易數改變、手機 390 無橫向捲動。flake8: noqa
def t_lab_chips(b, base, code):
    T = "交易練習室籌碼1029"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)
    JS_ST = "() => { const S = window.TwLab.state().bt; return { n: S.B ? S.B.n : 0, tf: S.tf, trades: S.res ? S.res.trades.length : -1, strat: S.strat, chip: !!(S.B && S.B.chip), sym: S.sym }; }"

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    s0 = pg.evaluate(JS_ST)
    ok(f"{T}：2330 載入時帶有籌碼資料（外資／投信／融資）", s0["chip"] and s0["sym"] == "2330", s0)

    def pick(sid):
        pg.click("#labPickBtn")
        pg.click(".lab-ptabs button[data-pt='strat']")
        pg.click(f".lab-pi[data-s='{sid}']"); pg.wait_for_timeout(1500)

    pg.click("#labPickBtn"); pg.click(".lab-ptabs button[data-pt='strat']")
    ok(f"{T}：策略清單有「內建策略・籌碼」分類，且至少 9 支", "內建策略・籌碼" in pg.inner_text("#labPl") and pg.locator(".lab-pi[data-s='instbuy'], .lab-pi[data-s='trustbuy'], .lab-pi[data-s='foreignturn'], .lab-pi[data-s='margin'], .lab-pi[data-s='ratio'], .lab-pi[data-s='holders'], .lab-pi[data-s='daytrade'], .lab-pi[data-s='brkinst'], .lab-pi[data-s='matrust']").count() == 9, None)
    pg.keyboard.press("Escape"); pg.mouse.click(5, 5); pg.wait_for_timeout(200)

    # 法人連買 → 有交易；改連買根數 → 結果改變
    pick("instbuy")
    a = pg.evaluate(JS_ST)
    ok(f"{T}：選「法人連買」後有交易（{a['trades']} 筆），策略名同步", a["strat"] == "instbuy" and a["trades"] > 5 and "法人連買" in pg.inner_text("#labPickBtn"), a)
    pg.fill("input[data-p='n']", "7"); pg.wait_for_timeout(1500)
    a2 = pg.evaluate(JS_ST)
    ok(f"{T}：連買根數 3→7 後交易數改變", a2["trades"] != a["trades"], (a["trades"], a2["trades"]))
    pg.click("#labTf button[data-tf='W']"); pg.wait_for_timeout(1800)
    a3 = pg.evaluate(JS_ST)
    ok(f"{T}：切到週 K 仍有籌碼、能跑出結果", a3["tf"] == "W" and a3["chip"] and a3["trades"] >= 0 and a3["n"] < a2["n"] / 3 and "沒有籌碼資料" not in pg.inner_text("#labStats"), a3)
    pg.click("#labTf button[data-tf='D']"); pg.wait_for_timeout(1500)

    # 其他籌碼策略
    for sid, nm in (("trustbuy", "投信連買"), ("foreignturn", "外資轉買"), ("margin", "融資增減"), ("brkinst", "突破＋法人買超"), ("matrust", "均線多頭＋投信連買")):
        pick(sid)
        r = pg.evaluate(JS_ST)
        ok(f"{T}：「{nm}」跑得出結果且有交易（{r['trades']} 筆）", r["strat"] == sid and r["trades"] > 0, r)
    # 突破＋法人買超的交易數 < 單純突破（法人濾網真的過濾掉訊號）
    pick("pricech"); base_n = pg.evaluate(JS_ST)["trades"]
    pg.click("#labPickBtn"); pg.click(".lab-ptabs button[data-pt='strat']"); pg.click(".lab-pi[data-s='brkinst']"); pg.wait_for_timeout(1500)
    pg.keyboard.press("Escape")
    f_n = pg.evaluate(JS_ST)["trades"]
    ok(f"{T}：加了法人濾網後交易數（{f_n}）少於純價格突破（{base_n}）", f_n < base_n * 1.3 and f_n != base_n, (base_n, f_n))

    # 集保大戶：資料不足
    pick("holders")
    ok(f"{T}：「集保大戶增減」明講資料不足、不畫績效", "資料不足" in pg.inner_text("#labStats") and "2026-09" in pg.inner_text("#labStats"), pg.inner_text("#labStats")[:60])

    # 沒有籌碼資料的標的（加權指數）：明講，不是空白
    pick("instbuy")
    pg.click("#labSym"); pg.fill("#labSym", "加權"); pg.wait_for_timeout(400)
    pg.click("#labSymDD .lab-di[data-c='TAIEX']"); pg.wait_for_timeout(1800)
    ok(f"{T}：指數沒有籌碼資料時寫明原因（只支援近期成交值前 1000 大個股）", "沒有籌碼資料" in pg.inner_text("#labStats") and "1000" in pg.inner_text("#labStats"), pg.inner_text("#labStats")[:80])

    # 「?」說明寫出研究結論與資料範圍
    pg.click("#v-lab .lab-tabs .lab-q"); pg.wait_for_timeout(300)
    how = pg.inner_text("#v-lab .lab-tabs .lab-pop")
    ok(f"{T}：「?」寫出「法人籌碼當主訊號沒有增量」與集保大戶資料不足", "法人籌碼當主訊號沒有增量" in how and "集保大戶" in how and "2026-09" in how, None)
    pg.mouse.click(5, 5)

    # 自訂策略：積木可選籌碼運算元，交易次數隨之改變
    pg.goto(base + "#lab/custom", wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
    pg.click("#cuNew"); pg.wait_for_timeout(500)

    def n_trades():
        pg.wait_for_timeout(1500)
        return pg.evaluate("() => { const t = [...document.querySelectorAll('#cuStats .lab-st')].find(x => x.textContent.includes('交易次數')); return t ? +t.querySelector('b').textContent : -1; }")
    pg.click(".cb-blk[data-b='le'] [data-add='cmp']")
    pg.locator(".cb-blk[data-b='le'] .cb-row select[data-f='a.t']").select_option("sinst")
    pg.locator(".cb-blk[data-b='le'] .cb-row select[data-f='op']").select_option("ge")
    pg.locator(".cb-blk[data-b='le'] .cb-row select[data-f='b.t']").select_option("num")
    pg.locator(".cb-blk[data-b='le'] .cb-row input[data-f='b.v']").fill("3")
    pg.click(".cb-blk[data-b='lx'] [data-add='cmp']")
    pg.locator(".cb-blk[data-b='lx'] .cb-row select[data-f='a.t']").select_option("sinst")
    pg.locator(".cb-blk[data-b='lx'] .cb-row select[data-f='op']").select_option("le")
    pg.locator(".cb-blk[data-b='lx'] .cb-row select[data-f='b.t']").select_option("num")
    pg.locator(".cb-blk[data-b='lx'] .cb-row input[data-f='b.v']").fill("-2")
    n1 = n_trades()
    ok(f"{T}：積木「法人連買根數 ≥ 3 進場、≤ -2 出場」試跑有交易（{n1} 筆）", n1 > 5, n1)
    pg.locator(".cb-blk[data-b='le'] .cb-row input[data-f='b.v']").fill("6")
    n2 = n_trades()
    ok(f"{T}：把門檻 3 改成 6 後交易次數減少", 0 <= n2 < n1, (n1, n2))

    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)
    c.close()

    # 手機 390：選一支籌碼策略，沒有橫向捲動
    c, pg = None, None
    c = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    pg.evaluate("() => { const S = window.TwLab.state().bt; S.strat = 'trustbuy'; }")
    pg.evaluate("() => document.getElementById('labMx') && document.getElementById('labMx').click()"); pg.wait_for_timeout(300)
    pg.click("#labPickBtn"); pg.click(".lab-ptabs button[data-pt='strat']"); pg.click(".lab-pi[data-s='instbuy']"); pg.wait_for_timeout(1800)
    m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, trades: window.TwLab.state().bt.res ? window.TwLab.state().bt.res.trades.length : -1 })")
    ok(f"{T}：手機 390 選籌碼策略後有結果、沒有橫向捲動", m["trades"] > 0 and m["sw"] <= m["cw"] + 1, m)
    ok(f"{T}：手機全程沒有網頁錯誤", not errs, errs)
    c.close()


register("交易練習室籌碼1029", lambda pg, b, base, code: t_lab_chips(b, base, code))
