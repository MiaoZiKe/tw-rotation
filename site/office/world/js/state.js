// 辦公室狀態層：所有演出只讀這一層。示範（模擬器）與之後的真資料，都以「事件」餵進同一個入口 state.emit(ev)。
//
// ── 事件格式（刻意對得上 docs/ai_office/bridge_test_report.md 實測到的掛鉤事件，之後橋接器送來的 JSON 可以直接 emit）──
//   共同欄位：hook_event_name（事件名）、ts（毫秒時間，沒有就用收到的時間）、session_id（可省略）
//   SessionStart / SessionEnd                       工作階段開始／結束
//   UserPromptSubmit                                使用者送出指令（不帶全文：隱私，只取「有人說話」這件事）
//   SubagentStart   { agent_id, agent_type, description }      派出子 Agent（agent_type 對得上同事代號就用他，否則依雜湊挑一位）
//   PreToolUse      { tool_category, agent_id? }               工具類別：read／write／search／test／deploy／wait／other；沒帶 agent_id 就是 CEO 自己
//   SubagentStop    { agent_id, status:'completed'|'failed', last_assistant_message? }
//   Notification    { notification_type:'permission_prompt'|'elicitation_dialog'|'idle_prompt', category?, question? }
//   NotificationClear { kinds?:['permission'|'question'] }    使用者處理完了（真資料裡是下一個 PostToolUse／UserPromptSubmit 自然帶出）
//   rate_limits     { five_hour?:{used_percentage,resets_at}, seven_day?:{…} } | null   狀態列腳本給的額度快照；null＝這個接入沒有額度資料（未提供）
//   rate_limit_event{ status:'allowed'|'allowed_warning'|'rejected', resetsAt? }          串流輸出的限流事件；rejected＝額度用完
//   QuotaRecovered                                  額度恢復（也可由時間到自動判定）
//   SignalLost                                      訊號不明（對方整段沒消息）
// resets_at／resetsAt：秒或毫秒的時間戳都收（小於 1e12 視為秒）。
//
// 鐵則：沒有的資料就是「未提供」，不亂猜、不補數字（detail_spec 的底線 ②）。
const toMs = v => (v == null ? null : (+v < 1e12 ? +v * 1000 : +v));
const CATS = ['read', 'write', 'search', 'test', 'deploy', 'wait', 'other'];
export const TOOL_TEXT = { read: '讀資料中', write: '寫程式中', search: '查資料中', test: '跑測試中', deploy: '部署中', wait: '等部署中', other: '工作中' };
export const PERM_TEXT = { command: '要執行一個指令', edit: '要修改檔案', web: '要連到網路', other: '要做一個動作' };

