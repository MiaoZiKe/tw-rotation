# 驗收段落「邀請欄1102」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 邀請欄1102
# 會員清單「邀請人數」「邀請延長天數」：/v1/admin/invite/stats 帶資料 → 有數字；後端 404 且 perm/list 沒欄位 → 「—」，不報錯。


def t_invite_cols_1102(b, base):
    T = "邀請欄1102"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin,
                            "--person", f"trial={TRIAL_TEST_EMAIL}=體驗測試帳號"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

        def new_ctx():
            c = b.new_context(viewport={"width": 1440, "height": 900})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def login(pg, who):
            pg.click("#acctBtn")
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=8000)
            pop.click("#as-" + who)
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        cu = new_ctx(); u = cu.new_page(); u.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(u, "() => !!document.getElementById('acctBtn')", 8000); login(u, "trial")
        CELL = "(e) => { const r = document.querySelector('#ptTable tr[data-email=\"' + e + '\"]'); return r ? [r.querySelector('td.c-inv').innerText.trim(), r.querySelector('td.c-invd').innerText.trim()] : null; }"
        for mode in ("data", "none"):
            ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append(f"{mode}: {e}"))
            if mode == "data":
                ad.route("**/v1/admin/invite/stats", lambda r: r.fulfill(status=200, content_type="application/json", headers={"access-control-allow-origin": "*"},
                         body=json.dumps({"stats": {"u1": {"email": TRIAL_TEST_EMAIL, "invited": 3, "reward_days": 6}}, "now": 0})))
            else:
                ad.route("**/v1/admin/invite/stats", lambda r: r.fulfill(status=404, content_type="application/json", headers={"access-control-allow-origin": "*"}, body="{}"))

                def strip(r):
                    resp = r.fetch(); j = resp.json()
                    for x in j.get("users", []):
                        x.pop("invited_count", None); x.pop("invite_reward_days", None)
                    r.fulfill(response=resp, body=json.dumps(j))
                ad.route("**/v1/admin/perm/list", strip)
            ad.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000); login(ad, "andy")
            to_members(ad, None)
            wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr[data-email='{TRIAL_TEST_EMAIL}'] td.c-inv\")", 8000)
            hdr = ad.evaluate("() => [...document.querySelectorAll('#ptTable thead th')].map(t => t.textContent.trim())")
            ok(f"{T}（{mode}）：表頭有「邀請人數」「邀請延長天數」", "邀請人數" in hdr and "邀請延長天數" in hdr, hdr)
            cell = ad.evaluate(CELL, TRIAL_TEST_EMAIL)
            if mode == "data":
                ok(f"{T}：stats 帶資料 → 邀請人數 3、延長天數 6", cell == ["3", "6"], cell)
            else:
                ok(f"{T}：404 且沒有欄位 → 兩欄都顯示「—」、頁面沒報錯", cell == ["—", "—"] and not errs, [cell, errs[:2]])
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("邀請欄1102", lambda pg, b, base, code: t_invite_cols_1102(b, base))
