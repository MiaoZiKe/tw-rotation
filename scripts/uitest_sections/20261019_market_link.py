# 驗收段落「市場頁連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 市場頁連動1019
# Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」「避免我重複下指令」。
# 普查第二輪 #13～#15（docs/chart_link_census_1019.md），1440／390 各走一輪，全部用真的滑鼠移動與點擊，每一步量畫面真的變了：
#   #13 #market/ma：滑過族群方格 → 走勢圖那條線（沒勾的走預覽線）加粗、其他線變淡；滑出恢復；
#       點方格第一下＝鎖定（還在這頁、其他方格 .lnk-dim）、點空白取消、鎖定後再點同一格才進族群頁；滑過已選色票 → 那條線加粗
#   #14 #season 長條：滑過長條 → 那個族群全亮＋外框、其他變淡、色票 .hl；滑過色票、滑過下拉列 → 同上；
#       點長條第一下＝鎖定（不跳頁）、點空白取消、再點同一族群才進族群頁
#   #15 #market/updown：滑過右表一列 → 它所在那根直條全亮＋外框、其他變淡、那列 .hl；滑出恢復；
#       漲停分頁 → 漲停那幾根有外框（其他不變淡）；點直條照舊開名單、同時右表落在那根的列 .hl
#   手機 390：沒有滑過，驗點擊兩步、不橫向捲動；全程沒有網頁錯誤

_MA_JS = """() => { const el = document.getElementById('maTrend'), c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const o = c.getOption(), S = o.series;
  const g = S.filter(s => String(s.id).startsWith('g:'));
  const pv = S.find(s => s.id === 'maPrev'), m1 = S.find(s => s.id === 'mk1');
  return { lnk: document.getElementById('maTrendBox').dataset.lnk || '',
    wide: g.filter(s => (s.lineStyle.width || 0) > 3).map(s => s.id.slice(2)),
    dimG: g.filter(s => (s.lineStyle.opacity == null ? 1 : s.lineStyle.opacity) < 1).length, nG: g.length,
    m1op: m1.lineStyle.opacity == null ? 1 : m1.lineStyle.opacity,
    prevN: (pv.data || []).filter(v => v != null).length, prevW: pv.lineStyle.width,
    hl: [...document.querySelectorAll('#mktBody .ma.lnk-hl')].map(e => e.dataset.gn),
    dim: document.querySelectorAll('#mktBody .ma.lnk-dim').length,
    keyHl: [...document.querySelectorAll('#maGroupKey .snk.hl')].map(e => e.dataset.n), hash: location.hash }; }"""

_SN_JS = """() => { const el = document.getElementById('seasonLine'), c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const S = c.getOption().series.filter(s => String(s.id || '').startsWith('b:'));
  return { lnk: el.dataset.lnk || '', sel: el.dataset.lnksel || '', names: S.map(s => s.name),
    ops: S.map(s => (s.itemStyle && s.itemStyle.opacity != null) ? s.itemStyle.opacity : 1),
    bw: S.map(s => (s.itemStyle && s.itemStyle.borderWidth) || 0),
    keyHl: [...document.querySelectorAll('#seasonKey .snk.hl')].map(e => e.dataset.n),
    ddHl: [...document.querySelectorAll('#seasonGroupDD .ddopt.hl')].map(e => e.dataset.n), hash: location.hash }; }"""

# 第 s 個長條系列在第 m 個月那根的中心（頁面座標）
_SN_PT_JS = """([s, m]) => { const el = document.getElementById('seasonLine'); el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const c = echarts.getInstanceByDom(el), r = el.getBoundingClientRect();
  const idx = c.getOption().series.findIndex(x => x.id === s);
  const L = c.getModel().getSeriesByIndex(idx).getData().getItemLayout(m); if (!L) return null;
  return { x: r.left + L.x + L.width / 2, y: r.top + L.y + L.height / 2, h: Math.abs(L.height) }; }"""

