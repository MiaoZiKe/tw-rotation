# 驗收段落「單篇公開1020」—— 2026-10-20 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_free_port()、ROOT… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 單篇公開1020（site/articles.js isOpenArt／remoteGet(pub)、workers/account-api/articles.js OPEN_ARTICLE_IDS）
# Andy 10-20：「暫時把這篇設成免費公開」—— 錄「今日事件＋精選文章」功能影片要用未登入訪客畫面，特斯拉那篇（2026-10-17-news-tesla）暫時開放全文。
# 起真的 worker.js（devserver.mjs），用**真的 site/articles/index.json**（那篇帶 open:true），以未登入訪客真的操作：
#   · 列表：特斯拉那張卡沒有鎖（data-lock=0、寫「限時公開」）；另一篇非公開的新文章仍是鎖卡（data-lock=1、寫「全文需 Plus 以上」）
#   · 真的點特斯拉那張卡 → 進詳情頁：內文來自會員後端（BODY-OPEN）、插圖（文章圖表）真的畫出來（有寬高、有 canvas）、沒有升級卡
#     ＋ 那次 /v1/articles/get 回 200 且請求裡沒有權杖
#   · 回列表點非公開那張 → 鎖定頁、DOM 沒有內文
#   · 不經畫面直接打後端讀非公開那篇（帶 open:true 想騙）→ 401、沒有內文
#   · 手機 390：特斯拉詳情頁可讀、沒有橫向捲軸
# ⚠ 一律 --workers 1（起 devserver 用）

AO_BOT_KEY = "dev-article-bot-key-0123456789abcdef"      # 跟 workers/account-api/devserver.mjs 的 ARTICLE_BOT_KEY 一致（只在本機）
AO_OPEN = "2026-10-17-news-tesla"


