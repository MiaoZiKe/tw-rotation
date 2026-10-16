# 驗收段落「客服聊天室1016」（Andy 10-16：「寄信拿掉，意見反饋和願望那邊改成聊天室的形式，下方可以附上Mail 但mail 是 liguligu0818那個。
# 可以參考IG那樣，目的是為了更快回覆訊息。做一版預覽版本看看」）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、MOBILE_VP、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
#
# 本機起真的 worker.js（devserver.mjs），真人操作走完：
#   ① 訪客：面板只剩「常見問題｜意見・願望」（寄信分頁不見）、底部一行信箱（可複製）、選標籤＋Enter 送出 → 右邊出現泡泡、後端真的收到
#      （第二則關掉「附上目前頁面」＋選「願望」→ 後端那則沒有網址、type＝wish）
#   ② 管理者：#admin/feedback 收件匣 → 那位訪客一列＋未讀數 → 點開未讀消失 → 常用回覆一鍵帶入 → 送出 → 右邊出現回覆
#   ③ 訪客重新整理 → 右下角比比亮紅點「1」→ 打開聊天室看到站方回覆（左邊）→ 紅點消失、後端未讀歸零
#   ④ 會員登入後送出 → 收件匣出現會員名字
#   ⑤ 後端還是舊版（/v1/chat/mine 回 404）→ 頂端說明、送出照樣進 /v1/feedback
#   ⑥ 預覽示範（window.__supDemo）：頂端「預覽示範：訊息不會真的送出」、有示範紅點、送出不打任何 API、示範回覆出現；示範收件匣能回覆
#   ⑦ 手機 390：全螢幕聊天、沒有橫向捲軸、字 ≥ 11px、輸入框 16px、鍵盤彈出（可視高度變矮）時輸入列仍在畫面內；手機收件匣點進對話／返回
def t_support_chat_1016(b, base, code):
    import urllib.request
    import urllib.parse
    T = "客服聊天室1016"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_CHAT_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)

    class _NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedir)

    def raw(path, method="GET", body=None, headers=None):
        req = urllib.request.Request(api + path, data=body, method=method, headers=headers or {})
        try:
            r = opener.open(req, timeout=5)
            return r.status, dict(r.headers), r.read().decode("utf8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf8", "replace")

    def post(path, body):
        s, _, t = raw(path, "POST", json.dumps(body).encode(), {"Origin": origin, "content-type": "text/plain"})
        try:
            return s, json.loads(t or "{}")
        except Exception:  # noqa: BLE001
            return s, {}

    def token(who):
        # 走一次真的登入流程（start → 假 Google → callback → redeem），拿權杖直接塞進 localStorage —— 登入畫面本身由「登入卡住1016」驗
        n = "n" + str(int(time.time() * 1000)) + who + "x" * 20
        s, h, _ = raw(f"/auth/start?n={n}&mode=popup&ret=" + urllib.parse.quote(base))
        loc = h.get("Location") or h.get("location")
        cookie = (h.get("Set-Cookie") or h.get("set-cookie") or "").split(";")[0]
        _, _, page = raw(urllib.parse.urlparse(loc).path + "?" + urllib.parse.urlparse(loc).query)
        href = re.search(r'id="as-' + who + r'" href="([^"]+)"', page).group(1).replace("&amp;", "&")
        u = urllib.parse.urlparse(href)
        raw(u.path + "?" + u.query, headers={"Cookie": cookie})
        return post("/auth/redeem", {"n": n})[1].get("tok")

    def ctx(w=1440, tok=None, demo=False, theme=None, h=None):
        kw = dict(**MOBILE_VP) if w <= 640 else dict(viewport={"width": w, "height": h or 900})
        c = b.new_context(**kw)
        init = ""
        if not demo:
            init += "window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";"
        else:
            init += "window.TW_ACCOUNT_OVERRIDE = {api: 'about:blank'}; window.__supDemo = true;"
        init += "try { localStorage.setItem('tw.tour.done', '1');" + (f"localStorage.setItem('tw.acct.tok', {json.dumps(tok)});" if tok else "") \
            + (f"localStorage.setItem('tw.theme', {json.dumps(theme)});" if theme else "") + " } catch (e) {}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        return c

    def page(c, hash_="#overview"):
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + hash_, wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('supFab') && !!window.TwSupport", 10000)
        return pg

    def open_chat(pg, mob=False):
        if mob:
            pg.evaluate("() => TwSupport.open('faq')")      # 手機第一下點比比是展開環狀選單（bibi.js），環上的「問比比」才開面板 —— 這裡直接開
            pg.wait_for_selector("#supPanel:not([hidden])", timeout=4000)
            pg.locator("#supPanel .sptabs button[data-t='fb']").tap()
        else:
            pg.click("#supFab")
            pg.wait_for_selector("#supPanel:not([hidden])", timeout=4000)
            pg.click("#supPanel .sptabs button[data-t='fb']")
        pg.wait_for_selector("#chIn", timeout=4000)
        wait_until(pg, "() => !/載入對話中/.test(document.getElementById('chLog').textContent)", 5000)

    def mine_bubbles(pg):
        return pg.evaluate("() => [...document.querySelectorAll('#chLog .chm.r .tx')].map(e => e.textContent)")

    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api（devserver）起得來", up):
            return
        andy = token("andy")
        bob = token("bob")
        ok(f"{T}：拿到管理者與會員的權杖", bool(andy and bob))

        # ① 訪客
        c = ctx()
        pg = page(c)
        pg.click("#supFab")
        pg.wait_for_selector("#supPanel:not([hidden])", timeout=4000)
        tabs = pg.evaluate("() => [...document.querySelectorAll('#supPanel .sptabs button')].map(b => b.dataset.t + ':' + b.textContent.trim())")
        ok(f"{T}：分頁只剩「常見問題｜意見・願望」，寄信分頁不見了", tabs == ["faq:常見問題", "fb:意見・願望"] and pg.locator("#supPanel [data-t='mail']").count() == 0, tabs)
        mr = pg.evaluate("""() => { const p = document.getElementById('supPanel').getBoundingClientRect(), r = document.getElementById('supMailRow');
            const q = r.getBoundingClientRect(); return { txt: r.textContent, gap: Math.round(p.bottom - q.bottom), href: document.getElementById('supMail').getAttribute('href') }; }""")
        ok(f"{T}：面板最底下一行信箱 liguligu0818@gmail.com（點了開 Gmail 撰寫）", "liguligu0818@gmail.com" in mr["txt"] and 0 <= mr["gap"] <= 2
           and "to=liguligu0818%40gmail.com" in (mr["href"] or ""), mr)
        c.grant_permissions(["clipboard-read", "clipboard-write"])
        pg.click("#supCopy")
        ok(f"{T}：按「複製」→ 鈕變「已複製」", bool(wait_until(pg, "() => document.getElementById('supCopy').textContent === '已複製'", 2000)))
        pg.click("#supPanel .sptabs button[data-t='fb']")
        pg.wait_for_selector("#chIn", timeout=4000)
        ok(f"{T}：聊天室：正式模式（沒有示範標示）、第一句是比比的歡迎", pg.locator("#chDemo").count() == 0
           and "站方真人會在這裡回覆你" in pg.inner_text("#chLog .chm.l.sys"), pg.evaluate("() => TwSupport.chat.state()"))
        ok(f"{T}：舊的表單元件都不在了（類別下拉、email 欄、送出大按鈕）", pg.locator("#fbCat, #fbMail, #fbBody, #wsWant").count() == 0)
        pg.click("#chTags button[data-tag='bug']")
        ok(f"{T}：點「錯誤回報」標籤 → 亮起（單選）", pg.evaluate("() => [...document.querySelectorAll('#chTags button.on')].map(b => b.dataset.tag).join()") == "bug")
        n0 = len(mine_bubbles(pg))
        pg.fill("#chIn", "1016 驗收：K 線切週期後空白")
        pg.press("#chIn", "Enter")
        good = wait_until(pg, "() => [...document.querySelectorAll('#chLog .chm.r')].some(e => /K 線切週期後空白/.test(e.textContent) && !e.classList.contains('sending'))", 5000)
        ok(f"{T}：按 Enter 送出 → 右邊多一個泡泡、輸入框清空、狀態「已送出」", bool(good) and len(mine_bubbles(pg)) == n0 + 1 and pg.input_value("#chIn") == ""
           and "已送出" in pg.inner_text("#chLog .chm.r:last-of-type .mt"), mine_bubbles(pg))
        ok(f"{T}：泡泡上有分類「錯誤回報」與「附上頁面：#overview」", "錯誤回報" in pg.inner_text("#chLog .chm.r:last-of-type .chtag") and "#overview" in pg.inner_text("#chLog .chm.r:last-of-type .churl"))
        gk = pg.evaluate("() => localStorage.getItem('tw.sup.gk')")
        ok(f"{T}：訪客第一次送出才產生這個瀏覽器的對話識別碼", bool(gk and len(gk) >= 20), gk)
        pg.click("#chTags button[data-tag='wish']")
        pg.click("label.chsw")
        ok(f"{T}：關掉「附上目前頁面」開關", not pg.is_checked("#chCtx"))
        pg.fill("#chIn", "想要自選股的價格提醒")
        pg.click("#fbSend")
        wait_until(pg, "() => [...document.querySelectorAll('#chLog .chm.r')].some(e => /價格提醒/.test(e.textContent) && !e.classList.contains('sending'))", 5000)
        s, L = post("/v1/admin/chat/list", {"t": andy})
        cg = next((x for x in L.get("convs", []) if x["ck"].startswith("g:")), None)
        ok(f"{T}：後端真的收到：一串訪客對話、2 則未讀、最後一句是願望", bool(cg) and cg["n"] == 2 and cg["unread"] == 2 and cg["wish"] == 1 and "價格提醒" in cg["last"]["body"], L)
        th = post("/v1/admin/chat/thread", {"t": andy, "ck": cg["ck"], "peek": True})[1] if cg else {}
        ms = th.get("msgs", [])
        ok(f"{T}：第一則 bug＋網址含 #overview；第二則 wish、沒有網址（開關關掉）", len(ms) == 2 and ms[0]["cat"] == "bug" and "#overview" in ms[0].get("url", "")
           and ms[1]["type"] == "wish" and not ms[1].get("url"), ms)
        if shots:
            pg.locator("#supPanel").screenshot(path=str(pathlib.Path(shots) / "chat_panel_1440_dark.png"))

        # ② 管理者收件匣
        ca = ctx(tok=andy)
        pa = ca.new_page(); pa.on("pageerror", lambda e: errs.append(str(e)))
        pa.goto(base + "#admin/feedback", wait_until="domcontentloaded")
        pa.wait_for_selector("#fbInbox .ibr", timeout=10000)
        row = pa.locator(f"#fbInbox .ibr[data-ck='{cg['ck']}']")
        ok(f"{T}：收件匣有那位訪客一列、未讀紅點 2、顯示最後一句", row.count() == 1 and row.locator(".ibdot").inner_text() == "2" and "價格提醒" in row.inner_text(), row.inner_text() if row.count() else None)
        ok(f"{T}：統計與完整列表預設收起", pa.evaluate("() => !document.getElementById('fbMore').open"))
        row.click()
        pa.wait_for_selector("#ibLog .chm", timeout=5000)
        ok(f"{T}：點開 → 右邊是對話串（使用者兩則在左）、那一列未讀消失", pa.locator("#ibLog .chm.l").count() == 2 and pa.locator(f"#fbInbox .ibr[data-ck='{cg['ck']}'] .ibdot").count() == 0)
        ok(f"{T}：後端也記成已讀（未讀 0）", post("/v1/admin/chat/list", {"t": andy})[1]["unread"] == 0)
        pa.click("#ibQuick button[data-q='0']")
        ok(f"{T}：點常用回覆 → 帶進輸入框", "我們查一下" in pa.input_value("#ibIn"))
        pa.fill("#ibIn", "已經修好了，請重新整理看看")
        pa.press("#ibIn", "Enter")
        ok(f"{T}：送出回覆 → 右邊出現站方泡泡、清單最後一句變成「你：…」", bool(wait_until(pa, "() => [...document.querySelectorAll('#ibLog .chm.r .tx')].some(e => /已經修好了/.test(e.textContent))", 5000))
           and "你：已經修好了" in pa.inner_text(f"#fbInbox .ibr[data-ck='{cg['ck']}']"))
        if shots:
            pa.locator("#fbInbox").screenshot(path=str(pathlib.Path(shots) / "admin_inbox_1440_dark.png"))
        ca.close()

        # ③ 訪客重新整理：紅點 → 打開看到回覆 → 紅點消失
        pg.reload(wait_until="domcontentloaded")
        badge = wait_until(pg, "() => { const b = document.querySelector('#supFab .supbadge'); return b && b.textContent === '1'; }", 9000)
        ok(f"{T}：訪客重新整理 → 右下角比比紅點「1」（站方回覆未讀）", bool(badge))
        open_chat(pg)
        ok(f"{T}：打開聊天室 → 站方回覆在左邊", "已經修好了" in " ".join(pg.evaluate("() => [...document.querySelectorAll('#chLog .chm.l .tx')].map(e => e.textContent)")))
        ok(f"{T}：自己的訊息顯示「已讀」（管理者打開過）", "已讀" in pg.inner_text("#chLog"))
        ok(f"{T}：紅點消失、後端未讀歸零", bool(wait_until(pg, "() => !document.querySelector('#supFab .supbadge')", 3000))
           and post("/v1/chat/mine", {"gk": gk})[1].get("unread") == 0)
        ok(f"{T}：別的瀏覽器（另一個識別碼）讀不到這串", post("/v1/chat/mine", {"gk": "other_" + "z" * 24})[1].get("msgs") == [])
        c.close()

        # ④ 會員
        cm = ctx(tok=bob)
        pm = page(cm)
        wait_until(pm, "() => !!(window.TwAccount && TwAccount.user())", 8000)
        open_chat(pm)
        ok(f"{T}：會員：沒有「訪客」提示", "訪客" not in pm.inner_text(".chopt"))
        pm.fill("#chIn", "會員的問題：方案怎麼升級")
        pm.click("#fbSend")
        wait_until(pm, "() => [...document.querySelectorAll('#chLog .chm.r')].some(e => /方案怎麼升級/.test(e.textContent) && !e.classList.contains('sending'))", 5000)
        L = post("/v1/admin/chat/list", {"t": andy})[1]
        cmv = next((x for x in L["convs"] if x["member"]), None)
        ok(f"{T}：收件匣出現會員（名字 Bob）", bool(cmv) and "Bob" in cmv["name"] and cmv["email"] == "bob@example.com", L)
        cm.close()

        # ⑤ 後端還是舊版（/v1/chat/mine 404）
        cl = ctx(tok=bob)
        hits = {"fb": 0}

        def old_worker(route):
            route.fulfill(status=404, body='{"error":"not_found"}', headers={"access-control-allow-origin": "*", "content-type": "application/json"})

        def count_fb(route):
            hits["fb"] += 1
            route.continue_()
        cl.route(api + "/v1/chat/mine", old_worker)
        cl.route(api + "/v1/feedback", count_fb)
        pl = page(cl)
        wait_until(pl, "() => !!(window.TwAccount && TwAccount.user())", 8000)
        open_chat(pl)
        ok(f"{T}：舊版後端 → 頂端說明「對話紀錄更新中」", bool(wait_until(pl, "() => !!document.getElementById('chLegacy')", 4000)))
        pl.fill("#chIn", "舊後端也送得出去")
        pl.click("#fbSend")
        ok(f"{T}：舊版後端 → 送出照樣打 /v1/feedback、泡泡留在畫面", bool(wait_until(pl, "() => [...document.querySelectorAll('#chLog .chm.r')].some(e => /舊後端/.test(e.textContent) && !e.classList.contains('sending'))", 5000)) and hits["fb"] == 1, hits)
        cl.close()

        # ⑥ 預覽示範
        for theme in ("dark", "light"):
            cd = ctx(demo=True, theme=theme)
            reqs: list = []
            cd.on("request", lambda r: reqs.append(r.url) if ("/v1/feedback" in r.url or "/v1/chat" in r.url) else None)
            pd = page(cd)
            if theme == "dark":
                ok(f"{T}：預覽示範 → 一進站就有示範紅點（站方回覆未讀）", bool(wait_until(pd, "() => !!document.querySelector('#supFab .supbadge')", 6000)))
            open_chat(pd)
            if theme == "dark":
                ok(f"{T}：預覽示範 → 頂端「預覽示範：訊息不會真的送出」", pd.inner_text("#chDemo") == "預覽示範：訊息不會真的送出")
                n1 = len(mine_bubbles(pd))
                pd.fill("#chIn", "預覽版試打一句")
                pd.press("#chIn", "Enter")
                ok(f"{T}：預覽示範 → 送出後本機顯示泡泡、1.2 秒後出現示範回覆、沒有打任何 API",
                   bool(wait_until(pd, "() => /示範回覆/.test(document.getElementById('chLog').textContent)", 4000)) and len(mine_bubbles(pd)) == n1 + 1 and not reqs, reqs)
            if shots:
                pd.wait_for_timeout(300)
                pd.locator("#supPanel").screenshot(path=str(pathlib.Path(shots) / f"chat_panel_1440_{theme}_demo.png"))
            pd.goto(base + "#admin/feedback", wait_until="domcontentloaded")
            pd.wait_for_selector("#fbInbox .ibr", timeout=10000)
            if theme == "dark":
                ok(f"{T}：預覽示範收件匣 → 標「示範資料」、5 位、未讀篩選只剩有紅點的", pd.locator("#ibDemo").count() == 1 and pd.locator("#fbInbox .ibr").count() == 5)
                pd.click("#ibFlt button[data-f='unread']")
                ok(f"{T}：點「未讀」篩選 → 只剩有紅點的", pd.locator("#fbInbox .ibr").count() == pd.locator("#fbInbox .ibr .ibdot").count() > 0)
                pd.click("#ibFlt button[data-f='']")
                pd.fill("#ibQ", "陳怡君")
                ok(f"{T}：搜尋「陳怡君」→ 只剩一列", pd.locator("#fbInbox .ibr").count() == 1)
                pd.fill("#ibQ", "")
            pd.locator("#fbInbox .ibr").first.click()
            pd.wait_for_selector("#ibIn", timeout=4000)
            pd.fill("#ibIn", "示範回覆一句")
            pd.click("#ibSend")
            ok(f"{T}：示範收件匣（{theme}）→ 回覆出現在右邊", bool(wait_until(pd, "() => [...document.querySelectorAll('#ibLog .chm.r .tx')].some(e => e.textContent === '示範回覆一句')", 3000)))
            if shots:
                pd.locator("#fbInbox").screenshot(path=str(pathlib.Path(shots) / f"admin_inbox_1440_{theme}_demo.png"))
            cd.close()

        # ⑦ 手機 390
        for theme in ("dark", "light"):
            c3 = ctx(390, demo=True, theme=theme)
            p3 = page(c3)
            open_chat(p3, mob=True)
            g = p3.evaluate("""() => { const p = document.getElementById('supPanel'), r = p.getBoundingClientRect(), bar = document.querySelector('.chbar').getBoundingClientRect();
                const els = [...p.querySelectorAll('*')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && e.getClientRects().length);
                const minFs = Math.min(...els.map(e => parseFloat(getComputedStyle(e).fontSize)));
                return { full: p.classList.contains('chfull'), x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), vw: innerWidth, vh: innerHeight,
                  barB: Math.round(bar.bottom), sw: document.documentElement.scrollWidth, psw: p.scrollWidth, minFs, taFs: parseFloat(getComputedStyle(document.getElementById('chIn')).fontSize) }; }""")
            ok(f"{T}：手機 390（{theme}）→ 全螢幕聊天（面板＝整個畫面）", g["full"] and g["x"] == 0 and g["y"] == 0 and g["w"] == g["vw"] and abs(g["h"] - g["vh"]) <= 1, g)
            ok(f"{T}：手機 390（{theme}）→ 沒有橫向捲軸、字 ≥ 11px、輸入框 16px（iPhone 不自動放大）", g["sw"] <= g["vw"] and g["psw"] <= g["vw"] and g["minFs"] >= 11 and g["taFs"] == 16, g)
            ok(f"{T}：手機 390（{theme}）→ 輸入列在畫面內", g["barB"] <= g["vh"], g)
            if theme == "dark":
                p3.locator("#chIn").tap()
                p3.fill("#chIn", "手機送一句")
                p3.locator("#fbSend").tap()
                ok(f"{T}：手機 → 點送出鈕 → 泡泡出現", bool(wait_until(p3, "() => [...document.querySelectorAll('#chLog .chm.r .tx')].some(e => e.textContent === '手機送一句')", 3000)))
                p3.set_viewport_size({"width": 390, "height": 480})      # 模擬鍵盤彈出：可視高度變矮
                p3.wait_for_timeout(300)
                k = p3.evaluate("() => ({ h: Math.round(document.getElementById('supPanel').getBoundingClientRect().height), barB: Math.round(document.querySelector('.chbar').getBoundingClientRect().bottom), vh: innerHeight })")
                ok(f"{T}：手機 → 可視高度變矮（鍵盤）→ 面板跟著縮、輸入列仍在畫面內", abs(k["h"] - 480) <= 1 and k["barB"] <= 480, k)
                p3.set_viewport_size({"width": 390, "height": 844})
                p3.wait_for_timeout(200)
            if shots:
                p3.wait_for_timeout(300)
                p3.screenshot(path=str(pathlib.Path(shots) / f"chat_mobile_390_{theme}.png"))
            p3.locator("#supClose").tap()
            ok(f"{T}：手機 → 關掉面板 → 比比回來、全螢幕狀態解除", bool(wait_until(p3, "() => !document.documentElement.classList.contains('supchat-full') && document.getElementById('supPanel').hidden", 2000)))
            p3.goto(base + "#admin/feedback", wait_until="domcontentloaded")
            p3.wait_for_selector("#fbInbox .ibr", timeout=10000)
            p3.locator("#fbInbox .ibr").first.tap()
            p3.wait_for_selector("#ibBack", state="visible", timeout=4000)
            m = p3.evaluate("() => ({ list: getComputedStyle(document.querySelector('.ibl')).display, sw: document.documentElement.scrollWidth, vw: innerWidth })")
            ok(f"{T}：手機收件匣（{theme}）→ 點一列 → 對話全寬、清單收起、沒有橫向捲軸", m["list"] == "none" and m["sw"] <= m["vw"], m)
            if shots:
                p3.screenshot(path=str(pathlib.Path(shots) / f"admin_inbox_mobile_390_{theme}.png"))
            p3.locator("#ibBack").tap()
            ok(f"{T}：手機收件匣 → 按 ‹ 回清單", p3.evaluate("() => getComputedStyle(document.querySelector('.ibl')).display") != "none")
            c3.close()
        ok(f"{T}：沒有頁面錯誤", not errs, errs[:5])
    finally:
        dev.terminate()


register("客服聊天室1016", lambda pg, b, base, code: t_support_chat_1016(b, base, code))
