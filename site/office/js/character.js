// 角色建模（第二版）：三頭身、立體五官、髮束、軟膠皮膚、有細節的衣服鞋子。全部原創、全部程式生成。
import { THREE, softMat, skinMat, dirSurface, ellipsoid, gradY, limbGeo, loftGeo, ringLoft, sweepGeo, paint, roundedSlab, canvasTex, Spring, sstep, lerp, clamp, gauss, C } from './core.js';
import { Face, makeSurf, makeNose, makeEar } from './face.js';
import { buildHair } from './hair.js';
import { makeSymbol } from './fx.js';
import { buildProps } from './props.js';
import { buildPet } from './pet.js';

const PI = Math.PI;
const V3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
export const mesh = (g, m, cast = true) => { const o = new THREE.Mesh(g, m); o.castShadow = cast; o.receiveShadow = true; return o; };
export const grp = (parent, x = 0, y = 0, z = 0) => { const g = new THREE.Group(); g.position.set(x, y, z); parent && parent.add(g); return g; };
const mix = (a, b, t) => '#' + C(a).lerp(C(b), t).getHexString();
// 幾個控制點之間的平滑內插（Catmull-Rom），放樣輪廓用
const cr = (keys) => (v) => { const n = keys.length - 1, f = clamp(v) * n, i = Math.min(n - 1, Math.floor(f)), t = f - i, p0 = keys[Math.max(0, i - 1)], p1 = keys[i], p2 = keys[i + 1], p3 = keys[Math.min(n, i + 2)]; return p1.map((_, k) => 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t * t * t)); };

const BROWN = { dark: '#2e150c', mid: '#6b3a1c', light: '#b87a40', R: 90, pupilR: 0.56 };
export const SPECS = {
  kai: { name: '阿澈', kind: '人類', role: '工程師', skin: '#ffe1cf', blush: '#ff8f88', iris: BROWN,
    hair: { kind: 'tuft', line: 'short', vol: 0.085, c: '#33344e', hi: '#6a6f9c', rim: 0xdfe6ff }, brow: '#3b3b58',
    top: { type: 'hoodie', c: '#ffb545', c2: '#fff3dc', c3: '#ff7f6e', print: 'star', sleeve: 'short' }, pants: { c: '#5a7cb6', cuff: '#a9c2e6' }, shoes: { c: '#ff7f6e', c2: '#ffffff', sole: '#fffaf2' }, acc: ['backpack'], pack: '#49b7a6' },
  he: { idle: 'clasp', name: '小禾', kind: '人類', role: '企劃', skin: '#f3c3a2', blush: '#f0796c', iris: { dark: '#24140f', mid: '#523220', light: '#9c6a38', R: 90, pupilR: 0.56 }, lashes: true,
    hair: { kind: 'bob', line: 'bob', c: '#7a4631', hi: '#c08055', band: '#ffd24d' }, brow: '#5c3324',
    top: { type: 'vest', c: '#b9a2f2', c2: '#ffffff', c3: '#ffd24d', print: 'argyle', sleeve: 'long' }, pants: { c: '#f1e4d2', cuff: '#fff8ee', plain: true }, shoes: { c: '#b9a2f2', c2: '#ffffff', sole: '#fffaf2' }, acc: ['badge'] },
  mo: { idle: 'hip', name: '阿莫', kind: '人類', role: '設計師', skin: '#c48a64', blush: '#e0694f', iris: { dark: '#1c2a22', mid: '#3e6a4c', light: '#9ccf7e', R: 90, pupilR: 0.56 },
    hair: { kind: 'part', line: 'short', c: '#e3b96e', hi: '#fff0c2', rim: 0xfff6d8 }, brow: '#9a6f3a',
    top: { type: 'jacket', c: '#7fae7a', c2: '#fff6e8', c3: '#ff9c6b', print: 'stripe', sleeve: 'long' }, pants: { c: '#5b5a70', cuff: '#7c7b93' }, shoes: { c: '#ffc24a', c2: '#ffffff', sole: '#fffaf2' }, acc: ['glasses'] },
  cat: { idle: 'one', name: '麻糬', kind: '貓', role: '客服', cat: true, skin: '#ffb766', blush: '#ff8a7a', iris: { dark: '#1f4a30', mid: '#4f9a52', light: '#c9e86e', glow: 'rgba(230,255,160,0.55)' }, sc: 0.95,
    brow: '#d98434', top: { type: 'hoodie', c: '#c3a8f5', c2: '#fff6ff', c3: '#ff9fc0', print: 'fish', sleeve: 'long' }, pants: { c: '#6d6a9c', cuff: '#9a97c9' }, shoes: { c: '#fff1d6', c2: '#ffb766', sole: '#ffffff' }, acc: ['badge'] },
  alien: { name: '啾比', kind: '外星人', role: '研究員', alien: true, skin: '#9fe6c0', blush: '#ff9fc6', iris: { dark: '#0d2b3a', mid: '#1c6a7e', light: '#6fe3d8', R: 104, pupilR: 0.6, glow: 'rgba(150,255,240,0.6)', ring: 'rgba(6,20,30,0.9)' }, sc: 0.92,
    top: { type: 'hoodie', c: '#8cc4ff', c2: '#ffffff', c3: '#ffd24d', print: 'planet', sleeve: 'long' }, pants: { c: '#7a7fb0', cuff: '#a6abd6', plain: true }, shoes: { c: '#b79cff', c2: '#ffffff', sole: '#fff7d6' }, acc: [] },
  ghost: { idle: 'clasp', name: '飄飄', kind: '幽靈', role: '夜班', ghost: true, skin: '#fbf9ff', blush: '#ff9fc0', iris: { dark: '#2b2350', mid: '#5a4aa8', light: '#b3a0ff', glow: 'rgba(210,200,255,0.6)' }, sc: 0.94, acc: ['badge'] },
  pet: { name: '雪球', kind: '天竺鼠', role: '辦公室寵物', pet: true },
};
export const CHAR_IDS = Object.keys(SPECS);

