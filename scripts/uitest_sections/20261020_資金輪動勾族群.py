# 驗收段落「資金輪動勾族群1020」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 資金輪動勾族群1020
# 事故（2026-10-20）：#flow/rotation 的「族群」下拉依序勾 晶圓代工／HPC 與網通 IC／矽晶圓，
#   每勾一個就丟 TypeError「reading 'width'」，右邊「族群資金排行」只剩族群名、長條全不見。
#   根因：softenOption 替「全為非負值的單一橫條」補底軌（showBackground），篩到只剩正值族群時底軌由關轉開，
#   ECharts 5.5.1 這條更新路徑用舊索引取新版面而中斷（修在 app.js 的 bgFlipReset）。
# 桌機 1800×1080 與手機 390×844 各跑一次：真的打開下拉、一個一個勾，每勾一個都量
#   ① 排行的類別數＝已勾數　② 真的畫出來（寬度 > 0、沒被略過）的長條數＝已勾數　③ 整段沒有 pageerror


def t_rot_pick_groups_1020(b, base, code):
    T = "資金輪動勾族群1020"
    GIDS = ["foundry", "hpc_network_ic", "silicon_wafer"]
    for (w, h) in ((1800, 1080), (390, 844)):
        errs: list[str] = []
        c = b.new_context(viewport={"width": w, "height": h})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#flow/rotation", wait_until="domcontentloaded")
        if not wait_until(pg, "() => { const e = document.getElementById('rankFlow'); return !!e && !!window.echarts && !!echarts.getInstanceByDom(e); }", 20000):
            ok(f"{T}（{w}）：族群資金排行畫出來", False); c.close(); continue
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        pg.wait_for_timeout(800)
        dd = pg.locator('#flowRotFilter .rotdd[data-dd="group"]')
        if not dd.count():
            ok(f"{T}（{w}）：篩選列有「族群」下拉", False); c.close(); continue
        for k, gid in enumerate(GIDS, 1):
            if not dd.locator(".ddpanel").is_visible():
                dd.locator(".ddbtn").click(); pg.wait_for_timeout(300)
            cb = dd.locator(f'input[data-g="{gid}"]')
            if not cb.count():
                ok(f"{T}（{w}）：下拉裡有族群 {gid}", False); break
            cb.first.check(force=True)
            wait_until(pg, f"""() => {{ const e = document.getElementById('rankFlow'); const i = e && echarts.getInstanceByDom(e);
                const o = i && i.getOption(); return !!o && o.yAxis[0].data.length === {k}; }}""", 5000)
            pg.wait_for_timeout(700)               # rotRedraw 是 rAF＋setTimeout，再等補間跑完
            m = pg.evaluate("""() => { const e = document.getElementById('rankFlow'); const i = e && echarts.getInstanceByDom(e);
                if (!i) return null; const o = i.getOption(); const d = i.getModel().getSeriesByIndex(0).getData();
                let n = 0; for (let j = 0; j < d.count(); j++) { const g = d.getItemGraphicEl(j);
                  if (g && !g.ignore && g.shape && Math.abs(g.shape.width) > 0.5) n++; }
                return { cats: o.yAxis[0].data, bars: n, w: e.clientWidth, h: e.clientHeight }; }""")
            good = bool(m) and len(m["cats"]) == k and m["bars"] == k and m["w"] > 0 and m["h"] > 0
            ok(f"{T}（{w}）：勾第 {k} 個族群（{gid}）後排行有 {k} 根長條", good, m)
        ok(f"{T}（{w}）：勾族群過程沒有頁面例外", not errs, errs[:3])
        c.close()


register("資金輪動勾族群1020", lambda pg, b, base, code: t_rot_pick_groups_1020(b, base, code))
