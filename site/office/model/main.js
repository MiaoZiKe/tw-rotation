// 角色模型實驗頁：載入自動綁骨架的模型，動作／表情／上色模式切換
import * as THREE from '../vendor/three.module.min.js';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { Char } from './char.js';
import { ACTIONS, ACTION_ORDER } from './actions.js';
import { EXPRESSIONS } from './face.js';

const Q = new URLSearchParams(location.search), SHOT = Q.has('shot');
const view = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: SHOT });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); renderer.outputColorSpace = THREE.SRGBColorSpace;
view.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color('#fbefe2');
const cam = new THREE.PerspectiveCamera(28, 1, 0.1, 60); cam.position.set(1.6, 1.5, 6.2);
const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(0, 0.95, 0); ctl.enableDamping = true; ctl.minDistance = 1.2; ctl.maxDistance = 12; ctl.maxPolarAngle = Math.PI * 0.55; ctl.update();
scene.add(new THREE.HemisphereLight(0xffffff, 0xf3d9c4, 2.3));
const key = new THREE.DirectionalLight(0xfff4e6, 1.9); key.position.set(2.5, 4, 5); scene.add(key);
const back = new THREE.DirectionalLight(0xcfe2ff, 1.1); back.position.set(-3, 3, -4); scene.add(back);

// 地面與柔和的圓形影子
const ground = new THREE.Mesh(new THREE.CircleGeometry(4.2, 64), new THREE.MeshBasicMaterial({ color: '#f4e2cf' })); ground.rotation.x = -Math.PI / 2; ground.position.y = -0.002; scene.add(ground);
const sc = document.createElement('canvas'); sc.width = sc.height = 128; { const g = sc.getContext('2d'), gr = g.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(120,80,50,0.42)'); gr.addColorStop(1, 'rgba(120,80,50,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); }
const shadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(sc), transparent: true, depthWrite: false })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.002; scene.add(shadow);

// 道具
const M = (c, r = 0.8) => new THREE.MeshStandardMaterial({ color: c, roughness: r });
const box = (w, h, d, c, x, y, z, par) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), M(c)); m.position.set(x, y, z); par.add(m); return m; };
const desk = new THREE.Group(); scene.add(desk);
function buildDesk(m) { desk.clear(); const top = m.deskTop, seat = m.seatTop;
  box(1.5, 0.05, 0.7, '#f1c999', 0, top - 0.025, 0.72, desk); for (const sx of [-0.68, 0.68]) for (const sz of [0.42, 1.02]) box(0.06, top - 0.05, 0.06, '#d8a877', sx, (top - 0.05) / 2, sz, desk);
  box(0.46, 0.022, 0.3, '#cfd6e2', 0, top + 0.011, 0.56, desk); const lid = box(0.46, 0.3, 0.02, '#b9c2d2', 0, top + 0.16, 0.74, desk); lid.rotation.x = 0.22; const scr = box(0.42, 0.26, 0.005, '#8fd0ff', 0, top + 0.16, 0.725, desk); scr.rotation.x = 0.22;
  box(0.5, 0.06, 0.46, '#7fb6a8', 0, seat - 0.03, -0.1, desk); box(0.5, 0.5, 0.05, '#7fb6a8', 0, seat + 0.3, -0.36, desk); box(0.08, seat - 0.06, 0.08, '#5f8f84', 0, (seat - 0.06) / 2, -0.1, desk); box(0.42, 0.03, 0.42, '#5f8f84', 0, 0.015, -0.1, desk); }
