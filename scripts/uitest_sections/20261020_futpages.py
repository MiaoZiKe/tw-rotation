# 驗收段落「期貨籌碼兩頁1020」（site/futpages.js：#market/fut 期貨籌碼：頂列分段開關切換台指期三大法人未平倉／微台指散戶多空比，同一位置顯示數字卡＋自動解讀＋圖＋明細表，期間鈕靠右在頂列）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa
# 資料還沒上正式站 → 這段自己產一份符合合約的假資料（只在測試裡，不寫進 site/data），用 page.route 攔下 data/fut_oi.json、data/retail_ratio.json。
# 真的操作：點每一顆期間鈕（驗圖上筆數與表格列數真的變）、滑過圖（表格那列亮、大數字換日期）、點圖鎖定／再點取消、
#   滑過表格列（圖上標示線出現）、點欄名排序（第一列真的換）、表格橫向捲動、資料不存在時顯示「資料準備中」。


def _fp_fake():
    import datetime, random, json as _j
    rnd = random.Random(11)
    ds, d = [], datetime.date(2021, 10, 1)
    while d <= datetime.date(2026, 10, 19):
        if d.weekday() < 5:
            ds.append(d.isoformat())
        d += datetime.timedelta(1)
    n = len(ds)
    tx, p = [], 15000.0
    for _ in range(n):
        p *= 1 + rnd.gauss(.0005, .01); tx.append(round(p, 2))

    def walk(b, v):
        o, x = [], b
        for _ in range(n):
            x = max(500, x + rnd.gauss(0, v)); o.append(int(x))
        return o
    fo = {}
    for k, (bl, bs) in {"foreign": (30000, 40000), "trust": (8000, 3000), "dealer": (9000, 9000)}.items():
        L, S = walk(bl, 800), walk(bs, 800)
        fo[k] = {"long": L, "short": S, "net": [a - c for a, c in zip(L, S)]}
    fut = {"asof": ds[-1], "source": "測試假資料", "order": "asc", "dates": ds, "taiex": tx, **fo}
    st = ds.index("2024-06-03"); rd = ds[st:]; m = len(rd)
    tot = walk(60000, 2000)[st:]
    rl, rs = [], []
    for i in range(m):
        rl.append(int(tot[i] * rnd.uniform(.38, .52))); rs.append(int(tot[i] * rnd.uniform(.38, .52)))
    ret = {"asof": rd[-1], "source": "測試假資料", "product": "TMF", "order": "asc", "dates": rd, "taiex": tx[st:], "total_oi": tot,
           "retail_long": rl, "retail_short": rs, "retail_net": [a - c for a, c in zip(rl, rs)],
           "ratio_pct": [round((a - c) / t * 100, 2) for a, c, t in zip(rl, rs, tot)],
           "settle_dates": [x for x in rd if datetime.date.fromisoformat(x).weekday() == 2 and 15 <= int(x[8:]) <= 21]}
    return fut, ret


