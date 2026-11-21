# 驗收段落「風險警示牌1109」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_sub_ctx() 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _RF1109_ 開頭（所有段落 exec 進同一個命名空間）。
# P-1107-02（Andy 2026-11-09 點頭「02 05 03 04 06」）：交易所公布的注意股／處置股（site/riskflag.js，資料 data/risk_flags.json）。
# 真的操作（假資料：data/risk_flags.json 換成下面這份，「今天」固定 2026-11-10）：
#   1. 個股頁：處置中的 2330 → K 線卡出現琥珀色警示條「處置中・期間 11/9～11/13・約每五分鐘撮合一次・預收款券」，顏色是 --amber 不是紅綠；
#      注意股 2454 → 「注意股・11/9 公布・近 10 個交易日被列注意 3 次」；即將處置 3711 →「即將處置」；
#      沒被列的 2303 → 沒有警示條（換股後舊的那條也要消失）；按「?」→ 說明寫來源與「公布注意暨處置專區」
#   2. 自選清單（#watch）：2330 角標「處置」、2454「注意」、3711「將處置」、2303 沒有
#   3. 族群頁：#industry/group/foundry →「本族群 1 檔處置中」；沒有任何一檔被列的族群（ip_asic）→ 沒有計數
#   4. 手機 390：警示條在畫面寬度內、整頁沒有橫向捲軸、點文字展開全文
#   5. 功能鍵 risk.flag：登記（bool、全站工具、不計次、不進 METERED）、四方案都開且不設次數、在「編輯：新會員體驗」清單；
#      註冊會員連開 6 檔個股頁照樣看得到（沒有上限可用完）；管理者把範本關掉 → 警示條／角標／族群計數都不畫；站主（owner）不受範本影響
import json as _rf1109_json

_RF1109_TODAY = "2026-11-10"
_RF1109_DATA = {
    "date": "2026-11-09", "notice_date": "2026-11-09", "since": "2026-10-20",
    "window": ["2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09"],
    "markets": ["TWSE", "TPEX"],
    "stocks": {
        "2330": {"name": "台積電", "market": "TWSE", "punish": [{"date": "2026-11-06", "start": "2026-11-09", "end": "2026-11-13", "reason": "連續三次",
                                                                  "measure": "第一次處置", "match": "約每五分鐘撮合一次", "prepay": True}]},
        "3711": {"name": "日月光投控", "market": "TWSE", "punish": [{"date": "2026-11-10", "start": "2026-11-11", "end": "2026-11-17", "reason": "連續三次",
                                                                     "measure": "第一次處置", "match": "約每二分鐘撮合一次", "prepay": False}]},
        "2454": {"name": "聯發科", "market": "TWSE", "notice": {"last": "2026-11-09", "reason": "最近六個營業日累積收盤價漲幅達32.15%", "n10": 3,
                                                               "dates": ["2026-11-04", "2026-11-06", "2026-11-09"]}},
        "1101": {"name": "台泥", "market": "TWSE", "punish": [{"date": "2026-10-20", "start": "2026-10-21", "end": "2026-10-27", "reason": "連續三次",
                                                               "measure": "第一次處置", "match": None, "prepay": False}]},
    },
    "groups": {"foundry": ["2330"], "ic_design": ["2454"]},
}
_RF1109_BAR = "() => { const b = document.getElementById('riskBar'); return b ? { code: b.dataset.code, txt: b.innerText, card: !!b.closest('#skChartCard') } : null; }"


