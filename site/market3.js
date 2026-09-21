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
 * 夜盤到底拿得到什麼（2026-09-19 查證 ＋ 2026-09-20 修正）
 *   ✔ 報價快照：期交所行情看板 `getQuoteList`（MarketType=1），Worker 的 `/fut?session=night`。
 *     每次只回**當下一筆**：現價／參考價／開高低／累計量／未平倉。fixture 在
 *     `docs/fixtures/taifex_night_probe.json`，實測 200。
 *   ◐ 夜盤分時序列：**正在接期交所的 `getChartData1M`**。
 *     2026-09-19 那次探測送了 `{"SymbolID": ["TXFJ6-F"]}` 被回 400，但錯誤訊息是
 *     `Cannot deserialize instance of java.lang.String out of START_ARRAY ... GetChartData1MReqDto["SymbolID"]`
 *     —— 也就是**這支端點存在**，它要的是字串不是陣列。
 *     ★ 所以「夜盤沒有現成的分時序列」這個結論是在**還沒正確問過一次**的情況下下的，不算數。
 *     `scripts/probe_sources.py` 已經改對（字串 ＋ `-M` 代號 ＋ 從報價清單撈近月），
 *     等 Actions 跑出 fixture 再接 parser（專案規矩：沒有真實樣本不寫 parser）。
 *     證交所的 `futures_chart.txt` 則確定只有日盤（白天那一段）。
 *   ✔ 夜盤的「日 K 歷史」FinMind 有：`TaiwanFuturesDaily` 的 `trading_session == 'after_market'`。
 *     2026-09-20 起 `pipeline/sources/finmind.py` 兩個時段都存（日盤 `FUT`、夜盤 `FUT_N`，
 *     同一次請求、不多花額度），所以歷史週期切到夜盤時會去讀 `FUT_N`；
 *     湖裡還沒長出來的期間退回 `FUT` 並在圖上講出來。
 *
 * ★ 2026-09-20 Andy：「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去，格式 follow 加權指數」
 * ------------------------------------------------------------------------------------
 * 他不接受「目前只收到 1 筆，畫成線至少要 2 筆」那塊說明方框把整張圖蓋掉。他是對的：
 * **「還沒有序列」不是「不要畫圖」的理由** —— 座標軸、參考價虛線、量柱、tooltip、
 * 工具列（走勢圖／K 線、週期下拉、展開）本來就都算得出來，跟加權指數同一套。
 * 所以現在夜盤一律**先把圖畫出來**（跟加權指數走同一個 `drawLine()` / `drawK()`），
 * 點數不足時只在圖上角落留一條窄的說明帶，而不是拿方框把圖換掉。
 * 最新那一點有呼吸燈，所以就算只有一個點，畫面上也看得到「它在哪、它還在跳」。
 *
 * 夜盤走勢的每個點都是真的：自動更新那一輪每拿到一筆夜盤報價，就把
 *   {時間, 成交價, 累計量的增量} 收進 `state.nightPts`，存在 localStorage（以 CDate 分天）。
 *   真實成交價與真實量差，不內插、不補值；代價是「只有你開著網頁的那段時間」才有點。
 *   這句話直接寫在圖上，不藏 —— 等 `getChartData1M` 接上就會換成完整的一整晚。
 *
 * ★ 呼吸燈（Andy 2026-09-20：「三張走勢圖最新的點需要做呼吸燈圓圈，
 *   只要他正在即時更新就會執行呼吸燈效果」）
 * ------------------------------------------------------------------
 * 三張走勢圖最右端那一點都有一顆小圓 ＋ 一圈擴散的光環（`.m3-pulse`）。
 * **只有「真的正在即時更新」才會呼吸**，判準見 `isPulsing()` —— 一盞會說謊的燈比沒有燈更糟。
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
    // 呼吸燈：tipKey＝上一次看到的「最後一個點」是誰；tipAt＝它最後一次真的往前走的時刻
    tipKey: {}, tipAt: {}, pulses: {}, pTimer: null,
    // lakeBack[鍵]=true：夜盤日 K（FUT_N）湖裡還沒有，這個週期先用日盤那一份
    lakeBack: {},
    // 夜盤：futSession＝日盤/夜盤；futNight＝最新一筆報價；nightPts＝累積到的真實觀測點
    futSession: 'day', futNight: null, futNightErr: '', nightPts: [], nightDate: '',
    // 期交所 getChartData1M 回來的**真正的分時序列**（2026-09-20 接上）
    futChart: null, futChartErr: '',
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
    /* 呼吸燈要能「自己熄」：資料停了之後沒有任何一輪會再呼叫 draw()，
       所以另外一組輕量的計時器負責重算亮不亮（只改 class 與位置，不重畫圖）。*/
    if (!state.pTimer) state.pTimer = setInterval(pulseTick, PULSE_PAINT);
  }
  /** 夜盤那一輪：只補一筆報價、只在真的是夜盤而且使用者也選在夜盤時才跑。 */
  async function tickNight() {
    if (document.hidden) return;
    if (!document.getElementById('m3')) return;
    if (state.futSession !== 'night' || futSession() !== 'night') return;
    // 走到這裡代表時鐘與畫面都在夜盤，不用再同步
    await pullNight();
    draw();
  }

  /** 夜盤要抓的兩樣東西：① 報價快照（未平倉只有這裡有）② 分時序列（走勢與 K 線的主體）。
   *  兩者互不依賴地失敗：序列掛了還有自己收的點，報價掛了序列自己也帶著開高低收。 */
  async function pullNight() {
    try {
      state.futNight = await fetchFut('night');
      state.futNightErr = '';
      pushNight(state.futNight);
    } catch (e) { state.futNightErr = String(e.message || e); }
    // 近月合約代號從報價清單來（每個月都在換，不寫死）；拿不到就沿用上一輪問到的那支
    const sym = (state.futNight && state.futNight.symbol) || (state.futChart && state.futChart.symbol);
    if (!sym) { state.futChartErr = state.futChartErr || 'NOSYMBOL'; return; }
    try { state.futChart = await fetchFutChart(sym); state.futChartErr = ''; }
    catch (e) { state.futChartErr = String(e.message || e); }
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
  /** 現在該看哪一段：時鐘說了算，除非使用者「在這一段裡」自己切過。
   *  舊格式（只存 'day' / 'night' 的純字串）一律當成過期 —— 那正是造成黏住的那一版。*/
  function pickSession() {
    const now = futSession();
    let raw = '';
    try { raw = ls.get(KEY_FUTS, '') || ''; } catch (e) { raw = ''; }
    if (!raw || raw.charAt(0) !== '{') return now;          // 沒存過、或是舊格式 → 跟時鐘
    try {
      const o = JSON.parse(raw);
      return (o && o.base === now && (o.sess === 'day' || o.sess === 'night')) ? o.sess : now;
    } catch (e) { return now; }
  }
  /** 時段翻頁時把畫面帶回當下該看的那一段。回傳「有沒有真的換」。 */
  function syncSession() {
    const want = pickSession();
    if (want === state.futSession) return false;
    state.futSession = want;
    return true;
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

  /* ---- ★ 夜盤（與日盤）的真正分時序列：期交所 getChartData1M -------------------
     2026-09-20 才確認這支能用，前一輪把它判死是因為**問錯了**：
     送 `{"SymbolID": ["TXFJ6-F"]}`（陣列）被回 400，訊息是
     `Cannot deserialize instance of java.lang.String out of START_ARRAY`
     —— 它要的是字串。改成字串之後：
       夜盤 TXFJ6-M → 200，`RtData.Ticks` **822 筆**（15:01 ~ 翌日 05:00）
       日盤 TXFJ6-F → 200，300 筆（08:46 ~ 13:45）
     日盤那 300 筆的筆數與區間跟證交所 `futures_chart.txt` **完全對得上**，
     等於交叉驗證了口徑：T 是台北時間、O/H/L/C 是那一分鐘真正的開高低收、V 是該分鐘口數。
     （fixture：docs/fixtures/taifex_night_probe.json）

     ★ 這比證交所的分時檔還好一件事：它給**真的分鐘 OHLC**。
     證交所那個檔只給每分鐘收盤價，所以我們的 K 棒開盤是「前一分鐘收盤」、
     高低是「分鐘收盤的極值」（檔頭那段說明講的就是這個）。這支不用合成。

     ⚠ 時間欄位有一個坑，先講清楚我怎麼處理的：
     夜盤倒數第二筆是 `"046000"` —— 硬切 HHMMSS 會得到 **04:60:00**，不是合法時間。
     這跟 CLAUDE.md 記過的「重大訊息 `70003` 要補零成 `07:00:03`」是同一類坑。
     我**沒有辦法從 fixture 數出它是偶發還是每個整點都有** —— 因為 fixture 為了不肥
     只留了頭 5 筆尾 2 筆（822 筆的中間被截掉了，那是我自己寫的 `shrink()` 幹的）。
     所以這裡採**兩種解釋都不會畫錯**的做法：
       ① `MM >= 60` 一律進位到下一個小時（04:60 → 05:00）
       ② 同一分鐘只留**最後一筆**（後到的那筆累積得比較完整；
          實測 046000 的量 36、050000 的量 47，後者確實是前者的超集）
     而且 `scripts/probe_sources.py` 已經補上 `series_stats`，
     下一次探測會直接把「有幾個怪時間、缺哪幾分鐘、量跟 Quote 對不對得上」算出來，
     到時候再回來把這段註解換成結論。★ 在那之前，這段是處理方式，不是結論。 */
  const FUT_TICK_MAX = 2000;                 // 夜盤 840 分鐘，留兩倍的餘裕就夠

  /** `"150100"` / `"046000"` → 台北分鐘數（跨午夜 +1440）。看不懂就回 null，寧可丟掉那一筆。 */
  function tickMin(t, startMin) {
    const s0 = String(t == null ? '' : t).trim();
    if (!/^\d{5,6}$/.test(s0)) return null;
    const s6 = s0.length === 5 ? '0' + s0 : s0;
    const h = +s6.slice(0, 2), mi = +s6.slice(2, 4), se = +s6.slice(4, 6);
    if (h >= 24) return null;
    let m = mi >= 60 ? h * 60 + 60 : h * 60 + mi + (se >= 60 ? 1 : 0);
    if (m < startMin) m += 24 * 60;           // 跨午夜
    return m;
  }

  /** 期交所分時的原始回應 → `{symbol, date, startMin, points:[{ms,min,o,h,l,c,s}]}`。 */
  function parseFutChart(j, baseDate) {
    const rt = (j || {}).RtData || {};
    const sess = ((rt.Info || {}).Sessions || [])[0] || {};
    const st = String(sess.Start || '1500');
    const startMin0 = (+st.slice(0, 2)) * 60 + (+st.slice(2, 4));
    // 夜盤從 15:00 起算，凌晨那段記成 24*60+，跟這個檔其他地方同一套
    const startMin = startMin0;
    const q = rt.Quote || {};
    const date = String(q.CDate || baseDate || '');
    const field = (rt.Field || []).map(String);
    const ix = (k, d) => { const i = field.indexOf(k); return i >= 0 ? i : d; };
    const iT = ix('T', 0), iO = ix('O', 1), iH = ix('H', 2), iL = ix('L', 3), iC = ix('C', 4), iV = ix('V', 5);
    const base = dateBaseMs(date);
    const byMin = {};
    (rt.Ticks || []).forEach(row => {
      if (!row || row.length < 5) return;
      const m = tickMin(row[iT], startMin);
      const c = num(row[iC]);
      if (m === null || c === null) return;
      // 同一分鐘只留最後一筆（見上面那段說明）
      byMin[m] = { ms: base + m * 60 * 1000, min: m,
        o: num(row[iO]), h: num(row[iH]), l: num(row[iL]), c, s: num(row[iV]) || 0 };
    });
    const pts = Object.keys(byMin).map(k => byMin[k]).sort((a, b) => a.min - b.min);
    return {
      symbol: String(rt.SymbolID || ''), name: String(rt.DispCName || ''),
      date, startMin, points: pts.slice(-FUT_TICK_MAX),
      // Quote 跟報價清單同一批欄位，拿來補「上排那些數字」（未平倉夜盤這裡是空的，走 /fut）
      quote: {
        open: num(q.COpenPrice), high: num(q.CHighPrice), low: num(q.CLowPrice),
        last: num(q.CLastPrice), ref: num(q.CRefPrice), vol: num(q.CTotalVolume),
      },
    };
  }

  /** 台北 YYYYMMDD 的 00:00 對應的 UTC 毫秒。 */
  function dateBaseMs(yyyymmdd) {
    const s0 = String(yyyymmdd || '');
    if (s0.length !== 8) return Date.now() - (Date.now() % 86400000);
    return Date.UTC(+s0.slice(0, 4), +s0.slice(4, 6) - 1, +s0.slice(6, 8)) - 8 * 3600 * 1000;
  }

  async function fetchFutChart(symbol) {
    const base = proxy();
    if (!base) throw new Error('還沒設定即時來源');
    if (!/^[A-Za-z0-9]{3,8}-[FM]$/.test(String(symbol || ''))) throw new Error('NOSYMBOL');
    const r = await fetch(`${base}/futchart?symbol=${encodeURIComponent(symbol)}&t=${Date.now()}`,
                          { cache: 'no-store' });
    // 404＝Worker 還是舊版（沒有 /futchart），要 Andy 去 Cloudflare 重貼一次
    if (r.status === 404) throw new Error('NOFUTCHART');
    if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
    const j = await r.json();
    if (String(j.RtCode || '0') !== '0') throw new Error('期交所回 RtCode ' + j.RtCode);
    const out = parseFutChart(j);
    if (!out.points.length) throw new Error('NOFUTTICKS');
    return out;
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
  /** 夜盤的序列 → 跟 `parse()` 同一個形狀，這樣走勢圖與 K 線可以完全共用。
   *
   *  ★ 兩個來源接在一起（2026-09-20），跟個股那一套（DECISIONS #126）同一個想法：
   *    主體 ← 期交所 `getChartData1M` 的分時序列（**一整晚都在**，而且是真的分鐘 OHLC）
   *    右緣 ← 這一頁自己每分鐘收到的報價（只補「官方序列最後一筆之後」的那幾分鐘）
   *  官方序列本身就會跟著更新，所以右緣通常只差 0~1 分鐘；
   *  真正的用處是官方那支暫時失敗時，畫面右邊不會停住。
   *  官方序列拿不到時就整條退回自己收的點（以前唯一的來源）。 */
  function nightSeries() {
    const q = state.futNight;
    const fc = state.futChart;
    const base = nightBaseMs();
    // 自己收的點（[分鐘, 價, 累計量, 該段量]）
    const mine = state.nightPts.map(p => ({
      // ms 是真正的 UTC epoch 毫秒（toBars 會自己 +8 小時換成台北牆鐘）
      ms: base + p[0] * 60 * 1000,
      min: p[0], c: p[1], s: p[3] || 0,
    }));
    let pts, src;
    if (fc && fc.points.length && (!q || !q.symbol || fc.symbol === q.symbol)) {
      const lastMin = fc.points[fc.points.length - 1].min;
      pts = fc.points.concat(mine.filter(p => p.min > lastMin));
      src = 'taifex';
    } else {
      pts = mine;
      src = 'self';
    }
    return {
      id: 'FUT', night: true, src,
      name: q ? (q.name || '') : (fc ? fc.name : ''),
      date: q ? q.date : (fc ? fc.date : state.nightDate), time: q ? q.time : '',
      prev: q ? q.ref : (fc ? fc.quote.ref : null), prevLabel: '參考價',
      open: q ? q.open : (fc ? fc.quote.open : null),
      high: q ? q.high : (fc ? fc.quote.high : null),
      low: q ? q.low : (fc ? fc.quote.low : null),
      last: q ? q.last : (fc ? fc.quote.last : null),
      vol: q ? q.vol : (fc ? fc.quote.vol : null), amt: null, oi: q ? q.oi : null,
      symbol: q ? q.symbol : (fc ? fc.symbol : ''),
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
      /* 成交金額（百萬元）；台指期沒有。
         ★ 加權指數這一筆就是**台股當日累積成交值**，而且是盤中就有的真實值
           （對照 fixture：info.v = 630917 百萬 ↔ staticObj.tz = 630,917,830,610 元）。
           「盤中即時資金去向」的分母用的就是它 —— 這張圖每分鐘本來就會抓，
           所以拿它當分母是**零額外請求、而且不是估算值**。
           取用點見下面的 `Market3.marketAmt`。*/
      amt: num(info.v),
      points: pts,
    };
  }

  async function refresh(manual) {
    if (state.busy) return;
    if (!document.getElementById('m3')) return;          // 不在總覽就不用抓
    // 分頁切走就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    /* ★ 每一輪都重新評估要看哪一段 —— 網頁可能整天開著，跨過 13:45（日盤收）
       或 15:00（夜盤開）時要自己翻過去，不能等使用者重新整理。*/
    syncSession();
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
      jobs.push(pullNight());
    }
    await Promise.all(jobs);
    state.busy = false; state.at = Date.now();
    state.fails = IDX.every(x => state.err[x.id]) ? state.fails + 1 : 0;
    draw();
  }

  /** 這張卡這個歷史週期，要讀資料湖裡的哪一個代號。
   *  台指期夜盤有自己的日 K：FinMind `TaiwanFuturesDaily` 的 `after_market`，
   *  2026-09-20 起 `pipeline/sources/finmind.py` 存成 `FUT_N`（跟日盤 `FUT` 同一張表、同一次請求）。
   *  湖裡還沒長出來的那段期間會退回 `FUT`，並在圖上寫出來（見 drawK 的 says）。 */
  function lakeSym(x) { return (isNight(x) && x.id === 'FUT') ? 'FUT_N' : x.id; }

  /** 歷史 K。日／週／月／季走資料湖（index_ohlc.json）；1 小時／4 小時走 Yahoo（只有加權有）。 */
  async function fetchHist(x, def) {
    const sym = def.lake ? lakeSym(x) : x.id;
    const key = sym + '|' + def.id;
    if (state.hist[key] || state.histBusy[key]) return;
    if (def.lake) {
      state.histBusy[key] = true;
      try {
        const A = window.App;
        const all = await A.load('index_ohlc', { fallback: {} });
        let bars = (all && all[sym]) || [];
        // 夜盤日 K 還沒進湖 → 退回日盤那一份，並記下來（卡片上要講出這件事）
        if (!bars.length && sym === 'FUT_N') {
          bars = (all && all.FUT) || [];
          state.lakeBack[key] = true;
        } else {
          delete state.lakeBack[key];
        }
        if (!bars.length) throw new Error('NOLAKE');
        bars = bars.map(b => b.slice());
        // 原始日線另外留一份：週／月／季看起來「只有幾根」時，要能講出日線到底有幾年（需求二）
        state.lakeDaily[sym] = bars.slice();
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
      /* ★ 有真的分鐘 OHLC 就用真的（期交所 getChartData1M 會給 O/H/L/C）；
         只有收盤價的來源（證交所分時檔）才照舊合成。
         合成出來的高低是「分鐘收盤的極值」，不是那一分鐘真正的高低 ——
         兩者混在同一張圖上會看起來像同一回事，所以哪一根是真的要由資料決定。 */
      const po = p.o != null ? p.o : (prevClose === null ? p.c : prevClose);
      const ph = p.h != null ? p.h : Math.max(po, p.c);
      const pl = p.l != null ? p.l : Math.min(po, p.c);
      if (k !== key) {
        if (cur) { out.push(cur); prevClose = cur[4]; }
        key = k;
        cur = [Math.floor(p.ms / 1000) + 8 * 3600, po, ph, pl, p.c, p.s * 1000];
      } else {
        cur[2] = Math.max(cur[2], ph); cur[3] = Math.min(cur[3], pl);
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
    // 有期交所的分時序列，或有一筆真的落在夜盤時段的報價 —— 兩者任一就是「夜盤那一份」。
    // 兩個來源互不依賴：序列掛了還有報價，報價掛了序列自己也帶著開高低收。
    if (isNight(x) && ((state.futNight && state.futNight.inSession) || state.futChart)) return nightSeries();
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
       ★ 2026-09-21 改掉一個會讓人以為壞掉的行為（Andy：「日盤跟夜盤統一一頁，
         到夜盤的週期走勢圖就顯示夜盤的，同理日盤就是日盤」）。
         以前是 `ls.get(KEY_FUTS, '') || futSession()` ——
         **使用者按過一次之後那個選擇就永久記住，再也不會跟著時間走**。
         他 09:36（日盤時段）打開看到的還停在夜盤，卡片上寫「夜盤報價未取得」，
         而夜盤 05:00 就收了、當然拿不到 —— 畫面看起來像壞掉，其實是黏住了。
         現在：**預設一律跟著台北時間走**；手動切只在「做選擇時的那個時段」內有效，
         時段一翻（日盤↔夜盤）就自動回到當下該看的那一個。
         存的是 {sess, base}：base＝做這個選擇時時鐘在哪一段，用來判斷過期。*/
    state.futSession = pickSession();
    loadNightPts();
    /* 切日盤／夜盤：換的是**同一張卡片**的資料來源（數字 ＋ 圖），不是多開一塊。
       切過去先 draw() 讓畫面立刻反應，再 refresh() 去補最新一筆夜盤報價。*/
    $$('#futSeg button').forEach(b => b.onclick = () => {
      state.futSession = b.dataset.s;
      // 連同「做這個選擇時時鐘在哪一段」一起存，時段翻頁時才知道要作廢
      try { ls.set(KEY_FUTS, JSON.stringify({ sess: state.futSession, base: futSession() })); }
      catch (e) { /* 私密視窗 */ }
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

  /* 夜盤的說明帶。
     ★ 2026-09-20 Andy：「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去，格式 follow 加權指數」
     以前點數不足 2 筆時，是拿一塊說明方框**把整張圖換掉**。他不接受，而且他是對的 ——
     「還沒有序列」不是「不要畫圖」的理由：座標軸、參考價虛線、量柱、tooltip、
     工具列本來就都算得出來，跟加權指數同一套。
     所以現在一律先畫圖，說明縮成圖上角落一條窄帶，而且只在**還沒有官方序列**時才出現。

     退場說明也改寫過：以前寫「夜盤沒有現成的分時序列」——
     那句話在我們還沒正確問過期交所那支端點之前是不精確的（我們問錯了，送了陣列）。 */
  function nightWhy() {
    const f = F();
    const e1 = state.futChartErr, e2 = state.futNightErr;
    const n = state.nightPts.length;
    if (e1 === 'NOFUTCHART')
      return 'Worker 還是舊版（沒有 <code>/futchart</code>）。到 Cloudflare → Workers → tw-quote，'
        + '把 repo 裡 <code>workers/quote-proxy/worker.js</code> 整份重貼一次再 Deploy，這條線就會變成一整晚的分時。';
    if (e2 === 'NOFUT')
      return 'Worker 還是舊版（沒有 <code>/fut</code>）。推一次 <code>workers/quote-proxy/worker.js</code> 就會自動部署。';
    if (e2 === 'NOFUTDATA')
      return '現在不是夜盤時段（台北 15:00～翌日 05:00），期交所沒有回任何合約報價。';
    if (e1 === 'NOFUTTICKS') return '期交所的分時端點回了空序列（通常是這一晚還沒開始）。';
    if (e1 === 'NOSYMBOL') return '還沒問到今天的近月合約代號（那是從夜盤報價清單撈的）。';
    if (e1) return '夜盤分時抓不到：' + (f ? f.esc(e1) : e1);
    if (e2) return '夜盤報價抓不到：' + (f ? f.esc(e2) : e2);
    if (state.futNight && !state.futNight.inSession)
      return '現在不是夜盤時段：期交所回的是日盤最後一筆，不能當夜盤點畫進來。';
    return n === 0 ? '還沒收到第一筆夜盤報價。' : `目前自己收到 ${n} 筆，連成線至少要 2 筆。`;
  }

  /** 圖畫完之後補上（或移除）那條說明帶。
   *  三種狀態、三種講法 —— 講法的輕重要跟「畫面上的東西有多可信」對齊：
   *    ① 官方序列到手      → 什麼都不用講，整條拿掉
   *    ② 自己收的點畫得成線 → 圖是真的、線也是真的，只是來源還不是官方，
   *                          用圖上方那一行細註講就好，不要拿方框蓋住一張能看的圖
   *    ③ 連線都畫不成      → 這時候圖上幾乎沒東西，才輪到說明帶出場 */
  function nightNote(el, d) {
    const had = el.querySelector('.m3-night');
    if (d && d.src === 'taifex' && d.points.length >= 2) { if (had) had.remove(); return; }
    if (d && d.points.length >= 2) {
      if (had) had.remove();
      /* 這一行是 ::before 畫的，會把底下的圖往下推 —— 所以只能一句話。
         「為什麼還沒接上」那些細節留給說明帶（連線都畫不成的時候才出場）。*/
      el.dataset.fallback = '這條線是本頁每分鐘自己收的真實成交價；期交所的完整分時正在接';
      return;
    }
    const box = had || document.createElement('div');
    box.className = 'm3-night';
    box.innerHTML = `<div class="m3-q"><b>正在接期交所的分時端點</b></div>
      <div class="note">夜盤的完整分時序列走期交所 <span class="mono">getChartData1M</span>
        （2026-09-20 實測可用，一晚 822 筆）。接上之前，這條線是這一頁每分鐘自己收一個
        真實成交價收出來的，收滿 2 筆才連得成線。${nightWhy()}</div>`;
    if (!had) el.appendChild(box);
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
    const s = spanOf(lakeSym(x)) || spanOf(x.id);
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
    // K 線模式、空狀態、退回日盤 —— 這些情況下 paintPulse 會自己把燈移掉
    paintPulses();
    setTimeout(() => window.dispatchEvent(new Event('resize')), 30);
  }

  function killK(id) {
    if (state.kcharts[id]) { try { state.kcharts[id].destroy(); } catch (e) { /* 忽略 */ } delete state.kcharts[id]; }
  }

  function drawOne(x) {
    const el = document.getElementById('m3c-' + x.id);
    if (!el) return;
    const night = isNight(x);
    /* ★ 2026-09-21（Andy 的截圖：日盤被選取，畫面上卻寫著「夜盤報價目前拿不到」）
       `dataset.fallback` 只在夜盤那條路徑裡被清掉，所以從夜盤切回日盤時那句話會留著。
       它是用 CSS 的 ::before 印出來的，所以不會報錯、只會一直說謊。
       切到日盤時一律先清乾淨，需要的人自己再設。*/
    if (!night) delete el.dataset.fallback;
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
      el.classList.remove('isempty');
      delete el.dataset.fallback;
      /* ★ 2026-09-20：夜盤一律**先把圖畫出來**，走的就是加權指數那兩支
         （`drawLine()` / `drawK()`）—— 同一套座標軸、同一排工具列、同一種 tooltip。
         以前點數不足 2 筆時是拿說明方框把整張圖換掉，Andy 明確說不接受。
         點數不足時只在圖上角落留一條窄的說明帶（`nightNote()`），
         而最新那一點有呼吸燈，所以就算只有一個點，也看得到它在哪、還在不在跳。 */
      if (d && d.night) {
        if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
        nightNote(el, d);
        return;
      }
      /* 連一筆夜盤報價都沒有 → 退回日盤那條線，並在圖上標出原因。
         這是 N11 的規矩：「不該出現沒有數據」—— 畫面上要有東西，但要老實說它是什麼。*/
      const dayD = state.data[x.id];
      if (dayD && dayD.points && dayD.points.length) {
        const had = el.querySelector('.m3-night'); if (had) had.remove();
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
      // 沒資料時先問「是不是根本還沒開盤」，再落回「載入中」——
      // 開盤前寫「載入中…」會讓人以為壞掉（Andy 2026-09-21 就是這樣問的）
      const hint = sessionHint(x, x.id === 'FUT' && state.futSession === 'night');
      el.innerHTML = `<div class="empty">${err === 'NOCHART'
        ? 'Worker 還是舊版（只有 /quote）。到 Cloudflare → Workers → tw-quote → 編輯程式碼，把 repo 裡 <code>workers/quote-proxy/worker.js</code> 整份貼上去再按 Deploy，這三張圖就會出現。'
        : err ? '抓不到：' + (window.App ? window.App.fmt.esc(err) : err)
        : hint || '載入中…'}</div>`;
      return;
    }
    el.classList.remove('isempty');
    if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
  }

  /* ★ 2026-09-21（Andy：「為何這是載入中，台指不應該先開始了嗎 在 08:30」）
     以前只要沒資料又沒錯誤就一律印「載入中…」，所以**開盤前打開網頁，三張圖會永遠寫著載入中**
     —— 看起來像壞掉，而其實只是還沒開盤。他 07:50 打開時：
       現貨 09:00 才正式開盤（08:30 只是盤前集合競價試撮，不成交）
       台指期日盤 08:45 開始
       台指期夜盤 15:00~翌日 05:00，05:00 就收了
     三個都還沒有資料，是對的；錯的是我們把「還沒開始」講成「正在載入」。

     ★ 08:30 不是台指期開盤時間。這一點要寫在程式裡，不然下次還會有人搞混。 */
  function sessionHint(x, night) {
    const d = (() => {
      try { return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' })); }
      catch (e) { return new Date(); }
    })();
    const w = d.getDay(), m = d.getHours() * 60 + d.getMinutes();
    const hhmm2 = (t) => String(Math.floor((t % 1440) / 60)).padStart(2, '0') + ':'
      + String(t % 60).padStart(2, '0');
    if (night) {
      // 夜盤跨午夜：15:00(900) ~ 翌日 05:00(300)。週五夜盤跨到週六凌晨，週日晚上沒有夜盤。
      const inNight = (m >= 900 && w >= 1 && w <= 5) || (m < 300 && w >= 2 && w <= 6);
      if (inNight) return '';                       // 真的在夜盤裡卻沒資料 → 交給原本的錯誤訊息
      if (w === 6 || w === 0) return '週末休市 · 夜盤週一 15:00 開始';
      return m < 900 ? '夜盤尚未開始 · 15:00 開盤（到翌日 05:00）'
                     : '夜盤已收盤 · 15:00 再開';
    }
    const [s0, s1] = SESSION[x.id] || SESSION.TSE;
    if (w === 0 || w === 6) return '週末休市 · 下一個交易日 ' + hhmm2(s0) + ' 開盤';
    if (m < s0) {
      // 現貨 08:30 開始盤前試撮，但那不是成交，所以講清楚「試撮中」而不是「開盤了」
      const pre = x.id !== 'FUT' && m >= 8 * 60 + 30;
      return pre ? '盤前試撮中（不成交）· ' + hhmm2(s0) + ' 正式開盤'
                 : '尚未開盤 · ' + hhmm2(s0) + ' 開始';
    }
    if (m > s1 + 5) return '今天已收盤（' + hhmm2(s1) + '）';
    return '';                                      // 在盤中卻沒資料 → 交給原本的錯誤訊息
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

    /* ---- 呼吸燈：標出「最新的那一點」，而且只在真的還在更新時才呼吸。
       位置不是算出來寫死的，是每次跟 ECharts 要（`convertToPixel`），
       所以展開／收合、縮放視窗、換主題之後都不會飄掉。 */
    let idx = -1;
    for (let i = price.length - 1; i >= 0; i--) if (price[i] != null) { idx = i; break; }
    markMove(x, d);
    let i0 = -1;
    for (let i = 0; i < price.length; i++) if (price[i] != null) { i0 = i; break; }
    state.pulses[x.id] = {
      idx, i0, val: idx >= 0 ? price[idx] : null, col,
      label: idx >= 0 ? cats[idx] : '', night: !!d.night, live: isPulsing(x, d),
    };
    paintPulse(x.id);
  }

  /* ================================================================ 呼吸燈
     Andy 2026-09-20：「三張走勢圖最新的點需要做呼吸燈圓圈…
                        只要他正在即時更新就會執行呼吸燈效果」

     ★ 判準要能撐住「這盞燈在說謊嗎」這個問題。
     會呼吸的三個條件，全部成立才亮：
       ① 分頁在前景（`document.hidden === false`）
          —— 分頁在背景時 `refresh()` 直接 return、根本沒在打端點，亮著就是假的。
       ② 現在是走勢圖模式
          —— K 線沒有「最新的那一個點」這個東西，最右邊那根是「還沒收的 K 棒」，
             它的語彙是 K 棒不是亮點，硬掛一顆燈只會讓人以為那是別的訊號。
       ③ ★這條才是重點：這條線的**最後一個點，最近真的往前走過**。
          量的是「資料有沒有在動」，不是「計時器有沒有在跑」——
          收盤、來源掛掉、Worker 回舊值，這幾種情況計時器都還在轉，但資料是死的。
          所以判準放在資料上：最後一個點的 (分鐘, 價) 一變，就記一次時間戳；
          超過 PULSE_WIN 個輪詢週期沒變，燈就自己熄。
     另外「第一次看到這條線」不算往前走 —— 不然盤後打開網頁，燈會先騙你 30 秒。 */
  const PULSE_WIN = 3;                    // 幾個輪詢週期沒有新點就熄燈
  const PULSE_PAINT = 4 * 1000;           // 多久重算一次燈的位置與亮不亮

  /** 這條線「最後一個點」的身分證。分鐘或價格任一個變了，就是真的往前走了。 */
  function tipKey(d) {
    const pts = d && d.points;
    if (!pts || !pts.length) return '';
    const p = pts[pts.length - 1];
    return p.min + ':' + p.c;
  }
  /** 同一張卡的日盤與夜盤是兩條不同的線，時間戳要分開記，不然切過去會沿用對方的。 */
  const pulseId = (x, d) => x.id + (d && d.night ? 'N' : '');
  /** 記一次「這條線有沒有往前走」。第一次看到只記身分、不算走過（見上面最後一句）。 */
  function markMove(x, d) {
    const k = tipKey(d);
    if (!k) return;
    const id = pulseId(x, d);
    if (!(id in state.tipKey)) { state.tipKey[id] = k; return; }
    if (state.tipKey[id] !== k) { state.tipKey[id] = k; state.tipAt[id] = Date.now(); }
  }
  /** 這張卡現在該不該呼吸。 */
  function isPulsing(x, d) {
    if (document.hidden) return false;
    if (state.mode !== 'line') return false;
    const at = state.tipAt[pulseId(x, d)] || 0;
    if (!at) return false;
    // 夜盤自己有一組 60 秒的計時器，日盤跟著盤中 10 秒／盤後 5 分鐘那一組
    const cadence = (d && d.night) ? MS_NIGHT : (state.tickMs || MS_LIVE);
    return Date.now() - at <= cadence * PULSE_WIN;
  }

  /** 把某一張卡的呼吸燈畫到「最新那一點」的像素位置上。
   *  位置是每次都跟 ECharts 重新要的（`convertToPixel`），所以縮放視窗、
   *  展開／收合、切主題之後都不會飄掉。 */
  function paintPulse(id) {
    const info = state.pulses[id];
    const el = document.getElementById('m3c-' + id);
    if (!el) return;
    let dot = el.querySelector('.m3-pulse');
    const inst = (typeof echarts !== 'undefined') ? echarts.getInstanceByDom(el) : null;
    // 不是走勢圖、沒有點、圖表不在了 → 燈就不該存在（留著會浮在 K 線上變成假訊號）
    if (!info || info.idx < 0 || !inst || el.dataset.kind !== 'line') {
      if (dot) dot.remove();
      return;
    }
    if (!dot) {
      dot = document.createElement('div');
      dot.className = 'm3-pulse';
      // 兩層：core＝最新點本身（永遠看得到），ring＝會呼吸的光環（只有在更新時才動）
      dot.innerHTML = '<i class="m3-ring"></i><i class="m3-core"></i>';
      el.appendChild(dot);
    }
    const pos = inst.convertToPixel({ seriesIndex: 0 }, [info.idx, info.val]);
    if (!pos || !isFinite(pos[0]) || !isFinite(pos[1])) { dot.style.display = 'none'; return; }
    dot.style.display = '';
    dot.style.left = pos[0] + 'px';
    dot.style.top = pos[1] + 'px';
    /* ★ 2026-09-21（Andy：「這點點怎麼不在正確位置上」）
       量出來的事實：那顆點的位置是**精準的**（實測 convertToPixel 給的座標與它的
       style.left/top 完全相同，一個像素都沒偏）。看起來脫節的原因是**它比線還大**——
       開盤 8 分鐘時，整段資料在 5 小時的軸上只佔 **4.6px**，
       而光環直徑 16px、核心 7px，等於一顆球掛在一條髮絲旁邊。
       所以這裡讓燈跟著「資料實際佔幾 px」縮：資料很窄時把光環收到和資料差不多寬，
       核心留 5px（再小就看不見了，那才是真的幫倒忙）。
       ★ 不要改成「把軸縮到目前為止」——「時間軸固定到收盤」是刻意的決定，
         而且那句話就印在卡片上方（空白＝還沒走到）。要改是產品決策，不是這裡的事。*/
    let spanPx = Infinity;
    try {
      const p0 = inst.convertToPixel({ seriesIndex: 0 }, [info.i0 != null ? info.i0 : 0, info.val]);
      if (p0 && isFinite(p0[0])) spanPx = Math.abs(pos[0] - p0[0]);
    } catch (e) { /* 圖還沒排好版就先不縮 */ }
    const tiny = spanPx < 20;
    dot.classList.toggle('tiny', tiny);
    dot.style.setProperty('--r', (tiny ? Math.max(8, Math.round(spanPx) + 4) : 16) + 'px');
    dot.style.setProperty('--c', info.col);
    dot.classList.toggle('on', info.live);
    dot.dataset.at = info.label || '';
    dot.dataset.live = info.live ? '1' : '0';
    dot.title = info.live
      ? `最新一筆：${info.label}（正在即時更新）`
      : `最新一筆：${info.label}（目前沒有在更新）`;
  }
  function paintPulses() {
    Object.keys(state.pulses).forEach(paintPulse);
  }
  /** 重算「還在不在更新」並重畫。資料沒動也要跑，燈才會自己熄。 */
  function pulseTick() {
    IDX.forEach(x => {
      const info = state.pulses[x.id];
      if (!info) return;
      info.live = isPulsing(x, info.night ? { night: true } : {});
    });
    paintPulses();
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
      const key = (def.lake ? lakeSym(x) : x.id) + '|' + def.id;
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
        /* 夜盤的歷史 K（2026-09-20）：資料湖有 `FUT_N` 就直接用它，並講明這是盤後交易時段的日 K；
           還沒長出來時退回日盤並把原因寫出來 —— 兩種情況畫面上看起來一樣，所以一定要講。*/
        if (isNight(x)) {
          says.push(state.lakeBack[key]
            ? '夜盤日 K 資料湖還沒長出來（FUT_N），先用一般交易時段（日盤）那一條'
            : '這是夜盤（盤後交易時段）的日 K，跟上面的日盤是兩條不同的線');
        }
      }
      if (says.length) el.dataset.fallback = says.join('　·　'); else delete el.dataset.fallback;
    } else {
      bars = toBars(d.points, +state.tf);
      tfName = state.tf + 'm';
    }
    /* 至少要有一根才畫得出東西。★ 門檻從 2 根降到 1 根（2026-09-20）：
       夜盤剛開盤只有一根時，以前會整張換成「資料還不夠畫一根 K」——
       但那時候明明已經有一根真的 K 棒了，Lightweight Charts 畫一根沒有問題。
       「資料少」該由圖自己表現，不該用一塊文字把圖換掉。 */
    if (!bars || bars.length < 1) {
      killK(x.id);
      el.innerHTML = `<div class="empty">${def ? '這個週期的資料不足' : '今天還沒有任何分鐘資料'}</div>`;
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
  /* ★ 順便處理呼吸燈：分頁切到背景時 `refresh()` 直接 return（不打端點），
     燈還在呼吸就是在說謊 —— 所以**切走的那一刻**就要重算一次，不能等下一輪。
     （全站的 visibilitychange 慣例寫在 app.js，但那個檔這一輪不歸我改，所以自己掛一個。）*/
  document.addEventListener('visibilitychange', () => {
    pulseTick();
    if (!document.hidden) refresh();
  });
  // 視窗一縮，ECharts 的座標就換了一組 —— 燈的位置要跟著重新跟它要一次
  window.addEventListener('resize', () => {
    clearTimeout(state._rzT);
    state._rzT = setTimeout(paintPulses, 120);
  });
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
    /** 台股當日累積成交值（元）。盤中即時、真實值不是估算 —— 見上面 `amt` 的註解。
     *  「即時資金去向」的分母用這個；分子（各板塊成交值）只能用「價×量」估算，
     *  所以**板塊佔比要用「板塊 ÷ 所有板塊加總」算**，不要拿估算的分子去除這個真實分母，
     *  那個百分比會系統性偏掉。 */
    get marketAmt() {
      const d = state.data && state.data.TSE;
      return d && d.amt != null ? d.amt * 1e6 : null;
    },
    get ticking() { return !!state.timer; },  // 驗收用：自己的計時器有沒有在跑
    // 驗收用：三張圖的呼吸燈現在各自亮不亮、燈標在哪一分鐘
    get pulses() {
      const o = {};
      IDX.forEach(x => { const p2 = state.pulses[x.id]; if (p2) o[x.id] = { live: !!p2.live, at: p2.label }; });
      return o;
    },
    get futChart() { return state.futChart; },   // 驗收用：期交所分時序列接到了沒
    parseFutChart, tickMin,                      // 驗收用：時間欄位的坑（046000）有沒有處理對
    isIntraday,
  };
})();