const pad = new THREE.Group(); box(0.26, 0.016, 0.34, '#fff8e8', 0, 0, 0, pad); box(0.26, 0.02, 0.04, '#e86a5a', 0, 0.004, -0.15, pad); for (let i = 0; i < 4; i++) box(0.17, 0.004, 0.008, '#9aa7bd', -0.01, 0.01, -0.07 + i * 0.045, pad); scene.add(pad);
const pen = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.2, 8), M('#3f6fd8', 0.4)); scene.add(pen);
// 特效：暈眩星星、撞擊
const stars = new THREE.Group(); scene.add(stars); { const sg = new THREE.OctahedronGeometry(0.05); for (let i = 0; i < 4; i++) stars.add(new THREE.Mesh(sg, new THREE.MeshBasicMaterial({ color: '#ffc531' }))); }
const impact = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.025, 8, 32), new THREE.MeshBasicMaterial({ color: '#ff7a59', transparent: true })); scene.add(impact);

const char = new Char(); scene.add(char.root);
let skel = null;
const state = { action: 'idle', t: 0, expr: 'auto', mode: 'part', lod: 'hi', skel: false, spin: false, speed: 1, blinkAt: 2, blink: 0 };
const dims = {};
const _v = new THREE.Vector3(), _v2 = new THREE.Vector3();
function bonePos(n, out) { return char.bones[n].getWorldPosition(out); }

async function loadLod(lod) {
  await char.load('models/', 'boy', lod); state.lod = lod;
  const J = char.meta.joints, shin = J.shinL[1] - J.footL[1];
  dims.sitDrop = J.thighL[1] - (J.footL[1] + shin + 0.015); dims.lieDrop = J.hips[1] - 0.27;
  dims.seatTop = J.thighL[1] - dims.sitDrop - 0.105; dims.deskTop = dims.seatTop + 0.4;
  buildDesk(dims);
  if (skel) { scene.remove(skel); skel = null; }
  skel = new THREE.SkeletonHelper(char.model); skel.material.depthTest = false; skel.material.color.set('#e11d48'); skel.material.vertexColors = false; skel.visible = state.skel; scene.add(skel);
  const info = document.getElementById('info'); if (info) info.textContent = `${+(char.count.tris / 10000).toFixed(1)} 萬面 · ${char.count.verts.toLocaleString()} 頂點 · 19 根骨頭`;
}

