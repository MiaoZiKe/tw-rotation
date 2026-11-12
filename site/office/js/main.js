// 樣張頁：場景、燈光、介面、截圖用的控制介面
import { THREE, canvasTex, setDetail } from './core.js';
import { OrbitControls } from '../vendor/OrbitControls.js';

const qs = new URLSearchParams(location.search);
if (qs.get('lod')) setDetail(qs.get('lod') === '1' ? 0.5 : 0.34); // 簡化等級：?lod=1（一半格數）、?lod=2（三分之一）
const { buildChar, SPECS, CHAR_IDS } = await import('./character.js');
const { Animator, ACTION_LIST } = await import('./anim.js');

const cv = document.getElementById('cv'), stage = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NoToneMapping;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(24, 1, 0.4, 60);
const controls = new OrbitControls(camera, cv);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.enablePan = false; controls.minDistance = 1.0; controls.maxDistance = 22; controls.maxPolarAngle = 1.54; controls.minPolarAngle = 0.5;

// 柔光：半球光打底（暗面不死黑）＋暖色主光（帶柔和陰影）＋冷色輪廓光
scene.add(new THREE.HemisphereLight(0xfffaf4, 0xffdccb, 1.42));
const key = new THREE.DirectionalLight(0xfff3e4, 2.1); key.position.set(-2.4, 4.6, 4.2); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -0.0004; key.shadow.normalBias = 0.012;
Object.assign(key.shadow.camera, { left: -4.2, right: 4.2, top: 3.6, bottom: -2.2, near: 0.5, far: 16 }); key.shadow.camera.updateProjectionMatrix(); scene.add(key);
const back = new THREE.DirectionalLight(0xdcebff, 0.7); back.position.set(3.2, 2.6, -3.6); scene.add(back);

// 地面：柔邊圓形舞台＋會跟著走路捲動的淡色圓點
const groundTex = canvasTex(512, 512, (c) => { const g = c.createRadialGradient(256, 256, 0, 256, 256, 256); g.addColorStop(0, 'rgba(255,243,226,1)'); g.addColorStop(0.55, 'rgba(255,240,220,0.95)'); g.addColorStop(1, 'rgba(255,238,216,0)'); c.fillStyle = g; c.fillRect(0, 0, 512, 512); });
const ground = new THREE.Mesh(new THREE.PlaneGeometry(18, 18), new THREE.MeshBasicMaterial({ map: groundTex, transparent: true, depthWrite: false })); ground.rotation.x = -Math.PI / 2; ground.renderOrder = -3; scene.add(ground);
const dotT = canvasTex(256, 256, (c) => { c.clearRect(0, 0, 256, 256); c.fillStyle = 'rgba(255,214,184,0.4)'; for (const [x, y, r] of [[64, 64, 9], [192, 192, 9], [192, 64, 5], [64, 192, 5]]) { c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); } });
dotT.wrapS = dotT.wrapT = THREE.RepeatWrapping; dotT.repeat.set(9, 9);
const dotAlpha = canvasTex(256, 256, (c) => { const g = c.createRadialGradient(128, 128, 0, 128, 128, 128); g.addColorStop(0, '#fff'); g.addColorStop(0.45, '#bbb'); g.addColorStop(0.8, '#000'); c.fillStyle = g; c.fillRect(0, 0, 256, 256); });
const dots = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshBasicMaterial({ map: dotT, alphaMap: dotAlpha, transparent: true, depthWrite: false })); dots.rotation.x = -Math.PI / 2; dots.position.y = 0.002; dots.renderOrder = -2; scene.add(dots);
const blobT = canvasTex(128, 128, (c) => { const g = c.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, 'rgba(150,105,95,0.42)'); g.addColorStop(0.5, 'rgba(150,105,95,0.26)'); g.addColorStop(1, 'rgba(150,105,95,0)'); c.fillStyle = g; c.fillRect(0, 0, 128, 128); });

// 角色
const IDS = CHAR_IDS, BIPEDS = IDS.filter((id) => !SPECS[id].pet);
const chars = {}, anims = {}, blobs = {};
for (const id of IDS) {
  const ch = chars[id] = buildChar(id); scene.add(ch.root); anims[id] = new Animator(ch);
  const b = blobs[id] = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: blobT, transparent: true, depthWrite: false })); b.rotation.x = -Math.PI / 2; b.position.y = 0.004; b.renderOrder = -1; scene.add(b);
}

