# 驗收段落「使用統計1109」（Andy 11-09：「多一個統計：手機 & 電腦點進去功能」；docs/account_analytics.md「手機與電腦」）
# 由 _uitest.py 用 exec 載入：ok()、wait_until()、ROOT、_free_port… 直接可用。本機起真的 worker.js（devserver），逐一真的操作：
#   ① 電腦訪客（1440）帶 ?u=th-id-20261109 進站 → 開 #overview、#flow、再回 #overview、真的按「切換深淺色」→ 伺服器記到
#      電腦的開站 1、各頁開啟次數（總覽 2、資金流向 1）、各頁不重複訪客（總覽仍是 1）、來源 threads、功能點擊 theme_toggle
#   ② 手機訪客（390、referrer＝instagram）→ 手機的開站、頁面、來源 instagram；跟電腦的數字分開
#   ③ 開「請勿追蹤」的訪客什麼都不記
#   ④ 管理區「流量觀測」出現「手機和電腦」卡：開站數字＝伺服器的數字；切到「不重複訪客」數字真的換了；
#      點「總覽」那一列就地展開（網址不變）；手機 390 沒有橫向捲軸、字不小於 11px
#   ⑤ 隱私權政策有「裝置與來源統計」
# 截圖：TW_USAGE_SHOTS＝資料夾。⚠ --workers 1
US_PEOPLE = {"andy": "andy@example.com"}


