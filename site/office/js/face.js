// 立體五官：真的眼球（鞏膜、放射紋虹膜、瞳孔、兩點高光）＋上下眼皮＋睫毛線、有厚度的眉毛、可開合的嘴、鼻、耳
import { THREE, softMat, skinMat, dirSurface, ellipsoid, sweepGeo, paint, canvasTex, clamp, lerp, sstep, C } from './core.js';

const V3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const PI = Math.PI;

// 由「方向 → 位置」的頭型函式，求正面 (x, y) 處的表面點與法線
export function makeSurf(fn) {
  const d = V3(), p = V3(), a = V3(), b = V3();
  const at = (x, y, out = V3()) => { let z = 0.22; for (let i = 0; i < 10; i++) { d.set(x, y, z).normalize(); fn(d, p); z = p.z; d.set(x, y, z); } d.set(x, y, z).normalize(); fn(d, out); return out; };
  const normal = (x, y, out = V3()) => { const e = 0.004; at(x + e, y, a).sub(at(x - e, y, p.clone())); const c = at(x, y + e, b).clone().sub(at(x, y - e, V3())); return out.crossVectors(a, c).normalize(); };
  return { at, normal, fn };
}

// 虹膜貼圖：放射紋、深色外圈、下半透亮、瞳孔
const IRIS = {};
export function irisTex(o) {
  const key = JSON.stringify(o); if (IRIS[key]) return IRIS[key];
  return IRIS[key] = canvasTex(256, 256, (c) => {
    const R = o.R ?? 80, cx = 128, cy = 128;
    let g = c.createRadialGradient(cx, cy, 30, cx, cy, 128); g.addColorStop(0, o.sclera ?? '#ffffff'); g.addColorStop(0.72, o.sclera ?? '#fffdfc'); g.addColorStop(1, o.scleraEdge ?? '#e8d8d8'); c.fillStyle = g; c.fillRect(0, 0, 256, 256);
    g = c.createLinearGradient(0, 20, 0, 120); g.addColorStop(0, 'rgba(120,90,110,0.22)'); g.addColorStop(1, 'rgba(120,90,110,0)'); c.fillStyle = g; c.fillRect(0, 0, 256, 128); // 上眼皮的陰影
    c.save(); c.beginPath(); c.arc(cx, cy, R, 0, 7); c.clip();
    g = c.createLinearGradient(0, cy - R, 0, cy + R); g.addColorStop(0, o.dark); g.addColorStop(0.45, o.mid); g.addColorStop(1, o.light); c.fillStyle = g; c.fillRect(0, 0, 256, 256);
    let s = 11; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 150; i++) { const a = rnd() * PI * 2, r0 = R * (0.42 + 0.15 * rnd()), r1 = R * (0.8 + 0.2 * rnd()); c.strokeStyle = i % 2 ? `rgba(255,236,200,${0.1 + 0.22 * rnd()})` : `rgba(30,12,6,${0.1 + 0.2 * rnd()})`; c.lineWidth = 0.8 + rnd() * 1.6; c.beginPath(); c.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); c.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); c.stroke(); }
    g = c.createRadialGradient(cx, cy + R * 0.5, 2, cx, cy + R * 0.45, R * 0.75); g.addColorStop(0, o.glow ?? 'rgba(255,214,150,0.6)'); g.addColorStop(1, 'rgba(255,214,150,0)'); c.fillStyle = g; c.fillRect(0, 0, 256, 256); // 下半透亮
    g = c.createRadialGradient(cx, cy, R * 0.74, cx, cy, R); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, o.ring ?? 'rgba(34,14,8,0.85)'); c.fillStyle = g; c.fillRect(0, 0, 256, 256);
    c.restore();
    c.fillStyle = o.pupil ?? '#140a08'; c.beginPath(); c.arc(cx, cy, R * (o.pupilR ?? 0.52), 0, 7); c.fill();
    g = c.createRadialGradient(cx, cy, R * 0.5, cx, cy, R * 0.62); g.addColorStop(0, 'rgba(20,10,8,0.7)'); g.addColorStop(1, 'rgba(20,10,8,0)'); c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R * 0.62, 0, 7); c.fill();
  });
}

