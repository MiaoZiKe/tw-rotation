# 驗收段落「體驗發放同步1109」
# Andy 11-09：「這3個我明明給我體驗，但卻沒有同步資訊，請確認以及顯示體驗期限」。
# 根因：會員清單的「體驗到期」只用「加入時間＋活動天數」推算，從不讀伺服器實際發出去的體驗（grants）。
# 這段用假 Worker（沿用 20261107 的 _mt_state／_mt_install，之後註冊的路由覆蓋同名路徑）驗：
#   發放 → 該列到期日立刻換成新的、標「手動」、方案旁出現「體驗中」→ 展開看到體驗紀錄（名稱、起訖、已用次數）
#   → 重新整理後仍在（Worker 還沒帶 grants 欄位時靠瀏覽器記住；Worker 帶了就以伺服器為準）
#   → 發放失敗要顯示明確原因、列不變 → 重發給已有的人，確認框要先說「已發人數不會增加」。
# flake8: noqa


def _gi_install(ctx, st, srv_field):
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

    def gl(email):
        return st["grants"].setdefault(email, [])

    def issue(route, b):
        if b.get("probe"):
            jr(route, {"ok": True, "probe": True})
            return
        st["issues"].append(b)
        em = b.get("email")
        if em in st.get("fail", {}):
            jr(route, {"error": st["fail"][em]}, 400 if st["fail"][em] != "no_user" else 404)
            return
        end = st["now"] + 14 * 86400000
        g = [x for x in gl(em) if x["gid"] == b.get("gid")]
        if g:
            g[0].update(start=st["now"], end=end)
            st["hits"] = [h for h in st["hits"] if not (h["email"] == em and h["gid"] == b.get("gid"))]
        else:
            gl(em).append({"gid": b["gid"], "name": "新會員體驗", "kind": "welcome", "start": st["now"], "end": end, "active": True})
        jr(route, {"ok": True, "email": em, "gid": b["gid"], "name": "新會員體驗", "start": st["now"], "end": end})

    def guser(route, b):
        em = b.get("email")
        jr(route, {"email": em, "known": True, "grants": gl(em), "hits": [{"gid": h["gid"], "k": "stock.draw", "day": "2026-11-09", "key": "x"} for h in st["hits"] if h["email"] == em], "now": st["now"]})

    def members(route, b):
        ms = []
        for m in st["mem"]:
            m = dict(m)
            if srv_field:
                m["grants"] = [{"gid": g["gid"], "name": g["name"], "kind": g["kind"], "start": g["start"], "end": g["end"]} for g in gl(m["email"])]
            ms.append(m)
        jr(route, {"members": ms})

    def gdefs(route, b):
        n = sum(1 for v in st["grants"].values() for g in v if g["gid"] == "welcome")
        jr(route, {"defs": [{"id": "welcome", "kind": "welcome", "name": "新會員體驗", "feats": {"stock.draw": 3}, "per": "total", "days": 14, "t0": None, "t1": None,
                             "audience": "free", "on": True, "issued": n, "used": len(st["hits"])}], "max": 40})

    for pat, fn in (("**/v1/admin/grants/issue", issue), ("**/v1/admin/grants/user", guser), ("**/v1/admin/members", members), ("**/v1/admin/grants/defs/list", gdefs)):
        ctx.route(pat, wrap(fn))


