# 驗收段落「登入卡住1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 登入卡住1016（Andy 10-16：「登入後會一直卡住這畫面，協助自動跳主畫面」）
# 本機起真的 worker.js（devserver.mjs，假 Google），用手指點（tap）走完三種情況，三種都要落在 #overview 而且已登入：
#   ① 彈窗失效（iPhone App 內建瀏覽器那種：window.close() 沒作用、opener 被切斷、原頁不在了）→「登入完成」頁 0.8 秒後整頁換回網站帶 #twn=<n>
#   ② 彈窗失效但原頁還在輪詢（兩邊搶同一個一次性代碼）→ 輸的那邊讀回共用的權杖，照樣登入
#   ③ LINE／FB／IG 的 UA → 一開始就整頁跳轉，不開彈窗
# 另外驗 10-16「所有信箱一律 liguligu0818@gmail.com」：客服寄信、條款聯絡信箱、登入告知裡沒有舊信箱。
def t_login_stuck_1016(b, base, code):
    import urllib.request
    T = "登入卡住1016"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_LOGIN1016_SHOTS")
    UA_LINE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
               "Mobile/15E148 Safari Line/14.12.0")
    UA_IOS = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
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

        def ctx(w, ua=None, broken_popup=False):
            kw = dict(viewport={"width": w, "height": 844 if w <= 640 else 900})
            if w <= 640:
                kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
            if ua:
                kw["user_agent"] = ua
            c = b.new_context(**kw)
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";")
            if broken_popup:
                # 只對 Worker 那邊的頁面：close() 沒作用、opener 被切斷 —— 就是 App 內建瀏覽器的樣子
                c.add_init_script("if (location.origin === " + json.dumps(api) + ") { try { window.close = function () {}; Object.defineProperty(window, 'opener', { get: () => null }); } catch (e) {} }")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            return c

        def tap(pg, sel):
            el = pg.locator(sel).first
            el.wait_for(state="visible", timeout=8000)
            if pg.context.pages and pg.viewport_size and pg.viewport_size["width"] <= 640:
                el.tap()
            else:
                el.click()

        def open_notice(pg):
            wait_until(pg, "() => !!window.TwAccount && TwAccount.on && TwAccount.on() && [...document.querySelectorAll('#acctBtn')].some(e => e.getClientRects().length)", 12000)
            btn = [i for i, v in enumerate(pg.evaluate("() => [...document.querySelectorAll('#acctBtn')].map(e => e.getClientRects().length > 0)")) if v]
            el = pg.locator("#acctBtn").nth(btn[0] if btn else 0)
            el.tap() if (pg.viewport_size or {}).get("width", 1440) <= 640 else el.click()
            if pg.evaluate("() => { const m = document.querySelector('#acctMenu [data-m=login]'); return !!m && m.getClientRects().length > 0; }"):
                tap(pg, "#acctMenu [data-m=login]")
            pg.wait_for_selector("#acctGo", state="visible", timeout=8000)

        def landed(pg, label):
            good = wait_until(pg, "() => location.hash === '#overview' && !!(window.TwAccount && TwAccount.user()) && !!localStorage.getItem('tw.acct.tok')", 15000)
            ok(f"{T}：{label} → 落在 #overview 而且已登入", bool(good),
               pg.evaluate("() => ({ url: location.href, user: !!(window.TwAccount && TwAccount.user()), tok: !!localStorage.getItem('tw.acct.tok') })"))
            ok(f"{T}：{label} → 網址不留一次性代碼", "twn=" not in pg.url, pg.url)

        # ① 彈窗失效、原頁不在了（390 手機、1440 桌機）
        for w in (390, 1440):
            c = ctx(w, ua=UA_IOS if w <= 640 else None, broken_popup=True)
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "#flow", wait_until="domcontentloaded")
            open_notice(pg)
            with pg.expect_popup() as pi:
                tap(pg, "#acctGo")
            pop = pi.value
            pop.on("pageerror", lambda e: errs.append(str(e)))
            pg.close()                    # 原頁不在了：只剩那個「小視窗」
            pop.wait_for_selector("#as-bob", timeout=8000)
            el = pop.locator("#as-bob")
            el.tap() if w <= 640 else el.click()
            pop.wait_for_load_state("domcontentloaded")
            if shots and w == 390:
                try:
                    pop.wait_for_selector("text=登入完成", timeout=3000)
                    pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
                    pop.screenshot(path=str(pathlib.Path(shots) / "login_done_page_390.png"))
                except Exception:  # noqa: BLE001
                    pass
            landed(pop, f"{w} 彈窗失效（close 沒作用、原頁已關）")
            if shots and w == 390:
                pop.wait_for_timeout(600)
                pop.screenshot(path=str(pathlib.Path(shots) / "login_after_390.png"))
            c.close()

        # ② 彈窗失效、原頁還在輪詢（兩邊搶同一個代碼）
        c = ctx(390, ua=UA_IOS, broken_popup=True)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        open_notice(pg)
        with pg.expect_popup() as pi:
            tap(pg, "#acctGo")
        pop = pi.value
        pop.wait_for_selector("#as-bob", timeout=8000)
        pop.locator("#as-bob").tap()
        landed(pop, "390 彈窗失效（原頁同時在輪詢）")
        ok(f"{T}：390 原頁也登入了", bool(wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 8000)))
        c.close()

        # ③ App 內建瀏覽器（LINE UA）：不開彈窗、直接整頁跳轉（360／390／430）
        for w in (360, 390, 430):
            c = ctx(w, ua=UA_LINE)
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
            pops: list = []
            pg.on("popup", lambda p: pops.append(p))
            pg.goto(base + "#season", wait_until="domcontentloaded")
            open_notice(pg)
            tap(pg, "#acctGo")
            pg.wait_for_selector("#as-bob", timeout=8000)
            ok(f"{T}：{w} LINE 內建瀏覽器 → 整頁跳到登入頁、沒有開彈窗", not pops and pg.url.startswith(api), pg.url)
            pg.locator("#as-bob").tap()
            landed(pg, f"{w} LINE 內建瀏覽器整頁跳轉")
            c.close()

        # ④ 信箱一律 liguligu0818@gmail.com（客服寄信分頁、條款聯絡）
        c = ctx(1440)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('supFab')", 8000)
        tap(pg, "#supFab")
        # 10-16 寄信分頁拿掉（客服聊天室1016）：信箱改在面板最底下一行，任何分頁都看得到
        pg.wait_for_selector("#supMail", state="visible", timeout=4000)
        href = pg.get_attribute("#supMail", "href") or ""
        ok(f"{T}：客服寄信 → 收件者是 liguligu0818@gmail.com", "to=liguligu0818%40gmail.com" in href, href)
        pg.goto(base + "#legal", wait_until="domcontentloaded")
        wait_until(pg, "() => /liguligu0818@gmail\\.com/.test(document.body.innerText)", 8000)
        txt = pg.evaluate("() => document.body.innerHTML")
        ok(f"{T}：條款頁聯絡信箱是 liguligu0818@gmail.com、沒有舊的個人信箱", "liguligu0818@gmail.com" in txt and "kcq01010909@" not in txt)
        c.close()
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:5])
    finally:
        dev.terminate()


# ★ 2026-10-16 Andy：「登入後會一直卡住這畫面，協助自動跳主畫面」＋「所有的Mail 包含意見回饋 使用liguligu那個」（devserver 真的 worker.js；⚠ --workers 1）
register("登入卡住1016", lambda pg, b, base, code: t_login_stuck_1016(b, base, code), after="帳號選單1009")
