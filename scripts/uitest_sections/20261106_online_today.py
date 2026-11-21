# 驗收段落「線上今天1106」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 線上今天1106（Andy 11-06：「只有站主看得到 今天有誰來 累積多久 主要看什麼 … 太長就改成拉Bar 形式 也需要新增訪客累積數量」）
# 本機起真的 worker.js（devserver）讓真人登入；「今天」端點用 Playwright 攔截回假資料（email 全是 example.com 假的），驗：
#   ① 站主 1440：點「N 人在線」→ 框內多一段「今天」（真 Worker 回 200 也畫得出來）
#   ② 假資料 21 筆（其中 1 筆是雜湊名單裡的測試帳）→ 列 20 筆、測試帳被排除、依累積時間排序、每列有時間／前 3 頁／最後出現
#   ③ 清單高度固定 288、scrollHeight 更大 → 滾輪能捲；捲動前後整個框高度不變；訪客今天／本週／累積數字出現
#   ④ 端點 404（後端還沒部署）→ 寫「需要更新會員後端」，上面的在線名單照舊
#   ⑤ 一般會員、純訪客：點人數不出現框、沒有任何 /online/today 請求、DOM 沒有「今天」
#   ⑥ 手機 390：同樣固定高度、手指拖得動（CDP 合成觸控捲動）、不橫向溢出、字 ≥ 11px
OT_PEOPLE = {"gary": "gary@example.com"}


