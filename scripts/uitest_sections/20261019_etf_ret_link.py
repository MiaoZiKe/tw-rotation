# 驗收段落「ETF報酬連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== ETF報酬連動1019
# Andy 10-19（附報酬比較截圖）：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」。
# 1440／390 各走一輪，全部用真的滑鼠移動與點擊（不是直接呼叫函式），每一步都量畫面真的變了：
#   ① 滑過折線某一條 → 那條 lineStyle.width 變粗、其他線 opacity 變淡；橫條那檔兩根全亮、其他變淡；表格那列 .hl
#   ② 滑出 → 全部恢復（寬度回 1.8、opacity 回 1、沒有 .hl）
#   ③ 滑過橫條、滑過表格列 → 同上（三處都能當起點）
#   ④ 點折線 → 鎖定（滑出後仍保留，線有陰影描邊、橫條有外框、表格列 .lk）；點空白處（圖內空白、卡片標題）→ 取消
#   ⑤ 點表格列 → 選取（不離開這頁）；桌機再點同一列 → 進個股頁；手機點一列＝展開＋選取，再點＝收起＋取消
#   ⑥ 切期間後那檔還在 → 選取保留
#   ⑦ 手機點選不捲動頁面、沒有橫向捲軸；全程沒有網頁錯誤

_RETLINK_JS = """() => {
  const g = (id) => echarts.getInstanceByDom(document.getElementById(id));
  const ln = g('etfRetLine'), br = g('etfRetBar');
  const lo = ln.getOption(), bo = br.getOption();
  const S = window.TwEtfPage.state;
  return {
    sel: S.retSel || null,
    lw: lo.series.map(s => s.lineStyle.width), lop: lo.series.map(s => s.lineStyle.opacity == null ? 1 : s.lineStyle.opacity),
    lsh: lo.series.map(s => s.lineStyle.shadowBlur || 0),
    bop: bo.series.map(s => s.data.map(d => (d && d.itemStyle && d.itemStyle.opacity != null) ? d.itemStyle.opacity : 1)),
    bbw: bo.series.map(s => s.data.map(d => (d && d.itemStyle && d.itemStyle.borderWidth) || 0)),
    bcol: bo.series.map(s => s.data.map(d => (d && d.itemStyle && d.itemStyle.color) ? 1 : 0)),
    hl: [...document.querySelectorAll('#etfRetTbl tr[data-code].hl')].map(t => t.dataset.code),
    lk: [...document.querySelectorAll('#etfRetTbl tr[data-code].lk')].map(t => t.dataset.code),
    dimTr: [...document.querySelectorAll('#etfRetTbl tr[data-code].dim')].length,
    trOp: Object.fromEntries([...document.querySelectorAll('#etfRetTbl tr[data-code]')].map(t => [t.dataset.code, +getComputedStyle(t).opacity])),
  };
}"""

# 折線第 k 條上「離其他線最遠」的一點（頁面座標），滑鼠停那裡才不會先碰到別條線
_RETLINE_PT_JS = """(k) => {
  document.getElementById('etfRetLine').scrollIntoView({ block: 'center', behavior: 'instant' });   // 手機頂端／底部有固定列，圖要在畫面中間才點得到
  const el = document.getElementById('etfRetLine'), ch = echarts.getInstanceByDom(el), o = ch.getOption(), r = el.getBoundingClientRect();
  const ser = o.series, me = ser[k].data, n = me.length;
  const maps = ser.map(s => new Map(s.data.map(d => [d[0], d[1]])));
  let best = null;
  for (let j = Math.floor(n * 0.25); j < Math.floor(n * 0.9); j += Math.max(1, Math.floor(n / 80))) {
    const [d, v] = me[j], p = ch.convertToPixel({ seriesIndex: k }, [d, v]);
    let gap = 1e9;
    ser.forEach((s, i) => { if (i === k) return; const w = maps[i].get(d); if (w == null) return; const q = ch.convertToPixel({ seriesIndex: i }, [d, w]); gap = Math.min(gap, Math.abs(q[1] - p[1])); });
    if (!best || gap > best.gap) best = { gap, x: r.left + p[0], y: r.top + p[1] };
  }
  return best;
}"""

