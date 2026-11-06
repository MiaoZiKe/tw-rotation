# 驗收段落「文章全部分頁隱藏1106」（site/articles.js：「全部文章」分頁也有眼睛、可隱藏；被隱藏時一般人導到第一個沒被隱藏的分頁）
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用，不要 import _uitest。不要在這裡寫三引號模組說明。
# flake8: noqa
# Andy 11-06：精選文章六個分頁只有「全部文章」沒有眼睛（紅框）：「補上隱藏功能」。
# 用假的會員 Worker（狀態存在 Python 端，各瀏覽器共用＝模擬存在伺服器對所有人生效）真的操作：
# 管理者點「全部」眼睛 → 刪除線半透明、伺服器收到 ['all']、重新整理仍在、再點恢復；
# 訪客／一般會員 → 全部分頁不見、打 #articles 導到「快訊」；六個全隱藏 → 一般人導回 #overview、管理者照看。1440 與 390。
import json as _aa_json
import re as _aa_re

_AA_API = "https://acct1106.example.test"


def t_articles_all_hide_1106(b, base, code):
    T = "文章全部分頁隱藏1106"
    errs = []
    st = {"hidden": [], "puts": []}

    def handler(route):
        req = route.request
        path = _aa_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _aa_json.loads(req.post_data or "{}")
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
            else:
                st["hidden"] = list(dict.fromkeys(body.get("hidden") or [])); out = {"ok": True, "hidden": list(st["hidden"])}
        route.fulfill(status=status, body=_aa_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w=1440):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _aa_json.dumps({"api": _AA_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _aa_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_AA_API + "/**", handler)
        c.route("**/articles/postmarket.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_aa_json.dumps({"updated": "", "days": []})))
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
            wait_until(pg, "() => document.querySelectorAll('#artCats .arteye:not([hidden])').length === 6", 10000)
        pg.wait_for_timeout(1500)   # 等 /v1/articles/tabs 回來並重畫（含一般人的導向）

    vis = "() => [...document.querySelectorAll('#artCats>button')].filter(b => b.getClientRects().length).map(b => b.dataset.cat)"
    on = "() => (document.querySelector('#artCats>button.on') || {dataset: {}}).dataset.cat"
    for W in (1440, 390):
        st["hidden"] = []; st["puts"].clear()
        c, pg = ctx("andy@example.com", W)
        open_articles(pg, admin=True)
        g = pg.evaluate("""() => { const t = document.querySelector('#artCats>button[data-cat=all]'), e = t.querySelector('.arteye'), a = e.getBoundingClientRect(), r = t.getBoundingClientRect(),
            lb = t.querySelector(':scope > span:not(.arteye)').getBoundingClientRect(), ne = document.querySelector('#artCats>button[data-cat=news] .arteye').getBoundingClientRect();
            return { shown: e.getClientRects().length > 0, inside: a.left >= r.left - .5 && a.right <= r.right + .5, right: a.left + a.width / 2 > r.left + r.width / 2,
              vc: Math.abs(a.top + a.height / 2 - r.top - r.height / 2) <= 3, noOv: a.left >= lb.right - .5, w: a.width, h: a.height, sameSize: Math.abs(a.width - ne.width) < .5 && Math.abs(a.height - ne.height) < .5,
              sameRight: Math.abs((r.right - a.right) - (document.querySelector('#artCats>button[data-cat=news]').getBoundingClientRect().right - ne.right)) <= 1.5 }; }""")
        ok(f"★ [{T}（{W}）] 管理者：「全部」分頁右邊有眼睛，位置、大小跟其他分頁一樣（靠右、垂直置中、不壓標題、≥24px）",
           g["shown"] and g["inside"] and g["right"] and g["vc"] and g["noOv"] and g["w"] >= 24 and g["h"] >= 24 and g["sameSize"] and g["sameRight"], g)
        ok(f"[{T}（{W}）] 管理者：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        h0 = pg.evaluate("() => location.hash")
        pg.click("#artCats .arteye[data-cat=all]"); pg.wait_for_timeout(500)
        s1 = pg.evaluate("""() => { const t = document.querySelector('#artCats>button[data-cat=all]'), e = t.querySelector('.arteye'), l = t.querySelector(':scope > span:not(.arteye)');
            return { hid: t.classList.contains('hid'), op: parseFloat(getComputedStyle(t).opacity), shown: t.getClientRects().length > 0, ln: getComputedStyle(l).textDecorationLine, pressed: e.getAttribute('aria-pressed') }; }""")
        ok(f"★ [{T}（{W}）] 管理者按「全部」眼睛 → 半透明＋刪除線（還看得到）、眼睛斜線、伺服器收到 ['all']、沒有跳頁",
           s1["hid"] and s1["op"] < 0.8 and s1["shown"] and "line-through" in s1["ln"] and s1["pressed"] == "true" and st["hidden"] == ["all"] and pg.evaluate("() => location.hash") == h0, [s1, st["hidden"]])
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('.arteye.off')", 15000); pg.wait_for_timeout(600)
        ok(f"★ [{T}（{W}）] 重新整理後「全部」仍是隱藏狀態（斜線眼睛）", pg.evaluate("() => document.querySelector('#artCats>button[data-cat=all]').classList.contains('hid')")
           and pg.locator("#artCats .arteye.off").count() == 1)
        c.close()

        for who, mail in (("訪客", None), ("一般會員", "bob@example.com")):
            c, pg = ctx(mail, W)
            open_articles(pg)
            ok(f"★ [{T}（{W}）] {who}：「全部」分頁不見，只剩 快訊／產業鏈／知識／盤前／盤後", pg.evaluate(vis) == ["news", "intro", "know", "premarket", "postmarket"], pg.evaluate(vis))
            ok(f"★ [{T}（{W}）] {who}：打 #articles → 自動落在第一個沒被隱藏的分頁（比比快訊）", pg.evaluate("() => location.hash") == "#articles/news" and pg.evaluate(on) == "news",
               [pg.evaluate("() => location.hash"), pg.evaluate(on)])
            ok(f"[{T}（{W}）] {who}：看不到眼睛、沒有橫向捲軸", pg.evaluate("() => [...document.querySelectorAll('.arteye')].every(e => e.getClientRects().length === 0)")
               and pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
            c.close()

        # 所有分頁都隱藏：一般人整個精選文章關閉 → #overview（比照側欄隱藏）；管理者仍六個分頁都看得到
        st["hidden"] = ["all", "news", "intro", "know", "premarket", "postmarket"]
        c, pg = ctx(None, W)
        pg.goto(base + "#articles", wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
        ok(f"★ [{T}（{W}）] 全部分頁都隱藏 → 訪客打 #articles 導回 #overview（不是空白頁、不無限導向）", pg.evaluate("() => location.hash") == "#overview", pg.evaluate("() => location.hash"))
        pg.goto(base + "#articles/know", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        ok(f"[{T}（{W}）] 全部分頁都隱藏 → 訪客打 #articles/know 也導回 #overview", pg.evaluate("() => location.hash") == "#overview", pg.evaluate("() => location.hash"))
        c.close()
        c, pg = ctx("andy@example.com", W)
        open_articles(pg, admin=True)
        ok(f"[{T}（{W}）] 全部分頁都隱藏 → 管理者仍看得到六個分頁（全是半透明）、可以再點恢復", len(pg.evaluate(vis)) == 6 and pg.locator("#artCats>button.hid").count() == 6)

        # 再按一次恢復 → 訪客又看得到「全部」並落在全部
        st["hidden"] = ["all"]
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => document.querySelectorAll('.arteye.off').length === 1", 15000)
        pg.click("#artCats .arteye[data-cat=all]"); pg.wait_for_timeout(500)
        ok(f"★ [{T}（{W}）] 管理者再按「全部」眼睛 → 恢復不透明、伺服器 []", st["hidden"] == [] and not pg.evaluate("() => document.querySelector('#artCats>button[data-cat=all]').classList.contains('hid')"), st["hidden"])
        c.close()
        c, pg = ctx(None, W); open_articles(pg)
        ok(f"★ [{T}（{W}）] 訪客重新開 → 六個分頁回來、落在「全部文章」", pg.evaluate(vis) == ["all", "news", "intro", "know", "premarket", "postmarket"] and pg.evaluate(on) == "all", [pg.evaluate(vis), pg.evaluate(on)])
        c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("文章全部分頁隱藏1106", lambda pg, b, base, code: t_articles_all_hide_1106(b, base, code))
