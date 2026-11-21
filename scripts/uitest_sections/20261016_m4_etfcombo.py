# 驗收段落「手機ETF組合參數1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）：「圖四將最上方功能配置在每個組合裡面，只有手機版本要這樣，網頁先不動，目的是每個組合都能自己個別調整」
#   手機（html.m4）月配試算：條件摘要鈕搬進目前分頁（單檔 ETF／組合 A～E）內容最上面、鈕上標分頁名；每個分頁的條件各自一份（tw.etf.inc.pt），預設＝全域設定。
#   驗：360／390／430（is_mobile、has_touch、DPR2；全部手指 tap）——
#   ① 組合 A 的鈕在 #incCombo 裡、寫「組合 A」② 在 A 改金額 → A 的鈕／結論句／A 分頁的投入都變，B 分頁的投入不變、全域 tw.etf.inc.year 沒被寫
#   ③ 切到 B → B 的鈕＝原本的條件、結論句＝原本的 ④ 在 B 改範圍 → 切回 A：A 仍是自己改的金額、範圍沒被 B 帶走
#   ⑤ 重新整理 → A 的條件還在（跟全域設定一樣會記住）⑥ 單檔 ETF 的鈕在 #incSingle 裡、寫「單檔 ETF」、條件＝全域
#   ⑦ 參數鎖（etf.inc.params 關）：每個分頁的鈕都反灰帶鎖、一律預設值（不套已存的分頁值）、抽屜點了不會改。
#   桌機 1440：沒有分頁裡的鈕，改範圍照舊寫全域 tw.etf.inc.scope、不寫 tw.etf.inc.pt。


