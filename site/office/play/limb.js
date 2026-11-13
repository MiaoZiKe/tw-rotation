// 肢體「從身體長出來」的幾何：根部張開、埋進身體、往末端收細
// 搭配 soft.js 的 root 材質（根部附近的顏色與法線朝身體表面混合），交界處沒有接縫。
import * as THREE from 'three';
import { DETAIL } from './soft.js';
const V3 = THREE.Vector3;

// ── 靜態：沿 +y 長的錐形體（耳朵、尾巴、觸手），根在 y=0（埋進身體），尖端在 y=1，單位半徑 1（再用 scale 放大）
//   q＝尖端半徑比例，p＝張開的曲線（越大越快收細），cap＝尖端圓頭佔的長度比例，bulge＝中段鼓起（0~0.4）
const cache = new Map();
export function taperGeo({ q = 0.4, p = 2.2, cap = 0.25, bulge = 0, curl = 0, flare = 1, fl = 0.22 } = {}) {
  const k = `${q}|${p}|${cap}|${bulge}|${curl}|${flare}|${fl}|${DETAIL.k}`; if (cache.has(k)) return cache.get(k);
  const pts = [new THREE.Vector2(0, 0)], N = Math.max(8, Math.round((flare > 1 ? 20 : 14) * DETAIL.k)), tc = 1 - cap;
  const body = (t) => (q + (1 - q) * Math.pow(1 - t, p)) * (1 + bulge * Math.sin(Math.PI * Math.min(1, t / tc))) * (1 + (flare - 1) * Math.pow(Math.max(0, 1 - t / fl), 2));   // flare＝根部喇叭口（內凹過渡弧）
  for (let i = 0; i <= N; i++) { const t = i / N * tc; pts.push(new THREE.Vector2(body(t), t)); }
  const rc = body(tc), M = Math.max(5, Math.round(8 * DETAIL.k));
  for (let i = 1; i <= M; i++) { const a = i / M * Math.PI / 2; pts.push(new THREE.Vector2(rc * Math.cos(a), tc + cap * Math.sin(a))); }
  const g = new THREE.LatheGeometry(pts, Math.max(12, Math.round(20 * DETAIL.k)));
  if (curl) {   // S 形：先下垂再上翹（沿 z 位移，curl 是單位半徑的倍數）
    const P = g.attributes.position, N = g.attributes.normal, f = (t) => -0.5 * Math.sin(Math.PI * t) + 1.2 * t * t * t, df = (t) => -0.5 * Math.PI * Math.cos(Math.PI * t) + 3.6 * t * t;
    for (let i = 0; i < P.count; i++) { const t = Math.min(1, Math.max(0, P.getY(i))); P.setZ(i, P.getZ(i) + curl * f(t)); let nx = N.getX(i), ny = N.getY(i), nz = N.getZ(i) - curl * df(t) * ny * 0.35; const il = 1 / Math.hypot(nx, ny, nz); N.setXYZ(i, nx * il, ny * il, nz * il); }
  }
  cache.set(k, g); return g;
}

