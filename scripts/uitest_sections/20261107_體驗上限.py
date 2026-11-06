# 驗收段落「體驗上限」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 體驗上限
# Andy 11-07：「編輯：新會員體驗」勾 88／93 項按儲存，紅字「沒有存進去：至少要勾一個功能」。
# 根因是 Worker 上限 40、超過也回 bad_feats。後端放寬到 200（回 max_feats、超過回 too_many_feats）要 Andy 同意才部署，
# 所以這段同時驗「舊後端」與「新後端」（用 Playwright 攔截 grants 兩支 API 當假 Worker）：
# ① 舊後端（清單沒回 max_feats）：全部全選 → 計數列寫「超過上限 40 項」；按儲存不送出、訊息「勾太多了，最多 40 項」，不再講「至少要勾一個」
# ② 全部清除後按儲存 → 「至少要勾一個功能」、不送出
# ③ 假新後端（max_feats 200）：勾 88 項 → 存檔真的送出 88 項、200、清單寫「已儲存」，重新打開仍是 88 項
# ④ 假新後端回 too_many_feats（max 200）→ 訊息「勾太多了，最多 200 項」


def t_grantmax_1107(b, base):
    T = "體驗上限"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
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
        if not ok(f"{T}：本機 account-api 起得來", up):
            return
        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        ctxs.append(c)
        ad = c.new_page(); ad.on("pageerror", lambda e: errs.append(str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        ad.click("#acctBtn")
        with ad.expect_popup() as pi:
            ad.click("#acctGo")
        pop = pi.value
        pop.wait_for_selector("#as-andy", timeout=8000)
        pop.click("#as-andy")
        wait_until(ad, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        # 假 Worker：mode 決定行為；puts 記下每一次真的送出的存檔
        fake = {"mode": "old", "store": None}
        puts: list[dict] = []

        def on_list(route):
            r = route.fetch()
            j = r.json()
            if fake["mode"] != "old":
                j["max_feats"] = 200
                if fake["store"] is not None:
                    for d in j.get("defs", []):
                        if d["id"] == "welcome":
                            d["feats"] = fake["store"]
            route.fulfill(response=r, json=j)

        def on_put(route):
            body = json.loads(route.request.post_data or "{}")
            puts.append(body)
            if fake["mode"] == "old":
                route.continue_()
                return
            if fake["mode"] == "too_many":
                route.fulfill(status=400, json={"error": "too_many_feats", "max": 200}, headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})
                return
            fake["store"] = body.get("feats")
            lst = route.fetch(url=api + "/v1/admin/grants/defs/list", post_data=json.dumps({"t": body.get("t")}))
            j = lst.json()
            j["max_feats"] = 200
            for d in j.get("defs", []):
                if d["id"] == "welcome":
                    d.update({k: body[k] for k in ("name", "feats", "per", "days", "audience", "on") if k in body})
            route.fulfill(response=lst, json=j)

        c.route("**/v1/admin/grants/defs/list", on_list)
        c.route("**/v1/admin/grants/defs/put", on_put)

        CNT = "() => document.querySelectorAll('#agrFeats input[data-fk]:checked').length"
        TOT = "() => document.querySelectorAll('#agrFeats input[data-fk]').length"

        def open_welcome():
            ad.goto(base + "#overview", wait_until="domcontentloaded")
            ad.goto(base + "#admin/grants", wait_until="domcontentloaded")
            wait_until(ad, "() => document.querySelectorAll('#agrList button[data-edit]').length > 0", 10000)
            ad.click("#agrList button[data-edit=\"welcome\"]")
            wait_until(ad, "() => document.querySelectorAll('#agrFeats input[data-fk]').length > 10", 5000)

        # ---------- ① 舊後端：前端預檢 40
        open_welcome()
        ad.click("#agrAllOn")
        tot = ad.evaluate(TOT)
        cnt_txt = ad.inner_text("#agrFCnt")
        ok(f"{T}：①全部全選（{tot} 項）→ 計數列寫「超過上限 40 項」且是紅字", "超過上限 40 項" in cnt_txt and ad.evaluate("() => document.getElementById('agrFCnt').classList.contains('over')"), cnt_txt)
        n0 = len(puts)
        ad.click("#agrSave"); ad.wait_for_timeout(400)
        msg = ad.inner_text("#agrFSt")
        ok(f"{T}：①按儲存 → 不送出", len(puts) == n0, len(puts) - n0)
        ok(f"{T}：①訊息是「勾太多了，最多 40 項（目前勾了 {tot} 項）」、不再講「至少要勾一個」", f"勾太多了，最多 40 項（目前勾了 {tot} 項）" in msg and "至少要勾一個" not in msg, msg)

        # ---------- ② 一個都沒勾
        ad.click("#agrAllOff")
        ad.click("#agrSave"); ad.wait_for_timeout(300)
        msg = ad.inner_text("#agrFSt")
        ok(f"{T}：②全部清除後儲存 → 「至少要勾一個功能」、不送出", "至少要勾一個功能" in msg and len(puts) == n0, [msg, len(puts) - n0])

        # ---------- ③ 假新後端：88 項存得進去
        fake["mode"] = "new"
        open_welcome()
        ad.click("#agrAllOn")
        tot = ad.evaluate(TOT)
        if not ok(f"{T}：③可勾功能至少 88 項", tot >= 88, tot):
            return
        ok(f"{T}：③上限 200 → 全選 {tot} 項不顯示超過上限", "超過上限" not in ad.inner_text("#agrFCnt"), ad.inner_text("#agrFCnt"))
        keys = ad.evaluate("() => [...document.querySelectorAll('#agrFeats input[data-fk]')].map(i => i.dataset.fk)")
        for k in keys[88:]:
            ad.click(f"#agrFeats input[data-fk='{k}']")
        ok(f"{T}：③取消 {tot - 88} 項後剩 88 項、計數列寫「已勾 88／{tot} 項」", ad.evaluate(CNT) == 88 and f"已勾 88／{tot} 項" in ad.inner_text("#agrFCnt"), ad.inner_text("#agrFCnt"))
        with ad.expect_response(lambda r: "/v1/admin/grants/defs/put" in r.url, timeout=8000) as ri:
            ad.click("#agrSave")
        body = json.loads(ri.value.request.post_data or "{}")
        ok(f"{T}：③存檔送出的就是那 88 項", sorted((body.get("feats") or {}).keys()) == sorted(keys[:88]), len(body.get("feats") or {}))
        ok(f"{T}：③存檔成功（200）", ri.value.status == 200, ri.value.status)
        wait_until(ad, "() => /已儲存/.test((document.getElementById('agrSt') || {}).textContent || '')", 5000)
        ok(f"{T}：③清單寫「已儲存「新會員體驗」」", "已儲存" in (ad.inner_text("#agrSt") if ad.query_selector("#agrSt") else ""), ad.inner_text("#agrSt") if ad.query_selector("#agrSt") else None)
        open_welcome()
        ok(f"{T}：③重新打開編輯 → 仍是 88 項", ad.evaluate(CNT) == 88, ad.evaluate(CNT))

        # ---------- ④ 假新後端回 too_many_feats
        fake["mode"] = "too_many"
        with ad.expect_response(lambda r: "/v1/admin/grants/defs/put" in r.url, timeout=8000) as ri:
            ad.click("#agrSave")
        ok(f"{T}：④後端回 400", ri.value.status == 400, ri.value.status)
        wait_until(ad, "() => /勾太多/.test(document.getElementById('agrFSt').textContent)", 4000)
        msg = ad.inner_text("#agrFSt")
        ok(f"{T}：④訊息「勾太多了，最多 200 項」、不講「至少要勾一個」", "勾太多了，最多 200 項" in msg and "至少要勾一個" not in msg and "還沒部署" not in msg, msg)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for cx in ctxs:
            try:
                cx.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("體驗上限", lambda pg, b, base, code: t_grantmax_1107(b, base))
