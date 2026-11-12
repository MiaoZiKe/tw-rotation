// 小房間：場景、輸入、鏡頭、介面與主迴圈
import * as THREE from 'three';
import { World, BOUNDS, G } from './world.js';
import { FX } from './fx.js';
import { Character } from './character.js';
import { blobGeo, softMat } from './soft.js';
import { SPECIES, SPECIES_IDS, ACCESSORIES, canWear } from './species.js';
import { renderThumb } from './lite.js';

const $ = (s) => document.querySelector(s), V3 = THREE.Vector3, clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const view = $('#view'), qs = new URLSearchParams(location.search);
const touch = matchMedia('(pointer:coarse)').matches || 'ontouchstart' in window || qs.has('touch');
if (touch) document.body.classList.add('touch');
if (qs.has('shot')) document.body.classList.add('shot');

// ── 繪圖器、場景、燈光
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: qs.has('shot') || qs.has('test') });
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = qs.get('tm') === 'aces' ? THREE.ACESFilmicToneMapping : THREE.NoToneMapping; renderer.toneMappingExposure = +(qs.get('ex') || 1.0);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
view.appendChild(renderer.domElement);
const scene = new THREE.Scene(), BG = 0xf6e6d4; scene.background = new THREE.Color(BG); scene.fog = new THREE.Fog(BG, 9, 26);
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 80);
scene.add(new THREE.HemisphereLight(0xfff6ec, 0xf0cdb0, +(qs.get('hl') || 1.3)));
const key = new THREE.DirectionalLight(0xfff1e0, +(qs.get('kl') || 2.0)); key.position.set(3.2, 7, 5.2); key.target.position.set(-0.3, 0, -0.4); key.castShadow = true;
const sm = touch ? 1024 : 2048; key.shadow.mapSize.set(sm, sm); Object.assign(key.shadow.camera, { left: -6.5, right: 6.5, top: 6, bottom: -6, near: 1, far: 22 }); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.03; key.shadow.radius = 5;
scene.add(key, key.target);
const rim = new THREE.DirectionalLight(0xffdcb8, 0.9); rim.position.set(-1.5, 3.5, -6); scene.add(rim);
const fill = new THREE.DirectionalLight(0xdfe9ff, 0.4); fill.position.set(-6, 3, 4); scene.add(fill);

const fx = new FX(scene), world = new World(scene, fx, touch);
// 台座下面的大片柔影
{ const m = new THREE.Mesh(new THREE.PlaneGeometry(16, 13), new THREE.MeshBasicMaterial({ map: fx.T.shadow, transparent: true, opacity: 0.45, depthWrite: false })); m.rotation.x = -Math.PI / 2; m.position.set(0, -0.52, 0.2); scene.add(m); }
const ring = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: fx.T.ring, transparent: true, depthWrite: false, opacity: 0 })); ring.rotation.x = -Math.PI / 2; ring.renderOrder = 4; scene.add(ring); let ringT = 9;

// ── 角色
let char = null, charIdx = -1; const pick = { pal: 0, acc: [] };
function setChar(i, force) {
  i = ((i % SPECIES_IDS.length) + SPECIES_IDS.length) % SPECIES_IDS.length; if (i === charIdx && !force) return;
  if (i !== charIdx) { pick.pal = 0; }
  const cfg = SPECIES[SPECIES_IDS[i]], old = char; let pos = null, yaw = 0; if (old) { pos = old.pos.clone(); yaw = old.yaw; old.dispose(); for (const o of world.dyn) { o.held = false; o.caught = false; } }
  char = new Character({ species: cfg.id, pal: pick.pal, acc: pick.acc, accColor: pick.pal + i }, scene, world, fx); charIdx = i;
  if (pos) { char.pos.copy(pos); char.pos.y += force ? 0.25 : 0.6; char.yaw = yaw; char.grounded = false; char.feet.forEach(f => f.p.copy(char.pos)); char.hands.forEach(h => h.p.copy(char.pos).setY(char.pos.y + 0.3)); fx.burst('spark', pos.clone().setY(pos.y + 0.4), 8, { speed: 1.4, up: 0.8, life: 0.5, size: 0.14 }); fx.sfx('boing'); }
  $('#btnDex').textContent = `圖鑑｜${cfg.name}`;
  const n = $('#charNote'); n.textContent = `${cfg.name}（${cfg.sub}）｜${cfg.why}`; n.style.opacity = 1; clearTimeout(setChar.t); setChar.t = setTimeout(() => n.style.opacity = 0, 5200);
  const sg = [...document.querySelectorAll('.chip')].find(x => x.dataset.sig); if (sg) sg.textContent = cfg.sigZh;
  try { localStorage.setItem('play.sp', cfg.id); } catch (e) { }
  renderDexSide();
}

