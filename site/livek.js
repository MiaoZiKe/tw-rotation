/* livek.js — 個股的當日即時分 K（5 秒 / 1 分 / 5 分）
 *
 * Andy 2026-09-15：「當我點擊一般股票時也能做到這樣的效果」
 *（指總覽那三張大盤圖的即時走勢），並追加「1 分 K 內的上下跳動都能出現會更好，就是 1 秒 K」。
 *
 * 為什麼最細只到 5 秒，不是 1 秒
 * ------------------------------
 * mis 的報價**本身**就是每 5 秒一張快照（回應裡自己寫 `userDelay: 5000`，
 * 證交所自己的網站也是每 5 秒問一次）。2026-09-15 10:25 實測：
 * 每 1.2 秒問一次、連問 14 次，撮合時間從 10:24:55 直接跳到 10:26:00 ——
 * 中間那一分鐘它沒有新東西可以給。問更密只是白打人家的端點。
 * 所以這裡是 **5 秒 K**，而且那是這條來源能給的最細顆粒。
 *
 * 為什麼要兩個來源
 * ----------------
 * 證交所只提供**大盤 / 櫃買 / 期貨 / 少數指數**的當日分時檔（mis_ohlc_*.txt），
 * **個股沒有**（2026-09-15 把 mis 網站的 53 個 JS chunk 全部掃過確認）。
 * 個股只有「當下這一筆報價」。所以：
 *
 *   早盤到 20 分鐘前  ← Yahoo 的 1 分 K（有量，但延遲 20 分鐘；
 *                        2026-09-15 10:22 實測它只給到 10:02）
 *   最近 20 分鐘到現在 ← mis 每 5 秒一筆，自己疊成 K 棒（即時）
 *
 * 兩邊接在一起才會是「從 09:00 到現在都完整，而且右緣是即時的」。
 * 只有 Yahoo 會慢 20 分鐘；只有 mis 則是「你幾點打開頁面，圖就從幾點開始」。
 *
 * 量的口徑（Andy 拍板：照畫，但要標註）
 * ------------------------------------
 * - Yahoo 那段的量偏低（2026-09-15 10:22 實測：Yahoo 累計 272 萬股、實際 510 萬股）
 * - mis 那段是用「累計成交張數的差值」回推每根的量，兩次輪詢之間的成交會被併進後面那根
 * 所以盤中量一律當估計值看，圖上會寫。收盤後由管線的正式資料覆蓋。
 *
 * 收集到的 5 秒序列會存在 localStorage（當天、當檔），
 * 這樣中途重新整理不會把早上盯著累積的細節丟掉。
 *
 * 非交易時段（Andy 2026-09-26：「為何這邊分 K 無法使用？」）
 * ------------------------------------------------------------
 * 以前只收「今天」的：週末、休市、開盤前打開個股頁，四個分 K 週期全是空的。
 * 現在今天沒有盤時，改畫「最近一個交易日」那一天的分 K（Yahoo 1 分 K，5 分／15 分由 1 分合成），
 * 圖上寫明「最近交易日 YYYY-MM-DD（非即時）」。
 * ★ 哪一天是「最近交易日」一律看資料本身帶的日期（Yahoo 每根 K 棒的時間戳、報價的撮合時間），
 *   不自己寫假日表、也不拿「現在幾月幾號」當交易日（CLAUDE.md 絕對不做的事 #3）。
 *   「今天」只拿來比對：資料裡有沒有「今天 09:00 以後」的成交 —— 有才算今天開盤了。
 * 5 秒 K 只有盤中開著頁面才收得到：那天有收過（localStorage 以那天的日期為鍵）就畫，
 * 沒有就先畫那天的 1 分 K，並寫明原因。盤中（今天有成交）的行為完全不變。
 */
