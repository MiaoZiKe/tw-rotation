# 驗收段落「提示框殘留1106」：圖被整塊換掉／縮放後，ECharts 提示框不能留在畫面（尤其左上角 LOGO 上）
# 由 _uitest.py exec 載入，ok()、wait_until()、ROOT… 直接可用。
# flake8: noqa
#
# 起因（2026-11-06，Andy：「偶爾會跑出左上角那問題 幫我處理不要讓他顯示」）：桌機 #overview 左上角殘留
#   「0:00 ● 走勢（相對大盤） -0.76 ● 資金占比 2.44」。提示框全站掛在 body；圖的容器被 innerHTML 換掉而實例沒 dispose，
#   提示框就永遠留在 body；縮放視窗又把它歸位到 (0,0)。
# 這一段真的把滑鼠停到圖上讓提示框出現，再做兩件事：
#   A 把圖所在的容器整塊換掉（模擬每 5 秒重畫）→ 不能還有可見提示框
#   B 把可見提示框硬貼到 (0,0)、滑鼠移到圖外 → 掃除後不能還有可見提示框；滑鼠回到圖上提示框仍正常出現

VIS_TIPS = """() => [...document.body.children].filter(d => d.style.zIndex === '9999999').filter(d => {
    const cs = getComputedStyle(d); if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return false;
    return (d.textContent || '').trim().length > 0; }).map(d => { const r = d.getBoundingClientRect(); return { t: d.textContent.trim().slice(0, 30), l: Math.round(r.left + scrollX), tp: Math.round(r.top + scrollY) }; })"""


