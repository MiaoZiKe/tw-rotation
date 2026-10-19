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
#   23（390 手機）#flow 分流長條 ⇄ 資金流向排名：點排名列第一下＝選取（長條上那個族群列 .lk、頁面不捲動、還沒展開成分股），
#          再點同一列＝展開成分股；點長條上的族群列＝展開＋選取排名那一列；點空白＝取消；滑鼠滑過排名列 → 長條那一列（或它的產業鏈列）.hl。
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


def _b7_legend(b, base, errs, shots):
    T = "第七批連動1019 17 圖例滑過（1440）"
    c, pg = _b7_open(b, base, 1440, "#stock/2330", errs, "localStorage.setItem('tw.revView','m');localStorage.setItem('tw.chipWinHo','63')")
    wait_until(pg, "() => document.querySelectorAll('#stockTabs button').length > 0", 15000)
    # ---- 營收：HTML 圖例（.chlegend）
    pg.locator("#stockTabs button", has_text="營收").first.click()
    if not wait_until(pg, "() => !!document.querySelector('.chlegend[data-for=\"revBar\"] button[data-n]')", 10000):
        ok(f"{T}：營收 HTML 圖例畫出來了", False); c.close(); return
    pg.wait_for_timeout(900)
    btns = pg.evaluate("() => [...document.querySelectorAll('.chlegend[data-for=\"revBar\"] button[data-n]')].map(b => b.dataset.n)")
    ok(f"{T}：營收圖例至少兩顆（{btns}）", len(btns) >= 2, btns)
    pg.evaluate("() => document.getElementById('revBar').scrollIntoView({ block: 'center', behavior: 'instant' })"); pg.wait_for_timeout(400)
    pg.mouse.move(5, 450); pg.wait_for_timeout(500)
    c0 = pg.evaluate(_B7_CANVAS, "revBar")
    nm = btns[-1]
    bx = pg.locator(f'.chlegend[data-for="revBar"] button[data-n="{nm}"]').bounding_box()
    pg.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2); pg.wait_for_timeout(700)
    hi = pg.evaluate("() => document.getElementById('revBar').dataset.legHi || ''")
    c1 = pg.evaluate(_B7_CANVAS, "revBar")
    d1 = _b7_diff(c0, c1)
    ok(f"{T}：滑過圖例「{nm}」→ 圖上那個系列 highlight、其他變淡（畫布 {d1} 格變了）", hi == nm and d1 >= 8, [hi, d1])
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_legend_1440.png"))
    pg.mouse.move(5, 450); pg.wait_for_timeout(800)
    hi2 = pg.evaluate("() => document.getElementById('revBar').dataset.legHi || ''")
    c2 = pg.evaluate(_B7_CANVAS, "revBar")
    d2 = _b7_diff(c0, c2)
    ok(f"{T}：滑出 → 恢復（highlight 清掉、畫布跟滑過前只差 {d2} 格）", hi2 == "" and 0 <= d2 <= 3, [hi2, d2])
    loc = pg.locator(f'.chlegend[data-for="revBar"] button[data-n="{nm}"]')
    loc.click(); pg.wait_for_timeout(500)
    p1 = loc.get_attribute("aria-pressed")
    loc.click(); pg.wait_for_timeout(500)
    p2 = loc.get_attribute("aria-pressed")
    ok(f"{T}：點擊開關照舊（關 → aria-pressed {p1}；再點 → {p2}）", p1 == "false" and p2 == "true", [p1, p2])
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


_B7_MF = """() => { const box = document.querySelector('#flowSankeyCard .mdtree'); const b = box ? box.parentElement : null; if (!b) return null;
  const rk = b.querySelector('#mSankeyRank');
  return { sel: b.dataset.lkSel || '', hov: b.dataset.lkHov || '',
    liHl: [...b.querySelectorAll('.mdtree li[data-k].hl')].map(l => l.dataset.k), liLk: [...b.querySelectorAll('.mdtree li[data-k].lk')].map(l => l.dataset.k),
    rkHl: rk ? [...rk.querySelectorAll('.skr-r.hl')].map(r => r.dataset.gid) : [], rkLk: rk ? [...rk.querySelectorAll('.skr-r.lk')].map(r => r.dataset.gid) : [],
    hit: b.querySelectorAll('.mdtree li.hit').length, open: +(b.dataset.open || 0), rkVis: !!rk && !rk.hidden && !rk.classList.contains('m4shut'),
    py: Math.round(scrollY), sw: document.documentElement.scrollWidth, iw: innerWidth }; }"""


