/* 2026-11-16 追蹤解鎖（第 2 批：網站端；設計 docs/marketing/channels/follow_unlock_design.md）
   流程：IG 私訊送「#unlock/<解鎖碼>/<單篇文章 id>」→ 本檔把碼暫存、網址改成單篇（沒註冊的人只讀得到那一篇）
         → 登入後呼叫會員 Worker 兌換（POST /v1/unlock/redeem）→ 帳號累積「已解鎖頻道」→ 精選文章顯示對應頻道分頁。
   ★ 本批不改、不部署 workers/account-api：Worker 端點還沒上線（回 404／連不到）時：
       · 預覽網域（window.TW_PREVIEW）→ 走「預覽用的假兌換」：只認 pv-<頻道>（例 pv-tech、pv-healing-x1），只存這台裝置、跟帳號（uid）綁；
       · 正式網域 → 假兌換不生效（一律回「解鎖碼無效或功能尚未開通」），不會因此多出任何頻道。
   Worker 上線後只要它回 { unlocked:['tech',…] }（兌換回應與 /v1/me 的 user.unlocked 都可），本檔自動改吃真的，假兌換仍只在預覽生效。 */
(function () {
  'use strict';
  const CHS = ['tech', 'ligu', 'caffaine', 'healing'];
  const PEND = 'tw.unl.pend';           // sessionStorage：連結帶來、還沒兌換的碼
  const FAKE = 'tw.unl.pv.';            // localStorage（只預覽用）＋ uid
  const S = { srv: [], busy: false, msg: '' };
  const uidOf = () => { try { const u = window.TwAccount && TwAccount.user && TwAccount.user(); return u ? (u.uid || u.email || '') : ''; } catch (e) { return ''; } };
  const rd = (k) => { try { return JSON.parse(localStorage.getItem(k) || '[]') || []; } catch (e) { return []; } };
  /* 預覽網域＝index.html 有 TW_PREVIEW（preview_inject 只注入首頁），或網址在 /preview/<名稱>/ 底下（獨立閱讀站 site/c/ 沒有被注入）*/
  const isPv = () => !!window.TW_PREVIEW || /\/preview\/[^/]+\//.test(location.pathname);
  const fakeList = () => (isPv() && uidOf() ? rd(FAKE + uidOf()).filter((c) => CHS.includes(c)) : []);
  const srvList = () => {
    try { const u = window.TwAccount && TwAccount.user && TwAccount.user(); if (u && Array.isArray(u.unlocked)) return u.unlocked.filter((c) => CHS.includes(c)); } catch (e) { /* 沒登入 */ }
    return S.srv;
  };
  const list = () => Array.from(new Set(srvList().concat(fakeList())));
  const has = (ch) => list().includes(ch);
  const toast = (m) => {   // 沿用 account.js 的提示條外觀（.accttoast），自己建一個，不依賴它的內部函式
    try {
      let t = document.getElementById('unlToast');
      if (!t) { t = document.createElement('div'); t.id = 'unlToast'; t.className = 'accttoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
      t.textContent = m; t.style.display = 'block'; clearTimeout(t._h); t._h = setTimeout(() => { t.style.display = 'none'; }, 4000);
    } catch (e) { /* 忽略 */ }
  };

  /* 開站處理連結：#unlock/<碼>[/<文章 id>] → 暫存碼，網址換成單篇（或精選文章）*/
  function takeLink(live) {
    const m = (location.hash || '').match(/^#unlock\/([\w.~-]{3,200})(?:\/([^/?#]+))?/);
    if (!m) return;
    try { sessionStorage.setItem(PEND, m[1]); } catch (e) { /* 私密視窗：只在這次載入有效 */ window.__twUnlPend = m[1]; }
    const to = typeof window.TW_UNLOCK_ROUTE === 'function' ? window.TW_UNLOCK_ROUTE(m[2] || '') : (m[2] ? '#article/' + m[2] : '#articles');   // 獨立閱讀站（site/c/）自己決定落地路由
    try { history.replaceState(null, '', location.pathname + location.search + to); } catch (e) { location.hash = to; }
    if (live) { try { window.dispatchEvent(new HashChangeEvent('hashchange')); } catch (e) { /* 舊瀏覽器 */ } }   // 頁面已開著、只改了 # 的情況：換完網址要叫路由重走一次
  }
  const pend = () => { try { return sessionStorage.getItem(PEND) || ''; } catch (e) { return ''; } };
  const clearPend = () => { try { sessionStorage.removeItem(PEND); } catch (e) { /* 忽略 */ } window.__twUnlPend = ''; };

  async function redeem(code) {
    code = String(code || '').trim();
    if (!code || !/^[\w.~-]{3,200}$/.test(code)) return { ok: false, why: 'bad' };
    if (!uidOf()) return { ok: false, why: 'login' };
    let j = null;
    try { j = await TwAccount.call('/v1/unlock/redeem', { code }); } catch (e) { j = null; }
    if (j && j._s === 200 && Array.isArray(j.unlocked)) { S.srv = j.unlocked.filter((c) => CHS.includes(c)); return { ok: true, ch: j.channel || S.srv[S.srv.length - 1] || '', src: 'server' }; }
    if (j && j._s && j._s !== 404) return { ok: false, why: 'rejected' };   // Worker 有回但拒絕（碼錯、已用過、過期）
    /* Worker 未上線（404／連不到）：只有預覽網域有假兌換 */
    if (isPv()) {
      const m = /^pv-(tech|ligu|caffaine|healing)(?:-[\w]{1,24})?$/.exec(code);
      if (!m) return { ok: false, why: 'rejected' };
      const k = FAKE + uidOf(), cur = rd(k);
      if (!cur.includes(m[1])) { cur.push(m[1]); try { localStorage.setItem(k, JSON.stringify(cur)); } catch (e) { /* 忽略 */ } }
      return { ok: true, ch: m[1], src: 'preview' };
    }
    return { ok: false, why: 'off' };
  }
  const WHY = { bad: '解鎖碼格式不對', login: '請先登入再兌換', rejected: '解鎖碼無效、已用過或已過期', off: '解鎖功能尚未開通，稍後再試' };
  const NAME = { tech: '科技透明圈', ligu: '哩股哩股', caffaine: 'CaffAIne', healing: '談晴說礙' };

  /* 登入後有待兌換的碼就兌換一次，成功就帶去該頻道的全部文章 */
  async function flush(go) {
    const c = pend() || window.__twUnlPend || '';
    if (!c || S.busy || !uidOf()) return;
    S.busy = true;
    try {
      const r = await redeem(c);
      if (r.ok || r.why !== 'login') clearPend();
      S.msg = r.ok ? '' : (WHY[r.why] || '兌換失敗');
      toast(r.ok ? `已解鎖「${NAME[r.ch] || r.ch}」全部文章` : S.msg);
      window.dispatchEvent(new Event('tw:chunl'));
      if (r.ok && go !== false && r.ch && /^#article(s)?(\/|$)/.test(location.hash || '#articles')) {
        if ((location.hash || '').startsWith('#articles')) location.hash = '#articles/' + r.ch;
      }
    } finally { S.busy = false; }
  }
  takeLink(false);
  window.addEventListener('hashchange', () => { if (/^#unlock\//.test(location.hash || '')) { takeLink(true); flush(); } });
  window.addEventListener('tw:account', () => { flush(); window.dispatchEvent(new Event('tw:chunl')); });
  window.addEventListener('load', () => setTimeout(flush, 600));
  window.TwUnlock = { list, has, redeem, flush, pending: () => !!pend(), channels: CHS, msg: () => S.msg };
})();
