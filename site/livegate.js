/* livegate.js — 盤中即時功能只給管理者帳號（Andy 2026-10-06，DECISIONS #326）
 *
 * Andy 原話：「所有的即時功能，只有在我這帳號才會出現，其他帳號都隱藏」。
 *
 * 這支是**唯一的閘門**。全站所有「盤中即時」相關的東西都問它：
 *   · live.js：報價格子每 5 秒更新、卡片的「即時」開關（個股／自選／大盤三張圖）、頂欄即時狀態、
 *     Live.proxy()／taifexProxy()（不是管理者時回空字串 → 任何模組都打不到 quote-proxy／Deno／mis）
 *   · market3.js：大盤三張圖的分時檔、台指期日盤／夜盤、Yahoo 1 分線 —— 不是管理者時只畫資料湖的最近交易日（盤後版本）
 *   · livek.js：個股即時分 K／分時尾巴（不 attach、不輪詢）
 *   · industry.js：個股週期列不列 1分／5分／15分（那三個週期只有即時來源）；族群總覽的「即時」鈕
 *   · app.js：市場明細漲跌家數「盤後／⚡ 即時」、輪動時鐘與資金去向的「即時」鈕、總覽摘要卡右上角的即時開關
 * 規則：已登入、而且 Worker 回的使用者帶 admin:true（＝ADMIN_EMAILS 裡的人，就是 Andy）才算。
 * 訪客、註冊會員、付費會員一律不算 —— 不只藏按鈕，**連輪詢都不跑、不打任何報價端點**（省 Cloudflare／Deno 免費額度，也避開授權風險）。
 *
 * 做法（集中式）：
 *   ① <html> 上掛 class `live-on`（只有管理者有）。這支放在 <head>、比 <body> 先跑，所以訪客第一幀就看不到任何即時 UI，不會先閃一下再消失。
 *   ② 下面注入一小段 CSS：`html:not(.live-on)` 時把 `.livetg`（卡片即時開關）、`.livebtn`（族群模式的即時鈕）、
 *      `#liveState`、以及任何標了 `data-live-ui` 的節點整顆 display:none（不是 visibility，所以不留空位）。
 *      各模組自己也會在「不是管理者」時乾脆不掛那顆鈕 —— CSS 是第二道保險（例如有人新增了一顆 .livebtn 卻忘了問閘門）。
 *   ③ 各模組開頭問 `TwLive.allowed()`；live.js 的 proxy() 不給網址是第三道（網路層）保險。
 *   ④ 登入狀態改變（account.js 的 tw:account）時重新評估；結果變了就**整頁重新載入**。
 *      為什麼不原地切換：關掉要把四種族群即時模式、大盤卡的計時器、已經被改寫的報價格子全部退回去，
 *      各模組各寫一套很容易漏一個（漏了就是訪客畫面還在打報價端點）；重新載入保證乾淨。只有「管理者登入／登出」那一下會發生，一般人永遠不會遇到。
 *
 * 判斷依據：先看 account.js 的 TwAccount.user()；account.js 還沒載入時（這支在 <head>，它在 <body> 尾端）
 * 直接讀同一份快取（localStorage tw.acct.tok＋tw.acct.user，account.js 第 39～40 行同樣的規則：沒有權杖就不算登入）。
 * 開頁時用快取先決定（Andy 不用等 Worker 回應就看得到即時）；/v1/me 回來說他不是管理者了（或權杖失效被登出）→ tw:account → 重新載入 → 關。
 *
 * ⚠ 誠實的限制：這是**畫面閘門，不是存取控制**。
 *   quote-proxy（Cloudflare Worker）與 taifex Deno 代理本身照舊公開可打（它們只看 Origin），
 *   懂技術的人改 localStorage 或直接打 Worker 網址仍然拿得到報價。要真的擋，得改 Worker：
 *   報價端點要求帶會員權杖、Worker 查 ADMIN_EMAILS 才回（列為後續，見 DECISIONS 同一條）。
 *
 * 驗收後門：`window.TW_LIVE_OVERRIDE = true／false`（只在 127.0.0.1／localhost 認，正式站與預覽版一律不認）。
 *   scripts/_uitest.py 預設對每一頁注入 true —— 既有幾十段即時驗收驗的是「管理者看到的樣子」；
 *   「即時僅管理者1006」那一段刻意不注入，走真的登入快取＋假 Worker（/v1/me 回 admin:true／false）。
 * 對外：window.TwLive.allowed()（布林）、window.TwLive.state()（驗收用：{on, src, email}）。
 */