// ── 動態：一隻角色的所有手腳「皮膚」合成一個網格（一次繪製）
//   每條肢體固定 R 圈、每圈 S 點。三種寫法：
//   set()    舊的直管（硬質物種、豆芽）：根→末端，根部張開
//   setArm() 短胖彎曲的手臂：二次貝茲曲線，末端圓頭就是手掌（手球縮進圓頭裡）
//   setLeg() 腿＋腳掌連成一體：腿末端往前擴成橢球腳掌
const sst = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
export class LimbSkin {
  constructor(n, mat, sides = 24, rings = 16) {
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
    this._u = new V3(); this._w = new V3(); this._d = new V3(); this._c = new V3(); this._p = new V3(); this._q = new V3();
    this.cen = new Float32Array(rings * 3); this.rad = new Float32Array(rings); this.tan = new Float32Array(rings * 3); this.fr = new Float32Array(rings * 6);
  }
  // 寫一圈：中心 c、基底 u/w、橢圓半徑 rx/rz、法線函式
  _ring(l, r, c, u, w, rx, rz, nfn) {
    const S = this.S, P = this.pos, N = this.nor, base = (l * this.per + r * S) * 3;
    for (let s = 0; s < S; s++) {
      const a = s / S * 6.2832, ca = Math.cos(a), sa = Math.sin(a), o = base + s * 3;
      P[o] = c.x + (u.x * ca * rx + w.x * sa * rz); P[o + 1] = c.y + (u.y * ca * rx + w.y * sa * rz); P[o + 2] = c.z + (u.z * ca * rx + w.z * sa * rz);
      nfn(ca, sa, N, o);
    }
  }
  // 舊直管
  set(l, A, B, rf, rt, Lf, p, ts, rip = 0) {
    const d = this._d.subVectors(B, A), L = d.length() || 1e-4; d.multiplyScalar(1 / L);
    const u = this._u, w = this._w; u.set(Math.abs(d.y) > 0.9 ? 1 : 0, Math.abs(d.y) > 0.9 ? 0 : 1, 0); w.crossVectors(d, u).normalize(); u.crossVectors(w, d).normalize();
    const Rg = this.Rg, c = this._c, t0 = Math.min(0.98, Math.max(0, ts - 0.5 * Lf / L));
    for (let r = 0; r < Rg; r++) {
      const t = t0 + (1 - t0) * r / (Rg - 1), sd = (t - ts) * L; let rad, slope = 0;
      if (sd <= 0) { rad = Math.max(rt * 1.15, rf * (1 + 1.6 * sd / Lf)); slope = rad > rt * 1.15 ? 1.6 * rf / Lf : 0; } else if (sd >= Lf) rad = rt; else { const q = 1 - sd / Lf; rad = rt + (rf - rt) * Math.pow(q, p); slope = -(rf - rt) * p * Math.pow(q, p - 1) / Lf; }
      if (rip && t > ts) { const q = (t - ts) / (1 - ts), ph = q * 18.85; slope += -rad * rip * Math.sin(ph) * 18.85 / ((1 - ts) * L) * 0.5; rad *= 1 + rip * (Math.cos(ph) - 1) * 0.5; }   // 波紋管：3 節皺褶
      c.copy(A).addScaledVector(d, L * t);
      this._ring(l, r, c, u, w, rad, rad, (ca, sa, N, o) => { const nx = u.x * ca + w.x * sa - d.x * slope, ny = u.y * ca + w.y * sa - d.y * slope, nz = u.z * ca + w.z * sa - d.z * slope, il = 1 / Math.hypot(nx, ny, nz); N[o] = nx * il; N[o + 1] = ny * il; N[o + 2] = nz * il; });
    }
  }
  // 手臂：A 肩（身體裡）→ ctrl 控制點 → B 手尖；rf 根半徑、rt 手掌半徑；末端半球圓頭；collar＝穿出身體處的裙邊半徑，Lf 裙邊長
  setArm(l, A, ctrl, B, rf, rt, collar, Lf, ts) {
    const Rg = this.Rg, NB = Rg - 4, T = this._d, E = this._p, c = this._c, u = this._u, w = this._w;
    T.subVectors(B, ctrl).normalize(); E.copy(B).addScaledVector(T, -rt * 0.5);   // 圓頭的底（再往外一個半徑的半球）
    const bz = (t, out) => { const m = 1 - t; return out.set(m * m * A.x + 2 * m * t * ctrl.x + t * t * E.x, m * m * A.y + 2 * m * t * ctrl.y + t * t * E.y, m * m * A.z + 2 * m * t * ctrl.z + t * t * E.z); };
    const L = A.distanceTo(E) || 1e-4, t0 = Math.min(0.9, Math.max(0, ts - 0.5 * Lf / L));
    const cen = this.cen, rad = this.rad, tan = this.tan, q = this._q, arc = [];
    let prev = null;
    for (let k = 0; k < NB; k++) {
      const t = t0 + (1 - t0) * k / (NB - 1); bz(t, q); cen[k * 3] = q.x; cen[k * 3 + 1] = q.y; cen[k * 3 + 2] = q.z;
      const m = 1 - t; tan[k * 3] = 2 * m * (ctrl.x - A.x) + 2 * t * (E.x - ctrl.x); tan[k * 3 + 1] = 2 * m * (ctrl.y - A.y) + 2 * t * (E.y - ctrl.y); tan[k * 3 + 2] = 2 * m * (ctrl.z - A.z) + 2 * t * (E.z - ctrl.z);
      const il = 1 / (Math.hypot(tan[k * 3], tan[k * 3 + 1], tan[k * 3 + 2]) || 1); tan[k * 3] *= il; tan[k * 3 + 1] *= il; tan[k * 3 + 2] *= il;
      const sd = (t - ts) * L; let r = rt + (rf - rt) * Math.pow(1 - t, 1.5);
      const col = sd <= 0 ? collar * Math.max(0, 1 + 1.6 * sd / Lf) : sd < Lf ? rt + (collar - rt) * Math.pow(1 - sd / Lf, 2.2) : 0; rad[k] = Math.max(r, col, rt);
      arc[k] = k ? arc[k - 1] + Math.hypot(cen[k * 3] - cen[k * 3 - 3], cen[k * 3 + 1] - cen[k * 3 - 2], cen[k * 3 + 2] - cen[k * 3 - 1]) : 0;
    }
    for (let k = 0; k < NB; k++) {
      c.set(cen[k * 3], cen[k * 3 + 1], cen[k * 3 + 2]); const tx = tan[k * 3], ty = tan[k * 3 + 1], tz = tan[k * 3 + 2];
      if (!prev) { u.set(Math.abs(ty) > 0.9 ? 1 : 0, Math.abs(ty) > 0.9 ? 0 : 1, 0); } else u.copy(prev);
      const dot = u.x * tx + u.y * ty + u.z * tz; u.x -= tx * dot; u.y -= ty * dot; u.z -= tz * dot; u.normalize(); prev = this._q2 ??= new V3(); prev.copy(u);
      w.set(ty * u.z - tz * u.y, tz * u.x - tx * u.z, tx * u.y - ty * u.x);
      const k0 = Math.max(0, k - 1), k1 = Math.min(NB - 1, k + 1), slope = (rad[k1] - rad[k0]) / Math.max(1e-5, arc[k1] - arc[k0]), r = rad[k];
      this._ring(l, k, c, u, w, r, r, (ca, sa, N, o) => { const nx = u.x * ca + w.x * sa - tx * slope, ny = u.y * ca + w.y * sa - ty * slope, nz = u.z * ca + w.z * sa - tz * slope, il = 1 / Math.hypot(nx, ny, nz); N[o] = nx * il; N[o + 1] = ny * il; N[o + 2] = nz * il; });
      if (k === NB - 1) { this._lastU = u.clone(); this._lastW = w.clone(); this._lastC = c.clone(); this._lastT = new V3(tx, ty, tz); }
    }
    const lu = this._lastU, lw = this._lastW, lc = this._lastC, lt = this._lastT;
    for (let j = 1; j <= 4; j++) {
      const a = j / 4 * Math.PI / 2, ca0 = Math.cos(a), sa0 = Math.sin(a); c.copy(lc).addScaledVector(lt, rt * sa0); const rr = Math.max(1e-4, rt * ca0);
      this._ring(l, NB - 1 + j, c, lu, lw, rr, rr, (ca, sa, N, o) => { const nx = (lu.x * ca + lw.x * sa) * ca0 + lt.x * sa0, ny = (lu.y * ca + lw.y * sa) * ca0 + lt.y * sa0, nz = (lu.z * ca + lw.z * sa) * ca0 + lt.z * sa0; N[o] = nx; N[o + 1] = ny; N[o + 2] = nz; });
    }
  }
  // 腿＋腳掌：A 髖（身體裡）→ 腳踝，接橢球腳掌（中心 F、半徑 fx 側、fy 高、fz 前後；yaw 朝向）
  setLeg(l, A, F, yaw, fx, fy, fz, rf, collar, Lf, ts) {
    const Rg = this.Rg, NL = 8, NF = Rg - NL, cy = Math.cos(yaw), sy = Math.sin(yaw), u = this._u.set(cy, 0, -sy), w = this._w.set(sy, 0, cy), c = this._c, d = this._d;
    const cE = this._p.copy(F); cE.y += fy; cE.x += sy * fz * 0.12; cE.z += cy * fz * 0.12;
    const th0 = 0.75, ank = this._q.set(cE.x, cE.y + fy * Math.cos(th0), cE.z); const rt = fx * Math.sin(th0);
    d.subVectors(ank, A); const L = d.length() || 1e-4; d.multiplyScalar(1 / L);
    const t0 = Math.min(0.9, Math.max(0, ts - 0.5 * Lf / L)), ezk = fz / fx;
    for (let k = 0; k < NL; k++) {
      const t = t0 + (1 - t0) * k / (NL - 1), sd = (t - ts) * L; let r = rt + (rf - rt) * Math.pow(1 - t, 1.8);
      const col = sd <= 0 ? collar * Math.max(0, 1 + 1.6 * sd / Lf) : sd < Lf ? rt + (collar - rt) * Math.pow(1 - sd / Lf, 2.2) : 0; r = Math.max(r, col, rt);
      const ez = 1 + (ezk - 1) * sst(0.55, 1, t) * 0.85, fwd = (ezk - 1) * sst(0.55, 1, t) * 0.0;
      c.copy(A).addScaledVector(d, L * t); const slope = -(rf - rt) * 1.8 * Math.pow(1 - t, 0.8) / L * 0.6;
      this._ring(l, k, c, u, w, r, r * ez, (ca, sa, N, o) => { const nx = u.x * ca + w.x * sa / ez - d.x * slope, ny = u.y * ca + w.y * sa / ez - d.y * slope, nz = u.z * ca + w.z * sa / ez - d.z * slope, il = 1 / Math.hypot(nx, ny, nz); N[o] = nx * il; N[o + 1] = ny * il; N[o + 2] = nz * il; });
    }
    for (let j = 0; j < NF; j++) {
      const th = th0 + (3.08 - th0) * j / (NF - 1), st = Math.sin(th), ct = Math.cos(th); c.set(cE.x, cE.y + fy * ct, cE.z);
      this._ring(l, NL + j, c, u, w, fx * st, fz * st, (ca, sa, N, o) => { const nx = u.x * ca * st / fx + w.x * sa * st / fz, ny = u.y * ca * st / fx + w.y * sa * st / fz + ct / fy, nz = u.z * ca * st / fx + w.z * sa * st / fz, il = 1 / Math.hypot(nx, ny, nz); N[o] = nx * il; N[o + 1] = ny * il; N[o + 2] = nz * il; });
    }
  }
  commit() { this.geo.attributes.position.needsUpdate = true; this.geo.attributes.normal.needsUpdate = true; }
}

