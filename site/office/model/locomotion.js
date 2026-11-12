// 走路／跑步／站立：角色在世界座標真的位移，著地的腳鎖在世界座標（記下著地點，用腿部反向運動學去搆），
// 所以不會腳滑。步頻由速度決定（速度＝步幅×步頻），起步、停步有加減速，轉彎時朝向跟著轉。
import * as THREE from '../vendor/three.module.min.js';
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)), lerp = (a, b, t) => a + (b - a) * t, ss = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const TAU = Math.PI * 2;
const wrap = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };

export class Loco {
  constructor(char) {
    const J = char.J; this.char = char;
    this.ankleY = J.footL.y; this.hipH = J.thighL.y; this.hipX = Math.abs(J.thighL.x - J.hips.x);
    this.legLen = char.legLen.a + char.legLen.b;
    this.ballZ = (J.footL_end.z - J.footL.z) * 0.62; this.heelZ = -0.075;
    this.latStand = this.hipX + this.legLen * 0.13; this.latWalk = this.hipX + 0.035;
    this.x = 0; this.z = 0; this.yaw = 0; this.v = 0; this.phase = 0.12; this.moving = false; this.settled = true; this.acc = 0;
    this.feet = { L: this.mkFoot(1), R: this.mkFoot(-1) };
  }
  mkFoot(side) { const lat = this.latStand; return { side, pos: new THREE.Vector3(this.x + Math.cos(this.yaw) * side * lat, 0, this.z - Math.sin(this.yaw) * side * lat), yaw: this.yaw, swing: false, ankle: new THREE.Vector3(), pitch: 0, cur: new THREE.Vector3() }; }
  reset(x = 0, z = 0, yaw = 0) { this.x = x; this.z = z; this.yaw = yaw; this.v = 0; this.phase = 0.12; this.moving = false; this.settled = true; this.feet = { L: this.mkFoot(1), R: this.mkFoot(-1) }; }
  fwd(yaw = this.yaw) { return new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw)); }
  left(yaw = this.yaw) { return new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)); }
  gait() { const v = this.v, run = ss((v - 1.05) / 0.45);
    const stride = lerp(0.26 + 0.4 * v, 0.5 + 0.38 * v, run);                 // 一個完整週期（左右各一步）前進的距離
    return { run, duty: lerp(0.62, 0.32, run), stride, T: clamp(stride / Math.max(v, 1e-3), 0.45, 0.95), k: clamp(v / 0.5) }; }
  // 腳掌貼地時的腳踝位置；pitch>0 腳跟離地（繞腳掌球轉）、pitch<0 腳尖翹起（繞腳跟轉）
  ankleAt(pos, yaw, pitch, out) {
    const pz = pitch >= 0 ? this.ballZ : this.heelZ, f = this.fwd(yaw);
    // 以著地點為原點：腳踝 = 繞 x 軸轉 pitch 的 (0, ankleY, -pz)
    const y = this.ankleY * Math.cos(pitch) + pz * Math.sin(pitch), zz = this.ankleY * Math.sin(pitch) - pz * Math.cos(pitch);
    return out.copy(pos).addScaledVector(f, pz + zz).setY(y);
  }
  update(dt, cmd = {}) {
    const tv = cmd.speed || 0, g0 = this.gait();
    // 朝向與速度
    if (cmd.yaw != null && (this.v > 0.02 || tv > 0)) { const d = wrap(cmd.yaw - this.yaw), rate = (cmd.turnRate || 2.4) * (0.35 + 0.65 * clamp(this.v / 0.4)); this.yaw += clamp(d, -rate * dt, rate * dt); }
    const a = tv > this.v ? (tv > 1.2 ? 2.6 : 1.3) : 2.0, v0 = this.v; this.v += clamp(tv - this.v, -a * dt, a * dt); if (this.v < 1e-3) this.v = 0;
    this.acc = dt > 0 ? lerp(this.acc, (this.v - v0) / dt, clamp(dt * 8)) : this.acc;
    const f = this.fwd(), l = this.left(); this.x += f.x * this.v * dt; this.z += f.z * this.v * dt;
    const g = this.gait(), home = (s) => new THREE.Vector3(this.x, 0, this.z).addScaledVector(l, s * lerp(this.latStand, this.latWalk, g.k));
    // 要不要邁步：有速度，或停下來但腳還沒收回站姿
    const off = (ft) => ft.pos.distanceTo(home(ft.side));
    const wasMoving = this.moving;
    if (this.v > 0.02 || tv > 0) this.moving = true;
    else if (!this.feet.L.swing && !this.feet.R.swing && off(this.feet.L) < 0.03 && off(this.feet.R) < 0.03) this.moving = false;
    if (this.moving && !wasMoving) this.phase = g.duty - 0.5 + 1e-4;          // 起步：右腳先離地
    this.settled = !this.moving;
    if (this.moving) this.phase = (this.phase + dt / g.T) % 1;
    const pose = { root: {} };
    for (const n of ['L', 'R']) {
      const ft = this.feet[n], p = (this.phase + (n === 'L' ? 0 : 0.5)) % 1, sw = this.moving && p >= g.duty;
      const toe = 0.75 * g.k + 0.25 * g.run, heel = -0.32 * g.k;
      if (sw && !ft.swing) { ft.from = ft.ankle.clone(); ft.fromYaw = ft.yaw; ft.fromPitch = ft.pitch; }
      if (sw) {
        const s = (p - g.duty) / (1 - g.duty), rem = (1 - s) * (1 - g.duty) * g.T;
        const land = home(ft.side).addScaledVector(f, this.v * rem + this.v * g.T * g.duty * 0.5);
        ft.cur.copy(land); ft.yaw = ft.fromYaw + wrap(this.yaw - ft.fromYaw) * ss(s);
        const tgt = this.ankleAt(land, this.yaw, heel, new THREE.Vector3());
        const e = ss(s), lift = (0.05 + 0.05 * g.k + 0.13 * g.run) * Math.sin(Math.PI * Math.pow(s, 0.85));
        ft.ankle.lerpVectors(ft.from, tgt, e); ft.ankle.y += lift + 0.1 * g.run * (s < 0.25 ? Math.sin(Math.PI * s / 0.25) ** 2 : s > 0.75 ? Math.sin(Math.PI * (1 - s) / 0.25) ** 2 : 0);
        ft.pitch = lerp(ft.fromPitch, heel, ss(s * 1.15)) + (0.25 * g.k + 0.5 * g.run) * Math.sin(Math.PI * s) * (1 - s);
      } else {
        if (ft.swing) ft.pos.copy(ft.cur);                                      // 著地：記下著地點，之後整個支撐期都不動
        const u = this.moving ? p / g.duty : 0.4;
        ft.pitch = u < 0.14 ? heel * (1 - u / 0.14) : u > 0.58 ? toe * Math.pow((u - 0.58) / 0.42, 1.6) : 0;
        if (!this.moving) ft.pitch = 0;
        this.ankleAt(ft.pos, ft.yaw, ft.pitch, ft.ankle);
      }
      ft.swing = sw;
      // 轉成角色座標
      const rel = ft.ankle.clone().sub(new THREE.Vector3(this.x, 0, this.z)), c = Math.cos(-this.yaw), s_ = Math.sin(-this.yaw);
      const loc = [rel.x * c + rel.z * s_, rel.y, -rel.x * s_ + rel.z * c];
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(ft.pitch, wrap(ft.yaw - this.yaw), 0, 'YXZ'));
      pose['ik' + n] = { ankle: loc, q, pole: [ft.side * 0.16, 0, 1] };
    }
    // 骨盆：走路時雙腳著地瞬間最低、單腳支撐中段最高；跑步相反（支撐中段最低、騰空最高）
    const ph = this.phase * TAU, k = g.k, r = g.run, mv = this.moving ? 1 : 0;
    const yWalk = -0.004 - 0.014 * k - 0.012 * k * Math.cos(2 * ph);
    const yRun = -0.045 - 0.05 * Math.cos(2 * (ph - g.duty * Math.PI));
    const swayPh = ph - 0.6 * Math.PI + Math.PI / 2;
    pose.root = { y: lerp(yWalk, yRun, r) * mv, x: 0.024 * k * (1 - 0.6 * r) * Math.sin(swayPh) * mv,
      rx: (0.035 * k + 0.16 * r + clamp(this.acc * 0.05, -0.08, 0.1)) * mv, ry: -(0.11 * k + 0.08 * r) * Math.cos(ph) * mv, rz: (0.045 * k + 0.02 * r) * Math.sin(swayPh) * mv };
    // 腿搆不到著地點時（加速、急轉彎）把骨盆壓低，腳就不會被拖離著地點
    for (const n of ['L', 'R']) { const ft = this.feet[n]; if (ft.swing) continue;
      const hx = this.x + l.x * ft.side * this.hipX + l.x * pose.root.x, hz = this.z + l.z * ft.side * this.hipX + l.z * pose.root.x, hor = Math.hypot(ft.ankle.x - hx, ft.ankle.z - hz), L = this.legLen * 0.972;
      if (hor < L) { const ymax = ft.ankle.y + Math.sqrt(L * L - hor * hor) - this.hipH; if (pose.root.y > ymax) pose.root.y = ymax; } }
    const yawC = (0.11 * k + 0.08 * r) * Math.cos(ph) * mv;
    pose.spine = [0.02 * k + 0.05 * r, 0.5 * yawC, -0.6 * pose.root.rz]; pose.chest = [0.02 * k + 0.05 * r, 1.0 * yawC, -0.3 * pose.root.rz];
    pose.neck = [-0.03 * k - 0.1 * r, -0.25 * yawC, 0]; pose.head = [-0.03 * k - 0.1 * r, -0.25 * yawC, -0.1 * pose.root.rz];
    // 手臂：與對側腿反向擺動，手肘微彎（跑步彎到接近直角）
    for (const [n, s] of [['L', 1], ['R', -1]]) {
      const th = -s * (0.36 * k + 0.5 * r) * Math.cos(ph - 0.25) * mv - 0.1 * r, el = (0.16 + 0.06 * k + 1.15 * r) + 0.22 * k * Math.max(0, Math.sin(th * 2));
      pose['arm' + n] = { dir: [s * (0.24 - 0.04 * r), -Math.cos(th), Math.sin(th)] }; pose['fore' + n] = { dir: [s * (0.16 - 0.14 * r), -Math.cos(th + el), Math.sin(th + el)], twist: s * lerp(1.1, 0.9, r) };
      pose['fingers' + n] = 0.25 + 0.55 * r;
    }
    this.g = g; return pose;
  }
}
