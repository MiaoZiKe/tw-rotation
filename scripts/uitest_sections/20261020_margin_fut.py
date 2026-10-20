# 驗收段落「大盤融資維持率1020」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 大盤融資維持率1020（site/marketfut.js，#market/credit）
# Andy 10-20 範本「大盤融資維持率 圖3-5」。用假的 market_fut.json（page.route 攔截）真的操作：
# 進頁 → 大數字／四格／兩張圖／明細表／排行都在；切 30/60/120 日圖根數真的變；點欄名排序真的換順序；
# 滑過圖 → 表格那天 .hl（連動）、點圖 → .lk；點「?」說明打開；點說明卡展開；排行連到個股；
# 空資料有「資料累積中」；390 手機無橫向捲軸；回到漲跌家數新卡消失。

def _mf_fake():
    import datetime as _dt
    days, d = [], _dt.date(2026, 4, 1)
    while len(days) < 300:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += _dt.timedelta(days=1)
    rows = [{"d": x, "ratio": 165 + (i % 40) * .6 - i * .05, "margin_lots": 7.5e6 + i * 1000, "margin_chg": (i % 9 - 4) * 1500.0,
             "margin_yi": 2400 + i * 3 - (i % 7) * 5, "cap_yi": 4000.0, "short_lots": 3e5 + i * 50, "short_chg": (i % 5 - 2) * 300.0,
             "taiex": 19000 + i * 25.0} for i, x in enumerate(days)]
    rk = {"d": days[-1], "rows": [{"code": "2330", "name": "台積電", "chg": 8000.0 - i * 500, "g": ["晶圓代工"]} for i in range(8)]
          + [{"code": "2317", "name": "鴻海", "chg": -9000.0 + i * 500, "g": ["AI伺服器"]} for i in range(8)]}
    return {"margin": {"rows": rows, "asof": days[-1], "rank": rk}}


