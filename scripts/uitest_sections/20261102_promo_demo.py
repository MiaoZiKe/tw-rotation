# 驗收段落「活動展示頁1102」—— 預覽版 #promo-demo（三顆展示鈕）＋邀請示範視窗＋公告
# 用真的 /preview/member-invite/ 子路徑起一台本機伺服器（不用 replaceState），比比圖等相對路徑才會跟正式預覽一樣。
# flake8: noqa

_PDM_OVERLAP = """() => { const o = document.getElementById('pwOv'); if (!o) return { bad: ['沒有訊息框'] };
  const sel = ['.pw-x', '.pw-bibi', '.pw-title', '.pw-sub', '.pw-list li:nth-child(1)', '.pw-list li:nth-child(2)', '.pw-list li:nth-child(3)', '.pw-btns .pw-pri', '.pw-btns button:nth-child(2)', '.pw-off', '.pw-tag'];
  const R = sel.map((s) => [s, o.querySelector(s)]).filter((x) => x[1]).map(([s, e]) => [s, e.getBoundingClientRect()]); const bad = [];
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) { const a = R[i][1], b = R[j][1];
    if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) bad.push(R[i][0] + ' x ' + R[j][0]); }
  const im = o.querySelector('.pw-bibi'); if (!im || !im.complete || !im.naturalWidth) bad.push('比比圖沒載入');
  return { n: R.length, bad }; }"""
_PDM_INV = """() => { const d = document.getElementById('invDlg'); if (!d || d.hidden) return null; const q = (s) => d.querySelector(s);
  const bx = d.querySelector('.box').getBoundingClientRect();
  return { text: d.innerText, wishForm: !!q('#invWf') && !!q('#invWt'), code: (q('#invCode') || {}).textContent, sw: document.documentElement.scrollWidth, vw: innerWidth,
           box: { l: bx.left, r: bx.right, t: bx.top, b: bx.bottom }, vh: innerHeight }; }"""


def _pdm_ctx(b, W):
    c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    return c


