# 驗收段落「精選文章分級1016」—— 2026-10-16 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、_acctm4_ctx()、ACCTM4_WHO… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 精選文章分級1016（site/articles.js、site/quota.js 的 TwQuota.total）
# Andy 10-16：「精選貼文限制給 Pro 可以看，Plus 只能所有類別共 5 篇，其他的只能看到標題。」
#   Pro＝全文；Plus＝所有分類合計累計 5 篇全文（同一篇重讀不重算、打開過的永遠能讀），用完其餘只看標題＋升級卡；訪客、註冊會員只看標題；管理者不受限。
# 真人操作（每一步都驗畫面真的變了，不是驗元素存在），五種身分各自一個瀏覽器環境（假會員 API 回該身分的 /v1/perm/me）：
#   · Plus（主線）：列表額度條 0／5 → 真的點開第 1 篇（全文在 DOM、額度 1／5）→ 回列表第 1 張卡解鎖（有摘要）、其餘只有標題 →
#     依序開到第 5 篇（5／5）→ 重讀第 1 篇不再增加 → 第 6 篇：**全文不在 DOM、沒有去抓文章 JSON**、升級卡、額度不變 → 重新整理仍鎖著 →
#     已解鎖清單的連結點得進去 → 回列表被鎖的卡寫「額度已用完」、DOM 裡沒有被鎖文章的摘要
#   · 訪客／註冊會員：列表與單篇都只有標題＋升級提示，**一篇文章 JSON 都沒抓**；累計紀錄沒有被寫
#   · Pro／管理者：額度條不顯示、全部全文、沒有累計紀錄
#   · 預覽版示範身分 ?demo_tier=plus（預覽版本來是擁有者全開，加參數才看得到限制）
#   · 手機 390（觸控）：額度條與升級卡在畫面內、沒有橫向捲軸、字 ≥ 11px
# 截圖：TW_ARTIER_SHOTS=<資料夾>
def t_artier_1016(b, base, code):
    import datetime as _dt
    T = "精選文章分級1016"
    today = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).date().isoformat()
    N = 8
    fakes = [{"id": f"uitest-tier-{i}", "cat": ["news", "intro", "know"][i % 3], "title": f"分級驗收文章{i}", "subtitle": f"SUB-SECRET-{i}", "date": today, "tags": [],
              "summary": f"SUMMARY-SECRET-{i}", "reading_min": 2, "groups": [{"id": "foundry", "name": "晶圓代工"}]} for i in range(1, N + 1)]
    posts = {a["id"]: {**a, "blocks": [{"t": "h", "text": f"標題區塊{a['id'][-1]}"}, {"t": "p", "text": f"BODY-SECRET-{a['id'][-1]}"}], "site_links": [], "sources": []} for a in fakes}
    reqs = []       # 這個測試期間「抓過哪些文章 JSON」
    shots = os.environ.get("TW_ARTIER_SHOTS")

    def idx_route(r):
        r.fulfill(status=200, content_type="application/json", body=json.dumps({"updated": today, "articles": fakes}, ensure_ascii=False))

    def post_route(r):
        m = re.search(r"/posts/([^/]+)\.json", r.request.url)
        pid = m.group(1) if m else ""
        reqs.append(pid)
        if pid in posts:
            r.fulfill(status=200, content_type="application/json", body=json.dumps(posts[pid], ensure_ascii=False))
        else:
            r.fulfill(status=404, body="{}")

    PERM = {
        "guest": {"who": "guest", "plan": "guest", "planName": "訪客", "feats": {"art.read.n": 0}, "lims": {}, "dq": None},
        "free": {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {"art.read.n": 0}, "lims": {}, "dq": None},
        "plus": {"who": "member", "plan": "plus", "planName": "Plus", "feats": {}, "lims": {}, "dq": None},     # 範本沒寫 → 吃 features.js 的 defBy（Plus 5）
        "pro": {"who": "member", "plan": "pro", "planName": "Pro", "feats": {"art.read.n": 999}, "lims": {}, "dq": None},
        "admin": {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {"art.read.n": 0}, "lims": {}, "dq": None},
    }

    def mk(who, desk=True, vp=None, seed=None, preview=False):
        c, _ = _acctm4_ctx(b, who, desk=desk, perm=PERM[who], vp=vp)
        init = "try{localStorage.setItem('tw.live.on','0')}catch(e){}"
        if seed:
            init += "try{if(!sessionStorage.getItem('artseed')){sessionStorage.setItem('artseed','1');localStorage.setItem('tw.total'," + json.dumps(json.dumps(seed)) + ");}}catch(e){}"
        if preview:
            init += "window.TW_PREVIEW={name:'uitest'};"
        c.add_init_script(init)
        c.route("**/articles/index.json", idx_route)
        c.route("**/articles/posts/*.json", post_route)
        return c

    def to_list(pg, url_suffix="#articles"):
        pg.goto(base + url_suffix, wait_until="domcontentloaded")
        wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 15000)
        pg.wait_for_timeout(500)

    ST = """() => { const q = document.getElementById('artQuota'), cs = [...document.querySelectorAll('#artList .artc')];
        return { mode: q ? q.dataset.mode : null, vis: !!q && !q.hidden && q.getClientRects().length > 0, used: q ? q.dataset.used : null, lim: q ? q.dataset.lim : null, txt: q ? q.textContent : '',
          go: q && q.querySelector('a.qgo') ? [q.querySelector('a.qgo').textContent.trim(), q.querySelector('a.qgo').getAttribute('href')] : null,
          cards: cs.map(a => ({ id: a.dataset.id, lock: a.dataset.lock, sm: !!a.querySelector('.sm'), st: !!a.querySelector('.st'), lk: (a.querySelector('.lk') || {}).textContent || '' })),
          html: document.getElementById('artList').innerHTML }; }"""
    POST = """() => ({ body: (document.querySelector('.artbody') || {}).textContent || null, lock: !!document.getElementById('artLock'), card: !!document.querySelector('#artLock .qcard'),
        cardTxt: (document.querySelector('#artLock .qcard') || {}).textContent || '', html: (document.getElementById('v-articles') || {}).innerHTML || '',
        qt: (document.querySelector('.artqt') || {}).textContent || '', unl: [...document.querySelectorAll('#artLock .unl a')].map(a => a.getAttribute('href')),
        title: (document.querySelector('h2.artttl') || {}).textContent || '', go: (document.querySelector('#artLock .qc-go') || {}).textContent || '' })"""
    TOTAL = "() => { try { return JSON.parse(localStorage.getItem('tw.total') || 'null'); } catch (e) { return 'bad'; } }"

    def open_post(pg, i):
        pg.evaluate("h => { location.hash = h; }", f"#article/uitest-tier-{i}")
        wait_until(pg, "() => !!document.querySelector('#artPost') && (!!document.querySelector('.artbody') || !!document.getElementById('artLock') || !!document.getElementById('artErr'))", 10000)
        pg.wait_for_timeout(350)
        return pg.evaluate(POST)

    def keys_of(pg, who="plus@example.com"):
        t = pg.evaluate(TOTAL)
        return ((t or {}).get("u:" + who) or {}).get("art.read.n", []) if isinstance(t, dict) else None

    # ============ Plus 1440（主線）
    c = mk("plus")
    pg = c.new_page()
    to_list(pg)
    st = pg.evaluate(ST)
    ok(f"{T}[Plus]：列表頂端額度條＝Plus 全文額度 0／5（累計），{N} 張卡全是鎖定（只有標題），沒有升級鈕（還有額度）",
       st["vis"] and st["mode"] == "quota" and st["lim"] == "5" and st["used"] == "0" and "0／5" in st["txt"] and "累計" in st["txt"] and len(st["cards"]) == N
       and all(x["lock"] == "1" and not x["sm"] and not x["st"] and "點開會用掉 1 篇額度" in x["lk"] for x in st["cards"]) and st["go"] is None, st)
    ok(f"{T}[Plus]：列表 DOM 裡完全沒有任何摘要／副標文字（不是 CSS 藏起來）", "SUMMARY-SECRET" not in st["html"] and "SUB-SECRET" not in st["html"], None)
    if shots:
        pg.screenshot(path=str(Path(shots) / "plus-list-0of5-1440.png"))
    pg.click('#artList .artc[data-id="uitest-tier-1"]')
    wait_until(pg, "() => !!document.querySelector('.artbody')", 8000); pg.wait_for_timeout(300)
    p1 = pg.evaluate(POST)
    ok(f"{T}[Plus]：真的點第 1 張卡 → 全文出現在畫面（BODY-SECRET-1）、麵包屑旁寫「全文額度 1／5 篇」、累計紀錄寫進 localStorage（1 筆）",
       "BODY-SECRET-1" in (p1["body"] or "") and "1／5" in p1["qt"] and keys_of(pg) == ["uitest-tier-1"] and not p1["lock"], [p1["qt"], keys_of(pg)])
    pg.go_back(); wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 8000); pg.wait_for_timeout(400)
    st = pg.evaluate(ST)
    c1 = next(x for x in st["cards"] if x["id"] == "uitest-tier-1")
    ok(f"{T}[Plus]：回列表 → 額度條 1／5、第 1 張卡解鎖（有摘要、寫「已解鎖」）、其餘 7 張仍鎖定且沒有摘要",
       st["used"] == "1" and "1／5" in st["txt"] and c1["lock"] == "0" and c1["sm"] and "已解鎖" in c1["lk"]
       and all(x["lock"] == "1" and not x["sm"] for x in st["cards"] if x["id"] != "uitest-tier-1") and "SUMMARY-SECRET-2" not in st["html"] and "SUMMARY-SECRET-1" in st["html"], st)
    for i in (2, 3, 4, 5):
        pp = open_post(pg, i)
        ok(f"{T}[Plus]：開第 {i} 篇 → 全文可讀、額度 {i}／5", f"BODY-SECRET-{i}" in (pp["body"] or "") and f"{i}／5" in pp["qt"] and len(keys_of(pg)) == i, [pp["qt"], keys_of(pg)])
    if shots:
        pg.screenshot(path=str(Path(shots) / "plus-article5-1440.png"))
    n_req_before = len(reqs)
    pp = open_post(pg, 1)
    ok(f"{T}[Plus]：5／5 之後重讀第 1 篇 → 照樣能讀、額度不增加（仍 5 筆）", "BODY-SECRET-1" in (pp["body"] or "") and len(keys_of(pg)) == 5, [pp["qt"], keys_of(pg)])
    reqs.clear()
    p6 = open_post(pg, 6)
    ok(f"{T}[Plus]：第 6 篇 → 內文處是升級卡（「全文額度 5／5 篇已用完」＋升級 Pro），**沒有文章內文**", p6["lock"] and p6["card"] and "5／5" in p6["cardTxt"] and "升級 Pro" in p6["go"] and p6["body"] is None, p6)
    ok(f"{T}[Plus]：第 6 篇的全文不在 DOM（整個 v-articles 找不到 BODY-SECRET-6）、也沒有去抓這篇的 JSON、標題仍看得到、累計紀錄仍是 5 筆",
       "BODY-SECRET-6" not in p6["html"] and "uitest-tier-6" not in reqs and "分級驗收文章6" in p6["title"] and len(keys_of(pg)) == 5, [reqs, keys_of(pg)])
    ok(f"{T}[Plus]：升級卡下面列出「已解鎖的 5 篇」連結", len(p6["unl"]) == 5 and all(("uitest-tier-" + str(i)) in " ".join(p6["unl"]) for i in (1, 2, 3, 4, 5)), p6["unl"])
    if shots:
        pg.screenshot(path=str(Path(shots) / "plus-article6-locked-1440.png"))
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('artLock') || !!document.querySelector('.artbody')", 10000); pg.wait_for_timeout(500)
    pr = pg.evaluate(POST)
    ok(f"{T}[Plus]：在第 6 篇重新整理 → 仍然鎖著（累計紀錄存在 localStorage，不會因重整歸零）", pr["lock"] and pr["body"] is None and len(keys_of(pg)) == 5, [pr["lock"], keys_of(pg)])
    pg.click('#artLock .unl a >> nth=0'); wait_until(pg, "() => !!document.querySelector('.artbody')", 8000); pg.wait_for_timeout(300)
    ok(f"{T}[Plus]：點已解鎖清單的連結 → 回到那篇全文", pg.evaluate("() => (document.querySelector('.artbody') || {}).textContent || ''").startswith("標題區塊") or "BODY-SECRET" in pg.evaluate("() => (document.querySelector('.artbody') || {}).textContent || ''"), None)
    to_list(pg)
    st = pg.evaluate(ST)
    locked = [x for x in st["cards"] if x["lock"] == "1"]
    ok(f"{T}[Plus]：5／5 後回列表 → 額度條「剩 0 篇」＋「升級 Pro 不限篇數」鈕；3 張鎖定卡寫「額度已用完・只顯示標題」、5 張已解鎖卡有摘要；被鎖文章的摘要不在 DOM",
       "剩 0" in st["txt"] and st["go"] and "升級 Pro" in st["go"][0] and len(locked) == 3 and all("額度已用完" in x["lk"] and not x["sm"] for x in locked)
       and "SUMMARY-SECRET-6" not in st["html"] and "SUMMARY-SECRET-1" in st["html"], st)
    pg.click('#artList .artc[data-id="uitest-tier-7"]'); wait_until(pg, "() => !!document.getElementById('artLock')", 8000); pg.wait_for_timeout(300)
    ok(f"{T}[Plus]：真的點一張鎖定卡（第 7 篇）→ 進到鎖定頁（升級卡）、仍沒有內文、累計仍 5 筆", pg.evaluate("() => !document.querySelector('.artbody') && !!document.querySelector('#artLock .qcard')") and len(keys_of(pg)) == 5, keys_of(pg))
    c.close()

    # ============ 訪客／註冊會員 1440
    for who, nm, btn in (("guest", "訪客", "登入或升級"), ("free", "註冊會員", "升級 Plus")):
        c = mk(who)
        pg = c.new_page()
        reqs.clear()
        to_list(pg)
        st = pg.evaluate(ST)
        ok(f"{T}[{nm}]：額度條＝只能看標題與分類（寫身分、寫「Plus 累計 5 篇」「Pro 不限篇數」）、升級鈕「{btn}」；{N} 張卡全是鎖定、沒有摘要／副標",
           st["vis"] and st["mode"] == "none" and nm in st["txt"] and "標題與分類" in st["txt"] and "5" in st["txt"] and st["go"] and btn in st["go"][0]
           and len(st["cards"]) == N and all(x["lock"] == "1" and not x["sm"] and not x["st"] and "Plus 以上" in x["lk"] for x in st["cards"])
           and "SUMMARY-SECRET" not in st["html"] and "SUB-SECRET" not in st["html"], st)
        if shots and who == "guest":
            pg.screenshot(path=str(Path(shots) / "guest-list-1440.png"))
        pg.click('#artList .artc[data-id="uitest-tier-2"]'); wait_until(pg, "() => !!document.getElementById('artLock')", 8000); pg.wait_for_timeout(300)
        pp = pg.evaluate(POST)
        ok(f"{T}[{nm}]：真的點一張卡 → 鎖定頁（標題＋升級卡「這篇文章的全文需要 Plus 以上」），沒有內文、DOM 沒有 BODY-SECRET、**一篇文章 JSON 都沒抓**、沒有寫累計紀錄",
           pp["lock"] and pp["card"] and "全文需要 Plus 以上" in pp["cardTxt"] and btn in pp["go"] and pp["body"] is None and "BODY-SECRET" not in pp["html"] and "SUMMARY-SECRET" not in pp["html"]
           and not [r for r in reqs if r.startswith("uitest-tier")] and pg.evaluate(TOTAL) is None, [pp["go"], reqs, pg.evaluate(TOTAL)])
        if shots and who == "guest":
            pg.screenshot(path=str(Path(shots) / "guest-article-locked-1440.png"))
        c.close()

    # ============ Pro／管理者 1440
    for who, nm in (("pro", "Pro"), ("admin", "管理者")):
        c = mk(who)
        pg = c.new_page()
        to_list(pg)
        st = pg.evaluate(ST)
        ok(f"{T}[{nm}]：不顯示額度條、{N} 張卡全部解鎖（有摘要）", not st["vis"] and len(st["cards"]) == N and all(x["lock"] == "0" and x["sm"] for x in st["cards"]), st)
        if shots and who == "pro":
            pg.screenshot(path=str(Path(shots) / "pro-list-1440.png"))
        for i in (1, 2, 3, 4, 5, 6, 7):
            pp = open_post(pg, i)
            if not (f"BODY-SECRET-{i}" in (pp["body"] or "") and not pp["lock"]):
                ok(f"{T}[{nm}]：第 {i} 篇可讀全文", False, pp)
                break
        else:
            ok(f"{T}[{nm}]：連開 7 篇（超過 Plus 的 5 篇）全部是全文、沒有任何鎖定", True)
        ok(f"{T}[{nm}]：不寫累計紀錄", pg.evaluate(TOTAL) is None, pg.evaluate(TOTAL))
        c.close()

    # ============ 預覽版示範身分（預覽版本來是擁有者全開）
    c = mk("plus", preview=True)
    pg = c.new_page()
    to_list(pg)
    ok(f"{T}[預覽版]：不加參數 → 擁有者全開（不顯示額度條、全部解鎖）", not pg.evaluate(ST)["vis"] and all(x["lock"] == "0" for x in pg.evaluate(ST)["cards"]), pg.evaluate(ST))
    to_list(pg, "?demo_tier=plus#articles")
    st = pg.evaluate(ST)
    ok(f"{T}[預覽版]：?demo_tier=plus → 額度條出現、寫「預覽示範身分：Plus」、{N} 張卡鎖定", st["vis"] and st["mode"] == "quota" and "預覽示範身分：Plus" in st["txt"] and all(x["lock"] == "1" for x in st["cards"]), st)
    pg.click('#artList .artc[data-id="uitest-tier-3"]'); wait_until(pg, "() => !!document.querySelector('.artbody')", 8000); pg.wait_for_timeout(300)
    t = pg.evaluate(TOTAL)
    ok(f"{T}[預覽版]：示範身分的計數另開（demo:plus），不寫進真實會員的紀錄", isinstance(t, dict) and "demo:plus" in t and not any(k.startswith("u:") for k in t), t)
    to_list(pg, "?demo_tier=off#articles")
    ok(f"{T}[預覽版]：?demo_tier=off → 回到擁有者全開", not pg.evaluate(ST)["vis"], None)
    c.close()

    # ============ 手機 390（觸控）
    seed5 = {"u:plus@example.com": {"art.read.n": [f"uitest-tier-{i}" for i in (1, 2, 3, 4, 5)]}}
    m = mk("plus", desk=False, vp=(390, 844))
    mp = m.new_page()
    to_list(mp)
    MS = """() => { const q = document.getElementById('artQuota'), r = q.getBoundingClientRect();
        const fs = [...q.querySelectorAll('*')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
        const lk = [...document.querySelectorAll('#artList .artc .lk')].map(e => parseFloat(getComputedStyle(e).fontSize));
        return { l: Math.round(r.left), r: Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, minq: Math.min(...fs), minlk: lk.length ? Math.min(...lk) : 99, txt: q.textContent }; }"""
    ms = mp.evaluate(MS)
    ok(f"{T}[手機390]：額度條在畫面內、沒有橫向捲軸、字 ≥ 11px、卡片的鎖定行字 ≥ 11px", ms["l"] >= 0 and ms["r"] <= ms["vw"] and ms["sw"] <= 1 and ms["minq"] >= 11 and ms["minlk"] >= 11 and "0／5" in ms["txt"], ms)
    if shots:
        mp.screenshot(path=str(Path(shots) / "plus-list-390.png"))
    mp.locator('#artList .artc[data-id="uitest-tier-1"]').tap()
    wait_until(mp, "() => !!document.querySelector('.artbody')", 8000); mp.wait_for_timeout(400)
    ok(f"{T}[手機390]：用手指點第 1 張卡 → 全文可讀、額度 1／5、沒有橫向捲軸", "BODY-SECRET-1" in (mp.evaluate(POST)["body"] or "") and "1／5" in mp.evaluate(POST)["qt"] and mp.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1, mp.evaluate(POST)["qt"])
    m.close()
    m = mk("plus", desk=False, vp=(390, 844), seed=seed5)
    mp = m.new_page()
    reqs.clear()
    mp.goto(base + "#article/uitest-tier-6", wait_until="domcontentloaded")
    wait_until(mp, "() => !!document.getElementById('artLock')", 15000); mp.wait_for_timeout(500)
    LS = """() => { const c = document.querySelector('#artLock .qcard'), r = c ? c.getBoundingClientRect() : null;
        const fs = [...document.querySelectorAll('#artLock *')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
        const bt = document.querySelector('#artLock .qc-go'), b = bt ? bt.getBoundingClientRect() : null;
        return { l: r && Math.round(r.left), r: r && Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, min: fs.length ? Math.min(...fs) : 0, btn: b && [Math.round(b.left), Math.round(b.right), Math.round(b.height)], body: !!document.querySelector('.artbody') }; }"""
    ls = mp.evaluate(LS)
    ok(f"{T}[手機390]：已用 5／5 直接開第 6 篇 → 升級卡在畫面內、沒有橫向捲軸、字 ≥ 11px、按鈕可點（高 ≥ 40）、沒有內文、沒抓文章 JSON",
       ls["l"] >= 0 and ls["r"] <= ls["vw"] and ls["sw"] <= 1 and ls["min"] >= 11 and ls["btn"] and ls["btn"][2] >= 40 and ls["btn"][1] <= ls["vw"] and not ls["body"] and "uitest-tier-6" not in reqs, [ls, reqs])
    if shots:
        mp.screenshot(path=str(Path(shots) / "plus-article6-locked-390.png"))
    m.close()


# ★ 2026-10-16 Andy：「精選貼文限制給 Pro 可以看，Plus 只能所有類別共 5 篇，其他的只能看到標題」—— 見檔頭
register("精選文章分級1016", lambda pg, b, base, code: t_artier_1016(b, base, code), after="精選文章分頁1016")
