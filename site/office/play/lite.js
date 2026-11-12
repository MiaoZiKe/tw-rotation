// 不需要房間也能用角色：假的地面世界、靜音的特效、以及把任一個體畫成縮圖（圖鑑、剪影圖用）
import * as THREE from 'three';
import { Character } from './character.js';

const dummy = () => { const m = new THREE.Mesh(); m.visible = false; m.material = new THREE.MeshBasicMaterial(); return m; };
// 平地、沒有家具：groundAt 永遠是 0；resolve／pushBox 不做事
export function stubWorld(o = {}) { return { plantShake: 0, groundAt: () => ({ h: o.y || 0, s: null }), resolve: () => null, pushBox() { }, bounceTramp() { }, mkShadow: o.mkShadow || dummy }; }
export const stubFx = { T: {}, spawn: () => ({ userData: {} }), burst() { }, sfx() { }, update() { } };

let thumbScene = null;
export function renderThumb(renderer, spec, o = {}) {
  const size = o.size || 256, S = thumbScene || (thumbScene = (() => { const s = new THREE.Scene(); s.add(new THREE.HemisphereLight(0xfff6ec, 0xf0cdb0, 1.35)); const k = new THREE.DirectionalLight(0xfff1e0, 2.0); k.position.set(2.5, 5, 4); s.add(k); const r = new THREE.DirectionalLight(0xffdcb8, 0.8); r.position.set(-2, 3, -5); s.add(r); return s; })());
  const space = new THREE.Group(); S.add(space);
  const c = new Character(spec, S, stubWorld(), stubFx, { space }); c.pos.set(0, 0, 0); c.yaw = o.yaw ?? 0.3; c.lookT = 1e9; c.face.blinkT = 1e9;
  const cam = new THREE.PerspectiveCamera(24, 1, 0.1, 50), d = o.dist || 4.3, cy = o.cy ?? 0.48; cam.position.set(Math.sin(o.camYaw ?? 0) * d, cy + (o.camH ?? 0.5), Math.cos(o.camYaw ?? 0) * d); cam.lookAt(0, cy, 0);
  c.lookP.copy(cam.position); const ctl = { mx: 0, mz: 0, run: false, jump: false }, env = { look: null, cam: cam.position };
  if (o.emote) c.emote(o.emote, 99);
  for (let i = 0; i < (o.frames || 40); i++) { c.step(1 / 60, ctl); c.animate(1 / 60, env); c.lookP.copy(cam.position); c.idleT = 0; }
  c.face.blink = 0; c.face.dirty = true; c.animate(1e-4, env);
  let shadow = null; if (o.shadowTex && !o.sil) { shadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: o.shadowTex, transparent: true, opacity: 0.4, depthWrite: false })); shadow.rotation.x = -Math.PI / 2; shadow.scale.setScalar(c.R * 3.2); shadow.position.y = 0.002; space.add(shadow); }
  const rt = new THREE.WebGLRenderTarget(size, size, { samples: 4 }); rt.texture.colorSpace = THREE.SRGBColorSpace;
  const prevT = renderer.getRenderTarget(), prevC = renderer.getClearColor(new THREE.Color()), prevA = renderer.getClearAlpha();
  S.overrideMaterial = o.sil ? new THREE.MeshBasicMaterial({ color: 0x1a1a1a }) : null; S.background = null;
  renderer.setRenderTarget(rt); renderer.setClearColor(o.bg ?? (o.sil ? 0xffffff : 0xfff3e4), o.sil || o.bg != null ? 1 : 0); renderer.clear(); renderer.render(S, cam);
  const px = new Uint8Array(size * size * 4); renderer.readRenderTargetPixels(rt, 0, 0, size, size, px);
  renderer.setRenderTarget(prevT); renderer.setClearColor(prevC, prevA); rt.dispose(); S.overrideMaterial = null;
  const cv = document.createElement('canvas'); cv.width = cv.height = size; const g = cv.getContext('2d'), im = g.createImageData(size, size);
  for (let y = 0; y < size; y++) im.data.set(px.subarray((size - 1 - y) * size * 4, (size - y) * size * 4), y * size * 4);
  g.putImageData(im, 0, 0);
  c.dispose(); S.remove(space); space.traverse(m => { if (m.isMesh && m.material && m.material.userData && m.material.userData.U) m.material.dispose(); });
  return cv.toDataURL('image/png');
}
