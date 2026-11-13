// 角色動畫控制器與狀態機（第三階段，糰糰起）。
//  · 固定時間步進（1/120 秒）：物理、步態、狀態機、姿勢產生都在固定步裡；畫面只做內插＋套用到骨頭。
//  · 通道所有權：每個骨頭／形態鍵通道，同一幀只有一個「基底寫入者」（目前狀態的姿勢提供者）；其餘（呼吸、待機小動作、次級彈簧、
//    擠壓彈簧、視線、覆蓋層、摸頭）全是明確的疊加層。PoseBus 會記錄衝突（測試要求 0 筆）。腿與腳只由腳 IK 寫。
//  · 交叉淡化：姿勢提供者一換，就從「上一幀實際輸出的姿勢」淡到新的（FADE 表），所以不會跳幀；任何狀態都能被打斷回 Idle。
//  · 卡通變形（擠壓／拉長／摸頭下壓）只作用在形態鍵（視覺），不改碰撞形狀；橫向膨脹受「到障礙物的間隙」限制。
import * as THREE from 'three';
import { Stepper, FIXED_DT, GRAVITY, PhysBody, measureShape } from './physics.js';
import { Feet } from './gait.js';
import { CHANNELS, CYCLES, CLIPS, POSES, MICRO, TRANSITIONS, FADE } from './actions.js';

