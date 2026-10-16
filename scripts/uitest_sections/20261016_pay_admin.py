# 驗收段落「付款管理區1016」（docs/payment_admin_tabs_1016.md）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 付款管理區1016（Andy 10-16）
# 「這邊應該是 會多出現已退款功能按鈕 並且跳到退款紀錄那邊紀錄」
# 「這邊好亂…不應該發生 他待審核，另一個退款分頁還有這個人，一個mail 身份只能存在一個，若他有最新的一筆資訊，就只會留下最新的一筆」
# 「並且需要制定完善的措施」
# 本機起真的 worker.js（devserver），管理者在 1440 真的點：
#   ① 七個分頁；退款申請那列有「已退款」、取消訂閱那列沒有
#   ② 按「已退款」→ 跳到「退款紀錄」、email 與對應訂單已預填、退款登記框直接打開（寫著來自申請）→ 填末 5 碼登記 →
#      申請變「已處理（已退款 NT$…）」、退款紀錄那筆標「來自申請」、頁首待處理數字消失
#   ③ 同一 email：gary 先申請退款、再申請取消、之後又送出新訂單 → 申請分頁 gary 只有一列（最新、已結案「已被新訂單取代」）＋「＋1 筆歷史」；
#      待確認的轉帳只有 gary 最新那筆；訂單清單 gary 一列＋歷史展開看得到舊單；有待審核時會員送取消申請被擋（409）
#   ④ 兩個管理者同時處理：畫面上還是「待確認」，另一位先確認了 → 這邊按「退回」→ 伺服器 409、畫面重新整理、寫是誰處理的、狀態變已開通
#   ⑤ 「操作紀錄」分頁：確認入帳／退款／申請結案（規則自動）都有，含操作者與前後狀態；搜尋 email 篩得出來
#   ⑥ 版面：分頁內按鈕兩兩不重疊、沒有整頁橫向捲軸（1440 與 800）
# 截圖：TW_PAY_SHOTS＝資料夾（與「結帳與付款1011」同一個）。
PAYADM_PEOPLE = {"fiona": "fiona@example.com", "gary": "gary@example.com"}


