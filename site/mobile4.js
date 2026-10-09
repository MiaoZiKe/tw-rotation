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
  /* ★ 2026-10-09（Andy：「手機…產業地圖點擊都會卡頓沒反應」）：以前每次都讀 window.innerWidth。
     底下兩支掛在 body 上的 MutationObserver 每一批 DOM 變動都會呼叫 isM()，畫面剛被改過時讀 innerWidth 會逼瀏覽器先排版一次
     （CPU profile 裡 isM 自己就佔 0.3～0.6 秒）。改用 matchMedia 的結果（跟 innerWidth ≤ 640 同一條界線，含捲軸寬），不必排版。 */
  const mqM = window.matchMedia ? window.matchMedia('(max-width: ' + MAX + 'px)') : null;
  const isM = () => (mqM ? mqM.matches : window.innerWidth <= MAX);
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
        rows.push(`<button type="button" class="m4item${on ? ' on' : ''}" data-h="${href}" data-v="${v}" title="${esc(P.t)}">${mi(v)}<span>${esc(P.t)}</span></button>`);
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
      swipeClose(drawer, 'left', close);   // 2026-10-09（Andy：「兩邊側邊欄位都具備可以左右滑動收起功能」）
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
    root.removeAttribute('data-m4flat');
    document.querySelectorAll('.m4sep,.m4sepb,.m4seg,.m4bleed').forEach((e) => e.classList.remove('m4sep', 'm4sepb', 'm4seg', 'm4bleed', 'm4end'));
    close();
    restoreTools();
    [burger, drawer, back, title].forEach((e) => { if (e) e.remove(); });
    burger = drawer = back = title = null;
    document.body.classList.remove('m4lock');
  }


  /* 2026-10-09（Andy：「並且兩邊側邊欄位都具備可以左右滑動收起功能」）：左側選單往左滑、右側今日事件往右滑就收起。
     抽屜跟著手指走；放開時拖超過抽屜寬 30%，或甩得夠快（≥ 0.5px/ms 且拖了 30px 以上）就關，否則彈回。
     先判主方向（動了 8px 之後：水平量 > 垂直量 ×1.2 才算左右滑），抽屜裡上下捲清單不會被當成要關；
     CSS 給兩個抽屜 touch-action:pan-y（mobile4.css 第 3 節），上下捲交給瀏覽器、左右交給這裡。只在手機（html.m4）作用。 */
  function swipeClose(el, dir, onClose) {
    if (!el || el._m4swipe) return; el._m4swipe = 1;
    let x0 = 0, y0 = 0, t0 = 0, mode = null, off = 0;
    const sign = dir === 'left' ? -1 : 1;
    const reset = (anim) => { el.style.transition = anim ? 'transform .2s ease-out' : ''; el.style.transform = ''; if (anim) setTimeout(() => { el.style.transition = ''; }, 220); };
    el.addEventListener('touchstart', (e) => { if (!isM() || e.touches.length !== 1) { mode = 'x'; return; } const t = e.touches[0]; x0 = t.clientX; y0 = t.clientY; t0 = Date.now(); mode = null; off = 0; }, { passive: true });
    el.addEventListener('touchmove', (e) => {
      if (mode === 'x' || mode === 'v') return;
      const t = e.touches[0], dx = t.clientX - x0, dy = t.clientY - y0;
      if (!mode) { if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return; mode = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v'; if (mode === 'v') return; }
      off = sign < 0 ? Math.min(0, dx) : Math.max(0, dx);
      el.style.transition = 'none'; el.style.transform = `translateX(${off}px)`;
    }, { passive: true });
    const end = () => {
      if (mode !== 'h') { mode = null; return; }
      mode = null;
      const w = el.getBoundingClientRect().width || 1, dist = Math.abs(off), v = dist / Math.max(1, Date.now() - t0);
      if (dist > w * 0.3 || (v >= 0.5 && dist > 30)) { el.style.transition = ''; el.style.transform = ''; onClose(); }
      else reset(true);
    };
    el.addEventListener('touchend', end, { passive: true });
    el.addEventListener('touchcancel', () => { if (mode === 'h') reset(true); mode = null; }, { passive: true });
  }

  /* ---------------- 頂欄右邊的小圖示（全部是「搬節點」：id、onclick 都是原本那顆，跟電腦版 layout4.js syncTools 同一套） ----------------
     順序同電腦版頁首右上：明暗（#themeBtn）→ 版面風格（#t4Btn）→ 平台導覽（#twPageTourBtn）→ 在線（#acctOnline）→ 登入（#acctBtn）。
     會員功能沒開時沒有 #acctBtn：放一顆 #m4Login，講清楚為什麼不能登入（同電腦版 #l4Login 的字）。
     搜尋收進抽屜最上面的「搜尋」；「⋯」選單拿掉（裡面的今日事件、自選都在抽屜）。 */
  const TOOLS = ['#m4Search', '#themeBtn', '#t4Btn', '#twPageTourBtn', '#acctOnline', '#acctBtn', '#m4Login'];   // 2026-10-09 Andy：「把明暗功能分出來」→ #themeBtn 在頂欄看得到（調色盤左邊，同網頁版）
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
  /* ★ 2026-10-09（Andy：「像這類型 子分頁裡面還有的 就用分頁形式表示……並且需要平均分散分頁寬度 填滿左右」）：
     子頁裡面還有第二層切換（整塊內容換掉的那種）的，手機一律攤平成上方同一排頁籤，第二層那排藏起來（電腦版側欄與頁面一個字都沒動）。
     普查（402 寬、10-09）三處：
       資金流向「族群×法人＋集中度」裡的「法人｜集中度」 → 資金輪動｜資金分流樹｜族群×法人｜集中度
       熱力圖「題材」裡的「題材熱力｜題材細節」          → 產業｜題材｜題材細節
       ETF「現金流試算」裡的「月配試算表｜複利試算表」    → 配息行事曆｜ETF 總覽｜月配試算｜複利試算
     名稱對照網頁版：「族群×法人」「集中度」＝網頁版側欄「族群×法人＋集中度」那一頁的上下兩塊；「月配試算」「複利試算」＝網頁版頁內的「月配試算表／複利試算表」。
     每一格有自己的網址（上一頁／下一頁鍵、分享連結都對）：第二層用網址尾巴分（#flow/inst/conc、#heatmap/theme/<題材>、#etf/inc/cx），
     app.js route() 只看第一層（rest[0]），尾巴不影響它；第二層那排鈕還在 DOM 裡，切換交給它自己（syncFlat 去按它，記憶、延後畫圖都照舊）。 */
  const FLAT = {
    flow: [
      { k: 'flow-rotation', h: '#flow/rotation', t: '資金輪動', m: /^#flow(\/rotation)?\/?$/ },
      { k: 'flow-sankey', h: '#flow/sankey', t: '資金分流樹', m: /^#flow\/sankey/ },
      { k: 'flow-inst', h: '#flow/inst', t: '族群×法人', m: /^#flow\/inst\/?$/, ctl: '#v-flow>.mpager', seg: '法人' },
      { k: 'flow-conc', h: '#flow/inst/conc', t: '集中度', m: /^#flow\/inst\/conc/, ctl: '#v-flow>.mpager', seg: '集中度' },
    ],
    heatmap: [
      { k: 'heat-industry', h: '#heatmap/industry', t: '產業', m: /^#heatmap(\/industry)?\/?$/ },
      { k: 'heat-theme', h: '#heatmap/theme', t: '題材', m: /^#heatmap\/theme\/?$/, ctl: '#v-heatmap>.mpager', seg: '題材熱力' },
      { k: 'heat-detail', h: '', t: '題材細節', m: /^#heatmap\/theme\/[^/]+/, ctl: '#v-heatmap>.mpager', seg: '題材細節' },
    ],
    etf: [
      { k: 'etf-cal', h: '#etf/cal', t: '配息行事曆', m: /^#etf\/cal/ },
      { k: 'etf-list', h: '#etf/list', t: 'ETF 總覽', m: /^#etf(\/list)?\/?$/ },
      { k: 'etf-inc', h: '#etf/inc', t: '月配試算', m: /^#etf\/inc\/?$/, ctl: '#incMain', seg: 'm' },
      { k: 'etf-cx', h: '#etf/inc/cx', t: '複利試算', m: /^#etf\/inc\/cx/, ctl: '#incMain', seg: 'x' },
    ],
  };
  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } };
  /* 題材細節那格：回到上次看的題材；沒看過就用 '_'（app.js renderThemeDetail 找不到 id 時畫第一個題材） */
  function flatHref(x) { return x.k === 'heat-detail' ? '#heatmap/theme/' + (lsGet('tw.m4.theme') || '_') : x.h; }
  function flatCur(pg) { const L = FLAT[pg], h = location.hash || ''; return L ? (L.find((x) => x.m.test(h)) || null) : null; }
  /* 第二層：按藏起來的那排鈕，讓它切到網址說的那一格（狀態已經對就什麼都不做） */
  function syncFlat() {
    if (!isM()) return;
    const pg = curPage(), x = flatCur(pg);
    root.toggleAttribute('data-m4flat', !!FLAT[pg]);
    const mt = /^#heatmap\/theme\/([^/]+)/.exec(location.hash || ''); if (mt && mt[1] !== '_') lsSet('tw.m4.theme', decodeURIComponent(mt[1]));
    if (!x || !x.ctl) { flatDone = true; return; }
    const ctl = $(x.ctl); if (!ctl) return;          // 第二層那排還沒長出來（資料晚到）：下一輪再試
    flatDone = true;
    const b = $$('button', ctl).find((e) => (x.ctl === '#incMain' ? e.dataset.v === x.seg : e.textContent.trim().startsWith(x.seg)));
    if (b && !(b.classList.contains('on') || b.getAttribute('aria-selected') === 'true')) b.click();
  }
  /* 反方向：第二層那排被直接按了（例如驗收或導覽用程式去按它），網址與上方頁籤跟著它走（replaceState，不多一筆歷史）。
     換網址之後要等 syncFlat 先把第二層按到位（flatDone）才開始跟，不然兩邊會互相拉扯 */
  let flatDone = false;
  function flatFollow() {
    if (!isM() || !flatDone) return;
    const pg = curPage(), L = FLAT[pg], x = flatCur(pg); if (!L || !x || !x.ctl) return;
    const ctl = $(x.ctl); if (!ctl) return;
    const on = $$('button', ctl).find((e) => e.classList.contains('on') || e.getAttribute('aria-selected') === 'true'); if (!on) return;
    const y = L.find((z) => z.ctl === x.ctl && (x.ctl === '#incMain' ? on.dataset.v === z.seg : on.textContent.trim().startsWith(z.seg)));
    if (y && y !== x) { history.replaceState(history.state, '', flatHref(y)); paintTitle(); }
  }

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
    const flat = FLAT[pg], fx = flat ? flatCur(pg) : null;
    const subs = flat ? flat.map((x) => ({ k: x.k, h: flatHref(x), t: x.t })) : (N.SUBS[pg] || []);
    const onK = flat ? (fx && fx.k) : (s && s.k);
    if (subs.length) {
      /* 子頁頁籤（底線頁籤）：頁名縮成小字放上面，下面一排頁籤，選中的高亮；2026-10-09 起每格等寬填滿左右（mobile4.css 第 18 節），不橫捲 */
      const want = `<small class="m4pgn">${esc(P.t)}</small><nav class="m4subtabs n${subs.length}" role="tablist">${subs.map((x) => `<button type="button" role="tab" data-h="${x.h}" data-sub="${x.k}" class="${onK === x.k ? 'on' : ''}" aria-selected="${onK === x.k}" title="${esc(x.t)}">${esc(x.t)}</button>`).join('')}</nav>`;
      if (title.innerHTML !== want) {
        title.innerHTML = want;
        $$('.m4subtabs button', title).forEach((b) => { b.onclick = () => { if (location.hash !== b.dataset.h) location.hash = b.dataset.h; else syncFlat(); }; });
      }
      // 抽屜「上次看的子頁」記的是側欄那一份（N.SUBS）的網址：攤平出來的第二層記成它所屬的那一頁
      if (s) lsSet('tw.m4.sub.' + pg, s.h);
      const onB = $('.m4subtabs button.on', title), nv = $('.m4subtabs', title);
      if (onB && nv) nv.scrollLeft = Math.max(0, onB.offsetLeft - (nv.clientWidth - onB.offsetWidth) / 2);
      return;
    }
    title.innerHTML = esc(name || brandName());
  }

  /* 2026-10-09（Andy：「所有大功能需要用線條分開」，延伸 10-08「原本每個功能底下的大方格需要取消，直接用線條區分」）：
     每一頁最上層的大區塊（.view.on 的直接子元素、看得到、高 ≥ 24）之間一律一條全寬 1px 分隔線（class m4sep，樣式在 mobile4.css 第 29 節）。
     規則：第一塊不畫；緊跟在「切換列」（分段控制器、頁籤）後面的那塊不畫 —— 切換列跟它控制的內容是同一件事，線畫在切換列上面。
     哪一塊看得到會跟著分段切換、資料晚到而變，所以掛在 main 的變動上（節流 200ms），只在狀態真的不同時才改 class（不自己觸發自己） */
  const CTL = '.mpager,.m4subtabs,.mspine,[role=tablist],.seg,.nbsw,.mseg,.chainsw';
  /* 高度一律扣掉自己加上去的線與內距（.m4sep／.m4sepb 各 1px 線＋12px 內距）再判斷 —— 不扣的話標上線之後高度變了、判斷翻轉、下一輪又拿掉，
     class 來回跳，版面跟著上下抖（10-09 實測：捲到頂之後 scrollY 還被拉走 68px） */
  const hOf = (e) => e.getBoundingClientRect().height - (e.classList.contains('m4sep') ? 13 : 0) - (e.classList.contains('m4sepb') ? 13 : 0);
  const isCtl = (e) => e.matches(CTL) || (!!e.querySelector(CTL) && hOf(e) <= 64);
  function markSeps() {
    if (!isM()) return;
    const view = $('main .view.on'); if (!view) return;
    const kids = [...view.children].filter((e) => e.getClientRects().length && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height >= 24);
    // 線要畫在 kids[i] 上面：一般區塊用它自己的上框（.m4sep）；切換列本身有膠囊外框、又會橫捲（偽元素會被裁掉），改畫在上一塊的下框（.m4sepb）
    const top = new Set(), bot = new Set();
    // 上一塊是矮的頁首／說明條（高 < 80、不是切換列，例如選股策略的標題說明、總覽最上面那排指數）：它跟下一塊是同一件事的開頭，不另畫線
    kids.forEach((e, i) => { if (i === 0) return; const prev = kids[i - 1]; if (isCtl(prev) && !isCtl(e)) return;
      if (!isCtl(prev) && hOf(prev) < 80) return; if (isCtl(e)) bot.add(prev); else top.add(e); });
    const put = (cls, want) => { $$('.' + cls, document).forEach((e) => { if (!want.has(e)) e.classList.remove(cls); }); want.forEach((e) => { if (!e.classList.contains(cls)) e.classList.add(cls); }); };
    put('m4sep', top); put('m4sepb', bot);
    // 頁內切換一律同一款分段控制器（mobile4.css 第 23 節）：掛同一個 class，驗收與之後的樣式都認它
    $$(SEGSEL).forEach((e) => { if (!e.classList.contains('m4seg')) e.classList.add('m4seg'); });
    markBleed();
  }
  /* 2026-10-09（Andy：「左右滑可以拓寬」）：一排放不下、要左右滑的列（分段控制器、個股工具列、剖析圖工具列）拓寬成滿版 ——
     左右貼齊螢幕邊、第一項與最後一項用內距對齊內容邊（mobile4.css 第 30 節 .m4bleed），右緣淡出暗示還能滑、滑到底淡出收掉（.m4end）。
     判斷「放不下」量的是內容本身的寬度（第一項左緣到最後一項右緣）對上「沒拓寬時」的可用寬度，拓寬前後判斷結果一樣，不會來回跳 */
  const BLEED = '.m4seg, #skTools, #dgTools';
  function markBleed() {
    $$(BLEED).forEach((e) => {
      if (!e.closest('.view.on') || !e.getClientRects().length) return;
      if (e.id === 'mktSeg2') return;   // 市場明細頂部四頁籤是等寬底線分頁（第 29 節），本來就填滿、不橫捲，不拓寬
      const kids = [...e.children].filter((k) => k.getClientRects().length && getComputedStyle(k).position !== 'absolute');
      if (kids.length < 2) return;
      const need = kids[kids.length - 1].offsetLeft + kids[kids.length - 1].offsetWidth - kids[0].offsetLeft;
      const par = e.parentElement, pcs = getComputedStyle(par);
      const avail = par.clientWidth - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight) - 8;
      // 自己獨佔一列、從父層內容的左緣開始的才拓寬（夾在一排東西中間的不動，免得把旁邊的擠掉）
      const pr = par.getBoundingClientRect(), cl = pr.left + parseFloat(pcs.paddingLeft) + par.clientLeft, cr = cl + par.clientWidth - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight);
      const sib = [...par.children].some((k) => k !== e && k.getClientRects().length && getComputedStyle(k).position !== 'absolute' && Math.abs(k.getBoundingClientRect().top - e.getBoundingClientRect().top) < 4 && k.getBoundingClientRect().height > 4);
      const on = need > avail && !sib;
      if (on) {
        // 量父層內容框到螢幕左右邊的距離（用 clientWidth＝版面寬，不用 100vw：手機模式下頁面一變寬 100vw 會跟著變大，越拓越寬）
        const L = Math.max(0, Math.round(cl)), R = Math.max(0, Math.round(root.clientWidth - cr));
        if (e.style.getPropertyValue('--m4bl') !== L + 'px') e.style.setProperty('--m4bl', L + 'px');
        if (e.style.getPropertyValue('--m4br') !== R + 'px') e.style.setProperty('--m4br', R + 'px');
        const W = root.clientWidth + 'px'; if (e.style.getPropertyValue('--m4bw') !== W) e.style.setProperty('--m4bw', W);   // 寬度直接給 px（給百分比會跟父層互相撐大：父層寬度又是看子元素算的）
      }
      if (on !== e.classList.contains('m4bleed')) e.classList.toggle('m4bleed', on);
      if (on && !e._m4s) { e._m4s = 1; e.addEventListener('scroll', () => bleedEnd(e), { passive: true }); }
      if (on) bleedEnd(e);
    });
  }
  function bleedEnd(e) { const end = e.scrollLeft + e.clientWidth >= e.scrollWidth - 4; if (end !== e.classList.contains('m4end')) e.classList.toggle('m4end', end); }
  const SEGSEL = '.view.on :is(.seg,.nbsw,.mpager,.mseg,[role=tablist]):not(.m4subtabs):not(#mbTabs):not(.hmbar)';
  let sepT = 0, sepLast = 0;
  function sepSoon() { if (sepT) return; const wait = Math.max(0, 200 - (Date.now() - sepLast)); sepT = setTimeout(() => { sepT = 0; sepLast = Date.now(); if (flatDone) flatFollow(); else syncFlat(); markSeps(); }, wait); }

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
    // ★ 2026-10-09：一幀最多檢查一次（以前每一批 DOM 變動都跑一次 7 個 querySelector；進族群頁會連續來幾十批）
    let tr = 0;
    new MutationObserver(() => { if (tr || !tools || !isM()) return; tr = requestAnimationFrame(() => { tr = 0; if (!tools || !isM()) return; const bar = $('.topbar'); const miss = TOOLS.some((q) => { const e = $(q); return e && e.parentNode !== tools; }) || (acctOn() && $('#m4Login')); if (bar && miss) buildTools(bar); }); })
      .observe(document.body, { childList: true, subtree: true });
    let ct = 0; new MutationObserver(() => { if (!isM()) return; clearTimeout(ct); ct = setTimeout(() => { wireCond(); wireChainList(); wireEtfTri(); wireIndMap(); wireIncMS(); wireCxMS(); wirePricing(); hideLabels(); }, 120); }).observe(document.body, { childList: true, subtree: true });
    wireCond();
    { const mn = $('main'); if (mn) new MutationObserver(sepSoon).observe(mn, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'hidden', 'style'] }); }
    window.addEventListener('hashchange', () => { flatDone = false; [0, 300, 1200].forEach((t) => setTimeout(() => { if (!flatDone) syncFlat(); markSeps(); }, t)); });
    window.addEventListener('resize', sepSoon);
    [0, 600, 1400].forEach((t) => setTimeout(() => { if (!flatDone) syncFlat(); markSeps(); }, t));
    swipeClose($('#side'), 'right', () => { if (window.twSetSide) window.twSetSide(false); });   // 右側今日事件：往右滑收起
  }
  window.TwM4 = { open, close, isOpen: () => !!(drawer && !drawer.hidden) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

/* ============================================================================
   ★ 29. 市場明細（#market）手機版（2026-10-09 Andy 06:1x，附三張截圖）
   Andy 原話：「上方全部改用分頁呈現／漲跌家數分上 長條圖 下清單 並且都是分段式控制／
              法人連續買賣超也是分段式控制以及下拉清單／站上均線也是分段式控制以及下拉清單／
              下方的方格圖 需要依據清單篩選，有幾個分類就做幾個收合 Default 是收狀態，並且紅框是清單式篩選／
              今日關注 正常表清單形式 控制好範圍調整適當大小」
   只在 html.m4（≤640）動；桌機那條路徑（app.js drawMarket）一行沒改。樣式在 mobile4.css 第 29 節。
     · 頂部四顆子頁（#mktSeg2）→ 等寬底線分頁（純 CSS）；mobile3.js 的第二層「分佈圖／名單」藏掉，圖與清單同頁上下排。
     · 漲跌家數清單的五顆分頁（#mktTabs）：手機換短名「漲停／跌停／漲幅／跌幅／成交值」，檔數疊在下面一行（原名留在 title）。
     · 站上均線：ECharts 圖例（43 個族群、分頁 1/43）手機不畫，改由既有的「族群」下拉多選（App.msDD）決定畫哪幾條；
       下方族群方格依產業鏈分成收合段，預設全收（只有一段時直接展開），並跟著同一份下拉清單篩選。
     · 今日關注：表格只留「股票／判定／漲跌／收盤」，族群與綜合分點一列展開在下面（同 ETF 報酬比較表的做法）。
   觸發：只觀察 #v-market 這一塊（節流 120ms）；⚠ 不在 body 上掛 MutationObserver（另一條分支正在收斂那幾個）。
   ============================================================================ */
(function () {
  'use strict';
  const MAX = 640;
  const root = document.documentElement;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const isM = () => window.innerWidth <= MAX && root.classList.contains('m4');
  const kindNow = () => { const b = $('#mktSeg2 button.on'); return (b && b.dataset.k) || ((location.hash || '').split('/')[1]) || 'updown'; };
  const CHAIN = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', software: '軟體與資訊服務', financial: '金融',
    traditional: '傳產', infrastructure: '基礎建設', industry: '法定產業別', _other: '其他族群' };
  const CHAIN_ORDER = Object.keys(CHAIN);
  /* 收合段的開關只記在這一次開頁裡（Andy 10-04：市場明細的設定切分頁、離開再回來一律回預設，所以不寫 localStorage） */
  const OPEN = new Map();
  let chainOf = null;   // group_id → chain（groups_today）

  /* 按鈕文字換短名：原字包進 .m4tx（手機藏、桌機顯示），短名放 .m4sh（只在手機顯示）；原名留在 title */
  function shortBtn(b, short) {
    if (b.querySelector('.m4sh')) return;
    const n = [...b.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim()); if (!n) return;
    const tx = document.createElement('span'); tx.className = 'm4tx'; tx.textContent = n.textContent;
    const sh = document.createElement('span'); sh.className = 'm4sh'; sh.textContent = short;
    if (!b.title) b.title = n.textContent.trim();
    n.replaceWith(tx, sh);
  }
  const LIST_SHORT = { '漲停': '漲停', '跌停': '跌停', '漲幅前段': '漲幅', '跌幅前段': '跌幅', '成交值前段': '成交值' };
  function wireUpdown() {
    $$('#mktTabs > button').forEach((b) => {
      const t = [...b.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim());
      if (t && LIST_SHORT[t.textContent.trim()]) shortBtn(b, LIST_SHORT[t.textContent.trim()]);
    });
  }

  /* ---- 站上均線：圖例不畫（改由下拉清單挑線）---- */
  function hideLegendOpt(o) {
    if (!o || !o.legend || Array.isArray(o.legend)) return o;
    const g = o.grid && !Array.isArray(o.grid) ? Object.assign({}, o.grid, { top: 14 }) : o.grid;
    return Object.assign({}, o, { legend: Object.assign({}, o.legend, { show: false }), grid: g });
  }
  function wireMaLegend() {
    const el = $('#maTrend'); if (!el || typeof echarts === 'undefined') return;
    const ci = echarts.getInstanceByDom(el); if (!ci || ci.isDisposed()) return;
    if (!ci._m4leg) {
      const raw = ci.setOption.bind(ci);
      ci.setOption = (o, ...r) => raw(isM() ? hideLegendOpt(o) : o, ...r);
      ci._m4leg = raw;
    }
    const op = ci.getOption(), lg = op && op.legend && op.legend[0];
    if (isM() && lg && lg.show !== false) ci._m4leg({ legend: { show: false }, grid: { top: 14 } });
  }
  /* 下拉裡勾了哪幾個族群（App.msDD 的勾選框，data-n＝族群名）；沒勾＝不篩 */
  function maPicked() { return new Set($$('#maGroupDD .ddlist input[type=checkbox]:checked').map((c) => c.dataset.n)); }
  const cardName = (c) => { const n = $('.n', c); if (!n) return ''; const w = $('.m4nm', n); if (w) return w.textContent.trim();
    const t = [...n.childNodes].find((x) => x.nodeType === 3); return t ? t.textContent.trim() : ''; };
  /* 兩欄卡片的族群名太長時截斷（…）：把名字那段文字包進 span 才截得動；拆收合段時還原成原本的文字節點 */
  function wrapName(c) {
    const n = $('.n', c); if (!n || $('.m4nm', n)) return;
    const t = [...n.childNodes].find((x) => x.nodeType === 3 && x.textContent.trim()); if (!t) return;
    const sp = document.createElement('span'); sp.className = 'm4nm'; t.replaceWith(sp); sp.appendChild(t);
  }
  function unwrapName(c) { const w = $('.n .m4nm', c); if (w) w.replaceWith(...w.childNodes); }

  /* ---- 站上均線：族群方格 → 依產業鏈收合段 ---- */
  let foldBusy = false;
  function wireMaFolds() {
    const grid = $('#mktBody > .magrid'); if (!grid) return;
    if (!chainOf) {
      if (!window.App || !window.App.load || foldBusy) return;
      foldBusy = true;
      Promise.resolve(window.App.load('groups_today', { fallback: [] })).then((gt) => {
        chainOf = {}; (gt || []).forEach((g) => { if (g && g.group_id) chainOf[g.group_id] = g.chain || '_other'; });
      }).catch(() => { chainOf = {}; }).then(() => { foldBusy = false; if (isM()) wireMaFolds(); });
      return;
    }
    let wrap = grid.nextElementSibling && grid.nextElementSibling.classList.contains('m4mafolds') ? grid.nextElementSibling : null;
    if (!wrap) {
      const cards = $$(':scope > .ma[data-gid]', grid); if (!cards.length) return;
      const by = {};
      cards.forEach((c) => { const ch = chainOf[c.dataset.gid] || '_other'; (by[ch] = by[ch] || []).push(c); if (!c.title) c.title = cardName(c); wrapName(c); });
      const rank = (k) => { const i = CHAIN_ORDER.indexOf(k); return i < 0 ? 99 : i; };
      const order = Object.keys(by).sort((a, b) => rank(a) - rank(b));
      wrap = document.createElement('div'); wrap.className = 'm4mafolds'; wrap._cards = cards;
      order.forEach((ch) => {
        const hd = document.createElement('button'); hd.type = 'button'; hd.className = 'm4fold'; hd.dataset.ch = ch;
        const box = document.createElement('div'); box.className = 'magrid m4fbox'; box.dataset.ch = ch;
        by[ch].forEach((c) => box.appendChild(c));
        hd.onclick = () => { OPEN.set(ch, box.hidden); paintFolds(); };
        wrap.append(hd, box);
      });
      grid.hidden = true; grid.after(wrap);
    }
    paintFolds();
  }
  function paintFolds() {
    const wrap = $('#mktBody .m4mafolds'); if (!wrap) return;
    const pick = maPicked();
    const hds = $$(':scope > .m4fold', wrap);
    let shown = 0;
    hds.forEach((hd) => {
      const box = hd.nextElementSibling; let n = 0;
      $$(':scope > .ma', box).forEach((c) => { const on = !pick.size || pick.has(cardName(c)); if (c.hidden === on) c.hidden = !on; if (on) n++; });
      hd._n = n; if (n) shown++;
      if (hd.hidden !== !n) hd.hidden = !n;
    });
    hds.forEach((hd) => {
      const box = hd.nextElementSibling;
      const open = !!hd._n && (shown === 1 ? true : !!OPEN.get(hd.dataset.ch));
      if (box.hidden !== !open) box.hidden = !open;
      if (!hd._n) return;
      const want = `<span>${esc(CHAIN[hd.dataset.ch] || hd.dataset.ch)}</span><small>${hd._n} 個族群${pick.size ? '（已篩選）' : ''}</small><i aria-hidden="true">${open ? '▾' : '▸'}</i>`;
      if (hd.innerHTML !== want) hd.innerHTML = want;
      hd.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  function unFolds() {
    $$('#mktBody .m4mafolds').forEach((w) => {
      const grid = w.previousElementSibling;
      if (grid && grid.classList.contains('magrid')) { (w._cards || []).forEach((c) => { c.hidden = false; if (c.title === cardName(c)) c.removeAttribute('title'); unwrapName(c); grid.appendChild(c); }); grid.hidden = false; }
      w.remove();
    });
  }

  function wire() {
    if (!isM() || !/^#market(\/|$)/.test(location.hash || '')) return;
    const k = kindNow();
    if (k === 'updown') wireUpdown();
    if (k === 'ma') { wireMaLegend(); wireMaFolds(); }
  }

  /* 今日關注表：點一列展開「族群、綜合分」與「看個股頁 ›」（原本點一列直接進個股頁 → 改成兩步，資訊收起來沒有消失） */
  document.addEventListener('click', (e) => {
    if (!isM() || kindNow() !== 'cand') return;
    const tr = e.target.closest && e.target.closest('#v-market #mktBody tbody tr[data-code]'); if (!tr) return;
    e.stopPropagation(); e.preventDefault();
    const nx = tr.nextElementSibling;
    if (nx && nx.classList.contains('m4retx')) { nx.remove(); tr.classList.remove('m4on'); return; }
    const t = tr.closest('table'), heads = $$('thead th', t).map((h) => h.textContent.trim());
    const cells = $$(':scope > td', tr);
    const parts = [1, 3].filter((i) => cells[i]).map((i) => `<span><b>${esc(heads[i] || '')}</b> ${cells[i].innerHTML}</span>`).join('');
    const row = document.createElement('tr'); row.className = 'm4retx';
    row.innerHTML = `<td colspan="${heads.length}"><div class="m4retd">${parts}<a href="#stock/${esc(tr.dataset.code)}">看個股頁 ›</a></div></td>`;
    tr.after(row); tr.classList.add('m4on');
  }, true);

  let tm = 0;
  function kick() { clearTimeout(tm); tm = setTimeout(wire, 120); }
  function init() {
    const v = $('#v-market'); if (!v) return;
    // 只看 #v-market 這一塊（drawMarket 每次整塊換 #mktBody、msDD 每次重寫清單、ECharts 第一次建立畫布都會進來）
    new MutationObserver(() => { if (isM()) kick(); }).observe(v, { childList: true, subtree: true });
    // 下拉清單勾選／全選／全不選：方格跟著重篩（msDD 會重寫清單 → 上面的觀察者也會進來，這裡是保險）
    v.addEventListener('change', (e) => { if (isM() && e.target.closest && e.target.closest('#maGroupDD')) setTimeout(paintFolds, 0); });
    let wasM = isM(), rt = 0;
    window.addEventListener('resize', () => {
      clearTimeout(rt); rt = setTimeout(() => {
        const m = isM(); if (m === wasM) return; wasM = m;
        if (!m) {     // 拉寬回桌機：拆掉收合段、讓 drawMarket 重畫一次（圖例回來）
          unFolds();
          if (/^#market(\/|$)/.test(location.hash || '')) window.dispatchEvent(new HashChangeEvent('hashchange'));
        } else kick();
      }, 200);
    });
    window.addEventListener('hashchange', kick);
    kick();
  }
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

/* ============================================================================
   ★ 31. 市場明細三頁的多組切換 → 一顆摘要鈕＋底部抽屜（2026-10-09，帳本 38 退件）
   照週期統計範本（第 C 段 m3／週期統計）：一顆摘要鈕 → 底部抽屜 → 每組一排分段控制器。只有一組的頁不收。
     · 漲跌家數：市場（全部／上市／上櫃）＋ ETF（不含／含）＋ 族群
     · 法人連買賣：畫法（排行／四象限，main 79c69fd8 新增的 #streakView）＋ 法人（投信／外資／合計）＋ 天數（≥2～≥12 天；原本是下拉 → 抽屜裡改成分段）
     · 站上均線：均線期間（5～240 日）＋ 族群
   做法：抽屜裡的分段鈕是「代理」—— 點一顆＝去按頁面上原本那顆（或改原本那個下拉／勾選再發 change），
   邏輯只有 app.js 那一份；族群是 43 個選項的可搜尋多選，放不進一排分段 → 把頁面上**同一個節點**搬進抽屜，關抽屜搬回去。
   app.js 換條件時會整塊重畫（例：勾含 ETF → drawMarket 重建 #distFilter），所以每次點完都重新對一次「頁面上最新的那個節點」。
   頁面上原本那幾組在手機藏起來（mobile4.css 第 31 節），桌機一行沒動；頂部四格頁籤（#mktSeg2）不碰。
   ============================================================================ */
(function () {
  'use strict';
  const root = document.documentElement;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const isM = () => window.innerWidth <= 640 && root.classList.contains('m4');
  const onMarket = () => /^#market(\/|$)/.test(location.hash || '');
  const kindNow = () => { const b = $('#mktSeg2 button.on'); return (b && b.dataset.k) || ((location.hash || '').split('/')[1]) || 'updown'; };
  const ICON = '<svg class="m4sico" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4"/></svg>';
  const sheetEl = () => $('#mSheet');
  /* 頁面上（不在抽屜裡）的那一個：app.js 重畫後同一個 id 可能一個在抽屜（舊的）、一個在頁面（新的）*/
  const live = (sel) => $$(sel).find((e) => !e.closest('.msheet')) || null;
  const ddText = (host) => { const b = host && $('button', host); return b ? b.textContent.replace(/[▾▸]/g, '').replace(/^族群[:：]\s*/, '').trim() : ''; };

  /* 每一頁：anchor＝摘要鈕插在誰前面；rows＝抽屜裡每一排；move＝要整個搬進抽屜的節點；sum＝摘要字 */
  const CFG = {
    updown: {
      title: '漲跌分佈設定',
      anchor: () => live('#distFilter'),
      rows: () => {
        const mk = live('#distMkt'), etf = live('#distEtf');
        return [
          mk && { k: 'mkt', lbl: '市場', items: $$('button', mk).map((b) => [b.dataset.m, b.textContent.trim(), b.classList.contains('on')]) },
          etf && { k: 'etf', lbl: 'ETF', items: [['0', '不含 ETF', !etf.checked], ['1', '含 ETF', etf.checked]] },
        ].filter(Boolean);
      },
      act: (k, v) => {
        if (k === 'mkt') { const b = $$('button', live('#distMkt')).find((x) => x.dataset.m === v); if (b && !b.classList.contains('on')) b.click(); }
        if (k === 'etf') { const c = live('#distEtf'); if (c && c.checked !== (v === '1')) c.click(); }
      },
      move: () => live('#distGroupDD'), moveLbl: '族群',
      sum: () => {
        const on = $('#distMkt button.on'), etf = live('#distEtf'), g = ddText(live('#distGroupDD'));
        return [on ? on.textContent.trim() : '全部', etf && etf.checked ? '含 ETF' : '不含 ETF', '族群 ' + (g || '不限')];
      },
    },
    streak: {
      title: '法人連續買賣超設定',
      anchor: () => live('#streakView') || live('#streakWho'),
      rows: () => {
        const v = live('#streakView'), w = live('#streakWho'), d = live('#streakDays');
        return [
          v && { k: 'view', lbl: '畫法', items: $$('button', v).map((b) => [b.dataset.v, b.textContent.trim(), b.classList.contains('on')]) },
          w && { k: 'who', lbl: '法人', items: $$('button', w).map((b) => [b.dataset.w, b.textContent.trim(), b.classList.contains('on')]) },
          d && { k: 'days', lbl: '連續天數', items: Array.from(d.options).map((o) => [o.value, o.text.trim(), o.value === d.value]) },
        ].filter(Boolean);
      },
      act: (k, v) => {
        if (k === 'view') { const b = $$('button', live('#streakView')).find((x) => x.dataset.v === v); if (b && !b.classList.contains('on')) b.click(); }
        if (k === 'who') { const b = $$('button', live('#streakWho')).find((x) => x.dataset.w === v); if (b && !b.classList.contains('on')) b.click(); }
        if (k === 'days') { const d = live('#streakDays'); if (d && d.value !== v) { d.value = v; d.dispatchEvent(new Event('change', { bubbles: true })); } }
      },
      move: () => null,
      sum: () => {
        const vw = $('#streakView button.on'), w = $('#streakWho button.on'), d = live('#streakDays');
        return [vw ? vw.textContent.trim() : '', w ? w.textContent.trim() : '投信', d && d.options[d.selectedIndex] ? d.options[d.selectedIndex].text.trim() : ''];
      },
    },
    ma: {
      title: '站上均線設定',
      anchor: () => live('#maPick'),
      rows: () => {
        const s = live('#maSeg');
        return s ? [{ k: 'ma', lbl: '均線期間', items: $$('button', s).map((b) => [b.dataset.n, b.textContent.trim(), b.classList.contains('on')]) }] : [];
      },
      act: (k, v) => { const b = $$('button', live('#maSeg')).find((x) => x.dataset.n === v); if (b && !b.classList.contains('on')) b.click(); },
      move: () => live('#maGroupCtl'), moveLbl: '族群（疊上去比）',
      sum: () => {
        const b = $('#maSeg button.on'), g = ddText(live('#maGroupDD'));
        return [b ? 'MA' + b.dataset.n : 'MA20', '族群 ' + (g || '未選')];
      },
    },
  };

  /* ---- 摘要鈕 ---- */
  function paintBtn(k) {
    const b = $('#m4MkSet'); if (!b) return;
    const parts = CFG[k].sum().filter(Boolean), s = parts.join('・'), l = parts.join(' · ');
    const want = `${ICON}<span class="m4st">${esc(s)}</span><i aria-hidden="true">›</i>`;
    if (b.innerHTML !== want) b.innerHTML = want;
    if (b.getAttribute('aria-label') !== CFG[k].title + '：' + l) { b.setAttribute('aria-label', CFG[k].title + '：' + l); b.title = CFG[k].title + '：' + l; }
  }
  function wire() {
    if (!isM() || !onMarket()) return;
    const k = kindNow(), c = CFG[k];
    if (!c) { const ob = $('#m4MkSet'); if (ob) ob.remove(); return; }
    const a = c.anchor(); if (!a) return;
    let b = $('#m4MkSet');
    if (b && b.dataset.k !== k) { b.remove(); b = null; }
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = 'm4MkSet'; b.className = 'mfilt m4mkset';
      b.dataset.k = k; b.setAttribute('aria-haspopup', 'dialog');
      b.addEventListener('click', () => openSet(k));
    }
    if (b.nextElementSibling !== a) a.before(b);
    root.classList.add('m4mkset');
    paintBtn(k);
  }

  /* ---- 抽屜 ---- */
  let cur = null;   // { k, slot, node, home }
  function segRows(c) {
    return c.rows().map((r) => `<div class="m4mkrow"><span class="m4mklbl">${esc(r.lbl)}</span><div class="seg" data-mk="${r.k}">${r.items.map(([v, t, on]) =>
      `<button type="button" data-v="${esc(v)}" class="${on ? 'on' : ''}" aria-pressed="${!!on}">${esc(t)}</button>`).join('')}</div></div>`).join('');
  }
  /* 搬：頁面上最新的那個節點 → 抽屜；原位留一個註解當家。抽屜裡舊的（app.js 已重畫掉的）直接丟 */
  function syncMove() {
    if (!cur) return;
    const n = CFG[cur.k].move(); if (!n || n === cur.node) return;
    if (cur.node && cur.node.parentNode === cur.slot) cur.node.remove();
    if (cur.home && cur.home.parentNode) cur.home.remove();
    cur.home = document.createComment('m4mkhome'); n.parentNode.insertBefore(cur.home, n);
    cur.slot.appendChild(n); cur.node = n;
  }
  function repaint() {
    if (!cur) return;
    const c = CFG[cur.k];
    cur.segs.innerHTML = segRows(c);
    syncMove();
    paintBtn(cur.k);
  }
  function restore() {
    if (!cur) return;
    const { node, home } = cur; cur = null;
    if (node && home && home.parentNode) home.parentNode.insertBefore(node, home);   // 家還在 → 搬回去
    else if (node && node.parentNode) node.remove();                                 // 家被 app.js 重畫掉了 → 頁面上已經有新的，抽屜這個丟掉
    if (home && home.parentNode) home.remove();
    setTimeout(wire, 0);
  }
  function openSet(k) {
    const api = window.M3, c = CFG[k]; if (!api || !c) return;
    const wrap = document.createElement('div');
    wrap.innerHTML = `<div class="mshhead"><b>${esc(c.title)}</b></div><div class="m4shsegs m4mksegs"></div>`
      + (c.move() ? `<div class="m4mkrow m4mkmv"><span class="m4mklbl">${esc(c.moveLbl || '')}</span><div class="m4mkslot"></div></div>` : '');
    cur = { k, segs: $('.m4mksegs', wrap), slot: $('.m4mkslot', wrap), node: null, home: null };
    cur.segs.innerHTML = segRows(c);
    if (cur.slot) syncMove();
    cur.segs.addEventListener('click', (e) => {
      const b = e.target.closest('.seg[data-mk] > button'); if (!b) return;
      c.act(b.parentNode.dataset.mk, b.dataset.v);
      setTimeout(repaint, 60); setTimeout(repaint, 400);   // app.js 有的重畫是非同步的，兩次對齊
    });
    // 族群下拉勾選／全選／清除：摘要字跟著換（msDD／TwMS 都會發 change 或重寫按鈕字）
    wrap.addEventListener('change', () => setTimeout(() => { if (cur) paintBtn(cur.k); }, 60));
    wrap.addEventListener('click', (e) => {
      if (e.target.closest('.seg[data-mk]')) return;
      setTimeout(() => { if (cur) { syncMove(); paintBtn(cur.k); } }, 120);
    });
    // 站上均線的族群面板開在抽屜裡（往下長）：抽屜拉高（CSS :has）並把面板捲進畫面，不用自己找（msDD 會擋冒泡 → 用捕獲）
    wrap.addEventListener('click', (e) => {
      if (e.target.closest('.ddbtn')) [80, 300].forEach((t) => setTimeout(() => { const p = $('.m4mkslot .ddpanel', wrap); if (p && !p.hidden) p.scrollIntoView({ block: 'nearest' }); }, t));
    }, true);
    api.openSheet(wrap, { kind: 'm4mkset', onClose: restore });
  }

  let tm = 0;
  function kick() { clearTimeout(tm); tm = setTimeout(wire, 120); }
  function init() {
    const v = $('#v-market'); if (!v) return;
    new MutationObserver(() => { if (isM()) kick(); }).observe(v, { childList: true, subtree: true });
    window.addEventListener('hashchange', kick);
    // TwMS 的族群下拉勾完（面板掛在 body 上）：摘要字跟著換
    document.addEventListener('change', (e) => {
      if (!isM() || !e.target.closest || !e.target.closest('.twms-pan')) return;
      [80, 350].forEach((t) => setTimeout(() => { if (onMarket() && CFG[kindNow()]) paintBtn(kindNow()); }, t));
    });
    let wasM = isM(), rt = 0;
    window.addEventListener('resize', () => {
      clearTimeout(rt); rt = setTimeout(() => {
        const m = isM(); if (m === wasM) return; wasM = m;
        if (!m) { const b = $('#m4MkSet'); if (b) b.remove(); root.classList.remove('m4mkset'); } else kick();
      }, 200);
    });
    kick();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
