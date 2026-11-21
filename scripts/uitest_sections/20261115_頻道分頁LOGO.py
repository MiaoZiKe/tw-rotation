# 驗收段落「頻道分頁LOGO1115」（site/articles.js 的 PRIV[k].logo、site/articles/<頻道>/logo*.svg|png）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-15：四個隱藏分頁前面的通用晶片圖示，換成各頻道自己的 LOGO。站主身分真的操作：
# ① 四個分頁都是 <img> LOGO、不是通用 svg；② 圖真的載入成功（naturalWidth>0）；③ 淺色／深色主題各只顯示對的那一張；
# ④ 約 15～18px、alt＝頻道名；⑤ 390 寬也一樣；⑥ 點進分頁後文章卡片上的頻道小標籤也是 LOGO。可用 TW_LOGO_SHOTS=<資料夾> 順手截圖。
import json as _lg_json
import os as _lg_os
import re as _lg_re


def t_channel_logo_1115(b, base, code):
    T = "頻道分頁LOGO1115"
    api = "https://acct1117.example.test"
    shots = _lg_os.environ.get("TW_LOGO_SHOTS")

    def handler(route):
        req = route.request
        path = _lg_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": "andy@example.com", "name": "andy", "admin": True}}
        elif path == "/v1/perm/me":
            out = {"who": "admin", "plan": "free", "planName": "站主", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/articles/tabs":
            out = {"hidden": []}
        route.fulfill(status=200, body=_lg_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    errs = []
    for W in (1440, 390):
        for theme in ("light", "dark"):
            mob = W <= 640
            c = b.new_context(device_scale_factor=2, viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _lg_json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','tok-andy@example.com');localStorage.setItem('tw.theme','" + theme + "')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            c.route(api + "/**", handler)
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}:{e}"))
            pg.goto(base + "#articles", wait_until="domcontentloaded")
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            wait_until(pg, "() => !!document.querySelector('#artCats>button[data-cat=healing]')", 20000)
            pg.wait_for_timeout(1500)
            pg.evaluate("() => document.documentElement.setAttribute('data-theme','" + theme + "')")
            pg.wait_for_timeout(300)
            for k, nm in (("tech", "科技透明圈"), ("ligu", "哩股哩股"), ("caffaine", "CaffAIne"), ("healing", "談晴說礙")):
                info = pg.evaluate("""(k) => { const b = document.querySelector('#artCats>button[data-cat=' + k + ']'); if (!b) return null;
                  const imgs = [...b.querySelectorAll('.artlg img')].filter(i => i.getClientRects().length);
                  return { svg: !!b.querySelector('svg.artic'), n: imgs.length, w: imgs[0] ? Math.round(imgs[0].getBoundingClientRect().width) : 0,
                    nat: imgs[0] ? imgs[0].naturalWidth : 0, alt: imgs[0] ? imgs[0].alt : '', cls: imgs[0] ? imgs[0].className : '' }; }""", k)
                ok(f"★ [{T}（{W}／{theme}）] {nm} 分頁換成 LOGO 圖（不是通用圖示）", bool(info) and not info["svg"] and info["n"] == 1, info)
                ok(f"[{T}（{W}／{theme}）] {nm} LOGO 載入成功、約 15～18px、alt＝頻道名、主題對的那張", bool(info) and info["nat"] > 0 and 14 <= info["w"] <= 18 and info["alt"] == nm and info["cls"] == ("lgl" if theme == "light" else "lgd"), info)
            if shots:
                _lg_os.makedirs(shots, exist_ok=True)
                pg.evaluate("() => document.querySelector('#artCats>button[data-cat=healing]').scrollIntoView({inline: 'end', block: 'nearest'})")
                pg.wait_for_timeout(300)
                pg.locator("#artCats").screenshot(path=f"{shots}/tabs_{W}_{theme}.png")
                pg.locator("#artCats>button[data-cat=healing]").click()
                pg.wait_for_timeout(800)
                pg.screenshot(path=f"{shots}/healing_{W}_{theme}.png")
            c.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("頻道分頁LOGO1115", lambda pg, b, base, code: t_channel_logo_1115(b, base, code))
