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
   ★ 2026-10-03 第三批（Andy 對預覽 preview/layout-v2 的四條，只作用在 >820 的電腦版）：
     ① 頁首只剩「頁名＋台北現在時間」、黏在最上面；分組小標、說明句拿掉，「本頁功能」那排只藏不刪（CSS）
     ② 收合鈕從左欄最底下的文字列，改成 logo 右側一顆側欄圖示小方鈕（#l4NavBtn）
     ③ 「事件」移到導覽最上面一格（CSS grid 換位置，DOM 不動）
     ④ 左欄底部改成帳號卡（#l4Acct，account.js 的 #acctBtn 本人搬進來當「登入」／名字那顆）＋「淺色｜深色」二段式（#l4Mode）
        ＋外觀調色盤小鈕（#t4Btn）；「★ 自選」與 ☀ 鈕在電腦版藏起來（≤820 照舊）
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
    flow: { grp: '資金流水', t: '資金流向', d: '錢正在往哪個族群跑：輪盤看輪動階段、排行看誰進誰出、資金去向看錢從哪裡流到哪裡。' },
    heatmap: { grp: '資金流水', t: '熱力圖', d: '全市場與題材的冷熱一眼看完：方塊越大錢越多、越紅漲越多；點方塊看成分股。' },
    industry: { grp: '族群與個股', t: '產業地圖', d: '每條產業鏈的強弱與上下游：先挑產業鏈，再看族群與零件，最後點個股看 K 線與基本面。' },
    stock: { grp: '族群與個股', t: '個股', d: 'K 線與多週期技術面、營收與獲利、籌碼與除權息 —— 決定「什麼時候進場」與「現在貴不貴」。' },
    market: { grp: '族群與個股', t: '市場明細', d: '完整名單：漲跌分佈、站上均線、法人動向與各項排行，可以排序篩選，找出符合條件的個股。' },
    season: { grp: '歷史規律', t: '週期統計', d: '每個族群在各月份的歷史表現：勝率、報酬中位數與超額報酬，看現在是不是它的旺季。' },
    watch: { grp: '專案', t: '自選', d: '你自己的自選清單（最多五頁）：今天的漲跌與走勢，點走勢圖原地展開、點名稱進個股頁。' },
    delivery: { grp: '專案', t: '交付清單', d: '提出過的需求與完成狀態，逐條可以點過去驗收。' },
  };
  const ALIAS = { themes: 'heatmap', tasks: 'delivery' };
  /* ★ 2026-10-03（Andy：「資金流向」四個本頁功能拆成三個側欄子分頁、「熱力圖」拆產業／題材）：
     側欄縮排子項。路由與「這一頁顯示哪幾張卡」在 app.js route()（<html data-l4sub>）＋ layout4.css；這裡只畫側欄那幾格、亮目前那格。
     短名（s）是收合成圖示列時顯示的兩個字。 */
  const SUBS = {
    flow: [
      { k: 'flow-rotation', h: '#flow/rotation', t: '資金輪動', s: '輪動' },
      { k: 'flow-sankey', h: '#flow/sankey', t: '資金去向', s: '去向' },
      { k: 'flow-inst', h: '#flow/inst', t: '族群×法人＋集中度', s: '法人' },
    ],
    heatmap: [
      { k: 'heat-industry', h: '#heatmap/industry', t: '產業', s: '產業' },
      { k: 'heat-theme', h: '#heatmap/theme', t: '題材', s: '題材' },
    ],
  };
  const subKey = () => root.getAttribute('data-l4sub') || '';
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
    if (p && SUBS[k]) { const it = SUBS[k].find((x) => x.k === subKey()); if (it) sub = it.t; }
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
    /* ★ 2026-10-03（Andy：「紅框處 只留下 總覽 及當下日期時間（所有分頁都是）」）：
       分組小標（eyebrow）、說明句（p）拿掉，只留頁名＋台北現在時間。「本頁功能」那排見 CSS（只藏不刪）。 */
    head.innerHTML = `<h1>${esc(p.t)}${sub && sub !== p.t ? `<span class="sub1">${esc(sub)}</span>` : ''}</h1>`
      + '<time class="l4clock" aria-live="off"></time>';
    tick();
  }

  /* ---------------- 頁首的現在時間（台北） ----------------
     容器、使用者的電腦都可能不在 UTC+8，所以一律用 Intl 指定 Asia/Taipei，不靠本機時區。
     ★ 每秒寫的是 data-t「屬性」，字由 CSS 的 ::before 畫：全站有兩支掛在 body 上的 MutationObserver
     （icons.js 看 childList＋characterData、live.js 看 childList），寫文字節點會讓它們每秒各掃一輪
     （DECISIONS #284 的卡頓就是這種東西造成的）；兩支都不看屬性，改屬性它們完全不會被叫醒。 */
  const CLOCK_FMT = (() => {
    try {
      return new Intl.DateTimeFormat('zh-TW', { timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
        weekday: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
    } catch (e) { return null; }
  })();
  function clockText(d) {
    if (!CLOCK_FMT) return '';
    const o = {}; CLOCK_FMT.formatToParts(d).forEach((x) => { o[x.type] = x.value; });
    // 例：2026-10-03（五）14:05:33 —— 星期拿 Intl 的「週五」去掉「週」
    return `${o.year}-${o.month}-${o.day}（${String(o.weekday || '').replace(/^週|^星期/, '')}）${o.hour}:${o.minute}:${o.second}`;
  }
  let clockT = 0;
  function tick() {
    const c = head && $('.l4clock', head);
    if (c) {
      const now = new Date(), t = clockText(now);
      c.setAttribute('data-t', t); c.setAttribute('datetime', now.toISOString());
      c.setAttribute('aria-label', '台北時間 ' + t); c.title = '台北時間（每秒更新）';
    }
    clearTimeout(clockT);
    if (active) clockT = setTimeout(tick, 1000 - (Date.now() % 1000) + 5);   // 對齊整秒，跳秒不會忽快忽慢
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

  /* ---------------- 側欄子分頁（資金流向三格、熱力圖兩格） ----------------
     插在 #tabs 裡、各自的父頁後面；class 是 l4subtab（**不是 .tab**）—— 手機版、app.js 的分頁列、驗收腳本都是數 .tab，
     不能讓它們多算。≤820 deactivate() 整批拿掉。點了只是換 hash，其餘交給 app.js 的 route()。 */
  function buildSubs() {
    const tabs = $('#tabs'); if (!tabs || $('.l4subtab', tabs)) return;
    Object.keys(SUBS).forEach((v) => {
      const parent = $(`.tab[data-view="${v}"]`, tabs); if (!parent) return;
      let after = parent;
      SUBS[v].forEach((it) => {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'l4subtab'; b.dataset.l4sub = it.k; b.dataset.parent = v;
        b.innerHTML = `<span class="lbl">${esc(it.t)}</span><span class="sh" aria-hidden="true">${esc(it.s)}</span>`;
        b.title = (PAGES[v] ? PAGES[v].t + '・' : '') + it.t;
        b.onclick = () => {
          // 熱力圖題材子分頁：已經在題材（可能還帶著 /<題材 id>）就不動網址，不要把展開中的題材收掉
          if (subKey() === it.k) return;
          location.hash = it.h;
        };
        after.after(b); after = b;
      });
    });
    markSubs();
  }
  function markSubs() {
    const k = subKey();
    $$('.l4subtab').forEach((b) => {
      const on = b.dataset.l4sub === k;
      b.classList.toggle('on', on);
      if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    });
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
  /* ★ 2026-10-03（Andy：「收合導覽改成圖三那樣」，參考 assetmetra）：收合鈕從左欄最底下的「‹ 收合導覽」文字列，
     改成 logo 右側一顆小方鈕（側欄圖示，像 lucide panel-left）。它是 .topbar 的直接子元素（不放進 .brand：
     .brand 本身有 onclick 回總覽，放進去會點一下同時收合又換頁）。 */
  function buildNavBtn() {
    const bar = $('.topbar'); if (!bar || $('#l4NavBtn')) return;
    const btn = document.createElement('button');
    btn.type = 'button'; btn.id = 'l4NavBtn'; btn.className = 'l4navbtn';
    btn.innerHTML = '<span class="ic" aria-hidden="true"></span>';
    const brand = $('.brand', bar);
    bar.insertBefore(btn, brand ? brand.nextSibling : bar.firstChild);
    btn.onclick = (e) => {
      e.stopPropagation();
      LS.set(NAV_KEY, root.classList.contains('l4-mini') ? 'full' : 'mini');
      applyNav();
    };
  }

  /* ---------------- 左欄底部：帳號卡＋「淺色｜深色」切換（Andy：「登入模式可以參考圖三下方」） ----------------
     原本底部是「★ 自選｜登入」兩顆、「外觀」鈕、☀ 鈕。改成：
       · 帳號卡：圓形頭像＋名稱＋一行小字。未登入＝「訪客」＋「登入」小鈕；已登入＝頭像、名字、信箱，點了開帳號選單。
       · 「淺色｜深色」二段式切換，取代 ☀ 鈕；「外觀」鈕縮成切換右邊一顆調色盤小鈕（三套風格只有它進得去，不能拿掉）。
       · 「★ 自選」整併：導覽「專案」組本來就有「自選」，這顆在電腦版藏起來（DOM 留著，≤820 的頂欄照舊用它）。
     ★ 不重寫登入邏輯：卡片右邊的「登入」／名字那顆**就是 account.js 的 #acctBtn 本人**（搬進卡片，id、onclick 都不變），
       所以登入、帳號選單、登出、刪除資料全部走原本那條路；這裡只負責頭像、名稱、小字這幾個「讀出來」的字。
       視窗縮到 ≤820（deactivate）時把它搬回 .acctbar。account.js 沒開會員功能（沒有設定檔）時不會有 #acctBtn ——
       卡片就只寫「訪客／自選存在這台瀏覽器」，不放一顆按了沒反應的登入鈕。 */
  function buildBottom() {
    const bar = $('.topbar'); if (!bar || $('#l4Acct')) return;
    const card = document.createElement('div');
    card.id = 'l4Acct'; card.className = 'l4acct';
    card.innerHTML = '<button type="button" class="av" tabindex="-1" aria-hidden="true"></button>'
      + '<b class="nm">訪客</b><small class="st"></small><span class="act"></span>';
    // 收合時只剩頭像：點頭像＝按「登入」（未登入）／打開帳號選單（已登入的頭像就是 #acctBtn 本人，不會走到這裡）
    $('.av', card).onclick = (e) => { e.stopPropagation(); const ab = $('#acctBtn'); if (ab) ab.click(); };
    const mode = document.createElement('div');
    mode.id = 'l4Mode'; mode.className = 'l4mode'; mode.setAttribute('role', 'group'); mode.setAttribute('aria-label', '明暗');
    mode.innerHTML = '<button type="button" data-l4m="light"><span class="ic" aria-hidden="true"></span><span class="lbl">淺色</span></button>'
      + '<button type="button" data-l4m="dark"><span class="ic" aria-hidden="true"></span><span class="lbl">深色</span></button>';
    mode.addEventListener('click', (e) => {
      const b = e.target.closest('[data-l4m]'); if (!b) return;
      const want = b.dataset.l4m, cur = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      // 跟 ☀ 鈕走同一條路（app.js 的 themeBtn.onclick → applyTheme(…, true)：重畫圖表、寫 tw.theme、通知外觀面板）；
      // 已經是這一邊就什麼都不做（二段式切換按目前那一邊不該翻過去）
      if (want !== cur) { const tb = $('#themeBtn'); if (tb) tb.click(); }
      syncMode();
    });
    bar.appendChild(card); bar.appendChild(mode);
    syncAcct(); syncMode();
  }
  function syncMode() {
    const m = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    $$('#l4Mode [data-l4m]').forEach((b) => {
      const on = b.dataset.l4m === m;
      b.setAttribute('aria-pressed', String(on));
      const nm = b.dataset.l4m === 'light' ? '淺色' : '深色';
      b.title = on ? `目前是${nm}` : `切換成${nm}`;
    });
  }
  let acctSig = '';
  function syncAcct() {
    const card = $('#l4Acct'); if (!card || !active) return;
    const ab = $('#acctBtn'), act = $('.act', card);
    if (ab && ab.parentNode !== act) act.appendChild(ab);                // 搬進卡片（已經在就不動，免得觸發自己的觀察器）
    const A = window.TwAccount, u = A && A.user ? A.user() : null, on = !!(A && A.on && A.on()) && !!ab;
    const n = A && A.online ? A.online() : null;
    let nm = '訪客', st = '自選存在這台瀏覽器', ini = '';
    if (u) { nm = u.name || u.email || '會員'; st = u.email || '已登入'; ini = nm.trim().charAt(0).toUpperCase(); }
    else if (on) st = n != null ? `${n} 人在線・登入同步自選` : '登入後自選跨裝置同步';
    const sig = [!!u, on, nm, st].join('|');
    if (sig === acctSig) return;
    acctSig = sig;
    card.classList.toggle('in', !!u);
    card.classList.toggle('noacct', !on);
    $('.nm', card).textContent = nm;
    const s = $('.st', card); s.textContent = st; s.title = st;
    const av = $('.av', card); av.textContent = ini; av.title = u ? nm : (on ? '登入' : '訪客');
    card.title = u ? `${nm}（${u.email || ''}）` : '';
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
    build(); buildNavBtn(); buildBottom(); buildSubs();
    lastHead = ''; lastSig = '';
    applyNav();
    renderHead(); scanCards(); syncAcct(); syncMode();
    fitNav();
  }
  /* 撤掉：回到 main 原本的頂欄 —— 插過的節點、掛過的 class、寫過的 inline style、補過的 title／aria-label 全部拿掉 */
  function deactivate() {
    active = false;
    clearTimeout(clockT);
    // #acctBtn 是 account.js 的那顆（被搬進帳號卡），拆卡片之前先放回原本的 .acctbar，不然會跟著被刪掉
    const ab = $('#acctBtn'), abar = $('#acctBar');
    if (ab && abar && ab.parentNode !== abar) abar.appendChild(ab);
    acctSig = '';
    ['#l4Head', '#l4Jump', '.l4foot', '#l4NavBtn', '#l4Acct', '#l4Mode', '.l4subtab', '.brand .l4pt'].forEach((sel) => $$(sel).forEach((e) => e.remove()));
    root.removeAttribute('data-l4sub');      // 子分頁只有電腦版有；手機版要看到整頁（app.js route() 掛的）
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
    /* 帳號鈕被 account.js 建出來／換字（登入、登出、線上人數）都在 .topbar 裡發生：順手把它搬進帳號卡、重寫卡片的字。
       syncAcct 有簽章比對，自己寫進去的變動再叫一次它也不會再寫，不會無限循環。 */
    if (bar) new MutationObserver(() => { fitNav(); if (active) syncAcct(); }).observe(bar, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['hidden', 'class', 'title'] });
    window.addEventListener('tw:account', () => { if (active) syncAcct(); });
    // 明暗：不管是誰切的（這裡的二段式、外觀面板、≤820 的「⋯」清單），都以 <html data-theme> 為準
    // 子分頁：app.js route() 一改 data-l4sub（含第一次進站、replace 導向）就亮對的那格、頁首補上子分頁名
    new MutationObserver((recs) => {
      if (!active) return;
      if (recs.some((r) => r.attributeName === 'data-theme')) syncMode();
      if (recs.some((r) => r.attributeName === 'data-l4sub')) { markSubs(); renderHead(); }
    }).observe(root, { attributes: true, attributeFilter: ['data-theme', 'data-l4sub'] });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitNav);
    const main = $('main');
    /* 只看「節點增減」：卡片出現／消失一定伴隨 childList。不看 class／style ——
       圖表動畫、盤中閃爍每秒都在改屬性，全部接進來會一直逼瀏覽器重排。
       換頁（.view.on 換人、產業頁改 display）另外由 hashchange 補掃三次。 */
    if (main) new MutationObserver(queueScan).observe(main, { childList: true, subtree: true });
    window.addEventListener('hashchange', () => {
      if (!active) return;
      lastHead = ''; lastSig = '';
      markSubs();
      [60, 700, 2000].forEach((t) => setTimeout(() => { markSubs(); renderHead(); scanCards(); }, t));
    });
    window.addEventListener('scroll', () => {
      if (!active) return;
      spy();
      // 頁首黏在最上面：捲下去之後才畫下框線（toggle 值沒變時不會改 DOM）
      if (head) head.classList.toggle('stuck', window.scrollY > 4);
    }, { passive: true });
    window.addEventListener('resize', () => {
      const w = WANT();
      if (w !== active) {
        if (w) activate(); else deactivate();
        /* 子分頁只有電腦版有：拉寬要把 #flow 導到子分頁，縮窄要讓 app.js 把「別的子分頁」那幾張卡補畫出來
           （手機版是整頁）—— 用 hashchange 請 route() 再跑一次，不另外寫一套 */
        /* 縮窄時資金流向不必重跑：拿掉 data-l4sub 之後藏起來的卡全部露出來，whenNear 的 IntersectionObserver 自己會把它們畫出來；
           重跑路由反而會讓資金去向在換寬度的同一刻被重新排一次（小圓點那層量到舊寬度，_uitest「新-資金流向」800px 抓到的）。
           熱力圖的題材／產業是 route() 裡直接畫的（沒有走 whenNear），所以縮窄時仍要重跑一次。 */
        const hp = location.hash || '';
        if (w ? /^#(flow|heatmap)(\/|$)/.test(hp) : /^#heatmap(\/|$)/.test(hp)) setTimeout(() => window.dispatchEvent(new HashChangeEvent('hashchange')), 0);
        return;
      }
      if (!active) return;
      if (!LS.get(NAV_KEY)) applyNav();
      queueScan(); spy(); fitNav();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
