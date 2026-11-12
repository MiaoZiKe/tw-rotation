// 導演：把事件（會議、任務、上下班、日常活動）變成角色的行為，並讓閒置的辦公室有生活感。
// 階段 2 接後端後，伺服器推來的事件直接丟給 director.play(events) 即可。
import { THREE } from './kit.js';

export function createDirector(W, ui) {
  const D = { meeting: null, running: false, ambient: true, log: [], stage: '', pets: [] };
  const sleep = W.sleep, C = id => W.chars.get(id), rnd = a => a[Math.floor(Math.random() * a.length)], R = (a, b) => a + Math.random() * (b - a);
  const pos = c => ({ x: c.object3D.position.x, z: c.object3D.position.z });
  const v3 = new THREE.Vector3();
  const headTop = c => v3.set(c.object3D.position.x, c.height + (c.lift || 0), c.object3D.position.z);
  // 冒怒氣：頭頂兩側噴出小煙團
  function steam(c, n = 3) { if (!W.fx) return; for (let i = 0; i < n; i++) W.fx.spawn('dust', headTop(c).clone().add(new THREE.Vector3((i % 2 ? 1 : -1) * 0.22, -0.08, 0)), { v: new THREE.Vector3((i % 2 ? 1 : -1) * R(0.5, 0.9), R(0.9, 1.4), 0), life: 0.7, size: 0.2, grow: 2.2, drag: 2.2, color: 0xffb0a6 }); }
  function hearts(c, n = 3) { if (W.fx) W.fx.burst('heart', headTop(c).clone(), n, { speed: 0.35, up: 0.7, life: 1.1, size: 0.18, sway: 0.4 }); }

  // 坐著的人轉回座位原本的方向
  function faceSeat(c) { if (c.spot && c.spot.seat && c.state === 'sit') { const f = c.spot.seat.face, p = pos(c); c.faceTo(p.x + Math.sin(f), p.z + Math.cos(f)); } }
  function release(c) { if (c.spot) { if (c.spot.taken === c.spec.id) c.spot.taken = null; c.spot = null; } }
  function claim(c, s) { release(c); s.taken = c.spec.id; c.spot = s; }

  // 走到一個目標點（有座位就跳上去坐好）。回傳 true 表示走到；被新的指令打斷回傳 false。
  async function goTo(c, s, o = {}) {
    if (!s || c.state === 'held') return false; const job = c.job = (c.job || 0) + 1;
    const from = pos(c), wasSeat = c.state === 'sit' ? c.spot : null; c.atDesk = false;
    claim(c, s);
    let path = W.nav.findPath(wasSeat ? { x: wasSeat.x, z: wasSeat.z } : from, { x: s.x, z: s.z });
    if (!path) { path = [wasSeat ? { x: wasSeat.x, z: wasSeat.z } : from, { x: s.x, z: s.z }]; c.noPath = (c.noPath || 0) + 1; W.stats.noPath++; }
    if (wasSeat) path.unshift(from);         // 第一段是從椅子跳到旁邊的地板
    W.stats.walks++;
    const ok = await c.walkTo(path, { speed: o.speed || 1.7 });
    if (c.job !== job) return false;
    if (!ok) { W.stats.interrupted++; return false; }
    if (s.seat) { c.sitAt(s.seat); await sleep(0.75); if (c.job !== job) return false; } else c.standAt(s.x, s.z, s.face);
    return true;
  }
  async function goHome(c, o) {
    const s = W.spots.find(q => q.name === 'seat:' + c.spec.id); if (!s) return false;
    const ok = await goTo(c, s, o); if (ok) { c.atDesk = true; if (!o || !o.keep) c.setAction('type'); c.workAt = W.time + R(4, 9); } return ok;
  }
  D.goTo = goTo; D.goHome = goHome;

  // ───────── 坐在位子上的工作細節 ─────────
  // 每個人依部門有不同的習慣：誰常講電話、誰常看文件、誰常想事情
  const HABIT = {
    def: { type: 5, note: 1.1, think: 1, phone: 0.7, cup: 1, tablet: 0.6, doc: 0.8, magnify: 0.3, stretch: 0.6, doze: 0.35 },
    design: { tablet: 2.4, think: 1.4 }, video: { tablet: 1.6 }, social: { phone: 2.2 }, biz: { phone: 2, doc: 1.4 }, legal: { doc: 2.6, magnify: 1.4 }, audit: { doc: 2.2, magnify: 1.6, note: 1.6 },
    quant: { think: 1.8, note: 1.6 }, industry: { doc: 1.8, magnify: 0.9 }, data: { type: 7 }, frontend: { type: 7 }, ops: { phone: 1.3, note: 1.4 }, ceo: { phone: 1.6, doc: 1.6, think: 1.4 }
  };
  function pickWork(c) {
    const w = { ...HABIT.def, ...(HABIT[c.spec.dept] || {}) }; let sum = 0; for (const k in w) sum += w[k]; let r = Math.random() * sum;
    for (const k in w) { r -= w[k]; if (r <= 0) return k; } return 'type';
  }
  function deskWork(c) {
    const k = pickWork(c); let dur = R(6, 12);
    switch (k) {
      case 'type': c.setAction('type'); if (Math.random() < 0.18) c.emote(rnd(['bulb', 'exclaim', 'note']), 1.6); break;
      case 'note': c.setAction('note'); break;
      case 'think': c.setAction('think'); c.emote('question', 1.8); sleep(dur * 0.6).then(() => { if (c.action === 'think' && c.atDesk) { c.emote('bulb', 1.6); c.setExpression('happy', 1.4); } }); break;
      case 'phone': c.setAction('phone'); dur = R(5, 9); break;
      case 'cup': c.setAction('drink'); c.emote('note', 1.4); dur = R(4.5, 7); break;
      case 'tablet': c.setAction('tablet'); break;
      case 'doc': c.setAction('doc'); break;
      case 'magnify': c.setAction('magnify'); dur = R(4, 7); break;
      case 'stretch': c.setAction('stretch'); dur = 3; break;
      case 'doze': c.setAction('doze'); c.emote('zzz', 2.4); dur = R(5, 8.5); break;
    }
    c.workAt = W.time + dur;
  }

  // ───────── 會議 ─────────
  const KIND = { open: '開場', assign: '交代', ack: '確認', question: '提問', add: '補充', object: '反對', agree: '附和', risk: '提醒', summary: '總結' };
  const LISTEN = ['note', 'listen', 'tablet', 'note', 'think', 'note', 'listen'];
  const settle = c => { if (D.meeting && c.state === 'sit' && !D.meeting.up.has(c)) c.setAction(c.meetBase || 'listen'); };
  async function meetingStart(ev) {
    const ceo = C(ev.by), att = ev.attendees.map(C).filter(Boolean), all = [ceo, ...att];
    D.meeting = { id: ev.meeting, topic: ev.topic, source: ev.source, people: all, lines: [], notes: [], up: new Set() }; D.stage = '召集';
    all.forEach(c => { c.busy = true; c.script = (c.script || 0) + 1; });
    ui.meetingOpen(D.meeting); W.whiteboard && W.whiteboard.set(ev.topic);
    ceo.say('開會囉！' + att.map(c => c.spec.nick).join('、') + '，會議室集合。', 3); ceo.setAction('raise'); ceo.emote('exclaim', 1.4);
    await sleep(0.9);
    att.forEach((c, i) => { c.emote('exclaim', 1.3); c.setExpression('surprised', 1); sleep(i * 0.08).then(() => c.setAction('raise')); });
    await sleep(0.8); D.stage = '走去會議室';
    const seats = W.findSpots('meet'); seats.forEach(s => { s.taken = null; });
    const jobs = all.map((c, i) => (async () => {
      await sleep(i * 0.22); c.setAction(i % 3 === 1 ? 'carry' : 'idle');
      const ok = await goTo(c, seats[i % seats.length], { speed: 3.1 }); c.meetBase = c === ceo ? 'listen' : LISTEN[i % LISTEN.length]; c.setAction(c.meetBase); return ok;
    })());
    await Promise.all(jobs); D.stage = '討論';
    await sleep(0.5);
  }
  // 爭執時站起來：從椅子跳到旁邊，面對對方
  async function standUp(c, toward) {
    const m = D.meeting; if (!m || m.up.has(c) || c.state !== 'sit' || !c.spot) return; m.up.add(c);
    const sp = c.spot; c.job = (c.job || 0) + 1; c.walkTo([pos(c), { x: sp.x, z: sp.z }], { speed: 2 }); await sleep(0.7); if (toward) { const t = pos(toward); c.faceTo(t.x, t.z); }
  }
  async function sitBack(c) { const m = D.meeting; if (!m || !m.up.has(c) || !c.spot || !c.spot.seat) return; m.up.delete(c); if (c.state === 'held') return; c.sitAt(c.spot.seat); await sleep(0.75); c.setAction(c.meetBase || 'listen'); }
  async function meetingSay(ev) {
    const m = D.meeting, c = C(ev.who); if (!m || !c) return;
    const dur = Math.max(2.3, Math.min(4.6, 1.5 + ev.text.length * 0.085));
    const others = m.people.filter(o => o !== c), to = ev.to && C(ev.to);
    const lookAt = () => { const sp = pos(c); others.forEach(o => { if (o.state !== 'walk') o.faceTo(sp.x, sp.z); }); if (to) { const t = pos(to); c.faceTo(t.x, t.z); } else faceSeat(c); };
    // 反對以外的發言：前一輪吵架的人先坐回去
    if (ev.kind !== 'object' && m.up.size) { [...m.up].forEach(o => { o.setExpression('awkward', 2.5); o.emote('sweat', 1.6); sitBack(o); }); }
    if (ev.kind === 'question' || ev.kind === 'risk') { c.setAction('raise', { duration: 1.1 }); c.emote(ev.kind === 'risk' ? 'exclaim' : 'question', 1.2); lookAt(); await sleep(0.9); }
    if (ev.kind === 'object') {
      D.stage = '爭執'; await standUp(c, to); if (to) standUp(to, c);
      lookAt(); c.setExpression('angry', dur + 0.5); c.setAction('slam', { duration: dur }); c.emote('anger', dur); steam(c, 4);
      sleep(0.5).then(() => { others.forEach((o, i) => { if (o === to) { o.setExpression('surprised', 1.2); return; } if (i % 2 === 0) o.emote('sweat', 1.8); o.setExpression(i % 2 ? 'surprised' : 'awkward', 2); }); });
      sleep(dur * 0.5).then(() => steam(c, 3));
    } else {
      lookAt(); c.setAction('talk', { duration: dur });
      if (ev.kind === 'agree') { c.setExpression('happy', dur); sleep(0.6).then(() => others.forEach((o, i) => { if (!m.up.has(o) && i % 2) o.setAction('nod'); })); }
      else if (ev.kind === 'summary') { c.setExpression('proud', dur); sleep(dur * 0.45).then(() => { if (W.whiteboardAt) { c.faceTo(W.whiteboardAt.x, W.whiteboardAt.z); c.setAction('point', { duration: dur * 0.5 }); } }); }
      else if (ev.kind === 'question') c.setExpression('think', dur);
      else if (ev.kind === 'risk') c.setExpression('surprised', 1.4);
      else if (ev.kind === 'open') { c.setExpression('happy', 1.5); }
      else if (ev.kind === 'ack' || ev.kind === 'add') { sleep(0.9).then(() => { const o = rnd(others); if (!m.up.has(o)) o.setAction('nod'); }); if (ev.kind === 'add') sleep(1.2).then(() => { const o = rnd(others); if (!m.up.has(o) && o.state === 'sit') { o.setAction('shake'); o.emote('question', 1.2); } }); }
    }
    c.say(ev.text, dur); c.speech.kind = ev.kind;
    m.lines.push({ who: c.spec.nick, kind: KIND[ev.kind] || '', k: ev.kind, text: ev.text, ts: ev.ts }); ui.meetingLine(m);
    await sleep(dur + 0.25); if (D.stage === '爭執') D.stage = '討論';
    settle(c);
  }
  async function meetingNote(ev) {
    const m = D.meeting; if (!m) return; W.whiteboard && W.whiteboard.add(ev.text); m.notes.push(ev.text); m.lines.push({ who: '白板', kind: '重點', k: 'note', text: ev.text, ts: ev.ts }); ui.meetingLine(m); D.stage = '白板重點';
    // 大家看向白板；主持人指著白板，做筆記的人低頭抄
    if (W.whiteboardAt) m.people.forEach((c, i) => { if (m.up.has(c) || c.state !== 'sit') return; c.faceTo(W.whiteboardAt.x, W.whiteboardAt.z); if (i === 0) c.setAction('point', { duration: 1.1 }); else if (c.meetBase !== 'note' && i % 2) c.setAction('nod', { duration: 0.9 }); });
    await sleep(1.0); D.stage = '討論';
  }
  async function meetingEnd(ev) {
    const m = D.meeting; if (!m) return; D.stage = '散會';
    await Promise.all([...m.up].map(sitBack));
    m.people.forEach((c, i) => { c.setExpression('happy', 2); c.setAction(i % 3 === 2 ? 'cheer' : 'clap', { duration: 1.7 }); if (i % 2 === 0) c.emote('note', 1.5); }); await sleep(1.8);
    if (ev.post_to) ui.postBoard(ev.post_to, { t: ui.fmtTs(ev.ts), title: '會議結論', text: ev.summary });
    m.lines.push({ who: '結論', kind: '已貼上佈告欄', k: 'end', text: ev.summary, ts: ev.ts }); ui.meetingLine(m);
    const jobs = m.people.map((c, i) => (async () => { await sleep(i * 0.25); c.setAction('idle'); const ok = await goHome(c, { speed: 2.3 }); c.busy = false; return ok; })());
    await Promise.all(jobs); D.stage = '回座位工作'; ui.meetingClosed(m); D.meeting = null;
  }
  const TOOL = { edit: ['type', 'exclaim'], search: ['read', 'question'], read: ['doc', 'dots'], wait: ['think', 'dots'] };
  async function taskStarted(ev) {
    const c = C(ev.who); if (!c) return; const [act, sym] = TOOL[ev.tool] || TOOL.edit;
    c.emote(sym, 1.6); c.task = ev.title;
    if (ev.tool === 'search') routine(c, 'lookup'); else { c.setAction(act); c.workAt = W.time + 14; }
    await sleep(0.4);
  }
  // 交件：拿著文件走到主管或 CEO 桌前
  async function taskDone(ev) {
    const c = C(ev.who), boss = C(ev.report_to || 'ceo'); if (!c || !boss) return; D.stage = '向 CEO 報告';
    c.busy = true; c.script = (c.script || 0) + 1; c.emote('exclaim', 1.2); c.setExpression('happy', 1.5); c.setAction('cheer', { duration: 1 }); await sleep(1.1);
    c.setAction('carry');
    const ok = await goTo(c, W.spot(boss.spec.isCeo ? 'ceo_front' : 'seat:' + boss.spec.id, pos(c), c.spec.id) || W.spot('ceo_front', pos(c), c.spec.id), { speed: 2.4 });
    if (ok) {
      const b = pos(boss); c.faceTo(b.x, b.z); boss.faceTo(pos(c).x, pos(c).z); c.setAction('present'); c.say(ev.summary, 3.6); c.speech.kind = 'ack'; boss.setAction('listen'); await sleep(3.7);
      if (ev.reply) { boss.say(ev.reply, 2.6); boss.speech.kind = 'summary'; boss.setAction('nod', { duration: 1.4 }); boss.emote('check', 2); await sleep(2.7); }
      c.setAction('idle'); c.setExpression('happy', 2); hearts(c, 2); await sleep(0.6); boss.setAction('type'); boss.workAt = W.time + 6; faceSeat(boss);
    }
    c.setAction('idle'); await goHome(c, { speed: 2 }); c.busy = false; D.stage = '';
  }

  // ───────── 桌球（兩個人才打得起來） ─────────
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 9), new THREE.MeshStandardMaterial({ color: '#ffb86b', roughness: 0.5 })); ball.visible = false; W.scene.add(ball);
  const pong = { on: false, t: 0, a: null, b: null };
  function tickPong(dt) {
    if (!pong.on) return; pong.t += dt; const pa = pos(pong.a), pb = pos(pong.b), u = (pong.t * 1.25) % 2, k = u < 1 ? u : 2 - u, e = 0.12 + 0.76 * k;
    ball.position.set(pa.x + (pb.x - pa.x) * e, 0.78 + 0.3 * Math.abs(Math.sin(k * Math.PI * 1.0)) + 0.02, pa.z + (pb.z - pa.z) * e);
  }

  // ───────── 日常行為 ─────────
  const SAY = { chat: [['今天咖啡不錯', '真的，比昨天香'], ['那批推上去了嗎？', '剛推，兩行都綠了'], ['等等一起吃飯？', '好啊，吃什麼'], ['剛剛驗收過了', '太好了，辛苦'], ['你看到新公告沒', '看了，下週要改版']] };
  const ROUTINES = {
    async coffee(c) {
      if (!await goTo(c, W.spot('coffee', null, c.spec.id))) return; c.setAction('pour'); await sleep(1.7);
      c.setAction('drink'); c.emote('note', 1.6); await sleep(3.3); c.keep = 'drink';
    },
    async water(c) { if (await goTo(c, W.spot('water', null, c.spec.id))) { c.setAction('pour'); await sleep(1.2); c.setAction('drink'); await sleep(3.2); c.setAction('idle'); } },
    async lookup(c) {
      if (!await goTo(c, W.spot('library', null, c.spec.id))) return;
      c.setAction('reach'); c.emote('question', 1.4); await sleep(1.4);
      if (Math.random() < 0.35) { c.setAction('magnify'); await sleep(3.4); } else { c.setAction('read'); await sleep(3.4); }
      c.emote('bulb', 1.4); c.setExpression('happy', 1.4); await sleep(1.2); c.setAction('read'); c.keep = 'read';
    },
    async rest(c) {
      if (!await goTo(c, W.spot(rnd(['sofa', 'sofa', 'bean']), null, c.spec.id))) return;
      const k = rnd(['sleep', 'sleep', 'phone', 'tablet', 'stretch']);
      if (k === 'stretch') { c.setAction('stretch'); await sleep(2.8); c.setAction('sleep'); } else c.setAction(k);
      if (k !== 'phone' && k !== 'tablet') c.emote('zzz', 2.4); await sleep(R(5, 7.5)); c.setAction('idle'); if (k === 'sleep') { c.setExpression('surprised', 0.8); await sleep(0.5); }
    },
    async snack(c) { if (await goTo(c, W.spot(rnd(['snack', 'dine', 'dine']), null, c.spec.id))) { c.setAction('eat'); c.emote('note', 1.6); await sleep(R(3.8, 5.2)); c.setAction('idle'); c.setExpression('happy', 1.6); hearts(c, 2); await sleep(0.7); } },
    async play(c) {
      const k = rnd(['pong', 'pong', 'arcade', 'bean']);
      if (k === 'pong' && !pong.on) {
        const tb = [...W.furn.values()].find(i => i.f.type === 'pingpong'), sp = tb ? W.spots.filter(s => s.fid === tb.f.id && !s.taken) : [], mate = pickIdle(c);
        if (sp.length >= 2 && mate) {
          pong.on = true; mate.busy = true; const tok = mate.script = (mate.script || 0) + 1;
          c.say('打一局？', 1.6); mate.emote('exclaim', 1.2);
          const [a, b] = await Promise.all([goTo(c, sp[0], { speed: 2.2 }), goTo(mate, sp[1], { speed: 2.2 })]);
          if (a && b && mate.script === tok) {
            const pa = pos(c), pb = pos(mate); c.faceTo(pb.x, pb.z); mate.faceTo(pa.x, pa.z); c.setAction('paddle'); mate.setAction('paddle'); mate.inner && (mate.inner.poseT = 0.4);
            pong.a = c; pong.b = mate; pong.t = 0; ball.visible = true; await sleep(R(6, 8)); ball.visible = false;
            const win = Math.random() < 0.5 ? c : mate, lose = win === c ? mate : c; win.setAction('cheer', { duration: 1.6, then: 'idle' }); win.emote('star', 1.6); lose.setAction('sulk', { duration: 1.6, then: 'idle' }); lose.emote('sweat', 1.6); lose.setExpression('sad', 1.6); await sleep(1.8);
          }
          pong.on = false; ball.visible = false; c.setAction('idle');
          if (mate.script === tok) { mate.setAction('idle'); goHome(mate).then(() => { if (mate.script === tok) mate.busy = false; }); }
          return;
        }
      }
      if (k === 'bean') { if (await goTo(c, W.spot('bean', null, c.spec.id))) { c.setAction(rnd(['phone', 'tablet'])); await sleep(R(4.5, 6.5)); c.setAction('idle'); } return; }
      const ar = W.spots.filter(s => s.name === 'play' && !s.taken && W.furn.get(s.fid) && W.furn.get(s.fid).f.type === 'arcade');
      if (ar.length && await goTo(c, rnd(ar))) { c.setAction('type'); await sleep(2.6); c.setAction('cheer', { duration: 1.6, then: 'idle' }); c.emote('star', 1.6); await sleep(1.8); }
    },
    async board(c) { const s = W.spot('board:' + c.spec.dept, null, c.spec.id); if (s && await goTo(c, s)) { c.setAction('think'); await sleep(2.4); c.setAction('nod', { duration: 1 }); c.emote('check', 1.2); await sleep(1.1); c.setAction('idle'); } },
    async chat(c) {
      const mate = pickIdle(c), all = W.findSpots('chat').filter(s => !s.taken), s0 = all.length ? rnd(all) : null, s1 = s0 && all.find(s => s !== s0 && s.fid === s0.fid);
      if (!mate || !s1) { if (s0 && await goTo(c, s0)) { c.setAction('phone'); await sleep(4); c.setAction('idle'); } return; }
      mate.busy = true; const tok = mate.script = (mate.script || 0) + 1;
      const [a, b] = await Promise.all([goTo(c, s0), goTo(mate, s1)]);
      if (a && b && mate.script === tok) {
        const pa = pos(c), pb = pos(mate), ln = rnd(SAY.chat); c.faceTo(pb.x, pb.z); mate.faceTo(pa.x, pa.z);
        c.setAction('talk', { duration: 2.2, then: 'listen' }); c.say(ln[0], 2.2); mate.setAction('listen'); await sleep(2.4);
        mate.setAction('talk', { duration: 2.2, then: 'listen' }); mate.say(ln[1], 2.2); await sleep(2.3);
        c.setExpression('laugh', 1.4); mate.setExpression('happy', 1.4); c.setAction('nod', { duration: 1 }); await sleep(1.2);
      }
      c.setAction('idle');
      if (mate.script === tok) { mate.setAction('idle'); goHome(mate).then(() => { if (mate.script === tok) mate.busy = false; }); }
    },
    // 被拎起來放下之後：愣一下，再自己走回座位
    async afterDrop(c) { c.setExpression('surprised', 1.2); c.emote('question', 1.4); await sleep(1.6); const p = pos(c), f = W.nav.isReach(p.x, p.z) ? p : W.nav.nearestFree(p.x, p.z, 24); if (f && (f.x !== p.x || f.z !== p.z)) await c.walkTo([p, { x: f.x, z: f.z }], { speed: 2 }); }
  };
  async function routine(c, name) {
    if (!c || c.away || c.state === 'held') return; const tok = c.script = (c.script || 0) + 1; c.busy = true; c.keep = null;
    try { await ROUTINES[name](c); } catch (e) { console.error(e); }
    if (c.script !== tok) return;            // 中途被叫去開會或報告，就不要再自己走回座位
    const keep = c.keep; c.keep = null; if (!keep) c.setAction('idle');
    if (!c.away) { const ok = await goHome(c, { keep: !!keep }); if (ok && keep && c.script === tok) { c.setAction(keep); c.workAt = W.time + R(4, 6); } }
    if (c.script === tok) c.busy = false;
  }
  D.routine = (id, name) => { const c = id ? C(id) : pickIdle(); if (c) return routine(c, name); };
  function pickIdle(not) { const pool = [...W.chars.values()].filter(c => c !== not && !c.busy && !c.away && !c.spec.isCeo && c.state === 'sit' && c.atDesk); return pool.length ? rnd(pool) : null; }
  D.pickIdle = pickIdle;
  let nextAmb = 3, nextWork = 0, lastT = 0;
  const MENU = ['coffee', 'coffee', 'lookup', 'lookup', 'rest', 'snack', 'water', 'board', 'play', 'play', 'chat', 'chat'];
  D.tick = () => {
    const dt = Math.min(0.1, W.time - lastT); lastT = W.time; tickPong(dt); tickPets(dt);
    // 坐在位子上的人，每隔幾秒換一件事做（開會、被叫走的不算）
    if (W.time >= nextWork) { nextWork = W.time + 0.4; for (const c of W.chars.values()) if (c.atDesk && !c.busy && c.state === 'sit' && W.time >= (c.workAt || 0)) deskWork(c); }
    if (!D.ambient || W.time < nextAmb) return; nextAmb = W.time + 1.9 + Math.random() * 2.4;
    const out = [...W.chars.values()].filter(c => c.busy && !(D.meeting && D.meeting.people.includes(c))).length; if (out >= 9) return;
    const c = pickIdle(); if (c) routine(c, rnd(MENU));
  };

  // ───────── 寵物：跟著主人，主人坐著就在附近閒晃、打滾、睡覺 ─────────
  function tickPets() {
    for (const p of D.pets) {
      if (p.state === 'held' || p.busyUntil > W.time || p.state === 'walk') continue;
      const o = C(p.spec.owner), me = pos(p), op = o && o.object3D.visible ? pos(o) : me, d = Math.hypot(op.x - me.x, op.z - me.z);
      const near = (r0, r1) => { for (let i = 0; i < 8; i++) { const a = Math.random() * 6.283, r = R(r0, r1), x = op.x + Math.cos(a) * r, z = op.z + Math.sin(a) * r; if (W.nav.isReach(x, z)) return { x, z }; } return null; };
      if (d > 3.4) { const t = near(0.9, 1.6); const path = t && W.nav.findPath(me, t); if (path) { p.setAction('idle'); p.emote(d > 9 ? 'exclaim' : 'heart', 1); p.walkTo(path, { speed: d > 7 ? 3.4 : 2.4 }); } p.busyUntil = W.time + 0.6; continue; }
      const k = Math.random();
      if (k < 0.5) { const t = near(0.8, 2.4), path = t && W.nav.findPath(me, t); if (path) { p.setAction('idle'); p.walkTo(path, { speed: 1.5 }); } p.busyUntil = W.time + R(1.5, 3); }
      else if (k < 0.7) { p.setAction('sleep'); p.busyUntil = W.time + R(5, 9); }
      else if (k < 0.85 && p.inner) { p.setAction('idle'); p.inner.doAct('sig'); p.busyUntil = W.time + 3; }
      else { p.setAction('idle'); p.faceTo(op.x, op.z); p.setExpression('happy', 2); p.emote('heart', 1.2); p.busyUntil = W.time + R(2, 4); }
    }
  }

  // 上班、下班
  async function clockOut(c) {
    if (c.away || c.state === 'held') return; c.busy = true; c.script = (c.script || 0) + 1; c.setAction('stretch'); c.say(rnd(['下班囉', '先走了，明天見', '收工！']), 1.8); await sleep(1.6 + Math.random());
    c.setAction('idle');
    if (await goTo(c, W.findSpots('door_out')[0], { speed: 1.9 })) { c.setAction('wave'); release(c); const path = W.nav.findPath(pos(c), W.findSpots('outside')[0]); if (path) await c.walkTo(path, { speed: 1.9 }); }
    c.away = true; c.setVisible(false); release(c);
  }
  async function clockIn(c) {
    const o = W.findSpots('outside')[0]; c.standAt(o.x + (Math.random() - 0.5), o.z + Math.random(), Math.PI); c.setVisible(true); c.away = false; c.busy = true; c.setAction('idle');
    await goTo(c, W.findSpots('door_in')[0], { speed: 1.9 }); c.say(rnd(['早安', '大家早', '今天也加油']), 1.6); c.setAction('wave'); c.setExpression('happy', 1.5); await sleep(1.4);
    await goHome(c); c.busy = false;
  }
  D.clockOut = async (n = 6) => { const pool = [...W.chars.values()].filter(c => !c.busy && !c.away && !c.spec.isCeo); pool.sort(() => Math.random() - 0.5); const ps = pool.slice(0, n).map((c, i) => sleep(i * 0.7).then(() => clockOut(c))); await Promise.all(ps); };
  D.clockIn = async (n = 6) => { let pool = [...W.chars.values()].filter(c => c.away); if (!pool.length) { pool = [...W.chars.values()].filter(c => !c.busy && !c.spec.isCeo).sort(() => Math.random() - 0.5).slice(0, n); pool.forEach(c => { release(c); c.away = true; c.setVisible(false); }); } const ps = pool.map((c, i) => sleep(i * 0.8).then(() => clockIn(c))); await Promise.all(ps); };

  // 使用者把角色拎起來：中斷他手上的事；放下後自己走回座位
  D.grabbed = c => { c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.atDesk = false; release(c); if (D.meeting) D.meeting.up.delete(c); };
  D.dropped = c => { if (c.spec.pet) { c.busyUntil = W.time + 1.5; c.setExpression('surprised', 1); return; } routine(c, 'afterDrop'); };
  D.sendHome = c => { if (c.away || c.state === 'held' || (D.meeting && D.meeting.people.includes(c))) return false; const tok = c.script = (c.script || 0) + 1; c.busy = true; c.setAction('idle'); goHome(c, { speed: 2.2 }).then(() => { if (c.script === tok) c.busy = false; }); return true; };

  // 事件重播
  const H = { 'meeting.start': meetingStart, 'meeting.say': meetingSay, 'meeting.note': meetingNote, 'meeting.end': meetingEnd, 'task.started': taskStarted, 'task.done': taskDone,
    'agent.clock': ev => (ev.action === 'out' ? clockOut(C(ev.who)) : clockIn(C(ev.who))), 'agent.activity': ev => { routine(C(ev.who), ev.activity); } };
  D.play = async events => {
    if (D.running) return false; D.running = true;
    try { for (const ev of events) { const h = H[ev.type]; if (h) await h(ev); if (ev.type === 'meeting.end') await sleep(1.2); } }
    catch (e) { console.error(e); }
    D.running = false; D.stage = ''; return true;
  };
  return D;
}