def t_online_today_1106(b, base, code):
    import urllib.request, hashlib
    T = "線上今天1106"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in OT_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shots = os.environ.get("TW_ONLINE_TODAY_SHOTS")
    ghost = "ghost-test@example.com"
    ghash = hashlib.sha256(ghost.encode()).hexdigest()
    cors = {"access-control-allow-origin": "*"}

    def fake(n=20, ts=None):
        import time as _t
        now = int((_t.time() if ts is None else ts) * 1000)
        pages = ["flow", "stock", "overview", "industry", "heatmap"]
        ms = [{"name": f"測試會員{i + 1:02d}", "email": f"demo{i + 1:02d}@example.com", "ms": (200 - i * 9) * 60000 // 3 + 60000, "seen": now - i * 240000,
               "pages": [[pages[(i + k) % 5], max(60000, ((120 - i * 4) - k * 25) * 60000 // 3)] for k in range(3)], "by": "time"} for i in range(n)]
        ms.insert(3, {"name": "幽靈測試", "email": ghost, "ms": 99999999, "seen": now, "pages": [["flow", 60000]], "by": "time"})
        return {"day": "2026-11-06", "now": now, "members": ms, "guests": {"today": 37, "week": 212, "total": 1480, "since": "2026-10-17"}}

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

        def new_ctx(w=1440, h=900, mobile=False):
            kw = dict(viewport={"width": w, "height": h})
            if mobile:
                kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
            c = b.new_context(**kw)
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + "; window.__TW_TEST_HASHES = " + json.dumps([ghash]) + ";")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def login(pg, who):
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
            pg.evaluate("() => TwAccount.login()")
            pg.wait_for_selector("#acctGo", state="visible", timeout=30000)
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=30000)
            pop.click("#as-" + who)
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 30000)

        def reopen(pg):
            pg.evaluate("() => { const p = document.getElementById('acctOnPop'); if (p) p.hidden = true; }")
            pg.click("#acctOnline")
            return wait_until(pg, "() => { const p = document.getElementById('acctOnPop'); return p && !p.hidden && p.querySelector('#acctOnToday') ? 1 : 0; }", 20000)

        def fulfill_json(data, status=200):
            return lambda r: r.fulfill(status=status, content_type="application/json", headers=cors, body=json.dumps(data, ensure_ascii=False))

        ap = new_ctx().new_page(); ap.on("pageerror", lambda e: errs.append("andy: " + str(e)))
        ap.goto(base + "#overview", wait_until="domcontentloaded")
        if not ok(f"{T}：站主 andy 登入", bool(login(ap, "andy"))):
            return
        wait_until(ap, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 15000)

        # ① 真 Worker（沒攔截）：「今天」段出現，且有訪客累積那一行
        ap.click("#acctOnline")
        okr = wait_until(ap, "() => { const t = document.getElementById('acctOnToday'); return t && /訪客累積/.test(t.textContent) ? 1 : 0; }", 20000)
        ok(f"{T}：①站主點人數 → 真 Worker 回應畫出「今天」段（含訪客累積）", bool(okr), ap.evaluate("() => (document.getElementById('acctOnToday') || {}).textContent"))
        ok(f"{T}：①原本的「目前在線」「複製 email 清單」「完整流量頁」都還在",
           ap.evaluate("() => { const p = document.getElementById('acctOnPop'); return /目前在線/.test(p.textContent) && !!p.querySelector('#acctOnCopy') && !!p.querySelector('#acctOnMore'); }"))

        # ② 假資料 21 筆
        ap.route("**/v1/admin/online/today", fulfill_json(fake()))
        ok(f"{T}：②重新打開 → 清單出現", bool(reopen(ap)) and bool(wait_until(ap, "() => document.querySelectorAll('#acctOnTodayList li').length ? 1 : 0", 8000)))
        st = ap.evaluate("""() => { const L = document.getElementById('acctOnTodayList'), lis = [...L.querySelectorAll('li')];
            const txt = lis.map(li => li.textContent);
            return { n: lis.length, first: lis[0].querySelector('.opn').textContent, ghost: txt.some(t => /ghost-test/.test(t)),
                     dur: lis[0].querySelector('.opd').textContent, pages: lis[0].querySelector('.opp').textContent,
                     sorted: lis.every((li, i) => i === 0 || (+li.querySelector('.ope').textContent.slice(4, 6)) > (+lis[i - 1].querySelector('.ope').textContent.slice(4, 6))),
                     head: document.getElementById('acctOnToday').querySelector('.opth').textContent, guests: document.getElementById('acctOnToday').querySelector('.optg').textContent }; }""")
        ok(f"{T}：②列出 20 位（測試帳雜湊命中被排除）、依累積時間由多到少、第一位是測試會員01", st["n"] == 20 and not st["ghost"] and st["sorted"] and st["first"] == "測試會員01", st)
        ok(f"{T}：②每列有「累積時間（x 小時 y 分）」「主要看：三個中文頁名」「最後出現 HH:MM」",
           bool(re.search(r"\d+ 小時", st["dur"])) and st["pages"].count("・") == 2 and "主要看：" in st["pages"] and bool(re.search(r"最後出現 \d\d:\d\d", st["pages"])) and not re.search(r"\b(flow|stock|overview|industry|heatmap)\b", st["pages"]), st)
        ok(f"{T}：②標題寫會員 20 位、訪客今天 37 台；訪客累積寫本週 212・累積 1480・自 2026-10-17 起",
           "會員 20 位" in st["head"] and "37" in st["head"] and "本週 212" in st["guests"] and "累積 1480" in st["guests"] and "2026-10-17" in st["guests"], st)

        # ③ 固定高度＋框內捲動
        g0 = ap.evaluate("() => { const L = document.getElementById('acctOnTodayList'), p = document.getElementById('acctOnPop'); return { ch: L.offsetHeight, sh: L.scrollHeight, oy: getComputedStyle(L).overflowY, ph: p.getBoundingClientRect().height, pt: p.getBoundingClientRect().top }; }")
        ok(f"{T}：③清單高度固定 288、內容比框高（有捲軸）、overflow-y=auto", g0["ch"] == 288 and g0["sh"] > g0["ch"] + 100 and g0["oy"] == "auto", g0)
        box = ap.evaluate("() => { const r = document.getElementById('acctOnTodayList').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
        ap.mouse.move(box[0], box[1]); ap.mouse.wheel(0, 400); ap.wait_for_timeout(300)
        g1 = ap.evaluate("() => { const L = document.getElementById('acctOnTodayList'), p = document.getElementById('acctOnPop'); return { st: L.scrollTop, ph: p.getBoundingClientRect().height, pst: p.scrollTop, wy: scrollY }; }")
        ok(f"{T}：③滾輪在清單上 → 清單自己捲動（scrollTop>0）、外框高度不變、外框與頁面都沒被捲走", g1["st"] > 100 and abs(g1["ph"] - g0["ph"]) < 1 and g1["pst"] == 0, [g0, g1])
        ap.evaluate("() => { const L = document.getElementById('acctOnTodayList'); L.scrollTop = L.scrollHeight; }")
        last = ap.evaluate("() => { const L = document.getElementById('acctOnTodayList'), li = L.querySelector('li:last-child'), a = li.getBoundingClientRect(), c = L.getBoundingClientRect(); return { name: li.querySelector('.opn').textContent, vis: a.bottom <= c.bottom + 1 && a.top >= c.top }; }")
        ok(f"{T}：③捲到底 → 最後一位（測試會員20）完整看得到", last["name"] == "測試會員20" and last["vis"], last)
        if shots:
            ap.evaluate("() => { document.getElementById('acctOnTodayList').scrollTop = 120; }")
            ap.screenshot(path=os.path.join(shots, "online_today_1440.png"))

        # ④ 端點 404
        ap.unroute("**/v1/admin/online/today")
        ap.route("**/v1/admin/online/today", fulfill_json({"error": "not_found"}, 404))
        ap.evaluate("() => { document.getElementById('acctOnPop').hidden = true; }")
        ap.click("#acctOnline")
        wait_until(ap, "() => { const t = document.getElementById('acctOnToday'); return t && /更新會員後端/.test(t.textContent) ? 1 : 0; }", 20000)
        s4 = ap.evaluate("() => { const p = document.getElementById('acctOnPop'); return { msg: /需要更新會員後端/.test(p.textContent), list: !!p.querySelector('#acctOnTodayList'), live: /目前在線/.test(p.textContent) && !!p.querySelector('#acctOnCopy') }; }")
        ok(f"{T}：④後端還沒部署（404）→ 寫「需要更新會員後端」、沒有清單，上面的在線名單照舊", s4["msg"] and not s4["list"] and s4["live"], s4)

        # ⑤ 一般會員、純訪客
        hits = []
        gp = new_ctx().new_page(); gp.on("pageerror", lambda e: errs.append("gary: " + str(e)))
        gp.on("request", lambda r: hits.append(r.url) if "/online/today" in r.url else None)
        gp.goto(base + "#flow", wait_until="domcontentloaded")
        if ok(f"{T}：會員 gary 登入", bool(login(gp, "gary"))):
            wait_until(gp, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 10000)
            gp.click("#acctOnline"); gp.wait_for_timeout(800)
            ok(f"{T}：⑤一般會員點人數 → 沒有框、DOM 沒有「今天」、沒送出任何 /online/today 請求",
               gp.evaluate("() => { const p = document.getElementById('acctOnPop'); return (!p || p.hidden) && !document.getElementById('acctOnToday'); }") and not hits, hits)
        vh = []
        vp = new_ctx().new_page(); vp.on("pageerror", lambda e: errs.append("guest: " + str(e)))
        vp.on("request", lambda r: vh.append(r.url) if "/online/today" in r.url else None)
        vp.goto(base + "#flow", wait_until="domcontentloaded"); vp.wait_for_timeout(2500)
        if vp.evaluate("() => { const o = document.getElementById('acctOnline'); return !!o && !o.hidden; }"):
            vp.click("#acctOnline", force=True); vp.wait_for_timeout(600)
        ok(f"{T}：⑤純訪客 → 沒有框、沒有「今天」、沒送出請求", vp.evaluate("() => { const p = document.getElementById('acctOnPop'); return (!p || p.hidden) && !document.getElementById('acctOnToday'); }") and not vh, vh)

        # ⑥ 手機 390
        mp = new_ctx(390, 844, mobile=True).new_page(); mp.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
        mp.goto(base + "#overview", wait_until="domcontentloaded")
        if ok(f"{T}：手機 390 站主登入", bool(login(mp, "andy"))):
            mp.route("**/v1/admin/online/today", fulfill_json(fake()))
            wait_until(mp, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden && o.getBoundingClientRect().width > 0 ? 1 : 0; }", 15000)
            mp.evaluate("() => document.getElementById('acctOnline').click()")
            okm = wait_until(mp, "() => document.querySelectorAll('#acctOnTodayList li').length ? 1 : 0", 10000)
            ok(f"{T}：⑥手機點人數 → 「今天」清單出現（20 位）", bool(okm) and mp.evaluate("() => document.querySelectorAll('#acctOnTodayList li').length") == 20)
            m0 = mp.evaluate("""() => { const L = document.getElementById('acctOnTodayList'), p = document.getElementById('acctOnPop'), r = p.getBoundingClientRect();
                const fs = Math.min(...[...L.querySelectorAll('li *')].map(e => parseFloat(getComputedStyle(e).fontSize)));
                return { ch: L.offsetHeight, sh: L.scrollHeight, ph: r.height, left: r.left, right: r.right, vw: innerWidth, pw: p.scrollWidth, pcw: p.clientWidth, lw: L.scrollWidth, lcw: L.clientWidth, docw: document.documentElement.scrollWidth, fs }; }""")
            ok(f"{T}：⑥手機清單高度固定 288、可捲；框在畫面內、沒有橫向溢出；字 ≥ 11px",
               m0["ch"] == 288 and m0["sh"] > 300 and m0["left"] >= 0 and m0["right"] <= m0["vw"] and m0["pw"] <= m0["pcw"] + 1 and m0["lw"] <= m0["lcw"] + 1 and m0["docw"] <= m0["vw"] + 1 and m0["fs"] >= 11, m0)
            cdp = mp.context.new_cdp_session(mp)
            r = mp.evaluate("() => { const r = document.getElementById('acctOnTodayList').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
            hit = mp.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e ? (e.id || e.className || e.tagName) + ' / inList=' + !!e.closest('#acctOnTodayList') : null; }", r)
            # 手指真的按下、往上拖、放開（逐步移動，瀏覽器才會把它判成捲動手勢）
            x0, y0 = r[0], r[1] + 100
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
            for i in range(1, 13):
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0, "y": y0 - i * 20}]})
                mp.wait_for_timeout(16)
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            mp.wait_for_timeout(800)
            m1 = mp.evaluate("() => { const L = document.getElementById('acctOnTodayList'); return { st: L.scrollTop, ph: document.getElementById('acctOnPop').getBoundingClientRect().height, wy: scrollY }; }")
            m1["hit"] = hit; m1["pt"] = r
            ok(f"{T}：⑥手機用手指往上拖 → 清單自己捲動、外框高度不變、頁面沒跟著捲", m1["st"] > 100 and abs(m1["ph"] - m0["ph"]) < 1 and m1["wy"] == 0, [m0, m1])
            if shots:
                mp.screenshot(path=os.path.join(shots, "online_today_390.png"))
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            c.close()
        dev.terminate()


register("線上今天1106", lambda pg, b, base, code: t_online_today_1106(b, base, code))
