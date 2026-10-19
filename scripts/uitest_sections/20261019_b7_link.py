# 驗收段落「第七批連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、click()、_rel_goto()、_rl_pick()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 第七批連動1019
# Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」「避免我重複下指令」。
# 普查 docs/chart_link_census_1019.md 第二輪第 17、18、19、23 項；規格 docs/style_guide.md 第十八節。全部用真的滑鼠／觸控，每一步量畫面真的變了：
#   17（1440）個股頁 HTML 圖例（營收）與大戶散戶色塊：滑過一顆 → 圖上那個系列 highlight（data-leg-hi＝那個名字），
#          畫布像素真的變了（其他系列變淡）；滑出 → 恢復（像素回到滑過之前）；點擊開關照舊（aria-pressed／data-ho-lines 真的變）。
#   18（1440）四週期同看：游標在日線那格 → 其他三格的十字線放到「包含那一天的那一根」，各自的看板寫出那一根的日期
#          （週／月 K 的日期 ≥ 那一天、且在同一週／同一月）；換到別格當來源也成立；滑出 → 其他格看板收掉。
#   19（1440）產業鏈關聯圖 ⇄ 右欄環節清單：滑過右欄列 → 圖上那張卡 .lkhl、連線提亮；滑過圖上的卡 → 右欄那一列 .hl；
#          點右欄列第一下＝選取（還在本頁、列 .lk、滑開後卡片仍亮），點空白＝取消；第二下才進個股頁。
#   23（390 手機）#flow：手機 v2（m4）實際畫的是桌機那棵樹＋#sankeyRank（mobile3.js 的長條替身 10-09 起在 m4 不畫）——
#          觸控點排名列第一下＝鎖定（樹上突顯、頁面不捲動、面板沒開），點空白取消，第二下開成分股面板；並確認舊替身沒冒出來。
#   管理區（1440）流量觀測「使用者」：時段直條 ⇄ 24 小時時鐘，同一個小時互亮、點擊鎖定（切 4H 保留、亮包含那小時的那一格）、點空白取消。
#   全程沒有網頁錯誤、390 沒有橫向捲軸。截圖：設 TW_B7_SHOT＝資料夾，存 b7_link_*.png。

_B7_CANVAS = """(id) => { const el = document.getElementById(id); const cv = el && el.querySelector('canvas'); if (!cv) return null;
  const g = cv.getContext('2d'), W = cv.width, H = cv.height, d = g.getImageData(0, 0, W, H).data, out = [];
  for (let y = 0; y < 24; y++) for (let x = 0; x < 24; x++) { let s = 0; const x0 = Math.floor(x * W / 24), y0 = Math.floor(y * H / 24), x1 = Math.floor((x + 1) * W / 24), y1 = Math.floor((y + 1) * H / 24);
    for (let yy = y0; yy < y1; yy += 2) for (let xx = x0; xx < x1; xx += 2) { const i = (yy * W + xx) * 4; s += d[i] + d[i + 1] + d[i + 2]; } out.push(s); }
  return out; }"""


def _b7_diff(a, b):
    if not a or not b or len(a) != len(b):
        return -1
    return sum(1 for x, y in zip(a, b) if abs(x - y) > max(50, 0.02 * max(x, y)))


def _b7_open(b, base, w, hash_, errs, extra=""):
    mob = w <= 640
    c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, is_mobile=mob, has_touch=mob)
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');" + extra + "}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
    pg.goto(base + hash_, wait_until="domcontentloaded")
    agree = pg.get_by_role("button", name="同意並繼續")
    try:
        agree.first.wait_for(state="visible", timeout=2500); agree.first.click(); pg.wait_for_timeout(300)
    except Exception:
        pass
    return c, pg


def _b7_center(pg, sel, idx=0):
    return pg.evaluate("""(a) => { const e = document.querySelectorAll(a[0])[a[1]]; if (!e) return null;
      e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }""", [sel, idx])


_B7_NATLEG = """(a) => { const [id, name] = a; const el = document.getElementById(id); el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect(); let best = null;
  ch.getZr().storage.getDisplayList().forEach(d => { if (!d.style || d.style.text !== name) return;
    const b = d.getBoundingRect().clone(); b.applyTransform(d.getComputedTransform());
    if (!best || b.y < best.y) best = b; });
  return best ? { x: r.left + best.x + best.width / 2, y: r.top + best.y + best.height / 2 } : null; }"""


