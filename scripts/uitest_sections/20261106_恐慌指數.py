# 驗收段落「恐慌指數1106」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx()、_sub_ctx()、P12_INL、OP_POP 直接可用，不要 import _uitest。
# Andy 2026-11-06：「另外需要新增恐慌指數再右上」—— 總覽摘要卡列最右邊一張「恐慌指數」（site/fearcard.js）。
# 真的操作：
#   1. 卡片排在同一排最右邊、數字是 fear.json 的值；按「?」說明打開、寫明「本站自算／非期交所官方」與門檻
#   2. 點卡片 → 完整圖真的展開（ECharts 有畫出資料點）、拖下方拉Bar 視窗真的變；按 × → 收起（節點拿掉）
#   3. 390 手機：卡片在可視寬內、整頁沒有橫向捲軸、卡片高度 ≤ 120；滑到最後一張看得到它
#   4. 功能鍵 ov.fear：註冊會員第 5 次照常、第 6 次（新分頁）完整圖反灰＋一行字；訪客第 4 次被鎖；站主種 99 次不鎖；
#      體驗中的會員被鎖後按「繼續看」→ 真的打 /v1/grants/hit、完整圖出現
import json as _t1106_json

_T1106_KEY = "ov.fear"
_T1106_NOTE = "恐慌指數完整圖今日 {n} 次已用完・Plus 以上可增加"
_T1106_CARD = "#hero .osc[data-k=\"fear\"]"


