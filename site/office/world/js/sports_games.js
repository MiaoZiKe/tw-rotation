// 運動場的四種玩法與球的物理（2026-11-15）：羽毛球／網球（同一套球拍球類）、籃球（蓄力投籃）、撞球（2D 剛體碰撞）。
// 規則：球一律用「固定時間步」積分（1/120 秒；撞球 1/240），所以 4× 倍速下結果跟 1× 一樣，不會因為畫面卡頓穿牆。
// 每個遊戲物件：update(dt)＝推進一個固定步；hud()＝給畫面提示的字與蓄力表；over／winner／score＝結束與分數；end()＝收尾。
// 球員（players）：{ c: 角色, id, human: 是不是人在操控, side: 'A'|'B', score }；人操控的由 pilot.js 走路，這裡只管「揮拍、投籃、擊球」；
//   電腦控制的由這裡用 c.drive(vx, vz, fx, fz) 移動（避開牆與家具，限制在自己的半場）。
import { THREE } from './kit.js';
import { LAY } from './sports_build.js';

const G0 = 9.8, clamp = (x, a, b) => Math.max(a, Math.min(b, x)), rnd = (a, b) => a + Math.random() * (b - a), gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) * 1.15;
const TAU = Math.PI * 2, deg = a => a * Math.PI / 180;
export const DT = 1 / 120;

// ───────────────────────── 球拍球類（羽毛球、網球） ─────────────────────────
const RP = {
  badminton: { zh: '羽毛球', C: LAY.bad, k: 0.218, e: 0, r: 0.05, reach: 1.3, hmax: 2.2, vcap: 11.5, tmin: 0.8, angles: [14, 20, 27, 35, 44, 54, 64], aiV: 2.45, aiHit: 0.86, win: 5 },
  tennis: { zh: '網球', C: LAY.ten, k: 0.012, e: 0.7, r: 0.07, reach: 1.45, hmax: 1.8, vcap: 11, tmin: 0.7, angles: [6, 9, 13, 18, 24, 32, 42], aiV: 2.6, aiHit: 0.84, win: 5 },
};
function integrate(b, dt, k) { const sp = Math.hypot(b.vx, b.vy, b.vz); b.vx -= k * sp * b.vx * dt; b.vy -= (G0 + k * sp * b.vy) * dt; b.vz -= k * sp * b.vz * dt; b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt; }
// 從 (x0,y0,z0) 以速度 v、仰角 th、水平方向 (ux,uz) 打出去，模擬到第一次落地，回傳落點、飛行時間與過網高度
function simulate(P, netX, x0, y0, z0, v, th, ux, uz) {
  const b = { x: x0, y: y0, z: z0, vx: v * Math.cos(th) * ux, vy: v * Math.sin(th), vz: v * Math.cos(th) * uz }; let t = 0, ny = 99; const dt = 1 / 90;
  while (t < 8) { const px = b.x; integrate(b, dt, P.k); t += dt; if ((px - netX) * (b.x - netX) < 0 && ny === 99) { const u = (netX - px) / (b.x - px || 1); ny = b.y - b.vy * dt * (1 - u); } if (b.y <= P.r && t > 0.05) break; }
  return { x: b.x, z: b.z, t, ny };
}
// 解出「能落在目標點、又過網」的發射速度與仰角（先試平的，再試高的；飛行時間太短的略過，讓對手有時間反應）
export function solveShot(P, x0, y0, z0, tx, tz) {
  const netX = P.C.cx, dx = tx - x0, dz = tz - z0, D = Math.hypot(dx, dz) || 1, ux = dx / D, uz = dz / D; let best = null;
  for (const a of P.angles) {
    const th = deg(a); let lo = 1.5, hi = P.vcap * 1.25;
    const rng = v => { const s = simulate(P, netX, x0, y0, z0, v, th, ux, uz); return Math.hypot(s.x - x0, s.z - z0); };
    if (rng(hi) < D) continue;
    for (let i = 0; i < 13; i++) { const m = (lo + hi) / 2; if (rng(m) < D) lo = m; else hi = m; }
    const v = (lo + hi) / 2, s = simulate(P, netX, x0, y0, z0, v, th, ux, uz), ok = s.ny > P.C.netH + P.r + 0.06 && s.t >= P.tmin && v <= P.vcap;
    const cand = { v, th, ux, uz, ok, t: s.t, ny: s.ny }; if (ok) return cand; if (!best || (s.ny > best.ny && v <= P.vcap * 1.2)) best = cand;
  }
  return best || { v: P.vcap, th: deg(P.angles[P.angles.length - 1]), ux, uz, ok: false, t: 1, ny: 0 };
}

