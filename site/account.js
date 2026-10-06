/* ============================================================================
   會員登入（Google）、使用統計、線上人數（Andy 2026-09-27）
   架構與取捨：DECISIONS #270 ／ 後端：workers/account-api/worker.js ／ 設定步驟：docs/login_setup.md ／
   事件清單：docs/account_analytics.md

   ★ 沒有設定就整個關掉：設定在 site/account_config.js（window.TW_ACCOUNT = { api: '…' }）。
     repo 裡那支永遠是空的；部署時由 GitHub Actions 依 repo Secret `ACCOUNT_API_URL` 覆寫（**網址不進版控**）。
     api 是空的 → 不出現登入鈕、不送任何統計、不連任何外部服務；自選清單照樣用（只存本機）。
     所以這支可以先部署上線，等 Andy 設好再生效。

   ★ 前端沒有任何第三方 SDK：登入是開一個小視窗到我們自己的 Worker（Worker 再轉 Google），
     其他全部是 fetch。Andy 公司網路擋 CDN 的問題碰不到；workers.dev 已經因為即時報價在用，連得到是已知事實。

   ★ 送出去的東西（跟隱私權政策 site/legal.js、登入前告知 noticeHTML() 必須一致）：
     · 心跳（每 60 秒，只在分頁看得到的時候）：一組這次載入頁面專用的隨機代碼（只在記憶體，關掉或重新整理就換一組）、
       現在在哪一頁、這段時間累積的「功能使用次數」、（登入者）權杖。不送 IP 以外的任何裝置資訊 —— IP 是連線本身帶的，Worker 不存。
     · 瀏覽器有開「請勿追蹤」（DNT）或「全球隱私控制」（GPC）→ 心跳與統計一律不送（登入與清單同步照常）。

   驗收：scripts/_uitest.py「會員雲端路徑」（本機跑真的 worker.js ＋ 假的 Google，見 workers/account-api/devserver.mjs）。
   ========================================================================== */
