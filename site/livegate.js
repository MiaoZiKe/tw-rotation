/* livegate.js — 盤中即時功能只給「站主或管理員」（Andy 2026-10-08）
 *
 * Andy 原話（2026-10-08，兩段）：先說「即時功能 除了我這個帳號其他都不能附上」，同天更正為「即時功能全拿掉，除了有管理權限帳號」；
 *   補一句「有類似功能都拿掉 因為都是盤後」（非管理身分連「盤後／即時」切換鈕組都不畫）。
 *   改前（2026-10-06，DECISIONS #326）：判斷 /v1/me 的 admin:true，預覽版（TW_PREVIEW）一律全開（#343）；非管理者的控制項多半是 CSS 藏、登入登出整頁重新載入。
 *   改後：canLive()＝/v1/me 的 owner:true（站主）**或** admin:true（管理權限頁加進去的管理員；跟 account.js 管理區選單、tabdrag.js 同一個欄位）。
 *         訪客、免費、Plus、Pro 一律看不到；**預覽版也不例外**（預覽只是部署位置不同，不是身分 —— Andy 就是在預覽站看到訪客也有切換鈕）。
 *         非管理身分的即時控制項**整個不畫**；登入／登出原地切換，不重新載入（見 ④）。
 *   （下面註解裡的「站主」一律讀成「站主或管理員」。）
 *
 * 這支是**唯一的閘門**。全站所有「盤中即時」相關的東西都問它：
 *   · live.js：報價格子每 5 秒更新、卡片的「即時」開關（個股／自選／大盤三張圖）、頂欄即時狀態、
 *     Live.proxy()／taifexProxy()（不是站主時回空字串 → 任何模組都打不到 quote-proxy／Deno／mis）
 *   · market3.js：大盤三張圖的分時檔、台指期日盤／夜盤、Yahoo 1 分線 —— 不是站主時只畫資料湖的最近交易日（盤後版本）
 *   · livek.js：個股即時分 K／分時尾巴（不 attach、不輪詢）
 *   · industry.js：個股週期列不列 1分／5分／15分（那三個週期只有即時來源）；族群總覽的「即時」鈕（非站主不畫）
 *   · app.js：市場明細漲跌家數「盤後／⚡ 即時」、輪動時鐘與資金分流樹的「即時」鈕、總覽摘要卡右上角的即時開關（非站主一律不畫）
 * 不只藏按鈕，**連輪詢都不跑、不打任何報價端點**（省 Cloudflare／Deno 免費額度，也避開授權風險）。
 *
 * 做法（集中式）：
 *   ① <html> 上掛 class `live-on`（只有站主有）。這支放在 <head>、比 <body> 先跑，所以訪客第一幀就看不到任何即時 UI，不會先閃一下再消失。
 *   ② 下面注入一小段 CSS：`html:not(.live-on)` 時把 `.livetg`、`.livebtn`、`#liveState`、以及任何標了 `data-live-ui` 的節點整顆 display:none。
 *      各模組自己在「不是站主」時本來就不畫那顆鈕 —— CSS 是第二道保險（例如有人新增了一顆 .livebtn 卻忘了問閘門）。
 *   ③ 各模組開頭問 `TwLive.allowed()`；live.js 的 proxy() 不給網址是第三道（網路層）保險。
 *   ④ 登入狀態改變（account.js 的 tw:account）時重新評估；結果變了就**原地切換，不重新載入**（2026-10-08 要求）：
 *      先換 live-on（CSS 當下就藏／露），再派 `tw:livegate`（detail.on）。各模組自己收：
 *        live.js 收掉推送連線、把被改過的報價格子退回盤後值、拔掉卡片開關（或反過來掛上、馬上抓一輪）；
 *        market3.js 依閘門重排計時器；industry.js 族群即時模式的計時器下一跳自己退出；
 *        app.js 關掉三種族群即時模式後整頁重畫一次（跟換主題同一條 applyTheme(…, true)），重畫時各頁依新的閘門決定要不要畫即時鈕。
 *      改前（#326）是整頁 location.reload()；理由是「各模組各寫一套退場很容易漏」—— 現在退場集中在上面幾處，
 *      而且 live.js 的 tick() 每一輪都會再問一次閘門（漏了也只會空轉、不會打端點）。
 *
 * 判斷依據：先看 account.js 的 TwAccount.user()；account.js 還沒載入時（這支在 <head>，它在 <body> 尾端）
 * 直接讀同一份快取（localStorage tw.acct.tok＋tw.acct.user，account.js 同樣的規則：沒有權杖就不算登入）。
 * 開頁時用快取先決定（站主不用等 Worker 回應就看得到即時）；/v1/me 回來說他不是站主了（或權杖失效被登出）→ tw:account → 原地關。
 *
 * ⚠ 誠實的限制：這是**畫面閘門，不是存取控制**。
 *   quote-proxy（Cloudflare Worker）與 taifex Deno 代理本身照舊公開可打（它們只看 Origin），
 *   懂技術的人改 localStorage 或直接打 Worker 網址仍然拿得到報價。要真的擋，得改 Worker：
 *   報價端點要求帶會員權杖、Worker 查 owner 才回（列為後續）。
 *
 * 驗收後門：`window.TW_LIVE_OVERRIDE = true／false`（只在 127.0.0.1／localhost 認，正式站與預覽版一律不認）。
 *   scripts/_uitest.py 預設對每一頁注入 true（大量舊段落驗的是「看得到即時的人」看到的樣子）；
 *   直接驗即時的那幾段（盤中即時、市場明細、個股即時分K、輪動時鐘即時、新-資金流向、播放普查1007）2026-10-08 起改用假的站主登入；
 *   「即時僅管理1008」走真的登入快取＋假 Worker（/v1/me 回 站主／管理員／免費／Plus／Pro）。
 * 對外：window.TwLive.allowed()（布林）、window.TwLive.state()（驗收用：{on, src, email, flips}）。
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
  /** 這個使用者能不能用即時：站主（owner）或管理員（admin）。全站只有這一條規則。 */
  function canLiveUser(u) { return !!(u && (u.owner === true || u.admin === true)); }
  function compute() {
    var o = override();
    if (o !== null) return { on: o, src: 'override', email: '' };
    /* 2026-10-08 改前：預覽版（TW_PREVIEW）一律 on:true（#343）；改後：預覽版也一樣要站主或管理員登入 */
    var w = who();
    return { on: canLiveUser(w.u), src: w.src, email: (w.u && w.u.email) || '' };
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
      /* 總覽摘要卡右上角那顆：管理者是即時開關；訪客原本看到的是資料日期（MM/DD）——
         2026-10-06 Andy「這類資訊（資料時段＋資料日期膠囊）一律拿掉」（DECISIONS #329）→ 訪客整顆不顯示，
         「›」箭頭跟著靠右（原本靠這顆把它推過去）。點不到、也就不會切換。 */
      'html:not(.live-on) .osc-d.ovl-tg{display:none!important}',
      'html:not(.live-on) .osc-d.ovl-tg + .osc-more{margin-left:auto}',
      /* 2026-10-08：非站主時 app.js 乾脆不畫那顆（不只藏），「›」緊接在標題後面 —— 一樣靠右 */
      'html:not(.live-on) .osc-h .osc-more{margin-left:auto}',
    ].join('\n');
    (document.head || root).appendChild(st);
  } catch (e) { /* 極舊瀏覽器：各模組自己的判斷仍然擋得住 */ }

  /* ---- 登入狀態變了 → 重新評估；變了就原地切換（理由見檔頭 ④；2026-10-08 起不再整頁重新載入）*/
  var flips = 0;
  function sync() {
    var nx = compute();
    if (nx.on === cur.on) { cur = nx; return; }
    cur = nx;
    flips++;
    root.classList.toggle('live-on', cur.on);
    try { window.dispatchEvent(new CustomEvent('tw:livegate', { detail: { on: cur.on } })); } catch (e) { /* 舊瀏覽器 */ }
  }
  window.addEventListener('tw:account', sync);

  window.TwLive = {
    /** 這個人看得到、也會觸發盤中即時嗎（＝已登入的站主或管理員）。每一個即時入口開頭都問它。
     *  2026-10-08 正式名稱是 canLive()；allowed() 是舊名，留著當別名（live.js／app.js／industry.js／market3.js／livek.js 都還在叫）。*/
    canLive: function () { return cur.on; },
    allowed: function () { return cur.on; },
    /** 驗收用：現在的判斷結果與依據（override／account／cache）。不回傳任何權杖。 */
    state: function () { return { on: cur.on, src: cur.src, email: cur.email, flips: flips }; },
  };
  /* 全站共用的短名：window.canLive()（跟 TwLive.canLive() 同一個）*/
  window.canLive = window.TwLive.canLive;
})();
