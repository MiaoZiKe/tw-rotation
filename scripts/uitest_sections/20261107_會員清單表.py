# 驗收段落「會員清單表1107」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 會員清單表1107
# Andy 11-07 四項＋追加排版：
#   1. 「最常用的功能 Top3」與「功能使用排行」不准出現內部代號（fn.land、sub.sankey…），對不到顯示「其他」、滑過看代號
#   2. 「方案」欄可點 → 小選單 → 確認 → 假 Worker 收到正確請求 → 該列顯示新方案；體驗選項後端沒更新時停用寫「需要更新後端」
#   3. 測試帳標籤縮成小灰字「測試」、排序時永遠排最底
#   4. 欄位可拖曳換位置（存 localStorage、重新整理還在、「欄位還原」復原；「會員」固定第一欄）
#   5. 1440／1280／1024：整頁不橫捲、表格自己捲、第一欄固定、列高一致、字級一致、單行不重疊
# 假 Worker：用 Playwright 攔截 /v1/admin/perm/*、members、members/stats、plans、grants 的請求（登入仍走本機 devserver），
# 全部是假 email（example.com），不含任何真實會員。TW_MEMTBL_SHOT=<資料夾> 會順手截圖（TW_MEMTBL_TAG 決定檔名前綴）。

_MT_CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST, GET, OPTIONS"}


def _mt_top(pg):
    """把「搜尋列」捲到畫面最上面再截圖（站內捲動是平滑的，要先關掉動畫＋等一下）。"""
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; document.querySelectorAll('*').forEach(e => { if (e.scrollTop) e.style.scrollBehavior = 'auto'; }); document.querySelector('#pmSearch').scrollIntoView({block: 'start', behavior: 'instant'}); }")
    pg.wait_for_timeout(500)


