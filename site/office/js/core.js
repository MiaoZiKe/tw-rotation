// 共用：柔和卡通材質、平滑幾何工具（全部用足夠細分的曲面＋解析法線，不留稜線）
import * as THREE from '../vendor/three.module.min.js';
export { THREE };

const V = () => new THREE.Vector3();
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export const C = (h) => new THREE.Color(h);

// 柔和材質：標準材質＋邊緣光（越靠輪廓越亮，偏上方），沒有硬邊色階
export function softMat(color, o = {}) {
  const m = new THREE.MeshStandardMaterial({
    color: o.map || o.vc ? 0xffffff : color, roughness: o.rough ?? 0.92, metalness: 0,
    vertexColors: !!o.vc, map: o.map || null, transparent: !!o.transparent, side: o.side ?? THREE.FrontSide,
    emissive: o.emissive ?? 0x000000, emissiveIntensity: o.emissiveIntensity ?? 1,
  });
  if (o.transparent) { m.depthWrite = false; m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -2; }
  const rimC = C(o.rim ?? 0xfff3e2), rimS = o.rimStr ?? 0.38, rimP = o.rimPow ?? 2.6;
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uRimC = { value: rimC }; sh.uniforms.uRimS = { value: rimS }; sh.uniforms.uRimP = { value: rimP };
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec3 uRimC; uniform float uRimS; uniform float uRimP;')
      .replace('#include <opaque_fragment>', `
        float rimF = pow(1.0 - saturate(dot(normalize(normal), normalize(vViewPosition))), uRimP);
        rimF *= 0.45 + 0.55 * smoothstep(-0.5, 0.7, normal.y);
        outgoingLight += uRimC * rimF * uRimS * (0.35 + 0.65 * diffuseColor.rgb);
        #include <opaque_fragment>`);
  };
  m.customProgramCacheKey = () => 'soft' + rimS + rimP + rimC.getHexString();
  return m;
}

// 以「單位方向 → 位置」函式產生平滑曲面；法線用差分算，接縫放在背面
export function dirSurface(fn, o = {}) {
  const w = o.w ?? 72, h = o.h ?? 48;
  const g = new THREE.SphereGeometry(1, w, h, o.phiStart ?? -Math.PI / 2, o.phiLen ?? Math.PI * 2, o.thetaStart ?? 0, o.thetaLen ?? Math.PI);
  const pos = g.attributes.position, nor = g.attributes.normal;
  const col = o.color ? new Float32Array(pos.count * 3) : null;
  const d = V(), p0 = V(), p1 = V(), p2 = V(), t1 = V(), t2 = V(), a = V(), n = V(), dd = V(), cc = new THREE.Color();
  const e = 0.004;
  for (let i = 0; i < pos.count; i++) {
    d.fromBufferAttribute(pos, i).normalize();
    fn(d, p0);
    a.set(0, 1, 0); if (Math.abs(d.y) > 0.9) a.set(1, 0, 0);
    t1.crossVectors(a, d).normalize(); t2.crossVectors(d, t1);
    fn(dd.copy(d).addScaledVector(t1, e).normalize(), p1);
    fn(dd.copy(d).addScaledVector(t2, e).normalize(), p2);
    n.crossVectors(p1.sub(p0), p2.sub(p0)).normalize();
    if (n.dot(d) < 0 && !o.noFlip) n.negate();
    pos.setXYZ(i, p0.x, p0.y, p0.z); nor.setXYZ(i, n.x, n.y, n.z);
    if (col) { o.color(d, p0, cc); col[i * 3] = cc.r; col[i * 3 + 1] = cc.g; col[i * 3 + 2] = cc.b; }
  }
  if (col) g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeBoundingSphere(); g.computeBoundingBox();
  return g;
}
export const ellipsoid = (rx, ry, rz, o = {}) => dirSurface((d, p) => p.set(d.x * rx, d.y * ry, d.z * rz), { w: 40, h: 28, ...o });

// 依高度上漸層色（上亮下深），布料與毛色用
export function gradY(g, top, bot, y0, y1) {
  const pos = g.attributes.position, col = new Float32Array(pos.count * 3), a = C(top), b = C(bot), c = new THREE.Color();
  if (y0 === undefined) { g.computeBoundingBox(); y0 = g.boundingBox.min.y; y1 = g.boundingBox.max.y; }
  for (let i = 0; i < pos.count; i++) { c.copy(b).lerp(a, sstep(y0, y1, pos.getY(i))); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3)); return g;
}

// 圓頭膠囊肢段：樞紐在上端球心，往 -y 延伸
export function limbGeo(r, len, r2) {
  const g = new THREE.CapsuleGeometry(r, len, 12, 28); g.translate(0, -len / 2, 0);
  if (r2 !== undefined) { // 末端稍粗或稍細，法線近似不變
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) { const y = pos.getY(i), k = lerp(1, r2 / r, clamp(-y / len)); pos.setX(i, pos.getX(i) * k); pos.setZ(i, pos.getZ(i) * k); }
  }
  return g;
}

