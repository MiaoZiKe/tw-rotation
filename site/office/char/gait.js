// 腳步規劃與腳 IK（第三階段）：
//  · 步態相位由「走過的距離」推進（相位速率＝速度÷步幅 ＝ 步頻），所以 速度 = 步頻 × 步幅 是構造出來的，不是調出來的；
//  · 著地期間腳的世界位置鎖定（plant）；擺動期間走拋物弧線到「預測的下一個落腳點」（swing）；
//  · 空中／坐著／被抓時腳跟著身體（free）；站定時用小步把腳補回原位（stand）；
//  · 腿只有一根骨頭（髖→踝），IK = 把腿骨轉向目標、再把腳骨沿腿軸平移到目標（腿皮膚伸縮，上限 maxStretch 倍）；
//  · 腳底最低點用腳掌網格的實際外形算（不是固定高度）：腳盆下沿 = 地面（或方塊頂面）+ 5 mm（與靜止姿勢一致）。
import * as THREE from 'three';

const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t;
const sm = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
const frac = (x) => x - Math.floor(x);
const angDiff = (a, b) => { let d = (b - a) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; };
const Y = new THREE.Vector3(0, 1, 0), X = new THREE.Vector3(1, 0, 0);
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3(), _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _q3 = new THREE.Quaternion(), _q4 = new THREE.Quaternion();

