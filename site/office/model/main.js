// 角色模型實驗頁：載入自動綁骨架的模型，動作／表情／上色模式切換
import * as THREE from '../vendor/three.module.min.js';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { Char } from './char.js';
import { Loco } from './locomotion.js';
import { ACTIONS, ACTION_ORDER } from './actions.js';
import { EXPRESSIONS } from './face.js';

const Q = new URLSearchParams(location.search), SHOT = Q.has('shot');
const view = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: SHOT });
renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); renderer.outputColorSpace = THREE.SRGBColorSpace;
view.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color('#fbefe2'); scene.fog = new THREE.Fog('#fbefe2', 14, 30);
const cam = new THREE.PerspectiveCamera(28, 1, 0.1, 60); cam.position.set(1.6, 1.5, 6.2);
const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(0, 0.95, 0); ctl.enableDamping = true; ctl.enablePan = false; ctl.minDistance = 1.2; ctl.maxDistance = 12; ctl.maxPolarAngle = Math.PI * 0.55; ctl.autoRotateSpeed = 4; ctl.update();
scene.add(new THREE.HemisphereLight(0xffffff, 0xf3d9c4, 2.3));
const key = new THREE.DirectionalLight(0xfff4e6, 1.9); key.position.set(2.5, 4, 5); scene.add(key);
const back = new THREE.DirectionalLight(0xcfe2ff, 1.1); back.position.set(-3, 3, -4); scene.add(back);

// 地面：淡淡的地磚，走動時看得出位移；柔和的圓形影子
const gc = document.createElement('canvas'); gc.width = gc.height = 256; { const g = gc.getContext('2d'); g.fillStyle = '#f4e2cf'; g.fillRect(0, 0, 256, 256); g.fillStyle = '#efdac4'; g.fillRect(0, 0, 128, 128); g.fillRect(128, 128, 128, 128); g.strokeStyle = '#e9d1b8'; g.lineWidth = 3; g.strokeRect(0, 0, 128, 128); g.strokeRect(128, 128, 128, 128); }
const gt = new THREE.CanvasTexture(gc); gt.wrapS = gt.wrapT = THREE.RepeatWrapping; gt.repeat.set(30, 30); gt.colorSpace = THREE.SRGBColorSpace; gt.anisotropy = 8;
const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshBasicMaterial({ map: gt })); ground.rotation.x = -Math.PI / 2; ground.position.y = -0.002; scene.add(ground);
const sc = document.createElement('canvas'); sc.width = sc.height = 128; { const g = sc.getContext('2d'), gr = g.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(120,80,50,0.42)'); gr.addColorStop(1, 'rgba(120,80,50,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); }
const shadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(sc), transparent: true, depthWrite: false })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.002; scene.add(shadow);

const char = new Char(); scene.add(char.root);
// 道具（桌椅跟著角色所在位置）
const M = (c, r = 0.8) => new THREE.MeshStandardMaterial({ color: c, roughness: r });
const box = (w, h, d, c, x, y, z, par) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), M(c)); m.position.set(x, y, z); par.add(m); return m; };
const desk = new THREE.Group(); char.root.add(desk);
function buildDesk(m) { desk.clear(); const top = m.deskTop, seat = m.seatTop;
  box(1.5, 0.05, 0.7, '#f1c999', 0, top - 0.025, 0.72, desk); for (const sx of [-0.68, 0.68]) for (const sz of [0.42, 1.02]) box(0.06, top - 0.05, 0.06, '#d8a877', sx, (top - 0.05) / 2, sz, desk);
  box(0.46, 0.022, 0.3, '#cfd6e2', 0, top + 0.011, 0.56, desk); const lid = box(0.46, 0.3, 0.02, '#b9c2d2', 0, top + 0.16, 0.74, desk); lid.rotation.x = 0.22; const scr = box(0.42, 0.26, 0.005, '#8fd0ff', 0, top + 0.16, 0.725, desk); scr.rotation.x = 0.22;
  box(0.5, 0.06, 0.46, '#7fb6a8', 0, seat - 0.03, -0.1, desk); box(0.5, 0.5, 0.05, '#7fb6a8', 0, seat + 0.3, -0.36, desk); box(0.08, seat - 0.06, 0.08, '#5f8f84', 0, (seat - 0.06) / 2, -0.1, desk); box(0.42, 0.03, 0.42, '#5f8f84', 0, 0.015, -0.1, desk); }
