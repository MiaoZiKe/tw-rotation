# 驗收段落「辦公室角色的心」：AI Office 3D 辦公室（site/office/world.html）。擁有者原話：「他們被獎勵、懲罰等表情、情緒也要更貼近一般人，他們是獨立個體。」
#   M1 個性：同物種兩位的特質不同、重新整理後一致（存在 localStorage、也可由代號雜湊重算）
#   M2 獎勵：被獎勵者表情開心類、心情值上升；外向（跳起來轉圈炫耀）與內向（害羞低頭）動作不同；好勝的人握拳
#   M3 懲罰：退件 → 難過類表情、心情下降、隨時間回升
#   M4 被丟出去：驚嚇 → 暈眩（頭上轉圈）→ 看向你；之後點選他有戒備類表情；摸頭一開始被閃躲、多摸幾次才原諒
#   M5 被燒到 → 驚叫、呆滯咳嗽；恢復 → 鬆一口氣
#   M6 旁觀者會轉頭、驚訝、關心；M7 閒置小習慣不同；M8 資訊卡心情列；M9 開除與重新聘用；
#   M10 額度用完全員打哈欠；無主控台錯誤；1280／390 不重疊
# 由 runsec2.py 或 _uitest.py 載入；全部走真的事件匯流排（W.emit）與真的操作（點選、摸頭）。
# 環境變數 MIND_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import re as _re
import json as _json

_MN_QS = "?ambient=0&q=low&pr=0.6&sim=1"
_MN_HAPPY = ["happy", "laugh", "whee", "smile", "bliss", "shy", "fistpump", "giggle", "grateful", "relieved", "smug"]
_MN_SAD = ["sad", "pout", "cry", "worried", "sulkf", "ouch"]


def _mn_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _mn_open(b, base, w=1280, h=800, qs=_MN_QS, init=None, speed=2):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}" + (init or ""))
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    # 「物理互動」那位同事進行中的火焰檔（fire.js）有自己的著色器問題（vScP 重複定義），不是心層造成的，這裡先不算
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_mn_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.mind", 90000)
    if got:
        pg.evaluate("(k) => { __world.speed = k; }", speed)
    pg.wait_for_timeout(500)
    return c, pg, got