def t_m4_etfcombo_1016(b, base):
    T = "手機ETF組合參數1016"
    INFO = """() => { const b = document.getElementById('m4EtfSet-inc');
        return { btn: b ? b.textContent.replace(/\\s+/g, '') : '', sec: b ? (b.closest('#incCombo') ? 'combo' : b.closest('#incSingle') ? 'single' : 'top') : '',
          tabs: [...document.querySelectorAll('#incTabs button')].map(x => x.textContent.replace(/\\s+/g, '')), pt: localStorage.getItem('tw.etf.inc.pt') || '',
          gy: localStorage.getItem('tw.etf.inc.year'), gs: localStorage.getItem('tw.etf.inc.scope'), cq: (document.getElementById('incCQ') || {}).textContent || '',
          lk: document.getElementById('etfInc').hasAttribute('data-inclk') }; }"""
    INIT = "try{ if(!sessionStorage.getItem('ec16')){ localStorage.clear(); sessionStorage.setItem('ec16','1'); %s } localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}"

    def tab(m, i):
        sel = "#incTabs button[data-v='s']" if i is None else f"#incTabs button[data-i='{i}']"
        m.locator(sel).scroll_into_view_if_needed(); m.tap(sel); m.wait_for_timeout(1800)

    for W in (360, 390, 430):
        tag = f"【{T}】{W}"
        ctx = b.new_context(viewport={"width": W, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        try:
            ctx.add_init_script(INIT % "")
            m = ctx.new_page()
            m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
            m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            m.goto(base + "#etf/inc", wait_until="domcontentloaded")
            wait_until(m, "(() => { const b = document.getElementById('m4EtfSet-inc'); return !!(b && b.getClientRects().length && document.querySelector(\"#incTabs button[data-i='1']\")); })()", 30000)
            m.wait_for_timeout(1500)
            tab(m, 0)
            a0 = m.evaluate(INFO)
            ok(f"{tag}①：組合 A 的條件鈕在組合 A 的內容裡、寫「組合A」", a0["sec"] == "combo" and a0["btn"].startswith("組合A"), a0)
            m4_etf_pick(m, "inc", "amt", wait=2500)
            a1 = m.evaluate(INFO)
            ok(f"{tag}②：在 A 改金額 → A 的鈕、結論句、A 分頁投入都變；B 分頁投入不變；全域金額沒被寫；只記在 c0",
               a1["btn"] != a0["btn"] and a1["cq"] != a0["cq"] and a1["tabs"][1] != a0["tabs"][1] and a1["tabs"][2] == a0["tabs"][2]
               and a1["gy"] is None and '"c0"' in a1["pt"] and '"c1"' not in a1["pt"], {"前": a0, "後": a1})
            tab(m, 1)
            b0 = m.evaluate(INFO)
            ok(f"{tag}③：切到 B → B 的鈕＝原本條件（只換分頁名）、結論句＝原本的", b0["sec"] == "combo" and b0["btn"] == a0["btn"].replace("組合A", "組合B", 1) and b0["cq"] == a0["cq"], b0)
            m4_etf_pick(m, "inc", "scope", wait=2500)
            b1 = m.evaluate(INFO)
            ok(f"{tag}④a：在 B 改範圍 → B 的鈕變、記在 c1、全域範圍沒被寫", b1["btn"] != b0["btn"] and '"c1"' in b1["pt"] and b1["gs"] is None, b1)
            tab(m, 0)
            a2 = m.evaluate(INFO)
            ok(f"{tag}④b：切回 A → A 仍是自己改過的金額、範圍沒被 B 帶走", a2["btn"] == a1["btn"], {"A改後": a1["btn"], "現在": a2["btn"]})
            m.reload(wait_until="domcontentloaded")
            wait_until(m, "(() => !!document.querySelector(\"#incTabs button[data-i='1']\"))()", 30000); m.wait_for_timeout(1200)
            tab(m, 0)
            a3 = m.evaluate(INFO)
            ok(f"{tag}⑤：重新整理後 A 的條件還在", a3["btn"] == a1["btn"], {"A改後": a1["btn"], "重整後": a3["btn"]})
            tab(m, None)
            s0 = m.evaluate(INFO)
            ok(f"{tag}⑥：單檔 ETF 的鈕在單檔內容裡、寫「單檔ETF」、條件＝全域原本的", s0["sec"] == "single" and s0["btn"] == a0["btn"].replace("組合A", "單檔ETF", 1), s0)
            sw = m.evaluate("() => [document.documentElement.scrollWidth, innerWidth]")
            ok(f"{tag}：整頁不橫捲 {sw}", sw[0] <= sw[1], sw)
        finally:
            ctx.close()
    # ⑦ 參數鎖：已存了 c0 的分頁值，鎖住時一律預設、點了不改
    c, _, _ = _sub_ctx(b, "member", width=390, plan="free", feats={"etf.inc.params": False}, touch=True)
    try:
        c.add_init_script(INIT % "localStorage.setItem('tw.etf.inc.pt', JSON.stringify({c0: {year: 200000}}));")
        m = c.new_page(); m.set_viewport_size({"width": 390, "height": 844})
        m.on("pageerror", lambda e: fails.append(f"{T} 鎖 pageerror: {e}"))
        m.goto(base + "#etf/inc", wait_until="domcontentloaded")
        wait_until(m, "(() => !!document.querySelector(\"#incTabs button[data-i='1']\") && document.getElementById('etfInc').hasAttribute('data-inclk'))()", 30000); m.wait_for_timeout(1200)
        for i in (0, 1):
            tab(m, i)
            d = m.evaluate(INFO)
            ok(f"【{T}】鎖：組合 {'AB'[i]} 的鈕反灰、一律預設值（年領 100 萬，不套已存的 c0）", d["lk"] and d["sec"] == "combo" and "100萬" in d["btn"] and "20萬" not in d["btn"], d)
        d0 = m.evaluate(INFO)
        m.locator("#m4EtfSet-inc").tap(force=True); m.wait_for_timeout(500)
        if m.locator("#m4EtfSegs button[data-g='amt']:not(.on)").count():
            m.locator("#m4EtfSegs button[data-g='amt']:not(.on)").first.tap(force=True); m.wait_for_timeout(1500)
        m.keyboard.press("Escape"); m.wait_for_timeout(300)
        d1 = m.evaluate(INFO)
        ok(f"【{T}】鎖：點條件也不會改（鈕字與存的分頁值都不變）", d1["btn"] == d0["btn"] and d1["pt"] == d0["pt"], {"前": d0, "後": d1})
    finally:
        c.close()
    # 桌機 1440：沒有分頁裡的鈕；改範圍照舊寫全域、不寫 pt
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    try:
        ctx.add_init_script(INIT % "")
        m = ctx.new_page()
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(base + "#etf/inc", wait_until="domcontentloaded")
        wait_until(m, "(() => !!document.querySelector('#incScope button'))()", 30000); m.wait_for_timeout(1200)
        m.click("#incScope button:not(.on)"); m.wait_for_timeout(1200)
        d = m.evaluate("() => ({ m4: document.documentElement.classList.contains('m4'), rows: document.querySelectorAll('.m4etfrow').length, gs: localStorage.getItem('tw.etf.inc.scope'), pt: localStorage.getItem('tw.etf.inc.pt') })")
        ok(f"【{T}】桌機 1440：沒有分頁裡的條件鈕、改範圍照舊寫全域、不寫分頁值", not d["m4"] and d["rows"] == 0 and d["gs"] in ("bond", "div") and d["pt"] is None, d)
    finally:
        ctx.close()


# ★ 2026-10-16 Andy（iPhone）：「圖四將最上方功能配置在每個組合裡面，只有手機版本要這樣」—— 360／390／430：每個分頁自己的條件鈕＋抽屜、互不影響、重整記住、參數鎖照舊；1440 不變
register("手機ETF組合參數1016", lambda pg, b, base, code: t_m4_etfcombo_1016(b, base), after="ETF月配金額1016")
