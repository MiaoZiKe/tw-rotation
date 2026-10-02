/* ==================================================================================
   版面 v2 結構搬到設計 v4 —— 頁首、「本頁功能」跳轉列、左側導覽收合、手機頂欄頁名（DECISIONS #291）
   2026-10-02（分支 claude/layout-v2-on-v4）。樣式在 layout4.css；改寫自 V2 分支的 site/ui2.js。

   ★ 這支**只讀畫面、只加導覽**，不改任何功能：
     · 不碰路由、不碰資料、不重畫任何圖表；不改任何既有元素的 id、data-*；
     · 「本頁功能」是從目前這一頁的卡片標題**讀出來**的，卡片新增或改名時自動跟著變，不必維護清單；
     · 今日事件抽屜完全交給 app.js 原本的 setSide()（v4 已經是浮層＋點背景關＋Esc），這裡不另外接一套關法 ——
       V2 自己接了 pointerdown／Esc／「一進站先關」三段，是因為 V2 那時的事件欄還是 grid 的一欄；v4 已經不需要。
   跟 V2 不同的地方：
     · 收合鍵名 tw.layout4.nav（不沿用 tw.ui2.nav：V2 是另一個預覽版，兩邊的預設門檻不同，共用一個鍵會互相蓋掉）；
     · 「自選」放進「專案」組（DECISIONS #274：自選是導覽最後一格，取代交付清單）；
     · 外觀面板、帳號選單是 theme4.js／account.js 用「按鈕下緣＋8px」定位的 —— 按鈕搬到左欄底部之後會掉出視窗，
       這裡在它們打開之後改放到左欄右邊（只改 style.top／left，面板內容與行為不動）。
   ================================================================================== */
