# 驗收段落「文章分類分段1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 文章分類分段1017（Andy 10-17：「這邊不同類型需要線條隔開」）
# 精選文章列表（#articles），1440 與 390：
#   ① 「全部文章」→ 依類型分段（比比快訊 → 比比產業鏈 → 比比知識，只列有文章的），每段標題寫類型與篇數、篇數＝該段卡片數
#   ② 第二段起上方有分隔線（border-top ≥ 1px），每段卡片的類型都跟段落一致，卡片總數＝「共 N 篇」
#   ③ 切到單一類型分頁 → 不分段（沒有 .artsec）
#   ④ 沒有橫向捲軸、段落標題不壓到卡片


def t_article_groups_1017(b, base, code):
    T = "文章分類分段1017"
    errs: list[str] = []
    for w in (1440, 390):
        c = b.new_context(viewport={"width": w, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#articles", wait_until="domcontentloaded")
        if not ok(f"{T}（{w}）：列表載入", bool(wait_until(pg, "() => document.querySelectorAll('#artList .artc').length ? 1 : 0", 15000))):
            c.close(); continue
        pg.evaluate("() => { const b = document.querySelector('#artCats>button[data-cat=all]'); if (b) b.click(); const c = document.querySelector('[data-wide]'); if (c) c.click(); }")
        pg.wait_for_timeout(500)
        st = pg.evaluate("""() => { const secs = [...document.querySelectorAll('#artList .artsec')], ORDER = ['news', 'intro', 'know'];
            const n = +((document.getElementById('artCount') || {}).dataset || {}).n || 0;
            return { n, total: document.querySelectorAll('#artList .artc').length, cats: secs.map(s => s.dataset.cat),
              ordered: secs.map(s => ORDER.indexOf(s.dataset.cat)).every((v, i, a) => i === 0 || a[i - 1] < v),
              eachOk: secs.every(s => { const cs = [...s.querySelectorAll('.artc')]; const em = s.querySelector('.artsech em').textContent; return cs.length && cs.every(c => c.dataset.cat === s.dataset.cat) && em.startsWith(String(cs.length)); }),
              lines: secs.slice(1).map(s => parseFloat(getComputedStyle(s).borderTopWidth)),
              noOverlap: secs.every(s => { const h = s.querySelector('.artsech').getBoundingClientRect(), f = s.querySelector('.artc').getBoundingClientRect(); return h.bottom <= f.top + 1; }),
              sw: document.documentElement.scrollWidth - innerWidth }; }""")
        kinds = len(set(st["cats"]))
        ok(f"{T}（{w}）：全部文章依類型分段（快訊→產業鏈→知識）、每段篇數對、卡片類型一致、總數＝共 N 篇",
           kinds >= 2 and st["ordered"] and st["eachOk"] and st["total"] == st["n"], st)
        ok(f"{T}（{w}）：第二段起有分隔線、標題不壓卡片、沒有橫向捲軸", all(x >= 1 for x in st["lines"]) and st["noOverlap"] and st["sw"] <= 1, st)
        shot = os.environ.get("TW_GRP_SHOT")
        if shot:
            pg.screenshot(path=shot.replace(".png", f"_{w}.png"), full_page=True)
        cat = st["cats"][0] if st["cats"] else "news"
        pg.click(f"#artCats>button[data-cat='{cat}']"); pg.wait_for_timeout(400)
        n2 = pg.evaluate("() => document.querySelectorAll('#artList .artsec').length")
        ok(f"{T}（{w}）：單一類型分頁不分段", n2 == 0, n2)
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("文章分類分段1017", lambda pg, b, base, code: t_article_groups_1017(b, base, code))
