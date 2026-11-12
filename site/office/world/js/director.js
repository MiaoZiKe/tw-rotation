// 導演：把事件（會議、任務、上下班、日常活動）變成角色的行為。
// 階段 2 接後端後，伺服器推來的事件直接丟給 director.play(events) 即可。
export function createDirector(W, ui) {
  const D = { meeting: null, running: false, ambient: true, log: [], stage: '' };
  const sleep = W.sleep, C = id => W.chars.get(id), rnd = a => a[Math.floor(Math.random() * a.length)];
  const pos = c => ({ x: c.object3D.position.x, z: c.object3D.position.z });

  function release(c) { if (c.spot) { if (c.spot.taken === c.spec.id) c.spot.taken = null; c.spot = null; } }
  function claim(c, s) { release(c); s.taken = c.spec.id; c.spot = s; }

  // 走到一個目標點（有座位就坐下）。回傳 true 表示走到；被新的指令打斷回傳 false。
  async function goTo(c, s, o = {}) {
    if (!s) return false; const job = c.job = (c.job || 0) + 1;
    const from = pos(c), wasSeat = c.state === 'sit' ? c.spot : null; c.atDesk = false;
    claim(c, s);
    let path = W.nav.findPath(wasSeat ? { x: wasSeat.x, z: wasSeat.z } : from, { x: s.x, z: s.z });
    if (!path) { path = [from, { x: s.x, z: s.z }]; c.noPath = (c.noPath || 0) + 1; W.stats.noPath++; }
    if (wasSeat) path.unshift(from);
    if (s.seat) path.push({ x: s.seat.x, z: s.seat.z });
    W.stats.walks++;
    const ok = await c.walkTo(path, { speed: o.speed || 1.7 });
    if (c.job !== job) return false;
    if (!ok) { W.stats.interrupted++; return false; }
    if (s.seat) c.sitAt(s.seat); else c.standAt(s.x, s.z, s.face);
    return true;
  }
  async function goHome(c, o) {
    const s = W.spots.find(q => q.name === 'seat:' + c.spec.id); if (!s) return false;
    const ok = await goTo(c, s, o); if (ok) { c.atDesk = true; c.setAction('type'); } return ok;
  }
  D.goTo = goTo; D.goHome = goHome;

  // ───────── 會議 ─────────
  const KIND = { open: '開場', assign: '交代', ack: '確認', question: '提問', add: '補充', object: '反對', agree: '附和', risk: '提醒', summary: '總結' };
  async function meetingStart(ev) {
    const ceo = C(ev.by), att = ev.attendees.map(C).filter(Boolean), all = [ceo, ...att];
    D.meeting = { id: ev.meeting, topic: ev.topic, source: ev.source, people: all, lines: [], notes: [] }; D.stage = '召集';
    all.forEach(c => { c.busy = true; c.script = (c.script || 0) + 1; });
    ui.meetingOpen(D.meeting); W.whiteboard && W.whiteboard.set(ev.topic);
    ceo.say('開會囉！' + att.map(c => c.spec.nick).join('、') + '，會議室集合。', 3); ceo.setAction('raise');
    await sleep(0.9);
    att.forEach(c => { c.emote('!', 1.4); c.setAction('raise'); });
    await sleep(0.7); D.stage = '走去會議室';
    const seats = W.findSpots('meet'); seats.forEach(s => { s.taken = null; });
    const jobs = all.map((c, i) => (async () => { await sleep(i * 0.22); const ok = await goTo(c, seats[i % seats.length], { speed: 3.1 }); c.setAction(i % 2 ? 'note' : 'listen'); return ok; })());
    await Promise.all(jobs); D.stage = '討論';
    await sleep(0.5);
  }
  async function meetingSay(ev) {
    const m = D.meeting, c = C(ev.who); if (!m || !c) return;
    const dur = Math.max(2.3, Math.min(4.6, 1.5 + ev.text.length * 0.085));
    const sp = pos(c);
    m.people.forEach(o => { if (o !== c && o.state === 'sit') { /* 轉頭看發言者 */ o.faceTo(sp.x, sp.z); } });
    if (ev.to && C(ev.to)) { const t = pos(C(ev.to)); c.faceTo(t.x, t.z); } else if (c.spot && c.spot.seat) c.heading = c.spot.seat.face;
    c.say(ev.text, dur); c.speech.kind = ev.kind;
    const others = m.people.filter(o => o !== c);
    if (ev.kind === 'question') { c.setExpression('think'); c.setAction('raise', { duration: 1.4 }); }
    else if (ev.kind === 'object') { c.setExpression('angry'); c.setAction('angry', { duration: dur }); sleep(0.6).then(() => others.slice(0, 3).forEach(o => o.setExpression('surprised'))); }
    else if (ev.kind === 'agree') { c.setExpression('happy'); sleep(0.5).then(() => others.forEach((o, i) => i % 2 && o.setAction('nod'))); }
    else if (ev.kind === 'risk') { c.setExpression('surprised'); c.setAction('raise', { duration: 1.2 }); }
    else if (ev.kind === 'summary') { c.setExpression('proud'); }
    else if (ev.kind === 'ack' || ev.kind === 'add') { sleep(0.8).then(() => rnd(others).setAction('nod')); }
    m.lines.push({ who: c.spec.nick, kind: KIND[ev.kind] || '', k: ev.kind, text: ev.text, ts: ev.ts }); ui.meetingLine(m);
    await sleep(dur + 0.25);
  }
  async function meetingNote(ev) { const m = D.meeting; if (!m) return; W.whiteboard && W.whiteboard.add(ev.text); m.notes.push(ev.text); m.lines.push({ who: '白板', kind: '重點', k: 'note', text: ev.text, ts: ev.ts }); ui.meetingLine(m); D.stage = '白板重點'; await sleep(0.7); D.stage = '討論'; }
  async function meetingEnd(ev) {
    const m = D.meeting; if (!m) return; D.stage = '散會';
    m.people.forEach(c => { c.setAction('clap'); c.emote('♪', 1.4); }); await sleep(1.5);
    if (ev.post_to) ui.postBoard(ev.post_to, { t: ui.fmtTs(ev.ts), title: '會議結論', text: ev.summary });
    m.lines.push({ who: '結論', kind: '已貼上佈告欄', k: 'end', text: ev.summary, ts: ev.ts }); ui.meetingLine(m);
    const jobs = m.people.map((c, i) => (async () => { await sleep(i * 0.25); const ok = await goHome(c, { speed: 2.3 }); c.busy = false; return ok; })());
    await Promise.all(jobs); D.stage = '回座位工作'; ui.meetingClosed(m); D.meeting = null;
  }
  const TOOL = { edit: ['type', '!'], search: ['read', '?'], read: ['read', '…'], wait: ['think', '…'] };
  async function taskStarted(ev) {
    const c = C(ev.who); if (!c) return; const [act, sym] = TOOL[ev.tool] || TOOL.edit;
    c.emote(sym, 1.6); c.task = ev.title;
    if (ev.tool === 'search') routine(c, 'lookup'); else c.setAction(act);
    await sleep(0.4);
  }
  async function taskDone(ev) {
    const c = C(ev.who), boss = C(ev.report_to || 'ceo'); if (!c || !boss) return; D.stage = '向 CEO 報告';
    c.busy = true; c.script = (c.script || 0) + 1; c.emote('!', 1.2); c.setAction('cheer', { duration: 1 }); await sleep(1);
    const ok = await goTo(c, W.spot('ceo_front', pos(c), c.spec.id), { speed: 2.4 });
    if (ok) {
      const b = pos(boss); c.faceTo(b.x, b.z); c.say(ev.summary, 3.6); c.speech.kind = 'ack'; await sleep(3.7);
      if (ev.reply) { boss.say(ev.reply, 2.6); boss.speech.kind = 'summary'; boss.setAction('nod'); await sleep(2.7); }
      c.setExpression('happy'); await sleep(0.6);
    }
    await goHome(c, { speed: 2 }); c.busy = false; D.stage = '';
  }

  // ───────── 日常行為 ─────────
  const ROUTINES = {
    async coffee(c) { if (await goTo(c, W.spot('coffee', null, c.spec.id))) { c.setAction('drink', { duration: 2.6 }); c.emote('♪', 2); await sleep(2.8); } },
    async water(c) { if (await goTo(c, W.spot('water', null, c.spec.id))) { c.setAction('drink', { duration: 2 }); await sleep(2.2); } },
    async lookup(c) { if (await goTo(c, W.spot('library', null, c.spec.id))) { c.setAction('read'); c.emote('?', 1.6); await sleep(2.4); c.emote('!', 1.2); await sleep(1.4); c.setAction('idle'); } },
    async rest(c) { if (await goTo(c, W.spot(rnd(['sofa', 'sofa', 'bean']), null, c.spec.id))) { c.setAction('sleep'); c.emote('…', 2.4); await sleep(5); c.setAction('idle'); } },
    async snack(c) { if (await goTo(c, W.spot(rnd(['snack', 'dine']), null, c.spec.id))) { c.setAction('drink', { duration: 2.4 }); c.emote('♪', 1.8); await sleep(3); } },
    async play(c) { if (await goTo(c, W.spot('play', null, c.spec.id))) { c.setAction('cheer', { duration: 3 }); c.emote('☆', 2); await sleep(3.2); } },
    async board(c) { const s = W.spot('board:' + c.spec.dept, null, c.spec.id); if (s && await goTo(c, s)) { c.setAction('read'); await sleep(2.6); c.setAction('nod'); await sleep(1); c.setAction('idle'); } },
    async chat(c) { if (await goTo(c, W.spot('chat', null, c.spec.id))) { c.say(rnd(['今天咖啡不錯', '那批推上去了嗎？', '等等一起吃飯', '剛剛驗收過了']), 2.2); await sleep(2.6); } }
  };
  async function routine(c, name) {
    if (c.away) return; const tok = c.script = (c.script || 0) + 1; c.busy = true;
    try { await ROUTINES[name](c); } catch (e) { console.error(e); }
    if (c.script !== tok) return;            // 中途被叫去開會或報告，就不要再自己走回座位
    if (!c.away) await goHome(c);
    if (c.script === tok) c.busy = false;
  }
  D.routine = (id, name) => { const c = id ? C(id) : pickIdle(); if (c) return routine(c, name); };
  function pickIdle() { const pool = [...W.chars.values()].filter(c => !c.busy && !c.away && !c.spec.isCeo && c.state === 'sit' && c.atDesk); return pool.length ? rnd(pool) : null; }
  let nextAmb = 3;
  D.tick = () => {
    if (!D.ambient || W.time < nextAmb) return; nextAmb = W.time + 2.2 + Math.random() * 2.6;
    const out = [...W.chars.values()].filter(c => c.busy && !(D.meeting && D.meeting.people.includes(c))).length; if (out >= 7) return;
    const c = pickIdle(); if (c) routine(c, rnd(['coffee', 'coffee', 'lookup', 'lookup', 'rest', 'snack', 'water', 'board', 'play', 'chat']));
  };

  // 上班、下班
  async function clockOut(c) {
    if (c.away) return; c.busy = true; c.script = (c.script || 0) + 1; c.say(rnd(['下班囉', '先走了，明天見', '收工！']), 1.8); await sleep(0.8 + Math.random());
    if (await goTo(c, W.findSpots('door_out')[0], { speed: 1.9 })) { c.setAction('wave'); release(c); const path = W.nav.findPath(pos(c), W.findSpots('outside')[0]); if (path) await c.walkTo(path, { speed: 1.9 }); }
    c.away = true; c.setVisible(false); release(c);
  }
  async function clockIn(c) {
    const o = W.findSpots('outside')[0]; c.standAt(o.x + (Math.random() - 0.5), o.z + Math.random(), Math.PI); c.setVisible(true); c.away = false; c.busy = true;
    await goTo(c, W.findSpots('door_in')[0], { speed: 1.9 }); c.say(rnd(['早安', '大家早', '今天也加油']), 1.6); c.setAction('wave'); await sleep(1.2);
    await goHome(c); c.busy = false;
  }
  D.clockOut = async (n = 6) => { const pool = [...W.chars.values()].filter(c => !c.busy && !c.away && !c.spec.isCeo); pool.sort(() => Math.random() - 0.5); const ps = pool.slice(0, n).map((c, i) => sleep(i * 0.7).then(() => clockOut(c))); await Promise.all(ps); };
  D.clockIn = async (n = 6) => { let pool = [...W.chars.values()].filter(c => c.away); if (!pool.length) { pool = [...W.chars.values()].filter(c => !c.busy && !c.spec.isCeo).sort(() => Math.random() - 0.5).slice(0, n); pool.forEach(c => { release(c); c.away = true; c.setVisible(false); }); } const ps = pool.map((c, i) => sleep(i * 0.8).then(() => clockIn(c))); await Promise.all(ps); };

  // 事件重播
  const H = { 'meeting.start': meetingStart, 'meeting.say': meetingSay, 'meeting.note': meetingNote, 'meeting.end': meetingEnd, 'task.started': taskStarted, 'task.done': taskDone,
    'agent.clock': ev => (ev.action === 'out' ? clockOut(C(ev.who)) : clockIn(C(ev.who))), 'agent.activity': ev => { routine(C(ev.who), ev.activity); } };
  D.play = async events => {
    if (D.running) return false; D.running = true;
    // 被點名的人先放下手邊的事回座位
    try { for (const ev of events) { const h = H[ev.type]; if (h) await h(ev); if (ev.type === 'meeting.end') await sleep(1.2); } }
    catch (e) { console.error(e); }
    D.running = false; D.stage = ''; return true;
  };
  return D;
}
