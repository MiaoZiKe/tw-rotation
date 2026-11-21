# 驗收段落「個股連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 個股連動1019
# Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」（普查 docs/chart_link_census_1019.md 第 1～4 項）。
# 個股頁四組（營收｜獲利｜除權息｜法人／資券／大戶散戶），1440 與 390 各走一輪，全部用真的滑鼠移動／點擊／觸控點（不呼叫函式），每一步量畫面真的變了：
#   ① 滑過圖上某一欄 → 那一欄的柱 opacity 1、其他柱變淡（< 1）；同頁另一張圖在同一時點畫虛線（data-lk-cols）；明細表那一列 .hl、其他列 .dim
#   ② 桌機：滑到表格看不到的那一列 → **表格自己的捲動框**捲過去（scrollTop 變了），整頁 scrollY 不動
#   ③ 滑出 → 全部恢復（沒有 .hl、柱 opacity 全 1、虛線清空）
#   ④ 點一下＝鎖定（滑出後仍在、表格列 .lk、柱有外框）；再點同一欄＝取消；點表格列＝選取；點空白處（標題字、頁面外）＝取消
#   ⑤ 獲利「季／年」：季選 2024Q3 → 切年變成 2024，本益比（每季）那張亮那一年的幾季（按年度對齊）；切回季那一年的季都亮
#   ⑥ 法人切區間（3 個月 → 4 週），選的那天還在 → 選取保留
#   ⑦ 手機（390）：觸控點圖 → 表格列 .hl；點同一處取消；點除權息一列＝展開＋選取；點選不捲動頁面；全程沒有網頁錯誤

_LK_STATE = """(a) => { const [id, tbl] = a; const el = document.getElementById(id); const ch = el && window.echarts && echarts.getInstanceByDom(el);
  const o = ch ? ch.getOption() : { series: [] };
  const ops = [], bws = [];
  o.series.forEach(s => { if (s.type !== 'bar' || s.silent) return; (s.data || []).forEach(d => { if (d == null || typeof d !== 'object') return;
    ops.push(d.itemStyle && d.itemStyle.opacity != null ? d.itemStyle.opacity : 1); bws.push(d.itemStyle && d.itemStyle.borderWidth || 0); }); });
  const rows = [...document.querySelectorAll(tbl + ' tr[data-k]')];
  const root = document.getElementById('stockTab').contains(el) ? document.getElementById('stockTab') : (el ? el.closest('#mbBody') : null);
  const box = rows.length ? rows[0].closest('.tw, .mbtblwrap') : null;
  return { sel: root ? root.dataset.lkSel || '' : '', hov: root ? root.dataset.lkHov || '' : '',
    lit: ops.filter(v => v === 1).length, dim: ops.filter(v => v < 1).length, bw: bws.filter(v => v > 0).length,
    cols: el ? el.dataset.lkCols || '' : '',
    hl: rows.filter(r => r.classList.contains('hl')).map(r => r.dataset.k), lk: rows.filter(r => r.classList.contains('lk')).map(r => r.dataset.k),
    rdim: rows.filter(r => r.classList.contains('dim')).length, nrow: rows.length,
    trOp: rows.length ? Math.min(...rows.map(r => +getComputedStyle(r).opacity)) : 1,
    tsc: box ? Math.round(box.scrollTop) : -1, py: Math.round(scrollY) }; }"""

# 第 g 格、第 j 個類別的中心點（頁面座標）；先把圖捲到畫面中間（手機頂端與底部有固定列）
_LK_PT = """(a) => { const [id, j, g, noScroll] = a; const el = document.getElementById(id);
  if (!noScroll) el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const gr = ch.getModel().getComponent('grid', g || 0).coordinateSystem.getRect();
  const x = ch.convertToPixel({ xAxisIndex: (g || 0) }, j);
  return { x: r.left + x, y: r.top + gr.y + gr.height * 0.55, n: (ch.getOption().xAxis[g || 0].data || []).length }; }"""


def _lk_open(b, base, w, code, errs):
    mob = w <= 640
    c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, is_mobile=mob, has_touch=mob)
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.chipWin','63');localStorage.setItem('tw.revView','m');localStorage.setItem('tw.profitMode','q')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
    pg.goto(base + f"#stock/{code}", wait_until="domcontentloaded")
    wait_until(pg, "() => document.querySelectorAll('#stockTabs button, #mbTabRow button').length > 0", 15000)
    agree = pg.get_by_role("button", name="同意並繼續")
    if agree.count() and agree.first.is_visible():
        agree.first.click(); pg.wait_for_timeout(300)
    return c, pg


