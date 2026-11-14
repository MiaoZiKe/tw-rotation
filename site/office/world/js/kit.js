// 圓角幾何工具箱：所有場景物件都用這裡的圓角方塊、圓角板、圓角柱、球組成，
// 每件家具合併成一個網格（頂點色），只佔一次繪製呼叫。
import * as THREE from 'three';
import { RoundedBoxGeometry } from '../../vendor/RoundedBoxGeometry.js';
import { mergeGeometries } from '../../vendor/BufferGeometryUtils.js';

export { THREE };

export const PAL = {
  wood: '#e9c79c', woodMid: '#d9ad7c', woodDark: '#bd8a5c', cream: '#fff4e3', white: '#fffaf2',
  mint: '#bfe3d0', sky: '#bfe0f2', peach: '#ffd2b8', pink: '#f9c5cf', lav: '#d9cdf2', yellow: '#ffe6a3',
  leaf: '#93d18b', leafDark: '#6fbb78', leafLight: '#b7e3a4', pot: '#f0a987', potAlt: '#fbe2c0',
  grey: '#d5d8dc', greyDark: '#9aa0aa', ink: '#6b6470', screen: '#dff3ff', red: '#f28b82', gold: '#ffcf6b'
};

export const MAT = {
  solid: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.82, metalness: 0 }),
};

const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new THREE.Vector3(), _s = new THREE.Vector3();
const _c = new THREE.Color();
const cache = new Map();
function cached(key, make) { let g = cache.get(key); if (!g) { g = make(); if (g.index) g = g.toNonIndexed(); g.deleteAttribute('uv'); cache.set(key, g); } return g; }

export const G = {
  box(w, h, d, r = 0.06, seg = 0) {
    if (!seg) seg = Math.max(w, h, d) < 0.62 || r < 0.03 ? 1 : 2;
    r = Math.max(0.005, Math.min(r, Math.min(w, h, d) / 2 - 0.002));
    return cached(`b${w}|${h}|${d}|${r}|${seg}`, () => new RoundedBoxGeometry(w, h, d, seg, r));
  },
  // 俯視是圓角矩形的薄板（地毯、桌面、地板）；原點在底面中心
  slab(w, d, h, r = 0.2, bev = 0.02, seg = 6) {
    return cached(`s${w}|${d}|${h}|${r}|${bev}|${seg}`, () => {
      r = Math.min(r, w / 2 - 0.001, d / 2 - 0.001); bev = Math.min(bev, h / 2 - 0.001, r * 0.8);
      const s = new THREE.Shape(), x = -w / 2 + bev, y = -d / 2 + bev, ww = w - bev * 2, dd = d - bev * 2, rr = Math.max(0.001, r - bev);
      s.moveTo(x + rr, y); s.lineTo(x + ww - rr, y); s.absarc(x + ww - rr, y + rr, rr, -Math.PI / 2, 0);
      s.lineTo(x + ww, y + dd - rr); s.absarc(x + ww - rr, y + dd - rr, rr, 0, Math.PI / 2);
      s.lineTo(x + rr, y + dd); s.absarc(x + rr, y + dd - rr, rr, Math.PI / 2, Math.PI);
      s.lineTo(x, y + rr); s.absarc(x + rr, y + rr, rr, Math.PI, Math.PI * 1.5);
      const g = new THREE.ExtrudeGeometry(s, { depth: h - bev * 2, bevelEnabled: true, bevelSize: bev, bevelThickness: bev, bevelSegments: 2, curveSegments: seg });
      g.rotateX(-Math.PI / 2); g.translate(0, bev, 0); return g;
    });
  },
  // 圓角柱（上下緣倒圓）；原點在底面中心
  cyl(r, h, bev = 0.03, seg = 18, rTop = r) {
    return cached(`c${r}|${h}|${bev}|${seg}|${rTop}`, () => {
      bev = Math.min(bev, h / 2 - 0.001, Math.min(r, rTop) - 0.001);
      const pts = [new THREE.Vector2(0.0001, 0)];
      for (let i = 0; i <= 2; i++) { const a = -Math.PI / 2 + i / 2 * Math.PI / 2; pts.push(new THREE.Vector2(r - bev + Math.cos(a) * bev, bev + Math.sin(a) * bev)); }
      for (let i = 0; i <= 2; i++) { const a = i / 2 * Math.PI / 2; pts.push(new THREE.Vector2(rTop - bev + Math.cos(a) * bev, h - bev + Math.sin(a) * bev)); }
      pts.push(new THREE.Vector2(0.0001, h));
      return new THREE.LatheGeometry(pts, seg);
    });
  },
  sph(r, ws = 14, hs = 10) { return cached(`p${r}|${ws}|${hs}`, () => new THREE.SphereGeometry(r, ws, hs)); },
  cap(r, len, seg = 14) { return cached(`k${r}|${len}|${seg}`, () => new THREE.CapsuleGeometry(r, len, 5, seg)); },
  torus(R, r, seg = 20) { return cached(`t${R}|${r}|${seg}`, () => new THREE.TorusGeometry(R, r, 8, seg)); }
};

