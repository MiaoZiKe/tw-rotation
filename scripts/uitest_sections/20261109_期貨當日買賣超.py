# 驗收段落「期貨當日買賣超1109」（site/futpages.js：台指期三大法人未平倉頁改成跟「三大法人買賣超日報」同款版面）
# Andy 2026-11-09：「這邊需要看到的是當日賣超，並非累計；圖表上也是必須有累計賣超與當日賣超」「期貨那邊改成跟法人這頁一樣方式呈現」
# 真的驗：當日值＝資料交易口數淨額（或舊格式的相鄰兩日累計相減）抽 3 天比對；四張卡大字＝當日、小字＝期間累積＋淨未平倉；
#   左圖直條＋加權指數線、中圖切「累積買賣超｜淨未平倉」真的換資料；右表當日五欄、點「看累計部位」多四欄；
#   與法人頁（#market/inst）卡片／三欄結構同 class、欄寬比例一致；滑過／點一下連動；手機 390 不橫向溢出、字級 ≥11。
# flake8: noqa


def t_fut_daily_1109(b, base, code):
    T = "期貨當日買賣超1109"
    import json as _j, datetime
    ds, d = [], datetime.date(2026, 9, 1)
    while len(ds) < 60:
        if d.weekday() < 5:
            ds.append(d.isoformat())
        d += datetime.timedelta(1)
    n = len(ds)

    def mk(base_net, step, with_day):
        net = [base_net + i * step + (i % 5) * 37 for i in range(n)]
        long_ = [25000 + x // 2 for x in net]
        short = [l - x for l, x in zip(long_, net)]
        o = {"long": long_, "short": short, "net": net}
        if with_day:
            o["day_net"] = [(-100 - i * 7 + (i % 3) * 400) for i in range(n)]   # 與累計刻意不相關：驗畫面用的是交易口數淨額
        return o
    SGN = lambda t: float(t.replace(",", "").replace("+", "").replace("−", "-"))
    FN = "() => !!document.getElementById('fpBars') && !!echarts.getInstanceByDom(document.getElementById('fpBars')) && !!echarts.getInstanceByDom(document.getElementById('fpLines')) && document.querySelectorAll('#fpTbl tbody tr').length > 3"
    for with_day in (True, False):
        fut = {"asof": ds[-1], "source": "測試假資料", "order": "asc", "dates": ds, "taiex": [20000 + i * 10 for i in range(n)],
               "foreign": mk(-30000, -900, with_day), "trust": mk(5000, 300, with_day), "dealer": mk(1000, 20, with_day)}
        for (w, h) in ((1440, 900), (390, 844)):
            errs = []
            c = b.new_context(viewport={"width": w, "height": h})
            c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            c.route("**/data/fut_oi.json*", lambda r, *_a, body=_j.dumps(fut): r.fulfill(status=200, content_type="application/json", body=body))
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "#market/fut", wait_until="domcontentloaded")
            tag = f"{T}（{'交易口數淨額' if with_day else '舊格式相減'}・{w}）"
            if not wait_until(pg, FN, 25000):
                ok(f"{tag}：畫出兩張圖與表", False); c.close(); continue
            agree = pg.get_by_role("button", name="同意並繼續")
            if agree.count() and agree.first.is_visible():
                agree.first.click(); pg.wait_for_timeout(300)
            pg.locator(".fp-per button", has_text="全部").first.click(); pg.wait_for_timeout(400)
            nrow0 = pg.evaluate("() => document.querySelectorAll('#fpTbl tbody tr').length")
            # ---- 四張卡 ----
            tiles = pg.evaluate("() => Array.from(document.querySelectorAll('#fpTiles .itile')).map(t => ({l: t.querySelector('.il').textContent, v: t.querySelector('.iv').textContent, cum: (t.querySelector('.icu') || {}).textContent, oi: (t.querySelector('.fp-oi') || {}).textContent, pct: !!t.querySelector('.ipct .trk i')}))")
            ok(f"{tag}：上方四張卡＝外資／投信／自營商／三大法人合計", [t["l"] for t in tiles] == ["外資", "投信", "自營商", "三大法人合計"], tiles)
            exp0 = (fut["foreign"]["day_net"][-1] if with_day else fut["foreign"]["net"][-1] - fut["foreign"]["net"][-2])
            ok(f"{tag}：外資卡大字＝最新一日當日買賣超 {exp0}（不是累計 {fut['foreign']['net'][-1]}）", tiles and SGN(tiles[0]["v"].replace("口", "")) == exp0, tiles[:1])
            cumexp = sum((fut["foreign"]["day_net"][i] if with_day else (fut["foreign"]["net"][i] - fut["foreign"]["net"][i - 1] if i else 0)) for i in range(n))
            ok(f"{tag}：小字＝期間累積＋淨未平倉（{fut['foreign']['net'][-1]}）＋進度條", tiles and "累積" in tiles[0]["cum"] and "淨未平倉" in tiles[0]["oi"] and SGN(tiles[0]["oi"].split("淨未平倉")[1].replace("口", "")) == fut["foreign"]["net"][-1] and all(t["pct"] for t in tiles), tiles[:1])
            # ---- 圖：左直條＋指數線，中累積線 ----
            ty = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fpBars')).getOption().series.filter(s => s.id !== 'lk').map(s => s.type)")
            ok(f"{tag}：左圖＝3 組當日直條＋加權指數折線", ty.count("bar") == 3 and ty.count("line") == 1, ty)
            ml = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fpLines')).getOption().series.filter(s => s.id !== 'lk').map(s => [s.type, s.data[0], s.data[s.data.length - 1]])")
            ok(f"{tag}：中圖「累積買賣超」3 條折線、起點是第一天當日值（起算 0）", len(ml) == 3 and all(x[0] == "line" for x in ml), ml)
            pg.locator('#fpMidSeg button[data-m="oi"]').click(); pg.wait_for_timeout(300)
            ml2 = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fpLines')).getOption().series.filter(s => s.id !== 'lk').map(s => s.data[s.data.length - 1])")
            ok(f"{tag}：中圖切「淨未平倉」→末點＝累計淨未平倉 {fut['foreign']['net'][-1]}", ml2[0] == fut["foreign"]["net"][-1] and ml2[0] != ml[0][2], [ml2, ml])
            pg.locator('#fpMidSeg button[data-m="cum"]').click(); pg.wait_for_timeout(300)
            # ---- 表：當日五欄；抽 3 天比對 ----
            pg.evaluate("() => { const b = document.getElementById('fpTblAll'); if (b && b.textContent.indexOf('看全部') >= 0) b.click(); }"); pg.wait_for_timeout(200)
            ths = pg.evaluate("() => Array.from(document.querySelectorAll('#fpTbl thead th')).map(t => t.textContent.replace(/[▲▼ ]/g, ''))")
            ok(f"{tag}：右表預設＝日期／外資／投信／自營商／合計（當日買賣超）", ths == ["日期", "外資", "投信", "自營商", "合計"], ths)
            pg.locator("#fpCumBtn").click(); pg.wait_for_timeout(250)
            ths2 = pg.evaluate("() => Array.from(document.querySelectorAll('#fpTbl thead th')).map(t => t.textContent.replace(/[▲▼ ]/g, ''))")
            ok(f"{tag}：點「看累計部位」→每法人多一欄累計（共 9 欄）", len(ths2) == 9 and "外資累計" in ths2 and "合計累計" in ths2, ths2)
            got = pg.evaluate("""() => { const o = {}, ths = Array.from(document.querySelectorAll('#fpTbl thead th')).map(t => t.dataset.k);
                document.querySelectorAll('#fpTbl tbody tr').forEach(tr => { const v = k => tr.children[ths.indexOf(k)].textContent; o[tr.dataset.d] = {fv: v('fv'), fn: v('fn')}; }); return o; }""")
            bad = []
            for i in (10, 30, n - 1):
                if ds[i] not in got:
                    continue   # 手機只列前 6 筆時抽不到舊日期，下面「看全部」再驗
                exp = (fut["foreign"]["day_net"][i] if with_day else fut["foreign"]["net"][i] - fut["foreign"]["net"][i - 1])
                if SGN(got[ds[i]]["fv"]) != exp or SGN(got[ds[i]]["fn"]) != fut["foreign"]["net"][i]:
                    bad.append([ds[i], got[ds[i]], exp])
            ok(f"{tag}：抽日期比對，當日＝{'資料交易口數淨額' if with_day else '今日累計－前一交易日累計'}、累計＝淨未平倉", not bad and ds[-1] in got, bad)
            pg.locator("#fpCumBtn").click(); pg.wait_for_timeout(200)
            # ---- 與法人頁同款結構 ----
            fcls = pg.evaluate("() => ({tiles: !!document.querySelector('#fpFut .card.irc.irtop .itiles .itile .ipct'), tri: Array.from(document.querySelectorAll('#fpFut .irtri > .card.irc')).length, tbl: !!document.querySelector('#fpFut .tw.irtbl'), bar: !!document.querySelector('.mktstreakbar'), cols: getComputedStyle(document.querySelector('#fpFut .irtri')).gridTemplateColumns})")
            pg.goto(base + "#market/inst", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('#instTiles .itile')", 20000)
            icls = pg.evaluate("() => ({tiles: !!document.querySelector('.card.irc.irtop .itiles .itile .ipct'), tri: Array.from(document.querySelectorAll('.irtri > .card.irc')).length, tbl: !!document.querySelector('.tw.irtbl'), bar: !!document.querySelector('.mktstreakbar'), cols: getComputedStyle(document.querySelector('.irtri')).gridTemplateColumns})")
            ok(f"{tag}：期貨頁與法人頁卡片／三欄結構同 class", fcls["tiles"] and icls["tiles"] and fcls["tri"] == icls["tri"] == 3 and fcls["tbl"] and icls["tbl"] and fcls["bar"] and icls["bar"], [fcls, icls])
            ok(f"{tag}：三欄欄寬比例與法人頁一致（{fcls['cols'].count('px')} 欄）", fcls["cols"].count("px") == icls["cols"].count("px") and (w <= 640 or abs(float(fcls["cols"].split("px")[0]) / float(icls["cols"].split("px")[0]) - 1) < 0.08), [fcls["cols"], icls["cols"]])
            pg.goto(base + "#market/fut", wait_until="domcontentloaded")
            if not wait_until(pg, FN, 25000):
                ok(f"{tag}：回到期貨頁", False); c.close(); continue
            # ---- 連動 ----
            pg.locator("#fpBars").scroll_into_view_if_needed(); pg.wait_for_timeout(250)
            box = pg.locator("#fpBars").bounding_box()
            pg.mouse.move(box["x"] + box["width"] * .45, box["y"] + box["height"] * .5); pg.wait_for_timeout(150)
            pg.mouse.move(box["x"] + box["width"] * .55, box["y"] + box["height"] * .5); pg.wait_for_timeout(300)
            st = pg.evaluate("() => ({hov: TwFut.state.hov, hl: document.querySelectorAll('#fpTbl tr.hl').length})")
            ok(f"{tag}：滑過左圖→右表恰一列亮（{st['hov']}）", bool(st["hov"]) and st["hl"] == 1, st)
            pg.mouse.click(box["x"] + box["width"] * .55, box["y"] + box["height"] * .5); pg.wait_for_timeout(300)
            lk = pg.evaluate("() => ({lock: TwFut.state.lock, lk: document.querySelectorAll('#fpTbl tr.lk').length})")
            ok(f"{tag}：點一下鎖定一天、表一列 .lk", bool(lk["lock"]) and lk["lk"] == 1, lk)
            pg.mouse.click(box["x"] + box["width"] * .55, box["y"] + box["height"] * .5); pg.wait_for_timeout(300)
            ok(f"{tag}：再點同一天取消鎖定", pg.evaluate("() => TwFut.state.lock") is None)
            # ---- 「?」寫明口徑 ----
            pg.locator("#fpHowBtn").click(); pg.wait_for_timeout(300)
            pop = pg.evaluate("() => { const p = document.getElementById('howPop'); return p && !p.hidden ? p.innerText : ''; }")
            ok(f"{tag}：「?」寫明當日買賣超（交易口數淨額／未平倉增減）與累計的口徑", "交易口數淨額" in pop and "未平倉增減" in pop and "累計" in pop, pop[:60])
            pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
            if w <= 640:
                pg.evaluate("window.scrollTo(0,0)")
                sw = pg.evaluate("() => document.scrollingElement.scrollWidth - window.innerWidth")
                ok(f"{tag}：手機 390 沒有橫向捲軸", sw <= 1, sw)
                ok(f"{tag}：手機表格預設只列前 6 筆（比照法人頁）", nrow0 == 6, nrow0)
                sizes = pg.evaluate("() => { const bad = []; document.querySelectorAll('#fpFut *').forEach(e => { if (e.children.length === 0 && e.textContent.trim() && getComputedStyle(e).display !== 'none') { const f = parseFloat(getComputedStyle(e).fontSize); if (f < 11) bad.push(e.className + ':' + f); } }); return bad.slice(0, 5); }")
                ok(f"{tag}：手機字級不小於 11px", not sizes, sizes)
            ok(f"{tag}：沒有頁面例外", not errs, errs[:3])
            c.close()


register("期貨當日買賣超1109", lambda pg, b, base, code: t_fut_daily_1109(b, base, code))
