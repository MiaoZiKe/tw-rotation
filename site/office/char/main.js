// 糰糰 v2 展示頁：可旋轉、四個固定視角、表情、最小動作示範、線框、剪影、新舊並排。
import * as THREE from 'three';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { Stage, BG } from './stage.js';
import { loadMochi, MochiChar } from './mochi.js';
import { EXPR_LIST } from './facerig.js';
import { PRESETS, PRESET_IDS } from '../play/materials.js';
import { Character } from '../play/character.js';
import { stubWorld, stubFx } from '../play/lite.js';
import { Field } from './field.js';
import { makeQA } from './qa.js';

const $ = (s) => document.querySelector(s), qs = new URLSearchParams(location.search), V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const view = $('#view');
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: qs.has('shot') });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2)); view.appendChild(renderer.domElement);
const stage = new Stage(renderer), scene = stage.scene;
const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 40);
const ctl = new OrbitControls(camera, renderer.domElement); ctl.enableDamping = true; ctl.dampingFactor = 0.12; ctl.minDistance = 0.8; ctl.maxDistance = 9; ctl.maxPolarAngle = Math.PI * 0.52; ctl.target.set(0, 0.36, 0);

const S = { ch: null, contact: null, old: null, lod: +(qs.get('lod') || 0), preset: qs.get('mat') || 'fur', cmp: false, play: false, focus: new V3(0, 0.36, 0), sil: false, wire: false, paused: false, track: false, act: null, tween: null, mouse: { x: 0, y: 0, on: false }, time: 0 };
let asset = null;

// ── 角色
async function buildNew() {
  if (S.ch) { stage.removeContact(S.contact); S.ch.dispose(); }
  asset = await loadMochi({ lod: S.lod });
  const prev = S.ch; S.ch = new MochiChar(asset, { preset: S.preset }); scene.add(S.ch.root);
  S.contact = stage.addContact(S.ch); applyWire();
  if (prev && prev.face && S.ch.face) S.ch.face.set(prev.face.name);
  if (S.lod === 2) S.contact.base = 1;
  if (S.field) { await S.field.attach(S.ch); S.field.ctl.look = null; }
  layout();
}
// 舊版（球體拼接）放在自己的場景，燈光與鏡頭跟新版完全一致，左右各畫半個畫面（畫面對比最公平，也不互相干擾）
const oldScene = new THREE.Scene(); oldScene.background = scene.background;
{ const L = (l) => { const c = l.clone(); c.castShadow = false; return c; }; oldScene.add(L(stage.hemi), L(stage.key), L(stage.rim), L(stage.fill)); oldScene.environment = null; }
function buildOld() {
  if (S.old) return S.old;
  const space = new THREE.Group(); oldScene.add(space);
  const c = new Character({ species: 'mochi', pal: 0, acc: [] }, oldScene, stubWorld(), stubFx, { space }); c.pos.set(0, 0, 0); c.yaw = 0; c.lookT = 1e9; c.face.blinkT = 1e9; c.idleT = 0;
  c.feet.forEach(f => { c.footHome(f, f.p); f.from.copy(f.p); f.m.position.copy(f.p); });
  for (let i = 0; i < 40; i++) { c.step(1 / 60, { mx: 0, mz: 0, run: false, jump: false }); c.animate(1 / 60, { look: null, cam: camera.position }); }
  const blob = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: stage.texBody, transparent: true, depthWrite: false, opacity: 0.3 })); blob.rotation.x = -Math.PI / 2; blob.position.y = 0.002; blob.scale.set(1.3, 1.2, 1); oldScene.add(blob);
  const disc = stage.scene.children.find(o => o.geometry && o.geometry.type === 'PlaneGeometry' && o.material.type === 'MeshBasicMaterial' && o.position.y < 0); if (disc) oldScene.add(disc.clone());
  S.old = c; return c;
}
function layout() { $('#tag').classList.toggle('on', S.cmp); if (S.ch && !S.play) S.ch.root.position.x = 0; }

