# 驗收段落「線上名單1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 線上名單1017（Andy 10-17：「點擊後我可以看到目前有誰上線，需要顯示 Mail list」）
# 本機起真的 worker.js（devserver），1440：
#   ① 會員 gary 開著網站（#flow）→ 站主 andy 點頂欄「N 人在線」→ 下方展開名單：gary 的名字、email、所在頁與多久前；andy 自己也在
#   ② 「複製 email 清單」→ 剪貼簿是 email 以逗號分隔、含 gary@example.com
#   ③ 再點一次人數／按 Esc → 收起；「完整流量頁 →」換到 #admin/traffic
#   ④ 會員 gary 點人數 → 什麼都不出現（只有站主看得到名單）
OL_PEOPLE = {"gary": "gary@example.com"}


def t_online_list_1017(b, base, code):
    import urllib.request
    T = "線上名單1017"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    args = ["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin]
    for k, e in OL_PEOPLE.items():
        args += ["--person", f"{k}={e}={k.capitalize()} 測試"]
    dev = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
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
        if not ok(f"{T}：本機 account-api（devserver）起得來", up):
            return

        def new_ctx():
            c = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def login(pg, who):
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
            pg.evaluate("() => TwAccount.login()")
            pg.wait_for_selector("#acctGo", state="visible", timeout=6000)
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=8000)
            pop.click("#as-" + who)
            return wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)

        gp = new_ctx().new_page(); gp.on("pageerror", lambda e: errs.append("gary: " + str(e)))
        gp.goto(base + "#flow", wait_until="domcontentloaded")
        if not ok(f"{T}：會員 gary 登入", bool(login(gp, "gary"))):
            return
        ap = new_ctx().new_page(); ap.on("pageerror", lambda e: errs.append("andy: " + str(e)))
        ap.goto(base + "#overview", wait_until="domcontentloaded")
        if not ok(f"{T}：站主 andy 登入", bool(login(ap, "andy"))):
            return
        gp.evaluate("() => { location.hash = '#flow'; }")
        ok(f"{T}：頂欄出現「N 人在線」（Andy：上線改回原本的樣式）", bool(wait_until(ap, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden && /人在線/.test(o.textContent) ? 1 : 0; }", 15000)))
        ap.click("#acctOnline")
        ok(f"{T}：點人數 → 下方展開名單", bool(wait_until(ap, "() => { const p = document.getElementById('acctOnPop'); return p && !p.hidden && p.querySelector('.opl, .opz') ? 1 : 0; }", 8000)))
        st = ap.evaluate("""() => { const p = document.getElementById('acctOnPop'), b = document.getElementById('acctOnline').getBoundingClientRect(), r = p.getBoundingClientRect();
            return { rows: [...p.querySelectorAll('.opl li')].map(li => [li.querySelector('.opn').textContent, li.querySelector('.ope').textContent, li.querySelector('.opr').textContent]),
                     head: p.querySelector('.oph').textContent, below: r.top >= b.bottom - 1, inview: r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth }; }""")
        g = [x for x in st["rows"] if x[1] == "gary@example.com"]
        ok(f"{T}：名單有 gary（名字、email、所在頁與多久前）與站主自己；在人數鈕下方、在畫面內",
           bool(g) and "Gary" in g[0][0] and "前" in g[0][2] and any("@" in x[1] and x[1] != "gary@example.com" for x in st["rows"])
           and "目前在線" in st["head"] and st["below"] and st["inview"], st)
        ap.click("#acctOnCopy"); ap.wait_for_timeout(300)
        clip = ap.evaluate("async () => { try { return await navigator.clipboard.readText(); } catch (e) { return 'ERR ' + e; } }")
        btn = ap.inner_text("#acctOnCopy")
        ok(f"{T}：複製 email 清單 → 剪貼簿是逗號分隔的 email、按鈕寫「已複製」", "gary@example.com" in clip and ", " in clip and "已複製" in btn, [clip, btn])
        shot = os.environ.get("TW_ONLINE_SHOT")
        if shot:
            ap.screenshot(path=shot)
        ap.keyboard.press("Escape"); ap.wait_for_timeout(200)
        ok(f"{T}：按 Esc → 收起", ap.evaluate("() => document.getElementById('acctOnPop').hidden"))
        ap.click("#acctOnline"); wait_until(ap, "() => !!document.querySelector('#acctOnPop:not([hidden]) #acctOnMore')", 8000)
        ap.click("#acctOnMore"); ap.wait_for_timeout(400)
        st = ap.evaluate("() => ({ h: location.hash, hid: document.getElementById('acctOnPop').hidden })")
        ok(f"{T}：「完整流量頁 →」換到 #admin/traffic 並收起", st["h"] == "#admin/traffic" and st["hid"], st)
        wait_until(gp, "() => { const o = document.getElementById('acctOnline'); return o && !o.hidden ? 1 : 0; }", 8000)
        if gp.evaluate("() => { const o = document.getElementById('acctOnline'); return !!o && !o.hidden; }"):
            gp.click("#acctOnline"); gp.wait_for_timeout(600)
        ok(f"{T}：一般會員點人數 → 不出現名單", gp.evaluate("() => { const p = document.getElementById('acctOnPop'); return !p || p.hidden; }"))
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            c.close()
        dev.terminate()


register("線上名單1017", lambda pg, b, base, code: t_online_list_1017(b, base, code))