def t_pay_admin_1016(b, base, code):
    import urllib.request
    T = "付款管理區1016"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in PAYADM_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_PAY_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)

    def shot(pg, name, sel=None):
        if not shots:
            return
        try:
            if sel and pg.locator(sel).count():
                pg.locator(sel).first.screenshot(path=str(pathlib.Path(shots) / name))
            else:
                pg.screenshot(path=str(pathlib.Path(shots) / name))
        except Exception as e:  # noqa: BLE001
            print(f"  （{T} 截圖 {name} 沒存成：{str(e)[:80]}）")

    def dev_post(path, body):
        req = urllib.request.Request(api + path, data=json.dumps(body).encode(), headers={"Origin": origin, "content-type": "text/plain"}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=8).read())
        except urllib.error.HTTPError as e:
            return {"_s": e.code, **json.loads(e.read() or b"{}")}

    # 按鈕兩兩不重疊＋沒有整頁橫向捲軸
    OVL = """() => { const bs = [...document.querySelectorAll('#payAdm button, #payAdm .stp, #subDlg:not([hidden]) button')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height; });
        const bad = []; for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) { const a = bs[i].getBoundingClientRect(), c = bs[j].getBoundingClientRect();
          if (bs[i].contains(bs[j]) || bs[j].contains(bs[i])) continue;
          if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > 1 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 1) bad.push(bs[i].innerText + ' × ' + bs[j].innerText); }
        return { bad: bad.slice(0, 5), sw: document.documentElement.scrollWidth - innerWidth }; }"""

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

        def tpe_today():
            return time.strftime("%Y-%m-%d", time.gmtime(time.time() + 8 * 3600))

        def paid(pg, plan, period, last5, confirm=True):
            c = call(pg, "/v1/pay/bank/create", {"plan": plan, "period": period})
            r = call(pg, "/v1/pay/bank/report", {"id": c.get("id"), "name": "測試", "last5": last5, "date": tpe_today()})
            if confirm:
                dev_post("/v1/admin/pay/confirm", {"t": atok, "id": c.get("id"), "received": c.get("amount")})
            time.sleep(0.03)
            return c, r

        # 前置：管理者定價＋收款帳號
        ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        login(ad, "andy")
        r1 = call(ad, "/v1/admin/plans/put", {"id": "plus", "name": "Plus", "feats": {}, "price": 299, "period": "month", "price_year": 2990})
        r1b = call(ad, "/v1/admin/plans/put", {"id": "pro", "name": "Pro", "feats": {}, "price": 499, "period": "month", "price_year": 5268})
        r2 = call(ad, "/v1/admin/pay/bank/put", {"bank_name": "測試銀行", "bank_code": "999", "account": "000011112222", "holder": "測試戶名"})
        atok = ad.evaluate("() => TwAccount.tok()")
        ok(f"{T}：前置：Plus／Pro 定價、收款帳號", all(x.get("_s") == 200 for x in (r1, r1b, r2)), (r1, r1b, r2))

        # 會員：fiona 付款開通後申請退款；gary 付款開通 → 申請退款 → 申請取消 → 又下新訂單（Pro 年繳）送出匯款資料
        cf = new_ctx(); pf = cf.new_page(); pf.on("pageerror", lambda e: errs.append("fiona: " + str(e)))
        pf.goto(base + "#pricing", wait_until="domcontentloaded"); login(pf, "fiona")
        fo, _ = paid(pf, "plus", "month", "11111")
        rqf = call(pf, "/v1/subscribe/change", {"type": "refund", "note": "fiona 不需要了"})
        cg = new_ctx(); pgy = cg.new_page(); pgy.on("pageerror", lambda e: errs.append("gary: " + str(e)))
        pgy.goto(base + "#pricing", wait_until="domcontentloaded"); login(pgy, "gary")
        go1, _ = paid(pgy, "plus", "month", "22222")
        rg1 = call(pgy, "/v1/subscribe/change", {"type": "refund", "note": "gary 第一次申請"}); time.sleep(0.03)
        rg2 = call(pgy, "/v1/subscribe/change", {"type": "cancel", "note": "gary 改成取消"}); time.sleep(0.03)
        go2, rep2 = paid(pgy, "pro", "year", "33333", confirm=False)
        ok(f"{T}：前置：fiona 申請退款；gary 退款→取消→新訂單送出（待確認）", rqf.get("_s") == 200 and rg1.get("_s") == 200 and rg2.get("_s") == 200 and rep2.get("_s") == 200, (rqf, rg1, rg2, rep2))
        blk = call(pgy, "/v1/subscribe/change", {"type": "cancel"})
        ok(f"{T}：有待審核的訂單時，會員再送取消申請 → 伺服器擋下（409、寫審核中）", blk.get("_s") == 409 and blk.get("error") == "pending_review" and "審核中" in (blk.get("msg") or ""), blk)

        # ① 七個分頁＋申請分頁
        ad.goto(base + "#admin/pay", wait_until="domcontentloaded")
        ok(f"{T}：七個分頁（多了「操作紀錄」）", bool(wait_until(ad, "() => document.querySelectorAll('#payTabs [data-ptab]').length === 7 && /操作紀錄/.test(document.getElementById('payTabs').innerText)", 10000)))
        ad.click("[data-ptab=reqs]")
        wait_until(ad, "() => !!document.getElementById('payReqs')", 4000)
        rq = ad.evaluate("""() => [...document.querySelectorAll('#payReqs tbody tr')].map(tr => ({ id: tr.dataset.rq, old: tr.classList.contains('old'), t: tr.innerText, rr: !!tr.querySelector('[data-rqr]'), hist: (tr.querySelector('[data-hist]') || {}).innerText || '' }))""")
        emails = [r["t"] for r in rq if not r["old"]]
        g_rows = [r for r in rq if "gary@" in r["t"] and not r["old"]]
        ok(f"{T}：同一 email 只顯示最新一筆：gary 只有一列（最新的取消申請、已結案「已被新訂單取代」）＋「＋1 筆歷史」",
           len(g_rows) == 1 and "取消訂閱" in g_rows[0]["t"] and "已結案" in g_rows[0]["t"] and "已被新訂單" in g_rows[0]["t"] and "＋1 筆歷史" in g_rows[0]["hist"] and not g_rows[0]["rr"], rq)
        f_rows = [r for r in rq if "fiona@" in r["t"]]
        ok(f"{T}：fiona 的退款申請：待處理、有「已退款」鈕、對應訂單已帶出", len(f_rows) == 1 and f_rows[0]["rr"] and "待處理" in f_rows[0]["t"] and fo.get("id") in f_rows[0]["t"], f_rows)
        ok(f"{T}：頁首「待處理申請」以 email 算：只算 fiona 1 件", (ad.evaluate("() => (document.getElementById('payReqCnt') || {}).innerText || ''") or "").strip().endswith("1"))
        ad.click(f"#payReqs tr[data-rq='{g_rows[0]['id']}'] [data-hist]")
        hist = ad.evaluate("() => [...document.querySelectorAll('#payReqs tbody tr.old')].map(tr => tr.innerText)")
        ok(f"{T}：按「＋1 筆歷史」→ 看得到 gary 較舊的退款申請（已結案「已被較新的取消訂閱申請取代」）", len(hist) == 1 and "申請退款" in hist[0] and "取消訂閱申請取代" in hist[0], hist)
        m = ad.evaluate(OVL)
        ok(f"{T}：申請分頁按鈕兩兩不重疊、沒有橫向捲軸", not m["bad"] and m["sw"] <= 1, m)
        shot(ad, "admin_reqs_1016.png", "#payAdm")

        # ② 已退款 → 跳到退款紀錄並預填、直接打開登記框 → 登記 → 申請變已處理
        ad.click(f"#payReqs [data-rqr='{rqf.get('id')}']")
        pre = wait_until(ad, """() => { const d = document.getElementById('payRefundDlg'); const t = document.querySelector('[data-ptab=refunds]');
            return d && !document.getElementById('subDlg').hidden && t.classList.contains('on') ? { em: document.getElementById('rfEm').value, oid: document.getElementById('rfOid').value,
              note: (document.getElementById('rfReqNote') || {}).innerText || '', from: (document.getElementById('payRfFrom') || {}).innerText || '' } : null; }""", 8000)
        ok(f"{T}：按「已退款」→ 跳到「退款紀錄」分頁、email 與對應訂單已預填、退款登記框直接打開並寫「來自退款申請、完成後自動標已處理」",
           bool(pre) and pre["em"] == "fiona@example.com" and pre["oid"] == fo.get("id") and "自動標成已處理" in pre["note"] and "fiona 不需要了" in pre["from"], pre)
        m = ad.evaluate(OVL)
        ok(f"{T}：退款登記框按鈕不重疊", not m["bad"], m)
        shot(ad, "admin_refund_from_req.png", "#subDlg .box")
        ad.fill("#rfL5", "44444")
        with ad.expect_response(lambda r: r.url.endswith("/v1/admin/pay/refund"), timeout=8000) as ri:
            ad.click("#rfGo")
        rb = json.loads(ri.value.request.post_data or "{}")
        ok(f"{T}：送出的退款帶著申請編號（req）與我看到的狀態（expect）", rb.get("req") == rqf.get("id") and rb.get("expect") == "active" and ri.value.status == 200, {k: v for k, v in rb.items() if k != "t"})
        rt = wait_until(ad, "() => { const t = document.getElementById('payRefunds'); return t && /來自申請/.test(t.innerText) ? t.innerText : ''; }", 8000)
        ok(f"{T}：退款紀錄出現 fiona 這筆、標「來自申請」", bool(rt) and "fiona@example.com" in rt, rt[:300] if rt else rt)
        ok(f"{T}：頁首「待處理申請」數字消失", bool(wait_until(ad, "() => !document.getElementById('payReqCnt')", 4000)))
        shot(ad, "admin_refunds_1016.png", "#payAdm")
        ad.click("[data-ptab=reqs]")
        fr = wait_until(ad, f"() => {{ const tr = document.querySelector('#payReqs tr[data-rq=\"{rqf.get('id')}\"]'); return tr ? tr.querySelector('.stp').innerText + '|' + tr.innerText : ''; }}", 4000)
        ok(f"{T}：回到申請分頁：fiona 那筆變「已處理」、原因寫「已退款 NT$ 299」、操作者 andy", bool(fr) and fr.startswith("已處理|") and "已退款 NT$ 299" in fr and "andy@example.com" in fr, fr)

        # ③ 待確認的轉帳／訂單清單：gary 只有一筆待確認、訂單清單一列＋歷史
        ad.click("[data-ptab=bankord]")
        wait_until(ad, "() => !!document.getElementById('payRevSec')", 4000)
        rv = ad.evaluate("() => [...document.querySelectorAll('#payRevSec tr.prow')].map(r => r.dataset.oid)")
        ok(f"{T}：待確認的轉帳：只有 gary 最新那筆（Pro 年繳）", rv == [go2.get("id")], (rv, go2.get("id")))
        gl = ad.evaluate("() => [...document.querySelectorAll('#payTbl tbody tr.prow:not(.old)')].filter(r => /gary@/.test(r.innerText)).map(r => ({ id: r.dataset.oid, h: (r.querySelector('[data-hist]') || {}).innerText || '' }))")
        ok(f"{T}：訂單清單 gary 只有一列（最新那筆）＋「＋1 筆歷史」", len(gl) == 1 and gl[0]["id"] == go2.get("id") and "＋1 筆歷史" in gl[0]["h"], gl)
        ad.click(f"#payTbl tr.prow[data-oid='{go2.get('id')}'] [data-hist]")
        ok(f"{T}：展開歷史 → 看得到 gary 舊的那筆（已開通）", bool(wait_until(ad, f"() => {{ const r = document.querySelector('#payTbl tr.prow.old[data-oid=\"{go1.get('id')}\"]'); return r && /已開通/.test(r.innerText); }}", 3000)))
        m = ad.evaluate(OVL)
        ok(f"{T}：銀行轉帳訂單分頁按鈕不重疊、沒有橫向捲軸", not m["bad"] and m["sw"] <= 1, m)
        shot(ad, "admin_bankord_1016.png", "#payAdm")
        ad.click("[data-ptab=subs]")
        wait_until(ad, "() => !!document.getElementById('paySubs')", 4000)
        se = ad.evaluate("() => [...document.querySelectorAll('#paySubs tr.prow')].map(r => r.dataset.em)")
        ok(f"{T}：會員訂閱：一個 email 一列", len(se) == len(set(se)) and {"fiona@example.com", "gary@example.com"} <= set(se), se)

        # ④ 兩個管理者同時處理：畫面上還是待確認，另一位先確認 → 這邊按退回 → 409、重新整理、寫誰處理的
        ad.click("[data-ptab=bankord]")
        wait_until(ad, "() => !!document.querySelector('#payRevSec [data-pa=reject]')", 4000)
        other = dev_post("/v1/admin/pay/confirm", {"t": atok, "id": go2.get("id"), "received": 5268, "expect": "review"})
        ad.click(f"#payRevSec [data-pa=reject][data-id='{go2.get('id')}']")
        wait_until(ad, "() => !!document.getElementById('pdWhy')", 3000)
        ad.fill("#pdWhy", "晚一步的退回")
        ad.click("#pdGo")
        cm = wait_until(ad, "() => { const e = document.getElementById('paySt'); return e && /bad/.test(e.className) && /andy@example.com/.test(e.innerText) ? e.innerText : ''; }", 6000)
        ok(f"{T}：另一位管理者先確認了 → 這邊按退回被擋、畫面寫是誰處理的", other.get("ok") is True and bool(cm) and "開通" in cm, (other.get("ok"), cm))
        ok(f"{T}：畫面已重新整理：待確認清單沒有這筆、訂單變已開通（沒有被退回）",
           bool(wait_until(ad, f"() => !document.querySelector('#payRevSec tr.prow') && /已開通/.test((document.querySelector('#payTbl tr.prow[data-oid=\"{go2.get('id')}\"]') || {{}}).innerText || '')", 4000)))

        # ⑤ 操作紀錄
        ad.click("[data-ptab=audit]")
        at = wait_until(ad, "() => { const t = document.getElementById('payAudit'); return t ? t.innerText : ''; }", 4000)
        ok(f"{T}：操作紀錄有確認入帳、退款、申請結案（規則自動）、申請已退款，含操作者與前後狀態",
           bool(at) and all(k in at for k in ("確認入帳", "退款", "申請結案", "申請已退款", "規則自動", "andy@example.com", "待確認 → 已開通", "待處理 → 已處理")), at[:600] if at else at)
        ad.fill("#paQ", "fiona")
        ok(f"{T}：操作紀錄搜尋 fiona → 只剩 fiona 的", bool(wait_until(ad, "() => { const rs = [...document.querySelectorAll('#payAudit tbody tr')]; return rs.length && rs.every(r => /fiona@/.test(r.innerText)); }", 3000)))
        m = ad.evaluate(OVL)
        ok(f"{T}：操作紀錄分頁不重疊、沒有橫向捲軸", not m["bad"] and m["sw"] <= 1, m)
        shot(ad, "admin_audit_1016.png", "#payAdm")

        # ⑥ 800 寬：每個分頁按鈕不重疊、沒有整頁橫向捲軸
        ad.set_viewport_size({"width": 800, "height": 900})
        res800 = {}
        for tab in ("bankord", "orders", "reqs", "subs", "refunds", "bank", "audit"):
            ad.click(f"[data-ptab={tab}]")
            ad.wait_for_timeout(150)
            res800[tab] = ad.evaluate(OVL)
        ok(f"{T}：800 寬七個分頁都沒有按鈕重疊、沒有整頁橫向捲軸", all(not x["bad"] and x["sw"] <= 1 for x in res800.values()), res800)
        ad.click("[data-ptab=reqs]")
        shot(ad, "admin_reqs_800.png", "#payAdm")
        ad.set_viewport_size({"width": 1440, "height": 900})
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


# ★ 2026-10-16 Andy：管理區付款分頁「已退款」鈕、同一 email 只留最新、處理措施（⚠ --workers 1）
register("付款管理區1016", lambda pg, b, base, code: t_pay_admin_1016(b, base, code), after="轉帳改版1016")
