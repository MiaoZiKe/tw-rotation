# 驗收段落「體驗上限」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 體驗上限
# Andy 11-07：「編輯：新會員體驗」勾 88／93 項按儲存，紅字「沒有存進去：至少要勾一個功能」。
# 根因是 Worker 上限 40、超過也回 bad_feats。11-07 先放寬到 200；同日 Andy：「為何需要限制200 我有幾個就能勾幾個 我後面如果繼續新增呢? 把這問題處理」
# → 不設業務上限：前端不再預檢、計數列只寫「已勾 X／總數 項」；後端只剩 2000 項防濫用安全網（too_many_feats 後備訊息）。
# 本機起真的 worker.js（devserver），錯誤訊息用 Playwright 攔截 grants 兩支 API 當假 Worker：
# ① 假 Worker 清單仍回舊的 max_feats 40（模擬舊後端）：全部全選 → 計數列「已勾 N／N 項」、沒有任何上限提示、不是紅字；
#    按儲存真的送出全部 N 項到真 worker.js → 200、「已儲存」，重新打開仍是 N 項
# ② 全部清除後按儲存 → 「至少要勾一個功能」、不送出
# ③ 假 Worker 回 too_many_feats（max 2000，安全網）→ 後備訊息「勾太多了，超過系統安全上限 2000 項」，不講「至少要勾一個」

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
        fake = {"mode": "small"}
        puts: list[dict] = []

        def on_list(route):
            r = route.fetch()
            j = r.json()
            if fake["mode"] == "small":
                j["max_feats"] = 40
            route.fulfill(response=r, json=j)

        def on_put(route):
            body = json.loads(route.request.post_data or "{}")
            puts.append(body)
            if fake["mode"] == "too_many":
                route.fulfill(status=400, json={"error": "too_many_feats", "max": 2000}, headers={"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"})
                return
            route.continue_()   # 真的送到本機 worker.js

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

        # ---------- ① 全選後存檔成功，不再有上限提示（假 Worker 清單回舊的 max_feats 40，前端必須忽略）
        open_welcome()
        ad.click("#agrAllOn")
        tot = ad.evaluate(TOT)
        if not ok(f"{T}：①可勾功能至少 88 項", tot >= 88, tot):
            return
        cnt_txt = ad.inner_text("#agrFCnt")
        ok(f"{T}：①全部全選 → 計數列只寫「已勾 {tot}／{tot} 項」、沒有上限提示", cnt_txt.strip() == f"已勾 {tot}／{tot} 項" and "上限" not in cnt_txt, cnt_txt)
        ok(f"{T}：①計數列不是紅字", not ad.evaluate("() => document.getElementById('agrFCnt').classList.contains('over')"))
        keys = ad.evaluate("() => [...document.querySelectorAll('#agrFeats input[data-fk]')].map(i => i.dataset.fk)")
        with ad.expect_response(lambda r: "/v1/admin/grants/defs/put" in r.url, timeout=8000) as ri:
            ad.click("#agrSave")
        body = json.loads(ri.value.request.post_data or "{}")
        ok(f"{T}：①存檔送出的是全部 {tot} 項", sorted((body.get("feats") or {}).keys()) == sorted(keys), len(body.get("feats") or {}))
        ok(f"{T}：①存檔成功（200）", ri.value.status == 200, ri.value.status)
        wait_until(ad, "() => /已儲存/.test((document.getElementById('agrSt') || {}).textContent || '')", 5000)
        ok(f"{T}：①清單寫「已儲存「新會員體驗」」", "已儲存" in (ad.inner_text("#agrSt") if ad.query_selector("#agrSt") else ""), ad.inner_text("#agrSt") if ad.query_selector("#agrSt") else None)
        open_welcome()
        ok(f"{T}：①重新打開編輯 → 仍是全部 {tot} 項", ad.evaluate(CNT) == tot, ad.evaluate(CNT))
        ok(f"{T}：①重新打開後計數列仍沒有上限提示", "上限" not in ad.inner_text("#agrFCnt"), ad.inner_text("#agrFCnt"))

        # ---------- ② 一個都沒勾
        n0 = len(puts)
        ad.click("#agrAllOff")
        ad.click("#agrSave"); ad.wait_for_timeout(300)
        msg = ad.inner_text("#agrFSt")
        ok(f"{T}：②全部清除後儲存 → 「至少要勾一個功能」、不送出", "至少要勾一個功能" in msg and len(puts) == n0, [msg, len(puts) - n0])

        # ---------- ③ 假 Worker 回 too_many_feats（2000 項安全網，後備訊息）
        fake["mode"] = "too_many"
        open_welcome()
        with ad.expect_response(lambda r: "/v1/admin/grants/defs/put" in r.url, timeout=8000) as ri:
            ad.click("#agrSave")
        ok(f"{T}：③後端回 400", ri.value.status == 400, ri.value.status)
        wait_until(ad, "() => /勾太多/.test(document.getElementById('agrFSt').textContent)", 4000)
        msg = ad.inner_text("#agrFSt")
        ok(f"{T}：③後備訊息「勾太多了，超過系統安全上限 2000 項」、不講「至少要勾一個」", "超過系統安全上限 2000 項" in msg and "至少要勾一個" not in msg, msg)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for cx in ctxs:
            try:
                cx.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("體驗上限", lambda pg, b, base, code: t_grantmax_1107(b, base))