// ───────── 布料與圖案貼圖 ─────────
function weave(c, w, h, a = 0.05, n = 5000) { let s = 3; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647; for (let i = 0; i < n; i++) { c.fillStyle = rnd() > 0.5 ? `rgba(255,255,255,${a * rnd()})` : `rgba(0,0,30,${a * rnd()})`; c.fillRect(rnd() * w, rnd() * h, 1 + rnd() * 3, 1 + rnd() * 2); } }
function drawPrint(c, kind, x, y, s, col, col2) {
  c.save(); c.translate(x, y); c.lineJoin = c.lineCap = 'round';
  if (kind === 'star') { c.fillStyle = col; c.beginPath(); for (let i = 0; i < 10; i++) { const a = -PI / 2 + i * PI / 5, r = i % 2 ? s * 0.48 : s; c.lineTo(Math.cos(a) * r, Math.sin(a) * r); } c.closePath(); c.lineWidth = s * 0.34; c.strokeStyle = col; c.stroke(); c.fill(); c.fillStyle = '#fff'; c.beginPath(); c.arc(-s * 0.28, -s * 0.12, s * 0.1, 0, 7); c.arc(s * 0.28, -s * 0.12, s * 0.1, 0, 7); c.fill(); c.strokeStyle = '#fff'; c.lineWidth = s * 0.09; c.beginPath(); c.arc(0, s * 0.05, s * 0.2, 0.25, PI - 0.25); c.stroke(); }
  else if (kind === 'fish') { c.fillStyle = col; c.beginPath(); c.ellipse(-s * 0.15, 0, s * 0.75, s * 0.48, 0, 0, 7); c.fill(); c.beginPath(); c.moveTo(s * 0.45, 0); c.lineTo(s * 1.05, -s * 0.5); c.lineTo(s * 1.05, s * 0.5); c.closePath(); c.lineWidth = s * 0.16; c.strokeStyle = col; c.stroke(); c.fill(); c.fillStyle = '#fff'; c.beginPath(); c.arc(-s * 0.5, -s * 0.1, s * 0.12, 0, 7); c.fill(); }
  else if (kind === 'planet') { c.fillStyle = col; c.beginPath(); c.arc(0, 0, s * 0.62, 0, 7); c.fill(); c.strokeStyle = col2; c.lineWidth = s * 0.17; c.beginPath(); c.ellipse(0, 0, s * 1.05, s * 0.3, -0.35, 0.25, PI * 2 - 0.9 - 2.2); c.stroke(); c.beginPath(); c.ellipse(0, 0, s * 1.05, s * 0.3, -0.35, PI - 0.55, PI + 0.55); c.stroke(); }
  c.restore();
}
function topTex(t) {
  return canvasTex(512, 512, (c) => {
    c.fillStyle = t.c; c.fillRect(0, 0, 512, 512); const Y = (v) => (1 - v) * 512; // v：0 下襬 → 1 領口；x：256＝正前
    if (t.type === 'hoodie') {
      c.fillStyle = t.c2; c.fillRect(0, Y(0.69), 512, Y(0.47) - Y(0.69)); // 胸前一圈淺色
      c.fillStyle = mix(t.c, '#000000', 0.1); c.fillRect(0, Y(0.705), 512, 3); c.fillRect(0, Y(0.47) - 3, 512, 3);
      drawPrint(c, t.print, 256, Y(0.58), 30, t.c3, t.c);
    } else if (t.type === 'vest') { // 針織背心：V 領露出白襯衫＋一排菱格
      c.fillStyle = t.c2; c.beginPath(); c.moveTo(256 - 70, Y(1)); c.lineTo(256, Y(0.6)); c.lineTo(256 + 70, Y(1)); c.closePath(); c.fill();
      c.strokeStyle = mix(t.c, '#ffffff', 0.45); c.lineWidth = 9; c.beginPath(); c.moveTo(256 - 70, Y(1)); c.lineTo(256, Y(0.6)); c.lineTo(256 + 70, Y(1)); c.stroke();
      c.fillStyle = '#e9e2f5'; for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(256, Y(0.86 - i * 0.085), 4.5, 0, 7); c.fill(); }
      for (let i = -9; i < 10; i++) { const x = 256 + i * 36, y = Y(0.33); c.fillStyle = i % 2 ? t.c3 : '#ffffff'; c.beginPath(); c.moveTo(x, y - 26); c.lineTo(x + 18, y); c.lineTo(x, y + 26); c.lineTo(x - 18, y); c.closePath(); c.fill(); }
      c.strokeStyle = 'rgba(60,30,110,0.07)'; c.lineWidth = 2; for (let x = 0; x < 512; x += 9) { c.beginPath(); c.moveTo(x, Y(0.6)); c.lineTo(x, 512); c.stroke(); }
    } else if (t.type === 'jacket') { // 敞開的外套：中間露出內搭、兩側口袋與車線
      c.fillStyle = t.c2; c.fillRect(256 - 46, 0, 92, 512);
      c.fillStyle = t.c3; for (let i = 0; i < 4; i++) c.fillRect(256 - 46, Y(0.3 + i * 0.16), 92, 16);
      c.strokeStyle = mix(t.c, '#000000', 0.22); c.lineWidth = 3; c.setLineDash([7, 5]);
      for (const s of [-1, 1]) { c.strokeRect(256 + s * 96 - 30, Y(0.42), 60, 62); c.beginPath(); c.moveTo(256 + s * 52, 0); c.lineTo(256 + s * 52, 512); c.stroke(); }
      c.setLineDash([]); c.fillStyle = '#ffe9b0'; for (const s of [-1, 1]) for (let i = 0; i < 3; i++) { c.beginPath(); c.arc(256 + s * 60, Y(0.72 - i * 0.2), 5, 0, 7); c.fill(); }
    }
    weave(c, 512, 512, 0.03, 9000);
  });
}
const TEX = {};
const clothTex = (col, kind = 'plain') => TEX[col + kind] || (TEX[col + kind] = (() => { const t = canvasTex(128, 128, (c) => { c.fillStyle = col; c.fillRect(0, 0, 128, 128); if (kind === 'denim') { c.strokeStyle = 'rgba(255,255,255,0.1)'; c.lineWidth = 1; for (let i = -128; i < 128; i += 4) { c.beginPath(); c.moveTo(i, 0); c.lineTo(i + 128, 128); c.stroke(); } } weave(c, 128, 128, kind === 'denim' ? 0.07 : 0.022, 2500); }); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(3, 3); return t; })());

// 兩端圓頭的肢段：樞紐在上端球心，往 -y；可加布料皺褶（wr）
function tubeLimb(len, r0, r1, o = {}) {
  const q = PI / 2, tot = r0 * q + len + (o.open ? 0 : r1 * q), ct = r0 * q / tot, cb = o.open ? 0 : r1 * q / tot, wr = o.wr ?? 0, f = o.wrF ?? 60;
  return ringLoft((vv) => { const v = 1 - vv;
    if (v < ct) { const a = v / ct * q; return [r0 * Math.cos(a), r0 * Math.sin(a) + 1e-5, r0 * Math.sin(a) + 1e-5]; }
    if (v > 1 - cb) { const a = (v - (1 - cb)) / cb * q; return [-len - r1 * Math.sin(a), r1 * Math.cos(a) + 1e-5, r1 * Math.cos(a) + 1e-5]; }
    const t = (v - ct) / (1 - ct - cb), r = lerp(r0, r1, t) * (1 + (o.bulge ?? 0) * Math.sin(PI * t)); return [-len * t, r, r];
  }, o.rows ?? 30, o.seg ?? 28, { mod: wr ? (vv, a) => { const v = 1 - vv, t = clamp((v - ct) / (1 - ct - cb)), m = sstep(o.wr0 ?? 0.35, (o.wr0 ?? 0.35) + 0.25, t) * (1 - sstep(0.93, 1, t)); return 1 + wr * m * (0.65 * Math.sin(t * f + 2.4 * Math.sin(a + (o.ph ?? 0)) + 1.1 * Math.sin(2 * a)) + 0.35 * Math.sin(t * f * 0.47 + 3 * a + (o.ph ?? 0))); } : null });
}

