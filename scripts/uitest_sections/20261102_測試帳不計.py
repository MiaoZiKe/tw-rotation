# 驗收段落「測試帳不計1102」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 測試帳不計1102
# Andy 11-02：會員使用概況要排除測試帳。標記只存站主瀏覽器 localStorage（email 不進 repo）；第一次預設標站主本人。
# ① 預設：站主本人那列有「測試・不計」徽章、統計總人數少 1、標題旁「已排除 1 個測試帳」
# ② 展開另一人 → 按「不列入統計」→ 徽章出現、總人數再少 1；按「恢復計入統計」→ 恢復
# ③ 重新整理標記保留；「隱藏測試帳」勾選 → 名單少掉被標的列；取消勾選恢復
# ④ 「依 email 標記」小工具：輸入開頭幾個字 → 標記成功、徽章出現


# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 體驗全選
# Andy 11-01：體驗編輯器「每個功能都看得到」「一次勾選該功能全部」；會員清單「體驗到期」。
# ① 功能清單有代表性項目、不含法遵禁止項，禁止灰字列有「分 K」
# ② 分組「全選／全不選」切換、頂端「全部全選」「全部清除」：勾選數與次數格真的變；全選後次數＝「每項次數」
# ③ 勾選後存檔（welcome 14 天）格式不變：存出去的 feats 就是勾的那些、次數是填的值
# ④ 會員清單「體驗到期」欄：有值、日期＝加入日＋活動天數、標「基本」；快到期琥珀、已過期灰字


def t_testacct_1102(b, base):
    T = "測試帳不計1102"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin,
                            "--person", f"trial={TRIAL_TEST_EMAIL}=體驗測試帳號"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_TESTACCT_SHOTS")
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
        if not ok(f"{T}：本機 account-api 起得來", up):
            return

        def new_ctx(width=1440):
            c = b.new_context(viewport={"width": width, "height": 900})
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

        def call(pg, path, body):
            return pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])

        # 先讓體驗測試帳號登入一次（建立會員、記下加入時間）
        cu = new_ctx(); up_ = cu.new_page(); up_.on("pageerror", lambda e: errs.append("user: " + str(e)))
        up_.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(up_, "() => !!document.getElementById('acctBtn')", 8000)
        login(up_, "trial")

        ca = new_ctx(); ad = ca.new_page(); ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        login(ad, "andy")


        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        to_members(ad, None)
        wait_until(ad, "() => document.querySelectorAll('#ptTable tr[data-email]').length >= 2 && !!document.querySelector('#msTotal b')", 8000)
        TOT = "() => +document.querySelector('#msTotal b').textContent.replace(/,/g, '')"
        BAD = "(e) => { const r = document.querySelector('#ptTable tr[data-email=\"' + e + '\"]'); return r ? !!r.querySelector('.tbadge') : null; }"
        n_all = ad.evaluate("() => document.querySelectorAll('#ptTable tr[data-email]').length")
        andy = ad.evaluate("() => [...document.querySelectorAll('#ptTable tr[data-email]')].map(r => r.dataset.email).find(e => e.startsWith('andy'))")
        trial = TRIAL_TEST_EMAIL
        ok(f"{T}：①站主本人預設標測試帳（徽章）、體驗測試帳沒有", ad.evaluate(BAD, andy) is True and ad.evaluate(BAD, trial) is False, [andy, trial])
        ok(f"{T}：①統計總人數＝名單 {n_all} 人 − 1（站主）", ad.evaluate(TOT) == n_all - 1, [ad.evaluate(TOT), n_all])
        ok(f"{T}：①標題旁寫「已排除 1 個測試帳」", "已排除 1 個測試帳" in (ad.inner_text("#msEx") if ad.locator("#msEx").count() else ""), ad.locator("#msEx").count())
        if shots:
            ad.locator("#ptStats").screenshot(path=str(pathlib.Path(shots) / "01_統計已排除.png"))
        # ② 展開 trial → 不列入統計
        ad.click(f"#ptTable tr[data-email='{trial}']")
        wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]\")", 6000)
        ad.click(f"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]")
        wait_until(ad, "(n) => +document.querySelector('#msTotal b').textContent === n", 4000) if False else ad.wait_for_timeout(600)
        ok(f"{T}：②不列入統計 → 徽章出現、總人數 {n_all - 2}", ad.evaluate(BAD, trial) is True and ad.evaluate(TOT) == n_all - 2, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        if shots:
            ad.locator("#ptMail").screenshot(path=str(pathlib.Path(shots) / "02_清單徽章.png"))
        ad.click(f"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]")
        ad.wait_for_timeout(600)
        ok(f"{T}：②恢復計入統計 → 徽章消失、總人數回 {n_all - 1}", ad.evaluate(BAD, trial) is False and ad.evaluate(TOT) == n_all - 1, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        # ④ 依 email 標記
        ad.fill("#pmTestMail", trial[:5])
        ad.click("#pmTestGo")
        ad.wait_for_timeout(600)
        ok(f"{T}：④依 email 開頭標記 → 回報、徽章出現、總人數 {n_all - 2}", "已標記" in ad.inner_text("#pmTestSt") and ad.evaluate(BAD, trial) is True and ad.evaluate(TOT) == n_all - 2, ad.inner_text("#pmTestSt"))
        # ③ 重新整理保留
        ad.reload(wait_until="domcontentloaded")
        to_members(ad, None)
        wait_until(ad, "() => document.querySelectorAll('#ptTable tr[data-email]').length >= 2 && !!document.querySelector('#msTotal b')", 8000)
        ok(f"{T}：③重新整理後標記保留（兩人都有徽章、總人數 {n_all - 2}）", ad.evaluate(BAD, trial) is True and ad.evaluate(BAD, andy) is True and ad.evaluate(TOT) == n_all - 2, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        ad.check("#pmHideTest")
        ad.wait_for_timeout(500)
        n_h = ad.evaluate("() => document.querySelectorAll('#ptTable tr[data-email]').length")
        ok(f"{T}：③勾「隱藏測試帳」→ 名單少掉被標的 2 列（{n_all}→{n_h}）、統計不變", n_h == n_all - 2 and ad.evaluate(TOT) == n_all - 2, [n_h, ad.evaluate(TOT)])
        ad.uncheck("#pmHideTest")
        ad.wait_for_timeout(500)
        ok(f"{T}：③取消勾選 → 名單恢復 {n_all} 列", ad.evaluate("() => document.querySelectorAll('#ptTable tr[data-email]').length") == n_all, n_all)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("測試帳不計1102", lambda pg, b, base, code: t_testacct_1102(b, base))
