// 樣張頁：場景、燈光、介面、截圖用的控制介面
import { THREE, softMat, canvasTex, clamp, lerp } from './core.js';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { buildChar, SPECS } from './character.js';
import { Animator, ACTION_LIST } from './anim.js';

const qs = new URLSearchParams(location.search);
const cv = document.getElementById('cv'), stage = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 60);
const controls = new OrbitControls(camera, cv);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.enablePan = false; controls.minDistance = 1.6; controls.maxDistance = 16; controls.maxPolarAngle = 1.52; controls.minPolarAngle = 0.5;

// 暖色柔光：半球光打底（不會有死黑的暗面）＋暖色主光＋冷色背光
scene.add(new THREE.HemisphereLight(0xfffaf2, 0xffe6de, 2.15));
const key = new THREE.DirectionalLight(0xfff0dc, 1.25); key.position.set(2.2, 4.5, 3.4); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 5; key.shadow.bias = -0.0006; key.shadow.normalBias = 0.03;
Object.assign(key.shadow.camera, { left: -3.6, right: 3.6, top: 3.2, bottom: -1.5, near: 0.5, far: 14 }); scene.add(key);
const back = new THREE.DirectionalLight(0xdcecff, 0.55); back.position.set(-3, 2.5, -3.5); scene.add(back);

// 地面：柔邊圓形舞台＋會跟著走路捲動的淡色圓點
const groundTex = canvasTex(512, 512, (c) => { const g = c.createRadialGradient(256, 256, 0, 256, 256, 256); g.addColorStop(0, 'rgba(255,241,220,1)'); g.addColorStop(0.55, 'rgba(255,238,214,0.95)'); g.addColorStop(1, 'rgba(255,236,210,0)'); c.fillStyle = g; c.fillRect(0, 0, 512, 512); });
const ground = new THREE.Mesh(new THREE.PlaneGeometry(13, 13), new THREE.MeshBasicMaterial({ map: groundTex, transparent: true, depthWrite: false })); ground.rotation.x = -Math.PI / 2; ground.renderOrder = -3; scene.add(ground);
const dotT = canvasTex(256, 256, (c) => { c.clearRect(0, 0, 256, 256); c.fillStyle = 'rgba(255,214,184,0.4)'; for (const [x, y, r] of [[64, 64, 9], [192, 192, 9], [192, 64, 5], [64, 192, 5]]) { c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); } });
dotT.wrapS = dotT.wrapT = THREE.RepeatWrapping; dotT.repeat.set(9, 9);
const dotAlpha = canvasTex(256, 256, (c) => { const g = c.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, '#fff'); g.addColorStop(0.45, '#bbb'); g.addColorStop(0.8, '#000'); c.fillStyle = g; c.fillRect(0, 0, 256, 256); });
const dots = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshBasicMaterial({ map: dotT, alphaMap: dotAlpha, transparent: true, depthWrite: false })); dots.rotation.x = -Math.PI / 2; dots.position.y = 0.002; dots.renderOrder = -2; scene.add(dots);
const blobT = canvasTex(128, 128, (c) => { const g = c.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, 'rgba(150,105,95,0.42)'); g.addColorStop(0.5, 'rgba(150,105,95,0.26)'); g.addColorStop(1, 'rgba(150,105,95,0)'); c.fillStyle = g; c.fillRect(0, 0, 128, 128); });

// 角色
const IDS = ['human', 'cat', 'alien', 'ghost', 'pet'];
const chars = {}, anims = {}, blobs = {};
for (const id of IDS) {
  const ch = chars[id] = buildChar(id); scene.add(ch.root); anims[id] = new Animator(ch);
  const b = blobs[id] = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: blobT, transparent: true, depthWrite: false })); b.rotation.x = -Math.PI / 2; b.position.y = 0.004; b.renderOrder = -1; scene.add(b);
}

