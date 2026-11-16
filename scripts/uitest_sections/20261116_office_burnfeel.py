# 驗收段落「辦公室被燒情緒細節」：AI Office 3D 辦公室（site/office/world.html）。
# 擁有者原話：「被燒到應該是有夠多掙扎還有情緒，燒完後也是，細節需要多點。」分鏡表 docs/ai_office/burn_storyboard.md
#   B1 著火當下：兩種個性（慌張亂跑／原地跳腳）真滑鼠丟進營火；掙扎至少 4 種動作／台詞、亂跑距離 > 1.5 公尺、同事圍過來關心（不嘲笑）
#   B2 熄火瞬間：大口喘氣；燒焦期：咳嗽、拍灰、看著自己難過、兩種個性的情緒小段不同
#   B3 恢復與之後：走路變慢（一拐一拐）、洗乾淨換裝的小儀式、之後繞火、看到你拎人會緊張
#   B4 被點燃的人一律跑向「路程最近」的水源（泳池或辦公室飲水機）、到了熄火；被拎著不跑、放下後繼續；來不及就原地拍熄
#   B5 燒一陣子（8～12 秒）、人傳火（上限 4 位、濕的不燒、和好）、燒著的人點燃可燃家具（上限 6 件、焦黑、復原、同事拿水桶滅）
# 由 runsec2.py 或 _uitest.py 載入。環境變數 BURN_SHOTS 指到資料夾時，順便存各階段截圖。
# flake8: noqa

import os as _os

_BF_QS = "?ambient=0&q=low&pr=0.6&sim=1"


def _bf_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _bf_open(b, base, w=1280, h=800, noWater=True):
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
    if got:
        pg.evaluate("(nw) => { __world.mind.feel.cfg.noWater = nw; __world.fire.noHelpers = nw; }", noWater)   # B1～B3 單獨驗原地掙扎；B4 才開「跑向水源」
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
    return pg.evaluate("""([cond, skip]) => { const f = eval(cond); for (const [id, c] of __world.chars) { if (c.spec.pet || c.spec.isCeo || c.jobless || c.away || c.sleeping || skip.includes(id) || (c.look && c.look.species === 'flame')) continue; const g = __world.mind.get(id); if (g && f(g.traits, c)) return id; } return null; }""", [cond_js, list(skip)])


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
    c1, pg, got = _bf_open(b, base, noWater=False)
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


# ───────── 11-16 追加：被燒後跑去滅火、人傳火、家具著火、燒一陣子 ─────────
def _bf_free(pg, cid, x, z):
    """把同事擺到最近的空位，清掉他手上的流程（不碰火的狀態）。"""
    return pg.evaluate("""([id, x, z]) => { const W = __world, c = W.chars.get(id), f = W.nav.nearestFree(x, z, 8) || { x, z }; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c._held = false; c.standAt(f.x, f.z, 0); return [f.x, f.z]; }""", [cid, x, z])


def _bf_run_until(pg, cid, cond_js, n=260, dt=0.1, shot=None, shot_name=None):
    """每 dt 秒一步，直到條件成立；回傳每步 [x, z, 狀態] 與是否成立。shot＝第幾步先停下來截一張圖。"""
    if shot is not None:
        pg.evaluate("""async ([id, k, dt]) => { const W = __world; for (let i = 0; i < k; i++) await W.advanceAsync(dt); }""", [cid, shot, dt])
        pg.wait_for_timeout(300)
        _bf_shot(pg, shot_name)
        n = max(1, n - shot)
    out = pg.evaluate("""async ([id, cond, n, dt]) => { const W = __world, c = W.chars.get(id), f = eval(cond), tr = []; let hit = false;
      for (let i = 0; i < n; i++) { await W.advanceAsync(dt); const p = c.object3D.position; tr.push([p.x, p.z, W.fire.stateOf(c).state]); if (f(c, W)) { hit = true; break; } } return { tr, hit }; }""", [cid, cond_js, n, dt])
    return out["tr"], out["hit"]


def _bf_look(pg, x, z, h=11):
    pg.evaluate("([x, z, h]) => { __world.godAt(x, z, h); }", [x, z, h])
    wait_until(pg, "() => !__world.view.tween", 20000)


