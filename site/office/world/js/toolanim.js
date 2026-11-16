// 真實工具呼叫 → 角色動作＋頭上小圖示（2026-11-16 第二批第 1 項；Andy：「全做」）
//
// 資料從哪來：外掛（bridge.py）在 PreToolUse 只送「工具類別」（read／write／search／test／deploy／wait／other／dispatch），
//   不送檔名、指令原文、檔案內容；收件服務（worker.js）把主工作階段最近一次的類別記在 sessions.tool／tool_at，子 Agent 記在 agents.tool／tool_at。
//   live.js 每讀到一筆事件就呼叫 W.toolanim.onEvent(e, 角色)，第一次連上時用快照（sessions／agents 的 tool、tool_at）補上。
// 對應（Andy 指定）：讀檔→翻書、寫檔／編輯→打字、跑測試→盯螢幕、搜尋→放大鏡、派子 Agent→打電話；部署、等部署、其他沿用原本的動作。
// 閒置：同一位 N 秒（預設 40 秒，網址 ?toolanim_idle=秒 可改）沒有新的工具事件 → 圖示收起、動作回到預設（坐著打字）。
//   外掛對同一類別 20 秒內只送一次，所以 N 必須大於 20 秒，不然連續讀檔時圖示會一閃一閃。
// 「失聯」：連線健康燈（health.js）判斷斷線時在 CEO 頭上掛「失聯」圖示，恢復後拿掉 —— 不讓角色假裝還在工作。
// 功能鍵 office.liveviz（gate.js）：關掉＝不顯示圖示、不改動作（原本 jobs.js 的動作照舊）。
import { THREE } from './kit.js';

const ICON = {
  read: ['翻書', '讀檔中', '<path d="M4 5.5c2.6-1 5-1 8 .8v12.2c-3-1.8-5.4-1.8-8-.8z"/><path d="M20 5.5c-2.6-1-5-1-8 .8v12.2c3-1.8 5.4-1.8 8-.8z"/>', '#4f7cc4'],
  write: ['打字', '寫檔中', '<rect x="3" y="7" width="18" height="10" rx="2"/><path d="M6.5 10.2h.01M9.5 10.2h.01M12.5 10.2h.01M15.5 10.2h.01M8 13.8h8"/>', '#d0812a'],
  test: ['盯螢幕', '跑測試中', '<rect x="3.5" y="4.5" width="17" height="11" rx="1.6"/><path d="M9 19.5h6M12 15.5v4"/><path d="M8 11l2 2 4-4.5"/>', '#2f9a62'],
  search: ['放大鏡', '搜尋中', '<circle cx="10.5" cy="10.5" r="5.5"/><path d="M15 15l5 5"/>', '#7a5bc2'],
  dispatch: ['打電話', '派人中', '<path d="M6.6 3.8l2.6 2.7-1.6 2.2a12 12 0 0 0 7.7 7.7l2.2-1.6 2.7 2.6-1.8 2.4C11.6 20 4 12.4 4.2 5.6z"/>', '#c2496f'],
  deploy: ['部署', '部署中', '<path d="M12 3c3 2 4.5 5.2 4 9l-2.5 2.5h-3L8 12c-.5-3.8 1-7 4-9z"/><path d="M9.5 15.5L7 19M14.5 15.5L17 19"/><circle cx="12" cy="9" r="1.2"/>', '#cf5d2b'],
  wait: ['等待', '等部署中', '<path d="M7 3.5h10M7 20.5h10M8 3.5c0 5 8 5 8 8.5s-8 3.5-8 8.5M16 3.5c0 5-8 5-8 8.5"/>', '#8a7d6e'],
  other: ['工作', '工作中', '<circle cx="12" cy="12" r="3"/><path d="M12 3.5v2.5M12 18v2.5M3.5 12H6M18 12h2.5M6 6l1.8 1.8M16.2 16.2L18 18M6 18l1.8-1.8M16.2 7.8L18 6"/>', '#6b7285'],
  lost: ['失聯', '失聯中：暫時收不到你的 Claude 的消息', '<path d="M4 9.5a12 12 0 0 1 16 0M7 12.8a7.5 7.5 0 0 1 10 0M10.2 16a3 3 0 0 1 3.6 0"/><path d="M4 4l16 16"/>', '#b8452a'],
};
const ACT = { read: 'read', write: 'type', test: 'think', search: 'magnify', dispatch: 'phone', deploy: 'tablet', wait: 'drink', other: 'type' };
export const TOOL_ICON = ICON;

