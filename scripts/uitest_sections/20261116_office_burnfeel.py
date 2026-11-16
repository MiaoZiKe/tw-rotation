# 驗收段落「辦公室被燒情緒細節」：AI Office 3D 辦公室（site/office/world.html）。
# 擁有者原話：「被燒到應該是有夠多掙扎還有情緒，燒完後也是，細節需要多點。」分鏡表 docs/ai_office/burn_storyboard.md
#   B1 著火當下：兩種個性（慌張亂跑／原地跳腳）真滑鼠丟進營火；掙扎至少 4 種動作／台詞、亂跑距離 > 1.5 公尺、同事圍過來關心（不嘲笑）
#   B2 熄火瞬間：大口喘氣；燒焦期：咳嗽、拍灰、看著自己難過、兩種個性的情緒小段不同
#   B3 恢復與之後：走路變慢（一拐一拐）、洗乾淨換裝的小儀式、之後繞火、看到你拎人會緊張
#   B4 附近有泳池：被點燃的人衝向泳池、入水熄火
# 由 runsec2.py 或 _uitest.py 載入。環境變數 BURN_SHOTS 指到資料夾時，順便存各階段截圖。
# flake8: noqa

import os as _os

_BF_QS = "?ambient=0&q=low&pr=0.6&sim=1"


def _bf_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _bf_open(b, base, w=1280, h=800):
    c = b.new_context(viewport={"width": w, "height": h})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_bf_root(base) + "/office/world.html" + _BF_QS, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.mind && window.__world.mind.feel", 90000)
    pg.wait_for_timeout(500)
    return c, pg, got


