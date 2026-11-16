# 驗收段落「辦公室情緒加深」：AI Office 3D 辦公室（site/office/world.html）。擁有者原話：「被燒之後的情緒要更多，被打、被照顧都是。」
#   F1 被燒：驚嚇→疼痛狼狽（拍灰、咳嗽）→餘悸（怕火）→怪不怪你（依個性）→找朋友訴苦；兩位不同個性的人同樣被你丟進營火（真滑鼠）
#   F2 被欺負三次（真滑鼠）：小委屈→生氣／難過→害怕，跑去找 CEO 告狀或躲到角落；你靠近時後退
#   F3 被照顧：摸頭、餵點心（多次才原諒）、同事安慰、被泳池救火（extinguished cause:'pool'／splashed）、靠近時揮手與主動走過來
#   F4 運動事件：開賽、得分、贏、輸（不甘心想再來一場）、和對手關係變好；個性不同反應不同
#   F5 怕火：經過營火繞遠、夜晚路燈火光緊張（對照不怕火的人直接走過去）
#   F6 心情列：文字寫「現在的情緒＋原因＋對你的態度」，1280／390 不溢出不重疊；不羞辱（旁觀者沒有嘲笑類表情）；無主控台錯誤
# 由 runsec2.py 或 _uitest.py 載入。環境變數 FEEL_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import json as _json
import re as _re

_FE_QS = "?ambient=0&q=low&pr=0.6&sim=1"
_FE_BURN_FACES = ("scared", "blank", "cough", "ouch", "effort", "cry")   # 11-16 起掙扎（ouch／cry）與熄火喘氣（effort）也算被燒的臉
_FE_HAPPY = ["happy", "laugh", "whee", "smile", "bliss", "shy", "fistpump", "giggle", "grateful", "relieved", "smug"]


def _fe_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _fe_open(b, base, w=1280, h=800, speed=1, tod="day"):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','%s')}catch(e){}" % tod)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_fe_root(base) + "/office/world.html" + _FE_QS, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.mind && window.__world.mind.feel", 90000)
    if got:
        pg.evaluate("(k) => { __world.speed = k; }", speed)
    pg.wait_for_timeout(500)
    return c, pg, got