// ───────── 頭型 ─────────
function headShape(h) {
  const ck = [V3(0.74, -0.5, 0.46).normalize(), V3(-0.74, -0.5, 0.46).normalize()], cn = V3(0, -0.86, 0.5).normalize(), mz = V3(0, -0.36, 0.93).normalize(), ey = [V3(0.42, -0.12, 0.9).normalize(), V3(-0.42, -0.12, 0.9).normalize()];
  return (d, p) => {
    const ry = lerp(h.ryD, h.ryU, sstep(-0.5, 0.5, d.y)), rz = lerp(h.rzB, h.rzF, sstep(-0.5, 0.5, d.z)), rx = h.rx * (1 + (h.topW ?? 0) * sstep(-0.2, 0.8, d.y));
    p.set(d.x * rx, d.y * ry, d.z * rz);
    let b = 0; for (const c of ck) b += gauss(2 - 2 * d.dot(c), 0.44);
    let k = h.cheek * b + h.chin * gauss(2 - 2 * d.dot(cn), 0.3) + (h.muzzle ?? 0) * gauss(2 - 2 * d.dot(mz), 0.24);
    for (const c of ey) k -= (h.socket ?? 0.006) * gauss(2 - 2 * d.dot(c), 0.2);
    p.addScaledVector(d, k);
  };
}
const HEADS = {
  human: { rx: 0.26, ryU: 0.252, ryD: 0.234, rzF: 0.236, rzB: 0.252, cheek: 0.044, chin: 0.01 },
  cat: { rx: 0.27, ryU: 0.24, ryD: 0.225, rzF: 0.235, rzB: 0.245, cheek: 0.04, chin: 0.004, muzzle: 0.03 },
  alien: { rx: 0.25, ryU: 0.275, ryD: 0.225, rzF: 0.24, rzB: 0.265, cheek: 0.018, chin: 0.01, topW: 0.14 },
  ghost: { rx: 0.25, ryU: 0.25, ryD: 0.235, rzF: 0.235, rzB: 0.245, cheek: 0.024, chin: 0.0 },
};

// ───────── 兩足角色 ─────────
export function buildChar(id) {
  const sp = SPECS[id]; if (sp.pet) return buildPet(sp);
  const ch = { id, spec: sp, springs: [], n: {}, props: {}, sym: {}, HIP: sp.ghost ? 0.66 : 0.6 };
  const root = ch.root = new THREE.Group(), outer = grp(root); outer.scale.setScalar(sp.sc ?? 1); ch.S = sp.sc ?? 1;
  const rig = ch.rig = grp(outer), n = ch.n;
  const skin = skinMat(sp.skin, sp.ghost ? { sssC: 0xb9a0ff, sss: 0.5, rimStr: 0.5 } : sp.alien ? { sssC: 0x30c0a0, sss: 0.3 } : {});
  const hips = n.hips = grp(rig, 0, ch.HIP, 0), spine = n.spine = grp(hips, 0, 0.03, 0);
  const head = n.head = grp(spine, 0, 0.352, 0.004), skull = n.skull = grp(head, 0, 0.222, 0.014);

  buildHead(ch, skull, skin);
  if (sp.ghost) buildGhostBody(ch, skin); else buildBody(ch, skin);

  // 頭上情緒符號
  const symA = ch.symAnchor = grp(skull, 0, 0.44, 0);
  for (const k of ['anger', 'q', 'ex', 'spark', 'bulb', 'drop', 'heart', 'note']) { const s = ch.sym[k] = makeSymbol(k, 0.2); symA.add(s); }
  ch.puffs = [0, 1, 2].map(() => { const s = makeSymbol('puff', 0.16); symA.add(s); return s; });
  ch.dizzy = [0, 1, 2].map(() => { const s = makeSymbol('star', 0.12); symA.add(s); return s; });
  ch.bubble = makeSymbol('dots', 0.3); symA.add(ch.bubble);
  ch.bdots = [0, 1, 2].map(() => { const d = new THREE.Sprite(new THREE.SpriteMaterial({ color: 0xb79cff, depthTest: false, map: dotTex() })); d.renderOrder = 21; d.scale.setScalar(0.04); symA.add(d); return d; });
  buildProps(ch);
  root.traverse((o) => { o.frustumCulled = false; });
  return ch;
}
let _dot; const dotTex = () => _dot || (_dot = canvasTex(64, 64, (c) => { c.fillStyle = '#fff'; c.beginPath(); c.arc(32, 32, 28, 0, 7); c.fill(); }));

