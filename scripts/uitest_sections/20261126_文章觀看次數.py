# 驗收段落「文章觀看次數1126」（site/articles.js：觀看次數、站主 24H 逐時圖、單篇隱藏眼睛）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-26：「每篇文章都要新增觀看次數 以及 24H 以小時為單位的觀看統計。觀看次數一般人可以看到，但是何時觀看的次數只有我可以看」
# Andy 11-26：「每個文章都具備 隱藏功能 和觀看功能 隱藏功能只有我可以動」
# 真的操作：訪客看得到「N 次觀看」、看不到逐時圖與眼睛鈕；站主看得到逐時圖、點眼睛隱藏 → 訪客清單少一篇、直接連結顯示已隱藏 → 再點恢復。
import json as _v6_json
import os as _v6_os
import re as _v6_re

_V6_API = "https://acct1126vw.example.test"
_V6_SHOT = _v6_os.environ.get("TW_SHOT_DIR", "/tmp/claude-0/-home-user/d68c9f33-7cf0-5a76-b297-0eb800ee0511/scratchpad/shots")


def t_art_views_1126(b, base, code):
    T = "文章觀看次數1126"
    errs = []
    st = {"hidden": set(), "hourly_calls": [], "views": {}}

    def handler(route):
        req = route.request
        path = _v6_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _v6_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        adm = bool(email and email.startswith("admin"))
        out, s = {}, 200
        if path == "/v1/me":
            out = {"user": {"email": email, "name": email.split("@")[0], "admin": adm}} if email else {"error": "auth"}
            s = 200 if email else 401
        elif path == "/v1/perm/me":
            out = {"who": "admin" if adm else ("member" if email else "guest"), "plan": "pro" if adm else "free", "planName": "站主" if adm else "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        elif path == "/v1/articles/stats":
            out = {"views": st["views"]}
        elif path == "/v1/articles/view":
            out = {"ok": True, "id": body.get("id"), "views": st["views"].get(body.get("id"), 0)}
        elif path == "/v1/articles/hidden":
            out = {"ids": sorted(st["hidden"])}
        elif path == "/v1/articles/hidden/put":
            if not adm: out, s = {"error": "forbidden"}, 403
            else:
                (st["hidden"].add if body.get("hide") else st["hidden"].discard)(body.get("id"))
                out = {"ok": True, "ids": sorted(st["hidden"])}
        elif path == "/v1/articles/get":
            out = {"ok": True, "post": {"id": body.get("id"), "cat": "know", "title": "驗收用文章", "date": "2026-10-20", "blocks": [{"t": "p", "text": "內文"}]}, "limit": None, "reads": []} if adm else {"error": "auth"}
            s = 200 if adm else 401
        elif path == "/v1/articles/stats/hourly":
            st["hourly_calls"].append(adm)
            if not adm: out, s = {"error": "forbidden"}, 403
            else: out = {"id": body.get("id"), "end": 1764140400000, "hours": [0, 0, 1, 0, 2, 0, 0, 0, 3, 5, 8, 6, 4, 2, 1, 0, 0, 2, 3, 7, 9, 4, 2, 1]}
        route.fulfill(status=s, body=_v6_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w=1440):
        c = b.new_context(viewport={"width": w, "height": 900})
        init = "window.TW_ACCOUNT_OVERRIDE = " + _v6_json.dumps({"api": _V6_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');sessionStorage.clear();"
        init += ("localStorage.setItem('tw.acct.tok'," + _v6_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_V6_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_, sel):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        try:
            ag.first.wait_for(timeout=2500); ag.first.click(timeout=1500)
        except Exception: pass
        wait_until(pg, "() => !!document.querySelector('%s')" % sel.replace(" .artc", ""), 20000)
        pg.wait_for_timeout(1200)
        if pg.query_selector("#artFrom"):   # 文章都超過一個月：日期區間放寬，所有文章都進清單
            pg.fill("#artFrom", "2020-01-01"); pg.dispatch_event("#artFrom", "change"); pg.wait_for_timeout(600)

    _v6_os.makedirs(_V6_SHOT, exist_ok=True)
    ids = "() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.id)"

    # ① 訪客：先抓清單，給每篇一個觀看數
    c, pg = ctx(None)
    open_(pg, "#articles", "#artList .artc")
    vis = pg.evaluate(ids)
    ok(f"[{T}] 訪客清單有文章", len(vis) >= 2, len(vis))
    for i, a in enumerate(vis):
        st["views"][a] = 1200 + i * 7
    c.close(); c, pg = ctx(None)
    open_(pg, "#articles", "#artList .artc")
    wait_until(pg, "() => !!document.querySelector('#artList [data-vw]:not([hidden])')", 8000)
    vw = pg.evaluate("() => [...document.querySelectorAll('#artList .artc')].map(a => { const v = a.querySelector('[data-vw]'); return [a.dataset.id, v && !v.hidden ? v.textContent.trim() : null]; })")
    ok(f"★ [{T}] 訪客：每張卡片寫「N 次觀看」", all(x[1] == f"{st['views'][x[0]]:,} 次觀看" for x in vw), vw[:4])
    ok(f"★ [{T}] 訪客：卡片上沒有隱藏眼睛鈕", pg.evaluate("() => document.querySelectorAll('.artceye').length") == 0)
    ok(f"[{T}] 沒有右側側欄、卡片區吃滿", pg.evaluate("() => !document.getElementById('artSide') && document.getElementById('artList').getBoundingClientRect().width > 1000"))
    target = vis[0]
    open_(pg, "#article/" + target, "#artPost")
    pg.wait_for_timeout(1000)
    p = pg.evaluate("() => ({ vw: (document.querySelector('#artPost .artmeta [data-vw]:not([hidden])') || {}).textContent, hr: !!document.getElementById('artHourly'), eye: document.querySelectorAll('.artceye').length })")
    ok(f"★ [{T}] 訪客單篇：有觀看次數、沒有逐時圖、沒有眼睛鈕、沒去要逐時資料", bool(p["vw"]) and "次觀看" in p["vw"] and not p["hr"] and p["eye"] == 0 and True not in st["hourly_calls"] and False not in st["hourly_calls"], [p, st["hourly_calls"]])
    c.close()

    # ② 站主：逐時圖＋眼睛隱藏
    ca, pa = ctx("admin@example.com")
    open_(pa, "#article/" + target, "#artPost")
    wait_until(pa, "() => !!document.getElementById('artHourly')", 8000)
    h = pa.evaluate("() => { const s = document.getElementById('artHourly'); return s ? { bars: s.querySelectorAll('rect.bar').length, tot: s.dataset.tot, avg: !!s.querySelector('.avg'), mx: (s.querySelector('.mx') || {}).textContent } : null }")
    ok(f"★ [{T}] 站主單篇：24 小時逐時直條 24 根、共 60 次、有平均虛線、只標最高 9", bool(h) and h["bars"] == 24 and h["tot"] == "60" and h["avg"] and h["mx"] == "9", h)
    pa.locator("#artHourly").scroll_into_view_if_needed()
    pa.locator("#artPost").screenshot(path=f"{_V6_SHOT}/views_owner_hourly_1440.png")
    open_(pa, "#articles", "#artList .artc")
    ok(f"[{T}] 站主清單：每張卡片都有眼睛鈕", pa.evaluate("() => document.querySelectorAll('#artList .artc').length === document.querySelectorAll('#artList .artc .artceye').length"))
    pa.click(f"#artList .artc[data-id='{target}'] .artceye"); pa.wait_for_timeout(600)
    s1 = pa.evaluate(f"() => {{ const a = document.querySelector(\"#artList .artc[data-id='{target}']\"); return a ? {{ hidd: a.classList.contains('hidd'), off: a.querySelector('.artceye').classList.contains('off') }} : null }}")
    ok(f"★ [{T}] 站主點眼睛 → 伺服器名單有這篇、站主仍看得到但變灰＋劃線眼睛、沒跳到文章頁", target in st["hidden"] and bool(s1) and s1["hidd"] and s1["off"] and pa.url.endswith("#articles"), [s1, pa.url])
    pa.screenshot(path=f"{_V6_SHOT}/views_list_owner_1440.png")

    cv, pv = ctx(None)
    open_(pv, "#articles", "#artList .artc")
    v2 = pv.evaluate(ids)
    ok(f"★ [{T}] 隱藏後訪客清單少一篇、看不到那篇", target not in v2 and len(v2) == len(vis) - 1, [len(v2), len(vis)])
    open_(pv, "#article/" + target, "#artPost")
    ok(f"★ [{T}] 隱藏後訪客直接連結顯示「此文章已隱藏」", "此文章已隱藏" in pv.evaluate("() => document.getElementById('artPost').textContent"))

    pa.click(f"#artList .artc[data-id='{target}'] .artceye"); pa.wait_for_timeout(600)
    ok(f"★ [{T}] 站主再點眼睛 → 恢復", target not in st["hidden"] and not pa.evaluate(f"() => document.querySelector(\"#artList .artc[data-id='{target}']\").classList.contains('hidd')"))
    cv.close(); cv, pv = ctx(None)
    open_(pv, "#articles", "#artList .artc")
    pv.wait_for_timeout(500)
    ok(f"★ [{T}] 恢復後訪客清單回到原本篇數", len(pv.evaluate(ids)) == len(vis), len(pv.evaluate(ids)))
    pv.screenshot(path=f"{_V6_SHOT}/views_list_guest_1440.png")
    cv.close(); ca.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章觀看次數1126", lambda pg, b, base, code: t_art_views_1126(b, base, code))
