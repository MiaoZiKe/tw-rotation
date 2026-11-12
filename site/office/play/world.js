// 小房間（辦公室一角）＋可互動物件＋簡單剛體物理（球、箱子、彈跳床）
import * as THREE from 'three';
import { DETAIL } from './soft.js';

export const G = 16;                       // 重力（公尺／秒²；角色約 0.75 公尺高，取大一點比較有精神）
export const BOUNDS = { x0: -4, x1: 4, z0: -3, z1: 3.2 };
const STEP = 0.14;                         // 能直接走上去的高度

// 圓角方塊：把頂點集中到邊角帶，再往內縮的方塊外推成圓角（沒有稜線）
export function rbox(w, h, d, r, k = 5) {
  k = Math.max(2, Math.round(k * DETAIL.k)); const N = k * 2 + 4, g = new THREE.BoxGeometry(w, h, d, N, N, N);
  const p = g.attributes.position, n = g.attributes.normal, half = [w / 2, h / 2, d / 2], v = [0, 0, 0], inn = [0, 0, 0];
  const a = k / N;
  for (let i = 0; i < p.count; i++) {
    v[0] = p.getX(i); v[1] = p.getY(i); v[2] = p.getZ(i);
    for (let j = 0; j < 3; j++) {
      const H = half[j], u = (v[j] + H) / (2 * H);
      let t; if (u < a) t = -H + r * (u / a); else if (u > 1 - a) t = H - r * ((1 - u) / a); else t = -H + r + (2 * H - 2 * r) * ((u - a) / (1 - 2 * a));
      v[j] = t; inn[j] = Math.max(-H + r, Math.min(H - r, t));
    }
    let dx = v[0] - inn[0], dy = v[1] - inn[1], dz = v[2] - inn[2]; const L = Math.hypot(dx, dy, dz) || 1; dx /= L; dy /= L; dz /= L;
    p.setXYZ(i, inn[0] + dx * r, inn[1] + dy * r, inn[2] + dz * r); n.setXYZ(i, dx, dy, dz);
  }
  return g;
}
export function lathe(pts, seg = 56, smooth = 48) {
  seg = Math.max(18, Math.round(seg * DETAIL.k)); smooth = Math.max(14, Math.round(smooth * DETAIL.k));
  const c = new THREE.CatmullRomCurve3(pts.map(q => new THREE.Vector3(q[0], q[1], 0)), false, 'catmullrom', 0.35);
  const ps = c.getPoints(smooth).map(q => new THREE.Vector2(Math.max(0, q.x), q.y));
  ps[0].x = 0; ps[ps.length - 1].x = pts[pts.length - 1][0] === 0 ? 0 : ps[ps.length - 1].x;
  return new THREE.LatheGeometry(ps, seg);
}
const std = (color, rough = 0.85, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...o });
function ctex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; }