function buildHead(ch, skull, skin) {
  const sp = ch.spec, n = ch.n, kind = sp.cat ? 'cat' : sp.alien ? 'alien' : sp.ghost ? 'ghost' : 'human', fn = headShape(HEADS[kind]), surf = makeSurf(fn);
  const base = C(sp.skin), bl = C(sp.blush), shade = C(sp.skin).lerp(C(sp.blush), 0.35).multiplyScalar(0.93), white = C('#fff8f0'), dkf = C('#e8873a'), lil = C('#d9ccff'), spk = C('#6fcfa8');
  const cheek = [V3(0.6, -0.4, 0.68).normalize(), V3(-0.6, -0.4, 0.68).normalize()], eyeD = [V3(0.42, -0.14, 0.9).normalize(), V3(-0.42, -0.14, 0.9).normalize()], noseD = V3(0, -0.34, 0.94).normalize(), chinD = V3(0, -0.88, 0.48).normalize();
  const hg = dirSurface(fn, { w: 112, h: 76, color: (d, p, c) => {
    c.copy(base);
    if (sp.cat) { const az = Math.atan2(d.x, d.z); c.lerp(white, sstep(0.5, 0.2, Math.hypot(d.x * 0.9, d.y + 0.52)) * sstep(-0.1, 0.3, d.z)); const st = sstep(0.55, 0.8, Math.sin(az * 9)) * sstep(0.3, 0.6, d.y) * sstep(0.95, 0.75, d.y) * sstep(0.75, 0.4, Math.abs(az)); c.lerp(dkf, st * 0.8); for (const s of [1, -1]) { const a2 = Math.atan2(d.y + 0.2, d.x * s); c.lerp(dkf, 0.7 * sstep(0.6, 0.85, Math.sin(a2 * 7 + 1.2)) * sstep(0.72, 0.86, Math.abs(d.x)) * sstep(-0.1, 0.25, d.z) * sstep(0.2, -0.15, d.y)); } }
    if (sp.alien) { let s = 0; for (const [x, y, z, r] of [[0.3, 0.8, 0.5, 0.1], [-0.2, 0.9, 0.35, 0.07], [0.05, 0.75, 0.66, 0.05], [-0.5, 0.7, 0.4, 0.06], [0.5, 0.75, -0.2, 0.09], [-0.3, 0.8, -0.5, 0.1]]) s = Math.max(s, sstep(r, r * 0.6, Math.hypot(d.x - x, d.y - y, d.z - z))); c.lerp(spk, s * 0.6); c.lerp(C('#c8f5dc'), 0.3 * sstep(0, -0.8, d.y)); }
    if (sp.ghost) c.lerp(lil, 0.45 * sstep(0.1, -1, d.y));
    for (const e of eyeD) c.lerp(shade, 0.3 * gauss(2 - 2 * d.dot(e), 0.19));
    let b = 0; for (const k of cheek) b += gauss(2 - 2 * d.dot(k), 0.25); c.lerp(bl, Math.min(1, b) * (sp.ghost ? 0.6 : 0.62));
    c.lerp(bl, 0.16 * gauss(2 - 2 * d.dot(noseD), 0.2) + 0.14 * gauss(2 - 2 * d.dot(chinD), 0.25));
  } });
  const hm = mesh(hg, skinMat(0xffffff, { vc: true, ...(sp.ghost ? { sssC: 0xb9a0ff, sss: 0.5, rimStr: 0.5 } : sp.alien ? { sssC: 0x30c0a0, sss: 0.3 } : {}) })); skull.add(hm);
  ch.headFn = fn;
  const E = { human: { x: 0.112, y: -0.04, r: 0.072 }, cat: { x: 0.112, y: -0.03, r: 0.066 }, alien: { x: 0.112, y: -0.035, r: 0.078 }, ghost: { x: 0.1, y: -0.03, r: 0.07 } }[kind];
  ch.face = new Face(skull, { surf, skin: sp.skin,
    lidMat: skinMat(sp.cat ? '#ffb05c' : mix(sp.skin, sp.blush, sp.ghost || sp.alien ? 0.05 : 0.14), { rimStr: 0.1, sss: 0.15, emissive: C(sp.cat ? '#ffb05c' : sp.skin).multiplyScalar(0.16) }),
    eye: { ...E, iris: sp.iris, lashes: sp.lashes, lashC: sp.cat ? '#7a4320' : sp.alien ? '#2f7f70' : sp.ghost ? '#8f86c9' : '#3a2420', lowC: mix(sp.skin, sp.blush, 0.55), lashW: sp.lashes ? 0.0052 : 0.0042 },
    brow: sp.brow ? { x: E.x + 0.004, y: E.y + 0.108, c: sp.brow, w: sp.cat ? 0.03 : 0.043, th: sp.cat ? 0.008 : 0.0145, arch: 0.012 } : sp.alien ? { x: E.x, y: E.y + 0.125, c: '#5fbf9a', w: 0.026, th: 0.007, arch: 0.006 } : { x: E.x, y: E.y + 0.1, c: '#cfc6f2', w: 0.026, th: 0.006, arch: 0.006 },
    mouth: { y: sp.cat ? -0.158 : -0.15, w: 0.031, c: sp.cat ? '#8a4a2c' : sp.alien ? '#2f8f78' : sp.ghost ? '#8f7fc9' : '#a8503f', in: sp.alien ? '#2b6f7a' : '#6e2530' } });
  if (kind === 'human') {
    skull.add(makeNose(surf, { y: -0.092, rx: 0.021, ry: 0.016, rz: 0.021, skin: sp.skin, tip: mix(sp.skin, sp.blush, 0.6), under: mix(sp.skin, sp.blush, 0.8), out: 0.003 }));
    for (const s of [1, -1]) { const ear = makeEar(s, { t: 0.024, h: 0.06, w: 0.046, skin: sp.skin, pink: mix(sp.skin, sp.blush, 0.75) }); const d = V3(s * 0.985, -0.1, -0.12).normalize(), p = V3(); fn(d, p); ear.position.copy(p).add(V3(s * 0.004, 0, 0)); ear.rotation.set(0, -s * 0.62, -s * 0.1); skull.add(ear); }
    const h = buildHair(skull, fn, sp.hair, sp.hair); for (const [node, len, o] of h.springs) ch.springs.push(new Spring(node, len, o));
    if (sp.acc.includes('glasses')) { const gm = softMat('#3a3550', { rough: 0.4 }); const gg = grp(skull); for (const s of [1, -1]) { const p = surf.at(s * 0.107, -0.04); const r = mesh(new THREE.TorusGeometry(0.058, 0.0055, 10, 40), gm, false); r.position.set(p.x, p.y, p.z + 0.03); r.rotation.y = s * 0.2; gg.add(r); const arm = mesh(sweepGeo([[s * 0.165, -0.035, p.z + 0.02], [s * 0.24, -0.03, 0.1], [s * 0.268, -0.02, -0.02]], () => [0.004, 0.004], { rows: 10, seg: 6 }), gm, false); gg.add(arm); } const br = mesh(sweepGeo([[-0.05, -0.03, 0.262], [0, -0.022, 0.272], [0.05, -0.03, 0.262]], () => [0.0045, 0.0045], { rows: 8, seg: 6 }), gm, false); gg.add(br); }
  } else if (kind === 'cat') {
    const nose = mesh(dirSurface((d, p) => p.set(d.x * 0.02 * (1 - 0.35 * sstep(0.2, -1, d.y)), d.y * 0.013, d.z * 0.014), { w: 20, h: 14 }), skinMat('#ff8f9c', { rough: 0.35 }), false); const np = surf.at(0, -0.098); nose.position.copy(np).add(V3(0, 0, 0.006)); skull.add(nose);
    const earIn = C('#ffb3c0'), earOut = C(sp.skin);
    for (const s of [1, -1]) {
      const e = n['ear' + (s > 0 ? 'L' : 'R')] = grp(skull); const p = V3(); fn(V3(s * 0.56, 0.78, 0.0).normalize(), p); e.position.copy(p).multiplyScalar(0.94); e.rotation.set(-0.08, 0, -s * 0.42);
      const g = dirSurface((d, q) => { const t = d.y * 0.5 + 0.5, w = 1 - 0.78 * t ** 1.3; q.set(d.x * 0.085 * w, d.y * 0.085 + 0.07, d.z * 0.034 * w - (d.z > 0 ? 0.012 * (1 - t) * (1 - (d.x * d.x)) : 0)); }, { w: 32, h: 24 });
      paint(g, (q, nn, c) => c.copy(earOut).lerp(earIn, sstep(0.25, 0.75, nn.z) * sstep(0.075, 0.05, Math.abs(q.x)) * sstep(0.135, 0.1, q.y)));
      e.add(mesh(g, skinMat(0xffffff, { vc: true, sss: 0.45 }))); ch.springs.push(new Spring(e, 0.12, { k: 190, c: 9, acc: 1.4 }));
      for (let i = 0; i < 3; i++) { const a = surf.at(s * 0.115, -0.115 - i * 0.012), b = a.clone().add(V3(s * 0.11, 0.022 - i * 0.026, -0.03)); skull.add(mesh(sweepGeo([a, a.clone().lerp(b, 0.5).add(V3(0, 0.004, 0.012)), b], (t) => [0.0022 * (1 - 0.7 * t), 0.0022 * (1 - 0.7 * t)], { rows: 8, seg: 5 }), softMat('#ffffff', { rough: 0.5 }), false)); }
    }
    const tuft = buildHairTuft(fn, sp.skin, '#ffd9a0'); skull.add(tuft);
  } else if (kind === 'alien') {
    for (const s of [1, -1]) {
      const a = n['ant' + (s > 0 ? 'L' : 'R')] = grp(skull); const p = V3(); fn(V3(s * 0.3, 0.93, 0.05).normalize(), p); a.position.copy(p).multiplyScalar(0.98); a.rotation.z = -s * 0.3;
      a.add(mesh(sweepGeo([[0, 0, 0], [s * 0.004, 0.06, 0], [s * 0.022, 0.115, 0]], (t) => [0.009 - 0.003 * t, 0.009 - 0.003 * t], { rows: 12, seg: 8 }), skinMat('#7fd1a8')));
      const ball = mesh(new THREE.SphereGeometry(0.03, 24, 16), softMat('#ffe45c', { emissive: 0xffc93c, emissiveIntensity: 0.45, rough: 0.4 })); ball.position.set(s * 0.026, 0.135, 0); a.add(ball);
      ch.springs.push(new Spring(a, 0.14, { k: 120, c: 5, acc: 2.6 }));
      const fin = mesh(dirSurface((d, q) => q.set(d.x * 0.022, d.y * 0.032, d.z * 0.03), { w: 20, h: 14 }), skinMat(mix(sp.skin, '#6fcfa8', 0.4))); const q = V3(); fn(V3(s, -0.12, -0.05).normalize(), q); fin.position.copy(q); skull.add(fin);
    }
  } else if (kind === 'ghost') {
    const w = n.wisp = grp(skull); const p = V3(); fn(V3(0.05, 1, -0.1).normalize(), p); w.position.copy(p).multiplyScalar(0.96);
    w.add(mesh(sweepGeo([[0, 0, 0], [0.01, 0.06, -0.01], [0.05, 0.1, -0.03], [0.1, 0.1, -0.05]], (t) => [0.045 * (1 - t) ** 0.7 + 0.004, 0.04 * (1 - t) ** 0.7 + 0.004], { rows: 16, seg: 12 }), skin));
    ch.springs.push(new Spring(w, 0.12, { k: 90, c: 5, acc: 2.4 }));
  }
}
function buildHairTuft(fn, col, hi) { // 貓額頭上的一小撮毛
  const g = new THREE.Group(), p = V3(); fn(V3(0, 0.93, 0.36).normalize(), p); g.position.copy(p).multiplyScalar(0.99);
  const m = softMat(0xffffff, { vc: true });
  for (const [dx, h, b] of [[0, 0.07, 0.02], [0.035, 0.05, 0.035], [-0.035, 0.052, -0.035]]) { const geo = sweepGeo([[dx, -0.02, 0], [dx, h * 0.6, 0.012], [dx + b, h, 0.03]], (t) => { const k = Math.sin(PI * clamp(0.2 + 0.8 * t)) ** 0.6; return [0.026 * k, 0.014 * k + 0.002]; }, { rows: 10, seg: 8 }); paint(geo, (q, nn, c) => c.set(col).lerp(C(hi), sstep(0, 0.07, q.y) * 0.6)); g.add(mesh(geo, m)); }
  return g;
}

