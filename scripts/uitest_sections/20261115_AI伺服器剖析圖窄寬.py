# 驗收段落「AI伺服器2D窄寬1115」（site/diagrams.js .dgaisv／site/industry.js fitCanvas 的 .dgsq）
# 這支由 _uitest.py 用 exec 載入：ok() 直接可用，不要 import _uitest。不要在這裡寫三引號模組說明。
# flake8: noqa
# 頻道④回報：#industry/ai_server 在 2D 模式、容器 410～659 被縮時字級反向放大，標題／說明／流程格交疊。
# 以前的 _preview 預設走 3D（沒有存 tw.dg3d），所以沒抓到；這裡明確設成 2D 後在 700／800／900／1000 都量。


def t_aiserver_2d_narrow_1115(b, base, code):
    import _preview as _P
    for w in (700, 800, 900, 1000):
        pg = b.new_page(viewport={"width": w, "height": 1000})
        pg.add_init_script("try{localStorage.setItem('tw.dg3d','0')}catch(e){}")
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.goto(f"{base}?svg=1#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(2200)
        n = pg.evaluate("() => document.querySelectorAll('svg.dgaisv text').length")
        ov = [o for o in pg.evaluate(_P.TEXT_OVERLAP_ALL_JS, 2) if o[0].startswith("AI 伺服器")]
        ok(f"[AI伺服器2D] @{w} 剖析圖 2D 文字零交疊（量到 {n} 個圖內字）", n > 20 and not ov, ov[:4])
        pg.close()


register("AI伺服器2D窄寬1115", lambda pg, b, base, code: t_aiserver_2d_narrow_1115(b, base, code))
