# 驗收段落「辦公室外觀修正」：AI Office 角色外觀稽核（docs/ai_office/character_audit_1113.md）A 類第一批的量化驗收。
#   A1 背面不出現臉（貼貼、夾夾、算算）；正面的臉還在     A2 彎彎沒有懸空的手
#   A3 滾滾沒有鼻子、啃啃沒有鼻吻鼓包與鼻孔點            A4 貼貼、夾夾、啵啵的手腳根部不比身體厚（不穿出白色碎片）
#   A5 手離身體中心 ≤ 2.2 倍身體半徑（站／走／跑／轉身／瞬間反向／跳；被拎起不算，另有 20261113_office_limbs 管）
#   A7 坐墊 ≤ 0.12 公尺、不夠的改升椅子座面、嘴巴高度不變；背後太長的往前坐；CEO 縮到 1.08 倍
#   第二批（段落「辦公室外觀修正2」）：A8 配件（識別證與領帶不貼地、不在身體以外、不同位置；最多一件頭飾；圍巾變細）
#   A9 拿鐵（液面不凸出杯口、前傾 ≤ 10 度、手不穿把手）、啃啃尾巴根部、八寶觸手不低於地面、小燭左舌不遮臉、閃閃腳同身體色；A10 啾啾翅膀貼身
#   外加硬性規則：25 種都沒有鼻子（face.js 不畫鼻點與鼻孔）
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。全部在真的 3D 場景裡量，驗「畫面／數值真的因此改變」。
# flake8: noqa

_FACE_JS = """async () => {
  const W = window.__world, T = W.THREE, mod = await import('/office/play/office_character.js'), out = {};
  const st = new T.Scene(); st.background = new T.Color('#efe6dc'); st.add(new T.HemisphereLight('#fffaf3', '#f3d5b4', 1.6)); const sun = new T.DirectionalLight('#fff3e0', 1.5); sun.position.set(6, 20, 14); sun.target.position.set(20, 0, 15); st.add(sun, sun.target);
  const cam = new T.PerspectiveCamera(28, 1, 0.05, 100), rt = new T.WebGLRenderTarget(192, 192), buf = new Uint8Array(192 * 192 * 4), buf2 = new Uint8Array(192 * 192 * 4);
  const env = { camera: cam, fx: W.fx, followed: null, bounds: { x0: 0.6, x1: 39.4, z0: 0.6, z1: 40 } };
  const shot = (c, az, dst) => { const p = c.object3D.position, h = c.height * 0.5, d = 3.4, yaw = c.object3D.rotation.y + az; cam.position.set(p.x + Math.sin(yaw) * d, h + 0.5, p.z + Math.cos(yaw) * d); cam.lookAt(p.x, h, p.z); cam.updateMatrixWorld();
    const old = W.renderer.getRenderTarget(); W.renderer.setRenderTarget(rt); W.renderer.render(st, cam); W.renderer.readRenderTargetPixels(rt, 0, 0, 192, 192, dst); W.renderer.setRenderTarget(old); };
  const diff = (a, b) => { let n = 0; for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 24) n++; return n; };
  let t = 900;
  for (const sp of ['note', 'folder', 'calc', 'mochi']) {
    const c = mod.createCharacter({ id: 'fz_' + sp, nick: sp, species: sp, pal: 0, acc: [] }, env); st.add(c.object3D); c.standAt(20, 15, 0);
    for (let i = 0; i < 40; i++) { t += 1 / 60; c.update(1 / 60, t); }
    const Z = c.inner.main.material.userData.U.uFaceZ, z0 = Z.value, r = {};
    for (const [name, az] of [['back', Math.PI], ['front', 0]]) { Z.value = z0; shot(c, az, buf); Z.value = 1e4; shot(c, az, buf2); r[name] = diff(buf, buf2); }
    Z.value = z0; out[sp] = r; c.dispose();
  }
  return out; }"""