// 手：手掌＋四根手指（兩節，可握拳）＋拇指
function buildHand(s, skinHex, tipHex) {
  const h = new THREE.Group(), sk = skinMat(0xffffff, { vc: true, sss: 0.3 }), a = C(skinHex), b = C(tipHex);
  const tint = (g, y0, y1) => paint(g, (p, n, c) => c.copy(a).lerp(b, 0.75 * sstep(y0, y1, p.y)));
  const palm = mesh(tint(dirSurface((d, p) => p.set(d.x * 0.02, d.y * 0.036 - 0.03, d.z * 0.034 * (1 + 0.1 * sstep(0.3, -1, d.y))), { w: 24, h: 18 }), -0.02, -0.075), sk); h.add(palm);
  const fingers = [], zs = [0.026, 0.0087, -0.0087, -0.026], ls = [0.021, 0.024, 0.023, 0.018];
  zs.forEach((z, i) => {
    const f = grp(h, -s * 0.001, -0.054 + Math.abs(i - 1.3) * 0.003, z); f.add(mesh(tint(limbGeo(0.0102, ls[i]), 0.02, -0.02), sk));
    const f2 = grp(f, 0, -ls[i], 0); f2.add(mesh(tint(limbGeo(0.0098, ls[i] * 0.8, 0.0088), 0.01, -0.015), sk)); fingers.push([f, f2]);
  });
  const th = grp(h, -s * 0.004, -0.02, 0.031); th.rotation.set(-0.75, 0, -s * 0.25); th.add(mesh(tint(limbGeo(0.0118, 0.02), 0.02, -0.02), sk));
  const th2 = grp(th, 0, -0.02, 0); th2.rotation.x = 0.3; th2.add(mesh(tint(limbGeo(0.0112, 0.016, 0.0098), 0.01, -0.015), sk));
  h.userData.curl = (k) => { for (const [f, f2] of fingers) { f.rotation.z = -s * (0.12 + 1.25 * k); f2.rotation.z = -s * (0.15 + 1.45 * k); } th.rotation.set(-0.75 + 0.45 * k, 0, -s * (0.25 + 0.85 * k)); th2.rotation.x = 0.3 + 0.5 * k; };
  h.userData.curl(0.25); return h;
}
// 運動鞋：鞋底、鞋面（鞋頭、側片、後跟提帶用頂點色分區）、鞋舌、鞋帶
function buildShoe(s, o) {
  const g = new THREE.Group(), main = C(o.c), c2 = C(o.c2), sole = C(o.sole), dark = C(o.c).multiplyScalar(0.8);
  const soleG = dirSurface((d, p) => { const zn = d.z, w = 0.058 * (1 - 0.14 * sstep(0.1, -1, zn)) * (1 + 0.05 * sstep(0.2, 0.7, zn)); const e = 0.6; p.set(Math.sign(d.x) * Math.abs(d.x) ** e * w, -0.069 + Math.sign(d.y) * Math.abs(d.y) ** 0.62 * 0.02, 0.038 + Math.sign(zn) * Math.abs(zn) ** 0.75 * 0.118); }, { w: 64, h: 32 });
  g.add(mesh(soleG, softMat(o.sole, { rough: 0.7 })));
  const H = (zn) => lerp(0.08, 0.046, sstep(-0.35, 0.8, zn));
  const upF = (d, p) => { const zn = d.z, w = 0.053 * (1 - 0.12 * sstep(0.1, -1, zn)); p.set(Math.sign(d.x) * Math.abs(d.x) ** 0.8 * w, -0.06 + (d.y > 0 ? d.y ** 0.8 * H(zn) : d.y * 0.01), 0.036 + Math.sign(zn) * Math.abs(zn) ** 0.8 * 0.108); };
  const capG = dirSurface((d, p) => { upF(d, p); const k = sstep(0.47, 0.52, d.z); p.y += 0.06; p.multiplyScalar(lerp(0.8, 1.045, k)); p.y -= 0.06; p.z += lerp(-0.02, 0.0015, k); }, { w: 56, h: 36 });
  g.add(mesh(capG, softMat(o.c2, { rough: 0.7 })));
  const upG = dirSurface(upF, { w: 56, h: 36, color: (d, p, c) => {
    c.copy(main); const zn = (p.z - 0.036) / 0.108;
    c.lerp(dark, sstep(-0.75, -0.88, zn)); // 後跟
  } });
  g.add(mesh(upG, softMat(0xffffff, { vc: true, rough: 0.8 })));
  const tongue = mesh(dirSurface((d, p) => p.set(d.x * 0.027, d.y * 0.034, d.z * 0.012), { w: 20, h: 14 }), softMat(o.c2, { rough: 0.8 })); tongue.position.set(0, 0.004, 0.05); tongue.rotation.x = -0.5; g.add(tongue);
  const lm = softMat(o.lace ?? '#ffffff', { rough: 0.6 });
  for (let i = 0; i < 3; i++) { const z = 0.058 + i * 0.019, y = -0.06 + H((z - 0.036) / 0.108) * 0.985 + 0.004; const l = mesh(sweepGeo([[-0.021, y - 0.006, z], [0, y + 0.002, z + 0.002], [0.021, y - 0.006, z]], () => [0.0042, 0.003], { rows: 8, seg: 6, nrm: (p, t, out) => out.set(0, 1, 0.3) }), lm, false); g.add(l); }
  const col = mesh(new THREE.TorusGeometry(0.043, 0.013, 10, 28), softMat(mix(o.c, '#ffffff', 0.25), { rough: 0.85 })); col.rotation.x = PI / 2 + 0.12; col.position.set(0, 0.012, -0.004); col.scale.set(1, 1.15, 1); g.add(col);
  return g;
}