function frame(dt) {
  const A = ACTIONS[state.action]; state.t += dt * state.speed;
  const r = A.fn(state.t, dims);
  char.apply(r.pose, dt);
  // 表情：動作自帶表情，可被按鈕蓋過；自動眨眼
  state.blinkAt -= dt; if (state.blinkAt < 0) { state.blinkT = 0.16; state.blinkAt = 2 + Math.random() * 3; }
  if (state.blinkT > 0) { state.blinkT -= dt; state.blink = Math.sin(Math.PI * Math.max(0, state.blinkT) / 0.16); } else state.blink = 0;
  const f = r.face || {}; const expr = state.expr === 'auto' ? (f.expr || 'neutral') : state.expr;
  char.setFace({ expr, blink: state.fixBlink != null ? state.fixBlink : state.blink, mouth: f.mouth || 0 });
  char.root.updateMatrixWorld(true);
  // 影子跟著髖
  bonePos('hips', _v); const hgt = Math.max(0, _v.y - char.meta.joints.hips[1] + (A.prop === 'desk' ? dims.sitDrop : 0)); const s = 1.05 / (1 + hgt * 1.2);
  shadow.position.set(_v.x, 0.002, _v.z + (state.action === 'hit' ? -0.15 : 0)); shadow.scale.set(s * (A.prop === 'desk' ? 0.01 : 1), s, 1); shadow.material.opacity = 1 / (1 + hgt * 2);
  desk.visible = A.prop === 'desk' && char.blend > 0.5;
  pad.visible = pen.visible = A.prop === 'note';
  if (pad.visible) { bonePos('handL', _v); bonePos('handR', _v2); const yaw = char.root.rotation.y;
    pad.position.copy(_v).add(_v2.clone().sub(_v).multiplyScalar(0.42)); pad.position.y = Math.min(_v.y, _v2.y) - 0.035; pad.position.z += 0.07; pad.rotation.set(0.55, yaw + 0.1, 0, 'YXZ');
    pen.position.copy(_v2).add(new THREE.Vector3(0.05, 0.03, 0.09)); pen.rotation.set(0.5, 0, -0.5); }
  stars.visible = !!r.stars; if (stars.visible) { bonePos('head', _v); stars.children.forEach((m, i) => { const a = state.t * 4 + i * Math.PI / 2; m.position.set(_v.x + 0.36 * Math.cos(a), _v.y + 0.38 + 0.03 * Math.sin(a * 2), _v.z - 0.25 + 0.36 * Math.sin(a)); m.rotation.y = a; }); }
  impact.visible = !!r.impact; if (impact.visible) { impact.position.set(0, 1.05, 0.35); impact.scale.setScalar(1 + (1 - r.impact) * 2.5); impact.material.opacity = r.impact; }
  if (state.spin) char.root.rotation.y += dt * 0.6;
  ctl.update(); renderer.render(scene, cam);
}
function resize() { const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
function setAction(k) { if (k === state.action) return; char.beginBlend(k === 'hit' || state.action === 'hit' ? 0.2 : 0.4); state.action = k; state.t = 0; syncUI(); }

// 介面
const $ = (s) => document.querySelector(s);
function chips(el, items, cur, on) { el.innerHTML = ''; for (const [k, label] of items) { const b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (k === cur ? ' on' : ''); b.textContent = label; b.dataset.k = k; b.onclick = () => on(k); el.appendChild(b); } }
function syncUI() { if (SHOT) return;
  chips($('#acts'), ACTION_ORDER.map((k) => [k, ACTIONS[k].label]), state.action, setAction);
  chips($('#exprs'), [['auto', '跟著動作'], ...Object.entries(EXPRESSIONS)], state.expr, (k) => { state.expr = k; syncUI(); });
  chips($('#modes'), [['part', '分區色'], ['proj', '正面投影'], ['clay', '素模']], state.mode, (k) => { state.mode = k; char.setMode(k); syncUI(); });
  chips($('#lods'), [['hi', '3 萬面'], ['lo', '1 萬面']], state.lod, async (k) => { await loadLod(k); char.setMode(state.mode); syncUI(); });
  chips($('#opts'), [['skel', '骨架'], ['spin', '自動旋轉']], null, (k) => { state[k] = !state[k]; if (skel) skel.visible = state.skel; syncUI(); });
  for (const b of document.querySelectorAll('#opts .chip')) b.classList.toggle('on', !!state[b.dataset.k]); }

await loadLod(Q.get('lod') || 'hi'); resize(); window.addEventListener('resize', resize); syncUI();
const clock = new THREE.Clock();
if (!SHOT) renderer.setAnimationLoop(() => frame(Math.min(0.05, clock.getDelta())));
// 截圖用：固定時間點、固定視角
window.stage = { async set(o = {}) {
  if (o.lod && o.lod !== state.lod) await loadLod(o.lod);
  if (o.mode) { state.mode = o.mode; char.setMode(o.mode); }
  if (o.faceOn != null) char.uniforms.uFaceOn.value = o.faceOn;
  if (o.skel != null) { state.skel = o.skel; skel.visible = o.skel; }
  if (o.action) state.action = o.action; state.expr = o.expr || 'auto'; state.fixBlink = o.blink != null ? o.blink : 0;
  if (o.palette) char.setPalette(o.palette);
  char.root.rotation.y = o.yaw || 0; char.root.position.x = o.x || 0;
  const tg = o.target || [0, 0.95, 0], d = o.dist || 6.4, az = o.az || 0, el = o.el != null ? o.el : 0.12;
  ctl.target.set(...tg); cam.position.set(tg[0] + d * Math.sin(az) * Math.cos(el), tg[1] + d * Math.sin(el), tg[2] + d * Math.cos(az) * Math.cos(el)); cam.fov = o.fov || 28; cam.updateProjectionMatrix();
  resize(); state.t = o.t || 0; char.blend = 1; state.speed = 0; frame(0); return true; }, char, state, THREE, scene };
window.READY = true;