export class Part {
  constructor() { this.list = []; }
  add(geo, color, x = 0, y = 0, z = 0, ry = 0, rx = 0, rz = 0, sx = 1, sy = 1, sz = 1) {
    const g = geo.clone();
    _e.set(rx, ry, rz, 'YXZ'); _q.setFromEuler(_e); _m.compose(_p.set(x, y, z), _q, _s.set(sx, sy, sz)); g.applyMatrix4(_m);
    const n = g.attributes.position.count, arr = new Float32Array(n * 3); _c.set(color);
    for (let i = 0; i < n; i++) { arr[i * 3] = _c.r; arr[i * 3 + 1] = _c.g; arr[i * 3 + 2] = _c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(arr, 3));
    this.list.push(g); return this;
  }
  // y0 = 底面高度
  box(color, w, h, d, x, y0, z, r = 0.06, ry = 0, rx = 0, rz = 0) { return this.add(G.box(w, h, d, r), color, x, y0 + h / 2, z, ry, rx, rz); }
  slab(color, w, d, h, x, y0, z, r = 0.2, ry = 0, bev = 0.02) { return this.add(G.slab(w, d, h, r, bev), color, x, y0, z, ry); }
  cyl(color, r, h, x, y0, z, bev = 0.03, rTop = r, seg = 0) { if (!seg) seg = r < 0.07 ? 8 : r < 0.3 ? 12 : 18; return this.add(G.cyl(r, h, bev, seg, rTop), color, x, y0, z); }
  sph(color, r, x, y, z, sx = 1, sy = 1, sz = 1) { return this.add(r < 0.1 ? G.sph(r, 8, 6) : r < 0.3 ? G.sph(r, 10, 7) : G.sph(r, 14, 10), color, x, y, z, 0, 0, 0, sx, sy, sz); }
  // 標記：把「可被撞開的小東西」（椅子、桌上的杯子…）在合併前標出是第幾個零件；合併後換算成頂點範圍，物理層（phys.js）才切得出來。
  mk(kind, meta, i0) { (this.marks ||= []).push({ kind, ...meta, i0, i1: this.list.length }); return this; }
  geometry() {
    if (this.marks) { const cum = [0]; for (const g of this.list) cum.push(cum[cum.length - 1] + g.attributes.position.count); for (const m of this.marks) { m.v0 = cum[m.i0]; m.v1 = cum[m.i1]; } }
    const g = mergeGeometries(this.list, false); this.list.forEach(x => x.dispose()); this.list = []; return g;
  }
  mesh(mat = MAT.solid) { const m = new THREE.Mesh(this.geometry(), mat); m.castShadow = true; m.receiveShadow = true; return m; }
}

export function shade(hex, k) { // k>0 變亮、k<0 變暗
  const c = new THREE.Color(hex), w = k > 0 ? new THREE.Color('#ffffff') : new THREE.Color('#5b4a3f');
  return '#' + c.lerp(w, Math.abs(k)).getHexString();
}

// 畫字的小牌子（畫布貼圖，不是向量圖）
export function textTexture(lines, o = {}) {
  const W = o.pw || 512, H = o.ph || 160, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  const c = cv.getContext('2d'); const r = o.radius ?? H * 0.28;
  c.fillStyle = o.bg || '#fffaf2'; c.beginPath(); c.roundRect(0, 0, W, H, r); c.fill();
  if (o.border) { c.lineWidth = o.borderW || 10; c.strokeStyle = o.border; c.beginPath(); c.roundRect(5, 5, W - 10, H - 10, r - 4); c.stroke(); }
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = o.fg || '#5a4638';
  const arr = Array.isArray(lines) ? lines : [lines];
  arr.forEach((t, i) => {
    let px = (o.px || H * 0.5) * (i ? (o.subScale || 0.6) : 1);
    c.font = `${i ? 600 : 800} ${px}px "Noto Sans TC","PingFang TC","Microsoft JhengHei","WenQuanYi Zen Hei",sans-serif`;
    while (c.measureText(t).width > W * 0.88 && px > 10) { px -= 2; c.font = c.font.replace(/\d+(\.\d+)?px/, px + 'px'); }
    const y = arr.length === 1 ? H / 2 : H * (i ? 0.72 : 0.36);
    if (i) c.fillStyle = o.fg2 || '#9a8576';
    c.fillText(t, W / 2, y + px * 0.04);
  });
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace; tx.anisotropy = 4; return tx;
}
export function textPlane(lines, w, h, o = {}) {
  const tx = textTexture(lines, { pw: o.pw || 512, ph: Math.round((o.pw || 512) * h / w), ...o });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: tx, roughness: 0.9, transparent: true, alphaTest: 0.3 }));
  m.userData.tex = tx; return m;
}