// 一顆眼睛：eye(群組，朝表面法線) → ball(可轉動看方向)、lidU / lidL(繞 x 軸開合、繞 z 軸傾斜)、高光
function buildEye(s, o) {
  const g = new THREE.Group(), r = o.r, rl = r * 1.05;
  const bg = new THREE.SphereGeometry(r, 40, 28), pos = bg.attributes.position, uv = bg.attributes.uv;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, 0.5 + pos.getX(i) / (2 * r), 0.5 + pos.getY(i) / (2 * r));
  const ball = new THREE.Mesh(bg, new THREE.MeshBasicMaterial({ map: irisTex(o.iris) })); g.add(ball);
  const lidM = o.lidMat; lidM.polygonOffset = true; lidM.polygonOffsetFactor = -1; lidM.polygonOffsetUnits = -2;
  const lidU = new THREE.Group(), lidL = new THREE.Group(); lidU.rotation.order = lidL.rotation.order = 'ZXY'; g.add(lidU, lidL);
  lidU.add(new THREE.Mesh(new THREE.SphereGeometry(rl, 40, 14, 0, PI * 2, 0, PI / 2), lidM));
  lidL.add(new THREE.Mesh(new THREE.SphereGeometry(rl, 40, 14, 0, PI * 2, PI / 2, PI / 2), lidM));
  // 睫毛線：沿上眼皮邊緣一道深色弧，外眼角略粗（可加翹睫毛）
  const arc = []; for (let i = 0; i <= 24; i++) { const a = lerp(-1.32, 1.32, i / 24); arc.push([Math.sin(a) * (rl + 0.0008), -0.0008, Math.cos(a) * (rl + 0.0008)]); }
  const lw = o.lashW ?? 0.0042;
  const lash = new THREE.Mesh(sweepGeo(arc, (t) => { const k = Math.sin(PI * clamp(t * 1.02)) ** 0.45; const side = s > 0 ? t : 1 - t; return [lw * k * (0.8 + 0.5 * side), 0.0022 * k]; }, { rows: 24, seg: 8, nrm: (p, t, out) => out.set(0, -1, 0) }), softMat(o.lashC ?? '#3a2420', { rough: 0.7, rimStr: 0.05 }));
  lidU.add(lash);
  if (o.lashes) for (const k of [0, 1]) { // 外眼角兩根翹睫毛
    const a = s * (0.95 + 0.22 * k), b = V3(Math.sin(a) * rl, 0, Math.cos(a) * rl), out = b.clone().normalize();
    const m = new THREE.Mesh(sweepGeo([b, b.clone().addScaledVector(out, 0.008).add(V3(s * 0.004, 0.004, 0)), b.clone().addScaledVector(out, 0.013).add(V3(s * 0.011, 0.012, 0))], (t) => [0.0028 * (1 - 0.8 * t), 0.002 * (1 - 0.8 * t)], { rows: 8, seg: 6 }), lash.material); lidU.add(m);
  }
  // 下眼皮邊緣一道很淡的線
  const arc2 = arc.map(([x, y, z]) => [x * 0.999, 0.0006, z * 0.999]);
  lidL.add(new THREE.Mesh(sweepGeo(arc2, (t) => { const k = Math.sin(PI * t) ** 0.6; return [0.0022 * k, 0.0012 * k]; }, { rows: 20, seg: 6, nrm: (p, t, out) => out.set(0, 1, 0) }), softMat(o.lowC ?? '#c98a7c', { rough: 0.8, rimStr: 0 })));
  const hm = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const hi = (x, y, rr) => { const z = Math.sqrt(Math.max(1e-6, r * r - x * x - y * y)); const m = new THREE.Mesh(ellipsoid(rr, rr * 1.1, rr * 0.25, { w: 14, h: 10 }), hm); m.position.set(x, y, z + 0.0006); m.lookAt(m.position.clone().multiplyScalar(2)); g.add(m); return m; };
  const h1 = hi(-0.3 * r, 0.3 * r, 0.2 * r), h2 = hi(0.3 * r, -0.32 * r, 0.085 * r);
  g.traverse((m) => { m.castShadow = false; });
  return { g, ball, lidU, lidL, lash, h1, h2 };
}