const pad = new THREE.Group(); box(0.26, 0.016, 0.34, '#fff8e8', 0, 0, 0, pad); box(0.26, 0.02, 0.04, '#e86a5a', 0, 0.004, -0.15, pad); for (let i = 0; i < 4; i++) box(0.17, 0.004, 0.008, '#9aa7bd', -0.01, 0.01, -0.07 + i * 0.045, pad); scene.add(pad);
const pen = new THREE.Group(); { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.17, 10), M('#3f6fd8', 0.4)); b.position.y = 0.035; pen.add(b); const tip = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.035, 10), M('#2b2b33', 0.5)); tip.rotation.x = Math.PI; tip.position.y = -0.0675; pen.add(tip); }
// 特效：暈眩星星、撞擊
const stars = new THREE.Group(); scene.add(stars); { const sg = new THREE.OctahedronGeometry(0.05); for (let i = 0; i < 4; i++) stars.add(new THREE.Mesh(sg, new THREE.MeshBasicMaterial({ color: '#ffc531' }))); }
const impact = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.025, 8, 32), new THREE.MeshBasicMaterial({ color: '#ff7a59', transparent: true })); char.root.add(impact);

let skel = null, loco = null;
const state = { action: 'idle', pending: null, t: 0, expr: 'auto', mode: 'part', lod: 'hi', skel: false, spin: false, speed: 1, blinkAt: 2, blink: 0, wp: 0, opts: {} };
const dims = {};
const ROUTE = [[0, 1.6], [1.9, 1.6], [1.9, -1.2], [-1.9, -1.2], [-1.9, 1.6]];
const _v = new THREE.Vector3(), _v2 = new THREE.Vector3(), last = new THREE.Vector3();
function bonePos(n, out) { return char.bones[n].getWorldPosition(out); }

async function loadLod(lod) {
  await char.load('models/', 'boy', lod); state.lod = lod;
  const J = char.meta.joints, shin = J.shinL[1] - J.footL[1];
  dims.sitDrop = J.thighL[1] - (J.footL[1] + shin + 0.015); dims.lieDrop = J.hips[1] - 0.27;
  dims.seatTop = J.thighL[1] - dims.sitDrop - 0.105; dims.deskTop = dims.seatTop + 0.4;
  buildDesk(dims);
  if (!loco) { loco = new Loco(char); loco.update(0); }
  // 筆握在右手：夾在拇指與食指之間，筆桿往虎口靠
  const fg = char.fingers.filter((f) => f.side === 'R');
  if (fg.length >= 2) { const th = fg.find((f) => f.kind === 'thumb'), ix = fg.find((f) => f.kind === 'index'), Jv = char.J;
    const pinch = Jv[th.bones[0] + '_end'].clone().add(Jv[ix.bones[1] + '_end']).multiplyScalar(0.5), web = Jv[th.bones[0]].clone().add(Jv[ix.bones[0]]).multiplyScalar(0.5);
    const dir = web.clone().sub(pinch).normalize(); pen.position.copy(pinch).sub(Jv.handR).addScaledVector(dir, 0.02); pen.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir); char.bones.handR.add(pen); }
  if (skel) { scene.remove(skel); skel = null; }
  skel = new THREE.SkeletonHelper(char.model); skel.material.depthTest = false; skel.material.color.set('#e11d48'); skel.material.vertexColors = false; skel.visible = state.skel; scene.add(skel);
  const info = document.getElementById('info'); if (info) info.textContent = `${+(char.count.tris / 10000).toFixed(1)} 萬面 · ${char.count.bones} 根骨頭`;
}