(function () {
  'use strict';

  const POLL_MS = 5000;             // 跟 mis 自己的 userDelay 一致
  const KEY = (d, c) => `tw.livek.${d}.${c}`;
  const MAX_TICKS = 3600;           // 5 秒 × 3600 ＝ 5 小時，蓋得住整個交易日
  // （2026-09-29 起失敗改成退避，不再「連 3 次就停」，MAX_FAILS 拿掉；見 poll() 上面的註解）
  /* 由同一份 1 分 K（Yahoo）＋ 即時 tick 推出來的週期。
     Andy 2026-09-18：「1 5 15 分 K 都限制當天即可」—— 所以 15 分也放進來，
     不再由後端預先產出 60 天的 15 分 K（那是部署最慢的一塊，見 DECISIONS #156）。
     一次請求換三個週期，比分開打三次便宜。*/
  const TFS = { '5s': 5, '1m': 60, '5m': 300, '15m': 900 };
  /* ★ 2026-10-02 分時一路即時（Andy：「個股分時需要有即時走勢」，DECISIONS #287）。
     兩筆報價相隔超過這個秒數，就當成「中間沒在收」（頁面關著、分頁在背景、代理斷線）——
     那段的累計量差不知道該分給哪幾分鐘，不硬塞給後面那一根（會長出一根假的巨量），也不畫成實線。
     65 秒：正常是 5 秒一筆，live.js 失敗退避最長到 40 秒還算連續；超過一分鐘就一定有整分鐘沒看到。*/
  const GAP_S = 65;
  /* Yahoo 早盤盤中多久重抓一次。Yahoo 延遲約 20 分鐘，只在打開頁面時抓一次的話，
     「Yahoo 最後一根」到「打開頁面那一刻」之間那 20 分鐘永遠是空的；每 2 分鐘重抓，
     開著頁面約 20 分鐘後缺口就會被 Yahoo 補滿。打的是 Worker 的 /y（Yahoo），不是 mis，
     所以不增加證交所的請求。*/
  const HIST_REFRESH_MS = 2 * 60 * 1000;

  const state = {
    code: null, market: null, symbol: null,
    ticks: [],        // [{s: epoch 秒, p: 價, cv: 累計張數}]
    hist: [],         // Yahoo 的 1 分 K：[{s, d(台北日期), o, h, l, c, v(股)}]；可能含前幾個交易日（range=5d）
    offTicks: null,   // 非交易時段：最近交易日那天在 localStorage 裡收過的 5 秒序列 {date, t}
    histTried: false, histErr: '', histErrRaw: '',
    histDone: false,  // 這一檔的 Yahoo 早盤那一趟「回來了」（成功或失敗都算）；分時走勢用它判斷「真的沒資料」還是「還在抓」
    timer: null, busy: false, fails: 0,
    lastAt: 0, lastErr: '', prevClose: null, name: '',
    today: null,      // 今天這一根日 K（直接來自報價的 o/h/l/z/v，見 todayBar()）
    subs: [],
  };

  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗或滿了，忽略 */ } },
  };
  const num = (v) => { const n = parseFloat(v); return isFinite(n) ? n : null; };
  const proxy = () => (window.Live && window.Live.proxy ? window.Live.proxy() : '');

  function taipeiNow() {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  }
  function today() {
    return new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Taipei' });
  }
  /** 盤中？09:00–13:35（收盤 13:30，多留 5 分鐘讓尾盤撮合落地）。與 live.js 同一個判斷。 */
  function isIntraday() {
    const d = taipeiNow();
    const w = d.getDay();
    if (w === 0 || w === 6) return false;
    const m = d.getHours() * 60 + d.getMinutes();
    return m >= 9 * 60 && m <= 13 * 60 + 35;
  }

  // ---------------------------------------------------------------- Yahoo 早盤
  function yahooSymbol(code, market) {
    return code + ((market || '').toUpperCase() === 'TPEX' || (market || '').toUpperCase() === 'OTC' ? '.TWO' : '.TW');
  }

  /* 台北日期（YYYY-MM-DD）。s 是真正的 epoch 秒。*/
  const dateOf = (s) => new Date((s + 8 * 3600) * 1000).toISOString().slice(0, 10);
  /* 台北牆鐘的「第幾分鐘」（09:00 ＝ 540）。*/
  const minOf = (s) => Math.floor(((s + 8 * 3600) % 86400) / 60);

  /** 打一次 /y，回 {bars} 或 {err}。Worker 只允許白名單裡的 interval／range（1m＋1d／5d 都在裡面），
   *  這裡不動 Worker。*/
  async function fetchYahoo(base, range) {
    const r = await fetch(`${base}/y?symbol=${encodeURIComponent(state.symbol)}&interval=1m&range=${range}`,
                          { cache: 'no-store' });
    if (r.status === 404 || r.status === 400) return { err: 'NOYAHOO' };
    if (!r.ok) {
      /* Worker 把 Yahoo 的 404（「查無資料」—— 冷門股、或代號在 Yahoo 那邊沒有分 K）包成 502 回來，
         本體寫著 status:404。那不是「連不到」，是「真的沒有」，要分開講。*/
      let j = null; try { j = await r.json(); } catch (e) { /* 本體不是 JSON 就當一般錯誤 */ }
      if (j && j.status === 404) return { err: 'EMPTY' };
      return { err: '代理回 HTTP ' + r.status };
    }
    const j = await r.json();
    const res = ((j.chart || {}).result || [])[0];
    if (!res || !res.timestamp || !res.timestamp.length) return { err: 'EMPTY', res };
    const q = ((res.indicators || {}).quote || [])[0] || {};
    const out = [];
    res.timestamp.forEach((s, i) => {
      const c = num(q.close && q.close[i]);
      if (c === null) return;
      out.push({
        s, d: dateOf(s),
        o: num(q.open && q.open[i]) ?? c,
        h: num(q.high && q.high[i]) ?? c,
        l: num(q.low && q.low[i]) ?? c,
        c,
        v: num(q.volume && q.volume[i]) || 0,          // 股
      });
    });
    return out.length ? { bars: out, res } : { err: 'EMPTY', res };
  }

  let histAt = 0, histBusy = false;
  async function loadHistory() {
    state.histTried = true;
    histAt = Date.now();
    const base = proxy();
    if (!base) { state.histErr = '還沒設定即時來源'; return; }
    try {
      /* 先打 range=1d（盤中跟以前一模一樣）。裡面沒有「今天」的 K 棒（週末、休市、開盤前、
         或開盤頭 20 分鐘 Yahoo 還沒給）才補打 range=5d，找最近一個有資料的交易日。*/
      let got = await fetchYahoo(base, '1d');
      const day = today();
      if (!got.bars || !got.bars.some(b => b.d === day)) {
        const more = await fetchYahoo(base, '5d');
        if (more.bars) got = more;
        else if (!got.bars && more.err === 'EMPTY' && got.err !== 'NOYAHOO') got = more;
      }
      if (got.err) {
        state.histErr = got.err === 'EMPTY' ? 'EMPTY' : got.err;
        if (got.err !== 'NOYAHOO') state.hist = [];
        return;
      }
      state.hist = got.bars;
      if (state.prevClose == null && got.res) state.prevClose = num((got.res.meta || {}).chartPreviousClose);
      state.histErr = '';
    } catch (e) {
      state.histErrRaw = String(e.message || e).slice(0, 120);
      state.histErr = zhErr(e);
    }
  }
  /* ★ 2026-09-25（審查 R5）：以前把瀏覽器的原始錯誤直接印在畫面上 ——「早盤資料抓不到（Failed to fetch）」，
     中文句子中間夾一段英文。換成人話；原文留在 state.histErrRaw（驗收與除錯看得到，畫面不印）。*/
  function zhErr(e) {
    const m = String((e && (e.name + ' ' + e.message)) || e || '');
    if (/abort|timeout|timed out/i.test(m)) return '連 Yahoo 逾時';
    if (/failed to fetch|networkerror|load failed|network|cors/i.test(m)) return '連不到分 K 來源';
    if (/json|unexpected token|syntax/i.test(m)) return 'Yahoo 回來的格式看不懂';
    return '抓取失敗';
  }

  /* 盤中重抓 Yahoo（只抓 range=1d，今天那段）。失敗就留著舊的，不清空 —— 已經畫出來的早盤不該因為一次失敗消失。*/
  async function refreshHist() {
    if (histBusy || !state.histDone || !isIntraday()) return;
    if (Date.now() - histAt < HIST_REFRESH_MS) return;
    const base = proxy(); if (!base) return;
    histBusy = true; histAt = Date.now();
    const code = state.code;
    try {
      const got = await fetchYahoo(base, '1d');
      const day = today();
      if (state.code === code && got.bars && got.bars.some(b => b.d === day)) {
        state.hist = state.hist.filter(b => b.d !== day).concat(got.bars.filter(b => b.d === day));
        state.histRefreshes = (state.histRefreshes || 0) + 1;
        emit();
      }
    } catch (e) { /* 下一輪再試 */ } finally { histBusy = false; }
  }

  // ---------------------------------------------------------------- mis 即時
  function exch(code, market) {
    const mk = (market || '').toUpperCase();
    if (mk === 'TPEX' || mk === 'OTC') return 'otc_' + code + '.tw';
    if (mk === 'TWSE' || mk === 'TSE') return 'tse_' + code + '.tw';
    return 'tse_' + code + '.tw|otc_' + code + '.tw';
  }

  /* ★ 2026-09-29：跟 live.js 共用同一批報價，不再各打各的。
     改前：個股頁上 live.js 每分鐘打一次 /quote（含這一檔）、這裡每 5 秒再打一次同一檔 —— 同一檔問兩次。
     改後：live.js 盤中也是每 5 秒一批（畫面上所有代號併成一個請求），這一檔一定在那一批裡，
     所以這裡先看 Live.raw()：5.5 秒內有新鮮的那一列就直接用；沒有（live.js 那一輪失敗、或還沒跑到）
     才自己打一次，而且要排 live.js 的節流閥（每 5 秒最多 3 個請求，見 live.js 檔頭）。
     失敗也不再是「連 3 次就停」—— 那會讓分時尾巴整天不動 —— 改成跟 live.js 一樣退避（10、20、40…秒）。*/
  const RAW_FRESH_MS = 5500;
  const cardOn = () => !window.Live || !window.Live.cardOn || window.Live.cardOn('stock');
  let nextTry = 0;                                  // 退避：這個時間之前不自己打端點
  let lastRawAt = 0;                                // 上一次吃進來的那一列是什麼時候抓的（同一列不吃兩次）
  function takeRaw() {
    const r = window.Live && window.Live.raw ? window.Live.raw(state.code, RAW_FRESH_MS) : null;
    if (!r) return false;
    if (r.at <= lastRawAt) return true;             // 這一列已經吃過了，也不用自己再打
    lastRawAt = r.at;
    pushTick(r.m);
    state.lastAt = Date.now(); state.lastErr = ''; state.fails = 0; nextTry = 0;
    emit();
    return true;
  }
  async function poll() {
    if (state.busy || !state.code) return;
    if (document.hidden) return;                    // 背景分頁不要一直打端點
    if (!cardOn()) return;                          // 個股卡的「即時」關著＝靜態
    refreshHist();                                  // 不等它；Yahoo 回來自己 emit
    if (takeRaw()) return;                          // live.js 這一輪已經問過這一檔
    if (Date.now() < nextTry) return;               // 退避中
    const base = proxy();
    if (!base) { state.lastErr = '還沒設定即時來源'; return; }
    state.busy = true;
    try {
      const url = base + '/quote?ex_ch=' + encodeURIComponent(exch(state.code, state.market));
      if (window.Live && window.Live.slot) await window.Live.slot(0);
      if (!(window.TwLive && window.TwLive.canLive())) throw new Error('即時已關閉');   // 2026-10-08：排隊期間站主或管理員登出 → 不打
      const r = await fetch(url, { cache: 'no-store' });
      if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
      const j = await r.json();
      const m = (j.msgArray || [])[0];
      if (!m) throw new Error('沒有這一檔的報價');
      pushTick(m);
      state.lastAt = Date.now(); state.lastErr = ''; state.fails = 0; nextTry = 0;
      if (window.Live && window.Live.stampCard) window.Live.stampCard('stock', { at: state.lastAt });
      emit();
    } catch (e) {
      state.fails++;
      // 自己丟的錯（代理回 HTTP xxx、沒有這一檔的報價）本來就是中文；瀏覽器丟的英文換成人話
      state.lastErr = /[一-鿿]/.test(String(e.message || '')) ? String(e.message).slice(0, 60) : zhErr(e).replace('Yahoo', '即時報價');
      // 退避：5 秒 × 2ⁿ（10、20、40…秒），封頂 5 分鐘（打不通就別一直洗 console，但也不永久停）
      nextTry = Date.now() + Math.min(5 * 60 * 1000, POLL_MS * Math.pow(2, state.fails));
    } finally {
      state.busy = false;
    }
  }
  // live.js 那一批一回來就吃（不必等自己的 5 秒計時器，兩邊節奏才會對齊、不會慢半拍）
  window.addEventListener('tw:live', () => { if (state.code && state.timer && cardOn()) takeRaw(); });
  // 個股卡的「即時」開關：關＝停掉輪詢；開＝重新排上（盤中才排）
  window.addEventListener('tw:livecard', (e) => {
    if (!e.detail || e.detail.key !== 'stock' || !state.code) return;
    if (e.detail.on) { startTimer(); poll(); } else stopTimer();
  });

  /** 一筆報價 → 一個 tick。價格的退位順序跟 live.js 一致（z → trade.z → 買價 → 開盤 → 昨收）。 */
  function pushTick(m) {
    const tr = m.trade || {};
    let p = num(m.z);
    let ts = m.tlong ? Math.floor(num(m.tlong) / 1000) : null;
    if (p === null) {
      const tz = num(tr.z);
      if (tz !== null) p = tz;
    }
    if (p === null && m.b) p = num(String(m.b).split('_')[0]);
    if (p === null) p = num(m.o);
    if (p === null) p = num(m.y);
    if (p === null) return;
    if (ts === null) ts = Math.floor(Date.now() / 1000);
    state.name = m.n || state.name;
    if (state.prevClose == null) state.prevClose = num(m.y);
    const cv = num(m.v) || 0;                        // 累計成交張數
    /* 今天這一根日 K。
       Andy 2026-09-15：「為何個股會是 9/14，而非 9/15呢? 我的目的就是要即時訊息」——
       個股頁的日線來自資料湖，而資料湖今天這一筆要等 15:30 那輪管線才會寫進去，
       所以盤中打開個股頁，最後一根永遠是昨天。
       但報價本身就帶著今天的開高低收與累計量（o/h/l/z、v），拿來當「今天這根還沒收的日 K」剛剛好。 */
    const d8 = String(m.d || '').trim();
    if (d8.length === 8) {
      const o = num(m.o), hi = num(m.h), lo = num(m.l);
      state.today = {
        date: `${d8.slice(0, 4)}-${d8.slice(4, 6)}-${d8.slice(6)}`,
        o: o == null ? p : o,
        h: hi == null ? p : Math.max(hi, p),
        l: lo == null ? p : Math.min(lo, p),
        c: p,
        v: cv * 1000,                                // 張 → 股，跟日線其他地方同口徑
        prev: num(m.y),
      };
    }
    const last = state.ticks[state.ticks.length - 1];
    /* q＝「這一筆是什麼時候收到的」（本機時鐘）。冷門股沒成交時撮合時間不動、ts 一直是同一個值，
       只看 ts 會誤以為那幾分鐘「沒在收」而畫成等待資料；有 q 才知道其實一直開著、只是沒成交。*/
    const q = Math.floor(Date.now() / 1000);
    // 同一個 5 秒格只留最後一筆（報價沒動的時候不要疊出一堆一樣的點）
    if (last && Math.floor(last.s / 5) === Math.floor(ts / 5)) {
      last.s = ts; last.p = p; last.cv = cv; last.q = q;
    } else {
      state.ticks.push({ s: ts, p, cv, q });
      if (state.ticks.length > MAX_TICKS) state.ticks.splice(0, state.ticks.length - MAX_TICKS);
    }
    save();
  }

  /* 隔天清掉（2026-10-02，DECISIONS #287）：今天真的開盤了（有今天 09:00 以後的報價）才把「今天以前」的 tw.livek.* 全刪。
     不在開盤前刪 —— 週末／開盤前要靠上一個交易日存的 5 秒序列畫「最近交易日」（2026-09-26 那條）。
     一頁只刪一次。*/
  let pruned = false;
  function pruneOld(day) {
    if (pruned) return;
    if (!state.ticks.some(t => dateOf(t.s) === day && minOf(t.s) >= 9 * 60)) return;
    pruned = true;
    try {
      const old = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i), m = /^tw\.livek\.(\d{4}-\d\d-\d\d)\./.exec(k || '');
        if (m && m[1] < day) old.push(k);
      }
      old.forEach(k => localStorage.removeItem(k));
    } catch (e) { /* 私密視窗，忽略 */ }
  }
  function save() {
    if (!state.code) return;
    pruneOld(today());
    /* 只存「今天」的 tick。週末打開頁面時報價回的是上一個交易日收盤那一筆（撮合時間是那天），
       那一筆不屬於今天，存進今天的鍵只是垃圾；更不能存進那天的鍵 —— 會把那天盤中收的整串 5 秒 K 蓋掉。*/
    const day = today();
    ls.set(KEY(day, state.code), JSON.stringify({
      t: state.ticks.filter(t => dateOf(t.s) === day), y: state.prevClose, n: state.name, d: state.today,
    }));
  }
  function load() {
    try {
      const raw = ls.get(KEY(today(), state.code));
      if (!raw) return;
      const o = JSON.parse(raw);
      if (Array.isArray(o.t)) state.ticks = o.t;
      if (o.d) state.today = o.d;
      if (state.prevClose == null) state.prevClose = o.y ?? null;
      state.name = state.name || o.n || '';
    } catch (e) { /* 壞掉就當沒有 */ }
  }

  // ---------------------------------------------------------------- 哪一天
  /** 今天有沒有盤：資料裡有「今天」的 Yahoo K 棒，或有「今天 09:00 以後」撮合的報價。
   *  ⚠ 不看星期幾、不看假日表 —— 看資料。開盤前的試撮（09:00 以前）不算開盤。*/
  function todayLive() {
    const day = today();
    if (state.hist.some(b => b.d === day)) return true;
    return state.ticks.some(t => dateOf(t.s) === day && minOf(t.s) >= 9 * 60);
  }
  /** 要畫哪一天：{date, live}。
   *  live＝今天有盤（行為跟以前一模一樣）；否則 date＝資料裡最新的那個交易日（Yahoo 的 K 棒或收到的報價）。*/
  function session() {
    if (todayLive()) return { date: today(), live: true };
    let best = null;
    for (const b of state.hist) if (!best || b.d > best) best = b.d;
    // 09:00 以前的報價是試撮，不代表那天開盤了（開盤前打開頁面，不可以把「今天」當成最近交易日）
    for (const t of state.ticks) { if (minOf(t.s) < 9 * 60) continue; const d = dateOf(t.s); if (!best || d > best) best = d; }
    return { date: best, live: false };
  }
  /** 非交易時段：某一天的 5 秒序列 ＝ 這次收到的（同一天的）＋ 那天盤中存進 localStorage 的。*/
  function ticksOf(date) {
    let stored = [];
    if (date !== today()) {
      if (!state.offTicks || state.offTicks.date !== date || state.offTicks.code !== state.code) {
        let t = [];
        try { const o = JSON.parse(ls.get(KEY(date, state.code)) || 'null'); if (o && Array.isArray(o.t)) t = o.t; } catch (e) { /* 壞掉就當沒有 */ }
        state.offTicks = { date, code: state.code, t };
      }
      stored = state.offTicks.t;
    }
    const seen = new Map();
    stored.concat(state.ticks).forEach(t => { if (t && dateOf(t.s) === date) seen.set(Math.floor(t.s / 5), t); });
    return [...seen.values()].sort((a, b) => a.s - b.s);
  }

  // ---------------------------------------------------------------- 合成 K 棒
  /** 自己收集的 tick → N 秒 K。
   *  開＝前一根的收（連續盤），量＝累計張數的差值 × 1000（換成股，跟個股頁其他地方同口徑）。
   *  list 不給就用這次收到的全部（盤中，跟以前一樣）。*/
  function barsFromTicks(sec, sinceSec, list) {
    const out = []; let cur = null, key = null, prevClose = null, prevCv = null;
    for (const t of (list || state.ticks)) {
      if (sinceSec != null && t.s < sinceSec) { prevCv = t.cv; prevClose = t.p; continue; }
      const k = Math.floor(t.s / sec);
      const dv = (prevCv == null || t.cv < prevCv) ? 0 : (t.cv - prevCv) * 1000;
      prevCv = t.cv;
      if (k !== key) {
        if (cur) { out.push(cur); prevClose = cur[4]; }
        key = k;
        const o = prevClose == null ? t.p : prevClose;
        cur = [k * sec + 8 * 3600, o, Math.max(o, t.p), Math.min(o, t.p), t.p, dv];
      } else {
        cur[2] = Math.max(cur[2], t.p); cur[3] = Math.min(cur[3], t.p);
        cur[4] = t.p; cur[5] += dv;
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  /** Yahoo 的 1 分 K → 我們的形狀（時間一律 +8 小時，跟 chart.js 的 fmtTime 對齊）。
   *  只取 date 那一天（range=5d 會帶前幾天的）。*/
  function barsFromHist(sec, untilSec, date) {
    const out = []; let cur = null, key = null;
    for (const b of state.hist) {
      if (b.d !== date) continue;
      if (untilSec != null && b.s >= untilSec) break;
      const k = Math.floor(b.s / sec);
      if (k !== key) {
        if (cur) out.push(cur);
        key = k;
        cur = [k * sec + 8 * 3600, b.o, b.h, b.l, b.c, b.v];
      } else {
        cur[2] = Math.max(cur[2], b.h); cur[3] = Math.min(cur[3], b.l);
        cur[4] = b.c; cur[5] += b.v;
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  /** 頭（Yahoo）接尾巴（tick），尾巴第一根用頭最後一根的收盤當開盤，接起來才連續。*/
  function join(head, tail) {
    if (!head.length) return tail;
    if (!tail.length) return head;
    tail[0][1] = head[head.length - 1][4];
    tail[0][2] = Math.max(tail[0][2], tail[0][1]);
    tail[0][3] = Math.min(tail[0][3], tail[0][1]);
    return head.concat(tail);
  }

  /** 非交易時段的分 K：那一天的 Yahoo 1 分 K（5／15 分由它合成），
   *  報價收到的只拿來補「Yahoo 最後一根之後」的部分 —— 那天的 Yahoo 已經是完整的，不必讓 tick 蓋掉它
   *  （尤其收盤那一筆報價的量是 0，蓋掉會把尾盤集合競價的量弄丟）。*/
  function offBars(sec, date) {
    const head = barsFromHist(sec, null, date);
    const dayTicks = ticksOf(date);
    if (!head.length) return barsFromTicks(sec, null, dayTicks);
    const lastS = head[head.length - 1][0] - 8 * 3600;
    return join(head, barsFromTicks(sec, lastS + sec, dayTicks));
  }

  /** 對外：某個週期的 K 棒。
   *  盤中（今天有盤）：5 秒只用自己收的；1／5／15 分是「Yahoo 早盤 ＋ 自己收的尾巴」—— 跟以前一模一樣。
   *  非交易時段：最近交易日那一天的（見 offBars）；5 秒那天沒收過就先給 1 分 K（drawnTf 會說）。*/
  function bars(tf) {
    const sec = TFS[tf];
    if (!sec) return [];
    const ses = session();
    if (!ses.live) {
      if (!ses.date) return [];
      if (tf === '5s') {
        const tk = ticksOf(ses.date);
        return tk.length >= 2 ? barsFromTicks(5, null, tk) : offBars(60, ses.date);
      }
      return offBars(sec, ses.date);
    }
    if (tf === '5s') return barsFromTicks(5);
    const firstTick = state.ticks.length ? state.ticks[0].s : null;
    // 接縫：自己有資料的第一格開始用自己的，之前的用 Yahoo（同一格不要兩邊都畫）
    const seam = firstTick == null ? null : Math.floor(firstTick / sec) * sec;
    return join(barsFromHist(sec, seam, ses.date), barsFromTicks(sec, seam));
  }
  /** ★ 2026-10-02 分時用的「今天每分鐘一根」（DECISIONS #287）。只在今天有盤時回東西，否則 null。
   *
   *  為什麼不直接用 bars('1m')：bars() 的接縫是「這次收到的第一筆報價」，前後各取一邊 ——
   *    · 早上 09:30 開過一下、10:26 再打開：localStorage 裡 09:30 那幾筆讓接縫落在 09:30，
   *      09:31～10:26 Yahoo 明明有，卻被丟掉、畫成一條直線；
   *    · Yahoo 最後一根（例 10:06）到第一筆報價（10:26）之間，join() 直接把兩點連起來，看起來像走勢，其實是空的。
   *  這裡改成逐分鐘決定：
   *    ① 那一分鐘的報價是「從上一分鐘就一直在收」（full：這一分鐘的第一筆跟上一筆連得上）→ 用報價疊的
   *      （即時、量是累計量差分，比 Yahoo 準）；
   *    ② 否則 Yahoo 有那一分鐘 → 用 Yahoo；
   *    ③ 都沒有、但報價有半分鐘（剛打開頁面那一分鐘）→ 用報價。
   *  ⚠ full 只看「連得上」，不看「這一分鐘頭幾秒就收到」：剛打開頁面那一分鐘、或盤後打開時收到的那一筆收盤價，
   *    前面那段的成交量根本沒看到（第一筆沒有上一筆可以相減，量是 0）。這種半分鐘讓 Yahoo 優先 ——
   *    不然 13:30 那根尾盤集合競價的大量會被一筆量 0 的收盤報價蓋掉（offBars 那段講過同一件事）。
   *  兩邊都沒涵蓋到的分鐘＝缺口（gaps），交給 TickChart 畫虛線、標「此段等待資料」，不准畫成實線冒充走勢。
   *  開盤頭 20 分鐘 Yahoo 還沒有今天的 K 棒時，09:00 到第一根之間也是缺口（lead；左邊沒有點可以連，只標字不畫虛線）。
   *  回 {bars:[[epoch+8h, o, h, l, c, 量(股)]], src:['yahoo'|'live'...]（每一根是哪裡來的）,
   *      gaps:[[起分鐘, 迄分鐘, 種類]]（epoch+8h，含頭含尾；種類 'lead'＝開盤到第一根、'open'＝打開頁面之前、'idle'＝打開之後沒收到）,
   *      segs:[{k:'yahoo'|'live'|'gap', a, b, why}]（照時間排好，說明文字用）,
   *      yahoo:[首, 末]|null, live:[首, 末]|null（即時疊出來的那段，epoch+8h）, ticks: 筆數, yahooWait: Yahoo 還可能追上來}。*/
  function minuteSeries() {
    const ses = session();
    if (!ses.live || !ses.date) return null;
    const day = ses.date;
    const day0 = Date.parse(day + 'T00:00:00Z') / 1000 - 8 * 3600;     // 台北那天 00:00 的真 epoch
    const OPEN = 9 * 60, CLOSE = 13 * 60 + 30;
    const K_OPEN = day0 / 60 + OPEN;                                    // 09:00 的分鐘鍵
    const mOf = (k) => k - day0 / 60;                                   // 分鐘鍵 → 當天第幾分鐘
    const T = (k) => k * 60 + 8 * 3600;                                 // 分鐘鍵 → 圖上的時間（epoch+8h）
    // Yahoo
    const yb = new Map();
    for (const b of state.hist) if (b.d === day) yb.set(Math.floor(b.s / 60), b);
    const yKeys = [...yb.keys()].sort((a, b) => a - b);
    const yFirst = yKeys.length ? yKeys[0] : null, yLast = yKeys.length ? yKeys[yKeys.length - 1] : null;
    // 報價 → 每分鐘一桶；同時記下「有在收」的時段（runs）
    const tk = state.ticks.filter(t => dateOf(t.s) === day).sort((a, b) => a.s - b.s);
    const tb = new Map(), runs = [];
    let prev = null, run = null;
    for (const t of tk) {
      const pEnd = prev ? Math.max(prev.s, prev.q || 0) : null;
      const cont = prev != null && t.s - pEnd <= GAP_S;
      const dv = cont && t.cv >= prev.cv ? (t.cv - prev.cv) * 1000 : 0;
      if (!cont || !run) { run = { a: t.s, b: Math.max(t.s, t.q || 0) }; runs.push(run); }
      else run.b = Math.max(run.b, t.s, t.q || 0);
      const k = Math.floor(t.s / 60);
      let c = tb.get(k);
      if (!c) {
        const o = cont ? prev.p : t.p;
        c = { o, h: Math.max(o, t.p), l: Math.min(o, t.p), c: t.p, v: dv, full: cont };
        tb.set(k, c);
      } else {
        c.h = Math.max(c.h, t.p); c.l = Math.min(c.l, t.p); c.c = t.p; c.v += dv;
      }
      prev = t;
    }
    // 逐分鐘挑來源
    const keys = [...new Set(yKeys.concat([...tb.keys()]))].sort((a, b) => a - b);
    const out = [], src = []; let liveA = null, liveB = null;
    for (const k of keys) {
      const m = mOf(k); if (m < OPEN || m > CLOSE) continue;
      const t = tb.get(k), y = yb.get(k);
      if (t && (t.full || !y)) {
        out.push([T(k), t.o, t.h, t.l, t.c, t.v]); src.push('live');
        if (liveA == null) liveA = k; liveB = k;
      } else if (y) { out.push([T(k), y.o, y.h, y.l, y.c, y.v]); src.push('yahoo'); }
    }
    const firstRun = runs.length ? Math.floor(runs[0].a / 60) : null;
    // 缺口：第一根到最後一根之間，Yahoo 跟報價都沒涵蓋到的分鐘
    const covered = (k) => (yFirst != null && k >= Math.min(yFirst, K_OPEN) && k <= yLast)
      || runs.some(r => k >= Math.floor(r.a / 60) && k <= Math.floor(r.b / 60));
    const gaps = [];
    if (out.length >= 2) {
      const k0 = (out[0][0] - 8 * 3600) / 60, k1 = (out[out.length - 1][0] - 8 * 3600) / 60;
      let g = null;
      for (let k = k0 + 1; k < k1; k++) {
        if (!covered(k)) {
          if (!g) { g = [k, k, firstRun != null && k < firstRun ? 'open' : 'idle']; gaps.push(g); } else g[1] = k;
        } else g = null;
      }
    }
    // 開盤到第一根：Yahoo 還沒有今天的 K 棒（開盤頭 20 分鐘），09:00～第一根之前也是空的
    if (out.length && yFirst == null) {
      const k0 = (out[0][0] - 8 * 3600) / 60;
      if (k0 > K_OPEN) gaps.unshift([K_OPEN, k0 - 1, 'lead']);
    }
    /* Yahoo 還會不會追上來：Yahoo 回「這一檔真的沒有分 K」（EMPTY）或 Worker 舊版（NOYAHOO）就不會；
       其他（還沒抓、網路失敗、單純延遲）盤中每 2 分鐘還會再試（refreshHist）。*/
    const yahooWait = !(state.histErr === 'EMPTY' && yFirst == null) && state.histErr !== 'NOYAHOO' && !!proxy();
    // 說明用的分段：連續、同來源的併成一段，缺口插在中間
    const segs = [];
    out.forEach((x, i) => {
      const k = (x[0] - 8 * 3600) / 60, last = segs[segs.length - 1];
      const brk = gaps.some(g => g[0] > (last ? last.b : -1) && g[1] < k);
      if (last && last.k === src[i] && !brk) last.b = k; else segs.push({ k: src[i], a: k, b: k });
    });
    gaps.forEach(g => segs.push({ k: 'gap', a: g[0], b: g[1], why: g[2] }));
    segs.sort((p, q) => p.a - q.a);
    return {
      bars: out, src, gaps: gaps.map(g => [T(g[0]), T(g[1]), g[2]]),
      segs: segs.map(sg => ({ k: sg.k, a: T(sg.a), b: T(sg.b), why: sg.why })),
      yahoo: yFirst != null ? [T(yFirst), T(yLast)] : null,
      live: liveA != null ? [T(liveA), T(liveB)] : null,
      ticks: tk.length, date: day, yahooWait,
    };
  }

  /** 這個週期實際畫的是哪一個週期（只有「非交易時段、那天沒收過 5 秒」會回 1m）。*/
  function drawnTf(tf) {
    const ses = session();
    if (tf === '5s' && !ses.live && ses.date && ticksOf(ses.date).length < 2) return '1m';
    return tf;
  }
  /** 非交易時段畫的那一天（YYYY-MM-DD）；盤中或完全沒資料回 null。*/
  function offDay() { const s = session(); return s.live ? null : s.date; }

  const TFZ = { '5s': '5 秒', '1m': '1 分', '5m': '5 分', '15m': '15 分' };
  /** 這個週期的資料是哪裡來的，畫面上要講清楚。 */
  function sourceNote(tf) {
    const ses = session();
    if (!ses.live) {
      const nh = ses.date ? state.hist.filter(b => b.d === ses.date).length : 0;
      /* 有日期但 Yahoo 是「連不到」（不是「沒有」）：照舊的說法往下走 —— industry.js 會據此先退回
         有資料的週期（審查 R5-6），這裡不要把網路問題講成「沒有資料」。*/
      const netErr = !nh && state.histErr && state.histErr !== 'EMPTY';
      // 報價比 Yahoo 先回來（週末那筆是上一交易日收盤）：Yahoo 還沒回之前不要先講「沒有分 K」
      if (!nh && !state.histTried && proxy()) return '正在抓最近交易日的分 K…';
      if (ses.date && !netErr) {
        const head = `最近交易日 ${ses.date}（非即時）`;
        const n = ticksOf(ses.date).length;
        if (tf === '5s' && n >= 2) return `${head}：那天盤中收集的 ${n} 筆，開盤後自動換回即時。`;
        if (!nh) {
          return n >= 2
            ? `${head}：那天盤中收集的 ${n} 筆報價`
            : `最近交易日（${ses.date}）也沒有分 K 資料`;
        }
        if (tf === '5s') return `${head}：先顯示最近交易日 1 分 K`;
        return `${head}，開盤後自動換回即時。`;
      }
      if (!state.histTried && proxy()) return '正在抓最近交易日的分 K…';
      if (state.histErr === 'EMPTY') return '最近交易日也沒有分 K 資料';
    }
    const n = state.ticks.length;
    if (tf === '5s') {
      return n < 2
        ? '5 秒 K 自打開本頁起收集'
        : `5 秒 K：${n} 筆`;
    }
    const h = state.hist.filter(b => b.d === ses.date).length;
    if (!h && state.histErr === 'NOYAHOO') {
      return '早盤資料暫時取不到';
    }
    if (!h) return `早盤資料抓不到${state.histErr && state.histErr !== 'EMPTY' ? '（' + state.histErr + '）' : ''}，目前 ${n} 筆`;
    return `早盤 ${h} 根＋即時報價`;   // 2026-10-06：來源／延遲／量是估計值收進 K 線「?」（Andy「不要出現這樣廢話」）
  }

  /** 週期鈕上的點：紅＝即時（今天有盤）、灰＝非即時（畫的是最近交易日）。
   *  industry.js 的 markTf 重畫按鈕時也會叫它，所以按鈕重建之後顏色不會跑掉。*/
  function paintDots() {
    // 還沒問到任何資料之前先不下結論（不然盤中每次打開都會先閃一下灰點）
    const off = (state.histTried || state.ticks.length > 0) && !session().live;
    const day = offDay();
    document.querySelectorAll('#tfSeg button.livetf').forEach(b => {
      b.classList.toggle('offhrs', off);
      b.title = off
        ? (day ? `非即時：顯示最近交易日 ${day}` : '非即時')
        : '當天即時';
    });
  }

  // ---------------------------------------------------------------- 排程
  function emit() { paintDots(); state.subs.forEach(fn => { try { fn(); } catch (e) { /* 一個壞掉不要影響其他 */ } }); }
  function stopTimer() { if (state.timer) { clearInterval(state.timer); state.timer = null; } }
  function startTimer() {
    stopTimer();
    // 盤後不必每 5 秒問，數字不會再動了；個股卡的「即時」關著也不排（關＝靜態）
    if (!isIntraday() || !cardOn()) return;
    state.timer = setInterval(poll, POLL_MS);
  }

  // ---------------------------------------------------------------- 對外
  const LiveK = {
    /** 切到某一檔。換股票就重來一份。 */
    async attach(code, market) {
      if (state.code === code) { startTimer(); return; }
      stopTimer();
      state.code = code; state.market = market || null;
      state.symbol = yahooSymbol(code, market);
      state.ticks = []; state.hist = []; state.histTried = false; state.histErr = ''; state.offTicks = null;
      state.histDone = false;
      state.prevClose = null; state.name = ''; state.fails = 0; state.lastErr = '';
      lastRawAt = 0; nextTry = 0;                   // 換股票：上一檔吃過的那一列、退避時間都不算數
      /* ★ 2026-10-06 即時僅管理者（DECISIONS #326）：不是管理者 → 不讀這台瀏覽器存過的今天 5 秒序列、不輪詢、不打 Yahoo。
         poll() 問 cardOn（live.js 的 permLive 含閘門）、loadHistory() 拿不到代理網址（Live.proxy() 回空字串），
         所以下面照常走完只會得到「沒有即時來源」（histErr）＋ settled —— 個股頁的分時會立刻改用資料湖的 60 分 K，不會等 8 秒。*/
      if (window.TwLive && window.TwLive.canLive()) load();
      startTimer();
      await poll();
      await loadHistory();
      if (state.code === code) state.histDone = true;
      emit();
    },
    detach() { stopTimer(); state.code = null; },
    bars, sourceNote, isIntraday, minuteSeries,
    // 非交易時段（Andy 2026-09-26「為何這邊分 K 無法使用？」）：畫哪一天、實際畫哪個週期、按鈕上的點
    session, offDay, drawnTf, paintDots,
    /** 還在抓 Yahoo（四週期同看用它決定「資料到了要不要重建那一格」）。*/
    get loading() { return !state.histTried; },
    /** Yahoo 早盤那一趟已經回來（loading 在「開始抓」那一刻就變 false，抓的途中也是 false，不能拿來判斷「抓完了還是沒有」）。
     *  2026-09-28 分時走勢：抓完還是沒有資料，才自動改用日 K。*/
    get settled() { return !!state.histDone; },
    /** Yahoo 早盤那段**真的抓失敗了**（不是還沒設定來源、也不是 Worker 舊版）。
     *  industry.js 用它決定要不要先退回有資料的週期，不讓使用者對著一塊空白。*/
    histFailed() {
      // 'EMPTY'＝Yahoo 回了、但這一檔真的沒有分 K（冷門股）—— 那要明講，不是悄悄退回別的週期
      return !!(state.histTried && !state.hist.length && state.histErr
        && state.histErr !== 'NOYAHOO' && state.histErr !== '還沒設定即時來源' && state.histErr !== 'EMPTY');
    },
    /** 今天那一根「還沒收的日 K」。沒有報價就回 null（例如假日、或代理打不通）。 */
    todayBar() {
      const t = state.today;
      if (!t || t.c == null) return null;
      return [t.date, t.o, t.h, t.l, t.c, t.v];
    },
    tfs: Object.keys(TFS),
    // 手動更新：Yahoo 還沒有「今天」的 K 棒就再抓一次（盤中開盤頭 20 分鐘、或休市日剛開盤）
    refresh: async () => { await poll(); if (!state.hist.some(b => b.d === today())) await loadHistory(); emit(); },
    onUpdate(fn) { state.subs.push(fn); return () => { state.subs = state.subs.filter(f => f !== fn); }; },
    get state() { return state; },
    get ticking() { return !!state.timer; },
    // 驗收用：塞一筆假報價進去，不必等真的 5 秒
    _feed(m) { pushTick(m); emit(); },
  };

  /* 離開個股頁就停掉 —— 不能只靠 industry.js 的 route()，因為切到「總覽」那種
     非個股分頁時，app.js 根本不會走 Industry.route，輪詢就會一直在背景跑。 */
  window.addEventListener('hashchange', () => {
    if (!/^#stock\//.test(location.hash || '')) LiveK.detach();
  });

  window.LiveK = LiveK;
})();