// 表情目標值
// eU / eL：上下眼皮邊緣的仰角（弧度）；tilt：眼皮斜度（＋＝內側下壓＝生氣）；bY / bR：眉毛高低與斜度；
// sm：嘴角上揚；op：張嘴；mw：嘴寬倍率；as：歪嘴；mx：嘴偏一邊
const EX = {
  neutral: { eU: 0.74, eL: -0.82, tilt: 0, bY: 0, bR: 0, bA: 0, sm: 0.55, op: 0, mw: 1, as: 0.2, mx: 0, lx: 0, ly: 0 },
  happy: { eU: 0.68, eL: -0.52, tilt: -0.06, bY: 0.014, bR: -0.1, bA: 0, sm: 1.0, op: 0.42, mw: 1.3, as: 0, mx: 0, lx: 0, ly: 0 },
  angry: { eU: 0.34, eL: -0.55, tilt: 0.42, bY: -0.022, bR: 0.5, bA: 0, sm: -0.8, op: 0.12, mw: 1.15, as: 0, mx: 0, lx: 0, ly: 0 },
  surprised: { eU: 1.05, eL: -1.0, tilt: 0, bY: 0.036, bR: -0.08, bA: 0, sm: 0, op: 0.85, mw: 0.62, as: 0, mx: 0, lx: 0, ly: 0 },
  think: { eU: 0.5, eL: -0.7, tilt: 0.05, bY: 0.004, bR: 0.12, bA: 0.03, sm: -0.15, op: 0, mw: 0.6, as: 0.5, mx: 0.012, lx: -0.6, ly: 0.55 },
  sad: { eU: 0.44, eL: -0.7, tilt: -0.36, bY: 0.008, bR: -0.48, bA: 0, sm: -1.0, op: 0.06, mw: 0.85, as: 0, mx: 0, lx: 0, ly: -0.4 },
  smug: { eU: 0.26, eL: -0.45, tilt: 0.1, bY: 0.012, bR: 0.1, bA: 0.016, sm: 1.0, op: 0, mw: 1.2, as: 0.9, mx: 0.006, lx: 0.5, ly: 0 },
  dizzy: { eU: 0.7, eL: -0.6, tilt: -0.1, bY: 0.02, bR: -0.3, bA: 0, sm: -0.3, op: 0.5, mw: 0.7, as: 0, mx: 0, lx: 0, ly: 0 },
};
export const EXPR_KEYS = Object.keys(EX);

