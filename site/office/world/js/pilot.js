// 操控模式：點選角色後，用鍵盤（或手機的虛擬搖桿）親自操控他。
// 為什麼獨立成一個檔：場景（main.js）與角色工廠（office_character.js）各只加幾行掛鉤，
// 輸入、碰撞、跳躍、溝通演出、提示卡、搖桿全部集中在這裡，之後要改操控手感只動這一支。
//
// 狀態分兩層（刻意的）：
//   選取（sel）  點角色就選取：腳下光環、名牌提亮、跳出提示卡；角色照原本的排程繼續做事，資訊卡照舊。
//   接管（engaged）第一次按方向鍵／Space／E／搖桿才接管：原本的排程中止、從椅子上起身，之後完全聽你的。
//   這樣只是「點開來看一下資訊」不會害同事停工；真的要操控才會動到他。
// 結束（Esc／點空白處／點別人）：把角色交還給導演（director.sendHome：從現在的位置走回座位，不瞬移）。
import * as THREE from 'three';

const KEY = 'aiOffice.pilot.tips';                         // 提示卡收起狀態（只記在這台裝置）
const DIRS = { ArrowUp: 'u', KeyW: 'u', ArrowDown: 'd', KeyS: 'd', ArrowLeft: 'l', KeyA: 'l', ArrowRight: 'r', KeyD: 'r' };
const DOUBLE_TAP_MS = 300;                                 // 同一方向 300 毫秒內連按兩次 ＝ 跑步
const TAU = 0.12;                                          // 碰撞往前看幾秒（要大於角色速度追上指令的時間常數 1/14 秒）
const JUMP_V = 4.6, JUMP_V_FLOAT = 3.6, PREP = 0.09;       // 起跳初速（角色單位／秒；重力 G=16 → 約 0.66 公尺高）、起跳前下蹲秒數
const NEAR_HINT = 1.8, NEAR_TALK = 2.1;                    // 顯示「按 E 溝通」的距離、真的能溝通的距離（公尺，中心到中心；放寬一點避免邊緣閃爍）
const BODY_R = 0.72;                                       // 兩個角色中心至少保持的距離（公尺），不穿過別人

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const isMobile = () => matchMedia('(pointer:coarse)').matches || innerWidth <= 640;
function lsGet() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
function lsSet(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* 無痕或封鎖儲存時，收起狀態只在這次有效 */ } }

