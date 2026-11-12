// 走路／跑步／站立：角色在世界座標真的位移，著地的腳鎖在世界座標（記下著地點，用腿部反向運動學去搆），所以不會腳滑。
// 第三輪：照真實步態的五個關鍵姿勢重做 ——
//   腳跟著地（前腿近乎伸直、腳尖翹起）→ 承重（膝蓋微彎吸震）→ 站立中期（支撐腿伸直、骨盆最高）
//   → 蹬離（腳跟先離地、腳踝伸展、膝蓋開始彎）→ 擺動（膝蓋彎著往前擺、腳尖離地有餘裕）。
// 骨盆高度不再用固定的波形，而是「由腿長反推」：每條腿給一個伸直比例（腳踝到髖的距離÷腿長），
// 骨盆取所有腿都搆得到的最高點，所以支撐腿在站立中期自然伸直、雙腳著地時自然最低（倒單擺）。
import * as THREE from '../vendor/three.module.min.js';
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x)), lerp = (a, b, t) => a + (b - a) * t, ss = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const TAU = Math.PI * 2;
const wrap = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };
const _qH = new THREE.Quaternion(), _eH = new THREE.Euler(), _d = new THREE.Vector3();
// 伸直比例 ↔ 膝角：比例 = sin(膝角/2)。0.997≈171°、0.987≈161°、0.94≈140°
const R_FULL = 0.997, R_STAND = 0.992, R_HARD = 0.9992;