const state = { char: qs.get('char') || 'all', action: qs.get('action') || 'idle', expr: qs.get('expr') || 'auto', view: 'front', box: [2, 2], center: 0.8 };
const narrow = () => stage.clientWidth / stage.clientHeight < 0.95;
function layout() {
  const { char, action } = state; let w = 1.3, h = 1.72, cy = 0.8;
  for (const id of IDS) { const ch = chars[id]; ch.root.visible = false; ch.root.position.set(0, 0, 0); ch.root.rotation.y = 0; ch.phase = 0; ch.noTable = false; ch.lookAmp = 0.35; }
  const put = (id, x, z, ry = 0, act = action) => { const ch = chars[id]; ch.root.visible = true; ch.root.position.set(x, 0, z); ch.root.rotation.y = ry; anims[id].play(act); };
  const wide = ['type', 'argue'].includes(action), far = action === 'hit';
  if (char === 'all') {
    if (narrow()) { const sx = wide || far ? 1.25 : 0.84, sz = wide ? 1.7 : 1.5; BIPEDS.forEach((id, i) => put(id, ((i % 2) - 0.5) * sx - (far ? 0.4 : 0), (Math.floor(i / 2) - 1) * sz - 0.3)); put('pet', 0, 2.05); w = sx + 1.15 + (far ? 0.9 : 0); h = 5.6; cy = 0.75; }
    else { const sp = wide ? 1.3 : far ? 1.5 : 0.76; BIPEDS.forEach((id, i) => put(id, (i - 2.5) * sp - 0.28, 0)); put('pet', 2.5 * sp + 0.42, 0.12); w = sp * 5 + 1.6 + (far ? 1 : 0); h = 2.0; cy = 0.66; }
  } else if (char === 'meeting') {
    put('kai', -0.95, 0.3, Math.PI / 2, 'argue'); put('mo', 0.95, 0.3, -Math.PI / 2, 'argue'); chars.mo.phase = 2.6; chars.mo.noTable = true;
    put('he', -0.05, -1.2, 0, 'notes'); chars.he.lookAmp = 0.6; put('alien', 2.55, -0.35, -0.8, 'research'); put('cat', -2.35, -0.45, 0.8, 'clap'); put('ghost', 1.5, -1.45, -0.35, 'think'); put('pet', -1.5, 0.75, 0.9, 'notes');
    w = 6.3; h = 2.5; cy = 0.62;
  } else {
    put(char, 0, 0); if (char === 'pet') { w = 1.0; h = 0.9; cy = 0.26; }
    else if (action === 'type') { w = 1.9; } else if (action === 'hit') { w = 3.6; h = 2.7; cy = 1.05; } else if (action === 'celebrate') { h = 2.5; cy = 1.0; } else if (action === 'argue') { w = 2.0; } else if (action === 'raise') { h = 2.1; cy = 0.9; }
  }
  { const tb = chars.kai.props.table, m = char === 'meeting'; tb.position.z = m ? 0.95 : 0.5; tb.userData.s0 = m ? 1.75 : 1.4; }
  for (const id of IDS) for (const sp of chars[id].springs) sp.reset();
  for (const id of IDS) anims[id].exprOverride = state.expr === 'auto' ? null : state.expr;
  state.box = [w, h]; state.center = cy;
  const c = char === 'all' || char === 'meeting' ? null : SPECS[char];
  document.getElementById('cName').textContent = c ? c.name : char === 'all' ? '全員集合' : '會議小場景';
  document.getElementById('cMeta').textContent = c ? `${c.kind}・${c.role}` : char === 'all' ? IDS.map((id) => SPECS[id].name).join('・') : '兩人爭執，一人做筆記，一人查資料';
}
const YAW = { front: 0, q: 0.72, side: Math.PI / 2, back: Math.PI, desk: 2.3, face: 0.22 };
function frame(view = state.view) {
  state.view = view; let [w, h] = state.box, cy = state.center; const single = state.char !== 'all' && state.char !== 'meeting';
  if (view === 'face' && single) { const pet = state.char === 'pet', S = chars[state.char].S || 1; w = pet ? 0.5 : 0.78; h = pet ? 0.45 : 0.8; cy = pet ? 0.2 : (state.action === 'type' ? 1.0 : 1.2) * S; }
  const asp = camera.aspect, tf = Math.tan(camera.fov * Math.PI / 360);
  const dist = Math.max(h / 2 / tf, w / 2 / (tf * asp)) * 1.05 + 0.4, yaw = YAW[view] ?? 0, pitch = view === 'face' ? 0.06 : state.char === 'meeting' ? 0.34 : state.char === 'all' && narrow() ? 0.42 : 0.14;
  controls.target.set(0, cy, 0);
  camera.position.set(Math.sin(yaw) * Math.cos(pitch) * dist, cy + Math.sin(pitch) * dist, Math.cos(yaw) * Math.cos(pitch) * dist);
  controls.update();
}
function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }

