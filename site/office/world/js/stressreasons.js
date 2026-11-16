// 壓力原因看得懂（2026-11-16，第二批第 8 項；參考 RimWorld「心情＝一串有過期時間的想法」）。
// 資訊卡的壓力旁多一塊「壓力原因」：連續被退件 3 次、熬夜加班、被燒到、被稱讚…，每條有剩餘時間，快到期就淡出，到期就消失；壓力數字漸變、不瞬跳。
//
// 跟成長組（growth.js／growth_ui.js）怎麼對齊（先讀過他們的程式才寫的）：
//   · 壓力數值只讀 W.growth.get(id).str（0～100，體力／壓力的唯一來源，growth.js 也會把它寫回 mind.js 的 m.stress）；沒有成長系統時退回 W.mind.get(id).mood.stress。
//   · 事件與數字跟 growth.js 的 bump 一樣：rejected +10、knocked +6、burned +12、praised −6、rewarded −10、comforted −8（這裡只「說明」，不另外改數值，所以不會重複加壓力）。
//   · 資訊卡：包住 ui.showCard，卡畫好後把自己的區塊放在成長區塊（#gmCard）後面；沒有成長區塊就放在心情列後面（存在才接，順序不管誰先載入都對）。
// 原因存 localStorage（aiOffice.game.stresswhy.<範圍>），用真實時間算剩餘，重新整理後還在、過期的自動不見。
import { $, esc, jget, lsSet, scopeOf, GAME, whenWorld, members } from './workkit.js';
import { taipeiNow } from './daytime.js';

const KEY = GAME + 'stresswhy.' + scopeOf();
const MIN = 60e3;
// 每一種原因：文字、壓力變化（顯示用，跟 growth.js 的 bump 同數字）、多久過期、是好是壞
const KIND = {
  rejected: { ttl: 20 * MIN, bad: true }, knocked: { text: '被丟出去或被撞到', d: 6, ttl: 8 * MIN, bad: true }, burned: { text: '被燒到', d: 12, ttl: 15 * MIN, bad: true },
  praised: { text: '被稱讚了', d: -6, ttl: 10 * MIN }, rewarded: { text: '得到獎勵', d: -10, ttl: 12 * MIN }, comforted: { text: '被同事安慰', d: -8, ttl: 10 * MIN },
  night: { text: '熬夜加班', ttl: 30 * MIN, bad: true, note: '壓力累積變快' }, long: { ttl: 3 * MIN, bad: true, note: '壓力持續上升' }, low: { text: '體力快見底', ttl: 2 * MIN, bad: true, note: '做事變慢' },
  rest: { ttl: 2 * MIN, note: '壓力下降中' },
};

