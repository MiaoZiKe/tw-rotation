# 驗收段落「冷啟動1110」（site/coldstart_config.js 總開關；pricing.js／checkout.js／qcard.js／promo_welcome.js／tour.js；
#   plan_presets.js、features.js 的額度）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_sub_ctx()、_p12_ctx()、CONSENT_PRESET 直接可用，不要 import _uitest。
# Andy 11-10「全部 O」核可 docs/marketing/restart_1109/00_plan.md 決定表第 2、3、4 項（依據 01_freemium.md 第 3-3、4-1 節）。
#
# 驗什麼（全部真的操作、驗畫面真的變）：
#   A. 預設值：檔案裡寫的就是 enabled: true；github.io 備援網址不論開關一律冷啟動（launch_standard 第 10 條 ⑥）。
#   B. 開著（用 page.route 把設定檔換成原檔）：
#      訪客 → #pricing 整頁找不到「NT$」「／月」「／年」、沒有月繳年繳切換；付費卡按鈕寫「免費註冊」；按了不開結帳面板；
#             TwCheckout.open() 也開不出來（回 #pricing）；沒有任何「升級 Plus／Pro」字樣。
#      註冊會員 → 付費卡按鈕寫「預約通知」，真的按下去：送出 /v1/subscribe/request（note 以 [預約開放通知] 開頭）、
#             畫面出現「已記下」；帳號選單沒有「訂閱方案」「我的訂單／付款紀錄」，有「會員權益」；
#             額度用完的大卡與 inline 備註改寫「預約通知」「明天 00:00 重置」，沒有「Plus 以上可增加」。
#      歡迎窗 → 沒有 Plus／Pro 字樣。
#   C. 關著（把設定檔換成 enabled:false）：價格、「升級」鈕、結帳面板、「訂閱方案」全部恢復。
#   D. 額度（plan_presets.js）：訪客 stock.page 5、法人／營收獲利分頁開、search 10、share.card 5、ind.3d 1；
#      註冊會員多數 ×2、標「試營運期額度」；體驗額度（welcome）沒被動。
#      真的操作：把這份預設當後端範本，訪客連看 5 檔個股都放行、第 6 檔被鎖；站主不受限。
#   E. 截圖（TW_COLD_SHOT＝資料夾）：價格頁、被鎖提示框、歡迎窗，390／1440 各一。
import json as _cs_json
import pathlib as _cs_pl

_CS_SITE = _cs_pl.Path(str(SITE))
_CS_FILE = _CS_SITE / "coldstart_config.js"
_CS_INIT = "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}"


def _cs_presets():
    """plan_presets.js 是 JS 物件（不一定是嚴格 JSON）→ 用 node 執行後吐 JSON"""
    out = subprocess.run(["node", "-e", "global.window = {}; require(process.argv[1]); process.stdout.write(JSON.stringify(window.TW_PLAN_PRESETS))", str(_CS_SITE / "plan_presets.js")],
                         capture_output=True, text=True, check=True).stdout
    return {t["key"]: t for t in _cs_json.loads(out)["tiers"]}


