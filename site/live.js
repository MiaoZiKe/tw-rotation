/* live.js — 盤中即時報價層（Andy 2026-09-14）
 *
 * Andy 的需求原話：「盤中至少每分鐘更新一次，盤後每 30min 更新一次，且需要新增更新按鍵…
 * 可以直接在盤中時去看股票網站，知道他的價錢後把數字更新過來。」
 *
 * 為什麼這件事不能放在 GitHub Actions
 * ------------------------------------
 * Actions 的 cron 最短 5 分鐘，而且免費層會延遲（本專案實測過延遲 4 小時）。
 * 「每分鐘」只可能在瀏覽器裡做 —— 網頁自己去抓。
 *
 * 為什麼中間一定要有一層代理
 * --------------------------
 * 2026-09-14 15:08 從 https://miaozike.github.io 實測：
 *   fetch(mis.twse…)            → TypeError: Failed to fetch
 *   fetch(mis.twse…, no-cors)   → 通
 * 連得到但讀不到 ＝ 被 CORS 擋的，不是網路不通。證交所那支沒有給
 * Access-Control-Allow-Origin，靜態網站的 JS 讀不到它。
 * 所以要一層 Cloudflare Worker 幫忙轉一手並補上 CORS 標頭（workers/quote-proxy/）。
 *
 * 資料源：https://mis.twse.com.tw/stock/api/getStockInfo.jsp
 * 2026-09-14 15:09 實測：一個請求 120 檔、120ms 回全；上市（tse_）與上櫃（otc_）
 * 可以混在同一個請求；tse_t00.tw 是加權指數。當時它已經有當天（20260914）的資料，
 * 而 openapi.twse 那支到 14:32 都還停在 09-11 —— 所以這條也順便解掉「網站慢一天」。
 *
 * 2026-09-23：從「每分鐘輪詢」改成「一條 SSE 連線」
 * --------------------------------------------------
 * Andy 看了永豐金 shioaji-pro-app 之後說「即時更新的功能幫我參考」。
 * 那支是本機跑的交易終端，資料源我們用不到（它打的是使用者自己電腦上的 server），
 * 但它的**做法**可以搬：前端不要自己輪詢，改成訂一條 SSE（伺服器推送）連線，
 * 由伺服器那一側去高頻問上游，只有值變了才推下來。
 *
 * 我們這邊的伺服器就是 workers/quote-proxy 那支 Cloudflare Worker，
 * 新增了 /stream 端點。好處是：高頻輪詢只發生在 Worker 一側，
 * 多個分頁共用同一份上游結果，畫面卻從「一分鐘一跳」變成「五秒一跳」。
 *
 * ★★ 退回輪詢是硬性設計，不是備案
 * Worker 隨時可能是舊版（還沒重新部署，就沒有 /stream）、可能被公司網路擋掉、
 * 也可能因為免費方案的 CPU 上限被平台砍斷。這三種情況使用者都不該看到壞掉的畫面 ——
 * 所以 SSE 一旦連不上或斷掉，**立刻回到原本那條每分鐘輪詢的路**，
 * 而且馬上補抓一次，畫面不會有缺口。狀態列會寫現在走的是「推送」還是「輪詢」。
 *
 * 2026-09-24：「更新」與「⚙ 即時來源設定」兩顆鈕拿掉
 * ------------------------------------------------
 * Andy：「按鈕更新、設定 版都移除」「即時 10:44 每分鐘（輪詢） → 只留時間」。
 * 拿掉的只是**手動入口**，自動更新一條都沒停（盤中每分鐘、盤後每 30 分鐘）。
 * 連帶改的三件事（不改就會出事）：
 *   ① 以前「連續失敗三次 → 關掉計時器，等使用者按『更新』」。按鈕沒了，那等於**自動更新永久停擺**。
 *      改成「連續失敗 → 放慢到每 5 分鐘試一次，成功就回到正常間隔」，洗版的理由照顧到、也不會停。
 *   ② 以前「有新資料，按『更新』載入」。改成點狀態那顆本身重新載入（只有那個狀態可以點）。
 *   ③ 以前「放棄 SSE 之後按『更新』重試」。改成分頁切回前景時重試（那是使用者回來看的時間點）。
 * 狀態那顆畫面上只剩時間，「即時／收盤、每分鐘（輪詢）、推送」這些字全部搬進 title。
 *
 * 更新哪些數字
 * ------------
 * 只更新「畫面上看得到的」（Andy 拍板）。做法是掃 DOM 上的 [data-lc]，
 * 有哪些代號就抓哪些，換一頁自然就換一組。全市場每分鐘既沒有意義
 * （資金輪動是族群層級的事），對官方端點也不禮貌。
 *
 * 2026-09-29：盤中從「每分鐘」改成「每 5 秒」＋ 每張卡片自己的「即時」開關
 * ------------------------------------------------------------------------
 * Andy：「即時…至少 5S 更新一次…可『即時』更新的圖表及數據多新增『即時』選項，
 * 歷史過往數據就沒辦要新增更新」。改前實測（假時間＋假 Worker，量 32 秒）：
 *   本檔報價 60 秒一次、大盤三張圖 10 秒、個股分 K 尾巴 5 秒、四個族群層級的即時模式 60 秒。
 * 為什麼是 5 秒、不是更快：mis 自己的快照就是 5 秒一張（回應裡 userDelay=5000，DECISIONS #127），
 * 問更密拿到的是同一張。為什麼 5 秒不會打爆來源，靠下面四道護欄（全部在這個檔案裡，其他模組共用）：
 *   ① **一批查完**：畫面上所有代號＋各卡片登記的代號（Live.want）併成一個請求（上限 110 檔）。
 *   ② **只查看得到的**：display:none 的分頁、關掉「即時」的卡片裡的代號不查。
 *   ③ **節流閥 slot()**：這個分頁對 mis（/quote、/chart）**每 5 秒最多 3 個請求**，其他模組
 *      （族群即時、大盤分時檔、個股分 K 備援）一律排隊過這一道。3 的來源：社群套件 twstock
 *      文件寫的「證交所每 5 秒超過 3 個請求會被封 IP」（非官方、中信心，但寧可照它）。
 *   ④ **錯誤退避**：連續失敗 n 次 → 間隔 5 秒 × 2ⁿ（10、20、40、80、160 秒，封頂 5 分鐘），
 *      通了立刻回 5 秒；分頁切到背景完全不打（document.hidden），切回來補一輪。
 * 盤後維持每 30 分鐘（數字不會再變）。
 *
 * 2026-10-02：總覽摘要卡四張也即時（DECISIONS #296）—— 「補位」，不多打請求
 * ------------------------------------------------------------------------
 * Andy：「這都需要具備即時功能」（漲跌家數、資金輪盤、資金去向、熱門題材四張摘要卡）。
 * 那四張要的是 455 檔成分股的報價，照一般做法要多 4～5 個請求一輪。這裡改成「補位」：
 * 主批次一個請求本來就塞得下 110 檔、總覽平常只用 2～10 檔，剩下的空位每 5 秒塞下一段（Live.want(key, fn, {fill:true})），
 * 約 25 秒輪完一圈。請求數、5 秒節奏、節流閥一個都沒變，變的只是每個請求多帶幾十檔。
 */