def _b7_leg_one(pg, T, cid, nm, pos, errs):
    """滑過一個圖例項目（pos＝螢幕座標）：量 highlight 名字與畫布像素；滑出恢復。回傳是否兩條都綠。"""
    pg.mouse.move(5, 450); pg.wait_for_timeout(600)
    c0 = pg.evaluate(_B7_CANVAS, cid)
    pg.mouse.move(pos["x"], pos["y"]); pg.wait_for_timeout(700)
    hi = pg.evaluate(f"() => document.getElementById('{cid}').dataset.legHi || ''")
    d1 = _b7_diff(c0, pg.evaluate(_B7_CANVAS, cid))
    a = ok(f"{T}：滑過圖例「{nm}」→ 圖上那個系列 highlight、其他變淡（畫布 {d1} 格變了）", hi == nm and d1 >= 8, [hi, d1])
    pg.mouse.move(5, 450); pg.wait_for_timeout(900)
    hi2 = pg.evaluate(f"() => document.getElementById('{cid}').dataset.legHi || ''")
    d2 = _b7_diff(c0, pg.evaluate(_B7_CANVAS, cid))
    z = ok(f"{T}：滑出「{nm}」→ 恢復（highlight 清掉、畫布跟滑過前只差 {d2} 格）", hi2 == "" and 0 <= d2 <= 3, [hi2, d2])
    return a and z


