# 驗收段落「預設雜湊1102」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 預設雜湊1102
# Andy 11-02：4 個測試帳預設標記（程式只放 email 的 SHA-256）。驗收用 window.__TW_TEST_HASHES 補「體驗測試帳」的雜湊當替身：
# ① 雜湊命中的會員自動有徽章、統計排除 ② 按「恢復計入統計」→ 徽章消失、總人數回來 ③ 重新整理後例外仍保留 ④ 再按「不列入統計」→ 又標回去


def t_testhash_1102(b, base):
    T = "預設雜湊1102"
    import urllib.request, hashlib
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


        h = hashlib.sha256(TRIAL_TEST_EMAIL.encode()).hexdigest()
        ad.add_init_script("window.__TW_TEST_HASHES = " + json.dumps([h]) + ";")
        ad.reload(wait_until="domcontentloaded")      # 同網址 goto 不會重載，init script 要重載才生效
        wait_until(ad, "() => !!document.getElementById('acctBtn') && Array.isArray(window.__TW_TEST_HASHES)", 8000)
        to_members(ad, None)
        wait_until(ad, "() => document.querySelectorAll('#ptTable tr[data-email]').length >= 2 && !!document.querySelector('#msTotal b')", 8000)
        ad.wait_for_timeout(800)
        TOT = "() => +document.querySelector('#msTotal b').textContent.replace(/,/g, '')"
        BAD = "(e) => { const r = document.querySelector('#ptTable tr[data-email=\"' + e + '\"]'); return r ? !!r.querySelector('.tbadge') : null; }"
        n_all = ad.evaluate("() => document.querySelectorAll('#ptTable tr[data-email]').length")
        trial = TRIAL_TEST_EMAIL
        ok(f"{T}：①雜湊命中的會員自動有徽章、統計排除（總人數 {n_all - 2}）", ad.evaluate(BAD, trial) is True and ad.evaluate(TOT) == n_all - 2, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        ad.click(f"#ptTable tr[data-email='{trial}']")
        wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]\")", 6000)
        ok(f"{T}：②展開列的按鈕寫「恢復計入統計」", "恢復計入統計" in ad.inner_text(f"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]"), None)
        ad.click(f"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]")
        ad.wait_for_timeout(700)
        ok(f"{T}：②按「恢復計入統計」→ 徽章消失、總人數回到 {n_all - 1}", ad.evaluate(BAD, trial) is False and ad.evaluate(TOT) == n_all - 1, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        ad.reload(wait_until="domcontentloaded")
        to_members(ad, None)
        wait_until(ad, "() => document.querySelectorAll('#ptTable tr[data-email]').length >= 2 && !!document.querySelector('#msTotal b')", 8000)
        ad.wait_for_timeout(1000)
        ok(f"{T}：③重新整理後例外仍保留（沒有又被預設標回去）", ad.evaluate(BAD, trial) is False and ad.evaluate(TOT) == n_all - 1, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        ad.click(f"#ptTable tr[data-email='{trial}']")
        wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]\")", 6000)
        ad.click(f"#ptTable tr.pmdet[data-for='{trial}'] button[data-test]")
        ad.wait_for_timeout(700)
        ok(f"{T}：④再按「不列入統計」→ 徽章回來、總人數 {n_all - 2}", ad.evaluate(BAD, trial) is True and ad.evaluate(TOT) == n_all - 2, [ad.evaluate(BAD, trial), ad.evaluate(TOT)])
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("預設雜湊1102", lambda pg, b, base, code: t_testhash_1102(b, base))
