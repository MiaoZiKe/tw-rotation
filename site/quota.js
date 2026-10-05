/* ============================================================================
   每日瀏覽次數（sub-v1，2026-10-05）—— features.js 的「瀏覽次數」分類（quota.*）
   ----------------------------------------------------------------------------
   Andy：功能開關新增「瀏覽次數」，例如個股頁每日次數、AI 分析每日次數、題材剖析圖每日次數。

   怎麼算：
     · 「一天」＝台北日期（容器與使用者電腦可能不是台北時區，一律 UTC+8 算）。
     · 算的是「看了幾個不同的」：同一檔個股、同一個題材一天內重複看不重算 —— 來回切頁不該把額度吃光。
     · 存在 localStorage（tw.quota）；登入者另外送 Worker（/v1/quota/hit），伺服器回今天看過哪些，
       兩邊取聯集 —— 清快取、換瀏覽器都繞不過（訪客只有本機計數，這是刻意的取捨：訪客本來就能清快取重來）。
     · 上限值：99（max）＝不限、0＝不能用、1～98＝每日 N 個（理由寫在 features.js 那一段）。預設 99 ＝ 上線不影響任何人。
   用完時：該區塊模糊＋蓋一層「今日已用完 N/N 次，升級方案可增加」＋「查看方案」鈕（→ #pricing）。
     · 用自己的屬性 data-qlk（不用 perm.js 的 data-plk）：perm.js 每次重畫會把「不是它掛的」data-plk 拔掉。
     · 遮罩是插在區塊裡的一個節點（要能點「查看方案」，::after 點不到）；區塊被整個重畫時，MutationObserver 補回來。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const K = 'tw.quota';
  const tpeDay = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
  const RULES = [
    /* [功能鍵, 這一頁是不是它、回傳 key（null＝不是）, 要蓋的區塊] */
    { id: 'quota.stock', key: (h) => { const m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h); return m ? m[1].toUpperCase() : null; }, sel: ['#v-industry'] },
    { id: 'quota.ai', key: (h) => { const m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h); return m ? m[1].toUpperCase() : null; }, sel: ['#skAi', '#ovAiCard', '#aiCard'] },
    { id: 'quota.theme', key: (h) => { const m = /^#heatmap\/theme\/([^/?]+)/.exec(h); return m ? safeKey(decodeURIComponent(m[1])) : null; }, sel: ['#themeDetail'] },
  ];
  function safeKey(s) {
    if (/^[0-9A-Za-z_.-]{1,24}$/.test(s)) return s;
    let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return 'x' + h.toString(16);
  }
  function load() {
    let d = null; try { d = JSON.parse((T() && T().ls.get(K)) || 'null'); } catch (e) { d = null; }
    if (!d || d.day !== tpeDay() || typeof d.k !== 'object') d = { day: tpeDay(), k: {} };
    return d;
  }
  const save = (d) => { if (T()) T().ls.set(K, JSON.stringify(d)); };
  function limitOf(id) {
    const F = window.TwFeatures, P = window.TwPerm;
    const f = F && F.byId(id); if (!f) return Infinity;
    const v = P ? P.value(id) : f.def;
    return v >= f.max ? Infinity : Math.max(0, v | 0);
  }
  const loggedIn = () => { const A = window.TwAccount; return !!(A && A.on() && A.user()); };

  /* 伺服器同步：登入者每看一個新的就送一次；回來的 keys 併進本機 */
  async function hit(id, key) {
    if (!loggedIn() || !T()) return;
    const j = await T().call('/v1/quota/hit', key ? { k: id, key } : { k: id });
    if (j && j._s === 200 && Array.isArray(j.keys)) {
      const d = load(); const set = new Set(d.k[id] || []); let grew = false;
      j.keys.forEach((x) => { if (!set.has(x)) { set.add(x); grew = true; } });
      if (grew) { d.k[id] = [...set]; save(d); schedule(); }
    }
  }
  /* 登入（或換人）時把三項都問一次伺服器：今天在別台裝置看過的也要算進來 */
  let syncedFor = '';
  function sync() {
    const A = window.TwAccount, u = A && A.on() && A.user();
    const who = u ? u.email : '';
    if (!who || who === syncedFor) return;
    syncedFor = who;
    /* 本機今天已經記下、但當時還沒確認登入（/v1/me 還沒回來）的，補送給伺服器；沒有就只查 */
    const d = load();
    RULES.forEach((r) => {
      if (limitOf(r.id) === Infinity) return;
      const ks = (d.k[r.id] || []).slice(0, 50);
      if (ks.length) ks.forEach((k) => hit(r.id, k)); else hit(r.id, null);
    });
  }

  // ------------------------------------------------------------------ 判定＋遮罩
  const S = { blocked: new Map(), obs: null, raf: 0 };     // 元素 → 訊息
  function evaluate() {
    S.raf = 0;
    const h = location.hash || '';
    const d = load(); let changed = false;
    const want = new Map();
    for (const r of RULES) {
      const key = r.key(h); if (!key) continue;
      const lim = limitOf(r.id); if (lim === Infinity) continue;
      const set = new Set(d.k[r.id] || []);
      if (set.has(key)) continue;
      if (set.size < lim) { set.add(key); d.k[r.id] = [...set]; changed = true; hit(r.id, key); continue; }
      const f = window.TwFeatures.byId(r.id);
      const msg = lim === 0 ? `${f.name}：目前方案不開放` : `今日已用完 ${set.size}/${lim} 次`;
      r.sel.forEach((s) => document.querySelectorAll(s).forEach((el) => { if (!want.has(el)) want.set(el, { msg, f, lim }); }));
    }
    if (changed) save(d);
    paint(want);
  }
  function paint(want) {
    css();
    document.querySelectorAll('[data-qlk]').forEach((el) => { if (!want.has(el)) { el.removeAttribute('data-qlk'); el.inert = false; const o = el.querySelector(':scope > .qlkov'); if (o) o.remove(); } });
    want.forEach((w, el) => {
      if (el.getAttribute('data-qlk') !== w.msg) el.setAttribute('data-qlk', w.msg);
      let o = el.querySelector(':scope > .qlkov');
      if (!o) {
        o = document.createElement('div'); o.className = 'qlkov'; o.setAttribute('role', 'alert');
        el.appendChild(o);
      }
      const html = `<b>${T().esc(w.msg)}</b><span>${T().esc(w.f.name)}・${w.lim === 0 ? '升級方案即可使用' : '升級方案可增加每日次數，明天（台北時間 0 點）自動恢復'}</span><a href="#pricing" class="qlkgo">查看方案</a>`;
      if (o.dataset.h !== html) { o.innerHTML = html; o.dataset.h = html; }
    });
    watch(want.size > 0);
  }
  function schedule() { if (!S.raf) S.raf = requestAnimationFrame(evaluate); }
  function watch(on) {
    if (on && !S.obs) { S.obs = new MutationObserver(() => { if (!S.raf) S.raf = requestAnimationFrame(reapply); }); S.obs.observe(document.body, { subtree: true, childList: true }); }
    else if (!on && S.obs) { S.obs.disconnect(); S.obs = null; }
  }
  /* 區塊被重畫（遮罩節點被沖掉）時只補遮罩，不重新計數 */
  function reapply() {
    S.raf = 0;
    const lost = [...document.querySelectorAll('[data-qlk]')].some((el) => !el.querySelector(':scope > .qlkov'));
    const h = location.hash || '';
    const need = RULES.some((r) => r.key(h) && r.sel.some((s) => { const el = document.querySelector(s); return el && !el.hasAttribute('data-qlk'); }));
    if (lost || need) evaluate();
  }
  function css() {
    if (!T()) return;
    T().css('quotaCss', `
[data-qlk]{position:relative;isolation:isolate;min-height:160px}
[data-qlk]>*:not(.qlkov){filter:blur(6px)!important;opacity:.25!important;pointer-events:none!important;user-select:none!important}
.qlkov{position:absolute;inset:0;z-index:40;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:8px;padding:48px 16px 0;text-align:center;
  background:color-mix(in srgb,var(--panel,#111a2b) 55%,transparent);border-radius:inherit}
.qlkov b{font-size:18px;color:var(--ink)}
.qlkov span{font-size:13.5px;color:var(--ink-2);max-width:420px;line-height:1.6}
.qlkov .qlkgo{margin-top:6px;display:inline-flex;align-items:center;height:36px;padding:0 18px;border-radius:10px;background:var(--cyan);color:#04121a;font-weight:700;font-size:14px;text-decoration:none}`);
  }

  // ------------------------------------------------------------------ 管理頁：把上限下拉的字換成「次」（admin.js 一律寫「頁」）
  /* 不改 admin.js（另一條分支正在改它）：在管理頁打開時，把 quota.* 下拉的選項文字換掉。數值不動，只換字。*/
  function relabel() {
    if (!(location.hash || '').startsWith('#admin')) return;
    const F = window.TwFeatures; if (!F) return;
    document.querySelectorAll('select[data-f^="quota."]').forEach((sel) => {
      if (sel.dataset.qlbl === '1' && sel.options.length && sel.options[sel.options.length - 1].text === '不限') return;
      const f = F.byId(sel.dataset.f); if (!f) return;
      [...sel.options].forEach((o) => { const v = +o.value; o.text = v >= f.max ? '不限' : v === 0 ? '不能用' : `每日 ${v} ${f.unit || '次'}`; });
      sel.dataset.qlbl = '1';
    });
  }
  let admObs = null;
  function admWatch() {
    const on = (location.hash || '').startsWith('#admin');
    if (on && !admObs) { admObs = new MutationObserver(relabel); admObs.observe(document.body, { subtree: true, childList: true }); relabel(); }
    else if (!on && admObs) { admObs.disconnect(); admObs = null; }
  }

  window.addEventListener('hashchange', () => { schedule(); admWatch(); });
  window.addEventListener('tw:perm', () => { syncedFor = ''; sync(); schedule(); });
  window.addEventListener('tw:account', () => { sync(); schedule(); });
  function boot() { schedule(); admWatch(); sync(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.TwQuota = { state: () => load(), limit: limitOf, evaluate: () => evaluate(), day: tpeDay };
})();
