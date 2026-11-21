# 驗收段落「交易練習室自訂策略1028」：積木式條件編輯器＋迷你腳本真人操作——加條件、改參數、AND／OR、事件條件、儲存、重新整理後還在、
# 匯出匯入、腳本錯誤行號、參數變數、範本、帶到歷史回測。每一項驗「畫面（交易次數）真的因此改變」。 flake8: noqa
import json
import tempfile


def t_lab_custom(b, base, code):
    T = "交易練習室自訂策略1028"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)

    c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/custom", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)

    def n_trades():   # 試跑結果「交易次數」
        pg.wait_for_timeout(1300)
        return pg.evaluate("() => { const t = [...document.querySelectorAll('#cuStats .lab-st')].find(x => x.textContent.includes('交易次數')); return t ? +t.querySelector('b').textContent : -1; }")

    ok(f"{T}：頁籤有 自訂策略，沒有儲存過時列表寫「還沒有儲存的策略」", "還沒有" in pg.inner_text("#cuList") and "自訂策略" in pg.evaluate("() => document.querySelector('#v-lab .lab-tabs').innerText"), None)
    pg.click("#cuNew"); pg.wait_for_timeout(500)
    ok(f"{T}：新增後有 多單進場／多單出場／空單進場／空單出場 四格", pg.locator(".cb-blk").count() == 4 and all(x in pg.inner_text("#cuEd") for x in ["多單進場", "多單出場", "空單進場", "空單出場"]), None)
    pg.wait_for_timeout(800)
    ok(f"{T}：還沒有進場條件時提示先加條件、不會跑出結果", "進場" in pg.inner_text("#cuStats") and "條件" in pg.inner_text("#cuStats"), pg.inner_text("#cuStats")[:30])
    # 加條件：只有進場沒有出場 → 只會進一次場一路持有（未平倉），要加出場條件才有交易
    pg.click(".cb-blk[data-b='le'] [data-add='cmp']")
    n0 = n_trades()
    ok(f"{T}：只加進場條件時一路持有（交易 0 筆、顯示另有未平倉）", n0 == 0 and "未平倉" in pg.inner_text("#cuStats"), pg.inner_text("#cuStats")[-30:])
    pg.click(".cb-blk[data-b='lx'] [data-add='cmp']")
    pg.select_option(".cb-blk[data-b='lx'] .cb-row select[data-f='op']", "dn")
    n1 = n_trades()
    ok(f"{T}：再加出場條件（5 日均線下穿 20 日均線）後試跑出現多筆交易", n1 > 5, n1)
    # 改參數：進場的長均線週期 20 → 60
    pg.fill(".cb-blk[data-b='le'] .cb-row input[data-f='b.n']", "60")
    n2 = n_trades()
    ok(f"{T}：把進場的長均線週期 20 改成 60 後交易次數改變", n2 != n1, (n1, n2))
    # 第二個條件（RSI < 30）AND → 變少；改 OR → 變多
    pg.click(".cb-blk[data-b='le'] [data-add='cmp']")
    r2 = pg.locator(".cb-blk[data-b='le'] .cb-row").nth(1)
    r2.locator("select[data-f='a.t']").select_option("rsi"); r2.locator("select[data-f='op']").select_option("lt"); r2.locator("select[data-f='b.t']").select_option("num")
    pg.locator(".cb-blk[data-b='le'] .cb-row").nth(1).locator("input[data-f='b.v']").fill("60")
    n3 = n_trades()
    ok(f"{T}：加「RSI < 60」（全部成立）後交易變少", 0 <= n3 < n2, (n2, n3))
    pg.click(".cb-blk[data-b='le'] .cb-join button[data-j='or']")
    n4 = n_trades()
    ok(f"{T}：改成「任一成立」後交易變多", n4 > n3, (n3, n4))
    pg.click(".cb-blk[data-b='le'] .cb-join button[data-j='and']"); n_trades()
    # 移除第二個條件
    pg.locator(".cb-blk[data-b='le'] .cb-row").nth(1).locator("[data-del]").click()
    n5 = n_trades()
    ok(f"{T}：刪掉第二個條件後回到 {n2} 筆", n5 == n2 and pg.locator(".cb-blk[data-b='le'] .cb-row").count() == 1, (n2, n5))
    n6 = n5
    # 事件條件（不在 FOMC 窗內）
    pg.click(".cb-blk[data-b='le'] [data-add='event']")
    n7 = n_trades()
    ok(f"{T}：加「不在 FOMC 前 3 後 1 日」事件條件後交易變少", n7 < n6, (n6, n7))
    # 風控：停損 → 結果改變
    net7 = pg.evaluate("() => window.TwLab.mods.custom.state().res.stats.net")
    pg.fill("input[data-r='sl']", "3")
    n8 = n_trades()
    ok(f"{T}：設停損 3% 後出現「停損」出場、損益改變", pg.evaluate("() => window.TwLab.mods.custom.state().res.trades.some(t => t.why === '停損')") and pg.evaluate("() => window.TwLab.mods.custom.state().res.stats.net") != net7, (n7, n8))
    # 儲存：改名＋儲存；重新整理後還在
    pg.fill("#cuName", "測試均線策略")
    ok(f"{T}：改名後（尚未儲存）儲存鈕外框變琥珀色（用顏色不用文字）", pg.evaluate("() => document.getElementById('cuSave').classList.contains('dirty')"), None)
    pg.click("#cuSave"); pg.wait_for_timeout(300)
    ok(f"{T}：儲存後外框恢復、列表出現這個策略", not pg.evaluate("() => document.getElementById('cuSave').classList.contains('dirty')") and "測試均線策略" in pg.inner_text("#cuList"), None)
    stored = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.lab.rules') || '[]')")
    ok(f"{T}：localStorage 真的寫進去（含事件條件與停損）", len(stored) == 1 and stored[0]["risk"]["sl"] == 3 and any(r.get("kind") == "event" for r in stored[0]["blocks"]["le"]["rows"]), stored[:1])
    pg.reload(wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    ok(f"{T}：重新整理後策略還在、自動帶出編輯器與同樣的交易次數", "測試均線策略" in pg.inner_text("#cuList") and n_trades() == n8, None)
    # 範本
    pg.select_option("#cuTpl", index=1); pg.wait_for_timeout(600)
    ok(f"{T}：選範本「均線上穿且 RSI 不過熱」後多單進場有兩個條件", pg.locator(".cb-blk[data-b='le'] .cb-row").count() == 2, None)
    n_tpl = n_trades()
    ok(f"{T}：範本試跑有結果", n_tpl > 0, n_tpl)
    # 腳本分頁
    pg.click("#cuTab button[data-t='script']"); pg.wait_for_timeout(400)
    sc = pg.input_value("#cuScript")
    ok(f"{T}：切到腳本頁，積木自動轉成腳本文字（含 若…則 進場）", "進場" in sc and "crossover" in sc, sc[:80])
    n_s = n_trades()
    ok(f"{T}：腳本版試跑交易次數與積木版相同", n_s == n_tpl, (n_tpl, n_s))
    pg.fill("#cuScript", '若 close > 則 進場("多")'); pg.wait_for_timeout(900)
    ok(f"{T}：腳本語法錯誤顯示「第 1 行」錯誤訊息", "第 1 行" in pg.inner_text("#cuErrs"), pg.inner_text("#cuErrs"))
    pg.fill("#cuScript", '快 = 參數("快線", 5)\n慢 = 參數("慢線", 20)\n若 上穿(均線(收盤,快), 均線(收盤,慢)) 則 進場("多")\n若 下穿(均線(收盤,快), 均線(收盤,慢)) 則 平倉("多")')
    na = n_trades()
    ok(f"{T}：腳本用「參數」宣告變數後，下方出現 快線／慢線 輸入框", pg.locator("#cuPs input[data-pv]").count() == 2 and na > 5, na)
    pg.fill("#cuPs input[data-pv='慢']", "60")
    nb = n_trades()
    ok(f"{T}：改腳本參數「慢線」20→60 後交易次數改變", nb != na, (na, nb))
    pg.fill("#cuScript", 'if ta.crossover(ta.sma(close,5), ta.sma(close,20)) then strategy.entry("L", strategy.long)'); pg.wait_for_timeout(900)
    ok(f"{T}：英文別名（ta.crossover、strategy.entry）也能編譯", pg.inner_text("#cuErrs").strip() == "" and (n_trades() >= 0) and "交易次數" in pg.inner_text("#cuStats"), pg.inner_text("#cuErrs"))
    # 匯出
    with pg.expect_download(timeout=5000) as dl:
        pg.click("#cuExp")
    path = dl.value.path(); data = json.load(open(path, encoding="utf-8"))
    ok(f"{T}：匯出 JSON 內含 v:1 與已儲存的策略", data.get("v") == 1 and len(data["rules"]) == 1 and data["rules"][0]["name"] == "測試均線策略", data.get("v"))
    # 匯入（含一筆有問題的資料也不會壞）
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"v": 1, "rules": [{"name": "匯入的策略", "mode": "blocks", "dir": "long", "blocks": {"le": {"join": "and", "rows": [{"kind": "cmp", "op": "gt", "a": {"t": "close"}, "b": {"t": "sma", "n": 20}}]}}, "risk": {"sl": 5}}, {"foo": 1}]}, f); f.close()
    pg.set_input_files("#cuImp", f.name); pg.wait_for_timeout(700)
    ok(f"{T}：匯入後列表多出「匯入的策略」（壞資料被略過）", "匯入的策略" in pg.inner_text("#cuList") and pg.locator(".cu-item").count() == 2, pg.inner_text("#cuList"))
    # 帶到歷史回測
    pg.click("#cuGo"); pg.wait_for_timeout(5000)
    ok(f"{T}：按「在歷史回測看完整結果」切到歷史回測並選用這個自訂策略（只做多）", pg.evaluate("() => location.hash") == "#lab/bt" and "匯入的策略" in pg.inner_text("#labPickBtn") and pg.evaluate("() => { const r = window.TwLab.state().bt.res; return r.trades.length + (r.opens || []).length; }") > 0 and pg.evaluate("() => window.TwLab.state().bt.mode") == "long", pg.evaluate("() => { const S = window.TwLab.state().bt; return [location.hash, S.strat, S.mode, S.res ? S.res.trades.length : -1]; }"))
    pg.click("#labPickBtn"); pg.wait_for_timeout(200)
    ok(f"{T}：策略挑選視窗有「我的策略」分類", "我的策略" in pg.inner_text("#labPl") and "測試均線策略" in pg.inner_text("#labPl"), None)
    # 刪除
    pg.goto(base + "#lab/custom", wait_until="domcontentloaded"); pg.wait_for_timeout(4000)
    pg.click("#cuDel"); pg.wait_for_timeout(300)
    ok(f"{T}：刪除後列表少一筆", pg.locator(".cu-item").count() == 1, pg.locator(".cu-item").count())
    c.close()

    # 手機
    c = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#lab/custom", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    ok(f"{T}：手機先看到編輯器，我的策略清單與範本收在「設定」面板（預設收起）", not pg.evaluate("() => !!document.querySelector('.cu-side').offsetParent") and pg.evaluate("() => !!document.getElementById('labMx').offsetParent"), None)
    pg.click("#labMx"); pg.wait_for_timeout(300)
    ok(f"{T}：點「我的策略・範本」後清單出現", pg.evaluate("() => !!document.querySelector('.cu-side').offsetParent"), None)
    pg.click("#cuNew"); pg.wait_for_timeout(400)
    ok(f"{T}：手機按「新增」後清單面板自動收起、編輯器就在眼前", not pg.evaluate("() => !!document.querySelector('.cu-side').offsetParent"), None)
    pg.click(".cb-blk[data-b='le'] [data-add='cmp']"); pg.wait_for_timeout(800)
    m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth })")
    ok(f"{T}：手機 390 沒有橫向捲軸", m["sw"] <= m["cw"] + 1, m)
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室自訂策略1028", lambda pg, b, base, code: t_lab_custom(b, base, code))
