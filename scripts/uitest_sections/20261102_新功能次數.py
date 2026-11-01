# 驗收段落「新功能次數1102」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx()、_sub_ctx()、OP_POP 直接可用，不要 import _uitest。
# Andy 2026-11-02：「信用交易、期貨籌碼是新加入的功能，以後只要有新加入功能都需要限制使用次數在權限那邊進行設定，這次也是，但體驗就 Follow 我設定的次數」。
# 三個新鍵：mkt.credit（#market/credit）、mkt.fut（#market/fut）、mkt.inst.day（#market/inst 的當天報告）。
# 真的操作：註冊會員第 5 次進來照常、第 6 次（新分頁）內容反灰＋一行字；訪客第 4 次被鎖；站主種再多次也不鎖；
# 有體驗額度的註冊會員被鎖後按「繼續看」→ 真的打 /v1/grants/hit → 內容出現；管理區「編輯：新會員體驗」清單列得到這三個鍵。
import json as _t1102_json
import pathlib as _t1102_pl

_T1102_CASES = [
    # (功能鍵, 網址, 被蓋的區塊, 等內容出現, 一行字)
    ("mkt.credit", "#market/credit", "#mktBody", "() => !!document.querySelector('#mf-credit')", "信用交易今日 {n} 次已用完・Plus 以上可增加"),
    ("mkt.fut", "#market/fut", "#mktBody", "() => !!document.querySelector('#mktBody .fp-bar')", "期貨籌碼今日 {n} 次已用完・Plus 以上可增加"),
    ("mkt.inst.day", "#market/inst", "#instToday", "() => !!document.querySelector('#instToday')", "三大法人當天報告今日 {n} 次已用完・Plus 以上可增加"),
]