export class Loco {
  constructor(char) {
    const J = char.J; this.char = char;
    this.ankleY = J.footL.y; this.hipH = J.thighL.y; this.hipX = Math.abs(J.thighL.x - J.hips.x);
    this.legLen = char.legLen.a + char.legLen.b;
    this.toeZ = J.footL_end.z - J.footL.z; this.ballZ = this.toeZ * 0.78; this.heelZ = -0.075;   // 蹬地時的支點：腳掌球偏前（鞋子是硬的，支點太靠後鞋尖會插進地板）
    this.latStand = this.hipX + this.legLen * 0.13; this.latWalk = this.hipX + 0.02;
    this.x = 0; this.z = 0; this.yaw = 0; this.v = 0; this.phase = 0.12; this.moving = false; this.settled = true; this.acc = 0; this.w = 0; this.py = null; this.mvW = 0;
    this.feet = { L: this.mkFoot(1), R: this.mkFoot(-1) };
  }
  mkFoot(side) { const lat = this.latStand; return { side, pos: new THREE.Vector3(this.x + Math.cos(this.yaw) * side * lat, 0, this.z - Math.sin(this.yaw) * side * lat), yaw: this.yaw, swing: false, ankle: new THREE.Vector3(), pitch: 0, cur: new THREE.Vector3() }; }
  reset(x = 0, z = 0, yaw = 0) { this.x = x; this.z = z; this.yaw = yaw; this.v = 0; this.phase = 0.12; this.moving = false; this.settled = true; this.w = 0; this.py = null; this.mvW = 0; this.acc = 0; this.feet = { L: this.mkFoot(1), R: this.mkFoot(-1) }; }
  fwd(yaw = this.yaw) { return new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw)); }
  left(yaw = this.yaw) { return new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)); }
  // 步幅依腿長取比例：走路一個週期約 1.2 倍髖高（腿短頭大的角色，步頻偏快）、跑步約 2 倍
  gait() { const v = this.v, run = ss((v - 1.1) / 0.6);
    const stride = lerp(clamp(0.3 + 0.575 * v, 0.3, 0.88), 0.5 + 0.42 * v, run);  // 一個完整週期（左右各一步）前進的距離
    return { run, duty: lerp(0.62, 0.32, run), stride, T: clamp(stride / Math.max(v, 1e-3), 0.5, 1.05), k: clamp(v / 0.6), fwdFrac: lerp(0.44, 0.3, run) }; }
  // 腳掌貼地時的腳踝位置；pitch>0 腳跟離地（繞腳掌球轉）、pitch<0 腳尖翹起（繞腳跟轉）
  ankleAt(pos, yaw, pitch, out) {
    const pz = pitch >= 0 ? this.ballZ : this.heelZ, f = this.fwd(yaw);
    const y = this.ankleY * Math.cos(pitch) + pz * Math.sin(pitch), zz = this.ankleY * Math.sin(pitch) - pz * Math.cos(pitch);
    return out.copy(pos).addScaledVector(f, pz + zz).setY(y);
  }
  // 支撐期腿的伸直比例：著地近乎伸直 → 承重微彎 → 站立中期伸直 → 對側腳著地後放掉（由前腳接手）
  stanceReach(u, g) { const rel = 0.5 / g.duty;   // 對側腳跟著地的時刻
    const walk = R_FULL - 0.001 - 0.008 * g.k * Math.sin(Math.PI * clamp((u + 0.02) / 0.44)) ** 2 + 0.4 * ss((u - rel) / 0.12);
    return lerp(walk, 0.99, g.run); }
  update(dt, cmd = {}) {
    let tv = cmd.speed || 0;
    // 朝向：轉彎半徑有下限（角速度 ≤ 速度÷半徑），不會原地打轉；偏很多時先放慢再轉
    if (cmd.yaw != null && (this.v > 0.02 || tv > 0)) { const d = wrap(cmd.yaw - this.yaw), rmin = tv > 1.2 ? 0.75 : 0.42, rate = Math.min(cmd.turnRate || 2.4, Math.max(this.v / rmin, 0.7));
      const w = clamp(d * 6, -rate, rate); this.w = dt > 0 ? lerp(this.w, w, clamp(dt * 10)) : this.w; this.yaw += this.w * dt; tv *= clamp(1.25 - Math.abs(d) * 0.5, 0.5, 1); }
    else this.w = dt > 0 ? lerp(this.w, 0, clamp(dt * 10)) : this.w;
    const a = tv > this.v ? (tv > 1.2 ? 2.8 : 1.5) : 2.2, v0 = this.v; this.v += clamp(tv - this.v, -a * dt, a * dt); if (this.v < 1e-3) this.v = 0;
    this.acc = dt > 0 ? lerp(this.acc, (this.v - v0) / dt, clamp(dt * 8)) : this.acc;
    const f = this.fwd(), l = this.left(); this.x += f.x * this.v * dt; this.z += f.z * this.v * dt;
    const g = this.gait(), home = (s) => new THREE.Vector3(this.x, 0, this.z).addScaledVector(l, s * lerp(this.latStand, this.latWalk, g.k));
    if (tv === 0 && this.v < 0.25) g.T = lerp(0.6, g.T, clamp(this.v / 0.25));   // 停步收腳：小碎步快一點
    // 要不要邁步：有速度，或停下來但腳還沒收回站姿
    const off = (ft) => ft.pos.distanceTo(home(ft.side));
    const wasMoving = this.moving;
    if (this.v > 0.02 || tv > 0) this.moving = true;
    else if (!this.feet.L.swing && !this.feet.R.swing && off(this.feet.L) < 0.03 && off(this.feet.R) < 0.03) this.moving = false;
    if (this.moving && !wasMoving) this.phase = g.duty - 0.5 + 1e-4;          // 起步：右腳先離地
    this.settled = !this.moving;
    if (this.moving) this.phase = (this.phase + dt / g.T) % 1;
    this.mvW = dt > 0 ? clamp(this.mvW + (this.moving ? dt : -dt) / 0.3) : (this.moving ? 1 : 0);
    const pose = { root: {} }, k = g.k, r = g.run, mv = ss(this.mvW), ph = this.phase * TAU, legs = [], L = this.legLen, J = this.char.J;
    // 骨盆：左右重心轉移、側傾（擺動側略低）、水平旋轉（擺動側往前）、前傾
    const swayPh = ph - 0.1 * Math.PI, turnLean = clamp(this.w * this.v * 0.045, -0.09, 0.09);
    pose.root = { x: 0.022 * k * (1 - 0.6 * r) * Math.sin(swayPh) * mv,
      rx: (0.03 * k + 0.13 * r + clamp(this.acc * 0.04, -0.03, 0.09)) * mv, ry: -(0.09 * k + 0.07 * r) * Math.cos(ph) * mv, rz: (0.04 * k + 0.02 * r) * Math.sin(swayPh) * mv - turnLean };
    _qH.setFromEuler(_eH.set(pose.root.rx, pose.root.ry, pose.root.rz, 'YXZ'));
    const cy = Math.cos(this.yaw), sy = Math.sin(this.yaw), toLoc = (a) => { const rx = a.x - this.x, rz = a.z - this.z; return [rx * cy - rz * sy, a.y, rx * sy + rz * cy]; };
    const hor2 = (lg, loc) => (loc[0] - lg.hip[0]) ** 2 + (loc[2] - lg.hip[2]) ** 2;
    const hmax = (lg, loc, rho) => loc[1] + Math.sqrt(Math.max(0, (rho * L) ** 2 - hor2(lg, loc))) - lg.hip[1];   // 這條腿伸到 rho 時骨盆能到多高
    const heel = lerp(-0.28 * k, -0.08, r), u1 = lerp(0.2, 0.15, r), rel = 0.5 / g.duty;
    for (const n of ['L', 'R']) {
      const ft = this.feet[n], p = (this.phase + (n === 'L' ? 0 : 0.5)) % 1, sw = this.moving && p >= g.duty;
      _d.copy(J['thigh' + n]).sub(J.hips).applyQuaternion(_qH);
      const lg = { n, ft, stance: !sw, hip: [J.hips.x + pose.root.x + _d.x, J.hips.y + _d.y, J.hips.z + _d.z], reach: R_STAND, solve: false }; legs.push(lg);
      if (sw && !ft.swing) { ft.from = ft.ankle.clone(); ft.fromYaw = ft.yaw; ft.fromPitch = ft.pitch; }
      if (sw) {
        const s = (p - g.duty) / (1 - g.duty), rem = (1 - s) * (1 - g.duty) * g.T;
        const land = home(ft.side).addScaledVector(f, this.v * rem + this.v * g.T * g.duty * g.fwdFrac);
        ft.cur.copy(land); ft.yaw = ft.fromYaw + wrap(this.yaw - ft.fromYaw) * ss(s);
        const tgt = this.ankleAt(land, this.yaw, heel, new THREE.Vector3());
        // 擺動：腳踝被小腿帶起（跑步時腳跟踢高）、過了支撐腿往前伸、落地前腳尖翹起
        ft.ankle.lerpVectors(ft.from, tgt, ss(s)); ft.ankle.y = lerp(ft.from.y, tgt.y, ss(s / lerp(0.62, 1, r)));
        ft.ankle.y += lerp(0.05, 0.022, k) * (1 - r) * Math.sin(Math.PI * s) + r * (0.2 * Math.sin(Math.PI * Math.pow(s, 0.7)) + 0.12 * Math.sin(Math.PI * clamp((s - 0.55) / 0.45)) ** 2);   // 跑步：腳跟踢高、再抬膝往前帶
        ft.pitch = lerp(ft.fromPitch, heel, ss((s - 0.3 * r) / lerp(0.8, 0.65, r)));
        // 鞋底（腳尖支點、腳跟）離地餘裕
        const c = Math.cos(ft.pitch), sn = Math.sin(ft.pitch), low = Math.min(-this.ankleY * c - this.ballZ * sn, -this.ankleY * c - this.heelZ * sn);
        ft.ankle.y = Math.max(ft.ankle.y, 0.014 * Math.sin(Math.PI * s) - low);
        lg.reach = R_FULL; lg.loc = toLoc(ft.ankle);
      } else {
        if (ft.swing) ft.pos.copy(ft.cur);                                      // 著地：記下著地點，之後整個支撐期都不動
        if (this.moving) { const u = p / g.duty; lg.u = u; lg.reach = lerp(R_STAND, this.stanceReach(u, g), mv);
          if (u < u1) ft.pitch = heel * (1 - ss(u / u1));                        // 腳跟著地 → 腳掌放平
          else { lg.solve = true;                                                // 之後腳跟要抬多少由腿長決定；這裡先給「最多能抬多少」來算骨盆
            lg.avail = lerp(0.75 * k * ss((u - 0.42) / 0.5), 0.95 * ss((u - 0.3) / 0.6), r);
            lg.cap = lerp(0.9975 - 0.07 * k * Math.pow(clamp((u - rel) / (1 - rel)), 1.5), 0.985, r); }
        } else ft.pitch = 0;
        lg.loc = toLoc(this.ankleAt(ft.pos, ft.yaw, lg.solve ? lg.avail : ft.pitch, ft.ankle));
      }
      ft.swing = sw;
    }
    // 骨盆高度：每條腿「伸直比例」允許的最高點、加上走路的頂（站立中期的高度）或跑步的騰空拋物線，取平滑最小值
    const flightMid = (g.duty + 0.5) / 2, yRun = -0.016 + 0.034 * Math.cos(2 * TAU * (this.phase - flightMid)), yTop = this.ankleY + R_FULL * L - this.hipH + 0.003 - 0.021 * k * k * (1 - Math.cos(2 * TAU * (this.phase - g.duty / 2 - 0.015))) / 2;   // 倒單擺：單腳支撐中段最高、雙腳著地最低
    const hs = legs.map((lg) => hmax(lg, lg.loc, lg.reach)); hs.push(lerp(yTop, yRun, r * mv));
    const sk = 0.004, m0 = Math.min(...hs), y = m0 - sk * Math.log(hs.reduce((acc, h) => acc + Math.exp(-(h - m0) / sk), 0));
    if (this.py == null) this.py = y; else if (dt > 0) this.py += (y - this.py) * (1 - Math.exp(-dt / 0.02));
    for (const lg of legs) this.py = Math.min(this.py, hmax(lg, lg.loc, R_HARD));   // 每隻腳都一定搆得到目標（著地的腳才不會被拖走）
    pose.root.y = this.py;
    for (const lg of legs) { const ft = lg.ft;
      if (lg.solve) { // 腳跟抬起的角度：剛好讓腿維持在該有的伸直比例（站立末期近乎伸直、蹬離前膝蓋開始彎）
        const dist = (pt) => { const loc = toLoc(this.ankleAt(ft.pos, ft.yaw, pt, ft.ankle)); return Math.sqrt(hor2(lg, loc) + (lg.hip[1] + this.py - loc[1]) ** 2) - lg.cap * L; };
        const pmin = Math.min(lg.avail, lerp(0.36 * k * Math.pow(clamp((lg.u - rel) / (1 - rel)), 1.3), 0.3 * Math.pow(clamp((lg.u - 0.55) / 0.45), 1.3), r)); let lo = pmin, hi = lg.avail;
        if (dist(lo) <= 0) hi = lo; else if (dist(hi) > 0) lo = hi; else for (let i = 0; i < 16; i++) { const m = (lo + hi) / 2; if (dist(m) > 0) lo = m; else hi = m; }
        ft.pitch = hi; lg.loc = toLoc(this.ankleAt(ft.pos, ft.yaw, ft.pitch, ft.ankle)); }
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(ft.pitch, wrap(ft.yaw - this.yaw), 0, 'YXZ'));
      pose['ik' + lg.n] = { ankle: lg.loc, q, pole: [ft.side * 0.16, 0, 1] };
    }
    // 軀幹：略微前傾（走路約 3～5 度、跑步約 15 度），胸與骨盆反向旋轉，頭保持水平看前方
    const yawC = (0.09 * k + 0.07 * r) * Math.cos(ph) * mv, lean = (0.018 * k + 0.07 * r) * mv;
    pose.spine = [lean, 0.5 * yawC, -0.6 * pose.root.rz]; pose.chest = [lean, 1.0 * yawC, -0.3 * pose.root.rz];
    pose.neck = [-(0.035 * k + 0.1 * r) * mv, -0.25 * yawC, 0]; pose.head = [-(0.035 * k + 0.1 * r) * mv, -0.25 * yawC, -0.1 * pose.root.rz];
    // 手臂：從肩膀擺、與對側腿反向；前擺時手肘多彎一點；跑步手肘約直角、握拳
    for (const [n, s] of [['L', 1], ['R', -1]]) {
      const sw = -s * Math.cos(ph - 0.15), af = 0.44 * k + 0.2 * r, ab = 0.42 * k + 0.45 * r;
      const th = ((af - ab) / 2 + (af + ab) / 2 * sw) * mv, el = 0.2 + (0.1 + 0.24 * Math.max(0, sw)) * k * (1 - r) * mv + (1.3 + 0.25 * sw) * r * mv;
      pose['arm' + n] = { dir: [s * (0.24 - 0.05 * k * mv * Math.max(0, sw) - 0.06 * r), -Math.cos(th), Math.sin(th)] };
      pose['fore' + n] = { dir: [s * (0.16 - 0.1 * k * mv * Math.max(0, sw) - 0.14 * r), -Math.cos(th + el), Math.sin(th + el)], twist: s * lerp(1.1, 0.9, r) };
      pose['fingers' + n] = 0.3 + 0.6 * r * mv;
    }
    this.g = g; return pose;
  }
}
