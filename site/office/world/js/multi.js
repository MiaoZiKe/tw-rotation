// 多選（擁有者 11-14：「按著 Ctrl 可以多選不同角色。」）
//
// 為什麼獨立成一個檔：多選會碰到選取（pilot）、點擊判定（main）、資訊卡（ui）、開除（hr）、導演排程（director），
// 全部集中在這裡，其他檔只加「掛鉤」（main.js 每處一行、pilot.js 一行提示），避免跟同時在改辦公室頁的人撞檔。
//
// 狀態分三種（刻意的）：
//   單選   0～1 位：照舊走 pilot.select（光環、面向鏡頭、資訊卡、操控），多選不介入。
//   群組   ≥2 位（手機「多選模式」開著時 ≥1 位）：pilot 不選任何人，改由這裡畫選取光環、顯示群組面板（取代單人資訊卡）。
//   操控   群組裡按方向鍵（或面板的「操控第一位」）：第一位被選的人交給 pilot 操控，其餘的人排成小隊伍跟在後面走。
// 規則：Ctrl／⌘＋點＝加入或移出；不按 Ctrl 點＝只選那一位；點空白處（既有的 330 毫秒延遲）或 Esc＝全部取消；
//       Ctrl＋在背景拖曳＝拉框（不按 Ctrl 的拖曳仍是平移鏡頭，這裡完全不攔）。
import * as THREE from 'three';

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const isMobile = () => matchMedia('(pointer:coarse)').matches || innerWidth <= 640;
const DIRS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyW', 'KeyA', 'KeyS', 'KeyD']);
const LONG_MS = 450, MOVE_PX = 8;          // 手機長按多久進入多選模式、手指移動超過幾像素就不算長按
const GAP = 0.95, TRAIL_STEP = 0.2;       // 隊伍：前後兩人沿著足跡相隔幾公尺、足跡取樣間距
const BODY = 0.72;                         // 同 pilot.js：兩個角色中心至少相隔的距離
const DWELL = 24;                          // 集合開會後待多久（模擬秒）自動散會回座位