export class World {
  constructor(scene, fx, mobile) {
    this.scene = scene; this.fx = fx; this.solids = []; this.dyn = []; this.pick = []; this.uses = [];
    this.build(mobile);
  }
  add(geo, mat, x, y, z, o = {}) {
    const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = o.cast !== false; m.receiveShadow = o.recv !== false;
    (o.parent || this.scene).add(m); return m;
  }
  build(mobile) {
    const S = this.scene, B = BOUNDS;
    // ── 地板（小模型台座）、地毯
    const floorT = ctex(1024, 1024, (g, w, h) => {
      g.fillStyle = '#f3dfc4'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 12; i++) {
        const y = i * h / 12; g.fillStyle = `rgba(${i % 2 ? '255,246,230' : '226,196,160'},${0.10 + (i * 37 % 5) * 0.02})`; g.fillRect(0, y, w, h / 12);
        g.fillStyle = 'rgba(190,150,110,.20)'; g.fillRect(0, y, w, 2);
        const off = (i * 263) % 400; for (let x = off; x < w; x += 420) g.fillRect(x, y, 2, h / 12);
      }
    });
    const slab = this.add(rbox(B.x1 - B.x0 + 0.6, 0.5, B.z1 - B.z0 + 0.6, 0.16), std(0xf3dfc4, 0.8, { map: floorT }), (B.x0 + B.x1) / 2, -0.25, (B.z0 + B.z1) / 2, { cast: false });
    this.floor = slab; slab.userData.floor = true;
    const rugT = ctex(512, 512, (g, w) => {
      const c = w / 2, cols = ['#fff6ea', '#ffd9cf', '#fff6ea', '#cfeadb', '#fff6ea', '#ffe7b3'];
      cols.forEach((col, i) => { g.fillStyle = col; g.beginPath(); g.arc(c, c, c * (0.97 - i * 0.155), 0, 7); g.fill(); });
      const gr = g.createRadialGradient(c, c, c * 0.9, c, c, c); gr.addColorStop(0, 'rgba(255,246,234,0)'); gr.addColorStop(1, 'rgba(255,246,234,1)');
      g.globalCompositeOperation = 'destination-out'; const e = g.createRadialGradient(c, c, c * 0.955, c, c, c); e.addColorStop(0, 'rgba(0,0,0,0)'); e.addColorStop(1, 'rgba(0,0,0,1)'); g.fillStyle = e; g.fillRect(0, 0, w, w);
    });
    const rug = this.add(new THREE.CircleGeometry(1.75, 72), std(0xffffff, 0.95, { map: rugT, transparent: true }), 0, 0.006, 0.35, { cast: false });
    rug.rotation.x = -Math.PI / 2;
    // ── 牆
    const wallT = ctex(64, 512, (g, w, h) => {
      g.fillStyle = '#fdf1df'; g.fillRect(0, 0, w, h); g.fillStyle = '#d7eadb'; g.fillRect(0, h * 0.68, w, h * 0.32); g.fillStyle = '#fffaf2'; g.fillRect(0, h * 0.665, w, h * 0.022);
      g.fillStyle = '#fffaf2'; g.fillRect(0, h * 0.955, w, h * 0.045);
    });
    const wm = std(0xffffff, 0.92, { map: wallT });
    const WH = 3.0, W = B.x1 - B.x0 + 0.6, D = B.z1 - B.z0 + 0.6;
    this.add(rbox(W, WH, 0.22, 0.09), wm, 0, WH / 2, B.z0 - 0.19, { cast: false });
    const lw = this.add(rbox(0.22, WH, D - 0.2, 0.09), wm, B.x0 - 0.19, WH / 2, (B.z0 + B.z1) / 2 + 0.1, { cast: false });
    // UV 讓左牆貼圖方向正確（BoxGeometry 的側面本來就是直向的）
    // ── 窗（後牆，辦公桌上方）
    const skyT = ctex(256, 256, (g, w, h) => {
      const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#bfe6ff'); gr.addColorStop(0.7, '#fff3df'); gr.addColorStop(1, '#ffe1c2'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
      g.fillStyle = 'rgba(255,255,255,.9)'; for (const [x, y, r] of [[60, 80, 26], [90, 70, 32], [124, 84, 24], [180, 150, 20], [205, 142, 26]]) { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); }
    });
    const wx = 1.9, wy = 1.75, wz = B.z0 - 0.075;
    this.add(rbox(1.9, 1.3, 0.12, 0.05), std(0xfffaf2, 0.7), wx, wy, wz, { cast: false });
    this.add(new THREE.PlaneGeometry(1.66, 1.06), new THREE.MeshBasicMaterial({ map: skyT, toneMapped: false }), wx, wy, wz + 0.065, { cast: false, recv: false });
    this.add(rbox(0.07, 1.1, 0.06, 0.03), std(0xfffaf2, 0.7), wx, wy, wz + 0.07, { cast: false });
    this.add(rbox(1.7, 0.07, 0.06, 0.03), std(0xfffaf2, 0.7), wx, wy, wz + 0.07, { cast: false });
    this.add(rbox(2.06, 0.08, 0.24, 0.04), std(0xfffaf2, 0.7), wx, wy - 0.68, wz + 0.1, { cast: false });
    // 灑在地上的窗光
    const beamT = ctex(256, 256, (g, w, h) => {
      g.filter = 'blur(10px)'; g.fillStyle = 'rgba(255,236,190,.9)';
      for (const [x, y] of [[40, 40], [136, 40], [40, 136], [136, 136]]) { g.beginPath(); g.roundRect(x, y, 80, 80, 10); g.fill(); }
    });
    const beam = this.add(new THREE.PlaneGeometry(2.6, 2.3), new THREE.MeshBasicMaterial({ map: beamT, transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending, depthWrite: false }), 0.9, 0.012, -0.9, { cast: false, recv: false });
    beam.rotation.x = -Math.PI / 2; beam.rotation.z = 0.5; beam.scale.set(1, 1.25, 1); beam.renderOrder = 2;
    // ── 沙發
    const sx = -1.75, sofaC = std(0xffc7b6, 0.95), cush = std(0xffdccf, 0.95);
    this.add(rbox(2.3, 0.4, 0.98, 0.13), sofaC, sx, 0.2, -2.42);
    this.add(rbox(2.3, 0.72, 0.3, 0.14), sofaC, sx, 0.66, -2.78);
    for (const s of [-1, 1]) this.add(rbox(0.3, 0.66, 0.98, 0.14), sofaC, sx + s * 1.1, 0.33, -2.42);
    for (const s of [-1, 1]) this.add(rbox(0.9, 0.2, 0.74, 0.09), cush, sx + s * 0.46, 0.44, -2.34);
    const pil = this.add(rbox(0.42, 0.42, 0.16, 0.075), std(0xbfe6d2, 0.95), sx - 0.62, 0.74, -2.56); pil.rotation.set(-0.25, 0.2, 0.12);
    const sofaSeat = { kind: 'box', x0: sx - 0.95, x1: sx + 0.95, z0: -2.72, z1: -1.95, top: 0.54, soft: 0.25, tag: 'sofa' };
    this.solids.push(sofaSeat,
      { kind: 'box', x0: sx - 1.25, x1: sx - 0.95, z0: -2.95, z1: -1.93, top: 0.66 }, { kind: 'box', x0: sx + 0.95, x1: sx + 1.25, z0: -2.95, z1: -1.93, top: 0.66 },
      { kind: 'box', x0: sx - 1.25, x1: sx + 1.25, z0: -2.95, z1: -2.66, top: 1.02 });
    this.uses.push({ type: 'sit', solid: sofaSeat, seat: new THREE.Vector3(sx + 0.46, 0.54, -2.3), from: new THREE.Vector3(sx + 0.46, 0, -1.45), yaw: 0, name: '沙發' });
    this.sofaUse = this.uses[this.uses.length - 1];
    // ── 立燈
    this.add(lathe([[0, 0], [0.16, 0], [0.17, 0.03], [0.04, 0.06], [0.03, 1.2], [0, 1.2]], 32), std(0xfffaf2, 0.6), -0.3, 0, -2.62);
    const shade = this.add(lathe([[0.13, 0], [0.2, -0.02], [0.27, -0.28], [0.26, -0.3]], 40), std(0xffe6a8, 0.7, { emissive: 0xffc56a, emissiveIntensity: 0.55, side: THREE.DoubleSide }), -0.3, 1.5, -2.62, { cast: false });
    this.solids.push({ kind: 'cyl', x: -0.3, z: -2.62, rad: 0.15, top: 1.5 });
    // ── 辦公桌＋螢幕＋圓凳
    const wood = std(0xf6d6a6, 0.75), white = std(0xfffaf2, 0.7);
    this.add(rbox(1.7, 0.09, 0.66, 0.04), wood, 1.9, 0.64, -2.62);
    for (const [x, z] of [[-0.74, -0.24], [0.74, -0.24], [-0.74, 0.24], [0.74, 0.24]]) this.add(lathe([[0, 0], [0.045, 0], [0.05, 0.3], [0.06, 0.6], [0, 0.6]], 20), white, 1.9 + x, 0, -2.62 + z);
    this.solids.push({ kind: 'box', x0: 1.05, x1: 2.75, z0: -2.95, z1: -2.29, top: 0.69 });
    const scrT = ctex(256, 160, (g, w, h) => {
      const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#26304f'); gr.addColorStop(1, '#333e66'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
      const cols = ['#ff9fb5', '#ffd27a', '#8fe3c4', '#9fc4ff', '#ffb38a', '#c6a8ff', '#8fe3c4'];
      cols.forEach((c, i) => { const bh = 30 + ((i * 53) % 70); g.fillStyle = c; g.beginPath(); g.roundRect(26 + i * 30, h - 24 - bh, 20, bh, 6); g.fill(); });
      g.strokeStyle = '#fff'; g.lineWidth = 4; g.lineJoin = 'round'; g.beginPath(); [96, 80, 88, 56, 62, 34, 28].forEach((y, i) => i ? g.lineTo(36 + i * 30, y) : g.moveTo(36, y)); g.stroke();
    });
    this.add(rbox(0.74, 0.5, 0.05, 0.024), white, 1.9, 1.06, -2.8);
    this.add(new THREE.PlaneGeometry(0.66, 0.42), new THREE.MeshBasicMaterial({ map: scrT, toneMapped: false }), 1.9, 1.06, -2.772, { cast: false, recv: false });
    this.add(lathe([[0, 0], [0.14, 0], [0.14, 0.02], [0.03, 0.04], [0.025, 0.16], [0, 0.16]], 24), white, 1.9, 0.685, -2.8);
    this.add(rbox(0.5, 0.03, 0.18, 0.014), white, 1.9, 0.7, -2.5);
    const mug = this.add(lathe([[0, 0], [0.05, 0], [0.055, 0.02], [0.055, 0.1], [0.048, 0.1], [0.045, 0.03], [0, 0.03]], 24), std(0xffb7c5, 0.5), 2.5, 0.685, -2.55);
    const stool = { kind: 'cyl', x: 1.9, z: -1.72, rad: 0.33, top: 0.4, soft: 0.2, tag: 'stool' };
    this.add(lathe([[0, 0], [0.26, 0], [0.31, 0.03], [0.33, 0.14], [0.33, 0.3], [0.29, 0.385], [0.18, 0.4], [0, 0.4]], 48), std(0xbfdcff, 0.95), stool.x, 0, stool.z);
    this.solids.push(stool);
    this.uses.push({ type: 'sit', solid: stool, seat: new THREE.Vector3(stool.x, 0.4, stool.z), from: new THREE.Vector3(stool.x - 0.3, 0, stool.z + 0.85), yaw: 0.25, name: '圓凳' });
    // ── 盆栽（葉子會晃）
    const px = 3.45, pz = -2.5;
    this.add(lathe([[0, 0], [0.2, 0], [0.23, 0.03], [0.29, 0.36], [0.3, 0.42], [0.26, 0.43], [0.24, 0.38], [0, 0.38]], 40), std(0xfff1dc, 0.7), px, 0, pz);
    this.plant = new THREE.Group(); this.plant.position.set(px, 0.4, pz); S.add(this.plant);
    const leafG = new THREE.SphereGeometry(1, 28, 20), leafM = [std(0x8fd4a0, 0.7), std(0xa9e0b0, 0.7), std(0x79c690, 0.7)];
    this.leaves = [];
    for (let i = 0; i < 9; i++) {
      const piv = new THREE.Group(), a = i * 2.4, tilt = 0.25 + (i % 3) * 0.3, len = 0.42 + (i % 4) * 0.1;
      piv.rotation.set(0, a, 0); const arm = new THREE.Group(); arm.rotation.z = tilt; piv.add(arm);
      const lf = new THREE.Mesh(leafG, leafM[i % 3]); lf.scale.set(0.13, len * 0.5, 0.035); lf.position.y = len * 0.5; lf.castShadow = true; arm.add(lf);
      this.plant.add(piv); this.leaves.push({ arm, tilt, ph: i * 1.7 });
    }
    this.plantShake = 0;
    this.solids.push({ kind: 'cyl', x: px, z: pz, rad: 0.3, top: 1.2, tag: 'plant' });
    // ── 彈跳床
    const tr = this.tramp = { kind: 'cyl', x: 2.75, z: 0.55, rad: 0.72, top: 0.3, bounce: true, tag: 'tramp', dip: 0, dipV: 0 };
    const ring = this.add(new THREE.TorusGeometry(0.76, 0.075, 20, 72), std(0xffd27a, 0.6), tr.x, 0.3, tr.z); ring.rotation.x = Math.PI / 2;
    const memG = new THREE.CircleGeometry(0.74, 48, 0, Math.PI * 2); memG.rotateX(-Math.PI / 2);
    // 細分膜面：用同心圓讓中央可以凹下去
    const mem = new THREE.Mesh(new THREE.RingGeometry(0.0001, 0.74, 56, 10).rotateX(-Math.PI / 2), std(0x9adfd2, 0.8, { side: THREE.DoubleSide }));
    mem.position.set(tr.x, 0.3, tr.z); mem.receiveShadow = true; S.add(mem); tr.mem = mem; tr.base = mem.geometry.attributes.position.array.slice();
    for (let i = 0; i < 5; i++) { const a = i / 5 * 6.283; this.add(lathe([[0, 0], [0.05, 0], [0.05, 0.28], [0, 0.28]], 16), std(0xfffaf2, 0.6), tr.x + Math.cos(a) * 0.72, 0, tr.z + Math.sin(a) * 0.72); }
    this.solids.push(tr);
    this.uses.push({ type: 'hop', solid: tr, seat: new THREE.Vector3(tr.x, 0.3, tr.z), from: new THREE.Vector3(tr.x - 1.25, 0, tr.z + 0.2), yaw: 0, name: '彈跳床' });
    // ── 小窩（睡覺用）
    const bed = { kind: 'cyl', x: -3.05, z: 0.5, rad: 0.5, top: 0.1, tag: 'bed' };
    const bt = this.add(new THREE.TorusGeometry(0.56, 0.13, 24, 64), std(0xcdbdf2, 0.98), bed.x, 0.13, bed.z); bt.rotation.x = Math.PI / 2;
    this.add(lathe([[0, 0], [0.5, 0], [0.54, 0.04], [0.5, 0.09], [0.3, 0.105], [0, 0.11]], 48), std(0xfff3e6, 0.98), bed.x, 0, bed.z);
    this.solids.push(bed);
    this.uses.push({ type: 'sleep', solid: bed, seat: new THREE.Vector3(bed.x, 0.1, bed.z), from: new THREE.Vector3(bed.x + 0.9, 0, bed.z + 0.3), yaw: 0.9, name: '小窩' });
    this.bedUse = this.uses[this.uses.length - 1];
    // ── 左牆層板與相框
    const shx = B.x0 - 0.02;
    this.add(rbox(0.26, 0.05, 1.3, 0.022), wood, shx + 0.12, 1.55, 0.4);
    [[0xffb7c5, 0.3, 0.07], [0xbfe6d2, 0.26, 0.06], [0xffe1a0, 0.33, 0.08], [0xbfd4ff, 0.28, 0.06]].forEach(([c, h, w], i) => { const b = this.add(rbox(0.19, h, w, 0.016), std(c, 0.8), shx + 0.13, 1.575 + h / 2, -0.05 + i * 0.095); if (i === 3) { b.rotation.x = -0.28; b.position.z += 0.05; } });
    this.add(lathe([[0, 0], [0.07, 0], [0.085, 0.1], [0.07, 0.1], [0, 0.09]], 24), std(0xffc7b6, 0.7), shx + 0.13, 1.575, 0.78);
    const cact = this.add(new THREE.SphereGeometry(1, 24, 18), std(0x8fd4a0, 0.8), shx + 0.13, 1.74, 0.78); cact.scale.set(0.06, 0.1, 0.06);
    const picT = ctex(256, 256, (g, w) => {
      g.fillStyle = '#fff6ea'; g.fillRect(0, 0, w, w); g.fillStyle = '#ffd9a0'; g.beginPath(); g.arc(128, 150, 62, 0, 7); g.fill();
      g.fillStyle = '#ffb7a0'; g.beginPath(); g.arc(128, 150, 40, 0, 7); g.fill(); g.fillStyle = '#cfeadb'; g.beginPath(); g.ellipse(128, 236, 150, 44, 0, 0, 7); g.fill();
    });
    this.add(rbox(0.7, 0.7, 0.06, 0.03), white, sx, 1.95, B.z0 - 0.06, { cast: false });
    this.add(new THREE.PlaneGeometry(0.56, 0.56), std(0xffffff, 0.9, { map: picT }), sx, 1.95, B.z0 - 0.028, { cast: false });
    // ── 可互動的動態物件
    const blobM = new THREE.MeshBasicMaterial({ map: this.fx.T.shadow, transparent: true, depthWrite: false, opacity: 0.55 });
    const mkShadow = (r) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), blobM.clone()); m.rotation.x = -Math.PI / 2; m.scale.setScalar(r * 2.6); m.renderOrder = 3; S.add(m); return m; };
    this.mkShadow = mkShadow;
    const ballT = ctex(512, 256, (g, w, h) => {
      const cols = ['#ff9fb5', '#fffaf2', '#ffd27a', '#fffaf2', '#8fdcc8', '#fffaf2'];
      cols.forEach((c, i) => { g.fillStyle = c; g.fillRect(i * w / 6, 0, w / 6 + 1, h); });
      g.fillStyle = '#fffaf2'; g.fillRect(0, 0, w, 14); g.fillRect(0, h - 14, w, 14);
    });
    const mkBall = (r, x, z, mat, e, m) => {
      const mesh = this.add(new THREE.SphereGeometry(r, 48, 32), mat, x, r, z, { recv: false });
      const b = { kind: 'ball', p: mesh.position, v: new THREE.Vector3(), r, e, m, mesh, shadow: mkShadow(r), held: false, quiet: 0 };
      mesh.userData.dyn = b; this.dyn.push(b); this.pick.push(mesh); return b;
    };
    this.bigBall = mkBall(0.27, 1.0, 1.45, std(0xffffff, 0.45, { map: ballT }), 0.72, 0.5);
    this.ball = mkBall(0.13, -0.5, 2.0, std(0xff9a8a, 0.4), 0.78, 0.25);
    const boxT = ctex(256, 256, (g, w) => {
      g.fillStyle = '#ffe6ae'; g.fillRect(0, 0, w, w); g.strokeStyle = '#ffd27a'; g.lineWidth = 10; g.beginPath(); g.roundRect(26, 26, w - 52, w - 52, 30); g.stroke();
      g.fillStyle = '#ffc56a'; g.beginPath(); const k = 34, cx = 128, cy = 132;
      g.moveTo(cx, cy + k * 0.78); g.bezierCurveTo(cx - k * 1.25, cy - k * 0.05, cx - k * 0.62, cy - k * 0.98, cx, cy - k * 0.38); g.bezierCurveTo(cx + k * 0.62, cy - k * 0.98, cx + k * 1.25, cy - k * 0.05, cx, cy + k * 0.78); g.fill();
    });
    const bh = 0.27, boxMesh = this.add(rbox(bh * 2, bh * 2, bh * 2, 0.07), std(0xffffff, 0.85, { map: boxT }), -1.5, bh, 1.25);
    const boxS = { kind: 'box', x0: 0, x1: 0, z0: 0, z1: 0, top: bh * 2, tag: 'box', dyn: true };
    this.box = { kind: 'box', p: boxMesh.position, v: new THREE.Vector3(), half: bh, mesh: boxMesh, solid: boxS, shadow: mkShadow(bh * 1.25) };
    boxS.ref = this.box; this.solids.push(boxS); this.syncBox();
    // 家具點擊（用隱形的簡單形狀當點擊範圍）
    for (const u of this.uses) {
      const s = u.solid, geo = s.kind === 'cyl' ? new THREE.CylinderGeometry(s.rad, s.rad, s.top + 0.1, 20) : new THREE.BoxGeometry(s.x1 - s.x0, s.top + 0.1, s.z1 - s.z0);
      const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ visible: false })); m.position.set(s.kind === 'cyl' ? s.x : (s.x0 + s.x1) / 2, (s.top + 0.1) / 2, s.kind === 'cyl' ? s.z : (s.z0 + s.z1) / 2);
      m.userData.use = u; S.add(m); this.pick.push(m);
    }
  }
  syncBox() { const b = this.box, s = b.solid; s.x0 = b.p.x - b.half; s.x1 = b.p.x + b.half; s.z0 = b.p.z - b.half; s.z1 = b.p.z + b.half; }
  inside(s, x, z, m = 0) { return s.kind === 'cyl' ? Math.hypot(x - s.x, z - s.z) < s.rad + m : (x > s.x0 - m && x < s.x1 + m && z > s.z0 - m && z < s.z1 + m); }
  groundAt(x, z, y, tol = STEP) {
    let h = 0, hit = null;
    for (const s of this.solids) if (s.top <= y + tol && s.top > h && this.inside(s, x, z)) { h = s.top; hit = s; }
    return { h, s: hit };
  }
  // 把圓（角色、球、箱子）推出擋路的家具與房間邊界；v 有給就把撞進去的速度分量去掉（e＝反彈係數）
  resolve(p, rad, y, v, e = 0, ignore = null, self = null) {
    let hit = null;
    for (const s of this.solids) {
      if (s === ignore || s === self || s.top <= y + STEP) continue;
      let nx = 0, nz = 0, pen = 0;
      if (s.kind === 'cyl') { const dx = p.x - s.x, dz = p.z - s.z, d = Math.hypot(dx, dz); if (d < rad + s.rad) { pen = rad + s.rad - d; nx = d > 1e-5 ? dx / d : 1; nz = d > 1e-5 ? dz / d : 0; } }
      else {
        const qx = Math.max(s.x0, Math.min(s.x1, p.x)), qz = Math.max(s.z0, Math.min(s.z1, p.z)); let dx = p.x - qx, dz = p.z - qz; const d = Math.hypot(dx, dz);
        if (d > 1e-6) { if (d < rad) { pen = rad - d; nx = dx / d; nz = dz / d; } }
        else { const l = p.x - s.x0, r = s.x1 - p.x, b = p.z - s.z0, f = s.z1 - p.z, m = Math.min(l, r, b, f); if (m === l) { nx = -1; pen = l + rad; } else if (m === r) { nx = 1; pen = r + rad; } else if (m === b) { nz = -1; pen = b + rad; } else { nz = 1; pen = f + rad; } }
      }
      if (pen > 0) { p.x += nx * pen; p.z += nz * pen; hit = s; if (v) { const vn = v.x * nx + v.z * nz; if (vn < 0) { v.x -= (1 + e) * vn * nx; v.z -= (1 + e) * vn * nz; } } }
    }
    const B = BOUNDS;
    if (p.x < B.x0 + rad) { p.x = B.x0 + rad; if (v && v.x < 0) v.x *= -e; hit = hit || 'wall'; } if (p.x > B.x1 - rad) { p.x = B.x1 - rad; if (v && v.x > 0) v.x *= -e; hit = hit || 'wall'; }
    if (p.z < B.z0 + rad) { p.z = B.z0 + rad; if (v && v.z < 0) v.z *= -e; hit = hit || 'wall'; } if (p.z > B.z1 - rad) { p.z = B.z1 - rad; if (v && v.z > 0) v.z *= -e; hit = hit || 'wall'; }
    return hit;
  }
  // 角色推箱子：箱子吃掉重疊量（被牆擋住時才換角色被擋），並帶著角色的速度滑出去
  pushBox(ch) {
    const b = this.box, R = ch.R * 0.8;
    if (ch.pos.y >= b.solid.top - STEP) return;
    const qx = Math.max(b.p.x - b.half, Math.min(b.p.x + b.half, ch.pos.x)), qz = Math.max(b.p.z - b.half, Math.min(b.p.z + b.half, ch.pos.z));
    const dx = ch.pos.x - qx, dz = ch.pos.z - qz, d = Math.hypot(dx, dz);
    if (d >= R || d < 1e-5) return;
    const nx = dx / d, nz = dz / d, pen = R - d, vn = -(ch.vel.x * nx + ch.vel.z * nz);
    if (vn < 0.05) return;
    b.p.x -= nx * pen; b.p.z -= nz * pen; this.resolve(b.p, b.half * 1.02, 0, null, 0, null, b.solid); this.syncBox();
    const cur = -(b.v.x * nx + b.v.z * nz), want = vn * 0.9; if (cur < want) { b.v.x -= (want - cur) * nx; b.v.z -= (want - cur) * nz; }
    ch.pushing = 0.12;
  }
  bounceTramp(impact) { const t = this.tramp; t.dipV -= Math.min(impact, 10) * 0.9; this.fx.sfx('boing'); }
  // 一個物理子步
  step(h, ch) {
    const fx = this.fx;
    // 箱子：地面摩擦滑行
    const b = this.box, sp0 = Math.hypot(b.v.x, b.v.z);
    if (sp0 > 0) {
      b.p.x += b.v.x * h; b.p.z += b.v.z * h; const k = Math.max(0, sp0 - 7 * h) / sp0; b.v.x *= k; b.v.z *= k;
      this.resolve(b.p, b.half * 1.02, 0, b.v, 0, null, b.solid); this.syncBox();
    }
    for (const o of this.dyn) {
      if (o.held) continue;
      const p = o.p, v = o.v, r = o.r;
      v.y -= G * h; p.addScaledVector(v, h);
      const gr = this.groundAt(p.x, p.z, p.y - r + 0.02 - Math.min(0, v.y * h), 0.06);
      let onG = false;
      if (p.y - r <= gr.h) {
        p.y = gr.h + r;
        if (v.y < -0.9) {
          const imp = -v.y;
          if (gr.s && gr.s.bounce) { v.y = Math.min(9, imp * 0.92 + 1.2); this.bounceTramp(imp); }
          else { v.y = imp * o.e * (gr.s && gr.s.soft ? 0.5 : 1); if (imp > 2) fx.sfx('land', imp / 8); }
          v.x *= 0.96; v.z *= 0.96;
        } else { v.y = 0; onG = true; }
      }
      if (onG) { const sp = Math.hypot(v.x, v.z), k = Math.max(0, sp - (0.5 + sp * 0.35) * h) / (sp || 1); v.x *= k; v.z *= k; }
      this.resolve(p, r, p.y - r, v, o.e);
      if (p.y > 3.4 && v.y > 0) v.y *= -0.3;
      // 跟角色碰撞（角色當成一顆很重的球）
      if (!o.caught) {
        const cx = ch.pos.x, cyy = ch.pos.y + ch.R, cz = ch.pos.z, dx = p.x - cx, dy = p.y - cyy, dz = p.z - cz, d = Math.hypot(dx, dy, dz), RR = r + ch.R * 0.92;
        if (d < RR && d > 1e-5) {
          const nx = dx / d, ny = dy / d, nz = dz / d, rvx = v.x - ch.vel.x, rvy = v.y - ch.vel.y, rvz = v.z - ch.vel.z, vn = rvx * nx + rvy * ny + rvz * nz;
          p.x += nx * (RR - d); p.y += ny * (RR - d); p.z += nz * (RR - d);
          if (vn < 0) {
            const j = -(1 + 0.6) * vn; v.x += j * nx; v.y += j * ny; v.z += j * nz;
            const cs = Math.hypot(ch.vel.x, ch.vel.z), bs = Math.hypot(rvx + ch.vel.x, rvy + ch.vel.y, rvz + ch.vel.z);
            if (cs > 0.6 && cs >= bs) { v.y += 0.9 + cs * 0.45; if (-vn > 0.8) { fx.sfx('kick'); ch.onKick && ch.onKick(o); } }
            else if (-vn > 2.2) ch.onBallHit(o, -vn, nx, ny, nz);
          }
        }
      }
      // 球跟球
      for (const q of this.dyn) {
        if (q === o || q.held) continue; const dx = q.p.x - p.x, dy = q.p.y - p.y, dz = q.p.z - p.z, d = Math.hypot(dx, dy, dz), RR = r + q.r;
        if (d < RR && d > 1e-5) {
          const nx = dx / d, ny = dy / d, nz = dz / d, vn = (q.v.x - v.x) * nx + (q.v.y - v.y) * ny + (q.v.z - v.z) * nz, mt = o.m + q.m, pen = RR - d;
          p.x -= nx * pen * q.m / mt; p.y -= ny * pen * q.m / mt; p.z -= nz * pen * q.m / mt; q.p.x += nx * pen * o.m / mt; q.p.y += ny * pen * o.m / mt; q.p.z += nz * pen * o.m / mt;
          if (vn < 0) { const j = -(1.7) * vn / (1 / o.m + 1 / q.m); v.x -= j / o.m * nx; v.y -= j / o.m * ny; v.z -= j / o.m * nz; q.v.x += j / q.m * nx; q.v.y += j / q.m * ny; q.v.z += j / q.m * nz; }
        }
      }
      // 滾動
      const sp = Math.hypot(v.x, v.z);
      if (sp > 0.01) { _ax.set(v.z, 0, -v.x).normalize(); o.mesh.rotateOnWorldAxis(_ax, sp * h / r); }
      if (onG && sp < 0.04) { v.x = v.z = 0; }
      // 球撞到盆栽 → 葉子晃
      if (Math.hypot(p.x - 3.45, p.z + 2.5) < 0.55 + r && sp > 0.5) this.plantShake = Math.min(1.5, this.plantShake + sp * 0.02);
    }
  }
  update(dt, t, ch) {
    // 彈跳床膜面：彈簧
    const tr = this.tramp; tr.dipV += (-260 * tr.dip - 9 * tr.dipV) * dt; tr.dip += tr.dipV * dt; tr.dip = Math.max(-0.26, Math.min(0.14, tr.dip));
    let load = 0, lx = 0, lz = 0;
    if (ch.grounded && ch.groundS === tr) { load = -0.05; lx = ch.pos.x - tr.x; lz = ch.pos.z - tr.z; }
    const pa = tr.mem.geometry.attributes.position, a = pa.array, b0 = tr.base;
    for (let i = 0; i < pa.count; i++) { const x = b0[i * 3], z = b0[i * 3 + 2], rr = Math.hypot(x, z) / 0.74, w = Math.cos(Math.min(1, rr) * Math.PI / 2); const dl = Math.hypot(x - lx, z - lz); a[i * 3 + 1] = (tr.dip) * w * w + load * Math.exp(-dl * dl / 0.08) * w; }
    pa.needsUpdate = true; tr.mem.geometry.computeVertexNormals();
    // 盆栽
    if (Math.hypot(ch.pos.x - 3.45, ch.pos.z + 2.5) < 0.75 && Math.hypot(ch.vel.x, ch.vel.z) > 0.5) this.plantShake = Math.min(1.5, this.plantShake + dt * 4);
    this.plantShake *= Math.exp(-dt * 1.6);
    for (const l of this.leaves) l.arm.rotation.z = l.tilt + Math.sin(t * 1.1 + l.ph) * 0.025 + Math.sin(t * 13 + l.ph) * 0.12 * this.plantShake;
    // 接觸陰影
    for (const o of this.dyn) { const g = this.groundAt(o.p.x, o.p.z, o.p.y - o.r + 0.05, 0.06), hgt = o.p.y - o.r - g.h; o.shadow.position.set(o.p.x, g.h + 0.014, o.p.z); o.shadow.material.opacity = 0.55 * Math.max(0.15, 1 - hgt * 0.6); o.shadow.scale.setScalar(o.r * 2.6 * (1 + hgt * 0.5)); }
    this.box.shadow.position.set(this.box.p.x, 0.013, this.box.p.z);
  }
}
const _ax = new THREE.Vector3();
