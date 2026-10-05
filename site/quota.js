/* ============================================================================
   每日瀏覽次數 —— admin-v3（2026-10-05）改寫：**每個功能**都可以設上限（蓋掉 sub-v1 只有三個 quota.* 的做法）
   ----------------------------------------------------------------------------
   Andy：「每個功能後面加『瀏覽次數』上限欄位（每日次數，留空或『不限』，0＝不能看）」，
         「超過上限蓋『今日已用完，升級方案』並可點去 #pricing」。

   上限從哪來：/v1/perm/me 的 lims（範本的 plans.lims；perm.js 存在 TwPerm.lim(功能鍵)）。
     · Infinity（沒設）＝不限 → 這支什麼都不做（上線預設，零成本：沒有任何上限時不掛 MutationObserver）
     · 0 ＝不能看 → 交給 perm.js（跟關掉開關同一個鎖頭＋「升級查看」鈕），這裡不重複蓋
     · N ＝每日 N 次 → 這裡計數

   怎麼算「一次」：
     · 「一天」＝台北日期（一律 UTC+8 算）。
     · 有對象的頁面算「看了幾個不同的」：個股頁＝代號、題材剖析＝題材、族群頁＝族群 —— 同一個一天內重複看不重算。
     · 沒有對象的頁面（總覽、資金流向…）＝「這個瀏覽器分頁、這一頁」算一次：同一個分頁來回切不重算，新開一個分頁才算下一次。
     · 只有功能的區塊**真的在畫面上**（getClientRects 有東西）才算 —— 隱藏的 view 不吃額度。
     · 存在 localStorage（tw.quota）；登入者另外送 Worker（/v1/quota/hit，鍵＝功能鍵），伺服器回今天看過哪些，兩邊取聯集。
   用完時：該區塊模糊＋蓋一層「今日已用完 N/N 次」＋「升級查看」鈕（→ #pricing/need/<功能鍵>）。
     · 用自己的屬性 data-qlk（不用 perm.js 的 data-plk）：perm.js 每次重畫會把「不是它掛的」data-plk 拔掉。
     · 遮罩是插在區塊裡的一個節點（要能點按鈕，::after 點不到）；區塊被整個重畫時，MutationObserver 補回來。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const K = 'tw.quota';
  const tpeDay = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
  /* 這個瀏覽器分頁的代號（sessionStorage）：沒有對象的頁面用它當 key —— 同一個分頁重複看不重算 */
  let TAB = null;
  try { TAB = sessionStorage.getItem('tw.quota.tab'); } catch (e) { TAB = null; }
  if (!TAB) { TAB = Math.random().toString(36).slice(2, 8); try { sessionStorage.setItem('tw.quota.tab', TAB); } catch (e) { /* 私密視窗 */ } }
  function safeKey(s) {
    if (/^[0-9A-Za-z_.-]{1,24}$/.test(s)) return s;
    let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return 'x' + h.toString(16);
  }
  /* 這一頁的 key：有對象的回對象；沒有的回「頁名.分頁代號」 */
  function pageKey(h) {
    let m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h); if (m) return m[1].toUpperCase();
    m = /^#heatmap\/theme\/([^/?]+)/.exec(h); if (m) return safeKey('t.' + decodeURIComponent(m[1]));
    m = /^#industry\/group\/([^/?]+)/.exec(h); if (m) return safeKey('g.' + decodeURIComponent(m[1]));
    const head = (h.replace(/^#/, '').split(/[/?]/)[0] || 'overview').replace(/[^0-9A-Za-z_-]/g, '').slice(0, 14) || 'p';
    return head + '.' + TAB;
  }
  function load() {
    let d = null; try { d = JSON.parse((T() && T().ls.get(K)) || 'null'); } catch (e) { d = null; }
    if (!d || d.day !== tpeDay() || typeof d.k !== 'object') d = { day: tpeDay(), k: {} };
    return d;
  }
  const save = (d) => { if (T()) T().ls.set(K, JSON.stringify(d)); };
  const P = () => window.TwPerm || null;
  const F = () => window.TwFeatures || null;
  function limitOf(id) { const p = P(); return p && p.lim ? p.lim(id) : Infinity; }
  /* 有設「每日 N 次（N≥1）」而且開關是開的功能（開關關了／上限 0 由 perm.js 鎖）*/
  function limited() {
    const Ft = F(), p = P(); if (!Ft || !p) return [];
    const st = p.state(); const ks = Object.keys(st.lims || {});
    return ks.map((k) => Ft.byId(k)).filter((f) => f && f.kind !== 'limit' && limitOf(f.id) >= 1 && limitOf(f.id) !== Infinity && p.can(f.id));
  }
  const vis = (el) => el.getClientRects().length > 0;
  const q = (sel) => { try { return Array.from(document.querySelectorAll(sel)); } catch (e) { return []; } };
  /* 這個功能在目前畫面上蓋得到的區塊（跟 perm.js 同一套 veil 規則：條件選擇器、route；族群走族群頁）*/
  function targets(f, h) {
    if (f.route && !f.route.test(h)) return [];
    if (f.cat === 'grp') {
      const m = /^#industry\/group\/([^/?]+)/.exec(h);
      return m && decodeURIComponent(m[1]) === f.gid ? q('#gpSec').filter(vis) : [];
    }
    const out = [];
    for (const [sel, when] of f.veil || []) {
      if (when && !q(when).length) continue;
      q(sel).forEach((el) => { if (vis(el) && !out.includes(el)) out.push(el); });
    }
    return out;
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
  /* 登入（或換人）時把有上限的功能都問一次伺服器：今天在別台裝置看過的也要算進來 */
  let syncedFor = '';
  function sync() {
    const A = window.TwAccount, u = A && A.on() && A.user();
    const who = u ? u.email : '';
    if (!who || who === syncedFor) return;
    syncedFor = who;
    const d = load();
    limited().slice(0, 30).forEach((f) => {
      const ks = (d.k[f.id] || []).slice(0, 50);
      if (ks.length) ks.forEach((k) => hit(f.id, k)); else hit(f.id, null);
    });
  }

  // ------------------------------------------------------------------ 判定＋遮罩
  const S = { obs: null, raf: 0 };
  function evaluate() {
    S.raf = 0;
    const h = location.hash || '';
    const fs = limited();
    const d = load(); let changed = false;
    const want = new Map();
    if (!h.startsWith('#admin') && !h.startsWith('#pricing')) {
      const key = pageKey(h);
      for (const f of fs) {
        const els = targets(f, h); if (!els.length) continue;
        const lim = limitOf(f.id);
        const set = new Set(d.k[f.id] || []);
        if (set.has(key)) continue;
        if (set.size < lim) { set.add(key); d.k[f.id] = [...set]; changed = true; hit(f.id, key); continue; }
        els.forEach((el) => { if (!want.has(el)) want.set(el, { msg: `今日已用完 ${set.size}/${lim} 次`, f, lim }); });
      }
    }
    if (changed) save(d);
    paint(want);
    watch(fs.length > 0);
  }
  function paint(want) {
    css();
    document.querySelectorAll('[data-qlk]').forEach((el) => { if (!want.has(el)) { el.removeAttribute('data-qlk'); const o = el.querySelector(':scope > .qlkov'); if (o) o.remove(); } });
    want.forEach((w, el) => {
      if (el.getAttribute('data-qlk') !== w.msg) el.setAttribute('data-qlk', w.msg);
      let o = el.querySelector(':scope > .qlkov');
      if (!o) { o = document.createElement('div'); o.className = 'qlkov'; o.setAttribute('role', 'alert'); el.appendChild(o); }
      const html = `<b>${T().esc(w.msg)}</b><span>${T().esc(w.f.name)}・升級方案可增加每日次數，明天（台北時間 0 點）自動恢復</span><a href="#pricing/need/${encodeURIComponent(w.f.id)}" class="qlkgo">升級查看 →</a>`;
      if (o.dataset.h !== html) { o.innerHTML = html; o.dataset.h = html; }
    });
  }
  /* 節流 200ms：有上限時要觀察整個 body，live.js 每幾秒改一堆格子 —— 不必每一格變動都重算 */
  function schedule() { if (!S.raf) S.raf = setTimeout(evaluate, 200); }
  /* 有上限才觀察 DOM：區塊晚一點才畫出來（個股頁、族群頁都是非同步）也要算到；遮罩被重畫沖掉時補回來 */
  function watch(on) {
    if (on && !S.obs && window.MutationObserver) { S.obs = new MutationObserver(schedule); S.obs.observe(document.body, { subtree: true, childList: true }); }
    else if (!on && S.obs) { S.obs.disconnect(); S.obs = null; }
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
.qlkov .qlkgo{margin-top:6px;display:inline-flex;align-items:center;height:36px;padding:0 18px;border-radius:999px;background:var(--amber,#f5b942);color:#1a1203;font-weight:700;font-size:14px;text-decoration:none}`);
  }

  window.addEventListener('hashchange', schedule);
  window.addEventListener('tw:perm', () => { syncedFor = ''; sync(); schedule(); });
  window.addEventListener('tw:account', () => { sync(); schedule(); });
  function boot() { schedule(); sync(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  window.TwQuota = { state: () => load(), limit: limitOf, evaluate: () => evaluate(), day: tpeDay, pageKey };
})();