export function createRacket(X, kind, players) {
  const P = RP[kind], C = P.C, netX = C.cx, G = { kind, zh: P.zh, players, over: false, winner: null, phase: 'serve', ball: { x: C.cx, y: 1, z: C.cz, vx: 0, vy: 0, vz: 0 }, stats: { hits: 0, byHuman: 0, byAI: 0, rallies: 0, maxRally: 0, points: 0 } };
  const b = G.ball, S = { A: players.find(p => p.side === 'A'), B: players.find(p => p.side === 'B') }, other = s => (s === 'A' ? 'B' : 'A'), dirOf = s => (s === 'A' ? 1 : -1);   // A 在西邊（x 小），往東（+x）打
  let t = 0, server = 'A', lastHit = null, bounces = 0, fault = false, rally = 0, pauseT = 0, serveWait = 0, tPredict = 0, predict = null, toastT = 0, rallyT = 0;
  for (const p of players) { p.score = 0; p.swing = 0; p.cool = 0; p.home = { x: netX + dirOf(p.side) * -C.L * 0.3, z: C.cz }; }
  const home = p => p.home;
  function msg(s, sec) { X.say && X.say(s, sec); }
  function startServe() { phase('serve'); lastHit = null; bounces = 0; fault = false; rally = 0; rallyT = 0; serveWait = 0; predict = null; const sv = S[server]; if (sv) holdBall(sv); }
  function phase(n) { G.phase = n; }
  function holdBall(p) { const q = p.c.object3D.position, f = p.c.heading || 0; b.x = q.x + Math.sin(f) * 0.32; b.z = q.z + Math.cos(f) * 0.32; b.y = 0.95; b.vx = b.vy = b.vz = 0; }
  const aim = p => (p.human ? X.aimInput() : { ax: 0, az: 0 });
  function hit(p, serve) {
    const q = p.c.object3D.position, d = dirOf(p.side), ai = aim(p), by = clamp(b.y, 0.35, 2.0);
    const err = (p.human ? 0.22 : 0.34) * (1 + Math.abs(by - 1.05) * 0.5) + (serve ? 0 : Math.hypot(b.vx, b.vz) * 0.012);
    let depth = (p.human ? 0.3 + 0.12 * clamp(ai.ax * d, -1, 1) : rnd(0.2, 0.46)) * C.L, tz;
    if (p.human) tz = C.cz + clamp(ai.az, -1, 1) * C.W * 0.34 + gauss() * err * 0.6;
    else { const opp = S[other(p.side)], oz = opp ? opp.c.object3D.position.z : C.cz; tz = C.cz + clamp(-(oz - C.cz) * 0.8 + rnd(-0.7, 0.7), -C.W * 0.4, C.W * 0.4) + gauss() * err * 0.5; depth += gauss() * 0.3; }
    const tx = netX + d * clamp(depth + gauss() * err * 0.4, 0.6, C.L / 2 - 0.1), z = clamp(tz, C.cz - C.W / 2 + 0.08, C.cz + C.W / 2 - 0.08);
    const sol = solveShot(P, b.x, by, b.z, tx, z);
    b.y = by; b.vx = sol.v * Math.cos(sol.th) * sol.ux; b.vy = sol.v * Math.sin(sol.th); b.vz = sol.v * Math.cos(sol.th) * sol.uz;
    lastHit = p.side; bounces = 0; fault = false; rally++; G.stats.hits++; if (p.human) G.stats.byHuman++; else G.stats.byAI++; G.stats.maxRally = Math.max(G.stats.maxRally, rally); phase('rally'); predict = null;
    p.c.faceTo(b.x + b.vx, b.z + b.vz); p.c.setAction('paddle', { duration: 0.55 }); p.cool = 0.3; p.swing = 0; X.hitFx && X.hitFx(kind, b);
  }
  function tryHit(p) {
    if (G.phase !== 'rally' || p.cool > 0) return false; if (lastHit === p.side) return false;
    const q = p.c.object3D.position, dd = Math.hypot(b.x - q.x, b.z - q.z); if (dd > P.reach || b.y > P.hmax || b.y < 0.06) return false;
    if ((b.x < netX ? 'A' : 'B') !== p.side && Math.abs(b.x - netX) > 0.45) return false;   // 球在自己這邊（貼網的 0.45 公尺內算兩邊都碰得到）
    hit(p, false); return true;
  }
  G.onSpace = (p) => {
    if (!p || G.over) return;
    if (!sideOk(p)) { X.toast && X.toast('請回自己的半場再揮拍'); return; }
    if (G.phase === 'serve' && S[server] === p) { if (!p.c.object3D.position) return; holdBall(p); hit(p, true); return; }
    p.swing = 0.3; p.c.setAction('paddle', { duration: 0.45 });
  };
  const sideOf = q => (q.x < netX ? 'A' : 'B'); const sideOk = p => sideOf(p.c.object3D.position) === p.side;
  function point(win, why) {
    G.stats.points++; const w = S[win]; if (w) w.score++; phase('point'); pauseT = 1.5; G.lastPoint = { winner: win, why };
    X.point && X.point(w, S[other(win)], { why, score: { A: S.A ? S.A.score : 0, B: S.B ? S.B.score : 0 } });
    if (w && w.score >= P.win) { G.over = true; G.winner = w; } server = win;
  }
  function land() {
    const side = b.x < netX ? 'A' : 'B', inb = Math.abs(b.x - C.cx) <= C.L / 2 + 0.03 && Math.abs(b.z - C.cz) <= C.W / 2 + 0.03, lh = lastHit; if (!lh) return;
    if (fault) { point(other(lh), '球網'); return; }
    if (kind === 'badminton') { if (!inb || side === lh) point(other(lh), inb ? '落在自己場內' : '出界'); else point(lh, '落地得分'); return; }
    if (bounces === 0) { if (!inb || side === lh) { point(other(lh), inb ? '沒過網' : '出界'); return; } bounces = 1; return; }
    point(lh, '對手沒接到');
  }
  // 電腦的腳步與揮拍
  function aiStep(p, dt) {
    const q = p.c.object3D.position, d = dirOf(p.side); let tx = home(p).x, tz = home(p).z, hurry = false;
    if (G.phase === 'rally' && lastHit !== p.side) {
      tPredict -= dt; if (tPredict <= 0 || !predict) { tPredict = 0.12; predict = landing(); }
      if (predict && ((predict.x - netX) * d < 0 || predict.t < 0.5)) { tx = predict.x; tz = predict.z; hurry = true; }
    }
    // 限制在自己半場內
    const xmin = d > 0 ? C.cx - C.L / 2 - 0.4 : netX + 0.5, xmax = d > 0 ? netX - 0.5 : C.cx + C.L / 2 + 0.4;
    tx = clamp(tx, xmin, xmax); tz = clamp(tz, C.cz - C.W / 2 - 0.5, C.cz + C.W / 2 + 0.5);
    X.aiMove(p.c, tx, tz, hurry ? P.aiV : P.aiV * 0.55, b.x, b.z);
    if (G.phase === 'rally' && lastHit !== p.side && p.cool <= 0) { const dd = Math.hypot(b.x - q.x, b.z - q.z); if (dd < P.reach * 0.9 && b.y < P.hmax - 0.2 && b.y > 0.1) { if (Math.random() < P.aiHit) tryHit(p); else p.cool = 0.6; } }
  }
  function landing() { const s = { x: b.x, y: b.y, z: b.z, vx: b.vx, vy: b.vy, vz: b.vz }; let tt = 0, bounced = 0; const dt = 1 / 60; while (tt < 5) { integrate(s, dt, P.k); tt += dt; if (s.y <= P.r) { if (kind === 'badminton' || bounced) break; bounced = 1; s.vy = Math.abs(s.vy) * P.e; s.y = P.r; } } return { x: s.x, z: s.z, t: tt }; }
  // 一個固定步
  G.update = dt => {
    if (G.over) return; t += dt; toastT -= dt;
    for (const p of players) { p.cool = Math.max(0, p.cool - dt); if (p.swing > 0) { p.swing -= dt; if (tryHit(p)) p.swing = 0; } if (!p.human) aiStep(p, dt); }
    if (G.phase === 'serve') {
      const sv = S[server]; if (!sv) return; holdBall(sv); serveWait += dt;
      if (!sv.human) { const dh = Math.hypot(sv.c.object3D.position.x - home(sv).x, sv.c.object3D.position.z - home(sv).z); if (serveWait > 1.1 && dh < 0.5) hit(sv, true); }
    } else if (G.phase === 'rally') {
      rallyT += dt; const px = b.x; integrate(b, dt, P.k);
      if ((px - netX) * (b.x - netX) < 0) { const u = (netX - px) / (b.x - px), y = b.y - b.vy * dt * (1 - u), z = b.z - b.vz * dt * (1 - u);
        if (y < C.netH && Math.abs(z - C.cz) < C.W / 2 + 0.5) { fault = true; b.x = netX - Math.sign(b.x - px) * 0.04; b.vx *= -0.12; b.vy *= 0.3; b.vz *= 0.3; X.hitFx && X.hitFx('net', b); } }
      if (b.y <= P.r && b.vy < 0) {
        if (kind === 'badminton') { b.y = P.r; b.vx = b.vy = b.vz = 0; land(); }
        else { b.y = P.r; b.vy = -b.vy * P.e; b.vx *= 0.88; b.vz *= 0.88; X.hitFx && X.hitFx('bounce', b); land(); if (G.phase === 'rally' && Math.abs(b.vy) < 0.6) b.vy = 0.6; }
      }
      if (rallyT > 22 && G.phase === 'rally') point(other(lastHit || 'A'), '太久沒結束');
      if (Math.abs(b.x - C.cx) > C.L / 2 + 5 || Math.abs(b.z - C.cz) > C.W / 2 + 5) { if (G.phase === 'rally') { fault = false; point(lastHit ? other(lastHit) : 'A', '出界'); } }
    } else if (G.phase === 'point') { pauseT -= dt; if (pauseT <= 0 && !G.over) startServe(); }
    X.ballAt && X.ballAt(kind, b, G.phase);
  };
  G.hud = () => {
    const a = S.A, c = S.B, nm = p => (p ? (p.human ? '你' : p.c.spec.nick) : '-');
    const tip = G.phase === 'serve' ? (S[server] && S[server].human ? '按空白鍵發球' : `${nm(S[server])} 準備發球`) : G.phase === 'point' ? (G.lastPoint ? `${nm(S[G.lastPoint.winner])} 得分（${G.lastPoint.why}）` : '') : '球來了：靠近球按空白鍵揮拍・方向鍵決定落點';
    return { title: `${P.zh}　${nm(a)} ${a ? a.score : 0} : ${c ? c.score : 0} ${nm(c)}（先到 ${P.win} 分）`, tip, meter: null };
  };
  G.start = () => { startServe(); G.ballKind = kind; };
  G.end = () => { X.ballHide && X.ballHide(); };
  return G;
}