def _b7_legend(b, base, errs, shots):
    T = "第七批連動1019 17 圖例滑過（1440）"
    c, pg = _b7_open(b, base, 1440, "#stock/2330", errs, "localStorage.setItem('tw.revView','m');localStorage.setItem('tw.chipWinHo','63')")
    wait_until(pg, "() => document.querySelectorAll('#stockTabs button').length > 0", 15000)
    # ---- 獲利：HTML 圖例（.chlegend，標題列右端那一排）
    pg.locator("#stockTabs button", has_text="獲利").first.click()
    if wait_until(pg, "() => { const b = document.querySelector('.chlegend[data-for=\"profitChart\"]'); return !!b && !b.hidden && b.querySelectorAll('button[data-n]').length >= 2; }", 10000):
        pg.wait_for_timeout(900)
        btns = pg.evaluate("() => [...document.querySelectorAll('.chlegend[data-for=\"profitChart\"] button[data-n]')].map(b => b.dataset.n)")
        nm = btns[1]
        loc = pg.locator(f'.chlegend[data-for="profitChart"] button[data-n="{nm}"]')
        loc.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
        bx = loc.bounding_box()
        _b7_leg_one(pg, T + " 獲利 HTML 圖例", "profitChart", nm, {"x": bx["x"] + bx["width"] / 2, "y": bx["y"] + bx["height"] / 2}, errs)
        if shots:
            pg.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2); pg.wait_for_timeout(600)
            pg.screenshot(path=os.path.join(shots, "b7_link_legend_1440.png")); pg.mouse.move(5, 450); pg.wait_for_timeout(500)
        loc.click(); pg.wait_for_timeout(500); p1 = loc.get_attribute("aria-pressed")
        loc.click(); pg.wait_for_timeout(500); p2 = loc.get_attribute("aria-pressed")
        ok(f"{T}：點擊開關照舊（關 → aria-pressed {p1}；再點 → {p2}）", p1 == "false" and p2 == "true", [p1, p2])
    else:
        ok(f"{T}：獲利 HTML 圖例畫出來了", False)
    # ---- 營收：1440 這一列放不下、退回 ECharts 自己的圖例（extLegFit wrap）—— 滑過一樣要有連動
    pg.locator("#stockTabs button", has_text="營收").first.click()
    if wait_until(pg, "() => !!window.echarts && !!echarts.getInstanceByDom(document.getElementById('revBar'))", 10000):
        pg.wait_for_timeout(1200)
        mode = pg.evaluate("() => { const b = document.querySelector('.chlegend[data-for=\"revBar\"]'); return b ? b.dataset.fit : 'none'; }")
        nm = pg.evaluate("() => { const o = echarts.getInstanceByDom(document.getElementById('revBar')).getOption(); return o.series[o.series.length - 1].name; }")
        if mode == "wrap":
            pos = pg.evaluate(_B7_NATLEG, ["revBar", nm])
        else:
            bx = pg.locator(f'.chlegend[data-for="revBar"] button[data-n="{nm}"]').bounding_box()
            pos = {"x": bx["x"] + bx["width"] / 2, "y": bx["y"] + bx["height"] / 2} if bx else None
        if ok(f"{T}：營收圖例（{mode}）找得到「{nm}」", bool(pos), mode):
            _b7_leg_one(pg, T + f" 營收（{'ECharts 圖例' if mode == 'wrap' else 'HTML 圖例'}）", "revBar", nm, pos, errs)
    else:
        ok(f"{T}：營收圖畫出來了", False)
    # ---- 大戶／散戶：三顆色塊（.hoTgl）
    pg.locator("#stockTabs button", has_text="大戶").first.click()
    if wait_until(pg, "() => !!document.querySelector('#hoTgls .hoTgl') && !!echarts.getInstanceByDom(document.getElementById('holderChart'))", 10000):
        pg.wait_for_timeout(900)
        pg.evaluate("() => document.getElementById('holderChart').scrollIntoView({ block: 'center', behavior: 'instant' })"); pg.wait_for_timeout(400)
        pg.mouse.move(5, 450); pg.wait_for_timeout(500)
        h0 = pg.evaluate(_B7_CANVAS, "holderChart")
        bb = pg.locator("#hoTgls .hoTgl").nth(0).bounding_box()
        pg.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(700)
        hi = pg.evaluate("() => document.getElementById('holderChart').dataset.legHi || ''")
        h1 = pg.evaluate(_B7_CANVAS, "holderChart")
        dh = _b7_diff(h0, h1)
        ok(f"{T}：大戶散戶 滑過第一顆色塊 → 那一格的線亮、其他兩格變淡（{hi}，畫布 {dh} 格變了）", hi != "" and dh >= 8, [hi, dh])
        if shots:
            pg.screenshot(path=os.path.join(shots, "b7_link_holder_1440.png"))
        pg.mouse.move(5, 450); pg.wait_for_timeout(800)
        dh2 = _b7_diff(h0, pg.evaluate(_B7_CANVAS, "holderChart"))
        ok(f"{T}：大戶散戶 滑出 → 恢復（差 {dh2} 格）", pg.evaluate("() => document.getElementById('holderChart').dataset.legHi || ''") == "" and 0 <= dh2 <= 3, dh2)
        l0 = pg.evaluate("() => document.getElementById('stockTab').dataset.hoLines || ''")
        pg.locator("#hoTgls .hoTgl").nth(0).click(); pg.wait_for_timeout(700)
        l1 = pg.evaluate("() => document.getElementById('stockTab').dataset.hoLines || ''")
        pg.locator("#hoTgls .hoTgl").nth(0).click(); pg.wait_for_timeout(700)
        l2 = pg.evaluate("() => document.getElementById('stockTab').dataset.hoLines || ''")
        ok(f"{T}：大戶散戶 點色塊開關照舊（{l0} → {l1} → {l2}）", l0 != l1 and l2 == l0, [l0, l1, l2])
    else:
        ok(f"{T}：大戶散戶分頁打得開", False)
    c.close()


_B7_MTF = """() => { const g = document.getElementById('mtfGrid'); if (!g) return null;
  return { sync: g.dataset.sync || '', tf: [...g.querySelectorAll('.mtf-cell')].map(c => c.dataset.tf),
    tips: [...g.querySelectorAll('.mtip')].map(t => t.hidden ? '' : (t.dataset.k || '')) }; }"""


