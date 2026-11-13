// 「等你處理」的提醒＋派工到交件的演出。只讀狀態層（state.js）的事件，把它變成角色的行為：
//   · 等核准：CEO 舉手、桌燈閃琥珀（每秒 1 次）、頂列琥珀膠囊、分頁標題前綴「(1) 」；只顯示動作類別，不顯示指令全文
//   · 等回答：CEO 頭上大問號、桌燈閃藍；也算一件要你處理的事
//   · 派工：同事走到 CEO 桌前領任務（不瞬移）→ 回座位，依工具類別換手上的道具（讀＝文件、寫＝筆記本、查＝放大鏡、泛用＝平板…）
//   · 交件：同事拿文件走去 CEO 桌前（同時最多 3 位在桌前，其餘在後面排隊）；失敗＝垮肩＋小烏雲，CEO 說「沒關係」，沒有任何羞辱
//   · 大動作演出同時最多 6 件，超過的改成頭上小圖示，事件照記不丟
//   · 訊號不明（30 分鐘沒消息）：CEO 名牌寫「待命中」，頂列出現灰色「訊號不明」，不寫離線
import { THREE } from './kit.js';
import { TOOL_TEXT, PERM_TEXT, hhmm } from './state.js';

const $ = id => document.getElementById(id);
const short = (t, n = 22) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const TOOL_ACT = { read: 'doc', write: 'note', search: 'magnify', test: 'type', deploy: 'phone', wait: 'drink', other: 'tablet' };   // 工具類別 → 角色動作（動作自帶手上的道具）
const TOOL_EMO = { test: 'dots', deploy: 'star', wait: 'dots' };

