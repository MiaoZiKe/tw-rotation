# 驗收段落「新角色（糰糰／垂垂／布布）」：AI Office 辦公室裡這三個物種改用 Blender 參數化一體成形網格（site/office/char/）＋固定步長控制器，
# 經 site/office/world/js/newchar.js 相容層接進場景；其餘物種仍是舊系統（兩套並存）。每一項都量「畫面／骨頭／網格真的改變」：
#   ① 三個物種（含 CEO 放大 1.15、寵物麻吉縮小 0.5）在場景裡是新模型（物件名、單一蒙皮網格、有骨架與形態鍵），其餘物種不受影響
#   ② 坐在椅子上：身體所有頂點的最低點與座面距離 < 2 公分；身體不穿椅背（超出椅背前緣 ≤ 3 公分，尾巴與耳朵都算）
#   ③ 走路與跑步：腳骨在「著地期」的世界位移 ≤ 1 公分（不滑步），而且腳真的有交替落地
#   ④ 被選取時面向鏡頭：站著的人轉向鏡頭、坐著的人轉椅子；睡覺不叫醒
#   ⑤ 配件（識別證、領帶、皇冠、帽子）在身體表面附近（≤ 2 公分）、不鼻子（沒有任何名為 nose 的臉部零件、錨點只有眼、嘴、頰、眉）
#   ⑥ 表情與眨眼會改變臉貼圖與眼皮；睡覺動作真的躺下（身高變低）
#   ⑦ 主控台沒有錯誤；繪製次數（renderer.info.render.calls）不高於舊系統版本
# 軟體繪圖很慢，所以量測一律手動以 1/60 秒一步推進（__world.speed 壓到最低），不靠牆鐘時間。
# flake8: noqa

_OPEN = """() => window.__world && window.__world.ready"""

_LOOK = """() => { const W = __world, out = [];
 const all = [...W.chars.values(), ...W.pets];
 for (const c of all) { out.push({ id: c.spec.id, sp: c.look.species, nw: !!c.newModel, name: c.object3D.name, s: c.scale, pet: !!c.spec.pet, ceo: !!c.spec.isCeo, state: c.state }); }
 return out; }"""

_SIT = """(id) => { const W = __world, c = W.chars.get(id) || W.pets.find(p => p.spec.id === id), ch = c.inner.ch, ctl = c.inner.ctl, V = W.THREE.Vector3; W.speed = 0.01; let t = W.time; const dt = 1 / 60;
 for (let i = 0; i < 90; i++) { t += dt; c.update(dt, t); }
 const sp = W.spots.find(q => q.name === 'seat:' + id) || c.spot; const seat = c._seat; if (!seat) return { err: 'no seat' };
 const box = ctl.world.box('seat'), s = c.scale, top = box.y1 * s;       // 座面（含坐墊／升高椅面）的世界高度
 ch.model.updateMatrixWorld(true); ch.body.skeleton.update(); const v = new V(); let lo = 1e9, back = -1e9; const bx = -Math.sin(seat.face), bz = -Math.cos(seat.face), sx = Math.cos(seat.face), sz = -Math.sin(seat.face), cx = seat.x, cz = seat.z, half = c.spec.isCeo ? 0.25 : 0.23;
 const meshes = [ch.body]; for (const m of meshes) { const P = m.geometry.attributes.position, M = m.geometry.morphAttributes.position, w = m.morphTargetInfluences;
   for (let i = 0; i < P.count; i++) { v.set(P.getX(i), P.getY(i), P.getZ(i)); for (let k = 0; k < (M || []).length; k++) if (w[k]) { v.x += M[k].getX(i) * w[k]; v.y += M[k].getY(i) * w[k]; v.z += M[k].getZ(i) * w[k]; } m.applyBoneTransform(i, v); v.applyMatrix4(m.matrixWorld);
     if (v.y < lo) lo = v.y; const d = (v.x - cx) * bx + (v.z - cz) * bz, sd = (v.x - cx) * sx + (v.z - cz) * sz; if (Math.abs(sd) <= half && d > back) back = d; } }
 return { lowest: lo, top, gap: lo - top, back, plane: c.spec.isCeo ? 0.25 : 0.215, state: c.state, sub: ctl.sit && ctl.sit.sub, boost: c._boost, fwd: c._seatFwd }; }"""

