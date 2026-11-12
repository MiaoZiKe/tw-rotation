// ════════════════════════════════════════════════════════════════════════
// 辦公室場景用的角色工廠：createCharacter(spec, env) —— 介面照 site/office/world/js/character.js 開頭那份約定。
// 用法：world.html?char=../../play/office_character.js （場景程式不用改）
//
// spec 除了場景原本的 { id, nick, zh, race, dept, color, isCeo, lead }，還可以直接指定外觀（都可省略）：
//   species   物種代號：mochi bean robo cloud flame cactus mug ghost bird octo star calc pudding seal bulb
//   pal       配色（編號 0~3 或名稱，例如 '草莓牛奶'）
//   hue       色相微調（-0.08 ~ 0.08）
//   acc       配件陣列：glasses hat bow tie scarf badge（物種戴不了的會自動略過）
//   accColor  配件顏色編號 0~5
// 沒指定時：依 race 的關鍵字挑物種，挑不到就用 id 的雜湊平均分配；配色、配件也由雜湊決定，
// 所以同一個 id 每次長得一樣。lead 會打領帶，CEO 戴帽子＋領帶＋識別證。
// 完整說明見 docs/ai_office/character_factory.md
// ════════════════════════════════════════════════════════════════════════
import * as THREE from 'three';
import { Character } from './character.js';
import { SPECIES, SPECIES_IDS, canWear } from './species.js';
import { stubWorld, stubFx } from './lite.js';

const RACE = [[/機器|機械|仿生/, 'robo'], [/幽靈|鬼|靈/, 'ghost'], [/史萊姆|果凍|布丁/, 'pudding'], [/龍|火|焰/, 'flame'], [/鳥|貓頭鷹|企鵝|雞|鴨/, 'bird'], [/章魚|外星|烏賊/, 'octo'], [/精靈|妖精|仙子|天使|星/, 'star'], [/樹|植物|花|仙人掌/, 'cactus'], [/豆|芽|哥布林|地精/, 'bean'], [/海豹|海獺|水獺|鯨/, 'seal'], [/雲|雪|冰/, 'cloud'], [/倉鼠|天竺鼠|兔|貓|狗|柴|狐|狸|熊|鼠/, 'mochi']];
const EXPR = { neutral: null, happy: 'happy', angry: 'angry', surprised: 'surprised', sad: 'sad', think: 'look', awkward: 'shy', proud: 'smug' };
const ONE_SHOT = { talk: 2.2, nod: 1.2, shake: 1.2, raise: 1.6, cheer: 1.8, clap: 1.6, angry: 1.8, wave: 1.4, drink: 2.4 };
const hash = (s) => { let h = 2166136261; for (const ch of String(s)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619) >>> 0; return h; };

export function lookFor(spec) {
  const h = hash(spec.id || spec.nick || 'x'), cfgId = spec.species && SPECIES[spec.species] ? spec.species : ((RACE.find(([re]) => re.test(spec.race || '')) || [0, SPECIES_IDS[h % SPECIES_IDS.length]])[1]);
  const cfg = SPECIES[cfgId], pool = ['glasses', 'bow', 'scarf', 'badge', 'hat'].filter(a => canWear(cfg, a));
  let acc = spec.acc; if (!acc) { acc = []; if (pool.length && (h >> 3) % 3) acc.push(pool[(h >> 5) % pool.length]); if (spec.lead || spec.isCeo) acc.push('tie'); if (spec.isCeo) acc.push('hat', 'badge'); }
  return { species: cfgId, pal: spec.pal ?? (h >> 9) % 4, hue: spec.hue ?? (((h >> 12) % 9) - 4) * 0.008, acc: [...new Set(acc)], accColor: spec.accColor ?? (h >> 16) % 6 };
}