(function () {
  'use strict';
  /* 使用統計白名單 —— 跟 workers/account-api/worker.js 同一份，測試會比對（改一邊要改另一邊與文件）*/
  /* 跟 Worker 的 VIEWS 完全一致（18 頁、同順序；tests/account.test.mjs 三邊一致測試）。後七頁 2026-10-05（hourly）Worker 先補、這裡跟上 */
  const VIEWS = ['overview', 'flow', 'industry', 'heatmap', 'market', 'season', 'delivery', 'stock', 'legal', 'watch', 'other', 'etf', 'explore', 'earnings', 'events', 'support', 'pricing', 'notices'];
  const EVENTS = ['session', 'session_login', 'login', 'logout', 'search', 'watch_add', 'watch_remove', 'watch_tab_new', 'watch_panel', 'stock_tab', 'k_period', 'ai_tab', 'open_3d', 'zoom', 'how', 'theme_toggle', 'events_drawer', 'mtf', 'indicators', 'draw', 'm_seg'];
  const K_TOK = 'tw.acct.tok', K_USER = 'tw.acct.user';
  const BEAT_MS = 60 * 1000;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：這次瀏覽有效 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const ss = { get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* 略 */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const rnd = (n) => { const a = crypto.getRandomValues(new Uint8Array(n)); return btoa(String.fromCharCode(...a)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); };
  const noTrack = () => navigator.doNotTrack === '1' || window.doNotTrack === '1' || navigator.globalPrivacyControl === true;

  const S = { api: null, on: false, tok: ls.get(K_TOK), user: null, online: null, poll: 0, beatT: 0, q: {}, q2: {}, lastPv: '', sid: null };
  try { S.user = JSON.parse(ls.get(K_USER) || 'null'); } catch (e) { S.user = null; }
  if (!S.tok) S.user = null;

  // ------------------------------------------------------------------ API
  async function call(path, body) {
    if (!S.api) return null;
    try {
      const r = await fetch(S.api + path, { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify(Object.assign({}, body || {}, S.tok ? { t: S.tok } : {})), credentials: 'omit' });
      let j = {}; try { j = await r.json(); } catch (e) { j = {}; }
      j._s = r.status;
      /* 權杖失效（過期、帳號被刪、Worker 換了金鑰）→ 當作登出，不要一直拿壞的權杖打 */
      if (r.status === 401 && S.tok && path !== '/auth/redeem') setUser(null, null);
      return j;
    } catch (e) { return null; }       // 連不到（公司網路、離線）：呼叫端自己決定怎麼退
  }
  function setUser(user, tok) {
    const was = !!S.user;
    S.user = user || null;
    if (tok) { S.tok = tok; ls.set(K_TOK, tok); }
    if (!user) { S.tok = null; ls.del(K_TOK); ls.del(K_USER); } else ls.set(K_USER, JSON.stringify(user));
    paintBar();
    if (was !== !!user || user) window.dispatchEvent(new CustomEvent('tw:account', { detail: { user: S.user } }));
    /* 身分換了就馬上跳一次心跳：線上名單才會立刻從「訪客」變成名字（或反過來），不用等下一分鐘 */
    if (S.on && S.sid) { clearTimeout(S.beatT); S.beatT = setTimeout(beat, 200); }
  }

  // ------------------------------------------------------------------ 使用統計＋線上人數
  function viewOf(hash) {
    const h = String(hash || '').replace(/^#/, '').split('/');
    const head = h[0] || 'overview';
    if (head === 'admin') return null;                         // 管理頁本身不計
    if (['terms', 'privacy', 'disclaimer', 'leave'].includes(head)) return 'legal';
    if (head === 'themes') return 'heatmap';
    if (head === 'tasks') return 'delivery';
    return VIEWS.includes(head) ? head : 'other';
  }
  function bump(k) { S.q[k] = Math.min(50, (S.q[k] || 0) + 1); }
  function track(e) { if (S.on && !noTrack() && EVENTS.includes(e)) bump('ev:' + e); }
  window.TwTrack = track;
  /* ---- 細項事件（2026-10-05 admin-v2，docs/account_analytics.md「細項事件」）：[頁面, 元件, 細項]
     · 頁面＝目前這一頁（viewOf，跟頁面瀏覽同一份白名單）；管理頁本身不記。
     · 元件＝小寫英數與 . _ 的固定名字（play、quad、filter_group、tab.revenue、kp.60m…），全部寫死在這支或 app.js 的三個點位。
     · 細項＝族群名／股票代號／元件 id／象限名，**只從畫面上既有的選項取**；使用者打的字（搜尋框）一律不送，只記「有搜尋」。
     跟舊的計數一樣：每分鐘跟心跳一起送、DNT／GPC 開著就不送、不帶任何識別碼。*/
  const E2_BAD = /[\u0000-\u001f\u007f<>"'`\\@]/g;
  const cleanDet = (d) => String(d == null ? '' : d).replace(E2_BAD, '').replace(/\s+/g, ' ').trim().slice(0, 24);
  const stockCode = () => { const m = /^#stock\/([0-9A-Z]{4,6})\b/.exec(location.hash || ''); return m ? m[1] : ''; };
  function t2(comp, detail, page) {
    if (!S.on || noTrack()) return;
    const pg = page || viewOf(location.hash); if (!pg || !/^[a-z][a-z0-9_.]{0,31}$/.test(comp)) return;
    const k = pg + '\t' + comp + '\t' + cleanDet(detail);
    S.q2[k] = Math.min(50, (S.q2[k] || 0) + 1);
  }
  window.TwT = (comp, detail) => t2(comp, detail);
  function pv() {
    const v = viewOf(location.hash); if (!v) return;
    const key = v === 'stock' ? location.hash.split('/').slice(0, 2).join('/') : v;   // 換一檔股票算一次、同一頁內部切換不重算
    if (key === S.lastPv) return;
    S.lastPv = key;
    if (S.on && !noTrack()) bump('pv:' + v);
    if (v === 'stock' && stockCode()) t2('view', stockCode(), 'stock');     // 個股被觀看：細項＝代號
  }
  function takeQ() {
    const keys = Object.keys(S.q).slice(0, 40), ev = {};
    keys.forEach((k) => { ev[k] = S.q[k]; delete S.q[k]; });
    return ev;
  }
  function putBack(ev) { Object.entries(ev).forEach(([k, n]) => { S.q[k] = Math.min(50, (S.q[k] || 0) + n); }); }
  function takeQ2() {
    return Object.keys(S.q2).slice(0, 60).map((k) => { const n = S.q2[k]; delete S.q2[k]; const [p, c, d] = k.split('\t'); return [p, c, d, n]; });
  }
  function putBack2(e2) { e2.forEach(([p, c, d, n]) => { const k = p + '\t' + c + '\t' + d; S.q2[k] = Math.min(50, (S.q2[k] || 0) + n); }); }
  async function beat() {
    clearTimeout(S.beatT);
    if (!S.on || noTrack()) return;
    if (document.visibilityState === 'hidden') return;
    if (!ss.get('tw.sess')) { ss.set('tw.sess', '1'); bump('ev:session'); if (S.user) bump('ev:session_login'); }
    const ev = takeQ(), e2 = takeQ2();
    const j = await call('/v1/beat', Object.assign({ sid: S.sid, r: viewOf(location.hash) || 'other', ev }, e2.length ? { e2 } : {}));
    if (!j || j._s >= 500 || j._s === 429) { putBack(ev); putBack2(e2); }
    if (j && typeof j.n === 'number') { S.online = j.n; paintOnline(); } else if (j && j._s === 200) { S.online = null; paintOnline(); }
    S.beatT = setTimeout(beat, BEAT_MS);
  }
  /* 離開（關分頁、切到別的分頁、手機切到背景）：用 sendBeacon 送最後一次，順便把自己從線上名單刪掉 ——「離線即刪」。
     sendBeacon 送 text/plain：跨站時才不會多一次預檢請求。*/
  function leave() {
    if (!S.on || noTrack() || !navigator.sendBeacon) return;
    const e2 = takeQ2();
    const body = JSON.stringify(Object.assign({ sid: S.sid, leave: true, ev: takeQ() }, e2.length ? { e2 } : {}, S.tok ? { t: S.tok } : {}));
    try { navigator.sendBeacon(S.api + '/v1/beat', new Blob([body], { type: 'text/plain' })); } catch (e) { /* 略 */ }
  }
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') { clearTimeout(S.beatT); leave(); } else beat(); });
  window.addEventListener('pagehide', leave);
  /* 子分頁開啟次數（sub.<子頁>）：資金流向（rotation／sankey／inst）、熱力圖（industry／theme）、產業地圖（chains／chain／group）、市場明細（<頁籤>）。
     管理區的堆疊長條用它拆「這一頁被看的次數」；只記固定的路由片段，不記任何輸入 */
  function subOf(hash) {
    const h = String(hash || '').replace(/^#/, '').split('/'), head = h[0] || 'overview', rest = h[1] || '';
    if (head === 'flow') return ['flow', ['rotation', 'sankey', 'inst'].includes(rest) ? rest : 'rotation'];
    if (head === 'heatmap') return ['heatmap', rest === 'theme' ? 'theme' : 'industry'];
    if (head === 'themes') return ['heatmap', 'theme'];
    if (head === 'industry') return ['industry', !rest ? 'chains' : rest === 'group' ? 'group' : 'chain'];
    if (head === 'market') return ['market', /^[a-z0-9]{1,16}$/.test(rest) ? rest : 'updown'];
    return null;
  }
  let lastSub = '';
  function subPv() { const r = subOf(location.hash); const k = r ? r.join('/') : ''; if (k && k !== lastSub) t2('sub.' + r[1], '', r[0]); lastSub = k; }
  window.addEventListener('hashchange', () => { pv(); subPv(); });

  /* 功能使用事件：用委派監聽認按鈕，不去改每個功能自己的程式（那些檔案別的 agent 正在改）。
     事件的定義與「回答什麼問題」寫在 docs/account_analytics.md。*/
  const HOOKS = [
    ['#tfSeg button[data-tf]', 'k_period'],
    ['#stockTabs button[data-t], #mbTabs button[data-t]', 'stock_tab'],
    ['#skAi .aitab', 'ai_tab'],
    ['button[data-dm="3d"]', 'open_3d'],
    ['.howbtn', 'how'],
    ['#themeBtn, #mmTheme', 'theme_toggle'],
    ['#evToggle, #mmEvents', 'events_drawer'],
    ['#mtfBtn', 'mtf'],
    ['#indBtn', 'indicators'],
    ['#drawTgl', 'draw'],
    ['.mpager button, .mspine button', 'm_seg'],
    ['#sugg [data-c]', 'search'],
  ];
  /* 細項：舊事件在個股頁一律帶「哪一檔」；K 線週期／個股分頁再細到「哪一個」（元件 kp.60m、tab.revenue）*/
  const SUBKEY = { k_period: (el) => el.dataset.tf, stock_tab: (el) => el.dataset.t };
  const QUAD = { leading: '領先', improving: '改善', weakening: '轉弱', lagging: '落後' };
  const idOf = (el, sel) => { const c = el && el.closest(sel); return c ? c.id : ''; };
  /* 新增的細項點位（只有這幾個，清單同 docs/account_analytics.md）：都是委派監聽，不改功能本身的程式 */
  const DETAIL = [
    ['.pb.play', (el) => ['play', idOf(el, '[id]')]],                                           // 時間軸播放（rotBack＝資金輪動）
    ['.rotquads .rq', (el) => ['quad', QUAD[el.dataset.k] || el.dataset.k || '']],               // 輪盤四象限卡
    ['.rotdd[data-dd="chain"] .ddopt[data-c]', (el) => ['filter_chain', el.dataset.c ? (el.firstChild && el.firstChild.textContent || '').trim() : '全部']],
    ['.rotdd[data-dd="group"] .ddbtn', () => ['filter_group_open', '']],
    ['.rot-top10', () => ['filter_top10', '']],
    ['.rot-clear', () => ['filter_clear', '']],
    /* 2026-10-05 流量觀測分頁統計（Andy 新規格）補的點位：只記次數與固定選項名，不記身分。
       頁面鍵：etf／explore／support／events 已在 Worker 白名單（2026-10-05 hourly），細項直接記在各自的頁面下；舊資料（切換前）記在 other＋前綴，管理區兩種都認 */
    ['#etfCatSeg button', (el) => ['etf.cat', (el.textContent || '').replace(/[\s\d,（）()]+$/, '').trim(), 'etf']],                       // ETF 分類按鈕
    ['#wpNew, #wlNew', () => ['watch_tab_new', '', 'watch']],                                                  // 自選：新增分頁
    ['#wpList .spkw, #wlList .spkw', () => ['watch.chart', '', 'watch']],                                      // 自選：點走勢圖
    ['#wpList [data-tf], #wpList .tfseg button, #wpList .kseg button', () => ['watch.kline', '', 'watch']],    // 自選：展開圖裡切 K 線週期
    ['#supFab', () => ['support.fab', '', 'support']],                                                           // 客服：打開面板
    ['#supPanel .sptabs button[data-t]', (el) => ['support.tab', ({ faq: '常見問題', fb: '意見反饋', mail: '寄信' })[el.dataset.t] || '', 'support']],
    ['#supPanel .faq > button', (el) => ['support.faq', (el.textContent || '').trim().slice(0, 20), 'support']],
    ['#supPanel #fbSend', () => ['support.send', '', 'support']],
    ['#supPanel #supMail', () => ['support.mail', '', 'support']],
    ['#evList .ev a', () => ['events.link', '', 'events']],
    ['#drawBar .dtool', (el) => ['draw.tool', (el.getAttribute('title') || el.textContent || '').trim().split(/[（(]/)[0].slice(0, 20), 'stock']],   // K 線畫線工具（工具名取自按鈕提示）                                                    // 事件抽屜：點事件連結
  ];
  document.addEventListener('click', (e) => {
    if (!S.on || !e.target || !e.target.closest) return;
    /* 面板型的頁（今日事件抽屜、客服面板）不換網址，pv() 抓不到：打開那一下算一次瀏覽（關起來的那一下不算） */
    if (!noTrack()) {
      const evb = e.target.closest('#evToggle, #mmEvents'), tg = document.getElementById('evToggle'); if (evb && tg && tg.getAttribute('aria-expanded') !== 'true') bump('pv:events');
      const sfb = e.target.closest('#supFab'); if (sfb) { const pn = document.getElementById('supPanel'); if (!pn || pn.hidden) bump('pv:support'); }
    }
    for (const [sel, ev] of HOOKS) {
      const el = e.target.closest(sel); if (!el) continue;
      track(ev);
      const code = stockCode(), sub = SUBKEY[ev] ? SUBKEY[ev](el) : '';
      const comp = sub && /^[a-z0-9_]{1,16}$/i.test(sub) ? ev + '.' + String(sub).toLowerCase() : ev;
      t2(comp === 'stock_tab' || comp.startsWith('stock_tab.') ? comp.replace('stock_tab', 'tab') : comp.replace('k_period', 'kp'),
        code || (ev === 'how' ? idOf(el, '.card[id], section[id], [id]') : ''));
      break;
    }
    for (const [sel, fn] of DETAIL) { const el = e.target.closest(sel); if (el) { const [c, d, pgx] = fn(el); t2(c, d, pgx); break; } }
  }, true);
  /* 族群下拉勾選：只記「勾上」那一下，細項＝族群名（取自清單本身的文字，不是使用者輸入）*/
  document.addEventListener('change', (e) => {
    const inp = e.target; if (!S.on || !inp || !inp.matches || !inp.matches('.rotdd input[data-g]') || !inp.checked) return;
    const row = inp.closest('.ddopt'), nm = row && row.querySelector('.nm');
    t2('filter_group', nm ? nm.textContent : inp.dataset.g);
  }, true);
  /* 技術指標勾選（只記「勾上」那一下）：細項＝指標名稱（取自面板上的固定文字，如 MACD、RSI、布林通道），元件 ind */
  document.addEventListener('change', (e) => {
    const inp = e.target; if (!S.on || !inp || !inp.matches || !inp.matches('.ion[data-k]') || !inp.checked) return;
    const nm = inp.closest('label') && inp.closest('label').querySelector('.iname');
    t2('ind', nm ? nm.textContent : inp.dataset.k, 'stock');
  }, true);
  document.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target && e.target.id === 'q' && e.target.value.trim()) { track('search'); t2('search', ''); } }, true);
  function watchZoom() {
    const z = document.getElementById('zoomOv');
    if (!z || !window.MutationObserver) return;
    new MutationObserver(() => { if (!z.hidden) track('zoom'); }).observe(z, { attributes: true, attributeFilter: ['hidden'] });
  }

  // ------------------------------------------------------------------ 樣式
  function injectCSS() {
    if (document.getElementById('acctCss')) return;
    const s = document.createElement('style'); s.id = 'acctCss';
    s.textContent = `
.acctbar .aonline{display:inline-flex;align-items:center;gap:4px;font-size:12.5px;color:var(--ink-2);white-space:nowrap;background:none;border:0;padding:0 4px;cursor:default}
.acctbar .aonline i{width:8px;height:8px;border-radius:50%;background:#35d07f;box-shadow:0 0 0 3px rgba(53,208,127,.18)}
.acctbar .aonline[hidden]{display:none}
.acctbar .ame img,.acctbar .ame .ini{width:22px;height:22px;border-radius:50%;object-fit:cover;flex:none}
.acctbar .ame .ini{display:inline-grid;place-items:center;background:var(--violet);color:#fff;font-size:12px;font-weight:700}
.acctbar .ame .anm{max-width:7em;overflow:hidden;text-overflow:ellipsis}
.acctmenu{position:fixed;z-index:1250;min-width:220px;background:var(--panel);border:1px solid var(--line-2);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.35);padding:6px;color:var(--ink);font-size:14px}
.acctmenu[hidden]{display:none}
.acctmenu .mh{padding:8px 10px 10px;border-bottom:1px solid var(--line);margin-bottom:4px}
.acctmenu .mh b{display:block}.acctmenu .mh small{color:var(--ink-2);font-size:12.5px;word-break:break-all}
.acctmenu button,.acctmenu a{display:block;width:100%;text-align:left;padding:9px 10px;border:0;border-radius:8px;background:none;color:var(--ink);font-size:14px;cursor:pointer;text-decoration:none;box-sizing:border-box}
.acctmenu button:hover,.acctmenu a:hover{background:var(--row-hover)}
.acctmenu .danger{color:#ff6b7a}
.acctdlg{position:fixed;inset:0;z-index:1400;display:grid;place-items:center;background:rgba(3,6,14,.6);padding:16px}
.acctdlg[hidden]{display:none}
.acctdlg .box{width:min(520px,100%);max-height:calc(100vh - 32px);overflow:auto;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:14px;padding:18px 20px;font-size:14px;line-height:1.65;box-sizing:border-box}
.acctdlg h3{margin:0 0 8px;font-size:18px}
.acctdlg ul{margin:6px 0 10px;padding-left:1.2em}.acctdlg li{margin:3px 0}
.acctdlg .row2{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:12px}
.acctdlg .row2 button{height:38px;padding:0 16px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink);font-size:14px;cursor:pointer}
.acctdlg .row2 .pri{background:var(--cyan);border-color:var(--cyan);color:#04121a;font-weight:700}
.acctdlg .row2 .danger{background:#c9303f;border-color:#c9303f;color:#fff;font-weight:700}
.acctdlg .muted{color:var(--ink-2);font-size:13px}
.accttoast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:1500;background:var(--panel-3);color:var(--ink);border:1px solid var(--line-2);border-radius:10px;padding:10px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:calc(100vw - 32px)}
@media (max-width:820px){
  .acctbar .abtn{height:34px;padding:0 8px;font-size:13px}
  .acctbar .ame .anm,.acctbar .aonline span{display:none}
  .acctmenu{left:8px!important;right:8px;width:auto}
}`;
    document.head.appendChild(s);
  }
  function toast(msg) {
    let t = document.getElementById('acctToast');
    if (!t) { t = document.createElement('div'); t.id = 'acctToast'; t.className = 'accttoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 4200);
  }

  // ------------------------------------------------------------------ 頂欄：線上人數＋登入鈕／頭像
  function paintBar() {
    const bar = window.TwAcctBar ? window.TwAcctBar() : null; if (!bar) return;
    injectCSS();
    let on = document.getElementById('acctOnline');
    if (!on) { on = document.createElement('button'); on.type = 'button'; on.id = 'acctOnline'; on.className = 'aonline'; on.hidden = true; bar.appendChild(on); on.onclick = () => { if (S.user && S.user.admin) location.hash = '#admin/traffic'; }; }
    let b = document.getElementById('acctBtn');
    if (!S.on) { if (b) b.remove(); on.hidden = true; const r = document.getElementById('mmAcct'); if (r) r.remove(); return; }
    if (!b) { b = document.createElement('button'); b.type = 'button'; b.id = 'acctBtn'; b.className = 'abtn'; bar.appendChild(b); b.onclick = onBtn; }
    if (S.user) {
      const ini = esc((S.user.name || S.user.email || '?').trim().charAt(0).toUpperCase());
      b.className = 'abtn ame'; b.setAttribute('aria-haspopup', 'menu'); b.title = (S.user.name || '') + '（' + (S.user.email || '') + '）';
      b.innerHTML = (S.user.pic ? `<img src="${esc(S.user.pic)}" alt="" referrerpolicy="no-referrer">` : `<span class="ini">${ini}</span>`) + `<span class="anm">${esc(S.user.name || S.user.email || '')}</span>▾`;
      const img = b.querySelector('img');
      /* 大頭貼放在 googleusercontent.com：公司網路擋掉就換成名字第一個字，不留一個破圖 */
      if (img) img.onerror = () => { img.replaceWith(Object.assign(document.createElement('span'), { className: 'ini', textContent: ini })); };
    } else {
      b.className = 'abtn'; b.removeAttribute('aria-haspopup'); b.title = '用 Google 帳號登入（自選清單跨裝置同步）'; b.textContent = '登入';
    }
    paintOnline();
  }
  /* 手機（≤640）頂欄的帳號鈕收在「⋯」清單裡（見 watchlists.js moreRow），線上人數也寫在那一列 */
  function paintMoreRow() {
    if (!window.TwMoreRow || !S.on) return;
    const n = S.online != null ? `<small style="margin-left:auto;color:var(--ink-2);font-size:12.5px">${S.online} 人在線</small>` : '';
    if (S.user) window.TwMoreRow('mmAcct', '●', '帳號：' + esc(S.user.name || S.user.email || '') + n, () => openMenu(document.getElementById('moreBtn') || document.body));
    else window.TwMoreRow('mmAcct', '⇥', '用 Google 帳號登入' + n, () => openDlg('notice'));
  }
  function paintOnline() {
    paintMoreRow();
    const on = document.getElementById('acctOnline'); if (!on) return;
    if (!S.on || S.online == null) { on.hidden = true; return; }
    on.hidden = false; on.innerHTML = `<i></i>${S.online}<span> 人在線</span>`;
    on.title = `目前約 ${S.online} 人正在看這個網站（最近 2 分半有動作）` + (S.user && S.user.admin ? '・點一下看是誰' : '');
    on.style.cursor = S.user && S.user.admin ? 'pointer' : 'default';
  }
  function onBtn(e) {
    e.stopPropagation();
    if (!S.user) return openDlg('notice');
    const m = document.getElementById('acctMenu');
    if (m && !m.hidden) { m.hidden = true; return; }
    openMenu(e.currentTarget);
  }
  function openMenu(anchor) {
    let m = document.getElementById('acctMenu');
    if (!m) {
      m = document.createElement('div'); m.id = 'acctMenu'; m.className = 'acctmenu'; m.setAttribute('role', 'menu'); document.body.appendChild(m);
      m.addEventListener('click', (e) => {
        if (e.target.closest('.planbadge')) { m.hidden = true; return; }
        const a = e.target.closest('[data-a]'); if (!a) return;
        m.hidden = true;
        if (a.dataset.a === 'watch') location.hash = '#watch';   // 2026-09-28：自選改成整頁（#watch）
        if (a.dataset.a === 'admin') location.hash = '#admin/traffic';
        if (a.dataset.a === 'perm') location.hash = '#admin/perm';      // 2026-10-02 會員功能權限（DECISIONS #288）
        if (a.dataset.a === 'privacy') location.hash = '#privacy';
        if (a.dataset.a === 'pricing') location.hash = '#pricing';            // 2026-10-05 sub-v1
        if (a.dataset.a === 'feedback') location.hash = '#admin/feedback';
        if (a.dataset.a === 'notices') location.hash = '#admin/notices';
        if (a.dataset.a === 'delete') openDlg('delete');
        if (a.dataset.a === 'logout') logout();
      });
    }
    const u = S.user || {};
    /* 2026-10-05（sub-v1）頂部：頭像字母＋名字＋方案徽章（pricing.js 的 TwPlanBadge，點了到 #pricing）*/
    const ini = esc((u.name || u.email || '?').trim().charAt(0).toUpperCase());
    m.innerHTML = `<div class="mh mhx"><span class="av" aria-hidden="true">${ini}</span><span class="nm"><b>${esc(u.name || '')}</b>${window.TwPlanBadge ? window.TwPlanBadge() : ''}</span><small>${esc(u.email || '')}</small></div>`
      + `<button type="button" role="menuitem" data-a="watch">★ 自選清單</button>`
      + `<button type="button" role="menuitem" data-a="pricing">訂閱方案</button>`
      + (u.admin ? `<button type="button" role="menuitem" data-a="feedback">管理區：意見反饋與訂閱申請</button><button type="button" role="menuitem" data-a="notices">管理區：公告</button>` : '')
      + (u.admin ? `<button type="button" role="menuitem" data-a="admin">管理區：流量觀測與線上名單</button><button type="button" role="menuitem" data-a="perm">管理區：會員功能權限</button>` : '')
      + `<button type="button" role="menuitem" data-a="privacy">隱私權政策</button>`
      /* 10-05 Andy：選單拿掉「刪除我的資料」；刪除改由客服信箱申請（隱私權政策「您的權利」）*/
      + `<button type="button" role="menuitem" data-a="logout">登出</button>`;
    m.hidden = false;
    const r = anchor.getBoundingClientRect();
    m.style.top = (r.bottom + 6) + 'px';
    m.style.left = Math.max(8, Math.min(window.innerWidth - 236, r.right - 228)) + 'px';
  }
  document.addEventListener('pointerdown', (e) => {
    const m = document.getElementById('acctMenu');
    if (m && !m.hidden && !m.contains(e.target) && !e.target.closest('#acctBtn')) m.hidden = true;
  }, true);

  // ------------------------------------------------------------------ 登入前告知、等待、刪除確認
  /* 登入前告知（個資法第 8 條要告知的：蒐集者、目的、類別、期間／地區／對象／方式、權利、不提供的影響）。
     全文在隱私權政策（#privacy）；這裡是按下去之前一定看得到的摘要。改內容要跟 site/legal.js 的 privacyDoc() 一起改。*/
  function noticeHTML() {
    return `<h3>用 Google 帳號登入</h3>
      <p class="muted">登入是選用的：不登入也能使用全部功能，只是自選清單只存在這台裝置。</p>
      <ul>
        <li><b>我們會收到並保存</b>：你的 Google 顯示名稱、email、大頭貼網址。Google 帳號識別碼只存加密雜湊，不存原值。<b>拿不到你的密碼</b>，也不會讀取 Gmail、雲端硬碟或聯絡人（只要求 openid、email、profile 三項基本權限）。</li>
        <li><b>用途</b>：辨識你是誰、讓自選清單在不同裝置同步；網站管理者看得到會員名單，以及目前線上的登入者名稱與所在頁面。</li>
        <li><b>自選清單</b>只存股票代號與清單名稱，<b>不存張數、成本、損益</b>。</li>
        <li><b>功能權限</b>：網站管理者可以替你的 email 設定方案與可用的功能（例如付費方案）；刪除帳號時一起刪除。</li>
        <li><b>使用統計（所有訪客，不論是否登入）</b>：每天每一頁、每一項功能被使用的<b>次數</b>，不含身分、不存 IP，保留 13 個月。瀏覽器開了「請勿追蹤」就完全不送。</li>
        <li><b>線上狀態</b>：關掉分頁，或 3 分鐘沒有訊號，就刪除。</li>
        <li><b>保存期限</b>：會員資料保存到你刪除為止；連續 24 個月沒有使用會自動刪除。</li>
        <li><b>存放</b>：Cloudflare（Workers／Durable Objects）；登入經由 Google 驗證身分。</li>
        <li><b>刪除</b>：來信客服 kcq01010909@gmail.com 申請，十五日內刪除會員資料與雲端自選清單。</li>
      </ul>
      <p class="muted">詳見 <a href="#privacy" data-close>隱私權政策</a>。按下「用 Google 帳號登入」即表示你同意上述蒐集與利用。</p>
      <div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="acctGo">用 Google 帳號登入</button></div>`;
  }
  function openDlg(kind) {
    injectCSS();
    let d = document.getElementById('acctDlg');
    if (!d) {
      d = document.createElement('div'); d.id = 'acctDlg'; d.className = 'acctdlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => {
        if (e.target === d || e.target.closest('[data-close]')) { stopPoll(); d.hidden = true; return; }
        if (e.target.closest('#acctGo')) startLogin();
        if (e.target.closest('#acctDelYes')) deleteMe();
      });
      d.addEventListener('keydown', (e) => { if (e.key === 'Escape') { stopPoll(); d.hidden = true; } });
    }
    d.dataset.kind = kind;
    d.innerHTML = '<div class="box">' + (kind === 'notice' ? noticeHTML()
      : kind === 'wait' ? `<h3>等待 Google 登入完成…</h3><p>請在跳出來的視窗選擇帳號。完成後這裡會自動關閉。</p><p class="muted">沒看到視窗？可能被瀏覽器擋了跳出式視窗，請允許後再按一次「登入」。</p><div class="row2"><button type="button" data-close>取消</button></div>`
      : kind === 'delete' ? `<h3>刪除我的資料</h3><p>會立即刪除：你的會員資料（名稱、email、大頭貼網址）、雲端上的自選清單、線上狀態、管理者替你設定的功能權限。<b>無法復原。</b></p><p class="muted">使用統計只記「每天每一項的次數」，本來就沒有記是誰，所以沒有可以刪的個人部分。這台裝置上的本機清單不受影響。</p><div class="row2"><button type="button" data-close>取消</button><button type="button" class="danger" id="acctDelYes">確定刪除</button></div>`
      : '') + '</div>';
    d.hidden = false;
    const f = d.querySelector('.pri,.danger,button'); if (f) try { f.focus(); } catch (e) { /* 略 */ }
  }
  function closeDlg() { const d = document.getElementById('acctDlg'); if (d) d.hidden = true; }

  /* 登入：網站自己產生一次性的 n，開小視窗走 Worker → Google → Worker，完成後拿 n 去 /auth/redeem 換權杖。
     小視窗被擋（或在 PWA 裡開不出來）就改整頁跳轉，n 先存在 sessionStorage，回來時再換。*/
  function startLogin() {
    if (!S.api) return;
    const n = rnd(24);
    const ret = location.origin + location.pathname;
    const url = `${S.api}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ret)}`;
    let w = null;
    try { w = window.open(url, 'twlogin', 'popup,width=480,height=680'); } catch (e) { w = null; }
    if (!w) {
      ss.set('tw.acct.n', n);
      location.href = `${S.api}/auth/start?n=${n}&mode=redirect&ret=${encodeURIComponent(location.href)}`;
      return;
    }
    openDlg('wait');
    const t0 = Date.now();
    stopPoll();
    const tick = async () => {
      const j = await call('/auth/redeem', { n });
      if (j && j.tok && j.user) { stopPoll(); closeDlg(); setUser(j.user, j.tok); track('login'); toast('已登入：' + (j.user.name || j.user.email)); return; }
      if (j && j._s === 404) { stopPoll(); openDlg('notice'); toast('登入沒有完成，請再試一次'); return; }
      if (Date.now() - t0 > 180 * 1000) { stopPoll(); closeDlg(); toast('等太久了，登入已取消'); return; }
      S.poll = setTimeout(tick, 1200);
    };
    S.pollN = n;
    S.poll = setTimeout(tick, 1200);
  }
  function stopPoll() { clearTimeout(S.poll); S.poll = 0; S.pollN = null; }
  window.addEventListener('message', (e) => {
    if (!S.api || e.origin !== new URL(S.api).origin) return;
    const d = e.data || {};
    if (d.type === 'tw-login' && d.n && d.n === S.pollN) { clearTimeout(S.poll); S.poll = setTimeout(async () => {
      const j = await call('/auth/redeem', { n: d.n });
      if (j && j.tok && j.user) { stopPoll(); closeDlg(); setUser(j.user, j.tok); track('login'); toast('已登入：' + (j.user.name || j.user.email)); }
    }, 0); }
  });
  function logout() { track('logout'); setUser(null, null); toast('已登出。這台裝置上不會留下你的雲端清單。'); if ((location.hash || '').startsWith('#admin')) route('admin'); }
  async function deleteMe() {
    const j = await call('/v1/delete', {});
    if (j && j.deleted) { closeDlg(); setUser(null, null); toast('你的會員資料與雲端清單已經刪除'); }
    else toast('刪除沒有成功（' + (j ? j._s : '連不到伺服器') + '），請稍後再試');
  }

  // ------------------------------------------------------------------ 管理頁 #admin（內容在 admin.js，用到才載入）
  function ensureView() {
    let v = document.getElementById('v-admin');
    if (v) return v;
    const main = document.querySelector('main'); if (!main) return null;
    v = document.createElement('section'); v.className = 'view'; v.id = 'v-admin';
    main.insertBefore(v, document.getElementById('siteFoot') || null);
    return v;
  }
  let adminLoading = null;
  function loadAdmin() {
    if (window.TwAdmin) return Promise.resolve();
    if (adminLoading) return adminLoading;
    adminLoading = new Promise((res) => {
      const s = document.createElement('script');
      const m = document.querySelector('meta[name="tw:build"]');
      s.src = 'admin.js?v=' + encodeURIComponent((m && m.content) || 'dev');
      s.onload = () => res(); s.onerror = () => res();
      document.head.appendChild(s);
    });
    return adminLoading;
  }
  /* app.js 的 route() 問這裡：'admin' → 由本檔接手（app.js 關掉其他 view）；null → 不關本檔的事 */
  /* 2026-10-05（sub-v1）：#admin/feedback、#admin/notices 由 support.js／notices.js 自己畫（app.js 的 TwSubRoutes 先攔），
     這裡不要再把 admin.js 載進來、在藏起來的 #v-admin 裡多畫一份流量觀測（還會多打一支 /v1/admin/stats）。*/
  const subAdmin = () => /^#admin\/(feedback|notices)\b/.test(location.hash || '');
  function route(head) {
    if (head !== 'admin' || subAdmin()) return null;
    admKey = '';
    const v = ensureView(); if (!v) return null;
    if (!S.on) { v.innerHTML = '<div class="card" style="margin-top:16px"><h2>管理頁</h2><p class="muted">會員功能尚未設定</p></div>'; return 'admin'; }
    if (!S.user) { v.innerHTML = '<div class="card" style="margin-top:16px"><h2>管理頁</h2><p>這一頁只有管理者看得到，請先登入。</p><p><button type="button" class="btn" id="admLogin">登入</button></p></div>';
      v.querySelector('#admLogin').onclick = () => openDlg('notice'); return 'admin'; }
    if (!S.user.admin) { v.innerHTML = '<div class="card" style="margin-top:16px"><h2>管理頁</h2><p>這個帳號不是管理者，看不到使用統計與線上名單。</p></div>'; return 'admin'; }
    admKey = admKeyNow();
    v.innerHTML = '<div class="card" style="margin-top:16px"><p class="muted">載入管理頁…</p></div>';
    loadAdmin().then(() => { if ((location.hash || '').startsWith('#admin') && window.TwAdmin) window.TwAdmin.render(v, API); });
    return 'admin';
  }
  /* ★ 2026-10-05 修：以前任何一次 tw:account（開頁的 /v1/me 回來、心跳刷新身分）都會整頁重畫管理頁，
     #admin/perm 上撥到一半、還沒按「儲存」的開關會被默默清掉（實測：撥一個開關後派一次 tw:account，「1 項變更還沒儲存」就不見了）。
     身分沒變（同一個 email、同樣是不是管理者、同一個網址）就不重畫；登入／登出／換人照舊重畫。 */
  let admKey = '';
  const admKeyNow = () => (S.user ? S.user.email + '|' + !!S.user.admin : '-') + '|' + (location.hash || '');
  window.addEventListener('tw:account', () => {
    if (!(location.hash || '').startsWith('#admin') || !S.api) return;
    if (admKey && admKey === admKeyNow()) return;
    route('admin');
  });

  // ------------------------------------------------------------------ 啟動
  const API = {
    on: () => S.on, user: () => S.user, api: () => S.api, online: () => S.online,
    call, route, login: () => openDlg('notice'), logout, track,
    /* 給驗收腳本：現在排隊中的統計（還沒送出的）*/
    pending: () => Object.assign({}, S.q),
    flush: () => beat(),
  };
  window.TwAccount = API;

  async function boot() {
    injectCSS(); watchZoom();
    /* TW_ACCOUNT_OVERRIDE：驗收腳本用 add_init_script 注入本機 devserver 的網址（跟 legal.js 的 TW_LEGAL_OVERRIDE 同一個做法）*/
    const cfg = window.TW_ACCOUNT_OVERRIDE || window.TW_ACCOUNT || null;
    const api = cfg && typeof cfg.api === 'string' ? cfg.api.replace(/\/+$/, '') : '';
    /* 只接受 https（正式）或本機（驗收用的 devserver）—— 設定檔被改成奇怪的東西時寧可關掉 */
    if (!/^https:\/\/[a-z0-9.-]+(:\d+)?$/i.test(api) && !/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(api)) { S.on = false; paintBar(); return; }
    S.api = api; S.on = true;
    window.TW_ACCOUNT_ON = true;
    window.dispatchEvent(new Event('tw:account-config'));
    /* 線上用的代碼：每次載入頁面一組、只在記憶體。不放 sessionStorage —— 重新整理時舊頁面的「離開」會比新頁面的第一次心跳晚到，
       同一組代碼會把新頁面剛登記的在線紀錄刪掉（驗收實測抓到），換一組就不會互相踩到。*/
    S.sid = rnd(12);
    paintBar();
    pv();
    /* 整頁跳轉登入回來：拿 sessionStorage 的 n 去換權杖 */
    const n = ss.get('tw.acct.n');
    if (n) {
      ss.del('tw.acct.n');
      const j = await call('/auth/redeem', { n });
      if (j && j.tok && j.user) { setUser(j.user, j.tok); track('login'); toast('已登入：' + (j.user.name || j.user.email)); }
    } else if (S.tok) {
      const j = await call('/v1/me', {});
      if (j && j.user) setUser(j.user, j.tok || null);
      else if (j && j._s === 401) { /* call() 已經處理成登出 */ }
      else if (S.user) window.dispatchEvent(new CustomEvent('tw:account', { detail: { user: S.user } }));   // 連不到：先用快取
    }
    if ((location.hash || '').startsWith('#admin')) route('admin');
    clearTimeout(S.beatT); S.beatT = setTimeout(beat, 1500);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