// ───────────────────────── 籃球 ─────────────────────────
export function createBasket(X, players) {
  const K = LAY.bask, R = K.R, br = K.ballR, G = { kind: 'basketball', zh: '籃球', players, over: false, winner: null, phase: 'ready', ball: { x: 0, y: 1, z: 0, vx: 0, vy: 0, vz: 0 }, stats: { shots: 0, made: 0, rim: 0, board: 0, bounces: 0 } };
  const b = G.ball, solo = players.length < 2, SHOTS = players.every(p => !p.human) ? 3 : 5; let turn = 0, charge = 0, charging = false, t = 0, settleT = 0, wait = 0, scored = false, crossed = false, lastY = 0, aiReady = 0, netDamp = false;
  for (const p of players) { p.score = 0; p.shots = 0; }
  const cur = () => players[turn % players.length], vmin = 3, vmax = 11.5;
  function ideal(p) {
    const q = p.c.object3D.position, y0 = 1.1, D = Math.max(0.6, Math.hypot(K.hx - q.x, K.rimZ - q.z) - 0.2), dy = K.rimY - y0;   // 球從身前 0.2 公尺、高 1.1 公尺出手（shoot 也是）
    const th = deg(D < 1.6 ? 68 : D < 3 ? 58 : 50), den = 2 * Math.cos(th) ** 2 * (D * Math.tan(th) - dy); const v = den > 0.05 ? Math.sqrt(G0 * D * D / den) : vmax;
    return { v: clamp(v, vmin + 0.2, vmax), th, D };
  }
  function holdBall(p) { const q = p.c.object3D.position, hd = Math.atan2(K.hx - q.x, K.rimZ - q.z); b.x = q.x + Math.sin(hd) * 0.34; b.z = q.z + Math.cos(hd) * 0.34; b.y = 0.72 + 0.3 * clamp(charge, 0, 1); b.vx = b.vy = b.vz = 0; }
  function shoot(p, v) {
    const q = p.c.object3D.position, id = ideal(p), th = id.th, dx = K.hx - q.x, dz = K.rimZ - q.z, D = Math.hypot(dx, dz) || 1, ux = dx / D, uz = dz / D;
    const vEff = p.human ? id.v + (v - id.v) * 0.3 + gauss() * 0.06 : v;      // 人操控的有輔助瞄準：誤差只算 30%（太難了沒人投得進）
    b.x = q.x + ux * 0.2; b.z = q.z + uz * 0.2; b.y = 1.1; b.vx = vEff * Math.cos(th) * ux; b.vy = vEff * Math.sin(th); b.vz = vEff * Math.cos(th) * uz;
    G.phase = 'flight'; settleT = 0; scored = false; crossed = false; netDamp = false; lastY = b.y; p.shots++; G.stats.shots++; charging = false; charge = 0;
    p.c.faceTo(K.hx, K.rimZ); p.c.setAction('raise', { duration: 0.9 }); X.hitFx && X.hitFx('shot', b);
  }
  G.onSpace = (p, down) => {
    if (G.over || cur() !== p || !p.human || G.phase !== 'ready') return;
    if (down && !charging) { charging = true; charge = 0; } else if (!down && charging) { const v = vmin + (vmax - vmin) * clamp(charge, 0, 1); shoot(p, v); }
  };
  function nextTurn() {
    const p = cur(); const done = players.every(q => q.shots >= SHOTS);
    if (!solo && done) {
      const a = players[0], c = players[1]; if (a.score === c.score && !G.sudden) { G.sudden = true; X.say && X.say('平手！再各投一球', 2); } else if (a.score !== c.score) { G.over = true; G.winner = a.score > c.score ? a : c; return; }
      if (G.sudden) { a.shots = c.shots = SHOTS - 1; }
    }
    turn++; G.phase = 'ready'; charge = 0; charging = false; wait = 0; aiReady = rnd(0.9, 1.5);
    const n = cur(); if (!n.human) { const spot = { x: K.hx + rnd(-0.9, 0.9), z: K.z0 + rnd(3.1, 4.4) }; n.spot = spot; }
    holdBall(n);
  }
  G.start = () => { turn = -1; nextTurn(); };
  G.update = dt => {
    if (G.over) return; t += dt; const p = cur();
    for (const q of players) if (!q.human && q !== p) X.aiMove(q.c, K.hx + (q === players[0] ? -2.2 : 2.2), K.z0 + 4.8, 1.6, K.hx, K.rimZ);   // 沒輪到的電腦站在一旁
    if (G.phase === 'ready') {
      if (p.human) { if (charging) charge = Math.min(1, charge + dt / 2.2); holdBall(p); }
      else { X.aiMove(p.c, p.spot.x, p.spot.z, 2.2, K.hx, K.rimZ); const dd = Math.hypot(p.c.object3D.position.x - p.spot.x, p.c.object3D.position.z - p.spot.z); holdBall(p); if (dd < 0.35) { wait += dt; if (wait > aiReady) { const id = ideal(p), v = id.v * (1 + gauss() * 0.09); shoot(p, v); } } }
    } else if (G.phase === 'flight') {
      settleT += dt; step(dt);
      if (settleT > (scored ? 2.0 : 5.5) || (b.y <= br + 0.01 && Math.hypot(b.vx, b.vz) < 0.2 && settleT > 0.6)) {
        if (scored) { p.score++; X.point && X.point(p, players.find(q => q !== p) || null, { why: '進球', score: Object.fromEntries(players.map(q => [q.id, q.score])), shots: p.shots }); G.stats.made++; X.hitFx && X.hitFx('score', b); } else X.say && X.say(`${p.human ? '你' : p.c.spec.nick}沒進`, 1.2);
        G.phase = 'pause'; wait = 0;
      }
    } else if (G.phase === 'pause') { step(dt); wait += dt; if (wait > 1.1) nextTurn(); }
    X.ballAt && X.ballAt('basketball', b, G.phase);
  };
  function step(dt) {
    const py = b.y; b.vy -= G0 * dt; b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
    // 地面
    if (b.y < br && b.vy < 0) { b.y = br; if (Math.abs(b.vy) > 0.9) { b.vy = -b.vy * 0.72; G.stats.bounces++; } else b.vy = 0; b.vx *= 0.97; b.vz *= 0.97; if (b.vy === 0) { b.vx *= 0.985; b.vz *= 0.985; } }
    // 籃板
    if (b.vz < 0 && b.z - br < K.boardZ + 0.03 && b.z > K.boardZ - 0.12 && Math.abs(b.x - K.hx) < 0.65 + br && b.y > 1.95 && b.y < 2.9) { b.z = K.boardZ + 0.03 + br; b.vz = -b.vz * 0.55; b.vx *= 0.92; G.stats.board++; }
    // 籃框（把框當成一圈的圓環，取球心到環上最近點）
    const dx = b.x - K.hx, dz = b.z - K.rimZ, h = Math.hypot(dx, dz) || 1e-6, qx = K.hx + dx / h * R, qz = K.rimZ + dz / h * R, nx = b.x - qx, ny = b.y - K.rimY, nz = b.z - qz, d = Math.hypot(nx, ny, nz);
    if (d < br + 0.03 && d > 1e-6) {
      const ux = nx / d, uy = ny / d, uz = nz / d, vn = b.vx * ux + b.vy * uy + b.vz * uz;
      if (vn < 0) { const e = 0.55; b.vx -= (1 + e) * vn * ux; b.vy -= (1 + e) * vn * uy; b.vz -= (1 + e) * vn * uz; b.vx *= 0.95; b.vz *= 0.95; G.stats.rim++; }
      const pen = br + 0.03 - d; b.x += ux * pen; b.y += uy * pen; b.z += uz * pen;
    }
    // 穿過框面（由上往下、中心離框心夠近）算進球；穿過後網子讓球慢下來
    if (!scored && py > K.rimY && b.y <= K.rimY && Math.hypot(b.x - K.hx, b.z - K.rimZ) < R - 0.03 && b.vy < 0) { scored = true; }
    if (scored && !netDamp && b.y < K.rimY - 0.05 && Math.hypot(b.x - K.hx, b.z - K.rimZ) < R) { netDamp = true; b.vx *= 0.3; b.vz *= 0.3; b.vy *= 0.55; }
    // 球場外圍的看不見的圍欄（不要飛到外面去）
    if (b.x < K.x0 - 1.2 || b.x > K.x1 + 1.2) { b.x = clamp(b.x, K.x0 - 1.2, K.x1 + 1.2); b.vx = -b.vx * 0.5; } if (b.z > K.z1 + 1.2) { b.z = K.z1 + 1.2; b.vz = -b.vz * 0.5; } if (b.z < K.z0 - 0.3) { b.z = K.z0 - 0.3; b.vz = Math.abs(b.vz) * 0.5; }
  }
  G.hud = () => {
    const p = cur(), nm = q => (q.human ? '你' : q.c.spec.nick), sc = solo ? `你 ${players[0].score}/${players[0].shots} 球` : players.map(q => `${nm(q)} ${q.score}`).join(' : ');
    let tip, meter = null;
    if (G.phase === 'ready' && p.human) { const id = ideal(p); tip = '按住空白鍵蓄力、放開投籃（對準綠色刻度）'; meter = { v: charge, ideal: (id.v - vmin) / (vmax - vmin), tol: 0.07 }; }
    else if (G.phase === 'ready') tip = `${nm(p)} 準備投籃`; else tip = G.phase === 'flight' ? '球在空中…' : '';
    return { title: `籃球　${sc}${solo ? '' : `（各 ${SHOTS} 球）`}`, tip, meter };
  };
  G.end = () => { X.ballHide && X.ballHide(); };
  G.ideal = ideal;
  return G;
}

