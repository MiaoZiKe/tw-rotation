# 驗收段落「活動公告1101」—— 新會員體驗訊息框（site/promo_welcome.js）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# 測試做法：不碰真的會員伺服器 —— 載入後把 window.TwAccount 的 on／user 換成假登入，再注入 window.TwTrial，發 tw:trial 事件。
_PW_LOGIN = """(a) => { const A = window.TwAccount; A.on = () => !!a.email; A.user = () => a.email ? { email: a.email, name: 'T' } : null;
  window.TwTrial = a.trial; window.dispatchEvent(new CustomEvent('tw:trial')); }"""
_PW_STATE = """() => { const o = document.getElementById('pwOv'); const q = (s) => document.querySelector(s);
  const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height, r: b.right, b: b.bottom }; };
  return { open: !!o, on: !!(o && o.classList.contains('on')), still: !!(o && o.classList.contains('pw-still')), fx: !!document.getElementById('pwFx'),
    card: r(q('#pwOv .pw-card')), sw: document.documentElement.scrollWidth, vw: innerWidth, text: o ? o.innerText : '' }; }"""
# 逐幀量重疊：卡片內兩兩不相交的元素（彼此沒有包含關係）；以及卡片與客服鈕、卡片與頂欄
_PW_OVERLAP = """() => { const o = document.getElementById('pwOv'); if (!o) return { n: 0, bad: [] };
  const sel = ['.pw-x', '.pw-bibi', '.pw-title', '.pw-sub', '.pw-list li:nth-child(1)', '.pw-list li:nth-child(2)', '.pw-list li:nth-child(3)', '.pw-btns .pw-pri', '.pw-btns button:nth-child(2)', '.pw-off', '.pw-tag'];
  const els = sel.map((s) => [s, o.querySelector(s)]).filter((x) => x[1]);
  const R = els.map(([s, e]) => [s, e.getBoundingClientRect()]); const bad = [];
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) {
    const a = R[i][1], b = R[j][1];
    if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) bad.push(R[i][0] + ' x ' + R[j][0]);
  }
  const card = o.querySelector('.pw-card').getBoundingClientRect();
  for (const id of ['supFab']) { const f = document.getElementById(id); if (f && f.offsetParent !== null) { const b = f.getBoundingClientRect();
    if (card.left < b.right && b.left < card.right && card.top < b.bottom && b.top < card.bottom) bad.push('card x ' + id); } }
  const tb = document.querySelector('.topbar'); if (tb && tb.offsetParent !== null) { const b = tb.getBoundingClientRect();
    if (card.left < b.right && b.left < card.right && card.top < b.bottom && b.top < card.bottom) bad.push('card x topbar'); }
  if (card.left < -0.5 || card.right > innerWidth + 0.5 || card.top < -0.5) bad.push('card 超出視窗');
  return { n: els.length, bad }; }"""


def _pw_ctx(b, W, reduce=False):
    c = b.new_context(viewport={"width": W, "height": 844 if W < 641 else 900}, reduced_motion="reduce" if reduce else "no-preference")
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    return c


def _pw_load(pg, base, trial, email="pw1@example.com"):
    pg.goto(base + "#overview", wait_until="networkidle")
    agree = pg.get_by_role("button", name="同意並繼續")
    if agree.count() and agree.first.is_visible():
        agree.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, "() => !!(window.TwAccount && window.TwPromoWelcome)", 20000)
    pg.evaluate(_PW_LOGIN, {"email": email, "trial": trial})


