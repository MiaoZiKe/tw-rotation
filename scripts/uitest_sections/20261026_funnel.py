# 驗收段落「漏斗事件1026」（行銷方案 W1／W2／W3，docs/marketing/growth_command_1026.md B-2、docs/account_analytics.md「漏斗」）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# 本機起真的 worker.js（devserver），逐一真的操作：
#   ① 訪客帶 ?u=th-id-20261027 進站 → 瀏覽器存「第一次來源」threads；再帶別的 utm 進來不覆蓋（first-touch）
#   ② 開 #pricing、點付費方案的訂閱鈕 → 送出 pricing_view、checkout_click（分來源）；進站 land 30 分鐘內只算一次
#   ③ 這個訪客用 Google 登入（新會員）→ 帳號收到來源、Worker 算 1 次註冊（threads）；沒來源的新會員算 direct
#   ④ 開「請勿追蹤」的訪客帶來源進站、登入 → 瀏覽器不存來源、不呼叫 /v1/me/src、任何漏斗計數都沒有 +1
#   ⑤ 管理區「流量觀測」出現「各來源的漏斗」卡：全站合計列＋Threads 列的進站／註冊真的是上面算出的數字；手機 390 沒有橫向捲軸
#   ⑥ 隱私權政策有「行銷來源與使用統計」一段
# 截圖：TW_FUNNEL_SHOTS＝資料夾。
FUNNEL_PEOPLE = {"fiona": "fiona@example.com", "gary": "gary@example.com"}


