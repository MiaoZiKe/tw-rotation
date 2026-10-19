# 驗收段落「ETF月配連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== ETF月配連動1019
# Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」。普查表第 5、6 項（#etf/inc）。
# 1440／390 各走一輪，全部用真的滑鼠移動與點擊，每一步都量畫面真的變了：
#  單檔（每月入帳直條＋右側清單＋膠囊）
#   ① 滑過清單列 → 那檔直條 opacity 1、其他檔變淡（.55 深／.35 淺）；該列 .hl；滑出恢復
#   ② 滑過膠囊（只有 1440，手機膠囊列換成下拉）→ 同上
#   ③ 滑過直條 → 清單那列 .hl
#   ④ 點直條＝鎖定（滑出仍保留、有外框、清單列 .lk），明細卡不開；再點同一根 → 才開明細卡
#   ⑤ 點圖內空白 → 取消；點清單名稱第一下＝選取、第二下才開明細
#  複利試算（回測走勢＋情境表）
#   ⑥ 滑過表格列 → 那條線變粗、其他線變淡；滑過線 → 表格那列 .hl；滑出恢復
#   ⑦ 點表格列＝鎖定（線有描邊、列 .lk），再點同一列取消；點線鎖定、點圖內空白取消
#  全程沒有網頁錯誤、手機沒有橫向捲軸

_INC_JS = """() => {
  const S = window.TwEtfPage.state, ch = echarts.getInstanceByDom(document.getElementById('incBar')), o = ch.getOption();
  const bars = o.series.filter(s => s.type === 'bar');
  return {
    sel: S.inc.ssel || null, det: (document.getElementById('incDet') || {dataset: {}}).dataset.code || '', detShown: !document.getElementById('incDet').hidden,
    codes: (document.getElementById('incBar').dataset.codes || '').split(','),
    op: bars.map(s => (s.itemStyle && s.itemStyle.opacity != null) ? s.itemStyle.opacity : 1),
    bw: bars.map(s => (s.itemStyle && s.itemStyle.borderWidth) || 0),
    col: bars.map(s => !!(s.itemStyle && s.itemStyle.color)),
    hl: [...document.querySelectorAll('#incList .ilr.hl')].map(r => r.dataset.code),
    lk: [...document.querySelectorAll('#incList .ilr.lk')].map(r => r.dataset.code),
    chipHl: [...document.querySelectorAll('#incChips .snk.hl')].map(b => b.dataset.n.split(' ').pop()),
    chipDim: document.querySelectorAll('#incChips .snk.dim').length,
  };
}"""

# 第 k 檔最高那一根直條的中心（頁面座標）
_INCBAR_PT_JS = """(k) => {
  document.getElementById('incBar').scrollIntoView({ block: 'center', behavior: 'instant' });
  const el = document.getElementById('incBar'), ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const d = ch.getModel().getSeriesByIndex(k).getData();
  let best = null;
  for (let j = 0; j < d.count(); j++) { const L = d.getItemLayout(j); if (!L || !(Math.abs(L.height) > 4)) continue; if (!best || Math.abs(L.height) > Math.abs(best.height)) best = L; }
  if (!best) return null;
  return { x: r.left + best.x + best.width / 2, y: r.top + best.y + best.height / 2 };
}"""

_GRID_TL_JS = """(id) => { document.getElementById(id).scrollIntoView({ block: 'center', behavior: 'instant' }); const el = document.getElementById(id), ch = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const g = ch.getModel().getComponent('grid').coordinateSystem.getRect(); return { x: r.left + g.x + 6, y: r.top + g.y + 6 }; }"""

_CX_JS = """() => {
  const S = window.TwEtfPage.state, el = document.getElementById('cxChart'), o = echarts.getInstanceByDom(el).getOption();
  return {
    sel: S.inc.xsel || null, keys: (el.dataset.lines || '').split(','),
    lw: o.series.map(s => s.lineStyle.width), lop: o.series.map(s => s.lineStyle.opacity == null ? 1 : s.lineStyle.opacity),
    lsh: o.series.map(s => s.lineStyle.shadowBlur || 0), dash: o.series.map(s => s.lineStyle.type || 'solid'),
    hl: [...document.querySelectorAll('#cxTbl tr[data-key].hl')].map(t => t.dataset.key),
    lk: [...document.querySelectorAll('#cxTbl tr[data-key].lk')].map(t => t.dataset.key),
    dimTr: document.querySelectorAll('#cxTbl tr[data-key].dim').length, nTr: document.querySelectorAll('#cxTbl tr[data-key]').length,
  };
}"""