const N = CHANNELS.length, IDX = Object.fromEntries(CHANNELS.map((n, i) => [n, i]));
const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t, TAU = Math.PI * 2;
const angDiff = (a, b) => { let d = (b - a) % TAU; if (d > Math.PI) d -= TAU; if (d < -Math.PI) d += TAU; return d; };
const _hq = new THREE.Quaternion(), _he = new THREE.Euler(), _hv = new THREE.Vector3();
const frac = (x) => x - Math.floor(x);
const EASE = { lin: (t) => t, in2: (t) => t * t, out2: (t) => 1 - (1 - t) * (1 - t), io: (t) => t * t * (3 - 2 * t), in3: (t) => t * t * t };
const BONES = ['root', 'pelvis', 'spine', 'head', 'tail', 'tail.tip', 'ear.L', 'ear.R', 'ear.tip.L', 'ear.tip.R', 'arm.L', 'arm.R', 'hand.L', 'hand.R'];
const BONE_IDX = BONES.map(b => ['rx', 'ry', 'rz'].map(a => IDX[b + '.' + a]));
const MORPHS = ['squash', 'stretch', 'land', 'plump', 'breath', 'cheek.L', 'cheek.R'];
function mulberry(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const pw = (map, x) => { if (x <= map[0][0]) return map[0][1]; for (let i = 1; i < map.length; i++) if (x <= map[i][0]) { const a = map[i - 1], b = map[i]; return lerp(a[1], b[1], (x - a[0]) / (b[0] - a[0])); } return map[map.length - 1][1]; };

export async function loadProfile(url) { return (await fetch(url)).json(); }

/** 姿勢匯流排：記錄每個通道這一幀被誰「設定」。同一通道被兩個不同來源設定＝衝突（測試要 0 筆）。 */
class PoseBus {
  constructor() { this.a = new Float32Array(N); this.owner = new Array(N).fill(null); this.conflicts = []; this.addWho = new Array(N).fill(null).map(() => new Set()); this.frames = 0; }
  begin() { this.a.fill(0); this.owner.fill(null); for (const s of this.addWho) s.clear(); this.frames++; }
  set(name, v, who) { const i = IDX[name]; if (i === undefined) throw new Error('未知通道 ' + name); if (this.owner[i] && this.owner[i] !== who) this.conflicts.push({ ch: name, a: this.owner[i], b: who, frame: this.frames }); this.owner[i] = who; this.a[i] = v; }
  add(name, v, who) { const i = IDX[name]; if (i === undefined) throw new Error('未知通道 ' + name); this.addWho[i].add(who); this.a[i] += v; }
}

/** 一次型動作播放器（五段）：段與段的起點永遠是「目前輸出」，所以不可能跳幀。 */
class ClipPlayer {
  constructor(segs, from) {
    this.segs = segs.map(s => { const to = new Float32Array(N); for (const [k, v] of Object.entries(s.to || {})) { if (IDX[k] === undefined) throw new Error('clip 未知通道 ' + k); to[IDX[k]] = v; } return { ...s, vec: to }; });
    this.i = 0; this.t = 0; this.from = Float32Array.from(from || new Float32Array(N)); this.out = Float32Array.from(this.from); this.done = false; this.seg = this.segs[0].n;
  }
  step(dt, until) {
    if (this.done) return;
    this.t += dt;
    for (let guard = 0; guard < 8; guard++) {
      const s = this.segs[this.i], d = s.d ?? 0;
      if (s.until) { if (!until || !until(s.until)) { this.out.set(s.vec); this.seg = s.n; return; } }
      else if (this.t < d - 1e-9) { const e = (EASE[s.e] || EASE.io)(d > 0 ? this.t / d : 1); for (let k = 0; k < N; k++) this.out[k] = lerp(this.from[k], s.vec[k], e); this.seg = s.n; return; }
      this.t -= s.until ? 0 : d; this.from.set(s.vec); this.out.set(s.vec); this.i++; if (s.until) this.t = 0;
      if (this.i >= this.segs.length) { this.done = true; this.seg = 'done'; return; }
    }
  }
}

export class CharController {
  /** ch：MochiChar；world：PhysWorld；profile：個性設定檔；opts：{ seed, life } */
  constructor(ch, world, profile, opts = {}) {
    this.ch = ch; this.world = world; this.P = profile; this.rng = mulberry(opts.seed ?? 20261113); this.life = opts.life !== false;
    this.shape = measureShape(ch); this.body = new PhysBody(world, this.shape);
    this.body.accel = profile.move.accel; this.body.decel = profile.move.decel; this.body.airCtl = profile.move.airCtl;
    this.feet = new Feet(ch, world, profile.gait);
    this.stepper = new Stepper(FIXED_DT, 8); this.bus = new PoseBus();
    this.time = 0; this.state = 'idle'; this.sub = null; this.stateT = 0; this.key = 'idle'; this.prevKey = 'idle';
    this.log = []; this.rejects = []; this.events = []; this.onEvent = null;
    this.intent = { x: 0, z: 0, mag: 0, run: false }; this.goal = null; this.faceYaw = null; this.jumpBuf = 0; this.coyote = 0; this.startT = 0; this.lastJump = -9; this.stuckT = 0;
    this.lastBase = new Float32Array(N); this.fade = { from: new Float32Array(N), t: 1, dur: 0.16 };
    this.pose = new Float32Array(N); this.prevPose = new Float32Array(N); this.poseDy = [0, 0, 0];
    this.sig = { vy: 0, speed: 0, n: 0, wy: 0, afwd: 0, alat: 0, avert: 0 }; this.vprev = { x: 0, z: 0, vy: 0 };
    this.springs = profile.secondary.map(s => ({ ...s, x: 0, v: 0, i: IDX[s.ch] }));
    this.sq = { x: 0, v: 0 }; this.pet = { on: false, want: false, t: 0, p: 0, v: 0, headHit: false }; this.overlay = null; this.clip = null; this.micro = null; this.microT = 1.5; this.cd = {};
    this.gaitAmp = 0; this.look = null; this.lookS = { y: 0, p: 0 }; this.expr = 'neutral'; this.exprOverride = null; this.held = null; this.sit = null; this.sleepT = 0; this.spin = { x: 0, z: 0, ax: 0, az: 0 }; this.pend = null; this.hang = { x: 0, vx: 0, z: 0, vz: 0 };
    this.snap = { x: 0, y: 0, z: 0, yaw: 0 }; this.snapPrev = { x: 0, y: 0, z: 0, yaw: 0 };
    this.debug = { rotCalls: 0, perBone: {}, proj: 0, projMax: 0, frames: 0 };
    this.sampleIdx = this.buildSamples();
    this.reset(opts.x ?? 0, opts.z ?? 0, opts.yaw ?? 0);
  }
  // ── 初始化／重設
  reset(x, z, yaw = 0) {
    const b = this.body; b.place(x, z, yaw); b.wy = 0; b.held = false; b.restitution = 0; b.ignoreH.clear();
    this.state = 'idle'; this.sub = null; this.stateT = 0; this.sit = null; this.held = null; this.pet.on = this.pet.want = false; this.pet.p = this.pet.v = 0; this.overlay = null; this.clip = null; this.micro = null; this.pend = null; this.hang.x = this.hang.vx = this.hang.z = this.hang.vz = 0;
    this.intent.mag = 0; this.goal = null; this.faceYaw = null; this.sq.x = this.sq.v = 0; for (const s of this.springs) s.x = s.v = 0;
    this.feet.phase = 0; this.feet.cad = 0; for (const f of this.feet.feet) { this.feet.plantAt(f, this.bodyState(), ...this.feet.homeWorld(f, this.bodyState())); f.yaw = yaw; }
    for (const f of this.feet.feet) { const g = f.goal; g.x = f.x; g.z = f.z; g.y = f.gy + this.feet.ankleH(0); g.pitch = 0; g.yaw = yaw; f.lastMode = f.mode; Object.assign(f.prev, g); }
    this.key = this.prevKey = 'idle'; this.lastBase.fill(0); this.fade.t = 1; this.pose.fill(0); this.prevPose.fill(0);
    this.snap = { x, y: b.y, z, yaw }; this.snapPrev = { ...this.snap }; this.ch.root.position.set(x, b.y, z); this.ch.root.rotation.y = yaw; this.vprev = { x: 0, z: 0, vy: 0 }; this.setExpr('neutral', true);
  }
  bodyState() { const b = this.body; return { x: b.x, y: b.y, z: b.z, yaw: b.yaw, vx: b.vx, vz: b.vz, wy: b.wy, grounded: b.grounded }; }
  // ── 狀態機
  can(to) { const row = TRANSITIONS[this.state]; return !!(row && row[to]); }
  /** 嘗試切換狀態；不存在的轉場回傳 false 並記錄（不直接賦值）。 */
  go(to, why = '') {
    if (to === this.state) return true;
    if (!this.can(to)) { this.rejects.push({ from: this.state, to, why, t: this.time }); return false; }
    this.log.push({ from: this.state, to, t: +this.time.toFixed(3), why }); if (this.log.length > 200) this.log.shift();
    this.exit(this.state); const from = this.state; this.state = to; this.stateT = 0; this.enter(to, from); return true;
  }
  exit(s) { if (s === 'held') { this.body.held = false; } if (s === 'tumble') { this.body.restitution = 0; this.spin.ax = this.spin.az = 0; } }
  enter(s, from) {
    this.clip = null;
    if (s === 'jumpPrep') this.clip = new ClipPlayer(CLIPS.jump, this.lastBase);
    else if (s === 'land') this.clip = new ClipPlayer(CLIPS.land, this.lastBase);
    else if (s === 'sleep') this.clip = new ClipPlayer(CLIPS.sleepIn, this.lastBase);
    else if (s === 'idle' && from === 'sleep') this.overlayStart('wake', true);
    if (s === 'idle' || s === 'walk' || s === 'run') this.startT = 0;
    if (s !== 'idle' && s !== 'sit') this.cancelOverlay();
    if (s === 'sleep') { this.sleepT = 0; this.cancelPet(); }
    if (s === 'air') this.micro = null;
  }
  // ── 對外指令
  /** 移動意圖：世界方向 (x,z)（不需單位化）、強度 0..1、是否跑。每幀持續呼叫；mag=0 表示放開。 */
  setMove(x, z, mag = 1, run = false) { const l = Math.hypot(x, z) || 1; this.intent.x = x / l; this.intent.z = z / l; this.intent.mag = clamp(mag, 0, 1) * (Math.hypot(x, z) > 1e-6 ? 1 : 0); this.intent.run = run; if (this.intent.mag > 0) { this.goal = null; this.cancelPet(); } }
  stop() { this.intent.mag = 0; this.goal = null; this.faceYaw = null; }
  walkTo(x, z, run = false) { if (this.state === 'sleep' || this.state === 'held' || this.state === 'tumble') return false; this.goal = { x, z, run }; this.stuckT = 0; this.cancelPet(); if (this.state === 'sit' && this.sit?.sub === 'seated') this.standUp(); return true; }
  jump() { this.jumpBuf = this.P.jump.buffer; return true; }
  faceTo(yaw) { this.faceYaw = yaw; }
  lookAt(p) { this.look = p; }
  setExpression(name) { this.exprOverride = name; }
  sitOn(id) {
    const box = this.world.box(id); if (!box || box.face === undefined) return false;
    if (!['idle', 'walk', 'run', 'land'].includes(this.state)) return false;
    if (!this.go('sit', 'sitOn')) return false; this.sit = { id, box, sub: 'approach', t: 0 }; this.cancelPet();
    const d = this.P.sit.standoff; this.sit.S = { x: box.cx + Math.sin(box.face) * d, z: box.cz + Math.cos(box.face) * d }; this.goal = { x: this.sit.S.x, z: this.sit.S.z, run: false, exact: true }; this.stuckT = 0; return true;
  }
  standUp() {
    if (this.state !== 'sit' || !this.sit) return false;
    if (this.sit.sub === 'seated') { this.sit.sub = 'risePrep'; this.sit.t = 0; this.clip = new ClipPlayer(CLIPS.riseHop, this.lastBase); this.cancelPet(); this.cancelOverlay(); return true; }
    if (['approach', 'turn'].includes(this.sit.sub)) { this.sit = null; this.goal = null; this.faceYaw = null; return this.go('idle', 'cancelSit'); }
    return false;
  }
  sleep() { if (this.state === 'sit' && this.sit?.sub === 'seated') { /* 坐著睡：沿用 sleep 姿勢但不離開凳子 */ } return this.go('sleep', 'sleep'); }
  wake() { return this.state === 'sleep' ? this.go('idle', 'wake') : false; }
  petStart() { if (!(this.state === 'idle' || (this.state === 'sit' && this.sit?.sub === 'seated'))) return false; this.pet.want = true; this.pet.t = 0; this.pet.on = false; return true; }
  petEnd() { this.pet.want = false; this.pet.on = false; }
  cancelPet() { this.pet.want = false; this.pet.on = false; }
  overlayStart(name, force = false) {
    const def = CLIPS[name]; if (!def || !def.segs) return false;
    if (!force && !(this.state === 'idle' || (this.state === 'sit' && this.sit?.sub === 'seated'))) { this.rejects.push({ from: this.state, to: 'overlay:' + name, t: this.time }); return false; }
    this.overlay = { name, def, player: new ClipPlayer(def.segs, new Float32Array(N)) }; this.cancelPet(); return true;
  }
  cancelOverlay() { this.overlay = null; }
  trigger(name) {
    switch (name) {
      case 'hit': case 'happy': case 'angry': case 'sad': {
        // 個性（profile.react）：糰糰「慢半拍」——開心／生氣／難過先歪頭看一下（好奇）再反應；受擊是反射，幾乎沒有延遲
        if (!(this.state === 'idle' || (this.state === 'sit' && this.sit?.sub === 'seated'))) return this.overlayStart(name);
        const R = this.P.react || {}, lat = name === 'hit' ? (R.hitLatency || [0.03, 0.08]) : (R.latency || [0.25, 0.45]);
        this.pend = { name, t: lerp(lat[0], lat[1], this.rng()), t0: 0 }; this.pend.t0 = this.pend.t; this.cancelPet(); return true; }
      case 'sleep': return this.sleep(); case 'wake': return this.wake();
      case 'jump': return this.jump(); case 'standUp': return this.standUp();
      default: return false;
    }
  }
  grab(x, y, z, pivot = null) { if (this.state === 'held') { this.held.t = { x, y, z }; return true; } this.cancelPet(); this.sit = null; this.goal = null; this.body.ignoreH.clear(); if (!this.go('held', 'grab')) { /* 睡覺／坐著不可直接抓：先強制喚醒 */ this.state = 'idle'; if (!this.go('held', 'grab')) return false; } this.body.held = true; this.held = { t: { x, y, z }, v: { x: 0, y: 0, z: 0 }, vp: { x: 0, y: 0, z: 0 }, last: { x: this.body.x, y: this.body.y, z: this.body.z }, pivot: pivot || { x: 0, y: 0.62, z: 0 } }; this.hang.x = this.hang.vx = this.hang.z = this.hang.vz = 0; return true; }
  release(vx = 0, vy = 0, vz = 0) {
    if (this.state !== 'held') return false; this.body.held = false;
    if (![vx, vy, vz].every(Number.isFinite)) { vx = vy = vz = 0; }   // 指標速度估計若出現非有限值，一律當作 0（不讓它進物理）
    vy = clamp(vy, -12, 9); const sp = Math.hypot(vx, vy, vz);
    if (sp > 3.2) { const k = Math.min(1, 10 / sp); this.go('tumble', 'throw'); this.body.restitution = 0.42; this.body.launch(vx * k * 0.9, vy * k * 0.9, vz * k * 0.9); this.spin.ax = (this.rng() - 0.5) * 12; this.spin.az = (this.rng() - 0.5) * 12; return true; }
    this.go('air', 'release'); this.body.launch(vx, vy, vz); return true;
  }
  throwAt(vx, vy, vz) { this.grab(this.body.x, this.body.y + 0.3, this.body.z); this.update(1 / 120); return this.release(vx, vy, vz); }
  /** 回到 Idle：任何狀態都能被打斷（空中會等落地：Air 不能直接 Idle） */
  interrupt() {
    this.pend = null; this.cancelPet(); this.cancelOverlay(); this.intent.mag = 0; this.goal = null; this.faceYaw = null; this.jumpBuf = 0; this.micro = null; this.exprOverride = null;
    if (this.sit) { if (this.sit.sub === 'seated') { this.standUp(); return 'rising'; } if (['hop', 'settle', 'risePrep', 'riseHop'].includes(this.sit.sub)) return 'busy'; this.sit = null; }
    if (this.state === 'held') { this.body.held = false; this.go('idle', 'interrupt'); this.body.launch(0, 0, 0); this.go('air', 'interrupt'); return 'fall'; }
    if (this.state === 'air' || this.state === 'tumble' || this.state === 'jumpPrep') return this.state === 'jumpPrep' ? (this.go('idle', 'interrupt'), 'idle') : 'airborne';
    this.go('idle', 'interrupt'); return this.state;
  }
  setExpr(name, snap = false) { if (this.expr === name && !snap) return; this.expr = name; const f = this.ch.face; if (f) { f.set(name); if (snap) f.snap(); } }

  // ── 主更新（每個畫面幀一次）
  update(dt) {
    const alpha = this.stepper.advance(dt, (h) => this.tick(h));
    this.render(alpha, dt);
    return alpha;
  }
  signal(dt) {
    const b = this.body, S = this.sig, k = 1 - Math.exp(-dt * 30), c = Math.cos(b.yaw), s = Math.sin(b.yaw);
    const ax = (b.vx - this.vprev.x) / dt, az = (b.vz - this.vprev.z) / dt, ay = (b.vy - this.vprev.vy) / dt;
    this.vprev.x = b.vx; this.vprev.z = b.vz; this.vprev.vy = b.vy;
    const fwd = ax * s + az * c, lat = ax * c - az * s;
    const dd = this.poseDy; const bob = (dd[0] - 2 * dd[1] + dd[2]) / (dt * dt);
    S.afwd += (clamp(fwd, -30, 30) - S.afwd) * k; S.alat += (clamp(lat, -30, 30) - S.alat) * k; S.avert += (clamp(ay + bob * 0.25, -60, 60) - S.avert) * k;
    S.vy = b.vy; S.speed = b.speed; S.wy = b.wy; S.n = clamp(b.speed / (this.P.gait[this.state === 'run' ? 'run' : 'walk'].vmax), 0, 1.3);
  }
  tick(dt) {
    this.time += dt; this.stateT += dt; const b = this.body, P = this.P, M = P.move;
    this.snapPrev = { ...this.snap };
    this.stateLogic(dt);
    // 1 意圖 → 水平速度指令與偏航角速度
    const wish = this.steer(dt);
    b.step(dt, wish);
    for (const e of b.drain()) this.onPhys(e);
    this.signal(dt);
    // 2 腳
    const dr = this.feetDrive(); this.feet.update(dt, this.bodyState(), dr);
    // 3 姿勢
    this.composePose(dt);
    this.gaitAmp += ((this.feet.cad > 0 ? 1 : 0) - this.gaitAmp) * (1 - Math.exp(-dt * 10));
    this.snap = { x: b.x, y: b.y, z: b.z, yaw: b.yaw };
    this.coyote = b.grounded ? P.jump.coyote : Math.max(0, this.coyote - dt); this.jumpBuf = Math.max(0, this.jumpBuf - dt);
  }
  // 各狀態的邏輯（轉場、計時）
  stateLogic(dt) {
    const b = this.body, P = this.P, I = this.intent, st = this.state;
    if (this.goal && ['idle', 'walk', 'run', 'land', 'sit'].includes(st)) {   // 自動走向目標
      const dx = this.goal.x - b.x, dz = this.goal.z - b.z, d = Math.hypot(dx, dz);
      const arrive = this.goal.exact ? 0.035 : 0.06;
      if (d < arrive) { this.goal = null; I.mag = 0; } else {
        I.x = dx / d; I.z = dz / d; I.mag = clamp(d / 0.3, 0.35, 1); I.run = this.goal.run;
        if (b.speed < 0.04 && this.stateT > 0.5 && ['walk', 'run'].includes(st)) { this.stuckT += dt; if (this.stuckT > 0.8) { this.goal = null; I.mag = 0; } } else this.stuckT = 0;
      }
    }
    switch (st) {
      case 'idle': {
        if (I.mag > 0.05 && b.grounded) { this.startT += dt; if (this.startT >= P.move.startDelay) this.go(I.run ? 'run' : 'walk', 'move'); } else this.startT = 0;
        if (this.jumpBuf > 0 && b.grounded && this.time - this.lastJump > P.jump.minRepeat) this.beginJump();
        if (this.life) this.lifeTick(dt);
        break; }
      case 'walk': case 'run': {
        if (!b.grounded && this.coyote <= 0) { this.go('air', 'fall'); break; }
        if (I.mag < 0.05 && b.speed < 0.07) this.go('idle', 'stop');
        else if (I.mag > 0.05 && I.run && st === 'walk') this.go('run', 'run'); else if (I.mag > 0.05 && !I.run && st === 'run') this.go('walk', 'walk');
        if (this.jumpBuf > 0 && b.grounded) this.beginJump();
        break; }
      case 'jumpPrep': {
        this.clip.step(dt);
        if (this.clip.done) {   // 起跳速度加 g·dt/2 補償半隱式歐拉，頂點高度＝設定值
 const J = P.jump, vy = Math.sqrt(2 * GRAVITY * J.height) + GRAVITY * FIXED_DT / 2; this.lastJump = this.time; this.jumpBuf = 0; b.jump(vy, b.vx, b.vz); this.go('air', 'jump'); this.stateT = 0; }
        break; }
      case 'air': {
        if (this.jumpBuf > 0 && this.coyote > 0 && b.vy < 0 && false) { /* 二段跳不做 */ }
        break; }
      case 'land': {
        this.clip.step(dt);
        if (this.jumpBuf > 0 && this.stateT > P.jump.minRepeat) { this.beginJump(); break; }
        if (I.mag > 0.05 && this.stateT > 0.1) { this.go(I.run ? 'run' : 'walk', 'move'); break; }
        if (this.clip.done) this.go('idle', 'landed');
        break; }
      case 'sit': this.sitLogic(dt); break;
      case 'sleep': this.clip.step(dt); this.sleepT += dt; if (I.mag > 0.05 || this.jumpBuf > 0) { this.go('idle', 'wake'); } break;
      case 'held': { const h = this.held, T = h.t, k = 1 - Math.exp(-dt * 14); const tx = lerp(b.x, T.x, k), ty = lerp(b.y, Math.max(T.y, b.supportY), k), tz = lerp(b.z, T.z, k);
        h.v.x = lerp(h.v.x, (tx - h.last.x) / dt, 1 - Math.exp(-dt * 12)); h.v.y = lerp(h.v.y, (ty - h.last.y) / dt, 1 - Math.exp(-dt * 12)); h.v.z = lerp(h.v.z, (tz - h.last.z) / dt, 1 - Math.exp(-dt * 12));
        h.last = { x: tx, y: ty, z: tz }; b.x = tx; b.y = ty; b.z = tz; b.grounded = false; b.vy = 0; b.collideH();
        // 懸吊擺盪：把抓點的加速度（平滑後的速度差）換成角色局部座標，驅動一個欠阻尼的擺（前後＝繞 X、左右＝繞 Z）；靜止時只剩很輕的呼吸式微晃
        { const g = this.hang, c = Math.cos(b.yaw), s = Math.sin(b.yaw), ax = (h.v.x - h.vp.x) / dt, az = (h.v.z - h.vp.z) / dt; h.vp.x = h.v.x; h.vp.z = h.v.z;
          const lat = clamp(ax * c - az * s, -40, 40), fwd = clamp(ax * s + az * c, -40, 40), W = TAU * 1.25, Z = 0.1, K = 0.045;
          const tz_ = clamp(-K * lat, -0.8, 0.8) + 0.03 * Math.sin(this.time * 2.1), tx_ = clamp(K * fwd, -0.8, 0.8) + 0.02 * Math.sin(this.time * 1.7 + 1);
          g.vz += (W * W * (tz_ - g.z) - 2 * Z * W * g.vz) * dt; g.z = clamp(g.z + g.vz * dt, -1.0, 1.0); g.vx += (W * W * (tx_ - g.x) - 2 * Z * W * g.vx) * dt; g.x = clamp(g.x + g.vx * dt, -1.0, 1.0); }
        break; }
      case 'tumble': {
        const sp = this.spin; this.rollA = (this.rollA || 0); this.pitchA = (this.pitchA || 0);
        if (!b.grounded) { this.pitchA += sp.ax * dt; this.rollA += sp.az * dt; } else { sp.ax *= 0.9; sp.az *= 0.9; this.pitchA = lerp(this.pitchA, Math.round(this.pitchA / TAU) * TAU, 1 - Math.exp(-dt * 10)); this.rollA = lerp(this.rollA, Math.round(this.rollA / TAU) * TAU, 1 - Math.exp(-dt * 10)); }
        if (b.grounded && b.speed < 0.3) { this.restT = (this.restT || 0) + dt; if (this.restT > 0.12) { this.restT = 0; this.pitchA = this.rollA = 0; this.go('recover', 'rest'); } } else this.restT = 0;
        break; }
      case 'recover': if (this.stateT > 0.8) this.go('idle', 'recovered'); else if (I.mag > 0.05 && this.stateT > 0.4) this.go('idle', 'recovered'); break;
    }
    if (this.pend) { this.pend.t -= dt; if (this.pend.t <= 0) { const n = this.pend.name; this.pend = null; this.overlayStart(n); } }
    // 摸頭
    const pt = this.pet;
    if (pt.want) { pt.t += dt; if (pt.t >= P.pet.latency) pt.on = true; }
    if (this.overlay) { const o = this.overlay; o.player.step(dt); if (o.player.done) this.overlay = null; }
    // 站著時按了跳（可能在 walk/run 之外的狀態）
    if (this.jumpBuf > 0 && st === 'sit' && this.sit?.sub === 'seated') this.standUp();
  }
  beginJump() {
    const moving = this.body.speed > 0.35;
    this.go('jumpPrep', 'jump'); this.clip = new ClipPlayer(moving ? [{ n: 'pre', d: this.P.jump.prepDurMoving, e: 'in2', to: CLIPS.jump[1].to }] : CLIPS.jump, this.lastBase); this.jumpBuf = 0;
  }
  sitLogic(dt) {
    const s = this.sit, b = this.body, P = this.P.sit, box = s.box; s.t += dt;
    switch (s.sub) {
      case 'approach': {
        if (!this.goal) { if (b.speed < 0.15) { s.sub = 'turn'; s.t = 0; this.faceYaw = box.face; this.intent.mag = 0; } }
        break; }
      case 'turn': {
        this.intent.mag = 0; this.faceYaw = box.face;
        const idle = !this.feet.feet.some(f => f.mode === 'swing');
        if (Math.abs(angDiff(b.yaw, box.face)) < P.turnTol && Math.abs(b.wy) < 0.6 && b.speed < 0.08 && idle) { s.sub = 'prep'; s.t = 0; this.faceYaw = box.face; this.clip = new ClipPlayer(CLIPS.jump, this.lastBase); }
        break; }
      case 'prep': {
        this.clip.step(dt);
        if (this.clip.done) {
          const apexY = box.y1 + P.hopApex, vy = Math.sqrt(2 * GRAVITY * (apexY - b.y)), T = vy / GRAVITY + Math.sqrt(2 * P.hopApex / GRAVITY);
          const dx = box.cx - b.x, dz = box.cz - b.z; b.ignoreH.add(box.id); b.jump(vy, dx / T, dz / T); s.sub = 'hop'; s.t = 0; s.hopV = { dx: dx / T, dz: dz / T };
        }
        break; }
      case 'hop': if (s.t > 1.5) { /* 失敗：沒落在座面上 */ b.ignoreH.clear(); this.sit = null; this.go('air', 'sitFail'); } break;
      case 'settle': { this.clip.step(dt); this.pinSeat(dt); if (this.clip.done) { s.sub = 'seated'; s.t = 0; } break; }
      case 'seated': this.pinSeat(dt); break;
      case 'risePrep': {
        this.clip.step(dt); this.pinSeat(dt);
        if (this.clip.done) {
          const S = s.S, hop = P.hopApex * 0.8, apexY = b.y + hop, vy = Math.sqrt(2 * GRAVITY * hop), T = vy / GRAVITY + Math.sqrt(2 * apexY / GRAVITY);
          b.jump(vy, (S.x - b.x) / T, (S.z - b.z) / T); s.sub = 'riseHop'; s.t = 0; this.faceYaw = null;
        }
        break; }
      case 'riseHop': if (s.t > 1.5) { b.ignoreH.clear(); this.sit = null; this.go('air', 'riseFail'); } break;
    }
  }
  pinSeat(dt) { const b = this.body, box = this.sit.box, k = 1 - Math.exp(-dt * 10); b.vx = b.vz = 0; b.x = lerp(b.x, box.cx, k); b.z = lerp(b.z, box.cz, k); b.wy = 0; b.yaw += angDiff(b.yaw, box.face) * k; }
  /** 水平速度指令：朝意圖方向轉身（慣性），沿目前朝向前進；朝向差越大走越慢（先轉再走） */
  steer(dt) {
    const b = this.body, I = this.intent, M = this.P.move, st = this.state;
    const locoOK = ['idle', 'walk', 'run', 'land', 'air'].includes(st) || (st === 'sit' && ['approach', 'turn'].includes(this.sit?.sub));
    if (!locoOK || st === 'recover') {
      if (st === 'jumpPrep') { b.wy = lerp(b.wy, 0, 1 - Math.exp(-dt * 18)); return { vx: b.vx, vz: b.vz, accel: 0, decel: 0 }; }
      if (st === 'sit' && ['hop', 'riseHop'].includes(this.sit?.sub)) { b.wy = 0; return { vx: b.vx, vz: b.vz, accel: 0, decel: 0 }; }
      if (st === 'tumble') { return null; }
      b.wy = lerp(b.wy, 0, 1 - Math.exp(-dt * 18)); return (st === 'sit' || st === 'sleep' || st === 'held') ? { vx: 0, vz: 0, decel: 14 } : { vx: 0, vz: 0, decel: M.decel };
    }
    let target = null;
    if (I.mag > 0.05) target = Math.atan2(I.x, I.z); else if (this.faceYaw != null) target = this.faceYaw;
    const hold = (st === 'idle' && I.mag > 0.05 && this.startT < M.startDelay);   // 慢半拍：先轉頭，過一會兒才動身體
    let wyT = 0, sc = 0;
    if (target != null && !hold) { const err = angDiff(b.yaw, target); wyT = clamp(err * 11, -M.turnRate, M.turnRate); if (I.mag > 0.05) sc = clamp(1.15 - Math.abs(err) / 1.2, 0, 1); if (Math.abs(err) < 0.01) wyT = err / dt * 0.5; }
    b.wy = lerp(b.wy, wyT, 1 - Math.exp(-dt * 16));
    if (st === 'air') { sc *= 0.6; }
    const sp = I.mag > 0.05 ? I.mag * (I.run ? M.run : M.walk) * sc : 0, c = Math.sin(b.yaw), z = Math.cos(b.yaw);
    return { vx: c * sp, vz: z * sp, decel: st === 'land' ? M.decel * 1.8 : M.decel };   // 落地時地面摩擦較大，衝勢很快收掉
  }
  onPhys(e) {
    const st = this.state, P = this.P;
    if (e.type === 'leave') { if (e.fall && ['idle', 'walk', 'run', 'land'].includes(st)) { this.go('air', 'fall'); } }
    else if (e.type === 'land') {
      this.kickSquash(e.imp); this.emit('land', e);
      if (st === 'air') this.go('land', 'land');
      else if (st === 'tumble') { /* 由 tumble 邏輯判斷停止 */ }
      else if (st === 'sit' && this.sit?.sub === 'hop') { if (this.body.groundId === this.sit.id) { this.sit.sub = 'settle'; this.sit.t = 0; this.clip = new ClipPlayer(CLIPS.land, this.lastBase); } else { this.body.ignoreH.clear(); this.sit = null; this.go('land', 'sitMiss'); } }
      else if (st === 'sit' && this.sit?.sub === 'riseHop') { this.body.ignoreH.clear(); this.sit = null; this.go('land', 'rose'); }
    } else if (e.type === 'bounce') { this.kickSquash(e.imp * 0.7); this.spin.ax *= 0.6; this.spin.az *= 0.6; this.emit('bounce', e); }
  }
  kickSquash(imp) {
    const L = this.P.land, w = TAU * L.hz, zt = L.zeta, wd = w * Math.sqrt(1 - zt * zt), tp = Math.atan2(wd, zt * w) / wd, f = Math.exp(-zt * w * tp) * Math.sin(wd * tp);
    const peak = clamp(L.peakB + L.peakK * imp, 0, L.peakMax); this.sq.v += peak * wd / f;
  }
  emit(type, d) { const ev = { type, t: this.time, ...d }; this.events.push(ev); if (this.events.length > 100) this.events.shift(); if (this.onEvent) this.onEvent(ev); }
  // ── 待機的生命力
  lifeTick(dt) {
    if (this.micro) { this.micro.t += dt; if (this.micro.t >= this.micro.def.dur) { this.micro = null; this.microT = lerp(...this.P.life.microGap, this.rng()); } }
    else if (!this.pet.want && !this.overlay && this.look == null) {
      this.microT -= dt;
      if (this.microT <= 0) {
        const L = this.P.life.micro.filter(m => (this.time - (this.cd[m.name] ?? -99)) > m.cd); if (!L.length) { this.microT = 1; return; }
        let tot = L.reduce((a, m) => a + m.w, 0), r = this.rng() * tot, pick = L[0]; for (const m of L) { r -= m.w; if (r <= 0) { pick = m; break; } }
        this.cd[pick.name] = this.time; this.micro = { name: pick.name, def: MICRO[pick.name], t: 0 };
      }
    }
  }
  // ── 腳的驅動模式
  feetDrive() {
    const st = this.state, b = this.body, d = { mode: 'stand', kind: 'walk', t: this.time, free: null };
    const key = this.key;
    if (key === 'walk' || key === 'run') { d.mode = 'gait'; d.kind = key; }
    else if (key === 'air' || st === 'held' || st === 'tumble') { d.mode = 'free'; d.free = { dy: st === 'held' ? -0.012 : clamp(pw([[-6, -0.02], [0, 0], [4, 0.03]], b.vy), -0.02, 0.03), pitch: st === 'held' ? 0.3 : 0.15, swingZ: st === 'held' ? 0.03 : 0, hz: 9 }; }
    else if (st === 'sit' && ['settle', 'seated', 'risePrep'].includes(this.sit?.sub)) { d.mode = 'free'; d.free = { dy: 0.012, swingZ: this.sit.sub === 'seated' ? 0.03 : 0.0, hz: 3.2, pitch: 0.12 }; }
    else if (key === 'jumpPrep' && b.speed > 0.3) { d.mode = 'gait'; d.kind = b.speed > 0.9 ? 'run' : 'walk'; }
    else if (st === 'land' && b.speed > 0.2) { d.mode = 'gait'; d.kind = b.speed > 0.9 ? 'run' : 'walk'; }   // 落地的衝勢用小碎步收掉，不滑腳
    return d;
  }
  // ── 姿勢產生
  keyOf() {
    const st = this.state, b = this.body;
    switch (st) {
      case 'idle': return 'idle'; case 'walk': return 'walk'; case 'run': return 'run';
      case 'jumpPrep': return 'jumpPrep'; case 'air': return 'air'; case 'land': return 'land';
      case 'sleep': return 'sleep'; case 'held': return 'held'; case 'tumble': return 'tumble'; case 'recover': return 'recover';
      case 'sit': { const sub = this.sit?.sub; if (sub === 'approach' || sub === 'turn') return this.feet.cad > 0 ? (this.intent.run ? 'run' : 'walk') : 'idle'; if (sub === 'prep' || sub === 'risePrep') return 'jumpPrep'; if (sub === 'hop' || sub === 'riseHop') return 'air'; if (sub === 'settle') return 'sitLand'; return 'sit'; }
    }
    return 'idle';
  }
  composePose(dt) {
    const bus = this.bus, S = this.sig, P = this.P; bus.begin();
    const key = this.keyOf();
    if (key !== this.key) { this.prevKey = this.key; this.key = key; this.fade.from.set(this.lastBase); this.fade.t = 0; this.fade.dur = FADE[this.prevKey + '>' + key] ?? FADE.default; }
    // 基底（唯一寫入者＝提供者本身）
    this.provide(key, dt);
    // 交叉淡化
    const a = bus.a;
    if (this.fade.t < 1) { this.fade.t = Math.min(1, this.fade.t + dt / this.fade.dur); const e = EASE.io(this.fade.t), f = this.fade.from; for (let i = 0; i < N; i++) a[i] = lerp(f[i], a[i], e); }
    this.lastBase.set(a);
    // ── 疊加層
    // 次級彈簧（耳朵、尾巴）：追蹤「加速度 × 增益」的目標，帶阻尼
    for (const s of this.springs) { const w = TAU * s.hz, tgt = s.gain * S[s.src]; s.v += (w * w * (tgt - s.x) - 2 * s.zeta * w * s.v) * dt; s.x = clamp(s.x + s.v * dt, -0.9, 0.9); bus.add(s.ch, s.x, 'secondary'); }
    // 呼吸（形態鍵）＋ 身體重心輕微起伏
    if (this.life) { const L = P.life.breath, slow = this.state === 'sleep' ? 1.9 : 1; bus.add('morph.breath', (0.5 + 0.5 * Math.sin(this.time * TAU / (L.period * slow))) * L.amp, 'breath'); }
    // 待機小動作
    if (this.micro) { const m = this.micro; for (const [ch, keys] of Object.entries(m.def.ch)) bus.add(ch, this.keyv(keys, m.t), 'micro'); }
    // 覆蓋層（hit／happy…）
    if (this.overlay) { const o = this.overlay.player.out, am = (P.react?.amp?.[this.overlay.name]) ?? 1; for (let i = 0; i < N; i++) if (o[i]) bus.a[i] += o[i] * am; for (let i = 0; i < N; i++) if (o[i]) bus.addWho[i].add('overlay'); }
    // 等待反應的那半拍：歪頭、耳朵豎起（好奇）。pend.t 由 t0 倒數到 0，用正弦包絡讓進出都是 0
    if (this.pend) { const u = 1 - this.pend.t / Math.max(1e-3, this.pend.t0), e = Math.sin(clamp(u, 0, 1) * Math.PI), tilt = P.react?.curiousTilt ?? 0.12; bus.add('head.rz', tilt * e, 'react'); bus.add('ear.L.rx', 0.12 * e, 'react'); bus.add('ear.R.rx', 0.12 * e, 'react'); }
    // 視線（疊加層）：轉身時頭先動（慢半拍）、看向游標
    this.gazeLayer(dt);
    // 擠壓彈簧（落地壓縮與回彈，卡通變形層）
    { const L = P.land, w = TAU * L.hz; this.sq.v += (-w * w * this.sq.x - 2 * L.zeta * w * this.sq.v) * dt; this.sq.x += this.sq.v * dt; const x = this.sq.x;
      bus.add('morph.land', Math.max(0, x), 'squash'); bus.add('morph.stretch', Math.max(0, -x) * 0.9, 'squash'); }
    // 摸頭
    this.petLayer(dt);
    // 翻滾旋轉（視覺）
    if (this.state === 'tumble') { bus.add('root.rx', this.pitchA || 0, 'tumble'); bus.add('root.rz', this.rollA || 0, 'tumble'); }
    // 橫向膨脹限制：不穿牆、不穿家具（規則 10）
    this.limitSquash();
    for (const m of MORPHS) { const i = IDX['morph.' + m]; a[i] = clamp(a[i], 0, 1); }
    this.poseDy[2] = this.poseDy[1]; this.poseDy[1] = this.poseDy[0]; this.poseDy[0] = a[IDX['root.dy']];
    this.prevPose.set(this.pose); this.pose.set(a);
    this.exprLayer();
  }
  keyv(keys, t) { if (t <= keys[0][0]) return keys[0][1]; for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) { const a = keys[i - 1], b = keys[i], u = (t - a[0]) / (b[0] - a[0]); return lerp(a[1], b[1], u * u * (3 - 2 * u)); } return keys[keys.length - 1][1]; }
  limitSquash() {
    const a = this.bus.a, g = (k) => a[IDX['morph.' + k]] || 0, R = this.shape.R, b = this.body;
    const ex = (0.10 * g('squash') + 0.17 * g('land') + 0.07 * g('plump') - 0.065 * g('stretch')) * R;
    if (ex <= 0.002) return; const clr = this.world.clearance(b.x, b.z, R, b.y, this.shape.H);
    if (ex > clr) { const k = Math.max(0, clr / ex); for (const m of ['squash', 'land', 'plump']) a[IDX['morph.' + m]] *= k; this.debug.squashLimited = (this.debug.squashLimited || 0) + 1; }
  }
  gazeLayer(dt) {
    const bus = this.bus, b = this.body, M = this.P.move, I = this.intent;
    let ty = 0, tp = 0, hy = 0, hp = 0;
    const target = I.mag > 0.05 ? Math.atan2(I.x, I.z) : this.goal ? Math.atan2(this.goal.x - b.x, this.goal.z - b.z) : null;
    if (target != null && ['idle', 'walk', 'run', 'land'].includes(this.state)) { const err = clamp(angDiff(b.yaw, target), -0.9, 0.9); hy += err * M.headFirst * 0.6; ty += clamp(err, -0.34, 0.34); }
    if (this.look) {
      const L = this.look, hx = b.x, hz = b.z, dy = L.y - (b.y + 0.5), d = Math.hypot(L.x - hx, L.z - hz) + 1e-3, yaw = clamp(angDiff(b.yaw, Math.atan2(L.x - hx, L.z - hz)), -1.1, 1.1), pit = clamp(Math.atan2(dy, d), -0.5, 0.5);
      hy += yaw * 0.45; hp += -pit * 0.3; ty += clamp(yaw, -0.34, 0.34); tp += pit * 0.5;
    }
    const k = 1 - Math.exp(-dt * 10), s = this.lookS; s.y = lerp(s.y, hy, k); s.p = lerp(s.p, hp, k); s.ey = lerp(s.ey || 0, ty, k); s.ep = lerp(s.ep || 0, tp, k);
    bus.add('head.ry', s.y, 'gaze'); bus.add('head.rx', s.p, 'gaze'); bus.add('eye.y', s.ey, 'gaze'); bus.add('eye.p', s.ep, 'gaze');
  }
  petLayer(dt) {
    const pt = this.pet, C = this.P.pet, w = TAU * C.hz, tgt = pt.on ? 1 : 0;
    pt.v += (w * w * (tgt - pt.p) - 2 * C.zeta * w * pt.v) * dt; pt.p += pt.v * dt;
    if (Math.abs(pt.p) < 1e-4 && Math.abs(pt.v) < 1e-3 && !pt.on) { pt.p = 0; pt.v = 0; }
    const p = pt.p, bus = this.bus; if (p === 0) return;
    const pos = Math.max(0, p), neg = Math.max(0, -p);
    bus.add('head.rx', 0.2 * p, 'pet'); bus.add('morph.squash', 0.32 * pos, 'pet'); bus.add('morph.stretch', 0.5 * neg, 'pet');
    bus.add('ear.L.rx', -0.3 * p, 'pet'); bus.add('ear.R.rx', -0.3 * p, 'pet'); bus.add('ear.L.rz', -0.2 * pos, 'pet'); bus.add('ear.R.rz', 0.2 * pos, 'pet');
    bus.add('morph.cheek.L', 0.9 * pos, 'pet'); bus.add('morph.cheek.R', 0.9 * pos, 'pet');
    bus.add('root.rx', 0.03 * p, 'pet'); bus.add('root.rz', 0.025 * Math.sin(this.time * 9) * pos, 'pet'); bus.add('tail.ry', 0.35 * Math.sin(this.time * 12) * pos, 'pet');
  }
  exprLayer() {
    let e = this.base_expr || 'neutral';
    if (this.exprOverride) e = this.exprOverride;
    else if (this.pet.on && this.pet.p > 0.25) e = 'bliss';
    else if (this.overlay) e = this.overlay.def.expr;
    this.setExpr(e);
  }
  /** 目前狀態的姿勢提供者 */
  provide(key, dt) {
    const bus = this.bus, P = this.P, who = key; let expr = 'neutral';
    const drv = (list, src) => { for (const d of list) bus.add(d.ch, pw(d.map, src[d.src]), who + '.drv'); };
    switch (key) {
      case 'idle': expr = POSES.idle.expr; break;
      case 'walk': case 'run': {
        const C = CYCLES[key], G = P.gait[key], duty = G.duty, m = this.feet.phase - duty / 2, n = clamp(this.sig.speed / G.vmax, 0, 1.2), wk = P.waddle / 0.085, turn = this.sig;
        for (const t of C.terms) {
          let v = (t.base || 0) + (t.amp ? t.amp * Math.sin(TAU * ((t.k || 1) * m + (t.ph || 0))) * this.gaitAmp : 0);   // 站定時擺動幅度平滑歸零
          if (t.n) v *= lerp(t.n[0], t.n[1], Math.min(1, n)); if (t.w) v *= wk;
          bus.set(t.ch, v, who);
        }
        drv(C.drv, this.sig); expr = C.expr; break; }
      case 'jumpPrep': case 'land': {
        const c = this.clip; if (c) bus.a.set(c.out); for (let i = 0; i < N; i++) if (c && c.out[i]) bus.owner[i] = who;
        expr = key === 'land' ? 'surprised' : 'neutral';
        if (key === 'land' && this.stateT > 0.25) expr = 'neutral'; break; }
      case 'sitLand': { const c = this.clip; if (c) { bus.a.set(c.out); } bus.set('root.dy', 0, who); expr = 'smile'; break; }
      case 'air': { const A = POSES.air; for (const [k, v] of Object.entries(A.pose)) bus.set(k, v, who); drv(A.drv, this.sig); expr = A.expr; break; }
      case 'sit': { const A = POSES.sit; for (const [k, v] of Object.entries(A.pose)) bus.set(k, v, who); bus.set('root.dy', 0, who); expr = A.expr; break; }
      case 'sleep': { const c = this.clip; if (c && !c.done) bus.a.set(c.out); else for (const [k, v] of Object.entries(POSES.sleep.pose)) bus.a[IDX[k]] = v; for (let i = 0; i < N; i++) bus.owner[i] = bus.a[i] ? who : null; expr = 'sleep'; break; }
      case 'held': case 'tumble': case 'recover': { const A = POSES[key]; for (const [k, v] of Object.entries(A.pose)) bus.set(k, v, who); expr = A.expr;
        if (key === 'held' && this.held) {   // 繞抓點旋轉：先轉身體，再把抓點補回原位（位置 = P − R·P）
          const g = this.hang, pv = this.held.pivot, R = _hq.setFromEuler(_he.set(g.x, 0, g.z, 'XYZ')), o = _hv.set(pv.x, pv.y, pv.z).applyQuaternion(R);
          bus.add('root.rx', g.x, 'hang'); bus.add('root.rz', g.z, 'hang'); bus.add('root.dx', pv.x - o.x, 'hang'); bus.add('root.dy', pv.y - o.y, 'hang'); bus.add('root.dz', pv.z - o.z, 'hang'); }
        break; }
    }
    if (this.state === 'sit' && ['approach', 'turn'].includes(this.sit?.sub) === false && key === 'jumpPrep') expr = 'neutral';
    this.base_expr = expr;
  }

  // ── 畫面：內插＋套用到骨頭＋腳 IK＋接地投影
  buildSamples() {
    // 取靜止姿勢下 y<0.13 的身體頂點（不含由腿腳主導的）當「接地取樣點」：之後每幀用 CPU 蒙皮算出實際最低點
    const ch = this.ch, b = ch.body, g = b.geometry, p = g.attributes.position, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, names = b.skeleton.bones.map(x => x.name), idx = [];
    ch.resetPose(); ch.model.updateMatrixWorld(true); b.skeleton.update(); const T = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      T.set(p.getX(i), p.getY(i), p.getZ(i)); b.applyBoneTransform(i, T); if (T.y > this.shape.bottom + 0.125) continue;
      let bi = 0, bw = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; bi = si.getComponent(i, k); } }
      if (/leg|foot/.test(names[bi])) continue; idx.push(i);
    }
    return idx;
  }
  /** 目前所有「身體取樣點」的最低世界 y（含形態鍵） */
  lowestBody(all = false, who = null) {
    const ch = this.ch, b = ch.body, g = b.geometry, p = g.attributes.position, M = g.morphAttributes.position, w = b.morphTargetInfluences, T = this._T || (this._T = new THREE.Vector3());
    ch.model.updateMatrixWorld(true); b.skeleton.update(); let mn = 1e9;
    const list = all ? null : this.sampleIdx, n = all ? p.count : list.length;
    for (let j = 0; j < n; j++) {
      const i = all ? j : list[j]; T.set(p.getX(i), p.getY(i), p.getZ(i));
      for (let k = 0; k < M.length; k++) if (w[k]) { T.x += M[k].getX(i) * w[k]; T.y += M[k].getY(i) * w[k]; T.z += M[k].getZ(i) * w[k]; }
      b.applyBoneTransform(i, T); T.applyMatrix4(b.matrixWorld); if (T.y < mn) { mn = T.y; if (who) who.i = i; }
    }
    return mn;
  }
  applyPose(p, dyExtra) {
    const ch = this.ch, dbg = this.debug, count = dbg.count;
    for (let j = 0; j < BONES.length; j++) { const bi = BONE_IDX[j]; ch.rot(BONES[j], p[bi[0]], p[bi[1]], p[bi[2]]); if (count) dbg.perBone[BONES[j]] = (dbg.perBone[BONES[j]] || 0) + 1; }
    ch.move('root', p[IDX['root.dx']], p[IDX['root.dy']] + dyExtra, p[IDX['root.dz']]);
    for (const m of MORPHS) ch.morph(m, p[IDX['morph.' + m]]);
  }
  render(alpha, dt) {
    const ch = this.ch, s0 = this.snapPrev, s1 = this.snap, root = ch.root, dbg = this.debug; dbg.frames++;
    root.position.set(lerp(s0.x, s1.x, alpha), lerp(s0.y, s1.y, alpha), lerp(s0.z, s1.z, alpha)); root.rotation.y = s0.yaw + angDiff(s0.yaw, s1.yaw) * alpha;
    const p = this._p || (this._p = new Float32Array(N)); for (let i = 0; i < N; i++) p[i] = lerp(this.prevPose[i], this.pose[i], alpha);
    dbg.perBone = {}; dbg.count = dbg.countOn;
    this.applyPose(p, 0); root.updateMatrixWorld(true); this.feet.apply(alpha);
    // 接地投影（視覺安全網，量的是蒙皮後的實際頂點）：
    //  · 一般：身體取樣點任一低於支撐面 → 整個身體抬起（只抬不壓；腳由腳 IK 負責）。
    //  · 坐著：閉環貼合——把身體取樣最低點（臀部）精準放到座面上（上下都修），接觸點來自網格而不是寫死的高度。
    const big = this.state === 'tumble' || Math.abs(p[IDX['root.rx']]) + Math.abs(p[IDX['root.rz']]) + Math.abs(p[IDX['head.rx']]) + Math.abs(p[IDX['spine.rx']]) + Math.abs(p[IDX['pelvis.rx']]) > 0.15, sup = this.body.supportY;
    const snap = this.state === 'sit' && ['settle', 'seated', 'risePrep'].includes(this.sit?.sub);
    let dyx = 0, pen = 0;
    for (let pass = 0; pass < 3; pass++) {
      const low = this.lowestBody(big && !snap); const e = sup + (snap ? 0.003 : 0) - low;   // 坐著留 3 mm 縫隙，避免座面與圓肚皮共平面的 z-fighting（仍遠小於 1 cm）
 if (pass === 0) pen = e;
      if (snap ? Math.abs(e) < 0.0005 : e < 0.0008) break;
      dyx = clamp(dyx + e, snap ? -0.08 : 0, 0.5); this.applyPose(p, dyx); root.updateMatrixWorld(true); this.feet.apply(alpha);
      if (pass === 0 && !snap) { dbg.proj++; }
    }
    if (dyx > 0 && !snap) dbg.projMax = Math.max(dbg.projMax, dyx); this.dyx = dyx;
    dbg.lastPen = Math.max(0, pen);
    ch.model.updateMatrixWorld(true);
    // 臉：視線（疊加層輸出）
    const f = ch.face; if (f) f.lookAt(p[IDX['eye.y']], p[IDX['eye.p']]);
    ch.update(dt);
  }
  info() {
    const b = this.body; return { state: this.state, sub: this.sit?.sub || null, key: this.key, speed: b.speed, vy: b.vy, grounded: b.grounded, x: b.x, y: b.y, z: b.z, yaw: b.yaw, cad: this.feet.cad, stride: this.feet.stride, phase: this.feet.phase, fade: this.fade.t, expr: this.expr, micro: this.micro?.name || null, pet: this.pet.p, dropped: this.stepper.dropped, conflicts: this.bus.conflicts.length, rejects: this.rejects.length };
  }
}
