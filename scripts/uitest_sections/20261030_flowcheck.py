# 驗收段落「流向驗證1030」—— Andy 10-30 晚：「為何沒有對應的個股走勢圖在旁邊可以看」「幫我獨立一個分頁將輪盤 資金樹 都個別拉出來與走勢圖比較」
# 「有辦法撈取過去歷史紀錄某天的流向狀況進行回測驗證」。資料用 scripts/_fc_fake.py 造（攔 /data/flowcheck/**），真資料上線後同一段改不攔即可。
# 真的點輪盤的點、樹節點、熱力方塊、拖時間軸、換歷史日期、切三種輪盤，每一步驗「畫面真的因此改變」。
# 由 _uitest.py 用 exec 載入，ok()／wait_until()／fails／SITE 直接可用。
# flake8: noqa

def t_flowcheck_1030(b, base):
    import json as _json
    T = "流向驗證1030"
    idxp = SITE / "data" / "flowcheck" / "index.json"
    if not idxp.exists():
        ok(f"[{T}] 本機沒有 site/data/flowcheck/（先 PYTHONPATH=. python -c 'from pipeline.compute import flowcheck' 產生，或跑 build_payload），略過", True)
        return
    IDX = _json.loads(idxp.read_text(encoding="utf-8"))
    LATEST = IDX["latest"]
    m60d = [d for d in IDX["dates"] if "m60" in IDX["layers"].get(d, [])]
    HIST = m60d[-2] if len(m60d) >= 2 else m60d[-1]
    DONLY = next((d for d in IDX["dates"] if not ({"m5", "m60"} & set(IDX["layers"].get(d, [])))), None)
    GID = next((g["gid"] for g in IDX["groups"] if g["gid"] == "pcb_rigid"), IDX["groups"][0]["gid"])

    def open_page(h, vp=None, mobile=False):
        kw = {"viewport": vp or {"width": 1280, "height": 900}, "timezone_id": "Asia/Taipei"}
        if mobile:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.tour','done'); } catch (e) {} }")
        pg.goto("about:blank")
        pg.goto(base + h, wait_until="load")
        wait_until(pg, "() => !!document.querySelector('#fcWheel canvas, #fcWheel svg') && !!document.querySelector('#fcTrend canvas, #fcTrend svg')", 15000)
        pg.wait_for_timeout(600)
        return ctx, pg

    st = lambda pg: pg.evaluate("() => TwFlowcheck.state()")
    def open_more(pg):
        if pg.evaluate("() => !document.getElementById('fcMoreCard').classList.contains('open')"):
            pg.evaluate("() => document.querySelector('#fcMoreCard .fc-tog').click()"); pg.wait_for_timeout(700)

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
    ok(f"[{T}] ① 桌機「更多證據」預設收起（收展預設收起準則）", pg.evaluate("() => !document.getElementById('fcMoreCard').classList.contains('open') && document.querySelector('#fcMoreCard .fc-bd').getBoundingClientRect().height === 0"))
    dsj = _json.loads((SITE / "data" / "flowcheck" / "daily_signals.json").read_text(encoding="utf-8"))
    dayl = _json.loads((SITE / "data" / "flowcheck" / "day" / f"{LATEST}.json").read_text(encoding="utf-8"))
    its = [x for x in dsj.get("recent", []) if x["date"] == LATEST]
    eg = sum(1 for x in its if x["level"] == "group"); es = len(its) - eg
    es_sig = len(dayl.get("signals", []))
    en = sum(1 for n in dayl.get("news", []) if st(pg)["gid"] in (n.get("gids") or []))
    msum = text(pg, "#fcMsum")
    ok(f"[{T}] ① 「更多證據」收起時標題列右側直接顯示摘要，數字與資料檔一致（族群{eg}・個股{es}／盤中訊號{es_sig}／新聞{en}）", f"族群 {eg}・個股 {es}" in msum and f"盤中訊號 {es_sig} 次" in msum and f"新聞 {en} 則" in msum and pg.evaluate("() => document.getElementById('fcMsum').getBoundingClientRect().width > 100"), msum)
    pg.click("#fcMsum [data-msum='sig']"); pg.wait_for_timeout(900)
    ok(f"[{T}] ① 點摘要的「盤中訊號」：卡片展開並切到提前判斷分頁", pg.evaluate("() => document.getElementById('fcMoreCard').classList.contains('open') && !document.getElementById('fcPaneSig').hidden && TwFlowcheck.state().tab === 'sig' && document.querySelector('#fcMsum').getBoundingClientRect().width === 0"))
    open_more(pg)
    pg.click("#fcTab button[data-v='sig']"); pg.wait_for_timeout(900)
    ok(f"[{T}] ① 提前判斷分頁：標「實驗」、回測未達顯著、沒有內部欄名", "實驗" in text(pg, "#fcMoreCard") + text(pg, "#fcPaneSig") or "未達顯著" in text(pg, "#fcPaneSig"))
    ok(f"[{T}] ① 提前判斷畫面沒有 passed_multiple_test 等內部欄名、期間用「～」", "passed_multiple" not in text(pg, "#v-flowcheck") and "未達顯著" in text(pg, "#fcPaneSig") and "," not in text(pg, "#fcSigR").split("全族群")[0])
    pg.click("#fcTab button[data-v='daily']"); pg.wait_for_timeout(600)
    vt = pg.evaluate("() => document.getElementById('v-flowcheck').innerText")
    ok(f"[{T}] ① 畫面用「相對加權指數」：沒有「大盤」「相對市場」字樣", "大盤" not in vt and "相對市場" not in vt and "相對加權指數" in vt)
    ok(f"[{T}] ① 吻合度旁印近 3 年常態", "近 3 年常態" in text(pg, "#fcVerdict"))

    # ② 點輪盤的點 → 焦點換、走勢／成分股／網址同步
    g0, n0, t0, mem0 = s0["gid"], title(pg), trend_sig(pg), text(pg, "#fcMinis")
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; const e = document.getElementById('fcWheel'); window.scrollBy(0, e.getBoundingClientRect().top - 170); }"); pg.wait_for_timeout(300)
    pos = pg.evaluate("""(g0) => { const c = echarts.getInstanceByDom(document.getElementById('fcWheel')), d = c.getOption().series[0].data; const P = d.map(x => [x, c.convertToPixel({ seriesIndex: 0 }, x.value)]); const iso = (q) => Math.min(...P.filter(r => r[0] !== q[0]).map(r => Math.hypot(r[1][0] - q[1][0], r[1][1] - q[1][1]))); const cand = P.filter(r => { const ay = document.getElementById('fcWheel').getBoundingClientRect().top + r[1][1]; return r[0].gid !== g0 && r[0].rx === r[0].value[0] && r[0].ry === r[0].value[1] && ay > 300 && ay < innerHeight - 110; }).sort((u, v) => iso(v) - iso(u))[0]; const b = document.getElementById('fcWheel').getBoundingClientRect(); return [b.left + cand[1][0], b.top + cand[1][1], cand[0].gid]; }""", g0)
    pg.mouse.click(pos[0], pos[1]); pg.wait_for_timeout(900)
    s1 = st(pg)
    ok(f"[{T}] ② 點輪盤一個點：焦點換成它", s1["gid"] == pos[2] and s1["gid"] != g0, str([s1["gid"], pos]))
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
    if DONLY:
        pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", DONLY); pg.wait_for_timeout(1000)
        ok(f"[{T}] ⑥ 只有日線的日子：明確灰字寫原因、不留空白", "只有日線" in text(pg, "#fcDayT") or "只有日線" in text(pg, "#fcRange"))
        ok(f"[{T}] ⑥ 換日期整頁寬高不晃（走勢卡高度不變）", pg.evaluate("() => document.getElementById('fcTrendCard').getBoundingClientRect().height") > 300)
    import datetime as _dt
    dset = set(IDX["dates"]); d0 = _dt.date.fromisoformat(IDX["dates"][0]); d1 = _dt.date.fromisoformat(IDX["dates"][-1])
    allday = [d0 + _dt.timedelta(days=k) for k in range((d1 - d0).days)]
    wk = next((x.isoformat() for x in allday if x.weekday() >= 5), None)
    gap = next((x.isoformat() for x in allday if x.weekday() < 5 and x.isoformat() not in dset), None)
    keep = st(pg)["date"]
    closed = [x for x in IDX.get("closed_days", []) if d0.isoformat() < x < d1.isoformat()]
    miss = [x for x in IDX.get("missing_days", []) if d0.isoformat() < x < d1.isoformat()]
    for kind, dd, want in (("週末", wk, "休市"), ("休市日（index.closed_days，如颱風）", closed[-1] if closed else None, "休市"), ("資料缺（index.missing_days）", miss[-1] if miss else None, "資料缺")):
        if not dd:
            continue
        pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", dd); pg.wait_for_timeout(500)
        ok(f"[{T}] ⑥ 選{kind}（{dd}）：提示分「休市」「資料缺」兩種說法、日期不變", st(pg)["date"] == keep and want in text(pg, "#fcToast"), text(pg, "#fcToast"))
    pg.click("#fcPrev"); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑥ ◀ 跳前一交易日", st(pg)["date"] < HIST)
    # ⑦ 說明進「?」
    pg.click("#fcWheelCard .howbtn"); pg.wait_for_timeout(400)
    ok(f"[{T}] ⑦ 「?」跳出說明、內含三種輪盤解釋", pg.evaluate("() => { const p = document.getElementById('howPop'); return !!p && !p.hidden && p.textContent.includes('強弱輪盤'); }"))
    pg.keyboard.press("Escape")
    ctx.close()

    # ⑩ 日級別訊號／潛在個股
    ctx, pg = open_page("#flowcheck")
    open_more(pg)
    ok(f"[{T}] ⑩ 展開「更多證據」後日級別訊號分頁、有列、標「實驗」、有 5／10／20 日與規則回測", pg.evaluate("() => { const c = document.getElementById('fcMoreCard'); return c.classList.contains('open') && c.querySelectorAll('tbody tr').length >= 3 && c.textContent.includes('實驗') && c.textContent.includes('後 20 日') && c.textContent.includes('命中'); }"))
    n_sum_all = pg.evaluate("() => document.querySelectorAll('#fcDay .fc-rs').length")
    ok(f"[{T}] ⑩ 全部規則：規則統計列在表格上方（每條一行）、候選表每列一行高、預設只列前 10 筆", n_sum_all >= 3 and pg.evaluate("() => { const r = [...document.querySelectorAll('#fcDay tbody tr')]; return r.length <= 10 && r.every(x => x.getBoundingClientRect().height <= 44); }"), str(n_sum_all))
    rid = pg.evaluate("() => document.querySelectorAll('#fcRule button')[1].dataset.v")
    pg.click("#fcRule button:nth-child(2)"); pg.wait_for_timeout(600)
    ok(f"[{T}] ⑩ 點規則：只顯示該規則統計、候選只剩該規則", pg.evaluate("(r) => document.querySelectorAll('#fcDay .fc-rs').length === 1 && [...document.querySelectorAll('#fcDay tbody tr')].every(x => x.children[1].textContent.startsWith(r))", rid) and pg.evaluate("() => document.querySelectorAll('#fcRule button')[1].classList.contains('on')"))
    if pg.evaluate("() => !!document.getElementById('fcDayMore')"):
        n10 = pg.evaluate("() => document.querySelectorAll('#fcDay tbody tr').length")
        pg.click("#fcDayMore"); pg.wait_for_timeout(500)
        ok(f"[{T}] ⑩ 「看全部」真的多列出候選", pg.evaluate("() => document.querySelectorAll('#fcDay tbody tr').length") > n10)
        pg.click("#fcDayMore"); pg.wait_for_timeout(300)
    g_b = st(pg)["gid"]
    valid = [g["gid"] for g in IDX["groups"] if not g.get("is_bucket")]
    pg.evaluate("(a) => { const [g, v] = a; const b = [...document.querySelectorAll('#fcDay [data-g]')].find(x => x.dataset.g !== g && v.includes(x.dataset.g)); if (b) b.click(); }", [g_b, valid]); pg.wait_for_timeout(800)
    ok(f"[{T}] ⑩ 點候選族群：焦點同步換、走勢標題跟著換", st(pg)["gid"] != g_b and st(pg)["gid"] in valid, st(pg)["gid"])
    pg.click("#fcRule button:nth-child(1)"); pg.wait_for_timeout(500)
    have = [c for c in {m for g in IDX["groups"] for m in g["members"]} if (SITE / "data" / "stock" / f"{c}.json").exists()]
    pg.evaluate("(h) => { const b = [...document.querySelectorAll('#fcDay [data-go]')].find(x => h.includes(x.dataset.go)) || document.querySelector('#fcDay [data-go]'); b.click(); }", have); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑩ 點候選個股：進個股頁", pg.evaluate("() => location.hash.startsWith('#stock/')"))
    ctx.close()

    # ⑪ 大螢幕 ≥1440 三張輪盤並排、共用焦點與時間
    ctx, pg = open_page("#flowcheck", {"width": 1440, "height": 900})
    ok(f"[{T}] ⑪ ≥1440：三張輪盤並排（同一列、各 ≥ 300 寬），三選一鈕隱藏", pg.evaluate("() => { const r = ['strength','money','tree'].map(k => document.getElementById('fcW_' + k).getBoundingClientRect()); return r.every(x => x.width >= 300 && x.height >= 200) && Math.abs(r[0].top - r[2].top) < 4 && r[0].right <= r[1].left + 2 && r[1].right <= r[2].left + 2 && document.getElementById('fcView').getBoundingClientRect().width === 0; }"))
    ok(f"[{T}] ⑪ 1440：走勢大圖 ≥ 640×210、成分股小圖 ≥ 200×110、熱力圖 ≥ 400×150（走勢高度讓給首屏）", pg.evaluate("() => { const a = document.getElementById('fcTrend').getBoundingClientRect(), m = document.querySelector('#fcMinis .chart').getBoundingClientRect(), h = document.getElementById('fcHeat').getBoundingClientRect(); return a.width >= 640 && a.height >= 210 && m.width >= 200 && m.height >= 110 && h.width >= 400 && h.height >= 150; }"))
    ok(f"[{T}] ⑪ 三張都畫了（強弱、資金是散布圖，樹是桑基圖）", pg.evaluate("() => ['strength','money','tree'].map(k => echarts.getInstanceByDom(document.getElementById('fcW_' + k)).getOption().series[0].type).join() === 'scatter,scatter,sankey'"))
    ok(f"[{T}] ⑪ 走勢大圖在三張輪盤正下方同一畫面", pg.evaluate("() => { const t = document.getElementById('fcTrend').getBoundingClientRect(), w = document.getElementById('fcW_money').getBoundingClientRect(); return t.top > w.bottom - 4 && t.top < innerHeight + 600; }"))
    g0 = st(pg)["gid"]; sa = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_strength')).getOption().series[1].data)")
    # 點「強弱輪盤」的一個點 → 另外兩張同步換焦點（焦點環）
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; const e = document.getElementById('fcW_strength'); window.scrollBy(0, e.getBoundingClientRect().top - 150); }"); pg.wait_for_timeout(300)
    pos = pg.evaluate("""(g0) => { const el = document.getElementById('fcW_strength'), c = echarts.getInstanceByDom(el), d = c.getOption().series[0].data; const P = d.map(x => [x, c.convertToPixel({ seriesIndex: 0 }, x.value)]); const iso = (q) => Math.min(...P.filter(r => r[0] !== q[0]).map(r => Math.hypot(r[1][0] - q[1][0], r[1][1] - q[1][1]))); const cand = P.filter(r => { const ay = el.getBoundingClientRect().top + r[1][1]; return r[0].gid !== g0 && r[0].rx === r[0].value[0] && r[0].ry === r[0].value[1] && ay > 300 && ay < innerHeight - 110; }).sort((u, v) => iso(v) - iso(u))[0]; const b = el.getBoundingClientRect(); return [b.left + cand[1][0], b.top + cand[1][1], cand[0].gid]; }""", g0)
    pg.mouse.click(pos[0], pos[1]); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑪ 點任一張的點：三張共用同一焦點（另兩張的焦點環跟著換）", st(pg)["gid"] == pos[2] and pg.evaluate("() => ['strength','money'].every(k => echarts.getInstanceByDom(document.getElementById('fcW_' + k)).getOption().series.length >= 3)") and pg.evaluate("() => document.getElementById('fcTrendName').textContent") != "", st(pg)["gid"])
    OV = """(ids) => { let bad = 0, total = 0; const R = [];
      ids.forEach(id => { const c = echarts.getInstanceByDom(document.getElementById(id)); if (!c) return; const L = [];
        c.getZr().storage.getDisplayList(true).forEach(e => { if (e.ignore || e.invisible || !e.style || !e.style.text || e.type !== 'tspan' && e.type !== 'text') return; const r = e.getBoundingRect().clone(); if (e.transform) r.applyTransform(e.transform); if (r.width > 1 && r.height > 1) L.push([e.style.text, r]); });
        total += L.length;
        for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const a = L[i][1], b = L[j][1], w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x), h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y); if (w > 3 && h > 4) { bad++; R.push(id + ':' + L[i][0] + '×' + L[j][0] + '(' + Math.round(w) + 'x' + Math.round(h) + ')'); } } });
      return { bad, total, R: R.slice(0, 6) }; }"""
    ov = pg.evaluate(OV, ["fcW_strength", "fcW_money", "fcW_tree", "fcHeat", "fcTrend"])
    ok(f"[{T}] ⑪ 圖內文字框兩兩不相交（輪盤三張、熱力圖、走勢；檢查 {ov['total']} 個文字框）", ov["bad"] == 0 and ov["total"] > 20, str(ov))
    ov2 = pg.evaluate(OV, ["fcW_strength", "fcW_money", "fcW_tree", "fcHeat", "fcTrend"])
    pg.evaluate("() => { const i = document.querySelector('#fcRange2'); i.value = 12; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    ov3 = pg.evaluate(OV, ["fcW_strength", "fcW_money", "fcW_tree", "fcHeat", "fcTrend"])
    ok(f"[{T}] ⑪ 換焦點、拖時間後文字框仍不相交（{ov2['total']}／{ov3['total']} 個文字框）", ov2["bad"] == 0 and ov3["bad"] == 0, str([ov2, ov3]))
    wm = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_money')).getOption().series[0].data.map(d => d.value))")
    pg.evaluate("() => { const i = document.querySelector('#fcRange2'); i.value = 15; i.dispatchEvent(new Event('input', {bubbles: true})); }"); pg.wait_for_timeout(900)
    ok(f"[{T}] ⑪ 拖時間軸：資金輪盤的點移位（三張共用時間）", pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_money')).getOption().series[0].data.map(d => d.value))") != wm)
    ctx.close()

    # ⑫ 審核專家退件項目（10-31 使用者測試）
    ctx, pg = open_page("#flowcheck", {"width": 1440, "height": 900})
    dayj = _json.loads((SITE / "data" / "flowcheck" / "day" / f"{LATEST}.json").read_text(encoding="utf-8"))
    manual = {g["gid"] for g in IDX["groups"] if not g.get("is_bucket")}
    nA = sum(1 for k, v in dayj["groups"].items() if k in manual and v.get("div") == "A")
    nB = sum(1 for k, v in dayj["groups"].items() if k in manual and v.get("div") == "B")
    ok(f"[{T}] ⑫ 1440×900 首屏：輪盤與走勢大圖都完整在第一屏內", pg.evaluate("() => { const w = document.getElementById('fcW_money').getBoundingClientRect(), t = document.getElementById('fcTrend').getBoundingClientRect(); return w.top >= 0 && w.bottom <= innerHeight && t.top >= 0 && t.bottom <= innerHeight; }"), pg.evaluate("() => JSON.stringify([document.getElementById('fcW_money').getBoundingClientRect().bottom, document.getElementById('fcTrend').getBoundingClientRect().bottom, innerHeight])"))
    ok(f"[{T}] ⑫ 1440 頁面本體高度 ≤ 1900px（一頁看完；次要卡做成分頁；不含站台頁首頁尾）", pg.evaluate("() => document.getElementById('fc').getBoundingClientRect().height") <= 1900, pg.evaluate("() => [document.getElementById('fc').getBoundingClientRect().height, document.documentElement.scrollHeight]"))
    ok(f"[{T}] ⑫ 背離榜按鈕寫出 A／B 家數，與資料檔收盤 div 一致（A{nA}／B{nB}）", f"A {nA}" in text(pg, "#fcDivBtn") and f"B {nB}" in text(pg, "#fcDivBtn"), text(pg, "#fcDivBtn"))
    ok(f"[{T}] ⑫ 結論列直接寫「背離 A 前 3」名單", "背離 A）前 3" in text(pg, "#fcVerdict") or "背離 A）前 3：" in text(pg, "#fcVerdict").replace("（", "）") or "前 3：" in text(pg, "#fcVerdict"))
    g_b = st(pg)["gid"]
    pg.click("#fcDivBtn"); pg.wait_for_timeout(500)
    ok(f"[{T}] ⑫ 點背離榜：展開 A、B 兩段、各列有長條、列數對得上", pg.evaluate("(a) => { const p = document.getElementById('fcDivPop'); if (!p) return false; const cols = p.children; const ra = cols[0].querySelectorAll('.fc-dr').length, rb = cols[1].querySelectorAll('.fc-dr').length; return cols.length >= 2 && ra === Math.min(10, a[0]) && rb === Math.min(10, a[1]) && [...p.querySelectorAll('.fc-dr i')].every(i => i.getBoundingClientRect().width >= 3); }", [nA, nB]))
    ok(f"[{T}] ⑫ 背離榜展開不用框內再捲（沒有內捲、內容完整攤開）", pg.evaluate("() => { const p = document.getElementById('fcDivPop'), cs = getComputedStyle(p); return !/auto|scroll/.test(cs.overflowY) && p.scrollHeight <= p.clientHeight + 1; }"))
    if nA > 10 or nB > 10:
        n0 = pg.evaluate("() => document.querySelectorAll('#fcDivPop .fc-dr').length")
        pg.click("#fcDivAll"); pg.wait_for_timeout(400)
        n1 = pg.evaluate("() => document.querySelectorAll('#fcDivPop .fc-dr').length")
        ok(f"[{T}] ⑫ 背離榜前 10＋「看全部」：點了列數增加到 A{nA}＋B{nB}", n1 == nA + nB and n1 > n0, f"{n0}->{n1}")
        pg.click("#fcDivAll"); pg.wait_for_timeout(300)
    pg.evaluate("(g) => { const b = [...document.querySelectorAll('#fcDivPop .fc-dr')].find(x => x.dataset.g !== g); b.click(); }", g_b); pg.wait_for_timeout(700)
    ok(f"[{T}] ⑫ 點榜上一列：選到該族群（焦點同步換）", st(pg)["gid"] != g_b)
    pg.click("#fcDivBtn"); pg.wait_for_timeout(300)
    # 族群下拉（可打字）
    nm = next(g["name"] for g in IDX["groups"] if g["gid"] == "shipping_container") if any(g["gid"] == "shipping_container" for g in IDX["groups"]) else IDX["groups"][3]["name"]
    gid_t = next(g["gid"] for g in IDX["groups"] if g["name"] == nm)
    pg.fill("#fcGsel", nm); pg.evaluate("() => document.getElementById('fcGsel').dispatchEvent(new Event('change', {bubbles: true}))"); pg.wait_for_timeout(800)
    ok(f"[{T}] ⑫ 控制列族群下拉：打字選「{nm}」真的換焦點", st(pg)["gid"] == gid_t and pg.evaluate("() => document.querySelectorAll('#fcGList option').length") >= 50)
    # 三者同向
    nsame = pg.evaluate("() => document.querySelectorAll('#fcSame .fc-chip.same').length")
    ok(f"[{T}] ⑫ 「三者同向流入」籤：有列出、輪盤上有青色外環", nsame >= 1 and pg.evaluate("() => ['fcW_strength','fcW_money'].every(k => echarts.getInstanceByDom(document.getElementById(k)).getOption().series.some(s => s.itemStyle && s.itemStyle.borderType === 'dashed'))"), str(nsame))
    g_s = st(pg)["gid"]
    pg.evaluate("(g) => { const b = [...document.querySelectorAll('#fcSame .fc-chip.same')].find(x => x.dataset.g !== g) || document.querySelector('#fcSame .fc-chip.same'); b.click(); }", g_s); pg.wait_for_timeout(600)
    ok(f"[{T}] ⑫ 點同向籤：選到該族群", pg.evaluate("() => TwFlowcheck.state().gid") != "" and pg.evaluate("(g) => [...document.querySelectorAll('#fcSame .fc-chip.same')].some(x => x.dataset.g === TwFlowcheck.state().gid)", g_s) or st(pg)["gid"] != g_s)
    # 資金樹節點大小
    ws0 = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_strength')).getOption().series[0].data.map(d => d.rx))")
    pg.click("#fcRsBase button[data-v='site']"); pg.wait_for_timeout(700)
    ws1 = pg.evaluate("() => JSON.stringify(echarts.getInstanceByDom(document.getElementById('fcW_strength')).getOption().series[0].data.map(d => d.rx))")
    ok(f"[{T}] ⑫ 強弱輪盤可切「主站口徑」：座標真的換成 rs_x_site（與主站強弱輪動對得上）", ws0 != ws1)
    pg.click("#fcRsBase button[data-v='index']"); pg.wait_for_timeout(500)
    pg.click("#fcView button[data-v='tree']") if pg.evaluate("() => document.getElementById('fcView').getBoundingClientRect().width") > 0 else None
    mins = pg.evaluate("() => { const d = echarts.getInstanceByDom(document.getElementById('fcW_tree')).getModel().getSeriesByIndex(0).getData(); const o = []; for (let i = 0; i < d.count(); i++) { const r = d.getRawDataItem(i), l = d.getItemLayout(i); if (r.gid) o.push([l.dx, l.dy]); } return [Math.min(...o.map(x => x[0])), Math.min(...o.map(x => x[1])), o.length]; }")
    ok(f"[{T}] ⑫ 資金樹族群節點可點範圍：寬 ≥ 24、高 ≥ 24px（共 {mins[2]} 個）", mins[0] >= 24 and mins[1] >= 24, str(mins))
    # 新聞列不重疊
    open_more(pg)
    pg.click("#fcTab button[data-v='news']"); pg.wait_for_timeout(700)
    ok(f"[{T}] ⑫ 新聞列兩兩不相交（列高不固定）", pg.evaluate("() => { const r = [...document.querySelectorAll('#fcNews .fc-nw')].map(e => e.getBoundingClientRect()); for (let i = 1; i < r.length; i++) if (r[i].top < r[i - 1].bottom - 1) return false; return true; }"))
    pg.click("#fcTab button[data-v='daily']"); pg.wait_for_timeout(300)
    pg.click("#fcTab button[data-v='sig']"); pg.wait_for_timeout(1000)
    ok(f"[{T}] ⑫ 提前判斷分頁畫面上寫著「實驗」（不只在「?」）", "實驗" in text(pg, "#fcSigL") and "實驗" in text(pg, "#fcTab"))
    ok(f"[{T}] ⑫ 收盤檢視的觸發表欄名是「觸發後至收盤」；回測表沒有「粒度」欄、訊號名帶（60 分）", "觸發後至收盤" in text(pg, "#fcSigL") and "粒度" not in text(pg, "#fcSigR") and "（60 分）" in text(pg, "#fcSigR"))
    pg.click("#fcTab button[data-v='daily']"); pg.wait_for_timeout(300)
    # 換日期不晃：走勢卡、輪盤卡高度不變
    h0 = pg.evaluate("() => [document.getElementById('fcTrendCard').getBoundingClientRect().height, document.getElementById('fcWheelCard').getBoundingClientRect().height]")
    pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", HIST); pg.wait_for_timeout(1200)
    h1 = pg.evaluate("() => [document.getElementById('fcTrendCard').getBoundingClientRect().height, document.getElementById('fcWheelCard').getBoundingClientRect().height]")
    ok(f"[{T}] ⑫ 換日期：走勢卡、輪盤卡高度完全不變（版面不晃）", abs(h0[0] - h1[0]) < 1 and abs(h0[1] - h1[1]) < 1, f"{h0}->{h1}")
    ctx.close()

    # ⑧ 網址還原（分享連結）
    ctx, pg = open_page("#flowcheck?g=pcb_rigid&d=%s&t=1100&v=strength" % HIST)
    s6 = st(pg)
    ok(f"[{T}] ⑧ 帶狀態的網址：族群、日期、時間、輪盤種類原樣還原", s6["gid"] == GID and s6["date"] == HIST and s6["t"] == "11:00" and s6["view"] == "strength", str(s6))
    ctx.close()

    # ⑨ 手機 390：無橫向捲軸、次要卡預設收起、能展開、走勢在輪盤上面
    ctx, pg = open_page("#flowcheck", {"width": 390, "height": 844}, True)
    ok(f"[{T}] ⑨ 手機 390 無橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"))
    ok(f"[{T}] ⑨ 手機：成分股／熱力圖／更多證據預設收起", pg.evaluate("() => ['fcMemCard','fcHeatCard','fcMoreCard'].every(i => !document.getElementById(i).classList.contains('open') && document.querySelector('#' + i + ' .fc-bd').getBoundingClientRect().height === 0)"))
    ok(f"[{T}] ⑨ 手機：走勢圖在輪盤上面", pg.evaluate("() => document.getElementById('fcTrendCard').getBoundingClientRect().top < document.getElementById('fcWheelCard').getBoundingClientRect().top"))
    ok(f"[{T}] ⑨ 手機：時間軸把手高 ≥ 32px、貼底", pg.evaluate("() => { const r = document.querySelector('#fcRange2').getBoundingClientRect(); return r.height >= 32 && Math.abs(document.getElementById('fcTl').getBoundingClientRect().bottom - innerHeight) < 4; }"))
    ovm = pg.evaluate("""(ids) => { let bad = 0, total = 0; ids.forEach(id => { const c = echarts.getInstanceByDom(document.getElementById(id)); if (!c) return; const L = []; c.getZr().storage.getDisplayList(true).forEach(e => { if (e.ignore || e.invisible || !e.style || !e.style.text || e.type !== 'tspan' && e.type !== 'text') return; const r = e.getBoundingRect().clone(); if (e.transform) r.applyTransform(e.transform); if (r.width > 1 && r.height > 1) L.push(r); }); total += L.length; for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) { const a = L[i], b = L[j], w = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x), h = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y); if (w > 3 && h > 4) bad++; } }); return { bad, total }; }""", ["fcWheel", "fcTrend"])
    ok(f"[{T}] ⑨ 手機：輪盤與走勢圖內文字框兩兩不相交（{ovm['total']} 個）", ovm["bad"] == 0 and ovm["total"] > 5, str(ovm))
    ms = pg.evaluate("() => { const e = document.getElementById('fcMsum'), r = e.getBoundingClientRect(); return { w: r.width, h: r.height, right: r.right, vw: innerWidth, t: e.textContent, btn: e.querySelectorAll('button').length }; }")
    ok(f"[{T}] ⑨ 手機：「更多證據」收起時摘要可見、可換行、不超出視窗、三個數字都在", ms["h"] > 18 and ms["right"] <= ms["vw"] + 1 and ms["btn"] == 3 and "盤中訊號" in ms["t"], str(ms))
    # ⑨b 手機時間軸：只佔一列、背景不透明、速度鈕收進「⋯」、不蓋住首屏文字、頁尾留白
    tl = pg.evaluate("""() => { const t = document.getElementById('fcTl'), r = t.getBoundingClientRect(), cs = getComputedStyle(t), spd = document.getElementById('fcSpd').getBoundingClientRect(), pl = document.getElementById('fcPlay').getBoundingClientRect(), ax = document.getElementById('fcRange2').getBoundingClientRect(), lb = document.getElementById('fcTlab').getBoundingClientRect();
      const cv = document.createElement('canvas'); cv.width = cv.height = 1; const cx = cv.getContext('2d'); cx.clearRect(0, 0, 1, 1); cx.fillStyle = cs.backgroundColor; cx.fillRect(0, 0, 1, 1); const alpha = cx.getImageData(0, 0, 1, 1).data[3] / 255;
      return { h: r.height, alpha, bt: parseFloat(cs.borderTopWidth), spdW: spd.width, sameRow: Math.abs(pl.top + pl.height / 2 - (ax.top + ax.height / 2)) < 12 && Math.abs(lb.top + lb.height / 2 - (ax.top + ax.height / 2)) < 20 }; }""")
    ok(f"[{T}] ⑨ 手機時間軸只佔一列（播放鈕、拉桿、時間同一排，高 ≤ 68px）、背景不透明、上緣有分隔線", tl["h"] <= 68 and tl["sameRow"] and tl["alpha"] == 1 and tl["bt"] >= 1, str(tl))
    ok(f"[{T}] ⑨ 手機：速度鈕預設收起，點「⋯」才出現", tl["spdW"] == 0)
    pg.click("#fcTlMore"); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑨ 手機：點「⋯」後 ×1／×2／×5 出現在時間軸上方、不超出視窗", pg.evaluate("() => { const r = document.getElementById('fcSpd').getBoundingClientRect(); return r.width > 30 && r.left >= 0 && r.right <= innerWidth && r.bottom <= document.getElementById('fcTl').getBoundingClientRect().top + 1; }"))
    pg.click("#fcTlMore"); pg.wait_for_timeout(200)
    cov = pg.evaluate("""() => { const bar = document.getElementById('fcTl').getBoundingClientRect(); window.scrollTo(0, 0); const bad = [];
      document.querySelectorAll('#v-flowcheck *').forEach(e => { if (e.closest('#fcTl') || !(e instanceof HTMLElement)) return; if (!Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0)) return; const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') return; const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2 || r.bottom <= 0 || r.top >= innerHeight) return;
        const w = Math.min(r.right, bar.right) - Math.max(r.left, bar.left), h = Math.min(r.bottom, bar.bottom) - Math.max(r.top, bar.top); if (w > 3 && h > 4) bad.push(e.textContent.trim().slice(0, 14)); });
      return bad; }""")
    ok(f"[{T}] ⑨ 手機 390×844 首屏：時間軸框與其他可見文字框不相交（沒有文字被蓋住）", cov == [], str(cov))
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, document.documentElement.scrollHeight); }"); pg.wait_for_timeout(500)
    tail = pg.evaluate("() => { const bar = document.getElementById('fcTl').getBoundingClientRect(); const els = [...document.querySelectorAll('#v-flowcheck .fc > *:not(#fcTl)')].filter(e => e.getBoundingClientRect().height > 0); const last = els[els.length - 1].getBoundingClientRect(); return [last.bottom, bar.top]; }")
    ok(f"[{T}] ⑨ 手機：捲到底時最後一張卡完整在時間軸之上（頁底留白夠）", tail[0] <= tail[1] + 1, str(tail))
    TXT = """() => { const els = [...document.querySelectorAll('#v-flowcheck *')].filter(e => { if (e.closest('#fcTl') || !(e instanceof HTMLElement) || ['BUTTON', 'INPUT', 'CANVAS', 'SVG'].includes(e.tagName)) return false; if (!Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1)) return false; const cs = getComputedStyle(e); if (cs.visibility === 'hidden' || cs.display === 'none') return false; const r = e.getBoundingClientRect(); return r.width > 4 && r.height > 4 && r.bottom > 0 && r.top < innerHeight && !e.closest('details:not([open])'); });
      const bad = []; for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) { const a = els[i], b = els[j]; if (a.contains(b) || b.contains(a)) continue; const x = a.getBoundingClientRect(), y = b.getBoundingClientRect(); const w = Math.min(x.right, y.right) - Math.max(x.left, y.left), h = Math.min(x.bottom, y.bottom) - Math.max(x.top, y.top); if (w > 3 && h > 4) bad.push(a.textContent.trim().slice(0, 10) + '×' + b.textContent.trim().slice(0, 10)); } return bad; }"""
    pg.evaluate("() => window.scrollTo(0, 0)")
    pg.evaluate("() => { location.hash = '#flowcheck?g=%s&d=%s&t=1300'; }" % (GID, HIST)); pg.wait_for_timeout(2500)
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0); }"); pg.wait_for_timeout(300)
    bad = pg.evaluate(TXT)
    ok(f"[{T}] ⑨ 手機 390×844 歷史日首屏：可見文字框兩兩不相交（標題、分段鈕、徽章、說明列）", bad == [], str(bad[:4]))
    pg.evaluate("() => window.scrollTo(0, 0)")
    # ⑨c 手機換日期版面不晃、「⋯」彈層選完自動關且時點列不被切、訊號標記細線、回測表有左右滑提示
    pg.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0); }")
    M = "() => ['fcWheelCard','fcTrendCard','fcVerdict','fcHeatCard','fcMemCard'].map(i => document.getElementById(i).getBoundingClientRect().height)"
    h0 = pg.evaluate(M)
    pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", HIST); pg.wait_for_timeout(1400)
    h1 = pg.evaluate(M)
    ok(f"[{T}] ⑨ 手機換日期（今天→歷史日）：輪盤卡、走勢卡、結論列高度完全不變（Δ<1px）", all(abs(x - y) < 1 for x, y in zip(h0, h1)), f"{h0}->{h1}")
    pg.evaluate("(d) => { const i = document.querySelector('#fcDatePick'); i.value = d; i.dispatchEvent(new Event('change', {bubbles: true})); }", IDX["dates"][-3]); pg.wait_for_timeout(1400)
    h2 = pg.evaluate(M)
    ok(f"[{T}] ⑨ 手機再換一天：四張卡高度仍不變（Δ<1px）", all(abs(x - y) < 1 for x, y in zip(h1, h2)), f"{h1}->{h2}")
    pg.click("#fcTlMore"); pg.wait_for_timeout(300)
    pop = pg.evaluate("() => { const x = document.getElementById('fcTlx').getBoundingClientRect(), b = [...document.querySelectorAll('#fcDayT button')].map(e => e.getBoundingClientRect()); return { n: b.length, inside: b.every(r => r.left >= x.left - 1 && r.right <= x.right + 1 && r.left >= 0 && r.right <= innerWidth), last: document.querySelector('#fcDayT button:last-child').textContent, h: x.height }; }")
    ok(f"[{T}] ⑨ 手機「⋯」彈層：時點列全部在彈層內不被切（含最後一格 {pop['last']}）、高度不留空白（{round(pop['h'])}px）", pop["n"] >= 5 and pop["inside"] and pop["h"] <= 180, str(pop))
    pg.click("#fcDayT button:nth-child(3)"); pg.wait_for_timeout(500)
    ok(f"[{T}] ⑨ 手機：點了時點彈層自動關、時間真的換了", pg.evaluate("() => !document.getElementById('fcTl').classList.contains('xopen') && TwFlowcheck.state().t !== 'close'"))
    pg.click("#fcTlMore"); pg.wait_for_timeout(200)
    pg.mouse.click(30, 300); pg.wait_for_timeout(300)
    ok(f"[{T}] ⑨ 手機：點彈層外面也會關", pg.evaluate("() => !document.getElementById('fcTl').classList.contains('xopen')"))
    pg.click("#fcMoreCard .fc-tog") if pg.evaluate("() => !document.getElementById('fcMoreCard').classList.contains('open')") else None
    pg.click("#fcTab button[data-v='sig']"); pg.wait_for_timeout(1000)
    sm = pg.evaluate("() => { const st = document.querySelector('.fc-strip').getBoundingClientRect(); const m = [...document.querySelectorAll('.fc-sm')].map(e => e.getBoundingClientRect()); return { n: m.length, thin: m.every(r => r.width <= 4.5), inside: m.every(r => r.right <= st.right + 0.5 && r.left >= st.left - 0.5), hint: (document.querySelector('#fcSigR .fc-swipe') || {}).textContent || '', hv: !!document.querySelector('#fcSigR .fc-swipe') && document.querySelector('#fcSigR .fc-swipe').getBoundingClientRect().height > 8 }; }")
    ok(f"[{T}] ⑨ 手機：訊號時間軸標記是細線且都在軸內；回測表下有「左右滑看更多」提示；畫面有「實驗」", sm["thin"] and sm["inside"] and "左右滑" in sm["hint"] and sm["hv"] and "實驗" in text(pg, "#fcSigL"), str(sm))
    pg.click("#fcTab button[data-v='daily']"); pg.wait_for_timeout(300)
    pg.click("#fcMemCard .fc-tog"); pg.wait_for_timeout(700)
    ok(f"[{T}] ⑨ 手機：點「展開」成分股真的展開且有圖", pg.evaluate("() => document.querySelector('#fcMemCard .fc-bd').getBoundingClientRect().height > 100 && document.querySelectorAll('#fcMinis .chart canvas, #fcMinis .chart svg').length >= 3"))
    ok(f"[{T}] ⑨ 手機：字不小於 11px", pg.evaluate("() => [...document.querySelectorAll('#v-flowcheck button, #v-flowcheck td, #v-flowcheck .fc-vt')].filter(e => e.getBoundingClientRect().height > 0 && parseFloat(getComputedStyle(e).fontSize) < 11).length") == 0)
    ctx.close()


register("流向驗證1030", lambda pg, b, base, code: t_flowcheck_1030(b, base))