def t_promo_demo_1102(b, base, code):
    import os, threading, tempfile
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    T = "活動展示頁1102"
    errs: list[str] = []
    shot = os.environ.get("TW_PROMO_SHOT")
    site = os.path.join(os.getcwd(), "site")
    tmp = tempfile.mkdtemp()
    os.makedirs(os.path.join(tmp, "preview"))
    os.symlink(site, os.path.join(tmp, "preview", "member-invite"))

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=tmp, **k)
        def log_message(self, *a): pass
        def end_headers(self): self.send_header("Cache-Control", "no-store"); super().end_headers()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/preview/member-invite/"
    try:
        for W in (1440, 390):
            c = _pdm_ctx(b, W); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            J = pg.evaluate
            pg.goto(url + "#promo-demo", wait_until="load")
            agree = pg.get_by_role("button", name="同意並繼續")
            wait_until(pg, "() => !!document.querySelector('#v-promodemo .pd-b')", 20000)
            if agree.count() and agree.first.is_visible():
                agree.first.click(); pg.wait_for_timeout(300)
            ok(f"{T}（{W}）展示頁出現三顆大按鈕", pg.locator("#v-promodemo .pd-b").count() == 3)
            hs = J("() => [...document.querySelectorAll('#v-promodemo .pd-b')].map(b => Math.round(b.getBoundingClientRect().height))")
            ok(f"{T}（{W}）按鈕夠大（≥48px）{hs}", all(h >= 48 for h in hs))
            if shot:
                os.makedirs(shot, exist_ok=True); pg.screenshot(path=f"{shot}/demo_page_{W}.png")
            # 預覽版首頁會自己跳公告；展示頁不在首頁，所以此刻不該有
            ok(f"{T}（{W}）展示頁上不自動跳公告", not J("() => !!document.getElementById('pwOv')"))
            # 1) 公告
            pg.locator("#v-promodemo .pd-b").nth(0).click()
            wait_until(pg, "() => !!document.getElementById('pwOv')", 8000); pg.wait_for_timeout(900)
            ok(f"{T}（{W}）按「看活動公告」→ 公告出現", J("() => !!document.getElementById('pwOv')"))
            ok(f"{T}（{W}）比比圖正常載入", J("() => { const i = document.querySelector('#pwOv .pw-bibi'); return !!i && i.complete && i.naturalWidth > 0; }"))
            fr = 0; bad = []
            for _ in range(20):
                r = J(_PDM_OVERLAP); fr += 1; bad += r["bad"]; pg.wait_for_timeout(100)
            ok(f"{T}（{W}）重疊檢查：程式 {fr} 幀 {len(bad)} 筆", not bad, bad[:3])
            if shot:
                pg.screenshot(path=f"{shot}/demo_promo_{W}.png")
            pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
            ok(f"{T}（{W}）公告可關閉", not J("() => !!document.getElementById('pwOv')"))
            ok(f"{T}（{W}）關閉後仍在展示頁", "#promo-demo" in pg.url)
            # 2) 邀請示範視窗
            pg.locator("#v-promodemo .pd-b").nth(1).click(); wait_until(pg, "() => { const d = document.getElementById('invDlg'); return d && !d.hidden; }", 6000)
            pg.wait_for_timeout(500)
            s = J(_PDM_INV)
            ok(f"{T}（{W}）邀請視窗出現", bool(s), s)
            if s:
                ok(f"{T}（{W}）邀請碼 DEMO1234", s["code"] == "DEMO1234", s["code"])
                ok(f"{T}（{W}）已邀請 3 人", "已邀請 3 人" in s["text"], s["text"][:200])
                ok(f"{T}（{W}）再邀 2 人升級 Pro", "再邀 2 人" in s["text"])
                ok(f"{T}（{W}）Pro 期內顯示許願表單", s["wishForm"])
                ok(f"{T}（{W}）邀請視窗不橫向溢出、在視窗內", s["sw"] <= s["vw"] + 1 and s["box"]["l"] >= -1 and s["box"]["r"] <= s["vw"] + 1, s["box"])
            if shot:
                pg.screenshot(path=f"{shot}/demo_invite_{W}.png")
            # 許願送出只模擬
            pg.fill("#invWf", "示範功能"); pg.fill("#invWt", "這是示範用的願望內容"); pg.click("#invWgo"); pg.wait_for_timeout(500)
            ok(f"{T}（{W}）示範送願望只模擬、不打 API", "示範模式" in J("() => document.getElementById('invWmsg') ? document.getElementById('invWmsg').textContent : ''"))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(400)
            # 3) 問卷
            pg.locator("#v-promodemo .pd-b").nth(2).click(); pg.wait_for_timeout(500)
            txt = J("() => (document.getElementById('pdMsg') || {}).textContent || ''")
            has_survey = J("() => !!(window.TwSurvey && window.TwSurvey.open)")
            ok(f"{T}（{W}）問卷鈕：{'打開問卷' if has_survey else '顯示製作中文案'}", has_survey or "問卷製作中" in txt, txt)
            if shot:
                pg.screenshot(path=f"{shot}/demo_survey_{W}.png")
            ok(f"{T}（{W}）展示頁不橫向溢出", J("() => document.documentElement.scrollWidth <= innerWidth + 1"))
            # 4) 預覽首頁（真子路徑）直接跳公告、不登入
            pg.goto(url + "#overview", wait_until="load"); pg.reload(wait_until="load")
            wait_until(pg, "() => !!document.getElementById('pwOv')", 15000); pg.wait_for_timeout(500)
            ok(f"{T}（{W}）預覽首頁未登入直接跳公告（真子路徑）", J("() => !!document.getElementById('pwOv')") and J(_PDM_OVERLAP)["bad"] == [], J(_PDM_OVERLAP))
            if shot:
                pg.screenshot(path=f"{shot}/preview_home_{W}.png")
            c.close()
    finally:
        srv.shutdown()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("活動展示頁1102", lambda pg, b, base, code: t_promo_demo_1102(b, base, code))