export class Face {
  // skull：頭的群組（原點在頭中心）；o：{ surf, skin, eye:{x,y,r,iris,depth}, brow:{y,c,w}, mouth:{y,w,c}, nose, ears… }
  constructor(skull, o) {
    this.o = o; this.s = { expr: 'neutral', mouth: 0, blink: 0, t: 0, lx: 0, ly: 0 }; this.cur = { ...EX.neutral }; const surf = o.surf;
    const lidMat = o.lidMat || skinMat(o.skin, { rimStr: 0.12, sss: 0.2 });
    this.eyes = [];
    for (const s of [1, -1]) {
      const e = o.eye, p = surf.at(s * e.x, e.y), n = surf.normal(s * e.x, e.y);
      const eye = buildEye(s, { r: e.r, iris: e.iris, lidMat, lashC: e.lashC, lashes: e.lashes, lashW: e.lashW, lowC: e.lowC });
      eye.g.position.copy(p).addScaledVector(n, -(e.depth ?? e.r * 0.62));
      eye.yaw = Math.atan2(n.x, n.z) * (e.follow ?? 0.8); eye.pitch = -Math.asin(clamp(n.y, -1, 1)) * 0.5; eye.g.rotation.set(eye.pitch, eye.yaw, 0, 'YXZ'); eye.s = s; eye.toe = -eye.yaw * (e.toe ?? 1.06);
      skull.add(eye.g); this.eyes.push(eye);
    }
    // 眉毛：貼著額頭弧面的一段有厚度的弧
    this.brows = [];
    if (o.brow) for (const s of [1, -1]) {
      const b = o.brow, w = b.w ?? 0.05, pts = [], c0 = surf.at(s * b.x, b.y), n0 = surf.normal(s * b.x, b.y);
      for (let i = 0; i <= 8; i++) { const u = i / 8 * 2 - 1, x = s * (b.x + u * w), y = b.y + (b.arch ?? 0.012) * (1 - u * u) - 0.006 * u; pts.push(surf.at(x, y).addScaledVector(surf.normal(x, y), 0.0035).sub(c0)); }
      const th = b.th ?? 0.0105;
      const g = sweepGeo(pts, (t) => { const k = Math.sin(PI * clamp(0.06 + t * 0.9)) ** 0.5; return [th * k * (1.15 - 0.55 * t), 0.006 * k]; }, { rows: 18, seg: 10, nrm: (p, t, out) => out.copy(n0) });
      const m = new THREE.Mesh(g, softMat(b.c, { rough: 0.8, rimStr: 0.15 })); m.castShadow = false; const grp = new THREE.Group(); grp.position.copy(c0); grp.add(m); skull.add(grp); grp.userData = { c0: c0.clone(), n0, s }; this.brows.push(grp);
    }
    // 嘴：上唇線、下唇線（動態管狀）＋口腔、舌頭、牙齒
    const mo = o.mouth; this.mN = 20;
    const mg = this.mg = new THREE.Group(); this.m0 = surf.at(0, mo.y); const mn = surf.normal(0, mo.y); mg.position.copy(this.m0).addScaledVector(mn, 0.0015); mg.rotation.x = -Math.asin(mn.y); skull.add(mg);
    this.mz = []; for (let i = 0; i <= 40; i++) { const x = (i / 40 * 2 - 1) * 0.09; this.mz.push(surf.at(x, mo.y).z - this.m0.z); }
    const lipM = softMat(mo.c ?? '#a4503f', { rough: 0.6, rimStr: 0 });
    this.lipU = dynTube(this.mN, 8, lipM); this.lipL = dynTube(this.mN, 8, lipM);
    this.cav = dynStrip(this.mN, softMat(mo.in ?? '#6e2530', { rough: 0.9, rimStr: 0 })); this.teeth = dynStrip(this.mN, softMat('#fffaf2', { rough: 0.4, rimStr: 0 })); this.tongue = dynStrip(this.mN, softMat('#f58c8f', { rough: 0.6, rimStr: 0 }));
    mg.add(this.cav.mesh, this.teeth.mesh, this.tongue.mesh, this.lipL.mesh, this.lipU.mesh);
    this.update(1);
  }
  zAt(x) { const f = clamp((x / 0.09 + 1) / 2) * 40, i = Math.min(39, Math.floor(f)); return lerp(this.mz[i], this.mz[i + 1], f - i); }
  update(dt = 1 / 60) {
    const s = this.s, T = EX[s.expr] || EX.neutral, c = this.cur, k = 1 - Math.exp(-dt * 13);
    for (const key in T) c[key] = lerp(c[key], T[key], k);
    const dz = s.expr === 'dizzy';
    const lx = clamp(c.lx + s.lx + (dz ? Math.cos(s.t * 9) * 0.8 : 0), -1, 1), ly = clamp(c.ly + s.ly + (dz ? Math.sin(s.t * 9) * 0.8 : 0), -1, 1);
    for (const e of this.eyes) {
      const close = -0.22, eU = lerp(c.eU, close, s.blink), eL = lerp(c.eL, Math.max(c.eL, close - 0.05), s.blink);
      e.lidU.rotation.set(-eU, 0, e.s * c.tilt); e.lidL.rotation.set(-eL, 0, e.s * c.tilt * 0.4);
      e.ball.rotation.set(-ly * 0.3, e.toe + lx * 0.34, 0, 'YXZ');
      const hv = eU > -0.05; e.h1.visible = hv; e.h2.visible = hv;
    }
    for (const b of this.brows) { const u = b.userData, up = c.bY + (u.s > 0 ? c.bA : -c.bA * 0.4); b.position.copy(u.c0).addScaledVector(u.n0, 0.001).add(V3(0, up, 0)); b.rotation.z = u.s * c.bR; }
    this.drawMouth(c, clamp(Math.max(c.op, s.mouth)));
  }
  drawMouth(c, open) {
    const mo = this.o.mouth, N = this.mN, w = (mo.w ?? 0.03) * c.mw * (1 + 0.12 * open), h = w * 0.36, hO = (mo.open ?? 0.03) * (0.7 + 0.3 * c.mw);
    const U = [], L = [], Tt = [], Tb = [], Gt = [], Gb = [];
    for (let i = 0; i <= N; i++) {
      const u = i / N * 2 - 1, x = c.mx + u * w, z = this.zAt(x) + 0.0012, e = 1 - u * u;
      const yc = c.sm * h * (u * u - 0.35) + c.as * h * 0.55 * u;
      const yU = yc + open * hO * 0.22 * e, yL = yc - open * hO * e ** 0.75 - 0.0001;
      U.push([x, yU, z + 0.0012]); L.push([x, yL, z + 0.0012]);
      const th = Math.min(0.3 * (yU - yL), 0.007); Tt.push([x * 0.94, yU, z + 0.0006]); Tb.push([x * 0.94, yU - th * Math.sqrt(e), z + 0.0006]);
      const tg = 0.45 * (yU - yL) * Math.sqrt(Math.max(0, 1 - (u / 0.72) ** 2)); Gt.push([x * 0.8, yL + tg, z + 0.0004]); Gb.push([x * 0.8, yL, z + 0.0004]);
    }
    const r = mo.r ?? 0.0032;
    this.lipU.set(U, (t) => r * (0.45 + 0.75 * Math.sin(PI * t) ** 0.5));
    const vis = open > 0.06; this.lipL.mesh.visible = this.cav.mesh.visible = vis; this.teeth.mesh.visible = vis && open > 0.25 && !mo.noTeeth; this.tongue.mesh.visible = vis && open > 0.3;
    if (vis) { this.lipL.set(L, (t) => r * 0.9 * (0.3 + 0.7 * Math.sin(PI * t) ** 0.5)); this.cav.set(U, L); if (this.teeth.mesh.visible) this.teeth.set(Tt, Tb); if (this.tongue.mesh.visible) this.tongue.set(Gt, Gb); }
  }
}

