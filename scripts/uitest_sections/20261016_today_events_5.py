# 驗收段落「今日事件訪客5次1016」—— 2026-10-16 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、_acctm4_ctx()、ACCTM4_WHO… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 今日事件訪客5次1016（site/app.js 今日事件抽屜與手機卡片、site/quota.js 的 TwQuota.total）
# Andy 10-16：「今日事件開放，修正，但限制次數 5 次 Total」—— 訪客累計 5 次（不歸零），滿了請註冊；註冊會員依既有額度不變。
# 「一次」的定義＝打開今日事件抽屜一次（手機總覽的今日事件卡：每個瀏覽器分頁第一次出現在畫面算一次）。
# 真人操作（每一步驗畫面真的變了）：
#   · 訪客 1440：真的按「事件」鈕 → 抽屜有事件清單、累計 1／5；關掉再開到第 5 次都有清單；
#     **第 6 次：清單不在 DOM（0 個 .ev）、換成「訪客預覽 5 次已用完」提示卡＋「免費註冊」鈕連 #pricing/plan/free**、累計仍 5；
#     點分類鈕仍擋著；重新整理後（抽屜關著）DOM 裡也沒有清單、再開仍是提示卡
#   · 訪客的範本若還留著舊的 events 每日 3 次（lims.events＝3）→ 不能干擾：第 4 次照樣開得到、沒有「今日已用完」遮罩
#   · 註冊會員：連開 7 次都有清單、沒有累計紀錄；管理者同
#   · 預覽版示範身分 ?demo_tier=guest
#   · 手機 390（觸控）：用手指開抽屜 → 清單；已滿 → 抽屜與總覽卡都是提示卡、在畫面內、沒有橫向捲軸、字 ≥ 11px；
#     總覽的今日事件卡捲進畫面算一次、同分頁重新整理不重複算
# 截圖：TW_EV5_SHOTS=<資料夾>
def t_today_events_5(b, base, code):
    T = "今日事件訪客5次1016"
    shots = os.environ.get("TW_EV5_SHOTS")
    GUEST = {"who": "guest", "plan": "guest", "planName": "訪客", "feats": {}, "lims": {"events": 3}, "dq": None}     # 範本沒寫 events.total → 吃 features.js defBy（訪客 5）；留著舊的每日 3 次
    FREE = {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {}, "lims": {}, "dq": None}

    def mk(who, perm, desk=True, vp=None, seed=None, preview=False):
        c, _ = _acctm4_ctx(b, who, desk=desk, perm=perm, vp=vp)
        init = "try{localStorage.setItem('tw.live.on','0')}catch(e){}"
        if seed:
            init += "try{if(!sessionStorage.getItem('evseed')){sessionStorage.setItem('evseed','1');localStorage.setItem('tw.total'," + json.dumps(json.dumps(seed)) + ");}}catch(e){}"
        if preview:
            init += "window.TW_PREVIEW={name:'uitest'};"
        c.add_init_script(init)
        return c

    def boot(pg, suffix="#overview"):
        pg.goto(base + suffix, wait_until="domcontentloaded")
        wait_until(pg, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000)
        pg.wait_for_timeout(600)

    TOTAL = "() => { try { return JSON.parse(localStorage.getItem('tw.total') || 'null'); } catch (e) { return 'bad'; } }"
    SIDE = """() => { const s = document.getElementById('side'), l = document.getElementById('evList');
        return { q: (document.getElementById('evQuota') || {}).textContent || '', open: s.classList.contains('open'), evs: l.querySelectorAll('.ev').length, lock: !!l.querySelector('#evLock .qcard'), lockTxt: (l.querySelector('#evLock .qcard') || {}).textContent || '',
          go: (l.querySelector('#evLock .qc-go') || {}).getAttribute ? l.querySelector('#evLock .qc-go').getAttribute('href') : null, veil: !!s.querySelector('.qlkov, [data-qlk]') || s.hasAttribute('data-qlk') }; }"""

    def keys(pg, who="guest"):
        t = pg.evaluate(TOTAL)
        return ((t or {}).get(who) or {}).get("events.total", []) if isinstance(t, dict) else None

    def open_drawer(pg):
        pg.click("#evToggle"); wait_until(pg, "() => document.getElementById('side').classList.contains('open')", 4000); pg.wait_for_timeout(350)
        return pg.evaluate(SIDE)

    def close_drawer(pg):
        pg.click("#evClose"); wait_until(pg, "() => !document.getElementById('side').classList.contains('open')", 4000); pg.wait_for_timeout(250)

    # ============ 訪客 1440
    c = mk("guest", GUEST)
    pg = c.new_page()
    boot(pg)
    s0 = pg.evaluate(SIDE)
    ok(f"{T}[訪客]：還沒打開過 → 累計紀錄是空的（只是載入頁面不算）、抽屜關著", not s0["open"] and pg.evaluate(TOTAL) is None, [s0, pg.evaluate(TOTAL)])
    for i in range(1, 6):
        s = open_drawer(pg)
        ok(f"{T}[訪客]：第 {i} 次按「事件」→ 抽屜打開、有事件清單（{s['evs']} 則）、累計 {i}／5、清單頂端小字寫「已用 {i}／5 次」、沒有提示卡、沒有舊的「今日已用完」遮罩",
           s["open"] and s["evs"] > 0 and not s["lock"] and f"已用 {i}／5 次" in s["q"] and len(keys(pg) or []) == i and not s["veil"], [s["evs"], s["lock"], s["veil"], keys(pg)])
        if i == 5 and shots:
            pg.screenshot(path=str(Path(shots) / "guest-5th-1440.png"))
        close_drawer(pg)
    s = open_drawer(pg)
    ok(f"{T}[訪客]：第 6 次 → 抽屜打開但**清單不在 DOM**（0 個 .ev）、換成「訪客預覽 5 次已用完」提示卡、「免費註冊」鈕連 #pricing/plan/free、累計仍 5",
       s["open"] and s["evs"] == 0 and s["lock"] and "5 次已用完" in s["lockTxt"] and s["go"] == "#pricing/plan/free" and len(keys(pg)) == 5, s)
    if shots:
        pg.screenshot(path=str(Path(shots) / "guest-6th-1440.png"))
    pg.click('#evFilters button[data-c="台股"]'); pg.wait_for_timeout(300)
    s = pg.evaluate(SIDE)
    ok(f"{T}[訪客]：已用完時點分類鈕（台股）→ 仍然沒有清單、仍是提示卡（不是換個分類就繞過）", s["evs"] == 0 and s["lock"], s)
    pg.click("#evLock .qc-go"); wait_until(pg, "() => location.hash.startsWith('#pricing')", 5000)
    ok(f"{T}[訪客]：點提示卡的「免費註冊」→ 真的到訂閱頁（{pg.evaluate('() => location.hash')}）", pg.evaluate("() => location.hash").startswith("#pricing/plan/free") or pg.evaluate("() => location.hash").startswith("#pricing"), pg.evaluate("() => location.hash"))
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => { const n = document.getElementById('evCount'); return !!n && +n.textContent > 0; }", 20000); pg.wait_for_timeout(800)
    s = pg.evaluate(SIDE)
    ok(f"{T}[訪客]：重新整理後（抽屜關著）DOM 裡就沒有事件清單、只有提示卡（累計存 localStorage，不會因重整歸零）", not s["open"] and s["evs"] == 0 and s["lock"] and len(keys(pg)) == 5, [s, keys(pg)])
    s = open_drawer(pg)
    ok(f"{T}[訪客]：重新整理後再開 → 仍是提示卡、累計仍 5（沒有再加）", s["evs"] == 0 and s["lock"] and len(keys(pg)) == 5, [s["evs"], s["lock"], keys(pg)])
    c.close()

    # ============ 註冊會員／管理者
    for who, nm in (("free", "註冊會員"), ("admin", "管理者")):
        c = mk(who, FREE)
        pg = c.new_page()
        boot(pg)
        res = []
        for i in range(1, 8):
            s = open_drawer(pg); res.append((s["evs"], s["lock"])); close_drawer(pg)
        ok(f"{T}[{nm}]：連開 7 次（超過訪客的 5 次）每次都有事件清單、沒有提示卡、沒有累計紀錄", all(e > 0 and not l for e, l in res) and pg.evaluate(TOTAL) is None, [res, pg.evaluate(TOTAL)])
        c.close()

    # ============ 預覽版示範身分
    c = mk("guest", GUEST, preview=True)
    pg = c.new_page()
    boot(pg)
    ok(f"{T}[預覽版]：不加參數 → 擁有者全開，連開 7 次都有清單", all(open_drawer(pg)["evs"] > 0 and not close_drawer(pg) for _ in range(7)) and pg.evaluate(TOTAL) is None, pg.evaluate(TOTAL))
    boot(pg, "?demo_tier=guest#overview")
    for i in range(1, 6):
        open_drawer(pg); close_drawer(pg)
    s = open_drawer(pg)
    t = pg.evaluate(TOTAL)
    ok(f"{T}[預覽版]：?demo_tier=guest → 第 6 次出提示卡、計數記在 demo:guest（不碰真實會員紀錄）", s["lock"] and s["evs"] == 0 and isinstance(t, dict) and len((t.get("demo:guest") or {}).get("events.total", [])) == 5 and "guest" not in t, [s["lock"], t])
    c.close()

    # ============ 手機 390（觸控）
    seed5 = {"guest": {"events.total": [f"o{i}" for i in range(5)]}}

    def m_open(mp):
        mp.locator("#m4Burger").tap(); wait_until(mp, "() => { const d = document.getElementById('m4Drawer'); return d && !d.hidden; }", 4000); mp.wait_for_timeout(300)
        mp.locator('#m4Drawer .m4item[data-act="events"]').tap()
        wait_until(mp, "() => document.getElementById('side').classList.contains('open')", 4000); mp.wait_for_timeout(500)
        return mp.evaluate(SIDE)

    m = mk("guest", GUEST, desk=False, vp=(390, 844))
    mp = m.new_page()
    boot(mp)
    s = m_open(mp)
    ok(f"{T}[手機390]：用手指開「事件」→ 抽屜有清單（{s['evs']} 則）、累計 1／5", s["open"] and s["evs"] > 0 and not s["lock"] and len(keys(mp) or []) >= 1, [s, keys(mp)])
    m.close()
    m = mk("guest", GUEST, desk=False, vp=(390, 844), seed=seed5)
    mp = m.new_page()
    boot(mp)
    s = m_open(mp)
    GEO = """() => { const c = document.querySelector('#evLock .qcard'), r = c ? c.getBoundingClientRect() : null;
        const fs = [...document.querySelectorAll('#evLock *')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
        const bt = document.querySelector('#evLock .qc-go'), b = bt ? bt.getBoundingClientRect() : null;
        return { l: r && Math.round(r.left), r: r && Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth, min: fs.length ? Math.min(...fs) : 0, btn: b && [Math.round(b.left), Math.round(b.right), Math.round(b.height)] }; }"""
    g = mp.evaluate(GEO)
    ok(f"{T}[手機390]：已用 5／5 → 抽屜是提示卡（沒有清單）、卡在畫面內、沒有橫向捲軸、字 ≥ 11px、按鈕高 ≥ 40",
       s["open"] and s["evs"] == 0 and s["lock"] and g["l"] >= 0 and g["r"] <= g["vw"] and g["sw"] <= 1 and g["min"] >= 11 and g["btn"] and g["btn"][2] >= 40, [s, g])
    if shots:
        mp.screenshot(path=str(Path(shots) / "guest-6th-390.png"))
    mp.evaluate("() => document.getElementById('evClose').click()"); mp.wait_for_timeout(300)
    m.close()
    # 手機總覽自己長出來的「今日事件」卡（#ovEvents）：html.m4（≤640）整張被 mobile4.css 藏掉（display:none），所以手機訪客只有抽屜一條路、不另外算；
    # 這裡驗：已用完時卡片裡也沒有新聞連結（換成提示卡）、而且看不到（沒有「看卡片不扣次」的漏洞）
    m = mk("guest", GUEST, desk=False, vp=(390, 844), seed=seed5)
    mp = m.new_page()
    boot(mp)
    card = mp.evaluate("() => { const e = document.getElementById('ovEvents'); return e ? { anchors: e.querySelectorAll('a.ev').length, lock: !!e.querySelector('#ovEvLock .qcard'), shown: e.getClientRects().length > 0 } : null; }")
    ok(f"{T}[手機390]：已用 5／5 → 總覽的今日事件卡沒有任何新聞連結（換成提示卡），而且 390 寬本來就整張藏起來（只有抽屜一條路）",
       card is not None and card["anchors"] == 0 and card["lock"] and not card["shown"], card)
    m.close()


# ★ 2026-10-16 Andy：「今日事件開放，修正，但限制次數 5 次 Total」—— 見檔頭
register("今日事件訪客5次1016", lambda pg, b, base, code: t_today_events_5(b, base, code))