def t_article_open_1020(b, base, code):
    import urllib.request
    T = "單篇公開1020"
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    idx = json.loads((ROOT / "site" / "articles" / "index.json").read_text(encoding="utf-8"))
    arts = idx.get("articles") or []
    # 10-20 錄完影片已關閉：index.json 沒有任何 open:true（Worker 的 OPEN_ARTICLE_IDS 也是空）時，
    # 跳過「公開那篇」的檢查，只驗非公開文章仍然上鎖；日後再開放某篇時，這段會自動恢復完整檢查。
    open_ids = [a.get("id") for a in arts if a.get("open") is True]
    is_open = AO_OPEN in open_ids
    if not is_open:
        ok(f"{T}：目前沒有任何公開文章（index.json 無 open:true）", not open_ids, open_ids)
    # 同一天（同在預設日期區間）的另一篇非公開新文章當對照
    other = next((a["id"] for a in arts if a.get("src") == "api" and a.get("id") != AO_OPEN and not a.get("open") and a.get("date") == "2026-10-17"), None)
    if not ok(f"{T}：找得到一篇同日期的非公開新文章當對照", bool(other)):
        return
    port = _free_port()
    dbg = bool(os.environ.get("TW_DEV_LOG"))
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=None if dbg else subprocess.DEVNULL, stderr=None if dbg else subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api（devserver）起得來", up):
            return

        def bot(body):
            r = urllib.request.Request(api + "/v1/articles/jobs/bot", data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + AO_BOT_KEY}, method="POST")
            return json.loads(urllib.request.urlopen(r, timeout=10).read())

        chart = {"t": "chart", "kind": "bar", "title": "驗收插圖", "x": ["A", "B", "C"], "series": [{"name": "數值", "data": [3, 5, 2]}]}
        for pid, tag in (((AO_OPEN, "OPEN"),) if is_open else ()) + ((other, "LOCKED"),):
            r = bot({"op": "put_body", "id": pid, "json": {"id": pid, "cat": "news", "title": "驗收 " + tag, "date": "2026-10-17", "reading_min": 3,
                                                           "blocks": [{"t": "h", "text": "小標"}, {"t": "p", "text": "BODY-" + tag}, chart], "sources": [], "site_links": []}})
            ok(f"{T}：機器路由上傳 {pid} 全文", bool(r.get("ok")), r)

        def new_ctx(width=1440):
            c = b.new_context(viewport={"width": width, "height": 900 if width > 640 else 844}, has_touch=width <= 640, is_mobile=width <= 640)
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.live.on','0')}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        CARDS = """() => [...document.querySelectorAll('#artList .artc')].map(a => ({ id: a.dataset.id, lock: a.dataset.lock, free: a.dataset.free || '', lk: (a.querySelector('.lk') || {}).textContent || '' }))"""
        POST = """() => { const f = document.querySelector('.artbody .artchart'), r = f ? f.getBoundingClientRect() : null;
            return { body: (document.querySelector('.artbody') || {}).textContent || null, lock: !!document.getElementById('artLock'),
              html: (document.getElementById('v-articles') || {}).innerHTML || '', fig: r ? [Math.round(r.width), Math.round(r.height)] : null,
              cv: f ? !!f.querySelector('canvas, svg') : false, qt: (document.querySelector('.artqt') || {}).textContent || '',
              sw: document.documentElement.scrollWidth, vw: window.innerWidth }; }"""

        def to_list(pg):
            pg.goto(base + "#articles", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#artList .artc').length > 0", 15000)
            pg.wait_for_timeout(1500)       # 等權限（permReady）載完，列表以訪客身分重畫

        def click_card(pg, pid):
            pg.locator(f'#artList .artc[data-id="{pid}"]').first.scroll_into_view_if_needed()
            pg.locator(f'#artList .artc[data-id="{pid}"]').first.click()
            wait_until(pg, "() => !!document.querySelector('#artPost') && (!!document.querySelector('.artbody') || !!document.getElementById('artLock') || !!document.getElementById('artErr'))", 12000)
            pg.wait_for_timeout(900)        # 圖表初始化
            return pg.evaluate(POST)

        # ================= 桌機 1440 訪客
        cg = new_ctx(); pg = cg.new_page()
        gets = []
        pg.on("request", lambda r: gets.append(r.post_data or "") if "/v1/articles/get" in r.url and r.method == "POST" else None)
        to_list(pg)
        cs = {c["id"]: c for c in pg.evaluate(CARDS)}
        co, cl = cs.get(AO_OPEN), cs.get(other)
        ok(f"{T}[訪客]：同日期非公開那張仍是鎖卡（data-lock=1、寫「全文需 Plus 以上」）", bool(cl) and cl["lock"] == "1" and "Plus" in cl["lk"], cl)
        if is_open:
            ok(f"{T}[訪客]：列表上特斯拉那張卡沒有鎖（data-lock=0、寫「限時公開」）", bool(co) and co["lock"] == "0" and co["free"] == "1" and "限時公開" in co["lk"], co)
            p = click_card(pg, AO_OPEN)
            ok(f"{T}[訪客]：真的點特斯拉那張 → 網址換成 #article/{AO_OPEN}", pg.evaluate("() => location.hash") == "#article/" + AO_OPEN, pg.evaluate("() => location.hash"))
            ok(f"{T}[訪客]：詳情頁內文來自會員後端（BODY-OPEN）、沒有升級卡、寫「限時公開・不佔額度」", "BODY-OPEN" in (p["body"] or "") and not p["lock"] and "限時公開" in p["qt"], [p["body"], p["lock"], p["qt"]])
            ok(f"{T}[訪客]：插圖（文章圖表）真的畫出來（寬高 > 0、有畫布）", bool(p["fig"]) and p["fig"][0] > 100 and p["fig"][1] > 80 and p["cv"], [p["fig"], p["cv"]])
            okreq = gets and all('"t"' not in g for g in gets)
            ok(f"{T}[訪客]：向 /v1/articles/get 要全文，請求裡沒有登入權杖", bool(okreq), gets)
        to_list(pg)
        p2 = click_card(pg, other)
        ok(f"{T}[訪客]：點非公開那張 → 鎖定頁、DOM 沒有內文", p2["lock"] and p2["body"] is None and "BODY-LOCKED" not in p2["html"], [p2["lock"], p2["body"]])
        raw = pg.evaluate("async ([a, id]) => { const r = await fetch(a + '/v1/articles/get', { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify({ id, open: true }) }); return { s: r.status, t: await r.text() }; }", [api, other])
        ok(f"{T}[訪客]：直接打後端讀非公開那篇（自己加 open:true）→ 401、沒有內文", raw["s"] == 401 and "BODY-LOCKED" not in raw["t"], raw)
        cg.close()

        # ================= 手機 390 訪客
        cm = new_ctx(390); pm = cm.new_page()
        to_list(pm)
        if is_open:
            p = click_card(pm, AO_OPEN)
            ok(f"{T}[手機 390]：特斯拉詳情頁可讀（有內文、有插圖）、沒有橫向捲軸", "BODY-OPEN" in (p["body"] or "") and bool(p["fig"]) and p["sw"] <= p["vw"] + 1, [p["fig"], p["sw"], p["vw"]])
        else:
            p = click_card(pm, other)
            ok(f"{T}[手機 390]：非公開文章仍是鎖定頁、沒有內文、沒有橫向捲軸", p["lock"] and p["body"] is None and p["sw"] <= p["vw"] + 1, [p["lock"], p["sw"], p["vw"]])
        cm.close()
    finally:
        for c in ctxs:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()
        try:
            dev.wait(timeout=5)
        except Exception:  # noqa: BLE001
            dev.kill()


register("單篇公開1020", lambda pg, b, base, code: t_article_open_1020(b, base, code))