function buildBody(ch, skin) {
  const sp = ch.spec, n = ch.n, hips = n.hips, spine = n.spine, t = sp.top, M = softMat;
  const topM = M(0xffffff, { map: topTex(t), rough: 0.95, rimStr: 0.3 }), plainM = M(0xffffff, { map: clothTex(t.c), rough: 0.95, rimStr: 0.3 }), c2M = M(0xffffff, { map: clothTex(t.c2), rough: 0.95 });
  const sleeveC = t.type === 'vest' ? t.c2 : t.c, sleeveM = M(0xffffff, { map: clothTex(sleeveC), rough: 0.95, rimStr: 0.3 });
  // 軀幹：超橢圓截面放樣（下襬收、肚子微凸、肩膀圓）
  const prof = cr([[-0.085, 0.118, 0.094, 0, 0.004], [-0.055, 0.146, 0.113, 0, 0.008], [0.0, 0.153, 0.118, 0, 0.01], [0.07, 0.154, 0.114, 0, 0.007], [0.15, 0.156, 0.108, 0, 0.003], [0.225, 0.158, 0.1, 0, 0], [0.275, 0.15, 0.092, 0, -0.002], [0.305, 0.115, 0.078, 0, -0.004], [0.325, 0.07, 0.058, 0, -0.004], [0.335, 0.03, 0.03, 0, -0.004]]);
  const torso = mesh(ringLoft(prof, 40, 48, { n: 2.35 }), topM); spine.add(torso);
  // 下襬羅紋
  const hemC = t.type === 'hoodie' ? t.c : t.type === 'vest' ? mix(t.c, '#ffffff', 0.25) : t.c;
  const hem = mesh(ringLoft((v) => { const a = v * PI; return [-0.068 - 0.022 * Math.cos(a) * 1, 0.132 + 0.013 * Math.sin(a), 0.104 + 0.012 * Math.sin(a), 0, 0.006]; }, 10, 72, { n: 2.35, mod: (v, a) => 1 + 0.01 * Math.sin(a * 44) }), M(mix(hemC, '#000000', 0.06), { rough: 0.95 })); spine.add(hem);
  // 脖子
  const neck = mesh(limbGeo(0.047, 0.09, 0.044), skin); neck.position.set(0, 0.385, -0.002); spine.add(neck);
  if (t.type === 'hoodie') {
    // 袋鼠口袋：兩側開口顏色較深
    const pk = dirSurface((d, p) => { const w = 0.092 * (1 - 0.22 * sstep(-0.6, 1, d.y)); p.set(Math.sign(d.x) * Math.abs(d.x) ** 0.7 * w, Math.sign(d.y) * Math.abs(d.y) ** 0.7 * 0.05, d.z * 0.042 - 0.024 * (d.x * d.x)); }, { w: 48, h: 28, color: (d, p, c) => c.set(t.c).lerp(C(mix(t.c, '#5a2a10', 0.45)), sstep(0.066, 0.086, Math.abs(p.x)) * sstep(-0.5, 0.2, d.z)) });
    const pocket = mesh(pk, M(0xffffff, { vc: true, map: clothTex('#ffffff'), rough: 0.95 })); pocket.position.set(0, 0.005, 0.112); pocket.rotation.x = -0.06; spine.add(pocket); ch.pocketY = 0.005;
    // 兜帽：披在後頸的一圈布
    const hood = mesh(dirSurface((d, p) => { const back = sstep(0.5, -0.6, d.z); p.set(d.x * 0.135, d.y * (0.04 + 0.03 * back) - 0.03 * (1 - back), d.z * (d.z < 0 ? 0.105 : 0.05)); p.y += 0.02 * back * (1 - d.x * d.x); }, { w: 48, h: 28, color: (d, p, c) => c.set(t.c).lerp(C(mix(t.c, '#3a1a00', 0.35)), sstep(0.3, 0.95, d.y) * sstep(0.55, 0.0, Math.hypot(d.x, d.z + 0.2))) }), M(0xffffff, { vc: true, map: clothTex('#ffffff'), rough: 0.95, rimStr: 0.3 })); hood.position.set(0, 0.325, -0.05); hood.rotation.x = 0.28; spine.add(hood);
    // 領口一圈＋兩條抽繩
    const col = mesh(ringLoft((v) => { const a = v * PI * 2; return [0.335 - 0.017 * Math.sin(a), 0.074 + 0.02 * Math.cos(a) * -1, 0.066 + 0.02 * Math.cos(a) * -1, 0, -0.002]; }, 12, 40, { mod: (v, a) => 1 }), plainM); col.rotation.x = 0.2; col.position.set(0, -0.012, 0.064); spine.add(col);
    for (const s of [1, -1]) {
      const d = mesh(sweepGeo([[s * 0.03, 0.318, 0.088], [s * 0.036, 0.28, 0.104], [s * 0.04, 0.235, 0.108], [s * 0.043, 0.2, 0.113]], () => [0.0055, 0.0055], { rows: 12, seg: 8 }), M(t.c2, { rough: 0.8 }), false); spine.add(d);
      const tip = mesh(limbGeo(0.0075, 0.016), M(t.c3, { rough: 0.5 }), false); tip.position.set(s * 0.043, 0.2, 0.113); spine.add(tip);
    }
  } else {
    // 襯衫領：兩片立體領片
    const cm = M(t.type === 'jacket' ? t.c : t.c2, { rough: 0.9 });
    for (const s of [1, -1]) { const c = mesh(dirSurface((d, p) => p.set(d.x * 0.046 * (1 - 0.35 * sstep(-0.5, 1, d.y)), d.y * 0.03, d.z * 0.012), { w: 24, h: 16 }), cm); c.position.set(s * 0.043, 0.318, 0.066); c.rotation.set(0.5, s * 0.5, -s * (t.type === 'jacket' ? 0.75 : 0.6)); if (t.type === 'jacket') c.scale.set(1.3, 1.35, 1.2); spine.add(c); }
    const band = mesh(ringLoft((v) => { const a = v * PI * 2; return [0.342 - 0.012 * Math.sin(a), 0.062 - 0.012 * Math.cos(a), 0.056 - 0.012 * Math.cos(a), 0, -0.006]; }, 10, 36), cm); spine.add(band);
    if (t.type === 'vest') { const bow = grp(spine, 0, 0.292, 0.098); const bm = M(t.c3, { rough: 0.7 }); for (const s of [1, -1]) { const w = mesh(dirSurface((d, p) => p.set(d.x * 0.03, d.y * 0.02 * (0.5 + 0.5 * Math.abs(d.x)), d.z * 0.01), { w: 20, h: 14 }), bm); w.position.x = s * 0.026; bow.add(w); } bow.add(mesh(ellipsoid(0.011, 0.012, 0.011, { w: 14, h: 10 }), bm)); }
  }
  // 手臂
  for (const [s, k] of [[1, 'L'], [-1, 'R']]) {
    const arm = n['arm' + k] = grp(spine, s * 0.158, 0.262, -0.004), elb = n['elb' + k] = grp(arm, 0, -0.185, 0), hand = n['hand' + k] = grp(elb, 0, -0.17, 0);
    if (t.sleeve === 'short') {
      arm.add(mesh(tubeLimb(0.125, 0.055, 0.056, { open: true }), sleeveM));
      const cuff = mesh(new THREE.TorusGeometry(0.052, 0.011, 10, 32), c2M); cuff.rotation.x = PI / 2; cuff.position.y = -0.125; arm.add(cuff);
      arm.add(mesh(limbGeo(0.045, 0.185, 0.043), skin));
      elb.add(mesh(limbGeo(0.043, 0.17, 0.034), skin));
    } else {
      arm.add(mesh(tubeLimb(0.185, 0.054, 0.049, { wr: 0.016, wr0: 0.45, wrF: 50 }), sleeveM));
      elb.add(mesh(tubeLimb(0.155, 0.049, 0.047, { wr: 0.028, wr0: 0.3, wrF: 60, ph: 1.5 }), sleeveM));
      const cuff = mesh(ringLoft((v) => { const a = (1 - v) * PI; return [-0.155 - 0.014 * (1 - Math.cos(a)), 0.04 + 0.006 * Math.sin(a), 0.04 + 0.006 * Math.sin(a)]; }, 8, 40, { mod: (v, a) => 1 + 0.02 * Math.sin(a * 22) }), t.type === 'vest' ? c2M : M(mix(t.c, '#000000', 0.07), { rough: 0.95 })); elb.add(cuff);
    }
    const hd = buildHand(s, sp.skin, mix(sp.skin, sp.blush, sp.cat ? 0.1 : 0.55)); hand.add(hd); n['hm' + k] = hd;
    n['grip' + k] = grp(hand, -s * 0.03, -0.05, 0.004);
  }
  // 骨盆與腿（牛仔褲：小腿有皺褶、反摺褲腳）
  const pm = M(0xffffff, { map: clothTex(sp.pants.c, sp.pants.plain ? 'plain' : 'denim'), rough: 0.9, vc: true, rimStr: 0.3 });
  const fade = (g, k = 0.22) => paint(g, (p, nn, c) => { c.setRGB(1, 1, 1).lerp(C('#dfe9ff'), 0).multiplyScalar(1 - 0.0); const f = k * sstep(-0.1, 0.9, nn.z) * sstep(-0.26, -0.08, p.y) * sstep(0.02, -0.06, p.y); c.setRGB(1 + f, 1 + f, 1 + f * 0.9); });
  const pelvis = mesh(fade(dirSurface((d, p) => p.set(d.x * 0.142, d.y * (d.y > 0 ? 0.075 : 0.092) - 0.012, d.z * 0.112 + 0.004), { w: 36, h: 24 }), 0), pm); hips.add(pelvis);
  for (const [s, k] of [[1, 'L'], [-1, 'R']]) {
    const leg = n['leg' + k] = grp(hips, s * 0.074, -0.03, 0), knee = n['knee' + k] = grp(leg, 0, -0.245, 0), foot = n['foot' + k] = grp(knee, 0, -0.245, 0);
    leg.add(mesh(fade(tubeLimb(0.245, 0.078, 0.072, { wr: 0.02, wr0: 0.0, wrF: 34, ph: s }), 0.16), pm));
    knee.add(mesh(fade(tubeLimb(0.215, 0.072, 0.078, { rows: 34, seg: 28, wr: 0.052, wr0: 0.4, wrF: 40, ph: s * 2, open: true }), 0.1), pm));
    const cuff = mesh(ringLoft((v) => { const a = (1 - v) * PI; return [-0.2 - 0.016 * (1 - Math.cos(a)), 0.079 + 0.008 * Math.sin(a), 0.079 + 0.008 * Math.sin(a)]; }, 8, 36), M(0xffffff, { map: clothTex(sp.pants.cuff, sp.pants.plain ? 'plain' : 'denim'), rough: 0.9 })); knee.add(cuff);
    const shoe = buildShoe(s, sp.shoes); shoe.scale.setScalar(1.28); foot.add(shoe);
  }
  if (sp.cat) { // 尾巴：三節彈簧
    let par = hips, tl = null; const tm = skinMat(0xffffff, { vc: true });
    for (let i = 0; i < 4; i++) { const g = grp(par, 0, i ? 0.105 : -0.045, i ? 0 : -0.105); if (!i) { g.rotation.x = -1.75; n.tail = g; } else g.rotation.x = 0.55; const geo = limbGeo(0.034 - i * 0.002, 0.105, 0.032 - i * 0.002); geo.translate(0, 0.105, 0); paint(geo, (p, nn, c) => c.set(i === 3 ? '#fff4e2' : i % 2 ? '#f29a45' : sp.skin)); g.add(mesh(geo, tm)); if (i) ch.springs.push(new Spring(g, 0.105, { k: 120, c: 6, acc: 1.5 })); par = g; }
  }
  // 配件
  if (sp.acc.includes('backpack')) {
    const bm = M(sp.pack, { rough: 0.85 }), bm2 = M(mix(sp.pack, '#ffffff', 0.35), { rough: 0.85 });
    const bag = grp(spine, 0, 0.15, -0.155); bag.rotation.x = 0.06;
    bag.add(mesh(dirSurface((d, p) => p.set(Math.sign(d.x) * Math.abs(d.x) ** 0.6 * 0.112, Math.sign(d.y) * Math.abs(d.y) ** 0.6 * 0.135 * (1 - 0.1 * sstep(0, 1, d.y)), Math.sign(d.z) * Math.abs(d.z) ** 0.7 * 0.062), { w: 40, h: 28 }), bm));
    const fp = mesh(dirSurface((d, p) => p.set(Math.sign(d.x) * Math.abs(d.x) ** 0.6 * 0.078, Math.sign(d.y) * Math.abs(d.y) ** 0.6 * 0.058, d.z * 0.03), { w: 28, h: 18 }), bm2); fp.position.set(0, -0.055, -0.052); bag.add(fp);
    const zip = mesh(sweepGeo([[-0.07, 0.04, -0.062], [0, 0.052, -0.066], [0.07, 0.04, -0.062]], () => [0.004, 0.003], { rows: 10, seg: 6 }), M('#fff3dc'), false); bag.add(zip);
    const charm = grp(bag, 0.075, 0.04, -0.062); charm.add(mesh(new THREE.SphereGeometry(0.018, 16, 12), M('#ffd24d', { rough: 0.5 }))); charm.children[0].position.y = -0.03; ch.springs.push(new Spring(charm, 0.04, { k: 60, c: 3, acc: 2, axis: V3(0, -1, 0), g: 30 }));
    for (const s of [1, -1]) spine.add(mesh(sweepGeo([[s * 0.085, 0.27, -0.1], [s * 0.098, 0.318, -0.02], [s * 0.112, 0.262, 0.088], [s * 0.128, 0.16, 0.098], [s * 0.15, 0.07, 0.03], [s * 0.1, 0.06, -0.1]], () => [0.017, 0.0065], { rows: 24, seg: 8, nrm: (p, tt, out) => out.set(p.x * 0.6, Math.max(0, p.y - 0.25) * 4, p.z) }), bm));
  }
  if (sp.acc.includes('badge')) buildBadge(ch, spine);
}
function buildBadge(ch, spine, y0 = 0.325, zf = 0.1) {
  const lm = softMat('#ff9f8e', { rough: 0.7 });
  for (const s of [1, -1]) spine.add(mesh(sweepGeo([[s * 0.058, y0 + 0.012, -0.03], [s * 0.07, y0 - 0.005, 0.04], [s * 0.045, y0 - 0.08, zf + 0.012], [0.0, y0 - 0.15, zf + 0.022]], () => [0.006, 0.0025], { rows: 16, seg: 6, nrm: (p, t, out) => out.set(p.x, 0.3, 1) }), lm, false));
  const b = ch.n.badge = grp(spine, 0, y0 - 0.15, zf + 0.024);
  const card = mesh(roundedSlab(0.062, 0.078, 0.01, 0.005, 0.002), softMat(0xffffff, { map: canvasTex(128, 160, (c) => { c.fillStyle = '#ffffff'; c.fillRect(0, 0, 128, 160); c.fillStyle = '#8fd0ff'; c.fillRect(0, 0, 128, 44); c.fillStyle = '#ffd9c4'; c.beginPath(); c.arc(64, 78, 24, 0, 7); c.fill(); c.fillStyle = '#6a557a'; c.beginPath(); c.arc(64, 70, 25, PI, 0); c.fill(); c.fillStyle = '#cfc8e6'; c.beginPath(); c.roundRect(24, 116, 80, 10, 5); c.fill(); c.beginPath(); c.roundRect(38, 134, 52, 8, 4); c.fill(); }), rough: 0.5 })); card.position.y = -0.045; b.add(card);
  ch.springs.push(new Spring(b, 0.05, { k: 70, c: 4, acc: 1.2, axis: V3(0, -1, 0), g: 40 }));
}

