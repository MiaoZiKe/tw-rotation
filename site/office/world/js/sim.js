// 事件模擬器（開發用）：手動觸發狀態層每一種事件，或一鍵播放一段「典型的一天」。
// 入口：網址加 ?sim=1 才會在頂列出現「模擬」鈕（預設收起，點開才是面板）；沒加這個參數時介面上完全看不到。
// 它送的事件格式與真資料完全相同（見 state.js 開頭），所以之後橋接器上線，只是把 emit 的來源換掉。
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const NAMES = { read: '讀檔', write: '寫檔', search: '查資料', test: '跑測試', deploy: '部署', wait: '等部署', other: '泛用' };

export function createSim(W, X) {
  const { state: S, demo, ui } = X, Sim = { n: 0, timers: [], playing: false, last: new Map() };
  const sec = () => Math.floor(Date.now() / 1000);
  Sim.cycleEnd = 0;     // 同一個額度週期的重置時間固定（真資料也是固定的），用完／恢復才換新的一輪
  const members = () => [...W.chars.values()].filter(c => !c.spec.isCeo && !c.jobless && !c.away);
  const emit = o => S.emit({ hook_event_name: o.name, ...o.rest, ...(o.ev || {}) });
  const E = (name, rest = {}) => S.emit({ hook_event_name: name, ...rest });
  Sim.emit = E;

  // ── 額度 ──
  Sim.quota = (remainFive, remainWeek, resetSec = 8100) => { if (!Sim.cycleEnd || Sim.cycleEnd < sec()) Sim.cycleEnd = sec() + resetSec; return E('rate_limits', {
    five_hour: remainFive == null ? undefined : { used_percentage: 100 - remainFive, resets_at: Sim.cycleEnd },
    seven_day: remainWeek == null ? undefined : { used_percentage: 100 - remainWeek, resets_at: sec() + 3 * 86400 }
  }); };
  Sim.quotaNone = () => E('rate_limits', { rate_limits: null });
  Sim.stale = (min = 23) => E('rate_limits', { ts: Date.now() - min * 60e3, five_hour: { used_percentage: 38, resets_at: sec() + 5000 }, seven_day: { used_percentage: 59, resets_at: sec() + 3 * 86400 } });
  Sim.exhaust = (resetSec = 8100) => E('rate_limit_event', { status: 'rejected', ...(resetSec == null ? {} : { resetsAt: sec() + resetSec }) });
  Sim.recover = () => { Sim.cycleEnd = 0; return E('QuotaRecovered'); };
  // ── 工作階段與提醒 ──
  Sim.session = on => E(on ? 'SessionStart' : 'SessionEnd');
  Sim.prompt = () => E('UserPromptSubmit');
  Sim.permission = (category = 'command') => E('Notification', { notification_type: 'permission_prompt', category });
  Sim.question = (question = '要用哪一個做法？') => E('Notification', { notification_type: 'elicitation_dialog', question });
  Sim.clear = () => E('NotificationClear');
  Sim.lost = () => E('SignalLost');
  // ── 派工 ──
  const descOf = c => { const pool = demo.tasks[c.spec.dept] || demo.tasks.ceo; return pool[(Sim.n * 3 + c.spec.id.length) % pool.length]; };
  Sim.start = (id, desc, tool) => { const c = W.chars.get(id) || members()[0]; const aid = 'sim-' + (++Sim.n); Sim.last.set(c.spec.id, aid); E('SubagentStart', { agent_id: aid, agent_type: c.spec.id, description: desc || descOf(c), ...(tool ? { tool_category: tool } : {}) }); return aid; };
  Sim.tool = (id, cat) => { const aid = id ? Sim.last.get(id) : null; E('PreToolUse', { tool_category: cat, ...(aid ? { agent_id: aid } : {}) }); };
  Sim.stop = (id, ok = true) => { const aid = Sim.last.get(id); if (!aid) return false; const c = W.chars.get(id); E('SubagentStop', { agent_id: aid, agent_type: id, status: ok ? 'completed' : 'failed', last_assistant_message: ok ? descOf(c) + ' 已完成' : '測試沒過，需要再看一下' }); return true; };

  // ── 典型的一天：約 80 秒；k 是時間倍率（k=0.1 就是 8 秒播完，測試用） ──
  Sim.stopDay = () => { Sim.timers.forEach(clearTimeout); Sim.timers = []; Sim.playing = false; if ($('simDay')) $('simDay').textContent = '播放'; };
  Sim.playDay = (k = 1, outSec = null) => {      // outSec：額度用完到恢復要幾秒（預設隨倍率縮；測試會給長一點，讓全員有時間睡下去）
    Sim.stopDay(); Sim.playing = true; if ($('simDay')) $('simDay').textContent = '停止';
    const ms = members(), pick = i => ms[(i * 7) % ms.length].spec.id, A = pick(1), B = pick(2), Cc = pick(3), Dd = pick(4);
    const out = outSec != null ? outSec : Math.max(3, Math.round(25 * k)), after = 57 * 1000 * k + (out + 2) * 1000;   // 恢復之後的步驟，接在恢復時間後面
    const steps = [
      [0, () => Sim.session(true)], [1, () => Sim.quota(62, 80)], [2.5, () => Sim.prompt()],
      [4, () => Sim.start(A)], [5, () => Sim.start(B)], [6, () => Sim.start(Cc)],
      [9, () => Sim.tool(A, 'read')], [10, () => Sim.tool(B, 'write')], [11, () => Sim.tool(Cc, 'search')],
      [14, () => Sim.permission('command')], [19, () => Sim.clear()],
      [21, () => Sim.tool(A, 'test')], [24, () => Sim.stop(A, true)], [27, () => Sim.stop(Cc, false)], [30, () => Sim.stop(B, true)],
      [33, () => Sim.quota(18, 70)], [37, () => Sim.question('要先處理哪一件？')], [42, () => Sim.prompt()],
      [44, () => Sim.start(Dd)], [47, () => Sim.tool(Dd, 'deploy')], [50, () => Sim.tool(Dd, 'wait')], [53, () => Sim.stop(Dd, true)],
      [57, () => Sim.exhaust(out)]                         // 額度用完：大家去睡，out 秒後時間到自動恢復
    ];
    for (const [t, fn] of steps) Sim.timers.push(setTimeout(() => { try { fn(); } catch (e) { console.error('模擬器步驟例外', e); } }, t * 1000 * k));
    Sim.timers.push(setTimeout(() => { try { Sim.quota(95, 60); } catch (e) { console.error(e); } }, after));
    Sim.timers.push(setTimeout(() => { try { Sim.session(false); } catch (e) { console.error(e); } }, after + 3000 * k));
    Sim.timers.push(setTimeout(() => Sim.stopDay(), after + 5000 * k));
  };

  // ── 面板（只有 ?sim=1 才建立入口） ──
  if (new URLSearchParams(location.search).get('sim') === '1') {
    const btn = document.createElement('button'); btn.className = 'btn'; btn.id = 'simBtn'; btn.innerHTML = '模擬<i></i>'; $('bar').insertBefore(btn, $('editBtn'));
    const pop = document.createElement('div'); pop.className = 'pop sim-pop'; pop.id = 'simPop'; pop.hidden = true; $('app').append(pop);
    const b = (id, t, cls = '') => `<button class="it sm ${cls}" data-sim="${id}">${esc(t)}</button>`;
    const render = () => {
      const opts = members().map(c => `<option value="${esc(c.spec.id)}">${esc(c.spec.nick)}・${esc(c.spec.zh)}</option>`).join('');
      pop.innerHTML = `<h4>額度</h4><div class="sm-row">${b('q62', '剩 62%')}${b('q18', '剩 18%')}${b('q8', '剩 8%')}${b('out1', '用完（有恢復時間）')}${b('out2', '用完（時間未提供）')}${b('rec', '恢復')}${b('qna', '未提供額度')}${b('stale', '資料過舊')}</div>
        <h4>提醒與訊號</h4><div class="sm-row">${b('perm', '等核准')}${b('ask', '等回答')}${b('clr', '處理完了')}${b('lost', '訊號不明')}${b('ping', '恢復訊號')}</div>
        <h4>工作階段</h4><div class="sm-row">${b('ss1', '開始')}${b('ss0', '結束')}${b('prompt', '送出指令')}</div>
        <h4>派工</h4><div class="sm-row"><select id="simWho" aria-label="同事">${opts}</select><select id="simTool" aria-label="工具類別">${Object.entries(NAMES).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div>
        <div class="sm-row">${b('st', '派出')}${b('tl', '換工具')}${b('okk', '交件成功')}${b('bad', '交件失敗')}${b('many', '一次派 10 位')}</div>
        <h4>情緒演示（對上面選的同事）</h4><div class="sm-row">${b('mrw', '頒獎')}${b('mpr', '稱讚')}${b('mrj', '退件')}${b('mdm', '降等')}${b('mkn', '被丟出去')}${b('mbn', '被燒到')}${b('mrc', '恢復')}</div>
        <h4>典型的一天</h4><div class="sm-row"><button class="it sm on" id="simDay" data-sim="day">${Sim.playing ? '停止' : '播放'}</button><label class="sm-k">倍速<select id="simK"><option value="1">1×</option><option value="0.2">5×</option><option value="0.1">10×</option></select></label></div>`;
    };
    const who = () => $('simWho').value;
    pop.addEventListener('click', e => {
      const t = e.target.closest('[data-sim]'); if (!t) return; const k = t.dataset.sim;
      const m = { q62: () => Sim.quota(62, 80), q18: () => Sim.quota(18, 70), q8: () => Sim.quota(8, 70), out1: () => Sim.exhaust(8100), out2: () => Sim.exhaust(null), rec: Sim.recover, qna: Sim.quotaNone, stale: () => Sim.stale(23),
        perm: () => Sim.permission('command'), ask: () => Sim.question(), clr: Sim.clear, lost: Sim.lost, ping: Sim.prompt, ss1: () => Sim.session(true), ss0: () => Sim.session(false), prompt: Sim.prompt,
        st: () => Sim.start(who(), null, $('simTool').value), tl: () => Sim.tool(who(), $('simTool').value), okk: () => Sim.stop(who(), true), bad: () => Sim.stop(who(), false),
        mrw: () => W.emit('rewarded', who(), { kind: 'award' }), mpr: () => W.emit('praised', who(), { by: 'ceo' }), mrj: () => W.emit('rejected', who(), {}), mdm: () => W.emit('demoted', who(), {}), mkn: () => W.emit('knocked', who(), { by: 'you' }), mbn: () => W.emit('burned', who(), {}), mrc: () => W.emit('recovered', who(), {}),
        many: () => members().slice(0, 10).forEach(c => Sim.start(c.spec.id)), day: () => { if (Sim.playing) Sim.stopDay(); else Sim.playDay(+$('simK').value || 1); } };
      if (m[k]) m[k]();
    });
    btn.onclick = () => { const was = pop.hidden; ui.closePops(); if (was) { render(); } pop.hidden = !was; if (was) { const r = btn.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; } };
    document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#simPop') && !e.target.closest('#simBtn')) pop.hidden = true; });
    Sim.pop = pop; Sim.btn = btn;
  }
  void emit;
  return Sim;
}
