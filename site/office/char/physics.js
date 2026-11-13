// 角色物理層（第三階段）：固定步進、碰撞形狀、地面與障礙物接地偵測、跳躍／落地事件。
// 與畫面更新率完全無關：呼叫端把「畫面 dt」丟進 Stepper，它切成固定的 1/120 秒，每個固定步才推進物理。
// 座標：世界公尺，Y 向上；偏航角 yaw 為繞 Y 軸（模型 +Z 朝前 → 世界 (sin yaw, cos yaw)）。
// 卡通變形（壓扁、拉長）只作用在視覺層，這裡的碰撞形狀不變。

export const FIXED_DT = 1 / 120;
export const GRAVITY = 16;            // 0.72 m 高的小個子用較大重力維持手感（規劃第三節）

/** 固定時間步進累加器：每幀最多 maxSteps 步，超過就丟棄多餘時間並計數（QA 顯示） */
export class Stepper {
  constructor(dt = FIXED_DT, maxSteps = 8) { this.dt = dt; this.maxSteps = maxSteps; this.acc = 0; this.dropped = 0; this.steps = 0; }
  /** 回傳這一幀內插用的 alpha（0..1）。fn 每個固定步呼叫一次。 */
  advance(frameDt, fn) {
    this.acc += Math.min(frameDt, this.dt * this.maxSteps * 4);
    let n = 0;
    while (this.acc >= this.dt - 1e-9) {
      if (n >= this.maxSteps) { this.dropped += Math.floor(this.acc / this.dt); this.acc = 0; break; }
      fn(this.dt); this.acc -= this.dt; n++; this.steps++;
    }
    if (this.acc < 0) this.acc = 0;
    return Math.min(1, this.acc / this.dt);
  }
}

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

/** 世界：地面（y=0）、四面邊界、軸對齊方塊（箱子、凳子）。 */
export class PhysWorld {
  constructor(bounds = { minX: -2.6, maxX: 2.6, minZ: -2.6, maxZ: 2.6 }) { this.bounds = bounds; this.boxes = []; }
  /** 方塊：中心 (cx,cz)、半寬 hx,hz、底 y0、頂 y1。seat＝可坐（face＝坐著時朝向的偏航角） */
  addBox(b) { const o = { y0: 0, ...b }; this.boxes.push(o); return o; }
  box(id) { return this.boxes.find(b => b.id === id); }
  /** 圓（x,z,r）下方的支撐高度：所有「頂面不高過 yRef+stepH」且與圓重疊的方塊頂面中最高者；否則地面 0。 */
  supportAt(x, z, r, yRef, stepH) {
    let h = 0, id = null;
    for (const b of this.boxes) {
      if (b.y1 > yRef + stepH + 1e-6 || b.y1 <= h) continue;
      const dx = Math.max(Math.abs(x - b.cx) - b.hx, 0), dz = Math.max(Math.abs(z - b.cz) - b.hz, 0);
      if (dx * dx + dz * dz < r * r) { h = b.y1; id = b.id; }
    }
    return { h, id };
  }
  /** 水平方向到最近障礙（方塊或邊界）的間隙（已扣掉半徑 R，≥0）：卡通壓扁橫向膨脹的上限 */
  clearance(x, z, R, y = 0, H = 0.77) {
    const bd = this.bounds; let c = Math.min(x - bd.minX, bd.maxX - x, z - bd.minZ, bd.maxZ - z) - R;
    for (const b of this.boxes) {
      if (b.y1 <= y + 0.05 || b.y0 >= y + H) continue;
      const dx = Math.max(Math.abs(x - b.cx) - b.hx, 0), dz = Math.max(Math.abs(z - b.cz) - b.hz, 0);
      c = Math.min(c, Math.hypot(dx, dz) - R);
    }
    return Math.max(0, c);
  }
}