# 橫條第 s 個系列、第 j 根的中心點（頁面座標）
_RETBAR_PT_JS = """([s, j]) => {
  document.getElementById('etfRetBar').scrollIntoView({ block: 'center', behavior: 'instant' });
  const el = document.getElementById('etfRetBar'), ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const L = ch.getModel().getSeriesByIndex(s).getData().getItemLayout(j);
  if (!L) return null;
  return { x: r.left + L.x + L.width / 2, y: r.top + L.y + L.height / 2 };
}"""


# 頁面真的往右捲不動才算「沒有橫向捲軸」（分類鈕列是自己的橫捲容器，m4bleed 的負邊距會讓 scrollWidth 多幾 px，但頁面本身捲不動）
_NOHSCROLL_X = "() => { const y = scrollY; scrollTo({ left: 60, top: y, behavior: 'instant' }); const x = scrollX; scrollTo({ left: 0, top: y, behavior: 'instant' }); return [x, document.documentElement.scrollWidth, innerWidth, getComputedStyle(document.documentElement).overflowX]; }"
_NOHSCROLL_JS = "() => { const y = scrollY; scrollTo({ left: 60, top: y, behavior: 'instant' }); const x = scrollX; scrollTo({ left: 0, top: y, behavior: 'instant' }); return x === 0; }"


