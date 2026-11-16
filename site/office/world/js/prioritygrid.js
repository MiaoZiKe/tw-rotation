// 優先度格子表（2026-11-16，第二批第 7 項；參考 Oxygen Not Included 的「優先度表」）。
// 一張表：橫軸是工作類型（寫程式、設計、研究、測試、文案、資料、部署、稽核、影音），縱軸是同事，每格 0～3：
//   0＝不派這類工作　1＝有空才派　2＝一般　3＝優先派。點一下格子加一，3 再點回 0。
// 預設值（沒動過的格子）依成長組的專長星數推出來：4～5 星＝3、2～3 星＝2、1 星或沒有這項專長＝1（預設不會有 0，不然沒人有的專長會一個人都派不出去；要排除某人得自己調成 0）；沒有成長系統時全部 1。只有被改過的格子才存起來。
// 跟成長組的自動派工對齊：W.growth.rank(skill) 存在就包住它——優先度 0 的人直接排除，其餘每 1 點優先度加 25 分（專長一顆星是 20 分，所以優先度會明顯影響、但不會完全蓋過專長與體力），
// 理由文字結尾補「優先度 N」。成長系統不存在或晚載入都沒關係（等它出現才接）。
// 存檔：aiOffice.game.prio.<範圍>（{ 同事代號: { 工作類型: 0～3 } }），重新整理還在，雲端存檔會一起帶走。
import { $, esc, jget, lsSet, scopeOf, GAME, whenWorld, members } from './workkit.js';

const KEY = GAME + 'prio.' + scopeOf();
const FALL = ['寫程式', '設計', '研究', '測試', '文案', '資料', '部署', '稽核', '影音'];
const LV = ['不派', '有空才派', '一般', '優先'];

export function createPriority(W) {
  const P = { key: KEY, skills: (W.growth && W.growth.SKILLS) || FALL };
  W.prio = P;
  let data = jget(KEY, {}); if (typeof data !== 'object' || Array.isArray(data)) data = {};
  const save = () => lsSet(KEY, JSON.stringify(data));
  const stars = (id, k) => { const g = W.growth && W.growth.get ? W.growth.get(id) : null; if (!g) return null; const s = g.skills.find(x => x.k === k); return s ? s.n : 0; };
  P.base = (id, k) => { const n = stars(id, k); return n == null ? 1 : n >= 4 ? 3 : n >= 2 ? 2 : 1; };
  P.get = (id, k) => { const v = data[id] && data[id][k]; return v == null ? P.base(id, k) : v; };
  P.isSet = (id, k) => !!(data[id] && data[id][k] != null);
  P.set = (id, k, v) => { v = Math.max(0, Math.min(3, v | 0)); (data[id] || (data[id] = {}))[k] = v; save(); render(); return v; };
  P.cycle = (id, k) => P.set(id, k, (P.get(id, k) + 1) % 4);
  P.reset = () => { data = {}; save(); render(); };

  // ───────── 面板 ─────────
  const el = document.createElement('aside'); el.className = 'panel'; el.id = 'prPanel'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', '優先度表'); el.hidden = true; ($('app') || document.body).append(el);
  const HELP = '優先度表：決定「依專長自動派工」會把哪類工作派給誰。每一格 0～3：0 不派、1 有空才派、2 一般、3 優先派。點一下格子加一，3 再點回 0。淡色的數字是系統依專長星數給的預設，你改過的格子會有橘色外框。真實專案裡這張表只影響「建議人選」，不會改 Claude 真實的派工。';
  function render() {
    if (el.hidden) return; const ms = members(W), ks = P.skills;
    const head = `<tr><th class="who">同事</th>${ks.map(k => `<th>${esc(k)}</th>`).join('')}</tr>`;
    const rows = ms.map(c => `<tr><th class="who"><b>${esc(c.spec.nick)}</b></th>${ks.map(k => { const v = P.get(c.spec.id, k), set = P.isSet(c.spec.id, k); return `<td><button class="pr-c v${v}${set ? ' set' : ''}" data-id="${esc(c.spec.id)}" data-k="${esc(k)}" data-v="${v}" aria-label="${esc(c.spec.nick)}　${esc(k)}　優先度 ${v}（${LV[v]}）">${v}</button></td>`; }).join('')}</tr>`).join('');
    el.innerHTML = `<button class="x" data-pr="x" aria-label="關閉">×</button><h3>優先度表<button class="gm-q" data-pr="q" aria-expanded="false" aria-label="優先度說明">?</button></h3>
      <div class="pr-help" hidden>${esc(HELP)}</div>
      <div class="pr-leg"><span><i class="v0"></i>0 不派</span><span><i class="v1"></i>1 有空才派</span><span><i class="v2"></i>2 一般</span><span><i class="v3"></i>3 優先</span></div>
      <div class="scroll pr-wrap">${ms.length ? `<table class="pr-t"><thead>${head}</thead><tbody>${rows}</tbody></table>` : '<p class="pr-none">目前辦公室沒有同事可以排優先度</p>'}</div>
      <div class="acts"><button class="btn" data-pr="reset">全部恢復預設</button></div>`;
  }
  P.open = () => { W.ui.closePops(); for (const id of ['bpPanel']) { const o = $(id); if (o) o.hidden = true; } el.hidden = false; render(); };
  P.close = () => { el.hidden = true; };
  el.addEventListener('click', e => {
    const c = e.target.closest('.pr-c'); if (c) { P.cycle(c.dataset.id, c.dataset.k); const b = el.querySelector(`.pr-c[data-id="${CSS.escape(c.dataset.id)}"][data-k="${CSS.escape(c.dataset.k)}"]`); if (b) b.focus(); return; }
    const a = e.target.closest('[data-pr]'); if (!a) return; const k = a.dataset.pr;
    if (k === 'x') P.close(); else if (k === 'reset') P.reset(); else if (k === 'q') { const h = el.querySelector('.pr-help'); h.hidden = !h.hidden; a.setAttribute('aria-expanded', !h.hidden); }
  });

  // ───────── 接上成長組的自動派工（存在才接） ─────────
  P.hooked = false;
  P.hook = () => {
    const G = W.growth; if (P.hooked || !G || typeof G.rank !== 'function') return false; P.hooked = true; const o = G.rank;
    G.rank = (skill, opt) => {
      const list = o(skill, opt), out = [];
      for (const r of list) { const p = P.get(r.id, skill); if (p <= 0) continue; r.score += p * 25; r.prio = p; r.why += `，優先度 ${p}`; out.push(r); }
      return out.sort((a, b) => b.score - a.score);
    };
    return true;
  };
  P.hook(); const t = setInterval(() => { if (P.hook()) clearInterval(t); }, 500); setTimeout(() => clearInterval(t), 120000);
  setInterval(() => { if (!el.hidden) { const sig = members(W).map(c => c.spec.id).join(); if (el.dataset.sig !== sig) { el.dataset.sig = sig; render(); } } }, 1000);
  return P;
}
whenWorld(W => { if (!W.prio) createPriority(W); });
