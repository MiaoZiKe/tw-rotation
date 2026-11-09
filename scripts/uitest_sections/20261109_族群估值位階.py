# 驗收段落「族群估值位階1109」—— P-1107-04 族群同業估值位階（site/peerval.js，資料 data/peer_val.json）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx()、_sub_ctx()、P12_INL、OP_POP、SITE 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _PV1109_ 開頭（所有段落 exec 進同一個命名空間）。
# 真的操作（讀本機 site/data/peer_val.json 的真資料，斷言一律跟 JSON 比，不寫死數字）：
#   0. 功能鍵 group.peerval／stock.peerval：登記（limBy 訪客 3、veil、qnote）、plan_presets 四方案都開、訪客 3／其他不限、在「編輯：新會員體驗」清單、有公告
#   1. 族群頁（註冊會員 1440）：位階表出現、列數＝JSON 的族群檔數、預設依代號；點「本益比」欄名 → 順序真的變成本益比由低到高（虧損排最後），
#      再點 → 反向；每一條分位條的寬度＝那一格的百分位（style 與實際量到的像素都對）、數字＝JSON；虧損那檔寫「不適用（虧損）」；中位數列＝JSON
#   2. 個股頁：小卡「在○○族群同業中：本益比位於第 N 百分位」N＝JSON；多族群可切換（族群名與數字跟著換）；虧損股寫「本益比不適用（虧損）」；
#      同業樣本不足的寫「同業樣本不足」
#   3. 上限：訪客第 4 個族群／第 4 檔被鎖（反灰＋一行字、不蓋大卡）；站主種 99 次也不鎖；
#      體驗：範本把註冊會員設成每日 1 次、有體驗額度 → 被鎖後「繼續看」真的打 /v1/grants/hit、表出現
#   4. 手機 390：表在畫面寬度內、整頁沒有橫向捲軸、表格框可以左右拖（scrollWidth > clientWidth）、超過 10 檔只先列 10 檔＋「看全部 N 檔」真的展開；個股小卡在寬度內
import json as _pv1109_json

_PV1109_GID = "analog_power_ic"          # 13 檔、含 1 檔虧損（2342 茂矽）——族群換了成員也沒關係，斷言都跟 JSON 比
_PV1109_NOTE_G = "族群估值位階表今日 {n} 次已用完"
_PV1109_NOTE_S = "同業估值位階今日 {n} 次已用完"


def _pv1109_data():
    return _pv1109_json.load(open(str(SITE / "data" / "peer_val.json"), encoding="utf-8"))