def t_usage_1109(b, base, code):
    import urllib.request
    T = "使用統計1109"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in US_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_USAGE_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
    sep = "&" if "?" in base else "?"

    def dev_post(path, body):
        req = urllib.request.Request(api + path, data=json.dumps(body).encode(), headers={"Origin": origin, "content-type": "text/plain"}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=8).read())
        except urllib.error.HTTPError as e:
            return {"_s": e.code, **json.loads(e.read() or b"{}")}

    ctxs = []
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

        def new_ctx(w=1440, dnt=False, mobile=False):
            c = b.new_context(viewport={"width": w, "height": 844 if mobile else 900}, is_mobile=mobile, has_touch=mobile)
            init = "window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}"
            if dnt:
                init += "Object.defineProperty(navigator,'doNotTrack',{get:()=>'1'});"
            c.add_init_script(init)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def consent(pg):
            a = pg.get_by_role("button", name="同意並繼續")
            if a.count() and a.first.is_visible():
                a.first.click(); pg.wait_for_timeout(300)

        def login(pg, who):
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
            pg.evaluate("() => TwAccount.login()")
            pg.wait_for_selector("#acctGo", state="visible", timeout=6000)
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=8000)
            pop.click("#as-" + who)
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        # 管理者先登入拿權杖（之後所有訪客的數字都從 /v1/admin/stats 讀）
        ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#pricing", wait_until="domcontentloaded"); consent(ad)
        login(ad, "andy")
        atok = ad.evaluate("() => TwAccount.tok()")

        def stats():
            """回 {(comp, page, detail): n}，只收 us.* """
            j = dev_post("/v1/admin/stats", {"t": atok, "days": 7})
            o = {}
            for r in j.get("e2", []):
                if r["comp"].startswith("us."):
                    o[(r["comp"], r["page"], r["detail"])] = o.get((r["comp"], r["page"], r["detail"]), 0) + r["n"]
            return o

        def tot(o, comp, page=None):
            return sum(n for (c, p, _d), n in o.items() if c == comp and (page is None or p == page))

        # 管理者自己開 #pricing 也算一次電腦訪客（開站＋pricing 頁），統計事件是登入後才非同步送到伺服器。
        # 先主動 flush，再等伺服器的數字連續 3 次（間隔 0.4 秒）都不變才記基準；
        # 否則管理者分頁的事件會晚到、被誤算進訪客的增量（2026-11-09 穩定紅 2 項的原因）。
        ad.evaluate("() => TwAccount.flush()")
        base0, same = stats(), 0
        for _ in range(40):
            ad.wait_for_timeout(400)
            cur = stats()
            same = same + 1 if cur == base0 else 0
            base0 = cur
            if same >= 3:
                break
        ok(f"{T}：管理者分頁的統計已送完、伺服器數字穩定（基準）", same >= 3 and tot(base0, "us.ses.d") >= 1, (same, tot(base0, "us.ses.d")))

        # ① 電腦訪客
        cd = new_ctx(); pd_ = cd.new_page(); pd_.on("pageerror", lambda e: errs.append("desk: " + str(e)))
        pd_.goto(base + sep + "u=th-id-20261109#overview", wait_until="domcontentloaded"); consent(pd_)
        wait_until(pd_, "() => !!(window.TwAccount && TwAccount.on()) && window.TwUsage", 10000)
        ok(f"{T}：①1440 寬判定為電腦（d）", pd_.evaluate("() => TwUsage.dev()") == "d")
        pd_.wait_for_timeout(600)
        pd_.evaluate("() => { location.hash = '#flow' }"); pd_.wait_for_timeout(500)
        pd_.evaluate("() => { location.hash = '#overview' }"); pd_.wait_for_timeout(500)
        tb = pd_.locator("#themeBtn")
        clicked = False
        if tb.count() and tb.first.is_visible():
            tb.first.click(); clicked = True; pd_.wait_for_timeout(300)
        ok(f"{T}：①真的按了「切換深淺色」", clicked)
        pd_.evaluate("() => TwAccount.flush()"); pd_.wait_for_timeout(900)
        s1 = stats()
        d = lambda comp, page=None: tot(s1, comp, page) - tot(base0, comp, page)
        ok(f"{T}：①伺服器收到電腦開站 +1、不重複訪客 +1", d("us.ses.d") == 1 and d("us.uvs.d") == 1, (d("us.ses.d"), d("us.uvs.d")))
        ok(f"{T}：①總覽被打開 2 次、不重複訪客 1；資金流向打開 1 次、不重複訪客 1",
           d("us.pv.d", "overview") == 2 and d("us.uv.d", "overview") == 1 and d("us.pv.d", "flow") == 1 and d("us.uv.d", "flow") == 1,
           {k: v for k, v in s1.items() if k[0].startswith("us.pv") or k[0].startswith("us.uv.")})
        ok(f"{T}：①來源記成 threads（網址的 ?u= 優先），utm 欄 threads/intraday（活動名去掉日期）",
           s1.get(("us.ref.d", "other", "threads"), 0) - base0.get(("us.ref.d", "other", "threads"), 0) == 1
           and s1.get(("us.utm.d", "other", "threads/intraday"), 0) == 1, [k for k in s1 if k[0].startswith("us.ref") or k[0].startswith("us.utm")])
        ok(f"{T}：①功能點擊：電腦 theme_toggle +1（歸在總覽頁）", s1.get(("us.fe.d", "overview", "theme_toggle"), 0) - base0.get(("us.fe.d", "overview", "theme_toggle"), 0) == 1, [k for k in s1 if k[0].startswith("us.fe")])
        ok(f"{T}：①電腦的動作沒有算到手機", d("us.ses.m") == 0 and d("us.pv.m") == 0 and d("us.fe.m") == 0)

        # ①b 同一個瀏覽器（同一個 context，localStorage 共用）再開一個新分頁 → 開站 +1，但今天的不重複訪客不再 +1、總覽的不重複訪客也不再 +1
        pd2 = cd.new_page(); pd2.on("pageerror", lambda e: errs.append("desk2: " + str(e)))
        pd2.goto(base + "#overview", wait_until="domcontentloaded"); consent(pd2)
        wait_until(pd2, "() => !!(window.TwAccount && TwAccount.on()) && window.TwUsage", 10000)
        pd2.wait_for_timeout(500)
        pd2.evaluate("() => TwAccount.flush()"); pd2.wait_for_timeout(900)
        s1b = stats()
        db = lambda comp, page=None: tot(s1b, comp, page) - tot(s1, comp, page)
        ok(f"{T}：①b同一瀏覽器再開一個分頁：開站 +1、但不重複訪客 +0；總覽打開 +1、總覽不重複訪客 +0",
           db("us.ses.d") == 1 and db("us.uvs.d") == 0 and db("us.pv.d", "overview") == 1 and db("us.uv.d", "overview") == 0,
           (db("us.ses.d"), db("us.uvs.d"), db("us.pv.d", "overview"), db("us.uv.d", "overview")))
        s1 = s1b

        # ② 手機訪客（referrer＝instagram）
        cm = new_ctx(390, mobile=True); pm = cm.new_page(); pm.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
        pm.goto(base + "#overview", wait_until="domcontentloaded", referer="https://l.instagram.com/?u=x"); consent(pm)
        wait_until(pm, "() => !!(window.TwAccount && TwAccount.on()) && window.TwUsage", 10000)
        ok(f"{T}：②390 寬判定為手機（m）", pm.evaluate("() => TwUsage.dev()") == "m")
        pm.wait_for_timeout(500)
        pm.evaluate("() => { location.hash = '#flow' }"); pm.wait_for_timeout(500)
        mt = pm.locator("#mmTheme, #themeBtn")
        mclicked = False
        for i in range(mt.count()):
            if mt.nth(i).is_visible():
                mt.nth(i).click(); mclicked = True; break
        if not mclicked:      # 手機的深淺色鈕收在選單裡，先打開選單
            mm = pm.locator("#mmBtn, .mmenu-btn, button[aria-label*='選單']")
            if mm.count():
                mm.first.click(); pm.wait_for_timeout(300)
                mt = pm.locator("#mmTheme")
                if mt.count() and mt.first.is_visible():
                    mt.first.click(); mclicked = True
        ok(f"{T}：②手機真的按了深淺色鈕", mclicked)
        pm.evaluate("() => TwAccount.flush()"); pm.wait_for_timeout(900)
        s2 = stats()
        d2 = lambda comp, page=None: tot(s2, comp, page) - tot(s1, comp, page)
        ok(f"{T}：②手機開站 +1、總覽 +1、資金流向 +1，電腦沒變", d2("us.ses.m") == 1 and d2("us.pv.m", "overview") == 1 and d2("us.pv.m", "flow") == 1 and d2("us.ses.d") == 0 and d2("us.pv.d") == 0, (d2("us.ses.m"), d2("us.pv.m", "overview"), d2("us.pv.m", "flow"), d2("us.ses.d")))
        ok(f"{T}：②來源記成 instagram（referrer 的分類，不存網址）", s2.get(("us.ref.m", "other", "instagram"), 0) == 1 and not any("instagram.com" in k[2] for k in s2), [k for k in s2 if k[0].startswith("us.ref")])
        ok(f"{T}：②手機的功能點擊記在 us.fe.m", d2("us.fe.m") >= 1 if mclicked else True, [k for k in s2 if k[0].startswith("us.fe")])

        # ③ 請勿追蹤
        cn = new_ctx(dnt=True); pn = cn.new_page(); pn.on("pageerror", lambda e: errs.append("dnt: " + str(e)))
        pn.goto(base + sep + "u=th-id-20261109#overview", wait_until="domcontentloaded"); consent(pn)
        wait_until(pn, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        pn.evaluate("() => { location.hash = '#flow' }"); pn.wait_for_timeout(500)
        pn.evaluate("() => TwAccount.flush()"); pn.wait_for_timeout(900)
        s3 = stats()
        ok(f"{T}：③請勿追蹤：電腦／手機任何 us.* 都沒增加", s3 == s2, {k: s3[k] - s2.get(k, 0) for k in s3 if s3[k] != s2.get(k, 0)})

        # ④ 管理區
        ad.goto(base + "#admin/traffic", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.querySelector('#trUsage')", 12000)
        try:
            ad.select_option("#admDaysSel", "7"); ad.wait_for_timeout(1200)
        except Exception:  # noqa: BLE001
            pass
        wait_until(ad, "() => !!document.querySelector('#trUsage .usk')", 8000)
        kp = ad.evaluate("() => [...document.querySelectorAll('#trUsage .usk > div')].map(d => [d.querySelector('b').textContent.trim(), d.querySelector('span').textContent.trim()])")
        want_ses = (tot(s3, "us.ses.d"), tot(s3, "us.ses.m"))
        ok(f"{T}：④卡片「開站次數」：電腦、手機＝伺服器的數字 {want_ses}", len(kp) == 3 and int(kp[1][0].replace(",", "")) == want_ses[0] and int(kp[2][0].replace(",", "")) == want_ses[1] and kp[0][0] == str(sum(want_ses)), kp)
        rows = ad.evaluate("() => [...document.querySelectorAll('#trUsage .usgrid > div:first-child .bars .bl')].map(e => e.textContent.trim())")
        ok(f"{T}：④「哪些頁被打開」列出總覽、資金流向", "總覽" in rows and "資金流向" in rows, rows)
        refs = ad.evaluate("() => [...document.querySelectorAll('#trUsage .usvl span')].map(e => e.textContent.trim())")
        ok(f"{T}：④「從哪裡來」直條有 Threads、IG", "Threads" in refs and "IG" in refs, refs)
        fes = ad.evaluate("() => [...document.querySelectorAll('#trUsage .usgrid > div:nth-child(2) .bars .bl')].map(e => e.textContent.trim())")
        ok(f"{T}：④「點了哪些功能」有切換深淺色", "切換深淺色" in fes, fes)
        # 切「不重複訪客」
        ad.click("#trUsMet button[data-met=uv]"); ad.wait_for_timeout(400)
        kp2 = ad.evaluate("() => [...document.querySelectorAll('#trUsage .usk > div')].map(d => d.querySelector('b').textContent.trim())")
        want_uv = (tot(s3, "us.uvs.d"), tot(s3, "us.uvs.m"))
        ok(f"{T}：④切到「不重複訪客」數字真的換了（電腦 {want_uv[0]}、手機 {want_uv[1]}）", kp2[1] == str(want_uv[0]) and kp2[2] == str(want_uv[1]) and kp2 != [x[0] for x in kp], (kp2, kp))
        on_ = ad.evaluate("() => document.querySelector('#trUsMet button.on').dataset.met")
        ok(f"{T}：④切換鈕高亮跟著換", on_ == "uv", on_)
        # 點「總覽」就地展開
        url0 = ad.url
        ad.click("#trUsMet button[data-met=pv]"); ad.wait_for_timeout(300)
        ad.click("#trUsage .bars .bl[data-usr=overview]"); ad.wait_for_timeout(400)
        x = ad.evaluate("() => { const e = document.querySelector('#trUsX'); return e ? e.textContent : '' }")
        ok(f"{T}：④點「總覽」→ 就地展開該頁功能點擊（網址不變）", "總覽" in x and "切換深淺色" in x and ad.url == url0, x[:80])
        ad.click("#trUsage .bars .bl[data-usr=overview]"); ad.wait_for_timeout(300)
        ok(f"{T}：④再點一次收起", ad.evaluate("() => !document.querySelector('#trUsX')"))
        if shots:
            ad.locator("#trUsage").screenshot(path=str(pathlib.Path(shots) / "usage_1440.png"))
        # 手機 390 的管理頁
        cmm = new_ctx(390, mobile=True); am = cmm.new_page(); am.on("pageerror", lambda e: errs.append("admin-m: " + str(e)))
        am.goto(base + "#pricing", wait_until="domcontentloaded"); consent(am)
        login(am, "andy")
        am.goto(base + "#admin/traffic", wait_until="domcontentloaded")
        wait_until(am, "() => !!document.querySelector('#trUsage .usk')", 14000)
        am.locator("#trUsage").scroll_into_view_if_needed()
        sw = am.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        small = am.evaluate("() => [...document.querySelectorAll('#trUsage *')].filter(e => e.children.length === 0 && e.textContent.trim() && e.getClientRects().length && parseFloat(getComputedStyle(e).fontSize) < 11).length")
        ok(f"{T}：④手機 390：統計卡沒有橫向捲軸、字不小於 11px", sw <= 0 and small == 0, (sw, small))
        if shots:
            am.locator("#trUsage").screenshot(path=str(pathlib.Path(shots) / "usage_390.png"))

        # ⑤ 隱私權政策
        pp = new_ctx().new_page(); pp.goto(base + "#privacy", wait_until="domcontentloaded"); consent(pp)
        wait_until(pp, "() => document.body.innerText.includes('行銷來源與使用統計')", 6000)
        txt = pp.inner_text("body")
        ok(f"{T}：⑤隱私權政策有「裝置與來源統計」、寫明不存上一頁完整網址與 IP", "裝置與來源統計" in txt and "不保存上一頁的完整網址" in txt)
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()
    ok(f"{T}：整段沒有頁面錯誤", not errs, errs[:3])


# ★ 2026-11-09 手機／電腦使用統計（⚠ --workers 1）
register("使用統計1109", lambda pg, b, base, code: t_usage_1109(b, base, code))