def t_grant_sync_1109(b, base):
    T = "體驗發放同步1109"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shot_dir = os.environ.get("TW_GI_SHOT")
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

        def new_admin(st, srv_field):
            c = b.new_context(viewport={"width": 1440, "height": 900})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');"
                              "if(!sessionStorage.getItem('mt.init')){sessionStorage.setItem('mt.init','1');localStorage.setItem('tw.adm.testAcct'," + json.dumps(json.dumps(st["test"])) + ");}}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            _mt_install(c, st)
            _gi_install(c, st, srv_field)
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

        WEL = "(em) => { const r = document.querySelector(`#ptTable tr[data-email='${em}']`); const w = r.querySelector('td.c-wel .wel'); return w ? [w.textContent.trim(), w.dataset.wel, w.title] : null; }"
        TAG = "(em) => !!document.querySelector(`#ptTable tr[data-email='${em}'] td.c-tpl .trialtag`)"
        DAY = lambda ms: time.strftime("%Y-%m-%d", time.gmtime(ms / 1000 + 8 * 3600))  # noqa: E731

        def issue_via_menu(pg, em, confirm=True):
            pg.click(f"button[data-plan-btn='{em}']")
            wait_until(pg, "() => !!document.getElementById('plMenu')", 3000)
            wait_until(pg, "() => { const b = [...document.querySelectorAll('#plMenu button')].find(x => x.textContent.includes('體驗：')); return b && !b.disabled; }", 3000)
            pg.click("#plMenu button:has-text('體驗：新會員體驗')")
            wait_until(pg, "() => !!document.getElementById('plGo')", 4000)

        for srv_field in (False, True):
            tag = "Worker 尚未帶 grants 欄位" if not srv_field else "Worker 已帶 grants 欄位"
            st = _mt_state(True)
            st.update(grants={}, hits=[], fail={})
            # 加入 dave 已經有一份自動發的體驗（註冊當天起算），用來驗「重發」
            dave_c = [u for u in st["users"] if u["email"] == "dave@example.com"][0]["created"]
            st["grants"]["dave@example.com"] = [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": dave_c, "end": dave_c + 14 * 86400000, "active": True}]
            st["hits"] = [{"email": "dave@example.com", "gid": "welcome"}]
            pg = new_admin(st, srv_field)
            pg.wait_for_timeout(1500)
            carol = "carol@example.com"
            before = pg.evaluate(WEL, carol)
            ok(f"{T}（{tag}）：發放前 carol 的體驗到期是舊的基本算法", before and before[1] == "base" and not pg.evaluate(TAG, carol), before)
            ok(f"{T}（{tag}）：已有自動體驗的 dave 若 Worker 有帶就標「自動」", True if not srv_field else pg.evaluate(WEL, "dave@example.com")[1] == "auto", pg.evaluate(WEL, "dave@example.com"))

            # 發放 carol
            issue_via_menu(pg, carol)
            ok(f"{T}（{tag}）：新人發放確認框不出現「已經有這一份」", pg.evaluate("() => !document.querySelector('dialog, .tw-dialog, [role=dialog]') || !/已經有這一份/.test(document.body.innerText)"))
            pg.click("#plGo")
            wait_until(pg, f"() => {{ const w = document.querySelector(\"#ptTable tr[data-email='{carol}'] td.c-wel .wel\"); return w && w.dataset.wel === 'man'; }}", 6000)
            after = pg.evaluate(WEL, carol)
            want = DAY(st["now"] + 14 * 86400000)
            ok(f"{T}（{tag}）：發放後 carol 體驗到期立刻變成 {want} 並標「手動」", after and after[0].startswith(want) and after[0].endswith("手動") and "手動發放" in after[2], after)
            ok(f"{T}（{tag}）：carol 方案旁出現「體驗中」小標", pg.evaluate(TAG, carol))
            ok(f"{T}（{tag}）：假 Worker 收到的是 carol／welcome", st["issues"] and st["issues"][-1].get("email") == carol and st["issues"][-1].get("gid") == "welcome", st["issues"])
            toast = pg.evaluate("() => (document.querySelector('#pmUndo') || {}).innerText || ''")
            ok(f"{T}（{tag}）：提示寫出到期日與「手動發放」", ("手動發放" in toast and want in toast), toast[-120:])
            # 展開 → 體驗紀錄
            wait_until(pg, f"() => !!document.querySelector(\"tr.pmdet[data-for='{carol}'] .grl li\")", 6000)
            li = pg.evaluate(f"() => document.querySelector(\"tr.pmdet[data-for='{carol}'] .grl li\").innerText")
            ok(f"{T}（{tag}）：展開明細列出體驗紀錄（名稱、起訖、手動發放、已用次數）", "新會員體驗" in li and want in li and "手動發放" in li and "已用 0 次" in li and "體驗中" in li, li)
            if shot_dir and srv_field:
                Path(shot_dir).mkdir(parents=True, exist_ok=True)
                _mt_top(pg)
                pg.screenshot(path=str(Path(shot_dir) / "after_1440.png"))
            # 「體驗額度」頁的已發人數：dave 1 + carol 1 = 2
            # 重新整理 → 仍在
            pg.reload(wait_until="domcontentloaded")
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)
            to_members(pg, None)
            wait_until(pg, "() => !!document.querySelector(\"#ptTable tr[data-email='carol@example.com'] td.c-wel .wel\")", 15000)
            pg.wait_for_timeout(1500)
            re_ = pg.evaluate(WEL, carol)
            ok(f"{T}（{tag}）：重新整理後 carol 的體驗到期仍是 {want}、標「手動」、「體驗中」還在", re_ and re_[0].startswith(want) and re_[1] == "man" and pg.evaluate(TAG, carol), re_)

            # 重發 dave：確認框要先說已經有、已發人數不增加
            issue_via_menu(pg, "dave@example.com")
            txt = pg.evaluate("() => document.body.innerText")
            ok(f"{T}（{tag}）：重發給已有的人，確認框說明「已發人數不會增加」", "已經有這一份" in txt and "不會增加" in txt)
            pg.click("#plGo")
            wait_until(pg, "() => { const w = document.querySelector(\"#ptTable tr[data-email='dave@example.com'] td.c-wel .wel\"); return w && w.dataset.wel === 'man'; }", 6000)
            dv = pg.evaluate(WEL, "dave@example.com")
            ok(f"{T}（{tag}）：重發後 dave 到期變成新日期 {want}", dv and dv[0].startswith(want), dv)
            ok(f"{T}（{tag}）：重發後 dave 的已用次數歸零（假 Worker 清掉）", not [h for h in st["hits"] if h["email"] == "dave@example.com"])

            # 失敗：沒登入過 → 明確原因、列不變
            st["fail"]["erin@example.com"] = "no_user"
            e0 = pg.evaluate(WEL, "erin@example.com")
            issue_via_menu(pg, "erin@example.com")
            pg.click("#plGo")
            wait_until(pg, "() => /沒有登入過|還沒登入過/.test((document.querySelector('#pmStat') || {}).textContent || '')", 5000)
            msg = pg.evaluate("() => document.querySelector('#pmStat').textContent")
            e1 = pg.evaluate(WEL, "erin@example.com")
            ok(f"{T}（{tag}）：發放失敗顯示明確原因、該列體驗到期不變、沒有「體驗中」", "發放體驗失敗" in msg and "還沒登入過" in msg and e0 == e1 and not pg.evaluate(TAG, "erin@example.com"), [msg, e0, e1])
            pg.close()
        ok(f"{T}：沒有 JS 例外", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("體驗發放同步1109", lambda pg, b, base, code: t_grant_sync_1109(b, base))
