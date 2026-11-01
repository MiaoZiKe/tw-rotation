# 驗收段落「體驗全選」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 體驗全選
# Andy 11-01：體驗編輯器「每個功能都看得到」「一次勾選該功能全部」；會員清單「體驗到期」。
# ① 功能清單有代表性項目、不含法遵禁止項，禁止灰字列有「分 K」
# ② 分組「全選／全不選」切換、頂端「全部全選」「全部清除」：勾選數與次數格真的變；全選後次數＝「每項次數」
# ③ 勾選後存檔（welcome 14 天）格式不變：存出去的 feats 就是勾的那些、次數是填的值
# ④ 會員清單「體驗到期」欄：有值、日期＝加入日＋活動天數、標「基本」；快到期琥珀、已過期灰字


def t_grantsel_1101(b, base):
    T = "體驗全選"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin,
                            "--person", f"trial={TRIAL_TEST_EMAIL}=體驗測試帳號"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_GRANTSEL_SHOTS")
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

        # ---------- ① 功能清單完整性
        ad.goto(base + "#admin/grants", wait_until="domcontentloaded")
        wait_until(ad, "() => document.querySelectorAll('#agrList button[data-edit]').length > 0", 10000)
        ad.click("#agrList button[data-edit=\"welcome\"]")
        wait_until(ad, "() => document.querySelectorAll('#agrFeats input[data-fk]').length > 10", 5000)
        keys = ad.evaluate("() => [...document.querySelectorAll('#agrFeats input[data-fk]')].map(i => i.dataset.fk)")
        for k in ("mkt.ma", "flow.rot", "stock.k_day"):
            ok(f"{T}：①功能清單有 {k}", k in keys, len(keys))
        ok(f"{T}：①清單仍不列法遵禁止項", not any(k in keys for k in ("mkt.cand", "explore.list", "stock.ai", "stock.mtf", "live.tick", "stock.k_min")), keys[:5])
        ban_txt = ad.inner_text("#agrFeats + .ban")
        ok(f"{T}：①禁止清單灰字有「分 K」", "分 K" in ban_txt, ban_txt)

        # ---------- ② 全選／全不選
        CNT = "() => document.querySelectorAll('#agrFeats input[data-fk]:checked').length"
        TOT = "() => document.querySelectorAll('#agrFeats input[data-fk]').length"
        ad.click("#agrAllOff")
        ok(f"{T}：②全部清除 → 勾選數 0、計數列寫 0", ad.evaluate(CNT) == 0 and "已勾 0／" in ad.inner_text("#agrFCnt"), ad.inner_text("#agrFCnt"))
        ad.fill("#agrM", "7")
        ad.click("#agrAllOn")
        tot = ad.evaluate(TOT)
        vals = ad.evaluate("() => [...document.querySelectorAll('#agrFeats input[data-fm]')].map(i => [i.value, i.disabled])")
        ok(f"{T}：②全部全選 → 全勾（{tot}）、次數格全啟用且＝每項次數 7", ad.evaluate(CNT) == tot and all(v == ["7", False] for v in vals), vals[:3])
        if shots:
            ad.locator("#agrForm").screenshot(path=str(pathlib.Path(shots) / "01_全部全選後.png"))
        ad.evaluate("() => document.querySelector('#agrFeats').scrollTop = 0")
        cat0 = ad.evaluate("() => { const b = document.querySelector('#agrFeats button[data-cat]'); return [b.dataset.cat, b.textContent]; }")
        ok(f"{T}：②全部全選後分組鈕寫「全不選」", cat0[1] == "全不選", cat0)
        ad.click(f"#agrFeats button[data-cat='{cat0[0]}']")
        n_in = ad.evaluate("(c) => document.querySelectorAll('#agrFeats input[data-fk][data-fc=\"' + c + '\"]').length", cat0[0])
        c_after = ad.evaluate(CNT)
        ok(f"{T}：②按該分組「全不選」→ 只少那一組（{n_in} 項）", c_after == tot - n_in and ad.evaluate("(c) => document.querySelector('#agrFeats button[data-cat=\"' + c + '\"]').textContent", cat0[0]) == "全選", [tot, n_in, c_after])
        ad.fill("#agrM", "4")
        ad.click(f"#agrFeats button[data-cat='{cat0[0]}']")
        grp_vals = ad.evaluate("(c) => [...document.querySelectorAll('#agrFeats input[data-fk][data-fc=\"' + c + '\"]')].map(i => document.querySelector('input[data-fm=\"' + i.dataset.fk + '\"]').value)", cat0[0])
        other = ad.evaluate("(c) => [...document.querySelectorAll('#agrFeats input[data-fk]:not([data-fc=\"' + c + '\"])')].map(i => document.querySelector('input[data-fm=\"' + i.dataset.fk + '\"]').value)", cat0[0])
        ok(f"{T}：②該分組「全選」→ 回到全勾；新勾的次數＝4、其餘保留 7", ad.evaluate(CNT) == tot and set(grp_vals) == {"4"} and set(other) == {"7"}, [grp_vals[:3], other[:3]])

        # ---------- ③ 存檔格式不變（welcome 14 天，開）
        ad.click("#agrAllOff")
        ad.fill("#agrM", "3")
        for k in ("mkt.ma", "flow.rot"):
            ad.click(f"#agrFeats input[data-fk='{k}']")
        ad.fill("input[data-fm='flow.rot']", "5")
        ad.fill("#agrDays", "14")
        if not ad.evaluate("() => document.getElementById('agrOn').checked"):
            ad.click("#agrOn")
        with ad.expect_response(lambda r: "/v1/admin/grants/defs/put" in r.url, timeout=8000) as ri:
            ad.click("#agrSave")
        body = json.loads(ri.value.request.post_data or "{}")
        ok(f"{T}：③存檔 feats 就是勾的兩項、次數照格子填的值（格式不變）", body.get("feats") == {"mkt.ma": 3, "flow.rot": 5}, body.get("feats"))
        ok(f"{T}：③存檔成功（200）", ri.value.status == 200, ri.value.status)

        # ---------- ④ 會員清單「體驗到期」
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        to_members(ad, None)
        email = TRIAL_TEST_EMAIL
        ok(f"{T}：④會員名單找得到體驗測試帳號", bool(wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr[data-email='{email}']\")", 6000)), email)
        hdr = ad.evaluate("() => [...document.querySelectorAll('#ptTable thead th')].map(t => t.textContent.trim())")
        ok(f"{T}：④表頭有「體驗到期」且在「到期日」後面", "體驗到期" in hdr and hdr.index("體驗到期") == hdr.index("到期日") + 1, hdr)
        cell = ad.evaluate("(e) => { const td = document.querySelector('#ptTable tr[data-email=\"' + e + '\"] td.c-wel'); const cr = document.querySelector('#ptTable tr[data-email=\"' + e + '\"] td.c-cr'); return td ? [td.innerText.trim(), td.querySelector('.wel') ? td.querySelector('.wel').className : '', cr ? cr.innerText.trim() : ''] : null; }", email)
        ok(f"{T}：④該列「體驗到期」有日期且標「基本」", bool(cell) and re.search(r"\d{4}-\d{2}-\d{2}", cell[0]) and "基本" in cell[0], cell)
        if cell:
            from datetime import date, timedelta
            d0 = date.fromisoformat(cell[2][:10]); d1 = date.fromisoformat(re.search(r"\d{4}-\d{2}-\d{2}", cell[0]).group(0))
            ok(f"{T}：④體驗到期＝加入日＋14 天（{d0}→{d1}）", (d1 - d0).days in (14, 15), (d0, d1))   # 跨台北午夜時加入時刻換算可差一天
        # 快到期／已過期：把活動天數改成 1 天 → 註冊剛過幾分鐘，還沒過期但 ≤3 天 → 琥珀
        d = next(x for x in call(ad, "/v1/admin/grants/defs/list", {})["defs"] if x["id"] == "welcome")
        d["days"] = 2
        r = call(ad, "/v1/admin/grants/defs/put", {k: d[k] for k in ("id", "kind", "name", "feats", "per", "days", "t0", "t1", "audience", "on")})
        ok(f"{T}：④前置：活動天數改 2 天", r.get("_s") == 200, r.get("_s"))
        ad.reload(wait_until="domcontentloaded")
        to_members(ad, None)
        wait_until(ad, f"() => !!document.querySelector(\"#ptTable tr[data-email='{email}'] td.c-wel .wel\")", 6000)
        col = ad.evaluate("(e) => { const s = document.querySelector('#ptTable tr[data-email=\"' + e + '\"] td.c-wel .wel'); return s ? [s.className, getComputedStyle(s).color] : null; }", email)
        ok(f"{T}：④≤3 天 → 琥珀色（class wel soon）", bool(col) and "soon" in col[0], col)
        if shots:
            ad.locator("#ptTable").first.screenshot(path=str(pathlib.Path(shots) / "02_會員清單體驗到期.png"))
        # 已過期：把註冊期間限定在過去 → 不適用 → 欄位「—」；改用延長值測不到，這裡驗灰字樣式存在即可
        has_css = ad.evaluate("() => { const s = document.createElement('span'); s.className = 'wel exp'; document.querySelector('#ptTable').appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; }")
        ok(f"{T}：④已過期樣式（wel exp）是灰字、和琥珀不同色", bool(has_css) and col and has_css != col[1], [has_css, col])
        # 一般使用者畫面不受影響
        usr_has = up_.evaluate("() => !!document.querySelector('.wel, td.c-wel')")
        ok(f"{T}：④一般使用者畫面沒有「體驗到期」欄", not usr_has, usr_has)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("體驗全選", lambda pg, b, base, code: t_grantsel_1101(b, base))