// ── 鏡頭
const cam = { mode: 'follow', yaw: 0.42, pitch: 0.36, dist: 6.4, tgt: new V3(0, 0.5, 0.6), cur: { yaw: 0.42, pitch: 0.36, dist: 6.4 }, zoom: 1 };
function camGoal() {
  const portrait = camera.aspect < 0.8;
  if (cam.over) return cam.over;
  if (cam.mode === 'god') return { pitch: 0.98, dist: (portrait ? 21 : 12.5) * cam.zoom, x: 0, y: 0.2, z: portrait ? 0.3 : 0.2 };
  return { pitch: cam.pitch, dist: (portrait ? 7.6 : 6.4) * cam.zoom, x: char.pos.x, y: char.pos.y * 0.6 + 0.48, z: char.pos.z };
}
function updateCam(dt, snap) {
  const g = camGoal(), k = snap ? 1 : 1 - Math.exp(-dt * 4.5), c = cam.cur;
  c.yaw += (cam.yaw - c.yaw) * (snap ? 1 : 1 - Math.exp(-dt * 10)); c.pitch += (g.pitch - c.pitch) * k; c.dist += (g.dist - c.dist) * k;
  cam.tgt.x += (g.x - cam.tgt.x) * k; cam.tgt.y += (g.y - cam.tgt.y) * k; cam.tgt.z += (g.z - cam.tgt.z) * k;
  const cp = Math.cos(c.pitch); camera.position.set(cam.tgt.x + Math.sin(c.yaw) * cp * c.dist, cam.tgt.y + Math.sin(c.pitch) * c.dist, cam.tgt.z + Math.cos(c.yaw) * cp * c.dist);
  camera.lookAt(cam.tgt);
}
function resize() { const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w / h < 0.8 ? 40 : 34; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();

// ── 輸入
const keys = new Set(), ctl = { mx: 0, mz: 0, run: false, jump: false }, joy = { x: 0, y: 0, on: false };
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), tmp = new V3(), look = new V3(); let lookT = 9;
let ptr = null, heldBall = null; const ballT = new V3(), pinch = { ids: new Map(), d0: 0, z0: 1 };
const setNdc = (e) => { const r = view.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera); };
function vPlane(point) { const d = camera.getWorldDirection(tmp); d.y = 0; if (d.lengthSq() < 0.05) d.set(0, 0, -1); d.normalize(); plane.setFromNormalAndCoplanarPoint(d, point); }
function floorPoint(out) { const o = ray.ray.origin, d = ray.ray.direction; if (d.y > -0.01) return null; const t = -o.y / d.y; return out.copy(o).addScaledVector(d, t); }
function firstUse() { $('#hint').classList.add('off'); fx._ac(); }
view.addEventListener('pointerdown', (e) => {
  firstUse(); view.setPointerCapture(e.pointerId); pinch.ids.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch.ids.size === 2) { const [a, b] = [...pinch.ids.values()]; pinch.d0 = Math.hypot(a.x - b.x, a.y - b.y); pinch.z0 = cam.zoom; if (ptr && ptr.kind === 'char' && !ptr.drag) { char.petEnd(); } ptr = null; return; }
  setNdc(e);
  const hits = ray.intersectObjects([...char.pickList, ...world.pick], false), h = hits[0];
  ptr = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, t0: performance.now(), moved: false, kind: 'floor', drag: false, pet: false };
  if (h) {
    const ud = h.object.userData;
    if (ud.char) { ptr.kind = 'char'; ptr.hit = h.point.clone(); ptr.dir = ray.ray.direction.clone(); }
    else if (ud.dyn) { ptr.kind = 'ball'; heldBall = ud.dyn; heldBall.held = true; heldBall.v.set(0, 0, 0); vPlane(heldBall.p); ballT.copy(heldBall.p); ballT.y = Math.max(ballT.y, heldBall.r + 0.25); char.idleT = 0; }
    else if (ud.use) { ptr.kind = 'use'; ptr.use = ud.use; }
  }
});
view.addEventListener('pointermove', (e) => {
  if (pinch.ids.has(e.pointerId)) pinch.ids.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch.ids.size === 2) { const [a, b] = [...pinch.ids.values()]; const d = Math.hypot(a.x - b.x, a.y - b.y); cam.zoom = clamp(pinch.z0 * pinch.d0 / Math.max(20, d), 0.6, 1.5); return; }
  setNdc(e); lookT = 0;
  if (!ptr || e.pointerId !== ptr.id) { return; }
  const dx = e.clientX - ptr.x, dy = e.clientY - ptr.y; ptr.x = e.clientX; ptr.y = e.clientY;
  if (!ptr.moved && Math.hypot(e.clientX - ptr.x0, e.clientY - ptr.y0) > (touch ? 12 : 7)) ptr.moved = true;
  if (ptr.kind === 'char') {
    if (ptr.moved && !ptr.drag && (!ptr.pet || Math.hypot(e.clientX - ptr.x0, e.clientY - ptr.y0) > 46)) { if (ptr.pet) { char.petEnd(); ptr.pet = false; } ptr.drag = true; char.grab(); vPlane(char.center); }
    if (ptr.drag && ray.ray.intersectPlane(plane, tmp)) char.dragTo(tmp);
  } else if (ptr.kind === 'ball') { if (ray.ray.intersectPlane(plane, tmp)) { ballT.set(clamp(tmp.x, BOUNDS.x0 + 0.2, BOUNDS.x1 - 0.2), clamp(tmp.y, heldBall.r, 2.9), clamp(tmp.z, BOUNDS.z0 + 0.2, BOUNDS.z1 - 0.2)); } }
  else if (ptr.moved) { cam.yaw = clamp(cam.yaw - dx * 0.006, -0.35, 1.3); cam.pitch = clamp(cam.pitch + dy * 0.004, 0.16, 0.8); }
});
function pointerEnd(e) {
  pinch.ids.delete(e.pointerId);
  if (!ptr || e.pointerId !== ptr.id) return; const p = ptr; ptr = null; setNdc(e);
  if (p.kind === 'char') { if (p.drag) char.release(); else if (p.pet) char.petEnd(); else char.poke(p.hit, p.dir); }
  else if (p.kind === 'ball') { const b = heldBall; heldBall = null; b.held = false; const s = b.v.length(); if (s > 12) b.v.multiplyScalar(12 / s); }
  else if (!p.moved) {
    if (p.kind === 'use') { char.useThing(p.use); fx.sfx('ui'); }
    else if (floorPoint(tmp)) { const d = Math.hypot(tmp.x - char.pos.x, tmp.z - char.pos.z), dbl = performance.now() - (pointerEnd.last || 0) < 320; pointerEnd.last = performance.now(); char.setGoal(tmp.x, tmp.z, d > 2.6 || dbl); ring.position.set(clamp(tmp.x, BOUNDS.x0 + 0.3, BOUNDS.x1 - 0.3), world.groundAt(tmp.x, tmp.z, 0.2).h + 0.02, clamp(tmp.z, BOUNDS.z0 + 0.3, BOUNDS.z1 - 0.3)); ringT = 0; }
  }
}
view.addEventListener('pointerup', pointerEnd); view.addEventListener('pointercancel', pointerEnd);
view.addEventListener('wheel', (e) => { e.preventDefault(); cam.zoom = clamp(cam.zoom * (1 + Math.sign(e.deltaY) * 0.08), 0.6, 1.5); }, { passive: false });
view.addEventListener('contextmenu', (e) => e.preventDefault());
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return; const k = e.key.toLowerCase();
  if ([' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) e.preventDefault();
  if (k === ' ' && !e.repeat) { ctl.jump = true; firstUse(); }
  if (k === '[') setChar(charIdx - 1); if (k === ']') setChar(charIdx + 1); if (k === 'escape') $('#dex').hidden = true;
  keys.add(k);
});
addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase())); addEventListener('blur', () => keys.clear());
// 虛擬搖桿
{
  const st = $('#stick'), kn = $('#knob'); let id = null;
  const mv = (e) => { const r = st.getBoundingClientRect(), R = r.width / 2; let x = (e.clientX - r.left - R) / (R - 14), y = (e.clientY - r.top - R) / (R - 14); const m = Math.hypot(x, y); if (m > 1) { x /= m; y /= m; } joy.x = x; joy.y = y; kn.style.transform = `translate(${x * (R - 26)}px,${y * (R - 26)}px)`; };
  st.addEventListener('pointerdown', (e) => { id = e.pointerId; st.setPointerCapture(id); joy.on = true; mv(e); firstUse(); });
  st.addEventListener('pointermove', (e) => { if (e.pointerId === id) mv(e); });
  const end = (e) => { if (e.pointerId !== id) return; id = null; joy.on = false; joy.x = joy.y = 0; kn.style.transform = ''; };
  st.addEventListener('pointerup', end); st.addEventListener('pointercancel', end);
  $('#btnJump').addEventListener('pointerdown', (e) => { e.preventDefault(); ctl.jump = true; firstUse(); });
}
function readInput() {
  let x = 0, y = 0; if (keys.has('a') || keys.has('arrowleft')) x -= 1; if (keys.has('d') || keys.has('arrowright')) x += 1; if (keys.has('w') || keys.has('arrowup')) y -= 1; if (keys.has('s') || keys.has('arrowdown')) y += 1;
  let run = keys.has('shift'); const m = Math.hypot(x, y); if (m > 1) { x /= m; y /= m; }
  if (joy.on) { x = joy.x; y = joy.y; const jm = Math.hypot(x, y); run = jm > 0.8; if (jm < 0.18) x = y = 0; else if (!run) { x *= 1 / 0.8; y *= 1 / 0.8; } }
  // 以鏡頭為準：上＝遠離鏡頭
  const cy = Math.cos(cam.cur.yaw), sy = Math.sin(cam.cur.yaw); ctl.mx = x * cy + y * sy; ctl.mz = -x * sy + y * cy; ctl.run = run;
}