_LIMB_JS = """async (only) => {
  const W = window.__world, out = {}; let t = 1200; const dt = 1 / 60;
  const ids = [...W.chars.keys()], seen = new Set(), pick = ['ceo'];
  for (const i of ids) { const sp = W.chars.get(i).spec.species; if (!seen.has(sp)) { seen.add(sp); pick.push(i); } }
  for (const p of W.pets) pick.push(p.spec.id);
  for (const id of [...new Set(pick)]) {
    const c = W.chars.get(id) || W.pets.find(p => p.spec.id === id), ch = c.inner; if (!ch.hands.length) continue;
    W.setView('char', c, true);
    const R = ch.cfg.R, meas = () => { let m = 0; ch.hands.forEach(h => { m = Math.max(m, Math.hypot(h.p.x - ch.pos.x, h.p.y - (ch.pos.y + R), h.p.z - ch.pos.z)); }); return m / R; };
    const res = {}, run = (name, n, fn) => { let mx = 0; for (let i = 0; i < n; i++) { fn(i); t += dt; c.update(dt, t); if (i > 5) mx = Math.max(mx, meas()); } res[name] = +mx.toFixed(2); };
    c.stop(false); c.standAt(20, 26, 0); c.busy = true; for (let i = 0; i < 20; i++) { t += dt; c.update(dt, t); }
    run('站', 140, () => c.drive(0, 0), 90); run('走', 90, () => c.drive(0, 1.5, 0, 1)); run('跑', 90, () => c.drive(0, 3.4, 0, 1));
    run('轉身', 90, i => { const an = i * 0.2; c.drive(Math.sin(an) * 3.4, Math.cos(an) * 3.4, Math.sin(an), Math.cos(an)); });
    run('瞬間反向', 90, i => { const d = (Math.floor(i / 10) % 2) ? 1 : -1; c.drive(d * 3.4, 0, d, 0); });
    run('跳', 70, i => { if (i === 0) { ch.extFall = true; ch.vel.y = 4.6; ch.pos.y = 0.001; ch.feet.forEach(f => f.planted = false); } c.drive(0, 2, 0, 1); });
    c.drive(null); for (let i = 0; i < 40; i++) { t += dt; c.update(dt, t); }
    out[id + '(' + c.spec.species + (c.scale !== 1 ? '×' + c.scale : '') + ')'] = res;
  }
  return out; }"""

_SEAT_JS = """() => {
  const W = window.__world, out = []; let t = 2000;
  for (const [id, c] of W.chars) {
    const sp = W.spots.find(q => q.name === 'seat:' + id); if (!sp) continue; c.stop(false); c.sitAt(sp.seat, { instant: true }); c.setAction('type');
    for (let i = 0; i < 30; i++) { t += 1 / 60; c.update(1 / 60, t); }
    const f = [Math.sin(sp.seat.face), Math.cos(sp.seat.face)], q = c.object3D.position, boost = c._boost || 0, lift = c._lift || 0;
    out.push({ id, species: c.spec.species, soft: +(boost - lift).toFixed(3), lift: +lift.toFixed(3), boost: +boost.toFixed(3), fwd: +((q.x - sp.seat.x) * f[0] + (q.z - sp.seat.z) * f[1]).toFixed(3), backExt: +((c._backExt || 0)).toFixed(3), lift_y: +(c.lift || 0).toFixed(3), ceo: !!c.spec.isCeo, scale: c.scale, mouthY: +(c.eye(new W.THREE.Vector3()).y).toFixed(3) });
  }
  return out; }"""


