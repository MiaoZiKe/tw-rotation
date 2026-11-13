// 角色 QA 量測（開發用，掛在 window.CH.qa）：固定時間步模擬，不依賴實際繪圖幀率；每個函式回傳 JSON，可由 Playwright 或 uitest 直接取用。
// 這些量測的原則：量「骨頭矩陣與網格的實際結果」，不是量控制器自己宣稱的內部狀態。
import * as THREE from 'three';

const V = THREE.Vector3;
function mulberry(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

export function makeQA(CH) {
  const cc = () => CH.cc;
  const finite = (c) => { const b = c.body; if (![b.x, b.y, b.z, b.vx, b.vy, b.vz, b.yaw].every(Number.isFinite)) return false; for (const v of c.pose) if (!Number.isFinite(v)) return false; for (const bn of c.ch.body.skeleton.bones) { const e = bn.matrixWorld.elements; for (let i = 0; i < 16; i++) if (!Number.isFinite(e[i])) return false; } return true; };   // 含骨頭世界矩陣（NaN 會讓蒙皮頂點消失，最低點量測會被漏掉）
  function prepare(o = {}) {
    CH.S.paused = true; CH.S.noFollow = true; const c = cc(); c.life = false; c.ch.face.autoBlink = false; c.reset(o.x ?? 0, o.z ?? 0, o.yaw ?? 0);
    c.bus.conflicts.length = 0; c.rejects.length = 0; c.feet.stats = { maxRatio: 1, minRatio: 1, clamped: 0, slide: 0 }; c.debug.proj = 0; c.debug.projMax = 0; return c;
  }
  /** 以 fps 推進 secs 秒；fn(t, i) 每幀更新前呼叫；after(t, i) 更新後呼叫 */
  function run(c, fps, secs, fn, after) {
    const dt = 1 / fps, n = Math.round(secs * fps);
    for (let i = 0; i < n; i++) { const t = i * dt; if (fn) fn(t, i); c.update(dt); if (after && after(t, i) === false) return i; }
    return n;
  }
  const until = (c, fps, max, cond) => { const dt = 1 / fps; for (let i = 0; i < max * fps; i++) { if (cond()) return i * dt; c.update(dt); } return cond() ? max : -1; };

  // 1 跳躍頂點：不同畫面幀率
  function jumpApex(fps) {
    const c = prepare(); let maxPhys = 0, maxVis = 0, t0 = -1, tl = -1;
    c.jump(); run(c, fps, 2.0, null, (t) => { maxPhys = Math.max(maxPhys, c.body.y); maxVis = Math.max(maxVis, c.ch.root.position.y); if (t0 < 0 && !c.body.grounded) t0 = t; if (t0 >= 0 && tl < 0 && c.body.grounded) tl = t; });
    const J = c.P.jump; return { fps, maxPhys, maxVis, expected: J.height, airTime: tl - t0 };
  }
  // 2 腳鎖地＋腿長：沿圓弧走／跑，量腳踝骨頭的世界位置
  function footLock(kind, fps, curve) {
    const spd = kind === 'run' ? 1.3 : 0.6, w = curve ? (kind === 'run' ? 1.5 : 0.85) : 0;   // 弧線半徑 v/w，圓心 (0, 0.3)，不碰箱子與凳子
    const c = prepare({ x: curve ? 0 : -1.9, z: curve ? 0.3 + spd / w : 0, yaw: Math.PI / 2 }), L0 = c.feet.L0, run_ = kind === 'run';
    const ank = [new V(), new V()], hip = new V(), foot = [c.ch.bones['foot.L'], c.ch.bones['foot.R']], leg = [c.ch.bones['leg.L'], c.ch.bones['leg.R']];
    const st = [{ prev: 'x', start: null, max: 0 }, { prev: 'x', start: null, max: 0 }], worst = []; let ratioMax = 0, ratioMin = 9, intervals = 0, solePen = 0, soleAir = 0;
    const th0 = Math.PI / 2;
    run(c, fps, curve ? 8 : (run_ ? 3.3 : 5.8), (t) => { const th = th0 + w * t; c.setMove(Math.sin(th), Math.cos(th), 1, run_); }, (t, i) => {
      if (t < 0.5) return;
      c.ch.model.updateMatrixWorld(true);
      for (let k = 0; k < 2; k++) {
        const f = c.feet.feet[k]; foot[k].getWorldPosition(ank[k]); leg[k].getWorldPosition(hip); const r = hip.distanceTo(ank[k]) / L0; ratioMax = Math.max(ratioMax, r); ratioMin = Math.min(ratioMin, r);
        const s = st[k];
        if (f.mode === 'plant' && c.feet.cad > 0 && s.prev === 'plant') { if (!s.start) { s.start = ank[k].clone(); intervals++; } s.max = Math.max(s.max, Math.hypot(ank[k].x - s.start.x, ank[k].z - s.start.z)); if (s.max > 0.005) worst.push(+s.max.toFixed(4)); }
        else if (s.start) { s.start = null; s.done = Math.max(s.done || 0, s.max); s.max = 0; }
        if (f.mode === 'plant' && c.feet.cad > 0 && s.prev === 'plant') { const g = f.gy; /* 腳底最低 ≈ 踝 y − 0.045（量網格） */ }
        s.prev = f.mode;
      }
    });
    return { kind, fps, curve: !!curve, maxSlide: Math.max(st[0].done || 0, st[1].done || 0, st[0].max, st[1].max), intervals, ratioMax, ratioMin, over5mm: worst.length, stats: c.feet.stats, proj: c.debug.proj };
  }
  // 3 速度 = 步頻 × 步幅：由實際落腳點量
  function strideTest(kind, fps) {
    const c = prepare({ x: -1.9, z: 0, yaw: Math.PI / 2 }), ev = [[], []]; c.feet.rec = [];
    run(c, fps, kind === 'run' ? 3.2 : 5.8, () => c.setMove(1, 0, 1, kind === 'run'));
    for (const e of c.feet.rec) if (e.from === 'swing') ev[e.side === 'L' ? 0 : 1].push(e);   // 落腳點與固定步的模擬時間（不受畫面幀率量化）
    const rows = [];
    for (let k = 0; k < 2; k++) for (let i = 2; i < ev[k].length - 1; i++) {
      const a = ev[k][i - 1], b = ev[k][i], dtt = b.t - a.t, stride = Math.hypot(b.x - a.x, b.z - a.z), cad = 1 / dtt, speed = Math.hypot(b.bx - a.bx, b.bz - a.bz) / dtt;
      rows.push({ stride, cad, speed, err: Math.abs(speed - stride * cad) / speed });
    }
    const avg = (f) => rows.reduce((s, r) => s + f(r), 0) / Math.max(1, rows.length);
    return { kind, fps, n: rows.length, speed: avg(r => r.speed), stride: avg(r => r.stride), cad: avg(r => r.cad), errMean: avg(r => r.err), errMax: Math.max(...rows.map(r => r.err)) };
  }
  // 4 全程最低點（全部頂點）
  function lowest(name, fps = 60) {
    const c = prepare({ x: 0, z: 0.6, yaw: 0 }); let mn = 1e9, mnAt = '', maxJump = 0, last = null, frames = 0, badFrames = 0;
    const names = c.ch.body.skeleton.bones.map(x => x.name), sk = c.ch.body.geometry.attributes.skinIndex, sw = c.ch.body.geometry.attributes.skinWeight; let mnBone = '';
    const chk = (t, i) => { frames++; if (!finite(c)) badFrames++; { const who = {}, v = c.lowestBody(true, who) - c.body.supportY; if (v < mn) { mn = v; let bi = 0, bw = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(who.i, k); if (w > bw) { bw = w; bi = sk.getComponent(who.i, k); } } mnBone = names[bi]; mnAt = c.state + '/' + (c.sit?.sub || '') + '@' + t.toFixed(2); } } const p = c.ch.root.position; if (last) maxJump = Math.max(maxJump, p.distanceTo(last)); last = p.clone(); };
    const S = {
      idle: () => run(c, fps, 1.5, null, chk),
      walk: () => { run(c, fps, 2.5, () => c.setMove(0, 1, 1, false), chk); c.setMove(0, 0, 0); run(c, fps, 1.2, null, chk); },
      run: () => { run(c, fps, 2.2, () => c.setMove(0, 1, 1, true), chk); c.setMove(0, 0, 0); run(c, fps, 1.2, null, chk); },
      jump: () => { run(c, fps, 0.4, null, chk); c.jump(); run(c, fps, 1.8, null, chk); },
      runjump: () => { run(c, fps, 1.2, () => c.setMove(0, 1, 1, true), chk); c.jump(); run(c, fps, 1.6, () => c.setMove(0, 1, 1, true), chk); c.setMove(0, 0, 0); run(c, fps, 1.4, null, chk); },
      sit: () => { c.sitOn('stool'); run(c, fps, 9, null, chk); c.standUp(); run(c, fps, 3, null, chk); },
      sleep: () => { c.sleep(); run(c, fps, 2.2, null, chk); c.wake(); run(c, fps, 1.8, null, chk); },
      pet: () => { c.petStart(); run(c, fps, 1.2, null, chk); c.petEnd(); run(c, fps, 1.4, null, chk); },
      overlays: () => { for (const k of ['hit', 'happy', 'angry', 'sad']) { c.trigger(k); run(c, fps, 2.4, null, chk); } },
      throw: () => { c.throwAt(2.5, 5.0, 1.5); run(c, fps, 5, null, chk); },
    };
    S[name](); return { name, badFrames, min: mn, at: mnAt, bone: mnBone, maxJump, frames, proj: c.debug.proj, projMax: c.debug.projMax, finite: finite(c), conflicts: c.bus.conflicts.length };
  }
  // 5 打斷後回到 Idle：骨頭與形態鍵回到靜止值、位置沒被重設
  function restDiff(c) {
    const ch = c.ch; let worstQ = 0, worstP = 0, worstName = '', worstM = 0;
    for (const [nm, b] of Object.entries(ch.bones)) {
      const r = ch.rest[nm];   // 角度用弦長估算（acos 在 1 附近會放大浮點誤差）
      const sg = b.quaternion.dot(r.q) < 0 ? -1 : 1, dq = 2 * Math.hypot(b.quaternion.x - sg * r.q.x, b.quaternion.y - sg * r.q.y, b.quaternion.z - sg * r.q.z, b.quaternion.w - sg * r.q.w);; const dp = b.position.distanceTo(r.p);
      if (dq > worstQ) { worstQ = dq; worstName = nm; } worstP = Math.max(worstP, dp);
    }
    for (const m of ['squash', 'stretch', 'land', 'plump', 'breath', 'cheek.L', 'cheek.R']) worstM = Math.max(worstM, Math.abs(ch.wm[m] || 0));
    return { worstQ, worstP, worstM, worstName };
  }
  function interruptFrom(name, fps = 60) {
    const untilU = (...a) => { const r = until(...a); last = c.ch.root.position.clone(); return r; };
    const c = prepare({ x: -0.5, z: 0.4, yaw: 0.4 }); let maxStep = 0, last = c.ch.root.position.clone(); const track = () => { const p = c.ch.root.position; maxStep = Math.max(maxStep, p.distanceTo(last)); last = p.clone(); };
    const go = (secs, fn) => run(c, fps, secs, fn, () => { track(); });
    const enter = {
      idle: () => go(0.3), walk: () => go(0.8, () => c.setMove(0.3, 1, 1, false)), run: () => go(1.0, () => c.setMove(0.3, 1, 1, true)),
      jumpPrep: () => { c.jump(); untilU(c, fps, 1, () => c.state === 'jumpPrep'); go(0.05); },
      air: () => { c.jump(); untilU(c, fps, 2, () => c.state === 'air'); go(0.2); }, land: () => { c.jump(); untilU(c, fps, 2, () => c.state === 'land'); go(0.05); },
      sit: () => { c.sitOn('stool'); untilU(c, fps, 14, () => c.sit && c.sit.sub === 'seated'); go(0.5); }, sleep: () => { c.sleep(); go(1.2); },
      held: () => { c.grab(0, 1.0, 0.4); go(0.8); }, tumble: () => { c.throwAt(2.5, 5, 1.5); go(0.5); }, recover: () => { c.throwAt(0.5, 3.4, 0); untilU(c, fps, 6, () => c.state === 'recover'); go(0.1); },
      hit: () => { c.trigger('hit'); go(0.15); }, happy: () => { c.trigger('happy'); go(0.4); }, angry: () => { c.trigger('angry'); go(0.4); }, sad: () => { c.trigger('sad'); go(0.6); },
      pet: () => { c.petStart(); go(0.7); },
    };
    enter[name](); last = c.ch.root.position.clone(); const ent = { state: c.state, sub: c.sit?.sub || null };
    const pos0 = [c.body.x, c.body.z];
    c.stop(); const r = c.interrupt();
    // 空中／坐著／被抓：等它自己落地、起身、回到 Idle
    let guard = 0; while (guard++ < 40 * fps) { if (c.state === 'idle' && !c.overlay && !c.pet.want) break; if (c.state === 'sit' && c.sit?.sub === 'seated') c.standUp(); if (c.state === 'sleep') c.interrupt(); go(1 / fps); }
    const tIdle = guard / fps; go(3.5);   // 次級彈簧、腳補步都結束
    const d = restDiff(c); return { name, entered: ent, ret: r, idleAfter: +tIdle.toFixed(2), state: c.state, ...d, maxStep, dispAfter: Math.hypot(c.body.x - pos0[0], c.body.z - pos0[1]), atSpawn: Math.hypot(c.body.x + 0.5, c.body.z - 0.4) < 0.02, finite: finite(c), conflicts: c.bus.conflicts.length };
  }
  // 6 隨機狀態風暴
  function storm(n = 500, seed = 7, fps = 60) {
    const c = prepare({ x: 0, z: 0.5, yaw: 0 }), R = mulberry(seed), dt = 1 / fps; let bad = 0, maxStateT = 0, maxOut = 0, held = false, longState = ''; const counts = {};
    const acts = [
      () => c.setMove(R() - 0.5, R() - 0.5, 1, R() < 0.4), () => c.setMove(0, 0, 0), () => c.walkTo((R() - 0.5) * 3.6, (R() - 0.5) * 3.6, R() < 0.3), () => c.jump(), () => c.sitOn('stool'), () => c.standUp(),
      () => c.sleep(), () => c.wake(), () => c.grab((R() - 0.5) * 3, 0.9 + R() * 0.5, (R() - 0.5) * 3), () => c.release((R() - 0.5) * 6, R() * 5, (R() - 0.5) * 6), () => c.throwAt((R() - 0.5) * 10, R() * 7, (R() - 0.5) * 10),
      () => c.petStart(), () => c.petEnd(), () => c.trigger('hit'), () => c.trigger('happy'), () => c.trigger('angry'), () => c.trigger('sad'), () => c.stop(), () => c.interrupt(), () => c.faceTo(R() * 6.28),
    ];
    for (let k = 0; k < n; k++) {
      const ai = Math.floor(R() * acts.length); counts[ai] = (counts[ai] || 0) + 1; acts[ai]();
      const secs = 0.05 + R() * 0.65, fr = Math.round(secs * fps);
      for (let i = 0; i < fr; i++) {
        c.update(dt); if (!finite(c)) bad++;
        const b = c.body; if (Math.abs(b.x) > 2.31 || Math.abs(b.z) > 2.31 || b.y < -0.001 || b.y > 6) maxOut = Math.max(maxOut, Math.max(Math.abs(b.x), Math.abs(b.z), b.y > 6 ? b.y : 0));
        const exempt = ['sleep', 'held'].includes(c.state) || (c.state === 'sit' && c.sit?.sub === 'seated'); if (!exempt && c.stateT > maxStateT) { maxStateT = c.stateT; longState = c.state + '/' + (c.sit?.sub || ''); }
      }
    }
    // 收尾：放開一切、打斷、必須能回到 Idle 站穩
    c.petEnd(); c.stop(); if (c.state === 'held') c.release(0, 0, 0);
    let t = 0; while (t < 20) { c.update(dt); t += dt; if (c.state === 'idle' && !c.overlay && !c.pet.want) break; if (c.state === 'sit' && c.sit?.sub === 'seated') c.standUp(); else if (c.state === 'sleep') c.wake(); else if (c.state === 'held') c.release(0, 0, 0); else c.interrupt(); }
    run(c, fps, 3, null); const d = restDiff(c);
    return { n, bad, maxStateT, longState, maxOut, endState: c.state, tSettle: +t.toFixed(2), transitions: c.log.length, rejects: c.rejects.length, conflicts: c.bus.conflicts.length, dropped: c.stepper.dropped, finite: finite(c), ...d, onGround: c.body.grounded };
  }
  // 7 坐下：臀部（身體最低點）與凳面
  function sitContact(fps = 60) {
    const c = prepare({ x: 0.3, z: 1.2, yaw: 2.2 }), box = c.world.box('stool'), T = new V(); c.sitOn('stool');
    const tReach = until(c, fps, 14, () => c.sit && c.sit.sub === 'seated'); run(c, fps, 1.2, null);
    // 最低頂點（含形態鍵與蒙皮）的世界位置
    const ch = c.ch, b = ch.body, g = b.geometry, p = g.attributes.position, M = g.morphAttributes.position, w = b.morphTargetInfluences; ch.model.updateMatrixWorld(true); b.skeleton.update();
    let mn = 1e9, best = null; const legIdx = new Set();
    for (let i = 0; i < p.count; i++) { T.set(p.getX(i), p.getY(i), p.getZ(i)); for (let k = 0; k < M.length; k++) if (w[k]) { T.x += M[k].getX(i) * w[k]; T.y += M[k].getY(i) * w[k]; T.z += M[k].getZ(i) * w[k]; } b.applyBoneTransform(i, T); T.applyMatrix4(b.matrixWorld); if (T.y < mn) { mn = T.y; best = T.clone(); } }
    // 身體取樣（不含腿腳）最低點
    const bodyLow = c.lowestBody(false);
    const inFoot = Math.abs(best.x - box.cx) <= box.hx + 0.01 && Math.abs(best.z - box.cz) <= box.hz + 0.01;
    const yawErr = Math.abs(((c.body.yaw - box.face + Math.PI * 3) % (Math.PI * 2)) - Math.PI);
    const out = { tReach, seat: box.y1, bodyLow, gapBody: bodyLow - box.y1, lowestAll: mn, gapAll: mn - box.y1, lowestInSeat: inFoot, yawErr, state: c.state, sub: c.sit?.sub, bodyY: c.body.y, dx: c.body.x - box.cx, dz: c.body.z - box.cz };
    c.standUp(); const tUp = until(c, fps, 6, () => c.state === 'land' || c.state === 'idle'); run(c, fps, 1.2, null);
    out.afterRise = c.state; out.riseT = tUp; out.afterY = c.body.y; out.afterDist = Math.hypot(c.body.x - box.cx, c.body.z - box.cz); return out;
  }
  // 走過去位置真的變、跳躍回到地面、摸頭表情等（給 uitest 用的小工具）
  return { prepare, run, until, jumpApex, footLock, strideTest, lowest, interruptFrom, storm, sitContact, restDiff, finite };
}