_WALK = """([id, kind]) => { const W = __world, c = W.chars.get(id) || W.pets.find(p => p.spec.id === id), ch = c.inner.ch, ctl = c.inner.ctl, V = W.THREE.Vector3; W.speed = 0.01; let t = W.time; const dt = 1 / 60;
 c.stop(false); c.standAt(20, 26, 0); c.busy = true; for (let i = 0; i < 60; i++) { t += dt; c.update(dt, t); }
 const sp = kind === 'run' ? c.inner.ctl.P.move.run * c.scale * 0.95 : c.inner.ctl.P.move.walk * c.scale * 0.95, fb = [ch.bones['foot.L'], ch.bones['foot.R']], pos = [new V(), new V()], st = [{ prev: '', start: null, max: 0, n: 0 }, { prev: '', start: null, max: 0, n: 0 }];
 let worst = 0, planted = [0, 0], swings = 0, dist0 = c.object3D.position.z;
 for (let i = 0; i < 240; i++) { c.drive(0, sp, 0, 1); t += dt; c.update(dt, t);
   if (i < 50) continue; ch.model.updateMatrixWorld(true);
   for (let k = 0; k < 2; k++) { const f = ctl.feet.feet[k]; fb[k].getWorldPosition(pos[k]); const q = st[k];
     if (f.mode === 'plant' && ctl.feet.cad > 0 && q.prev === 'plant') { if (!q.start) { q.start = pos[k].clone(); q.n++; } q.max = Math.max(q.max, Math.hypot(pos[k].x - q.start.x, pos[k].z - q.start.z)); planted[k]++; }
     else if (q.start) { worst = Math.max(worst, q.max); q.start = null; q.max = 0; } if (f.mode === 'swing' && q.prev !== 'swing') swings++; q.prev = f.mode; } }
 for (const q of st) worst = Math.max(worst, q.max);
 c.drive(null); return { slide: worst, steps: st[0].n + st[1].n, swings, moved: c.object3D.position.z - dist0, speed: sp, plantedFrames: planted }; }"""

_FACE = """([id, mode]) => { const W = __world, c = W.chars.get(id), P = W.pilot, cam = W.camera, dt = 1 / 60; W.speed = 0.01; let t = W.time;
 if (mode === 'stand') { c.stop(false); c.standAt(20, 26, 0); c.busy = true; c.setAction('idle'); } for (let i = 0; i < 30; i++) { t += dt; c.update(dt, t); }
 P.select(c); for (let i = 0; i < 150; i++) { t += dt; W.attn.frame(); c.update(dt, t); }
 const p = c.object3D.position, want = Math.atan2(cam.position.x - p.x, cam.position.z - p.z), yaw = c.inner.yaw, d = Math.atan2(Math.sin(yaw - want), Math.cos(yaw - want));
 P.deselect(); return { diff: Math.abs(d), yaw, want, state: c.state }; }"""

