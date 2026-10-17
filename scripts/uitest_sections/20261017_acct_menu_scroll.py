# 驗收段落「帳號選單捲動1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 帳號選單捲動1017（Andy 10-17：「這邊太長，需要有拉Bar」）
# 本機起真的 worker.js（devserver），站主 andy 登入，桌機 1440×700（矮視窗）：
#   ① 點右上帳號鈕 → 選單底邊不超過視窗、內容比選單高、可以捲（overflow-y auto）
#   ② 捲到底 → 最後一列「登出」整列在選單可視範圍內、點得到
#   ③ 高視窗 1440×1400 → 選單整份放得下，不出現捲動


def t_acct_menu_scroll_1017(b, base, code):
    import urllib.request
    T = "帳號選單捲動1017"
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    c = None
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
        c = b.new_context(viewport={"width": 1440, "height": 700})
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        pg.evaluate("() => TwAccount.login()")
        pg.wait_for_selector("#acctGo", state="visible", timeout=6000)
        with pg.expect_popup() as pi:
            pg.click("#acctGo")
        pop = pi.value
        pop.wait_for_selector("#as-andy", timeout=8000); pop.click("#as-andy")
        if not ok(f"{T}：站主登入", bool(wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000))):
            return
        pg.wait_for_timeout(600)

        M = """() => { const m = document.getElementById('acctMenu'); if (!m || m.hidden) return null; const r = m.getBoundingClientRect();
            return { bot: r.bottom, ih: innerHeight, sh: m.scrollHeight, ch: m.clientHeight, oy: getComputedStyle(m).overflowY }; }"""
        pg.click("#acctBtn"); pg.wait_for_timeout(400)
        st = pg.evaluate(M)
        ok(f"{T}：矮視窗（700）→ 選單底邊在視窗內、內容比選單高、可捲動", bool(st) and st["bot"] <= st["ih"] and st["sh"] > st["ch"] + 20 and st["oy"] == "auto", st)
        pg.evaluate("() => { const m = document.getElementById('acctMenu'); m.scrollTop = m.scrollHeight; }"); pg.wait_for_timeout(200)
        st = pg.evaluate("""() => { const m = document.getElementById('acctMenu'), l = m.querySelector('[data-a=logout]'); if (!l) return null;
            const a = m.getBoundingClientRect(), r = l.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return { t: l.textContent.trim(), inside: r.top >= a.top - 1 && r.bottom <= a.bottom + 1, hit: !!h && l.contains(h) }; }""")
        ok(f"{T}：捲到底 →「登出」整列看得到、點得到", bool(st) and st["t"] == "登出" and st["inside"] and st["hit"], st)
        shots = os.environ.get("TW_ACCT_SHOT")
        if shots:
            pg.evaluate("() => { document.getElementById('acctMenu').scrollTop = 120; }"); pg.wait_for_timeout(150)
            pg.screenshot(path=shots)
        pg.keyboard.press("Escape"); pg.mouse.click(700, 600); pg.wait_for_timeout(200)
        pg.set_viewport_size({"width": 1440, "height": 1400}); pg.wait_for_timeout(300)
        pg.click("#acctBtn"); pg.wait_for_timeout(400)
        st = pg.evaluate(M)
        ok(f"{T}：高視窗（1400）→ 整份放得下，不出現捲動", bool(st) and st["sh"] <= st["ch"] + 1 and st["bot"] <= st["ih"], st)
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
    finally:
        if c:
            c.close()
        dev.terminate()


register("帳號選單捲動1017", lambda pg, b, base, code: t_acct_menu_scroll_1017(b, base, code))
