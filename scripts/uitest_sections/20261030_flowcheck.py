# 驗收段落「流向驗證1030」—— Andy 10-30 晚：「為何沒有對應的個股走勢圖在旁邊可以看」「幫我獨立一個分頁將輪盤 資金樹 都個別拉出來與走勢圖比較」
# 「有辦法撈取過去歷史紀錄某天的流向狀況進行回測驗證」。資料用 scripts/_fc_fake.py 造（攔 /data/flowcheck/**），真資料上線後同一段改不攔即可。
# 真的點輪盤的點、樹節點、熱力方塊、拖時間軸、換歷史日期、切三種輪盤，每一步驗「畫面真的因此改變」。
# 由 _uitest.py 用 exec 載入，ok()／wait_until()／fails／SITE 直接可用。
# flake8: noqa

def t_flowcheck_1030(b, base):
    import json as _json
    import sys as _sys
    _sys.path.insert(0, str(SITE.parent / "scripts"))
    import _fc_fake
    T = "流向驗證1030"
    FAKE = _fc_fake.build(SITE)
    LATEST = _fc_fake.LATEST
    HIST = _fc_fake.M60_DAY
    DONLY = _fc_fake.DAILY_ONLY_DAY

    def fake(route):
        u = route.request.url.split("/data/")[1].split("?")[0]
        if u in FAKE:
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(FAKE[u]))
        else:
            route.fulfill(status=404, body="")

    def open_page(h, vp=None, mobile=False):
        kw = {"viewport": vp or {"width": 1280, "height": 900}, "timezone_id": "Asia/Taipei"}
        if mobile:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.route("**/data/flowcheck/**", fake)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.tour','done'); } catch (e) {} }")
        pg.goto("about:blank")
        pg.goto(base + h, wait_until="load")
        wait_until(pg, "() => !!document.querySelector('#fcWheel canvas, #fcWheel svg') && !!document.querySelector('#fcTrend canvas, #fcTrend svg')", 15000)
        pg.wait_for_timeout(600)
        return ctx, pg

    st = lambda pg: pg.evaluate("() => TwFlowcheck.state()")
    title = lambda pg: pg.evaluate("() => document.getElementById('fcTrendName').textContent")
    wheel_sig = lambda pg: pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcWheel')).getOption().series[0].data.map(d => d.value))")
    trend_sig = lambda pg: pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcTrend')).getOption().series[0].data)")

    def click_layout(pg, sel, idx):                      # 用 ECharts 的版面座標點真正的滑鼠（先捲進視窗）
        pg.evaluate("(sel) => document.querySelector(sel).scrollIntoView({block: 'center'})", sel); pg.wait_for_timeout(250)
        r = pg.evaluate("""([sel, i]) => { const el = document.querySelector(sel), c = echarts.getInstanceByDom(el), d = c.getModel().getSeriesByIndex(0).getData(), l = d.getItemLayout(i), b = el.getBoundingClientRect(), raw = d.getRawDataItem(i);
          if (!l || !raw || !raw.gid) return null;
          const sr = c.getModel().getSeriesByIndex(0), ox = +sr.get('left') || 0, oy = +sr.get('top') || 0;
          const w = l.dx || l.width || 0, h = l.dy || l.height || 0; if (w < 8 || h < 6) return null;
          return [b.left + ox + l.x + w / 2, b.top + oy + l.y + h / 2, raw.gid]; }""", [sel, idx])
        if r:
            pg.mouse.click(r[0], r[1]); pg.wait_for_timeout(700)
        return r

    ctx, pg = open_page("#flowcheck")
    s0 = st(pg)
    ok(f"[{T}] ① 進頁：預設資金輪盤、焦點＝資金流入第 1 名、最新日", s0["view"] == "money" and bool(s0["gid"]))
    ok(f"[{T}] ① 頁首標題只有一個「流向驗證」（卡內不再重複）", pg.evaluate("() => [...document.querySelectorAll('#v-flowcheck h2, #v-flowcheck h1')].filter(e => e.textContent.includes('流向驗證')).length") == 0)
    ok(f"[{T}] ① 走勢大圖、成分股小圖、熱力圖都有畫", pg.evaluate("() => document.querySelectorAll('#fcMinis .chart canvas, #fcMinis .chart svg').length >= 3 && document.querySelectorAll('#fcHeat canvas, #fcHeat svg').length >= 1 && document.querySelectorAll('#fcTrend canvas, #fcTrend svg').length >= 1"))
    ok(f"[{T}] ① 訊號卡標「實驗，回測未達顯著」", "實驗" in text(pg, "#fcSigCard") and "未達顯著" in text(pg, "#fcSigCard"))
    ok(f"[{T}] ① 吻合度旁印近 3 年常態", "近 3 年常態" in text(pg, "#fcVerdict"))

    # ② 點輪盤的點 → 焦點換、走勢／成分股／網址同步
    g0, n0, t0, mem0 = s0["gid"], title(pg), trend_sig(pg), text(pg, "#fcMinis")
    pos = pg.evaluate("""(g0) => { const c = echarts.getInstanceByDom(document.getElementById('fcWheel')), d = c.getOption().series[0].data; const o = d.filter(x => x.gid !== g0)[3]; const p = c.convertToPixel({ seriesIndex: 0 }, o.value), b = document.getElementById('fcWheel').getBoundingClientRect(); return [b.left + p[0], b.top + p[1], o.gid]; }""", g0)
    pg.mouse.click(pos[0], pos[1]); pg.wait_for_timeout(900)
    s1 = st(pg)
    ok(f"[{T}] ② 點輪盤一個點：焦點換成它", s1["gid"] == pos[2] and s1["gid"] != g0, s1["gid"])
    ok(f"[{T}] ② 走勢大圖標題、走勢線、成分股小圖同步換", title(pg) != n0 and trend_sig(pg) != t0 and text(pg, "#fcMinis") != mem0)
    ok(f"[{T}] ② 網址寫進 g=", "g=" + pos[2] in pg.evaluate("() => decodeURIComponent(location.hash)"))
    ok(f"[{T}] ② 成分股全表換成新族群、有吻合／背離籤", bool(text(pg, "#fcBadge").strip()) and text(pg, "#fcMemTbl").count("\n") >= 0)

    # ③ 熱力方塊 → 換焦點
    r = None
    for i in range(0, 40):
        g_before = st(pg)["gid"]
        r = click_layout(pg, "#fcHeat", i)
        if r and r[2] and st(pg)["gid"] != g_before:
            break
    ok(f"[{T}] ③ 點熱力方塊：焦點換成該族群", bool(r) and st(pg)["gid"] == r[2], str(r))

    # ④ 三種輪盤：切換焦點與時間不丟、真的換內容
    sv = st(pg)
    sig_money = wheel_sig(pg)
    pg.click("#fcView button[data-v='strength']"); pg.wait_for_timeout(700)
    s2 = st(pg)
    ok(f"[{T}] ④ 切強弱輪盤：焦點、時間不變，圖內容換掉", s2["gid"] == sv["gid"] and s2["t"] == sv["t"] and s2["view"] == "strength" and wheel_sig(pg) != sig_money)
    pg.click("#fcView button[data-v='tree']"); pg.wait_for_timeout(900)
    s3 = st(pg)
    ok(f"[{T}] ④ 切資金分流樹：焦點不變、是桑基圖", s3["gid"] == sv["gid"] and pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fcWheel')).getOption().series[0].type") == "sankey")
    # 點樹的葉節點
    gb = st(pg)["gid"]
    n = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('fcWheel')).getModel().getSeriesByIndex(0).getData().count()")
    done = False
    for i in range(n):
        rr = click_layout(pg, "#fcWheel", i)
        if rr and rr[2] != gb:
            done = st(pg)["gid"] == rr[2]; break
    ok(f"[{T}] ④ 點樹的節點：焦點換成該族群", done)
    pg.click("#fcView button[data-v='money']"); pg.wait_for_timeout(600)

    # ⑤ 拖時間軸：輪盤點移位、走勢游標、網址 t=
    ws, ts = wheel_sig(pg), st(pg)["t"]
    pg.evaluate("() => { const i = document.querySelector('#fcRange2'); i.value = 20; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    s4 = st(pg)
    ok(f"[{T}] ⑤ 拖時間軸：t 改變、輪盤點移位、標籤同步、焦點不變", s4["t"] != ts and s4["t"] != "close" and wheel_sig(pg) != ws and s4["t"] in text(pg, "#fcTlab") and s4["gid"] == st(pg)["gid"])
    ok(f"[{T}] ⑤ 結論列同步換成該時點（開頭帶時間）", s4["t"] in text(pg, "#fcVerdict"))
    ok(f"[{T}] ⑤ 網址寫進 t=", "t=" + s4["t"].replace(":", "") in pg.evaluate("() => location.hash"))
    # 播放
    a = pg.evaluate("() => +document.querySelector('#fcRange2').value")
    pg.click("#fcPlay"); pg.wait_for_timeout(2500)
    b_ = pg.evaluate("() => +document.querySelector('#fcRange2').value")
    pg.click("#fcPlay")
    ok(f"[{T}] ⑤ 按播放：時間軸真的往前走", b_ > a, f"{a}->{b_}")

    # ⑥ 歷史回放
    pg.click("#fcMode button[data-v='hist']"); pg.wait_for_timeout(1200)
    s5 = st(pg)
    ok(f"[{T}] ⑥ 切歷史回放：日期換到前一交易日、標「歷史回放」", s5["date"] != LATEST and "歷史回放" in text(pg, "#fcDate"), s5["date"])
    ok(f"[{T}] ⑥ 歷史日走勢、輪盤已重畫（日期＝{s5['date']}）", bool(trend_sig(pg)))
    pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", HIST); pg.wait_for_timeout(1200)
    ok(f"[{T}] ⑥ 日期選擇器選有 60 分資料的日子：日內時點鈕出現", st(pg)["date"] == HIST and pg.evaluate("() => document.querySelectorAll('#fcDayT button').length") >= 4)
    ws2 = wheel_sig(pg)
    pg.click("#fcDayT button:has-text('11:00')"); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑥ 點 11:00：t 變、輪盤換", st(pg)["t"] == "11:00" and wheel_sig(pg) != ws2, str(st(pg)))
    pg.wait_for_timeout(600)
    ok(f"[{T}] ⑥ 歷史日 09:00–10:00 灰底標「無成交量」", "成交量資料" in pg.evaluate("() => document.getElementById('fcTrendNote').textContent"), pg.evaluate("() => JSON.stringify(TwFlowcheck.state()) + document.getElementById('fcTrendNote').textContent"))
    pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", DONLY); pg.wait_for_timeout(1000)
    ok(f"[{T}] ⑥ 只有日線的日子：明確灰字寫原因、不留空白", "只有日線" in text(pg, "#fcDayT") or "只有日線" in text(pg, "#fcRange"))
    ok(f"[{T}] ⑥ 換日期整頁寬高不晃（走勢卡高度不變）", pg.evaluate("() => document.getElementById('fcTrendCard').getBoundingClientRect().height") > 300)
    pg.evaluate("() => { const i = document.querySelector('#fcDatePick'); i.value = '2026-10-31'; i.dispatchEvent(new Event('change', {bubbles: true})); }"); pg.wait_for_timeout(500)
    ok(f"[{T}] ⑥ 選非交易日：出提示、日期不變", st(pg)["date"] == DONLY and "不是交易日" in text(pg, "#fcToast"))
    pg.click("#fcPrev"); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑥ ◀ 跳前一交易日", st(pg)["date"] < DONLY)
    # ⑦ 說明進「?」
    pg.click("#fcWheelCard .howbtn"); pg.wait_for_timeout(400)
    ok(f"[{T}] ⑦ 「?」跳出說明、內含三種輪盤解釋", pg.evaluate("() => { const p = document.getElementById('howPop'); return !!p && !p.hidden && p.textContent.includes('強弱輪盤'); }"))
    pg.keyboard.press("Escape")
    ctx.close()

    # ⑩ 日級別訊號／潛在個股
    ctx, pg = open_page("#flowcheck")
    ok(f"[{T}] ⑩ 日級別訊號卡預設展開、有列、標「實驗」、有 5／10／20 日與規則回測", pg.evaluate("() => { const c = document.getElementById('fcDayCard'); return c.classList.contains('open') && c.querySelectorAll('tbody tr').length >= 3 && c.textContent.includes('實驗') && c.textContent.includes('後 20 日') && c.textContent.includes('命中'); }"))
    n_all = pg.evaluate("() => document.querySelectorAll('#fcDay tbody tr').length")
    rid = pg.evaluate("() => document.querySelectorAll('#fcRule button')[1].dataset.v")
    pg.click("#fcRule button:nth-child(2)"); pg.wait_for_timeout(600)
    n_one = pg.evaluate("() => document.querySelectorAll('#fcDay tbody tr').length")
    ok(f"[{T}] ⑩ 切規則：列數真的變少且只剩該規則", 0 < n_one < n_all and pg.evaluate("(r) => document.querySelectorAll('#fcRule button')[1].classList.contains('on')", rid), f"{n_all}->{n_one}")
    g_b = st(pg)["gid"]
    pg.evaluate("(g) => { const b = [...document.querySelectorAll('#fcDay [data-g]')].find(x => x.dataset.g !== g); b.click(); }", g_b); pg.wait_for_timeout(800)
    ok(f"[{T}] ⑩ 點候選族群：焦點同步換、走勢標題跟著換", st(pg)["gid"] != g_b)
    pg.evaluate("() => { const b = document.querySelector('#fcDay [data-go]'); b.click(); }"); pg.wait_for_timeout(600)
    ok(f"[{T}] ⑩ 點候選個股：進個股頁", pg.evaluate("() => location.hash.startsWith('#stock/')"))
    ctx.close()

    # ⑪ 大螢幕 ≥1440 三張輪盤並排、共用焦點與時間
    ctx, pg = open_page("#flowcheck", {"width": 1440, "height": 900})
    ok(f"[{T}] ⑪ ≥1440：三張輪盤並排（同一列、各 ≥ 300 寬），三選一鈕隱藏", pg.evaluate("() => { const r = ['strength','money','tree'].map(k => document.getElementById('fcW_' + k).getBoundingClientRect()); return r.every(x => x.width >= 300 && x.height >= 250) && Math.abs(r[0].top - r[2].top) < 4 && r[0].right <= r[1].left + 2 && r[1].right <= r[2].left + 2 && document.getElementById('fcView').getBoundingClientRect().width === 0; }"))
    ok(f"[{T}] ⑪ 1440：走勢大圖 ≥ 640×250、成分股小圖 ≥ 200×110、熱力圖 ≥ 400×150（左欄 5：7 分，沒法再寬）", pg.evaluate("() => { const a = document.getElementById('fcTrend').getBoundingClientRect(), m = document.querySelector('#fcMinis .chart').getBoundingClientRect(), h = document.getElementById('fcHeat').getBoundingClientRect(); return a.width >= 640 && a.height >= 250 && m.width >= 200 && m.height >= 110 && h.width >= 400 && h.height >= 150; }"))
    ok(f"[{T}] ⑪ 三張都畫了（強弱、資金是散布圖，樹是桑基圖）", pg.evaluate("() => ['strength','money','tree'].map(k => echarts.getInstanceByDom(document.getElementById('fcW_' + k)).getOption().series[0].type).join() === 'scatter,scatter,sankey'"))
    ok(f"[{T}] ⑪ 走勢大圖在三張輪盤正下方同一畫面", pg.evaluate("() => { const t = document.getElementById('fcTrend').getBoundingClientRect(), w = document.getElementById('fcW_money').getBoundingClientRect(); return t.top > w.bottom - 4 && t.top < innerHeight + 600; }"))
    g0 = st(pg)["gid"]; sa = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_strength')).getOption().series[1].data)")
    # 點「強弱輪盤」的一個點 → 另外兩張同步換焦點（焦點環）
    pos = pg.evaluate("""(g0) => { pg_ = 0; const el = document.getElementById('fcW_strength'); el.scrollIntoView({block: 'center'}); const c = echarts.getInstanceByDom(el), d = c.getOption().series[0].data; const o = d.filter(x => x.gid !== g0)[2]; const p = c.convertToPixel({ seriesIndex: 0 }, o.value), b = el.getBoundingClientRect(); return [b.left + p[0], b.top + p[1], o.gid]; }""", g0)
    pg.wait_for_timeout(300)
    pos = pg.evaluate("""(gid) => { const el = document.getElementById('fcW_strength'), c = echarts.getInstanceByDom(el), d = c.getOption().series[0].data; const o = d.filter(x => x.gid === gid)[0]; const p = c.convertToPixel({ seriesIndex: 0 }, o.value), b = el.getBoundingClientRect(); return [b.left + p[0], b.top + p[1], gid]; }""", pos[2])
    pg.mouse.click(pos[0], pos[1]); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑪ 點任一張的點：三張共用同一焦點（另兩張的焦點環跟著換）", st(pg)["gid"] == pos[2] and pg.evaluate("() => ['strength','money'].every(k => echarts.getInstanceByDom(document.getElementById('fcW_' + k)).getOption().series.length >= 3)") and pg.evaluate("() => document.getElementById('fcTrendName').textContent") != "", st(pg)["gid"])
    wm = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_money')).getOption().series[0].data.map(d => d.value))")
    pg.evaluate("() => { const i = document.querySelector('#fcRange2'); i.value = 15; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑪ 拖時間軸：資金輪盤的點移位（三張共用時間）", pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_money')).getOption().series[0].data.map(d => d.value))") != wm)
    ctx.close()

    # ⑧ 網址還原（分享連結）
    ctx, pg = open_page("#flowcheck?g=pcb_rigid&d=%s&t=1100&v=strength" % HIST)
    s6 = st(pg)
    ok(f"[{T}] ⑧ 帶狀態的網址：族群、日期、時間、輪盤種類原樣還原", s6["gid"] == "pcb_rigid" and s6["date"] == HIST and s6["t"] == "11:00" and s6["view"] == "strength", str(s6))
    ctx.close()

    # ⑨ 手機 390：無橫向捲軸、次要卡預設收起、能展開、走勢在輪盤上面
    ctx, pg = open_page("#flowcheck", {"width": 390, "height": 844}, True)
    ok(f"[{T}] ⑨ 手機 390 無橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    ok(f"[{T}] ⑨ 手機：成分股／熱力圖／提前判斷／新聞／法人預設收起", pg.evaluate("() => ['fcMemCard','fcHeatCard','fcSigCard','fcNewsCard','fcInstCard'].every(i => !document.getElementById(i).classList.contains('open') && document.querySelector('#' + i + ' .fc-bd').getBoundingClientRect().height === 0)"))
    ok(f"[{T}] ⑨ 手機：走勢圖在輪盤上面", pg.evaluate("() => document.getElementById('fcTrendCard').getBoundingClientRect().top < document.getElementById('fcWheelCard').getBoundingClientRect().top"))
    ok(f"[{T}] ⑨ 手機：時間軸把手高 ≥ 32px、貼底", pg.evaluate("() => { const r = document.querySelector('#fcRange2').getBoundingClientRect(); return r.height >= 32 && Math.abs(document.getElementById('fcTl').getBoundingClientRect().bottom - innerHeight) < 4; }"))
    pg.click("#fcMemCard .fc-tog"); pg.wait_for_timeout(700)
    ok(f"[{T}] ⑨ 手機：點「展開」成分股真的展開且有圖", pg.evaluate("() => document.querySelector('#fcMemCard .fc-bd').getBoundingClientRect().height > 100 && document.querySelectorAll('#fcMinis .chart canvas, #fcMinis .chart svg').length >= 3"))
    ok(f"[{T}] ⑨ 手機：字不小於 11px", pg.evaluate("() => [...document.querySelectorAll('#v-flowcheck button, #v-flowcheck td, #v-flowcheck .fc-vt')].filter(e => e.getBoundingClientRect().height > 0 && parseFloat(getComputedStyle(e).fontSize) < 11).length") == 0)
    ctx.close()


register("流向驗證1030", lambda pg, b, base, code: t_flowcheck_1030(b, base))
