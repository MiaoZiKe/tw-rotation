# 驗收段落「手機ETF成分股1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）：「ETF 成分股內圓圈需要滿版，且可以看到圖五 只有升級版本因為空間問題，他們資訊重疊，只留下面清單即可」
#   只動手機（html.m4）：甜甜圈＝卡片內寬、拿掉甜甜圈下面的圖例（只留表）、表格自動欄寬不截字、點列＝甜甜圈高亮（不跳頁）、點扇區＝表格那列高亮。
#   驗：360／390／430（is_mobile、has_touch、DPR2；訪客與 Plus 各一輪）用假成分（route 攔截 etf_holdings.json）＋法人假值（六位數，最寬的情況）——
#   ① 甜甜圈寬 ≥ 卡片內寬 95% ② 圖例不見 ③ 每格不截字（scrollWidth ≤ clientWidth）、子元素不超出格子、整頁不橫捲
#   ④ 手指點第 3 列 → 那列 .hi、甜甜圈中心字換成那檔、網址沒變；再點一次 → 取消 ⑤ 手指點第 2 塊扇區 → 第 2 列 .hi、網址沒變。
#   桌機 1440：圖例照舊在、代號照舊在第一行（.cdm 不出現）。
def t_m4_etfhold_1016(b, base):
    import json as _json
    T = "手機ETF成分股1016"
    stocks = _json.loads((SITE / "data" / "stocks.json").read_text(encoding="utf-8"))
    tw = sorted([r for r in stocks if r.get("market") == "TWSE" and not str(r["code"]).startswith("0") and r.get("turnover")], key=lambda r: -r["turnover"])[:30]
    ws = [round(30 / (i + 1) ** 0.9, 2) for i in range(len(tw))]
    k = 97.0 / sum(ws)
    items = [{"code": r["code"], "name": r["name"], "w": round(w * k, 2), "shares": 1000 * (5000 - i * 100)} for i, (r, w) in enumerate(zip(tw, ws))]
    FAKE = _json.dumps({"asof": "2026-10-06", "source": "測試假資料", "etfs": {"00927": {"asof": "2026-10-06", "issuer": "群益", "items": items}}}, ensure_ascii=False)
    codes = {x["code"] for x in items}
    ST = _json.dumps([dict(r, inst=((-1) ** i) * (123456 - i * 1111)) if str(r.get("code")) in codes else r for i, r in enumerate(stocks)], ensure_ascii=False).replace("NaN", "null")
    MEAS = """() => { const c = document.getElementById('etfHoldCard'), pie = document.getElementById('etfHoldPie'), tb = document.getElementById('etfHoldTbl');
        if (!c || !pie || !tb) return null; const cs = getComputedStyle(c), inner = c.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
        const lg = document.getElementById('etfHoldLegend'); const bad = [];
        tb.querySelectorAll('tbody tr[data-i], thead tr').forEach(r => { [...r.children].filter(x => x.getClientRects().length).forEach((x, k) => {
          if (x.scrollWidth > x.clientWidth + 1) bad.push(['截字', r.dataset.code || 'head', k]);
          const b = x.getBoundingClientRect(); [...x.querySelectorAll('*')].filter(y => y.getClientRects().length).forEach(y => { const a = y.getBoundingClientRect();
            if (a.right > b.right + 1 || a.left < b.left - 1) bad.push(['超出', r.dataset.code || 'head', k]); }); }); });
        return { inner, pie: pie.getBoundingClientRect().width, leg: !!lg && lg.getClientRects().length > 0, bad: bad.slice(0, 6), rows: tb.querySelectorAll('tbody tr[data-i]').length,
          inst: [...tb.querySelectorAll('td.iv')].filter(x => /張/.test(x.textContent)).length, sw: document.documentElement.scrollWidth, vw: innerWidth }; }"""
    HI = """() => { const hi = [...document.querySelectorAll('#etfHoldTbl tbody tr.hi')].map(r => r.dataset.code);
        const ch = echarts.getInstanceByDom(document.getElementById('etfHoldPie')); const o = ch.getOption();
        return { hi, center: (o.title && o.title[0] && o.title[0].text) || '', hash: location.hash }; }"""
    for plan in ("guest", "plus"):
        for W in (360, 390, 430):
            tag = f"【{T}】{plan} {W}"
            c, _, _ = _sub_ctx(b, None if plan == "guest" else "member", width=W, plan=plan, touch=True)
            try:
                c.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}")
                m = c.new_page(); m.set_viewport_size({"width": W, "height": 844})
                m.on("pageerror", lambda e, tag=tag: fails.append(f"{tag} pageerror: {e}"))
                m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
                m.route("**/data/etf_holdings.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=FAKE))
                m.route("**/data/stocks.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=ST))
                m.goto(base + "#stock/00927", wait_until="domcontentloaded")
                wait_until(m, "(() => { const b = document.querySelector(\"#mbTabs button[data-t='hold']\"); return !!(b && b.offsetParent); })()", 20000)
                m.tap("#mbTabs button[data-t='hold']")
                wait_until(m, "(() => { const e = document.getElementById('etfHoldPie'); const c = e && window.echarts && echarts.getInstanceByDom(e); return !!(c && c.getOption()); })()", 15000)
                m.wait_for_timeout(800)
                d = m.evaluate(MEAS)
                if not ok(f"{tag}：成分股表與甜甜圈畫出來（html.m4）", bool(d and d["rows"] > 0) and m.evaluate("document.documentElement.classList.contains('m4')"), d):
                    continue
                ok(f"{tag}：甜甜圈寬 {d['pie']:.0f} ≥ 卡片內寬 {d['inner']:.0f} 的 95%（滿版）", d["pie"] >= d["inner"] * 0.95, d)
                ok(f"{tag}：甜甜圈下面的圖例拿掉了（只留表）", not d["leg"], d)
                ok(f"{tag}：表格每一格不截字、內容不超出格子（法人六位數 {d['inst']} 列）", not d["bad"] and d["inst"] >= 10, d["bad"])
                ok(f"{tag}：整頁不橫捲（{d['sw']}／{d['vw']}）", d["sw"] <= d["vw"], d)
                h0 = m.evaluate("location.hash")
                r3 = "#etfHoldTbl tbody tr[data-i='2'] td.px"
                m.locator(r3).scroll_into_view_if_needed(); m.tap(r3); m.wait_for_timeout(300)
                s = m.evaluate(HI); nm3 = m.evaluate("(() => { const r = document.querySelector(\"#etfHoldTbl tbody tr[data-i='2'] .nmt a, #etfHoldTbl tbody tr[data-i='2'] .nmt\"); return r.childNodes[0].textContent.trim(); })()")
                ok(f"{tag}：手指點第 3 列 → 那列高亮、甜甜圈中心字換成「{nm3}」、不跳頁", s["hi"] == [items[2]["code"]] and nm3 in s["center"] and s["hash"] == h0, s)
                m.tap(r3); m.wait_for_timeout(300)
                s = m.evaluate(HI)
                ok(f"{tag}：再點同一列 → 取消高亮、中心字回到「前 N 大合計」", s["hi"] == [] and "合計" in s["center"], s)
                m.locator("#etfHoldPie").scroll_into_view_if_needed(); m.wait_for_timeout(200)
                pt = m.evaluate("""() => { const e = document.getElementById('etfHoldPie'), ch = echarts.getInstanceByDom(e); const L = ch.getModel().getSeriesByIndex(0).getData().getItemLayout(1);
                    const a = (L.startAngle + L.endAngle) / 2, r = (L.r0 + L.r) / 2, bx = e.getBoundingClientRect(); return { x: bx.left + L.cx + r * Math.cos(a), y: bx.top + L.cy + r * Math.sin(a) }; }""")
                m.touchscreen.tap(pt["x"], pt["y"]); m.wait_for_timeout(500)
                s = m.evaluate(HI)
                ok(f"{tag}：手指點第 2 塊扇區 → 表格第 2 列高亮、不跳頁", s["hi"] == [items[1]["code"]] and s["hash"] == h0, s)
            finally:
                c.close()
    # 桌機 1440：圖例照舊、代號照舊在名稱後面（.cdm 不出現）
    c = b.new_context(viewport={"width": 1440, "height": 900})
    try:
        c.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}")
        m = c.new_page()
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.route("**/data/etf_holdings.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=FAKE))
        m.goto(base + "#stock/00927", wait_until="domcontentloaded")
        wait_until(m, "(() => { const b = document.querySelector(\"#stockTabs button[data-t='holdings']\"); return !!(b && b.offsetParent); })()", 20000)
        m.click("#stockTabs button[data-t='holdings']")
        wait_until(m, "(() => document.querySelectorAll('#etfHoldLegend .lg').length > 0)()", 15000)
        dk = m.evaluate("() => ({ m4: document.documentElement.classList.contains('m4'), lg: document.getElementById('etfHoldLegend').getClientRects().length > 0, cdm: document.querySelectorAll('#etfHoldTbl .cdm').length, cd: document.querySelectorAll('#etfHoldTbl td.nm .cd').length, pie: Math.round(document.getElementById('etfHoldPie').getBoundingClientRect().width) })")
        ok(f"【{T}】桌機 1440：圖例照舊在、代號照舊在名稱後面（.cdm {dk['cdm']} 個）、甜甜圈 380", not dk["m4"] and dk["lg"] and dk["cdm"] == 0 and dk["cd"] > 0 and dk["pie"] == 380, dk)
    finally:
        c.close()


# ★ 2026-10-16 Andy（iPhone）：「ETF 成分股內圓圈需要滿版…只留下面清單即可」—— 360／390／430 訪客＋Plus：甜甜圈滿版、圖例拿掉、表不截字不重疊、點列／點扇區互相高亮不跳頁；1440 不變
register("手機ETF成分股1016", lambda pg, b, base, code: t_m4_etfhold_1016(b, base), after="手機圓餅放大1010")