def t_fear_1106(b, base, code):
    T = "恐慌指數1106"
    errs: list = []

    def go(pg, h="#overview"):
        pg.goto(base + h, wait_until="domcontentloaded")
        wait_until(pg, f"() => !!document.querySelector('{_T1106_CARD}') && !!window.FearCard && !!FearCard._s.data", 30000)
        pg.wait_for_timeout(600)

    def open_full(pg):
        # 新會員歡迎彈窗（promo_welcome.js）會蓋住整頁：照使用者的做法按 Esc 關掉再點
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        pg.evaluate(f"() => document.querySelector('{_T1106_CARD}').scrollIntoView({{block: 'center'}})")
        pg.locator(_T1106_CARD).click(position={"x": 30, "y": 60})
        return wait_until(pg, "() => !!document.querySelector('#ovFearFull')", 6000)

    # ---------------------------------------------------------------- 1～2. 桌機 1440：位置、數字、說明、展開、拉Bar、收起
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    d = pg.evaluate(f"""() => {{ const t = document.querySelector('#ovSumTrack'), c = document.querySelector('{_T1106_CARD}');
        const ks = [...t.children].map(x => x.dataset.k); const D = FearCard._s.data || {{}};
        return {{ ks, last: t.lastElementChild === c, title: c.querySelector('.osc-t').innerText,
          tw: c.querySelector('.fz-tw b') ? c.querySelector('.fz-tw b').innerText : null, us: c.querySelector('.fz-us b') ? c.querySelector('.fz-us b').innerText : null,
          dtw: D.tw ? D.tw.value : null, dus: D.us ? D.us.value : null, foot: c.querySelector('.osc-f').innerText, tag: (c.querySelector('.osc-h .fz-tag') || {{}}).innerText,
          spark: !!c.querySelector('svg.fz-sp path') || !(D.tw && D.tw.spark && D.tw.spark.length > 1),
          h: Math.round(c.getBoundingClientRect().height), hs: [...t.children].map(x => Math.round(x.getBoundingClientRect().height)) }}; }}""")
    ok(f"{T} 卡片排在摘要卡列最右邊（第 5 張）、標題「恐慌指數」", d["ks"][-1] == "fear" and d["last"] and d["title"] == "恐慌指數" and len(d["ks"]) >= 5, d)
    fmt2 = lambda v: "—" if v is None else f"{v:.2f}"  # noqa: E731
    ok(f"{T} 主數字＝fear.json 台指自算、副數字＝美股 VIX；標題旁標「非期交所官方」；走勢線有畫", d["tw"] == fmt2(d["dtw"]) and d["us"] == fmt2(d["dus"]) and d["tag"] == "非期交所官方" and d["spark"], d)
    ok(f"{T} 五張卡同一排等高", len(set(d["hs"])) == 1, d["hs"])
    pg.locator(f"{_T1106_CARD} .howbtn").click()
    wait_until(pg, "() => { const e = document.getElementById('how-ovs-fear'); return !!e && !e.hidden && e.getClientRects().length > 0; }", 4000)
    hw = pg.evaluate("() => (document.getElementById('how-ovs-fear') || {}).innerText || ''")
    ok(f"{T} 按「?」→ 說明打開，寫明本站自算、非期交所官方、平靜／警戒／恐慌門檻與樣本數", all(s in hw for s in ("本站自算", "非期交所官方", "50%", "85%", "平靜", "恐慌", "n")), hw[:200])
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    opened = open_full(pg)
    wait_until(pg, "() => !!(window.App && App._fear && App._fear.n > 0) || !!document.querySelector('#ovFearChart .empty')", 6000)
    f = pg.evaluate("""() => { const el = document.getElementById('ovFearChart'); const ch = el && echarts.getInstanceByDom(el);
        const o = ch && ch.getOption(); return { n: o ? o.xAxis[0].data.length : 0, ser: o ? o.series.map(s => s.name) : [],
          dz: o ? [o.dataZoom[1].start, o.dataZoom[1].end] : null, exp: document.querySelector('#hero .osc[data-k="fear"]').getAttribute('aria-expanded'),
          tag: (document.querySelector('#ovFearFull .fz-tag') || {}).innerText }; }""")
    ok(f"{T} 點卡片 → 完整圖展開（有資料點、標「非期交所官方」、aria-expanded=true）", bool(opened) and f["n"] > 0 and f["tag"] == "非期交所官方" and f["exp"] == "true", f)
    # 拖拉Bar 左把手往右：可視區間真的變
    box = pg.evaluate("() => { const r = document.getElementById('ovFearChart').getBoundingClientRect(); return [r.left, r.bottom, r.width]; }")
    if f["dz"] and f["dz"][0] > 1:
        # 抓住拉Bar 上「已選區間」的中間往左拖（平移視窗）：起訖兩端都要跟著變
        sw = box[2] - 44 - 64                              # 拉Bar 寬（fearcard.js：left 44、right 64）
        hx, hy = box[0] + 44 + sw * (f["dz"][0] + f["dz"][1]) / 200, box[1] - 8 - 11
        pg.mouse.move(hx, hy)
        pg.mouse.down(); pg.mouse.move(hx - sw * 0.25, hy, steps=12); pg.mouse.up()
        pg.wait_for_timeout(400)
        dz2 = pg.evaluate("() => { const o = echarts.getInstanceByDom(document.getElementById('ovFearChart')).getOption(); return [o.dataZoom[1].start, o.dataZoom[1].end]; }")
        ok(f"{T} 拖下方拉Bar → 可視區間真的變了", dz2 != f["dz"], (f["dz"], dz2))
    pg.locator("#ovFearFull .fz-x").click(); pg.wait_for_timeout(300)
    ok(f"{T} 按 × → 完整圖收起（節點拿掉、aria-expanded=false）",
       pg.evaluate("() => !document.querySelector('#ovFearFull') && document.querySelector('#hero .osc[data-k=\"fear\"]').getAttribute('aria-expanded') === 'false'"))
    c.close()

    # ---------------------------------------------------------------- 3. 手機 390
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free", width=390, touch=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    pg.evaluate("() => { const t = document.querySelector('#ovSumTrack'); t.scrollLeft = t.scrollWidth; }"); pg.wait_for_timeout(700)
    m = pg.evaluate(f"""() => {{ const c = document.querySelector('{_T1106_CARD}').getBoundingClientRect();
        return {{ l: Math.round(c.left), r: Math.round(c.right), h: Math.round(c.height), vw: innerWidth, sw: document.documentElement.scrollWidth,
          st: (document.querySelector('{_T1106_CARD} .osc-f') || {{}}).offsetHeight || 0 }}; }}""")
    ok(f"{T} 390：滑到最後一張，恐慌指數卡整張在畫面內、整頁沒有橫向捲軸、卡高 ≤ 120、狀態那一行沒被收掉",
       m["l"] >= 0 and m["r"] <= m["vw"] and m["sw"] <= m["vw"] and m["h"] <= 120 and m["st"] > 0, m)
    opened = open_full(pg)
    mm = pg.evaluate("() => { const r = document.getElementById('ovFearFull').getBoundingClientRect(); return { w: Math.round(r.width), r: Math.round(r.right), vw: innerWidth, sw: document.documentElement.scrollWidth }; }") if opened else {}
    ok(f"{T} 390：點卡片展開完整圖，寬度不超出畫面", bool(opened) and mm.get("r", 999) <= mm.get("vw", 0) and mm.get("sw", 999) <= mm.get("vw", 0), mm)
    c.close()

    # ---------------------------------------------------------------- 4. 功能鍵 ov.fear
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    r = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, k = 'ov.fear', f = F.byId(k); const tier = (t) => P.tiers.find(x => x.key === t);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(x => x.kind === 'bool' && !x.adminOnly && x.cat !== 'grp' && !BAN.includes(x.id)).map(x => x.id);
        return { reg: f ? [f.kind, f.cat, !!f.limBy, !!f.route, !!f.qnote, !!f.metered] : null, lim: TwPerm.lim(k),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).lims[k] == null ? null : tier(t).lims[k]), feats: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats[k]), ed: ed.includes(k) }; }""")
    ok(f"{T} ov.fear 登記（bool、總覽、limBy／route／qnote、算進全站共用額度）、四方案 3／5／50／不限都開、在體驗編輯清單",
       r["reg"] == ["bool", "overview", True, True, True, True] and r["lim"] == 5 and r["lims"] == [3, 5, 50, None] and r["feats"] == [True] * 4 and r["ed"], r)
    used0 = pg.evaluate(f"() => (TwQuota.used('{_T1106_KEY}') || []).length")
    ok(f"{T} 只看卡片（沒點開）不計次", used0 == 0, used0)
    c.close()

    seed_js = ("try { if (!localStorage.getItem('t1106.init')) { localStorage.setItem('t1106.init', '1'); localStorage.setItem('tw.live.on', '0');"
               " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); const k = {};"
               " Object.entries(%s).forEach(([id, n]) => { k[id] = Array.from({length: n}, (_, i) => 'seed' + i); });"
               " localStorage.setItem('tw.quota', JSON.stringify({ day, k })); } } catch (e) {}")
    locked = f"() => !!document.querySelector('#ovFearFull > .qcov .qcard.qcnote')"

    c = _p12_ctx(b, plan="free", seed={_T1106_KEY: 4})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg); open_full(pg); pg.wait_for_timeout(900)
    a = pg.evaluate(P12_INL, "#ovFearFull")
    n5 = pg.evaluate(f"() => (TwQuota.used('{_T1106_KEY}') || []).length")
    ok(f"{T} 註冊會員第 5 次打開完整圖照常、計數 5", not a["on"] and n5 == 5, (a, n5))
    pg2 = c.new_page(); pg2.on("pageerror", lambda e: errs.append(str(e)))
    go(pg2); open_full(pg2); wait_until(pg2, locked, 8000)
    a2 = pg2.evaluate(P12_INL, "#ovFearFull")
    want = _T1106_NOTE.replace("{n}", "5")
    ok(f"{T} 註冊會員第 6 次（新分頁）完整圖反灰＋一行「{want}」、不蓋大卡、沒有彈出層、卡片照常",
       a2["on"] and want in a2["txt"] and not a2["big"] and not pg2.evaluate(OP_POP) and pg2.evaluate(f"() => !document.querySelector('{_T1106_CARD}').closest('[data-qlk]')"), a2)
    c.close()

    c = _p12_ctx(b, plan="guest", seed={_T1106_KEY: 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg); open_full(pg); wait_until(pg, locked, 8000)
    g = pg.evaluate(P12_INL, "#ovFearFull")
    ok(f"{T} 訪客用滿 3 次後第 4 次被鎖（{_T1106_NOTE.replace('{n}', '3')}）、卡片的盤後值照樣看得到",
       g["on"] and _T1106_NOTE.replace("{n}", "3") in g["txt"] and pg.evaluate(f"() => !!document.querySelector('{_T1106_CARD} .osc-n')"), g)
    c.close()

    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script(seed_js % _t1106_json.dumps({_T1106_KEY: 99}))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg); open_full(pg); pg.wait_for_timeout(900)
    o = pg.evaluate(P12_INL, "#ovFearFull")
    ok(f"{T} 站主（owner）種 99 次也不鎖、完整圖在", not o["on"] and not o["big"] and pg.evaluate("() => !!document.querySelector('#ovFearChart canvas, #ovFearChart svg, #ovFearChart .empty')"), o)
    c.close()

    # 體驗：被鎖後按「繼續看」
    now = int(__import__("time").time() * 1000)
    API = "https://fear1106.example.test"
    stt = {"left": 3, "hit": 0}

    def handle(route, _rq=None):
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
                                                     "feats": {_T1106_KEY: {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1; stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_t1106_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _t1106_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
    c.add_init_script(seed_js % _t1106_json.dumps({_T1106_KEY: 5}))
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    ag = pg.get_by_role("button", name="同意並繼續")
    if ag.count() and ag.first.is_visible():
        ag.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, f"() => !!document.querySelector('{_T1106_CARD}') && !!window.FearCard && !!FearCard._s.data && window.TwGrants && TwGrants.left('{_T1106_KEY}') === 3", 30000)
    open_full(pg)
    wait_until(pg, "() => !!document.querySelector('#ovFearFull .qc-try')", 8000)
    btn = pg.locator("#ovFearFull .qc-try")
    ok(f"{T} 體驗中的註冊會員用完 5 次後，完整圖原位置多一顆「繼續看」、體驗剩 3 次", btn.count() == 1, pg.evaluate("() => ((document.querySelector('#ovFearFull') || {}).innerText || '').slice(0, 200)"))
    if btn.count():
        with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
            btn.first.click()
        hj = ri.value.json()
        ok(f"{T} 按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
        shown = wait_until(pg, "() => { const e = document.querySelector('#ovFearFull'); return !!e && !e.hasAttribute('data-qlk') && !e.querySelector(':scope > .qcov'); }", 6000)
        ok(f"{T} 扣完完整圖真的出現（鎖與一行字拿掉）", bool(shown))
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("恐慌指數1106", lambda pg, b, base, code: t_fear_1106(b, base, code))