def t_futpages_1020(b, base, code):
    T = "期貨籌碼兩頁1020"
    import json as _j
    fut, ret = _fp_fake()
    FN = "() => { const e = document.getElementById('fpChart-futoi'); return !!e && !!window.echarts && !!echarts.getInstanceByDom(e) && document.querySelectorAll('#fpTw-futoi tbody tr').length > 5; }"
    FNR = "() => { const e = document.getElementById('fpChart-retail'); return !!e && !!echarts.getInstanceByDom(e) && document.querySelectorAll('#fpTw-retail tbody tr').length > 5; }"
    for (w, h) in ((1440, 900), (390, 844)):
        errs: list[str] = []
        c = b.new_context(viewport={"width": w, "height": h})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        for fname, data in (("fut_oi", fut), ("retail_ratio", ret)):
            c.route(f"**/data/{fname}.json*", lambda r, *_a, body=_j.dumps(data): r.fulfill(status=200, content_type="application/json", body=body))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#market/fut", wait_until="domcontentloaded")
        tag = f"{T}（{w}）"
        if not wait_until(pg, FN, 25000):
            ok(f"{tag}：預設台指期畫出圖與表", False); c.close(); continue
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        npts = lambda k: pg.evaluate(f"() => echarts.getInstanceByDom(document.getElementById('fpChart-{k}')).getOption().series[0].data.length")
        nrows = lambda k: pg.evaluate(f"() => document.querySelectorAll('#fpTw-{k} tbody tr').length")
        bb = lambda sel: pg.locator(sel).first.bounding_box()
        # ---- 標題與頂列 ----
        ttl_vis = pg.evaluate("() => { const h = document.querySelector('#v-market .mkthead > h3'); return !!h && h.offsetParent !== null; }")
        ok(f"{tag}：卡內重複標題「市場明細：期貨籌碼 ?」已拿掉", not ttl_vis and "mkt-notitle" in (pg.locator("#v-market > .card").first.get_attribute("class") or ""), ttl_vis)
        prod = pg.locator(".fp-prod button")
        ok(f"{tag}：頂列分段開關兩顆、預設台指期", prod.count() == 2 and "台指期三大法人未平倉" in prod.nth(0).inner_text() and "微台指散戶多空比" in prod.nth(1).inner_text() and "on" in (prod.nth(0).get_attribute("class") or ""))
        bar, per = bb(".fp-bar"), bb(".fp-per")
        ok(f"{tag}：期間鈕在頂列、在圖的上方", per["y"] < bb("#fpChart-futoi")["y"] and per["y"] + per["height"] <= bar["y"] + bar["height"] + 2, [per, bar])
        if w > 640:
            ok(f"{tag}：期間鈕靠右（右緣貼近內容區右緣）", abs((per["x"] + per["width"]) - (bar["x"] + bar["width"])) < 6, [per["x"] + per["width"], bar["x"] + bar["width"]])
        ok(f"{tag}：整頁只有一組期間鈕、預設「6月」", pg.locator(".fp-per").count() == 1 and pg.locator(".fp-per button.on").inner_text() == "6月")
        ok(f"{tag}：說明改成頂列「?」、頁面上沒有說明卡", pg.locator("#fpHowBtn").count() == 1 and pg.locator(".fp-how").count() == 0)
        # ---- 版面位置 ----
        num, aut, ch, tb = bb("#fpLatest"), bb("#fpAuto-futoi"), bb("#fpChart-futoi"), bb(".fp-tblcard")
        cc = bb(".fp-main")
        if w > 900:
            ok(f"{tag}：數字卡與自動解讀同一列並排", abs(num["y"] - aut["y"]) < 3 and num["x"] < aut["x"], [num, aut])
            ok(f"{tag}：圖與明細表左右並排、等高（6:4）", abs(cc["y"] - tb["y"]) < 3 and cc["x"] < tb["x"] and abs(cc["height"] - tb["height"]) < 4 and 1.2 < cc["width"] / tb["width"] < 2.0, [cc, tb])
            ok(f"{tag}：上方一列在圖的上面、沒有右側欄", num["y"] + num["height"] <= cc["y"] + 1 and (tb["x"] + tb["width"]) <= 1440 and not pg.locator(".fp-side").count(), [num, cc])
            ok(f"{tag}：右側沒有大片空白（表格卡右緣＝圖卡右緣區）", abs((tb["x"] + tb["width"]) - (aut["x"] + aut["width"])) < 4, [tb, aut])
        # ---- 期間鈕真的按 ----
        seen = {}
        for lab in ["1月", "3月", "6月", "1年", "3年", "5年", "全部"]:
            btn = pg.locator(".fp-per button", has_text=lab)
            ok(f"{tag}：台指期期間鈕「{lab}」可按", not btn.first.is_disabled())
            btn.first.click(); pg.wait_for_timeout(250)
            seen[lab] = npts("futoi")
            ok(f"{tag}：按「{lab}」後圖、表同步（{seen[lab]} 筆）", npts("futoi") == nrows("futoi"), [npts("futoi"), nrows("futoi")])
        v = list(seen.values())
        ok(f"{tag}：期間越長筆數越多，全部＝{len(fut['dates'])}", v == sorted(v) and len(set(v)) == 7 and v[-1] == len(fut["dates"]), seen)
        pg.locator(".fp-per button", has_text="3月").first.click(); pg.wait_for_timeout(250)
        # ---- 台指期連動 ----
        def hover_check(K, who):
            pg.locator(f"#fpChart-{K}").scroll_into_view_if_needed(); pg.wait_for_timeout(250)
            box = pg.locator(f"#fpChart-{K}").bounding_box()
            pg.mouse.move(box["x"] + box["width"] * .5, box["y"] + box["height"] * .55); pg.wait_for_timeout(150)
            pg.mouse.move(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
            st = pg.evaluate("(K) => ({hov: TwFut.state.hov, hl: document.querySelectorAll('#fpTw-' + K + ' tr.hl').length, hlD: (document.querySelector('#fpTw-' + K + ' tr.hl')||{dataset:{}}).dataset.d, mk: JSON.stringify(echarts.getInstanceByDom(document.getElementById('fpChart-' + K)).getOption().series[0].markLine||{}), head: document.querySelector(K === 'futoi' ? '#fpLatT' : '#fpTop .lab').textContent})", K)
            ok(f"{tag}：{who}滑過圖→表格恰一列亮、同一天（{st['hov']}）", bool(st["hov"]) and st["hl"] == 1 and st["hlD"] == st["hov"], st)
            ok(f"{tag}：{who}滑過圖→圖上標示線＋數字卡換成 {st['hov']}", st["hov"] in st["mk"] and st["hov"] in st["head"], [st["mk"][:80], st["head"]])
        hover_check("futoi", "台指期")
        box = pg.locator("#fpChart-futoi").bounding_box()
        pg.mouse.click(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
        lk = pg.evaluate("() => ({lock: TwFut.state.lock, sel: document.querySelectorAll('#fpTw-futoi tr.sel').length})")
        ok(f"{tag}：點圖鎖定一天，表格一列 .sel", bool(lk["lock"]) and lk["sel"] == 1, lk)
        if w > 640:
            pg.mouse.click(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
            ok(f"{tag}：再點同一天取消鎖定", pg.evaluate("() => TwFut.state.lock") is None)
        row = pg.locator("#fpTw-futoi tbody tr").nth(4); d5 = row.get_attribute("data-d")
        row.click(); pg.wait_for_timeout(300)
        mk = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fpChart-futoi')).getOption().series[0].markLine||{})")
        ok(f"{tag}：點表格列→圖鎖 {d5}、數字卡換日期", d5 in mk and d5 in pg.locator("#fpLatT").inner_text(), mk[:100])
        pg.locator('#fpTw-futoi th[data-k="fn"]').click(); pg.wait_for_timeout(200)
        rd = lambda K, k: pg.evaluate("([K, k]) => { const idx = Array.from(document.querySelectorAll('#fpTw-' + K + ' thead th')).findIndex(t => t.dataset.k === k); return Array.from(document.querySelectorAll('#fpTw-' + K + ' tbody tr')).map(tr => parseFloat(tr.children[idx].textContent.replace(/[,%+]/g, '').replace('−', '-'))); }", [K, k])
        a1 = rd("futoi", "fn")
        ok(f"{tag}：台指期點欄名→由大到小", a1 == sorted(a1, reverse=True) and len(a1) > 5, a1[:4])
        sc = pg.evaluate("() => { const e = document.getElementById('fpTw-futoi'); e.scrollTop = 60; e.scrollLeft = 40; return {st: e.scrollTop, ch: e.clientHeight, sl: e.scrollLeft, wide: e.scrollWidth > e.clientWidth}; }")
        ok(f"{tag}：台指期表格內部可捲、高度固定", sc["st"] > 0 and sc["ch"] <= 420 and (sc["sl"] > 0 or not sc["wide"]), sc)
        ok(f"{tag}：台指期自動解讀有內容、數字卡三格", pg.locator("#fpAutoUl-futoi li").count() >= 2 and pg.locator("#fpBig3 .v").count() == 3)
        # ---- 「?」彈窗（台指期） ----
        pg.locator("#fpHowBtn").click(); pg.wait_for_timeout(300)
        pop = pg.evaluate("() => { const p = document.getElementById('howPop'); return p && !p.hidden ? p.innerText : ''; }")
        ok(f"{tag}：「?」開說明彈窗，內容是台指期（含資料來源）", "淨部位" in pop and "資料來源" in pop and "台指期三大法人未平倉怎麼看" in pop and "散戶多空比是用" not in pop, pop[:80])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
        ok(f"{tag}：Esc 關掉說明彈窗", pg.evaluate("() => { const p = document.getElementById('howPop'); return !p || p.hidden; }"))
        # ---- 切到微台：同一位置、內容全換 ----
        before_top = bb(".fp-main")["y"]
        before_chart_x = bb(".fp-main")["x"]
        pg.locator('.fp-prod button[data-k="retail"]').click()
        okr = wait_until(pg, FNR, 8000)
        ok(f"{tag}：切到「微台指散戶多空比」→畫出微台圖與表", okr)
        if okr:
            ok(f"{tag}：切換後台指期的圖、表、數字卡已拿掉（同一位置不堆疊）", pg.locator("#fpChart-futoi, #fpTw-futoi, #fpLatest").count() == 0 and pg.locator(".fp-prod button.on").inner_text() == "微台指散戶多空比")
            ok(f"{tag}：圖在同一個位置（頂端／左緣不變）", (w <= 640 or abs(bb(".fp-main")["y"] - before_top) < 140) and abs(bb(".fp-main")["x"] - before_chart_x) < 3, [bb(".fp-main"), before_top])
            cols = pg.evaluate("() => Array.from(document.querySelectorAll('#fpTw-retail thead th')).map(t => t.textContent)")
            ok(f"{tag}：明細表欄位換成散戶多單／空單／多空比", "散戶多空比" in cols and "外資 淨部位" not in cols, cols)
            top = pg.locator("#fpTop").inner_text()
            ok(f"{tag}：數字卡換成多空比大數字（較前一交易日 pp）", "較前一交易日" in top and "pp" in top and "%" in top, top[:90])
            ok(f"{tag}：自動解讀換成散戶內容", "散戶" in pg.locator("#fpAutoUl-retail").inner_text(), pg.locator("#fpAutoUl-retail").inner_text()[:60])
            ok(f"{tag}：小字寫微台資料回溯月份", "2024-06" in pg.locator("#fpSub").inner_text())
            ok(f"{tag}：微台只能選資料夠長的期間（5年反灰、全部可按）", pg.locator(".fp-per button", has_text="5年").first.is_disabled() and not pg.locator(".fp-per button", has_text="全部").first.is_disabled())
            nv = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fpChart-retail')).getOption().series[0].data.length")
            ok(f"{tag}：微台圖筆數＝表格列數", nv == nrows("retail") > 5, [nv, nrows("retail")])
            if w > 900:
                cc, tb = bb(".fp-main"), bb(".fp-tblcard")
                ok(f"{tag}：微台圖與表也左右並排、等高", abs(cc["y"] - tb["y"]) < 3 and cc["x"] < tb["x"] and abs(cc["height"] - tb["height"]) < 4, [cc, tb])
            hover_check("retail", "微台")
            pg.locator('#fpTw-retail th[data-k="p"]').click(); pg.wait_for_timeout(200)
            a2 = rd("retail", "p")
            ok(f"{tag}：微台點欄名→由大到小", a2 == sorted(a2, reverse=True) and len(a2) > 5, a2[:4])
            pg.locator("#fpHowBtn").click(); pg.wait_for_timeout(300)
            pop2 = pg.evaluate("() => { const p = document.getElementById('howPop'); return p && !p.hidden ? p.innerText : ''; }")
            ok(f"{tag}：切到微台後「?」說明換成散戶多空比", "什麼是散戶多空比" in pop2 and "微型台指" in pop2 and "淨部位＝多方" not in pop2, pop2[:80])
            pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
            pg.locator(".fp-per button", has_text="6月").first.click(); pg.wait_for_timeout(250)
            ok(f"{tag}：微台按「6月」圖表同步", pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fpChart-retail')).getOption().series[0].data.length") == nrows("retail"))
        # 切回台指期
        pg.locator('.fp-prod button[data-k="futoi"]').click()
        ok(f"{tag}：切回台指期→圖表與數字卡回來、微台元素拿掉", wait_until(pg, FN, 8000) and pg.locator("#fpChart-retail, #fpTop").count() == 0)
        ok(f"{tag}：兩個商品都掛 data-snap（切換後 fut-oi）", pg.locator('[data-snap="fut-oi"]').count() >= 1)
        if w <= 640:
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
            sw = pg.evaluate("() => document.scrollingElement.scrollWidth - window.innerWidth")
            ok(f"{tag}：手機沒有橫向捲軸", sw <= 1, sw)
            sg_, big, chb = bb(".fp-prod"), bb("#fpLatest"), bb("#fpChart-futoi")
            ok(f"{tag}：第一屏看得到分段開關、數字卡與主圖上緣", sg_["y"] + sg_["height"] < 844 and big["y"] + big["height"] < 844 and chb["y"] < 760, [sg_, big, chb["y"]])
            order = pg.evaluate("() => ['#fpLatest','#fpChart-futoi','#fpAuto-futoi','#fpTw-futoi'].map(s => document.querySelector(s).getBoundingClientRect().top + scrollY)")
            ok(f"{tag}：手機上下排順序 數字卡→圖→自動解讀→明細表", order == sorted(order), order)
            sizes = pg.evaluate("() => { const bad = []; document.querySelectorAll('.fp-pane *, .fp-bar *').forEach(e => { if (e.children.length === 0 && e.textContent.trim() && getComputedStyle(e).display !== 'none') { const f = parseFloat(getComputedStyle(e).fontSize); if (f < 11) bad.push(e.className + ':' + f); } }); return bad.slice(0, 5); }")
            ok(f"{tag}：手機字級不小於 11px", not sizes, sizes)
        ok(f"{tag}：整段沒有頁面例外", not errs, errs[:3])
        c.close()
    # 三大法人、信用交易：卡內重複標題列拿掉
    for kind, label in (("inst", "三大法人"), ("credit", "信用交易")):
        errs = []
        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#market/" + kind, wait_until="domcontentloaded")
        got = wait_until(pg, "() => (document.getElementById('mktBody')||{innerHTML:''}).innerHTML.length > 50", 25000)
        vis = pg.evaluate("() => Array.from(document.querySelectorAll('#v-market .mkthead > h3')).some(h => h.offsetParent !== null)")
        pre = pg.evaluate("() => /市場明細：/.test((document.getElementById('v-market')||{}).innerText||'')")
        ok(f"{T}（{label}）：卡內「市場明細：{label}」標題列已拿掉、內容照常", got and not vis and not pre and not errs, [got, vis, pre, errs[:2]])
        c.close()
    # 兩份資料都不存在：資料準備中；只缺微台：台指期照常、切到微台顯示資料準備中
    for miss, label in (("both", "兩份都不存在"), ("retail", "只缺微台")):
        errs = []
        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/data/retail_ratio.json*", lambda r: r.fulfill(status=404, body="no"))
        if miss == "both":
            c.route("**/data/fut_oi.json*", lambda r: r.fulfill(status=404, body="no"))
        else:
            c.route("**/data/fut_oi.json*", lambda r, *_a, body=_j.dumps(fut): r.fulfill(status=200, content_type="application/json", body=body))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#market/fut", wait_until="domcontentloaded")
        got = wait_until(pg, "() => /資料準備中/.test((document.getElementById('mktBody')||{}).textContent||'')", 25000)
        extra = True if miss == "both" else wait_until(pg, "() => !!document.getElementById('fpChart-futoi') && !!echarts.getInstanceByDom(document.getElementById('fpChart-futoi'))", 10000)
        if miss == "retail" and extra:
            pg.locator('.fp-prod button[data-k="retail"]').click(); pg.wait_for_timeout(300)
            got = "資料準備中" in pg.locator("#fpPaneBox").inner_text()
        ok(f"{T}（{label}）：顯示「資料準備中」、{'台指期照常、' if miss != 'both' else ''}無頁面例外", got and extra and not errs, errs[:3])
        c.close()


register("期貨籌碼兩頁1020", lambda pg, b, base, code: t_futpages_1020(b, base, code))
