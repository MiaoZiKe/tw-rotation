# 驗收段落「交易練習室事件1028」：事件分析頁（統計表、平均走勢圖、逐次明細）＋事件濾網（對照回測、歷史回測設定面板）真人操作。
# 驗：N 日切換後欄位與路徑長度真的變、勾選事件類型後列數真的變、加上事件條件後交易減少、事件統計數字（人工可算序列）。 flake8: noqa
def t_lab_events(b, base, code):
    T = "交易練習室事件1028"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/evt", wait_until="domcontentloaded"); pg.wait_for_timeout(5000)

    rows0 = pg.locator("#evStats tbody tr").count()
    ok(f"{T}：事件分析頁有統計表（每類事件一列）", rows0 >= 5, rows0)
    ok(f"{T}：平均走勢圖有畫出（echarts）", pg.evaluate("() => { const el = document.getElementById('evPath'); const c = el && window.echarts && echarts.getInstanceByDom(el); return !!c && c.getOption().series.length >= 5; }"), None)
    len10 = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('evPath')).getOption().series[0].data.length")
    ok(f"{T}：±10 日走勢有 21 個點", len10 == 21, len10)
    pg.click("#evN button[data-n='20']"); pg.wait_for_timeout(1200)
    len20 = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('evPath')).getOption().series[0].data.length")
    ok(f"{T}：切 ±20 日後走勢圖變 41 個點、表頭欄名跟著改", len20 == 41 and "後 20 日" in pg.inner_text("#evStats thead"), (len20, pg.inner_text("#evStats thead")[:30]))
    # 勾選事件類型：只留 FOMC
    pg.click("#evTypes .lab-msb"); pg.wait_for_timeout(200)
    pg.click("#evTypes .lab-mpa button[data-a='none']"); pg.wait_for_timeout(1000)
    ok(f"{T}：全不選事件後顯示「沒有符合的事件」", pg.locator("#evStats tbody tr").count() == 0 and "沒有符合" in pg.inner_text("#evStats"), None)
    pg.click("#evTypes input[data-k='fomc']"); pg.wait_for_timeout(1200)
    ok(f"{T}：只勾 FOMC 後統計表只剩一列、下拉按鈕寫「1 項」", pg.locator("#evStats tbody tr").count() == 1 and "1 項" in pg.inner_text("#evTypes .lab-msb"), pg.inner_text("#evTypes .lab-msb"))
    n_fomc = pg.evaluate("() => +document.querySelector('#evStats tbody tr td:nth-child(2)').textContent")
    ok(f"{T}：FOMC 事件數合理（2013 起每年約 8 次，加權指數 2000 起的資料只含 2013 之後）", 100 <= n_fomc <= 125, n_fomc)
    pg.click("#evTypes .lab-mpa button[data-a='all']"); pg.wait_for_timeout(1200)
    ok(f"{T}：全選後統計表恢復多列", pg.locator("#evStats tbody tr").count() == rows0, pg.locator("#evStats tbody tr").count())
    pg.click("body", position={"x": 5, "y": 5}); pg.wait_for_timeout(200)
    # 點列鎖定 → 明細標題改變
    h0 = pg.inner_text("#evDetH")
    pg.locator("#evStats tbody tr").nth(2).click(); pg.wait_for_timeout(400)
    h1 = pg.inner_text("#evDetH")
    ok(f"{T}：點統計列鎖定那一類，明細標題改變且寫著可再點取消", h1 != h0 and "取消" in h1, (h0, h1))
    pg.locator("#evStats tbody tr").nth(2).click(); pg.wait_for_timeout(300)
    ok(f"{T}：再點同一列取消鎖定", "取消" not in pg.inner_text("#evDetH"), pg.inner_text("#evDetH"))
    # 換標的 → 事件數改變（台指期資料到 2000 年，加權也一樣；換成只有 2016 起的個股事件數變少）
    cnt_idx = pg.evaluate("() => [...document.querySelectorAll('#evStats tbody tr td:nth-child(2)')].reduce((s, t) => s + +t.textContent, 0)")
    pg.fill("#labSym", "2330"); pg.wait_for_timeout(300); pg.click(".lab-di:first-child"); pg.wait_for_timeout(2500)
    cnt_stk = pg.evaluate("() => [...document.querySelectorAll('#evStats tbody tr td:nth-child(2)')].reduce((s, t) => s + +t.textContent, 0)")
    ok(f"{T}：換成 2330（資料 2016 起）事件總數變少", 0 < cnt_stk < cnt_idx, (cnt_idx, cnt_stk))
    # --- 事件濾網對照
    pg.fill("#labSym", "加權"); pg.wait_for_timeout(300); pg.click(".lab-di:first-child"); pg.wait_for_timeout(2500)
    pg.wait_for_timeout(800)
    cmp_rows = pg.evaluate("() => [...document.querySelectorAll('#evFRes .lab-sum tbody tr')].map(tr => [tr.children[0].textContent, tr.children[1].textContent, tr.children[2].textContent])")
    n = {r[0]: r for r in cmp_rows}
    ok(f"{T}：濾網對照表有 交易次數／淨利／報酬率／最大回撤／勝率／獲利因子", all(k in n for k in ["交易次數", "淨利", "報酬率", "最大回撤", "勝率", "獲利因子"]), cmp_rows[:2])
    base_n, evt_n = int(n["交易次數"][1].replace(",", "")), int(n["交易次數"][2].replace(",", ""))
    ok(f"{T}：事件窗內不進場（FOMC 前 3 後 1）後交易次數減少", evt_n < base_n, (base_n, evt_n))
    ok(f"{T}：疊圖有兩條線", pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('evEq')).getOption().series.length") == 2, None)
    pg.click("#evFMode button[data-m='only']"); pg.wait_for_timeout(1500)
    n2 = {r[0]: r for r in pg.evaluate("() => [...document.querySelectorAll('#evFRes .lab-sum tbody tr')].map(tr => [tr.children[0].textContent, tr.children[1].textContent, tr.children[2].textContent])")}
    only_n = int(n2["交易次數"][2].replace(",", ""))
    ok(f"{T}：改成「只在事件窗內進場」交易次數與「不進場」不同且少於原本", only_n != evt_n and only_n < base_n, (base_n, evt_n, only_n))
    pg.fill("#evFB", "10"); pg.wait_for_timeout(1500)
    n3 = {r[0]: r for r in pg.evaluate("() => [...document.querySelectorAll('#evFRes .lab-sum tbody tr')].map(tr => [tr.children[0].textContent, tr.children[1].textContent, tr.children[2].textContent])")}
    ok(f"{T}：把事件前天數改成 10 結果跟著改變", n3["交易次數"][2] != n2["交易次數"][2], (n2["交易次數"], n3["交易次數"]))

    # --- 歷史回測設定面板的事件濾網
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    t0 = pg.evaluate("() => window.TwLab.state().bt.res.trades.length")
    pg.click("#labAdvBtn"); pg.wait_for_timeout(300)
    ok(f"{T}：回測設定面板有事件濾網（預設沒勾）", pg.locator("#labAdv input[data-e='on']").count() == 1 and not pg.is_checked("#labAdv input[data-e='on']"), None)
    pg.check("#labAdv input[data-e='on']"); pg.wait_for_timeout(1500)
    t1 = pg.evaluate("() => window.TwLab.state().bt.res.trades.length")
    ok(f"{T}：勾選事件濾網（FOMC 前 3 後 1 不進場）後 2330 回測交易次數減少", t1 < t0, (t0, t1))
    pg.check("#labAdv input[data-e='flat']"); pg.wait_for_timeout(1500)
    why = pg.evaluate("() => window.TwLab.state().bt.res.trades.some(t => t.why === '事件出場')")
    ok(f"{T}：勾「進入事件窗就平倉」後出現「事件出場」", why, None)

    # --- 事件統計數字：人工可算的序列（事件日 2024-01-04 前一日收盤 100，事件日收 102、次日收 103、再次日收 105）
    r = pg.evaluate("""() => { const E = window.LabEngine, n = 6, d0 = E.strToDay('2024-01-01');
      const D = { n, tf: 'D', ts: new Float64Array(n), day: Float64Array.from([0,1,2,3,4,5].map(i => d0 + i)), dayEnd: Float64Array.from([0,1,2,3,4,5].map(i => d0 + i)),
        o: new Float64Array(n), h: new Float64Array(n), l: new Float64Array(n), c: Float64Array.from([98, 99, 100, 102, 103, 105]), v: new Float64Array(n) };
      const res = E.eventStudy(D, [{ d: '2024-01-04', t: 'x', name: 't', lag: 0 }], 2); const g = res.x;
      return { n: g.n, pre: g.pre.avg, day0: g.day0.avg, post1: g.post1.avg, postN: g.postN.avg, path: g.path }; }""")
    ok(f"{T}：事件統計：前 2 日 +2.0408%（98→100）、反應日 +2%、後 1 日 +3%、後 2 日 +5%",
       r["n"] == 1 and abs(r["pre"] - 2.0408163265) < 1e-6 and abs(r["day0"] - 2) < 1e-9 and abs(r["post1"] - 3) < 1e-9 and abs(r["postN"] - 5) < 1e-9 and abs(r["path"][1]) < 1e-9 and abs(r["path"][2] - 2) < 1e-9, r)   # 走勢路徑：事件前一日＝0、事件日＝+2%
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室事件1028", lambda pg, b, base, code: t_lab_events(b, base, code))