def t_coldstart_1110(b, base, code):
    T = "冷啟動1110"
    errs: list = []
    src = _CS_FILE.read_text(encoding="utf-8")
    shots = os.environ.get("TW_COLD_SHOT")
    if shots:
        _cs_pl.Path(shots).mkdir(parents=True, exist_ok=True)

    def cold_ctx(who, on, width=1440, **kw):
        """用 _sub_ctx 的假後端；設定檔用 route 換成「開」（原檔）或「關」（enabled:false）"""
        c, sent, st = _sub_ctx(b, who, width=width, **kw)
        body = src if on else src.replace("enabled: true,", "enabled: false,", 1)
        c.route(re.compile(r"/coldstart_config\.js"), lambda r: r.fulfill(status=200, body=body, headers={"content-type": "application/javascript; charset=utf-8"}))
        c.add_init_script(_CS_INIT)
        return c, sent, st

    def page(c, h):
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + h, wait_until="domcontentloaded")
        wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click(); pg.wait_for_timeout(300)
        return pg

    ON_ROUTE = lambda c: c.route(re.compile(r"/coldstart_config\.js"), lambda r: r.fulfill(status=200, body=src, headers={"content-type": "application/javascript; charset=utf-8"}))  # noqa: E731
    PG_CARD = """() => { const c = [...document.querySelectorAll('.qcard')].find(x => /個股頁/.test(x.innerText)); return { lock: !!c, txt: c ? c.innerText : '' }; }"""

    def shot(pg, name):
        if shots:
            try:
                pg.screenshot(path=str(_cs_pl.Path(shots) / name))
            except Exception as ex:  # noqa: BLE001
                print("   (截圖失敗)", name, ex)

    # ------------------------------------------------------------ A. 預設與備援網址
    ok(f"{T} A1 設定檔預設 enabled: true（冷啟動預設為開）", "enabled: true," in src and "window.TW_COLDSTART" in src)
    ok(f"{T} A2 備援網址 github.io 不論開關一律冷啟動（程式裡有 mirror 判斷、isOn 含 mirror）", "github\\.io" in src and "C.enabled || mirror" in src)
    c, _, _ = cold_ctx(None, False, plan="guest")
    pg = page(c, "#overview")
    r = pg.evaluate("() => ({ on: TwCold.on(), mirror: TwCold.mirror, cls: document.documentElement.classList.contains('cold') })")
    ok(f"{T} A3 開關關著、在本機網域：TwCold.on()＝false、沒有 cold class（網站完全是原樣）", r == {"on": False, "mirror": False, "cls": False}, r)
    c.close()
    # github.io 主機名：把 location.hostname 偽裝成 *.github.io（開關關著也要冷啟動）
    c, _, _ = cold_ctx(None, False, plan="guest")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    fake = src.replace("enabled: true,", "enabled: false,", 1).replace("/(^|\\.)github\\.io$/i.test(location.hostname || '')", "true")
    c.route(re.compile(r"/coldstart_config\.js"), lambda r2: r2.fulfill(status=200, body=fake, headers={"content-type": "application/javascript; charset=utf-8"}))
    pg.goto(base + "#pricing", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.querySelector('#prCards')", 15000)
    r = pg.evaluate("() => ({ on: TwCold.on(), m: TwCold.mirror, txt: document.getElementById('v-pricing').innerText })")
    ok(f"{T} A4 ★ 模擬 github.io：開關寫 false 也冷啟動，#pricing 沒有「NT$」", r["on"] and r["m"] and "NT$" not in r["txt"], r["txt"][:200])
    c.close()

    # ------------------------------------------------------------ B1. 開著：訪客
    c, sent, st = cold_ctx(None, True, plan="guest")
    pg = page(c, "#pricing")
    wait_until(pg, "() => !!document.querySelector('#prCards .prcard[data-tier=paid]')", 15000)
    pg.wait_for_timeout(500)
    v = pg.evaluate("""() => { const v = document.getElementById('v-pricing'); const paid = [...v.querySelectorAll('.prcard[data-tier=paid]')];
        return { txt: v.innerText, n: paid.length, per: !!v.querySelector('#prPeriod'), strike: !!v.querySelector('.prorig s'), prices: v.querySelectorAll('.prprice b').length,
                 btn: paid.map(x => x.querySelector('.prgo').textContent.trim()), ask: paid.map(x => x.querySelector('.prprice').textContent.trim()),
                 up: /升級\\s*(Plus|Pro)/.test(v.innerText), cmpPrice: /NT\\$|\\d\\s*\\/\\s*月/.test(v.innerText) }; }""")
    ok(f"{T} B1 ★ 訪客：#pricing 整頁找不到「NT$」、沒有月繳年繳切換、沒有劃線價、沒有價格數字", v["n"] >= 1 and "NT$" not in v["txt"] and not v["per"] and not v["strike"] and v["prices"] == 0 and not v["cmpPrice"], (v["n"], v["per"], v["prices"]))
    ok(f"{T} B2 訪客：付費卡價格處寫「即將開放」、按鈕寫「免費註冊」、整頁沒有「升級 Plus／Pro」", all(x == "即將開放" for x in v["ask"]) and all(x == "免費註冊" for x in v["btn"]) and not v["up"], (v["ask"], v["btn"]))
    ok(f"{T} B1b ★ 訪客：整頁找不到「399」「799」（方案名稱不含數字，改進階／完整）、頁首說明改試營運期", not re.search(r"399|799", v["txt"]) and "進階" in v["txt"] and "試營運期，進階功能開放免費體驗" in v["txt"], v["txt"][:300])
    shot(pg, "pricing_guest_1440.png")
    pg.locator('#prCards .prcard[data-tier=paid] .prgo').first.click()
    pg.wait_for_timeout(600)
    o = pg.evaluate("() => ({ dlg: !!document.querySelector('.codlg, .subco'), hash: location.hash })")
    ok(f"{T} B3 ★ 訪客按付費卡「免費註冊」：不開結帳面板、不開訂閱申請視窗", not o["dlg"], o)
    pg.evaluate("() => { try { TwCheckout.open({ plan: 'p399', per: 'month' }); } catch (e) {} }")
    pg.wait_for_timeout(500)
    o = pg.evaluate("() => ({ dlg: !!document.querySelector('.codlg'), hash: location.hash })")
    ok(f"{T} B4 ★ 直接呼叫 TwCheckout.open() 也開不出結帳面板（結帳入口全關），退回 #pricing", not o["dlg"] and o["hash"] == "#pricing", o)
    c.close()

    # ------------------------------------------------------------ B2. 開著：註冊會員
    c, sent, st = cold_ctx("member", True, plan="free")
    pg = page(c, "#pricing")
    wait_until(pg, "() => !!document.querySelector('#prCards .prcard[data-tier=paid] .prgo')", 15000)
    pg.wait_for_timeout(500)
    btn = pg.evaluate("() => [...document.querySelectorAll('#prCards .prcard[data-tier=paid] .prgo')].map(x => x.textContent.trim())")
    ok(f"{T} B5 註冊會員：付費卡按鈕寫「預約通知」", btn and all(x == "預約通知" for x in btn), btn)
    n0 = len(sent)
    pg.locator('#prCards .prcard[data-tier=paid] .prgo').first.click()
    wait_until(pg, "() => /已記下/.test(document.body.innerText)", 6000)
    req = [x for x in sent[n0:] if x[0] == "/v1/subscribe/request"]
    ok(f"{T} B6 ★ 按「預約通知」真的送出 /v1/subscribe/request（note 以 [預約開放通知] 開頭、不開結帳面板），畫面出現「已記下」",
       len(req) == 1 and str(req[0][1].get("note", "")).startswith("[預約開放通知]") and not pg.evaluate("() => !!document.querySelector('.codlg')")
       and "已記下" in pg.evaluate("() => document.body.innerText"), req)
    shot(pg, "pricing_member_1440.png")
    # 帳號選單
    pg.click("#acctBtn"); pg.wait_for_timeout(400)
    mt = pg.evaluate("() => { const m = document.querySelector('#acctMenu, .acctmenu, [role=menu]'); return m ? m.innerText : document.body.innerText; }")
    ok(f"{T} B7 ★ 帳號選單：沒有「訂閱方案」「我的訂單／付款紀錄」，有「會員權益」", "訂閱方案" not in mt and "我的訂單" not in mt and "會員權益" in mt, mt[:300])
    c.close()

    # ------------------------------------------------------------ B3. 開著：額度用完（大卡、inline 備註）
    for who, plan, want in ((None, "guest", "免費註冊"), ("member", "free", "預約通知")):
        c = _p12_ctx(b, plan=plan, seed={"share.card": 99})
        c.route(re.compile(r"/coldstart_config\.js"), lambda r: r.fulfill(status=200, body=src, headers={"content-type": "application/javascript; charset=utf-8"}))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click(); pg.wait_for_timeout(300)
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        wait_until(pg, "() => !!document.querySelector('.scBtn[data-sct=\"ov-fear\"]')", 25000)
        pg.wait_for_timeout(700)
        note = pg.evaluate("() => { const n = [...document.querySelectorAll('span.qnote[data-f=\"share.card\"]')].find(x => x.getClientRects().length > 0); return n ? n.textContent : ''; }")
        ok(f"{T} B8 {plan}：額度用完的備註寫「明天 00:00 重置／免費註冊可增加」，沒有「Plus 以上可增加」（{note}）",
           note and "Plus" not in note and ("明天 00:00 重置" in note if who else "免費註冊可增加" in note), note)
        c.close()

    # ------------------------------------------------------------ B4. 歡迎窗
    c, sent, st = cold_ctx("member", True, plan="free")
    pg = page(c, "#overview")
    pg.evaluate("() => { try { TwPromoWelcome.force(); } catch (e) {} }")
    wait_until(pg, "() => TwPromoWelcome.isOpen()", 6000)
    wt = pg.evaluate("() => document.querySelector('.pw-card').innerText")
    ok(f"{T} B9 ★ 歡迎窗（開著）：沒有 Plus／Pro／升級／訂閱字樣，改寫「進階額度」", not re.search(r"Plus|Pro|升級|訂閱", wt) and "進階額度" in wt, wt[:200])
    shot(pg, "welcome_member_1440.png")
    c.close()

    # ------------------------------------------------------------ C. 關著：完整恢復
    c, sent, st = cold_ctx("member", False, plan="free")
    pg = page(c, "#pricing")
    wait_until(pg, "() => !!document.querySelector('#prCards .prcard[data-tier=paid] .prgo')", 15000)
    pg.wait_for_timeout(500)
    v = pg.evaluate("""() => { const v = document.getElementById('v-pricing'); const paid = [...v.querySelectorAll('.prcard[data-tier=paid]')];
        return { txt: v.innerText, btn: paid.map(x => x.querySelector('.prgo').textContent.trim()), prices: v.querySelectorAll('.prprice b').length }; }""")
    ok(f"{T} C1 ★ 關著：#pricing 價格（NT$）與「升級」按鈕都回來了", "NT$" in v["txt"] and v["prices"] >= 1 and all(x.startswith("升級") for x in v["btn"]), (v["btn"], v["prices"]))
    pg.locator('#prCards .prcard[data-tier=paid] .prgo').first.click()
    wait_until(pg, "() => !!document.querySelector('.codlg')", 8000)
    ok(f"{T} C2 ★ 關著：按「升級」真的開出結帳面板（綠界結帳程式完整保留）", pg.evaluate("() => !!document.querySelector('.codlg')"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pg.click("#acctBtn"); pg.wait_for_timeout(400)
    mt = pg.evaluate("() => document.body.innerText")
    ok(f"{T} C3 關著：帳號選單的「訂閱方案」回來", "訂閱方案" in mt, "")
    c.close()

    # ------------------------------------------------------------ D. 額度預設與實際鎖
    P = _cs_presets()
    g, f = P["guest"], P["free"]
    ok(f"{T} D1 訪客：stock.page 5、search 10、share.card 5、ind.3d 1（開）、法人／營收獲利分頁開",
       g["lims"].get("stock.page") == 5 and g["lims"].get("search") == 10 and g["lims"].get("share.card") == 5 and g["lims"].get("ind.3d") == 1
       and g["feats"].get("ind.3d") is True and g["feats"].get("stock.inst") is True and g["feats"].get("stock.profit") is True,
       {k: g["lims"].get(k) for k in ("stock.page", "search", "share.card", "ind.3d")})
    ok(f"{T} D2 訪客仍關著：新聞、融資券、大戶（留給註冊的誘因）", g["feats"].get("stock.news") is False and g["feats"].get("stock.margin") is False and g["feats"].get("stock.holders") is False)
    exp = {"stock.page": 20, "search": 20, "share.card": 10, "flow.rank.click": 10, "flow.filter": 10, "flow.sankey.drill": 10, "mkt.credit": 10, "mkt.fut": 10,
           "mkt.inst.day": 10, "ov.advdec.tiles": 10, "ov.fear": 10, "ind.3d": 5, "ind.groups": 5, "ind.diagram": 5, "stock.mtf": 5, "stock.ind": 5, "stock.draw": 5, "stock.k_min": 5}
    bad = {k: f["lims"].get(k) for k, v in exp.items() if f["lims"].get(k) != v}
    ok(f"{T} D3 註冊會員：對照表 18 項（個股頁 20、搜尋 20、圖卡 10、資金流向 10…）都到位", not bad, bad)
    keep = {k: f["lims"].get(k) for k in ("stock.ai", "etf.returns", "etf.list", "etf.cmp", "etf.cashflow") if f["lims"].get(k) != 3}
    ok(f"{T} D4 註冊會員 stock.ai／ETF 相關維持 3（B 級內容不放寬）", not keep, keep)
    ok(f"{T} D5 註冊會員卡標「試營運期額度」", (f.get("meta") or {}).get("badge") == "試營運期額度", (f.get("meta") or {}).get("badge"))
    # 體驗額度沒被動：presets 不含 welcome／trial；features.js 的體驗清單（GRANT_BAN）沒變
    txt = (_CS_SITE / "plan_presets.js").read_text(encoding="utf-8")
    ok(f"{T} D6 體驗額度（新會員體驗）不在這批改動內：plan_presets.js 沒有 welcome／grant 鍵", '"welcome"' not in txt and '"grant"' not in txt)

    feats = {k: v for k, v in g["feats"].items() if v is False}   # 後端範本只回有明寫 false 的
    lims = dict(g["lims"])
    c, sent, st = _sub_ctx(b, None, plan="guest", feats=feats, lims=lims, dq=g.get("dq"))
    c.add_init_script(_CS_INIT)
    ON_ROUTE(c)
    pg = page(c, "#stock/2330")
    codes = ["2330", "2317", "2454", "2303", "2412"]
    locked_first5 = []
    for cd in codes:
        pg.evaluate(f"() => {{ location.hash = '#stock/{cd}'; }}")
        pg.wait_for_timeout(1300)
        locked_first5.append(pg.evaluate(PG_CARD)["lock"])
    used = pg.evaluate("() => (TwQuota.used('stock.page') || []).length")
    ok(f"{T} D7 ★ 訪客連看 5 檔個股：5 檔都放行（沒有鎖）、用量 5", not any(locked_first5) and used == 5, (locked_first5, used))
    pg.evaluate("() => { location.hash = '#stock/2881'; }")
    wait_until(pg, "() => [...document.querySelectorAll('.qcard')].some(x => /個股頁/.test(x.innerText))", 8000)
    pg.wait_for_timeout(600)
    lk = pg.evaluate(PG_CARD)
    ok(f"{T} D8 ★ 第 6 檔被鎖，提示寫「免費註冊」、沒有 Plus／Pro／升級", lk["lock"] and "免費註冊" in lk["txt"] and not re.search(r"Plus|Pro|升級", lk["txt"]), lk)
    # 訪客的個股頁分頁：法人、營收獲利現在是開的（沒有蓋鎖頭）
    pg.evaluate("() => { sessionStorage.clear(); }")
    shot(pg, "locked_guest_1440.png")
    c.close()
    # 註冊會員（試營運 20 檔）用滿 → 第 21 檔被鎖，提示寫「預約通知」＋「明天…重置」
    feats_f = {k: v for k, v in f["feats"].items() if v is False}
    c, sent, st = _sub_ctx(b, "member", plan="free", feats=feats_f, lims=dict(f["lims"]), dq=f.get("dq"))
    c.add_init_script(_CS_INIT + "try { if (!localStorage.getItem('cs1110m')) { localStorage.setItem('cs1110m', '1');"
                      " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      " localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'stock.page': Array.from({length: 20}, (_, i) => 'seed' + i) } })); } } catch (e) {}")
    ON_ROUTE(c)
    pg = page(c, "#stock/2330")
    wait_until(pg, "() => [...document.querySelectorAll('.qcard')].some(x => /個股頁/.test(x.innerText))", 10000)
    pg.wait_for_timeout(800)
    lk = pg.evaluate(PG_CARD)
    ok(f"{T} D8b ★ 註冊會員用滿 20 檔：第 21 檔被鎖，提示寫「預約通知」、沒有 Plus／Pro／升級", lk["lock"] and "預約通知" in lk["txt"] and not re.search(r"Plus|Pro|升級", lk["txt"]), lk)
    shot(pg, "locked_member_1440.png")
    c.close()
    # 站主不受限
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script(_CS_INIT + "try { if (!localStorage.getItem('cs1110')) { localStorage.setItem('cs1110', '1');"
                      " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      " localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'stock.page': Array.from({length: 99}, (_, i) => 'seed' + i) } })); } } catch (e) {}")
    pg = page(c, "#stock/2330")
    pg.wait_for_timeout(1500)
    lk = pg.evaluate(PG_CARD)["lock"]
    ok(f"{T} D9 ★ 站主種 99 次個股頁也不鎖", lk is False, lk)
    c.close()

    # ------------------------------------------------------------ E. 390 截圖＋不橫向捲動
    c, sent, st = cold_ctx(None, True, width=390, plan="guest", touch=True)
    pg = page(c, "#pricing")
    wait_until(pg, "() => !!document.querySelector('#prCards .prcard[data-tier=paid]')", 15000)
    pg.wait_for_timeout(600)
    CLIP = """() => [...document.querySelectorAll('#prCards .prprice.ask')].map(e => { const r = e.getBoundingClientRect(), p = e.closest('.prcard').getBoundingClientRect();
        return e.scrollWidth <= e.clientWidth + 1 && r.left >= p.left - 1 && r.right <= p.right + 1 && r.left >= 0 && r.right <= innerWidth; })"""
    for w in (360, 390, 1440):
        c2, _s2, _t2 = cold_ctx(None, True, width=w, plan="guest", touch=w < 600)
        p2 = page(c2, "#pricing")
        wait_until(p2, "() => document.querySelectorAll('#prCards .prprice.ask').length >= 2", 30000)
        p2.wait_for_timeout(900)
        cl = p2.evaluate(CLIP)
        for _ in range(10):   # 手機會再重畫一次方案卡；量到空的就等一下再量
            if cl: break
            p2.wait_for_timeout(500); cl = p2.evaluate(CLIP)
        ok(f"{T} E0 寬 {w}：「即將開放」大字沒被切（都在卡片內、螢幕內）", cl and all(cl), cl)
        c2.close()
    ow = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    ok(f"{T} E1 手機 390：價格頁不橫向捲動、整頁沒有「NT$」", ow <= 1 and "NT$" not in pg.evaluate("() => document.getElementById('v-pricing').innerText"), ow)
    shot(pg, "pricing_guest_390.png")
    c.close()
    # 手機 390：訪客個股頁用滿 5 檔（用 features.js 的預設 guest:5，不靠後端範本）→ 鎖定提示框
    c = _p12_ctx(b, plan="guest", width=390, seed={"stock.page": 5}, touch=True)
    ON_ROUTE(c)
    pg = page(c, "#stock/2330")
    wait_until(pg, "() => [...document.querySelectorAll('.qcard')].some(x => /個股頁/.test(x.innerText))", 12000)
    pg.wait_for_timeout(600)
    lk = pg.evaluate(PG_CARD)
    ok(f"{T} E2 手機 390：features.js 預設（訪客 5 檔）用滿 → 鎖定提示寫「免費註冊」、沒有 Plus／Pro／升級", lk["lock"] and "免費註冊" in lk["txt"] and not re.search(r"Plus|Pro|升級", lk["txt"]), lk)
    shot(pg, "locked_guest_390.png")
    c.close()
    c, sent, st = cold_ctx("member", True, width=390, plan="free", touch=True)
    pg = page(c, "#overview")
    pg.evaluate("() => { try { TwPromoWelcome.force(); } catch (e) {} }")
    wait_until(pg, "() => TwPromoWelcome.isOpen()", 6000)
    pg.wait_for_timeout(500)
    shot(pg, "welcome_member_390.png")
    c.close()

    ok(f"{T} 全程沒有頁面 JS 錯誤", not errs, errs[:3])


register("冷啟動1110", lambda pg, b, base, code: t_coldstart_1110(b, base, code))
