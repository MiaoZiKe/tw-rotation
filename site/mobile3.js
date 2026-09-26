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
     C 總覽＋資金流向：大盤三張合一張、足跡輪盤新雷達＋焦點條、資金去向長條、法人長條、篩選抽屜
     D 剖析圖：在 diagrams.js 的 DG.mobileNums（這支只提供共用的抽屜與推開算法）
   ============================================================================ */
(function () {
  'use strict';
  const MAX = 640;
  const isM = () => window.innerWidth <= MAX;
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const LS = {
    get(k, d) { try { const v = localStorage.getItem('tw.m3.' + k); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('tw.m3.' + k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const NAV_H = 58;                         // 底部導覽一列的高度（CSS 同一個數字）

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
    pop.style.top = '0px';
    const h = Math.min(pop.scrollHeight, vh * 0.56);
    const below = r.bottom + 8;
    const top = (below + h <= vh - NAV_H - 8) ? below : Math.max(60, r.top - 8 - h);
    pop.style.top = Math.round(top) + 'px';
    pop.style.setProperty('--arrow-x', Math.round(r.left + r.width / 2 - 12) + 'px');
    pop.dataset.flip = top < r.top ? '1' : '0';
  }
  document.addEventListener('click', (e) => {
    const b = e.target && e.target.closest && e.target.closest('.howbtn[data-how]');
    if (b && isM()) placeHowPop(b);
  });

  /* ---- 編號層：互相擋到的編號往外推（最多 8 輪），推開的拉一條細引線回原點 ----
     2D、3D 共用（diagrams.js 的 DG.mobileNums 與 3D 那一支都用這一份）。回傳推完之後還重疊的對數。*/
  function spread(P, MIN) {
    for (let k = 0; k < 8; k++) {
      let moved = false;
      for (let a = 0; a < P.length; a++) for (let b = a + 1; b < P.length; b++) {
        const dx = P[b].x - P[a].x, dy = P[b].y - P[a].y, d = Math.hypot(dx, dy);
        if (d < MIN) {
          const push = (MIN - d) / 2 + 0.5, ux = d ? dx / d : (b % 2 ? 1 : -1), uy = d ? dy / d : 0;
          P[a].x -= ux * push; P[a].y -= uy * push; P[b].x += ux * push; P[b].y += uy * push; moved = true;
        }
      }
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
  const MORE_VIEWS = ['market', 'season', 'delivery'];
  function buildNav() {
    const tabs = document.getElementById('tabs');
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
      ${row('delivery', '✓', '交付清單', '<small>Andy 的需求與完成狀態</small>', v === 'delivery')}
      <div class="mgrp">工具</div>
      ${row('events', '▤', '今日事件', `<span class="n">${esc(evn)}</span>`)}
      ${row('theme', '☀', '切換成' + theme)}
      <div class="mver">網頁版號 <span class="mono">${esc(ver.trim() || '—')}</span></div>`, { kind: 'more' });
    sh.querySelectorAll('.mrow').forEach(r => r.onclick = () => {
      const m = r.dataset.m;
      closeSheet();
      if (MORE_VIEWS.includes(m)) { location.hash = '#' + m; return; }
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
    if (hp) { hp.classList.remove('mbubble'); hp.style.top = ''; }
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
  window.addEventListener('resize', () => {
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
  const load = (n) => cache[n] || (cache[n] = fetch('data/' + n + '.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null));
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
     座標換算跟 app.js renderRotation 的 pos() 同一條：兩軸各除以今天的最大偏離，外圈虛線＝今天偏離最大的族群。*/
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
      const k = u <= 1 ? u : 1 + TAIL * (u - 1) / span;
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
          S = Math.max(260, Math.min(S, Math.floor(window.innerHeight - NAV_H - (vtop + window.scrollY) - opts.fitBelow)));
          el._radarKey = key; el._radarS = S; el._radarTop = vtop + window.scrollY;
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
    let feet = true;
    try { if (localStorage.getItem('tw.rot.feet') === '0') feet = false; } catch (e) { /* 私密視窗：用預設（畫） */ }
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
    const lbl = shown.slice(0, 5).map(p => p.group_id); if (opts.sel && !lbl.includes(opts.sel)) lbl.push(opts.sel);
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
    el.innerHTML = `<div class="mradar" style="width:${S}px;height:${S}px"><svg viewBox="0 0 ${S} ${S}" width="${S}" height="${S}" role="img" aria-label="足跡輪盤">${g}</svg>`
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
    });
    $$('.mqb', el).forEach(b => b.addEventListener('click', () => opts.onQuad && opts.onQuad(b.dataset.quad)));
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

  /* ---- 總覽 ①足跡輪盤：雷達＋四角徽章＋焦點條 ---- */
  async function ovRadar() {
    const wrap = document.getElementById('rotClockMiniWrap');
    if (!wrap) return;
    const box = host(wrap, 'radar', '<div class="mrhost" id="mRadarOv"></div><div class="mfhost"></div>');
    if (box.dataset.done) return;
    const f = await load('flow_v3'); if (!f || !f.rrg || !isM()) return;
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    const all = f.rrg.points;
    let sel = null, quad = null;
    const draw = () => {
      if (!box.isConnected) return;
      const el = $('.mrhost', box);
      const r = radar(el, all, { sel, quad, max: 360, fitBelow: 65 + 44 + 16,
        onPick: (p) => { sel = p.group_id; draw(); },
        onQuad: (q) => { quad = quad === q ? null : q; draw(); } });
      if (!sel || (quad && !r.shown.some(x => x.group_id === sel))) sel = r.shown.length ? r.shown[0].group_id : sel;
      const p = all.find(x => x.group_id === sel);
      $('.mfhost', box).innerHTML = focusHtml(p, quad ? `只看「${ST[quad]}」：盤上 ${r.shown.length} 個（佔比前 16 名內）· 再點一次角落還原` : '');
      el.dataset.sel = sel || ''; el.dataset.quad = quad || '';
      if (!r.shown.some(x => x.group_id === sel)) { /* 選到的不在盤上（被角落篩掉）：重畫一次讓外圈跟上 */ }
    };
    box._redraw = draw;
    draw();
  }

  /* ---- 資金去向：桑基 → 可以點開的長條（台股 → 產業鏈 ▸ → 族群 ▸ → 個股），數字同一份 flow_v3.sankey ----
     「其他族群／其他產業」永遠排最後、灰色 —— 不然它會以 46% 佔第一名，看起來像主流。
     長條以「同一層、不含『其他』的最大值」為滿格。*/
  async function drill(box) {
    if (!box || box.dataset.done) return;
    if (!box.innerHTML) box.innerHTML = '<div class="msub">載入資金去向中…</div>';
    const f = await load('flow_v3'); if (!f || !f.sankey || !box.isConnected) return;
    box.dataset.done = '1';
    box.parentElement.classList.add('m3host');        // 資料到了才藏桌機那一份（ready）
    const Lk = f.sankey.links;
    const isOther = (n) => /^其他/.test(n);
    const kids = (name) => Lk.filter(l => l.source === name).sort((a, b) => (isOther(a.target) - isOther(b.target)) || (b.value - a.value));
    const total = kids('台股成交值').reduce((s, l) => s + l.value, 0) || 1;
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
    const draw = () => { box.innerHTML = `<div class="msub">${esc((f.date || '').slice(5))}　台股 → 產業鏈 → 族群 → 個股（點 ▸ 往下看）</div><ul class="mrank">${rows('台股成交值', 1)}</ul>`; box.dataset.open = open.size; };
    box.addEventListener('click', (e) => {
      const li = e.target.closest('li[data-k]'); if (!li) return;
      const k = li.dataset.k; open.has(k) ? open.delete(k) : open.add(k); draw();
    });
    draw();
  }

  /* ---- 資金流向「輪動」：雷達＋焦點條＋排行前 8（點列＝在輪盤上只亮它）＋篩選抽屜 ---- */
  async function flowRot() {
    const card = document.getElementById('flowRotCard'); if (!card) return;
    const box = host(card, 'rot', null, { full: '完整版（回放、即時、放大）' });
    if (box.dataset.done) return;
    /* 資料還沒回來之前先放標題與一行「載入中」—— 不然這一段在資料回來之前整片空白（慢網路下看起來像壞掉）*/
    if (!box.innerHTML) box.innerHTML = '<div class="mhead"><h3>資金輪動</h3></div><div class="msub">載入足跡輪盤與資金排行中…</div>';
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
    box.innerHTML = `<div class="mhead"><h3>資金輪動</h3><span class="sp"></span><button type="button" class="mfilt" id="mFlowFilt"></button>`
      + `<button class="howbtn pop" data-how="rot" type="button" aria-label="資金輪動怎麼看">?</button></div>`
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
      $('.mfhost', box).innerHTML = p ? focusHtml(p, quad ? `只看「${ST[quad]}」：盤上 ${r.shown.length} 個（佔比前 16 名內）· 再點一次角落還原` : '')
        : `<div class="mfocus"><span class="nm">${esc((gs.find(g => g.group_id === sel) || {}).group_name || '')}</span><span class="note">不在這個篩選的輪盤上</span></div>`;
      const mx = gs.length ? gs[0].share : 1;
      $('#mRankSub', box).textContent = `${per.label}　${(per.from || '').slice(5)}～${(per.to || '').slice(5)}`;
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
        <div class="mgrp">排行期間</div><div class="mchips" id="mShPer">${periods.map(p => `<button type="button" data-p="${esc(p.key)}" class="${pk === p.key ? 'on' : ''}">${esc(p.label)}</button>`).join('')}</div>
        <div class="mgrp">回放某一天、盤中即時、族群晶片：點卡片最下面的「完整版」</div>`, { kind: 'filter' });
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
    const box = host(card, 'inst', null, { full: '完整版（看幾天、截止日）', after: head });
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
      + `<div class="msub" id="mInstSub">${esc(src.dates[last])}　淨買超（張）</div><div class="minst" id="mInst"></div>`;
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
      pos.innerHTML = M3IDS.map((_, j) => `<i class="${j === i ? 'on' : ''}"></i>`).join('') + `<span>${i + 1} / ${M3IDS.length}　左右滑切換</span>`; }
    if (!quiet) LS.set('idx', id);
    setTimeout(() => window.dispatchEvent(new Event('resize')), 40);
  }
  function unMarket() {
    ['mM3Sw', 'mM3Pos'].forEach(x => { const e = document.getElementById(x); if (e) e.remove(); });
    const g = document.getElementById('m3Grid');
    if (g) { g.classList.remove('m3one'); delete g.dataset.cur; $$('.m3-card', g).forEach(c => c.classList.remove('mcur')); }
  }

  /* 主題一換，雷達的顏色（吃 CSS token）要重畫 */
  window.addEventListener('tw:theme', () => { $$('.m3keep').forEach(b => { if (b._redraw) setTimeout(b._redraw, 60); }); });

  let cWait = null;
  function cOn(v) {
    if (v === 'overview') {
      ovRadar();
      const ow = document.getElementById('ovFlowWrap');
      if (ow) drill(host(ow, 'drill'));
      if (document.getElementById('m3Grid')) market1();
      else { clearTimeout(cWait); cWait = setTimeout(() => cOn(curView()), 800); }
    }
    if (v === 'flow') {
      flowRot();
      const sc = document.getElementById('flowSankeyCard');
      if (sc) { const hd = sc.querySelector(':scope > .row'); if (hd) hd.classList.add('m3keep-h'); drill(host(sc, 'drill', null, { full: '完整版（分流圖、回放、即時）', after: hd })); }
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
      + `<div class="mchips"><a href="#industry/group/${encodeURIComponent(d.gid)}">族群 ›</a></div>`, { kind: 'tile' });
    sh.dataset.name = d.name;
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
  }
  function unSeasonCtl() {
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

  window.M3 = {
    isM, openSheet, closeSheet, tileSheet, spread, overlaps, leaders, esc, LS, NAV_H,
    /** C／D 段登記：on(view) 在手機每次換頁跑；off() 回桌機時拆。*/
    hook(h) { hooks.push(h); if (isM() && document.body.classList.contains('m3on') && h.on) { try { h.on(curView()); } catch (e) { /* 略 */ } } },
    apply,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
})();
