/* market3.js — 總覽最上方那三張大盤圖：加權指數 / 櫃買指數 / 台指期
 *
 * Andy 2026-09-14：「總攬最上方需新增 加權 櫃買 期貨 指數 K線圖以及走勢圖 上下對應」
 *                  「需出現 加權與櫃買 台指期 即時 走勢圖並且可以切換K線型態，
 *                    且指標 格式 可以參考原本個股做好的執行。」
 *
 * 資料源（走 Cloudflare Worker 的 /chart，原因跟 live.js 一樣：CORS）
 * ------------------------------------------------------------------
 *   加權  https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt   ch=t00.tw
 *   櫃買  https://mis.twse.com.tw/stock/data/mis_ohlc_OTC.txt   ch=o00.tw
 *   台指期 https://mis.twse.com.tw/stock/data/futures_chart.txt  ex=taifex
 * 就是證交所「基本市況報導」那三張走勢圖自己在用的檔。2026-09-14 17:30 實測：
 *   TSE/OTC：ohlcArray 270 筆，09:01~13:33 每分鐘一筆 {t:epoch毫秒, ts:"090100", c:指數, s:該分鐘張數}
 *   FUT   ：ohlcArray 300 筆，08:46~13:45，沒有 ts 欄位，其餘一樣
 *   三個檔的 infoArray[0] 都直接附當天的 o/h/l/z（開高低收）與 y（昨收），
 *   所以卡片上方那排數字不用另外再打一次報價端點。
 *
 * 為什麼「走勢圖」和「K 線」是兩套繪圖
 * ------------------------------------
 * 走勢圖要的是「固定 09:00–13:30 的時間軸 + 分鐘量柱 + 昨收虛線」，
 * 未到的時間也要留白（才看得出現在走到哪），ECharts 的類目軸最自然。
 * K 線要的是縮放、指標面板、跟個股同一套設定，那是 KChart（Lightweight Charts）的強項。
 * 兩邊共用 localStorage 的 `tw.kcfg` —— 在個股頁調好的 MA/KD/MACD，這裡直接吃到。
 *
 * ★ 分 K 是合成的，這件事要講清楚
 * 來源只給「每分鐘的指數收盤價」，沒有分鐘的最高最低。所以：
 *   開 = 前一分鐘的收盤（連續盤，等於這一分鐘的起點）
 *   高/低 = 該區間內分鐘收盤的極值 —— **不是真正的盤中極值**
 * 卡片上的「高 / 低」那兩個數字才是當天真正的極值（來自 infoArray）。
 *
 * ★ 台指期夜盤：跟日盤共用同一張圖，不再另外疊一塊方框（Andy 2026-09-19）
 * ------------------------------------------------------------------
 * 他的原話：「夜盤勢會跟日盤共用同一個走試圖 而不是圖利分開，所以也具備即時走勢 K線等資訊」。
 * 以前的做法是在卡片上半部插一個 `.m3-night` 方框，下面還是日盤的走勢圖 ——
 * 同一張卡片上兩個東西、兩套數字，而且夜盤只有數字沒有圖。現在改成：
 * 「日盤／夜盤」就是同一個圖表容器（`#m3c-FUT`）與同一排數字（`.m3-nums`）的切換。
 *
 * 夜盤到底拿得到什麼（2026-09-19 查證，不是猜的）
 *   ✔ 報價快照：期交所行情看板 `getQuoteList`（MarketType=1），Worker 的 `/fut?session=night`。
 *     每次只回**當下一筆**：現價／參考價／開高低／累計量／未平倉。fixture 在
 *     `docs/fixtures/taifex_night_probe.json`，實測 200。
 *   ✘ 夜盤分時序列：**沒有**任何已驗證的免費來源。
 *     證交所的 `futures_chart.txt` 只有日盤（白天那一段）。
 *     期交所的 `getChartData1M` 存在但**還沒拿到過一次成功回應** —— 探測那次送了
 *     `{"SymbolID": ["TXFJ6-F"]}` 被回 400，錯誤訊息是
 *     `Cannot deserialize instance of java.lang.String out of START_ARRAY`，
 *     也就是它要的是**字串**不是陣列。要重探一次（把探測腳本那行改成字串）才知道回什麼，
 *     照專案規矩「沒有真實 API 樣本就不寫 parser」，這裡先不接。
 *   ✔ 夜盤的「日 K 歷史」其實 FinMind 有：`TaiwanFuturesDaily` 的
 *     `trading_session == 'after_market'`（`pipeline/sources/finmind.py` 現在刻意只取 `position`）。
 *     資料湖沒存，所以歷史週期切到夜盤時只能用日盤那條，畫面上會講出來。
 *
 * 所以夜盤的走勢圖是這樣畫的，而且**每個點都是真的**：
 *   自動更新那一輪（盤中 10 秒／盤後 5 分鐘）每拿到一筆夜盤報價，就把
 *   {時間, 成交價, 累計量的增量} 收進 `state.nightPts`，存在 localStorage（以 CDate 分天）。
 *   這是真實觀測到的成交價與真實的量差，不是內插也不是假資料；
 *   代價是「只有你開著網頁的那段時間」才有點 —— 這句話直接寫在圖上，不藏。
 *   點數不足 2 筆時不畫線，改在同一個容器裡寫清楚為什麼。
 */