def t_margin_1020(b, base, code):
    T = "大盤融資維持率1020"
    errs = []
    fake = json.dumps(_mf_fake())
    for w in (1440, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/data/market_fut.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=fake))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#market/credit", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            st = pg.evaluate("""() => { const c = document.querySelector('[data-snap=margin]'); const n = (id) => echarts.getInstanceByDom(document.getElementById(id)).getOption().xAxis[0].data.length;
              return { tiles: c.querySelectorAll('.mf-tile').length, rows: c.querySelectorAll('#mfTbl tbody tr').length, n1: n('mfChart'), n2: n('mfChart2'),
                       big: c.querySelector('.mf-bn').textContent, rk: c.querySelectorAll('.mf-rk').length, asof: "",
                       ov: document.documentElement.scrollWidth - innerWidth, ml: echarts.getInstanceByDom(document.getElementById('mfChart')).getOption().series[0].markLine.data[0].yAxis }; }""")
            ok(f"【{T}】{w} 大數字帶 %、4 格、明細 300 列、兩張圖各 126 根（6 月預設）、排行不在「大盤」分頁、130 追繳線", st["big"].endswith("%") and st["tiles"] == 4 and st["rows"] == 300 and st["n1"] == 126 and st["n2"] == 126 and st["rk"] == 0 and st["ml"] == 130, st)
            ok(f"【{T}】{w} 沒有橫向捲軸", st["ov"] <= 1 and True, st)
            ok(f"【{T}】{w} 卡內重複標題已拿掉、說明卡／計算方式框／右側三張收合全不在畫面上", pg.evaluate("() => { const h = document.querySelector('#v-market .mkthead > h3'); return !(h && h.offsetParent) && !document.querySelector('.mf-ex, .mf-how, .mf-aside, .mf-sub'); }"))
            ok(f"【{T}】{w} 分段開關「大盤｜個股排行」預設大盤、期間鈕在頂列", pg.locator("#mfTab button").count() == 2 and "on" in (pg.locator("#mfTab button").first.get_attribute("class") or "") and pg.locator("#mfDays").count() == 1)
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
            lay = pg.evaluate("""() => { const r = (s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top + scrollY, b.width, b.height]; };
              return { top: r('.mf-top'), c1: r('#mfChart'), c2: r('#mfChart2'), tb: r('.mf-tblbox'), ch: r('.mf-charts'), bar: r('.mf-bar'), days: r('#mfDays') }; }""")
            if not mob:
                ok(f"【{T}】{w} 兩圖上下、明細表在右側等高並排", lay["c2"][1] > lay["c1"][1] and lay["tb"][0] > lay["c1"][0] + lay["c1"][2] - 5 and abs(lay["tb"][3] - lay["ch"][3]) < 4 and abs(lay["tb"][1] - lay["ch"][1]) < 4, lay)
                ok(f"【{T}】{w} 桌機第一屏（900 高）看完期間鈕、大數字、兩圖與明細表", lay["tb"][1] + lay["tb"][3] <= 900 and lay["c2"][1] + lay["c2"][3] <= 900 and lay["days"][1] < 200, lay)
                ok(f"【{T}】{w} 頂端大數字與四格 KPI 同一列", abs(pg.evaluate("() => document.querySelector('.mf-big').getBoundingClientRect().top - document.querySelector('.mf-tiles').getBoundingClientRect().top")) < 12)
            else:
                ok(f"【{T}】{w} 手機並排改上下、第一屏有分段開關＋大數字＋圖", lay["c1"][1] > lay["top"][1] and lay["tb"][1] > lay["c2"][1] and lay["c1"][1] < 844 and lay["tb"][2] <= 390, lay)
            pg.click("#mfDays button[data-k='250']"); pg.wait_for_timeout(300)
            n120 = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('mfChart')).getOption().xAxis[0].data.length")
            pg.click("#mfDays button[data-k='21']"); pg.wait_for_timeout(300)
            n30 = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('mfChart2')).getOption().xAxis[0].data.length")
            ok(f"【{T}】{w} 切 1 年／1 月兩張圖的根數真的變", n120 == 250 and n30 == 21, (n120, n30))
            first0 = pg.evaluate("() => document.querySelector('#mfTbl tbody tr td').textContent")
            pg.click("#mfTbl th[data-s='ratio']"); pg.wait_for_timeout(300)
            r1 = pg.evaluate("() => [...document.querySelectorAll('#mfTbl tbody tr td:nth-child(2)')].slice(0, 3).map(t => parseFloat(t.textContent))")
            ok(f"【{T}】{w} 點「維持率」欄排序：由大到小", r1[0] >= r1[1] >= r1[2], r1)
            pg.click("#mfTbl th[data-s='ratio']"); pg.wait_for_timeout(300)
            r2 = pg.evaluate("() => [...document.querySelectorAll('#mfTbl tbody tr td:nth-child(2)')].slice(0, 3).map(t => parseFloat(t.textContent))")
            ok(f"【{T}】{w} 再點一次：由小到大", r2[0] <= r2[1] <= r2[2], r2)
            if not mob:
                box = pg.evaluate("() => { const e = document.getElementById('mfChart'); e.scrollIntoView({block:'center'}); const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
                pg.mouse.move(box[0] + box[2] * 0.5, box[1] + box[3] * 0.5); pg.mouse.move(box[0] + box[2] * 0.52, box[1] + box[3] * 0.5); pg.wait_for_timeout(400)
                hl = pg.evaluate("() => document.querySelectorAll('#mfTbl tr.hl').length")
                ok(f"【{T}】{w} 滑過維持率圖 → 明細表那一天亮起（連動）", hl == 1, hl)
                pg.mouse.click(box[0] + box[2] * 0.52, box[1] + box[3] * 0.5); pg.wait_for_timeout(300)
                lk = pg.evaluate("() => document.querySelectorAll('#mfTbl tr.lk').length")
                pg.mouse.click(box[0] + box[2] * 0.52, box[1] + box[3] * 0.5); pg.wait_for_timeout(300)
                lk2 = pg.evaluate("() => document.querySelectorAll('#mfTbl tr.lk').length")
                ok(f"【{T}】{w} 點圖鎖定那一天、再點取消", lk == 1 and lk2 == 0, (lk, lk2))
            pg.click("#mfTab button[data-k='rank']"); pg.wait_for_timeout(400)
            ok(f"【{T}】{w} 切「個股排行」→ 排行 16 列、圖與明細表換掉、期間鈕收起", pg.evaluate("() => document.querySelectorAll('.mf-rk').length") == 16 and pg.locator("#mfChart").count() == 0 and pg.locator("#mfDays").count() == 0)
            pg.click("#mfGroupDD .ddbtn"); pg.wait_for_timeout(200)
            pg.click("#mfGroupDD .ddlist >> text=晶圓代工"); pg.wait_for_timeout(300)
            nrk = pg.evaluate("() => document.querySelectorAll('.mf-rk').length")
            ok(f"【{T}】{w} 族群篩選清單選「晶圓代工」→ 排行只剩該族群個股（增加 8、減少 0）", nrk == 8, nrk)
            pg.keyboard.press("Escape")
            href = pg.evaluate("() => document.querySelector('.mf-rk').getAttribute('href')")
            ok(f"【{T}】{w} 排行列連到個股頁", href == "#stock/2330", href)
            pg.click("#mfTab button[data-k='mkt']"); pg.wait_for_timeout(400)
            ok(f"【{T}】{w} 切回「大盤」→ 圖與明細表回來", pg.locator("#mfChart").count() == 1 and pg.locator("#mfTbl tbody tr").count() == 300)
            pg.click("[data-snap=margin] .howbtn"); pg.wait_for_timeout(300)
            vis = pg.evaluate("() => { const p = document.getElementById('howPop'); return p && !p.hidden ? p.textContent : ''; }")
            ok(f"【{T}】{w} 「?」說明打開，寫出算式與非法定整戶維持率", "融資股票總市值" in vis and "整戶擔保維持率" in vis and "130% 追繳門檻是什麼意思" in vis and "大盤融資維持率是什麼" in vis, vis[:60])
            pg.keyboard.press("Escape")
            if mob:
                ok(f"【{T}】{w} 手機頁內分頁有「信用交易」", pg.evaluate("() => !!document.querySelector('#mktSeg2 button[data-k=\"credit\"]')"))
            else:
                ok(f"【{T}】{w} 側欄有「信用交易」子項", pg.evaluate("() => [...document.querySelectorAll('a,button,li,div,span')].some(e => e.children.length === 0 && e.textContent.trim() === '信用交易' && !e.closest('#mktSeg2, #mktTitle, #mktBody'))"))
            pg.evaluate("() => { location.hash = '#market/updown'; }"); pg.wait_for_timeout(600)
            ok(f"【{T}】{w} 回漲跌家數：新卡消失、舊內容還在", pg.evaluate("() => !document.querySelector('.mf-card') && !!document.getElementById('mktBody').children.length"))
        finally:
            c.close()
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/data/market_fut.json*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"margin":{"rows":[]}}'))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"empty:{e}"))
    pg.goto(base + "#market/credit", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.querySelector('[data-snap=margin]')", 20000)
    ok(f"【{T}】空資料：顯示「尚無資料」不報錯", "尚無資料" in pg.evaluate("() => document.querySelector('[data-snap=margin]').textContent"))
    c.close()
    ok(f"【{T}】沒有網頁錯誤", not errs, errs[:3])


register("大盤融資維持率1020", lambda pg, b, base, code: t_margin_1020(b, base, code))
