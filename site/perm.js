/* ============================================================================
   會員功能權限（前端套用）—— Andy 2026-10-02，DECISIONS #288
   ----------------------------------------------------------------------------
   做什麼：抓「我」的權限（未登入＝訪客方案；登入＝自己 email 那一份），把關掉的功能蓋上鎖頭與「此功能需開通」。
     · 功能清單在 site/features.js（每項的 veil／mark／block 選擇器）；後端是 workers/account-api 的 /v1/perm/me。
     · 不刪節點、不讓整頁消失：鎖頭畫在原本區塊的 ::after 上，內容模糊＋inert（點不到、Tab 走不進去），版面不跳。
     · 用屬性＋CSS 而不是插一個 <div> 進去：那些區塊大多會被各自的程式整個 innerHTML 重畫，插進去的節點會被沖掉；
       屬性掛在外框本身，重畫內容不影響。外框被整個換掉時，MutationObserver 下一個畫格補回來。
     · 一個都沒鎖（現在的預設：全部開啟）→ 不掛 MutationObserver、不攔點擊，對現有使用者零成本。

   ⚠ 誠實的限制（寫在 DECISIONS #288）：這是 GitHub Pages 靜態站，資料 JSON 是公開檔。
     鎖頭只擋一般使用者的畫面；懂技術的人直接讀 site/data/*.json 照樣拿得到。
     真正的付費內容保護，要讓那份資料改由 Worker 驗身分後才提供 —— 這次不做。

   對外：window.TwPerm
     can(id)            這個功能開著嗎（limit 類＝上限 > 0）
     limit(id, 備用值)   數量上限（例如 watch.tabs）
     state()            { who, plan, planName, feats, src }
     refresh()          重抓一次（登入、登出、管理者改了自己的權限之後）
     apply()            立刻重畫一次鎖頭
   事件：window 'tw:perm'（權限換了；watchpage 之類用來重畫上限）
   ============================================================================ */
