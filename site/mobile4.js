/* ============================================================================
   ★ 手機 v2（2026-10-08，規劃：docs/mobile_v2_plan.md）
   Andy 10-08：「手機版本 幫我 follow 現在版本進行設計規劃……我是側邊欄位就用側邊欄位進行」
   ＋「所有頁面接盡可能保持一個原則，開啟就能看到完整資訊」。

   這一支只做「導覽」：
     · ≤640 掛 <html class="m4">（index.html 開頭那行先掛一次，這裡處理之後跨寬度）；
     · 頂欄最左邊一顆漢堡鈕（#m4Burger），點開左側抽屜（#m4Drawer）；
     · 抽屜的分組與子項**直接讀 layout4.js 的 window.TwL4Nav**（電腦版側欄同一份清單），不另抄；
       管理區只對管理者畫（同 layout4.js syncPerm 的規則：isAdmin() 才建這幾列，訪客 DOM 裡沒有）；
     · 頂欄站名的位置改寫成「目前這一頁（子頁）」的名字。
   取代的舊東西：底部五格導覽（mobile3.js buildNav 在 m4 下不再插「更多」、CSS 把 #tabs 藏起來）、
   總覽「錢往哪跑／貴不貴／別進的理由」三顆大鈕（app.js miaPager 在 m4 下把步驟拍平）。

   ⚠ 桌機（>640）：這支什麼都不插；跨過 640 時把插過的節點全部拆掉、拿掉 m4。
   ============================================================================ */
