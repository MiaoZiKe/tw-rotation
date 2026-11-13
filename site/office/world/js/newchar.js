// ════════════════════════════════════════════════════════════════════════
// 新角色相容層（2026-11-14，3D 角色建模師）：辦公室的 createCharacter(spec, env) 掛鉤。
//   · 物種在 char/kinds.js 的 NEW_KINDS 裡（糰糰 mochi、垂垂 bunny、布布 pudding）→ 用 Blender 參數化一體成形網格（char/mochi.js）
//     ＋骨架／形態鍵＋固定步長控制器（char/controller.js）驅動；介面與 play/office_character.js 的 createCharacter 一樣（含 inner 墊片）。
//   · 其他物種 → 原封不動交給舊系統（play/office_character.js）。兩套並存。網址加 ?body=v1 可強制全部走舊系統（新舊對照用）。
// 世界端只需要把 loadCharacterModule 的預設路徑指到本檔；本檔會 re-export 舊模組的所有名稱（configure、lookFor、ICON_NAMES…）。
// 座標：控制器在「模型座標」（公尺、未縮放）裡運算；物件的世界位置＝模型位置 × scale（CEO 1.15、寵物 0.5）。
// ════════════════════════════════════════════════════════════════════════
import * as THREE from 'three';
import * as Old from '../../play/office_character.js';
import { loadMochi, MochiChar } from '../../char/mochi.js';
import { CharController, loadProfile } from '../../char/controller.js';
import { PhysWorld } from '../../char/physics.js';
import { CHANNELS } from '../../char/actions.js';
import { NEW_KINDS, isNew, colorsFor, mergeProfile, officeProfile, PROFILE_OVERRIDE } from '../../char/kinds.js';
import { addAccs, addCherry } from '../../char/accs.js';
import { G as KG } from './kit.js';
export * from '../../play/office_character.js';

const V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x)), lerp = (a, b, t) => a + (b - a) * t;
const IDX = Object.fromEntries(CHANNELS.map((n, i) => [n, i]));
const hash = (s) => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0; return h; };
const FORCE_OLD = /[?&]body=v1\b/.test(location.search);

// ── 資源預載（頂層 await：模組載入完成時，三個物種的近景／遠景網格與個性檔都已就緒，createCharacter 可以同步建立）
const ASSET = {}; let BASE_PROFILE = null;
if (!FORCE_OLD) {
  BASE_PROFILE = await loadProfile(new URL('../../char/profiles/mochi.json', import.meta.url).href);
  await Promise.all(Object.keys(NEW_KINDS).map(async (sp) => { const [a0, a2] = await Promise.all([loadMochi({ species: sp, lod: 0 }), loadMochi({ species: sp, lod: 2 })]); ASSET[sp] = { 0: a0, 2: a2 }; }));
}
export const newCharStats = { created: 0, species: {} };

