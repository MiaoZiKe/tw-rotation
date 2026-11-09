# 驗收段落「側欄拖曳1110」（site/navdrag.js、admin.js 會員表欄位順序；後端 workers/account-api 的 /v1/nav/order、/v1/admin/ui）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、to_members()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-10：「這邊改動就固定不變」「側邊也是具備拖曳功能，都只有我可以更改」。
# 用本機真的 account-api（devserver.mjs）：管理者真的用滑鼠拖「資金流水」到「今日市場」上面、拖組內大項 → 重新整理（清掉本機快取）順序還在
#   → 一般會員看到同樣順序、拖不動、沒有還原列 → 手機抽屜（390）同順序 → 管理者「還原預設順序」→ 回預設。
#   舊後端（/v1/nav/order* 回 404）：不跳錯、不登出、預設順序；管理者拖了只留本機並標「尚未同步」。
#   會員表欄位順序：拖一欄 → 伺服器 /v1/admin/ui 有 memcols → 清掉 localStorage 重新整理仍在 → 欄位還原後伺服器也清。
# 截圖：環境變數 TW_ND_SHOT＝資料夾 → drag_1440.png、member_1440.png、drawer_390.png、cols_after_1440.png。
import json as _nd_json

_ND_CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST, GET, OPTIONS"}
_ND_INIT = "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}"
_ND_GRPS = "() => [...document.querySelectorAll('#tabs .l4grp')].filter(e => e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.g)"
_ND_VIEWS = "(g) => { const G = TwL4Nav.GROUPS.find(x => x.g === g); return G.views.map(v => document.querySelector('#tabs .tab[data-view=' + v + ']')).filter(e => e && e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.view); }"