function frame(dt) {
  let A = ACTIONS[state.action]; state.t += dt * state.speed; const sdt = dt * state.speed;
  // 從走跑換到別的動作：先減速停好（腳收回站姿）才換，不會腳滑
  if (state.pending && (loco.settled || !A.loco)) { char.beginBlend(0.35); state.action = state.pending; state.pending = null; state.t = 0; A = ACTIONS[state.action]; syncUI(); }
  const cmd = { speed: 0 };
  if (A.loco && !state.pending) { cmd.speed = A.loco; const w = state.route || ROUTE; let p = w[state.wp % w.length];
    if (Math.hypot(p[0] - loco.x, p[1] - loco.z) < (state.routeOnce && state.wp >= w.length - 1 ? 0.4 : 0.62)) { if (state.routeOnce && state.wp >= w.length - 1) cmd.speed = 0; else { state.wp++; p = w[state.wp % w.length]; } }
    cmd.yaw = Math.atan2(p[0] - loco.x, p[1] - loco.z); cmd.turnRate = A.loco > 1 ? 3.2 : 2.4;
    if (state.routeOnce && state.wp >= w.length - 1) { const d = Math.hypot(p[0] - loco.x, p[1] - loco.z); cmd.speed = d < 0.12 ? 0 : Math.min(A.loco, Math.max(0.25, d * 1.6)); } }
  const lp = loco.update(sdt, cmd);
  // 站姿動作：腿由步態模組決定站多高 —— 往上不超過腿長（腳不離地），往下照動作本身
  let r;
  if (A.loco) r = { pose: lp, face: A.face };
  else { r = A.fn(state.t, dims, state.opts); if (A.stand) { r.pose.ikL = lp.ikL; r.pose.ikR = lp.ikR; r.pose.root = { ...(r.pose.root || {}) }; r.pose.root.y = lp.root.y + 0.004 + Math.min(0, r.pose.root.y || 0); } }
  char.root.position.set(loco.x, 0, loco.z); char.root.rotation.y = loco.yaw;
  char.apply(r.pose, sdt);
  // 表情：動作自帶表情，可被按鈕蓋過；自動眨眼
  state.blinkAt -= dt; if (state.blinkAt < 0) { state.blinkT = 0.18; state.blinkAt = 2 + Math.random() * 3; }
  if (state.blinkT > 0) { state.blinkT -= dt; state.blink = Math.sin(Math.PI * Math.max(0, state.blinkT) / 0.18); } else state.blink = 0;
  const f = r.face || {}; const expr = state.expr === 'auto' ? (f.expr || 'neutral') : state.expr;
  char.updateFace(state.snap ? 1 : dt, { expr, blink: state.fixBlink != null ? state.fixBlink : state.blink, mouth: f.mouth || 0, look: f.look }, cam);
  char.root.updateMatrixWorld(true);
  // 鏡頭跟著角色
  _v.set(loco.x, 0, loco.z).sub(last); ctl.target.add(_v); cam.position.add(_v); last.set(loco.x, 0, loco.z);
  // 影子跟著髖
  bonePos('hips', _v); const hgt = Math.max(0, _v.y - char.meta.joints.hips[1] + (A.prop === 'desk' ? dims.sitDrop : 0)); const s = 1.05 / (1 + hgt * 1.2);
  shadow.position.set(_v.x, 0.002, _v.z); shadow.scale.set(s * (A.prop === 'desk' ? 0.01 : 1), s, 1); shadow.material.opacity = 1 / (1 + hgt * 2);
  desk.visible = A.prop === 'desk' && char.blend > 0.5;
  pad.visible = pen.visible = A.prop === 'note';
  if (pad.visible) { bonePos('handL', _v); bonePos('handR', _v2); const yaw = loco.yaw, fw = loco.fwd();
    pad.position.copy(_v).add(_v2.clone().sub(_v).multiplyScalar(0.42)); pad.position.y = Math.min(_v.y, _v2.y) - 0.045; pad.position.addScaledVector(fw, 0.07); pad.rotation.set(0.55, yaw + 0.1, 0, 'YXZ'); }
  stars.visible = !!r.stars; if (stars.visible) { bonePos('head', _v); stars.children.forEach((m, i) => { const a = state.t * 4 + i * Math.PI / 2; m.position.set(_v.x + 0.36 * Math.cos(a), _v.y + 0.38 + 0.03 * Math.sin(a * 2), _v.z + 0.36 * Math.sin(a)).addScaledVector(loco.fwd(), -0.25); m.rotation.y = a; }); }
  impact.visible = !!r.impact; if (impact.visible) { impact.position.set(0, 1.05, 0.35); impact.scale.setScalar(1 + (1 - r.impact) * 2.5); impact.material.opacity = r.impact; }
  ctl.autoRotate = state.spin; ctl.update(); renderer.render(scene, cam);
}
function resize() { const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
function setAction(k) { if (k === state.action && !state.pending) return; const A = ACTIONS[state.action], B = ACTIONS[k];
  if (A.loco && !B.loco && !loco.settled) { state.pending = k; syncUI(); return; }
  state.pending = null; if (!(A.loco && B.loco)) char.beginBlend(k === 'hit' || state.action === 'hit' ? 0.2 : 0.4); state.action = k; state.t = 0; syncUI(); }

// 介面
const $ = (s) => document.querySelector(s);
function chips(el, items, cur, on) { el.innerHTML = ''; for (const [k, label] of items) { const b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (k === cur ? ' on' : ''); b.textContent = label; b.dataset.k = k; b.onclick = () => on(k); el.appendChild(b); } }
function syncUI() { if (SHOT) return;
  chips($('#acts'), ACTION_ORDER.map((k) => [k, ACTIONS[k].label]), state.pending || state.action, setAction);
  chips($('#exprs'), [['auto', '跟著動作'], ...Object.entries(EXPRESSIONS)], state.expr, (k) => { state.expr = k; syncUI(); });
  chips($('#modes'), [['part', '分區色'], ['proj', '正面投影'], ['clay', '素模']], state.mode, (k) => { state.mode = k; char.setMode(k); syncUI(); });
  chips($('#lods'), [['hi', '3 萬面'], ['lo', '1 萬面']], state.lod, async (k) => { await loadLod(k); char.setMode(state.mode); syncUI(); });
  chips($('#opts'), [['skel', '骨架'], ['spin', '自動旋轉']], null, (k) => { state[k] = !state[k]; if (skel) skel.visible = state.skel; syncUI(); });
  for (const b of document.querySelectorAll('#opts .chip')) b.classList.toggle('on', !!state[b.dataset.k]); }

await loadLod(Q.get('lod') || 'hi'); char.setMode('part'); resize(); window.addEventListener('resize', resize); syncUI();
if (view.clientWidth < 520) { cam.position.set(1.2, 1.35, 5.0); ctl.target.set(0, 0.98, 0); ctl.update(); }   // 窄螢幕：角色放大一點
const clock = new THREE.Clock();
if (!SHOT) renderer.setAnimationLoop(() => frame(Math.min(0.05, clock.getDelta())));
// 截圖與量測用：固定時間點、固定視角、固定步長模擬
function placeCam(o) { const tg = o.target || [0, 0.95, 0], d = o.dist || 6.4, az = o.az || 0, el = o.el != null ? o.el : 0.12;
  const bx = o.follow === false ? 0 : loco.x, bz = o.follow === false ? 0 : loco.z;
  ctl.target.set(tg[0] + bx, tg[1], tg[2] + bz); cam.position.set(tg[0] + bx + d * Math.sin(az) * Math.cos(el), tg[1] + d * Math.sin(el), tg[2] + bz + d * Math.cos(az) * Math.cos(el)); cam.fov = o.fov || 28; cam.updateProjectionMatrix(); last.set(loco.x, 0, loco.z); }
function probe() { const J = char.J, o = { t: state.t, x: loco.x, z: loco.z, yaw: loco.yaw, v: loco.v, phase: loco.phase, moving: loco.moving, action: state.action, pelvisY: bonePos('hips', new THREE.Vector3()).y, feet: {}, quats: {} };
  for (const n of ['L', 'R']) { const b = char.bones['foot' + n], ft = loco.feet[n];
    const pt = (dz) => { const p = b.localToWorld(new THREE.Vector3(0, -J['foot' + n].y, dz)); return [p.x, p.y, p.z]; };
    o.feet[n] = { swing: ft.swing, pitch: ft.pitch, ball: pt(loco.ballZ), heel: pt(loco.heelZ), reach: char.cur['reach' + n] }; }
  const W = (n) => bonePos(n, new THREE.Vector3()), deg = 180 / Math.PI, ang = (a, b, c) => a.clone().sub(b).angleTo(c.clone().sub(b)) * deg;
  const fw = loco.fwd(), sag = (a, b) => Math.atan2(b.clone().sub(a).dot(fw), -(b.y - a.y)) * deg;   // 從 a 垂下到 b 的線，往前擺幾度
  for (const n of ['L', 'R']) { o['knee' + n] = ang(W('thigh' + n), W('shin' + n), W('foot' + n)); o['arm' + n] = sag(W('upperArm' + n), W('foreArm' + n)); o['hand' + n] = sag(W('upperArm' + n), W('hand' + n)); o['elbow' + n] = ang(W('upperArm' + n), W('foreArm' + n), W('hand' + n));
    const b = char.bones['foot' + n]; o.feet[n].soleMinY = Math.min(...[loco.heelZ, 0, loco.ballZ, loco.toeZ].map((dz) => b.localToWorld(new THREE.Vector3(0, -J['foot' + n].y, dz)).y)); }
  { const h = W('hips'), nk = W('neck'); o.lean = Math.atan2(nk.clone().sub(h).dot(fw), nk.y - h.y) * deg; o.w = loco.w; }
  for (const k in char.cur.q) o.quats[k] = char.cur.q[k].toArray();
  return o; }
window.stage = { async set(o = {}) {
  if (o.lod && o.lod !== state.lod) await loadLod(o.lod);
  if (o.mode) { state.mode = o.mode; char.setMode(o.mode); }
  if (o.faceOn != null) char.uniforms.uFaceOn.value = o.faceOn;
  if (o.skel != null) { state.skel = o.skel; skel.visible = o.skel; }
  if (o.palette) char.setPalette(o.palette);
  state.pending = null; state.action = o.action || 'idle'; state.expr = o.expr || 'auto'; state.fixBlink = o.blink != null ? o.blink : 0; state.opts = o.opts || {};
  loco.reset(o.x || 0, o.z || 0, o.yaw || 0); loco.update(0); state.wp = 0; state.route = o.route || null; state.routeOnce = !!o.routeOnce;
  resize(); state.speed = 1; state.t = 0; char.blend = 1; state.snap = true;
  // 走跑要先模擬到穩定步態；其他動作直接跳到指定時間
  const A = ACTIONS[state.action], dt = 1 / 60;
  if (A.loco) { const n = Math.round((o.t != null ? o.t : 3) / dt); for (let i = 0; i < n; i++) stepNoRender(dt); } else { state.t = o.t || 0; }
  placeCam(o); state.speed = 0; frame(0); state.speed = 1; return probe(); },
  step(dt = 1 / 60, n = 1, camOpts) { state.snap = false; let out = []; for (let i = 0; i < n; i++) { stepNoRender(dt); out.push(probe()); } if (camOpts) placeCam(camOpts); state.speed = 0; frame(0); state.speed = 1; return out; },
  act(k) { setAction(k); }, probe, char, state, THREE, scene, get loco() { return loco; } };
function stepNoRender(dt) { const rr = renderer.render; renderer.render = () => {}; frame(dt); renderer.render = rr; }
window.READY = true;