def t_ghost_tip_1106(b, base, code):
    T = "提示框殘留1106"
    ctx = b.new_context(viewport={"width": 1840, "height": 1000}, timezone_id="Asia/Taipei")
    ctx.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = ctx.new_page()
    pg.goto(base + "#overview", wait_until="load"); pg.wait_for_timeout(2500)

    def hover_chart(tries=5):
        # 找一張畫面內、夠大、折線／長條（axis 提示）的圖，滑鼠停在中央偏右
        cid = pg.evaluate("""() => { for (const el of document.querySelectorAll('[_echarts_instance_]')) {
            const r = el.getBoundingClientRect(); if (r.width < 260 || r.height < 120) continue;
            const c = echarts.getInstanceByDom(el); if (!c) continue;
            const o = c.getOption(); if (!o || !o.series || !o.series.some(s => s.type === 'line' || s.type === 'bar')) continue;
            if (!o.xAxis || !o.xAxis[0] || o.xAxis[0].type === 'value') continue;
            el.setAttribute('data-ghostpick', '1'); el.scrollIntoView({ block: 'center' }); return 1; } return 0; }""")
        pt = None
        if cid:
            pg.wait_for_timeout(900)   # 頁面是平滑捲動，等捲完再量位置
            pt = pg.evaluate("""() => { const el = document.querySelector('[data-ghostpick]'); el.removeAttribute('data-ghostpick');
                const r = el.getBoundingClientRect(); return { x: r.left + r.width * 0.55, y: r.top + r.height * 0.5, id: el.id || el.parentElement.id || '' }; }""")
        if not pt:
            if tries > 1:
                pg.wait_for_timeout(1200); return hover_chart(tries - 1)
            return None
        # 長條圖的提示框是「滑到長條上」才出現：沿著圖的中線掃過去，直到真的出現提示框為止
        w = pg.evaluate("() => { const r = [...document.querySelectorAll('[_echarts_instance_]')].map(e => e.getBoundingClientRect()).find(r => Math.abs(r.left + r.width * 0.55 - %f) < 2); return r ? r.width : 400; }" % pt["x"])
        x0 = pt["x"] - w * 0.55
        for k in range(0, 24):
            pg.mouse.move(x0 + w * (0.08 + 0.037 * k), pt["y"]); pg.wait_for_timeout(120)
            if pg.evaluate(VIS_TIPS):
                pt["x"] = x0 + w * (0.08 + 0.037 * k); break
        return pt

    dbg = pg.evaluate("() => [...document.querySelectorAll('[_echarts_instance_]')].map(e => { const r = e.getBoundingClientRect(); return (e.id || '?') + ':' + Math.round(r.width) + 'x' + Math.round(r.height) + ':' + Math.round(r.top) + ':' + (() => { try { const o = echarts.getInstanceByDom(e).getOption(); return (o.series || []).map(q => q.type).join('/') + '|' + (o.xAxis && o.xAxis[0] && o.xAxis[0].type); } catch (x) { return 'err'; } })(); }).join(' ')")
    pt = hover_chart()
    ok(f"【{T}】總覽有可以滑過的折線／長條圖", pt is not None, dbg)
    if not pt:
        ctx.close(); return
    tips = pg.evaluate(VIS_TIPS)
    ok(f"【{T}】滑鼠停在圖上 → 真的出現提示框", len(tips) >= 1, tips)

    # A：整塊換掉圖所在的容器（innerHTML 重寫），舊實例沒被 dispose —— 就是「每 5 秒重畫」的情形
    pg.evaluate("""(id) => { const el = [...document.querySelectorAll('[_echarts_instance_]')].find(e => (e.id || e.parentElement.id || '') === id);
        const host = el.parentElement; window.__orphan = el; host.innerHTML = host.innerHTML; }""", pt["id"])
    pg.wait_for_timeout(1600)
    left = pg.evaluate(VIS_TIPS)
    ok(f"【{T}】A 圖容器被換掉後，畫面上沒有殘留的提示框", len(left) == 0, left)
    ok(f"【{T}】A 被拆下來的舊圖實例已被收掉（不再占記憶體）", pg.evaluate("() => { const e = window.__orphan; return !e || !echarts.getInstanceByDom(e); }"))

    # B：提示框被歸位到 (0,0)（視窗縮放的舊行為），滑鼠不在圖上
    pg.reload(wait_until="load"); pg.wait_for_timeout(2500)
    pt = hover_chart()
    if pt:
        pg.evaluate("""() => { for (const d of document.body.children) if (d.style.zIndex === '9999999') { d.style.left = '0px'; d.style.top = '0px'; d.style.transform = 'none'; } }""")
        pg.evaluate("() => { window.scrollTo(0, 0); }"); pg.mouse.move(5, 500, steps=3)   # 回頁首、移到圖外（側欄上）：Andy 看到的就是這個畫面
        pg.wait_for_timeout(1600)
        import os as _os
        if _os.environ.get("GT_SHOT"):
            pg.screenshot(path=_os.environ["GT_SHOT"], clip={"x": 0, "y": 0, "width": 900, "height": 420})
        left = pg.evaluate(VIS_TIPS)
        ok(f"【{T}】B 提示框貼在左上角 (0,0) 時被藏起來", len(left) == 0, left)
        # 回到圖上：提示框仍然正常（保險不能誤殺）
        pt = hover_chart()
        tips = pg.evaluate(VIS_TIPS) if pt else []
        ok(f"【{T}】B 滑鼠回到圖上，提示框照常出現、不在 (0,0)", len(tips) >= 1 and all(t["l"] > 8 or t["tp"] > 8 for t in tips), tips)
    else:
        ok(f"【{T}】B 找得到可滑過的圖", False)
    # C：換路由後也不留
    pg.evaluate("() => { location.hash = '#flow'; }"); pg.wait_for_timeout(1800)
    left = pg.evaluate(VIS_TIPS)
    pg.mouse.move(5, 500)
    pg.wait_for_timeout(600)
    left = pg.evaluate(VIS_TIPS)
    ok(f"【{T}】C 換到資金流向後（滑鼠離開圖），沒有殘留的提示框", len(left) == 0, left)
    ctx.close()


register("提示框殘留1106", lambda pg, b, base, code: t_ghost_tip_1106(b, base, code))