export class Feet {
  /** cfg：profile.gait；world：PhysWorld */
  constructor(ch, world, cfg) {
    this.ch = ch; this.world = world; this.cfg = cfg; this.phase = 0; this.cad = 0; this.stride = cfg.walk.stride[0]; this.kind = 'walk';
    this.maxStretch = cfg.maxStretch || 1.15; this.stats = { maxRatio: 1, minRatio: 1, clamped: 0, slide: 0 };
    this.feet = [1, -1].map(s => ({ s, side: s > 0 ? 'L' : 'R', mode: 'plant', x: 0, z: 0, gy: 0, yaw: 0, sw: null, goal: { x: 0, y: 0, z: 0, pitch: 0, yaw: 0 }, prev: { x: 0, y: 0, z: 0, pitch: 0, yaw: 0 }, blend: null, lastMode: 'plant', ratio: 1 }));
    // 腿骨長度、腳掌網格的底面點（相對踝、靜止姿勢）
    const r = ch.rest['foot.L']; this.L0 = r.p.length(); this.restAnkle = { x: ch.meta.bones['foot.L'].head[0], y: ch.meta.bones['foot.L'].head[1], z: ch.meta.bones['foot.L'].head[2] };
    const hp = ch.meta.bones['leg.L'].head; this.hip = { x: hp[0], y: hp[1], z: hp[2] };   // 髖位置取自模型
    cfg.footSpacing = this.hip.x * (cfg.footSpacingK ?? 0.86); cfg.centerZ = this.hip.z + (cfg.centerOff ?? 0.02);   // 步態落腳中心由模型量出，換模型不用改
    this.reachH = Math.sqrt(Math.max(1e-6, (0.97 * (cfg.maxStretch || 1.15) * this.L0) ** 2 - (this.hip.y + 0.015 + (cfg.bobReach || 0) - ch.meta.bones['foot.L'].head[1]) ** 2));   // 站立落腳點離髖的水平可及半徑（bobReach＝步態風格讓身體在站立期最多抬高多少，可及半徑要扣掉）
    this.sole = this.measureSole(); this.sub = this.buildSub(); this._T = new THREE.Vector3(); this._M = new THREE.Matrix4(); this._Q = new THREE.Quaternion(); this._S = new THREE.Vector3();
    // invB0＝靜止姿勢下 root 骨相對角色群組的矩陣之反矩陣
    ch.resetPose(); ch.model.updateMatrixWorld(true); this.invB0 = ch.bones.root.matrixWorld.clone().premultiply(ch.root.matrixWorld.clone().invert()).invert(); this.axis = { L: ch.rest['foot.L'].p.clone().normalize(), R: ch.rest['foot.R'].p.clone().normalize() }; this.restFootQ = {}; for (const f of this.feet) { const rr = ch.rest['foot.' + f.side]; this.restFootQ[f.side] = rr.pw.clone().multiply(rr.q); }
  }
  /** 每側腿＋腳掌的網格頂點索引（靜止姿勢 y<0.2、由該側腿骨或腳骨主導）：腳 IK 之後用它們算實際最低點，避免腿皮膚穿進地面 */
  buildSub() {
    const ch = this.ch, b = ch.body, g = b.geometry, p = g.attributes.position, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, T = new THREE.Vector3(), out = { L: [], R: [] };
    ch.resetPose(); ch.model.updateMatrixWorld(true); b.skeleton.update(); const bones = b.skeleton.bones, id = {}; for (const sd of ['L', 'R']) id[bones.indexOf(ch.bones['leg.' + sd])] = sd, id[bones.indexOf(ch.bones['foot.' + sd])] = sd;
    for (let i = 0; i < p.count; i++) {
      let bi = 0, bw = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; bi = si.getComponent(i, k); } }
      if (id[bi] === undefined || bw < 0.2) continue; T.set(p.getX(i), p.getY(i), p.getZ(i)); b.applyBoneTransform(i, T); if (T.y < this.hip.y * 1.9) out[id[bi]].push(i);
    }
    return out;
  }
  /** 該側腿＋腳掌頂點目前的最低世界 y（CPU 蒙皮；需先更新該側骨頭的世界矩陣） */
  lowestLeg(side) {
    const ch = this.ch, b = ch.body, g = b.geometry, p = g.attributes.position, T = this._T; b.skeleton.update(); let mn = 1e9;
    for (const i of this.sub[side]) { T.set(p.getX(i), p.getY(i), p.getZ(i)); b.applyBoneTransform(i, T); T.applyMatrix4(b.matrixWorld); if (T.y < mn) mn = T.y; }
    return mn;
  }
  measureSole() {
    const ch = this.ch, b = ch.body, g = b.geometry, p = g.attributes.position, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, T = new THREE.Vector3();
    ch.resetPose(); ch.model.updateMatrixWorld(true); b.skeleton.update();
    // 腳掌網格的實際頂點（相對踝、靜止姿勢）：只留 y 在踝下方的，之後每個步長用它們算最低點（不是用外框盒）
    const idx = b.skeleton.bones.indexOf(ch.bones['foot.L']), a = this.restAnkle, pts = [];
    for (let i = 0; i < p.count; i++) {
      let bi = 0, bw = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; bi = si.getComponent(i, k); } }
      if (bi !== idx || bw < 0.5) continue;
      T.set(p.getX(i), p.getY(i), p.getZ(i)); b.applyBoneTransform(i, T);
      if (T.y - a.y < -0.012) pts.push([T.x - a.x, T.y - a.y, T.z - a.z]);
    }
    this.restClear = Math.max(0, a.y + Math.min(...pts.map(q => q[1])));   // 靜止姿勢腳底離地的距離（取自模型）：站姿腳底離地＝此值，所以 Idle 與靜止姿勢完全一致
    return pts;
  }
  /** 腳掌俯仰 pitch（正＝腳尖向下）時，踝要比地面高多少，才能讓腳底最低點貼在地面上方 clear 公尺 */
  ankleH(pitch, clear = this.restClear) {
    const c = Math.cos(pitch), s = Math.sin(pitch); let mn = 1e9;
    for (const q of this.sole) mn = Math.min(mn, q[1] * c - q[2] * s);
    return clear - mn;
  }
  groundAt(b, x, z) { return this.world.supportAt(x, z, 0.03, b.y, 0.06).h; }
  // ── 固定步更新
  update(dt, b, d) {
    for (const f of this.feet) { const g = f.goal, p = f.prev; p.x = g.x; p.y = g.y; p.z = g.z; p.pitch = g.pitch; p.yaw = g.yaw; }
    const mode = d.mode; this.t = d.t;
    if (mode === 'gait' || mode === 'stand') {
      for (const f of this.feet) if (f.mode === 'free') this.plantAt(f, b, f.goal.x, f.goal.z);
      if (mode === 'gait') this.kind = d.kind || 'walk';
      this.gaitStep(dt, b, mode === 'gait');
    } else {
      for (const f of this.feet) { f.mode = 'free'; f.sw = null; }
      this.cad = 0;
    }
    for (const f of this.feet) this.makeGoal(f, b, d, dt);
  }
  plantAt(f, b, x, z) { if (this.rec) this.rec.push({ side: f.side, from: f.mode, t: this.t, x, z, bx: b.x, bz: b.z }); f.mode = 'plant'; f.x = x; f.z = z; f.yaw = b.yaw; f.gy = this.groundAt(b, x, z); f.sw = null; }
  bodyToWorld(b, lx, lz, yaw = b.yaw) { const c = Math.cos(yaw), s = Math.sin(yaw); return [b.x + lx * c + lz * s, b.z - lx * s + lz * c]; }
  homeWorld(f, b, yaw = b.yaw, px = b.x, pz = b.z) { const c = Math.cos(yaw), s = Math.sin(yaw), lx = f.s * this.restAnkle.x, lz = this.restAnkle.z; return [px + lx * c + lz * s, pz - lx * s + lz * c]; }
  gaitStep(dt, b, active) {
    const C = this.cfg, P = C[this.kind] || C.walk, v = Math.hypot(b.vx, b.vz), sp = v + Math.abs(b.wy) * C.turnR;
    const n = clamp(sp / P.vmax, 0, 1), stride = lerp(P.stride[0], P.stride[1], n); this.stride = stride;
    const going = active && sp > (this.cad > 0 ? 0.03 : 0.07) && b.grounded;
    if (!going) { this.cad = 0; this.standStep(dt, b); return; }
    this.cad = sp / stride; this.phase = frac(this.phase + this.cad * dt);
    const duty = P.duty, ex = stride * duty / 2 * (1 - Math.min(0.55, Math.abs(b.wy) * 0.45)),   // 轉彎時落腳點少往前伸
       vx = v > 1e-4 ? b.vx / v : 0, vz = v > 1e-4 ? b.vz / v : 0;
    for (const f of this.feet) {
      const pf = frac(this.phase + (f.s > 0 ? 0 : (P.sync ?? 0.5)));   // sync＝右腳相位落後量：0.5 交替走、0 雙腳同步（兔子跳步）
      if (f.mode === 'plant' && pf >= duty) { f.mode = 'swing'; f.sw = { fx: f.x, fz: f.z, fy: f.gy, fyaw: f.yaw, s: 0, timed: false, lift: P.lift, peak: P.liftPeak ?? 0.5, kick: P.kick || 0 }; }
      else if (f.mode === 'swing' && pf < duty && !f.sw.timed) { const t = f.sw; this.plantAt(f, b, t.tx ?? f.x, t.tz ?? f.z); f.yaw = t.tyaw ?? b.yaw; continue; }
      if (f.mode === 'swing') {
        const t = f.sw; if (t.timed) { this.timedSwing(f, b, dt); continue; }
        const s = clamp((pf - duty) / (1 - duty), 0, 1), rem = Math.max(0.01, (1 - s) * (1 - duty) / this.cad);
        const yaw = b.yaw + b.wy * rem, px = b.x + b.vx * rem, pz = b.z + b.vz * rem;
        const c = Math.cos(yaw), si = Math.sin(yaw), lx = f.s * C.footSpacing, lz = C.centerZ;
        t.tx = px + lx * c + lz * si + vx * ex + (f.hoX || 0); t.tz = pz - lx * si + lz * c + vz * ex + (f.hoZ || 0); t.tyaw = yaw;   // hoX/hoZ＝視覺上的髖相對名義髖的偏移（前傾、側傾、左右晃），落腳中心跟著實際髖走
        { // 落腳點不可超出「預測髖位置」的腿長可及範圍（急轉彎時，外側預測會偏遠 → 否則腳被迫滑動）
          const hx = px + this.hip.x * f.s * c + this.hip.z * si + (f.hoX || 0), hz = pz - this.hip.x * f.s * si + this.hip.z * c + (f.hoZ || 0), dx = t.tx - hx, dz = t.tz - hz, dl = Math.hypot(dx, dz);
          if (dl > this.reachH) { t.tx = hx + dx * this.reachH / dl; t.tz = hz + dz * this.reachH / dl; } } t.ty = this.groundAt(b, t.tx, t.tz); t.s = s;
        const e = sm(s); f.x = lerp(t.fx, t.tx, e); f.z = lerp(t.fz, t.tz, e); f.gy = lerp(t.fy, t.ty, e); f.yaw = t.fyaw + angDiff(t.fyaw, yaw) * e;
        if (t.kick) { const kk = t.kick * Math.sin(Math.PI * clamp((s - 0.2) / 0.8, 0, 1)) ** 1.5; f.x += Math.sin(yaw) * kk; f.z += Math.cos(yaw) * kk; }   // 往前踢：擺動後段腳掌伸出肚子前緣再落回落腳點（短腿角色側面才看得到在邁步）
      }
    }
  }
  /** 站定補步：兩腳不同時抬；離原位 > 1.2 cm 或朝向差 > 0.15 rad 就用 0.16 秒的小步補回 */
  standStep(dt, b) {
    for (const f of this.feet) if (f.mode === 'swing') {
      if (!f.sw.timed) { f.sw.timed = true; f.sw.age = f.sw.s * 0.16; f.sw.dur = 0.16; f.sw.fx = f.x; f.sw.fz = f.z; f.sw.fy = f.gy; f.sw.fyaw = f.yaw; f.sw.lift = 0.02; }
      this.timedSwing(f, b, dt);
    }
    if (this.feet.some(f => f.mode === 'swing')) return;
    let best = null, bd = 0;
    for (const f of this.feet) {
      const [hx, hz] = this.homeWorld(f, b), e = Math.hypot(f.x - hx, f.z - hz) + Math.abs(angDiff(f.yaw, b.yaw)) * 0.1;
      if ((e > 0.0003 || Math.abs(angDiff(f.yaw, b.yaw)) > 0.003) && e > bd) { bd = e; best = f; }
    }
    if (best) { best.mode = 'swing'; best.sw = { timed: true, age: 0, dur: 0.16, fx: best.x, fz: best.z, fy: best.gy, fyaw: best.yaw, lift: 0.02 }; }
  }
  timedSwing(f, b, dt) {
    const t = f.sw; t.age += dt; const s = clamp(t.age / t.dur, 0, 1), e = sm(s);
    const [hx, hz] = this.homeWorld(f, b); t.tx = hx; t.tz = hz; t.tyaw = b.yaw; t.ty = this.groundAt(b, hx, hz); t.s = s;
    f.x = lerp(t.fx, hx, e); f.z = lerp(t.fz, hz, e); f.gy = lerp(t.fy, t.ty, e); f.yaw = t.fyaw + angDiff(t.fyaw, b.yaw) * e;
    if (s >= 1) { f.mode = 'plant'; f.x = hx; f.z = hz; f.gy = t.ty; f.yaw = b.yaw; f.sw = null; }
  }
  makeGoal(f, b, d, dt) {
    const g = f.goal; let x, y, z, pitch = 0, yaw = f.yaw;
    if (f.mode === 'free') {
      const fr = d.free || {}; const lx = f.s * this.restAnkle.x, lz = this.restAnkle.z + (fr.dz || 0) + (fr.swingZ ? Math.sin(d.t * (fr.hz || 5) + (f.s > 0 ? 0 : Math.PI)) * fr.swingZ : 0);
      const w = this.bodyToWorld(b, lx, lz); x = w[0]; z = w[1]; y = b.y + this.restAnkle.y + (fr.dy || 0); pitch = fr.pitch || 0; yaw = b.yaw; f.x = x; f.z = z; f.yaw = yaw; f.gy = b.y;
      const pf = f.fl; f.flp = pf ? { ...pf } : null; f.fl = { x: lx, y: this.restAnkle.y + (fr.dy || 0), z: lz, pitch }; if (!f.flp) f.flp = { ...f.fl };
    } else {
      x = f.x; z = f.z; yaw = f.yaw; let lift = 0;
      if (f.mode === 'swing') {
        // 抬腳曲線：最高點落在擺動期的 peak 處（>0.5 ＝腳往前伸出肚子外緣時才抬到最高，側面看得到腳掌抬起）
        const t = f.sw, s = t.s ?? 0, pk = t.peak ?? 0.5, sw = s < pk ? 0.5 * s / pk : 0.5 + 0.5 * (s - pk) / (1 - pk); lift = t.lift * Math.sin(Math.PI * clamp(sw, 0, 1)) ** 0.8;
        pitch = 0.5 * Math.max(0, 1 - 2.2 * s) ** 2 - 0.22 * Math.sin(Math.PI * clamp((s - 0.45) / 0.55, 0, 1));
      }
      y = f.gy + this.ankleH(pitch) + lift;
    }
    // 模式切換：用 0.1 秒把目標混過去，避免瞬移
    if (f.mode !== f.lastMode) { f.blend = { t: 0, dur: f.lastMode === 'free' || f.mode === 'free' ? 0.12 : 0.04, from: { x: g.x, y: g.y, z: g.z, pitch: g.pitch, yaw: g.yaw } }; f.lastMode = f.mode; }
    if (f.blend) {
      f.blend.t += dt; const k = sm(f.blend.t / f.blend.dur), o = f.blend.from;
      x = lerp(o.x, x, k); y = lerp(o.y, y, k); z = lerp(o.z, z, k); pitch = lerp(o.pitch, pitch, k); yaw = o.yaw + angDiff(o.yaw, yaw) * k;
      if (f.blend.t >= f.blend.dur) f.blend = null;
    }
    g.x = x; g.y = y; g.z = z; g.pitch = pitch; g.yaw = yaw;
  }
  /** 把每隻腳的目標（渲染用，alpha 內插）套到骨頭上。需在身體其他骨頭與 root 變換都設好、世界矩陣更新之後呼叫。 */
  apply(alpha) {
    for (const f of this.feet) {
      const g = f.goal, p = f.prev;
      let gx = lerp(p.x, g.x, alpha), gy = lerp(p.y, g.y, alpha), gz = lerp(p.z, g.z, alpha), pitch = lerp(p.pitch, g.pitch, alpha), yaw = p.yaw + angDiff(p.yaw, g.yaw) * alpha, qb = null;
      if (f.mode === 'free' && !f.blend && f.fl) {   // 空中／坐著／被抓：腳跟著「視覺上的」身體（含 root 骨的位移與翻滾），不只是物理位置
        const L = f.fl, P0 = f.flp, M = this._M.multiplyMatrices(this.ch.bones.root.matrixWorld, this.invB0);
        _a.set(lerp(P0.x, L.x, alpha), lerp(P0.y, L.y, alpha), lerp(P0.z, L.z, alpha)).applyMatrix4(M); gx = _a.x; gy = _a.y; gz = _a.z; pitch = lerp(P0.pitch, L.pitch, alpha);
        M.decompose(_b, this._Q, this._S); qb = this._Q;
      }
      this.ikFoot(f, gx, gy, gz, pitch, yaw, qb);
      // 實際網格檢查：腿＋腳掌任一頂點低於腳下的支撐面，就把踝抬高那麼多再解一次（只抬、不下壓；腳不離開鎖定的水平位置）
      const gnd = f.mode === 'free' ? this.world.supportAt(gx, gz, 0.03, gy, 0.05).h : f.gy; let extra = 0; f.pen = 0;
      for (let it = 0; it < 4; it++) {
        const ly = this.lowestLeg(f.side); if (ly >= gnd - 0.0003) break;
        extra += (gnd - ly) * 1.05; f.pen = extra; this.ikFoot(f, gx, gy + extra, gz, pitch, yaw, qb);
      }
      if (extra > 0) this.stats.penMax = Math.max(this.stats.penMax || 0, extra);
      // 實際髖（骨頭世界位置）相對名義髖（角色根的位置與朝向＋模型髖座標）的水平偏移，低通後回饋給下一步的落腳規劃
      { const leg = this.ch.bones['leg.' + f.side], rp = this.ch.root.position, ry = this.ch.root.rotation.y, cs = Math.cos(ry), sn = Math.sin(ry); _a.setFromMatrixPosition(leg.matrixWorld);
        const nx = rp.x + this.hip.x * f.s * cs + this.hip.z * sn, nz = rp.z - this.hip.x * f.s * sn + this.hip.z * cs; f.hoX = lerp(f.hoX || 0, _a.x - nx, 0.3); f.hoZ = lerp(f.hoZ || 0, _a.z - nz, 0.3); }
    }
  }
  ikFoot(f, gx, gy, gz, pitch, yaw, qb = null) {
    const ch = this.ch, leg = ch.bones['leg.' + f.side], foot = ch.bones['foot.' + f.side], R = ch.rest['leg.' + f.side];
    leg.position.copy(R.p); leg.quaternion.copy(R.q);
    leg.parent.updateWorldMatrix(true, false); leg.updateWorldMatrix(false, false);
    const hip = _a.setFromMatrixPosition(leg.matrixWorld), A = _b.set(gx, gy, gz), dv = _c.subVectors(A, hip); let dist = dv.length();
    const maxLen = this.maxStretch * this.L0; f.ratio = dist / this.L0;
    if (dist > maxLen) { dv.multiplyScalar(maxLen / dist); dist = maxLen; f.clamped = true; this.stats.clamped++; if (f.mode === 'plant') this.stats.slide = Math.max(this.stats.slide, (f.ratio * this.L0 - maxLen)); } else f.clamped = false;
    this.stats.maxRatio = Math.max(this.stats.maxRatio, dist / this.L0); this.stats.minRatio = Math.min(this.stats.minRatio, dist / this.L0);
    leg.parent.getWorldQuaternion(_q1);
    _a.copy(this.axis[f.side]).applyQuaternion(R.q).applyQuaternion(_q1);                   // 靜止的腿軸（套上父骨目前姿態）
    _q2.setFromUnitVectors(_a, dv.clone().normalize());                    // 世界座標的補轉
    _q3.copy(_q2).multiply(_q1).multiply(R.q);                              // 腿骨的新世界旋轉
    leg.quaternion.copy(_q1.invert().multiply(_q3)); leg.updateWorldMatrix(false, false);
    foot.position.copy(this.axis[f.side]).multiplyScalar(dist);
    // 腳掌：世界朝向 = 偏航 · 俯仰 · 靜止的腳掌朝向（保持水平）
    (qb ? _q4.copy(qb) : _q4.setFromAxisAngle(Y, yaw)).multiply(_q2.setFromAxisAngle(X, pitch)).multiply(this.restFootQ[f.side]);
    leg.getWorldQuaternion(_q1); foot.quaternion.copy(_q1.invert().multiply(_q4)); foot.updateWorldMatrix(false, false);
  }
  /** 目前每隻腳「踝」的世界位置（量測用：直接從骨頭矩陣讀） */
  ankleWorld(side, out = new THREE.Vector3()) { return this.ch.bones['foot.' + side].getWorldPosition(out); }
}
