// 員工運動場（2026-11-15）：辦公室大門外小路西邊的羽毛球、籃球、網球、撞球、游泳池。
// 擁有者原話：「旁邊幫我設定員工運動場……每位員工都是可以直接操作、可使用，羽毛球就可以找個員工跟他打，籃球也是，
//   並且都需要符合世界物理效果，像是當我把員工拿去燒再放到泳池他會消火。」
//
// 怎麼玩
//   · 點選一位員工、用方向鍵操控他，走到場地裡按 E → 開始；畫面下方出現「找一位同事一起打」：點另一位員工邀請他（他會跑過來），
//     或按 E／Enter／「自動找同事」＝找最近閒著的人。羽毛球／網球：方向鍵走位、空白鍵揮拍（靠近球才打得到）、方向鍵順便決定落點；
//     籃球：按住空白鍵蓄力、放開投籃（對準綠色刻度）；撞球：滑鼠（手指）拖曳瞄準與力道；游泳：走進泳池（或在池邊按 E 跳進去）。Esc 結束。
//   · 沒人操控時，閒著的員工偶爾會兩兩自己去打球（或下去游泳）；網址加 ?ambient=0 或 ?sports=0 可關。
//   · 泳池：被丟進來會濺水、浮起來；燒著的人立刻熄火；身體濕一陣子（滴水）、短時間不會著火。見 sports_water.js、fire.js 的 F.extinguish。
// 事件（W.emit，情緒由 mind.js 處理）：splashed、left_pool、sport_start、sport_end、sport_score（每一分一則＋結束時勝負各一則，含對手 id）。
// 檔案：sports_build.js（場地模型）、sports_water.js（水）、sports_games.js（玩法與球的物理）、本檔（組裝、輸入、介面、閒著的員工去運動）。
import { THREE } from './kit.js';
import { mergeGeometries } from '../../vendor/BufferGeometryUtils.js';
import { LAY, VENUES, inRect, buildSports } from './sports_build.js';
import { createWater } from './sports_water.js';
import { DT, createRacket, createBasket, createBilliards } from './sports_games.js';

const clamp = (x, a, b) => Math.max(a, Math.min(b, x)), rnd = (a, b) => a + Math.random() * (b - a), pick = a => a[Math.floor(Math.random() * a.length)];
const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
const ARROWS = { ArrowUp: 'u', KeyW: 'u', ArrowDown: 'd', KeyS: 'd', ArrowLeft: 'l', KeyA: 'l', ArrowRight: 'r', KeyD: 'r' };
const ZH = { badminton: '羽毛球', tennis: '網球', basketball: '籃球', billiards: '撞球', pool: '游泳' };