export function createCharacter(spec, env = {}) {
  const root = new THREE.Group(), space = new THREE.Group(); root.add(space); space.matrixAutoUpdate = false; root.userData.character = true;
  const look = lookFor(spec), ch = new Character(look, null, stubWorld(), env.fx || stubFx, { space, faceSize: 256 });
  ch.ext = { vx: 0, vz: 0, yaw: 0, y: 0 }; ch.pos.set(0, 0, 0);
  const camP = new THREE.Vector3(0, 6, 10), aenv = { look: null, cam: camP, idleScale: 0 }, ctl = { mx: 0, mz: 0, run: false, jump: false };
  const c = {
    object3D: root, spec, look, inner: ch, radius: ch.R * 0.85, height: ch.cfg.top + (ch.cfg.floatH || 0) + 0.06, speech: null, emoteSym: null, expression: 'neutral', action: 'idle',
    _base: 'idle', _until: 0, _t: 0, _path: null, _pi: 0, _speed: 1.6, _resolve: null, _stuck: 0, _ghost: 0, heading: 0,
    get state() { return c._path ? 'walk' : ch.mode === 'sit' || (ch.mode === 'sleep' && c._seat) ? 'sit' : 'stand'; },
    update(dt, t) {
      c._t = t; dt = Math.min(dt, 0.05);
      // 場景可能直接改 object3D.position（瞬移），以它為準
      if (Math.abs(root.position.x - ch.pos.x) + Math.abs(root.position.z - ch.pos.z) > 0.5) { ch.pos.x = root.position.x; ch.pos.z = root.position.z; ch.feet.forEach(f => ch.footHome(f, f.p)); ch.hands.forEach(h => h.p.set(ch.pos.x, ch.pos.y + 0.3, ch.pos.z)); }
      if (c._until && t > c._until) { c._until = 0; apply(c._base); }
      if (c.speech && t > c.speech.until) c.speech = null; if (c.emoteSym && t > c.emoteSym.until) c.emoteSym = null;
      if (c._path) step(dt); else { ch.ext.vx = ch.ext.vz = 0; }
      ch.ext.yaw = c.heading;
      if (env.camera) camP.copy(env.camera.position);
      const n = Math.max(1, Math.ceil(dt / (1 / 90))), h = dt / n; for (let i = 0; i < n; i++) ch.step(h, ctl);
      root.position.set(ch.pos.x, 0, ch.pos.z); root.rotation.y = ch.yaw; root.updateMatrix(); space.matrix.copy(root.matrix).invert(); root.updateMatrixWorld(true);
      ch.animate(dt, aenv);
    },
    setAction(name, opts = {}) { if (ONE_SHOT[name]) { c._until = c._t + (opts.duration || ONE_SHOT[name]); apply(name); } else { c._base = name; if (!c._until) apply(name); } },
    setExpression(name) { c.expression = name; const e = EXPR[name]; if (e) ch.emote(e, 1e9); else ch.emo = null; },
    walkTo(path, opts = {}) {
      c.stop(false); if (!path || path.length < 2) return Promise.resolve(true);
      if (ch.mode !== 'normal') { ch.mode = 'normal'; } c._seat = null; ch.ext.y = 0; ch.extPose = null;
      c._path = path; c._pi = 1; c._speed = opts.speed || 1.6; c._stuck = 0; return new Promise(res => { c._resolve = res; });
    },
    stop(ok = false) { if (c._path) { c._path = null; const r = c._resolve; c._resolve = null; ch.ext.vx = ch.ext.vz = 0; if (r) r(ok); } },
    sitAt(seat) { c.stop(false); c._seat = seat; ch.pos.set(seat.x, Math.max(0, seat.y - 0.04), seat.z); ch.ext.y = ch.pos.y; ch.vel.set(0, 0, 0); c.heading = seat.face; ch.yaw = seat.face; ch.mode = 'sit'; ch.modeT = 0; ch.yawTo = seat.face; ch.idleSit = false; root.position.set(seat.x, 0, seat.z); },
    standAt(x, z, face) { c.stop(false); c._seat = null; ch.mode = 'normal'; ch.pos.set(x, 0, z); ch.ext.y = 0; ch.vel.set(0, 0, 0); if (face != null) { c.heading = face; ch.yaw = face; } ch.feet.forEach(f => { ch.footHome(f, f.p); f.planted = true; }); root.position.set(x, 0, z); },
    faceTo(x, z) { const dx = x - ch.pos.x, dz = z - ch.pos.z; if (dx * dx + dz * dz > 1e-4) { c.heading = Math.atan2(dx, dz); if (ch.mode === 'sit') ch.yawTo = c.heading; } },
    say(text, sec = 2.6) { c.speech = { text, until: c._t + sec }; ch.say(text, sec); ch.speech = null; ch.face.talk = 0; ch.speech = { text, t: sec, talk: Math.min(sec, 0.25 + text.length * 0.16) }; },
    emote(sym, sec = 2) { c.emoteSym = { sym, until: c._t + sec }; },
    setVisible(v) { root.visible = v; },
    dispose() { ch.dispose(); root.removeFromParent(); },
  };
  function apply(name) {
    c.action = name; ch.extPose = null;
    if (name === 'sleep') { if (ch.mode !== 'sleep') { const was = ch.mode; ch.mode = 'sleep'; ch.modeT = 0; c._wasSit = was === 'sit'; } return; }
    if (ch.mode === 'sleep') { ch.mode = c._seat ? 'sit' : 'normal'; }
    switch (name) {
      case 'idle': break;
      case 'talk': break;                                   // 嘴型由 say() 帶
      case 'wave': if (ch.mode === 'normal') ch.doAct('wave'); else ch.extPose = 'raise'; ch.speech = null; break;
      case 'shake': if (ch.mode === 'normal') ch.act = { name: 'shake', t: 0, dur: 1.0, f: 0 }; break;
      case 'angry': ch.emote('angry', ONE_SHOT.angry); break;
      default: ch.extPose = name;                           // type read note listen think nod raise clap cheer drink
    }
  }
  function step(dt) {
    const p = ch.pos, tgt = c._path[c._pi]; let dx = tgt.x - p.x, dz = tgt.z - p.z; const dist = Math.hypot(dx, dz);
    if (dist < 0.1) { c._pi++; if (c._pi >= c._path.length) c.stop(true); return; }
    dx /= dist; dz /= dist; let vx = dx * c._speed, vz = dz * c._speed, slow = 1; c._ghost = Math.max(0, c._ghost - dt);
    if (env.separation && c._ghost <= 0) { const s = env.separation(c, dx, dz); vx += s.x; vz += s.z; slow = s.slow ?? 1; }
    const sp = Math.min(c._speed * slow, dist / dt), vl = Math.hypot(vx, vz) || 1; vx = vx / vl * sp; vz = vz / vl * sp;
    if (env.isFree && !env.isFree(p.x + vx * dt, p.z + vz * dt)) { vx = dx * sp; vz = dz * sp; }
    const prog = (vx * dx + vz * dz) * dt; if (prog < c._speed * dt * 0.25) { c._stuck += dt; if (c._stuck > 0.9) { c._ghost = 1.2; c._stuck = 0; } } else c._stuck = Math.max(0, c._stuck - dt);
    ch.ext.vx = vx; ch.ext.vz = vz; c.heading = Math.atan2(vx, vz);
  }
  return c;
}
