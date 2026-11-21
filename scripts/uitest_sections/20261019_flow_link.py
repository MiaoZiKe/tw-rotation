# 驗收段落「資金流向連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 資金流向連動1019（Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」）
# 規格：docs/style_guide.md 第十八節；普查表 docs/chart_link_census_1019.md 第 8、9 項。1440／390 各走一遍，全部用真的滑鼠：
#   #flow/sankey（資金分流樹 ⇄ 右欄資金流向排名）
#     ① 滑過排名列 → 樹上那個族群成為外部焦點（FlowTopo.probe().ext）、不相關的族群 fade 真的降到 .55（深色）、那一列 .hl
#     ② 滑過樹上的族群點 → 那一列 .hl；滑開 → .hl 消失
#     ③ 點列第一下＝鎖定（dataset.sel、樹的焦點），成分股面板「沒有」打開；點空白（排名說明那一行）＝取消、fade 全回 1
#     ④ 同一列點兩下 → 成分股面板打開（第二下才進下一層）
#   #flow/rotation（足跡輪盤 ⇄ 族群資金排行）
#     ⑤ 滑過輪盤族群點 → 排行那一根全亮、其他根 opacity 真的變成 .55；滑開恢復
#     ⑥ 滑過排行長條 → 輪盤 _hiGid 換成那個族群
#     ⑦ 點輪盤族群點＝鎖定：排行同步亮、成分股面板沒開（不蓋住排行）；點排行空白處＝取消
#     ⑧ 同一根長條點兩下 → 成分股面板打開；全程沒有網頁錯誤