// ── 輸入：在模組載入時就掛在 window 的捕捉階段（比 pilot.js 早），才能在「運動中」攔下 E／空白鍵／Esc，不讓操控層拿去跳躍或溝通
let API = null; const held = new Set();
const typing = () => { const a = document.activeElement; return !!a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable); };
addEventListener('keydown', e => { if (!API) return; if (ARROWS[e.code]) held.add(e.code); if (typing() || e.ctrlKey || e.metaKey || e.altKey || document.body.classList.contains('dlg-open')) return; API.key(e, true); }, true);
addEventListener('keyup', e => { if (!API) return; held.delete(e.code); if (typing()) return; API.key(e, false); }, true);
addEventListener('blur', () => held.clear());
for (const t of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel']) addEventListener(t, e => { if (API) API.ptr(e, t); }, true);

export function mountSports(W, X = {}) {
  const qs = new URLSearchParams(location.search); if (qs.get('sports') === '0') return null;
  const ui = X.ui || { toast() { } }, D = () => W.director || X.director, scene = W.scene, nav = W.nav;
  const S = { sess: null, steps: 0, venues: VENUES, LAY, stats: { sessions: 0, ambient: 0, points: 0 }, ambientOn: qs.get('ambient') !== '0', log: [] };
  W.sports = S;
  // ───────── 場地、水、nav ─────────
  const B = buildSports(W); S.build = B;
  W.layout.walkAreas = [...(W.layout.walkAreas || []), { x0: 0.7, x1: 19.6, z0: 31.6, z1: 48.6, note: '員工運動場（sports_build.js）' }];
  W.respot(); if (W.glowRebuild) W.glowRebuild(); if (W.outLightRebuild) W.outLightRebuild();
  const water = createWater(W); S.water = water;
  const allChars = () => [...W.chars.values(), ...(W.pets || []), ...(W.extras || [])];
  const idOf = c => c.spec.id, nick = c => c.spec.nick;
  const say = (t, sec = 2) => { S.lastSay = t; if (S.sess && S.sess.me) S.sess.me.say && S.sess.me.say(t, sec); };

  // ───────── 球與球桌的畫面 ─────────
  const V = {};
  { // 羽毛球（尖端朝前）、網球、籃球、陰影
    const cone = new THREE.ConeGeometry(0.11, 0.26, 10, 1, true), cork = new THREE.SphereGeometry(0.048, 10, 8); cork.translate(0, 0.15, 0);
    const paint = (g, hex) => { const c = new THREE.Color(hex), n = g.attributes.position.count, a = new Float32Array(n * 3); for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; } g.setAttribute('color', new THREE.BufferAttribute(a, 3)); return g; };
    const sh = mergeGeometries([paint(cone.toNonIndexed(), '#fffaf2'), paint(cork.toNonIndexed(), '#f28b82')], false);
    V.shuttle = new THREE.Mesh(sh, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, side: THREE.DoubleSide }));
    V.tennis = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), new THREE.MeshStandardMaterial({ color: '#d7e86a', roughness: 0.9 }));
    const cv = document.createElement('canvas'); cv.width = 128; cv.height = 64; const c2 = cv.getContext('2d'); c2.fillStyle = '#f0924f'; c2.fillRect(0, 0, 128, 64); c2.strokeStyle = '#7a3f1e'; c2.lineWidth = 3; c2.beginPath(); c2.moveTo(0, 32); c2.lineTo(128, 32); for (const x of [32, 96]) { c2.moveTo(x, 0); c2.lineTo(x, 64); } c2.stroke();
    const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
    V.basket = new THREE.Mesh(new THREE.SphereGeometry(LAY.bask.ballR, 16, 12), new THREE.MeshStandardMaterial({ map: tx, roughness: 0.85 }));
    V.shadow = new THREE.Mesh(new THREE.CircleGeometry(0.5, 16).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: '#3a2f2a', transparent: true, opacity: 0.28, depthWrite: false })); V.shadow.renderOrder = 3;
    for (const k of ['shuttle', 'tennis', 'basket', 'shadow']) { V[k].visible = false; V[k].frustumCulled = false; scene.add(V[k]); }
    V.shuttle.castShadow = V.tennis.castShadow = V.basket.castShadow = false;
    // 撞球：7 顆球一個實例網格；球桿＋瞄準線各一個
    V.balls = new THREE.InstancedMesh(new THREE.SphereGeometry(LAY.table.r, 14, 10), new THREE.MeshStandardMaterial({ roughness: 0.35 }), 7); V.balls.visible = false; V.balls.frustumCulled = false; scene.add(V.balls);
    V.cue = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.02, 1.3, 8).rotateZ(Math.PI / 2).translate(-0.65, 0, 0), new THREE.MeshStandardMaterial({ color: '#e9c79c', roughness: 0.7 })); V.cue.visible = false; V.cue.frustumCulled = false; scene.add(V.cue);
    V.line = new THREE.Mesh(new THREE.PlaneGeometry(1, 0.016).rotateX(-Math.PI / 2).translate(0.5, 0, 0), new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.8, depthWrite: false })); V.line.visible = false; V.line.frustumCulled = false; V.line.renderOrder = 5; scene.add(V.line);
  }
  const q4 = new THREE.Quaternion(), vUp = new THREE.Vector3(0, 1, 0), vv = new THREE.Vector3(), dm = new THREE.Object3D();
  const ballAt = (kind, b) => {
    const m = kind === 'badminton' ? V.shuttle : kind === 'tennis' ? V.tennis : V.basket; for (const k of ['shuttle', 'tennis', 'basket']) V[k].visible = V[k] === m;
    m.position.set(b.x, b.y, b.z);
    if (kind === 'badminton') { vv.set(b.vx, b.vy, b.vz); if (vv.lengthSq() > 0.04) { vv.normalize(); q4.setFromUnitVectors(vUp, vv); m.quaternion.copy(q4); } else m.quaternion.identity(); }
    V.shadow.visible = true; const hgt = Math.max(0, b.y); V.shadow.position.set(b.x, 0.085, b.z); const sc = (kind === 'basketball' ? 0.34 : kind === 'tennis' ? 0.18 : 0.16) * (1 + hgt * 0.12); V.shadow.scale.set(sc, 1, sc); V.shadow.material.opacity = clamp(0.3 - hgt * 0.08, 0.1, 0.3);
  };
  const ballHide = () => { for (const k of ['shuttle', 'tennis', 'basket', 'shadow', 'balls', 'cue', 'line']) V[k].visible = false; };
  const colObj = new THREE.Color();
  const billAt = G => {
    const T = G.T; V.balls.visible = true;
    G.balls.forEach((q, i) => { dm.position.set(T.cx + q.x, T.top + T.r, T.cz + q.z); dm.scale.setScalar(q.in ? 1 : 0.0001); dm.updateMatrix(); V.balls.setMatrixAt(i, dm.matrix); V.balls.setColorAt(i, colObj.set(q.col)); });
    V.balls.instanceMatrix.needsUpdate = true; if (V.balls.instanceColor) V.balls.instanceColor.needsUpdate = true;
    const a = G.aimState(), c = G.balls[0]; V.cue.visible = V.line.visible = !!a.on && c.in;
    if (a.on) { const px = T.cx + c.x, pz = T.cz + c.z, back = 0.1 + a.pow * 0.5; V.line.position.set(px, T.top + 0.03, pz); V.line.rotation.y = -a.ang; V.line.scale.set(1.0, 1, 1); V.cue.position.set(px - Math.cos(a.ang) * (T.r + back), T.top + T.r + 0.01, pz - Math.sin(a.ang) * (T.r + back)); V.cue.rotation.y = -a.ang; }
  };
  // 打到、進球的小動畫：用既有的粒子（W.fx）冒愛心／星星，不另外加繪製
  const hitFx = (kind, p) => { if (!W.fx || reduce) return; if (kind === 'score' || kind === 'pot') W.fx.burst && W.fx.burst('heart', new THREE.Vector3(p.x, (p.y || 1) + 0.4, p.z), 3, { speed: 0.4, up: 0.9, life: 1.0, size: 0.16, sway: 0.3 }); };

  // ───────── 電腦控制的角色走位 ─────────
  const aiMove = (c, tx, tz, vmax, lx, lz) => {
    const p = c.object3D.position, dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz), fx = lx - p.x, fz = lz - p.z;
    if (d < 0.1) { c.drive(0, 0, fx, fz); return; }
    let sp = Math.min(vmax, d * 3.2), vx = dx / d * sp, vz = dz / d * sp; const tau = 0.12;
    if (!nav.isFree(p.x + vx * tau, p.z)) vx = 0; if (!nav.isFree(p.x + vx * tau, p.z + vz * tau)) vz = 0;
    c.drive(vx, vz, fx, fz);
  };
  const aimInput = () => {   // 方向鍵相對「鏡頭」換成世界方向（跟 pilot.js 一樣的算法），回傳沿世界 x、z 的分量
    let ix = 0, iy = 0; const ds = new Set([...held].map(k => ARROWS[k])); if (ds.has('u')) iy++; if (ds.has('d')) iy--; if (ds.has('r')) ix++; if (ds.has('l')) ix--;
    if (!ix && !iy) return { ax: 0, az: 0 }; const f = new THREE.Vector3(); W.camera.getWorldDirection(f); let fx = f.x, fz = f.z; const fl = Math.hypot(fx, fz) || 1; fx /= fl; fz /= fl;
    const rx = -fz, rz = fx, dx = fx * iy + rx * ix, dz = fz * iy + rz * ix, dl = Math.hypot(dx, dz) || 1; return { ax: dx / dl, az: dz / dl };
  };
  const XG = { say, toast: t => ui.toast(t), aiMove, aimInput, ballAt, ballHide, billAt, hitFx, point: (w, l, ex) => onPoint(w, l, ex) };

  // ───────── 找人、叫人 ─────────
  const busyish = c => !c || c.away || c.jobless || c.spec.pet || c.state === 'held' || c._held || c.sportSess || (D().meeting && D().meeting.people.includes(c));
  function candidates(me, at) {
    const pool = allChars().filter(c => c !== me && !busyish(c) && !c.piloted && !c.sleeping && !c.spec.isCeo);
    const idle = pool.filter(c => !c.busy && c.state === 'sit' && c.atDesk), list = idle.length ? idle : pool.filter(c => !c.busy);
    return list.sort((a, b) => Math.hypot(a.object3D.position.x - at.x, a.object3D.position.z - at.z) - Math.hypot(b.object3D.position.x - at.x, b.object3D.position.z - at.z));
  }
  function take(c, s) {   // 把一位同事從他手上的事叫過來（同「被拎起來」的處理：中止排程、離開座位）
    const d = D(); d.grabbed(c); c.sportSess = s; c.busy = true; c.keep = null; c.stop(false); c.setAction('idle');
  }
  function giveBack(c) {
    if (!c || !c.sportSess) return; c.sportSess = null; c._sportGo = (c._sportGo || 0) + 1; c.drive && c.drive(null); c.setAction('idle'); c.setExpression && c.setExpression('neutral');
    if (c.piloted) return; if (!D().sendHome(c)) c.busy = false;
  }
  function sendTo(c, tx, tz, speed = 3.4) {   // 走（跑）到定位；回傳 Promise（到了才 resolve，最久 18 模擬秒，之後直接站過去）
    const p = c.object3D.position, tok = c._sportGo = (c._sportGo || 0) + 1; c.drive && c.drive(null);
    const f = nav.nearestFree(tx, tz, 10) || { x: tx, z: tz }, path = nav.findPath({ x: p.x, z: p.z }, f);
    if (c.state === 'sit') { c.atDesk = false; }
    const run = path && path.length >= 2 ? c.walkTo(path, { speed }) : Promise.resolve(false);
    return Promise.race([run, W.sleep(18).then(() => false)]).then(ok => { if (c._sportGo !== tok) return false; if (!ok) { c.stop(false); const q = c.object3D.position; if (Math.hypot(q.x - f.x, q.z - f.z) > 0.6) c.standAt(f.x, f.z, c.heading); } return true; });
  }

  // ───────── 事件 ─────────
  function emitStart(s) { W.emit && W.emit('sport_start', idOf(s.me), { kind: s.kind, zh: ZH[s.kind], with: s.partner ? idOf(s.partner) : null, ambient: !!s.ambient, x: s.venue.at.x, z: s.venue.at.z }); S.log.push({ type: 'start', kind: s.kind, t: W.time }); }
  function onPoint(w, l, ex) {
    const s = S.sess || S.amb; if (!s) return; S.stats.points++;
    const wid = w ? idOf(w.c) : null, lid = l ? idOf(l.c) : null;
    W.emit && W.emit('sport_score', wid || idOf(s.me), { kind: s.kind, opponent: lid, result: 'point', final: false, ...ex, score: ex && ex.score });
    if (w && !s.ambient) S.lastPoint = { winner: wid, why: ex && ex.why };
    if (w && w.c && !reduce) { try { w.c.setExpression('happy', 1.2); w.c.emote('star', 1.2); } catch (e) { /* 沒這個表情就算了 */ } }
    if (l && l.c && ex && ex.why && /沒接到|出界|沒過網|落在自己場內|球網/.test(ex.why) && Math.random() < 0.4) { try { l.c.emote('sweat', 1.2); } catch (e) { /* 同上 */ } }
  }
  function finish(s, reason) {
    const G = s.game; if (!G || s.finished) return; s.finished = true;
    const ps = G.players, a = ps[0], b = ps[1] || null, win = G.winner || null;
    W.emit && W.emit('sport_end', idOf(s.me), { kind: s.kind, zh: ZH[s.kind], with: s.partner ? idOf(s.partner) : null, winner: win ? idOf(win.c) : null, reason, ambient: !!s.ambient, score: Object.fromEntries(ps.map(p => [idOf(p.c), p.score || 0])) });
    if (win && b) { const lose = ps.find(p => p !== win); for (const [p, o, r] of [[win, lose, 'win'], [lose, win, 'lose']]) W.emit && W.emit('sport_score', idOf(p.c), { kind: s.kind, opponent: idOf(o.c), result: r, final: true, score: Object.fromEntries(ps.map(q => [idOf(q.c), q.score || 0])) }); }
    else if (win && !b) W.emit && W.emit('sport_score', idOf(win.c), { kind: s.kind, opponent: null, result: 'done', final: true, score: { [idOf(win.c)]: win.score || 0 } });
    if (win && !s.ambient) { const nm = win.human ? '你' : nick(win.c); ui.toast(`${ZH[s.kind]}結束：${nm}贏了！`); win.c.setAction('cheer'); win.c.setExpression('happy', 2); const lose = ps.find(p => p !== win); if (lose && lose.c) { lose.c.setExpression(lose.human ? 'neutral' : 'sad', 2); } }
  }

  // ───────── 開始、結束一場 ─────────
  const humanOf = s => (s.game ? s.game.players.find(p => p.human) : null);
  function venueAt(c) { const p = c.object3D.position; return VENUES.find(v => inRect(v.zone, p.x, p.z)) || null; }
  async function startFor(me, venue, partner) {
    if (S.sess || !me) return null;
    const P = W.pilot; if (P && P.sel === me && !P.engaged) { const ok = await P.engage(); if (!ok) { ui.toast('現在不能開始運動'); return null; } }
    if (S.sess) return null;
    const s = S.sess = { kind: venue.kind, venue, me, partner: null, phase: venue.kind === 'pool' ? 'play' : 'invite', t0: W.time, game: null, ambient: false, id: ++S.stats.sessions };
    me.sportSess = s; document.body.classList.add('sp-on');
    if (venue.kind === 'pool') { startSwim(s); return s; }
    const camNeeded = !(W.view && W.view.mode === 'god' && false); try { if (W.godAt && !document.body.classList.contains('pov-on')) W.godAt(venue.at.x, venue.at.z + 0.5, venue.kind === 'billiards' ? 11 : 17); } catch (e) { /* 鏡頭飛不過去也沒關係 */ }
    if (partner) await invite(partner);
    renderHud(true); return s;
  }
  async function invite(c) {
    const s = S.sess; if (!s || s.phase !== 'invite' || busyish(c) || c === s.me) { if (c && busyish(c)) ui.toast('他現在不方便'); return false; }
    s.phase = 'wait'; s.partner = c; take(c, s); say(`${nick(c)}，一起來打${ZH[s.kind]}吧！`, 2.2); c.emote && c.emote('exclaim', 1.4); c.say && c.say('好啊，我來了！', 2);
    const tg = partnerSpot(s); const tok = s.id; const arrived = await sendTo(c, tg.x, tg.z, 3.4);
    if (S.sess !== s || !arrived) return false; if (c._held) return false; beginGame(s); return true;
  }
  function partnerSpot(s) {
    const v = s.venue, me = s.me.object3D.position;
    if (v.kind === 'badminton' || v.kind === 'tennis') { const C = v.kind === 'badminton' ? LAY.bad : LAY.ten, sideA = me.x < C.cx; return { x: C.cx + (sideA ? 1 : -1) * C.L * 0.3, z: C.cz }; }
    if (v.kind === 'basketball') return { x: LAY.bask.hx + 2.2, z: LAY.bask.z0 + 4.8 };
    const T = LAY.table; return { x: T.cx + 0.4, z: T.cz + 1.3 };
  }
  function autoPartner() { const s = S.sess; if (!s || s.phase !== 'invite') return; const l = candidates(s.me, s.venue.at); if (!l.length) { ui.toast('現在沒有閒著的同事，先自己練習吧'); soloStart(); return; } invite(l[0]); }
  function soloStart() {
    const s = S.sess; if (!s || s.phase !== 'invite') return; if (s.kind === 'badminton' || s.kind === 'tennis') { ui.toast('羽毛球要有人對打，先找一位同事'); return; }
    beginGame(s);
  }
  function mkPlayers(s) {
    const me = s.me, ps = [{ c: me, id: idOf(me), human: true, score: 0 }]; if (s.partner) ps.push({ c: s.partner, id: idOf(s.partner), human: false, score: 0 }); return ps;
  }
  function beginGame(s) {
    const ps = s.players = s.ambientPlayers || mkPlayers(s); s.phase = 'play'; let G;
    if (s.kind === 'badminton' || s.kind === 'tennis') {
      const C = s.kind === 'badminton' ? LAY.bad : LAY.ten, h = ps.find(p => p.human); const hx = h ? h.c.object3D.position.x : C.cx - 1;
      if (h) { h.side = hx < C.cx ? 'A' : 'B'; ps.find(p => p !== h).side = h.side === 'A' ? 'B' : 'A'; } else { ps[0].side = 'A'; ps[1].side = 'B'; }
      G = createRacket(XG, s.kind, ps);
    } else if (s.kind === 'basketball') G = createBasket(XG, ps); else G = createBilliards(XG, ps);
    s.game = G; G.start(); s.acc = 0; emitStart(s);
    for (const p of ps) { if (!p.human) { p.c.drive(0, 0); } }
    if (!s.ambient) say(`${ZH[s.kind]}開始！`, 1.6);
  }
  function end(reason = 'user') {
    const s = S.sess; if (!s) return; S.sess = null;
    if (s.game) { finish(s, reason); s.game.end(); } else if (s.kind !== 'pool') { W.emit && W.emit('sport_end', idOf(s.me), { kind: s.kind, zh: ZH[s.kind], with: null, winner: null, reason: reason === 'user' ? 'cancel' : reason, ambient: false, score: {} }); }
    if (s.kind === 'pool') { W.emit && W.emit('sport_end', idOf(s.me), { kind: 'pool', zh: '游泳', with: null, winner: null, reason, ambient: false, score: {} }); }
    ballHide(); s.me.sportSess = null; if (s.partner) giveBack(s.partner);
    for (const p of (s.ambientPlayers || [])) if (p.c !== s.me) giveBack(p.c);
    s.me.drive && s.me.drive(null); document.body.classList.remove('sp-on'); hud.hidden = true; hudKey = '';
    if (reason === 'user' && !s.ambient) ui.toast(`已結束${ZH[s.kind]}`);
    s.phase = 'over';
  }
  function startSwim(s) {
    const me = s.me, p = me.object3D.position, to = { x: 4.4, z: 35.4 };
    if (water.inWater(me)) { emitStart(s); s.swimStarted = true; renderHud(true); return; }
    s.hop = { t: 0, from: { x: p.x, z: p.z }, to, heading: Math.atan2(to.x - p.x, to.z - p.z) }; me._noSplashUntil = W.time + 1.5; say('跳進泳池囉！', 1.6); emitStart(s); s.swimStarted = true; renderHud(true);
  }

  // ───────── 閒著的員工自己去運動 ─────────
  let nextAmb = 22 + Math.random() * 20; S.amb = null;
  function startAmbient(kind) {
    if (S.sess || S.amb || (D().meeting)) return null; kind = kind || pick(['badminton', 'tennis', 'basketball', 'billiards', 'swim', 'badminton', 'tennis']);
    const v = VENUES.find(q => q.kind === (kind === 'swim' ? 'pool' : kind)); const l = candidates({ object3D: { position: { x: v.at.x, z: v.at.z } } }, v.at); const need = (kind === 'swim' || kind === 'basketball') ? 1 : 2;
    if (l.length < need) return null;
    const a = l[0], c2 = need === 2 ? l[1] : (kind === 'basketball' ? l[1] || null : null);
    const s = S.amb = { kind: v.kind, venue: v, me: a, partner: c2, phase: 'wait', t0: W.time, game: null, ambient: true, id: ++S.stats.sessions }; S.stats.ambient++;
    take(a, s); if (c2) take(c2, s);
    if (kind === 'swim') { sendTo(a, 4.4, 36.0, 2.4).then(() => { if (S.amb !== s) return; s.phase = 'play'; s.swimT = 0; s.wp = null; emitStart(s); }); return s; }
    const spots = ambientSpots(v, 2); const A = { c: a, id: idOf(a), human: false, score: 0 }, Bp = c2 ? { c: c2, id: idOf(c2), human: false, score: 0 } : null;
    s.ambientPlayers = Bp ? [A, Bp] : [A]; if (v.kind === 'basketball' && !Bp) { s.ambientPlayers = [A]; }
    Promise.all([sendTo(a, spots[0].x, spots[0].z, 2.8), c2 ? sendTo(c2, spots[1].x, spots[1].z, 2.8) : Promise.resolve(true)]).then(() => { if (S.amb !== s) return; s.game = null; beginAmbientGame(s); });
    return s;
  }
  function ambientSpots(v, n) {
    if (v.kind === 'badminton' || v.kind === 'tennis') { const C = v.kind === 'badminton' ? LAY.bad : LAY.ten; return [{ x: C.cx - C.L * 0.3, z: C.cz }, { x: C.cx + C.L * 0.3, z: C.cz }]; }
    if (v.kind === 'basketball') return [{ x: LAY.bask.hx - 0.8, z: LAY.bask.z0 + 3.8 }, { x: LAY.bask.hx + 2.2, z: LAY.bask.z0 + 4.8 }];
    const T = LAY.table; return [{ x: T.cx - 0.5, z: T.cz + 1.3 }, { x: T.cx + 0.6, z: T.cz - 1.3 }];
  }
  function beginAmbientGame(s) {
    const ps = s.ambientPlayers; let G; s.phase = 'play';
    if (s.kind === 'badminton' || s.kind === 'tennis') { ps[0].side = 'A'; ps[1].side = 'B'; G = createRacket(XG, s.kind, ps); } else if (s.kind === 'basketball') G = createBasket(XG, ps); else G = createBilliards(XG, ps);
    s.game = G; G.start(); emitStart(s);
  }
  function endAmbient(reason) {
    const s = S.amb; if (!s) return; S.amb = null;
    if (s.game) { finish(s, reason); s.game.end(); } else if (s.kind === 'pool') W.emit && W.emit('sport_end', idOf(s.me), { kind: 'pool', zh: '游泳', with: null, winner: null, reason, ambient: true, score: {} });
    ballHide(); for (const c of [s.me, s.partner]) if (c) giveBack(c); nextAmb = W.time + 30 + Math.random() * 40;
  }
  S.ambientNow = kind => startAmbient(kind); S.endAmbient = () => endAmbient('forced');

  // ───────── 每個模擬步 ─────────
  let acc = 0, lastT = W.time;
  function tick(h) {
    water.tick(h);
    // 自己操控的角色走進泳池 → 自動變成游泳（離開再結束）
    const P = W.pilot, me0 = P && P.sel && P.engaged ? P.sel : null;
    if (!S.sess && me0 && water.inWater(me0) && !me0.sportSess) { const v = VENUES.find(q => q.kind === 'pool'); S.sess = { kind: 'pool', venue: v, me: me0, partner: null, phase: 'play', t0: W.time, game: null, ambient: false, id: ++S.stats.sessions, swimStarted: true }; me0.sportSess = S.sess; document.body.classList.add('sp-on'); emitStart(S.sess); renderHud(true); }
    const s = S.sess;
    if (s) {
      if (s.me.sportSess !== s) { S.sess = null; } // 被別的流程取消
      else if (!s.ambient && P && (P.sel !== s.me || !P.engaged) && !(s.hop)) end('release');
      else if (s.hop) hopStep(s, h);
      else if (s.kind === 'pool') { if (!water.inWater(s.me)) { s.outT = (s.outT || 0) + h; if (s.outT > 1.2) end('left'); } else s.outT = 0; }
      else if (s.game) {
        const mp = s.me.object3D.position, z = s.venue.zone; if (mp.x < z.x0 - 4 || mp.x > z.x1 + 4 || mp.z < z.z0 - 4 || mp.z > z.z1 + 4) end('left');
        else if (s.partner && (s.partner._held || s.partner.state === 'held')) { ui.toast('同事被你拎起來了，結束這場'); end('partner'); }
        else if (s.game.over) { s.overT = (s.overT || 0) + h; if (s.overT > 2.2) end('over'); }
      } else if (s.phase === 'invite') { s.inv = (s.inv || 0) + h; if (s.inv > 12) autoPartner(); }
    }
    const a = S.amb;
    if (a) {
      if (a.game && a.game.over) { a.overT = (a.overT || 0) + h; if (a.overT > 2) endAmbient('over'); }
      else if (W.time - a.t0 > 70 || (a.phase === 'play' && W.time - (a.pt0 || (a.pt0 = W.time)) > 38)) endAmbient('timeout');
      else if (a.kind === 'pool' && a.phase === 'play') swimWander(a, h);
      else if (a.game) { for (const p of a.game.players) if (p.c._held || p.c.state === 'held') { endAmbient('grabbed'); break; } }
    } else if (!s && S.ambientOn && D().ambient && W.time > nextAmb) { nextAmb = W.time + 25 + Math.random() * 30; if (Math.random() < 0.7) startAmbient(); }
    // 球的固定時間步
    const G = (s && s.game && s.phase === 'play') ? s.game : (a && a.game) || null;
    if (G) { acc += h; let n = 0; while (acc >= DT && n < 32) { G.update(DT); acc -= DT; n++; S.steps++; } if (n >= 32) acc = 0; } else acc = 0;
  }
  function hopStep(s, h) {
    const hp = s.hop, c = s.me; hp.t += h; const u = Math.min(1, hp.t / 0.75), e = u * u * (3 - 2 * u), x = hp.from.x + (hp.to.x - hp.from.x) * e, z = hp.from.z + (hp.to.z - hp.from.z) * e;
    c.standAt(x, z, hp.heading); c._hopY = Math.sin(Math.PI * u) * 0.8;
    if (u >= 1) { s.hop = null; c._hopY = 0; water.splash(hp.to.x, hp.to.z, 3.2); W.emit && W.emit('splashed', idOf(c), { x: hp.to.x, z: hp.to.z, speed: 3.2, thrown: false, burning: false, from: 'dive' }); const F = W.fire; if (F && F.extinguish) F.extinguish(c, 'pool'); c.setExpression && c.setExpression('happy', 1.6); }
  }
  function swimWander(s, h) {
    const c = s.me, L = LAY.pool, p = c.object3D.position; s.swimT = (s.swimT || 0) + h;
    if (s.swimT > 16) { if (!s.leaving) { s.leaving = true; c.drive(null); const path = nav.findPath({ x: p.x, z: p.z }, { x: 4.4, z: 38.0 }); if (path) c.walkTo(path, { speed: 1.6 }).then(() => { if (S.amb === s) endAmbient('done'); }); else endAmbient('done'); } return; }
    if (s.leaving) return;
    if (!s.wp || Math.hypot(p.x - s.wp.x, p.z - s.wp.z) < 0.35 || (s.wpT = (s.wpT || 0) + h) > 4) { s.wp = { x: rnd(L.x0 + 0.8, L.x1 - 0.8), z: rnd(L.z0 + 0.8, L.z1 - 0.8) }; s.wpT = 0; }
    aiMove(c, s.wp.x, s.wp.z, 1.0, s.wp.x, s.wp.z);
  }

  // ───────── 介面 ─────────
  const css = document.createElement('style'); css.textContent = `
.sp-hud{position:absolute;z-index:23;left:50%;bottom:16px;transform:translateX(-50%);width:min(460px,calc(100vw - 24px));background:var(--card,#fffaf2);border-radius:var(--r,14px);box-shadow:var(--sh,0 6px 22px rgba(74,58,50,.22));padding:8px 12px 10px;font:600 13px/1.5 "Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;color:#5a4638;pointer-events:auto}
.sp-hud[hidden]{display:none}.sp-hud .sp-t{display:block;font-size:14px;font-weight:800}.sp-hud .sp-p{display:block;color:#7a6556;min-height:19px}
.sp-meter{height:14px;border-radius:99px;background:#ecdcc2;position:relative;margin:7px 2px 3px}.sp-meter i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:#f2a65a;width:0}.sp-meter u{position:absolute;top:-3px;bottom:-3px;width:12px;margin-left:-6px;border-radius:5px;background:#43b57f;opacity:.92}
.sp-btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.sp-btns button{min-height:36px;padding:4px 14px;border-radius:99px;border:2px solid #d9a867;background:#fff1d8;color:#6b4a22;font:700 13px "Noto Sans TC","PingFang TC",sans-serif;cursor:pointer;touch-action:manipulation}.sp-btns button:hover{background:#ffe6bd}.sp-btns button.sp-main{background:#f2a65a;border-color:#d98a3e;color:#fff}
.sp-go{position:absolute;z-index:9;left:16px;bottom:44px;border:2px solid #7fc4a0;background:#e4f6ec;color:#2f6e55;border-radius:999px;padding:6px 14px;min-height:36px;font:700 13px/1.2 "Noto Sans TC",sans-serif;box-shadow:var(--sh,0 4px 14px rgba(74,58,50,.2));cursor:pointer}.sp-go[hidden]{display:none}body.pt-sel .sp-go{display:none}
@media (max-width:640px){.sp-hud{bottom:calc(162px + var(--lift,0px));padding:6px 10px 8px}.sp-go{left:12px;bottom:calc(58px + env(safe-area-inset-bottom,0px))}}
@media (max-width:1100px){body.sp-on .pt-tips{display:none}}
body.sp-on .jl-hint,body.sp-on .pt-hint{display:none}`;
  document.head.append(css);
  const hud = document.createElement('div'); hud.className = 'sp-hud'; hud.hidden = true; hud.setAttribute('role', 'status'); hud.setAttribute('aria-live', 'polite');
  hud.innerHTML = '<b class="sp-t"></b><span class="sp-p"></span><div class="sp-meter" hidden><i></i><u></u></div><div class="sp-btns"></div>';
  (document.getElementById('app') || document.body).append(hud);
  const elT = hud.querySelector('.sp-t'), elP = hud.querySelector('.sp-p'), elM = hud.querySelector('.sp-meter'), elMi = elM.querySelector('i'), elMu = elM.querySelector('u'), elB = hud.querySelector('.sp-btns');
  const go = document.createElement('button'); go.className = 'sp-go'; go.type = 'button'; go.hidden = true; go.textContent = '▼ 員工運動場'; go.setAttribute('aria-label', '前往員工運動場（辦公室大門外小路西邊）'); (document.getElementById('app') || document.body).append(go);
  go.addEventListener('click', () => { try { W.godAt(9.9, 40.2, 26); } catch (e) { /* 鏡頭不動也沒關係 */ } });
  const PV = new THREE.Vector3(); let hint0 = 0, hudKey = '', btnKey = '';
  function setBtns(list) {
    const k = list.map(b => b[0]).join('|'); if (k === btnKey) return; btnKey = k; elB.innerHTML = '';
    for (const [id, label, main] of list) { const b = document.createElement('button'); b.type = 'button'; b.dataset.a = id; b.textContent = label; if (main) b.className = 'sp-main'; elB.append(b); }
  }
  elB.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return; const a = b.dataset.a, s = S.sess;
    if (a === 'end') end('user'); else if (a === 'auto') autoPartner(); else if (a === 'solo') soloStart();
    else if (a === 'start') { const P = W.pilot, me = P && P.sel, v = me && venueAt(me); if (me && v) startFor(me, v); }
    else if (a === 'act' && s && s.game) { const p = humanOf(s); if (p) { s.game.onSpace && s.game.onSpace(p, true); if (s.kind === 'basketball') { /* 手機：按一下＝蓄力，再按一下＝投 */ } } }
  });
  // 手機：籃球「蓄力」鈕用按下／放開
  elB.addEventListener('pointerdown', e => { const b = e.target.closest('button[data-a=charge]'); if (b && S.sess && S.sess.game) { const p = humanOf(S.sess); p && S.sess.game.onSpace(p, true); e.preventDefault(); } });
  const up = e => { const b = e.target.closest && e.target.closest('button[data-a=charge]'); if (b && S.sess && S.sess.game) { const p = humanOf(S.sess); p && S.sess.game.onSpace(p, false); } };
  elB.addEventListener('pointerup', up); elB.addEventListener('pointercancel', up);
  function renderHud(force) {
    const s = S.sess, P = W.pilot, me = P && P.sel && P.engaged ? P.sel : (P && P.sel) || null; let key, title = '', tip = '', meter = null, btns = [];
    const mobile = matchMedia('(pointer:coarse)').matches || innerWidth <= 640;
    if (s) {
      if (s.kind === 'pool') { title = '游泳'; tip = water.inWater(s.me) ? (mobile ? '搖桿游動；游到缺口（南邊台階）上岸，按「結束」' : '方向鍵游動；從南邊缺口的台階上岸，Esc 結束') : '準備下水…'; btns = [['end', '結束']]; }
      else if (s.phase === 'invite') { title = `${ZH[s.kind]}：找一位同事一起打`; tip = (mobile ? '點一位同事邀請他（他會跑過來），或按「自動找同事」' : '點另一位員工邀請他（他會跑過來），或按 E／Enter 自動找閒著的同事'); btns = [['auto', '自動找同事', true]]; if (s.kind === 'basketball' || s.kind === 'billiards') btns.push(['solo', '自己練習']); btns.push(['end', '結束（Esc）']); }
      else if (s.phase === 'wait') { title = `${ZH[s.kind]}：${s.partner ? nick(s.partner) : '同事'}正在趕過來`; tip = '稍等一下，他到了就開始'; btns = [['end', '結束（Esc）']]; }
      else if (s.game) { const h = s.game.hud(); title = h.title; tip = h.tip; meter = h.meter; btns = [['end', '結束（Esc）']]; if (mobile) { if (s.kind === 'badminton' || s.kind === 'tennis') btns.unshift(['act', '揮拍', true]); else if (s.kind === 'basketball') btns.unshift(['charge', '按住蓄力・放開投籃', true]); } if (s.game.over && s.game.winner) tip = `${s.game.winner.human ? '你' : nick(s.game.winner.c)} 贏了！`; }
      key = 's' + title + tip + (meter ? '1' : '0');
    } else if (me && !me.sportSess) {
      const v = venueAt(me); if (!v) { hud.hidden = true; hudKey = ''; return; }
      title = `${ZH[v.kind]}場`; tip = mobile ? `點「開始」${v.kind === 'pool' ? '跳進泳池' : '打' + ZH[v.kind]}` : `按 E ${v.kind === 'pool' ? '跳進泳池游泳' : '開始打' + ZH[v.kind]}`; btns = [['start', '開始', true]]; key = 'n' + v.kind;
    } else { if (!hud.hidden) { hud.hidden = true; hudKey = ''; } return; }
    hud.hidden = false;
    { // 主聊天室（#chatPanel，在畫面底部中間）開著時，介面往上讓開，兩者不重疊；手機則在虛擬搖桿的上方
      const cp = document.getElementById('chatPanel'), cr = cp && !cp.hidden ? cp.getBoundingClientRect() : null, lift = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--lift')) || 0;
      let b = mobile ? 162 + lift : 16; if (cr && cr.height > 0 && cr.width > 0) { const kids = [...cp.querySelectorAll('.mc-bar,.mc-peek,.mc-top')].filter(e => e.getBoundingClientRect().height > 0); const top = kids.length ? Math.min(...kids.map(e => e.getBoundingClientRect().top)) : cr.top; b = Math.max(b, innerHeight - top + 8); }
      b = Math.min(b, Math.max(16, innerHeight - 170)); const bs = Math.round(b) + 'px'; if (hud.style.bottom !== bs) hud.style.bottom = bs;
    }
    if (key !== hudKey || force) { hudKey = key; elT.textContent = title; elP.textContent = tip; setBtns(btns); }
    elM.hidden = !meter; if (meter) { elMi.style.width = Math.round(meter.v * 100) + '%'; elMu.style.left = Math.round(clamp(meter.ideal, 0, 1) * 100) + '%'; elMu.style.width = Math.round(meter.tol * 200) + '%'; elMu.style.marginLeft = (-meter.tol * 100) + '%'; }
    if (s && s.game && elP.textContent !== tip) elP.textContent = tip;
    if (s && s.game) { elT.textContent = title; }
  }
  // ───────── 輸入 ─────────
  API = {
    get sess() { return S.sess; },
    key(e, down) {
      const s = S.sess, P = W.pilot;
      if (down && e.code === 'Escape' && s) { e.preventDefault(); e.stopImmediatePropagation(); end('user'); return; }
      if (down && !e.repeat && (e.code === 'KeyE' || e.code === 'Enter')) {
        if (s) { if (s.phase === 'invite') { e.preventDefault(); e.stopImmediatePropagation(); autoPartner(); } else if (e.code === 'KeyE') { e.preventDefault(); e.stopImmediatePropagation(); } return; }
        const me = P && P.sel; if (e.code === 'KeyE' && me && !me.sportSess && P) { const v = venueAt(me); if (v) { e.preventDefault(); e.stopImmediatePropagation(); startFor(me, v); } }
        return;
      }
      if (e.code === 'Space' && s && s.game && s.phase === 'play') { e.preventDefault(); e.stopImmediatePropagation(); const p = humanOf(s); if (!p) return; if (s.kind === 'basketball') s.game.onSpace(p, down); else if (down && !e.repeat) s.game.onSpace(p, true); return; }
    },
    ptr(e, type) {
      const s = S.sess; if (!s) return;
      if (type === 'pointerdown' && s.phase === 'invite' && e.target && e.target.id === 'cv') {
        let best = null, bd = 64; const cvr = document.getElementById('cv').getBoundingClientRect();
        for (const c of W.chars.values()) { if (c === s.me || busyish(c) || c.piloted || c.spec.isCeo && false) continue; if (!(c._sx > -900)) continue; const d = Math.hypot(c._sx - (e.clientX - cvr.left), c._sy - (e.clientY - cvr.top)); if (d < bd) { bd = d; best = c; } }
        if (best) { e.preventDefault(); e.stopImmediatePropagation(); invite(best); }
        return;
      }
      if (s.kind === 'billiards' && s.game && s.phase === 'play') {
        const G = s.game; const cv = document.getElementById('cv');
        if (type === 'pointerdown' && e.target === cv && G.canAim()) { S.drag = e.pointerId; e.preventDefault(); e.stopImmediatePropagation(); aimTo(e, true); }
        else if ((type === 'pointermove') && S.drag === e.pointerId) { e.stopImmediatePropagation(); aimTo(e, true); }
        else if ((type === 'pointerup' || type === 'pointercancel') && S.drag === e.pointerId) { e.stopImmediatePropagation(); S.drag = null; if (type === 'pointerup') G.release(); else G.aimOn = false; }
      }
    }
  };
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -LAY.table.top), hit = new THREE.Vector3();
  function aimTo(e, down) {
    const r = document.getElementById('cv').getBoundingClientRect(); ndc.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, W.camera);
    if (ray.ray.intersectPlane(plane, hit)) { const t = S.sess.game.toTable(hit.x, hit.z); S.sess.game.aim(t.x, t.z, down); }
  }
  S.screenToTable = (cx, cy) => { const r = document.getElementById('cv').getBoundingClientRect(); ndc.set((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, W.camera); return ray.ray.intersectPlane(plane, hit) ? { x: hit.x, z: hit.z } : null; };

  // ───────── 每一畫面 ─────────
  function frame() {
    water.frame(); const s = S.sess;
    if (s && s.hop) s.me.object3D.position.y = s.me._hopY || 0;
    renderHud(false);
    const t = performance.now(); if (t - hint0 > 250) { hint0 = t; PV.set(9.9, 0.5, 40.2).project(W.camera); const off = !(PV.z < 1 && Math.abs(PV.x) < 0.8 && PV.y > -0.78 && PV.y < 1) || document.body.classList.contains('pov-on'); go.hidden = !off; }
  }
  // 掛進主迴圈：每個模擬步（W.tickTimers 後面）、每一畫面（W.updateBlobs 後面）
  const t0 = W.tickTimers; S.perf = { ms: 0, n: 0, max: 0 }; W.tickTimers = () => { t0(); const h = W.time - lastT; lastT = W.time; if (h > 0) { const p0 = performance.now(); try { tick(Math.min(h, 0.1)); } catch (e) { if (!S.err) console.error('運動場例外', e); S.err = (S.err || 0) + 1; } const dt = performance.now() - p0; S.perf.ms += dt; S.perf.n++; if (dt > S.perf.max) S.perf.max = dt; } };   // 量測：運動場每個模擬步花多少毫秒（驗收用）
  const u0 = W.updateBlobs; W.updateBlobs = () => { u0(); try { frame(); } catch (e) { if (!S.err) console.error('運動場畫面例外', e); S.err = (S.err || 0) + 1; } };
  // 運動場自己的繪製物件（驗收數「繪製次數增量」用：靜態＋目前顯示中的球、陰影、撞球組）
  S.drawObjects = () => [B.mesh, B.nets, B.sign, water.mesh, water.points, V.shuttle, V.tennis, V.basket, V.shadow, V.balls, V.cue, V.line].filter(o => o && o.visible);
  S.end = end; S.start = (id, kind, partnerId) => { const me = W.chars.get(id), v = VENUES.find(q => q.kind === kind); return startFor(me, v, partnerId ? W.chars.get(partnerId) : null); };
  S.invite = invite; S.autoPartner = autoPartner; S.hud = hud; S.XG = XG; S.venueAt = venueAt;
  return S;
}