# 複利走勢第 k 條上「離其他線最遠」的一點（只在目前 dataZoom 看得到的範圍裡找）
_CXLINE_PT_JS = """(k) => {
  document.getElementById('cxChart').scrollIntoView({ block: 'center', behavior: 'instant' });
  const el = document.getElementById('cxChart'), ch = echarts.getInstanceByDom(el), o = ch.getOption(), r = el.getBoundingClientRect();
  const ser = o.series, n = ser[k].data.length, g = ch.getModel().getComponent('grid').coordinateSystem.getRect();
  let best = null;
  for (let j = Math.floor(n * 0.3); j < Math.floor(n * 0.85); j += Math.max(1, Math.floor(n / 90))) {
    const v = ser[k].data[j]; if (v == null) continue;
    const p = ch.convertToPixel({ seriesIndex: k }, [j, v]);
    if (p[0] < g.x + 10 || p[0] > g.x + g.width - 10) continue;
    let gap = 1e9;
    ser.forEach((s, i) => { if (i === k || s.data[j] == null) return; const q = ch.convertToPixel({ seriesIndex: i }, [j, s.data[j]]); gap = Math.min(gap, Math.abs(q[1] - p[1])); });
    if (!best || gap > best.gap) best = { gap, x: r.left + p[0], y: r.top + p[1] };
  }
  return best;
}"""

_NOHSCROLL_INC = "() => { const y = scrollY; scrollTo({ left: 60, top: y, behavior: 'instant' }); const x = scrollX; scrollTo({ left: 0, top: y, behavior: 'instant' }); return x === 0; }"