(function () {
  'use strict';

  const KEY_PROXY = 'tw.live.proxy';   // Worker 網址（不是密鑰，可以放 localStorage）
  const KEY_ON = 'tw.live.on';         // 自動更新開關
  const MAX_CODES = 110;               // 實測一個請求 120 檔 OK，留一點邊際
  const MS_FAST = 5 * 1000;            // ★ 2026-09-29：盤中每 5 秒（＝mis 自己的 userDelay，見檔頭）
  const MS_INTRADAY = MS_FAST;         // 盤中：每 5 秒（2026-09-29 以前是每分鐘）
  const MS_AFTER = 30 * 60 * 1000;     // 盤後：每 30 分鐘
  const STALE_MS = 3 * 60 * 1000;      // 超過這麼久沒成功就把狀態標成「停了」
  /* 錯誤退避（2026-09-29 改）：連續失敗 n 次 → 下一輪間隔 MS_FAST × 2ⁿ，封頂 BACKOFF_MAX。
     改前是「連 3 次失敗 → 直接放慢到 5 分鐘」。5 秒一輪之後那樣太粗：
     網路抖一下（失敗 1 次）就該 10 秒後再試，不是照樣 5 秒猛敲；
     真的打不通（公司網路擋 workers.dev）也會在一分多鐘內退到 5 分鐘一次，不洗版 console。
     ★ 2026-09-24 以前是「關掉，等使用者按『更新』」—— 那顆鈕拿掉之後就等於永久停擺，所以一律是退避不是停。*/
  const BACKOFF_MAX = 5 * 60 * 1000;
  const backoffMs = (n) => Math.min(BACKOFF_MAX, MS_FAST * Math.pow(2, Math.max(1, n)));
  const MAX_FAILS = 3;                 // 連續失敗到這個次數，狀態列才用「連續抓不到」的警示字眼
  /* ---- 節流閥（見檔頭 ③）：這個分頁對 mis 的請求，每 MIS_WINDOW_MS 最多 MIS_MAX 個。 */
  const MIS_WINDOW_MS = 5000;
  const MIS_MAX = 3;
  /* meta.json（網站有沒有重新部署）不必跟著 5 秒一輪一起問 —— 部署一天才幾次，盤中一分鐘看一次就夠。*/
  const META_EVERY_MS = 60 * 1000;
  const KEY_CARD = (k) => 'tw.live.card.' + k;   // 每張卡片的「即時」開關（'0'＝關；沒設定＝開）

  // ---- SSE（伺服器推送）相關
  // 退避序列：斷了之後隔多久再試。從 1 秒開始翻倍到 30 秒封頂 ——
  // 前面密一點是為了「只是換頁／連線輪替」那種瞬斷能馬上接回來，
  // 後面拉長是為了「Worker 根本是舊版」那種永遠不會成功的情況不要一直洗。
  const SSE_BACKOFF = [1000, 2000, 4000, 8000, 15000, 30000];
  // **從來沒連上過**就失敗這麼多次 → 這次開頁不再試 SSE，安靜地用輪詢。
  // 曾經連上過就不放棄（那代表 Worker 是新版，斷掉多半是輪替或網路抖動）。
  const SSE_GIVEUP = 4;
  // 連著卻這麼久沒收到任何東西（含心跳）就當成斷了。
  // Worker 心跳最慢 30 秒一次（盤前盤後），所以 90 秒是「連漏三次心跳」。
  const SSE_WATCHDOG_MS = 90 * 1000;
  // SSE 活著的時候仍然保留一個**保底輪詢**，只是放很慢。
  // 為什麼不乾脆關掉：推送這條路是新的，萬一它安靜地壞掉（連著但不推），
  // 五分鐘一次的對帳至少能讓數字繼續走，而不是整頁停在那裡。
  const MS_SAFETY = 5 * 60 * 1000;

  // Andy 的 Cloudflare Worker（2026-09-14 部署完成並實測過）。
  // 填成預設值，換一台電腦／換一個瀏覽器都不用再設定一次。
  // localStorage['tw.live.proxy'] 仍然蓋得過它（本機測試與驗收用）；
  // ⚙ 設定面板 2026-09-24 拿掉了，要換 Worker 就改這一行。
  // 這不是密鑰 —— Worker 本身只轉一個端點、只給白名單網域 CORS。
  const DEFAULT_PROXY = 'https://tw-quote.kcq01010909.workers.dev';

  // 台指期（期交所 /fut、/futchart）專用的代理：Deno Deploy（DECISIONS #286）。
  // 期交所在 Cloudflare 後面、拒絕所有經 Cloudflare Worker 來的請求（上游 520，#281），
  // 所以上面那台 Worker 打不到期交所；Deno Deploy 不走 Cloudflare 出口，2026-10-02 實測日盤夜盤四支全 200。
  // market3.js 先打這台，失敗才退回 DEFAULT_PROXY 的 /fut、/futchart（Worker 那兩支保留不刪）。
  // 原始碼 workers/taifex-deno/main.ts，推上 main 由 .github/workflows/deploy-deno.yml 部署。這不是密鑰。
  const TAIFEX_PROXY = 'https://tw-taifex.miaozike.deno.net';

  const state = {
    quotes: {},        // code -> { price, prevClose, chgPct, open, high, low, volume, time, name }
    timer: null,
    busy: false,
    lastOk: 0,
    lastErr: '',
    tries: 0,
    slow: false,         // 連續失敗 MAX_FAILS 次之後放慢重試（見 MAX_FAILS）
    period: 0,           // 目前計時器的間隔（毫秒）；驗收用它確認「每分鐘／每 30 分」真的排上去了
    fresher: false,      // 伺服器上已經有更新的資料，但盤中不自動重載
    // ---- SSE
    mode: 'poll',        // 現在真的走哪條路：'sse' 推送／'poll' 輪詢
    es: null,            // EventSource
    sseIds: '',          // 這條連線訂的是哪一組代號（畫面換了就要重開）
    sseFails: 0,         // 連續失敗次數（連上就歸零）
    sseEverOk: false,    // 這次開頁有沒有成功過
    sseGaveUp: false,    // 放棄 SSE（分頁切回前景會重來）
    sseTimer: null,      // 重連計時器
    sseWatch: null,      // 看門狗
    ssePaused: false,    // 分頁切到背景時暫停，不算失敗
    sseAt: 0,            // 最後一次收到推送的時間
    // ---- 2026-09-29 每 5 秒＋卡片開關
    raw: {},             // code -> { m: mis 原始那一列, at }：個股分 K（livek.js）與大盤卡（market3.js）直接吃這一份，不再各打一次
    wants: {},           // 卡片登記「畫面上沒有 [data-lc]、但我要」的代號：key -> [code]
    /* ★ 2026-10-02（DECISIONS #296）：「補位」登記 —— key -> fn(room)。跟 wants 的差別：
       wants 是「一定要」（大盤卡的 t00／o00），補位是「這一批還有空位才塞」（總覽摘要卡要的 455 檔成分股，
       每輪輪一段）。它**不會多打任何一個請求**、也不會擠掉畫面上的代號：主批次本來就是一個請求最多 110 檔，
       總覽平常只用掉 2～10 檔，剩下的空位每 5 秒塞下一段，約 25 秒輪完一圈。*/
    fills: {},
    fillSent: {},        // 這一輪真的塞進請求的補位代號：key -> [code]（跟 tw:live 一起送出去，登記的人才知道輪到哪）
    cardAt: {},          // 卡片 key -> 這張卡最後一次真的拿到新報價的時間（卡上那行「更新 HH:MM:SS」）
    metaAt: 0,           // 上一次比對 meta.json 的時間（見 META_EVERY_MS）
    reqs: 0,             // 驗收用：這個分頁總共打了幾次 /quote
  };
  /* ---- 節流閥的狀態：最近 5 秒內發出去的請求時間戳，與排隊中的請求 */
  const slotHist = [];
  const slotQ = [];
  let slotT = null;
  /* ---- 其他模組的錯誤退避（2026-09-29 收尾補上）：key -> { n: 連續失敗次數, at: 最後一次失敗的時間 }
     族群即時模式（漲跌家數 mud、輪動時鐘 rlv、資金去向 skl、族群頁 gp）與大盤卡的期貨報價（m3fut）
     各自一個 key。改前它們失敗了照樣每 5 秒再打一次 —— 節流閥擋得住「5 秒超過 3 個」，
     但擋不住「一直打一個已經壞掉的端點」。跟本檔主批次同一條曲線：10、20、40…秒，封頂 5 分鐘。*/
  /* ⚠ at 記的是「那一輪開始抓的時間」（t0），不是失敗回來的時間：族群模式一輪要排節流閥、可能花好幾秒，
     用失敗時間起算的話，5 秒一跳的計時器會把 10 秒量化成 15 秒（實測 15.2 秒）。
     250ms 的寬容是給 setInterval 的抖動（第 10 秒那一跳可能早幾毫秒到）。*/
  const cool = {};
  function cooling(k) { const c = cool[k]; return !!c && c.n > 0 && Date.now() - c.at < backoffMs(c.n) - 250; }
  function report(k, good, t0) {
    if (good) { delete cool[k]; return; }
    const c = cool[k] || { n: 0, at: 0 }; c.n++; c.at = t0 || Date.now(); cool[k] = c;
  }

  const ls = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗會丟例外，忽略 */ } },
  };

  const proxy = () => (ls.get(KEY_PROXY, '') || DEFAULT_PROXY).replace(/\/+$/, '');
  const autoOn = () => ls.get(KEY_ON, '1') === '1';

  // ---------------------------------------------------------------- 台北時間
  function taipeiNow() {
    // 使用者的電腦可能不在台北（Andy 兩台機器），一律換算成台北時間再判斷盤中盤後
    const s = new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' });
    return new Date(s);
  }

  /** 現在是不是盤中。09:00–13:35（收盤 13:30，多留 5 分鐘讓尾盤撮合落地）。
   *  只看星期幾，**不管國定假日** —— 假日會照跑但拿到的是上一個交易日的數字，
   *  沒有壞處（頁面會顯示資料時間），不值得為此在前端維護一份行事曆。 */
  function isIntraday(d) {
    d = d || taipeiNow();
    const w = d.getDay();
    if (w === 0 || w === 6) return false;
    const m = d.getHours() * 60 + d.getMinutes();
    return m >= 9 * 60 && m <= 13 * 60 + 35;
  }

  const intervalMs = () => (isIntraday() ? MS_INTRADAY : MS_AFTER);

  // ---------------------------------------------------------------- 代號
  /* ---------------------------------------------------------------- 卡片的「即時」開關
   * 一張卡片＝一個 key（'stock' 個股報價＋分時、'watch' 自選清單、'm3' 大盤三張圖）。
   * 卡片的外框帶 data-livekey，裡面的 [data-live][data-lc] 就跟著那顆開關走：
   * 關掉＝那些格子不查、不改，而且**退回頁面原本的靜態值**（盤後資料）。*/
  /* ★ 2026-10-02 會員功能權限（DECISIONS #288）：「盤中即時（5 秒）」被管理者關掉的人＝所有卡片都當作「即時」關著。
     market3.js（m3On）、livek.js（cardOn）都是問這一支，所以只要這裡一行就全站一致。預設全開，沒載入 perm.js 也是開。*/
  const permLive = () => !window.TwPerm || window.TwPerm.can('live.tick');
  const cardOn = (k) => permLive() && ls.get(KEY_CARD(k), '1') !== '0';
  const keyOf = (el) => { const c = el.closest && el.closest('[data-livekey]'); return c ? c.dataset.livekey : ''; };
  /** 這個元素現在該不該被即時層動到：沒有歸屬卡片的照舊（一律跟著全站自動更新），有歸屬的看那張卡的開關。 */
  const elOn = (el) => { if (!permLive()) return false; const k = keyOf(el); return !k || cardOn(k); };
  /** 看得到嗎。display:none 的分頁、收起來的面板 getClientRects() 是空的。
   *  ★ 沒有 data-live 的純標記（例如總覽那個看不見的 [data-lc=t00]）不看可見度 —— 它本來就是「看不見但要抓」。*/
  const visible = (el) => !el.dataset.live || el.getClientRects().length > 0;

  /** 掃畫面上有哪些代號要更新。這就是「只更新看得到的」的實作。
   *  ★ 2026-09-29：加上兩條 —— 看不見的格子不查、卡片「即時」關掉的不查；
   *    再併進各卡片用 Live.want() 登記的代號（大盤卡要 t00／o00，畫面上沒有對應的格子）。*/
  function codesOnScreen(forFetch) {
    const seen = [];
    const add = (c) => { if (c && seen.indexOf(c) < 0) seen.push(c); };
    Object.keys(state.wants).forEach(k => {
      if (!cardOn(k)) return;
      const w = state.wants[k];
      let list = w;
      if (typeof w === 'function') { try { list = w(); } catch (e) { list = []; } }
      (list || []).forEach(add);
    });
    document.querySelectorAll('[data-lc]').forEach(el => {
      if (!elOn(el) || !visible(el)) return;
      add(el.dataset.lc);
    });
    const out = seen.slice(0, MAX_CODES);
    /* ★ 2026-10-02（DECISIONS #296）：補位 —— 只在「真的要去抓」的那一次（tick）才塞，SSE 訂閱（streamIds）不塞：
       推送訂的是畫面上那幾格，一份每 5 秒換一段的名單訂上去只會讓連線一直重開。
       預算用 ex_ch 的「個數」算、不是代號數：上市上櫃不明的代號會變成兩個（tse_＋otc_），
       Worker 一個請求最多收 140 個（workers/quote-proxy MAX_TOKENS），這裡守在 MAX_CODES（110）以內。
       補位**排在畫面代號後面**，所以永遠不會把畫面上的格子擠出請求。*/
    if (forFetch) {
      state.fillSent = {};
      let tok = 0; out.forEach(c => { tok += exch(c).length; });
      Object.keys(state.fills).forEach(k => {
        if (!cardOn(k)) return;
        const room = MAX_CODES - out.length;
        if (room <= 0 || tok >= MAX_CODES) return;
        let list = [];
        try { list = state.fills[k](room) || []; } catch (e) { list = []; }
        const sent = [];
        for (const c of list) {
          if (!c) continue;
          if (out.indexOf(c) >= 0) { sent.push(c); continue; }      // 畫面上本來就有：算它這一輪問過了（不重複塞）
          const t = exch(c).length;
          if (out.length >= MAX_CODES || tok + t > MAX_CODES) break;  // 塞滿就停；沒塞進去的留到下一輪（登記的人照 sent 的長度往前推）
          out.push(c); sent.push(c); tok += t;
        }
        if (sent.length) state.fillSent[k] = sent;
      });
    }
    return out;
  }

  /* ---------------------------------------------------------------- 節流閥
   * 這個分頁所有打到 mis 的請求（本檔的 /quote、族群即時模式借用的 fetchQuotes、
   * market3.js 的 /chart、livek.js 的備援 /quote）都要先 await slot()。
   * 5 秒內已經發了 3 個 → 排隊，等最舊那個滿 5 秒再放行。prio 越小越先（本檔的主批次是 0）。*/
  function slotPump() {
    const now = Date.now();
    while (slotHist.length && now - slotHist[0] >= MIS_WINDOW_MS) slotHist.shift();
    while (slotQ.length && slotHist.length < MIS_MAX) { slotHist.push(now); slotQ.shift().go(); }
    if (slotQ.length && !slotT) {
      const wait = Math.max(20, MIS_WINDOW_MS - (now - slotHist[0]) + 10);
      slotT = setTimeout(() => { slotT = null; slotPump(); }, wait);
    }
  }
  function slot(prio) {
    return new Promise(go => {
      slotQ.push({ prio: prio == null ? 1 : prio, t: Date.now(), go });
      slotQ.sort((a, b) => a.prio - b.prio || a.t - b.t);
      slotPump();
    });
  }

  /** 代號 → mis 的 ex_ch。t00 是加權指數、o00 是櫃買指數；其餘靠 stocks.json 分上市上櫃，
   *  查不到就兩邊都要（多要一個不會錯，回應本來就只回有的那個）。 */
  function exch(code) {
    if (code === 't00') return ['tse_t00.tw'];
    if (code === 'o00') return ['otc_o00.tw'];
    let mk = null;
    try {
      const A = window.App;
      mk = A && A.L && A.L.cmarket && A.L.cmarket[code];   // 全市場索引建好的代號→市場對照
    } catch (e) { /* 索引還沒載好 */ }
    if (mk === 'TPEX' || mk === 'otc') return ['otc_' + code + '.tw'];
    if (mk === 'TWSE' || mk === 'tse') return ['tse_' + code + '.tw'];
    return ['tse_' + code + '.tw', 'otc_' + code + '.tw'];
  }

  // ---------------------------------------------------------------- 抓取
  const num = v => {
    const n = parseFloat(v);
    return isFinite(n) ? n : null;
  };

  /** mis 的一列轉成我們要的形狀。
   *
   *  ★ 成交價的退位順序（2026-09-15 實測修正）
   *  mis 每 5 秒給一次快照，**兩次撮合之間 `z` 是 '-'**，真正的最新成交價
   *  在 `trade` 這個子物件裡。2026-09-15 10:26 抓到的 2330：
   *      { z: "-", tv: "-", v: "5280",
   *        trade: { ft: 20, t: "10:25:35", v: 1, z: "2395.0000" } }
   *  舊版遇到 z='-' 會退去用**最佳買價**，等於盤中有一大段時間顯示的根本不是成交價
   *  （買價永遠比成交價低一檔，看起來就像一直在跌）。
   *  正確順序：z → trade.z → 最佳買價 → 開盤 → 昨收。 */
  function normalise(m) {
    const prev = num(m.y);
    const tr = m.trade || {};
    let price = num(m.z);
    let at = m.t || '';
    if (price === null) {
      const tz = num(tr.z);
      if (tz !== null) { price = tz; at = tr.t || at; }
    }
    if (price === null && m.b) price = num(String(m.b).split('_')[0]);
    if (price === null) price = num(m.o);
    if (price === null) price = prev;
    return {
      code: m.c,
      name: m.n,
      price,
      prevClose: prev,
      chgPct: (price !== null && prev) ? (price - prev) / prev * 100 : null,
      open: num(m.o), high: num(m.h), low: num(m.l),
      volume: num(m.v),          // 累計成交張數
      limitUp: num(m.u), limitDown: num(m.w),   // ★ 2026-10-05：mis 自帶的漲停價／跌停價（市場明細判漲跌停用；沒有就前端照升降單位自己算）
      time: at,                  // 這筆成交的時間（HH:MM:SS）
      date: m.d || '',
      at: Date.now(),
    };
  }

  const FETCH_TIMEOUT_MS = 12000;   // 報價請求逾時
  /** 打一次 /quote。opts.prio：節流閥的優先序（本檔主批次 0；族群即時模式沒給＝2，排在後面）。 */
  async function fetchQuotes(codes, opts) {
    const base = proxy();
    if (!base) throw new Error('還沒設定代理網址');
    if (!codes.length) return {};
    const ex = [];
    codes.forEach(c => exch(c).forEach(t => ex.push(t)));
    const url = base + '/quote?ex_ch=' + encodeURIComponent(ex.slice(0, MAX_CODES * 2).join('|'));
    await slot(opts && opts.prio != null ? opts.prio : 2);
    state.reqs++;
    // ★ 2026-09-24：加逾時。以前代理卡住時 fetch 永遠不回，即時模式就停在「更新中」不動。
    const ctl = (typeof AbortController === 'function') ? new AbortController() : null;
    const tm = ctl ? setTimeout(() => ctl.abort(), FETCH_TIMEOUT_MS) : 0;
    let r;
    try {
      r = await fetch(url, ctl ? { cache: 'no-store', signal: ctl.signal } : { cache: 'no-store' });
    } catch (e) {
      if (e && e.name === 'AbortError') throw new Error('報價逾時（' + FETCH_TIMEOUT_MS / 1000 + ' 秒沒回應）');
      /* ★ 2026-09-25（R3 審查）：連不上代理時瀏覽器丟的是英文 TypeError「Failed to fetch」
         （Firefox 是「NetworkError when attempting to fetch resource」），原樣印在畫面上。
         網站一律繁中，而且這句對使用者沒有資訊，改成講人話：是網路連不到報價代理。*/
      if (e && (e.name === 'TypeError' || /fetch|network/i.test(String(e.message || '')))) {
        throw new Error('連不到報價代理（網路不通或被擋）');
      }
      throw e;
    } finally { if (tm) clearTimeout(tm); }
    if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
    const j = await r.json();
    if (j.rtcode && j.rtcode !== '0000') throw new Error('來源回 rtcode ' + j.rtcode);
    return absorb(j);
  }

  /** mis 的整包回應 → { code: 報價 }。
   *  輪詢與 SSE 推送共用這一支：兩條路拿到的是同一份上游 JSON，
   *  解析各寫一套的話遲早會一邊對一邊錯（2026-09-15 那個「一直在跌」就是這樣來的）。 */
  function absorb(j) {
    const out = {};
    const now = Date.now();
    ((j && j.msgArray) || []).forEach(m => {
      const q = normalise(m);
      if (q.code) { out[q.code] = q; state.raw[q.code] = { m, at: now }; }
    });
    return out;
  }

  /** 把一包報價寫進 state 並重畫。推送與輪詢的收尾動作完全一樣。 */
  function apply(pack) {
    const n = Object.keys(pack).length;
    if (!n) return 0;
    state.quotes = Object.assign({}, state.quotes, pack);
    state.lastOk = Date.now();
    state.lastErr = '';
    state.tries = 0;
    paint();
    return n;
  }

  // ---------------------------------------------------------------- SSE 推送
  /* 這一整段就是「把每分鐘輪詢換成一條連線」。
   *
   * 設計上只有三個規矩，其他都是細節：
   *   1. **推送是加分，輪詢是底線。** 任何一步失敗都回到輪詢，
   *      而且立刻補抓一次，畫面不准出現缺口。
   *   2. **只動 [data-live] 的格子。** 推送走的是跟輪詢同一個 apply() → paint()，
   *      沒有另外一條會整頁重畫的路。
   *   3. **重連一定要拿完整快照。** Worker 那邊對每條新連線的第一筆刻意不做去重，
   *      所以重連＝補回斷線期間漏掉的值。
   */

  /** 這次要訂哪一組代號（跟輪詢用的是同一套 exch 規則）。 */
  function streamIds() {
    const ex = [];
    codesOnScreen().forEach(c => exch(c).forEach(t => ex.push(t)));
    return ex.slice(0, MAX_CODES * 2).join('|');
  }

  function clearWatch() {
    if (state.sseWatch) { clearTimeout(state.sseWatch); state.sseWatch = null; }
  }

  /** 看門狗：連著卻沒聲音就當成斷了。
   *  為什麼需要它：SSE 有一種最難查的壞法是「TCP 還在、資料不來」，
   *  這時 onerror 永遠不會觸發，畫面會安靜地停住。 */
  function armWatch() {
    clearWatch();
    state.sseWatch = setTimeout(() => {
      dropStream('太久沒收到推送');
    }, SSE_WATCHDOG_MS);
  }

  /** 關掉連線。paused=true 代表是我們自己暫停（切到背景），不算失敗。 */
  function closeStream(paused) {
    clearWatch();
    if (state.sseTimer) { clearTimeout(state.sseTimer); state.sseTimer = null; }
    if (state.es) { try { state.es.close(); } catch (e) { /* 已經關了 */ } state.es = null; }
    state.ssePaused = !!paused;
    if (state.mode === 'sse') { state.mode = 'poll'; reschedule(); }
  }

  /** 連線掉了：退回輪詢 → 立刻補抓一次 → 排一次重連。 */
  function dropStream(why) {
    const wasLive = state.mode === 'sse';
    clearWatch();
    if (state.es) { try { state.es.close(); } catch (e) { /* 已經關了 */ } state.es = null; }
    state.mode = 'poll';
    state.sseFails++;
    // ★ 硬性要求：退回輪詢的同時馬上抓一次，不要等下一個整分鐘。
    //   這一步就是「使用者不該看到任何壞掉的畫面」的實作。
    reschedule();
    if (autoOn()) tick(false);
    if (!state.sseEverOk && state.sseFails >= SSE_GIVEUP) {
      // 從頭到尾沒連上過 → 多半是 Worker 還是舊版（沒有 /stream）。
      // 安靜地用輪詢就好，不要一直重試洗 console。
      state.sseGaveUp = true;
      stamp();
      return;
    }
    const wait = SSE_BACKOFF[Math.min(state.sseFails - 1, SSE_BACKOFF.length - 1)];
    if (state.sseTimer) clearTimeout(state.sseTimer);
    state.sseTimer = setTimeout(() => { state.sseTimer = null; openStream(); }, wait);
    stamp();
    void wasLive; void why;
  }

  /** 開一條 SSE 連線。開不起來就當作一次失敗，交給 dropStream 處理。 */

  /* ★★ 2026-09-24：SSE 推送預設關閉（DECISIONS #256）。
     為什麼：Andy 一天之內四次回報「夜盤沒有數值」。時間軸攤開來看——
       19:43 SSE 上線 → 20:39 探測全 200 → 23:33 探測 POST 全 520
       → 23:5x 修掉「POST 帶了 GET 的快取選項」 → 00:15 探測全 200 → 02:00 他又看到 520
     同一版 Worker，200 → 520 → 200 → 520。**恆定的錯誤已經修掉了，剩下的是時好時壞**，
     而「時好時壞」指向的是額度／CPU 被吃掉，不是程式邏輯。
     免費方案的 Worker 每次調用只有 10ms CPU，而 SSE 是**長連線**：
     只要他把網頁開著，那條連線就一直在累加 CPU 與請求數，
     吃掉的是**同一個 Worker 上其他端點**（/fut、/futchart）的額度。

     取捨很清楚：**他抱怨「夜盤看不到數字」四次，要求「即時推送」一次。**
     可靠度優先於延遲。所以推送改成預設關閉、程式碼全部留著：
       localStorage['tw.sse'] === '1'  → 開推送
       其他（含沒設定）              → 走輪詢（跟 2026-09-23 之前一模一樣）
     要重新開啟只要在瀏覽器主控台打 `localStorage['tw.sse']='1'` 再重新整理。
     ⚠ 這不是「SSE 做壞了」——離線驗收 49 條全過。是這個免費方案養不起長連線。
     真要長期用推送，得先確認 Cloudflare 那邊的用量（只有 Andy 看得到後台）。*/
  function sseAllowed() {
    try { return localStorage.getItem('tw.sse') === '1'; } catch (e) { return false; }
  }

  function openStream() {
    if (!sseAllowed()) { state.sseGaveUp = true; return; }   // 預設關閉，見上面那段
    if (!autoOn() || state.sseGaveUp || state.ssePaused) return;
    if (typeof EventSource === 'undefined') { state.sseGaveUp = true; return; }
    const base = proxy();
    if (!base) return;
    const ids = streamIds();
    if (!ids) return;                       // 畫面上一個代號都沒有，不用開
    if (state.es && state.sseIds === ids) return;   // 同一組代號已經在推了
    if (state.es) { try { state.es.close(); } catch (e) { /* 已經關了 */ } state.es = null; }
    state.sseIds = ids;

    let es;
    try {
      es = new EventSource(base + '/stream?ids=' + encodeURIComponent(ids));
    } catch (e) {
      dropStream('開不起來：' + e);
      return;
    }
    state.es = es;

    const alive = () => {
      state.sseAt = Date.now();
      state.sseEverOk = true;
      state.sseFails = 0;
      if (state.mode !== 'sse') { state.mode = 'sse'; reschedule(); }
      armWatch();
    };

    es.addEventListener('hello', () => { alive(); stamp(); });
    es.addEventListener('quote', ev => {
      alive();
      try {
        const j = JSON.parse(ev.data);
        if (j.rtcode && j.rtcode !== '0000') return;
        apply(absorb(j));
      } catch (e) { /* 壞掉的一筆不值得把整條連線收掉 */ }
      stamp();
    });
    // 非交易時段：Worker 給一份快照就收線，我們安靜地退回慢速輪詢，不算失敗
    es.addEventListener('idle', () => {
      closeStream(false);
      state.sseFails = 0;
      stamp();
    });
    // 連線輪替（Worker 為了不撞免費方案的 CPU 上限，每 4 分鐘換一條）。
    // 這是**正常結束**，所以不退避、直接重連。
    es.addEventListener('bye', () => {
      clearWatch();
      if (state.es) { try { state.es.close(); } catch (e) { /* 已經關了 */ } state.es = null; }
      state.sseFails = 0;
      state.sseIds = '';
      setTimeout(() => openStream(), 120);
    });
    es.onerror = () => {
      // EventSource 自己也會重連，但它分不出「404」跟「網路抖一下」，
      // 而且重連期間畫面是停的。所以一律由我們接手：先退回輪詢再自己排重連。
      state.sseIds = '';
      dropStream('連線錯誤');
    };
  }

  /** 畫面上的代號換了一批（換頁）就重開連線，訂閱才會跟著換。 */
  function syncStream() {
    if (state.mode !== 'sse' && !state.es) { openStream(); return; }
    if (streamIds() !== state.sseIds) { state.sseIds = ''; openStream(); }
  }

  // ---------------------------------------------------------------- 上色
  /** 把抓回來的價格寫回畫面。
   *  只動 [data-live] 標記過的元素 —— 不做「猜哪個是價格」那種事。 */
  function paint() {
    const A = window.App;
    if (!A || !A.fmt) return 0;
    const f = A.fmt;
    let n = 0;
    document.querySelectorAll('[data-live][data-lc]').forEach(el => {
      const q = state.quotes[el.dataset.lc];
      if (!q) return;
      // ★ 2026-09-29：這張卡的「即時」關著就不動它（關掉＝靜態，見 setCard）
      const key = keyOf(el);
      if (key && !cardOn(key)) return;
      if (key && q.at && (!state.cardAt[key] || q.at > state.cardAt[key])) state.cardAt[key] = q.at;
      const kind = el.dataset.live;
      // 第一次改寫之前記下頁面原本的靜態值 —— 關掉「即時」時要退回它（盤後資料），不是停在最後一筆即時價
      if (el.dataset.lst === undefined) { el.dataset.lst = el.textContent; el.dataset.lstc = el.className; }
      let txt = null;
      if (kind === 'close' || kind === 'idx') {
        txt = q.price == null ? '—' : f.n(q.price, kind === 'idx' ? 0 : 2);
      } else if (kind === 'chg') {
        txt = q.chgPct == null ? '—' : f.pct(q.chgPct, 2);
        el.className = el.className.replace(/\b(up|down|flat)\b/g, '').trim() + ' ' + f.cls(q.chgPct);
      } else if (kind === 'vol') {
        txt = q.volume == null ? '—' : f.lot(q.volume);
      }
      if (txt === null || el.textContent === txt) return;
      el.textContent = txt;
      el.classList.remove('liveflash');
      void el.offsetWidth;              // 強制重排，動畫才會重播
      el.classList.add('liveflash');
      n++;
    });
    /* 改過畫面上的數字就吼一聲：正照著收盤／漲跌排序的表格要重排，
       不然表頭標著 ▲、那一欄卻不是排好的（Andy 2026-09-15）。
       非同步發，避免在 paint 的迴圈裡同步重畫整張表。 */
    if (n) setTimeout(() => window.dispatchEvent(new CustomEvent('tw:quotes', { detail: { n } })), 0);
    return n;
  }

  // ---------------------------------------------------------------- 狀態列
  /* ★ 2026-09-24（Andy：「即時 10:44 每分鐘（輪詢）」→「只留時間」）：
     畫面上只顯示報價時間（例如 `10:44`）；「即時／收盤」「每分鐘（輪詢）」「推送」「已停」這些
     **狀態文字一個字都沒刪，全部搬進 title**。那是「現在是不是即時、多久更新一次」的唯一線索
     （2026-09-23 夜盤出事時就是靠它判斷的），藏起來可以、刪掉不行。
     顏色（class）照舊分四種：live 盤中、ok 收盤、bad 有問題、off 還沒資料 —— 只剩時間之後，
     「出事了」要靠顏色一眼看出來，細節滑上去看。*/
  const hhmm = (ms) => new Date(ms)
    .toLocaleTimeString('zh-TW', { timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hour12: false });
  function stamp() {
    const q = Object.values(state.quotes)[0];
    const el = document.getElementById('liveState');
    if (!el) return;                    // 沒有狀態那顆（例如被別的版面拿掉）就安靜略過，不丟例外

    const intr = isIntraday();
    const way = state.mode === 'sse' ? '推送（SSE）'
      : !autoOn() ? '自動已關（這台瀏覽器的 localStorage 設了 tw.live.on=0）'
        : state.slow ? `連續 ${state.tries} 次抓不到，退避成每 ${secTxt(state.period)} 重試（輪詢）`
          : (intr ? '每 5 秒（輪詢）' : '每 30 分（輪詢）');
    const how = state.mode === 'sse'
      ? '推送（SSE）：跟代理保持一條連線，值一變就送過來（約 5 秒）。'
      : (state.sseGaveUp
        ? '輪詢：代理沒有推送功能（或推送預設關閉），用固定間隔去抓。'
        : '輪詢：目前用固定間隔去抓；推送連上之後會自動切過去。');
    let cls = 'off', txt = '—', tip;
    if (!proxy()) {
      tip = '未設定即時來源';
    } else if (!state.lastOk) {
      tip = state.lastErr ? '即時：' + state.lastErr : '即時：尚未取得';
      cls = state.lastErr ? 'bad' : 'off';
    } else if (Date.now() - state.lastOk > STALE_MS) {
      // 停了：畫面上留「最後一次拿到的時間」，顏色轉成警示，原因寫在提示裡
      txt = hhmm(state.lastOk);
      tip = '即時已停（' + Math.round((Date.now() - state.lastOk) / 60000) + ' 分鐘沒更新）'
        + (state.lastErr ? '：' + state.lastErr : '');
      cls = 'bad';
    } else {
      txt = q && q.time ? q.time.slice(0, 5) : hhmm(state.lastOk);
      tip = (intr ? '即時 ' : '收盤 ') + txt + '　' + way;
      cls = intr ? 'live' : 'ok';
      if (state.fresher) { tip = '有新資料（網站重新部署過），點一下重新載入　' + tip; cls = 'bad fresh'; }
    }
    if (state.lastErr && cls !== 'bad' && cls !== 'bad fresh') tip += '\n上一次錯誤：' + state.lastErr;
    el.textContent = txt;
    el.className = 'livestate ' + cls;
    el.title = tip + '\n自動更新：' + way + '\n' + how;
    /* ★ 2026-09-24 晚（Andy：「時間刪除」）：這顆從畫面上收起來了，同一串說明鏡射到標題下版號那行的提示，
       「有新資料」改成版號旁的一顆小鈕 —— 資訊與功能都還在，只是不佔頂欄。*/
    const asof = document.getElementById('asof');
    if (asof) { asof.dataset.live = '即時報價：' + tip + '\n自動更新：' + way; asof.title = (asof.dataset.fresh || '') + '\n\n' + asof.dataset.live; }
    const fb = document.getElementById('freshBtn');
    if (fb) fb.hidden = !state.fresher;
  }

  // ---------------------------------------------------------------- 一輪
  async function tick(manual) {
    if (state.busy) return;
    if (!permLive()) return;                       // 會員權限關掉即時：不打 mis（DECISIONS #288）
    if (manual) {
      // manual＝「再試一次」（以前是按「更新」鈕；鈕 2026-09-24 拿掉了，這條路留給 Live.tick(true) 呼叫端）。
      state.tries = 0; state.slow = false;
      if (!state.timer && autoOn()) reschedule();
      state.sseGaveUp = false; state.sseFails = 0; state.ssePaused = false;
      if (!state.es) openStream();
    }
    /* 盤前開的頁面，計時器排的是「盤後每 30 分」；過了 09:00 不重排的話，盤中也是 30 分鐘才跳一次。
       每一輪檢查一次「現在該用的間隔」跟排上去的一不一樣，不一樣就重排。*/
    if (state.timer && !state.slow && state.mode !== 'sse' && state.period !== intervalMs()) reschedule();
    // 分頁在背景就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    const codes = codesOnScreen(true);
    const fill = state.fillSent;                    // 這一輪塞了哪些補位代號（await 期間別人呼叫 codesOnScreen 也不會蓋掉這一份）
    state.busy = true; stamp();
    let tickOk = false;
    try {
      if (proxy() && codes.length) {
        const got = await fetchQuotes(codes, { prio: 0 });
        apply(got);
        state.lastOk = Date.now(); state.lastErr = ''; state.tries = 0;
        if (state.slow) { state.slow = false; reschedule(); }     // 通了 → 回到正常間隔
        /* 通知吃同一批報價的模組（livek.js 個股分 K、market3.js 大盤卡）：
           它們用 Live.raw() 拿原始那一列，不必各自再打一次 mis —— 這就是「一批查完」。*/
        /* ★ 2026-10-02：多帶 fill（這一輪塞進去的補位代號，DECISIONS #296）—— 總覽摘要卡靠它知道輪到哪一段、哪些代號問過了。*/
        tickOk = true;
        window.dispatchEvent(new CustomEvent('tw:live', { detail: { at: state.lastOk, codes: Object.keys(got), fill } }));
      } else if (!proxy()) {
        state.lastErr = '還沒設定代理網址';
      }
      /* 三張大盤圖現在自己有一組計時器（盤中 10 秒），不再寄生在這一輪。
         這裡只在「手動按更新」時順便叫它一次 —— 按了就該全部都新，包含那三張圖。
         之所以要拆開：以前掛在這裡，報價連續失敗三次把計時器關掉時，三張圖也跟著不動了。 */
      if (manual && window.Market3) { try { await window.Market3.refresh(true); } catch (e) { /* 圖壞掉不該影響報價 */ } }
    } catch (e) {
      state.tries++;
      state.lastErr = String(e.message || e).slice(0, 60);
      if (autoOn()) {
        // ★ 退避，不是停掉（見 BACKOFF_MAX 的註解）：每失敗一次間隔翻倍，通了立刻回到 5 秒
        state.slow = true; reschedule();
        if (state.tries >= MAX_FAILS) {
          state.lastErr = `連續 ${state.tries} 次抓不到，退避成每 ${secTxt(state.period)}自動重試：` + state.lastErr;
        }
      }
    } finally {
      /* 靜態 JSON 有沒有換新版（Actions 重新部署過）。
         ★ 每一輪都要檢查，不是只有手動那次 —— Andy 要的「盤後每 30 分鐘更新」指的是
           **資料**要變新，不是只有報價數字在跳。以前只在 manual 時檢查，
           等於開著的頁面永遠不會自己拿到 18:30 那輪跑完的新資料。
         ★ 2026-09-24（R6 審查）：以前這一行寫在上面抓報價的同一個 try 裡 —— 報價一丟錯（公司網路擋 workers.dev、
           Worker 掛了）就整段跳過，「有新資料」鈕永遠不會出現、盤後也不會自動重新載入。
           它跟報價是兩件不相干的事，所以搬到 finally：報價成功或失敗都照樣檢查（它自己有 try，失敗不會往外丟）。*/
      /* ★ 2026-09-29：盤中一輪變 5 秒之後，meta.json 不必每輪都問（部署一天才幾次）——
         手動、盤後（本來就 30 分鐘一輪）照舊每輪都比對；盤中最多一分鐘一次。*/
      if (manual || !isIntraday() || Date.now() - state.metaAt >= META_EVERY_MS) {
        state.metaAt = Date.now();
        try { await reloadIfRedeployed(manual); } catch (e) { /* 自己有 try；這層只是保險 */ }
      }
      state.busy = false; stamp(); stampCards();
      /* ★ 2026-10-02：每一輪（成功或失敗）都吼一聲。總覽摘要卡的「即時 HH:MM:SS」靠它在抓不到時轉成警示色 ——
         失敗的那幾輪沒有 tw:live，不吼的話卡上的時間會安靜地停住，看起來像一切正常（DECISIONS #296）。*/
      try { window.dispatchEvent(new CustomEvent('tw:livetick', { detail: { ok: tickOk, err: state.lastErr, at: state.lastOk } })); } catch (e) { /* 舊瀏覽器 */ }
    }
  }

  /** 比對 meta.json 的 `generated_at`，判斷 Actions 是不是重新部署過。
   *
   *  盤中不自動重載 —— reload 會把展開的列、勾選的族群、K 線縮放全部弄掉，
   *  而盤中價格本來就靠即時報價在更新，沒必要打斷正在看盤的人。
   *  改成把狀態那顆轉成警示色（提示寫「有新資料」），點那顆才真的載入
   *  （2026-09-24 以前是按「更新」鈕，鈕拿掉了）。
   *  盤後（以及 manual）就直接重載，那時打斷不了什麼。 */
  async function reloadIfRedeployed(manual) {
    try {
      const A = window.App;
      const cur = A && A.D && A.D.meta && A.D.meta.generated_at;
      const r = await fetch('data/meta.json?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return;
      const m = await r.json();
      if (!cur || !m.generated_at || m.generated_at === cur) { state.fresher = false; return; }
      if (manual || !isIntraday()) location.reload();
      else state.fresher = true;          // 盤中：先講一聲，不打斷
    } catch (e) { /* 抓不到就算了，不影響即時報價 */ }
  }

  function reschedule() {
    if (state.timer) clearInterval(state.timer);
    // SSE 活著的時候不是把輪詢關掉，而是放慢到五分鐘一次當對帳（見 MS_SAFETY）。
    // 失敗中：退避（5 秒 × 2ⁿ，封頂 5 分鐘），但不會比平常的間隔更密（盤後本來就 30 分鐘）。
    const ms = state.mode === 'sse' ? MS_SAFETY
      : state.slow ? Math.max(intervalMs(), backoffMs(state.tries)) : intervalMs();
    state.period = autoOn() ? ms : 0;
    state.timer = autoOn() ? setInterval(() => tick(false), ms) : null;
    stamp();
  }

  // ---------------------------------------------------------------- 卡片的「即時」開關與更新時間（2026-09-29）
  /* Andy：「可『即時』更新的圖表及數據多新增『即時』選項…回報多久會更新一次」。
   * 每張有盤中來源的卡片上放一顆「即時」＋一行最後更新時間（台北）：
   *   開（預設）＝盤中每 5 秒更新、盤後每 30 分鐘；關＝靜態（退回盤後資料、不再打端點）。
   * 哪些卡片有、哪些沒有、為什麼 —— 見 DECISIONS #277。
   *
   * ★ 為什麼掛載寫在這裡、不寫進各頁的 render：
   *   各頁（industry.js／watchpage.js／watchlists.js／market3.js／mobile3.js）的 render 會整塊 innerHTML 重畫，
   *   開關跟著被洗掉；在這裡用一張表＋MutationObserver 自動補回去，開關的長相、狀態、更新時間只有一份實作。*/
  const TPE_HMS = (() => {
    try { return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }); }
    catch (e) { return null; }
  })();
  /** 台北時間 HH:MM:SS（使用者電腦不一定在台北）。 */
  const hms = (ms) => TPE_HMS ? TPE_HMS.format(new Date(ms)) : new Date(ms).toTimeString().slice(0, 8);
  function secTxt(ms) { return ms >= 60000 ? Math.round(ms / 60000) + ' 分鐘' : Math.round(ms / 1000) + ' 秒'; }

  const cardMeta = {};   // 不走本檔報價的卡片（大盤三張圖）自己回報：key -> { at, err, every }
  /* 掛載表：key＝開關的名字；card＝卡片外框（帶 data-livekey，裡面的 [data-lc] 都歸它管）；
     at＝開關插在誰旁邊（沒有 at＝只標歸屬、不放鈕：手機總覽那條橫向自選清單放不下，開關在 #watch 頁）。*/
  const MOUNTS = [
    { key: 'stock', card: '#skChartCard', at: '#skPx [data-live="chg"]', pos: 'after' },
    { key: 'stock', card: '#mbHead', at: '#mbStar', pos: 'before', cls: 'mb' },
    { key: 'watch', card: '.wpcard', at: '.wphd .sp', pos: 'before' },
    { key: 'watch', card: '#wlPanel', at: '.wlhd .wlx', pos: 'before' },
    { key: 'watch', card: '#mbWatch' },
    { key: 'm3', card: '#m3Frame', at: '.m3-bar .howbtn[data-how="m3"]', pos: 'after' },
  ];
  const TG_NAME = { stock: '個股報價與分時', watch: '自選清單', m3: '大盤三張圖', ovs: '總覽摘要卡' };

  function injectCss() {
    if (document.getElementById('liveTgCss')) return;
    const st = document.createElement('style');
    st.id = 'liveTgCss';
    /* 顏色一律走主題變數（v4 三主題 × 深淺自動換色）；字級 ≥ 12px（手機v3 驗收的下限）。*/
    st.textContent = `
.livetg{display:inline-flex;align-items:center;gap:5px;flex:none;vertical-align:middle;margin-left:8px;white-space:nowrap}
.livetg-b{font:inherit;font-size:12px;line-height:1;min-height:24px;padding:0 9px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--ink-2);cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.livetg-b::before{content:'';width:7px;height:7px;border-radius:50%;background:currentColor;opacity:.45}
.livetg-b[aria-pressed="true"]{border-color:var(--rise);color:var(--rise)}
.livetg-b[aria-pressed="true"]::before{opacity:1}
.livetg-t{font-size:12px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.livetg.bad .livetg-t,.livetg.stale .livetg-t{color:var(--amber,var(--ink-2))}
/* ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #324）：鈕旁的「HH:MM:SS · 盤後／5秒」「靜態」「重試中」不再顯示。
   狀態改用鈕的顏色講（style_guide 原則 8「狀態用顏色不用文字」）：開＝紅框、關＝灰、抓不到／太久沒更新＝琥珀框；
   細節（最後更新時間、節奏、錯誤）本來就寫在鈕的滑鼠提示。.livetg-t 節點留著當機器讀數（驗收與 aria 用），畫面上藏起來。*/
.livetg .livetg-t{display:none!important}
.livetg.bad .livetg-b,.livetg.stale .livetg-b{border-color:var(--amber);color:var(--amber)}
.livetg.mb{margin:0;align-self:stretch}
.livetg.mb .livetg-b{flex-direction:column;justify-content:center;gap:2px;border-radius:0;border:0;border-left:1px solid var(--line);min-height:44px;padding:0 8px;font-size:12px}
.livetg.mb .livetg-b::before{display:none}
.livetg.mb .livetg-t{font-size:12px}
.livetg.mb .livetg-b[aria-pressed="true"] .livetg-l::before{content:'● '}
`;
    document.head.appendChild(st);
  }

  function makeToggle(key, cls) {
    const w = document.createElement('span');
    w.className = 'livetg' + (cls ? ' ' + cls : '');
    w.dataset.livekey = key;
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'livetg-b';
    const t = document.createElement('span'); t.className = 'livetg-t';
    if (cls === 'mb') {
      // 手機：一顆 44px 高的鈕，上面「即時」、下面時間（放在分頁列 ☆ 左邊，不讓報價列變高）
      const l = document.createElement('span'); l.className = 'livetg-l'; l.textContent = '即時';
      b.appendChild(l); b.appendChild(t);
    } else {
      b.textContent = '即時';
      w.appendChild(b); w.appendChild(t);
    }
    if (cls === 'mb') w.appendChild(b);
    b.addEventListener('click', (e) => { e.stopPropagation(); e.preventDefault(); setCard(key, !cardOn(key)); });
    return w;
  }

  function mountAll() {
    MOUNTS.forEach(sp => {
      document.querySelectorAll(sp.card).forEach(card => {
        if (card.dataset.livekey !== sp.key) card.dataset.livekey = sp.key;
        if (!sp.at || card.querySelector('.livetg')) return;
        const a = card.querySelector(sp.at);
        if (!a || !a.parentNode) return;
        const tg = makeToggle(sp.key, sp.cls);
        if (sp.pos === 'before') a.parentNode.insertBefore(tg, a);
        else a.parentNode.insertBefore(tg, a.nextSibling);
      });
    });
    stampCards();
  }

  /** 把每一顆開關的狀態與「最後更新時間」寫上去。每一輪報價、每次開關、每次掛載都會叫。 */
  function stampCards() {
    const intr = isIntraday();
    document.querySelectorAll('.livetg[data-livekey]').forEach(w => {
      const k = w.dataset.livekey, on = cardOn(k), meta = cardMeta[k] || {};
      const b = w.querySelector('.livetg-b'), t = w.querySelector('.livetg-t');
      if (!b || !t) return;
      const at = Math.max(state.cardAt[k] || 0, meta.at || 0);
      const every = meta.every || (intr ? MS_FAST : MS_AFTER);
      const name = TG_NAME[k] || '這張卡';
      const err = meta.err || ((k === 'stock' || k === 'watch') && state.slow ? state.lastErr : '');
      let txt, tip, cls = '';
      if (!on) {
        txt = '靜態'; cls = 'off';
        tip = `${name}：即時已關，停在盤後資料、不再打報價端點。\n按一下打開＝${meta.tip || '盤中每 5 秒更新'}；盤後每 30 分鐘。`;
      } else if (!at && err) {
        txt = '重試中'; cls = 'bad';
        tip = `${name}：還沒拿到即時報價（${err}）。失敗會自動退避重試（10、20、40…秒，最慢 5 分鐘一次）。`;
      } else if (!at) {
        txt = '—';
        tip = `${name}：即時開著，還沒拿到第一筆報價。`;
      } else {
        const stale = Date.now() - at > Math.max(every * 3, 20000);
        // meta.lbl／meta.tip：卡片裡各數字節奏不一樣時（大盤卡：台指期 15 秒，DECISIONS #299），卡片自己講清楚
        txt = hms(at) + (intr ? ' · ' + (meta.lbl || '5秒') : ' · 盤後');
        cls = err ? 'bad' : (stale ? 'stale' : '');
        tip = `${name}：最後更新 ${hms(at)}（台北時間）\n`
          + (intr ? (meta.tip || '盤中每 5 秒更新一次（證交所報價本身就是 5 秒一張快照）') : '現在不是盤中（現貨 09:00–13:30），盤後每 30 分鐘對一次')
          + (err ? `\n上一次抓失敗：${err}（自動退避重試中）` : '')
          + (stale && !err ? '\n⚠ 已經超過平常間隔很久沒有新資料' : '')
          + '\n按一下關掉＝靜態（退回盤後資料）。';
      }
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.title = tip;
      b.setAttribute('aria-label', `${name}即時更新：${on ? '開' : '關'}`);
      if (t.textContent !== txt) t.textContent = txt;
      t.title = tip;
      w.classList.toggle('off', cls === 'off');
      w.classList.toggle('bad', cls === 'bad');
      w.classList.toggle('stale', cls === 'stale');
    });
  }

  /** 開／關一張卡的即時。關＝那張卡裡被即時層改過的格子退回原本的靜態值。 */
  function setCard(k, on) {
    ls.set(KEY_CARD(k), on ? '1' : '0');
    if (!on) {
      document.querySelectorAll('[data-live][data-lc]').forEach(el => {
        if (keyOf(el) !== k || el.dataset.lst === undefined) return;
        el.textContent = el.dataset.lst; el.className = el.dataset.lstc || el.className;
        delete el.dataset.lst; delete el.dataset.lstc;
      });
    }
    try { window.dispatchEvent(new CustomEvent('tw:livecard', { detail: { key: k, on } })); } catch (e) { /* 舊瀏覽器 */ }
    stampCards();
    if (on) setTimeout(() => tick(false), 0);    // 打開就馬上抓一輪，不要等下一個 5 秒
  }

  // ---------------------------------------------------------------- 設定面板
  /* ★ 2026-09-24 整段刪除（Andy：「按鈕更新、設定 版都移除」）。原本面板裡有四樣東西：
       ① Worker 網址輸入框（存 localStorage['tw.live.proxy']）—— DEFAULT_PROXY 已經寫死正式的那台
       ② 「自動更新」勾選框（存 localStorage['tw.live.on']）—— 預設就是開；localStorage 設了 0 仍然尊重（驗收在用）
       ③ 「測試」鈕：打一次 /quote 與 /health，回報通不通、Worker 支不支援推送
       ④ 「儲存」鈕
     SSE 推送的開關本來就不在面板裡（localStorage['tw.sse']，見 sseAllowed）。*/

  // ---------------------------------------------------------------- 對外
  const Live = {
    tick,
    paint,
    proxy,                                     // market3.js／livek.js 共用同一組來源
    taifexProxy: () => TAIFEX_PROXY,            // 台指期優先走的 Deno 代理（market3.js 用）
    /* ★ 2026-09-21：對外開放這一支，給「即時資金去向」批次抓板塊成分股用。
       它要的不是「畫面上看得到的代號」（那是 codesOnScreen 的工作），
       而是一組指定的代號 —— 但 Worker 代理、上市上櫃判定（exch）、
       `z` 是 '-' 時的退位順序（normalise）這三件事必須共用，
       各寫一套的話盤中一定會有一邊拿到錯的價（2026-09-15 那個「一直在跌」的 bug）。
       MAX_CODES 一起送出去，呼叫端才知道一批最多能塞幾檔。*/
    fetchQuotes,
    MAX_CODES,
    get quotes() { return state.quotes; },
    get timerOn() { return !!state.timer; },   // 驗收用：自動更新到底有沒有在跑
    get periodMs() { return state.period; },   // 驗收用：計時器排的間隔（盤中 5000／盤後 1800000／退避 10000～300000）
    get mode() { return state.mode; },         // 驗收用：現在真的走推送還是輪詢
    get streamOn() { return !!state.es && state.mode === 'sse'; },
    get sseGaveUp() { return state.sseGaveUp; },
    get busy() { return state.busy; },
    get tries() { return state.tries; },       // 驗收用：連續失敗幾次（退避的依據）
    get reqs() { return state.reqs; },         // 驗收用：這個分頁總共打了幾次 /quote
    isIntraday,
    /* ---- 2026-09-29：每 5 秒＋卡片開關，給其他模組共用的介面 ---- */
    FAST_MS: MS_FAST,                          // 盤中節奏（族群即時模式、大盤卡、個股分 K 都用這一個數字）
    intervalMs,                                // 現在該用的間隔（盤中 5 秒／盤後 30 分鐘）
    /** 族群即時模式的計時器是固定 5 秒一跳；這支判斷「這一跳該不該真的去抓」：
     *  盤中一律要；盤後只有「還沒抓過」或「上次已經超過 30 分鐘」才抓 —— 盤後數字不會動，5 秒一跳是白打。*/
    due(lastAt) { return isIntraday() || !lastAt || Date.now() - lastAt >= MS_AFTER; },
    slot,                                      // 節流閥：打 mis 之前 await Live.slot(prio)
    /** 其他模組的錯誤退避：`if (Live.cooling('mud')) return;` 抓之前問；抓完 `Live.report('mud', 成功與否, 這一輪開始的時間)`。
     *  使用者重新打開即時時 `Live.report(key, true)` 清掉，第一輪不必等退避。*/
    cooling, report,
    get coolStats() { const o = {}; Object.keys(cool).forEach(k => { o[k] = { n: cool[k].n, waitMs: backoffMs(cool[k].n) }; }); return o; },
    get slotStats() { const now = Date.now(); return { recent: slotHist.filter(t => now - t < MIS_WINDOW_MS).length, queued: slotQ.length, max: MIS_MAX, windowMs: MIS_WINDOW_MS }; },
    cardOn, setCard, stampCards, mountAll, hms,
    /** 卡片登記「畫面上沒有格子、但我要」的代號（大盤卡登記 t00／o00）。
     *  codes 可以是陣列，或每一輪才問的函式（回陣列；看不到那張卡時回 []）。給 null／空陣列＝撤銷。
     *  ★ 2026-10-02（DECISIONS #296）：opts.fill＝true 是「補位」—— codes 必須是函式 fn(room)，
     *    room＝這一批還剩幾個空位；回傳的代號只在有空位時塞、**不會多打一個請求**、排在畫面代號後面。
     *    真的塞了哪幾檔，tw:live 的 detail.fill[key] 會告訴你（登記的人照它往前輪）。key 的「即時」開關關著就不塞。*/
    want(key, codes, opts) {
      if (opts && opts.fill) {
        if (typeof codes === 'function') state.fills[key] = codes; else delete state.fills[key];
        return;
      }
      if (typeof codes === 'function') state.wants[key] = codes;
      else if (codes && codes.length) state.wants[key] = codes.slice();
      else { delete state.wants[key]; delete state.fills[key]; }
    },
    /** mis 原始那一列（maxAge 毫秒內才回；沒有就 null）。個股分 K 與大盤卡用它，不另外打端點。 */
    raw(code, maxAge) { const r = state.raw[code]; return r && (!maxAge || Date.now() - r.at <= maxAge) ? r : null; },
    /** 不走本檔報價的卡片回報自己的更新時間／錯誤（大盤三張圖）。 */
    stampCard(key, meta) { cardMeta[key] = Object.assign({}, cardMeta[key] || {}, meta || {}); stampCards(); },
    start() {
      /* ★ 2026-09-29：卡片的「即時」開關自動掛載（各頁 render 重畫後自動補回，見 mountAll 的註解）。*/
      injectCss();
      mountAll();
      try {
        let mt = null;
        /* ★ 2026-10-02 卡頓（DECISIONS #284）：輪動時鐘的聲納圓圈（.rotping，每秒好幾顆、加一次拿一次）不會洗掉任何開關，
           整批都是它就不必重掛 —— 以前資金流向頁停著不動，光它就讓 mountAll＋stampCards 每 150ms 跑一輪。*/
        const pingOnly = (recs) => recs.every(r => { const ns = [...r.addedNodes, ...r.removedNodes];
          return ns.length > 0 && ns.every(n => n.classList && n.classList.contains('rotping')); });
        new MutationObserver((recs) => { if (mt || pingOnly(recs)) return; mt = setTimeout(() => { mt = null; mountAll(); }, 150); })
          .observe(document.body, { childList: true, subtree: true });
      } catch (e) { /* 沒有 MutationObserver 的瀏覽器：換頁時 hashchange 那一輪仍會掛 */ }
      /* ★ 2026-09-24：「更新」鈕與 ⚙ 設定面板拿掉了，這裡不再綁它們。
         狀態那顆只有在「有新資料」時可以點（重新載入），平常點了什麼都不做。
         ⚠ 每一個 getElementById 都要容忍拿到 null —— 版面以後再拿掉什麼，這裡都不准丟例外。*/
      const st = document.getElementById('liveState');
      if (st) st.addEventListener('click', () => { if (state.fresher) location.reload(); });
      const fb = document.getElementById('freshBtn');
      if (fb) fb.addEventListener('click', (e) => { e.stopPropagation(); location.reload(); });
      reschedule();
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          // 背景分頁不該一直佔著一條連線（跟輪詢在背景不跑是同一個道理）
          closeStream(true);
        } else {
          /* 切回前景＝使用者回來看了：以前「按更新重試」做的事改在這裡做 ——
             失敗計數歸零、放慢的間隔恢復、放棄的推送再試一次。*/
          state.ssePaused = false;
          state.tries = 0; state.sseGaveUp = false; state.sseFails = 0;
          if (state.slow) { state.slow = false; reschedule(); }
          // 先開推送、再補抓一輪（跟以前按「更新」時 tick(true) 裡的順序一樣）：
          // 推送的第一筆快照先到，輪詢那一輪再對帳，兩邊不會互相蓋掉對方剛寫上去的數字。
          openStream();     // 重連會拿到完整快照，剛好補回背景期間的變化
          tick(false);
        }
      });
      // 換頁之後畫面上的代號就換了一批，重抓一次讓新的那批也有即時價，
      // 並且把 SSE 的訂閱換成新的那一組（不換的話新頁面的格子永遠不會動）
      window.addEventListener('hashchange', () => setTimeout(() => { mountAll(); tick(false); syncStream(); }, 800));
      window.addEventListener('pagehide', () => closeStream(true));
      tick(false);
      openStream();
    },
  };

  window.Live = Live;
})();
