# 驗收段落「頻道作品1120」（site/hub/hub.js、site/hub/works.json、功能鍵 hub.dl／hub.copy）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until() 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# Andy 11-20：「各頻道影片 文案 資訊可以下載，及觀看」。真的操作：
# ① 開 #hub：四個頻道分頁、每頁卡片數＝works.json；切分頁卡片真的換、網址跟著變；
# ② 按「播放」卡片原地展開（有 video、有文案、不離開本頁）、再按收起；③ 訪客：下載鈕「登入後可下載」；
# ④ 註冊會員：下載鈕真的下載、檔名正確；⑤「複製文案」真的寫進剪貼簿（內容＝文案）；⑥「看文章」連到 #article/<id>；
# ⑦ 390：無橫向捲軸、第一屏看得到分頁與第一張卡、四顆鈕都 ≥ 36px 高、字 ≥ 11px。
import json as _hb_json
import os as _hb_os
import re as _hb_re

_HB_API = "https://acct1120hub.example.test"


def t_hub_1120(b, base, code):
    T = "頻道作品1120"
    errs = []
    root = _hb_os.path.dirname(_hb_os.path.abspath(__file__))
    for _ in range(4):
        if _hb_os.path.isdir(_hb_os.path.join(root, "site")): break
        root = _hb_os.path.dirname(root)
    W_ = _hb_json.load(open(_hb_os.path.join(root, "site", "hub", "works.json"), encoding="utf-8"))
    cnt = {c["id"]: c["n"] for c in W_["channels"]}

    def handler(route):
        req = route.request
        path = _hb_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _hb_json.loads(req.post_data or "{}")
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
        route.fulfill(status=200 if out.get("error") != "auth" else 401, body=_hb_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(email, w):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, accept_downloads=True, **({"has_touch": True, "is_mobile": True} if mob else {}))
        try: c.grant_permissions(["clipboard-read", "clipboard-write"])
        except Exception: pass
        init = "window.TW_ACCOUNT_OVERRIDE = " + _hb_json.dumps({"api": _HB_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
        init += ("localStorage.setItem('tw.acct.tok'," + _hb_json.dumps("tok-" + email) + ");" if email else "localStorage.removeItem('tw.acct.tok');") + "}catch(e){}"
        c.add_init_script(init)
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_HB_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_(pg, h="#hub"):
        pg.goto(base + h, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => document.querySelectorAll('#v-hub .hbc').length > 0", 20000)
        pg.wait_for_timeout(800)

    shots = "/tmp/claude-0/-home-user/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad"
    for W in (1440, 390):
        c, pg = ctx(None, W)
        open_(pg)
        tabs = pg.evaluate("() => [...document.querySelectorAll('#v-hub .hubtabs button')].map(b => ({ch: b.dataset.ch, on: b.classList.contains('on'), n: +b.querySelector('b').textContent}))")
        ok(f"★ [{T}（{W}）] 四個頻道分頁、數字＝works.json、預設哩股哩股", [t["ch"] for t in tabs] == ["ligu", "tech", "caffaine", "healing"] and all(t["n"] == cnt[t["ch"]] for t in tabs) and tabs[0]["on"], tabs)
        if W == 1440: pg.screenshot(path=f"{shots}/hub_1440.png")
        else: pg.screenshot(path=f"{shots}/hub_390.png")
        for ch in ("tech", "caffaine", "healing", "ligu"):
            pg.locator(f'#v-hub .hubtabs button[data-ch="{ch}"]').click()
            wait_until(pg, f"() => location.hash === '#hub/{ch}' && document.querySelectorAll('#v-hub .hbc').length === {cnt[ch]}", 8000)
            n = pg.evaluate("() => document.querySelectorAll('#v-hub .hbc').length")
            ok(f"[{T}（{W}）] 切到 {ch}：網址＝#hub/{ch}、卡片 {cnt[ch]} 張（實際 {n}）", n == cnt[ch], n)
        # 版面：沒有橫向捲軸、手機第一屏看得到分頁與第一張卡
        m = pg.evaluate("() => { const t = document.querySelector('#v-hub .hubtabs').getBoundingClientRect(), c = document.querySelector('#v-hub .hbc').getBoundingClientRect(); const bs = [...document.querySelectorAll('#v-hub .hbc:first-child .hbb')].map(x => { const r = x.getBoundingClientRect(); return [Math.round(r.height), parseFloat(getComputedStyle(x).fontSize)]; }); return { sw: document.documentElement.scrollWidth, iw: innerWidth, tabBottom: t.bottom, cardTop: c.top, cardBottom: c.bottom, ih: innerHeight, bs, tabsW: t.width }; }")
        ok(f"★ [{T}（{W}）] 無橫向捲軸", m["sw"] <= m["iw"], m)
        ok(f"[{T}（{W}）] 第一屏看得到分頁與第一張卡的按鈕列", m["cardBottom"] <= m["ih"] + 2, m)
        ok(f"[{T}（{W}）] 按鈕高 ≥ 36、字 ≥ 11", all(h >= 36 and f >= 11 for h, f in m["bs"]), m["bs"])
        # 播放：原地展開
        h0 = pg.evaluate("() => location.hash")
        pg.locator("#v-hub .hbc .hbb.pri").first.click()
        wait_until(pg, "() => !!document.querySelector('#v-hub .hbc.open video')", 5000)
        o = pg.evaluate("() => { const v = document.querySelector('#v-hub .hbc.open video'); const r = v.getBoundingClientRect(); return { src: v.getAttribute('src'), w: Math.round(r.width), pre: document.querySelector('#v-hub .hbc.open .hbcap pre').textContent.length, hash: location.hash, sw: document.documentElement.scrollWidth, iw: innerWidth }; }")
        ok(f"★ [{T}（{W}）] 按播放：原地展開 video＋文案、網址不變、不撐爆", o["src"].endswith(".mp4") and o["pre"] > 20 and o["hash"] == h0 and o["sw"] <= o["iw"] and o["w"] > 100, o)
        pg.locator("#v-hub .hbc.open .hbb.pri").click()
        wait_until(pg, "() => !document.querySelector('#v-hub .hbc.open')", 3000)
        ok(f"[{T}（{W}）] 再按收起：展開區消失", pg.evaluate("() => !document.querySelector('#v-hub .hbx')"))
        # 訪客下載鎖住
        d = pg.evaluate("() => { const a = document.querySelector('#v-hub .hbc a.dl'); return { t: a.textContent.trim(), d: a.getAttribute('download'), lock: a.classList.contains('lock') }; }")
        ok(f"★ [{T}（{W}）] 訪客：下載鈕「登入後可下載」、無 download 屬性", d["lock"] and "登入後" in d["t"] and d["d"] is None, d)
        # 看文章連結
        a = pg.evaluate("() => document.querySelector('#v-hub .hbc .hbb[href^=\"#article/\"]').getAttribute('href')")
        ok(f"[{T}（{W}）] 「看文章」連到 #article/<id>", bool(_hb_re.match(r"^#article/\d{4}-\d\d-\d\d-", a)), a)
        c.close()

        # 註冊會員：下載、複製
        c, pg = ctx("bob@example.com", W)
        open_(pg)
        wait_until(pg, "() => { const a = document.querySelector('#v-hub .hbc a.dl'); return !!a && !a.classList.contains('lock'); }", 8000)
        first = W_["works"][[w["ch"] for w in W_["works"]].index("ligu")]
        with pg.expect_download(timeout=15000) as dli:
            pg.locator("#v-hub .hbc a.dl").first.click()
        got = dli.value
        size = _hb_os.path.getsize(got.path())
        real = _hb_os.path.getsize(_hb_os.path.join(root, "site", first["video"]))
        ok(f"★ [{T}（{W}）] 註冊會員：下載鈕真的下載（檔名 {got.suggested_filename}、大小與站內檔一致）", got.suggested_filename.endswith(".mp4") and size == real and size > 100000, (got.suggested_filename, size, real))
        pg.locator("#v-hub .hbc .hbb.cp").first.click()
        pg.wait_for_timeout(300)
        btn = pg.evaluate("() => document.querySelector('#v-hub .hbc .hbb.cp').textContent")
        clip = ""
        try: clip = pg.evaluate("() => navigator.clipboard.readText()")
        except Exception: clip = None
        ok(f"★ [{T}（{W}）] 按複製文案：鈕變「已複製 ✓」" + ("、剪貼簿內容＝文案" if clip is not None else "（此環境讀不到剪貼簿，只驗鈕回饋）"), "已複製" in btn and (clip is None or clip.strip() == first["caption"].strip()), (btn, (clip or "")[:40]))
        c.close()

    ok(f"[{T}] 每個頻道至少一則作品（四頻道都有內容）", all(v > 0 for v in cnt.values()), cnt)
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("頻道作品1120", lambda pg, b, base, code: t_hub_1120(b, base, code))
