# 驗收段落「深層連結導覽1102」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_sub_ctx()、_gp_presets()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 深層連結導覽1102
# 社群貼文導流進站（docs/marketing/diagnosis_1102/landing_conversion_review.md）：
#   ① 從 #market/inst?u=… 這種深層連結＋來源參數進站、同意條款後 —— 不自動跑全站導覽、網址不改（貼文連的那頁不被換掉）；
#      之後訪客自己第一次走到首頁（#overview）才補跑一次導覽（tw.tour 才寫入）。
#   ② 從 #overview／沒有 hash 進站：行為照舊（同意後自動跑全站導覽 1/N）。桌機也一樣：深層連結不被劫持。
#   ③ 手機（≤640）同意橫幅是底部細條：不蓋首屏主內容（高度 ≤ 120px），「同意」鈕仍在畫面內、點得到。
#   ④ 手機頂欄（flow／market／earnings，額度計數＋圓環都在）登入圖示整顆在可視範圍內、整頁不橫捲。


def t_deeplink_tour_1102(b, base):
    T = "深層連結導覽1102"
    ctxs = []
    raw = getattr(type(b), "_tw_raw_new_context", None)
    # _sub_ctx 內部呼叫 b.new_context —— 換成沒有預寫 tw.consent 的原版，才看得到橫幅
    class _RawB:
        def new_context(self, **k):
            return raw(b, **k) if raw else b.new_context(**k)
    PR = _gp_presets()

    def mk(w, h=844, touch=True):
        c, _sent, _st = _sub_ctx(_RawB(), None, width=w, feats=dict(PR["guest"]["feats"]), lims=dict(PR["guest"]["lims"]), dq=14, touch=touch)
        c.add_init_script("window.TW_LEGAL_OVERRIDE={operator:'驗收用營業人',email:'uitest@example.com',effective_date:'2026-10-01',tax_id:'尚未辦理',court:'臺灣臺北地方法院',enabled:true};"
                          "try{localStorage.setItem('tw.live.on','0')}catch(e){}")
        pg = c.new_page(); pg.set_viewport_size({"width": w, "height": h})
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {e}"))
        ctxs.append(c)
        return pg

    LS = "(k) => { try { return localStorage.getItem(k); } catch (e) { return 'ERR'; } }"
    TOUR = "() => !!(window.TwTour && TwTour.state().active)"
    try:
        # ---------- ① 手機從社群貼文連結（深層路由＋?u=）進站
        for label, url in (("?u=在網址列", "?u=th-id-20261102#market/inst"), ("?u=在 hash 裡", "#market/inst?u=threads")):
            pg = mk(390)
            pg.goto(base + url, wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.getElementById('lgAccept')", 12000)
            pg.wait_for_timeout(600)
            bn = pg.evaluate("""() => { const r = document.getElementById('lgBanner').getBoundingClientRect(), a = document.getElementById('lgAccept').getBoundingClientRect();
                return { h: Math.round(r.height), top: Math.round(r.top), bottom: Math.round(r.bottom), vh: innerHeight, ah: Math.round(a.height), atop: Math.round(a.top), abot: Math.round(a.bottom) }; }""")
            ok(f"{T}【手機 {label}】同意橫幅是底部細條：高度 ≤ 120px（不蓋首屏主內容）", bn["h"] <= 120 and bn["bottom"] <= bn["vh"], bn)
            ok(f"{T}【手機 {label}】「同意並繼續」仍在畫面內、可點高度 ≥ 36px", 0 <= bn["atop"] and bn["abot"] <= bn["vh"] and bn["ah"] >= 36, bn)
            pg.tap("#lgAccept"); pg.wait_for_timeout(2500)
            st = pg.evaluate("() => ({ h: location.hash, tour: !!(window.TwTour && TwTour.state().active), ov: !!document.querySelector('#twTour:not([hidden])'), banner: !!document.getElementById('lgBanner'), view: (document.querySelector('.view.on') || {}).id || '' })")
            ok(f"{T}【手機 {label}】同意後網址仍是 #market/inst（沒被改成 #overview）", st["h"].startswith("#market/inst"), st)
            ok(f"{T}【手機 {label}】同意後沒有導覽浮層、導覽沒在跑", not st["tour"] and not st["ov"], st)
            ok(f"{T}【手機 {label}】同意條款這個動作本身有生效：橫幅消失、tw.consent 寫進去", not st["banner"] and pg.evaluate(LS, "tw.consent") not in (None, "ERR"), st)
            ok(f"{T}【手機 {label}】tw.tour 沒被記成「看過」（導覽留給之後從首頁進來）", pg.evaluate(LS, "tw.tour") is None, pg.evaluate(LS, "tw.tour"))
            # 之後這位訪客自己走到首頁：才補跑一次導覽
            pg.evaluate("() => { location.hash = '#overview'; }")
            okt = wait_until(pg, "() => !!(window.TwTour && TwTour.state().active && TwTour.state().i >= 0)", 10000)
            ok(f"{T}【手機 {label}】之後自己走到首頁（#overview）→ 補跑全站導覽、第 1 步", okt and pg.evaluate("() => TwTour.state().i") == 0, pg.evaluate("() => window.TwTour && TwTour.state()"))
            ok(f"{T}【手機 {label}】導覽開跑後才寫進 tw.tour（之後不會再自動跑）", pg.evaluate(LS, "tw.tour") not in (None, "ERR"), pg.evaluate(LS, "tw.tour"))
            pg.evaluate("() => TwTour.stop()"); pg.wait_for_timeout(400)
            pg.evaluate("() => { location.hash = '#market/inst'; }"); pg.wait_for_timeout(300)
            pg.evaluate("() => { location.hash = '#overview'; }"); pg.wait_for_timeout(1800)
            ok(f"{T}【手機 {label}】看過之後再回首頁不會再自動跑", not pg.evaluate(TOUR))
            pg.context.close()

        # ---------- ① 之三：下次這位訪客「自己」直接開首頁（整頁重新載入、沒有來源參數）→ 補跑一次導覽（tw.tour.defer 跨載入還在）
        pg = mk(390)
        pg.goto(base + "?u=th-id-20261102#market/inst", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('lgAccept')", 12000)
        pg.tap("#lgAccept"); pg.wait_for_timeout(1500)
        ok(f"{T}【下次來】延後旗標 tw.tour.defer 真的寫進去", pg.evaluate(LS, "tw.tour.defer") == "1", pg.evaluate(LS, "tw.tour.defer"))
        pg.goto(base + "#overview", wait_until="domcontentloaded")
        okt = wait_until(pg, "() => !!(window.TwTour && TwTour.state().active && TwTour.state().i >= 0)", 12000)
        ok(f"{T}【下次來】直接開首頁（整頁重新載入）→ 補跑全站導覽、第 1 步", okt, pg.evaluate("() => window.TwTour && TwTour.state()"))
        ok(f"{T}【下次來】導覽開跑後 tw.tour 寫進去、tw.tour.defer 清掉", pg.evaluate(LS, "tw.tour") not in (None, "ERR") and pg.evaluate(LS, "tw.tour.defer") is None)
        pg.context.close()

        # ---------- ① 之二：桌機的深層連結也不被劫持（版面不動，只驗導覽）
        pg = mk(1440, 900, touch=False)
        pg.goto(base + "?u=th-id-20261102#market/inst", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.getElementById('lgAccept')", 12000)
        pg.click("#lgAccept"); pg.wait_for_timeout(2500)
        st = pg.evaluate("() => ({ h: location.hash, tour: !!(window.TwTour && TwTour.state().active) })")
        ok(f"{T}【桌機 1440】深層連結同意後網址仍是 #market/inst、導覽沒在跑", st["h"].startswith("#market/inst") and not st["tour"], st)
        pg.context.close()

        # ---------- ② 從 #overview／沒有 hash 進站：行為照舊
        for label, url in (("#overview", "#overview"), ("沒有 hash", ""), ("#overview?tour 無關的非來源參數", "?x=1#overview")):
            for w, touch in ((390, True), (1440, False)):
                pg = mk(w, 844 if touch else 900, touch)
                pg.goto(base + url, wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.getElementById('lgAccept')", 12000)
                pg.wait_for_timeout(500)
                (pg.tap if touch else pg.click)("#lgAccept")
                okt = wait_until(pg, "() => !!(window.TwTour && TwTour.state().active && TwTour.state().i >= 0)", 10000)
                s = pg.evaluate("() => window.TwTour && TwTour.state()") or {}
                ok(f"{T}【{w} 寬，{label}進站】同意後自動跑全站導覽（第 1 步、共 N 步），網址是首頁", okt and s.get("tour") == "site" and s.get("i") == 0 and (s.get("hash") or "") in ("", "#overview"), s)
                ok(f"{T}【{w} 寬，{label}進站】tw.tour 真的寫進去（只自動跑一次）", pg.evaluate(LS, "tw.tour") not in (None, "ERR"))
                pg.context.close()

        # ---------- ④ 手機頂欄：額度計數＋圓環都在時，登入圖示整顆在可視範圍內
        for w in (390, 360):
            for h in ("#flow", "#market/inst", "#earnings"):
                pg = mk(w)
                pg.add_init_script(CONSENT_ONLY)       # 這段驗頂欄，不要橫幅干擾
                pg.goto(base + h, wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.getElementById('acctBtn') && !!document.querySelector('.m4tools')", 12000)
                pg.wait_for_timeout(2500)
                m = pg.evaluate("""() => { const q = (s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null; const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right), Math.round(r.top), Math.round(r.bottom)]; };
                    const tools = [...document.querySelectorAll('.m4tools > *')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return [e.id || e.className, Math.round(r.left), Math.round(r.right)]; });
                    return { acct: q('#acctBtn'), ring: q('#twQRing'), qp: q('#twQPage'), vw: innerWidth, sw: document.documentElement.scrollWidth, tools }; }""")
                a = m["acct"]
                ok(f"{T}【手機 {w} {h}】登入圖示整顆在可視範圍內（左 ≥ 0、右 ≤ 視窗寬）", bool(a) and a[0] >= 0 and a[1] <= m["vw"], m)
                ok(f"{T}【手機 {w} {h}】頂欄右側每一顆都沒出框、整頁不橫向捲動", all(t[2] <= m["vw"] and t[1] >= 0 for t in m["tools"]) and m["sw"] <= m["vw"], m)
                if h in ("#flow", "#market/inst") and w == 390:
                    ok(f"{T}【手機 {w} {h}】（前提）這一頁頂欄真的有額度圓環或計數，否則上面兩項沒驗到東西", bool(m["ring"] or m["qp"]), m)
                pg.context.close()
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass


register("深層連結導覽1102", lambda pg, b, base, code: t_deeplink_tour_1102(b, base))
