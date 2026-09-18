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
 */
(function () {
  'use strict';

  const POLL_MS = 5000;             // 跟 mis 自己的 userDelay 一致
  const KEY = (d, c) => `tw.livek.${d}.${c}`;
  const MAX_TICKS = 3600;           // 5 秒 × 3600 ＝ 5 小時，蓋得住整個交易日
  const MAX_FAILS = 3;
  /* 由同一份 1 分 K（Yahoo）＋ 即時 tick 推出來的週期。
     Andy 2026-09-18：「1 5 15 分 K 都限制當天即可」—— 所以 15 分也放進來，
     不再由後端預先產出 60 天的 15 分 K（那是部署最慢的一塊，見 DECISIONS #156）。
     一次請求換三個週期，比分開打三次便宜。*/
  const TFS = { '5s': 5, '1m': 60, '5m': 300, '15m': 900 };

  const state = {
    code: null, market: null, symbol: null,
    ticks: [],        // [{s: epoch 秒, p: 價, cv: 累計張數}]
    hist: [],         // Yahoo 的 1 分 K：[{s, o, h, l, c, v(股)}]
    histTried: false, histErr: '',
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

  async function loadHistory() {
    state.histTried = true;
    const base = proxy();
    if (!base) { state.histErr = '還沒設定即時來源'; return; }
    try {
      const r = await fetch(`${base}/y?symbol=${encodeURIComponent(state.symbol)}&interval=1m&range=1d`,
                            { cache: 'no-store' });
      if (r.status === 404 || r.status === 400) { state.histErr = 'NOYAHOO'; return; }
      if (!r.ok) { state.histErr = '代理回 HTTP ' + r.status; return; }
      const j = await r.json();
      const res = ((j.chart || {}).result || [])[0];
      if (!res || !res.timestamp) { state.histErr = 'Yahoo 沒有今天的資料'; return; }
      const q = ((res.indicators || {}).quote || [])[0] || {};
      const day = today();
      const out = [];
      res.timestamp.forEach((s, i) => {
        const c = num(q.close && q.close[i]);
        if (c === null) return;
        // 只留「今天」的（range=1d 偶爾會夾帶前一個交易日的尾巴）
        if (new Date((s + 8 * 3600) * 1000).toISOString().slice(0, 10) !== day) return;
        out.push({
          s,
          o: num(q.open && q.open[i]) ?? c,
          h: num(q.high && q.high[i]) ?? c,
          l: num(q.low && q.low[i]) ?? c,
          c,
          v: num(q.volume && q.volume[i]) || 0,          // 股
        });
      });
      state.hist = out;
      if (state.prevClose == null) state.prevClose = num((res.meta || {}).chartPreviousClose);
      state.histErr = '';
    } catch (e) {
      state.histErr = String(e.message || e).slice(0, 60);
    }
  }

  // ---------------------------------------------------------------- mis 即時
  function exch(code, market) {
    const mk = (market || '').toUpperCase();
    if (mk === 'TPEX' || mk === 'OTC') return 'otc_' + code + '.tw';
    if (mk === 'TWSE' || mk === 'TSE') return 'tse_' + code + '.tw';
    return 'tse_' + code + '.tw|otc_' + code + '.tw';
  }

  async function poll() {
    if (state.busy || !state.code) return;
    if (document.hidden) return;                    // 背景分頁不要一直打端點
    const base = proxy();
    if (!base) { state.lastErr = '還沒設定即時來源'; return; }
    state.busy = true;
    try {
      const url = base + '/quote?ex_ch=' + encodeURIComponent(exch(state.code, state.market));
      const r = await fetch(url, { cache: 'no-store' });
      if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
      const j = await r.json();
      const m = (j.msgArray || [])[0];
      if (!m) throw new Error('沒有這一檔的報價');
      pushTick(m);
      state.lastAt = Date.now(); state.lastErr = ''; state.fails = 0;
      emit();
    } catch (e) {
      state.fails++;
      state.lastErr = String(e.message || e).slice(0, 60);
      if (state.fails >= MAX_FAILS) stopTimer();     // 打不通就別一直洗 console
    } finally {
      state.busy = false;
    }
  }

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
    // 同一個 5 秒格只留最後一筆（報價沒動的時候不要疊出一堆一樣的點）
    if (last && Math.floor(last.s / 5) === Math.floor(ts / 5)) {
      last.s = ts; last.p = p; last.cv = cv;
    } else {
      state.ticks.push({ s: ts, p, cv });
      if (state.ticks.length > MAX_TICKS) state.ticks.splice(0, state.ticks.length - MAX_TICKS);
    }
    save();
  }

  function save() {
    if (!state.code) return;
    ls.set(KEY(today(), state.code), JSON.stringify({
      t: state.ticks, y: state.prevClose, n: state.name, d: state.today,
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

  // ---------------------------------------------------------------- 合成 K 棒
  /** 自己收集的 tick → N 秒 K。
   *  開＝前一根的收（連續盤），量＝累計張數的差值 × 1000（換成股，跟個股頁其他地方同口徑）。 */
  function barsFromTicks(sec, sinceSec) {
    const out = []; let cur = null, key = null, prevClose = null, prevCv = null;
    for (const t of state.ticks) {
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

  /** Yahoo 的 1 分 K → 我們的形狀（時間一律 +8 小時，跟 chart.js 的 fmtTime 對齊）。 */
  function barsFromHist(sec, untilSec) {
    const out = []; let cur = null, key = null;
    for (const b of state.hist) {
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

  /** 對外：某個週期的 K 棒。5 秒只用自己收的；1 分 / 5 分是「Yahoo 早盤 ＋ 自己收的尾巴」。 */
  function bars(tf) {
    const sec = TFS[tf];
    if (!sec) return [];
    if (tf === '5s') return barsFromTicks(5);
    const firstTick = state.ticks.length ? state.ticks[0].s : null;
    // 接縫：自己有資料的第一格開始用自己的，之前的用 Yahoo（同一格不要兩邊都畫）
    const seam = firstTick == null ? null : Math.floor(firstTick / sec) * sec;
    const head = barsFromHist(sec, seam);
    const tail = barsFromTicks(sec, seam);
    if (!head.length) return tail;
    if (!tail.length) return head;
    // 尾巴的第一根用 Yahoo 最後一根的收盤當開盤，接起來才連續
    tail[0][1] = head[head.length - 1][4];
    tail[0][2] = Math.max(tail[0][2], tail[0][1]);
    tail[0][3] = Math.min(tail[0][3], tail[0][1]);
    return head.concat(tail);
  }

  /** 這個週期的資料是哪裡來的，畫面上要講清楚。 */
  function sourceNote(tf) {
    const n = state.ticks.length;
    if (tf === '5s') {
      return n < 2
        ? '5 秒 K 是打開這一頁之後才開始收集的（證交所沒有個股的歷史分時檔）。開著就會一路長出來。'
        : `5 秒 K：每 5 秒一筆，${n} 筆。這是證交所報價能給的最細顆粒（它自己就是 5 秒更新一次）。盤中量為估計值。`;
    }
    const h = state.hist.length;
    if (!h && state.histErr === 'NOYAHOO') {
      return '早盤那段還沒接上：Worker 還是舊版（沒有 /y）。到 Cloudflare 重貼 workers/quote-proxy/worker.js 就會補齊 09:00 起的 K 棒。';
    }
    if (!h) return `早盤資料抓不到${state.histErr ? '（' + state.histErr + '）' : ''}，目前只有打開這一頁之後收集到的 ${n} 筆。`;
    return `早盤 ${h} 根來自 Yahoo（延遲約 20 分鐘、量偏低），最近這段是證交所即時報價每 5 秒一筆自己疊的。盤中量為估計值，收盤後由管線的正式資料覆蓋。`;
  }

  // ---------------------------------------------------------------- 排程
  function emit() { state.subs.forEach(fn => { try { fn(); } catch (e) { /* 一個壞掉不要影響其他 */ } }); }
  function stopTimer() { if (state.timer) { clearInterval(state.timer); state.timer = null; } }
  function startTimer() {
    stopTimer();
    // 盤後不必每 5 秒問，數字不會再動了
    if (!isIntraday()) return;
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
      state.ticks = []; state.hist = []; state.histTried = false; state.histErr = '';
      state.prevClose = null; state.name = ''; state.fails = 0; state.lastErr = '';
      load();
      startTimer();
      await poll();
      await loadHistory();
      emit();
    },
    detach() { stopTimer(); state.code = null; },
    bars, sourceNote, isIntraday,
    /** 今天那一根「還沒收的日 K」。沒有報價就回 null（例如假日、或代理打不通）。 */
    todayBar() {
      const t = state.today;
      if (!t || t.c == null) return null;
      return [t.date, t.o, t.h, t.l, t.c, t.v];
    },
    tfs: Object.keys(TFS),
    refresh: async () => { await poll(); if (!state.hist.length) await loadHistory(); emit(); },
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
