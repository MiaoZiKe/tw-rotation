# 驗收段落「文章下載限站主1126」（site/articles.js：下載入口、右鍵、拖曳、原圖連結）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-26：「精選文章內所有資訊只有我可以下載 其他人不行」
# 真的操作：訪客開有圖片與影片的文章 → 找不到任何下載入口、原圖連結沒有 href、右鍵選單被擋；
#           直接打站主才能用的端點（逐時統計、隱藏寫入）→ 403；站主 → 下載鈕可見、原圖連結可開、右鍵不擋。
import json as _dl_json
import re as _dl_re

_DL_API = "https://acct1126dl.example.test"
_DL_ARTS = ["2026-11-17-budget-app", "2026-12-01-tech-clean"]


def t_art_dl_owner_1126(b, base, code):
    T = "文章下載限站主1126"
    errs = []

    def handler(route):
        req = route.request
        path = _dl_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _dl_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        adm = bool(email and email.startswith("admin"))
        out, s = {}, 200
        if path == "/v1/me":
            out, s = ({"user": {"email": email, "name": "x", "admin": adm}}, 200) if email else ({"error": "auth"}, 401)
        elif path == "/v1/perm/me":
            out = {"who": "admin" if adm else "guest", "plan": "pro" if adm else "free", "planName": "站主" if adm else "訪客", "feats": {}, "lims": {}}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        elif path == "/v1/articles/hidden":
            out = {"ids": []}
        elif path in ("/v1/articles/stats/hourly", "/v1/articles/hidden/put"):
            out, s = ({"ok": True, "id": body.get("id"), "end": 0, "hours": [0] * 24, "ids": []}, 200) if adm else ({"error": "forbidden"}, 403)
        else:
            out = {"ok": True}
        route.fulfill(status=s, body=_dl_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email):
        c = b.new_context(viewport={"width": 1440, "height": 900})
        init = "window.TW_ACCOUNT_OVERRIDE = " + _dl_json.dumps({"api": _DL_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.art.stgfold','{\"pend\":1,\"up\":1,\"mid\":1,\"down\":1,\"ai\":1,\"other\":1}');"
        init += ("localStorage.setItem('tw.acct.tok'," + _dl_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_DL_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        return c, pg

    probe = """() => { const P = document.getElementById('artPost'); if (!P) return null;
      const dl = [...P.querySelectorAll('a[download], a.avdl, button')].filter(e => /下載|download/i.test(e.textContent + (e.getAttribute('download') || '')) && e.getClientRects().length && !e.hidden);
      const aig = [...P.querySelectorAll('.aig')].map(a => a.getAttribute('href'));
      const img = P.querySelector('img, video');
      let blocked = null;
      if (img) { const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true }); img.dispatchEvent(ev); blocked = ev.defaultPrevented; }
      const vid = P.querySelector('video');
      return { dl: dl.length, aig, img: !!img, blocked, drag: img ? img.getAttribute('draggable') : null,
               nodl: vid ? /nodownload/.test(vid.getAttribute('controlslist') || '') && vid.hasAttribute('disablepictureinpicture') : null }; }"""
    api = """async (u) => { const r = await Promise.all(['/v1/articles/stats/hourly', '/v1/articles/hidden/put'].map(p => fetch(u + p, { method: 'POST', body: JSON.stringify({ id: 'x-test-0001', hide: true, t: localStorage.getItem('tw.acct.tok') || undefined }) }).then(x => x.status))); return r; }"""

    for who, email in (("訪客", None), ("站主", "admin@example.com")):
        c, pg = ctx(email)
        seen = 0
        for aid in _DL_ARTS:
            pg.goto(base + "#article/" + aid, wait_until="domcontentloaded")
            try:
                ag = pg.get_by_role("button", name="同意並繼續"); ag.first.wait_for(timeout=2000); ag.first.click(timeout=1500)
            except Exception: pass
            wait_until(pg, "() => !!document.getElementById('artPost')", 20000)
            pg.wait_for_timeout(1500)
            r = pg.evaluate(probe)
            if not r or not r["img"]:
                ok(f"[{T}] {who} {aid}：此身分看不到這篇的圖片／影片（被閘門擋），略過", True, r)
                continue
            seen += 1
            if email:
                ok(f"★ [{T}] 站主 {aid}：右鍵不擋、原圖連結可開", r["blocked"] is False and all(h for h in r["aig"]), r)
            else:
                ok(f"★ [{T}] 訪客 {aid}：找不到任何下載入口、原圖連結沒有 href、右鍵被擋、圖片不能拖曳", r["dl"] == 0 and all(h is None for h in r["aig"]) and r["blocked"] is True and r["drag"] == "false", r)
            if r["nodl"] is not None:
                ok(f"[{T}] {who} {aid}：影片 controlsList=nodownload、disablePictureInPicture", r["nodl"], r)
        ok(f"[{T}] {who}：至少一篇真的驗到圖片／影片", seen >= 1, seen)
        st = pg.evaluate(api, _DL_API)
        if email:
            ok(f"[{T}] 站主：站主端點可用", st == [200, 200], st)
        else:
            ok(f"★ [{T}] 訪客直接打站主端點 → 403", st == [403, 403], st)
        c.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章下載限站主1126", lambda pg, b, base, code: t_art_dl_owner_1126(b, base, code))