def t_etf_ret_link_1019(b, base, code):
    T = "ETF報酬連動1019"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_ETFRET_SHOT")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#etf/list", wait_until="networkidle")   # 報酬比較在「ETF 總覽」分頁（#etf 預設是配息行事曆）
        J("() => { try { Object.keys(localStorage).filter(k => k.startsWith('tw.etf.')).forEach(k => localStorage.removeItem(k));"
          " localStorage.setItem('tw.etf.cat', '配息型'); localStorage.setItem('tw.etf.cmp.配息型', JSON.stringify(['0056', '00878', '00919'])); } catch (e) {} }")
        pg.reload(wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, """() => { const S = window.TwEtfPage && window.TwEtfPage.state; if (!S || !S.series) return false;
            const l = document.getElementById('etfRetLine'), b = document.getElementById('etfRetBar');
            return !!l && !!b && +l.dataset.n >= 2 && +b.dataset.n >= 2 && !!echarts.getInstanceByDom(l) && !!echarts.getInstanceByDom(b); }""", 20000)
        ok(f"{T}（{W}）：報酬比較畫出 ≥ 2 條走勢與 ≥ 2 檔橫條（前置）", bool(ready),
           J("() => [document.querySelector('#v-etf') && document.querySelector('#v-etf').dataset.cat, (document.getElementById('etfRetLine') || {dataset:{}}).dataset.n]"))
        if not ready:
            c.close(); continue
        pg.locator("#etfRetCard").scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        dim = J("() => document.documentElement.getAttribute('data-theme') === 'light' ? 0.35 : 0.55")
        codes_line = J("() => { const o = echarts.getInstanceByDom(document.getElementById('etfRetLine')).getOption(); return o.series.map(s => (s.name.match(/\\b([0-9]{4,6}[A-Z]?)\\b/) || [])[1]); }")
        codes_bar = J("() => [...document.querySelectorAll('#etfRetTbl tr[data-code]')].map(t => t.dataset.code)")
        bar_codes = J("() => { const o = echarts.getInstanceByDom(document.getElementById('etfRetBar')).getOption(); return o.yAxis[0].data.map(x => String(x).split('\\n')[0]); }")
        st0 = J(_RETLINK_JS)
        ok(f"{T}（{W}）：初始全部正常亮度（線寬 1.8、opacity 1、沒有 .hl）",
           all(w == 1.8 for w in st0["lw"]) and all(o == 1 for o in st0["lop"]) and all(o == 1 for s in st0["bop"] for o in s) and not st0["hl"] and st0["sel"] is None, st0)

        def away():
            pg.mouse.move(W - 4, 4); pg.wait_for_timeout(250)

        def lit_ok(st, code_, lvl=1):
            li = codes_line.index(code_) if code_ in codes_line else -1
            bj = bar_codes.index(code_) if code_ in bar_codes else -1
            line_ok = li < 0 or (st["lw"][li] > 3 and st["lop"][li] == 1 and all(abs(o - dim) < 1e-6 for i, o in enumerate(st["lop"]) if i != li))
            bar_ok = bj < 0 or all(s[bj] == 1 and all(abs(o - dim) < 1e-6 for j, o in enumerate(s) if j != bj) for s in st["bop"] if s[bj] is not None)
            tr_ok = code_ in st["hl"] and st["dimTr"] == len(codes_bar) - 1
            lock_ok = lvl < 2 or (st["sel"] == code_ and code_ in st["lk"] and (li < 0 or st["lsh"][li] > 0) and (bj < 0 or any(s[bj] > 0 for s in st["bbw"])))
            col_ok = all(all(x for x in s) for s in st["bcol"])   # 資料項帶 itemStyle 也要帶顏色（不然退回預設色）
            return line_ok and bar_ok and tr_ok and lock_ok and col_ok

        def normal(st):
            return all(w == 1.8 for w in st["lw"]) and all(o == 1 for o in st["lop"]) and all(o == 1 for s in st["bop"] for o in s) and not st["hl"] and st["dimTr"] == 0

        # ① 滑過折線
        k = 0
        pt = J(_RETLINE_PT_JS, k)
        pg.mouse.move(pt["x"], pt["y"]); pg.wait_for_timeout(300)
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：滑過折線 {codes_line[k]} → 那條加粗、其他線變淡 {dim}；橫條那檔亮、其他淡；表格那列 .hl", lit_ok(st, codes_line[k]), [pt, st])
        if shot_dir and W == 1440:
            pg.locator("#etfRetCard").screenshot(path=os.path.join(shot_dir, "etfret_link_hover.png"))
        away(); st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：滑出 → 全部恢復", normal(st) and st["sel"] is None, st)
        # ③ 滑過橫條（含息那根，若有）
        j = 1
        bp = J(_RETBAR_PT_JS, [len(st["bop"]) - 1, j])
        pg.mouse.move(bp["x"], bp["y"]); pg.wait_for_timeout(300)
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：滑過橫條 {bar_codes[j]} → 三處同一檔亮、其他變淡", lit_ok(st, bar_codes[j]), [bp, st])
        away()
        # 滑過表格列
        tcode = codes_bar[-1]
        pg.hover(f"#etfRetTbl tr[data-code='{tcode}'] td:first-child"); pg.wait_for_timeout(300)
        wait_until(pg, f"() => Math.abs(+getComputedStyle(document.querySelector('#etfRetTbl tr[data-code=\"{codes_bar[0]}\"]')).opacity - {dim}) < 0.02", 2000)
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：滑過表格列 {tcode} → 折線那條加粗、橫條那檔亮、該列 .hl、其他列 opacity 變淡",
           lit_ok(st, tcode) and abs(st["trOp"][codes_bar[0]] - dim) < 0.02, st)
        away(); ok(f"{T}（{W}）：滑出表格 → 恢復", normal(J(_RETLINK_JS)))
        # ④ 點折線＝鎖定
        pt = J(_RETLINE_PT_JS, k)   # 上一步 hover 表格列時 Playwright 可能捲過頁面，座標要重量
        y0 = J("() => scrollY")
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(300); away()
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：點折線 {codes_line[k]} → 鎖定（滑出後仍保留；線有描邊、橫條外框、表格列 .lk）", lit_ok(st, codes_line[k], 2), st)
        if W == 390:
            ok(f"{T}（390）：點圖選取不捲動頁面（手機不捲去表格）", abs(J("() => scrollY") - y0) < 2, [y0, J("() => scrollY")])
            # ⚠ 提示框（ECharts 掛在 body、nowrap）點線當下會比 390 寬幾 px —— main 上本來就有、跟連動無關；提示框收掉之後頁面不能橫捲
            pg.wait_for_timeout(600)
            ok(f"{T}（390）：提示框收掉後頁面沒有橫向捲軸", J(_NOHSCROLL_JS), J(_NOHSCROLL_X))
        if shot_dir and W == 1440:
            pg.locator("#etfRetCard").screenshot(path=os.path.join(shot_dir, "etfret_link_locked.png"))
        # 點圖內空白（繪圖區左上角：期初全部是 0%，左上角不會有線）
        blank = J("""() => { document.getElementById('etfRetLine').scrollIntoView({ block: 'center', behavior: 'instant' }); const el = document.getElementById('etfRetLine'), ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
            const g = ch.getModel().getComponent('grid').coordinateSystem.getRect(); return { x: r.left + g.x + 4, y: r.top + g.y + 4 }; }""")
        pg.mouse.click(blank["x"], blank["y"]); pg.wait_for_timeout(300); away()
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：點折線圖空白處 → 取消選取、全部恢復", st["sel"] is None and normal(st), [blank, st])
        # 點橫條鎖定 → 點卡片標題（空白）取消
        bp = J(_RETBAR_PT_JS, [0, 0])
        pg.mouse.click(bp["x"], bp["y"]); pg.wait_for_timeout(300); away()
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：點橫條 {bar_codes[0]} → 鎖定", lit_ok(st, bar_codes[0], 2), st)
        pg.mouse.click(bp["x"], bp["y"]); pg.wait_for_timeout(400); away()
        ok(f"{T}（{W}）：再點同一根 → 取消", J(_RETLINK_JS)["sel"] is None)
        pg.mouse.click(bp["x"], bp["y"]); pg.wait_for_timeout(400)
        pg.click("#etfRetLineTtl"); pg.wait_for_timeout(300); away()
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：鎖定後點卡片內空白（圖標題）→ 取消", st["sel"] is None and normal(st), st)
        # ⑤ 點表格列＝選取（不離開這頁）
        h0 = J("() => location.hash")
        pg.click(f"#etfRetTbl tr[data-code='{tcode}'] td:first-child"); pg.wait_for_timeout(400); away()
        st = J(_RETLINK_JS)
        ok(f"{T}（{W}）：點表格列 {tcode} → 選取三處連動、沒有離開這頁", lit_ok(st, tcode, 2) and J("() => location.hash") == h0, [st, J("() => location.hash")])
        # ⑥ 切期間（1 年）→ 那檔還在 → 保留
        if pg.locator("#etfRng .rpsel").count() and pg.locator("#etfRng .rpsel").is_visible():
            pg.select_option("#etfRng .rpsel", "1y"); pg.wait_for_timeout(700); away()
            st = J(_RETLINK_JS)
            ok(f"{T}（{W}）：切期間 1 年重畫後，選取的 {tcode} 仍保留連動", st["sel"] == tcode and tcode in st["lk"], st)
            codes_line = J("() => { const o = echarts.getInstanceByDom(document.getElementById('etfRetLine')).getOption(); return o.series.map(s => (s.name.match(/\\b([0-9]{4,6}[A-Z]?)\\b/) || [])[1]); }")
            bar_codes = J("() => { const o = echarts.getInstanceByDom(document.getElementById('etfRetBar')).getOption(); return o.yAxis[0].data.map(x => String(x).split('\\n')[0]); }")
            ok(f"{T}（{W}）：切期間後重畫的圖也套上選取（線加粗＋其他淡）", lit_ok(st, tcode, 2), st)
        if W == 1440:
            pg.click(f"#etfRetTbl tr[data-code='{tcode}'] td:first-child"); pg.wait_for_timeout(500)
            ok(f"{T}（1440）：已選中的表格列再點一次 → 進個股頁", bool(wait_until(pg, f"() => location.hash === '#stock/{tcode}'", 4000)), J("() => location.hash"))
        else:
            pg.click(f"#etfRetTbl tr[data-code='{tcode}'] td:first-child"); pg.wait_for_timeout(400)
            st = J(_RETLINK_JS)
            ok(f"{T}（390）：手機再點同一列 → 收起明細＋取消選取（不離開這頁）",
               st["sel"] is None and normal(st) and J("() => !document.querySelector('#etfRetTbl tr.m4retx') && location.hash") == h0, st)
            pg.click(f"#etfRetTbl tr[data-code='{tcode}'] td:first-child"); pg.wait_for_timeout(400)
            st = J(_RETLINK_JS)
            ok(f"{T}（390）：手機點一列 → 展開明細＋選取連動", st["sel"] == tcode and lit_ok(st, tcode, 2) and J("() => !!document.querySelector('#etfRetTbl tr.m4retx')"), st)
            ok(f"{T}（390）：沒有橫向捲軸", J(_NOHSCROLL_JS))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF報酬連動1019", lambda pg, b, base, code: t_etf_ret_link_1019(b, base, code))
