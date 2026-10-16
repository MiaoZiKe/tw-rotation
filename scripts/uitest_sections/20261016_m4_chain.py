# 驗收段落「手機產業鏈1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

def t_m4_chain1016(b, base):
    """★ 2026-10-16 Andy iPhone（390）兩件事，一律真的用手指點：
    1.「產業地圖那邊，不該出現這樣的說明框了……只會出現 關聯圖 和 上面的2D 3D 圖以及公司的說明卡」
       → 手機產業鏈頁用「篩選 環節」下拉點任何一格，都不准長出環節詳情 #segBox／跨鏈比較卡（「切到這條鏈看 →」）／「其他產業鏈」列。
       改前：下拉選「IC 設計」等跨鏈環節 → #segBox 1400px 高、3 張 .xchain 卡（每條鏈每一格都紅）。
    2.「說明卡最下方為何有個空白方框，點選後就是股票頁面，這拿掉，因為點選股票名稱即可連結到個股分頁」
       → 公司說明卡 #coBox 裡不准有「沒字、沒圖」的框（連結／按鈕），也不准有字跟底同色的按鈕；
         名字本身是 #stock/<代號> 連結、點下去真的換到個股頁；「在圖上highlight」改繁中（不准有 highlight）。
       改前：最下面那顆「看個股頁 →」是 .btn.primary 深色字＋主題 v4 半透明底（對比 1.0），看起來就是空框。
    360／390／430 三種寬度；390 走過每一條產業鏈的每一格。⚠ --workers 1"""
    T = "手機產業鏈1016"
    AUD = """(root) => {
      const rgba = s => { const m = (s || '').match(/[\\d.]+/g); if (!m) return [0,0,0,0]; return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1]; };
      const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); };
      const hasImg = el => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e); if (/gradient|url/.test(cs.backgroundImage)) return true; if (rgba(cs.backgroundColor)[3] >= .95) return false; } return false; };
      const effBg = el => { const st = []; for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const c = rgba(getComputedStyle(e).backgroundColor); if (c[3] > 0) st.push(c); if (c[3] >= .95) break; }
        let o = rgba(getComputedStyle(document.body).backgroundColor); if (o[3] === 0) o = [10, 15, 25, 1];
        for (let i = st.length - 1; i >= 0; i--) { const c = st[i]; o = [0, 1, 2].map(k => c[k] * c[3] + o[k] * (1 - c[3])); } return o; };
      const box = document.querySelector(root); if (!box) return null;
      const bad = [];
      box.querySelectorAll('*').forEach(e => {
        if (e.closest('svg')) return;
        const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
        if (r.width < 14 || r.height < 14 || !e.getClientRects().length || cs.visibility === 'hidden' || +cs.opacity < .2) return;
        const bordered = parseFloat(cs.borderTopWidth) > 0 || parseFloat(cs.borderBottomWidth) > 0 || parseFloat(cs.borderLeftWidth) > 0;
        const clickable = /^(A|BUTTON)$/.test(e.tagName);
        if (!bordered && !clickable) return;
        const txt = (e.innerText || '').trim();
        const media = e.querySelector('img,svg,canvas,i,video');
        const pc = x => { const c = getComputedStyle(e, x).content; return c && c !== 'none' && c !== '""'; };
        if (!txt && !media && !pc('::before') && !pc('::after') && !e.getAttribute('aria-label')) { bad.push({ k: '空框', tag: e.tagName, cls: String(e.className).slice(0, 40), href: e.getAttribute('href'), w: Math.round(r.width), h: Math.round(r.height) }); return; }
        if (clickable && txt && !hasImg(e)) { const L1 = lum(rgba(cs.color)), L2 = lum(effBg(e)); const cr = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
          if (cr < 2) bad.push({ k: '字跟底同色', tag: e.tagName, txt: txt.slice(0, 16), cr: +cr.toFixed(2) }); }
      });
      return { bad, title: (box.querySelector('h3 a') || {}).getAttribute ? box.querySelector('h3 a').getAttribute('href') : null,
               hi: (box.querySelector('#relHi') || {}).textContent || '', text: box.innerText };
    }"""
    for vw in (390, 360, 430):
        ctx = b.new_context(viewport={"width": vw, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{ if(!sessionStorage.getItem('ch1016')){ localStorage.clear(); localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); localStorage.setItem('tw.m4.3danim','0'); sessionStorage.setItem('ch1016','1'); } }catch(e){}")
        m = ctx.new_page()
        m.on("pageerror", lambda e: fails.append(f"{T} pageerror: {e} @ {m.url}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        J = lambda js: m.evaluate(js)

        def tap(js_find):
            J(f"() => {{ const e = ({js_find})(); if (e) e.scrollIntoView({{ block: 'center', behavior: 'instant' }}); }}")
            m.wait_for_timeout(350)
            xy = J(f"() => {{ const e = ({js_find})(); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }}")
            if xy:
                m.touchscreen.tap(xy[0], xy[1])
            return xy
        try:
            m.goto(base + "#industry/semiconductor", wait_until="domcontentloaded"); m.wait_for_timeout(5000)
            ok(f"【{T}】{vw}：html.m4 掛上", J("() => document.documentElement.classList.contains('m4')"))
            chains = ["semiconductor"]
            if vw == 390:
                chains = J("""() => [...new Set([...document.querySelectorAll('a[href^="#industry/"]')].map(a => a.getAttribute('href').slice(10))
                    .filter(h => h && !h.includes('/') && h !== 'industry'))]""")
                chains = list(dict.fromkeys(["semiconductor"] + chains))
            seen_any = 0
            for cid in chains:
                m.goto(base + "#industry/" + cid, wait_until="domcontentloaded"); m.wait_for_timeout(3500)
                segs = J("() => [...document.querySelectorAll('.view.on #segChips .segchip')].map(e => e.dataset.seg)")
                bad = []
                for sg in segs:
                    J("() => { const s = document.getElementById('mSheetBack'); if (s && !s.hidden) s.click(); }")
                    if not J("() => { const d = document.querySelector('.view.on #segDD'); return !!(d && d.classList.contains('open')); }"):
                        tap("() => document.querySelector('.view.on #segDDBtn')")
                        m.wait_for_timeout(300)
                    xy = tap(f"() => document.querySelector('.view.on #segChips .segchip[data-seg=\"{sg}\"]')")
                    if not xy:
                        continue
                    m.wait_for_timeout(500)
                    seen_any += 1
                    r = J("""() => { const v = x => !!(x && x.getClientRects().length && x.getBoundingClientRect().height > 1);
                        return { dd: (document.querySelector('#segDDBtn b') || {}).textContent || '',
                                 sb: v(document.getElementById('segBox')), x: [...document.querySelectorAll('.xchain, .xgo, #cgXChains')].filter(v).length,
                                 oth: [...document.querySelectorAll('.view.on .linkrow.chainothers')].filter(v).length,
                                 go: [...document.querySelectorAll('.view.on button, .view.on a')].filter(e => v(e) && /切到這條鏈看/.test(e.textContent)).length }; }""")
                    if r["sb"] or r["x"] or r["oth"] or r["go"]:
                        bad.append({"seg": sg, **r})
                ok(f"【{T}】{vw}：{cid} 用手指從「篩選 環節」點了 {len(segs)} 格，沒有一格長出環節詳情／跨鏈比較卡／「切到這條鏈看」／其他產業鏈列（壞 {len(bad)}）",
                   not bad, bad[:3])
            ok(f"【{T}】{vw}：真的點到了環節（{seen_any} 格；0 ＝ 下拉沒點開，這段等於沒驗）", seen_any > 0)
            # 下拉真的生效：最後點的那一格名字出現在下拉鈕上（畫面真的因此改變了）
            ok(f"【{T}】{vw}：下拉鈕顯示已選的環節（不是「全部」）", J("() => ((document.querySelector('#segDDBtn b') || {}).textContent || '全部').trim() !== '全部'"))

            # ---- 2. 公司說明卡：光洋科 1785 ----
            m.goto(base + "#industry", wait_until="domcontentloaded"); m.wait_for_timeout(1500)
            m.goto(base + "#industry/semiconductor", wait_until="domcontentloaded"); m.wait_for_timeout(4500)
            for _ in range(30):
                if J("() => !!document.querySelector('.view.on #chainMap .co[data-code=\"1785\"]')"):
                    break
                idx = J("""() => { const ts = [...document.querySelectorAll('.view.on #chainMap .segtitle')]; const i = (window.__ch16 = (window.__ch16 || 0) + 1) - 1; return i < ts.length ? i : -1; }""")
                if idx < 0:
                    break
                tap(f"() => document.querySelectorAll('.view.on #chainMap .segtitle')[{idx}]"); m.wait_for_timeout(450)
            xy = tap("() => document.querySelector('.view.on #chainMap .co[data-code=\"1785\"]')")
            ok(f"【{T}】{vw}：關聯圖上找得到光洋科 1785 節點", bool(xy))
            m.wait_for_timeout(1200)
            a = J(f"({AUD})('#coBox')")
            if not ok(f"【{T}】{vw}：點光洋科之後公司說明卡打開", bool(a) and "光洋科" in (a or {}).get("text", ""), (a or {}).get("text", "")[:60]):
                continue
            ok(f"【{T}】{vw}：說明卡裡沒有空框、沒有字跟底同色的按鈕（{len(a['bad'])}）", not a["bad"], a["bad"][:4])
            ok(f"【{T}】{vw}：說明卡沒有「看個股頁 →」那顆（改前是空框）", "看個股頁" not in a["text"])
            ok(f"【{T}】{vw}：說明卡的「在圖上…」鈕是繁中、沒有 highlight（{a['hi']}）", a["hi"].strip() == "在圖上標示" and "highlight" not in a["text"].lower())
            ok(f"【{T}】{vw}：名字本身是個股頁連結（{a['title']}）", a["title"] == "#stock/1785")
            # 「在圖上標示」真的按：按了變「取消標示」、關聯圖上別家被壓暗；再按一次還原
            tap("() => document.querySelector('#coBox #relHi')"); m.wait_for_timeout(500)
            # 手機的關聯圖其他環節預設收著（只剩膠囊），所以量「圖上有東西被壓暗或亮起來」（線 .edge.hi／.dim、公司 .co.dim）
            h1 = J("() => ({ t: document.querySelector('#coBox #relHi').textContent, dim: document.querySelectorAll('#chainMap .dim, #chainMap .hi').length })")
            ok(f"【{T}】{vw}：按「在圖上標示」→ 變「取消標示」、圖上的線／公司真的亮暗改變（{h1}）", h1["t"] == "取消標示" and h1["dim"] > 0, h1)
            tap("() => document.querySelector('#coBox #relHi')"); m.wait_for_timeout(500)
            ok(f"【{T}】{vw}：再按一次還原成「在圖上標示」", J("() => document.querySelector('#coBox #relHi').textContent") == "在圖上標示")
            tap("() => document.querySelector('#coBox h3 a')"); m.wait_for_timeout(2500)
            ok(f"【{T}】{vw}：點名字真的換到個股頁（{J('() => location.hash')}）", J("() => location.hash").startswith("#stock/1785"))
        finally:
            ctx.close()
    # 1440 桌機：環節面板照舊不畫；說明卡那顆「看個股頁 →」留著，但字要看得到（theme4 補 .btn.primary）
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try{ localStorage.setItem('tw.live.on','0'); localStorage.setItem('tw.tourDone','1'); }catch(e){}")
    d = ctx.new_page(); d.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    try:
        d.goto(base + "#industry/semiconductor", wait_until="domcontentloaded"); d.wait_for_timeout(5000)
        ok(f"【{T}】1440：沒有 html.m4", not d.evaluate("() => document.documentElement.classList.contains('m4')"))
        found = d.evaluate("() => { const e = document.querySelector('.view.on #chainMap .co[data-code]'); if (!e) return null; e.scrollIntoView({ block: 'center' }); e.dispatchEvent(new MouseEvent('click', { bubbles: true })); return e.dataset.code; }")
        d.wait_for_timeout(1200)
        if ok(f"【{T}】1440：點一家公司打開說明卡（{found}）", bool(found) and d.evaluate("() => !!document.getElementById('coBox')")):
            a = d.evaluate(f"({AUD})('#coBox')")
            ok(f"【{T}】1440：說明卡裡沒有空框、沒有字跟底同色的按鈕（{len(a['bad'])}）", not a["bad"], a["bad"][:4])
            ok(f"【{T}】1440：「看個股頁 →」桌機照舊在", "看個股頁" in a["text"])
    finally:
        ctx.close()


# ★ 2026-10-16 Andy iPhone：產業鏈頁只留剖析圖／關聯圖／公司說明卡、說明卡最下面的空白方框拿掉（360／390／430 觸控＋1440 守桌機；⚠ --workers 1）
register("手機產業鏈1016", lambda pg, b, base, code: t_m4_chain1016(b, base), after="手機產業地圖回應1009")