export function createState(opts = {}) {
  const S = {
    now: opts.now || (() => Date.now()),
    // 門檻（全部可調，預設值照 detail_spec A.0）；毫秒
    cfg: { quietMs: 5 * 60e3, unknownMs: 30 * 60e3, stuckMs: [3 * 60e3, 10 * 60e3], remindMs: [3 * 60e3, 10 * 60e3], lowPct: 20, mildPct: 10 },
    q: { five: null, week: null, provided: false, exhausted: false, resetsAt: null, asOf: null },   // 額度；five／week＝{used 0..100, resetsAt ms|null}
    flags: { permission: null, question: null },                                                         // 等核准、等回答（只存動作類別，不存全文）
    session: { active: false, startedAt: null, lastEventAt: null, hadEvent: false, forcedUnknown: false },
    signal: 'ok',                                                                                        // ok｜quiet（5 分鐘沒消息，不當異常）｜unknown（30 分鐘沒消息且曾有事件）
    agents: new Map(),                                                                                   // 同事代號 → { phase, tool, task, agentId, since, lastToolAt, done, failed }
    byAgentId: new Map(),                                                                                // 事件裡的 agent_id → 同事代號
    log: [], seen: new Set(), count: 0, listeners: [],
  };
  const say = text => { S.log.unshift({ t: S.now(), text }); if (S.log.length > 120) S.log.length = 120; };
  S.say = say;
  S.on = fn => { S.listeners.push(fn); return () => { S.listeners = S.listeners.filter(f => f !== fn); }; };
  const agent = id => { let a = S.agents.get(id); if (!a) { a = { phase: 'idle', tool: null, task: '', agentId: null, since: 0, lastToolAt: 0, done: [], failed: 0 }; S.agents.set(id, a); } return a; };
  S.agent = agent;

  // 額度的衍生資訊：剩餘比例取「有資料的時間窗裡最少的那個」；全部沒資料就是 null（未提供）
  S.quotaInfo = () => {
    const q = S.q, w = k => (q[k] ? { remain: Math.max(0, Math.min(100, Math.round(100 - q[k].used))), resetsAt: q[k].resetsAt } : null);
    const five = w('five'), week = w('week'), have = [five, week].filter(Boolean);
    const remain = q.exhausted ? 0 : have.length ? Math.min(...have.map(x => x.remain)) : null;
    const level = q.exhausted ? 'out' : remain == null ? 'na' : remain <= S.cfg.mildPct ? 'mild' : remain <= S.cfg.lowPct ? 'low' : 'ok';
    return { provided: q.provided || q.exhausted, remain, five, week, level, exhausted: q.exhausted, resetsAt: q.resetsAt, resetKnown: q.resetsAt != null };
  };

  function applyRate(r) {
    const q = S.q;
    if (r == null) { q.five = q.week = null; q.provided = false; if (!q.exhausted) q.resetsAt = null; return; }
    const one = x => (x && x.used_percentage != null ? { used: Math.max(0, Math.min(100, +x.used_percentage)), resetsAt: toMs(x.resets_at ?? x.resetsAt) } : null);
    q.five = one(r.five_hour); q.week = one(r.seven_day); q.provided = !!(q.five || q.week);
    const full = [q.five, q.week].filter(x => x && x.used >= 100);
    if (full.length) { q.exhausted = true; q.resetsAt = full.map(x => x.resetsAt).filter(Boolean).sort()[0] ?? null; }
    else if (q.exhausted) { q.exhausted = false; q.resetsAt = null; }       // 快照顯示又有額度了＝已恢復
  }

  // 事件進來：去重（同一個 uid 不演第二次）→ 更新狀態 → 通知控制器。回傳這筆事件正規化後的樣子。
  S.emit = ev => {
    if (!ev || !(ev.hook_event_name || ev.type)) return null;
    const e = { ...ev }; e.name = e.hook_event_name || e.type; e.ts = e.ts || S.now();
    if (e.uid) { if (S.seen.has(e.uid)) return null; S.seen.add(e.uid); }
    S.count++;
    const ss = S.session; ss.lastEventAt = e.ts; if (e.name !== 'SignalLost') { ss.hadEvent = true; ss.forcedUnknown = false; }
    const wasExhausted = S.q.exhausted;
    switch (e.name) {
      case 'SessionStart': ss.active = true; ss.startedAt = e.ts; say('CEO 開工'); break;
      case 'SessionEnd': { const m = ss.startedAt ? Math.max(1, Math.round((e.ts - ss.startedAt) / 60000)) : null; ss.active = false; say(m ? `CEO 收工・本次 ${m} 分鐘` : 'CEO 收工'); break; }
      case 'UserPromptSubmit': S.flags.permission = S.flags.question = null; say('你對 CEO 下了指令'); break;
      case 'SubagentStart': break;      // 對應同事由控制器決定（要看座位與在職狀態），見 jobs.js
      case 'rate_limits': applyRate(e.rate_limits === undefined ? e : e.rate_limits); break;
      case 'rate_limit_event':
        if (e.status === 'rejected') { S.q.exhausted = true; S.q.resetsAt = toMs(e.resetsAt ?? e.resets_at); }
        else { S.q.exhausted = false; S.q.resetsAt = null; }
        break;
      case 'QuotaRecovered': S.q.exhausted = false; S.q.resetsAt = null; break;
      case 'Notification': {
        const k = e.notification_type;
        if (k === 'permission_prompt') S.flags.permission = { category: PERM_TEXT[e.category] ? e.category : 'other', since: e.ts, reminded: 0 };
        else if (k === 'elicitation_dialog') S.flags.question = { text: e.question ? String(e.question).slice(0, 60) : '', since: e.ts };
        break;
      }
      case 'NotificationClear': { const ks = e.kinds || ['permission', 'question']; if (ks.includes('permission')) S.flags.permission = null; if (ks.includes('question')) S.flags.question = null; break; }
      case 'SignalLost': ss.forcedUnknown = true; break;
    }
    if (e.name === 'rate_limits' || e.name === 'rate_limit_event' || e.name === 'QuotaRecovered') S.q.asOf = e.ts;
    S.derive();
    for (const f of S.listeners.slice()) { try { f(e, S, { wasExhausted }); } catch (x) { console.error('狀態監聽例外', x); } }
    return e;
  };

  // 衍生：連線訊號與「額度用完後時間到了自動恢復」。由控制器每秒呼叫一次。
  S.derive = () => {
    const ss = S.session, gap = ss.lastEventAt ? S.now() - ss.lastEventAt : 0;
    S.signal = ss.forcedUnknown || (ss.hadEvent && gap >= S.cfg.unknownMs) ? 'unknown' : ss.hadEvent && gap >= S.cfg.quietMs ? 'quiet' : 'ok';
  };
  S.tick = () => {
    S.derive();
    if (S.q.exhausted && S.q.resetsAt != null && S.now() >= S.q.resetsAt) S.emit({ hook_event_name: 'QuotaRecovered', source: 'timer' });
  };
  S.CATS = CATS;
  return S;
}

// 台北時間的小工具（顯示一律台北時間）
const f1 = new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', hourCycle: 'h23', hour: '2-digit', minute: '2-digit' });
const f2 = new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', weekday: 'short' });
const f3 = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', month: '2-digit', day: '2-digit' });
export const hhmm = ms => f1.format(new Date(ms));
export const wk = ms => f2.format(new Date(ms)).replace('週', '週');
export const mmdd = ms => { const p = {}; for (const x of f3.formatToParts(new Date(ms))) p[x.type] = x.value; return `${p.month}-${p.day}`; };
// 剩餘時間的口語：約 2 小時 15 分／不到 1 分鐘
export const span = ms => { const m = Math.ceil(Math.max(0, ms) / 60000); if (m < 1) return '不到 1 分鐘'; const h = Math.floor(m / 60), r = m % 60; return '約 ' + (h ? h + ' 小時' + (r ? ' ' + r + ' 分' : '') : r + ' 分'); };
