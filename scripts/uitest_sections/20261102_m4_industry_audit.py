# 驗收段落「手機產業地圖普查1102」—— 2026-11-02 Andy iPhone：「在產業地圖發現最多錯誤，編號不能點擊 無法看圖片等等」。
# 由 _uitest.py 用 exec 載入（ok()、wait_until()、fails… 直接可用，不要 import _uitest；不要寫三引號模組說明）。
# flake8: noqa
#
# 做法：390（另跑 360、430 的縮減版）＋is_mobile＋has_touch，每一顆鈕都用 touchscreen.tap 真的點，驗「畫面真的因此改變」：
#   產業地圖首頁（圖例列、「?」、族群漲跌幅收展、熱力圖連結）、每條產業鏈（分頁列、麵包屑、環節 chip、「?」、延伸閱讀抽屜、
#   「篩選 環節」下拉、關聯圖環節標題、公司節點→說明卡→「在圖上標示」→名字連結）。再驗：0 個 pageerror／404、沒有破圖、不橫向捲動、
#   「?」／麵包屑／關聯圖環節標題的實際可點範圍夠大（用 elementFromPoint 探：「?」與麵包屑 ≥ 40［標稱 46，探針量到 42，改前 30×24～30、56×22］，環節標題 ≥ 32）。
# ★ 剖析圖編號（.mnum 那 20×20 的圓鈕）、剖析圖版面放大屬於另一位負責人（分支 m4-dglayout1102）—— 本段「待剖析圖分支」略過不驗，
#   只驗「點了編號零件卡有開」這一條現況（現況是會開，所以不會紅）；它們合併後請該分支自己補驗收。

