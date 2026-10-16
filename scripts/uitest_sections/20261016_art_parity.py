# 驗收段落「精選文章共通功能1016」—— 2026-10-16
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_tour_walk_1009()、_free_port()、ROOT…直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章共通功能1016
# Andy 10-16：「精選文章其他分頁有的功能 他也要有 例如導覽 限制 這些都要在確認」。逐項真的操作、驗畫面真的變了：
#   ① 導覽：#articles、#article/<id> 頁名旁「導覽」（手機 🧭 → 本頁導覽）真的點下去，一路按「下一步」到「完成」，每一步都框得到元素、0 步被跳過；
#      全站導覽多一步「精選文章」，框的是側欄那一格、真的換到 #articles。
#   ② 限制：本機 account-api（devserver，真的 Worker 邏輯）。管理者在 #admin/perm「訪客」範本把「閱讀文章（單篇）」關掉、按儲存 →
#      訪客打開文章看到需開通卡（清單頁不受影響、也不記點閱）→ 打開開關 → 恢復；關掉「比比產業鏈」類別 → 只有那一類被擋；
#      設「每日 1 篇」→ 讀第一篇正常、第二篇蓋「今日已用完 1/1」、回頭看第一篇照常（同一篇不重算）。
#   ③ 流量觀測：訪客看過文章 → Worker 記到 pv:articles；管理區流量觀測有「精選文章」分頁、數字 > 0、細項列出被讀的文章標題。
#   ④ 搜尋：左上搜尋框打文章標題的一段 → 下拉出現「精選文章」那一段 → 點下去進那一篇（電腦點、手機點）。
#   截圖：TW_ART_SHOTS 有設才存（導覽進行中、鎖卡、管理區設定頁；1440 與 390）。
ART_A = "2026-10-14-know-cowos"            # 比比知識
ART_B = "2026-10-14-intro-ai-server"       # 比比產業鏈


def _art_shot(pg, name):
    d = os.environ.get("TW_ART_SHOTS")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(d) / f"{name}.png"))