/** 物理本體：垂直圓柱（半徑 R、高 H，量自模型實際包圍）＋較小的支撐圓（站在方塊邊緣的腳印）。 */
export class PhysBody {
  constructor(world, shape) {
    this.world = world; this.shape = { R: 0.39, H: 0.77, supportR: 0.16, stepH: 0.05, ...shape };
    this.x = 0; this.y = 0; this.z = 0; this.vx = 0; this.vy = 0; this.vz = 0; this.yaw = 0; this.wy = 0;
    this.grounded = true; this.groundId = null; this.supportY = 0;
    this.ignoreH = new Set();      // 水平碰撞暫時忽略的方塊（坐下／起身的跳躍用）
    this.held = false; this.restitution = 0; this.bounces = 0; this.airT = 0; this.events = [];
    this.accel = 7; this.decel = 9; this.airCtl = 0.35; this.stats = { maxPush: 0 };
  }
  place(x, z, yaw = this.yaw) {
    this.x = x; this.z = z; this.yaw = yaw; this.vx = this.vz = this.vy = 0;
    const s = this.world.supportAt(x, z, this.shape.supportR, 10, this.shape.stepH); this.y = s.h; this.supportY = s.h; this.groundId = s.id; this.grounded = true;
  }
  get speed() { return Math.hypot(this.vx, this.vz); }
  jump(vy, vx = this.vx, vz = this.vz) { this.vy = vy; this.vx = vx; this.vz = vz; this.grounded = false; this.groundId = null; this.airT = 0; this.events.push({ type: 'leave', vy }); }
  launch(vx, vy, vz) { this.vx = vx; this.vy = vy; this.vz = vz; this.grounded = false; this.groundId = null; this.airT = 0; this.bounces = 0; this.events.push({ type: 'leave', vy }); }
  /** wish：想要的水平速度 {vx,vz}；null＝照慣性 */
  step(dt, wish) {
    const s = this.shape;
    if (this.held) { this.vx = this.vy = this.vz = 0; return; }
    // 水平：往想要的速度逼近（加速度有限＝慣性）；空中控制力較弱
    if (wish) {
      const dx = wish.vx - this.vx, dz = wish.vz - this.vz, dl = Math.hypot(dx, dz);
      if (dl > 1e-6) {
        const a = (Math.hypot(wish.vx, wish.vz) > 1e-4 ? (wish.accel || this.accel) : (wish.decel || this.decel)) * (this.grounded ? 1 : this.airCtl);
        const k = Math.min(1, a * dt / dl); this.vx += dx * k; this.vz += dz * k;
      }
    } else if (this.grounded) { /* 無指令且著地：摩擦 */ const sp = this.speed; if (sp > 1e-6) { const k = Math.max(0, 1 - this.decel * dt / sp); this.vx *= k; this.vz *= k; } }
    const prevY = this.y;
    this.x += this.vx * dt; this.z += this.vz * dt;
    this.collideH();
    // 垂直
    if (!this.grounded) { this.vy -= GRAVITY * dt; this.y += this.vy * dt; this.airT += dt; }
    const sup = this.world.supportAt(this.x, this.z, s.supportR, prevY, s.stepH);
    this.supportY = sup.h;
    if (!this.grounded) {
      if (this.vy <= 0 && this.y <= sup.h) {
        const imp = -this.vy; this.y = sup.h; this.groundId = sup.id;
        if (this.restitution > 0 && imp > 0.9 && this.bounces < 6) { this.vy = imp * this.restitution; this.bounces++; this.vx *= 0.8; this.vz *= 0.8; this.events.push({ type: 'bounce', imp }); }
        else { this.vy = 0; this.grounded = true; this.bounces = 0; this.events.push({ type: 'land', imp, airT: this.airT }); }
      }
    } else if (sup.h < this.y - 1e-4) { this.grounded = false; this.groundId = null; this.vy = 0; this.airT = 0; this.events.push({ type: 'leave', vy: 0, fall: true }); }
    else { this.y = sup.h; this.groundId = sup.id; }
    if (!this.grounded && this.y < prevY) this.collideH();   // 垂直下落跨過方塊的「踏高」門檻後，同一步立刻把水平嵌入推出去（否則要到下一步才推，端點狀態會嵌在方塊裡）
    this.yaw += this.wy * dt;
  }
  collideH() {
    const s = this.shape, w = this.world, bd = w.bounds, R = s.R;
    for (const b of w.boxes) {
      if (this.ignoreH.has(b.id)) continue;
      if (this.y + s.H <= b.y0 + 1e-3 || this.y >= b.y1 - s.stepH) continue;
      const qx = clamp(this.x, b.cx - b.hx, b.cx + b.hx), qz = clamp(this.z, b.cz - b.hz, b.cz + b.hz);
      let dx = this.x - qx, dz = this.z - qz, d = Math.hypot(dx, dz);
      if (d >= R) continue;
      if (d < 1e-6) {   // 圓心在方塊內：往最近的邊推出
        const ex = b.hx - Math.abs(this.x - b.cx), ez = b.hz - Math.abs(this.z - b.cz);
        if (ex < ez) { dx = Math.sign(this.x - b.cx) || 1; dz = 0; d = 0; this.x = b.cx + dx * (b.hx + R); }
        else { dz = Math.sign(this.z - b.cz) || 1; dx = 0; d = 0; this.z = b.cz + dz * (b.hz + R); }
      } else { const k = R / d; this.stats.maxPush = Math.max(this.stats.maxPush, R - d); this.x = qx + dx * k; this.z = qz + dz * k; dx /= d; dz /= d; }
      const vn = this.vx * dx + this.vz * dz; if (vn < 0) { this.vx -= vn * dx; this.vz -= vn * dz; }
    }
    if (this.x < bd.minX + R) { this.x = bd.minX + R; if (this.vx < 0) this.vx = this.restitution > 0 ? -this.vx * 0.5 : 0; }
    if (this.x > bd.maxX - R) { this.x = bd.maxX - R; if (this.vx > 0) this.vx = this.restitution > 0 ? -this.vx * 0.5 : 0; }
    if (this.z < bd.minZ + R) { this.z = bd.minZ + R; if (this.vz < 0) this.vz = this.restitution > 0 ? -this.vz * 0.5 : 0; }
    if (this.z > bd.maxZ - R) { this.z = bd.maxZ - R; if (this.vz > 0) this.vz = this.restitution > 0 ? -this.vz * 0.5 : 0; }
  }
  drain() { const e = this.events; this.events = []; return e; }
}

