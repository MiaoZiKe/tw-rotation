// 糰糰 v2：載入 Blender 產出的一體成形網格（GLB）＋骨架＋形態鍵，在執行期掛上材質、臉、物理驅動介面。
//
// 第三階段要接的介面（全部以「模型座標」表示：X 往角色的左、Y 向上、Z 朝前；角度為弧度）：
//   const asset = await loadMochi({ lod: 0 });           // 載入一次，可重複 new
//   const ch = new MochiChar(asset, { preset: 'fur', color: 0xffdcc4, top: 0xfff4e8 });
//   scene.add(ch.root);   // root 的 position／rotation.y 就是角色在世界的位置與朝向（腳底在 y=0）
//   ch.rot('head', x, y, z)   // 骨頭相對「靜止姿勢」的旋轉（模型座標軸的歐拉角 XYZ），自動套上父骨頭的目前動作
//   ch.move('pelvis', dx, dy, dz)  // 骨頭相對靜止位置的位移（模型座標，公尺）
//   ch.morph('squash', 0.6)   // 形態鍵權重 0..1：squash stretch land plump breath cheek.L cheek.R
//   ch.face.set('happy'); ch.face.lookAt(yaw, pitch); ch.face.blinkNow();
//   ch.update(dt)             // 每幀呼叫一次（臉、眼睛位置、頂點色以外全部在這裡收尾）
//   ch.resetPose(); ch.dispose();
// 骨頭名稱：root pelvis spine head tail tail.tip ear.L ear.R ear.tip.L ear.tip.R arm.L arm.R hand.L hand.R leg.L leg.R foot.L foot.R
import * as THREE from 'three';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { makeMaterial, setAOStrength, aoAt, PRESETS } from '../play/materials.js';
import { cloneSkinned } from './skin.js';
import { FaceRig } from './facerig.js';

const BASE = new URL('./models/', import.meta.url).href;
const cache = new Map();
export const SHAPES = ['squash', 'stretch', 'land', 'plump', 'breath', 'cheek.L', 'cheek.R'];

/** 載入（並快取）一個 LOD：回傳 { scene, meta, lod, loadMs }。 */
export function loadMochi({ lod = 0 } = {}) {
  const key = 'mochi' + lod; if (cache.has(key)) return cache.get(key);
  const t0 = performance.now();
  const p = Promise.all([new GLTFLoader().loadAsync(BASE + `mochi_lod${lod}.glb`), fetch(BASE + 'mochi.json').then(r => r.json())]).then(([g, meta]) => {
    g.scene.updateMatrixWorld(true); return { scene: g.scene, meta, lod, loadMs: performance.now() - t0 };
  });
  cache.set(key, p); return p;
}

