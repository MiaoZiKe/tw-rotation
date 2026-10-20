# 驗收段落「熱力圖即時1020」—— 2026-10-20 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、count()、text()、fails、SITE… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 熱力圖即時1020（app.js HL、industry.js renderHeat soft、live.js MOUNTS heat、snap.js）
# Andy 10-20：「熱力圖都需要具備即時功能，他也是需要截圖發布的內容」。假時鐘（台北 10:30）＋假 Worker（每個請求報價整體漂移一格），真的操作：
#   ① 四張熱力圖（總覽資金熱力圖／熱門題材、熱力圖頁整個台股／題材）標題旁都有「即時」鈕（aria-pressed=true）、卡片帶 data-snap、
#      剛開時 data-snap-live=pending 且 TwSnapReady=false；輪完一圈後 live、TwSnapReady=true
#   ② ★ 格子的顏色／面積／數字真的跟著報價變（兩輪之間 treemap 資料簽名不同；#indTree 的 DOM 節點沒被換掉＝滾輪縮放不會被 5 秒重置）
#   ③ 點「即時」關掉：簽名退回盤後那一份、data-snap-live=close；再點開：重新輪一圈
#   ④ 盤後時鐘：沒有 pending、TwSnapReady 立刻 true；訪客（非站主）：沒有即時鈕、一律 close
#   ⑤ 手機 390：總覽熱力圖卡有即時鈕、沒有橫向捲軸
#   ⑥ 資金輪盤／資金分流樹／法人連續買賣超 也掛了 data-snap，TwSnapReady 在畫完後為 true
HL_SIG = """(id) => { const el = document.getElementById(id); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return null;
  const out = []; const walk = (a) => (a || []).forEach(d => { if (d.children && d.children.length) walk(d.children);
    else out.push([d.name, Math.round(d.value || 0), (d.itemStyle && d.itemStyle.color) || '']); });
  walk(((i.getOption().series || [])[0] || {}).data); return JSON.stringify(out); }"""
HL_SNAP = "(n) => { const e = document.querySelector('[data-snap=\"' + n + '\"]'); return e ? { live: e.dataset.snapLive || '', ready: window.TwSnapReady ? window.TwSnapReady(n) : null } : null; }"


