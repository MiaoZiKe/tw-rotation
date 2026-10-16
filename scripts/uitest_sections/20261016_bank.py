# 驗收段落「轉帳改版1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 轉帳改版1016（Andy 10-16）
# 「以後透過銀行轉帳，金額直接當客戶寫死對應金額，只有我這還有可以更改」「拿掉補送匯款資料這功能」
# 「手機…備註不相關內容，以及排版不正常…空框內都不要有備註詞」「需要多一個客戶填姓名的欄位，強制要求填寫」
# 本機起真的 worker.js（devserver），360／390／430 三種寬度各一位會員用手指（tap）走完：
#   表單一欄一列不截字、輸入框沒有範例字、沒有備註欄、金額唯讀＝訂單金額、沒填姓名擋下 → 送出 → 我的訂單沒有「補送」、有意見反饋提示
# 管理區（1440）：待確認清單看得到匯款人姓名、「改金額」真的改到伺服器、會員端看到新金額。
BANK1016_PEOPLE = {"m360": "m360@example.com", "m390": "m390@example.com", "m430": "m430@example.com"}


def t_bank_1016(b, base, code):
    import urllib.request
    T = "轉帳改版1016"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in BANK1016_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.upper()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_BANK1016_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
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

        def new_ctx(w):
            kw = dict(viewport={"width": w, "height": 844 if w <= 640 else 900})
            if w <= 640:
                kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
            c = b.new_context(**kw)
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def login(pg, who):
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
            pg.evaluate("() => TwAccount.login()")
            pg.wait_for_selector("#acctGo", state="visible", timeout=6000)
            with pg.expect_popup() as pi:
                pg.locator("#acctGo").tap() if (pg.viewport_size or {}).get("width", 1440) <= 640 else pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=8000)
            pop.click("#as-" + who)
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        def call(pg, path, body):
            return pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])

        # 管理者：定價＋收款帳號
        ca = new_ctx(1440); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        login(ad, "andy")
        r1 = call(ad, "/v1/admin/plans/put", {"id": "plus", "name": "Plus", "feats": {}, "price": 299, "period": "month", "price_year": 2990})
        r2 = call(ad, "/v1/admin/pay/bank/put", {"bank_name": "測試銀行", "bank_code": "999", "account": "000011112222", "holder": "測試戶名"})
        ok(f"{T}：前置：Plus 定價、收款帳號", r1.get("_s") == 200 and r2.get("_s") == 200, (r1, r2))

        oids = {}
        # TW_BANK1016_W=390：只跑某個寬度（拿來對改版前的網站截「改前」圖；平常不設＝三個寬度都跑）
        only_w = os.environ.get("TW_BANK1016_W")
        for w, who in ((360, "m360"), (390, "m390"), (430, "m430")):
            if only_w and str(w) != only_w:
                continue
            cm = new_ctx(w); pm = cm.new_page(); pm.on("pageerror", lambda e, w=w: errs.append(f"{w}: {e}"))
            pm.goto(base + "#pricing", wait_until="domcontentloaded")
            if not ok(f"{T}：{w} 登入", bool(login(pm, who))):
                continue
            pm.evaluate("() => TwCheckout.open({ plan: 'plus', per: 'year' })")
            wait_until(pm, "() => !!document.getElementById('coTabB')", 6000)
            pm.tap("#coTabB")
            wait_until(pm, "() => !!document.getElementById('coL5')", 8000)
            if shots:
                pm.locator("#coSendB").scroll_into_view_if_needed()
                pm.screenshot(path=str(pathlib.Path(shots) / f"bank_form_{w}.png"))
            g = pm.evaluate("""() => { const f = document.querySelector('#subDlg .cofrm'); const ins = [...f.querySelectorAll('input')];
                const cells = [...f.children].map(c => c.getBoundingClientRect()); const fr = f.getBoundingClientRect();
                const labs = [...f.querySelectorAll('label, .lb')];
                return { ph: ins.filter(i => (i.getAttribute('placeholder') || '').trim()).map(i => i.id), note: !!document.getElementById('coNote'),
                         ids: ins.map(i => i.id), oneCol: cells.every(r => Math.abs(r.left - fr.left) < 2 && Math.abs(r.width - fr.width) < 2),
                         rows: new Set(cells.map(r => Math.round(r.top))).size, n: cells.length,
                         clip: labs.filter(l => l.scrollWidth > l.clientWidth + 1).map(l => l.textContent),
                         inView: ins.every(i => { const r = i.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }),
                         amt: (document.getElementById('coXAmt') || {}).tagName, amtTxt: (document.getElementById('coXAmt') || {}).innerText || '',
                         sw: document.documentElement.scrollWidth - innerWidth, txt: f.innerText }; }""")
            ok(f"{T}：{w} 表單一欄一列（每格同寬、各自一列、不截字、都在螢幕內、沒有橫向捲軸）",
               g["oneCol"] and g["rows"] == g["n"] and not g["clip"] and g["inView"] and g["sw"] <= 1, g)
            ok(f"{T}：{w} 輸入框沒有任何範例字（placeholder）、沒有「備註」欄、沒有「實際轉帳金額」輸入框", not g["ph"] and not g["note"] and "coXAmt" not in g["ids"] and "備註" not in g["txt"], g)
            ok(f"{T}：{w} 轉帳金額唯讀＝訂單金額 NT$ 2,990", g["amt"] != "INPUT" and "2,990" in g["amtTxt"], g)
            ok(f"{T}：{w} 有「匯款人姓名」欄、標「必填」", "匯款人姓名" in g["txt"] and "必填" in g["txt"] and "coPayer" in g["ids"], g)
            oids[who] = pm.evaluate("() => document.getElementById('coOid').innerText")
            pm.locator("#coL5").tap(); pm.fill("#coL5", "1" + w.__str__() + "1")
            pm.tap("#coAgree") if pm.locator("#coAgree").count() else None
            pm.locator("#coSendB").scroll_into_view_if_needed(); pm.tap("#coSendB")
            ok(f"{T}：{w} 沒填姓名按送出 → 擋下、不出確認區", bool(wait_until(pm, "() => /請填匯款人姓名/.test(document.getElementById('coMsg').innerText) && !document.getElementById('coCfm')", 3000)))
            pm.locator("#coPayer").tap(); pm.fill("#coPayer", f"王{w}")
            pm.locator("#coSendB").scroll_into_view_if_needed(); pm.tap("#coSendB")
            cf = wait_until(pm, "() => { const c = document.getElementById('coCfm'); return c ? c.innerText : ''; }", 3000)
            ok(f"{T}：{w} 確認區顯示姓名、末 5 碼、金額 NT$ 2,990", bool(cf) and f"王{w}" in cf and "2,990" in cf, cf)
            pm.locator("#coCfmGo").scroll_into_view_if_needed()
            with pm.expect_request(lambda r: "/v1/pay/bank/report" in r.url, timeout=6000) as rq:
                pm.tap("#coCfmGo")
            body = json.loads(rq.value.post_data or "{}")
            ok(f"{T}：{w} 送出的資料只有姓名／末 5 碼／日期（不帶金額、不帶備註）", body.get("name") == f"王{w}" and "amount" not in body and "note" not in body, {k: v for k, v in body.items() if k != "t"})
            ok(f"{T}：{w} 送出成功（待確認）", bool(wait_until(pm, "() => { const d = document.getElementById('subDlg'); return d && /待確認/.test(d.innerText); }", 6000)))
            pm.tap("#coSeeOrders")
            row = wait_until(pm, f"() => {{ const r = document.querySelector('#ordList .ordr[data-oid=\"{oids[who]}\"]'); return r ? r.innerText : ''; }}", 8000)
            ok(f"{T}：{w} 我的訂單：這筆待確認、沒有「補送新的匯款資料」鈕、有意見反饋提示、看得到匯款人",
               bool(row) and "待確認" in row and "補送" not in row and pm.locator("[data-rep]").count() == 0 and "意見反饋" in row and f"王{w}" in row, row)
            ok(f"{T}：{w} 我的訂單沒有橫向捲軸", pm.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
            if shots:
                pm.screenshot(path=str(pathlib.Path(shots) / f"orders_{w}.png"))
            again = call(pm, "/v1/pay/bank/report", {"id": oids[who], "name": "x", "last5": "99999", "date": time.strftime("%Y-%m-%d", time.gmtime(time.time() + 8 * 3600))})
            ok(f"{T}：{w} 伺服器也不收第二次（補送已拿掉）", again.get("_s") == 409 and again.get("error") == "already_reported", again)

        # 管理區：姓名欄＋改金額
        ad.goto(base + "#admin/pay", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.querySelector('#payTabs [data-ptab=bankord]')", 10000)
        ad.click("[data-ptab=bankord]")
        ad.click("#payReload")
        rev = wait_until(ad, "() => { const s = document.getElementById('payRevSec'); return s && s.querySelectorAll('tr[data-oid]').length >= 3 ? s.innerText : ''; }", 8000)
        heads = ad.evaluate("() => [...document.querySelectorAll('#payRevSec thead th')].map(t => t.textContent)")
        ok(f"{T}：管理區待確認清單有「匯款人姓名」欄、看得到三位的姓名", "匯款人姓名" in heads and all(f"王{w}" in (rev or "") for w in (360, 390, 430)), (heads, rev))
        oid = oids.get("m390")
        if shots:
            ad.locator("#payRevSec").screenshot(path=str(pathlib.Path(shots) / "admin_rev_names.png"))
        ad.click(f"#payRevSec [data-pa=amt][data-id='{oid}']")
        wait_until(ad, "() => !!document.getElementById('pdAmt')", 4000)
        ad.fill("#pdAmt", "2500"); ad.fill("#pdAmtWhy", "驗收：早鳥價")
        with ad.expect_response(lambda r: "/v1/admin/pay/amount" in r.url, timeout=6000) as ri:
            ad.click("#pdGo")
        ok(f"{T}：管理區「改金額」→ 真的存進伺服器、清單應付變 2,500", ri.value.status == 200 and bool(wait_until(ad, f"() => {{ const r = document.querySelector('#payRevSec tr[data-oid=\"{oid}\"]'); return r && /2,500/.test(r.innerText); }}", 6000)))
        cm = new_ctx(390); pm = cm.new_page(); pm.goto(base + "#overview", wait_until="domcontentloaded")
        login(pm, "m390")
        mine = [o for o in (call(pm, "/v1/pay/my", {}).get("orders") or []) if o["id"] == oid]
        ok(f"{T}：會員端看到新金額 2500（只有管理者能改）", bool(mine) and mine[0]["amount"] == 2500 and mine[0]["xferAmount"] == 2500, mine)
        hack = call(pm, "/v1/admin/pay/amount", {"id": oid, "amount": 1})
        ok(f"{T}：會員自己打改金額 → 403", hack.get("_s") == 403, hack)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:5])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


# ★ 2026-10-16 Andy：銀行轉帳改版（金額鎖定、拿掉補送、表單清理、匯款人姓名必填、管理區改金額；360／390／430 各一位；⚠ --workers 1）
register("轉帳改版1016", lambda pg, b, base, code: t_bank_1016(b, base, code), after="結帳與付款1011")