// ── 視角
const VIEWS = { front: ['正面', 0], side: ['側面', Math.PI / 2], back: ['背面', Math.PI], q45: ['45 度', Math.PI / 4] };
function setView(name, instant) {
  const az = VIEWS[name][1], d = camDist(), el = S.play ? 0.42 : 0.12, tg = S.focus.clone();
  const to = new V3(tg.x + Math.sin(az) * d * Math.cos(el), 0.36 + Math.sin(el) * d, tg.z + Math.cos(az) * d * Math.cos(el));
  ctl.minPolarAngle = 0;
  if (instant) { camera.position.copy(to); ctl.target.copy(tg); ctl.update(); } else S.tween = { t: 0, a: camera.position.clone(), b: to };
  document.querySelectorAll('#gView button').forEach(b => b.classList.toggle('on', b.dataset.v === name)); S.view = name;
}

// ── 動作示範（最小驅動：證明骨頭＋形態鍵變形不裂不穿；完整動作與狀態機是第三階段）
const ease = (t) => t * t * (3 - 2 * t);
const ACTS = {
  wave: { dur: 2.2, fn(c, t, u) { const e = Math.min(ease(Math.min(1, t / 0.35)), ease(Math.min(1, (2.2 - t) / 0.35))); c.rot('arm.L', 0, -0.55 * e, 1.0 * e); c.rot('hand.L', 0, 0, 0.5 * Math.sin(t * 15) * e); c.rot('head', 0, 0, -0.1 * e); c.face?.set(e > 0.4 ? 'smile' : 'neutral'); } },
  squash: { dur: 1.5, fn(c, t) { const p = t < 0.35 ? ease(t / 0.35) : Math.exp(-(t - 0.35) * 3.4) * Math.cos((t - 0.35) * 13); const w = clamp(p, -0.25, 1); c.morph('land', clamp(w, 0, 1) * 0.9); c.morph('stretch', clamp(-w, 0, 1) * 0.6); c.rot('ear.L', 0, 0, 0.35 * (w - (t < 0.35 ? 0 : 0))); c.rot('ear.R', 0, 0, -0.35 * w); c.face?.set(t < 0.4 ? 'sad' : 'surprised'); } },
  stretch: { dur: 1.6, fn(c, t) { const w = t < 0.4 ? ease(t / 0.4) : Math.exp(-(t - 0.4) * 3) * Math.cos((t - 0.4) * 11); c.morph('stretch', clamp(w, 0, 1)); c.morph('squash', clamp(-w, 0, 1) * 0.7); c.rot('ear.L', 0, 0, -0.3 * w); c.rot('ear.R', 0, 0, 0.3 * w); c.rot('arm.L', 0, 0, 0.8 * w); c.rot('arm.R', 0, 0, -0.8 * w); c.face?.set('surprised'); } },
  turn: { dur: 2.6, fn(c, t) { const y = Math.sin(t / 2.6 * Math.PI * 2) * 0.62; c.rot('head', 0, y, 0); c.rot('spine', 0, y * 0.3, 0); c.rot('tail', 0, 0, y * 0.5); } },
  hop: { dur: 1.0, fn(c, t) { const y = 0.55 * 4 * t * (1 - t) * (t < 1 ? 1 : 0); c.rot('root', 0, 0, 0); c.move('root', 0, y, 0); const pre = t < 0.12 ? ease(t / 0.12) : 0, post = t > 0.86 ? ease((t - 0.86) / 0.14) : 0; c.morph('land', Math.max(pre * 0.6, post * 0.8 * (1 - (t - 0.86) * 0)) * (t > 0.93 ? (1 - (t - 0.93) / 0.07) : 1)); c.morph('stretch', y > 0.05 ? 0.5 : 0); c.rot('ear.L', 0, 0, -0.5 * Math.sin(t * Math.PI)); c.rot('ear.R', 0, 0, 0.5 * Math.sin(t * Math.PI)); } },
};
function playAct(name) { if (S.act) endAct(); S.act = { name, t: 0, ...ACTS[name] }; document.querySelectorAll('#gAct button[data-a]').forEach(b => b.classList.toggle('on', b.dataset.a === name)); }
function endAct() { S.act = null; if (S.ch) { S.ch.resetPose(); } document.querySelectorAll('#gAct button[data-a]').forEach(b => b.classList.remove('on')); }

