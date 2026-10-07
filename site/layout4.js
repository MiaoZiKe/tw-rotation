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
   ★ 2026-10-03 第四批（Andy 看正式站：「這個登入功能不見了」「明暗用原來的圖示即可，並且都放在右上」「圖案換個圖案，畫在線上」
     ＋「子分頁每一個都要有自己的圖示」，DECISIONS #312）：
     ④ 的帳號卡與「淺色｜深色」拿掉 → 頁首右上角放 ☀／🌙（#themeBtn 本人）、外觀調色盤（#t4Btn）、登入（#acctBtn 本人；
        會員功能沒開時是一顆會講原因的 #l4Login）；② 的收合鈕改成騎在側欄分隔線上的圓形 «／» 小鈕；
        側欄子分頁加各自的圖示，收合時只顯示圖示。
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
    earnings: { grp: '今日市場', t: '財經日曆', d: '三大分類排在同一張月曆：公司財報（市值前 50 公告的財報董事會與已公布財報）、公司法說（全部上市櫃公司公告的法說會）、FED 消息（FOMC 與美國重大數據）；點一項看分析與說明。' },
    flow: { grp: '資金流水', t: '資金流向', d: '錢正在往哪個族群跑：輪盤看輪動階段、排行看誰進誰出、資金去向看錢從哪裡流到哪裡。' },
    heatmap: { grp: '資金流水', t: '熱力圖', d: '全市場與題材的冷熱一眼看完：方塊越大錢越多、越紅漲越多；點方塊看成分股。' },
    industry: { grp: '族群與個股', t: '產業地圖', d: '每條產業鏈的強弱與上下游：先挑產業鏈，再看族群與零件，最後點個股看 K 線與基本面。' },
    stock: { grp: '族群與個股', t: '個股', d: 'K 線與多週期技術面、營收與獲利、籌碼與除權息 —— 決定「什麼時候進場」與「現在貴不貴」。' },
    market: { grp: '族群與個股', t: '市場明細', d: '完整名單：漲跌分佈、站上均線、法人動向與各項排行，可以排序篩選，找出符合條件的個股。' },
    explore: { grp: '族群與個股', t: '選股策略', d: 'Strategy Lab：每張卡是一組公開條件（獲利、估值、成長、技術、法人、股利、動能），列出前 3 檔；點一列看入選原因，點 i 看條件與資料出處。' },
    season: { grp: '歷史規律', t: '週期統計', d: '每個族群在各月份的歷史表現：勝率、報酬中位數與超額報酬，看現在是不是它的旺季。' },
    etf: { grp: '族群與個股', t: 'ETF', d: 'ETF 分類、殖利率、配息行事曆與長期報酬比較（價格與含息分開算）—— 純資料整理，不構成投資建議。' },
    watch: { grp: '專案', t: '自選', d: '你自己的自選清單（最多五頁）：今天的漲跌與走勢，點名稱進個股頁。' },
    delivery: { grp: '專案', t: '交付清單', d: '提出過的需求與完成狀態，逐條可以點過去驗收。' },
  };
  const ALIAS = { themes: 'heatmap', tasks: 'delivery' };
  /* ★ 2026-10-03（Andy：「資金流向」四個本頁功能拆成三個側欄子分頁、「熱力圖」拆產業／題材）：
     側欄縮排子項。路由與「這一頁顯示哪幾張卡」在 app.js route()（<html data-l4sub>）＋ layout4.css；這裡只畫側欄那幾格、亮目前那格。
     短名（s）留給讀屏與滑鼠提示；ic 是圖示（site/icons.js 的 Lucide 鍵）。
     ★ 第四批（Andy：「子分頁每一個都要有自己的圖示」）：圖示放在字左邊、比主項目小一號（16 vs 19）；
       收合成圖示列時只顯示圖示（取代第三批的兩字短名），滑過有 title。
       資金輪動＝羅盤（輪盤看輪動階段）、資金去向＝分流箭頭（錢從哪裡分到哪裡）、族群×法人＝法人機構（landmark，法人＝機構）、
       產業＝格狀方塊（全市場 treemap 的樣子）、題材＝火焰（題材熱度；跟卡片標題的題材圖示同一個）。 */
  const SUBS = {
    flow: [
      { k: 'flow-rotation', h: '#flow/rotation', t: '資金輪動', s: '輪動', ic: 'compass' },
      { k: 'flow-sankey', h: '#flow/sankey', t: '資金去向', s: '去向', ic: 'split' },
      { k: 'flow-inst', h: '#flow/inst', t: '族群×法人＋集中度', s: '法人', ic: 'landmark' },
    ],
    heatmap: [
      { k: 'heat-industry', h: '#heatmap/industry', t: '產業', s: '產業', ic: 'treemap' },
      { k: 'heat-theme', h: '#heatmap/theme', t: '題材', s: '題材', ic: 'flame' },
    ],
  };
  /* 子分頁圖示：優先用 icons.js（全站同一套 Lucide、同一個線寬）；它被擋掉時退回這裡內嵌的同一組路徑 */
  const SUB_IC = {
    compass: '<circle cx="12" cy="12" r="10"/><path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/>',
    split: '<path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3"/><path d="m15 9 6-6"/>',
    landmark: '<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="M12 2 20 7H4z"/>',
    treemap: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    flame: '<path d="M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4"/>',
  };
  function subIcon(key) {
    const I = window.TwIcons;
    if (I && I.svg && I.ICONS && I.ICONS[key]) return I.svg(key, 16).replace('<svg ', '<svg class="ic" ');
    return '<svg class="ic" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
      + 'stroke-linejoin="round" focusable="false" aria-hidden="true">' + (SUB_IC[key] || '') + '</svg>';
  }
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
    /* 頁首三塊：頁名（每次換頁重寫）｜台北時間（每秒寫屬性）｜右上角工具（☀、外觀、登入 —— 別支檔的按鈕本人，只建一次、不重寫） */
    head.innerHTML = '<h1></h1><time class="l4clock" aria-live="off"></time><div class="l4tools" id="l4Tools"></div>';
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
    /* ★ 2026-10-03（Andy：「紅框處 只留下 總覽 及當下日期時間（所有分頁都是）」）：
       分組小標（eyebrow）、說明句（p）拿掉，只留頁名＋台北現在時間。「本頁功能」那排見 CSS（只藏不刪）。
       ★ 第四批：頁首右上角放了登入、明暗、外觀 —— 法律頁、管理頁這些不在 PAGES 的頁面也要按得到（#admin 要先登入），
       所以頁首不再整塊藏起來，只把頁名那一格清空。只重寫 h1，不碰右上角那幾顆（重寫 innerHTML 會把按鈕本人刪掉）。 */
    const h1 = $('h1', head);
    if (h1) {
      h1.hidden = !p;
      h1.innerHTML = p ? `${esc(p.t)}${sub && sub !== p.t ? `<span class="sub1">${esc(sub)}</span>` : ''}` : '';
    }
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


  /* ---------------- 側欄收展（2026-10-05，Andy 截圖圈「這邊點選可以收展」） ----------------
     ① 群組標題（今日市場／資金流水／族群與個股／歷史規律／專案）原本是 .tab::before（pointer-events:none，點不到），
        改成真的按鈕 .l4grp（不是 .tab —— 手機版、app.js、驗收腳本都在數 .tab），點一下收起／展開該組。
     ② 有子項的大項（資金流向、熱力圖）右邊一顆 ▸／▾（.l4car）收展子項；再點一次「已選中的大項」也是收展。
     ③ 狀態記在 localStorage（l4.navFold），讀寫都包 try/catch（LS）。
     ④ 2026-10-06 改（Andy：「收合後應該只會出現母分頁」）：收起就整組（含目前所在頁與它的子項）全部藏起來，只剩群組標題；目前頁在組裡時標題右邊那顆點提示「你在這組裡」。
     ⑤ 收合成圖示列（l4-mini）時整套不作用：標題按鈕藏起來、群組不收（圖示列本來就短，收了反而找不到）。 */
  const GROUPS = [
    { g: 'today', t: '今日市場', first: 'overview', views: ['overview', 'earnings'] },
    { g: 'money', t: '資金流水', first: 'flow', views: ['flow', 'heatmap'] },
    { g: 'stock', t: '族群與個股', first: 'industry', views: ['industry', 'stock', 'market', 'explore', 'etf'] },
    { g: 'hist', t: '歷史規律', first: 'season', views: ['season'] },
    { g: 'proj', t: '專案', first: 'watch', views: ['watch', 'delivery', 'admin'] },
  ];
  const FOLD_KEY = 'l4.navFold';
  function readFold() {
    try { const o = JSON.parse(LS.get(FOLD_KEY) || '{}'); return { g: Array.isArray(o.g) ? o.g : [], s: Array.isArray(o.s) ? o.s : [] }; }
    catch (e) { return { g: [], s: [] }; }
  }
  function applyFold() {
    const tabs = $('#tabs'); if (!tabs) return;
    const f = readFold();
    tabs.setAttribute('data-cg', f.g.join(' '));
    tabs.setAttribute('data-cs', f.s.join(' '));
    const curView = (($('.tab.on', tabs) || {}).dataset || {}).view || (($('.tab.on', tabs) || {}).id === 'l4Perm' ? 'admin' : '');
    $$('.l4grp', tabs).forEach((b) => {
      const shut = f.g.includes(b.dataset.g);
      const G = GROUPS.find((x) => x.g === b.dataset.g);
      b.setAttribute('aria-expanded', shut ? 'false' : 'true');
      b.classList.toggle('here', shut && !!G && G.views.includes(curView));
      b.title = (shut ? '展開「' : '收起「') + b.dataset.t + '」';
    });
    $$('.l4car', tabs).forEach((c) => {
      const shut = f.s.includes(c.dataset.p);
      c.setAttribute('aria-expanded', shut ? 'false' : 'true');
      c.title = shut ? '展開子項' : '收起子項';
    });
  }
  function toggleFold(kind, id) {
    const f = readFold(), arr = f[kind], i = arr.indexOf(id);
    if (i >= 0) arr.splice(i, 1); else arr.push(id);
    LS.set(FOLD_KEY, JSON.stringify(f));
    applyFold(); fitNav();
  }
  /* 2026-10-06（Andy：「管理區也需要收納」）：管理區跟資金流向一樣有 ▸／▾，收合鍵 'admin'。
     子項清單不寫死 —— CSS 只認 .l4subtab[data-parent="admin"]，另一分支拿掉「會員管理」也不用改這裡；沒有任何子項就不放箭頭。 */
  function addAdmCar() {
    const b = $('#l4Perm'); if (!b || $('.l4car', b)) return;
    if (!$('.l4subtab[data-parent="admin"]', $('#tabs'))) return;
    const c = document.createElement('span');
    c.className = 'l4car'; c.dataset.p = 'admin'; c.setAttribute('role', 'button'); c.tabIndex = 0;
    c.setAttribute('aria-label', '管理區子項收展');
    // 箭頭建立得比 applyFold 晚（管理者身分是非同步回來的），當場把方向設對，不能留一個沒有 aria-expanded 的箭頭
    const shut = readFold().s.includes('admin');
    c.setAttribute('aria-expanded', shut ? 'false' : 'true'); c.title = shut ? '展開子項' : '收起子項';
    b.appendChild(c);
  }
  function buildFold() {
    const tabs = $('#tabs'); if (!tabs) return;
    GROUPS.forEach((G) => {
      if ($(`.l4grp[data-g="${G.g}"]`, tabs)) return;
      const first = $(`.tab[data-view="${G.first}"]`, tabs); if (!first) return;
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'l4grp'; b.dataset.g = G.g; b.dataset.t = G.t; b.dataset.first = G.first;
      b.innerHTML = `<i class="car" aria-hidden="true"></i><span>${esc(G.t)}</span><i class="dot" aria-hidden="true"></i>`;
      b.addEventListener('click', (e) => { e.stopPropagation(); toggleFold('g', G.g); });
      first.before(b);
    });
    Object.keys(SUBS).forEach((v) => {
      const t = $(`.tab[data-view="${v}"]`, tabs); if (!t || $('.l4car', t)) return;
      const c = document.createElement('span');
      c.className = 'l4car'; c.dataset.p = v; c.setAttribute('role', 'button'); c.tabIndex = 0;
      c.setAttribute('aria-label', (PAGES[v] ? PAGES[v].t : v) + '子項收展');
      t.appendChild(c);
    });
    addAdmCar();
    if (!tabs._l4fold) {
      tabs._l4fold = true;
      /* capture：比 app.js 掛在每顆 .tab 上的「換 hash」先跑。
         2026-10-06 狀態機（Andy：「點擊母分頁名稱即可收合展開」）—— 每個有子項的母分頁各自一個展開／收合狀態（l4.navFold 的 s），
         箭頭方向＝aria-expanded＝子項可見性（CSS 只看 data-cs，沒有任何「目前頁例外」）：
           · 點箭頭 → 只切換，不導頁
           · 點母分頁名稱、已在這一頁 → 只切換，不導頁
           · 點母分頁名稱、不在這一頁 → 導到它（第一個子頁），而且若是收著就展開
           · 點子項、換頁 → 不動任何母分頁或群組的狀態 */
      tabs.addEventListener('click', (e) => {
        if (!active || root.classList.contains('l4-mini')) return;
        const car = e.target.closest('.l4car');
        if (car) { e.stopPropagation(); e.preventDefault(); toggleFold('s', car.dataset.p); return; }
        const tab = e.target.closest('.tab');
        const key = tab && (tab.id === 'l4Perm' ? ($('.l4subtab[data-parent="admin"]', tabs) ? 'admin' : '') : (SUBS[tab.dataset.view] ? tab.dataset.view : ''));
        if (!key) return;
        if (tab.classList.contains('on')) { e.stopPropagation(); e.preventDefault(); toggleFold('s', key); return; }
        const f = readFold();
        if (f.s.includes(key)) toggleFold('s', key);   // 收著 → 展開；導頁照常交給 app.js／syncPerm 的 onclick
      }, true);
      tabs.addEventListener('keydown', (e) => {
        const car = e.target.closest && e.target.closest('.l4car');
        if (car && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); e.stopPropagation(); toggleFold('s', car.dataset.p); }
      }, true);
    }
    root.classList.add('l4g');
    applyFold();
  }

  /* ---------------- 側欄子分頁（資金流向三格、熱力圖兩格） ----------------
     插在 #tabs 裡、各自的父頁後面；class 是 l4subtab（**不是 .tab**）—— 手機版、app.js 的分頁列、驗收腳本都是數 .tab，
     不能讓它們多算。≤820 deactivate() 整批拿掉。點了只是換 hash，其餘交給 app.js 的 route()。 */
  function buildSubs() {
    const tabs = $('#tabs'); if (!tabs || $('.l4subtab[data-l4sub]', tabs)) return;   // 只看資金流向／熱力圖那幾格（會員權限那格另外管，見 syncPerm）
    Object.keys(SUBS).forEach((v) => {
      const parent = $(`.tab[data-view="${v}"]`, tabs); if (!parent) return;
      let after = parent;
      SUBS[v].forEach((it) => {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'l4subtab'; b.dataset.l4sub = it.k; b.dataset.parent = v;
        b.innerHTML = `${subIcon(it.ic)}<span class="lbl">${esc(it.t)}</span>`;
        b.setAttribute('aria-label', it.t);
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
    syncPerm();
    if (active) applyFold();   // 換頁後「收起的群組裡有目前這頁」的提示點要跟著換
  }

  /* ---------------- 「專案 → 自選 → 會員權限」（2026-10-04，Andy：「多一個分頁，只有我這帳號及特定帳號可以用…分頁放在自選下」）----------------
     只有「已登入、而且 Worker 回報 admin=true」才**建立**這一格；訪客與一般會員的 DOM 裡根本沒有它（不是 hidden）——
     管理者名單仍然只在 Worker 的 ADMIN_EMAILS（不寫進 repo）。就算有人自己在網址打 #admin/perm，account.js 的 route 也只給管理者看內容、
     Worker 的 /v1/admin/* 也只回管理者；這一格只是入口。
     長相跟資金流向的子分頁一樣（l4subtab、縮排在「自選」下面），但不帶 data-l4sub：它是另一個頁面（#admin/perm），不是自選頁裡的一段。 */
  // 2026-10-05（admin-v2c，Andy）：子項順序改成「會員管理」在上、「會員權限」在下，流量觀測維持最後
  // 2026-10-07（Andy：意見反饋要留在站上、只有我看得到）：管理區下加「意見反饋」（#admin/feedback，support.js 畫；未讀數紅點由 support.js 填 TwSupport.unread）
  const ADM_SUBS = [['perm', '會員權限', 'admTabPerm', 'scale'], ['traffic', '流量觀測', 'admTabTraffic', 'gauge'], ['feedback', '意見反饋', 'admTabFeedback', 'mail'], ['admins', '管理權限', 'admTabAdmins', 'users']];   // 2026-10-07：誰擁有管理權限（admin.js renderAdmins）
  function isAdmin() { const A = window.TwAccount; const u = A && A.on && A.on() && A.user(); return !!(u && u.admin); }
  function syncPerm() {
    const tabs = $('#tabs');
    let b = $('#l4Perm');
    if (!active || !tabs || !isAdmin()) { if (b) b.remove(); $$('.l4subtab[data-parent="admin"]').forEach((x) => x.remove()); return; }
    if (!b) {
      const parent = $('.tab[data-view="watch"]', tabs); if (!parent) return;
      b = document.createElement('button');
      // ★ 2026-10-04 23:50 Andy：「是指在自選下方，不是列在自選裡面」→ 改成跟「自選」同一層的 .tab（不縮排、同字級、自己的圖示）
      b.type = 'button'; b.id = 'l4Perm'; b.className = 'tab l4perm';
      // 2026-10-05（admin-v2）：改成「管理區」入口 —— 會員權限／流量觀測三個子分頁在頁內頂部 tab
      b.textContent = '管理區';
      b.setAttribute('aria-label', '管理區'); b.title = '專案・管理區：會員權限／流量觀測（只有管理者看得到）';
      b.onclick = () => {
        if (/^#admin\b/.test(location.hash || '')) return;
        // 2026-10-06：子項清單不寫死（另一分支會拿掉會員管理）—— 有「會員權限」照舊進它（會員權限導覽段落與帳號選單都認這個入口），沒有才進第一個實際存在的子項
        const f1 = $('.l4subtab[data-parent="admin"][data-adm="perm"]', tabs) || $('.l4subtab[data-parent="admin"]', tabs);
        location.hash = '#admin/' + (f1 ? f1.dataset.adm : 'perm');
      };
      parent.after(b);
    }
    /* 2026-10-05（admin-v2b，Andy：頂部那排三顆搬到左側欄「管理區」下面當縮排子項，同資金流向的子分頁）。
       沿用 admTabPerm／admTabMembers／admTabTraffic 這三個 id（原本頁內頂部那排的 id），驗收與其他程式找得到同一個東西。
       有沒存的權限草稿時，換子頁先問一次（admin.js 的 TwAdmin.guard）。 */
    if (!$('.l4subtab[data-parent="admin"]', tabs)) {
      let after = b;
      ADM_SUBS.forEach(([k, t, id, ic]) => {
        const s = document.createElement('button');
        s.type = 'button'; s.className = 'l4subtab'; s.id = id; s.dataset.parent = 'admin'; s.dataset.adm = k;
        s.innerHTML = `${subIcon(ic)}<span class="lbl">${esc(t)}</span>`;
        s.setAttribute('aria-label', t); s.title = '管理區・' + t;
        s.onclick = () => {
          if (location.hash === '#admin/' + k) return;
          const G = window.TwAdmin; if (G && G.guard && !G.guard()) return;
          location.hash = '#admin/' + k;
        };
        after.after(s); after = s;
      });
    }
    const on = /^#admin\b/.test(location.hash || '');
    const m = /^#admin\/(perm|members|traffic|feedback|admins)\b/.exec(location.hash || ''), cur = on ? (m ? (m[1] === 'members' ? 'perm' : m[1]) : 'traffic') : '';
    // 子項亮著時「管理區」本身不實心反白（同一個位置不要亮兩格，同資金流向），但保留 .on 讓「在管理區裡」這件事查得到
    b.classList.toggle('on', on); b.classList.toggle('l4hassub', on);
    if (on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    $$('.l4subtab[data-parent="admin"]').forEach((x) => {
      const o = x.dataset.adm === cur;
      x.classList.toggle('on', o);
      if (o) x.setAttribute('aria-current', 'page'); else x.removeAttribute('aria-current');
    });
    const fbt = $('#admTabFeedback'), S2 = window.TwSupport;
    if (fbt && S2 && S2.paintDot) S2.paintDot();
    if (root.classList.contains('l4g')) addAdmCar();
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
    /* ★ 第四批（Andy：「圖案換個圖案，畫在線上」）：圖示從側欄方框換成雙箭頭（展開時 «、收合時 » —— CSS 轉 180°），
       位置從 logo 右側的方鈕改成**騎在側欄與內容之間那條分隔線上**的圓形小鈕（垂直在 logo 那一列）。
       仍是 .topbar 的直接子元素（不放進 .brand：.brand 有 onclick 回總覽），定位改成 absolute（.topbar 是 fixed，就是它的定位基準）。 */
    const brand = $('.brand', bar);
    bar.insertBefore(btn, brand ? brand.nextSibling : bar.firstChild);
    btn.onclick = (e) => {
      e.stopPropagation();
      LS.set(NAV_KEY, root.classList.contains('l4-mini') ? 'full' : 'mini');
      applyNav();
    };
  }

  /* ---------------- 頁首右上角：明暗鈕＋外觀調色盤＋登入（2026-10-03 第四批，DECISIONS #312） ----------------
     Andy：「這個登入功能不見了」「明暗用原來的圖示即可，並且都放在右上」。
     第三批把登入鈕塞進左欄底部的帳號卡、明暗改成「淺色｜深色」二段式 —— 兩樣都拿掉，改成：
       · 明暗＝**v4 原本那顆 #themeBtn 本人**（☀／🌙 由 app.js applyTheme() 寫字、onclick 也是 app.js 的），只是搬進頁首右上角；
       · 外觀調色盤＝theme4.js 的 #t4Btn 本人（面板定位本來就是「按鈕下緣＋8px、右緣對齊」，放在右上角剛好不用再挪）；
       · 登入＝account.js 的 #acctBtn 本人（未登入寫「登入」、已登入是頭像＋名字＋▾，點開是原本的帳號選單；
         帳號選單也是「按鈕下緣＋6px、右緣對齊」，同樣不用挪）。線上人數 #acctOnline 也一起搬過來，緊貼在登入鈕左邊。
     ★ 全部是「搬節點」不是「做新鈕」：id、onclick、account.js 的登入流程一行都沒碰；≤820（deactivate）時搬回原位。
     ★ 沒有會員設定檔（account.js 沒開）時：第三批的規則是「不放按了沒反應的登入鈕」——
       結果正式站看到的是「訪客／自選存在這台瀏覽器」、沒有任何登入入口，Andy 判斷成「登入功能不見了」，而我們從這個容器
       連不到正式站、沒辦法確認部署那一刻 account_config.js 到底有沒有填到網址（本機用同樣的設定檔重跑，登入鈕會出現）。
       所以改成：會員功能關著時，右上角照樣有一顆「登入」（#l4Login，不是 #acctBtn），按了用一小段字講清楚「這次部署沒有讀到
       會員伺服器設定、暫時不能登入、自選照樣存在這台瀏覽器」—— 入口不消失，原因直接寫在畫面上，下一次就不必猜。
       account.js 一開（tw:account-config）它就自己拿掉，換成真的 #acctBtn。 */
  const TOOL_ORDER = ['#themeBtn', '#t4Btn', '#acctOnline', '#acctBtn', '#l4Login'];
  let tools = null;
  function acctOn() { const A = window.TwAccount; return !!(A && A.on && A.on()); }
  function syncTools() {
    if (!active || !head) return;
    if (!tools || !tools.isConnected) tools = $('#l4Tools', head);
    if (!tools) return;
    // 會員功能關著才放 #l4Login；開了（或 #acctBtn 已經在）就拿掉
    let lg = $('#l4Login');
    const real = $('#acctBtn');
    if (!acctOn() && !real) {
      if (!lg) {
        lg = document.createElement('button');
        lg.type = 'button'; lg.id = 'l4Login'; lg.className = 'l4login';
        lg.textContent = '登入'; lg.title = '會員登入（目前沒有連上線）';
        lg.setAttribute('aria-haspopup', 'dialog'); lg.setAttribute('aria-expanded', 'false');
        lg.onclick = (e) => { e.stopPropagation(); loginTip(); };
      }
    } else if (lg) { lg.remove(); closeLoginTip(); lg = null; }
    // 照固定順序排：已經是這個順序就不動 DOM（避免自己觸發觀察器、也避免按鈕焦點被搬走）
    const want = TOOL_ORDER.map((s) => (s === '#l4Login' ? lg : $(s))).filter(Boolean);
    const cur = Array.from(tools.children);
    if (want.length !== cur.length || want.some((e, i) => cur[i] !== e)) want.forEach((e) => tools.appendChild(e));
  }
  /* 會員功能關著時，按「登入」跳出的說明（不是 account.js 的告知對話框 —— 那支沒開就什麼都不畫） */
  function loginTip() {
    let tip = $('#l4LoginTip');
    if (tip && !tip.hidden) { closeLoginTip(); return; }
    if (!tip) {
      tip = document.createElement('div');
      tip.id = 'l4LoginTip'; tip.className = 'l4logintip'; tip.setAttribute('role', 'dialog'); tip.setAttribute('aria-label', '會員登入');
      tip.innerHTML = '<b>會員系統目前沒有連上線</b>'
        + '<p>網站暫時連不到會員系統，所以現在不能登入。</p>'
        + '<p>自選清單照樣可以用，會存在這台瀏覽器。</p>';
      document.body.appendChild(tip);
    }
    tip.hidden = false;
    const b = $('#l4Login'); if (b) b.setAttribute('aria-expanded', 'true');
    const r = b ? b.getBoundingClientRect() : { bottom: 49, right: window.innerWidth - 16 };
    tip.style.top = Math.round(r.bottom + 8) + 'px';
    tip.style.left = Math.round(Math.max(8, Math.min(window.innerWidth - tip.offsetWidth - 8, r.right - tip.offsetWidth))) + 'px';
  }
  function closeLoginTip() {
    const tip = $('#l4LoginTip'); if (tip) tip.hidden = true;
    const b = $('#l4Login'); if (b) b.setAttribute('aria-expanded', 'false');
  }
  /* ≤820（deactivate）：右上角那幾顆搬回原位 —— #themeBtn／#t4Btn 回頂欄（#t4Btn 原本就插在 ☀ 前面），
     #acctOnline／#acctBtn 回 .acctbar（account.js 當初就是 append 進去的） */
  function restoreTools() {
    const bar = $('.topbar'), tb = $('#themeBtn'), t4 = $('#t4Btn'), abar = $('#acctBar'), mb = $('#moreBtn');
    // ☀ 原本在「⋯」（#moreBtn）前面：放回同一個位置，≤820 的頂欄排列才跟 main 一樣
    if (bar && tb && tb.parentNode !== bar) bar.insertBefore(tb, mb && mb.parentNode === bar ? mb : null);
    if (bar && t4 && tb && t4.parentNode !== bar) bar.insertBefore(t4, tb);
    ['#acctOnline', '#acctBtn'].forEach((s) => { const e = $(s); if (e && abar && e.parentNode !== abar) abar.appendChild(e); });
    const lg = $('#l4Login'); if (lg) lg.remove();
    const tip = $('#l4LoginTip'); if (tip) tip.remove();
    tools = null;
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

  /* 掛上：桌機（或手機旗標打開時）才有的整套東西 */
  function activate() {
    active = true;
    root.classList.add('l4');
    if (!DESK()) root.classList.add('l4m');
    build(); buildNavBtn(); buildSubs(); syncPerm(); buildFold();
    lastHead = ''; lastSig = '';
    applyNav();
    renderHead(); scanCards(); syncTools();
    fitNav();
  }
  /* 撤掉：回到 main 原本的頂欄 —— 插過的節點、掛過的 class、寫過的 inline style、補過的 title／aria-label 全部拿掉 */
  function deactivate() {
    active = false;
    clearTimeout(clockT);
    // ☀／外觀／登入／線上人數是別支檔的按鈕本人（被搬進頁首右上角）：拆頁首之前一定要先放回原位，不然會跟著 #l4Head 一起被刪掉
    restoreTools();
    ['#l4Head', '#l4Jump', '.l4foot', '#l4NavBtn', '.l4subtab', '.brand .l4pt', '.l4grp', '.l4car'].forEach((sel) => $$(sel).forEach((e) => e.remove()));
    root.removeAttribute('data-l4sub');      // 子分頁只有電腦版有；手機版要看到整頁（app.js route() 掛的）
    head = jump = chips = null; cards = []; lastHead = ''; lastSig = '';
    root.classList.remove('l4', 'l4-mini', 'l4m', 'l4g');
    root.style.removeProperty('--l4-tabs-h'); root.style.removeProperty('--l4-spine-h');
    if (root.getAttribute('style') === '') root.removeAttribute('style');
    $$('.tab').forEach((t) => { t.removeAttribute('title'); t.removeAttribute('aria-label'); });
    $$('.l4-hit').forEach((e) => e.classList.remove('l4-hit'));
    setTimeout(() => window.dispatchEvent(new Event('resize')), 60);   // 版面換回頂欄，讓圖表與分頁列重量一次
  }

  function init() {
    if (WANT()) activate(); else deactivate();
    const bar = $('.topbar');
    /* account.js 把 #acctBtn／#acctOnline 建在 .topbar 裡的 .acctbar、theme4.js 把 #t4Btn 插在 ☀ 前面 —— 都發生在 .topbar 裡：
       一有節點冒出來就搬到右上角。syncTools 已經是對的順序就不動 DOM，所以搬完觸發的那一次觀察不會再搬，不會無限循環。 */
    if (bar) new MutationObserver(() => { fitNav(); if (active) syncTools(); }).observe(bar, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['hidden', 'class', 'title'] });
    /* 會員功能晚一步才開（設定檔晚到）、登入／登出：換掉「沒開」那顆 #l4Login、補上真的 #acctBtn */
    ['tw:account', 'tw:account-config'].forEach((ev) => window.addEventListener(ev, () => { if (active) { syncTools(); syncPerm(); } }));
    document.addEventListener('pointerdown', (e) => { if (!e.target.closest('#l4LoginTip, #l4Login')) closeLoginTip(); }, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLoginTip(); });
    // 子分頁：app.js route() 一改 data-l4sub（含第一次進站、replace 導向）就亮對的那格、頁首補上子分頁名
    new MutationObserver((recs) => {
      if (!active) return;
      if (recs.some((r) => r.attributeName === 'data-l4sub')) { markSubs(); renderHead(); }
    }).observe(root, { attributes: true, attributeFilter: ['data-l4sub'] });
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
