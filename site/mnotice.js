/* ============================================================================
   會員通知（2026-11-09）—— 站主發給你的體驗、方案升級、延長，登入時跳一個小視窗＋併進右上鈴鐺
   ----------------------------------------------------------------------------
   Andy 11-09：「你發放的那一刻，會員伺服器幫他記一則『你獲得了○○體驗，到期 ○/○』。需要新增 只要我有更動 給他多的福祿都要跳出」
     · 資料：Worker /v1/notices/mine（本人：未讀全部＋最近 20 則）、/v1/notices/seen（標已讀）。後端在 workers/account-api 的「會員通知區塊」。
     · 有未讀 → 跳一個小視窗（多則就列表），按「知道了」（或關掉）＝標已讀，之後不再跳；同時出現在鈴鐺清單（類型「會員權益」）。
     · 鈴鐺那邊點一則＝標已讀（notices.js 認得 m- 開頭的 id，交給這裡送 /v1/notices/seen）。
     · 舊後端沒有這個端點（404）或連不到 → 安靜略過，不跳、不報錯。
     · 不計次、不設功能鍵：這是站主對「這個人」的帳務／權益告知，每位會員都該看到（同 pay 帳務通知）。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  if (!T()) return;
  const { esc, css, call, dialog } = T();
  const A = () => window.TwAccount;
  const logged = () => { const a = A(); return !!(a && a.on() && a.user()); };
  const S = { list: [], who: '', fly: null, shown: new Set(), off: false };
  const who = () => { const a = A(), u = a && a.user ? a.user() : null; return u && u.email ? String(u.email) : ''; };
  const dstr = (ms) => new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, '/');

  css('mnCss', `
.mnbox h3{display:flex;align-items:center;gap:8px}
.mnbox .mnic{display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:color-mix(in srgb,var(--cyan) 18%,transparent);color:var(--cyan);flex:none}
.mnbox .mnic svg{width:16px;height:16px;display:block}
.mnbox ul{list-style:none;margin:10px 0 0;padding:0;display:flex;flex-direction:column;gap:8px;max-height:min(50vh,360px);overflow:auto}
.mnbox li{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.mnbox li b{display:block;font-size:var(--fs-body,14px);font-weight:600;color:var(--ink);line-height:1.45}
.mnbox li span{display:block;font-size:var(--fs-sm,13px);color:var(--ink-2);line-height:1.6;margin-top:2px}
.mnbox li i{display:block;font-style:normal;font-size:var(--fs-min,12px);color:var(--ink-3,var(--ink-2));margin-top:4px;font-family:var(--mono);font-variant-numeric:tabular-nums}
.ntkind.k-gift{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 50%,transparent)}`);

  /* 給 notices.js 的鈴鐺：id 前面加 m-，類型 gift（會員權益）；read＝伺服器說看過了 */
  function notes() {
    if (!logged() || S.who !== who()) return [];
    return S.list.map((n) => ({ id: 'm-' + n.id, title: n.title, body: n.body, kind: 'gift', start: n.created, end: 0, pinned: false, read: !!n.seen, mn: true }));
  }
  const unread = () => S.list.filter((n) => !n.seen);
  function changed() { window.dispatchEvent(new CustomEvent('tw:mnotice')); }

  async function seen(ids) {
    const raw = ids.map((x) => String(x).replace(/^m-/, '')).filter(Boolean);
    if (!raw.length) return;
    S.list.forEach((n) => { if (raw.includes(n.id)) n.seen = true; });
    changed();
    if (logged()) await call('/v1/notices/seen', { ids: raw });
  }

  function fetchMine() {
    if (!logged() || S.off) { S.list = []; changed(); return Promise.resolve(); }
    if (S.fly) return S.fly;
    const w = who();
    S.fly = call('/v1/notices/mine', {}).then((j) => {
      S.fly = null;
      if (!j) return;                                   // 連不到：下次再試
      if (j._s === 404) { S.off = true; return; }        // 舊後端沒有這個端點：這一頁都不再問
      if (j._s !== 200 || !Array.isArray(j.notices)) return;
      S.who = w; S.list = j.notices;
      changed();
      popup();
    }).catch(() => { S.fly = null; });
    return S.fly;
  }

  /* 小視窗：只跳還沒跳過的未讀；別的對話框（問卷、歡迎）開著就晚一點再跳，不蓋掉它 */
  const GIFT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5C11 3 12 8 12 8s1-5 4.5-5a2.5 2.5 0 0 1 0 5"/></svg>';
  let retry = 0, retryT = 0, watchT = 0;
  const otherModal = () => [...document.querySelectorAll('[aria-modal="true"]')].some((el) => el.id !== 'subDlg' && !el.hidden && el.getClientRects().length > 0);
  /* 我的視窗開著時，別的視窗（歡迎、問卷）才跳出來 → 先讓位：收起、不算看過，等它關了再跳，兩個不疊在一起 */
  function watchYield(d) {
    clearInterval(watchT);
    watchT = setInterval(() => {
      if (d.hidden || !d.querySelector('#mnPop')) { clearInterval(watchT); return; }
      if (!otherModal()) return;
      clearInterval(watchT);
      const ids = d._mnIds || []; d._mnIds = null; d.hidden = true;
      ids.forEach((id) => S.shown.delete(id));
      retry = 0; clearTimeout(retryT); retryT = setTimeout(popup, 2000);
    }, 400);
  }
  function popup() {
    const list = unread().filter((n) => !S.shown.has(n.id));
    if (!list.length) return;
    const sub = document.getElementById('subDlg');
    if (otherModal() || (sub && !sub.hidden && !sub.querySelector('.mnbox'))) {
      if (retry++ < 30) { clearTimeout(retryT); retryT = setTimeout(popup, 2000); }
      return;
    }
    retry = 0;
    list.forEach((n) => S.shown.add(n.id));
    const ids = unread().map((n) => n.id);
    const all = unread();
    const one = all.length === 1;
    const html = `<div class="mnbox" id="mnPop"><h3><span class="mnic">${GIFT}</span>${one ? esc(all[0].title) : `站主給了你 ${all.length} 項權益`}</h3>
      ${one ? `<p>${esc(all[0].body)}</p>` : `<ul>${all.map((n) => `<li><b>${esc(n.title)}</b><span>${esc(n.body)}</span><i>${dstr(n.created)}</i></li>`).join('')}</ul>`}
      <div class="row2"><button type="button" class="pri" id="mnOk" data-close>知道了</button></div></div>`;
    const d = dialog(html);
    if (!d) return;
    d._mnIds = ids;
    watchYield(d);
    if (!d._mnHook) {
      d._mnHook = true;
      const done = () => { if (d._mnIds && d.hidden && d.querySelector('#mnPop')) { const x = d._mnIds; d._mnIds = null; seen(x); } };
      d.addEventListener('click', () => setTimeout(done, 0));
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setTimeout(done, 0); });
    }
  }

  window.TwMemberNotes = { notes, seen, refresh: fetchMine, unread: () => unread().length };
  window.addEventListener('tw:account', () => { if (!logged()) { S.list = []; S.who = ''; S.shown.clear(); changed(); return; } fetchMine(); });
  window.addEventListener('tw:account-config', () => fetchMine());
  setInterval(() => { if (!document.hidden && logged()) fetchMine(); }, 10 * 60 * 1000);
  function boot() { if (logged()) fetchMine(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
