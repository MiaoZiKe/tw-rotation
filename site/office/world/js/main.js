// 進入點：載入資料 → 蓋場景 → 放角色 → 鏡頭、標籤、點選、整修 → 主迴圈。
import * as THREE from 'three';
import { OrbitControls } from '../../vendor/OrbitControls.js';
import { createWorld, saveOverrides, clearOverrides } from './world.js';
import { createDirector } from './director.js';
import { createUI } from './ui.js';

const $ = id => document.getElementById(id);
const qs = new URLSearchParams(location.search);
const J = u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });

// 正式角色做好後：world.html?char=../../play/xxx.js，或直接把下面的預設路徑換掉
async function loadCharacterModule() { const p = qs.get('char') || './character.js'; const m = await import(p); if (typeof m.createCharacter !== 'function') throw new Error('角色模組必須匯出 createCharacter'); return m; }

(async function boot() {
  const [layout, org, demo, meet, charMod] = await Promise.all([J('world/data/layout.json'), J('world/data/org.json'), J('world/data/demo.json'), J('world/data/meeting_demo.json'), loadCharacterModule()]);
  const coarse = matchMedia('(pointer:coarse)').matches || innerWidth < 720;
  let quality = qs.get('q') || (coarse ? 'low' : 'high'); const pinned = qs.has('q');
  const cv = $('cv'), W = createWorld(cv, layout, org, quality), { renderer, scene, camera } = W;
  W.stats = { calls: 0, tris: 0, fps: 0, walks: 0, noPath: 0, interrupted: 0, quality };
  let pr = Math.min(devicePixelRatio || 1, quality === 'low' ? 1.5 : 2);
  function resize() { const w = cv.clientWidth, h = cv.clientHeight; renderer.setPixelRatio(pr); renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
  addEventListener('resize', resize); resize();

  // ── 角色 ──
  const env = {
    isFree: (x, z) => W.nav.isFree(x, z),
    separation(c, dx, dz) {
      let px = 0, pz = 0, slow = 1; const p = c.object3D.position;
      for (const o of W.chars.values()) {
        if (o === c || o.state === 'sit' || !o.object3D.visible) continue;
        const q = o.object3D.position, ex = p.x - q.x, ez = p.z - q.z, d = Math.hypot(ex, ez); if (d > 0.95 || d < 1e-4) continue;
        const w = (0.95 - d) / 0.95; px += ex / d * w * 2.4; pz += ez / d * w * 2.4;
        const ahead = (-ex * dx - ez * dz) / d; if (ahead > 0.25) { px += -dz * w * 1.8; pz += dx * w * 1.8; if (d < 0.55) slow = 0.55; }
      }
      return { x: px, z: pz, slow };
    }
  };
  const specs = [{ ...org.ceo, isCeo: true }]; for (const d of org.departments) for (const m of d.members) specs.push({ ...m, dept: d.id, color: d.color });
  const labels = $('labels');
  for (const s of specs) {
    const c = charMod.createCharacter(s, env); W.chars.set(s.id, c); scene.add(c.object3D);
    const seat = W.spots.find(q => q.name === 'seat:' + s.id);
    if (seat) { seat.taken = s.id; c.spot = seat; c.sitAt(seat.seat); c.atDesk = true; c.setAction('type'); } else c.standAt(20, 26, 0);
    const tag = document.createElement('div'); tag.className = 'tag'; tag.innerHTML = `<b></b><span></span>`; tag.firstChild.textContent = s.nick; tag.lastChild.textContent = s.isCeo ? s.zh : `${s.id}・${s.zh}`;
    const bub = document.createElement('div'); bub.className = 'bub'; const emo = document.createElement('div'); emo.className = 'emo';
    labels.append(tag, bub, emo); c._lab = { tag, bub, emo, cls: '', txt: '', sym: '', on: false, bon: false, eon: false };
  }
  const ceo = W.chars.get('ceo');

  // ── 鏡頭 ──
  const controls = new OrbitControls(camera, cv); controls.enableDamping = true; controls.dampingFactor = 0.14; controls.screenSpacePanning = false; controls.maxPolarAngle = 1.32; controls.zoomSpeed = 1.1;
  const view = { mode: 'ceo', char: ceo, tween: null, lastUser: -10 }; W.view = view; W.controls = controls;
  controls.addEventListener('start', () => { view.lastUser = performance.now() / 1000; if (view.tween) view.tween = null; });
  const CENTER = new THREE.Vector3(layout.size.w / 2, 0, layout.size.d / 2 + 0.6), v3 = new THREE.Vector3(), v3b = new THREE.Vector3();
  const portrait = () => cv.clientWidth < cv.clientHeight;
  function modeControls(follow) {
    controls.enablePan = !follow; controls.minDistance = follow ? 2.5 : 7; controls.maxDistance = follow ? 18 : 130;
    controls.mouseButtons = follow ? { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE } : { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
    controls.touches = follow ? { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN } : { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
  }
  // 跟隨視角：鏡頭在角色身後，看向角色前方一點的地方（角色在畫面下半，前面的辦公室看得到）
  const AHEAD = 2.2, ahead = { x: 0, z: 0 };
  const charTarget = (c, out) => out.set(c.object3D.position.x + ahead.x, 0.9, c.object3D.position.z + ahead.z);
  // 高的家具（佈告欄、名牌、書架…）會擋住鏡頭：先試正後方，被擋就往兩側找一個看得到角色的角度
  const TALL = { board: 1, deptsign: 1, bookshelf: 1, fridge: 1, whiteboard: 1, cabinet: 1, arcade: 1, plant_big: 1, snack: 1, door: 1, roomsign: 1 };
  function blocked(ax, az, bx, bz) {
    for (const inst of W.furn.values()) {
      if (!TALL[inst.f.type] || !inst.spec.foot.length) continue; const f = inst.f, r = Math.max(inst.spec.foot[0].w || 0.6, 0.6) / 2 + 0.25;
      const dx = bx - ax, dz = bz - az, L = dx * dx + dz * dz; let t = L ? ((f.x - ax) * dx + (f.z - az) * dz) / L : 0; t = Math.max(0, Math.min(1, t));
      if (Math.hypot(ax + dx * t - f.x, az + dz * t - f.z) < r) return true;
    }
    return false;
  }
  function followPose(c) {
    const h0 = c.heading, back = portrait() ? 5.2 : 4.2, up = portrait() ? 3.4 : 2.5, cp = c.object3D.position;
    let best = null;
    for (const da of [0, 0.6, -0.6, 1.15, -1.15, 1.8, -1.8, Math.PI]) {
      const h = h0 + da, p = new THREE.Vector3(cp.x - Math.sin(h) * back, up, cp.z - Math.cos(h) * back);
      p.x = Math.max(0.55, Math.min(layout.size.w - 0.55, p.x)); p.z = Math.max(0.55, Math.min(layout.size.d + 4, p.z));
      const d = Math.hypot(p.x - cp.x, p.z - cp.z); if (d < back - 0.3) p.y += (back - d) * 0.35;
      const cand = { p, h, d }; if (!best) best = cand;
      if (d > back * 0.6 && !blocked(p.x, p.z, cp.x, cp.z)) { best = cand; break; }
    }
    const fx = cp.x - best.p.x, fz = cp.z - best.p.z, fl = Math.hypot(fx, fz) || 1;
    ahead.x = fx / fl * AHEAD; ahead.z = fz / fl * AHEAD;
    return { t: charTarget(c, new THREE.Vector3()), p: best.p, fov: 46 };
  }
  function godPose(target, dist) {
    const t = (target || CENTER).clone(), d = dist || (portrait() ? 96 : 52), pol = 0.62;
    return { t, p: new THREE.Vector3(t.x, t.y + d * Math.cos(pol), t.z + d * Math.sin(pol)), fov: 38 };
  }
  function tweenTo(pose, sec = 0.95) { view.tween = { p0: camera.position.clone(), t0: controls.target.clone(), f0: camera.fov, pose, t: 0, sec, off: pose.p.clone().sub(pose.t) }; }
  function setView(mode, c, instant) {
    if (mode === 'ceo') c = ceo; if (mode === 'char' && !c) c = view.char || ceo;
    view.mode = mode; view.char = mode === 'god' ? null : c; modeControls(mode !== 'god');
    const pose = mode === 'god' ? godPose() : followPose(c);
    if (instant) { camera.position.copy(pose.p); controls.target.copy(pose.t); camera.fov = pose.fov; camera.updateProjectionMatrix(); view.tween = null; } else tweenTo(pose);
    ui.setViewUI(mode, c); W.ring.visible = mode === 'char';
    if (mode !== 'char') ui.hideCard();
  }
  function jumpTo(roomId) {
    const r = layout.rooms.find(q => q.id === roomId); if (!r) return;
    view.mode = 'god'; view.char = null; modeControls(false); ui.setViewUI('god'); W.ring.visible = false;
    tweenTo(godPose(new THREE.Vector3(r.x + r.w / 2, 0, r.z + r.d / 2 + 0.4), Math.max(r.w, r.d * 1.5) * (portrait() ? 2.2 : 0.82) + 5));
  }
  function updateCamera(dt) {
    const tw = view.tween;
    if (tw) {
      tw.t += dt / tw.sec; const k = Math.min(1, tw.t), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      if (view.char) { charTarget(view.char, tw.pose.t); tw.pose.p.copy(tw.pose.t).add(tw.off); }
      camera.position.lerpVectors(tw.p0, tw.pose.p, e); controls.target.lerpVectors(tw.t0, tw.pose.t, e);
      if (tw.pose.fov && tw.pose.fov !== tw.f0) { camera.fov = tw.f0 + (tw.pose.fov - tw.f0) * e; camera.updateProjectionMatrix(); }
      if (k >= 1) view.tween = null; return;
    }
    if (view.char) {
      const c = view.char; { const cp = c.object3D.position, fx = cp.x - camera.position.x, fz = cp.z - camera.position.z, fl = Math.hypot(fx, fz) || 1, kk = Math.min(1, dt * 2); ahead.x += (fx / fl * AHEAD - ahead.x) * kk; ahead.z += (fz / fl * AHEAD - ahead.z) * kk; } charTarget(c, v3); v3b.subVectors(v3, controls.target).multiplyScalar(Math.min(1, dt * 7)); controls.target.add(v3b); camera.position.add(v3b);
      // 角色走路時，鏡頭慢慢繞回他身後（使用者剛拖過就先不動）
      if (c.state === 'walk' && performance.now() / 1000 - view.lastUser > 2.5) {
        const ox = camera.position.x - controls.target.x, oz = camera.position.z - controls.target.z, a = Math.atan2(ox, oz), want = c.heading + Math.PI;
        let d = Math.atan2(Math.sin(want - a), Math.cos(want - a)); d = Math.max(-dt * 0.9, Math.min(dt * 0.9, d));
        const cs = Math.cos(d), sn = Math.sin(d); camera.position.x = controls.target.x + ox * cs + oz * sn; camera.position.z = controls.target.z - ox * sn + oz * cs;
      }
      if (W.ring.visible) W.ring.position.set(c.object3D.position.x, 0.08, c.object3D.position.z);
    }
  }

  // ── 導演與介面 ──
  let director;
  const ui = createUI(W, demo, {
    setView: (m, c) => setView(m, c), jumpTo, cardClosed() { },
    ambient: () => director.ambient, setSpeed: s => { W.speed = s; },
    toggleEdit: () => toggleEdit(),
    runDemo(k) {
      if (k === 'ambient') { director.ambient = !director.ambient; return; }
      if (k === 'meeting') { if (director.running) { ui.toast('會議示範正在進行中'); return; } director.play(meet.events); return; }
      if (k === 'clockout') { director.clockOut(6); ui.toast('下班：幾位同事從大門離開'); return; }
      if (k === 'clockin') { director.clockIn(6); ui.toast('上班：同事從大門進來'); return; }
      const c = director.routine(null, k); ui.toast(c ? '已派一位同事去' + { coffee: '倒咖啡', lookup: '查資料', rest: '休息', play: '遊樂區', snack: '吃點心' }[k] : '目前沒有空閒的同事');
    }
  });
  director = createDirector(W, ui); W.director = director; W.ui = ui; W.meet = meet;
  if (qs.get('ambient') === '0') director.ambient = false;

  // ── 名牌、泡泡 ──
  const pv = new THREE.Vector3();
  function updateLabels() {
    const w = cv.clientWidth, h = cv.clientHeight;
    for (const c of W.chars.values()) {
      const L = c._lab, p = c.object3D.position; let on = c.object3D.visible;
      if (on) { pv.set(p.x, p.y + c.height + 0.12, p.z); var dist = pv.distanceTo(camera.position); pv.project(camera); if (pv.z > 1 || Math.abs(pv.x) > 1.08 || Math.abs(pv.y) > 1.2 || (view.mode !== 'god' && dist > 17 && !c.speech)) on = false; }
      if (!on) { if (L.on) { L.tag.style.transform = L.bub.style.transform = L.emo.style.transform = 'translate(-999px,-999px)'; L.on = L.bon = L.eon = false; } c._sx = -999; continue; }
      const x = Math.round((pv.x + 1) / 2 * w), y = Math.round((1 - pv.y) / 2 * h); c._sx = x; c._sy = y; c._sd = dist;
      const cls = 'tag' + (c.spec.lead || c.spec.isCeo ? ' lead' : '') + (dist < 15 ? '' : dist < 34 ? ' mid' : ' far'); if (cls !== L.cls) { L.tag.className = cls; L.cls = cls; }
      L.tag.style.transform = `translate(${x}px,${y}px) translate(-50%,-100%)`; L.on = true;
      const th = dist < 15 ? 38 : dist < 34 ? 24 : 18;
      if (c.speech) {
        if (L.txt !== c.speech.text) { L.bub.textContent = c.speech.text; L.txt = c.speech.text; L.bub.className = 'bub ' + (c.speech.kind || ''); }
        L.bub.style.transform = `translate(${x}px,${y - th - 10}px) translate(-50%,-100%)`; L.bon = true;
      } else if (L.bon) { L.bub.style.transform = 'translate(-999px,-999px)'; L.bon = false; L.txt = ''; }
      if (c.emoteSym && !c.speech) {
        if (L.sym !== c.emoteSym.sym) { L.emo.textContent = c.emoteSym.sym; L.sym = c.emoteSym.sym; L.emo.className = 'emo' + (c.emoteSym.sym === '怒' ? ' hot' : ''); }
        L.emo.style.transform = `translate(${x}px,${y - th - 4}px) translate(-50%,-100%)`; L.eon = true;
      } else if (L.eon) { L.emo.style.transform = 'translate(-999px,-999px)'; L.eon = false; }
    }
  }

  // ── 點選 ──
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const setRay = e => { const r = cv.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera); return r; };
  function pickChar(e) {
    const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top; let best = null, bd = 1e9;
    for (const c of W.chars.values()) { if (c._sx < 0) continue; const pxPerM = cv.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360) * c._sd), rad = Math.max(20, pxPerM * 0.45); const d = Math.hypot(mx - c._sx, my - (c._sy + pxPerM * 0.45)); if (d < rad && d < bd) { bd = d; best = c; } }
    return best;
  }
  let down = null;
  cv.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; if (edit.on) editDown(e); }, true);
  cv.addEventListener('pointermove', e => { if (edit.drag) editMove(e); });
  addEventListener('pointerup', e => {
    if (edit.drag) { editUp(e); down = null; return; }
    if (!down || e.target !== cv) { down = null; return; } const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t; down = null;
    if (moved > 7 || dt > 600) return; ui.closePops();
    if (edit.on) { editTap(e); return; }
    const c = pickChar(e); if (c) { setView('char', c); ui.showCard(c); return; }
    setRay(e); const hit = ray.intersectObjects(W.boardsMesh, false)[0]; if (hit) { ui.showBoard(hit.object.userData.board); return; }
  });
  cv.addEventListener('contextmenu', e => e.preventDefault());

  // ── 整修模式 ──
  const edit = { on: false, sel: null, room: null, drag: null }; W.edit = edit;
  const TYPE = { workstation: '辦公桌', ceo_desk: 'CEO 辦公桌', meeting_table: '會議桌', whiteboard: '白板', bookshelf: '書架', cabinet: '資料櫃', sofa: '沙發', armchair: '單人沙發', reserve_seat: '後備座位', beanbag: '懶骨頭', coffee_table: '茶几', side_table: '小圓桌', dining: '餐桌', counter: '流理台', water: '飲水機', fridge: '冰箱', snack: '點心櫃', pingpong: '桌球桌', arcade: '街機', plant: '盆栽', plant_big: '大盆栽', lamp: '立燈', board: '佈告欄', deptsign: '部門名牌', roomsign: '區域名牌', doormat: '門墊', kiosk: '打卡機', bench: '長凳', rug: '地毯' };
  const SWATCH = ['#f3dfc2', '#fde6c4', '#fbe0d4', '#f9d5df', '#e3d8f6', '#d6e6fa', '#d9ecdc', '#fdf1b8', '#e8e2d6'];
  function editBar() {
    const el = $('editBar'); if (!edit.on) { el.hidden = true; return; }
    let h = '';
    if (edit.sel) h = `<span class="nm">${TYPE[edit.sel.f.type] || '家具'}</span><button class="btn" data-e="l">向左轉</button><button class="btn" data-e="r">向右轉</button><button class="btn" data-e="home">放回原位</button>`;
    else if (edit.room) h = `<span class="nm">${edit.room.room.name}地板</span>` + SWATCH.map(c => `<button class="sw${edit.room.color === c ? ' on' : ''}" data-c="${c}" style="background:${c}" aria-label="地板顏色"></button>`).join('');
    else h = `<span class="nm">拖曳家具可移動，點地板可換顏色</span>`;
    el.innerHTML = h + `<button class="btn" data-e="reset">全部復原</button><button class="btn on" data-e="done">完成</button>`; el.hidden = false;
  }
  function toggleEdit() {
    edit.on = !edit.on; edit.sel = null; edit.room = null; $('editBtn').classList.toggle('on', edit.on); W.ring.visible = false;
    if (edit.on) { setView('god'); ui.toast('整修模式：改動會記在這台裝置上'); } editBar();
  }
  function commit() {
    const ov = W.overrides; ov.f = ov.f || {};
    for (const inst of W.furn.values()) { const f = inst.f, h = inst.home; if (f.x !== h.x || f.z !== h.z || f.rot !== h.rot) ov.f[f.id] = [f.x, f.z, f.rot]; else delete ov.f[f.id]; }
    if (!saveOverrides(ov)) ui.toast('這台裝置無法儲存，重新整理後會還原');
    W.respot();
    for (const c of W.chars.values()) { if (!c.spot) continue; const s = W.spots.find(q => q.uid === c.spot.uid); if (!s) { c.spot = null; continue; } c.spot = s; if (c.state === 'sit' && s.seat) c.sitAt(s.seat); }
  }
  function editDown(e) {
    setRay(e); const hit = ray.intersectObjects(W.pickFurn, false)[0]; if (!hit) return;
    const inst = W.furn.get(hit.object.userData.fid); if (!inst) return;
    const pt = new THREE.Vector3(); ray.ray.intersectPlane(ground, pt);
    edit.sel = inst; edit.room = null; edit.drag = { inst, ox: pt.x - inst.f.x, oz: pt.z - inst.f.z, moved: false }; controls.enabled = false; editBar();
    W.ring.visible = true; W.ring.position.set(inst.f.x, 0.09, inst.f.z); const s = Math.max(1.2, (inst.spec.w || 1.4) * 0.9); W.ring.scale.setScalar(s);
  }
  function editMove(e) {
    setRay(e); const pt = new THREE.Vector3(); if (!ray.ray.intersectPlane(ground, pt)) return; const d = edit.drag, f = d.inst.f;
    const nx = Math.round((pt.x - d.ox) * 4) / 4, nz = Math.round((pt.z - d.oz) * 4) / 4;
    const x = Math.max(0.4, Math.min(layout.size.w - 0.4, nx)), z = Math.max(0.4, Math.min(layout.size.d - 0.4, nz));
    if (x !== f.x || z !== f.z) { f.x = x; f.z = z; d.moved = true; W.place(d.inst); W.ring.position.set(x, 0.09, z); }
  }
  function editUp() { const d = edit.drag; edit.drag = null; controls.enabled = true; if (d.moved) commit(); }
  function editTap(e) {
    setRay(e); if (ray.intersectObjects(W.pickFurn, false)[0]) return;
    const hit = ray.intersectObjects([...W.rooms.values()].map(r => r.mesh), false)[0];
    edit.sel = null; W.ring.visible = false; edit.room = hit ? W.rooms.get(hit.object.userData.room) : null; editBar();
  }
  $('editBar').onclick = e => {
    const sw = e.target.closest('[data-c]');
    if (sw && edit.room) { const id = edit.room.room.id; W.overrides.floor = W.overrides.floor || {}; W.overrides.floor[id] = sw.dataset.c; saveOverrides(W.overrides); W.buildRoomFloor(edit.room.room); edit.room = W.rooms.get(id); editBar(); return; }
    const b = e.target.closest('[data-e]'); if (!b) return; const k = b.dataset.e;
    if (k === 'done') { toggleEdit(); return; }
    if (k === 'reset') { clearOverrides(); W.overrides.f = {}; W.overrides.floor = {}; for (const inst of W.furn.values()) { Object.assign(inst.f, inst.home); W.place(inst); } layout.rooms.forEach(W.buildRoomFloor); edit.sel = null; edit.room = null; W.ring.visible = false; commit(); editBar(); ui.toast('已全部復原'); return; }
    const inst = edit.sel; if (!inst) return;
    if (k === 'l') inst.f.rot = (inst.f.rot + 1) % 4; else if (k === 'r') inst.f.rot = (inst.f.rot + 3) % 4; else if (k === 'home') Object.assign(inst.f, inst.home);
    W.place(inst); W.ring.position.set(inst.f.x, 0.09, inst.f.z); commit();
  };

  // ── 主迴圈 ──
  setView(qs.get('view') === 'god' ? 'god' : 'ceo', ceo, true);
  let last = performance.now(), acc = 0, frames = 0, slowFor = 0, first = true;
  function frame(now) {
    requestAnimationFrame(frame);
    const wall = Math.min(0.3, (now - last) / 1000), real = Math.min(0.1, wall); last = now;
    const sim = real * W.speed, n = Math.max(1, Math.ceil(sim / 0.034)), h = sim / n;
    for (let i = 0; i < n; i++) { W.time += h; W.tickTimers(); director.tick(); for (const c of W.chars.values()) c.update(h, W.time); }
    W.updateBlobs(); W.updateScreens(real);
    updateCamera(wall); controls.update();
    renderer.render(scene, camera);
    W.stats.calls = renderer.info.render.calls; W.stats.tris = renderer.info.render.triangles;
    updateLabels(); ui.tickCard();
    acc += real; frames++;
    if (acc >= 1) {
      W.stats.fps = Math.round(frames / acc); acc = 0; frames = 0;
      // 自動降級：太慢就先降解析度，再關陰影（網址帶 q= 時不自動調整）
      if (!pinned) { slowFor = W.stats.fps < 26 ? slowFor + 1 : 0; if (slowFor >= 3) { slowFor = 0; if (pr > 1) { pr = Math.max(1, pr - 0.5); resize(); W.stats.quality = 'auto-' + pr; } else if (renderer.shadowMap.enabled) { renderer.shadowMap.enabled = false; W.sun.castShadow = false; W.stats.quality = 'auto-noshadow'; } } }
    }
    if (first) { first = false; $('loading').hidden = true; W.ready = true; }
  }
  W.shadowDirty(); requestAnimationFrame(frame);
  window.__world = W; W.THREE = THREE; W.setView = setView; W.jumpTo = jumpTo; W.toggleEdit = toggleEdit;
})().catch(e => { console.error(e); const l = document.getElementById('loading'); if (l) l.textContent = '載入失敗：' + e.message; });
