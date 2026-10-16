# 驗收段落「訂單通知跳轉1016」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 訂單通知跳轉1016（Andy 10-16：「管理者有訂單，點擊後會跳到對應分頁」）
# 本機起真的 worker.js（devserver），1440：
#   ① 會員 gary 送出銀行轉帳匯款資料 → 管理者鈴鐺有「新訂單」→ 通知上寫「前往付款與訂單處理 →」
#      → 點那則 → 換到 #admin/pay、「銀行轉帳訂單」分頁亮著、搜尋框是那張訂單號、那一列標亮並展開明細、在畫面內、網址改回 #admin/pay、通知變已讀
#   ② 會員 fiona 付款開通後申請退款 → 管理者鈴鐺「新申請」→ 點 → 「取消／退款申請」分頁
#   ③ 公告頁 #notices 那則也有「前往…」連結，點了一樣跳過去
#   ④ 一般公告（不是新訂單）點了照舊只是展開、不換頁
NJ_PEOPLE = {"fiona": "fiona@example.com", "gary": "gary@example.com"}


def t_pay_notice_jump_1016(b, base, code):
    import urllib.request
    T = "訂單通知跳轉1016"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in NJ_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_PAY_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)

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

        def new_ctx(w=1440):
            c = b.new_context(viewport={"width": w, "height": 900})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

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

        def call(pg, path, body):
            return pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])

        tpe_today = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 8 * 3600))

        # 前置：管理者定價＋收款帳號＋一則一般公告
        ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        login(ad, "andy")
        r1 = call(ad, "/v1/admin/plans/put", {"id": "plus", "name": "Plus", "feats": {}, "price": 299, "period": "month", "price_year": 2990})
        r2 = call(ad, "/v1/admin/pay/bank/put", {"bank_name": "測試銀行", "bank_code": "999", "account": "000011112222", "holder": "測試戶名"})
        r3 = call(ad, "/v1/admin/notices/put", {"title": "一般公告測試", "body": "這是一則一般公告", "kind": "feature", "audience": "all", "start": int(time.time() * 1000) - 60000, "end": 0})
        atok = ad.evaluate("() => TwAccount.tok()")
        ok(f"{T}：前置：定價、收款帳號、一般公告", all(x.get("_s") == 200 for x in (r1, r2, r3)), (r1, r2, r3))

        # fiona：付款開通 → 申請退款（新申請）；gary：送出匯款資料（新訂單，待確認）
        cf = new_ctx(); pf = cf.new_page(); pf.on("pageerror", lambda e: errs.append("fiona: " + str(e)))
        pf.goto(base + "#pricing", wait_until="domcontentloaded"); login(pf, "fiona")
        fo = call(pf, "/v1/pay/bank/create", {"plan": "plus", "period": "month"})
        call(pf, "/v1/pay/bank/report", {"id": fo.get("id"), "name": "費歐娜", "last5": "11111", "date": tpe_today})
        dev_post("/v1/admin/pay/confirm", {"t": atok, "id": fo.get("id"), "received": fo.get("amount")})
        rqf = call(pf, "/v1/subscribe/change", {"type": "refund", "note": "不需要了"})
        time.sleep(0.05)
        cg = new_ctx(); pgy = cg.new_page(); pgy.on("pageerror", lambda e: errs.append("gary: " + str(e)))
        pgy.goto(base + "#pricing", wait_until="domcontentloaded"); login(pgy, "gary")
        go = call(pgy, "/v1/pay/bank/create", {"plan": "plus", "period": "year"})
        rep = call(pgy, "/v1/pay/bank/report", {"id": go.get("id"), "name": "蓋瑞", "last5": "22222", "date": tpe_today})
        oid = go.get("id")
        ok(f"{T}：前置：fiona 申請退款、gary 送出匯款資料", rqf.get("_s") == 200 and rep.get("_s") == 200 and bool(oid), (rqf, rep))

        # ① 鈴鐺 → 新訂單 → 點 → 銀行轉帳訂單分頁＋那一列
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        ad.reload(wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ntBell')", 10000)
        ad.evaluate("() => TwNotices.refresh()"); wait_until(ad, "() => TwNotices.list().some(n => /^新(訂單|申請)：/.test(n.title))", 8000)   # 鈴鐺有 10 分鐘本機快取
        ad.click("#ntBell")
        it = wait_until(ad, """() => { const b = [...document.querySelectorAll('#ntDrop .ntitem')].find(x => /新訂單：蓋瑞/.test(x.innerText)); return b ? { id: b.dataset.id, go: (b.querySelector('.ntgo') || {}).innerText || '' } : null; }""", 8000)
        ok(f"{T}：管理者鈴鐺有 gary 的「新訂單」，通知上寫「前往付款與訂單處理 →」", bool(it) and "前往付款與訂單處理" in it["go"], it)
        if shots:
            ad.locator("#ntDrop").screenshot(path=str(pathlib.Path(shots) / "notice_jump_bell.png"))
        if it:
            ad.click(f"#ntDrop .ntitem[data-id='{it['id']}']")
            res = wait_until(ad, f"""() => {{ const on = document.querySelector('#payTabs [data-ptab].on'); const tr = document.querySelector('tr.prow.hit[data-oid="{oid}"]');
                if (!on || !tr) return null; const r = tr.getBoundingClientRect();
                return {{ tab: on.dataset.ptab, q: (document.getElementById('pfQ') || {{}}).value, det: !!(tr.nextElementSibling && tr.nextElementSibling.classList.contains('det')), inView: r.top >= 0 && r.bottom <= innerHeight, hash: location.hash, drop: !document.getElementById('ntDrop') || document.getElementById('ntDrop').hidden }}; }}""", 12000)
            ok(f"{T}：點「新訂單」→ 換到付款與訂單「銀行轉帳訂單」分頁、搜尋框是訂單號、那一列標亮＋展開明細＋在畫面內、網址改回 #admin/pay、通知下拉收起",
               bool(res) and res["tab"] == "bankord" and res["q"] == oid and res["det"] and res["inView"] and res["hash"] == "#admin/pay" and res["drop"], res)
            if shots:
                ad.screenshot(path=str(pathlib.Path(shots) / "notice_jump_bankord.png"))
            rd = call(ad, "/v1/notices", {})
            ok(f"{T}：點過的那則變已讀（伺服器）", any(x.get("id") == it["id"] and x.get("read") for x in (rd.get("notices") or [])) or it["id"] in (rd.get("read") or []), [x for x in (rd.get("notices") or []) if x.get("id") == it["id"]])

        # ② 新申請 → 取消／退款申請分頁
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ntBell')", 10000)
        ad.evaluate("() => TwNotices.refresh()"); wait_until(ad, "() => TwNotices.list().some(n => /^新(訂單|申請)：/.test(n.title))", 8000)   # 鈴鐺有 10 分鐘本機快取
        ad.click("#ntBell")
        it2 = wait_until(ad, """() => { const b = [...document.querySelectorAll('#ntDrop .ntitem')].find(x => /新申請：/.test(x.innerText)); return b ? { id: b.dataset.id, go: (b.querySelector('.ntgo') || {}).innerText || '' } : null; }""", 8000)
        ok(f"{T}：管理者鈴鐺有 fiona 的「新申請」，寫「前往取消／退款申請 →」", bool(it2) and "前往取消／退款申請" in it2["go"], it2)
        if it2:
            ad.click(f"#ntDrop .ntitem[data-id='{it2['id']}']")
            on2 = wait_until(ad, "() => { const on = document.querySelector('#payTabs [data-ptab].on'); return on && document.getElementById('payReqs') ? on.dataset.ptab : ''; }", 12000)
            ok(f"{T}：點「新申請」→ 換到「取消／退款申請」分頁、看得到 fiona", on2 == "reqs" and "fiona@example.com" in ad.inner_text("#payReqs"), on2)

        # ③ 公告頁的連結
        ad.goto(base + "#notices", wait_until="domcontentloaded")
        ad.evaluate("() => TwNotices.refresh()")
        wait_until(ad, "() => !!document.querySelector('#v-notices a.ntgo')", 10000)
        hrefs = ad.evaluate("() => [...document.querySelectorAll('#v-notices a.ntgo')].map(a => a.getAttribute('href'))")
        ok(f"{T}：公告頁：新訂單帶 #admin/pay/bankord/<訂單號>、新申請帶 #admin/pay/reqs", f"#admin/pay/bankord/{oid}" in hrefs and "#admin/pay/reqs" in hrefs, hrefs)
        ad.click(f"#v-notices a.ntgo[href='#admin/pay/bankord/{oid}']")
        ok(f"{T}：公告頁點「前往付款與訂單處理」→ 一樣跳到那一列", bool(wait_until(ad, f"() => !!document.querySelector('#payTabs [data-ptab=bankord].on') && !!document.querySelector('tr.prow.hit[data-oid=\"{oid}\"]')", 12000)))

        # ④ 一般公告：點了只展開、不換頁
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ntBell')", 10000)
        ad.evaluate("() => TwNotices.refresh()"); wait_until(ad, "() => TwNotices.list().some(n => /^新(訂單|申請)：/.test(n.title))", 8000)   # 鈴鐺有 10 分鐘本機快取
        ad.click("#ntBell")
        gid = wait_until(ad, "() => { const b = [...document.querySelectorAll('#ntDrop .ntitem')].find(x => /一般公告測試/.test(x.innerText)); return b ? b.dataset.id : ''; }", 8000)
        if gid:
            ad.click(f"#ntDrop .ntitem[data-id='{gid}']")
            ad.wait_for_timeout(400)
        ok(f"{T}：一般公告點了只展開、還在 #overview、沒有「前往」字樣", bool(gid) and ad.evaluate("() => location.hash") == "#overview"
           and ad.evaluate(f"() => {{ const b = document.querySelector('#ntDrop .ntitem[data-id=\"{gid}\"]'); return !!b && b.classList.contains('ex') && !b.querySelector('.ntgo'); }}"), gid)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


# ★ 2026-10-16 Andy：「管理者有訂單，點擊後會跳到對應分頁」（⚠ --workers 1）
register("訂單通知跳轉1016", lambda pg, b, base, code: t_pay_notice_jump_1016(b, base, code), after="付款管理區1016")