(function () {
  'use strict';
  const MAX = 640;
  const root = document.documentElement;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const isM = () => window.innerWidth <= MAX;
  let burger = null, drawer = null, back = null, title = null;

  /* 頁面 → 抽屜裡要點的網址（有子項的大項點了進第一個子項，跟電腦版一樣） */
  const HREF = { overview: '#overview', earnings: '#earnings', flow: '#flow/rotation', heatmap: '#heatmap/industry',
    industry: '#industry', market: '#market', explore: '#explore', etf: '#etf/list', season: '#season', watch: '#watch', delivery: '#delivery' };

  function nav() { return window.TwL4Nav || null; }
  function brandName() { const b = $('.topbar .brand b'); return (b && b.textContent.trim()) || '哩股哩股'; }
  function curPage() {
    const h = (location.hash || '#overview').slice(1).split('/')[0] || 'overview';
    return { themes: 'heatmap', tasks: 'delivery' }[h] || h;
  }
  function curSub() { return root.getAttribute('data-l4sub') || ''; }
  function curAdm() { const m = /^#admin\/(\w+)/.exec(location.hash || ''); return /^#admin\b/.test(location.hash || '') ? (m ? (m[1] === 'members' ? 'perm' : m[1]) : 'traffic') : ''; }

  /* ---------------- 抽屜內容（每次打開都重畫：登入／登出之後管理區要跟著出現或消失） ---------------- */
  function render() {
    const N = nav(); if (!drawer || !N) return;
    const tabs = $('#tabs');
    const has = (v) => !!(tabs && $(`.tab[data-view="${v}"]`, tabs)) || v === 'delivery';
    const pg = curPage(), sub = curSub(), adm = curAdm();
    const ic = (k) => (N.subIcon ? N.subIcon(k) : '');
    /* 2026-10-08（Andy：「左側的內容需要排序跟網頁版一樣，切換明暗也出現一個就夠」）：
       順序＝電腦版側欄：最上面搜尋、再來「事件」（件數徽章），之後各分組。
       分組與順序直接讀 layout4.js 的 GROUPS.views（電腦版側欄用 CSS 依它換位置，畫面順序＝這份；#tabs 的 DOM 順序不是畫面順序）。
       明暗切換頂欄「⋯」裡已經有一個，抽屜不再放；「工具」分組拿掉。 */
    const evn = (($('#evCount') || {}).textContent || '').trim();
    let h = `<div class="m4grp m4top"><button type="button" class="m4item" data-act="search">搜尋</button>
      <button type="button" class="m4item" data-act="events">事件${evn ? `<span class="n">${esc(evn)}</span>` : ''}</button></div>`;
    N.GROUPS.forEach((G) => {
      const rows = [];
      G.views.forEach((v) => {
        if (v === 'admin') {
          if (!N.isAdmin()) return;
          rows.push(`<button type="button" class="m4item${adm ? ' on' : ''}" data-h="#admin/perm" data-v="admin">管理區</button>`);
          N.admSubs().forEach(([k, t, , icn]) => rows.push(`<button type="button" class="m4sub${adm === k ? ' on' : ''}" data-h="#admin/${k}" data-adm="${k}">${ic(icn)}<span>${esc(t)}</span></button>`));
          return;
        }
        if (v === 'stock' || v === 'delivery' || !has(v)) return;    // 個股頁沒有側欄入口；交付清單入口桌機也收掉了
        const P = N.PAGES[v] || { t: v };
        const subs = N.SUBS[v] || [];
        const on = pg === v || (v === 'industry' && pg === 'stock');
        rows.push(`<button type="button" class="m4item${on && !subs.length ? ' on' : ''}${on && subs.length ? ' here' : ''}" data-h="${HREF[v] || '#' + v}" data-v="${v}">${esc(P.t)}</button>`);
        subs.forEach((s) => rows.push(`<button type="button" class="m4sub${sub === s.k ? ' on' : ''}" data-h="${s.h}" data-sub="${s.k}">${ic(s.ic)}<span>${esc(s.t)}</span></button>`));
      });
      if (rows.length) h += `<div class="m4grp" data-g="${G.g}"><div class="m4gt">${esc(G.t)}</div>${rows.join('')}</div>`;
    });
    const ver = (($('#buildver') || {}).textContent || '').trim();
    h += `<div class="m4ver">網頁版號 <span class="mono">${esc(ver || '—')}</span></div>`;
    $('.m4body', drawer).innerHTML = h;
  }

  function open() {
    if (!drawer) return;
    render();
    drawer.hidden = false; back.hidden = false;
    burger.setAttribute('aria-expanded', 'true');
    document.body.classList.add('m4lock');
    requestAnimationFrame(() => drawer.classList.add('in'));
    const on = $('.on', drawer); if (on) on.scrollIntoView({ block: 'center' });
  }
  function close() {
    if (!drawer || drawer.hidden) return;
    drawer.classList.remove('in');
    drawer.hidden = true; back.hidden = true;
    burger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('m4lock');
  }

  function build() {
    const bar = $('.topbar'); if (!bar) return;
    if (!burger) {
      burger = document.createElement('button');
      burger.type = 'button'; burger.id = 'm4Burger'; burger.className = 'm4burger';
      burger.setAttribute('aria-label', '開啟導覽'); burger.setAttribute('aria-controls', 'm4Drawer'); burger.setAttribute('aria-expanded', 'false');
      burger.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>';
      burger.onclick = (e) => { e.stopPropagation(); if (drawer && !drawer.hidden) close(); else open(); };
    }
    if (burger.parentNode !== bar) bar.insertBefore(burger, bar.firstChild);
    if (!drawer) {
      back = document.createElement('div'); back.id = 'm4Back'; back.className = 'm4back'; back.hidden = true;
      back.addEventListener('click', close);
      drawer = document.createElement('nav'); drawer.id = 'm4Drawer'; drawer.className = 'm4drawer'; drawer.hidden = true;
      drawer.setAttribute('aria-label', '網站導覽');
      // 品牌：跟頂欄同一顆頭像（site/brand/）＋站名（讀 .brand b 的字，改名時不必改這裡）
      const nm = esc(brandName());
      drawer.innerHTML = '<div class="m4head"><span class="m4brand"><picture><source srcset="brand/mark-64.webp 1x, brand/mark-128.webp 2x" type="image/webp">'
        + `<img src="brand/mark-64.png" srcset="brand/mark-64.png 1x, brand/mark-128.png 2x" width="32" height="32" alt="${nm}"></picture><b>${nm}</b></span>`
        + '<button type="button" class="m4x" aria-label="關閉導覽">✕</button></div><div class="m4body"></div>';
      $('.m4x', drawer).onclick = close;
      drawer.addEventListener('click', (e) => {
        const b = e.target.closest('button[data-h], button[data-act]'); if (!b) return;
        if (b.dataset.act) {
          close();
          const t = document.getElementById(b.dataset.act === 'events' ? 'evToggle' : 'mSearchBtn');
          if (t) t.click();
          return;
        }
        const want = b.dataset.h;
        close();
        if (b.dataset.adm) { const G = window.TwAdmin; if (G && G.guard && !G.guard()) return; }
        // 已經在同一頁同一子項：不動網址（同電腦版「點已選中的子項不換頁」）
        if (location.hash !== want) location.hash = want;
      });
      document.body.append(back, drawer);
    }
    const brand = $('.brand > div:not(.logo)', bar);
    if (brand && !title) {
      title = document.createElement('span'); title.id = 'm4Title'; title.className = 'm4title';
      brand.insertBefore(title, brand.firstChild);
    }
    paintTitle();
  }
  function teardown() {
    close();
    [burger, drawer, back, title].forEach((e) => { if (e) e.remove(); });
    burger = drawer = back = title = null;
    document.body.classList.remove('m4lock');
  }

  /* 頂欄頁名：「分組小字＋頁名（子頁名）」—— 側欄收進抽屜之後，這是「我在哪」唯一的提示 */
  function paintTitle() {
    const N = nav(); if (!title || !N) return;
    const pg = curPage(), P = N.PAGES[pg];
    let name = P ? P.t : '', grp = P ? P.grp : '';
    const s = (N.SUBS[pg] || []).find((x) => x.k === curSub());
    if (s) { grp = P.t; name = s.t; }        // 子頁：小字寫母頁（資金流向），大字寫子頁（資金輪動）—— 390 寬放不下「資金流向・族群×法人＋集中度」
    if (pg === 'admin') { name = '管理區'; grp = '專案'; }
    if (pg === 'stock') { const c = $('#indCrumbs .cur'); if (c && c.textContent.trim()) name = c.textContent.trim(); }
    // 小字：站名・分組（品牌一直看得到）；大字：頁名
    title.innerHTML = `<i>${esc(brandName())}${grp ? '・' + esc(grp) : ''}</i><span>${esc(name || brandName())}</span>`;
  }

  function sync() {
    const want = isM();
    const had = root.classList.contains('m4');
    root.classList.toggle('m4', want);
    if (want) build(); else teardown();
    // 跨過 640：請 route() 重跑一次（掛上 m4 要導到子分頁、撤掉要讓整頁的卡回來）
    // 只有用到子分頁的三頁需要（同 layout4.js 的做法）；其他頁重跑 route() 會在輸入框還有焦點時重畫（#watch 實測噴 NotFoundError）
    if (want !== had && /^#(flow|heatmap|etf)(\/|$)/.test(location.hash || '')) setTimeout(() => window.dispatchEvent(new HashChangeEvent('hashchange')), 0);
  }

  function init() {
    sync();
    let rt = 0;
    window.addEventListener('resize', (e) => { if (e.twEcho) return; clearTimeout(rt); rt = setTimeout(sync, 150); });
    window.addEventListener('hashchange', () => { close(); [0, 120, 800].forEach((t) => setTimeout(paintTitle, t)); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    new MutationObserver(paintTitle).observe(root, { attributes: true, attributeFilter: ['data-l4sub'] });
  }
  window.TwM4 = { open, close, isOpen: () => !!(drawer && !drawer.hidden) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
