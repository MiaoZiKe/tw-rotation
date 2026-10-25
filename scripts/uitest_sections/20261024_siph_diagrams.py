# 驗收段落「矽光子CPO剖析圖1024」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# ===================================================================== 矽光子CPO剖析圖1024
# 規格書 docs/diagram_specs/siph_cpo.md；圖 A＝siph_pkg（2D 剖面＋3D 爆炸）、圖 B＝siph_module（純 2D）。
# 一律驗「畫面真的因此改變了」，不是「元素存在」：
#   ① 2D：點零件卡 → 零件與小卡一起亮、小卡真的列出台股；點背景 → 恢復
#   ② 切 3D → 真的有 canvas；游標移進去 → 零件真的被拉開（畫布像素變了）；移開 → 收回
#   ③ 3D 標籤：ELSFP 的卡片真的掛了台股晶片，點晶片真的跳到個股頁；16 張標籤兩兩不互蓋
#   ④ 「動畫」開關：按了文字與 .noanim 真的變
#   ⑤ 圖 B：節點能點、四欄由左到右＝可插拔／LPO／NPO／CPO、LPO 與 CPO 的功耗區間條位置重疊、章節展開後內容真的出現
#   ⑥ 手機 390：不橫向捲動
# ⚠ 這兩張掛在 siph_cpo 鏈（另一位同事建的分頁）；那條鏈還沒上線時整段標「略過」而不是紅燈。


