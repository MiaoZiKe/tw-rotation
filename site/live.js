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
  // 連續失敗這麼多次就把自動輪詢關掉，等使用者自己按「更新」再試。
  // 理由有兩個：(1) 公司網路可能整個擋掉 Worker，一直重試只會洗版 console；
  // (2) 打不通的端點每分鐘敲一次沒有意義。按「更新」會把計數歸零重新開始。
  const MAX_FAILS = 3;

  // Andy 的 Cloudflare Worker（2026-09-14 部署完成並實測過）。
  // 填成預設值，換一台電腦／換一個瀏覽器都不用再設定一次；
  // ⚙ 面板裡填的值會蓋過它（要換 Worker 或本機測試時用）。
  // 這不是密鑰 —— Worker 本身只轉一個端點、只給白名單網域 CORS。
  const DEFAULT_PROXY = 'https://tw-quote.kcq01010909.workers.dev';

  const state = {
    quotes: {},        // code -> { price, prevClose, chgPct, open, high, low, volume, time, name }
    timer: null,
    busy: false,
    lastOk: 0,
    lastErr: '',
    tries: 0,
    fresher: false,      // 伺服器上已經有更新的資料，但盤中不自動重載
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
   *  z＝成交價，但沒成交時是 '-'；此時退回 b（最佳買價第一檔）再退回 y（昨收）。 */
  function normalise(m) {
    const prev = num(m.y);
    let price = num(m.z);
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
      time: m.t || '',           // 這筆報價的時間（HH:MM:SS）
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
    const out = {};
    (j.msgArray || []).forEach(m => {
      const q = normalise(m);
      if (q.code) out[q.code] = q;
    });
    return out;
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
    return n;
  }

  // ---------------------------------------------------------------- 狀態列
  function stamp() {
    const q = Object.values(state.quotes)[0];
    const A = window.App;
    const el = document.getElementById('liveState');
    const btn = document.getElementById('liveBtn');
    if (!el || !btn) return;

    const intr = isIntraday();
    let cls = 'off', txt;
    if (!proxy()) {
      txt = '未設定即時來源';
    } else if (!state.lastOk) {
      txt = state.lastErr ? '即時：' + state.lastErr : '即時：尚未取得';
      cls = state.lastErr ? 'bad' : 'off';
    } else if (Date.now() - state.lastOk > STALE_MS) {
      txt = '即時已停（' + Math.round((Date.now() - state.lastOk) / 60000) + ' 分鐘沒更新）';
      cls = 'bad';
    } else {
      const t = q && q.time ? q.time.slice(0, 5) : new Date(state.lastOk)
        .toLocaleTimeString('zh-TW', { timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit', hour12: false });
      txt = (intr ? '即時 ' : '收盤 ') + t + (autoOn() ? (intr ? '　每分鐘' : '　每 30 分') : '　自動已關');
      cls = intr ? 'live' : 'ok';
      if (state.fresher) { txt = '有新資料，按「更新」載入'; cls = 'bad'; }
    }
    el.textContent = txt;
    el.className = 'livestate ' + cls;
    btn.disabled = state.busy;
    btn.textContent = state.busy ? '更新中…' : '更新';
    void A;
  }

  // ---------------------------------------------------------------- 一輪
  async function tick(manual) {
    if (state.busy) return;
    if (manual) { state.tries = 0; if (!state.timer && autoOn()) reschedule(); }
    // 分頁在背景就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    const codes = codesOnScreen();
    state.busy = true; stamp();
    try {
      if (proxy() && codes.length) {
        state.quotes = Object.assign({}, state.quotes, await fetchQuotes(codes));
        state.lastOk = Date.now(); state.lastErr = ''; state.tries = 0;
        paint();
      } else if (!proxy()) {
        state.lastErr = '還沒設定代理網址';
      }
      // 總覽最上面那三張大盤走勢圖跟報價同一個節奏（盤中每分鐘、盤後每 30 分、手動更新也算）
      if (window.Market3) { try { await window.Market3.refresh(); } catch (e) { /* 三張圖壞掉不該影響報價 */ } }
      // 靜態 JSON 有沒有換新版（Actions 重新部署過）。
      // ★ 每一輪都要檢查，不是只有手動那次 —— Andy 要的「盤後每 30 分鐘更新」指的是
      //   **資料**要變新，不是只有報價數字在跳。以前只在 manual 時檢查，
      //   等於開著的頁面永遠不會自己拿到 18:30 那輪跑完的新資料。
      await reloadIfRedeployed(manual);
    } catch (e) {
      state.tries++;
      state.lastErr = String(e.message || e).slice(0, 60);
      if (state.tries >= MAX_FAILS && state.timer) {
        clearInterval(state.timer);
        state.timer = null;
        state.lastErr = `連續 ${state.tries} 次抓不到，已暫停自動更新（按「更新」重試）`;
      }
    } finally {
      state.busy = false; stamp();
    }
  }

  /** 比對 meta.json 的 `generated_at`，判斷 Actions 是不是重新部署過。
   *
   *  盤中不自動重載 —— reload 會把展開的列、勾選的族群、K 線縮放全部弄掉，
   *  而盤中價格本來就靠即時報價在更新，沒必要打斷正在看盤的人。
   *  改成在狀態列掛一句「有新資料」，按「更新」才真的載入。
   *  盤後（以及手動按更新）就直接重載，那時打斷不了什麼。 */
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
    state.timer = autoOn() ? setInterval(() => tick(false), intervalMs()) : null;
    stamp();
  }

  // ---------------------------------------------------------------- 設定面板
  function wireSettings() {
    const pop = document.getElementById('livePop');
    const gear = document.getElementById('liveGear');
    if (!pop || !gear) return;
    const inp = document.getElementById('liveProxy');
    const chk = document.getElementById('liveAuto');
    inp.value = ls.get(KEY_PROXY, '');
    chk.checked = autoOn();
    gear.onclick = e => { e.stopPropagation(); pop.hidden = !pop.hidden; };
    pop.onclick = e => e.stopPropagation();
    document.addEventListener('click', () => { pop.hidden = true; });
    document.getElementById('liveSave').onclick = () => {
      ls.set(KEY_PROXY, inp.value.trim().replace(/\/+$/, ''));
      ls.set(KEY_ON, chk.checked ? '1' : '0');
      state.lastOk = 0; state.lastErr = '';
      pop.hidden = true;
      reschedule();
      tick(true);
    };
    document.getElementById('liveTest').onclick = async () => {
      const out = document.getElementById('liveTestOut');
      const base = inp.value.trim().replace(/\/+$/, '');
      out.textContent = '測試中…';
      if (!base) { out.textContent = '先填網址'; return; }
      try {
        const r = await fetch(base + '/quote?ex_ch=tse_2330.tw', { cache: 'no-store' });
        const j = await r.json();
        const m = (j.msgArray || [])[0];
        out.textContent = m ? `通了：${m.n} ${m.z}（${m.d} ${m.t}）` : '回應沒有資料：' + JSON.stringify(j).slice(0, 80);
      } catch (e) {
        out.textContent = '失敗：' + String(e.message || e).slice(0, 80);
      }
    };
  }

  // ---------------------------------------------------------------- 對外
  const Live = {
    tick,
    paint,
    proxy,                                     // market3.js 共用同一組設定（⚙ 面板改這裡也跟著改）
    get quotes() { return state.quotes; },
    get timerOn() { return !!state.timer; },   // 驗收用：自動更新到底有沒有在跑
    isIntraday,
    start() {
      const btn = document.getElementById('liveBtn');
      if (btn) btn.onclick = () => tick(true);
      wireSettings();
      reschedule();
      document.addEventListener('visibilitychange', () => { if (!document.hidden) tick(false); });
      // 換頁之後畫面上的代號就換了一批，重抓一次讓新的那批也有即時價
      window.addEventListener('hashchange', () => setTimeout(() => tick(false), 800));
      tick(false);
    },
  };

  window.Live = Live;
})();
