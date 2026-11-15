# 辦公室：角色被拎起丟到公司外「無業遊民區」（或被開除走到遊民區）之後，不准「狀態是走路、人卻原地不動」（2026-11-15）
#   根因：被丟出去落地後心情層讓他頭暈、暫停走路約 3.6～5 秒，但導演（afterDrop）／人事（life）在暫停期間就把路徑給了他 →
#   state 是 walk、速度 0，名牌與跟隨鏡頭都以為他在走。修法：暫停結束才給路徑（W.untilUnpaused）＋走路保底（walkguard.js）。
#   這一段用真滑鼠（長按 → 拖 → 放開）把新舊模型角色各丟 18 次到遊民區的各個角落（沒被開除的、被開除的輪流），
#   每次放開後把模擬往前推 14～18 秒（W.advanceAsync，逐 0.25 秒取樣），量：
#     · 走路狀態（state==walk、不算被你點選的設計性暫停）而 2 秒內位移 < 0.1 公尺的次數（含暫停）→ 必須 0
#     · 手上有路徑（沒被你點選）卻原地超過 10 秒的次數（含暫停）→ 必須 0
#     · 有多少次真的演到「頭暈」（knocked 場景）→ 至少 10 次，證明測試真的碰到事故條件
import os as _os
import random as _r

_MON = """() => { const W = __world; if (window.__hm) return; window.__hm = { ev: [], long: [], last2: {}, dizzy: 0, last: {}, sampled: 0, dz: new Set() };
  window.__hmAdv = async (sec) => { const n = Math.ceil(sec / 0.25);
    for (let i = 0; i < n; i++) { await W.advanceAsync(0.25); const t = W.time; __hm.sampled++;
      for (const c of W.chars.values()) { const id = c.spec.id, p = c.object3D.position, walking = c.state === 'walk' && !c._held, m = W.mind && W.mind.minds.get(id), scn = m && m.sc && m.sc.name;
        if (scn === 'knocked' && c._pause && !__hm.dz.has(id + ':' + Math.floor(t / 20))) { __hm.dz.add(id + ':' + Math.floor(t / 20)); __hm.dizzy++; }
        let L2 = __hm.last2[id];   // 第二道：不管暫停與否，只要手上有路徑（沒被你點選）原地 10 秒沒前進就算（暫停最久也不過頭暈那幾秒）
        if (!c._path || c._held || (W.attn && W.attn.current() === c)) __hm.last2[id] = null;
        else if (!L2 || Math.hypot(p.x - L2.x, p.z - L2.z) > 0.1) __hm.last2[id] = { t, x: p.x, z: p.z, rep: false };
        else if (t - L2.t > 10 && !L2.rep) { L2.rep = true; __hm.long.push({ id, t: +t.toFixed(1), pos: [+p.x.toFixed(2), +p.z.toFixed(2)], pause: !!c._pause, sc: scn || '', state: c.state }); }
        let L = __hm.last[id];
        if (!walking || (W.attn && W.attn.current() === c)) { __hm.last[id] = null; continue; }
        if (!L || Math.hypot(p.x - L.x, p.z - L.z) > 0.1) { __hm.last[id] = { t, x: p.x, z: p.z, rep: false }; continue; }
        if (t - L.t > 2 && !L.rep) { L.rep = true; const lastPt = c._path ? c._path[c._path.length - 1] : null;
          __hm.ev.push({ id, jobless: !!c.jobless, newModel: !!c.newModel, t: +t.toFixed(1), pos: [+p.x.toFixed(2), +p.z.toFixed(2)], last: lastPt && [+lastPt.x.toFixed(2), +lastPt.z.toFixed(2)], pause: !!c._pause, sc: scn || '', hr: !!c.hrBusy }); } } } }; }"""


