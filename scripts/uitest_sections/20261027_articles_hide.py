# 驗收段落「文章分頁隱藏1027」（site/articles.js 的眼睛、盤後消息分頁；workers/account-api/articles.js 的 /v1/articles/tabs）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 10-27：「這邊需要新增一個眼睛 可以讓管理者選擇隱藏，其他所有的分頁也都需要新增隱藏功能 我點擊後其他人就看不到，還需要新增盤後消息 在盤前旁邊」。
# 用假的會員 Worker（page.route，狀態存在 Python 端，三個瀏覽器共用＝模擬「存在伺服器、對所有人生效」）真的操作：
# 管理者點眼睛 → 分頁半透明＋眼睛斜線、伺服器收到；訪客／一般會員 → 那幾個分頁不見、眼睛列不存在、直接打路由導回 #articles；
# 再點一次恢復 → 訪客又看得到；伺服器寫入失敗 → 畫面還原；盤後消息分頁在盤前右邊、空狀態一句話、有資料時可複製整包。1440 與 390。
import json as _ah_json
import re as _ah_re

_AH_API = "https://acct1027.example.test"


def _ah_fake_post(n=3):
    cats = ["總經", "事件", "科技", "新聞"]
    return {"updated": "2026-10-27", "days": [{"date": "2026-10-27", "items": [
        {"cat": cats[i % 4], "title": f"盤後測試標題{i}", "url": f"https://example.com/post/{i}", "source": "鉅亨", "time": "2026-10-27T15:10:00+08:00", "desc": "盤後簡述"} for i in range(n)]}]}


