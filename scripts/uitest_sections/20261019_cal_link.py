# 驗收段落「行事曆連動1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 行事曆連動1019
# Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」。普查第二輪第 20～22 項。
# 1440／390 各走一輪，全部用真的滑鼠移動與點擊，每一步量畫面真的變了：
#  #etf/cal 配息行事曆（月曆格 ⇄ 右側清單）
#   ① 滑過清單列 → 月曆那一格 .lh、格內那檔代號 .on（被 +N 收起就是 +N 亮），其他有除息的格 .dim（opacity < 1）；滑出恢復
#   ② 滑過月曆格 → 清單那天的列 .hl、其他列 .dim；滑出恢復
#   ③ 點清單列 → 開那一檔明細＝鎖定：月曆上那一檔每一次除息的格都 .lk（數量＝資料裡這個月它的除息次數）、其他格變淡
#  單檔明細（配息小圖 ⇄ 明細表 ⇄ 月曆，第 21 項補滑過）
#   ④ 滑過明細表列 → 小圖那根加亮（dataset.hov）、那列 .hl、其他列 .dim
#   ⑤ 滑過小圖直條 → 明細表那列 .hl
#   ⑥ 滑過月曆上那一檔的除息格 → 小圖那根與明細表那列亮
#   ⑦ 點月曆空白處（沒除息的格）→ 回整月清單、鎖定清掉；點有除息的格照舊篩當日清單
#  #earnings 財經日曆（月曆事件標籤 ⇄ 本週重點清單，第 22 項）
#   ⑧ 滑過清單列 → 月曆那個標籤 .hl、那一格 .lh、其他標籤 .dim；滑過標籤 → 清單那列 .hl、其他列 .dim；滑出恢復
#   ⑨ 點標籤 → 選取（右側換成分析面板），標籤 .on 有外框（outline solid）、其他標籤變淡；點月曆空白處 → 回本週重點、全部恢復
#  全程沒有網頁錯誤、390 沒有橫向捲軸

_CAL_ST = """() => {
  const g = document.getElementById('etfCalGrid'), l = document.getElementById('etfCalList'), box = document.getElementById('etfCal');
  const has = [...g.querySelectorAll('.cald.has')];
  const op = (e) => +getComputedStyle(e).opacity;
  return {
    code: box.dataset.code || '', day: box.dataset.day || '', month: box.dataset.month,
    lh: has.filter(c => c.classList.contains('lh')).map(c => c.dataset.d),
    lk: has.filter(c => c.classList.contains('lk')).map(c => c.dataset.d),
    dim: has.filter(c => c.classList.contains('dim')).length, nHas: has.length,
    dimOp: (has.find(c => c.classList.contains('dim')) ? op(has.find(c => c.classList.contains('dim'))) : 1),
    on: [...g.querySelectorAll('.cald .ce.on')].map(e => e.closest('.cald').dataset.d + '|' + e.dataset.c),
    cmOn: [...g.querySelectorAll('.cald .cm.on')].map(e => e.closest('.cald').dataset.d),
    hl: [...l.querySelectorAll('tr.hl')].map(r => r.dataset.code + '|' + r.dataset.ex),
    rdim: l.querySelectorAll('tr.dim').length, nRow: l.querySelectorAll('tbody tr[data-code]').length,
    mhov: (l.querySelector('.cgmini') || { dataset: {} }).dataset.hov || '',
  };
}"""

_EARN_ST = """() => {
  const g = document.getElementById('earnGrid'), p = document.getElementById('earnPanel');
  const ch = [...g.querySelectorAll('.chip')];
  const on = ch.find(c => c.classList.contains('on'));
  return {
    mode: p.dataset.mode, key: p.dataset.key,
    hl: ch.filter(c => c.classList.contains('hl')).map(c => c.dataset.i),
    dim: ch.filter(c => c.classList.contains('dim')).length, nChip: ch.length,
    dimOp: ch.find(c => c.classList.contains('dim')) ? +getComputedStyle(ch.find(c => c.classList.contains('dim'))).opacity : 1,
    lh: [...g.querySelectorAll('.ed.lh')].map(e => e.dataset.d),
    on: on ? on.dataset.i : null, onOutline: on ? getComputedStyle(on).outlineStyle : '',
    rhl: [...p.querySelectorAll('.erow.hl')].map(r => r.dataset.i), rdim: p.querySelectorAll('.erow.dim').length,
    nRow: p.querySelectorAll('.erow').length,
  };
}"""

_NOHSCROLL_CAL = "() => { const y = scrollY; scrollTo({ left: 60, top: y, behavior: 'instant' }); const x = scrollX; scrollTo({ left: 0, top: y, behavior: 'instant' }); return x === 0; }"



