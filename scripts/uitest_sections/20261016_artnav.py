# 驗收段落「精選文章分頁1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章分頁1016
# Andy 10-16：「精選文章已經裡面有分頁，側邊子分頁就拿掉，並且手機版的分頁需要適當調整寬度」
#   ① 電腦側欄、手機抽屜都只剩一格「精選文章」（沒有比比快訊／比比產業鏈／比比知識子項）
#   ② 四格分頁每一格完整看得到（不被外框裁、字不被切、不換行），手機五格等寬、短名（全部／快訊／產業鏈／知識）
#   ③ 真的點每一格 → 篇數與卡片跟著變；④ #articles/<類別> 深連結選對分頁
def t_artnav_1016(b, base):
    import datetime as _dt
    T = "精選文章分頁1016"
    today = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).date().isoformat()
    # 每類各塞幾篇今天的假文章（真文章日期會漸漸掉出「近一個月」預設區間，篇數不能靠它）：快訊 2、產業鏈 1、知識 3 → 四格篇數兩兩不同
    fake = [{"id": f"uitest-nav-{c}-{i}", "cat": c, "title": f"驗收用{c}{i}", "subtitle": "", "date": today, "tags": [], "summary": "", "reading_min": 1, "groups": []}
            for c, k in (("news", 2), ("intro", 1), ("know", 3)) for i in range(k)]

    def idx_route(r):
        try:
            j = r.fetch().json()
        except Exception:  # noqa: BLE001
            j = {"updated": today, "articles": []}
        j["articles"] = list(j.get("articles", [])) + fake
        r.fulfill(status=200, content_type="application/json", body=json.dumps(j, ensure_ascii=False))
    SUBT = ("比比快訊", "比比產業鏈", "比比知識")
    TABST = """() => { const C = document.getElementById('artCats'); if (!C) return null; const cr = C.getBoundingClientRect();
        return { cats: [cr.left, cr.right], vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, ov: C.scrollWidth - C.clientWidth,
          tabs: [...C.children].map(b => { const r = b.getBoundingClientRect(), sp = b.querySelector('span'), cs = getComputedStyle(b), lh = parseFloat(cs.fontSize) * 1.8;
            const spOn = sp && getComputedStyle(sp).display !== 'none';
            const lbl = spOn ? sp.textContent.trim() : getComputedStyle(b, '::after').content.replace(/^"|"$/g, '');
            const em = b.querySelector('em'), emOn = em && getComputedStyle(em).display !== 'none' && em.textContent.trim();
            return { cat: b.dataset.cat, l: r.left, r: r.right, w: r.width, h: r.height, on: b.classList.contains('on'), lbl,
              cut: b.scrollWidth > b.clientWidth + 1 || (spOn && sp.scrollWidth > sp.clientWidth + 1),
              wrap: spOn ? sp.getClientRects().length > 1 || sp.getBoundingClientRect().height > lh : false,
              emFs: emOn ? parseFloat(getComputedStyle(em).fontSize) : null, fs: parseFloat(cs.fontSize) }; }) }; }"""
    cnt = lambda pg: pg.evaluate("() => { const c = document.getElementById('artCount'); return c && c.dataset.n !== undefined ? +c.dataset.n : -1; }")
    cats_of = lambda pg: pg.evaluate("() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.cat)")

    def tabs_ok(tag, st, short):
        tb = st["tabs"]
        okw = len(tb) == 5 and all(t["l"] >= st["cats"][0] - 0.5 and t["r"] <= st["cats"][1] + 0.5 and t["l"] >= 0 and t["r"] <= st["vw"] + 0.5 for t in tb)
        ok(f"{T}[{tag}]：五格分頁全部在外框與視窗內、外框不用橫捲（ov={st['ov']}）、整頁沒有橫向捲軸",
           okw and st["ov"] <= 1 and st["sw"] <= 0, st)
        ok(f"{T}[{tag}]：每格字完整（沒有被切成…）、不換行", all(not t["cut"] and not t["wrap"] for t in tb), tb)
        if short:
            ws = [t["w"] for t in tb]
            ok(f"{T}[{tag}]：手機五格等寬（{[round(w) for w in ws]}）、短名＝全部／快訊／產業鏈／知識、篇數小字 ≥ 11px、分頁字 ≥ 11px",
               max(ws) - min(ws) <= 1.5 and [t["lbl"] for t in tb] == ["全部", "快訊", "產業鏈", "知識", "盤前"]
               and all(t["fs"] >= 11 and (t["emFs"] is None or t["emFs"] >= 11) for t in tb) and any(t["emFs"] for t in tb), tb)
            ok(f"{T}[{tag}]：五格填滿內容寬（外框 {round(st['cats'][1] - st['cats'][0])} ≥ 視窗 {st['vw']} − 40）", st["cats"][1] - st["cats"][0] >= st["vw"] - 40, st["cats"])
        else:
            ok(f"{T}[{tag}]：電腦版名稱照舊（全部文章／比比快訊／比比產業鏈／比比知識／盤前消息）", [t["lbl"] for t in tb] == ["全部文章", *SUBT, "盤前消息"], [t["lbl"] for t in tb])

    def filter_round(tag, pg, tap):
        n_all = cnt(pg); seen = {"all": n_all}
        for c in ("news", "intro", "know", "all"):
            sel = f"#artCats>button[data-cat={c}]"
            (pg.locator(sel).tap() if tap else pg.locator(sel).click())
            want = "#articles" if c == "all" else "#articles/" + c
            wait_until(pg, f"() => location.hash === '{want}' && document.querySelector('{sel}').classList.contains('on')", 5000); pg.wait_for_timeout(250)
            n, cs = cnt(pg), cats_of(pg)
            if c == "all":
                ok(f"{T}[{tag}]：點回「全部」→ #articles、篇數回到 {n_all}", n == n_all and len(cs) == n_all, [n, n_all])
            else:
                seen[c] = n
                ok(f"{T}[{tag}]：點「{c}」→ {want}、篇數 {n_all} → {n}（變少了）、卡片全是 {c}",
                   0 < n < n_all and len(cs) == n and all(x == c for x in cs), [n, n_all, cs])
        ok(f"{T}[{tag}]：三個類別篇數兩兩不同（{seen}）—— 確認是真的換了清單，不是同一份", len({seen["news"], seen["intro"], seen["know"]}) == 3, seen)

    # ---- 電腦 1440
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.removeItem('l4.navFold')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort()); c.route("**/articles/index.json", idx_route)
    pg = c.new_page()
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.querySelector('#tabs .tab[data-view=articles]')", 15000); pg.wait_for_timeout(500)
    side = pg.evaluate("""() => ({ subs: document.querySelectorAll('#tabs .l4subtab[data-parent=articles], #tabs [data-l4sub^=art-]').length,
        txt: [...document.querySelectorAll('#tabs *')].filter(e => e.getClientRects().length && !e.children.length).map(e => e.textContent.trim()),
        nav: Object.keys(((window.TwL4Nav || {}).SUBS_DESK) || {}) })""")
    ok(f"{T}[1440]：側欄精選文章底下沒有子項（比比快訊／比比產業鏈／比比知識都不在側欄）",
       side["subs"] == 0 and not any(t in SUBT for t in side["txt"]) and "精選文章" in side["txt"] and "articles" not in side["nav"], side)
    pg.click("#tabs .tab[data-view=articles]")
    wait_until(pg, "() => location.hash === '#articles' && document.querySelectorAll('#artList .artc').length > 0", 10000); pg.wait_for_timeout(400)
    st = pg.evaluate("() => ({ on: (document.querySelector('#artCats>button.on') || {}).dataset.cat, l4sub: document.documentElement.getAttribute('data-l4sub'), tab: getComputedStyle(document.querySelector('#tabs .tab[data-view=articles]')).backgroundColor })")
    ok(f"{T}[1440]：點側欄「精選文章」→ #articles、分頁亮「全部文章」、不掛 data-l4sub、母項實心反白（不是讓位給子項的透明底）",
       st["on"] == "all" and st["l4sub"] is None and st["tab"] not in ("rgba(0, 0, 0, 0)", "transparent"), st)
    tabs_ok("1440", pg.evaluate(TABST), False)
    filter_round("1440", pg, False)
    # 深連結（新分頁直接開 #articles/know）＋頁首只有「精選文章」不帶子名
    p2 = c.new_page(); p2.goto(base + "#articles/know", wait_until="domcontentloaded")
    wait_until(p2, "() => document.querySelectorAll('#artList .artc').length > 0 && !!document.querySelector('#artCats>button.on')", 15000); p2.wait_for_timeout(400)
    st = p2.evaluate("() => ({ on: document.querySelector('#artCats>button.on').dataset.cat, head: ((document.getElementById('l4Head') || {}).textContent || ''), cats: [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.cat) })")
    ok(f"{T}[1440]：直接開 #articles/know → 分頁亮知識、卡片全是知識、頁首不再掛子分頁名",
       st["on"] == "know" and st["cats"] and all(x == "know" for x in st["cats"]) and "精選文章" in st["head"] and not any(t in st["head"] for t in SUBT), st)
    for w in (1024, 1280):   # 窄一點的電腦寬度：分頁也不能被裁
        p2.set_viewport_size({"width": w, "height": 900}); p2.wait_for_timeout(500)
        st = p2.evaluate(TABST)
        ok(f"{T}[{w}]：四格分頁在外框內、字沒有被切、不換行", st["ov"] <= 1 and all(t["l"] >= st["cats"][0] - 0.5 and t["r"] <= st["cats"][1] + 0.5 and not t["cut"] and not t["wrap"] for t in st["tabs"]), st)
    if os.environ.get("TW_ARTNAV_SHOTS"):
        pg.screenshot(path=str(Path(os.environ["TW_ARTNAV_SHOTS"]) / "artnav-1440.png"))
    c.close()

    # ---- 手機 360／390／430（觸控）
    for w in (360, 390, 430):
        tag = str(w)
        m = b.new_context(viewport={"width": w, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.add_init_script("try{localStorage.setItem('tw.live.on','0')}catch(e){}")
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort()); m.route("**/articles/index.json", idx_route)
        mp = m.new_page()
        mp.goto(base + "#overview", wait_until="domcontentloaded"); wait_until(mp, "() => !!document.getElementById('m4Burger')", 15000); mp.wait_for_timeout(700)
        mp.locator("#m4Burger").tap(); wait_until(mp, "() => { const d = document.getElementById('m4Drawer'); return d && !d.hidden; }", 4000); mp.wait_for_timeout(400)
        dr = mp.evaluate("""() => { const d = document.getElementById('m4Drawer');
            return { txt: [...d.querySelectorAll('*')].filter(e => e.getClientRects().length && !e.children.length).map(e => e.textContent.trim()),
              art: !!d.querySelector('button[data-v=articles]') }; }""")
        ok(f"{T}[{tag}]：手機抽屜有「精選文章」、沒有比比快訊／比比產業鏈／比比知識", dr["art"] and not any(t in SUBT for t in dr["txt"]), dr)
        mp.locator('#m4Drawer button[data-v="articles"]').tap()
        wait_until(mp, "() => location.hash === '#articles' && document.querySelectorAll('#artList .artc').length > 0", 10000); mp.wait_for_timeout(500)
        tabs_ok(tag, mp.evaluate(TABST), True)
        if os.environ.get("TW_ARTNAV_SHOTS") and w == 390:
            mp.screenshot(path=str(Path(os.environ["TW_ARTNAV_SHOTS"]) / "artnav-390.png"))
        filter_round(tag, mp, True)
        mp.goto(base + "#articles/intro", wait_until="domcontentloaded")
        wait_until(mp, "() => document.querySelectorAll('#artList .artc').length > 0 && !!document.querySelector('#artCats>button.on')", 15000); mp.wait_for_timeout(300)
        st = mp.evaluate("() => ({ on: document.querySelector('#artCats>button.on').dataset.cat, cats: [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.cat) })")
        ok(f"{T}[{tag}]：手機直接開 #articles/intro → 分頁亮產業鏈、卡片全是產業鏈", st["on"] == "intro" and st["cats"] and all(x == "intro" for x in st["cats"]), st)
        m.close()


# ★ 2026-10-16 Andy：「精選文章已經裡面有分頁，側邊子分頁就拿掉，並且手機版的分頁需要適當調整寬度」
#   —— 側欄／抽屜沒有比比快訊等子項、四格分頁完整不裁不換行（1440／360／390／430）、點每格真的篩選、#articles/<類別> 深連結
register("精選文章分頁1016", lambda pg, b, base, code: t_artnav_1016(b, base), after="精選文章1014")