// ── 食物與丟球
const foods = []; let foodKind = 0;
function mkFood(k) {
  const sh = { uTint: { value: new THREE.Color(1, 1, 1) }, uTintAmt: { value: 0 }, uGround: { value: -50 } }, g = new THREE.Group(), sp = new THREE.SphereGeometry(1, 24, 18);
  if (k === 0) { // 草莓
    const b = new THREE.Mesh(blobGeo(v => { const w = 0.62 + 0.38 * (v.y * 0.5 + 0.5); v.set(v.x * 0.085 * w, v.y * 0.1, v.z * 0.085 * w); }, 28, 20), softMat({ color: 0xff6b7d, top: 0xff8f98, y0: -0.1, y1: 0.1, sss: 0xff3050, sssAmt: 0.5, rough: 0.4 }, sh)); g.add(b);
    const c = new THREE.Mesh(sp, softMat({ color: 0x7fd08a, sss: 0x9be070 }, sh)); c.scale.set(0.07, 0.022, 0.07); c.position.y = 0.095; g.add(c);
  } else if (k === 1) { // 餅乾
    const b = new THREE.Mesh(sp, softMat({ color: 0xf0c27a, top: 0xf8d79a, y0: -1, y1: 1, sss: 0xffa040, rough: 0.8 }, sh)); b.scale.set(0.1, 0.035, 0.1); g.add(b);
    for (let i = 0; i < 5; i++) { const c = new THREE.Mesh(sp, softMat({ color: 0x7a4a34, sss: 0x7a4a34, sssAmt: 0.1 }, sh)); c.scale.setScalar(0.016); const a = i * 1.257; c.position.set(Math.cos(a) * 0.05 * (i % 2 ? 1 : 0.5), 0.03, Math.sin(a) * 0.05 * (i % 2 ? 1 : 0.5)); g.add(c); }
    g.rotation.x = 0.9;
  } else { // 飯糰
    const b = new THREE.Mesh(blobGeo(v => { const w = 1 - 0.38 * (v.y * 0.5 + 0.5); v.set(v.x * 0.105 * w, v.y * 0.09, v.z * 0.07); }, 28, 20), softMat({ color: 0xfff6ea, top: 0xffffff, y0: -0.1, y1: 0.1, sss: 0xffd0a0, rough: 0.7 }, sh)); g.add(b);
    const n = new THREE.Mesh(sp, softMat({ color: 0x3f5a48, sss: 0x3f5a48, sssAmt: 0.1 }, sh)); n.scale.set(0.06, 0.045, 0.073); n.position.y = -0.05; g.add(n);
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); return g;
}
function feed() {
  if (!char.doAct('eat')) { hitChip('餵食', false); return false; }
  const m = mkFood(foodKind++ % 3); scene.add(m);
  const d = camera.getWorldDirection(new V3()), r = new V3().crossVectors(d, camera.up).normalize();
  const s = camera.position.clone().addScaledVector(d, 2.2).addScaledVector(r, 0.7).add(new V3(0, -0.5, 0));
  foods.push({ m, s, t: 0, T: 0.62 }); fx.sfx('whee'); return true;
}
function throwBall(force) {
  const b = world.ball; if (b.held) return false; char.wake();
  const d = camera.getWorldDirection(new V3()), s = camera.position.clone().addScaledVector(d, 1.6).add(new V3(0, -0.2, 0));
  const tgt = char.center.clone(); tgt.y += 0.08; const T = 0.72;
  s.x = clamp(s.x, BOUNDS.x0 + 0.3, BOUNDS.x1 - 0.3); s.z = clamp(s.z, BOUNDS.z0 + 0.3, BOUNDS.z1 - 0.3); s.y = Math.min(s.y, 2.4);
  b.p.copy(s); b.v.set((tgt.x - s.x) / T, (tgt.y - s.y) / T + 0.5 * G * T, (tgt.z - s.z) / T); b.caught = false;
  const ok = force != null ? force : Math.random() < 0.7; if (char.mode === 'normal') char.startCatch(b, ok); fx.sfx('whee'); return true;
}