def t_auditfix(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 800, "height": 500})
    pg = c.new_page(); pg.set_default_timeout(180000); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.3&view=ceo", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    ok("外觀修正：載入完成", got)
    if not got:
        c.close(); return
    try:
        # ── A1 背面不出現臉
        fr = pg.evaluate(_FACE_JS)
        for sp in ("note", "folder", "calc"):
            ok("A1 背面沒有臉：%s 背面有／無臉貼圖的畫面相差 %d 個像素（要 0）" % (sp, fr[sp]["back"]), fr[sp]["back"] == 0, fr[sp])
            ok("A1 正面的臉還在：%s 正面有／無臉貼圖的畫面相差 %d 個像素（要 > 150）" % (sp, fr[sp]["front"]), fr[sp]["front"] > 150, fr[sp])
        ok("A1 其他物種沒被連帶改到：糰糰正面臉還在（%d 像素）" % fr["mochi"]["front"], fr["mochi"]["front"] > 150, fr["mochi"])
        # ── A2 A3 A4 設定值
        cfg = pg.evaluate("""async () => { const S = (await import('/office/play/species.js')).SPECIES, W = window.__world, ch = (id) => W.chars.get(id).inner;
          const thick = (id) => ({ 'frontend-ui': 0.055, 'legal-compliance': 0.07 })[id];   // 身體半厚（rbox 的厚度 0.11、0.14 的一半；便利貼翹起的角不算）
          const slot = (id) => (ch(id).slots || []).map(s => ({ k: s.kind, rf: s.rf, hr: s.hr || 0, foot: !!s.f }));
          return { lamp: W.chars.get('visual-explainer').inner.hands.length, lampSkin: slot('visual-explainer').length, seal: !!S.seal.face.nose, dino: !!S.dino.face.nostril,
            note: { half: thick('frontend-ui'), slots: slot('frontend-ui') }, folder: { half: thick('legal-compliance'), slots: slot('legal-compliance') }, robo: slot('semi-chain-analyst') }; }""")
        ok("A2 彎彎沒有手（手球 %d 個、手臂皮膚 %d 條）" % (cfg["lamp"], cfg["lampSkin"]), cfg["lamp"] == 0 and cfg["lampSkin"] == 0, cfg)
        ok("A3 滾滾沒有畫鼻子、啃啃沒有畫鼻孔", (not cfg["seal"]) and (not cfg["dino"]), cfg)
        for key in ("note", "folder"):
            half = cfg[key]["half"]; worst = max(s["rf"] for s in cfg[key]["slots"])
            ok("A4 %s 手腳根部半徑最大 %.3f ≤ 身體半厚 %.3f（不從正面穿出來）" % (key, worst, half), worst <= half + 1e-3, cfg[key])
        wr = max(s["rf"] / s["hr"] for s in cfg["robo"] if not s["foot"])
        ok("A4 啵啵手臂根部半徑不超過手球的 1.05 倍（實測 %.2f 倍）" % wr, wr <= 1.05, cfg["robo"])
        # ── A5 手的偏離
        lr = pg.evaluate(_LIMB_JS)
        worst = (0, None)
        for k, v in lr.items():
            m = max(v.values())
            if m > worst[0]:
                worst = (m, k, v)
        bad = [(k, v) for k, v in lr.items() if max(v.values()) > 2.2]
        ok("A5 手離身體中心 ≤ 2.2 倍身體半徑：%d 個角色（含 CEO、寵物）站／走／跑／轉身／瞬間反向／跳，最大 %.2f（%s）" % (len(lr), worst[0], worst[1]), not bad and len(lr) >= 16, bad[:2])
        run_ = [max(v["跑"], v["轉身"], v["瞬間反向"]) for v in lr.values()]
        ok("A5 跑步與轉彎時手被甩在後面的程度：平均 %.2f 倍（修正前約 2.1 倍頂到上限）" % (sum(run_) / len(run_)), sum(run_) / len(run_) < 1.95, run_[:5])
        # ── A7 坐姿
        sr = pg.evaluate(_SEAT_JS)
        ok("A7 辦公室成員逐一坐到自己的椅子：%d 位" % len(sr), len(sr) >= 40, len(sr))
        over = [r for r in sr if r["soft"] > 0.12 + 1e-6]
        ok("A7 軟坐墊最厚 %.3f 公尺 ≤ 0.12（修正前最厚 0.27）" % max(r["soft"] for r in sr), not over, over[:2])
        lifted = [r for r in sr if r["boost"] > 0.12 + 1e-6]
        ok("A7 墊高超過 0.12 的 %d 位改升椅子座面（一個座面盤＋一根桿，不再疊軟坐墊）" % len(lifted), lifted and all(abs(r["lift"] - r["boost"]) < 2e-3 and r["soft"] < 1e-3 for r in lifted), lifted[:2])
        pads = pg.evaluate("""() => { const W = window.__world; const o = []; for (const [id, c] of W.chars) { if (!(c._lift > 0)) continue; let discs = 0, poles = 0; c.object3D.traverse(m => { if (m.userData && m.userData.prop === 'cushion') { if (m.isGroup) { poles += m.children.length - 1; discs += 1; } else discs += 1; } }); o.push({ id, discs, poles }); } return o; }""")
        ok("A7 升高椅子的每位只有一個座面盤加一根桿（共 %d 位）" % len(pads), pads and all(p_["discs"] == 1 and p_["poles"] == 1 for p_ in pads), pads[:2])
        low = [r for r in sr if r["mouthY"] < 0.9 and r["boost"] > 0]
        ok("A7 坐上去的總高度沒變：被墊高的 %d 位嘴巴高度都 ≥ 0.9 公尺（高過桌面 0.74）" % len([r for r in sr if r["boost"] > 0]), not low, low[:2])
        tail = [r for r in sr if r["backExt"] > 0.3]
        slack = [r for r in tail if r["fwd"] < min(0.1, r["backExt"] - (0.25 if r["ceo"] else 0.2)) - 0.012]
        ok("A7 背後超出椅背的 %d 位都往前坐了 min(0.1, 超出量) 公尺（最小 %.3f）" % (len(tail), min([r["fwd"] for r in tail] or [0])), tail and not slack, slack[:2])
        thin = [r for r in sr if r["backExt"] <= 0.2 and r["fwd"] > 0.001]
        ok("A7 沒有超出椅背的（貼貼、算算、啵啵等）不亂往前坐", not thin, thin[:2])
        ceo = [r for r in sr if r["ceo"]][0]
        ok("A7 CEO 縮到 1.08 倍（實測 %.2f）" % ceo["scale"], abs(ceo["scale"] - 1.08) < 1e-6, ceo)
        ok("外觀修正：沒有主控台錯誤", not errs, errs[:3])
    finally:
        c.close()