/** 由模型實際網格量出碰撞形狀（靜止姿勢、排除手／耳／尾／腿腳）：R＝身體水平半徑、H＝頭頂高 */
export function measureShape(ch) {
  const b = ch.body, g = b.geometry, p = g.attributes.position, si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
  ch.resetPose(); ch.model.updateMatrixWorld(true); b.skeleton.update();
  const names = b.skeleton.bones.map(x => x.name), T = ch.root.position.clone();
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9, top = -1e9, bot = 1e9;
  const skip = /hand|ear|tail|arm/;
  for (let i = 0; i < p.count; i++) {
    let bi = 0, bw = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; bi = si.getComponent(i, k); } }
    if (skip.test(names[bi])) continue;
    T.set(p.getX(i), p.getY(i), p.getZ(i)); b.applyBoneTransform(i, T);
    x0 = Math.min(x0, T.x); x1 = Math.max(x1, T.x); z0 = Math.min(z0, T.z); z1 = Math.max(z1, T.z); top = Math.max(top, T.y); bot = Math.min(bot, T.y);
  }
  return { R: ((x1 - x0) + (z1 - z0)) / 4, H: top, bottom: bot, halfW: (x1 - x0) / 2, halfD: (z1 - z0) / 2, supportR: 0.16, stepH: 0.05 };
}
