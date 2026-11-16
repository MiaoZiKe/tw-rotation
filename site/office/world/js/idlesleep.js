// 閒置就睡（2026-11-16，擁有者：「專案做完後沒在工作的 Agent 要處於睡覺狀態，一眼看出哪些在執行、哪些在休息」）。
// 規則：某位同事「最後一次任務事件」（領任務／進行中／交件）離現在超過 IDLE_SLEEP_MS（預設 30 分鐘）→ 回自己座位趴桌睡，
//   頭上持續 Zz、名牌狀態字寫「休息中」；睡著期間不參與 director 的隨機閒晃、運動（director.pickIdle 看 napDue）。
//   一有新任務（領任務、工具事件）立刻醒來：驚醒表情＋驚嘆號，接著 jobs.js 照常演出去領任務。
//   CEO、寵物、離職、外出的人不睡。額度用完全員睡覺（power.js）照舊：那段期間這支完全不動，額度恢復被喚醒的人重新計 30 分鐘。
// 「最後一次任務」從哪來：狀態層 S.agents 的 since（領任務）、lastToolAt（最近一次工具事件）、done[0].t（最近交件，live.js 也會把歷史交件塞進來）；
//   進行中（phase 不是 idle）一律算在工作。都沒有紀錄的人，以這個頁面載入的時間當起點（所以新開頁面不會一進來就全員睡）。
// 為什麼獨立一支：不改 main.js／live.js（別人同時在改），只掛在 window.__world 上；與 director／jobs／ui 只有三個一行的銜接點（napDue、napping）。
// 示範模式（?demo=1）：載入時替部分同事塞「假的最後工作時間」，才看得到睡著的樣子。
import { whenWorld } from './workkit.js';

export const IDLE_SLEEP_MS = 30 * 60e3;   // 閒置多久就睡；要改只改這一個常數（驗收用 ?idlesleep=<分鐘> 或 W.idlesleep.ms 覆寫）
const FEATURE = 'office.idlesleep';
const hash = s => { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };

whenWorld(W => {
  const S = W.state, D = W.director, qs = new URLSearchParams(location.search), C = id => W.chars.get(id);
  const qm = +qs.get('idlesleep');
  const IS = { ms: qm > 0 ? qm * 60e3 : IDLE_SLEEP_MS, last: new Map(), born: S.now(), naps: 0, wakes: 0, on: true };
  W.idlesleep = IS;
  const sleepable = c => c && !c.spec.isCeo && !c.spec.pet && !c.jobless && !c.away;
  const featureOn = () => { try { const g = W.gate && W.gate.peek ? W.gate.peek(FEATURE) : null; return !g || g.pass !== false; } catch (e) { return true; } };
  const powerOut = () => !!(W.power && W.power.sleeping && W.power.sleeping());

  // 最後一次任務時間（毫秒）；正在做事回傳 now
  IS.lastWork = c => {
    const id = c.spec.id, a = S.agents.get(id), now = S.now();
    if (a && a.phase !== 'idle') return now;
    const t = Math.max(IS.last.get(id) || 0, a ? a.since || 0 : 0, a ? a.lastToolAt || 0 : 0, a && a.done && a.done[0] ? a.done[0].t || 0 : 0);
    return t || IS.born;                       // 完全沒有紀錄才用載入時間當起點（有紀錄就照紀錄，才能反映「很久以前做過」）
  };
  IS.setLast = (id, ts) => { IS.last.set(id, ts); const a = S.agents.get(id); if (a && a.phase === 'idle') { a.since = 0; a.lastToolAt = 0; if (a.done) a.done.length = 0; } };   // 驗收／示範注入用：把這個人的最後工作時間設成 ts
  IS.idleMs = c => S.now() - IS.lastWork(c);
  IS.isNapping = c => !!(c && c.napping);

  function wake(c, why) {
    if (!c.napping) return;
    c.napping = false; c.napDue = false; c.sleeping = false; IS.wakes++; if (why !== 'task') c.busy = false;   // 有任務時 jobs.js 自己會設 busy
    IS.last.set(c.spec.id, S.now());          // 醒了就重新計時（任務事件本身也會更新）
    if (c.action === 'sleep' && c.state === 'sit') { c.setExpression('neutral', 0.1); c.setAction('stretch', { then: 'type' }); }
    if (why === 'task') { c.setExpression('surprised', 1.4); c.emote('exclaim', 1.4); }
  }
  function nap(c) {
    c.napping = true; c.napDue = true; c.sleeping = true; IS.naps++; c.busy = true; c.script = (c.script || 0) + 1; c.job = (c.job || 0) + 1;
    c.setAction('sleep'); c.setExpression('sleepy', 1e9); c.emote('zzz', 3.2);
    const f = c.spot && c.spot.seat && c.spot.seat.face, p = c.object3D.position; if (f != null && c.state === 'sit') c.faceTo(p.x + Math.sin(f), p.z + Math.cos(f));
  }

  IS.check = () => {
    const out = powerOut(), on = featureOn();
    for (const c of W.chars.values()) {
      if (!sleepable(c)) { if (c.napping || c.napDue) { c.napping = false; c.napDue = false; } continue; }
      const a = S.agents.get(c.spec.id), working = !!a && a.phase !== 'idle';
      if (c.napping) {
        if (out) continue;                                                       // 額度用完全員睡：由 power.js 負責，這裡不插手
        if (working || !on || c.action !== 'sleep' || c.state !== 'sit' || c.piloted || IS.idleMs(c) < IS.ms) { wake(c, working ? 'task' : 'other'); continue; }
        if (!c.emoteSym) c.emote('zzz', 3.2);                                    // 頭上持續 Zz
        continue;
      }
      if (out || !on || working || c.piloted || c.state === 'held' || (D.meeting && D.meeting.people.includes(c))) { c.napDue = false; continue; }
      if (IS.idleMs(c) < IS.ms) { c.napDue = false; continue; }
      c.napDue = true;                                                           // 到時間了：director 不再派他去閒晃
      if (c.state === 'sit' && c.atDesk && !c.busy) nap(c);
      else if (!c.hrBusy && S.now() - (c._napSent || 0) > 8000) { c._napSent = S.now(); D.sendHome(c); }   // 不在座位或還在晃（咖啡、運動…）：中斷手上的事走回座位，到了 sendHome 會放掉 busy，下一秒就睡
    }
  };
  // 示範：載入時塞假的最後工作時間（約三分之一的人超過門檻），其餘是剛工作過
  if (qs.get('demo') === '1') {
    for (const c of W.chars.values()) if (sleepable(c)) { const h = hash(c.spec.id); IS.last.set(c.spec.id, S.now() - (h % 3 === 0 ? (IS.ms + 12 * 60e3 + (h % 7) * 60e3) : (1 + h % 9) * 60e3)); }
  }
  S.on(() => setTimeout(IS.check, 0));
  setInterval(IS.check, 1000);
  IS.check();
});
