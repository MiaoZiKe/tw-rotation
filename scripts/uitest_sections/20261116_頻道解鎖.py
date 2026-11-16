# 驗收段落「頻道解鎖1116」（site/articles.js 的 tw.chunl／?tc= 憑證、chBanner、articles/unlock.json）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-16：「沒註冊只能看那篇文章；有註冊且有追蹤頻道則可以看該頻道的所有文章」。
# 真的操作：訪客用私訊連結（?tc=碼）→ 只能讀那一篇、看到「註冊並追蹤」提示、?tc 被拿掉、分頁仍藏；
# 會員用同一連結 → 分頁出現（不變淡）、點進去看到頻道全部文章；沒帶碼或碼錯 → 不解鎖；訪客先解鎖、之後登入 → 自動生效。1440 與 390。
import hashlib as _cu_hash
import json as _cu_json
import re as _cu_re

_CU_API = "https://acct1116.example.test"
_CU_ID = "2026-11-15-tech-2nm"
_CU_CODE = "tctest0001"


def t_chunlock_1116(b, base, code):
    T = "頻道解鎖1116"
    errs = []
    h = _cu_hash.sha256(_CU_CODE.encode()).hexdigest()

    def handler(route):
        req = route.request
        path = _cu_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _cu_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": email, "name": email.split("@")[0], "admin": False}} if email else {"error": "auth"}
        elif path == "/v1/perm/me":
            out = {"who": "member" if email else "guest", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_cu_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _cu_json.dumps({"api": _CU_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _cu_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        # 只在這個分頁第一次載入時清憑證，重新整理要留著驗「記在這台裝置」
        init += "try{if(!sessionStorage.getItem('zzUnl')){localStorage.removeItem('tw.chunl');sessionStorage.setItem('zzUnl','1')}}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/articles/unlock.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_cu_json.dumps({"tech": {"sha256": [h]}})))
        c.route(_CU_API + "/**", handler)
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

    tabvis = "() => { const b = document.querySelector('#artCats>button[data-cat=tech]'); return !!b && !b.hidden && b.getClientRects().length > 0; }"
    cards = "() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.id + '|' + a.dataset.cat)"
    chl = "() => { const e = document.getElementById('artChl'); return e ? e.dataset.st : ''; }"
    for W in (1440, 390):
        # ── A 訪客用私訊連結：能讀那一篇、有註冊提示、?tc 被拿掉、分頁仍藏
        c, pg = ctx(None, W)
        open_(pg, base + "?tc=" + _CU_CODE + "#article/" + _CU_ID)
        ok(f"★ [{T}（{W}）] 訪客：私訊連結打得開那一篇", "兩奈米" in pg.inner_text("#artPost .artttl"), "")
        ok(f"[{T}（{W}）] 訪客：網址的 ?tc= 憑證被拿掉（不留在書籤）", "tc=" not in pg.evaluate("() => location.href"), pg.evaluate("() => location.href"))
        ok(f"★ [{T}（{W}）] 訪客：文章上方有「註冊並追蹤頻道，即可看全部文章」提示＋登入／註冊鈕", pg.evaluate(chl) == "guest" and "註冊並追蹤" in pg.inner_text("#artChl") and pg.locator("#artChlLogin").count() == 1, pg.evaluate(chl))
        ok(f"[{T}（{W}）] 訪客：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        pg.locator("#artChlLogin").scroll_into_view_if_needed(); pg.click("#artChlLogin"); pg.wait_for_timeout(800)
        ok(f"★ [{T}（{W}）] 訪客：按「登入／註冊」→ 跳出登入視窗", pg.evaluate("() => !!document.querySelector('[role=dialog], .acctdlg, #acctDlg, .tw-dlg')"), "")
        open_(pg, base + "#articles")
        ok(f"★ [{T}（{W}）] 訪客：回清單，分頁列仍沒有「科技透明圈」（要註冊才看得到）", not pg.evaluate(tabvis), "")
        pg.goto(base + "#articles/tech", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
        ok(f"[{T}（{W}）] 訪客：直接打 #articles/tech → 導回 #articles", pg.evaluate("() => location.hash") == "#articles", pg.evaluate("() => location.hash"))
        # ── D 訪客先解鎖，之後才登入（同一台裝置）→ 自動生效
        saved = pg.evaluate("() => localStorage.getItem('tw.chunl')")
        c.add_init_script("try{localStorage.setItem('tw.acct.tok','tok-dora@example.com');localStorage.setItem('tw.chunl'," + _cu_json.dumps(saved) + ")}catch(e){}")   # 之後才登入：補一支在清權杖那支之後跑的 init；只對「之後開的新分頁」生效
        pg.close(); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}:{e}"))
        open_(pg, base + "#articles")
        wait_until(pg, tabvis, 8000)
        ok(f"★ [{T}（{W}）] 先解鎖、之後登入同一台裝置 → 「科技透明圈」分頁自動出現", pg.evaluate(tabvis), pg.evaluate("() => [localStorage.getItem('tw.chunl'), localStorage.getItem('tw.acct.tok'), (window.TwAccount&&TwAccount.user())&&1]"))
        c.close()

        # ── B/C 已登入會員
        c, pg = ctx("bob@example.com", W)
        open_(pg, base + "#article/" + _CU_ID)
        ok(f"★ [{T}（{W}）] 會員沒帶憑證直接開：能讀那一篇，提示「還沒解鎖全部」、分頁仍藏", pg.evaluate(chl) == "nogate" and not pg.evaluate(tabvis), pg.evaluate(chl))
        open_(pg, base + "?tc=wrongcode99#article/" + _CU_ID)
        ok(f"[{T}（{W}）] 會員帶錯誤憑證：不解鎖", pg.evaluate(chl) == "nogate" and not pg.evaluate(tabvis), pg.evaluate(chl))
        open_(pg, base + "?tc=" + _CU_CODE + "#article/" + _CU_ID)
        ok(f"★ [{T}（{W}）] 會員帶正確憑證：提示「已解鎖」＋「看…全部文章」鈕", pg.evaluate(chl) == "ok" and pg.locator("#artChlGo").count() == 1, pg.evaluate(chl))
        pg.locator("#artChlGo").scroll_into_view_if_needed(); pg.click("#artChlGo"); pg.wait_for_timeout(1500)
        wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 10000)
        ok(f"★ [{T}（{W}）] 會員：點鈕 → #articles/tech，清單列出頻道文章（含兩奈米）", pg.evaluate("() => location.hash") == "#articles/tech" and _CU_ID + "|tech" in pg.evaluate(cards), [pg.evaluate("() => location.hash"), pg.evaluate(cards)])
        st = pg.evaluate("() => { const t = document.querySelector('#artCats>button[data-cat=tech]'); return { on: t.classList.contains('on'), hid: t.classList.contains('hid'), op: parseFloat(getComputedStyle(t).opacity) }; }")
        ok(f"[{T}（{W}）] 會員：科技透明圈分頁亮起、不是站主的「變淡」樣式", st["on"] and not st["hid"] and st["op"] >= 0.9, st)
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 12000)
        ok(f"[{T}（{W}）] 會員：重新整理仍在頻道清單（解鎖記在這台裝置）", pg.evaluate("() => location.hash") == "#articles/tech", pg.evaluate("() => location.hash"))
        ok(f"[{T}（{W}）] 會員：頻道清單沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        open_(pg, base + "#articles")
        ok(f"[{T}（{W}）] 會員：「全部文章」清單仍不混進頻道文章", not any(x.endswith("|tech") for x in pg.evaluate(cards)), pg.evaluate(cards)[:3])
        c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("頻道解鎖1116", lambda pg, b, base, code: t_chunlock_1116(b, base, code), after="科技透明圈文章1115")