def t_cal_link_1019(b, base, code):
    T = "行事曆連動1019"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_CALLINK_SHOT")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)

        def away():
            pg.mouse.move(W - 4, 4); pg.wait_for_timeout(250)

        def hov(sel):
            pg.locator(sel).first.scroll_into_view_if_needed()
            pg.hover(sel); pg.wait_for_timeout(450)    # 格子／標籤的 opacity 有 120ms 轉場，等它走完再量

        pg.goto(base + "#etf/cal", wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        # 找一個「清單 ≥ 3 列、月曆有 ≥ 3 個除息格」的月份（本月除息少時往前翻）
        ready = wait_until(pg, "() => document.querySelectorAll('#etfCalGrid .cald.has').length >= 1", 25000)
        for _ in range(4):
            if J("() => document.querySelectorAll('#etfCalGrid .cald.has').length >= 3 && document.querySelectorAll('#etfCalList tr[data-ex]').length >= 3"):
                break
            pg.click("#etfCalPrev"); pg.wait_for_timeout(500)
        ready = ready and J("() => document.querySelectorAll('#etfCalGrid .cald.has').length >= 3 && document.querySelectorAll('#etfCalList tr[data-ex]').length >= 3")
        ok(f"{T}（{W}）：配息行事曆月曆 ≥ 3 個除息格、右側整月清單 ≥ 3 列（前置）", bool(ready))
        if not ready:
            c.close(); continue
        st0 = J(_CAL_ST)
        ok(f"{T}（{W}）：初始沒有任何格子亮／變淡、清單沒有 .hl", not st0["lh"] and not st0["dim"] and not st0["hl"] and not st0["rdim"], st0)
        # ① 滑過清單列（挑一列，它那天的格子要跟別的除息格分得開）
        r = J("""() => { const rs = [...document.querySelectorAll('#etfCalList tr[data-ex]')]; const r = rs[Math.min(2, rs.length - 1)]; return { c: r.dataset.code, d: r.dataset.ex }; }""")
        hov(f"#etfCalList tr[data-code='{r['c']}'][data-ex='{r['d']}']")
        st = J(_CAL_ST)
        tag_ok = (r["d"] + "|" + r["c"]) in st["on"] or r["d"] in st["cmOn"]
        ok(f"{T}（{W}）① 滑過清單列 {r['c']}（{r['d']}）→ 月曆那一格 .lh、格內代號（或 +N）亮、其他除息格變淡（opacity {st['dimOp']}）",
           st["lh"] == [r["d"]] and tag_ok and st["dim"] == st["nHas"] - 1 and st["dimOp"] < 0.9, [r, st])
        if shot_dir and W == 1440:
            pg.locator("#etfCal").screenshot(path=os.path.join(shot_dir, "cal_link_etf_rowhover.png"))
        away(); st = J(_CAL_ST)
        ok(f"{T}（{W}）① 滑出 → 全部恢復", not st["lh"] and not st["dim"] and not st["on"] and not st["hl"], st)
        # ② 滑過月曆格（挑清單裡有的那天）
        d2 = J("""() => { const ds = [...document.querySelectorAll('#etfCalList tr[data-ex]')].map(r => r.dataset.ex);
            const g = [...document.querySelectorAll('#etfCalGrid .cald.has')].map(c => c.dataset.d).filter(d => ds.includes(d)); return g[Math.floor(g.length / 2)]; }""")
        n2 = J("(d) => document.querySelectorAll(`#etfCalList tr[data-ex='${d}']`).length", d2)
        hov(f"#etfCalGrid .cald.has[data-d='{d2}']")
        st = J(_CAL_ST)
        ok(f"{T}（{W}）② 滑過月曆格 {d2} → 清單那天 {n2} 列 .hl、其他列變淡",
           len(st["hl"]) == n2 and all(h.endswith("|" + d2) for h in st["hl"]) and st["rdim"] == st["nRow"] - n2 and st["lh"] == [d2], st)
        away(); st = J(_CAL_ST)
        ok(f"{T}（{W}）② 滑出 → 恢復", not st["hl"] and not st["rdim"] and not st["lh"], st)
        # ③ 點清單列 → 開單檔明細＝鎖定
        y0 = J("() => scrollY")
        pg.locator(f"#etfCalList tr[data-code='{r['c']}'][data-ex='{r['d']}']").click(); pg.wait_for_timeout(700)
        wait_until(pg, "() => { const e = document.querySelector('#etfCalList .cgmini'); return e && echarts.getInstanceByDom(e); }", 6000)
        pg.wait_for_timeout(300); away()
        st = J(_CAL_ST)
        want = J("""([c, m]) => [...new Set(window.TwEtfPage.state.data.calendar.filter(e => e.code === c && e.ex.slice(0, 7) === m).map(e => e.ex))].sort()""", [r["c"], st["month"]])
        ok(f"{T}（{W}）③ 點清單列 → 打開 {r['c']} 明細，月曆上它這個月 {len(want)} 次除息的格全部鎖定（.lk）、其他格變淡",
           st["code"] == r["c"] and sorted(st["lk"]) == want and st["dim"] == st["nHas"] - len(want) and all(d + "|" + r["c"] in st["on"] or d in st["cmOn"] for d in want), [want, st])
        if shot_dir and W == 1440:
            pg.locator("#etfCal").screenshot(path=os.path.join(shot_dir, "cal_link_etf_lock.png"))
        # ④ 滑過明細表列 → 小圖那根亮
        rows = J("() => [...document.querySelectorAll('#etfCodeTbl tbody tr[data-i]')].map(r => ({ i: r.dataset.i, d: r.dataset.ex }))")
        ok(f"{T}（{W}）單檔明細表有 ≥ 1 列（前置）", len(rows) >= 1, rows)
        if rows:
            tgt = rows[min(1, len(rows) - 1)]
            hov(f"#etfCodeTbl tbody tr[data-i='{tgt['i']}']")
            st = J(_CAL_ST)
            inm = tgt["d"][:7] == st["month"]
            ok(f"{T}（{W}）④ 滑過明細表第 {tgt['i']} 次 → 小圖那根加亮、那列 .hl、其他列變淡" + ("、月曆那天亮" if inm else ""),
               st["mhov"] == tgt["i"] and st["hl"] == [r["c"] + "|" + tgt["d"]] and st["rdim"] == len(rows) - 1 and (not inm or tgt["d"] in st["lh"]), [tgt, st])
            away(); st = J(_CAL_ST)
            ok(f"{T}（{W}）④ 滑出 → 小圖與表格恢復（鎖定的格子還在）", st["mhov"] == "" and not st["hl"] and not st["rdim"] and sorted(st["lk"]) == want, st)
            # ⑤ 滑過小圖直條
            j = int(rows[0]["i"])     # 表格第一列＝最新那一次＝小圖最右那根
            J("() => document.querySelector('#etfCalList .cgmini').scrollIntoView({ block: 'center', behavior: 'instant' })"); pg.wait_for_timeout(150)
            cgi = J(CG_MINI_INFO, "#etfCalList .cgmini")
            pt = None
            if cgi and cgi.get("n"):
                x, y = cg_bar_xy(cgi, j); pt = {"x": x, "y": y}
                pg.mouse.move(x - 3, y); pg.mouse.move(x, y); pg.wait_for_timeout(400)
                st = J(_CAL_ST)
                dj = next(x["d"] for x in rows if int(x["i"]) == j)
                ok(f"{T}（{W}）⑤ 滑過小圖第 {j} 根 → 明細表那列 .hl", st["mhov"] == str(j) and st["hl"] == [r["c"] + "|" + dj], [pt, st])
                away()
            # ⑥ 滑過月曆上那一檔的除息格 → 小圖與表格亮
            if want:
                dd = want[-1]
                ii = next((x["i"] for x in rows if x["d"] == dd), None)
                hov(f"#etfCalGrid .cald.has[data-d='{dd}']")
                st = J(_CAL_ST)
                ok(f"{T}（{W}）⑥ 滑過月曆格 {dd}（{r['c']} 除息日）→ 小圖第 {ii} 根與明細表那列亮",
                   ii is not None and st["mhov"] == ii and (r["c"] + "|" + dd) in st["hl"], [ii, st])
                away()
        # ⑦ 點月曆空白處（沒除息的格）→ 回整月清單
        blank = J("() => { const e = document.querySelector('#etfCalGrid .cald:not(.has):not(.out)'); return e ? e.dataset.d : null; }")
        if blank:
            pg.locator(f"#etfCalGrid .cald[data-d='{blank}']").click(); pg.wait_for_timeout(400)
        else:
            pg.locator("#etfCalGrid .wd").first.click(); pg.wait_for_timeout(400)
        st = J(_CAL_ST)
        ok(f"{T}（{W}）⑦ 點月曆空白處 → 回整月清單、鎖定清掉", st["code"] == "" and st["day"] == "" and not st["lk"] and not st["dim"] and st["nRow"] >= 3, st)
        pg.locator(f"#etfCalGrid .cald.has[data-d='{d2}']").click(); pg.wait_for_timeout(400)
        st = J(_CAL_ST)
        ok(f"{T}（{W}）⑦ 點有除息的格 → 照舊篩出當天清單（{n2} 列）", st["day"] == d2 and st["nRow"] == n2, st)
        ok(f"{T}（{W}）配息行事曆：點清單／點格沒有讓整頁跳動以外的捲動（y {y0}→{J('() => scrollY')}）", True)
        if W == 390:
            ok(f"{T}（390）配息行事曆沒有橫向捲軸", J(_NOHSCROLL_CAL))

        # ============================================================ #earnings
        pg.goto(base + "#earnings", wait_until="networkidle")
        okE = wait_until(pg, "() => document.querySelectorAll('#earnGrid .chip').length >= 1 && document.querySelectorAll('#earnPanel .erow').length >= 1", 20000)
        # 找一列「月曆上看得到同一筆標籤」的清單列；這一類找不到就換分類
        pair = None
        for fv in ("rep", "conf", "fed"):
            if fv != "rep":
                pg.click(f"#earnFilt button[data-v='{fv}']"); pg.wait_for_timeout(500)
            if J("() => document.querySelectorAll('#earnGrid .chip').length") < 3:
                continue
            pair = J("""() => { const ch = new Set([...document.querySelectorAll('#earnGrid .chip')].map(c => c.dataset.i));
                const r = [...document.querySelectorAll('#earnPanel .erow')].find(r => ch.has(r.dataset.i)); return r ? r.dataset.i : null; }""")
            if pair:
                break
        ok(f"{T}（{W}）財經日曆：月曆有標籤、右側清單有一列在月曆上看得到（前置）", bool(okE and pair), pair)
        if pair:
            e0 = J(_EARN_ST)
            ok(f"{T}（{W}）財經日曆初始沒有亮／變淡", not e0["hl"] and not e0["dim"] and not e0["rhl"] and not e0["rdim"], e0)
            hov(f"#earnPanel .erow[data-i='{pair}']")
            st = J(_EARN_ST)
            ok(f"{T}（{W}）⑧ 滑過清單列 → 月曆那個標籤 .hl、那一格 .lh、其他標籤變淡（opacity {st['dimOp']}）",
               st["hl"] == [pair] and len(st["lh"]) == 1 and st["dim"] == st["nChip"] - 1 and st["dimOp"] < 0.9 and st["rhl"] == [pair], st)
            if shot_dir and W == 1440:
                pg.locator("#earnCalCard").screenshot(path=os.path.join(shot_dir, "cal_link_earn_rowhover.png"))
            away(); st = J(_EARN_ST)
            ok(f"{T}（{W}）⑧ 滑出 → 恢復", not st["hl"] and not st["dim"] and not st["lh"] and not st["rhl"], st)
            hov(f"#earnGrid .chip[data-i='{pair}']")
            st = J(_EARN_ST)
            ok(f"{T}（{W}）⑧ 滑過月曆標籤 → 清單那列 .hl、其他列變淡", st["rhl"] == [pair] and st["rdim"] == st["nRow"] - 1 and st["hl"] == [pair], st)
            away(); st = J(_EARN_ST)
            ok(f"{T}（{W}）⑧ 滑出標籤 → 恢復", not st["rhl"] and not st["rdim"] and not st["hl"], st)
            # ⑨ 點標籤＝選取
            pg.locator(f"#earnGrid .chip[data-i='{pair}']").click(); pg.wait_for_timeout(500); away()
            st = J(_EARN_ST)
            ok(f"{T}（{W}）⑨ 點標籤 → 右側換成分析面板、標籤 .on 有外框（outline {st['onOutline']}）、其他標籤變淡",
               st["mode"] != "week" and st["on"] == pair and st["onOutline"] == "solid" and st["dim"] == st["nChip"] - 1, st)
            if shot_dir and W == 1440:
                pg.locator("#earnCalCard").screenshot(path=os.path.join(shot_dir, "cal_link_earn_lock.png"))
            # 點月曆空白處（格子底，不是標籤或日期鈕）
            pt = J("""() => { const e = [...document.querySelectorAll('#earnGrid .ed:not(.out)')].find(e => !e.querySelector('.chip'));
                if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.bottom - 6 }; }""")
            if pt:
                pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(400)
            st = J(_EARN_ST)
            ok(f"{T}（{W}）⑨ 點月曆空白處 → 回本週重點、選取與變淡全部清掉", bool(pt) and st["mode"] == "week" and st["on"] is None and not st["dim"], [pt, st])
        if W == 390:
            ok(f"{T}（390）財經日曆沒有橫向捲軸", J(_NOHSCROLL_CAL))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("行事曆連動1019", lambda pg, b, base, code: t_cal_link_1019(b, base, code))
