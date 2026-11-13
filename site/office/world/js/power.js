// 額度＝電力（擁有者原話：「會顯示目前額度剩下多少，沒額度會反應 Agent 都會自動睡覺」）。
// 這支只讀狀態層（state.js）的額度與事件，做五件事：
//   ① 頂列膠囊「電力 62%」＋點開看兩個時間窗（5 小時、本週）與重置時間（台北時間）
//   ② CEO 辦公室後牆的電力表（兩條電量條；沒資料畫灰色虛線，不假裝有）
//   ③ 剩 20% 轉琥珀並提示一次（同一個重置週期不重複）、剩 10% 進入節電氣氛（燈光 85%）
//   ④ 額度用完：CEO 宣布 → 散會、全員回座 → 趴睡、燈光漸暗到 35% → 門口掛牌「休息中・額度恢復 HH:MM」＋倒數
//   ⑤ 恢復：CEO 先醒、其他人依座位順序陸續醒；睡覺中又收到工作事件＝資料有誤，全員立刻醒來
// 規則（設計決定，見交件說明）：
//   · 額度資料沒提供（null）＝灰色虛線＋「未提供」，不演預警也不演睡覺；只有「用完」才睡。
//   · 被你操控中的角色不睡（仍可操控）；放開後他走回座位，之後才趴下。
//   · 睡覺期間點角色的資訊卡、摸頭都照常，他只是不會自己去做別的事。
import { THREE } from './kit.js';
import { hhmm, wk, span } from './state.js';

const $ = id => document.getElementById(id);
const rnd = (a, b) => a + Math.random() * (b - a);
const DIM_SLEEP = 0.35, DIM_MILD = 0.85;
const WORK_EVENTS = new Set(['SessionStart', 'UserPromptSubmit', 'SubagentStart', 'SubagentStop', 'PreToolUse', 'Notification']);

