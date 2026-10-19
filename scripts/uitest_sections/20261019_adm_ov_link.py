# 驗收段落「管理區與總覽連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_adm2_ctx()、HM_LEAF_XY、DNX_PT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 管理區與總覽連動1019（Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」）
# 規格：docs/style_guide.md 第十八節；普查表 docs/chart_link_census_1019.md 第 10、11、12 項＋第二輪第 24 項。全部用真的滑鼠／觸控：
#   #overview（資金熱力圖 ⇄ 迷你資金輪盤）
#     ① 滑過熱力圖族群方塊 → 輪盤同族群亮（_hiGid）、其他點真的變淡；滑開恢復
#     ② 滑過輪盤族群點 → 熱力圖那一塊外框 3px、其他方塊 opacity ≤ .55
#     ③ 點方塊第一下＝鎖定（網址不動、輪盤同族群亮）；點空白＝取消；同一塊點第二下 → 進族群頁
#     ④ 點輪盤族群點＝鎖定（熱力圖那塊外框亮）＋說明框；再點同一顆＝取消
#   #admin/traffic（同一個 .trpair 的長條＋圓餅；個股分頁四處同一組代號）
#     ⑤ 滑過「全部」長條 → 圓餅同頁扇區外框、其他扇區 .55；其他長條 .lkdim 真的 opacity .55
#     ⑥ 滑過圓餅扇區 → 長條那一列 .lkon、其他變淡
#     ⑦ 點長條第一下＝鎖定（還在「全部」），點空白取消，第二下才進該頁
#     ⑧ 子頁：滑過第 6 名以後的長條 → 圓餅「其他」亮
#     ⑨ 個股分頁：滑過功能表那一列 → 散點、被點最多的個股長條同代號亮；點散點＝鎖定，功能表那列 .lksel
#     ⑩ 淺色主題變淡 .35；390 觸控：第一下鎖定、第二下才進該頁；全程沒有網頁錯誤、沒有橫向捲軸

OVL_MINI = """() => { const el = document.getElementById('rotClockMini'), c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const o = c.getOption(), si = o.series.findIndex(s => s.type === 'scatter'); if (si < 0) return null;
  const R = el.getBoundingClientRect();
  const pts = (el._rotHov ? el._rotHov.top : []).map(r => { const pp = r._pt || r.p; let q = null; try { q = c.convertToPixel({ seriesIndex: si }, [pp[0], pp[1]]); } catch (e) {}
    return q ? { gid: r.gid, x: R.left + q[0], y: R.top + q[1], vis: R.left + q[0] > 0 && R.top + q[1] > 70 && R.top + q[1] < innerHeight - 20 } : null; }).filter(Boolean);
  const op = (o.series[si].data || []).map(d => [d.row && d.row.gid, d.itemStyle && d.itemStyle.opacity != null ? d.itemStyle.opacity : 1]);
  return { hi: el._hiGid || null, sel: el.dataset.sel || '', pts, op }; }"""
OVL_HEAT = """() => { const el = document.getElementById('heat'), c = echarts.getInstanceByDom(el); const out = [];
  const walk = (a) => (a || []).forEach(d => { if (d.children) walk(d.children); else if (d.gid) out.push([d.gid, d.itemStyle ? (d.itemStyle.opacity == null ? 1 : d.itemStyle.opacity) : 1, d.itemStyle ? (d.itemStyle.borderWidth || 0) : 0]); });
  walk(c.getOption().series[0].data); return { hi: el.dataset.hi || '', sel: el.dataset.sel || '', leaves: out }; }"""


