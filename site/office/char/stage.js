// 展示舞台：棚拍光、程序化環境、地面柔影、接觸陰影（跟著姿勢與離地高度變化）。
import * as THREE from 'three';
import { makeEnvironment } from '../play/materials.js';

export const BG = 0xf3e6d8;
function blobTex(core = 0.0, soft = 1.0) {
  const s = 128, cv = document.createElement('canvas'); cv.width = cv.height = s; const g = cv.getContext('2d');
  const gr = g.createRadialGradient(s / 2, s / 2, s * 0.5 * core, s / 2, s / 2, s * 0.5);
  gr.addColorStop(0, 'rgba(60,34,24,1)'); gr.addColorStop(0.45 * soft + 0.1, 'rgba(60,34,24,0.55)'); gr.addColorStop(0.8, 'rgba(60,34,24,0.12)'); gr.addColorStop(1, 'rgba(60,34,24,0)');
  g.fillStyle = gr; g.fillRect(0, 0, s, s); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export class Stage {
  constructor(renderer) {
    this.renderer = renderer; this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(BG);
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping; renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.VSMShadowMap;
    this.env = makeEnvironment(renderer); this.scene.environment = this.env; this.scene.environmentIntensity = 1.0;
    const S = this.scene;
    this.hemi = new THREE.HemisphereLight(0xfffaf4, 0xf4d6c0, 1.75); S.add(this.hemi);
    this.key = new THREE.DirectionalLight(0xfff1e0, 1.7); this.key.position.set(1.7, 5.2, 2.6); this.key.castShadow = true; this.key.shadow.mapSize.set(1024, 1024);
    Object.assign(this.key.shadow.camera, { left: -1.4, right: 1.4, top: 1.4, bottom: -1.4, near: 1, far: 12 }); this.key.shadow.bias = -0.0002; this.key.shadow.normalBias = 0.003; this.key.shadow.radius = 14; this.key.shadow.blurSamples = 20;
    S.add(this.key, this.key.target);
    this.rim = new THREE.DirectionalLight(0xffdcb8, 0.75); this.rim.position.set(-2.2, 2.6, -3.4); S.add(this.rim);
    this.fill = new THREE.DirectionalLight(0xdfe9ff, 0.35); this.fill.position.set(-3, 1.8, 2.5); S.add(this.fill);
    // 地面：只接影子的透明層＋淡淡的棚底漸層
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), new THREE.ShadowMaterial({ color: 0x7a3f2c, opacity: 0.07 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; S.add(floor); this.floor = floor;
    const cv = document.createElement('canvas'); cv.width = cv.height = 256; const g = cv.getContext('2d'); const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(255,250,242,0.85)'); gr.addColorStop(0.55, 'rgba(255,248,238,0.35)'); gr.addColorStop(1, 'rgba(255,246,234,0)'); g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    const disc = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false })); disc.rotation.x = -Math.PI / 2; disc.position.y = -0.002; S.add(disc); this.disc = disc;
    // 接觸陰影
    this.texBody = blobTex(0.0, 1.0); this.texFoot = blobTex(0.0, 0.7);
    this.shadows = [];
  }
  /** 為一隻角色建立接觸陰影（身體下緣的大柔影＋腹下暗部＋兩個腳掌小影） */
  addContact(ch) {
    const mk = (tex, order) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 })); m.rotation.x = -Math.PI / 2; m.renderOrder = order; this.scene.add(m); return m; };
    const o = { ch, body: mk(this.texBody, 1), belly: mk(this.texBody, 2), feet: [mk(this.texFoot, 3), mk(this.texFoot, 3)], base: 1 };
    this.shadows.push(o); return o;
  }
  removeContact(o) { for (const m of [o.body, o.belly, ...o.feet]) { m.removeFromParent(); m.material.dispose(); m.geometry.dispose(); } this.shadows = this.shadows.filter(s => s !== o); }
  updateContact() {
    const v = new THREE.Vector3(), tmp = new THREE.Vector3(); const wm = this.scene.matrixWorld;
    for (const o of this.shadows) {
      const ch = o.ch, rw = ch.root.matrixWorld; ch.root.updateMatrixWorld(true);
      const bw = (n) => ch.bones[n].getWorldPosition(new THREE.Vector3());
      const pel = bw('pelvis'), spn = bw('spine'), lf = bw('foot.L'), rf = bw('foot.R');
      const w = ch.wm, land = w.land || 0, sq = w.squash || 0, st = w.stretch || 0;
      // 離地高度：腳底與身體下緣中較低者（地面 y=0）
      const bodyBottom = (pel.y - 0.135 * (1 - 0.3 * land - 0.2 * sq)); const footBottom = Math.min(lf.y, rf.y) - 0.03; const h = Math.max(0, Math.min(bodyBottom, footBottom + 0.0));
      const lift = THREE.MathUtils.clamp(h / 0.7, 0, 1);
      const fp = 1 + 0.15 * sq + 0.28 * land - 0.07 * st;
      // 身體大柔影：離地越高越淡越大
      const cx = (pel.x + spn.x) / 2, cz = (pel.z + spn.z) / 2;
      o.body.position.set(cx, 0.002, cz + 0.02); o.body.scale.set(1.34 * fp * (1 + lift * 0.55), 1.2 * fp * (1 + lift * 0.55), 1); o.body.material.opacity = 0.34 * (1 - lift) * o.base;
      // 腹下暗部：貼著身體下緣（落地時最濃）
      o.belly.position.set(pel.x, 0.003, pel.z + 0.015); o.belly.scale.set(0.84 * fp * (1 + lift * 0.3), 0.76 * fp * (1 + lift * 0.3), 1); o.belly.material.opacity = 0.42 * (1 - Math.min(1, lift * 1.6)) * (1 - 0.15 * st) * o.base;
      [lf, rf].forEach((f, i) => { const m = o.feet[i]; m.position.set(f.x, 0.004, f.z + 0.02); const fh = THREE.MathUtils.clamp((f.y - 0.04) / 0.25, 0, 1); m.scale.set(0.34 * (1 + fh * 0.5), 0.42 * (1 + fh * 0.5), 1); m.material.opacity = 0.62 * (1 - fh) * o.base; });
    }
  }
}