def t_bf_water(b, base):
    c1, pg, got = _bf_open(b, base, noWater=False)
    if not ok("被燒跑去滅火：世界載入", got):
        c1.close(); return
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.fire.noHelpers = true; W.speed = 0.001; }")
    # ① 辦公室飲水機：身旁沒有泳池就近的位置（飲水機在 29.2, 1.5）
    A = _bf_pick(pg, "(t) => true")
    x0, z0 = _bf_free(pg, A, 24.5, 8.0)
    pg.evaluate("() => __world.advanceAsync(.5)")
    d0 = ((29.2 - x0) ** 2 + (1.52 - z0) ** 2) ** 0.5
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", A)
    pg.evaluate("() => __world.advanceAsync(.2)")
    st = _bf_get(pg, A)["feel"]["style"]
    ok("被燒後選最近的水源：飲水機（style=%s，離飲水機 %.1f 公尺）" % (st, d0), st == "water", st)
    _bf_look(pg, 27.0, 5.0, 12)
    tr, hit = _bf_run_until(pg, A, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 200, shot=10, shot_name="被燒滅火_3跑向飲水機途中.png")
    ds = [((29.2 - x) ** 2 + (1.52 - z) ** 2) ** 0.5 for x, z, _ in tr]
    ex = pg.evaluate("(id) => __world.eventLog ? 0 : 0", A)
    ok("辦公室水源：跑向飲水機、距離縮短（%.1f → %.1f 公尺）" % (d0, ds[-1]), hit and ds[-1] < 1.2 and ds[-1] < d0 - 2, (d0, ds[-1]))
    g = _bf_get(pg, A)["feel"]; sg = g["struggle"]
    ok("到飲水機潑水熄火（拍熄紀錄 douse、狀態 %s、焦黑仍在不洗掉）" % tr[-1][2], any(x.get("k") == "douse" for x in sg) and tr[-1][2] == "smoldering" and pg.evaluate("(id) => __world.chars.get(id)._sootU.value", A) > 0.3, (sg[-3:], tr[-1][2]))
    ok("熄火後身上濕 15 秒、碰火不著火（免疫）", pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); return (c._fireImmuneUntil || 0) > W.time && (c._fireImmuneUntil - W.time) <= 15.01 }", A), None)
    pg.wait_for_timeout(200); _bf_shot(pg, "被燒滅火_4辦公室水源潑水.png")
    # ② 營火位置被點燃：一樣跑（不限 12 公尺）、距離水源縮短、到達後熄火（泳池）
    B = _bf_pick(pg, "(t) => true", skip=(A,))
    pg.evaluate("() => { __world.fire.reset(); }")
    _bf_free(pg, B, 30.2, 38.0)
    pg.evaluate("() => __world.advanceAsync(.3)")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", B)
    pg.evaluate("() => __world.advanceAsync(.2)")
    kind = _bf_get(pg, B)["feel"]["style"]
    tgt = {"pool": (5.0, 41.0), "water": (29.2, 1.52)}.get(kind, (5.0, 41.0))
    tr, hit = _bf_run_until(pg, B, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 260)
    dd = [((tgt[0] - x) ** 2 + (tgt[1] - z) ** 2) ** 0.5 for x, z, _ in tr]
    ok("營火位置被點燃也會跑向水源（%s）：距離 %.1f → %.1f 公尺、中途沒停下" % (kind, dd[0], dd[-1]), hit and dd[-1] < dd[0] - 8, (dd[0], dd[-1], tr[-1]))
    ok("到水源後熄火（最後狀態 %s）" % tr[-1][2], tr[-1][2] != "burning", tr[-1])
    # ③ 被拎著不跑、放下後繼續跑（真滑鼠拎起來）；燒著不會因離開營火就熄
    pg.evaluate("() => { __world.fire.reset(); }")
    C = _bf_pick(pg, "(t) => true", skip=(A, B))
    _bf_free(pg, C, 30.2, 38.0)
    _bf_look(pg, 30.2, 38.0, 12)
    pg.evaluate("() => __world.advanceAsync(.3)")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", C)
    pg.evaluate("() => __world.advanceAsync(.3)")      # 還在原地驚叫（前 0.9 秒不跑），這時用真滑鼠拎起來
    cx, cy = _bf_proj(pg, C)
    pg.mouse.move(cx, cy); pg.mouse.down(); pg.wait_for_timeout(800); pg.mouse.move(cx + 6, cy - 6, steps=2); pg.wait_for_timeout(300)
    heldNow = pg.evaluate("(id) => __world.chars.get(id).state === 'held'", C)
    p0 = pg.evaluate("(id) => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; }", C)
    pg.evaluate("() => __world.advanceAsync(5)")
    p1 = pg.evaluate("(id) => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; }", C)
    still = pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", C)
    mv = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
    ok("被你拎著（真滑鼠，held=%s）時不跑（5 秒位移 %.2f 公尺）、而且 5 秒後仍在燒（%s）" % (heldNow, mv, still), heldNow and mv < 0.6 and still == "burning", (heldNow, mv, still))
    pg.mouse.up()
    pg.evaluate("() => __world.advanceAsync(2.5)")
    p2 = pg.evaluate("(id) => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; }", C)
    mv2 = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    ok("放下後繼續跑去滅火（2.5 秒位移 %.1f 公尺）" % mv2, mv2 > 3.0, mv2)
    # ④ 路程太遠（超過上限）→ 原地拍打把火拍熄
    pg.evaluate("() => { __world.fire.reset(); __world.mind.feel.cfg.cap = 6; }")
    D = _bf_pick(pg, "(t) => true", skip=(A, B, C))
    _bf_free(pg, D, 30.2, 38.0)
    pg.evaluate("() => __world.advanceAsync(.3)")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", D)
    tr, hit = _bf_run_until(pg, D, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 300)
    sg = _bf_get(pg, D)["feel"]["struggle"]
    ok("來不及跑到（上限 6 秒）→ 停下來原地拍打（紀錄 pat-out），火拍熄（%s）" % tr[-1][2], any(x.get("k") == "pat-out" for x in sg) and hit, (sg[-3:], tr[-1]))
    pg.evaluate("() => { __world.mind.feel.cfg.cap = 20; }")
    ok("滅火場景沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_bf_keepburn(b, base):
    c1, pg, got = _bf_open(b, base)       # 關掉跑向水源與同事幫忙：只看「離開火源之後會不會馬上熄」
    if not ok("燒一陣子：世界載入", got):
        c1.close(); return
    A = _bf_pick(pg, "(t) => true")
    pg.evaluate("() => { __world.fire.reset(); __world.speed = 0.001; }")
    _bf_free(pg, A, 30.2, 38.0)
    pg.evaluate("() => __world.advanceAsync(.3)")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", A)
    pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), f = W.fire.center; c.standAt(f.x + 7, f.z + 4, 0); c._held = true; }", A)   # 一下子搬離營火 7 公尺（被拎著）
    pg.evaluate("() => __world.advanceAsync(5)")
    r = pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), f = W.fire.center, p = c.object3D.position; return { st: W.fire.stateOf(c).state, d: Math.hypot(p.x - f.x, p.z - f.z), dur: W.fire.states.get(id).dur }; }", A)
    ok("拎著燒著的人移離營火 %.1f 公尺，5 秒後仍在燒（%s，燒的時間 %.1f 秒）" % (r["d"], r["st"], r["dur"]), r["st"] == "burning" and r["d"] > 6, r)
    ok("角色燃燒時間在 8～12 秒之間（%.1f）" % r["dur"], 8 <= r["dur"] <= 12.01, r)
    pg.evaluate("(id) => { __world.chars.get(id)._held = false; }", A)
    tr, hit = _bf_run_until(pg, A, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 300)
    ok("沒有人滅、也沒水源時，燒完時間自然熄（%s）" % tr[-1][2], hit, tr[-1])
    c1.close()


