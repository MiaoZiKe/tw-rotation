# 驗收段落「夜盤轉打1105」：正式網域打不進 Deno（CORS 被拒）時，台指期夜盤改經 GitHub Pages 上的轉打頁拿資料
# 由 _uitest.py exec 載入，ok()、wait_until()、ROOT… 直接可用。
# flake8: noqa
#
# 起因（2026-11-05 夜盤，台北 17:40，Andy：「為何夜盤沒有即時功能」）：總覽台指期卡小標仍是「日盤」。
#   探測 run 42005914871（docs/fixtures/taifex_deno_origin_1105_probe.json）：
#     Deno /fut?session=night，Origin＝https://liguligu-puipui.com → 403「origin not allowed」、沒有 ACAO
#     同一支，Origin＝https://miaozike.github.io                   → 200、7 檔報價、ACAO 正確
#     Worker /fut?session=night                                   → 502（期交所擋 Cloudflare 出口，上游 520）
#   線上 Deno 還是 10-02 版：deploy-deno.yml 10-11 兩次都是 AUTH_INVALID_TOKEN（部署金鑰失效），
#   加正式網域進白名單的那一版從來沒部署上去。
#
# 這一段用假的夜盤回應把三種情況真的跑一次：
#   B（重現當晚）：轉打頁關著 → Deno 直連丟例外、Worker 502 → 小標「日盤」，說明講得出兩條路都失敗
#   A（修好之後）：轉打頁開著 → Deno 直連丟例外 → 經轉打頁拿到夜盤 → 小標「夜盤」、畫出夜盤線、Worker 一次都沒打；
#                 下一輪（60 秒）直接走轉打頁，不再白打直連
#   C（轉打頁也壞）：iframe 載不到 → 5 秒內放棄、退回 Worker，頁面不爆