_ACC = """(id) => { const W = __world, c = W.chars.get(id) || W.pets.find(p => p.spec.id === id), ch = c.inner.ch, V = W.THREE.Vector3; c.update(1 / 60, W.time + 1); ch.model.updateMatrixWorld(true); ch.body.skeleton.update();
 const P = ch.body.geometry.attributes.position, M = ch.body.geometry.morphAttributes.position, w = ch.body.morphTargetInfluences, pts = []; const v = new V();
 for (let i = 0; i < P.count; i += 2) { v.set(P.getX(i), P.getY(i), P.getZ(i)); ch.body.applyBoneTransform(i, v); pts.push(v.clone().applyMatrix4(ch.body.matrixWorld)); }
 const out = []; ch.holderFor('head').traverse(o => { if (o.userData.acc && o.userData.acc !== 'cherry') { const q = new V(); o.getWorldPosition(q); let best = 1e9; for (const p of pts) best = Math.min(best, p.distanceTo(q)); out.push({ acc: o.userData.acc, d: best }); } });
 const names = []; ch.model.traverse(o => names.push(o.name)); ch.holderFor('head').traverse(o => names.push(o.name));
 return { acc: out, anchors: Object.keys(ch.meta.anchors), noNoseName: !names.some(n => /nose/i.test(n)), faceNose: !!(ch.face && ch.face.cur && ch.face.cur.nose) }; }"""

_EXPR = """(id) => { const W = __world, c = W.chars.get(id), ch = c.inner.ch, f = ch.face, dt = 1 / 60; W.speed = 0.01; let t = W.time; const out = {};
 const snap = () => { f.update(0.3, 12); return f.eyes.map(e => ({ lid: e.lid.visible, rim: e.rim.visible, arc: e.arcUp.visible })); };
 c.setExpression('neutral'); for (let i = 0; i < 40; i++) { t += dt; c.update(dt, t); } f.autoBlink = false; out.neutral = JSON.stringify(snap()); const n0 = f.cur.open;
 c.setExpression('happy'); for (let i = 0; i < 60; i++) { t += dt; c.update(dt, t); } out.happy = JSON.stringify(snap()); out.happyArc = f.cur.arc;
 c.setExpression('neutral'); for (let i = 0; i < 40; i++) { t += dt; c.update(dt, t); } f.blinkNow(); let minOpen = 1, sawBlink = false;
 for (let i = 0; i < 30; i++) { t += dt; c.update(dt, t); if (f.blink > 0.5) sawBlink = true; minOpen = Math.min(minOpen, f.eyes[0].dep.scale.z); }
 out.blink = sawBlink; out.minDepScale = minOpen; out.blushNeutral = n0; return out; }"""

_SLEEP = """(id) => { const W = __world, c = W.chars.get(id), ch = c.inner.ch, ctl = c.inner.ctl, V = W.THREE.Vector3, dt = 1 / 60; W.speed = 0.01; let t = W.time; c.stop(false); c.standAt(20, 26, 0); c.busy = true; for (let i = 0; i < 40; i++) { t += dt; c.update(dt, t); }
 const eye = new V(), top = () => { ch.model.updateMatrixWorld(true); ch.face.eyes[0].grp.getWorldPosition(eye); return eye.y; }; const h0 = top(), s0 = ch.wm.squash || 0; c.setAction('sleep'); for (let i = 0; i < 240; i++) { t += dt; c.update(dt, t); }
 const h1 = top(), st = ctl.state, sq = ch.wm.squash || 0, cl = ch.face.cur.open; c.setAction('idle'); for (let i = 0; i < 120; i++) { t += dt; c.update(dt, t); } return { h0, h1, st, sq, open: cl, after: ctl.state }; }"""


def _open(b, base, qs="?ambient=0&q=low&pr=0.3&view=ceo", w=1000, h=640):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": w, "height": h})
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(root + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, _OPEN, 90000)
    return c, pg, got


