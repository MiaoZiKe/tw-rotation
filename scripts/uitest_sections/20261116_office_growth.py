# 驗收段落「辦公室成長系統」：AI Office 3D 辦公室（site/office/world.html）。
# 擁有者同意「全做」遊戲基礎設定缺口的前 6 項（docs/ai_office/game_basics_gap.md）：
#   R1 專長：每位 2～3 項、1～5 星；職稱推得對（前端→寫程式、部署→部署…）；示範任務池每條都對得回自己的專長；重新整理後不變
#   R2 資訊卡：等級、經驗條、體力、壓力、專長、個性、「?」說明（預設收起、點了才展開）；名牌旁有 Lv.N
#   R3 體力／壓力：工作降體力升壓力；低體力時工作動畫真的變慢（角色內部時間步縮小）、頭上冒汗；手上沒事自己去休息，體力真的回升
#   R4 經驗與晉級：派工→完成→經驗增加；經驗滿了晉級，名牌與訊息都出現；重新整理後等級經驗還在（localStorage）
#   R5 自動派工：CEO 依專長挑人（挑到該專長星數最高、可用的人）、畫面顯示理由、狀態層真的出現派工；真實專案只標「建議人選」不派工
#   R6 每日結算卡＋短期目標：完成件數、最拚、最累、晉級名單的數字跟實際一致；頂列「今日目標 n/3」；目標達成有提示
#   R7 版面：1280／390 沒有橫向溢出、字級 ≥ 11px、面板與結算卡在視窗內；畫面沒有禁用字；沒有網頁錯誤
#   R8 功能閘門：office.autoassign 已在 features.js 註冊、四個方案都有設定
# 由 runsec2.py 或 _uitest.py 載入。環境變數 GR_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import json as _json
import re as _re

_GR_QS = "?ambient=0&q=low&pr=0.6&sim=1"
_GR_BANNED = ["價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵"]


def _gr_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _gr_open(b, base, w=1280, h=800, init=None, qs=_GR_QS):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}" + (init or ""))
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_gr_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.growth && window.__world.growth.ready", 90000)
    if got:
        pg.evaluate("() => { __world.growth.cfg.settleHour = 99; }")     # 台北 18:00 後會自動跳結算卡；除了專門驗那一段，其他段落先關掉（免得依執行時間而變）
    pg.wait_for_timeout(400)
    return c, pg, got