_DIST_JS = """() => { const el = document.getElementById('chgDist'), c = el && echarts.getInstanceByDom(el); if (!c) return null;
  const d = c.getOption().series[0].data;
  return { lnk: document.getElementById('chgDistBox').dataset.lnk || '',
    ops: d.map(x => (x && x.itemStyle && x.itemStyle.opacity != null) ? x.itemStyle.opacity : 1),
    bw: d.map(x => (x && x.itemStyle && x.itemStyle.borderWidth) || 0), vals: d.map(x => x.value),
    hl: [...document.querySelectorAll('#mktInner tr.hl')].map(t => t.dataset.code),
    hlBins: [...new Set([...document.querySelectorAll('#mktInner tr.hl')].map(t => t.dataset.bin))],
    pick: (document.getElementById('distPick') || {}).dataset ? document.getElementById('distPick').dataset.bin : null,
    pickOpen: !document.getElementById('distPick').hidden,
    tab: (document.querySelector('#mktTabs button.on') || {}).textContent || '' }; }"""

_NOH = "() => { const y = scrollY; scrollTo({ left: 60, top: y, behavior: 'instant' }); const x = scrollX; scrollTo({ left: 0, top: y, behavior: 'instant' }); return x === 0; }"


def _mkt_ctx(b, W, errs):
    c = b.new_context(viewport={"width": W, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.removeItem('tw.maSecOpen')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
    return c, pg


def _agree(pg):
    a = pg.get_by_role("button", name="同意並繼續")
    if a.count() and a.first.is_visible():
        a.first.click(); pg.wait_for_timeout(300)


def _ma_part(pg, T, W, shot):
    J = lambda js, *a: pg.evaluate(js, *a)
    ready = wait_until(pg, "() => { const e = document.getElementById('maTrend'); return e && window.echarts && echarts.getInstanceByDom(e) && document.querySelectorAll('#mktBody .ma[data-gn]').length > 3; }", 20000)
    if not ok(f"{T}（{W}）#13：站上均線走勢與族群方格畫出來（前置）", bool(ready)):
        return
    pg.wait_for_timeout(500)
    # 方格在收合段裡：展開第一段（網頁 details／手機 m4fold）
    J("() => { const d = document.querySelector('#maSecs details.masec'); if (d && !d.open) d.open = true; const h = document.querySelector('#mktBody .m4fold'); if (h && h.nextElementSibling && h.nextElementSibling.hidden) h.click(); }")
    pg.wait_for_timeout(400)
    gn = J("() => { const e = [...document.querySelectorAll('#mktBody .ma[data-gn]')].find(x => x.checkVisibility()); return e ? e.dataset.gn : null; }")
    if not ok(f"{T}（{W}）#13：有看得到的族群方格（前置）", bool(gn)):
        return
    sel = f'#mktBody .ma[data-gn="{gn}"]'
    s0 = J(_MA_JS)
    ok(f"{T}（{W}）#13：一開始沒有任何線被加粗、預覽線是空的", not s0["wide"] and s0["prevN"] == 0 and s0["m1op"] == 1, s0)
    if W > 640:
        pg.locator(sel).hover(); pg.wait_for_timeout(300)
        s1 = J(_MA_JS)
        ok(f"★ {T}（{W}）#13：滑過方格 → 那個族群的線被畫成粗線（沒勾就用預覽線）、全市場線變淡、方格 .lnk-hl",
           s1["lnk"] == gn and (gn in s1["wide"] or (s1["prevN"] > 50 and s1["prevW"] > 3)) and s1["m1op"] < 1 and s1["hl"] == [gn], s1)
        pg.mouse.move(5, 5); pg.wait_for_timeout(300)
        s2 = J(_MA_JS)
        ok(f"{T}（{W}）#13：滑出 → 全部恢復", s2["lnk"] == "" and s2["prevN"] == 0 and s2["m1op"] == 1 and not s2["hl"], s2)
    h0 = J("() => location.hash")
    pg.locator(sel).click(); pg.wait_for_timeout(400)
    s3 = J(_MA_JS)
    ok(f"★ {T}（{W}）#13：點方格第一下＝選取（還在這頁、線加粗、其他方格變淡）",
       s3["hash"] == h0 and s3["lnk"] == gn and s3["dim"] > 0 and (gn in s3["wide"] or s3["prevN"] > 50), s3)
    if W > 640:
        pg.mouse.move(5, 5); pg.wait_for_timeout(250)
        ok(f"{T}（{W}）#13：鎖定後滑出仍保留", J(_MA_JS)["lnk"] == gn)
        if shot:
            pg.locator("#maTrendBox").scroll_into_view_if_needed()
            pg.locator("#mktBody").screenshot(path=os.path.join(shot, "mkt_link_ma.png"))
    # 點空白（走勢圖卡片的標題列文字）＝取消
    J("() => document.querySelector('#maTrendSub').scrollIntoView({ block: 'center', behavior: 'instant' })")
    pg.locator("#maTrendSub").click(); pg.wait_for_timeout(300)
    s4 = J(_MA_JS)
    ok(f"★ {T}（{W}）#13：點空白處 → 取消選取、全部恢復", s4["lnk"] == "" and s4["dim"] == 0 and s4["prevN"] == 0, s4)
    # 色票：勾一個族群疊上去，滑過它的色票 → 那條線加粗（網頁才有滑過）
    if W > 640:
        J("() => document.querySelector('#maGroupDD .ddbtn').scrollIntoView({ block: 'center', behavior: 'instant' })")
        pg.locator("#maGroupDD .ddbtn").click(); pg.wait_for_timeout(300)
        cb = pg.locator("#maGroupDD .ddlist input[type=checkbox]").first
        nm = cb.get_attribute("data-n"); cb.check(); pg.wait_for_timeout(300)
        pg.keyboard.press("Escape"); pg.mouse.click(5, 300); pg.wait_for_timeout(300)
        if ok(f"{T}（{W}）#13：勾一個族群後出現它的色票（前置）", pg.locator(f'#maGroupKey button.snk[data-n="{nm}"]').count() == 1):
            pg.locator(f'#maGroupKey button.snk[data-n="{nm}"]').hover(); pg.wait_for_timeout(300)
            s5 = J(_MA_JS)
            ok(f"★ {T}（{W}）#13：滑過色票 → 那條線（已疊在圖上）加粗、其他族群線變淡、色票 .hl",
               s5["wide"] == [nm] and s5["prevN"] == 0 and s5["keyHl"] == [nm], s5)
            pg.mouse.move(5, 5); pg.wait_for_timeout(250)
            ok(f"{T}（{W}）#13：滑出色票 → 恢復", not J(_MA_JS)["wide"])
    # 鎖定後再點同一格 → 進族群頁
    J(f"() => document.querySelector('{sel}').scrollIntoView({{ block: 'center', behavior: 'instant' }})")
    pg.locator(sel).click(); pg.wait_for_timeout(450)
    ok(f"{T}（{W}）#13：第一下仍在市場頁", J("() => location.hash").startswith("#market"))
    pg.locator(sel).click(); pg.wait_for_timeout(900)
    ok(f"★ {T}（{W}）#13：鎖定後再點同一格 → 進族群頁", J("() => location.hash").startswith("#industry/group/"), J("() => location.hash"))


def _sn_part(pg, T, W, shot, base):
    J = lambda js, *a: pg.evaluate(js, *a)
    pg.goto(base + "#season", wait_until="networkidle"); pg.reload(wait_until="networkidle"); _agree(pg)
    if not wait_until(pg, "() => { const b = document.querySelector('#seasonView button[data-v=\"line\"]'); return !!b && !!document.querySelector('#seasonHeat canvas'); }", 20000):
        ok(f"{T}（{W}）#14：季節性頁有長條模式鈕（前置）", False); return
    # 手機的期間／指標／圖別收在「設定」抽屜裡（mobile4.js），那顆鈕不在畫面上 —— 這裡只是切到長條模式的前置，直接觸發它自己的 click
    if W > 640:
        pg.locator('#seasonView button[data-v="line"]').click()
    else:
        J("() => document.querySelector('#seasonView button[data-v=\"line\"]').click()")
    pg.wait_for_timeout(900)
    ready = wait_until(pg, "() => { const e = document.getElementById('seasonLine'); const c = e && echarts.getInstanceByDom(e); return c && c.getOption().series.filter(s => String(s.id || '').startsWith('b:')).length >= 2; }", 10000)
    if not ok(f"{T}（{W}）#14：長條模式畫出 ≥ 2 個族群（前置）", bool(ready)):
        return
    s0 = J(_SN_JS); names = s0["names"]
    ok(f"{T}（{W}）#14：一開始全部長條全亮、沒有外框", all(o == 1 for o in s0["ops"]) and not any(s0["bw"]), s0)
    # 找一根夠高的長條（滑鼠停得到）
    pt = None; k = 0
    for k in range(len(names)):
        for m in range(12):
            p = J(_SN_PT_JS, ["b:" + names[k], m])
            if p and p["h"] >= 12:
                pt = p; break
        if pt: break
    if not ok(f"{T}（{W}）#14：找得到一根夠高的長條（前置）", bool(pt)):
        return
    nm = names[k]
    dim = J("() => document.documentElement.getAttribute('data-theme') === 'light' ? 0.35 : 0.55")
    if W > 640:
        pg.mouse.move(pt["x"], pt["y"]); pg.wait_for_timeout(350)
        s1 = J(_SN_JS)
        ok(f"★ {T}（{W}）#14：滑過長條 → 那個族群全亮＋外框、其他變淡、色票 .hl",
           s1["lnk"] == nm and s1["ops"][k] == 1 and s1["bw"][k] > 0 and all(abs(o - dim) < 1e-6 for i, o in enumerate(s1["ops"]) if i != k) and s1["keyHl"] == [nm], s1)
        pg.mouse.move(5, 5); pg.wait_for_timeout(300)
        s2 = J(_SN_JS)
        ok(f"{T}（{W}）#14：滑出 → 全部恢復", s2["lnk"] == "" and all(o == 1 for o in s2["ops"]) and not s2["keyHl"], s2)
        k2 = (k + 1) % len(names); n2 = names[k2]
        pg.locator(f'#seasonKey button.snk[data-n="{n2}"]').hover(); pg.wait_for_timeout(300)
        s3 = J(_SN_JS)
        ok(f"★ {T}（{W}）#14：滑過色票 → 那個族群的長條全亮、其他變淡", s3["lnk"] == n2 and s3["ops"][k2] == 1 and s3["ops"][k] < 1, s3)
        pg.mouse.move(5, 5); pg.wait_for_timeout(200)
        J("() => document.querySelector('#seasonGroupDD .ddbtn').scrollIntoView({ block: 'center', behavior: 'instant' })")
        pg.locator("#seasonGroupDD .ddbtn").click(); pg.wait_for_timeout(350)
        row = pg.locator(f'#seasonGroupDD .ddopt[data-n="{n2}"]')
        if ok(f"{T}（{W}）#14：下拉裡有那個族群的列（前置）", row.count() == 1):
            row.hover(); pg.wait_for_timeout(300)
            s4 = J(_SN_JS)
            ok(f"★ {T}（{W}）#14：滑過下拉那一列 → 那個族群的長條全亮、下拉列 .hl", s4["lnk"] == n2 and s4["ops"][k2] == 1 and s4["ops"][k] < 1 and s4["ddHl"] == [n2], s4)
        pg.keyboard.press("Escape"); pg.mouse.move(5, 5); pg.wait_for_timeout(300)
        J("() => document.body.click()"); pg.wait_for_timeout(200)
        pt = J(_SN_PT_JS, ["b:" + nm, [m for m in range(12) if (J(_SN_PT_JS, ["b:" + nm, m]) or {}).get("h", 0) >= 12][0]])
    h0 = J("() => location.hash")
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(450)
    s5 = J(_SN_JS)
    ok(f"★ {T}（{W}）#14：點長條第一下＝鎖定（不跳頁、那族群全亮、其他變淡）",
       s5["hash"] == h0 and s5["sel"] == nm and s5["ops"][k] == 1 and all(o < 1 for i, o in enumerate(s5["ops"]) if i != k), s5)
    if W > 640:
        pg.mouse.move(5, 5); pg.wait_for_timeout(250)
        ok(f"{T}（{W}）#14：鎖定後滑出仍保留", J(_SN_JS)["sel"] == nm)
        if shot:
            pg.locator("#seasonLine").screenshot(path=os.path.join(shot, "mkt_link_season.png"))
    # 圖內空白（格線上方的留白）＝取消
    r = J("() => { const r = document.getElementById('seasonLine').getBoundingClientRect(); return { x: r.left + 30, y: r.top + 6 }; }")
    pg.mouse.click(r["x"], r["y"]); pg.wait_for_timeout(350)
    s6 = J(_SN_JS)
    ok(f"★ {T}（{W}）#14：點圖的空白處 → 取消、全部恢復", s6["sel"] == "" and all(o == 1 for o in s6["ops"]), s6)
    pt = J(_SN_PT_JS, ["b:" + nm, [m for m in range(12) if (J(_SN_PT_JS, ["b:" + nm, m]) or {}).get("h", 0) >= 12][0]])
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(500)
    pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(900)
    ok(f"★ {T}（{W}）#14：鎖定後再點同一族群 → 進族群頁", J("() => location.hash").startswith("#industry/group/"), J("() => location.hash"))


def _dist_part(pg, T, W, shot, base):
    J = lambda js, *a: pg.evaluate(js, *a)
    pg.goto(base + "#market/updown", wait_until="networkidle"); pg.reload(wait_until="networkidle"); _agree(pg)
    ready = wait_until(pg, "() => { const e = document.getElementById('chgDist'); return e && window.echarts && echarts.getInstanceByDom(e) && document.querySelector('#mktInner tr[data-code]'); }", 15000)
    if not ok(f"{T}（{W}）#15：漲跌分佈與右表畫出來（前置）", bool(ready)):
        return
    pg.wait_for_timeout(400)
    dim = J("() => document.documentElement.getAttribute('data-theme') === 'light' ? 0.35 : 0.55")
    s0 = J(_DIST_JS)
    # 預設停在「漲停」分頁：漲停那幾根有外框、其他不變淡
    if "漲停" in s0["tab"]:
        lit = [i for i, w in enumerate(s0["bw"]) if w > 0]
        ok(f"★ {T}（{W}）#15：停在漲停分頁 → 漲停所在的直條有外框（≥ +8% 那邊）、其他直條不變淡",
           bool(lit) and all(i >= 10 for i in lit) and all(o == 1 for o in s0["ops"]), s0)
    # 切到跌幅前段：外框消失；滑過一列 → 那根亮
    tabs = J("() => [...document.querySelectorAll('#mktTabs button')].map(b => b.textContent)")
    ti = next((i for i, t in enumerate(tabs) if "跌幅前段" in t), None)
    if ti is not None:
        pg.locator(f'#mktTabs button[data-i="{ti}"]').click(); pg.wait_for_timeout(350)
        s1 = J(_DIST_JS)
        ok(f"{T}（{W}）#15：切到跌幅前段 → 沒有常亮的直條", not any(s1["bw"]) and all(o == 1 for o in s1["ops"]), s1)
    if W > 640:
        tr = pg.locator("#mktInner tr[data-code][data-bin]").nth(2)
        code, bn = tr.get_attribute("data-code"), int(tr.get_attribute("data-bin"))
        tr.hover(); pg.wait_for_timeout(300)
        s2 = J(_DIST_JS)
        ok(f"★ {T}（{W}）#15：滑過右表一列 → 它所在那根直條全亮＋外框、其他變淡、那列 .hl",
           s2["lnk"] == str(bn) and s2["ops"][bn] == 1 and s2["bw"][bn] > 0 and all(abs(o - dim) < 1e-6 for i, o in enumerate(s2["ops"]) if i != bn) and s2["hl"] == [code], s2)
        if shot:
            pg.locator("#mktDuo").screenshot(path=os.path.join(shot, "mkt_link_dist.png"))
        pg.mouse.move(5, 5); pg.wait_for_timeout(300)
        s3 = J(_DIST_JS)
        ok(f"{T}（{W}）#15：滑出 → 全部恢復", s3["lnk"] == "" and all(o == 1 for o in s3["ops"]) and not s3["hl"], s3)
    # 點直條：照舊開名單 ＋ 右表落在那根的列 .hl
    s4 = J(_DIST_JS)
    rowbins = J("() => [...document.querySelectorAll('#mktInner tr[data-bin]')].map(t => +t.dataset.bin)")
    bn = max(set(rowbins), key=rowbins.count) if rowbins else None
    if ok(f"{T}（{W}）#15：右表的列帶得出所在直條（前置）", bn is not None):
        p = J("""(i) => { const e = document.getElementById('chgDist'); e.scrollIntoView({ block: 'center', behavior: 'instant' }); const c = echarts.getInstanceByDom(e), r = e.getBoundingClientRect();
          const v = c.getOption().series[0].data[i].value; const p = c.convertToPixel({ seriesIndex: 0 }, [i, Math.max(v, 0) / 2]); const b0 = c.convertToPixel({ seriesIndex: 0 }, [i, 0]);
          return { x: r.left + p[0], y: r.top + ((b0[1] - p[1] < 12) ? b0[1] - 12 : p[1]) }; }""", bn)
        pg.mouse.click(p["x"], p["y"]); pg.wait_for_timeout(500)
        s5 = J(_DIST_JS)
        ok(f"★ {T}（{W}）#15：點直條 → 照舊打開名單、那根全亮其他變淡、右表落在那根的列一起 .hl",
           s5["pickOpen"] and s5["pick"] == str(bn) and s5["ops"][bn] == 1 and all(o < 1 for i, o in enumerate(s5["ops"]) if i != bn)
           and s5["hl"] and s5["hlBins"] == [str(bn)] and len(s5["hl"]) == rowbins.count(bn), s5)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(350)
        s6 = J(_DIST_JS)
        ok(f"{T}（{W}）#15：收起名單 → 直條恢復、右表沒有 .hl", not s6["pickOpen"] and all(o == 1 for o in s6["ops"]) and not s6["hl"], s6)


def t_market_link_1019(b, base, code):
    T = "市場頁連動1019"
    errs: list[str] = []
    shot = os.environ.get("TW_MKTLINK_SHOT")
    for W in (1440, 390):
        c, pg = _mkt_ctx(b, W, errs)
        pg.goto(base + "#market/ma", wait_until="networkidle"); _agree(pg)
        _ma_part(pg, T, W, shot)
        _sn_part(pg, T, W, shot, base)
        _dist_part(pg, T, W, shot, base)
        ok(f"{T}（{W}）：頁面沒有橫向捲軸", pg.evaluate(_NOH))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("市場頁連動1019", lambda pg, b, base, code: t_market_link_1019(b, base, code))