function idle(c, t) {
  const w = 0.5 + 0.5 * Math.sin(t * 2 * Math.PI / 3.4);
  c.morph('breath', w * 0.9); c.move('head', 0, 0.004 * Math.sin(t * 2 * Math.PI / 3.4 + 0.5), 0);
  c.rot('ear.L', 0, 0, 0.04 * Math.sin(t * 1.3)); c.rot('ear.R', 0, 0, -0.04 * Math.sin(t * 1.3 + 1.1)); c.rot('tail', 0, 0.12 * Math.sin(t * 2.1), 0);
}
function trackGaze(c) {
  const f = c.face; if (!f) return;
  if (!S.track || !S.mouse.on) { f.lookAt(0, 0); c.rot('head', ...[0, 0, 0]); return; }
  // 滑鼠射線與「角色前方、面向鏡頭」的平面相交，換成頭部座標的角度
  const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2(S.mouse.x, S.mouse.y), camera);
  const head = c.boneWorld('head').add(new V3(0, 0.0, 0)); const hw = head.clone().applyMatrix4(c.root.matrixWorld);
  const nrm = camera.getWorldDirection(new V3()).negate(); const pl = new THREE.Plane().setFromNormalAndCoplanarPoint(nrm, hw), hit = new V3();
  if (!ray.ray.intersectPlane(pl, hit)) return;
  const loc = c.root.worldToLocal(hit.clone()).sub(new V3(0, 0.31, 0)); const yaw = Math.atan2(loc.x, Math.max(0.2, loc.z + 0.6)), pit = Math.atan2(loc.y, Math.hypot(loc.x, Math.max(0.2, loc.z + 0.6)));
  f.lookAt(clamp(yaw, -0.9, 0.9) * 0.4, clamp(pit, -0.6, 0.6) * 0.4);
  c._gy = (c._gy ?? 0) + (clamp(yaw, -0.9, 0.9) - (c._gy ?? 0)) * 0.12; c._gp = (c._gp ?? 0) + (clamp(pit, -0.6, 0.6) - (c._gp ?? 0)) * 0.12;
  c.rot('head', -c._gp * 0.25, c._gy * 0.3, 0); c.rot('spine', 0, c._gy * 0.1, 0);
}

// ── 顯示切換
// 線框／剪影：用覆蓋材質畫整個場景（深褐線框或純黑剪影），並收起地面與柔影
let oldDisc = null;
function applyMode() {
  const om = S.sil ? new THREE.MeshBasicMaterial({ color: 0x111111 }) : S.wire ? new THREE.MeshBasicMaterial({ color: 0x6a4636, wireframe: true }) : null;
  scene.overrideMaterial = om; oldScene.overrideMaterial = om;
  const flat = S.sil || S.wire;
  scene.background.set(S.sil ? 0xffffff : BG); stage.floor.visible = !flat; stage.disc.visible = !flat;
  for (const o of stage.shadows) for (const m of [o.body, o.belly, ...o.feet]) m.visible = !flat;
  oldScene.children.forEach(o => { if (o.geometry && o.geometry.type === 'PlaneGeometry') o.visible = !flat; });
}
const applyWire = applyMode, applySil = applyMode;