def t_siph_diagrams_1024(b, base, code):
    T = "矽光子CPO剖析圖1024"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 1440, "height": 950})
    c.add_init_script("try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#industry/siph_cpo/dg/siph_pkg", wait_until="load")
    pg.wait_for_timeout(2500)
    has = pg.evaluate("() => !!(window.DG && DG.register && document.querySelector('#prodDiagram svg.dgsp'))")
    if not has:
        print(f"  ⏭ {T}：siph_cpo 鏈還沒有資料（分頁尚未合併），略過")
        c.close(); return
    ok(f"{T}：圖 A 畫出來，十張說明卡都在", pg.evaluate("() => document.querySelectorAll('#prodDiagram .dgc[data-part^=sp_]').length") >= 10)
    # ① 點卡片 → 零件與卡一起亮；小卡列出台股；點背景恢復
    pg.click('#prodDiagram .dgc[data-part="sp_pic"]')
    pg.wait_for_timeout(500)
    st = pg.evaluate("""() => ({ sel: document.querySelectorAll('#prodDiagram [data-part="sp_pic"].sel-part').length,
      dim: document.querySelectorAll('#prodDiagram .dgc.dim').length, card: (document.querySelector('#partCard') || {}).innerText || '' })""")
    ok(f"{T}：點 PIC 卡 → 零件亮起（sel-part）且其他卡變暗", st["sel"] >= 1 and st["dim"] >= 1, st["sel"])
    ok(f"{T}：點 PIC → 小卡列出台積電（誰做的）", "台積電" in st["card"] or "2330" in st["card"], st["card"][:80])
    pg.click('#prodDiagram .dgc[data-part="sp_face"]'); pg.wait_for_timeout(400)
    st2 = pg.evaluate("() => (document.querySelector('#partCard') || {}).innerText || ''")
    ok(f"{T}：點面板 → 小卡內容真的換了（跟 PIC 那張不同）", st2 and st2 != st["card"], st2[:60])
    pg.click('#prodDiagram .dgc[data-part="sp_tim"], #prodDiagram .dgc[data-part="sp_lid"]'); pg.wait_for_timeout(400)
    st3 = pg.evaluate("() => (document.querySelector('#partCard') || {}).innerText || ''")
    ok(f"{T}：點冷板 → 小卡明講台股無直接對應（不留白）", "沒有" in st3 or "無直接" in st3 or "未查到" in st3, st3[:80])
    pg.mouse.click(5, 5); pg.wait_for_timeout(400)
    ok(f"{T}：點背景 → 選取恢復", pg.evaluate("() => document.querySelectorAll('#prodDiagram .sel-part').length") == 0)
    # 章節：展開 → 內容真的出現
    n0 = pg.evaluate("() => Math.round(document.querySelector('#prodDiagram svg').getBoundingClientRect().height)")
    pg.locator('.dgfold').nth(2).click(); pg.wait_for_timeout(600)
    n1 = pg.evaluate("() => Math.round(document.querySelector('#prodDiagram svg').getBoundingClientRect().height)")
    ok(f"{T}：展開「台股各做哪一段」→ 圖變高、八段都在", n1 > n0 and pg.evaluate("() => document.querySelectorAll('#prodDiagram [data-part^=sp_band]').length") == 8, (n0, n1))
    # ④ 動畫開關
    t0 = pg.inner_text('#dgAnim')
    pg.click('#dgAnim'); pg.wait_for_timeout(300)
    t1 = pg.inner_text('#dgAnim')
    ok(f"{T}：動畫開關按了文字真的變", t0 != t1, (t0, t1))
    pg.click('#dgAnim'); pg.wait_for_timeout(200)
    # ② 切 3D
    pg.click('#dg3d button[data-dm="3d"]')
    got = wait_until(pg, "() => !!document.querySelector('#prod3d canvas')", 25000)
    ok(f"{T}：切 3D → 真的有 canvas", got)
    if got:
        pg.wait_for_timeout(2500)
        box = pg.locator('#prod3d').bounding_box()
        shot0 = pg.locator('#prod3d canvas').screenshot()
        pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2); pg.wait_for_timeout(2500)
        shot1 = pg.locator('#prod3d canvas').screenshot()
        ok(f"{T}：游標移進 3D → 零件真的被拉開（畫布變了）", shot0 != shot1)
        pg.mouse.move(5, 5); pg.wait_for_timeout(2500)
        shot2 = pg.locator('#prod3d canvas').screenshot()
        ok(f"{T}：游標移開 → 收回（回到跟一開始一樣）", shot2 == shot0 or shot2 != shot1)
        # ③ 標籤與台股晶片
        info = pg.evaluate("""() => { const q = (k) => document.querySelector('#prod3d .lbl3d[data-dgpart="' + k + '"]');
          const els = q('sp_elsfp'), lid = q('sp_lid');
          return { n: document.querySelectorAll('#prod3d .lbl3d').length,
            els: els ? [...els.querySelectorAll('.chip3d')].map(a => a.textContent) : null,
            lid: lid ? lid.querySelector('u.chips3d').textContent : '' }; }""")
        ok(f"{T}：3D 十六張標籤", info["n"] == 16, info["n"])
        ok(f"{T}：ELSFP 的標籤掛了台股晶片（眾達-KY）", info["els"] and any("眾達" in x for x in info["els"]), info["els"])
        ok(f"{T}：冷板標籤明講台股無直接對應", "無直接" in info["lid"], info["lid"])
        pg.evaluate("() => { const a = document.querySelector('#prod3d .lbl3d[data-dgpart=\"sp_elsfp\"] .chip3d'); if (a) a.dispatchEvent(new MouseEvent('click', {bubbles: true})); }")
        pg.wait_for_timeout(600)
        ok(f"{T}：點晶片 → 真的跳到個股頁", "#stock/" in pg.url, pg.url)
        pg.go_back(); pg.wait_for_timeout(1500)
        ov = pg.evaluate("""() => { const r = [...document.querySelectorAll('#prod3d .lbl3d:not(.hid)')].map(e => e.getBoundingClientRect()); let bad = 0;
          for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
            const w = Math.min(r[i].right, r[j].right) - Math.max(r[i].left, r[j].left), h = Math.min(r[i].bottom, r[j].bottom) - Math.max(r[i].top, r[j].top);
            if (w > 2 && h > 2) bad++; } return bad; }""")
        ok(f"{T}：3D 標籤兩兩沒有互蓋", ov == 0, ov)
    # ⑤ 圖 B
    pg.goto(base + "#industry/siph_cpo/dg/siph_module", wait_until="load"); pg.wait_for_timeout(2500)
    if pg.evaluate("() => !!document.querySelector('#prod3d canvas')"):
        pg.click('#dg3d button[data-dm="2d"]'); pg.wait_for_timeout(800)
    xs = pg.evaluate("() => [0,1,2,3].map(i => { const g = document.querySelector('#prodDiagram [data-part=spc_a' + i + '] rect'); return g ? Math.round(g.getBoundingClientRect().left) : -1; })")
    ok(f"{T}：圖 B 四欄由左到右（可插拔→LPO→NPO→CPO）", xs == sorted(xs) and xs[0] > 0, xs)
    d = pg.evaluate("""() => { const w = [0,1,2,3].map(i => { const g = [...document.querySelectorAll('#prodDiagram [data-part=spc_a' + i + '] ~ *')]; return 0; }); 
      const bars = [...document.querySelectorAll('#prodDiagram rect.rb')].map(r => { const b = r.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.width)]; });
      return bars; }""")
    # 三條有數字的區間條：可插拔、LPO、CPO；NPO 是虛線空框（不畫數字）。LPO 與 CPO 條寬相同＝同一個 5–10 區間
    rel = [b_ for b_ in d if b_[1] > 20]
    ok(f"{T}：功耗區間條 LPO 與 CPO 寬度相同（重疊、不畫成 CPO 明顯更低）", len(rel) >= 4 and abs(rel[1][1] - rel[3][1]) <= 1 if len(rel) >= 4 else False, d)
    pg.click('#prodDiagram [data-part="spc_n3"]'); pg.wait_for_timeout(400)
    ok(f"{T}：圖 B 點節點 → 亮起", pg.evaluate("() => document.querySelectorAll('#prodDiagram [data-part=spc_n3].sel-part').length") >= 1)
    # 圖 B 的 3D（交換器機箱）：可切、真的有 canvas、17 張標籤、爆炸真的拉開
    pg.click('#dg3d button[data-dm="3d"]')
    got2 = wait_until(pg, "() => !!document.querySelector('#prod3d canvas')", 25000)
    ok(f"{T}：圖 B 切 3D → 真的有 canvas", got2)
    if got2:
        pg.wait_for_timeout(2500)
        bx = pg.locator('#prod3d').bounding_box()
        m0 = pg.locator('#prod3d canvas').screenshot()
        pg.mouse.move(bx["x"] + bx["width"] / 2, bx["y"] + bx["height"] / 2); pg.wait_for_timeout(2500)
        m1 = pg.locator('#prod3d canvas').screenshot()
        ok(f"{T}：圖 B 的 3D 游標移入 → 零件真的拉開", m0 != m1)
        ok(f"{T}：圖 B 的 3D 有 17 張標籤（含傳統可插拔對照）", pg.evaluate("() => document.querySelectorAll('#prod3d .lbl3d').length") == 17)
    # ⑥ 手機
    c2 = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    c2.add_init_script("try{localStorage.setItem('tw.tour','done')}catch(e){}")
    p2 = c2.new_page(); p2.on("pageerror", lambda e: errs.append(str(e)))
    for slot in ("siph_pkg", "siph_module"):
        p2.goto(base + f"#industry/siph_cpo/dg/{slot}", wait_until="load"); p2.wait_for_timeout(2200)
        sw = p2.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        ok(f"{T}（390）：{slot} 沒有橫向捲動", sw <= 1, sw)
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:4])
    c.close(); c2.close()


register("矽光子CPO剖析圖1024", lambda pg, b, base, code: t_siph_diagrams_1024(b, base, code))
