# 驗收段落「手腳跟隨」：操控移動、跑、跳、急轉、瞬間改變方向、被拎起再放下、坐下、睡覺時，每隻角色的手腳（含皮膚）
# 到身體的世界距離都不得超過身高的 2.0 倍。（擁有者 11-13 回報：操控 CEO 在走道上移動，手腳留在後面。
# 根因：辦公室群組對 CEO 放大 1.18 倍、寵物縮小，皮膚與跳躍時的腳用「世界座標」算，手腳網格卻用「群組內座標」，兩者差 (縮放−1)×離原點的距離，越遠偏越多。）
# 手動以 1/60 秒一步推進（模擬高幀率），不靠瀏覽器幀率；軟體繪圖很慢，所以不用真實時間。
# flake8: noqa
LIMIT = 2.0
LIMIT_HELD = 4.0     # 被拎在半空中時手腳本來就會垂下來晃（寵物個子小，相對身高更大）

_JS = """(id) => { const W = __world, V = W.THREE.Vector3, a = new V(), b = new V(), c = W.chars.get(id) || W.pets.find(p => p.spec.id === id), ch = c.inner, out = {};
 W.speed = 0.01; let t = W.time; const dt = 1 / 60;
 const meas = () => { c.object3D.updateMatrixWorld(true); c.object3D.getWorldPosition(a); const H = c.height; let m = 0;
   ch.hands.forEach(h => { h.m.getWorldPosition(b); m = Math.max(m, b.distanceTo(a)); }); ch.feet.forEach(f => { f.m.getWorldPosition(b); m = Math.max(m, b.distanceTo(a)); });
   if (ch.skin) { const P = ch.skin.pos, M = ch.skin.mesh.matrixWorld, v = new V(); for (let i = 0; i < P.length; i += 15) { v.set(P[i], P[i + 1], P[i + 2]).applyMatrix4(M); m = Math.max(m, v.distanceTo(a)); } }
   return m / H; };
 const run = (name, n, fn, skip = 0) => { let mx = 0; for (let i = 0; i < n; i++) { fn(i); t += dt; c.update(dt, t); if (i >= skip) mx = Math.max(mx, meas()); } out[name] = +mx.toFixed(2); };   // skip：瞬間傳送後的前幾幀（遠景角色每 3 幀才重算一次姿態）不計
 c.stop(false); c.standAt(20, 26, 0); c.busy = true; for (let i = 0; i < 20; i++) { t += dt; c.update(dt, t); }
 run('站', 60, () => c.drive(0, 0)); run('走', 120, () => c.drive(0, 1.5, 0, 1)); run('跑', 120, () => c.drive(0, 3.4, 0, 1));
 run('轉身', 120, i => { const an = i * 0.2; c.drive(Math.sin(an) * 3.4, Math.cos(an) * 3.4, Math.sin(an), Math.cos(an)); });
 run('瞬間反向', 120, i => { const d = (Math.floor(i / 10) % 2) ? 1 : -1; c.drive(d * 3.4, 0, d, 0); });
 run('跳', 90, i => { if (i === 0) { ch.extFall = true; ch.vel.y = 4.6; ch.pos.y = 0.001; ch.feet.forEach(f => f.planted = false); } c.drive(0, 2, 0, 1); });
 c.drive(null); for (let i = 0; i < 60; i++) { t += dt; c.update(dt, t); }
 run('被拎起放下', 150, i => { if (i === 0) c.grab(); if (i < 90) c.dragTo(c.object3D.position.x + 0.05 * Math.sin(i * 0.2), 1.05, c.object3D.position.z + 0.03); if (i === 90) c.release(); });
 for (let i = 0; i < 120; i++) { t += dt; c.update(dt, t); }
 c.stop(false); const sp = W.spots.find(q => q.name === 'seat:' + id);
 if (sp && sp.seat) { c.standAt(sp.seat.x, sp.seat.z, 0); run('坐下', 90, i => { if (i === 0) c.sitAt(sp.seat, { instant: true }); }, 6); run('睡覺', 90, i => { if (i === 0) c.setAction('sleep'); }); }
 return out; }"""


def t_limbs(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 800, "height": 500})
    pg = c.new_page(); pg.set_default_timeout(120000); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.3&view=ceo", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    ok("手腳跟隨：載入完成", got)
    if not got:
        c.close(); return
    try:
        pg.evaluate("() => { __world.setView('char', __world.chars.get('ceo'), true); }")
        ids = pg.evaluate("() => [...__world.chars.keys()]")
        # 每個物種挑一位（共 %d 位角色、25 種物種都涵蓋）＋CEO（放大 1.18）＋寵物（縮小）
        seen, pick = set(), ["ceo"]
        for i in ids:
            sp = pg.evaluate("(i) => __world.chars.get(i).spec.species", i)
            if sp not in seen:
                seen.add(sp); pick.append(i)
        pick += pg.evaluate("() => __world.pets.map(p => p.spec.id)")
        worst = (0, None)
        bad = []
        for cid in dict.fromkeys(pick):
            r = pg.evaluate(_JS, cid)
            m = max(v for v in r.values() if v == v)
            if m > worst[0]:
                worst = (m, cid, r)
            if not all(v == v and v <= (LIMIT_HELD if k == '被拎起放下' else LIMIT) for k, v in r.items()):
                bad.append((cid, r))
        ok("手腳跟隨：%d 個角色（%d 種物種＋CEO＋寵物）在 站／走／跑／轉身／瞬間反向／跳／被拎起放下／坐下／睡覺 時，手腳到身體的距離都 ≤ 身高的 %.1f 倍（被拎起時 ≤ 4 倍；最大 %.2f，%s）" % (len(dict.fromkeys(pick)), len(seen), LIMIT, worst[0], worst[1]), not bad, bad[:2])
        ok("手腳跟隨：沒有主控台錯誤", not errs, errs[:3])
    finally:
        c.close()


register("辦公室手腳", lambda pg, b, base, code: t_limbs(b, base))
