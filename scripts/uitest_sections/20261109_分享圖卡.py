# 驗收段落「分享圖卡1109」—— P-1107-05 一鍵分享圖卡（site/sharecard.js）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_p12_ctx()、_sub_ctx()、OP_POP 直接可用。
# 真的操作：點標題列「分享圖卡」鈕 → 視窗產生圖卡 → 切尺寸 → 下載（攔下載檔、讀 PNG 檔頭量真實尺寸）；
# 手機攔 navigator.share 呼叫；?src=card 進站被記成來源；用到上限被鎖、站主不受限；
# 版型每個元素外框兩兩不相交、不出界（含超長標題的壓力測試）；深色主題也能輸出；390 寬不橫向捲動。
import json as _sc_json
import struct as _sc_struct

_SC_URL = "https://liguligu-puipui.com/?src=card"


def _sc_png_size(path):
    with open(path, "rb") as f:
        h = f.read(24)
    if h[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return _sc_struct.unpack(">II", h[16:24])


def t_sharecard_1109(b, base, code):
    T = "分享圖卡1109"
    errs: list = []
    import tempfile as _tf

    def go(pg, h, wait=None, t=25000):
        if pg.url == "about:blank":
            pg.goto(base + h, wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        else:
            pg.evaluate(f"() => {{ location.hash = '{h}'; }}")
        if wait:
            wait_until(pg, wait, t)
        pg.wait_for_timeout(700)

    def agree(pg):
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click(); pg.wait_for_timeout(300)

    def to_fear(pg):
        """總覽最底下的恐慌指數走勢：捲過去它才建圖，按鈕要等圖畫好才出現"""
        pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        wait_until(pg, "() => !!document.querySelector('.scBtn[data-sct=\"ov-fear\"]')", 25000)
        pg.locator('.scBtn[data-sct="ov-fear"]').first.scroll_into_view_if_needed()

    used = lambda pg: pg.evaluate("() => (TwQuota.used('share.card') || []).length")  # noqa: E731
    rep = lambda pg: pg.evaluate("() => TwShareCard.last")  # noqa: E731

    def layout_ok(r):
        return r and r["overlaps"] == [] and r["outside"] == [] and len(r["boxes"]) >= 5

    # ------------------------------------------------------------ 0. 登記：功能鍵、四個方案、體驗編輯器、公告
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#overview")
    d = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, keys = ['share.card', 'share.card.plus'];
        const tier = (k) => P.tiers.find(t => t.key === k);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(f => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && !BAN.includes(f.id)).map(f => f.id);
        const f1 = F.byId('share.card');
        return { reg: keys.map(k => !!F.byId(k)), kind: f1 && [f1.kind, f1.cat, !!f1.limBy, !!f1.qspent, !!f1.qbtn],
          free: [TwPerm.lim('share.card'), TwPerm.can('share.card'), TwPerm.can('share.card.plus')],
          lims: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).lims['share.card'] == null ? null : tier(t).lims['share.card']),
          feats: ['guest', 'free', 'plus', 'pro'].map(t => keys.map(k => tier(t).feats[k])),
          inEditor: keys.map(k => ed.includes(k)) }; }""")
    ok(f"{T} 兩個功能鍵都登記了（share.card 有 limBy／qspent／qbtn）", all(d["reg"]) and d["kind"] == ["bool", "global", True, True, True], d)
    ok(f"{T} 註冊會員範本沒寫時：每日 5 次、可用、Plus 功能關著", d["free"] == [5, True, False], d["free"])
    ok(f"{T} plan_presets.js：share.card 訪客 3／註冊會員 5／Plus 50／Pro 不限，四個方案都開；share.card.plus 只有 Plus、Pro 開",
       d["lims"] == [3, 5, 50, None] and d["feats"] == [[True, False], [True, False], [True, True], [True, True]], (d["lims"], d["feats"]))
    ok(f"{T} 「編輯：新會員體驗」清單列得到兩個鍵（不在法遵禁止清單）", all(d["inEditor"]), d["inEditor"])
    notes = _sc_json.load(open(str(SITE / "notices" / "features.json"), encoding="utf-8"))
    nt = [n for n in notes if n.get("id") == "f-20261109-share-card"]
    ok(f"{T} 同一個 commit 有「功能更新」公告（f-20261109-share-card、給所有人、有站內連結）", len(nt) == 1 and nt[0]["aud"] == "all" and "](#overview)" in nt[0]["body"], nt[:1])
    c.close()

    # ------------------------------------------------------------ 1. 註冊會員（桌機）：真的按、真的產生、真的下載
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#overview"); agree(pg)
    to_fear(pg)
    ok(f"{T} 恐慌指數走勢標題列有「分享圖卡」鈕、字級 ≥ 11px、可見", pg.evaluate(
        "() => { const b = document.querySelector('.scBtn[data-sct=\"ov-fear\"]'); const s = b.querySelector('span'); return !!b && b.getClientRects().length > 0 && parseFloat(getComputedStyle(s).fontSize) >= 11 && s.textContent === '分享圖卡'; }"))
    ok(f"{T} 按之前：沒有視窗、次數 0", not pg.evaluate("() => !!document.querySelector('.scDlg')") and used(pg) == 0)
    pg.locator('.scBtn[data-sct="ov-fear"]').first.click()
    wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
    r = rep(pg)
    ok(f"{T} 視窗出現、圖卡預覽 canvas 畫好、次數 +1", pg.evaluate("() => !!document.querySelector('.scDlg .scCv')") and used(pg) == 1, used(pg))
    ok(f"{T} 恐慌指數圖是寬扁的 → 預設橫式 1200×630", r["size"] == "land" and (r["W"], r["H"]) == (1200, 630), r)
    ok(f"{T} 圖卡標題寫「恐慌指數走勢・台股」、日期列有「資料日期 yyyy-mm-dd・僅供研究參考」",
       r["title"] == "恐慌指數走勢・台股" and bool(re.match(r"^資料日期 \d{4}-\d{2}-\d{2}・僅供研究參考$", r["date"])), (r["title"], r["date"]))
    ok(f"{T} ★ 圖上網址文字＝{_SC_URL}#overview（含 src=card、該頁路由）", r["url"] == _SC_URL + "#overview" and any(x["name"] == "footerUrl" for x in r["boxes"]), r["url"])
    ok(f"{T} ★ 版型：標題／日期／圖例／圖／角標／頁尾 外框兩兩不相交、不出界（重疊檢查 {len(r['boxes'])} 個元素 0 筆）", layout_ok(r) and any(x["name"] == "legend" for x in r["boxes"]) and r["badge"], r)
    ok(f"{T} 註冊會員圖卡帶右上角標；方形、限動直式鈕是反灰的（Plus 以上）",
       pg.evaluate("() => [...document.querySelectorAll('.scSz button')].map(b => b.dataset.sz + ':' + b.disabled).join()") == "portrait:false,land:false,square:true,story:true")
    ok(f"{T} 圖卡裡沒有比比（沒有圖片元素、圖例以外只有文字與圖）", not pg.evaluate("() => !!document.querySelector('.scDlg img')"))
    # 切到直式：真的重畫、尺寸變、不再扣次數
    pg.locator('.scSz button[data-sz="portrait"]').click()
    wait_until(pg, "() => TwShareCard.last && TwShareCard.last.size === 'portrait'", 6000)
    r2 = rep(pg)
    ok(f"{T} 切到直式：1080×1350、版型照樣不重疊、次數仍是 1（切尺寸不重算）", (r2["W"], r2["H"]) == (1080, 1350) and layout_ok(r2) and used(pg) == 1, (r2["W"], r2["H"], used(pg)))
    # 下載
    with pg.expect_download(timeout=8000) as di:
        pg.locator('.scGo').click()
    dl = di.value
    path = dl.path()
    sz = _sc_png_size(path)
    ok(f"{T} ★ 下載到真的 PNG 檔：檔名 .png、檔頭尺寸 1080×1350", dl.suggested_filename.endswith(".png") and sz == (1080, 1350), (dl.suggested_filename, sz))
    ok(f"{T} 下載後次數仍是 1", used(pg) == 1)
    pg.locator('.scSz button[data-sz="land"]').click()
    wait_until(pg, "() => TwShareCard.last && TwShareCard.last.size === 'land'", 6000)
    with pg.expect_download(timeout=8000) as di:
        pg.locator('.scGo').click()
    ok(f"{T} 橫式下載：PNG 檔頭 1200×630", _sc_png_size(di.value.path()) == (1200, 630))
    # 關閉：Esc、焦點回到按鈕
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    ok(f"{T} Esc 關視窗、焦點回到「分享圖卡」鈕", not pg.evaluate("() => !!document.querySelector('.scDlg')") and pg.evaluate("() => document.activeElement && document.activeElement.classList.contains('scBtn')"))
    # 壓力測試：超長標題縮字放進一行、不跟角標重疊
    st = pg.evaluate("""async () => { const t = { id: 'x', fig: '#ovFearFull', title: () => '很長的標題'.repeat(14), legend: () => [{ c: '#c00', text: '一二三四五六七八九十'.repeat(3) }, { c: '#00c', text: 'abcdefghij'.repeat(4) }] };
        const out = {}; for (const k of Object.keys(TwShareCard.sizes)) { const r = (await TwShareCard.compose(t, k)).rep; out[k] = [r.overlaps, r.outside, r.boxes.length]; } return out; }""")
    ok(f"{T} 壓力測試：超長標題＋超長圖例，四種尺寸都 0 重疊、0 出界", all(v[0] == [] and v[1] == [] for v in st.values()), st)
    # 其他頁的圖：資金流向輪盤、總覽輪動與分流樹、產業地圖族群漲跌幅
    for hsh, sct, nm in [("#flow", "flow-rot", "資金流向輪盤"), ("#industry/industry", "grp", "產業地圖族群漲跌幅")]:
        go(pg, hsh, f"() => !!document.querySelector('.scBtn[data-sct=\"{sct}\"]')", 25000)
        has = pg.locator(f'.scBtn[data-sct="{sct}"]').count() == 1
        ok(f"{T} {nm}：標題列有「分享圖卡」鈕", has)
        if has:
            pg.locator(f'.scBtn[data-sct="{sct}"]').first.click()
            wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
            rr_ = rep(pg)
            ok(f"{T} {nm}：產生圖卡、網址帶該頁路由（{hsh}）、0 重疊、圖有畫進去（figN ≥ 1）", rr_["url"].startswith(_SC_URL + hsh) and layout_ok(rr_) and rr_["figN"] >= 1, (rr_["url"], rr_["overlaps"], rr_["figN"]))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
    go(pg, "#overview")
    pg.wait_for_timeout(800)
    for sct, nm in [("ov-rot", "總覽強弱輪動"), ("ov-flow", "總覽昨日資金分流樹")]:
        wait_until(pg, f"() => !!document.querySelector('.scBtn[data-sct=\"{sct}\"]')", 20000)
        has = pg.locator(f'.scBtn[data-sct="{sct}"]').count() == 1
        ok(f"{T} {nm}：標題列有「分享圖卡」鈕", has)
        if has:
            pg.locator(f'.scBtn[data-sct="{sct}"]').first.scroll_into_view_if_needed()
            pg.locator(f'.scBtn[data-sct="{sct}"]').first.click()
            wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
            rr_ = rep(pg)
            ok(f"{T} {nm}：產生圖卡、0 重疊、圖有畫進去", layout_ok(rr_) and rr_["figN"] >= 1, (rr_["overlaps"], rr_["figN"]))
            pg.keyboard.press("Escape"); pg.wait_for_timeout(150)
    ok(f"{T} 全部操作完用掉的次數＝按過的次數（恐慌1＋輪盤1＋族群1＋輪動1＋分流樹1＝5）", used(pg) == 5, used(pg))
    # 5 次用完 → 第 6 次被鎖：按鈕反灰、旁邊一行字、點了沒視窗
    pg.evaluate("() => { window.scrollTo(0, 0); }")
    wait_until(pg, "() => { const v = [...document.querySelectorAll('.scBtn')].filter(b => b.getClientRects().length > 0); return v.length > 0 && v.every(b => b.hasAttribute('data-qnote')); }", 8000)
    locked = pg.evaluate("""() => { const bs = [...document.querySelectorAll('.scBtn')].filter(b => b.getClientRects().length > 0);
        const n = [...document.querySelectorAll('span.qnote[data-f="share.card"]')].find(x => x.getClientRects().length > 0);
        return { n: bs.length, op: bs.map(b => +getComputedStyle(b).opacity), note: n ? n.textContent : '' }; }""")
    ok(f"{T} ★ 註冊會員用完 5 張：旁邊一行「今日 5 張圖卡已用完・Plus 以上可增加」", "今日 5 張圖卡已用完・Plus 以上可增加" in locked["note"], locked)
    vb = pg.locator(".scBtn:visible").first
    vb.click(force=True); pg.wait_for_timeout(500)
    ok(f"{T} ★ 用完後按鈕反灰、點了不開視窗、不跳升級卡、次數不再增加", locked["op"] and max(locked["op"]) < 1 and not pg.evaluate("() => !!document.querySelector('.scDlg')") and not pg.evaluate(OP_POP) and used(pg) == 5, (locked, used(pg)))
    c.close()

    # ------------------------------------------------------------ 2. 訪客：3 張，第 4 張被鎖
    c = _p12_ctx(b, plan="guest", seed={"share.card": 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#overview"); agree(pg)
    to_fear(pg)
    pg.wait_for_timeout(800)
    g = pg.evaluate("""() => { const b = document.querySelector('.scBtn[data-sct="ov-fear"]'); const n = [...document.querySelectorAll('span.qnote[data-f="share.card"]')].find(x => x.getClientRects().length > 0);
        return { op: +getComputedStyle(b).opacity, note: n ? n.textContent : '' }; }""")
    pg.locator('.scBtn[data-sct="ov-fear"]').first.click(force=True); pg.wait_for_timeout(500)
    ok(f"{T} ★ 訪客用滿 3 張後第 4 張被鎖（今日 3 張圖卡已用完）、按了不開視窗", "今日 3 張圖卡已用完" in g["note"] and not pg.evaluate("() => !!document.querySelector('.scDlg')"), g)
    c.close()

    # ------------------------------------------------------------ 3. 站主：種 99 次也不鎖
    c, sent, stt = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script("try { if (!localStorage.getItem('sc1109.init')) { localStorage.setItem('sc1109.init', '1'); localStorage.setItem('tw.live.on', '0');"
                      " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      " localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'share.card': Array.from({length: 99}, (_, i) => 'seed' + i) } })); } } catch (e) {}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#overview"); agree(pg)
    to_fear(pg)
    pg.locator('.scBtn[data-sct="ov-fear"]').first.click()
    wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
    ok(f"{T} ★ 站主（owner）種 99 次也不鎖：照常產生圖卡、不帶角標、四種尺寸都能選",
       pg.evaluate("() => !!document.querySelector('.scDlg .scCv')") and rep(pg)["badge"] is False
       and pg.evaluate("() => [...document.querySelectorAll('.scSz button')].every(b => !b.disabled)"), rep(pg))
    pg.locator('.scSz button[data-sz="story"]').click()
    wait_until(pg, "() => TwShareCard.last && TwShareCard.last.size === 'story'", 6000)
    with pg.expect_download(timeout=8000) as di:
        pg.locator('.scGo').click()
    ok(f"{T} Plus 以上限動直式：下載 PNG 檔頭 1080×1920、0 重疊", _sc_png_size(di.value.path()) == (1080, 1920) and layout_ok(rep(pg)))
    pg.locator('.scSz button[data-sz="square"]').click()
    wait_until(pg, "() => TwShareCard.last && TwShareCard.last.size === 'square'", 6000)
    r3 = rep(pg)
    ok(f"{T} Plus 以上 IG 方形：1080×1080、0 重疊", (r3["W"], r3["H"]) == (1080, 1080) and layout_ok(r3), r3)
    c.close()


    # ------------------------------------------------------------ 3b. 體驗：註冊會員用完 5 張、有體驗額度 → 按鈕不反灰成死的，按下去跳體驗卡，「繼續」才扣體驗、圖卡才產生
    now = int(__import__("time").time() * 1000)
    API = "https://sharecard1109.example.test"
    stt = {"left": 3, "hit": 0}

    def handle(route):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": "new@example.com", "name": "新會員", "admin": False, "owner": False}}
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {}, "lims": {}, "dq": None}
        elif path == "/v1/grants/public":
            out = {"now": now, "promo": [], "welcome": []}
        elif path == "/v1/grants/me":
            out = {"now": now, "today": {}, "grants": [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": now, "end": now + 14 * 86400000 - 1000, "per": "day",
                                                     "feats": {"share.card": {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1
            stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_sc_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _sc_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test');localStorage.setItem('tw.live.on','0');"
                      "const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      "localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'share.card': Array.from({length: 5}, (_, i) => 'seed' + i) } }))}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    agree(pg)
    wait_until(pg, "() => window.TwGrants && TwGrants.left('share.card') === 3", 30000)
    to_fear(pg)
    wait_until(pg, "() => document.querySelector('.scBtn[data-sct=\"ov-fear\"]').hasAttribute('data-qnote')", 8000)
    pg.locator('.scBtn[data-sct="ov-fear"]').first.click(force=True)
    wait_until(pg, "() => !!window.TwGrants && !!TwGrants.extra('share.card') && TwQuota.out('share.card')", 8000)
    pg.locator('.scBtn[data-sct="ov-fear"]').first.click(force=True)
    modal = wait_until(pg, "() => { const m = document.getElementById('qcModal'); return !!m && !m.hidden && m.getClientRects().length > 0; }", 6000)
    if not modal:
        pg.locator('.scBtn[data-sct="ov-fear"]').first.click(force=True)
        modal = wait_until(pg, "() => { const m = document.getElementById('qcModal'); return !!m && !m.hidden && m.getClientRects().length > 0; }", 6000)
    ok(f"{T} ★ 體驗中的註冊會員用完 5 張後按「分享圖卡」：跳出體驗卡（剩 3 次），圖卡視窗還沒開", bool(modal) and not pg.evaluate("() => !!document.querySelector('.scDlg')") and stt["hit"] == 0, (modal, stt))
    if modal:
        tb = pg.locator("#qcModal .qc-try, #qcModal button:has-text('繼續')")
        ok(f"{T} 體驗卡上有「繼續」鈕", tb.count() >= 1)
        if tb.count():
            with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
                tb.first.click()
            hj = ri.value.json()
            ok(f"{T} ★ 按「繼續」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
            opened = wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
            ok(f"{T} ★ 扣完體驗圖卡視窗真的開了、圖卡畫好、0 重疊、本機體驗剩 2 次", bool(opened) and layout_ok(rep(pg)) and pg.evaluate("() => TwGrants.left('share.card')") == 2, (opened, pg.evaluate("() => TwGrants.left('share.card')")))
    c.close()

    # ------------------------------------------------------------ 4. 深色主題也能輸出
    c = _p12_ctx(b, plan="free")
    c.add_init_script("try { localStorage.setItem('tw.themeOv', JSON.stringify({ mode: 'dark', until: Date.now() + 9e9 })); localStorage.setItem('tw.theme', 'dark'); } catch (e) {}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#flow", "() => !!document.querySelector('.scBtn[data-sct=\"flow-rot\"]')", 25000); agree(pg)
    dk = pg.evaluate("() => document.documentElement.getAttribute('data-theme')")
    pg.locator('.scBtn[data-sct="flow-rot"]').first.click()
    wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
    rd = rep(pg)
    ok(f"{T} 深色主題：照樣能輸出（theme={rd['theme']}）、0 重疊", dk != "light" and rd["theme"] == "dark" and layout_ok(rd), (dk, rd["theme"]))
    c.close()

    # ------------------------------------------------------------ 5. 手機 390：不橫向捲動、navigator.share 帶檔案、不支援就下載
    for mode in ("share", "noshare"):
        c = _p12_ctx(b, plan="free", width=390, touch=True)
        if mode == "share":
            c.add_init_script("""window.__shared = null;
              Object.defineProperty(navigator, 'canShare', { value: (d) => !!(d && d.files && d.files.length), configurable: true });
              Object.defineProperty(navigator, 'share', { value: async (d) => { window.__shared = { n: d.files.length, type: d.files[0].type, name: d.files[0].name, size: d.files[0].size, url: d.url || '' }; }, configurable: true });""")
        else:
            c.add_init_script("try { Object.defineProperty(navigator, 'canShare', { value: undefined, configurable: true }); Object.defineProperty(navigator, 'share', { value: undefined, configurable: true }); } catch (e) {}")
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        go(pg, "#overview"); agree(pg)
        to_fear(pg)
        has = pg.locator('.scBtn[data-sct="ov-fear"]').count() == 1
        ok(f"{T} 手機（{mode}）：恐慌指數走勢標題列有「分享圖卡」鈕、可點（高 ≥ 28）", has and pg.evaluate("() => document.querySelector('.scBtn[data-sct=\"ov-fear\"]').getBoundingClientRect().height >= 28"))
        pg.locator('.scBtn[data-sct="ov-fear"]').first.click()
        wait_until(pg, "() => !!document.querySelector('.scDlg .scCv')", 8000)
        geo = pg.evaluate("""() => { const d = document.querySelector('.scBox').getBoundingClientRect(), de = document.documentElement;
            const fs = [...document.querySelectorAll('.scDlg button, .scDlg .scNote')].map(e => parseFloat(getComputedStyle(e).fontSize));
            return { over: de.scrollWidth > de.clientWidth, left: d.left, right: d.right, vw: innerWidth, minfs: Math.min(...fs),
                     go: [...document.querySelectorAll('.scAct .btn')].map(b => b.textContent.trim() + ':' + Math.round(b.getBoundingClientRect().height)) }; }""")
        ok(f"{T} 手機（{mode}）：視窗在 390 內、不橫向捲動、字 ≥ 11px、按鈕高 ≥ 40", not geo["over"] and geo["left"] >= 0 and geo["right"] <= geo["vw"] + 0.5 and geo["minfs"] >= 11
           and all(int(x.split(":")[1]) >= 40 for x in geo["go"][:1]), geo)
        r5 = rep(pg)
        ok(f"{T} 手機（{mode}）：0 重疊", layout_ok(r5), r5["overlaps"])
        if mode == "share":
            ok(f"{T} 手機：有「分享圖片」主鈕（支援 navigator.share 帶檔案）", pg.evaluate("() => document.querySelector('.scGo').dataset.go") == "share")
            pg.locator('.scGo').click(); pg.wait_for_timeout(600)
            sh = pg.evaluate("() => window.__shared")
            ok(f"{T} ★ 手機按「分享圖片」→ 真的呼叫 navigator.share，帶 1 個 PNG 檔、檔名正確、網址帶 src=card",
               bool(sh) and sh["n"] == 1 and sh["type"] == "image/png" and sh["name"].endswith(".png") and sh["size"] > 2000 and "src=card" in sh["url"], sh)
        else:
            ok(f"{T} 手機不支援分享檔案：主鈕直接是「下載 PNG」", pg.evaluate("() => document.querySelector('.scGo').dataset.go") == "save")
            with pg.expect_download(timeout=8000) as di:
                pg.locator('.scGo').click()
            ok(f"{T} 手機（不支援分享）：下載到 PNG", (_sc_png_size(di.value.path()) or (0, 0))[0] in (1080, 1200), _sc_png_size(di.value.path()))
        c.close()

    # ------------------------------------------------------------ 6. 流量：?src=card 進站 → 第一次來源記成 card
    c = _p12_ctx(b, plan="guest")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "?src=card#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwSrc", 10000)
    pg.wait_for_timeout(600)
    sv = pg.evaluate("() => ({ get: TwSrc.get(), ls: localStorage.getItem('tw.src'), parse: TwSrc.parse() })")
    ok(f"{T} ★ 圖卡網址 ?src=card 進站：第一次來源記成 card（medium＝share）、存進 localStorage", sv["get"] and sv["get"]["s"] == "card" and sv["get"].get("m") == "share" and "card" in (sv["ls"] or ""), sv)
    ok(f"{T} 路由照常（hash 仍是 #overview、總覽有畫出來）", pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => !!document.querySelector('#v-overview.on, #v-overview')"))
    c.close()
    c = _p12_ctx(b, plan="guest")
    pg = c.new_page()
    pg.goto(base + "?src=evil#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwSrc", 10000); pg.wait_for_timeout(300)
    ok(f"{T} 只認 src=card，其他 ?src= 值不當來源", not pg.evaluate("() => TwSrc.parse()") or pg.evaluate("() => TwSrc.parse().s") != "evil")
    c.close()

    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("分享圖卡1109", lambda pg, b, base, code: t_sharecard_1109(b, base, code))
