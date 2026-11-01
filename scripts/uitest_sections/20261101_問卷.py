# 驗收段落「問卷1101」：新會員體驗到期前問卷（site/survey.js）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# Andy 11-01：快到期時打開首頁跳出問卷，填完再送 7 天。用 page.route 假後端，真的操作每一步，
# 並驗「送出的 JSON 符合契約」「第 6 個母分頁被擋」「稍後再說 24 小時內不再跳」。

SVP_API = "http://127.0.0.1:9"


def _svp_ctx(b, W, trial, submit=None, logged=True, admin=False):
    import json as _j
    c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900})
    init = "window.TW_ACCOUNT_OVERRIDE = " + _j.dumps({"api": SVP_API}) + "; try { localStorage.setItem('tw.tour','done'); localStorage.setItem('tw.live.on','0');"
    if logged:
        init += " localStorage.setItem('tw.acct.tok','tok-sv'); localStorage.setItem('tw.acct.user', JSON.stringify({email:'m@example.com',name:'測試會員'}));"
    c.add_init_script(init + " } catch (e) {}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    log = {"reqs": [], "submit": None}

    def handle(route):
        req = route.request
        path = req.url.replace(SVP_API, "").split("?")[0]
        h = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST", "content-type": "application/json"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=h)
        log["reqs"].append((req.method, path))
        out, st = {}, 200
        if path == "/v1/me":
            out = {"user": {"email": "m@example.com", "name": "測試會員", "admin": admin}}
        elif path == "/v1/me/trial":
            out = dict({"active": True, "until": "2026-11-03", "base_until": "2026-11-03", "survey_done": False, "survey_eligible": True, "pro_until": None}, **trial)
        elif path == "/v1/survey/submit":
            try:
                log["submit"] = _j.loads(req.post_data)
            except Exception:
                log["submit"] = None
            out, st = submit or ({"ok": True, "until": "2026-11-10", "plus_until": "2026-11-17"}, 200)
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/notices":
            out = {"notices": []}
        route.fulfill(status=st, body=_j.dumps(out), headers=h)
    c.route(SVP_API + "/**", handle)
    return c, log


def _svp_open(c, base, hsh="#overview"):
    pg = c.new_page()
    pg.goto(base + hsh, wait_until="domcontentloaded")
    agree = pg.get_by_role("button", name="同意並繼續")
    try:
        if agree.count() and agree.first.is_visible():
            agree.first.click()
    except Exception:
        pass
    return pg


def t_survey_popup_1101(b, base, code):
    import os as _os
    T = "問卷1101"
    shots = _os.environ.get("TW_SURVEY_SHOT")
    errs: list[str] = []

    def shot(pg, name):
        if shots:
            _os.makedirs(shots, exist_ok=True)
            pg.screenshot(path=f"{shots}/{name}.png")
    VIS = "() => !!document.querySelector('#svOv .svbox')"

    # ---- A. 條件：不成立都不跳
    for label, trial, logged, hsh in (("沒登入", {}, False, "#overview"), ("沒有資格", {"survey_eligible": False}, True, "#overview"),
                                      ("已填過", {"survey_done": True, "survey_eligible": False}, True, "#overview"), ("不在首頁(#flow)", {}, True, "#flow")):
        c, log = _svp_ctx(b, 1440, trial, logged=logged)
        pg = _svp_open(c, base, hsh); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.wait_for_timeout(3500)
        ok(f"{T}：{label} → 不跳問卷", not pg.evaluate(VIS), log["reqs"])
        if label == "不在首頁(#flow)":
            pg.evaluate("location.hash = '#overview'")
            got = wait_until(pg, VIS, 15000)
            ok(f"{T}：從別頁回到首頁 → 才跳出", bool(got))
        c.close()
    # 後端 404（尚未部署）→ 靜默
    c, log = _svp_ctx(b, 1440, {})
    c.unroute(SVP_API + "/**")
    c.route(SVP_API + "/**", lambda r: r.fulfill(status=404, body="{}", headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "content-type": "application/json"}))
    pg = _svp_open(c, base); pg.wait_for_timeout(3500)
    ok(f"{T}：後端回 404 → 靜默不跳", not pg.evaluate(VIS))
    c.close()

    # ---- B. 桌機整段操作
    c, log = _svp_ctx(b, 1440, {})
    pg = _svp_open(c, base); pg.on("pageerror", lambda e: errs.append(str(e)))
    got = wait_until(pg, VIS, 15000)
    ok(f"{T}：已登入＋有資格＋首頁 → 跳出問卷", bool(got), log["reqs"])
    ok(f"{T}：用 POST 打 /v1/me/trial", ("POST", "/v1/me/trial") in log["reqs"], log["reqs"])
    ok(f"{T}：第 1 題顯示、下一步停用（還沒選星）", pg.locator("#svStepNo").inner_text() == "1" and pg.locator("#svNext").is_disabled())
    prv = pg.locator("#svPrv")
    ok(f"{T}：底部有「資料怎麼使用」小字連結 → #privacy-promo（新分頁開，不丟掉答案）", prv.count() == 1 and prv.get_attribute("href").endswith("#privacy-promo") and prv.get_attribute("target") == "_blank", prv.get_attribute("href"))
    shot(pg, "1_desktop_step1")
    ok(f"{T}：開頭說明提到送 7 天 Plus、送出鈕寫「領 7 天 Plus」", "7 天 Plus" in pg.locator(".svhint").inner_text())
    pg.click("[data-sat='4']"); pg.wait_for_timeout(150)
    ok(f"{T}：點 4 顆星 → 顯示 4 顆星、下一步啟用", "4 顆星" in pg.locator("#svSatTx").inner_text() and pg.locator("#svNext").is_enabled())
    pg.click("#svNext"); pg.wait_for_timeout(200)
    ok(f"{T}：進到第 2 題", pg.locator("#svStepNo").inner_text() == "2")
    navn = pg.evaluate("() => Object.keys(window.TwL4Nav.PAGES).filter(k => !['admin','delivery','tc','lab'].includes(k)).length")
    cards = pg.locator(".svpar").count()
    ok(f"{T}：母分頁卡片數＝側欄清單（動態讀，{navn}）", cards == navn and cards >= 10, [cards, navn])
    ok(f"{T}：母分頁有「總覽」「產業地圖」「ETF」", all(pg.locator(f".svpar:has-text('{t}')").count() for t in ("總覽", "產業地圖", "ETF")))
    ok(f"{T}：一般會員的母分頁沒有科技透明圈、交易練習室、管理區、交付清單", all(pg.locator(f"[data-par='{k}']").count() == 0 for k in ("tc", "lab", "admin", "delivery")))
    pg.click("[data-par='flow']"); pg.wait_for_timeout(150)
    chips = pg.locator("#svSub .svchip").count()
    ok(f"{T}：點母分頁「資金流向」→ 展開 3 個子分頁小籤", chips == 3, chips)
    pg.click("#svSub .svchip >> nth=0"); pg.click("#svSub .svchip >> nth=2"); pg.wait_for_timeout(100)
    ok(f"{T}：子分頁可多選（選 2 個、母卡角標 2）", pg.locator("#svSub .svchip.on").count() == 2 and pg.locator("[data-par='flow'] .svbd").inner_text() == "2")
    shot(pg, "2_desktop_step2_sub")
    for k in ("overview", "heatmap", "etf", "market"):
        pg.click(f"[data-par='{k}']")
    pg.wait_for_timeout(150)
    ok(f"{T}：選滿 5 個母分頁（計數 5/5）", "5" in pg.locator("#svCnt").inner_text() and pg.locator(".svpar.on").count() == 5)
    pg.click("[data-par='season']"); pg.wait_for_timeout(150)
    w = pg.locator(".svwarn").inner_text()
    ok(f"{T}：第 6 個被擋下並提示「最多選 5 個」", "最多選 5 個" in w and pg.locator(".svpar.on").count() == 5 and not pg.locator("[data-par='season'].on").count(), w)
    shot(pg, "3_desktop_step2_limit")
    pg.click("[data-par='etf']"); pg.click("#svSub .svchip >> nth=0"); pg.click("#svSub .svchip >> nth=1"); pg.click("#svSub .svchip >> nth=2")
    ok(f"{T}：子分頁不限數量（ETF 三個全選）", pg.locator("#svSub .svchip.on").count() == 3)
    pg.click("[data-par='overview']"); pg.click("[data-drop='overview']"); pg.wait_for_timeout(100)
    ok(f"{T}：取消一個後又能再選別的（4→可選第 5）", pg.locator(".svpar.on").count() == 4)
    pg.click("#svNext"); pg.wait_for_timeout(200)
    ok(f"{T}：第 3 題的選擇是空的（與第 2 題各自獨立）", pg.locator("#svStepNo").inner_text() == "3" and pg.locator(".svpar.on").count() == 0)
    pg.click("[data-par='stock']"); pg.wait_for_timeout(100)
    ok(f"{T}：沒有子分頁的母分頁(個股)直接算選好", pg.locator(".svpar.on").count() == 1 and pg.locator("#svSub .svchip").count() == 0)
    pg.fill("#svImp", "圖表載入有點慢"); shot(pg, "4_desktop_step3")
    pg.click("#svNext"); pg.wait_for_timeout(200)
    nw = pg.locator("[data-want]").count()
    ok(f"{T}：第 4 題給 6～8 個新增功能選項（{nw}）", 6 <= nw <= 8, nw)
    pg.click("[data-want='策略回測']"); pg.click("[data-want='手機 App']"); pg.fill("#svWant", "想要財報提醒")
    shot(pg, "5_desktop_step4")
    pg.click("#svPrev"); pg.wait_for_timeout(150)
    ok(f"{T}：上一步回第 3 題，文字仍在", pg.locator("#svStepNo").inner_text() == "3" and pg.input_value("#svImp") == "圖表載入有點慢")
    pg.click("#svNext"); pg.wait_for_timeout(150)
    pg.click("#svSend"); pg.wait_for_timeout(600)
    msg = pg.locator("#svOkMsg").inner_text() if pg.locator("#svOkMsg").count() else ""
    ok(f"{T}：送出成功 → 「已獲得 7 天 Plus，到 2026-11-17」（取 plus_until）", "已獲得 7 天 Plus，到 2026-11-17" in msg, msg)
    shot(pg, "6_desktop_success")
    s = dict(log["submit"] or {}); s.pop("t", None)   # t＝TwAccount.call 自動帶的登入權杖
    ok(f"{T}：送出的 JSON 欄位符合契約", set(s) == {"sat", "useful", "improve", "improve_text", "want", "want_text"} and s.get("sat") == 4, s)
    u = {x["p"]: sorted(x["subs"]) for x in s.get("useful", [])}
    ok(f"{T}：useful 格式 [{{p, subs[]}}]、母分頁 5 個內、資金流向帶 2 個子分頁", len(u) <= 5 and len(u.get("flow", [])) == 2 and len(u.get("etf", [])) == 3 and "season" not in u, u)
    ok(f"{T}：improve 帶個股(無子分頁→空陣列)、improve_text/want/want_text 正確",
       s.get("improve") == [{"p": "stock", "subs": []}] and s.get("improve_text") == "圖表載入有點慢" and sorted(s.get("want", [])) == ["手機 App", "策略回測"] and s.get("want_text") == "想要財報提醒", s)
    pg.click("#svOk"); pg.wait_for_timeout(200)
    ok(f"{T}：按「好」關閉", not pg.evaluate(VIS))
    c.close()

    # ---- C. 稍後再說
    c, log = _svp_ctx(b, 1440, {})
    pg = _svp_open(c, base); wait_until(pg, VIS, 15000)
    pg.click("#svLater2"); pg.wait_for_timeout(200)
    snz = pg.evaluate("() => +localStorage.getItem('tw.survey.snooze')")
    import time as _t
    ok(f"{T}：稍後再說 → 關閉並記下 24 小時", not pg.evaluate(VIS) and 23.5 * 3600e3 < snz - _t.time() * 1000 < 24.5 * 3600e3, snz)
    pg.reload(wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
    ok(f"{T}：重新整理 24 小時內不再跳", not pg.evaluate(VIS))
    c.close()

    # ---- D. 後端失敗訊息
    c, log = _svp_ctx(b, 1440, {}, submit=({"ok": False, "error": "你已經填寫過囉"}, 409))
    pg = _svp_open(c, base); wait_until(pg, VIS, 15000)
    pg.click("[data-sat='5']"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svSend"); pg.wait_for_timeout(500)
    ok(f"{T}：送出失敗 → 顯示後端訊息、仍在問卷內", "你已經填寫過囉" in pg.locator(".sverr").inner_text() and pg.evaluate(VIS))
    c.close()

    # ---- D2. 測試模式（Andy 11-02）：預覽版直接跳；正式站 ?survey=test 只有站主
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}; window.__fcnt = 0; const _f = window.fetch; window.fetch = function(u){ if (/survey\\/submit/.test(String(u))) window.__fcnt++; return _f.apply(this, arguments); };")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = _svp_open(c, base); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.wait_for_timeout(2500)
    ok(f"{T}：（正式路徑、沒登入）不跳", not pg.evaluate(VIS))
    pg.evaluate("history.replaceState(null, '', '/preview/member-invite/#overview')")
    pg.evaluate("window.TwSurvey.check()")
    got = wait_until(pg, VIS, 6000)
    ok(f"{T}：預覽版路徑（/preview/）首頁、沒登入也直接跳出", bool(got))
    ok(f"{T}：預覽版有「測試模式・不會送出」標示", pg.locator(".svtest").count() == 1)
    shot(pg, "12_preview_direct")
    pg.click("[data-sat='5']"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svSend"); pg.wait_for_timeout(400)
    ok(f"{T}：預覽版送出 → 「預覽測試：已獲得 7 天 Plus（示範）」且沒打後端", "預覽測試：已獲得 7 天 Plus（示範）" in pg.locator("#svOkMsg").inner_text() and pg.evaluate("() => window.__fcnt") == 0)
    shot(pg, "13_preview_success")
    pg.click("#svOk")
    pg.evaluate("location.hash = '#flow'"); pg.wait_for_timeout(200); pg.evaluate("location.hash = '#overview'"); pg.wait_for_timeout(300)
    pg.evaluate("window.__x = 1")
    c.close()
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = _svp_open(c, base); pg.wait_for_timeout(1500)
    pg.evaluate("history.replaceState(null, '', '/preview/member-invite/#overview')"); pg.evaluate("window.TwSurvey.check()")
    wait_until(pg, VIS, 6000)
    pg.click("#svLater2"); pg.wait_for_timeout(200)
    ok(f"{T}：預覽版「稍後再說」不寫 24 小時記錄", pg.evaluate("() => localStorage.getItem('tw.survey.snooze')") is None)
    pg.evaluate("window.TwSurvey.check()")
    ok(f"{T}：預覽版再檢查一次又跳出（沒被擋）", bool(wait_until(pg, VIS, 4000)))
    c.close()
    # 正式站 ?survey=test：站主強制顯示（即使沒資格），一般會員不行
    for who, admin, want in (("站主", True, True), ("一般會員", False, False)):
        c, log = _svp_ctx(b, 1440, {"survey_eligible": False, "survey_done": True}, admin=admin)
        pg = _svp_open(c, base + "?survey=test", "#overview"); pg.on("pageerror", lambda e: errs.append(str(e)))
        got = wait_until(pg, VIS, 15000 if want else 3500) if want else (pg.wait_for_timeout(4000) or pg.evaluate(VIS))
        ok(f"{T}：正式站 ?survey=test + {who}（沒資格）→ {'強制跳出' if want else '不跳'}", bool(got) == want, log["reqs"])
        if want:
            pg.click("[data-sat='3']"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svNext"); pg.click("#svSend"); pg.wait_for_timeout(500)
            ok(f"{T}：站主測試送出 → 示範成功、沒打 /v1/survey/submit", "示範" in pg.locator("#svOkMsg").inner_text() and not any(r[1] == "/v1/survey/submit" for r in log["reqs"]), log["reqs"])
            pg.click("#svOk")
            ok(f"{T}：站主測試不寫 24 小時記錄", pg.evaluate("() => localStorage.getItem('tw.survey.snooze')") is None)
        c.close()

    # ---- E. 手機 390
    c, log = _svp_ctx(b, 390, {})
    pg = _svp_open(c, base); pg.on("pageerror", lambda e: errs.append(str(e)))
    got = wait_until(pg, VIS, 15000)
    ok(f"{T}（390）跳出問卷", bool(got))
    M = """() => { const r = document.querySelector('#svOv .svbox').getBoundingClientRect(), f = (document.querySelector('.svft') || document.querySelector('.svbox')).getBoundingClientRect();
        const bs = [...document.querySelectorAll('#svOv button')].filter(e => e.offsetParent);
        const small = bs.filter(e => { const q = e.getBoundingClientRect(); return q.height < 32 || q.width < 32; }).map(e => e.id || e.className);
        const fs = Math.min(...[...document.querySelectorAll('#svOv *')].filter(e => e.children.length === 0 && (e.textContent||'').trim() && e.offsetParent).map(e => parseFloat(getComputedStyle(e).fontSize)));
        const over = [...document.querySelectorAll('#svOv .svbox *')].filter(e => e.offsetParent && e.getBoundingClientRect().right > r.right + 1).length;
        return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, fb: f.bottom, vh: innerHeight, vw: innerWidth, sx: document.documentElement.scrollWidth, small, fs, over }; }"""
    def chk(tag):
        m = pg.evaluate(M)
        ok(f"{T}（390）{tag}：在螢幕內、無橫向捲軸、按鈕 ≥32px、字 ≥11px、沒有超出框", m["bottom"] <= m["vh"] + 1 and m["top"] >= 0 and m["left"] >= 0 and m["right"] <= m["vw"] + 1 and m["sx"] <= m["vw"] and not m["small"] and m["fs"] >= 11 and m["over"] == 0 and m["fb"] <= m["vh"] + 1, m)
    chk("第1題"); shot(pg, "7_mobile_step1")
    pg.click("[data-sat='3']"); pg.click("#svNext"); pg.wait_for_timeout(200)
    pg.click("[data-par='flow']"); pg.click("#svSub .svchip >> nth=0")
    chk("第2題展開子分頁"); shot(pg, "8_mobile_step2")
    for k in ("overview", "heatmap", "etf", "market", "season"):
        pg.click(f"[data-par='{k}']")
    ok(f"{T}（390）第 6 個被擋並提示", "最多選 5 個" in pg.locator(".svwarn").inner_text() and pg.locator(".svpar.on").count() == 5)
    chk("擋下提示後"); shot(pg, "9_mobile_limit")
    pg.click("#svNext"); chk("第3題"); pg.click("#svNext"); chk("第4題"); shot(pg, "10_mobile_step4")
    pg.click("#svSend"); pg.wait_for_timeout(500)
    ok(f"{T}（390）送出後顯示新截止日", "2026-11-17" in (pg.locator("#svOkMsg").inner_text() if pg.locator("#svOkMsg").count() else ""))
    chk("成功畫面"); shot(pg, "11_mobile_success")
    c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("問卷1101", lambda pg, b, base, code: t_survey_popup_1101(b, base, code))