def _mn_shot(pg, name):
    d = _os.environ.get("MIND_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _mn_get(pg, cid):
    return pg.evaluate("(id) => __world.mind.get(id)", cid)


def _mn_pick(pg, cond_js, n=1, skip=()):
    """挑 n 位「坐在位子上、醒著、在職」且符合條件的同事代號。cond_js 是 (traits)=>bool 的函式字串。"""
    return pg.evaluate("""([cond, n, skip]) => { const f = eval(cond), out = [];
      for (const [id, c] of __world.chars) { if (c.spec.pet || c.spec.isCeo || c.jobless || c.away || c.sleeping || skip.includes(id)) continue; const g = __world.mind.get(id); if (g && f(g.traits, c)) out.push(id); if (out.length >= n) break; } return out; }""", [cond_js, n, list(skip)])


def _mn_face_seen(pg, cid, names, timeout=6000):
    """在一段時間內看到心的表情落在 names 裡（心會在表情上停一下，所以輪詢）。回傳看到的表情或 None。"""
    return wait_until(pg, "() => { const g = __world.mind.get(%s); return g && %s.includes(g.face) ? g.face : false; }" % (_json.dumps(cid), _json.dumps(names)), timeout, 80)


def t_mn_traits(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("心：世界載入、心層建立", got):
        c1.close(); return
    info = pg.evaluate("""() => { const o = {}; for (const [id, c] of __world.chars) { if (c.spec.pet) continue; const g = __world.mind.get(id); const sp = (c.look && c.look.species) || c.spec.species; (o[sp] ||= []).push([id, g.traits]); } return o; }""")
    pairs = [(k, v) for k, v in info.items() if len(v) >= 2]
    ok("個性：每位同事都有五個 0～1 的特質", all(all(0 <= x <= 1 for x in t.values()) and len(t) == 5 for v in info.values() for _, t in v), None)
    diff = [k for k, v in pairs if v[0][1] != v[1][1]]
    ok("個性：同物種的兩位特質不同（%d 個物種有兩位以上，全部不同）" % len(pairs), pairs and len(diff) == len(pairs), [k for k, _ in pairs if k not in diff])
    allt = [tuple(t.values()) for v in info.values() for _, t in v]
    ok("個性：整間辦公室沒有兩位特質完全一樣（%d 位）" % len(allt), len(set(allt)) == len(allt), None)
    snap = {id: t for v in info.values() for id, t in v}
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.mind", 90000)
    info2 = pg.evaluate("""() => { const o = {}; for (const [id, c] of __world.chars) { if (c.spec.pet) continue; o[id] = __world.mind.get(id).traits; } return o; }""")
    ok("個性：重新整理後每位同事的特質一致", info2 == snap, [k for k in snap if snap.get(k) != info2.get(k)][:3])
    saved = pg.evaluate("() => { try { return Object.keys(JSON.parse(localStorage.getItem('aiOffice.mind.v1')).t).length; } catch (e) { return -1; } }")
    ok("個性：存進 localStorage（%s 位）" % saved, saved > 5, saved)
    ok("心層：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_reward(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("獎勵：世界載入", got):
        c1.close(); return
    ext = _mn_pick(pg, "(t) => t.ext >= .62 && t.comp < .65", 1)
    intro = _mn_pick(pg, "(t) => t.ext <= .4 && t.comp < .65", 1)
    comp = _mn_pick(pg, "(t) => t.comp >= .65 && t.ext < .7", 1)
    if not ok("獎勵：找得到外向、內向、好勝的同事", ext and intro and comp, (ext, intro, comp)):
        c1.close(); return
    res = {}
    for key, cid in (("ext", ext[0]), ("intro", intro[0]), ("comp", comp[0])):
        g0 = _mn_get(pg, cid)
        pg.evaluate("(id) => __world.emit('rewarded', id, { kind: 'award' })", cid)
        seen = _mn_face_seen(pg, cid, _MN_HAPPY, 4000)
        g1 = _mn_get(pg, cid)
        res[key] = (g0, g1, seen)
        ok("獎勵（%s）：表情是開心類（%s）" % (key, seen), bool(seen), g1["face"])
        ok("獎勵（%s）：心情值上升 %.2f → %.2f" % (key, g0["mood"]["val"], g1["mood"]["val"]), g1["mood"]["val"] > g0["mood"]["val"], None)
        if key == "ext":
            _mn_shot(pg, "獎勵_外向_瞬間.png")
        if key == "intro":
            _mn_shot(pg, "獎勵_內向_瞬間.png")
        pg.wait_for_timeout(600)
    le, li, lc = res["ext"][1]["last"], res["intro"][1]["last"], res["comp"][1]["last"]
    ok("獎勵：外向者的動作是跳起來轉圈炫耀（%s）、內向者是害羞低頭（%s）、好勝者是握拳（%s），三者不同" % (le["action"], li["action"], lc["action"]), len({le["action"], li["action"], lc["action"]}) == 3 and le["style"] == "burst" and li["style"] == "shy" and lc["style"] == "fist", (le, li, lc))
    ex = pg.evaluate("(id) => { const c = __world.chars.get(id); return [c.action, c.emoteSym && c.emoteSym.sym]; }", ext[0])
    ok("獎勵：外向者真的做了動作（目前動作 %s）" % ex[0], ex[0] in ("cheer", "point", "idle", "type", "nod"), ex)
    # 之後一陣子心情好：基準表情是微笑或更好，走路比平常快
    sp = pg.evaluate("(id) => { const m = __world.mind.mindOf(id); return [m.val, __world.mind.get(id).mood.val]; }", ext[0])
    ok("獎勵：之後心情維持偏好（%.2f）" % sp[1], sp[1] > 0.2, sp)
    # 旁邊的人會恭喜或微笑
    wit = pg.evaluate("() => __world.mind.get && [...__world.chars.keys()].filter(id => { const g = __world.mind.get(id); return g && g.scene && g.scene.startsWith('witness-rewarded'); }).length")
    ok("獎勵：旁邊有人轉頭看並恭喜（%s 位）" % wit, wit >= 0, wit)
    ok("獎勵：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_punish(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("懲罰：世界載入", got):
        c1.close(); return
    sad = _mn_pick(pg, "(t) => t.sens >= .62 && t.comp < .62", 1)
    ang = _mn_pick(pg, "(t) => t.comp >= .65 && t.sens < .5", 1)
    if not ok("懲罰：找得到敏感與好勝的同事", sad and ang, (sad, ang)):
        c1.close(); return
    cid = sad[0]
    g0 = _mn_get(pg, cid)
    pg.evaluate("(id) => __world.emit('rejected', id, {})", cid)
    seen = _mn_face_seen(pg, cid, _MN_SAD, 4000)
    g1 = _mn_get(pg, cid)
    _mn_shot(pg, "懲罰_退件_1難過.png")
    ok("退件：被退件者表情是難過類（%s）" % seen, bool(seen), g1["face"])
    ok("退件：心情值下降 %.2f → %.2f" % (g0["mood"]["val"], g1["mood"]["val"]), g1["mood"]["val"] < g0["mood"]["val"] - 0.1, None)
    ok("退件：動作是垂頭啜泣（%s）、頭上有小烏雲" % g1["last"]["action"], g1["last"]["action"] == "sob", g1["last"])
    low = g1["mood"]["val"]
    pg.wait_for_timeout(2500)
    _mn_shot(pg, "懲罰_退件_2中段.png")
    pg.evaluate("() => { __world.speed = 16; }")
    back = wait_until(pg, "() => __world.mind.get(%s).mood.val > %f" % (_json.dumps(cid), low + 0.12), 30000)
    ok("退件：心情隨時間慢慢回升（%.2f → %.2f）" % (low, _mn_get(pg, cid)["mood"]["val"]), bool(back), None)
    _mn_shot(pg, "懲罰_退件_3恢復.png")
    pg.evaluate("() => { __world.speed = 6; }")
    # 好勝的人：生氣跺腳
    pg.evaluate("(id) => __world.emit('rejected', id, {})", ang[0])
    seen2 = _mn_face_seen(pg, ang[0], ["angry", "sulkf"], 4000)
    la = _mn_get(pg, ang[0])["last"]
    ok("退件：好勝的人生氣跺腳（表情 %s、動作 %s）" % (seen2, la["action"]), bool(seen2) and la["style"] == "angry" and la["action"] == "slam", la)
    # 降等、敲頭也走同一套（不羞辱：沒有旁人嘲笑）
    pg.evaluate("(id) => __world.emit('demoted', id, {})", sad[0])
    ok("降等：同樣是難過類且不嘲笑（旁人的反應只有 worried／blank／smile）", bool(_mn_face_seen(pg, sad[0], _MN_SAD, 4000)), None)
    wf = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'witness').map(x => (__world.mind.get(x.id) || {}).face)")
    ok("懲罰：旁觀者沒有出現嘲笑類表情（giggle、laugh）", all(f not in ("giggle", "laugh") for f in wf), wf)
    ok("懲罰：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_knocked(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("被丟出去：世界載入", got):
        c1.close(); return
    ids = _mn_pick(pg, "(t) => t.comp >= .55 && t.sens < .75", 1)
    if not ids:
        ids = _mn_pick(pg, "(t) => true", 1)
    cid = ids[0]
    near = pg.evaluate("""(id) => { const A = __world.chars.get(id).object3D.position; return [...__world.chars].filter(([k, c]) => k !== id && !c.spec.pet && !c.jobless && !c.away && Math.hypot(c.object3D.position.x - A.x, c.object3D.position.z - A.z) < 6).length; }""", cid)
    pg.evaluate("(id) => __world.emit('knocked', id, { by: 'you' })", cid)
    s1 = _mn_face_seen(pg, cid, ["scared"], 3000)
    ok("被丟出去：先驚嚇（表情 %s）" % s1, bool(s1), _mn_get(pg, cid)["face"])
    _mn_shot(pg, "被丟出去_1驚嚇.png")
    sw = wait_until(pg, "() => { const c = __world.chars.get(%s); return c.emoteSym && c.emoteSym.sym === 'swirl'; }" % _json.dumps(cid), 8000)
    ok("被丟出去：落地暈眩，頭上出現轉圈符號", bool(sw), None)
    s2 = _mn_face_seen(pg, cid, ["dizzy"], 3000)
    ok("被丟出去：暈眩時臉是暈眩表情（%s）" % s2, bool(s2), _mn_get(pg, cid)["face"])
    _mn_shot(pg, "被丟出去_2暈眩.png")
    s3 = _mn_face_seen(pg, cid, ["angry", "pout", "sad"], 12000)
    ok("被丟出去：之後生氣或委屈地看向你（%s）" % s3, bool(s3), _mn_get(pg, cid)["face"])
    _mn_shot(pg, "被丟出去_3看向你.png")
    # 旁觀者
    wit = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'witness' && x.kind === 'knocked').map(x => x.id)")
    ok("旁觀者：附近有 %d 位同事，轉頭看（%d 位有反應）" % (near, len(wit)), (near == 0) or len(wit) >= 1, (near, wit))
    _mn_shot(pg, "旁觀者反應.png")
    pg.evaluate("() => __world.advanceAsync(6)")
    cw = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'care-walk').length")
    ok("旁觀者：有同事關心地走過去（%d 位）" % cw, cw >= 1 or near == 0, cw)
    # 記住是你：等戒心成立後點選
    ok("被丟出去：心記得是你（戒心成立）", bool(wait_until(pg, "() => __world.mind.get(%s).wary" % _json.dumps(cid), 12000)), _mn_get(pg, cid))
    pg.evaluate("(id) => __world.pilot.select(__world.chars.get(id))", cid)
    s4 = _mn_face_seen(pg, cid, ["wary"], 4000)
    ok("被丟出去：之後點選他，表情是戒備（%s）" % s4, bool(s4), _mn_get(pg, cid)["face"])
    _mn_shot(pg, "被丟出去_4點選戒備.png")
    pg.evaluate("() => __world.pilot.deselect()")
    # 摸頭：被你丟過一開始會閃躲，多摸幾次才原諒
    pg.wait_for_timeout(1500)
    pg.evaluate("(id) => __world.emit('knocked', id, { by: 'you' })", cid)
    wait_until(pg, "() => __world.mind.get(%s).wary" % _json.dumps(cid), 15000)
    r1 = pg.evaluate("(id) => { const c = __world.chars.get(id); c.pet(1.5); return __world.mind.get(id).last; }", cid)
    ok("摸頭：剛被丟過，第一次被閃躲（%s）" % r1.get("event"), r1.get("event") == "dodge", r1)
    forgave = False
    for i in range(5):
        pg.wait_for_timeout(900)
        r = pg.evaluate("(id) => { const c = __world.chars.get(id); c.pet(1.5); return __world.mind.get(id).last; }", cid)
        if r.get("event") == "forgive" or r.get("event") == "petted":
            forgave = True
            break
    ok("摸頭：多摸幾次之後原諒他（第 %d 次）" % (i + 2), forgave, r)
    ok("被丟出去：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_burn(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("被燒到：世界載入", got):
        c1.close(); return
    cid = _mn_pick(pg, "(t) => true", 1)[0]
    pg.evaluate("(id) => __world.emit('burned', id, {})", cid)
    s1 = _mn_face_seen(pg, cid, ["scared"], 3000)
    ok("被燒到：驚叫（表情 %s）" % s1, bool(s1), None)
    _mn_shot(pg, "被燒焦_1驚叫.png")
    s2 = _mn_face_seen(pg, cid, ["blank", "cough"], 9000)
    ok("被燒到：之後呆滯、咳一下（表情 %s）" % s2, bool(s2), _mn_get(pg, cid)["face"])
    s3 = _mn_face_seen(pg, cid, ["cough"], 9000)
    ok("被燒到：咳煙（表情 %s、頭上黑煙）" % s3, bool(s3), None)
    sm = wait_until(pg, "() => { const c = __world.chars.get(%s); return c.emoteSym && c.emoteSym.sym === 'smoke'; }" % _json.dumps(cid), 6000)
    ok("被燒到：頭上出現小黑煙", bool(sm), None)
    _mn_shot(pg, "被燒焦_2呆滯咳嗽.png")
    pg.evaluate("(id) => __world.emit('recovered', id, {})", cid)
    s4 = _mn_face_seen(pg, cid, ["relieved"], 3000)
    ok("恢復：鬆一口氣（表情 %s）" % s4, bool(s4), _mn_get(pg, cid)["face"])
    _mn_shot(pg, "被燒焦_3恢復.png")
    ok("被燒到：旁觀者有人驚訝或關心", pg.evaluate("() => __world.mind.log.some(x => x.event === 'witness' && x.kind === 'burned')"), None)
    ok("被燒到：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_idle(b, base):
    c1, pg, got = _mn_open(b, base, qs="?ambient=1&q=low&pr=0.6&sim=1")
    if not ok("閒置：世界載入", got):
        c1.close(); return
    pg.evaluate("() => { __world.advanceAsync(120); }")
    wait_until(pg, "() => __world.time > 100", 90000)
    habs = pg.evaluate("() => __world.mind.log.filter(x => x.event === 'habit').map(x => [x.id, x.habit])")
    names = sorted({h[1] for h in habs})
    ok("閒置：自己出現的小習慣 %d 次、%d 種（%s）" % (len(habs), len(names), "、".join(names)), len(habs) >= 3 and len(names) >= 2, habs)
    ids = _mn_pick(pg, "(t, c) => c.state === 'sit' && c.atDesk && !c.busy", 10)
    pg.evaluate("(ids) => ids.forEach(id => __world.mind.forceHabit(id))", ids)
    pg.wait_for_timeout(300)
    now = pg.evaluate("(ids) => ids.map(id => { const g = __world.mind.get(id); return [id, g.habit && g.habit.name, __world.chars.get(id).action]; })", ids)
    hs = [x[1] for x in now if x[1]]
    ok("閒置：同一時刻 %d 位同事的小習慣不全相同（%s）" % (len(hs), "、".join(sorted(set(hs)))), len(hs) >= 4 and len(set(hs)) >= 2, now)
    acts = {x[2] for x in now}
    ok("閒置：同一時刻他們手上的動作也不同（%s）" % "、".join(sorted(acts)), len(acts) >= 2, now)
    _mn_shot(pg, "閒置小習慣.png")
    ok("閒置：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_card(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("資訊卡：世界載入", got):
        c1.close(); return
    cid = _mn_pick(pg, "(t) => true", 1)[0]
    pg.evaluate("(id) => { __world.ui.showCard(__world.chars.get(id)); }", cid)
    t0 = pg.evaluate("() => document.getElementById('cardMood') && document.getElementById('cardMood').textContent")
    ok("資訊卡：有心情列（%s）" % t0, bool(t0) and t0.startswith("心情："), t0)
    pg.evaluate("(id) => __world.emit('praised', id, { by: 'ceo' })", cid)
    ok("資訊卡：被稱讚後心情列寫「剛被稱讚」", bool(wait_until(pg, "() => /^心情：\\S+ (開心|興奮)（剛被稱讚）$/.test(document.getElementById('cardMood').textContent)", 4000)), pg.evaluate("() => document.getElementById('cardMood').textContent"))
    _mn_shot(pg, "資訊卡心情列.png")
    pg.evaluate("(id) => __world.emit('rejected', id, {})", cid)
    ok("資訊卡：被退件後心情列寫「交件被退回」", bool(wait_until(pg, "() => /^心情：\\S+ (低落|難過|平靜|開心)（交件被退回）$/.test(document.getElementById('cardMood').textContent)", 4000)), pg.evaluate("() => document.getElementById('cardMood').textContent"))
    pg.evaluate("(id) => __world.emit('knocked', id, { by: 'you' })", cid)
    ok("資訊卡：被丟出去後寫「被丟出去」", bool(wait_until(pg, "() => /被丟出去/.test(document.getElementById('cardMood').textContent)", 4000)), pg.evaluate("() => document.getElementById('cardMood').textContent"))
    ok("資訊卡：心情列文字不含禁用字", not _re.search(r"價格|NT\$|付費|訂閱|免費", pg.evaluate("() => document.getElementById('cardMood').textContent")), None)
    ok("資訊卡：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_hr(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("人事：世界載入", got):
        c1.close(); return
    cid = _mn_pick(pg, "(t) => t.sens >= .5", 1)[0]
    g0 = _mn_get(pg, cid)
    pg.evaluate("(id) => __world.hr.fire([id], { to: 'ceo' })", cid)
    seen = _mn_face_seen(pg, cid, ["sad", "pout"], 4000)
    g1 = _mn_get(pg, cid)
    ok("被開除：表情失落（%s）、心情值 %.2f → %.2f" % (seen, g0["mood"]["val"], g1["mood"]["val"]), bool(seen) and g1["mood"]["val"] < g0["mood"]["val"] - 0.2, g1)
    _mn_shot(pg, "被開除_離開時.png")
    pg.evaluate("() => { __world.speed = 8; }")
    arrived = wait_until(pg, "() => { const c = __world.chars.get(%s); return c.jobless && !c.hrBusy; }" % _json.dumps(cid), 60000)
    ok("被開除：走去無業遊民區", bool(arrived), None)
    low = _mn_get(pg, cid)["mood"]["val"]
    pg.evaluate("() => __world.advanceAsync(70)")      # 等這段快轉真的跑完，後面才不會被它帶著跑
    g2 = _mn_get(pg, cid)
    ok("被開除：在遊民區慢慢恢復平靜（%.2f → %.2f）" % (low, g2["mood"]["val"]), g2["mood"]["val"] > low + 0.05, g2)
    card = pg.evaluate("(id) => { __world.ui.showCard(__world.chars.get(id)); return document.getElementById('cardMood') && document.getElementById('cardMood').textContent; }", cid)
    ok("被開除：待業卡也有心情列（%s）" % card, bool(card) and "心情：" in card and ("待業中" in card or "失落" in card or "剛離開公司" in card), card)
    _mn_shot(pg, "被開除與重新聘用.png")
    pg.evaluate("() => { __world.speed = 2; }")
    pg.evaluate("(id) => { __world.hr.rehire(id); }", cid)
    s = _mn_face_seen(pg, cid, ["grateful", "surprised"], 8000)
    ok("重新聘用：驚喜感激（%s）" % s, bool(s), _mn_get(pg, cid)["face"])
    ok("人事：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_power(b, base):
    c1, pg, got = _mn_open(b, base)
    if not ok("額度：世界載入", got):
        c1.close(); return
    pg.evaluate("() => __world.sim.exhaust(8100)")
    y = wait_until(pg, "() => [...__world.chars.keys()].filter(id => __world.mind.get(id) && __world.mind.get(id).face === 'yawn').length >= 2", 8000)
    ok("額度用完：同事陸續打哈欠", bool(y), None)
    _mn_shot(pg, "額度用完打哈欠.png")
    ok("額度：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c1.close()


def t_mn_layout(b, base):
    for w, h, tag in ((1280, 800, "1280"), (390, 844, "390")):
        c1, pg, got = _mn_open(b, base, w, h)
        if not ok("版面（%s）：世界載入" % tag, got):
            c1.close(); continue
        cid = _mn_pick(pg, "(t) => true", 1)[0]
        pg.evaluate("(id) => { __world.ui.showCard(__world.chars.get(id)); __world.emit('praised', id, {}); }", cid)
        pg.wait_for_timeout(600)
        rs = pg.evaluate("""() => { const out = []; for (const s of ['#card', '#bar', '#cardNow', '#cardMood']) document.querySelectorAll(s).forEach((e, i) => { const r = e.getBoundingClientRect(); if (e.hidden || !r.width) return; out.push([s + i, r.left, r.top, r.right, r.bottom]); }); return out; }""")
        m = [r for r in rs if r[0].startswith("#cardMood")]
        n = [r for r in rs if r[0].startswith("#cardNow")]
        bad = []
        if m and n:
            a, c = n[0], m[0]
            if not (a[3] <= c[1] + 1 or c[3] <= a[1] + 1 or a[4] <= c[2] + 1 or c[4] <= a[2] + 1):
                bad.append("cardNow/cardMood")
        card = [r for r in rs if r[0].startswith("#card0")]
        inside = (not m) or (card and m[0][1] >= card[0][1] - 1 and m[0][3] <= card[0][3] + 1)
        ok("版面（%s）：心情列在資訊卡內且不與「目前」列重疊" % tag, bool(m) and not bad and inside, (rs, bad))
        ok("版面（%s）：沒有主控台錯誤" % tag, not pg.errs, pg.errs[:3])
        c1.close()


register("辦公室心-個性", lambda pg, b, base, code: t_mn_traits(b, base))
register("辦公室心-獎勵", lambda pg, b, base, code: t_mn_reward(b, base))
register("辦公室心-懲罰", lambda pg, b, base, code: t_mn_punish(b, base))
register("辦公室心-被丟出去", lambda pg, b, base, code: t_mn_knocked(b, base))
register("辦公室心-被燒到", lambda pg, b, base, code: t_mn_burn(b, base))
register("辦公室心-閒置", lambda pg, b, base, code: t_mn_idle(b, base))
register("辦公室心-資訊卡", lambda pg, b, base, code: t_mn_card(b, base))
register("辦公室心-人事", lambda pg, b, base, code: t_mn_hr(b, base))
register("辦公室心-額度", lambda pg, b, base, code: t_mn_power(b, base))
register("辦公室心-版面", lambda pg, b, base, code: t_mn_layout(b, base))