const EXPR = { neutral: null, happy: 'happy', angry: 'angry', surprised: 'surprised', sad: 'sad', think: 'look', awkward: 'shy', proud: 'smug', sleepy: 'sleepy', laugh: 'laugh', ouch: 'ouch' };
const ALIAS = { '!': 'exclaim', '?': 'question', '怒': 'anger', '♪': 'note', '…': 'dots', '汗': 'sweat', '☆': 'star', '♥': 'heart' };
const ONE_SHOT = { talk: 2.2, nod: 1.2, shake: 1.2, raise: 1.6, cheer: 1.8, clap: 1.6, angry: 1.8, wave: 1.4, stretch: 2.7, slam: 1.8, point: 1.6, pour: 1.6, reach: 1.4 };
const ACTS = {
  idle: {}, type: { pose: 'type' }, read: { pose: 'read', A: 'book' }, tablet: { pose: 'read', A: 'tablet' }, doc: { pose: 'read', A: 'doc' },
  note: { pose: 'note', L: 'notebook', R: 'pen' }, listen: { pose: 'listen' }, think: { pose: 'think' }, nod: { pose: 'nod' }, shake: { pose: 'no' },
  raise: { pose: 'raise' }, clap: { pose: 'clap' }, cheer: { pose: 'cheer' }, drink: { pose: 'drink', R: 'cup' }, phone: { pose: 'phone', R: 'phone' },
  talk: { pose: 'talkg' }, stretch: { pose: 'stretch' }, doze: { pose: 'doze' }, slam: { pose: 'slam' }, point: { pose: 'point' },
  carry: { pose: 'carry', A: 'doc' }, present: { pose: 'present', A: 'doc' }, eat: { pose: 'eat', R: 'donut' }, magnify: { pose: 'magnify', R: 'magnifier', L: 'doc' },
  box: { pose: 'carry', A: 'box' }, paddle: { pose: 'paddle', R: 'paddle' }, pour: { pose: 'pour', R: 'cup' }, reach: { pose: 'reach' }, sulk: { pose: 'sulk' }, angry: { pose: 'slam' }, wave: { pose: 'raise' }, sleep: {},
};
// 動作姿勢＝疊在控制器輸出之上的「手臂／頭」增量（模型座標軸的歐拉角；arm.L 骨頭朝 +X：rz＋抬起、ry－往前；arm.R 朝 −X：rz－抬起、ry＋往前）
const sn = Math.sin;
const POSES = {
  type: (t) => { const a = sn(t * 17), b = sn(t * 17 + 2.1); return { 'arm.L': [0, -0.85, 0.38 + 0.12 * a], 'arm.R': [0, 0.85, -0.38 - 0.12 * b], head: [0.12, 0, 0] }; },
  read: (t) => ({ 'arm.L': [0, -1.0, 0.55], 'arm.R': [0, 1.0, -0.55], head: [0.2, 0.04 * sn(t * 0.7), 0] }),
  note: (t) => ({ 'arm.L': [0, -0.95, 0.5], 'arm.R': [0, 0.9, -0.62 + 0.1 * sn(t * 9)], head: [0.22, 0, 0] }),
  listen: (t) => ({ head: [0.02, 0, 0.13], 'ear.L': [-0.12, 0, 0], 'ear.R': [-0.12, 0, 0] }),
  think: (t) => ({ 'arm.R': [0, 0.5, -1.15], head: [0.04, 0.1, -0.16 + 0.03 * sn(t * 1.3)] }),
  nod: (t) => ({ head: [0.2 * sn(t * 7), 0, 0] }), no: (t) => ({ head: [0, 0.3 * sn(t * 8), 0] }),
  raise: (t) => ({ 'arm.L': [0, -0.25, 1.9], head: [-0.06, 0, 0] }),
  clap: (t) => { const k = 0.5 + 0.5 * sn(t * 14); return { 'arm.L': [0, -1.1 - 0.35 * k, 0.4], 'arm.R': [0, 1.1 + 0.35 * k, -0.4] }; },
  cheer: (t) => ({ 'arm.L': [0, 0, 2.0 + 0.2 * sn(t * 11)], 'arm.R': [0, 0, -2.0 - 0.2 * sn(t * 11 + 1)], head: [-0.1, 0, 0] }),
  drink: (t) => { const u = (t % 3.2) / 3.2, k = clamp((u - 0.1) / 0.2, 0, 1) * (1 - clamp((u - 0.62) / 0.18, 0, 1)); return { 'arm.R': [0, 0.5 * k, -0.3 - 1.0 * k], head: [-0.1 * k, 0, 0] }; },
  phone: (t) => ({ 'arm.R': [0, 0.2, -1.55], head: [0, 0, 0.14] }),
  talkg: (t) => ({ head: [0.04 * sn(t * 5), 0.06 * sn(t * 3.1), 0], 'arm.L': [0, -0.3 * (0.5 + 0.5 * sn(t * 2.3)), 0.5], 'arm.R': [0, 0.3 * (0.5 + 0.5 * sn(t * 2.1)), -0.5] }),
  stretch: (t) => { const k = clamp(Math.min(t / 0.6, (2.7 - t) / 0.6), 0, 1); return { 'arm.L': [0, -0.2, 2.5 * k], 'arm.R': [0, 0.2, -2.5 * k], head: [-0.25 * k, 0, 0], spine: [-0.12 * k, 0, 0] }; },
  doze: (t) => ({ head: [0.35 + 0.05 * sn(t * 1.1), 0, 0.12 * sn(t * 0.7)], spine: [0.1, 0, 0] }),
  slam: (t) => { const u = (t % 1.8) / 1.8, k = u < 0.4 ? u / 0.4 : Math.max(0, 1 - (u - 0.4) / 0.12); return { 'arm.R': [0, 0.2, -2.2 * k], 'arm.L': [0, -0.2, 2.2 * k], head: [0.15 * (1 - k), 0, 0] }; },
  point: (t) => ({ 'arm.R': [0, 1.35, -0.35], head: [0, -0.12, 0] }),
  carry: (t) => ({ 'arm.L': [0, -1.25, 0.35], 'arm.R': [0, 1.25, -0.35] }), present: (t) => ({ 'arm.L': [0, -1.2, 0.5], 'arm.R': [0, 1.2, -0.5], head: [-0.04, 0, 0] }),
  eat: (t) => { const u = (t % 1.9) / 1.9, k = clamp((u - 0.05) / 0.25, 0, 1) * (1 - clamp((u - 0.5) / 0.2, 0, 1)); return { 'arm.R': [0, 0.6 * k, -0.3 - 0.9 * k], head: [0.05 * sn(t * 12) * k, 0, 0] }; },
  magnify: (t) => ({ 'arm.R': [0, 1.0, -0.8], 'arm.L': [0, -0.9, 0.6], head: [0.1, 0.12 * sn(t * 0.9), 0] }),
  paddle: (t) => ({ 'arm.R': [0, 1.1, -0.7 + 0.5 * sn(t * 6)] }), pour: (t) => ({ 'arm.R': [0, 1.0, -0.6], head: [0.12, 0, 0] }), reach: (t) => ({ 'arm.R': [0, 1.3, -0.6], 'arm.L': [0, -1.3, 0.6], head: [0.05, 0, 0] }),
  sulk: (t) => ({ head: [0.3, 0.2, 0.05], spine: [0.08, 0, 0] }),
};

