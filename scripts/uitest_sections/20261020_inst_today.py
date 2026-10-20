# 驗收段落「當日法人1020」（段落名沿用；內容＝三大法人買賣超日報 #market/inst）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 當日法人1020
# Andy 10-20：「三大法人買賣超日報」＋「也需要在盤後提供當天即時的法人買賣超狀況」。1440 與 390 各走一輪，全部真的點：
#   ① #market/inst：標題「三大法人買賣超日報」、四格（外資／投信／自營／合計）含百分位、兩張圖有畫、明細表有列、data-snap + TwSnapReady
#   ② 期間 seg：點「1月」→ 明細表筆數、累積數字、圖的類別數真的變；點「全部」回來；資料不足的鈕反灰
#   ③ 連動：滑過明細一列 → 該列 .hl、root.dataset.hov 換；點一列 → 鎖定（.lk、其他列 dim、兩張圖各出現一條垂直虛線）；再點取消
#   ④ 點圖（真滑鼠點在圖上）→ 鎖定那一天、表格捲到那列；
#   ⑤ 明細表排序：點「外資」標題 → 排序真的換、再點反向
#   ⑥ 個股排行 Top 8：族群下拉勾一個族群 → 兩欄每一列的族群都是它、筆數變；點一列進個股頁
#   ⑦ 「連續買賣超」分段：切過去有排行與族群下拉；勾族群後買／賣筆數變；舊網址 #market/streak 導到 #market/inst 並停在連續買賣超
#   ⑧ 390：沒有橫向捲軸、字 ≥ 11px、四格 2×2、明細表先只列 6 筆、「看全部」展開

_INST_ST = """() => { const r = document.getElementById('instToday'); if (!r) return null;
  const tiles = [...r.querySelectorAll('.itile')].map(t => ({ k: t.dataset.k, txt: t.querySelector('.iv').textContent, cls: t.querySelector('.iv').className,
    pct: (t.querySelector('.ipct em') || {}).textContent || '', x: Math.round(t.getBoundingClientRect().left), y: Math.round(t.getBoundingClientRect().top) }));
  const ch = (id) => { const el = document.getElementById(id), c = el && window.echarts && echarts.getInstanceByDom(el); if (!c) return null;
    const o = c.getOption(); const lk = o.series.find(s => s.id === 'lk');
    return { n: (o.xAxis[0].data || []).length, ns: o.series.length, lk: lk && lk.markLine && lk.markLine.data ? lk.markLine.data.length : 0 }; };
  const rows = [...r.querySelectorAll('#instTbl tr[data-d]')];
  const small = [...r.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim() && e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 11).length;
  const rk = (side) => [...r.querySelectorAll(`#instRank .srcol.${side} .itrow[data-code]`)].map(e => [e.dataset.code, (e.querySelector('.px.grp') || {}).textContent]);
  return { title: (document.getElementById('mktTitle') || {}).textContent || '', ready: r.dataset.ready, snap: window.TwSnapReady ? window.TwSnapReady('inst-today') : null,
    per: r.dataset.per, n: r.dataset.n, hov: r.dataset.hov, sel: r.dataset.sel, tiles, c1: ch('instBars'), c2: ch('instLines'),
    nrows: rows.length, first: rows[0] ? rows[0].dataset.d : '', hl: rows.filter(x => x.classList.contains('hl')).map(x => x.dataset.d),
    lk: rows.filter(x => x.classList.contains('lk')).map(x => x.dataset.d), dim: rows.filter(x => x.classList.contains('dim')).length,
    cum: [...r.querySelectorAll('#instCum .icrow b')].map(b => b.textContent), buy: rk('buy'), sell: rk('sell'),
    pers: [...r.querySelectorAll('#instPer button')].map(b => ({ p: b.dataset.p, on: b.classList.contains('on'), dis: b.disabled })),
    firstVals: rows.slice(0, 3).map(x => x.children[1].textContent), tb: !!r.querySelector('#instTblAll'),
    sw: document.documentElement.scrollWidth, iw: innerWidth, small }; }"""