(function () {
  'use strict';
  const root = document.documentElement;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const LS = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗，忽略 */ } },
  };
  const DESK = () => window.innerWidth > 820;
  /* ★ 2026-10-03 手機版暫停（Andy：「手機版先停擺，等電腦版 OK 之後再做。電腦版要先上線」）：
     MOBILE＝false 時，視窗 ≤820 這支**什麼都不做**：不掛 l4、不插任何節點（#l4Head／#l4Jump／.l4foot／.brand .l4pt）、
     不寫任何 inline style、不動分頁的 title／aria-label —— ≤820 的畫面與 DOM 跟 main 一樣。
     視窗被拉寬／縮窄跨過 821 時，activate()／deactivate() 會把東西整套掛上或撤乾淨。
     第二批的手機程式（一行頁首、分段列統一、.l4pt）都還在，MOBILE 改 true 就會在 ≤820 也掛上（另外掛 l4m 旗標，CSS 那兩段吃它）。 */
  const MOBILE = false;
  const WANT = () => DESK() || MOBILE;
  let active = false;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

  /* ---------------- 每一頁「這頁回答什麼」 ----------------
     判斷順序是網站的核心：M1 資金面 → M2 基本面 → M3 技術面 → M4 事件面（CLAUDE.md 第一段）。
     這裡一句話講清楚每一頁在那個順序裡的位置，讓第一次來的人知道從哪裡開始看。 */
  const PAGES = {
    overview: { grp: '今日市場', t: '總覽', d: '今天大盤怎麼走、錢集中在哪幾個族群、題材在做什麼 —— 從這裡開始，一頁看完今天的重點。' },
    flow: { grp: '錢往哪裡跑', t: '資金流向', d: '錢正在往哪個族群跑：輪盤看輪動階段、排行看誰進誰出、資金去向看錢從哪裡流到哪裡。' },
    heatmap: { grp: '錢往哪裡跑', t: '熱力圖', d: '全市場與題材的冷熱一眼看完：方塊越大錢越多、越紅漲越多；點方塊看成分股。' },
    industry: { grp: '族群與個股', t: '產業地圖', d: '每條產業鏈的強弱與上下游：先挑產業鏈，再看族群與零件，最後點個股看 K 線與基本面。' },
    stock: { grp: '族群與個股', t: '個股', d: 'K 線與多週期技術面、營收與獲利、籌碼與除權息 —— 決定「什麼時候進場」與「現在貴不貴」。' },
    market: { grp: '族群與個股', t: '市場明細', d: '完整名單：漲跌分佈、站上均線、法人動向與各項排行，可以排序篩選，找出符合條件的個股。' },
    season: { grp: '歷史規律', t: '週期統計', d: '每個族群在各月份的歷史表現：勝率、報酬中位數與超額報酬，看現在是不是它的旺季。' },
    watch: { grp: '專案', t: '自選', d: '你自己的自選清單（最多五頁）：今天的漲跌與走勢，點走勢圖原地展開、點名稱進個股頁。' },
    delivery: { grp: '專案', t: '交付清單', d: '提出過的需求與完成狀態，逐條可以點過去驗收。' },
  };
  const ALIAS = { themes: 'heatmap', tasks: 'delivery' };
  /* 卡片標題讀出來不像「這一節」的，指定名字（大盤三張圖的外框第一個標題是「加權指數」，但這一節是三張圖） */
  const CARD_NAME = { m3Frame: '大盤走勢' };

  function curKey() {
    const h = (location.hash || '#overview').slice(1).split('/')[0] || 'overview';
    if (h === 'stock') return 'stock';
    const v = $('.view.on');
    if (v && v.id && v.id.startsWith('v-')) {
      const k = v.id.slice(2);
      return ALIAS[k] || k;            // legal／admin 等不在 PAGES 的頁面 → 頁首整塊收起來
    }
    return ALIAS[h] || h;
  }

  /* ---------------- 頁首與跳轉列 ---------------- */
  let head, jump, chips;
  function build() {
    const lay = $('#layout'); if (!lay || $('#l4Head')) return !!$('#l4Head');
    head = document.createElement('header'); head.id = 'l4Head';
    jump = document.createElement('nav'); jump.id = 'l4Jump'; jump.setAttribute('aria-label', '本頁功能');
    jump.innerHTML = '<span class="lbl">本頁功能</span><div class="chips"></div>';
    chips = $('.chips', jump);
    lay.parentNode.insertBefore(head, lay);
    lay.parentNode.insertBefore(jump, lay);
    return true;
  }
  function chainName() {
    // 產業地圖的麵包屑最後一格（例如「AI 伺服器」「台積電 2330」）；industry.js 畫的，這裡只讀
    const cur = $('#indCrumbs .cur');
    return cur ? cur.textContent.trim() : '';
  }
  let lastHead = '';
  function renderHead() {
    if (!head) return;
    const k = curKey(), p = PAGES[k];
    let sub = '';
    if (p && (k === 'industry' || k === 'stock') && /^#(industry\/|stock\/)/.test(location.hash)) sub = chainName();
    const sig = [k, sub].join('|');
    if (sig === lastHead) return;
    lastHead = sig;
    // 手機：頁首整塊不顯示（每頁有一屏高度預算），改把「分組＋頁名」放進頂欄原本寫站名的位置 —— 一個 px 都不多佔
    const bt = MOBILE ? $('.brand > div:not(.logo)') : null;   // 頂欄頁名是手機版的東西（暫停中）
    if (bt) {
      let mpt = $('.l4pt', bt);
      if (!mpt) { mpt = document.createElement('span'); mpt.className = 'l4pt'; bt.insertBefore(mpt, bt.firstChild); }
      const nm = p ? (k === 'stock' && sub ? sub : p.t) : (($('.view.on h1, .view.on h2') || {}).textContent || '').trim();
      mpt.innerHTML = (p ? `<i>${esc(p.grp)}</i>` : '') + `<span>${esc(nm || '台股資金輪動')}</span>`;
    }
    head.hidden = !p;
    if (!p) { head.innerHTML = ''; return; }
    head.innerHTML = `<div class="eyebrow">${esc(p.grp)}</div>`
      + `<div class="ttl"><h1>${esc(p.t)}${sub && sub !== p.t ? `<span class="sub1">${esc(sub)}</span>` : ''}</h1>`
      + `<p>${esc(p.d)}</p></div>`;
  }

  /* 「本頁功能」：目前這一頁、看得見的、最外層卡片的標題。
     標題裡的「?」鈕、下拉、日期、數字徽章、小圖示都拿掉，只留字；太長就截。 */
  function cardTitle(card) {
    if (card.id && CARD_NAME[card.id]) return CARD_NAME[card.id];
    const h = card.querySelector('h3, h2');
    if (!h || h.closest('.card') !== card) return '';
    const c = h.cloneNode(true);
    c.querySelectorAll('button, select, input, small, svg, img, .howbtn, .pill, .muted, .note, [hidden], .rotdd, .seg, .n, .ticon, [class*="tag"], [data-warn]').forEach((x) => x.remove());
    let t = c.textContent.replace(/\s+/g, ' ').trim().replace(/[?？]$/, '').trim();
    if (t.length > 14) t = t.slice(0, 13) + '…';
    return t;
  }
  let cards = [], lastSig = '';
  const MOB = () => window.innerWidth <= 640 && document.body.classList.contains('m3on');
  const shown = (e) => !!e && !e.hidden && e.getClientRects().length > 0;
  function scanCards() {
    if (!jump) return;
    const view = $('.view.on');
    /* 手機：分段列（.mspine 四步／.mpager 分段）就是這一頁的「本頁功能」，個股頁的是券商式分頁列（#mbHead）——
       有其中一個就不再出第二排膠囊（Andy：「不要做出兩排功能重複的膠囊」）。
       總覽的分段列要黏在四步列底下，四步列多高這裡量給 CSS（--l4-spine-h）。 */
    let own = false;
    if (MOB() && view) {
      const sp = view.querySelector(':scope > .mspine');
      if (shown(sp)) root.style.setProperty('--l4-spine-h', Math.round(sp.getBoundingClientRect().height) + 'px');
      own = shown(sp) || shown(view.querySelector(':scope > .mpager')) || document.body.classList.contains('mbon');
    }
    const list = view && !own ? $$('.card', view).filter((c) => {
      if (c.parentElement && c.parentElement.closest('.card')) return false;        // 只要最外層
      if (!c.getClientRects().length) return false;                                  // 看不見的不列
      return c.getBoundingClientRect().height > 40;
    }) : [];
    /* 編號照「畫面上的位置」排（先上後左），不是 DOM 順序 —— 總覽的熱力圖｜輪盤是並排的兩欄，
       DOM 裡輪盤排在題材後面，照 DOM 編號會變成 01 熱力圖、02 題材、03 輪盤，跟眼睛看到的順序對不起來。 */
    const sy = window.scrollY;
    const pos = list.map((c) => { const r = c.getBoundingClientRect(); return { c, top: Math.round(r.top + sy), left: Math.round(r.left) }; });
    pos.sort((a, b) => (Math.abs(a.top - b.top) > 8 ? a.top - b.top : a.left - b.left));
    const items = [], seen = new Set();
    pos.forEach(({ c }) => { const t = cardTitle(c); if (t && !seen.has(t)) { seen.add(t); items.push({ c, t }); } });
    const sig = curKey() + '|' + items.map((x) => x.t).join('|');
    if (sig === lastSig) { cards = items; return; }   // 名單沒變也要換成新的節點參照（卡片可能整塊重建過）
    lastSig = sig;
    cards = items;
    jump.hidden = items.length < 2;                  // 只有一張卡的頁面不需要跳轉列
    chips.innerHTML = items.map((x, i) => `<button type="button" data-i="${i}"><i>${String(i + 1).padStart(2, '0')}</i>${esc(x.t)}</button>`).join('');
    $$('button', chips).forEach((b) => { b.onclick = () => go(+b.dataset.i); });
    if (Date.now() >= lockUntil) mark(current()); spy(true);   // 重建之後當場亮一顆（不等下一幀：機器忙時那一幀可能晚到，膠囊列會有一段時間全暗）
  }
  let lockUntil = 0;
  function go(i) {
    const it = cards[i]; if (!it || !it.c.isConnected) { lastSig = ''; scanCards(); return; }
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    // 自己算位置（扣掉跳轉列高度＋一點呼吸），不靠 scroll-padding 與各卡片 scroll-margin 疊加 —— 兩者會相加，落點不一
    const stickTop = parseFloat(getComputedStyle(jump).top) || 0;        // 桌機 0、641～820 黏在頂欄 58 下、手機 52 下
    const off = stickTop + (jump.getBoundingClientRect().height || 48) + 12;
    window.scrollTo({ top: Math.max(0, it.c.getBoundingClientRect().top + window.scrollY - off), behavior: reduce ? 'auto' : 'smooth' });
    it.c.classList.remove('l4-hit'); void it.c.offsetWidth; it.c.classList.add('l4-hit');
    setTimeout(() => it.c.classList.remove('l4-hit'), 1300);
    lockUntil = Date.now() + (reduce ? 100 : 900);
    mark(i);
  }
  function mark(i) {
    $$('button', chips).forEach((b) => {
      const on = +b.dataset.i === i;
      b.classList.toggle('on', on);
      if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
    });
    const on = $(`button[data-i="${i}"]`, chips);
    if (on) {
      const r = on.getBoundingClientRect(), s = chips.getBoundingClientRect();
      if (r.left < s.left || r.right > s.right - 28) chips.scrollBy({ left: r.left - s.left - s.width / 3 });
    }
  }
  /* 捲動時亮起「目前在看的那一張」：頂端已經過了基準線（跳轉列下緣＋24）、而且最靠近基準線的那張；捲到底就亮最後一張。
     並排的兩張卡頂端不同高，不能只看 DOM 順序的最後一張。 */
  let spyRaf = 0;
  function spy(force) {
    if (spyRaf) return;
    spyRaf = requestAnimationFrame(() => {
      spyRaf = 0;
      if (!cards.length || !jump || jump.hidden) return;
      const stickTop = parseFloat(getComputedStyle(jump).top) || 0;
      jump.classList.toggle('stuck', jump.getBoundingClientRect().top <= stickTop + 1 && window.scrollY > 10);
      if (!force && Date.now() < lockUntil) return;   // 剛點過膠囊：捲動動畫跑完之前不要被偵測改掉
      mark(current());
    });
  }
  function current() {
    const line = jump.getBoundingClientRect().bottom + 24;
    let best = 0, bestTop = -Infinity;
    cards.forEach((x, i) => { const t = x.c.getBoundingClientRect().top; if (t <= line && t > bestTop + 1) { best = i; bestTop = t; } });
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4 && window.scrollY > 0) best = cards.length - 1;
    return best;
  }
  /* 卡片是非同步畫出來的（圖表、資料載入完才出現），所以用 MutationObserver 追，
     但只在「最外層卡片的組成」變了才重畫膠囊（scanCards 內部有簽章比對），盤中每 5 秒的報價更新不會讓膠囊列重排。
     節流不是防抖：動畫中 DOM 一直在變時，防抖會永遠等不到。 */
  let scanT = 0;
  function queueScan() {
    if (scanT) return;
    scanT = setTimeout(() => { scanT = 0; renderHead(); scanCards(); }, 300);
  }

  /* ---------------- 左側導覽收合（寬 ↔ 圖示列） ----------------
     使用者按過就記住（tw.layout4.nav＝mini／full）；沒按過時，視窗 ≤1180px 自動收成圖示列，讓內容有地方放
     （1180 沿用 V2 的門檻：1180 − 224 ＝ 956，再窄兩欄的卡片就開始擠）。 */
  const NAV_KEY = 'tw.layout4.nav';
  function applyNav() {
    if (!active) return;
    const pref = LS.get(NAV_KEY);
    const mini = pref ? pref === 'mini' : (window.innerWidth <= 1180);
    const was = root.classList.contains('l4-mini');
    root.classList.toggle('l4-mini', mini);
    /* 收合時頁名字級是 0（只剩圖示）：補 title 給滑鼠提示、aria-label 給讀屏（展開時拿掉，避免唸兩次） */
    $$('.tab').forEach((t) => {
      if (mini && DESK()) { const n = t.textContent.trim(); t.title = n; t.setAttribute('aria-label', n); }
      else { t.removeAttribute('title'); t.removeAttribute('aria-label'); }
    });
    const btn = $('#l4NavBtn');
    if (btn) {
      btn.title = mini ? '展開導覽' : '收合導覽';
      btn.setAttribute('aria-expanded', String(!mini));
      btn.setAttribute('aria-label', btn.title);
    }
    /* 內容寬度變了：圖表容器有 ResizeObserver 會自己重算，這裡再派一次 resize 給還沒掛觀察器的（例如分頁列溢出判斷） */
    if (was !== mini) setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
    fitNav();
  }
  function buildFoot() {
    const bar = $('.topbar'); if (!bar || $('#l4NavBtn')) return;
    const foot = document.createElement('div'); foot.className = 'l4foot';
    foot.innerHTML = '<button type="button" id="l4NavBtn"><span class="ic"></span><span class="lbl">收合導覽</span></button>';
    bar.appendChild(foot);
    $('#l4NavBtn').onclick = () => {
      LS.set(NAV_KEY, root.classList.contains('l4-mini') ? 'full' : 'mini');
      applyNav();
    };
  }

  /* ---------------- 左欄中間（頁面清單）那一列的高度 ----------------
     .topbar 的盒子只有頂端 49px（理由見 layout4.css 第 1 段），其餘列溢出往下長，所以沒有「1fr 吃掉剩下的高度」可用：
     這裡量「視窗高 −（品牌＋搜尋＋底部工具各列）− 底部留白」寫進 --l4-tabs-h。頁面太多放不下時清單自己捲；
     視窗矮到連 120px 都給不起時就讓它 120（底部工具會被推出視窗 —— 那是 <560px 高的視窗，桌機幾乎碰不到）。
     帳號列（登入／線上人數）、「有新資料」鈕出現與否都會改變其他列的高，所以 .topbar 裡的節點一變就重量。 */
  let fitRaf = 0;
  function fitNav() {
    if (fitRaf) return;
    fitRaf = requestAnimationFrame(() => {
      fitRaf = 0;
      const bar = $('.topbar'), tw = $('#tabsWrap');
      if (!active || !bar || !tw || !DESK()) return;
      const cur = tw.getBoundingClientRect().height;
      let last = tw.getBoundingClientRect().bottom;
      Array.from(bar.children).forEach((c) => {
        if (c === tw || !c.getClientRects().length) return;
        last = Math.max(last, c.getBoundingClientRect().bottom);
      });
      const want = Math.max(120, Math.floor(window.innerHeight - 12 - (last - cur)));
      if (Math.abs(want - cur) > 1) root.style.setProperty('--l4-tabs-h', want + 'px');
    });
  }

  /* ---------------- 外觀面板、帳號選單：改放到左欄右邊 ----------------
     theme4.js 的 place() 與 account.js 的 openMenu() 都是「按鈕下緣 ＋ 8px」—— 按鈕在頂欄時正確，
     搬到左欄底部之後面板會整塊掉到視窗外。不改那兩支（不是這一批的檔），在它們打開之後的下一幀改座標：
     面板左緣貼左欄右緣、下緣對齊按鈕下緣（夾在視窗內）。手機與 641～820 不動（那兩個寬度還是頂欄）。 */
  function besideNav(pop, btn) {
    if (!active || !pop || pop.hidden || !btn || !DESK()) return;
    const r = btn.getBoundingClientRect(), h = pop.offsetHeight;
    const navW = $('.topbar').getBoundingClientRect().width;
    pop.style.left = Math.round(navW + 8) + 'px';
    pop.style.top = Math.round(Math.max(8, Math.min(r.bottom - h, window.innerHeight - h - 8))) + 'px';
  }
  function wirePopups() {
    // capture：theme4.js 的按鈕處理會 stopPropagation，冒泡階段收不到；在捕獲階段排一幀，等它打開之後再挪
    document.addEventListener('click', (e) => {
      const t = e.target.closest && e.target.closest('#t4Btn, #acctBtn');
      if (!t) return;
      requestAnimationFrame(() => besideNav(t.id === 't4Btn' ? $('#t4Pop') : $('#acctMenu'), t));
    }, true);
    // theme4.js 自己在 resize 時會重新 place()；這支在它之後登記，所以會接著把它挪回左欄旁邊
    window.addEventListener('resize', () => { besideNav($('#t4Pop'), $('#t4Btn')); besideNav($('#acctMenu'), $('#acctBtn')); });
  }

  /* 掛上：桌機（或手機旗標打開時）才有的整套東西 */
  function activate() {
    active = true;
    root.classList.add('l4');
    if (!DESK()) root.classList.add('l4m');
    build(); buildFoot();
    lastHead = ''; lastSig = '';
    applyNav();
    renderHead(); scanCards();
    fitNav();
  }
  /* 撤掉：回到 main 原本的頂欄 —— 插過的節點、掛過的 class、寫過的 inline style、補過的 title／aria-label 全部拿掉 */
  function deactivate() {
    active = false;
    ['#l4Head', '#l4Jump', '.l4foot', '.brand .l4pt'].forEach((sel) => $$(sel).forEach((e) => e.remove()));
    head = jump = chips = null; cards = []; lastHead = ''; lastSig = '';
    root.classList.remove('l4', 'l4-mini', 'l4m');
    root.style.removeProperty('--l4-tabs-h'); root.style.removeProperty('--l4-spine-h');
    if (root.getAttribute('style') === '') root.removeAttribute('style');
    $$('.tab').forEach((t) => { t.removeAttribute('title'); t.removeAttribute('aria-label'); });
    $$('.l4-hit').forEach((e) => e.classList.remove('l4-hit'));
    setTimeout(() => window.dispatchEvent(new Event('resize')), 60);   // 版面換回頂欄，讓圖表與分頁列重量一次
  }

  function init() {
    if (WANT()) activate(); else deactivate();
    wirePopups();
    const bar = $('.topbar');
    if (bar) new MutationObserver(fitNav).observe(bar, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['hidden'] });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitNav);
    const main = $('main');
    /* 只看「節點增減」：卡片出現／消失一定伴隨 childList。不看 class／style ——
       圖表動畫、盤中閃爍每秒都在改屬性，全部接進來會一直逼瀏覽器重排。
       換頁（.view.on 換人、產業頁改 display）另外由 hashchange 補掃三次。 */
    if (main) new MutationObserver(queueScan).observe(main, { childList: true, subtree: true });
    window.addEventListener('hashchange', () => {
      if (!active) return;
      lastHead = ''; lastSig = '';
      [60, 700, 2000].forEach((t) => setTimeout(() => { renderHead(); scanCards(); }, t));
    });
    window.addEventListener('scroll', () => { if (active) spy(); }, { passive: true });
    window.addEventListener('resize', () => {
      const w = WANT();
      if (w !== active) { if (w) activate(); else deactivate(); return; }
      if (!active) return;
      if (!LS.get(NAV_KEY)) applyNav();
      queueScan(); spy(); fitNav();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
