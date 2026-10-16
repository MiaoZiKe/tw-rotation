# 驗收段落「防白嫖後端1016」—— 2026-10-16 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_free_port()、_acctm4_ctx()、ACCTM4_API… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 防白嫖後端1016（site/quota.js TwQuota.total、site/articles.js remoteGet、site/app.js 今日事件抽屜）
# Andy 10-16 批准資安評估「最小有效版本」：新文章全文只在會員後端、Plus 篇數與訪客今日事件 5 次改伺服器計數、累計額度 fail-closed。
# 這段**起真的 worker.js（devserver.mjs，Durable Object 換成 node:sqlite）**，用真的瀏覽器走完整條路：
#   · 今日事件（訪客，真的按「事件」鈕）：伺服器簽發訪客編號寫進 localStorage 的 tw.gid、第 1～5 次有清單、第 6 次提示卡；
#     清掉 localStorage 的計數快取（tw.total）重新整理仍然擋著（伺服器說了算）；
#     開無痕（全新 context）的前 3 個編號各有 5 次、第 4 個編號用到同 IP 總量 20 次、第 5 個編號被同 IP 接住（提示卡寫「這個網路」）
#   · 精選文章（新文章 src:'api'，索引沒有摘要／副標／標籤）：訪客與註冊會員只看標題、DOM 與網路回應裡都沒有內文；
#     Plus 第 1～5 篇可讀、第 6 篇 402 提示卡；竄改 tw.total 或換一個全新的瀏覽器（只帶登入權杖）結果一樣；Pro 全部可讀
#   · fail-closed：擋掉會員伺服器的網址、擋掉 quota.js → 文章與今日事件都**不是全開**
# 截圖：TW_AF_SHOTS=<資料夾>（桌機 1440＋手機 390：訪客、Plus 第 5／6 篇、Pro、今日事件第 6 次）
# ⚠ 一律 --workers 1（起 devserver 用）

AF_BOT_KEY = "dev-article-bot-key-0123456789abcdef"      # 跟 workers/account-api/devserver.mjs 的 ARTICLE_BOT_KEY 一致（只在本機）


