// 肢體「從身體長出來」的幾何：根部張開、埋進身體、往末端收細
// 搭配 soft.js 的 root 材質（根部附近的顏色與法線朝身體表面混合），交界處沒有接縫。
import * as THREE from 'three';
import { DETAIL } from './soft.js';
const V3 = THREE.Vector3;

// ── 靜態：沿 +y 長的錐形體（耳朵、尾巴、觸手），根在 y=0（埋進身體），尖端在 y=1，單位半徑 1（再用 scale 放大）
//   q＝尖端半徑比例，p＝張開的曲線（越大越快收細），cap＝尖端圓頭佔的長度比例，bulge＝中段鼓起（0~0.4）
const cache = new Map();
export function taperGeo({ q = 0.4, p = 2.2, cap = 0.25, bulge = 0 } = {}) {
  const k = `${q}|${p}|${cap}|${bulge}|${DETAIL.k}`; if (cache.has(k)) return cache.get(k);
  const pts = [new THREE.Vector2(0, 0)], N = Math.max(8, Math.round(14 * DETAIL.k)), tc = 1 - cap;
  const body = (t) => (q + (1 - q) * Math.pow(1 - t, p)) * (1 + bulge * Math.sin(Math.PI * Math.min(1, t / tc)));
  for (let i = 0; i <= N; i++) { const t = i / N * tc; pts.push(new THREE.Vector2(body(t), t)); }
  const rc = body(tc), M = Math.max(5, Math.round(8 * DETAIL.k));
  for (let i = 1; i <= M; i++) { const a = i / M * Math.PI / 2; pts.push(new THREE.Vector2(rc * Math.cos(a), tc + cap * Math.sin(a))); }
  const g = new THREE.LatheGeometry(pts, Math.max(12, Math.round(20 * DETAIL.k)));
  cache.set(k, g); return g;
}

// ── 動態：一隻角色的所有手腳「皮膚」合成一個網格（一次繪製）
//   每條肢體 ＝ 根（身體座標裡的錨點，埋在身體裡）→ 末端（手／腳的球心），路徑略彎，粗細 rr→rt，根部張開
export class LimbSkin {
  constructor(n, mat, sides = 24, rings = 14) {
    this.n = n; this.S = sides; this.Rg = rings; this.per = sides * rings;
    const g = this.geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(n * this.per * 3); this.nor = new Float32Array(n * this.per * 3);
    const idx = [];
    for (let l = 0; l < n; l++) for (let r = 0; r < rings - 1; r++) for (let s = 0; s < sides; s++) {
      const a = l * this.per + r * sides + s, b = l * this.per + r * sides + (s + 1) % sides, c = a + sides, d = b + sides;
      idx.push(a, c, b, b, c, d);
    }
    g.setIndex(idx);
    const pa = new THREE.BufferAttribute(this.pos, 3), na = new THREE.BufferAttribute(this.nor, 3); pa.setUsage(THREE.DynamicDrawUsage); na.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('position', pa); g.setAttribute('normal', na);
    g.boundingSphere = new THREE.Sphere(new V3(), 1e4);
    mat.side = THREE.DoubleSide; this.mesh = new THREE.Mesh(g, mat); this.mesh.frustumCulled = false; this.mesh.castShadow = false; this.mesh.userData.limb = true;
    this.on = new Array(n).fill(true);
    this._u = new V3(); this._w = new V3(); this._d = new V3(); this._c = new V3(); this._m = new V3();
  }
  // A 根、B 末端（世界座標）；rt 末端半徑、rf 穿出身體表面處的半徑（張開的裙邊）、Lf 張開的長度、ts 軸線穿出身體的位置（0~1）
  set(l, A, B, rf, rt, Lf, p, ts) {
    const d = this._d.subVectors(B, A), L = d.length() || 1e-4; d.multiplyScalar(1 / L);
    const u = this._u, w = this._w; u.set(Math.abs(d.y) > 0.9 ? 1 : 0, Math.abs(d.y) > 0.9 ? 0 : 1, 0); w.crossVectors(d, u).normalize(); u.crossVectors(w, d).normalize();
    const S = this.S, Rg = this.Rg, P = this.pos, Nn = this.nor, base = l * this.per * 3, c = this._c, t0 = Math.min(0.98, Math.max(0, ts - 0.5 * Lf / L));
    for (let r = 0; r < Rg; r++) {
      const t = r === 0 ? 0 : t0 + (1 - t0) * (r - 1) / (Rg - 2), sd = (t - ts) * L;
      let rad, slope = 0;
      if (sd <= 0) { rad = Math.max(rt * 1.15, rf * (1 + 1.6 * sd / Lf)); slope = rad > rt * 1.15 ? 1.6 * rf / Lf : 0; } else if (sd >= Lf) rad = rt; else { const q = 1 - sd / Lf; rad = rt + (rf - rt) * Math.pow(q, p); slope = -(rf - rt) * p * Math.pow(q, p - 1) / Lf; }
      c.copy(A).addScaledVector(d, L * t);
      for (let s = 0; s < S; s++) {
        const a = s / S * 6.2832, ca = Math.cos(a), sa = Math.sin(a);
        const rx = u.x * ca + w.x * sa, ry = u.y * ca + w.y * sa, rz = u.z * ca + w.z * sa, o = base + (r * S + s) * 3;
        P[o] = c.x + rx * rad; P[o + 1] = c.y + ry * rad; P[o + 2] = c.z + rz * rad;
        const nx = rx - d.x * slope, ny = ry - d.y * slope, nz = rz - d.z * slope, il = 1 / Math.hypot(nx, ny, nz);
        Nn[o] = nx * il; Nn[o + 1] = ny * il; Nn[o + 2] = nz * il;
      }
    }
  }
  hide(l) { const P = this.pos, b = l * this.per * 3; for (let i = 0; i < this.per * 3; i++) P[b + i] = 0; }
  commit() { this.geo.attributes.position.needsUpdate = true; this.geo.attributes.normal.needsUpdate = true; }
}