def t_bf_spread(b, base):
    c1, pg, got = _bf_open(b, base)
    if not ok("人傳火：世界載入", got):
        c1.close(); return
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 0.001; W.fire.noHelpers = true; }")
    ids = []
    for k in range(6):
        ids.append(_bf_pick(pg, "(t) => true", skip=tuple(ids)))
    A, B, W2 = ids[0], ids[1], ids[2]
    for i in ids:
        _bf_free(pg, i, 14.0 + 0.1 * ids.index(i), 30.0)
    # 空曠處：把六個人都擺在 14, 30 附近的同一個點上（疊在一起），其餘跟著燒不到
    pg.evaluate("(ids) => { const W = __world, f = W.nav.nearestFree(14, 30, 8) || { x: 14, z: 30 }; ids.forEach((id, i) => { const c = W.chars.get(id); c.standAt(f.x + (i ? 0.45 : 0) * Math.cos(i), f.z + (i ? 0.45 : 0) * Math.sin(i), 0); }); }", ids)
    # 濕的人：W2 剛被水澆濕
    pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c._wetUntil = W.time + 15; c._fireImmuneUntil = W.time + 15; }", W2)
    pg.evaluate("() => { const W = __world; for (const c of W.chars.values()) c.busy = true; }")
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", A)
    pg.evaluate("() => __world.advanceAsync(1.0)")
    sts = pg.evaluate("(ids) => ids.map(id => __world.fire.stateOf(__world.chars.get(id)).state)", ids)
    nb = sum(1 for x in sts if x == "burning")
    ok("燒著的人撞到同事 → 同事著火（%s）" % sts, sts[1] == "burning", sts)
    ok("濕的人（W2 剛被澆濕）不會被傳火（%s）" % sts[2], sts[2] == "none", sts)
    ok("同時著火上限 4 位生效（實際 %d 位著火，6 人疊在一起）" % nb, nb == 4, (nb, sts))
    fr = pg.evaluate("(id) => { const m = __world.mind.mindOf(id), f = __world.mind.feel.of(m); return { from: f.bs && f.bs.from, catchFrom: f.catchFrom }; }", B)
    ok("被傳火的人記得是誰傳的（from=%s）" % fr["from"], fr["from"] == A, fr)
    pg.evaluate("() => __world.advanceAsync(2)")
    sg = _bf_get(pg, B)["feel"]["struggle"]
    ok("被傳火的人怪那位同事一下（blame-peer）", any(x.get("k") == "blame-peer" for x in sg), sg)
    # 兩個人都去滅火：打開跑向水源，重新再來一次
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.mind.feel.cfg.noWater = false; for (const c of W.chars.values()) { c.busy = false; } }")
    A2, B2 = ids[3], ids[4]
    for i in (A2, B2):
        _bf_free(pg, i, 26.0, 8.0)
    pg.evaluate("([a, b]) => { const W = __world, f = W.nav.nearestFree(25, 8, 6), ca = W.chars.get(a), cb = W.chars.get(b); ca.standAt(f.x, f.z, 0); cb.standAt(f.x + 0.4, f.z, 0); for (const c of [ca, cb]) c.busy = true; }", [A2, B2])
    pg.evaluate("(id) => { const W = __world; W.fire.ignite(W.chars.get(id), 'test'); }", A2)
    ex = {}
    def _fin(i):
        return pg.evaluate("(id) => { const W = __world; return W.fire.stateOf(W.chars.get(id)).state }", i)
    trA, hitA = _bf_run_until(pg, A2, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 300)
    trB, hitB = _bf_run_until(pg, B2, "(c, W) => W.fire.stateOf(c).state !== 'burning'", 300)
    ok("傳火的兩人都跑去水源滅火（A %s、B %s）" % (trA[-1][2], trB[-1][2]), hitA and hitB, (trA[-1], trB[-1]))
    # 和好
    pg.evaluate("(id) => { __world.emit('recovered', id, {}); }", B2)
    pg.evaluate("() => __world.advanceAsync(12)")
    rec = _bf_log(pg, B2, "reconcile")
    ok("火滅後兩個人和好（reconcile 紀錄 %s）" % bool(rec), bool(rec), rec)
    ok("人傳火場景沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_bf_furn(b, base):
    c1, pg, got = _bf_open(b, base)
    if not ok("家具著火：世界載入", got):
        c1.close(); return
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.speed = 0.001; W.fire.noHelpers = true; }")
    F = "(type) => { const W = __world; const i = [...W.furn.values()].find(q => q.f.type === type); return i ? { id: i.f.id, x: i.f.x, z: i.f.z } : null; }"
    desk = pg.evaluate(F, "workstation"); fridge = pg.evaluate(F, "fridge"); water = pg.evaluate(F, "water"); arcade = pg.evaluate(F, "arcade")
    A = _bf_pick(pg, "(t) => true")
    _bf_look(pg, desk["x"], desk["z"], 9)
    # ① 不可燃：燒著的人站在飲水機、冰箱、遊戲機上 → 不著火
    for o in (fridge, water, arcade):
        if not o:
            continue
        pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.busy = true; c.stop(false); c.standAt(x, z, 0); W.fire.ignite(c, 'test'); }", [A, o["x"], o["z"]])
        pg.evaluate("() => __world.advanceAsync(.6)")
        pg.evaluate("(id) => { const W = __world; W.fire.states.get(id).state = 'none'; }", A)
    nf = pg.evaluate("() => [...__world.fire.furn.keys()]")
    ok("金屬／水源／機台不會著火（飲水機、冰箱、遊戲機；著火家具 %s）" % nf, not nf, nf)
    pg.evaluate("() => { __world.fire.reset(); }")
    # ② 燒著的人碰桌子 → 桌子著火
    pg.evaluate("([id, x, z]) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.busy = true; c.stop(false); c.standAt(x, z, 0); W.fire.ignite(c, 'test'); }", [A, desk["x"], desk["z"] + 0.2])
    pg.evaluate("() => __world.advanceAsync(.5)")
    fs = pg.evaluate("(id) => { const o = __world.fire.furn.get(id); return o ? { state: o.state, dur: o.dur, ov: !!o.ov && !!o.ov.parent } : null; }", desk["id"])
    ok("燒著的人碰到桌子 → 桌子著火（%s，會燒 %.1f 秒，焦黑疊層已掛上）" % (fs and fs["state"], fs["dur"] if fs else 0), bool(fs) and fs["state"] == "burning" and fs["ov"] and 15 <= fs["dur"] <= 25.01, fs)
    pg.evaluate("() => __world.advanceAsync(1.5)")
    pl = pg.evaluate("() => ({ a: __world.fire.pools.PA.live, s: __world.fire.pools.PS.live })")
    ok("家具著火有火焰、煙、光暈（粒子 PA %d／PS %d，共用營火的粒子池）" % (pl["a"], pl["s"]), pl["a"] > 20 and pl["s"] > 3, pl)
    pg.wait_for_timeout(300); _bf_shot(pg, "被燒滅火_5家具著火.png")
    # 沒人滅：燒到時間自己熄 → 焦黑 → 過一陣子復原
    pg.evaluate("(id) => { __world.fire.states.get(id).state = 'none'; }", A)
    pg.evaluate("() => __world.advanceAsync(26)")
    sc = pg.evaluate("(id) => { const o = __world.fire.furn.get(id); return o ? { state: o.state, scorch: o.scorch, op: o.ov.material.opacity } : null; }", desk["id"])
    ok("沒人滅就燒完自己熄、留下焦黑（%s）" % sc, bool(sc) and sc["state"] == "scorched" and sc["scorch"] > 0.5 and sc["op"] > 0.3, sc)
    pg.evaluate("() => __world.advanceAsync(80)")
    gone = pg.evaluate("(id) => ({ has: __world.fire.furn.has(id), stat: __world.fire.stats.furnRecovered || 0 })", desk["id"])
    ok("一段時間後自動復原（焦黑褪掉、疊層移除；復原 %d 件）" % gone["stat"], not gone["has"] and gone["stat"] >= 1, gone)
    # ③ 同事拿水桶去滅（桶子拿在手上）
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.fire.noHelpers = false; }")
    H = _bf_pick(pg, "(t) => true", skip=(A,))
    pg.evaluate("([h, x, z]) => { const W = __world, c = W.chars.get(h), f = W.nav.nearestFree(x + 5.5, z + 5.5, 6); c.script = (c.script || 0) + 1; c.busy = false; c.stop(false); c.standAt(f.x, f.z, 0); }", [H, desk["x"], desk["z"]])
    pg.evaluate("() => { window.__bk = []; __world.on('bucketed', e => window.__bk.push(['bk', e.id, e.kind])); __world.on('furn_extinguished', e => window.__bk.push(['fx', e.id, e.cause])); }")
    pg.evaluate("(id) => { const W = __world; W.fire.igniteFurn(W.furn.get(id)); }", desk["id"])
    seen_bucket = False; tmax = 0.0
    for i in range(200):
        pg.evaluate("() => __world.advanceAsync(.1)")
        if pg.evaluate("() => [...__world.chars.values()].some(c => c._bucket)"):
            seen_bucket = True
            if not _os.path.exists(_os.path.join(_os.environ.get("BURN_SHOTS", "/nonexistent"), "被燒滅火_6同事拿水桶.png")) and i > 6:
                pg.wait_for_timeout(200); _bf_shot(pg, "被燒滅火_6同事拿水桶.png")
        o = pg.evaluate("(id) => { const o = __world.fire.furn.get(id); return o ? { t: o.t, dur: o.dur, state: o.state } : null; }", desk["id"])
        if o and o["state"] == "burning":
            tmax = o["t"]
        if not o or o["state"] != "burning":
            break
    bk = pg.evaluate("() => window.__bk")
    ok("同事拿水桶（手上看得到桶子）跑去滅桌子的火（滅在第 %.1f 秒、原本會燒 %.1f 秒；%s）" % (tmax, o["dur"] if o else 0, bk[:2]), seen_bucket and any(x[0] == "fx" and x[2] == "bucket" for x in bk) and any(x[0] == "bk" and x[2] == "furn" for x in bk) and o and tmax < o["dur"] - 3, (seen_bucket, bk, o, tmax))
    pg.evaluate("() => __world.advanceAsync(3)")
    ok("滅完火桶子收起來（bucket 移除）", not pg.evaluate("() => [...__world.chars.values()].some(c => c._bucket)"), None)
    # ④ 家具同時著火上限
    pg.evaluate("() => { const W = __world; W.fire.reset(); W.fire.noHelpers = true; }")
    n = pg.evaluate("() => { const W = __world; let ok = 0; for (const i of W.furn.values()) if (W.fire.combustible(i.f.type) && W.fire.igniteFurn(i)) ok++; return ok; }")
    burning = pg.evaluate("() => [...__world.fire.furn.values()].filter(o => o.state === 'burning').length")
    ok("家具同時著火上限 6 件生效（嘗試點燃全部可燃家具，實際 %d 件）" % burning, burning == 6 and n == 6, (n, burning))
    pg.evaluate("() => __world.advanceAsync(1)")
    ok("家具著火場景沒有主控台錯誤", not pg.errs, pg.errs[:3])
    pg.evaluate("() => { __world.fire.reset(); }")
    c1.close()


