// ════════════════════════════════════════════════════════════════════════
// 角色介面（佔位版）—— 之後換正式角色時，只要另一個模組匯出同名的 createCharacter 即可。
// world.html?char=<模組路徑> 可以在不改場景程式的情況下換掉（見 main.js 的 loadCharacterModule）。
//
// createCharacter(spec, env) → character
//   spec：{ id 職稱代號, nick 暱稱, zh 中文職稱, race 種族, dept 部門代號, color 部門色, isCeo, lead }
//   env ：{ isFree(x,z) 這一點能不能站, separation(character) → {x,z} 與別人錯身用的推力 }（場景提供，可不理會）
//
// character 必須有：
//   object3D            THREE.Object3D；原點在腳底，rotation.y=0 時面朝 +z
//   spec                原樣保留
//   radius              碰撞半徑（公尺）
//   height              頭頂高度（名牌與泡泡的位置）
//   state               'stand' | 'walk' | 'sit'（唯讀）
//   update(dt, t)       每幀呼叫；dt 秒、t 累計秒
//   setAction(name, opts?)      動作。持續型：idle type read note listen sleep think；
//                               一次型（做完回到原本的持續動作，opts.duration 秒）：talk nod shake raise cheer clap angry wave drink
//   setExpression(name) 表情：neutral happy angry surprised sad think awkward proud
//   walkTo(path, opts?) 沿路徑走；path=[{x,z}…]；opts.speed 公尺／秒；回傳 Promise<boolean>（true 走到、false 被打斷）
//   stop()              停止走路
//   sitAt(seat)         坐到座位 {x,y,z,face}；face 是朝向角
//   standAt(x,z,face?)  站到某一點
//   faceTo(x,z)         轉向某一點
//   say(text, sec?)     說話；只記錄在 character.speech={text,until}，泡泡由場景的標籤層畫
//   emote(symbol, sec?) 頭上符號；記錄在 character.emoteSym={sym,until}
//   setVisible(bool)
//   dispose()
// 場景只會用到上面這些；正式角色可以自己多做骨架、表情貼圖、手上的道具。
// ════════════════════════════════════════════════════════════════════════
import { THREE, G, Part, MAT, shade } from './kit.js';

const EARS = [
  [/貓頭鷹|狐|狸|柴犬|松鼠|獵豹|蝙蝠/, 'point'], [/兔/, 'long'], [/倉鼠|天竺鼠|雪怪|獸人|哥布林|地精/, 'round'],
  [/機器人|機械|外星/, 'antenna'], [/天使/, 'halo'], [/龍|石像鬼/, 'horn'], [/精靈|妖精|仙子/, 'elf'], [/幽靈|史萊姆/, 'blob']
];
const EXPR_SYM = { happy: '♪', angry: '怒', surprised: '!', sad: '…', think: '?', awkward: '汗', proud: '☆' };
const ONE_SHOT = { talk: 2.2, nod: 1.2, shake: 1.2, raise: 1.6, cheer: 1.8, clap: 1.6, angry: 1.8, wave: 1.4, drink: 2.4 };

function hueShift(hex, seed) {
  const c = new THREE.Color(hex), hsl = {}; c.getHSL(hsl);
  c.setHSL((hsl.h + (seed % 7 - 3) * 0.012 + 1) % 1, Math.min(0.9, hsl.s * 1.05), Math.min(0.8, hsl.l * (0.94 + (seed % 5) * 0.02)));
  return '#' + c.getHexString();
}

