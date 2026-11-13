// 新角色的配件（識別證、領帶、帽子、皇冠、蝴蝶結、眼鏡、圍巾）：掛在頭骨的靜止座標下，位置取自模型錨點（表面點與法線）。
// 全部是小而圓的布料／塑膠件，貼在身體表面外 3～8 mm；跟著形態鍵的身體尺寸變化一起位移（MochiChar.follow）。
import * as THREE from 'three';
const V3 = THREE.Vector3, Q = THREE.Quaternion;
const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: o.r ?? 0.85, metalness: o.m ?? 0, ...o.extra });
function orient(n) { const z = new V3(...n).normalize(), x = new V3(0, 1, 0).cross(z); if (x.lengthSq() < 1e-6) x.set(1, 0, 0); x.normalize(); const y = z.clone().cross(x); return new Q().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z)); }
function rbox(w, h, d, r) { const s = new THREE.Shape(), x = -w / 2, y = -h / 2; s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h); s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); const g = new THREE.ExtrudeGeometry(s, { depth: d, bevelEnabled: true, bevelSize: r * 0.5, bevelThickness: r * 0.5, bevelSegments: 2, curveSegments: 6 }); g.translate(0, 0, -d / 2); return g; }

/** ch：MochiChar；list：配件名；col：配件色（hex）。回傳實際戴上的配件 [{name, obj}]。 */
export function addAccs(ch, list, col) {
  const A = ch.meta.anchors, hold = ch.holderFor('head'), worn = []; if (!hold) return worn;
  const cloth = mat(col, { r: 0.95 }), silk = mat(col, { r: 0.45 }), white = mat(0xfffaf2, { r: 0.9 }), dk = mat(0x6a5a55, { r: 0.6 }), gold = mat(0xffd04a, { r: 0.35, m: 0.2 });
  const put = (name, anchor, build, lift = 0.004) => {
    const a = A[anchor]; if (!a) return; const g = new THREE.Group(), p = new V3(...a.p).addScaledVector(new V3(...a.n), lift); g.position.copy(p); g.quaternion.copy(orient(a.n)); build(g);
    hold.add(g); ch.follow(g, g.position); worn.push({ name, obj: g }); g.userData.acc = name; return g;
  };
  let head = false;
  for (const a of list) {
    if (a === 'badge') put('badge', 'badge' in A ? 'badge' : 'chest', (g) => {
      const plate = new THREE.Mesh(rbox(0.07, 0.09, 0.008, 0.008), white), band = new THREE.Mesh(rbox(0.07, 0.024, 0.01, 0.006), silk), face = new THREE.Mesh(new THREE.SphereGeometry(0.016, 12, 8), mat(0xf2c9a4)), ln = new THREE.Mesh(new THREE.BoxGeometry(0.044, 0.006, 0.003), dk);
      plate.position.set(0, -0.012, 0); band.position.set(0, 0.026, 0.001); face.scale.z = 0.25; face.position.set(0, -0.012, 0.006); ln.position.set(0, -0.045, 0.006); g.add(plate, band, face, ln); g.rotation.z = -0.1; g.quaternion.multiply(new Q().setFromAxisAngle(new V3(0, 0, 1), -0.1));
    });
    else if (a === 'tie') put('tie', 'chest', (g) => {
      const knot = new THREE.Mesh(new THREE.SphereGeometry(0.024, 14, 10), silk); knot.scale.set(1, 0.9, 0.7); const bl = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.1, 4, 1), silk); bl.rotation.set(0, Math.PI / 4, Math.PI); bl.scale.set(0.75, 1, 0.38); bl.position.set(0, -0.065, -0.004);
      g.add(knot, bl);
    }, 0.006);
    else if ((a === 'hat' || a === 'crown') && !head && A.hat) { head = true; put(a, 'hat', (g) => {
      if (a === 'crown') { const r = 0.062, ring = new THREE.Mesh(new THREE.TorusGeometry(r, 0.012, 8, 28), gold); ring.rotation.x = Math.PI / 2; ring.position.y = 0.012; g.add(ring);
        for (let i = 0; i < 5; i++) { const t = i / 5 * Math.PI * 2, sp = new THREE.Mesh(new THREE.ConeGeometry(0.014, 0.05, 6), gold); sp.position.set(Math.sin(t) * r, 0.045, Math.cos(t) * r); g.add(sp); const b = new THREE.Mesh(new THREE.SphereGeometry(0.009, 8, 6), mat(0xff7f9c)); b.position.set(Math.sin(t) * r, 0.074, Math.cos(t) * r); g.add(b); } }
      else { const cap = new THREE.Mesh(new THREE.SphereGeometry(0.095, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), cloth); cap.scale.set(1, 0.7, 1); const br = new THREE.Mesh(new THREE.TorusGeometry(0.095, 0.01, 8, 28), white); br.rotation.x = Math.PI / 2; const pom = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 8), white); pom.position.y = 0.072; g.add(cap, br, pom); }
      g.quaternion.copy(new Q()); g.rotation.set(0, 0, 0); g.position.y -= 0.012; }, 0); }
    else if (a === 'bow' && !head && A.bow) { head = true; put('bow', 'bow', (g) => {
      for (const s of [-1, 1]) { const w = new THREE.Mesh(new THREE.SphereGeometry(0.04, 14, 10), cloth); w.scale.set(1.05, 0.8, 0.45); w.position.set(s * 0.038, 0, 0.004); w.rotation.z = s * 0.3; g.add(w); }
      const k = new THREE.Mesh(new THREE.SphereGeometry(0.02, 10, 8), silk); k.position.z = 0.008; g.add(k); g.rotation.z = -0.3; g.quaternion.multiply(new Q().setFromAxisAngle(new V3(0, 0, 1), -0.3)); }, 0.012); }
    else if (a === 'glasses') { for (const sd of ['L', 'R']) { const an = A['eye.' + sd]; if (!an) continue; const k = ch.meta.face?.eyeK ?? 1;
      const g = new THREE.Group(), r = new THREE.Mesh(new THREE.TorusGeometry(0.1 * k, 0.0075, 8, 32), dk); r.scale.set(0.82, 1.05, 1); g.add(r); g.position.set(an.p[0], an.p[1], an.p[2]).addScaledVector(new V3(...an.n), 0.036); g.quaternion.copy(orient(an.n)); hold.add(g); ch.follow(g, g.position); worn.push({ name: 'glasses', obj: g }); }
      const aL = A['eye.L'], aR = A['eye.R']; if (aL && aR) { const g = new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.005, Math.abs(aL.p[0] - aR.p[0]) - 0.15 * (ch.meta.face?.eyeK ?? 1), 6), dk); g.rotation.z = Math.PI / 2; g.position.set(0, aL.p[1] + 0.02, aL.p[2] + 0.034); hold.add(g); ch.follow(g, g.position); worn.push({ name: 'glasses', obj: g }); } }
    else if (a === 'scarf' && A.scarf) { const an = A.scarf, rr = an.p[2], g = new THREE.Mesh(new THREE.TorusGeometry(1, 0.2, 10, 40), mat(col, { r: 0.95 })); g.rotation.x = Math.PI / 2; g.scale.set(rr * 1.18, rr * 1.0, 0.04 / 0.2 * 1.0); g.scale.z = 0.3; g.scale.setX(rr * 1.12); g.scale.setY(rr); g.scale.setZ(0.07 / 0.2 * 0.5); g.position.set(0, an.p[1], 0); hold.add(g); ch.follow(g, g.position); worn.push({ name: 'scarf', obj: g }); g.userData.acc = 'scarf'; }
  }
  return worn;
}

// 櫻桃（布布）：小圓球＋細梗，坐在頂面凹窩裡；掛在頭骨下、跟著身體尺寸變化
export function addCherry(ch, color) {
  const h = ch.holderFor('head'); if (!h) return null; const g = new THREE.Group();
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.058, 20, 14), new THREE.MeshStandardMaterial({ color, roughness: 0.28, metalness: 0 }));
  const st = new THREE.Mesh(new THREE.CylinderGeometry(0.0055, 0.0075, 0.075, 8), new THREE.MeshStandardMaterial({ color: 0x7a9a50, roughness: 0.7 })); st.position.set(0.012, 0.062, 0); st.rotation.z = -0.3;
  const hl = new THREE.Mesh(new THREE.SphereGeometry(0.012, 8, 6), new THREE.MeshBasicMaterial({ color: 0xfff4ec })); hl.position.set(-0.02, 0.028, 0.04);
  g.add(ball, st, hl); const cp = ch.meta.cherry; g.position.set(cp ? cp[0] : 0.03, cp ? cp[1] : 0.478, cp ? cp[2] : 0); h.add(g); ch.follow(g, g.position); g.userData.acc = 'cherry'; return g;
}