def _b7_mtf(b, base, errs, shots):
    T = "第七批連動1019 18 四週期十字線（1440）"
    c, pg = _b7_open(b, base, 1440, "#stock/2330", errs, "localStorage.setItem('tw.kcfg', JSON.stringify({mtfTfs:['1d','1w','1M','60m']}))")
    wait_until(pg, "() => !!document.getElementById('mtfBtn')", 15000)
    pg.click("#mtfBtn")
    if not wait_until(pg, "() => document.querySelectorAll('#mtfGrid .mtf-cell canvas').length >= 4 && [0,1,2,3].every(i => document.querySelector('#mini-' + i + ' canvas'))", 12000):
        ok(f"{T}：四格都畫出來了", False); c.close(); return
    pg.wait_for_timeout(1200)
    s0 = pg.evaluate(_B7_MTF)
    ok(f"{T}：四格週期 {s0['tf']}", s0["tf"][:3] == ["1d", "1w", "1M"], s0)
    pg.evaluate("() => document.getElementById('mtfGrid').scrollIntoView({ block: 'start', behavior: 'instant' })"); pg.wait_for_timeout(400)
    r = pg.evaluate("() => { const r = document.getElementById('mini-0').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }")
    pg.mouse.move(r["x"] + r["w"] * 0.4, r["y"] + r["h"] * 0.3); pg.wait_for_timeout(150)
    pg.mouse.move(r["x"] + r["w"] * 0.45, r["y"] + r["h"] * 0.3); pg.wait_for_timeout(450)
    s1 = pg.evaluate(_B7_MTF)
    d0 = s1["tips"][0]
    import datetime as _dt
    def _okw(src, t, tf):
        if not src or not t:
            return False
        a = _dt.date.fromisoformat(src[:10]); z = _dt.date.fromisoformat(t[:10])
        if tf == "1w":
            return z >= a and (z - a).days <= 6 and z.isocalendar()[:2] == a.isocalendar()[:2]
        if tf == "1M":
            return z >= a and z.strftime("%Y-%m") == a.strftime("%Y-%m")
        return t[:10] == src[:10] or (tf == "60m" and z <= a)
    good = [_okw(d0, s1["tips"][j], s0["tf"][j]) for j in (1, 2)]
    ok(f"{T}：游標在日線 {d0} → 週線格十字線在 {s1['tips'][1]}、月線格在 {s1['tips'][2]}（包含那一天的那一根）",
       bool(d0) and all(good) and s1["sync"].startswith("0@"), s1)
    h60 = s1["tips"][3]
    ok(f"{T}：1 小時格：有涵蓋那一天就放到那天最後一根（{h60 or '沒涵蓋→收掉'}）", (h60 == "" ) or h60[:10] == d0[:10], s1)
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_mtf_1440.png"))
    # 換週線格當來源
    r1 = pg.evaluate("() => { const r = document.getElementById('mini-1').getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }")
    pg.mouse.move(r1["x"] + r1["w"] * 0.5, r1["y"] + r1["h"] * 0.3); pg.wait_for_timeout(150)
    pg.mouse.move(r1["x"] + r1["w"] * 0.55, r1["y"] + r1["h"] * 0.3); pg.wait_for_timeout(450)
    s2 = pg.evaluate(_B7_MTF)
    w0 = s2["tips"][1]
    ok(f"{T}：游標換到週線 {w0} → 日線格放到那一天、月線格放到那個月（{s2['tips'][0]}／{s2['tips'][2]}）",
       bool(w0) and s2["tips"][0][:10] >= w0[:10] and s2["tips"][2][:7] == w0[:7] and s2["sync"].startswith("1@"), s2)
    pg.mouse.move(5, 300); pg.wait_for_timeout(450)
    s3 = pg.evaluate(_B7_MTF)
    ok(f"{T}：滑出四格 → 其他格十字線收掉（看板都藏起來、sync 清空）", s3["sync"] == "" and not any(s3["tips"]), s3)
    c.close()


_B7_REL = """() => { const rm = document.getElementById('relMain'); if (!rm) return null;
  return { sel: rm.dataset.rlSel || '', hov: rm.dataset.rlHov || '',
    rowHl: [...rm.querySelectorAll('#relList .rlco.hl')].map(r => r.dataset.code), rowLk: [...rm.querySelectorAll('#relList .rlco.lk')].map(r => r.dataset.code),
    card: [...rm.querySelectorAll('.chainmap .co.lkhl')].map(n => n.dataset.code), edgeHi: rm.querySelectorAll('.chainmap .edge.hi').length,
    stroke: (() => { const n = rm.querySelector('.chainmap .co.lkhl rect'); return n ? getComputedStyle(n).stroke : ''; })(),
    hash: location.hash }; }"""


