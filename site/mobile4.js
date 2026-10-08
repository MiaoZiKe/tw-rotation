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

  /* ---------------- 主項目圖示：直接讀電腦版側欄（layout4.css）那一格的同一個遮罩，不另外畫一套 ----------------
     2026-10-08 Andy：「側邊欄位對應圖示不見了」。電腦版的圖示是 :root.l4 .tab[data-view=X] 的 --l4-ic（多半指向 --l4-ic-NAME），
     手機不掛 l4，這些變數不會生效 → 這裡從樣式表把同一個值讀出來，寫到抽屜那一列的 --m4-ic。 */
  let IC = null;
  function icons() {
    if (IC) return IC;
    const vars = {}, map = {};
    const walk = (rules) => { for (const r of rules) {
      if (r.cssRules && !r.selectorText) { try { walk(r.cssRules); } catch (e) { /* 跨網域樣式表 */ } continue; }
      const sel = r.selectorText || '', st = r.style; if (!st) continue;
      if (/^:root\.l4\s*,\s*:root\.l4m$/.test(sel)) for (let i = 0; i < st.length; i++) { const k = st[i]; if (k.startsWith('--l4-ic-')) vars[k] = st.getPropertyValue(k).trim(); }
      const ic = st.getPropertyValue('--l4-ic').trim(); if (!ic) continue;
      let m = /^:root\.l4 \.tab\[data-view="(\w+)"\]$/.exec(sel);
      if (m) map[m[1]] = ic;
      else if (sel === ':root.l4 .tab.l4perm') map.admin = ic;
    } };
    for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (e) { /* 跨網域樣式表讀不到 */ } }
    const res = (v) => { const m = /^var\((--l4-ic-[\w-]+)\)$/.exec(v || ''); return m ? vars[m[1]] : v; };
    IC = {}; Object.keys(map).forEach((k) => { IC[k] = res(map[k]); });
    IC.search = vars['--l4-ic-search']; IC.palette = vars['--l4-ic-palette']; IC.events = vars['--l4-ic-bell'];
    if (!Object.keys(map).length) IC = null;      // 樣式表還沒載好：下次打開再讀
    return IC || {};
  }
  const mi = (k) => { const v = icons()[k]; return v ? `<i class="m4ic" style="--m4-ic:${esc(v)}" aria-hidden="true"></i>` : ''; };

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
    let h = `<div class="m4grp m4top"><button type="button" class="m4item" data-act="search">${mi('search')}<span>搜尋</span></button>
      <button type="button" class="m4item" data-act="events">${mi('events')}<span>事件</span>${evn ? `<span class="n">${esc(evn)}</span>` : ''}</button></div>`;
    N.GROUPS.forEach((G) => {
      const rows = [];
      G.views.forEach((v) => {
        if (v === 'admin') {
          if (!N.isAdmin()) return;
          rows.push(`<button type="button" class="m4item${adm ? ' on' : ''}" data-h="#admin/perm" data-v="admin">${mi('admin')}<span>管理區</span></button>`);
          N.admSubs().forEach(([k, t, , icn]) => rows.push(`<button type="button" class="m4sub${adm === k ? ' on' : ''}" data-h="#admin/${k}" data-adm="${k}">${ic(icn)}<span>${esc(t)}</span></button>`));
          return;
        }
        if (v === 'stock' || v === 'delivery' || !has(v)) return;    // 個股頁沒有側欄入口；交付清單入口桌機也收掉了
        const P = N.PAGES[v] || { t: v };
        const subs = N.SUBS[v] || [];
        const on = pg === v || (v === 'industry' && pg === 'stock');
        rows.push(`<button type="button" class="m4item${on && !subs.length ? ' on' : ''}${on && subs.length ? ' here' : ''}" data-h="${HREF[v] || '#' + v}" data-v="${v}">${mi(v)}<span>${esc(P.t)}</span></button>`);
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
    /* 2026-10-08（Andy：「在線人數 以及 明暗功能 版面風格都跟網頁版一樣放在上方變成小圖。上方留LOGO就好。今日事件重複出現 留左側欄位的」）：
       頁名從頂欄搬到內容區最上面（同電腦版頁首大標）；頂欄只留 ☰＋頭像，右邊一排小圖示（明暗、版面風格、平台導覽、在線、登入）。 */
    const main = $('main');
    if (main && !title) {
      title = document.createElement('h1'); title.id = 'm4Title'; title.className = 'm4pghead';
      main.insertBefore(title, main.firstChild);
    }
    buildTools(bar);
    paintTitle();
  }
  function teardown() {
    close();
    restoreTools();
    [burger, drawer, back, title].forEach((e) => { if (e) e.remove(); });
    burger = drawer = back = title = null;
    document.body.classList.remove('m4lock');
  }


  /* ---------------- 頂欄右邊的小圖示（全部是「搬節點」：id、onclick 都是原本那顆，跟電腦版 layout4.js syncTools 同一套） ----------------
     順序同電腦版頁首右上：明暗（#themeBtn）→ 版面風格（#t4Btn）→ 平台導覽（#twPageTourBtn）→ 在線（#acctOnline）→ 登入（#acctBtn）。
     會員功能沒開時沒有 #acctBtn：放一顆 #m4Login，講清楚為什麼不能登入（同電腦版 #l4Login 的字）。
     搜尋收進抽屜最上面的「搜尋」；「⋯」選單拿掉（裡面的今日事件、自選都在抽屜）。 */
  const TOOLS = ['#themeBtn', '#t4Btn', '#twPageTourBtn', '#acctOnline', '#acctBtn', '#m4Login'];   // #themeBtn 搬進來但藏著（明暗在「外觀」面板裡，去按它本人）
  let tools = null; const home = new Map();
  function acctOn() { const A = window.TwAccount; return !!(A && A.on && A.on()); }
  function buildTools(bar) {
    if (!tools) { tools = document.createElement('div'); tools.id = 'm4Tools'; tools.className = 'm4tools'; }
    if (tools.parentNode !== bar) bar.appendChild(tools);
    let lg = $('#m4Login');
    if (!acctOn() && !$('#acctBtn')) {
      if (!lg) {
        lg = document.createElement('button'); lg.type = 'button'; lg.id = 'm4Login'; lg.className = 'm4login';
        lg.textContent = '登入'; lg.title = '會員登入（目前沒有連上線）'; lg.setAttribute('aria-haspopup', 'dialog');
        lg.onclick = (e) => { e.stopPropagation(); loginTip(lg); };
      }
    } else if (lg) { lg.remove(); lg = null; }
    const want = TOOLS.map((q) => (q === '#m4Login' ? lg : $(q))).filter(Boolean);
    want.forEach((e) => { if (e.parentNode !== tools && !home.has(e) && e.id !== 'm4Login') home.set(e, [e.parentNode, e.nextSibling]); });
    const cur = Array.from(tools.children);
    if (want.length !== cur.length || want.some((e, i) => cur[i] !== e)) want.forEach((e) => tools.appendChild(e));
    const t4 = $('#t4Btn'), I = icons();
    if (t4 && !$('.m4ic', t4) && I.palette) { t4.dataset.m4txt = t4.textContent; t4.setAttribute('aria-label', '版面風格'); t4.innerHTML = mi('palette'); }
  }
  function restoreTools() {
    home.forEach(([p, nx], e) => { if (p && p.isConnected) p.insertBefore(e, nx && nx.parentNode === p ? nx : null); });
    home.clear();
    const t4 = $('#t4Btn'); if (t4 && t4.dataset.m4txt) { t4.textContent = t4.dataset.m4txt; delete t4.dataset.m4txt; }
    ['#m4Login', '#m4LoginTip', '#m4Tools'].forEach((q) => { const e = $(q); if (e) e.remove(); });
    tools = null;
  }
  function loginTip(b) {
    let tip = $('#m4LoginTip');
    if (tip && !tip.hidden) { tip.hidden = true; return; }
    if (!tip) {
      tip = document.createElement('div'); tip.id = 'm4LoginTip'; tip.className = 'm4logintip'; tip.setAttribute('role', 'dialog'); tip.setAttribute('aria-label', '會員登入');
      tip.innerHTML = '<b>會員系統目前沒有連上線</b><p>網站暫時連不到會員系統，所以現在不能登入。</p><p>自選清單照樣可以用，會存在這台瀏覽器。</p>';
      document.body.appendChild(tip);
      document.addEventListener('pointerdown', (e) => { if (!tip.hidden && !tip.contains(e.target) && e.target !== $('#m4Login')) tip.hidden = true; }, true);
    }
    tip.hidden = false;
    const r = b.getBoundingClientRect();
    tip.style.top = Math.round(r.bottom + 8) + 'px'; tip.style.right = '8px';
  }


  /* ---------------- 現金流試算／複利試算的控制區收成一顆「條件 ▾」摘要列（2026-10-08 Andy：「這邊版面優化 不要換行太多」） ----------------
     控制項本身一個都沒換（id、onclick 照舊在 etfpage.js），只是在手機預設收起來，上面放一行摘要（例如「年領 100 萬・配息型・近 5 年」），點開才看到全部。 */
  const txt = (e) => (e ? (e.tagName === 'SELECT' ? ((e.options[e.selectedIndex] || {}).text || '') : e.textContent) : '').replace(/\s+/g, ' ').trim();
  function condSummary(ctl) {
    if (ctl.classList.contains('cxctl')) {
      const o = txt($('#cxObj', ctl)), f = ($('#cxFrom', ctl) || {}).value || '';
      return [o, f ? f + ' 起' : ''].filter(Boolean).join('・');
    }
    const mode = txt($('#incMode .on', ctl)), amtB = txt($('#incAmtBox .on', ctl)), amtI = ($('#incAmt', ctl) || {}).value;
    const amt = amtB || (amtI ? Number(amtI).toLocaleString('zh-TW') + ' 元' : '');
    const scope = txt($('#incScope .on', ctl)), nhi = ($('#incNhi', ctl) || {}).checked ? '扣二代健保' : '';
    const rng = $('#etfIncRngBox', ctl); const per = rng ? txt($('select', rng) || $('.on', rng)) : '';
    return [mode + (amt ? ' ' + amt : ''), scope, per, nhi].filter(Boolean).join('・');
  }

  /* 產業鏈頁：環節卡清單（#chainList）與「全部展開」列（#segTools）收進一顆「環節卡清單 ▸」收合列，預設收起（Andy：「其餘的可以不用拿掉，但一定要收合」） */
  function wireChainList() {
    if (!isM()) return;
    const pane = $('#indChain .chainpane'); if (!pane || !$('#chainList', pane)) return;
    let b = $(':scope > .m4fold', pane);
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.className = 'm4fold'; b.setAttribute('aria-expanded', 'false');
      b.innerHTML = '環節卡清單 <i aria-hidden="true">▸</i>';
      b.onclick = () => { const on = !pane.classList.contains('m4listopen'); pane.classList.toggle('m4listopen', on); b.setAttribute('aria-expanded', on ? 'true' : 'false'); $('i', b).textContent = on ? '▾' : '▸'; };
      const anchor = $('#segTools', pane) || $('#chainList', pane); pane.insertBefore(b, anchor);
    }
  }
  function wireCond() {
    if (!isM()) return;
    $$('#v-etf #incPM > .incctl, #v-etf #incPX .cxctl').forEach((ctl) => {
      let b = ctl.previousElementSibling;
      if (!b || !b.classList.contains('m4cond')) {
        b = document.createElement('button'); b.type = 'button'; b.className = 'm4cond'; b.setAttribute('aria-expanded', 'false');
        b.onclick = () => { const on = !ctl.classList.contains('m4open'); ctl.classList.toggle('m4open', on); b.setAttribute('aria-expanded', on ? 'true' : 'false'); paint(); };
        ctl.before(b);
        new MutationObserver(() => paint()).observe(ctl, { subtree: true, attributes: true, attributeFilter: ['class', 'value'], childList: true });
        ctl.addEventListener('change', () => setTimeout(paint, 0)); ctl.addEventListener('input', () => setTimeout(paint, 0));
      }
      function paint() { const t = '條件：' + (condSummary(ctl) || '—'); const want = `<span>${esc(t)}</span><i aria-hidden="true">${ctl.classList.contains('m4open') ? '▴' : '▾'}</i>`; if (b.innerHTML !== want) b.innerHTML = want; }
      paint();
    });
  }

  /* 頂欄頁名：「分組小字＋頁名（子頁名）」—— 側欄收進抽屜之後，這是「我在哪」唯一的提示 */
  function paintTitle() {
    const N = nav(); if (!title || !N) return;
    const pg = curPage(), P = N.PAGES[pg];
    let name = P ? P.t : '';
    const s = (N.SUBS[pg] || []).find((x) => x.k === curSub());
    
    if (pg === 'admin') name = '管理區';
    if (pg === 'stock') { const c = $('#indCrumbs .cur'); if (c && c.textContent.trim()) name = c.textContent.trim(); }
    // 產業鏈頁與個股頁自己有麵包屑／個股名當頁首（產業地圖 › 一般電子），再加一行大標只會把主圖往下推出第一屏
    title.hidden = pg === 'industry' || pg === 'stock';
    // 內容區頁首大標（同電腦版 #l4Head）：「頁名 子頁名」
    title.innerHTML = s ? `${esc(P.t)} <span>${esc(s.t)}</span>` : esc(name || brandName());
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
    // 會員功能晚一步才開（account.js 讀完設定檔）、#acctBtn／#acctOnline 晚一步才建：出現時收進頂欄小圖示列
    new MutationObserver(() => { if (tools && isM()) { const bar = $('.topbar'); const miss = TOOLS.some((q) => { const e = $(q); return e && e.parentNode !== tools; }) || (acctOn() && $('#m4Login')); if (bar && miss) buildTools(bar); } })
      .observe(document.body, { childList: true, subtree: true });
    let ct = 0; new MutationObserver(() => { if (!isM()) return; clearTimeout(ct); ct = setTimeout(() => { wireCond(); wireChainList(); }, 120); }).observe(document.body, { childList: true, subtree: true });
    wireCond();
  }
  window.TwM4 = { open, close, isOpen: () => !!(drawer && !drawer.hidden) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