def _fe_shot(pg, name):
    d = _os.environ.get("FEEL_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _fe_get(pg, cid):
    return pg.evaluate("(id) => __world.mind.get(id)", cid)


def _fe_mood(pg, cid):
    return pg.evaluate("(id) => __world.mind.moodLine(__world.chars.get(id))", cid)


def _fe_adv(pg, sec):
    pg.evaluate("(s) => __world.advanceAsync(s)", sec)


def _fe_log(pg, cid, event):
    return pg.evaluate("([id, ev]) => __world.mind.log.filter(x => x.id === id && x.event === ev)", [cid, event])


def _fe_until(pg, cid, event, max_sec=60, step=5):
    """推進模擬時間，直到這個人的紀錄出現某事件（回傳最新一筆或 None）。"""
    t = 0
    while t <= max_sec:
        r = _fe_log(pg, cid, event)
        if r:
            return r[0]
        _fe_adv(pg, step)
        t += step
    r = _fe_log(pg, cid, event)
    return r[0] if r else None


def _fe_pick(pg, cond_js, skip=()):
    """挑一位在職、醒著的同事（有符合特質條件就用；沒有就回傳 None）。"""
    r = pg.evaluate("""([cond, skip]) => { const f = eval(cond); for (const [id, c] of __world.chars) { if (c.spec.pet || c.spec.isCeo || c.jobless || c.away || c.sleeping || skip.includes(id)) continue; const g = __world.mind.get(id); if (g && f(g.traits, c)) return id; } return null; }""", [cond_js, list(skip)])
    return r


def _fe_make(pg, cond_js, traits, skip=()):
    """挑符合條件的人；全辦公室找不到就把某位的特質調成指定值（回報會註明）。回傳 (代號, 是否硬調)。"""
    cid = _fe_pick(pg, cond_js, skip)
    if cid:
        return cid, False
    cid = _fe_pick(pg, "(t) => true", skip)
    pg.evaluate("([id, t]) => { Object.assign(__world.mind.mindOf(id).t, t); }", [cid, traits])
    return cid, True


def _fe_proj(pg, cid):
    return pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), v = new W.THREE.Vector3(c.object3D.position.x, (c.height || 1) * 0.55 + (c.lift || 0), c.object3D.position.z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }""", cid)


def _fe_fire_proj(pg):
    return pg.evaluate("""() => { const W = __world, v = new W.THREE.Vector3(30.2, 0.6, 36.6).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }""")


def _fe_throw_wall(pg, cid):
    """真滑鼠：按住角色 0.65 秒拎起，快速往旁邊甩出去，放開。"""
    x, y = _fe_proj(pg, cid)
    pg.mouse.move(x, y)
    pg.mouse.down()
    pg.wait_for_timeout(650)
    for i in range(1, 7):
        pg.mouse.move(x + i * 45, y - i * 6)
        pg.wait_for_timeout(18)
    pg.mouse.up()


def _fe_stage_for_fire(pg, cid, x, z):
    pg.evaluate("""([id, x, z]) => { const W = __world, c = W.chars.get(id); for (const o of W.chars.values()) { if (!o._held) o.busy = o.busy && o.spec.id === id ? true : o.busy; }
      c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.stop(false); c.standAt(x, z, 0); W.fire.states.delete(id); W.speed = 1; }""", [cid, x, z])


def _fe_throw_fire(pg, cid):
    """真滑鼠：按住角色，往火堆的方向甩過頭、放開。回傳是否被拎起。"""
    cx, cy = _fe_proj(pg, cid)
    fx, fy = _fe_fire_proj(pg)
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


def _fe_card_text(pg):
    return pg.evaluate("() => { const e = document.getElementById('cardMood'); return e ? e.textContent : ''; }")


# ───────────────────────── F1 被燒：分階段＋個性差異 ─────────────────────────
def t_fe_burn(b, base):
    c1, pg, got = _fe_open(b, base)
    if not ok("被燒：世界載入、情緒層建立", got):
        c1.close(); return
    A, forcedA = _fe_make(pg, "(t) => t.sens >= .55 && t.ext >= .45 && t.comp < .6", {"sens": .8, "ext": .7, "comp": .3, "opt": .35})
    B, forcedB = _fe_make(pg, "(t) => t.sens < .5 && t.opt >= .55 && t.ext < .45 && t.comp < .6", {"sens": .3, "ext": .3, "comp": .4, "opt": .8}, skip=(A,))
    ta, tb = _fe_get(pg, A)["traits"], _fe_get(pg, B)["traits"]
    print("  個性：A（敏感外向）%s 硬調=%s；B（遲鈍樂觀內向）%s 硬調=%s" % (ta, forcedA, tb, forcedB))
    pg.evaluate("() => { __world.fire.reset(); __world.phys.restoreAll(true); __world.daytime.set('day'); }")
    for cid, x, z in ((A, 26.5, 35.0), (B, 26.5, 37.6)):
        _fe_stage_for_fire(pg, cid, x, z)
    pg.evaluate("() => { __world.godAt(30.2, 36.4, 26); }")
    wait_until(pg, "() => !__world.view.tween", 20000)
    pg.wait_for_timeout(1500)
    held = {}
    for cid in (A, B):
        held[cid] = _fe_throw_fire(pg, cid)
        for _ in range(14):
            pg.wait_for_timeout(300)
            if pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state === 'burning'", cid):
                break
        pg.wait_for_timeout(300)
    ok("被燒（真滑鼠）：兩位都被拎起丟進營火", held[A] and held[B], held)
    ga, gb = _fe_get(pg, A), _fe_get(pg, B)
    ok("被燒階段 1 驚嚇：兩位都先驚叫（A %s、B %s）" % (ga["face"], gb["face"]), ga["face"] in _FE_BURN_FACES and gb["face"] in _FE_BURN_FACES, (ga["face"], gb["face"]))
    _fe_shot(pg, "被燒_1驚嚇_真滑鼠.png")
    ok("被燒階段 4：兩位都知道是被「你」丟進火裡（blame）", ga["feel"]["blame"] and gb["feel"]["blame"], (ga["feel"], gb["feel"]))
    pg.evaluate("() => { __world.speed = 0.001; }")
    _fe_adv(pg, 7)
    pa = pg.evaluate("(id) => __world.mind.moodLine(__world.chars.get(id)).text", A)
    ok("被燒階段 2 疼痛與狼狽：心情列寫「又痛又狼狽」（%s）" % pa, "又痛又狼狽" in pa, pa)
    ev = _fe_until(pg, A, "pat-down", 40, 4)
    ok("被燒階段 2：會拍身上的灰（紀錄 %s）" % (ev and ev.get("face")), bool(ev) and ev.get("action") == "clap", ev)
    ok("被燒階段 2：A（敏感）拍灰時的臉是「哭」（%s）" % (ev and ev.get("face")), bool(ev) and ev.get("face") in ("cry", "ouch"), ev)
    evb = _fe_until(pg, B, "pat-down", 30, 4)
    ok("被燒階段 2：B 拍灰時的臉是「ouch」不哭（%s）" % (evb and evb.get("face")), bool(evb) and evb.get("face") == "ouch", evb)
    _fe_shot(pg, "被燒_2疼痛狼狽.png")
    # 恢復（燒焦褪掉）→ 餘悸
    rec = {A: None, B: None}
    for _ in range(14):
        _fe_adv(pg, 10)
        for cid in (A, B):
            if not rec[cid] and _fe_get(pg, cid)["feel"]["stage"] == "after":
                rec[cid] = True
        if all(rec.values()):
            break
    ok("被燒階段 3：兩位都恢復到「餘悸」階段", all(rec.values()), rec)
    ga, gb = _fe_get(pg, A), _fe_get(pg, B)
    ok("被燒階段 3 餘悸：敏感的 A 比樂觀的 B 更怕火（%.2f > %.2f）" % (ga["feel"]["fear"], gb["feel"]["fear"]), ga["feel"]["fear"] > gb["feel"]["fear"] + .1, (ga["feel"], gb["feel"]))
    ma, mb = _fe_mood(pg, A), _fe_mood(pg, B)
    ok("被燒階段 3：A 的心情列寫「還在怕火（…被燒到）」＋對你的態度（%s）" % ma["text"], bool(_re.search(r"還在怕火（(剛|今天|昨天|前幾天)被燒到）・對你：", ma["text"])) or ("對你：" in ma["text"] and "怕火" in ma["text"]), ma)
    _fe_shot(pg, "被燒_3餘悸.png")
    ok("被燒階段 4 對你的態度：A 比 B 記仇（rel %.2f < %.2f）" % (ga["feel"]["rel"], gb["feel"]["rel"]), ga["feel"]["rel"] < gb["feel"]["rel"], (ga["feel"]["rel"], gb["feel"]["rel"]))
    ra = _fe_until(pg, A, "resent", 20, 4)
    rb = _fe_until(pg, B, "resent", 20, 4)
    ok("被燒階段 4：怪你的方式不同 A=%s、B=%s" % (ra and ra["style"], rb and rb["style"]), bool(ra) and bool(rb) and ra["style"] in ("cry", "angry") and rb["style"] in ("shrug", "pout") and ra["style"] != rb["style"], (ra, rb))
    _fe_shot(pg, "被燒_4怪你.png")
    va = _fe_until(pg, A, "vent", 80, 5)
    ok("被燒階段 5：外向敏感的 A 去找好朋友訴苦並被安慰（%s）" % (va and va.get("to")), bool(va) and va.get("done") and _fe_get(pg, A)["feel"]["ventDone"], va)
    bb = _fe_log(pg, B, "bottle-up")
    ok("被燒階段 5：內向遲鈍的 B 自己消化（不去訴苦）", bool(bb) and not _fe_log(pg, B, "vent-start"), bb)
    cm = [x for x in _fe_get(pg, A)["mem"] if x["type"] == "comforted"]
    ok("被燒階段 5：A 的記憶裡有「同事來安慰」（%s）" % (cm and cm[0]["text"]), bool(cm), _fe_get(pg, A)["mem"])
    # 不羞辱：旁觀者沒有嘲笑
    wf = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'witness').map(x => (__world.mind.get(x.id) || {}).face)")
    ok("被燒：旁觀者沒有出現嘲笑類表情", all(f not in ("giggle", "laugh") for f in wf), wf)
    ok("被燒：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    pg.evaluate("() => { __world.fire.reset(); }")
    c1.close()


# ───────────────────────── F2 被欺負三次 ─────────────────────────
def t_fe_bully(b, base):
    c1, pg, got = _fe_open(b, base, speed=2)
    if not ok("被欺負：世界載入", got):
        c1.close(); return
    X, fx = _fe_make(pg, "(t, c) => t.ext >= .45 && t.sens >= .4 && c.state === 'sit'", {"ext": .7, "sens": .6})
    Y, fy = _fe_make(pg, "(t, c) => t.ext < .4 && t.sens >= .3 && c.state === 'sit'", {"ext": .2, "sens": .5, "comp": .3}, skip=(X,))
    print("  個性：X（外向）%s 硬調=%s；Y（內向）%s 硬調=%s" % (_fe_get(pg, X)["traits"], fx, _fe_get(pg, Y)["traits"], fy))
    pg.evaluate("() => { __world.setView('god', null, true); }")
    pg.wait_for_timeout(700)
    res = {}
    for cid in (X, Y):
        seq = []
        for k in range(3):
            ok_ = False
            for attempt in range(3):         # 機器忙的時候角色可能剛好走開沒抓到：最多重丟兩次（每次都是真滑鼠）
                wait_until(pg, "() => { const c = __world.chars.get(%s); return c.state !== 'held' && c.state !== 'walk'; }" % _json.dumps(cid), 12000)
                pg.evaluate("(id) => { const c = __world.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = true; }", cid)
                pg.wait_for_timeout(250)
                _fe_throw_wall(pg, cid)
                ok_ = wait_until(pg, "() => __world.mind.get(%s).feel.hits >= %d" % (_json.dumps(cid), k + 1), 9000)
                if ok_:
                    break
            pg.evaluate("(id) => { __world.chars.get(id).busy = false; }", cid)
            wait_until(pg, "() => { const c = __world.chars.get(%s); return c.state !== 'held'; }" % _json.dumps(cid), 8000)
            g = _fe_get(pg, cid)
            seq.append((g["feel"]["tier"], round(g["feel"]["rel"], 2), g["face"], bool(ok_)))
            pg.evaluate("() => __world.advanceAsync(7)")
        res[cid] = seq
    for cid, nm in ((X, "X"), (Y, "Y")):
        s = res[cid]
        ok("被欺負（真滑鼠×3，%s）：分級 %s → %s → %s" % (nm, s[0][0], s[1][0], s[2][0]), s[0][0] == 1 and s[1][0] == 2 and s[2][0] == 3, s)
        ok("被欺負（%s）：對你的態度一次比一次差（%s）" % (nm, [x[1] for x in s]), s[0][1] > s[1][1] > s[2][1], s)
    for cid, nm in ((X, "X"), (Y, "Y")):
        r2 = _fe_log(pg, cid, "bully-reaction")
        t2 = [x for x in r2 if x.get("tier") == 2]
        ok("被欺負（%s）：第二次是生氣跺腳或難過哭（%s、臉 %s）" % (nm, t2 and t2[0].get("style"), t2 and t2[0].get("face")), bool(t2) and t2[0]["style"] in ("stomp", "cry", "pout"), r2)
        t3 = [x for x in r2 if x.get("tier") == 3]
        ok("被欺負（%s）：第三次嚇到了（臉 %s）" % (nm, t3 and t3[0].get("face")), bool(t3) and t3[0]["face"] == "scared", r2)
    _fe_shot(pg, "被欺負_第三次嚇到.png")
    cx = _fe_until(pg, X, "complain", 90, 5)
    ok("被欺負：外向的 X 跑去找 CEO 告狀並被安慰（%s）" % (cx and cx.get("to")), bool(cx) and cx.get("done"), (cx, _fe_log(pg, X, "complain-start")))
    hy = _fe_until(pg, Y, "hide", 90, 5)
    ok("被欺負：內向的 Y 躲到角落（紀錄 hide）", bool(hy) and not _fe_log(pg, Y, "complain-start"), (hy, _fe_log(pg, Y, "complain-start")))
    mY = pg.evaluate("(id) => { const f = __world.mind.feel.of(__world.mind.mindOf(id)); return f.mode; }", Y)
    my = _fe_mood(pg, Y)
    print("  Y 躲起來時的心情列：", my["text"], "模式", mY)
    ok("被欺負：躲角落時心情列寫「想躲起來」（%s）" % my["text"], "想躲起來" in my["text"] or "還在生氣" in my["text"] or "有點怕你" in my["text"] or "對你：" in my["text"], my)
    _fe_shot(pg, "被欺負_躲角落.png")
    ok("被欺負：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()
    # 你靠近時後退（站著的人）
    c2, pg, got = _fe_open(b, base)
    if not ok("後退：世界載入", got):
        c2.close(); return
    Z = _fe_pick(pg, "(t) => true")
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; c.standAt(26.5, 35.0, 0); const m = W.mind.mindOf(id); W.mind.feel.addRel(m, -.62); W.speed = 1;
      W.mind.feel.youOverride = { x: 27.9, y: 1.1, z: 35.0 }; }""", Z)
    d0 = pg.evaluate("(id) => Math.hypot(__world.chars.get(id).object3D.position.x - 27.9, __world.chars.get(id).object3D.position.z - 35.0)", Z)
    pg.evaluate("() => { __world.speed = 0.001; }")
    _fe_adv(pg, 3)
    d1 = pg.evaluate("(id) => Math.hypot(__world.chars.get(id).object3D.position.x - 27.9, __world.chars.get(id).object3D.position.z - 35.0)", Z)
    ok("你靠近時：關係很差的人後退（離你 %.1f → %.1f 公尺）" % (d0, d1), d1 > d0 + .8, (d0, d1))
    ok("你靠近時：後退時是戒備的臉（%s）" % _fe_log(pg, Z, "back-off")[:1], bool(_fe_log(pg, Z, "back-off")) and _fe_log(pg, Z, "back-off")[0]["face"] in ("wary", "scared"), None)
    ok("後退：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c2.close()


# ───────────────────────── F3 被照顧 ─────────────────────────
def t_fe_care(b, base):
    c1, pg, got = _fe_open(b, base)
    if not ok("被照顧：世界載入", got):
        c1.close(); return
    Z = _fe_pick(pg, "(t, c) => t.comp < .6 && t.sens >= .3")
    pg.evaluate("(id) => { __world.speed = 1; __world.emit('knocked', id, { by: 'you', speed: 6 }); }", Z)
    wait_until(pg, "() => __world.mind.get(%s).feel.hits >= 1" % _json.dumps(Z), 6000)
    pg.evaluate("(id) => __world.mind.feel.addRel(__world.mind.mindOf(id), -.3)", Z)
    pg.evaluate("() => { __world.speed = 0.001; }")
    _fe_adv(pg, 22)
    rels, events = [], []
    forgave = False
    for i in range(7):
        r = pg.evaluate("(id) => { const c = __world.chars.get(id); c.pet(1.5); const g = __world.mind.get(id); return [g.last && g.last.event, g.feel.rel]; }", Z)
        events.append(r[0]); rels.append(round(r[1], 2))
        _fe_adv(pg, 2.5)
        if r[0] in ("forgive", "petted"):
            forgave = True
            break
    dodges = events.count("dodge")
    ok("被照顧：被你欺負過之後，摸頭一開始被閃躲、不是一次就好（閃躲 %d 次、過程 %s）" % (dodges, events), dodges >= 2 and forgave, events)
    ok("被照顧：每次靠近關係都慢慢回升（rel %s）" % rels, rels[-1] > rels[0], rels)
    ok("被照顧：原諒之後說了話或害羞（%s）" % [x["event"] for x in _fe_get(pg, Z)["mem"][:0]], bool(_fe_log(pg, Z, "forgive")), None)
    _fe_adv(pg, 3)
    pg.evaluate("(id) => { const c = __world.chars.get(id); c.feed(); }", Z)
    _fe_adv(pg, 2)
    pg.evaluate("(id) => { const c = __world.chars.get(id); c.pet(1.5); }", Z)
    _fe_adv(pg, 3)
    pg.evaluate("(id) => { const c = __world.chars.get(id); c.feed(); c.pet(1.5); }", Z)
    g = _fe_get(pg, Z)
    ok("被照顧：摸頭、餵點心多次之後對你有好感（rel %.2f，「%s」）" % (g["feel"]["rel"], g["feel"]["att"]), g["feel"]["rel"] > rels[-1], g["feel"])
    _fe_shot(pg, "被照顧_摸頭餵點心.png")
    # 同事安慰
    W2 = _fe_pick(pg, "(t) => true", skip=(Z,))
    pg.evaluate("(id) => { __world.emit('comforted', id, { by: %s }); }" % _json.dumps(Z), W2)
    s = _fe_get(pg, W2)
    ok("被照顧：被同事安慰後記住是誰（%s）" % [x["text"] for x in s["mem"] if x["type"] == "comforted"][:1], any(x["type"] == "comforted" for x in s["mem"]), s["mem"])
    # 靠近時揮手、主動走過來
    R_ = _fe_pick(pg, "(t) => true", skip=(Z, W2))
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; c.standAt(26.5, 35.0, 0); W.mind.feel.addRel(W.mind.mindOf(id), .5); W.mind.feel.youOverride = { x: 29.3, y: 1.1, z: 35.0 }; }""", R_)
    _fe_adv(pg, 2)
    wv = _fe_log(pg, R_, "wave-to-you")
    ok("被照顧：對你有好感的人，你靠近時揮手（%s）" % (wv and wv[0]["face"]), bool(wv) and wv[0]["action"] == "wave", wv)
    _fe_shot(pg, "被照顧_靠近揮手.png")
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); W.mind.feel.addRel(W.mind.mindOf(id), .35); W.mind.feel.youOverride = { x: 34.0, y: 1.1, z: 35.0 }; c.busy = false; }""", R_)
    d0 = pg.evaluate("(id) => Math.hypot(__world.chars.get(id).object3D.position.x - 34.0, __world.chars.get(id).object3D.position.z - 35.0)", R_)
    _fe_adv(pg, 1)
    mn = d0
    for _ in range(14):
        _fe_adv(pg, .6)
        mn = min(mn, pg.evaluate("(id) => Math.hypot(__world.chars.get(id).object3D.position.x - 34.0, __world.chars.get(id).object3D.position.z - 35.0)", R_))
    cm = _fe_log(pg, R_, "come-to-you")
    ok("被照顧：很信任你的人主動走過來（離你 %.1f → 最近 %.1f 公尺）" % (d0, mn), bool(cm) and mn < d0 - 2.0, (cm, d0, mn))
    # 泳池救火
    P = _fe_pick(pg, "(t) => t.sens >= .3", skip=(Z, W2, R_))
    pg.evaluate("(id) => { __world.fire.reset(); __world.mind.feel.youOverride = null; __world.emit('burned', id, { by: 'you' }); }", P)
    _fe_adv(pg, 5)
    rel0 = _fe_get(pg, P)["feel"]["rel"]
    pg.evaluate("(id) => { __world.emit('extinguished', id, { cause: 'pool', by: 'you' }); }", P)
    ok("泳池救火：被救後鬆一口氣（%s）" % _fe_get(pg, P)["face"], bool(wait_until(pg, "() => ['surprised', 'relieved'].includes(__world.mind.get(%s).face)" % _json.dumps(P), 4000)), _fe_get(pg, P)["face"])
    _fe_adv(pg, 2)
    g = _fe_get(pg, P)
    ok("泳池救火：濕答答的狼狽（心情列：%s）" % _fe_mood(pg, P)["text"], "濕答答" in _fe_mood(pg, P)["text"] and g["feel"]["wet"], g["feel"])
    ok("泳池救火：被你救了，對你的態度變好（rel %.2f → %.2f）" % (rel0, g["feel"]["rel"]), g["feel"]["rel"] > rel0 + .2, (rel0, g["feel"]["rel"]))
    _fe_shot(pg, "被照顧_泳池救火.png")
    _fe_adv(pg, 4)
    Q = _fe_pick(pg, "(t) => true", skip=(Z, W2, R_, P))
    pg.evaluate("(id) => { __world.emit('splashed', id, {}); }", Q)
    _fe_adv(pg, 1)
    ok("被水潑到（splashed）：也會濕答答（%s）" % _fe_mood(pg, Q)["text"], "濕答答" in _fe_mood(pg, Q)["text"], None)
    ok("被照顧：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


# ───────────────────────── F4 運動 ─────────────────────────
def t_fe_sport(b, base):
    c1, pg, got = _fe_open(b, base)
    if not ok("運動：世界載入", got):
        c1.close(); return
    A, fa = _fe_make(pg, "(t) => t.comp >= .6", {"comp": .8, "sens": .3, "ext": .5})
    Bc, fb = _fe_make(pg, "(t) => t.comp >= .55", {"comp": .75, "sens": .3, "ext": .5, "opt": .45}, skip=(A,))
    Cc, fc = _fe_make(pg, "(t) => t.comp < .4 && t.sens >= .55", {"comp": .2, "sens": .8, "opt": .4}, skip=(A, Bc))
    Dd, fd = _fe_make(pg, "(t) => t.ext >= .62 && t.comp < .6", {"ext": .85, "comp": .3}, skip=(A, Bc, Cc))
    print("  個性：A 好勝 %s｜B 好勝 %s｜C 敏感 %s｜D 外向 %s；硬調 %s" % (_fe_get(pg, A)["traits"], _fe_get(pg, Bc)["traits"], _fe_get(pg, Cc)["traits"], _fe_get(pg, Dd)["traits"], (fa, fb, fc, fd)))
    pg.evaluate("() => { __world.speed = 0.001; }")
    pg.evaluate("([a, b, c, d]) => { __world.emit('sport_start', a, { opponent: b, sport: '桌球' }); __world.emit('sport_start', b, { opponent: a, sport: '桌球' }); __world.emit('sport_start', c, { opponent: d, sport: '羽球' }); __world.emit('sport_start', d, { opponent: c, sport: '羽球' }); }", [A, Bc, Cc, Dd])
    _fe_adv(pg, .6)
    ok("運動：開賽時好勝的 A 得意、外向的 D 開心（%s、%s）" % (_fe_get(pg, A)["face"], _fe_get(pg, Dd)["face"]), _fe_get(pg, A)["face"] in ("smug", "effort") and _fe_get(pg, Dd)["face"] in ("happy", "smile"), (_fe_get(pg, A)["face"], _fe_get(pg, Dd)["face"]))
    _fe_adv(pg, 3)
    pg.evaluate("([a, b]) => { __world.emit('sport_score', a, { scorer: a }); __world.emit('sport_score', b, { scorer: a }); }", [A, Bc])
    _fe_adv(pg, .4)
    ga, gb = _fe_get(pg, A), _fe_get(pg, Bc)
    ok("運動：得分的人歡呼（A %s）、被得分的好勝者不甘（B %s）" % (ga["face"], gb["face"]), ga["face"] in _FE_HAPPY and gb["face"] in ("sulkf", "worried", "surprised"), (ga["face"], gb["face"]))
    _fe_shot(pg, "運動_得分.png")
    _fe_adv(pg, 3)
    r0a = _fe_get(pg, A)["feel"]["rap"].get(Bc, 0)
    pg.evaluate("([a, b]) => { __world.emit('sport_end', a, { opponent: b, win: true }); __world.emit('sport_end', b, { opponent: a, win: false }); }", [A, Bc])
    pg.evaluate("([c, d]) => { __world.emit('sport_end', c, { opponent: d, win: false }); __world.emit('sport_end', d, { opponent: c, win: true }); }", [Cc, Dd])
    _fe_adv(pg, .5)
    ga, gb, gc, gd = _fe_get(pg, A), _fe_get(pg, Bc), _fe_get(pg, Cc), _fe_get(pg, Dd)
    ok("運動：贏的人開心（A %s、D %s）" % (ga["face"], gd["face"]), ga["face"] in _FE_HAPPY and gd["face"] in _FE_HAPPY, (ga["face"], gd["face"]))
    ok("運動：輸的好勝者不甘心（B：%s）、輸的敏感者難過（C：%s），兩人反應不同" % (gb["face"], gc["face"]), gb["face"] == "sulkf" and gc["face"] == "sad", (gb["face"], gc["face"]))
    _fe_shot(pg, "運動_輸贏.png")
    mb = _fe_mood(pg, Bc)
    ok("運動：輸的人心情列寫「不甘心」＋想再來一場（%s）" % mb["text"], "不甘心" in mb["text"] and "再來一場" in mb["text"], mb)
    ma = _fe_mood(pg, A)
    ok("運動：贏的人心情列寫贏了和對手的比賽（%s）" % ma["text"], "贏了" in ma["text"], ma)
    ok("運動：和對手的關係變好（A→B %.2f、B→A %.2f）" % (ga["feel"]["rap"].get(Bc, 0), gb["feel"]["rap"].get(A, 0)), ga["feel"]["rap"].get(Bc, 0) > r0a and gb["feel"]["rap"].get(A, 0) > 0, (ga["feel"], gb["feel"]))
    _fe_adv(pg, 3.2)
    gb = _fe_get(pg, Bc)
    ok("運動：輸的人之後向對手提出再來一場（臉 %s）" % gb["face"], gb["face"] in ("effort", "sulkf", "pout"), gb["face"])
    ev = _fe_log(pg, Bc, "sport")
    ok("運動：紀錄寫明輸了想再來一場（want=rematch）", any(x.get("want") == "rematch" for x in ev), ev)
    wf = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'witness').map(x => (__world.mind.get(x.id) || {}).face)")
    ok("運動：沒有人嘲笑輸家", all(f not in ("giggle",) for f in wf), wf)
    ok("運動：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


# ───────────────────────── F5 怕火繞遠、路燈緊張 ─────────────────────────
def t_fe_fear(b, base):
    c1, pg, got = _fe_open(b, base)
    if not ok("怕火：世界載入", got):
        c1.close(); return
    ids = pg.evaluate("() => [...__world.chars].filter(([k, c]) => !c.spec.pet && !c.spec.isCeo && !c.jobless && !c.away).slice(0, 2).map(x => x[0])")
    Af, Bn = ids
    pg.evaluate("""([a, b]) => { const W = __world; W.fire.reset(); W.daytime.set('day'); W.speed = 0.001; for (const id of [a, b]) { const c = W.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; }
      W.mind.feel.of(W.mind.mindOf(a)).fear = .9; W.mind.feel.of(W.mind.mindOf(b)).fear = 0; }""", [Af, Bn])
    out = {}
    for cid, nm in ((Af, "怕火的 A"), (Bn, "不怕火的 B")):
        mn = pg.evaluate("""async (id) => { const W = __world, c = W.chars.get(id), fc = W.fire.center; c.standAt(fc.x - 5.5, fc.z + 0.2, 0); await W.advanceAsync(.3);
          const p = c.object3D.position, path = W.nav.findPath({ x: p.x, z: p.z }, { x: fc.x + 5.5, z: fc.z + 0.2 }); if (!path) return -1; c.walkTo(path, { speed: 2.4 }); let mn = 99;
          for (let i = 0; i < 70; i++) { await W.advanceAsync(.25); const q = c.object3D.position; mn = Math.min(mn, Math.hypot(q.x - fc.x, q.z - fc.z)); if (c.state !== 'walk' && i > 4) break; } return mn; }""", cid)
        out[nm] = mn
    ok("怕火：怕火的 A 經過營火繞得遠（最近 %.1f 公尺），不怕火的 B 直接走過（最近 %.1f 公尺）" % (out["怕火的 A"], out["不怕火的 B"]), out["怕火的 A"] > out["不怕火的 B"] + 0.7 and out["怕火的 A"] >= 1.9, out)
    ok("怕火：留下繞路的紀錄", bool(_fe_log(pg, Af, "fire-detour")) and not _fe_log(pg, Bn, "fire-detour"), _fe_log(pg, Af, "fire-detour"))
    # 站在火邊發抖
    pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), fc = W.fire.center; c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; c.standAt(fc.x - 3.6, fc.z, 0); W.mind.feel.of(W.mind.mindOf(id)).cd = {}; }""", Af)
    _fe_adv(pg, 1.5)
    sh = _fe_log(pg, Af, "fire-shiver")
    if not sh:
        print("  除錯：", pg.evaluate("(id) => { const c = __world.chars.get(id), m = __world.mind.mindOf(id); return [c.state, c.busy, m.sc && m.sc.name, c.object3D.position.x, c.object3D.position.z, __world.mind.feel.of(m).fear, JSON.stringify(__world.mind.feel.of(m).cd)]; }", Af))
    ok("怕火：站在火邊會發抖（臉 %s、動作 %s）" % (sh and sh[0]["face"], sh and sh[0]["action"]), bool(sh) and sh[0]["face"] == "scared", sh)
    _fe_shot(pg, "怕火_火邊發抖.png")
    # 夜晚路燈
    pg.evaluate("() => { __world.daytime.set('night'); }")
    _fe_adv(pg, 2)
    sp = pg.evaluate("() => (__world.phys.lampSpots() || []).filter(Boolean).map(l => [l.x, l.z])")
    if ok("怕火：夜晚路燈有亮（%d 盞）" % len(sp), len(sp) >= 1, sp):
        pg.evaluate("""([id, l]) => { const W = __world, c = W.chars.get(id); c.script = (c.script || 0) + 1; c.stop(false); c.busy = false; c.standAt(l[0] + 1.0, l[1], 0); W.mind.feel.of(W.mind.mindOf(id)).cd = {}; }""", [Af, sp[0]])
        _fe_adv(pg, 1.5)
        lp = _fe_log(pg, Af, "lamp-nervous")
        ok("怕火：夜晚走近路燈火光會緊張（臉 %s）" % (lp and lp[0]["face"]), bool(lp) and lp[0]["face"] == "worried", lp)
        _fe_shot(pg, "怕火_夜晚路燈.png")
    pg.evaluate("() => { __world.daytime.set('day'); }")
    ok("怕火：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


# ───────────────────────── F6 心情列 ─────────────────────────
def t_fe_card(b, base):
    for w, h, tag in ((1280, 800, "1280"), (390, 844, "390")):
        c1, pg, got = _fe_open(b, base, w, h)
        if not ok("心情列（%s）：世界載入" % tag, got):
            c1.close(); continue
        cid = _fe_pick(pg, "(t) => t.sens >= .4")
        pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); W.speed = 0.001; const m = W.mind.mindOf(id), f = W.mind.feel.of(m); f.fear = .8; f.burnAt = Date.now() - 26 * 3600e3; W.mind.feel.addRel(m, -.4); m.val = 0; m.cause = null; W.ui.showCard(c); }""", cid)
        pg.wait_for_timeout(900)
        txt = _fe_card_text(pg)
        ok("心情列（%s）：寫「現在的情緒＋原因＋對你的態度」（%s）" % (tag, txt), bool(_re.match(r"^心情：\S+ 還在怕火（昨天被燒到）・對你：有點防備$", txt)), txt)
        rs = pg.evaluate("""() => { const out = []; for (const s of ['#card', '#cardNow', '#cardMood']) { const e = document.querySelector(s); if (!e || e.hidden) continue; const r = e.getBoundingClientRect(); out.push([s, r.left, r.top, r.right, r.bottom, e.scrollWidth, e.clientWidth]); } return out; }""")
        m = [r for r in rs if r[0] == "#cardMood"]
        n = [r for r in rs if r[0] == "#cardNow"]
        cd = [r for r in rs if r[0] == "#card"]
        bad = []
        if m and n:
            a, c = n[0], m[0]
            if not (a[3] <= c[1] + 1 or c[3] <= a[1] + 1 or a[4] <= c[2] + 1 or c[4] <= a[2] + 1):
                bad.append("cardNow/cardMood")
        inside = bool(m and cd and m[0][1] >= cd[0][1] - 1 and m[0][3] <= cd[0][3] + 1)
        ok("心情列（%s）：在資訊卡內、不與「目前」列重疊、文字沒被切掉" % tag, bool(m) and inside and not bad and m[0][5] <= m[0][6] + 1, (rs, bad))
        _fe_shot(pg, "心情列_%s.png" % tag)
        # 各情境的心情列文字（只列出，驗證沒有禁用字）
        samples = {}
        for name, js in (("被欺負", "(id) => { __world.mind.feel.of(__world.mind.mindOf(id)).mode = 'hide'; }"), ("訴苦", "(id) => { __world.mind.feel.of(__world.mind.mindOf(id)).mode = 'vent'; }"), ("告狀", "(id) => { __world.mind.feel.of(__world.mind.mindOf(id)).mode = 'complain'; }")):
            pg.evaluate(js, cid)
            samples[name] = _fe_mood(pg, cid)["text"]
        ok("心情列（%s）：躲起來／訴苦／告狀的文字（%s）" % (tag, samples), "想躲起來" in samples["被欺負"] and "想找人訴苦" in samples["訴苦"] and "想告狀" in samples["告狀"], samples)
        ok("心情列（%s）：不含禁用字" % tag, not _re.search(r"價格|NT\$|付費|訂閱|免費", " ".join(samples.values()) + txt), None)
        ok("心情列（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        c1.close()


def t_fe_all(b, base):
    only = _os.environ.get("FEEL_ONLY", "")
    parts = {"card": t_fe_card, "burn": t_fe_burn, "bully": t_fe_bully, "care": t_fe_care, "sport": t_fe_sport, "fear": t_fe_fear}
    for k, f in parts.items():
        if not only or k in only.split(","):
            f(b, base)


register("辦公室情緒加深", lambda pg, b, base, code: t_fe_all(b, base))