def _b7_rel(b, base, errs, shots):
    T = "第七批連動1019 19 關聯圖⇄右欄（1440）"
    c, pg = _b7_open(b, base, 1440, "#overview", errs)
    _rel_goto(pg, base, chain="ai_server", w=1440, view="layer", fold="1")
    pg.evaluate("() => { const s = document.getElementById('side'); if (s) s.classList.remove('open'); }")
    seg = pg.evaluate("""() => { const map = document.getElementById('chainMap');
      const c = [...document.querySelectorAll('#segChips .segchip:not(.nomem)')].find(s => map.querySelector('.co[data-segment="' + s.dataset.seg + '"][data-code]:not([data-code=""])'));
      return c ? c.dataset.seg : null; }""")
    if not ok(f"{T}：找得到有台股的環節", bool(seg)):
        c.close(); return
    _rl_pick(pg, seg, 1200)
    pg.evaluate("document.getElementById('relSec').scrollIntoView({block:'start'}); window.scrollBy({top:-70, behavior:'instant'})"); pg.wait_for_timeout(500)
    code = pg.evaluate("""(seg) => { const map = document.getElementById('chainMap');
      const r = [...document.querySelectorAll('#relList .rlseg.on .rlco[data-code]')].find(a => map.querySelector('.co[data-code="' + a.dataset.code + '"]'));
      return r ? r.dataset.code : null; }""", seg)
    if not ok(f"{T}：右欄有在圖上也畫著的個股", bool(code)):
        c.close(); return
    pg.mouse.move(5, 300); pg.wait_for_timeout(300)
    s0 = pg.evaluate(_B7_REL)
    p = pg.evaluate("(c) => { const r = document.querySelector('#relList .rlseg.on .rlco[data-code=\"' + c + '\"]').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }", code)
    pg.mouse.move(p["x"], p["y"]); pg.wait_for_timeout(400)
    s1 = pg.evaluate(_B7_REL)
    ok(f"{T}：滑過右欄 {code} → 圖上那張卡亮琥珀框（{s1['stroke']}）、連線提亮 {s1['edgeHi']} 條、那一列 .hl",
       code in s1["card"] and s1["rowHl"] == [code] and s1["hov"] == code and s1["stroke"] != s0["stroke"] and not s0["card"], [s0, s1])
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_rel_1440.png"))
    pg.mouse.move(5, 300); pg.wait_for_timeout(400)
    s2 = pg.evaluate(_B7_REL)
    ok(f"{T}：滑出 → 卡與列都恢復", not s2["card"] and not s2["rowHl"] and s2["edgeHi"] == 0, s2)
    # 滑過圖上的卡 → 右欄那一列 .hl
    q = pg.evaluate("""(c) => { const n = document.querySelector('#chainMap .co[data-code="' + c + '"]'); const r = n.getBoundingClientRect();
      return { x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2, vis: r.top > 60 && r.bottom < innerHeight }; }""", code)
    if not q["vis"]:
        pg.evaluate("(c) => document.querySelector('#chainMap .co[data-code=\"' + c + '\"]').scrollIntoView({block:'center', behavior:'instant'})", code)
        pg.wait_for_timeout(300)
        q = pg.evaluate("""(c) => { const n = document.querySelector('#chainMap .co[data-code="' + c + '"]'); const r = n.getBoundingClientRect();
          return { x: r.left + Math.min(20, r.width / 2), y: r.top + r.height / 2 }; }""", code)
    pg.mouse.move(q["x"], q["y"]); pg.wait_for_timeout(400)
    s3 = pg.evaluate(_B7_REL)
    ok(f"{T}：滑過圖上 {code} 的卡 → 右欄那一列 .hl", s3["rowHl"] == [code] and s3["hov"] == code, s3)
    pg.mouse.move(5, 300); pg.wait_for_timeout(300)
    # 點右欄列：第一下選取
    pg.evaluate("document.getElementById('relSec').scrollIntoView({block:'start'}); window.scrollBy({top:-70, behavior:'instant'})"); pg.wait_for_timeout(300)
    row = pg.locator(f'#relList .rlseg.on .rlco[data-code="{code}"]')
    row.click(); pg.wait_for_timeout(400); pg.mouse.move(5, 300); pg.wait_for_timeout(300)
    s4 = pg.evaluate(_B7_REL)
    ok(f"{T}：點右欄 {code} 第一下 → 選取（還在本頁 {s4['hash']}、列 .lk、滑開後圖上那張卡仍亮）",
       s4["hash"].startswith("#industry/") and s4["sel"] == code and s4["rowLk"] == [code] and code in s4["card"], s4)
    pg.locator("#relHead h4").click(position={"x": 4, "y": 6}); pg.wait_for_timeout(400)
    s5 = pg.evaluate(_B7_REL)
    ok(f"{T}：點空白（關聯圖標題）→ 取消選取", s5["sel"] == "" and not s5["rowLk"] and not s5["card"], s5)
    row = pg.locator(f'#relList .rlseg.on .rlco[data-code="{code}"]')
    if row.count() and row.first.is_visible():
        row.first.click(); pg.wait_for_timeout(300)
        row.first.click(); pg.wait_for_timeout(1500)
        ok(f"{T}：同一列點第二下 → 進 {code} 個股頁", pg.evaluate("location.hash") == f"#stock/{code}", pg.evaluate("location.hash"))
    else:
        ok(f"{T}：取消選取後右欄列還在（可以再點）", False)
    c.close()