def _lk_tab(pg, name, chart_id):
    sel = "#mbTabRow button" if pg.viewport_size["width"] <= 640 else "#stockTabs button"
    btn = pg.locator(sel, has_text=name).first
    if not btn.count():
        return False
    btn.click()
    return wait_until(pg, f"() => {{ const e = document.getElementById('{chart_id}'); return !!e && !!window.echarts && !!echarts.getInstanceByDom(e); }}", 10000)


def _lk_hover(pg, cid, j, g=0):
    p = pg.evaluate(_LK_PT, [cid, j, g, False]); pg.mouse.move(p["x"], p["y"]); pg.wait_for_timeout(250); return p


def _lk_click(pg, cid, j, g=0):
    p = pg.evaluate(_LK_PT, [cid, j, g, False]); pg.mouse.click(p["x"], p["y"]); pg.wait_for_timeout(300); return p


def _lk_away(pg):
    # 滑到頁首（不在任何圖或表上）＝滑出
    pg.mouse.move(700, 20); pg.wait_for_timeout(250)


def t_stock_link_desktop(b, base, errs):
    T = "個股連動1019（1440）"
    shots = os.environ.get("TW_STOCK_LINK_SHOT")
    c, pg = _lk_open(b, base, 1440, "2330", errs)
    st = lambda cid, tbl: pg.evaluate(_LK_STATE, [cid, tbl])
    # ---------------- 營收
    if _lk_tab(pg, "營收", "revBar"):
        pg.click("#revWin button[data-v='36']"); pg.wait_for_timeout(500)
        py0 = pg.evaluate("() => { document.getElementById('revBar').scrollIntoView({ block: 'center', behavior: 'instant' }); return Math.round(scrollY); }")
        p = _lk_hover(pg, "revBar", 0)
        s1 = st("revBar", "#revTbl")
        ok(f"{T} 營收：滑過最左一欄 → 那一欄全亮、其他柱變淡、逐年同月畫虛線、明細表那列 .hl", s1["lit"] >= 1 and s1["dim"] > 10 and s1["hl"] and s1["rdim"] > 5
           and pg.evaluate("() => document.getElementById('revYear').dataset.lkCols") != "", s1)
        ok(f"{T} 營收：滑到表格底部那一列 → 只捲表格（scrollTop {s1['tsc']} > 0）、整頁不動（{py0}→{s1['py']}）", s1["tsc"] > 0 and abs(s1["py"] - py0) <= 1, s1)
        _lk_away(pg)
        s2 = st("revBar", "#revTbl")
        ok(f"{T} 營收：滑出 → 全部恢復", not s2["hl"] and s2["dim"] == 0 and s2["rdim"] == 0 and s2["cols"] == "", s2)
        _lk_click(pg, "revBar", p["n"] - 3); _lk_away(pg)
        s3 = st("revBar", "#revTbl")
        ok(f"{T} 營收：點一欄 → 鎖定（滑出後仍在、表格列 .lk、柱有外框、其他列變淡 opacity {s3['trOp']}）", s3["sel"] != "" and s3["lk"] == [s3["sel"]] and s3["bw"] >= 1 and s3["dim"] > 0 and s3["trOp"] < 0.6, s3)
        if shots:
            pg.screenshot(path=f"{shots}/stock_link_rev.png")
        _lk_click(pg, "revBar", p["n"] - 3); _lk_away(pg)
        s4 = st("revBar", "#revTbl")
        ok(f"{T} 營收：再點同一欄 → 取消", s4["sel"] == "" and not s4["hl"] and s4["dim"] == 0, s4)
        pg.locator("#revTbl tr[data-k]").nth(4).click(); pg.wait_for_timeout(300)
        k5 = pg.evaluate("() => document.querySelectorAll('#revTbl tr[data-k]')[4].dataset.k")
        _lk_away(pg)
        s5 = st("revBar", "#revTbl")
        ok(f"{T} 營收：點表格第 5 列 → 選取 {k5}，圖上那一欄亮、虛線在那一欄", s5["sel"] == k5 and s5["lit"] >= 1 and s5["dim"] > 0 and s5["cols"] != "", s5)
        pg.click("#revView button[data-v='y']"); pg.wait_for_timeout(600)
        s6 = st("revBar", "#revTbl")
        ok(f"{T} 營收：切「年度走勢」→ 選取保留，年度柱亮 {k5[:4]} 那一根", s6["sel"] == k5 and s6["lit"] == 1 and s6["dim"] > 0, s6)
        pg.click("#revView button[data-v='m']"); pg.wait_for_timeout(600)
        pg.locator("#revSub").click(); pg.wait_for_timeout(300)
        s7 = st("revBar", "#revTbl")
        ok(f"{T} 營收：點空白（標題旁的讀數字）→ 取消", s7["sel"] == "" and not s7["hl"] and s7["dim"] == 0, s7)
    else:
        ok(f"{T} 營收：分頁打得開", False)
    # ---------------- 獲利
    if _lk_tab(pg, "獲利", "profitChart"):
        pg.wait_for_timeout(800)
        n = pg.evaluate(_LK_PT, ["profitChart", 0, 0, False])["n"]
        _lk_hover(pg, "profitChart", n - 4)
        s1 = st("profitChart", "#profitTbl")
        pq = pg.evaluate("() => document.getElementById('peQ').dataset.lkCols || ''")
        ok(f"{T} 獲利：滑過 EPS 一季 → 本益比（每季）同一季畫虛線、季報明細那列 .hl", s1["lit"] >= 1 and s1["dim"] > 0 and len(s1["hl"]) == 1 and pq != "", [s1, pq])
        _lk_click(pg, "profitChart", n - 4); _lk_away(pg)
        q = pg.evaluate("() => document.getElementById('stockTab').dataset.lkSel")
        pg.click("#profitMode button[data-v='y']"); pg.wait_for_timeout(700)
        s2 = st("profitChart", "#profitTbl")
        pq2 = pg.evaluate("() => document.getElementById('peQ').dataset.lkCols || ''")
        ok(f"{T} 獲利：季選 {q} → 切「年」變成 {q[:4]}，年度柱亮一根、年度明細那列亮、本益比亮那一年的 {len(pq2.split(',')) if pq2 else 0} 季",
           len(q) == 6 and s2["sel"] == q[:4] and s2["lit"] == 1 and s2["hl"] == [q[:4]] and 1 <= len(pq2.split(",")) <= 4 and pq2 != "", [s2, pq2])
        pg.click("#profitMode button[data-v='q']"); pg.wait_for_timeout(700)
        s3 = st("profitChart", "#profitTbl")
        ok(f"{T} 獲利：切回「季」→ {q[:4]} 那一年的季都亮（{s3['lit']} 根）、明細表那一年的列都亮", s3["sel"] == q[:4] and 1 <= s3["lit"] <= 4 and len(s3["hl"]) == s3["lit"], s3)
        pg.locator("#peQCard h3").first.click(position={"x": 8, "y": 8}); pg.wait_for_timeout(300)
        s4 = st("profitChart", "#profitTbl")
        ok(f"{T} 獲利：點空白（卡片標題）→ 取消", s4["sel"] == "" and s4["dim"] == 0 and not s4["hl"], s4)
        if shots:
            _lk_click(pg, "peQ", max(0, pg.evaluate(_LK_PT, ["peQ", 0, 0, False])["n"] - 5)); _lk_away(pg)
            pg.screenshot(path=f"{shots}/stock_link_profit.png")
            pg.locator("#peQCard h3").first.click(position={"x": 8, "y": 8}); pg.wait_for_timeout(200)
    else:
        ok(f"{T} 獲利：分頁打得開", False)
    # ---------------- 除權息
    if _lk_tab(pg, "除權息", "divBar"):
        pg.wait_for_timeout(500)
        ks = pg.evaluate("() => [...document.querySelectorAll('#divRec tr[data-k]')].map(r => r.dataset.k)")
        yrs = pg.evaluate("() => echarts.getInstanceByDom(document.getElementById('divBar')).getOption().xAxis[0].data")
        yi = next((i for i, y in enumerate(yrs) if any(k.startswith(str(y)) for k in ks)), None)
        if yi is None:
            ok(f"{T} 除權息：有對得到紀錄的年份", False, [ks[:3], yrs])
        else:
            _lk_hover(pg, "divBar", yi)
            s1 = st("divBar", "#divRec")
            want = [k for k in ks if k.startswith(str(yrs[yi]))]
            ok(f"{T} 除權息：滑過 {yrs[yi]} 那根 → 紀錄表那一年的 {len(want)} 次全亮、其他列變淡", s1["hl"] == want and s1["dim"] > 0 and (s1["rdim"] > 0 or len(ks) == len(want)), s1)
            _lk_away(pg)
            pg.locator("#divRec tr[data-k]").first.click(); pg.wait_for_timeout(300)
            _lk_away(pg)
            s2 = st("divBar", "#divRec")
            ok(f"{T} 除權息：點紀錄第一列 → 選取那一次（{ks[0]}），它那一年的柱亮、有外框", s2["sel"] == ks[0] and s2["lit"] >= 1 and s2["bw"] >= 1 and s2["lk"] == [ks[0]], s2)
            if shots:
                pg.screenshot(path=f"{shots}/stock_link_div.png")
            pg.mouse.click(700, 20); pg.wait_for_timeout(300)
            s3 = st("divBar", "#divRec")
            ok(f"{T} 除權息：點頁面其他地方（頁首）→ 取消", s3["sel"] == "" and not s3["hl"] and s3["dim"] == 0, s3)
    else:
        ok(f"{T} 除權息：分頁打得開", False)
    # ---------------- 法人
    if _lk_tab(pg, "法人", "instChart"):
        pg.wait_for_timeout(500)
        py0 = pg.evaluate("() => { document.getElementById('instChart').scrollIntoView({ block: 'center', behavior: 'instant' }); return Math.round(scrollY); }")
        n = pg.evaluate(_LK_PT, ["instChart", 0, 0, True])["n"]
        _lk_hover(pg, "instChart", 3)
        s1 = st("instChart", "#instTbl")
        ok(f"{T} 法人：滑過 3 個月前那一天 → 表格那一列 .hl 並捲進表格（scrollTop {s1['tsc']}）、整頁不動", len(s1["hl"]) == 1 and s1["dim"] > 0 and s1["tsc"] > 0 and abs(s1["py"] - py0) <= 1, s1)
        _lk_click(pg, "instChart", n - 3); _lk_away(pg)
        s2 = st("instChart", "#instTbl")
        pg.click("#chipWin button[data-v='20']"); pg.wait_for_timeout(700)
        s3 = st("instChart", "#instTbl")
        ok(f"{T} 法人：點選 {s2['sel']} → 切「4 週」重畫後選取保留、那天的柱仍亮", s2["sel"] != "" and s3["sel"] == s2["sel"] and s3["lit"] == 1 and s3["dim"] > 0 and s3["lk"] == [s2["sel"]], [s2, s3])
        if shots:
            pg.screenshot(path=f"{shots}/stock_link_inst.png")
        _lk_click(pg, "instChart", pg.evaluate(_LK_PT, ["instChart", 0, 0, False])["n"] - 3); _lk_away(pg)
        s4 = st("instChart", "#instTbl")
        ok(f"{T} 法人：再點同一天 → 取消", s4["sel"] == "" and s4["dim"] == 0 and not s4["hl"], s4)
        pg.click("#chipWin button[data-v='63']"); pg.wait_for_timeout(500)
    else:
        ok(f"{T} 法人：分頁打得開", False)
    # ---------------- 資券
    if _lk_tab(pg, "資券", "marginChart"):
        pg.wait_for_timeout(500)
        n = pg.evaluate(_LK_PT, ["marginChart", 0, 0, False])["n"]
        _lk_hover(pg, "marginChart", n - 5)
        s1 = st("marginChart", "#mgTbl")
        ok(f"{T} 資券：滑過一天 → 那天柱亮、其他變淡、明細那列 .hl", len(s1["hl"]) == 1 and s1["dim"] > 0 and s1["lit"] == 1, s1)
        _lk_click(pg, "marginChart", n - 5); _lk_away(pg)
        s2 = st("marginChart", "#mgTbl")
        pg.locator("#marginChartDuo h3").first.click(position={"x": 6, "y": 6}); pg.wait_for_timeout(300)
        s3 = st("marginChart", "#mgTbl")
        ok(f"{T} 資券：點一天鎖定 → 點卡片標題取消", s2["sel"] != "" and s2["lk"] == [s2["sel"]] and s3["sel"] == "" and s3["dim"] == 0, [s2, s3])
    else:
        ok(f"{T} 資券：分頁打得開", False)
    # ---------------- 大戶散戶
    if _lk_tab(pg, "大戶／散戶", "holderChart"):
        pg.wait_for_timeout(500)
        n = pg.evaluate(_LK_PT, ["holderChart", 0, 0, False])["n"]
        _lk_hover(pg, "holderChart", n // 2)
        s1 = st("holderChart", "#hoTbl")
        ok(f"{T} 大戶散戶：滑過任一天 → 吸到最近的公布日，每週明細那一列 .hl、三格都畫虛線", len(s1["hl"]) == 1 and s1["cols"] != "" and s1["rdim"] >= 1, s1)
        _lk_click(pg, "holderChart", n // 2); _lk_away(pg)
        s2 = st("holderChart", "#hoTbl")
        if shots:
            pg.screenshot(path=f"{shots}/stock_link_holder.png")
        _lk_click(pg, "holderChart", n // 2); _lk_away(pg)
        s3 = st("holderChart", "#hoTbl")
        ok(f"{T} 大戶散戶：點一下鎖定（鎖的是滑過時那個公布日）", bool(s1["hl"]) and s2["sel"] == s1["hl"][0] and s2["lk"] == [s2["sel"]], [s1, s2])
        ok(f"{T} 大戶散戶：取消後恢復", s3["sel"] == "" and not s3["hl"] and s3["cols"] == "", s3)
    else:
        ok(f"{T} 大戶散戶：分頁打得開", False)
    c.close()


def t_stock_link_mobile(b, base, errs):
    T = "個股連動1019（390）"
    c, pg = _lk_open(b, base, 390, "2330", errs)
    st = lambda cid, tbl: pg.evaluate(_LK_STATE, [cid, tbl])

    def tap(cid, j):
        p = pg.evaluate(_LK_PT, [cid, j, 0, False]); pg.wait_for_timeout(150)
        y0 = pg.evaluate("() => Math.round(scrollY)")
        pg.touchscreen.tap(p["x"], p["y"]); pg.wait_for_timeout(450)
        return p, y0

    for tab, cid in (("營收", "mbChart"), ("獲利", "mbChart"), ("法人", "mbChart"), ("資券", "mbChart"), ("大戶／散戶", "mbChart")):
        if not _lk_tab(pg, tab, cid):
            ok(f"{T} {tab}：分頁打得開", False); continue
        pg.wait_for_timeout(500)
        n = pg.evaluate(_LK_PT, [cid, 0, 0, False])["n"]
        p, y0 = tap(cid, n - 2)
        s1 = st(cid, "#mbBody .mbtbl")
        if os.environ.get("TW_STOCK_LINK_SHOT") and tab == "法人":
            pg.screenshot(path=os.environ["TW_STOCK_LINK_SHOT"] + "/stock_link_m390.png")
        ok(f"{T} {tab}：點圖上一欄 → 表格那一列亮（{s1['hl'][:1]}）、其他列變淡、頁面不捲動（{y0}→{s1['py']}）",
           s1["sel"] != "" and len(s1["hl"]) >= 1 and s1["rdim"] > 0 and abs(s1["py"] - y0) <= 1 and (s1["dim"] > 0 or tab == "大戶／散戶"), s1)
        pg.touchscreen.tap(p["x"], p["y"]); pg.wait_for_timeout(450)
        s2 = st(cid, "#mbBody .mbtbl")
        ok(f"{T} {tab}：再點同一欄 → 取消", s2["sel"] == "" and not s2["hl"] and s2["dim"] == 0, s2)
    # 除權息：點一列＝展開＋選取那一年
    if _lk_tab(pg, "除權息", "mbChart"):
        pg.wait_for_timeout(500)
        row = pg.locator("#mbBody .mbtbl tr.mbdrow").first
        row.scroll_into_view_if_needed(); row.click(); pg.wait_for_timeout(400)
        s1 = st("mbChart", "#mbBody .mbtbl")
        opened = pg.evaluate("() => !document.querySelector('#mbBody .mbtbl tr.mbdrow').nextElementSibling.hidden")
        ok(f"{T} 除權息：點一列 → 展開明細＋選取那一年（圖上那根亮、其他變淡）", opened and s1["sel"] != "" and s1["lit"] >= 1 and s1["dim"] > 0, [opened, s1])
        row.click(); pg.wait_for_timeout(400)
        s2 = st("mbChart", "#mbBody .mbtbl")
        ok(f"{T} 除權息：再點同一列 → 收起＋取消", s2["sel"] == "" and s2["dim"] == 0, s2)
    else:
        ok(f"{T} 除權息：分頁打得開", False)
    ok(f"{T}：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
    c.close()


def t_stock_link_1019(b, base, code):
    errs: list[str] = []
    t_stock_link_desktop(b, base, errs)
    t_stock_link_mobile(b, base, errs)
    ok("個股連動1019：沒有網頁錯誤", not errs, errs[:3])


register("個股連動1019", lambda pg, b, base, code: t_stock_link_1019(b, base, code))
