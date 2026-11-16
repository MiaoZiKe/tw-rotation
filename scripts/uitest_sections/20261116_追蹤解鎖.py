# 驗收段落「追蹤解鎖1116」（site/unlock.js、site/articles.js 的 canPriv／chBanner、features.js 的 art.ch.<頻道>、plan_presets.js）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-16：「追蹤了科技版跟 AI，那兩個都可以看到；如果沒有註冊，只能看到那一篇文章；這個方式沿用到不同頻道」。
# 真的操作：連結 #unlock/<碼>/<單篇 id>。訪客→只讀那一篇、四個頻道分頁都藏；會員（預覽網域假兌換 pv-<頻道>）→ 該頻道分頁出現、可讀全部、
# 再兌換第二個頻道兩個都在、其他仍藏、重新整理仍在；訪客先開連結之後才登入也生效；正式網域（沒有 TW_PREVIEW）假兌換不生效；
# 假想 Worker 上線（回 200＋unlocked）→ 正式網域也生效；站主四個分頁都看得到。1440 與 390。
import json as _fu_json
import re as _fu_re

_FU_API = "https://acct1116fu.example.test"
_FU_T = "2026-11-17-tech-yield"
_FU_H = "2026-11-22-healing-firstmarriage"
_FU_L = "2026-11-17-ligu-2008-check"
_FU_C = "2026-11-17-two-answers"