_B7_MF = """() => { const bx = document.getElementById('sankeyRank'), t = window.App && App.sankeyTopo ? App.sankeyTopo() : null;
  return { sel: bx ? bx.dataset.sel || '' : '', hl: bx ? [...bx.querySelectorAll('.skr-r.hl')].map(r => r.dataset.gid) : [],
    ext: t ? t.ext : null, fadeMin: t && t.fade ? Math.min(1, ...Object.values(t.fade)) : 1, panel: !document.getElementById('sankeyPanel').hidden,
    m4: document.documentElement.classList.contains('m4'), legacy: !!document.querySelector('#flowSankeyCard .mdtree'),
    py: Math.round(scrollY), sw: document.documentElement.scrollWidth, iw: innerWidth }; }"""


def _b7_mflow(b, base, errs, shots):
    # 普查第 23 項寫的是 mobile3.js 的「分流長條＋排名」（.mdtree／#mSankeyRank）。實測：手機 v2（html.m4）在 ≤640 一律掛上，
    # 那一份替身從 2026-10-09 起就不畫了（mobile3.js cOn：v === 'flow' && !m4on()），手機上看到的是桌機那棵樹（flowtopo）＋ #sankeyRank，
    # 它的連動在 app.js SKLINK（資金流向連動1019 已做）。所以這裡驗「手機上真的看到的那一份」用觸控也連得起來，並確認舊替身沒有冒出來。
    T = "第七批連動1019 23 手機分流樹⇄排名（390 觸控）"
    c, pg = _b7_open(b, base, 390, "#flow/sankey", errs)
    if not ok(f"{T}：手機（m4）樹與排名都畫出來了",
              bool(wait_until(pg, "() => !!(window.App && App.sankeyTopoOn && App.sankeyTopoOn() && document.querySelectorAll('#sankeyRank:not([hidden]) .skr-r').length >= 3)", 15000))):
        c.close(); return
    s0 = pg.evaluate(_B7_MF)
    ok(f"{T}：手機是 m4、舊的長條替身（.mdtree）沒有畫", s0["m4"] and not s0["legacy"], s0)
    gid = pg.evaluate("() => document.querySelectorAll('#sankeyRank .skr-r')[1].dataset.gid")
    pt = _b7_center(pg, "#sankeyRank .skr-r", 1); pg.wait_for_timeout(300)
    y0 = pg.evaluate("() => Math.round(scrollY)")
    pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(500)
    s1 = pg.evaluate(_B7_MF)
    ok(f"{T}：點排名列第一下 → 鎖定（列 .hl、樹上那個族群突顯、其他變淡 {s1['fadeMin']}）、頁面不捲動（{y0}→{s1['py']}）、成分股面板沒開",
       s1["sel"] == gid and s1["hl"] == [gid] and s1["ext"] == "g:" + gid and s1["fadeMin"] < 1 and abs(s1["py"] - y0) <= 1 and not s1["panel"], s1)
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_mflow_390.png"))
    pg.locator("#sankeyRank .skr-k").tap(); pg.wait_for_timeout(400)
    s2 = pg.evaluate(_B7_MF)
    ok(f"{T}：點空白（排名說明那一行）→ 取消", s2["sel"] == "" and not s2["hl"] and s2["fadeMin"] == 1, s2)
    pt = _b7_center(pg, f"#sankeyRank .skr-r[data-gid='{gid}']", 0); pg.wait_for_timeout(200)
    pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(500)
    pt = _b7_center(pg, f"#sankeyRank .skr-r[data-gid='{gid}']", 0); pg.wait_for_timeout(200)
    pg.touchscreen.tap(pt["x"], pt["y"])
    ok(f"{T}：同一列點第二下 → 成分股面板打開（下一層）", bool(wait_until(pg, "() => !document.getElementById('sankeyPanel').hidden", 4000)))
    ok(f"{T}：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"))
    c.close()