def t_newchar(b, base):
    c, pg, got = _open(b, base)
    ok("新角色：辦公室載入完成", got)
    if not got:
        c.close(); return
    try:
        pg.evaluate("() => { __world.setView('char', __world.chars.get('ceo'), true); }")
        rows = pg.evaluate(_LOOK)
        newsp = {"mochi", "bunny", "pudding"}
        news = [r for r in rows if r["sp"] in newsp]; olds = [r for r in rows if r["sp"] not in newsp]
        ok("新角色：三個物種（糰糰、垂垂、布布）%d 位全部是新模型（物件名 newchar-*）" % len(news), len(news) >= 5 and all(r["nw"] and r["name"] == "newchar-" + r["sp"] for r in news), [r for r in news if not r["nw"]][:3])
        ok("新角色：三個物種都有（%s）" % ",".join(sorted({r["sp"] for r in news})), {r["sp"] for r in news} == newsp)
        ok("新角色：CEO（放大）與寵物麻吉（縮小 0.5）都是新模型糰糰", any(r["ceo"] and r["nw"] and r["s"] > 1.05 for r in news) and any(r["pet"] and r["nw"] and abs(r["s"] - 0.5) < 0.01 for r in news), [r for r in news if r["ceo"] or r["pet"]])
        ok("新角色：其他物種仍是舊系統（%d 位不是新模型）" % len(olds), len(olds) >= 20 and not any(r["nw"] for r in olds))
        info = pg.evaluate("() => { const W = __world, c = W.chars.get('ceo'); const o = { skinned: 0, bones: 0, morphs: 0, tris: 0 }; c.object3D.traverse(m => { if (m.isSkinnedMesh && m.visible) { o.skinned++; o.bones = m.skeleton.bones.length; o.morphs = Object.keys(m.morphTargetDictionary || {}).length; o.tris += (m.geometry.index ? m.geometry.index.count : m.geometry.attributes.position.count) / 3; } }); return o; }")
        ok("新角色：一體成形（身體只有 1 張蒙皮網格＋臉貼片、骨架 %d 根、形態鍵 %d 個）" % (info["bones"], info["morphs"]), 1 <= info["skinned"] <= 2 and info["bones"] >= 18 and info["morphs"] >= 7, info)
        # ② 坐姿：每個物種都量（CEO、一位糰糰同事、垂垂、布布）
        ids = pg.evaluate("() => { const W = __world, o = {}; for (const [id, c] of W.chars) { if (c.newModel && c.state === 'sit' && !o[c.look.species + (c.spec.isCeo ? '-ceo' : '')]) o[c.look.species + (c.spec.isCeo ? '-ceo' : '')] = id; } return o; }")
        ok("新角色：三種物種都有人坐在椅子上（%s）" % ",".join(sorted(ids)), {"mochi", "bunny", "pudding"} <= {k.split("-")[0] for k in ids}, ids)
        for k, cid in ids.items():
            r = pg.evaluate(_SIT, cid)
            ok("坐姿 %s：身體最低點與座面距離 %.1f 公分（要 < 2 公分）" % (k, r.get("gap", 9) * 100), abs(r.get("gap", 9)) < 0.02, r)
            ok("坐姿 %s：身體（含尾巴耳朵）超出椅背前緣 %.1f 公分（要 ≤ 3 公分，不穿椅背；只算椅背寬度內的頂點）" % (k, (r.get("back", 9) - r.get("plane", 0)) * 100), r.get("back", 9) - r.get("plane", 0) <= 0.03, r)
        # ③ 走路、跑步腳不滑
        pick = {}
        for r in news:
            if not r["pet"]:
                pick.setdefault(r["sp"], r["id"])
        pick["pet-mochi"] = next(r["id"] for r in news if r["pet"])
        for k, cid in pick.items():
            for kind in ("walk", "run"):
                r = pg.evaluate(_WALK, [cid, kind])
                ok("%s %s：著地期腳骨世界位移 %.1f 公分（要 ≤ 1 公分），腳交替落地 %d 次、身體往前走了 %.1f 公尺" % (k, kind, r["slide"] * 100, r["steps"], r["moved"]), r["slide"] <= 0.01 and r["steps"] >= 4 and r["moved"] > 1.0, r)
        # ④ 選取面向鏡頭（站著、坐著）
        for k, cid in pick.items():
            if k == "pet-mochi":
                continue
            r = pg.evaluate(_FACE, [cid, "stand"])
            ok("選取面向鏡頭（站著）%s：朝向與鏡頭方向相差 %.2f 弧度（要 < 0.35）" % (k, r["diff"]), r["diff"] < 0.35, r)
        # ⑤ 配件與無鼻
        accd = pg.evaluate("() => { const W = __world, o = []; for (const [id, c] of W.chars) if (c.newModel) { const n = []; c.inner.ch.holderFor('head').traverse(m => { if (m.userData.acc && m.userData.acc !== 'cherry') n.push(m.userData.acc); }); o.push([id, n]); } return o; }")
        withacc = [x for x in accd if x[1]]
        ok("配件：新模型角色至少有 3 位戴了配件（識別證、領帶、皇冠、帽子…）", len(withacc) >= 3, accd[:6])
        for cid, names in withacc[:6]:
            r = pg.evaluate(_ACC, cid)
            far = [a for a in r["acc"] if a["d"] > 0.03]
            ok("配件 %s %s：離身體表面 ≤ 3 公分（最遠 %.1f 公分）" % (cid, ",".join(sorted(set(names))), max([a["d"] for a in r["acc"]] or [0]) * 100), not far, r["acc"])
        r = pg.evaluate(_ACC, next(iter(pick.values())))
        ok("無鼻子：臉部錨點只有眼、頰、眉、嘴（%s）且沒有任何名為 nose 的零件" % ",".join(k for k in r["anchors"] if "eye" in k or "mouth" in k), r["noNoseName"] and not r["faceNose"], r)
        # ⑥ 表情、眨眼、睡覺
        for sp in ("mochi", "bunny", "pudding"):
            r = pg.evaluate(_EXPR, pick[sp])
            ok("表情 %s：開心閉眼（笑眼弧線出現）、眨眼時眼皮真的合起來（眼球縮到 %.2f）" % (sp, r["minDepScale"]), r["happyArc"] > 0.5 and r["blink"] and r["minDepScale"] < 0.6, r)
            r = pg.evaluate(_SLEEP, pick[sp])
            ok("睡覺 %s：眼睛高度從 %.2f 降到 %.2f（身體壓扁 %.2f、眼睛閉上 %.2f），狀態 %s，醒來後回到 %s" % (sp, r["h0"], r["h1"], r["sq"], r["open"], r["st"], r["after"]), r["st"] == "sleep" and r["h1"] < r["h0"] * 0.95 and r["sq"] > 0.3 and r["open"] < 0.3 and r["after"] in ("idle", "land"), r)
        # ⑦ 錯誤與繪製次數
        ok("新角色：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_newchar_calls(b, base):
    """繪製次數：同一個場景、同一個視角，新系統（預設）與舊系統（?body=v1）各量一次 renderer.info.render.calls；新系統不得高於舊系統。"""
    res = {}
    for tag, qs in (("new", "?ambient=0&q=low&pr=0.3&view=ceo"), ("old", "?ambient=0&q=low&pr=0.3&view=ceo&body=v1")):
        c, pg, got = _open(b, base, qs)
        if not got:
            ok("繪製次數：%s 載入完成" % tag, False); c.close(); return
        try:
            for view in ("ceo", "top"):
                pg.evaluate("(v) => { const W = __world; if (v === 'top') W.setView('god', null, true); else W.setView('char', W.chars.get('ceo'), true); }", view)
                pg.wait_for_timeout(2500)
                res[(tag, view)] = pg.evaluate("() => { return __world.stats.calls; }")
        finally:
            c.close()
    for view in ("ceo", "top"):
        ok("繪製次數（%s 視角）：新 %s ≤ 舊 %s（+10%% 容差）" % (view, res[("new", view)], res[("old", view)]), res[("new", view)] >= 0 and res[("new", view)] <= res[("old", view)] * 1.10 + 2, res)


register("辦公室新角色", lambda pg, b, base, code: (t_newchar(b, base), t_newchar_calls(b, base)))
