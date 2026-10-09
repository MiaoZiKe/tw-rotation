/* ============================================================================
   ★ 手機版 v3（規格：docs/mobile_v3_spec.md；原型：docs/mobile_v3_proto/）
   Andy 2026-09-24：「補充文字可以用 ? 代替，點擊後會有說明；2D 3D 圖那麼多說明可以使用編號顯示就好，
   想知道再點編號，編號就會給出答案」＋ 已拍板的四條（大盤三張合一張、補充文字一律「?」、
   剖析圖只留編號、足跡輪盤套新雷達）。

   ⚠⚠ 桌機一個像素都不准變（Andy 2026-09-23：「除了桌面不可以遷就手機」）：
     · 這支檔插進 DOM 的每一個節點都**只在 ≤640px 插**，視窗一變寬就整個拆掉（`teardown()`）。
     · 樣式全部寫在 index.html 最後面的 `@media (max-width:640px)` 裡，而且一律掛在 `body.m3on` 底下。
     · 既有的桌機函式一個都不改行為；需要接手的地方（例如「?」在手機改成氣泡）
       只在 app.js 多一個「手機就走這條」的分支。
   斷點 640 跟第二版一樣（`docs/mobile_ia.md`「斷點為什麼是 640px」：800px 是「桌機縮半邊」，不是手機）。

   這一支分四段：
     A 共用元件：底部抽屜（M3.sheet）、「?」氣泡定位、編號層（M3.spread／M3.leaders，給 diagrams.js 用）
     B 骨架：底部一列五顆＋「更多」、頂欄 52px（搜尋收成一顆鈕）
     C 總覽＋資金流向：大盤三張合一張、足跡輪盤新雷達＋焦點條、資金分流樹長條、法人長條、篩選抽屜
     D 剖析圖：在 diagrams.js 的 DG.mobileNums（這支只提供共用的抽屜與推開算法）
     E 其他頁：熱力圖點方塊、市場明細分段、週期統計設定抽屜
     F 個股頁（券商 App 式，2026-09-27）：固定報價列＋橫捲分頁列＋分段鈕＋柱狀圖＋每日表
   ============================================================================ */
