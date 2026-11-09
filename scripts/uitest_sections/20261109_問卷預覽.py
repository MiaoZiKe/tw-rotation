# 驗收段落「問卷預覽1109」：預覽版不再強制跳問卷／歡迎框；已選選項是實心主色；兩框不同時疊
# flake8: noqa


def t_survey_preview_1109(b, base, code):
    import os, threading, tempfile
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    T = "問卷預覽1109"
    errs: list[str] = []
    site = os.path.join(os.getcwd(), "site")
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "preview")); os.symlink(site, os.path.join(tmp, "preview", "t"))

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=tmp, **k)
        def log_message(self, *a): pass
        def end_headers(self): self.send_header("Cache-Control", "no-store"); super().end_headers()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/preview/t/"
    SV = "() => !!document.querySelector('#svOv .svbox')"
    PW = "() => !!document.getElementById('pwOv')"
    shot = os.environ.get("TW_SV_SHOT")
    try:
        def mk(W, theme="dark"):
            c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900})
            c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme','%s')}catch(e){}" % theme)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            return c
        c = mk(1440); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url, wait_until="load"); pg.wait_for_timeout(4500)
        agree = pg.get_by_role("button", name="同意並繼續")
        ok(f"{T}：預覽路徑不帶參數 → 問卷與歡迎框都不出現", not pg.evaluate(SV) and not pg.evaluate(PW))
        c.close()
        # ?promo=test 只出歡迎框；兩個參數一起帶：同一時間最多一個，問卷先、關掉後歡迎框才出現
        c = mk(1440); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "?promo=test#overview", wait_until="load"); wait_until(pg, PW, 10000)
        ok(f"{T}：?promo=test → 只出歡迎框，沒有問卷", pg.evaluate(PW) and not pg.evaluate(SV))
        c.close()
        c = mk(1440); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url + "?survey=test&promo=test#overview", wait_until="load"); wait_until(pg, SV, 8000)
        both = []
        for _ in range(12):
            pg.wait_for_timeout(500); both.append(pg.evaluate(SV) and pg.evaluate(PW))
        ok(f"{T}：兩個參數一起帶 → 問卷開著時歡迎框不疊上來", pg.evaluate(SV) and not pg.evaluate(PW) and not any(both))
        pg.click("#svLater"); wait_until(pg, PW, 8000)
        ok(f"{T}：關掉問卷後歡迎框才出現（且問卷已不在）", pg.evaluate(PW) and not pg.evaluate(SV))
        c.close()
        for theme in ("dark", "light"):
            for W in (1440, 390):
                c = mk(W, theme); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(url + "?survey=test#overview", wait_until="load")
                wait_until(pg, SV, 8000); pg.wait_for_timeout(1500)
                ok(f"{T}（{theme}/{W}）?survey=test → 問卷出現，歡迎框不疊上來", pg.evaluate(SV) and not pg.evaluate(PW))
                pg.click("[data-sat='5']"); pg.click("#svNext")
                par = pg.locator(".svpar").first
                bg0 = par.evaluate("e => getComputedStyle(e).backgroundColor")
                par.click(); pg.wait_for_timeout(150)
                bg1 = pg.locator(".svpar").first.evaluate("e => getComputedStyle(e).backgroundColor")
                cyan = pg.evaluate("() => { const d = document.createElement('i'); d.style.color = getComputedStyle(document.documentElement).getPropertyValue('--cyan'); document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }")
                ok(f"{T}（{theme}/{W}）已選大項＝實心主色底（{bg1}）且與未選（{bg0}）不同", bg1 == cyan and bg1 != bg0)
                if shot:
                    os.makedirs(shot, exist_ok=True); pg.screenshot(path=f"{shot}/q2_{theme}_{W}.png")
                chip = pg.locator(".svchip").first
                if chip.count():
                    chip.click(); pg.wait_for_timeout(150)
                    cb = pg.locator(".svchip.on").first.evaluate("e => getComputedStyle(e).backgroundColor")
                    ok(f"{T}（{theme}/{W}）已選小項膠囊＝實心主色底", cb == cyan, cb)
                c.close()
    finally:
        srv.shutdown()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("問卷預覽1109", lambda pg, b, base, code: t_survey_preview_1109(b, base, code))
