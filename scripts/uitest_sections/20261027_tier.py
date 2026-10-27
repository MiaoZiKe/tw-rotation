# 驗收段落「體驗額度1027」（site/grants.js 的 14 天體驗額度橫幅＋#pricing 價格頁）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用，不要 import _uitest。
# Andy 2026-10-27 拍板（docs/marketing/tier_plan_1027.md）：新會員送 14 天體驗額度；Pro 照樣標價。
# 假 Worker（page.route）→ 新帳號登入 → 總覽橫幅寫「體驗額度」「還剩 14 天」「不含」清單 → 用 3D 一次（TwGrants.use，打 /v1/grants/hit）
# 次數 10→9 → 價格頁 Plus 與 Pro 都有價格。1440 與 390 各一次，並截圖。
import json as _t27_json
import time as _t27_time

_T27_API = "https://tier1027.example.test"
_T27_SHOTS = "/tmp/claude-0/-home-user-tw-rotation/5cb9df1a-365b-5e58-9994-2ccda431af9a/scratchpad"


def t_tier_1027(b, base, code):
    T = "體驗額度1027"
    errs = []
    now = int(_t27_time.time() * 1000)
    for W in (1440, 390):
        mob = W <= 640
        st = {"left": 10, "hit": 0}

        def handle(route, _rq=None, st=st):
            req = route.request
            path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
            if req.method == "OPTIONS":
                return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
            out = {}
            if path == "/v1/me":
                out = {"user": {"email": "new@example.com", "name": "新會員", "admin": False, "owner": False}}
            elif path == "/v1/perm/me":
                out = {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {}, "lims": {}, "dq": None}
            elif path == "/v1/grants/public":
                out = {"now": now, "promo": [], "welcome": []}
            elif path == "/v1/grants/me":
                out = {"now": now, "today": {}, "grants": [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": now, "end": now + 14 * 86400000 - 1000, "per": "day",
                                                         "feats": {"ind.3d": {"max": 10, "used": 10 - st["left"], "left": st["left"]}, "ind.rel": {"max": 10, "used": 0, "left": 10}}}]}
            elif path == "/v1/grants/hit":
                st["hit"] += 1
                st["left"] -= 1
                out = {"ok": True, "gid": "welcome", "left": st["left"]}
            elif path == "/v1/plans/public":
                out = {"plans": [
                    {"id": "guest", "name": "訪客", "feats": {}, "lims": {}, "builtin": True, "price": 0, "period": "month"},
                    {"id": "free", "name": "註冊會員", "feats": {}, "lims": {}, "builtin": True, "price": 0, "period": "month"},
                    {"id": "plus", "name": "Plus", "feats": {}, "lims": {}, "builtin": False, "price": 299, "price_year": 2990, "period": "month"},
                    {"id": "pro", "name": "Pro", "feats": {}, "lims": {}, "builtin": False, "price": 549, "price_year": 5490, "period": "month"}]}
            elif path == "/v1/billing/me":
                out = {"plan": "free", "planName": "註冊會員", "paid": False, "canRefund": False, "refundWhy": "not_paid", "refundDays": 7}
            route.fulfill(status=200, body=_t27_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

        c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _t27_json.dumps({"api": _T27_API}) + ";"
                          "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        c.route(_T27_API + "/**", handle)
        pg = c.new_page(); pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        a = pg.get_by_role("button", name="同意並繼續")
        if a.count() and a.first.is_visible():
            a.first.click(); pg.wait_for_timeout(300)
        got = wait_until(pg, "() => { const e = document.getElementById('grantBar'); return !!e && !e.hidden && /體驗額度/.test(e.textContent); }", 15000)
        txt = pg.evaluate("() => (document.getElementById('grantBar') || {}).textContent || ''")
        ok(f"{T}（{W}）新帳號登入 → 總覽橫幅寫「體驗額度」、還剩 14 天、列出「不含」清單、不含「免費試用」字樣",
           bool(got) and "還剩 14 天" in txt and "不含" in txt and "選股名單" in txt and "免費試用" not in txt and "最後機會" not in txt, txt[:200])
        if W == 1440 or True:
            pg.screenshot(path=f"{_T27_SHOTS}/tier_trial_banner_{W}.png", clip={"x": 0, "y": 0, "width": W, "height": 420})
        # 用 3D 一次：次數遞減（打伺服器 /v1/grants/hit，前端剩餘次數 10 → 9）
        l0 = pg.evaluate("() => window.TwGrants.left('ind.3d')")
        pg.evaluate("() => window.TwGrants.use('ind.3d', 'c.test')")
        done = wait_until(pg, "() => window.TwGrants.left('ind.3d') === 9", 4000)
        ok(f"{T}（{W}）用 3D 一次 → 體驗剩餘 {l0} → 9、伺服器收到 1 次 hit", bool(done) and l0 == 10 and st["hit"] == 1, [l0, st])
        # 明細對話框
        pg.click("#grantBar .gb-t")
        dlg = wait_until(pg, "() => !!document.getElementById('grantRules') && /不含/.test(document.getElementById('grantRules').textContent)", 3000)
        ok(f"{T}（{W}）點橫幅 → 明細對話框列出每天次數與「不含」", bool(dlg), pg.evaluate("() => (document.getElementById('grantRules')||{}).textContent||''")[:120])
        pg.keyboard.press("Escape")
        # 價格頁：Plus 與 Pro 都有價格
        pg.evaluate("() => { location.hash = '#pricing'; }")
        wait_until(pg, "() => { const v = document.getElementById('v-pricing'); return !!v && /549/.test(v.textContent) && /299/.test(v.textContent); }", 12000)
        body = pg.evaluate("() => (document.getElementById('v-pricing') || document.body).textContent")
        ok(f"{T}（{W}）價格頁 Plus 299 與 Pro 549 都有標價", "299" in body and "549" in body, body[:160])
        pg.screenshot(path=f"{_T27_SHOTS}/tier_pricing_{W}.png", full_page=False)
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


register("體驗額度1027", lambda pg, b, base, code: t_tier_1027(b, base, code))
