# 驗收段落「精選文章收合1016」—— 2026-10-16
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用。不要寫三引號模組說明。
# flake8: noqa

# Andy 10-16：「不必要資訊改成收合，像是相關連結」→ 單篇文末「站內相關頁面／資料來源／同類別其他文章」預設收起，
# 點標題展開、再點收起；展開過的重新整理後記得（手機準則 5）。電腦 1440、手機 390 各走一次。
def t_art_fold_1016(b, base):
    T = "精選文章收合1016"
    art = "2026-10-14-know-cowos"
    for w, h, mob in ((1440, 900, False), (390, 844, True)):
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob)
        ctx.add_init_script("try{localStorage.setItem('tw.live.on','0');if(!sessionStorage.getItem('zzFold')){localStorage.removeItem('tw.art.fold');sessionStorage.setItem('zzFold','1')}}catch(e){}")   # 只在第一次載入清（重新整理要留著驗「記得」）
        pg = ctx.new_page()
        pg.goto(base + "#article/" + art, wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.querySelector('#artPost #artBody')", 12000); pg.wait_for_timeout(400)
        st = pg.evaluate("""() => [...document.querySelectorAll('#artPost details.artfold')].map(d => ({ id: d.id, open: d.open,
            h: Math.round(d.getBoundingClientRect().height), sum: d.querySelector('summary').innerText }))""")
        ok(f"{T}：{w} 文末三塊（站內相關頁面／資料來源／同類別其他文章）預設收起、只剩一行標題＋數量",
           {x["id"] for x in st} >= {"artLinks", "artSrc"} and all(not x["open"] and x["h"] <= 60 for x in st) and all("展開" not in x["sum"] for x in st), st)
        pg.locator("#artSrc > summary").scroll_into_view_if_needed()
        pg.click("#artSrc > summary"); pg.wait_for_timeout(200)
        op = pg.evaluate("() => ({ open: document.getElementById('artSrc').open, n: document.querySelectorAll('#artSrc li').length, vis: document.querySelector('#artSrc li').getBoundingClientRect().height > 0 })")
        ok(f"{T}：{w} 點「資料來源」→ 展開、看得到來源清單", op["open"] and op["n"] > 0 and op["vis"], op)
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('#artSrc')", 12000); pg.wait_for_timeout(300)
        rm = pg.evaluate("() => [document.getElementById('artSrc').open, document.getElementById('artLinks') ? document.getElementById('artLinks').open : false]")
        ok(f"{T}：{w} 重新整理 → 展開過的「資料來源」記得是開的、沒展開過的仍收起", rm == [True, False], rm)
        pg.click("#artSrc > summary"); pg.wait_for_timeout(200)
        ok(f"{T}：{w} 再點一次 → 收起", not pg.evaluate("() => document.getElementById('artSrc').open"), None)
        ctx.close()


register("精選文章收合1016", lambda pg, b, base, code: t_art_fold_1016(b, base), after="精選文章1014")