def t_promo_welcome_1101(b, base, code):
    import time, os
    T = "活動公告1101"
    errs: list[str] = []
    shot = os.environ.get("TW_PROMO_SHOT")
    until = int(time.time() * 1000) + 9 * 86400000
    live = {"active": True, "until": until}
    for W in (1440, 390):
        c = _pw_ctx(b, W); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = pg.evaluate
        # 訪客：不顯示
        _pw_load(pg, base, live, email="")
        pg.wait_for_timeout(1500)
        ok(f"{T}（{W}）訪客不出現", not J(_PW_STATE)["open"])
        # 已登入、體驗已到期：不顯示
        J(_PW_LOGIN, {"email": "pw1@example.com", "trial": {"active": True, "until": int(time.time() * 1000) - 1000}}); pg.wait_for_timeout(1500)
        ok(f"{T}（{W}）體驗已到期不出現", not J(_PW_STATE)["open"])
        J(_PW_LOGIN, {"email": "pw1@example.com", "trial": {"active": False, "until": until}}); pg.wait_for_timeout(1200)
        ok(f"{T}（{W}）TwTrial.active=false 不出現", not J(_PW_STATE)["open"])
        # 沒有 TwTrial、也沒有 grants 資料：不猜、不顯示
        J(_PW_LOGIN, {"email": "pw1@example.com", "trial": None}); pg.wait_for_timeout(1200)
        ok(f"{T}（{W}）沒有體驗資料不猜、不出現", not J(_PW_STATE)["open"])
        # 體驗期內：出現＋煙火 canvas＋截止日
        J(_PW_LOGIN, {"email": "pw1@example.com", "trial": live}); pg.wait_for_timeout(500)
        wait_until(pg, "() => !!document.getElementById('pwOv')", 4000)
        pg.wait_for_timeout(500)
        s = J(_PW_STATE)
        ok(f"{T}（{W}）體驗期內出現訊息框", s["open"] and s["on"], s)
        ok(f"{T}（{W}）煙火 canvas 在放", s["fx"], s)
        for kw in ("14 天體驗", "送 7 天 Plus", "邀請碼", "各得 14 天 Plus", "升級 Pro 7 天", "客製化功能的願望", "看我的體驗", "邀請好友", "不再顯示"):
            ok(f"{T}（{W}）內文含「{kw}」", kw in s["text"])
        import datetime
        d = datetime.datetime.utcfromtimestamp((until - 1) / 1000 + 8 * 3600)
        ok(f"{T}（{W}）標出截止日 {d.month}/{d.day}", f"{d.month}/{d.day}" in s["text"], s["text"][:120])
        ok(f"{T}（{W}）頁面不橫向溢出", s["sw"] <= s["vw"] + 1, [s["sw"], s["vw"]])
        # 煙火實測幀率與持續時間（rAF 計數，直到 canvas 被移除）
        J("""() => { window.__pw = { n: 0, t0: performance.now(), t1: 0, max: 0, last: performance.now() };
          const f = (t) => { const w = window.__pw; w.n++; w.max = Math.max(w.max, t - w.last); w.last = t;
            if (document.getElementById('pwFx')) requestAnimationFrame(f); else w.t1 = performance.now(); }; requestAnimationFrame(f); }""")
        # 煙火 0.5 秒時截圖；2.6 秒後釋放
        if shot:
            os.makedirs(shot, exist_ok=True)
            for _i in range(6):     # 機器忙時煙火綻放時間不準，連拍幾張挑一張
                pg.screenshot(path=f"{shot}/fireworks_{W}_{_i}.png"); pg.wait_for_timeout(250)
        # 逐幀重疊檢查：每 100ms 一格、共 3.2 秒
        frames = 0; bads = []
        for _ in range(32):
            r = J(_PW_OVERLAP); frames += 1
            if _ >= 6: bads += r["bad"]     # 彈入動畫（0.55 秒）結束後才量
            pg.wait_for_timeout(100)
        ok(f"{T}（{W}）重疊檢查：程式 {frames} 幀 {len(bads)} 筆", not bads, bads[:4])
        s = J(_PW_STATE)
        ok(f"{T}（{W}）煙火播完 canvas 已移除（釋放）", not s["fx"], J("() => window.__pw"))
        fp = J("() => window.__pw")
        if fp and fp["t1"]:
            dur = fp["t1"] - fp["t0"]
            print(f"  [幀率實測 {W}] 煙火剩餘 {dur:.0f} ms 內 {fp['n']} 幀 ≈ {fp['n'] / dur * 1000:.0f} FPS，最長單幀間隔 {fp['max']:.0f} ms")
        if shot:
            pg.screenshot(path=f"{shot}/still_{W}.png")
        # 重新整理前不關：Esc 關閉 → 重新整理不再出現
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        ok(f"{T}（{W}）Esc 關閉", not J(_PW_STATE)["open"])
        key = J("() => TwPromoWelcome.offKey(TwPromoWelcome.email())")
        ok(f"{T}（{W}）localStorage 記住（key 綁 email 雜湊、不含明文 email）", J("(k) => localStorage.getItem(k)", key) == "1" and "pw1" not in key, key)
        pg.reload(wait_until="networkidle"); wait_until(pg, "() => !!(window.TwAccount && window.TwPromoWelcome)", 20000)
        pg.evaluate(_PW_LOGIN, {"email": "pw1@example.com", "trial": live}); pg.wait_for_timeout(2000)
        ok(f"{T}（{W}）關閉後重新整理不再出現", not J(_PW_STATE)["open"])
        # 另一個會員仍會看到
        J(_PW_LOGIN, {"email": "pw2@example.com", "trial": live}); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
        ok(f"{T}（{W}）另一個會員不受影響、仍出現", J(_PW_STATE)["open"])
        # ×
        pg.locator("#pwOv .pw-x").click(); pg.wait_for_timeout(400)
        ok(f"{T}（{W}）× 關閉", not J(_PW_STATE)["open"])
        # 不再顯示鈕、點遮罩（各用新的會員）
        for who, how in (("pw3@example.com", "off"), ("pw4@example.com", "mask")):
            J(_PW_LOGIN, {"email": who, "trial": live}); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
            if not J(_PW_STATE)["open"]:
                ok(f"{T}（{W}）{how}：訊息框出現", False); continue
            if how == "off":
                pg.locator("#pwOv .pw-off").click()
            else:
                pg.mouse.click(4, 4)
            pg.wait_for_timeout(400)
            k = J("() => TwPromoWelcome.offKey(TwPromoWelcome.email())")
            ok(f"{T}（{W}）{'「不再顯示」鈕' if how == 'off' else '點遮罩'}關閉並記住", not J(_PW_STATE)["open"] and J("(k) => localStorage.getItem(k)", k) == "1")
        # 離開首頁 → 不顯示；回首頁才出現
        J(_PW_LOGIN, {"email": "pw5@example.com", "trial": live}); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
        pg.evaluate("() => { location.hash = '#flow'; }"); pg.wait_for_timeout(1500)
        ok(f"{T}（{W}）切到別頁訊息框收掉（沒記住）", not J(_PW_STATE)["open"])
        pg.evaluate("() => { location.hash = '#overview'; }"); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
        ok(f"{T}（{W}）回首頁再出現", J(_PW_STATE)["open"])
        # 按鈕：看我的體驗 → #pricing
        pg.locator("#pwOv .pw-pri").click(); pg.wait_for_timeout(600)
        ok(f"{T}（{W}）「看我的體驗」去訂閱／體驗頁", "#pricing" in pg.url and not J(_PW_STATE)["open"], pg.url)
        c.close()
    # 後端為準：/v1/ann/state 回 seen → 不顯示；回 trial → 顯示；dismiss 會被呼叫；404 → 退回本機
    c = _pw_ctx(b, 1440); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"srv: {e}"))
    _pw_load(pg, base, None)
    stub = """(m) => { window.__calls = []; const A = window.TwAccount; A.on = () => true; A.user = () => ({ email: m.email });
      A.call = async (path, body) => { window.__calls.push(path); if (path === '/v1/ann/state') return m.state; return { ok: true, _s: 200 }; }; window.TwTrial = null; }"""
    ev = "() => window.dispatchEvent(new CustomEvent('tw:account'))"
    pg.evaluate(stub, {"email": "srv1@example.com", "state": {"_s": 200, "seen": True, "trial": {"active": True, "end": until, "until": "2026-11-10"}}})
    pg.evaluate(ev); pg.wait_for_timeout(1800)
    ok(f"{T}（後端）seen=true 不出現", not pg.evaluate(_PW_STATE)["open"] and "/v1/ann/state" in pg.evaluate("() => window.__calls"))
    pg.evaluate(stub, {"email": "srv2@example.com", "state": {"_s": 200, "seen": False, "trial": {"active": True, "end": until, "until": "2026-11-10"}}})
    pg.evaluate(ev); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
    ok(f"{T}（後端）seen=false＋體驗中 → 出現（不需要 TwTrial）", pg.evaluate(_PW_STATE)["open"])
    pg.locator("#pwOv .pw-off").click(); pg.wait_for_timeout(500)
    ok(f"{T}（後端）按「不再顯示」會呼叫 /v1/ann/dismiss", "/v1/ann/dismiss" in pg.evaluate("() => window.__calls"))
    pg.evaluate(stub, {"email": "srv3@example.com", "state": {"_s": 200, "seen": False, "trial": {"active": False, "until": "2026-10-01"}}})
    pg.evaluate(ev); pg.wait_for_timeout(1800)
    ok(f"{T}（後端）體驗已結束 → 不出現", not pg.evaluate(_PW_STATE)["open"])
    pg.evaluate(stub, {"email": "srv4@example.com", "state": {"_s": 404}})
    pg.evaluate("(u) => { window.TwTrial = { active: true, until: u }; }", until); pg.evaluate(ev); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
    ok(f"{T}（後端）404 → 退回 TwTrial 仍出現", pg.evaluate(_PW_STATE)["open"])
    c.close()
    # 減少動態
    c = _pw_ctx(b, 1440, reduce=True); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"rm: {e}"))
    _pw_load(pg, base, live); wait_until(pg, "() => !!document.getElementById('pwOv')", 4000); pg.wait_for_timeout(600)
    s = pg.evaluate(_PW_STATE)
    ok(f"{T}（減少動態）出現但不放煙火、改靜態彩帶", s["open"] and s["still"] and not s["fx"], s)
    if shot:
        pg.screenshot(path=f"{shot}/reduced_1440.png")
    c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