// ── 介面
const gv = $('#gView'); for (const [k, [zh]] of Object.entries(VIEWS)) { const b = document.createElement('button'); b.textContent = zh; b.dataset.v = k; b.onclick = () => setView(k); gv.appendChild(b); }
const ge = $('#gExpr'); for (const [k, zh] of EXPR_LIST) { const b = document.createElement('button'); b.textContent = zh; b.dataset.e = k; b.onclick = () => { S.ch.face?.set(k); ge.querySelectorAll('button[data-e]').forEach(x => x.classList.toggle('on', x === b)); }; ge.appendChild(b); }
{ const b = document.createElement('button'); b.textContent = '眨眼一下'; b.onclick = () => S.ch.face?.blinkNow(); ge.appendChild(b);
  const t = document.createElement('button'); t.textContent = '視線追蹤游標'; t.id = 'btnTrack'; t.onclick = () => { S.track = !S.track; t.classList.toggle('on', S.track); }; ge.appendChild(t); }
const ga = $('#gAct'); for (const [k, zh] of [['wave', '揮手'], ['squash', '被壓扁回彈'], ['stretch', '拉長'], ['turn', '轉頭'], ['hop', '小跳']]) { const b = document.createElement('button'); b.textContent = zh; b.dataset.a = k; b.onclick = () => playAct(k); ga.appendChild(b); }
{ const b = document.createElement('button'); b.textContent = '動態'; b.id = 'btnMotion'; b.className = 'on'; b.setAttribute('aria-pressed', 'true'); b.onclick = () => { S.paused = !S.paused; b.textContent = S.paused ? '靜止' : '動態'; b.classList.toggle('on', !S.paused); b.setAttribute('aria-pressed', String(!S.paused)); }; ga.appendChild(b); }
const gs = $('#gShow');
const tog = (label, id, fn) => { const b = document.createElement('button'); b.textContent = label; b.id = id; b.onclick = () => { const on = fn(); b.classList.toggle('on', on); }; gs.appendChild(b); return b; };
tog('線框', 'btnWire', () => (S.wire = !S.wire, applyWire(), S.wire));
tog('新舊並排', 'btnCmp', () => { S.cmp = !S.cmp; if (S.cmp) buildOld(); layout(); applyOffset(); setView(S.view || 'front'); return S.cmp; });
tog('黑色剪影', 'btnSil', () => (S.sil = !S.sil, applySil(), S.sil));
const sm = $('#selMat'); for (const id of PRESET_IDS) { const o = document.createElement('option'); o.value = id; o.textContent = PRESETS[id].zh; sm.appendChild(o); } sm.value = S.preset; sm.onchange = () => { S.preset = sm.value; S.ch.setPreset(S.preset); applyWire(); };
const sl = $('#selLod'); sl.value = String(S.lod); sl.onchange = async () => { S.lod = +sl.value; await buildNew(); };

{ const hd = $('header'), b = document.createElement('button'); b.textContent = '控制面板'; b.id = 'btnPanel'; b.style.marginLeft = 'auto'; b.setAttribute('aria-pressed', 'true'); b.className = 'on';
  const set = (on) => { $('#panel').style.display = on ? '' : 'none'; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); requestAnimationFrame(() => { applyOffset(); }); };
  b.onclick = () => set($('#panel').style.display === 'none'); hd.appendChild(b); if (matchMedia('(max-width:640px)').matches) set(false); }
addEventListener('pointermove', (e) => { const r = renderer.domElement.getBoundingClientRect(); S.mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1; S.mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1; S.mouse.on = true; });
// 鏡頭距離依畫面寬高比調整（直式手機要拉遠才裝得下），並把角色往上推，讓出下方控制面板的位置
function camDist() { const a = (view.clientWidth || 1) / (view.clientHeight || 1); return Math.max(S.play ? 5.4 : S.cmp ? 4.3 : 3.4, (S.cmp ? 1.5 : 0.78) / (Math.tan(14 * Math.PI / 180) * a)); }
function applyOffset() {
  const w = view.clientWidth, h = view.clientHeight, pn = $('#panel'), ph = pn.style.display === 'none' ? 0 : Math.min(pn.getBoundingClientRect().height, h * 0.55);
  if (S.cmp) { camera.clearViewOffset(); return; }
  camera.setViewOffset(w, h, 0, Math.round(ph / 2), w, h);
}
function resize() { const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); applyOffset(); if (S.view) setView(S.view, true); }
addEventListener('resize', resize);


