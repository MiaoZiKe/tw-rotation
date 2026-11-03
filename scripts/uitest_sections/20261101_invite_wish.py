# 驗收段落「好友邀請許願1101」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# 帳號選單「邀請好友／許願」（site/invite.js）。用 page.route 假後端，契約見 docs/api/20261101_member_promo.md。
# 驗：後端 404 → 選單沒這一項；有後端 → 開得了、碼與連結對、複製、兌換成功與各種錯誤碼的訊息、許願送出與覆寫；桌機 1440、手機 390。
INV_API = "https://acct-invite.example.test"


def t_invite_wish_1101(b, base, code):
    import json as _j, re as _r
    T = "好友邀請許願1101"
    errs: list[str] = []

    def make_ctx(width, st):
        mobile = width <= 640
        c = b.new_context(viewport={"width": width, "height": 844 if mobile else 900}, has_touch=mobile, is_mobile=mobile,
                          permissions=["clipboard-read", "clipboard-write"] if not mobile else [])
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _j.dumps({"api": INV_API}) + "; try { localStorage.setItem('tw.acct.tok', 'tok-test'); localStorage.setItem('tw.tour','done'); localStorage.setItem('tw.live.on','0'); } catch (e) {}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())

        def handle(route):
            req = route.request
            path = _r.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
            cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST", "content-type": "application/json"}
            if req.method == "OPTIONS":
                return route.fulfill(status=204, headers=cors)
            try:
                bd = _j.loads(req.post_data or "{}")
            except Exception:  # noqa: BLE001
                bd = {}
            code_, out = 200, {}
            if path == "/v1/me":
                out = {"user": {"email": "member@example.com", "name": "測試會員", "admin": False}}
            elif path == "/v1/perm/me":
                out = {"who": "member", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
            elif path == "/v1/notices":
                out = {"notices": []}
            elif path.startswith("/v1/invite/") or path.startswith("/v1/wish"):
                if not st["on"]:
                    code_, out = 404, {"error": "not_found"}
                elif path == "/v1/invite/me":
                    out = {"code": "AB12CD34", "link": "https://liguligu-puipui.com/?invite=AB12CD34", "redeemed_count": st.get("cnt", 3), "reward_days_total": 28, **st.get("extra", {}),
                           "can_redeem": st["can"], "redeemed": st["redeemed"], "pro_days": 14}
                elif path == "/v1/invite/redeem":
                    st["calls"].append(("redeem", bd))
                    if st["err"]:
                        code_, out = st["err"][1], {"error": st["err"][0]}
                    else:
                        st["can"] = False; st["redeemed"] = {"at": 1, "pro_until": "2026-11-15"}; st["pro"] = True
                        out = {"ok": True, "pro_until": "2026-11-15", "pro_end": 1, "days": 14}
                elif path == "/v1/wish/mine":
                    out = {"ok": st["pro"], "wish": st["wish"]}
                elif path == "/v1/wish":
                    st["calls"].append(("wish", bd))
                    rep = st["wish"] is not None
                    st["wish"] = {"at": 1, "feature": bd.get("feature"), "text": bd.get("text"), "status": "doing" if rep else "new"}
                    out = {"ok": True, "replaced": rep}
            route.fulfill(status=code_, body=_j.dumps(out), headers=cors)
        c.route(INV_API + "/**", handle)
        return c

    def open_menu(pg, mobile):
        pg.click("#acctBtn", timeout=60000) if pg.locator("#acctBtn").count() else None
        pg.wait_for_selector("#acctMenu:not([hidden])", timeout=30000)

    for W in (1440, 390):
        mobile = W <= 640
        tag = f"{T}（{W}）"
        # ---- A. 後端 404：選單沒有這一項
        st = {"on": False, "can": True, "redeemed": None, "pro": False, "wish": None, "err": None, "calls": []}
        c = make_ctx(W, st)
        try:
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwAccount && TwAccount.user()", 12000)
            pg.wait_for_timeout(800)
            open_menu(pg, mobile)
            ok(f"★ {tag}後端還沒開（404）→ 帳號選單沒有「邀請好友」", pg.locator("#acctMenu [data-inv]").count() == 0)
        finally:
            c.close()
        # ---- B. 有後端
        st = {"on": True, "can": True, "redeemed": None, "pro": False, "wish": None, "err": None, "calls": []}
        c = make_ctx(W, st)
        try:
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            pg.goto(base + "?invite=zz99yy88#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwAccount && TwAccount.user() && window.TwInvite && TwInvite.state().st === 'ok'", 12000)
            open_menu(pg, mobile)
            item = pg.locator("#acctMenu [data-inv='open']")
            ok(f"★ {tag}有後端 → 帳號選單出現「邀請好友／許願」", item.count() == 1)
            item.first.click(); pg.wait_for_selector("#invDlg:not([hidden])", timeout=5000)
            ok(f"{tag}按下去 → 選單收起、對話框打開", pg.evaluate("() => document.getElementById('acctMenu').hidden"))
            ok(f"{tag}顯示邀請碼 AB12CD34 與連結", pg.inner_text("#invCode") == "AB12CD34" and "invite=AB12CD34" in pg.input_value("#invLink"))
            ok(f"{tag}顯示已有 3 位朋友使用、已累積 28 天、文案寫「你也得 14 天 Pro」", "3" in pg.inner_text("#invCnt") and pg.inner_text("#invDays") == "28" and "你也得 14 天 Plus" in pg.inner_text("#invDlg"))
            ok(f"★ {tag}進度：已邀請 3 人・再邀 2 人升級 Pro（7 天）、進度條 3/5", pg.inner_text("#invProgTxt") == "已邀請 3 人・再邀 2 人升級 Pro（7 天）" and pg.get_attribute("#invDlg [role=progressbar]", "aria-valuenow") == "3" and abs(pg.evaluate("() => document.querySelector('#invDlg .invbar i').getBoundingClientRect().width / document.querySelector('#invDlg .invbar').getBoundingClientRect().width") - 0.6) < 0.05)
            if os.environ.get("TW_INV_SHOT"):
                os.makedirs(os.environ["TW_INV_SHOT"], exist_ok=True); pg.screenshot(path=f"{os.environ['TW_INV_SHOT']}/invite_{W}_a.png")
            ok(f"{tag}邀請連結帶來的碼已預填（ZZ99YY88）", pg.input_value("#invIn") == "ZZ99YY88")
            r = pg.evaluate("""() => { const d = document.querySelector('#invDlg .box').getBoundingClientRect(); const vw = innerWidth;
              const small = [...document.querySelectorAll('#invDlg *')].filter(e => e.offsetParent && e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11).length;
              return { right: d.right, vw, sx: document.documentElement.scrollWidth, small,
                       btn: Math.min(...[...document.querySelectorAll('#invDlg .invbtn')].map(e => e.getBoundingClientRect().height)) } }""")
            ok(f"★ {tag}對話框不超出畫面、無橫向捲軸、字 ≥ 11px、按鈕高 ≥ {44 if mobile else 38}px", r["right"] <= r["vw"] + 1 and r["sx"] <= r["vw"] + 1 and r["small"] == 0 and r["btn"] >= (43.5 if mobile else 37.5), r)
            if not mobile:
                pg.click("[data-inv='copy-code']"); pg.wait_for_timeout(900)
                ok(f"{tag}按「複製邀請碼」→ 剪貼簿真的是 AB12CD34", pg.evaluate("() => navigator.clipboard.readText()") == "AB12CD34")
                ok(f"{tag}複製後有提示文字", "已複製" in pg.inner_text("#invCopyMsg"))
            # 錯誤碼
            for err, want in (("bad_code", "找不到"), ("used", "用過"), ("same_ip", "網路"), ("not_new", "7 天")):
                st["err"] = (err, 409 if err == "used" else 400)
                pg.fill("#invIn", "AAAA1111"); pg.click("#invGo"); pg.wait_for_timeout(500)
                ok(f"{tag}兌換失敗 {err} → 顯示「{want}」且按鈕可再按", want in pg.inner_text("#invMsg") and not pg.evaluate("() => document.getElementById('invGo').disabled"), pg.inner_text("#invMsg"))
            # 空白
            pg.fill("#invIn", ""); pg.click("#invGo")
            ok(f"{tag}沒填碼按兌換 → 提示先輸入、不打 API", "請先輸入" in pg.inner_text("#invMsg") and not [x for x in st["calls"] if x[1].get("code") == ""])
            # 成功
            st["err"] = None; n0 = len(st["calls"])
            pg.fill("#invIn", "ab12cd34"); pg.click("#invGo")
            wait_until(pg, "() => !document.getElementById('invIn')", 5000)
            ok(f"★ {tag}兌換成功 → 後端收到大寫碼、輸入框換成「已兌換 … 2026-11-15」", st["calls"][n0][1].get("code") == "AB12CD34" and "2026-11-15" in pg.inner_text("#invDlg .ok"), st["calls"][-1])
            # 許願（兌換後變 Pro）
            wait_until(pg, "() => !!document.getElementById('invWf')", 5000)
            if os.environ.get("TW_INV_SHOT"):
                pg.screenshot(path=f"{os.environ['TW_INV_SHOT']}/invite_{W}_b.png")
            RECT = """(pos) => { const bx = document.querySelector('#invDlg .box'); bx.scrollTop = pos < 0 ? bx.scrollHeight : pos;
              const g = document.getElementById('invWgo').getBoundingClientRect(); const rows = bx.querySelectorAll(':scope > .row2'); const c = rows[rows.length - 1].getBoundingClientRect();
              const hit = !(g.right <= c.left || g.left >= c.right || g.bottom <= c.top || g.top >= c.bottom);
              return { hit, g: [g.top, g.bottom], c: [c.top, c.bottom], st: getComputedStyle(document.getElementById('invWgo').parentElement).position } }"""
            for pos in (0, -1):
                rr = pg.evaluate(RECT, pos)
                ok(f"★ {tag}捲動位置 {'頂端' if pos == 0 else '底端'}：「送出願望」鈕與底部「關閉」列不相交", not rr["hit"], rr)
            if os.environ.get("TW_INV_SHOT"):
                pg.screenshot(path=f"{os.environ['TW_INV_SHOT']}/invite_{W}_bottom.png")
            pg.evaluate("() => { document.querySelector('#invDlg .box').scrollTop = 0; }")
            pg.fill("#invWf", "自選提醒"); pg.fill("#invWt", "短"); pg.click("#invWgo")
            ok(f"{tag}願望內容太短 → 提示至少 6 字、不打 API", "6" in pg.inner_text("#invWmsg") and not [x for x in st["calls"] if x[0] == "wish"])
            pg.fill("#invWt", "到價時用 Email 通知我，不用一直盯盤"); pg.click("#invWgo")
            wait_until(pg, "() => document.getElementById('invWst')", 5000)
            w1 = [x for x in st["calls"] if x[0] == "wish"]
            ok(f"★ {tag}送出願望 → 後端收到功能名稱與內容、畫面顯示「已收到」狀態與更新鈕", len(w1) == 1 and w1[0][1]["feature"] == "自選提醒" and pg.inner_text("#invWst") == "已收到" and "更新願望" in pg.inner_text("#invWgo"), w1)
            pg.fill("#invWt", "改成：到價時用 LINE 通知我"); pg.click("#invWgo"); pg.wait_for_timeout(600)
            w2 = [x for x in st["calls"] if x[0] == "wish"]
            ok(f"{tag}再送一次 → 覆寫（後端第二筆是新內容）", len(w2) == 2 and "LINE" in w2[1][1]["text"], w2[-1:])
            pg.evaluate("() => TwInvite.open({ demo: true })"); pg.wait_for_selector("#invLink", timeout=3000)
            ok(f"★ {tag}示範模式的連結是正式網域、不是 localhost", pg.input_value("#invLink") == "https://liguligu-puipui.com/?invite=DEMO1234", pg.input_value("#invLink"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
            ok(f"{tag}Esc 關閉對話框", pg.evaluate("() => document.getElementById('invDlg').hidden"))
            # 隱私：底部小字連結 → 隱私權政策「意見問卷、許願與邀請碼」展開
            pg.evaluate("() => TwInvite.open()"); pg.wait_for_selector("#invDlg:not([hidden])", timeout=3000)
            wait_until(pg, "() => !!document.querySelector('#invDlg a[href*=privacy-promo]')", 6000)
            lk = pg.locator("#invDlg a[href='#privacy-promo']")
            ok(f"{tag}對話框底部有一行小字連結「資料怎麼使用」", lk.count() == 1 and lk.inner_text() == "資料怎麼使用")
            lk.click(); pg.wait_for_timeout(3500)
            pv = pg.evaluate("""() => { const d = document.getElementById('privacy-promo'); const r = d && d.getBoundingClientRect();
              return { hash: location.hash, hidden: document.getElementById('invDlg').hidden, open: !!d && d.open, vis: !!r && r.top >= 0 && r.bottom <= innerHeight, rect: r && [r.top, r.bottom, innerHeight, scrollY],
                       txt: d ? d.innerText : '', sx: document.documentElement.scrollWidth <= innerWidth + 1 } }""")
            ok(f"★ {tag}按連結 → 跳到隱私權政策、對話框收掉、段落自動展開且在畫面內、含雜湊保存 30 天", pv["hash"] == "#privacy-promo" and pv["hidden"] and pv["open"] and pv["vis"] and "30 天" in pv["txt"] and pv["sx"], pv)
            pg.goto(base + "#privacy", wait_until="domcontentloaded"); pg.wait_for_selector("#privacy-promo", timeout=8000)
            ok(f"{tag}直接開 #privacy → 這段預設收合", not pg.evaluate("() => document.getElementById('privacy-promo').open"))
        finally:
            c.close()
        # ---- C. 沒有 Pro：許願區是說明、不是表單；已不能兌換
        st = {"on": True, "can": False, "redeemed": None, "pro": False, "wish": None, "err": None, "calls": []}
        c = make_ctx(W, st)
        try:
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwInvite && TwInvite.state().st === 'ok'", 12000)
            open_menu(pg, mobile); pg.click("#acctMenu [data-inv='open']"); pg.wait_for_selector("#invDlg:not([hidden])", timeout=5000)
            wait_until(pg, "() => document.getElementById('invCode')", 3000)
            ok(f"★ {tag}沒有 Pro 體驗 → 沒有許願表單、不能輸入邀請碼（只有說明）", pg.locator("#invWt").count() == 0 and pg.locator("#invIn").count() == 0 and "邀請滿 5 人升級 Pro 即可許願" in pg.inner_text("#invDlg"))
        finally:
            c.close()
        # ---- D. 邀滿 5 人（後端新欄位 pro_unlocked／next_pro_need 缺時前端自己算）
        for extra, cnt in (({}, 5), ({"pro_unlocked": True, "next_pro_need": 0}, 6)):
            st = {"on": True, "can": False, "redeemed": None, "pro": True, "wish": None, "err": None, "calls": [], "cnt": cnt, "extra": extra}
            c = make_ctx(W, st)
            try:
                pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
                pg.goto(base + "#overview", wait_until="domcontentloaded")
                wait_until(pg, "() => window.TwInvite && TwInvite.state().st === 'ok'", 12000)
                open_menu(pg, mobile); pg.click("#acctMenu [data-inv='open']"); pg.wait_for_selector("#invDlg:not([hidden])", timeout=5000)
                wait_until(pg, "() => document.getElementById('invProgTxt')", 3000)
                ok(f"★ {tag}邀請 {cnt} 人（{'後端欄位' if extra else '前端計算'}）→ 顯示「已升級 Pro」、進度條滿、許願表單出現", pg.inner_text("#invProgTxt") == "已升級 Pro" and pg.get_attribute("#invDlg [role=progressbar]", "aria-valuenow") == "5" and pg.locator("#invWt").count() == 1)
            finally:
                c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("好友邀請許願1101", lambda pg, b, base, code: t_invite_wish_1101(b, base, code))