def t_funnel_1026(b, base, code):
    import urllib.request
    T = "漏斗事件1026"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in FUNNEL_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_FUNNEL_SHOTS")
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

        def new_ctx(w=1440, dnt=False):
            c = b.new_context(viewport={"width": w, "height": 900})
            init = "window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}"
            if dnt:
                init += "Object.defineProperty(navigator,'doNotTrack',{get:()=>'1'});"
            c.add_init_script(init)
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

        def consent(pg):
            a = pg.get_by_role("button", name="同意並繼續")
            if a.count() and a.first.is_visible():
                a.first.click(); pg.wait_for_timeout(300)

        # 前置：管理者登入（新會員、沒來源 → 算 1 次 direct 註冊）＋定價（訂閱鈕才有付費方案可點）
        ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded"); consent(ad)
        login(ad, "andy")
        atok = ad.evaluate("() => TwAccount.tok()")
        dev_post("/v1/admin/plans/put", {"t": atok, "id": "plus", "name": "Plus", "feats": {}, "price": 299, "period": "month", "price_year": 2990})
        dev_post("/v1/admin/plans/put", {"t": atok, "id": "pro", "name": "Pro", "feats": {}, "price": 549, "period": "month", "price_year": 5490})

        def stats():
            j = dev_post("/v1/admin/stats", {"t": atok, "days": 7})
            ev = {}
            for r in j.get("rows", []):
                ev[r["k"]] = ev.get(r["k"], 0) + r["n"]
            e2 = {}
            for r in j.get("e2", []):
                if r["page"] == "other" and r["comp"].startswith("fn."):
                    e2[(r["comp"][3:], r["detail"])] = e2.get((r["comp"][3:], r["detail"]), 0) + r["n"]
            return ev, e2

        # ① 訪客帶短參數進站
        cv = new_ctx(); pv_ = cv.new_page(); pv_.on("pageerror", lambda e: errs.append("visitor: " + str(e)))
        pv_.goto(base + sep + "u=th-id-20261027#overview", wait_until="domcontentloaded"); consent(pv_)
        wait_until(pv_, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        src = pv_.evaluate("() => JSON.parse(localStorage.getItem('tw.src') || 'null')")
        ok(f"{T}：①帶 ?u=th-id-20261027 進站 → 存第一次來源 threads／intraday_20261027", bool(src) and src.get("s") == "threads" and src.get("c") == "intraday_20261027", src)
        pv_.goto(base + sep + "utm_source=ig_bio&utm_medium=profile#pricing", wait_until="domcontentloaded"); consent(pv_)
        wait_until(pv_, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        src2 = pv_.evaluate("() => JSON.parse(localStorage.getItem('tw.src') || 'null')")
        ok(f"{T}：①再帶別的 utm 進站 → 第一次來源不被覆蓋（first-touch）", bool(src2) and src2.get("s") == "threads", src2)

        # ② 看價格、點訂閱鈕
        wait_until(pv_, "() => !!document.querySelector('#v-pricing .prgo')", 8000)
        lay = pv_.locator("#prLayout button[data-lay='cards']")
        if lay.count():
            lay.first.click(); pv_.wait_for_timeout(300)
        btn = pv_.locator("#prCards .prcard[data-plan='plus'] .prgo")
        clicked = False
        if btn.count():
            btn.first.click(); clicked = True
        else:
            pv_.locator("#v-pricing .prgo").nth(1).click(); clicked = True
        pv_.wait_for_timeout(400)
        pend = pv_.evaluate("() => TwAccount.pending()")
        # 排隊中的計數會被心跳隨時收進送出佇列，pending() 讀到空是正常的；真正的證據是下面「伺服器收到」
        ok(f"{T}：②真的點了付費方案的訂閱鈕", clicked, pend)
        pv_.evaluate("() => TwAccount.flush()"); pv_.wait_for_timeout(800)
        ev, e2 = stats()
        ok(f"{T}：②伺服器收到：進站 threads 1 次（30 分鐘內第二次進站不重算）、看價格／點訂閱都歸 threads",
           e2.get(("land", "threads")) == 1 and e2.get(("land", "ig_bio")) is None and e2.get(("pricing_view", "threads"), 0) >= 1 and e2.get(("checkout_click", "threads"), 0) >= 1, e2)
        # 關掉可能打開的登入／結帳視窗
        pv_.keyboard.press("Escape"); pv_.wait_for_timeout(200)

        # ③ 這位訪客登入成為新會員
        login(pv_, "fiona")
        wait_until(pv_, "() => localStorage.getItem('tw.src.sent')", 6000)
        pv_.wait_for_timeout(500)
        ev, e2 = stats()
        ok(f"{T}：③新會員 fiona 登入 → 註冊 1 次歸 threads；管理者的註冊歸 direct", e2.get(("signup", "threads")) == 1 and e2.get(("signup", "direct")) == 1 and ev.get("ev:signup") == 2, (ev.get("ev:signup"), e2))
        n_before = ev.get("ev:signup")
        pv_.reload(wait_until="domcontentloaded"); pv_.wait_for_timeout(1500)
        ev, e2 = stats()
        ok(f"{T}：③重新整理／再登入不重複算註冊", ev.get("ev:signup") == n_before, ev.get("ev:signup"))

        # ④ 請勿追蹤
        cd = new_ctx(dnt=True); pd = cd.new_page(); pd.on("pageerror", lambda e: errs.append("dnt: " + str(e)))
        reqs: list[str] = []
        pd.on("request", lambda r: reqs.append(r.url) if r.method == "POST" else None)
        pd.goto(base + sep + "u=ig-pm-20261027#pricing", wait_until="domcontentloaded"); consent(pd)
        wait_until(pd, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        pd.wait_for_timeout(500)
        btn = pd.locator("#v-pricing .prgo")
        if btn.count() > 1:
            btn.nth(1).click(); pd.wait_for_timeout(300)
        pd.keyboard.press("Escape")
        login(pd, "gary"); pd.wait_for_timeout(800)
        pd.evaluate("() => TwAccount.flush()"); pd.wait_for_timeout(500)
        ev2, e22 = stats()
        ok(f"{T}：④請勿追蹤：瀏覽器沒存來源、沒呼叫 /v1/me/src、沒送統計",
           pd.evaluate("() => localStorage.getItem('tw.src')") is None and not any("/v1/me/src" in u or "/v1/track/batch" in u or "/v1/beat" in u for u in reqs), [u for u in reqs][:6])
        ok(f"{T}：④請勿追蹤：註冊、進站、點訂閱計數都沒有增加", ev2.get("ev:signup") == n_before and e22.get(("land", "instagram")) is None and e22.get(("land", "ig")) is None and e22 == e2, e22)

        # ⑤ 管理區漏斗卡
        ad.goto(base + "#admin/traffic", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.querySelector('#trFunnel')", 12000)
        # 期間預設若是「即時」，今天的資料一樣包含在內；切到近 7 天保險
        try:
            ad.select_option("#admDaysSel", "7"); ad.wait_for_timeout(1200)
        except Exception:  # noqa: BLE001
            pass
        wait_until(ad, "() => !!document.querySelector('#trFunnel .funt')", 8000)
        tbl = ad.evaluate("() => [...document.querySelectorAll('#trFunnel .funt tbody tr')].map(tr => [...tr.children].map(c => c.textContent.trim()))")
        tot = next((r for r in tbl if r[0] == "全站合計"), None)
        thr = next((r for r in tbl if r[0] == "Threads"), None)
        ok(f"{T}：⑤管理區「各來源的漏斗」：全站合計列、Threads 列都在", bool(tot) and bool(thr), tbl)
        ok(f"{T}：⑤Threads 列：進站 1、註冊 1、看價格 ≥1、點結帳 ≥1；註冊率 100.0%", bool(thr) and thr[1] == "1" and thr[2] == "1" and int(thr[4]) >= 1 and int(thr[5]) >= 1 and thr[7] == "100.0%", thr)
        dirr = next((r for r in tbl if r[0].startswith("直接進站")), None)
        ok(f"{T}：⑤直接進站列：進站 ≥ 1 且 ≥ 註冊", bool(dirr) and int(dirr[1]) >= 1 and int(dirr[1]) >= int(dirr[2]), dirr)
        def _rt(r):
            return r[-1] == "—" or float(r[-1].rstrip("%")) <= 100.0
        ok(f"{T}：⑤任何列註冊率都不超過 100%", all(_rt(r) for r in tbl), tbl)
        ok(f"{T}：⑤全站合計註冊＝2（threads 1＋direct 1）", bool(tot) and tot[2] == "2", tot)
        ok(f"{T}：⑤「?」說明收在標題旁、卡內沒有攤開的說明段落", ad.evaluate("() => { const c = document.querySelector('#trFunnel'); return !!c.querySelector('h3 .qtip') && !c.querySelector('p, details'); }"))
        if shots:
            ad.locator("#trFunnel").screenshot(path=str(pathlib.Path(shots) / "funnel_1440.png"))
        cm = new_ctx(390); am = cm.new_page(); am.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
        am.goto(base + "#overview", wait_until="domcontentloaded"); consent(am)
        login(am, "andy")
        am.goto(base + "#admin/traffic", wait_until="domcontentloaded")
        wait_until(am, "() => !!document.querySelector('#trFunnel .funt')", 12000)
        am.locator("#trFunnel").scroll_into_view_if_needed()
        sw = am.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        small = am.evaluate("() => [...document.querySelectorAll('#trFunnel td, #trFunnel th')].filter(e => e.getClientRects().length && parseFloat(getComputedStyle(e).fontSize) < 11).length")
        ok(f"{T}：⑤手機 390：漏斗卡沒有橫向捲軸、字不小於 11px", sw <= 0 and small == 0, (sw, small))
        if shots:
            am.locator("#trFunnel").screenshot(path=str(pathlib.Path(shots) / "funnel_390.png"))

        # ⑥ 隱私權政策
        pp = new_ctx().new_page(); pp.goto(base + "#privacy", wait_until="domcontentloaded"); consent(pp)
        wait_until(pp, "() => document.body.innerText.includes('行銷來源與使用統計')", 6000)
        txt = pp.inner_text("body")
        ok(f"{T}：⑥隱私權政策有「行銷來源與使用統計」，寫明第一次來源、帳號欄位、DNT／GPC", "行銷來源與使用統計" in txt and "第一次來源" in txt and "請勿追蹤" in txt)
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()
    ok(f"{T}：整段沒有頁面錯誤", not errs, errs[:3])


# ★ 2026-10-26 行銷方案 W2：漏斗事件（⚠ --workers 1）
register("漏斗事件1026", lambda pg, b, base, code: t_funnel_1026(b, base, code))