export function createStressWhy(W) {
  const S = { key: KEY, shown: new Map() };
  W.stressWhy = S;
  let data = jget(KEY, {}); if (typeof data !== 'object' || Array.isArray(data)) data = {};
  const save = () => lsSet(KEY, JSON.stringify(data));
  const prune = () => { const now = Date.now(); let ch = false; for (const id of Object.keys(data)) { const a = data[id].filter(r => r.at + r.ttl > now); if (a.length !== data[id].length) ch = true; if (a.length) data[id] = a; else delete data[id]; } if (ch) save(); };
  const rej = new Map();    // 連續被退件次數：被稱讚／獎勵／安慰就歸零

  // 新增或刷新一條原因（同一個 k 只留一條；刷新就重新計時）
  S.add = (id, k, o = {}) => {
    const kd = KIND[k] || {}, ttl = o.ttl || kd.ttl || 5 * MIN, list = data[id] || (data[id] = []);
    const r = { k, text: o.text || kd.text || k, d: o.d != null ? o.d : kd.d, note: o.note || kd.note || '', bad: o.bad != null ? !!o.bad : !!kd.bad, at: Date.now(), ttl };
    const i = list.findIndex(x => x.k === k); if (i >= 0) list[i] = r; else list.push(r);
    if (list.length > 8) list.shift(); save(); return r;
  };
  S.drop = (id, k) => { if (data[id]) { data[id] = data[id].filter(r => r.k !== k); if (!data[id].length) delete data[id]; save(); } };
  S.list = id => { prune(); const now = Date.now(); return (data[id] || []).map(r => ({ ...r, left: r.at + r.ttl - now, frac: (r.at + r.ttl - now) / r.ttl })).sort((a, b) => (b.bad - a.bad) || b.left - a.left); };
  S.clear = () => { data = {}; rej.clear(); save(); };

  // ───────── 壓力數字（漸變）：目標讀成長系統，顯示值每 0.4 秒最多走 3（約每秒 7.5），不瞬跳 ─────────
  const target = id => { const g = W.growth && W.growth.get ? W.growth.get(id) : null; if (g) return g.str; const m = W.mind && W.mind.get ? W.mind.get(id) : null; return m ? Math.round(m.mood.stress * 100) : 0; };
  S.target = target;
  S.value = id => { const t = target(id); let v = S.shown.has(id) ? S.shown.get(id) : t; v += Math.max(-3, Math.min(3, t - v)); S.shown.set(id, v); return v; };

  // ───────── 事件 → 原因 ─────────
  // 事件匯流排有兩種長相：phys.js 的處理函式只收一個事件物件 { type, id, … }，mind.js 的收 (代號, 附加欄位)——兩種都吃（跟 chat.js 同一個做法）
  const on = (n, fn) => { if (W.on) W.on(n, (a, b) => { try { if (a && typeof a === 'object') fn(a.id, a); else fn(a, b || {}); } catch (e) { console.warn('壓力原因事件例外', e); } }); };
  on('rejected', id => { const n = (rej.get(id) || 0) + 1; rej.set(id, n); S.add(id, 'rejected', { text: n >= 2 ? `連續被退件 ${n} 次` : '被退件了一次', d: Math.min(30, 10 * n), n }); });
  const relief = (k, id) => { rej.set(id, 0); S.drop(id, 'rejected'); S.add(id, k); };
  on('praised', id => relief('praised', id)); on('rewarded', id => relief('rewarded', id)); on('comforted', id => relief('comforted', id));
  on('knocked', id => S.add(id, 'knocked')); on('burned', id => S.add(id, 'burned'));

  // ───────── 每秒看一次：熬夜、連續工作、體力見底、休息中 ─────────
  const since = new Map();
  setInterval(() => {
    if (document.visibilityState === 'hidden') return;
    const hr = taipeiNow().h, late = hr >= 22 || hr < 5, now = Date.now();
    for (const c of members(W)) {
      const id = c.spec.id, g = W.growth && W.growth.get ? W.growth.get(id) : null, a = W.state && W.state.agents ? W.state.agents.get(id) : null, w = g ? g.working : !!(a && a.phase !== 'idle');
      if (w) {
        if (!since.has(id)) since.set(id, now);
        if (late) S.add(id, 'night');
        const mins = Math.floor((now - since.get(id)) / MIN); if (mins >= 1) S.add(id, 'long', { text: `已連續工作 ${mins} 分鐘` });
      } else since.delete(id);
      if (g && g.sta < 25) S.add(id, 'low');
      if (g && g.resting) S.add(id, 'rest', { text: `正在休息（${g.restZh}）` });
    }
  }, 1000);

  // ───────── 資訊卡 ─────────
  const left = ms => ms >= MIN ? `剩 ${Math.ceil(ms / MIN)} 分鐘` : `剩 ${Math.max(1, Math.ceil(ms / 1000))} 秒`;
  const HELP = '壓力原因：這位同事現在為什麼有壓力（或為什麼在減壓）。每一條都有剩餘時間，時間到就消失；快到期時會變淡。紅色是加壓力的原因，綠色是減壓力的原因。壓力數字會慢慢跟著變，不會一下子跳動。';
  function html(id) {
    const v = Math.round(S.value(id)), rs = S.list(id);
    const li = rs.length ? rs.map(r => `<li class="${r.bad ? 'bad' : 'good'}" data-k="${esc(r.k)}" style="opacity:${Math.max(.3, Math.min(1, r.frac * 3)).toFixed(2)}"><span class="sr-t">${esc(r.text)}</span><em>${r.d != null ? (r.d > 0 ? '壓力 +' : '壓力 ') + r.d : esc(r.note)}</em><time>${left(r.left)}</time></li>`).join('')
      : '<li class="none">目前沒有特別的壓力原因</li>';
    return `<div class="sr-h"><b>壓力原因</b><span class="sr-v" data-k="srv">壓力 ${v}</span><button class="gm-q" data-srq aria-expanded="false" aria-label="壓力原因說明">?</button></div><ul class="sr-l">${li}</ul><div class="sr-help" hidden>${esc(HELP)}</div>`;
  }
  function refresh() {
    const root = $('srCard'); if (!root) return; const id = root.dataset.id, h = root.querySelector('.sr-help'), open = h && !h.hidden;
    const sig = S.list(id).map(r => r.k + r.text).join('|');
    if (root.dataset.sig !== sig) { root.dataset.sig = sig; root.innerHTML = html(id); const nh = root.querySelector('.sr-help'); if (nh && open) { nh.hidden = false; root.querySelector('[data-srq]').setAttribute('aria-expanded', 'true'); } return; }
    const sv = root.querySelector('[data-k="srv"]'); if (sv) sv.textContent = '壓力 ' + Math.round(S.value(id));
    for (const li of root.querySelectorAll('.sr-l li[data-k]')) { const r = S.list(id).find(x => x.k === li.dataset.k); if (r) { li.style.opacity = Math.max(.3, Math.min(1, r.frac * 3)).toFixed(2); const t = li.querySelector('time'); if (t) t.textContent = left(r.left); } }
  }
  S.refresh = refresh;
  function decorate(c) {
    if (!c || c.spec.pet || c.spec.isCeo || c.jobless) return; const card = $('card'); if (!card || card.querySelector('#srCard')) return;
    const anchor = card.querySelector('#gmCard') || card.querySelector('#cardMood') || card.querySelector('#cardNow'); if (!anchor) return;
    const id = c.spec.id; S.shown.set(id, target(id));       // 打開卡片時從目前的值開始，之後才漸變
    anchor.insertAdjacentHTML('afterend', `<div class="sr" id="srCard" data-id="${esc(id)}">${html(id)}</div>`); $('srCard').dataset.sig = S.list(id).map(r => r.k + r.text).join('|');
  }
  const ui = W.ui, origShow = ui.showCard; ui.showCard = c => { const r = origShow.call(ui, c); try { decorate(c); } catch (e) { console.error('壓力原因區塊失敗', e); } return r; };
  $('card').addEventListener('click', e => { const q = e.target.closest('[data-srq]'); if (!q) return; const h = $('card').querySelector('#srCard .sr-help'); if (h) { h.hidden = !h.hidden; q.setAttribute('aria-expanded', !h.hidden); } });
  setInterval(() => { if (!$('card').hidden) refresh(); }, 400);
  addEventListener('pagehide', save);
  return S;
}
whenWorld(W => { if (!W.stressWhy) createStressWhy(W); });