export function createToolAnim(W, X = {}) {
  const S = X.state, qs = new URLSearchParams(location.search);
  const idleSec = Math.max(3, +qs.get('toolanim_idle') || 40);
  const T = { idleMs: idleSec * 1000, cur: new Map(), on: true, nSet: 0 };
  W.toolanim = T;
  const gateOn = () => { try { return !W.gate || !W.gate.peek || W.gate.peek('office.liveviz').pass !== false; } catch (e) { return true; } };

  const css = document.createElement('style'); css.id = 'taCss';
  css.textContent = `
#taLayer{position:fixed;inset:0;pointer-events:none;z-index:4;overflow:hidden}
.ta-i{position:absolute;left:0;top:0;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;background:#fffaf2;border:2.5px solid var(--c);box-shadow:0 2px 6px rgba(74,58,50,.25);display:flex;align-items:center;justify-content:center;transition:opacity .35s;will-change:transform}
.ta-i svg{width:18px;height:18px;fill:none;stroke:var(--c);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ta-i.pop{animation:taPop .45s ease-out}.ta-i.off{opacity:0}
.ta-i.lost{background:#fff1ea}
@keyframes taPop{0%{scale:.4}60%{scale:1.18}100%{scale:1}}
@media (prefers-reduced-motion:reduce){.ta-i.pop{animation:none}}
@media (max-width:640px){.ta-i{width:24px;height:24px;margin:-12px 0 0 -12px;border-width:2px}.ta-i svg{width:14px;height:14px}}`;
  document.head.append(css);
  const layer = document.createElement('div'); layer.id = 'taLayer'; layer.setAttribute('aria-hidden', 'true'); document.body.append(layer);

  const keyOf = c => (c && c.spec && c.spec.id) || null;
  const free = c => c && !c.piloted && !c.sleeping && c.state === 'sit' && c.state !== 'held';
  function act(c, cat) {
    const a = ACT[cat]; if (!a || !free(c)) return;
    if (c.spec.isCeo && S && (S.flags.permission || S.flags.question)) return;   // 等核准／等回答時 CEO 舉手的動作優先
    c.setAction(a); c.workAt = W.time + (c.spec.isCeo ? 30 : 600);
  }
  /** 設定某位角色目前的工具類別。at＝事件時間（本機毫秒）；sticky＝不受閒置計時（失聯用） */
  T.set = (c, cat, at, opt = {}) => {
    const k = keyOf(c); if (!k || !ICON[cat] || !gateOn()) return false;
    let x = T.cur.get(k);
    if (!x) { const el = document.createElement('div'); el.className = 'ta-i'; layer.append(el); x = { el, c }; T.cur.set(k, x); }
    const changed = x.cat !== cat;
    Object.assign(x, { c, cat, at: at || Date.now(), sticky: !!opt.sticky, prev: opt.sticky ? (x.sticky ? x.prev : x.cat ? { cat: x.cat, at: x.at } : null) : null });
    if (changed) {
      const [, label, svg, col] = ICON[cat];
      x.el.style.setProperty('--c', col); x.el.innerHTML = `<svg viewBox="0 0 24 24">${svg}</svg>`; x.el.dataset.cat = cat; x.el.dataset.who = k; x.el.title = label;
      x.el.classList.toggle('lost', cat === 'lost'); x.el.classList.remove('off', 'pop'); void x.el.offsetWidth; x.el.classList.add('pop');
    }
    if (!opt.sticky && !opt.noAct) act(c, cat);
    T.nSet++;
    return true;
  };
  T.clear = (c, revert = true) => {
    const k = typeof c === 'string' ? c : keyOf(c), x = k && T.cur.get(k); if (!x) return;
    T.cur.delete(k); x.el.classList.add('off'); setTimeout(() => x.el.remove(), 400);
    if (revert && x.cat && x.cat !== 'lost' && free(x.c) && x.c.action === ACT[x.cat]) { x.c.setAction('type'); x.c.workAt = W.time + 5; }
  };
  /** 失聯：在 CEO（與分身）頭上掛「失聯」；恢復時還原原本的工具圖示（還沒過期的話） */
  T.lost = (chars, on) => {
    for (const c of chars) {
      const k = keyOf(c); if (!k) continue; const x = T.cur.get(k);
      if (on) T.set(c, 'lost', Date.now(), { sticky: true });
      else if (x && x.cat === 'lost') { const p = x.prev; if (p && Date.now() - p.at < T.idleMs) { x.sticky = false; T.set(c, p.cat, p.at, { noAct: true }); } else T.clear(c, false); }
    }
  };
  T.state = () => [...T.cur].map(([k, x]) => ({ who: k, cat: x.cat, act: x.c && x.c.action, age: Date.now() - x.at, el: !!x.el.isConnected }));
  /** live.js 每一筆真實事件都丟進來；c＝這筆事件屬於哪一位角色（live.js 已經算好：子 Agent＝名冊上的同事，主工作階段＝CEO 或分身） */
  T.onEvent = (e, c, at) => {
    if (!c) return;
    if (e.event === 'PreToolUse' && e.tool_category && e.tool_category !== 'ask') T.set(c, e.tool_category, at);
    else if (e.event === 'SubagentStop' || e.event === 'Stop' || e.event === 'SessionEnd') T.clear(c);
  };
  T.reset = () => { for (const k of [...T.cur.keys()]) T.clear(k, false); };

  // ───────── 每一幀：把圖示放到角色頭上；過期的收起來 ─────────
  const v = new THREE.Vector3(), LIFT_PX = matchMedia('(max-width:640px)').matches ? 28 : 34;
  function frame() {
    requestAnimationFrame(frame);
    if (!T.cur.size) return;
    const cam = W.camera, cv = W.renderer && W.renderer.domElement; if (!cam || !cv) return;
    const r = cv.getBoundingClientRect(), now = Date.now(), on = gateOn();
    for (const [k, x] of T.cur) {
      if (!on || (!x.sticky && now - x.at > T.idleMs)) { T.clear(k); continue; }
      const o = x.c && x.c.object3D;
      if (!o || !o.visible || !o.parent) { x.el.style.display = 'none'; continue; }
      o.getWorldPosition(v); v.y += (x.c.height || 1.2) + (x.c.lift || 0) + 0.1;   // 頭頂；圖示再往上推 34px，放在名牌上方，不壓名牌
      v.project(cam);
      const vis = v.z < 1 && v.x > -1.1 && v.x < 1.1 && v.y > -1.1 && v.y < 1.1;
      x.el.style.display = vis ? '' : 'none';
      if (vis) x.el.style.transform = `translate(${(r.left + (v.x + 1) / 2 * r.width).toFixed(1)}px,${(r.top + (1 - v.y) / 2 * r.height - LIFT_PX).toFixed(1)}px)`;
    }
  }
  requestAnimationFrame(frame);
  return T;
}