// 幽靈：沒有腳，身體往下收成一條飄動的尾巴；短手；圍巾＋識別證
function buildGhostBody(ch, skin) {
  const sp = ch.spec, n = ch.n, spine = n.spine;
  const prof = cr([[-0.4, 0.004, 0.004, 0.035, -0.15], [-0.35, 0.02, 0.02, 0.02, -0.105], [-0.295, 0.04, 0.038, 0.005, -0.055], [-0.255, 0.085, 0.075, 0, -0.02], [-0.225, 0.15, 0.122, 0, -0.004], [-0.17, 0.186, 0.15, 0, 0.004], [-0.06, 0.18, 0.142, 0, 0.006], [0.07, 0.166, 0.128, 0, 0.005], [0.18, 0.15, 0.11, 0, 0], [0.27, 0.126, 0.092, 0, -0.003], [0.33, 0.085, 0.066, 0, -0.004], [0.35, 0.04, 0.035, 0, -0.004]]);
  const g = ringLoft(prof, 56, 60, { n: 2.15, mod: (v, a) => 1 + 0.085 * Math.sin(a * 6 + 0.5) * Math.exp(-(((v - 0.43) / 0.085) ** 2)) });
  paint(g, (p, nn, c) => c.set('#ffffff').lerp(C('#cdbcf7'), sstep(0.12, -0.36, p.y) * 0.8));
  const body = mesh(g, skinMat(0xffffff, { vc: true, sssC: 0xb9a0ff, sss: 0.5, rimStr: 0.5 })); const tail = n.gtail = grp(spine); tail.add(body);
  // 圍巾
  const sm = softMat(0xffffff, { map: clothTex('#ff8f7e'), rough: 0.95 });
  spine.add(mesh(ringLoft((v) => { const a = v * PI * 2; return [0.318 - 0.026 * Math.sin(a), 0.098 - 0.026 * Math.cos(a), 0.08 - 0.026 * Math.cos(a), 0, -0.002]; }, 12, 40, { mod: (v, a) => 1 + 0.02 * Math.sin(a * 30) }), sm));
  const sc = n.scarf = grp(spine, 0.07, 0.31, 0.075); sc.add(mesh(sweepGeo([[0, 0, 0], [0.012, -0.05, 0.016], [0.02, -0.105, 0.012], [0.016, -0.15, 0.008]], (t) => [0.03, 0.009], { rows: 14, seg: 10, nrm: (p, t, out) => out.set(0.2, 0, 1) }), sm));
  ch.springs.push(new Spring(sc, 0.12, { k: 60, c: 4, acc: 1.6, axis: V3(0.1, -1, 0.05), g: 30 }));
  for (const [s, k] of [[1, 'L'], [-1, 'R']]) {
    const arm = n['arm' + k] = grp(spine, s * 0.15, 0.245, 0), elb = n['elb' + k] = grp(arm, 0, -0.15, 0), hand = n['hand' + k] = grp(elb, 0, -0.14, 0);
    arm.add(mesh(limbGeo(0.047, 0.15, 0.042), skin)); elb.add(mesh(limbGeo(0.042, 0.14, 0.034), skin));
    const hd = buildHand(s, '#fbf9ff', '#e3d6ff'); hand.add(hd); n['hm' + k] = hd; n['grip' + k] = grp(hand, -s * 0.03, -0.05, 0.004);
  }
}