export function createPilot(W, X) {
  const { cv, camera, ui, setView } = X, D = () => X.director(), layout = W.layout;
  const P = { sel: null, engaged: false, engaging: null, talking: false, near: null, speedNow: 0, run: false };
  const held = new Set(), lastTap = {}, joy = { x: 0, y: 0, on: false, id: -1 };
  let runLatched = false, jumpReq = false, prep = 0, tipsOpen = null, hintO = null;
  const fwd = new THREE.Vector3();

  // ───────── 場景裡的選取光環（腳下，不蓋臉、不跟名牌重疊） ─────────
  const halo = new THREE.Group(); halo.visible = false; halo.renderOrder = 6;
  const mk = (a, b, color, op) => { const m = new THREE.Mesh(a ? new THREE.RingGeometry(a, b, 56) : new THREE.CircleGeometry(b, 56), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: op, depthWrite: false })); m.rotation.x = -Math.PI / 2; m.renderOrder = 6; halo.add(m); return m; };
  const disc = mk(0, 0.62, '#ffcf3a', 0.26), ringA = mk(0.64, 0.78, '#ffb300', 0.95), ringB = mk(0.5, 0.55, '#fff2b0', 0.7);
  W.scene.add(halo);

  // ───────── 介面 ─────────
  const root = $('app'), labels = $('labels');
  const tips = document.createElement('div'); tips.className = 'pt-tips'; tips.hidden = true;
  const hint = document.createElement('div'); hint.className = 'pt-hint'; hint.hidden = true; labels.append(hint);
  const pad = document.createElement('div'); pad.className = 'pt-pad'; pad.hidden = true;
  pad.innerHTML = `<div class="pt-joy" aria-label="虛擬搖桿"><div class="pt-knob"></div></div>
    <div class="pt-btns"><button class="pt-b pt-jump" data-b="jump" aria-label="跳躍">跳</button><button class="pt-b pt-talk" data-b="talk" aria-label="與旁邊的同事溝通">溝通</button><button class="pt-b pt-wave" data-b="wave" aria-label="揮手打招呼">揮手</button></div>`;
  root.append(tips, pad);
  const knob = pad.querySelector('.pt-knob'), joyEl = pad.querySelector('.pt-joy'), talkBtn = pad.querySelector('.pt-talk');

  function renderTips() {
    const c = P.sel; if (!c) { tips.hidden = true; document.body.classList.remove('pt-sel', 'pt-tipsopen'); return; }
    if (tipsOpen == null) { const v = lsGet(); tipsOpen = v == null ? !isMobile() : v === '1'; }
    const mob = isMobile(), nm = esc(c.spec.nick);
    const rows = mob
      ? [['左下搖桿', '移動（推到底＝跑步）'], ['跳', '跳躍'], ['溝通', '與旁邊的同事溝通'], ['揮手', '揮手打招呼'], ['結束', '結束操控']]
      : [['方向鍵／WASD', '移動'], ['連按兩次方向', '跑步'], ['Space', '跳躍'], ['E', '與旁邊的同事溝通'], ['F', '揮手打招呼'], ['Esc', '結束操控']];
    tips.className = 'pt-tips' + (tipsOpen ? '' : ' min');
    tips.innerHTML = `<div class="pt-th"><b>${P.engaged ? '操控中' : '已選取'}：${nm}</b><button class="pt-min" data-t="min" aria-label="${tipsOpen ? '收起操作說明' : '展開操作說明'}" aria-expanded="${tipsOpen}">${tipsOpen ? '收起' : '說明'}</button><button class="pt-end" data-t="end" aria-label="結束操控">結束</button></div>
      <ul class="pt-list">${P.engaged ? '' : `<li class="pt-first">${mob ? '拖動左下搖桿' : '按方向鍵'}開始操控</li>`}${rows.map(([k, v]) => `<li><kbd>${esc(k)}</kbd><span>${esc(v)}</span></li>`).join('')}</ul>`;
    tips.hidden = false; document.body.classList.add('pt-sel'); document.body.classList.toggle('pt-tipsopen', tipsOpen && !mob);
  }
  tips.addEventListener('click', e => {
    const b = e.target.closest('[data-t]'); if (!b) return;
    if (b.dataset.t === 'min') { tipsOpen = !tipsOpen; lsSet(tipsOpen ? '1' : '0'); renderTips(); } else release();
  });

  // ───────── 選取／結束 ─────────
  function select(c) {
    if (!c || c.spec.pet || c.away) return;
    if (P.sel === c) { renderTips(); return; }
    if (P.sel) release();
    P.sel = c; halo.visible = true; P.engaged = false; renderTips(); syncPad();
  }
  function deselect() { if (P.sel) release(); }
  function release(o = {}) {
    const c = P.sel; if (!c) return; if (o.only && o.only !== c) return;
    const was = P.engaged; P.sel = null; P.engaged = false; P.engaging = null; P.near = null; held.clear(); runLatched = false; jumpReq = false; prep = 0; joy.x = joy.y = 0; joy.on = false; knob.style.transform = '';
    halo.visible = false; hint.hidden = true; tips.hidden = true; pad.hidden = true; document.body.classList.remove('pt-sel', 'pt-tipsopen');
    c.inner.jumpPrep = 0; c.piloted = false; c.drive(null);
    if (was && !o.noHome) goHomeAfterLanding(c);
    if (was && !o.silent) ui.toast(`已結束操控${c.spec.nick}，他自己走回座位`);
  }
  async function goHomeAfterLanding(c) {
    for (let i = 0; i < 30 && c.inner.extFall; i++) await W.sleep(0.05);           // 還在空中就等落地，再交還
    if (c.away || c.state === 'held' || c.piloted) return;
    if (!D().sendHome(c)) { const m = D().meeting; if (!(m && m.people.includes(c))) c.busy = false; }
  }
  const inMeeting = c => { const m = D().meeting; return !!(m && m.people.includes(c)); };

  // 第一次輸入才接管：中止原本的排程（同「被拎起來」的處理），再從椅子上起身
  function engage() {
    if (P.engaged) return P.engaging || Promise.resolve(true);
    const c = P.sel; if (!c) return Promise.resolve(false);
    if (inMeeting(c)) { ui.toast('他正在開會，散會後再操控'); return Promise.resolve(false); }
    if (c.away || c.state === 'held') return Promise.resolve(false);
    const seat = c.state === 'sit' && c.spot && c.spot.seat ? c.spot.seat : null, from = { x: c.object3D.position.x, z: c.object3D.position.z };
    D().grabbed(c); c.piloted = true; c.keep = null; c.setAction('idle'); P.engaged = true;
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    renderTips();
    if (seat) {                                                      // 把椅子拉開，站到椅子後方
      const bx = -Math.sin(seat.face), bz = -Math.cos(seat.face);
      const to = W.nav.nearestFree(seat.x + bx * 0.8, seat.z + bz * 0.8, 12) || W.nav.nearestFree(seat.x, seat.z, 12) || from;
      P.engaging = c.walkTo([from, { x: to.x, z: to.z }], { speed: 1.8 }).then(() => { P.engaging = null; return true; });
      return P.engaging;
    }
    c.stop(false); return Promise.resolve(true);
  }

  // ───────── 輸入：鍵盤 ─────────
  const typing = () => { const a = document.activeElement; return !!a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable); };
  addEventListener('keydown', e => {
    if (!P.sel || typing() || e.ctrlKey || e.metaKey || e.altKey) return;
    if (!$('board').hidden) return;                                  // 佈告欄面板開著：方向鍵等不移動角色（Esc 由面板自己關），關掉面板才恢復
    const k = e.code;
    if ((k === 'Space' || k === 'Enter') && document.activeElement && document.activeElement.closest && document.activeElement.closest('#card,#board') && document.activeElement.matches('button,[role=button]')) return;   // 鍵盤操作面板上的按鈕時，Space 不當成跳躍
    if (k === 'Escape') { e.preventDefault(); release(); return; }
    const d = DIRS[k];
    if (d) {
      e.preventDefault();
      if (!e.repeat) {
        const now = e.timeStamp || performance.now();
        if (now - (lastTap[d] ?? -1e9) < DOUBLE_TAP_MS) runLatched = true;      // 300 毫秒內同一方向第二次按下 → 跑步
        lastTap[d] = now; held.add(k);
        engage();
      }
      return;
    }
    if (k === 'Space') { e.preventDefault(); if (!e.repeat) { engage(); jumpReq = true; } return; }
    if (k === 'KeyE') { e.preventDefault(); if (!e.repeat) doTalk(); return; }
    if (k === 'KeyF') { e.preventDefault(); if (!e.repeat) doWave(); return; }
  }, true);
  addEventListener('keyup', e => {
    if (!P.sel) return;
    if (DIRS[e.code] || e.code === 'Space') e.preventDefault();             // 避免剛點過的按鈕被 Space 又觸發一次
    held.delete(e.code); if (![...held].some(c => DIRS[c]) && joy.x === 0 && joy.y === 0) runLatched = false;   // 全部放開 → 回到走路
  }, true);
  addEventListener('blur', () => { held.clear(); runLatched = false; });

  // ───────── 輸入：手機搖桿與按鈕 ─────────
  function syncPad() { pad.hidden = !(P.sel && isMobile()); }
  addEventListener('resize', () => { if (P.sel) { renderTips(); syncPad(); } });
  const R_JOY = 44;
  function joyMove(e) {
    const r = joyEl.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let dx = e.clientX - cx, dy = e.clientY - cy; const m = Math.hypot(dx, dy); if (m > R_JOY) { dx *= R_JOY / m; dy *= R_JOY / m; }
    joy.x = dx / R_JOY; joy.y = -dy / R_JOY; knob.style.transform = `translate(${dx}px,${dy}px)`; joyEl.classList.toggle('run', Math.hypot(joy.x, joy.y) >= 0.9);
  }
  joyEl.addEventListener('pointerdown', e => { e.preventDefault(); joy.on = true; joy.id = e.pointerId; try { joyEl.setPointerCapture(e.pointerId); } catch (x) { /* 合成事件沒有可捕捉的指標，照常處理 */ } joyMove(e); engage(); });
  joyEl.addEventListener('pointermove', e => { if (joy.on && e.pointerId === joy.id) joyMove(e); });
  const joyEnd = e => { if (e.pointerId !== joy.id) return; joy.on = false; joy.x = joy.y = 0; knob.style.transform = ''; joyEl.classList.remove('run'); };
  joyEl.addEventListener('pointerup', joyEnd); joyEl.addEventListener('pointercancel', joyEnd);
  pad.querySelector('.pt-btns').addEventListener('pointerdown', e => {
    const b = e.target.closest('[data-b]'); if (!b) return; e.preventDefault();
    if (b.dataset.b === 'jump') { engage(); jumpReq = true; } else if (b.dataset.b === 'talk') doTalk(); else doWave();
  });

  // ───────── 靠近的同事（互動對象） ─────────
  function candidates(me, r) {
    let best = null, bd = r; const mp = me.object3D.position;
    for (const o of W.chars.values()) {
      if (o === me || o.spec.pet || o.away || !o.object3D.visible || o.state === 'held' || o.piloted || inMeeting(o)) continue;
      const q = o.object3D.position, d = Math.hypot(q.x - mp.x, q.z - mp.z); if (d < bd) { bd = d; best = o; }
    }
    return best;
  }
  // 對方的通用招呼與回話：用他現有的職稱、目前任務、進度卡資料；都沒有就用通用語
  function lineFor(o) {
    let task = o.task; if (!task && ui.progress) { try { const p = ui.progress(o.spec); const cur = p.list.find(x => x.s === 2); task = cur && cur.title; } catch (e) { task = null; } }
    const zh = o.spec.zh || '';
    return task ? `我是${zh}，手上在做「${task}」。` : (zh ? `我是${zh}，有什麼事嗎？` : '你好呀，有什麼事嗎？');
  }
  function greetFor(me, o) { return o.task ? `嗨 ${o.spec.nick}，聽說你在忙「${o.task}」？` : `嗨 ${o.spec.nick}，我是${me.spec.nick}，來打個招呼！`; }

  async function doTalk() {
    if (!P.sel || P.talking) return;
    const ok = await engage(); const me = P.sel; if (!ok || !me) return;
    const o = candidates(me, NEAR_TALK);
    if (!o) { ui.toast('附近沒有可以溝通的同事，先走到他旁邊'); return; }
    P.talking = true;
    const was = { sit: o.state === 'sit' && o.atDesk, base: o._base };
    // 對方停下原本的事（同「被拎起來」：中止排程與路徑），兩人面對面
    o.script = (o.script || 0) + 1; o.job = (o.job || 0) + 1; o.busy = true; o.stop(false); o.setAction('idle');
    const mp = me.object3D.position, op = o.object3D.position; me.faceTo(op.x, op.z); o.faceTo(mp.x, mp.z); o.setAction('listen');
    ui.showCard(o);
    me.setAction('talk', { duration: 2.2 }); me.say(greetFor(me, o), 2.6); await W.sleep(2.7);
    if (P.sel === me) { o.setAction('talk', { duration: 2.2 }); o.say(lineFor(o), 2.8); me.setAction('listen'); }
    await W.sleep(2.9);
    if (P.sel === me) { me.setExpression('happy', 1.2); o.setExpression('happy', 1.2); me.setAction('nod'); }
    await W.sleep(0.9);
    P.talking = false;
    if (o.piloted) return;
    if (was.sit && o.state === 'sit') { o.setAction(was.base || 'type'); o.atDesk = true; o.workAt = W.time + 3; o.busy = false; const s = o.spot && o.spot.seat; if (s) o.faceTo(op.x + Math.sin(s.face), op.z + Math.cos(s.face)); }
    else if (!D().sendHome(o)) { o.busy = false; }
  }

  function doWave() {
    if (!P.sel) return; const me = P.sel;
    me.setAction('wave'); me.say('嗨～', 1.4); me.emote('note', 1.2);
    const o = candidates(me, 3.2); if (!o) return;
    W.sleep(0.5).then(() => {
      if (P.sel !== me || o.piloted || o.state === 'held') return;
      const mp = me.object3D.position; o.faceTo(mp.x, mp.z);
      if (o.state !== 'walk') { o.setAction('wave'); o.say('嗨～', 1.4); } else o.emote('heart', 1.2);
      o.setExpression('happy', 1.4);
    });
  }

  // ───────── 每個模擬步：把輸入變成移動指令 ─────────
  const inBox = (x, z) => x > 0.55 && x < layout.size.w - 0.55 && z > 0.55 && z < layout.size.d - 0.55;
  const free = (x, z) => inBox(x, z) && W.nav.isFree(x, z);
  P.input = () => {                                                  // 鏡頭為準的移動向量（往上＝遠離鏡頭）
    let ix = 0, iy = 0; const ds = new Set([...held].map(k => DIRS[k]));
    if (ds.has('u')) iy++; if (ds.has('d')) iy--; if (ds.has('r')) ix++; if (ds.has('l')) ix--;
    let m = Math.hypot(ix, iy); if (m) { ix /= m; iy /= m; m = 1; }
    const jm = Math.hypot(joy.x, joy.y); if (jm > 0.15) { ix += joy.x; iy += joy.y; m = Math.max(m, jm); }
    const L = Math.hypot(ix, iy); if (L < 0.1) return null;
    camera.getWorldDirection(fwd); let fx = fwd.x, fz = fwd.z; const fl = Math.hypot(fx, fz); if (fl < 1e-3) { fx = 0; fz = -1; } else { fx /= fl; fz /= fl; }
    const rx = -fz, rz = fx;                                         // 鏡頭的右手邊
    const dx = fx * iy + rx * ix, dz = fz * iy + rz * ix, dl = Math.hypot(dx, dz) || 1;
    return { dx: dx / dl, dz: dz / dl, mag: Math.min(1, m), joyOnly: !held.size };
  };
  P.tick = h => {
    const c = P.sel; if (!c || !P.engaged) return;
    // 被別的事接手就自動交還：開會召集、被滑鼠拎起來
    if (inMeeting(c)) { ui.toast('會議開始了，操控自動結束'); release({ noHome: true, silent: true }); return; }
    if (c.state === 'held') { release({ noHome: true, silent: true }); return; }
    if (P.engaging) { c.drive(null); return; }                       // 還在從椅子上起身
    if (c._path) { release({ noHome: true, silent: true }); return; }  // 有人叫他走路（理論上不會發生），不跟導演搶
    if (c.action !== 'idle' && !c._until && !P.talking) c.setAction('idle');   // 排程殘留的動作（剛放下的杯子等）不留在手上
    const ch = c.inner, cfg = ch.cfg, s = c.scale || 1, p = c.object3D.position;
    // 跳躍：起跳前下蹲一下 → 給垂直初速（物理在角色的外部驅動模式，有重力、落地擠壓）
    if (prep > 0) { prep -= h; if (prep <= 0) { ch.jumpPrep = 0; ch.extFall = true; ch.vel.y = cfg.move === 'float' ? JUMP_V_FLOAT : JUMP_V; ch.pos.y = 0.001; ch.sqV += 6; ch.airT = 0.2; ch.feet.forEach(f => { f.planted = false; }); } }
    else if (jumpReq && !ch.extFall && ch.mode === 'normal') { ch.jumpPrep = PREP; prep = PREP; ch.sqV -= 3; }
    jumpReq = false;
    if (P.talking) { c.drive(0, 0); P.speedNow = 0; return; }
    const inp = P.input(); let vx = 0, vz = 0;
    if (inp) {
      P.run = runLatched || (inp.joyOnly && inp.mag >= 0.9);
      const walkV = (cfg.walk || 1.5) * s, runV = (cfg.run || 3.5) * 0.95 * s;
      const sp = P.run ? runV : walkV * (inp.joyOnly ? Math.max(0.3, Math.min(1, inp.mag / 0.85)) : 1);
      vx = inp.dx * sp; vz = inp.dz * sp;
      // 碰撞：先看往前一小段是不是牆或家具（依軸向分開判斷，貼著牆會順著滑）
      // （萬一現在站的格子本身就被擋住，例如剛從椅子起身，只限制在辦公室範圍內，讓他能走出來）
      const tau = TAU, qx = p.x + vx * tau, qz = p.z + vz * tau, ok = free(p.x, p.z) ? free : inBox;
      if (!ok(qx, p.z)) vx = 0;
      if (!ok(p.x + vx * tau, qz)) vz = 0;
      for (const o of W.chars.values()) {                            // 不穿過其他角色：撞到就只保留切線方向
        if (o === c || !o.object3D.visible || o.away) continue;
        const q = o.object3D.position, ex = p.x - q.x, ez = p.z - q.z, d = Math.hypot(ex, ez), pad2 = (o.spec.pet ? 0.5 : BODY_R) * (s > 1 ? 1.1 : 1);
        if (d < pad2 + Math.hypot(vx, vz) * tau && d > 1e-3) { const nx = ex / d, nz = ez / d, toward = -(vx * nx + vz * nz); if (toward > 0) { vx += nx * toward; vz += nz * toward; } }
      }
      if (vx === 0 && vz === 0) { ch.vel.x *= 0.5; ch.vel.z *= 0.5; }
      c.drive(vx, vz, inp.dx, inp.dz);
    } else { P.run = false; c.drive(0, 0); }
    P.speedNow = Math.hypot(vx, vz);
  };

  // ───────── 每一幀：光環、提示、手機按鈕的位置 ─────────
  const card = $('card'), board = $('board'), log = $('log');
  P.frame = (dt, t) => {
    const c = P.sel; if (!c) return;
    const p = c.object3D.position, k = c.scale || 1, pulse = 0.5 + 0.5 * Math.sin(t * 4.2);
    halo.position.set(p.x, 0.1, p.z); halo.scale.setScalar(Math.max(0.6, k));
    ringA.scale.setScalar(1 + 0.07 * pulse); ringA.material.opacity = 0.7 + 0.3 * pulse; ringB.scale.setScalar(1 - 0.05 * pulse); disc.material.opacity = 0.2 + 0.1 * pulse;
    halo.visible = !c.away && c.object3D.visible;
    if (W.ring.visible) W.ring.visible = false;                      // 舊的細環讓位，不要兩圈疊在一起
    // 「按 E 溝通」：頭上提示（貼在對方名牌上方，演出中或對方正在說話就先收起，避免跟泡泡重疊）
    const o = P.engaged && !P.engaging && !P.talking ? candidates(c, P.near ? NEAR_TALK : NEAR_HINT) : null;
    P.near = o; talkBtn.classList.toggle('ready', !!o);
    if (o && o._sx > -900 && !o.speech) {
      hint.hidden = false; if (hintO !== o) { hintO = o; hint.textContent = isMobile() ? '點「溝通」鈕' : '按 E 溝通'; }
      hint.style.transform = `translate(${Math.round(o._sx)}px,${Math.round(o._sy - (o._sd < 15 ? 38 : 24) - 10)}px) translate(-50%,-100%)`;
    } else hint.hidden = true;
    // 手機：搖桿與按鈕要在底部面板的上方，不被卡片蓋住
    if (!pad.hidden) { let lift = 0; for (const el of [card, board, log]) if (!el.hidden && !el.classList.contains('mini')) lift = Math.max(lift, el.offsetHeight + 8); document.documentElement.style.setProperty('--lift', lift + 'px'); }
    else if (P.sel && isMobile()) syncPad();
  };
  P.releaseIf = c => release({ only: c, noHome: true, silent: true });   // 換造型要重建角色時，先放開舊的
  P.select = select; P.deselect = deselect; P.release = release; P.engage = engage; P.talk = doTalk; P.wave = doWave; P.halo = halo; P.tipsEl = tips; P.hintEl = hint; P.padEl = pad;
  return P;
}
