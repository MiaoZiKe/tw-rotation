# 驗收段落「交易練習室標準策略1029」：自訂策略頁的「標準策略」10 組——逐組真的選、真的載入、真的試跑，
# 並驗「網頁試跑的交易次數＝結果檔（由 scripts/gen_standard_strategies.js 產生）的交易次數」（同一支引擎，不一致就是有一邊壞了）；
# 積木與腳本兩種寫法切換後交易次數不變；週期鈕、「?」說明、手機寬度。 flake8: noqa
import json


def t_lab_standard(b, base, code):
    T = "交易練習室標準策略1029"
    errs: list[str] = []
    step = [""]
    _ok = globals()["ok"]

    def ok(name, cond, detail=None):
        step[0] = name
        return _ok(name, cond, detail)

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_LAB_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e) + " @ 上一步＝" + step[0]))
    pg.goto(base + "#lab/custom", wait_until="domcontentloaded"); pg.wait_for_timeout(4500)
    res = pg.evaluate("async () => { const r = await fetch('lab/standard_results.json'); return r.ok ? await r.json() : null; }")
    ok(f"{T}：結果檔 standard_results.json 讀得到、12 組齊全", bool(res) and len(res["strategies"]) == 12, None)
    opts = pg.evaluate("() => [...document.querySelectorAll('#cuStdSel option')].filter(o => o.value).map(o => o.value)")
    ok(f"{T}：下拉有 12 組標準策略", len(opts) == 12, opts)

    def n_trades():
        pg.wait_for_timeout(1500)
        return pg.evaluate("() => { const t = [...document.querySelectorAll('#cuStats .lab-st')].find(x => x.textContent.includes('交易次數')); return t ? +t.querySelector('b').textContent : -1; }")

    for sid in opts:
        st = res["strategies"][sid]
        h = next(r for r in st["runs"] if r["sym"] == st["headline"]["sym"] and r["tf"] == st["headline"]["tf"])
        pg.select_option("#cuStdSel", sid)
        pg.wait_for_timeout(1200)
        nm = pg.inner_text("#cuStd .cu-stdh > b")
        ok(f"{T}：{sid} 載入後出現成績卡（{nm}）且有 6 格數字", pg.locator("#cuStd .cu-stdst .lab-st").count() == 6, nm)
        n = n_trades()
        ok(f"{T}：{sid} 網頁試跑交易 {n} 筆＝結果檔 {h['n']} 筆", n == h["n"], (n, h["n"]))
        ok(f"{T}：{sid} 編輯器是腳本模式、有內容", pg.evaluate("() => (document.getElementById('cuScript')||{}).value ? document.getElementById('cuScript').value.length > 30 : false"), None)
    # 積木與腳本等價：第 1 組切到積木，交易次數不變
    pg.select_option("#cuStdSel", "std_ma"); n0 = n_trades()
    pg.click("#cuTab button[data-t='blocks']"); n1 = n_trades()
    ok(f"{T}：雙均線 切到積木後交易次數不變（{n0}→{n1}）", n0 == n1 and pg.locator(".cb-blk .cb-row").count() >= 2, (n0, n1))
    # 週期鈕：週 K 的表格列數與日 K 不同、內容改變
    t0 = pg.inner_text("#cuStd .cu-stdtb")
    pg.click("#cuStdTf button[data-k='W']"); pg.wait_for_timeout(500)
    t1 = pg.inner_text("#cuStd .cu-stdtb")
    ok(f"{T}：切到週 K 後成績表內容改變", t0 != t1 and pg.locator("#cuStdTf button.on").inner_text() == "週 K", None)
    # 「?」說明有規則與失效條件
    pg.click("#cuStd .lab-q"); pg.wait_for_timeout(300)
    tx = pg.inner_text("#cuStd .lab-pop")
    ok(f"{T}：「?」寫了進場、出場、停損、出處、失效條件與免責", all(k in tx for k in ["進場", "出場", "停損", "出處", "什麼時候會失效", "免責"]), tx[:40])
    # 沒有說明卡常駐文字（說明只在「?」）—— 「?」的浮層就長在標題列裡、上一步剛打開，比對前先把浮層排除（1030 合併時修）
    ok(f"{T}：卡片上沒有整段規則原文（說明都收在「?」）", "下一個交易日開盤買進" not in pg.evaluate("() => { const h = document.querySelector('#cuStd .cu-stdh').cloneNode(true); h.querySelectorAll('.lab-pop').forEach(x => x.remove()); return h.innerText; }") and "出處" not in pg.inner_text("#cuStd .cu-stdtb"), None)
    # 手機寬度
    pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(600)
    m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth })")
    ok(f"{T}：手機 390 沒有整頁橫向捲軸", m["sw"] <= m["cw"] + 1, m)
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:3])


register("交易練習室標準策略1029", lambda pg, b, base, code: t_lab_standard(b, base, code))