def t_inc_link_1019(b, base, code):
    T = "ETF月配連動1019"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_INCLINK_SHOT")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#etf/inc", wait_until="networkidle")
        J("() => { try { Object.keys(localStorage).filter(k => k.startsWith('tw.etf.')).forEach(k => localStorage.removeItem(k)); } catch (e) {} }")
        pg.reload(wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, """() => { const el = document.getElementById('incBar'); return !!el && +el.dataset.n >= 3 && !!echarts.getInstanceByDom(el)
            && document.querySelectorAll('#incList .ilr').length >= 5 && window.TwEtfPage && window.TwEtfPage.state.series; }""", 25000)
        ok(f"{T}（{W}）：單檔每月入帳畫出 ≥ 3 檔、右側清單 ≥ 5 列（前置）", bool(ready))
        if not ready:
            c.close(); continue
        pg.wait_for_timeout(500)
        dim = J("() => document.documentElement.getAttribute('data-theme') === 'light' ? 0.35 : 0.55")

        def away():
            pg.mouse.move(W - 4, 4); pg.wait_for_timeout(250)

        def lit(st, cd, lvl=1):
            k = st["codes"].index(cd)
            bar = st["op"][k] == 1 and all(abs(o - dim) < 1e-6 for i, o in enumerate(st["op"]) if i != k) and st["bw"][k] > 0 and all(st["col"])
            row = cd in st["hl"]
            lock = lvl < 2 or (st["sel"] == cd and cd in st["lk"] and st["bw"][k] >= 1.5)
            return bar and row and lock

        def normal(st):
            return all(o == 1 for o in st["op"]) and all(w == 0 for w in st["bw"]) and not st["hl"] and st["sel"] is None

        st0 = J(_INC_JS)
        codes = st0["codes"]
        ok(f"{T}（{W}）：初始全部正常亮度（直條 opacity 1、沒有外框、清單沒有 .hl）", normal(st0), st0)
        # ① 滑過清單列（第 2 檔）
        c2 = codes[1]
        pg.locator(f"#incList .ilr[data-code='{c2}'] .lt").scroll_into_view_if_needed()
        pg.hover(f"#incList .ilr[data-code='{c2}'] .lt"); pg.wait_for_timeout(300)
        st = J(_INC_JS)
        ok(f"{T}（{W}）：滑過清單列 {c2} → 那檔直條全亮＋外框、其他檔 opacity {dim}、該列 .hl", lit(st, c2), st)
        if W == 1440:
            ok(f"{T}（1440）：滑過清單列 → 膠囊那顆亮、其他膠囊變淡", st["chipHl"] == [c2] and st["chipDim"] == len(codes) - 1, st)
        away(); st = J(_INC_JS)
        ok(f"{T}（{W}）：滑出清單 → 全部恢復", normal(st), st)
        # ② 滑過膠囊
        if W == 1440:
            c3 = codes[2]
            pg.hover(f"#incChips .snk[data-n$=' {c3}']"); pg.wait_for_timeout(300)
            st = J(_INC_JS)
            ok(f"{T}（1440）：滑過膠囊 {c3} → 直條那檔亮、其他淡，清單那列 .hl", lit(st, c3), st)
            away()
        # ③ 滑過直條（第 1 檔）
        c1 = codes[0]
        bp = J(_INCBAR_PT_JS, 0)
        pg.mouse.move(bp["x"], bp["y"]); pg.wait_for_timeout(300)
        st = J(_INC_JS)
        ok(f"{T}（{W}）：滑過直條 {c1} → 清單那列 .hl、其他直條變淡", lit(st, c1), [bp, st])
        if shot_dir and W == 1440:
            pg.locator("#incSingle .incsg").screenshot(path=os.path.join(shot_dir, "inc_link_hover.png"))
        away()
        # ④ 點直條＝鎖定，明細卡不開
        y0 = J("() => scrollY")
        bp = J(_INCBAR_PT_JS, 0)
        pg.mouse.click(bp["x"], bp["y"]); pg.wait_for_timeout(400); away()
        st = J(_INC_JS)
        ok(f"{T}（{W}）：點直條 {c1} → 鎖定（滑出後仍保留、外框、清單列 .lk），明細卡沒有開", lit(st, c1, 2) and not st["detShown"], st)
        if W == 390:
            ok(f"{T}（390）：點直條選取不捲動頁面", abs(J("() => scrollY") - y0) < 2, [y0, J("() => scrollY")])
        if shot_dir and W == 1440:
            pg.locator("#incSingle .incsg").screenshot(path=os.path.join(shot_dir, "inc_link_locked.png"))
        bp = J(_INCBAR_PT_JS, 0)
        pg.mouse.click(bp["x"], bp["y"]); pg.wait_for_timeout(900); away()
        st = J(_INC_JS)
        ok(f"{T}（{W}）：已選中再點同一檔直條 → 才開明細卡（選取保留）", st["detShown"] and st["det"] == c1 and st["sel"] == c1, st)
        # ⑤ 點圖內空白 → 取消
        bl = J(_GRID_TL_JS, "incBar")
        pg.mouse.click(bl["x"], bl["y"]); pg.wait_for_timeout(400); away()
        st = J(_INC_JS)
        ok(f"{T}（{W}）：點圖內空白 → 取消選取、全部恢復", normal(st), [bl, st])
        # 清單名稱：第一下選取、第二下開明細（換一檔，先把明細收掉）
        J("() => { const S = window.TwEtfPage.state; S.inc.det = null; }")
        pg.locator(f"#incList .ilr[data-code='{c2}'] .iln").scroll_into_view_if_needed()
        pg.click(f"#incList .ilr[data-code='{c2}'] .iln"); pg.wait_for_timeout(500); away()
        st = J(_INC_JS)
        ok(f"{T}（{W}）：點清單名稱 {c2} 第一下 → 選取三處連動，明細卡不換成它", lit(st, c2, 2) and st["det"] != c2, st)
        pg.click(f"#incList .ilr[data-code='{c2}'] .iln"); pg.wait_for_timeout(900); away()
        st = J(_INC_JS)
        ok(f"{T}（{W}）：再點一次 → 開 {c2} 的明細卡", st["detShown"] and st["det"] == c2, st)
        # 點清單列空白處（.lt）＝鎖定／再點取消
        pg.click(f"#incList .ilr[data-code='{c1}'] .lt"); pg.wait_for_timeout(400); away()
        ok(f"{T}（{W}）：點清單列 {c1} → 鎖定換成它", lit(J(_INC_JS), c1, 2), J(_INC_JS))
        pg.click(f"#incList .ilr[data-code='{c1}'] .lt"); pg.wait_for_timeout(500); away()
        ok(f"{T}（{W}）：再點同一列 → 取消", normal(J(_INC_JS)), J(_INC_JS))
        if W == 1440:
            # 膠囊：點名字＝鎖定，× 照舊拿掉
            c3 = codes[2]
            pg.click(f"#incChips .snk[data-n$=' {c3}']", position={"x": 12, "y": 8}); pg.wait_for_timeout(400); away()
            st = J(_INC_JS)
            ok(f"{T}（1440）：點膠囊名字 {c3} → 鎖定（不會拿掉那檔）", lit(st, c3, 2) and len(st["codes"]) == len(codes), st)
            pg.click("#incSQ"); pg.wait_for_timeout(400); away()
            ok(f"{T}（1440）：點卡片內空白（說明句）→ 取消", normal(J(_INC_JS)), J(_INC_JS))
        if W == 390:
            ok(f"{T}（390）：單檔區沒有橫向捲軸", J(_NOHSCROLL_INC))

        # ---------------- 複利試算
        if pg.locator("#incMain button[data-v='x']").is_visible():
            pg.click("#incMain button[data-v='x']")
        else:
            J("() => { location.hash = '#etf/inc/cx'; }")
        okc = wait_until(pg, "() => { const el = document.getElementById('cxChart'); return el && el.dataset.state === 'ok' && !!echarts.getInstanceByDom(el) && document.querySelectorAll('#cxTbl tr[data-key]').length >= 3; }", 25000)
        ok(f"{T}（{W}）：複利試算畫出回測走勢與情境表（前置）", bool(okc))
        if not okc:
            c.close(); continue
        pg.wait_for_timeout(600)
        x0 = J(_CX_JS)
        keys = x0["keys"]
        base_w = list(x0["lw"])

        def xlit(st, k, lvl=1):
            i = keys.index(k)
            line = st["lw"][i] > base_w[i] + 1 and st["lop"][i] == 1 and all(abs(o - dim) < 1e-6 for j, o in enumerate(st["lop"]) if j != i)
            row = k in st["hl"] and st["dimTr"] == st["nTr"] - 1
            lock = lvl < 2 or (st["sel"] == k and k in st["lk"] and st["lsh"][i] > 0)
            return line and row and lock and st["dash"] == x0["dash"]   # 虛線／點線樣式不能被洗掉

        def xnormal(st):
            return st["lw"] == base_w and all(o == 1 for o in st["lop"]) and not st["hl"] and st["dimTr"] == 0 and st["sel"] is None

        ok(f"{T}（{W}）：複利初始全部正常（沒有變淡、沒有 .hl）", xnormal(x0), x0)
        k1 = keys[1]
        pg.locator(f"#cxTbl tr[data-key='{k1}'] td:first-child").scroll_into_view_if_needed()
        pg.hover(f"#cxTbl tr[data-key='{k1}'] td:first-child"); pg.wait_for_timeout(300)
        st = J(_CX_JS)
        ok(f"{T}（{W}）：滑過情境表列 {k1} → 那條線變粗、其他線 opacity {dim}、該列 .hl、其他列 .dim", xlit(st, k1), st)
        if shot_dir and W == 1440:
            pg.locator("#incPX .cxg").screenshot(path=os.path.join(shot_dir, "inc_link_cx_hover.png"))
        away(); st = J(_CX_JS)
        ok(f"{T}（{W}）：滑出表格 → 恢復", xnormal(st), st)
        # 滑過線
        k0 = keys[0]
        pt = J(_CXLINE_PT_JS, 0)
        pg.mouse.move(pt["x"], pt["y"]); pg.wait_for_timeout(300)
        st = J(_CX_JS)
        ok(f"{T}（{W}）：滑過走勢線 {k0} → 表格那列 .hl、其他線變淡", xlit(st, k0), [pt, st])
        away()
        # 點表格列＝鎖定；再點取消
        pg.click(f"#cxTbl tr[data-key='{k1}'] td:first-child"); pg.wait_for_timeout(400); away()
        st = J(_CX_JS)
        ok(f"{T}（{W}）：點情境表列 {k1} → 鎖定（滑出仍保留、線描邊、列 .lk）", xlit(st, k1, 2), st)
        if shot_dir and W == 1440:
            pg.locator("#incPX .cxg").screenshot(path=os.path.join(shot_dir, "inc_link_cx_locked.png"))
        pg.click(f"#cxTbl tr[data-key='{k1}'] td:first-child"); pg.wait_for_timeout(500); away()
        ok(f"{T}（{W}）：再點同一列 → 取消", xnormal(J(_CX_JS)), J(_CX_JS))
        # 點線鎖定 → 點圖內空白取消
        pt = J(_CXLINE_PT_JS, 0)
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(400); away()
        st = J(_CX_JS)
        ok(f"{T}（{W}）：點走勢線 {k0} → 鎖定", xlit(st, k0, 2), [pt, st])
        bl = J(_GRID_TL_JS, "cxChart")
        pg.mouse.click(bl["x"], bl["y"]); pg.wait_for_timeout(400); away()
        st = J(_CX_JS)
        ok(f"{T}（{W}）：點走勢圖空白處 → 取消、全部恢復", xnormal(st), [bl, st])
        if W == 390:
            ok(f"{T}（390）：複利區沒有橫向捲軸", J(_NOHSCROLL_INC))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("ETF月配連動1019", lambda pg, b, base, code: t_inc_link_1019(b, base, code))