// ── 走動小場地（第三階段）：點地面走過去、雙擊跑、WASD／方向鍵移動、Shift 跑、Space 跳、點凳子坐下、按住頭頂摸頭
S.keys = new Set(); S.keyMag = 0; S.runMode = false; S.dragMode = false; S.drag = null; S.click = null; S.devOn = false; S.grabbed = false;
async function enablePlay(on) {
  if (on === S.play) return;
  S.play = on; $('#btnPlay').classList.toggle('on', on); $('#btnPlay').setAttribute('aria-pressed', String(on)); $('#playHint').hidden = !on;
  if (on) {
    if (S.cmp) { S.cmp = false; $('#btnCmp').classList.remove('on'); layout(); applyOffset(); }
    endAct(); if (!S.field) { S.field = new Field(scene, stage); }
    S.field.setVisible(true); await S.field.attach(S.ch, { x: 0, z: 0.5, yaw: 0 });
    const k = stage.key; k.shadow.camera.left = -3.4; k.shadow.camera.right = 3.4; k.shadow.camera.top = 3.4; k.shadow.camera.bottom = -3.4; k.shadow.camera.far = 14; k.shadow.camera.updateProjectionMatrix(); k.shadow.mapSize.set(2048, 2048); k.shadow.map?.dispose(); k.shadow.map = null; k.shadow.radius = 10;
    S.focus.set(0, 0.36, 0.5); setView(S.view || 'front', true);
  } else {
    if (S.field) S.field.setVisible(false);
    const k = stage.key; k.position.set(1.7, 5.2, 2.6); k.target.position.set(0, 0, 0); k.shadow.camera.left = -1.4; k.shadow.camera.right = 1.4; k.shadow.camera.top = 1.4; k.shadow.camera.bottom = -1.4; k.shadow.mapSize.set(1024, 1024); k.shadow.map?.dispose(); k.shadow.map = null; k.shadow.radius = 14;
    S.focus.set(0, 0.36, 0); S.ch.resetPose(); S.ch.root.position.set(0, 0, 0); S.ch.root.rotation.y = 0; setView(S.view || 'front', true); S.ch.face?.set('neutral');
  }
  for (const b of document.querySelectorAll('#gPlay button[data-p]')) b.disabled = !on && b.dataset.p !== 'play' && b.dataset.p !== 'dev';
}
function camForward() { const f = new V3(); camera.getWorldDirection(f); f.y = 0; return f.lengthSq() < 1e-6 ? new V3(0, 0, -1) : f.normalize(); }
function trackPlay(dt, cc) {
  // 鍵盤：相機相對方向
  const k = S.keys, up = (k.has('w') || k.has('arrowup')) - (k.has('s') || k.has('arrowdown')), rt = (k.has('d') || k.has('arrowright')) - (k.has('a') || k.has('arrowleft'));
  const f = camForward(), r = new V3(-f.z, 0, f.x);
  if (up || rt) { const x = f.x * up + r.x * rt, z = f.z * up + r.z * rt; cc.setMove(x, z, 1, k.has('shift') || S.runMode); S.keyMag = 1; }
  else if (S.keyMag) { cc.setMove(0, 0, 0); S.keyMag = 0; }
  else if (S.drag && S.drag.on) { const d = S.drag, dx = d.x - d.x0, dy = d.y - d.y0, len = Math.hypot(dx, dy); if (len > 14) cc.setMove(f.x * -dy + r.x * dx, f.z * -dy + r.z * dx, clamp(len / 70, 0.3, 1), len > 120 || S.runMode); else cc.setMove(0, 0, 0); }
  if (S.mouse.on && S.track) { const rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(S.mouse.x, S.mouse.y), camera); const h = new V3(); if (rc.ray.intersectPlane(new THREE.Plane(new V3(0, 1, 0), -0.5), h)) cc.lookAt(h); } else cc.lookAt(null);
}
function followCam(dt, cc) {
  if (S.noFollow) return;
  const b = cc.body, tg = new V3(b.x, 0.36, b.z), d = tg.clone().sub(ctl.target); d.y = 0; d.multiplyScalar(1 - Math.exp(-dt * 4)); ctl.target.add(d); camera.position.add(d); S.focus.set(ctl.target.x, 0.36, ctl.target.z);
  const kk = stage.key; kk.position.set(ctl.target.x + 1.7, 5.2, ctl.target.z + 2.6); kk.target.position.set(ctl.target.x, 0, ctl.target.z); kk.target.updateMatrixWorld();
}
const gp = $('#gPlay');
const pbtn = (label, id, p, fn, opt = {}) => { const b = document.createElement('button'); b.textContent = label; b.id = id; b.dataset.p = p; b.onclick = fn; if (opt.hold) { const dn = (e) => { e.preventDefault(); opt.hold(true); }, up = () => opt.hold(false); b.addEventListener('pointerdown', dn); addEventListener('pointerup', up); b.addEventListener('pointercancel', up); } gp.appendChild(b); return b; };
const cc = () => S.field?.ctl;
pbtn('場地模式', 'btnPlay', 'play', () => enablePlay(!S.play)); $('#btnPlay').setAttribute('aria-pressed', 'false');
pbtn('跳', 'btnJump', 'jump', () => cc()?.jump());
pbtn('坐下／起身', 'btnSit', 'sit', () => { const c = cc(); if (!c) return; if (c.state === 'sit') c.standUp(); else c.sitOn('stool'); });
pbtn('摸頭（按住）', 'btnPet', 'pet', () => {}, { hold: (on) => { const c = cc(); if (!c || !S.play) return; if (on) c.petStart(); else c.petEnd(); } });
pbtn('睡覺／起床', 'btnSleep', 'sleep', () => { const c = cc(); if (!c) return; if (c.state === 'sleep') c.wake(); else c.sleep(); });
pbtn('抓起／放下', 'btnGrab', 'grab', () => { const c = cc(); if (!c) return; if (c.state === 'held') c.release(0, 0, 0); else c.grab(c.body.x, 1.0, c.body.z); });
pbtn('丟出去', 'btnThrow', 'throw', () => { const c = cc(); if (!c) return; const f = camForward(); c.throwAt(f.x * 4.2, 4.6, f.z * 4.2); });
for (const [k, zh] of [['hit', '受擊'], ['happy', '開心'], ['angry', '生氣'], ['sad', '難過']]) pbtn(zh, 'btn_' + k, k, () => cc()?.trigger(k));
pbtn('停下回待機', 'btnStop', 'stop', () => { const c = cc(); if (!c) return; c.stop(); c.interrupt(); });
pbtn('跑（切換）', 'btnRun', 'run', () => { S.runMode = !S.runMode; $('#btnRun').classList.toggle('on', S.runMode); });
pbtn('拖曳跑（切換）', 'btnDrag', 'drag', () => { S.dragMode = !S.dragMode; $('#btnDrag').classList.toggle('on', S.dragMode); });
pbtn('開發面板', 'btnDev', 'dev', () => { S.devOn = !S.devOn; $('#dev').hidden = !S.devOn; $('#btnDev').classList.toggle('on', S.devOn); });
for (const b of gp.querySelectorAll('button[data-p]')) if (b.dataset.p !== 'play' && b.dataset.p !== 'dev') b.disabled = true;
// 指標：點地面走過去（雙擊跑）、點凳子坐下、按住頭頂摸頭、拖曳跑
view.addEventListener('pointerdown', (e) => {
  if (!S.play || !cc() || e.button !== 0) return;
  const r = renderer.domElement.getBoundingClientRect(), rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
  const hit = S.field.pick(rc);
  if (hit.kind === 'head') { if (cc().petStart()) { S.petPtr = e.pointerId; e.stopPropagation(); ctl.enabled = false; } return; }
  if (S.dragMode && hit.kind !== 'stool') { S.drag = { on: true, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, id: e.pointerId }; e.stopPropagation(); ctl.enabled = false; return; }
  S.click = { x: e.clientX, y: e.clientY, t: performance.now(), kind: hit.kind, point: hit.point, id: e.pointerId };
}, true);
addEventListener('pointermove', (e) => { if (S.drag && S.drag.on) { S.drag.x = e.clientX; S.drag.y = e.clientY; } });
addEventListener('pointerup', (e) => {
  if (S.petPtr != null) { S.petPtr = null; cc()?.petEnd(); ctl.enabled = true; }
  if (S.drag && S.drag.on) { S.drag.on = false; cc()?.setMove(0, 0, 0); S.drag = null; ctl.enabled = true; }
  const c = S.click; S.click = null; if (!c || !S.play || !cc()) return;
  if (Math.hypot(e.clientX - c.x, e.clientY - c.y) > 6 || performance.now() - c.t > 450) return;
  const now = performance.now(), dbl = S.lastClick && now - S.lastClick.t < 380 && Math.hypot(e.clientX - S.lastClick.x, e.clientY - S.lastClick.y) < 24; S.lastClick = { t: now, x: e.clientX, y: e.clientY };
  if (c.kind === 'stool') { if (cc().state === 'sit') cc().standUp(); else cc().sitOn('stool'); }
  else if (c.kind === 'crate') { cc().walkTo(c.point.x + (cc().body.x < c.point.x ? -0.62 : 0.62), c.point.z, false); }
  else if (c.kind === 'ground') { const H = 2.3 - 0.4; cc().walkTo(clamp(c.point.x, -H, H), clamp(c.point.z, -H, H), dbl || S.runMode); }
});
addEventListener('keydown', (e) => {
  if (!S.play || !cc() || /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName || '')) return;
  const k = e.key.toLowerCase();
  if (k === ' ') { e.preventDefault(); if (!e.repeat) cc().jump(); }
  else if (k === 'e' && !e.repeat) { const c = cc(); if (c.state === 'sit') c.standUp(); else c.sitOn('stool'); }
  else if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'shift'].includes(k)) { if (k.startsWith('arrow')) e.preventDefault(); S.keys.add(k); }
});
addEventListener('keyup', (e) => S.keys.delete(e.key.toLowerCase()));
addEventListener('blur', () => S.keys.clear());
// 開發用小面板（預設收起）
setInterval(() => {
  if (!S.devOn || !cc()) return; const i = cc().info(), f = (v, n = 2) => (+v).toFixed(n);
  $('#devTxt').textContent = `狀態　${i.state}${i.sub ? '／' + i.sub : ''}　（姿勢 ${i.key}）\n速度　${f(i.speed)} m/s　垂直 ${f(i.vy)}\n著地　${i.grounded ? '是' : '否'}　高度 ${f(i.y, 3)} m\n步頻　${f(i.cad)} Hz　步幅 ${f(i.stride, 3)} m\n位置　(${f(i.x)}, ${f(i.z)})　朝向 ${f(i.yaw)}\n表情　${i.expr}　小動作 ${i.micro || '—'}\n衝突 ${i.conflicts}　被拒轉場 ${i.rejects}　丟棄步 ${i.dropped}`;
}, 150);