def t_peerval_1109(b, base, code):
    T = "族群估值位階1109"
    errs: list = []
    D = _pv1109_data()
    cols = D["cols"]
    rows_of = lambda gid: [dict(zip(cols, r)) for r in D["groups"][gid]["rows"]]  # noqa: E731

    def agree(pg):
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click(); pg.wait_for_timeout(300)

    def grp(pg, gid=_PV1109_GID, fresh=True):
        if fresh:
            pg.goto(base + "#industry/group/" + gid, wait_until="domcontentloaded")
        else:
            pg.evaluate(f"() => {{ location.hash = '#industry/group/{gid}'; }}")
        return wait_until(pg, f"() => {{ const c = document.getElementById('pvCard'); return !!c && c.dataset.gid === '{gid}'; }}", 30000)

    def stock(pg, cd, fresh=True):
        if fresh:
            pg.goto(base + "#stock/" + cd, wait_until="domcontentloaded")
        else:
            pg.evaluate(f"() => {{ location.hash = '#stock/{cd}'; }}")
        want_ = f"() => {{ const c = document.getElementById('pvStock'); return !!c && c.dataset.code === '{cd}' && !!c.querySelector('.pvsline'); }}"
        r_ = wait_until(pg, want_, 30000)
        # 個股頁載完後 industry.js 會再重畫一次總覽（#skOv 整塊換掉），小卡會在 50ms 內補回來：等穩了再讀
        pg.wait_for_timeout(800)
        r_ = r_ and wait_until(pg, want_, 8000)
        if not r_:
            ok(f"{T} 個股頁 {cd} 的小卡畫得出來", False, pg.evaluate("() => [location.hash, !!document.getElementById('skOv'), !!document.getElementById('pvStock'), window.__pvErr || '', (document.querySelector('#stockTabs button.on') || {}).textContent]"))
        return r_

    order = lambda pg: pg.evaluate("() => [...document.querySelectorAll('#pvCard tbody tr')].map(r => r.dataset.code)")  # noqa: E731

    # ------------------------------------------------------------ 0. 登記
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    grp(pg)
    d = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, keys = ['group.peerval', 'stock.peerval'];
        const tier = (k) => P.tiers.find(t => t.key === k);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(f => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && !BAN.includes(f.id)).map(f => f.id);
        return { reg: keys.map(k => { const f = F.byId(k); return f && [f.kind, f.limBy && f.limBy.guest, !!(f.limBy && f.limBy.free), (f.veil[0] || [])[0], !!f.qnote, f.route.source]; }),
          free: keys.map(k => [TwPerm.can(k), TwPerm.lim(k)]),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => keys.map(k => tier(t).lims[k] == null ? null : tier(t).lims[k])),
          feats: ['guest', 'free', 'plus', 'pro'].map(t => keys.map(k => tier(t).feats[k])),
          inEditor: keys.map(k => ed.includes(k)) }; }""")
    ok(f"{T} 兩個功能鍵都登記了（bool、訪客 limBy 3、註冊會員沒有 limBy、veil 是 #pvCard／#pvStock、有 qnote）",
       d["reg"][0][:5] == ["bool", 3, False, "#pvCard", True] and d["reg"][1][:5] == ["bool", 3, False, "#pvStock", True], d["reg"])
    ok(f"{T} 註冊會員：可用、不限次數（Infinity）", d["free"][0][0] and d["free"][1][0] and all(x[1] is None or x[1] > 1e9 for x in d["free"]), d["free"])
    ok(f"{T} plan_presets.js：四個方案都開；每日次數 訪客 3、註冊會員／Plus／Pro 不設＝不限",
       d["feats"] == [[True, True]] * 4 and d["lims"] == [[3, 3], [None, None], [None, None], [None, None]], (d["feats"], d["lims"]))
    ok(f"{T} 「編輯：新會員體驗」清單列得到兩個鍵（不在法遵禁止清單）", all(d["inEditor"]), d["inEditor"])
    notes = _pv1109_json.load(open(str(SITE / "notices" / "features.json"), encoding="utf-8"))
    nt = [n for n in notes if n.get("id") == "f-20261109-peer-val"]
    ok(f"{T} 同一個 commit 有「功能更新」公告（f-20261109-peer-val、給所有人、有站內連結）",
       len(nt) == 1 and nt[0]["aud"] == "all" and "](#industry/group/" in nt[0]["body"], nt[:1])
    for bad in ("便宜可買", "高估", "低估", "買進", "賣出", "避開"):
        ok(f"{T} 法遵：公告與表格文字不出現「{bad}」", bad not in nt[0]["body"] and bad not in pg.evaluate("() => document.getElementById('pvCard').innerText"))

    # ------------------------------------------------------------ 1. 族群頁位階表（註冊會員 1440）
    G = D["groups"][_PV1109_GID]
    R = {r["code"]: r for r in rows_of(_PV1109_GID)}
    o0 = order(pg)
    ok(f"{T} 位階表出現在族群卡內容區（.nbbody 最後）、看得到、列數＝JSON 族群檔數（{G['n']}）",
       pg.evaluate("() => { const c = document.querySelector('.nbbody > #pvCard'); return !!c && c.getClientRects().length > 0; }") and len(o0) == G["n"] == len(R), (len(o0), G["n"]))
    # 有剖析圖的族群（族群頁顯示剖析圖、#gpSec 藏著）也要看得到
    dgg = next((g for g in ("foundry", "panel", "bank") if g in D["groups"]), None)
    if dgg:
        grp(pg, dgg, fresh=False); pg.wait_for_timeout(400)
        ok(f"{T} ★ 有剖析圖的族群（{dgg}）：位階表照樣看得到（不被藏在 #gpSec 裡）", pg.evaluate("() => { const c = document.getElementById('pvCard'); return !!c && c.getClientRects().length > 0 && c.getBoundingClientRect().height > 100; }"))
        grp(pg, _PV1109_GID, fresh=False); pg.wait_for_timeout(400)
        o0 = order(pg)
    ok(f"{T} 預設依代號排序（不依估值排，避免像推薦清單）", o0 == sorted(o0), o0)
    pg.locator('#pvCard th[data-sk="pe"]').click(); pg.wait_for_timeout(250)
    o1 = order(pg)
    want = sorted([c_ for c_ in R if R[c_]["pe"] is not None], key=lambda c_: (R[c_]["pe"], c_)) + sorted(c_ for c_ in R if R[c_]["pe"] is None)
    ok(f"{T} ★ 點「本益比」欄名：順序真的變了、＝本益比由低到高（沒有本益比的排最後）、欄名標 ▲", o1 != o0 and o1 == want
       and pg.evaluate("() => document.querySelector('#pvCard th[data-sk=\"pe\"]').getAttribute('aria-sort')") == "ascending", (o1, want))
    pg.locator('#pvCard th[data-sk="pe"]').click(); pg.wait_for_timeout(250)
    o2 = order(pg)
    want2 = sorted([c_ for c_ in R if R[c_]["pe"] is not None], key=lambda c_: (-R[c_]["pe"], c_)) + sorted(c_ for c_ in R if R[c_]["pe"] is None)
    ok(f"{T} ★ 再點一次：反向（由高到低）、▼", o2 == want2 and pg.evaluate("() => document.querySelector('#pvCard th[data-sk=\"pe\"]').getAttribute('aria-sort')") == "descending", o2)
    pg.locator('#pvCard th[data-sk="yoy"]').click(); pg.wait_for_timeout(250)
    o3 = order(pg)
    want3 = sorted([c_ for c_ in R if R[c_]["yoy"] is not None], key=lambda c_: (R[c_]["yoy"], c_)) + sorted(c_ for c_ in R if R[c_]["yoy"] is None)
    ok(f"{T} 換點「營收 YoY」：依營收年增由低到高", o3 == want3, o3)
    bars = pg.evaluate("""() => [...document.querySelectorAll('#pvCard tbody tr')].flatMap(tr => [...tr.querySelectorAll('td[data-k] .pvbar')].map(b => {
        const i = b.querySelector('i'), bw = b.getBoundingClientRect().width, iw = i.getBoundingClientRect().width;
        return { code: tr.dataset.code, k: b.closest('td').dataset.k, p: +b.dataset.p, style: parseFloat(i.style.width), ratio: bw ? iw / bw * 100 : -1,
          num: +(b.nextElementSibling || {}).textContent }; }))""")
    pk = {"pe": "p_pe", "pb": "p_pb", "dy": "p_dy", "yoy": "p_yoy", "own": "own"}
    bad = [x for x in bars if not (x["style"] == x["p"] and abs(x["ratio"] - x["p"]) <= 1.5 and x["num"] == x["p"] and R[x["code"]][pk[x["k"]]] == x["p"])]
    ok(f"{T} ★ 每一條分位條：寬度＝百分位（style 與實際量到的比例都對，誤差 ≤1.5%）、旁邊數字＝JSON（共 {len(bars)} 條）", len(bars) >= G["n"] * 3 and not bad, bad[:4])
    loss = [c_ for c_, r in R.items() if r["st"] == "loss"]
    if loss:
        t_ = pg.evaluate(f"() => document.querySelector('#pvCard tr[data-code=\"{loss[0]}\"] td[data-k=\"pe\"]').innerText")
        ok(f"{T} 虧損那檔（{loss[0]}）本益比寫「不適用（虧損）」、不畫條", "不適用（虧損）" in t_ and not pg.evaluate(f"() => !!document.querySelector('#pvCard tr[data-code=\"{loss[0]}\"] td[data-k=\"pe\"] .pvbar')"), t_)
    med = pg.evaluate("() => [...document.querySelectorAll('#pvCard tfoot td[data-k]')].map(td => [td.dataset.k, td.innerText.trim()])")
    want_med = [[k, ("—" if G["med"][k] is None else (f"{G['med'][k]:.{nd}f}" + ("%" if k in ("dy", "yoy") else "")))] for k, nd in (("pe", 1), ("pb", 2), ("dy", 2), ("yoy", 1))]
    ok(f"{T} 族群中位數列＝JSON（{want_med}）", med == want_med, med)
    ok(f"{T} 表格在卡片寬度內（1440 不需要左右捲）", pg.evaluate("() => { const s = document.querySelector('#pvCard .pvscroll'); return s.scrollWidth <= s.clientWidth + 1; }"))
    # 「?」說明
    pg.locator('#pvCard .howbtn[data-how="pv"]').click(); pg.wait_for_timeout(400)
    how = pg.evaluate("() => { const v = [...document.querySelectorAll('.howtxt, .howpop, [role=dialog]')].filter(e => e.getClientRects().length > 0).map(e => e.innerText).join(' '); return v; }")
    ok(f"{T} 按「?」看得到口徑（同業百分位、虧損不排、樣本不足、自身歷史、不是買賣建議）", all(s_ in how for s_ in ("比它低", "虧損", "5 檔", "近 3～5 年", "不是買賣建議")), how[:200])
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    # 點名稱進個股頁
    first = o3[0]
    pg.locator(f'#pvCard tr[data-code="{first}"] a.pvlk').click()
    ok(f"{T} 點表格裡的股票名稱 → 進那一檔的個股頁", bool(wait_until(pg, f"() => location.hash === '#stock/{first}'", 6000)))
    c.close()

    # ------------------------------------------------------------ 2. 個股頁小卡
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    multi = next((cd for cd, ids in D["stocks"].items() if len(ids) >= 2 and all(D["groups"][g]["kind"] == "grp" for g in ids)
                  and any(dict(zip(cols, r))["p_pe"] is not None for g in ids for r in D["groups"][g]["rows"] if r[0] == cd)), None)
    if multi:
        stock(pg, multi)
        agree(pg)
        s1 = pg.evaluate("() => { const c = document.getElementById('pvStock'); return { gid: c.dataset.gid, line: c.querySelector('.pvsline').innerText, chips: [...c.querySelectorAll('.pvchip')].map(b => b.dataset.g), card: !!c.closest('#skOv') }; }")
        r1 = next(dict(zip(cols, r)) for r in D["groups"][s1["gid"]]["rows"] if r[0] == multi)
        g1 = D["groups"][s1["gid"]]
        want_line = f"在「{g1['name']}」族群同業中（{g1['n']} 檔）：" + (f"本益比位於第 {r1['p_pe']} 百分位" if r1["p_pe"] is not None else "")
        ok(f"{T} ★ 個股頁（{multi}）總覽三欄卡下面有小卡，文字「{want_line}」＝JSON", s1["card"] and s1["line"].startswith(want_line), s1)
        ok(f"{T} 屬多個族群：上方有族群鈕可切換（{len(s1['chips'])} 顆）", len(s1["chips"]) == len(D["stocks"][multi][:4]) >= 2, s1["chips"])
        other = [g for g in s1["chips"] if g != s1["gid"]][0]
        pg.locator(f'#pvStock .pvchip[data-g="{other}"]').click(); pg.wait_for_timeout(300)
        s2 = pg.evaluate("() => { const c = document.getElementById('pvStock'); return { gid: c.dataset.gid, line: c.querySelector('.pvsline').innerText }; }")
        g2 = D["groups"][other]
        ok(f"{T} ★ 點另一個族群鈕：比較的族群真的換成「{g2['name']}」、檔數＝JSON", s2["gid"] == other and f"「{g2['name']}」" in s2["line"] and f"（{g2['n']} 檔）" in s2["line"], s2)
        mini = pg.evaluate("() => [...document.querySelectorAll('#pvStock .pvminis .pvbar')].map(b => [b.closest('.pvc').dataset.k, +b.dataset.p, parseFloat(b.querySelector('i').style.width)])")
        r2 = next(dict(zip(cols, r)) for r in D["groups"][other]["rows"] if r[0] == multi)
        ok(f"{T} 小卡四格的分位條＝JSON（換族群後）", all(p == w == r2[{"pe": "p_pe", "pb": "p_pb", "dy": "p_dy", "yoy": "p_yoy"}[k]] for k, p, w in mini) and len(mini) >= 1, mini)
        if D["groups"][other]["kind"] == "grp":
            pg.locator("#pvStock .pvgo").click()
            ok(f"{T} 「看族群位階表 ›」→ 進那個族群頁、位階表出現", bool(wait_until(pg, f"() => location.hash === '#industry/group/{other}' && !!document.getElementById('pvCard')", 20000)))
    else:
        ok(f"{T} 找得到屬多個族群的股票（資料）", False)
    lossc = next((cd for cd, ids in D["stocks"].items() if any(r[0] == cd and dict(zip(cols, r))["st"] == "loss" for r in D["groups"][ids[0]]["rows"])
                  and len(ids) == 1), None)
    if lossc:
        stock(pg, lossc, fresh=False)
        t_ = pg.evaluate("() => (document.querySelector('#pvStock .pvsline') || {}).innerText || ''")
        ok(f"{T} 虧損股（{lossc}）小卡寫「本益比不適用（虧損）」", "本益比不適用（虧損）" in t_, t_)
    thinc = next((cd for cd, ids in D["stocks"].items() if len(ids) == 1 and D["groups"][ids[0]]["nv"]["pe"] < 5
                  and any(r[0] == cd and dict(zip(cols, r))["st"] == "" for r in D["groups"][ids[0]]["rows"])), None)
    if thinc:
        stock(pg, thinc, fresh=False)
        t_ = pg.evaluate("() => (document.querySelector('#pvStock .pvsline') || {}).innerText || ''")
        ok(f"{T} 同業有效樣本 < 5 檔（{thinc}）寫「同業樣本不足」、不給百分位", "同業樣本不足" in t_ and "百分位" not in t_, t_)
    pg.evaluate("() => { location.hash = '#overview'; }"); pg.wait_for_timeout(600)
    ok(f"{T} 離開個股頁 → 小卡拿掉", not pg.evaluate("() => !!document.getElementById('pvStock')"))
    c.close()

    # ------------------------------------------------------------ 3. 上限：訪客、站主、體驗
    gids = [g for g, v in D["groups"].items() if v["kind"] == "grp" and v["rows"]][:6]
    c = _p12_ctx(b, plan="guest", seed={"group.peerval": 3, "stock.peerval": 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    grp(pg); agree(pg)
    wait_until(pg, "() => !!document.querySelector('#pvCard > .qcov .qcard.qcnote')", 8000)
    a = pg.evaluate(P12_INL, "#pvCard")
    ok(f"{T} ★ 訪客用滿 3 個族群後第 4 個被鎖：表反灰＋一行「{_PV1109_NOTE_G.replace('{n}', '3')}」、不蓋大卡、沒有彈出層",
       a["on"] and _PV1109_NOTE_G.replace("{n}", "3") in a["txt"] and not a["big"] and not pg.evaluate(OP_POP), a)
    stock(pg, "2303", fresh=False)
    wait_until(pg, "() => !!document.querySelector('#pvStock > .qcov .qcard.qcnote')", 8000)
    a = pg.evaluate(P12_INL, "#pvStock")
    ok(f"{T} ★ 訪客第 4 檔個股小卡被鎖：「{_PV1109_NOTE_S.replace('{n}', '3')}」", a["on"] and _PV1109_NOTE_S.replace("{n}", "3") in a["txt"] and not a["big"], a)
    c.close()

    c = _p12_ctx(b, plan="guest")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    grp(pg, gids[0]); agree(pg)
    for g in gids[1:3]:
        grp(pg, g, fresh=False); pg.wait_for_timeout(500)
    n3 = pg.evaluate("() => (TwQuota.used('group.peerval') || []).length")
    ok(f"{T} 訪客真的看了 3 個族群 → 計數 3、第 3 個還看得到", n3 == 3 and not pg.evaluate(P12_INL, "#pvCard")["on"], n3)
    grp(pg, gids[0], fresh=False); pg.wait_for_timeout(500)
    ok(f"{T} 同一天重看已看過的族群不重算（仍 3）", pg.evaluate("() => (TwQuota.used('group.peerval') || []).length") == 3)
    grp(pg, gids[3], fresh=False)
    locked = wait_until(pg, "() => !!document.querySelector('#pvCard > .qcov .qcard.qcnote')", 8000)
    ok(f"{T} ★ 真的操作：第 4 個族群被鎖", bool(locked), pg.evaluate(P12_INL, "#pvCard"))
    c.close()

    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script("try { if (!localStorage.getItem('pv1109.init')) { localStorage.setItem('pv1109.init', '1'); localStorage.setItem('tw.live.on', '0');"
                      " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      " const s = Array.from({length: 99}, (_, i) => 'seed' + i);"
                      " localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'group.peerval': s, 'stock.peerval': s } })); } } catch (e) {}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    grp(pg); agree(pg); pg.wait_for_timeout(900)
    o = pg.evaluate(P12_INL, "#pvCard")
    stock(pg, "2303", fresh=False); pg.wait_for_timeout(900)
    o2 = pg.evaluate(P12_INL, "#pvStock")
    ok(f"{T} ★ 站主（owner）種 99 次也不鎖：位階表與個股小卡都照常", not o["on"] and not o["big"] and not o2["on"] and not o2["big"], (o, o2))
    c.close()

    # 體驗：範本把註冊會員設成每日 1 次（管理者可以這樣設）、新會員體驗給 3 次 → 用完後「繼續看」
    now = int(__import__("time").time() * 1000)
    API = "https://peerval1109.example.test"
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
            out = {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {}, "lims": {"group.peerval": 1}, "dq": None}
        elif path == "/v1/grants/public":
            out = {"now": now, "promo": [], "welcome": []}
        elif path == "/v1/grants/me":
            out = {"now": now, "today": {}, "grants": [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": now, "end": now + 14 * 86400000 - 1000, "per": "day",
                                                     "feats": {"group.peerval": {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1; stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_pv1109_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _pv1109_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test');localStorage.setItem('tw.live.on','0');"
                      "const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);"
                      "localStorage.setItem('tw.quota', JSON.stringify({ day, k: { 'group.peerval': ['seed0'] } }))}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#industry/group/" + _PV1109_GID, wait_until="domcontentloaded")
    agree(pg)
    wait_until(pg, "() => window.TwGrants && TwGrants.left('group.peerval') === 3 && !!document.getElementById('pvCard')", 30000)
    wait_until(pg, "() => !!document.querySelector('#pvCard .qc-try')", 8000)
    btn = pg.locator("#pvCard .qc-try")
    ok(f"{T} ★ 體驗中的註冊會員用完每日 1 次後，位階表原位置多一顆「繼續看」、體驗剩 3 次", btn.count() == 1 and stt["hit"] == 0,
       pg.evaluate("() => ((document.getElementById('pvCard') || {}).innerText || '').slice(0, 200)"))
    if btn.count():
        pg.wait_for_timeout(1500)
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        btn.first.scroll_into_view_if_needed()
        with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
            btn.first.click()
        hj = ri.value.json()
        ok(f"{T} 按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
        shown = wait_until(pg, "() => { const e = document.getElementById('pvCard'); return !!e && !e.hasAttribute('data-qlk') && !e.querySelector(':scope > .qcov') && e.querySelectorAll('tbody tr').length > 0; }", 6000)
        ok(f"{T} ★ 扣完體驗位階表真的出現（鎖與一行字拿掉、列都在）", bool(shown))
    c.close()

    # ------------------------------------------------------------ 4. 手機 390
    c = _p12_ctx(b, plan="free", width=390, touch=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    grp(pg); agree(pg); pg.wait_for_timeout(600)
    m = pg.evaluate("""() => { const c = document.getElementById('pvCard'), s = c.querySelector('.pvscroll'), r = c.getBoundingClientRect();
        const vis = [...c.querySelectorAll('tbody tr')].filter(t => t.getClientRects().length > 0).length;
        const mo = c.querySelector('.pvmore');
        return { l: r.left, r: r.right, vw: innerWidth, page: document.scrollingElement.scrollWidth, sw: s.scrollWidth, cw: s.clientWidth, ox: getComputedStyle(s).overflowX,
          vis, all: c.querySelectorAll('tbody tr').length, more: mo && !mo.hidden ? mo.innerText : '' }; }""")
    ok(f"{T} 手機 390：位階表在畫面寬度內、整頁沒有橫向捲軸", m["l"] >= 0 and m["r"] <= m["vw"] + 0.5 and m["page"] <= m["vw"], m)
    ok(f"{T} 手機 390：表格框可以左右拖（overflow-x auto、內容比框寬）", m["ox"] == "auto" and m["sw"] > m["cw"], m)
    pg.evaluate("() => { document.querySelector('#pvCard .pvscroll').scrollLeft = 200; }"); pg.wait_for_timeout(100)
    ok(f"{T} 手機 390：真的捲得動（scrollLeft 變了）", pg.evaluate("() => document.querySelector('#pvCard .pvscroll').scrollLeft") > 0)
    if m["all"] > 10:
        ok(f"{T} 手機 390：超過 10 檔只先列 10 檔＋「看全部 {m['all']} 檔」", m["vis"] == 10 and m["more"] == f"看全部 {m['all']} 檔", m)
        pg.locator("#pvCard .pvmore").click(); pg.wait_for_timeout(200)
        ok(f"{T} 手機 390：按「看全部」→ {m['all']} 檔都出現、按鈕收起", pg.evaluate("() => [...document.querySelectorAll('#pvCard tbody tr')].filter(t => t.getClientRects().length > 0).length") == m["all"]
           and pg.evaluate("() => document.querySelector('#pvCard .pvmore').hidden"))
    stock(pg, "2303", fresh=False); pg.wait_for_timeout(600)
    s = pg.evaluate("() => { const r = document.getElementById('pvStock').getBoundingClientRect(); return { l: r.left, r: r.right, vw: innerWidth, page: document.scrollingElement.scrollWidth, vis: r.height > 0 }; }")
    ok(f"{T} 手機 390：個股小卡看得到、在畫面寬度內、整頁沒有橫向捲軸", s["vis"] and s["l"] >= 0 and s["r"] <= s["vw"] + 0.5 and s["page"] <= s["vw"], s)
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("族群估值位階1109", lambda pg, b, base, code: t_peerval_1109(b, base, code))