// 旋轉體（梨形身體、椅座等）：輪廓用樣條取樣，UV 的 v 改成依高度
export function latheGeo(pts, o = {}) {
  const curve = new THREE.CatmullRomCurve3(pts.map(([r, y]) => new THREE.Vector3(r, y, 0)), false, 'catmullrom', o.tension ?? 0.5);
  const n = o.rows ?? 40, sp = curve.getPoints(n).map((p) => new THREE.Vector2(Math.max(0, p.x), p.y));
  sp[0].x = 0; if (!o.open) sp[n].x = 0;
  const seg = o.seg ?? 56;
  const g = new THREE.LatheGeometry(sp, seg, Math.PI, Math.PI * 2);
  const pos = g.attributes.position, uv = g.attributes.uv; g.computeBoundingBox();
  const y0 = g.boundingBox.min.y, y1 = g.boundingBox.max.y;
  for (let i = 0; i < pos.count; i++) uv.setY(i, (pos.getY(i) - y0) / (y1 - y0));
  g.userData = { seg, rows: n + 1 };
  return g;
}
// 變形後重算法線，並把背面接縫兩排的法線平均（避免一條細縫）
export function fixSeam(g) {
  g.computeVertexNormals();
  const { seg, rows } = g.userData, nor = g.attributes.normal;
  for (let j = 0; j < rows; j++) {
    const a = j, b = seg * rows + j;
    const x = nor.getX(a) + nor.getX(b), y = nor.getY(a) + nor.getY(b), z = nor.getZ(a) + nor.getZ(b), l = Math.hypot(x, y, z) || 1;
    nor.setXYZ(a, x / l, y / l, z / l); nor.setXYZ(b, x / l, y / l, z / l);
  }
  return g;
}

// 圓角板（桌面、識別證、筆電）
export function roundedSlab(w, h, r, depth, bevel = 0.006) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 5, curveSegments: 14 });
  g.translate(0, 0, -depth / 2); return g;
}

export function canvasTex(w, h, draw) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h; const ctx = cv.getContext('2d'); draw(ctx, w, h);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

// 彈簧尾端：耳朵、尾巴、觸角、頭髮、識別證的晃動（世界座標下的阻尼擺）
export class Spring {
  constructor(node, len, o = {}) {
    this.node = node; this.len = len; this.k = o.k ?? 90; this.c = o.c ?? 9; this.acc = o.acc ?? 1.6; this.g = o.g ?? 0;
    this.axis = (o.axis ?? new THREE.Vector3(0, 1, 0)).clone().normalize();
    this.rest = node.quaternion.clone(); this.p = null; this.v = V(); this.pa = null; this.va = V();
  }
  step(dt) {
    const n = this.node, par = n.parent;
    n.quaternion.copy(this.rest); n.updateMatrix(); par.updateWorldMatrix(true, false); n.matrixWorld.multiplyMatrices(par.matrixWorld, n.matrix);
    const anchor = V().setFromMatrixPosition(n.matrixWorld);
    const target = this.axis.clone().multiplyScalar(this.len).applyMatrix4(n.matrixWorld);
    if (!this.p) { this.p = target.clone(); this.pa = anchor.clone(); }
    const va = anchor.clone().sub(this.pa).divideScalar(dt); const aa = va.clone().sub(this.va).divideScalar(dt); this.va.copy(va); this.pa.copy(anchor);
    aa.clampLength(0, 60);
    const f = target.clone().sub(this.p).multiplyScalar(this.k).addScaledVector(this.v, -this.c).addScaledVector(aa, -this.acc * 0.05); f.y -= this.g;
    this.v.addScaledVector(f, dt); this.p.addScaledVector(this.v, dt);
    const dir = this.p.clone().sub(anchor); if (dir.lengthSq() < 1e-9) return; dir.setLength(this.len); this.p.copy(anchor).add(dir);
    // 轉回父座標，求出把休息方向轉到實際方向的旋轉
    const inv = new THREE.Matrix4().copy(par.matrixWorld).invert();
    const lp = this.p.clone().applyMatrix4(inv).sub(n.position).normalize();
    const restDir = this.axis.clone().applyQuaternion(this.rest);
    n.quaternion.copy(new THREE.Quaternion().setFromUnitVectors(restDir, lp).multiply(this.rest));
    n.updateMatrix(); n.matrixWorld.multiplyMatrices(par.matrixWorld, n.matrix);
  }
  reset() { this.p = null; this.v.set(0, 0, 0); this.va.set(0, 0, 0); }
}
