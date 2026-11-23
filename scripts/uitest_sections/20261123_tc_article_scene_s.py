# 驗收段落「文章精簡剖析圖與公司卡1123」（site/articles.js：scene size:'s'、stocks 的 biz／mkt／外國公司）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-23：文章要能嵌站內 2D／3D 剖析圖「但版面不用太大」；每家公司都要有 LOGO 與業務說明。
# 真的操作：用 page.route 攔 2026-11-19-tech-hbm.json 換成帶 scene size:'s' 與外國公司卡的假 JSON，
# 開文章、量畫布高度、數說明卡、按「展開全部」、點外國公司卡確認不會跳頁。
import json as _sc_json
import os as _sc_os

_SC_SHOT = "/tmp/claude-0/-home-user-tw-rotation/4f7a0102-8fac-5da8-aae4-92443922682f/scratchpad/shots"


def t_art_scene_s_1123(b, base, code):
    T = "文章精簡剖析圖與公司卡1123"
    errs = []
    _sc_os.makedirs(_SC_SHOT, exist_ok=True)
    blocks = []
    blocks += [
        {"t": "h", "text": "HBM 長什麼樣"},
        {"t": "scene", "kind": "3d", "id": "hbm", "title": "HBM 立體剖面", "caption": "可拖曳旋轉", "size": "s"},
        {"t": "stocks", "title": "", "items": [
            {"code": "000660", "name": "SK hynix", "mkt": "KRX", "biz": "全球 HBM 市佔第一的記憶體廠", "why": "HBM 主要供應商"},
            {"code": "AMD", "name": "Advanced Micro Devices", "mkt": "NASDAQ", "biz": "設計 AI 加速器與 CPU", "why": "HBM 的買家"},
            {"code": "ASML", "name": "ASML", "mkt": "Euronext", "biz": "EUV 曝光機", "why": "設備"},
            {"code": "2330", "name": "台積電", "mkt": "TWSE", "biz": "晶圓代工與先進封裝", "why": "CoWoS 封裝"},
        ]},
    ]

    def art(route):
        # 真檔照拿（保留 id／標題／日期等欄位），只把 blocks 換成測試用的
        fake = _sc_json.loads(route.fetch().text()); fake["blocks"] = [x for x in fake["blocks"] if x["t"] in ("lead", "sum")] + blocks
        route.fulfill(status=200, body=_sc_json.dumps(fake), headers={"content-type": "application/json", "access-control-allow-origin": "*"})

    for W in (1440, 390):
        mob = W <= 640
        c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/articles/tech/2026-11-19-tech-hbm.json*", art)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}:{e}"))
        pg.goto(base + "#article/2026-11-19-tech-hbm", wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('.artscene.s')", 20000)
        pg.locator(".artscene.s").scroll_into_view_if_needed()
        wait_until(pg, "() => document.querySelector('.artscene.s')?.dataset.st === 'ready'", 30000)
        pg.wait_for_timeout(1500)
        info = pg.evaluate("""() => { const f = document.querySelector('.artscene.s'); const cv = f.querySelector('canvas');
            const cards = [...f.querySelectorAll('.dgstage-b > *')];
            return { st: f.dataset.st, ch: cv ? Math.round(cv.getBoundingClientRect().height) : -1, total: cards.length,
              vis: cards.filter(e => e.getClientRects().length).length,
              btn: (f.querySelector('.asmore') || {}).textContent || '', btnShown: !!(f.querySelector('.asmore') && f.querySelector('.asmore').getClientRects().length) }; }""")
        lim = 360 if not mob else 260
        ok(f"★ [{T}（{W}）] 精簡 3D 載入成功、畫布高度 ≤{lim}（實際 {info['ch']}）", info["st"] == "ready" and 0 < info["ch"] <= lim, info)
        ok(f"★ [{T}（{W}）] 說明卡預設只顯示 ≤6 張（共 {info['total']}、顯示 {info['vis']}），超過 6 張時有展開鈕", info["vis"] <= 6 and (info["total"] <= 6 or (info["btnShown"] and "展開全部" in info["btn"])), info)
        if info["total"] > 6:
            pg.locator(".artscene.s .asmore").click(); pg.wait_for_timeout(400)
            n2 = pg.evaluate("() => [...document.querySelectorAll('.artscene.s .dgstage-b > *')].filter(e => e.getClientRects().length).length")
            ok(f"★ [{T}（{W}）] 按「展開全部」後顯示張數變多（{info['vis']}→{n2}）", n2 > info["vis"], n2)
        pg.evaluate("() => document.querySelector('.artscene.s').scrollIntoView({block:'start'})")
        pg.screenshot(path=f"{_SC_SHOT}/tc_scene_s_{W}.png")
        # 公司卡
        h0 = pg.evaluate("() => location.hash")
        st = pg.evaluate("""() => { const g = [...document.querySelectorAll('.artstk.neo .g > *')];
            return { n: g.length, title: document.querySelector('.artstk.neo .lbl').textContent,
              foreignLinks: g.filter(e => ['AMD','ASML','000660'].includes(e.dataset.code) && (e.tagName === 'A' || e.querySelector('a[href]'))).length,
              twLink: g.filter(e => e.dataset.code === '2330' && e.tagName === 'A' && e.getAttribute('href') === '#stock/2330').length,
              tx: g.filter(e => e.querySelector('.lg.tx')).length, mk: g.map(e => e.querySelector('.t b').textContent),
              hs: Object.values(g.reduce((m, e) => { const r = e.getBoundingClientRect(); (m[Math.round(r.top)] = m[Math.round(r.top)] || new Set()).add(Math.round(r.height)); return m; }, {})).map(x => x.size), logoH: Math.round(g[0].querySelector('.lg').getBoundingClientRect().height) }; }""")
        ok(f"★ [{T}（{W}）] 公司卡 4 張、標題預設「相關公司」、代號旁顯示交易所", st["n"] == 4 and st["title"] == "相關公司" and "AMD・NASDAQ" in st["mk"] and "000660・KRX" in st["mk"], st)
        ok(f"★ [{T}（{W}）] 外國公司卡沒有 #stock 連結、台股卡有", st["foreignLinks"] == 0 and st["twLink"] == 1, st)
        ok(f"[{T}（{W}）] 沒有 logo 的卡都有文字卡（4 張）、LOGO 固定 28px 高", st["tx"] == 4 and st["logoH"] == 28, st)
        if not mob:
            ok(f"[{T}（{W}）] 同一列卡片等高", all(n == 1 for n in st["hs"]), st["hs"])
        pg.locator(".artstk.neo .g > [data-code='AMD']").click(); pg.wait_for_timeout(500)
        ok(f"★ [{T}（{W}）] 點外國公司卡不跳頁", pg.evaluate("() => location.hash") == h0, pg.evaluate("() => location.hash"))
        ok(f"[{T}（{W}）] 沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 1)
        pg.locator(".artstk.neo").scroll_into_view_if_needed()
        pg.screenshot(path=f"{_SC_SHOT}/tc_stocks_{W}.png")
        c.close()
    ok(f"{T}：全程沒有頁面例外", not errs, errs[:3])


register("文章精簡剖析圖與公司卡1123", lambda pg, b, base, code: t_art_scene_s_1123(b, base, code))
