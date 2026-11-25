# 驗收段落「頻道分頁眼睛1125」（site/articles.js 的 PRIV 頻道分頁眼睛、'show'+key 標記）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-25：「為何我無法設定隱藏和顯示」（科技透明圈／哩股哩股／CaffAIne／談晴說礙四個分頁沒有眼睛）。
# 真的操作：站主 1440／390 看到四個頻道分頁都有眼睛 → 點眼睛打開 → 送出的清單含 showtech、分頁不再變淡 →
# 訪客（共用同一份伺服器狀態）看得到分頁與那篇、直接打 #articles/tech 不被導回 → 再點一次關掉 → 訪客又看不到。預設仍是隱藏。
import json as _ce_json
import re as _ce_re

_CE_API = "https://acct1125.example.test"
_CE_CH = ["tech", "ligu", "caffaine", "healing"]


def t_chan_eye_1125(b, base, code):
    T = "頻道分頁眼睛1125"
    errs = []
    st = {"hidden": [], "puts": []}   # 模擬伺服器：所有 context 共用

    def handler(route):
        req = route.request
        path = _ce_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _ce_json.loads(req.post_data or "{}")
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
            out = {"hidden": st["hidden"]}
        elif path == "/v1/articles/tabs/put":
            if email != "andy@example.com":
                return route.fulfill(status=403, body="{}", headers={"access-control-allow-origin": "*", "content-type": "application/json"})
            st["hidden"] = list(body.get("hidden") or []); st["puts"].append(list(st["hidden"]))
            out = {"ok": True, "hidden": st["hidden"]}
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_ce_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _ce_json.dumps({"api": _CE_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _ce_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_CE_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_):
        pg.goto("about:blank")   # 同網址只差 fragment 不會重載 JS，記憶體裡的隱藏名單會是舊的；先離開再進來才等於真的重新整理
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=all]')", 20000)
        pg.wait_for_timeout(1500)

    vis = "() => [...document.querySelectorAll('#artCats>button')].filter(b => b.getClientRects().length).map(b => b.dataset.cat)"
    for W in (1440, 390):
        st["hidden"] = []; st["puts"] = []
        c, pg = ctx("andy@example.com", W)
        open_(pg, "#articles")
        pg.wait_for_timeout(800)
        info = pg.evaluate("""() => ['tech','ligu','caffaine','healing','news'].map(k => { const t = document.querySelector('#artCats>button[data-cat='+k+']'), e = t && t.querySelector('.arteye');
            return { k, hid: !!t && t.classList.contains('hid'), eye: e ? e.getClientRects().length : 0, off: !!e && e.classList.contains('off') }; })""")
        ok(f"★ [{T}（{W}）] 站主：四個頻道分頁都有眼睛、預設是關（變淡）", all(x["eye"] > 0 and x["hid"] and x["off"] for x in info if x["k"] != "news"), info)
        ok(f"[{T}（{W}）] 站主：比比快訊的眼睛照舊在", [x for x in info if x["k"] == "news"][0]["eye"] > 0, info)
        # 訪客一開始看不到
        cg, pgg = ctx(None, W); open_(pgg, "#articles")
        ok(f"★ [{T}（{W}）] 訪客（開眼睛前）：沒有頻道分頁", not any(k in pgg.evaluate(vis) for k in _CE_CH), pgg.evaluate(vis))
        # 點科技透明圈的眼睛
        pg.locator("#artCats>button[data-cat=tech]").scroll_into_view_if_needed()
        pg.locator("#artCats>button[data-cat=tech] .arteye").click(); pg.wait_for_timeout(900)
        s2 = pg.evaluate("""() => { const t = document.querySelector('#artCats>button[data-cat=tech]'), e = t.querySelector('.arteye'); return { hid: t.classList.contains('hid'), off: e.classList.contains('off'), on: t.classList.contains('on'), hash: location.hash }; }""")
        ok(f"★ [{T}（{W}）] 站主：點眼睛 → 分頁不再變淡、眼睛打開，而且沒有順便切到那個分頁", (not s2["hid"]) and (not s2["off"]) and not s2["on"] and s2["hash"] == "#articles", s2)
        ok(f"★ [{T}（{W}）] 送去伺服器的清單含 showtech、不含 tech，其他頻道仍隱藏", st["puts"] and "showtech" in st["puts"][-1] and "tech" not in st["puts"][-1], st["puts"])
        # 訪客重新整理 → 看得到
        open_(pgg, "#articles"); pgg.wait_for_timeout(900)
        ok(f"★ [{T}（{W}）] 訪客：科技透明圈分頁出現了，其他三個頻道仍沒有", "tech" in pgg.evaluate(vis) and not any(k in pgg.evaluate(vis) for k in _CE_CH[1:]), pgg.evaluate(vis))
        open_(pgg, "#articles/tech"); pgg.wait_for_timeout(1500)
        ok(f"★ [{T}（{W}）] 訪客：直接打 #articles/tech 不被導回，亮起的是科技透明圈、清單有文章", pgg.evaluate("() => location.hash") == "#articles/tech" and pgg.evaluate("() => (document.querySelector('#artCats>button.on')||{dataset:{}}).dataset.cat") == "tech" and pgg.locator("#artList .artc").count() >= 1, [pgg.evaluate("() => location.hash"), pgg.locator("#artList .artc").count()])
        # 站主重新整理：狀態保留
        open_(pg, "#articles"); pg.wait_for_timeout(900)
        ok(f"[{T}（{W}）] 站主重新整理：科技透明圈眼睛仍是開的、哩股哩股仍是關的", pg.evaluate("() => !document.querySelector('#artCats>button[data-cat=tech] .arteye').classList.contains('off') && document.querySelector('#artCats>button[data-cat=ligu] .arteye').classList.contains('off')"))
        # 再點一次關掉
        pg.locator("#artCats>button[data-cat=tech]").scroll_into_view_if_needed()
        pg.locator("#artCats>button[data-cat=tech] .arteye").click(); pg.wait_for_timeout(900)
        ok(f"★ [{T}（{W}）] 站主：再點一次 → 回到隱藏（變淡），清單不含 showtech", pg.evaluate("() => document.querySelector('#artCats>button[data-cat=tech]').classList.contains('hid')") and "showtech" not in st["puts"][-1], st["puts"][-1])
        open_(pgg, "#articles"); pgg.wait_for_timeout(900)
        ok(f"★ [{T}（{W}）] 訪客：重新整理後科技透明圈又不見", "tech" not in pgg.evaluate(vis), pgg.evaluate(vis))
        ok(f"[{T}（{W}）] 沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        cg.close(); c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("頻道分頁眼睛1125", lambda pg, b, base, code: t_chan_eye_1125(b, base, code))