(function () {
  'use strict';
  const F = window.TwFeatures;
  if (!F) return;
  const K_CACHE = 'tw.perm';
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const S = { who: 'guest', plan: '', planName: '', feats: {}, src: 'default', key: null, obs: null, raf: 0, seq: 0 };

  const acct = () => window.TwAccount || null;
  const meKey = () => { const A = acct(); const u = A && A.on() && A.user(); return u && u.email ? 'u:' + String(u.email).toLowerCase() : 'guest'; };

  function value(id) {
    const f = F.byId(id); if (!f) return true;
    const v = S.feats[id];
    if (f.kind === 'limit') return Number.isInteger(v) ? Math.max(0, Math.min(f.max, v)) : (v === false ? 0 : f.def);
    return typeof v === 'boolean' ? v : f.def;
  }
  function can(id) { const v = value(id); return typeof v === 'number' ? v > 0 : v !== false; }
  function limit(id, fb) { const f = F.byId(id); return f ? value(id) : fb; }
  const lockedList = () => F.list.filter((f) => f.kind !== 'limit' && !can(f.id));

  // ------------------------------------------------------------------ 樣式
  function css() {
    if (document.getElementById('permCss')) return;
    const s = document.createElement('style'); s.id = 'permCss';
    /* isolation:isolate —— 讓 ::after 的 z-index 只在這個區塊裡比，不會蓋到頁面上的下拉、抽屜（DECISIONS #278 同一個原則）*/
    s.textContent = `
[data-plk]{isolation:isolate;min-height:96px}
[data-plk][data-plk-rel]{position:relative}
[data-plk]>*{filter:blur(5px)!important;opacity:.28!important;pointer-events:none!important;user-select:none!important}
[data-plk]::after{content:attr(data-plk)!important;position:absolute!important;inset:0!important;z-index:30!important;display:flex!important;
  align-items:flex-start!important;justify-content:center!important;padding:22px 16px 0!important;box-sizing:border-box!important;
  white-space:pre-line!important;text-align:center!important;font:600 15px/1.6 system-ui,sans-serif!important;color:var(--ink,#e6edf6)!important;
  background:color-mix(in srgb,var(--panel,#111a2b) 45%,transparent)!important;border-radius:inherit!important;pointer-events:none!important;
  opacity:1!important;filter:none!important;width:auto!important;height:auto!important;transform:none!important}
[data-plkb]::after{content:" 🔒"!important;font-size:.85em!important;color:inherit!important;opacity:.9!important;margin-left:2px!important;vertical-align:0!important}
[data-plkb="block"]{opacity:.62}
.permtoast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:1500;background:var(--panel-3,#1c2638);color:var(--ink,#e6edf6);
  border:1px solid var(--line-2,#33415a);border-radius:10px;padding:10px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:calc(100vw - 32px)}
.permtoast[hidden]{display:none}`;
    document.head.appendChild(s);
  }
  function toast(msg) {
    let t = document.getElementById('permToast');
    if (!t) { t = document.createElement('div'); t.id = 'permToast'; t.className = 'permtoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3200);
  }
  function msgOf(f) {
    const tail = S.who === 'guest' && acct() && acct().on() ? '登入會員或洽網站管理者開通' : '請洽網站管理者開通';
    return `🔒 此功能需開通\n${f.name}・${tail}`;
  }

  // ------------------------------------------------------------------ 套用鎖頭
  const q = (sel) => { try { return Array.from(document.querySelectorAll(sel)); } catch (e) { return []; } };
  function apply() {
    S.raf = 0;
    css();
    const want = new Map(), wantB = new Map();
    for (const f of lockedList()) {
      for (const [sel, when] of f.veil || []) {
        if (when && !q(when).length) continue;
        q(sel).forEach((el) => { if (!want.has(el)) want.set(el, msgOf(f)); });
      }
      (f.mark || []).forEach((sel) => q(sel).forEach((el) => { if (!wantB.has(el)) wantB.set(el, 'mark'); }));
      (f.block || []).forEach((sel) => q(sel).forEach((el) => wantB.set(el, 'block')));
    }
    /* 只動「該變」的：屬性沒變就不寫（寫屬性會觸發樣式重算；live.js 每 5 秒改一堆格子，這裡每次都會被叫到）*/
    q('[data-plk]').forEach((el) => { if (!want.has(el)) { el.removeAttribute('data-plk'); el.removeAttribute('data-plk-rel'); el.inert = false; el.removeAttribute('aria-label'); } });
    want.forEach((m, el) => {
      if (el.getAttribute('data-plk') !== m) {
        el.setAttribute('data-plk', m);
        if (getComputedStyle(el).position === 'static') el.setAttribute('data-plk-rel', '');
        el.inert = true;
        el.setAttribute('aria-label', m.replace('\n', '：'));
      }
    });
    q('[data-plkb]').forEach((el) => { if (!wantB.has(el)) { el.removeAttribute('data-plkb'); if (el.dataset.plkTitle != null) { el.title = el.dataset.plkTitle; delete el.dataset.plkTitle; } } });
    wantB.forEach((k, el) => {
      if (el.getAttribute('data-plkb') !== k) {
        el.setAttribute('data-plkb', k);
        if (el.dataset.plkTitle == null) el.dataset.plkTitle = el.title || '';
        el.title = '此功能需開通';
      }
    });
    watch(want.size + wantB.size > 0 || lockedList().length > 0);
  }
  function schedule() { if (!S.raf) S.raf = requestAnimationFrame(apply); }
  function watch(on) {
    if (on && !S.obs && window.MutationObserver) {
      S.obs = new MutationObserver(schedule);
      S.obs.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'data-tab', 'hidden'] });
    } else if (!on && S.obs) { S.obs.disconnect(); S.obs = null; }
  }
  /* 「按了不會動作」的鈕：捕獲階段攔下來（比各自的 onclick 早），不必改那幾支別人正在改的檔案 */
  document.addEventListener('click', (e) => {
    const b = e.target && e.target.closest && e.target.closest('[data-plkb="block"]');
    if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const f = lockedList().find((x) => (x.block || []).some((s) => { try { return b.matches(s); } catch (er) { return false; } }));
    toast('🔒 此功能需開通' + (f ? '：' + f.name : ''));
  }, true);

  // ------------------------------------------------------------------ 讀取
  function set(d, src) {
    const before = JSON.stringify([S.who, S.plan, S.feats]);
    S.who = d.who || 'guest'; S.plan = d.plan || ''; S.planName = d.planName || '';
    S.feats = d.feats && typeof d.feats === 'object' ? d.feats : {};
    S.src = src;
    apply();
    if (before !== JSON.stringify([S.who, S.plan, S.feats])) window.dispatchEvent(new CustomEvent('tw:perm', { detail: state() }));
  }
  function state() { return { who: S.who, plan: S.plan, planName: S.planName, feats: Object.assign({}, S.feats), src: S.src }; }
  async function refresh() {
    const A = acct();
    const key = meKey();
    /* 會員功能沒設定（線上目前的狀態：account_config.js 是空的）→ 不連任何地方，全部照預設（＝全開）*/
    if (!A || !A.on()) { ls.del(K_CACHE); set({ who: 'guest', feats: {} }, 'default'); return; }
    const seq = ++S.seq; S.reqKey = key;
    const j = await A.call('/v1/perm/me', {});
    if (seq !== S.seq) return;                      // 期間又登入／登出過：以最新那次為準
    if (j && j._s === 200 && j.feats) {
      ls.set(K_CACHE, JSON.stringify({ k: key, who: j.who, plan: j.plan, planName: j.planName, feats: j.feats }));
      set(j, 'server');
    } else if (j && j._s === 401) {
      /* account.js 已經把權杖清掉、改回訪客；tw:account 事件會再叫一次 refresh */
    } else if (S.key !== key) {
      /* 連不到（公司網路、Worker 還沒更新成有這支 API 的版本）：沒有這個人的快取就全開 —— 寧可多給，不要誤鎖 */
      set({ who: key === 'guest' ? 'guest' : 'member', feats: {} }, 'default');
    }
    S.key = key;
  }
  /* 先用上次存的（同一個人才用）把鎖頭立刻掛上，避免重新整理時「先看到內容、一秒後才上鎖」 */
  function fromCache() {
    try {
      const c = JSON.parse(ls.get(K_CACHE) || 'null');
      if (c && c.k === meKey() && c.feats) { S.key = c.k; set(c, 'cache'); return true; }
    } catch (e) { /* 壞掉的快取當沒有 */ }
    return false;
  }

  window.TwPerm = { can, limit, value, state, refresh, apply: () => apply(), locked: () => lockedList().map((f) => f.id) };

  /* 啟動：account.js 先跑（它決定會員功能開不開），開了會發 tw:account-config；沒開就照預設全開。
     account.js 啟動時驗權杖也會發一次 tw:account —— 同一個人 5 秒內不重抓（不然每次重新整理都打兩次）。*/
  let started = false;
  function start() { if (started) return; started = true; fromCache(); S.at = Date.now(); refresh(); }
  function boot() { if (window.TW_ACCOUNT_ON) start(); else if (!started) refresh(); }
  window.addEventListener('tw:account', () => {
    if (meKey() === S.reqKey && Date.now() - (S.at || 0) < 5000) return;
    S.at = Date.now(); refresh();
  });
  window.addEventListener('tw:account-config', start);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