// ───────────────────────── 撞球 ─────────────────────────
export function createBilliards(X, players) {
  const T = LAY.table, r = T.r, hx = T.L / 2, hz = T.W / 2, G = { kind: 'billiards', zh: '撞球', players, over: false, winner: null, phase: 'aim', stats: { hits: 0, cushion: 0, pots: 0, shots: 0 }, T };
  const solo = players.length < 2, DT2 = 1 / 240;
  const COLS = ['#ffffff', '#f28b82', '#ffcf6b', '#93d18b', '#7ab8e8', '#b49be0', '#ff9ec0'];
  const B = COLS.map((c, i) => ({ i, x: 0, z: 0, vx: 0, vz: 0, in: true, col: c }));
  G.balls = B; const pockets = [[-hx, -hz], [hx, -hz], [-hx, hz], [hx, hz], [0, -hz], [0, hz]], PR = 0.115;
  for (const p of players) p.score = 0;
  let turn = 0, aimAng = 0, aimPow = 0, aiT = 0, aiShot = null, potThis = 0, scratch = false, restT = 0;
  function rack() {
    B[0].x = -hx * 0.5; B[0].z = 0; B[0].in = true; B[0].vx = B[0].vz = 0; let k = 1; const x0 = hx * 0.35, dx = r * 1.78, dz = r * 2.06;
    for (let row = 0; row < 3; row++) for (let j = 0; j <= row; j++) { const q = B[k++]; q.x = x0 + row * dx; q.z = (j - row / 2) * dz; q.vx = q.vz = 0; q.in = true; }
  }
  const cur = () => players[turn % players.length], moving = () => B.some(q => q.in && Math.hypot(q.vx, q.vz) > 0.01);
  G.start = () => { rack(); G.phase = 'aim'; turn = 0; potThis = 0; scratch = false; };
  // 檯面座標 ↔ 世界座標：世界 = 桌心 + (x, z)
  G.toTable = (wx, wz) => ({ x: wx - T.cx, z: wz - T.cz });
  G.canAim = () => G.phase === 'aim' && cur().human && !G.over;
  G.aim = (px, pz, down) => {            // 人拖曳：滑鼠點到的位置在白球的「反方向」＝拉桿；力道＝拉的距離
    if (!G.canAim()) return; const c = B[0], dx = c.x - px, dz = c.z - pz, d = Math.hypot(dx, dz); if (d < 0.02) return;
    aimAng = Math.atan2(dz, dx); aimPow = clamp(d / 0.9, 0, 1); G.aiming = down; G.aimOn = true;
  };
  G.release = () => { if (!G.canAim() || !G.aimOn) return; G.aimOn = false; if (aimPow < 0.08) { aimPow = 0; return; } fire(aimAng, aimPow); };
  function fire(ang, pow) { const c = B[0], v = 0.8 + pow * 4.8; c.vx = Math.cos(ang) * v; c.vz = Math.sin(ang) * v; G.phase = 'roll'; potThis = 0; scratch = false; restT = 0; G.stats.shots++; cur().c.setAction('think', { duration: 0.2 }); G.aimOn = false; G.aiming = false; X.hitFx && X.hitFx('cue', { x: T.cx + c.x, y: T.top + r, z: T.cz + c.z }); }
  function aiPlan() {
    const c = B[0]; let best = null;
    for (const q of B) { if (q.i === 0 || !q.in) continue; for (const [px, pz] of pockets) {
      const ex = px - q.x, ez = pz - q.z, el = Math.hypot(ex, ez) || 1, gx = q.x - ex / el * 2 * r, gz = q.z - ez / el * 2 * r, ax = gx - c.x, az = gz - c.z, al = Math.hypot(ax, az) || 1;
      const cut = Math.abs(((ax * ex + az * ez) / (al * el))); if (cut < 0.55) continue; const score = al + el * 0.7 + (1 - cut) * 2;
      let blocked = false; for (const o of B) { if (!o.in || o.i === 0 || o === q) continue; const t = ((o.x - c.x) * ax + (o.z - c.z) * az) / (al * al); if (t > 0 && t < 1) { const dd = Math.hypot(c.x + ax * t - o.x, c.z + az * t - o.z); if (dd < 2 * r) { blocked = true; break; } } }
      if (!blocked && (!best || score < best.score)) best = { ang: Math.atan2(az, ax), pow: clamp(0.25 + (al + el) * 0.32, 0.25, 0.85), score };
    } }
    if (!best) { const q = B.filter(o => o.i && o.in)[0]; best = q ? { ang: Math.atan2(q.z - c.z, q.x - c.x), pow: 0.5, score: 9 } : { ang: 0, pow: 0.4, score: 9 }; }
    best.ang += gauss() * deg(1.7); return best;
  }
  function collide() {
    const n = B.length;
    for (let i = 0; i < n; i++) { const a = B[i]; if (!a.in) continue; for (let j = i + 1; j < n; j++) { const c = B[j]; if (!c.in) continue;
      const dx = c.x - a.x, dz = c.z - a.z, d2 = dx * dx + dz * dz; if (d2 >= 4 * r * r || d2 < 1e-10) continue;
      const d = Math.sqrt(d2), nx = dx / d, nz = dz / d, rel = (a.vx - c.vx) * nx + (a.vz - c.vz) * nz;
      const pen = 2 * r - d; a.x -= nx * pen / 2; a.z -= nz * pen / 2; c.x += nx * pen / 2; c.z += nz * pen / 2;
      if (rel > 0) { const e = 0.96, jv = (1 + e) * rel / 2; a.vx -= jv * nx; a.vz -= jv * nz; c.vx += jv * nx; c.vz += jv * nz; G.stats.hits++; if (rel > 0.3) X.hitFx && X.hitFx('ball', { x: T.cx + (a.x + c.x) / 2, y: T.top + r, z: T.cz + (a.z + c.z) / 2 }); }
    } }
  }
  function sub(dt) {
    for (const q of B) {
      if (!q.in) continue; q.x += q.vx * dt; q.z += q.vz * dt; const sp = Math.hypot(q.vx, q.vz);
      if (sp > 0) { const ns = Math.max(0, sp - (0.55 + 0.25 * sp) * dt); const k = ns / sp; q.vx *= k; q.vz *= k; if (ns < 0.012) q.vx = q.vz = 0; }
      let pocketed = false; for (const [px, pz] of pockets) if (Math.hypot(q.x - px, q.z - pz) < PR) { pocketed = true; break; }
      if (pocketed) { q.in = false; q.vx = q.vz = 0; G.stats.pots++; if (q.i === 0) scratch = true; else { potThis++; cur().score++; X.point && X.point(cur(), players.find(o => o !== cur()) || null, { why: '進袋', ball: q.i, score: Object.fromEntries(players.map(o => [o.id, o.score])) }); } X.hitFx && X.hitFx('pot', { x: T.cx + q.x, y: T.top, z: T.cz + q.z }); continue; }
      const nearP = pockets.some(([px, pz]) => Math.hypot(q.x - px, q.z - pz) < PR + 0.08);
      if (!nearP) { if (q.x < -hx + r) { q.x = -hx + r; q.vx = Math.abs(q.vx) * 0.8; G.stats.cushion++; } else if (q.x > hx - r) { q.x = hx - r; q.vx = -Math.abs(q.vx) * 0.8; G.stats.cushion++; } if (q.z < -hz + r) { q.z = -hz + r; q.vz = Math.abs(q.vz) * 0.8; G.stats.cushion++; } else if (q.z > hz - r) { q.z = hz - r; q.vz = -Math.abs(q.vz) * 0.8; G.stats.cushion++; } }
      else { q.x = clamp(q.x, -hx - 0.1, hx + 0.1); q.z = clamp(q.z, -hz - 0.1, hz + 0.1); }
    }
    collide();
  }
  G.update = dt => {
    if (G.over) return; let n = Math.round(dt / DT2); n = Math.max(1, n);
    if (G.phase === 'roll') { for (let i = 0; i < n; i++) sub(DT2); if (!moving()) { restT += dt; if (restT > 0.25) endShot(); } }
    else if (G.phase === 'aim') {
      const p = cur(); if (!p.human) { aiT += dt; if (!aiShot) { aiShot = aiPlan(); aiT = 0; aimAng = aiShot.ang; aimPow = 0; G.aiming = true; } aimPow = Math.min(aiShot.pow, aimPow + dt * 0.7); if (aiT > 1.5) { const s = aiShot; aiShot = null; G.aiming = false; fire(s.ang, s.pow); } }
    } else if (G.phase === 'pause') { restT += dt; if (restT > 1.0) { G.phase = 'aim'; G.aiming = false; } }
    X.billAt && X.billAt(G);
  };
  function endShot() {
    const left = B.filter(q => q.i && q.in).length;
    if (!B[0].in) { B[0].in = true; B[0].x = -hx * 0.5; B[0].z = 0; B[0].vx = B[0].vz = 0; for (const q of B) if (q !== B[0] && q.in && Math.hypot(q.x - B[0].x, q.z - B[0].z) < 2 * r + 0.02) q.x += 0.12; }
    if (left === 0) { G.over = true; G.winner = solo ? players[0] : players.slice().sort((a, b) => b.score - a.score)[0]; if (!solo && players[0].score === players[1].score) G.winner = null; return; }
    if (!(potThis > 0 && !scratch)) { turn++; } G.phase = 'pause'; restT = 0; aimPow = 0; G.aimOn = false;
  }
  G.hud = () => {
    const p = cur(), nm = q => (q.human ? '你' : q.c.spec.nick), left = B.filter(q => q.i && q.in).length;
    const sc = solo ? `你 ${players[0].score} 顆（剩 ${left}）` : players.map(q => `${nm(q)} ${q.score}`).join(' : ') + `（剩 ${left}）`;
    return { title: `撞球　${sc}`, tip: G.phase === 'aim' ? (p.human ? '滑鼠拖曳：拉的方向的反面是出桿方向，拉越遠越用力，放開出桿' : `${nm(p)} 瞄準中…`) : G.phase === 'roll' ? '球在滾…' : '', meter: null };
  };
  G.aimState = () => ({ ang: aimAng, pow: aimPow, on: (G.phase === 'aim' && (G.aimOn || G.aiming)) });
  G.end = () => { X.ballHide && X.ballHide(); };
  return G;
}