def af_fake_total(c, used=None, limit=5):
    """假的 /v1/total/*（給「畫面行為」類的舊段落用）：照真伺服器的規則回應 —— 第一次沒帶訪客編號就發一個、同一個 key 不重算、滿了回 ok:false。"""
    st = {"used": list(used or []), "g": None, "calls": []}
    G = "g1." + "A" * 22 + "." + "B" * 22

    def h(route):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        hd = {"access-control-allow-origin": "*", "content-type": "application/json"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            b = json.loads(req.post_data or "{}")
        except Exception:  # noqa: BLE001
            b = {}
        st["calls"].append((path, b.get("key")))
        out = {"limits": {"events.total": {"limit": limit, "used": list(st["used"])}}}
        if path.endswith("/v1/total/use"):
            key, ex = b.get("key"), {}
            if not req.headers.get("x-tw-guest"):
                st["g"] = G
                ex["g"] = G
            if key in st["used"]:
                okk = True
            elif len(st["used"]) >= limit:
                okk = False
            else:
                st["used"].append(key)
                okk = True
            out = {"ok": okk, "limit": limit, "used": list(st["used"]), **ex, **({} if okk else {"why": "quota"})}
        route.fulfill(status=200, body=json.dumps(out), headers=hd)

    c.route(ACCTM4_API + "/v1/total/**", h)
    return st


def t_anti_freeload_1016(b, base, code):
    import urllib.request
    T = "防白嫖後端1016"
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dbg = bool(os.environ.get("TW_DEV_LOG"))
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin,
                            "--person", "plus=plus@example.com=Plus 測試", "--person", "pro=pro@example.com=Pro 測試"],
                           stdout=None if dbg else subprocess.DEVNULL, stderr=None if dbg else subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    shots = os.environ.get("TW_AF_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)

    def shot(pg, name):
        if not shots:
            return
        try:
            pg.screenshot(path=str(pathlib.Path(shots) / name))
        except Exception as e:  # noqa: BLE001
            print(f"  （{T} 截圖 {name} 沒存成：{str(e)[:80]}）")

    ctxs = []
    N = 8
    today = time.strftime("%Y-%m-%d")
    IDS = [f"2026-10-16-know-af{i}" for i in range(1, N + 1)]
    index = {"updated": today, "articles": [{"id": i, "cat": ["news", "intro", "know"][k % 3], "title": f"後端文章{k + 1}", "date": today, "topic": f"t{k}", "reading_min": 3,
                                              "groups": [{"id": "foundry", "name": "晶圓代工"}], "src": "api"} for k, i in enumerate(IDS)]}
    static_hits = []        # 這輪有沒有人去抓公開的 posts/*.json（新文章不該有）
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

        def bot(body):
            r = urllib.request.Request(api + "/v1/articles/jobs/bot", data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + AF_BOT_KEY}, method="POST")
            return json.loads(urllib.request.urlopen(r, timeout=10).read())

        def new_ctx(width=1440, tok=None, block=None):
            c = b.new_context(viewport={"width": width, "height": 900 if width > 640 else 844}, has_touch=width <= 640, is_mobile=width <= 640)
            init = "window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.live.on','0')}catch(e){}"
            if tok:
                init += "try{if(!sessionStorage.getItem('afseed')){sessionStorage.setItem('afseed','1');localStorage.setItem('tw.acct.tok'," + json.dumps(tok) + ")}}catch(e){}"
            c.add_init_script(init)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            c.route("**/articles/index.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(index, ensure_ascii=False)))

            def post_route(r):
                static_hits.append(r.request.url)
                r.fulfill(status=404, body="{}")
            c.route("**/articles/posts/*.json", post_route)
            for pat in (block or []):
                c.route(pat, lambda r: r.abort())
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
            return pg.evaluate("() => TwAccount.tok()")

        def call(pg, path, body):
            return pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])

        # ---------------- 準備：管理者建 Plus／Pro 方案與帳號、機器路由上傳 8 篇全文；各身分登入拿權杖
        ca = new_ctx(); ad = ca.new_page()
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('acctBtn')", 8000)
        login(ad, "andy")
        for pid, nm in (("plus", "Plus"), ("pro", "Pro")):
            call(ad, "/v1/admin/plans/put", {"id": pid, "name": nm, "feats": {}})
            call(ad, "/v1/admin/perm/put", {"email": f"{pid}@example.com", "plan": pid})
        for k, i in enumerate(IDS):
            r = bot({"op": "put_body", "id": i, "json": {"id": i, "cat": index["articles"][k]["cat"], "title": f"後端文章{k + 1}", "subtitle": f"SUB-SECRET-{k + 1}", "date": today,
                                                         "summary": f"SUMMARY-SECRET-{k + 1}", "reading_min": 3, "blocks": [{"t": "h", "text": f"小標{k + 1}"}, {"t": "p", "text": f"BODY-SECRET-{k + 1}"}],
                                                         "sources": [], "site_links": []}})
            if not r.get("ok"):
                ok(f"{T}：機器路由上傳第 {k + 1} 篇全文", False, r)
        toks = {}
        for who in ("plus", "pro", "bob"):
            cx = new_ctx(); px = cx.new_page()
            px.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(px, "() => !!document.getElementById('acctBtn')", 8000)
            toks[who] = login(px, who)
            cx.close()
        ca.close()
        ok(f"{T}：準備完成（Plus／Pro／註冊會員各拿到登入權杖）", all(toks.values()), toks)

        ST = """() => { const q = document.getElementById('artQuota'), cs = [...document.querySelectorAll('#artList .artc')];
            return { mode: q ? q.dataset.mode : null, vis: !!q && !q.hidden && q.getClientRects().length > 0, used: q ? q.dataset.used : null, lim: q ? q.dataset.lim : null, txt: q ? q.textContent : '',
              cards: cs.map(a => ({ id: a.dataset.id, lock: a.dataset.lock, lk: (a.querySelector('.lk') || {}).textContent || '' })), html: document.getElementById('artList').innerHTML }; }"""
        POST = """() => ({ body: (document.querySelector('.artbody') || {}).textContent || null, lock: !!document.getElementById('artLock'), cardTxt: (document.querySelector('#artLock .qcard') || {}).textContent || '',
            html: (document.getElementById('v-articles') || {}).innerHTML || '', qt: (document.querySelector('.artqt') || {}).textContent || '', err: (document.getElementById('artErr') || {}).textContent || '' })"""

        def to_list(pg):
            pg.goto(base + "#articles", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 15000)
            pg.wait_for_timeout(1200)       # 給「向伺服器同步已讀清單」一點時間

        def open_post(pg, i):
            pg.evaluate("h => { location.hash = h; }", f"#article/{IDS[i - 1]}")
            wait_until(pg, "() => !!document.querySelector('#artPost') && (!!document.querySelector('.artbody') || !!document.getElementById('artLock') || !!document.getElementById('artErr'))", 10000)
            pg.wait_for_timeout(400)
            return pg.evaluate(POST)

        def watch(pg):
            log = []
            pg.on("response", lambda r: log.append((re.sub(r"^https?://[^/]+", "", r.url).split("?")[0], r.status)) if "/v1/articles/get" in r.url else None)
            return log

        # ================= 精選文章：Plus（桌機 1440 主線）
        cp = new_ctx(tok=toks["plus"]); pg = cp.new_page(); glog = watch(pg)
        to_list(pg)
        st = pg.evaluate(ST)
        ok(f"{T}[Plus]：列表 {N} 張卡全是鎖定（只有標題，索引裡根本沒有摘要／副標），額度條 0／5", st["mode"] == "quota" and st["used"] == "0" and st["lim"] == "5" and len(st["cards"]) == N
           and "SUMMARY-SECRET" not in st["html"] and "SUB-SECRET" not in st["html"], [st["mode"], st["used"], st["lim"]])
        for i in (1, 2, 3, 4, 5):
            pp = open_post(pg, i)
            ok(f"{T}[Plus]：開第 {i} 篇 → 全文來自會員後端（BODY-SECRET-{i}）、額度 {i}／5", f"BODY-SECRET-{i}" in (pp["body"] or "") and f"{i}／5" in pp["qt"], [pp["qt"], pp["body"]])
        ok(f"{T}[Plus]：這 5 篇都沒有去抓公開的 posts/*.json（新文章全文不在靜態檔）", not static_hits, static_hits)
        shot(pg, "plus-article5-1440.png")
        pp = open_post(pg, 1)
        ok(f"{T}[Plus]：重讀第 1 篇 → 照樣能讀、伺服器的讀過紀錄仍是 5 篇", "BODY-SECRET-1" in (pp["body"] or "") and len(call(pg, "/v1/total/state", {"ids": ["art.read.n"]})["limits"]["art.read.n"]["used"]) == 5, pp["qt"])
        glog.clear()
        p6 = open_post(pg, 6)
        ok(f"{T}[Plus]：第 6 篇 → 升級卡（額度 5／5 已用完），畫面與 DOM 都沒有內文（本機快取已知用完，不必再問伺服器）", p6["lock"] and p6["body"] is None and "BODY-SECRET-6" not in p6["html"] and "5／5" in p6["cardTxt"], [p6["cardTxt"][:60], glog])
        shot(pg, "plus-article6-locked-1440.png")
        # 竄改本機快取：把 tw.total 清空、重新整理 → 伺服器說了算，仍然鎖著
        pg.evaluate("() => { localStorage.removeItem('tw.total'); }")
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('artLock') || !!document.querySelector('.artbody')", 15000); pg.wait_for_timeout(600)
        pr = pg.evaluate(POST)
        ok(f"{T}[Plus]：把本機計數（tw.total）清空再重新整理 → 第 6 篇仍然鎖著、伺服器真的回了 402（計數在伺服器，改 localStorage 沒用）", pr["lock"] and pr["body"] is None and any(s == 402 for _, s in glog), [pr["cardTxt"][:40], glog])
        # 連本機快取都竄改成「還有 5 篇」→ 伺服器照樣拒絕
        pg.evaluate("() => { localStorage.setItem('tw.total', '{}'); }")
        to_list(pg)
        st = pg.evaluate(ST)
        ok(f"{T}[Plus]：回列表 → 額度條由伺服器校正回 5／5（不是被清掉的 0／5）、5 張已解鎖卡", st["used"] == "5" and sum(1 for x in st["cards"] if x["lock"] == "0") == 5, [st["used"], st["txt"]])
        shot(pg, "plus-list-5of5-1440.png")
        cp.close()
        # 換一個全新的瀏覽器（沒有任何本機快取，只帶登入權杖）：同一個帳號結果一樣
        cn = new_ctx(tok=toks["plus"]); pn = cn.new_page()
        pn.goto(base + f"#article/{IDS[5]}", wait_until="domcontentloaded")
        wait_until(pn, "() => !!document.getElementById('artLock') || !!document.querySelector('.artbody')", 15000); pn.wait_for_timeout(500)
        p = pn.evaluate(POST)
        ok(f"{T}[Plus 換瀏覽器]：全新環境直接開第 6 篇 → 鎖著（不會因為換裝置又有 5 篇）", p["lock"] and p["body"] is None, p["cardTxt"][:40])
        p = open_post(pn, 3)
        ok(f"{T}[Plus 換瀏覽器]：第 3 篇（之前讀過）→ 仍能重讀", "BODY-SECRET-3" in (p["body"] or ""), p["qt"])
        cn.close()

        # ================= 訪客／註冊會員：只看標題
        for who, nm in (("guest", "訪客"), ("bob", "註冊會員")):
            cg = new_ctx(tok=toks.get(who)); pg = cg.new_page(); glog = watch(pg)
            to_list(pg)
            st = pg.evaluate(ST)
            ok(f"{T}[{nm}]：列表 {N} 張卡全鎖、額度條＝只能看標題與分類", st["mode"] == "none" and len(st["cards"]) == N and all(x["lock"] == "1" for x in st["cards"]), [st["mode"], len(st["cards"])])
            if who == "guest":
                shot(pg, "guest-list-1440.png")
            pp = open_post(pg, 2)
            ok(f"{T}[{nm}]：點進第 2 篇 → 鎖定頁、DOM 沒有任何內文、沒有去抓公開 posts/*.json", pp["lock"] and pp["body"] is None and "BODY-SECRET" not in pp["html"] and not static_hits, [pp["cardTxt"][:40], static_hits])
            if who == "guest":
                shot(pg, "guest-article-locked-1440.png")
            # 直接打後端（繞過畫面）：訪客 401、註冊會員 403，回應都沒有內文
            raw = pg.evaluate("async (a) => { const o = {}; const r = await fetch(a + '/v1/articles/get', { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify(Object.assign({ id: '" + IDS[1] + "' }, window.TwAccount.tok() ? { t: window.TwAccount.tok() } : {})) }); return { s: r.status, t: await r.text() }; }", api)
            ok(f"{T}[{nm}]：不經畫面直接打後端 /v1/articles/get → {'401' if who == 'guest' else '403'}、回應沒有內文", raw["s"] == (401 if who == "guest" else 403) and "BODY-SECRET" not in raw["t"], raw)
            cg.close()

        # ================= Pro
        cr = new_ctx(tok=toks["pro"]); pg = cr.new_page()
        to_list(pg)
        st = pg.evaluate(ST)
        ok(f"{T}[Pro]：不顯示額度條、{N} 張卡全解鎖", not st["vis"] and all(x["lock"] == "0" for x in st["cards"]), [st["mode"], st["vis"]])
        res = [("BODY-SECRET-%d" % i) in (open_post(pg, i)["body"] or "") for i in range(1, N + 1)]
        ok(f"{T}[Pro]：連開 {N} 篇（超過 Plus 的 5 篇）全部是全文", all(res), res)
        shot(pg, "pro-article-1440.png")
        ok(f"{T}[Pro]：伺服器沒有為 Pro 記讀過紀錄（不限量的人不計數）", call(pg, "/v1/total/state", {"ids": ["art.read.n"]})["limits"]["art.read.n"]["used"] == [], None)
        cr.close()

        # ================= fail-closed：擋掉會員伺服器網址、擋掉 quota.js —— 不是全開
        for nm, tk, blk in (("Pro＋擋掉會員伺服器", "pro", [api + "/**"]), ("Pro＋擋掉 quota.js", "pro", ["**/quota.js*"]), ("Plus＋擋掉會員伺服器", "plus", [api + "/**"])):
            cb = new_ctx(tok=toks[tk], block=blk); pg = cb.new_page()
            pg.goto(base + "#articles", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 15000)
            pg.wait_for_timeout(5500)       # permReady 最多等 4 秒，之後照訪客算
            st = pg.evaluate(ST)
            ok(f"{T}[fail-closed {nm}]：列表 {N} 張卡全是鎖定（不是全開）", len(st["cards"]) == N and all(x["lock"] == "1" for x in st["cards"]), [x["lock"] for x in st["cards"]])
            pp = open_post(pg, 1)
            ok(f"{T}[fail-closed {nm}]：點進文章 → 沒有內文（鎖定頁或讀不到提示）", pp["body"] is None and "BODY-SECRET" not in pp["html"], pp["cardTxt"][:40] or pp["err"][:40])
            if nm.startswith("Pro＋擋掉會員"):
                shot(pg, "failclosed-articles-1440.png")
            cb.close()

        # ================= 今日事件：訪客（真的 Worker）
        EV = """() => { const s = document.getElementById('side'), l = document.getElementById('evList');
            return { q: (document.getElementById('evQuota') || {}).textContent || '', open: s.classList.contains('open'), evs: l.querySelectorAll('.ev').length, lock: !!l.querySelector('#evLock .qcard'),
              lockTxt: (l.querySelector('#evLock .qcard') || {}).textContent || '', gid: (function () { try { return localStorage.getItem('tw.gid') || ''; } catch (e) { return ''; } })(),
              wait: !!l.querySelector('#evWait') }; }"""

        def boot(pg):
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000)
            pg.wait_for_timeout(500)

        def open_ev(pg, n_wait=9000):
            pg.click("#evToggle")
            wait_until(pg, "() => document.getElementById('side').classList.contains('open') && !document.querySelector('#evList #evWait')", n_wait)
            pg.wait_for_timeout(250)
            return pg.evaluate(EV)

        def close_ev(pg):
            pg.click("#evClose"); wait_until(pg, "() => !document.getElementById('side').classList.contains('open')", 4000); pg.wait_for_timeout(200)

        ce = new_ctx(); pg = ce.new_page()
        boot(pg)
        gid = ""
        for i in range(1, 6):
            s = open_ev(pg)
            gid = s["gid"] or gid
            ok(f"{T}[今日事件·訪客]：第 {i} 次按「事件」→ 有事件清單（{s['evs']} 則）、清單頂端寫「已用 {i}／5 次」", s["evs"] > 0 and not s["lock"] and f"已用 {i}／5 次" in s["q"], [s["evs"], s["lock"], s["q"]])
            if i == 5:
                shot(pg, "events-5th-1440.png")
            close_ev(pg)
        ok(f"{T}[今日事件·訪客]：伺服器簽發的訪客編號存在 localStorage（tw.gid，格式 g1.<隨機>.<簽章>）", bool(re.match(r"^g1\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{22}$", gid)), gid)
        s = open_ev(pg)
        ok(f"{T}[今日事件·訪客]：第 6 次 → 清單不在 DOM（0 個 .ev）、「訪客預覽 5 次已用完」提示卡", s["evs"] == 0 and s["lock"] and "5 次已用完" in s["lockTxt"], s)
        shot(pg, "events-6th-locked-1440.png")
        close_ev(pg)
        pg.evaluate("() => { localStorage.removeItem('tw.total'); }")
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000); pg.wait_for_timeout(500)
        s = open_ev(pg)
        ok(f"{T}[今日事件·訪客]：把本機計數（tw.total）清掉重新整理再開 → 仍是提示卡（伺服器記得這個訪客編號）", s["evs"] == 0 and s["lock"], s)
        ce.close()
        # 無痕視窗（全新 context＝沒有訪客編號）：同一個網路（本機都是同一個 IP）
        for k in range(2, 5):
            cx = new_ctx(); px = cx.new_page(); boot(px)
            res = []
            for i in range(1, 6):
                s = open_ev(px); res.append(s["evs"] > 0 and not s["lock"]); close_ev(px)
            ok(f"{T}[今日事件·無痕 {k}]：第 {k} 個全新訪客編號（同一個網路）：連開 5 次都有清單" + ("（前 3 個各有 5 次；第 4 個吃同 IP 總量 20 次的最後 5 次）" if k >= 3 else ""), all(res), res)
            cx.close()
        cx = new_ctx(); px = cx.new_page(); boot(px)
        s = open_ev(px)
        ok(f"{T}[今日事件·無痕 5]：第 5 個全新訪客編號（同一個網路）→ 第一次就被接住：沒有清單、提示卡寫「這個網路」", s["evs"] == 0 and s["lock"] and "這個網路" in s["lockTxt"], s)
        shot(px, "events-ipcap-1440.png")
        cx.close()
        # fail-closed：擋掉 /v1/total/*、擋掉 quota.js → 訪客開抽屜不是全開
        for nm, blk in (("擋掉會員伺服器", [api + "/**"]), ("擋掉 quota.js", ["**/quota.js*"])):
            cb = new_ctx(block=blk); pg = cb.new_page()
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000); pg.wait_for_timeout(800)
            s = open_ev(pg, 14000)
            ok(f"{T}[fail-closed 今日事件·{nm}]：訪客按「事件」→ 沒有事件清單（0 個 .ev）、是提示卡（不是全開）", s["evs"] == 0 and s["lock"], s)
            cb.close()

        # ================= 手機 390（觸控）
        cm = new_ctx(390, tok=toks["plus"]); mp = cm.new_page()
        mp.goto(base + f"#article/{IDS[0]}", wait_until="domcontentloaded")
        wait_until(mp, "() => !!document.querySelector('.artbody') || !!document.getElementById('artLock')", 15000); mp.wait_for_timeout(500)
        shot(mp, "plus-article-390.png")
        mp.goto(base + f"#article/{IDS[5]}", wait_until="domcontentloaded")
        wait_until(mp, "() => !!document.getElementById('artLock') || !!document.querySelector('.artbody')", 15000); mp.wait_for_timeout(600)
        GEO = """() => { const c = document.querySelector('#artLock .qcard'), r = c ? c.getBoundingClientRect() : null;
            const fs = [...document.querySelectorAll('#artLock *')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
            return { l: r && Math.round(r.left), r: r && Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, min: fs.length ? Math.min(...fs) : 0 }; }"""
        g = mp.evaluate(GEO)
        ok(f"{T}[手機390·Plus]：5／5 後第 6 篇 → 升級卡在畫面內、沒有橫向捲軸、字 ≥ 11px、沒有內文", g["l"] is not None and g["l"] >= 0 and g["r"] <= g["vw"] and g["sw"] <= 1 and g["min"] >= 11 and mp.evaluate(POST)["body"] is None, g)
        shot(mp, "plus-article6-locked-390.png")
        cm.close()
        cm = new_ctx(390); mp = cm.new_page()
        to_list(mp)
        shot(mp, "guest-list-390.png")
        cm.close()
        cm = new_ctx(390, tok=toks["pro"]); mp = cm.new_page()
        mp.goto(base + f"#article/{IDS[6]}", wait_until="domcontentloaded")
        wait_until(mp, "() => !!document.querySelector('.artbody')", 15000); mp.wait_for_timeout(400)
        shot(mp, "pro-article-390.png")
        cm.close()
        # 手機今日事件第 6 次（這個網路的總量已被前面用完 → 提示卡；用手指開抽屜）
        cm = new_ctx(390); mp = cm.new_page()
        mp.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(mp, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000); mp.wait_for_timeout(600)
        mp.locator("#m4Burger").tap(); wait_until(mp, "() => { const d = document.getElementById('m4Drawer'); return d && !d.hidden; }", 4000); mp.wait_for_timeout(300)
        mp.locator('#m4Drawer .m4item[data-act="events"]').tap()
        wait_until(mp, "() => document.getElementById('side').classList.contains('open') && !document.querySelector('#evList #evWait')", 12000); mp.wait_for_timeout(500)
        s = mp.evaluate(EV)
        g = mp.evaluate("""() => { const c = document.querySelector('#evLock .qcard'), r = c ? c.getBoundingClientRect() : null; return { l: r && Math.round(r.left), r: r && Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth }; }""")
        ok(f"{T}[手機390·今日事件]：用手指開抽屜 → 提示卡（沒有清單）、卡在畫面內、沒有橫向捲軸", s["evs"] == 0 and s["lock"] and g["l"] is not None and g["l"] >= 0 and g["r"] <= g["vw"] and g["sw"] <= 1, [s["lock"], g])
        shot(mp, "events-locked-390.png")
        cm.close()
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("防白嫖後端1016", lambda pg, b, base, code: t_anti_freeload_1016(b, base, code))