(function () {
  'use strict';
  var K_TOK = 'tw.acct.tok', K_USER = 'tw.acct.user';
  var root = document.documentElement;

  function cachedUser() {
    try {
      if (!localStorage.getItem(K_TOK)) return null;               // 跟 account.js 同一條：沒有權杖＝沒登入
      return JSON.parse(localStorage.getItem(K_USER) || 'null');
    } catch (e) { return null; }                                  // 私密視窗讀不到 → 當作沒登入
  }
  function override() {
    var h = location.hostname;
    if (h !== '127.0.0.1' && h !== 'localhost') return null;      // 只給本機驗收用
    var v = window.TW_LIVE_OVERRIDE;
    return v === true || v === false ? v : null;
  }
  function who() {
    var A = window.TwAccount;
    if (A && typeof A.user === 'function') return { u: A.user(), src: 'account' };
    return { u: cachedUser(), src: 'cache' };
  }
  function compute() {
    var o = override();
    if (o !== null) return { on: o, src: 'override', email: '' };
    var w = who();
    return { on: !!(w.u && w.u.admin === true), src: w.src, email: (w.u && w.u.email) || '' };
  }

  var cur = compute();
  root.classList.toggle('live-on', cur.on);

  /* ---- CSS：訪客／會員看不到的即時 UI。display:none（不是 visibility）＝不佔位，版面不留洞。*/
  try {
    var st = document.createElement('style');
    st.id = 'liveGateCss';
    st.textContent = [
      'html:not(.live-on) .livetg,',
      'html:not(.live-on) .livebtn,',
      'html:not(.live-on) #liveState,',
      'html:not(.live-on) #rotLiveTag,',
      'html:not(.live-on) #rotLive,',
      'html:not(.live-on) [data-live-ui]{display:none!important}',
      /* 總覽摘要卡右上角那顆同時是「資料日期」標籤：訪客看到的是日期，不是開關 ——
         點了不切換（點穿到卡片本身＝捲到那一區，跟點卡片其他地方一樣）、游標也不變成手指 */
      'html:not(.live-on) .osc-d.ovl-tg{pointer-events:none;cursor:default}',
    ].join('\n');
    (document.head || root).appendChild(st);
  } catch (e) { /* 極舊瀏覽器：各模組自己的判斷仍然擋得住 */ }

  /* ---- 登入狀態變了 → 重新評估；變了就整頁重新載入（理由見檔頭 ④）*/
  var reloading = false;
  function sync() {
    var nx = compute();
    if (nx.on === cur.on) { cur = nx; return; }
    cur = nx;
    root.classList.toggle('live-on', cur.on);
    if (reloading) return;
    reloading = true;
    try { window.dispatchEvent(new CustomEvent('tw:livegate', { detail: { on: cur.on } })); } catch (e) { /* 舊瀏覽器 */ }
    /* 留一點時間給 account.js 把「已登入／已登出」的提示寫完、把權杖存好，再重新載入 */
    setTimeout(function () { try { location.reload(); } catch (e) { /* 略 */ } }, 400);
  }
  window.addEventListener('tw:account', sync);

  window.TwLive = {
    /** 這個人看得到、也會觸發盤中即時嗎（＝已登入的管理者）。每一個即時入口開頭都問它。 */
    allowed: function () { return cur.on; },
    /** 驗收用：現在的判斷結果與依據（override／account／cache）。不回傳任何權杖。 */
    state: function () { return { on: cur.on, src: cur.src, email: cur.email, reloading: reloading }; },
  };
})();
