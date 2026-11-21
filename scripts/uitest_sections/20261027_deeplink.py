# 驗收段落「深層連結1027」（docs/marketing/feature_funnel_1027.md 第四節 A＋B＋C）
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。不要寫三引號模組說明。
# flake8: noqa
#   ① 站內 TwSrc.parse 讀得懂新功能碼：th-f3d → threads／diagram3d_日期，舊全名 threads-f3d 歸併一樣，evfomc → ev_fomc，igs → instagram_story
#   ② 貼文白名單路由逐條真的打開：?u=… 在 # 前、頁面進得去、網址沒被導掉、沒有頁面錯誤、主內容有字
DL_ROUTES = ["flow/rotation", "market/inst", "market/credit", "earnings", "etf/cal", "etf/list", "etf/inc", "heatmap/industry",
             "industry/semiconductor", "industry/ai_server", "industry/electronics"]


def t_deeplink_1027(b, base, code):
    T = "深層連結1027"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    try:
        root = base.split("?")[0].split("#")[0]
        pg = c.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
        want = {"th-f3d-20261028": ("threads", "diagram3d_20261028"), "threads-f3d-20261028": ("threads", "diagram3d_20261028"),
                "th-evfomc-20261029": ("threads", "ev_fomc_20261029"), "igs-etfd-20261030": ("instagram_story", "etf_div_20261030"),
                "th-earn-20261027": ("threads", "earnings_20261027"), "th-id-20261027": ("threads", "intraday_20261027")}
        for u, (s, cc) in want.items():
            pg.goto(f"{root}?u={u}#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwSrc", 6000)
            got = pg.evaluate("() => { const o = window.TwSrc.parse(); return o ? [o.s, o.c] : null }")
            ok(f"{T}：①?u={u} 解析成 {s}／{cc}", got == [s, cc], got)
        for r in DL_ROUTES:
            pg.goto(f"{root}?u=th-f3d-20261028#{r}", wait_until="domcontentloaded")
            pg.wait_for_timeout(1500)
            h = pg.evaluate("() => location.hash")
            n = pg.evaluate("() => (document.querySelector('main, #app, body').innerText || '').length")
            ok(f"{T}：②#{r} 進得去（網址沒被導掉、有內容）", h.startswith("#" + r.split("/")[0]) and n > 200, [h, n])
    finally:
        c.close()
    ok(f"{T}：整段沒有頁面錯誤", not errs, errs[:3])


register("深層連結1027", lambda pg, b, base, code: t_deeplink_1027(b, base, code))