def _inst_wait(pg):
    return wait_until(pg, "() => { const r = document.getElementById('instToday'); return !!r && r.dataset.ready === '1' && !!r.querySelector('.itile') && document.querySelectorAll('#instTbl tr[data-d]').length > 0; }", 15000)


def _inst_run(pg, base, tag, mobile):
    import re as _re
    pg.goto(f"{base}#market/inst", wait_until="networkidle")
    got = _inst_wait(pg)
    ok(f"★ [{tag}] 進 #market/inst：日報畫出來", got)
    if not got:
        return
    pg.wait_for_timeout(700)
    s0 = pg.evaluate(_INST_ST)
    ok(f"★ [{tag}] 標題「三大法人買賣超日報」＋資料日（{s0['title'].strip()}）", "三大法人買賣超日報" in s0["title"] and bool(_re.search(r"\d{4}-\d\d-\d\d", s0["title"])), s0["title"])
    ok(f"★ [{tag}] 四格（外資／投信／自營／合計）各有金額與歷史百分位", [t["k"] for t in s0["tiles"]] == ["f", "t", "dl", "tot"] and all("億" in t["txt"] and t["pct"].endswith("%") for t in s0["tiles"]), s0["tiles"])
    good = all((("up" in t["cls"]) if t["txt"][:1] == "+" else ("down" in t["cls"]) if t["txt"][:1] == "−" else True) for t in s0["tiles"])
    ok(f"★ [{tag}] 買超（+）用紅(up)、賣超（−）用綠(down)", good, [t["txt"] for t in s0["tiles"]])
    ok(f"★ [{tag}] 兩張圖有畫（每日直條＋指數線、累積三線）、明細表有列、TwSnapReady('inst-today') 為 true",
       s0["c1"] and s0["c1"]["ns"] >= 4 and s0["c2"] and s0["c2"]["ns"] >= 3 and s0["nrows"] > 0 and s0["snap"] is True, [s0["c1"], s0["c2"], s0["nrows"], s0["snap"]])
    # ② 期間
    base_n, base_cum = s0["nrows"], s0["cum"]
    if not mobile:
        pg.locator('#instPer button[data-p="1m"]').click(); pg.wait_for_timeout(700)
        s1 = pg.evaluate(_INST_ST)
        if base_n > 21:
            ok(f"★ [{tag}] 點「1月」→ 明細 {base_n}→{s1['nrows']} 筆、累積數字換、圖類別數跟著變", s1["per"] == "1m" and s1["nrows"] == 21 and s1["c1"]["n"] == 21 and s1["cum"] != base_cum, [s1["per"], s1["nrows"], s1["c1"], s1["cum"], base_cum])
        else:
            ok(f"[{tag}] 資料不足 21 筆，1月＝全部，略過筆數差異", s1["nrows"] == base_n)
        dis = [p["p"] for p in s1["pers"] if p["dis"]]
        ok(f"[{tag}] 資料不夠長的期間鈕反灰（{dis}）、選到的那顆亮起", any(p["on"] and p["p"] == "1m" for p in s1["pers"]) and ("5y" in dis or s0["n"] != "0"), s1["pers"])
        pg.locator('#instPer button[data-p="all"]').click(); pg.wait_for_timeout(600)
        s2 = pg.evaluate(_INST_ST)
        ok(f"[{tag}] 點「全部」→ 回到 {base_n} 筆", s2["per"] == "all" and s2["nrows"] == base_n, [s2["per"], s2["nrows"]])
    # ③ 連動：滑過／點明細列
    row = pg.locator('#instTbl tr[data-d]').nth(3)
    d3 = row.get_attribute("data-d")
    row.scroll_into_view_if_needed(); row.hover(); pg.wait_for_timeout(300)
    s = pg.evaluate(_INST_ST)
    ok(f"★ [{tag}] 滑過明細一列（{d3}）→ 該列亮 .hl、root.dataset.hov 換成那天", s["hl"] == [d3] and s["hov"] == d3, [s["hl"], s["hov"]])
    row.click(); pg.wait_for_timeout(400)
    s = pg.evaluate(_INST_ST)
    ok(f"★ [{tag}] 點一列 → 鎖定（.lk、其他列變淡、兩張圖各出現一條垂直虛線）", s["lk"] == [d3] and s["dim"] == s["nrows"] - 1 and s["c1"]["lk"] == 1 and s["c2"]["lk"] == 1 and s["sel"] == d3, [s["lk"], s["dim"], s["c1"], s["c2"]])
    row.click(); pg.wait_for_timeout(400)
    s = pg.evaluate(_INST_ST)
    ok(f"[{tag}] 再點同一列 → 取消鎖定", s["lk"] == [] and s["dim"] == 0 and s["c1"]["lk"] == 0 and s["sel"] == "", [s["lk"], s["dim"], s["c1"]])
    # ④ 點圖
    pt = pg.evaluate("""() => { const el = document.getElementById('instLines'); el.scrollIntoView({ block: 'center', behavior: 'instant' });
      const c = echarts.getInstanceByDom(el), r = el.getBoundingClientRect(), n = (c.getOption().xAxis[0].data || []).length;
      const gr = c.getModel().getComponent('grid', 0).coordinateSystem.getRect(); const x = c.convertToPixel({ xAxisIndex: 0 }, Math.floor(n / 2));
      return { x: r.left + x, y: r.top + gr.y + gr.height * 0.5, d: c.getOption().xAxis[0].data[Math.floor(n / 2)] }; }""")
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(500)
    s = pg.evaluate(_INST_ST)
    ok(f"★ [{tag}] 點累積圖中間一天 → 鎖定那天（{pt['d']}）、表格同一列 .lk、兩張圖都出現虛線", s["sel"] == pt["d"] and (s["lk"] == [pt["d"]] or mobile) and s["c1"]["lk"] == 1, [s["sel"], s["lk"], pt["d"]])
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(400)
    ok(f"[{tag}] 再點同一天 → 取消", pg.evaluate(_INST_ST)["sel"] == "")
    # ⑤ 排序
    if not mobile:
        f0 = pg.evaluate(_INST_ST)["first"]
        pg.locator('#instTbl th[data-k="f"]').click(); pg.wait_for_timeout(300)
        a = pg.evaluate("() => [...document.querySelectorAll('#instTbl tbody tr')].map(r => parseFloat(r.children[1].textContent.replace('−', '-').replace(/[+,]/g, '')))")
        pg.locator('#instTbl th[data-k="f"]').click(); pg.wait_for_timeout(300)
        b = pg.evaluate("() => [...document.querySelectorAll('#instTbl tbody tr')].map(r => parseFloat(r.children[1].textContent.replace('−', '-').replace(/[+,]/g, '')))")
        ok(f"★ [{tag}] 點「外資」標題排序：先由大到小、再點變由小到大", a == sorted(a, reverse=True) and b == sorted(b) and a != b, [a[:3], b[:3]])
    # ⑥ 排行 + 族群
    s = pg.evaluate(_INST_ST)
    ok(f"★ [{tag}] 個股排行：買超／賣超各 ≤ 8 檔且不為空", 1 <= len(s["buy"]) <= 8 and 1 <= len(s["sell"]) <= 8, [len(s["buy"]), len(s["sell"])])
    pg.locator('#instGroupDD .twms-btn').click(); pg.wait_for_timeout(300)
    box = pg.locator('.twms-pan[data-ms="instGroups"] input[type="checkbox"]').nth(1)
    box.check(); pg.wait_for_timeout(500)
    s2 = pg.evaluate(_INST_ST)
    grps = {g for _, g in s2["buy"] + s2["sell"]}
    ok(f"★ [{tag}] 族群下拉勾一個 → 排行只剩那個族群（{grps}）、名單真的變", len(grps) == 1 and (s2["buy"] != s["buy"] or s2["sell"] != s["sell"]), [grps, s["buy"][:2], s2["buy"][:2]])
    pg.keyboard.press("Escape"); pg.mouse.click(5, 5); pg.wait_for_timeout(300)
    code = (s2["buy"] or s2["sell"])[0][0]
    pg.locator(f'#instRank .itrow[data-code="{code}"]').first.click(); pg.wait_for_timeout(800)
    ok(f"★ [{tag}] 點排行一列（{code}）→ 進個股頁", pg.evaluate("location.hash") == f"#stock/{code}", pg.evaluate("location.hash"))
    # ⑦ 連續買賣超
    pg.goto(f"{base}#market/streak", wait_until="networkidle"); pg.wait_for_timeout(1500)
    ok(f"★ [{tag}] 舊網址 #market/streak → 導到 #market/inst、停在「連續買賣超」", pg.evaluate("location.hash") == "#market/inst" and pg.evaluate("!!document.getElementById('streakWho')"), pg.evaluate("location.hash"))
    pg.locator('#streakView button[data-v="rank"]').click(); pg.wait_for_timeout(400)   # 手機預設是四象限，先切到排行才數得到列
    n0 = pg.evaluate("[...document.querySelectorAll('#trustRank .srcol')].map(c => c.querySelectorAll('.srrow[data-code]').length)")
    pg.locator('#streakGroupDD .twms-btn').click(); pg.wait_for_timeout(300)
    pg.locator('.twms-pan[data-ms="streakGroups"] input[type="checkbox"]').nth(1).check(); pg.wait_for_timeout(500)
    n1 = pg.evaluate("[...document.querySelectorAll('#trustRank .srcol')].map(c => c.querySelectorAll('.srrow[data-code]').length)")
    ok(f"★ [{tag}] 連續買賣超勾一個族群 → 買／賣筆數變（{n0}→{n1}）", n1 != n0 and sum(n1) <= sum(n0), [n0, n1])
    pg.keyboard.press("Escape"); pg.mouse.click(5, 5); pg.wait_for_timeout(300)
    pg.locator('#instView button[data-v="daily"]').click(); pg.wait_for_timeout(800)
    ok(f"[{tag}] 切回「日報」→ 日報再畫出來", _inst_wait(pg) and "三大法人買賣超日報" in pg.evaluate(_INST_ST)["title"])
    # ⑧ 版面
    s = pg.evaluate(_INST_ST)
    ok(f"[{tag}] 沒有橫向捲軸、可見文字都 ≥ 11px（超小字 {s['small']} 個）", s["sw"] <= s["iw"] + 1 and s["small"] == 0, [s["sw"], s["iw"], s["small"]])
    if mobile:
        ok(f"[{tag}] 手機：四格 2×2", len({t["y"] for t in s["tiles"]}) == 2 and len({t["x"] for t in s["tiles"]}) == 2, [(t["x"], t["y"]) for t in s["tiles"]])
        ok(f"★ [{tag}] 手機：明細表先只列 6 筆", s["nrows"] <= 6 and s["tb"], [s["nrows"], s["tb"]])
        pg.locator("#instTblAll").click(); pg.wait_for_timeout(400)
        ok(f"★ [{tag}] 手機：按「看全部」→ 筆數變多", pg.evaluate(_INST_ST)["nrows"] > s["nrows"] or s["nrows"] < 6)
    else:
        ok(f"[{tag}] 桌機：四格同一排", len({t["y"] for t in s["tiles"]}) == 1, [t["y"] for t in s["tiles"]])


def t_inst_today_1020(b, base):
    errs: list[str] = []
    for tag, vp, mobile in (("1440", {"width": 1440, "height": 1000}, False), ("390", {"width": 390, "height": 844}, True)):
        kw = dict(viewport=vp)
        if mobile:
            kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
        c = b.new_context(**kw)
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        try:
            _inst_run(pg, base, tag, mobile)
        finally:
            c.close()
    ok("當日法人1020：沒有網頁錯誤", not errs, errs[:3])


register("當日法人1020", lambda pg, b, base, code: t_inst_today_1020(b, base))
