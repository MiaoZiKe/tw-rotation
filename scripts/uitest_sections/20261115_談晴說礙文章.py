# 驗收段落「談晴說礙文章1115」（site/articles.js 的 PRIV 頻道隱藏分頁、site/articles/healing/；複製自 20261115_哩股哩股文章.py）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-15：「所有頻道都需要這樣」—— 每篇貼文也存成精選文章裡自己頻道的隱藏分頁（對外不顯示、只有站主看得到）。
# 四件事都真的操作：① 訪客／一般會員看不到「談晴說礙」分頁、直接打 #articles/healing 被導回；② 「全部文章」列表、搜尋、側欄都不列這篇；
# ③ 站主看得到分頁（變淡＋刪除線、沒有眼睛）、點進去看到那一篇；④ 任何人用直接連結 #article/<id> 打得開全文與出處，找不到的 id 顯示找不到。1440 與 390。
import json as _hl_json
import re as _hl_re

_HL_API = "https://acct1117.example.test"
_HL_ID = "2026-11-14-healing-resume"
_HL_TITLE = "48%求職青年"


def t_healing_articles_1115(b, base, code):
    T = "談晴說礙文章1115"
    errs = []

    def handler(route):
        req = route.request
        path = _hl_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _hl_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": email, "name": email.split("@")[0], "admin": email == "andy@example.com"}} if email else {"error": "auth"}
        elif path == "/v1/perm/me":
            out = {"who": "member" if email else "guest", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_hl_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _hl_json.dumps({"api": _HL_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _hl_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_HL_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=all]') || !!document.querySelector('#artPost')", 20000)
        pg.wait_for_timeout(1500)

    vis = "() => [...document.querySelectorAll('#artCats>button')].filter(b => b.getClientRects().length).map(b => b.dataset.cat)"
    cards = "() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.id + '|' + a.dataset.cat)"
    for W in (1440, 390):
        # ── 訪客與一般會員：看不到分頁、全部文章不列、搜尋搜不到、直接打分頁被導回
        for who, mail in (("訪客", None), ("一般會員", "bob@example.com")):
            c, pg = ctx(mail, W)
            open_(pg, "#articles")
            ok(f"★ [{T}（{W}）] {who}：分頁列沒有「談晴說礙」", "healing" not in pg.evaluate(vis), pg.evaluate(vis))
            ok(f"[{T}（{W}）] {who}：分頁按鈕雖在 DOM 但是 hidden（不佔位）", pg.evaluate("() => { const b = document.querySelector('#artCats>button[data-cat=healing]'); return !b || b.hidden || b.getClientRects().length === 0; }"))
            lst = pg.evaluate(cards)
            ok(f"★ [{T}（{W}）] {who}：「全部文章」列表沒有這篇、沒有任何 healing 卡片（共 {len(lst)} 篇）", not any(_HL_ID in x or x.endswith("|healing") for x in lst), lst[:5])
            vt = pg.evaluate("() => [...document.querySelectorAll('#artList, #artSide, #artCats>button:not([hidden])')].map(e => e.textContent).join(' ')")
            ok(f"[{T}（{W}）] {who}：列表、側欄、分頁列的文字都不含「談晴說礙」「不敢投履歷」", "不敢投履歷" not in vt and "談晴說礙" not in vt, "")
            q = pg.locator("#artQ"); q.fill("不敢投履歷"); pg.wait_for_timeout(500)
            ok(f"★ [{T}（{W}）] {who}：搜尋「不敢投履歷」→ 0 篇", pg.locator("#artList .artc").count() == 0 and pg.evaluate("() => document.getElementById('artCount').dataset.n") == "0", pg.evaluate("() => document.getElementById('artCount').textContent"))
            pg.goto(base + "#articles/healing", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
            ok(f"★ [{T}（{W}）] {who}：直接打 #articles/healing → 導回 #articles、亮起的是「全部」", pg.evaluate("() => location.hash") == "#articles" and pg.evaluate("() => document.querySelector('#artCats>button.on').dataset.cat") == "all", pg.evaluate("() => location.hash"))
            # 直接連結：誰都打得開
            open_(pg, "#article/" + _HL_ID)
            wait_until(pg, "() => !!document.querySelector('#artPost .artttl')", 15000)
            ok(f"★ [{T}（{W}）] {who}：直接連結 #article/{_HL_ID} 打得開，標題含「{_HL_TITLE}」", _HL_TITLE in (pg.inner_text("#artPost .artttl") if pg.locator("#artPost .artttl").count() else ""), pg.inner_text("#artPost")[:80])
            body = pg.inner_text("#artBody")
            ok(f"[{T}（{W}）] {who}：內文有文案全文（民調口徑、1925 安心專線）、沒有升級鎖定卡", "這是民調" in body and "1925" in body and pg.locator(".artpost .lockcard, .artpost .artlock, #artQuota:visible").count() == 0, body[:80])
            pg.locator(".artimgs").first.scroll_into_view_if_needed(); pg.wait_for_timeout(800)
            im = pg.evaluate("() => [...document.querySelectorAll('.artimgs img')].map(i => ({src: i.getAttribute('src'), w: i.naturalWidth, cw: i.clientWidth}))")
            ok(f"★ [{T}（{W}）] {who}：3 張貼文圖都載得出來（naturalWidth 1080、在文章欄內）", len(im) == 3 and all(x["w"] == 1080 and 0 < x["cw"] <= W for x in im), im)
            lk = pg.evaluate("() => [...document.querySelectorAll('.artxl a')].map(a => a.href)")
            ok(f"★ [{T}（{W}）] {who}：發布紀錄有 IG 與 Threads 公開網址兩個連結", len(lk) == 2 and "instagram.com/p/" in lk[0] and "threads.com/" in lk[1], lk)
            pg.evaluate("() => document.querySelectorAll('details.artfold').forEach(d => d.open = true)")
            ok(f"★ [{T}（{W}）] {who}：出處清單 ≥ 4 筆、每筆有日期、一手發布者寫明民調與樣本數", pg.locator(".artsrc li").count() >= 4 and all(_hl_re.search(r"20\d\d", t) for t in pg.locator(".artsrc li").all_inner_texts()) and "1,114" in pg.inner_text(".artsrc"), pg.locator(".artsrc li").count())
            ok(f"[{T}（{W}）] {who}：文章裡不用「我／我們」（1925 的「依舊愛我」是專線名稱除外）", not _hl_re.search(r"我", body.replace("依舊愛我", "")), _hl_re.findall(r".{0,6}我.{0,6}", body)[:3])
            ok(f"[{T}（{W}）] {who}：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
            pg.locator("#artBack").click(); pg.wait_for_timeout(800)
            ok(f"[{T}（{W}）] {who}：「← 返回」回到文章清單，且清單仍不列這篇", pg.evaluate("() => location.hash").startswith("#articles") and not any(_HL_ID in x for x in pg.evaluate(cards)), pg.evaluate("() => location.hash"))
            open_(pg, "#article/2026-11-14-healing-not-exist")
            ok(f"[{T}（{W}）] {who}：不存在的 id → 顯示「暫時讀不到」", pg.locator("#artErr").count() == 1, "")
            c.close()

        # ── 站主：分頁在、變淡＋刪除線、沒有眼睛、點進去看到那篇；全部文章仍不列
        c, pg = ctx("andy@example.com", W)
        open_(pg, "#articles")
        wait_until(pg, "() => [...document.querySelectorAll('#artCats>button')].some(b => b.dataset.cat === 'healing' && b.getClientRects().length)", 10000)
        ok(f"★ [{T}（{W}）] 站主：分頁列（消息分頁之後）多一格「談晴說礙」", "healing" in pg.evaluate(vis) and pg.evaluate(vis).index("healing") > pg.evaluate(vis).index("postmarket"), pg.evaluate(vis))
        st = pg.evaluate("""() => { const t = document.querySelector('#artCats>button[data-cat=healing]'), s = t.querySelector(':scope > span:not(.arteye)'), e = t.querySelector('.arteye');
            return { hid: t.classList.contains('hid'), op: parseFloat(getComputedStyle(t).opacity), line: getComputedStyle(s).textDecorationLine, eye: e ? e.getClientRects().length : 0, title: t.title }; }""")
        ok(f"★ [{T}（{W}）] 站主：分頁變淡（opacity<0.8）、文字刪除線、沒有眼睛（不能被打開成公開）", st["hid"] and st["op"] < 0.8 and "line-through" in st["line"] and st["eye"] == 0, st)
        ok(f"[{T}（{W}）] 站主：全部文章列表仍不列這篇", not any(_HL_ID in x for x in pg.evaluate(cards)), pg.evaluate(cards)[:3])
        pg.locator("#artCats>button[data-cat=healing]").scroll_into_view_if_needed()
        pg.click("#artCats>button[data-cat=healing]"); pg.wait_for_timeout(1200)
        ok(f"★ [{T}（{W}）] 站主：點分頁 → #articles/healing、亮起、清單有 6 篇、都是 healing、含這一篇", pg.evaluate("() => location.hash") == "#articles/healing" and pg.evaluate("() => document.querySelector('#artCats>button.on').dataset.cat") == "healing" and len(pg.evaluate(cards)) >= 6 and all(x.endswith("|healing") for x in pg.evaluate(cards)) and (_HL_ID + "|healing") in pg.evaluate(cards), [pg.evaluate("() => location.hash"), pg.evaluate(cards)])
        pg.click(f"#artList .artc[data-id='{_HL_ID}']"); pg.wait_for_timeout(1500)
        ok(f"★ [{T}（{W}）] 站主：點卡片 → 打開全文 #article/{_HL_ID}", pg.evaluate("() => location.hash") == "#article/" + _HL_ID and _HL_TITLE in pg.inner_text("#artPost .artttl"), pg.evaluate("() => location.hash"))
        ok(f"[{T}（{W}）] 站主：文章沒有「全文額度」字樣（不佔額度）", "全文額度" not in pg.inner_text("#artPost"))
        c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("談晴說礙文章1115", lambda pg, b, base, code: t_healing_articles_1115(b, base, code))