register("辦公室外觀修正", lambda pg, b, base, code: t_auditfix(b, base))


_ACC_JS = """async () => {
  const W = window.__world, T = W.THREE, mod = await import('/office/play/office_character.js'), SP = (await import('/office/play/species.js')), out = [];
  const st = new T.Scene(); st.add(new T.HemisphereLight('#fff', '#ccc', 1));
  const cam = new T.PerspectiveCamera(28, 1, 0.05, 100), env = { camera: cam, fx: W.fx, followed: null, bounds: { x0: 0.6, x1: 39.4, z0: 0.6, z1: 40 } };
  let t = 3000;
  for (const sp of Object.keys(SP.SPECIES)) {
    const c = mod.createCharacter({ id: 'ac_' + sp, nick: sp, species: sp, pal: 0, acc: ['badge', 'tie', 'scarf', 'hat', 'bow', 'crown'], accColor: '#f0a070' }, env); st.add(c.object3D); c.standAt(20, 15, 0);
    for (let i = 0; i < 40; i++) { t += 1 / 60; c.update(1 / 60, t); }
    const ch = c.inner, body = new T.Box3().setFromObject(ch.main), ap = ch.apps.filter(a => a.acc), my = ch.cfg.mouth ? ch.cfg.mouth[1] : 0.4;
    const box = (k) => ap.filter(a => a.acc === k).map(a => new T.Box3().setFromObject(a.piv));
    const wp = (a) => a.piv.getWorldPosition(new T.Vector3());
    const heads = ap.filter(a => a.acc === 'hat' || a.acc === 'bow' || a.acc === 'crown').length;
    const row = { sp, heads, kinds: [...new Set(ap.map(a => a.acc))], min_y: 9, over_z: -9, dup: false, tieY: null, badgeY: null, mouthY: my, scarfTk: null };
    for (const k of ['tie', 'badge']) for (const b of box(k)) { row.min_y = Math.min(row.min_y, b.min.y - c.object3D.position.y); row.over_z = Math.max(row.over_z, b.max.z - body.max.z); }
    const tie = ap.find(a => a.acc === 'tie'), bd = ap.find(a => a.acc === 'badge');
    if (tie) row.tieY = tie.piv.position.y; if (bd) row.badgeY = bd.piv.position.y;
    if (tie && bd) row.dup = Math.abs(tie.piv.position.x - bd.piv.position.x) < 0.1;
    const sc = ap.find(a => a.acc === 'scarf'); if (sc) { const b = new T.Box3().setFromObject(sc.piv); row.scarf = true; }
    out.push(row); c.dispose();
  }
  return out; }"""