def t_art_parity_1016(b, base):
    T = "精選文章共通功能1016"
    import urllib.request

    # ---------------------------------------------------------------- ① 導覽（電腦 1440、手機 402 觸控）
    floors = {("articles", "desk"): 4, ("article", "desk"): 6, ("articles", "mob"): 3, ("article", "mob"): 5}
    for mode in ("desk", "mob"):
        W = "1440" if mode == "desk" else "402"
        if mode == "desk":
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
        else:
            ctx = b.new_context(viewport={"width": 402, "height": 874}, is_mobile=True, has_touch=True, device_scale_factor=1)
        ctx.add_init_script("try{localStorage.setItem('tw.live.on','0')}catch(e){}")
        errs = []
        try:
            for r, want in (("#articles", "articles"), ("#article/" + ART_A, "article")):
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(base + r, wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.querySelector('#artList .artc, #artPost .artttl')", 12000)
                pg.wait_for_timeout(1200)
                ok(f"{T}[導覽] {W} {r}：這一頁有本頁導覽（{want}）", pg.evaluate("() => TwTour.pageTour()") == want, pg.evaluate("() => TwTour.pageTour()"))
                vis = pg.evaluate("() => { const e = document.getElementById('twPageTourBtn'); if (!e || e.hidden) return false; const q = e.getBoundingClientRect(); return q.width > 0 && q.height > 0 && q.left >= 0 && q.right <= innerWidth; }")
                ok(f"{T}[導覽] {W} {r}：入口看得見（{'頁名旁「導覽」' if mode == 'desk' else '頂欄 🧭'}）", vis)
                if not vis:
                    pg.close(); continue
                if mode == "desk":
                    nx = pg.evaluate("() => { const b = document.getElementById('twPageTourBtn'), h = document.querySelector('#l4Head h1'); return !!h && b.previousElementSibling === h && (b.textContent || '').trim() === '導覽'; }")
                    ok(f"{T}[導覽] {W} {r}：「導覽」緊貼在頁名「精選文章」右邊", nx)
                    pg.locator("#twPageTourBtn").click()
                else:
                    pg.locator("#twPageTourBtn").tap()
                    pk = wait_until(pg, "() => { const m = document.getElementById('twTourPick'); return !!m && !m.hidden && m.getClientRects().length > 0; }", 3000)
                    ok(f"{T}[導覽] {W} {r}：點 🧭 跳出「本頁導覽／平台導覽」，本頁那列寫的是{'精選文章導覽' if want == 'articles' else '文章導覽'}",
                       bool(pk) and ("精選文章導覽" if want == "articles" else "文章導覽") in pg.inner_text("#twTourPick"))
                    pg.locator("#twPickPage").tap()
                pg.wait_for_timeout(300)
                # 走到第 2 步截圖（聚光燈＋說明卡），再從頭整套走完
                if wait_until(pg, "() => { const s = TwTour.state(); return s.active && !s.busy && s.i === 0 && s.since > 350; }", 8000):
                    pg.evaluate("() => TwTour.next()")
                    wait_until(pg, "() => { const s = TwTour.state(); return s.active && !s.busy && s.i === 1 && s.since > 450; }", 8000)
                    _art_shot(pg, f"tour_{want}_{W}")
                    pg.evaluate("() => TwTour.prev()")
                    wait_until(pg, "() => { const s = TwTour.state(); return s.active && !s.busy && s.i === 0; }", 8000)
                n, bad = _tour_walk_1009(pg, f"{T}[導覽] {W} {r}", want, mode == "mob")
                ok(f"{T}[導覽] {W} {r}：一路按「下一步」到「完成」，每一步框得到元素、說明卡在畫面內、沒有步驟被跳過、不卡住", not bad, bad[:4])
                fl = floors[(want, mode)]
                ok(f"{T}[導覽] {W} {r}：至少走 {fl} 步（實際 {n}）", n >= fl, n)
                hs = pg.evaluate("() => location.hash")
                ok(f"{T}[導覽] {W} {r}：導覽結束後還停在原本那一頁（{hs}）", hs == r, hs)
                pg.close()
            # 全站導覽：多一步「精選文章」→ 框側欄（手機框頁名）、真的換到 #articles
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(2200)
            stp = pg.evaluate("() => TwTour.steps('site').map(s => s.t)")
            k = next((i for i, t in enumerate(stp) if "精選文章" in t), -1)
            ok(f"{T}[導覽] {W} 全站導覽有「精選文章」那一步，排在總覽之後、財經日曆之前", k > 0 and "總覽" in stp[k - 1] and "財經日曆" in stp[k + 1], stp)
            pg.evaluate("() => TwTour.start('site')")
            got = None
            for _ in range(k + 2):
                if not wait_until(pg, "() => { const s = TwTour.state(); return s.active && !s.busy && s.i >= 0 && s.since > 250; }", 15000):
                    break
                st = pg.evaluate("() => TwTour.state()")
                if "精選文章" in st["title"]:
                    got = st; break
                pg.evaluate("() => TwTour.next()")
            ok(f"{T}[導覽] {W} 全站導覽走到「精選文章」：網址換成 #articles、框的是 {'側欄那一格' if mode == 'desk' else '頁名'}、框在畫面內",
               bool(got) and got["hash"] == "#articles" and got["target"] and got["target"]["w"] > 10 and got["target"]["b"] > 0 and got["target"]["t"] < got["vh"]
               and (mode != "desk" or "articles" in got["sel"]), got and {k2: got[k2] for k2 in ("title", "hash", "sel", "target")})
            pg.evaluate("() => TwTour.stop()")
            pg.close()
            ok(f"{T}[導覽] {W}：沒有 JS 錯誤", not errs, errs[:3])
        finally:
            ctx.close()

    # ---------------------------------------------------------------- ②③④ 本機 account-api（devserver）
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    errs: list[str] = []
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

        def new_ctx(width=1440):
            kw = {"has_touch": True, "is_mobile": True, "device_scale_factor": 1} if width <= 640 else {}
            c = b.new_context(viewport={"width": width, "height": 900 if width > 640 else 844}, **kw)
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + "; try{localStorage.setItem('tw.live.on','0')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            return c

        # ---- 管理者登入、到 #admin/perm「訪客」範本
        ca = new_ctx(); ad = ca.new_page()
        ad.on("pageerror", lambda e: errs.append("admin: " + str(e)))
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        ad.click("#acctBtn")
        with ad.expect_popup() as pi:
            ad.click("#acctGo")
        pop = pi.value; pop.wait_for_selector("#as-andy", timeout=8000); pop.click("#as-andy")
        wait_until(ad, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        ad.evaluate("() => { location.hash = '#admin/perm'; }")
        wait_until(ad, "() => location.hash === '#admin/perm' && document.querySelectorAll('#pmCats .pmcat').length > 0", 12000)
        ad.click("#ptTier button[data-tier='guest']")
        wait_until(ad, "() => !!document.querySelector(\"#pmCats input[data-f='art.read']\") || !!document.querySelector(\"#pmCats .pmcat[data-cat='articles']\")", 5000)
        if not ad.evaluate("() => !!document.querySelector(\"#pmCats input[data-f='art.read']\")"):
            ad.click("#pmCats .pmcat[data-cat='articles'] .pmcathd")     # 預設收起：點標題展開
        wait_until(ad, "() => !!document.querySelector(\"#pmCats input[data-f='art.read']\")", 4000)
        cat = ad.evaluate("""() => { const c = document.querySelector("#pmCats .pmcat[data-cat='articles']"); if (!c) return null;
            const ids = [...c.querySelectorAll('input[role=switch][data-f]')].map(i => [i.dataset.f, i.checked]);
            const order = [...document.querySelectorAll('#pmCats .pmcat')].map(x => x.dataset.cat);
            return { ids, h: (c.querySelector('h3') || {}).textContent || '', order }; }""")
        ok(f"{T}[限制] #admin/perm 有「精選文章」分類卡，五個開關（清單、單篇、三個類別）預設全開",
           bool(cat) and [x[0] for x in cat["ids"]] == ["art.list", "art.read", "art.cat.news", "art.cat.intro", "art.cat.know"] and all(x[1] for x in cat["ids"]) and "精選文章" in cat["h"], cat)
        ok(f"{T}[限制] 卡片順序跟左側選單一樣：總覽 → 精選文章", bool(cat) and cat["order"][:2] == ["overview", "articles"], cat and cat["order"][:4])

        def save_plan():
            wait_until(ad, "() => !document.getElementById('pmSave').hidden", 3000)
            with ad.expect_response(lambda r: "/v1/admin/plans/put" in r.url, timeout=8000) as ri:
                ad.click("#pmSaveGo")
            j = ri.value.json()
            return next((p for p in j.get("plans", []) if p.get("id") == "guest"), {})

        def flip(fid):
            ad.click(f"#pmCats input[data-f='{fid}']")
            return save_plan()

        # 訪客（另一個瀏覽器）
        cg = new_ctx(); reqs: list[str] = []
        cg.on("request", lambda r: reqs.append(r.url.split("?")[0].replace(api, "")) if r.url.startswith(api + "/v1/") else None)
        gp = cg.new_page(); gp.on("pageerror", lambda e: errs.append("guest: " + str(e)))
        PERM_OK = "() => window.TwPerm && TwPerm.state().src === 'server'"
        LOCKED = """() => { const p = document.getElementById('artPost'); if (!p) return null;
            const card = p.querySelector(':scope > .qcov .qcard');
            return { plk: p.getAttribute('data-plk') || '', qlk: p.getAttribute('data-qlk') || '', card: card ? card.textContent.replace(/\\s+/g, ' ') : '',
                     cardVis: !!card && card.getBoundingClientRect().height > 40 && card.getBoundingClientRect().top < innerHeight && card.getBoundingClientRect().bottom > 0,
                     cat: p.dataset.cat, id: p.dataset.id, list: !!document.querySelector('#artCard[data-plk], #artCard[data-qlk]') }; }"""

        def open_art(pg, aid):
            pg.evaluate("(h) => { location.hash = h; }", "#article/" + aid)
            wait_until(pg, f"() => !!document.querySelector('#artPost[data-id=\"{aid}\"] .artttl')", 10000)
            pg.wait_for_timeout(900)     # 鎖頭／額度卡是下一個畫格才掛；點閱 recordOpen 等 450ms
            return pg.evaluate(LOCKED)

        gp.goto(base + "#articles", wait_until="domcontentloaded")
        wait_until(gp, PERM_OK, 10000)
        st0 = open_art(gp, ART_A)
        ok(f"{T}[限制] 上線預設：訪客打開文章，沒有任何鎖頭、內文看得到", bool(st0) and not st0["plk"] and not st0["qlk"] and gp.evaluate("() => document.getElementById('artBody').getClientRects().length > 0"), st0)

        # (a) 訪客範本關掉「閱讀文章（單篇）」
        g = flip("art.read")
        ok(f"{T}[限制] 管理者關掉訪客的「閱讀文章（單篇）」→ 儲存後 Worker 範本 feats 有 art.read: false", (g.get("feats") or {}).get("art.read") is False, g.get("feats"))
        _art_shot(ad, "admin_perm_1440")
        n_view0 = sum(1 for u in reqs if u == "/v1/articles/view")
        gp.reload(wait_until="domcontentloaded"); wait_until(gp, PERM_OK, 10000)
        wait_until(gp, "() => TwPerm.locked().includes('art.read')", 8000)
        st1 = open_art(gp, ART_B)
        ok(f"{T}[限制] 訪客打開文章 → 內文蓋「此功能需開通」卡（置中、在畫面內）", bool(st1) and "此功能需開通" in st1["plk"] and "此功能需開通" in st1["card"] and st1["cardVis"], st1)
        ok(f"{T}[限制] 被擋住的那一篇不算點閱（沒有送 /v1/articles/view）", sum(1 for u in reqs if u == "/v1/articles/view") == n_view0, reqs[-8:])
        _art_shot(gp, "lock_read_1440")
        gp.evaluate("() => { location.hash = '#articles'; }")
        wait_until(gp, "() => document.querySelectorAll('#artList .artc').length > 0", 8000); gp.wait_for_timeout(500)
        ok(f"{T}[限制] 清單頁不受「單篇」開關影響（沒有鎖頭、卡片點得到）", gp.evaluate("() => !document.querySelector('#artCard[data-plk]') && document.querySelectorAll('#artList .artc').length > 0"))
        # 手機 390 看鎖卡
        cm = new_ctx(390); mp = cm.new_page(); mp.on("pageerror", lambda e: errs.append("guest-m: " + str(e)))
        mp.goto(base + "#article/" + ART_B, wait_until="domcontentloaded"); wait_until(mp, PERM_OK, 10000)
        wait_until(mp, "() => !!document.querySelector('#artPost[data-plk]')", 8000); mp.wait_for_timeout(600)
        stm = mp.evaluate(LOCKED)
        ok(f"{T}[限制] 手機 390 一樣蓋需開通卡、卡片在畫面內、沒有橫向捲軸", bool(stm) and "此功能需開通" in stm["card"] and stm["cardVis"]
           and mp.evaluate("() => document.documentElement.scrollWidth <= innerWidth"), stm)
        _art_shot(mp, "lock_read_390")
        cm.close()

        # (b) 打開恢復；改關「比比產業鏈」類別
        g = flip("art.read")
        ok(f"{T}[限制] 管理者把「閱讀文章」打開 → 範本不再有 art.read: false", (g.get("feats") or {}).get("art.read") is not False, g.get("feats"))
        g = flip("art.cat.intro")
        ok(f"{T}[限制] 管理者關掉訪客的「比比產業鏈（單篇）」→ 範本 feats 有 art.cat.intro: false", (g.get("feats") or {}).get("art.cat.intro") is False, g.get("feats"))
        gp.reload(wait_until="domcontentloaded"); wait_until(gp, PERM_OK, 10000)
        wait_until(gp, "() => TwPerm.locked().includes('art.cat.intro') && !TwPerm.locked().includes('art.read')", 8000)
        sa = open_art(gp, ART_A); sb = open_art(gp, ART_B)
        ok(f"{T}[限制] 打開恢復：比比知識那篇正常看得到（沒有鎖頭）", bool(sa) and not sa["plk"] and not sa["qlk"], sa)
        ok(f"{T}[限制] 只關比比產業鏈：產業鏈那篇蓋需開通卡、卡上寫的是「比比產業鏈（單篇）」", bool(sb) and "此功能需開通" in sb["card"] and "比比產業鏈" in sb["card"] and sb["cat"] == "intro", sb)
        g = flip("art.cat.intro")
        ok(f"{T}[限制] 再把比比產業鏈打開 → 範本恢復", (g.get("feats") or {}).get("art.cat.intro") is not False, g.get("feats"))

        # (c) 每日 1 篇
        ad.click("#pmCats button[data-limb='art.read']")
        ad.fill("#pmCats input[data-lim='art.read']", "1")
        ad.click("#pmCats .pmlimpop button[data-limok]")
        ok(f"{T}[限制] 「閱讀文章」設每日 1 次 → 徽章「1/日」", bool(wait_until(ad, "() => (document.querySelector(\"#pmCats button[data-limb='art.read']\") || {}).textContent === '1/日'", 3000)))
        g = save_plan()
        ok(f"{T}[限制] 儲存後 Worker 範本 lims 有 art.read: 1", (g.get("lims") or {}).get("art.read") == 1, g.get("lims"))
        cq = new_ctx(); qp = cq.new_page(); qp.on("pageerror", lambda e: errs.append("guest-q: " + str(e)))
        qp.goto(base + "#articles", wait_until="domcontentloaded"); wait_until(qp, "() => window.TwPerm && TwPerm.state().src === 'server' && TwPerm.lim('art.read') === 1", 10000)
        q1 = open_art(qp, ART_A)
        ok(f"{T}[額度] 每日 1 篇：讀第一篇正常（沒有額度卡）、計數 1", bool(q1) and not q1["qlk"] and qp.evaluate("() => TwQuota.used('art.read').length") == 1, (q1, qp.evaluate("() => TwQuota.used('art.read')")))
        q2 = open_art(qp, ART_B)
        ok(f"{T}[額度] 第二篇 → 蓋「今日已用完 1/1」額度卡（置中、在畫面內）", bool(q2) and "1/1" in q2["qlk"] and q2["cardVis"] and "閱讀文章" in q2["card"], q2)
        _art_shot(qp, "quota_read_1440")
        q3 = open_art(qp, ART_A)
        ok(f"{T}[額度] 回頭看第一篇 → 照常看得到（同一篇同一天不重算）", bool(q3) and not q3["qlk"] and qp.evaluate("() => TwQuota.used('art.read').length") == 1, q3)
        cq.close()
        ad.click("#pmCats button[data-limb='art.read']")
        ad.click("#pmCats button[data-limclr='art.read']")
        ad.click("#pmCats .pmlimpop button[data-limok]") if ad.locator("#pmCats .pmlimpop button[data-limok]").count() else None
        g = save_plan()
        ok(f"{T}[額度] 管理者按「不限」→ 範本 lims 拿掉 art.read（恢復不限）", "art.read" not in (g.get("lims") or {}), g.get("lims"))

        # ---- ④ 搜尋（訪客那一頁）：打標題的一段 → 精選文章那一段 → 點進去
        gp.evaluate("() => { location.hash = '#overview'; }"); gp.wait_for_timeout(600)
        gp.click("#q"); gp.fill("#q", "CoWoS 是什麼")
        sg = wait_until(gp, "() => { const r = document.querySelector('#sugg [data-art]'); return r && r.getClientRects().length ? [document.getElementById('sgArtHd') ? document.getElementById('sgArtHd').textContent : '', r.dataset.art, r.textContent] : null; }", 6000)
        ok(f"{T}[搜尋] 左上搜尋框打「CoWoS 是什麼」→ 下拉出現「精選文章」那一段與那篇文章", bool(sg) and "精選文章" in sg[0] and sg[1] == ART_A, sg)
        _art_shot(gp, "search_1440")
        gp.click(f"#sugg [data-art='{ART_A}']")
        okp = wait_until(gp, f"() => location.hash === '#article/{ART_A}' && !!document.querySelector('#artPost[data-id=\"{ART_A}\"] .artttl')", 8000)
        ok(f"{T}[搜尋] 點那一列 → 換到那一篇、內文畫出來、下拉收起", bool(okp) and gp.evaluate("() => getComputedStyle(document.getElementById('sugg')).display === 'none'"))
        gp.click("#q"); gp.fill("#q", "伺服器產業鏈"); wait_until(gp, "() => !!document.querySelector('#sugg [data-art]')", 6000)
        gp.press("#q", "Enter")
        ok(f"{T}[搜尋] 只有文章符合時按 Enter → 進第一篇符合的文章", bool(wait_until(gp, f"() => location.hash === '#article/{ART_B}'", 6000)), gp.evaluate("() => location.hash"))
        cm = new_ctx(390); mp = cm.new_page(); mp.on("pageerror", lambda e: errs.append("guest-m2: " + str(e)))
        mp.goto(base + "#overview", wait_until="domcontentloaded"); mp.wait_for_timeout(2000)
        if mp.locator("#m4Search").count():
            mp.locator("#m4Search").tap()
        mp.locator("#q").fill("法說會")
        msg = wait_until(mp, "() => { const r = document.querySelector('#sugg [data-art]'); if (!r || !r.getClientRects().length) return null; const q = r.getBoundingClientRect(); return [r.dataset.art, q.left >= 0 && q.right <= innerWidth + 0.5, parseFloat(getComputedStyle(r.querySelector('.nm')).fontSize)]; }", 6000)
        ok(f"{T}[搜尋] 手機 390：搜尋「法說會」→ 文章列在畫面內、字 ≥ 12px", bool(msg) and msg[1] and msg[2] >= 12, msg)
        _art_shot(mp, "search_390")
        if msg:
            mp.locator(f"#sugg [data-art='{msg[0]}']").first.tap()
            ok(f"{T}[搜尋] 手機點文章列 → 進那一篇", bool(wait_until(mp, f"() => location.hash === '#article/{msg[0]}' && !!document.querySelector('#artPost .artttl')", 8000)))
        cm.close()

        # ---- ③ 流量觀測：訪客那一頁的統計送出去 → Worker 有 pv:articles；管理區「精選文章」分頁有數字、列得出被讀的文章
        u0 = {r["k"]: r["n"] for r in json.loads(urllib.request.urlopen(api + "/__usage", timeout=3).read())}
        gp.evaluate("() => { location.hash = '#articles/know'; }"); gp.wait_for_timeout(400)
        gp.evaluate("() => TwAccount.flush && TwAccount.flush()"); gp.wait_for_timeout(1200)
        u1 = {r["k"]: r["n"] for r in json.loads(urllib.request.urlopen(api + "/__usage", timeout=3).read())}
        ok(f"{T}[流量] 訪客看過精選文章 → Worker 記到 pv:articles（{u1.get('pv:articles', 0)}）", u1.get("pv:articles", 0) >= 1, {k: v for k, v in u1.items() if k.startswith("pv:")})
        ad.evaluate("() => { location.hash = '#admin/traffic'; }")
        wait_until(ad, "() => !!document.querySelector('#trTabs [data-t=articles]')", 15000)
        em = ad.evaluate("() => { const t = document.querySelector('#trTabs [data-t=articles]'); return t ? [t.textContent, +((t.querySelector('em') || {}).textContent || '0').replace(/,/g, '')] : null; }")
        ok(f"{T}[流量] 管理區流量觀測有「精選文章」分頁、次數 > 0（{em}）", bool(em) and "精選文章" in em[0] and em[1] > 0, em)
        ad.click("#trTabs [data-t=articles]")
        wait_until(ad, "() => !!document.querySelector('#trSubs [data-sub=post]')", 6000)
        body = ad.inner_text("#trPageBody") if ad.locator("#trPageBody").count() else ""
        subs = ad.evaluate("() => [...document.querySelectorAll('#trSubs button')].map(b => b.textContent.replace(/\\s+/g, ''))")
        ok(f"{T}[流量] 「精選文章」分頁有子分頁（全部文章／比比快訊／比比產業鏈／比比知識／單篇文章）", len(subs) == 6 and any("單篇文章" in s for s in subs) and any("比比知識" in s for s in subs), subs)
        ok(f"{T}[流量] 「被點最多的文章」列得出剛剛讀過的那篇（標題）", "CoWoS" in body or "AI 伺服器" in body, body[:300])
        _art_shot(ad, "admin_traffic_1440")
        cg.close(); ca.close()
        ok(f"{T}：沒有 JS 錯誤", not errs, errs[:3])
    finally:
        dev.terminate()
        try:
            dev.wait(timeout=5)
        except Exception:  # noqa: BLE001
            dev.kill()


register("精選文章共通功能1016", lambda pg, b, base, code: t_art_parity_1016(b, base), after="精選文章分頁1016")