// ── 彎曲的錐管：沿任意曲線 path(t)→[x,y,z]（t 0~1，根在 t=0、埋進身體）掃出圓管，半徑 rad(t)
//   flare＝根部喇叭口倍數（內凹過渡弧，fl＝佔全長比例），cap＝末端半球圓頭佔全長比例（尖端一定是圓的，不會平切）
//   用途：八寶捲尾觸手、啃啃彎尾、啾啾尾羽；單位＝公尺，直接 put(...,1) 使用
const tcache = new Map();
export function tubeGeo({ key, path, rad, flare = 1, fl = 0.2, cap = 0.16, N = 26, S = 16 }) {
  const kk = `${key}|${DETAIL.k}`; if (key && tcache.has(kk)) return tcache.get(kk);
  N = Math.max(12, Math.round(N * Math.max(0.6, DETAIL.k))); S = Math.max(8, Math.round(S * Math.max(0.6, DETAIL.k)));
  const tc = 1 - cap, cs = [], rs = [], arc = [];
  const R = (t) => { const base = rad(Math.min(t, tc)), fa = 1 + (flare - 1) * Math.pow(Math.max(0, 1 - t / fl), 2); if (t <= tc) return base * fa; const s = (t - tc) / cap; return base * Math.sqrt(Math.max(0, 1 - s * s)); };
  for (let i = 0; i <= N; i++) { const t = i / N; cs.push(path(t)); rs.push(R(t)); arc.push(i ? arc[i - 1] + Math.hypot(cs[i][0] - cs[i - 1][0], cs[i][1] - cs[i - 1][1], cs[i][2] - cs[i - 1][2]) : 0); }
  const pos = new Float32Array((N + 1) * (S + 1) * 3), nor = new Float32Array(pos.length), idx = [];
  let u = new V3(0, 0, 1), w = new V3(), T = new V3();
  for (let i = 0; i <= N; i++) {
    const a = cs[Math.max(0, i - 1)], b = cs[Math.min(N, i + 1)]; T.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]).normalize();
    if (Math.abs(u.dot(T)) > 0.97) u.set(T.y > 0.9 ? 1 : 0, T.y > 0.9 ? 0 : 1, 0);
    u.addScaledVector(T, -u.dot(T)).normalize(); w.crossVectors(T, u);
    const i0 = Math.max(0, i - 1), i1 = Math.min(N, i + 1), dr = (rs[i1] - rs[i0]) / Math.max(1e-6, arc[i1] - arc[i0]);
    for (let s = 0; s <= S; s++) {
      const th = s / S * Math.PI * 2, ca = Math.cos(th), sa = Math.sin(th), o = (i * (S + 1) + s) * 3;
      const dx = u.x * ca + w.x * sa, dy = u.y * ca + w.y * sa, dz = u.z * ca + w.z * sa;
      pos[o] = cs[i][0] + dx * rs[i]; pos[o + 1] = cs[i][1] + dy * rs[i]; pos[o + 2] = cs[i][2] + dz * rs[i];
      const nx = dx - T.x * dr, ny = dy - T.y * dr, nz = dz - T.z * dr, il = 1 / Math.hypot(nx, ny, nz); nor[o] = nx * il; nor[o + 1] = ny * il; nor[o + 2] = nz * il;
    }
  }
  for (let i = 0; i < N; i++) for (let s = 0; s < S; s++) { const a = i * (S + 1) + s, b = a + 1, c = a + S + 1, d = c + 1; idx.push(a, b, c, b, d, c); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setIndex(idx);
  // 繞法方向若反了就翻面
  const p0 = new V3(pos[0], pos[1], pos[2]); void p0;
  if (key) tcache.set(kk, g); return g;
}