_BIRD_JS = """async () => {
  const W = window.__world, T = W.THREE, mod = await import('/office/play/office_character.js');
  const st = new T.Scene(), cam = new T.PerspectiveCamera(28, 1, 0.05, 100), env = { camera: cam, fx: W.fx, followed: null, bounds: { x0: 0.6, x1: 39.4, z0: 0.6, z1: 40 } };
  const c = mod.createCharacter({ id: 'bw', nick: 'bw', species: 'bird', pal: 0, acc: [] }, env); st.add(c.object3D); c.standAt(20, 15, 0); const ch = c.inner; let t = 3500; const dt = 1 / 60, R = ch.cfg.R, res = { hands: ch.hands.length, wings: ch.apps.filter(a => a.fn).length };
  const meas = () => { let m = 0; const ctr = new T.Vector3(ch.pos.x, ch.pos.y + R, ch.pos.z), v = new T.Vector3(); for (const a of ch.apps) if (a.fn) { a.piv.updateWorldMatrix(true, true); a.piv.traverse(o => { if (!o.isMesh) return; const P = o.geometry.attributes.position; for (let k = 0; k < P.count; k++) { v.fromBufferAttribute(P, k).applyMatrix4(o.matrixWorld); m = Math.max(m, v.distanceTo(ctr)); } }); } return m / R; };
  const run = (name, n, fn, skip = 8) => { let mx = 0, lo = 9, ang = []; for (let i = 0; i < n; i++) { fn(i); t += dt; c.update(dt, t); if (i > skip) { mx = Math.max(mx, meas()); const a = ch.apps.find(q => q.fn && q.side > 0); ang.push(a.piv.rotation.z); } } res[name] = +mx.toFixed(2); res[name + '擺幅'] = +(Math.max(...ang) - Math.min(...ang)).toFixed(3); };
  c.busy = true; run('站', 40, () => c.drive(0, 0)); run('走', 90, () => c.drive(0, 1.5, 0, 1)); run('跑', 90, () => c.drive(0, 3.4, 0, 1));
  run('轉身', 90, i => { const an = i * 0.2; c.drive(Math.sin(an) * 3.4, Math.cos(an) * 3.4, Math.sin(an), Math.cos(an)); });
  c.drive(null); for (let i = 0; i < 40; i++) { t += dt; c.update(dt, t); }
  ch.doAct('sig'); run('拍翅招式', 90, () => {});
  c.stop(false); c.standAt(20, 15, 0); c.sitAt({ x: 20, y: 0.42, z: 15, face: 0 }, { instant: true }); c.setAction('type'); run('坐著打字', 60, () => {});
  // 坐著時翅膀有沒有擋在臉前：翅膀包圍盒的最前面 z 不超過身體最前面 z 的一半
  const body = new T.Box3().setFromObject(ch.main); let wz = -9; for (const a of ch.apps) if (a.fn) wz = Math.max(wz, new T.Box3().setFromObject(a.piv).max.z);
  res.翅膀最前z比身體 = +(wz - (body.min.z + body.max.z) / 2).toFixed(3); res.身體半深 = +((body.max.z - body.min.z) / 2).toFixed(3);
  c.dispose(); return res; }"""

