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
 */
(function () {
  'use strict';

  const KEY_PROXY = 'tw.live.proxy';   // Worker 網址（不是密鑰，可以放 localStorage）
  const KEY_ON = 'tw.live.on';         // 自動更新開關
  const MAX_CODES = 110;               // 實測一個請求 120 檔 OK，留一點邊際
  const MS_INTRADAY = 60 * 1000;       // 盤中：每分鐘
  const MS_AFTER = 30 * 60 * 1000;     // 盤後：每 30 分鐘
  const STALE_MS = 3 * 60 * 1000;      // 超過這麼久沒成功就把狀態標成「停了」
  // 連續失敗這麼多次就把自動輪詢**放慢**到 MS_SAFETY（5 分鐘）一次，成功就回到正常間隔。
  // 理由有兩個：(1) 公司網路可能整個擋掉 Worker，一直重試只會洗版 console；
  // (2) 打不通的端點每分鐘敲一次沒有意義。
  // ★ 2026-09-24 以前是「關掉，等使用者按『更新』」—— 那顆鈕拿掉之後就等於永久停擺，所以改成放慢。
  const MAX_FAILS = 3;

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
  };

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
  /** 掃畫面上有哪些代號要更新。這就是「只更新看得到的」的實作。 */
  function codesOnScreen() {
    const seen = [];
    document.querySelectorAll('[data-lc]').forEach(el => {
      const c = el.dataset.lc;
      if (c && seen.indexOf(c) < 0) seen.push(c);
    });
    return seen.slice(0, MAX_CODES);
  }

  /** 代號 → mis 的 ex_ch。t00 是加權指數；其餘靠 stocks.json 分上市上櫃，
   *  查不到就兩邊都要（多要一個不會錯，回應本來就只回有的那個）。 */
  function exch(code) {
    if (code === 't00') return ['tse_t00.tw'];
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
      time: at,                  // 這筆成交的時間（HH:MM:SS）
      date: m.d || '',
      at: Date.now(),
    };
  }

  async function fetchQuotes(codes) {
    const base = proxy();
    if (!base) throw new Error('還沒設定代理網址');
    if (!codes.length) return {};
    const ex = [];
    codes.forEach(c => exch(c).forEach(t => ex.push(t)));
    const url = base + '/quote?ex_ch=' + encodeURIComponent(ex.slice(0, MAX_CODES * 2).join('|'));
    const r = await fetch(url, { cache: 'no-store' });
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
    ((j && j.msgArray) || []).forEach(m => {
      const q = normalise(m);
      if (q.code) out[q.code] = q;
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
      const kind = el.dataset.live;
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
        : state.slow ? '連續抓不到，改成每 5 分鐘重試（輪詢）'
          : (intr ? '每分鐘（輪詢）' : '每 30 分（輪詢）');
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
  }

  // ---------------------------------------------------------------- 一輪
  async function tick(manual) {
    if (state.busy) return;
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
    const codes = codesOnScreen();
    state.busy = true; stamp();
    try {
      if (proxy() && codes.length) {
        apply(await fetchQuotes(codes));
        state.lastOk = Date.now(); state.lastErr = ''; state.tries = 0;
        if (state.slow) { state.slow = false; reschedule(); }     // 通了 → 回到正常間隔
      } else if (!proxy()) {
        state.lastErr = '還沒設定代理網址';
      }
      /* 三張大盤圖現在自己有一組計時器（盤中 10 秒），不再寄生在這一輪。
         這裡只在「手動按更新」時順便叫它一次 —— 按了就該全部都新，包含那三張圖。
         之所以要拆開：以前掛在這裡，報價連續失敗三次把計時器關掉時，三張圖也跟著不動了。 */
      if (manual && window.Market3) { try { await window.Market3.refresh(true); } catch (e) { /* 圖壞掉不該影響報價 */ } }
      // 靜態 JSON 有沒有換新版（Actions 重新部署過）。
      // ★ 每一輪都要檢查，不是只有手動那次 —— Andy 要的「盤後每 30 分鐘更新」指的是
      //   **資料**要變新，不是只有報價數字在跳。以前只在 manual 時檢查，
      //   等於開著的頁面永遠不會自己拿到 18:30 那輪跑完的新資料。
      await reloadIfRedeployed(manual);
    } catch (e) {
      state.tries++;
      state.lastErr = String(e.message || e).slice(0, 60);
      if (state.tries >= MAX_FAILS && autoOn()) {
        // ★ 放慢，不是停掉（見 MAX_FAILS 的註解）
        if (!state.slow) { state.slow = true; reschedule(); }
        state.lastErr = `連續 ${state.tries} 次抓不到，改成每 5 分鐘自動重試：` + state.lastErr;
      }
    } finally {
      state.busy = false; stamp();
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
    const ms = (state.mode === 'sse' || state.slow) ? MS_SAFETY : intervalMs();
    state.period = autoOn() ? ms : 0;
    state.timer = autoOn() ? setInterval(() => tick(false), ms) : null;
    stamp();
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
    get periodMs() { return state.period; },   // 驗收用：計時器排的間隔（盤中 60000／盤後 1800000／放慢 300000）
    get mode() { return state.mode; },         // 驗收用：現在真的走推送還是輪詢
    get streamOn() { return !!state.es && state.mode === 'sse'; },
    get sseGaveUp() { return state.sseGaveUp; },
    isIntraday,
    start() {
      /* ★ 2026-09-24：「更新」鈕與 ⚙ 設定面板拿掉了，這裡不再綁它們。
         狀態那顆只有在「有新資料」時可以點（重新載入），平常點了什麼都不做。
         ⚠ 每一個 getElementById 都要容忍拿到 null —— 版面以後再拿掉什麼，這裡都不准丟例外。*/
      const st = document.getElementById('liveState');
      if (st) st.addEventListener('click', () => { if (state.fresher) location.reload(); });
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
          tick(false);
          openStream();     // 重連會拿到完整快照，剛好補回背景期間的變化
        }
      });
      // 換頁之後畫面上的代號就換了一批，重抓一次讓新的那批也有即時價，
      // 並且把 SSE 的訂閱換成新的那一組（不換的話新頁面的格子永遠不會動）
      window.addEventListener('hashchange', () => setTimeout(() => { tick(false); syncStream(); }, 800));
      window.addEventListener('pagehide', () => closeStream(true));
      tick(false);
      openStream();
    },
  };

  window.Live = Live;
})();