def t_featkeys_1102(b, base, code):
    T = "新功能次數1102"
    errs: list = []
    sh = os.environ.get("TW_FEATKEYS_SHOTS")
    if sh:
        _t1102_pl.Path(sh).mkdir(parents=True, exist_ok=True)

    def shot(pg, name):
        if not sh:
            return
        try:
            pg.screenshot(path=str(_t1102_pl.Path(sh) / name))
        except Exception as ex:  # noqa: BLE001
            print("  截圖失敗", name, ex)

    def go(pg, h, wait=None, t=20000):
        if pg.url == "about:blank":
            pg.goto(base + h, wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        else:
            pg.evaluate(f"() => {{ location.hash = '{h}'; }}")
        if wait:
            wait_until(pg, wait, t)
        pg.wait_for_timeout(900)

    used = lambda pg, k: pg.evaluate(f"() => (TwQuota.used('{k}') || []).length")  # noqa: E731
    pop = lambda pg: pg.evaluate(OP_POP)  # noqa: E731
    seed_js = ("try { if (!localStorage.getItem('t1102.init')) { localStorage.setItem('t1102.init', '1'); localStorage.setItem('tw.live.on', '0');"
               " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); const k = {};"
               " Object.entries(%s).forEach(([id, n]) => { k[id] = Array.from({length: n}, (_, i) => 'seed' + i); });"
               " localStorage.setItem('tw.quota', JSON.stringify({ day, k })); } } catch (e) {}")

    # ---------------------------------------------------------------- 0. 功能鍵登記、範本、體驗編輯器
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg, "#overview")
    d = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, keys = ['mkt.credit', 'mkt.fut', 'mkt.inst.day'];
        const tier = (k) => P.tiers.find(t => t.key === k);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(f => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && !BAN.includes(f.id)).map(f => f.id);
        return { reg: keys.map(k => { const f = F.byId(k); return f ? [f.kind, f.cat, !!f.limBy, !!f.route, !!f.qnote, !!f.metered] : null; }),
          free: keys.map(k => TwPerm.lim(k)), can: keys.map(k => TwPerm.can(k)),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => keys.map(k => tier(t).lims[k] == null ? null : tier(t).lims[k])),
          feats: ['guest', 'free', 'plus', 'pro'].map(t => keys.map(k => tier(t).feats[k])),
          inEditor: keys.map(k => ed.includes(k)), sub: [F.bySub('mkt-credit'), F.bySub('mkt-fut'), F.bySub('flow-conc')] }; }""")
    ok(f"{T} 三個鍵都登記了（bool、市場明細、有 limBy／route／qnote、算進全站共用額度）", all(r == ["bool", "market", True, True, True, True] for r in d["reg"]), d["reg"])
    ok(f"{T} 註冊會員範本沒寫時：三項每日 5 次、開關是開的", d["free"] == [5, 5, 5] and d["can"] == [True] * 3, (d["free"], d["can"]))
    ok(f"{T} plan_presets.js：訪客 3／註冊會員 5／Plus 50／Pro 不限（不寫）、四個方案都開",
       d["lims"] == [[3] * 3, [5] * 3, [50] * 3, [None] * 3] and all(v == [True] * 3 for v in d["feats"]), (d["lims"], d["feats"]))
    ok(f"{T} 「編輯：新會員體驗」清單列得到這三個鍵（不在法遵禁止清單）", all(d["inEditor"]), d["inEditor"])
    ok(f"{T} 側欄／手機子分頁代號：信用交易、期貨籌碼、集中度各掛到自己的鍵", d["sub"] == [["mkt.credit"], ["mkt.fut"], ["flow.conc"]], d["sub"])
    c.close()

    for key, hsh, sel, ready, note in [x for x in _T1102_CASES if not os.environ.get('TW_T1102_KEY') or x[0] == os.environ.get('TW_T1102_KEY')]:
        nm = note.split("今日")[0]
        # ------------------------------------------------------------ 註冊會員：第 5 次照常、第 6 次（新分頁）被鎖
        c = _p12_ctx(b, plan="free", seed={key: 4})
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        go(pg, hsh, ready)
        a = pg.evaluate(P12_INL, sel)
        ok(f"{T} {nm}：註冊會員第 5 次進來內容照常、計數 5", not a["on"] and not a["big"] and used(pg, key) == 5, (a, used(pg, key)))
        pg2 = c.new_page(); pg2.on("pageerror", lambda e: errs.append(str(e)))
        go(pg2, hsh, f"() => !!document.querySelector('{sel} > .qcov .qcard.qcnote') && ({ready})()", 25000)
        a2 = pg2.evaluate(P12_INL, sel)
        want = note.replace("{n}", "5")
        ok(f"{T} {nm}：註冊會員第 6 次（新分頁）內容反灰＋一行「{want}」、不蓋大卡、沒有彈出層、點不動",
           a2["on"] and want in a2["txt"] and not a2["big"] and not pop(pg2)
           and pg2.evaluate(f"() => {{ const k = [...document.querySelector('{sel}').children].find(x => !x.classList.contains('qcov')); return !!k && getComputedStyle(k).pointerEvents === 'none'; }}"), a2)
        shot(pg2, f"free_{key}.png")
        # 三大法人：被鎖的只有「當天報告」，上面的「當天／連買賣」切換列照樣能按（切去連買賣 ＝ 另一個鍵）
        if key == "mkt.inst.day":
            sw = pg2.evaluate("() => { const b = document.querySelector('#instView button[data-v=\"streak\"]'); return !!b && !b.closest('.qcov') && getComputedStyle(b).pointerEvents !== 'none'; }")
            ok(f"{T} {nm}：用完之後切換列（當天／連買賣）沒被一起蓋住", bool(sw))
        c.close()

        # ------------------------------------------------------------ 訪客：3 次
        c = _p12_ctx(b, plan="guest", seed={key: 3})
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        go(pg, hsh, f"() => !!document.querySelector('{sel} > .qcov .qcard.qcnote') && ({ready})()", 25000)
        g = pg.evaluate(P12_INL, sel)
        ok(f"{T} {nm}：訪客用滿 3 次後第 4 次被鎖（{note.replace('{n}', '3')}）", g["on"] and note.replace("{n}", "3") in g["txt"] and not pop(pg), (g, pg.evaluate(f"() => ({{ qlk: document.querySelector('{sel}').getAttribute('data-qlk'), perm: TwPerm.lim('{key}'), used: (TwQuota.used('{key}')||[]).length, h: location.hash, html: document.querySelector('{sel}').innerHTML.slice(0, 300) }})")))
        shot(pg, f"guest_{key}.png")
        c.close()

        # ------------------------------------------------------------ 站主：種 99 次也不鎖
        c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
        c.add_init_script(seed_js % _t1102_json.dumps({key: 99}))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        go(pg, hsh, ready)
        o = pg.evaluate(P12_INL, sel)
        ok(f"{T} {nm}：站主（owner）種 99 次也不鎖、內容在", not o["on"] and not o["big"] and pg.evaluate(f"() => !!document.querySelector('{sel}')"), o)
        c.close()

    # ---------------------------------------------------------------- 體驗：被鎖後按「繼續看」
    now = int(__import__("time").time() * 1000)
    API = "https://featkeys1102.example.test"
    for key, hsh, sel, ready, note in [x for x in _T1102_CASES if not os.environ.get('TW_T1102_KEY') or x[0] == os.environ.get('TW_T1102_KEY')]:
        nm = note.split("今日")[0]
        stt = {"left": 3, "hit": 0}

        def handle(route, _rq=None, stt=stt, key=key):
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
                                                         "feats": {key: {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
            elif path == "/v1/grants/hit":
                stt["hit"] += 1
                stt["left"] -= 1
                out = {"ok": True, "gid": "welcome", "left": stt["left"]}
            elif path == "/v1/plans/public":
                out = {"plans": []}
            route.fulfill(status=200, body=_t1102_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

        c = b.new_context(viewport={"width": 1440, "height": 900})
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _t1102_json.dumps({"api": API}) + ";"
                          "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
        c.add_init_script(seed_js % _t1102_json.dumps({key: 5}))
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
        c.route(API + "/**", handle)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + hsh, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click(); pg.wait_for_timeout(300)
        wait_until(pg, f"() => window.TwGrants && TwGrants.left('{key}') === 3 && !!document.querySelector('{sel} .qc-try') && ({ready})()", 30000)
        pg.wait_for_timeout(500)
        btn = pg.locator(f"{sel} .qc-try")
        ok(f"{T} {nm}：體驗中的註冊會員用完 5 次後，鎖住的原位置多一顆「繼續看」、體驗剩 3 次", btn.count() == 1 and pg.evaluate(f"() => TwGrants.left('{key}')") == 3,
           pg.evaluate(f"() => ({{ qlk: (document.querySelector('{sel}') || {{}}).getAttribute && document.querySelector('{sel}').getAttribute('data-qlk'), left: window.TwGrants && TwGrants.left('{key}'), lim: TwPerm.lim('{key}'), used: (TwQuota.used('{key}')||[]).length, src: TwPerm.state().src, who: TwPerm.state().who, qcov: ((document.querySelector('{sel} > .qcov')||{{}}).innerText||'').slice(0,200) }})"))
        shot(pg, f"grant_before_{key}.png")
        if btn.count():
            with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
                btn.first.click()
            hj = ri.value.json()
            ok(f"{T} {nm}：按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
            opened = wait_until(pg, f"() => {{ const e = document.querySelector('{sel}'); return !!e && !e.hasAttribute('data-qlk') && !e.querySelector(':scope > .qcov') && e.getClientRects().length > 0; }}", 6000)
            ok(f"{T} {nm}：扣完內容真的出現（鎖與一行字拿掉）、本機體驗剩 2 次", bool(opened) and pg.evaluate(f"() => TwGrants.left('{key}')") == 2, pg.evaluate(f"() => TwGrants.left('{key}')"))
            shot(pg, f"grant_after_{key}.png")
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("新功能次數1102", lambda pg, b, base, code: t_featkeys_1102(b, base, code))
