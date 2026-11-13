# 驗收段落「辦公室外觀修正」：AI Office 角色外觀稽核（docs/ai_office/character_audit_1113.md）A 類第一批的量化驗收。
#   A1 背面不出現臉（貼貼、夾夾、算算）；正面的臉還在     A2 彎彎沒有懸空的手
#   A3 滾滾沒有鼻子、啃啃沒有鼻吻鼓包與鼻孔點            A4 貼貼、夾夾、啵啵的手腳根部不比身體厚（不穿出白色碎片）
#   A5 手離身體中心 ≤ 2.2 倍身體半徑（站／走／跑／轉身／瞬間反向／跳；被拎起不算，另有 20261113_office_limbs 管）
#   A7 坐墊 ≤ 0.12 公尺、不夠的改升椅子座面、嘴巴高度不變；背後太長的往前坐；CEO 縮到 1.08 倍
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
    run('站', 40, () => c.drive(0, 0)); run('走', 90, () => c.drive(0, 1.5, 0, 1)); run('跑', 90, () => c.drive(0, 3.4, 0, 1));
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