_B7_ADM = """() => { const g = document.querySelector('#v-admin .hrlk'); if (!g) return null;
  const el = g.querySelector('.dnc[data-clock]'), ch = el && window.echarts && echarts.getInstanceByDom(el);
  const items = []; if (ch) (ch.getOption().series || []).slice(0, 2).forEach(s => (s.data || []).forEach(d => items.push({ h: d.hour, op: d.itemStyle && d.itemStyle.opacity != null ? d.itemStyle.opacity : 1, bw: d.itemStyle ? d.itemStyle.borderWidth : 0 })));
  const dcs = [...g.querySelectorAll('#trHrBars .dc[data-hrs]')];
  return { sel: g.dataset.hrSel || '', act: g.dataset.hrAct || '', on: dcs.filter(d => d.classList.contains('lkon')).map(d => d.dataset.hrs),
    lsel: dcs.filter(d => d.classList.contains('lksel')).map(d => d.dataset.hrs), dim: dcs.filter(d => d.classList.contains('lkdim')).length,
    dimOp: dcs.filter(d => d.classList.contains('lkdim')).slice(0, 1).map(d => +getComputedStyle(d).opacity)[0] || 1, n: dcs.length,
    ckDim: items.filter(x => x.op < 1).length, ckHi: items.filter(x => x.bw > 2).map(x => x.h),
    title: ch ? ((ch.getOption().title || [])[0] || {}).text || '' : '' }; }"""

# 時鐘第 hour 格的中心點（頁面座標）：從 ECharts 的版面算（上午＝第 0 個系列、下午＝第 1 個）
_B7_CKPT = """(hr) => { const el = document.querySelector('#v-admin .hrlk .dnc[data-clock]'); el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const L = ch.getModel().getSeriesByIndex(hr >= 12 ? 1 : 0).getData().getItemLayout(hr % 12);
  const a = (L.startAngle + L.endAngle) / 2, rr = (L.r0 + L.r) / 2;
  return { x: r.left + L.cx + rr * Math.cos(a), y: r.top + L.cy + rr * Math.sin(a) }; }"""