export function createJobs(W, X) {
  const { state: S, ui, director: D } = X, C = id => W.chars.get(id), pos = c => ({ x: c.object3D.position.x, z: c.object3D.position.z });
  const J = { big: 0, bigMax: 6, bigPeak: 0, slotUser: [null, null, null], queue: [], baseTitle: document.title || 'AI 辦公室', handled: 0, small: 0 };
  const reduce = () => !!(W.reduceMotion || matchMedia('(prefers-reduced-motion: reduce)').matches);
  const acquire = () => { if (J.big >= J.bigMax) { J.small++; return false; } J.big++; J.bigPeak = Math.max(J.bigPeak, J.big); return true; };
  const free = () => { J.big = Math.max(0, J.big - 1); };

  // ───────── 同事對應 ─────────
  const ok = c => c && !c.jobless && !c.away && !c.spec.isCeo && !c.spec.pet;
  function resolveMember(ev) {
    const t = ev.agent_type; let c = C(t); if (ok(c)) return c;
    if (ev.agent_id && S.byAgentId.has(ev.agent_id)) { c = C(S.byAgentId.get(ev.agent_id)); if (c) return c; }
    const pool = [...W.chars.values()].filter(ok); if (!pool.length) return null;
    let h = 0; for (const ch of String(t || ev.agent_id || 'x')) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return pool[h % pool.length];
  }
  J.holds = c => { const a = S.agents.get(c.spec.id); return !!a && a.phase !== 'idle'; };
  J.live = id => { const a = S.agents.get(id); return a ? { doing: a.phase !== 'idle' ? a.task : null, done: a.done } : { doing: null, done: [] }; };

  // ───────── 名牌上的狀態字 ─────────
  J.statusOf = c => {
    if (c.sleeping) return '睡覺中';
    const id = c.spec.id;
    if (c.spec.isCeo) {
      if (S.flags.permission) return '等你核准';
      if (S.flags.question) return '等你回答';
      if (S.signal !== 'ok') return '待命中';
    }
    const a = S.agents.get(id); if (!a || a.phase === 'idle') return '';
    if (a.phase === 'delivering') return a.failedNow ? '遇到問題' : '交件中';
    if (a.stuck >= 1) return `好像卡住了（已 ${Math.max(1, Math.round((S.now() - a.lastToolAt) / 60000))} 分鐘）`;
    return a.phase === 'queued' ? '領任務中' : (a.tool ? TOOL_TEXT[a.tool] : '進行中');
  };

  // ───────── CEO 桌前的 3 個位子與排隊 ─────────
  const deskSpots = () => W.findSpots('ceo_front');
  const qPoint = i => { const b = deskSpots()[0], p = W.nav.nearestFree(b.x + (i % 2 ? 0.95 : -0.95), b.z + 1.5 + Math.floor(i / 2) * 0.95, 14) || { x: b.x, z: b.z + 2 }; return { x: p.x, z: p.z, face: Math.PI }; };
  async function takeSlot(c, jt) {
    J.queue.push(c); let walked = false;
    for (let guard = 0; guard < 400; guard++) {
      if (c.jtok !== jt) { J.queue = J.queue.filter(q => q !== c); return -1; }
      const i = J.slotUser.findIndex(u => !u);
      if (i >= 0 && J.queue[0] === c) { J.slotUser[i] = c; J.queue.shift(); J.slotPeak = Math.max(J.slotPeak || 0, J.slotUser.filter(Boolean).length); return i; }
      if (!walked && J.queue.indexOf(c) >= 0 && (i < 0 || J.queue[0] !== c)) { walked = true; D.goTo(c, qPoint(Math.max(0, J.queue.indexOf(c))), { speed: 2.6 }); }
      await W.sleep(0.4);
    }
    J.queue = J.queue.filter(q => q !== c); return -1;
  }
  const ceoTurn = c => { const ceo = C('ceo'); if (!ceo || ceo.piloted) return null; const p = pos(c); ceo.faceTo(p.x, p.z); return ceo; };
  const ceoBack = () => { const ceo = C('ceo'); if (!ceo || ceo.piloted || ceo.state !== 'sit' || ceo.sleeping) return; ceo.setAction('type'); ceo.workAt = W.time + 5; const f = ceo.spot && ceo.spot.seat && ceo.spot.seat.face, p = pos(ceo); if (f != null) ceo.faceTo(p.x + Math.sin(f), p.z + Math.cos(f)); };

  // ───────── 工具類別 → 動作 ─────────
  function applyTool(c, a) {
    if (!a || a.phase !== 'doing' || c.piloted || c.sleeping || c.state !== 'sit') return;
    const act = TOOL_ACT[a.tool] || 'type'; c.setAction(act); c.atDesk = true; c.workAt = W.time + 600;       // 工作中不要被日常的桌上小動作蓋掉
    if (TOOL_EMO[a.tool]) c.emote(TOOL_EMO[a.tool], 1.6);
  }
  const wakeOne = c => { if (c.sleeping) { c.sleeping = false; c.setExpression('neutral', 0.1); c.setAction('stretch', { then: 'type' }); } };

  async function goWork(c, a, jt) {
    const okk = await D.goHome(c, { speed: 2.4 });
    if (c.jtok !== jt) return;
    if (okk || c.state === 'sit') { a.phase = 'doing'; a.lastToolAt = S.now(); applyTool(c, a); } else { a.phase = 'doing'; }
  }
  async function startJob(e) {
    const c = resolveMember(e); if (!c) return; const id = c.spec.id, a = S.agent(id);
    if (e.agent_id) S.byAgentId.set(e.agent_id, id);
    Object.assign(a, { phase: 'queued', task: short(e.description || '新任務', 40), agentId: e.agent_id || null, since: S.now(), lastToolAt: S.now(), tool: e.tool_category || null, stuck: 0, failedNow: false });
    S.say(`CEO 派給 ${c.spec.nick}：${a.task}`); J.handled++;
    wakeOne(c); const jt = c.jtok = (c.jtok || 0) + 1;
    c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true;
    const inMeet = D.meeting && D.meeting.people.includes(c);
    if (inMeet || c.piloted || c.state === 'held') { a.phase = 'doing'; return; }
    if (reduce() || !acquire()) {                       // 超過演出預算：只亮燈泡，不走動；人已在座位就直接開工
      c.emote('bulb', 1.8); if (c.state === 'sit' && c.atDesk) { a.phase = 'doing'; applyTool(c, a); } else goWork(c, a, jt); return;
    }
    try {
      c.setAction('idle'); const slot = await takeSlot(c, jt); if (slot < 0) return;
      let done = false; try {
        const sp = deskSpots()[slot], okk = await D.goTo(c, sp, { speed: 2.6 });
        if (okk && c.jtok === jt) {
          const ceo = ceoTurn(c), p = pos(C('ceo') || c); c.faceTo(p.x, p.z);
          if (ceo) { ceo.setAction('talk', { duration: 2.2 }); ceo.say('交給你：' + short(a.task, 16), 2.6); ceo.speech.kind = 'summary'; }
          c.setAction('listen'); await W.sleep(2.4); if (c.jtok !== jt) return;
          c.emote('bulb', 1.4); c.setExpression('happy', 1.2); c.setAction('nod'); await W.sleep(0.9);
          ceoBack(); done = true;
        }
      } finally { J.slotUser[slot] = null; }
      if (c.jtok !== jt) return; await goWork(c, a, jt); void done;
    } finally { free(); }
  }
  function tool(e) {
    const cat = S.CATS.includes(e.tool_category) ? e.tool_category : 'other';
    const mid = e.agent_id && S.byAgentId.get(e.agent_id), c = mid ? C(mid) : C('ceo'); if (!c) return;
    if (c.spec.isCeo) { if (!c.piloted && !c.sleeping && c.state === 'sit' && !S.flags.permission && !S.flags.question) { c.setAction(TOOL_ACT[cat] || 'type'); c.workAt = W.time + 30; if (TOOL_EMO[cat]) c.emote(TOOL_EMO[cat], 1.6); } J.ceoTool = cat; return; }
    const a = S.agent(c.spec.id); a.tool = cat; a.lastToolAt = S.now(); a.stuck = 0; wakeOne(c); applyTool(c, a);
  }
  async function stopJob(e) {
    const mid = (e.agent_id && S.byAgentId.get(e.agent_id)) || (resolveMember(e) || { spec: {} }).spec.id, c = C(mid); if (!c) return;
    const a = S.agent(mid), failed = e.status === 'failed', summary = short(e.last_assistant_message || a.task || (failed ? '遇到問題' : '做完了'), 26), title = a.task;
    a.phase = 'delivering'; a.failedNow = failed; a.stuck = 0; const jt = c.jtok = (c.jtok || 0) + 1; wakeOne(c);
    S.say(failed ? `${c.spec.nick}遇到問題：${summary}` : `${c.spec.nick}交件：${summary}`);
    const finalize = () => { a.phase = 'idle'; a.tool = null; a.failedNow = false; if (failed) a.failed++; else a.done.unshift({ title: title || '任務', t: S.now(), summary }); a.task = ''; c.busy = !!(D.meeting && D.meeting.people.includes(c)); c.workAt = W.time + 3; if (W.ui && W.ui.refreshCard) W.ui.refreshCard(); };
    const inMeet = D.meeting && D.meeting.people.includes(c);
    if (inMeet || c.piloted || c.state === 'held' || reduce() || !acquire()) { c.emote(failed ? 'cloud' : 'check', 2.4); if (c.state === 'sit') c.setAction('type'); finalize(); return; }
    try {
      c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1; c.busy = true; c.setAction('carry'); if (failed) { c.setExpression('sad', 4); c.emote('cloud', 2.6); }
      const slot = await takeSlot(c, jt); if (slot < 0) return;
      try {
        const okk = await D.goTo(c, deskSpots()[slot], { speed: 2.4 });
        if (okk && c.jtok === jt) {
          const ceo = ceoTurn(c), p = pos(C('ceo') || c); c.faceTo(p.x, p.z);
          if (failed) {
            c.setAction('sulk', { duration: 2.2 }); c.say('這邊卡住了：' + summary, 3); if (ceo) { ceo.setAction('listen'); } await W.sleep(3.1); if (c.jtok !== jt) return;
            if (ceo) { ceo.say('沒關係，我來看看', 2.4); ceo.setAction('nod', { duration: 1.4 }); ceo.emote('check', 1.6); } c.setExpression('neutral', 0.1); await W.sleep(1.8);
          } else {
            c.setAction('present'); c.say(summary, 3.2); c.speech.kind = 'ack'; if (ceo) ceo.setAction('listen'); await W.sleep(3.3); if (c.jtok !== jt) return;
            if (ceo) { ceo.say('收到，辛苦了', 2.2); ceo.speech.kind = 'summary'; ceo.setAction('nod', { duration: 1.4 }); ceo.emote('check', 2); } c.setExpression('happy', 1.8); await W.sleep(1.6);
          }
          ceoBack();
        }
      } finally { J.slotUser[slot] = null; }
      if (c.jtok !== jt) return; c.setAction('idle'); finalize(); await D.goHome(c, { speed: 2.2 }); if (c.jtok === jt) c.busy = false;
    } finally { free(); }
  }

  // ───────── 等核准／等回答：頂列琥珀膠囊、桌燈、分頁標題 ─────────
  const bar = $('bar'), fl = document.createElement('div'); fl.className = 'btn fl'; fl.id = 'flBadge'; fl.hidden = true; fl.setAttribute('role', 'status');
  bar.insertBefore(fl, $('editBtn'));
  const lk = document.createElement('div'); lk.className = 'btn lk'; lk.id = 'linkBadge'; lk.hidden = true; lk.setAttribute('role', 'status'); bar.insertBefore(lk, $('editBtn'));
  const glow = (col) => { const cv = document.createElement('canvas'); cv.width = cv.height = 64; const c = cv.getContext('2d'), g = c.createRadialGradient(32, 32, 1, 32, 32, 31); g.addColorStop(0, col + 'ff'); g.addColorStop(0.4, col + '88'); g.addColorStop(1, col + '00'); c.fillStyle = g; c.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t; };
  const lampMat = new THREE.SpriteMaterial({ map: glow('#ffb300'), transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, opacity: 0 });
  const lamp = new THREE.Sprite(lampMat); lamp.scale.set(1.1, 1.1, 1); lamp.position.set(5.0, 1.0, 5.55); lamp.visible = false; lamp.renderOrder = 8; W.scene.add(lamp); J.lamp = lamp;
  const amber = glow('#ffb300'), blue = glow('#4d9bff');
  function flagCount() { return (S.flags.permission ? 1 : 0) + (S.flags.question ? 1 : 0); }
  function flagsChanged() {
    const p = S.flags.permission, q = S.flags.question, n = flagCount();
    if (!n) { fl.hidden = true; fl.className = 'btn fl'; lamp.visible = false; document.title = J.baseTitle; J.titleFlash = false; return; }
    fl.hidden = false; fl.className = 'btn fl ' + (p ? 'perm' : 'ask');
    fl.innerHTML = p ? `<i class="fl-ic" aria-hidden="true">盾</i><span>CEO 等你核准</span><small>${PERM_TEXT[p.category] || PERM_TEXT.other}</small>` : `<i class="fl-ic" aria-hidden="true">？</i><span>CEO 等你回答</span><small>${q.text ? short(q.text, 20) : '有問題要問你'}</small>`;
    fl.setAttribute('aria-label', p ? 'CEO 等你核准：' + (PERM_TEXT[p.category] || PERM_TEXT.other) : 'CEO 等你回答');
    lampMat.map = p ? amber : blue; lampMat.needsUpdate = true; lamp.visible = true;
    document.title = `(${n}) ${J.baseTitle}`;
  }
  J.flagsChanged = flagsChanged;
  function linkChanged() {
    const un = S.signal === 'unknown';
    lk.hidden = !un; if (un) lk.innerHTML = `<span>訊號不明</span><small>最後消息 ${S.session.lastEventAt ? hhmm(S.session.lastEventAt) : '—'}</small>`;
  }

  // ───────── 每一幀（模擬時間）：舉手／問號的維持、桌燈閃爍 ─────────
  let nextPose = 0, lastSig = 'ok';
  J.frame = (dt, t) => {
    if (lamp.visible) { lampMat.opacity = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(performance.now() / 1000 * 2 * Math.PI)); }   // 每秒 1 次，遠低於每秒 3 次的限制
    if (t < nextPose) return; nextPose = t + 0.5;
    const ceo = C('ceo'); if (!ceo || ceo.piloted || ceo.sleeping || ceo.state !== 'sit') return;
    if (S.flags.permission) { if (ceo.action !== 'raise' && !ceo._until) { ceo.setAction('raise'); } if (!ceo.emoteSym) ceo.emote('shield', 2.4); }
    else if (S.flags.question) { if (!ceo.emoteSym) { ceo.emote('question', 2.4); ceo.setAction('shake'); } }
  };

  // ───────── 每秒：卡住偵測、訊號、提醒 ─────────
  setInterval(() => {
    S.derive(); const now = S.now();
    for (const [id, a] of S.agents) {
      if (a.phase !== 'doing') continue; const c = C(id); if (!c) continue; const idle = now - a.lastToolAt;
      if (idle >= S.cfg.stuckMs[1] && a.stuck < 2) { a.stuck = 2; if (!c.sleeping) { c.emote('sweat', 2.4); } }
      else if (idle >= S.cfg.stuckMs[0] && a.stuck < 1) { a.stuck = 1; if (!c.sleeping && c.state === 'sit') { c.setAction('think'); c.emote('question', 2.2); } }
    }
    const ceo = C('ceo');
    if (S.signal !== lastSig) { if (S.signal === 'quiet' && ceo && !ceo.piloted && !ceo.sleeping && ceo.state === 'sit') { ceo.setAction('drink'); ceo.emote('note', 1.4); } lastSig = S.signal; linkChanged(); }
    const p = S.flags.permission;       // 3 分鐘再提醒一次（分頁標題閃一下）、10 分鐘 CEO 開始抓頭
    if (p) { const age = now - p.since; if (p.reminded < 1 && age >= S.cfg.remindMs[0]) { p.reminded = 1; J.remindN = (J.remindN || 0) + 1; document.title = `(!) CEO 還在等你核准`; setTimeout(() => flagsChanged(), 4000); }
      if (p.reminded < 2 && age >= S.cfg.remindMs[1]) { p.reminded = 2; if (ceo && !ceo.piloted && !ceo.sleeping) { ceo.emote('sweat', 2.6); } } }
  }, 1000);

  // ───────── 事件 ─────────
  S.on(e => {
    switch (e.name) {
      case 'SubagentStart': startJob(e); break;
      case 'PreToolUse': tool(e); break;
      case 'SubagentStop': stopJob(e); break;
      case 'UserPromptSubmit': { const c = C('ceo'); if (c && !c.piloted && !c.sleeping) { c.emote('bulb', 1.6); if (c.state === 'sit') c.setAction('type'); } break; }
      case 'SessionStart': { const c = C('ceo'); if (c && !c.piloted) { wakeOne(c); c.emote('star', 1.6); if (c.state === 'sit' && c.atDesk) c.setAction('type'); else D.goHome(c, { speed: 2.4 }); } break; }
      case 'SessionEnd': { const c = C('ceo'); if (c && !c.piloted && !c.sleeping) { c.setAction('wave'); c.say('今天先到這裡，收工！', 2.4); } break; }
    }
    flagsChanged(); linkChanged();
  });
  J.statusSync = linkChanged;
  return J;
}
