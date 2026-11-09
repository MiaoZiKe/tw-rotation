# 驗收段落「大小戶無404」：進個股頁（一般訪客）不得出現任何 data/bigsmall/*.json 的 404；一般訪客（功能鍵關）更不該發任何 bigsmall 請求
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def t_bigsmall_no404(b, base, code):
    T = "大小戶無404"
    for owner in (False,):
        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page()
        bad, reqs = [], []
        pg.on("response", lambda r: ("data/bigsmall/" in r.url and r.status >= 400) and bad.append(f"{r.status} {r.url}"))
        pg.on("request", lambda r: ("data/bigsmall/" in r.url) and reqs.append(r.url))
        try:
            pg.goto(base + "#stock/2330", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelector('#v-stock') && document.querySelector('#v-stock').textContent.length > 200", 20000)
            pg.wait_for_timeout(2500)
            ok(f"【{T}】{'站主' if owner else '一般訪客'}進個股頁沒有 bigsmall 404", not bad, str(bad[:3]))
            if not owner:
                ok(f"【{T}】一般訪客（功能鍵關）完全不發 bigsmall 請求", not reqs, str(reqs[:3]))
        finally:
            c.close()

register("大小戶無404", lambda pg, b, base, code: t_bigsmall_no404(b, base, code))