def _b7_admin(b, base, errs, shots):
    T = "第七批連動1019 管理區 時段直條⇄時鐘（1440）"
    pbase = base.replace("/index.html", "/preview/style-guide/index.html")
    c, _sent = _adm2_ctx(b, width=1440, many=True)
    c.add_init_script("try{localStorage.setItem('tw.tour','done');}catch(e){}")
    c.route(re.compile(r".*/preview/style-guide/.*"), lambda r: r.continue_(url=r.request.url.replace("/preview/style-guide/", "/")))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"adm:{e}"))
    pg.goto(pbase + "#admin/traffic", wait_until="domcontentloaded")
    if not wait_until(pg, "() => !!document.querySelector('#trTabs [data-t=users]')", 15000):
        ok(f"{T}：流量觀測打得開", False); c.close(); return
    pg.click("#trTabs [data-t=users]")
    if not ok(f"{T}：使用者頁的時段直條與時鐘畫出來了", bool(wait_until(pg, "() => document.querySelectorAll('#trHrBars .dc[data-hrs]').length === 24 && !!(window.echarts && echarts.getInstanceByDom(document.querySelector('.hrlk .dnc[data-clock]')))", 10000))):
        c.close(); return
    pg.wait_for_timeout(600)
    bar = pg.locator("#trHrBars .dc[data-hrs='14']"); bar.scroll_into_view_if_needed(); bar.hover(); pg.wait_for_timeout(450)
    s1 = pg.evaluate(_B7_ADM)
    ok(f"{T}：滑過直條 14 時 → 時鐘 14 時那格外框、其他 {s1['ckDim']} 格變淡；其他直條變淡（{s1['dimOp']}）、中心字「{s1['title'][:20]}」",
       s1["act"] == "14" and s1["ckHi"] == [14] and s1["ckDim"] == 23 and s1["dim"] == 23 and abs(s1["dimOp"] - 0.55) < 0.02 and "14" in s1["title"], s1)
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_admin_1440.png"))
    pg.mouse.move(4, 4); pg.wait_for_timeout(350)
    s2 = pg.evaluate(_B7_ADM)
    ok(f"{T}：滑開 → 全部恢復", s2["act"] == "" and s2["ckDim"] == 0 and s2["dim"] == 0, s2)
    p = pg.evaluate(_B7_CKPT, 9); pg.mouse.move(p["x"], p["y"]); pg.wait_for_timeout(450)
    s3 = pg.evaluate(_B7_ADM)
    ok(f"{T}：滑過時鐘 09 時 → 直條 09 那一根亮、其他變淡", s3["act"] == "9" and s3["on"] == ["9"] and s3["dim"] == 23, s3)
    pg.mouse.click(p["x"], p["y"]); pg.wait_for_timeout(400); pg.mouse.move(4, 4); pg.wait_for_timeout(350)
    s4 = pg.evaluate(_B7_ADM)
    ok(f"{T}：點時鐘 09 時 → 鎖定（滑開後直條 09 仍 .lksel、時鐘其他格仍淡）", s4["sel"] == "9" and s4["lsel"] == ["9"] and s4["ckDim"] == 23, s4)
    pg.click("#trHrModes [data-hr='4']"); pg.wait_for_timeout(700)
    s5 = pg.evaluate(_B7_ADM)
    ok(f"{T}：切 4H → 鎖定保留，亮的是包含 09 時的那一格（{s5['lsel']}）", s5["sel"] == "9" and s5["lsel"] == ["8,9,10,11"] and s5["n"] == 6, s5)
    pg.locator("#trHours h3").click(); pg.wait_for_timeout(350)
    s6 = pg.evaluate(_B7_ADM)
    ok(f"{T}：點空白（卡片標題）→ 取消", s6["sel"] == "" and not s6["lsel"] and s6["ckDim"] == 0, s6)
    bar = pg.locator("#trHrBars .dc[data-hrs='12,13,14,15']"); bar.click(); pg.wait_for_timeout(350); pg.mouse.move(4, 4); pg.wait_for_timeout(300)
    s7 = pg.evaluate(_B7_ADM)
    ok(f"{T}：點 4H 直條 12–16 → 時鐘那 4 個小時外框、其他 20 格淡", s7["sel"] == "12,13,14,15" and sorted(s7["ckHi"]) == [12, 13, 14, 15] and s7["ckDim"] == 20, s7)
    bar.click(); pg.wait_for_timeout(350)
    ok(f"{T}：再點同一根 → 取消", pg.evaluate(_B7_ADM)["sel"] == "")
    pg.click("#trHrModes [data-hr='1']"); pg.wait_for_timeout(400)
    c.close()


def t_b7_link_1019(b, base, code):
    errs: list[str] = []
    shots = os.environ.get("TW_B7_SHOT")
    for fn in (_b7_legend, _b7_mtf, _b7_rel, _b7_mflow, _b7_admin):
        try:
            fn(b, base, errs, shots)
        except Exception as e:  # 一段炸了不擋後面幾段，但要記一筆
            ok(f"第七批連動1019 {fn.__name__} 執行完沒有例外", False, repr(e)[:300])
    ok("第七批連動1019：沒有網頁錯誤", not errs, errs[:3])


register("第七批連動1019", lambda pg, b, base, code: t_b7_link_1019(b, base, code))