_MUG_JS = """async () => {
  const W = window.__world, T = W.THREE, mod = await import('/office/play/office_character.js');
  const st = new T.Scene(), cam = new T.PerspectiveCamera(28, 1, 0.05, 100), env = { camera: cam, fx: W.fx, followed: null, bounds: { x0: 0.6, x1: 39.4, z0: 0.6, z1: 40 } };
  const c = mod.createCharacter({ id: 'mg', nick: 'mg', species: 'mug', pal: 0, acc: ['badge', 'tie'] }, env); st.add(c.object3D); c.standAt(20, 15, 0); const ch = c.inner; let t = 4000; const dt = 1 / 60, out = {};
  const disc = ch.slosh.children[0], inv = new T.Matrix4(), v = new T.Vector3(), P = disc.geometry.attributes.position;
  const handle = new T.Vector3(0.275, 0.31, 0);
  const meas = () => { ch.root.updateMatrixWorld(true); inv.copy(ch.deform.matrixWorld).invert(); let my = -9, rad = 0; for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i).applyMatrix4(disc.matrixWorld).applyMatrix4(inv); my = Math.max(my, v.y); rad = Math.max(rad, Math.hypot(v.x, v.z)); }
    let hd = 9; ch.hands.forEach(h => { v.copy(h.p); if (!c.object3D.parent.isScene) v.applyMatrix4(ch.scene.matrixWorld); const q = ch.deform.worldToLocal(v.clone()); /* 手球到把手環（圓心 handle、半徑 0.105、在 xy 平面）的距離 */ const dx = Math.hypot(q.x - handle.x, q.y - handle.y) - 0.105; hd = Math.min(hd, Math.hypot(dx, q.z) - 0.036); }); return { y: my, rad, hd, pitch: Math.abs(ch.pitch) }; };
  const run = (name, n, act) => { c.stop(false); c.standAt(20, 15, 0); if (act === 'type') c.sitAt({ x: 20, y: 0.42, z: 15, face: 0 }, { instant: true }); if (act === 'sig') ch.doAct('sig'); else if (act) c.setAction(act); let o = { y: -9, rad: 0, hd: 9, pitch: 0 }; for (let i = 0; i < n; i++) { t += dt; c.update(dt, t); if (i > 10) { const m = meas(); o = { y: Math.max(o.y, m.y), rad: Math.max(o.rad, m.rad), hd: Math.min(o.hd, m.hd), pitch: Math.max(o.pitch, m.pitch) }; } } out[name] = o; };
  run('站', 60, null); run('睡', 240, 'sleep'); run('看書', 120, 'read'); run('舉手', 90, 'raise'); run('坐打字', 90, 'type'); run('乾杯招式', 70, 'sig');
  c.stop(false); c.standAt(20, 15, 0); for (let i = 0; i < 20; i++) { t += dt; c.update(dt, t); } let mw = 0; for (let i = 0; i < 90; i++) { c.drive(0, 3.4, 0, 1); t += dt; c.update(dt, t); if (i > 8) { const m = meas(); out['跑'] = out['跑'] || { y: -9, rad: 0, hd: 9, pitch: 0 }; out['跑'].y = Math.max(out['跑'].y, m.y); out['跑'].hd = Math.min(out['跑'].hd, m.hd); out['跑'].pitch = Math.max(out['跑'].pitch, m.pitch); } }
  out.rim = 0.56; c.dispose(); return out; }"""

_MISC_JS = """async () => {
  const W = window.__world, T = W.THREE, mod = await import('/office/play/office_character.js'), out = {};
  const st = new T.Scene(), cam = new T.PerspectiveCamera(28, 1, 0.05, 100), env = { camera: cam, fx: W.fx, followed: null, bounds: { x0: 0.6, x1: 39.4, z0: 0.6, z1: 40 } }; let t = 4500; const dt = 1 / 60;
  const mk = (sp, acc) => { const c = mod.createCharacter({ id: 'm_' + sp, nick: sp, species: sp, pal: 0, acc: acc || [] }, env); st.add(c.object3D); c.standAt(20, 15, 0); for (let i = 0; i < 30; i++) { t += dt; c.update(dt, t); } return c; };
  // 八寶：走路時觸手最低點不低於地面（會被地面裁掉變碎片）
  { const c = mk('octo'), ch = c.inner; let lo = 9; for (let i = 0; i < 140; i++) { c.drive(1.5, 0); t += dt; c.update(dt, t); if (i > 20 && i % 4 === 0) for (const a of ch.apps) if (a.wig != null) { a.piv.updateWorldMatrix(true, true); a.piv.traverse(m => { if (!m.isMesh) return; const P = m.geometry.attributes.position, v = new T.Vector3(); for (let k = 0; k < P.count; k += 3) { v.fromBufferAttribute(P, k).applyMatrix4(m.matrixWorld); lo = Math.min(lo, v.y - c.object3D.position.y); } }); } } out.octoLow = +lo.toFixed(3); c.dispose(); }
  // 啃啃：尾根埋進身體
  { const c = mk('dino'), ch = c.inner; out.dinoTailZ = ch.tail.piv.position.z; c.dispose(); }
  // 閃閃：腳（皮膚）與身體同色
  { const c = mk('star'), ch = c.inner; out.starLimb = (ch.limbMat.userData.o.color === ch.main.material.userData.o.color); out.starFootMat = !!ch.footMat && ch.footMat !== ch.limbMat; c.dispose(); }
  // 圍巾：環的粗細（包圍盒高度）與顏色（和身體色相差 60 度以上，或身體本身幾乎沒有顏色）
  for (const sp of ['cactus', 'ghost', 'bean', 'bird']) { const c = mk(sp, ['scarf']), ch = c.inner; let ring = null; ch.deform.traverse(o => { if (o.userData && o.userData.scarfRing) ring = o; });
    if (!ring) { out['scarf_' + sp] = null; c.dispose(); continue; }
    ring.geometry.computeBoundingBox(); const bb = ring.geometry.boundingBox, hs = {}, hb = {}; new T.Color(ring.material.userData.o.color).getHSL(hs); new T.Color(ch.main.material.userData.o.color).getHSL(hb);
    let d = Math.abs(hs.h - hb.h); d = Math.min(d, 1 - d); out['scarf_' + sp] = { th: +(bb.max.y - bb.min.y).toFixed(3), hue: Math.round(d * 360), sat: +hb.s.toFixed(2) }; c.dispose(); }
  return out; }"""