// ── 介面
const TABS = {
  emo: [['開心', 'happy'], ['大笑', 'laugh'], ['驚訝', 'surprised'], ['生氣', 'angry'], ['難過', 'sad'], ['想睡', 'sleepy'], ['害羞', 'shy'], ['得意', 'smug']].map(([n, e]) => [n, () => { char.wake(); char.act = null; char.goal = null; char.emote(e, 3.6); }]),
  act: [['招牌動作', () => char.doAct('sig'), 'sig'], ['揮手', () => char.doAct('wave')], ['鞠躬', () => char.doAct('bow')], ['跳舞', () => char.doAct('dance')], ['轉圈', () => char.doAct('spin')], ['說話', () => char.doAct('talk', ['今天也要加油！', '陪我玩嘛～', '肚子餓了…', '你好呀！'][Math.floor(Math.random() * 4)])], ['打哈欠', () => char.doAct('yawn')], ['坐下', () => { char.wake(); char.sit(); }], ['睡覺', () => char.sleep()]],
  play: [['餵食', feed], ['丟球給它', () => throwBall()], ['坐沙發', () => char.useThing(world.sofaUse)], ['坐圓凳', () => char.useThing(world.uses[1])], ['跳彈跳床', () => char.useThing(world.uses[2])], ['回小窩睡', () => char.useThing(world.bedUse)], ['過來這邊', () => { const d = camera.getWorldDirection(new V3()); char.setGoal(cam.tgt.x - d.x * 1.6, cam.tgt.z - d.z * 1.6 + 0.4, true); }]],
};
let tab = 'emo';
function hitChip(name) { const b = [...document.querySelectorAll('.chip')].find(x => x.textContent === name); if (b) { b.classList.add('hit'); setTimeout(() => b.classList.remove('hit'), 160); } }
function renderChips() {
  const box = $('#chips'); box.innerHTML = '';
  for (const [n, fn, sig] of TABS[tab]) { const b = document.createElement('button'); b.className = 'chip'; b.textContent = sig && char ? char.cfg.sigZh : n; if (sig) b.dataset.sig = 1; b.addEventListener('click', () => { firstUse(); fx.sfx('ui'); fn(); }); box.appendChild(b); }
  document.querySelectorAll('#segTab button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
}
document.querySelectorAll('#segTab button').forEach(b => b.addEventListener('click', () => { tab = b.dataset.tab; renderChips(); }));
// ── 圖鑑：全部物種一覽，點一隻放進房間；右側可換配色與配件
const thumbs = {};
function thumbOf(id, pal = 0) { const k = id + ':' + pal; return thumbs[k] || (thumbs[k] = renderThumb(renderer, { species: id, pal }, { size: 240, shadowTex: fx.T.shadow, cy: 0.5, dist: 3.5, yaw: 0.3 })); }
function renderDex() {
  const grid = $('#dexGrid'); grid.innerHTML = '';
  SPECIES_IDS.forEach((id, i) => {
    const c = SPECIES[id], b = document.createElement('button'); b.className = 'card' + (i === charIdx ? ' on' : ''); b.dataset.id = id;
    b.innerHTML = `<img alt="${c.name}" width="100" height="100"><b>${c.name}</b><span>${c.sub}</span><i>${c.moveZh}・${c.sigZh}</i>`;
    b.addEventListener('click', () => { firstUse(); setChar(i); $('#dex').hidden = true; }); grid.appendChild(b);
  });
  // 縮圖一張一張慢慢畫，不要卡住畫面
  let k = 0; const imgs = [...grid.querySelectorAll('img')]; const next = () => { if (k >= imgs.length || $('#dex').hidden) return; imgs[k].src = thumbOf(SPECIES_IDS[k]); k++; (manual ? next : () => setTimeout(next, 0))(); }; next();
  $('#dexCount').textContent = `共 ${SPECIES_IDS.length} 種`;
}
function renderDexSide() {
  const box = $('#dexPal'); if (!box || !char) return; box.innerHTML = '';
  char.cfg.pals.forEach((p, i) => { const b = document.createElement('button'); b.className = 'chip' + (i === pick.pal ? ' sel' : ''); b.innerHTML = `<em style="background:#${(p.body ?? p.acc).toString(16).padStart(6, '0')}"></em>${p.n}`; b.addEventListener('click', () => { pick.pal = i; setChar(charIdx, true); }); box.appendChild(b); });
  const ab = $('#dexAcc'); ab.innerHTML = '';
  for (const [k, zh] of ACCESSORIES) { const ok = canWear(char.cfg, k), b = document.createElement('button'); b.className = 'chip' + (pick.acc.includes(k) && ok ? ' sel' : ''); b.textContent = zh; b.disabled = !ok; if (!ok) b.title = '這個物種戴不了'; b.addEventListener('click', () => { pick.acc = pick.acc.includes(k) ? pick.acc.filter(x => x !== k) : [...pick.acc, k]; setChar(charIdx, true); }); ab.appendChild(b); }
  document.querySelectorAll('#dexGrid .card').forEach((b, i) => b.classList.toggle('on', i === charIdx));
  $('#dexNow').textContent = `${char.cfg.name}｜${char.cfg.sub}`;
}
$('#btnDex').addEventListener('click', () => { firstUse(); const d = $('#dex'); d.hidden = !d.hidden; if (!d.hidden) { renderDex(); renderDexSide(); } });
$('#dexClose').addEventListener('click', () => { $('#dex').hidden = true; });
$('#btnPrev').addEventListener('click', () => { firstUse(); setChar(charIdx - 1); }); $('#btnNext').addEventListener('click', () => { firstUse(); setChar(charIdx + 1); });
document.querySelectorAll('#segCam button').forEach(b => b.addEventListener('click', () => { cam.mode = b.dataset.cam; document.querySelectorAll('#segCam button').forEach(x => x.classList.toggle('on', x === b)); }));
$('#btnSnd').addEventListener('click', (e) => { fx.muted = !fx.muted; e.currentTarget.textContent = fx.muted ? '音效關' : '音效開'; e.currentTarget.setAttribute('aria-pressed', String(!fx.muted)); if (!fx.muted) fx.sfx('ui'); });
$('#btnHelp').addEventListener('click', () => { $('#help').hidden = !$('#help').hidden; }); $('#helpClose').addEventListener('click', () => { $('#help').hidden = true; });
renderChips();
let saved = 0; try { saved = Math.max(0, SPECIES_IDS.indexOf(localStorage.getItem('play.sp'))); } catch (e) { }
if (qs.has('acc')) pick.acc = qs.get('acc').split(',');
setChar(qs.has('c') ? (isNaN(+qs.get('c')) ? Math.max(0, SPECIES_IDS.indexOf(qs.get('c'))) : +qs.get('c')) : saved);
updateCam(0, true);

// ── 主迴圈
const env = { look: null, cam: camera.position, idleScale: +(qs.get('idle') || 1), food: null };
let T = 0, skipRender = false; const bubble = $('#bubble');
function frame(dt) {
  dt = Math.min(dt, 0.05); T += dt; readInput();
  const n = Math.max(1, Math.ceil(dt / (1 / 120))), h = dt / n;
  for (let i = 0; i < n; i++) {
    char.step(h, ctl); world.step(h, char);
    if (heldBall) { const b = heldBall; b.v.x += ((ballT.x - b.p.x) * 130 - b.v.x * 16) * h; b.v.y += ((ballT.y - b.p.y) * 130 - b.v.y * 16) * h; b.v.z += ((ballT.z - b.p.z) * 130 - b.v.z * 16) * h; b.p.addScaledVector(b.v, h); }
  }
  // 摸頭：按住角色不動超過 0.4 秒
  if (ptr && ptr.kind === 'char' && !ptr.drag && !ptr.pet && performance.now() - ptr.t0 > 400 || (ptr && ptr.forcePet && !ptr.pet)) { ptr.pet = true; char.petStart(ptr.hit); }
  // 視線：游標／手指 → 會動的球 → 自己東張西望
  lookT += dt; env.look = null;
  if (heldBall) env.look = heldBall.p;
  else if (lookT < 3.5 && !touch || ptr) { vPlaneLook(); if (ray.ray.intersectPlane(plane, look)) env.look = look; }
  if (!env.look) for (const o of world.dyn) if (o.v.lengthSq() > 2.2 && !o.caught) { env.look = o.p; break; }
  // 食物飛進嘴裡
  env.food = null;
  for (let i = foods.length - 1; i >= 0; i--) {
    const f = foods[i]; f.t += dt; const u = Math.min(1, f.t / f.T), e = char.mouthWorld(tmp);
    f.m.position.lerpVectors(f.s, e, u); f.m.position.y += Math.sin(u * Math.PI) * 0.45; f.m.rotation.y += dt * 6; f.m.scale.setScalar(u > 0.85 ? Math.max(0.01, 1 - (u - 0.85) / 0.15) : 1); env.food = f.m.position;
    if (u >= 1) { scene.remove(f.m); foods.splice(i, 1); }
  }
  char.animate(dt, env); world.update(dt, T, char); fx.update(dt, T);
  ringT += dt; ring.material.opacity = Math.max(0, 0.9 - ringT * 1.8); ring.scale.setScalar(0.3 + ringT * 0.9);
  updateCam(dt);
  // 對話泡泡
  if (char.speech) { char.headTop(tmp); tmp.y += 0.22; tmp.project(camera); const w = view.clientWidth, hh = view.clientHeight, bx = clamp((tmp.x * 0.5 + 0.5) * w, 60, w - 60), by = Math.max(70, (-tmp.y * 0.5 + 0.5) * hh); bubble.hidden = false; if (bubble.textContent !== char.speech.text) bubble.textContent = char.speech.text; bubble.style.transform = `translate(${bx}px,${by}px) translate(-50%,-100%)`; }
  else if (!bubble.hidden) bubble.hidden = true;
  if (!skipRender) renderer.render(scene, camera);
}
function vPlaneLook() { const d = camera.getWorldDirection(tmp).negate(); plane.setFromNormalAndCoplanarPoint(d, char.center.clone().addScaledVector(d, 1.2)); }
let last = performance.now(), manual = qs.has('manual');
function loop(now) { requestAnimationFrame(loop); const dt = (now - last) / 1000; last = now; if (!manual) frame(dt); }
requestAnimationFrame(loop);

// 給自動測試用的接口
window.PLAY = {
  get char() { return char; }, world, cam, fx, ctl, keys, SPECIES, SPECIES_IDS, pick, setChar, thumb: (spec, o) => renderThumb(renderer, spec, { shadowTex: fx.T.shadow, ...o }), feed, throwBall, env, camera, renderer,
  set manual(v) { manual = v; }, get manual() { return manual; },
  // 只有最後一幀真的畫（軟體繪圖很慢，測試時省時間）
  tick(dt = 1 / 60, n = 1, all = false) { for (let i = 0; i < n; i++) { skipRender = !all && i < n - 1; frame(dt); } skipRender = false; },
  sim(n = 1, dt = 1 / 60) { skipRender = true; for (let i = 0; i < n; i++) frame(dt); skipRender = false; },
  setCam(o) { Object.assign(cam, o); if (o.snap) updateCam(0, true); },
  snapCam() { updateCam(0, true); },
  screen(v) { const q = new V3(v.x, v.y, v.z).project(camera), r = view.getBoundingClientRect(); return [r.left + (q.x * 0.5 + 0.5) * r.width, r.top + (-q.y * 0.5 + 0.5) * r.height]; },
  state() { const c = char; return { mode: c.mode, x: c.pos.x, y: c.pos.y, z: c.pos.z, vx: c.vel.x, vy: c.vel.y, vz: c.vel.z, grounded: c.grounded, sq: c.sq, yaw: c.yaw, expr: c.face.name, act: c.act ? c.act.name : null, emo: c.emo ? c.emo.name : null, speech: c.speech ? c.speech.text : null, feet: c.feet.map(f => [f.p.x, f.p.y, f.p.z, f.planted]), slip: c.stat.slip, tab, charIdx }; },
};
