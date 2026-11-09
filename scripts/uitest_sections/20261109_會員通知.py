# 驗收段落「會員通知1109」（site/mnotice.js＋notices.js 鈴鐺；後端 workers/account-api 的會員通知區塊）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_free_port、ROOT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-09：「你發放的那一刻，會員伺服器幫他記一則『你獲得了○○體驗，到期 ○/○』……給他多的福祿都要跳出」。
# 用本機真的 account-api（devserver.mjs，同一支 worker.js）：
#   Bob 登入 → Andy（管理者）真的打 /v1/admin/grants/issue 發體驗給 Bob → Bob 重新整理：跳小視窗、鈴鐺多一則「會員權益」未讀
#   → 按「知道了」→ 視窗關、紅點少 1、伺服器未讀 0 → 重新整理不再跳、鈴鐺那則變已讀。1440 與 390 各一次（390 用同一個權杖）。
#   另一個情境：後端沒有 /v1/notices/mine（攔成 404）→ 不跳、不出網頁錯誤。
# 截圖：環境變數 TW_MN_SHOT＝資料夾 → 存 pop_1440.png、bell_1440.png、pop_390.png、bell_390.png。
import json as _mn_json

_MN_CORS = {"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST, GET, OPTIONS"}
_MN_INIT = "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}"


def _mn_overlap(pg, sel_a, sel_b):
    return pg.evaluate("""([a, b]) => { const A = document.querySelector(a), B = document.querySelector(b); if (!A || !B) return null;
      const r = A.getBoundingClientRect(), s = B.getBoundingClientRect();
      return !(r.right <= s.left || s.right <= r.left || r.bottom <= s.top || s.bottom <= r.top); }""", [sel_a, sel_b])