def t_articles_hide_1027(b, base, code):
    T = "文章分頁隱藏1027"
    errs = []
    st = {"hidden": [], "fail": False, "puts": []}

    def handler(route):
        req = route.request
        path = _ah_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _ah_json.loads(req.post_data or "{}")
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
        elif path == "/v1/articles/tabs":
            out = {"hidden": list(st["hidden"])}
        elif path == "/v1/articles/tabs/put":
            st["puts"].append([email, body.get("hidden")])
            if not is_adm: out, status = {"error": "forbidden"}, 403
            elif st["fail"]: out, status = {"error": "boom"}, 500
            else:
                st["hidden"] = list(dict.fromkeys(body.get("hidden") or [])); out = {"ok": True, "hidden": list(st["hidden"])}
        route.fulfill(status=status, body=_ah_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w=1440, post=None):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _ah_json.dumps({"api": _AH_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _ah_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_AH_API + "/**", handler)
        body = _ah_json.dumps(post if post is not None else {"updated": "", "days": []})
        c.route("**/articles/postmarket.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=body))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_articles(pg, hash_="#articles", admin=False):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=postmarket]')", 20000)
        if admin:
            wait_until(pg, "() => document.querySelectorAll('#artCats .arteye:not([hidden])').length === 5", 10000)
        pg.wait_for_timeout(900)   # 等 /v1/articles/tabs 回來並重畫

    vis = "() => [...document.querySelectorAll('#artCats>button')].filter(b => b.getClientRects().length).map(b => b.dataset.cat)"
    for W in (1440, 390):
        mob = W <= 640
        st["hidden"] = []; st["fail"] = False; st["puts"].clear()
        # ── 管理者：六個分頁、五顆眼睛（全部那格沒有）
        c, pg = ctx("andy@example.com", W)
        open_articles(pg, admin=True)
        ok(f"★ [{T}（{W}）] 管理者：分頁順序 全部→快訊→產業鏈→知識→盤前→盤後（盤後在盤前右邊）", pg.evaluate(vis) == ["all", "news", "intro", "know", "premarket", "postmarket"], pg.evaluate(vis))
        geo = pg.evaluate("""() => [...document.querySelectorAll('#artCats .arteye')].map(e => { const t = e.closest('button'), a = e.getBoundingClientRect(), r = t.getBoundingClientRect(), lb = t.querySelector(':scope > span:not(.arteye)').getBoundingClientRect();
            return { cat: e.dataset.cat, own: t.dataset.cat === e.dataset.cat, inside: a.left >= r.left - 0.5 && a.right <= r.right + 0.5 && a.top >= r.top - 0.5 && a.bottom <= r.bottom + 0.5,
              right: (a.left + a.width / 2) > (r.left + r.width / 2), vc: Math.abs((a.top + a.height / 2) - (r.top + r.height / 2)) <= 3, noOverlap: a.left >= lb.right - 0.5, w: a.width, h: a.height }; })""")
        ok(f"★ [{T}（{W}）] 管理者：眼睛 5 顆都在自己標籤裡面、靠右半邊、垂直置中、不壓到標題文字、沒有分頁上方那一列", len(geo) == 5 and all(g["own"] and g["inside"] and g["right"] and g["vc"] and g["noOverlap"] for g in geo)
           and pg.locator("#artEyes").count() == 0, geo)
        ok(f"[{T}（{W}）] 管理者：眼睛點擊區 ≥ 24×24", all(g["w"] >= 24 and g["h"] >= 24 for g in geo), geo)
        ok(f"[{T}（{W}）] 管理者：分頁文字沒被切成「…」（用 canvas 量短名／全名寬度，要放得進標籤扣掉眼睛後的空間）", pg.evaluate("""() => [...document.querySelectorAll('#artCats>button:not([hidden])')].every(b => {
            const cs = getComputedStyle(b), mob = innerWidth <= 640, txt = mob ? b.dataset.s : b.querySelector(':scope > span:not(.arteye)').textContent;
            const c = document.createElement('canvas').getContext('2d'); c.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
            const em = b.querySelector('em'), emW = em && getComputedStyle(em).display !== 'none' ? em.getBoundingClientRect().width + 4 : 0, ic = b.querySelector(':scope > svg'), icW = ic && getComputedStyle(ic).display !== 'none' ? ic.getBoundingClientRect().width + 4 : 0, avail = b.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - emW - icW;
            return c.measureText(txt).width <= avail + 0.5; })"""))
        ok(f"[{T}（{W}）] 管理者：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        if mob:
            ok(f"[{T}（{W}）] 手機：六個分頁都在畫面內、字 ≥ 11px", pg.evaluate("() => [...document.querySelectorAll('#artCats>button')].every(b => { const r = b.getBoundingClientRect(); return r.left >= -1 && r.right <= 391; })")
               and pg.evaluate("() => [...document.querySelectorAll('#artCats>button span')].every(s => parseFloat(getComputedStyle(s).fontSize) >= 11)"))
        h0 = pg.evaluate("() => location.hash")
        pg.click("#artCats .arteye[data-cat=premarket]"); pg.wait_for_timeout(500)
        ok(f"★ [{T}（{W}）] 點眼睛不會切到那個分頁（網址與亮起的分頁都沒變）", pg.evaluate("() => location.hash") == h0 and pg.evaluate("() => document.querySelector('#artCats>button.on').dataset.cat") == "all", pg.evaluate("() => location.hash"))
        s1 = pg.evaluate("""() => { const t = document.querySelector('#artCats>button[data-cat=premarket]'), e = document.querySelector('#artCats .arteye[data-cat=premarket]');
            return { hid: t.classList.contains('hid'), op: parseFloat(getComputedStyle(t).opacity), shown: t.getClientRects().length > 0, pressed: e.getAttribute('aria-pressed'), off: e.classList.contains('off') }; }""")
        ok(f"★ [{T}（{W}）] 管理者點「盤前」眼睛 → 分頁變半透明（還看得到）、眼睛斜線、伺服器收到 ['premarket']",
           s1["hid"] and s1["op"] < 0.8 and s1["shown"] and s1["pressed"] == "true" and s1["off"] and st["hidden"] == ["premarket"], [s1, st["hidden"]])
        pg.click("#artCats .arteye[data-cat=postmarket]"); pg.wait_for_timeout(500)
        ok(f"[{T}（{W}）] 再點「盤後」眼睛 → 伺服器 ['premarket','postmarket']、全部那格沒有眼睛", sorted(st["hidden"]) == ["postmarket", "premarket"]
           and pg.locator("#artCats .arteye[data-cat=all]").count() == 0, st["hidden"])
        # 重新整理後設定還在（存在伺服器，不是只在畫面）
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('.arteye.off')", 15000); pg.wait_for_timeout(600)
        ok(f"[{T}（{W}）] 管理者重新整理 → 兩顆眼睛仍是斜線", pg.locator(".arteye.off").count() == 2)
        c.close()

        # ── 訪客與一般會員：被隱藏的分頁不見、沒有眼睛列
        for who, mail in (("訪客", None), ("一般會員", "bob@example.com")):
            c, pg = ctx(mail, W)
            open_articles(pg)
            ok(f"★ [{T}（{W}）] {who}：只看到 全部／快訊／產業鏈／知識（盤前、盤後不見）", pg.evaluate(vis) == ["all", "news", "intro", "know"], pg.evaluate(vis))
            ok(f"[{T}（{W}）] {who}：看不到任何眼睛、欄數跟著變 4（分頁沒擠成一角）", pg.evaluate("() => [...document.querySelectorAll('.arteye')].every(e => e.getClientRects().length === 0)")
               and pg.evaluate("() => getComputedStyle(document.getElementById('artCats')).gridTemplateColumns.split(' ').length") == 4)
            pg.goto(base + "#articles/premarket", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
            ok(f"★ [{T}（{W}）] {who}：直接打 #articles/premarket → 導回 #articles（停在全部文章）", pg.evaluate("() => location.hash") == "#articles"
               and pg.evaluate("() => document.querySelector('#artCats>button.on').dataset.cat") == "all", pg.evaluate("() => location.hash"))
            pg.goto(base + "#articles/postmarket", wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
            ok(f"[{T}（{W}）] {who}：直接打 #articles/postmarket 一樣導回", pg.evaluate("() => location.hash") == "#articles")
            c.close()
        if W != 1440:
            st["hidden"] = []
            continue

        # ── 一般會員想自己寫入 → 伺服器擋（防偽造）
        c3, pg3 = ctx("bob@example.com", W); open_articles(pg3)
        r403 = pg3.evaluate("async () => { const r = await TwAccount.call('/v1/articles/tabs/put', { hidden: ['news'] }); return r && r._s; }")
        ok(f"[{T}] 一般會員硬打寫入 → 回 403、伺服器設定沒變", r403 == 403 and sorted(st["hidden"]) == ["postmarket", "premarket"], [r403, st["hidden"]])
        c3.close()
        # ── 管理者恢復盤前 → 訪客馬上看得到
        c, pg = ctx("andy@example.com", W); open_articles(pg, admin=True)
        pg.click("#artCats .arteye[data-cat=premarket]"); pg.wait_for_timeout(500)
        ok(f"★ [{T}] 管理者再點「盤前」眼睛 → 伺服器 ['postmarket']、分頁回到不透明", st["hidden"] == ["postmarket"] and not pg.evaluate("() => document.querySelector('#artCats>button[data-cat=premarket]').classList.contains('hid')"), st["hidden"])
        c2, pg2 = ctx(None, W); open_articles(pg2)
        ok(f"★ [{T}] 訪客重新開 → 盤前回來、盤後仍不見", pg2.evaluate(vis) == ["all", "news", "intro", "know", "premarket"], pg2.evaluate(vis))
        c2.close()
        # ── 寫入失敗 → 畫面還原
        st["fail"] = True
        pg.click("#artCats .arteye[data-cat=news]"); pg.wait_for_timeout(900)
        ok(f"★ [{T}] 伺服器寫入失敗（500）→ 快訊分頁不留在半透明、伺服器沒變", not pg.evaluate("() => document.querySelector('#artCats>button[data-cat=news]').classList.contains('hid')") and st["hidden"] == ["postmarket"], st["hidden"])
        st["fail"] = False
        c.close()

    # ── 盤後消息分頁：空狀態與有資料（管理者看得到全部分頁）
    st["hidden"] = []
    for label, post in (("空", None), ("有資料", _ah_fake_post())):
        for W in (1440, 390):
            c, pg = ctx("andy@example.com", W, post=post)
            try: c.grant_permissions(["clipboard-read", "clipboard-write"])
            except Exception: pass
            open_articles(pg, admin=True)
            dbg = pg.evaluate("() => { const t = document.querySelector('#artCats>button[data-cat=postmarket]'), r = t.getBoundingClientRect(), el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); const e = t.querySelector('.arteye').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.width), Math.round(e.left), Math.round(e.width), Math.round(r.left + r.width / 2), el && el.className]; }")
            pg.click("#artCats>button[data-cat=postmarket]"); pg.wait_for_timeout(700)
            tag = f"{T}（盤後 {label}，{W}）"
            ok(f"★ [{tag}] 點分頁 → #articles/postmarket、分頁亮起、文章清單收起", pg.evaluate("() => location.hash") == "#articles/postmarket"
               and pg.evaluate("() => document.querySelector('#artCats>button.on').dataset.cat") == "postmarket" and not pg.locator("#artList").is_visible(), dbg)
            if post is None:
                wait_until(pg, "() => !!document.querySelector('#artPreEmpty')", 8000)
                ok(f"★ [{tag}] 空狀態一句話「今天的盤後消息還沒整理好」、沒有卡片", "今天的盤後消息還沒整理好" in pg.inner_text("#artPre") and pg.locator("#artPre .pmday").count() == 0)
            else:
                wait_until(pg, "() => document.querySelectorAll('#artPre .pmday').length > 0", 8000)
                ok(f"★ [{tag}] 最新一天展開、3 則、標題是新分頁連結", pg.locator("#artPre .pmday.open .pmi").count() == 3 and pg.locator("#artPre a.tt").first.get_attribute("target") == "_blank")
                btn = pg.locator("#artPre .pmcp").first; btn.click(); pg.wait_for_timeout(400)
                clip = btn.get_attribute("data-copied") or ""
                ok(f"★ [{tag}] 複製整包 → 標題行是「【台股盤後消息｜2026-10-27】」", clip.startswith("【台股盤後消息｜2026-10-27】\n1. 總經｜盤後測試標題0\nhttps://example.com/post/0"), clip[:80])
            pg.click("#artCard .howbtn"); pg.wait_for_timeout(300)
            ok(f"[{tag}] 「?」是盤後消息那份（how-artpost）", pg.evaluate("() => document.querySelector('#artCard .howbtn').dataset.how") == "artpost"
               and "所以" in pg.evaluate("() => (document.getElementById('how-artpost') || {}).textContent || ''"))
            pg.keyboard.press("Escape"); pg.mouse.click(5, 5)
            ok(f"[{tag}] 沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
            c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("文章分頁隱藏1027", lambda pg, b, base, code: t_articles_hide_1027(b, base, code))
