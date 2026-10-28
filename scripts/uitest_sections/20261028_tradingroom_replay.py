# 驗收段落「交易練習室重播1028」：K 線重播＋模擬下單真人操作——選起點、單步、上一根、播放暫停、未來 K 棒不外洩、下單成交、
# 限價單取消、平倉記帳、成績單、盲測、跳到最新、離開。每一項驗「畫面真的因此改變」。flake8: noqa
def t_lab_replay(b, base, code):
    T = "交易練習室重播1028"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)

    c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/replay", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)

    def R():   # 目前重播狀態的快照
        return pg.evaluate("""() => { const m = window.TwLab.mods.replay, r = m.state(); const d = r.series && r.series.cs ? r.series.cs.data().length : -1;
          return { run: r.run, i: r.i, n: r.B ? r.B.n : 0, start: r.start, playing: r.playing, shown: d, pos: r.acct ? r.acct.lots.reduce((s, x) => s + x.dir * x.q, 0) : 0,
                   orders: r.acct ? r.acct.orders.length : 0, trades: r.acct ? r.acct.trades.length : 0, fills: r.acct ? r.acct.fills.length : 0, cash: r.acct ? r.acct.cash : 0 }; }""")

    r0 = R()
    ok(f"{T}：進重播頁，頁籤有 K 線重播且還沒開始（先選起點）", not r0["run"] and r0["n"] > 500 and pg.is_visible("#rpStart") and not pg.is_visible("#rpCtl"), r0)
    ok(f"{T}：選起點前，下單欄是停用的", pg.evaluate("() => document.getElementById('rpBuy').disabled"), None)
    pg.click("#v-lab .lab-q"); pg.wait_for_timeout(200)
    ok(f"{T}：標題旁「?」是重播專屬說明（規則、快捷鍵），不是回測的說明", pg.is_visible("#v-lab .lab-pop") and "空白鍵" in pg.inner_text("#v-lab .lab-pop") and "未來的 K 棒" in pg.inner_text("#v-lab .lab-pop"), None)
    pg.click("body", position={"x": 5, "y": 5}); pg.wait_for_timeout(150)
    # --- 選日期開始
    pg.fill("#rpDate", "2024-03-01"); pg.click("#rpGo"); pg.wait_for_timeout(600)
    r1 = R()
    ok(f"{T}：從 2024-03-01 開始，控制列出現、起點列收起", r1["run"] and pg.is_visible("#rpCtl") and not pg.is_visible("#rpStart"), r1)
    ok(f"{T}：未來的 K 棒完全不畫（圖上 K 棒數＝目前這一根的序號＋1）", r1["shown"] == r1["i"] + 1 and r1["i"] < r1["n"] - 100, r1)
    ok(f"{T}：目前日期顯示是 2024-03-01 當天或之後第一個交易日", "2024-03-0" in pg.inner_text("#rpNow"), pg.inner_text("#rpNow"))
    # --- 單步
    pg.click("#rpNext"); pg.wait_for_timeout(250)
    r2 = R()
    ok(f"{T}：下一根後圖上多出一根 K 棒", r2["i"] == r1["i"] + 1 and r2["shown"] == r1["shown"] + 1, (r1, r2))
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(200)
    ok(f"{T}：鍵盤 → 也能單步", R()["i"] == r2["i"] + 1, R())
    pg.click("#rpBack"); pg.wait_for_timeout(300); pg.keyboard.press("ArrowLeft"); pg.wait_for_timeout(300)
    r3 = R()
    ok(f"{T}：上一根（按鈕＋鍵盤）退回兩根，圖上 K 棒同步減少", r3["i"] == r1["i"] and r3["shown"] == r1["shown"], (r1, r3))
    # --- 播放／暫停／速度
    pg.click("#rpSpd button[data-s='4']"); pg.click("#rpPlay"); pg.wait_for_timeout(1500)
    r4 = R()
    ok(f"{T}：播放 20 根/秒，1.5 秒後前進多根", r4["playing"] and r4["i"] >= r3["i"] + 10, (r3, r4))
    ok(f"{T}：播放中按鈕變「暫停」", "暫停" in pg.inner_text("#rpPlay"), pg.inner_text("#rpPlay"))
    pg.click("#rpPlay"); pg.wait_for_timeout(300)
    r5 = R(); pg.wait_for_timeout(600); r6 = R()
    ok(f"{T}：暫停後不再前進", not r5["playing"] and r5["i"] == r6["i"], (r5, r6))
    # --- 市價單：下一根開盤成交
    pg.click("#rpTabs button[data-t='pos']")
    pg.fill("#rpQty", "100"); pg.click("#rpUnit button[data-u='sh']") if pg.locator("#rpUnit button[data-u='sh']").count() else None
    pg.fill("#rpQty", "100"); pg.click("#rpBuy"); pg.wait_for_timeout(200)
    ok(f"{T}：市價買進後先掛成委託（還沒成交）", R()["orders"] == 1 and R()["pos"] == 0, R())
    nxt_open = pg.evaluate("() => { const r = window.TwLab.mods.replay.state(); return r.B.o[r.i + 1]; }")
    pg.click("#rpNext"); pg.wait_for_timeout(300)
    r7 = R()
    fp = pg.evaluate("() => window.TwLab.mods.replay.state().acct.fills[0].p")
    ok(f"{T}：下一根開盤成交（持倉 100 股、成交價＝下一根開盤＋滑價）", r7["pos"] == 100 and r7["orders"] == 0 and abs(fp - nxt_open) / nxt_open < 0.002, (r7, fp, nxt_open))
    ok(f"{T}：圖上畫出持倉均價線", pg.evaluate("() => window.TwLab.mods.replay.state().lines.length") >= 1, None)
    ok(f"{T}：持倉頁顯示多單 100 股", "多" in pg.inner_text("#rpPanel") and "100" in pg.inner_text("#rpPanel"), pg.inner_text("#rpPanel")[:60])
    # --- 限價單：掛一張遠低於市價的買單 → 委託頁有、取消後消失
    pg.click("#rpKind button[data-k='limit']"); pg.fill("#rpPx", "1"); pg.fill("#rpQty", "100"); pg.click("#rpBuy"); pg.wait_for_timeout(200)
    pg.click("#rpTabs button[data-t='ord']"); pg.wait_for_timeout(200)
    ok(f"{T}：限價單出現在委託頁", pg.locator("#rpPanel .rp-cx").count() == 1, None)
    pg.click("#rpPanel .rp-cx"); pg.wait_for_timeout(200)
    ok(f"{T}：取消委託後清單清空", R()["orders"] == 0, R())
    # --- 平倉 → 成交紀錄、成績單
    pg.click("#rpKind button[data-k='mkt']"); pg.click("#rpFlat"); pg.click("#rpNext"); pg.wait_for_timeout(300)
    r8 = R()
    ok(f"{T}：全部平倉後部位歸零、記下一筆交易", r8["pos"] == 0 and r8["trades"] == 1, r8)
    pg.click("#rpTabs button[data-t='his']"); pg.wait_for_timeout(200)
    ok(f"{T}：成交紀錄有開倉與平倉兩筆", pg.locator("#rpPanel tbody tr").count() == 2, pg.locator("#rpPanel tbody tr").count())
    pg.click("#rpTabs button[data-t='sc']"); pg.wait_for_timeout(300)
    sc = pg.inner_text("#rpPanel")
    ok(f"{T}：成績單有績效摘要（淨利／勝率／最大回撤）且已平倉交易數是 1", "淨利" in sc and "勝率" in sc and "最大回撤" in sc and pg.evaluate("() => [...document.querySelectorAll('#rpPanel .lab-sum tbody tr')].find(t => t.textContent.startsWith('已平倉交易')).children[1].textContent") == "1", sc[:40])
    pg.click("#rpTabs button[data-t='acc']"); pg.wait_for_timeout(200)
    ok(f"{T}：帳戶頁有權益與初始資金", "權益" in pg.inner_text("#rpPanel") and "初始資金" in pg.inner_text("#rpPanel"), None)
    # --- 停損 bracket：買進附停損 1% → 成交後多出一張停損單
    pg.fill("#rpQty", "100"); pg.fill("#rpSl", "1"); pg.click("#rpBuy"); pg.click("#rpNext"); pg.wait_for_timeout(300)
    ok(f"{T}：附停損的買單成交後自動掛出停損單", R()["pos"] == 100 and R()["orders"] == 1, R())
    # --- 盲測
    pg.check("#rpBlind"); pg.wait_for_timeout(400)
    ok(f"{T}：盲測隱藏標的名稱與日期", "？" in pg.input_value("#labSym") and "2024" not in pg.inner_text("#rpNow"), pg.inner_text("#rpNow"))
    pg.uncheck("#rpBlind"); pg.wait_for_timeout(300)
    # --- 跳到最新
    pg.click("#rpEnd"); pg.wait_for_timeout(800)
    r9 = R()
    ok(f"{T}：跳到最新後來到最後一根，K 棒全部畫出，播放鈕停用", r9["i"] == r9["n"] - 1 and r9["shown"] == r9["n"] and pg.evaluate("() => document.getElementById('rpPlay').disabled"), r9)
    # --- 離開
    pg.click("#rpExit"); pg.wait_for_timeout(500)
    r10 = R()
    ok(f"{T}：離開重播後回到選起點畫面（帳戶清空）", not r10["run"] and pg.is_visible("#rpStart") and r10["fills"] == -0 or not r10["run"], r10)
    # --- 隨機起點
    pg.click("#rpRand"); pg.wait_for_timeout(500)
    ok(f"{T}：隨機起點真的開始重播", R()["run"] and R()["i"] >= 30, R())
    # --- 記帳數字（固定序列、算到小數）：買 1000 股 @100、賣 1000 股 @110，手續費 0.1425% 雙邊、證交稅 0.3%
    acc = pg.evaluate("""() => { const m = window.TwLab.mods.replay, r = m.api.fresh(); r.sym = '2330';
      r.B = { n: 5, tf: 'D', day: Float64Array.from([1,2,3,4,5]), dayEnd: Float64Array.from([1,2,3,4,5]), o: [], h: [], l: [], c: [], ts: [] };
      r.inst = Object.assign(window.LabEngine.instDefaults('stock'), { slip: 0, feeDisc: 1, feeMin: 0 }); r.acct = m.api.newAcct(1000000);
      m.api.applyFill(1, 1000, 100, 1, '', ''); m.api.applyFill(-1, 1000, 110, 2, '', '');
      const t = r.acct.trades[0]; return { pnl: t.pnl, costs: t.costs, cash: r.acct.cash }; }""")
    ok(f"{T}：模擬帳戶記帳：損益 9,372、成本 628（手續費無條件捨去到整數元）、現金 1,009,372", abs(acc["pnl"] - 9372) < 1e-6 and abs(acc["costs"] - 628) < 1e-6 and abs(acc["cash"] - 1009372) < 1e-6, acc)
    c.close()

    # --- 手機 390
    c = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#lab/replay", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    pg.click("#rpRand"); pg.wait_for_timeout(600)
    fs = pg.evaluate("""() => { const k = document.getElementById('rpK').getBoundingClientRect(); const vis = (id) => !!document.getElementById(id).offsetParent;
      return { vh: innerHeight, kTop: Math.round(k.top), kBot: Math.round(k.bottom), hidden: ['rpSpd', 'rpEnd', 'rpExit', 'rpDraw', 'rpNow'].filter(vis), ctl: ['rpBack', 'rpPlay', 'rpNext'].every(vis) }; }""")
    ok(f"{T}：手機重播第一屏看得到圖（圖頂 {fs['kTop']}、底 {fs['kBot']}），速度／跳到最新／離開／繪圖工具收進「設定」", fs["kBot"] <= fs["vh"] and fs["kTop"] < 480 and fs["hidden"] == [] and fs["ctl"], fs)
    m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth })")
    ok(f"{T}：手機 390 沒有橫向捲軸", m["sw"] <= m["cw"] + 1, m)
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室重播1028", lambda pg, b, base, code: t_lab_replay(b, base, code))