def t_night_bridge_1105(b, base):
    import json as _json
    import os as _os
    import datetime as _dt
    T = "夜盤轉打1105"
    fx = _json.loads((ROOT / "docs/fixtures/taifex_night_probe.json").read_text(encoding="utf-8"))
    S = {r["id"]: r for r in fx["results"]}
    FUT_NIGHT = S["taifex_quotelist_night"]["sample"]
    CHART_NIGHT = S["taifex_chartdata_1m_night"]["sample"]
    _ticks = ((CHART_NIGHT.get("RtData") or {}).get("Ticks") or [])
    assert _ticks, "fixture 裡沒有 Ticks，這一段的前提不成立"
    LAST = int(float(_ticks[-1][4]))
    # fixture 為了不肥只留頭 5 筆尾 2 筆，畫出來幾乎看不到線 —— 這裡把它補成 15:01～22:00 每分鐘一筆的假序列
    # （最後一筆收在 fixture 的 LAST，時間停在 22:00），截圖才看得出「夜盤線真的畫出來了」。
    import copy as _copy
    import math as _math
    CHART_NIGHT = _copy.deepcopy(CHART_NIGHT)
    _p0 = float(_ticks[0][4])
    _dense = []
    _N = 7 * 60
    for _i in range(_N):
        _m = 15 * 60 + 1 + _i
        _c = _p0 + (LAST - _p0) * _i / (_N - 1) + (0 if _i == _N - 1 else 40 * _math.sin(_i / 23.0))
        _c = round(_c)
        _dense.append(["%02d%02d00" % (_m // 60, _m % 60), str(_c - 3), str(_c + 6), str(_c - 8), f"{_c}.00", str(20 + _i % 37)])
    CHART_NIGHT["RtData"]["Ticks"] = _dense
    _ticks = _dense
    _t = str(_ticks[-1][0]).zfill(6)
    _d = str(((CHART_NIGHT.get("RtData") or {}).get("Quote") or {}).get("CDate") or "20260930")
    _base = _dt.datetime(int(_d[:4]), int(_d[4:6]), int(_d[6:8]), int(_t[:2]), int(_t[2:4]))
    if int(_t[:2]) < 6:
        _base += _dt.timedelta(days=1)
    FIXED = (_base + _dt.timedelta(minutes=2) - _dt.timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    BRIDGE = "https://miaozike.github.io/tw-rotation/taifex_bridge.html"
    GH = "https://miaozike.github.io"
    W502 = _json.dumps({"error": "upstream", "upstream_status": 520, "head": "error code: 520\n"})
    bridge_html = (ROOT / "site/taifex_bridge.html").read_text(encoding="utf-8")

    live_src = (ROOT / "site/live.js").read_text(encoding="utf-8")
    ok(f"[{T}] [前提] live.js 的轉打頁網址是 GitHub Pages 上的 taifex_bridge.html",
       f"const TAIFEX_BRIDGE = '{BRIDGE}';" in live_src)
    ok(f"[{T}] [前提] 轉打頁的白名單有正式網域、目的地寫死是 Deno",
       "'https://liguligu-puipui.com'" in bridge_html and "https://tw-taifex.miaozike.deno.net" in bridge_html)

    PROBE = """() => { const el = document.getElementById('m3c-FUT'), ss = document.getElementById('futSess');
        let last = null, n = 0;
        try { const i = echarts.getInstanceByDom(el);
          if (i) { const d = (i.getOption().series || [])[0];
            if (d) { const v = (d.data || []).filter(x => x != null); n = v.length; last = v.length ? v[v.length - 1] : null; } } } catch (e) {}
        const f = document.getElementById('twFutBridge');
        return { shown: window.Market3.shown, via: window.Market3.futVia, dwhy: window.Market3.futDenoWhy,
          label: ss ? ss.textContent.trim() : '', why: ss ? (ss.dataset.why || '') : '', last, n,
          brg: (window.Live && window.Live.taifexBridge) ? window.Live.taifexBridge() : null,
          iframe: f ? { src: f.src, w: f.offsetWidth, h: f.offsetHeight, vis: getComputedStyle(f).visibility } : null }; }"""

    def lastnum(v):
        if isinstance(v, dict):
            v = v.get("value")
        if isinstance(v, list):
            v = v[-1] if v else None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def open_page(bridge_on, bridge_mode="ok"):
        ctx = b.new_context(viewport={"width": 1500, "height": 1000}, timezone_id="Asia/Taipei")
        if bridge_on:
            ctx.add_init_script("window.TW_TAIFEX_BRIDGE = true;")
        pg = ctx.new_page()
        boom = []
        pg.on("pageerror", lambda e: boom.append(str(e)[:200]))
        pg.clock.install(time=FIXED)
        hits = {"direct": 0, "via_bridge": 0, "worker": 0, "bridge_page": 0}

        def on_deno(route):
            req = route.request
            # request.headers 不一定帶 Origin（Playwright 會濾掉部分標頭），all_headers() 才是瀏覽器真的送出的那份
            try:
                org = (req.all_headers() or {}).get("origin", "")
            except Exception:
                org = (req.headers or {}).get("origin", "")
            try:
                furl = req.frame.url if req.frame else ""
            except Exception:
                furl = ""
            if not org and not furl:
                print("  [夜盤轉打1105] 分不出請求來源：", req.url, flush=True)
            if org == GH or furl.startswith(BRIDGE):
                hits["via_bridge"] += 1
                body = CHART_NIGHT if "/futchart?" in req.url else FUT_NIGHT
                if "session=day" in req.url:
                    body = {"RtCode": "0", "RtData": {"QuoteList": []}}
                route.fulfill(status=200, content_type="application/json; charset=utf-8",
                              headers={"Access-Control-Allow-Origin": GH, "Vary": "Origin"},
                              body=_json.dumps(body))
                return
            # 正式網域直連：真實世界是 403 而且沒有 ACAO → 瀏覽器丟 TypeError。這裡直接讓連線失敗，效果相同。
            hits["direct"] += 1
            route.abort("failed")

        def on_bridge_page(route):
            hits["bridge_page"] += 1
            if bridge_mode == "dead":
                route.abort("failed")
                return
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=bridge_html)

        def on_worker(route):
            hits["worker"] += 1
            route.fulfill(status=502, content_type="application/json; charset=utf-8", body=W502)

        ctx.route("https://tw-taifex.miaozike.deno.net/**", on_deno)
        ctx.route(BRIDGE + "*", on_bridge_page)
        ctx.route("https://fake-worker.test/fut?*", on_worker)
        ctx.route("https://fake-worker.test/futchart?*", on_worker)
        ctx.route("**/futstream?*", lambda r: r.abort("failed"))
        ctx.route("https://fake-worker.test/chart?*", lambda r: r.fulfill(
            status=200, content_type="application/json", body='{"RtCode":"0","RtData":{"QuoteList":[]}}'))
        ctx.route("https://fake-worker.test/quote?*", lambda r: r.fulfill(
            status=200, content_type="application/json", body='{"msgArray":[],"rtcode":"0000"}'))
        ctx.route("**/stream?*", lambda r: r.abort("failed"))
        ctx.route("**/y?*", lambda r: r.abort("failed"))
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.evaluate("""() => { try {
            ['tw.m3.mode','tw.m3.tf','tw.m3.big','tw.m3.fut','tw.m3.nightpts','tw.m3.futsym','tw.sse']
              .forEach(k => localStorage.removeItem(k));
            localStorage.setItem('tw.live.proxy','https://fake-worker.test');
          } catch (e) {} }""")
        pg.goto("about:blank")
        pg.goto(base + "#overview", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        pg.evaluate("() => window.Market3.forceClock('night')")
        wait_until(pg, "() => { const ss = document.getElementById('futSess'); return !!ss && ss.textContent.trim() !== '' && (window.Market3.shown === 'night' || (window.Market3.futDenoWhy || '').length > 0); }", 15000)
        pg.wait_for_timeout(1500)
        return ctx, pg, hits, boom

    # ---------------- B. 重現 11-05 當晚：沒有轉打頁 → 日盤
    ctx, pg, hits, boom = open_page(False)
    r = pg.evaluate(PROBE)
    ok(f"[{T}] B. [前提] 沒開轉打頁時 Live.taifexBridge() 是空字串", r["brg"] == "", r["brg"])
    ok(f"[{T}] B. Deno 直連有試、失敗後退回 Worker", hits["direct"] >= 1 and hits["worker"] >= 1, hits)
    ok(f"[{T}] ★ B. 重現當晚：Deno 被擋＋Worker 502 → 小標「日盤」", r["label"] == "日盤" and r["shown"] != "night", r)
    ok(f"[{T}] B. 小標說明講得出兩條路都失敗", "主要來源連不上" in r["why"] and "備援來源也回 HTTP 502" in r["why"], r["why"])
    ok(f"[{T}] B. 頁面沒爆", not boom, boom)
    ctx.close()

    # ---------------- A. 修好之後：經轉打頁拿到夜盤
    ctx, pg, hits, boom = open_page(True)
    r = pg.evaluate(PROBE)
    ok(f"[{T}] A. [前提] Live.taifexBridge() 回轉打頁網址", r["brg"] == BRIDGE, r["brg"])
    ok(f"[{T}] A. 轉打頁真的被載入、而且真的替我們打了 Deno", hits["bridge_page"] >= 1 and hits["via_bridge"] >= 2, hits)
    lv = lastnum(r["last"])
    ok(f"[{T}] ★ A. 小標變成「夜盤」", r["label"] == "夜盤" and r["shown"] == "night", r)
    ok(f"[{T}] ★ A. 畫出夜盤線（{r['n']} 點，最後一點＝假資料的夜盤收盤 {LAST}）",
       r["n"] >= 2 and lv is not None and abs(lv - LAST) < 0.5, {"n": r["n"], "last": r["last"]})
    ok(f"[{T}] A. Market3.futVia 是 'bridge'、沒有失敗原因、小標不帶失敗說明",
       r["via"] == "bridge" and r["dwhy"] == "" and r["why"] == "", r)
    ok(f"[{T}] A. Worker 一次都沒被打（轉打頁成功就不退）", hits["worker"] == 0, hits)
    ifr = r["iframe"] or {}
    ok(f"[{T}] A. 轉打頁是看不見的 iframe（0×0、hidden），版面不受影響",
       ifr.get("w") == 0 and ifr.get("h") == 0 and ifr.get("vis") == "hidden", ifr)
    shot_dir = _os.environ.get("TW_NIGHT_SHOT_DIR", "")
    if shot_dir:
        try:
            pg.locator("#m3Grid .m3-card[data-id='FUT']").screenshot(path=str(Path(shot_dir) / "night_bridge_fut_card.png"))
            pg.screenshot(path=str(Path(shot_dir) / "night_bridge_overview.png"))
        except Exception as e:
            print("  截圖失敗：", e)
    d0 = hits["direct"]
    v0 = hits["via_bridge"]
    pg.clock.run_for(61 * 1000)
    pg.wait_for_timeout(2500)
    r = pg.evaluate(PROBE)
    ok(f"[{T}] A. 下一輪（60 秒）直接走轉打頁：直連沒有再白打、轉打次數有增加",
       hits["direct"] == d0 and hits["via_bridge"] > v0, {"direct": [d0, hits["direct"]], "bridge": [v0, hits["via_bridge"]]})
    ok(f"[{T}] A. 下一輪之後小標仍是「夜盤」", r["label"] == "夜盤", r["label"])
    ok(f"[{T}] A. 頁面沒爆", not boom, boom)
    ctx.close()

    # ---------------- C. 轉打頁載不到 → 放棄轉打、退回 Worker，頁面不爆
    ctx, pg, hits, boom = open_page(True, "dead")
    pg.wait_for_timeout(5500)
    r = pg.evaluate(PROBE)
    ok(f"[{T}] C. 轉打頁載不到 → 退回 Worker 有被試", hits["worker"] >= 1, hits)
    ok(f"[{T}] C. 小標退回「日盤」、走的是 Worker（轉打頁壞了不會卡住整條路）", r["label"] == "日盤" and r["via"] == "worker", r)
    ok(f"[{T}] C. 轉打頁只試載一次（判定壞掉之後不再每一輪多等 5 秒）", hits["bridge_page"] == 1, hits)
    ok(f"[{T}] C. 頁面沒爆", not boom, boom)
    ctx.close()


register("夜盤轉打1105", lambda pg, b, base, code: t_night_bridge_1105(b, base))