def t_flow_link_1019(b, base, code):
    T = "資金流向連動1019"
    errs: list[str] = []
    shots = os.environ.get("TW_FLOWLINK_SHOT")          # 給一個資料夾：存 1440 的滑過／鎖定截圖
    for w in (1440, 390):
        c = b.new_context(viewport={"width": w, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#flow/sankey", wait_until="domcontentloaded")
        agree = pg.get_by_role("button", name="同意並繼續")
        try:
            agree.first.wait_for(state="visible", timeout=2500); agree.first.click(); pg.wait_for_timeout(300)
        except Exception:
            pass
        topo = wait_until(pg, "() => !!(window.App && App.sankeyTopoOn && App.sankeyTopoOn() && document.querySelectorAll('#sankeyRank:not([hidden]) .skr-r').length >= 3)", 15000)
        if not ok(f"{T}（{w}）：資金分流樹（Canvas）與右欄排名都畫出來了", bool(topo)):
            c.close(); continue
        P = """() => { const t = App.sankeyTopo(), bx = document.getElementById('sankeyRank');
            return { ext: t.ext, hover: t.hover, extDim: t.extDim, fade: t.fade, sel: bx.dataset.sel || '',
                     hl: [...bx.querySelectorAll('.skr-r.hl')].map(r => r.dataset.gid),
                     panel: !document.getElementById('sankeyPanel').hidden }; }"""
        pg.evaluate("() => document.getElementById('sankeyRank').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(300)
        row = pg.locator("#sankeyRank .skr-r").nth(1); gid = row.get_attribute("data-gid")
        row.hover(); pg.wait_for_timeout(350)
        s = pg.evaluate(P)
        lo = min(s["fade"].values()) if s["fade"] else 1
        ok(f"{T}（{w}）：① 滑過排名列 → 樹上那個族群突顯、其他變淡（.55）、那一列 .hl",
           s["ext"] == "g:" + gid and s["fade"].get("g:" + gid) == 1 and abs(lo - 0.55) < 0.01 and s["hl"] == [gid], {k: s[k] for k in ("ext", "hover", "extDim", "hl")} | {"lo": lo, "own": s["fade"].get("g:" + gid)})
        if shots and w == 1440:
            pg.screenshot(path=os.path.join(shots, "flow_link_sankey_hover.png"))
        pg.mouse.move(2, 450); pg.wait_for_timeout(250)
        s = pg.evaluate(P)
        ok(f"{T}（{w}）：滑開 → 焦點取消、全部回到 1、沒有列亮著", s["ext"] is None and set(s["fade"].values()) == {1} and not s["hl"], s["hl"])
        # ② 滑過樹上的族群點（挑一個排名表上也有的族群）
        rk = pg.evaluate("() => [...document.querySelectorAll('#sankeyRank .skr-r')].map(r => r.dataset.gid)")
        pg.evaluate("() => document.getElementById('sankey').scrollIntoView({block:'start',behavior:'instant'})"); pg.wait_for_timeout(300)
        # 只挑畫面內、不在固定標題列底下的點（手機的樹比一屏高）
        nd = pg.evaluate("(rk) => App.sankeyTopo().nodes.filter(n => n.lv === 2 && rk.includes(n.key.slice(2)) && n.cy > 120 && n.cy < innerHeight - 60).map(n => [n.key.slice(2), n.cx, n.cy])", rk)
        if ok(f"{T}（{w}）：樹上找得到排名表裡的族群點", bool(nd), rk):
            g2, x, y = nd[0]
            pg.mouse.move(x, y); pg.wait_for_timeout(350)
            s = pg.evaluate(P)
            ok(f"{T}（{w}）：② 滑過樹上的族群點 → 右欄那一列 .hl", s["hl"] == [g2], [g2, s["hl"]])
            pg.mouse.move(2, 450); pg.wait_for_timeout(250)
            ok(f"{T}（{w}）：滑開樹 → 那一列 .hl 消失", not pg.evaluate(P)["hl"])
        # ③ 點列＝鎖定；點空白＝取消
        pg.evaluate("() => document.getElementById('sankeyRank').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(250)
        row.click(); pg.mouse.move(2, 450); pg.wait_for_timeout(300)
        s = pg.evaluate(P)
        ok(f"{T}（{w}）：③ 點列第一下＝鎖定（樹上突顯、列 .hl），成分股面板沒開",
           s["sel"] == gid and s["ext"] == "g:" + gid and s["hl"] == [gid] and not s["panel"] and min(s["fade"].values()) < 1, s | {"fade": None})
        if shots and w == 1440:
            pg.screenshot(path=os.path.join(shots, "flow_link_sankey_lock.png"))
        pg.locator("#sankeyRank .skr-k").click(); pg.wait_for_timeout(300)
        s = pg.evaluate(P)
        ok(f"{T}（{w}）：點空白（排名說明那一行）→ 取消鎖定、樹全亮", s["sel"] == "" and s["ext"] is None and set(s["fade"].values()) == {1} and not s["hl"], s | {"fade": None})
        # ④ 點兩下 → 成分股面板
        row = pg.locator(f"#sankeyRank .skr-r[data-gid='{gid}']")
        row.click(); pg.wait_for_timeout(200); row.click()
        ok(f"{T}（{w}）：④ 同一列點第二下 → 成分股面板打開", bool(wait_until(pg, "() => !document.getElementById('sankeyPanel').hidden", 4000)))

        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)   # 收掉成分股面板（下鑽狀態是全頁共用的，不收的話輪盤那邊的面板會先開著）
        wait_until(pg, "() => document.getElementById('sankeyPanel').hidden", 3000)
        # ===== #flow/rotation：足跡輪盤 ⇄ 族群資金排行
        pg.goto(base + "#flow/rotation", wait_until="domcontentloaded")
        got = wait_until(pg, "() => { const el = document.getElementById('rankFlow'); return !!(el && el._rfRows && window.echarts && echarts.getInstanceByDom(document.getElementById('rotClock'))); }", 15000)
        if not ok(f"{T}（{w}）：輪盤與族群資金排行都畫出來了", bool(got)):
            c.close(); continue
        pg.wait_for_timeout(1500)                        # 輪盤補間跑完，點的位置才是定位
        RF = """() => { const el = document.getElementById('rankFlow'), c = echarts.getInstanceByDom(el);
            const d = c.getOption().series[0].data;
            return { focus: el.dataset.focus || '', ops: d.map(x => [x.gid, (x.itemStyle || {}).opacity]),
                     hi: document.getElementById('rotClock')._hiGid || null,
                     panel: !document.getElementById('rankPanel').hidden }; }"""
        DOTS = """() => { const el = document.getElementById('rotClock'), c = echarts.getInstanceByDom(el), o = c.getOption();
            const si = o.series.findIndex(s => s.type === 'scatter'), b = el.getBoundingClientRect();
            const rf = document.getElementById('rankFlow')._rfRows.map(g => g.group_id);
            return o.series[si].data.filter(d => d && d.row && !d.row.isStock && rf.includes(d.row.gid))
              .map(d => { const q = c.convertToPixel({ seriesIndex: si }, [d.value[0], d.value[1]]); return [d.row.gid, b.left + q[0], b.top + q[1]]; })
              .filter(p => p[2] > 0 && p[2] < innerHeight); }"""
        BARS = """() => { const el = document.getElementById('rankFlow'), c = echarts.getInstanceByDom(el), b = el.getBoundingClientRect();
            return el._rfRows.map((g, i) => { const q = c.convertToPixel({ seriesIndex: 0 }, [g.share_chg / 2, i]); return [g.group_id, b.left + q[0], b.top + q[1]]; })
              .filter(p => p[2] > 0 && p[2] < innerHeight); }"""
        pg.evaluate("() => document.getElementById('rotClock').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
        dots = pg.evaluate(DOTS)
        if not ok(f"{T}（{w}）：輪盤上找得到排行裡也有的族群點", bool(dots)):
            c.close(); continue
        g, x, y = dots[0]
        pg.mouse.move(x, y); pg.wait_for_timeout(450)
        r = pg.evaluate(RF)
        dims = sorted(set(o[1] for o in r["ops"] if o[0] != g))
        ok(f"{T}（{w}）：⑤ 滑過輪盤族群點 → 排行那一根全亮、其他根 opacity 變成 .55",
           r["focus"] == g and dict(r["ops"]).get(g) == 1 and dims == [0.55], [g, r["focus"], dims])
        if shots and w == 1440:
            pg.screenshot(path=os.path.join(shots, "flow_link_rot_hover.png"))
        pg.mouse.move(2, 450); pg.wait_for_timeout(400)
        r = pg.evaluate(RF)
        ok(f"{T}（{w}）：滑開 → 排行全部回到 1", r["focus"] == "" and all(o[1] == 1 for o in r["ops"]), r["focus"])
        # ⑥ 滑過長條 → 輪盤跟著亮
        pg.evaluate("() => document.getElementById('rankFlow').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(400)
        dg = set(d[0] for d in dots)
        bars = [bb for bb in pg.evaluate(BARS) if bb[0] in dg] or pg.evaluate(BARS)
        gb, bx, by = bars[-1]
        pg.mouse.move(bx, by); pg.wait_for_timeout(450)
        r = pg.evaluate(RF)
        ok(f"{T}（{w}）：⑥ 滑過排行長條 → 輪盤那個族群變焦點（_hiGid）、排行同步", r["hi"] == gb and r["focus"] == gb, [gb, r["hi"], r["focus"]])
        pg.mouse.move(2, 450); pg.wait_for_timeout(400)
        # ⑦ 點輪盤族群點＝鎖定
        pg.evaluate("() => document.getElementById('rotClock').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(500)
        g, x, y = pg.evaluate(DOTS)[0]
        pg.mouse.click(x, y); pg.mouse.move(2, 450); pg.wait_for_timeout(600)
        r = pg.evaluate(RF)
        ok(f"{T}（{w}）：⑦ 點輪盤族群點＝鎖定 → 排行那一根同步亮、成分股面板沒有蓋住排行",
           r["focus"] == g and r["hi"] == g and not r["panel"] and sorted(set(o[1] for o in r["ops"] if o[0] != g)) == [0.55], [g, r["focus"], r["hi"], r["panel"]])
        if shots and w == 1440:
            pg.screenshot(path=os.path.join(shots, "flow_link_rot_lock.png"))
        pg.evaluate("() => document.getElementById('rankFlow').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(300)
        bp = pg.evaluate("() => { const b = document.getElementById('rankFlow').getBoundingClientRect(); return [b.left + 16, b.top + 5]; }")
        pg.mouse.click(*bp); pg.wait_for_timeout(500)
        r = pg.evaluate(RF)
        ok(f"{T}（{w}）：點排行空白處 → 取消鎖定（兩張圖都回到全亮）", r["focus"] == "" and r["hi"] is None and all(o[1] == 1 for o in r["ops"]), [r["focus"], r["hi"]])
        # ⑧ 同一根點兩下 → 面板
        gb, bx, by = pg.evaluate(BARS)[-1]
        pg.mouse.click(bx, by); pg.wait_for_timeout(500)
        r1 = pg.evaluate(RF)
        pg.mouse.click(bx, by)
        opened = wait_until(pg, "() => !document.getElementById('rankPanel').hidden", 4000)
        ok(f"{T}（{w}）：⑧ 長條第一下只鎖定、第二下才展開成分股面板", r1["focus"] == gb and not r1["panel"] and bool(opened), [gb, r1["focus"], r1["panel"], opened])
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("資金流向連動1019", lambda pg, b, base, code: t_flow_link_1019(b, base, code))