def _hw_drop(pg, who, wx, wz):
    pg.evaluate("() => __world.setView('god', null, true)"); pg.wait_for_timeout(350)
    q = pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), cv = document.getElementById('cv'); if (!c || !(c._sx > 0)) return null;
      const k = cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd); return [c._sx, c._sy + k * 0.45 * (c.scale || 1)]; }""", who)
    if not q:
        return False
    tg = pg.evaluate("([x, z]) => { const W = __world, s = new W.THREE.Vector3(x, 1.05, z).project(W.camera); return [(s.x + 1) / 2 * innerWidth, (1 - s.y) / 2 * innerHeight]; }", [wx, wz])
    pg.mouse.move(q[0], q[1]); pg.mouse.down(); pg.wait_for_timeout(800); pg.mouse.move(q[0] + 8, q[1] - 8, steps=2); pg.wait_for_timeout(200)
    held = pg.evaluate(f"() => __world.chars.get('{who}').state") == "held"
    pg.mouse.move(tg[0], tg[1], steps=6); pg.wait_for_timeout(400); pg.mouse.up()
    return held


def t_hobowalk(b, base):
    n_per = int(_os.environ.get("HW_N", 18))        # 每種模型丟幾次（在職與待業輪流）；2 種模型 × 18 = 36 次
    rnd = _r.Random(20261115)
    c = b.new_context(viewport={"width": 1280, "height": 800})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.removeItem('aiOffice.hr.v1')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)[:200]))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    try:
        pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html?ambient=0&q=low&pr=0.5", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
        ok("遊民區走路：頁面載入", got)
        if not got:
            return
        pg.wait_for_timeout(800); pg.evaluate(_MON)
        pool = pg.evaluate("() => [...__world.chars.values()].filter(c => !c.spec.isCeo && !c.spec.pet && !c.away && c.state === 'sit').map(c => [c.spec.id, !!c.newModel])")
        new_ids = [i for i, n in pool if n]; old_ids = [i for i, n in pool if not n]
        ok(f"遊民區走路：新模型 {len(new_ids)} 位、舊模型 {len(old_ids)} 位可丟（各需 ≥ 4）", len(new_ids) >= 4 and len(old_ids) >= 4, (len(new_ids), len(old_ids)))
        Z = pg.evaluate("() => { const z = __world.outside.zone; return [z.x0, z.x1, z.z0, z.z1]; }")
        drops = held_n = 0; fails = []
        for kind, ids in (("新模型", new_ids), ("舊模型", old_ids)):
            ids = ids[:max(4, min(len(ids), 8)) // 2 * 2]
            # 後半先開除（placeInstant 直接放進遊民區，照真的開除流程的記錄），一半沒被開除；每個人輪流丟，直到丟滿 n_per 次（新模型只有幾位，所以會重複丟）
            half = len(ids) // 2; hired, fired = ids[:half], ids[half:]
            pg.evaluate("""(ids) => { const W = __world; for (const id of ids) { const c = W.chars.get(id); W.hr.fired.set(id, { id, at: Date.now(), reason: '', to: 'ceo', moved: [], nick: c.spec.nick, dept: c.spec.dept || '', zh: c.spec.zh || '' }); W.hr.placeInstant(c); } }""", fired)
            order = [(hired + fired)[k % len(ids)] if k % 2 == 0 else (fired + hired)[k % len(ids)] for k in range(n_per)]
            for who in order:
                x = rnd.uniform(Z[0] - 0.8, Z[1] + 1.2); z = rnd.uniform(Z[2] - 0.8, Z[3] + 0.4)
                h = _hw_drop(pg, who, x, z)
                drops += 1; held_n += 1 if h else 0
                if not h:
                    fails.append((kind, who, "沒被拎起來"))
                pg.evaluate("() => __hmAdv(15)")
        pg.evaluate("() => __hmAdv(20)")
        r = pg.evaluate("() => ({ ev: __hm.ev, long: __hm.long, dizzy: __hm.dizzy, sampled: __hm.sampled, guard: __world.walkGuard ? __world.walkGuard.stats : null, glog: __world.walkGuard ? __world.walkGuard.log.slice(-6) : [] })")
        print("    丟了", drops, "次，被拎起", held_n, "次，頭暈", r["dizzy"], "次，取樣", r["sampled"], "格，保底", r["guard"], flush=True)
        for e in r["ev"]:
            print("    卡住", e, flush=True)
        ok(f"遊民區走路：丟了 {drops} 次、其中 {held_n} 次真的被拎起來（≥ 30）", held_n >= 30, (drops, held_n, fails[:3]))
        ok(f"遊民區走路：其中 {r['dizzy']} 次演到頭暈（≥ 10，確認測到事故條件）", r["dizzy"] >= 10, r["dizzy"])
        ok(f"遊民區走路：「狀態走路卻 2 秒內位移 < 0.1 公尺」共 {len(r['ev'])} 次（必須 0）", len(r["ev"]) == 0, r["ev"][:4])
        ok(f"遊民區走路：手上有路徑卻原地超過 10 秒（含暫停）共 {len(r['long'])} 次（必須 0）", len(r["long"]) == 0, r["long"][:4])
        ok("遊民區走路：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


register("辦公室遊民區走路", lambda pg, b, base, code: t_hobowalk(b, base))