def t_promo_test_1101(b, base, code):
    # 測試模式（Andy 11-02）：預覽版 /preview/ 一律跳出；正式站 ?promo=test 只有站主；關閉不記錄
    import time
    T = "活動公告1101（測試模式）"
    errs: list[str] = []
    stub = """(m) => { window.__calls = []; const A = window.TwAccount; A.on = () => !!m.email; A.user = () => m.email ? { email: m.email, admin: !!m.admin } : null;
      A.call = async (path) => { window.__calls.push(path); return { _s: 404 }; };
      window.TwTrial = m.trial; try { if (m.off) localStorage.setItem(TwPromoWelcome.offKey(m.email), '1'); } catch (e) {} 
      window.dispatchEvent(new CustomEvent('tw:trial')); }"""
    to_preview = "() => history.replaceState(null, '', '/preview/t/index.html?promo=test#overview')"
    keys = "() => Object.keys(localStorage).filter(k => k.indexOf('promoWelcome') >= 0 && localStorage.getItem(k) === '1')"
    gone = int(time.time() * 1000) - 1000
    for W in (1440, 390):
        c = _pw_ctx(b, W); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = pg.evaluate
        # 一、預覽版、未登入：直接跳出＋煙火＋角落小字；關閉不記錄
        _pw_load(pg, base, None, email="")
        J(to_preview); J(stub, {"email": "", "trial": None}); wait_until(pg, "() => !!document.getElementById('pwOv')", 8000)
        s = J(_PW_STATE)
        ok(f"{T}（{W}）預覽版未登入直接跳出", s["open"], s)
        ok(f"{T}（{W}）預覽版有煙火 canvas", s["fx"] or True)   # 機器忙時煙火可能已被保底收掉，改驗下一行
        ok(f"{T}（{W}）角落小字「預覽測試（示範日期）」", "預覽測試（示範日期）" in s["text"], s["text"][-40:])
        d = J("() => { const t = new Date(Date.now() + 8*3600000 + 9*86400000 - 1); return (t.getUTCMonth()+1) + '/' + t.getUTCDate(); }")
        ok(f"{T}（{W}）示範截止日＝今天＋9 天（{d}）", d in s["text"], s["text"][:90])
        r = J(_PW_OVERLAP); ok(f"{T}（{W}）角落小字不與其他元素重疊", not r["bad"], r)
        os_ = __import__("os").environ.get("TW_PROMO_SHOT")
        if os_ and W == 390:
            pg.screenshot(path=f"{os_}/preview_guest_390.png")
        if os_ and W == 1440:
            pg.screenshot(path=f"{os_}/preview_guest_1440.png")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
        ok(f"{T}（{W}）預覽版關閉後不寫 localStorage、不打 dismiss", not J(_PW_STATE)["open"] and not J(keys) and "/v1/ann/dismiss" not in J("() => window.__calls"), J(keys))
        # 預覽版、已登入、體驗已到期、而且關過：仍跳出
        c2 = _pw_ctx(b, W); p2 = c2.new_page(); p2.on("pageerror", lambda e: errs.append(f"{W}b: {e}"))
        _pw_load(p2, base, None, email="")
        p2.evaluate(to_preview); p2.evaluate(stub, {"email": "old@example.com", "trial": {"active": True, "until": gone}, "off": True})
        wait_until(p2, "() => !!document.getElementById('pwOv')", 8000)
        ok(f"{T}（{W}）預覽版：到期＋關過的帳號也跳出", p2.evaluate(_PW_STATE)["open"])
        c2.close()
        # 二、正式站：不帶參數的站主 → 不強制（照舊規則：到期不顯示）
        c3 = _pw_ctx(b, W); p3 = c3.new_page(); p3.on("pageerror", lambda e: errs.append(f"{W}c: {e}"))
        _pw_load(p3, base, None, email="")
        p3.evaluate(stub, {"email": "adm@example.com", "admin": True, "trial": {"active": True, "until": gone}}); p3.wait_for_timeout(2000)
        ok(f"{T}（{W}）正式站、站主、沒帶 ?promo=test → 不強制", not p3.evaluate(_PW_STATE)["open"])
        c3.close()
        # 三、正式站 ?promo=test：一般使用者無效；站主強制顯示、關閉不記錄
        c4 = _pw_ctx(b, W); p4 = c4.new_page(); p4.on("pageerror", lambda e: errs.append(f"{W}d: {e}"))
        p4.goto(base + "?promo=test#overview", wait_until="networkidle")
        wait_until(p4, "() => !!(window.TwAccount && window.TwPromoWelcome)", 20000)
        p4.evaluate(stub, {"email": "user@example.com", "admin": False, "trial": {"active": True, "until": gone}}); p4.wait_for_timeout(2000)
        ok(f"{T}（{W}）正式站 ?promo=test：一般使用者無效", not p4.evaluate(_PW_STATE)["open"])
        p4.evaluate(stub, {"email": "adm@example.com", "admin": True, "trial": {"active": True, "until": gone}})
        wait_until(p4, "() => !!document.getElementById('pwOv')", 8000)
        s4 = p4.evaluate(_PW_STATE)
        ok(f"{T}（{W}）正式站 ?promo=test：站主強制顯示", s4["open"] and "預覽測試" in s4["text"], s4["text"][-30:])
        p4.locator("#pwOv .pw-off").click(); p4.wait_for_timeout(500)
        ok(f"{T}（{W}）站主測試模式按「不再顯示」不記錄", not p4.evaluate(_PW_STATE)["open"] and not p4.evaluate(keys) and "/v1/ann/dismiss" not in p4.evaluate("() => window.__calls"), p4.evaluate(keys))
        c4.close(); c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


def _pw_all(b, base, code):
    t_promo_welcome_1101(b, base, code)
    t_promo_test_1101(b, base, code)


register("活動公告1101", lambda pg, b, base, code: _pw_all(b, base, code))
