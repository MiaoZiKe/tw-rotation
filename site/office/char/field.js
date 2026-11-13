// 展示頁的「走動小場地」：地毯、箱子、矮凳、四面邊界（視覺＋物理），並把鍵盤／指標輸入接到控制器。
import * as THREE from 'three';
import { PhysWorld } from './physics.js';
import { CharController, loadProfile } from './controller.js';

const V3 = THREE.Vector3;
export const FIELD = { half: 2.3 };

function roundedBox(w, h, d, r, seg = 5) {
  const g = new THREE.BoxGeometry(w, h, d, seg, seg, seg), p = g.attributes.position, hx = w / 2 - r, hy = h / 2 - r, hz = d / 2 - r, q = new V3(), c = new V3();
  for (let i = 0; i < p.count; i++) {
    q.fromBufferAttribute(p, i); c.set(Math.max(-hx, Math.min(hx, q.x)), Math.max(-hy, Math.min(hy, q.y)), Math.max(-hz, Math.min(hz, q.z)));
    q.sub(c); const l = q.length(); if (l > 1e-6) q.multiplyScalar(r / l); p.setXYZ(i, c.x + q.x, c.y + q.y, c.z + q.z);
  }
  g.computeVertexNormals(); return g;
}
function rugTexture() {
  const s = 512, cv = document.createElement('canvas'); cv.width = cv.height = s; const g = cv.getContext('2d'), r = 60;
  const rr = (m, c) => { g.fillStyle = c; g.beginPath(); g.roundRect(m, m, s - 2 * m, s - 2 * m, r); g.fill(); };
  rr(10, 'rgba(232,206,184,0.55)'); rr(22, 'rgba(250,240,228,0.96)'); rr(52, 'rgba(244,226,208,0.7)'); rr(60, 'rgba(252,245,236,0.98)');
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

export class Field {
  constructor(scene, stage) {
    this.scene = scene; this.stage = stage; this.group = new THREE.Group(); this.group.name = 'field'; scene.add(this.group);
    const H = FIELD.half; this.world = new PhysWorld({ minX: -H, maxX: H, minZ: -H, maxZ: H }); this.meshes = {};
    // 地毯（只是地面的視覺界線，不是碰撞）
    const rug = new THREE.Mesh(new THREE.PlaneGeometry(H * 2 + 0.5, H * 2 + 0.5), new THREE.MeshBasicMaterial({ map: rugTexture(), transparent: true, depthWrite: false })); rug.rotation.x = -Math.PI / 2; rug.position.y = 0.0015; rug.renderOrder = -2; this.group.add(rug); this.rug = rug;
    const wood = new THREE.MeshStandardMaterial({ color: 0xd9a77c, roughness: 0.85, metalness: 0, envMapIntensity: 0.6 }), wood2 = new THREE.MeshStandardMaterial({ color: 0xc58f66, roughness: 0.9, metalness: 0, envMapIntensity: 0.5 }), cream = new THREE.MeshStandardMaterial({ color: 0xf1dcc2, roughness: 0.95, metalness: 0, envMapIntensity: 0.5 });
    const add = (m, x, y, z, sh = true) => { m.position.set(x, y, z); m.castShadow = sh; m.receiveShadow = true; this.group.add(m); return m; };
    // 箱子：0.5 × 0.34 × 0.5（比身高低，跳得上去）
    const crate = add(new THREE.Mesh(roundedBox(0.5, 0.34, 0.5, 0.035), wood), 1.15, 0.17, -0.85); crate.name = 'crate';
    const strap = add(new THREE.Mesh(roundedBox(0.52, 0.05, 0.52, 0.018), wood2), 1.15, 0.17, -0.85, false);
    this.world.addBox({ id: 'crate', cx: 1.15, cz: -0.85, hx: 0.25, hz: 0.25, y0: 0, y1: 0.34 }); this.meshes.crate = crate;
    // 矮凳：座面 0.30 高、0.44 見方
    const sx = -1.1, sz = -0.7, st = new THREE.Group(); st.name = 'stool'; st.position.set(sx, 0, sz);
    const seat = new THREE.Mesh(roundedBox(0.44, 0.06, 0.44, 0.025), cream); seat.position.y = 0.27; seat.castShadow = seat.receiveShadow = true; st.add(seat);
    for (const [lx, lz] of [[-0.15, -0.15], [0.15, -0.15], [-0.15, 0.15], [0.15, 0.15]]) { const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.034, 0.25, 12), wood); leg.position.set(lx, 0.125, lz); leg.castShadow = leg.receiveShadow = true; st.add(leg); }
    this.group.add(st); this.meshes.stool = st; this.stool = st;
    this.world.addBox({ id: 'stool', cx: sx, cz: sz, hx: 0.22, hz: 0.22, y0: 0, y1: 0.30, face: Math.PI * 0.15 });
    // 邊界矮欄（視覺）
    const rail = new THREE.MeshStandardMaterial({ color: 0xe9cfb4, roughness: 0.95, envMapIntensity: 0.5 });
    for (const [w, d, x, z] of [[H * 2 + 0.16, 0.08, 0, -H - 0.04], [H * 2 + 0.16, 0.08, 0, H + 0.04], [0.08, H * 2 + 0.16, -H - 0.04, 0], [0.08, H * 2 + 0.16, H + 0.04, 0]]) add(new THREE.Mesh(roundedBox(w, 0.1, d, 0.035), rail), x, 0.05, z, false);
    // 道具的接觸柔影
    this.blobs = [];
    const blob = (x, z, sx, sz, op) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: stage.texBody, transparent: true, depthWrite: false, opacity: op })); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.0025, z); m.scale.set(sx, sz, 1); m.renderOrder = 1; this.group.add(m); this.blobs.push(m); };
    blob(1.15, -0.85, 0.95, 0.95, 0.5); blob(sx, sz, 0.8, 0.8, 0.42);
    this.keys = new Set(); this.ctl = null; this.dragMode = false;
  }
  async attach(ch, { x = 0, z = 0.9, yaw = Math.PI, keep = null, seed } = {}) {
    if (!this.profile) this.profile = await loadProfile(new URL('./profiles/mochi.json', import.meta.url).href);
    const old = this.ctl, pos = keep || old && { x: old.body.x, z: old.body.z, yaw: old.body.yaw };
    this.ctl = new CharController(ch, this.world, this.profile, { x: pos?.x ?? x, z: pos?.z ?? z, yaw: pos?.yaw ?? yaw, seed });
    return this.ctl;
  }
  setVisible(v) { this.group.visible = v; }
  /** 滑鼠／觸控射線（THREE.Raycaster）：回傳 { kind:'head'|'stool'|'crate'|'ground'|null, point, d } */
  pick(rc) {
    const ctl = this.ctl, ch = ctl?.ch, ray = rc.ray; let best = { kind: null, d: 1e9, point: null };
    if (ch) {
      ch.root.updateMatrixWorld(true);
      const head = new V3(0, 0.46, 0.02).applyMatrix4(ch.root.matrixWorld), hit = new V3(), sph = new THREE.Sphere(head, 0.37);
      if (ray.intersectSphere(sph, hit)) { const loc = ch.root.worldToLocal(hit.clone()); if (loc.y > 0.4) { const d = hit.distanceTo(ray.origin); if (d < best.d) best = { kind: 'head', d, point: hit.clone() }; } }
    }
    for (const k of ['stool', 'crate']) { const h = rc.intersectObject(this.meshes[k], true)[0]; if (h && h.distance < best.d) best = { kind: k, d: h.distance, point: h.point.clone() }; }
    const hit = new V3(); if (best.kind == null && ray.intersectPlane(new THREE.Plane(new V3(0, 1, 0), 0), hit)) best = { kind: 'ground', d: hit.distanceTo(ray.origin), point: hit };
    return best;
  }
  update(dt) { if (this.ctl) { this.ctl.update(dt); } }
  dispose() { this.scene.remove(this.group); }
}