def _ovl_overview(b, base, T, w, errs, shots):
    c = b.new_context(viewport={"width": w, "height": 900}, has_touch=(w <= 640))
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    agree = pg.get_by_role("button", name="同意並繼續")
    try:
        agree.first.wait_for(state="visible", timeout=2500); agree.first.click(); pg.wait_for_timeout(300)
    except Exception:
        pass
    TT = f"{T}（總覽 {w}）"
    if not ok(f"{TT}：熱力圖與迷你輪盤都畫出來了", bool(wait_until(pg, "() => !!(window.echarts && document.getElementById('heat') && echarts.getInstanceByDom(document.getElementById('heat')) && document.getElementById('rotClockMini') && echarts.getInstanceByDom(document.getElementById('rotClockMini')) && document.getElementById('rotClockMini')._rotHov)", 20000))):
        c.close(); return
    pg.wait_for_timeout(1200)
    ok(f"{TT}：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
    if w <= 640:
        # 手機：熱力圖在「熱度」分頁、輪盤在另一頁，兩張不同屏 → 驗觸控「第一下鎖定、第二下才進族群頁」
        try:
            pg.locator(".mpager button", has_text="熱度").first.tap(); pg.wait_for_timeout(700)
        except Exception:
            pass
        pg.evaluate("() => document.getElementById('heat').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
        lf = (pg.evaluate(HM_LEAF_XY, {"id": "heat"}) or [None])[0]
        if ok(f"{TT}：找得到族群方塊（前提）", bool(lf), lf):
            pg.touchscreen.tap(lf["cx"], lf["cy"]); pg.wait_for_timeout(600)
            h = pg.evaluate(OVL_HEAT)
            ok(f"{TT}：③ 觸控點一下＝鎖定（外框亮、網址仍是 #overview）", h["sel"] == lf["key"] and h["hi"] == lf["key"] and pg.evaluate("location.hash") == "#overview", {"sel": h["sel"], "hash": pg.evaluate("location.hash")})
            pg.touchscreen.tap(lf["cx"], lf["cy"]); pg.wait_for_timeout(1200)
            ok(f"{TT}：同一塊點第二下 → 進族群頁", pg.evaluate("decodeURIComponent(location.hash)").startswith("#industry/group/"), pg.evaluate("location.hash"))
        c.close(); return
    pg.evaluate("() => document.getElementById('heat').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
    m = pg.evaluate(OVL_MINI)
    leaves = pg.evaluate(HM_LEAF_XY, {"id": "heat"}) or []
    ongid = {p["gid"] for p in m["pts"]}
    lf = next((x for x in leaves if x["key"] in ongid and x["cy"] > 80 and x["cy"] < 880), None)
    if not ok(f"{TT}：熱力圖上找得到「輪盤上也有」的族群方塊（前提）", bool(lf), [len(leaves), len(ongid)]):
        c.close(); return
    g = lf["key"]
    # ① 滑過熱力圖方塊 → 輪盤同族群亮、其他變淡
    pg.mouse.move(lf["cx"] - 3, lf["cy"] - 3); pg.mouse.move(lf["cx"], lf["cy"], steps=3); pg.wait_for_timeout(500)
    m = pg.evaluate(OVL_MINI)
    own = [o for gg, o in m["op"] if gg == g]; oth = [o for gg, o in m["op"] if gg and gg != g]
    ok(f"{TT}：① 滑過熱力圖「{lf['name']}」→ 輪盤同族群亮、其他點變淡", m["hi"] == g and own and own[0] == 1 and oth and max(oth) < 1, {"hi": m["hi"], "own": own[:1], "oth": oth[:4]})
    if shots:
        pg.screenshot(path=os.path.join(shots, "adm_ov_link_ov_hover.png"))
    pg.mouse.move(4, 450); pg.wait_for_timeout(450)
    ok(f"{TT}：滑開 → 輪盤全部恢復", pg.evaluate(OVL_MINI)["hi"] is None)
    # ② 滑過輪盤族群點 → 熱力圖那一塊外框亮、其他變淡
    pg.evaluate("() => document.getElementById('rotClockMini').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
    m = pg.evaluate(OVL_MINI)
    hgids = {x[0] for x in pg.evaluate(OVL_HEAT)["leaves"]}
    pt = next((p for p in m["pts"] if p["vis"] and p["gid"] in hgids), None)
    if ok(f"{TT}：輪盤上找得到熱力圖也有的族群點（前提）", bool(pt), m["pts"][:3]):
        pg.mouse.move(pt["x"] - 4, pt["y"] - 4); pg.mouse.move(pt["x"], pt["y"], steps=3); pg.wait_for_timeout(500)
        h = pg.evaluate(OVL_HEAT)
        own = [x for x in h["leaves"] if x[0] == pt["gid"]]; oth = [x[1] for x in h["leaves"] if x[0] != pt["gid"]]
        ok(f"{TT}：② 滑過輪盤族群點 → 熱力圖那一塊外框 3px、其他方塊 ≤ .55", h["hi"] == pt["gid"] and own and own[0][2] == 3 and own[0][1] == 1 and oth and max(oth) <= 0.551, {"hi": h["hi"], "own": own[:1], "max": max(oth) if oth else None})
        pg.mouse.move(4, 450); pg.wait_for_timeout(450)
        h = pg.evaluate(OVL_HEAT)
        ok(f"{TT}：滑開輪盤 → 熱力圖全部恢復（沒有外框、沒有變淡）", h["hi"] == "" and all(x[2] == 0 and x[1] == 1 for x in h["leaves"]), h["hi"])
        # ④ 點輪盤族群點＝鎖定＋說明框；再點同一顆＝取消
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(600)
        pop = pg.evaluate("() => { const p = document.getElementById('ovRotPop'); return !!p && !p.hidden; }")
        pg.mouse.move(4, 450); pg.wait_for_timeout(400)
        h = pg.evaluate(OVL_HEAT)
        ok(f"{TT}：④ 點輪盤族群點＝鎖定（滑開後熱力圖那塊仍外框亮）、說明框浮出", h["sel"] == pt["gid"] and h["hi"] == pt["gid"] and pop, {"sel": h["sel"], "pop": pop})
        if shots:
            pg.screenshot(path=os.path.join(shots, "adm_ov_link_ov_lock.png"))
        under = pg.evaluate(f"() => {{ const e = document.elementFromPoint({pt['x']}, {pt['y']}); return e ? (e.id || e.tagName) + '/' + ((e.closest('[id]') || {{}}).id || '') : ''; }}")
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(400)
        pg.mouse.move(4, 450); pg.wait_for_timeout(400)   # 滑鼠還停在點上＝滑過狀態（外框會亮），移開才看得到「取消鎖定」
        h = pg.evaluate(OVL_HEAT)
        ok(f"{TT}：再點同一顆 → 取消鎖定、說明框收起", h["sel"] == "" and h["hi"] == "" and pg.evaluate("() => { const p = document.getElementById('ovRotPop'); return !p || p.hidden; }"), [h["sel"], under, pt])
    # ③ 點熱力圖方塊＝鎖定；點空白取消；第二下進族群頁
    pg.evaluate("() => document.getElementById('heat').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
    lf = next((x for x in (pg.evaluate(HM_LEAF_XY, {"id": "heat"}) or []) if x["key"] == g), lf)
    pg.mouse.click(lf["cx"], lf["cy"]); pg.wait_for_timeout(600)
    pg.mouse.move(4, 450); pg.wait_for_timeout(450)
    h = pg.evaluate(OVL_HEAT); m = pg.evaluate(OVL_MINI)
    ok(f"{TT}：③ 點方塊第一下＝鎖定（網址不動、外框亮、輪盤同族群亮）", h["sel"] == g and h["hi"] == g and m["hi"] == g and pg.evaluate("location.hash") == "#overview", {"sel": h["sel"], "mini": m["hi"], "hash": pg.evaluate("location.hash")})
    pg.locator("#ovHeatCard h3").first.click(); pg.wait_for_timeout(500)
    h = pg.evaluate(OVL_HEAT); m = pg.evaluate(OVL_MINI)
    ok(f"{TT}：點空白（卡片標題）→ 取消鎖定、兩張圖全部恢復", h["sel"] == "" and h["hi"] == "" and m["hi"] is None, {"sel": h["sel"], "mini": m["hi"]})
    lf = next((x for x in (pg.evaluate(HM_LEAF_XY, {"id": "heat"}) or []) if x["key"] == g), lf)
    pg.mouse.click(lf["cx"], lf["cy"]); pg.wait_for_timeout(450); pg.mouse.click(lf["cx"], lf["cy"]); pg.wait_for_timeout(1200)
    ok(f"{TT}：同一塊點第二下 → 進族群頁（原本的點擊行為）", pg.evaluate("decodeURIComponent(location.hash)") == "#industry/group/" + g, pg.evaluate("location.hash"))
    c.close()


ADL = """(sel) => { const g = document.querySelector(sel); if (!g) return null; const dn = g.querySelector('.dnc[data-spec]'), c = dn && echarts.getInstanceByDom(dn);
  const o = c ? c.getOption() : null, d = o ? o.series[0].data : [];
  const op = (e) => +getComputedStyle(e).opacity;
  return { sel: g.dataset.sel || '', act: g.dataset.act || '',
    dn: d.map(x => ({ name: x.name, lk: x.lk, op: x.itemStyle.opacity == null ? 1 : x.itemStyle.opacity, bw: x.itemStyle.borderWidth })),
    title: o ? (o.title || []).flatMap(t => String(t.text).replace(/\\{\\w+\\|([^}]*)\\}/g, '$1').split('\\n')) : [],
    on: [...g.querySelectorAll('.lkon')].map(e => e.tagName.toLowerCase() + ':' + e.dataset.lk),
    lsel: [...g.querySelectorAll('.lksel')].map(e => e.tagName.toLowerCase() + ':' + e.dataset.lk),
    dim: g.querySelectorAll('.lkdim').length, dimOp: [...g.querySelectorAll('.bars .lkdim, tr.lkdim, circle.lkdim')].slice(0, 3).map(op),
    tab: (document.querySelector('#trTabs button.on') || {}).dataset ? document.querySelector('#trTabs button.on').dataset.t : '' }; }"""


def _ovl_admin(b, base, T, w, theme, errs, shots):
    pbase = base.replace("/index.html", "/preview/style-guide/index.html")
    touch = w <= 640
    c, _sent = _adm2_ctx(b, width=w, touch=touch, many=True)
    c.add_init_script(f"try{{localStorage.setItem('tw.theme','{theme}');localStorage.setItem('tw.tour','done');}}catch(e){{}}")
    c.route(re.compile(r".*/preview/style-guide/.*"), lambda r: r.continue_(url=r.request.url.replace("/preview/style-guide/", "/")))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(pbase + "#admin/traffic", wait_until="domcontentloaded")
    TT = f"{T}（管理區 {w}・{theme}）"
    if not ok(f"{TT}：流量觀測「全部」長條＋圓餅畫出來了", bool(wait_until(pg, "() => !!document.querySelector('#trAllB .bl[data-lk]') && !!(window.echarts && echarts.getInstanceByDom(document.querySelector('#trAllDonut .dnc')))", 15000))):
        c.close(); return
    pg.wait_for_timeout(500)
    G = "#trPageBody .lkbox"
    dimv = 0.35 if theme == "light" else 0.55
    if touch:
        ok(f"{TT}：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        bl = pg.locator("#trAllB .bt[data-lk] >> nth=0"); bl.scroll_into_view_if_needed(); k = bl.get_attribute("data-lk")
        bl.tap(); pg.wait_for_timeout(500)
        s = pg.evaluate(ADL, G)
        ok(f"{TT}：⑩ 觸控點長條第一下＝鎖定（圓餅同頁亮、還在「全部」）", s["sel"] == k and s["tab"] == "all" and any(x["lk"] == k and x["bw"] == 3 for x in s["dn"]), {"sel": s["sel"], "tab": s["tab"]})
        pg.locator("#trDetailTtl").tap(); pg.wait_for_timeout(400)
        s = pg.evaluate(ADL, G)
        ok(f"{TT}：點空白 → 取消鎖定、沒有變淡", s["sel"] == "" and s["dim"] == 0, s["sel"])
        bl.tap(); pg.wait_for_timeout(500); bl.tap(); pg.wait_for_timeout(700)
        ok(f"{TT}：同一條點第二下 → 進該頁", pg.evaluate("() => document.querySelector('#trTabs button.on').dataset.t") == k)
        c.close(); return
    # ⑤ 滑過長條 → 圓餅同頁扇區外框、其他變淡
    pg.locator("#trAllB .bl[data-lk='flow']").scroll_into_view_if_needed()
    pg.locator("#trAllB .bl[data-lk='flow']").hover(); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, G)
    own = [x for x in s["dn"] if x["lk"] == "flow"]; oth = [x["op"] for x in s["dn"] if x["lk"] != "flow"]
    ok(f"{TT}：⑤ 滑過「資金流向」長條 → 圓餅那一塊外框、其他扇區 {dimv}；其他長條真的變淡 {dimv}",
       own and own[0]["bw"] == 3 and own[0]["op"] == 1 and oth and all(abs(o - dimv) < 0.01 for o in oth) and s["dimOp"] and all(abs(o - dimv) < 0.02 for o in s["dimOp"]) and s["title"][:1] == [own[0]["name"]],
       {"own": own, "oth": oth, "dimOp": s["dimOp"], "title": s["title"]})
    if theme == "light":
        c.close(); return
    if shots and w >= 1440:
        pg.screenshot(path=os.path.join(shots, "adm_ov_link_adm_hover.png"))
    pg.mouse.move(4, 4); pg.wait_for_timeout(300)
    s = pg.evaluate(ADL, G)
    ok(f"{TT}：滑開 → 長條與圓餅都恢復", s["act"] == "" and s["dim"] == 0 and all(x["op"] == 1 for x in s["dn"]), s["act"])
    # ⑥ 滑過圓餅扇區 → 長條那一列亮
    dd = _dnx(pg, "#trAllDonut")
    ix = next(i for i, d in enumerate(dd["data"]) if d["p"] == "stock")
    _dnx_hover(pg, "#trAllDonut", ix)
    s = pg.evaluate(ADL, G)
    ok(f"{TT}：⑥ 滑過圓餅「個股」扇區 → 長條那一列 .lkon、其他列變淡", "button:stock" in s["on"] and "span:stock" in s["on"] and s["dim"] > 3, s["on"])
    pg.mouse.move(4, 4); pg.wait_for_timeout(300)
    # ⑦ 點長條＝鎖定；點空白取消；第二下進該頁
    bl = pg.locator("#trAllB .bl[data-lk='flow']")
    bl.click(); pg.mouse.move(4, 4); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, G)
    ok(f"{TT}：⑦ 點長條第一下＝鎖定（滑開後仍亮、還在「全部」、長條外框）", s["sel"] == "flow" and s["tab"] == "all" and "span:flow" in s["lsel"] and s["dim"] > 3 and any(x["lk"] == "flow" and x["bw"] == 3 for x in s["dn"]), s)
    if shots and w >= 1440:
        pg.screenshot(path=os.path.join(shots, "adm_ov_link_adm_lock.png"))
    pg.locator("#trDetailTtl h2").click(); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, G)
    ok(f"{TT}：點空白（分頁統計標題）→ 取消鎖定", s["sel"] == "" and s["dim"] == 0 and not s["lsel"], s["sel"])
    # 點圓餅扇區第一下＝鎖定、第二下進該頁
    pt = pg.evaluate(DNX_PT, ["#trAllDonut", ix]); pg.mouse.move(pt[0], pt[1], steps=3); pg.mouse.click(pt[0], pt[1]); pg.wait_for_timeout(500)
    s = pg.evaluate(ADL, G)
    ok(f"{TT}：點圓餅扇區第一下＝鎖定（長條「個股」那列 .lksel、還在「全部」）", s["sel"] == "stock" and s["tab"] == "all" and "button:stock" in s["lsel"], {"sel": s["sel"], "tab": s["tab"]})
    bl.click(); pg.wait_for_timeout(450); bl.click(); pg.wait_for_timeout(600)
    ok(f"{TT}：換點別條＝改鎖那條；同一條第二下 → 進資金流向分頁", pg.evaluate("() => document.querySelector('#trTabs button.on').dataset.t") == "flow")
    # ⑧ 子頁：第 6 名以後的長條 → 圓餅「其他」亮
    wait_until(pg, "() => document.querySelectorAll('#trFBars .bl[data-lk]').length >= 6 && !!echarts.getInstanceByDom(document.querySelector('#trFD .dnc'))", 5000)
    pg.wait_for_timeout(300)
    r6 = pg.locator("#trFBars .bl[data-lk] >> nth=6"); r6.scroll_into_view_if_needed(); r6.hover(); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, "#trPageBody .lkbox:has(#trFBars)")
    oth = [x for x in s["dn"] if x["lk"] == "__other"]
    ok(f"{TT}：⑧ 子頁滑過第 7 名長條 → 圓餅「其他」那塊亮、中心字＝其他", oth and oth[0]["op"] == 1 and oth[0]["bw"] == 3 and s["title"] and s["title"][0].startswith("其他"), {"oth": oth, "title": s["title"]})
    pg.mouse.move(4, 4)
    # ⑨ 個股分頁：功能表 ⇄ 散點 ⇄ 被點最多的個股
    pg.click("#trTabs [data-t=stock]")
    wait_until(pg, "() => !!document.querySelector('#trStockFeat tr[data-lk]') && !!document.querySelector('#trSc circle[data-lk]') && !!document.querySelector('#trDBars .bt[data-lk]')", 6000)
    pg.wait_for_timeout(400)
    tr = pg.locator("#trStockFeat tr[data-lk] >> nth=1"); code = tr.get_attribute("data-lk")
    tr.scroll_into_view_if_needed(); tr.hover(); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, "#trPageBody .lkgrp")
    ok(f"{TT}：⑨ 滑過功能表「{code}」那一列 → 散點那一顆、被點最多的個股長條同代號亮，其他變淡", f"circle:{code}" in s["on"] and f"span:{code}" in s["on"] and f"tr:{code}" in s["on"] and s["dim"] > 10, s["on"])
    cc = pg.locator(f"#trSc circle[data-lk='{code}']")
    box = cc.bounding_box(); pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2); pg.mouse.move(4, 4); pg.wait_for_timeout(400)
    s = pg.evaluate(ADL, "#trPageBody .lkgrp")
    ok(f"{TT}：點散點＝鎖定 → 功能表那一列 .lksel、長條 .lksel、圓餅同代號外框", s["sel"] == code and f"tr:{code}" in s["lsel"] and f"span:{code}" in s["lsel"] and any(x["lk"] == code and x["bw"] == 3 for x in s["dn"]), {"sel": s["sel"], "lsel": s["lsel"]})
    if shots and w >= 1440:
        pg.screenshot(path=os.path.join(shots, "adm_ov_link_adm_stock.png"), full_page=False)
    pg.locator("#trDetailTtl h2").click(); pg.wait_for_timeout(300)
    ok(f"{TT}：點空白 → 個股分頁四處都恢復", pg.evaluate(ADL, "#trPageBody .lkgrp")["dim"] == 0)
    c.close()


def t_adm_ov_link_1019(b, base, code):
    T = "管理區與總覽連動1019"
    errs: list[str] = []
    shots = os.environ.get("TW_ADMOV_SHOT")
    for w in (1440, 390):
        _ovl_overview(b, base, T, w, errs, shots)
        _ovl_admin(b, base, T, w, "dark", errs, shots)
    _ovl_admin(b, base, T, 1440, "light", errs, None)
    ok(f"{T}：整段沒有網頁錯誤", not errs, errs[:3])


register("管理區與總覽連動1019", lambda pg, b, base, code: t_adm_ov_link_1019(b, base, code))
