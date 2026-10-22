# 驗收段落「PWA可安裝1022」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# ===================================================================== PWA可安裝1022
# 為什麼（2026-10-22，docs/app_store_plan.md）：Google Play 的 TWA 包裝與「加到主畫面」都靠同一份 manifest＋Service Worker。
# 在 360／390／430 三種手機寬度（is_mobile、has_touch）各跑一次，量：
#   ① Chrome 自己的可安裝檢查（CDP Page.getInstallabilityErrors）沒有任何錯誤 ＝ 符合 beforeinstallprompt 的條件
#   ② Page.getAppManifest 解析 manifest 沒有錯誤，名稱是「哩股哩股」、display standalone、有 192/512 與 maskable 圖示
#   ③ Service Worker 真的註冊並接手（navigator.serviceWorker.controller）
#   ④ 快取裡沒有任何 data/ 或 .json（「寧可不快取也不准看到昨天的數字」那條）
#   ⑤ /.well-known/assetlinks.json 回 200、是合法 JSON、套件名稱 com.liguligu.app（TWA 驗證用）
#   ⑥ 用手指點一下底部分頁換頁後，SW 仍是接手狀態、沒有頁面例外


def t_pwa_install_1022(b, base, code):
    T = "PWA可安裝1022"
    for w in (360, 390, 430):
        errs: list[str] = []
        c = b.new_context(viewport={"width": w, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#overview", wait_until="load")
        got = wait_until(pg, "() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)", 15000)
        if not got:                                   # 第一次載入時 SW 在 load 後才註冊；clients.claim 後就會接手，再保險重載一次
            pg.reload(wait_until="load")
            got = wait_until(pg, "() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)", 15000)
        ok(f"{T}（{w}）：Service Worker 註冊並接手", got)
        cdp = c.new_cdp_session(pg)
        man = cdp.send("Page.getAppManifest")
        mj = {}
        try:
            import json as _j
            mj = _j.loads(man.get("data") or "{}")
        except Exception:
            pass
        icons = mj.get("icons") or []
        has = lambda size, purpose: any(size in (i.get("sizes") or "") and purpose in (i.get("purpose") or "any") for i in icons)
        ok(f"{T}（{w}）：manifest 解析無錯誤", not man.get("errors"), man.get("errors"))
        ok(f"{T}（{w}）：manifest 名稱／顯示模式／圖示齊全",
           mj.get("name") == "哩股哩股" and mj.get("short_name") == "哩股哩股" and mj.get("display") == "standalone"
           and has("192x192", "any") and has("512x512", "any") and has("192x192", "maskable") and has("512x512", "maskable"),
           {k: mj.get(k) for k in ("name", "short_name", "display", "start_url")})
        # Playwright 的 new_context 一律是無痕模式，Chrome 會固定回 in-incognito（那是測試環境，不是網站的問題）→ 這裡濾掉它，
        # 真正「0 錯誤」由下面 _pwa_persistent_1022 用一般（非無痕）設定檔再量一次。
        real = []
        for _ in range(10):                           # 可安裝檢查要等 SW 的 fetch handler 被 Chrome 看到，最多等 5 秒
            real = [e for e in (cdp.send("Page.getInstallabilityErrors").get("installabilityErrors") or []) if e.get("errorId") != "in-incognito"]
            if not real:
                break
            pg.wait_for_timeout(500)
        ok(f"{T}（{w}）：Chrome 可安裝檢查除無痕模式外沒有錯誤", not real, real)
        # 用手指點底部／頂部分頁換一頁，確認換頁後 SW 仍接手、沒有例外
        tabs = pg.locator('[data-view="flow"]')
        vis = [tabs.nth(i) for i in range(tabs.count()) if tabs.nth(i).is_visible()]
        if vis:
            vis[0].tap(); pg.wait_for_timeout(1200)
        else:                                         # 手機版把分頁收進選單時，退回直接換 hash（只影響「怎麼換頁」，不影響要量的東西）
            pg.evaluate("() => { location.hash = '#flow'; }"); pg.wait_for_timeout(1200)
        ok(f"{T}（{w}）：換頁後網址換到資金流向", "#flow" in pg.evaluate("() => location.hash"))
        ok(f"{T}（{w}）：換頁後 Service Worker 仍接手", pg.evaluate("() => !!navigator.serviceWorker.controller"))
        cached = pg.evaluate("""async () => { const out = []; for (const n of await caches.keys()) {
            const cc = await caches.open(n); for (const r of await cc.keys()) out.push(new URL(r.url).pathname); } return out; }""")
        bad = [p for p in cached if "/data/" in p or p.lower().endswith(".json")]
        ok(f"{T}（{w}）：快取裡沒有任何 data/ 或 .json（共 {len(cached)} 筆）", not bad, bad[:5])
        al = pg.evaluate("""async () => { const r = await fetch('.well-known/assetlinks.json', {cache: 'no-store'});
            let j = null; try { j = await r.json(); } catch (e) {} return { s: r.status, j }; }""")
        pkg = ""
        try:
            pkg = al["j"][0]["target"]["package_name"]
        except Exception:
            pass
        ok(f"{T}（{w}）：/.well-known/assetlinks.json 回 200 且套件名稱正確", al.get("s") == 200 and pkg == "com.liguligu.app", al)
        ok(f"{T}（{w}）：過程沒有頁面例外", not errs, errs[:3])
        c.close()


def _pwa_persistent_1022(b, base):
    """非無痕的一般設定檔（跟真人手機上的 Chrome 一樣）：可安裝檢查必須 0 錯誤，且 beforeinstallprompt 真的觸發。"""
    import tempfile, shutil
    T = "PWA可安裝1022"
    d = tempfile.mkdtemp(prefix="pwa1022-")
    try:
        bt = b.browser_type
        c = bt.launch_persistent_context(d, executable_path="/opt/pw-browsers/chromium", headless=True, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                         device_scale_factor=2)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}"
                          "window.__bip=0;addEventListener('beforeinstallprompt',function(e){window.__bip++;});")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.pages[0] if c.pages else c.new_page()
        pg.goto(base + "#overview", wait_until="load")
        wait_until(pg, "() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)", 15000) or pg.reload(wait_until="load")
        wait_until(pg, "() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)", 15000)
        cdp = c.new_cdp_session(pg)
        errs = []
        for _ in range(10):
            errs = cdp.send("Page.getInstallabilityErrors").get("installabilityErrors") or []
            if not errs:
                break
            pg.wait_for_timeout(500)
        ok(f"{T}（390 一般設定檔）：Chrome 可安裝檢查 0 錯誤", not errs, errs)
        bip = wait_until(pg, "() => window.__bip > 0", 8000)
        if not bip:                                    # 事件只在載入時發一次；重載一次再等
            pg.reload(wait_until="load"); bip = wait_until(pg, "() => window.__bip > 0", 8000)
        ok(f"{T}（390 一般設定檔）：beforeinstallprompt 真的觸發", bip, pg.evaluate("() => window.__bip"))
        c.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _pwa_all_1022(b, base, code):
    t_pwa_install_1022(b, base, code)
    _pwa_persistent_1022(b, base)


register("PWA可安裝1022", lambda pg, b, base, code: _pwa_all_1022(b, base, code))