const state = { char: qs.get('char') || 'all', action: qs.get('action') || 'idle', expr: qs.get('expr') || 'auto', view: 'front', box: [2, 2], center: 0.66 };
const narrow = () => stage.clientWidth / stage.clientHeight < 0.95;
function layout() {
  const { char, action } = state; let w = 1.75, h = 1.8, cy = 0.68;
  for (const id of IDS) { const ch = chars[id]; ch.root.visible = false; ch.root.position.set(0, 0, 0); ch.root.rotation.y = 0; ch.phase = 0; ch.noTable = false; ch.lookAmp = 0.35; }
  const put = (id, x, z, ry = 0, act = action) => { const ch = chars[id]; ch.root.visible = true; ch.root.position.set(x, 0, z); ch.root.rotation.y = ry; anims[id].play(act); };
  if (char === 'all') {
    if (narrow()) { put('alien', -0.62, -1.45); put('ghost', 0.62, -1.45); put('human', -0.58, 0.35); put('cat', 0.58, 0.35); put('pet', 0, 1.15); w = 2.6; h = 3.3; cy = 0.6; }
    else { const big = ['type', 'argue'].includes(action), sp = big ? 1.45 : 1.08; ['human', 'cat', 'alien', 'ghost'].forEach((id, i) => put(id, (i - 1.5) * sp - 0.38, 0)); put('pet', 1.5 * sp + 0.42, 0.15); w = sp * 3 + 2.0; h = 1.9; }
  } else if (char === 'meeting') {
    put('human', -0.86, 0.12, Math.PI / 2, 'argue'); put('alien', 0.86, 0.12, -Math.PI / 2, 'argue'); chars.alien.phase = 2.6; chars.alien.noTable = true;
    put('cat', 0.0, -0.8, 0, 'notes'); chars.cat.lookAmp = 0.6; put('ghost', 1.95, -0.45, -0.7, 'research'); put('pet', -1.8, -0.1, 0.7, 'notes');
    w = 5.2; h = 2.1; cy = 0.62;
  } else {
    put(char, 0, 0); if (char === 'pet') { w = 1.0; h = 0.9; cy = 0.26; }
    else if (action === 'type') { w = 2.0; } else if (action === 'hit') { w = 3.0; h = 2.3; cy = 0.85; } else if (action === 'celebrate') { h = 2.2; cy = 0.8; } else if (action === 'argue') { w = 2.1; }
  }
  { const tb = chars.human.props.table, m = char === 'meeting'; tb.position.z = m ? 0.86 : 0.56; tb.userData.s0 = m ? 1.7 : 1; }
  for (const id of IDS) for (const sp of chars[id].springs) sp.reset();
  for (const id of IDS) anims[id].exprOverride = state.expr === 'auto' ? null : state.expr;
  state.box = [w, h]; state.center = cy;
  const c = char === 'all' || char === 'meeting' ? null : SPECS[char];
  document.getElementById('cName').textContent = c ? c.name : char === 'all' ? '全員集合' : '會議小場景';
  document.getElementById('cMeta').textContent = c ? `${c.kind}・${c.role}` : char === 'all' ? '小禾・麻糬・啾比・飄飄・雪球' : '兩人爭執，一人做筆記';
}
const YAW = { front: 0, q: 0.72, side: Math.PI / 2, back: Math.PI, desk: 2.3 };
function frame(view = state.view, instant = true) {
  state.view = view; const [w, h] = state.box, asp = camera.aspect, tf = Math.tan(camera.fov * Math.PI / 360);
  const dist = Math.max(h / 2 / tf, w / 2 / (tf * asp)) * 1.06 + 0.4, yaw = YAW[view] ?? 0, pitch = state.char === 'meeting' ? 0.36 : state.char === 'all' && narrow() ? 0.5 : 0.24;
  controls.target.set(state.char === 'pet' ? 0 : 0, state.center, 0);
  camera.position.set(Math.sin(yaw) * Math.cos(pitch) * dist, state.center + Math.sin(pitch) * dist, Math.cos(yaw) * Math.cos(pitch) * dist);
  controls.update();
}
function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }

// 介面
const chip = (box, list, get, set) => { const el = document.getElementById(box); el.innerHTML = ''; for (const [v, label, sub] of list) { const b = document.createElement('button'); b.innerHTML = label + (sub ? `<small>${sub}</small>` : ''); b.dataset.v = v; b.onclick = () => { set(v); sync(); }; el.appendChild(b); } el._get = get; };
function sync() { for (const id of ['chars', 'acts', 'exprs', 'views']) { const el = document.getElementById(id); for (const b of el.children) b.classList.toggle('on', b.dataset.v === el._get()); } }
chip('chars', [['all', '全員'], ['meeting', '會議場景'], ...IDS.map((id) => [id, SPECS[id].name, SPECS[id].kind])], () => state.char, (v) => { state.char = v; layout(); frame(v === 'meeting' ? 'front' : state.view); });
chip('acts', ACTION_LIST, () => state.action, (v) => { state.action = v; if (state.char === 'meeting') state.char = 'all'; layout(); frame(); });
chip('exprs', [['auto', '跟著動作'], ['happy', '開心'], ['angry', '生氣'], ['surprised', '驚訝'], ['think', '思考'], ['sad', '難過'], ['smug', '得意']], () => state.expr, (v) => { state.expr = v; layout(); });
chip('views', [['front', '正面'], ['q', '斜側'], ['side', '側面'], ['back', '背面'], ['desk', '看螢幕']], () => state.view, (v) => frame(v));

let last = performance.now();
function step(dt, draw = true) {
  let speed = 0;
  for (const id of IDS) { const ch = chars[id]; if (!ch.root.visible) continue; anims[id].update(dt); speed = Math.max(speed, anims[id].out.speed * (ch.pet && state.char !== 'pet' ? 0 : 1));
    const b = blobs[id]; b.visible = true; ch.rig.getWorldPosition(b.position); const hgt = b.position.y; b.position.y = 0.004; const s = (ch.pet ? 0.62 : ch.spec.ghost ? 0.62 : 0.8) * (ch.props.desk?.visible ? 1.5 : 1) / (1 + hgt * 0.9); b.scale.set(s, s, 1); b.material.opacity = ch.spec.ghost ? 0.6 : 1; }
  for (const id of IDS) if (!chars[id].root.visible) blobs[id].visible = false;
  dotT.offset.y += speed * dt / (9 / 9) * (state.char === 'meeting' ? 0 : 1);
  if (draw) { controls.update(); renderer.render(scene, camera); }
}
function loop(now) { const dt = Math.min(0.05, (now - last) / 1000); last = now; if (!paused) step(dt); requestAnimationFrame(loop); }
let paused = qs.get('auto') === '0';
window.addEventListener('resize', () => { resize(); layout(); frame(); });
resize(); layout(); frame('front'); sync(); step(0.016);
document.getElementById('loading').classList.add('off');
requestAnimationFrame(loop);

// 給自動截圖用
window.OFFICE = {
  set(o) { Object.assign(state, o); layout(); frame(o.view || state.view); sync(); },
  step(sec, dt = 1 / 60) { const n = Math.round(sec / dt); for (let i = 0; i < n; i++) step(dt, i === n - 1); },
  pause(v) { paused = v; }, state, chars, anims, camera, controls, ready: true,
};