def t_nav_drag_1110(b, base):
    T = "側欄拖曳1110"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shot = os.environ.get("TW_ND_SHOT")
    over = "window.TW_ACCOUNT_OVERRIDE = " + _nd_json.dumps({"api": api}) + ";"
    try:
        up = False
        for _ in range(100):
            try:
                up = _nd_json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api 起得來", up):
            return

        def ctx(W, extra="", old=False):
            mob = W <= 640
            c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
            c.add_init_script(over + _ND_INIT + extra)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            if old:   # 舊 Worker：沒有這兩個端點
                c.route(re.compile(r".*/v1/(nav/order(/put)?|admin/ui(/put)?)$"), lambda r: r.fulfill(status=204, headers=_ND_CORS, body="") if r.request.method == "OPTIONS"
                        else r.fulfill(status=404, content_type="application/json", headers=_ND_CORS, body='{"error":"not_found"}'))
            ctxs.append(c)
            pg = c.new_page()
            pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
            return c, pg

        def login(pg, who, h="#overview"):
            pg.goto(base + h, wait_until="domcontentloaded")
            a = pg.get_by_role("button", name="同意並繼續")
            if a.count() and a.first.is_visible():
                a.first.click(); pg.wait_for_timeout(300)
            wait_until(pg, "() => !!document.getElementById('acctBtn')", 8000)
            pg.click("#acctBtn")
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector(f"#as-{who}", timeout=8000)
            pop.click(f"#as-{who}")
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        acall = lambda pg, path, body={}: pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])  # noqa: E731
        ready = lambda pg: wait_until(pg, "() => !!document.querySelector('#tabs .l4grp[data-g=today]') && !!window.TwNavOrder", 15000)  # noqa: E731

        def drag(pg, a, z, steps=14):
            pg.mouse.move(*a); pg.mouse.down(); pg.mouse.move(a[0] + 4, a[1] + 8, steps=3); pg.mouse.move(z[0], z[1], steps=steps)

        def center(pg, sel, scroll=True):
            return pg.evaluate("([s, sc]) => { if (sc) document.querySelector(s).scrollIntoView({ block: 'center', behavior: 'instant' }); const r = document.querySelector(s).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r.top, r.bottom, r.left + 40]; }", [sel, scroll])

        # ---------- 管理者登入（1440）
        ca, andy = ctx(1440)
        ok(f"{T}：Andy 登入", login(andy, "andy"))
        andy.reload(wait_until="domcontentloaded"); ready(andy); andy.wait_for_timeout(800)
        tok = andy.evaluate("() => localStorage.getItem('tw.acct.tok')"); usr = andy.evaluate("() => localStorage.getItem('tw.acct.user')")
        g0 = andy.evaluate(_ND_GRPS)
        ok(f"{T}：預設組順序＝今日市場在最上面（{g0}）", g0[:2] == ["today", "money"], g0)
        ok(f"{T}：管理者看得到「拖曳可調整順序」列，沒排過時「還原預設順序」是藏著的", andy.is_visible("#ndBar .ndh") and not andy.is_visible("#ndBar .ndr"))
        srv0 = acall(andy, "/v1/nav/order")
        ok(f"{T}：伺服器沒存過 → order 為 null", srv0 and srv0.get("_s") == 200 and srv0.get("order") is None, srv0)

        # 拖組：資金流水 → 今日市場上面
        gm = center(andy, ".l4grp[data-g=money]"); gt = center(andy, ".l4grp[data-g=today]", False)
        drag(andy, gm[:2], (gt[4], gt[2] + 3))
        line = andy.evaluate("() => { const l = document.querySelector('.nd-line'), g = document.querySelector('.nd-ghost'); return [!!l && l.getBoundingClientRect().width > 40, g ? g.textContent : '']; }")
        ok(f"{T}：拖曳中有落點線與提示標籤「移動『資金流水』」", line[0] and "資金流水" in line[1], line)
        if shot:
            Path(shot).mkdir(parents=True, exist_ok=True)
            andy.screenshot(path=str(Path(shot) / "drag_1440.png"))
        andy.mouse.up(); andy.wait_for_timeout(500)
        g1 = andy.evaluate(_ND_GRPS)
        ok(f"{T}：放開後「資金流水」移到最上面、其餘組順序不變（{g1}）", g1[0] == "money" and g1[1] == "today", g1)
        ok(f"{T}：拖曳沒有變成點擊（沒換頁、網址仍是 #overview）", andy.evaluate("() => location.hash") == "#overview")
        ok(f"{T}：「還原預設順序」出現", andy.is_visible("#ndBar .ndr"))
        # 不准跨組：把「總覽」拖到「資金流水」那組的區域 → 仍留在今日市場
        a = center(andy, "#tabs .tab[data-view=overview]"); z = center(andy, "#tabs .tab[data-view=flow]", False)
        drag(andy, a[:2], (z[4], z[2] + 3)); andy.mouse.up(); andy.wait_for_timeout(400)
        ok(f"{T}：不能拖到別的組底下（總覽仍在今日市場）", "overview" in andy.evaluate("() => TwL4Nav.GROUPS.find(x => x.g === 'today').views") and "overview" not in andy.evaluate("() => TwL4Nav.GROUPS.find(x => x.g === 'money').views"))
        # 拖大項：同組內「財經日曆」→「總覽」上面
        v0 = andy.evaluate(_ND_VIEWS, "today")
        a = center(andy, "#tabs .tab[data-view=earnings]"); z = center(andy, "#tabs .tab[data-view=overview]", False)
        drag(andy, a[:2], (z[4], z[2] + 3)); andy.mouse.up(); andy.wait_for_timeout(500)
        v1 = andy.evaluate(_ND_VIEWS, "today")
        ok(f"{T}：組內拖大項：財經日曆排到總覽前面（{v0}→{v1}）", v1[0] == "earnings" and sorted(v0) == sorted(v1), [v0, v1])
        # 子項：找一組同母項、看得到的兩個子項
        sp = andy.evaluate("() => { const by = {}; document.querySelectorAll('#tabs .l4subtab[data-l4sub]').forEach(e => { if (e.getClientRects().length) (by[e.dataset.parent] = by[e.dataset.parent] || []).push(e.dataset.l4sub); }); const p = Object.keys(by).find(k => by[k].length >= 2); return p ? [p, by[p]] : null; }")
        if ok(f"{T}：側欄有可見的子項可以測試", bool(sp), sp):
            order0 = andy.evaluate("(p) => [...document.querySelectorAll('#tabs .l4subtab[data-parent=' + p + ']')].filter(e => e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.l4sub)", sp[0])
            a = center(andy, f"#tabs .l4subtab[data-l4sub={order0[-1]}]"); z = center(andy, f"#tabs .l4subtab[data-l4sub={order0[0]}]", False)
            drag(andy, a[:2], (z[4], z[2] + 2)); andy.mouse.up(); andy.wait_for_timeout(500)
            order1 = andy.evaluate("(p) => [...document.querySelectorAll('#tabs .l4subtab[data-parent=' + p + ']')].filter(e => e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.l4sub)", sp[0])
            ok(f"{T}：拖子項：最後一個排到最前面（{order0[:3]}→{order1[:3]}）", order1[0] == order0[-1] and len(order1) == len(order0), [order0, order1])
        # 管理區子項
        adm0 = andy.evaluate("() => [...document.querySelectorAll('#tabs .l4subtab[data-parent=admin]')].filter(e => e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.adm)")
        if adm0 and len(adm0) >= 2:
            a = center(andy, f"#tabs .l4subtab[data-adm={adm0[1]}]"); z = center(andy, f"#tabs .l4subtab[data-adm={adm0[0]}]", False); a = center(andy, f"#tabs .l4subtab[data-adm={adm0[1]}]"); z = center(andy, f"#tabs .l4subtab[data-adm={adm0[0]}]", False)
            drag(andy, a[:2], (z[4], z[2] + 2)); andy.mouse.up(); andy.wait_for_timeout(500)
            adm1 = andy.evaluate("() => [...document.querySelectorAll('#tabs .l4subtab[data-parent=admin]')].filter(e => e.getClientRects().length).sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top).map(e => e.dataset.adm)")
            ok(f"{T}：拖管理區子項：第二個排到最前面", adm1[0] == adm0[1] and adm1[1] == adm0[0], [adm0, adm1])
        srv = acall(andy, "/v1/nav/order")
        o = (srv or {}).get("order") or {}
        ok(f"{T}：伺服器存到了（g 以 money 開頭、今日市場大項順序有存）", (o.get("g") or [None])[0] == "money" and (o.get("v") or {}).get("today", [None])[0] == "earnings", o)
        ok(f"{T}：瀏覽器標記為已同步（沒有「尚未同步」）", not andy.evaluate("() => TwNavOrder.unsynced()"))

        # 重新整理（清掉本機快取）→ 仍在
        andy.evaluate("() => localStorage.removeItem('tw.nav.ord')")
        andy.reload(wait_until="domcontentloaded"); ready(andy); andy.wait_for_timeout(1200)
        g2 = andy.evaluate(_ND_GRPS)
        ok(f"{T}：清掉本機快取重新整理 → 順序從伺服器回來（{g2}）", g2[0] == "money" and andy.evaluate(_ND_VIEWS, "today")[0] == "earnings", g2)

        # ---------- 一般會員
        cb, bob = ctx(1440)
        ok(f"{T}：Bob 登入", login(bob, "bob"))
        bob.reload(wait_until="domcontentloaded"); ready(bob); bob.wait_for_timeout(1200)
        btok = bob.evaluate("() => localStorage.getItem('tw.acct.tok')"); busr = bob.evaluate("() => localStorage.getItem('tw.acct.user')")
        gb = bob.evaluate(_ND_GRPS)
        ok(f"{T}：一般會員看到站主排好的順序（{gb}）", gb[0] == "money" and bob.evaluate(_ND_VIEWS, "today")[0] == "earnings", gb)
        ok(f"{T}：一般會員沒有拖曳列、側欄不是可拖的游標", bob.locator("#ndBar").count() == 0 and bob.evaluate("() => !document.documentElement.classList.contains('nd-adm')"))
        gm = center(bob, ".l4grp[data-g=money]"); gt = center(bob, ".l4grp[data-g=today]", False)
        drag(bob, gm[:2], (gt[4], gt[3] - 2)); no_line = bob.evaluate("() => !document.querySelector('.nd-line')"); bob.mouse.up(); bob.wait_for_timeout(400)
        gb2 = bob.evaluate(_ND_GRPS)
        ok(f"{T}：一般會員拖不動（順序沒變、沒有落點線、伺服器順序沒變）", no_line and gb2 == gb and (acall(bob, "/v1/nav/order") or {}).get("order", {}).get("g", [None])[0] == "money", [gb, gb2])
        put = acall(bob, "/v1/nav/order/put", {"order": None})
        ok(f"{T}：一般會員直接打 API 寫入被擋（403）", put and put.get("_s") == 403, put)
        if shot:
            bob.screenshot(path=str(Path(shot) / "member_1440.png"))

        # ---------- 手機抽屜（390）同順序
        cm, mob = ctx(390, "try{localStorage.setItem('tw.acct.tok'," + _nd_json.dumps(btok) + ");localStorage.setItem('tw.acct.user'," + _nd_json.dumps(busr) + ")}catch(e){}")
        mob.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(mob, "() => !!document.getElementById('m4Burger') && !!window.TwNavOrder", 15000); mob.wait_for_timeout(1500)
        mob.click("#m4Burger"); wait_until(mob, "() => document.querySelectorAll('#m4Drawer .m4grp[data-g]').length >= 3", 6000)
        mg = mob.evaluate("() => [...document.querySelectorAll('#m4Drawer .m4grp[data-g]')].map(e => e.dataset.g)")
        ok(f"{T}（390）手機抽屜的組順序＝站主排好的（{mg}）", mg[:2] == ["money", "today"], mg)
        ok(f"{T}（390）手機沒有拖曳列", mob.locator("#ndBar").count() == 0 or not mob.is_visible("#ndBar"))
        if shot:
            mob.screenshot(path=str(Path(shot) / "drawer_390.png"))
        cm.close()

        # ---------- 還原預設
        andy.click("#ndBar .ndr"); andy.wait_for_timeout(700)
        g3 = andy.evaluate(_ND_GRPS)
        ok(f"{T}：按「還原預設順序」→ 回到今日市場在上（{g3}）、按鈕又藏起來", g3[:2] == ["today", "money"] and andy.evaluate(_ND_VIEWS, "today")[0] == "overview" and not andy.is_visible("#ndBar .ndr"), g3)
        ok(f"{T}：還原後伺服器 order 為 null", (acall(andy, "/v1/nav/order") or {}).get("order") is None)
        bob.reload(wait_until="domcontentloaded"); ready(bob); bob.wait_for_timeout(1200)
        ok(f"{T}：一般會員重新整理也回預設", bob.evaluate(_ND_GRPS)[:2] == ["today", "money"])

        # ---------- 舊後端（404）
        co, old = ctx(1440, "try{localStorage.setItem('tw.acct.tok'," + _nd_json.dumps(tok) + ");localStorage.setItem('tw.acct.user'," + _nd_json.dumps(usr) + ")}catch(e){}", old=True)
        old.goto(base + "#overview", wait_until="domcontentloaded"); ready(old); old.wait_for_timeout(1500)
        ok(f"{T}：舊後端（404）→ 預設順序、沒登出", old.evaluate(_ND_GRPS)[:2] == ["today", "money"] and old.evaluate("() => !!TwAccount.user()"))
        gm = center(old, ".l4grp[data-g=money]"); gt = center(old, ".l4grp[data-g=today]", False)
        drag(old, gm[:2], (gt[4], gt[2] + 3)); old.mouse.up(); old.wait_for_timeout(700)
        ok(f"{T}：舊後端時管理者仍可排（只留本機）並標「尚未同步」、不跳錯", old.evaluate(_ND_GRPS)[0] == "money" and "尚未同步" in old.inner_text("#ndBar") and old.evaluate("() => !!TwAccount.user()"))
        co.close()

        # ---------- 會員表欄位順序（存伺服器）
        andy.goto(base + "#admin/perm", wait_until="domcontentloaded")
        try:
            to_members(andy, None)
        except Exception:  # noqa: BLE001
            pass
        has_tbl = wait_until(andy, "() => !!document.querySelector('#ptTable thead th[data-colk=plan]')", 12000)
        if ok(f"{T}：會員表出得來", has_tbl):
            HDR = "() => [...document.querySelectorAll('#ptTable thead th')].map(t => t.dataset.colk || 'email')"
            h0 = andy.evaluate(HDR)
            a = center(andy, "#ptTable th[data-colk=created]"); z = center(andy, "#ptTable th[data-colk=plan]", False)
            andy.mouse.move(a[0], a[1]); andy.mouse.down(); andy.mouse.move(a[0] - 30, a[1], steps=3); andy.mouse.move(z[4] - 32, z[1], steps=12); andy.mouse.up(); andy.wait_for_timeout(700)
            h1 = andy.evaluate(HDR)
            ok(f"{T}：拖「加入日」到「方案」前面（{h1[:4]}）", h1.index("created") < h1.index("plan") and h1[0] == "email", h1)
            ui = acall(andy, "/v1/admin/ui")
            mc = ((ui or {}).get("ui") or {}).get("memcols")
            ok(f"{T}：伺服器 /v1/admin/ui 存到 memcols", isinstance(mc, list) and mc and mc.index("created") < mc.index("plan"), ui)
            andy.evaluate("() => { localStorage.removeItem('tw.adm.memCols'); }")
            andy.reload(wait_until="domcontentloaded"); wait_until(andy, "() => !!window.TwAccount && !!TwAccount.user()", 12000)
            andy.evaluate("() => { location.hash = '#overview'; }"); andy.wait_for_timeout(600)
            try:
                to_members(andy, None)
            except Exception as e:  # noqa: BLE001
                pass
            wait_until(andy, "() => !!document.querySelector('#ptTable thead th[data-colk=plan]')", 12000)
            wait_until(andy, "() => { const h = [...document.querySelectorAll('#ptTable thead th')].map(t => t.dataset.colk || 'email'); return h.indexOf('created') < h.indexOf('plan'); }", 6000)
            h2 = andy.evaluate(HDR)
            ok(f"{T}：清掉 localStorage 重新整理 → 欄位順序仍在（從伺服器回來）", h2.index("created") < h2.index("plan"), h2)
            if shot:
                andy.evaluate("() => document.querySelector('#ptTable').scrollIntoView({ block: 'start', behavior: 'instant' })"); andy.wait_for_timeout(200)
                andy.screenshot(path=str(Path(shot) / "cols_after_1440.png"))
            # 欄位還原
            if andy.is_enabled("#pmColReset"):
                andy.click("#pmColReset"); andy.wait_for_timeout(700)
            h3 = andy.evaluate(HDR)
            ok(f"{T}：「欄位還原」→ 回預設順序、伺服器也清掉", h3 == h0 and not (((acall(andy, "/v1/admin/ui") or {}).get("ui") or {}).get("memcols")), [h3[:4], h0[:4]])
            bobui = acall(bob, "/v1/admin/ui")
            ok(f"{T}：一般會員讀不到管理區設定（403）", bobui and bobui.get("_s") == 403, bobui)
        ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("側欄拖曳1110", lambda pg, b, base, code: t_nav_drag_1110(b, base))