export function createCharacter(spec, env = {}) {
  let seed = 0; for (const ch of spec.id) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
  const col = spec.isCeo ? '#ffb057' : hueShift(spec.color || '#bfe0f2', seed), belly = shade(col, 0.6), dark = shade(col, -0.25);
  const kind = (EARS.find(([re]) => re.test(spec.race || '')) || [0, 'tuft'])[1];
  const P = new Part(), k = spec.isCeo ? 1.12 : (spec.lead ? 1.04 : 0.94 + (seed % 4) * 0.025);
  // 身體：圓滾的膠囊＋淺色肚子
  P.add(G.cap(0.27, 0.26, 12), kind === 'blob' ? shade(col, 0.35) : col, 0, 0.4, 0);
  P.sph(belly, 0.2, 0, 0.3, 0.115, 1, 1.05, 0.7);
  // 臉：眼睛、高光、腮紅、小嘴
  for (const s of [-1, 1]) {
    P.sph('#4a3a36', 0.042, s * 0.1, 0.56, 0.235, 1, 1.25, 0.6); P.sph('#ffffff', 0.014, s * 0.1 + 0.012, 0.578, 0.262);
    P.sph('#ff9aa8', 0.045, s * 0.175, 0.49, 0.2, 1.1, 0.65, 0.4);
    P.sph(dark, 0.075, s * 0.275, 0.36, 0.03, 0.8, 1.25, 0.85);
    if (kind !== 'blob') P.sph(dark, 0.085, s * 0.11, 0.045, 0.05, 1, 0.55, 1.35);
  }
  P.sph('#c46a6a', 0.022, 0, 0.5, 0.262, 1.4, 0.7, 0.5);
  // 種族特徵（很簡單的耳朵、角、天線，只是讓 44 個人看得出不同）
  const top = 0.8;
  if (kind === 'point') for (const s of [-1, 1]) { P.sph(col, 0.09, s * 0.15, top - 0.02, 0, 0.7, 1.25, 0.55); P.sph('#ffd9df', 0.05, s * 0.15, top - 0.02, 0.03, 0.6, 1.1, 0.4); }
  else if (kind === 'long') for (const s of [-1, 1]) P.add(G.sph(0.07), col, s * 0.1, top + 0.12, 0, 0, 0, s * -0.18, 0.75, 2.6, 0.6);
  else if (kind === 'round') for (const s of [-1, 1]) P.sph(col, 0.085, s * 0.21, top - 0.06, 0, 1, 1, 0.6);
  else if (kind === 'antenna') { P.cyl('#c9ccd2', 0.014, 0.14, 0, top - 0.02, 0, 0.004); P.sph('#ff9f7a', 0.045, 0, top + 0.15, 0); }
  else if (kind === 'halo') P.add(G.torus(0.14, 0.022), '#ffd766', 0, top + 0.1, 0, 0, Math.PI / 2);
  else if (kind === 'horn') for (const s of [-1, 1]) P.add(G.sph(0.05), '#fff3d6', s * 0.13, top + 0.01, 0, 0, 0, s * -0.35, 0.7, 1.7, 0.7);
  else if (kind === 'elf') for (const s of [-1, 1]) P.add(G.sph(0.06), col, s * 0.29, 0.6, 0, 0, 0, s * -0.5, 1.7, 0.6, 0.45);
  else if (kind === 'tuft') { P.sph(dark, 0.06, 0, top + 0.01, 0, 1, 0.9, 1); P.sph(dark, 0.04, 0.05, top + 0.05, 0); }
  if (spec.isCeo) { P.add(G.cyl(0.11, 0.07, 0.015, 14, 0.13), '#ffd766', 0, top - 0.015, 0); for (let i = 0; i < 5; i++) P.sph('#ffd766', 0.032, Math.cos(i * 1.2566) * 0.12, top + 0.07, Math.sin(i * 1.2566) * 0.12); P.sph('#ff8f8f', 0.028, 0, top + 0.03, 0.125); }

  const mesh = P.mesh(MAT.solid); mesh.receiveShadow = false; mesh.castShadow = false;
  const pivot = new THREE.Group(); pivot.add(mesh); pivot.scale.setScalar(k);
  const root = new THREE.Group(); root.add(pivot); root.userData.character = true;

  const c = {
    object3D: root, spec, radius: 0.27, height: 0.92 * k, state: 'stand', heading: 0,
    speech: null, emoteSym: null, expression: 'neutral', action: 'idle', busy: false, seatY: 0,
    _base: 'idle', _until: 0, _t: 0, _phase: (seed % 100) / 16, _path: null, _pi: 0, _speed: 1.6, _resolve: null, _stuck: 0, _ghost: 0,
    update(dt, t) {
      c._t = t;
      if (c._until && t > c._until) { c._until = 0; c.action = c._base; }
      if (c.speech && t > c.speech.until) c.speech = null;
      if (c.emoteSym && t > c.emoteSym.until) c.emoteSym = null;
      if (c._path) step(dt);
      // 朝向平滑轉
      let d = c.heading - root.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); root.rotation.y += d * Math.min(1, dt * 10);
      pose(t + c._phase);
    },
    setAction(name, opts = {}) {
      if (ONE_SHOT[name]) { c.action = name; c._until = c._t + (opts.duration || ONE_SHOT[name]); }
      else { c._base = name; if (!c._until) c.action = name; }
    },
    setExpression(name) { c.expression = name; if (EXPR_SYM[name]) c.emote(EXPR_SYM[name], 2.2); },
    walkTo(path, opts = {}) {
      c.stop(false);
      if (!path || path.length < 2) return Promise.resolve(true);
      if (c.state === 'sit') { root.position.y = 0; }
      c._path = path; c._pi = 1; c._speed = opts.speed || 1.6; c.state = 'walk'; c._stuck = 0;
      return new Promise(res => { c._resolve = res; });
    },
    stop(ok = false) { if (c._path) { c._path = null; c.state = 'stand'; const r = c._resolve; c._resolve = null; if (r) r(ok); } },
    sitAt(seat) { c.stop(false); root.position.set(seat.x, 0, seat.z); c.seatY = seat.y - 0.16 * k; c.heading = seat.face; c.state = 'sit'; },
    standAt(x, z, face) { c.stop(false); root.position.set(x, 0, z); c.seatY = 0; if (face != null) c.heading = face; c.state = 'stand'; },
    faceTo(x, z) { const dx = x - root.position.x, dz = z - root.position.z; if (dx * dx + dz * dz > 1e-4) c.heading = Math.atan2(dx, dz); },
    say(text, sec = 2.6) { c.speech = { text, until: c._t + sec }; c.setAction('talk', { duration: Math.min(sec, 2.4) }); },
    emote(sym, sec = 2) { c.emoteSym = { sym, until: c._t + sec }; },
    setVisible(v) { root.visible = v; },
    dispose() { mesh.geometry.dispose(); root.removeFromParent(); }
  };

  function step(dt) {
    const p = root.position, tgt = c._path[c._pi]; let dx = tgt.x - p.x, dz = tgt.z - p.z; const dist = Math.hypot(dx, dz);
    if (dist < 0.1) { c._pi++; if (c._pi >= c._path.length) { p.x = tgt.x; p.z = tgt.z; c.stop(true); } return; }
    dx /= dist; dz /= dist;
    let vx = dx * c._speed, vz = dz * c._speed, slow = 1;
    c._ghost = Math.max(0, c._ghost - dt);
    if (env.separation && c._ghost <= 0) { const s = env.separation(c, dx, dz); vx += s.x; vz += s.z; slow = s.slow ?? 1; }
    const sp = Math.min(c._speed * slow, dist / dt); const vl = Math.hypot(vx, vz) || 1; vx = vx / vl * sp; vz = vz / vl * sp;
    let nx = p.x + vx * dt, nz = p.z + vz * dt;
    if (env.isFree && !env.isFree(nx, nz)) { nx = p.x + dx * sp * dt; nz = p.z + dz * sp * dt; }
    const prog = (nx - p.x) * dx + (nz - p.z) * dz;
    if (prog < c._speed * dt * 0.25) { c._stuck += dt; if (c._stuck > 0.9) { c._ghost = 1.2; c._stuck = 0; } } else c._stuck = Math.max(0, c._stuck - dt);
    p.x = nx; p.z = nz; c.heading = Math.atan2(vx, vz);
  }

  function pose(t) {
    let y = c.state === 'sit' ? c.seatY : 0, sy = 1, sxz = 1, rx = 0, rz = 0, ry = 0; const a = c.state === 'walk' ? 'walk' : c.action;
    const S = Math.sin, A = Math.abs;
    switch (a) {
      case 'walk': { const f = 6 + c._speed * 2.2; y += A(S(t * f)) * 0.07; rz = S(t * f) * 0.09; sy = 1 + S(t * f * 2) * 0.03; rx = c._speed > 2.4 ? 0.14 : 0.04; break; }
      case 'type': rx = 0.1; y += A(S(t * 16)) * 0.008; rz = S(t * 3.1) * 0.02; break;
      case 'read': rx = 0.2; rz = S(t * 1.3) * 0.03; break;
      case 'note': rx = 0.16 + S(t * 9) * 0.02; break;
      case 'listen': rx = S(t * 1.1) * 0.03; rz = S(t * 0.7) * 0.03; break;
      case 'sleep': rz = 0.22; sy = 1 + S(t * 1.4) * 0.03; break;
      case 'think': rz = 0.14 + S(t * 1.2) * 0.03; break;
      case 'talk': sy = 1 + A(S(t * 9)) * 0.06; rz = S(t * 4.5) * 0.06; y += A(S(t * 9)) * 0.015; break;
      case 'nod': rx = 0.1 + S(t * 9) * 0.14; break;
      case 'shake': ry = S(t * 10) * 0.4; break;
      case 'raise': sy = 1.14; y += 0.05 + A(S(t * 6)) * 0.03; break;
      case 'cheer': y += A(S(t * 8)) * 0.2; sy = 1 + S(t * 16) * 0.06; break;
      case 'clap': sxz = 1 + A(S(t * 14)) * 0.07; sy = 1 - A(S(t * 14)) * 0.04; break;
      case 'angry': rz = S(t * 38) * 0.05; sxz = 1.06; rx = 0.1; break;
      case 'wave': rz = S(t * 10) * 0.16; break;
      case 'drink': rx = -0.16 + S(t * 2.6) * 0.08; break;
      default: sy = 1 + S(t * 2) * 0.018;
    }
    sxz = sxz * (1 + (1 - sy) * 0.5);
    root.position.y = y; pivot.rotation.set(rx, ry, rz); pivot.scale.set(k * sxz, k * sy, k * sxz);
  }
  return c;
}