def t_bf_wetshot(b, base):
    """濕答答名牌、水滴、碰火冒白煙的截圖與事件。"""
    c1, pg, got = _bf_open(b, base)
    if not ok("濕答答截圖：世界載入", got):
        c1.close(); return
    pg.evaluate("() => { __world.fire.reset(); __world.daytime.set('day'); __world.godAt(30.2, 36.4, 14); }")
    wait_until(pg, "() => !__world.view.tween", 20000)
    A = _bf_pick(pg, "(t) => true"); Bc = _bf_pick(pg, "(t) => true", skip=(A,))
    pg.evaluate("([a, b]) => { const W = __world, f = W.fire.center; for (const [id, dx] of [[a, 2.6], [b, -2.6]]) { const c = W.chars.get(id); c.script = (c.script || 0) + 1; c.busy = true; c.stop(false); c.standAt(f.x + dx, f.z + 0.6, 0); } const c = W.chars.get(a); c._wetUntil = W.time + 15; c._fireImmuneUntil = W.time + 15; }", [A, Bc])
    pg.evaluate("() => __world.advanceAsync(1.0)")
    pg.wait_for_timeout(600)
    info = pg.evaluate("(a) => { const W = __world, c = W.chars.get(a); return { icon: c.emoteSym && c.emoteSym.sym, tag: W.statusOf(c), dom: c._lab && c._lab.stEl.textContent, drips: W.sports.water.stats.drips }; }", A)
    ok("濕的人：頭上水滴圖示、名牌「濕答答」（%s）、滴水 %d 滴" % (info["dom"], info["drips"]), info["icon"] == "sweat" and "濕答答" in (info["dom"] or ""), info)
    _bf_shot(pg, "被燒滅火_1濕答答名牌與水滴.png")
    pg.evaluate("([a]) => { const W = __world, f = W.fire.center; W.chars.get(a).standAt(f.x + 0.6, f.z + 0.2, 0); }", [A])
    pg.evaluate("() => __world.advanceAsync(0.35)")
    pg.wait_for_timeout(250)
    _bf_shot(pg, "被燒滅火_2碰火冒白煙.png")
    ok("濕的人碰營火：冒白煙、不著火（%s）" % pg.evaluate("(a) => __world.fire.stateOf(__world.chars.get(a)).state", A), pg.evaluate("(a) => __world.fire.stateOf(__world.chars.get(a)).state === 'none' && __world.fire.stats.sizzled >= 1", A), None)
    c1.close()


def t_bf_all(b, base):
    only = _os.environ.get("BURN_ONLY", "")
    parts = {"burn": t_bf_burn, "grab": t_bf_grab, "pool": t_bf_pool, "water": t_bf_water, "keepburn": t_bf_keepburn, "spread": t_bf_spread, "furn": t_bf_furn, "wetshot": t_bf_wetshot}
    for k, f in parts.items():
        if not only or k in only.split(","):
            f(b, base)


register("辦公室被燒情緒細節", lambda pg, b, base, code: t_bf_all(b, base))