// 介面
const chip = (box, list, get, set) => { const el = document.getElementById(box); el.innerHTML = ''; for (const [v, label, sub] of list) { const b = document.createElement('button'); b.innerHTML = label + (sub ? `<small>${sub}</small>` : ''); b.dataset.v = v; b.onclick = () => { set(v); sync(); }; el.appendChild(b); } el._get = get; };
function sync() { for (const id of ['chars', 'acts', 'exprs', 'views']) { const el = document.getElementById(id); for (const b of el.children) b.classList.toggle('on', b.dataset.v === el._get()); } }
chip('chars', [['all', '全員'], ['meeting', '會議場景'], ...IDS.map((id) => [id, SPECS[id].name, SPECS[id].kind])], () => state.char, (v) => { state.char = v; layout(); frame(v === 'meeting' ? 'front' : state.view === 'face' && (v === 'all') ? 'front' : state.view); });
chip('acts', ACTION_LIST, () => state.action, (v) => { state.action = v; if (state.char === 'meeting') state.char = 'all'; layout(); frame(); });
chip('exprs', [['auto', '跟著動作'], ['happy', '開心'], ['angry', '生氣'], ['surprised', '驚訝'], ['think', '思考'], ['sad', '難過'], ['smug', '得意']], () => state.expr, (v) => { state.expr = v; layout(); });
chip('views', [['front', '正面'], ['q', '斜側'], ['side', '側面'], ['back', '背面'], ['face', '臉部特寫'], ['desk', '看螢幕']], () => state.view, (v) => { if (v === 'face' && (state.char === 'all' || state.char === 'meeting')) { state.char = 'kai'; layout(); } frame(v); });

let last = performance.now();
function step(dt, draw = true) {
  let speed = 0;
  for (const id of IDS) { const ch = chars[id]; if (!ch.root.visible) continue; anims[id].update(dt); speed = Math.max(speed, anims[id].out.speed * (ch.pet && state.char !== 'pet' ? 0 : 1));
    const b = blobs[id]; b.visible = true; ch.rig.getWorldPosition(b.position); const hgt = b.position.y; b.position.y = 0.004; const s = (ch.pet ? 0.62 : ch.spec.ghost ? 0.6 : 0.72) * (ch.props.desk?.visible ? 1.6 : 1) / (1 + hgt * 0.9); b.scale.set(s, s, 1); b.material.opacity = ch.spec.ghost ? 0.6 : 1; }
  for (const id of IDS) if (!chars[id].root.visible) blobs[id].visible = false;
  dotT.offset.y += speed * dt / (12 / 9) * (state.char === 'meeting' ? 0 : 1);
  if (draw) { controls.update(); renderer.render(scene, camera); }
}
function loop(now) { const dt = Math.min(0.05, (now - last) / 1000); last = now; if (!paused) step(dt); requestAnimationFrame(loop); }
let paused = qs.get('auto') === '0';
cv.addEventListener('pointerdown', () => document.getElementById('hint').classList.add('off'), { once: true });
window.addEventListener('resize', () => { resize(); layout(); frame(); });
resize(); layout(); frame('front'); sync(); step(0.016);
document.getElementById('loading').classList.add('off');
requestAnimationFrame(loop);

// 給自動截圖用
window.OFFICE = {
  set(o) { Object.assign(state, o); layout(); frame(o.view || state.view); sync(); },
  step(sec, dt = 1 / 60) { const n = Math.round(sec / dt); for (let i = 0; i < n; i++) step(dt, i === n - 1); },
  pause(v) { paused = v; }, state, chars, anims, camera, controls, renderer, scene, ready: true,
};