def t_heat_live_1020(b, base):
    import json as _json
    import time as _time
    import datetime as _dt
    from urllib.parse import urlparse, parse_qs
    T = "熱力圖即時1020"
    S = {"k": 0}
    day = _dt.date.today()
    try:
        _dd = _json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8")).get("data_date") or ""
        day = _dt.date.fromisoformat(_dd[:10]) + _dt.timedelta(days=1)
        while day.weekday() >= 5:
            day += _dt.timedelta(days=1)
    except Exception:  # noqa: BLE001
        day = _dt.date(2026, 10, 19)
    DAY = day.isoformat(); DAY8 = DAY.replace("-", "")
    CLK_INTRA = f"{DAY}T02:30:00Z"      # 台北 10:30
    CLK_AFTER = f"{DAY}T12:30:00Z"      # 台北 20:30

    def hhmmss(sec):
        sec = 10 * 3600 + 30 * 60 + sec
        return "%02d:%02d:%02d" % (sec // 3600, sec // 60 % 60, sec % 60)

    def fake_quote(route):
        ex = (parse_qs(urlparse(route.request.url).query).get("ex_ch") or [""])[0]
        S["k"] += 1; k = S["k"]
        arr = []
        for tok in [t for t in ex.split("|") if t]:
            try:
                c = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            if c == "t00":
                z, y = 20100 + k, 20000
            elif c == "o00":
                z, y = 300 + k / 10, 299
            else:
                h = sum(ord(ch) * (i + 3) for i, ch in enumerate(c))
                y = 100.0
                # 整體漂移：每個請求全部股票一起 +1.2% 的階梯（-4.8%～+4.8% 循環），族群加權之後顏色級距一定會換
                chg = (((h * 7) % 21) - 10) * 0.2 + ((k % 9) - 4) * 1.2
                z = round(y * (1 + chg / 100), 2)
            vol = 1000 + (sum(map(ord, c)) % 50) * 100 + k * 10
            arr.append({"c": c, "n": "測試" + c, "ex": tok[:3], "z": f"{z:.2f}", "y": f"{y:.2f}", "o": f"{y:.2f}",
                        "h": f"{max(z, y) + 1:.2f}", "l": f"{min(z, y) - 1:.2f}", "v": str(vol), "t": hhmmss(5 * k), "d": DAY8,
                        "tlong": str(int(_time.time() * 1000))})
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps({"rtcode": "0000", "rtmessage": "OK", "msgArray": arr}))

    def other(route):
        route.fulfill(status=404, content_type="application/json", body='{"error":"not found"}')

    def open_page(clock, route_hash, vp=None, mobile=False, admin=True):
        kw = {"viewport": vp or {"width": 1440, "height": 1000}, "timezone_id": "Asia/Taipei"}
        if mobile:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script("window.TW_LIVE_OVERRIDE = %s;" % ("true" if admin else "false"))
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.clock.install(time=clock)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("https://fake-worker.test/**", other)
        pg.route("https://fake-worker.test/quote?*", fake_quote)
        pg.goto(base + route_hash, wait_until="domcontentloaded")
        pg.evaluate("""() => { try { localStorage.clear(); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); } catch (e) {} }""")
        pg.goto("about:blank")
        pg.goto(base + route_hash, wait_until="load")
        return ctx, pg

    def card_live(pg, name):
        return wait_until(pg, f"() => {{ const e = document.querySelector('[data-snap=\"{name}\"]'); return !!e && e.dataset.snapLive === 'live'; }}", 90000, 300)

    # ------------------------------------------------------------------ ① 總覽：資金熱力圖＋熱門題材（1440、盤中）
    ctx, pg = open_page(CLK_INTRA, "#overview")
    wait_until(pg, "() => !!document.querySelector('#heat canvas, #heat svg') && !!document.querySelector('#ovTheme canvas, #ovTheme svg')", 20000)
    ok(f"[{T}] 假時鐘在盤中", pg.evaluate("() => window.Live.isIntraday()") is True)
    for nm, card in (("heat-overview", "#ovHeatCard"), ("heat-ovtheme", "#ovThemeCard")):
        wait_until(pg, f"() => !!document.querySelector('{card} .livetg-b')", 8000)
        ok(f"[{T}] {nm}：標題旁有「即時」鈕、預設開著（aria-pressed=true）",
           pg.evaluate(f"() => (document.querySelector('{card} .livetg-b') || {{}}).getAttribute && document.querySelector('{card} .livetg-b').getAttribute('aria-pressed')") == "true"
           and "即時" in text(pg, f"{card} .livetg-b"))
        ok(f"[{T}] {nm}：卡片有 data-snap 標記", count(pg, f'[data-snap="{nm}"]') == 1)
    sig0 = pg.evaluate(HL_SIG, "heat"); sigt0 = pg.evaluate(HL_SIG, "ovTheme")
    s0 = pg.evaluate(HL_SNAP, "heat-overview")
    ok(f"[{T}] 剛打開（還沒輪完一圈）：data-snap-live 是 pending（或已 live），pending 時 TwSnapReady=false",
       bool(s0) and s0["live"] in ("pending", "live") and (s0["live"] != "pending" or s0["ready"] is False), s0)
    ok(f"[{T}] ★ 輪完一圈後 90 秒內 data-snap-live=live 且 TwSnapReady=true（截圖程式可以截了）",
       bool(card_live(pg, "heat-overview")) and pg.evaluate("() => window.TwSnapReady('heat-overview')") is True)
    sig1 = pg.evaluate(HL_SIG, "heat")
    ok(f"[{T}] ★ 總覽資金熱力圖：套上即時後，格子的顏色／面積跟盤後不同", bool(sig0) and bool(sig1) and sig0 != sig1)
    pg.evaluate("() => { const e = document.getElementById('heat'); e.__keep = 1; }")
    sig2 = sig1
    t0 = _time.time()
    while _time.time() - t0 < 40 and sig2 == sig1:
        pg.wait_for_timeout(1000)
        sig2 = pg.evaluate(HL_SIG, "heat")
    ok(f"[{T}] ★ 再過幾輪報價：總覽資金熱力圖的格子又變了（顏色或面積，不是只有第一次）", sig2 != sig1)
    ok(f"[{T}] 重畫沒有換掉圖表容器節點（滾輪縮放狀態不會被 5 秒重置）", pg.evaluate("() => document.getElementById('heat').__keep === 1") is True)
    st = pg.evaluate(HL_SNAP, "heat-ovtheme")
    sigt1 = pg.evaluate(HL_SIG, "ovTheme")
    ok(f"[{T}] ★ 熱門題材：面積／數字跟盤後不同、data-snap-live=live", bool(st) and st["live"] == "live" and sigt1 != sigt0, st)
    # ③ 關掉
    pg.click("#ovHeatCard .livetg-b")
    pg.wait_for_timeout(600)
    ok(f"[{T}] ③ 點「即時」關掉：aria-pressed=false、data-snap-live=close", pg.evaluate("() => document.querySelector('#ovHeatCard .livetg-b').getAttribute('aria-pressed')") == "false"
       and pg.evaluate(HL_SNAP, "heat-overview")["live"] == "close")
    ok(f"[{T}] ③ 關掉後格子退回盤後那一份", pg.evaluate(HL_SIG, "heat") == sig0)
    pg.click("#ovHeatCard .livetg-b")
    ok(f"[{T}] ③ 再點開：重新輪一圈後回到即時（格子又和盤後不同）", bool(card_live(pg, "heat-overview")) and pg.evaluate(HL_SIG, "heat") != sig0)
    ctx.close()

    # ------------------------------------------------------------------ ② 熱力圖頁：整個台股一次看＋題材資金熱力
    ctx, pg = open_page(CLK_INTRA, "#heatmap/industry")
    wait_until(pg, "() => !!document.querySelector('#indTree canvas, #indTree svg')", 20000)
    wait_until(pg, "() => !!document.querySelector('[data-hlcard=ind] .livetg-b')", 8000)
    ok(f"[{T}] heat-industry：卡片有 data-snap、標題旁有即時鈕", count(pg, '[data-snap="heat-industry"]') == 1 and count(pg, "[data-hlcard=ind] .livetg-b") == 1,
       [count(pg, '[data-snap="heat-industry"]'), count(pg, "[data-hlcard=ind] .livetg-b"), count(pg, ".livetg")])
    isig0 = pg.evaluate(HL_SIG, "indTree")
    pg.evaluate("() => { document.getElementById('indTree').__keep = 1; }")
    ok(f"[{T}] ★ 整個台股一次看：輪完一圈後 live 且 TwSnapReady=true", bool(card_live(pg, "heat-industry")) and pg.evaluate("() => window.TwSnapReady('heat-industry')") is True)
    isig1 = pg.evaluate(HL_SIG, "indTree")
    ok(f"[{T}] ★ 整個台股一次看：格子顏色／面積真的變了", bool(isig0) and isig1 != isig0)
    t0 = _time.time(); isig2 = isig1
    while _time.time() - t0 < 40 and isig2 == isig1:
        pg.wait_for_timeout(1000); isig2 = pg.evaluate(HL_SIG, "indTree")
    ok(f"[{T}] 整個台股一次看：之後幾輪還在變；且圖表容器節點沒被換掉（soft 重畫）",
       isig2 != isig1 and pg.evaluate("() => document.getElementById('indTree').__keep === 1") is True)
    ctx.close()
    ctx, pg = open_page(CLK_INTRA, "#heatmap/theme")      # 題材另開一頁（同頁從產業切過來時名單會重輪一圈，等的時間太長）
    wait_until(pg, "() => !!document.querySelector('#themeMap canvas, #themeMap svg')", 20000)
    wait_until(pg, "() => !!document.querySelector('#themeMapCard .livetg-b')", 8000)
    ok(f"[{T}] heat-theme：卡片有 data-snap、標題旁有即時鈕", count(pg, '[data-snap="heat-theme"]') == 1 and count(pg, "#themeMapCard .livetg-b") == 1)
    pg.select_option("#themeColorSel", "chg")
    tsig0 = pg.evaluate(HL_SIG, "themeMap")
    tl = card_live(pg, "heat-theme")
    pg.wait_for_timeout(1500)
    tsig1 = pg.evaluate(HL_SIG, "themeMap")
    ok(f"[{T}] ★ 題材資金熱力：輪完一圈後 live 且 TwSnapReady=true", bool(tl) and pg.evaluate("() => window.TwSnapReady('heat-theme')") is True,
       [pg.evaluate(HL_SNAP, "heat-theme"), pg.evaluate("() => { const H = App.HL.data; return [H.ready, H.asked.size, H.uni && H.uni.length, H.err, Live.reqs, document.getElementById('themeMap').getClientRects().length]; }")])
    ok(f"[{T}] ★ 題材資金熱力：選「平均漲跌」上色時，面積／顏色跟著即時報價變", bool(tsig0) and tsig1 != tsig0, [tsig0 and tsig0[:120], tsig1 and tsig1[:120]])
    t0 = _time.time(); tsig2 = tsig1
    while _time.time() - t0 < 40 and tsig2 == tsig1:
        pg.wait_for_timeout(1000); tsig2 = pg.evaluate(HL_SIG, "themeMap")
    ok(f"[{T}] 題材資金熱力：之後幾輪還在變", tsig2 != tsig1)
    ctx.close()

    # ------------------------------------------------------------------ ④ 盤後時鐘、訪客
    ctx, pg = open_page(CLK_AFTER, "#overview")
    wait_until(pg, "() => !!document.querySelector('#heat canvas, #heat svg')", 20000); pg.wait_for_timeout(1500)
    sa = pg.evaluate(HL_SNAP, "heat-overview")
    ok(f"[{T}] ④ 盤後：沒有 pending（close）且 TwSnapReady 立刻 true（顯示最後收盤）", bool(sa) and sa["live"] == "close" and sa["ready"] is True, sa)
    ctx.close()
    ctx, pg = open_page(CLK_INTRA, "#overview", admin=False)
    wait_until(pg, "() => !!document.querySelector('#heat canvas, #heat svg')", 20000); pg.wait_for_timeout(2500)
    sv = pg.evaluate(HL_SNAP, "heat-overview")
    ok(f"[{T}] ④ 訪客（非站主）：沒有即時鈕、一律 close、TwSnapReady=true", bool(sv) and sv["live"] == "close" and sv["ready"] is True
       and pg.evaluate("() => [...document.querySelectorAll('#ovHeatCard .livetg')].every(e => e.getClientRects().length === 0)") is True, sv)
    ctx.close()

    # ------------------------------------------------------------------ ⑤ 手機 390
    ctx, pg = open_page(CLK_INTRA, "#overview", vp={"width": 390, "height": 844}, mobile=True)
    wait_until(pg, "() => !!document.querySelector('#heat canvas, #heat svg, [data-snap=\"heat-overview\"] canvas')", 20000); pg.wait_for_timeout(1500)
    ok(f"[{T}] ⑤ 手機 390：總覽資金熱力圖卡有 data-snap；頁面沒有橫向捲軸",
       count(pg, '[data-snap="heat-overview"]') == 1 and pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1") is True)
    ctx.close()

    # ------------------------------------------------------------------ ⑥ 其他截圖目標
    ctx, pg = open_page(CLK_AFTER, "#flow/rotation")
    wait_until(pg, "() => !!document.querySelector('#rotClock canvas, #rotClock svg') && !!document.querySelector('#sankey canvas, #sankey svg')", 25000); pg.wait_for_timeout(1500)
    ok(f"[{T}] ⑥ #flow/rotation：資金輪盤（含族群資金排行）rot-wheel 有 data-snap 且 TwSnapReady=true",
       pg.evaluate("() => window.TwSnapReady('rot-wheel')") is True, pg.evaluate("() => window.TwSnapList()"))
    pg.evaluate("() => { location.hash = '#flow/sankey'; }")
    wait_until(pg, "() => window.TwSnapReady('flow-tree')", 20000)
    ok(f"[{T}] ⑥ #flow/sankey：資金分流樹（含右側資金流向排名）flow-tree 有 data-snap 且 TwSnapReady=true",
       pg.evaluate("() => window.TwSnapReady('flow-tree')") is True, pg.evaluate("() => window.TwSnapList()"))
    pg.evaluate("() => { location.hash = '#market/streak'; }")
    wait_until(pg, "() => window.TwSnapReady('market-streak')", 20000)
    ok(f"[{T}] ⑥ #market/streak：法人連續買賣超 market-streak 有 data-snap 且 TwSnapReady=true",
       pg.evaluate("() => window.TwSnapReady('market-streak')") is True, pg.evaluate("() => window.TwSnapList()"))
    ctx.close()


    # ------------------------------------------------------------------ ⑦ 資金輪盤「即時」→ 旁邊族群資金排行同步（Andy 10-20 圖四）
    RANK_SIG = "() => { const el = document.getElementById('rankFlow'); const r = (el && el._rfRows) || []; return JSON.stringify(r.map(g => [g.group_id, +g.share_chg.toFixed(3), +(g.ret || 0).toFixed(2), g.lv == null ? null : +g.lv.toFixed(2)])); }"
    ctx, pg = open_page(CLK_INTRA, "#flow/rotation")
    wait_until(pg, "() => !!document.querySelector('#rankFlow canvas') && !!document.getElementById('rotLiveBtn')", 25000); pg.wait_for_timeout(800)
    rs0 = pg.evaluate(RANK_SIG)
    ok(f"[{T}] ⑦ 盤後狀態：排行不是即時（#rankFlow 沒有 data-live）", pg.evaluate("() => document.getElementById('rankFlow').dataset.live || ''") == "" and bool(rs0))
    pg.click("#rotLiveBtn")
    up = wait_until(pg, "() => { const s = App.rlvState(); return s.on && !s.err && s.at > 0 && Object.keys(s.pts).length > 0; }", 60000, 400)
    ok(f"[{T}] ⑦ 按輪盤「即時」後輪盤有即時座標", bool(up))
    pg.wait_for_timeout(1200)
    rs1 = pg.evaluate(RANK_SIG)
    ok(f"[{T}] ⑦ ★ 旁邊的族群資金排行同步變成即時：#rankFlow data-live=1、數字（佔比變化／期間報酬）跟盤後不同", pg.evaluate("() => document.getElementById('rankFlow').dataset.live") == "1" and rs1 != rs0)
    live_rows = [r for r in _json.loads(rs1) if r[3] is not None]
    pts = pg.evaluate("() => Object.keys(App.rlvState().pts)")
    ok(f"[{T}] ⑦ 排行裡的即時族群都是輪盤有即時座標的那些（兩邊同一份資料），且有 {len(live_rows)} 個", len(live_rows) > 0 and all(r[0] in pts for r in live_rows))
    t0 = _time.time(); rs2 = rs1
    while _time.time() - t0 < 40 and rs2 == rs1:
        pg.wait_for_timeout(1000); rs2 = pg.evaluate(RANK_SIG)
    ok(f"[{T}] ⑦ ★ 報價再變，排行長條的數字又跟著變", rs2 != rs1)
    pg.click("#rotLiveBtn"); pg.wait_for_timeout(800)
    ok(f"[{T}] ⑦ 關掉即時：排行回盤後那一份", pg.evaluate(RANK_SIG) == rs0 and pg.evaluate("() => document.getElementById('rankFlow').dataset.live || ''") == "")
    ok(f"[{T}] ⑦ 圖本體截圖目標 rotation-wheel／rotation-rank 有標記且就緒", pg.evaluate("() => window.TwSnapReady('rotation-wheel') && window.TwSnapReady('rotation-rank')") is True)
    pg.evaluate("() => { location.hash = '#flow/sankey'; }")
    wait_until(pg, "() => window.TwSnapReady('sankey-tree')", 20000)
    ok(f"[{T}] ⑦ 分流樹圖本體 sankey-tree 有標記且就緒", pg.evaluate("() => window.TwSnapReady('sankey-tree')") is True)
    ctx.close()


register("熱力圖即時1020", lambda pg, b, base, code: t_heat_live_1020(b, base), after="單篇公開1020")
