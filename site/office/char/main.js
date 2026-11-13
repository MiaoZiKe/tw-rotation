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
import { QAView } from './qaview.js';

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
  const om = S.sil ? new THREE.MeshBasicMaterial({ color: 0x111111 }) : S.wire ? new THREE.MeshBasicMaterial({ color: 0x6a4636, wireframe: true }) : S.norm ? new THREE.MeshNormalMaterial() : null;
  if (scene.overrideMaterial) scene.overrideMaterial.dispose(); scene.overrideMaterial = om; oldScene.overrideMaterial = om;
  const flat = S.sil || S.wire || S.norm; if (S.qav) S.qav.group.visible = !flat && (S.qav.collide || S.qav.contacts); if (S.field) S.field.fx.group.visible = !flat && S.play;
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
S.timeScale = 1; S.stepN = 0; S.keys = new Set(); S.keyMag = 0; S.runMode = false; S.dragMode = false; S.drag = null; S.click = null; S.devOn = false; S.grabbed = false;
async function enablePlay(on) {
  if (on === S.play) return;
  S.play = on; document.body.classList.toggle('play', on); if (!on) document.body.classList.remove('more'); $('#btnPlay').classList.toggle('on', on); $('#btnPlay').setAttribute('aria-pressed', String(on)); $('#playHint').hidden = !on;
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
  requestAnimationFrame(applyOffset);
  for (const b of document.querySelectorAll('#gPlay button[data-p]')) b.disabled = !on && !['play', 'dev', 'more', 'qa'].includes(b.dataset.p);
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
pbtn('跑（切換）', 'btnRun', 'run', () => { S.runMode = !S.runMode; $('#btnRun').classList.toggle('on', S.runMode); }).classList.add('adv');
pbtn('拖曳跑（切換）', 'btnDrag', 'drag', () => { S.dragMode = !S.dragMode; $('#btnDrag').classList.toggle('on', S.dragMode); }).classList.add('adv');
pbtn('開發面板', 'btnDev', 'dev', () => { S.devOn = !S.devOn; $('#dev').hidden = !S.devOn; $('#btnDev').classList.toggle('on', S.devOn); });
pbtn('檢查模式', 'btnQA', 'qa', () => { qa.hidden = !qa.hidden; $('#btnQA').classList.toggle('on', !qa.hidden); $('#btnQA').setAttribute('aria-pressed', String(!qa.hidden)); });
{ const mb = document.createElement('button'); mb.id = 'btnMore'; mb.textContent = '更多選項'; mb.setAttribute('aria-pressed', 'false'); mb.style.marginLeft = '6px';   // 放在標題列（場地模式才顯示）：精簡動作列保持乾淨，要看視角／表情／材質再展開
  mb.onclick = () => { const on = document.body.classList.toggle('more'); mb.classList.toggle('on', on); mb.setAttribute('aria-pressed', String(on)); requestAnimationFrame(applyOffset); };
  $('#btnPanel').after(mb); }
for (const b of gp.querySelectorAll('button[data-p]')) if (!['play', 'dev', 'more', 'qa'].includes(b.dataset.p)) b.disabled = true;
// 指標：點地面走過去（雙擊跑）、點凳子坐下、按住頭頂摸頭、拖曳跑
view.addEventListener('pointerdown', (e) => {
  if (!S.play || !cc() || e.button !== 0) return;
  const r = renderer.domElement.getBoundingClientRect(), rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
  const hit = S.field.pick(rc);
  if ((hit.kind === 'head' || hit.kind === 'body') && !S.dragMode) {   // 按住角色：不動＝摸頭（頭）；拖曳超過幾個像素＝抓起、甩出去放手＝拋擲
    S.gp = { id: e.pointerId, x0: e.clientX, y0: e.clientY, kind: hit.kind, point: hit.point.clone(), grabbed: false, samples: [] };
    if (hit.kind === 'head' && cc().petStart()) S.petPtr = e.pointerId;
    e.stopPropagation(); ctl.enabled = false; try { view.setPointerCapture(e.pointerId); } catch (_) {} return;
  }
  if (S.dragMode && hit.kind !== 'stool') { S.drag = { on: true, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, id: e.pointerId }; e.stopPropagation(); ctl.enabled = false; return; }
  S.click = { x: e.clientX, y: e.clientY, t: performance.now(), kind: hit.kind, point: hit.point, id: e.pointerId };
}, true);
addEventListener('pointermove', (e) => {
  if (S.drag && S.drag.on) { S.drag.x = e.clientX; S.drag.y = e.clientY; }
  const g = S.gp; if (!g || e.pointerId !== g.id || !S.play || !cc()) return;
  if (!g.grabbed && Math.hypot(e.clientX - g.x0, e.clientY - g.y0) > (e.pointerType === 'touch' ? 12 : 8)) beginGrab(g);
  if (g.grabbed) { g.x = e.clientX; g.y = e.clientY; const o = holdOrigin(g); if (o) { cc().grab(o.x, o.y, o.z, g.pivot); g.samples.push({ t: e.timeStamp, x: o.x, y: o.y, z: o.z }); while (g.samples.length > 12) g.samples.shift(); } }
});
// ── 抓起與拋出：抓點＝按下的那個點（在角色身上）；抓點跟著指標走在「面向鏡頭的垂直面」上，放手時依最近 ~100 ms 的指標速度拋出
function beginGrab(g) {
  const c = cc(), root = c.ch.root; S.petPtr = null; c.petEnd(); root.updateMatrixWorld(true);
  const lp = root.worldToLocal(g.point.clone()); lp.y = clamp(lp.y, 0.12, 0.72); g.pivot = { x: lp.x, y: lp.y, z: lp.z };
  const f = camForward(); g.plane = new THREE.Plane().setFromNormalAndCoplanarPoint(new V3(-f.x, 0, -f.z), g.point); g.x = g.x0; g.y = g.y0;
  g.grabbed = true; g.samples = [];
  const o = holdOrigin(g); if (o) c.grab(o.x, o.y, o.z, g.pivot); else c.grab(c.body.x, c.body.y + 0.2, c.body.z, g.pivot);
}
function holdOrigin(g) {
  const r = renderer.domElement.getBoundingClientRect(), rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(((g.x - r.left) / r.width) * 2 - 1, -((g.y - r.top) / r.height) * 2 + 1), camera);
  const q = new V3(); if (!rc.ray.intersectPlane(g.plane, q)) return null;
  const yaw = cc().body.yaw, c = Math.cos(yaw), s = Math.sin(yaw), p = g.pivot, ox = p.x * c + p.z * s, oz = -p.x * s + p.z * c, H = 2.3 - cc().shape.R;
  return { x: clamp(q.x - ox, -H, H), y: clamp(q.y - p.y, 0, 1.9), z: clamp(q.z - oz, -H, H) };
}
function endGrab(e, cancel) {
  const g = S.gp; if (!g) return; S.gp = null; ctl.enabled = true; try { view.releasePointerCapture(g.id); } catch (_) {}
  if (!g.grabbed) return false;
  const c = cc(); if (!c) return true; const now = e.timeStamp, sm = g.samples.filter(q => now - q.t < 110); let v = { x: 0, y: 0, z: 0 };
  if (!cancel && sm.length >= 2) { const a = sm[0], b = sm[sm.length - 1], dt = Math.max(0.03, (b.t - a.t) / 1000); v = { x: (b.x - a.x) / dt, y: (b.y - a.y) / dt, z: (b.z - a.z) / dt }; }
  const sp = Math.hypot(v.x, v.y, v.z); if (!Number.isFinite(sp)) v = { x: 0, y: 0, z: 0 }; else if (sp > 12) { const k = 12 / sp; v = { x: v.x * k, y: v.y * k, z: v.z * k }; }
  S.lastRelease = { ...v, speed: Math.hypot(v.x, v.y, v.z), n: sm.length }; c.release(v.x, v.y, v.z); return true;
}
addEventListener('pointercancel', (e) => { if (S.gp && e.pointerId === S.gp.id) { if (S.petPtr != null) { S.petPtr = null; cc()?.petEnd(); } endGrab(e, true); } });
addEventListener('pointerup', (e) => {
  if (S.petPtr != null) { S.petPtr = null; cc()?.petEnd(); ctl.enabled = true; }
  if (S.gp && e.pointerId === S.gp.id) { endGrab(e, false); return; }
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
// ── 檢查模式（開發用 Character QA）：鏡頭視角、線框／法線、碰撞形狀、接觸點與接地、各動作單獨播放、慢速、暫停與逐格、狀態與速度、新舊對照、截圖
const qa = $('#qa'); S.qav = null;
function qbtn(parent, label, id, fn, tip) { const b = document.createElement('button'); b.textContent = label; if (id) b.id = id; if (tip) b.title = tip; b.onclick = () => fn(b); parent.appendChild(b); return b; }
function qgrp(title) { const g = document.createElement('div'); g.className = 'grp'; g.innerHTML = '<b>' + title + '</b><div class="row"></div>'; qa.appendChild(g); return g.querySelector('.row'); }
{
  const h = document.createElement('div'); h.className = 'qh'; h.innerHTML = '<b>檢查模式</b><span>開發用・不影響一般使用</span>'; qa.appendChild(h);
  const rv = qgrp('鏡頭'); for (const [k, [zh]] of Object.entries(VIEWS)) qbtn(rv, zh, 'qv_' + k, () => setView(k));
  const rs = qgrp('顯示'); const tg = (label, id, get, set) => qbtn(rs, label, id, (b) => { const on = !get(); set(on); b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
  tg('線框', 'qWire', () => S.wire, (on) => { S.wire = on; if (on) S.norm = false, $('#qNorm').classList.remove('on'); applyMode(); });
  tg('法線', 'qNorm', () => S.norm, (on) => { S.norm = on; if (on) S.wire = false, $('#qWire').classList.remove('on'); applyMode(); });
  tg('碰撞形狀', 'qCollide', () => S.qav?.collide, (on) => { ensureQav().setCollide(on); applyMode(); });
  tg('接觸點與接地', 'qContacts', () => S.qav?.contacts, (on) => { ensureQav().setContacts(on); applyMode(); });
  tg('狀態與速度', 'qInfo', () => !$('#qTxt').hidden, (on) => { $('#qTxt').hidden = !on; });
  const rt = qgrp('播放速度'); for (const [k, zh] of [[1, '1×'], [0.5, '0.5×'], [0.25, '0.25×']]) qbtn(rt, zh, 'qs_' + k, (b) => { S.timeScale = k; rt.querySelectorAll('button[data-k]').forEach(x => x.classList.toggle('on', x === b)); }).dataset.k = k;
  rt.querySelector('[data-k="1"]').classList.add('on');
  qbtn(rt, '暫停', 'qPause', () => setPaused(!S.paused)); qbtn(rt, '逐格 ▶|', 'qStep', () => { if (!S.paused) setPaused(true); S.stepN++; }, '暫停時前進 1/60 秒');
  const ra = qgrp('各動作單獨播放'); for (const [k, zh] of [['idle', '待機'], ['walk', '走'], ['run', '跑'], ['jump', '跳'], ['sit', '坐下'], ['sleep', '睡覺'], ['grab', '抓起'], ['throw', '拋出'], ['hit', '受擊'], ['happy', '開心'], ['angry', '生氣'], ['sad', '難過']]) qbtn(ra, zh, 'qa_' + k, () => qaPlay(k));
  const rx = qgrp('工具'); qbtn(rx, '新舊對照', 'qCmp', () => { if (S.play) enablePlay(false); document.getElementById('btnCmp').click(); }); qbtn(rx, '截圖輸出', 'qShot', () => { const u = shotPNG(); const a = document.createElement('a'); a.href = u; a.download = `糰糰_${cc()?.state || S.view}_${Date.now()}.png`; a.click(); });
  const tx = document.createElement('pre'); tx.id = 'qTxt'; tx.hidden = true; qa.appendChild(tx);
}
function ensureQav() { if (!S.qav) S.qav = new QAView(scene); return S.qav; }
function setPaused(p) { S.paused = p; const b = $('#btnMotion'); b.textContent = p ? '靜止' : '動態'; b.classList.toggle('on', !p); b.setAttribute('aria-pressed', String(!p)); $('#qPause').classList.toggle('on', p); $('#qPause').textContent = p ? '繼續' : '暫停'; }
$('#btnMotion').addEventListener('click', () => { $('#qPause').classList.toggle('on', S.paused); $('#qPause').textContent = S.paused ? '繼續' : '暫停'; });
function shotPNG() { renderer.render(scene, camera); return renderer.domElement.toDataURL('image/png'); }
async function qaPlay(name) {
  if (!S.play) await enablePlay(true); const c = cc(); if (!c) return false; setPaused(false); c.life = false; S.runMode = false;
  c.interrupt?.(); c.stop();
  switch (name) {
    case 'idle': c.reset(0, 0.9, 0); break;
    case 'walk': c.reset(0, 1.6, Math.PI); c.walkTo(0, -1.2, false); break;
    case 'run': c.reset(0, 1.8, Math.PI); c.walkTo(0, -1.6, true); break;
    case 'jump': c.reset(0, 0.9, 0); c.jump(); break;
    case 'sit': c.reset(-0.6, 0.1, 0.4); c.sitOn('stool'); break;
    case 'sleep': c.reset(0, 0.9, 0); c.sleep(); break;
    case 'grab': c.reset(0, 0.9, 0); c.grab(0, 0.95, 0.9); break;
    case 'throw': c.reset(-1.4, 0.9, 0); c.throwAt(3.2, 5.2, -0.4); break;
    default: c.reset(0, 0.9, 0); c.trigger(name);
  }
  S.qaAction = name; return true;
}
setInterval(() => {
  if (qa.hidden || $('#qTxt').hidden) return; const c = cc(); if (!c) { $('#qTxt').textContent = '（先進入場地模式）'; return; }
  const i = c.info(), f = (v, n = 2) => (+v).toFixed(n), b = c.body;
  $('#qTxt').textContent = `狀態　${i.state}${i.sub ? '／' + i.sub : ''}（姿勢 ${i.key}）\n速度　水平 ${f(i.speed)}　垂直 ${f(i.vy)} m/s\n接地　${i.grounded ? '是（接地）' : '否（空中）'}　支撐面 ${f(b.supportY, 3)} m\n高度　${f(i.y, 3)} m　位置 (${f(i.x)}, ${f(i.z)})\n播放　${S.timeScale}×${S.paused ? '（暫停）' : ''}　逐格 ${S.stepped || 0}`;
}, 120);
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
  // 播放速度與逐格：timeScale 0.25／0.5／1；暫停時按「逐格」才前進 1/60 秒（不受 timeScale 影響）
  let sim = S.paused ? 0 : dt * S.timeScale; if (S.paused && S.stepN > 0) { S.stepN--; sim = 1 / 60; S.stepped = (S.stepped || 0) + 1; }
  const sdt = sim; S.time += sdt;
  if (S.ch) {
    const c = S.ch;
    if (S.play && S.field?.ctl) {
      const cc = S.field.ctl; trackPlay(dt, cc); if (sim > 0) { cc.update(sim); S.field.fx.update(sim, cc); } else c.update(dt, true);
      followCam(dt, cc); S.qav?.update(cc);
    } else {
    if (sim > 0) {
      if (S.act) { S.act.t += sim; if (S.act.t >= S.act.dur) endAct(); }
      if (!S.act) { c.resetPose(); } else { c.resetPose(); }
      idle(c, S.time); trackGaze(c);
      if (S.act) S.act.fn(c, S.act.t);
    }
    c.update(sim > 0 ? sim : dt, sim <= 0);
    }
    stage.updateContact();
  }
  if (S.old && S.cmp && sdt > 0) { S.old.step(sdt, { mx: 0, mz: 0, run: false, jump: false }); S.old.animate(sdt, { look: null, cam: camera.position }); S.old.lookT = 1e9; }
  if (S.skipRender) { /* 自動驗收用：不繪圖，只跑模擬與互動（軟體繪圖一幀要 1 秒） */ }
  else if (S.cmp && S.old) {
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
window.CH.qa = makeQA(window.CH); Object.assign(window.CH, { qaPlay, shotPNG, setPaused, ensureQav, applyMode, qaPanel: qa }); Object.defineProperty(window.CH, 'qav', { get: () => S.qav });   // Object.assign 會把 getter 取值一次，所以 qav 要用 defineProperty
if (qs.has('qa')) { qa.hidden = false; $('#btnQA').classList.add('on'); }
document.title = 'ok'; document.documentElement.dataset.ready = '1';