export function createPower(W, X) {
  const { state: S, ui, director: D } = X, C = id => W.chars.get(id);
  const P = { phase: 'awake', tok: 0, wakeOrder: [], sleepOrder: [], signText: '', meterModel: {}, warned: new Set(), mildDone: false, dimTarget: 1, dimRate: 1, signK: 0, signShow: false, staleMs: 15 * 60e3 };
  W.dim = 1;
  const reduce = () => !!(W.reduceMotion || (matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches));
  const people = () => [...W.chars.values()].filter(c => !c.away && !c.jobless);
  const seatOrder = () => people();            // W.chars 依編制順序建立：CEO 先、其後各部門依座位順序

  // ───────── ① 頂列膠囊與說明 ─────────
  const bar = $('bar'), pill = document.createElement('button'); pill.className = 'btn pw na'; pill.id = 'pwBtn'; pill.setAttribute('aria-haspopup', 'true'); pill.setAttribute('aria-expanded', 'false');
  pill.innerHTML = `<span class="pw-ic" aria-hidden="true"></span><span class="pw-t" id="pwTxt">電力 未提供</span>`;
  bar.insertBefore(pill, $('editBtn'));
  const pop = document.createElement('div'); pop.className = 'pop pw-pop'; pop.id = 'pwPop'; pop.hidden = true; $('app').append(pop);
  let noteOpen = false;
  const rowOf = (name, w) => `<div class="pw-row"><span>${name}</span>${w ? `<b>${w.remain}%</b><em>${w.resetsAt ? (name === '本週' ? wk(w.resetsAt) + ' ' : '') + hhmm(w.resetsAt) + ' 重置' : '重置時間未提供'}</em>` : '<b class="na">未提供</b><em></em>'}</div>`;
  function renderPop() {
    const Q = S.quotaInfo(), age = S.q.asOf ? Math.round((S.now() - S.q.asOf) / 60000) : null;
    const html = rowOf('5 小時', Q.five) + rowOf('本週', Q.week) +
      (Q.exhausted ? `<div class="pw-state">休息中・${Q.resetKnown ? '額度恢復 ' + hhmm(Q.resetsAt) + '（台北）' : '恢復時間未提供'}</div>` : '') +
      `<div class="pw-foot"><span>${age == null ? '' : `資料更新於 ${age < 1 ? '剛剛' : age + ' 分鐘前'}`}</span><button class="q" id="pwQ" aria-label="這是什麼" aria-expanded="${noteOpen}">?</button></div>` +
      `<p class="pw-note" ${noteOpen ? '' : 'hidden'}>${Q.provided ? '剩餘比例取兩個時間窗裡較少的那個。時間一律是台北時間。' : '這個接入沒有回報額度，所以不顯示剩餘比例；額度用完時，才會看到大家去睡覺。'}</p>`;
    if (html !== pop._html) { pop._html = html; pop.innerHTML = html; }   // 內容沒變就不重畫：每秒重畫會把正在按的按鈕換掉，按了沒反應
  }
  pop.addEventListener('click', e => { if (e.target.closest('#pwQ')) { noteOpen = !noteOpen; renderPop(); } });
  function placePop() { const r = pill.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; }
  pill.onclick = () => { const was = pop.hidden; ui.closePops(); pop.hidden = !was; pill.setAttribute('aria-expanded', String(was)); if (was) { renderPop(); placePop(); } };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#pwPop') && !e.target.closest('#pwBtn')) { pop.hidden = true; pill.setAttribute('aria-expanded', 'false'); } });
  addEventListener('resize', () => { if (!pop.hidden) placePop(); });

  // 門牌（HTML 版，貼在頂列下方；3D 版掛在大門上）
  const signEl = document.createElement('div'); signEl.className = 'pw-sign'; signEl.id = 'pwSign'; signEl.hidden = true; signEl.setAttribute('role', 'status'); $('app').append(signEl);

  // ───────── ② 電力表（CEO 辦公室北牆）與 ④ 大門的牌子：都是畫布貼圖，各一個網格 ─────────
  const mCv = document.createElement('canvas'); mCv.width = 512; mCv.height = 320;
  const mTex = new THREE.CanvasTexture(mCv); mTex.colorSpace = THREE.SRGBColorSpace; mTex.anisotropy = 4;
  const meter = new THREE.Mesh(new THREE.PlaneGeometry(1.3, 0.81), new THREE.MeshBasicMaterial({ map: mTex, transparent: true })); meter.position.set(4.0, 1.38, 0.16); meter.renderOrder = 2; W.scene.add(meter);
  P.meter = meter; P.meterCanvas = mCv;
  const font = (px, w = 800) => `${w} ${px}px "Noto Sans TC","PingFang TC","Microsoft JhengHei","WenQuanYi Zen Hei",sans-serif`;
  const rr = (c, x, y, w, h, r) => { c.beginPath(); c.roundRect(x, y, w, h, r); };
  const FILL = { ok: '#6cc08b', low: '#f2a93b', mild: '#ef7a3a', out: '#cfc8c0' };
  function drawMeter() {
    const c = mCv.getContext('2d'), Q = S.quotaInfo(), stale = S.q.asOf && S.now() - S.q.asOf > P.staleMs;
    c.clearRect(0, 0, 512, 320); c.globalAlpha = stale ? 0.55 : 1;
    c.fillStyle = '#fffaf2'; rr(c, 4, 4, 504, 312, 34); c.fill(); c.lineWidth = 8; c.strokeStyle = Q.level === 'low' || Q.level === 'mild' ? '#f2a93b' : '#e7c9a3'; rr(c, 6, 6, 500, 308, 32); c.stroke();
    const bars = [['5 小時', Q.five, 58], ['本週', Q.week, 178]];
    P.meterModel = { level: Q.level };
    for (const [name, w, y] of bars) {
      c.fillStyle = '#7a665a'; c.font = font(40, 800); c.textAlign = 'left'; c.textBaseline = 'alphabetic'; c.fillText(name, 34, y + 36);
      const x = 34, bw = 444, by = y + 52, bh = 50;
      c.fillStyle = '#efe3d3'; rr(c, x, by, bw, bh, 22); c.fill();
      let frac = 0, dashed = false;
      if (Q.exhausted) frac = 0;
      else if (w) frac = w.remain / 100; else dashed = true;
      if (dashed) { c.setLineDash([14, 10]); c.lineWidth = 5; c.strokeStyle = '#a89c92'; rr(c, x + 2, by + 2, bw - 4, bh - 4, 20); c.stroke(); c.setLineDash([]); c.fillStyle = '#a89c92'; c.font = font(34, 700); c.textAlign = 'center'; c.fillText('未提供', x + bw / 2, by + 36); }
      else if (frac > 0) { const lv = Q.level === 'ok' ? 'ok' : Q.level; c.fillStyle = FILL[(w && w.remain <= S.cfg.lowPct) ? (w.remain <= S.cfg.mildPct ? 'mild' : 'low') : 'ok']; rr(c, x, by, Math.max(bh, bw * frac), bh, 22); c.fill(); }
      if (!dashed) { c.strokeStyle = 'rgba(122,102,90,.35)'; c.lineWidth = 3; for (const t of [0.25, 0.5, 0.75]) { c.beginPath(); c.moveTo(x + bw * t, by + 6); c.lineTo(x + bw * t, by + bh - 6); c.stroke(); } c.fillStyle = '#7a665a'; c.font = font(34, 800); c.textAlign = 'right'; c.fillText(Q.exhausted ? '0%' : w ? w.remain + '%' : '', 478, y + 36); }
      P.meterModel[name === '本週' ? 'week' : 'five'] = { frac, dashed, color: dashed ? 'dashed' : FILL[w && w.remain <= S.cfg.lowPct ? (w.remain <= S.cfg.mildPct ? 'mild' : 'low') : 'ok'] };
    }
    c.globalAlpha = 1; mTex.needsUpdate = true;
  }

  // 大門的牌子：外面一面（朝南）、裡面一面（朝北），共用一張貼圖；平時隱藏，不佔繪製次數
  const sCv = document.createElement('canvas'); sCv.width = 512; sCv.height = 196;
  const sTex = new THREE.CanvasTexture(sCv); sTex.colorSpace = THREE.SRGBColorSpace; sTex.anisotropy = 4;
  const sMat = new THREE.MeshBasicMaterial({ map: sTex, transparent: true }), sGeo = new THREE.PlaneGeometry(1.9, 0.727);
  const signOut = new THREE.Mesh(sGeo, sMat), signIn = new THREE.Mesh(sGeo, sMat);
  signOut.position.set(20.5, 1.85, 30.3); signIn.position.set(20.5, 1.85, 29.7); signIn.rotation.y = Math.PI;
  signOut.visible = signIn.visible = false; signOut.renderOrder = signIn.renderOrder = 3; W.scene.add(signOut, signIn); P.signMeshes = [signOut, signIn];
  let signKey = '';
  function drawSign(l1, l2, l3) {
    const key = l1 + l2 + l3; if (key === signKey) return; signKey = key;
    const c = sCv.getContext('2d'); c.clearRect(0, 0, 512, 196);
    c.fillStyle = '#fff3d6'; rr(c, 4, 4, 504, 188, 36); c.fill(); c.lineWidth = 9; c.strokeStyle = '#ffb86b'; rr(c, 8, 8, 496, 180, 32); c.stroke();
    c.textAlign = 'center'; c.fillStyle = '#5a4638'; c.font = font(62, 800); c.fillText(l1, 256, 78);
    c.font = font(l2.length > 14 ? 30 : 36, 700); c.fillStyle = '#7a5a40'; c.fillText(l2, 256, 126);
    if (l3) { c.font = font(28, 600); c.fillStyle = '#9a8576'; c.fillText(l3, 256, 168); }
    sTex.needsUpdate = true;
  }
  function renderSign() {
    const Q = S.quotaInfo(); let l1, l2, l3 = '';
    if (P.phase === 'waking' && P.signText === '已恢復') { l1 = '已恢復'; l2 = '大家上工了'; }
    else if (Q.exhausted) { l1 = '休息中'; if (Q.resetKnown) { l2 = `額度恢復 ${hhmm(Q.resetsAt)}（台北）`; l3 = span(Q.resetsAt - S.now()); } else l2 = '恢復時間未提供'; }
    else return;
    P.signText = l1 === '已恢復' ? '已恢復' : `${l1}・${l2.replace('（台北）', '')}`;
    drawSign(l1, l2, l3);
    const sh = `<b>${l1}</b><span>${l2}</span>${l3 ? `<i>${l3}</i>` : ''}`; if (sh !== signEl._html) { signEl._html = sh; signEl.innerHTML = sh; }
  }

  // ───────── 膠囊／電力表／門牌的整體更新 ─────────
  let lastKey = '';
  function refresh(force) {
    const Q = S.quotaInfo(), stale = S.q.asOf && S.now() - S.q.asOf > P.staleMs;
    const age = stale ? Math.round((S.now() - S.q.asOf) / 60000) : 0;
    let txt = Q.exhausted ? '電力 0%・休息中' : Q.remain == null ? '電力 未提供' : `電力 ${Q.remain}%`;
    if (stale && !Q.exhausted && Q.remain != null) txt += `（${age} 分鐘前）`;
    const lv = Q.level; pill.className = 'btn pw ' + lv + (stale ? ' stale' : ''); pill.dataset.level = lv; pill.style.setProperty('--pw', (Q.exhausted ? 0 : (Q.remain || 0)) + '%');
    if ($('pwTxt').textContent !== txt) $('pwTxt').textContent = txt;
    pill.setAttribute('aria-label', txt + (lv === 'low' || lv === 'mild' ? '，電力吃緊' : ''));
    const key = JSON.stringify([Q.five, Q.week, Q.exhausted, lv, !!stale, P.phase]);
    if (key !== lastKey || force) { lastKey = key; drawMeter(); }
    if (!pop.hidden) { renderPop(); placePop(); }
    if (Q.exhausted || P.signText === '已恢復') renderSign();
    document.body.classList.toggle('pw-sign', !!P.signShow);   // 牌子出現時，提示（toast）改放畫面下方，不蓋到牌子
    signEl.hidden = !P.signShow; if (signEl.hidden) signEl.removeAttribute('data-on'); else signEl.dataset.on = '1';
    const showMesh = P.signShow && P.signK > 0.02; signOut.visible = signIn.visible = showMesh;
    // 手機：牌子放在頂列下方，位置會隨頂列高度變，這裡隨時對一次
    if (P.signShow) {                  // 牌子貼在頂列下方；窄螢幕時頂列下方還有鏡頭提示與時間小字，要再往下讓
      let bt = bar.getBoundingClientRect().bottom; if (innerWidth < 1180) for (const el of [document.querySelector('.cm-hint'), document.querySelector('.dt-chip')]) if (el && el.offsetParent) bt = Math.max(bt, el.getBoundingClientRect().bottom);
      signEl.style.top = Math.round(bt + 6) + 'px';
    }
  }
  P.refresh = refresh;

  // ───────── ③ 預警：剩 20%、10% ─────────
  function warnCheck(e, ctx) {
    const Q = S.quotaInfo(); if (Q.exhausted || Q.remain == null) return;
    const lim = [Q.five, Q.week].filter(Boolean).sort((a, b) => a.remain - b.remain)[0], key = String(lim && lim.resetsAt || 'na');
    if (Q.remain <= S.cfg.lowPct && !P.warned.has('low' + key)) {
      P.warned.add('low' + key); ui.toast(`電力剩 ${Q.remain}%${lim.resetsAt ? '，約 ' + hhmm(lim.resetsAt) + ' 重置' : ''}`);
      const ceo = C('ceo'); if (ceo && !ceo.piloted && !P.sleeping()) { ceo.emote('sweat', 2.4); }
    }
    if (Q.remain <= S.cfg.mildPct && !P.warned.has('mild' + key)) { P.warned.add('mild' + key); ui.toast('電力吃緊，大家開始省著用'); }
    if (Q.remain > S.cfg.lowPct) { P.warned.clear(); }          // 回到安全區（新的重置週期）才重新計次
    if (P.phase === 'awake') P.dimTo(Q.remain <= S.cfg.mildPct ? DIM_MILD : 1, 1.5);
  }

  // ───────── 燈光漸變 ─────────
  P.dimTo = (v, sec) => { P.dimTarget = v; P.dimRate = Math.abs(v - W.dim) / Math.max(0.05, sec); if (reduce() || sec <= 0) { W.dim = v; X.daytime.applyDim(); } };
  P.frame = dt => {
    if (Math.abs(W.dim - P.dimTarget) > 1e-4) { const d = P.dimTarget - W.dim, st = Math.min(Math.abs(d), P.dimRate * dt); W.dim += Math.sign(d) * st; X.daytime.applyDim(); }
    // 牌子垂下／收起
    const want = P.signShow ? 1 : 0; if (Math.abs(P.signK - want) > 0.001) { P.signK += Math.sign(want - P.signK) * Math.min(Math.abs(want - P.signK), dt * 1.2); const y = 2.5 - 0.65 * P.signK; signOut.position.y = signIn.position.y = y; signOut.visible = signIn.visible = P.signShow ? P.signK > 0.02 : P.signK > 0.02; }
    else if (!P.signShow) signOut.visible = signIn.visible = false;
  };

  // ───────── ④ 睡覺與 ⑤ 醒來 ─────────
  P.sleeping = () => P.phase === 'declare' || P.phase === 'asleep';
  const snapHome = c => {               // 動作減量：不走路，直接坐回自己的位子
    const s = c.homeSpot || W.spots.find(q => q.name === 'seat:' + c.spec.id); if (!s || !s.seat) return;
    c.stop(false); D.release(c); s.taken = c.spec.id; c.spot = s; c.sitAt(s.seat, { instant: true }); c.atDesk = true;
  };
  const sleepOne = c => { c.sleeping = true; c.busy = true; c.script = (c.script || 0) + 1; c.setAction('sleep'); c.emote('zzz', 3); c.setExpression('sleepy', 1e9); P.sleepOrder.push(c.spec.id); };
  async function sleepSeq() {
    const tok = ++P.tok; P.phase = 'declare'; P.sleepOrder = []; D.hold = true; P.signShow = false;
    const ceo = C('ceo'); ui.toast('電力用完了，大家先睡一下');
    if (ceo && !ceo.piloted) { ceo.script = (ceo.script || 0) + 1; ceo.setAction('raise'); ceo.emote('battery', 2.4); ceo.say('電力用完了，大家先休息吧', 3); }
    await W.sleep(reduce() ? 0.05 : 1.5); if (tok !== P.tok) return;
    const gone = D.cancelMeeting('因額度用完提前散會'); if (gone) ui.toast('額度用完，會議提前散會');
    const walkers = seatOrder().filter(c => !c.spec.isCeo && !c.piloted);
    for (const c of walkers) {
      if (c.state === 'sit' && c.atDesk) continue;
      if (reduce()) { snapHome(c); continue; }
      c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.setAction('idle'); D.goHome(c, { speed: 3.2 });
    }
    if (ceo && !ceo.atDesk && !ceo.piloted) { if (reduce()) snapHome(ceo); else D.goHome(ceo, { speed: 3 }); }
    for (let i = 0; i < 40; i++) { if (walkers.every(c => c.piloted || (c.state === 'sit' && c.atDesk)) ) break; await W.sleep(0.3); if (tok !== P.tok) return; }
    P.dimTo(DIM_SLEEP, 3);
    for (const c of seatOrder().filter(c => !c.spec.isCeo)) { if (c.piloted) continue; sleepOne(c); await W.sleep(reduce() ? 0 : 0.1); if (tok !== P.tok) return; }
    for (const p of W.pets || []) { p.stop(false); p.setAction('sleep'); p.busyUntil = 1e9; }
    if (ceo && !ceo.piloted) { await W.sleep(reduce() ? 0 : 0.4); if (tok !== P.tok) return; sleepOne(ceo); }
    await W.sleep(reduce() ? 0 : 1.2); if (tok !== P.tok) return;
    P.signShow = true; if (reduce()) P.signK = 1; renderSign(); refresh(true);
    P.phase = 'asleep'; P.sleptAt = W.time; P.sleepLoopAt = 0;
  }
  async function wakeSeq(fast, label) {
    const tok = ++P.tok; P.phase = 'waking'; P.wakeOrder = []; P.dimTo(1, fast ? 1 : 3);
    if (fast) { P.signShow = false; } else { P.signText = '已恢復'; P.signShow = true; renderSign(); }
    refresh(true);
    ui.toast(label || '額度恢復了，大家上工');
    const step = reduce() ? 0 : fast ? 0.08 : 0.4;
    for (const c of seatOrder()) {
      if (tok !== P.tok) return;
      if (c.sleeping) { c.sleeping = false; c.setExpression('neutral', 0.1); c.setAction('stretch', { then: 'type' }); c.emote('star', 1.2); if (c.spec.isCeo) c.say('額度恢復了，大家上工！', 2.6); }
      P.wakeOrder.push({ id: c.spec.id, t: W.time }); await W.sleep(step);
    }
    for (const p of W.pets || []) { p.setAction('idle'); p.busyUntil = W.time + 1; }
    if (tok !== P.tok) return;
    D.hold = false; for (const c of seatOrder()) { c.busy = !!(W.jobs && W.jobs.holds(c)); c.workAt = W.time + rnd(3, 7); }
    P.phase = 'awake'; await W.sleep(reduce() ? 0 : 2); if (tok !== P.tok) return;
    P.signShow = false; P.signText = ''; refresh(true);
  }
  P.wakeAll = (fast, label) => { if (P.phase === 'awake') return; wakeSeq(fast, label); };

  // 睡覺中的「維持」：放開操控的人走回座位後趴下、被拎走又放下的人回座位、動作被別的事蓋掉就補回來
  P.keep = () => {
    if (P.phase !== 'asleep') return;
    for (const c of seatOrder()) {
      if (c.piloted) { if (c.sleeping) { c.sleeping = false; } continue; }
      if (c.sleeping) { if (c.action !== 'sleep' && !c._until && c.state === 'sit') c.setAction('sleep'); continue; }
      if (c.state === 'sit' && c.atDesk) sleepOne(c);
      else if (c.state === 'stand' && !c.piloted && c.state !== 'held') { c.busy = true; D.sendHome(c); }
    }
  };
  P.tick = () => { if (P.phase === 'asleep' && W.time >= (P.sleepLoopAt || 0)) { P.sleepLoopAt = W.time + 0.5; P.keep(); } };

  // ───────── 事件進來 ─────────
  S.on((e, _s, ctx) => {
    const nowOut = S.q.exhausted;
    if (nowOut && !ctx.wasExhausted) { sleepSeq(); refresh(true); return; }
    if (!nowOut && ctx.wasExhausted) { P.wakeAll(false); refresh(true); return; }
    if (nowOut && P.phase !== 'awake' && WORK_EVENTS.has(e.name)) {           // 睡著時收到工作事件＝畫面與真實不符：立刻全員醒來
      S.q.exhausted = false; S.q.resetsAt = null; P.wakeAll(true, '資料已更正，大家醒了'); refresh(true); return;
    }
    warnCheck(e, ctx); refresh();
  });
  setInterval(() => { S.tick(); refresh(); }, 1000);
  refresh(true);
  return P;
}