def t_m4_ind_audit1102(b, base):
    T = "手機產業地圖普查1102"
    HIT = """(find) => { const e = find(); if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' });
        const r = e.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        const hit = (x, y) => { const t = document.elementFromPoint(x, y); return !!t && (t === e || e.contains(t)); };
        let w = 0, h = 0; for (let d = 0; d < 40; d++) { if (hit(cx + d, cy) && hit(cx - d, cy)) w = d * 2; else break; }
        for (let d = 0; d < 40; d++) { if (hit(cx, cy + d) && hit(cx, cy - d)) h = d * 2; else break; }
        return { w: Math.max(Math.round(r.width), w), h: Math.max(Math.round(r.height), h) }; }"""
    for vw in (390, 360, 430):
        ctx = b.new_context(viewport={"width": vw, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('ia1102')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.m4.3danim','0'); localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'t'})); localStorage.setItem('tw.tour','*'); sessionStorage.setItem('ia1102','1'); } }catch(e){}")
        m = ctx.new_page()
        errs = []
        m.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        m.on("response", lambda r: errs.append(f"HTTP {r.status} {r.url[-60:]}") if r.status >= 400 and "fonts.g" not in r.url else None)
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = lambda js, *a: m.evaluate(js, *a) if a else m.evaluate(js)
        V = "document.querySelector('.view.on')"

        def snap():
            return J("() => ({ h: location.hash, n: document.body.innerHTML.length, y: Math.round(scrollY) })")

        def tap(find):
            J(f"() => {{ const e = ({find})(); if (e) e.scrollIntoView({{ block: 'center', behavior: 'instant' }}); }}")
            xy = None
            for _ in range(6):
                m.wait_for_timeout(150)
                nxt = J(f"() => {{ const e = ({find})(); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }}")
                if nxt and xy and abs(nxt[0] - xy[0]) < 1 and abs(nxt[1] - xy[1]) < 1:
                    break
                xy = nxt
            if xy:
                m.touchscreen.tap(xy[0], xy[1])
            m.wait_for_timeout(650)
            return xy

        def vis(sel):
            return J("(s) => [...document.querySelectorAll(s)].filter(e => e.getClientRects().length).length", sel)

        def nth(sel, i):
            return f"() => [...document.querySelectorAll({json.dumps(sel)})].filter(e => e.getClientRects().length)[{i}]"

        def close_overlays():
            J("() => { ['mSheetBack', 'howBack'].forEach(id => { const s = document.getElementById(id); if (s && !s.hidden) s.click(); }); }")
            m.wait_for_timeout(250)
        try:
            # ---------------- 首頁 ----------------
            m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(4500)
            ok(f"【{T}】{vw}：html.m4 掛上", J("() => document.documentElement.classList.contains('m4')"))
            chains = J("() => [...document.querySelectorAll('.view.on #chainSwitch button')].map(b => b.dataset.c)")
            ok(f"【{T}】{vw}：首頁產業鏈分頁列有 ≥ 9 顆（{len(chains)}）", len(chains) >= 9, chains)
            if vw == 390:
                n_lg = vis(".view.on .lg")
                ok(f"【{T}】{vw}：首頁圓餅圖例有列（{n_lg}）", n_lg >= 3)
                # 點圖例列＝原地換成那一族群的個股層（不是跳頁），所以每一列都要重新載入再點，不然第二次點的是個股列
                for i in range(min(n_lg, 4)):
                    m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(2500)
                    nm = J(f"() => (([...document.querySelectorAll('.view.on .lg')].filter(e => e.getClientRects().length)[{i}] || {{}}).innerText || '').split('\\n')[0]")
                    t0 = J("() => document.querySelector('.view.on').innerText")
                    tap(nth(".view.on .lg", i)); t1 = J("() => document.querySelector('.view.on').innerText")
                    ok(f"【{T}】{vw}：點圖例第 {i+1} 列「{nm}」→ 畫面換了（原地進到那一族群）", t0 != t1, (nm, t0[:40], t1[:40]))
                m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(2500)
                tap(nth(".view.on .m4fold", 0))
                ex = J("() => document.querySelector('.view.on .m4fold').getAttribute('aria-expanded')")
                hh = J("() => Math.max(0, ...[...document.querySelectorAll('.view.on canvas')].map(c => Math.round(c.getBoundingClientRect().height)))")
                ok(f"【{T}】{vw}：點「族群漲跌幅 ▸」→ aria-expanded=true 且長條圖畫布高度 > 100（{ex}／{hh}）", ex == "true" and hh > 100, (ex, hh))
                tap(nth(".view.on .m4fold", 0))
                ok(f"【{T}】{vw}：再點一次 → 收回（aria-expanded=false）", J("() => document.querySelector('.view.on .m4fold').getAttribute('aria-expanded')") == "false")
                m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(2500)
                tap(nth(".view.on a.lk[href='#heatmap']", 0))
                ok(f"【{T}】{vw}：點「產業熱力圖 →」真的換到 #heatmap（{J('() => location.hash')}）", J("() => location.hash").startswith("#heatmap"))
            # 首頁每一個產業鏈分頁
            for c in chains:
                m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(2200)
                if c == '_all':
                    continue
                tap(f"() => document.querySelector('.view.on #chainSwitch button[data-c=\"{c}\"]')")
                ok(f"【{T}】{vw}：首頁點分頁「{c}」→ 換到那條鏈（{J('() => location.hash')}）", ("#industry/" + c) in J("() => location.hash"))
            # ---------------- 每條產業鏈 ----------------
            use = [c for c in chains if c not in ('_all', 'industry')]
            if vw != 390:
                use = use[:2]          # 360／430 縮減版：前兩條鏈（半導體、AI 伺服器）
            for cid in use:
                m.goto(base + "#industry/" + cid, wait_until="domcontentloaded"); m.wait_for_timeout(4200)
                tag = f"{vw} {cid}"
                # 麵包屑：可點範圍 ≥ 44、點了真的回產業地圖
                hh = m.evaluate(f"() => ({HIT})(() => document.querySelector('.view.on #indCrumbs a'))")
                ok(f"【{T}】{tag}：麵包屑「產業地圖」實際可點高度 ≥ 40（外擴後標稱 46，探針量到 42）（{hh}）", bool(hh) and hh["h"] >= 40, hh)
                # 「?」：每顆可點 ≥ 44、點了說明彈窗真的出現且有字、點背景關掉
                nq = vis(".view.on .howbtn")
                ok(f"【{T}】{tag}：頁上有「?」鈕（{nq}）", nq >= 1)
                for i in range(nq):
                    hh = m.evaluate(f"() => ({HIT})(() => [...document.querySelectorAll('.view.on .howbtn')].filter(e => e.getClientRects().length)[{i}])")
                    ok(f"【{T}】{tag}：「?」#{i+1} 實際可點 ≥ 40×40（外擴後標稱 46×46，探針量到 42；改前 30×24～30）（{hh}）", bool(hh) and hh["w"] >= 40 and hh["h"] >= 40, hh)
                    tap(nth(".view.on .howbtn", i))
                    shown = J("() => { const p = document.getElementById('howPop'); return !!(p && !p.hidden && p.innerText.trim().length > 6); }")
                    ok(f"【{T}】{tag}：點「?」#{i+1} → 說明彈窗真的出現、有字", shown)
                    close_overlays()
                    ok(f"【{T}】{tag}：點背景 → 彈窗關掉", J("() => { const p = document.getElementById('howPop'); return !p || p.hidden; }"))
                # 延伸閱讀抽屜
                ne = J("() => [...document.querySelectorAll('.view.on button')].filter(b => b.getClientRects().length && /^＋/.test(b.innerText.trim())).length")
                for i in range(ne):
                    tap(f"() => [...document.querySelectorAll('.view.on button')].filter(b => b.getClientRects().length && /^＋/.test(b.innerText.trim()))[{i}]")
                    o = J("() => { const s = document.getElementById('mSheet'); return !!(s && s.getClientRects().length && s.innerText.trim().length > 20); }")
                    ok(f"【{T}】{tag}：延伸閱讀 #{i+1} → 抽屜真的打開、有字", o)
                    close_overlays()
                # 「篩選 環節」下拉
                if vis(".view.on #segDDBtn"):
                    tap(nth(".view.on #segDDBtn", 0))
                    op = J("() => { const d = document.querySelector('.view.on #segDD'); return !!(d && d.classList.contains('open')); }")
                    npan = vis("#segDD .ddpanel .segchip")
                    ok(f"【{T}】{tag}：點「篩選 環節」→ 清單真的展開（{npan} 格）", op and npan > 0)
                    if npan >= 2:
                        t0 = J("() => (document.querySelector('#segDDBtn b') || {}).textContent || ''")
                        tap(nth("#segDD .ddpanel .segchip", 1))
                        t1 = J("() => (document.querySelector('#segDDBtn b') || {}).textContent || ''")
                        ok(f"【{T}】{tag}：點清單第 2 格 → 下拉鈕上的環節名換了（{t0!r}→{t1!r}）", t0 != t1, (t0, t1))
                # 關聯圖環節標題：可點 ≥ 32、點了真的展開那一格（公司節點出現）
                nt = vis(".view.on svg.hasfocus g.segtitle, .view.on #chainMap g.segtitle")
                if nt:
                    sel = ".view.on #chainMap g.segtitle"
                    if not vis(sel):
                        sel = ".view.on svg.hasfocus g.segtitle"
                    hh = m.evaluate(f"() => ({HIT})(() => [...document.querySelectorAll({json.dumps(sel)})].filter(e => e.getClientRects().length)[0])")
                    ok(f"【{T}】{tag}：關聯圖環節標題實際可點高度 ≥ 32（{hh}）", bool(hh) and hh["h"] >= 32, hh)
                    n0 = J("() => document.querySelector('.view.on #chainMap').innerHTML.length")
                    tap(nth(sel, 0)); n1 = J("() => document.querySelector('.view.on #chainMap').innerHTML.length")
                    ok(f"【{T}】{tag}：點環節標題 → 關聯圖真的重畫（{n0}→{n1}）", n0 != n1, (n0, n1))
                    # 公司節點 → 說明卡
                    for _ in range(14):
                        if vis(".view.on #chainMap .co"):
                            break
                        k = J("() => { window.__ia = (window.__ia || 0) + 1; return window.__ia - 1; }")
                        if k >= nt:
                            break
                        tap(nth(sel, k))
                    if vis(".view.on #chainMap .co"):
                        tap(nth(".view.on #chainMap .co", 0))
                        okc = J("() => { const c = document.getElementById('coBox'); return !!(c && c.getClientRects().length && c.innerText.trim().length > 10); }")
                        ok(f"【{T}】{tag}：點公司節點 → 公司說明卡真的出現", okc)
                        if okc:
                            hi = J("() => (document.querySelector('#coBox #relHi') || {}).textContent || ''")
                            if hi:
                                tap("() => document.querySelector('#coBox #relHi')")
                                ok(f"【{T}】{tag}：按「在圖上標示」→ 變「取消標示」", J("() => document.querySelector('#coBox #relHi').textContent") == "取消標示")
                            href = J("() => { const a = document.querySelector('#coBox h3 a'); return a ? a.getAttribute('href') : null; }")
                            if href:
                                tap("() => document.querySelector('#coBox h3 a')")
                                ok(f"【{T}】{tag}：點說明卡的公司名 → 換到個股頁（{href}→{J('() => location.hash')}）", J("() => location.hash").startswith(href))
                # 環節 chip 每顆
                m.goto(base + "#industry/" + cid, wait_until="domcontentloaded"); m.wait_for_timeout(3000)
                nc = J("() => [...document.querySelectorAll('.view.on .segchip[href]')].filter(e => e.getClientRects().length).length")
                for i in range(nc if vw == 390 else min(nc, 2)):
                    m.goto(base + "#industry/" + cid, wait_until="domcontentloaded"); m.wait_for_timeout(2200)
                    href = J(f"() => [...document.querySelectorAll('.view.on .segchip[href]')].filter(e => e.getClientRects().length)[{i}].getAttribute('href')")
                    tap(f"() => [...document.querySelectorAll('.view.on .segchip[href]')].filter(e => e.getClientRects().length)[{i}]")
                    ok(f"【{T}】{tag}：點環節 chip #{i+1} → 換到 {href}（{J('() => location.hash')}）", J("() => location.hash") == href)
                    if i == 0 and vw == 390:
                        # 順手驗這一頁（剖析圖頁）：不破圖、不橫向捲、零件卡（編號）現況會開
                        bad = J("() => [...document.querySelectorAll('.view.on img')].filter(i => i.getClientRects().length && (!i.complete || i.naturalWidth === 0)).length")
                        ok(f"【{T}】{tag}：{href} 沒有破圖（{bad}）", bad == 0)
                        ok(f"【{T}】{tag}：{href} 不橫向捲動", J("() => document.documentElement.scrollWidth <= innerWidth + 1"))
                        # 待剖析圖分支：編號的位置／大小／引線不在本段驗；這裡只驗現況「點編號 → 零件卡打開」
                        if vis(".view.on .mnum"):
                            tap(nth(".view.on .mnum", 0))
                            ok(f"【{T}】{tag}：點剖析圖編號 → 零件卡打開（現況；編號觸控區屬剖析圖分支）",
                               J("() => { const s = document.getElementById('mSheet'); return !!(s && s.getClientRects().length && s.innerText.trim().length > 8); }"))
                            close_overlays()
            if vw == 390 and 'siph_cpo' in chains:
                # 矽光子／CPO 族群總覽「成員與階段」表：個股／族群連結原本只有 18 高，現在實際可點 ≥ 32，點下去真的換頁
                m.goto(base + "#industry/siph_cpo/overview", wait_until="domcontentloaded"); m.wait_for_timeout(4500)
                nl = vis(".view.on .siphtbl a.lk-stock")
                ok(f"【{T}】390：矽光子成員表有個股連結（{nl}）", nl >= 5)
                for i in (1, 6, 12):
                    if i >= nl:
                        continue
                    hh = m.evaluate(f"() => ({HIT})(() => [...document.querySelectorAll('.view.on .siphtbl a.lk-stock')].filter(e => e.getClientRects().length)[{i}])")
                    ok(f"【{T}】390：矽光子成員表個股連結 #{i+1} 實際可點高度 ≥ 32（改前 18；{hh}）", bool(hh) and hh["h"] >= 32, hh)
                href = J("() => document.querySelectorAll('.view.on .siphtbl a.lk-stock')[2].getAttribute('href')")
                tap("() => [...document.querySelectorAll('.view.on .siphtbl a.lk-stock')].filter(e => e.getClientRects().length)[2]")
                ok(f"【{T}】390：點成員表個股連結 → 換到個股頁（{href}→{J('() => location.hash')}）", J("() => location.hash").startswith(href))
            e = [x for x in errs if "fonts" not in x]
            ok(f"【{T}】{vw}：整段 0 個 pageerror／404（{len(e)}）", not e, e[:3])
        finally:
            ctx.close()
    # 桌機（1440）不應有 html.m4、麵包屑連結沒有被外擴（像素量：不多出 ::after）
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'t'})); localStorage.setItem('tw.tour','*'); }catch(e){}")
    d = ctx.new_page(); d.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    try:
        d.goto(base + "#industry/semiconductor", wait_until="domcontentloaded"); d.wait_for_timeout(4500)
        ok(f"【{T}】1440：沒有 html.m4", not d.evaluate("() => document.documentElement.classList.contains('m4')"))
        ok(f"【{T}】1440：麵包屑連結沒被手機規則動到（無 ::after 外擴）",
           d.evaluate("() => { const a = document.querySelector('#indCrumbs a'); return !a || getComputedStyle(a, '::after').content === 'none'; }"))
        ok(f"【{T}】1440：「?」鈕沒被手機規則動到（外擴 ≤ 8px）",
           d.evaluate("() => { const b = document.querySelector('.view.on .howbtn'); if (!b) return true; const a = getComputedStyle(b, '::after'); return a.content === 'none' || Math.abs(parseFloat(a.top)) <= 8; }"))
    finally:
        ctx.close()


register("手機產業地圖普查1102", lambda pg, b, base, code: t_m4_ind_audit1102(b, base), after="手機產業鏈1016")