(function () {
  'use strict';

  const KEY_MODE = 'tw.m3.mode';     // line | k
  const KEY_TF = 'tw.m3.tf';         // 1 | 5 | 15 | 30（分鐘）
  const KEY_BIG = 'tw.m3.big';       // 放大哪一張（空字串＝三張並排）
  const KEY_FUTS = 'tw.m3.fut';      // 台指期看日盤還是夜盤
  const KEY_NPTS = 'tw.m3.nightpts'; // 夜盤累積到的報價點（真實觀測值，以 CDate 分天）

  const IDX = [
    // yahoo：有歷史 OHLC 可以抓的才填。櫃買的 ^TWOII 在 Yahoo 已經壞掉
    //（2026-09-15 實測：最後一筆停在 2026-07-17、現價給 269.45 而實際 395），
    // 台指期則沒有免費來源 —— 這兩個只有「當天即時」，選到歷史週期時畫面會說清楚為什麼。
    { id: 'TSE', name: '加權指數', sub: '上市', turnover: true, yahoo: '^TWII' },
    { id: 'OTC', name: '櫃買指數', sub: '上櫃', turnover: true, yahoo: null },
    { id: 'FUT', name: '台指期', sub: '近月', turnover: false, yahoo: null },
  ];
  // 交易時段（台北）。留白到收盤，才看得出「現在走到哪」。
  const SESSION = {
    TSE: [9 * 60, 13 * 60 + 30], OTC: [9 * 60, 13 * 60 + 30], FUT: [8 * 60 + 45, 13 * 60 + 45],
  };
  // 夜盤：台北 15:00 ~ 翌日 05:00。跨午夜，所以凌晨那段一律記成 24*60 + 分鐘，軸才是連續的。
  const SESSION_NIGHT = [15 * 60, 29 * 60];
  /* 週期清單。Andy 2026-09-15：「時間週期需要新增1H 4H 日 周 月 季K 太多的話可以改清單式選項」
     —— 按鈕排一排會超出卡片寬度，所以改成下拉選單，分「當天即時」與「歷史」兩組。
     即時那組是 mis 的當日分時檔自己合成的；歷史那組是 Yahoo 的 ^TWII。
     4 小時與季 K 是拿 1 小時 / 月線再合成的（Yahoo 沒有這兩個原生週期）。 */
  const TFS = [1, 5, 15, 30];                        // 當天即時的分鐘週期（相容舊的 tw.m3.tf）
  /* 日／週／月／季都從 `site/data/index_ohlc.json` 來 —— 那是管線用 FinMind 存進資料湖的
     （TaiwanStockPrice 的 TAIEX / TPEx 與 TaiwanFuturesDaily 的 TX 近月）。
     Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」—— 對，Yahoo 那條壞了不代表沒有別條。
     只有「1 小時 / 4 小時」還是走 Yahoo，因為那是日線合成不出來的週期，而且只有加權有。 */
  const HIST = [
    { id: 'H1', label: '1 小時', iv: '60m', range: '3mo', group: 1, yahooOnly: true },
    { id: 'H4', label: '4 小時', iv: '60m', range: '1y', group: 4, yahooOnly: true },
    { id: 'D', label: '日 K', lake: true },
    { id: 'W', label: '週 K', lake: true, roll: 'W' },
    { id: 'M', label: '月 K', lake: true, roll: 'M' },
    { id: 'Q', label: '季 K', lake: true, roll: 'M', group: 3 },
  ];
  const histDef = (id) => HIST.filter(h => h.id === id)[0] || null;
  /** 存進 localStorage 的值可能是舊版的數字，也可能是新的歷史週期代號。 */
  function normTf(v) {
    const sv = String(v == null ? '5' : v);
    if (histDef(sv)) return sv;
    return TFS.indexOf(+sv) >= 0 ? String(+sv) : '5';
  }

  /* 自動更新的節奏。
     Andy 2026-09-15：「當我只要開啟走勢圖跟K線圖 他會自動更新 而非我要按下更新才更新」——
     之前這三張圖是寄生在 live.js 的報價輪詢裡（每分鐘一次），而且掛在 fetchQuotes 後面：
     報價連續失敗三次時整個計時器會被關掉，連帶這三張圖也不動了，只能按「更新」。
     現在改成自己有一組計時器，跟報價完全脫鉤 —— 報價壞掉不影響圖，圖壞掉也不影響報價。
     盤中 10 秒一次：mis 的 infoArray（卡片上那排數字）本來就是每 5 秒更新，
     分時檔每分鐘多一筆，10 秒足以讓數字一直在跳、新的一分鐘一出現就補上去。 */
  const MS_LIVE = 10 * 1000;
  const MS_AFTER = 5 * 60 * 1000;
  /* 夜盤另外一組 60 秒的計時器（2026-09-19）。
     夜盤走勢是「一輪收一個點」收出來的，跟著盤後那 5 分鐘走的話一小時只有 12 個點 ——
     那不叫即時走勢。改成 60 秒，顆粒度就跟日盤的分 K 一致。
     它只打 /fut，不碰那三個分時檔（收盤後它們不會再變，多打是白費）。
     期交所行情看板本身是秒級更新，一分鐘問一次已經很客氣。 */
  const MS_NIGHT = 60 * 1000;

  const state = { data: {}, err: {}, mode: 'line', tf: 5, big: '', kcharts: {}, busy: false, at: 0,
    hist: {}, histErr: {}, histBusy: {}, timer: null, nTimer: null, tickMs: 0, fails: 0,
    // 夜盤：futSession＝日盤/夜盤；futNight＝最新一筆報價；nightPts＝累積到的真實觀測點
    futSession: 'day', futNight: null, futNightErr: '', nightPts: [], nightDate: '',
    lakeDaily: {},     // 資料湖原始日線（用來講「歷史只有幾年」，需求二）
    // noSrc[指數|週期] = true：這張卡片的這個週期沒有免費來源，已自動退回日線（N11）
    noSrc: {} };   // hist[TSE+'|'+id] = [[t,o,h,l,c,v]]

  function taipeiNow() {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  }
  /** 盤中？台指期 08:45 開盤，所以比現貨早；收盤後多留 10 分鐘讓尾盤落地。 */
  function isIntraday() {
    const d = taipeiNow();
    const w = d.getDay();
    if (w === 0 || w === 6) return false;
    const m = d.getHours() * 60 + d.getMinutes();
    return m >= 8 * 60 + 40 && m <= 13 * 60 + 55;
  }
  function schedule() {
    /* ★ 只有「節奏真的變了」才重設計時器。
       檔案最下面有一個每 60 秒呼叫 schedule() 的迴圈（用來跨越開盤／收盤換節奏）——
       如果每次都 clearInterval 再 setInterval，週期比 60 秒長的計時器
       （盤後 5 分鐘、夜盤 60 秒）會在自己觸發之前就被歸零，永遠跑不到。 */
    const ms = isIntraday() ? MS_LIVE : MS_AFTER;
    if (!state.timer || state.tickMs !== ms) {
      if (state.timer) clearInterval(state.timer);
      state.tickMs = ms;
      state.timer = setInterval(() => refresh(), ms);
    }
    if (!state.nTimer) state.nTimer = setInterval(tickNight, MS_NIGHT);
  }
  /** 夜盤那一輪：只補一筆報價、只在真的是夜盤而且使用者也選在夜盤時才跑。 */
  async function tickNight() {
    if (document.hidden) return;
    if (!document.getElementById('m3')) return;
    if (state.futSession !== 'night' || futSession() !== 'night') return;
    try { state.futNight = await fetchFut('night'); state.futNightErr = ''; pushNight(state.futNight); }
    catch (e) { state.futNightErr = String(e.message || e); }
    draw();
  }

  const ls = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗，忽略 */ } },
  };
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
  const num = (v) => { const n = parseFloat(v); return isFinite(n) ? n : null; };
  const F = () => (window.App && window.App.fmt) || null;

  // ---------------------------------------------------------------- 抓資料
  function proxy() {
    // 跟 live.js 用同一組設定（⚙ 面板改了這裡也跟著改）
    if (window.Live && window.Live.proxy) return window.Live.proxy();
    return '';
  }

  /* 台指期夜盤（Andy 2026-09-18 圖一「台指期需要顯示夜盤」；2026-09-19 N11）。
     證交所的 futures_chart.txt 只有日盤，所以夜盤另外走期交所（Worker 的 /fut）。
     2026-09-18 在 Actions 上實測過四個端點，欄位存在 docs/fixtures/taifex_night_probe.json：
       getQuoteList MarketType=0/1 都回 200；夜盤的合約代號是 `-M` 結尾（日盤是 `-F`），
       第一筆 `TXF-P/-S` 是臺指**現貨**參考列，要跳過。
     近月＝跳過現貨列之後成交量最大的那一支。*/
  /** 現在（台北）是不是夜盤時段。凌晨算成「昨天的 24+」，軸才不會斷。 */
  function nightMin(d) {
    const m = d.getHours() * 60 + d.getMinutes();
    return m < 6 * 60 ? m + 24 * 60 : m;
  }
  function futSession() {
    const mm = nightMin(taipeiNow());
    return (mm >= SESSION_NIGHT[0] && mm <= SESSION_NIGHT[1]) ? 'night' : 'day';
  }
  async function fetchFut(session) {
    const base = proxy();
    if (!base) throw new Error('還沒設定即時來源');
    const r = await fetch(`${base}/fut?session=${session}&t=${Date.now()}`, { cache: 'no-store' });
    if (r.status === 404 || r.status === 400) throw new Error('NOFUT');
    if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
    const j = await r.json();
    const list = ((j.RtData || {}).QuoteList || [])
      .filter(q => q.SymbolID && q.SymbolID.indexOf('-') > 0
        && !/-[SP]$/.test(q.SymbolID));      // 跳過 TXF-S / TXF-P（臺指現貨參考列）
    if (!list.length) throw new Error('NOFUTDATA');
    const num = (v) => { const n2 = parseFloat(v); return isFinite(n2) ? n2 : null; };
    list.sort((a, b) => (num(b.CTotalVolume) || 0) - (num(a.CTotalVolume) || 0));
    const q = list[0];
    const last = num(q.CLastPrice), ref = num(q.CRefPrice);
    return {
      session, symbol: q.SymbolID, name: q.DispCName,
      last, ref, open: num(q.COpenPrice), high: num(q.CHighPrice), low: num(q.CLowPrice),
      vol: num(q.CTotalVolume), oi: num(q.OpenInterest), settle: num(q.SettlementPrice),
      diff: last != null && ref != null ? last - ref : null,
      pct: last != null && ref ? (last - ref) / ref * 100 : null,
      time: q.CTime || '', date: q.CDate || '',
      /* 夜盤時段外打 MarketType=1，期交所回的是日盤最後一筆（CTime 13 點多）。
         那筆不能當成夜盤報價顯示，所以先標起來，畫面上退回日盤數字並說明。*/
      inSession: (() => { const m = nightMinOf(q.CTime);
        return m !== null && m >= SESSION_NIGHT[0] && m <= SESSION_NIGHT[1]; })(),
    };
  }

  /* ---- 夜盤走勢：把每一輪真的拿到的報價收成序列 -------------------------------
     期交所只給「當下一筆」，所以序列是我們自己一筆一筆收的。
     每個點都是真實成交價 ＋ 真實的累計量增量，沒有內插、沒有補值。
     存 localStorage（以 CDate 分天），重新整理不會歸零；換一天就整組丟掉重來。
     上限 1200 筆：夜盤 14 小時，就算每 10 秒一筆也只會用到其中一段，
     真正的作用是防止 localStorage 被無限灌大。 */
  const NPTS_MAX = 1200;
  function loadNightPts() {
    try {
      const j = JSON.parse(localStorage.getItem(KEY_NPTS) || 'null');
      if (j && Array.isArray(j.pts)) { state.nightPts = j.pts; state.nightDate = String(j.date || ''); }
    } catch (e) { /* 壞掉就當作沒有 */ }
  }
  function saveNightPts() {
    ls.set(KEY_NPTS, JSON.stringify({ date: state.nightDate, pts: state.nightPts.slice(-NPTS_MAX) }));
  }
  /** "134459" → 台北分鐘數（凌晨 +1440）。拿不到時間就回 null，寧可丟掉這一點。 */
  function nightMinOf(hhmmss) {
    const s = String(hhmmss || '');
    if (s.length < 4) return null;
    const h = +s.slice(0, 2), mi = +s.slice(2, 4);
    if (!isFinite(h) || !isFinite(mi)) return null;
    const m = h * 60 + mi;
    return m < 6 * 60 ? m + 24 * 60 : m;
  }
  /** 收一筆夜盤報價。回傳 true＝真的多了一個新的點（同一分鐘只留最後一筆）。 */
  function pushNight(q) {
    if (!q || q.last == null) return false;
    const min = nightMinOf(q.time);
    if (min === null) return false;
    /* 只收落在夜盤時段（15:00~翌日 05:00）的點。
       夜盤時段外打 MarketType=1，期交所回的是日盤最後那一筆（CTime 會是 13 點多）——
       把它畫進夜盤走勢圖就是在說謊，所以直接丟掉。*/
    if (min < SESSION_NIGHT[0] || min > SESSION_NIGHT[1]) return false;
    if (q.date && q.date !== state.nightDate) {   // 換一天（或第一次）→ 整組重來
      state.nightDate = q.date; state.nightPts = [];
    }
    const pts = state.nightPts;
    const prev = pts.length ? pts[pts.length - 1] : null;
    // 累計量的增量＝這段時間真的成交了多少口；第一筆沒有前一筆可以比，記 0
    const dv = (prev && q.vol != null && prev[2] != null) ? Math.max(0, q.vol - prev[2]) : 0;
    if (prev && prev[0] === min) {               // 同一分鐘：用最新的價，量累加上去
      prev[1] = q.last; prev[2] = q.vol; prev[3] = (prev[3] || 0) + dv;
      saveNightPts();
      return false;
    }
    pts.push([min, q.last, q.vol, dv]);          // [分鐘, 價, 累計量, 該段量]
    if (pts.length > NPTS_MAX) pts.splice(0, pts.length - NPTS_MAX);
    saveNightPts();
    return true;
  }
  /** 累積到的夜盤點 → 跟 `parse()` 同一個形狀，這樣走勢圖與 K 線可以完全共用。 */
  function nightSeries() {
    const q = state.futNight;
    const base = nightBaseMs();
    const pts = state.nightPts.map(p => ({
      // ms 是真正的 UTC epoch 毫秒（toBars 會自己 +8 小時換成台北牆鐘）
      ms: base + p[0] * 60 * 1000,
      min: p[0], c: p[1], s: p[3] || 0,
    }));
    return {
      id: 'FUT', night: true,
      name: q ? (q.name || '') : '', date: q ? q.date : state.nightDate, time: q ? q.time : '',
      prev: q ? q.ref : null, prevLabel: '參考價',
      open: q ? q.open : null, high: q ? q.high : null, low: q ? q.low : null,
      last: q ? q.last : null, vol: q ? q.vol : null, amt: null, oi: q ? q.oi : null,
      symbol: q ? q.symbol : '',
      points: pts,
    };
  }
  /** 夜盤那天台北 00:00 對應的 UTC 毫秒，給上面換算每個點的時間戳。 */
  function nightBaseMs() {
    const s = String(state.nightDate || '');
    if (s.length !== 8) return Date.now() - (Date.now() % 86400000);
    return Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)) - 8 * 3600 * 1000;
  }
  /** 現在這張 FUT 卡片要看的是夜盤嗎。 */
  const isNight = (x) => x.id === 'FUT' && state.futSession === 'night';

  async function fetchOne(id) {
    const base = proxy();
    if (!base) throw new Error('還沒設定即時來源');
    const r = await fetch(base + '/chart?id=' + id + '&t=' + Date.now(), { cache: 'no-store' });
    if (r.status === 404 || r.status === 400) {
      // Worker 還是舊版（只有 /quote）。這是 Andy 要自己去 Cloudflare 重貼的那一步，直接寫在畫面上。
      throw new Error('NOCHART');
    }
    if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
    const j = await r.json();
    if (j.rtcode && j.rtcode !== '0000') throw new Error('來源回 rtcode ' + j.rtcode);
    return parse(id, j);
  }

  /** 原始 JSON → {info, points:[{ms,min,c,s}], y, date} */
  function parse(id, j) {
    const info = (j.infoArray || [])[0] || {};
    const pts = [];
    (j.ohlcArray || []).forEach(o => {
      const ms = num(o.t); const c = num(o.c); if (ms === null || c === null) return;
      const d = new Date(ms + 8 * 3600 * 1000);          // 換算成台北牆鐘
      pts.push({ ms, min: d.getUTCHours() * 60 + d.getUTCMinutes(), c, s: num(o.s) || 0 });
    });
    pts.sort((a, b) => a.ms - b.ms);
    return {
      id,
      name: info.n || '',
      date: info.d || String(j.lastDatetime || '').slice(0, 8),
      time: info.t || '',
      prev: num(info.y),
      open: num(info.o), high: num(info.h), low: num(info.l), last: num(info.z),
      vol: num((j.staticObj || {}).tv),                  // 累計成交張數（台指期是口數）
      amt: num(info.v),                                  // 成交金額（百萬元）；台指期沒有
      points: pts,
    };
  }

  async function refresh(manual) {
    if (state.busy) return;
    if (!document.getElementById('m3')) return;          // 不在總覽就不用抓
    // 分頁切走就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    state.busy = true;
    const jobs = IDX.map(async x => {
      try { state.data[x.id] = await fetchOne(x.id); state.err[x.id] = ''; }
      catch (e) { state.err[x.id] = String(e.message || e); }
    });
    /* 夜盤報價也放進同一輪（2026-09-19）。
       以前只有 mount 與按鈕點擊時抓一次，等於「夜盤的數字永遠不會自己更新」——
       Andy 要的是「夜盤也具備即時」，那就得跟日盤吃同一個計時器。
       只有選在夜盤時才打，不然平白多一個請求。 */
    if (state.futSession === 'night') {
      jobs.push((async () => {
        try { state.futNight = await fetchFut('night'); state.futNightErr = ''; pushNight(state.futNight); }
        catch (e) { state.futNightErr = String(e.message || e); }
      })());
    }
    await Promise.all(jobs);
    state.busy = false; state.at = Date.now();
    state.fails = IDX.every(x => state.err[x.id]) ? state.fails + 1 : 0;
    draw();
  }

  /** 歷史 K。日／週／月／季走資料湖（index_ohlc.json）；1 小時／4 小時走 Yahoo（只有加權有）。 */
  async function fetchHist(x, def) {
    const key = x.id + '|' + def.id;
    if (state.hist[key] || state.histBusy[key]) return;
    if (def.lake) {
      state.histBusy[key] = true;
      try {
        const A = window.App;
        const all = await A.load('index_ohlc', { fallback: {} });
        let bars = (all && all[x.id]) || [];
        if (!bars.length) throw new Error('NOLAKE');
        bars = bars.map(b => b.slice());
        // 原始日線另外留一份：週／月／季看起來「只有幾根」時，要能講出日線到底有幾年（需求二）
        state.lakeDaily[x.id] = bars.slice();
        if (def.roll) bars = rollLake(bars, def.roll);
        if (def.group > 1) bars = groupBars(bars, def.group);
        state.hist[key] = bars;
        state.histErr[key] = '';
      } catch (e) {
        state.histErr[key] = String(e.message || e);
      } finally {
        state.histBusy[key] = false;
        draw();
      }
      return;
    }
    if (!x.yahoo) { state.histErr[key] = 'NOSRC'; return; }
    const base = proxy();
    if (!base) { state.histErr[key] = '還沒設定即時來源'; return; }
    state.histBusy[key] = true;
    try {
      const r = await fetch(`${base}/y?symbol=${encodeURIComponent(x.yahoo)}&interval=${def.iv}&range=${def.range}`,
                            { cache: 'no-store' });
      if (r.status === 404 || r.status === 400) throw new Error('NOCHART');
      if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
      const j = await r.json();
      const res = ((j.chart || {}).result || [])[0];
      if (!res || !res.timestamp) throw new Error('Yahoo 沒有資料');
      const q = ((res.indicators || {}).quote || [])[0] || {};
      let bars = [];
      res.timestamp.forEach((t, i) => {
        const c = num(q.close && q.close[i]); if (c === null) return;
        bars.push([t + 8 * 3600, num(q.open && q.open[i]) ?? c, num(q.high && q.high[i]) ?? c,
                   num(q.low && q.low[i]) ?? c, c, num(q.volume && q.volume[i]) || 0]);
      });
      if (def.roll === 'W') bars = rollWeek(bars);
      if (def.group > 1) bars = groupBars(bars, def.group);
      state.hist[key] = bars;
      state.histErr[key] = '';
    } catch (e) {
      state.histErr[key] = String(e.message || e);
    } finally {
      state.histBusy[key] = false;
      draw();
    }
  }

  /** N 根併一根（4 小時＝四根 1 小時；季＝三根月線）。 */
  function groupBars(bars, n) {
    const out = [];
    for (let i = 0; i < bars.length; i += n) {
      const g = bars.slice(i, i + n); if (!g.length) continue;
      out.push([g[0][0], g[0][1], Math.max.apply(null, g.map(b => b[2])),
                Math.min.apply(null, g.map(b => b[3])), g[g.length - 1][4],
                g.reduce((a, b) => a + (b[5] || 0), 0)]);
    }
    return out;
  }
  /** 資料湖的日線（日期是 'YYYY-MM-DD' 字串）→ 週／月。直接用個股頁那一套，口徑才會一致。 */
  function rollLake(bars, mode) {
    return (window.KUtil && window.KUtil.resampleDaily)
      ? window.KUtil.resampleDaily(bars, mode) : bars;
  }

  /** 日線 → 週線（以該週第一個交易日標示，與個股頁的 resampleDaily 同口徑）。 */
  function rollWeek(bars) {
    const out = []; let cur = null, key = null;
    for (const b of bars) {
      const d = new Date(b[0] * 1000);
      const day = (d.getUTCDay() + 6) % 7;
      const k = Math.floor((b[0] - day * 86400) / 86400);
      if (k !== key) { if (cur) out.push(cur); key = k; cur = b.slice(); }
      else {
        cur[2] = Math.max(cur[2], b[2]); cur[3] = Math.min(cur[3], b[3]);
        cur[4] = b[4]; cur[5] += (b[5] || 0);
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  // ---------------------------------------------------------------- 合成分 K
  /** 分鐘收盤序列 → N 分鐘 K 棒 [[時間, 開, 高, 低, 收, 量]]。
   *  開＝前一根的收（連續盤）；高低是分鐘收盤的極值，不是真正盤中極值。 */
  function toBars(pts, n) {
    const out = []; let cur = null, key = null, prevClose = null;
    for (const p of pts) {
      const k = Math.floor(p.min / n);
      if (k !== key) {
        if (cur) { out.push(cur); prevClose = cur[4]; }
        key = k;
        const o = prevClose === null ? p.c : prevClose;
        cur = [Math.floor(p.ms / 1000) + 8 * 3600, o, Math.max(o, p.c), Math.min(o, p.c), p.c, p.s * 1000];
      } else {
        cur[2] = Math.max(cur[2], p.c); cur[3] = Math.min(cur[3], p.c);
        cur[4] = p.c; cur[5] += p.s * 1000;
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  // ---------------------------------------------------------------- 版面
  // 夜盤跨午夜，分鐘數會 >= 1440（例如 01:30 記成 25*60+30），顯示時要折回 24 小時制
  const hhmm = (m) => String(Math.floor((m % 1440) / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

  /* 這張卡片現在該用哪一份數字／哪一組點。
     台指期切到夜盤時，整張卡片（數字 ＋ 圖）都換成夜盤那一份 ——
     不是在日盤上面再疊一塊（Andy 2026-09-19：「夜盤要跟日盤共用同一個走勢圖」）。
     夜盤報價真的抓不到時**退回日盤並在圖上說明**，畫面不會變成一片空白（N11 的規矩）。 */
  function seriesOf(x) {
    if (isNight(x) && state.futNight && state.futNight.inSession) return nightSeries();
    return state.data[x.id];
  }

  function cardHead(x) {
    const d = seriesOf(x);
    const f = F();
    if (!d || !f) return `<div class="m3-nums"><span class="m3-px">—</span></div>`;
    const chg = (d.last != null && d.prev) ? d.last - d.prev : null;
    const pct = chg != null ? chg / d.prev * 100 : null;
    const dp = x.id === 'OTC' ? 2 : (x.id === 'FUT' ? 0 : 2);
    const extra = x.turnover
      ? `成交 ${d.amt != null ? f.n(d.amt / 100, 0) + ' 億' : '—'}`
      : `總量 ${d.vol != null ? f.i(d.vol) + ' 口' : '—'}`
        + (d.oi != null ? `　未平倉 ${f.i(d.oi)}` : '');
    // 夜盤沒有「昨收」的概念，期交所給的是「參考價」（日盤收盤價）
    const base = d.prevLabel || '昨收';
    const tag = d.night ? `<span class="m3-tag">夜盤 ${f.esc(d.symbol || '')}</span>`
      : isNight(x) ? '<span class="m3-tag warn">夜盤報價未取得</span>' : '';
    return `<div class="m3-nums">
      <span class="m3-px ${f.cls(chg)}">${f.n(d.last, dp)}</span>
      <span class="m3-chg ${f.cls(chg)}">${chg == null ? '—' : (chg > 0 ? '+' : '') + f.n(chg, dp)} ${f.pct(pct, 2)}</span>
      <span class="m3-sub">開 ${f.n(d.open, dp)}　高 <b class="up">${f.n(d.high, dp)}</b>　低 <b class="down">${f.n(d.low, dp)}</b>　${base} ${f.n(d.prev, dp)}</span>
      <span class="m3-sub">${extra}　<span class="mono">${f.esc(String(d.date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'))} ${f.esc(String(d.time || '').replace(/^(\d{2})(\d{2})(\d{2})?$/, '$1:$2'))}</span>${tag}</span>
    </div>`;
  }

  function mount() {
    const host = document.getElementById('m3');
    if (!host) return;
    // 重掛（例如切主題）之前先收掉舊的 Lightweight Charts，不然 ResizeObserver 會留著
    Object.keys(state.kcharts).forEach(killK);
    state.mode = ls.get(KEY_MODE, 'line') === 'k' ? 'k' : 'line';
    state.tf = normTf(ls.get(KEY_TF, '5'));
    state.big = ls.get(KEY_BIG, '');
    if (!IDX.some(x => x.id === state.big)) state.big = '';
    host.innerHTML = `
      <div class="m3-bar">
        <div class="seg" id="m3Mode"><button data-m="line">走勢圖</button><button data-m="k">K 線</button></div>
        <label class="m3-tfsel">週期
          <select id="m3Tf">
            <optgroup label="當天即時（證交所分時）">${TFS.map(n => `<option value="${n}">${n} 分</option>`).join('')}</optgroup>
            <optgroup label="歷史（Yahoo ^TWII）">${HIST.map(h => `<option value="${h.id}">${h.label}</option>`).join('')}</optgroup>
          </select></label>
        <span class="note" id="m3Note"></span>
      </div>
      <div class="m3-grid" id="m3Grid">${IDX.map(x => `
        <div class="card m3-card" data-id="${x.id}">
          <div class="m3-h">
            <h3>${x.name} <small>${x.sub}</small></h3>
            ${x.id === 'FUT' ? `<div class="seg tiny" id="futSeg">
              <button data-s="day">日盤</button><button data-s="night">夜盤</button></div>` : ''}
            <button class="btn small m3-big" data-id="${x.id}">展開 ⤢</button>
          </div>
          ${cardHead(x)}
          <div class="m3-chart" id="m3c-${x.id}"></div>
        </div>`).join('')}</div>`;
    $$('#m3Mode button').forEach(b => b.onclick = () => { state.mode = b.dataset.m; ls.set(KEY_MODE, state.mode); draw(); });
    $('#m3Tf').onchange = (e) => { state.tf = e.target.value; ls.set(KEY_TF, state.tf); draw(); };
    /* 台指期的日盤／夜盤（Andy 2026-09-18 圖一）。
       預設依台北時間自己選：15:00~翌日 05:00 算夜盤。使用者可以自己切，切了就記住。*/
    state.futSession = ls.get(KEY_FUTS, '') || futSession();
    loadNightPts();
    /* 切日盤／夜盤：換的是**同一張卡片**的資料來源（數字 ＋ 圖），不是多開一塊。
       切過去先 draw() 讓畫面立刻反應，再 refresh() 去補最新一筆夜盤報價。*/
    $$('#futSeg button').forEach(b => b.onclick = () => {
      state.futSession = b.dataset.s; ls.set(KEY_FUTS, state.futSession);
      draw(); refresh(true);
    });
    $$('#m3Grid .m3-big').forEach(b => b.onclick = () => {
      state.big = state.big === b.dataset.id ? '' : b.dataset.id;
      ls.set(KEY_BIG, state.big); draw();
    });
    draw();
    refresh(true);
    schedule();
  }

  /* 夜盤點數不夠畫線時，在**同一個圖表容器裡**寫清楚為什麼，而不是留一塊空白或另外開一塊方框。
     這是刻意的誠實：期交所行情看板每次只回當下一筆，沒有分時序列可以抓，
     所以「夜盤走勢」只能由這一頁自己一筆一筆收。收到幾筆就講幾筆。 */
  function nightWhy() {
    const f = F();
    const n = state.nightPts.length;
    const err = state.futNightErr;
    return err === 'NOFUT'
      ? 'Worker 還是舊版（沒有 <code>/fut</code>）。推一次 <code>workers/quote-proxy/worker.js</code> 就會自動部署。'
      : err === 'NOFUTDATA'
      ? '現在不是夜盤時段（台北 15:00～翌日 05:00），期交所沒有回任何合約報價。'
      : err ? '夜盤報價抓不到：' + (f ? f.esc(err) : err)
      : (state.futNight && !state.futNight.inSession)
        ? '現在不是夜盤時段：期交所回的是日盤最後一筆，不能當夜盤點畫進來。'
      : n === 0 ? '還沒收到第一筆夜盤報價。'
      : `目前只收到 ${n} 筆，畫成線至少要 2 筆。`;
  }
  function nightHint(el) {
    const n = state.nightPts.length;
    const why = nightWhy();
    el.innerHTML = `<div class="m3-night">
      <div class="m3-q"><b>夜盤沒有現成的分時序列</b></div>
      <div class="note">期交所行情看板（<span class="mono">getQuoteList</span>）每次只回<b>當下一筆</b>報價，
        證交所的分時檔只有日盤。所以這張走勢圖是這一頁自己一筆一筆收的：
        夜盤每分鐘自動更新一次，一次收一個真實成交價與真實的量差，收滿 2 筆就會開始畫。</div>
      <div class="note">${why}　·　${state.futNight
        && state.futNight.inSession ? '上面那排數字是最新一筆夜盤報價（即時）。'
        : '夜盤報價還沒拿到，上面那排暫時是日盤的數字。'}</div>
    </div>`;
  }

  /* 需求二（Andy 2026-09-19：「為何這些走勢都沒有過往歷史數據，幫我新增至少3年」）。
     根因不在前端、也不在 payload —— 是**資料湖裡的指數只有 40 天**：
     `run_daily` 抓指數時寫死 since = 今天 −40 天，而回補計畫本來沒有這張表，
     所以 `data/index_ohlc` 實測只有 2026-08-06～09-18 共 32 個交易日（三個代號都一樣），
     週 K 只剩 7 根、月 K 2 根、季 K 1 根。`build_payload` 給的是 tail(1300)，它沒有截斷。
     真正的修法在 `pipeline/run_backfill.py` 的 `backfill_indices()`（3 次請求補到 2000 年），
     排在 run_plan 最前面，雲端每小時那輪跑到就會自己長出來。
     前端這邊該做的是**別讓使用者自己猜**：不到 3 年就在圖上直接講出現在有幾年、為什麼。 */
  const YEAR_BARS = 243;                  // 一年約 243 個交易日
  const WANT_BARS = YEAR_BARS * 3;        // Andy 要的下限：3 年
  function spanOf(id) {
    const b = state.lakeDaily[id];
    if (!b || !b.length) return null;
    return { n: b.length, from: String(b[0][0]).slice(0, 10), to: String(b[b.length - 1][0]).slice(0, 10) };
  }
  function lakeSpan() {
    const s = spanOf('TSE');
    if (!s) return '';
    return `　目前日線涵蓋 ${s.from} ~ ${s.to}（${s.n} 根，約 ${(s.n / YEAR_BARS).toFixed(1)} 年）。`;
  }
  /** 歷史不夠 3 年時要標在那張卡片上的話；夠長就回空字串（不夠長才是問題，夠長不用囉嗦）。 */
  function shortHistNote(x) {
    const s = spanOf(x.id);
    if (!s || s.n >= WANT_BARS) return '';
    return `${x.name}的歷史只有 ${s.n} 根日 K（${s.from} 起，約 ${(s.n / YEAR_BARS).toFixed(1)} 年）`
      + `，所以週／月／季 K 也只有這麼幾根。26 年歷史正在回補（雲端每小時一輪），補完這裡會自己變長。`;
  }

  function draw() {
    const grid = document.getElementById('m3Grid');
    if (!grid) return;
    $$('#m3Mode button').forEach(b => b.classList.toggle('on', b.dataset.m === state.mode));
    const sel = document.getElementById('m3Tf');
    if (sel) { sel.value = String(state.tf); sel.parentElement.style.display = state.mode === 'k' ? '' : 'none'; }
    const note = document.getElementById('m3Note');
    if (note) {
      note.textContent = state.mode !== 'k'
        ? '紅／綠對照昨收；下方是每分鐘成交量。時間軸固定到收盤，空白＝還沒走到。'
        : histDef(state.tf)
        ? '日／週／月／季來自資料湖（FinMind：加權 TAIEX、櫃買 TPEx、台指期 TX 近月），週月季是拿日線合成的；1 小時／4 小時走 Yahoo，只有加權有。' + lakeSpan()
        : '分 K 由每分鐘指數收盤價合成：開＝前一分收盤，高低是分鐘收盤的極值（卡片上的「高／低」才是當天真正極值）。指標與個股共用同一組設定。';
    }
    // 台指期的日盤／夜盤鈕：選中的要亮起來（以前藏在 drawFutNight 裡，拆掉之後移到這裡）
    const seg = document.getElementById('futSeg');
    if (seg) $$('button', seg).forEach(b => b.classList.toggle('on', b.dataset.s === state.futSession));
    grid.classList.toggle('big', !!state.big);
    IDX.forEach(x => {
      const card = grid.querySelector(`.m3-card[data-id="${x.id}"]`);
      if (!card) return;
      card.classList.toggle('on', state.big === x.id);
      card.style.display = (state.big && state.big !== x.id) ? 'none' : '';
      const head = card.querySelector('.m3-nums');
      if (head) head.outerHTML = cardHead(x);
      const btn = card.querySelector('.m3-big');
      if (btn) btn.textContent = state.big === x.id ? '收合 ⤡' : '展開 ⤢';
      drawOne(x);
    });
    setTimeout(() => window.dispatchEvent(new Event('resize')), 30);
  }

  function killK(id) {
    if (state.kcharts[id]) { try { state.kcharts[id].destroy(); } catch (e) { /* 忽略 */ } delete state.kcharts[id]; }
  }

  function drawOne(x) {
    const el = document.getElementById('m3c-' + x.id);
    if (!el) return;
    const night = isNight(x);
    let d = night ? seriesOf(x) : state.data[x.id];
    let err = night ? '' : state.err[x.id];
    // 歷史週期不需要今天的分時檔（Worker 沒更新也照樣看得到日線）
    if (state.mode === 'k' && histDef(state.tf)) { el.classList.remove('isempty'); drawK(x, d || {}, el); return; }
    /* 夜盤：同一個容器，只是資料換一份。
       ★ 這裡一定要用「真的是夜盤那一份」（d.night）來判斷 ——
       `seriesOf()` 在夜盤報價還沒到手時會退回日盤，那份有 300 個點，
       拿它去畫就會變成「按了夜盤卻看到日盤的線」，是最糟的一種說謊。
       點數不足 2 筆就在這裡寫清楚原因（不加 .isempty —— 版面要跟日盤一樣高，不能塌掉）。 */
    if (night) {
      killK(x.id);
      if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
      el.classList.remove('isempty');
      delete el.dataset.fallback;
      if (d && d.night && d.points.length >= 2) {
        if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
        return;
      }
      /* 有夜盤報價、但累積到的點還不夠畫線 → 在容器裡講清楚（這時候上面那排數字已經是夜盤的，
         底下卻放日盤的線會前後矛盾，所以寧可先只放說明）。*/
      if (d && d.night) { el.dataset.kind = 'nighthint'; nightHint(el); return; }
      /* 連一筆夜盤報價都沒有 → 退回日盤那條線，並在圖上標出原因。
         這是 N11 的規矩：「不該出現沒有數據」—— 畫面上要有東西，但要老實說它是什麼。*/
      const dayD = state.data[x.id];
      if (dayD && dayD.points && dayD.points.length) {
        el.dataset.fallback = '夜盤報價目前拿不到，先顯示日盤走勢';
        if (state.mode === 'k') drawK(x, dayD, el); else drawLine(x, dayD, el);
        return;
      }
      /* 連日盤的分時檔都沒有 → 問題不是「夜盤沒有序列」，是整個來源連不上
         （例如還沒設定即時來源、Worker 是舊版）。那就照日盤那一套訊息講，
         不要用夜盤的說明把真正的原因蓋掉。*/
      d = dayD; err = state.err[x.id];
    }
    if (!d || !d.points.length) {
      killK(x.id);
      if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
      el.classList.add('isempty');
      el.dataset.kind = '';
      el.innerHTML = `<div class="empty">${err === 'NOCHART'
        ? 'Worker 還是舊版（只有 /quote）。到 Cloudflare → Workers → tw-quote → 編輯程式碼，把 repo 裡 <code>workers/quote-proxy/worker.js</code> 整份貼上去再按 Deploy，這三張圖就會出現。'
        : err ? '抓不到：' + (window.App ? window.App.fmt.esc(err) : err) : '載入中…'}</div>`;
      return;
    }
    el.classList.remove('isempty');
    if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
  }

  // ---------------------------------------------------------------- 走勢圖（ECharts）
  function drawLine(x, d, el) {
    killK(x.id);
    // 從 K 線切回來時容器裡還留著 Lightweight Charts 的 DOM，不清掉 ECharts 會疊在上面
    if (el.dataset.kind !== 'line') { el.innerHTML = ''; el.dataset.kind = 'line'; }
    const f = F(); if (!f) return;
    // 夜盤走的是 15:00~翌日 05:00 的軸（凌晨那段的分鐘數是 24*60+）
    const [s0, s1] = d.night ? SESSION_NIGHT : SESSION[x.id];
    const cats = []; for (let m = s0; m <= s1; m++) cats.push(hhmm(m));
    const price = new Array(cats.length).fill(null);
    const vol = new Array(cats.length).fill(null);
    d.points.forEach(p => { const i = p.min - s0; if (i >= 0 && i < cats.length) { price[i] = p.c; vol[i] = p.s; } });
    const up = d.last != null && d.prev ? d.last >= d.prev : true;
    const col = up ? '#ff4d6d' : '#2ee59d';
    const dp = x.id === 'FUT' ? 0 : 2;
    const unit = x.id === 'FUT' ? '口' : '張';
    const A = window.App;
    // 價格軸以昨收為中心對稱，漲跌幅一眼看得出來（跟官方走勢圖同一個習慣）
    const vals = price.filter(v => v != null);
    const span = Math.max.apply(null, vals.map(v => Math.abs(v - (d.prev || v))).concat([(d.prev || 1) * 0.001]));
    const lo = (d.prev || vals[0]) - span * 1.08, hi = (d.prev || vals[0]) + span * 1.08;
    const vmax = Math.max.apply(null, vol.filter(v => v != null).concat([1]));
    A.chart(el, {
      grid: [{ left: 14, right: 58, top: 10, bottom: 74, containLabel: true },
        { left: 14, right: 58, height: 44, bottom: 24, containLabel: true }],
      tooltip: Object.assign({}, A.tip, {
        trigger: 'axis', axisPointer: { type: 'cross' },
        formatter: (ps) => {
          const i = ps[0].dataIndex;
          if (price[i] == null) return cats[i] + '<br>尚未成交';
          const c = price[i], ch = d.prev ? c - d.prev : null;
          return `<b>${cats[i]}</b><br>指數 <b class="mono">${f.n(c, dp)}</b>`
            + (ch != null ? ` <span style="color:${ch >= 0 ? '#ff4d6d' : '#2ee59d'}">${(ch > 0 ? '+' : '') + f.n(ch, dp)}（${f.pct(ch / d.prev * 100, 2)}）</span>` : '')
            + `<br>該分量 ${f.lot(vol[i] || 0)}`;
        },
      }),
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      xAxis: [
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 0, boundaryGap: false,
          axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } }),
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 1, boundaryGap: false,
          // 台指期的盤比較長（08:45–13:45），每半小時一個刻度會擠成一團
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, margin: 8,
            interval: (i) => (s0 + i) % (cats.length > 280 ? 60 : 30) === 0 },
          axisTick: { show: false }, splitLine: { show: false } }),
      ],
      yAxis: [
        // 小數位數看振幅決定：櫃買一天的區間不到 10 點，寫成整數會變成「396 396 395 395」
        Object.assign({}, A.axisStyle, { gridIndex: 0, min: lo, max: hi, position: 'right', splitNumber: 4,
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, showMinLabel: false,
            formatter: (v) => f.n(v, (hi - lo) < 10 ? 2 : (hi - lo) < 100 ? 1 : 0) },
          splitLine: { lineStyle: { color: A.CH.grid } } }),
        // 量軸只有 44px 高，放三個刻度一定疊在一起 —— interval 設成最大值等於只留「頂」那一格
        Object.assign({}, A.axisStyle, { gridIndex: 1, position: 'right', splitLine: { show: false },
          min: 0, max: vmax, interval: vmax || 1,
          axisLabel: { color: A.CH.ink3, fontSize: 9, showMinLabel: false,
            // 台指期算「口」，指數算「張」—— 單位寫錯 Andy 一眼就看得出來
            formatter: (v) => (v >= 1e4 ? (v / 1e4).toFixed(1) + ' 萬' + unit : f.i(v) + ' ' + unit) } }),
      ],
      series: [
        { type: 'line', data: price, showSymbol: false, connectNulls: false, xAxisIndex: 0, yAxisIndex: 0,
          lineStyle: { color: col, width: 1.6 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexa(col, .30) }, { offset: 1, color: hexa(col, 0) }]) },
          markLine: { silent: true, symbol: 'none', label: { show: true, position: 'insideEndTop', color: A.CH.ink3, fontSize: 10, formatter: (d.prevLabel || '昨收') + ' ' + f.n(d.prev, dp) },
            lineStyle: { color: A.CH.ink3, type: 'dashed', width: 1 },
            data: [{ yAxis: d.prev }] } },
        { type: 'bar', data: vol, xAxisIndex: 1, yAxisIndex: 1, barWidth: '70%',
          itemStyle: { color: (p) => {
            const i = p.dataIndex; const prev = i > 0 ? price[i - 1] : d.prev;
            return (price[i] != null && prev != null && price[i] >= prev) ? hexa('#ff4d6d', .7) : hexa('#2ee59d', .7);
          } } },
      ],
    }, { notMerge: true });
  }

  const hexa = (hex, a) => {
    const h = String(hex).replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const v = parseInt(n, 16);
    return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
  };

  // ---------------------------------------------------------------- K 線（KChart，與個股同一套）
  /** K 線的指標設定。跟個股頁共用 localStorage 的 `tw.kcfg`，但有兩個調整：
   *  1. 指數沒有供需區／BOS/CHoCH／停損目標，那三項在這裡沒有意義。
   *  2. 三張並排時每張只有 ~300px 高，塞四個面板等於什麼都看不到 ——
   *     並排時只留均線＋成交量，按「展開」變成整列大圖時才把使用者勾的指標全部放出來。 */
  function loadCfg(expanded) {
    const DEF = { ma: [5, 20, 60], maColor: [], maWidth: [], lineWidth: 1, st: {},
      vol: true, volma: 20, kd: { n: 9, m1: 3, m2: 3 }, macd: null, rsi: null, boll: null, bar: 9 };
    let c = DEF;
    try {
      const s = localStorage.getItem('tw.kcfg');
      if (s) c = Object.assign({}, DEF, JSON.parse(s));
    } catch (e) { /* 忽略 */ }
    c = Object.assign({}, c);
    delete c.smc; delete c.marks; delete c.lines; delete c.tfs;
    if (!expanded) { c.kd = null; c.macd = null; c.rsi = null; c.boll = null; }
    return c;
  }

  function drawK(x, d, el) {
    if (typeof window.KChart === 'undefined') { el.innerHTML = '<div class="empty">圖表函式庫載入失敗</div>'; return; }
    if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
    /* 2026-09-19（Andy N11「這邊不該出現沒有數據」）：
       櫃買與台指期沒有 1 小時／4 小時的免費來源，以前就直接在卡片上寫一句
       「沒有免費來源」然後留一塊空白 —— 使用者看到的是「這張圖壞了」。
       改成**自動退回日線並在卡片上說明**：畫面上永遠有東西可看，
       同時老實講「這個週期沒來源，改用日線」。
       fallbackTf 只影響這一張卡片，上方的週期選單不動（其他卡片仍照選的走）。*/
    let def = histDef(state.tf);
    const fbKey = x.id + '|' + state.tf;
    if (def && state.noSrc && state.noSrc[fbKey]) def = histDef('D') || def;
    let bars, tfName;
    if (def) {
      const key = x.id + '|' + def.id;
      bars = state.hist[key];
      if (!bars) {
        const err = state.histErr[key];
        killK(x.id); el.dataset.kind = '';
        if (!err) { fetchHist(x, def); el.innerHTML = '<div class="empty">載入中…</div>'; return; }
        /* 沒有這個週期的來源 → 記下來、退回日線、立刻重畫一次。
           只記一次就好，否則會無限重畫。*/
        if (err === 'NOSRC' && !(state.noSrc && state.noSrc[fbKey])) {
          state.noSrc = state.noSrc || {};
          state.noSrc[fbKey] = true;
          setTimeout(draw, 0);
          el.innerHTML = '<div class="empty">這個週期沒有免費來源，改用日線…</div>';
          return;
        }
        el.innerHTML = `<div class="empty">${window.App ? window.App.fmt.esc(
          err === 'NOLAKE' ? `${x.name}的歷史日 K 還沒進資料湖 —— 下一輪每日管線跑完（台北 15:30 / 18:30 / 21:30）就會有。`
          : err === 'NOSRC' ? `${x.name}沒有這個週期的免費來源，正在改用日線…`
          : err === 'NOCHART' ? 'Worker 還是舊版（沒有 /y）。到 Cloudflare 重貼 workers/quote-proxy/worker.js 就會有 1 小時／4 小時。'
          : '抓不到歷史 K：' + err) : err}</div>`;
        return;
      }
      tfName = def.lake ? '1d' : def.id === 'H4' ? '240m' : '60m';
      /* 圖上方那行說明。可能同時有三件事要講，所以收成一個陣列再串起來：
         ① 這個週期沒來源、已退回日線（N11）
         ② 歷史不到 3 年（Andy 2026-09-19「為何這些走勢都沒有過往歷史數據」）
         ③ 選在夜盤，但歷史 K 只有一般交易時段（日盤）那條 */
      const says = [];
      if (state.noSrc && state.noSrc[fbKey]) says.push(`${x.name}沒有這個週期的免費來源，已改用「日」`);
      if (def.lake) {
        const sh = shortHistNote(x);
        if (sh) says.push(sh);
        if (isNight(x)) says.push('歷史 K 用的是一般交易時段（日盤）收盤 —— 夜盤日 K 資料湖還沒存');
      }
      if (says.length) el.dataset.fallback = says.join('　·　'); else delete el.dataset.fallback;
    } else {
      bars = toBars(d.points, +state.tf);
      tfName = state.tf + 'm';
    }
    if (!bars || bars.length < 2) {
      killK(x.id);
      el.innerHTML = `<div class="empty">${def ? '這個週期的資料不足' : '今天的分鐘資料還不夠畫一根 K'}</div>`;
      el.dataset.kind = ''; return;
    }
    const expanded = state.big === x.id;
    // key 含日盤／夜盤：切 session 時資料整組換掉，不能沿用同一個圖表就地改
    const key = x.id + '|' + String(state.tf) + '|' + (expanded ? 'big' : 'small')
      + '|' + (d && d.night ? 'n' : 'd');
    const live0 = state.kcharts[x.id];
    /* 同一張卡、同一個週期、同樣大小 → 就地換資料。
       盤中 10 秒重畫一次，如果每次都 destroy 再 new，使用者的縮放與位置會一直被彈回最右邊，
       等於不能往左看早盤（Andy 2026-09-15 要的是「自動更新」，不是「自動跳回去」）。 */
    if (live0 && live0._m3key === key && el.dataset.kind === 'k') {
      live0.setBars(bars, tfName, true);
      live0.applyIndicators(loadCfg(expanded));
      return;
    }
    killK(x.id);
    el.innerHTML = ''; el.dataset.kind = 'k';
    // mini：不要面板標題與浮水印（那兩個的 CSS 只掛在個股頁的 #lwc 底下，放這裡會掉到卡片外面）
    const k = new window.KChart(el, { tf: tfName, mini: true, compact: !expanded });
    k._m3key = key;
    state.kcharts[x.id] = k;
    k.setBars(bars, tfName);
    const cfg = loadCfg(expanded);
    k.applyIndicators(cfg);
    const f = F();
    const dp = x.id === 'FUT' ? 0 : 2;
    k.setBarSpacing(expanded ? (cfg.bar || 9) : 5);
    // 當天的圖把整個交易日塞滿；歷史的圖看最近一段就好，不然幾百根擠成一片
    k.fitLast(def ? (expanded ? 160 : 90) : bars.length + 2);
    if (!def && d.prev != null) k.setPriceLines([{ price: d.prev,
      title: (d.prevLabel || '昨收') + ' ' + (f ? f.n(d.prev, dp) : d.prev), color: '#8ea0c4' }]);
  }

  // ---------------------------------------------------------------- 對外
  // 分頁切回來就補抓一次，不用等下一個 10 秒
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  // 跨越開盤／收盤時要換節奏（10 秒 ↔ 5 分鐘），每分鐘檢查一次就夠
  setInterval(() => { if (document.getElementById('m3')) schedule(); }, 60 * 1000);

  window.Market3 = {
    mount, refresh, draw, schedule,
    get state() { return state; },
    toBars,                                  // 驗收用
    get session() { return state.futSession; },          // 驗收用：現在看的是日盤還是夜盤
    get nightPoints() { return state.nightPts.slice(); },  // 驗收用：真的收到幾個夜盤點
    get histSpan() { return spanOf('TSE'); },             // 驗收用：日線到底有幾根、從哪天起
    get lastAt() { return state.at; },
    get ticking() { return !!state.timer; },  // 驗收用：自己的計時器有沒有在跑
    isIntraday,
  };
})();
