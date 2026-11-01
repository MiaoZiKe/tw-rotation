# 驗收段落「自設提醒上限1102」（site/digest.js、perm.js、grants.js、features.js）
# Andy 2026-11-02：自設提醒條數 Plus 5、Pro 20、新會員體驗期間視同 Plus（5）；每條提醒可勾「網頁通知」「email」。
# 假 Worker（page.route）：伺服器端上限照方案（free 1／體驗仍 1，由前端抬高到 5 → 假 Worker 對體驗放行 5，模擬後端同事改完後）。
# 驗：免費第 2 條被擋、體驗期內可到 5（第 6 條擋）、Plus 第 6 條擋、Pro 可到 20（第 21 條擋）、
#     勾選通知方式會存（重新載入還在）、條件成立時站內鈴鐺出現通知、手機 390 不橫捲。
import json as _al_json
_AL_API = "https://alert1102.example.test"
_AL_SHOTS = "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad"
_AL_DATA = {"v": 1, "asof": "2026-10-22", "prev": "2026-10-21", "ia": "2026-10-22", "unit": {},
            "s": {"2330": {"n": "台積電", "c": 2385.0, "pc": 2420.0, "v": 29797, "i": [-1, 1, 1, 1], "k": [-12, 17, -12]}}}


def _al_ctx(b, W, plan, welcome, st, errs):
    mob = W <= 640
    cap = {"free": 1, "plus": 5, "pro": 20}[plan]
    srv = 5 if welcome else cap   # 假 Worker 的伺服器上限（體驗期＝5，模擬後端已配合）
    feats = {"watch.page": True, "watch.tabs": 50, "watch.size": 200, "watch.digest": plan == "pro", "watch.alert": cap} if plan != "free" else {"watch.page": True, "watch.tabs": 1, "watch.size": 10}

    def handle(route):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            body = _al_json.loads(req.post_data or "{}")
        except Exception:
            body = {}
        out, status = {}, 200
        now = 1798800000000
        if path == "/v1/me":
            out = {"user": {"email": plan + "@example.com", "name": "測試", "admin": False, "owner": False}}
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": plan if plan != "free" else "free", "planName": plan, "feats": feats, "lims": {}, "dq": None}
        elif path == "/v1/lists/get":
            out = {"lists": [{"id": "t1", "name": "我的", "codes": ["2330"]}], "rev": 1}
        elif path == "/v1/lists/put":
            out = {"ok": True, "rev": 2, "lists": body.get("lists", [])}
        elif path == "/v1/alerts/get":
            out = {"alerts": st["rules"], "rev": st["rev"], "cap": srv}
        elif path == "/v1/alerts/put":
            if len(body.get("alerts", [])) > max(srv, len(st["rules"])):
                out, status = {"error": "alert_limit", "limit": srv, "alerts": st["rules"], "rev": st["rev"]}, 403
            else:
                st["rules"] = [{k: v for k, v in r.items() if k != "nt"} for r in body["alerts"]]   # 真 Worker 目前會丟掉 nt
                st["rev"] += 1
                out = {"ok": True, "rev": st["rev"], "alerts": st["rules"], "cap": srv}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path == "/v1/grants/public":
            out = {"now": 0, "promo": [], "welcome": []}
        elif path == "/v1/grants/me":
            g = [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": 0, "end": 4102444800000, "per": "day", "feats": {"ind.3d": {"max": 10, "used": 0, "left": 10}}}] if welcome else []
            out = {"now": 0, "today": {}, "grants": g}
        route.fulfill(status=status, body=_al_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _al_json.dumps({"api": _AL_API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route("**/data/digest.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_al_json.dumps(st["digest"])))
    c.route(_AL_API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}/{plan}: {e}"))
    return c, pg


def _al_open_rules(pg, base):
    pg.goto(base + "#watch", wait_until="domcontentloaded")
    a = pg.get_by_role("button", name="同意並繼續")
    if a.count() and a.first.is_visible():
        a.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, "() => !!document.getElementById('wdCard') && !!document.querySelector('#wdCard [data-wdv=rules]')", 15000)
    pg.click("#wdCard [data-wdv=rules]")
    return wait_until(pg, "() => !!document.getElementById('wdAdd')", 5000)


def _al_fill_to(pg, n, price0=5000):
    """連續加到 n 條（高於 N 元，不成立）；回傳實際條數"""
    for i in range(n):
        have = pg.evaluate("() => document.querySelectorAll('#wdCard .wdrule').length")
        if pg.evaluate("() => document.getElementById('wdAdd').disabled"):
            break
        pg.select_option("#wdType", "above")
        pg.fill("#wdX", str(price0 + have)); pg.click("#wdAdd")
        wait_until(pg, f"() => document.querySelectorAll('#wdCard .wdrule').length === {have + 1}", 4000)
    return pg.evaluate("() => document.querySelectorAll('#wdCard .wdrule').length")


def t_alert_limit_1102(b, base, code):
    T = "自設提醒上限1102"
    errs = []
    for W in (1440, 390):
        for plan, welcome, want in (("free", False, 1), ("free", True, 5), ("plus", False, 5), ("pro", False, 20)):
            tag = f"{W}/{plan}{'+體驗' if welcome else ''}"
            st = {"rules": [], "rev": 0, "digest": _AL_DATA}
            c, pg = _al_ctx(b, W, plan, welcome, st, errs)
            got = _al_open_rules(pg, base)
            n = _al_fill_to(pg, want + 1)
            dis = pg.evaluate("() => document.getElementById('wdAdd').disabled")
            lab = pg.evaluate("() => document.querySelector('#wdCard [data-wdv=rules]').innerText")
            ok(f"{T}（{tag}）可設到 {want} 條、第 {want + 1} 條被擋（加入鈕反灰、分頁寫 {want}／{want}）", bool(got) and n == want and dis and f"{want}／{want}" in lab, [n, dis, lab])
            if plan == "pro" and W == 1440:
                pg.screenshot(path=f"{_AL_SHOTS}/alert_pro20_{W}.png")
            c.close()
        # ---- 通知方式勾選會存 + 條件成立站內通知
        st = {"rules": [], "rev": 0, "digest": json_copy(_AL_DATA)}
        c, pg = _al_ctx(b, W, "plus", False, st, errs)
        _al_open_rules(pg, base)
        ok(f"{T}（{W}/Plus）新增表單有「網頁通知」（預設勾）與「email」（預設不勾）", pg.evaluate("() => document.getElementById('wdNtW').checked && !document.getElementById('wdNtM').checked"))
        pg.select_option("#wdType", "below"); pg.fill("#wdX", "3000")   # 現價 2385 < 3000 → 新建即成立
        pg.check("#wdNtM"); pg.click("#wdAdd")
        wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 1", 4000)
        st1 = pg.evaluate("() => [...document.querySelectorAll('#wdCard .wdrule [data-wdnt]')].map(e => e.dataset.wdnt + ':' + e.checked).join()")
        ok(f"{T}（{W}/Plus）勾 email 加入 → 該條顯示 網頁✓ email✓", st1 == "w:true,m:true", st1)
        wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && !d.hidden && Number(d.textContent) >= 1; }", 8000)
        pg.click("#ntBell")
        wait_until(pg, "() => document.querySelectorAll('#ntDrop .ntitem').length >= 1", 3000)
        it = pg.evaluate("() => [...document.querySelectorAll('#ntDrop .ntitem')].map(e => e.innerText).join('|')")
        ok(f"{T}（{W}/Plus）條件成立 → 站內鈴鐺出現「提醒：台積電…收盤價低於 3,000.00 元」", "提醒：台積電" in it and "你設定的條件成立" in it, it[:200])
        pg.screenshot(path=f"{_AL_SHOTS}/alert_bell_{W}.png")
        pg.keyboard.press("Escape"); pg.mouse.click(5, 300); pg.wait_for_timeout(200)
        # 取消 email、重新載入後保存（Worker 丟掉 nt，靠本機偏好）
        pg.uncheck("#wdCard [data-wdnt=m]")
        wait_until(pg, "() => !document.querySelector('#wdCard [data-wdnt=m]').checked", 3000)
        pg.wait_for_timeout(400)
        pg.reload(wait_until="domcontentloaded")
        _al_open_rules(pg, base)
        wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 1", 5000)
        st2 = pg.evaluate("() => [...document.querySelectorAll('#wdCard .wdrule [data-wdnt]')].map(e => e.dataset.wdnt + ':' + e.checked).join()")
        ok(f"{T}（{W}/Plus）取消 email、重新載入 → 設定還在（網頁✓ email✗）", st2 == "w:true,m:false", st2)
        ovf = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        small = pg.evaluate("() => [...document.querySelectorAll('#wdCard *')].filter(e => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11).length")
        ok(f"{T}（{W}/Plus）沒有橫向捲軸、卡內沒有小於 11px 的字", ovf <= 1 and small == 0, [ovf, small])
        pg.screenshot(path=f"{_AL_SHOTS}/alert_rules_{W}.png")
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


def json_copy(d):
    return _al_json.loads(_al_json.dumps(d))


register("自設提醒上限1102", lambda pg, b, base, code: t_alert_limit_1102(b, base, code))