(function () {
  'use strict';
  const MAX = 640;
  const isM = () => window.innerWidth <= MAX;
  const $ = (s, r) => (r || document).querySelector(s);
  /* 2026-10-06 即時僅管理者（DECISIONS #326）：「完整版」那幾顆鈕的字只對管理者提「即時」—— 其他人點進去也看不到即時鈕 */
  const liveTxt = (s) => (window.TwLive && window.TwLive.allowed() ? s : s.replace(/、?盤中即時|、即時/g, ''));
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const LS = {
    get(k, d) { try { const v = localStorage.getItem('tw.m3.' + k); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('tw.m3.' + k, v); } catch (e) { /* 私密視窗 */ } },
  };
  /* 底部導覽一列的高度（CSS 同一個數字）。★ 2026-10-08 手機 v2（html.m4）拿掉底部導覽 → 0。 */
  const m4 = () => document.documentElement.classList.contains('m4');
  const navH = () => (m4() ? 0 : 58);

  /* ====================================================================== A 共用元件
     ---- 底部抽屜 ----
     點編號、點方塊、篩選、「更多」共用一個。最高 46vh、上緣 18px 圓角、拉柄；
     **點背景關**（沒有「收起」鈕，沿用 2026-09-24「不需要收起選項，點擊背景即可消除」），Esc 也關。*/
  let scrim = null, sheet = null, onClose = null;
  function ensureSheet() {
    if (sheet && sheet.isConnected) return;
    scrim = document.createElement('div'); scrim.className = 'msheetback'; scrim.id = 'mSheetBack'; scrim.hidden = true;
    sheet = document.createElement('div'); sheet.className = 'msheet'; sheet.id = 'mSheet'; sheet.hidden = true;
    sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-modal', 'true');
    sheet.innerHTML = '<div class="mgrab" aria-hidden="true"></div><div class="msheetbody"></div>';
    document.body.append(scrim, sheet);
    scrim.addEventListener('click', closeSheet);
  }
  function closeSheet() {
    if (!sheet || sheet.hidden) return;
    sheet.hidden = true; scrim.hidden = true;
    delete sheet.dataset.kind; delete sheet.dataset.no;
    const f = onClose; onClose = null;
    if (f) { try { f(); } catch (e) { /* 關閉時的收尾壞掉不該卡住抽屜 */ } }
  }
  /* html 可以是字串或節點；kind 寫在 data-kind（驗收用來確認開的是哪一種抽屜）。*/
  function openSheet(html, opts) {
    opts = opts || {};
    ensureSheet();
    closeSheet();
    const body = $('.msheetbody', sheet);
    body.innerHTML = '';
    if (typeof html === 'string') body.innerHTML = html; else if (html) body.appendChild(html);
    sheet.dataset.kind = opts.kind || '';
    sheet.hidden = false; scrim.hidden = false;
    sheet.scrollTop = 0;
    onClose = opts.onClose || null;
    return sheet;
  }
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });
  window.addEventListener('hashchange', closeSheet);

  /* ---- 「?」在手機的呈現：氣泡開在「?」的正下方，下面放不下才翻到上面 ----
     內容、開關、搬家都是 app.js howPop() 那一套（同一個委派監聽器），這裡只補「放在哪裡」。
     這個監聽器註冊得比 app.js 晚，所以同一次點擊裡它一定在 howPop 打開之後才跑。*/
  function placeHowPop(btn) {
    const pop = document.getElementById('howPop');
    if (!pop || pop.hidden || !isM()) return;
    pop.classList.add('mbubble');
    const r = btn.getBoundingClientRect(), vh = window.innerHeight;
    pop.style.top = '0px'; pop.style.maxHeight = '';
    const h = Math.min(pop.scrollHeight, vh * 0.56);
    const below = r.bottom + 8;
    /* ★ 2026-09-29（mobile-onescreen-fix）：上下都放不下時，不准蓋住「?」本身。
       改前：下面放不下就翻上去、頂端夾在 60px —— 360×780 總覽「資金輪盤 ?」的說明 332px 高，
       「?」在 377～409，上面只剩 309、下面只剩 297，翻上去夾在 60 之後框底到 392，**蓋住「?」15px**
       （箭頭指向的那顆被自己蓋掉，也點不到它來關）。
       改後：下面放得下＝正下方；上面放得下＝正上方（規格 R2 照舊）；兩邊都放不下＝挑空間大的那一邊，
       把框高限在那一邊的空間（框本來就 overflow:auto，內容一個字都沒少，只是在框裡捲），並標 data-scroll 讓底部淡出提示還有字。*/
    const roomB = vh - navH() - 8 - below, roomA = r.top - 8 - 60;
    let top;
    if (h <= roomB) top = below;
    else if (h <= roomA) top = r.top - 8 - h;
    else if (roomB >= roomA) { top = below; pop.style.maxHeight = Math.floor(roomB) + 'px'; }
    else { pop.style.maxHeight = Math.floor(roomA) + 'px'; top = r.top - 8 - Math.floor(roomA); }
    pop.style.top = Math.round(top) + 'px';
    const more = () => { pop.dataset.scroll = pop.scrollHeight - pop.clientHeight - pop.scrollTop > 1 ? '1' : '0'; };   // 捲到底就收掉淡出
    pop.scrollTop = 0; more();
    if (!pop._moreWired) { pop._moreWired = true; pop.addEventListener('scroll', () => { if (pop.classList.contains('mbubble')) more(); }, { passive: true }); }
    pop.style.setProperty('--arrow-x', Math.round(r.left + r.width / 2 - 12) + 'px');
    pop.dataset.flip = top < r.top ? '1' : '0';
  }
  document.addEventListener('click', (e) => {
    const b = e.target && e.target.closest && e.target.closest('.howbtn[data-how]');
    if (b && isM()) placeHowPop(b);
  });

  /* ---- 編號層：互相擋到的編號往外推（最多 8 輪），推開的拉一條細引線回原點 ----
     2D、3D 共用（diagrams.js 的 DG.mobileNums 與 3D 那一支都用這一份）。回傳推完之後還重疊的對數。*/
  /* ★ 2026-09-26 覆蓋普查（scripts/_dg_overlap.py）：3D 的層狀剖面（第三代半導體）十幾個編號排成一直欄，
     原本最多推 8 輪 —— 一整排互相擠的時候推不開（實測 09／10 還疊 6.5px）；呼叫端推完之後又把跑出畫面的鈕夾回邊界，
     夾回去就又疊上了。改成：最多推 40 輪，而且可以傳邊界 B（{x0,y0,x1,y1}），每一輪推完就夾一次，夾完再推。*/
  function spread(P, MIN, B) {
    const clamp = () => { if (!B) return; P.forEach((q) => { q.x = Math.max(B.x0, Math.min(B.x1, q.x)); q.y = Math.max(B.y0, Math.min(B.y1, q.y)); }); };
    for (let k = 0; k < 40; k++) {
      let moved = false;
      for (let a = 0; a < P.length; a++) for (let b = a + 1; b < P.length; b++) {
        const dx = P[b].x - P[a].x, dy = P[b].y - P[a].y, d = Math.hypot(dx, dy);
        if (d < MIN) {
          const push = (MIN - d) / 2 + 0.5, ux = d ? dx / d : (b % 2 ? 1 : -1), uy = d ? dy / d : 0;
          P[a].x -= ux * push; P[a].y -= uy * push; P[b].x += ux * push; P[b].y += uy * push; moved = true;
        }
      }
      clamp();
      if (!moved) break;
    }
    return overlaps(P, MIN);
  }
  function overlaps(P, MIN) {
    let ov = 0;
    for (let a = 0; a < P.length; a++) for (let b = a + 1; b < P.length; b++)
      if (Math.hypot(P[b].x - P[a].x, P[b].y - P[a].y) < MIN - 2) ov++;
    return ov;
  }
  const leaders = (P) => P.filter(p => Math.hypot(p.x - p.x0, p.y - p.y0) > 8)
    .map(p => `<path d="M${p.x0.toFixed(1)},${p.y0.toFixed(1)}L${p.x.toFixed(1)},${p.y.toFixed(1)}" stroke="${p.c}" stroke-width="1.2" fill="none" opacity=".8"/>`
      + `<circle cx="${p.x0.toFixed(1)}" cy="${p.y0.toFixed(1)}" r="2.5" fill="${p.c}"/>`).join('');

  /* ====================================================================== B 骨架
     ---- 底部導覽：一列五顆（總覽／資金流向／產業／熱力圖／更多），58px ----
     現行是兩列七顆 102px；多出來的 44px 全部給圖。市場明細／週期統計／交付清單收進「更多」
     （Andy：「可以多點頁面沒關係」）。三顆原本的分頁**還在 DOM 裡**，只是手機用 CSS 藏起來 ——
     路由、驗收、桌機全部照舊。「更多」這顆只在手機插，不帶 `.tab`（route() 的 `$$('.tab')` 不會碰到它）。*/
  /* ★ 2026-09-28（Andy：「"自選分頁替代"交付清單」）：「更多」裡的交付清單換成自選（#watch）。
     交付清單的網址 #delivery 照樣打得開，只是入口收掉（桌機導覽列同一件事）。*/
  /* ★ 2026-10-06：ETF 專區、財經日曆（10-05 新增的頂層分頁）一起收進「更多」—— 沒收的話五欄格線被擠成兩列，「更多」掉到畫面外（index.html 同日註解）。*/
  const MORE_VIEWS = ['market', 'season', 'etf', 'earnings', 'watch'];
  /* ★ 2026-10-04「會員權限」（#admin/perm）：跟電腦版側欄同一條規則 —— 只有登入且 Worker 回報 admin=true 才「畫」這一列，
     訪客與一般會員的清單 HTML 裡根本沒有它。清單每次打開都重畫，所以登入／登出之後下一次打開就對。 */
  const isAdmin = () => { const A = window.TwAccount; const u = A && A.on && A.on() && A.user(); return !!(u && u.admin); };
  function buildNav() {
    const tabs = document.getElementById('tabs');
    /* ★ 2026-10-08 手機 v2：底部五格＋「更多」退役，換成 mobile4.js 的漢堡鈕側欄抽屜（分組照桌機側欄）。
       改前：底部一列五顆＋「更多」抽屜；改後：不插 #mTabMore，已經插過的拿掉。 */
    if (m4()) { const old = document.getElementById('mTabMore'); if (old) old.remove(); return; }
    if (!tabs) return;
    let b = document.getElementById('mTabMore');
    if (!b) {
      b = document.createElement('button');
      b.type = 'button'; b.id = 'mTabMore'; b.className = 'mtabmore';
      b.setAttribute('aria-haspopup', 'dialog');
      b.textContent = '更多';
      b.onclick = openMore;
      tabs.appendChild(b);
    }
    syncNav();
  }
  function curView() { return (location.hash.replace('#', '').split('/')[0]) || 'overview'; }
  function syncNav() {
    const b = document.getElementById('mTabMore');
    if (b) b.classList.toggle('on', MORE_VIEWS.includes(curView()));
  }
  function openMore() {
    const ver = (document.getElementById('buildver') || {}).textContent || '';
    const evn = (document.getElementById('evCount') || {}).textContent || '0';
    const theme = document.documentElement.dataset.theme === 'light' ? '深色主題' : '明亮主題';
    const v = curView();
    const row = (id, ic, txt, extra, on) => `<button type="button" class="mrow${on ? ' on' : ''}" data-m="${id}"><span class="ic">${ic}</span>${txt}${extra || ''}</button>`;
    const sh = openSheet(`<div class="mshhead"><b>更多</b></div>
      <div class="mgrp">頁面</div>
      ${row('market', '▦', '市場明細', '<small>漲跌家數、站上均線、完整名單</small>', v === 'market')}
      ${row('season', '◷', '週期統計', '<small>族群 × 月份的歷史表現</small>', v === 'season')}
      ${row('etf', '◫', 'ETF', '<small>配息、市值、主題型 ETF 一覽</small>', v === 'etf')}
      ${row('earnings', '▣', '財經日曆', '<small>財報、法說會、FED 消息</small>', v === 'earnings')}
      ${row('watch', '★', '自選', '<small>最多五頁的自選清單</small>', v === 'watch')}
      ${isAdmin() ? row('perm', '⛨', '管理區', '<small>會員權限／流量觀測</small>', /^#admin\b/.test(location.hash)) : ''}
      <div class="mgrp">工具</div>
      ${row('events', '▤', '今日事件', `<span class="n">${esc(evn)}</span>`)}
      ${row('theme', '☀', '切換成' + theme)}
      <div class="mver">網頁版號 <span class="mono">${esc(ver.trim() || '—')}</span></div>`, { kind: 'more' });
    sh.querySelectorAll('.mrow').forEach(r => r.onclick = () => {
      const m = r.dataset.m;
      closeSheet();
      if (MORE_VIEWS.includes(m)) { location.hash = '#' + m; return; }
      if (m === 'perm') { location.hash = '#admin/perm'; return; }
      // 不重寫邏輯：一律去按桌機原來那顆鈕（跟頂欄「⋯」同一條路，見 app.js initMore）
      const t = document.getElementById(m === 'events' ? 'evToggle' : 'themeBtn');
      if (t) t.click();
    });
  }

  /* ---- 頂欄 52px：搜尋框收成一顆鈕，點了展開成整列 ----
     搜尋框本身（#q 與建議清單 #sugg）一個字都沒改，只是平常藏起來；
     展開時蓋住頂欄那一列，點旁邊的「取消」或按 Esc 收回。*/
  function buildTop() {
    const bar = $('.topbar'), s = $('.topbar .search');
    if (!bar || !s) return;
    let b = document.getElementById('mSearchBtn');
    if (!b) {
      b = document.createElement('button');
      b.type = 'button'; b.id = 'mSearchBtn'; b.className = 'msearchbtn';
      b.setAttribute('aria-label', '搜尋個股（代號或簡稱）');
      b.textContent = '⌕';
      s.before(b);
      b.onclick = () => {
        bar.classList.add('msearch');
        const q = document.getElementById('q'); if (q) { q.focus(); }
        /* ★ 2026-09-27 手機按鈕普查：展開的搜尋列蓋住整條頂欄（左上品牌、搜尋鈕都在它底下），
           以前只有「取消」和 Esc 收得回來 —— 點旁邊空白處它還開著，頂欄那兩顆就一直點不到。
           改成登記進全站那一份「點外面就關」（app.js dismissable：按下記位置、放開才關，
           手指滑動捲頁不算；用 pointer 事件，iPhone 點在一般背景上也收得到）。
           點搜尋框本身、建議清單（都在 .search 裡）不算外面。 */
        if (window.App && App.dismissable) {
          App.dismissable(s, () => bar.classList.remove('msearch'),
            { ignore: ['#mSearchBtn'], isOpen: () => bar.classList.contains('msearch') && isM() });
        }
      };
      let c = document.getElementById('mSearchX');
      if (!c) {
        c = document.createElement('button');
        c.type = 'button'; c.id = 'mSearchX'; c.className = 'msearchx'; c.textContent = '取消';
        s.appendChild(c);
        c.onclick = (e) => { e.stopPropagation(); bar.classList.remove('msearch'); };
      }
    }
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { const bar = $('.topbar'); if (bar) bar.classList.remove('msearch'); }
  });
  window.addEventListener('hashchange', () => { const bar = $('.topbar'); if (bar) bar.classList.remove('msearch'); });

  /* ====================================================================== 生命週期
     每次換頁（hashchange）與視窗寬度跨過 640 都重跑一次。桌機一律拆乾淨。*/
  const hooks = [];                        // C／D 段各自登記「手機要做的事」與「回桌機要拆的東西」
  function teardown() {
    document.body.classList.remove('m3on');
    ['mTabMore', 'mSearchBtn', 'mSearchX', 'mSheet', 'mSheetBack'].forEach(id => { const e = document.getElementById(id); if (e) e.remove(); });
    sheet = null; scrim = null;
    const bar = $('.topbar'); if (bar) bar.classList.remove('msearch');
    const hp = document.getElementById('howPop');
    if (hp) { hp.classList.remove('mbubble'); hp.style.top = ''; hp.style.maxHeight = ''; delete hp.dataset.scroll; }
    hooks.forEach(h => { if (h.off) { try { h.off(); } catch (e) { /* 拆不乾淨不該讓桌機掛掉 */ } } });
  }
  function apply() {
    if (!isM()) { if (document.body.classList.contains('m3on')) teardown(); return; }
    document.body.classList.add('m3on');
    buildNav(); buildTop();
    /* 先把手機版要用的資料抓進來（瀏覽器會快取）：切到資金流向時不必等網路，雷達與排行當場就畫得出來 */
    load('flow_v3'); load('sankey_daily');
    hooks.forEach(h => { if (h.on) { try { h.on(curView()); } catch (e) { console.warn('[m3]', e); } } });
  }
  let rt = null;
  let wasM = isM();
  /* ★ 2026-10-02 卡頓（DECISIONS #284）：不理自己 apply() 裡 m3go(…, quiet) 派的回聲（e.twEcho === 'm3'）——
     以前 apply() → m3go() → 40ms 後派 resize → 200ms 後又 apply() → …，手機寬度下每 0.25 秒一輪停不下來。
     其他 resize（真的視窗變動、app.js 分段排完派的那一下、使用者切卡片／分頁）照舊會 apply()。*/
  window.addEventListener('resize', (e) => {
    if (e.twEcho === 'm3') return;
    clearTimeout(rt);
    rt = setTimeout(() => { const now = isM(); if (now !== wasM || now) { wasM = now; apply(); } }, 200);
  });
  window.addEventListener('hashchange', () => { syncNav(); setTimeout(apply, 60); });


  /* ====================================================================== C 總覽＋資金流向
     做法（每一張都一樣）：手機專屬的內容插在**既有卡片裡面**（`.m3keep`），卡片掛 `.m3host`，
     CSS 把卡片裡其餘桌機內容藏起來 —— 分段導覽（modules.js）藏的是卡片本身，所以不必改分段表。
     每張卡最下面一顆「完整版 ›」（`.mfullbtn`）把桌機那一份叫回來（回放、即時、放大都在那裡）：
     **收起來可以，刪掉不行**。*/
  const cache = {};
  const load = (n) => cache[n] || (cache[n] = (window.TwGw && window.TwGw.on()) ? window.TwGw.json(n, { cache: 'no-cache' })   // data-gw：付費檔走 gateway
    : fetch('data/' + n + '.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null));
  const cssv = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const sgn = (v, d) => (v > 0 ? '+' : '') + (+v).toFixed(d == null ? 1 : d);
  const ucls = (v) => v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
  const yi = (v) => (v / 1e8).toFixed(v >= 1e11 ? 0 : 1);
  const ST = { improving: '改善', leading: '領先', weakening: '轉弱', lagging: '落後' };
  const stc = (q) => cssv(({ improving: '--cyan', leading: '--rise', weakening: '--amber', lagging: '--fall' })[q] || '--flat');
  const light = () => document.documentElement.dataset.theme === 'light';

  function host(card, key, html, opts) {
    if (!card) return null;
    let box = card.querySelector(':scope > .m3keep[data-k="' + key + '"]');
    if (!box) {
      box = document.createElement('div'); box.className = 'm3keep'; box.dataset.k = key;
      if (opts && opts.after) opts.after.after(box); else card.insertBefore(box, card.firstChild);
      if (html != null) box.innerHTML = html;
    }
    /* ⚠ 這裡**不**掛 .m3host（它會把桌機那一份藏掉）：等資料回來、手機版真的畫好了才掛（見各支的 ready）。
       慢網路下先藏桌機、手機版又還沒畫，整張卡就是一片空白 —— 2026-09-25 合 main 時「手機」段量到只剩 30 個字。*/
    let fb = card.querySelector(':scope > .mfullbtn');
    if (opts && opts.full && !fb) {
      fb = document.createElement('button'); fb.type = 'button'; fb.className = 'mfullbtn m3keep';
      card.appendChild(fb);
      const sync = () => { fb.textContent = card.classList.contains('mfull') ? '收回手機版 ‹' : opts.full + ' ›'; };
      fb.onclick = () => { card.classList.toggle('mfull'); sync(); setTimeout(() => window.dispatchEvent(new Event('resize')), 60); };
      sync();
    }
    return box;
  }
  function unhost() {
    $$('.m3host').forEach(c => { c.classList.remove('m3host', 'mfull'); });
    $$('.m3keep').forEach(e => e.remove());
  }

  /* ---- 足跡輪盤（新雷達長相）：R4，照桌機 ROT_GRAD_V2 那一版 ----
     象限底色離圓心越遠越濃（深色 .12→.27、淺色 .07→.18）、三圈刻度＋兩圈虛線、十字軸、盤緣 72 刻、
     四角膠囊徽章（象限名＋族群數，點了只看那一段）、淡淡的掃描（系統「減少動態效果」就不畫）、
     前掌＋腳跟的小腳印（佔比前 3 的最近 8 天；09-26 稍早拿掉、當晚依 Andy「先退回到有腳印那版本」畫回來）、點＝發光核心＋1px 白外圈、名字＝點右側的小膠囊（佔比前 5＋選到的）。
     座標換算跟 app.js renderRotation 的 pos() 同一條：兩軸各除以今天的最大偏離，盤內半徑取平方根（2026-10-04），外圈虛線＝今天偏離最大的族群。*/
  const MAXR = 1.25, TAIL = 0.18;
  function radarPos(points) {
    let sx = 1e-6, sy = 1e-6;
    points.forEach(r => { sx = Math.max(sx, Math.abs(r.x - 100)); sy = Math.max(sy, Math.abs(r.y - 100)); });
    const raw = (x, y) => Math.hypot((x - 100) / sx, (y - 100) / sy);
    let sr = 1e-9, srAll = 1e-9;
    points.forEach(r => { sr = Math.max(sr, raw(r.x, r.y)); (r.trail || []).slice(-9).forEach(w => { srAll = Math.max(srAll, raw(w[1], w[2])); }); });
    srAll = Math.max(srAll, sr);
    const span = Math.max(1e-6, srAll / sr - 1), RIM = MAXR * (1 + TAIL);
    return (x, y) => {
      const dx = (x - 100) / sx, dy = (y - 100) / sy;
      const u = Math.hypot(dx, dy) / sr;
      // 2026-10-04 中心太擠：盤內用 √u（跟 app.js pos() 同一條；內圈虛線＝最大偏離的 25%）
      const k = u <= 1 ? Math.sqrt(u) : 1 + TAIL * (u - 1) / span;
      return [Math.min(RIM, k * MAXR) / RIM, Math.atan2(dy, dx)];
    };
  }
  function radar(el, all, opts) {
    opts = opts || {};
    const cw = el.clientWidth, W = Math.round(cw || 340);
    let S = Math.min(W, opts.max || 360);
    /* ★ 2026-09-25（stale-reds）：輪盤大小「量到可信的一次就記住」，之後點東西重畫都沿用。
       改前：每次重畫（點一顆點、點角落徽章）都重量「輪盤頂端」來決定大小。第一次畫的時候容器還沒排版
       （寬 0、頂端 0）→ 一律 340px；使用者一點才量到真正的頂端 → 資金流向縮成 290px。
       結果是**每點一下整個盤面就縮一圈、所有點都跳位置**，看起來像點錯東西。
       改後：
         · 寬 0（還沒排版）：先用 340 畫，不記；ResizeObserver 等它真的有寬度再重畫一次。
         · 量得到寬、而且輪盤頂端在第一屏之內（頂端 < 視窗高）：照「塞得進一屏」算大小，記住。
         · 頂端還在第一屏外（實測總覽剛換頁那一刻會量到 1483px —— 上面的桌機內容還沒藏）：
           量到的東西不可信，先用「欄寬」畫、不記，等下一次重畫再量。
       記憶的鍵是「容器寬 × 視窗高」，轉向或縮放視窗才重量。
       ResizeObserver 只在寬度真的變了才重畫（高度跟著大小變不算），不會自己繞圈。*/
    el._radarArgs = [all, opts];
    if (!el._radarRO && window.ResizeObserver) {
      let lastW = cw;
      el._radarRO = new ResizeObserver(() => {
        const w = el.clientWidth;
        if (w && w !== lastW && el.isConnected) { lastW = w; radar(el, el._radarArgs[0], el._radarArgs[1]); }
      });
      el._radarRO.observe(el);
    }
    /* 依「可視高度 − 輪盤頂端 − 底部導覽 − 下面要放的東西」決定大小（下限 260）：先保數字，再給圖 */
    /* ★ 2026-09-25（clock-mobile-reds）：輪盤上方的東西晚一步才插進來時，記住的大小要作廢重量。
       實測 390×844 資金流向：第一次量的時候上方的分段列（.mpager，app.js 在卡片畫完之後才插）還不在，
       輪盤頂端量到 139px → 記住 324px 的盤；分段列插進來把整張卡往下推 36px（頂端變 175），
       盤卻還是 324 —— 排行第 5 名的底落在 794px，被底部導覽（786 以下）蓋掉半列，第一屏看不完。
       上面那段「量到可信的一次就記住」只防「點一下就縮一圈」，防不到「上方版面後來才變」。
       做法：盯住整個分頁（.view）的大小；它一變就比「輪盤在頁面上的頂端」跟記住的時候差多少，
       差超過 2px 才作廢重量、重畫一次。點盤面、點角落不會改變輪盤頂端，所以不會讓盤面跳。*/
    if (opts.fitBelow && !el._radarTopRO && window.ResizeObserver) {
      el._radarTopRO = new ResizeObserver(() => {
        if (!el.isConnected || !el.clientWidth || el._radarTop == null) return;
        const t = el.getBoundingClientRect().top + window.scrollY;
        if (Math.abs(t - el._radarTop) > 2) { el._radarKey = null; el._radarTop = null; radar(el, el._radarArgs[0], el._radarArgs[1]); }
      });
      el._radarTopRO.observe(el.closest('.view') || document.body);
    }
    if (opts.fitBelow && cw) {
      const key = W + 'x' + window.innerHeight;
      if (el._radarKey === key) S = el._radarS;
      else {
        const vtop = el.getBoundingClientRect().top;
        if (vtop < window.innerHeight) {
          S = Math.max(260, Math.min(S, Math.floor(window.innerHeight - navH() - (vtop + window.scrollY) - opts.fitBelow)));
          el._radarKey = key; el._radarS = S; el._radarTop = vtop + window.scrollY;
          /* ★ 2026-10-06（既有紅字清理，_uitest 足跡輪盤 ⑤）：記住之後 0.7 秒再對一次頂端。
             實測 390×844 資金流向：第一次量時輪盤頂端在 197，之後上方版面收了 4px（193）但整個分頁高度沒變，
             上面那支盯 .view 大小的 ResizeObserver 不會叫 —— 直到使用者點角落徽章（焦點條換字、分頁變高）才重量，
             盤面 268 → 272、每顆點跟著挪 1～2px，看起來就是「點一下盤面跳一下」（09-25 修過的同一個症狀）。
             在使用者動手之前把它量準，點角落就不會再動。只對一次、差超過 2px 才重畫。 */
          if (!el._radarSettle) {
            el._radarSettle = setTimeout(() => {
              el._radarSettle = null;
              if (!el.isConnected || el._radarTop == null || !el.clientWidth) return;
              const t = el.getBoundingClientRect().top + window.scrollY;
              if (Math.abs(t - el._radarTop) > 2) { el._radarKey = null; el._radarTop = null; radar(el, el._radarArgs[0], el._radarArgs[1]); }
            }, 700);
          }
        }
      }
    }
    const c = S / 2, R = c - 30;
    /* ★ 2026-09-25（stale-reds）：尺度改從「盤上那 16 顆」算，不再從全部族群算。
       改前：radarPos(all) —— 全部約 50 個族群（含沒畫上盤的小族群）一起決定「今天最大偏離」。
       改後：radarPos(top16) —— 跟桌機 renderRotation 一樣（桌機的 `scope` 就是盤上的 top0）。
       為什麼：沒上盤的小族群常常偏離最大（成交值小、相對強弱一跳就很大），
       用它當尺，盤上的 16 顆全被壓在圓心 25% 以內 —— 390 手機實測 16 顆有 15 對圓點互相重疊、
       名字膠囊被擠離自己的點，使用者根本分不出誰是誰；外圈虛線「今天偏離最大的族群」也對應到一顆看不到的點。
       這支上面的註解本來就寫「跟 app.js 的 pos() 同一條」，是實作跟註解對不上。
       象限篩選（quad）刻意放在算尺之後：點角落只看一段時，點的位置不跳。*/
    const top16 = all.slice().sort((a, b) => b.share - a.share).slice(0, opts.top || 16);
    const pos = radarPos(top16);
    const shown = top16.filter(p => !opts.quad || p.quadrant === opts.quad);
    const xy = (x, y) => { const [r, a] = pos(x, y); return [c + Math.cos(a) * r * R, c - Math.sin(a) * r * R]; };
    const ringR = R / (1 + TAIL);
    const Q = [['leading', 0], ['improving', 90], ['lagging', 180], ['weakening', 270]];
    const A = light() ? [.07, .10, .14, .18] : [.12, .17, .22, .27];
    const ink3 = cssv('--ink-3'), line = cssv('--line-2'), cyan = cssv('--cyan');
    const uid = el.id || 'mr';
    let g = '<defs>';
    Q.forEach(([q]) => {
      const col = stc(q);
      g += `<radialGradient id="${uid}-${q}" cx="${c}" cy="${c}" r="${R}" gradientUnits="userSpaceOnUse">`
        + `<stop offset="0" stop-color="${col}" stop-opacity="${A[0]}"/><stop offset=".42" stop-color="${col}" stop-opacity="${A[1]}"/>`
        + `<stop offset=".85" stop-color="${col}" stop-opacity="${A[2]}"/><stop offset="1" stop-color="${col}" stop-opacity="${A[3]}"/></radialGradient>`;
    });
    g += `<linearGradient id="${uid}-scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${cyan}" stop-opacity="0"/><stop offset="1" stop-color="${cyan}" stop-opacity=".12"/></linearGradient>`
      + `<filter id="${uid}-glow" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="2.4"/></filter></defs>`;
    const arc = (a0, a1, r) => {
      const p = (a) => [c + Math.cos(a * Math.PI / 180) * r, c - Math.sin(a * Math.PI / 180) * r];
      const [x0, y0] = p(a0), [x1, y1] = p(a1);
      return `M${c},${c} L${x0.toFixed(1)},${y0.toFixed(1)} A${r},${r} 0 0 0 ${x1.toFixed(1)},${y1.toFixed(1)} Z`;
    };
    Q.forEach(([q, a]) => { g += `<path d="${arc(a, a + 90, R)}" fill="url(#${uid}-${q})" opacity="${opts.quad && opts.quad !== q ? .35 : 1}"/>`; });
    [.25, .5, .75].forEach(f => { g += `<circle cx="${c}" cy="${c}" r="${(R * f).toFixed(1)}" fill="none" stroke="${line}" stroke-opacity=".35" stroke-width=".6"/>`; });
    g += `<circle cx="${c}" cy="${c}" r="${(ringR / 2).toFixed(1)}" fill="none" stroke="${ink3}" stroke-opacity=".55" stroke-dasharray="3 4"/>`;
    g += `<circle cx="${c}" cy="${c}" r="${ringR.toFixed(1)}" fill="none" stroke="${ink3}" stroke-opacity=".7" stroke-dasharray="5 4"/>`;
    [[ringR / 2, '25%'], [ringR, '100%']].forEach(([rr, t]) => { g += `<text x="${c + 3}" y="${(c - rr - 2).toFixed(1)}" font-size="11" fill="${ink3}" fill-opacity=".85">${t}</text>`; });
    g += `<circle cx="${c}" cy="${c}" r="${R}" fill="none" stroke="${line}" stroke-width="1.2"/>`;
    g += `<path d="M${c - R},${c}H${c + R}M${c},${c - R}V${c + R}" stroke="${line}" stroke-width=".8"/>`;
    for (let i = 0; i < 72; i++) {
      const a = i * 5 * Math.PI / 180, L = i % 9 === 0 ? 8 : 3.5;
      g += `<path d="M${(c + Math.cos(a) * R).toFixed(1)},${(c - Math.sin(a) * R).toFixed(1)}L${(c + Math.cos(a) * (R - L)).toFixed(1)},${(c - Math.sin(a) * (R - L)).toFixed(1)}" stroke="${ink3}" stroke-opacity="${L > 4 ? .8 : .4}" stroke-width=".8"/>`;
    }
    g += `<g class="mrscan" style="transform-origin:${c}px ${c}px"><path d="${arc(0, 45, R)}" fill="url(#${uid}-scan)"/><path d="M${c},${c}L${c + R},${c}" stroke="${cyan}" stroke-opacity=".35" stroke-width="1"/></g>`;
    /* ★ 2026-09-26 晚（Andy：「先退回到有腳印那版本」）：佔比前 3 名身後那串小腳印（最近 8 天）畫回來。
       改前（同日稍早）：「足跡輪盤只需要留下圓圈即可」→ 手機這張直接不畫腳印。
       改後：回到 09-25 的畫法。手機這張沒有自己的開關，但跟桌機讀同一個偏好 `tw.rot.feet` ——
       只有使用者在桌機勾掉過（'0'）才不畫，沒有值就畫（跟桌機預設勾選一致）。*/
    let feet = opts.feet !== false;
    /* ★ 2026-09-28（Andy：「首頁 -> 資金輪盤不需要標示軌跡，只要標示點即可」）：總覽那一張傳 feet:false，一律不畫；
       資金流向那一張照舊跟桌機的偏好走（DECISIONS #274）。*/
    try { if (feet && localStorage.getItem('tw.rot.feet') === '0') feet = false; } catch (e) { /* 私密視窗：用預設（畫） */ }
    if (feet) shown.slice(0, 3).forEach(p => {
      const tr = (p.trail || []).slice(-9), col = stc(p.quadrant);
      for (let i = 1; i < tr.length; i++) {
        const [x0, y0] = xy(tr[i - 1][1], tr[i - 1][2]), [x1, y1] = xy(tr[i][1], tr[i][2]);
        if (Math.hypot(x1 - x0, y1 - y0) < 3) continue;
        const ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI + 90, op = (.18 + .6 * i / tr.length).toFixed(2);
        g += `<g class="mrfoot" transform="translate(${x1.toFixed(1)},${y1.toFixed(1)}) rotate(${ang.toFixed(0)})" fill="${col}" opacity="${op}"><ellipse cx="0" cy="-1.6" rx="1.9" ry="2.6"/><ellipse cx="0" cy="2.6" rx="1.3" ry="1.4"/></g>`;
      }
    });
    const pts = [];
    shown.forEach(p => {
      const [x, y] = xy(p.x, p.y), col = stc(p.quadrant), r = Math.max(4, Math.min(11, 3 + Math.sqrt(p.share) * 2.2));
      pts.push({ p, x, y, r });
      const sel = opts.sel === p.group_id;
      g += `<g data-g="${esc(p.group_id)}"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 3).toFixed(1)}" fill="${col}" opacity=".45" filter="url(#${uid}-glow)"/>`
        + `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${col}" stroke="#fff" stroke-width="${sel ? 2.4 : 1}"/>`
        + (sel ? `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r + 6).toFixed(1)}" fill="none" stroke="${col}" stroke-width="2"/>` : '') + '</g>';
    });
    const boxes = [];
    /* ★ 2026-09-28（Andy：「homepage wheel dots only, popover beside the dot」）：總覽那一張傳 labels:false ——
       盤上只畫點，不掛任何名字膠囊（連選取的那一顆也不掛：名字已經寫在點旁的說明框 #mOvPop 裡，掛兩次只是多一塊擋點的東西）。
       資金流向那一張照舊掛前 5 名＋選取的那一顆。*/
    const lbl = opts.labels === false ? [] : shown.slice(0, 5).map(p => p.group_id); if (opts.labels !== false && opts.sel && !lbl.includes(opts.sel)) lbl.push(opts.sel);
    const bg = cssv('--bg'), ink = cssv('--ink');
    /* ★ 2026-09-25（clock-mobile-reds）：選取的那一顆先找位置。
       改前：依佔比順序找，選取的排最後 —— 前 5 名把好位置佔完，點一顆沒掛名字的點（實測「石化與塑膠產業」），
       盤上圈起來了卻沒有名字，要往下看焦點條才知道點到誰。
       改後：選取的先放，前 5 名在剩下的位置裡找；放不下的那一個前 5 名，點一下一樣會出現。*/
    pts.filter(q => lbl.includes(q.p.group_id)).sort((a, b) => (b.p.group_id === opts.sel) - (a.p.group_id === opts.sel)).forEach(q => {
      const t = q.p.group_name.length > 6 ? q.p.group_name.slice(0, 6) + '…' : q.p.group_name;
      const w = t.length * 12 + 12, h = 18;
      /* ★ 2026-09-25（stale-reds）：名字膠囊找位置改成「八個候選位置挑第一個乾淨的」。
         改前：固定掛在點右邊，撞到別的膠囊就一路往下推（最多三格）—— 推完常常離自己的點 40px 以上、
         還蓋住別顆點，看起來像是在標另一顆。
         改後：依序試 右／左／右上／右下／左上／左下／正上／正下，先找「不撞膠囊、也不蓋住別顆點、不出盤」的；
         找不到就退而求其次只要「不撞膠囊、不出盤」；再不行才不寫（點本身還在，點了一樣看得到名字）。*/
      const gap = q.r + 4, cand = [
        [q.x + gap, q.y - h / 2], [q.x - gap - w, q.y - h / 2],
        [q.x + gap - 4, q.y - h - q.r], [q.x + gap - 4, q.y + q.r],
        [q.x - gap - w + 4, q.y - h - q.r], [q.x - gap - w + 4, q.y + q.r],
        [q.x - w / 2, q.y - q.r - 4 - h], [q.x - w / 2, q.y + q.r + 4]];
      const inS = (x, y) => x >= 2 && y >= 2 && x + w <= S - 2 && y + h <= S - 2;
      const hitB = (x, y) => boxes.some(b => x < b[0] + b[2] && x + w > b[0] && y < b[1] + b[3] && y + h > b[1]);
      const hitP = (x, y) => pts.some(o => o !== q && o.x + o.r > x && o.x - o.r < x + w && o.y + o.r > y && o.y - o.r < y + h);
      const at = cand.find(([x, y]) => inS(x, y) && !hitB(x, y) && !hitP(x, y)) || cand.find(([x, y]) => inS(x, y) && !hitB(x, y));
      if (!at) return;
      const [x, y] = at;
      boxes.push([x, y, w, h]);
      g += `<g pointer-events="none"><rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w}" height="${h}" rx="9" fill="${bg}" fill-opacity=".82" stroke="${stc(q.p.quadrant)}" stroke-opacity=".8"/>`
        + `<text x="${(x + 6).toFixed(1)}" y="${(y + 13.2).toFixed(1)}" font-size="12" fill="${ink}">${esc(t)}</text></g>`;
    });
    const cnt = {}; all.forEach(p => { cnt[p.quadrant] = (cnt[p.quadrant] || 0) + 1; });
    const corner = { improving: 'left:0;top:0', leading: 'right:0;top:0', lagging: 'left:0;bottom:0', weakening: 'right:0;bottom:0' };
    el.innerHTML = `<div class="mradar" style="width:${S}px;height:${S}px"><svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}" role="img" aria-label="資金輪盤">${g}</svg>`
      + Object.keys(ST).map(q => `<button type="button" class="mqb${opts.quad === q ? ' on' : ''}" data-quad="${q}" style="${corner[q]};--c:${stc(q)}" aria-pressed="${opts.quad === q}">${ST[q]}<b>${cnt[q] || 0}</b></button>`).join('')
      + '</div>';
    el.dataset.shown = shown.length;
    const svg = $('svg', el);
    /* 點選：找最近的一顆（24px 內）—— 點太小、又常常疊在一起，逐顆掛點擊區會互相搶 */
    svg.addEventListener('click', (e) => {
      const b = svg.getBoundingClientRect(), k = S / b.width;
      const mx = (e.clientX - b.left) * k, my = (e.clientY - b.top) * k;
      let best = null, bd = 24 * k;
      pts.forEach(q => { const d = Math.hypot(q.x - mx, q.y - my) - q.r; if (d < bd) { bd = d; best = q; } });
      if (best && opts.onPick) opts.onPick(best.p);
      // 2026-10-08（Andy：「當點擊後 再次點擊背景會恢復預設」）：只看某一段時，點盤上沒有點的地方＝清掉篩選、回到全部
      else if (!best && opts.quad && opts.onQuad) { e.stopPropagation(); opts.onQuad(opts.quad); }
    });
    $$('.mqb', el).forEach(b => b.addEventListener('click', (e) => { e.stopPropagation(); if (opts.onQuad) opts.onQuad(b.dataset.quad); }));
    // 輪盤卡片裡的空白處（盤外、四顆角落鈕以外）也一樣清掉
    if (!el._m3bgClr) {
      el._m3bgClr = true;
      const card = el.closest('.m3keep, .card') || el;
      card.addEventListener('click', (e) => {
        const o = el._m3opts; if (!o || !o.quad || !o.onQuad) return;
        if (e.target.closest('svg, button, a, input, select, .mfocus, .mrank li, li[data-g]')) return;
        o.onQuad(o.quad);
      });
    }
    el._m3opts = opts;
    return { shown, pts, S };
  }
  /* 焦點條：圖正下方一條（色點＋名字＋階段＋強弱／動能／佔比＋「族群 ›」）。預設選佔比第一名，不留空。*/
  function focusHtml(p, note) {
    if (!p) return '';
    return `<div class="mfocus" style="--c:${stc(p.quadrant)}" data-focus="${esc(p.group_id)}"><span class="nm"><i></i>${esc(p.group_name)}</span>`
      + `<span class="st">${ST[p.quadrant] || ''}</span><a href="#industry/group/${encodeURIComponent(p.group_id)}">族群 ›</a>`
      + `<span class="nums"><span><em>強弱</em><span class="${ucls(p.x - 100)}">${sgn(p.x - 100)}</span></span>`
      + `<span><em>動能</em><span class="${ucls(p.y - 100)}">${sgn(p.y - 100)}</span></span>`
      + `<span><em>佔比</em>${(+p.share).toFixed(1)}%</span></span>`
      + (note ? `<span class="note">${esc(note)}</span>` : '') + '</div>';
  }

  /* ---- 總覽 ①資金輪盤：雷達＋四角徽章＋點一下出說明框 ----
     ★ 2026-09-28（Andy：「首頁 -> 資金輪盤不需要標示軌跡，只要標示點即可，點擊後需要出現的資訊在點擊圓圈旁內說明欄位簡短呈現，
       並且只需要說明這點即可」）：跟桌機 ovRotPop 同一套規則 ——
       · 不畫腳印（feet:false）；
       · 圖下方的焦點條拿掉，改成點一顆 → 圓圈旁邊浮出小說明框（族群＋象限、強弱、動能、佔比、N 天前在哪一段、「進族群頁 →」）；
       · 預設不選任何一顆（以前預設選佔比第一名、焦點條不留空；現在沒點就沒有框，盤面乾淨）；
       · 點外面關（全站 App.dismissable：按下記位置、放開才判斷，手指滑動捲頁不算）、再點同一顆也關、Esc 關。
     角落徽章「只看某一段」照舊；那一段的一行說明留在圖下（它講的是篩選狀態，不是某一顆點）。*/
  const quadOf = (x, y) => (x >= 100 ? (y >= 100 ? 'leading' : 'weakening') : (y >= 100 ? 'improving' : 'lagging'));
  function ovPopHtml(p) {
    const tr = p.trail || [], back = 5, w = tr.length > back ? tr[tr.length - 1 - back] : null;
    const was = w && w[1] != null && w[2] != null ? quadOf(w[1], w[2]) : '';
    return `<div class="rp-h"><b>${esc(p.group_name)}</b><span class="rp-st" style="color:${stc(p.quadrant)}">${ST[p.quadrant] || ''}</span></div>`
      + `<dl class="rp-kv"><dt>相對大盤強弱</dt><dd>${sgn(p.x - 100, 2)}</dd><dt>動能</dt><dd>${sgn(p.y - 100, 2)}</dd>`
      + `<dt>成交值佔比</dt><dd>${(+p.share).toFixed(1)}%</dd></dl>`
      + (was ? `<div class="rp-was">${back} 天前在「${ST[was]}」${was !== p.quadrant ? '，剛換段' : ''}</div>` : '')
      + (window.App && App.rotPopMembers ? App.rotPopMembers(p.group_id) : '')   // 成交值前 3 檔（跟桌機同一支）
      + `<a class="rp-go" href="#industry/group/${encodeURIComponent(p.group_id)}">進族群頁 →</a>`;
  }
  async function ovRadar() {
    const wrap = document.getElementById('rotClockMiniWrap');
    if (!wrap) return;
    const box = host(wrap, 'radar', '<div class="mrhost" id="mRadarOv"></div><div class="mfhost"></div><div class="rotpop mrpop" id="mOvPop" role="dialog" aria-label="族群說明" hidden></div>');
    if (box.dataset.done) return;
    const f = await load('flow_v3'); if (!f || !f.rrg || !isM()) return;
    // 說明框的「成交值前 3 檔」讀 App 的全域快取 D.groups_detail —— 先確定它載進來了（總覽本來就會載，這裡只是保險）
    if (window.App && App.load) { try { await App.load('groups_detail'); } catch (e) { /* 載不到：框裡就不列成分股，進族群頁那條還在 */ } }
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    box.classList.add('mrbox');
    const all = f.rrg.points;
    const pop = $('#mOvPop', box);
    let sel = null, quad = null, R = null;
    const close = () => { pop.hidden = true; if (sel) { sel = null; draw(); } };
    const place = () => {
      const q = R && R.pts.find(o => o.p.group_id === sel);
      if (!q) { pop.hidden = true; return; }
      const p = q.p;
      pop.innerHTML = ovPopHtml(p);
      pop.dataset.gid = p.group_id;
      pop.hidden = false;
      const br = box.getBoundingClientRect(), mr = $('.mradar', box).getBoundingClientRect();
      const k = mr.width / R.S;                                   // SVG 單位 → 螢幕 px（盤是等比縮放）
      const cx = mr.left - br.left + q.x * k, cy = mr.top - br.top + q.y * k, rad = (q.r + 6) * k;
      const w = pop.offsetWidth, h = pop.offsetHeight, gap = 4, pad = 4;
      const minY = Math.max(pad, mr.top - br.top), maxY = Math.min(br.height, mr.bottom - br.top) - h - pad;
      /* ★ 2026-09-29（mobile-onescreen-fix）：說明框一律夾在「頂欄（＋黏住的四步列）」與「底部導覽」之間。
         改前：左右都放不下（框寬 200 ＞ 點旁剩的寬，手機上幾乎每一顆都是）就走上／下，
         上面放不下就直接放下面、**完全不夾** —— 390×844 點盤上偏下的點（實測 ccl），框底 819px，
         底部導覽從 786 開始，框的最後兩行（成分股、「進族群頁 →」）被導覽蓋掉 33px；360×780 蓋掉 84px。
         輪盤本身在一屏內，但「點了才看得到的關鍵數字」跑出一屏 —— 正是手機判準「一屏看完一件事」要擋的。
         改後：先試「在輪盤裡」的上／下；都不行再試「在可視範圍裡」的上／下（可以蓋到輪盤上方的卡片標題，那是暫時的浮層；不准高過四步列）；
         還是不行就夾在可視範圍內（寧可蓋到那一顆的一角，也不讓數字被導覽吃掉）。左右那兩種也多夾一次可視範圍。*/
      const topbar = document.querySelector('.topbar'), spine = document.querySelector('#v-overview .mspine');
      const tb = topbar ? topbar.getBoundingClientRect().bottom : 52;
      const spr = spine && spine.getClientRects().length ? spine.getBoundingClientRect() : null;
      // 四步列（.mspine）是 sticky、z-index 31，比說明框（z 6）高 —— 沒黏住的時候也一樣會蓋在框上面（360×780 實測框頂被它吃掉），
      // 所以只要它在畫面上，框頂就不准高過它的底。
      const vTop = Math.max(tb, spr && spr.bottom > tb ? spr.bottom : 0) + pad - br.top;          // 框頂最高到這裡（相對於 box）
      const vBot = window.innerHeight - navH() - pad - br.top;                                      // 框底最低到這裡
      const cy2 = (y) => {
        const lo = Math.max(minY, vTop), hi = Math.min(maxY, vBot - h);
        return lo <= hi ? Math.max(lo, Math.min(hi, y)) : Math.max(vTop, Math.min(vBot - h, y));
      };
      let at, x, y;
      if (cx + rad + gap + w <= br.width - pad) { at = 'right'; x = cx + rad + gap; y = cy2(cy - h / 2); }
      else if (cx - rad - gap - w >= pad) { at = 'left'; x = cx - rad - gap - w; y = cy2(cy - h / 2); }
      else {
        x = Math.max(pad, Math.min(br.width - pad - w, cx - w / 2));
        const yA = cy - rad - gap - h, yB = cy + rad + gap;
        const inR = (t) => t >= Math.max(minY, vTop) && t + h <= Math.min(maxY + h, vBot);   // 在輪盤裡、也在可視範圍裡
        const inV = (t) => t >= vTop && t + h <= vBot;                                        // 只要在可視範圍裡
        if (inR(yA)) { at = 'above'; y = yA; }
        else if (inR(yB)) { at = 'below'; y = yB; }
        else if (inV(yA)) { at = 'above'; y = yA; }
        else if (inV(yB)) { at = 'below'; y = yB; }
        else { at = 'clamp'; y = Math.max(vTop, Math.min(vBot - h, yB)); }
      }
      pop.style.left = Math.round(x) + 'px'; pop.style.top = Math.round(y) + 'px';
      pop.dataset.at = at; pop.dataset.cx = Math.round(cx); pop.dataset.cy = Math.round(cy); pop.dataset.rad = Math.round(rad);
      if (window.App && App.dismissable) App.dismissable(pop, close, { isOpen: () => !pop.hidden && isM() });
    };
    const draw = () => {
      if (!box.isConnected) return;
      const el = $('.mrhost', box);
      R = radar(el, all, { sel, quad, max: 360, fitBelow: 44 + 16, feet: false, labels: false,   // 以前 65＋44＋16：65 是焦點條，已拿掉
        onPick: (p) => { if (sel === p.group_id && !pop.hidden) { close(); return; } sel = p.group_id; draw(); },
        onQuad: (q) => { quad = quad === q ? null : q; pop.hidden = true; sel = null; draw(); } });
      if (sel && !R.shown.some(x => x.group_id === sel)) sel = null;
      $('.mfhost', box).innerHTML = quad ? `<div class="msub mquadnote">只看「${ST[quad]}」：盤上 ${R.shown.length} 個（佔比前 16 名內）</div>` : '';
      el.dataset.sel = sel || ''; el.dataset.quad = quad || '';
      if (sel) place(); else pop.hidden = true;
    };
    box._redraw = draw;
    draw();
    /* ★ 2026-09-28（wheel-watch 收尾）：第一次點盤面，整個盤縮一圈、點下去的那一顆跑到框底下。
       實測 390×844：總覽剛換頁那一刻輪盤頂端還量不準（radar() 那段註解寫的「量到 1483px」），
       所以第一次畫用欄寬 324px、不記大小；之後**唯一**會重量的時機是使用者點盤面 —— 一點就縮成 301px，
       選的那一顆往上跳 10px，點旁說明框是照「縮完的位置」放的，跟手指點的地方對不上（驗收量到框蓋住點）。
       修法：輪盤第一次真的出現在畫面上（使用者看得到、才點得到）就重畫一次，讓 radar() 在可信的位置量好、記住；
       之後點盤面只換選取，不再改大小。走 draw()（不是直接呼叫 radar()）是為了讓 R 跟著換，說明框才用新尺寸定位。*/
    const host0 = $('.mrhost', box);
    if (host0 && host0._radarKey == null && window.IntersectionObserver) {
      const io = new IntersectionObserver((es) => {
        if (!es.some(e => e.isIntersecting)) return;
        io.disconnect();
        if (box.isConnected && host0._radarKey == null) draw();
      });
      io.observe(host0);
    }
  }

  /* ---- 資金分流樹：桑基 → 可以點開的長條（台股 → 產業鏈 ▸ → 族群 ▸ → 個股），數字同一份 flow_v3.sankey ----
     「其他族群／其他產業」永遠排最後、灰色 —— 不然它會以 46% 佔第一名，看起來像主流。
     長條以「同一層、不含『其他』的最大值」為滿格。*/
  async function drill(box) {
    if (!box || box.dataset.done) return;
    if (!box.innerHTML) box.innerHTML = '<div class="msub">載入資金分流樹中…</div>';
    const f = await load('flow_v3'); if (!f || !f.sankey || !box.isConnected) return;
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    let Lk = f.sankey.links;
    const isOther = (n) => /^其他/.test(n);
    const kids = (name) => Lk.filter(l => l.source === name).sort((a, b) => (isOther(a.target) - isOther(b.target)) || (b.value - a.value));
    let total = kids('台股成交值').reduce((s, l) => s + l.value, 0) || 1;
    const open = new Set();
    const baseOf = (ls) => Math.max(1, ...ls.filter(l => !isOther(l.target)).map(l => l.value));
    const rows = (src, lv) => { const ks = kids(src), base = baseOf(ks); return ks.map((l, i) => {
      const k = lv + ':' + l.target, isOpen = open.has(k), has = lv < 3 && kids(l.target).length > 0;
      const col = isOther(l.target) ? 'var(--flat)' : lv === 1 ? 'var(--cyan)' : lv === 2 ? 'var(--violet)' : 'var(--amber)';
      return `<li data-k="${esc(k)}" class="${isOther(l.target) ? 'other' : ''}" style="--c:${col}"><span class="r">${has ? (isOpen ? '▾' : '▸') : (i + 1)}</span>`
        + `<span class="bar" style="width:calc((100% - 150px) * ${Math.min(1, l.value / base).toFixed(3)})"></span>`
        + `<span class="n">${esc(l.target)}</span><span class="v">${yi(l.value)} 億<small>${(l.value / total * 100).toFixed(1)}%</small></span></li>`
        + (isOpen && has ? `<li class="sub"><ul class="mrank lv">${rows(l.target, lv + 1)}</ul></li>` : '');
    }).join(''); };
    /* ★ 2026-10-07（Andy：「樹狀圖只是看整體族群，但詳細的資金流向排名還是需要旁邊有圖表搭配」）：
       手機把桌機右欄那張「資金流向排名」放在長條下方（同一支 App.sankeyRankDraw、同一份 sankey_daily 最新一天）。
       長條與排名各住一個子容器 —— 長條每點一次就整個重寫，不能把排名一起洗掉。*/
    //   只放在資金流向頁那一份（總覽的「昨日資金分流樹」是摘要，不加長；id 也只能有一個）。
    const onFlow = !!box.closest('#flowSankeyCard');
    /* ★ 2026-10-08（Andy：「分流樹需要出現樹狀圖而非長條圖」）：手機 v2 總覽那一份畫成真的樹（SVG 節點＋連線，由上往下）：
       根（台股成交值）→ 產業鏈（前 5）→ 每條鏈的前 3 個族群；節點寫「名稱＋占比」兩行。點整張圖進完整的資金分流樹頁。 */
    if (!onFlow && document.documentElement.classList.contains('m4')) {
      const W = Math.max(300, box.clientWidth || 370), top = kids('台股成交值').filter(l => !isOther(l.target)).slice(0, 5);
      const cw = W / top.length, y0 = 22, y1 = 92, y2 = 150, gh = 34;
      let svg = `<text x="${W / 2}" y="${y0}" text-anchor="middle" class="tr0">台股成交值 ${yi(total)} 億</text>`;
      top.forEach((l, i) => {
        const cx = cw * i + cw / 2, pct = (l.value / total * 100).toFixed(1);
        svg += `<path d="M${W / 2},${y0 + 8} C${W / 2},${(y0 + y1) / 2} ${cx},${(y0 + y1) / 2 - 10} ${cx},${y1 - 26}" class="tl" style="stroke-width:${Math.max(1.2, Math.min(6, l.value / total * 18)).toFixed(1)}"/>`;
        svg += `<circle cx="${cx}" cy="${y1 - 20}" r="5" class="tn1"/><text x="${cx}" y="${y1 - 4}" text-anchor="middle" class="tr1">${esc(l.target.length > 5 ? l.target.slice(0, 5) : l.target)}</text><text x="${cx}" y="${y1 + 12}" text-anchor="middle" class="tp">${pct}%</text>`;
        // 第二層：每條鏈底下一根豎線靠欄的左側，族群掛在線的右邊（名稱＋占比），線不穿過字
        const lx = cx - cw / 2 + 12, gs = kids(l.target).filter(c => !isOther(c.target)).slice(0, 3);
        if (gs.length) svg += `<path d="M${cx},${y1 + 16} C${cx},${y1 + 26} ${lx},${y1 + 22} ${lx},${y2 - 12} L${lx},${y2 + (gs.length - 1) * gh - 4}" class="tl2"/>`;
        gs.forEach((c, j) => {
          const gy = y2 + j * gh;
          svg += `<circle cx="${lx}" cy="${gy - 4}" r="3" class="tn2"/>`
            + `<text x="${lx + 7}" y="${gy}" class="tr2">${esc(c.target.length > 5 ? c.target.slice(0, 5) : c.target)}</text>`
            + `<text x="${lx + 7}" y="${gy + 13}" class="tp">${(c.value / total * 100).toFixed(1)}%</text>`;
        });
      });
      const H = y2 + 3 * gh;
      box.innerHTML = `<a class="mtree" href="#flow/sankey" aria-label="資金分流樹（點了看完整版）"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img">${svg}</svg></a><div class="msub">點樹狀圖看完整的資金分流樹 ›</div>`;
      box.dataset.open = '0';
      return;
    }
    /* ★ 2026-10-08（Andy：「資金樹 Default 就在最上方開啟…外面那個框拿掉」）：
       根節點「台股成交值 X 億」放在最上面一列（樹由上往下：根 → 產業鏈 ▸ → 族群 ▸ → 個股）；
       下方的「資金流向排名」改成一顆「資金流向排名 ▸」標題列，預設收起，點了才展開（手機準則第 5 條）。 */
    box.innerHTML = '<div class="mdtree"></div>' + (onFlow ? '<button type="button" class="mrkhd" id="mSankeyRankHd" aria-expanded="false" hidden>資金流向排名 <i aria-hidden="true">▸</i></button><div class="hpanel skrank m4shut" id="mSankeyRank" hidden></div>' : '');
    const tree = box.querySelector('.mdtree'), rk = box.querySelector('#mSankeyRank'), rkh = box.querySelector('#mSankeyRankHd');
    if (rkh) rkh.onclick = () => { const on = rk.classList.contains('m4shut'); rk.classList.toggle('m4shut', !on); rkh.setAttribute('aria-expanded', on ? 'true' : 'false'); rkh.querySelector('i').textContent = on ? '▾' : '▸'; };
    /* ★ 2026-10-08（Andy：日期拉桿手機也要有）：讀桌機同一份 sankey_daily（每天各族群成交值＋成分股），拉到哪一天，樹就換成那一天。
       拉桿把手 ≥ 32px、手指拖得動；▶ 播放一天一天往後，播放中拉桿鎖住（同桌機）。沒有 sankey_daily 時照舊只看最新一天（flow_v3）。 */
    let dayIdx = -1, dayDates = [];
    const linksOfDay = (sd, i) => {
      const L = [], byChain = {};
      (sd.groups || []).forEach((g) => { const v = (g.tv || [])[i]; if (!(v > 0)) return; const ch = g.chain_name || g.chain || '其他產業';
        (byChain[ch] = byChain[ch] || []).push({ g, v }); });
      Object.entries(byChain).forEach(([ch, gs]) => {
        L.push({ source: '台股成交值', target: ch, value: gs.reduce((a, x) => a + x.v, 0) });
        gs.forEach(({ g, v }) => {
          L.push({ source: ch, target: g.name, value: v });
          const mem = (sd.members || {})[g.gid] || {};
          Object.entries(mem).map(([code, arr]) => ({ code, v: (arr || [])[i] })).filter((x) => x.v > 0).sort((a, b) => b.v - a.v).slice(0, 8)
            .forEach((x) => L.push({ source: g.name, target: (sd.names || {})[x.code] || x.code, value: x.v }));
        });
      });
      return L;
    };
    const draw = () => { tree.innerHTML = `<div class="mroot"><span class="n">${dayIdx >= 0 ? '族群成交值合計' : '台股成交值'}</span><b>${yi(total)} 億</b>${dayIdx >= 0 ? `<small class="mday">${esc(dayDates[dayIdx])}</small>` : ''}</div><div class="msub">台股 → 產業鏈 → 族群 → 個股</div><ul class="mrank">${rows('台股成交值', 1)}</ul>`; box.dataset.open = open.size; };
    tree.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-k]'); if (!li) return;
      const k = li.dataset.k; open.has(k) ? open.delete(k) : open.add(k); draw();
    });
    draw();
    if (rk) load('sankey_daily').then(sd => {
      /* ★ 2026-10-09 審核修：sankey_daily 是非同步載入的；等它回來之前這張卡可能已經重畫過一次（box.innerHTML 換新、
         舊的 tree 被拔掉），這時再 box.insertBefore(bar, 舊tree) 會丟 NotFoundError（_uitest 新-版面等高與多寬度 560／390 抓到）。
         舊 tree 已經不在 box 裡＝這一輪作廢，交給新的那一輪畫。 */
      if (!sd || !(sd.dates || []).length || !box.isConnected || tree.parentNode !== box || !(window.App && App.sankeyRankDraw)) return;
      // 日期拉桿＋播放（只在手機 v2；放在樹的上面，第一屏看得到）
      if (document.documentElement.classList.contains('m4') && !box.querySelector('.mdaybar')) {
        dayDates = sd.dates; dayIdx = sd.dates.length - 1;
        const bar = document.createElement('div'); bar.className = 'mdaybar';
        bar.innerHTML = `<button type="button" class="mplay" aria-label="播放：一天一天往後看">▶</button><input type="range" class="mday" min="0" max="${sd.dates.length - 1}" step="1" value="${dayIdx}" aria-label="看哪一天"><span class="mdl"></span>`;
        box.insertBefore(bar, tree);
        const rg = bar.querySelector('input'), lab = bar.querySelector('.mdl'), pb = bar.querySelector('.mplay');
        const setDay = (i) => { dayIdx = i; rg.value = String(i); lab.textContent = sd.dates[i].slice(5);
          Lk = linksOfDay(sd, i); total = kids('台股成交值').reduce((a, l) => a + l.value, 0) || 1; open.clear(); draw();
          box.dataset.day = sd.dates[i];
          try { App.sankeyRankDraw(rk, sd, i, rk._pick); } catch (e) { /* 排名畫不出來不擋樹 */ } };
        rg.addEventListener('input', () => setDay(+rg.value));
        let timer = 0;
        const stop = () => { clearInterval(timer); timer = 0; pb.textContent = '▶'; rg.disabled = false; bar.classList.remove('playing'); };
        pb.onclick = () => {
          if (timer) { stop(); return; }
          let i = +rg.value >= sd.dates.length - 1 ? Math.max(0, sd.dates.length - 20) : +rg.value;
          pb.textContent = '❚❚'; rg.disabled = true; bar.classList.add('playing'); setDay(i);
          timer = setInterval(() => { i += 1; if (i >= sd.dates.length || !box.isConnected) { stop(); return; } setDay(i); }, 700);
        };
        // 一進來就用同一份每日資料畫最新一天（拉來拉去口徑才一致：每天都是「有對到族群的成交值合計」，不混用 flow_v3 的全市場口徑）
        setDay(dayIdx);
      }
      rk.hidden = false; if (rkh) rkh.hidden = false;
      /* 點排名的列＝在上面的長條裡展開那個族群（找到它掛在哪一條鏈底下），再捲過去 —— 原地展開，不換頁。*/
      App.sankeyRankDraw(rk, sd, sd.dates.length - 1, rk._pick = (gid) => {
        const g = (sd.groups || []).find(x => x.gid === gid); if (!g) return;
        const ch = kids('台股成交值').find(l => kids(l.target).some(c => c.target === g.name));
        if (!ch) return;
        open.add('1:' + ch.target); open.add('2:' + g.name); draw();
        const li = [...tree.querySelectorAll('li[data-k]')].find(x => x.dataset.k === '2:' + g.name);
        if (li) { li.classList.add('hit'); li.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
      });
    });
  }

  /* ---- 資金流向「輪動」：雷達＋焦點條＋排行前 8（點列＝在輪盤上只亮它）＋篩選抽屜 ---- */
  async function flowRot() {
    const card = document.getElementById('flowRotCard'); if (!card) return;
    const box = host(card, 'rot', null, { full: liveTxt('完整版（回放、即時、放大）') });
    if (box.dataset.done) return;
    /* 資料還沒回來之前先放標題與一行「載入中」—— 不然這一段在資料回來之前整片空白（慢網路下看起來像壞掉）*/
    if (!box.innerHTML) box.innerHTML = '<div class="mhead"><h3>資金輪動</h3></div><div class="msub">載入資金輪盤與資金排行中…</div>';
    const [f, sd] = await Promise.all([load('flow_v3'), load('sankey_daily')]);
    if (!f || !f.rrg || !box.isConnected) return;
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    const chainName = { traditional: '傳產', financial: '金融', industry: '其他產業別' };
    ((sd && sd.groups) || []).forEach(g => { if (g.chain_name) chainName[g.chain] = g.chain_name; });
    const periods = f.periods || [];
    /* quad＝角落徽章選到的象限（null＝全部）。
       ★ 2026-09-25（批次30 收尾）：以前這裡的 onQuad 是 `() => {}` —— 四顆角落徽章長得跟總覽那四顆一模一樣
       （同一支 radar() 畫的，有 aria-pressed、有按下去的底色樣式），**點了卻完全沒反應**。
       使用者只會覺得「壞掉了」。改成跟總覽同一套：點一下只看那一段、再點一次還原。
       不寫進 localStorage：它是「這一眼要看哪一段」的暫時聚焦，不是篩選條件（篩選在抽屜裡，那個才會記住）。*/
    let chain = LS.get('flow.chain', ''), pk = LS.get('flow.period', periods[0] && periods[0].key), sel = null, quad = null, quadNew = false;
    if (!periods.some(p => p.key === pk)) pk = periods[0] && periods[0].key;
    /* ★ 2026-09-26（Andy：「將所有『怎麼看』變成『?』，說明方式 Follow 總覽頁」）：
       改前「?」排在這一列最右邊（篩選鈕後面）→ 改後跟總覽一樣住在標題「資金輪動」文字的右側，彈窗標題才讀得到卡片名稱。*/
    box.innerHTML = `<div class="mhead"><h3>資金輪動<button class="howbtn pop" data-how="rot" type="button" aria-label="資金輪動怎麼看">?</button></h3>`
      + `<span class="sp"></span><button type="button" class="mfilt" id="mFlowFilt"></button></div>`
      /* 2026-10-06：免責一行放在標題列正下方自己一行 —— 標題列（標題＋篩選鈕）在 390 只剩 43px，擠進去只看得到「不構…」*/
      + (window.App && window.App.disc ? `<div class="mdisc">${window.App.disc('rot')}</div>` : '')
      + `<div class="mrhost" id="mRadarFlow"></div><div class="mfhost"></div>`
      + `<div class="mhead sm"><h3>資金排行</h3><small id="mRankSub"></small><span class="sp"></span></div><ul class="mrank" id="mRank"></ul>`;
    const draw = () => {
      const pts = f.rrg.points.filter(p => !chain || p.chain === chain);
      const per = periods.find(p => p.key === pk) || { label: '', groups: [], from: '', to: '' };
      const gs = per.groups.filter(g => !chain || g.chain === chain).sort((a, b) => b.share - a.share).slice(0, 8);
      const fb = $('#mFlowFilt', box);
      fb.textContent = '篩選 · ' + (chain ? (chainName[chain] || chain) : '全部') + ' · ' + per.label;
      fb.classList.toggle('on', !!chain || pk !== (periods[0] && periods[0].key));
      const r = radar($('#mRadarFlow', box), pts, { sel, quad, max: 340, fitBelow: 65 + 42 + 5 * 36 + 34,
        onPick: (p) => { sel = p.group_id; draw(); },
        onQuad: (q) => { quad = quad === q ? null : q; quadNew = !!quad; draw(); } });
      /* 剛點角落時，焦點條換成那一段盤上佔比最大的一顆（不然焦點條還寫著別段的族群，跟盤面對不起來）。
         只在「剛點角落」那一次換：之後使用者點排行某一列，就算那一族不在這一段，也照他點的顯示，不要搶回來。*/
      if (quadNew) {
        quadNew = false;
        // 換了焦點就再畫一次，選取外圈才會圈在新的那一顆上（quadNew 已經清掉，不會繞圈）
        if (r.shown.length && r.shown[0].group_id !== sel) { sel = r.shown[0].group_id; return draw(); }
      }
      if (!sel && r.shown.length) sel = r.shown[0].group_id;
      $('#mRadarFlow', box).dataset.quad = quad || '';
      const p = pts.find(x => x.group_id === sel);
      $('.mfhost', box).innerHTML = p ? focusHtml(p, quad ? `只看「${ST[quad]}」：盤上 ${r.shown.length} 個（佔比前 16 名內）` : '')
        : `<div class="mfocus"><span class="nm">${esc((gs.find(g => g.group_id === sel) || {}).group_name || '')}</span><span class="note">不在這個篩選的輪盤上</span></div>`;
      const mx = gs.length ? gs[0].share : 1;
      // 2026-10-06（DECISIONS #329）：副標不再寫日期區間，只留「本週／上週…」
      $('#mRankSub', box).textContent = per.label || '';
      $('#mRank', box).innerHTML = gs.map((g, i) => `<li data-g="${esc(g.group_id)}" class="${g.group_id === sel ? 'on' : ''}" style="--c:${stc((f.rrg.points.find(x => x.group_id === g.group_id) || {}).quadrant)}">`
        + `<span class="r">${i + 1}</span><span class="bar" style="width:calc((100% - 140px) * ${(g.share / mx).toFixed(3)})"></span>`
        + `<span class="n">${esc(g.group_name)}</span><span class="v">${g.share.toFixed(1)}%<small class="${ucls(g.share_chg)}">${sgn(g.share_chg)}</small></span></li>`).join('');
      box.dataset.n = pts.length; box.dataset.chain = chain; box.dataset.sel = sel || '';
    };
    $('#mRank', box).addEventListener('click', (e) => { const li = e.target.closest('li[data-g]'); if (!li) return; sel = li.dataset.g; draw(); });
    $('#mFlowFilt', box).onclick = () => {
      const chains = [...new Set(f.rrg.points.map(p => p.chain))];
      const sh = openSheet(`<div class="mshhead"><b>篩選與期間</b></div>
        <div class="mgrp">產業鏈</div><div class="mchips" id="mShChain"><button type="button" data-c="" class="${!chain ? 'on' : ''}">全部</button>${chains.map(c => `<button type="button" data-c="${esc(c)}" class="${chain === c ? 'on' : ''}">${esc(chainName[c] || c)}</button>`).join('')}</div>
        <div class="mgrp">排行期間</div><div class="mchips" id="mShPer">${periods.map(p => `<button type="button" data-p="${esc(p.key)}" class="${pk === p.key ? 'on' : ''}">${esc(p.label)}</button>`).join('')}</div>`, { kind: 'filter' });
      sh.onclick = (e) => {
        const a = e.target.closest('[data-c],[data-p]'); if (!a) return;
        if (a.dataset.c != null) { chain = a.dataset.c; LS.set('flow.chain', chain); sel = null; }
        if (a.dataset.p) { pk = a.dataset.p; LS.set('flow.period', pk); }
        closeSheet(); draw();
      };
    };
    box._redraw = draw;
    draw();
  }

  /* ---- 法人：外資／投信／自營／合計四格切換，買超前 8＋賣超前 8 的對稱長條，紅買綠賣 ----
     ⚠ 法人資料比價量晚一天，inst_daily 最後一天常常整天是 null —— 往回找第一個有值的日子，副標寫那一天。*/
  async function flowInst() {
    const card = document.getElementById('flowInstCard'); if (!card) return;
    const head = card.querySelector(':scope > .row');
    if (head) head.classList.add('m3keep-h');
    const box = host(card, 'inst', null, { full: '完整版（拉區間看任一段）', after: head });
    if (box.dataset.done) return;
    if (!box.innerHTML) box.innerHTML = '<div class="msub">載入法人資料中…</div>';
    const f = await load('flow_v3'); if (!f || !f.inst_daily || !box.isConnected) return;
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    const src = f.inst_daily;
    let last = src.dates.length - 1;
    while (last > 0 && !src.groups.some(g => g.foreign[last] != null || g.trust[last] != null || g.dealer[last] != null)) last--;
    const KS = [['foreign', '外資'], ['trust', '投信'], ['dealer', '自營'], ['total', '合計']];
    let k = LS.get('inst', 'total');
    box.innerHTML = `<div class="mseg" id="mInstSw">${KS.map(x => `<button type="button" data-k="${x[0]}">${x[1]}</button>`).join('')}</div>`
      + `<div class="msub" id="mInstSub">淨買超（張）</div><div class="minst" id="mInst"></div>`;
    const fmtN = (v) => Math.round(Math.abs(v)).toLocaleString('en-US');
    const draw = () => {
      $$('#mInstSw button', box).forEach(b => b.classList.toggle('on', b.dataset.k === k));
      /* ★ 2026-09-26（Andy：「ETF 族群拿掉」）：同一張「族群 × 法人」卡的手機版也不列 ETF ——
         它的法人買賣超幾乎全是自營商避險部位，單日就能幾十萬張，這裡的長條是「除以最長那條」，
         ETF 一在，其他族群全縮成細線（和桌機那張同一個理由，見 app.js renderInstPeriod）。*/
      const gs = src.groups.filter(g => !/ETF/i.test(g.group_id || '') && !/ETF/.test(g.group_name || '')).map(g => { const fo = g.foreign[last] || 0, tr = g.trust[last] || 0, de = g.dealer[last] || 0;
        return { n: g.group_name, v: (k === 'total' ? fo + tr + de : k === 'foreign' ? fo : k === 'trust' ? tr : de) / 1000 }; })
        .filter(g => g.v).sort((a, b) => b.v - a.v);
      const buy = gs.filter(g => g.v > 0).slice(0, 8), sell = gs.filter(g => g.v < 0).slice(-8).reverse();
      const mx = Math.max(1, ...buy.concat(sell).map(g => Math.abs(g.v)));
      const row = (g) => `<li class="${g.v > 0 ? 'b' : 's'}"><span class="n">${esc(g.n)}</span><span class="t"><i style="width:${(Math.abs(g.v) / mx * 100).toFixed(1)}%"></i></span><span class="v ${g.v > 0 ? 'up' : 'dn'}">${g.v > 0 ? '+' : '−'}${fmtN(g.v)}</span></li>`;
      $('#mInst', box).innerHTML = `<div class="mgrp">買超前 ${buy.length}</div><ul>${buy.map(row).join('')}</ul><div class="mgrp">賣超前 ${sell.length}</div><ul>${sell.map(row).join('')}</ul>`;
      box.dataset.inst = k; box.dataset.sig = buy.concat(sell).map(g => g.n + g.v.toFixed(0)).join('|').slice(0, 200);
    };
    $('#mInstSw', box).addEventListener('click', (e) => { const b = e.target.closest('button[data-k]'); if (!b) return; k = b.dataset.k; LS.set('inst', k); draw(); });
    draw();
  }

  /* ---- 大盤三張合一張（R1）：三格切換＋圖上左右滑＋「● ○ ○ 1 / 3」位置指示 ----
     卡片、盤中走勢、分 K、夜盤自動切換全部照 market3.js 現有的（只改「三張變一張」這件事）：
     三張卡仍然都在 DOM 裡，手機只把「不是現在這張」的藏起來，換張之後補一次 resize。*/
  const M3IDS = [['TSE', '加權'], ['OTC', '櫃買'], ['FUT', '台指期']];
  function market1() {
    const grid = document.getElementById('m3Grid'); if (!grid) return;
    let sw = document.getElementById('mM3Sw');
    if (!sw) {
      sw = document.createElement('div'); sw.id = 'mM3Sw'; sw.className = 'mseg m3keep-sw';
      sw.innerHTML = M3IDS.map(([id, n]) => `<button type="button" data-id="${id}">${n}</button>`).join('');
      grid.before(sw);
      const pos = document.createElement('div'); pos.id = 'mM3Pos'; pos.className = 'mpos';
      grid.after(pos);
      sw.addEventListener('click', (e) => { const b = e.target.closest('button[data-id]'); if (b) m3go(b.dataset.id); });
      let t0 = null;
      grid.addEventListener('touchstart', (e) => { if (!isM()) return; const t = e.touches[0]; t0 = [t.clientX, t.clientY]; }, { passive: true });
      grid.addEventListener('touchend', (e) => {
        if (!t0) return; const t = e.changedTouches[0], dx = t.clientX - t0[0], dy = t.clientY - t0[1]; t0 = null;
        // 水平位移 > 50px 而且明顯大於垂直，才算切換（不然會搶掉整頁的上下捲動）
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) m3step(dx < 0 ? 1 : -1);
      }, { passive: true });
    }
    grid.classList.add('m3one');
    m3go(LS.get('idx', 'TSE'), true);
  }
  function m3step(d) {
    const i = Math.max(0, M3IDS.findIndex(x => x[0] === (document.getElementById('m3Grid') || {}).dataset.cur));
    m3go(M3IDS[(i + d + M3IDS.length) % M3IDS.length][0]);
  }
  function m3go(id, quiet) {
    const grid = document.getElementById('m3Grid'); if (!grid) return;
    if (!M3IDS.some(x => x[0] === id)) id = 'TSE';
    grid.dataset.cur = id;
    $$('.m3-card', grid).forEach(c => c.classList.toggle('mcur', c.dataset.id === id));
    $$('#mM3Sw button').forEach(b => b.classList.toggle('on', b.dataset.id === id));
    const i = M3IDS.findIndex(x => x[0] === id);
    const pos = document.getElementById('mM3Pos');
    if (pos) { pos.dataset.pos = i + 1; pos.dataset.of = M3IDS.length;
      pos.innerHTML = M3IDS.map((_, j) => `<i class="${j === i ? 'on' : ''}"></i>`).join('') + `<span>${i + 1} / ${M3IDS.length}${document.documentElement.classList.contains('m4') ? '' : '　左右滑切換'}</span>`; }   // 2026-10-09 手機 v2（≤640）：提示字拿掉，只留位置（點點＋第幾張）
    if (!quiet) LS.set('idx', id);
    // quiet＝apply() 自己帶的那一次：派出去的 resize 標成回聲（twEcho），apply() 與分段都不再因為它重跑（#284）
    setTimeout(() => { const ev = new Event('resize'); if (quiet) ev.twEcho = 'm3'; window.dispatchEvent(ev); }, 40);
  }
  function unMarket() {
    ['mM3Sw', 'mM3Pos'].forEach(x => { const e = document.getElementById(x); if (e) e.remove(); });
    const g = document.getElementById('m3Grid');
    if (g) { g.classList.remove('m3one'); delete g.dataset.cur; $$('.m3-card', g).forEach(c => c.classList.remove('mcur')); }
  }

  /* 主題一換，雷達的顏色（吃 CSS token）要重畫 */
  window.addEventListener('tw:theme', () => { $$('.m3keep').forEach(b => { if (b._redraw) setTimeout(b._redraw, 60); }); });

  let cWait = null;
  /* ★ 2026-10-09（Andy：「資金分流樹……光、子樹特效都要一模一樣跟網頁版本」「所有的圖表……顏色風格都要一樣」
     「資金輪動直接是完整版」「族群 × 法人……跟網頁版一樣直接上長條圖」）：
     手機 v2（html.m4）不再用這一節的手機替身（SVG 輪盤、長條式分流樹、SVG 小樹、法人單色細條＋「完整版 ›」）——
     桌機那幾張圖本身（app.js renderRotClock／renderSankey→flowtopo.js／renderOvFlow／族群×法人堆疊長條）直接在手機上畫，
     只有尺寸跟著寬度縮（app.js 的 rotM4()／sankeyTopoOn()、flowtopo.js 的 clNarrow）。
     舊的手機 v1（≤640 但沒有 m4）照舊走這一節。*/
  const m4on = () => document.documentElement.classList.contains('m4');
  function cOn(v) {
    if (v === 'overview') {
      if (!m4on()) {
        ovRadar();
        const ow = document.getElementById('ovFlowWrap');
        if (ow) drill(host(ow, 'drill'));
      }
      if (document.getElementById('m3Grid')) market1();
      else { clearTimeout(cWait); cWait = setTimeout(() => cOn(curView()), 800); }
    }
    if (v === 'flow' && !m4on()) {
      flowRot();
      const sc = document.getElementById('flowSankeyCard');
      if (sc) { const hd = sc.querySelector(':scope > .row'); if (hd) hd.classList.add('m3keep-h'); drill(host(sc, 'drill', null, { full: liveTxt('完整版（分流圖、回放、即時）'), after: hd })); }
      flowInst();
    }
  }
  function cOff() { unhost(); unMarket(); $$('.m3keep-h').forEach(e => e.classList.remove('m3keep-h')); }
  hooks.push({ on: cOn, off: cOff });


  /* ====================================================================== E 其他頁
     ---- 熱力圖：手機沒有 hover，小方塊的字被截成「石 -3.0」—— 點一下開抽屜（全名、漲跌、成交值、佔比、「族群 ›」）----
     industry.js 的樹狀圖 click 在手機改叫這一支（桌機照舊直接進族群頁）。*/
  function tileSheet(d) {
    const pct = (v) => v == null ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(2) + '%';
    const sh = openSheet(`<div class="mshhead"><b>${esc(d.name)}</b></div>`
      + `<div class="mshbody"><i>${esc(d.chain || '')}</i>`
      + `<i>漲跌幅 <b class="${ucls(d.chg)}">${pct(d.chg)}</b></i>`
      + `<i>成交值 ${d.to != null ? yi(d.to) + ' 億' : '—'}${d.share != null ? `（佔 ${(+d.share).toFixed(1)}%）` : ''}</i>`
      + `<i>成分股 ${d.n != null ? d.n : '—'} 檔　本益比中位 ${d.pe != null ? (+d.pe).toFixed(1) : '—'}</i></div>`
      + `<div class="mchips"><a href="#industry/group/${encodeURIComponent(d.gid)}" data-hmgo="1">族群 ›</a></div>`, { kind: 'tile' });
    sh.dataset.name = d.name;
    /* 2026-10-09 手機與桌機同步：「族群 ›」＝從熱力圖跳族群頁，權限跟桌機點方塊同一支（app.js hmGo → quota.js heatGo）：
       Plus 以上照跳；訪客、免費會員不跳、跳同一張升級卡（heatLinkBlock）。以前是普通連結，訪客照樣進得去。
       先關抽屜再判斷：放行時 hashchange 本來就會關；擋下時升級卡不要疊在抽屜上面。*/
    const a = sh.querySelector('a[data-hmgo]');
    if (a) a.addEventListener('click', (e) => {
      e.preventDefault();
      const to = a.getAttribute('href'), App = window.App;
      closeSheet();
      if (App && App.hmGo) App.hmGo(to); else location.hash = to;
    });
    /* 幽靈點擊：zrender 在 touchend 就發 click → 這裡開抽屜；瀏覽器接著在同一個座標補發原生 click，
       落在剛蓋上來的背景（mSheetBack）→ 抽屜一開就被關掉（390 觸控實測：開了 0.1 秒就收）；落在抽屜裡則可能直接按到「族群 ›」。
       跟 quota.js heatLinkBlock 同一套：開抽屜後 450ms 內落在抽屜／背景上的 click 一律吃掉，之後使用者自己按的照常。*/
    const t0 = Date.now(), back = document.getElementById('mSheetBack');
    const eat = (e) => {
      if (Date.now() - t0 > 450) { document.removeEventListener('click', eat, true); return; }
      if (e.target && (sh.contains(e.target) || (back && back.contains(e.target)))) { e.preventDefault(); e.stopImmediatePropagation(); }
    };
    document.addEventListener('click', eat, true);
    setTimeout(() => document.removeEventListener('click', eat, true), 500);
    return sh;
  }

  /* ---- 市場明細：分兩段「分佈圖／名單」（現行 1981px 是一張圖＋一張完整名單串在一起）----
     分段列插在 #mktBody 前面（#mktBody 會整個重畫，插在裡面會被洗掉），狀態寫進 localStorage。*/
  function marketSeg() {
    const body = document.getElementById('mktBody'); if (!body) return;
    let bar = document.getElementById('mMktSeg');
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'mMktSeg'; bar.className = 'mseg';
      bar.innerHTML = '<button type="button" data-s="dist">分佈圖</button><button type="button" data-s="list">名單</button>';
      body.before(bar);
      bar.onclick = (e) => { const b = e.target.closest('button[data-s]'); if (!b) return; LS.set('mkt.seg', b.dataset.s); paint(); window.scrollTo({ top: 0 }); setTimeout(() => window.dispatchEvent(new Event('resize')), 60); };
    }
    const paint = () => {
      const s = LS.get('mkt.seg', 'dist') === 'list' ? 'list' : 'dist';
      body.classList.toggle('mseg-dist', s === 'dist'); body.classList.toggle('mseg-list', s === 'list');
      $$('button', bar).forEach(b => b.classList.toggle('on', b.dataset.s === s));
    };
    paint();
  }
  function unMarketSeg() {
    const b = document.getElementById('mMktSeg'); if (b) b.remove();
    const body = document.getElementById('mktBody'); if (body) body.classList.remove('mseg-dist', 'mseg-list');
  }

  /* ---- 週期統計：四列選項（約 150px）收進抽屜，標題列一顆「設定 · 目前條件 ›」----
     搬的是**同一個節點**（#seasonCtl，選項的事件都掛在上面），關抽屜時原封不動搬回去。*/
  function seasonCtl() {
    const ctl = document.getElementById('seasonCtl'); if (!ctl) return;
    let b = document.getElementById('mSeasonBtn');
    const label = () => '設定 · ' + ($$('.on', ctl).map(x => x.textContent.trim()).filter(Boolean).slice(0, 4).join(' · ') || '預設') + ' ›';
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = 'mSeasonBtn'; b.className = 'mfilt';
      ctl.before(b);
      b.onclick = () => {
        const home = document.createComment('mseasonhome');
        ctl.parentNode.insertBefore(home, ctl);
        const wrap = document.createElement('div');
        wrap.innerHTML = '<div class="mshhead"><b>週期統計設定</b></div>';
        wrap.appendChild(ctl); ctl.classList.add('min');
        openSheet(wrap, { kind: 'season', onClose: () => {
          ctl.classList.remove('min');
          if (home.parentNode) { home.parentNode.insertBefore(ctl, home); home.remove(); }
          b.textContent = label();
        } });
      };
    }
    ctl.classList.add('mhide');
    b.textContent = label();
    seasonSort(b);
  }
  /* ---- 週期統計：依月份排序（設計 v4 第二批 2D，2026-09-28）----
     熱力圖上方那排 1～12 月表頭本來就能點（點哪個月＝依那個月由強到弱排），但 360～390 寬一格只有 19px、
     十二顆緊貼著排 —— 手指點「9」常常點到 8 或 10（手機按鈕普查：12 顆全部 < 40px）。
     手機改由一顆 40px 的「排序：9 月 ›」接手：點開底部抽屜，十二個月各一顆大鈕（3 欄 × 4 列、48px 高），
     點一顆＝去按表頭同一顆（排序邏輯只有 app.js 那一份）。表頭照樣顯示目前依哪個月排、照樣可以點（次要入口）。*/
  function seasonSort(after) {
    let s = document.getElementById('mSeasonSort');
    const cur = () => { const on = document.querySelector('#seasonHeatHead button.on'); return on ? +on.dataset.m : null; };
    const label = () => { const m = cur(); return m ? `排序：${m} 月 ›` : '依月份排序 ›'; };
    if (!s) {
      s = document.createElement('button'); s.type = 'button'; s.id = 'mSeasonSort'; s.className = 'mfilt';
      after.after(s);
      s.onclick = () => {
        const m0 = cur();
        const sh = openSheet(`<div class="mshhead"><b>依哪個月排序</b></div><div class="msub">由強到弱排</div>`
          + `<div class="mballgrid">${Array.from({ length: 12 }, (_, i) => i + 1).map(m =>
            `<button type="button" data-m="${m}" class="${m === m0 ? 'on' : ''}" aria-pressed="${m === m0}">${m} 月</button>`).join('')}</div>`, { kind: 'seasonsort' });
        sh.querySelector('.mballgrid').onclick = (e) => {
          const bt = e.target.closest('button[data-m]'); if (!bt) return;
          const h = document.querySelector(`#seasonHeatHead button[data-m="${bt.dataset.m}"]`);
          closeSheet();
          if (h) h.click();
          s.textContent = label();
        };
      };
    }
    s.textContent = label();
    /* 2026-10-08（Andy：「週期統計數字選項呢？」）：「排序」旁邊一顆「數字：開／關」，按下去就是去按桌機那顆 #seasonNum（app.js 只有一份邏輯，手機預設關、開了記住） */
    let nb = document.getElementById('mSeasonNum');
    const numOn = () => { const b = document.querySelector('#seasonNum button'); return !!b && b.getAttribute('aria-pressed') === 'true'; };
    if (!nb) {
      nb = document.createElement('button'); nb.type = 'button'; nb.id = 'mSeasonNum'; nb.className = 'mfilt';
      s.after(nb);
      nb.onclick = () => { const b = document.querySelector('#seasonNum button'); if (b) b.click(); setTimeout(() => { nb.textContent = '數字：' + (numOn() ? '開' : '關'); nb.setAttribute('aria-pressed', String(numOn())); }, 50); };
    }
    nb.textContent = '數字：' + (numOn() ? '開' : '關'); nb.setAttribute('aria-pressed', String(numOn()));
    /* 表頭是 app.js 畫完熱力圖才生出來的（也會因為換條件重畫）：表頭一換，鈕上的「N 月」跟著換 */
    const hd = document.getElementById('seasonHeatHead');
    if (hd && !hd.__mSort) {
      hd.__mSort = new MutationObserver(() => { const x = document.getElementById('mSeasonSort'); if (x) x.textContent = label(); });
      hd.__mSort.observe(hd, { childList: true });
    }
  }
  function unSeasonCtl() {
    const s = document.getElementById('mSeasonSort'); if (s) s.remove();
    const n2 = document.getElementById('mSeasonNum'); if (n2) n2.remove();
    const b = document.getElementById('mSeasonBtn'); if (b) b.remove();
    const c = document.getElementById('seasonCtl'); if (c) c.classList.remove('mhide', 'min');
  }

  let eWait = null;
  function eOn(v) {
    if (v === 'market') { if (document.getElementById('mktBody')) marketSeg(); }
    if (v === 'season') {
      if (document.getElementById('seasonCtl') && document.querySelector('#seasonCtl .on')) seasonCtl();
      else { clearTimeout(eWait); eWait = setTimeout(() => { if (curView() === 'season') eOn('season'); }, 700); }
    }
  }
  hooks.push({ on: eOn, off: () => { unMarketSeg(); unSeasonCtl(); } });


  /* ====================================================================== F 個股頁（券商 App 式）
     Andy 2026-09-27：「依據我提供的手機頁面，將手機版也設計類似這樣」（華邦電 2344，某券商 App 十張截圖）。
     資訊架構照截圖：
       · 頂部固定報價列：◀ 名稱／市場別徽章＋代號　大字現價　漲跌／漲跌幅 ▶（左右切同族群上一檔／下一檔）
       · 下接一條可橫向捲動的分頁列（只有這一條可以橫捲，整頁不准）
       · 每個分頁：分段鈕 → 關鍵數字（貼著圖）→ 柱狀圖（可收合）→ 每日表（新到舊）；時間窗預設一季（60 交易日）
     ⚠ 券商 App 的「主力」頁是**券商分點**資料 —— CLAUDE.md 第 7 條禁止爬分點。這裡改叫「大戶」，
       用集保千張大戶週增減＋法人合計當替代口徑，頁面上直接寫明「替代口徑：集保大戶＋法人，非券商分點」。
     ⚠ 沒有合規來源的分頁（相關 ETF、權證、董監持股）與分段（當沖、借券賣）**不顯示**，不放空殼
       （CEO 2026-09-27 轉 Andy：「沒來源的分頁先不顯示，不要放空殼」）—— 欄位一到（見 skExtra）就自動長出來。
     做法（跟 C 段同一個原則：桌機一個像素都不動）：
       · 報價列＋分頁列（#mbHead）與分頁內容（#mbBody）是**插在 #stockPage 前面的兄弟節點**，只在 ≤640 插；
         不插在 #stockPage 裡面：industry.js 換股時會整個重寫 #stockPage，插在裡面會被洗掉。
         也不包成一層：sticky 只在父元素的盒子裡有效，#v-industry 才蓋得住整張 K 線卡。
       · K 線分頁直接沿用 industry.js 畫好的 #skChartCard（週期列、指標、即時分 K 全部照舊），只藏掉它的標題列；
         其他分頁的內容由這裡畫，資料讀同一份 `data/stock/<代號>.json`（App.load 的快取，不會多抓一次）。
       · AI 分析分頁直接呼叫 StockAI.mount（積木 stock.mtf 的渲染），不重寫它的內容；離開這一頁就清掉，避免重複 id。
       · 桌機回來（或離開個股頁）一律拆乾淨：skOff()。*/
  /* 分頁順序照 CEO 2026-09-27 轉的清單（參考截圖的順序，AI 分析與新聞放後面）；「完整版」是本站自己加的最後一頁
     （桌機那一組分頁，含技術面訊號、本益比河流等上面各頁沒有的內容 —— 收起來可以，刪掉不行）。
     has(pg)：這一檔沒有那份資料就**不顯示那一頁**（不放空殼）。相關 ETF、權證、董監持股、當沖、借券
     要等 finance-quant 找到合規來源（docs/stock_page_audit_0927.md），欄位到了才加。*/
  /* ★ 2026-10-02（Andy：「基本資料分頁移到總覽旁邊…手機版個股分頁的順序也一起改」，DECISIONS #294）：
     桌機新順序＝總覽、基本資料、指標、營收、獲利、除權息、法人、資券、大戶／散戶、公告／新聞。
     手機沒有「總覽」（第一頁是 K 線），所以照同一個相對順序排：K線、基本資料、指標、營收、獲利（＋手機才有的「財務」緊跟在後）、
     除權息、法人、資券、大戶／散戶；「AI 分析」照 09-27 的決定留在新聞前面，「完整版」最後。
     改前：K線、指標、法人、資券、大戶／散戶、營收、獲利、財務、基本資料、除權息、AI 分析、新聞、完整版。
     會員權限（features.js）是用 data-t 對 #mbTabs 的鈕，不看位置。*/
  const SK_TABS = [
    { t: 'k', n: 'K線' },
    /* ★ 2026-10-07（Andy：ETF 成分股要「左清單、右權重甜甜圈」）：手機原本沒有成分股這一頁 —— ETF 才出現，內容直接用桌機那支（StockHold.render，手機上下堆疊）*/
    { t: 'hold', n: '成分股', has: (pg) => /^00/.test(String((pg.meta && pg.meta.code) || '')) && !!window.StockHold },
    { t: 'basic', n: '基本資料' },
    { t: 'tag', n: '指標' },
    { t: 'rev', n: '營收', has: (pg) => ((pg.revenue && pg.revenue.monthly) || []).length > 0 },
    { t: 'profit', n: '獲利', has: (pg) => ((pg.profit && pg.profit.quarters) || []).some(r => r[5] != null) },
    { t: 'fin', n: '財務', has: (pg) => (pg.pe_history || []).some(r => r.pe != null) || ((pg.profit && pg.profit.quarters) || []).length > 0 },
    { t: 'div', n: '除權息', has: (pg) => { const d = pg.dividends || {}; return (d.by_year || []).some(y => y.n > 0 || y.cash > 0 || y.stock > 0) || (d.upcoming || []).length > 0 || (d.by_period || []).length > 0; } },
    /* 2026-09-28（Andy）：「籌碼」（集保）與「大戶」（主力替代）兩頁併成「大戶／散戶」一頁（三條持股線）；
       主力替代與股東人數拿掉。順序跟桌機一樣：法人、資券、大戶／散戶。*/
    { t: 'inst', n: '法人', has: (pg) => skInstRows(pg).length > 0 },
    { t: 'margin', n: '資券', has: (pg) => (pg.margin || []).some(r => r[1] != null) },
    { t: 'big', n: '大戶／散戶', has: (pg) => (pg.holders || []).some(r => r[1] != null) },
    { t: 'ai', n: 'AI 分析', has: () => !!window.StockAI && !!document.getElementById('aiCard') },
    { t: 'news', n: '新聞', has: (pg) => (pg.news || []).length > 0 || (pg.material_news || []).length > 0 },
    { t: 'full', n: '完整版' },
  ];
  const SK_WIN = 63;                      // 一季 ≈ 63 個交易日（截圖是 7/02～9/24；跟桌機籌碼預設、docs/stock_page_audit_0927.md 同一個數）
  const SK = { code: null, pg: null, wait: null, tries: 0, card: null, ro: null };
  const skApp = () => window.App;
  const skInstRows = (pg) => ((pg.inst_v3 && pg.inst_v3.daily) || []).filter(r => r[1] != null || r[2] != null || r[3] != null);
  /* 這一檔看得到的分頁（沒有資料的那幾頁整顆不出現）*/
  const skTabs = (pg) => SK_TABS.filter(x => { if (!x.has || !pg) return true; try { return !!x.has(pg); } catch (e) { return false; } });
  // 舊版記住的「籌碼」分頁（chip）已併進「大戶／散戶」（big）
  const skTab = () => { const t0 = LS.get('sk.tab', 'k'), t = t0 === 'chip' ? 'big' : t0; return skTabs(SK.pg).some(x => x.t === t) ? t : 'k'; };
  const skSeg = (t, d) => LS.get('sk.seg.' + t, d);
  const int = (v) => v == null || !isFinite(v) ? '—' : Math.round(v).toLocaleString('en-US');
  const sInt = (v) => v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + int(v);
  const sFix = (v, d) => v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(d);
  const uc = (v) => v > 0 ? 'up' : v < 0 ? 'dn' : 'fl';
  const md = (d) => String(d || '').slice(5).replace('-', '/');
  const lot = (v) => v == null ? null : v / 1000;           // 法人原始單位是「股」→ 張

  function skCode() { const h = location.hash.replace('#', '').split('/'); return h[0] === 'stock' ? (h[1] || '') : ''; }

  /* ---- 生命週期：等 industry.js 把個股頁畫完（#skChartCard 帶著這一檔的代號）才接手 ----
     apply() 在換頁 60ms 後就跑，而 renderStock 要等 JSON 回來 —— 所以輪詢，最多 8 秒；
     簡版個股頁（沒有個股 JSON、沒有 #skChartCard）等不到就放手，維持原本的手機版。*/
  function skOn(v) {
    /* ★ 2026-10-09 帳本 85（Andy：「所有分頁打開來 Default 都是最左邊的子分頁」）：手機 v2（html.m4）離開個股頁 → 下次從別頁點進任何一檔都從最左邊「K線」開始。
       改前：記住上次看的分頁（tw.m3.sk.tab），從清單點進另一檔也停在上次那格；改後：只有在個股頁裡換檔（‹ ›、同頁連結）才保留分頁。 */
    if (v !== 'stock') { if (SK.code && document.documentElement.classList.contains('m4')) LS.set('sk.tab', 'k'); skOff(); return; }
    const code = skCode();
    if (!code) { skOff(); return; }
    clearTimeout(SK.wait);
    const ready = () => {
      const card = document.getElementById('skChartCard');
      const id = document.querySelector('#skIdent .mono');
      return card && id && id.textContent.trim() === code ? card : null;
    };
    const card = ready();
    if (!card) {
      if (SK.code !== code) SK.tries = 0;
      if (++SK.tries > 40) { skOff(); return; }
      SK.wait = setTimeout(() => { if (isM() && skCode() === code) skOn('stock'); }, 200);
      return;
    }
    SK.tries = 0;
    /* 已經接手過這一檔：只有 industry.js 重畫過個股頁（K 線卡換了一個節點）才重套一次分頁。
       ⚠ 不要每次都 skPaint：apply() 在手機上**每一次 resize 都會跑**，而 K 線分頁會發 resize 叫圖表重排 ——
         兩個互叫就是每 260ms 一輪的無窮迴圈。*/
    if (SK.code === code && SK.pg && document.getElementById('mbHead')) {
      document.body.classList.add('mbon');
      if (SK.card !== card) { SK.card = card; skPaint(); }
      return;
    }
    const A = skApp();
    if (!A || !A.load) return;
    A.load('stock/' + code, { fallback: null }).then(pg => {
      if (!pg || !isM() || skCode() !== code) return;
      SK.code = code; SK.pg = pg; SK.card = card;
      skBuild(pg);
    });
  }
  function skOff() {
    clearTimeout(SK.wait);
    ['mbHead', 'mbBody'].forEach(id => { const e = document.getElementById(id); if (e) e.remove(); });
    document.body.classList.remove('mbon');
    delete document.body.dataset.mbt;
    if (SK.ro) { try { SK.ro.disconnect(); } catch (e) { /* 略 */ } SK.ro = null; }
    SK.code = null; SK.pg = null; SK.card = null;
  }
  hooks.push({ on: skOn, off: skOff });

  /* ---- 報價列＋分頁列 ---- */
  function skBuild(pg) {
    const A = skApp(), m = pg.meta || {}, s = pg.summary || {};
    const st = document.getElementById('stockPage');
    if (!st) return;
    let head = document.getElementById('mbHead'), body = document.getElementById('mbBody');
    if (!head) { head = document.createElement('div'); head.id = 'mbHead'; head.className = 'mbhead'; st.before(head); }
    if (!body) { body = document.createElement('div'); body.id = 'mbBody'; body.className = 'mbbody'; st.before(body); }
    const mk = m.market === 'TPEX' ? ['櫃', '上櫃'] : m.market === 'TWSE' ? ['市', '上市'] : ['興', m.market || ''];
    head.innerHTML = `<div class="mbq" id="mbQuote">
        <button type="button" class="mbarrow" id="mbPrev" aria-label="上一檔" disabled>◀</button>
        <div class="mbid"><b class="mbname">${esc(m.name || '')}</b><span class="mbcode"><i class="mbmkt" title="${esc(mk[1])}">${mk[0]}</i><span class="num">${esc(m.code || '')}</span></span></div>
        <div class="mbpx num" id="mbPx" data-live="close" data-lc="${esc(m.code)}">${A.fmt.n(s.close)}</div>
        <div class="mbchg"><span class="num" id="mbDelta"></span><span class="num" id="mbPct" data-live="chg" data-lc="${esc(m.code)}">${A.fmt.pct(s.chg_pct, 2)}</span></div>
        <button type="button" class="mbarrow" id="mbNext" aria-label="下一檔" disabled>▶</button></div>
      <div class="mbtabwrap"><button type="button" class="mball" id="mbAll" aria-label="全部分頁">☰</button>
        <nav class="mbtabs" id="mbTabs" role="tablist">${skTabs(pg).map(x => `<button type="button" role="tab" data-t="${x.t}">${x.n}</button>`).join('')}</nav>
        <button type="button" class="mbstar" id="mbStar" aria-pressed="false">☆</button></div>`;
    skQuoteColor();
    skNeighbours(pg);
    const tabs = document.getElementById('mbTabs');
    tabs.onclick = (e) => { const b = e.target.closest('button[data-t]'); if (b) skGo(b.dataset.t); };
    tabs.addEventListener('scroll', () => tabs.classList.toggle('end', tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 4), { passive: true });
    document.getElementById('mbAll').onclick = skAllSheet;
    /* ☆：跳出「要放進哪幾頁」（watchlists.js 的 pick，手機是底部抽屜）*/
    document.getElementById('mbStar').onclick = (e) => { if (SK.pg && TW()) TW().pick(SK.pg.meta.code, e.currentTarget); };
    skStar();
    document.body.classList.add('mbon');
    /* 表頭釘在報價列＋分頁列正下方：高度用量的（字型載入前後會差幾 px），寫進 --mbtop */
    const setTop = () => { const h = head.getBoundingClientRect().height; document.body.style.setProperty('--mbtop', (52 + h) + 'px'); };
    setTop();
    if (window.ResizeObserver) { if (SK.ro) SK.ro.disconnect(); SK.ro = new ResizeObserver(setTop); SK.ro.observe(head); }
    skPaint();
  }
  /* 即時層（live.js）只改 [data-live] 的字與漲跌幅的 class；現價的顏色與「▼1.00」這個漲跌點數由這裡跟著算 */
  function skQuoteColor() {
    const px = document.getElementById('mbPx'), pc = document.getElementById('mbPct'), dl = document.getElementById('mbDelta');
    if (!px || !pc || !dl) return;
    const p = parseFloat(String(px.textContent).replace(/,/g, '')), r = parseFloat(String(pc.textContent).replace(/[+%,]/g, ''));
    const c = isFinite(r) ? uc(r) : 'fl';
    [px, dl].forEach(e => { e.classList.remove('up', 'dn', 'fl'); e.classList.add(c); });
    pc.classList.remove('up', 'dn', 'fl', 'down', 'flat'); pc.classList.add(c === 'dn' ? 'down' : c === 'up' ? 'up' : 'flat');
    if (isFinite(p) && isFinite(r) && r > -100) {
      const d = p - p / (1 + r / 100);
      dl.textContent = (d > 0.0049 ? '▲' : d < -0.0049 ? '▼' : '') + Math.abs(d).toFixed(2);
    } else dl.textContent = '—';
  }
  window.addEventListener('tw:quotes', () => { if (document.getElementById('mbHead')) skQuoteColor(); });
  /* 同族群的上一檔／下一檔：groups_detail 的成員順序（成交值大到小），頭尾相接；只算有個股頁的 */
  function skNeighbours(pg) {
    const A = skApp(), gid = pg.meta && pg.meta.group_id;
    if (!gid) return;
    A.load('groups_detail').then(gd => {
      const g = gd && gd[gid];
      const mem = ((g && g.members) || []).filter(x => x.has_page !== false);
      const i = mem.findIndex(x => x.code === pg.meta.code);
      if (i < 0 || mem.length < 2) return;
      const prev = mem[(i - 1 + mem.length) % mem.length], next = mem[(i + 1) % mem.length];
      const set = (id, x, w) => { const b = document.getElementById(id); if (!b) return;
        b.disabled = false; b.dataset.code = x.code; b.setAttribute('aria-label', `${w}：${x.name} ${x.code}`); b.title = `${w}：${x.name}`;
        b.onclick = () => { location.hash = '#stock/' + x.code; }; };
      set('mbPrev', prev, '上一檔'); set('mbNext', next, '下一檔');
      const q = document.getElementById('mbQuote'); if (q) q.dataset.pos = `${i + 1}/${mem.length}`;
    });
  }
  /* 觀察清單的 ☆（跟總覽的觀察清單同一份 localStorage `tw.watch`，只存代號；見 G 段）*/
  function skStar() {
    const b = document.getElementById('mbStar'); if (!b || !SK.pg) return;
    const on = wHas(SK.pg.meta.code);
    b.textContent = on ? '★' : '☆'; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on));
    b.setAttribute('aria-label', on ? '已在自選清單（選要放哪幾頁）' : '加入自選清單'); b.title = b.getAttribute('aria-label');
  }
  function skAllSheet() {
    const cur = skTab();
    const sh = openSheet(`<div class="mshhead"><b>全部分頁</b></div><div class="mballgrid">${skTabs(SK.pg).map(x =>
      `<button type="button" data-t="${x.t}" class="${x.t === cur ? 'on' : ''}">${x.n}</button>`).join('')}</div>`, { kind: 'sktabs' });
    sh.querySelector('.mballgrid').onclick = (e) => { const b = e.target.closest('button[data-t]'); if (!b) return; closeSheet(); skGo(b.dataset.t); };
  }
  function skGo(t) {
    LS.set('sk.tab', t);
    skPaint();
    /* K 線卡／完整版的圖剛從 display:none 回來：叫圖表重排一次（只在使用者切分頁時發，見 skOn 的註解）*/
    if (t === 'k' || t === 'full') setTimeout(() => window.dispatchEvent(new Event('resize')), 60);
    /* 換分頁回到頂端（報價列下方）：不然從很長的新聞清單切到 K 線，會停在半截 */
    window.scrollTo({ top: 0 });
  }

  /* ---- 畫目前的分頁 ---- */
  function skPaint() {
    const pg = SK.pg; if (!pg) return;
    const t = skTab();
    document.body.dataset.mbt = t;
    const tabs = document.getElementById('mbTabs');
    if (tabs) {
      $$('button[data-t]', tabs).forEach(b => { const on = b.dataset.t === t; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
      const b = $('button.on', tabs);
      if (b) tabs.scrollLeft = Math.max(0, b.offsetLeft - (tabs.clientWidth - b.offsetWidth) / 2);
    }
    const body = document.getElementById('mbBody'); if (!body) return;
    body.dataset.tab = t;
    /* K 線與「完整版」用的是 industry.js 畫好的節點：順手把（藏起來的）第二版分段列切到對應那一段，
       它掛的 .mp-off 才不會跟這裡打架（K 線卡在「K 線」段、#stockTabs／#stockTab 在「財報籌碼」段）。*/
    const want = t === 'k' ? 'K 線' : t === 'full' ? '財報籌碼' : t === 'ai' ? 'AI 分析' : null;
    if (want) { const pb = $$('#v-industry > .mpager button').find(x => x.textContent.trim() === want); if (pb && !pb.classList.contains('on')) pb.click(); }
    if (t === 'k') { body.innerHTML = ''; return; }
    if (t === 'full') {
      body.innerHTML = '';
      return;
    }
    const fn = { hold: (p, b) => window.StockHold.render(p, b), ai: skAi, tag: skTagTab, inst: skInst, big: skBig, margin: skMargin, rev: skRev, fin: skFin, profit: skProfit, basic: skBasic, div: skDiv, news: skNews }[t];
    try { fn(pg, body); } catch (e) { console.warn('[m3 個股]', e); body.innerHTML = '<div class="mbempty">這一頁載入失敗</div>'; }
  }

  /* ---- 共用：分段鈕、關鍵數字、柱狀圖、每日表 ---- */
  function segBar(t, segs, cur) {
    return `<div class="mbseg" role="tablist" data-tab="${t}">${segs.map(s => `<button type="button" role="tab" data-s="${s[0]}" class="${s[0] === cur ? 'on' : ''}" aria-selected="${s[0] === cur}">${s[1]}</button>`).join('')}</div>`;
  }
  function wireSeg(body, t) {
    const bar = $('.mbseg', body); if (!bar) return;
    bar.onclick = (e) => { const b = e.target.closest('button[data-s]'); if (!b || b.classList.contains('on')) return; LS.set('sk.seg.' + t, b.dataset.s); skPaint(); };
  }
  const kpi = (items) => `<div class="mbkpi">${items.filter(Boolean).map(x => `<span>${x[0]} <b class="num ${x[2] || ''}">${x[1]}</b></span>`).join('')}</div>`;
  const legend = (items) => `<div class="mblegend">${items.map(x => `<span><i style="background:${x[1]}${x[2] ? ';height:3px' : ''}"></i>${x[0]}</span>`).join('')}</div>`;
  function chartBox(inner) {
    const fold = LS.get('sk.fold', '0') === '1';
    return `<div class="mbchartbox${fold ? ' fold' : ''}" id="mbChartBox">${inner}<div class="mbchart" id="mbChart"></div>
      <button type="button" class="mbfold" id="mbFold" aria-expanded="${!fold}">${fold ? '展開圖 ﹀' : '收合圖 ︿'}</button></div>`;
  }
  function wireFold(body, draw) {
    const b = $('#mbFold', body), box = $('#mbChartBox', body); if (!b || !box) return;
    b.onclick = () => { const f = !box.classList.contains('fold'); box.classList.toggle('fold', f); LS.set('sk.fold', f ? '1' : '0');
      b.textContent = f ? '展開圖 ﹀' : '收合圖 ︿'; b.setAttribute('aria-expanded', String(!f)); if (!f && draw) setTimeout(draw, 30); };
  }
  /* 柱狀圖（ECharts，App.chart）。o.bars：[{name, data, color?}]（沒給 color 就紅正綠負）；o.lines：右軸的折線 */
  function barChart(o) {
    const A = skApp(), CH = A.CH, el = document.getElementById('mbChart');
    if (!el || $('#mbChartBox.fold')) return;
    const n = o.x.length;
    const pick = (i) => n <= 8 || i === 0 || i === n - 1 || i === Math.floor((n - 1) / 2);
    const signed = (arr) => arr.map(v => ({ value: v, itemStyle: { color: v > 0 ? CH.up : v < 0 ? CH.down : CH.ink3 } }));
    const yfmt = o.yfmt || ((v) => { const a = Math.abs(v); return a >= 1e4 ? (v / 1e4).toFixed(a >= 1e5 ? 0 : 1) + '萬' : String(Math.round(v)); });
    const hasR = (o.lines || []).length > 0;
    const series = (o.bars || []).map((b, k) => ({ name: b.name, type: 'bar', barMaxWidth: 14, barGap: '15%',
      data: b.color ? b.data : signed(b.data), itemStyle: b.color ? { color: b.color } : undefined, z: 2 + k,
      /* 柱頂不標數字：App.chart 的 softenOption 會替 ≤ 一定根數的長條自動補標籤，60 根、12 根雙柱標上去會疊成一片；
         數字在圖上方的關鍵數字列與下方的每日表，點一根看提示框 */
      label: { show: false } }))
      .concat((o.lines || []).map(L => ({ name: L.name, type: 'line', yAxisIndex: hasR && !L.left ? 1 : 0, data: L.data, showSymbol: n <= 16,
        symbolSize: 5, connectNulls: true, smooth: false, lineStyle: { color: L.color, width: 2 }, itemStyle: { color: L.color },
        areaStyle: L.area ? { color: L.color, opacity: 0.18 } : undefined, label: { show: false }, z: 5 })));
    A.chart(el, {
      animation: false,
      grid: { left: 50, right: hasR ? 44 : 12, top: 12, bottom: 24 },
      tooltip: { ...A.tip, trigger: 'axis', confine: true, axisPointer: { type: o.linesOnly ? 'line' : 'shadow' },
        formatter: (ps) => `<b>${o.full ? o.full[ps[0].dataIndex] : ps[0].axisValue}</b>` + ps.map(p => {
          const v = p.value && typeof p.value === 'object' ? p.value.value : p.value;
          const f = p.seriesType === 'line' && hasR ? (o.y2tip || o.y2fmt || yfmt) : (o.ytip || yfmt);
          return `<br>${p.marker}${p.seriesName} ${v == null ? '—' : f(v)}`; }).join('') },
      xAxis: { ...A.axisStyle, type: 'category', data: o.x, boundaryGap: !o.linesOnly,
        axisLabel: { color: CH.ink3, fontSize: 12, fontFamily: A.NUM_FONT, interval: (i) => pick(i), hideOverlap: true, formatter: (v, i) => pick(i) ? v : '' },
        axisTick: { show: false } },
      yAxis: [{ ...A.axisStyle, type: 'value', scale: !!o.scale, splitNumber: 4, axisLabel: { color: CH.ink3, fontSize: 12, fontFamily: A.NUM_FONT, formatter: yfmt } }]
        .concat(hasR ? [{ ...A.axisStyle, type: 'value', scale: true, splitNumber: 4, splitLine: { show: false },
          axisLabel: { color: CH.ink3, fontSize: 12, fontFamily: A.NUM_FONT, formatter: o.y2fmt || yfmt } }] : []),
      series,
    }, { notMerge: true });
  }
  /* 每日表：cols＝[{h, f(row)→[文字, class]}]；rows 已經是新到舊。sel＝目前分段對應的欄（加底色） */
  function table(cols, rows, sel, cap) {
    return `<div class="mbtblwrap"><table class="mbtbl">${cap ? `<caption>${cap}</caption>` : ''}<thead><tr>${cols.map((c, i) => `<th class="${i === sel ? 'sel' : ''}">${c.h}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r => `<tr>${cols.map((c, i) => { const v = c.f(r); return `<td class="${(v[1] || '')}${i === sel ? ' sel' : ''}">${v[0]}</td>`; }).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  const empty = (msg) => `<div class="mbempty">${msg}</div>`;

  /* ---- AI 分析：不另外 render —— 用 app.js miaStock 搬進 #aiCard 的那一個 #skAi 節點（積木 stock.mtf，四標籤版）----
     2026-09-27 協調：AI 分析四標籤版（claude/ai-topright）桌機住在 K 線卡右上角；手機由 miaStock 把**同一個節點**
     搬進空殼 #aiCard（分段導覽的「AI 分析」段）。這裡只負責讓 #aiCard 在「AI 分析」分頁露出來（CSS 看 data-mbt="ai"），
     順便把藏起來的第二版分段列切到「AI 分析」段，它掛的 .mp-off 才不會把 #aiCard 藏掉。
     選中的標籤、收合狀態都跟著節點走，不重畫。*/
  function skAi(pg, body) {
    const card = document.getElementById('aiCard'), ai = document.getElementById('skAi');
    if (!card || !ai) { body.innerHTML = empty('AI 分析載入失敗'); return; }
    body.innerHTML = '';
    if (ai.parentElement !== card) card.appendChild(ai);      // miaStock 還沒跑到（或順序不同）時先搬，行為跟它一樣
    card.classList.remove('mp-off');
    if (window.StockAI && window.StockAI.refit) setTimeout(() => { try { window.StockAI.refit(); } catch (e) { /* 略 */ } }, 30);
  }

  /* ---- 指標：一列一個標籤（產業鏈／族群／題材／指標），點了進去 ----
     指標列先用現有 payload 在前端判斷（月營收、三率、法人連買、集保、均線、量比、估值）；
     finance-quant 補的後端標籤欄位（pg.tags）一到就改用它 —— 規則只留一份在後端。*/
  function skTags(pg) {
    const L = window.Link || {}, m = pg.meta || {}, s = pg.summary || {}, f = pg.fundamental || {};
    const out = [];
    const cid = L.gchain && L.gchain[m.group_id];
    if (cid && L.chains && L.chains[cid]) out.push({ k: '產業鏈', n: L.chains[cid], href: '#industry/' + cid });
    (m.groups || []).forEach(gn => { const gid = (L.gid && L.gid[gn]) || m.group_id; out.push({ k: '族群', n: gn, href: '#industry/group/' + encodeURIComponent(gid) }); });
    ((L.ctheme && L.ctheme[m.code]) || []).forEach(t => out.push({ k: '題材', n: t.name, href: '#heatmap/theme/' + encodeURIComponent(t.id) }));
    /* 後端標籤（finance-quant：pg.tags＝{items:[{id, kind, label, hit, detail}], n_hit}）一到就改用它，規則只留一份在後端；
       hit===false 的收進「未符合」（收起來可以，刪掉不行），hit===null（資料不足）不列。舊的陣列寫法也認。*/
    const bt = Array.isArray(pg.tags) ? pg.tags : (pg.tags && Array.isArray(pg.tags.items) ? pg.tags.items : null);
    if (bt && bt.length) {
      bt.forEach(x => {
        out.push({ k: x.type || x.kind || '指標', n: (x.name || x.label || '') + (x.hit == null ? '（資料不足）' : ''), tone: x.tone != null ? x.tone : (x.hit === true ? 1 : 0), go: x.tab || null, href: x.href || null, miss: x.hit !== true, det: x.detail || '' }); });
      return out;
    }
    const R = (n, tone, go) => out.push({ k: '指標', n, tone, go });
    const mo = (pg.revenue && pg.revenue.monthly) || [];
    const y3 = mo.slice(-3).map(r => r[2]);
    if (y3.length === 3 && y3.every(v => v != null && v > 20)) R('連三月營收年增 > 20%', 1, 'rev');
    if (f.rev_record_high) R('月營收創新高', 1, 'rev');
    if (f.rev_streak >= 3) R(`月營收連續 ${f.rev_streak} 個月年增`, 1, 'rev');
    const q4 = ((pg.profit && pg.profit.quarters) || []).slice(-4);
    if (q4.length === 4) {
      if (q4.filter(r => r[2] != null && r[2] > 30).length >= 3) R('近四季有三季毛利率 > 30%', 1, 'profit');
      if (q4.filter(r => r[3] != null && r[3] > 10).length >= 3) R('近四季有三季營益率 > 10%', 1, 'profit');
      if (q4.filter(r => r[5] != null && r[5] < 0).length >= 2) R('近四季有兩季以上虧損', -1, 'profit');
    }
    if (f.roe != null && f.roe >= 15) R(`股東權益報酬率 ${(+f.roe).toFixed(1)}%（≥ 15%）`, 1, 'profit');
    if (f.vs_median != null && !f.thin_sample && f.vs_median < -10) R('本益比低於同族群中位 10% 以上', 1, null);
    const iv = ((pg.inst_v3 && pg.inst_v3.daily) || []).filter(r => r[1] != null || r[2] != null);
    const streak = (k) => { let n = 0, sg = 0; for (let i = iv.length - 1; i >= 0; i--) { const v = iv[i][k]; const g = v > 0 ? 1 : v < 0 ? -1 : 0; if (!g) break; if (!sg) sg = g; if (g !== sg) break; n++; } return n * sg; };
    const fs = streak(1), ts = streak(2);
    if (Math.abs(fs) >= 3) R(`外資連 ${Math.abs(fs)} 日${fs > 0 ? '買超' : '賣超'}`, Math.sign(fs), 'inst');
    if (Math.abs(ts) >= 3) R(`投信連 ${Math.abs(ts)} 日${ts > 0 ? '買超' : '賣超'}`, Math.sign(ts), 'inst');
    const ho = pg.holders || [];
    if (ho.length >= 2 && ho[ho.length - 1][1] != null && ho[ho.length - 2][1] != null) {
      const d = ho[ho.length - 1][1] - ho[ho.length - 2][1];
      if (Math.abs(d) >= 0.005) R(`千張大戶持股週${d > 0 ? '增' : '減'} ${Math.abs(d).toFixed(2)} 個百分點`, Math.sign(d), 'big');
    }
    if (s.ma_align === 1) R('均線多頭排列', 1, 'k'); else if (s.ma_align === -1) R('均線空頭排列', -1, 'k');
    if (s.bias20 != null) R(s.bias20 >= 0 ? '站上 20 日均線' : '跌破 20 日均線', s.bias20 >= 0 ? 1 : -1, 'k');
    if (s.vol_ratio != null && s.vol_ratio >= 1.5) R(`量比 ${(+s.vol_ratio).toFixed(1)} 倍（放量）`, 0, 'k');
    else if (s.vol_ratio != null && s.vol_ratio <= 0.5) R(`量比 ${(+s.vol_ratio).toFixed(1)} 倍（量縮）`, 0, 'k');
    const dv = pg.dividends || {};
    if (dv.yield_ttm != null && dv.yield_ttm >= 4) R(`殖利率 ${(+dv.yield_ttm).toFixed(1)}%（≥ 4%）`, 1, null);
    return out;
  }
  function skTagTab(pg, body) {
    const tags = skTags(pg);
    const nInd = tags.filter(x => x.k === '指標' && !x.miss).length;
    const li = (x, i) => `<li><button type="button" data-i="${i}"><i class="mbtagk">${esc(x.k)}</i><span class="${x.miss ? '' : x.tone > 0 ? 'up' : x.tone < 0 ? 'dn' : ''}">${esc(x.n)}${x.det ? `<small>${esc(x.det)}</small>` : ''}</span><em aria-hidden="true">›</em></button></li>`;
    const miss = tags.map((x, i) => [x, i]).filter(p => p[0].miss);
    body.innerHTML = `<div class="mbtaghead"><b>符合 ${nInd} 項指標</b></div>
      <ul class="mbtags">${tags.map((x, i) => x.miss ? '' : li(x, i)).join('')}</ul>
      ${miss.length ? `<details class="mbmiss"><summary>未符合／資料不足 ${miss.length} 項 ›</summary><ul class="mbtags">${miss.map(p => li(p[0], p[1])).join('')}</ul></details>` : ''}
      <div class="mbfoot">${esc((window.App && window.App.DISC_LINE) || '以下為依公開資料統計計算之結果，不構成任何投資建議或參考')}</div>`;
    body.onclick = (e) => {
      const b = e.target.closest('.mbtags button[data-i]'); if (!b) return;
      const x = tags[+b.dataset.i];
      if (x.href) location.hash = x.href; else if (x.go) skGo(x.go);
    };
  }

  /* ---- 法人：外資｜投信｜自營商｜合計；柱＝每日買賣超（張），表＝每日四欄 ---- */
  function skInst(pg, body) {
    const all = ((pg.inst_v3 && pg.inst_v3.daily) || []).filter(r => r[1] != null || r[2] != null || r[3] != null);
    if (!all.length) { body.innerHTML = empty('尚無法人資料'); return; }
    const icol = (pg.inst_v3 && pg.inst_v3.columns) || [], iSelf = icol.indexOf('dealer_self'), iHedge = icol.indexOf('dealer_hedge');
    const rows = all.slice(-SK_WIN).map(r => ({ d: r[0], f: lot(r[1]), t: lot(r[2]), p: lot(r[3]), s: lot((r[1] || 0) + (r[2] || 0) + (r[3] || 0)),
      ps: iSelf >= 0 && r[iSelf] != null ? lot(r[iSelf]) : null, ph: iHedge >= 0 && r[iHedge] != null ? lot(r[iHedge]) : null }));
    const SEG = [['f', '外資'], ['t', '投信'], ['p', '自營商'], ['s', '合計']];
    const seg = SEG.some(x => x[0] === skSeg('inst', 'f')) ? skSeg('inst', 'f') : 'f';
    const nm = SEG.find(x => x[0] === seg)[1];
    const sum = (n) => rows.slice(-n).reduce((a, r) => a + (r[seg] || 0), 0);
    const last = rows[rows.length - 1];
    body.innerHTML = segBar('inst', SEG, seg)
      + chartBox(kpi([[`${md(last.d)} ${nm}`, sInt(last[seg]), uc(last[seg])], ['5 日', sInt(sum(5)), uc(sum(5))], ['20 日', sInt(sum(20)), uc(sum(20))], [`${rows.length} 日`, sInt(sum(rows.length)), uc(sum(rows.length))]]
        .concat(seg === 'p' && (last.ps != null || last.ph != null) ? [['自行買賣', sInt(last.ps), uc(last.ps)], ['避險', sInt(last.ph), uc(last.ph)]] : [])))
      + table([{ h: '日期', f: r => [md(r.d)] }, { h: '外資', f: r => [sInt(r.f), uc(r.f)] }, { h: '投信', f: r => [sInt(r.t), uc(r.t)] },
        { h: '自營商', f: r => [sInt(r.p), uc(r.p)] }, { h: '合計', f: r => [sInt(r.s), uc(r.s)] }], rows.slice().reverse(), SEG.findIndex(x => x[0] === seg) + 1, '單位：張；紅＝買超、綠＝賣超')
      + `<div class="mbfoot">法人資料比價量晚一個交易日。</div>`;
    const draw = () => barChart({ x: rows.map(r => md(r.d)), full: rows.map(r => r.d), bars: [{ name: nm, data: rows.map(r => r[seg] == null ? null : Math.round(r[seg])) }], ytip: (v) => sInt(v) + ' 張' });
    wireSeg(body, 'inst'); wireFold(body, draw); draw();
  }

  /* ---- 集保週資料 ----
     holders 每列＝[公布日, 千張大戶%, 400–1000 張%, 10 張以下散戶%, 股東人數]（pipeline/compute/stockpage.py holder_series）。
     股東人數（第 5 欄）2026-09-28 起畫面不再顯示（Andy：「籌碼內股東人數拿掉」），這裡照樣讀進來但不用。*/
  function skWeeks(pg) {
    const ho = (pg.holders || []).filter(r => r[1] != null);
    return ho.map((r, i) => { const p = i > 0 ? ho[i - 1] : null;
      const dd = (k) => p && p[k] != null && r[k] != null ? r[k] - p[k] : null;
      return { d: r[0], big: r[1], mid: r[2], ret: r[3], dBig: dd(1), dMid: dd(2), dRet: dd(3) }; });
  }
  const tri = (v) => v == null ? '' : v > 0 ? '▲' : v < 0 ? '▼' : '';

  /* ---- 大戶／散戶（2026-09-28 Andy：「大戶／散戶持股獨立分頁，並且千張、400–1000、≤10 持股線圖需重點且可篩選」）----
     以前手機有「籌碼」（集保三選一的面積圖＋股東人數）和「大戶」（主力替代：法人買賣超＋集中度）兩頁。
     Andy 要主力替代拿掉、股東人數拿掉，所以兩頁併成這一頁：
       · 「持股比例」段：三條週線（千張以上＝青、400～1000 張＝琥珀、≤10 張＝紫，避開紅綠），每條各自一格、各自 Y 軸；
         上方三顆色塊＝圖例兼開關，按掉一條那一格就收掉（記在 sk.hoLines）；下方每週表。
       · 「董監持股」段：每月申報（payload 有 insider 才出現）。
     跟桌機 industry.js tabHolders 同一套口徑與配色。*/
  const SK_HO = [{ k: 'big', d: 'dBig', n: '千張以上', c: 'cyan' }, { k: 'mid', d: 'dMid', n: '400～1000 張', c: 'amber' }, { k: 'ret', d: 'dRet', n: '≤10 張', c: 'violet' }];
  function skBig(pg, body) {
    const W = skWeeks(pg);
    if (!W.length) { body.innerHTML = empty('尚無大戶／散戶持股資料'); return; }
    const A = skApp(), CH = A.CH;
    const hasIns = !!(pg.insider && typeof pg.insider === 'object');
    const SEG = [['lines', '持股比例']].concat(hasIns ? [['ins', '董監持股']] : []);
    const seg = SEG.some(x => x[0] === skSeg('big', 'lines')) ? skSeg('big', 'lines') : 'lines';
    if (seg === 'ins') { skInsider(pg, body, SEG); return; }
    const raw = String(LS.get('sk.hoLines', 'big,mid,ret'));
    const on = new Set(raw.split(',').filter(k => SK_HO.some(h => h.k === k)));
    const last = W[W.length - 1];
    const pct = (v) => v == null ? '—' : (+v).toFixed(2) + '%';
    const tg = SK_HO.map(h => `<button type="button" class="mbhotgl${on.has(h.k) ? '' : ' off'}" data-k="${h.k}" aria-pressed="${on.has(h.k)}" style="--hc:${CH[h.c]}">`
      + `<i></i><span class="nm">${h.n}</span><b class="num">${pct(last[h.k])}</b><small class="num ${uc(last[h.d])}">${sFix(last[h.d], 2)}</small></button>`).join('');
    const cols = [{ h: '公布日', f: r => [md(r.d)] }].concat(SK_HO.map(h => ({ h: h.n.replace(' 張', ''), f: r => [r[h.k] == null ? '—' : tri(r[h.d]) + (+r[h.k]).toFixed(2), uc(r[h.d])] })));
    // 補不了歷史的原因跟桌機 tabHolders 同一句（集保只公開最新一週；DECISIONS #210）
    const grow = W.length < 52 ? `從 ${esc(W[0].d)} 起每週累積，目前 ${W.length} 週。` : '';
    body.innerHTML = segBar('big', SEG, seg)
      + `<div class="mbhotgls" id="mbHoTgls" role="group" aria-label="顯示哪幾條線">${tg}</div>`
      + chartBox('')
      + table(cols, W.slice().reverse(), -1, '單位：持股比例 %；▲▼＝比上一週（紅＝增加、綠＝減少）')
      + `<div class="mbfoot">每週公布一次。千張以上往上、≤10 張往下＝籌碼往大戶集中。${grow}散戶＝持股 ≤10 張，與部分券商 App 的散戶定義不同。</div>`;
    const draw = () => {
      const el = document.getElementById('mbChart');
      if (!el || $('#mbChartBox.fold')) return;
      const L = SK_HO.filter(h => on.has(h.k));
      body.dataset.hoLines = L.map(h => h.k).join(',');
      if (!L.length) { A.empty(el, '三條線都已隱藏'); return; }
      if (el.classList.contains('isempty')) { el.classList.remove('isempty'); el.innerHTML = ''; }
      const CELL = 104, TOP = 2, BOT = 24;
      el.style.height = (TOP + BOT + CELL * L.length) + 'px';
      const x = W.map(r => md(r.d));
      A.chart(el, {
        animation: false,
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        tooltip: { ...A.tip, trigger: 'axis', confine: true, formatter: (ps) => { const r = W[ps[0].dataIndex]; if (!r) return '';
          return `<b>${esc(r.d)}</b>` + L.map(h => `<br><span style="color:${CH[h.c]}">●</span> ${h.n} ${pct(r[h.k])}　週 ${r[h.d] == null ? '—' : sFix(r[h.d], 2) + 'pp'}`).join(''); } },
        title: L.map((h, i) => ({ left: 46, top: TOP + i * CELL, padding: 0, text: h.n, textStyle: { color: CH[h.c], fontSize: 12.5, fontWeight: 700 } })),
        grid: L.map((h, i) => ({ left: 46, right: 12, top: TOP + i * CELL + 20, height: CELL - 30 })),
        xAxis: L.map((h, i) => ({ ...A.axisStyle, type: 'category', data: x, gridIndex: i, boundaryGap: false,
          axisTick: { show: false }, axisLabel: { show: i === L.length - 1, color: CH.ink3, fontSize: 12, fontFamily: A.NUM_FONT, hideOverlap: true } })),
        yAxis: L.map((h, i) => ({ ...A.axisStyle, type: 'value', gridIndex: i, scale: true, splitNumber: 2,
          axisLabel: { color: CH.ink3, fontSize: 11, fontFamily: A.NUM_FONT, formatter: (v) => (+v).toFixed(v >= 10 ? 1 : 2) } })),
        series: L.map((h, i) => ({ name: h.n, type: 'line', xAxisIndex: i, yAxisIndex: i, data: W.map(r => r[h.k]), connectNulls: true,
          showSymbol: true, symbolSize: 7, lineStyle: { color: CH[h.c], width: 3 }, itemStyle: { color: CH[h.c] }, label: { show: false } })),
      }, { notMerge: true });
    };
    $('#mbHoTgls', body).onclick = (e) => {
      const b = e.target.closest('button[data-k]'); if (!b) return;
      const k = b.dataset.k;
      if (on.has(k)) on.delete(k); else on.add(k);
      LS.set('sk.hoLines', SK_HO.filter(h => on.has(h.k)).map(h => h.k).join(','));
      b.classList.toggle('off', !on.has(k)); b.setAttribute('aria-pressed', String(on.has(k)));
      draw();
    };
    wireSeg(body, 'big'); wireFold(body, draw); draw();
  }

  function skInsider(pg, body, SEG) {
    const A = skApp(), CH = A.CH, ins = pg.insider || {};
    const mo = (ins.monthly || []).filter(r => r && r.ym);
    const foot = '<div class="mbfoot">董監持股比例＝董監目前持股 ÷ 總股數；每月申報一次。</div>';
    if (!mo.length) {
      body.innerHTML = segBar('big', SEG, 'ins') + '<div class="mbwhy">尚無董監持股資料</div>' + foot;
      wireSeg(body, 'big'); return;
    }
    const last = mo[mo.length - 1];
    const pct = (v) => v == null ? '—' : (+v).toFixed(2) + '%';
    body.innerHTML = segBar('big', SEG, 'ins')
      + chartBox(kpi([[`${esc(last.ym)} 董監持股`, pct(last.director_pct)], ['設質', last.pledge_pct != null ? (+last.pledge_pct).toFixed(1) + '%' : '—'], ['董監', last.n_directors != null ? last.n_directors + ' 人' : '—']]))
      + table([{ h: '月份', f: r => [esc(r.ym)] }, { h: '董監持股', f: r => [r.flag === 'over100' ? '—' : pct(r.director_pct)] }, { h: '設質', f: r => [r.pledge_pct == null ? '—' : (+r.pledge_pct).toFixed(1) + '%'] },
        { h: '董監人數', f: r => [r.n_directors == null ? '—' : String(r.n_directors)] }], mo.slice().reverse(), 1, '每月申報一次')
      + foot;
    const draw = () => barChart({ x: mo.map(r => r.ym), linesOnly: true, scale: true, bars: [],
      lines: [{ name: '董監持股', data: mo.map(r => r.flag === 'over100' ? null : r.director_pct), color: CH.cyan, area: true, left: true }], yfmt: (v) => (+v).toFixed(1) + '%', ytip: (v) => (+v).toFixed(2) + '%' });
    wireSeg(body, 'big'); wireFold(body, draw); draw();
  }

  /* ---- 資券：融資｜融券（＋當沖｜借券賣：欄位到了才出現）----
     margin 每列＝[日期, 融資餘額, 融券餘額, 融資增減, 融券增減]（張）。
     當沖／借券賣出：finance-quant 在補（分支 claude/stock-data-audit），欄位名稱未定 —— skExtra 先認幾個候選名，
     每列格式 [日期, 張數, …]；認不到就不顯示那個分段（不放空殼）。*/
  function skExtra(pg, names) {
    for (const k of names) { const v = pg[k]; if (Array.isArray(v) && v.length) return v; if (v && Array.isArray(v.daily) && v.daily.length) return v.daily; }
    return null;
  }
  function skMargin(pg, body) {
    const mg = (pg.margin || []).filter(r => r[1] != null);
    if (!mg.length) { body.innerHTML = empty('尚無融資融券資料'); return; }
    const A = skApp(), CH = A.CH;
    /* 當沖／借券賣出：finance-quant 的規格（docs/stock_page_audit_0927.md §3）併進 margin 每列的第 6～9 欄
       ［daytrade_lots, daytrade_ratio, sbl_sell_lots, sbl_balance_lots］，欄名在 pg.margin_columns。
       · payload 有這幾欄（margin_columns 列得出來）→ 四段照截圖都出現（融資｜當沖｜融券｜借券賣）；
         那一段近一季完全沒資料（回補還沒輪到，或資料源帳號等級拿不到）→ 不畫假圖，寫出原因（跟桌機同一段話）。
       · payload 沒有這幾欄（舊版）→ 只有融資／融券兩段，不放空殼。
       舊的候選寫法（獨立陣列 pg.daytrade／pg.sbl）也認。*/
    const mc = Array.isArray(pg.margin_columns) ? pg.margin_columns : [];
    const ci = (name, dflt) => { const i = mc.indexOf(name); return i >= 0 ? i : (mc.length ? -1 : dflt); };
    const I = { dt: ci('daytrade_lots', -1), dr: ci('daytrade_ratio', -1), sl: ci('sbl_sell_lots', -1), sb: ci('sbl_balance_lots', -1) };
    const alt = (names) => { const v = skExtra(pg, names); return v ? new Map(v.map(r => [String(r[0]).slice(0, 10), r[1]])) : null; };
    const dtAlt = I.dt < 0 ? alt(['daytrade', 'day_trade', 'daytrading']) : null, slAlt = I.sl < 0 ? alt(['sbl', 'lending', 'sbl_sell', 'lend_sell']) : null;
    const at = (r, i) => i >= 0 && r.length > i ? r[i] : null;
    const rows = mg.slice(-SK_WIN).map(r => ({ d: r[0], mb: r[1], sb: r[2], mc: r[3], sc: r[4],
      dt: dtAlt ? dtAlt.get(r[0]) : at(r, I.dt), dr: at(r, I.dr), sl: slAlt ? slAlt.get(r[0]) : at(r, I.sl), slb: at(r, I.sb) }));
    const hasCol = { dt: I.dt >= 0 || !!dtAlt, sl: I.sl >= 0 || !!slAlt };
    const hasData = { dt: rows.some(r => r.dt != null), sl: rows.some(r => r.sl != null) };
    const SEG = [['m', '融資']].concat(hasCol.dt ? [['dt', '當沖']] : []).concat([['s', '融券']]).concat(hasCol.sl ? [['sl', '借券賣']] : []);
    const seg = SEG.some(x => x[0] === skSeg('margin', 'm')) ? skSeg('margin', 'm') : 'm';
    const nm = SEG.find(x => x[0] === seg)[1];
    const last = rows[rows.length - 1];
    const sum = (k, n) => rows.slice(-n).reduce((a, r) => a + (r[k] || 0), 0);
    /* ★ 2026-10-02（#294 對帳時順手抓到）：當沖／借券賣出跟融資券是兩個來源，常晚幾天才到 ——
       改前一律讀最後一列（融資券最新那天），當沖那天還沒資料就顯示「09/30 當沖 — 張」。
       改成各自讀「最後一個有值的交易日」並寫出那一天（跟總覽籌碼快照、桌機資券分頁同一個規則）；5 日也只數有值的天。*/
    const lastOf = (k) => rows.slice().reverse().find(r => r[k] != null) || last;
    const lastDt = lastOf('dt'), lastSl = lastOf('sl');
    const dt5 = rows.filter(r => r.dt != null).slice(-5), sl5 = rows.filter(r => r.sl != null).slice(-5);
    const ratio = last.mb ? last.sb / last.mb * 100 : null;
    // 2026-09-28：讀者語言（不寫資料集名稱與帳號等級），跟桌機 tabMargin 同一句
    const WHY = { dt: '尚無當沖資料', sl: '尚無借券賣出資料' };
    /* 表照截圖：日期｜融資｜當沖｜融券｜借券賣（融資／融券＝當日增減；當沖＝當沖成交張數；借券賣＝當日借券賣出張數）。
       舊 payload 沒有當沖／借券欄 → 表改放資餘／券餘，不放整欄「—」。*/
    const cols = [{ h: '日期', f: r => [md(r.d)] }, { h: '融資', f: r => [sInt(r.mc), uc(r.mc)] }]
      .concat(hasCol.dt ? [{ h: '當沖', f: r => [r.dt == null ? '—' : int(r.dt)] }] : [])
      .concat([{ h: '融券', f: r => [sInt(r.sc), uc(r.sc)] }])
      .concat(hasCol.sl ? [{ h: '借券賣', f: r => [r.sl == null ? '—' : int(r.sl)] }] : [])
      .concat(!hasCol.dt && !hasCol.sl ? [{ h: '資餘', f: r => [int(r.mb)] }, { h: '券餘', f: r => [int(r.sb)] }] : []);
    const sel = cols.findIndex(c => c.h === nm);
    /* ★ 2026-10-03（#304，跟桌機 tabMargin 同一個規則）：pg.margin_asof＝資券三個來源全市場最新到哪天。
       某個來源比其他舊＝資料源自己停在那天 → 那之後的格子寫「未提供」（不是 0），表下寫「更新到 MM-DD」。*/
    const AS = pg.margin_asof || {};
    const asRef = [AS.margin, AS.daytrade, AS.sbl].filter(Boolean).sort().pop() || '';
    const CUT = { dt: AS.daytrade && AS.daytrade < asRef ? AS.daytrade : null, sl: AS.sbl && AS.sbl < asRef ? AS.sbl : null };
    for (const c of cols) {
      const k = c.h === '當沖' ? 'dt' : c.h === '借券賣' ? 'sl' : null;
      if (!k || !CUT[k]) continue;
      const f0 = c.f; c.f = r => (r[k] == null && String(r.d).slice(0, 10) > CUT[k] ? ['未提供', 'mbna'] : f0(r));
    }
    const srcFoot = [hasCol.dt && CUT.dt && `當沖資料只更新到 ${md(CUT.dt)}`, hasCol.sl && CUT.sl && `借券賣出資料只更新到 ${md(CUT.sl)}`].filter(Boolean).join('、');
    const srcTxt = srcFoot ? `<span class="mbsrc" data-src-cut="1">${srcFoot}；之後寫「未提供」，不是 0。</span>` : '';
    const cap = '單位：張；融資／融券＝當日增減（紅＝增加、綠＝減少）' + (hasCol.dt ? '；當沖＝當沖成交張數' : '') + (hasCol.sl ? '；借券賣＝當日借券賣出張數（向借券系統借來賣，多為法人避險，不是融券）' : '；資餘／券餘＝餘額');
    const tbl = table(cols, rows.slice().reverse(), sel, cap);
    if ((seg === 'dt' || seg === 'sl') && !hasData[seg]) {
      body.innerHTML = segBar('margin', SEG, seg) + `<div class="mbwhy"><b>${nm}：這一檔還沒有資料</b>${WHY[seg]}</div>` + tbl + (srcTxt ? `<div class="mbfoot">${srcTxt}</div>` : '');
      wireSeg(body, 'margin'); return;
    }
    const k = seg === 'm' ? [[`${md(last.d)} 融資增減`, sInt(last.mc), uc(last.mc)], ['融資餘額', int(last.mb) + ' 張'], ['5 日', sInt(sum('mc', 5)), uc(sum('mc', 5))], ['券資比', ratio != null ? ratio.toFixed(1) + '%' : '—']]
      : seg === 's' ? [[`${md(last.d)} 融券增減`, sInt(last.sc), uc(last.sc)], ['融券餘額', int(last.sb) + ' 張'], ['5 日', sInt(sum('sc', 5)), uc(sum('sc', 5))], ['券資比', ratio != null ? ratio.toFixed(1) + '%' : '—']]
        : seg === 'dt' ? [[`${md(lastDt.d)} 當沖`, int(lastDt.dt) + ' 張'], ['當沖率', lastDt.dr != null ? (+lastDt.dr).toFixed(1) + '%' : '—'], ['5 日平均', dt5.length ? int(dt5.reduce((a, r) => a + r.dt, 0) / dt5.length) + ' 張' : '—']]
          : [[`${md(lastSl.d)} 借券賣出`, int(lastSl.sl) + ' 張'], ['借券賣出餘額', lastSl.slb != null ? int(lastSl.slb) + ' 張' : '—'], ['5 日合計', int(sl5.reduce((a, r) => a + r.sl, 0)) + ' 張']];
    const line = seg === 'dt' && rows.some(r => r.dr != null) ? [{ name: '當沖率', data: rows.map(r => r.dr), color: CH.amber }]
      : seg === 'sl' && rows.some(r => r.slb != null) ? [{ name: '借券賣出餘額', data: rows.map(r => r.slb), color: CH.amber }] : [];
    const lg = line.length ? legend([[seg === 'dt' ? '當沖張數（左軸）' : '借券賣出（張，左軸）', CH.violet], [seg === 'dt' ? '當沖率（%，右軸）' : '借券賣出餘額（張，右軸）', CH.amber, 1]]) : '';
    body.innerHTML = segBar('margin', SEG, seg) + chartBox(kpi(k) + lg) + tbl + `<div class="mbfoot">券資比＝融券餘額 ÷ 融資餘額。${srcTxt}</div>`;
    const signedSeg = seg === 'm' || seg === 's';
    const key = { m: 'mc', s: 'sc', dt: 'dt', sl: 'sl' }[seg];
    const draw = () => barChart({ x: rows.map(r => md(r.d)), full: rows.map(r => r.d),
      bars: [{ name: nm + (signedSeg ? '增減' : ''), data: rows.map(r => r[key] == null ? null : r[key]), color: signedSeg ? null : CH.violet }], lines: line,
      ytip: (v) => (signedSeg ? sInt(v) : int(v)) + ' 張',
      y2fmt: seg === 'dt' ? ((v) => Math.round(v) + '%') : undefined, y2tip: seg === 'dt' ? ((v) => (+v).toFixed(1) + '%') : ((v) => int(v) + ' 張') });
    wireSeg(body, 'margin'); wireFold(body, draw); draw();
  }

  /* ---- 營收：月走勢｜年度走勢（照截圖：當月＋去年同期並排柱，MoM、YoY 兩條線，左軸百萬、右軸 %）----
     revenue.monthly 每列＝[年月, 營收(元), YoY%, MoM%, 累計, 累計 YoY%, 去年同月營收（finance-quant 補的第 7 欄，有就直接用）]；revenue.yearly＝[{year, months, revenue, by_month}] */
  /* 2026-10-09 手機與桌機同步：比率線一律不用紅／綠（本站紅＝漲、綠＝跌，紅色的 YoY 線會被讀成「在漲」）。
     顏色照桌機同類圖：營收 YoY＝琥珀（industry.js 月營收圖 #ffb454）、淨利率＝紫（獲利圖 #8b7bff）、殖利率＝青（股利圖 CH.cyan）。*/
  function skRev(pg, body) {
    const rv = pg.revenue || {}, mo = rv.monthly || [];
    if (!mo.length) { body.innerHTML = empty('尚無月營收資料'); return; }
    const A = skApp(), CH = A.CH;
    const SEG = [['m', '月走勢'], ['y', '年度走勢']];
    const seg = skSeg('rev', 'm') === 'y' ? 'y' : 'm';
    const mil = (v) => v == null ? null : v / 1e6;
    const byYm = new Map(mo.map(r => [r[0], r]));
    const prevYm = (ym) => (+ym.slice(0, 4) - 1) + ym.slice(4);
    const lastY = CH.cyan, prevC = light() ? '#a9c8e8' : '#c9e6ff';
    if (seg === 'm') {
      const X = mo.slice(-12).map(r => ({ ym: r[0], v: mil(r[1]), yoy: r[2], mom: r[3], ly: r[6] != null ? mil(r[6]) : byYm.has(prevYm(r[0])) ? mil(byYm.get(prevYm(r[0]))[1]) : (r[1] != null && r[2] != null && r[2] > -100 ? mil(r[1] / (1 + r[2] / 100)) : null) }));
      const last = X[X.length - 1];
      const rows = mo.slice(-36).reverse();
      body.innerHTML = segBar('rev', SEG, seg)
        + chartBox(kpi([[`${last.ym.replace('-', '/')} 營收`, int(last.v) + ' 百萬'], ['YoY', sFix(last.yoy, 1) + '%', uc(last.yoy)], ['MoM', sFix(last.mom, 1) + '%', uc(last.mom)]])
          + legend([['當月', lastY], ['去年同期', prevC], ['MoM(%)', CH.violet, 1], ['YoY(%)', CH.amber, 1]]))
        + table([{ h: '年/月', f: r => [r[0].replace('-', '/')] }, { h: '月營收（百萬）', f: r => [r[1] == null ? '—' : (r[1] / 1e6).toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 })] },
          { h: 'YoY（%）', f: r => [sFix(r[2], 2), uc(r[2])] }, { h: 'MoM（%）', f: r => [sFix(r[3], 2), uc(r[3])] }], rows, -1)
        + `<div class="mbfoot">圖：近 12 個月；表：近 ${rows.length} 個月。</div>`;
      const draw = () => barChart({ x: X.map(r => r.ym.slice(2).replace('-', '/')), full: X.map(r => r.ym),
        bars: [{ name: '當月', data: X.map(r => r.v == null ? null : Math.round(r.v)), color: lastY }, { name: '去年同期', data: X.map(r => r.ly == null ? null : Math.round(r.ly)), color: prevC }],
        lines: [{ name: 'MoM(%)', data: X.map(r => r.mom), color: CH.violet }, { name: 'YoY(%)', data: X.map(r => r.yoy), color: CH.amber }],
        yfmt: (v) => { const a = Math.abs(v); return a >= 1e4 ? (v / 1e3).toFixed(0) + 'k' : String(Math.round(v)); }, ytip: (v) => int(v) + ' 百萬', y2fmt: (v) => Math.round(v) + '%', y2tip: (v) => sFix(v, 1) + '%' });
      wireSeg(body, 'rev'); wireFold(body, draw); draw();
    } else {
      const ys = (rv.yearly || []).filter(y => y.revenue != null);
      if (!ys.length) { body.innerHTML = segBar('rev', SEG, seg) + empty('尚無年度營收資料'); wireSeg(body, 'rev'); return; }
      /* 年增率用「同月份」比：今年只到 8 月就跟去年 1～8 月比，不跟去年全年比（不然每年年中都會看起來大衰退）*/
      const Y = ys.map((y, i) => { const p = ys.find(z => z.year === y.year - 1);
        let base = null;
        if (p && p.by_month && y.by_month) { const ks = Object.keys(y.by_month); const s = ks.reduce((a, k) => a + (p.by_month[k] || 0), 0); if (ks.every(k => p.by_month[k] != null)) base = s; }
        else if (p && p.months === 12 && y.months === 12) base = p.revenue;
        return { y: y.year, m: y.months, v: mil(y.revenue), yoy: base ? (y.revenue / base - 1) * 100 : null }; });
      const last = Y[Y.length - 1];
      body.innerHTML = segBar('rev', SEG, seg)
        + chartBox(kpi([[`${last.y}${last.m < 12 ? `（1–${last.m} 月）` : ''}`, int(last.v) + ' 百萬'], ['同期 YoY', sFix(last.yoy, 1) + '%', uc(last.yoy)]])
          + legend([['年營收', lastY], ['YoY(%)，同月份比', CH.amber, 1]]))
        + table([{ h: '年', f: r => [r.y + (r.m < 12 ? `<small>（${r.m} 個月）</small>` : '')] }, { h: '營收（百萬）', f: r => [int(r.v)] }, { h: 'YoY（%）', f: r => [sFix(r.yoy, 2), uc(r.yoy)] }], Y.slice().reverse(), -1)
        + '<div class="mbfoot">未滿 12 個月的年度，YoY 跟前一年同月份比。</div>';
      const draw = () => barChart({ x: Y.map(r => String(r.y)), bars: [{ name: '年營收', data: Y.map(r => r.v == null ? null : Math.round(r.v)), color: lastY }],
        lines: [{ name: 'YoY(%)', data: Y.map(r => r.yoy == null ? null : +r.yoy.toFixed(1)), color: CH.amber }],
        yfmt: (v) => { const a = Math.abs(v); return a >= 1e4 ? (v / 1e3).toFixed(0) + 'k' : String(Math.round(v)); }, ytip: (v) => int(v) + ' 百萬', y2fmt: (v) => Math.round(v) + '%', y2tip: (v) => sFix(v, 1) + '%' });
      wireSeg(body, 'rev'); wireFold(body, draw); draw();
    }
  }

  /* ---- 獲利（照截圖）：季 EPS 柱＋毛利率、淨利率兩條線（雙軸）；表＝季、毛利率、淨利率、EPS、累計 EPS ----
     profit.quarters 每列＝[季, 營收, 毛利率, 營益率, 淨利率, EPS, 累計 EPS, EPS 年增, 稅後淨利] */
  function skProfit(pg, body) {
    const q = ((pg.profit && pg.profit.quarters) || []);
    if (!q.some(r => r[5] != null)) { body.innerHTML = empty('尚無季報資料'); return; }
    const A = skApp(), CH = A.CH, f = pg.fundamental || {};
    const epsC = light() ? '#3b82c4' : '#4aa8f0';
    /* 年度分段：finance-quant 的 profit.yearly（四季單季加總，今年標「前 n 季」）到了才出現 */
    const yr = ((pg.profit && pg.profit.yearly) || []).filter(y => y.eps != null);
    const SEG = [['q', '季走勢']].concat(yr.length ? [['y', '年度走勢']] : []);
    const seg = SEG.some(x => x[0] === skSeg('profit', 'q')) ? skSeg('profit', 'q') : 'q';
    const p2 = (v) => v == null ? '—' : (+v).toFixed(2);
    const lg = legend([['EPS（元，左軸）', epsC], ['毛利率（%，右軸）', CH.cyan, 1], ['淨利率（%，右軸）', CH.violet, 1]]);
    const opt = { yfmt: (v) => (+v).toFixed(1), ytip: (v) => (+v).toFixed(2) + ' 元', y2fmt: (v) => Math.round(v) + '', y2tip: (v) => (+v).toFixed(2) + '%' };
    if (seg === 'q') {
      /* 缺季是整列 null（profit.gaps）：圖照樣留一格空位（看得出缺），關鍵數字取最後一個有 EPS 的季 */
      const X = q.slice(-20), last = X.filter(r => r[5] != null).pop();
      body.innerHTML = (SEG.length > 1 ? segBar('profit', SEG, seg) : '')
        + chartBox(kpi([[`${last[0]} EPS`, last[5] != null ? (+last[5]).toFixed(2) + ' 元' : '—', uc(last[5])], ['累計', last[6] != null ? (+last[6]).toFixed(2) + ' 元' : '—'],
          ['近四季', f.ttm_eps != null ? (+f.ttm_eps).toFixed(2) + ' 元' : '—'], ['毛利率', last[2] != null ? (+last[2]).toFixed(1) + '%' : '—']]) + lg)
        + table([{ h: '季', f: r => [r[0]] }, { h: '毛利率（%）', f: r => [p2(r[2])] }, { h: '淨利率（%）', f: r => [p2(r[4]), r[4] < 0 ? 'dn' : ''] },
          { h: 'EPS', f: r => [p2(r[5]), r[5] < 0 ? 'dn' : ''] }, { h: '累計 EPS', f: r => [p2(r[6]), r[6] < 0 ? 'dn' : ''] }], q.slice().reverse(), 3)
        + `<div class="mbfoot">圖：近 ${X.length} 季；累計 EPS＝當年度第 1 季起累加${(pg.profit.gaps || []).length ? `；缺季 ${(pg.profit.gaps || []).map(esc).join('、')}（財報沒有，圖上留空）` : ''}。</div>`;
      const draw = () => barChart({ x: X.map(r => r[0]), bars: [{ name: 'EPS', data: X.map(r => r[5]), color: epsC }],
        lines: [{ name: '毛利率', data: X.map(r => r[2]), color: CH.cyan }, { name: '淨利率', data: X.map(r => r[4]), color: CH.violet }], ...opt });
      wireSeg(body, 'profit'); wireFold(body, draw); draw();
    } else {
      const last = yr[yr.length - 1];
      const yl = (y) => String(y.year) + (y.partial ? `（前 ${y.quarters} 季）` : '');
      body.innerHTML = segBar('profit', SEG, seg)
        + chartBox(kpi([[`${yl(last)} EPS`, (+last.eps).toFixed(2) + ' 元', uc(last.eps)], ['毛利率', last.gm != null ? (+last.gm).toFixed(1) + '%' : '—'], ['淨利率', last.nm != null ? (+last.nm).toFixed(1) + '%' : '—']]) + lg)
        + table([{ h: '年', f: r => [r.year + (r.partial ? `<small>（${r.quarters} 季）</small>` : '')] }, { h: '毛利率（%）', f: r => [p2(r.gm)] }, { h: '淨利率（%）', f: r => [p2(r.nm), r.nm < 0 ? 'dn' : ''] },
          { h: 'EPS', f: r => [p2(r.eps), r.eps < 0 ? 'dn' : ''] }], yr.slice().reverse(), 3)
        + '<div class="mbfoot">年度＝四季單季加總；今年還沒滿四季的標「前 n 季」。</div>';
      const draw = () => barChart({ x: yr.map(r => String(r.year)), bars: [{ name: 'EPS', data: yr.map(r => r.eps), color: epsC }],
        lines: [{ name: '毛利率', data: yr.map(r => r.gm), color: CH.cyan }, { name: '淨利率', data: yr.map(r => r.nm), color: CH.violet }], ...opt });
      wireSeg(body, 'profit'); wireFold(body, draw); draw();
    }
  }

  /* ---- 財務：本益比｜營收與淨利（每季）----
     pe_history 每筆＝{period, ttm_eps, pe, pe_high, pe_low}（該季財報公布後那段期間的本益比與區間高低） */
  function skFin(pg, body) {
    const A = skApp(), CH = A.CH;
    const pe = (pg.pe_history || []).filter(r => r.pe != null);
    const q = ((pg.profit && pg.profit.quarters) || []);
    const SEG = [['pe', '本益比'], ['ni', '營收與淨利']];
    let seg = skSeg('fin', 'pe') === 'ni' ? 'ni' : 'pe';
    if (!pe.length && q.length) seg = 'ni';
    if (!pe.length && !q.length) { body.innerHTML = empty('尚無財報資料'); return; }
    const segs = SEG.filter(s => s[0] === 'pe' ? pe.length : q.length);
    const f = pg.fundamental || {};
    if (seg === 'pe') {
      const last = pe[pe.length - 1];
      body.innerHTML = (segs.length > 1 ? segBar('fin', segs, seg) : '')
        + chartBox(kpi([['目前本益比', f.pe ? (+f.pe).toFixed(1) : '—'], ['同族群中位', f.group_median != null ? (+f.group_median).toFixed(1) : '—'], ['股價淨值比', f.pb != null ? (+f.pb).toFixed(2) : '—'], ['近四季 EPS', f.ttm_eps != null ? (+f.ttm_eps).toFixed(2) : '—']])
          + legend([['本益比（期間平均）', CH.cyan, 1], ['期間最高', CH.up, 1], ['期間最低', CH.down, 1]]))
        + table([{ h: '財報季', f: r => [r.period] }, { h: '近四季 EPS', f: r => [r.ttm_eps == null ? '—' : (+r.ttm_eps).toFixed(2), r.ttm_eps < 0 ? 'dn' : ''] },
          { h: '本益比', f: r => [(+r.pe).toFixed(1)] }, { h: '高', f: r => [r.pe_high == null ? '—' : (+r.pe_high).toFixed(1)] }, { h: '低', f: r => [r.pe_low == null ? '—' : (+r.pe_low).toFixed(1)] }], pe.slice().reverse(), 2)
        + `<div class="mbfoot">每一季＝該季財報公布後到下一季公布前這段期間的本益比（股價 ÷ 近四季 EPS）。</div>`;
      const draw = () => barChart({ x: pe.map(r => r.period), linesOnly: true, bars: [], scale: true,
        lines: [{ name: '本益比', data: pe.map(r => r.pe), color: CH.cyan, left: true }, { name: '最高', data: pe.map(r => r.pe_high), color: CH.up, left: true }, { name: '最低', data: pe.map(r => r.pe_low), color: CH.down, left: true }],
        yfmt: (v) => Math.round(v) + '', ytip: (v) => (+v).toFixed(1) + ' 倍' });
      wireSeg(body, 'fin'); wireFold(body, draw); draw();
    } else {
      const X = q.slice(-12), last = X[X.length - 1];
      const revC = light() ? '#3b82c4' : '#4aa8f0';
      body.innerHTML = (segs.length > 1 ? segBar('fin', segs, seg) : '')
        + chartBox(kpi([[`${last[0]} 營收`, last[1] != null ? (last[1] / 1e8).toFixed(1) + ' 億' : '—'], ['稅後淨利', last[8] != null ? (last[8] / 1e8).toFixed(1) + ' 億' : '—', uc(last[8])], ['營益率', last[3] != null ? (+last[3]).toFixed(1) + '%' : '—'], ['ROE', f.roe != null ? (+f.roe).toFixed(1) + '%' : '—']])
          + legend([['營收（億，左軸）', revC], ['稅後淨利（億，右軸）', CH.amber, 1]]))
        + table([{ h: '季', f: r => [r[0]] }, { h: '營收（億）', f: r => [r[1] == null ? '—' : (r[1] / 1e8).toFixed(1)] }, { h: '淨利（億）', f: r => [r[8] == null ? '—' : (r[8] / 1e8).toFixed(1), r[8] < 0 ? 'dn' : ''] },
          { h: '營益率（%）', f: r => [r[3] == null ? '—' : (+r[3]).toFixed(1), r[3] < 0 ? 'dn' : ''] }], q.slice(-16).reverse(), 1)
        + '<div class="mbfoot">圖：近 12 季；表：近 16 季。</div>';
      const draw = () => barChart({ x: X.map(r => r[0].slice(2)), full: X.map(r => r[0]), bars: [{ name: '營收', data: X.map(r => r[1] == null ? null : +(r[1] / 1e8).toFixed(1)), color: revC }],
        lines: [{ name: '稅後淨利', data: X.map(r => r[8] == null ? null : +(r[8] / 1e8).toFixed(1)), color: CH.amber }],
        yfmt: (v) => Math.round(v) + '', ytip: (v) => (+v).toFixed(1) + ' 億', y2fmt: (v) => Math.round(v) + '', y2tip: (v) => (+v).toFixed(1) + ' 億' });
      wireSeg(body, 'fin'); wireFold(body, draw); draw();
    }
  }

  /* ---- 基本資料：一列一項（名稱在左、值在右），族群／題材可以點 ---- */
  function skBasic(pg, body) {
    const b = pg.basics || {}, f = pg.fundamental || {}, m = pg.meta || {}, L = window.Link || {}, A = skApp();
    const cid = L.gchain && L.gchain[m.group_id];
    const lk = (href, txt) => `<a href="${href}">${esc(txt)}</a>`;
    const rows = [['公司全名', esc(b.full_name || m.name || '—')], ['市場', esc(({ TWSE: '上市', TPEX: '上櫃' })[b.market || m.market] || b.market || '—')],
      ['產業別', esc(b.industry || '—')], ['上市日', esc(b.listed_date || '—')], ['股本', b.capital_billion != null ? b.capital_billion + ' 億' : '—'],
      ['董事長', esc(b.chairman || '—')], ['市值', f.market_cap != null ? A.fmt.yi(f.market_cap) : '—'],
      ['股價淨值比', f.pb != null ? (+f.pb).toFixed(2) : '—'], ['股價營收比', f.ps != null ? (+f.ps).toFixed(2) : '—'],
      ['產業鏈', cid && L.chains && L.chains[cid] ? lk('#industry/' + cid, L.chains[cid]) : '—'],
      ['族群', (m.groups || []).map(gn => lk('#industry/group/' + encodeURIComponent((L.gid && L.gid[gn]) || m.group_id), gn)).join('、') || '—'],
      ['題材', ((L.ctheme && L.ctheme[m.code]) || []).map(t => lk('#heatmap/theme/' + encodeURIComponent(t.id), t.name)).join('、') || '—'],
      ['網站', b.website ? `<a href="${esc(/^https?:/i.test(b.website) ? b.website : 'https://' + b.website)}" target="_blank" rel="noopener">${esc(b.website)}</a>` : '—']];
    body.innerHTML = `<dl class="mbkv">${rows.map(r => `<dt>${r[0]}</dt><dd>${r[1]}</dd>`).join('')}</dl>`;
  }

  /* ---- 除權息：全部｜現金股利｜股票股利（紀念品、股息再投入不做）----
     年度＝除權息日所在的年（dividends.by_year）；殖利率＝現金股利 ÷ 除息前一日收盤（dividends.results 的 before_price，原始價）。
     finance-quant 若補了每年的 yield 欄位就改用它（by_year[i].yield）。每列點一下展開當年每一次除權息的明細。
     ★ 2026-09-28（Andy：「股利政策&股利公告移除」，跟桌機 tabDividend 同一批）：
       改前第一段叫「股利政策」、表是所屬期間（2025H2…）＋底下一行「股利政策表＝所屬期間…」的說明 →
       改後第一段叫「全部」、表一律是年度表（年度＋點開每一次明細），所屬期間表與那行說明拿掉。後端 by_period 照舊產出。*/
  function skDiv(pg, body) {
    const A = skApp(), CH = A.CH, dv = pg.dividends || {};
    const by = (dv.by_year || []).filter(y => y.n > 0 || y.cash > 0 || y.stock > 0);
    const res = new Map((dv.results || []).map(r => [String(r.date).slice(0, 10), r]));
    const up = dv.upcoming || [];
    if (!by.length && !up.length) { body.innerHTML = empty('這一檔近年沒有除權息紀錄。'); return; }
    const Y = by.map(y => {
      const it = y.items || [];
      const xi = it.find(x => x.kind === '息'), qi = it.find(x => x.kind === '權');
      let yl = y.cash_yield != null ? +y.cash_yield : y.yield != null ? +y.yield : null;
      if (yl == null && y.cash > 0) { const s = it.filter(x => x.kind === '息' && x.cash > 0).reduce((a, x) => { const r = res.get(String(x.date).slice(0, 10)); return r && r.before_price ? a + x.cash / r.before_price * 100 : a; }, 0); yl = s || null; }
      return { y: y.year, cash: y.cash || 0, stock: y.stock || 0, xd: xi ? xi.date : null, qd: qi ? qi.date : null, yl, part: y.partial, it };
    });
    const SEG = [['all', '全部'], ['cash', '現金股利'], ['stock', '股票股利']];
    const seg = SEG.some(s => s[0] === skSeg('div', 'all')) ? skSeg('div', 'all') : 'all';
    const cashC = light() ? '#3b82c4' : '#4aa8f0', stockC = CH.amber;
    const last = Y[Y.length - 1];
    const hasYl = Y.some(r => r.yl != null);
    const upTxt = up.length ? up.slice(0, 2).map(u => `${esc(u.period || '')} ${u.kind === 'stock' ? '股票' : '現金'} ${(+u.amount || 0).toFixed(2)} 元（${u.ex_date ? esc(u.ex_date) + ' 除' + (u.kind === 'stock' ? '權' : '息') : '除權息日未定'}）`).join('；') : '';
    const k = [['近四次現金股利', dv.cash_ttm != null ? (+dv.cash_ttm).toFixed(2) + ' 元' : '—'], ['現價殖利率', dv.yield_ttm != null ? (+dv.yield_ttm).toFixed(2) + '%' : '—']];
    const lg = seg === 'all' ? [['現金股利', cashC], ['股票股利', stockC]] : seg === 'cash' ? [['現金股利', cashC]] : [['股票股利', stockC]];
    if (hasYl && seg !== 'stock') lg.push(['殖利率（%，右軸）', CH.cyan, 1]);
    body.innerHTML = segBar('div', SEG, seg)
      + '<div class="mbwarn">＊除權息資訊以公開資訊觀測站公告為主＊</div>'
      + (upTxt ? `<div class="mbfoot" style="margin-top:0">已公告、尚未除權息：${upTxt}</div>` : '')
      + chartBox(kpi(k) + legend(lg))
      + (`<div class="mbtblwrap"><table class="mbtbl mbdiv"><thead><tr><th>年度</th><th>除權日<br>除息日</th><th class="${seg !== 'all' ? 'sel' : ''}">股票股利<br>現金股利</th>${hasYl ? '<th>殖利率</th>' : ''}<th aria-label="展開"></th></tr></thead><tbody>`
      + Y.slice().reverse().map((r, i) => `<tr class="mbdrow" data-i="${i}" tabindex="0" aria-expanded="false"><td>${r.y}${r.part ? '<br><small>今年</small>' : ''}</td><td>${r.qd ? md(r.qd) : '—'}<br>${r.xd ? md(r.xd) : '—'}</td>`
        + `<td class="${seg !== 'all' ? 'sel' : ''}">${r.stock ? (+r.stock).toFixed(3) : '0'}<br>${r.cash ? (+r.cash).toFixed(3) : '0'}</td>${hasYl ? `<td>${r.yl != null ? r.yl.toFixed(2) + '%' : '—'}</td>` : ''}<td class="mbx">﹀</td></tr>`
        + `<tr class="mbdet" hidden><td colspan="${hasYl ? 5 : 4}">${r.it.map(x => { const rr = res.get(String(x.date).slice(0, 10));
          return `<div>${esc(x.date)} 除${esc(x.kind)}${x.period ? '（' + esc(x.period) + '）' : ''}：${x.kind === '息' ? '現金 ' + (x.cash != null ? (+x.cash).toFixed(3) : '—') + ' 元' : '股票 ' + (x.stock != null ? (+x.stock).toFixed(3) : '—') + ' 元'}`
            + (rr ? `；前一日收盤 ${rr.before_price ?? '—'}、參考價 ${rr.reference_price ?? '—'}${rr.fill_days != null ? `、${rr.fill_days} 天填${esc(x.kind)}` : '、尚未填' + esc(x.kind)}` : '') + '</div>'; }).join('') || '無明細'}</td></tr>`).join('')
      + '</tbody></table></div>')
      + `<div class="mbfoot">年度＝除權息日所在年；${hasYl ? '殖利率＝當年現金股利 ÷ 除息前一日收盤（原始價）。' : ''}</div>`;
    $$('.mbdrow', body).forEach(tr => { const tg = () => { const d = tr.nextElementSibling, o = d.hidden; d.hidden = !o; tr.setAttribute('aria-expanded', String(o)); tr.querySelector('.mbx').textContent = o ? '︿' : '﹀'; };
      tr.onclick = tg; tr.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tg(); } }; });
    const draw = () => barChart({ x: Y.map(r => String(r.y)),
      bars: (seg !== 'stock' ? [{ name: '現金股利', data: Y.map(r => r.cash), color: cashC }] : []).concat(seg !== 'cash' ? [{ name: '股票股利', data: Y.map(r => r.stock), color: stockC }] : []),
      lines: hasYl && seg !== 'stock' ? [{ name: '殖利率', data: Y.map(r => r.yl == null ? 0 : +r.yl.toFixed(2)), color: CH.cyan }] : [],
      yfmt: (v) => (+v).toFixed(1), ytip: (v) => (+v).toFixed(3) + ' 元', y2fmt: (v) => (+v).toFixed(0), y2tip: (v) => (+v).toFixed(2) + '%' });
    wireSeg(body, 'div'); wireFold(body, draw); draw();
  }

  /* ---- 新聞：一列＝日期時間＋兩行內的標題＋ ›；重大訊息點開看全文（抽屜），新聞點開原文（新分頁）---- */
  function skNews(pg, body) {
    const it = [].concat((pg.material_news || []).map((r, i) => ({ d: r.date, tm: r.time || '', t: r.subject, src: '重大訊息', mi: i })),
      (pg.news || []).map(r => ({ d: r.date, tm: r.time || '', t: r.title, src: ({ cnyes: '鉅亨', moneydj: 'MoneyDJ', yahoo: 'Yahoo' })[r.source] || r.source || '', url: r.url })))
      .filter(x => x.t).sort((a, b) => (b.d + b.tm).localeCompare(a.d + a.tm));
    if (!it.length) { body.innerHTML = empty('近期沒有這一檔的新聞與重大訊息。'); return; }
    body.innerHTML = `<ul class="mbnews">${it.map((x, i) => {
      const when = String(x.d || '').replace(/-/g, '/') + (x.tm ? ' ' + x.tm : '');
      const inner = `<span class="mbnt"><i class="num">${esc(when)}</i><em class="${x.mi != null ? 'mat' : ''}">${esc(x.src)}</em></span><b>${esc(x.t)}</b><s aria-hidden="true">›</s>`;
      return `<li>${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${inner}</a>` : `<button type="button" data-i="${i}">${inner}</button>`}</li>`; }).join('')}</ul>
      `;
    $('.mbnews', body).onclick = (e) => {
      const b = e.target.closest('button[data-i]'); if (!b) return;
      const x = it[+b.dataset.i], r = (pg.material_news || [])[x.mi]; if (!r) return;
      openSheet(`<div class="mshhead"><b>${esc(r.subject)}</b></div><div class="mbmat"><i>${esc(r.date)} ${esc(r.time || '')}　${esc(r.clause || '')}</i><pre>${esc(r.detail || '')}</pre></div>`, { kind: 'news' });
    };
  }

  /* ====================================================================== G 總覽最上方：指數三格＋觀察清單（2026-09-27）
     借券商 App 首頁截圖的兩塊（交易捷徑與廣告不做）：
       · 「指數」：加權／上櫃／台指近全三格一屏，往左滑還有費半、那斯達克、標普 500、美元兌台幣；下方「● ○ ○ 1 / 3」位置指示。
         數字讀 index_ohlc.json（加權 TSE、上櫃 OTC、台指期近月日盤 FUT／夜盤 FUT_N）與 intl.json；
         盤中若即時層（live.js）抓到加權（t00）就跟著換。台指近全＝日盤與夜盤兩段裡時間比較晚的那一段收盤，
         漲跌跟上一段比（券商 App 用前一日結算價當基準，資料湖沒有結算價，所以數字會跟 App 差一點）。
       · 「觀察清單」：localStorage `tw.watch`，**只存股票代號**（JSON 陣列），不存張數、成本 —— 這些不該離開使用者的裝置，
         也不需要。價格讀 stocks.json，盤中由 live.js 用 [data-live] 更新。加入：＋ 開抽屜搜尋；個股頁報價列的 ☆ 也能加。
         刪除：「編輯」→ 每格出現 ✕。
     只在 ≤640、#overview 插（#mbHome 是 #v-overview 的第一個子節點）；離開總覽或回桌機就拆掉。*/
  /* ★ 2026-09-27（Andy：「新增自選清單並且可以新增五個分頁」）：清單本體搬到 site/watchlists.js（window.TwWatch，最多五頁、登入後雲端同步）。
     這一列顯示「目前那一頁」，左邊一顆頁名鈕可以換頁；舊的 `tw.watch` 由 watchlists.js 第一次載入時搬進第 1 頁。
     下面三支保留原本的名字與介面，只是改成轉給 TwWatch —— 這一段其他程式幾乎不用動。*/
  const TW = () => window.TwWatch || null;
  const wGet = () => (TW() ? TW().codes() : []);
  const wSet = (a) => { if (TW()) TW().setCodes(a); };
  const wHas = (c) => !!(TW() && TW().has(c));
  const HM = { edit: false };
  function hmOn(v) {
    if (v !== 'overview') { hmOff(); return; }
    const view = document.getElementById('v-overview'); if (!view) return;
    let home = document.getElementById('mbHome');
    if (!home) {
      home = document.createElement('div'); home.id = 'mbHome'; home.className = 'mbhome';
      /* 高度預算（量過的）：總覽第①步的輪盤＋焦點條要留在第一屏（_uitest「手機v3」#1，390×844 與 360×780）。
         所以版面是兩條窄列 —— ① 指數列＋右邊一顆「＋ 觀察」（清單是空的時候只有這一列，約 56px）；
         ② 觀察清單有東西才出現（一列橫捲的小格，48px）。不放標題列與說明句（說明在「＋」抽屜裡）。*/
      home.innerHTML = `<div class="mbidxwrap"><div class="mbidxbox"><div class="mbidx" id="mbIdx" role="list" aria-label="指數（可左右滑）"></div>
          <div class="mbdots" id="mbIdxPos" aria-live="polite"></div></div>
          <button type="button" class="mbwadd" id="mbWAdd" aria-label="加入觀察清單"><b>＋</b><span>觀察</span></button></div>
        <div class="mbwatch" id="mbWatch" role="list" aria-label="觀察清單（可左右滑）" hidden></div>`;
      $('#mbWAdd', home).onclick = () => hmAddSheet();
      $('#mbWatch', home).onclick = (e) => {
        const x = e.target.closest('button[data-del]');
        if (x) { e.stopPropagation(); wSet(wGet().filter(c => c !== x.dataset.del)); return; }
        if (e.target.closest('#mbWEdit')) { HM.edit = !HM.edit; hmWatch(); return; }
        if (e.target.closest('#mbWTab')) { hmTabSheet(); return; }
        const t = e.target.closest('[data-go]'); if (t && !HM.edit) location.hash = '#stock/' + t.dataset.go;
      };
      $('#mbIdx', home).addEventListener('scroll', () => hmDots(), { passive: true });
    }
    if (view.firstElementChild !== home) view.insertBefore(home, view.firstChild);
    /* ★ 2026-09-28（Andy：總覽摘要卡列「在手機上放在指數列下面，可以橫向滑動，高度要小」）：
       摘要卡列（#hero，app.js renderOvSummary）緊貼在 #mbHome 後面 —— 在四步導覽列之前，不管切到第幾步都看得到。
       它不參與分段（modules.js 的 market.kpi 沒有 seg），高度由 index.html 的 @container ovsum (max-width:560px) 壓矮。*/
    const hmSum = () => { const h = document.getElementById('mbHome'), s = document.getElementById('hero');
      if (h && s && h.parentElement === view && h.nextElementSibling !== s) h.after(s); };
    hmSum();
    /* app.js 的分段導覽（.mspine／.mpager）是在路由畫完之後才插到 #v-overview 最前面，可能比這裡晚 ——
       盯著 #v-overview 的子節點，誰擠到前面就把 #mbHome 放回第一個（放回去那一次不會再觸發條件，不會迴圈）。
       摘要卡列同理：被擠開就放回 #mbHome 後面（條件成立才搬，搬完條件就不成立，不會迴圈）。*/
    if (!HM.mo && window.MutationObserver) {
      HM.mo = new MutationObserver(() => { const h = document.getElementById('mbHome'); if (h && h.parentElement === view && view.firstElementChild !== h) view.insertBefore(h, view.firstChild); hmSum(); });
      HM.mo.observe(view, { childList: true });
    }
    /* 第一次跑可能比 app.js 早（window.App 還沒好）：資料沒畫上去就等一下再試 */
    const A = skApp();
    if (!A || !A.load) { clearTimeout(HM.wait); HM.wait = setTimeout(() => { if (isM() && curView() === 'overview') hmOn('overview'); }, 300); return; }
    if (!document.querySelector('#mbIdx .mbit')) hmIdx(); else hmFit();
    hmWatch();
  }
  function hmOff() {
    const e = document.getElementById('mbHome'); if (e) e.remove(); HM.edit = false;
    clearTimeout(HM.wait); if (HM.mo) { HM.mo.disconnect(); HM.mo = null; }
  }
  hooks.push({ on: hmOn, off: hmOff });
  window.addEventListener('tw:watch', () => { if (document.getElementById('mbHome')) hmWatch(); if (document.getElementById('mbStar')) skStar(); });
  /* 同一個瀏覽器的另一個分頁改了觀察清單，這裡也跟著換 */
  /* （另一個分頁改清單的同步由 watchlists.js 的 storage 監聽負責，它會發 tw:watch）*/

  function hmTile(o) {
    const c = uc(o.chg);
    const f = (v) => (+v).toLocaleString('en-US', { minimumFractionDigits: o.dp, maximumFractionDigits: o.dp });
    return `<div class="mbit" role="listitem" data-id="${esc(o.id)}"><span class="mbitn">${esc(o.name)}${o.sub ? `<small>${esc(o.sub)}</small>` : ''}</span>
      <b class="num ${c}" data-k="v">${o.v == null ? '—' : f(o.v)}</b>
      <span class="num mbitc ${c}" data-k="c">${o.chg == null ? '—' : `<i>${(o.chg > 0 ? '▲' : o.chg < 0 ? '▼' : '') + f(Math.abs(o.chg))}</i>`}${o.pct == null ? '' : `<em>(${Math.abs(o.pct).toFixed(2)}%)</em>`}</span></div>`;
  }
  function hmIdx() {
    const A = skApp(); if (!A || !A.load) return;
    Promise.all([A.load('index_ohlc', { fallback: {} }), A.load('intl', { fallback: [] })]).then(([ix, it]) => {
      const box = document.getElementById('mbIdx'); if (!box) return;
      ix = ix || {};
      const mk = (id, name, arr, dp, sub) => {
        const a = (arr || []).filter(r => r && r[4] != null); if (!a.length) return null;
        const l = a[a.length - 1], p = a[a.length - 2] || null, chg = p ? l[4] - p[4] : null;
        return { id, name, sub: sub || '', v: l[4], chg, pct: p && p[4] ? chg / p[4] * 100 : null, dp, d: l[0] };
      };
      const tiles = [mk('TSE', '加權指數', ix.TSE, 2), mk('OTC', '上櫃指數', ix.OTC, 2)].filter(Boolean);
      /* 台指近全：夜盤那一列的日期是「下一個交易日」（期交所慣例），比日盤最後一天新就代表夜盤是最後一段 */
      const fd = (ix.FUT || []).filter(r => r[4] != null), fn = (ix.FUT_N || []).filter(r => r[4] != null);
      const ld = fd[fd.length - 1], ln = fn[fn.length - 1];
      if (ld) {
        const night = !!(ln && ln[0] > ld[0]);
        const cur = night ? ln : ld, ref = night ? ld : (fn.filter(r => r[0] <= ld[0]).pop() || fd[fd.length - 2]);
        const chg = ref ? cur[4] - ref[4] : null;
        tiles.push({ id: 'FUT', name: '台指近全', sub: night ? '夜盤' : '日盤', v: cur[4], chg, pct: ref && ref[4] ? chg / ref[4] * 100 : null, dp: 0, d: cur[0] });
      }
      const by = {};
      (it || []).forEach(r => { (by[r.symbol] = by[r.symbol] || []).push([r.date, null, null, null, r.close]); });
      [['^SOX', '費城半導體', 2], ['^IXIC', '那斯達克', 2], ['^GSPC', '標普 500', 2], ['TWD=X', '美元兌台幣', 3]]
        .forEach(([sym, nm, dp]) => { const t = mk(sym, nm, by[sym], dp); if (t) tiles.push(t); });
      box.innerHTML = tiles.map(hmTile).join('');
      box.dataset.n = String(tiles.length);
      hmDots(); hmLiveIdx(); hmFit();
    });
  }
  /* 窄螢幕（360 寬時一格約 90px）放不下「▼132.69 (0.28%)」：放不下的那一格只留漲跌幅（比點數重要），不截字 */
  function hmFit() {
    $$('#mbIdx .mbitc').forEach(e => { e.classList.remove('tight'); if (e.scrollWidth > e.clientWidth + 1) e.classList.add('tight'); });
  }
  function hmDots() {
    const box = document.getElementById('mbIdx'), pos = document.getElementById('mbIdxPos'); if (!box || !pos) return;
    const n = box.children.length; if (!n) { pos.innerHTML = ''; return; }
    const per = 3, pages = Math.ceil(n / per);
    const w = box.children[0].getBoundingClientRect().width || 1;
    const end = box.scrollLeft + box.clientWidth >= box.scrollWidth - 4;
    const c = end ? pages : Math.min(pages, Math.round(box.scrollLeft / (w * per)) + 1);
    pos.dataset.pos = String(c); pos.dataset.of = String(pages);
    pos.innerHTML = Array.from({ length: pages }, (_, i) => `<i class="${i + 1 === c ? 'on' : ''}"></i>`).join('') + `<span>${c} / ${pages}</span>`;
    box.classList.toggle('end', end);
  }
  /* 盤中：即時層抓到加權（t00）就換掉加權那一格（上櫃、台指期沒有同一條即時來源，照舊顯示收盤） */
  function hmLiveIdx() {
    const L = window.Live, q = L && L.quotes && L.quotes.t00, t = document.querySelector('#mbIdx .mbit[data-id="TSE"]');
    if (!q || !t || q.price == null) return;
    const v = t.querySelector('[data-k="v"]'), c = t.querySelector('[data-k="c"]');
    const pc = q.chgPct, cls = uc(pc), d = pc != null && pc > -100 ? q.price - q.price / (1 + pc / 100) : null;
    v.textContent = (+q.price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    c.innerHTML = d == null ? '—' : `<i>${d > 0 ? '▲' : d < 0 ? '▼' : ''}${Math.abs(d).toFixed(2)}</i><em>(${Math.abs(pc).toFixed(2)}%)</em>`;
    [v, c].forEach(e => { e.classList.remove('up', 'dn', 'fl'); e.classList.add(cls); });
    hmFit();
  }
  window.addEventListener('tw:quotes', () => { if (document.getElementById('mbIdx')) hmLiveIdx(); });

  function hmWatch() {
    const box = document.getElementById('mbWatch'); if (!box) return;
    const codes = wGet();
    const T = TW(), tabs = T ? T.tabs() : [], cur = T ? T.curTab() : { name: '' };
    const any = tabs.some(t => t.codes.length);
    if (!codes.length) HM.edit = false;
    /* 目前這一頁是空的、但別頁有東西：列照樣出現（才換得了頁），裡面寫一句提示 */
    box.hidden = !any;
    const tabBtn = any ? `<button type="button" class="mbwedit" id="mbWTab" aria-haspopup="dialog" title="換一頁自選清單">${esc(cur.name)} ▾</button>` : '';
    box.classList.toggle('editing', HM.edit);
    const A = skApp();
    const paint = (list) => {
      const by = new Map((list || []).map(r => [r.code, r]));
      /* ★ 2026-10-08 手機 v2：「編輯」從整列最後面搬到「自選頁 ▾」右邊 —— 放在最後面時它在橫捲列的畫面外（量到 left 882），
         要先橫拖才點得到，手機按鈕普查抓成「沒反應」；搬到前面一進來就看得到、一點就切換。 */
      const editBtn = codes.length ? `<button type="button" class="mbwedit" id="mbWEdit" aria-pressed="${HM.edit}">${HM.edit ? '完成' : '編輯'}</button>` : '';
      box.innerHTML = tabBtn + editBtn + (codes.length ? '' : '<span class="mbwn" style="align-self:center;padding:0 6px;color:var(--ink-2)">這頁還沒有股票</span>') + codes.map(c => {
        const r = by.get(c) || { code: c, name: c };
        const cls = r.chg_pct > 0 ? 'up' : r.chg_pct < 0 ? 'down' : 'flat';
        return `<div class="mbw" role="listitem" data-go="${esc(c)}" tabindex="0"><span class="mbwn">${esc(r.name || c)}</span>
          <b class="num" data-live="close" data-lc="${esc(c)}">${r.close == null || !A ? '—' : A.fmt.n(r.close)}</b>
          <small class="num">${esc(c)}</small><span class="num ${cls}" data-live="chg" data-lc="${esc(c)}">${r.chg_pct == null || !A ? '—' : A.fmt.pct(r.chg_pct, 2)}</span>
          ${HM.edit ? `<button type="button" class="mbwdel" data-del="${esc(c)}" aria-label="從觀察清單刪除 ${esc(r.name || c)}">✕</button>` : ''}</div>`;
      }).join('');
      box.querySelectorAll('.mbw').forEach(el => { el.onkeydown = (e) => { if (e.key === 'Enter' && !HM.edit) location.hash = '#stock/' + el.dataset.go; }; });
    };
    if (!any) { box.innerHTML = ''; return; }
    if (!A || !A.load) { paint([]); return; }
    A.load('stocks', { fallback: [] }).then(paint);
  }
  /* 換頁：列出所有自選頁（最多五頁），點一頁就換；「管理清單」打開完整面板（新增、改名、刪除、搬移）*/
  function hmTabSheet() {
    const T = TW(); if (!T) return;
    const cur = T.cur();
    const sh = openSheet(`<div class="mshhead"><b>換一頁自選清單</b></div><div class="mballgrid">${T.tabs().map(t =>
      `<button type="button" data-wt="${esc(t.id)}" class="${t.id === cur ? 'on' : ''}">${esc(t.name)}（${t.codes.length}）</button>`).join('')}</div>
      <div class="mballgrid" style="margin-top:8px"><button type="button" id="mbWManage">管理清單（新增／改名／刪除）</button></div>`, { kind: 'watchtabs' });
    const onPick = (e) => {
      const b = e.target.closest('button[data-wt]');
      if (b) { closeSheet(); T.setCur(b.dataset.wt); return; }
      if (e.target.closest('#mbWManage')) { closeSheet(); location.hash = '#watch'; }   // 2026-09-28：管理清單改到自選分頁（整頁）
    };
    sh.querySelectorAll('.mballgrid').forEach(g => { g.onclick = onPick; });
  }
  function hmAddSheet() {
    const A = skApp();
    const sh = openSheet(`<div class="mshhead"><b>加入觀察清單</b></div>
      <input type="search" id="mbWQ" class="mbwq" placeholder="代號或名稱，例如 2344 或 華邦電" autocomplete="off" enterkeyhint="search" aria-label="搜尋股票">
      <ul class="mbwres" id="mbWRes"></ul><div class="mbfoot">加進「${esc(TW() ? TW().curTab().name : '')}」。只存股票代號與清單名（不存張數、成本）。</div>`, { kind: 'watch' });
    const q = sh.querySelector('#mbWQ'), res = sh.querySelector('#mbWRes');
    let all = [];
    const run = () => {
      const k = q.value.trim().toUpperCase(), have = new Set(wGet());
      const hit = !k ? [] : all.filter(r => r.code.startsWith(k) || String(r.name || '').toUpperCase().includes(k)).slice(0, 8);
      // 2026-09-28：名稱旁的迷你走勢跟頂欄搜尋下拉同一套（app.js sparkSVG；sparks.json 還沒到時先留空位，到了再重畫一次）
      const spk = (c) => `<span class="spkw" data-spk="${esc(c)}">${A && A.sparkSVG ? A.sparkSVG(c) : ''}</span>`;
      res.innerHTML = hit.map(r => `<li><button type="button" data-c="${esc(r.code)}" ${have.has(r.code) ? 'disabled' : ''}><span class="num">${esc(r.code)}</span><b>${esc(r.name)}</b>${spk(r.code)}<em>${have.has(r.code) ? '已在清單' : '＋ 加入'}</em></button></li>`).join('')
        || (k ? '<li class="mbwnone">找不到這個代號或名稱</li>' : '');
    };
    res.onclick = (e) => { const b = e.target.closest('button[data-c]'); if (!b || b.disabled) return; const a = wGet(); a.push(b.dataset.c); wSet(a); run(); };
    q.oninput = run;
    (A && A.load ? A.load('stocks', { fallback: [] }) : Promise.resolve([])).then(l => { all = (l || []).filter(r => r && r.code); run(); });
    if (A && A.sparkLoad) A.sparkLoad().then(() => { if (q.value.trim()) run(); });
    setTimeout(() => { try { q.focus(); } catch (e) { /* 略 */ } }, 50);
  }

  window.M3 = {
    isM, openSheet, closeSheet, tileSheet, spread, overlaps, leaders, esc, LS, get NAV_H() { return navH(); },
    /** C／D 段登記：on(view) 在手機每次換頁跑；off() 回桌機時拆。*/
    hook(h) { hooks.push(h); if (isM() && document.body.classList.contains('m3on') && h.on) { try { h.on(curView()); } catch (e) { /* 略 */ } } },
    apply,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
})();