def _rf1109_ctx(b, who="member", owner=False, feats=None, width=1440, touch=False, data=None):
    c, sent, st = _sub_ctx(b, who, owner=owner, feats=feats if feats is not None else {}, lims={}, width=width, touch=touch)
    body = _rf1109_json.dumps(data if data is not None else _RF1109_DATA, ensure_ascii=False)
    c.route("**/data/risk_flags.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=body))
    # 登入的人自選清單走雲端（/v1/lists/get）：假 Worker 回一份含 4 檔的清單；改動（刪除）回 ok
    lists = {"rev": 1, "lists": [{"id": "t1", "name": "自選 1", "codes": ["2330", "2303", "2454", "3711"]}]}

    def _lists(route):
        rq = route.request
        if rq.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        if rq.url.split("?")[0].endswith("/put"):
            try:
                lists["lists"] = _rf1109_json.loads(rq.post_data or "{}").get("lists") or lists["lists"]
            except Exception:  # noqa: BLE001
                pass
            lists["rev"] += 1
            out = {"ok": True, "rev": lists["rev"]}
        else:
            out = lists
        route.fulfill(status=200, body=_rf1109_json.dumps(out, ensure_ascii=False), headers={"access-control-allow-origin": "*", "content-type": "application/json"})
    if who:
        c.route(SUB_API + "/v1/lists/**", _lists)
    c.add_init_script(f"window.TW_RISK_TODAY = '{_RF1109_TODAY}';"
                      "try { localStorage.setItem('tw.live.on', '0'); if (!localStorage.getItem('rf.init')) { localStorage.setItem('rf.init', '1');"
                      " localStorage.setItem('tw.watch', JSON.stringify(['2330', '2303', '2454', '3711'])); } } catch (e) {}")
    return c


def t_risk_flag_1109(b, base, code):
    T = "風險警示牌1109"
    errs: list = []

    def stock(pg, cd, want=True):
        pg.goto(base + "#stock/" + cd, wait_until="domcontentloaded")
        wait_until(pg, f"() => !!document.getElementById('skChartCard') && !!window.TwRisk && !!TwRisk._d() && location.hash === '#stock/{cd}'", 30000)
        if want:
            wait_until(pg, f"() => {{ const b = document.getElementById('riskBar'); return !!b && b.dataset.code === '{cd}'; }}", 8000)
        else:
            pg.wait_for_timeout(1200)
        return pg.evaluate(_RF1109_BAR)

    # ---------------------------------------------------------------- 1. 個股頁（註冊會員，桌機 1440）
    c = _rf1109_ctx(b)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    r = stock(pg, "2330")
    ok(f"{T} 處置中的 2330：K 線卡裡出現警示條「處置中」、期間 11/9～11/13、撮合方式原文、預收款券、11/6 公布",
       bool(r) and r["card"] and all(s in r["txt"] for s in ("處置中", "期間 11/9～11/13", "約每五分鐘撮合一次", "預收款券", "第一次處置", "11/6 公布")), r)
    col = pg.evaluate("""() => { const b = document.getElementById('riskBar'), t = b.querySelector('.rk-tag');
        const probe = document.createElement('i'); probe.style.color = 'var(--amber)'; document.body.appendChild(probe); const amber = getComputedStyle(probe).color; probe.remove();
        const pr = document.createElement('i'); pr.style.color = 'var(--rise, #ff5b6e)'; document.body.appendChild(pr); const rise = getComputedStyle(pr).color; pr.remove();
        return { edge: getComputedStyle(b).borderLeftColor, tag: getComputedStyle(t).backgroundColor, amber, rise,
          head: !!document.getElementById('skHead') && document.getElementById('skHead').nextElementSibling === b }; }""")
    ok(f"{T} 警示條用琥珀色（左邊框與標籤底色＝--amber，不是漲跌紅綠）、緊接在名稱區下方", col["edge"] == col["amber"] and col["tag"] == col["amber"] and col["edge"] != col["rise"] and col["head"], col)
    txt = pg.evaluate("() => document.getElementById('riskBar').innerText")
    ok(f"{T} 法遵：警示條沒有「避開／危險／快跑／建議」字眼", not any(w in txt for w in ("避開", "危險", "快跑", "建議", "買進", "賣出")), txt)
    pg.locator("#riskBar .howbtn").click()
    wait_until(pg, "() => { const e = document.getElementById('how-risk'); return !!e && !e.hidden && e.getClientRects().length > 0; }", 4000)
    hw = pg.evaluate("() => (document.getElementById('how-risk') || {}).innerText || ''")
    ok(f"{T} 按「?」→ 說明寫來源（證交所、櫃買）、只數公告不推算門檻、交易所「公布注意暨處置專區」", all(s in hw for s in ("證交所", "櫃買", "不推算", "公布注意暨處置專區")), hw[:200])
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    r2 = stock(pg, "2303", want=False)
    ok(f"{T} 換到沒被列的 2303 → 沒有警示條（2330 那條也跟著消失）", r2 is None and pg.evaluate("() => document.querySelectorAll('.riskbar').length") == 0, r2)
    r3 = stock(pg, "2454")
    ok(f"{T} 注意股 2454：「注意股・11/9 公布・近 10 個交易日被列注意 3 次」＋交易所原因原文；湖的起點早於視窗，不寫「本站自…起記錄」",
       bool(r3) and all(s in r3["txt"] for s in ("注意股", "11/9 公布", "近 10 個交易日被列注意 3 次", "32.15%")) and "本站自" not in r3["txt"], r3)
    r4 = stock(pg, "3711")
    ok(f"{T} 即將處置 3711（起日 11/11 晚於今天 11/10）→「即將處置」、不寫「處置中」、沒有預收款券", bool(r4) and "即將處置" in r4["txt"] and "處置中" not in r4["txt"] and "預收款券" not in r4["txt"], r4)
    r5 = stock(pg, "1101", want=False)
    ok(f"{T} 處置已結束（訖日 10/27）的 1101 → 沒有警示條", r5 is None, r5)

    # ---------------------------------------------------------------- 2. 自選清單角標
    pg.goto(base + "#watch", wait_until="domcontentloaded")
    wait_until(pg, "() => document.querySelectorAll('#wpTbl tr[data-go]').length >= 4 && document.querySelectorAll('#wpTbl .rkb').length >= 3", 20000)
    w = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('#wpTbl tr[data-go]')].map(r => [r.dataset.go, (r.querySelector('.rkb') || {}).textContent || null]))")
    dbg = pg.evaluate("() => ({ d: !!(window.TwRisk && TwRisk._d()), n: window.TwRisk && TwRisk._d() ? Object.keys(TwRisk._d().stocks || {}).length : -1, can: window.TwPerm ? TwPerm.can('risk.flag') : null, info: window.TwRisk ? !!TwRisk.info('2330') : null, at: !!document.querySelector('#wpTbl tr[data-go] .t small.num'), h: location.hash })")
    ok(f"{T} 自選清單：2330「處置」、2454「注意」、3711「將處置」、2303 沒有角標", w.get("2330") == "處置" and w.get("2454") == "注意" and w.get("3711") == "將處置" and w.get("2303") is None, (w, dbg))
    # 刪掉 2330 再看：角標跟著那一列走，不會黏到別列
    pg.locator("#wpTbl button.del[data-del='2330']").click()
    wait_until(pg, "() => !document.querySelector('#wpTbl tr[data-go=\"2330\"]')", 6000)
    pg.wait_for_timeout(400)
    w2 = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('#wpTbl tr[data-go]')].map(r => [r.dataset.go, (r.querySelector('.rkb') || {}).textContent || null]))")
    ok(f"{T} 刪掉 2330 後清單重畫，其餘角標照舊（2454 注意、3711 將處置、2303 沒有）", "2330" not in w2 and w2.get("2454") == "注意" and w2.get("3711") == "將處置" and w2.get("2303") is None, w2)

    # ---------------------------------------------------------------- 3. 族群頁計數
    pg.goto(base + "#industry/group/foundry", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('riskGrp')", 30000)
    g = pg.evaluate("() => { const e = document.getElementById('riskGrp'); return { txt: e.innerText, np: e.dataset.np, tip: e.title, inPick: !!e.closest('#dgPick') }; }")
    ok(f"{T} 族群頁 foundry：分頁列右邊「本族群 1 檔處置中」、滑過看得到是哪一檔", g["txt"] == "本族群 1 檔處置中" and g["np"] == "1" and "2330" in g["tip"] and g["inPick"], g)
    pg.goto(base + "#industry/group/ip_asic", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('dgPick') && location.hash.includes('ip_asic')", 30000)
    pg.wait_for_timeout(1500)
    ok(f"{T} 沒有任何一檔被列的族群（ip_asic）→ 沒有計數", pg.evaluate("() => !document.getElementById('riskGrp')"))
    c.close()

    # ---------------------------------------------------------------- 4. 手機 390
    c = _rf1109_ctx(b, width=390, touch=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    stock(pg, "2454")
    m = pg.evaluate("""() => { const b = document.getElementById('riskBar').getBoundingClientRect(), t = document.querySelector('#riskBar .rk-row[data-rk="notice"] .rk-t');
        return { l: Math.round(b.left), r: Math.round(b.right), h: Math.round(b.height), vw: innerWidth, sw: document.documentElement.scrollWidth, th: Math.round(t.getBoundingClientRect().height) }; }""")
    ok(f"{T} 390：警示條整條在畫面內、整頁沒有橫向捲軸、高度 ≤ 80（文字最多兩行）", m["l"] >= 0 and m["r"] <= m["vw"] and m["sw"] <= m["vw"] and m["h"] <= 80, m)
    pg.locator('#riskBar .rk-row[data-rk="notice"] .rk-t').tap()
    pg.wait_for_timeout(300)
    th2 = pg.evaluate("() => Math.round(document.querySelector('#riskBar .rk-row[data-rk=\"notice\"] .rk-t').getBoundingClientRect().height)")
    ok(f"{T} 390：點警示條文字 → 展開全文（高度變高）", th2 > m["th"], (m["th"], th2))
    c.close()

    # ---------------------------------------------------------------- 5. 功能鍵 risk.flag
    c = _rf1109_ctx(b)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    stock(pg, "2330")
    reg = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, k = 'risk.flag', f = F.byId(k); const tier = (t) => P.tiers.find(x => x.key === t);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(x => x.kind === 'bool' && !x.adminOnly && x.cat !== 'grp' && !BAN.includes(x.id)).map(x => x.id);
        return { reg: f ? [f.kind, f.cat, !!f.limBy, !!f.route, !!f.metered, f.def] : null, lim: TwPerm.lim(k) === Infinity, can: TwPerm.can(k),
          feats: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats[k]), lims: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).lims[k] == null ? null : tier(t).lims[k]), ed: ed.includes(k),
          route: ['#stock/2330', '#watch', '#industry/group/foundry', '#overview'].map(h => f.route.test(h)) }; }""")
    ok(f"{T} risk.flag 登記（bool、全站工具、沒有 limBy、不計次、預設開）、四方案都開且不設次數、在體驗編輯清單、route 只含個股／自選／族群頁",
       reg["reg"] == ["bool", "global", False, True, False, True] and reg["lim"] and reg["can"] and reg["feats"] == [True] * 4 and reg["lims"] == [None] * 4 and reg["ed"]
       and reg["route"] == [True, True, True, False], reg)
    seen = 0
    miss = []
    for cd in ("2330", "2454", "3711", "2330", "2454", "3711"):
        if stock(pg, cd):
            seen += 1
        else:
            miss.append((cd, pg.evaluate("() => ({ dbg: TwRisk._dbg(), now: Date.now(), bar: !!document.getElementById('riskBar'), code: (document.querySelector('#skChartCard [data-lc]') || {}).dataset ? document.querySelector('#skChartCard [data-lc]').dataset.lc : null })")))
    ok(f"{T} 註冊會員連開 6 次有警示的個股頁都看得到（不計次、沒有上限可用完；體驗不需要「繼續看」）", seen == 6 and not pg.evaluate("() => !!document.querySelector('#riskBar [data-qlk], .qcov .qcard')"), (seen, miss))
    c.close()

    c = _rf1109_ctx(b, feats={"risk.flag": False})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    stock(pg, "2330", want=False)
    wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server'", 10000)
    pg.wait_for_timeout(600)
    off1 = pg.evaluate(_RF1109_BAR)
    pg.goto(base + "#watch", wait_until="domcontentloaded")
    wait_until(pg, "() => document.querySelectorAll('#wpTbl tr[data-go]').length >= 4", 20000)
    pg.wait_for_timeout(800)
    off2 = pg.evaluate("() => document.querySelectorAll('.rkb').length")
    pg.goto(base + "#industry/group/foundry", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('dgPick')", 30000)
    pg.wait_for_timeout(1500)
    off3 = pg.evaluate("() => !!document.getElementById('riskGrp')")
    ok(f"{T} 管理者把範本的 risk.flag 關掉 → 個股頁沒有警示條、自選沒有角標、族群頁沒有計數", off1 is None and off2 == 0 and not off3, (off1, off2, off3))
    c.close()

    c = _rf1109_ctx(b, who="admin", owner=True, feats={"risk.flag": False})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    ro = stock(pg, "2330")
    ok(f"{T} 站主（owner）不受範本影響：範本關掉也看得到警示條", bool(ro) and "處置中" in ro["txt"], ro)
    c.close()

    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("風險警示牌1109", lambda pg, b, base, code: t_risk_flag_1109(b, base, code))