def t_followunlock_1116(b, base, code):
    T = "追蹤解鎖1116"
    errs = []
    state = {"mode": "404", "admin": False, "email": None, "redeemed": 0, "posts": []}

    def handler(route):
        req = route.request
        path = _fu_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        hd = {"access-control-allow-origin": "*", "content-type": "application/json", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"}
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers=hd)
        try: body = _fu_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        if path in ("/v1/track/batch", "/v1/beat"): state["posts"].append(req.post_data or "")
        email = tok[4:] if tok.startswith("tok-") else None
        out, st = {}, 200
        if path == "/v1/me":
            out = {"user": {"email": email, "name": email.split("@")[0], "admin": bool(state["admin"])}} if email else {"error": "auth"}
            st = 200 if email else 401
        elif path == "/v1/perm/me":
            out = {"who": "member" if email else "guest", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        elif path == "/v1/unlock/redeem":
            state["redeemed"] += 1
            if state["mode"] == "404": out, st = {"error": "nf"}, 404
            else: out = {"unlocked": ["tech"], "channel": "tech"}
        route.fulfill(status=st, body=_fu_json.dumps(out), headers=hd)

    def ctx(email, w, preview=True, mode="404", admin=False):
        state.update(mode=mode, admin=admin, redeemed=0, posts=[])
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = ("window.TW_PREVIEW = { name: 'fu' };" if preview else "") + "window.TW_ACCOUNT_OVERRIDE = " + _fu_json.dumps({"api": _FU_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += "if(!sessionStorage.getItem('zzFu')){sessionStorage.setItem('zzFu','1');"
        init += ("localStorage.setItem('tw.acct.tok'," + _fu_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');")
        init += "Object.keys(localStorage).filter(function(k){return k.indexOf('tw.unl.pv.')===0}).forEach(function(k){localStorage.removeItem(k)})}}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_FU_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, url, sel="() => !!document.querySelector('#artCats>button[data-cat=all]') || !!document.querySelector('#artPost .artttl')"):
        pg.goto(url, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, sel, 20000)
        pg.wait_for_timeout(1500)

    tabs = "() => ['tech','ligu','caffaine','healing'].filter(k => { const b = document.querySelector('#artCats>button[data-cat=' + k + ']'); return !!b && !b.hidden && b.getClientRects().length > 0; })"
    cards = "() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.id + '|' + a.dataset.cat)"
    chl = "() => { const e = document.getElementById('artChl'); return e ? e.dataset.st : ''; }"
    hashf = "() => location.hash"
    nohs = "() => document.documentElement.scrollWidth - innerWidth"
    for W in (1440, 390):
        # ── A 訪客：只能讀連結那一篇；碼從網址拿掉；四個頻道分頁都藏
        c, pg = ctx(None, W)
        open_(pg, base + "#unlock/pv-tech/" + _FU_T)
        ok(f"★ [{T}（{W}）] 訪客：解鎖連結打得開那一篇、網址變成單篇（碼不留在網址）", pg.evaluate(hashf) == "#article/" + _FU_T and pg.locator("#artPost .artttl").count() == 1, pg.evaluate(hashf))
        ok(f"★ [{T}（{W}）] 訪客：提示「只能看這一篇」＋登入／註冊鈕", pg.evaluate(chl) == "guest" and pg.locator("#artChlLogin").count() == 1, pg.evaluate(chl))
        ok(f"[{T}（{W}）] 訪客：沒有橫向捲軸", pg.evaluate(nohs) <= 1)
        open_(pg, base + "#articles")
        ok(f"★ [{T}（{W}）] 訪客：分頁列四個頻道都沒有", pg.evaluate(tabs) == [], pg.evaluate(tabs))
        pg.goto(base + "#articles/healing", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
        ok(f"[{T}（{W}）] 訪客：直接打 #articles/healing → 導回 #articles", pg.evaluate(hashf) == "#articles", pg.evaluate(hashf))
        # ── D 訪客先開連結，之後才登入（同一個分頁，重新整理後）→ 登入即兌換
        pg.goto(base + "#unlock/pv-tech/" + _FU_T, wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
        pg.evaluate("() => localStorage.setItem('tw.acct.tok', 'tok-dora@example.com')")
        pg.reload(wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
        open_(pg, base + "#articles")
        wait_until(pg, tabs.replace("filter(", "filter(") + ".length > 0", 8000)
        ok(f"★ [{T}（{W}）] 先開連結、之後登入 → 自動兌換，出現科技透明圈分頁", pg.evaluate(tabs) == ["tech"], [pg.evaluate(tabs), pg.evaluate("() => sessionStorage.getItem('tw.unl.pend')")])
        c.close()

        # ── B 會員（預覽網域，Worker 未上線 → 假兌換）：逐頻道累積
        c, pg = ctx("bob@example.com", W)
        open_(pg, base + "#article/" + _FU_T)
        ok(f"[{T}（{W}）] 會員沒兌換直接開單篇：能讀、提示「還沒解鎖全部」、分頁藏", pg.evaluate(chl) == "nogate" and pg.evaluate(tabs) == [], [pg.evaluate(chl), pg.evaluate(tabs)])
        open_(pg, base + "#unlock/pv-tech/" + _FU_T)
        wait_until(pg, "() => document.getElementById('artChl') && document.getElementById('artChl').dataset.st === 'ok'", 8000)
        ok(f"★ [{T}（{W}）] 會員兌換 pv-tech：提示「已解鎖」＋鈕", pg.evaluate(chl) == "ok" and pg.locator("#artChlGo").count() == 1, pg.evaluate(chl))
        pg.locator("#artChlGo").scroll_into_view_if_needed(); pg.click("#artChlGo")
        wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 10000)
        ok(f"★ [{T}（{W}）] 會員：點鈕 → #articles/tech，清單列出科技頻道全部文章", pg.evaluate(hashf) == "#articles/tech" and any(x.endswith("|tech") for x in pg.evaluate(cards)) and _FU_T + "|tech" in pg.evaluate(cards), [pg.evaluate(hashf), pg.evaluate(cards)[:4]])
        ok(f"★ [{T}（{W}）] 會員：只有科技分頁，哩股／CaffAIne／談晴仍藏", pg.evaluate(tabs) == ["tech"], pg.evaluate(tabs))
        ok(f"[{T}（{W}）] 會員：頻道清單沒有橫向捲軸", pg.evaluate(nohs) <= 1)
        st = pg.evaluate("() => { const t = document.querySelector('#artCats>button[data-cat=tech]'); return { on: t.classList.contains('on'), hid: t.classList.contains('hid') }; }")
        ok(f"[{T}（{W}）] 會員：科技分頁亮起、不是站主的「變淡」樣式", st["on"] and not st["hid"], st)
        open_(pg, base + "#unlock/pv-ligu-x1/" + _FU_L)
        wait_until(pg, "() => document.getElementById('artChl') && document.getElementById('artChl').dataset.st === 'ok'", 8000)
        open_(pg, base + "#articles")
        ok(f"★ [{T}（{W}）] 再兌換哩股哩股 → 科技＋哩股兩個都在，其餘仍藏", sorted(pg.evaluate(tabs)) == ["ligu", "tech"], pg.evaluate(tabs))
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=all]')", 12000); pg.wait_for_timeout(1500)
        ok(f"[{T}（{W}）] 會員：重新整理仍是兩個頻道（記在帳號，不是連結）", sorted(pg.evaluate(tabs)) == ["ligu", "tech"], pg.evaluate(tabs))
        pg.goto(base + "#articles/ligu", wait_until="domcontentloaded"); wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 12000)
        ok(f"[{T}（{W}）] 會員：哩股頻道清單看得到哩股文章、不混科技文章", any(x.endswith("|ligu") for x in pg.evaluate(cards)) and not any(x.endswith("|tech") for x in pg.evaluate(cards)), pg.evaluate(cards)[:3])
        pg.goto(base + "#articles/caffaine", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
        ok(f"[{T}（{W}）] 會員：沒解鎖的 CaffAIne 頻道直接打網址 → 導回", pg.evaluate(hashf) == "#articles", pg.evaluate(hashf))
        open_(pg, base + "#articles")
        ok(f"[{T}（{W}）] 會員：「全部文章」清單不混進頻道文章", not any(x.endswith("|tech") or x.endswith("|ligu") for x in pg.evaluate(cards)), pg.evaluate(cards)[:3])
        pg.evaluate("() => localStorage.setItem('tw.acct.tok', 'tok-carol@example.com')")
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=all]')", 12000); pg.wait_for_timeout(2000)
        ok(f"[{T}（{W}）] 換另一個帳號登入：不繼承上一個帳號的解鎖", pg.evaluate(tabs) == [], pg.evaluate(tabs))
        c.close()

        # ── G 獨立閱讀站（site/c/<頻道>/）：CaffAIne、談晴說礙
        c, pg = ctx(None, W)
        ST = "() => !!document.querySelector('#app .art h1, #app #gate, #app .cards')"
        open_(pg, base + "c/healing/#/" + _FU_H, ST)
        ok(f"★ [{T}（{W}）] 獨立站：訪客用單篇連結讀得到談晴那一篇、有「只能看這一篇」提示", pg.evaluate("() => (document.querySelector('.art h1')||{}).textContent||''") != "" and pg.evaluate("() => (document.getElementById('bn')||{dataset:{}}).dataset.st") == "guest", pg.evaluate("() => location.href"))
        ok(f"[{T}（{W}）] 獨立站：沒有哩股哩股主站的導覽列、沒有橫向捲軸", pg.evaluate("() => !document.querySelector('#sidebar, nav.side, #topbar')") and pg.evaluate(nohs) <= 1, pg.evaluate(nohs))
        ok(f"[{T}（{W}）] 獨立站：頁尾是「文章與影片 ©」、沒有投資建議字樣", "文章與影片 © 談晴說礙" in pg.inner_text(".ft") and "投資建議" not in pg.inner_text(".ft"), pg.inner_text(".ft"))
        ok(f"[{T}（{W}）] 獨立站：談晴配色（暖米紙底）", pg.evaluate("() => getComputedStyle(document.body).backgroundColor") == "rgb(251, 245, 234)", pg.evaluate("() => getComputedStyle(document.body).backgroundColor"))
        open_(pg, base + "c/healing/#/", ST); pg.wait_for_timeout(600)
        ok(f"★ [{T}（{W}）] 獨立站：訪客看清單 → 有說明卡，文章列成卡片但全部加鎖淡化", pg.evaluate("() => !!document.getElementById('gate') && document.querySelectorAll('#list .card').length >= 2 && document.querySelectorAll('#list .card.lk .lkc').length === document.querySelectorAll('#list .card').length"), "")
        pg.locator("#list .card").first.click(); pg.wait_for_timeout(900)
        ok(f"★ [{T}（{W}）] 獨立站：點加鎖卡片 → 跳登入視窗、不進內文", pg.evaluate("() => !!document.querySelector('[role=dialog], .acctdlg, #acctDlg, .tw-dlg')") and pg.evaluate("() => location.hash") in ("", "#/"), pg.evaluate("() => location.hash"))
        ok(f"[{T}（{W}）] 獨立站：卡片有封面縮圖框", pg.evaluate("() => document.querySelectorAll('#list .card .th').length") >= 2)
        c.close()
        c, pg = ctx("bob@example.com", W)
        open_(pg, base + "#unlock/pv-caffaine/" + _FU_C, ST)
        wait_until(pg, "() => document.querySelector('.art') && document.getElementById('bn') && document.getElementById('bn').dataset.st === 'ok'", 12000)
        ok(f"★ [{T}（{W}）] 兌換連結 → 轉進 /c/caffaine/ 獨立站、提示「已解鎖」", "/c/caffaine/" in pg.evaluate("() => location.pathname") and pg.evaluate("() => document.getElementById('bn').dataset.st") == "ok", pg.evaluate("() => location.href"))
        v = pg.evaluate("() => { const v = document.querySelector('.art video'); return v ? { src: v.getAttribute('src'), dl: !!document.querySelector('.art .vid a[download]'), w: v.getBoundingClientRect().width } : null; }")
        ok(f"★ [{T}（{W}）] 獨立站：內文有 mp4 區塊（含下載鈕）、寬度不超過版面", bool(v) and v["dl"] and v["w"] <= W, v)
        pg.wait_for_timeout(1500)
        rs = pg.evaluate("() => { const v = document.querySelector('.art video'); return v ? { rs: v.readyState, err: !!v.error, nw: v.networkState } : null; }")
        ok(f"★ [{T}（{W}）] 獨立站：影片能載入（讀得到中繼資料、沒有錯誤）", bool(rs) and not rs["err"] and rs["rs"] >= 1, rs)
        ok(f"[{T}（{W}）] 獨立站：內文頁沒有橫向捲軸", pg.evaluate(nohs) <= 1, pg.evaluate(nohs))
        pg.click("#bn a.btn"); wait_until(pg, "() => document.querySelectorAll('#list .card').length > 0", 10000)
        ok(f"★ [{T}（{W}）] 獨立站：已解鎖會員看得到清單、有 CaffAIne 全部文章卡", pg.evaluate("() => document.querySelectorAll('#list .card').length") >= 2, pg.evaluate("() => location.hash"))
        ok(f"[{T}（{W}）] 獨立站：清單沒有橫向捲軸", pg.evaluate(nohs) <= 1)
        open_(pg, base + "#articles/caffaine")
        wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 10000)
        hr = pg.evaluate("() => document.querySelector('#artList .artc').getAttribute('href')")
        ok(f"★ [{T}（{W}）] 主站 CaffAIne 分頁：卡片連結指向獨立站", hr.startswith("c/caffaine/#/"), hr)
        pg.locator("#artList .artc").first.scroll_into_view_if_needed(); pg.locator("#artList .artc").first.click()
        wait_until(pg, "() => /\\/c\\/caffaine\\//.test(location.pathname) && !!document.querySelector('.art h1')", 10000)
        ok(f"★ [{T}（{W}）] 從主站點卡片 → 同分頁開到獨立站內文", "/c/caffaine/" in pg.evaluate("() => location.pathname") and pg.evaluate("() => !!document.querySelector('.art h1')"), pg.evaluate("() => location.href"))
        open_(pg, base + "#article/" + _FU_H, ST)
        ok(f"[{T}（{W}）] 舊連結 #article/<談晴 id> 自動轉到獨立站", "/c/healing/" in pg.evaluate("() => location.pathname"), pg.evaluate("() => location.href"))
        c.close()

        # ── H 文章觀測（只記錄）：瀏覽、收藏、分享、影片播放與下載各送一筆事件（沿用 ev2 管道，不帶任何識別碼）
        c, pg = ctx("bob@example.com", W)
        open_(pg, base + "#unlock/pv-caffaine/" + _FU_C, ST)
        wait_until(pg, "() => document.querySelector('.art') && document.getElementById('artM')", 12000)
        def sent(comp):
            pg.evaluate("() => TwAccount.flush()"); pg.wait_for_timeout(700)
            return any(comp in x for x in state["posts"])
        ok(f"★ [{T}（{W}）] 觀測：打開文章 → 送出「瀏覽．會員．私訊來源」事件", sent("ch.view.member.dm"), [x[:160] for x in state["posts"][:2]])
        pg.evaluate("() => { document.querySelector('#artM [data-am=save]').scrollIntoView(); }")
        pg.click("#artM [data-am=save]"); pg.wait_for_timeout(300)
        ok(f"★ [{T}（{W}）] 觀測：會員點收藏 → 鈕變「已收藏」、送出 ch.save.member", "已收藏" in pg.inner_text("#artM [data-am=save]") and sent("ch.save.member"), pg.inner_text("#artM"))
        pg.click("#artM [data-am=share]"); pg.wait_for_timeout(300)
        ok(f"★ [{T}（{W}）] 觀測：點分享 → 送出 ch.share.copy.member（桌機複製連結）", sent("ch.share.copy.member"), "")
        pg.evaluate("() => { const v = document.querySelector('.art video'); v.muted = true; return v.play().catch(() => v.dispatchEvent(new Event('play'))); }"); pg.wait_for_timeout(500)
        ok(f"★ [{T}（{W}）] 觀測：播放影片 → 送出 ch.play.member", sent("ch.play.member"), "")
        pg.evaluate("() => { const a = document.querySelector('.art .vid a[download]'); a.addEventListener('click', e => e.preventDefault()); a.click(); }"); pg.wait_for_timeout(300)
        ok(f"★ [{T}（{W}）] 觀測：點下載 → 送出 ch.dl.member", sent("ch.dl.member"), "")
        c.close()
        c, pg = ctx(None, W)
        open_(pg, base + "c/caffaine/#/" + _FU_C, ST)
        wait_until(pg, "() => document.getElementById('artM')", 12000)
        ok(f"[{T}（{W}）] 觀測：訪客打開 → ch.view.guest.site", sent("ch.view.guest.site"), "")
        pg.click("#artM [data-am=save]"); pg.wait_for_timeout(900)
        ok(f"★ [{T}（{W}）] 觀測：訪客點收藏 → 不收藏、跳登入視窗、送出 ch.savetry.guest", sent("ch.savetry.guest") and "收藏" in pg.inner_text("#artM [data-am=save]") and "已收藏" not in pg.inner_text("#artM [data-am=save]") and pg.evaluate("() => !!document.querySelector('[role=dialog], .acctdlg, #acctDlg, .tw-dlg')"), "")
        c.close()
        c, pg = ctx("bob@example.com", W)
        open_(pg, base + "#article/" + _FU_T)
        wait_until(pg, "() => document.getElementById('artM')", 12000)
        ok(f"★ [{T}（{W}）] 觀測：主站文章頁也有收藏／分享鈕並記瀏覽（ch.view.member.site）", pg.locator("#artM [data-am]").count() == 2 and sent("ch.view.member.site"), "")
        c.close()

        # ── I 發文包：只有站主看得到（兩個獨立站）
        for who, em, adm in (("站主", "andy@example.com", True), ("會員", "bob@example.com", False), ("訪客", None, False)):
            for ch, aid in (("caffaine", _FU_C), ("healing", _FU_H)):
                c, pg = ctx(em, W, admin=adm)
                pg.add_init_script("try{localStorage.setItem('tw.unl.pv.' + 'x','[]')}catch(e){}")
                open_(pg, base + "c/" + ch + "/#/" + aid, ST); pg.wait_for_timeout(2500)
                has = pg.locator("#kit").count()
                ok(f"★ [{T}（{W}）] 發文包（{ch}）：{who}{'看得到' if adm else '看不到'}內頁「發文包」", (has == 1) == adm, has)
                if adm:
                    ok(f"[{T}（{W}）] 發文包（{ch}）：站主內頁有文案、複製鈕、{'影片與封面下載' if ch == 'caffaine' else '複製鈕'}", pg.locator("#kit textarea").first.input_value() != "" and pg.locator("#kit [data-copy]").count() >= 2 and (ch != "caffaine" or pg.locator("#kit a[download]").count() >= 2), "")
                    pg.locator("#kit [data-copy=ig]").first.scroll_into_view_if_needed(); pg.locator("#kit [data-copy=ig]").first.click(); pg.wait_for_timeout(400)
                    ok(f"[{T}（{W}）] 發文包（{ch}）：按複製 → 鈕變「已複製」或提示手動複製", pg.locator("#kit [data-copy=ig]").first.inner_text() in ("已複製 ✓", "請按 Ctrl+C"), pg.locator("#kit [data-copy=ig]").first.inner_text())
                    ok(f"[{T}（{W}）] 發文包（{ch}）：沒有橫向捲軸", pg.evaluate(nohs) <= 1, pg.evaluate(nohs))
                open_(pg, base + "c/" + ch + "/#/", ST); pg.wait_for_timeout(2500)
                n = pg.locator("#kitAll .kit1").count()
                ok(f"★ [{T}（{W}）] 發文包總覽（{ch}）：{who}{'看到全部（含狀態）' if adm else '看不到'}", (n >= 2 and pg.locator("#kitAll .kst").count() == n) if adm else n == 0 and pg.locator("#kitAll").count() == 0, n)
                c.close()

        # ── C 正式網域（沒有 TW_PREVIEW）：Worker 未上線 → 假兌換不生效；Worker 回 200 → 生效
        c, pg = ctx("bob@example.com", W, preview=False)
        open_(pg, base + "#unlock/pv-tech/" + _FU_T); pg.wait_for_timeout(1200)
        open_(pg, base + "#articles")
        ok(f"★ [{T}（{W}）] 正式網域：Worker 未上線時 pv-tech 假碼無效，不出現頻道分頁", pg.evaluate(tabs) == [], pg.evaluate(tabs))
        c.close()
        c, pg = ctx("bob@example.com", W, preview=False, mode="ok")
        open_(pg, base + "#unlock/ZZreal.token.abc/" + _FU_T)
        wait_until(pg, "() => document.getElementById('artChl') && document.getElementById('artChl').dataset.st === 'ok'", 8000)
        ok(f"★ [{T}（{W}）] 正式網域＋Worker 回已解鎖 → 科技頻道生效（真的打了兌換端點）", pg.evaluate(chl) == "ok" and state["redeemed"] >= 1, [pg.evaluate(chl), state["redeemed"]])
        c.close()

        # ── E 站主：四個頻道分頁都看得到（變淡樣式），不需解鎖
        c, pg = ctx("andy@example.com", W, admin=True)
        open_(pg, base + "#articles")
        wait_until(pg, tabs + ".length >= 4", 10000)
        ok(f"★ [{T}（{W}）] 站主：四個頻道分頁都看得到、不受解鎖限制", sorted(pg.evaluate(tabs)) == ["caffaine", "healing", "ligu", "tech"], pg.evaluate(tabs))
        c.close()

    # ── F 功能鍵與方案（CLAUDE.md 2026-11-02：新功能一律註冊功能鍵、四方案都寫值）
    c, pg = ctx(None, 1440)
    open_(pg, base + "#articles")
    r = pg.evaluate("""() => { const T = Object.values((window.TW_PLAN_PRESETS || {}).tiers || {}), ks = ['tech','ligu','caffaine','healing'].map(k => 'art.ch.' + k);
      const miss = []; T.forEach(t => ks.forEach(k => { if (!(k in (t.feats || {}))) miss.push(t.name + ':' + k); }));
      const F = (window.TwFeatures && TwFeatures.list ? TwFeatures.list : []).map(x => x.id);
      return { n: T.length, miss, reg: ks.filter(k => F.includes(k)), guest: T.map(t => t.feats['art.ch.tech']) }; }""")
    ok(f"★ [{T}] 功能鍵：四個 art.ch.<頻道> 在每個方案都有值", r["n"] >= 4 and not r["miss"] and len(r["reg"]) == 4 and r["guest"][0] is False, r)
    c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("追蹤解鎖1116", lambda pg, b, base, code: t_followunlock_1116(b, base, code), after="科技透明圈文章1115")
