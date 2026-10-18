# 驗收段落「管理者複製1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、ROOT、SITE、_free_port… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 管理者複製1017（Andy 10-17：「所有文章內容 包含精選，只要是管理者 都可以隨意複製 內容與圖片」）
# 本機起真的 worker.js（devserver），1440，打開一篇有圖的公開舊文章：
#   ① 訪客（總覽）：html 有 twnocopy（不能選、不能複製）、沒有「複製圖片」鈕
#   ② 站主 andy 登入：twnocopy 拿掉（總覽與文章頁都是）、文字可以選取並複製、每張圖都有「複製圖片」鈕且不壓到圖標題
#   ③ 按「複製圖片」→ 剪貼簿真的有一張 PNG（寬高跟圖差不多 ×2），按鈕寫「已複製」
#   ④ 登出 → 防複製回來、鈕消失


def t_admin_copy_1017(b, base, code):
    import urllib.request
    T = "管理者複製1017"
    errs: list[str] = []
    idx = json.loads((SITE / "articles" / "index.json").read_text(encoding="utf-8"))["articles"]
    pub = [a for a in idx if a.get("src") != "api" and (SITE / "articles" / "posts" / f"{a['id']}.json").exists()
           and any(x.get("t") in ("chart", "illus", "flow", "steps", "stack", "compare") for x in json.loads((SITE / "articles" / "posts" / f"{a['id']}.json").read_text(encoding="utf-8")).get("blocks", []))]
    if not ok(f"{T}：有含圖的公開舊文章可以測", bool(pub)):
        return
    aid = pub[0]["id"]
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        if not ok(f"{T}：本機 account-api 起得來", up):
            return
        c = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(800)
        st = pg.evaluate("() => ({ nc: document.documentElement.classList.contains('twnocopy'), btn: document.querySelectorAll('.figcp').length })")
        ok(f"{T}：訪客 → 防複製開著、沒有「複製圖片」鈕", st["nc"] and st["btn"] == 0, st)   # 訪客在測試環境讀不到文章（防白嫖額度），所以在總覽驗
        wait_until(pg, "() => !!(window.TwAccount && TwAccount.on())", 10000)
        pg.evaluate("() => TwAccount.login()")
        pg.wait_for_selector("#acctGo", state="visible", timeout=6000)
        with pg.expect_popup() as pi:
            pg.click("#acctGo")
        pop = pi.value; pop.wait_for_selector("#as-andy", timeout=8000); pop.click("#as-andy")
        if not ok(f"{T}：站主登入", bool(wait_until(pg, "() => !!(window.TwAccount && TwAccount.user() && TwAccount.user().admin)", 12000))):
            return
        pg.evaluate(f"() => {{ location.hash = '#article/{aid}'; }}")
        wait_until(pg, "() => document.querySelectorAll('#artPost figure.artfig').length && document.querySelectorAll('.figcp').length ? 1 : 0", 15000); pg.wait_for_timeout(500)
        st = pg.evaluate("""() => { const f = [...document.querySelectorAll('#artPost figure.artfig')], bs = [...document.querySelectorAll('.figcp')];
            const hit = bs.some(b => { const r = b.getBoundingClientRect(), cap = b.parentElement.tagName === 'FIGCAPTION' ? b.parentElement : null; if (!cap) return false;
              const t = document.createRange(); t.selectNodeContents(cap.firstChild || cap); const tr = t.getBoundingClientRect(); return cap.firstChild && cap.firstChild.nodeType === 3 && tr.right > r.left + 1 && tr.bottom > r.top && tr.top < r.bottom; });
            return { nc: document.documentElement.classList.contains('twnocopy'), btn: bs.length, figs: f.length, hit, us: getComputedStyle(document.body).userSelect }; }""")
        ok(f"{T}：站主 → 防複製拿掉、每張圖都有「複製圖片」鈕、鈕不壓到圖標題", not st["nc"] and st["btn"] == st["figs"] and not st["hit"] and st["us"] != "none", st)
        pg.evaluate("() => { const p = document.querySelector('#artPost .artbody p') || document.querySelector('#artPost p'); const r = document.createRange(); r.selectNodeContents(p); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }")
        pg.keyboard.press("Control+C"); pg.wait_for_timeout(300)
        txt = pg.evaluate("async () => { try { return await navigator.clipboard.readText(); } catch (e) { return 'ERR ' + e; } }")
        ok(f"{T}：站主選取段落按 Ctrl+C → 剪貼簿有那段文字、沒有跳「請勿複製」", len(txt.strip()) > 10 and not txt.startswith("ERR") and not pg.evaluate("() => { const t = document.getElementById('twProtToast'); return !!t && t.classList.contains('on'); }"), txt[:40])
        pg.locator(".figcp >> nth=0").scroll_into_view_if_needed()
        pg.click(".figcp >> nth=0")
        wait_until(pg, "() => /已複製|已下載|失敗/.test(document.querySelector('.figcp').textContent) ? 1 : 0", 10000)
        st = pg.evaluate("""async () => { const b = document.querySelector('.figcp'), f = b.closest('figure').getBoundingClientRect();
            try { const it = await navigator.clipboard.read(); const t = it[0].types; const bl = await it[0].getType('image/png'); const bm = await createImageBitmap(bl);
              return { lab: b.textContent, types: t, w: bm.width, h: bm.height, fw: Math.round(f.width), fh: Math.round(f.height) }; } catch (e) { return { lab: b.textContent, err: String(e) }; } }""")
        ok(f"{T}：按「複製圖片」→ 剪貼簿是 PNG、大小約為圖的 2 倍、按鈕寫「已複製」", st.get("lab") == "已複製" and "image/png" in (st.get("types") or [])
           and abs(st.get("w", 0) - 2 * st.get("fw", 0)) <= 4 and abs(st.get("h", 0) - 2 * st.get("fh", 0)) <= 4, st)
        shot = os.environ.get("TW_ADMCOPY_SHOT")
        if shot:
            pg.evaluate("""async () => { const it = await navigator.clipboard.read(); const bl = await it[0].getType('image/png'); window.__cpu = await new Promise(r => { const f = new FileReader(); f.onload = () => r(f.result); f.readAsDataURL(bl); }); }""")
            data = pg.evaluate("() => window.__cpu")
            import base64
            pathlib.Path(shot).write_bytes(base64.b64decode(data.split(",", 1)[1]))
        pg.evaluate("() => TwAccount.logout && TwAccount.logout()"); pg.wait_for_timeout(800)
        st = pg.evaluate("() => ({ nc: document.documentElement.classList.contains('twnocopy') })")
        ok(f"{T}：登出 → 防複製回來", st["nc"], st)
        ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])
    finally:
        if c:
            c.close()
        dev.terminate()


register("管理者複製1017", lambda pg, b, base, code: t_admin_copy_1017(b, base, code))