def _mt_state(issue_ok=True):
    now = int(time.time() * 1000)
    day = 86400000
    P = [
        # email, 名字, plan, expires, seen(小時前), created(天前), topFeat, topStock, views, 測試帳?
        ("alice.chen@example.com", "陳小美", "plus", now + 20 * day, 2, 40, [["fn.land", 14], ["sub.sankey", 9], ["tab.revenue", 5]], [["2330", 18], ["2317", 7], ["2454", 3]], 420, False),
        ("bob.lin@example.com", "林大雄", "pro", 0, 5, 90, [["sub.all", 31], ["sub.inst", 20], ["fx.land", 11]], [["2330", 40], ["3711", 12], ["2382", 9]], 880, False),
        ("a.very.long.email.address.for.layout.check@example.com", "名字很長很長的測試會員", "free", 0, 30, 12, [["sub.industry", 8], ["sub.post", 7], ["fn.pricing_view", 6]], [["2330", 5], ["6669", 4], ["3037", 2]], 150, False),
        ("carol@example.com", "", "free", 0, 50, 7, [["fx.pricing_view", 12], ["tab.inst", 5], ["kp.60m", 4]], [["2603", 9], ["2881", 5]], 95, False),
        ("dave@example.com", "戴夫", "free", 0, 72, 3, [["zz.mystery", 3]], [["2330", 1]], 12, False),
        ("erin@example.com", "艾琳", "free", 0, 9, 25, [["sub.rotation", 22], ["sub.updown", 4], ["play", 3]], [["2412", 6]], 60, False),
        ("frank@example.com", "", "free", 0, 100, 60, [], [], 0, False),
        ("grace.wu@example.com", "吳雅婷", "free", 0, 1, 5, [["sub.credit", 10], ["sub.fut", 8], ["sub.know", 6]], [["2308", 11], ["2330", 4]], 300, False),
        ("test1@example.com", "站主測試帳", "free", 0, 0, 100, [["fn.land", 99]], [["2330", 99]], 9999, True),
    ]
    rows, users, mem = {}, [], []
    for em, nm, plan, exp, sh, cd, tf, ts, vw, _t in P:
        if plan != "free" or exp:
            rows[em] = {"email": em, "plan": plan, "n": 0, "updated": now - day, "expires": exp}
        users.append({"name": nm, "email": em, "seen": now - sh * 3600000, "created": now - cd * day, "visits": max(0, vw // 12), "invited_count": 2 if nm == "陳小美" else 0, "invite_reward_days": 14 if nm == "陳小美" else 0})
        mem.append({"email": em, "onlineMs": vw * 90000, "online30": vw * 60000, "visits30": max(0, vw // 12), "days30": 5, "views30": vw, "topFeat": tf, "topStock": ts})
    return {"rows": rows, "users": users, "mem": mem, "puts": [], "issues": [], "issue_ok": issue_ok, "test": [p[0] for p in P if p[9]], "now": now}


def _mt_install(ctx, st):
    def jr(route, body, status=200):
        route.fulfill(status=status, content_type="application/json", headers=_MT_CORS, body=json.dumps(body))

    def wrap(fn):
        def h(route):
            if route.request.method == "OPTIONS":
                route.fulfill(status=204, headers=_MT_CORS, body="")
                return
            try:
                b = json.loads(route.request.post_data or "{}")
            except Exception:  # noqa: BLE001
                b = {}
            fn(route, b)
        return h

    def perm_list(route, b):
        jr(route, {"rows": list(st["rows"].values()), "users": st["users"], "now": st["now"]})

    def perm_get(route, b):
        r = st["rows"].get(b.get("email"))
        jr(route, {"email": b.get("email"), "set": bool(r), "plan": r["plan"] if r else "free", "over": {}, "expires": (r or {}).get("expires", 0)})

    def perm_put(route, b):
        st["puts"].append(b)
        r = {"email": b["email"], "plan": b["plan"], "n": 0, "updated": st["now"], "expires": b.get("expires") or 0}
        st["rows"][b["email"]] = r
        jr(route, {"email": b["email"], "plan": b["plan"], "expires": r["expires"], "feats": {}})

    def members(route, b):
        jr(route, {"members": st["mem"]})

    def mstats(route, b):
        to = b.get("to") or time.strftime("%Y-%m-%d")
        days = [{"day": time.strftime("%Y-%m-%d", time.gmtime(time.time() - (29 - i) * 86400)), "n": 3 + i % 5, "visits": 8 + i % 7, "pv": 50 + i} for i in range(30)]
        jr(route, {"n": 9, "scope": "all", "from": b.get("from"), "to": to, "bin": "day", "keepDays": 90, "active7": 6, "active": 8, "visits": 240, "ms": 3600000 * 6, "pv": 1800, "joined": 3,
                   "featTotal": 400, "stockTotal": 90, "days": days,
                   "feats": [["fn.land", 120], ["fx.land", 90], ["sub.sankey", 60], ["sub.all", 40], ["sub.inst", 30], ["sub.industry", 20], ["sub.post", 12], ["fn.pricing_view", 9]], "stocks": [["2330", 40], ["2317", 12]]})

    def plans(route, b):
        mk = lambda i, n, bi: {"id": i, "name": n, "feats": {}, "builtin": bi, "price": 0 if bi else 299, "period": "month", "members": 0}  # noqa: E731
        jr(route, {"plans": [mk("guest", "訪客（未登入）", True), mk("free", "免費會員（預設）", True), mk("plus", "Plus", False), mk("pro", "Pro", False)]})

    def gdefs(route, b):
        jr(route, {"defs": [{"id": "welcome", "kind": "welcome", "name": "新會員體驗", "feats": {"stock.draw": 3}, "per": "total", "days": 14, "t0": None, "t1": None, "audience": "free", "on": True}], "max": 40})

    def issue(route, b):
        if not st["issue_ok"]:
            jr(route, {"error": "not_found"}, 404)
            return
        if b.get("probe"):
            jr(route, {"ok": True, "probe": True})
            return
        st["issues"].append(b)
        jr(route, {"ok": True, "email": b.get("email"), "gid": b.get("gid"), "end": st["now"] + 14 * 86400000})

    for pat, fn in (("**/v1/admin/perm/list", perm_list), ("**/v1/admin/perm/get", perm_get), ("**/v1/admin/perm/put", perm_put), ("**/v1/admin/members", members),
                    ("**/v1/admin/members/stats", mstats), ("**/v1/admin/plans/get", plans), ("**/v1/admin/grants/defs/list", gdefs), ("**/v1/admin/grants/issue", issue)):
        ctx.route(pat, wrap(fn))


def t_member_table_1107(b, base):
    T = "會員清單表1107"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shot_dir = os.environ.get("TW_MEMTBL_SHOT")
    tag = os.environ.get("TW_MEMTBL_TAG", "after")
    try:
        up = False
        for _ in range(100):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api 起得來", up):
            return

        def new_admin(st, w=1440):
            c = b.new_context(viewport={"width": w, "height": 900})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');"
                              "if(!sessionStorage.getItem('mt.init')){sessionStorage.setItem('mt.init','1');localStorage.setItem('tw.adm.testAcct'," + json.dumps(json.dumps(st["test"])) + ");}}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            _mt_install(c, st)
            ctxs.append(c)
            pg = c.new_page()
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.getElementById('acctBtn')", 8000)
            pg.click("#acctBtn")
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-andy", timeout=8000)
            pop.click("#as-andy")
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)
            to_members(pg, None)
            wait_until(pg, "() => !!document.querySelector('#ptTable tbody tr[data-email]')", 8000)
            return pg

        HDR = "() => [...document.querySelectorAll('#ptTable thead th')].map(t => t.textContent.replace(/[▲▼]/g,'').trim())"
        ORDER = "() => [...document.querySelectorAll('#ptTable tbody tr[data-email]')].map(r => r.dataset.email)"

        # ---------------- 1440：Top3 名稱、方案欄、測試帳、拖曳
        st = _mt_state(True)
        pg = new_admin(st)
        pg.wait_for_timeout(3800)
        if shot_dir:
            Path(shot_dir).mkdir(parents=True, exist_ok=True)
            _mt_top(pg)
            pg.screenshot(path=str(Path(shot_dir) / f"{tag}_1440.png"))
        if os.environ.get("TW_MEMTBL_ONLYSHOT"):      # 只拍「修改前」對照圖（舊版沒有新元素，後面的斷言不跑）
            for w in (1280, 1024):
                pw = new_admin(_mt_state(True), w); pw.wait_for_timeout(3800)
                _mt_top(pw)
                pw.screenshot(path=str(Path(shot_dir) / f"{tag}_{w}.png"))
            return
        feat = pg.evaluate("() => [...document.querySelectorAll('#ptTable td.c-feat .mcn')].map(e => e.textContent.trim())")
        bad = [x for x in feat if re.search(r"[A-Za-z]+\.[a-z_]+|^(fn|fx|sub)\b", x)]
        ok(f"{T}：Top3 沒有英文代號（共 {len(feat)} 個標籤）", feat and not bad, bad[:5])
        want = ["帶來源進站（來源）", "帶來源進站（功能）", "子頁：資金分流樹", "子頁：全部文章", "子頁：三大法人／族群×法人", "子頁：產業熱力圖", "子頁：單篇文章", "看訂閱方案（來源）", "看訂閱方案（功能）"]
        miss = [w for w in want if w not in feat]
        ok(f"{T}：代號都換成中文名（fn.land／fx.land／sub.sankey／sub.all／sub.inst／sub.industry／sub.post／fn.pricing_view／fx.pricing_view）", not miss, miss)
        ttl = pg.evaluate("() => { const r = document.querySelector(\"#ptTable tr[data-email='dave@example.com'] td.c-feat\"); return [r.innerText.trim(), (r.querySelector('.mchips')||{}).title || '']; }")
        ok(f"{T}：對不到的代號顯示「其他」、滑過才看得到原碼", ttl[0].startswith("其他") and "zz.mystery" in ttl[1], ttl)
        # 功能使用排行（上方統計）
        wait_until(pg, "() => !!document.querySelector('#msFeat .bl')", 8000)
        rank = pg.evaluate("() => [...document.querySelectorAll('#msFeat .bl')].map(e => e.textContent.trim())")
        ok(f"{T}：上方「功能使用排行」長條也是中文名（fn.land／fx.land…）", rank and not [x for x in rank if re.search(r"[A-Za-z]+\.[a-z_]+", x)] and "帶來源進站（來源）" in rank, rank)

        # 測試帳：小灰字、排最底
        def last_row():
            return pg.evaluate("() => { const r = [...document.querySelectorAll('#ptTable tbody tr[data-email]')]; return [r[r.length-1].dataset.email, r[r.length-1].classList.contains('tst')]; }")
        tb = pg.evaluate("() => { const e = document.querySelector('#ptTable tr.tst .tbadge'); const r = e.getBoundingClientRect(); const td = e.closest('td'); const nx = td.nextElementSibling.getBoundingClientRect(); return [e.textContent.trim(), Math.round(r.width), e.title, r.right <= td.getBoundingClientRect().right + 0.5, r.right <= nx.left + 0.5, getComputedStyle(e).color]; }")
        ok(f"{T}：測試帳標籤是小灰字「測試」（寬 {tb[1]}px），滑過顯示「不計入統計」，沒有壓到旁邊欄位", tb[0] == "測試" and tb[1] <= 48 and "不計入統計" in tb[2] and tb[3] and tb[4], tb)
        for col, dirn in (("views", "desc"), ("views", "asc"), ("email", "asc"), ("created", "desc"), ("plan", "asc")):
            # 點表頭：第一次點 → 預設方向；再點 → 反向；逐個排一遍看測試帳是否都在最底
            pg.click(f"#ptTable th[data-sort='{col}']")
            pg.wait_for_timeout(120)
            lr = last_row()
            if not lr[1]:
                pg.click(f"#ptTable th[data-sort='{col}']"); pg.wait_for_timeout(120); lr = last_row()
            ok(f"{T}：依「{col}」排序（兩個方向）測試帳都在最底", lr[1] and lr[0] == "test1@example.com", lr)
        pg.click("#ptTable th[data-sort='views']"); pg.wait_for_timeout(100)
        d1 = last_row()
        pg.click("#ptTable th[data-sort='views']"); pg.wait_for_timeout(100)
        d2 = last_row()
        ok(f"{T}：views 升冪、降冪切換後測試帳都還是最後一列", d1[0] == "test1@example.com" and d2[0] == "test1@example.com", [d1, d2])

        # 方案欄：點 → 選單 → 選 Plus → 確認
        pg.click("#ptTable th[data-sort='email']"); pg.wait_for_timeout(100)
        pg.click("button[data-plan-btn='carol@example.com']")
        wait_until(pg, "() => !!document.getElementById('plMenu')", 3000)
        items = pg.evaluate("() => [...document.querySelectorAll('#plMenu button')].map(b => [b.textContent.trim(), b.disabled])")
        names = [i[0] for i in items]
        ok(f"{T}：選單有 註冊會員（免費）／Plus／Pro／體驗方案", any("註冊會員（免費）" in n for n in names) and any(n.startswith("Plus") for n in names) and any(n.startswith("Pro") for n in names) and any(n.startswith("體驗：新會員體驗") for n in names), names)
        ok(f"{T}：點方案欄不會同時展開那一列", pg.evaluate("() => !document.querySelector(\"#ptTable tr.pmdet[data-for='carol@example.com']\")"))
        if shot_dir:
            pg.screenshot(path=str(Path(shot_dir) / f"{tag}_1440_menu.png"))
        pg.click("#plMenu button:has-text('Plus')")
        wait_until(pg, "() => !!document.getElementById('plGo')", 3000)
        n_before = len(st["puts"])
        ok(f"{T}：選完先跳確認，這時還沒送出請求", n_before == 0)
        pg.select_option("#plDays", "30")
        if shot_dir:
            pg.screenshot(path=str(Path(shot_dir) / f"{tag}_1440_confirm.png"))
        pg.click("#plGo")
        wait_until(pg, "() => (document.querySelector(\"#ptTable tr[data-email='carol@example.com'] .plbtn span\")||{}).textContent === 'Plus'", 5000)
        put = st["puts"][-1] if st["puts"] else {}
        exp_ok = abs((put.get("expires") or 0) - (st["now"] + 30 * 86400000)) < 3 * 86400000
        ok(f"{T}：假 Worker 收到 perm/put（carol → plus、30 天後到期）", put.get("email") == "carol@example.com" and put.get("plan") == "plus" and exp_ok, put)
        ok(f"{T}：確認後該列立即顯示 Plus", pg.evaluate("() => document.querySelector(\"#ptTable tr[data-email='carol@example.com'] .plbtn span\").textContent") == "Plus")
        # 取消不送
        pg.click("button[data-plan-btn='erin@example.com']"); wait_until(pg, "() => !!document.getElementById('plMenu')", 3000)
        pg.click("#plMenu button:has-text('Pro')"); wait_until(pg, "() => !!document.getElementById('plGo')", 3000)
        pg.click("#plGo >> xpath=../button[@data-close]"); pg.wait_for_timeout(200)
        ok(f"{T}：確認視窗按「取消」不會送出請求", len(st["puts"]) == 1 and pg.evaluate("() => document.querySelector(\"#ptTable tr[data-email='erin@example.com'] .plbtn span\").textContent") == "註冊會員")
        # 改回註冊會員
        pg.click("button[data-plan-btn='alice.chen@example.com']"); wait_until(pg, "() => !!document.getElementById('plMenu')", 3000)
        pg.click("#plMenu button:has-text('註冊會員（免費）')"); wait_until(pg, "() => !!document.getElementById('plGo')", 3000)
        pg.click("#plGo")
        wait_until(pg, "() => document.querySelector(\"#ptTable tr[data-email='alice.chen@example.com'] .plbtn span\").textContent === '註冊會員'", 5000)
        ok(f"{T}：Plus 改回註冊會員 → perm/put plan=free，該列更新", st["puts"][-1].get("plan") == "free" and st["puts"][-1].get("email") == "alice.chen@example.com", st["puts"][-1])
        # 體驗
        pg.click("button[data-plan-btn='dave@example.com']"); wait_until(pg, "() => !!document.getElementById('plMenu')", 3000)
        wait_until(pg, "() => { const b = [...document.querySelectorAll('#plMenu button')].find(x => x.textContent.includes('體驗：')); return b && !b.disabled; }", 3000)
        pg.click("#plMenu button:has-text('體驗：新會員體驗')"); wait_until(pg, "() => !!document.getElementById('plGo')", 3000)
        pg.click("#plGo"); wait_until(pg, "() => true", 100); pg.wait_for_timeout(500)
        ok(f"{T}：發放體驗 → 假 Worker 收到 grants/issue（dave、welcome）", st["issues"] and st["issues"][-1].get("email") == "dave@example.com" and st["issues"][-1].get("gid") == "welcome", st["issues"])

        # 拖曳換欄
        base_hdr = pg.evaluate(HDR)
        ok(f"{T}：預設表頭順序以「會員」開頭", base_hdr[0] == "會員" and "方案" in base_hdr and "觀看次數" in base_hdr, base_hdr)
        ok(f"{T}：沒動過順序時「欄位還原」是停用的", pg.evaluate("() => document.getElementById('pmColReset').disabled"))
        r_from = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-colk='online']\").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        r_to = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-colk='plan']\").getBoundingClientRect(); return [r.left + 8, r.top + r.height/2]; }")
        pg.mouse.move(*r_from); pg.mouse.down(); pg.mouse.move(r_from[0] - 30, r_from[1], steps=3); pg.mouse.move(r_to[0], r_to[1], steps=12)
        drop = pg.evaluate("() => { const d = document.querySelector('.memdrop'); const g = document.querySelector('.memghost'); const pl = document.querySelector(\"#ptTable th[data-colk='plan']\").getBoundingClientRect(); return [!!d && d.getBoundingClientRect().height > 40, !!g, g ? g.textContent : '', d ? Math.abs(d.getBoundingClientRect().left + 1.5 - pl.left) : 999]; }")
        if shot_dir:
            pg.screenshot(path=str(Path(shot_dir) / f"{tag}_1440_drag.png"))
        pg.mouse.up(); pg.wait_for_timeout(250)
        ok(f"{T}：拖動中有落點直線與提示標籤", drop[0] and drop[1] and "累計在線" in drop[2] and drop[3] <= 3, drop)
        h2 = pg.evaluate(HDR)
        ok(f"{T}：放開後「累計在線」移到「方案」前面，「會員」仍在第一欄", h2[0] == "會員" and h2.index("累計在線") == h2.index("方案") - 1, h2)
        ok(f"{T}：沒有因為拖曳而變更排序方向（表頭沒被當成點擊）", pg.evaluate("() => document.querySelector(\"#ptTable th[data-sort='online']\").getAttribute('aria-sort')") == "none")
        cell_ok = pg.evaluate("() => { const r = document.querySelector('#ptTable tbody tr[data-email]'); return r.children[1].classList.contains('c-on'); }")
        ok(f"{T}：內容欄跟著表頭一起換位", cell_ok)
        saved = pg.evaluate("() => localStorage.getItem('tw.adm.memCols')")
        ok(f"{T}：順序存進 localStorage", bool(saved) and "online" in saved, saved)
        # 會員欄不能被拖走
        e_from = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-sort='email']\").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        e_to = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-colk='created']\").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        pg.mouse.move(*e_from); pg.mouse.down(); pg.mouse.move(e_to[0], e_to[1], steps=10); pg.mouse.up(); pg.wait_for_timeout(200)
        ok(f"{T}：按住「會員」表頭拖不動（固定第一欄）", pg.evaluate(HDR)[0] == "會員" and pg.evaluate(HDR) == h2, pg.evaluate(HDR))
        # 其他欄拖到「會員」左邊 → 只能排在它後面
        a_from = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-colk='seen']\").getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]; }")
        a_to = pg.evaluate("() => { const r = document.querySelector(\"#ptTable th[data-sort='email']\").getBoundingClientRect(); return [r.left + 6, r.top + r.height/2]; }")
        pg.mouse.move(*a_from); pg.mouse.down(); pg.mouse.move(a_from[0] - 40, a_from[1], steps=3); pg.mouse.move(a_to[0], a_to[1], steps=14); pg.mouse.up(); pg.wait_for_timeout(250)
        h3 = pg.evaluate(HDR)
        ok(f"{T}：把「最後上線」拖到「會員」左邊 → 只會排在會員後面", h3[0] == "會員" and h3[1] == "最後上線", h3)
        # 重新整理後順序還在
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        to_members(pg, None)
        wait_until(pg, "() => !!document.querySelector('#ptTable tbody tr[data-email]')", 8000)
        h4 = pg.evaluate(HDR)
        ok(f"{T}：重新整理後欄位順序還在", h4 == h3, [h3[:4], h4[:4]])
        ok(f"{T}：順序變過之後「欄位還原」可按", not pg.evaluate("() => document.getElementById('pmColReset').disabled"))
        pg.click("#pmColReset"); pg.wait_for_timeout(250)
        h5 = pg.evaluate(HDR)
        ok(f"{T}：按「欄位還原」回到預設順序、localStorage 清掉", h5 == base_hdr and pg.evaluate("() => localStorage.getItem('tw.adm.memCols')") is None, [h5[:4], base_hdr[:4]])

        # 版面逐欄檢查（1440／1280／1024）
        MEASURE = r"""() => {
          const sc = document.querySelector('#ptTable').closest('.memscroll'), tb = document.querySelector('#ptTable');
          const ths = [...tb.querySelectorAll('thead th')];
          const rows = [...tb.querySelectorAll('tbody tr[data-email]')];
          const cols = ths.map((th, i) => {
            const tds = rows.map(r => r.children[i]);
            const trunc = tds.filter(td => td.scrollWidth > td.clientWidth + 1).length;
            const inner = tds.filter(td => { const tr = td.getBoundingClientRect(); return [...td.querySelectorAll('*')].some(c => { const cr = c.getBoundingClientRect(); return cr.width > 0 && cr.right > tr.right + 1; }); }).length;
            return { name: th.textContent.replace(/[▲▼]/g,'').trim(), w: Math.round(th.getBoundingClientRect().width), thTrunc: th.scrollWidth > th.clientWidth + 1, trunc, inner, hasTitle: tds.every(td => !(td.scrollWidth > td.clientWidth + 1) || !!td.querySelector('[title]') || !!td.title || !!td.querySelector('b[title]')) };
          });
          const hs = rows.map(r => Math.round(r.getBoundingClientRect().height));
          const fs = { th: [...new Set(ths.map(t => getComputedStyle(t).fontSize))], td: [...new Set(rows.flatMap(r => [...r.children].map(td => getComputedStyle(td).fontSize)))], chip: [...new Set([...tb.querySelectorAll('.mchip')].map(c => getComputedStyle(c).fontSize))] };
          const vc = rows.map(r => [...r.children].every(td => { const v = getComputedStyle(td).verticalAlign; return v === 'middle'; })).every(Boolean);
          const num = [...tb.querySelectorAll('td.num')].every(td => getComputedStyle(td).textAlign === 'right' && /mono|Mono|Consolas|Menlo/.test(getComputedStyle(td).fontFamily));
          const first = rows[0].children[0].getBoundingClientRect();
          sc.scrollLeft = 120; const f2 = rows[0].children[0].getBoundingClientRect(); const s2 = sc.getBoundingClientRect(); const moved = sc.scrollLeft; sc.scrollLeft = 0;
          return { page: [document.documentElement.scrollWidth, window.innerWidth], scroll: [sc.scrollWidth, sc.clientWidth], cols, hs: [...new Set(hs)], fs, vc, num, sticky: [Math.round(f2.left - s2.left), moved] };
        }"""
        for w in (1440, 1280, 1024):
            pgw = new_admin(_mt_state(True), w)
            pgw.wait_for_timeout(3800)
            if shot_dir and w != 1440:
                _mt_top(pgw)
                pgw.screenshot(path=str(Path(shot_dir) / f"{tag}_{w}.png"))
            m = pgw.evaluate(MEASURE)
            if shot_dir and w == 1440:
                _mt_top(pgw)
                pgw.screenshot(path=str(Path(shot_dir) / f"{tag}_1440_clean.png"))
            if shot_dir:
                pgw.evaluate("() => { const s = document.querySelector('#ptTable').closest('.memscroll'); s.scrollLeft = 99999; }")
                pgw.screenshot(path=str(Path(shot_dir) / f"{tag}_{w}_scrolled.png"))
            print(f"    [{w}] 頁寬 {m['page']}、表格捲動區 {m['scroll']}、列高 {m['hs']}、字級 {m['fs']}、第一欄固定位移 {m['sticky']}")
            for c in m["cols"]:
                print(f"        {c['name']:<14} 寬 {c['w']:>4}px  表頭截斷 {c['thTrunc']}  內容被截 {c['trunc']} 列  超出格子 {c['inner']} 列  截斷處有滑過全文 {c['hasTitle']}")
            ok(f"{T}（{w}）：整頁沒有橫向捲軸", m["page"][0] <= m["page"][1], m["page"])
            ok(f"{T}（{w}）：只有表格自己能橫向捲（捲動區 {m['scroll']}），捲動時「會員」欄固定不動", m["scroll"][0] >= m["scroll"][1] and abs(m["sticky"][0]) <= 1 and (m["scroll"][0] == m["scroll"][1] or m["sticky"][1] > 0), m)
            ok(f"{T}（{w}）：列高一致、文字垂直置中", len(m["hs"]) == 1 and m["vc"], [m["hs"], m["vc"]])
            ok(f"{T}（{w}）：字級一致（表頭 12、內文 13、晶片 12）", m["fs"]["th"] == ["12px"] and m["fs"]["td"] == ["13px"] and m["fs"]["chip"] in (["12px"], []), m["fs"])
            ok(f"{T}（{w}）：數字欄靠右＋等寬數字", m["num"])
            ok(f"{T}（{w}）：表頭沒被截斷、沒有內容超出自己的格子", not [c["name"] for c in m["cols"] if c["thTrunc"] or c["inner"]], [(c["name"], c["thTrunc"], c["inner"]) for c in m["cols"] if c["thTrunc"] or c["inner"]])
            tr = [(c["name"], c["trunc"]) for c in m["cols"] if c["trunc"] and c["name"] not in ("會員", "最常用的功能 Top3", "最常看的股票 Top3")]
            ok(f"{T}（{w}）：除了會員與兩個 Top3，其他欄一個字都沒被截", not tr, tr)
            ok(f"{T}（{w}）：被截的格子（長 email、Top3）滑過看得到全文", all(c["hasTitle"] for c in m["cols"]), [c["name"] for c in m["cols"] if not c["hasTitle"]])

        # 手機 390：維持原樣（只留重點欄位、不開放拖曳、沒有欄位還原鈕）、整頁不橫捲
        pm = new_admin(_mt_state(True), 1440)
        pm.set_viewport_size({"width": 390, "height": 844})      # 手機版登入入口不同：登入後直接縮窗再重新整理
        pm.reload(wait_until="domcontentloaded")
        wait_until(pm, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        to_members(pm, None)
        wait_until(pm, "() => !!document.querySelector('#ptTable tbody tr[data-email]')", 8000)
        pm.wait_for_timeout(800)
        mm = pm.evaluate("() => { const th = [...document.querySelectorAll('#ptTable thead th')].filter(t => t.offsetParent).map(t => t.textContent.replace(/[▲▼]/g, '').trim()); return { th, page: [document.documentElement.scrollWidth, innerWidth], reset: getComputedStyle(document.getElementById('pmColReset').parentElement).display }; }")
        ok(f"{T}（390）：整頁沒有橫向捲軸、只留重點欄位、「欄位還原」不顯示", mm["page"][0] <= mm["page"][1] and mm["th"][0] == "會員" and len(mm["th"]) <= 5 and mm["reset"] == "none", mm)
        if shot_dir:
            _mt_top(pm)
            pm.screenshot(path=str(Path(shot_dir) / f"{tag}_390.png"))
        # 後端沒更新體驗端點：選項停用＋提示
        st2 = _mt_state(False)
        p2 = new_admin(st2)
        p2.click("button[data-plan-btn='carol@example.com']"); wait_until(p2, "() => !!document.getElementById('plMenu')", 3000)
        wait_until(p2, "() => { const b = [...document.querySelectorAll('#plMenu button')].find(x => x.textContent.includes('體驗：')); return b && b.textContent.includes('需要更新後端'); }", 4000)
        gb = p2.evaluate("() => { const b = [...document.querySelectorAll('#plMenu button')].find(x => x.textContent.includes('體驗：')); return [b.disabled, b.textContent.trim()]; }")
        ok(f"{T}：後端沒有 grants/issue → 體驗選項停用並寫「需要更新後端」", gb[0] and "需要更新後端" in gb[1], gb)
        ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("會員清單表1107", lambda pg, b, base, code: t_member_table_1107(b, base))
