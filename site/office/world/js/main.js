// 進入點：載入資料 → 蓋場景 → 放角色 → 鏡頭、標籤、點選、整修 → 主迴圈。
import * as THREE from 'three';
import { OrbitControls } from '../../vendor/OrbitControls.js';
import { createWorld, saveOverrides, clearOverrides } from './world.js';
import { createDirector } from './director.js';
import { createPilot } from './pilot.js';
import { createCamHint } from './camhint.js';
import { createDaytime } from './daytime.js';
import { createUI } from './ui.js';
import { FX } from '../../play/fx.js';
import { SPECIES, canWear } from '../../play/species.js';

const $ = id => document.getElementById(id);
const qs = new URLSearchParams(location.search);
const J = u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });

// 角色模組：預設用正式角色（play/office_character.js）；world.html?char=./character.js 可換回膠囊佔位角色（只供除錯）
async function loadCharacterModule() { const p = qs.get('char') || '../../play/office_character.js'; const m = await import(p); if (typeof m.createCharacter !== 'function') throw new Error('角色模組必須匯出 createCharacter'); return m; }

(async function boot() {
  const [layout, org, demo, meet, roster, charMod] = await Promise.all([J('world/cfg/layout.json'), J('world/cfg/org.json'), J('world/cfg/demo.json'), J('world/cfg/meeting_demo.json'), J('world/cfg/roster.json'), loadCharacterModule()]);
  const coarse = matchMedia('(pointer:coarse)').matches || innerWidth < 720;
  let quality = qs.get('q') || (coarse ? 'low' : 'high'); const pinned = qs.has('q');
  const cv = $('cv'), W = createWorld(cv, layout, org, quality), { renderer, scene, camera } = W;
  W.stats = { calls: 0, tris: 0, fps: 0, walks: 0, noPath: 0, interrupted: 0, quality };
  let pr = Math.min(devicePixelRatio || 1, quality === 'low' ? 1.5 : 2); if (qs.get('pr')) pr = Math.max(0.25, +qs.get('pr') || 1);   // 網址可指定解析度倍率（測試或很慢的裝置用）
  function resize() { const w = cv.clientWidth, h = cv.clientHeight; renderer.setPixelRatio(pr); renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
  addEventListener('resize', resize); resize();

  // ── 角色 ──
  // 手機自動降級：幾何面數、臉部貼圖、遠近分級的距離都調低
  if (charMod.configure) charMod.configure(quality === 'low' ? { detail: 0.4, faceSize: 128, lodNear: 9, lodFar: 22, fxDist: 16 } : { detail: 0.55, faceSize: 256, lodNear: 14, lodFar: 30, fxDist: 26 });
  const fx = new FX(scene); W.fx = fx;
  // 使用者在網頁上改的名字、暱稱、物種、配色、配件（只存在這台裝置）
  const RKEY = 'aiOffice.roster.v1'; let edits = {}; try { edits = JSON.parse(localStorage.getItem(RKEY) || '{}') || {}; } catch (e) { edits = {}; }
  W.roster = { base: roster, edits, save() { try { localStorage.setItem(RKEY, JSON.stringify(edits)); return true; } catch (e) { return false; } } };
  // 組出一位成員的完整規格：編制（原職稱不可改）＋固定外觀＋使用者的修改；戴不了識別證的物種改用同色圍巾或蝴蝶結
  function makeSpec(b) {
    const look = b.pet ? b : (b.isCeo ? roster.ceo : roster.members[b.id]) || {}, ed = edits[b.id] || {}, sp = { ...b, ...look, ...ed, id: b.id, zh: b.zh, nick0: b.nick0 ?? b.nick };
    const cfg = SPECIES[sp.species]; let acc = [...(sp.acc || [])];
    if (cfg && acc.includes('badge') && !canWear(cfg, 'badge')) { const alt = ['scarf', 'bow', 'hat'].find(a => canWear(cfg, a) && !acc.includes(a)); if (alt) acc.push(alt); }
    if (cfg && acc.includes('tie') && !canWear(cfg, 'tie') && !acc.includes('hat') && canWear(cfg, 'hat')) acc.push('hat');
    sp.acc = acc; return sp;
  }
  W.makeSpec = makeSpec;
  const env = {
    camera, fx, followed: null, bounds: { x0: 0.6, x1: layout.size.w - 0.6, z0: 0.6, z1: layout.size.d + 3 },
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
  const bases = [{ ...org.ceo, isCeo: true }]; for (const d of org.departments) for (const m of d.members) bases.push({ ...m, dept: d.id, color: d.color });
  const baseOf = new Map(bases.map(b => [b.id, b]));
  const labels = $('labels');
  function setTag(c) { const s = c.spec, L = c._lab; L.tag.firstChild.textContent = s.nick; L.tag.lastChild.textContent = s.pet ? s.zh : s.isCeo ? s.zh : `${s.id}・${s.zh}`; }
  function addLabel(c) {
    const tag = document.createElement('div'); tag.className = 'tag'; tag.innerHTML = `<b></b><span></span>`;
    const bub = document.createElement('div'); bub.className = 'bub';
    labels.append(tag, bub); c._lab = { tag, bub, cls: '', txt: '', on: false, bon: false }; setTag(c);
  }
  for (const b of bases) {
    const s = makeSpec(b), c = charMod.createCharacter(s, env); W.chars.set(s.id, c); scene.add(c.object3D); c.onDrop = q => director.dropped(q);
    const seat = W.spots.find(q => q.name === 'seat:' + s.id);
    if (seat) { seat.taken = s.id; c.spot = seat; c.sitAt(seat.seat, { instant: true }); c.atDesk = true; c.setAction('type'); c.workAt = 1 + Math.random() * 9; } else c.standAt(20, 26, 0);
    addLabel(c);
  }
  // 寵物：迷你版的物種，在主人附近自由走動
  W.pets = [];
  for (const p of roster.pets || []) {
    const s = makeSpec({ ...p, nick: p.name, pet: true }), c = charMod.createCharacter(s, env); c.onDrop = q => director.dropped(q); c.busyUntil = 0; scene.add(c.object3D);
    const o = W.chars.get(p.owner), op = o ? o.object3D.position : { x: 20, z: 26 }, f = W.nav.nearestFree(op.x + 1.1, op.z + 0.9, 12) || { x: 20, z: 26 }; c.standAt(f.x, f.z, Math.random() * 6);
    addLabel(c); W.pets.push(c);
  }
  let everyone = [...W.chars.values(), ...W.pets];
  // 改了物種、配色、配件之後，原地換一個新的身體
  W.rebuildChar = id => {
    const old = W.chars.get(id); if (!old) return null; if (director.meeting && director.meeting.people.includes(old)) return null;
    W.pilot && W.pilot.releaseIf(old);   // 正在被操控的角色要換身體：先放開（新身體由下面的邏輯送回座位）
    const p = old.object3D.position.clone(), st = old.state, keep = { spot: old.spot, atDesk: old.atDesk, away: old.away, _lab: old._lab, workAt: old.workAt, task: old.task };
    old.script = (old.script || 0) + 1; old.job = (old.job || 0) + 1; old.stop(false); const vis = old.object3D.visible; old.dispose();
    const c = charMod.createCharacter(makeSpec(baseOf.get(id)), env); Object.assign(c, keep); c.onDrop = q => director.dropped(q); W.chars.set(id, c); scene.add(c.object3D); c.setVisible(vis);
    if (keep.spot && keep.spot.seat && st === 'sit') { c.sitAt(keep.spot.seat, { instant: true }); c.setAction(keep.atDesk ? 'type' : 'idle'); } else { const f = W.nav.isReach(p.x, p.z) ? p : (W.nav.nearestFree(p.x, p.z, 24) || p); c.standAt(f.x, f.z, old.heading); c.busy = false; if (!c.away) director.sendHome(c); }
    setTag(c); if (view.char === old) { view.char = c; env.followed = c; } everyone = [...W.chars.values(), ...W.pets]; return c;
  };
  const ceo = W.chars.get('ceo');

  // ── 鏡頭 ──
  const controls = new OrbitControls(camera, cv); controls.enableDamping = true; controls.dampingFactor = 0.14; controls.screenSpacePanning = false; controls.maxPolarAngle = 1.32; controls.zoomSpeed = 1.1;
  const view = { mode: 'ceo', char: ceo, tween: null, lastUser: -10 }; W.view = view; W.controls = controls;
  controls.addEventListener('start', () => { view.lastUser = performance.now() / 1000; if (view.tween) view.tween = null; });
  const CENTER = new THREE.Vector3(layout.size.w / 2, 0, layout.size.d / 2 + 0.6), v3 = new THREE.Vector3(), v3b = new THREE.Vector3(), v3c = new THREE.Vector3();
  const portrait = () => cv.clientWidth < cv.clientHeight;
  // 任何視角（CEO 視角、俯瞰、跟隨角色）滑鼠操作都一樣：左鍵拖曳旋轉、右鍵或 Shift＋左鍵拖曳平移、滾輪縮放；
  // 觸控單指旋轉、雙指平移＋縮放。距離範圍固定：近不穿牆（≥3 公尺）、遠不離開辦公室太多。
  function modeControls() {
    controls.enablePan = true; controls.enableRotate = true; controls.enableZoom = true; controls.minDistance = 3; controls.maxDistance = 110;
    controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
    controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  }
  const LIM = { x0: -6, x1: layout.size.w + 6, z0: -6, z1: layout.size.d + 10 };    // 注視點可以平移到的範圍（辦公室外圍多留一圈）
  function clampCam() {
    const t = controls.target, cx = Math.max(LIM.x0, Math.min(LIM.x1, t.x)), cz = Math.max(LIM.z0, Math.min(LIM.z1, t.z)), cy = Math.max(0, Math.min(3, t.y));
    camera.position.x += cx - t.x; camera.position.z += cz - t.z; camera.position.y += cy - t.y; t.set(cx, cy, cz);
    if (camera.position.y < 0.8) camera.position.y = 0.8;                            // 不穿到地板下
  }
  let userActive = 0;      // 使用者正在拖曳（放開後再算 0.6 秒，讓阻尼的餘動也算在內）
  controls.addEventListener('start', () => { userActive = 1e9; }); controls.addEventListener('end', () => { userActive = performance.now() + 600; });
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
    const sitV = c.state === 'sit', k = (c.scale || 1) > 1 ? 1.12 : 1, h0 = c.spot && c.spot.seat && sitV ? c.spot.seat.face : c.heading, back = (portrait() ? 5.6 : 4.4) * (sitV ? 1.25 : 1) * k, up = ((portrait() ? 3.4 : 2.5) + (sitV ? 1.3 : 0)) * k, cp = c.object3D.position;
    let best = null;
    const seatedC = c.state === 'sit';
    // 坐著的人從斜後方看（不被椅背擋住）；兩側挑「看出去是辦公室而不是牆」的那一側
    const toC = (da) => { const h = h0 + da; return Math.sin(h) * (CENTER.x - cp.x) + Math.cos(h) * (CENTER.z - cp.z); }, sg = toC(0.72) >= toC(-0.72) ? 1 : -1;
    for (const da of (seatedC ? [0.72 * sg, -0.72 * sg, 1.25 * sg, -1.25 * sg, 0.3, 1.9, -1.9, Math.PI] : [0, 0.6, -0.6, 1.15, -1.15, 1.8, -1.8, Math.PI])) {
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
    const t = (target || CENTER).clone(), d = dist || (portrait() ? 84 : 52), pol = 0.62;
    return { t, p: new THREE.Vector3(t.x, t.y + d * Math.cos(pol), t.z + d * Math.sin(pol)), fov: 38 };
  }
  function tweenTo(pose, sec = 0.95) { view.tween = { p0: camera.position.clone(), t0: controls.target.clone(), f0: camera.fov, pose, t: 0, sec, off: pose.p.clone().sub(pose.t) }; }
  function setView(mode, c, instant) {
    if (mode === 'ceo') c = ceo; if (mode === 'char' && !c) c = view.char || ceo;
    view.mode = mode; view.char = mode === 'god' ? null : c; env.followed = view.char; modeControls(); view.detached = false; view.pull = 0; view.last = null;
    const pose = mode === 'god' ? godPose() : followPose(c);
    if (instant) { camera.position.copy(pose.p); controls.target.copy(pose.t); camera.fov = pose.fov; camera.updateProjectionMatrix(); view.tween = null; } else tweenTo(pose);
    ui.setViewUI(mode, c); W.ring.visible = mode !== 'god'; W.ring.scale.setScalar(Math.max(0.6, (c && c.scale) || 1));
    if (mode !== 'char') ui.hideCard();
  }
  // 手機直式：上方有工具列，注視點往後牆移一點，後牆的佈告欄才會落在工具列下面、點得到
  function jumpTo(roomId) {
    const r = layout.rooms.find(q => q.id === roomId); if (!r) return;
    view.mode = 'god'; view.char = null; env.followed = null; modeControls(); ui.setViewUI('god'); W.ring.visible = false;
    tweenTo(godPose(new THREE.Vector3(r.x + r.w / 2, 0, portrait() ? r.z + r.d * 0.3 : r.z + r.d / 2 + 0.4), Math.max(r.w, r.d * 1.5) * (portrait() ? 2.2 : 0.82) + 5));
  }
  // 跟隨的做法：不是每幀把注視點「拉」到角色身上，而是角色走多少、鏡頭就跟著平移多少（保留使用者拖出來的方位、距離、平移量）。
  // 使用者手動平移之後暫停跟隨（view.detached），直到角色「再次移動」超過 0.25 公尺才自動接回（平順拉回）；或按「回到角色」鈕。
  // 只旋轉、縮放不會暫停跟隨。移到定位之後鏡頭的控制權就完全給滑鼠，不會被拉回固定位置。
  view.detached = false; view.pull = 0; view.last = null; view.dpos = null;
  view.recenter = () => { view.detached = false; view.pull = 1; if (view.tween) view.tween = null; };
  function updateCamera(dt) {
    const tw = view.tween;
    if (tw) {
      tw.t += dt / tw.sec; const k = Math.min(1, tw.t), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      if (view.char && !view.detached) { charTarget(view.char, tw.pose.t); tw.pose.p.copy(tw.pose.t).add(tw.off); }
      camera.position.lerpVectors(tw.p0, tw.pose.p, e); controls.target.lerpVectors(tw.t0, tw.pose.t, e);
      if (tw.pose.fov && tw.pose.fov !== tw.f0) { camera.fov = tw.f0 + (tw.pose.fov - tw.f0) * e; camera.updateProjectionMatrix(); }
      if (k >= 1) { view.tween = null; view.last = null; } return;
    }
    if (view.char) {
      const c = view.char, cp = c.object3D.position;
      if (!view.last) view.last = { x: cp.x, z: cp.z };
      const mx = cp.x - view.last.x, mz = cp.z - view.last.z; view.last.x = cp.x; view.last.z = cp.z;
      if (view.detached && view.dpos && Math.hypot(cp.x - view.dpos.x, cp.z - view.dpos.z) > 0.25) { view.detached = false; view.pull = 0.9; }
      if (!view.detached) {
        if (view.pull > 0) {                    // 剛接回：平順拉向角色
          view.pull -= dt; const fx = cp.x - camera.position.x, fz = cp.z - camera.position.z, fl = Math.hypot(fx, fz) || 1, kk = Math.min(1, dt * 2); ahead.x += (fx / fl * AHEAD - ahead.x) * kk; ahead.z += (fz / fl * AHEAD - ahead.z) * kk;
          charTarget(c, v3); v3b.subVectors(v3, controls.target).multiplyScalar(Math.min(1, dt * 6)); controls.target.add(v3b); camera.position.add(v3b);
        } else { controls.target.x += mx; controls.target.z += mz; camera.position.x += mx; camera.position.z += mz; }
        // 角色走路時，鏡頭慢慢繞回他身後（使用者剛拖過就先不動）
        if (c.state === 'walk' && !grab && performance.now() / 1000 - view.lastUser > 2.5) {
          const ox = camera.position.x - controls.target.x, oz = camera.position.z - controls.target.z, a = Math.atan2(ox, oz), want = c.heading + Math.PI;
          let d = Math.atan2(Math.sin(want - a), Math.cos(want - a)); d = Math.max(-dt * 0.9, Math.min(dt * 0.9, d));
          const cs = Math.cos(d), sn = Math.sin(d); camera.position.x = controls.target.x + ox * cs + oz * sn; camera.position.z = controls.target.z - ox * sn + oz * cs;
        }
      }
      if (W.ring.visible) { W.ring.position.set(cp.x, 0.08, cp.z); W.ring.material.opacity = c.state === 'sit' ? 0.45 : 0.9; }
    }
  }
  // 雙擊（雙點）地面：鏡頭平順移過去（保留目前的方位與距離），並暫停跟隨
  function moveCamTo(x, z) {
    const t = new THREE.Vector3(Math.max(LIM.x0, Math.min(LIM.x1, x)), controls.target.y, Math.max(LIM.z0, Math.min(LIM.z1, z)));
    view.detached = !!view.char; if (view.char) view.dpos = { x: view.char.object3D.position.x, z: view.char.object3D.position.z };
    tweenTo({ t, p: t.clone().add(camera.position.clone().sub(controls.target)), fov: camera.fov }, 0.8);
  }

  // ── 導演與介面 ──
  let director;
  const ui = createUI(W, demo, {
    setView: (m, c) => setView(m, c), jumpTo, cardClosed() { }, director: () => director, rebuild: id => W.rebuildChar(id), setTag: c => setTag(c),
    ambient: () => director.ambient, setSpeed: s => { W.speed = s; },
    toggleEdit: () => toggleEdit(),
    runDemo(k) {
      if (k === 'ambient') { director.ambient = !director.ambient; return; }
      if (k === 'meeting') { if (director.running) { ui.toast('會議示範正在進行中'); return; } director.play(meet.events); return; }
      if (k === 'clockout') { director.clockOut(6); ui.toast('下班：幾位同事從大門離開'); return; }
      if (k === 'clockin') { director.clockIn(6); ui.toast('上班：同事從大門進來'); return; }
      if (k === 'report') { const c = director.pickIdle(); if (!c) { ui.toast('目前沒有空閒的同事'); return; } director.play([{ type: 'task.done', who: c.spec.id, report_to: 'ceo', summary: '這批做完了，請過目。', reply: '收到，辛苦了。' }]); ui.toast(c.spec.nick + '拿著文件去找 CEO'); return; }
      const c = director.routine(null, k); ui.toast(c ? '已派一位同事去' + { coffee: '倒咖啡', lookup: '查資料', rest: '休息', play: '遊樂區', snack: '吃點心', chat: '找人聊天' }[k] : '目前沒有空閒的同事');
    }
  });
  director = createDirector(W, ui); W.director = director; W.ui = ui; W.meet = meet; director.pets = W.pets;
  if (qs.get('ambient') === '0') director.ambient = false;
  // 鍵盤／觸控操控（點選角色後）：輸入、碰撞、溝通演出都在 pilot.js，這裡只掛鉤
  const pilot = createPilot(W, { cv, camera, controls, ui, setView, director: () => director }); W.pilot = pilot; const camHint = createCamHint(view);
  const daytime = createDaytime(W, {}); W.daytime = daytime;   // 天色依台北時間連續變化

  // ── 名牌、泡泡 ──
  const pv = new THREE.Vector3(), bubs = [];
  function updateLabels() {
    const w = cv.clientWidth, h = cv.clientHeight; bubs.length = 0;
    for (const c of everyone) {
      const L = c._lab, p = c.object3D.position; let on = c.object3D.visible;
      if (on) { pv.set(p.x, c.height + (c.lift || 0) + 0.12, p.z); var dist = pv.distanceTo(camera.position); pv.project(camera); if (pv.z > 1 || Math.abs(pv.x) > 1.08 || Math.abs(pv.y) > 1.2 || (view.mode !== 'god' && dist > 17 && !c.speech) || (c.spec.pet && dist > 40)) on = false; }
      if (!on) { if (L.on) { L.tag.style.transform = L.bub.style.transform = 'translate(-999px,-999px)'; L.on = L.bon = false; L.txt = ''; } c._sx = -999; continue; }
      const x = Math.round((pv.x + 1) / 2 * w), y = Math.round((1 - pv.y) / 2 * h); c._sx = x; c._sy = y; c._sd = dist;
      const cls = 'tag' + (c.spec.lead || c.spec.isCeo ? ' lead' : '') + (c.spec.pet ? ' pet' : '') + (view.char === c ? ' me' : '') + (pilot.sel === c ? ' sel' : '') + (dist < 15 ? '' : dist < 34 ? ' mid' : ' far'); if (cls !== L.cls) { L.tag.className = cls; L.cls = cls; }
      L.tag.style.transform = `translate(${x}px,${y}px) translate(-50%,-100%)`; L.on = true;
      const th = dist < 15 ? 38 : dist < 34 ? 24 : 18;
      if (c.speech) {
        if (L.txt !== c.speech.text) { L.bub.textContent = c.speech.text; L.txt = c.speech.text; L.bub.className = 'bub ' + (c.speech.kind || ''); L.bw = L.bub.offsetWidth; L.bh = L.bub.offsetHeight; }
        // 泡泡不超出畫面左右，也不蓋到最上面的工具列
        bubs.push({ L, x: Math.max(L.bw / 2 + 6, Math.min(w - L.bw / 2 - 6, x)), y: Math.max(L.bh + (w < 640 ? 100 : 60), y - th - 10), w: L.bw, h: L.bh });
      } else if (L.bon) { L.bub.style.transform = 'translate(-999px,-999px)'; L.bon = false; L.txt = ''; }
    }
    // 泡泡互相不重疊：由下往上排，撞到就往上讓
    bubs.sort((a, b) => b.y - a.y);
    for (let i = 0; i < bubs.length; i++) {
      const a = bubs[i];
      for (let k = 0; k < 4; k++) { let hit = false; for (let j = 0; j < i; j++) { const b = bubs[j]; if (Math.abs(a.x - b.x) < (a.w + b.w) / 2 + 4 && a.y > b.y - b.h - 4 && a.y - a.h < b.y + 4) { a.y = b.y - b.h - 8; hit = true; } } if (!hit) break; }
      const top = a.h + (w < 640 ? 100 : 60); if (a.y < top) { a.y = top; for (let j = 0; j < i; j++) { const b = bubs[j]; if (Math.abs(a.x - b.x) < (a.w + b.w) / 2 + 4 && a.y > b.y - b.h - 4 && a.y - a.h < b.y + 4) a.x = a.x < b.x ? Math.max(a.w / 2 + 6, b.x - (a.w + b.w) / 2 - 8) : Math.min(w - a.w / 2 - 6, b.x + (a.w + b.w) / 2 + 8); } }
      a.L.bub.style.transform = `translate(${Math.round(a.x)}px,${Math.round(a.y)}px) translate(-50%,-100%)`; a.L.bon = true; a.L.rect = a;
    }
  }

  // ── 點選 ──
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const setRay = e => { const r = cv.getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera); return r; };
  function pickChar(e) {
    const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top; let best = null, bd = 1e9;
    for (const c of everyone) { if (c._sx < 0) continue; const k = c.scale || 1, pxPerM = cv.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360) * c._sd), rad = Math.max(18, pxPerM * 0.45 * k); const d = Math.hypot(mx - c._sx, my - (c._sy + pxPerM * 0.45 * k)); if (d < rad && d < bd) { bd = d; best = c; } }
    return best;
  }
  // 拎起來：按住角色拖曳；放開後掉下來（甩得快會滾出去），再自己走回座位
  const lastTap = { t: 0, x: 0, y: 0 }; let deselT = 0;
  let down = null, grab = null; const hold = new THREE.Plane(new THREE.Vector3(0, 1, 0), -1.05), hp = new THREE.Vector3();
  cv.addEventListener('pointerdown', e => {
    down = { x: e.clientX, y: e.clientY, t: performance.now(), c: null };
    if (edit.on) { editDown(e); return; }
    const c = pickChar(e); if (c && c.grab && !c.away) { down.c = c; controls.enabled = false; }
  }, true);
  cv.addEventListener('pointermove', e => {
    if (edit.drag) { editMove(e); return; }
    if (down && down.c && !grab && Math.hypot(e.clientX - down.x, e.clientY - down.y) > 9) { grab = down.c; director.grabbed(grab); grab.grab(); ui.closePops(); }
    if (grab) { setRay(e); if (ray.ray.intersectPlane(hold, hp)) grab.dragTo(hp.x, 1.05, hp.z); }
  });
  const endGrab = () => { if (grab) { grab.release(); grab = null; } controls.enabled = true; };
  addEventListener('pointercancel', () => { endGrab(); down = null; });
  addEventListener('pointerup', e => {
    if (edit.drag) { editUp(e); down = null; return; }
    if (grab) { endGrab(); down = null; return; }
    if (down && down.c) controls.enabled = true;
    if (!down || e.target !== cv) { down = null; return; } const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t; down = null;
    if (moved > 5 || dt > 250) return; ui.closePops();   // 位移超過約 5 像素或按住超過約 250 毫秒＝拖曳，不是點一下：不取消選取、不關資訊卡
    if (edit.on) { editTap(e); return; }
    const c = pickChar(e); if (c) { clearTimeout(deselT); lastTap.t = 0; if (c.spec.pet) { pilot.deselect(); ui.showPet(c); return; } setView('char', c); ui.showCard(c); pilot.select(c); return; }
    setRay(e); const hit = ray.intersectObjects(W.boardsMesh, false)[0]; if (hit) { clearTimeout(deselT); lastTap.t = 0; ui.showBoard(hit.object.userData.board); return; }   // 操控中點佈告欄只開面板，不結束操控
    // 點空白處：取消選取；但 0.3 秒內再點一下（雙點地面）是「鏡頭移過去」，不取消
    const now = performance.now(), gp = new THREE.Vector3();
    if (now - lastTap.t < 320 && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 30 && ray.ray.intersectPlane(ground, gp)) { clearTimeout(deselT); lastTap.t = 0; moveCamTo(gp.x, gp.z); return; }
    lastTap.t = now; lastTap.x = e.clientX; lastTap.y = e.clientY; clearTimeout(deselT); deselT = setTimeout(() => pilot.deselect(), 330);
  });
  cv.addEventListener('contextmenu', e => e.preventDefault());
  // 佈告欄：滑鼠停上去游標變手指、板子微微提亮（用一塊半透明的外框蓋在板子上，不動共用材質）
  const bh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({ color: '#fff3c4', transparent: true, opacity: 0.28, depthWrite: false })); bh.visible = false; bh.renderOrder = 7; scene.add(bh); W.boardHover = bh;
  let hoverBoard = null, hoverT = 0; const bbox = new THREE.Box3(), bsz = new THREE.Vector3(), bct = new THREE.Vector3();
  cv.addEventListener('pointermove', e => {
    if (e.pointerType === 'touch' || grab || edit.on || (e.buttons & 7)) return; const t = performance.now(); if (t - hoverT < 60) return; hoverT = t;
    setRay(e); const hit = ray.intersectObjects(W.boardsMesh, false)[0], m = hit ? hit.object : null; if (m === hoverBoard) return; hoverBoard = m;
    cv.style.cursor = m ? 'pointer' : ''; bh.visible = !!m;
    if (m) { bbox.setFromObject(m); bbox.getSize(bsz); bbox.getCenter(bct); bh.position.copy(bct); bh.scale.set(bsz.x + 0.06, bsz.y + 0.06, bsz.z + 0.06); }
  });

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
    W.respot(); W.glowRebuild && W.glowRebuild();
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
  setView(qs.get('view') === 'ceo' ? 'ceo' : 'god', ceo, true);   // 預設進場是俯視（看得到整間辦公室）；網址帶 view=ceo 才從 CEO 視角開始
  let last = performance.now(), acc = 0, frames = 0, slowFor = 0, first = true, shift = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    const wall = Math.max(0.004, Math.min(0.3, (now - last) / 1000)), real = Math.min(0.1, wall); last = now;   // max(0.004,…)：第一幀的 rAF 時間戳可能比 last 早，負 dt 會讓臉部表情彈簧發散、之後一連串畫臉例外；也不能是 0（慣性要除以 dt，0/0 會讓身體變成 NaN 而消失）
    const sim = real * W.speed, n = Math.max(1, Math.ceil(sim / 0.034)), h = sim / n;
    for (let i = 0; i < n; i++) { W.time += h; try { W.tickTimers(); pilot.tick(h); director.tick(); for (const c of everyone) c.update(h, W.time); fx.update(h, W.time); } catch (e) { if (!W.loopErr) console.error('主迴圈例外', e); W.loopErr = (W.loopErr || 0) + 1; } }
    W.updateBlobs(); W.updateScreens(real);
    updateCamera(wall); const tg0 = v3c.copy(controls.target); controls.update();
    // 使用者拖曳平移（注視點被他移動）→ 暫停跟隨
    if (view.char && !view.detached && !view.tween && performance.now() < userActive && controls.target.distanceToSquared(tg0) > 1e-4) { view.detached = true; view.dpos = { x: view.char.object3D.position.x, z: view.char.object3D.position.z }; }
    clampCam();
    { // 手機開著底部面板時，把畫面往上推，角色不會被面板蓋住
      const want = portrait() && (!$('card').hidden || !$('board').hidden || (!$('log').hidden && !$('log').classList.contains('mini'))) ? 0.2 : 0;
      if (Math.abs(want - shift) > 0.002) { shift += (want - shift) * Math.min(1, wall * 6); const w = cv.clientWidth, h = cv.clientHeight; camera.setViewOffset(w, h, 0, shift * h, w, h); }
      else if (shift !== want) { shift = want; if (!want) camera.clearViewOffset(); }
    }
    renderer.render(scene, camera);
    W.stats.calls = renderer.info.render.calls; W.stats.tris = renderer.info.render.triangles;
    updateLabels(); pilot.frame(real, W.time); camHint.tick(); daytime.tick(); ui.tickCard();
    acc += real; frames++;
    if (acc >= 1) {
      W.stats.fps = Math.round(frames / acc); acc = 0; frames = 0;
      // 自動降級：太慢就先降解析度，再關陰影（網址帶 q= 時不自動調整）
      if (!pinned) { slowFor = W.stats.fps < 26 ? slowFor + 1 : 0; if (slowFor >= 3) { slowFor = 0; if (pr > 1) { pr = Math.max(1, pr - 0.5); resize(); W.stats.quality = 'auto-' + pr; } else if (renderer.shadowMap.enabled) { renderer.shadowMap.enabled = false; W.sun.castShadow = false; W.stats.quality = 'auto-noshadow'; } } }
    }
    if (first) { first = false; $('loading').hidden = true; W.ready = true; }
  }
  W.shadowDirty(); requestAnimationFrame(frame);
  W.godAt = (x, z, d) => { view.mode = 'god'; view.char = null; modeControls(); ui.setViewUI('god'); W.ring.visible = false; tweenTo(godPose(new THREE.Vector3(x, 0, z), d)); };
  window.__world = W; W.THREE = THREE; W.setView = setView; W.jumpTo = jumpTo; W.toggleEdit = toggleEdit;
})().catch(e => { console.error(e); const l = document.getElementById('loading'); if (l) l.textContent = '載入失敗：' + e.message; });
