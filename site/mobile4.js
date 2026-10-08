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
    // 2026-10-08 晚（Andy：「搜尋功能放在上方欄位」）：搜尋移到頂欄（#m4Search），抽屜不再放
    let h = `<div class="m4grp m4top"><button type="button" class="m4item" data-act="events">${mi('events')}<span>事件</span>${evn ? `<span class="n">${esc(evn)}</span>` : ''}</button></div>`;
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
        /* 2026-10-08 晚（Andy：「手機版本的側邊欄位，子分頁都需要變成在圖二那邊」）：抽屜只列主項目，子頁改成頁面頂端的頁籤（paintTitle）；
           有子頁的主項目點了進「上次看的那個子頁」（沒看過就第一個） */
        let href = HREF[v] || '#' + v;
        if (subs.length) { let last = null; try { last = localStorage.getItem('tw.m4.sub.' + v); } catch (e) { /* 私密視窗 */ } const hit = subs.find((x) => x.h === last); if (hit) href = hit.h; }
        rows.push(`<button type="button" class="m4item${on ? ' on' : ''}" data-h="${href}" data-v="${v}">${mi(v)}<span>${esc(P.t)}</span></button>`);
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
    { const bb = $('#m4BackBtn'); if (bb) bb.remove(); }
    [burger, drawer, back, title].forEach((e) => { if (e) e.remove(); });
    burger = drawer = back = title = null;
    document.body.classList.remove('m4lock');
  }


  /* ---------------- 頂欄右邊的小圖示（全部是「搬節點」：id、onclick 都是原本那顆，跟電腦版 layout4.js syncTools 同一套） ----------------
     順序同電腦版頁首右上：明暗（#themeBtn）→ 版面風格（#t4Btn）→ 平台導覽（#twPageTourBtn）→ 在線（#acctOnline）→ 登入（#acctBtn）。
     會員功能沒開時沒有 #acctBtn：放一顆 #m4Login，講清楚為什麼不能登入（同電腦版 #l4Login 的字）。
     搜尋收進抽屜最上面的「搜尋」；「⋯」選單拿掉（裡面的今日事件、自選都在抽屜）。 */
  const TOOLS = ['#m4Search', '#themeBtn', '#t4Btn', '#twPageTourBtn', '#acctOnline', '#acctBtn', '#m4Login'];   // #themeBtn 搬進來但藏著（明暗在「外觀」面板裡，去按它本人）
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
    let sb = $('#m4Search');
    if (!sb) {
      sb = document.createElement('button'); sb.type = 'button'; sb.id = 'm4Search'; sb.className = 'm4srch'; sb.setAttribute('aria-label', '搜尋個股（代號或簡稱）');
      sb.innerHTML = mi('search');
      // 就是去按 mobile3.js 原本那顆 #mSearchBtn：頂欄展開成一條全寬搜尋框、自動 focus、有「取消」；搜尋結果照舊
      sb.onclick = (e) => { e.stopPropagation(); const m3 = $('#mSearchBtn'); if (m3) m3.click(); };
    }
    const want = TOOLS.map((q) => (q === '#m4Login' ? lg : q === '#m4Search' ? sb : $(q))).filter(Boolean);
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
    ['#m4Login', '#m4LoginTip', '#m4Search', '#m4Tools'].forEach((q) => { const e = $(q); if (e) e.remove(); });
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

  /* ETF 總覽上方三張前 5 名卡：手機改成分頁（Andy：「把上方變成分頁式 不要用滑動」）—— 一排膠囊分段鈕，一次只顯示一張；卡片本身與裡面的切換一個都沒換 */
  const TRI = [['etfPopCard', '最受歡迎'], ['etfRetTopCard', '報酬率'], ['etfYldCard', '殖利率']];
  let triCur = 0;
  function wireEtfTri() {
    if (!isM()) return;
    const tri = $('#etfTri'); if (!tri) return;
    let seg = tri.previousElementSibling;
    if (!seg || !seg.classList.contains('m4trisg')) {
      seg = document.createElement('div'); seg.className = 'mpager m4trisg'; seg.setAttribute('role', 'tablist');
      seg.innerHTML = TRI.map(([id, t], i) => `<button type="button" role="tab" data-i="${i}">${t}</button>`).join('');
      seg.onclick = (e) => { const b = e.target.closest('button[data-i]'); if (!b) return; triCur = +b.dataset.i; paintTri(); };
      tri.before(seg);
    }
    seg.hidden = tri.hidden;
    paintTri();
  }
  function paintTri() {
    const seg = $('.m4trisg'); if (!seg) return;
    $$('button', seg).forEach((b, i) => { const on = i === triCur; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    TRI.forEach(([id], i) => { const c = document.getElementById(id); if (c) c.classList.toggle('m4trioff', i !== triCur); });
  }

  /* 產業地圖：手機只留「成交值占比」甜甜圈（Andy：「產業地圖在手機版本只要留下圓餅圖」）；
     「族群漲跌幅」橫條圖不拿掉，收進甜甜圈下面一顆預設收起的「族群漲跌幅 ▸」收合列（「其餘不用拿掉，但要收合」） */
  function wireIndMap() {
    if (!isM()) return;
    const grid = $('#v-industry .gpgrid'); if (!grid) return;
    const bar = $('.gpcard:not(.gppie)', grid); if (!bar) return;
    let b = $(':scope > .m4fold', grid);
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.className = 'm4fold'; b.setAttribute('aria-expanded', 'false');
      b.innerHTML = '族群漲跌幅 <i aria-hidden="true">▸</i>';
      b.onclick = () => { const on = !bar.classList.contains('m4open'); bar.classList.toggle('m4open', on); b.setAttribute('aria-expanded', on ? 'true' : 'false'); $('i', b).textContent = on ? '▾' : '▸';
        setTimeout(() => window.dispatchEvent(new Event('resize')), 30); };
      grid.appendChild(b);
    }
    if (b.nextElementSibling !== bar) b.after(bar);   // 收合列在甜甜圈下面、橫條圖接在收合列後面
  }

  /* ★ 已選膠囊列 → 一顆「已選 N ▾」篩選下拉（Andy：「手機版本出現這種的，就都改成篩選式下拉清單」）。
     共用元件 = window.MultiSelect.dropdown，底層就是全站已在用的 App.msDD（週期統計、站上均線、ETF 報酬比較同一支），
     不另寫一套：搜尋框、勾選框、色點、全選／清除都是它的。這裡只負責「長出一顆 msDD 的外殼」，
     勾選動作一律轉給頁面原本的控制項（清單勾選框、加入鈕、膠囊本身），上限與重畫照頁面自己的規則走。
     盤點（402 寬）：
       · 週期統計 #seasonKey、站上均線 #maGroupKey → 旁邊本來就有 msDD 下拉，手機只把膠囊列藏起來（CSS）
       · 現金流試算單檔 #incChips → 新長一顆下拉，候選＝右側清單 #incList
       · 複利試算自訂再投入 #cxChips → 新長一顆下拉，候選＝ #incRxList（ETF 與上市個股）
       · ETF 報酬比較「加入比較」本來就是 msDD（#etfCmpDD），不動 */
  const MS_SHELL = (label, ph) => `<button type="button" class="ddbtn" aria-haspopup="true" aria-expanded="false">${label}<b>未選</b><i aria-hidden="true">▾</i></button>
    <div class="ddpanel" hidden><input type="search" class="sndd-q" placeholder="${ph || '搜尋代號或名稱'}" aria-label="${ph || '搜尋代號或名稱'}" autocomplete="off">
    <div class="ddbar"><span class="muted sndd-n"></span><button type="button" class="btn small dd-all">全選</button><button type="button" class="btn small dd-none">清除</button></div>
    <div class="ddlist"></div></div>`;
  window.MultiSelect = window.MultiSelect || {
    /* host＝放在誰前面；id＝這顆下拉的 id；cfg＝msDD 的 cfg（menu／onToggle／onAll／onNone）。回 msDD 的 api（sync 用） */
    dropdown(host, id, label, cfg, ph) {
      const A = window.App; if (!host || !A || !A.msDD) return null;
      let dd = document.getElementById(id);
      if (!dd) { dd = document.createElement('div'); dd.id = id; dd.className = 'rotdd wide msdd m4ms'; dd.innerHTML = MS_SHELL(label, ph); host.before(dd); }
      return A.msDD(dd, cfg);
    },
  };
  const msNote = (t) => { const m = $('#incListMsg') || $('#cxMsg'); if (m && t) m.textContent = t; };
  function wireIncMS() {
    if (!isM()) return;
    const key = $('#incChips'), list = $('#incList'); if (!key || !list) return;
    const sig = key.innerHTML.length + ':' + list.innerHTML.length + ':' + $$('.ilr.in', list).length;
    if (key._m4sig === sig && document.getElementById('m4IncMS')) return;
    key._m4sig = sig;
    const box = (n) => $(`.ilr[data-code="${CSS.escape(n.split(' ').pop())}"] input[type=checkbox]`, list);
    const flip = (n, on) => { const c = box(n); if (!c || c.checked === on) return; if (on && c.disabled) { msNote('最多 5 檔，請先取消一檔'); return; } c.checked = on; c.dispatchEvent(new Event('change', { bubbles: true })); };
    const ms = window.MultiSelect.dropdown(key, 'm4IncMS', '單檔：', {
      menu: { rf: 'm4', kind: 'inc' },
      onToggle: (c) => flip(c.dataset.n, c.checked),
      onAll: (vis) => vis.forEach((n) => flip(n, true)),
      onNone: (vis) => (vis || $$('.ilr.in', list).map((r) => r.dataset.code)).forEach((n) => flip(n, false)),
    });
    if (!ms) return;
    const col = {}; $$('button.snk[data-n]', key).forEach((b) => { col[b.dataset.n.split(' ').pop()] = b.style.getPropertyValue('--c'); });
    const rows = $$('.ilr', list).map((r) => { const cb = $('input', r), on = !!(cb && cb.checked);
      return { name: `${$('.nm', r) ? $('.nm', r).textContent : ''} ${r.dataset.code}`, on, color: on ? (col[r.dataset.code] || 'var(--ink-3)') : 'rgba(128,128,128,.45)',
        val: ($('.mv', r) || {}).textContent || '', title: cb && cb.disabled && !on ? '最多 5 檔，先取消一檔' : '' }; });
    const n = rows.filter((r) => r.on).length;
    const avg = $('.snk.avg', key);
    ms.sync({ head: avg ? `<div class="ddopt" data-headrow="1" style="--c:var(--ink-3)"><label><span class="nm">— 平均（細灰線，永遠畫）</span></label></div>` : '',
      rows, count: `最多 5 檔 · 已選 ${n} 檔`, label: n ? `已選 ${n} 檔` : '未選', n });
    $$('.ddopt input[type=checkbox]', document.getElementById('m4IncMS')).forEach((c) => { if (!c.checked && n >= 5) c.disabled = true; });
  }
  function wireCxMS() {
    if (!isM()) return;
    const key = $('#cxChips'), dl = $('#incRxList'), inp = $('#cxIn'), add = $('#cxAdd'); if (!key || !dl || !inp || !add) return;
    const wrap = key.closest('.cxlg') || key.parentElement;
    const sig = key.innerHTML;
    if (key._m4sig === sig && document.getElementById('m4CxMS')) return;
    key._m4sig = sig;
    const cur = () => $$('.cmpx', key).map((b) => b.dataset.code);
    const flip = (code, on) => {
      if (on) { if (cur().includes(code)) return; inp.value = code; add.click(); }
      else { const b = $(`.cmpx[data-code="${CSS.escape(code)}"]`, key); if (b) b.click(); }
    };
    const ms = window.MultiSelect.dropdown(wrap.querySelector('.cmpw') || key, 'm4CxMS', '自訂再投入：', {
      menu: { rf: 'm4', kind: 'cx' },
      onToggle: (c) => flip(c.dataset.n.split(' ')[0], c.checked),
      onAll: (vis) => vis.slice(0, 5).forEach((n) => flip(n.split(' ')[0], true)),
      onNone: (vis) => (vis ? vis.map((n) => n.split(' ')[0]) : cur()).forEach((c) => flip(c, false)),
    }, '搜尋代號或名稱（ETF、個股）');
    if (!ms) return;
    const on = new Set(cur());
    const opts = $$('option', dl).map((o) => ({ code: o.value, name: o.textContent }));
    opts.sort((a, b) => (on.has(b.code) - on.has(a.code)));
    ms.sync({ rows: opts.map((o) => ({ name: `${o.code} ${o.name}`, on: on.has(o.code), color: on.has(o.code) ? 'var(--accent)' : 'rgba(128,128,128,.45)', val: '' })),
      count: `已選 ${on.size} 檔`, label: on.size ? `已選 ${on.size} 檔` : '未選', n: on.size });
  }

  /* 訂閱方案頁（Andy：「已經有格式表，下方就不需要再一次出現，格式表需要一頁看到不同方案，所以需要精簡優化」）：
     比較表的格子改短寫（每日 10 次 → 10/日、最多 3 檔 → 3 檔、1 頁・每頁 10 檔 → 1×10），原文留在 title；表格本身與方案卡的精簡在 mobile4.css 第 24 節 */
  const PR_SHORT = [[/^每日\s*(\d+)\s*次$/, '$1/日'], [/^每日\s*(\d+)\s*(\S+)$/, '$1$2/日'], [/^最多\s*(\d+)\s*(\S+)$/, '$1 $2'],
    [/^(\d+)\s*頁・每頁\s*(\d+)\s*檔$/, '$1×$2'], [/^不限頁・每頁\s*(\d+)\s*檔$/, '不限×$1'], [/^全部方案皆可用$/, '全部皆可']];
  function wirePricing() {
    if (!isM()) return;
    const t = $('#prTable'); if (!t || t._m4short) return;
    t._m4short = true;
    $$('tbody td:not(:first-child), tbody tr.base td', t).forEach((td) => {
      const x = td.textContent.trim(); let y = x;
      for (const [re, to] of PR_SHORT) if (re.test(y)) { y = y.replace(re, to); break; }
      if (y !== x) { td.title = x; td.textContent = y; }
    });
  }

  /* ETF 報酬比較的表：手機只留「名稱＋價格年化＋含息年化」三欄（不橫捲），其餘（期間、殖利率、配息年化）點一列展開在下面；
     展開列裡放「看個股頁 ›」—— 原本「點一列就進個股頁」改成點兩下的路徑，資訊收起來但沒有消失 */
  document.addEventListener('click', (e) => {
    if (!isM()) return;
    const tr = e.target.closest && e.target.closest('#etfRetTbl tbody tr[data-code]'); if (!tr) return;
    e.stopPropagation(); e.preventDefault();
    const nx = tr.nextElementSibling;
    if (nx && nx.classList.contains('m4retx')) { nx.remove(); tr.classList.remove('m4on'); return; }
    const t = tr.closest('table'), heads = $$('thead th', t).map((h) => h.textContent.trim());
    const cells = $$(':scope > td', tr);
    const parts = [1, 4, 5].filter((i) => cells[i]).map((i) => `<span><b>${esc(heads[i] || '')}</b> ${cells[i].innerHTML}</span>`).join('');
    const row = document.createElement('tr'); row.className = 'm4retx';
    row.innerHTML = `<td colspan="${heads.length}"><div class="m4retd">${parts}<a href="#stock/${esc(tr.dataset.code)}">看個股頁 ›</a></div></td>`;
    tr.after(row); tr.classList.add('m4on');
  }, true);

  /* 控制區裡多餘的字（「期間」「加入比較：」「扣除二代健保（…）」）：手機藏起來省寬度。
     用 span 包起來再藏，不用 font-size:0（全站有「字 ≥ 11px」的普查，字級 0 會被當成違規；而且藏的是字不是控制項） */
  function hideLabels() {
    if (!isM()) return;
    $$('#etfRetCtl .rpk label, #etfCmpDD .ddbtn, #v-etf .incctl.m4sel .rpk label, #v-etf .incctl.m4sel label.chk').forEach((el) => {
      [...el.childNodes].forEach((n) => { if (n.nodeType === 3 && n.textContent.trim()) { const sp = document.createElement('span'); sp.className = 'm4tx'; sp.textContent = n.textContent; n.replaceWith(sp); } });
    });
    shortTitles();
  }

  /* 卡片標題太長、「?」被擠到第二行的：手機換一個短標題（原標題包進 .m4tx 藏起來、保留在 DOM 與 title 裡，點「?」的說明一字未改）。
     2026-10-08 CEO 交辦：複利試算的標題在 390 寬（與 iPhone 的蘋方字寬）會把「?」擠成自己一行。 */
  const SHORT_TTL = [['#incPX > .row > h3', '複利試算：配息再投入多賺幾 %']];
  function shortTitles() {
    SHORT_TTL.forEach(([q, short]) => {
      const h = $(q); if (!h || h.querySelector('.m4sh')) return;
      const n = [...h.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim()); if (!n) return;
      const full = n.textContent.trim();
      const sp = document.createElement('span'); sp.className = 'm4tx'; sp.textContent = n.textContent;
      const sh = document.createElement('span'); sh.className = 'm4sh'; sh.textContent = short + ' '; sh.title = full;
      n.replaceWith(sp, sh);
    });
  }

  /* 細節頁的「‹ 返回」（Andy：「這需要附上一個倒退符號」）：題材細節、單一產業鏈、族群頁、個股頁。
     有站內上一頁就 history.back()；直接開網址進來的（沒有上一頁）就回到這個功能的上一層。 */
  let navN = 0;
  window.addEventListener('hashchange', () => { navN++; });
  function parentOf(h) {
    const p = h.replace(/^#/, '').split('/');
    if (p[0] === 'heatmap' && p[1] === 'theme' && p[2]) return '#heatmap/theme';
    if (p[0] === 'industry' && p[1] === 'group' && p[2]) return '#industry';
    if (p[0] === 'industry' && p[1] && p[1] !== 'group') return p[2] ? '#industry/' + p[1] : '#industry';
    if (p[0] === 'stock' && p[1]) return '#industry';
    return null;
  }
  function paintBack() {
    if (!isM()) return;
    const main = $('main'); if (!main) return;
    let bb = $('#m4BackBtn');
    const par = parentOf(location.hash || '');
    if (!par) { if (bb) bb.hidden = true; return; }
    if (!bb) {
      bb = document.createElement('button'); bb.type = 'button'; bb.id = 'm4BackBtn'; bb.className = 'm4back2'; bb.innerHTML = '‹ 返回';
      bb.onclick = () => { const to = parentOf(location.hash || ''); if (navN > 0 && history.length > 1) history.back(); else if (to) location.hash = to; };
    }
    if (bb.parentNode !== main || main.firstChild !== bb) main.insertBefore(bb, main.firstChild);
    bb.hidden = false;
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
      condSelects(ctl);
      function paint() { const t = '條件：' + (condSummary(ctl) || '—'); const want = `<span>${esc(t)}</span><i aria-hidden="true">${ctl.classList.contains('m4open') ? '▴' : '▾'}</i>`; if (b.innerHTML !== want) b.innerHTML = want; }
      paint();
    });
  }

  /* 現金流試算／複利試算的條件區：分段鈕群組一律換成下拉（Andy：「不要換行太多」＋協調者：條件區沒有分段鈕群組、全部是 select 或 checkbox、展開 ≤ 84px）。
     原本的分段鈕留在 DOM 裡（藏起來），下拉改了就去點對應的那顆 —— 狀態與重畫照頁面自己的邏輯走，不另存一份。
     custom＝最後多一個「自訂」選項：沒有任何一顆亮著時選中它，並把 show（自訂金額框／起始日框）顯示出來；其他時候藏起來。 */
  function segSelect(seg, opt) {
    if (!seg) return;
    const bs = $$(':scope > button', seg); if (!bs.length) return;
    let sel = seg.nextElementSibling && seg.nextElementSibling.classList.contains('m4segsel') ? seg.nextElementSibling : null;
    const sig = bs.map((b) => b.textContent.trim() + (b.classList.contains('on') ? '*' : '')).join('|');
    if (sel && sel._sig === sig) return;
    if (!sel) {
      sel = document.createElement('select'); sel.className = 'm4segsel'; sel.setAttribute('aria-label', opt.label || '選擇');
      sel.onchange = () => {
        const cur = $$(':scope > button', seg);
        if (sel.value === 'custom') { if (opt.show) { opt.show.classList.add('m4show'); const i = opt.show.matches('input') ? opt.show : $('input', opt.show); if (i) i.focus(); } return; }
        if (opt.show) opt.show.classList.remove('m4show');
        const b = cur[+sel.value]; if (b) b.click();
      };
      seg.after(sel);
    }
    sel._sig = sig;
    const on = bs.findIndex((b) => b.classList.contains('on'));
    sel.innerHTML = bs.map((b, i) => `<option value="${i}">${esc(b.textContent.replace(/\s+/g, ' ').trim())}</option>`).join('') + (opt.custom ? '<option value="custom">自訂…</option>' : '');
    sel.value = on >= 0 ? String(on) : opt.custom ? 'custom' : '0';
    if (opt.show) opt.show.classList.toggle('m4show', on < 0);
  }
  function condSelects(ctl) {
    ctl.classList.add('m4sel');
    segSelect($('#incMode', ctl), { label: '年領或月領' });
    segSelect($('#incAmtSeg', ctl), { label: '目標金額', custom: true, show: $('#incAmt', ctl) });
    segSelect($('#incScope', ctl), { label: '範圍' });
    segSelect($('#cxQuick', ctl), { label: '起始日', custom: true, show: $('#cxFrom', ctl) });
    const nhi = $('#incNhi', ctl);
    if (nhi && !nhi.parentElement.querySelector('.m4short')) {   // 勾選框的長說明縮成「二代健保」，完整說明留在 title
      const lb = nhi.parentElement; lb.title = lb.textContent.trim(); lb.insertAdjacentHTML('beforeend', '<span class="m4short">扣二代健保</span>');
    }
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
    const subs = N.SUBS[pg] || [];
    if (subs.length) {
      /* 子頁頁籤（底線頁籤）：頁名縮成小字放上面，下面一排頁籤，選中的高亮、自動捲進畫面；放不下時左右拖 */
      const want = `<small class="m4pgn">${esc(P.t)}</small><nav class="m4subtabs" role="tablist">${subs.map((x) => `<button type="button" role="tab" data-h="${x.h}" data-sub="${x.k}" class="${s && s.k === x.k ? 'on' : ''}" aria-selected="${!!(s && s.k === x.k)}">${esc(x.t)}</button>`).join('')}</nav>`;
      if (title.innerHTML !== want) {
        title.innerHTML = want;
        $$('.m4subtabs button', title).forEach((b) => { b.onclick = () => { try { localStorage.setItem('tw.m4.sub.' + pg, b.dataset.h); } catch (e) { /* 私密視窗 */ } if (location.hash !== b.dataset.h) location.hash = b.dataset.h; }; });
      }
      if (s) { try { localStorage.setItem('tw.m4.sub.' + pg, s.h); } catch (e) { /* 私密視窗 */ } }
      const onB = $('.m4subtabs button.on', title), nv = $('.m4subtabs', title);
      if (onB && nv) nv.scrollLeft = Math.max(0, onB.offsetLeft - (nv.clientWidth - onB.offsetWidth) / 2);
      return;
    }
    title.innerHTML = esc(name || brandName());
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
    window.addEventListener('hashchange', () => { close(); [0, 120, 800].forEach((t) => setTimeout(paintTitle, t)); setTimeout(paintBack, 0); });
    paintBack();
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    new MutationObserver(paintTitle).observe(root, { attributes: true, attributeFilter: ['data-l4sub'] });
    // 會員功能晚一步才開（account.js 讀完設定檔）、#acctBtn／#acctOnline 晚一步才建：出現時收進頂欄小圖示列
    new MutationObserver(() => { if (tools && isM()) { const bar = $('.topbar'); const miss = TOOLS.some((q) => { const e = $(q); return e && e.parentNode !== tools; }) || (acctOn() && $('#m4Login')); if (bar && miss) buildTools(bar); } })
      .observe(document.body, { childList: true, subtree: true });
    let ct = 0; new MutationObserver(() => { if (!isM()) return; clearTimeout(ct); ct = setTimeout(() => { wireCond(); wireChainList(); wireEtfTri(); wireIndMap(); wireIncMS(); wireCxMS(); wirePricing(); hideLabels(); }, 120); }).observe(document.body, { childList: true, subtree: true });
    wireCond();
  }
  window.TwM4 = { open, close, isOpen: () => !!(drawer && !drawer.hidden) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

/* ============================================================================
   提示框殘留1009（Andy 2026-10-09 04:2x：「所有分頁會發生當我點擊資訊，他顯示的訊息框會殘留…正常情況是點擊背景會消失」）
   手機沒有滑鼠「離開」這回事：ECharts 的提示框（全站一律 appendToBody，掛在 body 底下）點一下出現之後，
   只有再點同一張圖才會換掉／收掉 —— 點背景、點別張圖、捲頁、換分頁，它都留在原地（現金流試算的時鐘、熱力圖方塊都是）。
   做法（只限 html.m4；桌機有 hover，行為一個字都不動 —— 守門1008）：
     ① document 的 pointerdown（capture 階段先跑，但不攔、不 preventDefault —— 圖上原本的「點選」「點空白處恢復」照舊）：
        按在哪一張圖裡面，那一張交給 ECharts 自己決定（要換成新的提示框）；其他每一張都 hideTip。
     ② 換分頁（hashchange）、整頁捲動超過 24px：全部 hideTip。
     ③ 保險：hideTip 之後，body 底下還看得見的 ECharts 提示框，照 ECharts 自己收起來的樣子藏掉
        （換頁時舊頁的圖可能已經被 dispose 或藏起來，dispatchAction 叫不到它）；下一次 ECharts 要顯示時會整段蓋掉這兩個樣式。
     「?」說明（#howPop）與點了才出現的面板（app.js dismissable）原本就會點背景關、換頁關，這裡不重做。
   ============================================================================ */
(function () {
  'use strict';
  const isM4 = () => document.documentElement.classList.contains('m4');
  const TIP_Z = '9999999';   // ECharts 提示框的 z-index（appendToBody 的那一層 div）
  const isTipDiv = (d) => !!d && d.parentElement === document.body && d.tagName === 'DIV' && d.style && d.style.zIndex === TIP_Z;
  function hideTips(keep) {
    if (window.echarts) {
      document.querySelectorAll('[_echarts_instance_]').forEach((el) => {
        if (keep && el.contains(keep)) return;
        let c = null; try { c = echarts.getInstanceByDom(el); } catch (e) { /* 已經 dispose */ }
        if (!c || (c.isDisposed && c.isDisposed())) return;
        try { c.dispatchAction({ type: 'hideTip' }); } catch (e) { /* 這張沒有 tooltip 元件 */ }
      });
    }
    if (keep) return;   // 按在某張圖裡：那一張的提示框正要換成新的，不做保險清除
    for (const d of document.body.children) {
      if (!isTipDiv(d)) continue;
      const cs = getComputedStyle(d);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
      d.style.visibility = 'hidden'; d.style.opacity = '0';
    }
  }
  document.addEventListener('pointerdown', (e) => {
    if (!isM4()) return;
    const t = e.target;
    if (!t || !t.closest) return;
    for (let n = t; n && n !== document.body; n = n.parentElement) if (isTipDiv(n)) return;   // 按在提示框本身：不動
    hideTips(t.closest('[_echarts_instance_]'));
  }, true);
  window.addEventListener('hashchange', () => { if (isM4()) hideTips(null); });
  let y0 = window.scrollY;
  window.addEventListener('scroll', () => {
    if (!isM4()) { y0 = window.scrollY; return; }
    if (Math.abs(window.scrollY - y0) < 24) return;
    y0 = window.scrollY;
    hideTips(null);
  }, { passive: true });
  window.TwM4Tips = { hide: () => hideTips(null) };
})();