def _b7_mflow(b, base, errs, shots):
    T = "第七批連動1019 23 手機分流長條⇄排名（390）"
    c, pg = _b7_open(b, base, 390, "#flow/sankey", errs)
    if not wait_until(pg, "() => document.querySelectorAll('#flowSankeyCard #mSankeyRank .skr-r').length >= 3 && !!document.querySelector('#flowSankeyCard .mdtree li[data-k]')", 15000):
        ok(f"{T}：手機長條與排名都畫出來了", False); c.close(); return
    hd = pg.locator("#mSankeyRankHd")
    if hd.count() and hd.is_visible() and hd.get_attribute("aria-expanded") != "true":
        hd.tap(); pg.wait_for_timeout(400)
    s0 = pg.evaluate(_B7_MF)
    ok(f"{T}：排名展開了", s0["rkVis"], s0)
    gid = pg.evaluate("() => document.querySelectorAll('#mSankeyRank .skr-r')[1].dataset.gid")
    pt = _b7_center(pg, "#mSankeyRank .skr-r", 1); pg.wait_for_timeout(300)
    y0 = pg.evaluate("() => Math.round(scrollY)")
    pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(500)
    s1 = pg.evaluate(_B7_MF)
    ok(f"{T}：點排名列第一下 → 選取（排名列 .lk、長條上「{s1['sel']}」那一列 .lk）、頁面不捲動（{y0}→{s1['py']}）、還沒展開成分股",
       s1["sel"] != "" and s1["rkLk"] == [gid] and s1["liLk"] == ["2:" + s1["sel"]] and abs(s1["py"] - y0) <= 1 and s1["hit"] == 0, s1)
    if shots:
        pg.screenshot(path=os.path.join(shots, "b7_link_mflow_390.png"))
    pt = _b7_center(pg, f"#mSankeyRank .skr-r[data-gid='{gid}']", 0); pg.wait_for_timeout(200)
    pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(900)
    s2 = pg.evaluate(_B7_MF)
    ok(f"{T}：再點同一列 → 原本的下一層（長條上那個族群展開成分股）", s2["hit"] >= 1 and s2["sel"] == s1["sel"], s2)
    pg.locator("#flowSankeyCard .mdtree .msub").first.tap(); pg.wait_for_timeout(400)
    s3 = pg.evaluate(_B7_MF)
    ok(f"{T}：點空白（長條上方的說明字）→ 取消選取", s3["sel"] == "" and not s3["rkLk"] and not s3["liLk"], s3)
    # 點長條上的族群列 → 展開＋選取排名那一列
    k = pg.evaluate("""() => { const rk = [...document.querySelectorAll('#mSankeyRank .skr-r')].map(r => r.querySelector('.n b').textContent);
      const li = [...document.querySelectorAll('#flowSankeyCard .mdtree li[data-k]')].find(l => l.dataset.k.indexOf('2:') === 0 && rk.includes(l.dataset.k.slice(2)) && !l.nextElementSibling?.classList.contains('sub'));
      return li ? li.dataset.k : null; }""")
    if ok(f"{T}：長條上看得到排名表裡的族群列", bool(k)):
        pt = pg.evaluate("""(k) => { const li = [...document.querySelectorAll('#flowSankeyCard .mdtree li[data-k]')].find(l => l.dataset.k === k);
          li.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = li.querySelector('.n').getBoundingClientRect(); return { x: r.left + 10, y: r.top + r.height / 2 }; }""", k)
        pg.wait_for_timeout(200)
        pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(500)
        s4 = pg.evaluate(_B7_MF)
        ok(f"{T}：點長條上的族群列「{k[2:]}」→ 照舊展開、排名那一列 .lk", s4["sel"] == k[2:] and len(s4["rkLk"]) == 1 and s4["open"] > s3["open"], s4)
        pg.touchscreen.tap(pt["x"], pt["y"]); pg.wait_for_timeout(500)
        s5 = pg.evaluate(_B7_MF)
        ok(f"{T}：再點同一列 → 收起＋取消選取", s5["sel"] == "" and not s5["rkLk"], s5)
    # 滑鼠滑過排名列 → 長條那一列（或它所屬的產業鏈列）.hl
    pt = _b7_center(pg, "#mSankeyRank .skr-r", 0); pg.wait_for_timeout(200)
    pg.mouse.move(pt["x"], pt["y"]); pg.wait_for_timeout(400)
    s6 = pg.evaluate(_B7_MF)
    ok(f"{T}：滑鼠滑過排名第一列 → 長條上「{s6['hov']}」那一列（或它的產業鏈列）.hl", s6["hov"] != "" and len(s6["liHl"]) >= 1 and len(s6["rkHl"]) == 1, s6)
    pg.mouse.move(195, 5); pg.wait_for_timeout(300)
    s7 = pg.evaluate(_B7_MF)
    ok(f"{T}：滑開 → 恢復", s7["hov"] == "" and not s7["liHl"] and not s7["rkHl"], s7)
    ok(f"{T}：沒有橫向捲軸", s7["sw"] <= s7["iw"] + 1, s7)
    c.close()


def t_b7_link_1019(b, base, code):
    errs: list[str] = []
    shots = os.environ.get("TW_B7_SHOT")
    for fn in (_b7_legend, _b7_mtf, _b7_rel, _b7_mflow):
        try:
            fn(b, base, errs, shots)
        except Exception as e:  # 一段炸了不擋後面幾段，但要記一筆
            ok(f"第七批連動1019 {fn.__name__} 執行完沒有例外", False, repr(e)[:300])
    ok("第七批連動1019：沒有網頁錯誤", not errs, errs[:3])


register("第七批連動1019", lambda pg, b, base, code: t_b7_link_1019(b, base, code))