def _bf_shot(pg, name):
    d = _os.environ.get("BURN_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _bf_get(pg, cid):
    return pg.evaluate("(id) => __world.mind.get(id)", cid)


def _bf_adv(pg, sec):
    pg.evaluate("(s) => __world.advanceAsync(s)", sec)


def _bf_log(pg, cid, event):
    return pg.evaluate("([id, ev]) => __world.mind.log.filter(x => x.id === id && x.event === ev)", [cid, event])


def _bf_pick(pg, cond_js, skip=()):
    return pg.evaluate("""([cond, skip]) => { const f = eval(cond); for (const [id, c] of __world.chars) { if (c.spec.pet || c.spec.isCeo || c.jobless || c.away || c.sleeping || skip.includes(id)) continue; const g = __world.mind.get(id); if (g && f(g.traits, c)) return id; } return null; }""", [cond_js, list(skip)])


def _bf_make(pg, cond_js, traits, skip=()):
    cid = _bf_pick(pg, cond_js, skip)
    if cid:
        return cid, False
    cid = _bf_pick(pg, "(t) => true", skip)
    pg.evaluate("([id, t]) => { Object.assign(__world.mind.mindOf(id).t, t); }", [cid, traits])
    return cid, True


def _bf_proj(pg, cid):
    return pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), v = new W.THREE.Vector3(c.object3D.position.x, (c.height || 1) * 0.55 + (c.lift || 0), c.object3D.position.z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }""", cid)


def _bf_fire_proj(pg):
    return pg.evaluate("""() => { const W = __world, v = new W.THREE.Vector3(30.2, 0.6, 36.6).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }""")


def _bf_stage(pg, cid, x, z):
    pg.evaluate("""([id, x, z]) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c.standAt(x, z, 0); W.fire.states.delete(id); W.speed = 1; }""", [cid, x, z])


def _bf_throw_fire(pg, cid):
    cx, cy = _bf_proj(pg, cid)
    fx, fy = _bf_fire_proj(pg)
    fx, fy = fx + (fx - cx) * 0.5, fy + (fy - cy) * 0.5
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    pg.wait_for_timeout(700)
    for i in range(1, 9):
        pg.mouse.move(cx + (fx - cx) * i / 8, cy + (fy - cy) * i / 8)
        pg.wait_for_timeout(16)
    held = pg.evaluate("(id) => __world.chars.get(id).state === 'held'", cid)
    pg.mouse.up()
    return held


_BF_STEP = """async ([ids, n, dt]) => { const W = __world, out = {}; for (const id of ids) out[id] = { pos: [], face: [], act: [], st: [] };
  for (let i = 0; i < n; i++) { await W.advanceAsync(dt); for (const id of ids) { const c = W.chars.get(id), p = c.object3D.position, o = out[id]; o.pos.push([p.x, p.z]); o.face.push(c.expression); o.act.push(c.action); o.st.push(W.fire.stateOf(c).state); } }
  return out; }"""


def _bf_path(pos):
    t = 0.0
    for i in range(1, len(pos)):
        t += ((pos[i][0] - pos[i - 1][0]) ** 2 + (pos[i][1] - pos[i - 1][1]) ** 2) ** 0.5
    return t


def t_bf_burn(b, base):
    c1, pg, got = _bf_open(b, base)
    if not ok("被燒細節：世界載入、情緒層建立", got):
        c1.close(); return
    A, fA = _bf_make(pg, "(t) => t.sens >= .55 && t.ext >= .45 && t.comp < .6", {"sens": .8, "ext": .7, "comp": .3, "opt": .35})
    B, fB = _bf_make(pg, "(t) => t.sens < .45 && t.opt >= .55 && t.ext < .5 && t.comp < .5", {"sens": .3, "ext": .3, "comp": .4, "opt": .8}, skip=(A,))
    Ws = []
    for _ in range(3):
        Ws.append(_bf_pick(pg, "(t) => true", skip=tuple([A, B] + Ws)))
    pg.evaluate("() => { __world.fire.reset(); __world.phys.restoreAll(true); __world.daytime.set('day'); }")
    for cid, x, z in ((A, 26.5, 35.0), (B, 26.5, 37.6), (Ws[0], 25.0, 33.2), (Ws[1], 24.2, 39.0), (Ws[2], 28.5, 40.2)):
        _bf_stage(pg, cid, x, z)
    for w in Ws:
        pg.evaluate("(id) => { const c = __world.chars.get(id); c.busy = false; }", w)
    pg.evaluate("() => { __world.godAt(30.2, 36.4, 26); }")
    wait_until(pg, "() => !__world.view.tween", 20000)
    pg.wait_for_timeout(1200)
    held, S = {}, {}
    shots = {5: "被燒細節_1驚叫", 18: "被燒細節_2掙扎", 36: "被燒細節_3求救逃開"}
    for cid, tagn in ((A, "A"), (B, "B")):
        pg.evaluate("() => { __world.speed = 1; }")
        held[cid] = _bf_throw_fire(pg, cid)
        for _ in range(40):
            if pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state === 'burning'", cid):
                break
            pg.wait_for_timeout(60)
        pg.evaluate("() => { __world.speed = 0.001; }")
        S[cid] = {"pos": [], "face": [], "act": [], "st": []}
        for i in range(1, 90):
            r = pg.evaluate(_BF_STEP, [[cid], 1, 0.1])
            for kk in S[cid]:
                S[cid][kk] += r[cid][kk]
            if tagn == "A" and i in shots:
                _bf_shot(pg, shots[i] + ".png")
            if tagn == "B" and i == 12:
                _bf_shot(pg, "被燒細節_B原地跳腳.png")
            if S[cid]["st"][-1] != "burning":
                break
        _bf_adv(pg, 0.5)
    ok("被燒細節（真滑鼠）：兩位都被拎起丟進營火", held[A] and held[B], held)
    sa, sb = _bf_get(pg, A)["feel"], _bf_get(pg, B)["feel"]
    ok("個性不同掙扎不同：A 慌張亂跑（%s）、B 原地跳腳（%s）" % (sa["style"], sb["style"]), sa["style"] == "run" and sb["style"] == "hop", (sa["style"], sb["style"]))
    ga, gb = _bf_get(pg, A), _bf_get(pg, B)
    la, lb = ga["feel"]["struggle"], gb["feel"]["struggle"]
    kinds_a = {x["k"] for x in la}
    vars_a = {x.get("act") for x in la} | {x.get("say") for x in la if x.get("say")}
    ok("著火期至少 4 種不同動作／台詞（A：%s）" % sorted(v for v in vars_a if v), len(vars_a) >= 4 and len(la) >= 4, la)
    ok("著火期 B 也至少 4 段（B：%s）" % [x["k"] for x in lb], len(lb) >= 4, lb)
    ok("兩種個性掙扎不同：A 段落 %s、B 段落 %s" % ([x["k"] for x in la], [x["k"] for x in lb]), [x["k"] for x in la] != [x["k"] for x in lb] and {x.get("say") for x in la} != {x.get("say") for x in lb}, (la, lb))
    pa = _bf_path(S[A]["pos"])
    ok("亂跑距離 > 1.5 公尺（A 走了 %.1f 公尺、離起點最遠 %.1f 公尺）" % (pa, ga["feel"]["maxDisp"]), pa > 1.5 and ga["feel"]["moved"] > 1.5, (pa, ga["feel"]["moved"]))
    ok("著火期臉用驚嚇系（A %s）" % sorted(set(S[A]["face"])), "scared" in S[A]["face"] or "ouch" in S[A]["face"], S[A]["face"][:20])
    ok("著火期汗滴與驚嚇圖示：粒子池有活的粒子", pg.evaluate("() => __world.fire.pools.PS.live + __world.fire.pools.PA.live") > 0, None)
    # 熄火瞬間
    for _ in range(30):
        if all(pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", x) != "burning" for x in (A, B)):
            break
        _bf_adv(pg, 0.5)
    _bf_adv(pg, 0.4)
    ra, rb = _bf_log(pg, A, "burn-relief"), _bf_log(pg, B, "burn-relief")
    ok("熄火瞬間：兩位都大口喘氣（臉 %s、動作 %s）" % (ra and ra[0]["face"], ra and ra[0]["action"]), bool(ra) and bool(rb) and ra[0]["face"] == "effort", (ra, rb))
    ok("熄火瞬間：心情列已是「又痛又狼狽」階段", _bf_get(pg, A)["feel"]["stage"] == "pain", _bf_get(pg, A)["feel"]["stage"])
    _bf_shot(pg, "被燒細節_4熄火喘氣.png")
    # 圍觀同事
    crowd = pg.evaluate("() => __world.mind.log.filter(x => x.event && x.event.indexOf('crowd-') === 0 && x.event !== 'crowd-care').map(x => [x.id, x.event])")
    roles = {e for _, e in crowd}
    ok("同事圍過來：至少 2 位反應、至少 2 種角色（%s）" % sorted(roles), len({i for i, _ in crowd}) >= 2 and len(roles) >= 2, crowd)
    bad = pg.evaluate("""(ids) => { const bad = ['giggle', 'smug', 'laugh']; return ids.map(id => { const m = __world.mind.get(id); return m && bad.includes(m.face) ? [id, m.face] : null; }).filter(Boolean); }""", Ws)
    ok("同事不嘲笑（沒有偷笑／得意／大笑的臉）", not bad, bad)
    care = []
    for _ in range(14):
        care = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'crowd-care').map(x => [x.id, x.role])")
        if care:
            break
        _bf_adv(pg, 1.5)
    ok("同事走到身邊關心（%s）" % care, bool(care), care)
    _bf_shot(pg, "被燒細節_5同事圍過來.png")
    # 燒焦期：咳嗽、拍灰、看著自己難過、哭／苦笑
    faces_a, faces_b = set(), set()
    kinds = {A: [], B: []}
    for _ in range(36):
        _bf_adv(pg, 1.0)
        for cid, fs in ((A, faces_a), (B, faces_b)):
            fs.add(pg.evaluate("(id) => __world.chars.get(id).expression", cid))
        kinds = {k: [x["k"] for x in _bf_get(pg, k)["feel"]["struggle"] if x["k"] in ("self-look", "cry", "wry", "stomp", "daze")] for k in (A, B)}
        if len(kinds[A]) >= 2 and len(kinds[B]) >= 2 and "cough" in faces_a:
            break
        if pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", A) == "recovering":
            break
    ok("燒焦期咳嗽（A 出現過的臉 %s）" % sorted(faces_a), "cough" in faces_a, faces_a)
    ok("燒焦期有看著自己難過、再接各自的情緒小段（A %s、B %s）" % (kinds[A], kinds[B]), kinds[A][:1] == ["self-look"] and kinds[B][:1] == ["self-look"] and len(kinds[A]) >= 2 and len(kinds[B]) >= 2, kinds)
    ok("兩種個性燒焦期反應不同：A（敏感）%s、B（樂觀）%s" % (kinds[A][1:2], kinds[B][1:2]), kinds[A][1:2] == ["cry"] and kinds[B][1:2] == ["wry"], kinds)
    _bf_shot(pg, "被燒細節_6燒焦期.png")
    # 恢復：洗乾淨／換裝的小儀式
    rec = False
    for _ in range(20):
        _bf_adv(pg, 5)
        if _bf_get(pg, A)["feel"]["stage"] == "after":
            rec = True
            break
    ok("恢復完成（A 進入餘悸階段）", rec, _bf_get(pg, A)["feel"])
    wash = [x["k"] for x in _bf_get(pg, A)["feel"]["struggle"] if x["k"] in ("wash", "dress")]
    for _ in range(10):
        if wash == ["wash", "dress"]:
            break
        _bf_adv(pg, 4)
        wash = [x["k"] for x in _bf_get(pg, A)["feel"]["struggle"] if x["k"] in ("wash", "dress")]
    ok("恢復的小儀式：去飲水機洗乾淨、換好衣服（%s）" % wash, wash == ["wash", "dress"], wash)
    ga = _bf_get(pg, A)
    ok("恢復後：燒傷未癒、走路一拐一拐（limp=%s）" % ga["feel"]["limp"], ga["feel"]["limp"] is True, ga["feel"])
    # 走路變慢：同樣一段 5 公尺路，有傷 vs 無傷
    res = pg.evaluate("""async (id) => { const W = __world, c = W.chars.get(id), m = W.mind.mindOf(id), f = m.f; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = false; c.stop(false);
      const run = async (dx) => { const p = c.object3D.position, t = W.nav.nearestFree(p.x + dx, p.z, 4), path = W.nav.findPath({ x: p.x, z: p.z }, t); c.walkTo(path, { speed: 2.4 }); const x0 = p.x, z0 = p.z; await W.advanceAsync(2.5); const q = c.object3D.position; const d = Math.hypot(q.x - x0, q.z - z0); c.stop(false); return d; };
      c.standAt(14, 20, 0); await W.advanceAsync(.3); const slow = await run(6); f.limpUntil = 0; m.burned = false; c.standAt(14, 20, 0); await W.advanceAsync(.3); const fast = await run(6); return { slow, fast }; }""", A)
    ok("走路變慢：燒傷期 2.5 秒走 %.1f 公尺、痊癒後 %.1f 公尺" % (res["slow"], res["fast"]), res["fast"] > 0.5 and res["slow"] < res["fast"] * 0.78, res)
    # 之後：繞火
    out = pg.evaluate("""async (id) => { const W = __world, c = W.chars.get(id), f = W.mind.feel.of(W.mind.mindOf(id)), fc = W.fire.center; W.fire.reset(); c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; f.fear = .9; f.cd = {};
      c.standAt(fc.x - 5.5, fc.z + 0.2, 0); await W.advanceAsync(.3); const p = c.object3D.position, path = W.nav.findPath({ x: p.x, z: p.z }, { x: fc.x + 5.5, z: fc.z + 0.2 }); c.walkTo(path, { speed: 2.4 }); let mn = 99;
      for (let i = 0; i < 90; i++) { await W.advanceAsync(.25); const q = c.object3D.position; mn = Math.min(mn, Math.hypot(q.x - fc.x, q.z - fc.z)); if (c.state !== 'walk' && i > 4) break; } return mn; }""", A)
    ok("之後路過營火繞遠（最近 %.1f 公尺）並留下繞路紀錄" % out, out >= 1.9 and bool(_bf_log(pg, A, "fire-detour")), out)
    ok("被燒細節：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_bf_grab(b, base):
    c1, pg, got = _bf_open(b, base)
    if not ok("看到你拎人：世界載入", got):
        c1.close(); return
    A = _bf_pick(pg, "(t) => true")
    G = _bf_pick(pg, "(t) => true", skip=(A,))
    pg.evaluate("() => { __world.fire.reset(); __world.phys.restoreAll(true); __world.daytime.set('day'); __world.godAt(30.2, 36.4, 26); }")
    wait_until(pg, "() => !__world.view.tween", 20000)
    pg.evaluate("""([a, g]) => { const W = __world; for (const id of [a, g]) { const c = W.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = true; } W.chars.get(g).standAt(24.5, 33.5, 0); W.chars.get(a).standAt(22.5, 33.8, 0); const m = W.mind.mindOf(a), f = W.mind.feel.of(m); m.burned = false; m.sc = null; f.fear = .8; f.grabAt = -999; W.speed = 1; }""", [A, G])
    pg.wait_for_timeout(800)
    gx, gy = _bf_proj(pg, G)
    pg.mouse.move(gx, gy)
    pg.mouse.down()
    pg.wait_for_timeout(800)
    pg.mouse.move(gx + 6, gy - 4)
    pg.wait_for_timeout(400)
    near = _bf_log(pg, A, "grab-nervous")
    dbg = pg.evaluate("([a, g]) => { const W = __world; return [[...W.chars].filter(([k, c]) => c._held || c.state === 'held').map(x => x[0]), W.chars.get(g).state, W.mind.mindOf(g).grabbedAt, W.time, W.mind.mindOf(a).sc && W.mind.mindOf(a).sc.name, W.mind.feel.of(W.mind.mindOf(a)).grabAt]; }", [A, G])
    print("  除錯：拎起的人 %s、G=%s、A=%s" % (dbg, G, A))
    _bf_shot(pg, "被燒細節_7看到你拎人緊張.png")
    pg.mouse.up()
    ok("看到你拎人（真滑鼠按住）：被燒過、還怕火的同事會緊張（%s）" % (near and near[0].get("face")), bool(near) and near[0].get("face") == "scared", (near, pg.evaluate("(g) => __world.chars.get(g).state", G)))
    ok("看到你拎人：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_bf_pool(b, base):
    c1, pg, got = _bf_open(b, base)
    if not ok("被燒跑向泳池：世界載入", got):
        c1.close(); return
    C = _bf_pick(pg, "(t) => true")
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); W.fire.reset(); W.speed = 0.001; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c.standAt(4.4, 41.0, 0); }""", C)
    pg.evaluate("() => __world.advanceAsync(.5)")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", C)
    r = pg.evaluate(_BF_STEP, [[C], 1, 0.1])
    st = _bf_get(pg, C)["feel"]["style"]
    ok("附近有泳池：被點燃的人選擇跑向泳池（style=%s）" % st, st == "pool", st)
    pos, states, ins = [], [], False
    for i in range(110):
        r = pg.evaluate(_BF_STEP, [[C], 1, 0.1])
        pos.append(r[C]["pos"][0]); states.append(r[C]["st"][0])
        if i == 20:
            _bf_shot(pg, "被燒細節_8衝向泳池.png")
        x, z = pos[-1]
        if 1.8 <= x <= 8.2 and 33.0 <= z <= 37.0:
            ins = True
        if states[-1] != "burning":
            break
    ok("衝進泳池並熄火（進池 %s、最後狀態 %s）" % (ins, states[-1]), ins and states[-1] != "burning", (pos[-1], states[-1]))
    _bf_adv(pg, 1.0)
    g = _bf_get(pg, C)
    ok("入水後情緒接到「被水救了」階段（stage=%s）" % g["feel"]["stage"], g["feel"]["stage"] == "wet", g["feel"])
    _bf_shot(pg, "被燒細節_9入水熄火.png")
    ok("泳池場景沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_bf_all(b, base):
    only = _os.environ.get("BURN_ONLY", "")
    parts = {"burn": t_bf_burn, "grab": t_bf_grab, "pool": t_bf_pool}
    for k, f in parts.items():
        if not only or k in only.split(","):
            f(b, base)


register("辦公室被燒情緒細節", lambda pg, b, base, code: t_bf_all(b, base))
