# 驗收段落「文章影片下載1115」（site/articles.js 的 {t:'mp4'} 區塊、功能鍵 art.video.dl）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-15：「做好的影片都需要放在網站上對應的文章內，並且都具備下載功能」。真的操作：
# ① 1440／390 開示範文章：video 元素在、有 poster、不撐爆（390 無橫向捲軸、影片高 ≤ 80% 視窗）、能讀到 metadata；
# ② 訪客：下載鈕變「登入後可下載」、沒有 download 屬性；③ 註冊會員：下載鈕真的觸發下載、檔名正確、檔案大小對得上；
# ④ 不在白名單的 src（網址、..、副檔名不對、路徑層數不對）一律不畫；⑤ site/media 底下每支 mp4 ≤ 25 MiB（Cloudflare Pages 單檔上限）。
import json as _av_json
import os as _av_os
import re as _av_re

_AV_API = "https://acct1115av.example.test"
_AV_ID = "2026-11-15-healing-marriage-video"
_AV_NAME = "10年，結婚登記少了近3成.mp4"
_AV_SHOT = "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/artvid"


def t_article_mp4_1115(b, base, code):
    T = "文章影片下載1115"
    errs = []

    def handler(route):
        req = route.request
        path = _av_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _av_json.loads(req.post_data or "{}")
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
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_av_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, accept_downloads=True, **({"has_touch": True, "is_mobile": True} if mob else {}))
        init = "window.TW_ACCOUNT_OVERRIDE = " + _av_json.dumps({"api": _AV_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _av_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_AV_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, hash_="#article/" + _AV_ID):
        pg.goto(base + hash_, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#artPost')", 20000)
        pg.wait_for_timeout(1500)

    _av_os.makedirs(_AV_SHOT, exist_ok=True)
    info = "() => { const v = document.querySelector('#artPost .artvid.mp4 video'); if (!v) return null; const r = v.getBoundingClientRect(); return { n: document.querySelectorAll('#artPost .artvid.mp4').length, poster: v.getAttribute('poster') || '', src: v.getAttribute('src') || '', w: Math.round(r.width), h: Math.round(r.height), rs: v.readyState, dur: v.duration || 0, vw: v.videoWidth, ctl: v.controls, sw: document.documentElement.scrollWidth, iw: window.innerWidth, ih: window.innerHeight } }"
    dl = "() => { const a = document.querySelector('#artPost a.avdl'); return a ? { t: a.textContent.trim(), d: a.getAttribute('download'), h: a.getAttribute('href'), lock: a.classList.contains('lock') } : null }"

    for W in (1440, 390):
        # ── 訪客：影片能看、下載鈕鎖住
        c, pg = ctx(None, W)
        open_(pg)
        i = pg.evaluate(info)
        ok(f"★ [{T}（{W}）] 文章內有 video 元素（controls、poster 指向封面、src 正確）", bool(i) and i["n"] == 1 and i["ctl"] and i["poster"].endswith("cover.jpg") and i["src"].endswith("20261115v_marriage/video.mp4"), i)
        wait_until(pg, "() => { const v = document.querySelector('#artPost .artvid.mp4 video'); return !!v && (v.readyState >= 1 || !!v.error); }", 15000)
        i = pg.evaluate(info)
        # Playwright 附的 Chromium 不一定帶 H.264 解碼器：解不了就只驗元素與下載，並如實註明
        can = pg.evaluate("() => document.createElement('video').canPlayType('video/mp4; codecs=\"avc1.42E01E\"')")
        if can:
            ok(f"[{T}（{W}）] 影片真的載入 metadata（duration > 0、有影像寬度）", i["dur"] > 0 and i["vw"] > 0, i)
        else:
            ok(f"[{T}（{W}）] 此瀏覽器無 H.264 解碼器，改驗檔案本身存在且可下載（見下方下載驗收）", True, "canPlayType 空字串")
        ok(f"★ [{T}（{W}）] 不撐爆：無橫向捲軸、影片高度 ≤ 視窗 80%", i["sw"] <= i["iw"] and i["h"] <= i["ih"] * 0.8 + 2, i)
        d = pg.evaluate(dl)
        ok(f"★ [{T}（{W}）] 訪客：下載鈕顯示「登入後可下載」、沒有 download 屬性", bool(d) and d["lock"] and "登入後" in d["t"] and d["d"] is None, d)
        pg.locator("#artPost .artvid.mp4").scroll_into_view_if_needed()
        pg.wait_for_timeout(400)
        pg.locator("#artPost .artvid.mp4").screenshot(path=f"{_AV_SHOT}/guest_{W}.png")
        c.close()

        # ── 註冊會員：下載鈕可用，真的下載
        c, pg = ctx("bob@example.com", W)
        open_(pg)
        wait_until(pg, "() => { const a = document.querySelector('#artPost a.avdl'); return !!a && !a.classList.contains('lock'); }", 8000)
        d = pg.evaluate(dl)
        ok(f"★ [{T}（{W}）] 註冊會員：下載鈕為「下載影片」、download 屬性＝{_AV_NAME}", bool(d) and not d["lock"] and "下載影片" in d["t"] and d["d"] == _AV_NAME, d)
        with pg.expect_download(timeout=15000) as dli:
            pg.locator("#artPost a.avdl").click()
        got = dli.value
        pth = got.path()
        size = _av_os.path.getsize(pth) if pth else 0
        real = _av_os.path.getsize(_av_os.path.join(_av_os.path.dirname(_av_os.path.abspath(__file__)), "..", "..", "site", "media", "healing", "20261115v_marriage", "video.mp4"))
        ok(f"★ [{T}（{W}）] 按下載鈕真的下載：檔名＝{_AV_NAME}、大小與站內檔案一致（{size} B）", got.suggested_filename == _AV_NAME and size == real and size > 100000, (got.suggested_filename, size, real))
        pg.locator("#artPost .artvid.mp4").scroll_into_view_if_needed()
        pg.wait_for_timeout(400)
        pg.locator("#artPost .artvid.mp4").screenshot(path=f"{_AV_SHOT}/member_{W}.png")
        c.close()

        # ── 白名單：不合格的 src 一律不畫
        c, pg = ctx("bob@example.com", W)
        bad = ["https://evil.example.com/x.mp4", "media/../site/x.mp4", "media/healing/a/b.mp4.exe", "media/healing/x.mp4", "/media/healing/a/b.mp4", "media/Healing/a/b.mp4", "javascript:alert(1)//.mp4", "media/healing/a/b/c.mp4"]
        good = {"t": "mp4", "src": "media/healing/20261115v_marriage/video.mp4", "poster": "https://evil.example.com/p.jpg", "title": "好的"}

        def fake(route):
            r = route.fetch()
            j = _av_json.loads(r.text())
            j["blocks"] = [{"t": "mp4", "src": s, "title": "壞" + str(k)} for k, s in enumerate(bad)] + [good]
            route.fulfill(response=r, body=_av_json.dumps(j), headers={**r.headers, "content-type": "application/json"})
        c.route("**/articles/healing/" + _AV_ID + ".json", fake)
        open_(pg)
        i = pg.evaluate("() => ({ n: document.querySelectorAll('#artPost .artvid.mp4').length, srcs: [...document.querySelectorAll('#artPost .artvid.mp4 video')].map(v => v.getAttribute('src')), posters: [...document.querySelectorAll('#artPost .artvid.mp4 video')].map(v => v.getAttribute('poster')), bad: document.querySelectorAll('#artPost video[src*=evil], #artPost video[src*=javascript], #artPost a.avdl[href*=evil]').length })")
        ok(f"★ [{T}（{W}）] 8 個不合格路徑全不渲染，只剩合格那 1 個，且網址型的 poster 被丟掉", i["n"] == 1 and i["bad"] == 0 and i["posters"] == [None], i)
        c.close()

    # ── 檔案大小：Cloudflare Pages 單檔上限 25 MiB（頻道規定 ≤ 20 MiB，這裡用 25 MiB 當硬上限）
    root = _av_os.path.join(_av_os.path.dirname(_av_os.path.abspath(__file__)), "..", "..", "site", "media")
    big = []
    for dp, _dn, fns in _av_os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".mp4") and _av_os.path.getsize(_av_os.path.join(dp, fn)) > 25 * 1024 * 1024:
                big.append(_av_os.path.join(dp, fn))
    ok(f"★ [{T}] site/media 底下每支 mp4 ≤ 25 MiB", not big, big)
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章影片下載1115", lambda pg, b, base, code: t_article_mp4_1115(b, base, code))
