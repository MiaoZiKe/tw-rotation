# 驗收段落「手機法人散布1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）：「法人買賣圓點不需要路上超連結，只要可以看就好，另外需要加上十字虛線座標軸，才知道目前看哪個，並且可以放大看」
#   只動手機（html.m4）的市場明細 › 法人連買賣 四象限：點圓點只出提示框不跳頁；十字虛線準星（橫、直兩條虛線＋兩軸數值標籤）吸附最近的點、手指拖動跟著換；
#   橫軸／縱軸兩條拉Bar（dataZoom slider）＋兩指縮放（dataZoom inside）＋「重置」。
#   驗：360／390／430（is_mobile、has_touch、DPR2；全部用 CDP 真的送觸控事件）——
#   ① 手指點第 1 顆點 → 網址沒變、準星標到那一檔（data-cross）、畫面上真的多出 2 條虛線＋2 塊軸標籤、圖上方那一列寫著那一檔的代號與累計張數
#   ② 按住第 1 顆點拖到第 2 顆點附近 → 準星跳到第 2 顆、網址沒變 ③ 拖橫軸拉Bar 右把手往左 → 橫軸可視範圍真的變窄、「重置」亮起
#   ④ 按「重置」→ 回全圖 ⑤ 兩指在圖中央撐開 → 縮放範圍真的變了 ⑥ 提示列＋圖整塊高 ≤ 600（一屏內）、整頁不橫捲。
#   桌機 1440：沒有提示列、沒有 dataZoom，點圓點照舊進個股頁。
def t_m4_scatter_1016(b, base):
    T = "手機法人散布1016"
    PTS = """() => { const e = document.getElementById('trust'), ch = echarts.getInstanceByDom(e); const d = ch.getOption().series[0].data, r = e.getBoundingClientRect();
        const R = ch.getModel().getComponent('grid', 0).coordinateSystem.getRect();
        return { pts: d.map(x => { const p = ch.convertToPixel({ seriesIndex: 0 }, x.value); return { x: r.left + p[0], y: r.top + p[1], code: x.code, side: x.r.side }; }),
                 grid: { l: r.left + R.x, t: r.top + R.y, w: R.width, h: R.height } }; }"""
    ST = """() => { const e = document.getElementById('trust'), ch = echarts.getInstanceByDom(e), o = ch.getOption();
        const ds = ch.getZr().storage.getDisplayList();
        const tipEl = document.getElementById('trustM4Info');
        const xa = ch.getModel().getComponent('xAxis', 0).axis.scale.getExtent(), ya = ch.getModel().getComponent('yAxis', 0).axis.scale.getExtent();
        return { cross: e.dataset.cross || '', dash: ds.filter(x => x.type === 'line' && x.style && x.style.lineDash && x.z === 50).length,
                 tags: ds.filter(x => x.type === 'tspan' && x.z === 51).map(x => x.style.text), tip: tipEl ? tipEl.textContent : '', hash: location.hash,
                 dz: (o.dataZoom || []).map(z => [+(z.start || 0).toFixed(1), +(z.end == null ? 100 : z.end).toFixed(1)]), xr: xa, yr: ya,
                 zoomed: document.getElementById('trustWrap').dataset.zoomed }; }"""
    for W in (360, 390, 430):
        tag = f"【{T}】{W}"
        ctx = b.new_context(viewport={"width": W, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        try:
            ctx.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}")
            m = ctx.new_page()
            m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
            m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            cdp = ctx.new_cdp_session(m)

            def touch(frm, to, steps=10, gap=20, hold_end=True):
                mk = lambda pts: [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": mk(frm)})
                for k in range(1, steps + 1):
                    cur = [(a[0] + (c[0] - a[0]) * k / steps, a[1] + (c[1] - a[1]) * k / steps) for a, c in zip(frm, to)]
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": mk(cur)}); m.wait_for_timeout(gap)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); m.wait_for_timeout(400)

            m.goto(base + "#market/streak", wait_until="domcontentloaded")
            wait_until(m, "(() => { const e = document.getElementById('trust'); return !!(e && e.querySelector('canvas') && document.getElementById('trustM4Bar')); })()", 20000)
            m.evaluate("() => { const w = document.getElementById('trustWrap'); window.scrollTo(0, w.getBoundingClientRect().top + scrollY - 70); }"); m.wait_for_timeout(600)
            h0 = m.evaluate("location.hash")
            box = m.evaluate("() => { const b = document.getElementById('trustM4Bar').getBoundingClientRect(), w = document.getElementById('trustWrap').getBoundingClientRect(); return { h: w.bottom - b.top, bot: w.bottom, vh: innerHeight, sw: document.documentElement.scrollWidth, vw: innerWidth, rb: document.getElementById('trustReset').getBoundingClientRect().height }; }")
            ok(f"{tag}：提示列＋圖整塊高 {box['h']:.0f} ≤ 600、捲到卡片時圖底 {box['bot']:.0f} ≤ 視窗 {box['vh']}、整頁不橫捲、重置鈕高 ≥ 36",
               box["h"] <= 600 and box["bot"] <= box["vh"] and box["sw"] <= box["vw"] and box["rb"] >= 36, box)
            P = m.evaluate(PTS); pts = P["pts"]
            if not ok(f"{tag}：四象限有點可以點（{len(pts)} 顆）", len(pts) >= 2, P["grid"]):
                continue
            g = P["grid"]
            inside = [p for p in pts if g["l"] + 6 < p["x"] < g["l"] + g["w"] - 6 and g["t"] + 6 < p["y"] < g["t"] + g["h"] - 6]
            a = inside[0]
            bb = max(inside, key=lambda p: (p["x"] - a["x"]) ** 2 + (p["y"] - a["y"]) ** 2)
            m.touchscreen.tap(a["x"], a["y"]); m.wait_for_timeout(500)
            s = m.evaluate(ST)
            ok(f"{tag}①：點圓點 → 不跳頁（{s['hash']}）、準星標到 {a['code']}、2 條虛線＋2 塊軸標籤 {s['tags']}、圖上方那列寫出這一檔",
               s["hash"] == h0 and s["cross"] == a["code"] and s["dash"] == 2 and len(s["tags"]) == 2 and any("天" in t for t in s["tags"]) and a["code"] in s["tip"] and "累計" in s["tip"], s)
            touch([(a["x"], a["y"])], [(bb["x"] + 1, bb["y"] + 1)], steps=14)
            s = m.evaluate(ST)
            ok(f"{tag}②：手指從 {a['code']} 拖到 {bb['code']} 附近 → 準星吸附到 {bb['code']}、上方那列換成它、仍不跳頁", s["cross"] == bb["code"] and bb["code"] in s["tip"] and s["hash"] == h0 and s["dash"] == 2, s)
            x0 = s["xr"]
            hd = m.evaluate("""() => { const e = document.getElementById('trust'), ch = echarts.getInstanceByDom(e), r = e.getBoundingClientRect();
                const v = ch.getModel().getComponent('dataZoom', 0); const W = r.width, op = v.option; return { y: r.bottom - 6 - 11, x1: r.left + 40, x2: r.left + W - 44 }; }""")
            touch([(hd["x2"], hd["y"])], [(hd["x2"] - (hd["x2"] - hd["x1"]) * 0.45, hd["y"])], steps=12)
            s = m.evaluate(ST)
            ok(f"{tag}③：拖橫軸拉Bar 右把手往左 → 橫軸範圍 {x0} → {s['xr']} 真的變窄、「重置」亮起", (s["xr"][1] - s["xr"][0]) < (x0[1] - x0[0]) * 0.8 and s["zoomed"] == "1", s)
            m.locator("#trustReset").tap(); m.wait_for_timeout(900)   # 鈕若被頂欄蓋住，Playwright 會先把它捲出來（頁面 scroll-behavior:smooth）→ 等捲完
            s = m.evaluate(ST)
            ok(f"{tag}④：按「重置」→ 橫軸回全圖 {s['xr']}、全部 dataZoom 回 0～100", abs((s["xr"][1] - s["xr"][0]) - (x0[1] - x0[0])) < 0.01 and all(z == [0, 100] for z in s["dz"]) and s["zoomed"] == "0", s)
            m.evaluate("() => { const w = document.getElementById('trust'); window.scrollTo({ top: w.getBoundingClientRect().top + scrollY - 70, behavior: 'instant' }); }"); m.wait_for_timeout(700)
            g = m.evaluate(PTS)["grid"]   # 上一步可能捲過頁面：圖捲回視窗內、重新量圖區位置
            cx, cy = g["l"] + g["w"] / 2, g["t"] + g["h"] / 2
            y0 = s["yr"]
            touch([(cx - 20, cy - 20), (cx + 20, cy + 20)], [(cx - 110, cy - 110), (cx + 110, cy + 110)], steps=12, gap=30)
            s = m.evaluate(ST)
            ok(f"{tag}⑤：兩指撐開 → 縮放範圍真的變了（dataZoom {s['dz']}）", any(z != [0, 100] for z in s["dz"]) and s["zoomed"] == "1" and s["hash"] == h0, s)
        finally:
            ctx.close()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    try:
        ctx.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}")
        m = ctx.new_page()
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(base + "#market/streak", wait_until="domcontentloaded")
        wait_until(m, "(() => !!document.querySelector('#streakView button[data-v=\"quad\"]'))()", 20000)
        m.evaluate("() => document.querySelector('#streakView button[data-v=\"quad\"]').click()")
        wait_until(m, "(() => { const e = document.getElementById('trust'); return !!(e && e.querySelector('canvas')); })()", 10000)
        m.wait_for_timeout(800)
        dk = m.evaluate("() => { const ch = echarts.getInstanceByDom(document.getElementById('trust')); return { m4: document.documentElement.classList.contains('m4'), bar: !!document.getElementById('trustM4Bar'), dz: (ch.getOption().dataZoom || []).length }; }")
        ok(f"【{T}】桌機 1440：沒有手機提示列、沒有 dataZoom", not dk["m4"] and not dk["bar"] and dk["dz"] == 0, dk)
        P = m.evaluate(PTS); g = P["grid"]
        p0 = [p for p in P["pts"] if g["l"] + 6 < p["x"] < g["l"] + g["w"] - 6 and g["t"] + 6 < p["y"] < g["t"] + g["h"] - 6][0]
        m.mouse.click(p0["x"], p0["y"]); m.wait_for_timeout(800)
        ok(f"【{T}】桌機 1440：點圓點照舊進個股頁（#stock/{p0['code']}）", m.evaluate("location.hash") == f"#stock/{p0['code']}", m.evaluate("location.hash"))
    finally:
        ctx.close()


# ★ 2026-10-16 Andy（iPhone）：「法人買賣圓點不需要路上超連結…加上十字虛線座標軸…可以放大看」—— 360／390／430 觸控：點不跳頁、準星吸附、拖動換點、拉Bar 縮放、重置、雙指縮放；1440 不變
register("手機法人散布1016", lambda pg, b, base, code: t_m4_scatter_1016(b, base), after="手機ETF成分股1016")