const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3();
export class MochiChar {
  constructor(asset, o = {}) {
    this.meta = asset.meta; this.lod = asset.lod; this.root = new THREE.Group(); this.root.name = 'mochi';
    this.model = cloneSkinned(asset.scene); this.root.add(this.model); this.model.updateMatrixWorld(true);
    // GLTFLoader 會把節點名稱裡的「.」拿掉（foot.L → footL），這裡用 mochi.json 還原成原名
    const san = {}; for (const k of Object.keys(this.meta.bones)) san[k.replace(/[\[\]\.:\/]/g, '')] = k;
    this.bones = {}; this.model.traverse(n => { if (n.isBone) this.bones[san[n.name] || n.name] = n; });
    this.body = null; this.decal = null; this.model.traverse(n => { if (n.isSkinnedMesh) { if (n.name.toLowerCase().includes('decal')) this.decal = n; else this.body = n; } });
    // 靜止姿勢資料：每根骨頭的父骨靜止世界旋轉（模型座標），用來把「模型座標軸的旋轉」換成骨頭局部旋轉
    this.rest = {}; const inv = this.model.matrixWorld.clone().invert(), M = new THREE.Matrix4();
    for (const [nm, b] of Object.entries(this.bones)) {
      const pw = new THREE.Quaternion(); if (b.parent) { M.multiplyMatrices(inv, b.parent.matrixWorld); pw.setFromRotationMatrix(M); }
      this.rest[nm] = { q: b.quaternion.clone(), p: b.position.clone(), pw, pwi: pw.clone().invert() };
    }
    this.cfg = { preset: o.preset || 'fur', color: o.color ?? 0xffdcc4, top: o.top ?? 0xfff4e8, far: !!o.far };
    this.mat = makeMaterial(this.cfg.preset, { color: this.cfg.color, top: this.cfg.top, vertexAO: true, far: this.cfg.far });
    if (this.body) { this.body.material = this.mat; this.body.castShadow = true; this.body.frustumCulled = false; setAOStrength(this.body.geometry, PRESETS[this.cfg.preset].ao); }
    this.lidMat = this.makeLidMat();
    if (this.decal) { this.decal.frustumCulled = false; }
    this.morphTargets = {};
    this.face = null;
    if (this.decal && this.bones.head) {
      // 臉的零件掛在 head 骨頭下；holder 抵銷骨頭的靜止矩陣，之後零件座標就是「靜止姿勢的模型座標」
      this.holder = new THREE.Group(); this.holder.matrixAutoUpdate = false; M.multiplyMatrices(inv, this.bones.head.matrixWorld); this.holder.matrix.copy(M.invert()); this.holder.matrixWorldNeedsUpdate = true;
      this.bones.head.add(this.holder);
      this.face = new FaceRig(this.meta, this.holder, this.decal, this.lidMat, { faceW: o.faceW || 640 });
      this.holder.traverse(n => { if (n.isMesh) n.castShadow = false; });
    }
    this.t = 0; this.breathe = o.breathe !== false; this.wm = {};
  }
  /** 眼皮殼沒有頂點色：取眼睛位置附近的 AO 與上下漸層，把顏色調到跟身體一致 */
  makeLidMat() {
    const P = PRESETS[this.cfg.preset], ao = this.body ? aoAt(this.body.geometry, this.meta.anchors['eye.L'].p) : 1, k = 1 - (1 - ao) * P.ao;
    const base = new THREE.Color(this.cfg.color).lerp(new THREE.Color(this.cfg.top), 0.1 * P.topAmt).multiplyScalar(k * 0.95);
    return makeMaterial(this.cfg.preset, { color: base, over: { topAmt: 0, noiseA: 0 }, far: this.cfg.far });
  }
  setPreset(id, extra = {}) {
    const old = this.mat, oldLid = this.lidMat; this.cfg.preset = id; Object.assign(this.cfg, extra);
    this.mat = makeMaterial(id, { color: this.cfg.color, top: this.cfg.top, vertexAO: true, far: this.cfg.far });
    this.body.material = this.mat; setAOStrength(this.body.geometry, PRESETS[id].ao); this.lidMat = this.makeLidMat();
    if (this.face) for (const e of this.face.eyes) e.lid.material = this.lidMat;
    old.dispose(); oldLid.dispose();
  }
  setColor(color, top) { this.cfg.color = color; if (top != null) this.cfg.top = top; this.setPreset(this.cfg.preset); }
  // ── 驅動介面
  rot(name, x = 0, y = 0, z = 0) {
    const b = this.bones[name], r = this.rest[name]; if (!b) return;
    _q.setFromEuler(_e.set(x, y, z, 'XYZ')); _q2.copy(r.pwi).multiply(_q).multiply(r.pw).multiply(r.q); b.quaternion.copy(_q2);
  }
  move(name, dx = 0, dy = 0, dz = 0) {
    const b = this.bones[name], r = this.rest[name]; if (!b) return; _v.set(dx, dy, dz).applyQuaternion(r.pwi); b.position.copy(r.p).add(_v);
  }
  morph(name, w) { this.wm[name] = w; for (const m of [this.body, this.decal]) { if (!m || !m.morphTargetDictionary) continue; const i = m.morphTargetDictionary[name]; if (i !== undefined) m.morphTargetInfluences[i] = w; } }
  resetPose() { for (const [nm, b] of Object.entries(this.bones)) { b.quaternion.copy(this.rest[nm].q); b.position.copy(this.rest[nm].p); } for (const s of SHAPES) this.morph(s, 0); }
  /** 骨頭在模型座標的目前位置 */
  boneWorld(name, out = new THREE.Vector3()) { this.model.updateMatrixWorld(); const b = this.bones[name]; return b.getWorldPosition(out).applyMatrix4(this.root.matrixWorld.clone().invert()); }
  update(dt) {
    this.t += dt;
    if (this.face) {
      // 形態鍵造成的身體尺寸改變 → 眼睛位置跟著走
      const w = this.wm, g = (k) => w[k] || 0;
      const sx = 1 + g('squash') * 0.10 + g('stretch') * -0.065 + g('land') * 0.17 + g('plump') * 0.07;
      const sz = 1 + g('squash') * 0.10 + g('stretch') * -0.065 + g('land') * 0.17 + g('plump') * 0.07;
      const sy = 1 + g('squash') * -0.20 + g('stretch') * 0.15 + g('land') * -0.30 + g('plump') * -0.025;
      this.face.setMorphScale(sx, sy, sz); this.face.update(dt);
    }
    this.model.updateMatrixWorld(true);
  }
  dispose() {
    this.mat.dispose(); this.lidMat.dispose(); if (this.face) { this.face.tex.dispose(); this.holder.traverse(n => { if (n.isMesh && !n.geometry.userData.shared) n.geometry.dispose(); }); this.decal.material.dispose(); }
    this.root.removeFromParent();
  }
}
