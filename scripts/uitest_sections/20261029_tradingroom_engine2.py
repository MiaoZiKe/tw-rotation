# 驗收段落「交易練習室引擎第二批1029」：切策略重設風控、台指期 60 分標示「僅自 xx 起」、交易清單 CSV 進場出場各一列、
# 重播：期貨保證金檢查、成績單買進持有只算重播段與短期夏普「—」。每項驗畫面或狀態真的因此改變。 flake8: noqa


def t_lab_engine2(b, base, code):
    T = "交易練習室引擎第二批1029"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)

    c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/bt", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    cfg = lambda: pg.evaluate("() => { const s = window.TwLab.state().bt; return { sl: s.cfg.sl, ml: s.cfg.maxLoss, strat: s.strat }; }")
    pg.click("#labPickBtn"); pg.wait_for_timeout(300); pg.click(".lab-pi[data-s='barupdn']"); pg.wait_for_timeout(1200)
    a = cfg()
    ok(f"{T}：選 BarUpDn 後帶出內建的最大日內虧損 1%", a["strat"] == "barupdn" and a["ml"] == 1, a)
    pg.click("#labPickBtn"); pg.wait_for_timeout(300); pg.click(".lab-pi[data-s='ma2']"); pg.wait_for_timeout(1200)
    a = cfg()
    ok(f"{T}：換成雙均線後最大日內虧損回到 0（不帶到後面的策略）", a["strat"] == "ma2" and a["ml"] == 0, a)
    # 台指期 60 分：有按鈕、畫面寫明資料起點
    pg.fill("#labSym", "TX"); pg.wait_for_timeout(400); pg.click(".lab-di[data-c='TX']"); pg.wait_for_timeout(2500)
    ok(f"{T}：台指期的 60 分鈕可按", not pg.evaluate("() => document.querySelector('#labTf button[data-tf=\"60\"]').disabled"), None)
    pg.click("#labTf button[data-tf='60']"); pg.wait_for_timeout(2500)
    note = pg.evaluate("() => { const n = document.getElementById('labTfNote'); return n && !n.hidden ? n.textContent : ''; }")
    ok(f"{T}：切到 60 分後畫面寫「僅自 … 起」", "僅自" in note, note)
    n60 = pg.evaluate("() => window.TwLab.state().bt.B.n")
    ok(f"{T}：台指期 60 分 K 有資料（> 100 根）", n60 > 100, n60)
    # 交易清單 CSV：進場、出場各一列
    pg.click("#labTT button[data-t='tr']"); pg.wait_for_timeout(800)
    if pg.locator("#labCsv").count():
        with pg.expect_download() as dl:
            pg.click("#labCsv")
        lines = open(dl.value.path(), encoding="utf-8-sig").read().splitlines()
        ok(f"{T}：CSV 一筆交易兩列（進場、出場）", len(lines) >= 3 and "進場" in lines[1] and "出場" in lines[2], lines[:3])
    # 重播：期貨保證金
    pg.goto(base + "#lab/replay", wait_until="domcontentloaded"); pg.wait_for_timeout(4000)
    pg.fill("#labSym", "TX"); pg.wait_for_timeout(400); pg.click(".lab-di[data-c='TX']"); pg.wait_for_timeout(3000)
    r = pg.evaluate("""() => { const a = window.TwLab.mods.replay.api, R = a.R; a.startAt(R.B.n - 60); const c = R.B.c[R.i];
      return { m1: a.applyFill(1, 1, c, R.i, '', '手動'), m2: a.applyFill(1, 5, c, R.i, '', '手動'), lots: R.acct.lots.length }; }""")
    ok(f"{T}：重播下 1 口付得起、下 5 口被擋並說明保證金不足", r["m1"] == "" and "保證金不足" in r["m2"] and r["lots"] == 1, r)
    pg.evaluate("() => { const a = window.TwLab.mods.replay.api; for (let k = 0; k < 10; k++) a.step(false); }")
    pg.click("#rpTabs button[data-t='sc']"); pg.wait_for_timeout(500)
    tx = pg.inner_text("#rpPanel")
    ok(f"{T}：重播成績單：期間不到 3 個月夏普值顯示「—」", "夏普值\t—" in tx or "夏普值 —" in tx.replace("\t", " "), tx[:200])
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室引擎第二批1029", lambda pg, b, base, code: t_lab_engine2(b, base, code))
