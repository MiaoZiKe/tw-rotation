// 檢查模式的疊加顯示（第四階段，開發用）：碰撞形狀、接觸點、接地偵測、速度箭頭。
// 全部用 depthTest:false 的線條與小球畫在場景最上層；預設隱藏；dispose() 會釋放幾何與材質（檢查模式開關不會讓資源增加）。
import * as THREE from 'three';

const V3 = THREE.Vector3;
const mat = (c, o = 0.9) => new THREE.LineBasicMaterial({ color: c, transparent: true, opacity: o, depthTest: false, depthWrite: false });
const dot = (c, r = 0.022) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 8), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.95, depthTest: false, depthWrite: false })); m.renderOrder = 31; return m; };

export class QAView {
  constructor(scene) {
    this.scene = scene; this.group = new THREE.Group(); this.group.name = 'qaview'; this.group.visible = false; scene.add(this.group);
    this.collide = false; this.contacts = false; this.disposables = []; this.boxKey = '';
    // 碰撞圓柱（半徑 R、高 H）與支撐圓（站在方塊邊緣的腳印）
    this.cyl = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.CylinderGeometry(1, 1, 1, 28, 1, true)), mat(0x1fa971)); this.cyl.renderOrder = 30;
    this.support = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 33 }, (_, i) => new V3(Math.cos(i / 32 * 6.2832), 0, Math.sin(i / 32 * 6.2832)))), mat(0x2b7de9)); this.support.renderOrder = 30;
    this.boxes = new THREE.Group();
    this.ring = new THREE.LineLoop(this.support.geometry, mat(0x1fa971, 1)); this.ring.renderOrder = 30;
    this.feetDots = [dot(0x1fa971), dot(0x1fa971)]; this.low = dot(0xd6336c, 0.026);
    this.arrow = new THREE.ArrowHelper(new V3(0, 1, 0), new V3(), 0.3, 0xe8590c, 0.07, 0.05); this.arrow.line.material.depthTest = false; this.arrow.cone.material.depthTest = false; this.arrow.renderOrder = 31; this.arrow.line.renderOrder = 31; this.arrow.cone.renderOrder = 31;
    this.cGroup = new THREE.Group(); this.cGroup.add(this.cyl, this.support, this.boxes);
    this.kGroup = new THREE.Group(); this.kGroup.add(this.ring, ...this.feetDots, this.low, this.arrow);
    this.group.add(this.cGroup, this.kGroup);
    this._T = new V3();
  }
  setCollide(on) { this.collide = on; this.sync(); }
  setContacts(on) { this.contacts = on; this.sync(); }
  sync() { this.cGroup.visible = this.collide; this.kGroup.visible = this.contacts; this.group.visible = this.collide || this.contacts; }
  buildBoxes(world) {
    const key = world.boxes.map(b => [b.id, b.cx, b.cz, b.hx, b.hz, b.y0, b.y1].join()).join('|'); if (key === this.boxKey) return; this.boxKey = key;
    for (const c of [...this.boxes.children]) { c.geometry.dispose(); c.material.dispose(); this.boxes.remove(c); }
    for (const b of world.boxes) { const g = new THREE.EdgesGeometry(new THREE.BoxGeometry(b.hx * 2, b.y1 - b.y0, b.hz * 2)), l = new THREE.LineSegments(g, mat(0xf08c00)); l.position.set(b.cx, (b.y0 + b.y1) / 2, b.cz); l.renderOrder = 30; this.boxes.add(l); }
  }
  /** 每幀（或每次需要）呼叫：依控制器目前狀態更新所有疊加物 */
  update(ctl) {
    if (!this.group.visible || !ctl) return;
    const b = ctl.body, sh = ctl.shape, grounded = b.grounded;
    if (this.collide) {
      this.buildBoxes(ctl.world);
      this.cyl.scale.set(sh.R, sh.H, sh.R); this.cyl.position.set(b.x, b.y + sh.H / 2, b.z); this.cyl.material.color.setHex(grounded ? 0x1fa971 : 0xf59f00);
      this.support.scale.set(sh.supportR, 1, sh.supportR); this.support.position.set(b.x, b.supportY + 0.004, b.z);
    }
    if (this.contacts) {
      this.ring.scale.set(0.12, 1, 0.12); this.ring.position.set(b.x, b.supportY + 0.006, b.z); this.ring.material.color.setHex(grounded ? 0x1fa971 : 0xf59f00);
      ctl.feet.feet.forEach((f, i) => { const d = this.feetDots[i]; if (!d) return; const w = ctl.feet.ankleWorld(f.side, this._T); d.position.set(w.x, Math.max(f.gy ?? 0, 0) + 0.012, w.z); d.material.color.setHex(f.mode !== 'plant' ? 0xf59f00 : 0x1fa971); });
      // 身體取樣最低點（蒙皮後的實際頂點）
      const ch = ctl.ch, bm = ch.body, g = bm.geometry, p = g.attributes.position, M = g.morphAttributes.position, w = bm.morphTargetInfluences, T = this._T;
      ch.model.updateMatrixWorld(true); bm.skeleton.update(); let mn = 1e9, bx = 0, bz = 0;
      for (const i of ctl.sampleIdx) { T.set(p.getX(i), p.getY(i), p.getZ(i)); for (let k = 0; k < M.length; k++) if (w[k]) { T.x += M[k].getX(i) * w[k]; T.y += M[k].getY(i) * w[k]; T.z += M[k].getZ(i) * w[k]; } bm.applyBoneTransform(i, T); T.applyMatrix4(bm.matrixWorld); if (T.y < mn) { mn = T.y; bx = T.x; bz = T.z; } }
      this.low.position.set(bx, mn, bz);
      const v = new V3(b.vx, b.vy, b.vz), sp = v.length(); this.arrow.visible = sp > 0.05; if (sp > 0.05) { this.arrow.position.set(b.x, b.y + sh.H * 0.55, b.z); this.arrow.setDirection(v.normalize()); this.arrow.setLength(Math.min(1.6, 0.12 + sp * 0.18), 0.07, 0.05); }
    }
  }
  dispose() {
    this.group.traverse(o => { if (o.geometry && !o.geometry.userData.keep) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    this.scene.remove(this.group);
  }
}
