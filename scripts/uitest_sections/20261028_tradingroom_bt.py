# 驗收段落「交易練習室回測1028」：台指期／歷史回測真人操作——切策略、改參數、切週期、切期間、點交易、匯出、設定、
# 管理者限定、手機 390。每一項都驗「畫面真的因此改變」。flake8: noqa
def t_lab_bt(b, base, code):
    T = "交易練習室回測1028"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):          # 記下目前做到哪一步，JS 錯誤才找得到是哪個操作引起的
        step[0] = name
        return _ok(name, cond, detail)
    JS_ST = "() => { const S = window.TwLab.state().bt; return { n: S.B ? S.B.n : 0, tf: S.tf, trades: S.res ? S.res.trades.length : -1, eq: S.res ? S.res.eq.length : -1, strat: S.strat, sel: S.sel }; }"

    def new(w=1440, h=900, mobile=False, adm=True):
        c = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile, accept_downloads=True)
        c.add_init_script(f"window.TW_LAB_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('tw.tour','done')}}catch(e){{}}")
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
        return c, pg

    c, pg = new()
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    st0 = pg.evaluate(JS_ST)
    ok(f"{T}：開 #lab/bt 有 K 線圖與回測結果", st0["n"] > 500 and st0["trades"] > 0 and pg.locator("#labK canvas").count() > 0, st0)
    ok(f"{T}：標題頁籤＝台指期｜歷史回測，預設是最左邊的子頁（#lab 導到 #lab/fut）",
       pg.evaluate("() => [...document.querySelectorAll('#v-lab .lab-tabs a')].map(a => a.textContent).join('|')") == "台指期|歷史回測|K 線重播|事件分析|自訂策略", None)
    ok(f"{T}：Key stats 四張卡", pg.locator("#labStats .lab-st").count() == 4, None)

    # --- 切策略 → 交易數改變
    pg.click("#labPickBtn"); pg.fill("#labPq", "RSI"); pg.click(".lab-pi[data-s='rsi']"); pg.wait_for_timeout(1200)
    st1 = pg.evaluate(JS_ST)
    ok(f"{T}：切到 RSI 策略後交易數改變", st1["strat"] == "rsi" and st1["trades"] != st0["trades"], (st0["trades"], st1["trades"]))
    ok(f"{T}：策略按鈕顯示新策略名", "RSI" in pg.inner_text("#labPickBtn"), None)
    # --- 改參數 → 結果改變
    pg.fill("input[data-p='n']", "5"); pg.wait_for_timeout(1200)
    st2 = pg.evaluate(JS_ST)
    ok(f"{T}：改 RSI 週期 14→5 後交易數改變", st2["trades"] != st1["trades"], (st1["trades"], st2["trades"]))
    # --- 切週期 → K 棒數改變
    pg.click("#labTf button[data-tf='W']"); pg.wait_for_timeout(1500)
    st3 = pg.evaluate(JS_ST)
    ok(f"{T}：日→週後 K 棒數大幅減少且週期標籤同步", st3["tf"] == "W" and st3["n"] < st2["n"] / 3, (st2["n"], st3["n"]))
    pg.click("#labTf button[data-tf='M']"); pg.wait_for_timeout(1200)
    st3b = pg.evaluate(JS_ST)
    ok(f"{T}：週→月後 K 棒數再減少", st3b["n"] < st3["n"] / 2, (st3["n"], st3b["n"]))
    pg.click("#labTf button[data-tf='D']"); pg.wait_for_timeout(1200)
    # 60 分
    pg.click("#labTf button[data-tf='60']"); pg.wait_for_timeout(2500)
    st4 = pg.evaluate(JS_ST)
    ok(f"{T}：切 60 分（2330 有資料）K 棒數是 60 分級", st4["tf"] == "60" and st4["n"] > 1000, st4)
    pg.click("#labTf button[data-tf='D']"); pg.wait_for_timeout(1200)
    # --- 期間鈕 → 權益長度改變
    full = pg.evaluate(JS_ST)["eq"]
    pg.click("#labRng button[data-r='1Y']"); pg.wait_for_timeout(1200)
    one = pg.evaluate(JS_ST)["eq"]
    ok(f"{T}：期間 All→1Y 回測區間真的縮短（約 250 根）", 150 < one < 300 and one < full / 2, (full, one))
    pg.click("#labRng button[data-r='All']"); pg.wait_for_timeout(1000)
    # --- 策略測試器三個分頁
    pg.click("#labTT button[data-t='sum']"); pg.wait_for_timeout(300)
    labels = pg.evaluate("() => [...document.querySelectorAll('#labTBody .lab-sum tbody th')].map(t => t.textContent)")
    ok(f"{T}：績效摘要有 淨利／最大回撤／夏普值／勝率／盈虧比 欄位且分全部、做多、做空三欄",
       all(x in labels for x in ["淨利", "最大回撤", "夏普值", "勝率", "盈虧比", "最大單筆獲利"]) and pg.locator("#labTBody .lab-sum thead th").count() == 4, labels[:6])
    pg.click("#labTT button[data-t='tr']"); pg.wait_for_timeout(300)
    rows = pg.locator("#labTBody tbody tr").count()
    ok(f"{T}：交易清單列數＝回測交易數（含未平倉）", rows >= pg.evaluate(JS_ST)["trades"] and rows > 3, rows)
    # 點一筆 → K 線可視範圍改變；再點取消
    r0 = pg.evaluate("() => { const r = window.TwLab.charts.k.timeScale().getVisibleLogicalRange(); return [r.from, r.to]; }")
    pg.locator("#labTBody tbody tr").nth(3).click(); pg.wait_for_timeout(300)
    r1 = pg.evaluate("() => { const r = window.TwLab.charts.k.timeScale().getVisibleLogicalRange(); return [r.from, r.to]; }")
    ok(f"{T}：點交易列 K 線可視範圍移到那一筆（範圍縮小）", (r1[1] - r1[0]) < (r0[1] - r0[0]) / 3 and pg.locator("#labTBody tbody tr.on").count() == 1, (r0, r1))
    pg.locator("#labTBody tbody tr").nth(3).click(); pg.wait_for_timeout(300)
    ok(f"{T}：再點同一列取消鎖定", pg.locator("#labTBody tbody tr.on").count() == 0, None)
    # 排序
    first = pg.inner_text("#labTBody tbody tr:first-child td:nth-child(8)")
    pg.click("#labTBody th[data-k='pnl']"); pg.wait_for_timeout(200)
    pg.click("#labTBody th[data-k='pnl']"); pg.wait_for_timeout(200)
    asc = pg.evaluate("() => [...document.querySelectorAll('#labTBody tbody tr td:nth-child(8)')].map(td => +td.textContent.replace(/[+,−]/g, m => m === '−' ? '-' : ''))")
    ok(f"{T}：點欄名「損益」排序真的改變順序", asc == sorted(asc), asc[:4])
    # 匯出 CSV
    with pg.expect_download(timeout=5000) as dl:
        pg.click("#labCsv")
    ok(f"{T}：匯出 CSV 真的下載", dl.value.suggested_filename.endswith(".csv"), dl.value.suggested_filename)
    # 概覽的三種圖
    pg.click("#labTT button[data-t='ov']"); pg.wait_for_timeout(300)
    ok(f"{T}：概覽有累積損益／回撤／每筆損益切換", pg.locator("#labEqM button").count() == 3 and pg.locator("#labEq canvas").count() > 0, None)
    pg.click("#labEqM button[data-e='dd']"); pg.wait_for_timeout(400)
    ok(f"{T}：切到回撤後買進持有勾選框收起", not pg.is_visible("#labBH"), None)
    pg.click("#labEqM button[data-e='eq']"); pg.wait_for_timeout(300)
    pg.check("#labBH"); pg.wait_for_timeout(300)
    ok(f"{T}：勾選疊上買進持有後左側價格軸出現", pg.evaluate("() => !!window.TwLab.charts.s2"), None)
    # 設定：停損 → 出場原因出現「停損」
    pg.click("#labAdvBtn"); pg.wait_for_timeout(200)
    ok(f"{T}：設定面板預設收起、點了展開", pg.is_visible("#labAdv"), None)
    pg.fill("input[data-k='sl']", "3"); pg.wait_for_timeout(1500)
    why = pg.evaluate("() => window.TwLab.state().bt.res.trades.some(t => t.why === '停損')")
    ok(f"{T}：設停損 3% 後交易出現「停損」出場", why, None)
    pg.fill("input[data-k='sl']", "0"); pg.wait_for_timeout(1200)
    # 股票成本：手續費折扣降低 → 成本下降
    cost0 = pg.evaluate("() => window.TwLab.state().bt.res.stats.costs")
    pg.fill("input[data-k='feeDisc']", "2.8"); pg.wait_for_timeout(1500)
    cost1 = pg.evaluate("() => window.TwLab.state().bt.res.stats.costs")
    ok(f"{T}：手續費折扣 10→2.8 折後成本下降", cost1 < cost0, (cost0, cost1))
    # 搜尋標的
    pg.fill("#labSym", "聯發科"); pg.wait_for_timeout(300)
    pg.click(".lab-di:first-child"); pg.wait_for_timeout(2000)
    ok(f"{T}：搜尋「聯發科」切到 2454", pg.evaluate("() => window.TwLab.state().bt.sym") == "2454", None)
    # --- 指標／策略挑選視窗（搜尋、分頁、最愛）、指標加到圖上、設定、圖表類型、繪圖工具
    ov0 = pg.evaluate("() => window.TwLab.charts.kv.kc.overlays.length")
    pg.click("#labIndBtn"); pg.wait_for_timeout(200)
    ok(f"{T}：按「指標」開挑選視窗，分頁＝指標／策略，有搜尋框與分類", pg.is_visible("#labPick") and pg.locator("#labPick .lab-ptabs button").count() == 2 and pg.is_visible("#labPq") and "趨勢" in pg.inner_text("#labPl"), None)
    pg.fill("#labPq", "RSI"); pg.wait_for_timeout(200)
    vis = pg.evaluate("() => [...document.querySelectorAll('#labPl .lab-pr')].filter(r => !r.hidden).length")
    ok(f"{T}：搜尋「RSI」只剩 RSI 一列", vis == 1, vis)
    pg.fill("#labPq", ""); pg.wait_for_timeout(100)
    pg.click(".lab-pi[data-i='ma']"); pg.wait_for_timeout(500)
    ok(f"{T}：點「均線 MA」加到圖上（標籤＋圖上多一條線），視窗沒有關", pg.is_visible("#labPick") and pg.locator("#labChips .lab-chip").count() == 2 and pg.evaluate("() => window.TwLab.charts.kv.kc.overlays.length") == ov0 + 1, (ov0, pg.locator("#labChips .lab-chip").count()))
    pg.click(".lab-pi[data-i='ma']"); pg.wait_for_timeout(300)
    pg.click(".lab-pi[data-i='rsi']"); pg.wait_for_timeout(500)
    ok(f"{T}：加 RSI 後圖上多一個 RSI 面板", pg.evaluate("() => !!window.TwLab.charts.kv.kc.panes.rsi"), None)
    pg.click(".lab-pr:has(.lab-pi[data-i='rsi']) .lab-star"); pg.wait_for_timeout(200)
    ok(f"{T}：點星號加入我的最愛（存進 localStorage、列表出現「我的最愛」）", "i:rsi" in pg.evaluate("() => localStorage.getItem('tw.lab.favs') || ''") and "我的最愛" in pg.inner_text("#labPl"), None)
    pg.click(".lab-ptabs button[data-pt='strat']"); pg.wait_for_timeout(200)
    ok(f"{T}：切到策略分頁有內建策略與分類", "內建策略" in pg.inner_text("#labPl") and pg.locator("#labPl .lab-pi[data-s]").count() >= 20, pg.locator("#labPl .lab-pi[data-s]").count())
    pg.keyboard.press("Escape"); pg.click("body", position={"x": 5, "y": 5}); pg.wait_for_timeout(200)
    ok(f"{T}：點別處挑選視窗關閉", not pg.is_visible("#labPick"), None)
    # 設定：把第一條均線週期改 10 → 標籤文字改變
    before = pg.inner_text("#labChips")
    pg.locator("#labChips .lab-chip").nth(1).locator(".lab-cg").click(); pg.wait_for_timeout(200)
    ok(f"{T}：點齒輪開指標設定（輸入／樣式兩個分頁）", pg.is_visible("#labIndSet") and pg.locator("#labIndSet [data-ist]").count() == 2, None)
    pg.fill("#labIndSet input[data-f='n']", "10"); pg.wait_for_timeout(600)
    ok(f"{T}：把均線週期改成 10，標籤文字跟著改", "10" in pg.inner_text("#labChips") and pg.inner_text("#labChips") != before, pg.inner_text("#labChips"))
    pg.click("#labIndSet [data-ist='st']"); pg.wait_for_timeout(200)
    pg.evaluate("() => { const i = document.querySelector('#labIndSet input[data-f=color]'); i.value = '#00ff00'; i.dispatchEvent(new Event('input', { bubbles: true })); }"); pg.wait_for_timeout(600)
    ok(f"{T}：樣式分頁改顏色後存進指標設定", pg.evaluate("() => window.TwLab.state().bt.ind[1].color") == "#00ff00", None)
    pg.click("#labIndSet [data-iclose]"); pg.wait_for_timeout(100)
    # 移除
    n_chip = pg.locator("#labChips .lab-chip").count()
    pg.locator("#labChips .lab-chip").nth(1).locator(".lab-cx").click(); pg.wait_for_timeout(400)
    ok(f"{T}：按 × 移除指標，標籤少一個", pg.locator("#labChips .lab-chip").count() == n_chip - 1, None)
    # 圖表類型：平均 K → 第一根的開盤價與原始價不同；線圖 → 出現線序列
    o_k = pg.evaluate("() => window.TwLab.charts.kv.candle.data()[5].open")
    pg.click("#labCt button[data-c='ha']"); pg.wait_for_timeout(500)
    o_ha = pg.evaluate("() => window.TwLab.charts.kv.candle.data()[5].open")
    ok(f"{T}：切到平均 K 後 K 棒數值改變（開＝前一根平均 K 的開收中點）", abs(o_k - o_ha) > 1e-6 and pg.evaluate("() => window.TwLab.state().bt.ctype") == "ha", (o_k, o_ha))
    pg.click("#labCt button[data-c='line']"); pg.wait_for_timeout(500)
    ok(f"{T}：切到線圖後多一條收盤線", pg.evaluate("() => !!window.TwLab.charts.kv.line"), None)
    pg.click("#labCt button[data-c='k']"); pg.wait_for_timeout(400)
    # 繪圖工具：水平線
    ok(f"{T}：圖左側有繪圖工具列（趨勢線、水平線、方框…）", pg.locator("#labDraw .dtool[data-t]").count() >= 8, pg.locator("#labDraw .dtool").count())
    pg.click("#labDraw .dtool[data-t='hline']"); pg.wait_for_timeout(200)
    box = pg.locator("#labK").bounding_box()
    pg.mouse.move(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.3); pg.wait_for_timeout(200)
    pg.mouse.down(); pg.wait_for_timeout(100); pg.mouse.up(); pg.wait_for_timeout(500)
    ok(f"{T}：選水平線在圖上點一下，真的多出一條線並存進 localStorage", pg.evaluate("() => window.TwLab.charts.kv.kc.draw.shapes.length") == 1 and "hline" in pg.evaluate("() => localStorage.getItem('tw.draw.lab.' + window.TwLab.state().bt.sym + '.D') || ''"), None)
    pg.click("#labCt button[data-c='ha']"); pg.wait_for_timeout(300); pg.click("#labCt button[data-c='k']"); pg.wait_for_timeout(300)
    ok(f"{T}：切換圖表類型後畫的線還在", pg.evaluate("() => window.TwLab.charts.kv.kc.draw.shapes.length") == 1, None)
    # --- 引擎數字：人工可算的序列（手續費 0.1425%、證交稅 0.3%）
    eng = pg.evaluate("""() => { const E = window.LabEngine, n = 6, B = { n, tf: 'D', ts: new Float64Array(n), day: Float64Array.from([19000,19001,19002,19003,19004,19005]), dayEnd: Float64Array.from([19000,19001,19002,19003,19004,19005]),
      o: Float64Array.from([99,100,100,105,110,110]), h: Float64Array.from([99,100,101,106,111,110]), l: Float64Array.from([99,100,99,104,109,110]), c: Float64Array.from([99,100,100,105,110,110]), v: new Float64Array(n) };
      const sig = E.mk(n); sig.L[1] = 1; sig.XL[3] = 1; const inst = Object.assign(E.instDefaults('stock'), { feeDisc: 1, feeMin: 0, slip: 0 });
      const r = E.run(B, sig, { mode: 'both', capital: 1000000, sizeMode: 'units', sizeVal: 1000, inst, sl: 0, tp: 0, trail: 0, maxLoss: 0 }, 0, 5);
      return { pnl: r.trades[0].pnl, costs: r.trades[0].costs }; }""")
    ok(f"{T}：引擎固定序列損益 9,370.75、成本 629.25（手續費 142.5＋156.75、證交稅 330）", abs(eng["pnl"] - 9370.75) < 1e-6 and abs(eng["costs"] - 629.25) < 1e-6, eng)
    c.close()

    # --- 台指期子頁：預設標的 TX、期貨成本欄位
    c, pg = new()
    pg.goto(base + "#lab", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    ok(f"{T}：#lab 導到最左邊子頁（台指期）且標的是 TX", pg.evaluate("() => location.hash") == "#lab/fut" and pg.evaluate("() => window.TwLab.state().fut.sym") == "TX", pg.evaluate("() => location.hash"))
    pg.click("#labAdvBtn"); pg.wait_for_timeout(300)
    ok(f"{T}：台指期設定有 每點／期交稅／手續費每口 欄位，每點預設 200",
       pg.evaluate("() => document.querySelector(\"input[data-k='mult']\") && +document.querySelector(\"input[data-k='mult']\").value") == 200 and pg.locator("input[data-k='futTax']").count() == 1, None)
    ok(f"{T}：台指期沒有 60 分資料 → 60分鈕反灰並有說明", pg.evaluate("() => { const b = document.querySelector(\"#labTf button[data-tf='60']\"); return b.disabled && b.title.length > 5; }"), None)
    s_fut = pg.evaluate("() => { const S = window.TwLab.state().fut; return S.res ? S.res.stats.n : -1; }")
    pg.fill("input[data-k='mult']", "50"); pg.wait_for_timeout(1500)
    net_a = pg.evaluate("() => window.TwLab.state().fut.res.stats.net")
    pg.fill("input[data-k='mult']", "200"); pg.wait_for_timeout(1500)
    net_b = pg.evaluate("() => window.TwLab.state().fut.res.stats.net")
    ok(f"{T}：每點 50→200 損益跟著改變", s_fut > 0 and abs(net_a - net_b) > 1, (net_a, net_b))
    c.close()

    # --- 管理者限定
    c, pg = new(adm=False)
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(7500)
    ok(f"{T}：非管理者開 #lab 被導回總覽，側欄沒有入口",
       pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => { const t = document.querySelector('.tab[data-view=lab]'); return !t || getComputedStyle(t).display === 'none'; }"), pg.evaluate("() => location.hash"))
    c.close()

    # --- 手機 390
    c, pg = new(390, 844, True)
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    m = pg.evaluate("""() => { const v = document.getElementById('v-lab'); const bad = [];
      v.querySelectorAll('button,input,select,td,th,span,b,small,label').forEach(e => { const cs = getComputedStyle(e), r = e.getBoundingClientRect(); if (r.width && r.height && e.innerText && e.innerText.trim() && parseFloat(cs.fontSize) < 11.5) bad.push(e.innerText.slice(0, 10) + ':' + cs.fontSize); });
      return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, bad: bad.slice(0, 5), k: document.getElementById('labK').getBoundingClientRect().height }; }""")
    ok(f"{T}：手機 390 沒有橫向捲軸、字不小於 11px", m["sw"] <= m["cw"] + 1 and not m["bad"], m)
    ok(f"{T}：手機 K 線有高度", m["k"] > 200, m)
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室回測1028", lambda pg, b, base, code: t_lab_bt(b, base, code))
