# 驗收段落「側欄隱藏眼睛1029」（site/navhide.js；workers/account-api/articles.js 的 /v1/nav/hidden）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-29：「交易練習室先隱藏，並且圖一分頁都需要新增眼睛圖案 方便我隱藏」「跟這個一樣 小小的圖示即可」。
# 假會員 Worker（page.route，狀態存 Python 端，各瀏覽器共用＝模擬「存在伺服器、對所有人生效」，預設 ['lab'] 同真 Worker）：
# 管理者點眼睛 → 項目半透明＋劃掉、伺服器收到、不會順便換頁；訪客／一般會員 → 該項整個不見、直接打網址導回 #overview；
# 再點回來 → 訪客又看得到；整組隱藏；寫入失敗 → 還原；交易練習室預設不見。1440（側欄）與 390（手機抽屜）。
import json as _nh_json
import re as _nh_re

_NH_API = "https://nav1029.example.test"


def t_nav_eye_1029(b, base, code):
    T = "側欄隱藏眼睛1029"
    errs = []
    st = {"hidden": ["lab"], "fail": False, "puts": []}

    def handler(route):
        req = route.request
        path = _nh_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _nh_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        is_adm = email == "andy@example.com"
        out, status = {}, 200
        if path == "/v1/me":
            out, status = ({"user": {"email": email, "name": email.split("@")[0], "admin": is_adm}}, 200) if email else ({"error": "auth"}, 401)
        elif path == "/v1/perm/me":
            out = {"who": "member" if email else "guest", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/nav/hidden":
            out = {"hidden": list(st["hidden"])}
        elif path == "/v1/nav/hidden/put":
            st["puts"].append([email, body.get("hidden")])
            if not is_adm: out, status = {"error": "forbidden"}, 403
            elif st["fail"]: out, status = {"error": "boom"}, 500
            else:
                st["hidden"] = list(dict.fromkeys(body.get("hidden") or [])); out = {"ok": True, "hidden": list(st["hidden"])}
        route.fulfill(status=status, body=_nh_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w=1440):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _nh_json.dumps({"api": _NH_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _nh_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_NH_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_="#overview", admin=False):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#tabs .tab[data-view=market]')", 20000)
        if admin:
            wait_until(pg, "() => document.querySelectorAll('.naveye').length > 5", 15000)
        pg.wait_for_timeout(900)

    vis_tab = "(v) => { const t = document.querySelector('#tabs .tab[data-view=' + v + ']'); return !!t && t.getClientRects().length > 0; }"
    vis_sub = "(k) => { const t = document.querySelector('.l4subtab[data-l4sub=' + k + ']'); return !!t && t.getClientRects().length > 0; }"
    vis_grp = "(g) => { const t = document.querySelector('.l4grp[data-g=' + g + ']'); return !!t && t.getClientRects().length > 0; }"
    GUARDS = []

    # ═════════ 1440 側欄
    W = 1440
    st["hidden"] = ["lab"]; st["puts"].clear()
    c, pg = ctx("andy@example.com", W); open_(pg, admin=True)
    cnt = pg.evaluate("""() => { const q = (s) => [...document.querySelectorAll(s)].filter(e => e.getClientRects().length);
        const tabs = q('#tabs .tab[data-view]').filter(t => t.dataset.view !== 'delivery'), subs = q('#tabs .l4subtab[data-l4sub]'), grps = q('#tabs .l4grp[data-g]');
        const miss = [...tabs, ...subs, ...grps].filter(e => !e.querySelector(':scope > .naveye')).map(e => e.dataset.view || e.dataset.l4sub || e.dataset.g);
        return { tabs: tabs.length, subs: subs.length, grps: grps.length, miss, eyes: q('.naveye').length }; }""")
    ok(f"★ [{T}（{W}）] 管理者：側欄每個大項、子項、組標題都有眼睛（缺 0）", cnt["tabs"] >= 10 and cnt["subs"] >= 12 and cnt["grps"] >= 4 and not cnt["miss"], cnt)
    geo = pg.evaluate("""() => [...document.querySelectorAll('#tabs .naveye')].filter(e => e.getClientRects().length).map(e => { const p = e.parentElement, a = e.getBoundingClientRect(), r = p.getBoundingClientRect();
        const lb = [...p.children].filter(x => x !== e && !x.classList.contains('l4car') && x.getClientRects().length && x.textContent.trim()).map(x => x.getBoundingClientRect().right);
        return { id: e.dataset.id, inside: a.left >= r.left - 1 && a.right <= r.right + 1 && a.top >= r.top - 1 && a.bottom <= r.bottom + 1, right: a.left + a.width / 2 > r.left + r.width / 2, w: a.width, h: a.height, noOverlap: !lb.length || a.left >= Math.max(...lb) - 0.5 }; })""")
    bad = [g for g in geo if not (g["inside"] and g["right"] and g["noOverlap"] and g["w"] <= 24 and g["h"] <= 24)]
    ok(f"★ [{T}（{W}）] 管理者：眼睛都在自己那列裡面、靠右、不壓到文字、小小的（≤ 24px）", len(geo) > 20 and not bad, bad[:4])
    ok(f"★ [{T}（{W}）] 交易練習室預設隱藏：管理者看得到它但是半透明＋眼睛斜線", pg.evaluate("() => { const t = document.querySelector('#tabs .tab[data-view=lab]'); const e = t && t.querySelector('.naveye'); return !!t && t.getClientRects().length > 0 && t.classList.contains('nav-hid') && parseFloat(getComputedStyle(t).opacity) < 0.8 && !!e && e.classList.contains('off'); }"))
    h0 = pg.evaluate("() => location.hash"); fold0 = pg.evaluate("() => document.getElementById('tabs').getAttribute('data-cs') + '|' + document.getElementById('tabs').getAttribute('data-cg')")
    pg.click("#tabs .tab[data-view=market] > .naveye"); pg.wait_for_timeout(500)
    ok(f"★ [{T}（{W}）] 點「市場明細」眼睛 → 半透明、斜線、伺服器收到 ['lab','market']；網址與子項收展都沒動",
       pg.evaluate("() => document.querySelector('#tabs .tab[data-view=market]').classList.contains('nav-hid')") and st["hidden"] == ["lab", "market"]
       and pg.evaluate("() => location.hash") == h0 and fold0 == pg.evaluate("() => document.getElementById('tabs').getAttribute('data-cs') + '|' + document.getElementById('tabs').getAttribute('data-cg')"), [st["hidden"], h0])
    ok(f"[{T}（{W}）] 管理者：「市場明細」底下的子項跟著半透明（上層被隱藏）", pg.evaluate("() => [...document.querySelectorAll('.l4subtab[data-parent=market]')].every(s => s.classList.contains('nav-hid'))"))
    pg.click(".l4subtab[data-l4sub=xp-news] > .naveye"); pg.wait_for_timeout(500)
    ok(f"[{T}（{W}）] 點子項「消息面」眼睛 → 伺服器多一個 xp-news、網址沒動", "xp-news" in st["hidden"] and pg.evaluate("() => location.hash") == h0, st["hidden"])
    pg.click(".l4grp[data-g=hist] > .naveye"); pg.wait_for_timeout(500)
    ok(f"[{T}（{W}）] 點組標題「歷史規律」眼睛 → 伺服器多一個 g:hist；組內週期統計半透明", "g:hist" in st["hidden"]
       and pg.evaluate("() => document.querySelector('#tabs .tab[data-view=season]').classList.contains('nav-hid')"), st["hidden"])
    ok(f"[{T}（{W}）] 管理者：沒有橫向捲軸、眼睛列不影響側欄寬度", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
    pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => document.querySelectorAll('.naveye.off').length >= 4", 15000)
    ok(f"[{T}（{W}）] 管理者重新整理 → 斜線眼睛仍在（存在伺服器）", pg.locator(".naveye.off").count() >= 4)
    # 寫入失敗 → 還原
    st["fail"] = True
    pg.click("#tabs .tab[data-view=flow] > .naveye"); pg.wait_for_timeout(900)
    ok(f"★ [{T}（{W}）] 伺服器寫入失敗（500）→ 資金流向不留在半透明、伺服器沒變", not pg.evaluate("() => document.querySelector('#tabs .tab[data-view=flow]').classList.contains('nav-hid')") and "flow" not in st["hidden"], st["hidden"])
    st["fail"] = False
    c.close()

    # 訪客與一般會員
    for who, mail in (("訪客", None), ("一般會員", "bob@example.com")):
        c, pg = ctx(mail, W); open_(pg)
        ok(f"★ [{T}（{W}）] {who}：市場明細、週期統計、整組「歷史規律」、交易練習室全不見，總覽／資金流向／產業地圖還在",
           not pg.evaluate(vis_tab, "market") and not pg.evaluate(vis_tab, "season") and not pg.evaluate(vis_tab, "lab") and not pg.evaluate(vis_grp, "hist")
           and pg.evaluate(vis_tab, "overview") and pg.evaluate(vis_tab, "flow") and pg.evaluate(vis_tab, "industry"),
           pg.evaluate("() => [...document.querySelectorAll('#tabs .tab')].filter(t => t.getClientRects().length).map(t => t.dataset.view)"))
        ok(f"[{T}（{W}）] {who}：側欄看不到任何眼睛", pg.evaluate("() => [...document.querySelectorAll('.naveye')].every(e => e.getClientRects().length === 0)"))
        ok(f"[{T}（{W}）] {who}：市場明細的子項（漲跌家數）也不見", not pg.evaluate(vis_sub, "mkt-updown"))
        for hh in ("#market", "#market/updown", "#season", "#lab"):
            pg.goto(base + hh, wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
            GUARDS.append((who, hh, pg.evaluate("() => location.hash")))
        ok(f"★ [{T}（{W}）] {who}：直接打 #market／#market/updown／#season／#lab → 全導回 #overview", all(g[2] == "#overview" for g in GUARDS if g[0] == who), GUARDS)
        c.close()

    # 管理者恢復 → 訪客馬上看得到；explore 的 xp-news 單獨隱藏時其他面向照常
    st["hidden"] = ["lab", "market", "xp-news", "g:hist"]
    c, pg = ctx("andy@example.com", W); open_(pg, admin=True)
    pg.click("#tabs .tab[data-view=market] > .naveye"); pg.wait_for_timeout(500)
    pg.click(".l4grp[data-g=hist] > .naveye"); pg.wait_for_timeout(500)
    ok(f"★ [{T}（{W}）] 管理者再點「市場明細」與「歷史規律」眼睛 → 伺服器 ['lab','xp-news']、項目回到不透明", st["hidden"] == ["lab", "xp-news"]
       and not pg.evaluate("() => document.querySelector('#tabs .tab[data-view=market]').classList.contains('nav-hid')"), st["hidden"])
    c2, pg2 = ctx(None, W); open_(pg2)
    ok(f"★ [{T}（{W}）] 訪客重新開 → 市場明細、週期統計回來；選股策略只少「消息面」；交易練習室仍不見",
       pg2.evaluate(vis_tab, "market") and pg2.evaluate(vis_tab, "season") and pg2.evaluate(vis_sub, "xp-fund") and pg2.evaluate(vis_sub, "xp-chip")
       and not pg2.evaluate(vis_sub, "xp-news") and not pg2.evaluate(vis_tab, "lab"))
    pg2.goto(base + "#explore/news", wait_until="domcontentloaded"); pg2.wait_for_timeout(1800)
    ok(f"[{T}（{W}）] 訪客打 #explore/news（被隱藏的子項）→ 導到 #explore/fund", pg2.evaluate("() => location.hash") == "#explore/fund", pg2.evaluate("() => location.hash"))
    c2.close()
    # 一般會員硬打寫入 → 擋
    c3, pg3 = ctx("bob@example.com", W); open_(pg3)
    r403 = pg3.evaluate("async () => { const r = await TwAccount.call('/v1/nav/hidden/put', { hidden: [] }); return r && r._s; }")
    ok(f"[{T}] 一般會員硬打寫入 → 403、伺服器設定沒變", r403 == 403 and st["hidden"] == ["lab", "xp-news"], [r403, st["hidden"]])
    c3.close(); c.close()

    # ═════════ 390 手機抽屜
    W = 390
    st["hidden"] = ["lab", "market"]; st["puts"].clear()
    c, pg = ctx("andy@example.com", W); open_(pg, "#overview")
    wait_until(pg, "() => !!document.getElementById('m4Burger')", 15000)
    pg.click("#m4Burger"); pg.wait_for_timeout(700)
    wait_until(pg, "() => document.querySelectorAll('#m4Drawer .naveye').length > 5", 10000)
    geo = pg.evaluate("""() => [...document.querySelectorAll('#m4Drawer .naveye')].filter(e => e.getClientRects().length).map(e => { const p = e.closest('.m4item,.m4gt'), a = e.getBoundingClientRect(), r = p.getBoundingClientRect(); return { id: e.dataset.id, inside: a.left >= r.left - 1 && a.right <= r.right + 1, w: a.width, h: a.height }; })""")
    ok(f"★ [{T}（{W}）] 管理者手機抽屜：每個大項與組標題右側有眼睛、在列內、點擊區 ≥ 32px", len(geo) >= 10 and all(g["inside"] and g["w"] >= 32 and g["h"] >= 32 for g in geo), geo[:3])
    ok(f"[{T}（{W}）] 管理者手機抽屜：市場明細半透明、眼睛斜線", pg.evaluate("() => { const t = document.querySelector('#m4Drawer .m4item[data-v=market]'); return !!t && t.classList.contains('nav-hid') && t.querySelector('.naveye').classList.contains('off'); }"))
    h0 = pg.evaluate("() => location.hash")
    pg.click("#m4Drawer .m4item[data-v=flow] > .naveye"); pg.wait_for_timeout(600)
    ok(f"★ [{T}（{W}）] 手機點「資金流向」眼睛 → 伺服器收到 flow、抽屜沒關、網址沒動、該列半透明",
       "flow" in st["hidden"] and pg.evaluate("() => !document.getElementById('m4Drawer').hidden") and pg.evaluate("() => location.hash") == h0
       and pg.evaluate("() => document.querySelector('#m4Drawer .m4item[data-v=flow]').classList.contains('nav-hid')"), [st["hidden"], h0])
    ok(f"[{T}（{W}）] 手機抽屜：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
    c.close()
    c, pg = ctx("bob@example.com", W); open_(pg, "#overview")
    wait_until(pg, "() => !!document.getElementById('m4Burger')", 15000)
    pg.click("#m4Burger"); pg.wait_for_timeout(700)
    items = pg.evaluate("() => [...document.querySelectorAll('#m4Drawer .m4item[data-v]')].filter(e => e.getClientRects().length).map(e => e.dataset.v)")
    ok(f"★ [{T}（{W}）] 一般會員手機抽屜：資金流向、市場明細、交易練習室不列，總覽還在，沒有任何眼睛", "flow" not in items and "market" not in items and "lab" not in items and "overview" in items
       and pg.evaluate("() => document.querySelectorAll('#m4Drawer .naveye').length") == 0, items)
    pg.goto(base + "#market", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
    ok(f"[{T}（{W}）] 一般會員手機直接打 #market → 導回 #overview", pg.evaluate("() => location.hash") == "#overview", pg.evaluate("() => location.hash"))
    c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("側欄隱藏眼睛1029", lambda pg, b, base, code: t_nav_eye_1029(b, base, code))
