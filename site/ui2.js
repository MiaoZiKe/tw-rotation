/* ==========================================================================
   新版介面 UI v2 —— 頁首說明、「本頁功能」跳轉列、導覽收合、事件浮層
   2026-09-26（分支 claude/elegant-pasteur-ggwgnb）。樣式在 ui2.css。

   ★ 這支**只讀畫面、只加裝飾**，不改任何功能：
     · 不碰路由、不碰資料、不重畫任何圖表；
     · 開關事件浮層一律呼叫 app.js 原本就開放的 window.twSetSide()（跟按「事件」鈕同一條路）；
     · 「本頁功能」是從目前這一頁的卡片標題**讀出來**的，卡片新增或改名時自動跟著變，不必維護清單。
   ========================================================================== */
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

  /* ---------------- 每一頁的「這頁回答什麼」 ----------------
     判斷順序是網站的核心：M1 資金面 → M2 基本面 → M3 技術面 → M4 事件面。
     這裡用一句話講清楚每一頁在那個順序裡的位置，讓第一次來的人知道從哪裡開始看。 */
  const PAGES = {
    overview: { grp: '今日市場', t: '總覽', d: '今天大盤怎麼走、錢集中在哪幾個族群、題材與法人在做什麼 —— 從這裡開始，一頁看完今天的重點。' },
    flow: { grp: '錢往哪裡跑', t: '資金流向', d: '錢正在往哪個族群跑：資金輪盤看輪動階段、排行看誰進誰出、資金去向看錢從哪裡流到哪裡。' },
    heatmap: { grp: '錢往哪裡跑', t: '熱力圖', d: '全市場與題材的冷熱一眼看完：方塊越大錢越多、顏色越紅漲越多；點方塊看成分股。' },
    industry: { grp: '族群與個股', t: '產業地圖', d: '每條產業鏈的強弱與上下游：先挑產業鏈，再看族群與零件，最後點個股看 K 線與基本面。' },
    stock: { grp: '族群與個股', t: '個股', d: 'K 線與多週期技術面、營收與獲利、籌碼與除權息 —— 決定「什麼時候進場」與「現在貴不貴」。' },
    market: { grp: '族群與個股', t: '市場明細', d: '完整名單：漲跌分佈、站上均線、各項排行，可以排序與篩選，找出符合條件的個股。' },
    season: { grp: '歷史規律', t: '週期統計', d: '每個族群在各月份的歷史表現：勝率、報酬中位數與超額報酬，看現在是不是它的旺季。' },
    delivery: { grp: '專案', t: '交付清單', d: '提出過的需求與完成狀態，逐條可以點過去驗收。' },
  };
  const ALIAS = { themes: 'heatmap', tasks: 'delivery' };
  /* 總覽頁首右邊的判斷四步（M1 → M2 → M3 → M4），每一步連到回答它的那一頁。
     第四步「有沒有理由不進場」連到今日事件 —— 那是浮層不是頁面，所以用 data-ev 由下面接去按「事件」鈕。 */
  const STEPS = '<nav class="steps" aria-label="判斷順序">'
    + '<a href="#flow"><b>STEP 1</b><span>錢往哪裡跑</span><small>資金流向</small></a>'
    + '<a href="#industry"><b>STEP 2</b><span>現在貴不貴</span><small>產業與估值</small></a>'
    + '<a href="#market"><b>STEP 3</b><span>何時進場</span><small>技術面名單</small></a>'
    + '<a href="#overview" data-ev="1"><b>STEP 4</b><span>有沒有理由不進場</span><small>今日事件</small></a>'
    + '</nav>';

  function curKey() {
    const h = (location.hash || '#overview').slice(1).split('/')[0] || 'overview';
    if (h === 'stock') return 'stock';
    const v = $('.view.on');
    if (v && v.id && v.id.startsWith('v-')) {
      const k = v.id.slice(2);
      if (k === 'industry' && $('#stockPage') && $('#stockPage').style.display !== 'none' && h === 'stock') return 'stock';
      return ALIAS[k] || k;
    }
    return ALIAS[h] || h;
  }

  /* ---------------- 頁首與跳轉列 ----------------
     放在 <main> 外面、#layout 前面（body 的直接子元素）：
     · 跳轉列是 sticky，要以整個 body 為範圍才黏得住整頁；
     · 它是「導覽」不是內容 —— 跟頂欄一樣不屬於 main，捲過去的卡片從它底下經過是設計，不是疊字。 */
  let head, jump, chips;
  function build() {
    const main = $('main'), lay = $('#layout'); if (!main || !lay) return false;
    head = document.createElement('header'); head.id = 'ui2Head';
    head.addEventListener('click', (e) => {
      const a = e.target.closest('a[data-ev]'); if (!a) return;
      e.preventDefault();
      const t = $('#evToggle'); if (t && $('#layout').classList.contains('noside')) t.click();
    });
    jump = document.createElement('nav'); jump.id = 'ui2Jump'; jump.setAttribute('aria-label', '本頁功能');
    jump.innerHTML = '<span class="lbl">本頁功能</span><div class="chips"></div>';
    chips = $('.chips', jump);
    lay.parentNode.insertBefore(head, lay);
    lay.parentNode.insertBefore(jump, lay);
    return true;
  }

  function chainName() {
    // 產業地圖的麵包屑最後一格（例如「AI 伺服器」「台積電 2330」）；app 自己畫的，這裡只讀
    const cur = $('#indCrumbs .cur');
    return cur ? cur.textContent.trim() : '';
  }
  let lastHead = '';
  function renderHead() {
    if (!head) return;
    const k = curKey(), p = PAGES[k] || { grp: '', t: (($('.tab.on') || {}).textContent || '').trim(), d: '' };
    let sub = '';
    if ((k === 'industry' || k === 'stock') && /^#(industry\/|stock\/)/.test(location.hash)) sub = chainName();
    const asof = (($('#buildver') || {}).textContent || '').trim();
    const sig = [k, p.t, sub, asof].join('|');
    if (sig === lastHead) return;
    lastHead = sig;
    const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
    head.innerHTML = `<div class="ph">${p.grp ? `<div class="eyebrow">${esc(p.grp)}</div>` : ''}`
      + `<h1>${esc(p.t)}${sub && sub !== p.t ? `<span class="sub1">${esc(sub)}</span>` : ''}</h1>`
      + (p.d ? `<p>${esc(p.d)}</p>` : '') + '</div>'
      + (k === 'overview' ? STEPS : '');
  }

  /* 「本頁功能」：目前這一頁、看得見的、最外層卡片的標題。
     標題裡的「?」鈕、下拉、日期、數字徽章都拿掉，只留字；太長就截。 */
  function cardTitle(card) {
    const h = card.querySelector(':scope > h3, :scope > .cardhd h3, :scope > .row h3, :scope > div > h3, h3');
    if (!h || h.closest('.card') !== card) return '';
    const c = h.cloneNode(true);
    c.querySelectorAll('button, select, input, small, svg, .howbtn, .pill, .muted, .note, [hidden], .rotdd, .seg, .n').forEach((x) => x.remove());
    let t = c.textContent.replace(/\s+/g, ' ').trim();
    t = t.replace(/[?？]$/, '').trim();
    if (t.length > 14) t = t.slice(0, 13) + '…';
    return t;
  }
  let cards = [], lastSig = '', io = null;
  function scanCards() {
    if (!jump) return;
    const view = $('.view.on');
    const list = view ? $$('.card', view).filter((c) => {
      if (c.parentElement && c.parentElement.closest('.card')) return false;      // 只要最外層
      if (!c.offsetParent && getComputedStyle(c).position !== 'fixed') return false;  // 看不見的不列
      return c.getBoundingClientRect().height > 40;
    }) : [];
    const items = [];
    const seen = new Set();
    list.forEach((c) => { const t = cardTitle(c); if (t && !seen.has(t)) { seen.add(t); items.push({ c, t }); } });
    const sig = curKey() + '|' + items.map((x) => x.t).join('|');
    if (sig === lastSig) return;
    lastSig = sig;
    cards = items;
    jump.hidden = items.length < 2;               // 只有一張卡的頁面不需要跳轉列
    chips.innerHTML = items.map((x, i) => `<button type="button" data-i="${i}"><i>${String(i + 1).padStart(2, '0')}</i>${x.t.replace(/</g, '&lt;')}</button>`).join('');
    $$('button', chips).forEach((b) => b.onclick = () => go(+b.dataset.i));
    spy();
  }
  function go(i) {
    const it = cards[i]; if (!it) return;
    it.c.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    it.c.classList.remove('ui2-hit'); void it.c.offsetWidth; it.c.classList.add('ui2-hit');
    setTimeout(() => it.c.classList.remove('ui2-hit'), 1300);
    lockUntil = Date.now() + 900;
    mark(i);
  }
  function mark(i) {
    $$('button', chips).forEach((b) => b.classList.toggle('on', +b.dataset.i === i));
    const on = $(`button[data-i="${i}"]`, chips);
    if (on) {
      const r = on.getBoundingClientRect(), s = chips.getBoundingClientRect();
      if (r.left < s.left || r.right > s.right - 28) chips.scrollBy({ left: r.left - s.left - s.width / 3, behavior: 'smooth' });
    }
  }
  /* 捲動時亮起「目前在看的那一張」：取頂端落在跳轉列下緣以下、最靠上的那張；捲到底就亮最後一張。 */
  let spyRaf = 0, lockUntil = 0;
  function spy() {
    if (spyRaf) return;
    spyRaf = requestAnimationFrame(() => {
      spyRaf = 0;
      if (!cards.length || !DESK()) return;
      jump.classList.toggle('stuck', jump.getBoundingClientRect().top <= 1 && window.scrollY > 10);
      if (Date.now() < lockUntil) return;          // 剛點過膠囊：捲動動畫跑完之前不要被偵測改掉
      const line = (jump.getBoundingClientRect().bottom || 60) + 24;
      /* 取「頂端已經過了基準線、而且最靠近基準線」的那張 ——
         並排的兩張卡（例如總覽的熱力圖｜輪盤）頂端不同高，不能只看 DOM 順序的最後一張。 */
      let best = 0, bestTop = -Infinity;
      cards.forEach((x, i) => { const t = x.c.getBoundingClientRect().top; if (t <= line && t > bestTop + 1) { best = i; bestTop = t; } });
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) best = cards.length - 1;
      mark(best);
    });
  }

  /* 卡片是非同步畫出來的（圖表、資料載入完才出現），所以用 MutationObserver 追，
     但只在「最外層卡片的組成」變了才重畫膠囊（scanCards 內部有簽章比對），盤中每分鐘的報價更新不會觸發重排。 */
  let scanT = 0;
  function queueScan() {            // 節流不是防抖：動畫中 DOM 一直在變時，防抖會永遠等不到
    if (scanT) return;
    scanT = setTimeout(() => { scanT = 0; renderHead(); scanCards(); }, 300);
  }

  /* ---------------- 導覽收合（寬 ↔ 圖示列） ----------------
     使用者按過就記住（tw.ui2.nav）；沒按過時，視窗 ≤1180px 自動收成圖示列，讓內容有地方放。 */
  const NAV_KEY = 'tw.ui2.nav';
  function applyNav() {
    const pref = LS.get(NAV_KEY);
    const mini = pref ? pref === 'mini' : (window.innerWidth <= 1180);
    const was = root.classList.contains('ui2-mini');
    root.classList.toggle('ui2-mini', mini);
    $$('.tab').forEach((t) => { if (mini) t.title = t.textContent.trim(); else t.removeAttribute('title'); });
    const btn = $('#ui2NavBtn');
    if (btn) { btn.title = mini ? '展開導覽' : '收合導覽'; const l = $('.lbl', btn); if (l) l.textContent = '收合'; }
    if (was !== mini) setTimeout(() => window.dispatchEvent(new Event('resize')), 260);   // 內容寬度變了，圖表重算尺寸
  }
  function buildFoot() {
    const bar = $('.topbar'); if (!bar) return;
    const foot = document.createElement('div'); foot.className = 'ui2-foot';
    const onV2 = /\/v2\//.test(location.pathname);
    foot.innerHTML = `<button type="button" id="ui2NavBtn"><span class="ic"></span><span class="lbl">收合</span></button>`
      + (onV2 ? `<a href="../${location.hash}" id="ui2Old" title="回到舊版介面（同一份資料）"><span class="ic"></span><span class="lbl">舊版介面</span></a>` : '');
    bar.appendChild(foot);
    $('#ui2NavBtn').onclick = () => {
      LS.set(NAV_KEY, root.classList.contains('ui2-mini') ? 'full' : 'mini');
      applyNav();
    };
    // 舊版連結要帶著目前的頁面走（換頁後 hash 變了）
    if (onV2) window.addEventListener('hashchange', () => { const a = $('#ui2Old'); if (a) a.href = '../' + location.hash; });
    if (onV2) {
      const b = $('.brand b');
      if (b && !$('.ui2-badge', b)) b.insertAdjacentHTML('beforeend', '<span class="ui2-badge">新版</span>');
    }
  }

  /* ---------------- 今日事件：桌機改成浮層 ----------------
     開關照舊是 app.js 的 setSide（掛 .layout.noside）；這裡只補浮層該有的兩個關法：
       · 點浮層外面任何地方就關 —— **但那一下照樣生效**（不用遮罩擋住）：
         舊版事件欄開著時，其他按鈕一樣按得動；改成浮層之後不能變成「要先關浮層才按得到」。
       · 按 Esc 關。
     兩種都用 remember=false：不改寫存起來的偏好（舊版介面跟這裡共用同一份 localStorage）。 */
  function wireDrawer() {
    const isOpen = () => { const l = $('#layout'); return !!l && !l.classList.contains('noside'); };
    const close = () => { if (typeof window.twSetSide === 'function') window.twSetSide(false, false); };
    document.addEventListener('pointerdown', (e) => {
      if (!DESK() || !isOpen()) return;
      if (e.target.closest('#side, #evToggle')) return;
      close();
    }, true);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && DESK() && isOpen()) close();
    });
  }

  /* 一進站事件浮層先關著。app.js 載完新聞才呼叫 setSide(記住的偏好)，
     那時可能把它打開 —— 桌機的浮層會整個蓋住內容，所以在使用者自己按過「事件」之前，
     開起來就再關回去（remember=false：不改寫存起來的偏好，舊版介面仍照他原本的設定）。 */
  function keepEventsClosed() {
    const lay = $('#layout'), tg = $('#evToggle');
    if (!lay) return;
    let touched = false;
    if (tg) tg.addEventListener('click', () => { touched = true; }, true);
    const shut = () => {
      if (touched || !DESK() || lay.classList.contains('noside')) return;
      if (typeof window.twSetSide === 'function') window.twSetSide(false, false, true);
    };
    new MutationObserver(shut).observe(lay, { attributes: true, attributeFilter: ['class'] });
    shut();
  }

  function init() {
    if (!build()) return;
    buildFoot();
    wireDrawer();
    applyNav();
    renderHead(); scanCards();
    const main = $('main');
    /* 只看「節點增減」：卡片出現／消失一定伴隨 childList。不看 class／style ——
       圖表動畫、盤中閃爍每秒都在改屬性，全部接進來會一直逼瀏覽器重排。
       換頁（.view.on 換人、產業頁 show() 改 display）另外由 hashchange 補掃三次。 */
    new MutationObserver(queueScan).observe(main, { childList: true, subtree: true });
    window.addEventListener('hashchange', () => {
      lastHead = '';
      [60, 700, 2000].forEach((t) => setTimeout(() => { renderHead(); scanCards(); }, t));
    });
    keepEventsClosed();
    window.addEventListener('scroll', spy, { passive: true });
    window.addEventListener('resize', () => { if (!LS.get(NAV_KEY)) applyNav(); spy(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