export function createMulti(W, X) {
  const { cv, camera, ui, pilot, setView } = X, D = () => X.director(), layout = W.layout;
  const M = { list: [], mode: false, driving: false, leader: null, mobileBar: false };
  const inMeeting = c => { const m = D().meeting; return !!(m && m.people.includes(c)); };
  const okChar = c => c && !c.spec.pet && !c.jobless && !c.away && c.object3D.visible;
  const typing = () => { const a = document.activeElement; return !!a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable); };

  // ───────── 選取光環：全部合成兩個實例網格（一個圓盤＋一個細環），選 47 位也只多 2 次繪製 ─────────
  const MAXI = 64;
  const discG = new THREE.CircleGeometry(0.6, 40), ringG = new THREE.RingGeometry(0.64, 0.78, 40); discG.rotateX(-Math.PI / 2); ringG.rotateX(-Math.PI / 2);
  const discM = new THREE.InstancedMesh(discG, new THREE.MeshBasicMaterial({ color: '#ffcf3a', transparent: true, opacity: 0.26, depthWrite: false }), MAXI);
  const ringM = new THREE.InstancedMesh(ringG, new THREE.MeshBasicMaterial({ color: '#ffb300', transparent: true, opacity: 0.95, depthWrite: false }), MAXI);
  for (const m of [discM, ringM]) { m.frustumCulled = false; m.renderOrder = 6; m.count = 0; m.visible = false; W.scene.add(m); }
  const mat = new THREE.Matrix4(), q0 = new THREE.Quaternion(), sc = new THREE.Vector3(), ps = new THREE.Vector3();
  M.halo = { disc: discM, ring: ringM };

  // ───────── 群組面板（獨立的新元素，不動 ui.js 的單人資訊卡） ─────────
  const root = $('app'), panel = document.createElement('aside'); panel.className = 'panel grp'; panel.id = 'grp'; panel.hidden = true; root.append(panel);
  const box = document.createElement('div'); box.id = 'mBox'; box.hidden = true; root.append(box);                // 框選的半透明矩形
  const bar = document.createElement('div'); bar.id = 'mBar'; bar.hidden = true; root.append(bar);              // 手機：多選模式切換鈕與「完成」
  let sumT = 0, lastKey = '';
  const avatar = c => { try { if (ui.ava) return ui.ava(c.spec); } catch (e) { /* 縮圖畫不出來就用色塊 */ } return `<div class="ava" style="background:${esc(c.spec.color || '#ffb057')}"></div>`; };
  const sums = () => { let a = 0, b = 0, d = 0; for (const c of M.list) { try { const p = ui.progress(c.spec); a += p.nDoing; b += p.nTodo; d += p.nDone; } catch (e) { /* 沒進度資料就不計 */ } } return { doing: a, todo: b, done: d }; };
  function renderPanel() {
    const n = M.list.length, s = sums(), drv = M.driving, mob = isMobile();
    const key = M.list.map(c => c.spec.id).join(',') + '|' + drv + '|' + mob + M.mode + '|' + s.doing + s.todo + s.done; if (key === lastKey && !panel.hidden) return; lastKey = key;
    panel.className = 'panel grp' + (drv ? ' drv' : '');
    panel.innerHTML = `<button class="x" data-g="clear" aria-label="取消全部選取">×</button>
      <div class="hd"><div><b id="grpN">已選 ${n} 位</b>${drv ? '<span class="tag2">操控中</span>' : ''}<p>${mob ? (drv ? '搖桿移動第一位，其他人排隊跟著走；按 × 結束' : (M.mode ? '點角色加入或移出，按「完成」結束' : '點「多選」可再加人；按 × 全部取消')) : (drv ? '方向鍵移動第一位，其他人排隊跟著走；Esc 結束' : 'Ctrl＋點可加入或移出；Esc 全部取消')}</p></div></div>
      <div class="grp-sum" id="grpSum"><span class="k2"><b>${s.doing}</b>進行中</span><span class="k1"><b>${s.todo}</b>未完成</span><span class="k3"><b>${s.done}</b>已完成</span></div>
      <ul class="grp-list" id="grpList">${M.list.map((c, i) => `<li><button class="grp-who" data-who="${esc(c.spec.id)}" aria-label="單獨看${esc(c.spec.nick)}的資訊卡">${avatar(c)}<b>${esc(c.spec.nick)}</b><span>${i === 0 ? '第一位・' : ''}${esc(c.spec.zh || '')}</span></button><button class="grp-rm" data-rm="${esc(c.spec.id)}" aria-label="把${esc(c.spec.nick)}移出選取">✕</button></li>`).join('')}</ul>
      <div class="grp-acts">
        <button class="btn" data-g="home">一起回座位</button><button class="btn" data-g="rest">一起去休息</button><button class="btn" data-g="meet">集合開會</button>
        <button class="btn" data-g="pet">全部摸頭</button><button class="btn" data-g="wave">全部揮手</button><button class="btn" data-g="lead">操控第一位</button>
        <button class="btn dng" data-g="fire" title="開除選取的人：會先跳確認框，列出名單與任務轉交">開除選取的人</button></div>`;
  }
  panel.addEventListener('click', e => {
    let b;
    if ((b = e.target.closest('[data-rm]'))) { const c = W.chars.get(b.dataset.rm); if (c) remove(c); return; }
    if ((b = e.target.closest('[data-who]'))) { const c = W.chars.get(b.dataset.who); if (c) only(c); return; }
    if ((b = e.target.closest('[data-g]'))) { if (e.detail) queueMicrotask(() => b.blur()); act(b.dataset.g); }
  });

  // ───────── 選取集合的增減 ─────────
  // 同「點角色」的既有做法；但 Ctrl＋點是在「挑人」，鏡頭不能飛走（不然畫面上其他人的位置全變了、下一個要點的人找不到），所以只有明確要看他時才移鏡頭
  function single(c, fly) { if (fly) setView('char', c); ui.showCard(c); pilot.select(c); }
  function refresh() {
    const n = M.list.length, grp = n >= 2 || (M.mode && n >= 1);
    if (!grp) {
      lastKey = ''; panel.hidden = true; M.driving = false; M.leader = null;
      if (n === 1) { const c = M.list[0]; M.list = []; single(c); }
      syncBar(); return;
    }
    if (pilot.sel && !M.driving) pilot.deselect();
    ui.hideCard(); const bd = $('board'); if (bd) bd.hidden = true;
    renderPanel(); panel.hidden = false; syncBar();
  }
  function add(c) { adopt(); if (!okChar(c) || M.list.includes(c)) return false; stopDrive(); M.list.push(c); refresh(); return true; }
  function remove(c) { const i = M.list.indexOf(c); if (i < 0) return; stopDrive(); M.list.splice(i, 1); if (!M.list.length && !M.mode) { clear(); return; } refresh(); }
  function toggle(c) { if (M.list.includes(c)) remove(c); else add(c); }
  function only(c) { clear(true); single(c, true); }
  // 把目前的單選也算進來：Ctrl＋點第二位時，第一位是 pilot.sel
  function adopt() { const s = pilot.sel; if (s && !M.list.length && okChar(s)) M.list.push(s); }
  function clear(silent) {
    stopDrive(true); M.list = []; M.mode = false; lastKey = ''; panel.hidden = true; gatherTok++; syncBar();
    if (!silent && pilot.sel) pilot.deselect();
  }
  const prune = () => { const n = M.list.length; M.list = M.list.filter(okChar); if (M.list.length !== n) { if (M.driving) stopDrive(); if (!M.list.length && !M.mode) clear(); else refresh(); } };

  // ───────── 滑鼠：Ctrl＋點、Ctrl＋拖曳框選（掛在 main 的第一個 pointerdown 與 pointerup 裡） ─────────
  const drag = { on: false, id: -1, x0: 0, y0: 0, x1: 0, y1: 0, moved: false };
  let lp = null, swallow = false;                              // 手機長按偵測、長按那一下的放開不要再當成點擊
  const inCv = e => e.target === cv;
  M.down = e => {
    swallow = false;
    if (e.button !== 0 || !inCv(e) || X.isEdit() || (W.pov && W.pov.on())) return false;
    if (e.ctrlKey || e.metaKey) {
      drag.on = true; drag.id = e.pointerId; drag.x0 = drag.x1 = e.clientX; drag.y0 = drag.y1 = e.clientY; drag.moved = false;
      e.stopImmediatePropagation(); e.preventDefault(); try { cv.setPointerCapture(e.pointerId); } catch (x) { /* 合成事件沒有可捕捉的指標 */ }
      return true;
    }
    if (e.pointerType === 'touch' && isMobile()) {              // 手機：在角色身上長按不動 → 進入多選模式
      const c = X.pick(e); clearTimeout(lp && lp.t); lp = null;
      if (c && okChar(c)) { const L = lp = { c, x: e.clientX, y: e.clientY, id: e.pointerId, t: 0, ts: e.timeStamp }; L.t = setTimeout(() => { if (lp !== L) return; lp = null; swallow = true; enterMode(c); if (navigator.vibrate) { try { navigator.vibrate(18); } catch (x) { /* 不支援就算了 */ } } }, LONG_MS); }
    }
    return false;
  };
  addEventListener('pointermove', e => {
    if (lp && e.pointerId === lp.id && Math.hypot(e.clientX - lp.x, e.clientY - lp.y) > MOVE_PX) { clearTimeout(lp.t); lp = null; }
    if (!drag.on || e.pointerId !== drag.id) return;
    drag.x1 = e.clientX; drag.y1 = e.clientY;
    if (!drag.moved && Math.hypot(drag.x1 - drag.x0, drag.y1 - drag.y0) > 5) drag.moved = true;
    if (drag.moved) { const l = Math.min(drag.x0, drag.x1), t = Math.min(drag.y0, drag.y1); box.hidden = false; box.style.cssText = `left:${l}px;top:${t}px;width:${Math.abs(drag.x1 - drag.x0)}px;height:${Math.abs(drag.y1 - drag.y0)}px`; }
  }, true);
  const upAll = e => {
    if (lp && e.pointerId === lp.id) {       // 畫面很卡時計時器會晚響：放開時再用「事件時間」補判一次（同 main 的長按判斷）
      const L = lp; clearTimeout(L.t); lp = null;
      if (e.type === 'pointerup' && e.timeStamp - L.ts >= LONG_MS) { swallow = true; enterMode(L.c); }
    }
    if (!drag.on || e.pointerId !== drag.id) return;
    drag.on = false; box.hidden = true; try { cv.releasePointerCapture(e.pointerId); } catch (x) { /* 沒捕捉就算了 */ }
    if (e.type === 'pointercancel') return;
    if (!drag.moved) { const c = X.pick(e); if (c && okChar(c)) { if (!M.list.length) adopt(); toggle(c); } return; }     // Ctrl＋點（沒拖）
    boxSelect(Math.min(drag.x0, drag.x1), Math.min(drag.y0, drag.y1), Math.max(drag.x0, drag.x1), Math.max(drag.y0, drag.y1));
  };
  addEventListener('pointerup', upAll, true); addEventListener('pointercancel', upAll, true);
  function boxSelect(l, t, r, b) {
    const rc = cv.getBoundingClientRect(); let n = 0; adopt();
    for (const c of W.chars.values()) {
      if (!okChar(c) || c._sx < 0 || M.list.includes(c)) continue;
      const k = c.scale || 1, pxPerM = cv.clientHeight / (2 * Math.tan(camera.fov * Math.PI / 360) * c._sd), x = rc.left + c._sx, y = rc.top + c._sy + pxPerM * 0.45 * k;   // 身體中心的螢幕位置（同 pickChar）
      if (x >= l && x <= r && y >= t && y <= b) { stopDrive(); M.list.push(c); n++; }
    }
    refresh(); if (n) ui.toast(`框選加入 ${n} 位，共 ${M.list.length} 位`);
  }
  // main 的 pointerup 點到角色時先問這裡：回 true ＝ 這次點擊已處理（Ctrl／多選模式），回 false ＝ 照舊單選（並先清掉群組）
  M.tap = (e, c) => {
    if (swallow) { swallow = false; return true; }
    if (e.ctrlKey || e.metaKey) { if (okChar(c)) { if (!M.list.length) adopt(); toggle(c); } return true; }     // 保險：Ctrl＋點若是走到這裡
    if (M.mode) { if (okChar(c)) toggle(c); return true; }
    if (M.list.length) clear(true);
    return false;
  };
  // 空白處的點擊：手機多選模式中不取消選取（要按「完成」）
  M.bgTap = () => M.mode;

  // ───────── 手機：多選模式切換鈕 ─────────
  function enterMode(c) { adopt(); M.mode = true; if (c && !M.list.includes(c)) { stopDrive(); M.list.push(c); } if (c && M.list.includes(c) && M.list.length === 1) { /* 只有他一位：模式開著，面板照樣顯示「已選 1 位」 */ } refresh(); }
  function exitMode() { M.mode = false; const n = M.list.length; if (n >= 2) refresh(); else if (n === 1) refresh(); else clear(); ui.toast(n >= 2 ? `已選 ${n} 位` : '多選結束'); }
  function syncBar() {
    const show = isMobile() && (M.mode || M.list.length >= 2 || !!pilot.sel); bar.hidden = !show; if (!show) return;
    if (M.mode) bar.innerHTML = `<span id="mBarN">多選中：已選 ${M.list.length} 位</span><button class="mb-done" data-m="done" aria-label="完成多選">完成</button>`;
    else bar.innerHTML = `<button class="mb-on" data-m="on" aria-label="開啟多選模式（之後點角色就是加入或移出）">多選</button>`;
  }
  bar.addEventListener('click', e => { const b = e.target.closest('[data-m]'); if (!b) return; if (b.dataset.m === 'done') exitMode(); else { adopt(); M.mode = true; refresh(); ui.toast('多選模式：點角色加入或移出'); } });
  addEventListener('resize', syncBar);

  // ───────── 群組動作 ─────────
  let gatherTok = 0;
  const people = () => M.list.filter(c => okChar(c) && c.state !== 'held');
  function release1(c) { if (c.piloted) { c.piloted = false; c.drive(null); } }
  function act(k) {
    prune(); if (!M.list.length) return;
    if (k === 'clear') { clear(); return; }
    if (k === 'fire') { if (W.hr) W.hr.ask(M.list.map(c => c.spec.id), '選取的人'); return; }
    if (k === 'lead') { lead(); return; }
    if (k === 'home' || k === 'rest' || k === 'meet') { stopDrive(); gatherTok++; }
    const ps = people(), idle = ps.filter(c => !inMeeting(c)); let n = 0;
    if (k === 'home') { for (const c of idle) { release1(c); if (D().sendHome(c)) n++; } ui.toast(n ? `${n} 位一起走回座位` : '他們正在開會'); }
    else if (k === 'rest') { for (const c of idle) { release1(c); D().routine(c.spec.id, 'rest'); n++; } ui.toast(`${n} 位一起去休息區`); }
    else if (k === 'meet') gather(idle);
    else if (k === 'pet') { for (const c of ps) { c.pet(2.4); n++; } ui.toast(`摸摸 ${n} 位，大家都很開心`); }
    else if (k === 'wave') { for (const c of ps) { c.setAction('wave'); c.say('嗨～', 1.4); c.emote('note', 1.2); n++; } ui.toast(`${n} 位一起揮手`); }
  }
  // 集合開會：走到會議室（有座位的先坐，其餘站在桌子周圍，彼此保持間距），待一陣子自動散會回座位
  async function gather(ps) {
    if (!ps.length) { ui.toast('他們正在開會'); return; }
    const tok = ++gatherTok, room = layout.rooms.find(r => r.id === 'meeting'); if (!room) return;
    const cx = room.x + room.w / 2, cz = room.z + room.d / 2, seats = W.findSpots('meet').filter(s => !s.taken), used = [];
    const standPt = () => {
      for (let r = 1.3; r < 6; r += 0.75) for (let a = 0; a < 6.283; a += 0.5) {
        const x = cx + Math.cos(a) * r * 1.25, z = cz + Math.sin(a) * r;
        if (x < room.x + 0.8 || x > room.x + room.w - 0.8 || z < room.z + 0.8 || z > room.z + room.d - 0.8) continue;
        if (!W.nav.isFree(x, z) || used.some(u => Math.hypot(u.x - x, u.z - z) < 0.9)) continue;
        used.push({ x, z }); return { x, z };
      }
      const f = W.nav.nearestFree(cx, cz, 12) || { x: cx, z: cz }; used.push(f); return f;
    };
    ui.toast(`${ps.length} 位到會議室集合`);
    let said = false;
    await Promise.all(ps.map(async (c, i) => {
      release1(c); D().grabbed(c); c.busy = true; c.meetTok = tok;
      await W.sleep(i * 0.12); if (tok !== gatherTok) return;
      c.setAction(i % 3 === 1 ? 'carry' : 'idle');
      if (i < seats.length) { const ok = await D().goTo(c, seats[i], { speed: 2.8 }); if (ok && tok === gatherTok) c.setAction('listen'); return; }
      const t = standPt(), p = { x: c.object3D.position.x, z: c.object3D.position.z }, path = W.nav.findPath(p, t) || [p, t];
      const ok = await c.walkTo(path, { speed: 2.8 }); if (tok !== gatherTok) return;
      if (!ok) c.standAt(t.x, t.z, 0);
      c.standAt(c.object3D.position.x, c.object3D.position.z, Math.atan2(cx - c.object3D.position.x, cz - c.object3D.position.z)); c.setAction('listen');
      if (!said) { said = true; c.say('集合開會～', 2); }
    }));
    if (tok !== gatherTok) return;
    await W.sleep(DWELL); if (tok !== gatherTok) return;
    ui.toast('散會，大家回座位'); for (const c of ps) if (c.meetTok === tok && !c.piloted && !inMeeting(c)) D().sendHome(c);
  }

  // ───────── 群組操控：第一位交給 pilot 操控，其餘排隊跟著走 ─────────
  const trail = []; let foll = [], tookOver = false;
  function lead() {
    prune(); if (M.list.length < 1) return false;
    if (M.driving) return true;
    const c = M.list[0]; if (inMeeting(c)) { ui.toast('他正在開會，散會後再操控'); return false; }
    gatherTok++; M.driving = true; M.leader = c; tookOver = false; trail.length = 0; foll = [];
    setView('char', c); pilot.select(c); renderPanel(); panel.hidden = false; syncBar(); return true;
  }
  function stopDrive(silent) {
    if (!M.driving) return; M.driving = false; const l = M.leader; M.leader = null; lastKey = '';
    for (const c of foll) { release1(c); if (c.state !== 'held' && !inMeeting(c)) D().sendHome(c); }          // 小隊伍解散：跟隨的人自己走回座位
    foll = []; tookOver = false; trail.length = 0;
    if (pilot.sel && pilot.sel === l) pilot.release({ silent: !!silent });      // 領頭的那位由 pilot 交還導演
    if (!silent && M.list.length) renderPanel();
  }
  // 跟隨者接管：同 pilot.engage（先中止原排程；坐著的人先從椅子起身站到旁邊）
  function takeOver(c) {
    const seat = c.state === 'sit' && c.spot && c.spot.seat ? c.spot.seat : null, from = { x: c.object3D.position.x, z: c.object3D.position.z };
    D().grabbed(c); c.piloted = true; c.keep = null; c.setAction('idle'); c.fol = { rise: 0, path: null, pt: 0 };
    if (seat) {
      const bx = -Math.sin(seat.face), bz = -Math.cos(seat.face), to = W.nav.nearestFree(seat.x + bx * 0.8, seat.z + bz * 0.8, 12) || from;
      c.fol.rise = 1; c.walkTo([from, { x: to.x, z: to.z }], { speed: 2 }).then(() => { if (c.fol) c.fol.rise = 0; });
      W.sleep(5).then(() => { if (c.fol && c.fol.rise && c._path) { c.stop(false); c.fol.rise = 0; } });
    }
  }
  const free = (x, z) => x > 0.55 && x < layout.size.w - 0.55 && z > 0.55 && z < layout.size.d - 0.55 && W.nav.isFree(x, z);
  function followTick(c, i, tx, tz, h, stopR) {
    const f = c.fol; if (!f || f.rise) { c.drive(null); return; }
    if (c.state === 'held' || inMeeting(c)) { release1(c); foll = foll.filter(q => q !== c); return; }
    const ch = c.inner, cfg = ch.cfg, s = c.scale || 1, p = c.object3D.position;
    if (c.action !== 'idle' && !c._until) c.setAction('idle');
    ch.idleT = 0; if (ch.mode === 'sit' || ch.mode === 'sleep') ch.wake();
    if (tx == null) { c.drive(0, 0); return; }
    const dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz);
    if (d < (stopR || 0.2)) { c.drive(0, 0); return; }
    // 直線被擋就改走尋路（每 0.8 秒重算一次，用編號錯開，避免全員同一幀算路徑）
    let wx = tx, wz = tz, ux = dx / d, uz = dz / d;
    if (!free(p.x + ux * 0.45, p.z + uz * 0.45) || f.path) {
      f.pt -= h; if (f.pt <= 0 || !f.path) { f.pt = 0.8 + (i % 8) * 0.05; f.path = W.nav.findPath({ x: p.x, z: p.z }, { x: tx, z: tz }); if (f.path && f.path.length > 1) f.path.shift(); }
      while (f.path && f.path.length > 1 && Math.hypot(f.path[0].x - p.x, f.path[0].z - p.z) < 0.3) f.path.shift();
      if (f.path && f.path.length) { wx = f.path[0].x; wz = f.path[0].z; const l = Math.hypot(wx - p.x, wz - p.z) || 1; ux = (wx - p.x) / l; uz = (wz - p.z) / l; }
      if (free(p.x + (tx - p.x) / d * 0.45, p.z + (tz - p.z) / d * 0.45) && d < 2) f.path = null;
    }
    const walkV = (cfg.walk || 1.5) * s, runV = (cfg.run || 3.5) * 0.95 * s, sp = Math.min(runV, Math.max(walkV * 0.5, d * 1.6));
    let vx = ux * sp, vz = uz * sp;
    for (const o of W.chars.values()) {                         // 不穿過別人（含領頭的人）：撞到就只保留切線方向
      if (o === c || !o.object3D.visible || o.away) continue;
      const q = o.object3D.position, ex = p.x - q.x, ez = p.z - q.z, dd = Math.hypot(ex, ez), pad = (o.spec.pet ? 0.5 : BODY) * (s > 1 ? 1.1 : 1);
      if (dd < pad + Math.hypot(vx, vz) * 0.12 && dd > 1e-3) { const nx = ex / dd, nz = ez / dd, toward = -(vx * nx + vz * nz); if (toward > 0) { vx += nx * toward; vz += nz * toward; } }
    }
    if (!free(p.x + vx * 0.12, p.z)) vx = 0; if (!free(p.x + vx * 0.12, p.z + vz * 0.12)) vz = 0;
    c.drive(vx, vz, vx || ux, vz || uz);
  }
  M.tick = h => {
    if (!M.driving) return;
    const l = M.leader;
    if (!l || pilot.sel !== l || !okChar(l)) { stopDrive(); if (M.list.length) clear(true); return; }       // 領頭的人被別的事接手／按了 Esc → 整隊結束
    if (!pilot.engaged) return;
    if (!tookOver) { tookOver = true; foll = M.list.filter(c => c !== l && okChar(c) && !inMeeting(c) && c.state !== 'held'); foll.forEach(takeOver); trail.length = 0; trail.push({ x: l.object3D.position.x, z: l.object3D.position.z }); }
    const p = l.object3D.position, hd = trail[0];
    if (!hd || Math.hypot(p.x - hd.x, p.z - hd.z) >= TRAIL_STEP) { trail.unshift({ x: p.x, z: p.z }); if (trail.length > 400) trail.length = 400; }
    for (let i = 0; i < foll.length; i++) {
      const c = foll[i]; let want = (i + 1) * GAP, acc = 0, tx = null, tz = null, a = { x: p.x, z: p.z };
      for (const q of trail) { const seg = Math.hypot(q.x - a.x, q.z - a.z); if (acc + seg >= want) { const r = seg ? (want - acc) / seg : 0; tx = a.x + (q.x - a.x) * r; tz = a.z + (q.z - a.z) * r; break; } acc += seg; a = q; }
      // 領頭的人才剛起步、足跡還不夠長：先聚到足跡最早的那一點附近，一個挨一個排（到達半徑隨順位放大，不會全部疊在同一點）
      if (tx == null) followTick(c, i, a.x, a.z, h, 0.6 + 0.55 * i); else followTick(c, i, tx, tz, h);
    }
  };

  // ───────── 鍵盤：群組裡按方向鍵＝操控第一位；Esc＝全部取消 ─────────
  addEventListener('keydown', e => {
    if (!M.list.length || typing() || document.body.classList.contains('dlg-open')) return;
    if (e.code === 'Escape') { if (W.pov && W.pov.on() && W.pov.st !== 'out') return; if (M.driving || !pilot.sel) { e.preventDefault(); clear(); } return; }   // 此時 pilot 的 Esc 處理已先跑完（領頭的人已交還）
    if (e._multi || e.ctrlKey || e.metaKey || e.altKey || !DIRS.has(e.code) || M.driving || M.list.length < 2 || !$('board').hidden) return;
    if (!lead()) return; e.preventDefault();
    const ev = new KeyboardEvent('keydown', { code: e.code, key: e.key, bubbles: true, cancelable: true }); ev._multi = true; dispatchEvent(ev);                // 領頭的人已被 pilot 選取，把這個按鍵重送一次讓 pilot 接手
  }, true);

  // ───────── 每一幀：光環位置、面板彙總 ─────────
  const pf = pilot.frame, pt = pilot.tick;
  pilot.tick = h => { pt(h); M.tick(h); };
  pilot.frame = (dt, t) => {
    pf(dt, t);
    let n = 0; const pulse = 0.5 + 0.5 * Math.sin(t * 4.2);
    if (M.list.length && !panel.hidden) {
      for (const c of M.list) {
        if (!okChar(c) || pilot.sel === c || n >= MAXI || (W.pov && W.pov.hides(c))) continue;
        const p = c.object3D.position, k = Math.max(0.6, c.scale || 1);
        ps.set(p.x, 0.1, p.z); sc.set(k, 1, k); mat.compose(ps, q0, sc); discM.setMatrixAt(n, mat);
        sc.set(k * (1 + 0.07 * pulse), 1, k * (1 + 0.07 * pulse)); mat.compose(ps, q0, sc); ringM.setMatrixAt(n, mat); n++;
      }
      discM.material.opacity = 0.2 + 0.1 * pulse; ringM.material.opacity = 0.7 + 0.3 * pulse;
      discM.instanceMatrix.needsUpdate = ringM.instanceMatrix.needsUpdate = true;
    }
    discM.count = ringM.count = n; discM.visible = ringM.visible = n > 0;
    if (!panel.hidden) {
      sumT -= dt; if (sumT <= 0) { sumT = 1.2; prune(); if (M.list.length) renderPanel(); }
      if (isMobile() && !pilot.padEl.hidden) { const cur = parseFloat(document.documentElement.style.getPropertyValue('--lift')) || 0; document.documentElement.style.setProperty('--lift', Math.max(cur, panel.offsetHeight + 8) + 'px'); }
    }
    if (M.mode || M.list.length >= 2 || pilot.sel) { if (isMobile() && bar.hidden) syncBar(); } else if (!bar.hidden) syncBar();
    const nb = $('mBarN'); if (nb) { const t2 = `多選中：已選 ${M.list.length} 位`; if (nb.textContent !== t2) nb.textContent = t2; }
  };

  // 「?」說明：把多選的用法接在最後面（ui.js 的說明清單不動）
  { const ul = $('helpPop') && $('helpPop').querySelector('ul'); if (ul) ul.insertAdjacentHTML('beforeend', '<li>多選：按住 Ctrl（Mac 是 ⌘）點角色＝加入或移出；Ctrl＋在背景拖曳＝拉框一次選多位；不按 Ctrl 點角色＝只選那一位；點空白處或 Esc＝全部取消。選了 2 位以上會出現群組面板：一起回座位、一起去休息、集合開會、全部摸頭、全部揮手、開除選取的人；按方向鍵可操控第一位，其他人排隊跟著走。手機：長按角色出現「多選」，之後點角色加入或移出，按「完成」結束。</li>'); }

  M.add = add; M.remove = remove; M.toggle = toggle; M.clear = clear; M.has = c => M.list.includes(c) && !panel.hidden; M.only = only; M.act = act; M.lead = lead; M.panelEl = panel; M.barEl = bar; M.boxEl = box;
  M.followers = () => foll.slice();
  return M;
}
