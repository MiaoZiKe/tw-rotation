# 驗收段落「手機導流1110」—— 2026-11-10 Andy「全部 O」：手機四項修正（同意細條、頂欄站名、總覽一句話、訪客鈴鐺無數字）＋LOGO 換 ⑤C 的淺深主題。
# 這支由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。用 Browser 原版 new_context（訪客視角：沒有預先寫同意）。
# flake8: noqa

def t_mobile_restart_1110(b, base):
    T = "手機導流1110"
    raw = getattr(type(b), "_tw_raw_new_context", None)
    if not ok(f"【{T}】拿得到 Browser 原版 new_context（要看沒有同意紀錄的訪客畫面）", raw is not None):
        return
    HEAD = """() => { const r = s => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null; const x = e.getBoundingClientRect(); return { l: Math.round(x.left), r: Math.round(x.right), t: Math.round(x.top), b: Math.round(x.bottom) }; };
      return { txt: r('.topbar .brand b.brandtxt'), tools: r('#m4Tools'), login: r('.m4login') || r('#acctBtn'), sw: document.documentElement.scrollWidth,
        ban: r('#lgBanner'), lead: (document.querySelector('.m4lead') || {}).textContent || '', sub: (document.querySelector('.m4tagline') || {}).textContent || '' }; }"""
    for w in (375, 390):
        c = raw(b, viewport={"width": w, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page()
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pg, "() => document.documentElement.classList.contains('m4') && !!document.getElementById('lgBanner')", 25000)
        pg.wait_for_timeout(3000)
        h = pg.evaluate(HEAD)
        # ① 同意細條
        ban = h["ban"]
        ok(f"【{T}】{w}：同意橫幅高度 ≤ 50（細條，改前 109）", bool(ban) and ban["b"] - ban["t"] <= 50, ban)
        bi = pg.evaluate("""() => { const q = s => document.querySelector(s); const cs = e => getComputedStyle(e);
          return { links: [...document.querySelectorAll('#lgBanner p a')].map(a => a.getAttribute('href')),
            declBg: cs(q('#lgDecline')).backgroundColor, declUl: cs(q('#lgDecline')).textDecorationLine, declH: Math.round(q('#lgDecline').getBoundingClientRect().height),
            accW: Math.round(q('#lgAccept').getBoundingClientRect().width), accAfter: getComputedStyle(q('#lgAccept'), '::after').content, bannerBottom: Math.round(q('#lgBanner').getBoundingClientRect().bottom) }; }""")
        ok(f"【{T}】{w}：三個條款連結都還在（使用條款／隱私權／免責）", bi["links"] == ["#terms", "#privacy", "#disclaimer"], bi)
        ok(f"【{T}】{w}：不同意＝無底色的底線文字連結（次要）、同意＝主鈕且帶「同意」字、不同意點擊高度 ≥ 40",
           bi["declBg"] in ("rgba(0, 0, 0, 0)", "transparent") and "underline" in bi["declUl"] and bi["declH"] >= 40 and bi["accW"] >= 60 and "同意" in bi["accAfter"], bi)
        # ② 頂欄站名：放得進去、不把右邊的登入鈕擠出畫面
        if w >= 370:
            ok(f"【{T}】{w}：頂欄有站名「哩股哩股」、在工具列左邊不重疊、登入鈕在畫面內、整頁不橫捲",
               bool(h["txt"]) and h["txt"]["r"] <= h["tools"]["l"] and h["login"]["r"] <= w and h["sw"] <= w, h)
        # ③ 總覽一句話＋副標
        bad = [x for x in ("進場", "時機", "明牌") if x in h["lead"] or x in h["sub"]]
        ok(f"【{T}】{w}：總覽頁首有副標「台股資金流向」與一句白話說明，且沒有進場／時機／明牌字眼", h["sub"] == "台股資金流向" and "三分鐘" in h["lead"] and not bad, h)
        g = pg.evaluate("""() => { const e = document.querySelector('#v-overview canvas, #v-overview svg.chart, #v-overview .echarts'); const cv = [...document.querySelectorAll('#v-overview canvas')].filter(x => x.getBoundingClientRect().height > 150)[0];
          const x = cv ? cv.getBoundingClientRect() : null; return x ? { top: Math.round(x.top), bottom: Math.round(x.bottom) } : null; }""")
        ok(f"【{T}】{w}：總覽主圖底緣在第一屏（≤ 視窗高 844）— 圖與數字同一屏", bool(g) and g["bottom"] <= 844, g)
        # ④ 訪客鈴鐺不顯示紅色數字
        bell = pg.evaluate("""() => { const b = document.getElementById('ntBell'); if (!b) return null; const d = b.querySelector('.dot');
          return { guest: b.classList.contains('guest'), dotHidden: d.hidden, disp: getComputedStyle(d).display, n: d.textContent }; }""")
        ok(f"【{T}】{w}：未登入 → 鈴鐺標 guest、紅色數字不顯示（display:none）", bool(bell) and bell["guest"] and bell["disp"] == "none", bell)
        # 按「同意」→ 紀錄真的寫進 localStorage、橫幅消失
        pg.click("#lgAccept"); pg.wait_for_timeout(600)
        cs = pg.evaluate("() => ({ v: localStorage.getItem('tw.consent'), has: !!document.getElementById('lgBanner') })")
        ok(f"【{T}】{w}：按「同意」→ tw.consent 真的寫入、橫幅移除", bool(cs["v"]) and not cs["has"], cs)
        # 淺／深主題的 LOGO 擇一顯示
        for th in ("light", "dark"):
            pg.evaluate(f"() => document.documentElement.setAttribute('data-theme', '{th}')"); pg.wait_for_timeout(200)
            lg = pg.evaluate("""() => { const v = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; }; return { l: v('.topbar .brand picture.mkl'), d: v('.topbar .brand picture.mkd') }; }""")
            ok(f"【{T}】{w}：{th} 主題只顯示對應的 LOGO（淺底版／深底版）", lg["l"] == (th == "light") and lg["d"] == (th == "dark"), lg)
        c.close()
    # 「不同意」行為不變：還是回 #leave
    c = raw(b, viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = c.new_page(); pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('lgBanner')", 25000); pg.wait_for_timeout(1500)
    pg.click("#lgDecline"); pg.wait_for_timeout(800)
    ok(f"【{T}】按「不同意」→ 仍然跳到 #leave、不寫同意紀錄", pg.evaluate("() => location.hash") == "#leave" and not pg.evaluate("() => localStorage.getItem('tw.consent')"))
    c.close()
    # 桌機：沒有手機專屬的東西冒出來
    c = raw(b, viewport={"width": 1440, "height": 900})
    pg = c.new_page(); pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
    d = pg.evaluate("""() => ({ lead: !!document.querySelector('.m4lead'), m4: document.documentElement.classList.contains('m4'),
      txtStroke: (() => { const e = document.querySelector('.topbar .brand b.brandtxt, .brand b.brandtxt'); return e ? getComputedStyle(e).webkitTextStrokeWidth : null; })(),
      logoVis: (() => { const v = s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none'; }; return [v('.brand picture.mkl'), v('.brand picture.mkd')]; })() })""")
    ok(f"【{T}】桌機 1440：沒有 .m4lead、不是 m4、站名無描邊（11-10 改 LIGULIGU 墨色）、淺深其中一張 LOGO 顯示", (not d["lead"]) and (not d["m4"]) and d["txtStroke"] == "0px" and sum(d["logoVis"]) == 1, d)
    c.close()

register("手機導流1110", lambda pg, b, base, code: t_mobile_restart_1110(b, base), after="桌機守門1008")