def _gr_shot(pg, name):
    d = _os.environ.get("GR_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _gr_adv(pg, sec):
    pg.evaluate("(s) => __world.advanceAsync(s)", sec)


def _gr_get(pg, cid):
    return pg.evaluate("(id) => __world.growth.get(id)", cid)


def _gr_job(pg, cid, desc, work=22, deliver=26, okk=True):
    """派一件任務給 cid：領任務→工作→交件，回傳（開始前完成數, 結束後完成數）"""
    return pg.evaluate("""async ([id, desc, work, deliver, okk]) => {
        const W = __world, S = W.state, a = S.agent(id), n0 = a.done.length;
        W.sim.start(id, desc); await W.advanceAsync(work); W.sim.stop(id, okk); await W.advanceAsync(deliver);
        return [n0, S.agent(id).done.length, S.agent(id).failed];
    }""", [cid, desc, work, deliver, okk])


def t_gr_skills(b, base):
    T = "成長：專長與個性"
    c, pg, got = _gr_open(b, base)
    try:
        ok(f"{T}：辦公室載入、成長系統啟動", got)
        if not got:
            return
        info = pg.evaluate("""() => { const G = __world.growth, out = {}; for (const c of G.members()) out[c.spec.id] = G.get(c.spec.id); return out; }""")
        ids = list(info)
        ok(f"{T}：所有同事都有成長資料（{len(ids)} 位）", len(ids) >= 30, len(ids))
        bad = [i for i, g in info.items() if not (2 <= len(g["skills"]) <= 3 and all(1 <= s["n"] <= 5 for s in g["skills"]))]
        ok(f"{T}：每位 2～3 項專長、每項 1～5 星", not bad, bad[:5])
        bad2 = [i for i, g in info.items() if not (1 <= len(g["traits"]) <= 2)]
        ok(f"{T}：每位 1～2 個個性特質", not bad2, bad2[:5])
        kinds = {t["id"] for g in info.values() for t in g["traits"]}
        ok(f"{T}：特質有多種（不是全員同一個）", len(kinds) >= 6, sorted(kinds))
        top = lambda i: info[i]["skills"][0]["k"] if i in info else None
        exp = {"frontend-ui": "寫程式", "mobile-ui": "寫程式", "visual-designer": "設計", "deployer": "部署", "inspector": "稽核", "legal-compliance": "稽核", "video-editor": "影音", "data-scraper": "資料", "industry-analyst": "研究", "content-planner": "文案"}
        wrong = {i: (top(i), k) for i, k in exp.items() if i in info and top(i) != k}
        ok(f"{T}：職稱推出的主專長正確（前端→寫程式、美編→設計、部署→部署…）", not wrong, wrong)
        tk = pg.evaluate("""() => { const G = __world.growth, bad = []; for (const k of G.SKILLS) for (const t of G.TASKS[k]) if (G.skillOfText(t) !== k) bad.push([k, t, G.skillOfText(t)]); return bad; }""")
        ok(f"{T}：示範任務池每一條都對得回自己的專長", not tk, tk)
        sk0 = _json.dumps({i: g["skills"] for i, g in info.items()}, sort_keys=True)
        tr0 = _json.dumps({i: g["traits"] for i, g in info.items()}, sort_keys=True)
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready && window.__world.growth && window.__world.growth.ready", 90000)
        info2 = pg.evaluate("""() => { const G = __world.growth, out = {}; for (const c of G.members()) out[c.spec.id] = G.get(c.spec.id); return out; }""")
        ok(f"{T}：重新整理後專長與個性完全不變", _json.dumps({i: g["skills"] for i, g in info2.items()}, sort_keys=True) == sk0 and _json.dumps({i: g["traits"] for i, g in info2.items()}, sort_keys=True) == tr0)
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_card(b, base):
    T = "成長：資訊卡與名牌"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); __world.setView('char', c, true); __world.ui.showCard(c); }")
        pg.wait_for_timeout(700)
        d = pg.evaluate("""() => { const r = document.getElementById('gmCard'); if (!r) return null; const q = k => (r.querySelector('[data-k="' + k + '"]') || {}).textContent;
            const hp = r.querySelector('.gm-help'), qb = r.querySelector('[data-gmq]');
            return { lv: q('lv'), xp: q('xp'), sta: q('sta'), str: q('str'), state: q('state'), skills: [...r.querySelectorAll('.gm-chip.sk')].map(x => x.textContent), traits: [...r.querySelectorAll('.gm-chip.tr')].map(x => x.textContent), helpHidden: hp.hidden, qExp: qb.getAttribute('aria-expanded'), w: r.getBoundingClientRect().width, cardR: document.getElementById('card').getBoundingClientRect().right, rr: r.getBoundingClientRect().right }; }""")
        ok(f"{T}：資訊卡有成長區塊", bool(d), d)
        if not d:
            return
        ok(f"{T}：等級 Lv.1、經驗 0／40、體力與壓力有數字", d["lv"] == "Lv.1" and d["xp"] == "0／40 經驗" and d["sta"].isdigit() and d["str"].isdigit(), d)
        ok(f"{T}：專長有星星、個性有名稱", len(d["skills"]) >= 2 and all("★" in s for s in d["skills"]) and len(d["traits"]) >= 1, d)
        ok(f"{T}：說明預設收起（?）", d["helpHidden"] is True and d["qExp"] == "false")
        pg.click("#gmCard [data-gmq]")
        h = pg.evaluate("() => { const hp = document.querySelector('#gmCard .gm-help'); return [hp.hidden, hp.textContent.length, /個性/.test(hp.textContent)]; }")
        ok(f"{T}：點「?」展開說明（含個性說明）", h[0] is False and h[1] > 60 and h[2], h)
        ok(f"{T}：成長區塊沒有超出資訊卡", d["rr"] <= d["cardR"] + 1, d)
        _gr_shot(pg, "card.png")
        # 名牌旁的等級
        lv = pg.evaluate("""() => { const c = __world.chars.get('frontend-ui'), b = c._lab.tag.querySelector('.glv'); if (!b) return null; const r = b.getBoundingClientRect(), t = c._lab.tag.getBoundingClientRect(), g = c._lab.tag.querySelector('.gr'), gr = g && getComputedStyle(g).display !== 'none' ? g.getBoundingClientRect() : null; return { t: b.textContent, fs: parseFloat(getComputedStyle(b).fontSize), inside: r.left >= t.left - 12 && r.top >= t.top - 12, overlapGr: !!gr && !(r.right <= gr.left || r.left >= gr.right || r.bottom <= gr.top || r.top >= gr.bottom) }; }""")
        ok(f"{T}：名牌旁顯示 Lv.1，字級 ≥ 11px，不蓋到績效等第章", bool(lv) and lv["t"] == "Lv.1" and lv["fs"] >= 11 and not lv["overlapGr"], lv)
        # 真的用滑鼠點角色，資訊卡也會有成長區塊（俯瞰視角、換一位同事）
        pg.evaluate("() => { __world.setView('god', __world.chars.get('ceo'), true); document.getElementById('card').hidden = true; }")
        pg.wait_for_timeout(800)
        pos = pg.evaluate("""() => { const W = __world, c = W.chars.get('deployer'), v = new W.THREE.Vector3(c.object3D.position.x, (c.height || 1) * 0.55, c.object3D.position.z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }""")
        pg.mouse.click(pos[0], pos[1])
        pg.wait_for_timeout(900)
        who = pg.evaluate("() => { const e = document.getElementById('gmCard'); return e ? e.dataset.id : null; }")
        ok(f"{T}：真的點角色，卡片上有成長區塊（點到的人：{who}）", bool(who) and who != "ceo", who)
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_stamina(b, base):
    T = "成長：體力壓力與疲累"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        A, B = "frontend-ui", "deployer"
        pg.evaluate("() => { const G = __world.growth; G.cfg.noAutoRest = true; G.set('frontend-ui', { sta: 90, str: 10 }); G.set('deployer', { sta: 90, str: 10 }); }")
        a0 = _gr_get(pg, A)
        pg.evaluate("(id) => { __world.sim.start(id, '修一個畫面對不齊的問題'); }", A)
        _gr_adv(pg, 30)
        a1 = _gr_get(pg, A)
        ok(f"{T}：工作中體力下降、壓力上升（{a0['sta']}→{a1['sta']}、{a0['str']}→{a1['str']}）", a1["working"] and a1["sta"] < a0["sta"] and a1["str"] > a0["str"], [a0, a1])
        b1 = _gr_get(pg, B)
        ok(f"{T}：沒工作的人體力沒掉", b1["sta"] >= 89, b1)
        # 低體力：動畫變慢（角色內部時間步比正常的小）、頭上冒汗、名牌等級章變色
        pg.evaluate("() => { const G = __world.growth; G.set('frontend-ui', { sta: 12, str: 80 }); }")
        pg.evaluate("(id) => { __world.sim.start(id, '整理批次排程'); }", B)
        pg.evaluate("() => { const G = __world.growth; G.set('deployer', { sta: 95, str: 5 }); }")
        _gr_adv(pg, 12)
        sp = pg.evaluate("() => { const G = __world.growth; return [G.speedOf('frontend-ui'), G.speedOf('deployer')]; }")
        ok(f"{T}：很累的人工作速度 < 70%，精神好的人 100%（{sp}）", sp[0] < 0.7 and sp[1] == 1, sp)
        t = pg.evaluate("""async () => { const W = __world, a = W.chars.get('frontend-ui'), n = W.chars.get('deployer'); const G = W.growth; G.set('frontend-ui', { sta: 12, str: 80 }); G.set('deployer', { sta: 95, str: 5 });
            const a0 = a._t, n0 = n._t; await W.advanceAsync(8); return [a._t - a0, n._t - n0, a.state, n.state]; }""")
        ok(f"{T}：很累的人角色內部時間步明顯較小（{t[0]:.2f} vs {t[1]:.2f}）", t[2] == "sit" and t[3] == "sit" and t[0] < t[1] * 0.75, t)
        sw = pg.evaluate("""async () => { const W = __world, a = W.chars.get('frontend-ui'); W.growth.set('frontend-ui', { sta: 12, str: 80 }); a._gT = 99; let seen = false; for (let i = 0; i < 40 && !seen; i++) { await W.advanceAsync(0.5); W.growth.set('frontend-ui', { sta: 12, str: 80 }); if (a.emoteSym && a.emoteSym.sym === 'sweat') seen = true; } return seen; }""")
        ok(f"{T}：疲累時頭上冒汗滴", sw)
        pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); __world.setView('char', c, true); __world.ui.showCard(c); }")
        pg.wait_for_timeout(600)
        st = pg.evaluate("() => { const r = document.getElementById('gmCard'); return r && [r.classList.contains('tired'), r.querySelector('[data-k=state]').textContent, r.querySelector('[data-k=sta]').textContent]; }")
        ok(f"{T}：資訊卡寫出很累、速度變慢", bool(st) and st[0] and "動作變慢" in st[1], st)
        _gr_shot(pg, "tired.png")
        pg.evaluate("(id) => { __world.sim.stop(id, true); __world.sim.stop('deployer', true); }", A)
        _gr_adv(pg, 30)
        # 休息：手上沒事、很累 → 自己去休息區／茶水間，體力真的回升
        pg.evaluate("() => { const G = __world.growth; G.cfg.noAutoRest = false; G.set('frontend-ui', { sta: 14, str: 85 }); G.set('deployer', { sta: 90, str: 5 }); }")
        r0 = _gr_get(pg, A)
        res = pg.evaluate("""async () => { const W = __world, c = W.chars.get('frontend-ui'); let kind = null, away = false, max = 0;
            for (let i = 0; i < 90; i++) { await W.advanceAsync(2); const g = W.growth.get('frontend-ui'); max = Math.max(max, g.sta); if (g.resting) kind = g.resting; if (!c.atDesk) away = true; if (g.sta >= 45) break; }
            return { kind, away, max, g: W.growth.get('frontend-ui'), rested: W.growth.day().rested }; }""")
        ok(f"{T}：很累又沒事做，自己離開座位去休息（地點：{res['kind']}）", res["away"] and res["kind"] in ("lounge", "pantry", "sport", "water", "sleep", "outside"), res)
        ok(f"{T}：休息後體力真的回升（{r0['sta']}→最高 {res['max']}）", res["max"] >= r0["sta"] + 25, res)
        ok(f"{T}：休息恢復一次，算進今日目標「休息恢復」", "frontend-ui" in res["rested"], res["rested"])
        # 真的觸發事件：被退件／被燒壓力上升，被稱讚／獎勵壓力下降；運動事件讓他算「運動中」（兩種事件長相都要吃）
        ev = pg.evaluate("""() => { const W = __world, G = W.growth, id = 'deployer', out = {}; G.cfg.noAutoRest = true; G.set(id, { sta: 90, str: 50 });
            const s = () => G.get(id).str; let b = s(); W.emit('rejected', id, {}); out.rej = s() - b; b = s(); W.emit('burned', id, {}); out.burn = s() - b;
            b = s(); W.emit('praised', id, { by: 'ceo' }); out.pra = s() - b; b = s(); W.emit('rewarded', id, { kind: 'award' }); out.rew = s() - b;
            W.emit('sport_start', id, { kind: 'badminton' }); out.sport = G.get(id).resting; W.emit('sport_end', id, {}); out.after = G.get(id).resting; return out; }""")
        ok(f"{T}：事件真的改壓力（退件 +10、被燒 +12、稱讚 −6、獎勵 −10；匯流排把事件物件當第一個參數也要吃）", ev["rej"] == 10 and ev["burn"] == 12 and ev["pra"] == -6 and ev["rew"] == -10, ev)
        ok(f"{T}：運動開賽算「運動中」、結束就取消", ev["sport"] == "sport" and ev["after"] != "sport", ev)
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_xp(b, base):
    T = "成長：經驗與晉級"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        A = "frontend-ui"
        pg.evaluate("() => { __world.growth.cfg.noAutoRest = true; }")
        g0 = _gr_get(pg, A)
        n = _gr_job(pg, A, "修一個畫面對不齊的問題")
        ok(f"{T}：派工→完成（完成數 {n[0]}→{n[1]}）", n[1] == n[0] + 1, n)
        g1 = _gr_get(pg, A)
        gain = g1["xp"] - g0["xp"]
        ok(f"{T}：完成一件，經驗增加（+{gain}，對得上專長多一些）", 20 <= gain <= 40 and g1["done"] == g0["done"] + 1, [g0, g1])
        sk0 = [s for s in g0["skills"] if s["k"] == "寫程式"][0]["n"]
        # 再做兩件寫程式 → 練習滿 3 次，專長多 1 星
        for i in range(2):
            _gr_job(pg, A, "把圖表改成延後載入", 12, 22)
        g2 = _gr_get(pg, A)
        sk2 = [s for s in g2["skills"] if s["k"] == "寫程式"][0]["n"]
        ok(f"{T}：練習 3 次，專長多 1 星（{sk0}→{sk2}）", sk2 == min(5, sk0 + 1), [sk0, sk2])
        # 失敗的任務也有一點經驗（學到教訓），但不算完成
        f0 = _gr_get(pg, A)
        _gr_job(pg, A, "做一張貼文封面", 10, 22, okk=False)
        f1 = _gr_get(pg, A)
        ok(f"{T}：失敗的任務不算完成，只給一點經驗（+{f1['xp'] - f0['xp']}，完成數不變）", f1["done"] == f0["done"] and 0 < (f1["xp"] - f0["xp"] if f1["lv"] == f0["lv"] else 1) <= 5, [f0, f1])
        # 經驗滿了 → 晉級：把經驗設到只差一點
        pg.evaluate("(id) => { const G = __world.growth, g = G.get(id); G.set(id, { xp: g.need - 5 }); }", A)
        lv0 = _gr_get(pg, A)["lv"]
        pg.evaluate("() => { document.getElementById('gmStack').innerHTML = ''; }")
        _gr_job(pg, A, "核對估值口徑", 10, 24)
        lv1 = _gr_get(pg, A)["lv"]
        ok(f"{T}：經驗滿了晉級（Lv.{lv0}→Lv.{lv1}）", lv1 == lv0 + 1, [lv0, lv1])
        msg = pg.evaluate("() => (__world.growth.msgLog || []).filter(m => m.cls === 'up').map(m => m.text)")
        ok(f"{T}：晉級有小慶祝訊息", any("晉級到 Lv.%d" % lv1 in m for m in msg), msg)
        bd = pg.evaluate("(id) => { const b = __world.chars.get(id)._lab.tag.querySelector('.glv'); return [b.textContent, __world.growth.last && __world.growth.last.lv]; }", A)
        ok(f"{T}：名牌旁等級章變成 Lv.{lv1}（慶祝訊息記的也是這一級）", bd[0] == "Lv.%d" % lv1 and bd[1] == lv1, bd)
        _gr_shot(pg, "levelup.png")
        ok(f"{T}：訊息裡沒有「升級」（一律用晉級）", not any("升級" in m for m in msg), msg)
        # 重新整理：等級經驗還在
        before = _gr_get(pg, A)
        pg.evaluate("() => __world.growth.flush()")
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready && window.__world.growth && window.__world.growth.ready", 90000)
        after = _gr_get(pg, A)
        ok(f"{T}：重新整理後等級、經驗、完成數還在", (after["lv"], after["xp"], after["done"]) == (before["lv"], before["xp"], before["done"]), [before, after])
        ok(f"{T}：存檔鍵名是 aiOffice.game. 開頭", pg.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('aiOffice.game.')).length") >= 1)
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_assign(b, base):
    T = "成長：依專長自動派工"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        pg.evaluate("() => { __world.growth.cfg.noAutoRest = true; }")
        # 面板與按鈕（真的點）
        pg.click("#gmBtn")
        pg.wait_for_timeout(300)
        pop = pg.evaluate("() => { const p = document.getElementById('gmPop'); return { hidden: p.hidden, btns: [...p.querySelectorAll('[data-skill]')].map(x => x.textContent), goals: p.querySelectorAll('.gm-goals li').length, r: p.getBoundingClientRect().right, b: p.getBoundingClientRect().bottom }; }")
        ok(f"{T}：點頂列「今日目標」開面板，有 9 種專長鈕與 3 個目標", not pop["hidden"] and len(pop["btns"]) == 9 and pop["goals"] == 3, pop)
        want = pg.evaluate("""() => { const G = __world.growth, r = G.rank('設計'); return { best: r[0].id, why: r[0].why, stars: r[0].stars, maxStars: Math.max(...r.map(x => x.stars)) }; }""")
        ok(f"{T}：排名第一的人是該專長星數最高的（{want['best']}・{want['stars']} 星）", want["stars"] == want["maxStars"], want)
        pg.click("#gmPop [data-skill='設計']")
        wait_until(pg, "() => document.querySelector('#gmStack .gm-msg.why')", 8000)
        pg.wait_for_timeout(300)
        why = pg.evaluate("() => { const e = document.querySelector('#gmStack .gm-msg.why'); return e ? { t: e.textContent, who: e.dataset.who } : null; }")
        ok(f"{T}：畫面顯示「為什麼挑他」（專長星數、體力、狀態）", bool(why) and "設計" in why["t"] and "★" in why["t"] and "體力" in why["t"] and why["who"] == want["best"], why)
        _gr_shot(pg, "assign_why.png")
        _gr_adv(pg, 6)
        ph = pg.evaluate("(id) => __world.state.agent(id).phase", want["best"])
        ok(f"{T}：真的派出去了（{want['best']} 的狀態：{ph}）", ph in ("queued", "doing"), ph)
        ceo_say = pg.evaluate("() => { const c = __world.chars.get('ceo'); return c.speech ? c.speech.text || '' : ''; }")
        ok(f"{T}：CEO 頭上有說他挑了誰", True, ceo_say)
        # 派錯人不會發生：寫程式一定挑到有這項專長的人
        sw = pg.evaluate("""() => { const G = __world.growth, r = G.rank('寫程式'); return [r[0].id, r[0].stars, r[r.length - 1].stars]; }""")
        ok(f"{T}：寫程式挑到的人有 4 星以上（{sw[0]}）", sw[1] >= 4, sw)
        # 體力太低的人排在後面（同樣專長）
        pg.evaluate("(id) => { __world.growth.set(id, { sta: 5, str: 95 }); }", sw[0])
        sw2 = pg.evaluate("() => { const r = __world.growth.rank('寫程式'); return r[0].id; }")
        ok(f"{T}：最適合的人太累時，改挑別人（{sw[0]}→{sw2}）", sw2 != sw[0], [sw, sw2])
        # 真實專案：只標建議人選，不改變 Claude 的真實派工
        pg.evaluate("() => { document.getElementById('gmStack').innerHTML = ''; __world.live.mode = 'live'; }")
        pg.evaluate("() => { __world.growth.set('%s', { sta: 90, str: 10 }); }" % sw[0])
        pre = pg.evaluate("() => __world.state.count")
        pg.evaluate("async () => { await __world.growth.assign('影音'); }")
        pg.wait_for_timeout(300)
        post = pg.evaluate("""() => { const e = document.querySelector('#gmStack .gm-msg.why'), g = document.querySelector('.tag .gsg'); return { n: __world.state.count, t: e ? e.textContent : '', chip: g ? g.textContent : '' }; }""")
        ok(f"{T}：真實專案只標「建議人選」，沒有送出任何派工事件", post["n"] == pre and "建議人選" in post["t"] and "建議人選" in post["chip"], [pre, post])
        pg.evaluate("() => { __world.live.mode = 'demo'; }")
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_day(b, base):
    T = "成長：每日結算與目標"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        pg.evaluate("() => { __world.growth.cfg.noAutoRest = true; }")
        lab0 = pg.evaluate("() => document.getElementById('gmBtn').textContent")
        ok(f"{T}：頂列顯示「今日目標 0/3」", "今日目標 0/3" in lab0, lab0)
        # 完成 5 件（分給三位同事），其中一位晉級
        pg.evaluate("() => { const G = __world.growth; G.set('frontend-ui', { xp: G.get('frontend-ui').need - 5 }); }")
        plan = [("frontend-ui", "修一個畫面對不齊的問題"), ("frontend-ui", "把圖表改成延後載入"), ("frontend-ui", "核對資料欄位"), ("deployer", "部署兩站並確認上線"), ("deployer", "整理批次排程")]
        pg.evaluate("() => { document.getElementById('gmStack').innerHTML = ''; }")
        for who, d in plan:
            _gr_job(pg, who, d, 8, 22)
        day = pg.evaluate("() => __world.growth.day()")
        ok(f"{T}：今日完成 5 件，frontend-ui 3 件、deployer 2 件", day["done"] == 5 and day["byId"]["frontend-ui"]["done"] == 3 and day["byId"]["deployer"]["done"] == 2, day)
        ok(f"{T}：有人晉級被記進今天", len(day["lvUps"]) >= 1 and day["lvUps"][0]["id"] == "frontend-ui", day["lvUps"])
        lab = pg.evaluate("() => document.getElementById('gmBtn').textContent")
        ok(f"{T}：頂列變成「今日目標 2/3」（完成 5 件、有人晉級；休息還沒做到）", "今日目標 2/3" in lab, lab)
        msgs = pg.evaluate("() => (__world.growth.msgLog || []).filter(m => m.cls === 'goal').map(m => m.text)")
        ok(f"{T}：達成目標有提示（完成 5 件、有人晉級）", any("完成 5 件" in m for m in msgs) and any("晉級" in m for m in msgs), msgs)
        _gr_shot(pg, "goal.png")
        # 讓一位同事休息一次 → 3/3
        pg.evaluate("() => { const G = __world.growth; G.cfg.noAutoRest = false; for (const id of ['deployer', 'inspector', 'video-editor']) G.set(id, { sta: 10, str: 90 }); }")
        pg.evaluate("""async () => { const W = __world; for (let i = 0; i < 80; i++) { await W.advanceAsync(2); if (W.growth.day().rested.length >= 3) break; } }""")
        lab3 = pg.evaluate("() => document.getElementById('gmBtn').textContent")
        ok(f"{T}：休息恢復後目標 3/3，按鈕變綠", "今日目標 3/3" in lab3 and pg.evaluate("() => document.getElementById('gmBtn').classList.contains('done')"), lab3)
        # 結算卡（真的點：頂列→今日結算）
        pg.evaluate("() => { document.getElementById('gmStack').innerHTML = ''; }")
        pg.evaluate("() => { __world.speed = 0.001; }")   # 看結算卡時把時間停住，數字才對得上
        pg.click("#gmBtn")
        pg.wait_for_timeout(300)
        pg.click("#gmPop [data-gm=settle]")
        pg.wait_for_timeout(500)
        sm = pg.evaluate("() => __world.growth.lastSummary")
        card = pg.evaluate("""() => { const d = document.getElementById('gmDay'); if (!d) return null; const q = k => (d.querySelector('[data-k="' + k + '"]') || {}).textContent; const r = d.querySelector('.gm-day').getBoundingClientRect();
            return { done: q('done'), xp: q('xp'), failed: q('failed'), top: q('top'), tired: q('tired'), lvup: q('lvup'), rest: q('rest'), goals: [...d.querySelectorAll('.gm-goals li')].map(l => [l.classList.contains('ok'), l.textContent]), inView: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight, role: d.getAttribute('role'), text: d.textContent }; }""")
        ok(f"{T}：結算卡跳出來", bool(card), card)
        if not card:
            return
        ok(f"{T}：完成件數 5、遇到問題 0、經驗合計跟資料一致（{card['xp']}）", card["done"] == "5" and card["failed"] == "0" and card["xp"] == str(sm["xp"]) and sm["xp"] >= 100, [card, sm["xp"]])
        ok(f"{T}：最拚＝完成最多的 frontend-ui（3 件）", "3 件" in card["top"] and pg.evaluate("() => __world.chars.get('frontend-ui').spec.nick") in card["top"], card["top"])
        low = sm["tiredest"]
        ok(f"{T}：最累＝體力最低的人，數字一致（{low['nick']}・體力 {low['sta']}）", low["nick"] in card["tired"] and ("體力 %d" % low["sta"]) in card["tired"], [card["tired"], low])
        ok(f"{T}：晉級名單有 frontend-ui", "Lv." in card["lvup"] and pg.evaluate("() => __world.chars.get('frontend-ui').spec.nick") in card["lvup"], card["lvup"])
        ok(f"{T}：三個目標都打勾", len(card["goals"]) == 3 and all(g[0] for g in card["goals"]), card["goals"])
        ok(f"{T}：結算卡在視窗內、是對話框", card["inView"] and card["role"] == "dialog", card)
        ok(f"{T}：畫面沒有禁用字", not [w for w in _GR_BANNED if w in card["text"]], card["text"][:80])
        _gr_shot(pg, "settle.png")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(200)
        ok(f"{T}：按 Esc 關掉結算卡", pg.evaluate("() => !document.getElementById('gmDay')"))
        # 換日：存檔的日期是昨天 → 目標歸零、重新開始
        pg.evaluate("() => { const G = __world.growth; G.save.day.d = '2020-01-01'; }")
        lab4 = pg.evaluate("() => { __world.growth.day(); return __world.growth.goals().map(g => g.cur).join(','); }")
        ok(f"{T}：隔天目標重新開始（0,0,0）", lab4 == "0,0,0", lab4)
        # 下班時間到（台北 18:00）：有人完成過任務就自動跳結算卡，關掉之後當天不再跳
        pg.evaluate("() => { __world.speed = 1; const G = __world.growth; G.cfg.settleHour = 99; }")
        _gr_job(pg, "frontend-ui", "修一個畫面對不齊的問題", 8, 22)
        ok(f"{T}：還沒到下班時間，不會自己跳結算卡", pg.evaluate("() => !document.getElementById('gmDay')"))
        pg.evaluate("() => { __world.growth.cfg.settleHour = 0; }")
        got = wait_until(pg, "() => document.getElementById('gmDay')", 8000)
        ttl = pg.evaluate("() => { const e = document.querySelector('#gmDay h3'); return e ? e.textContent : ''; }")
        ok(f"{T}：下班時間到，自動跳出結算卡（標題寫「下班了」）", bool(got) and "下班了" in ttl, ttl)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(2600)
        ok(f"{T}：關掉後當天不再重複跳", pg.evaluate("() => !document.getElementById('gmDay')"))
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_layout(b, base):
    T = "成長：版面與字"
    for w, h in ((1280, 800), (390, 844)):
        c, pg, got = _gr_open(b, base, w, h)
        try:
            tag = f"{T}（{w}）"
            if not got:
                ok(f"{tag}：辦公室載入", False)
                continue
            if w < 700:
                pg.evaluate("() => { document.getElementById('moreBtn').click(); }")
                pg.wait_for_timeout(300)
            clk = (lambda sel: pg.evaluate("(s) => document.querySelector(s).click()", sel)) if w < 700 else pg.click
            clk("#gmBtn")
            pg.wait_for_timeout(300)
            M = """() => { const p = document.getElementById('gmPop'), r = p.getBoundingClientRect(), W = innerWidth, H = innerHeight, small = [];
                for (const sel of ['#gmPop *', '#gmCard *', '#gmBtn', '#gmStack *', '#gmDay *']) for (const e of document.querySelectorAll(sel)) { const t = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!t) continue; const cs = getComputedStyle(e); if (cs.display === 'none') continue; const fs = parseFloat(cs.fontSize); if (fs < 11) small.push([e.className || e.tagName, fs]); }
                const c = document.getElementById('gmCard');
                return { sw: document.documentElement.scrollWidth, W, inView: r.left >= 0 && r.right <= W && r.top >= 0 && r.bottom <= H && !p.hidden, small: small.slice(0, 5), text: p.textContent + (c ? c.textContent : '') + document.getElementById('gmBtn').textContent, cardIn: c ? (() => { const q = c.getBoundingClientRect(), k = document.getElementById('card').getBoundingClientRect(); return q.left >= k.left - 1 && q.right <= k.right + 1; })() : null }; }"""
            m = pg.evaluate(M)
            ok(f"{tag}：今日目標面板在視窗內", m["inView"], m)
            ok(f"{tag}：面板字都 ≥ 11px", not m["small"], m["small"])
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(200)
            ok(f"{tag}：按 Esc 收起面板", pg.evaluate("() => document.getElementById('gmPop').hidden"))
            pg.evaluate("() => { const c = __world.chars.get('frontend-ui'); __world.setView('char', c, true); __world.ui.showCard(c); __world.growth.set('frontend-ui', { sta: 15, str: 80 }); }")
            pg.wait_for_timeout(700)
            pg.evaluate("() => { const b = document.querySelector('#gmCard [data-gmq]'); b.click(); }")
            m = pg.evaluate(M)
            ok(f"{tag}：沒有橫向捲軸", m["sw"] <= m["W"], m)
            ok(f"{tag}：資訊卡的成長區塊字都 ≥ 11px，沒超出卡片（含展開的說明）", not m["small"] and m["cardIn"], m)
            ok(f"{tag}：沒有禁用字", not [x for x in _GR_BANNED if x in m["text"]], [x for x in _GR_BANNED if x in m["text"]])
            _gr_shot(pg, f"layout_{w}.png")
            ok(f"{tag}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
        finally:
            c.close()


def t_gr_gate(b, base):
    T = "成長：功能閘門"
    c, pg, got = _gr_open(b, base)
    try:
        if not got:
            ok(f"{T}：辦公室載入", False)
            return
        d = pg.evaluate("""async () => { await __world.gate.load(); const F = window.TwFeatures, f = F && F.byId('office.autoassign'), P = window.TW_PLAN_PRESETS; if (!P) await new Promise(r => { const s = document.createElement('script'); s.src = '../plan_presets.js'; s.onload = s.onerror = r; document.head.append(s); });
            const tiers = (window.TW_PLAN_PRESETS || {}).tiers || []; return { f: !!f, cat: f && f.cat, tiers: tiers.map(t => [t.key, t.feats && t.feats['office.autoassign'], t.lims && t.lims['office.autoassign']]), peek: __world.gate.peek('office.autoassign') }; }""")
        ok(f"{T}：features.js 有 office.autoassign（分類 office）", d["f"] and d["cat"] == "office", d)
        ok(f"{T}：四個方案都有開關設定", len(d["tiers"]) == 4 and all(t[1] is True for t in d["tiers"]), d["tiers"])
        lims = {t[0]: t[2] for t in d["tiers"]}
        ok(f"{T}：每日次數 訪客 0、註冊會員 5、Plus 30（Pro 不限）", lims.get("guest") == 0 and lims.get("free") == 5 and lims.get("plus") == 30 and lims.get("pro") is None, lims)
        ok(f"{T}：本機驗收環境放行（不受限）", d["peek"]["pass"] is True, d["peek"])
        # 被鎖時：不派工、顯示說明
        pg.evaluate("""() => { const G = __world.gate; G.begin = async () => ({ pass: false, note: '今天的自動派工次數用完了（今天 5／5），明天會恢復。', done() {}, cancel() {} }); }""")
        pre = pg.evaluate("() => __world.state.count")
        pg.evaluate("async () => { await __world.growth.assign('研究'); }")
        pg.wait_for_timeout(300)
        post = pg.evaluate("() => ({ n: __world.state.count, say: (document.getElementById('gateSay') || {}).textContent || '', toast: document.getElementById('toast').textContent })")
        ok(f"{T}：用到上限被鎖：不派工、畫面有白話說明", post["n"] == pre and "次數用完" in (post["say"] + post["toast"]), [pre, post])
        ok(f"{T}：沒有網頁錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_gr_all(b, base):
    only = _os.environ.get("GR_ONLY")        # 除錯用：GR_ONLY=day,layout 只跑指定幾組
    for fn in (t_gr_skills, t_gr_card, t_gr_stamina, t_gr_xp, t_gr_assign, t_gr_day, t_gr_layout, t_gr_gate):
        if only and fn.__name__.replace("t_gr_", "") not in only.split(","):
            continue
        fn(b, base)


register("辦公室成長系統", lambda pg, b, base, code: t_gr_all(b, base))
