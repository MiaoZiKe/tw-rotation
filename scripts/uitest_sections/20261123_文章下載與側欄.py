# 驗收段落「文章下載與側欄1123」（site/articles.js：快速瀏覽側欄、mp4 播放器寬度、cover 區塊、下載鈕）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-23：「這邊先隱藏，只有我看得到。影片太大、左右太空、下方圖片拿掉、都不能下載，下載只有我可以用」；
# 11-23 追加：規範套用每個頻道的文章。所以四個頻道各抽一篇有 mp4 的文章驗。
# 真的操作：訪客／站主各開列表頁與文章頁，驗側欄有沒有渲染、卡片格線有沒有吃滿、播放器寬度、封面區塊、下載鈕。
import json as _d3_json
import os as _d3_os
import re as _d3_re

_D3_API = "https://acct1123dl.example.test"
_D3_SHOT = "/tmp/claude-0/-home-user-tw-rotation/a8775f1d-2776-5c25-bf5f-68c5d0869fd6/scratchpad/shots"
_D3_ARTS = ["2026-12-01-tech-clean", "2026-11-29-healing-quit-video", "2026-11-17-ligu-power-bill", "2026-11-18-sketch-game"]


def t_art_dl_1123(b, base, code):
    T = "文章下載與側欄1123"
    errs = []

    def handler(route):
        req = route.request
        path = _d3_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _d3_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        adm = bool(email and email.startswith("admin"))
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": email, "name": email.split("@")[0], "admin": adm}} if email else {"error": "auth"}
        elif path == "/v1/perm/me":
            out = {"who": "admin" if adm else ("member" if email else "guest"), "plan": "pro" if adm else "free", "planName": "站主" if adm else "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_d3_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _d3_json.dumps({"api": _D3_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _d3_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_D3_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_, sel):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('%s')" % sel, 20000)
        pg.wait_for_timeout(1800)

    _d3_os.makedirs(_D3_SHOT, exist_ok=True)
    side = "() => { const s = document.getElementById('artSide'), m = document.querySelector('.artmain'), l = document.getElementById('artList'); return s ? { html: s.innerHTML.length, noside: m.classList.contains('noside'), sw: Math.round(s.getBoundingClientRect().width), lw: Math.round(l.getBoundingClientRect().width), mw: Math.round(m.getBoundingClientRect().width) } : null }"
    vid = "() => { const f = document.querySelector('#artPost .artvid.mp4'); if (!f) return null; const v = f.querySelector('video'), a = f.querySelector('a.avdl'), p = document.querySelector('#artPost').getBoundingClientRect(); return { vw: Math.round(v.getBoundingClientRect().width), vh: Math.round(v.getBoundingClientRect().height), pw: Math.round(p.width), ih: window.innerHeight, nd: (v.getAttribute('controlslist') || ''), ctx: v.getAttribute('oncontextmenu') || '', vdl: v.hasAttribute('download'), cover: document.querySelectorAll('#artPost .acover').length, dlHidden: a ? (a.hidden && getComputedStyle(a).display === 'none') : null, dlRect: a ? Math.round(a.getBoundingClientRect().width) : null, dlHref: a ? a.getAttribute('href') : null, dlAttr: a ? a.getAttribute('download') : null, sw: document.documentElement.scrollWidth, iw: window.innerWidth } }"

    for W in (1440, 390):
        for who, email in (("訪客", None), ("站主", "admin@example.com")):
            c, pg = ctx(email, W)
            open_(pg, "#articles", "#artSide")
            if email:
                wait_until(pg, "() => document.getElementById('artSide').innerHTML.length > 50", 8000)
            s = pg.evaluate(side)
            if not email:
                ok(f"★ [{T}（{W}）] 訪客：快速瀏覽側欄完全不渲染、格線吃滿（noside）", bool(s) and s["html"] == 0 and s["noside"] and (W < 1280 or s["lw"] >= s["mw"] - 2), s)
            else:
                ok(f"★ [{T}（{W}）] 站主：側欄有內容、沒有 noside", bool(s) and s["html"] > 50 and not s["noside"], s)
                if W >= 1280:
                    ok(f"[{T}（{W}）] 站主：寬螢幕側欄實際佔位（寬 > 200）", s["sw"] > 200, s)
            pg.screenshot(path=f"{_D3_SHOT}/list_{who}_{W}.png")
            for aid in _D3_ARTS:
                open_(pg, "#article/" + aid, "#artPost")
                if email:
                    pg.wait_for_timeout(1200)
                v = pg.evaluate(vid)
                if v is None:
                    ok(f"[{T}（{W}）{who}] {aid}：此身分看不到影片（被頻道閘門擋），略過影片斷言", True, "gated")
                    continue
                ok(f"★ [{T}（{W}）{who}] {aid}：沒有封面原圖區塊（.acover=0）", v["cover"] == 0, v)
                ok(f"★ [{T}（{W}）{who}] {aid}：video 有 nodownload、禁右鍵、無 download 屬性", "nodownload" in v["nd"] and "return false" in v["ctx"] and not v["vdl"], v)
                ok(f"★ [{T}（{W}）{who}] {aid}：播放器貼合影片、高度 ≤ 視窗 70%、無橫向捲軸", v["vh"] <= v["ih"] * 0.7 + 2 and v["sw"] <= v["iw"] and (W <= 640 or v["vw"] <= 480), v)
                if email:
                    ok(f"★ [{T}（{W}）站主] {aid}：下載影片鈕可見、有 href 與 download", v["dlHidden"] is False and v["dlRect"] > 0 and bool(v["dlHref"]) and bool(v["dlAttr"]), v)
                else:
                    ok(f"★ [{T}（{W}）訪客] {aid}：沒有任何下載鈕（hidden、無 href／download）", v["dlHidden"] is True and v["dlHref"] is None and v["dlAttr"] is None, v)
                pg.locator("#artPost .artvid.mp4").scroll_into_view_if_needed()
                pg.screenshot(path=f"{_D3_SHOT}/art_{aid[-12:]}_{who}_{W}.png")
            c.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章下載與側欄1123", lambda pg, b, base, code: t_art_dl_1123(b, base, code))