_NOSE_JS = """async () => {
  const SP = await import('/office/play/species.js'), out = [];
  for (const [k, v] of Object.entries(SP.SPECIES)) if (v.face && (v.face.nose || v.face.nostril)) out.push(k);
  const src = await (await fetch('/office/play/face.js')).text();
  return { open: out, drawsNose: /if \\(s\\.nose\\)|if \\(s\\.nostril\\)/.test(src) }; }"""


def t_auditfix2(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 800, "height": 500})
    pg = c.new_page(); pg.set_default_timeout(180000); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.3&view=ceo", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    ok("外觀修正2：載入完成", got)
    if not got:
        c.close(); return
    try:
        # ── A8 配件
        rows = pg.evaluate(_ACC_JS)
        ok("A8 全部 %d 種物種逐一戴上識別證、領帶、圍巾、帽子、蝴蝶結、皇冠" % len(rows), len(rows) >= 25, len(rows))
        bad = [r for r in rows if r["heads"] > 1]
        ok("A8 同一隻頭上最多一件頭飾（帽子／蝴蝶結／皇冠擇一）：%d 種違規" % len(bad), not bad, bad[:3])
        low = [(r["sp"], r["min_y"]) for r in rows if r["tieY"] is not None and r["min_y"] < 0.04]
        ok("A8 識別證與領帶最低點離地 ≥ 0.04 公尺（不貼地）：%d 種違規" % len(low), not low, low[:3])
        out_ = [(r["sp"], r["over_z"]) for r in rows if r["tieY"] is not None and r["over_z"] > 0.06]
        ok("A8 識別證與領帶不浮在身體前面超過 0.06 公尺（貼著身體表面）：%d 種違規" % len(out_), not out_, out_[:3])
        below = [(r["sp"], r["tieY"], r["mouthY"]) for r in rows if r["tieY"] is not None and r["tieY"] > r["mouthY"] + 1e-6]
        ok("A8 領帶掛點不高過嘴巴（在下巴下方貼著身體）：%d 種違規" % len(below), not below, below[:3])
        dup = [r["sp"] for r in rows if r["dup"]]
        ok("A8 識別證與領帶不掛同一個位置（左右相距 ≥ 0.1）：%d 種違規" % len(dup), not dup, dup[:3])
        mis = pg.evaluate(_MISC_JS)
        ok("A9 八寶走路時觸手最低點 %.3f ≥ -0.005（不低於地面，不再被裁成碎片）" % mis["octoLow"], mis["octoLow"] >= -0.005, mis)
        ok("A9 啃啃尾巴根部埋進身體（根部 z = %.2f ≥ -0.12）" % mis["dinoTailZ"], mis["dinoTailZ"] >= -0.12, mis)
        ok("A9 閃閃的腳與身體同色、腳掌另用鞋色", mis["starLimb"] and mis["starFootMat"], mis)
        for sp in ("cactus", "ghost", "bean", "bird"):
            sc = mis["scarf_" + sp]
            ok("A8 圍巾 %s：環厚 %.3f ≤ 0.1（修正前約 0.15 像游泳圈），與身體色相差 %d 度（要 ≥ 60，身體近無彩色 %.2f<0.2 除外）" % (sp, sc["th"], sc["hue"], sc["sat"]), sc and sc["th"] <= 0.1 and (sc["hue"] >= 60 or sc["sat"] < 0.2), sc)
        # ── A9 拿鐵
        mg = pg.evaluate(_MUG_JS)
        worst_y = max(v["y"] for k, v in mg.items() if isinstance(v, dict))
        ok("A9 拿鐵咖啡液面最高點 %.3f ≤ 杯口 0.56（睡／看書／舉手／坐／乾杯／跑，都不凸出）" % worst_y, worst_y <= mg["rim"] + 1e-3, mg)
        worst_rad = max(v["rad"] for v in mg.values() if isinstance(v, dict) and "rad" in v and v["rad"])
        ok("A9 拿鐵液面半徑 %.3f ≤ 杯內壁 0.25" % worst_rad, worst_rad <= 0.25 + 1e-3, mg)
        worst_p = max(v["pitch"] for v in mg.values() if isinstance(v, dict))
        ok("A9 拿鐵前傾角度最大 %.1f 度 ≤ 10 度（睡覺、看書時整杯不再往前翻）" % (worst_p * 57.3), worst_p <= 0.175 + 1e-3, mg)
        hd = min(v["hd"] for k, v in mg.items() if isinstance(v, dict) and k != "跑")
        ok("A9 拿鐵的手到把手最近 %.3f 公尺 ≥ 0.02（站／睡／看書／舉手／坐／乾杯，不穿過把手）" % hd, hd >= 0.02, mg)
        # ── A10 啾啾
        bd = pg.evaluate(_BIRD_JS)
        ok("A10 啾啾沒有手球（改成兩片貼身小翅 %d 片）" % bd["wings"], bd["hands"] == 0 and bd["wings"] == 2, bd)
        far = max(bd[k] for k in ("站", "走", "跑", "轉身", "坐著打字"))
        ok("A10 啾啾拍翅招式時翅膀最遠 %.2f 倍 ≤ 2.4（招式本來就要張開）" % bd["拍翅招式"], bd["拍翅招式"] <= 2.4, bd)
        ok("A10 啾啾翅膀離身體中心最遠 %.2f 倍身體半徑 ≤ 2.0（站／走／跑／轉身／坐著打字，修正前跑步時整片離身）" % far, far <= 2.0, bd)
        ok("A10 走路時翅膀有在小幅拍動（擺幅 %.3f 弧度 > 0.1 且 < 0.9）" % bd["走擺幅"], 0.1 < bd["走擺幅"] < 0.9, bd)
        ok("A10 站著時翅膀只有輕微的待機擺動（擺幅 %.3f < 0.2，走路是 %.3f）" % (bd["站擺幅"], bd["走擺幅"]), bd["站擺幅"] < 0.2 and bd["站擺幅"] < bd["走擺幅"] * 0.5, bd)
        ok("A10 拍翅膀招式的擺幅 %.3f 大於走路 %.3f（動作真的有變化）" % (bd["拍翅招式擺幅"], bd["走擺幅"]), bd["拍翅招式擺幅"] > bd["走擺幅"], bd)
        ok("A10 坐著打字時翅膀在身體兩側不擋臉（最前端比身體中心前 %.3f ≤ 身體半深 %.3f）" % (bd["翅膀最前z比身體"], bd["身體半深"]), bd["翅膀最前z比身體"] <= bd["身體半深"] * 0.75, bd)
        # ── 硬性規則：不要鼻子
        nz = pg.evaluate(_NOSE_JS)
        ok("不要鼻子：25 種物種都沒有開 nose／nostril（開著的：%s）" % (nz["open"] or "無"), not nz["open"], nz)
        ok("不要鼻子：face.js 不再畫鼻點與鼻孔", not nz["drawsNose"], nz)
        ok("外觀修正2：沒有主控台錯誤", not errs, errs[:3])
    finally:
        c.close()


register("辦公室外觀修正2", lambda pg, b, base, code: t_auditfix2(b, base))
