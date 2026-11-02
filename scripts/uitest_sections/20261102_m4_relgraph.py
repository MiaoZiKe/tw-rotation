# 驗收段落「手機關聯圖一屏1102」—— 2026-11-02 Andy：手機產業地圖「確保每個功能每個按鈕都被使用過」，普查留下「關聯圖在 390 寬左右被切、只能拖、沒有提示」。
# 由 _uitest.py 用 exec 載入（ok()、fails… 直接可用，不要 import _uitest；不要寫三引號模組說明）。
# flake8: noqa
#
# 做法：360／390／430 ＋ is_mobile ＋ has_touch ＋ DPR2。每一項都驗「畫面真的因此改變」：
#   ① 一開頁：導覽列（.relmini）在、欄數鈕＝圖的欄數、全部鈕都在畫面內（量 getBoundingClientRect）、整頁不橫向捲、圖右緣淡出（rgR）、導覽列與圖頂在同一屏（bottom ≤ 視窗高）。
#   ② 手指拖（CDP dispatchTouchEvent，真的 touchstart／touchmove／touchend）→ scrollLeft 變大、亮的欄鈕換了、左緣淡出（rgL）出現。
#   ③ 點欄位鈕「最後一欄」→ 圖真的捲到最右、讀數變成「第 N 欄」、右緣淡出消失、›鈕停用。
#   ④ 雙指縮放（CDP 兩指 dispatchTouchEvent）→ 圖的寬度真的變了（縮小或放大）；「全景」鈕 → 圖縮到剛好一屏寬、按鈕變「回到 100%」、再按回原寬。
#   ⑤ 點公司節點 → 說明卡出現；點說明卡的公司名連結 → 換到個股頁。
def t_m4_relgraph1102(b, base):
    T = "手機關聯圖一屏1102"
    for vw in (390, 360, 430):
        ctx = b.new_context(viewport={"width": vw, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('rg1102')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.m4.3danim','0'); localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'t'})); localStorage.setItem('tw.tour','*'); sessionStorage.setItem('rg1102','1'); } }catch(e){}")
        m = ctx.new_page()
        errs = []
        m.on("pageerror", lambda e: errs.append(str(e)))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = m.evaluate
        cdp = ctx.new_cdp_session(m)
        # 手指手勢一律用 CDP Input.dispatchTouchEvent 一格一格送（真的 touchstart／touchmove／touchend）。
        # ⚠ 不用 Input.synthesizeScrollGesture／synthesizePinchGesture：這個無頭模擬環境下它們不會讓捲動容器動（實測 scrollLeft 0→0），不是網站的錯。
        def tev(t, pts):
            cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": pts})
        def swipe(x, y, dx):
            tev("touchStart", [{"x": x, "y": y}])
            for i in range(1, 11):
                tev("touchMove", [{"x": x + dx * i / 10, "y": y}]); m.wait_for_timeout(16)
            tev("touchEnd", []); m.wait_for_timeout(500)
        def pinch(x, y, f):
            d0 = 60.0
            tev("touchStart", [{"x": x - d0 / 2, "y": y, "id": 1}, {"x": x + d0 / 2, "y": y, "id": 2}])
            for i in range(1, 13):
                d = d0 * (1 + (f - 1) * i / 12)
                tev("touchMove", [{"x": x - d / 2, "y": y, "id": 1}, {"x": x + d / 2, "y": y, "id": 2}]); m.wait_for_timeout(16)
            tev("touchEnd", []); m.wait_for_timeout(500)
        def tap_el(js):
            xy = J(f"() => {{ const e = ({js})(); if (!e) return null; e.scrollIntoView({{ block: 'center', behavior: 'instant' }}); const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }}")
            m.wait_for_timeout(250)
            xy = J(f"() => {{ const e = ({js})(); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }}")
            if xy:
                m.touchscreen.tap(xy[0], xy[1])
            m.wait_for_timeout(700)
            return xy
        ST = """() => { const h = document.querySelector('.view.on #chainMap'), s = h && h.querySelector('svg'), mi = document.querySelector('.view.on .relmini');
            return { sl: Math.round(h.scrollLeft), sw: h.scrollWidth, cw: h.clientWidth, svgw: Math.round(s.getBoundingClientRect().width), L: h.classList.contains('rgL'), R: h.classList.contains('rgR'),
                     on: mi ? [...mi.querySelectorAll('.rgc.on')].map(c => c.textContent).join(',') : '', txt: mi ? mi.querySelector('.rgt').textContent : '', z: mi ? mi.querySelector('.rgz').textContent : '',
                     nR: mi ? mi.querySelector('.rgp[data-d="1"]').disabled : null, doc: document.documentElement.scrollWidth }; }"""
        try:
            for cid, ncol in (("ai_server", 6), ("semiconductor", 4)):
                tag = f"{vw}／{cid}"
                m.goto(base + f"#industry/{cid}/overview", wait_until="domcontentloaded"); m.wait_for_timeout(3800)
                J("() => { document.querySelector('#relSec').scrollIntoView({ block: 'start', behavior: 'instant' }); scrollBy({ top: -70, behavior: 'instant' }); }"); m.wait_for_timeout(500)
                # ① 一開頁
                g = J("""() => { const mi = document.querySelector('.view.on .relmini'), h = document.querySelector('.view.on #chainMap'); if (!mi || mi.hidden) return null;
                    const cs = [...mi.querySelectorAll('.rgc')].map(c => c.getBoundingClientRect()); const hr = h.getBoundingClientRect(), mr = mi.getBoundingClientRect();
                    return { n: cs.length, inside: cs.every(r => r.left >= 0 && r.right <= innerWidth), minH: Math.min(...cs.map(r => r.height)), miniBottom: Math.round(mr.bottom), mapTop: Math.round(hr.top), H: innerHeight }; }""")
                if not ok(f"【{T}】{tag}：一開頁就有欄位導覽列", bool(g), g):
                    continue
                ok(f"【{T}】{tag}：欄位鈕 {g['n']} 顆＝圖的欄數 {ncol}，且全部在畫面內", g["n"] == ncol and g["inside"], g)
                ok(f"【{T}】{tag}：欄位鈕可點高度 ≥ 36（{g['minH']}）", g["minH"] >= 36, g)
                ok(f"【{T}】{tag}：導覽列與圖頂同一屏（導覽列底 {g['miniBottom']}、圖頂 {g['mapTop']} ≤ {g['H']}）", g["miniBottom"] <= g["H"] and g["mapTop"] < g["H"] - 120, g)
                s0 = J(ST)
                ok(f"【{T}】{tag}：整頁沒有橫向捲動（{s0['doc']} ≤ {vw}）", s0["doc"] <= vw, s0)
                ok(f"【{T}】{tag}：圖比框寬（{s0['sw']}＞{s0['cw']}）→ 右緣淡出提示（rgR）亮著、左緣沒有", s0["sw"] > s0["cw"] and s0["R"] and not s0["L"], s0)
                ok(f"【{T}】{tag}：讀數寫明「共 {ncol} 欄」與上下游方向（{s0['txt']}）", f"共 {ncol} 欄" in s0["txt"] and "上游" in s0["txt"], s0)
                # ② 手指拖
                ctr = J("() => { const r = document.querySelector('.view.on #chainMap').getBoundingClientRect(); return [r.left + r.width / 2, r.top + Math.min(r.height, 300) / 2]; }")
                swipe(ctr[0], ctr[1], -150)
                s1 = J(ST)
                ok(f"【{T}】{tag}：手指左滑 → 圖真的捲了（scrollLeft {s0['sl']}→{s1['sl']}）、左緣淡出出現", s1["sl"] > s0["sl"] + 40 and s1["L"], (s0, s1))
                ok(f"【{T}】{tag}：滑過之後亮著的欄鈕換了（{s0['on']}→{s1['on']}）", s1["on"] != s0["on"], (s0, s1))
                # ③ 點最後一欄
                tap_el(f"() => [...document.querySelectorAll('.view.on .relmini .rgc')].pop()")
                m.wait_for_timeout(700)
                s2 = J(ST)
                ok(f"【{T}】{tag}：點最後一欄鈕 → 圖捲到最右（{s1['sl']}→{s2['sl']}／最大 {s2['sw'] - s2['cw']}）、右緣淡出消失、›停用", s2["sl"] >= s2["sw"] - s2["cw"] - 6 and not s2["R"] and s2["nR"] is True, s2)
                ok(f"【{T}】{tag}：讀數換成最後一欄（{s2['txt']}）", f"第 {ncol}" in s2["txt"] or f"–{ncol} 欄" in s2["txt"], s2)
                # 點第 1 欄回來
                tap_el("() => document.querySelector('.view.on .relmini .rgc')")
                m.wait_for_timeout(700)
                s3 = J(ST)
                ok(f"【{T}】{tag}：點第 1 欄鈕 → 捲回最左（{s3['sl']}）", s3["sl"] <= 12 and not s3["L"], s3)
                # ④ 雙指縮放
                J("() => document.querySelector('.view.on #chainMap').scrollIntoView({ block: 'center', behavior: 'instant' })"); m.wait_for_timeout(400)
                ctr = J("() => { const r = document.querySelector('.view.on #chainMap').getBoundingClientRect(); return [r.left + r.width / 2, r.top + Math.min(r.height, 400) / 2]; }")
                w0 = J(ST)["svgw"]
                pinch(ctr[0], ctr[1], 0.6)
                s4 = J(ST)
                ok(f"【{T}】{tag}：雙指捏合 → 圖真的縮小（寬 {w0}→{s4['svgw']}）、導覽按鈕變「回到 100%」（{s4['z']}）", s4["svgw"] < w0 - 40 and s4["z"] == "回到 100%", (w0, s4))
                pinch(ctr[0], ctr[1], 1.8)
                s5 = J(ST)
                ok(f"【{T}】{tag}：雙指張開 → 圖又變大（寬 {s4['svgw']}→{s5['svgw']}）", s5["svgw"] > s4["svgw"] + 40, (s4, s5))
                # 全景鈕
                tap_el("() => document.querySelector('.view.on .relmini .rgz')")
                s6 = J(ST)
                if s6["z"] == "全景":    # 縮放後剛好又是 100%，按鈕還是「全景」→ 再按一次進全景
                    tap_el("() => document.querySelector('.view.on .relmini .rgz')"); s6 = J(ST)
                ok(f"【{T}】{tag}：全景 → 整張縮到一屏寬（圖寬 {s6['svgw']}／框寬 {s6['cw']}），不必再拖", s6["svgw"] <= s6["cw"] + 3, s6)
                tap_el("() => document.querySelector('.view.on .relmini .rgz')")
                s7 = J(ST)
                ok(f"【{T}】{tag}：再按「回到 100%」→ 回原寬（{s7['svgw']}）、按鈕變回「全景」", s7["svgw"] >= w0 - 2 and s7["z"] == "全景", s7)
                # ⑤ 點公司節點 → 說明卡 → 名字連結（只在半導體那條，節點要先展開環節）
                if cid == "semiconductor" and vw == 390:
                    for k in range(8):
                        if J("() => [...document.querySelectorAll('.view.on #chainMap .co')].filter(e => e.getClientRects().length).length"):
                            break
                        tap_el(f"() => [...document.querySelectorAll('.view.on #chainMap g.segtitle')].filter(e => e.getClientRects().length)[{k}]")
                    n_co = J("() => [...document.querySelectorAll('.view.on #chainMap .co')].filter(e => e.getClientRects().length).length")
                    if ok(f"【{T}】{tag}：點環節標題後出現公司節點（{n_co}）", n_co > 0):
                        tap_el("() => [...document.querySelectorAll('.view.on #chainMap .co')].filter(e => e.getClientRects().length)[0]")
                        okc = J("() => { const c = document.getElementById('coBox'); return !!(c && c.getClientRects().length && c.innerText.trim().length > 10); }")
                        ok(f"【{T}】{tag}：點公司節點 → 說明卡真的出現", okc)
                        href = J("() => { const a = document.querySelector('#coBox h3 a'); return a ? a.getAttribute('href') : null; }")
                        if okc and href:
                            tap_el("() => document.querySelector('#coBox h3 a')")
                            ok(f"【{T}】{tag}：點說明卡的公司名 → 換到個股頁（{href}→{J('() => location.hash')}）", J("() => location.hash").startswith(href))
            ok(f"【{T}】{vw}：0 個 pageerror（{len(errs)}）", not errs, errs[:3])
        finally:
            ctx.close()
    # 淺色：390 看一眼導覽列與淡出有出來（不橫向捲、鈕在畫面內）
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    ctx.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.m4.3danim','0'); localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'t'})); localStorage.setItem('tw.tour','*'); localStorage.setItem('tw.theme','light'); }catch(e){}")
    m = ctx.new_page(); m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    try:
        m.goto(base + "#industry/ai_server/overview", wait_until="domcontentloaded"); m.wait_for_timeout(3800)
        r = m.evaluate("() => ({ th: document.documentElement.dataset.theme, mi: !!document.querySelector('.view.on .relmini:not([hidden])'), doc: document.documentElement.scrollWidth })")
        ok(f"【{T}】390 淺色：導覽列在、整頁不橫向捲（{r}）", r["th"] == "light" and r["mi"] and r["doc"] <= 390, r)
    finally:
        ctx.close()


register("手機關聯圖一屏1102", lambda pg, b, base, code: t_m4_relgraph1102(b, base), after="手機產業地圖普查1102")
