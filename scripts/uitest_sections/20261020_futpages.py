# 驗收段落「期貨籌碼兩頁1020」（site/futpages.js：#market/fut 期貨籌碼：上半台指期三大法人未平倉、下半微台指散戶多空比，共用期間鈕與日期軸十字線）
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
    FN = "() => { const e = document.getElementById('fpChart-futoi'); const r = document.getElementById('fpChart-retail'); return !!e && !!r && !!window.echarts && !!echarts.getInstanceByDom(e) && !!echarts.getInstanceByDom(r) && document.querySelectorAll('#fpTw-futoi tbody tr').length > 0 && document.querySelectorAll('#fpTw-retail tbody tr').length > 0; }"
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
            ok(f"{tag}：兩區都畫出圖與表", False); c.close(); continue
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        npts = lambda k: pg.evaluate(f"() => echarts.getInstanceByDom(document.getElementById('fpChart-{k}')).getOption().series[0].data.length")
        nrows = lambda k: pg.evaluate(f"() => document.querySelectorAll('#fpTw-{k} tbody tr').length")
        nval = lambda k: pg.evaluate(f"() => echarts.getInstanceByDom(document.getElementById('fpChart-{k}')).getOption().series[0].data.filter(x => x != null && (typeof x !== 'object' || x.value != null)).length")
        ok(f"{tag}：整頁只有一組期間鈕、預設「6月」", pg.locator(".fp-per").count() == 1 and pg.locator(".fp-per button.on").inner_text() == "6月")
        ok(f"{tag}：台指期區圖上筆數＝表格列數", npts("futoi") == nrows("futoi") > 50, [npts("futoi"), nrows("futoi")])
        ok(f"{tag}：兩張圖共用同一條日期軸（筆數相同）", npts("futoi") == npts("retail"), [npts("futoi"), npts("retail")])
        # 期間鈕真的按
        seen = {}
        for lab in ["1月", "3月", "6月", "1年", "3年", "5年", "全部"]:
            btn = pg.locator(".fp-per button", has_text=lab)
            ok(f"{tag}：期間鈕「{lab}」可按（整組不反灰）", not btn.first.is_disabled())
            btn.first.click(); pg.wait_for_timeout(250)
            seen[lab] = npts("futoi")
            ok(f"{tag}：按「{lab}」後兩區的圖、表同步（{seen[lab]} 筆）", npts("futoi") == nrows("futoi") and npts("retail") == npts("futoi") and nval("retail") == nrows("retail"), [npts("futoi"), nrows("futoi"), nval("retail"), nrows("retail")])
        v = list(seen.values())
        ok(f"{tag}：期間越長筆數越多，全部＝{len(fut['dates'])}", v == sorted(v) and len(set(v)) == 7 and v[-1] == len(fut["dates"]), seen)
        ok(f"{tag}：微台區註明「資料自 2024-06 起」", "資料自 2024-06 起" in pg.locator("#fpHint-retail").inner_text(), pg.locator("#fpHint-retail").inner_text())
        pg.locator(".fp-per button", has_text="3月").first.click(); pg.wait_for_timeout(250)
        # 滑過任一張圖：兩區一起亮
        for who in ("futoi", "retail"):
            box = pg.locator(f"#fpChart-{who}").bounding_box()
            pg.locator(f"#fpChart-{who}").scroll_into_view_if_needed(); pg.wait_for_timeout(250)
            box = pg.locator(f"#fpChart-{who}").bounding_box()
            pg.mouse.move(box["x"] + box["width"] * .5, box["y"] + box["height"] * .55); pg.wait_for_timeout(150)
            pg.mouse.move(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
            st = pg.evaluate("() => ({hov: TwFut.state.hov, hl: ['futoi','retail'].map(k => document.querySelectorAll('#fpTw-' + k + ' tr.hl').length), hlD: ['futoi','retail'].map(k => (document.querySelector('#fpTw-' + k + ' tr.hl')||{dataset:{}}).dataset.d), mk: ['futoi','retail'].map(k => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fpChart-' + k)).getOption().series[0].markLine||{}))})")
            ok(f"{tag}：滑過「{who}」圖→兩區表格各恰一列亮且同一天（{st['hov']}）", bool(st["hov"]) and st["hl"] == [1, 1] and st["hlD"] == [st["hov"]] * 2, st)
            ok(f"{tag}：滑過「{who}」圖→兩張圖都出現同一天標示線", all(st["hov"] in m for m in st["mk"]), [m[:80] for m in st["mk"]])
            head_ = pg.evaluate("() => [document.getElementById('fpLatT').textContent, document.querySelector('#fpTop .lab').textContent]")
            ok(f"{tag}：兩個大數字區都換成 {st['hov']}", all(st["hov"] in t for t in head_), head_)
        # 點圖鎖定、再點取消
        pg.locator("#fpChart-retail").scroll_into_view_if_needed(); pg.wait_for_timeout(250)
        box = pg.locator("#fpChart-retail").bounding_box()
        pg.mouse.click(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
        lk = pg.evaluate("() => ({lock: TwFut.state.lock, sel: ['futoi','retail'].map(k => document.querySelectorAll('#fpTw-' + k + ' tr.sel').length)})")
        ok(f"{tag}：點圖鎖定一天，兩區表格各一列 .sel", bool(lk["lock"]) and lk["sel"] == [1, 1], lk)
        if w > 600:
            pg.mouse.click(box["x"] + box["width"] * .6, box["y"] + box["height"] * .55); pg.wait_for_timeout(300)
            ok(f"{tag}：再點同一天取消鎖定", pg.evaluate("() => TwFut.state.lock") is None)
        # 點台指期表格列 → 微台區也鎖同一天
        row = pg.locator("#fpTw-futoi tbody tr").nth(4); d5 = row.get_attribute("data-d")
        row.click(); pg.wait_for_timeout(300)
        mk = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fpChart-retail')).getOption().series[0].markLine||{})")
        ok(f"{tag}：點台指期表格列→微台圖也鎖 {d5}", d5 in mk and pg.locator("#fpTw-retail tr.sel").get_attribute("data-d") == d5, mk[:100])
        # 排序
        for K, ck in (("futoi", "fn"), ("retail", "p")):
            rd = lambda: pg.evaluate("([K, k]) => { const idx = Array.from(document.querySelectorAll('#fpTw-' + K + ' thead th')).findIndex(t => t.dataset.k === k); return Array.from(document.querySelectorAll('#fpTw-' + K + ' tbody tr')).map(tr => parseFloat(tr.children[idx].textContent.replace(/[,%+−]/g, m => m === '−' ? '-' : ''))).filter(x => !isNaN(x)); }", [K, ck])
            pg.locator(f'#fpTw-{K} th[data-k="{ck}"]').click(); pg.wait_for_timeout(200); a = rd()
            ok(f"{tag}：{K} 點欄名→由大到小", a == sorted(a, reverse=True) and len(a) > 5, a[:4])
            pg.locator(f'#fpTw-{K} th[data-k="{ck}"]').click(); pg.wait_for_timeout(200); b2 = rd()
            ok(f"{tag}：{K} 再點→反向", b2 == sorted(b2) and b2[0] != a[0], b2[:3])
            sc = pg.evaluate("(K) => { const e = document.getElementById('fpTw-' + K); e.scrollLeft = 40; e.scrollTop = 60; return {sl: e.scrollLeft, st: e.scrollTop, ch: e.clientHeight, wide: e.scrollWidth > e.clientWidth, cw: e.clientWidth}; }", K)
            ok(f"{tag}：{K} 表格上下左右都可捲且固定高度", (sc["sl"] > 0 or not sc["wide"]) and (sc["sl"] > 0 or K != "futoi") and sc["st"] > 0 and sc["ch"] <= 400 and (w > 640 or sc["ch"] <= 330), sc)
            ok(f"{tag}：{K} 自動解讀有內容、說明卡有資料來源", pg.locator(f"#fpAutoUl-{K} li").count() >= 2 and "資料來源" in pg.locator(f"#fpHow-{K}").inner_html())
        top = pg.locator("#fpTop").inner_text()
        ok(f"{tag}：微台大卡有多空比、較前一交易日 pp", "較前一交易日" in top and "pp" in top and "%" in top, top[:100])
        ok(f"{tag}：標題下小字寫回溯月份", "2024-06" in pg.locator("#fpSub").inner_text())
        ok(f"{tag}：台指期區最新大數字三格", pg.locator("#fpBig3 .v").count() == 3)
        ok(f"{tag}：兩區都掛 data-snap", pg.locator('[data-snap="fut-oi"]').count() >= 1 and pg.locator('[data-snap="retail-ratio"]').count() >= 1)
        if w <= 640:
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
            sw = pg.evaluate("() => document.scrollingElement.scrollWidth - window.innerWidth")
            ok(f"{tag}：手機沒有橫向捲軸", sw <= 1, sw)
            big = pg.locator("#fpLatest").bounding_box(); ch = pg.locator("#fpChart-futoi").bounding_box()
            ok(f"{tag}：第一屏看得到大數字與台指期主圖上緣", big["y"] + big["height"] < 844 and ch["y"] < 760, [big, ch["y"]])
        ok(f"{tag}：整段沒有頁面例外", not errs, errs[:3])
        c.close()
    # 兩份資料都不存在：資料準備中；只缺微台：那一區資料準備中、台指期照常
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
        ok(f"{T}（{label}）：顯示「資料準備中」、{'台指期照常' if miss != 'both' else ''}無頁面例外", got and extra and not errs, errs[:3])
        c.close()


register("期貨籌碼兩頁1020", lambda pg, b, base, code: t_futpages_1020(b, base, code))