// ── 主迴圈（頁面切走就停，切回來再開）
let last = performance.now(), raf = 0, frames = 0, acc = 0, fpsT = 0;
function frame(now) {
  raf = requestAnimationFrame(frame); S.frames = (S.frames || 0) + 1;
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (S.tween) { S.tween.t += dt / 0.55; const u = ease(Math.min(1, S.tween.t)); const r = S.tween.a.length() > 0 ? 1 : 1; camera.position.lerpVectors(S.tween.a, S.tween.b, u); if (S.tween.t >= 1) S.tween = null; }
  ctl.update();
  const sdt = S.paused ? 0 : dt; S.time += sdt;
  if (S.ch) {
    const c = S.ch;
    if (S.play && S.field?.ctl) {
      const cc = S.field.ctl; trackPlay(dt, cc); if (!S.paused) cc.update(dt); else c.update(dt, true);
      followCam(dt, cc);
    } else {
    if (!S.paused) {
      if (S.act) { S.act.t += dt; if (S.act.t >= S.act.dur) endAct(); }
      if (!S.act) { c.resetPose(); } else { c.resetPose(); }
      idle(c, S.time); trackGaze(c);
      if (S.act) S.act.fn(c, S.act.t);
    }
    c.update(dt, S.paused);
    }
    stage.updateContact();
  }
  if (S.old && S.cmp && sdt > 0) { S.old.step(sdt, { mx: 0, mz: 0, run: false, jump: false }); S.old.animate(sdt, { look: null, cam: camera.position }); S.old.lookT = 1e9; }
  if (S.cmp && S.old) {
    const W = renderer.domElement.width, H = renderer.domElement.height, hw = Math.floor(W / 2);
    renderer.setScissorTest(true); camera.aspect = hw / H; camera.updateProjectionMatrix();
    renderer.setViewport(0, 0, hw, H); renderer.setScissor(0, 0, hw, H); renderer.render(scene, camera);
    renderer.setViewport(hw, 0, W - hw, H); renderer.setScissor(hw, 0, W - hw, H); renderer.render(oldScene, camera);
    renderer.setScissorTest(false); renderer.setViewport(0, 0, W, H);
  } else { renderer.setScissorTest(false); const w = view.clientWidth, h = view.clientHeight; if (Math.abs(camera.aspect - w / h) > 1e-3) { camera.aspect = w / h; camera.updateProjectionMatrix(); applyOffset(); } renderer.render(scene, camera); }
  frames++; fpsT += dt; if (fpsT > 1) { $('#stat').textContent = `${Math.round(frames / fpsT)} fps｜${renderer.info.render.calls} 繪製呼叫｜${renderer.info.render.triangles} 三角面`; frames = 0; fpsT = 0; }
}
document.addEventListener('visibilitychange', () => { if (document.hidden) { cancelAnimationFrame(raf); raf = 0; } else if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); } });

resize(); await buildNew(); setView(qs.get('view') || 'front', true);
if (qs.has('play')) await enablePlay(true);
if (S.cmp) layout();
raf = requestAnimationFrame(frame);
// 測試與截圖用的對外介面
window.CH = { enablePlay, get field() { return S.field; }, get cc() { return S.field?.ctl; }, THREE, pose(name, t) { const c = S.ch; c.resetPose(); idle(c, 0.5); if (name) ACTS[name].fn(c, t); c.update(0); stage.updateContact(); }, S, stage, scene, camera, renderer, ctl, setView, playAct, endAct, buildNew, buildOld, layout, applyWire, applySil, get ch() { return S.ch; }, frame, mood: (k) => S.ch.face.set(k), setCmp(on) { S.cmp = on; if (on) buildOld(); layout(); applyOffset(); setView(S.view || 'front', true); }, setSil(on) { S.sil = on; applySil(); }, setWire(on) { S.wire = on; applyWire(); } };
window.CH.qa = makeQA(window.CH);
document.title = 'ok'; document.documentElement.dataset.ready = '1';