export function createCharacter(spec, env = {}) {
  const look = Old.lookFor(spec);
  if (FORCE_OLD || !isNew(look.species) || !ASSET[look.species]) return Old.createCharacter(spec, env);
  return makeNew(spec, look, env);
}

function makeNew(spec, look, env) {
  const kind = NEW_KINDS[look.species], col = colorsFor(look), s = spec.scale || 1, B = env.bounds || { x0: 0.6, x1: 39.4, z0: 0.6, z1: 33 };
  const A = ASSET[look.species], meta = A[0].meta;
  const ch = new MochiChar(A[0], { preset: kind.preset, color: col.color, top: col.top, zone: col.zone, faceW: 512 }); ch.attachFar(A[2]);
  const root = new THREE.Group(), space = new THREE.Group(); space.matrixAutoUpdate = false; root.userData.character = true; root.add(ch.root, space); root.name = 'newchar-' + look.species;
  ch.body.castShadow = false; ch.body.receiveShadow = false;
  const worn = addAccs(ch, col.accWorn, col.acc), anch = meta.anchors, mouthY = anch.mouth.p[1], eyeY = anch['eye.L'].p[1], front = Math.abs(anch.mouth.p[2]);
  const cherry = kind.cherry ? addCherry(ch, col.cherry) : null;
  const topY = look.species === 'bunny' ? 1.07 : look.species === 'pudding' ? 0.52 : 0.72;
  const world = new PhysWorld({ minX: B.x0 / s, maxX: B.x1 / s, minZ: B.z0 / s, maxZ: B.z1 / s });
  const k = 1.5 * Math.pow(1 / s, 0.5);
  const prof = officeProfile(mergeProfile(BASE_PROFILE, PROFILE_OVERRIDE[look.species]), k), walkV = prof.move.walk * s, runV = prof.move.run * s;
  const ctl = new CharController(ch, world, prof, { life: true, seed: hash(spec.id || spec.nick || 'x') });
  newCharStats.created++; newCharStats.species[look.species] = (newCharStats.species[look.species] || 0) + 1;

  const ext = { vx: 0, vz: 0 };
  // inner 墊片：世界端（pilot／pov／attention／director）讀寫的舊角色欄位，轉成控制器的動作
  const inner = {
    ctl, ch, kind: 'new', mouthY, poseT: 0, idleT: 0, sqV: 0, airT: 0, petting: false, phase0: 0,
    get mode() { const st = ctl.state; return (st === 'sleep' || c.action === 'sleep') ? 'sleep' : (st === 'sit' || c._seat) ? 'sit' : 'normal'; },
    get yaw() { return ctl.body.yaw; }, set yaw(v) { ctl.body.yaw = v; },
    vel: new V3(), pos: new V3(),     // 與舊角色一樣是 Vector3（世界端會呼叫 length() 等）；每幀由控制器的物理狀態同步（寫入無效）
    cfg: { R: kind.rad, move: 'walk', walk: 1.5, run: 3.5, mouth: [0, mouthY, front], top: topY, front, cheek: [0.25, 0.3, 0.3] },
    get extFall() { return ['air', 'jumpPrep', 'tumble'].includes(ctl.state); }, set extFall(v) { if (v && !['air', 'jumpPrep', 'tumble', 'held'].includes(ctl.state) && ctl.body.grounded && !c._seat) ctl.jump(); },
    get jumpPrep() { return ctl.state === 'jumpPrep' ? 1 : 0; }, set jumpPrep(v) { if (v > 0 && ctl.state !== 'jumpPrep' && ctl.body.grounded && !c._seat) ctl.jump(); },
    onLand(imp, sf) { }, get sq() { return ctl.sq.x; },
    feet: { forEach() { } }, hands: look.species === 'pudding' ? [] : ['L', 'R'].map(sd => ({ m: ch.bones['hand.' + sd], get p() { return ch.boneWorld('hand.' + sd).add(inner.pos); } })), ext,
    wake() { if (ctl.state === 'sleep') ctl.wake(); if (c._seat) { c._seat = null; ctl.standUp(); } },
    doAct(n) { if (n === 'sig') { ctl.trigger('happy'); ctl.jump(); } else if (n === 'wave') c.setAction('wave'); },
    emote(n, sec) { ctl.setExpression(EXPR[n] ?? n); setTimeout(() => { if (ctl.exprOverride === (EXPR[n] ?? n)) ctl.setExpression(c.expression && EXPR[c.expression] || null); }, (sec || 1) * 1000); },
    headTop(out) { return out.set(root.position.x, (ctl.body.y + topY) * s, root.position.z); },
    get extPose() { return ACTS[c.action]?.pose || null; }, set extPose(v) { },
  };
  ctl.onEvent = (e) => { if (e.type === 'land') { inner.sqV = -(e.imp * 0.85); inner.onLand(e.imp, false); } };
  const camP = new V3(0, 6, 10), slot = { A: null, L: null, R: null }, slotType = { A: '', L: '', R: '' };
  let icon = null, iconT = 0, iconDur = 0, lod = 0, frame = (hash(spec.id || 'x') % 6), accDt = 0, react = null, loud = 0, hold = null, speakUntil = 0, curPose = null, poseT0 = 0;
  const c = {
    object3D: root, spec, look, inner, scale: s, radius: kind.rad * s, height: (topY + 0.06) * s, speech: null, emoteSym: null, expression: 'neutral', action: 'idle', lift: 0,
    _base: 'idle', _until: 0, _t: 0, _path: null, _pi: 0, _speed: 1.6, _resolve: null, _stuck: 0, _ghost: 0, _seat: null, _hop: null, _held: false, heading: 0, onDrop: null, sleeping: false, newModel: true,
    get state() { return (c._held || ctl.state === 'held') ? 'held' : (c._path || c._rising) ? 'walk' : c._seat ? 'sit' : 'stand'; },
    get lod() { return lod; },
    update(dt, t) {
      c._t = t; dt = Math.min(dt, 0.05); if (loud > 0) loud -= dt;
      const b = ctl.body;
      // 場景直接改 object3D.position（瞬移）以它為準
      if (!c._held && ctl.state !== 'held' && !c._seat && !c._rising && Math.abs(root.position.x - b.x * s) + Math.abs(root.position.z - b.z * s) > 0.5) place(root.position.x, root.position.z);
      if (c._until && t > c._until) { c._until = 0; apply(c._base); }
      if (c.speech && t > c.speech.until) c.speech = null; if (c.emoteSym && t > c.emoteSym.until) c.emoteSym = null;
      if (react && t > react.until) { const r = react; react = null; r.done && r.done(); }
      drive(dt);
      c.sleeping = c.action === 'sleep';
      if (c._held && ctl.state !== 'held' && ctl.state !== 'tumble' && ctl.state !== 'air' && ctl.body.grounded) dropped();
      // 遠近分級
      let dist = 0; if (env.camera) { camP.copy(env.camera.position); dist = camP.distanceTo(root.position); }
      const want = c._held || react || env.followed === c ? 0 : dist > 30 ? 2 : dist > 14 ? 1 : 0; if (want !== lod) setLod(want);
      accDt += dt; frame++;
      if (lod === 0 || c._path || c._held || ctl.state !== 'idle' || frame % (lod + 1) === 0) {
        step(Math.min(accDt, 0.066)); accDt = 0; applyPose(t); props(t); Old.tickShared(t);
      }
      { const sv = !!c._seat && ctl.state === 'sit' && lod < 2 && root.visible; if (cushion) cushion.visible = sv && c._boost > 0 && !(c._lift > 0); if (riser) riser.visible = sv && c._lift > 0; }
      speakLip(t);
      if (icon && icon.visible) {
        iconT += dt; const u = iconT / iconDur; if (u >= 1) icon.visible = false; else { const pop = u < 0.12 ? 1 + 0.5 * Math.sin(u / 0.12 * Math.PI) : 1, kk = clamp(dist * 0.03, 0.34, 1.3) * pop * (u > 0.85 ? (1 - u) / 0.15 : Math.min(1, u / 0.06)); icon.scale.setScalar(kk); icon.position.set(0, c.height + c.lift + 0.2 + dist * 0.04 + kk * 0.5 + Math.sin(iconT * 5) * 0.02, 0); }
      }
    },
    setAction(name, opts = {}) { if (!ACTS[name]) name = 'idle'; if (ONE_SHOT[name]) { c._until = c._t + (opts.duration || ONE_SHOT[name]); if (opts.then) c._base = opts.then; apply(name); } else { c._base = name; if (opts.duration) { c._until = c._t + opts.duration; c._base = opts.then || 'idle'; apply(name); } else if (!c._until) apply(name); } },
    setExpression(name, sec) { c.expression = name; ctl.setExpression(EXPR[name] ?? null); if (sec && sec < 1e8) { const tok = c._exTok = (c._exTok || 0) + 1; setTimeout(() => { if (c._exTok === tok && c.expression === name) { c.expression = 'neutral'; ctl.setExpression(null); } }, sec * 1000); } },
    drive(vx, vz, fx, fz) { c._drive = vx == null ? null : { vx, vz, fx: fx || 0, fz: fz || 0 }; if (vx == null) { ext.vx = ext.vz = 0; ctl.stop(); } },
    walkTo(path, opts = {}) {
      c._drive = null; c.stop(false); if (!path || path.length < 2 || c._held) return Promise.resolve(!c._held);
      c._path = path; c._pi = 1; c._speed = opts.speed || 1.6; c._stuck = 0;
      if (c._seat) { c._seat = null; c._rising = true; ctl.standUp(); }
      return new Promise(res => { c._resolve = res; });
    },
    stop(ok = false) { if (c._path) { c._path = null; const r = c._resolve; c._resolve = null; ctl.stop(); if (r) r(ok); } },
    sitAt(seat, opts = {}) {
      c.stop(false); if (c._held) return; const px = root.position.x, pz = root.position.z, d = Math.hypot(seat.x - px, seat.z - pz);
      c._seat = seat; c._rising = false; const sy = seatY(seat), SP = seatPos(seat); setSeatBox(seat, sy, SP);
      if (opts.instant || d > 2.4 || d < 0.05) { seatInstant(seat, sy, SP); return; }
      if (['sleep', 'held', 'tumble'].includes(ctl.state)) { seatInstant(seat, sy, SP); return; }
      if (!ctl.sitOn('seat')) seatInstant(seat, sy, SP); else { ctl.goal = null; ctl.sit.S = { x: ctl.body.x, z: ctl.body.z }; }
    },
    standAt(x, z, face) { c.stop(false); if (c._held) return; c._seat = null; c._rising = false; c._hop = null; world.boxes.length = 0; place(x, z); if (face != null) { c.heading = face; ctl.reset(x / s, z / s, face); } apply(c.action); },
    faceTo(x, z) { const dx = x - ctl.body.x * s, dz = z - ctl.body.z * s; if (dx * dx + dz * dz > 1e-4) { c.heading = Math.atan2(dx, dz); if (c._seat && ctl.sit) ctl.sit.box.face = c.heading; } },
    say(text, sec = 2.6) { c.speech = { text, until: c._t + sec }; speakUntil = c._t + Math.min(sec, 0.25 + text.length * 0.16); },
    emote(sym, sec = 2) {
      const name = ALIAS[sym] || sym; c.emoteSym = { sym: name, until: c._t + sec };
      if (!icon) { icon = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false, depthTest: false })); icon.renderOrder = 30; root.add(icon); }
      icon.material.map = Old.iconTex(name); icon.material.needsUpdate = true; icon.visible = true; iconT = 0; iconDur = sec;
    },
    pet(sec = 2.2) { loud = sec + 1; holdWork(sec + 0.6); ctl.petStart(); c.emote('heart', sec); react = { until: c._t + sec, done() { ctl.petEnd(); } }; },
    bonk() {
      loud = 3; holdWork(3.2); ctl.trigger('hit'); c.emote('sweat', 2.4); c.say(['嗚…', '好痛…', '我會改進的…'][Math.floor(Math.random() * 3)], 2);
      const base = c._base, until = c._until; c._until = 0; apply('sulk'); react = { until: c._t + 2.6, done() { c._until = until; apply(base); } };
    },
    feed() {
      loud = 4; holdWork(5); const base = c._base; c._until = 0; apply('eat'); c.emote('note', 1.2);
      react = { until: c._t + 3.2, done() { apply(base); ctl.trigger('happy'); c.emote('heart', 1.6); c.say(['好吃！', '謝謝～', '還要！'][Math.floor(Math.random() * 3)], 1.6); } };
    },
    grab() { c.stop(false); c._rising = false; if (c._seat) { c._seat = null; ctl.sit = null; } c._held = true; c._until = 0; react = null; loud = 9; apply('idle'); const b = ctl.body; ctl.grab(b.x, b.y + 0.3, b.z); hist.length = 0; },
    dragTo(x, y, z) { ctl.grab(x / s, y / s, z / s); loud = 6; hist.push([c._t, x, y, z]); if (hist.length > 8) hist.shift(); },
    release() {
      if (!c._held) return; let vx = 0, vy = 0, vz = 0; const n = hist.length;
      if (n >= 2) { const a = hist[Math.max(0, n - 4)], b = hist[n - 1], dt = Math.max(0.03, b[0] - a[0]); vx = (b[1] - a[1]) / dt / s; vy = (b[2] - a[2]) / dt / s; vz = (b[3] - a[3]) / dt / s; }
      ctl.release(vx * 0.9, vy * 0.9, vz * 0.9); c._released = true;
    },
    setVisible(v) { root.visible = v; },
    lookAt(v) { ctl.lookAt(v ? { x: v.x / s, y: v.y / s, z: v.z / s } : null); },
    pause(on) { c._pause = !!on; if (on) ctl.stop(); },
    swivel(yaw) { if (!(c._seat && ctl.sit)) return false; ctl.sit.box.face = yaw == null ? c._seat.face : yaw; return true; },
    perk(sec = 1.1) { ctl.trigger('happy'); },
    eye(out) { const y = (ctl.body.y + eyeY) * s, f = front * 0.7 * s, yaw = root.rotation.y; return out.set(root.position.x + Math.sin(yaw) * f, y, root.position.z + Math.cos(yaw) * f); },
    hideFromCam(on) { const L = on ? 1 : 0; root.traverse(o => { if (o.layers.mask !== (1 << L)) o.layers.set(L); }); c._hidCam = !!on; },
    dispose() { ch.dispose(); if (cushion) { cushion.geometry.dispose(); cushion.material.dispose(); } if (riser) riser.traverse(m => { if (m.isMesh) { m.geometry.dispose(); m.material.dispose(); } }); if (icon) icon.material.dispose(); root.removeFromParent(); },
  };
  const hist = [];
  function holdWork(sec) { c.workAt = Math.max(c.workAt || 0, c._t + sec); }
  function place(x, z) { ctl.reset(x / s, z / s, ctl.body.yaw); root.position.set(x, 0, z); }
  function dropped() { c._held = false; c._released = false; c._seat = null; c.heading = ctl.body.yaw; if (c.onDrop) c.onDrop(c); }
  function setLod(l) { lod = l; ch.setFar(l === 2); for (const k in slot) if (slot[k]) slot[k].visible = l < 2; for (const w of worn) w.obj.visible = l < 2; if (cherry) cherry.visible = l < 2; }

  // ── 移動：把舊介面的「路徑／外部速度」轉成控制器的移動意圖
  function drive(dt) {
    const b = ctl.body;
    if (c._held || ctl.state === 'held') return;
    if (c._rising) { if (ctl.state !== 'sit') { c._rising = false; ctl.stop(); } return; }
    if (c._seat) { if (ctl.sit && ctl.sit.sub === 'seated' && !c._seated) { c._seated = true; seated(); } return; }
    c._seated = false;
    if (c._path) { if (c._pause) { ctl.stop(); ctl.faceTo(c.heading); return; } pathStep(dt); return; }
    if (c._drive) {
      const d = c._drive, sp = Math.hypot(d.vx, d.vz);
      if (d.fx || d.fz) c.heading = Math.atan2(d.fx, d.fz); else if (sp > 0.01) c.heading = Math.atan2(d.vx, d.vz);
      if (sp > 0.02) { const run = sp > walkV * 1.35; ctl.setMove(d.vx, d.vz, clamp(sp / (run ? runV : walkV), 0.2, 1), run); } else { ctl.stop(); ctl.faceTo(c.heading); }
      return;
    }
    if (ctl.state === 'idle' || ctl.state === 'land') { ctl.stop(); ctl.faceTo(c.heading); }
  }
  function pathStep(dt) {
    const p = { x: ctl.body.x * s, z: ctl.body.z * s }, tgt = c._path[c._pi]; let dx = tgt.x - p.x, dz = tgt.z - p.z; const dist = Math.hypot(dx, dz);
    if (dist < 0.12) { c._pi++; if (c._pi >= c._path.length) c.stop(true); return; }
    dx /= dist; dz /= dist; let vx = dx * c._speed, vz = dz * c._speed, slow = 1; c._ghost = Math.max(0, c._ghost - dt);
    if (env.separation && c._ghost <= 0 && !spec.pet) { const q = env.separation(c, dx, dz); vx += q.x; vz += q.z; slow = q.slow ?? 1; }
    const sp = Math.min(c._speed * slow, dist / Math.max(dt, 1e-3)), vl = Math.hypot(vx, vz) || 1; vx = vx / vl * sp; vz = vz / vl * sp;
    if (env.isFree && !env.isFree(p.x + vx * dt, p.z + vz * dt)) { vx = dx * sp; vz = dz * sp; }
    const prog = ctl.body.speed * s * dt; if (prog < c._speed * dt * 0.2 && ctl.state !== 'idle') { c._stuck += dt; if (c._stuck > 1.2) { c._ghost = 1.2; c._stuck = 0; } } else c._stuck = Math.max(0, c._stuck - dt);
    c.heading = Math.atan2(vx, vz); const run = sp > walkV * 1.35;
    ctl.setMove(vx, vz, clamp(sp / (run ? runV : walkV), 0.25, 1), run);
  }
  function step(dt) {
    root.position.set(0, 0, 0); root.rotation.set(0, 0, 0); root.scale.setScalar(1); root.updateMatrixWorld(true);
    ctl.update(dt);
    const p = ch.root.position, yaw = ch.root.rotation.y, py = p.y;
    root.position.set(p.x * s, 0, p.z * s); root.rotation.y = yaw; root.scale.setScalar(s); ch.root.position.set(0, py, 0); ch.root.rotation.y = 0;
    const bd = ctl.body; inner.vel.set(bd.vx * s, bd.vy * s, bd.vz * s); inner.pos.set(bd.x, bd.y, bd.z); c.lift = py * s; root.updateMatrix(); space.matrix.copy(root.matrix).invert(); root.updateMatrixWorld(true);
  }
  // 動作姿勢疊加：在控制器輸出的骨頭旋轉上加增量（站著或坐著、沒在走路時才套；走路／空中／被抓時由控制器完全負責）
  const POSE_OK = new Set(['idle', 'sit', 'land']);
  function applyPose(t) {
    const st = ctl.state; inner.poseT = (t - poseT0); const p = ctl._p; if (!p) return;
    let name = ACTS[c.action]?.pose; if (c.action === 'sleep' && st !== 'sleep') name = 'doze';
    const calm = POSE_OK.has(st) && !(st === 'sit' && ctl.sit && ctl.sit.sub !== 'seated') && !ctl.overlay && !ctl.pet.on, ex = {};
    if (name && calm && POSES[name]) Object.assign(ex, POSES[name](t - poseT0));
    // 坐穩了：尾巴往身側擺開（身體超出椅背前緣的物種），不頂椅背
    if (st === 'sit' && ctl.sit && ctl.sit.sub === 'seated' && c._backExt > (spec.isCeo ? 0.25 : 0.215) + 0.24) ex.tail = [0, 1.25, 0];
    const bs = Object.keys(ex); if (!bs.length) return;
    for (const bn of bs) { const e = ex[bn], ix = IDX[bn + '.rx']; if (ix === undefined) continue; ch.rot(bn, p[ix] + e[0], p[ix + 1] + e[1], p[ix + 2] + e[2]); }
    ch.model.updateMatrixWorld(true);
  }
  // 坐著的收尾：尾巴往身側擺開（不頂椅背）；被抓／站起來後由控制器自己恢復
  function seated() { }
  function speakLip(t) { if (ch.face) ch.face.talk = t < speakUntil ? 0.3 + 0.3 * Math.abs(Math.sin(t * 14)) : 0; }

  // ── 道具：跟著手（有手的物種）或飄在身前
  const hasHands = look.species !== 'pudding';
  function props(t) {
    if (!slot.A && !slot.L && !slot.R) return; const bob = Math.sin(t * 2.3) * 0.012, hl = hasHands ? ch.boneWorld('hand.L') : null, hr = hasHands ? ch.boneWorld('hand.R') : null;
    const fr = front + 0.12, my = mouthY;
    const put = (m, x, y, z) => m.position.set(x, y, z);
    if (slot.A) { const m = slot.A; if (hasHands) put(m, 0, (hl.y + hr.y) / 2 + 0.03, Math.max(hl.z, hr.z) + 0.06); else put(m, 0, my - 0.12 + bob, fr + 0.1); m.rotation.set(ACTS[c.action]?.pose === 'present' ? 0.35 : 0, 0, 0); }
    if (slot.L) { const m = slot.L; if (hasHands) put(m, hl.x * 0.7, hl.y + 0.04, hl.z + 0.07); else put(m, -0.1, my - 0.14 + bob, fr + 0.1); m.rotation.set(0, 0, 0); }
    if (slot.R) {
      const m = slot.R, ty = slotType.R; if (hasHands) put(m, hr.x * 0.7, hr.y + (ty === 'pen' ? 0.05 : 0.045), hr.z + 0.07); else put(m, 0.2, my - 0.1 + bob, fr + 0.06);
      m.rotation.set(0, ty === 'pen' ? -0.5 : 0, ty === 'phone' ? 0.25 : 0, 'YXZ');
    }
  }
  function setSlot(kk, type) {
    if (slotType[kk] === (type || '')) return; slotType[kk] = type || '';
    if (slot[kk]) { slot[kk].removeFromParent(); slot[kk] = null; }
    if (type) { slot[kk] = Old.propMesh(type); slot[kk].visible = lod < 2; ch.root.add(slot[kk]); }
  }
  function apply(name) {
    c.action = name; const a = ACTS[name] || {}; poseT0 = c._t; setSlot('A', a.A); setSlot('L', a.L); setSlot('R', a.R);
    if (name === 'sleep') { if (!c._seat && ctl.state !== 'sleep' && !c._held) { ctl.sleep(); } ctl.setExpression('sleep'); return; }
    if (ctl.state === 'sleep') ctl.wake(); if (ctl.exprOverride === 'sleep') ctl.setExpression(EXPR[c.expression] ?? null);
    if (name === 'angry') { ctl.trigger('angry'); }
    if (name === 'wave' && !c._seat) ctl.trigger('happy');
  }

  // ── 坐下：椅子座面抬高／坐墊（與舊系統相同的規則：嘴要高過桌面；薄墊一塊、厚就換一張高一點的椅面），座面用控制器的方塊
  const CUSHION_MAX = 0.12; let cushion = null, riser = null, poleM = null, padM = null, _cushH = -1, _chairCol = null;
  const seatMat = () => new THREE.MeshStandardMaterial({ color: new THREE.Color(spec.color || '#ffd9b0').lerp(new THREE.Color('#ffffff'), 0.35), roughness: 0.9 });
  function sampleChair(seat) {
    const out = { seat: null, pole: null }, sc = root.parent; if (!sc) return out; const v = new V3();
    sc.traverse(o => { if (!o.isMesh || !o.geometry || !o.geometry.attributes.color || (out.seat && out.pole)) return; const g = o.geometry; if (!g.boundingBox) g.computeBoundingBox();
      const P = g.attributes.position, C = g.attributes.color; o.updateWorldMatrix(true, false); const bb = g.boundingBox.clone().applyMatrix4(o.matrixWorld); if (seat.x < bb.min.x - 0.3 || seat.x > bb.max.x + 0.3 || seat.z < bb.min.z - 0.3 || seat.z > bb.max.z + 0.3) return;
      for (let i = 0; i < P.count; i++) { v.fromBufferAttribute(P, i).applyMatrix4(o.matrixWorld); const dx = v.x - seat.x, dz = v.z - seat.z, d = Math.hypot(dx, dz);
        if (!out.seat && d > 0.2 && d < 0.3 && v.y > 0.33 && v.y < 0.4) out.seat = new THREE.Color().fromBufferAttribute(C, i);
        else if (!out.pole && d < 0.05 && v.y > 0.06 && v.y < 0.345) out.pole = new THREE.Color().fromBufferAttribute(C, i); if (out.seat && out.pole) break; } });
    return out;
  }
  function seatY(seat) {
    const base = Math.max(0, seat.y - 0.04), chair = seat.y > 0.405 && seat.y < 0.435; let boost = chair ? clamp(0.93 - (mouthY * s + base), 0, 0.27) : 0; if (boost < 0.03) boost = 0;
    const high = boost > CUSHION_MAX, P = seatPos(seat);
    if (boost && !high) {
      if (!cushion) { cushion = new THREE.Mesh(KG.cyl(0.23, boost, 0.03, 20), seatMat()); cushion.userData.prop = 'cushion'; space.add(cushion); _cushH = boost; }
      if (Math.abs(_cushH - boost) > 1e-3) { cushion.geometry = KG.cyl(0.23, Math.max(boost, 0.02), Math.min(0.03, boost * 0.45), 20); _cushH = boost; }
      cushion.position.set(seat.x + (P.x - seat.x) * 0.6, base, seat.z + (P.z - seat.z) * 0.6);
    }
    if (high) {
      if (!riser) {
        _chairCol ||= sampleChair(seat); const R0 = spec.isCeo ? 0.27 * 1.15 + 0.012 : 0.27 + 0.012;
        riser = new THREE.Group(); poleM = new THREE.Mesh(KG.cyl(0.045, 1, 0.01, 10), new THREE.MeshStandardMaterial({ color: _chairCol.pole || new THREE.Color('#7d8490'), roughness: 0.82 }));
        padM = new THREE.Mesh(KG.cyl(R0, 0.11, 0.045, 24), new THREE.MeshStandardMaterial({ color: _chairCol.seat || seatMat().color, roughness: 0.82 }));
        riser.add(poleM, padM); riser.userData.prop = 'cushion'; space.add(riser);
      }
      const bot = base + boost - 0.11, pl = Math.max(0.001, bot + 0.01 - (seat.y - 0.01));
      padM.position.y = boost - 0.11; poleM.position.y = seat.y - 0.01 - base; poleM.scale.set(1, pl, 1); riser.position.set(seat.x, base, seat.z);
    }
    c._boost = boost; c._lift = high ? boost : 0; return base + boost;
  }
  // 坐下的位置：身體（含尾巴、耳）超出椅背前緣的，往前坐一點（最多 0.2 公尺）；後緣用目前姿態的外框量一次
  let _backExt = null;
  function seatPos(seat) {
    if (_backExt == null) {
      ch.resetPose(); ch.model.updateMatrixWorld(true); const inv = new THREE.Matrix4().copy(ch.root.matrixWorld).invert(), m4 = new THREE.Matrix4(), v = new V3(); let mn = 0;
      for (const o of [ch.body]) { const P = o.geometry.attributes.position, st = Math.max(1, Math.floor(P.count / 3000)); m4.multiplyMatrices(inv, o.matrixWorld); for (let i = 0; i < P.count; i += st) { v.fromBufferAttribute(P, i).applyMatrix4(m4); if (v.z < mn) mn = v.z; } }
      _backExt = -mn * s;
    }
    const fwd = clamp(_backExt - (spec.isCeo ? 0.25 : 0.215), 0, 0.24); c._backExt = _backExt; c._seatFwd = fwd;
    return { x: seat.x + Math.sin(seat.face) * fwd, z: seat.z + Math.cos(seat.face) * fwd };
  }
  function setSeatBox(seat, sy, SP) {
    world.boxes.length = 0; world.addBox({ id: 'seat', cx: SP.x / s, cz: SP.z / s, hx: 0.24 / s, hz: 0.24 / s, y0: 0, y1: sy / s, face: seat.face, seat: true });
  }
  function seatInstant(seat, sy, SP) {
    ctl.reset(SP.x / s, SP.z / s, seat.face); const b = ctl.body, box = world.box('seat'); b.y = box.y1; b.supportY = box.y1; b.grounded = true; b.groundId = 'seat'; b.ignoreH.clear();
    ctl.go('sit', 'instant'); const d = ctl.P.sit.standoff; ctl.sit = { id: 'seat', box, sub: 'seated', t: 0, S: { x: box.cx + Math.sin(box.face) * d, z: box.cz + Math.cos(box.face) * d } }; ctl.clip = null; ctl.stateT = 0;
    root.position.set(SP.x, 0, SP.z); c.heading = seat.face; c._seated = true; apply(c.action);
  }
  c.resetPose = () => ch.resetPose();
  ctl.update(0.05); step(0); apply('idle');
  return c;
}