def t_member_notices_1109(b, base):
    T = "會員通知1109"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    shot = os.environ.get("TW_MN_SHOT")
    over = "window.TW_ACCOUNT_OVERRIDE = " + _mn_json.dumps({"api": api}) + ";"
    try:
        up = False
        for _ in range(100):
            try:
                up = _mn_json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api 起得來", up):
            return

        def ctx(W, extra="", block404=False):
            mob = W <= 640
            c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
            c.add_init_script(over + _MN_INIT + extra)
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            if block404:
                c.route("**/v1/notices/mine", lambda r: r.fulfill(status=204, headers=_MN_CORS, body="") if r.request.method == "OPTIONS"
                        else r.fulfill(status=404, content_type="application/json", headers=_MN_CORS, body='{"error":"not_found"}'))
            ctxs.append(c)
            pg = c.new_page()
            pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
            return c, pg

        def login(pg, who):
            pg.goto(base + "#season", wait_until="domcontentloaded")
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

        acall = lambda pg, path, body: pg.evaluate("([p, b]) => TwAccount.call(p, b)", [path, body])  # noqa: E731
        dot = lambda pg: pg.evaluate("() => { const d = document.getElementById('ntDot'); return d && !d.hidden ? +d.textContent : 0; }")  # noqa: E731

        # Bob 先登入（沒登入過的人發不了體驗）
        cb, bob = ctx(1440)
        ok(f"{T}：Bob 登入", login(bob, "bob"))
        wait_until(bob, "() => !!window.TwMemberNotes", 5000)
        bob.wait_for_timeout(1500)
        ok(f"{T}：登入時沒有任何會員通知 → 不跳視窗", not bob.evaluate("() => !!document.getElementById('mnPop') && !document.getElementById('subDlg').hidden"))
        tok = bob.evaluate("() => localStorage.getItem('tw.acct.tok')")
        usr = bob.evaluate("() => localStorage.getItem('tw.acct.user')")
        # Andy 發體驗
        ca, andy = ctx(1440)
        ok(f"{T}：Andy 登入", login(andy, "andy"))
        defs = acall(andy, "/v1/admin/grants/defs/list", {})
        w = [d for d in (defs or {}).get("defs", []) if d.get("id") == "welcome"]
        if not (w and w[0].get("on")):
            acall(andy, "/v1/admin/grants/defs/put", {"id": "welcome", "kind": "welcome", "name": "新會員體驗", "feats": {"stock.draw": 3}, "per": "day", "days": 14, "on": True})
        r = acall(andy, "/v1/admin/grants/issue", {"email": "bob@example.com", "gid": "welcome"})
        ok(f"{T}：管理者發放體驗成功", r and r.get("_s") == 200 and r.get("ok"), r)

        for W in (1440, 390):
            if W == 1440:
                pg = bob
                d0 = dot(pg)
                pg.reload(wait_until="domcontentloaded")
            else:
                r = acall(andy, "/v1/admin/grants/issue", {"email": "bob@example.com", "gid": "welcome"})   # 再發一次（重新起算）給手機那輪看
                _c, pg = ctx(390, "try{localStorage.setItem('tw.acct.tok'," + _mn_json.dumps(tok) + ");localStorage.setItem('tw.acct.user'," + _mn_json.dumps(usr) + ")}catch(e){}")
                pg.goto(base + "#season", wait_until="domcontentloaded")
                d0 = None
            # 新會員的「歡迎加入」訊息框若先跳：會員通知要讓位（不疊在一起），關掉歡迎框之後才跳
            popped = None
            for _ in range(40):
                if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
                    stacked = pg.evaluate("() => { const d = document.getElementById('subDlg'); return !!d && !d.hidden && !!d.querySelector('#mnPop'); }")
                    pg.wait_for_timeout(900)
                    stacked2 = pg.evaluate("() => { const d = document.getElementById('subDlg'); return !!d && !d.hidden && !!d.querySelector('#mnPop'); }")
                    ok(f"{T}（{W}）歡迎框開著時會員通知不疊上去", not stacked2, [stacked, stacked2])
                    pg.click("#pwOv .pw-x")
                    pg.wait_for_timeout(300)
                if pg.evaluate("() => { const d = document.getElementById('subDlg'); return !!d && !d.hidden && !!d.querySelector('#mnPop'); }"):
                    pg.wait_for_timeout(600)
                    if not pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
                        popped = True
                        break
                pg.wait_for_timeout(500)
            txt = pg.evaluate("() => (document.getElementById('mnPop') || {}).innerText || ''")
            ok(f"{T}（{W}）有未讀 → 跳小視窗，寫出體驗名稱與到期日", bool(popped) and "新會員體驗" in txt and "到期" in txt, txt[:200])
            ok(f"{T}（{W}）視窗有「知道了」鈕、標題與按鈕不重疊", pg.is_visible("#mnOk") and _mn_overlap(pg, "#mnPop h3", "#mnOk") is False)
            wait_until(pg, "() => (TwNotices.list() || []).some(n => n.kind === 'gift')", 5000)
            n_gift = pg.evaluate("() => TwNotices.list().filter(n => n.kind === 'gift' && !n.read).length")
            ok(f"{T}（{W}）鈴鐺清單多了「會員權益」未讀", n_gift >= 1, n_gift)
            if d0 is not None:
                d1 = dot(pg)
                ok(f"{T}（{W}）紅點數 +1（{d0}→{d1}）", d1 == d0 + 1, [d0, d1])
            if shot:
                Path(shot).mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=str(Path(shot) / f"pop_{W}.png"))
            before = dot(pg)
            pg.click("#mnOk")
            closed = wait_until(pg, "() => document.getElementById('subDlg').hidden", 3000)
            srv = wait_until(pg, "async () => { const j = await TwAccount.call('/v1/notices/mine', {}); return j && j._s === 200 && j.unread === 0; }", 5000)
            after = dot(pg)
            ok(f"{T}（{W}）按「知道了」→ 視窗關、伺服器未讀 0、紅點少（{before}→{after}）", bool(closed) and bool(srv) and after < before, [before, after])
            # 鈴鐺下拉看得到、已讀
            pg.click("#ntBell")
            wait_until(pg, "() => { const d = document.getElementById('ntDrop'); return d && !d.hidden && !!d.querySelector('.ntkind.k-gift'); }", 4000)
            it = pg.evaluate("() => { const k = document.querySelector('#ntDrop .ntkind.k-gift'); const it = k && k.closest('.ntitem'); return it ? { t: it.innerText, u: it.classList.contains('unread') } : null; }")
            ok(f"{T}（{W}）鈴鐺下拉有「會員權益」那則、已讀", it and "會員權益" in it["t"] and not it["u"], it)
            if shot:
                pg.screenshot(path=str(Path(shot) / f"bell_{W}.png"))
            # 重新整理不再跳
            pg.reload(wait_until="domcontentloaded")
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.user()) && !!window.TwMemberNotes", 10000)
            pg.wait_for_timeout(3000)
            again = pg.evaluate("() => { const d = document.getElementById('subDlg'); return !!d && !d.hidden && !!d.querySelector('#mnPop'); }")
            ok(f"{T}（{W}）重新整理後不再跳", not again)
            if W == 390:
                pg.close()

        # 舊後端：/v1/notices/mine 回 404 → 安靜略過
        c4, p4 = ctx(1440, "try{localStorage.setItem('tw.acct.tok'," + _mn_json.dumps(tok) + ");localStorage.setItem('tw.acct.user'," + _mn_json.dumps(usr) + ")}catch(e){}", block404=True)
        acall(andy, "/v1/admin/grants/issue", {"email": "bob@example.com", "gid": "welcome"})   # 伺服器端其實有未讀，但前端拿到 404
        p4.goto(base + "#season", wait_until="domcontentloaded")
        wait_until(p4, "() => !!(window.TwAccount && TwAccount.user()) && !!window.TwMemberNotes", 10000)
        p4.wait_for_timeout(3000)
        st = p4.evaluate("() => ({ pop: !!document.getElementById('mnPop'), n: TwMemberNotes.unread(), user: !!TwAccount.user() })")
        ok(f"{T}：後端沒有這個端點（404）→ 不跳、不登出、沒有未讀", not st["pop"] and st["n"] == 0 and st["user"], st)
        ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:3])
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("會員通知1109", lambda pg, b, base, code: t_member_notices_1109(b, base))