// 每幀改寫頂點的小管子（嘴線）
function dynTube(rows, seg, mat) {
  const n = (rows + 1) * (seg + 1), g = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), idx = [];
  for (let j = 0; j < rows; j++) for (let i = 0; i < seg; i++) { const a = j * (seg + 1) + i, b = a + 1, c = a + seg + 1, d = c + 1; idx.push(a, b, c, b, d, c); }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setIndex(idx);
  const mesh = new THREE.Mesh(g, mat); mesh.frustumCulled = false; mesh.castShadow = false;
  const T = V3(), B = V3(), Nn = V3(), Z = V3(0, 0, 1);
  return { mesh, set(pts, rad) {
    for (let j = 0; j <= rows; j++) {
      const p = pts[j], a = pts[Math.max(0, j - 1)], b = pts[Math.min(rows, j + 1)]; T.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]).normalize();
      Nn.copy(Z).addScaledVector(T, -Z.dot(T)).normalize(); B.crossVectors(T, Nn); const r = rad(j / rows);
      for (let i = 0; i <= seg; i++) { const an = i / seg * PI * 2, cs = Math.cos(an), sn = Math.sin(an), k = (j * (seg + 1) + i) * 3; const nx = B.x * cs + Nn.x * sn, ny = B.y * cs + Nn.y * sn, nz = B.z * cs + Nn.z * sn; pos[k] = p[0] + nx * r; pos[k + 1] = p[1] + ny * r; pos[k + 2] = p[2] + nz * r * 0.7; nor[k] = nx; nor[k + 1] = ny; nor[k + 2] = nz; }
    }
    g.attributes.position.needsUpdate = true; g.attributes.normal.needsUpdate = true;
  } };
}
// 兩條曲線之間的面（口腔、牙齒、舌頭）
function dynStrip(rows, mat) {
  const n = (rows + 1) * 2, g = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), idx = [];
  for (let j = 0; j < rows; j++) { const a = j * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  for (let i = 0; i < n; i++) nor[i * 3 + 2] = 1;
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setIndex(idx);
  const mesh = new THREE.Mesh(g, mat); mesh.frustumCulled = false; mesh.castShadow = false;
  return { mesh, set(A, Bp) { for (let j = 0; j <= rows; j++) { pos.set(A[j], j * 6); pos.set(Bp[j], j * 6 + 3); } g.attributes.position.needsUpdate = true; } };
}

