# 驗收段落「文章模式1126」（site/site_mode.js：全站只開放精選文章）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-26：「整站切成『只開放文章』模式」「只有對應的該頻道文章」。
# 真的操作：訪客與一般會員打各工具路由 → 全被導到 #articles、選單（電腦版側欄＋手機抽屜）只剩精選文章、搜尋與導覽鈕不見；
#           #pricing、法律頁照常開，付費卡的鈕是「預約」不是結帳；站主打 #flow 不被導走、頁首有小標、按「以一般人視角預覽」真的變成訪客畫面。
import json as _am_json
import re as _am_re

_AM_API = "https://acct1126am.example.test"
_AM_TOOLS = ["#overview", "#flow", "#stock/2330", "#industry", "#heatmap", "#market/credit", "#etf", "#watch", "#explore", "#season", "#earnings", ""]


def t_article_mode_1126(b, base, code):
    T = "文章模式1126"
    errs = []

    def handler(route):
        req = route.request
        path = _am_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _am_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        adm = bool(email and email.startswith("admin"))
        out, s = {}, 200
        if path == "/v1/me":
            out, s = ({"user": {"email": email, "name": "x", "admin": adm}}, 200) if email else ({"error": "auth"}, 401)
        elif path == "/v1/perm/me":
            out = {"who": "admin" if adm else ("member" if email else "guest"), "plan": "pro" if adm else "free", "planName": "站主" if adm else "免費", "feats": {}, "lims": {}}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        elif path == "/v1/articles/hidden":
            out = {"ids": []}
        elif path == "/v1/plans/public":
            out = {"plans": [{"id": "free", "name": "註冊會員", "builtin": True, "feats": {}, "lims": {}, "price": 0},
                             {"id": "plus", "name": "Plus", "feats": {}, "lims": {}, "price": 199, "price_year": 1990},
                             {"id": "pro", "name": "Pro", "feats": {}, "lims": {}, "price": 399, "price_year": 3990}]}
        elif path == "/v1/nav/hidden":
            out = {"hidden": []}
        else:
            out = {"ok": True}
        route.fulfill(status=s, body=_am_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w=1440, h=900):
        c = b.new_context(viewport={"width": w, "height": h})
        init = "window.TW_SITE_MODE_OFF = 0;window.TW_ACCOUNT_OVERRIDE = " + _am_json.dumps({"api": _AM_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _am_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_AM_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        return c, pg

    side = """() => [...document.querySelectorAll('#tabs .tab, #tabs .l4grp, #tabs .l4subtab')].filter(e => e.getClientRects().length && getComputedStyle(e).display !== 'none').map(e => (e.textContent || '').trim().slice(0, 8))"""
    chrome = """() => ['.search', '#evToggle', '#twTourBtn', '#twPageTourBtn', '#m4Search'].filter(s => { const e = document.querySelector(s); return e && e.getClientRects().length && getComputedStyle(e).display !== 'none'; })"""

    for who, email in (("訪客", None), ("一般會員", "member@example.com")):
        c, pg = ctx(email)
        bad = []
        for r in _AM_TOOLS:
            pg.goto(base + r, wait_until="domcontentloaded")
            try:
                ag = pg.get_by_role("button", name="同意並繼續"); ag.first.wait_for(timeout=800); ag.first.click(timeout=1000)
            except Exception: pass
            try: wait_until(pg, "() => location.hash === '#articles'", 6000)
            except Exception: pass
            h = pg.evaluate("location.hash")
            if h != "#articles": bad.append((r, h))
        ok(f"★ [{T}] {who}：{len(_AM_TOOLS)} 條工具路由（含空網址）全被導到 #articles", not bad, bad)
        pg.goto(base + "#articles", wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
        names = pg.evaluate(side)
        ok(f"★ [{T}] {who}：電腦版側欄只剩「精選文章」", names == ["精選文章"] or all(n.startswith("精選文章") for n in names) and len(names) >= 1, names)
        ok(f"[{T}] {who}：搜尋代號、導覽鈕、事件鈕都藏起來", pg.evaluate(chrome) == [], pg.evaluate(chrome))
        ok(f"[{T}] {who}：精選文章頁有畫出來（頻道分頁列在）", pg.evaluate("() => !!document.querySelector('#v-articles.on') && !!document.getElementById('artQ')"))
        # 放行的路由不被導走
        for r in ("#pricing", "#terms", "#privacy", "#refund"):
            pg.goto(base + r, wait_until="domcontentloaded"); pg.wait_for_timeout(700)
            ok(f"[{T}] {who}：{r} 照常開（不被導走）", pg.evaluate("location.hash") == r, pg.evaluate("location.hash"))
        # #pricing 回到預約
        pg.goto(base + "#pricing", wait_until="domcontentloaded"); pg.wait_for_timeout(800)
        try: wait_until(pg, "() => document.querySelectorAll('#v-pricing .prgo').length >= 2", 6000)
        except Exception: pass
        btns = pg.evaluate("() => [...document.querySelectorAll('#v-pricing .prgo')].map(e => e.textContent.trim())")
        want = "免費註冊" if not email else "預約通知"
        ok(f"★ [{T}] {who}：#pricing 付費卡鈕是「{want}」（冷啟動、不開結帳；沒有「訂閱／付款」鈕）", any(want in t for t in btns) and not any(_am_re.search("付款|結帳|訂閱", t) for t in btns), btns)
        ok(f"[{T}] {who}：#pricing 沒有結帳字樣", not pg.evaluate("() => /立即付款|前往結帳|立即訂閱|去付款/.test(document.getElementById('v-pricing').innerText)"))
        c.close()

    # 手機 390：抽屜只剩精選文章
    c, pg = ctx(None, 390, 844)
    pg.goto(base + "#stock/2330", wait_until="domcontentloaded"); pg.wait_for_timeout(2000)
    ok(f"[{T}] 手機訪客：#stock/2330 → #articles", pg.evaluate("location.hash") == "#articles", pg.evaluate("location.hash"))
    try:
        pg.click("#m4Burger", timeout=3000); pg.wait_for_timeout(500)
    except Exception: pass
    items = pg.evaluate("() => [...document.querySelectorAll('#m4Drawer .m4item[data-v]')].filter(e => e.getClientRects().length).map(e => e.dataset.v)")
    ok(f"★ [{T}] 手機訪客：抽屜只剩精選文章", items == ["articles"], items)
    ok(f"[{T}] 手機訪客：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1"))
    c.close()

    # 站主：完整網站、頁首小標、一般人視角預覽
    c, pg = ctx("admin@example.com")
    pg.goto(base + "#flow", wait_until="domcontentloaded")
    try:
        ag = pg.get_by_role("button", name="同意並繼續"); ag.first.wait_for(timeout=800); ag.first.click(timeout=1000)
    except Exception: pass
    pg.wait_for_timeout(2500)
    ok(f"★ [{T}] 站主：打 #flow 不被導走", pg.evaluate("location.hash").startswith("#flow"), pg.evaluate("location.hash"))
    ok(f"★ [{T}] 站主：頁首有「文章模式中（一般人只看得到文章）」小標", pg.evaluate("() => /文章模式中/.test((document.getElementById('siteModeBar') || {}).innerText || '')"))
    n_adm = len(pg.evaluate(side))
    ok(f"[{T}] 站主：側欄看得到完整選單（>1 項）", n_adm > 3, n_adm)
    pg.click("#siteModePv"); pg.wait_for_timeout(800)
    ok(f"★ [{T}] 站主按「以一般人視角預覽」→ 被導到 #articles 且側欄只剩文章", pg.evaluate("location.hash") == "#articles" and len(pg.evaluate(side)) == 1, [pg.evaluate("location.hash"), pg.evaluate(side)])
    pg.click("#siteModePv"); pg.wait_for_timeout(800)
    ok(f"[{T}] 再按「回到站主視角」→ 選單恢復完整", len(pg.evaluate(side)) > 3, pg.evaluate(side))
    c.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章模式1126", lambda pg, b, base, code: t_article_mode_1126(b, base, code))