// 鼻子：小小一顆立體鼻頭，鼻尖帶粉紅、下緣略深
export function makeNose(surf, o) {
  const g = dirSurface((d, p) => p.set(d.x * o.rx, d.y * o.ry * (d.y > 0 ? 1.25 : 0.9), d.z * o.rz), { w: 28, h: 20 });
  const a = C(o.skin), tip = C(o.tip), dk = C(o.under);
  paint(g, (p, n, c) => { c.copy(a).lerp(tip, 0.75 * sstep(-0.3, 0.9, n.z) * sstep(0.9, -0.2, n.y)).lerp(dk, 0.5 * sstep(-0.35, -0.95, n.y)); });
  const m = new THREE.Mesh(g, skinMat(0xffffff, { vc: true, rough: 0.42, sss: 0.3 })); m.castShadow = false;
  const p = surf.at(0, o.y), n = surf.normal(0, o.y); m.position.copy(p).addScaledVector(n, o.out ?? 0.004); m.rotation.x = -Math.asin(n.y) - 0.15; return m;
}
// 耳朵：外凸的耳殼，內側凹進去且偏粉紅
export function makeEar(s, o) {
  const g = dirSurface((d, p) => {
    const dish = Math.exp(-((d.y + 0.1) ** 2 + (d.z - 0.1) ** 2) * 3.2) * sstep(0, 0.5, d.x * s);
    p.set(d.x * o.t - s * dish * o.t * 0.9, d.y * o.h * (1 + 0.12 * d.z), d.z * o.w * (1 - 0.18 * sstep(0.2, -1, d.y)));
  }, { w: 36, h: 28 });
  const a = C(o.skin), pk = C(o.pink);
  paint(g, (p, n, c) => { const dish = Math.exp(-((p.y / o.h + 0.1) ** 2 + (p.z / o.w - 0.1) ** 2) * 2.6) * sstep(-0.2, 0.6, n.x * s); c.copy(a).lerp(pk, 0.3 + 0.6 * dish); });
  const m = new THREE.Mesh(g, skinMat(0xffffff, { vc: true, sss: 0.5 })); return m;
}
