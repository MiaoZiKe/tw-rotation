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
 * ★ 2026-09-23 Andy：「幫我修復 夜盤拿不到資訊的問題，並且若沒有資訊則空白」
 * ------------------------------------------------------------------------------------
 * 他的截圖：台北 18:3x、分頁選在「夜盤」，徽章寫「夜盤報價未取得」，圖上一行黃字
 * 「夜盤報價目前拿不到，先顯示日盤走勢」，而**下面畫的是日盤的線**。
 * 那是這支檔案裡最糟的一種說謊：一行小字擋不住第一眼的印象，
 * 使用者會直接把日盤那條線當成夜盤在動。**畫錯的線比空白更會誤導。**
 * 所以現在拿不到夜盤資料時：
 *   圖表區留白（只留一句極簡狀態文字，說明為什麼拿不到）—— 不畫任何日盤的線
 *   上面那排數字也一起留白 —— 理由相同，數字比線更容易被當成真的
 *   「夜盤報價未取得」那個徽章留著（它本來就是誠實的）
 * ⚠ 這件事只改夜盤那條路徑；**日盤一個字都沒動**，歷史日 K（FUT_N）那條路也沒動。
 * ⚠ 這同時修正了 N11「不該出現沒有數據」的理解：N11 要的是「不要讓人看不懂畫面」，
 *   用「空白 ＋ 講清楚為什麼」就滿足了，不必、也不該拿別的資料頂替。
 *
 * 「為什麼拿不到」這一題（2026-09-23 的調查結論）
 * ------------------------------------------------------------------------------------
 * 期交所那兩支端點在 2026-09-21 00:46 的 Actions 探測裡**全部 200**
 * （`getQuoteList` MarketType=1 回 7 檔、`getChartData1M` TXFJ6-M 回 822 筆，
 *  fixture：docs/fixtures/taifex_night_probe.json）—— 也就是資料源本身是有的。
 * Claude 的容器連不出去（`mis.taifex.com.tw` 與 Worker 網址都被出口代理擋掉，
 * CONNECT 403），所以**這一輪無法實測現況**，只能從程式碼推論：
 * 畫面要出現「夜盤報價未取得」，必須 `/fut` 與 `/futchart` **兩支同時失敗**
 * （任一支成功都會走進 `nightSeries()`）。而同一時間 `/chart?id=FUT`（證交所日盤分時）
 * 是好的 —— 兩者只差在上游是期交所還是證交所。
 * 所以最可能的是**期交所那一側整個連不上**（Worker 沒更新到有 `/futchart` 的版本、
 * 或期交所擋掉 Cloudflare 出口）。確認方法：直接開
 * `https://tw-quote.kcq01010909.workers.dev/fut?session=night`，
 * 或在 Actions 跑一次「端點探測（寫 fixture）」選 taifex_night。
 * ★ 在有人真的打過一次之前，上面這段是推論，不是結論。
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
  const KEY_FSYM = 'tw.m3.futsym';   // 最後一次真的問到的近月合約代號（見 futSymbol()）

  const IDX = [
    // yahoo：有歷史 OHLC 可以抓的才填。櫃買的 ^TWOII 在 Yahoo 已經壞掉
    //（2026-09-15 實測：最後一筆停在 2026-07-17、現價給 269.45 而實際 395），
    // 台指期則沒有免費來源 —— 這兩個只有「當天即時」，選到歷史週期時畫面會說清楚為什麼。
    // ★ 2026-09-26：拿掉 yahoo15（瀏覽器端抓 Yahoo 15 分 K）。多日分 K 三個指數一律讀資料湖
    //   （每天盤後存的證交所分時 1 分 K；加權另有 Yahoo 歷史），見 synthBars 的註解。
    // short：卡片上那一行短句用的簡稱（2026-09-25，Andy 要把長文案縮成一行）
    { id: 'TSE', name: '加權指數', short: '加權', sub: '上市', turnover: true, yahoo: '^TWII', yahoo1m: '^TWII' },
    { id: 'OTC', name: '櫃買指數', short: '櫃買', sub: '上櫃', turnover: true, yahoo: null, yahoo1m: '^TWOII' },
    { id: 'FUT', name: '台指期', short: '台指期', sub: '近月', turnover: false, yahoo: null },
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
    /* ★ 2026-09-24：1 小時／4 小時改成「15 分 K 依台股交易時段合成」（Andy：櫃買與台指期
       「沒有這個週期的免費來源，已改用日」要改成用分 K 合成，拿不到才退回日並標明）。
       以前走 Yahoo 的 60m，只有加權有、而且 4 小時是「四根 1 小時硬併」—— 那會跨午休、跨日
       （例如 12:00～隔天 10:00 被併成一根），不是台股的交易節奏。規則寫在 sessKey() 上。*/
    { id: 'H1', label: '1 小時', synth: 'H1' },
    { id: 'H4', label: '4 小時', synth: 'H4' },
    { id: 'D', label: '日 K', lake: true },
    { id: 'W', label: '週 K', lake: true, roll: 'W' },
    { id: 'M', label: '月 K', lake: true, roll: 'M' },
    { id: 'Q', label: '季 K', lake: true, roll: 'M', group: 3 },
  ];
  const histDef = (id) => HIST.filter(h => h.id === id)[0] || null;
  /** 存進 localStorage 的值可能是舊版的數字，也可能是新的歷史週期代號。 */
  /* ★ 2026-10-04 Andy：「週期只留下 日周月，需確保數據完整」。
     分 K（1／5／15／30 分）與 1 小時／4 小時、季 K 從下拉拿掉 —— 盤後／週末那幾個週期最容易畫出殘缺或錯的東西
     （同一天的週日事故），日／週／月三個都直接吃資料湖日線，三張卡都有 2021 年起的完整歷史。
     合成程式碼留著（走勢圖、別的驗收還在用），只是使用者選不到。存著被拿掉的週期 → 退回日 K。*/
  const TF_SHOWN = ['D', 'W', 'M'];
  function normTf(v) {
    const sv = String(v == null ? 'D' : v);
    return TF_SHOWN.indexOf(sv) >= 0 ? sv : 'D';
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
  /* ★ 2026-09-29（Andy：「即時…至少 5S 更新一次」）：卡片上的數字與走勢線的最右端改成每 5 秒。
     做法**不是**把三個分時檔改成 5 秒抓一次 —— 那樣每 5 秒 3 個請求＋live.js 那一批就 4 個，
     超過 live.js 節流閥的「每 5 秒最多 3 個」；而且 Worker 對分時檔有 10 秒邊緣快取，5 秒去問一半是同一份。
     所以拆成兩條：
       · 分時檔（整條線、每分鐘多一個點）維持 MS_LIVE＝10 秒（＝Worker 的快取時間，問更密沒有新東西）。
       · 加權／櫃買的**當下值**吃 live.js 每 5 秒那一批（登記 t00／o00，**零額外請求**），
         台指期日盤的當下值問期交所報價（/fut?session=day，不是 mis，不佔證交所的額度）——
         原本也是 5 秒，2026-10-03 起改 15 秒（見下面 MS_FUT_DAY）。
       拿到的當下值只准往前蓋（撮合時間比分時檔新才蓋，見 patchLive），不會把數字往回拉。*/
  const MS_FAST = 5 * 1000;
  /* ★ 2026-10-03（Andy 同意，DECISIONS #299）：台指期日盤的當下值改成每 15 秒問一次，不再跟加權／櫃買一起 5 秒。
     原因是額度不是速度：/fut 自 #286 起先打 Deno Deploy，免費層每月 100 萬次請求（deno.com/deploy/pricing 與第三方整理兩個來源一致，見 #299），
     一個讀者整天開著總覽光日盤 fastTick 就要 08:40～13:55 × 每 5 秒 ≈ 3,780 次／天；改 15 秒 ≈ 1,260 次，省三分之二。
     這是過渡做法 —— 正解是「Deno 中央抓一次、用推播（SSE）發給所有讀者」，實測與架構見 DECISIONS #299。
     加權／櫃買的當下值吃 live.js 那一批（零額外請求）照舊每 5 秒；夜盤 60 秒、/futchart 分時節奏都不動。*/
  const MS_FUT_DAY = 15 * 1000;
  const m3On = () => !window.Live || !window.Live.cardOn || window.Live.cardOn('m3');
  /* ★ 2026-10-06 即時僅管理者（DECISIONS #326）：不是管理者 → 這三張圖整個不碰即時來源
     （證交所分時檔、台指期日盤／夜盤、Yahoo 1 分線、推送），只畫資料湖的最近交易日（seedLake）＝盤後版本。
     m3On 經過 live.js 的 cardOn 已經含這個判斷；這支另外擋「mount 那一次／別人呼叫 refresh(true)」那幾條不看 m3On 的路。*/
  const liveOK = () => !!(window.TwLive && window.TwLive.allowed());
  /* ★ 2026-09-29 順手修：`#m3` 寫死在 index.html 的總覽區塊裡，**換到別頁它還在 DOM 裡**（只是 .view 被 display:none）。
     所以以前那句「不在總覽就不用抓」（`!getElementById('m3')`）從來沒成立過 —— 實測在 #market、#flow 也照樣
     每 10 秒打三個分時檔。改成看「畫面上真的看得到」（getClientRects），別頁一律不抓。*/
  const m3Shown = () => { const el = document.getElementById('m3'); return !!el && el.getClientRects().length > 0; };
  /* 夜盤另外一組 60 秒的計時器（2026-09-19）。
     夜盤走勢是「一輪收一個點」收出來的，跟著盤後那 5 分鐘走的話一小時只有 12 個點 ——
     那不叫即時走勢。改成 60 秒，顆粒度就跟日盤的分 K 一致。
     它只打 /fut，不碰那三個分時檔（收盤後它們不會再變，多打是白費）。
     期交所行情看板本身是秒級更新，一分鐘問一次已經很客氣。 */
  const MS_NIGHT = 60 * 1000;

  const state = { data: {}, err: {}, liveQ: {}, liveAt: 0, fTimer: null, fBusy: false, fErr: '', lakeHead: {}, mode: 'line', tf: 'D', big: '', kcharts: {}, busy: false, at: 0,
    hist: {}, histErr: {}, histBusy: {}, timer: null, nTimer: null, tickMs: 0, fails: 0,
    // 呼吸燈：tipKey＝上一次看到的「最後一個點」是誰；tipAt＝它最後一次真的往前走的時刻
    tipKey: {}, tipAt: {}, pulses: {}, pTimer: null,
    // lakeBack[鍵]=true：夜盤日 K（FUT_N）湖裡還沒有，這個週期先用日盤那一份
    lakeBack: {},
    // 夜盤：futSession＝日盤/夜盤；futNight＝最新一筆報價；nightPts＝累積到的真實觀測點
    futSession: 'day', futNight: null, futNightErr: '', nightPts: [], nightDate: '',
    // 期交所 getChartData1M 回來的**真正的分時序列**（2026-09-20 接上）
    futChart: null, futChartErr: '',
    // 台指期最後一次走哪條路（'deno'／'worker'）與 Deno 沒用上的原因（DECISIONS #286；只給除錯與驗收看）
    futVia: '', futDenoWhy: '',
    /* 「這兩份資料各自是什麼時候拿到的」。用途只有一個：`nightSeries()` 要決定
       官方分時的最後一根（＝還沒收的那一分鐘）該不該被更新的報價改寫。
       只有「報價比分時新」才准改 —— 不然會把線往回拉，那比慢一分鐘更糟。*/
    futChartAt: 0, nightQuoteAt: 0,
    /* ---- 夜盤 SSE 推送（Andy 2026-09-23：「夜盤要即時推送」）
       欄位的意義跟 live.js 那一組一模一樣，刻意用同一套命名，
       兩邊出問題時要查的東西才會長得一樣。 */
    fsMode: 'poll',      // 現在真的走哪條路：'sse' 推送／'poll' 輪詢
    fsEs: null,          // EventSource
    fsKey: '',           // 這條連線訂的是哪一段＋哪一支合約（換了就要重開）
    fsFails: 0,          // 連續失敗次數（連上就歸零）
    fsEverOk: false,     // 這次開頁有沒有成功過
    fsGaveUp: false,     // 放棄推送（多半是 Worker 還是舊版，沒有 /futstream）
    fsTimer: null,       // 重連計時器
    fsWatch: null,       // 看門狗（連著卻沒聲音）
    fsAt: 0,             // 最後一次收到推送的時間
    fsPushes: 0,         // 驗收用：總共真的收到幾筆推送
    fsWhy: '',           // 上一次退回輪詢的原因（只給除錯與驗收看）
    lakeDaily: {},     // 資料湖原始日線（用來講「歷史只有幾年」，需求二）
    // noSrc[指數|週期] = true：這張卡片的這個週期沒有免費來源，已自動退回日線（N11）
    noSrc: {},     // （舊）保留欄位；2026-09-24 起 1H／4H 退回日線不再是黏著的旗標，每次畫都重算
    histEst: {} };   // （2026-09-28 起不再估算日線缺量，保留空物件給舊的讀取點）   // hist[TSE+'|'+id] = [[t,o,h,l,c,v]]

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
    /* ★ 2026-09-29：卡片的「即時」關著＝靜態：三組會打端點的計時器都收掉（呼吸燈那組只改 class，留著）。*/
    if (!m3On()) {
      if (state.timer) { clearInterval(state.timer); state.timer = null; state.tickMs = 0; }
      if (state.fTimer) { clearInterval(state.fTimer); state.fTimer = null; }
      syncFutStream();
      return;
    }
    // 登記成「函式」：live.js 每一輪問一次 —— 總覽看得到才要 t00／o00，換到別頁自動不問（零額外請求的前提）
    if (window.Live && window.Live.want) window.Live.want('m3', () => (m3Shown() ? ['t00', 'o00'] : []));
    if (isIntraday()) { if (!state.fTimer) state.fTimer = setInterval(fastTick, MS_FUT_DAY); }
    else if (state.fTimer) { clearInterval(state.fTimer); state.fTimer = null; }
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
    /* 夜盤那組 60 秒的輪詢**一直開著**，推送活著時它就是保底對帳 ——
       「連著但不推」是 SSE 最難查的壞法，看門狗與這組計時器各擋一半。
       （2026-09-23：夜盤這條路一天壞三次，新做法不准比舊做法更容易全白。）*/
    if (!state.nTimer) state.nTimer = setInterval(tickNight, MS_NIGHT);
    // 夜盤推送：時段翻頁／切日夜盤／分頁回前景時，這裡負責把連線開起來或收掉
    syncFutStream();
    /* 呼吸燈要能「自己熄」：資料停了之後沒有任何一輪會再呼叫 draw()，
       所以另外一組輕量的計時器負責重算亮不亮（只改 class 與位置，不重畫圖）。*/
    if (!state.pTimer) state.pTimer = setInterval(pulseTick, PULSE_PAINT);
  }
  /** 夜盤那一輪：只補一筆報價、只在真的是夜盤而且使用者也選在夜盤時才跑。 */
  async function tickNight() {
    /* ★ 這三個早退分支都要先 `syncFutStream()` 再 return：
       它們正好是「該把夜盤那條推送連線收掉」的三種情況
       （分頁切到背景、離開總覽頁、時段翻回日盤）。
       不收的話，離開這一頁之後那條連線會一直開著 —— 使用者看不到，但它還在耗
       Worker 的 CPU 額度，而且 4 分鐘輪替時還會自己重連一次。*/
    if (document.hidden) { syncFutStream(); return; }
    if (!m3Shown()) { syncFutStream(); return; }          // 不在總覽頁（#m3 還在 DOM 裡，要看可見度）
    if (!m3On()) { syncFutStream(); return; }            // 大盤卡「即時」關著＝靜態
    if (state.futSession !== 'night' || futSession() !== 'night') { syncFutStream(); return; }
    // 走到這裡代表時鐘與畫面都在夜盤，不用再同步
    await pullNight();
    draw();
    syncFutStream();
  }

  /** 夜盤要抓的兩樣東西：① 報價快照（未平倉只有這裡有）② 分時序列（走勢與 K 線的主體）。
   *  兩者互不依賴地失敗：序列掛了還有自己收的點，報價掛了序列自己也帶著開高低收。 */
  async function pullNight() {
    try {
      applyFutQuote(await fetchFut('night'));
    } catch (e) { state.futNightErr = String(e.message || e); }
    /* ★ 2026-09-23（夜盤空白的根因）：以前這裡是
         `const sym = futNight.symbol || futChart.symbol; if (!sym) return;`
       —— 那一個 `return` 讓 **`/futchart` 整支綁在 `/fut` 身上**：
       `/fut` 在瀏覽器這邊只要失敗一次（被公司網路擋、代理回 403、逾時），
       就連問都不會去問 `/futchart`，於是 `state.futChart` 永遠是空的，
       `seriesOf()` 兩個條件同時不成立 → 整張卡片留白，錯誤訊息還寫成
       「還沒問到今天的近月合約代號」，把讀者導去查一個根本沒壞的東西。
       檔頭那句「兩者互不依賴地失敗」在這一行之前是**假的**。

       近月合約代號其實不需要跟 `/fut` 要：它每個月只換一次，而且算得出來。
       所以改成三層：① 這一輪真的問到的 ② 記在 localStorage 的上一支
       ③ 從台北日期推算（見 `futSymbol()`）。猜錯的代價只是期交所回空序列，
       跟現在的留白一樣，不會更糟；猜對就是整晚的線都回來了。 */
    const sym = (state.futNight && state.futNight.symbol)
      || (state.futChart && state.futChart.symbol) || futSymbol();
    if (!sym) { state.futChartErr = state.futChartErr || 'NOSYMBOL'; return; }
    try { applyFutChart(await fetchFutChart(sym)); rememberSym(sym); }
    catch (e) { state.futChartErr = String(e.message || e); }
  }

  /* ---- 收下一筆夜盤報價／一份夜盤分時序列 ---------------------------------------
     輪詢（`pullNight()`）與推送（`/futstream` 的 fut／futchart 事件）都走這兩支，
     所以「推送進來的」跟「輪詢抓到的」在 state 裡是同一個形狀、同一套副作用。
     退回輪詢時不會有任何一條沒人走過的路 —— 這是整個推送設計的底線。 */
  function applyFutQuote(q) {
    state.futNight = q;
    state.futNightErr = '';
    state.nightQuoteAt = Date.now();
    pushNight(q);
    if (q && q.symbol) rememberSym(q.symbol);
  }
  function applyFutChart(fc) {
    state.futChart = fc;
    state.futChartErr = '';
    state.futChartAt = Date.now();
  }

  /* ================================================================ 夜盤的 SSE 推送
   *
   * Andy 2026-09-23：「夜盤要即時推送」。
   * 在這之前夜盤是**每 60 秒輪詢一次 `/fut`**（`MS_NIGHT`），
   * 現貨那邊 live.js 早上已經換成一條 SSE 連線，夜盤這張卡還停在輪詢。
   *
   * ★★ 這一段只有一條紅線：**推送是加分，輪詢是底線。**
   * 連不上、斷掉、看門狗逾時、Worker 是舊版 —— 任何一種情況都**立刻**回到
   * 本來就在跑的那條 60 秒輪詢，而且馬上補抓一次，畫面不准出現缺口。
   * 這條紅線不是保守，是**今天才付過學費**：2026-09-23 一天之內夜盤壞了三次
   * （DECISIONS #255），三個根因完全不同，共通點是「這條路很脆弱」。
   * 新做法不准讓它比現在更容易全白，所以：
   *   · 60 秒那組輪詢計時器**一直開著**，推送活著的時候它就是保底對帳
   *     （推送安靜地壞掉 ——「連著但不推」—— 是最難查的一種，看門狗 ＋ 保底輪詢各擋一半）
   *   · 推送收到的東西走的是 `applyFutQuote()` / `applyFutChart()`，
   *     跟輪詢**完全同一支**，所以退回輪詢時不會走到任何沒人驗過的路
   *   · 連續四次從來沒連上過就安靜放棄（多半是 Worker 還沒更新到有 `/futstream` 的版本），
   *     不要一直重試洗 console
   *
   * ★ 為什麼另外開一條 EventSource，而不是共用 live.js 那條
   * 那條訂的是現貨代號、由 live.js 自己管生命週期，而且**夜盤時段現貨本來就該停**。
   * 兩條各自斷線、各自退回，一邊壞掉不會連累另一邊（DECISIONS #255 教訓 2）。
   * 而且這個檔案不准動 live.js。
   */
  const FS_BACKOFF = [1000, 2000, 4000, 8000, 15000, 30000];   // 斷線後隔多久再試
  const FS_GIVEUP = 4;                 // **從來沒連上過**就失敗這麼多次 → 這次開頁不再試
  const FS_WATCHDOG_MS = 90 * 1000;    // 連著卻這麼久沒收到任何東西（含心跳）就當成斷了
  const FS_PUSH_HINT_MS = 10 * 1000;   // 只拿來寫在提示文字裡：Worker 那側問報價的節奏

  /** 這條連線訂的是哪一段＋哪一支合約。合約代號換月就要重開，不然會一直推上個月的。 */
  function fsKeyNow() {
    const sym = (state.futNight && state.futNight.symbol)
      || (state.futChart && state.futChart.symbol) || futSymbol();
    return 'night|' + String(sym || '');
  }

  /** 現在畫面上「應該」要有一條夜盤推送連線嗎（只看時段與畫面，不看退避狀態）。 */
  function fsWanted() {
    if (!m3Shown()) return false;                           // 不在總覽頁（#m3 還在 DOM 裡，要看可見度）
    if (document.hidden) return false;                      // 分頁在背景：不佔連線
    if (!m3On()) return false;                              // 大盤卡「即時」關著
    return state.futSession === 'night' && futSession() === 'night';
  }
  /** 現在可以「開」一條嗎。
   *  ★ `state.fsTimer` 那一條是 2026-09-23 踩到的：`dropFutStream()` 會順手補抓一次
   *  （`tickNight()`），而 `tickNight()` 收尾時又會呼叫 `syncFutStream()` ——
   *  如果這裡不把「正在退避等重連」擋掉，就會變成
   *  斷線 → 重開 → 又斷 → 重開 的**熱迴圈**，退避完全沒有作用，
   *  而且瀏覽器會被打到永遠到不了 networkidle（驗收就是這樣先卡住才發現的）。 */
  /* ★★ 2026-09-24：夜盤推送也預設關閉，理由同 site/live.js 裡那一段（DECISIONS #256）。
     兩條 SSE 共用同一個 Cloudflare Worker，額度也是同一份 —— 只留一條沒有意義。
     開關同一個：localStorage['tw.sse'] === '1'。
     關著的時候走的是 2026-09-23 之前那條輪詢，而且今天修好的兩件事都還在：
     拿不到就真的空白（不冒充日盤）、/futchart 不被 /fut 綁死。 */
  function sseAllowed() {
    try { return localStorage.getItem('tw.sse') === '1'; } catch (e) { return false; }
  }

  function fsCanOpen() {
    if (!sseAllowed()) return false;                        // 預設關閉，見上面那段
    if (typeof EventSource === 'undefined') return false;   // 很舊的瀏覽器：安靜地用輪詢
    if (state.fsGaveUp) return false;
    if (state.fsTimer) return false;                        // 正在退避等重連，不要插隊
    if (!fsWanted()) return false;
    return !!proxy();
  }

  function clearFsWatch() { if (state.fsWatch) { clearTimeout(state.fsWatch); state.fsWatch = null; } }
  /** 看門狗：連著卻沒聲音就當成斷了。
   *  SSE 最難查的壞法是「TCP 還在、資料不來」—— 那時 onerror 永遠不會觸發，
   *  畫面會安靜地停住。Worker 心跳最慢 10 秒一次，90 秒等於連漏九次。 */
  function armFsWatch() {
    clearFsWatch();
    state.fsWatch = setTimeout(() => dropFutStream('太久沒收到推送'), FS_WATCHDOG_MS);
  }

  /** 主動收掉連線（離開夜盤、切到背景、Worker 說 idle）。這不算失敗。 */
  function closeFutStream() {
    clearFsWatch();
    if (state.fsTimer) { clearTimeout(state.fsTimer); state.fsTimer = null; }
    if (state.fsEs) { try { state.fsEs.close(); } catch (e) { /* 已經關了 */ } state.fsEs = null; }
    state.fsKey = '';
    state.fsMode = 'poll';
  }

  /** ★ 連線掉了：**立刻退回輪詢** → 馬上補抓一次 → 排一次重連。
   *  「馬上補抓」這一步就是「畫面不准出現缺口」的實作 —— 不要等下一個 60 秒。 */
  function dropFutStream(why) {
    /* ★ 只有「本來真的在收推送」才需要補抓。
       連都沒連上過的時候（Worker 還是舊版、公司網路擋掉），
       那條 60 秒的輪詢**從頭到尾沒有停過**，根本沒有缺口要補；
       這時候還跟著補一次，只會在每一次重試退避時多敲一次期交所
       （驗收就是這樣抓到的：夜盤點數從 1 變成 5，因為多打了四次 /fut）。*/
    const wasLive = state.fsMode === 'sse';
    clearFsWatch();
    if (state.fsTimer) { clearTimeout(state.fsTimer); state.fsTimer = null; }
    if (state.fsEs) { try { state.fsEs.close(); } catch (e) { /* 已經關了 */ } state.fsEs = null; }
    state.fsMode = 'poll';
    state.fsKey = '';
    state.fsWhy = String(why || '');
    state.fsFails++;
    /* ★ 順序很要緊：**先**把「接下來要怎麼辦」決定好（放棄／排退避），**最後**才補抓。
       `tickNight()` 收尾會呼叫 `syncFutStream()`，如果那時候退避計時器還沒排好，
       它會立刻再開一條 —— 斷線就變成熱迴圈（見 `fsCanOpen()` 的說明）。*/
    if (!state.fsEverOk && state.fsFails >= FS_GIVEUP) {
      /* 從頭到尾沒連上過 → 多半是 Worker 還是舊版（沒有 /futstream）。
         安靜地用輪詢就好，狀態列會寫「輪詢」，滑鼠移上去說得出原因。 */
      state.fsGaveUp = true;
    } else {
      const wait = FS_BACKOFF[Math.min(state.fsFails - 1, FS_BACKOFF.length - 1)];
      state.fsTimer = setTimeout(() => { state.fsTimer = null; openFutStream(); }, wait);
    }
    paintNight();
    // ← 退回輪詢的同時就抓一次（走的就是原本那條路），不等下一個 60 秒
    if (wasLive) tickNight();
  }

  /** 開一條夜盤推送連線。開不起來就當成一次失敗，交給 dropFutStream 處理。 */
  function openFutStream() {
    if (!fsCanOpen()) return;
    const key = fsKeyNow();
    if (state.fsEs && state.fsKey === key) return;     // 同一支合約已經在推了
    if (state.fsEs) { try { state.fsEs.close(); } catch (e) { /* 已經關了 */ } state.fsEs = null; }
    state.fsKey = key;
    const sym = key.split('|')[1];
    let es;
    try {
      es = new EventSource(proxy() + '/futstream?session=night'
        + (sym ? '&symbol=' + encodeURIComponent(sym) : ''));
    } catch (e) { dropFutStream('開不起來：' + e); return; }
    state.fsEs = es;

    const alive = () => {
      state.fsAt = Date.now();
      state.fsEverOk = true;
      state.fsFails = 0;
      state.fsMode = 'sse';
      armFsWatch();
    };
    es.addEventListener('hello', () => { alive(); paintNight(); });
    /* 報價：跟輪詢拿到的是同一份上游 JSON，所以解讀它的是同一支 parseFutQuote()。
       壞掉的一筆不值得把整條連線收掉 —— 記下原因、等下一筆。 */
    es.addEventListener('fut', (ev) => {
      alive();
      try { applyFutQuote(parseFutQuote(JSON.parse(ev.data), 'night')); state.fsPushes++; }
      catch (e) { state.futNightErr = String(e.message || e); }
      paintNight();
    });
    es.addEventListener('futchart', (ev) => {
      alive();
      try {
        const out = parseFutChart(JSON.parse(ev.data));
        if (out.points.length) { applyFutChart(out); state.fsPushes++; }
        else state.futChartErr = 'NOFUTTICKS';
      } catch (e) { state.futChartErr = String(e.message || e); }
      paintNight();
    });
    // 上游某一支這一輪失敗：連線本身還活著，而且另一支通常還是好的（失敗要獨立）
    es.addEventListener('warn', () => { alive(); });
    // 非夜盤時段：Worker 一個上游請求都不打就收線。這不是失敗，安靜地回到輪詢。
    es.addEventListener('idle', () => { closeFutStream(); state.fsFails = 0; paintNight(); });
    // 4 分鐘輪替（Worker 為了不撞免費方案的 CPU 上限）。正常結束 → 不退避、直接重連，
    // 重連的第一筆一定是完整快照，所以中間那 120ms 不會漏值。
    es.addEventListener('bye', () => {
      clearFsWatch();
      if (state.fsEs) { try { state.fsEs.close(); } catch (e) { /* 已經關了 */ } state.fsEs = null; }
      state.fsFails = 0; state.fsKey = '';
      setTimeout(() => openFutStream(), 120);
    });
    /* EventSource 自己也會重連，但它分不出「404（Worker 是舊版）」跟「網路抖一下」，
       而且重連期間畫面是停的。所以一律由我們接手：先退回輪詢再自己排重連。 */
    es.onerror = () => { state.fsKey = ''; dropFutStream('連線錯誤'); };
  }

  /** 時段翻頁／切日盤夜盤／分頁切回前景時，把連線的狀態跟畫面對齊。 */
  function syncFutStream() {
    // 離開夜盤（時段翻頁、切回日盤、換頁、分頁切到背景）：連線與還沒到期的重連一起收掉，
    // 不然切回日盤之後還會有一條在背景重連。
    if (!fsWanted()) { if (state.fsEs || state.fsTimer) closeFutStream(); return; }
    if (!fsCanOpen()) return;                         // 已經放棄、或正在退避等重連
    if (!state.fsEs) { openFutStream(); return; }
    if (fsKeyNow() !== state.fsKey) { state.fsKey = ''; openFutStream(); }
  }

  /** 收到一筆推送之後**只動台指期那張卡**：那排數字換掉、走勢圖只補最後一根。
   *  不重畫另外兩張圖、不重建整個 option —— 不然十秒閃一次，比不推還糟。 */
  /* ★ 2026-10-04 修：「日盤／夜盤」小標（#futSess）抽成一支，draw() 與只補台指期那張卡的 paintNight() 都呼叫。
     改前只有 draw() 會更新它；夜盤資料若是由 paintNight()（推送／輪詢只動台指期那張卡）第一次補進來，
     圖與數字列已經是夜盤、小標卻還停在先前畫的「日盤」—— 標籤沒跟著畫的那一份走，正是 #258 第 1 條不准的事
     （夜盤真實 fixture 在 America/New_York 時區量到：線是夜盤收盤價、合約 TXFJ6-M，小標寫「日盤」）。*/
  function syncFutSess() {
    const ss = document.getElementById('futSess');
    /* ★ 2026-09-30（Andy 23:26：「為何沒有顯示夜盤」，DECISIONS #280）：夜盤時段卻顯示日盤時，
       小標的說明要講出**夜盤那兩支為什麼沒拿到**（例如「代理回 HTTP 520」）。
       那一晚前端每一條路都有去抓，是 Worker 打期交所回 520 —— 但畫面只寫「還沒拿到夜盤資料」，
       讀者只能來問，我們也只能從頭查一輪。DECISIONS #255 教訓 3：錯誤訊息要指到真正的斷點。
       `data-why` 給驗收讀；nightWhy() 回的是 HTML（帶 <code>），title 只能放純文字。*/
    if (ss) { const n = nightHas(); ss.textContent = n ? '夜盤' : '日盤'; ss.dataset.s = n ? 'night' : 'day';
      const why = (!n && state.futSession === 'night' && (state.futNightErr || state.futChartErr))
        ? nightWhy().replace(/<[^>]+>/g, '') : '';
      ss.dataset.why = why;
      ss.title = n ? '夜盤（15:00～翌日 05:00）有資料，顯示夜盤' : (state.futSession === 'night'
        ? '夜盤時段，但還沒拿到夜盤資料 —— 先顯示日盤' + (why ? '\n原因：' + why : '') : '日盤時段（08:45～13:45）'); }
  }
  function paintNight() {
    const grid = document.getElementById('m3Grid');
    if (!grid) return;
    const x = IDX.filter(v => v.id === 'FUT')[0];
    if (!x || !isNight(x)) return;
    const card = grid.querySelector('.m3-card[data-id="FUT"]');
    if (!card) return;
    const head = card.querySelector('.m3-nums');
    if (head) head.outerHTML = cardHead(x);
    const el = document.getElementById('m3c-' + x.id);
    const d = seriesOf(x);
    /* 走勢圖：能只補最後一根就只補（`patchLine`）。補不了的情況
       （剛從空狀態長出來、切到 K 線、日夜換邊）才整張畫一次；
       K 線那邊 `drawK()` 本來就會沿用同一個實例，縮放不會被彈回去。*/
    if (!(state.mode === 'line' && d && d.night && el && patchLine(x, d, el))) drawOne(x);
    syncFutSess();
    paintPulses();
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
    // 驗收用：`Market3.forceClock('night'|'day')` 可以把時鐘釘在某一段（null＝跟著台北時間）。
    // 只有驗收會呼叫；使用者沒有任何入口能碰到它（2026-09-24 切換鈕拿掉之後，時鐘是唯一的依據）。
    if (state.clock === 'day' || state.clock === 'night') return state.clock;
    const mm = nightMin(taipeiNow());
    return (mm >= SESSION_NIGHT[0] && mm <= SESSION_NIGHT[1]) ? 'night' : 'day';
  }

  /* ---- 近月合約代號：不必跟 `/fut` 要 -----------------------------------------
     `pullNight()` 以前只從報價清單拿代號，所以 `/fut` 一掛整條夜盤就斷（見那裡的說明）。
     代號的規則是公開的，算得出來：
       `TXF` ＋ 月碼 ＋ 西元年個位數 ＋ `-M`（夜盤；日盤是 `-F`）
     月碼是台期所自己那一套 **A~L ＝ 1~12 月**（不是 CME 的 F,G,H…，那是選擇權用的）。
     對照 fixture（docs/fixtures/taifex_night_probe.json，2026-09-23 夜盤實測）：
       TXFJ6-M ＝ 臺指期 **10** 月（J 是第 10 個字母）、TXFK6-M ＝ 11 月、TXFL6-M ＝ 12 月。★ 對得上。

     ⚠ 為什麼 9 月 23 日的近月是「10 月」：台指期在**每月第三個星期三**結算，
     2026-09 的第三個星期三是 09-16，早就過了，所以近月已經滾到 10 月。
     夜盤是「結算日當天晚上就算新的那一個月」，所以判斷用 `>=`。

     ⚠ 這是**推算值**，不是期交所講的。猜錯的代價只是期交所回空序列
     （畫面照樣留白，跟現在一樣），所以順序一律是「真的問到的 → 記住的 → 推算的」。*/
  function rememberSym(sym) {
    if (!/^[A-Za-z0-9]{3,8}-[FM]$/.test(String(sym || ''))) return;
    ls.set(KEY_FSYM, String(sym).toUpperCase());
  }
  /** 這個月第三個星期三是幾號（台指期結算日）。 */
  function thirdWed(y, m0) {
    const first = new Date(Date.UTC(y, m0, 1)).getUTCDay();   // 0=日
    return 1 + ((3 - first + 7) % 7) + 14;                    // 第一個星期三再加兩週
  }
  /** 夜盤近月合約代號。先用記住的，沒有才推算。 */
  function futSymbol() {
    const kept = (ls.get(KEY_FSYM, '') || '').toUpperCase();
    if (/^[A-Z0-9]{3,8}-M$/.test(kept)) return kept;
    const d = taipeiNow();
    /* 夜盤凌晨那幾個小時屬於「前一天晚上」開始的那一盤，所以先把日期退回去，
       月底跨月時才不會一口氣多滾一個月。*/
    const t = new Date(d.getTime() - (d.getHours() < 6 ? 12 * 3600 * 1000 : 0));
    let y = t.getFullYear(), m0 = t.getMonth();
    if (t.getDate() >= thirdWed(y, m0)) { m0 += 1; if (m0 > 11) { m0 = 0; y += 1; } }
    return 'TXF' + 'ABCDEFGHIJKL'.charAt(m0) + String(y % 10) + '-M';
  }
  /** 現在該「抓」哪一段：只看台北時鐘。
   *  ★ 2026-09-24（Andy：「台指期的『日盤／夜盤』切換拿掉、合併成一張 —— 自動顯示目前有資料的那一段」）：
   *  以前這裡還會讀 localStorage 的手動選擇（`tw.m3.fut`，{sess, base}）。切換鈕拿掉之後
   *  使用者沒有任何方式改它，留著只會讓舊版存下的值把畫面卡在錯的那一段，所以一律不讀。
   *  「抓哪一段」與「顯示哪一段」是兩件事：抓由時鐘決定（夜盤時段才去問期交所），
   *  顯示由 `nightHas()` 決定（真的拿到夜盤資料才顯示夜盤，否則顯示日盤）。 */
  function pickSession() {
    return futSession();
  }
  /** 夜盤這一輪真的有資料嗎（有一筆落在夜盤時段的報價，或期交所的分時序列有點）。
   *  這就是「自動切」的判準：沒有 → 卡片整張顯示日盤（並在標題旁寫「日盤」）；有 → 顯示夜盤。
   *  ⚠ DECISIONS #255 ① 反對的是「標著夜盤、畫著日盤」。現在標籤永遠跟著畫的那一份走，
   *    顯示日盤時就寫「日盤」，所以不再是冒充 —— 這是 Andy 這次明講的新規則。 */
  function nightHas() {
    if (state.futSession !== 'night') return false;
    if (state.futNight && state.futNight.inSession) return true;
    return !!(state.futChart && state.futChart.points && state.futChart.points.length);
  }
  /** 時段翻頁時把畫面帶回當下該看的那一段。回傳「有沒有真的換」。 */
  function syncSession() {
    const want = pickSession();
    if (want === state.futSession) return false;
    state.futSession = want;
    return true;
  }
  /* ---- 台指期的兩支（/fut、/futchart）先打 Deno 代理，失敗才退回 Worker（DECISIONS #286）----
     為什麼：期交所在 Cloudflare 後面，拒絕所有經 Cloudflare Worker 來的請求（上游 520，#281），
     Worker 那條路日盤夜盤一起壞；Deno Deploy 不走 Cloudflare 出口，2026-10-02 兩輪實測
     （10:25 日盤、18:28 夜盤交易中）/fut 日夜盤、/futchart 日夜盤四支全 200。
     兩邊回的是**同一份期交所原始 JSON**（main.ts 原文照轉），所以下游解析一個字都不用改。
     退回 Worker 留著當保險：哪天 Deno 掛了、額度用完或被公司網路擋，至少還有第二條路可以試
     （雖然 2026-10-02 當下那條也是壞的）。
     ⚠ 只有台指期這兩支走這裡；加權、櫃買（以及台指期日盤分時）的 /chart 走 mis.twse，照舊只走 Worker。
     ⚠ 夜盤推送（/futstream，預設關閉）Deno 沒有做，仍然只走 Worker；輪詢那條 60 秒的才是底線。 */
  const FUT_DENO_TIMEOUT_MS = 6000;   // Deno 6 秒沒回就換 Worker：寧可快速換路，不讓讀者等到瀏覽器逾時（#256）
  function taifexProxy() {
    return (window.Live && window.Live.taifexProxy) ? String(window.Live.taifexProxy() || '') : '';
  }
  /** 打一次台指期端點。回 `{ r, deno }`：
   *    r    ＝ 拿來解析的那個 Response（成功的那一個，或最後一條路的失敗回應）
   *    deno ＝ Deno 那一趟為什麼沒用上（成功或沒試就是空字串）；兩條路都壞時要一起講出來，
   *           不然畫面只寫得出 Worker 的 502，讀者會以為新的那條路根本沒去試。
   *  兩條路都連不上（例外）就丟一個把兩個原因串起來的錯誤。 */
  async function futGet(path) {
    const deno = taifexProxy();
    const base = proxy();
    let why = '';
    if (deno) {
      try {
        const opt = { cache: 'no-store' };
        if (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) opt.signal = AbortSignal.timeout(FUT_DENO_TIMEOUT_MS);
        const r = await fetch(deno + path, opt);
        if (r.ok) { state.futVia = 'deno'; state.futDenoWhy = ''; return { r, deno: '' }; }
        why = 'Deno 回 HTTP ' + r.status;
        // 沒有 Worker 可以退：直接把 Deno 的回應交給呼叫端照原本的規則解讀
        if (!base) { state.futVia = 'deno'; state.futDenoWhy = why; return { r, deno: '' }; }
      } catch (e) {
        why = 'Deno 連不上（' + ((e && e.name) || e) + '）';
        if (!base) { state.futVia = 'deno'; state.futDenoWhy = why; throw new Error(why); }
      }
    }
    if (!base) throw new Error('還沒設定即時來源');
    state.futVia = 'worker';
    state.futDenoWhy = why;
    try {
      return { r: await fetch(base + path, { cache: 'no-store' }), deno: why };
    } catch (e) {
      if (!why) throw e;
      throw new Error(why + '，Worker 連不上（' + ((e && e.message) || e) + '）');
    }
  }
  /** 兩條路都沒拿到時的說明。只走 Worker 時維持原本的「代理回 HTTP 502」字樣（既有驗收與 nightWhy 都認它）。*/
  function futFailText(g) {
    return g.deno ? `${g.deno}，Worker 也回 HTTP ${g.r.status}` : '代理回 HTTP ' + g.r.status;
  }
  async function fetchFut(session) {
    const g = await futGet(`/fut?session=${session}&t=${Date.now()}`);
    const r = g.r;
    // 404／400＝Worker 還是舊版（沒有 /fut）。Deno 先失敗過的話這個判讀不成立，改講兩條路各回了什麼
    if (!g.deno && (r.status === 404 || r.status === 400)) throw new Error('NOFUT');
    if (!r.ok) throw new Error(futFailText(g));
    return parseFutQuote(await r.json(), session);
  }

  /** 期交所報價清單的原始 JSON → 這一頁要用的那一筆（近月）。
   *
   *  ★ 為什麼要獨立成一支（2026-09-23 夜盤推送）：
   *  推送（`/futstream` 的 `fut` 事件）與輪詢（`/fut`）拿到的是**同一份**上游 JSON，
   *  所以解讀它的程式碼也必須是同一份。兩邊各寫一次，就等於「退回輪詢」時
   *  走的是一條沒人驗過的路 —— 那退路等於沒有。 */
  function parseFutQuote(j, session) {
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
         那筆不能當成夜盤報價顯示，所以先標起來；畫面上該段就留白並講出原因
         （2026-09-23 之前是退回日盤數字，已經改掉 —— 見檔頭與 drawOne）。*/
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
    if (!/^[A-Za-z0-9]{3,8}-[FM]$/.test(String(symbol || ''))) throw new Error('NOSYMBOL');
    const g = await futGet(`/futchart?symbol=${encodeURIComponent(symbol)}&t=${Date.now()}`);
    const r = g.r;
    // 404＝Worker 還是舊版（沒有 /futchart），要 Andy 去 Cloudflare 重貼一次（Deno 先失敗過就不是這個原因）
    if (!g.deno && r.status === 404) throw new Error('NOFUTCHART');
    if (!r.ok) throw new Error(futFailText(g));
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
    /* ★ 2026-09-23：**只有真的落在夜盤時段的那一筆報價**才准拿來填數字。
       夜盤時段外打 MarketType=1，期交所回的是日盤最後一筆（`inSession` 就是為此標的）。
       以前這裡直接 `const q = state.futNight`，於是只要 `/futchart` 拿得到序列，
       上排的開高低收與成交價就會被那筆**日盤**報價填滿，而標籤寫著「夜盤」——
       那正是 Andy 2026-09-23 明講不要的「拿日盤冒充夜盤」。
       更糟的是它還會連帶把圖弄空：下面那個「代號要對得上」的判斷會拿日盤合約
       （`-F`）去比夜盤序列（`-M`），比不過就整條序列丟掉，變成「有數字、沒有線」。
       濾掉之後這兩件事一起解決：數字改由序列自己帶的 Quote 提供，序列也留得住。*/
    const q = (state.futNight && state.futNight.inSession) ? state.futNight : null;
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
      pts = fc.points.slice();
      /* ★ 2026-09-23（夜盤推送）：官方分時是 60 秒問一次，報價是 10 秒推一次。
         官方序列的**最後一根就是「還沒收的那一分鐘」**（fixture 證實：相隔 6 秒的兩次探測，
         "001600" 那一根的收盤從 48009 被就地改寫成 48013）。
         所以報價比它新的時候，就用新的成交價把那一根的收盤改掉、高低跟著撐開 ——
         這正是個股 K 線 `KChart.applyQuote()` 在做的事（那支不歸這一輪改，做法照抄）。
         沒有這一段，畫面會變成「上面的數字每 10 秒在跳，線卻要等滿一分鐘才動」。

         ⚠ 只有「報價真的比較新」才准改（比的是兩份資料各自**拿到手的時間**）。
         反過來拿舊報價去蓋新分時，會讓線往回跳 —— 那比慢一分鐘更糟。
         成交量一律留官方那一份：我們手上的是「累計量的差」，會跟官方的分鐘量重複計算。*/
      const cur = mine.filter(p => p.min === lastMin).pop();
      if (cur && cur.c != null && state.nightQuoteAt > state.futChartAt) {
        const b = pts[pts.length - 1];
        pts[pts.length - 1] = {
          ms: b.ms, min: b.min, o: b.o, s: b.s, c: cur.c,
          h: b.h != null ? Math.max(b.h, cur.c) : cur.c,
          l: b.l != null ? Math.min(b.l, cur.c) : cur.c,
        };
      }
      pts = pts.concat(mine.filter(p => p.min > lastMin));
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
  const isNight = (x) => x.id === 'FUT' && nightHas();

  async function fetchOne(id) {
    const base = proxy();
    if (!base) throw new Error('還沒設定即時來源');
    // 分時檔跟 /quote 同一台主機（mis.twse），一起排 live.js 的節流閥（每 5 秒最多 3 個請求）
    if (window.Live && window.Live.slot) await window.Live.slot(1);
    // 排隊等節流閥的期間使用者把「即時」關了 → 這一個就不打（關掉之後不准再有請求）
    if (!state.runManual && !m3On()) throw new Error('OFF');
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

  /** 台北日期 YYYYMMDD（毫秒時間戳 → 台北牆鐘）。 */
  const tpeYmd = (ms) => new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, '');
  /** 日盤分時清洗（2026-10-04 週日事故）：只留「最後那一天」、落在交易時段內、價格在當天高低區間內的點。
   *  證交所分時本身是權威來源，不做價格過濾；備援來源（Yahoo、本機暫存）才拿 live.js 那筆 t00／o00 報價的
   *  當天高低（同一天才用）去擋亂值。
   *  Yahoo 自己的 high／low 是拿這些點算出來的，不能拿來驗自己，所以清完一律重算。 */
  function tidyDay(x, d) {
    if (!d || !d.points || !d.points.length || !SESSION[x.id]) return d;
    const [s0, s1] = SESSION[x.id];
    const days = d.points.map(p => tpeYmd(p.ms));
    const day = String(d.date || '').length === 8 && days.includes(String(d.date)) ? String(d.date) : days.reduce((a, b) => (b > a ? b : a));
    let hi = null, lo = null;
    const code = { TSE: 't00', OTC: 'o00' }[x.id];
    const r = d.src && code && window.Live && window.Live.raw ? window.Live.raw(code, 864e5) : null;
    if (r && r.m && String(r.m.d) === day) { hi = num(r.m.h); lo = num(r.m.l); }
    const pad = (hi != null && lo != null) ? Math.max(hi * 0.002, 1e-9) : 0;
    const pts = d.points.filter((p, i) => days[i] === day && p.min >= s0 && p.min <= s1 &&
      (hi == null || lo == null || (p.c <= hi + pad && p.c >= lo - pad)));
    const out = Object.assign({}, d, { points: pts, date: day });
    if (d.src && pts.length) {
      const cs = pts.map(p => p.c); const L = pts[pts.length - 1];
      out.open = cs[0]; out.high = Math.max.apply(null, cs); out.low = Math.min.apply(null, cs);
      if (out.last == null || d.src === 'Yahoo') out.last = L.c;
      out.time = new Date(L.ms + 8 * 3600 * 1000).toISOString().slice(11, 19);
    }
    return out;
  }
  /** 一份分時算不算「完整的一天」：涵蓋到收盤前 15 分鐘內、點數至少六成時段。盤後只收這種。 */
  function fullDay(x, d) {
    const [s0, s1] = SESSION[x.id] || [0, 0];
    const p = d.points;
    return p.length >= (s1 - s0) * 0.6 && p[0].min <= s0 + 30 && p[p.length - 1].min >= s1 - 15;
  }
  /** 資料湖最近一個交易日的 15 分 K → 走勢圖的點（每 15 分一點，標在該格收盤那一分鐘）。 */
  function lakeDay(x) {
    const b = (((state.lakeIntra || {})[x.id] || {}).M15 || []);
    if (!b.length) return null;
    const dayOf = (t) => Math.floor(t / 86400);
    // 最近「完整」的那一天（至少 12 根 15 分 K，約 3 小時）—— 盤後管線偶爾只存到當天頭一兩根，那種不算一天
    const cnt = new Map(); b.forEach(r => cnt.set(dayOf(r[0]), (cnt.get(dayOf(r[0])) || 0) + 1));
    const full = [...cnt.entries()].filter(([, n]) => n >= 12).map(([k]) => k);
    if (!full.length) return null;
    const last = Math.max.apply(null, full);
    const rows = b.filter(r => dayOf(r[0]) === last);
    const [s0, s1] = SESSION[x.id];
    const pts = rows.map(r => { const m = Math.min(s1, Math.floor((r[0] % 86400) / 60) + 15);
      return { ms: (r[0] - 8 * 3600 + (m - Math.floor((r[0] % 86400) / 60)) * 60) * 1000, min: m, c: r[4], s: 0 }; })
      .filter(p => p.min >= s0 && p.min <= s1);
    if (!pts.length) return null;
    const cs = pts.map(p => p.c);
    return { id: x.id, name: x.name, src: '資料湖 15 分', date: tpeYmd(pts[0].ms), time: '收盤',
      prev: null, open: rows[0][1], high: Math.max.apply(null, rows.map(r => r[2])), low: Math.min.apply(null, rows.map(r => r[3])),
      last: cs[cs.length - 1], vol: null, amt: null, points: pts, sparse: true };
  }

  /** 備援：Yahoo 1 分鐘線 → 跟 parse() 一樣的形狀。 */
  async function fetchYahoo1m(x) {
    const base = proxy(); if (!base) return null;
    const r = await fetch(`${base}/y?symbol=${encodeURIComponent(x.yahoo1m)}&interval=1m&range=1d`, { cache: 'no-store' });
    if (!r.ok) return null;
    const j = await r.json();
    const res = ((j.chart || {}).result || [])[0];
    if (!res || !res.timestamp) return null;
    const q = ((res.indicators || {}).quote || [])[0] || {}, m = res.meta || {};
    const pts = [];
    res.timestamp.forEach((t, i) => {
      const c = num(q.close && q.close[i]); if (c === null) return;
      const d = new Date(t * 1000 + 8 * 3600 * 1000);
      pts.push({ ms: t * 1000, min: d.getUTCHours() * 60 + d.getUTCMinutes(), c, s: num(q.volume && q.volume[i]) || 0 });
    });
    if (!pts.length) return null;
    const cs = pts.map(p => p.c), last = pts[pts.length - 1];
    const dd = new Date(last.ms + 8 * 3600 * 1000);
    return {
      id: x.id, name: x.name, src: 'Yahoo',
      date: dd.toISOString().slice(0, 10).replace(/-/g, ''),
      time: dd.toISOString().slice(11, 19),
      prev: num(m.chartPreviousClose) ?? num(m.previousClose),
      open: cs[0], high: Math.max.apply(null, cs), low: Math.min.apply(null, cs),
      last: num(m.regularMarketPrice) ?? last.c, vol: null, amt: null, points: pts,
    };
  }
  /** 這台瀏覽器存的「當天最後一份分時」—— 只給同一天用，隔天就作廢。 */
  function tpeDay() { try { return new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Taipei' }).replace(/-/g, ''); } catch (e) { return ''; } }
  function cachePut(id, d) { try { localStorage.setItem('m3.last.' + id, JSON.stringify({ day: tpeDay(), d })); } catch (e) {} }
  function cacheGet(id) {
    try { const o = JSON.parse(localStorage.getItem('m3.last.' + id) || 'null'); return (o && o.day === tpeDay()) ? o.d : null; }
    catch (e) { return null; }
  }

  async function refresh(manual) {
    if (!liveOK()) return;                               // 不是管理者：不抓任何即時來源（DECISIONS #326；畫面由 seedLake 的資料湖種子撐著）
    if (state.busy) return;
    if (!document.getElementById('m3')) return;          // 版面上根本沒有這一塊
    // 分頁切走就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    // 不在總覽（#m3 看不到）就不用抓；manual（mount 那一次、輪動時鐘要總成交值時）照抓
    if (!manual && !m3Shown()) return;
    if (!manual && !m3On()) return;                      // 大盤卡「即時」關著＝靜態（mount 那一次 manual 照抓，給一份快照）
    state.runManual = !!manual;
    /* ★ 每一輪都重新評估要看哪一段 —— 網頁可能整天開著，跨過 13:45（日盤收）
       或 15:00（夜盤開）時要自己翻過去，不能等使用者重新整理。*/
    syncSession();
    state.busy = true;
    if (state.seedP) { try { await state.seedP; } catch (e) {} }
    const jobs = IDX.map(async x => {
      let d = null, err = '';
      try { d = tidyDay(x, await fetchOne(x.id)); } catch (e) { err = String(e.message || e); }
      if (err === 'OFF') return;                       // 卡片剛被關掉：這一輪什麼都不動（不去打 Yahoo 備援）
      /* ★ 2026-10-04（週日）Andy 截圖：加權走勢只剩 13:15～13:30 一小段、從 46,000 暴衝到 51,000，
         5 分 K 冒出 14:01～15:00 的棒。根因：週末證交所分時回空 → 退到 Yahoo 1 分線，
         Yahoo 在非交易日給的是「收盤前後一小段 ＋ 盤後亂值」，以前**照單全收**。
         現在兩道關：① tidyDay 只留同一天 09:00～13:30 內、落在當天高低區間的點；
         ② 不在盤中時，備援來源（Yahoo、本機暫存）要涵蓋大半個交易時段（fullDay）才算數 —— 盤後要畫的是
         「最近交易日完整的一天」，殘缺的一小段寧可換下一個來源。盤中照舊有多少畫多少。*/
      const want = (v) => v && v.points.length && (isIntraday() || fullDay(x, v));
      // 證交所分時是權威來源：有點就用（颱風假半天盤也是真資料），完整度檢查只套在備援來源上
      let best = null;
      /* ★ 2026-09-24 Andy：「日盤不能重新整理找不到數據就空白，麻煩補上該有數據」。
         證交所分時在收盤後常回空、櫃買那支會回 502 —— 以前就直接留白。
         現在依序退：① Yahoo 1 分鐘線（加權 ^TWII、櫃買 ^TWOII）② 這台瀏覽器存下的當天最後一份。
         退到備援時卡片上會標來源，不假裝是證交所即時。*/
      if ((!d || !d.points.length) && x.yahoo1m) {
        try {
          const y = tidyDay(x, await fetchYahoo1m(x));
          if (y && y.points.length) {
            if (want(y)) { d = y; err = ''; }
            else if (!best || y.points.length > best.points.length) best = y;
          }
        } catch (e) {}
      }
      if (!d || !d.points.length) {
        const c = tidyDay(x, cacheGet(x.id));
        if (want(c)) { d = Object.assign(c, { src: '本機暫存' }); err = ''; }
      } else if (!d.src) cachePut(x.id, d);
      // 盤後三個來源都不完整 → 退資料湖最近一個完整交易日的 15 分 K（整天 09:00～13:30 都有）；湖也沒有才用最完整的殘段
      /* 只在「有來源回了殘段」時才退湖（best 存在）；Worker 根本連不到時維持原本的退日 K（那條路有自己的說明字）。*/
      const seeded = !isIntraday() && state.data[x.id] && state.data[x.id].seed && state.data[x.id].points.length >= 20;
      if ((!d || !d.points.length) && !isIntraday() && best && !seeded) {
        if (state.lakeIntra === undefined) await loadLakeIntra();
        const L = lakeDay(x);
        if (L) {
          // 昨收：資料湖日線裡「那一天之前」最後一根的收盤（沒有昨收就畫不出昨收虛線與對稱的價格軸）
          try {
            const all = await window.App.load('index_ohlc', { fallback: {} });
            const ymd = L.date.slice(0, 4) + '-' + L.date.slice(4, 6) + '-' + L.date.slice(6);
            const pb = ((all && all[x.id]) || []).filter(b => String(b[0]) < ymd);
            if (pb.length) L.prev = pb[pb.length - 1][4];
          } catch (e) {}
          d = L; err = '';
        }
        else { d = best; err = ''; }
      }
      // ③ 都沒有分時 → 至少把資料湖最後一根日線的收盤放上標題列，不讓數字是「—」
      /* ★ 2026-09-24（審查 R1）：以前這裡寫 `x.id !== 'FUT'` 把台指期排除，但 index_ohlc 裡明明有 FUT，
         於是 Worker 一掛台指期的大數字就只剩「—」。三張一律退到資料湖最後一根日線。*/
      if ((!d || !d.points.length) && !seeded) {
        try {
          const all = await window.App.load('index_ohlc', { fallback: {} });
          const b = (all && all[x.id]) || [];
          if (b.length) {
            const L = b[b.length - 1], P = b.length > 1 ? b[b.length - 2] : null;
            state.lakeHead[x.id] = { id: x.id, src: '資料湖日線', date: String(L[0]).replace(/-/g, ''), time: '收盤',
              open: L[1], high: L[2], low: L[3], last: L[4], prev: P ? P[4] : null, amt: null, vol: null, points: [] };
          }
        } catch (e) {}
      }
      if (d && d.points.length) {
        state.data[x.id] = d; state.err[x.id] = '';
        snapPut(x, d);
        // 分時檔可能比剛剛 5 秒那一輪的當下值舊（Worker 10 秒快取）—— 把較新的當下值蓋回去，數字不往回跳
        if (state.liveQ[x.id]) patchLive(x.id, state.liveQ[x.id]);
      }
      else { if (!state.data[x.id] || !state.data[x.id].points.length) state.data[x.id] = d; state.err[x.id] = err; }
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
    if (manual) draw(); else drawLive();        // 計時器那一輪走輕量版（見 drawLive）；手動／掛載那一次照舊整張畫
    m3Stamp();
  }

  /* ---- 2026-09-29：每 5 秒的當下值（見 MS_FAST 的註解）---------------------------------- */
  const hmsNum = (t) => { const v = parseInt(String(t || '').replace(/:/g, ''), 10); return isFinite(v) ? v : null; };
  /** 把一筆當下值蓋進某張卡的資料：只准往前（同一天、撮合時間不比現有的舊），同時推動走勢線的最右端。 */
  function patchLive(id, q) {
    const d = state.data[id];
    if (!d || !d.points || !d.points.length || q == null || q.last == null) return false;
    if (q.date && d.date && String(q.date) !== String(d.date)) return false;     // 不同天不混
    const tNew = hmsNum(q.time), tOld = hmsNum(d.time);
    if (tNew == null || (tOld != null && tNew < tOld)) return false;             // 不准往回
    const changed = d.last !== q.last || tNew !== tOld;
    d.last = q.last;
    if (q.high != null) d.high = d.high == null ? q.high : Math.max(d.high, q.high);
    if (q.low != null) d.low = d.low == null ? q.low : Math.min(d.low, q.low);
    d.time = String(tNew).padStart(6, '0');
    /* 走勢線：分時檔的點「090100」代表 09:00～09:01 那一分鐘的收盤，所以 10:30:15 這一筆屬於 10:31 那個點。
       同一分鐘就改它的收盤；新的一分鐘先補一個暫時點（量記 0），下一次分時檔回來整條換掉。*/
    const hh = Math.floor(tNew / 10000), mm = Math.floor(tNew / 100) % 100, ss = tNew % 100;
    const min = hh * 60 + mm + (ss > 0 ? 1 : 0);
    const lp = d.points[d.points.length - 1];
    /* ★ 2026-10-04：收盤後／週末 live.js 照樣每 5 秒丟 t00／o00 回來（時間會走到 13:3x、14:xx），
       以前只要「比最後一點新、差 5 分鐘內」就往後補點，於是線一路長到 13:30 之後。
       現在超出交易時段、或根本不在盤中，就只更新數字，不碰走勢線。*/
    const ses = SESSION[id];
    if (!isIntraday() || (ses && (min < ses[0] || min > ses[1]))) { state.liveQ[id] = q; return changed; }
    if (min === lp.min) lp.c = q.last;
    else if (min > lp.min && min - lp.min <= 5) d.points.push({ ms: lp.ms + (min - lp.min) * 60000, min, c: q.last, s: 0, live: true });
    state.liveQ[id] = q;
    return changed;
  }
  /** live.js 那一批（每 5 秒）一回來：加權 t00、櫃買 o00 的當下值蓋進去。零額外請求。*/
  function patchFromLive() {
    if (!m3Shown() || !m3On() || !window.Live || !window.Live.raw) return false;
    const moved = [];                                // 這一輪真的有變的那幾張（drawLive 只補它們）
    [['TSE', 't00'], ['OTC', 'o00']].forEach(([id, code]) => {
      const r = window.Live.raw(code, 6000); if (!r) return;
      const m = r.m, z = num(m.z);
      if (z === null) return;                        // 指數兩次撮合之間 z 可能是 '-'，不拿買價那套去猜
      if (patchLive(id, { last: z, high: num(m.h), low: num(m.l), time: m.t, date: m.d })) moved.push(id);
    });
    if (moved.length) { state.liveAt = Date.now(); drawLive(moved); m3Stamp(); }
    return moved.length > 0;
  }
  /** 台指期日盤的當下值：每 15 秒問一次期交所報價（MS_FUT_DAY；夜盤另有自己那條路，不在這裡）。*/
  async function fastTick() {
    if (document.hidden || !m3Shown() || !m3On() || !isIntraday()) return;
    if (state.fBusy || nightHas()) return;
    const L = window.Live;
    if (L && L.cooling && L.cooling('m3fut')) return;     // 期交所報價上一輪失敗 → 退避中（10、20、40…秒）
    state.fBusy = true;
    const t0 = Date.now();
    try {
      const q = await fetchFut('day');
      const t = String(q.time || '').replace(/:/g, '');
      if (patchLive('FUT', { last: q.last, high: q.high, low: q.low, time: t, date: q.date })) { state.liveAt = Date.now(); drawLive(['FUT']); }
      state.fErr = '';
      if (L && L.report) L.report('m3fut', true);
    } catch (e) { state.fErr = String(e.message || e); if (L && L.report) L.report('m3fut', false, t0); }
    state.fBusy = false;
    m3Stamp();
  }
  /** 卡片上那行「更新 HH:MM:SS」（live.js 的開關共用元件）。*/
  function m3Stamp() {
    if (!window.Live || !window.Live.stampCard) return;
    const allBad = IDX.every(x => state.err[x.id]);
    window.Live.stampCard('m3', { at: Math.max(state.at || 0, state.liveAt || 0),
      err: allBad ? (state.err.TSE || '分時抓不到') : '', every: isIntraday() ? MS_FAST : MS_AFTER, lbl: '5/15秒',
      // 這張卡裡三個數字的節奏不一樣（DECISIONS #299）：卡上的短字寫最快那個，提示框把三條分開講清楚
      tip: '盤中：加權、櫃買每 5 秒更新（證交所報價本身就是 5 秒一張快照）；台指期日盤每 15 秒更新（期交所報價，'
        + '經 Deno 代理，放慢是為了省免費額度）；整條分時走勢線每 10 秒對一次' });
  }
  window.addEventListener('tw:live', () => { patchFromLive(); });
  window.addEventListener('tw:livecard', (e) => {
    if (!e.detail || e.detail.key !== 'm3' || !document.getElementById('m3')) return;
    schedule();
    if (e.detail.on) refresh(true);
  });

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
        // ★ 2026-09-28：日線缺量的日子不再用前後 5 日均量補（那是假的量）—— 照實空著，週／月／季照實加總。
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
    /* 1 小時／4 小時不走這裡（synthBars ＋ 資料湖 index_intraday，見下面）。走到這裡代表週期代號對不上。*/
    state.histErr[key] = 'NOSRC';
  }

  /* ---------------------------------------------------------------- 1 小時／4 小時：依交易時段合成
     ★ 2026-09-24（Andy：「改成用 15 分 K 合成 1H、4H，依台股交易時段切」）
     ★★ 2026-09-26（Andy：「加權 櫃買 台指期，這三個到底有沒有統一的來源，不是一個有一個沒有」）

     來源 —— 三個指數同一條路，不再「加權一套、櫃買一套、台指期一套」：
       ① 多日：資料湖 `index_intraday.json`（build_payload 合成好的 H1／H4／M15）。
          裡面是每個交易日盤後由管線存下來的**證交所當日分時**（mis_ohlc_TSE／OTC、futures_chart，
          就是今天走勢圖那三個檔），加權另外保留 Yahoo 的兩年歷史（同一天兩邊都有時以證交所為準）。
          櫃買、台指期的歷史從第一個存到的交易日開始累積（過去的補不回來），卡片上一行短句講「自哪天起、幾天」。
       ② 今天：走勢圖那一份分時（證交所；台指期夜盤時是期交所），用 toBars(…, 15) 切成 15 分 K 再合成。
          今天那一盤以 ② 為準（第一手、10 秒更新），規則在 mergeLake()。
       以前還有一條「瀏覽器經 Worker 抓 Yahoo 15 分 K」（只有加權拿得到），以及「合成不到 2 根就整張退回日 K、
       寫『已改用日』」—— 兩條都拿掉了：累積天數不夠就照畫有的那幾天（4 小時選了只有 3 天就畫 3 根）。
       只有「湖裡一根都沒有、今天的分時也拿不到」這種什麼都畫不出來的情況，drawK 才退到日 K 並寫明原因。

     怎麼切（全部用台北牆鐘）
       · 日盤 1 小時：對齊 09:00 起每小時 —— 09、10、11、12、13 五根。
         台指期 08:45～09:00 那 15 分鐘併進 09:00 那根；13:00 之後（現貨 13:30 收、期貨 13:45 收）併進 13:00 那根。
         刻意不多開一根只有 15 分鐘的 08:45 或 13:30 K 棒：那種半截 K 棒的高低會被讀成「那一小時很安靜」。
       · 日盤 4 小時：一天一根（09:00～13:30／13:45）。台股一個交易日本來就只有 4.5～5 小時，
         硬切成「4 小時＋半小時」兩根，第二根永遠是殘缺的，不如一日一根、跟交易節奏對齊。
       · 夜盤 1 小時：15:00 起每小時（跨午夜照樣接著算，05:00 收）。
       · 夜盤 4 小時：一晚一根（15:00～翌日 05:00），歸在開盤那天。
     時間戳：用那一根「開始」的台北時間（跟其他週期同一個口徑：秒數＋8 小時）。
     ⚠ 這套切法跟 pipeline/compute/intraday_bars.py 的 session_key() 一字不差，改一邊記得改另一邊。 */

  /** 資料湖合成好的 1H／4H／15 分（site/data/index_intraday.json）。只載一次；讀不到記成 {}（只畫今天）。 */
  /* 回傳同一個 promise：加權、櫃買兩張卡的 refresh 會同時要湖資料（盤後退回 lakeDay），
     以前第二個呼叫者看到 busy 就直接回來、拿到 undefined，於是只有一張卡退得到湖。*/
  function loadLakeIntra() {
    if (state.lakeIntraP) return state.lakeIntraP;
    state.lakeIntraBusy = true;
    state.lakeIntraP = (async () => {
      try {
        const all = window.App ? await window.App.load('index_intraday', { fallback: {} }) : {};
        state.lakeIntra = all || {};
      } catch (e) { state.lakeIntra = {}; }
      state.lakeIntraBusy = false;
      state.lakeIntraP = null;            // 只共用「進行中」的那一次；之後有人把 lakeIntra 清回 undefined 就重抓
      draw();
    })();
    return state.lakeIntraP;
  }

  /** 一根 K 棒（台北牆鐘秒數）→ 它屬於哪一個 1 小時／4 小時的格子（回傳那一格的開始時間）。 */
  function sessKey(t, tf) {
    const day = Math.floor(t / 86400), min = Math.floor((t % 86400) / 60);
    const night = min >= 15 * 60 || min < 5 * 60 + 1;
    if (night) {
      if (tf === 'H4') return (min < 5 * 60 + 1 ? day - 1 : day) * 86400 + 15 * 3600;
      return Math.floor(t / 3600) * 3600;
    }
    if (tf === 'H4') return day * 86400 + 9 * 3600;
    const h = Math.min(13, Math.max(9, Math.floor(min / 60)));
    return day * 86400 + h * 3600;
  }
  /** 今天（或今晚）的分時 → 15 分 K → 1 小時／4 小時。回傳 { bars, n15, days, today }。
   *  多日的部分由呼叫端拿資料湖的 H1／H4 用 mergeLake() 接上。 */
  function synthBars(x, tf) {
    const d = seriesOf(x);
    const b15 = (d && !d.seed && d.points && d.points.length) ? toBars(d.points, 15, volUnit(x)) : [];
    b15.sort((a, b) => a[0] - b[0]);
    const out = []; let cur = null, key = null;
    for (const b of b15) {
      const k = sessKey(b[0], tf);
      if (k !== key) { if (cur) out.push(cur); key = k; cur = [k, b[1], b[2], b[3], b[4], b[5] || 0]; }
      else { cur[2] = Math.max(cur[2], b[2]); cur[3] = Math.min(cur[3], b[3]); cur[4] = b[4]; cur[5] += (b[5] || 0); }
    }
    if (cur) out.push(cur);
    const days = new Set(out.map(b => sessKey(b[0], 'H4'))).size;
    return { bars: out, n15: b15.length, days, today: b15.length };
  }
  /** 多日分 K 累積到哪 → 卡片上一行短句（Andy 2026-09-26：「櫃買／台指期分 K 自 YYYY-MM-DD 起累積（N 天）」，
   *  一行、不要長段落；「?」裡不放附註）。天數讀資料湖 src（build_payload 算的），不寫死。
   *   · 整段歷史都是自己累積的（first ≥ mis_first，也就是櫃買、台指期）→「自 … 起累積（N 天）」
   *   · 加權有 Yahoo 兩年歷史 → 不囉嗦（回空字串）
   *   · 湖裡這個指數還一盤都沒有 →「多日分 K 尚未累積，只含今日」
   *   · 台指期夜盤：2026-09-26 起期交所每筆成交合成 FUT_N 1 分 K（前 30 個交易日＋之後每天）→ 讀 FUT_N 的 src；
   *     湖裡還沒有夜盤時才說「夜盤多日分 K 未累積，只含今晚」。
   *  ★ 天數讀 m1_first／m1_days（1 分 K 不分來源：證交所分時＋期交所逐筆）；舊版 payload 沒有就退 mis_first／mis_days。 */
  function accumSay(x) {
    const night = isNight(x);
    const L = (state.lakeIntra || {})[lakeSym(x)] || {}, o = L.src || {};
    const f1 = o.m1_first || o.mis_first, n1 = o.m1_days != null ? o.m1_days : o.mis_days;
    if (night) return f1 ? `夜盤分 K 自 ${f1} 起（${n1} 晚）` : '夜盤多日分 K 未累積，只含今晚';
    if (f1 && (!o.first || o.first >= f1)) return `${x.short}分 K 自 ${f1} 起累積（${n1} 天）`;
    // src 缺欄位（舊版 payload）時用實際的 4 小時根數當天數 —— 有畫出多日就不能說「尚未累積」
    const days = o.days != null ? o.days : (L.H4 || []).length;
    if (!days) return `${x.short}多日分 K 尚未累積，只含今日`;
    return '';
  }
  /* ---------------------------------------------------------------- 成交量：只畫真實的量（2026-09-28 改寫）
     Andy 2026-09-28：「加權指數的成交量 15min 30min 1H 都沒有確切成交量」。
     以前（2026-09-25 那版）為了「每個週期都要有量」，Yahoo 那段歷史用「那天總量 × 分時量分布」估、灰色量柱標「估」，
     日 K 缺量的日子用前後 5 日均量補。那些都是假的量 —— 看起來有、其實不是那一小時真正成交的。
     ★ 新規則（延續 #258 第 3 點、取代 09-25 的估算，DECISIONS #272）：
       1. 只畫真實的量，**不估、不補、不畫一排 0**。
       2. 量的來源：
          · 加權、櫃買 ＝ **成交金額（元）**：證交所分時的 s（百萬元，2026-09-28 查證它不是張數）、
            FinMind 每 5 秒成交統計（加權，可回補兩年）、日線 index_ohlc 的成交金額 —— 三個來源同一把尺。
          · 台指期 ＝ 口數（期交所逐筆、證交所分時、日線）。
       3. 4 小時一盤一根 ＝ 那天的**日線實際總量**（真實值，不是估；分 K 沒量的那幾盤才用它）。
       4. 最近看得到的那一段（fitLast 那幾根）不到九成有量 → 整個量面板收掉，圖上方那一行寫「此週期無成交量資料」，
          滑鼠提示講原因。看得到量的時候，更早沒有量的那幾根就是空的（不畫 0 張、不畫假的）。 */
  const volUnit = (x) => (x.id === 'FUT' ? 1 : 1e6);   // 分時 s → K 棒量：指數 s 是百萬元 → 元；台指期 s 是口
  const isMoney = (x) => x.id !== 'FUT';
  /** K 棒量（元或口）→ 畫面上的字。 */
  function volTxt(x, v) {
    const f = F();
    if (!(v > 0) || !f) return '—';
    return isMoney(x) ? f.yi(v) : f.i(v) + ' 口';
  }
  /** 看得到的那一段（跟 drawK 的 fitLast 同一個根數）裡有量的比例。 */
  const VOL_SHOW = 0.9;
  function volRatio(bars, n) {
    if (!bars || !bars.length) return 0;
    const seg = bars.slice(-Math.max(1, n || bars.length));
    return seg.filter(b => b[5] > 0).length / seg.length;
  }
  /** 資料湖日線的量（4 小時一盤一根用）。只載一次，載完重畫。 */
  async function loadDailyVol() {
    if (state.dvolBusy || state.dvol) return;
    state.dvolBusy = true;
    try {
      const all = window.App ? await window.App.load('index_ohlc', { fallback: {} }) : {};
      const o = {};
      Object.keys(all || {}).forEach(sym => {
        const m = new Map();
        (all[sym] || []).forEach(b => { if (b && +b[5] > 0) m.set(String(b[0]).slice(0, 10), +b[5]); });
        o[sym] = { m };
      });
      state.dvol = o;
    } catch (e) { state.dvol = {}; }
    state.dvolBusy = false;
    draw();
  }
  /** 4 小時（一盤一根）：那一根＝一整個交易時段，量直接用那天日線的**實際總量**。就地改 bars，回傳 Map(時間字串 → 'day')。
   *  ★ 2026-09-28：分 K 本身有量的盤也換成日線總量 —— 盤中逐分鐘成交值加總（FinMind 5 秒統計／證交所分時）
   *    比官方當日成交金額少約 5%（2026-09-24：7,366 億 vs 7,756 億；推測差在盤後定價、零股、鉅額不在盤中統計裡），
   *    同一天 4 小時那根跟日 K 那根差 5% 會被讀成「數字有錯」。日線還沒進湖的那一盤（通常是今天）才用分 K 加總。
   *  ⚠ 只處理「一盤只有一根」的情況（4 小時）；1 小時一天五根，拿日總量去分就是估，不做。 */
  function fillDayTotal(x, bars, night) {
    const out = new Map();
    if (!bars || !bars.length || typeof bars[0][0] !== 'number') return out;
    const dv = state.dvol ? state.dvol[night ? 'FUT_N' : x.id] : null;
    if (!dv) return out;
    const per = new Map();
    bars.forEach((b, i) => { const k = sessKey(b[0], 'H4'); per.set(k, (per.get(k) || []).concat(i)); });
    per.forEach((idx, k) => {
      if (idx.length !== 1) return;
      const b = bars[idx[0]];
      const date = new Date(k * 1000).toISOString().slice(0, 10);
      const tot = dv.m.get(date);
      if (tot > 0) { b[5] = tot; out.set(String(b[0]), 'day'); }
    });
    return out;
  }
  /** 量柱面板的後處理：量軸刻度的單位（指數＝億／萬元、台指期＝口）。KChart 每次 applyIndicators 都重建量柱，所以每畫一次套一次。 */
  function decorVol(x, k) {
    const s = k && k.panes && k.panes.vol && k.panes.vol[0];
    if (!s) return;
    try {
      s.applyOptions({ priceFormat: { type: 'custom', minMove: 1, formatter: isMoney(x)
        ? (v) => (Math.abs(v) >= 1e8 ? (v / 1e8).toFixed(Math.abs(v) >= 1e10 ? 0 : 1) + '億' : Math.round(v / 1e4) + '萬')
        : (v) => (Math.abs(v) >= 1e4 ? (v / 1e4).toFixed(1) + '萬口' : Math.round(v) + '口') } });
    } catch (e) { /* 圖表庫不支援就維持預設刻度 */ }
  }
  /** 沒有量時圖上方那一行的原因（滑鼠提示）。天數讀資料湖 src，不寫死。 */
  function noVolWhy(x, tfKey) {
    const o = (((state.lakeIntra || {})[lakeSym(x)] || {}).src) || {};
    const since = o.vol_first ? `（真實分鐘量從 ${o.vol_first} 起才有，共 ${o.vol_days} 天）` : '';
    if (x.id === 'OTC') return `櫃買指數的歷史分 K 只有價格（Yahoo）；逐分鐘成交值只有證交所分時檔，每天盤後存起來${since}，不足以畫量柱，所以不畫、也不估。`;
    if (x.id === 'TSE') return `加權的真實分鐘成交值（FinMind 每 5 秒成交統計）還在回補${since}；還沒補到的這一段不畫量柱、也不估。`;
    return `台指期這個週期沒有逐筆成交量${since}，不畫量柱。`;
  }
  /* ---------------------------------------------------------------- 量副圖高度三張連動（2026-09-28）
     Andy：「調整加權、櫃買、台指的成交量縮放只需要抓取其中一條，其他兩條會連動調整寬度」。
     把手＝Lightweight Charts 本身的面板分隔線（主圖與量柱中間那條，hover 會亮；chart.js baseOptions 開了 enableResize）。
     拖完放開 → 量這張的量副圖佔圖高的比例 → 存 localStorage `tw.m3.volr` → 另外兩張照同一個比例重排。
     重新整理、換週期、展開收合都讀同一個比例（KChart 的 opts.volRatio）。 */
  const VOLR_KEY = 'tw.m3.volr';
  /* 上限 0.45：mini 圖主圖至少要留一半（chart.js _ph 的 min），超過的話另外兩張會被夾住、三張對不齊。
     所以拖超過就三張（含被拖的那張）一起 snap 回 45%，保證「一樣」這件事永遠成立。*/
  const VOLR_MIN = 0.08, VOLR_MAX = 0.45;
  const clampR = (r) => Math.min(VOLR_MAX, Math.max(VOLR_MIN, r));
  function loadVolR() {
    try { const v = parseFloat(localStorage.getItem(VOLR_KEY)); return v >= VOLR_MIN && v <= VOLR_MAX ? v : null; } catch (e) { return null; }
  }
  function saveVolR(r) { try { localStorage.setItem(VOLR_KEY, String(Math.round(r * 1000) / 1000)); } catch (e) { /* 存不了就只連動這一次 */ } }
  /** 這張圖的量副圖現在佔圖高多少（沒有量副圖回 null）。 */
  function volShare(k) {
    try {
      if (!k || !k.paneIndex || k.paneIndex.vol == null) return null;
      const h = k.paneHeights(); const tot = Object.values(h).reduce((a, v) => a + (v || 0), 0);
      return tot > 0 && h.vol ? h.vol / tot : null;
    } catch (e) { return null; }
  }
  /** r0＝按下那一刻這張圖的比例。放開後比例沒變（只是點一下、拖的是 K 線本身）就什麼都不做。 */
  function syncVolFrom(id, r0) {
    const k = state.kcharts[id]; const r1 = volShare(k);
    if (r1 == null || (r0 != null && Math.abs(r1 - r0) < 0.01)) return;
    applyVolR(clampR(r1));
  }
  /** 三張一起套同一個比例（被拖的那張也套：超過上限時要 snap 回來），並記住。 */
  function applyVolR(r) {
    saveVolR(r);
    IDX.forEach(y => { const kk = state.kcharts[y.id]; if (kk && kk.setVolRatio) kk.setVolRatio(r); });
    state.volSyncN = (state.volSyncN || 0) + 1;                      // 驗收用：連動發生過幾次
  }
  /** 掛在圖表容器上（容器跨圖表活著，只掛一次）：按下時記比例、放開（不論放在哪）就量一次。 */
  function armVolSync(x, el) {
    if (el._volSync) return;
    el._volSync = true;
    el.addEventListener('pointerdown', () => {
      const r0 = volShare(state.kcharts[x.id]);
      const up = () => { document.removeEventListener('pointerup', up, true); setTimeout(() => syncVolFrom(x.id, r0), 60); };
      document.addEventListener('pointerup', up, true);
    }, true);
  }
  /** 資料湖 15 分 K → 30 分 K（對齊整點與半點；13:30 那根自成一根，跟今天的分時 toBars(…, 30) 同一個切法）。 */
  function rollMin(b15, n) {
    const out = []; let cur = null, key = null; const w = n * 60;
    for (const b of b15) {
      const k = Math.floor(b[0] / w) * w;
      if (k !== key) { if (cur) out.push(cur); key = k; cur = [k, b[1], b[2], b[3], b[4], b[5] || 0]; }
      else { cur[2] = Math.max(cur[2], b[2]); cur[3] = Math.min(cur[3], b[3]); cur[4] = b[4]; cur[5] += (b[5] || 0); }
    }
    if (cur) out.push(cur);
    return out;
  }

  /** 資料湖的 1H／4H ＋ 今天的分時合成出來的那幾根 → 一條序列。
   *
   *  ★ 2026-09-25 根因（線上 1H／4H 報「Value is null」約 35 筆、游標看板不出現）：
   *  舊寫法是「湖裡去掉今天那一盤 ＋ 今天的分時**直接接在最後面**」，默認今天的分時一定比湖裡每一根都新。
   *  但「今天的分時」其實是 `seriesOf(x)` 手上那一份 —— Worker 連不上時的 localStorage 快取、
   *  假日或開盤前停在上一個交易日、驗收的假資料（2026-09-14）都可能比湖裡最後一天還舊。
   *  舊的一盤被接在最後 → 時間倒退。Lightweight Charts 的正式版**不檢查**順序，
   *  直接吃進去，畫到那一段時內部 `ensureNotNull` 丟「Value is null」，游標看板也跟著畫不出來。
   *  （重現：把 TSE 的分時換成 2026-09-14 那一盤，1H／4H 各噴 10 筆錯、看板消失。）
   *
   *  新規則：
   *   · 湖裡最後一盤（含）之後的盤 → 用今天的分時（證交所第一手、盤中 10 秒一更，比湖新）。
   *   · 湖裡已經有、而且比湖裡最後一盤還舊的盤 → 用湖的（那是收完盤的完整紀錄，分時只是某一刻的快照）。
   *   · 湖裡沒有的舊盤 → 補進來。
   *  最後照時間排好 —— 真正的「嚴格遞增、不重複」保證由 cleanBars 負責，這裡只決定誰蓋誰。 */
  function mergeLake(lb, today) {
    const lake = (lb || []).map(b => b.slice());
    if (!today || !today.length) return lake;
    const lakeSess = new Set(lake.map(b => sessKey(b[0], 'H4')));
    const lastSess = lake.length ? sessKey(lake[lake.length - 1][0], 'H4') : -Infinity;
    const take = new Set(today.map(b => sessKey(b[0], 'H4'))
      .filter(s => s >= lastSess || !lakeSess.has(s)));
    return lake.filter(b => !take.has(sessKey(b[0], 'H4')))
      .concat(today.filter(b => take.has(sessKey(b[0], 'H4'))))
      .sort((a, b) => a[0] - b[0]);
  }

  /** K 棒時間 → 可以比大小的秒數。數字（台北牆鐘秒數）照用；'YYYY-MM-DD'（資料湖日線）當 UTC 午夜。
   *  認不得的回 NaN，由 cleanBars 丟掉。 */
  function barSec(t) {
    if (typeof t === 'number') return t;
    if (typeof t === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(t)) return Date.parse(t + 'T00:00:00Z') / 1000;
    return NaN;
  }
  /** 交給 Lightweight Charts 之前的最後一道清洗 —— 不依賴任何上游保證（防禦寫法）。
   *
   *  為什麼要有這一道：Lightweight Charts 的正式版不驗資料，時間倒退、重複、開高低收是 null／NaN
   *  都會被收下，然後在畫圖的某一幀內部 `ensureNotNull` 丟「Value is null」，錯誤訊息完全不指向資料。
   *  上游有四條路（資料湖、Yahoo、今天的分時、localStorage 快取），每條都各自可能出錯，
   *  與其每條路各自修，不如在唯一的出口把關：
   *   ① 時間認不得、或開高低收任一不是有限數 → 整根丟掉（畫一根假的比少一根更糟）。
   *   ② 高＝四價最大、低＝四價最小（合成時偶爾高 < 收，圖會畫出倒掛的影線）。
   *   ③ 量不是有限數 → 0（量是輔助資訊，不值得為它丟掉一根價格）。
   *   ④ 照時間排序；同一個時間出現兩次留**後面**那一根（mergeLake 已把較新的放後面）。 */
  function cleanBars(bars) {
    if (!bars || !bars.length) return [];
    const rows = [];
    bars.forEach((b, i) => {
      if (!b) return;
      const s = barSec(b[0]);
      // null／'' 用 + 轉會變成 0（有限數）—— 一根開盤 0 點的 K 棒比丟掉更糟，所以先當成缺值
      const num = (v) => (v === null || v === undefined || v === '' ? NaN : +v);
      const o = num(b[1]), h = num(b[2]), l = num(b[3]), c = num(b[4]);
      if (!Number.isFinite(s) || ![o, h, l, c].every(Number.isFinite)) return;
      const v = num(b[5]);
      rows.push({ s, i, b: [b[0], o, Math.max(o, h, l, c), Math.min(o, h, l, c), c, Number.isFinite(v) ? v : 0] });
    });
    rows.sort((a, b) => a.s - b.s || a.i - b.i);
    const out = [];
    for (const r of rows) {
      if (out.length && out[out.length - 1].s === r.s) out[out.length - 1] = r;
      else out.push(r);
    }
    return out.map(r => r.b);
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
  function toBars(pts, n, unit) {
    /* unit：分時的 s 換成 K 棒量的倍數。★ 2026-09-28 更正：加權／櫃買的 s 是「成交金額（百萬元）」→ ×1e6 存「元」
       （跟 index_ohlc.json 的成交金額、資料湖分 K 同一把尺，見 volUnit）；
       ★ 2026-09-25：台指期的 s 是「口」，以前也 ×1000，游標看板印「N 口」時就大了一千倍。台指期改傳 1（見 volUnit）。*/
    const u = unit == null ? 1000 : unit;
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
        cur = [Math.floor(p.ms / 1000) + 8 * 3600, po, ph, pl, p.c, (p.s || 0) * u];
      } else {
        cur[2] = Math.max(cur[2], ph); cur[3] = Math.min(cur[3], pl);
        cur[4] = p.c; cur[5] += (p.s || 0) * u;
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
     ★ 2026-09-23 起：夜盤報價真的抓不到時**留白**，不再退回日盤（Andy：「若沒有資訊則空白」）。
     以前為了遵守 N11「不該出現沒有數據」而退回日盤，結果是「按夜盤卻看到日盤的線」——
     那不是「有東西」，那是畫錯的東西。N11 的精神用「空白 ＋ 講清楚為什麼」來滿足。
     這個函式本身仍然可能回日盤那一份（沒有夜盤資料時），
     呼叫端一律用 `d.night` 判斷拿到的是不是真的夜盤。 */
  function seriesOf(x) {
    // 有期交所的分時序列，或有一筆真的落在夜盤時段的報價 —— 兩者任一就是「夜盤那一份」。
    // 兩個來源互不依賴：序列掛了還有報價，報價掛了序列自己也帶著開高低收。
    if (isNight(x)) return nightSeries();
    return state.data[x.id];
  }

  /** 夜盤現在走「推送」還是「輪詢」——**沿用現貨那條狀態列的講法**（live.js 的 stamp()），
   *  掛在既有那排字後面，不另外做一塊。
   *  平常沒人在意它；只有「數字為什麼跳得比較慢」的時候才需要一眼看得出走的是哪條路。
   *  ⚠ 只有夜盤那張卡才有 —— 日盤與加權／櫃買走的是原本的輪詢，狀態沒有變，不該多一個字。 */
  function futWayTag() {
    if (!nightHas()) return '';
    const push = state.fsMode === 'sse';
    const tip = push
      ? `推送（SSE）：跟代理保持一條連線，值一變就送過來（約 ${Math.round(FS_PUSH_HINT_MS / 1000)} 秒）。`
      : state.fsGaveUp
        ? '輪詢：代理沒有夜盤推送功能（可能還沒更新到新版），已退回每分鐘抓一次。'
        : '輪詢：目前用固定間隔去抓；推送連上之後會自動切過去。';
    return `<span class="m3-tag" data-way="${push ? 'sse' : 'poll'}" title="${tip}">`
      + `${push ? '推送' : '輪詢'}</span>`;
  }

  /* ★ 2026-09-24（Andy：「每張中間那兩行資訊移除：『開 高 低 昨收』與『成交 xx 億／日期時間』——
     只留名稱、大數字、漲跌」）。那兩行沒有刪掉資訊，是搬到這排數字的滑鼠提示（title）裡：
     開高低、昨收（夜盤是參考價）、成交值（台指期是口數與未平倉）、資料時間、夜盤合約代號都還拿得到。
     留在畫面上的只有「不寫就會被讀錯」的來源標籤：數字不是證交所即時（Yahoo／本機暫存／資料湖收盤）、
     以及夜盤走推送還是輪詢（小標）。*/
  function cardHead(x) {
    let d = seriesOf(x);
    const f = F();
    if ((!d || !d.points || !d.points.length) && !isNight(x) && state.lakeHead && state.lakeHead[x.id]) d = state.lakeHead[x.id];
    if (!d || !f) return `<div class="m3-nums"><span class="m3-px">—</span></div>`;
    const chg = (d.last != null && d.prev) ? d.last - d.prev : null;
    const pct = chg != null ? chg / d.prev * 100 : null;
    const dp = x.id === 'FUT' ? 0 : 2;
    const base = d.prevLabel || '昨收';
    const when = `${String(d.date || '').replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')} ${String(d.time || '').replace(/^(\d{2})(\d{2})(\d{2})?$/, '$1:$2')}`.trim();
    const extra = x.turnover
      ? `成交 ${d.amt != null ? f.n(d.amt / 100, 0) + ' 億' : '—'}`
      : `總量 ${d.vol != null ? f.i(d.vol) + ' 口' : '—'}` + (d.oi != null ? `　未平倉 ${f.i(d.oi)}` : '');
    /* ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：數字旁的來源膠囊（「最近交易日 10/05」「上次存的 10/05 13:30」
       「資料湖日線」「Yahoo」「本機暫存」）拿掉 —— 它們講的是「這份數字是哪個時段／哪一天的」。來源併進這排數字原本就有的滑鼠提示
       （那裡本來就寫資料時間），不另外加圖示。夜盤的「推送／輪詢」小標不是時段，留著。*/
    const tipTxt = `開 ${f.n(d.open, dp)}　高 ${f.n(d.high, dp)}　低 ${f.n(d.low, dp)}　${base} ${f.n(d.prev, dp)}\n${extra}　${when}`
      + (d.src && d.src !== 'taifex' && !d.night ? `\n來源：${d.src}` : '')
      + (d.night && d.symbol ? `\n夜盤合約 ${d.symbol}` : '');
    const tag = d.night ? futWayTag() : '';
    return `<div class="m3-nums" title="${f.esc(tipTxt)}" data-open="${d.open ?? ''}" data-prev="${d.prev ?? ''}">
      <span class="m3-px ${f.cls(chg)}">${f.n(d.last, dp)}</span>
      <span class="m3-chg ${f.cls(chg)}">${chg == null ? '—' : (chg > 0 ? '+' : '') + f.n(chg, dp)} ${f.pct(pct, 2)}</span>${tag}
    </div>`;
  }

  function mount() {
    const host = document.getElementById('m3');
    if (!host) return;
    // 重掛（例如切主題）之前先收掉舊的 Lightweight Charts，不然 ResizeObserver 會留著
    Object.keys(state.kcharts).forEach(killK);
    state.mode = ls.get(KEY_MODE, 'line') === 'k' ? 'k' : 'line';
    state.tf = normTf(ls.get(KEY_TF, 'D'));
    state.big = ls.get(KEY_BIG, '');
    if (!IDX.some(x => x.id === state.big)) state.big = '';
    /* ★ 2026-09-26：KPI 橫條（#hero）桌機時住在這個工具列裡（見 placeKpi）。
       下一行 innerHTML 會把整個工具列換掉 —— 不先把 #hero 搬回頁面上，它（連同 app.js 寫好的數字、
       漲跌家數／前五族群佔比的點擊、live.js 認的 [data-live] 格子）會跟著被丟掉，重掛之後就是一條空的。*/
    { const hero = document.getElementById('hero'); if (hero && host.contains(hero)) host.before(hero); }
    /* ★ 2026-09-24（Andy：「三張圖合併進一個大方框，彼此用細線隔開；『走勢圖／K 線』切換（及週期下拉）
       放在大框內左上角；那行說明文字拿掉（改 ?）」）。
       #m3Note 留著但不上畫面：它是會跟著模式／週期換字的口徑說明，「?」打開時由 HOW.m3 讀它。
       .m3-card 不再是 .card（外框只有一個：.m3-frame）；手機 ≤820px 的左右滑仍然吃 .m3-grid > .m3-card。*/
    host.innerHTML = `
      <div class="card m3-frame" id="m3Frame">
      <div class="m3-bar">
        <div class="seg" id="m3Mode"><button data-m="line">走勢圖</button><button data-m="k">K 線</button></div>
        <label class="m3-tfsel">週期
          <select id="m3Tf">
            ${HIST.filter(h => TF_SHOWN.indexOf(h.id) >= 0).map(h => `<option value="${h.id}">${h.label}</option>`).join('')}
          </select></label>
        <button class="howbtn pop" data-how="m3" data-ttl="大盤三張圖" aria-label="大盤三張圖怎麼看">?</button>
        <!-- 2026-09-26：這顆不在標題裡，data-ttl 給彈窗標題（改前彈窗標題是預設的「說明」，全站問號普查抓到的） -->
        <span class="note" id="m3Note" hidden></span>
        <div class="m3-kpis" id="m3Kpis"></div>
      </div>
      <div class="howtxt" id="how-m3" hidden></div>
      <div class="m3-grid" id="m3Grid">${IDX.map(x => `
        <div class="m3-card" data-id="${x.id}">
          <div class="m3-h">
            <h3 title="${x.sub}">${x.name}</h3>
            ${x.id === 'FUT' ? '<span class="m3-sess" id="futSess" data-s="day">日盤</span>' : ''}
            <button class="btn small m3-big" data-id="${x.id}">展開 ⤢</button>
          </div>
          ${cardHead(x)}
          <div class="m3-fb" data-for="${x.id}"></div>
          <div class="m3-chart" id="m3c-${x.id}"></div>
        </div>`).join('')}</div></div>`;
    $$('#m3Mode button').forEach(b => b.onclick = () => { state.mode = b.dataset.m; ls.set(KEY_MODE, state.mode); draw(); });
    $('#m3Tf').onchange = (e) => { state.tf = normTf(e.target.value); ls.set(KEY_TF, state.tf); draw(); };
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
    /* ★ 2026-09-24：「日盤／夜盤」切換鈕拿掉（Andy：「合併成一張 —— 自動顯示目前有資料的那一段」）。
       時鐘決定要不要去抓夜盤；抓到了（`nightHas()`）才顯示夜盤，否則整張卡顯示日盤。
       標題旁的 `#futSess` 小標註明現在畫的是哪一段（draw() 會更新）。*/
    state.futSession = pickSession();
    loadNightPts();
    $$('#m3Grid .m3-big').forEach(b => b.onclick = () => {
      state.big = state.big === b.dataset.id ? '' : b.dataset.id;
      ls.set(KEY_BIG, state.big); draw();
    });
    placeKpi();
    /* ★ 2026-10-04 Andy：「每次開啟都會先是 K 線圖，然後才切到走勢圖」。
       以前掛載當下就 draw()：分時還沒回來＋週末有 sessionHint → 直接退去畫日 K，等 refresh 回來才換走勢圖。
       現在：非交易時段先用資料湖最近一個完整交易日的 15 分 K 把走勢圖與數字列種好（seedLake），
       第一幀就是使用者選的模式；第一輪 refresh 也先等種子落地，免得兩邊搶著畫。*/
    if (!isIntraday() || !liveOK()) state.seedP = seedLake();   // 非管理者：盤中也一樣只種資料湖的最近交易日
    draw();
    if (liveOK()) refresh(true);
    schedule();
  }
  /* ★ 2026-10-04 晚（Andy 21:19 週日截圖：三張圖卡在「載入中…」；21:20：「有最後一筆數據就存起來，以後打開直接貼上」）。
     以前種子要先下載 index_intraday（944KB）＋ index_ohlc（334KB）才畫得出來。現在依序找、誰新用誰：
       ① 這台瀏覽器上次真的畫出來的分時（localStorage m3.snap.<id>，存在 snapPut；卡片標「上次存的 日期 時間」）
       ② index_lastday.json（build_payload 切好的最近一個完整交易日 1 分 K ＋ 該日前一交易日的昨收，約 19KB）
       兩個都沒有才退回舊流程（大檔）。大檔改成背景補：只有 K 線模式（要多日）才順手去抓。
     種子只給走勢圖與數字列（d.seed，分 K 合成不吃它）；Worker 的即時資料一回來就整個換掉。*/
  function snapPut(x, d) {
    try {
      if (!d || d.seed || !d.points || d.points.length < 2 || d.night) return;
      localStorage.setItem('m3.snap.' + x.id, JSON.stringify({ at: Date.now(), d }));
    } catch (e) { /* 私密視窗／滿了：只是下次少一個種子 */ }
  }
  function snapGet(x) {
    try { const o = JSON.parse(localStorage.getItem('m3.snap.' + x.id) || 'null');
      return o && o.d && o.d.points && o.d.points.length >= 2 ? o : null; } catch (e) { return null; }
  }
  function fromLastday(x, o) {
    if (!o || !o.points || o.points.length < 2 || !o.date) return null;
    const y = +o.date.slice(0, 4), mo = +o.date.slice(4, 6) - 1, dd = +o.date.slice(6);
    const base = Date.UTC(y, mo, dd) - 8 * 3600 * 1000;
    const pts = o.points.map(p => ({ ms: base + p[0] * 60000, min: p[0], c: p[1], s: 0 }));   // 種子不畫量
    return { id: x.id, name: x.name, src: '最近交易日 ' + o.date.slice(4, 6) + '/' + o.date.slice(6), date: o.date, time: '收盤',
      prev: o.prev, open: o.open, high: o.high, low: o.low, last: o.last, vol: null, amt: null, points: pts };
  }
  async function seedLake() {
    try {
      let ld = null;
      try { ld = window.App ? await window.App.load('index_lastday', { fallback: null }) : null; } catch (e) {}
      IDX.forEach(x => {
        const cur = state.data[x.id];
        if (cur && cur.points && cur.points.length) return;
        const a = fromLastday(x, ld && ld[x.id]);
        const sp = liveOK() ? snapGet(x) : null;     // 這台瀏覽器存過的即時分時：只給管理者用（非管理者一律看資料湖那一份）
        let pick = a;
        if (sp && (!a || String(sp.d.date || '') > a.date)) {
          const t = new Date(sp.at).toLocaleString('sv-SE', { timeZone: 'Asia/Taipei' }).slice(5, 16);
          pick = Object.assign({}, sp.d, { src: '上次存的 ' + t.replace('-', '/') });
        }
        if (!pick) return;
        pick.seed = true;
        state.data[x.id] = pick;
      });
      if (!ld || IDX.some(x => !(state.data[x.id] && state.data[x.id].points && state.data[x.id].points.length))) {
        // 舊資料（沒有小檔）或小檔缺代號 → 原流程：資料湖 15 分 K ＋ 日 K 昨收
        await loadLakeIntra();
        const all = window.App ? await window.App.load('index_ohlc', { fallback: {} }) : {};
        IDX.forEach(x => {
          const cur = state.data[x.id];
          if (cur && cur.points && cur.points.length) return;
          const L = lakeDay(x); if (!L) return;
          const rows = (all && all[x.id]) || [];
          const ymd = L.date.slice(0, 4) + '-' + L.date.slice(4, 6) + '-' + L.date.slice(6);
          const pb = rows.filter(b => String(b[0]) < ymd);
          if (pb.length) L.prev = pb[pb.length - 1][4];
          L.seed = true;
          state.data[x.id] = L;
        });
      } else if (state.mode === 'k') {
        setTimeout(() => { loadLakeIntra(); }, 0);       // K 線要多日：背景補，不擋第一幀
      }
    } catch (e) { /* 種不起來就照舊等 refresh */ }
    state.seedP = null;
    draw();
  }

  /* 2026-10-04：app.js 先貼存檔、網路版到了且內容不同時發 tw:data-refreshed（app.js 的 swrSettle）。
     大盤三張圖不重掛（重掛會閃），只把吃資料湖檔的快取清掉、整張重畫一次，讓 K 線／種子換成新檔。*/
  window.addEventListener('tw:data-refreshed', () => {
    if (!document.getElementById('m3')) return;
    state.lakeIntra = undefined;
    IDX.forEach(x => { const d = state.data[x.id]; if (d && d.seed) delete state.data[x.id]; });
    state.seedP = seedLake();
  });

  /* ★ 2026-09-26（Andy：「將我把這內容放進來，並且排版一下」）：總覽頂端那條 KPI 橫條
     （加權指數／成交值／漲跌家數／前五族群佔比）搬進這張卡的工具列，排在「?」右邊那段本來空著的地方。
     做法是**搬同一個節點**（#hero），不是另外畫一份：
       · app.js 寫數字與點擊（wireKpiDrill 綁在 #hero .kpi.clickable 上）、live.js 盤中改 [data-live] 格子，
         兩邊都是在整份文件裡找，節點搬到哪裡都找得到 —— 不用多維護第二套、也不會有兩份數字對不上。
       · 手機（≤640px，mobile3.js 的斷點）維持原位：手機的分段導覽（modules.js 的 #hero 選擇器）與版面都沒動，
         所以窄到手機寬就搬回 #m3 前面；放寬再搬進來（matchMedia 監聽，縮放視窗也跟著走）。*/
  const KPI_MOBILE = window.matchMedia ? window.matchMedia('(max-width:640px)') : null;
  function placeKpi() {
    const hero = document.getElementById('hero'), host = document.getElementById('m3');
    const slot = document.getElementById('m3Kpis');
    if (!hero || !host) return;
    const mobile = KPI_MOBILE ? KPI_MOBILE.matches : window.innerWidth <= 640;
    if (!mobile && slot) {
      if (hero.parentNode !== slot) slot.appendChild(hero);
      slot.hidden = false;
    } else {
      if (host.contains(hero)) host.before(hero);
      if (slot) slot.hidden = true;
    }
  }
  if (KPI_MOBILE) {
    const onMq = () => placeKpi();
    if (KPI_MOBILE.addEventListener) KPI_MOBILE.addEventListener('change', onMq); else if (KPI_MOBILE.addListener) KPI_MOBILE.addListener(onMq);
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

  /** 「?」裡的來源與量的完整口徑（#m3Note → app.js HOW.m3 打開時讀）。
   *  ★ 2026-09-25：卡片上只留一行短句，完整口徑搬到這裡。天數是讀資料湖實際的 index_intraday.json 算的，不寫死。
   *  ★ 2026-09-26：多日分 K 改成三個指數同一個來源（證交所分時每天盤後存進資料湖）—— 以前那段
   *    「為什麼櫃買、台指期只有今天（^TWOII 停更、付費等級）」已經不成立，拿掉。*/
  function srcNote() {
    const L = state.lakeIntra || {};
    const per = IDX.map(x => {
      const o = L[x.id] || {};
      const s = o.src || {};
      const d4 = (o.H4 || []).length, d15 = new Set((o.M15 || []).map(b => sessKey(b[0], 'H4'))).size;
      if (!d4) return `${x.short}還沒累積（只有今天）`;
      const bits = [];
      if (s.taifex_first) bits.push(`期交所逐筆自 ${s.taifex_first} 起 ${s.taifex_days} 天`);
      if (s.mis_first) bits.push(`證交所分時自 ${s.mis_first} 起 ${s.mis_days} 天`);
      return `${x.short} ${d4} 個交易日（其中 ${d15} 天有 15 分 K${bits.length ? '；' + bits.join('、') : ''}）`;
    }).join('、');
    const nt = ((L.FUT_N || {}).src) || {};
    const nightSay = nt.m1_first
      ? `台指期夜盤的多日分 K＝期交所逐筆合成，自 ${nt.m1_first} 起 ${nt.m1_days} 晚。`
      : '台指期夜盤的多日分 K 還沒有（只含今晚）。';
    const tsrc = (L.TSE || {}).src || {};
    const tseVol = tsrc.finmind_first ? `加權自 ${tsrc.finmind_first} 起 ${tsrc.finmind_days} 天有 FinMind 每 5 秒成交統計合成的真實逐分鐘成交值（回補中）` : '加權的真實逐分鐘成交值（FinMind 每 5 秒成交統計）還在回補';
    return '【來源】日／週／月／季＝資料湖日線（FinMind：加權 TAIEX、櫃買 TPEx、台指期 TX 近月），週月季由日線合成。'
      + '1 小時／4 小時／15／30 分＝資料湖分 K：加權、櫃買各有 Yahoo 兩年 60 分 K 與近 60 天 15 分 K（櫃買代號 IX0043.TWO），'
      + '加權另有 FinMind 每 5 秒資料合成的 1 分 K（真實高低與成交值），三個指數每天盤後再存證交所當日分時；同一盤有多個來源時取最細、最真的那個。'
      + `依交易時段切（1 小時 09:00 起每小時、13:00 那根含到收盤；4 小時一盤一根；夜盤一晚一根），多日分 K：${per}。`
      + '1／5 分只有今天。' + nightSay
      + '台指期逐筆資料來源：臺灣期貨交易所（政府資料開放平臺 資料集 20668，政府資料開放授權條款第 1 版）。'
      + '【量】加權、櫃買的量一律是成交值（元），台指期是口數。' + tseVol + '；櫃買的歷史分 K 只有價格（Yahoo 指數沒有量），'
      + '只有證交所分時存下來的那幾天有逐分鐘成交值。沒有真實量的那一段不畫量柱、也不估；看得到的那一段不到九成有量就整個量面板收起來。'
      + '4 小時一盤一根＝當天日線的實際成交總量。'
      + '【分 K 的開高低】由每分鐘收盤價合成：開＝前一分收盤，高低是分鐘收盤的極值（卡片上的「高／低」才是當天真正極值）。';
  }

  let drawGen = 0;                       // draw() 第幾輪（分張畫到一半又被叫一次時，舊的那一輪自己停）
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
          // 2026-10-03（DECISIONS #299）：三個數字的更新節奏不一樣，「?」裡講清楚（卡上只寫「5/15秒」）
          + '盤中更新：加權、櫃買每 5 秒；台指期日盤每 15 秒（省 Deno 免費額度）；夜盤每 60 秒。'
        : srcNote() + (histDef(state.tf) ? lakeSpan() : '');
    }
    // 台指期的日盤／夜盤鈕：選中的要亮起來（以前藏在 drawFutNight 裡，拆掉之後移到這裡）
    // 台指期現在畫的是哪一段（2026-09-24 切換鈕拿掉之後，這個小標是唯一的標示，不准省）
    syncFutSess();
    grid.classList.toggle('big', !!state.big);
    const one = (x) => {
      const card = grid.querySelector(`.m3-card[data-id="${x.id}"]`);
      if (!card) return;
      card.classList.toggle('on', state.big === x.id);
      card.style.display = (state.big && state.big !== x.id) ? 'none' : '';
      const head = card.querySelector('.m3-nums');
      if (head) head.outerHTML = cardHead(x);
      const btn = card.querySelector('.m3-big');
      if (btn) btn.textContent = state.big === x.id ? '收合 ⤡' : '展開 ⤢';
      drawOne(x);
      syncFb(x, card);
    };
    const tail = () => {
      // K 線模式、空狀態、退回日盤 —— 這些情況下 paintPulse 會自己把燈移掉
      paintPulses();
      setTimeout(() => window.dispatchEvent(new Event('resize')), 30);
    };
    /* ★ 2026-09-25 效能（perf-2）：**第一次**把三張圖建出來時，一張一張來、中間讓瀏覽器畫一幀。
       三張 K 線（含指標）同一個任務建完＝ drawK 243ms ＋ 下一幀 Lightweight Charts 一次畫三張 293ms，
       首次開總覽最長的兩個卡頓就是它們（4 倍降速 1 秒以上），這段時間整頁點不動。
       拆開之後每一張各自一個任務（約 80～100ms）、各自一幀畫出來，總工作量一樣，但中間點得動、捲得動。
       只在「三張都還沒有圖」時這樣做（＝剛進站、資料剛到）；之後的切週期、展開、盤中更新照舊同一個任務畫完，
       行為與驗收都不變。draw() 再被叫一次就取消還沒畫的那幾張（新的那一輪會全部重畫）。*/
    const gen = ++drawGen;
    const hasChart = (x) => { const el = document.getElementById('m3c-' + x.id);
      return !!(el && (state.kcharts[x.id] || (typeof echarts !== 'undefined' && echarts.getInstanceByDom(el)))); };
    if (IDX.length > 1 && !IDX.some(hasChart)) {
      const rest = IDX.slice();
      const step = () => {
        if (gen !== drawGen) return;
        one(rest.shift());
        if (!rest.length) { tail(); return; }
        // 讓出一幀：rAF 讓剛建好的那張先畫出來，setTimeout 把下一張排到新的任務（分頁在背景 rAF 不跑，100ms 保底）
        let done = false; const go = () => { if (!done) { done = true; setTimeout(step, 0); } };
        requestAnimationFrame(go); setTimeout(go, 100);
      };
      step();
      return;
    }
    IDX.forEach(one);
    tail();
  }

  /* ★ 2026-09-24：圖上方那行「已改用日／只有幾根日 K／先顯示資料湖日 K」以前是圖表容器的 ::before，
     會把 Lightweight Charts 往下推 21px、戳出大方框底（三格高低還不一樣）。
     改成圖表上方一條**固定 18px** 的字列（.m3-fb）：三格永遠一樣高，字太長就截斷、完整內容在滑鼠提示。
     `data-fallback` 仍然寫在圖表容器上（驗收與其他段落照舊讀它），只是不再由 ::before 畫出來。*/
  function syncFb(x, card) {
    const fb = card && card.querySelector('.m3-fb'); if (!fb) return;
    const el = document.getElementById('m3c-' + x.id);
    const t = (el && el.dataset.fallback) || '';
    // 沒有量柱時，滑鼠提示多一句「為什麼沒有」（2026-09-28，noVolWhy）
    const why = (el && el.dataset.novolWhy) || '';
    const tt = why ? t + '\n' + why : t;
    if (fb.textContent !== t) fb.textContent = t;
    if (fb.title !== tt) fb.title = tt;
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
    /* ★ 2026-10-04 修：夜盤點數不足時 nightNote() 會在圖表容器裡放一塊說明面板（.m3-night），只有夜盤那條路會收它。
       從夜盤換回日盤（時段翻頁、夜盤資料沒了退回日盤）時它留在容器裡、蓋在日盤走勢上面 ——
       游標移上去被它吃掉、讀不到價格（週日驗收「走勢圖 FUT 游標」紅燈的根因：hit-test 打到的是 div.note）。
       畫日盤一律先把它清掉。*/
    if (!night) { const nb = el.querySelector(':scope > .m3-night'); if (nb) nb.remove(); }
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
      /* ★ 2026-09-23 Andy：「幫我修復 夜盤拿不到資訊的問題，並且若沒有資訊則空白」
         ------------------------------------------------------------------
         以前這裡的做法是**退回去畫日盤那條線**，只在圖上加一行
         「夜盤報價目前拿不到，先顯示日盤走勢」。他明確不要這個，而且他是對的：
         使用者按的是「夜盤」，看到的卻是日盤的線在動 —— 瞄一眼很容易當成夜盤正在跳。
         **畫錯的線比空白更會誤導**，那一行小字擋不住第一眼的印象。
         所以現在：拿不到夜盤資料就留白，只留一句極簡的狀態文字說明為什麼拿不到。
         ⚠ 這條路徑只管夜盤；日盤那一邊一個字都沒動。*/
      killK(x.id);
      if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
      el.classList.add('isempty');
      el.dataset.kind = '';                     // 燈是靠這個判斷的，清掉才不會有燈浮在空白上
      /* 先問「是不是根本不在夜盤時段」（那是最常見也最無害的原因），
         再落回 nightWhy() 講真正的錯誤（Worker 舊版、期交所回空、還沒問到合約代號…）。
         這段字是下一個人唯一的線索，所以寧可囉嗦也不要只寫「沒有資料」。*/
      const why = sessionHint(x, true) || nightWhy();
      el.innerHTML = `<div class="empty">夜盤資料未取得${why ? '：' + why : ''}</div>`;
      return;
    }
    if (!d || !d.points.length) {
      /* ★ 2026-09-24（審查 R1：「Worker 掛掉就全倒並顯示英文『抓不到：Failed to fetch』」）。
         以前這裡只印一行錯誤（還是英文），三張圖整塊空白。證交所分時、Yahoo 1 分線、本機暫存
         三層備援都走不到時（例如 Worker 連不上、或根本還沒開盤），**最後一層一律退到資料湖的日 K**
         （index_ohlc.json，三個代號都有），圖上方用一行字講清楚為什麼、畫的是什麼。
         還在「載入中」（第一輪還沒回來、也沒有錯誤）才先印載入中。*/
      const hint = sessionHint(x, false);
      // 2026-10-04：第一輪還沒回來（或資料湖種子還在路上）一律先「載入中」，不准先退日 K 再跳成走勢圖
      if (!err && state.seedP && state.mode !== 'k') {
        killK(x.id);
        if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
        el.classList.add('isempty'); el.dataset.kind = '';
        el.innerHTML = '<div class="empty">載入中…</div>';
        return;
      }
      el.classList.remove('isempty');
      const why = err === 'NOCHART' ? '即時代理是舊版（沒有分時功能）' : err ? errZh(err) : (hint || '還沒有今天的分時');
      /* ★ 2026-09-25：K 線選 15／30 分、而資料湖有這張的 15 分 K（加權約 60 天）→ 照畫多日 15／30 分，
         只是少了今天那一盤；不必整張退回日 K。其他週期／沒有湖資料的照舊退日 K。*/
      const mt = +state.tf;
      if (state.mode === 'k' && (mt === 15 || mt === 30) && (((state.lakeIntra || {})[x.id] || {}).M15 || []).length >= 1) {
        el.dataset.fallback = why + '，只有資料湖的歷史 ' + mt + ' 分 K';
        drawK(x, { points: [] }, el);
        return;
      }
      drawK(x, {}, el, 'D', why + '，先顯示資料湖的日 K');
      return;
    }
    el.classList.remove('isempty');
    if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
  }

  /** 瀏覽器／代理丟回來的英文錯誤 → 中文（畫面上一律繁中，原字串留在括號裡給除錯用）。*/
  function errZh(e) {
    const t = String(e || '');
    if (/failed to fetch|networkerror|load failed/i.test(t)) return '連不到即時代理';
    if (/HTTP (\d+)/.test(t)) return '代理回 ' + t.match(/HTTP (\d+)/)[0];
    if (/timeout|timed out|abort/i.test(t)) return '代理逾時';
    return t;
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
  /** 走勢圖要用的三組陣列與兩個軸的範圍。
   *  `drawLine()`（整張畫）與 `patchLine()`（只換最後一根）**一定要共用這一支** ——
   *  兩邊各算一次，推一筆進來就會出現「線動了、軸沒動」這種對不上的畫面。 */
  function lineData(x, d) {
    // 夜盤走的是 15:00~翌日 05:00 的軸（凌晨那段的分鐘數是 24*60+）
    const [s0, s1] = d.night ? SESSION_NIGHT : SESSION[x.id];
    const cats = []; for (let m = s0; m <= s1; m++) cats.push(hhmm(m));
    const price = new Array(cats.length).fill(null);
    const vol = new Array(cats.length).fill(null);
    d.points.forEach(p => { const i = p.min - s0; if (i >= 0 && i < cats.length) { price[i] = p.c; vol[i] = p.s; } });
    const up = d.last != null && d.prev ? d.last >= d.prev : true;
    const col = up ? '#ff4d6d' : '#2ee59d';
    // 價格軸以昨收為中心對稱，漲跌幅一眼看得出來（跟官方走勢圖同一個習慣）
    const vals = price.filter(v => v != null);
    const span = Math.max.apply(null, vals.map(v => Math.abs(v - (d.prev || v))).concat([(d.prev || 1) * 0.001]));
    const lo = (d.prev || vals[0]) - span * 1.08, hi = (d.prev || vals[0]) + span * 1.08;
    const vmax = Math.max.apply(null, vol.filter(v => v != null).concat([1]));
    return { s0, s1, cats, price, vol, col, lo, hi, vmax };
  }

  /** 走勢圖那顆呼吸燈要標在哪一點。畫完（或補完）都要重算一次。 */
  function setLinePulse(x, d, L) {
    markMove(x, d);
    let idx = -1;
    for (let i = L.price.length - 1; i >= 0; i--) if (L.price[i] != null) { idx = i; break; }
    let i0 = -1;
    for (let i = 0; i < L.price.length; i++) if (L.price[i] != null) { i0 = i; break; }
    state.pulses[x.id] = {
      idx, i0, val: idx >= 0 ? L.price[idx] : null, col: L.col,
      label: idx >= 0 ? L.cats[idx] : '', night: !!d.night, live: isPulsing(x, d),
    };
    paintPulse(x.id);
  }

  /* ★ 只換最後一根，不整張重畫（2026-09-23 夜盤推送）。
     推送進來的頻率比輪詢高很多。如果每一筆都走 `drawLine()`：
     ECharts 會把整個 option 重建一次（軸、tooltip、markLine、漸層），
     補間動畫從頭跑，視覺上就是「整張圖每十秒閃一下」，而且 tooltip 會被關掉。
     所以這裡只送 series 的資料與價／量軸的範圍，其餘設定原封不動 ——
     跟個股 K 線那邊 `KChart.applyQuote()` 是同一個想法（那支不歸這一輪改，做法照抄）。

     ⚠ 只要「軸的前提」變了就回 false，交給 `drawLine()` 整張畫：
       · 容器現在畫的不是走勢圖（切到 K 線、或被清成空狀態）
       · 日盤／夜盤換邊（時間軸整條不一樣）
       · 參考價變了（markLine 的位置與標籤要跟著換）
     寧可閃一下，也不要讓線和軸對不上。*/
  // 價格軸刻度的小數位數（看振幅）：drawLine 的 formatter 與 patchLine 的「要不要整張重畫」共用這一支
  const axisDec = (span) => (span < 10 ? 2 : span < 100 ? 1 : 0);

  /* ★ 2026-10-01 卡頓（Andy：「整體畫面卡頓有點多」，DECISIONS #284）：盤中每 5 秒那一輪的輕量版。
     以前 live.js 每 5 秒一批報價回來（patchFromLive）、台指期每 5 秒（fastTick）、分時每 10 秒（refresh）
     都走 draw()：三張圖各自 drawLine() 整張重建（notMerge，軸、tooltip、markLine、漸層全部重來），
     最後還 dispatch 一次假的 window resize —— 等於每 5 秒叫醒全站所有 resize 監聽（每張圖 resize 檢查、
     標題圖示重量 fitAll…）。這裡改成：每張先試 patchLine()（只換線與量的資料、價／量軸範圍），
     標題數字照舊整塊換（cardHead）；**任何一張的前提不符就整個退回 draw()**（K 線模式、夜盤、
     參考價變了、軸刻度小數位數要換、容器不是走勢圖、還沒有資料…），畫面與資料口徑跟以前一樣，只是少做事。
     頻率不變（仍是每 5 秒），只減少每一輪做的工作。
     ★ 2026-10-02 再收一刀（同一批 #284）：`ids`＝這一輪真的有變的那幾張。live.js 那一批只帶加權／櫃買、
       期交所那支只帶台指期 —— 以前兩條路都把三張一起補，沒變的那張也整張重畫一次（每次 setOption 會跑約 12 幀的補間重畫）。
       前提檢查照舊看三張（任何一張不能補就整個退回 draw()），只有「補哪幾張」縮小；分時檔 10 秒那一輪不帶 ids ＝三張都補。*/
  function drawLive(ids) {
    const grid = document.getElementById('m3Grid');
    /* ★ 2026-10-05：K 線的日／週／月 —— 只把「這一輪有變的那張」最後一根就地更新（drawK 走 setBars 的尾巴快路），
       不再整張 draw()。節流與「只補有變的那張」（#284）照舊由呼叫端的 ids 決定。*/
    if (grid && state.mode === 'k' && histDef(state.tf) && histDef(state.tf).lake) {
      for (const x of IDX) {
        if (ids && ids.indexOf(x.id) < 0) continue;
        const el = document.getElementById('m3c-' + x.id);
        const card = grid.querySelector(`.m3-card[data-id="${x.id}"]`);
        if (!el || !card || card.style.display === 'none') continue;
        if (el.dataset.kind !== 'k' || !state.kcharts[x.id]) { draw(); return; }
        const fb0 = el.dataset.fallback;
        drawK(x, isNight(x) ? seriesOf(x) : (state.data[x.id] || {}), el);
        if (el.dataset.fallback !== fb0) syncFb(x, card);
        const head = card.querySelector('.m3-nums');
        if (head) { const h = cardHead(x); if (head.outerHTML !== h) head.outerHTML = h; }
      }
      return;
    }
    if (!grid || state.mode !== 'line' || state.futSession === 'night' || IDX.some(isNight)) { draw(); return; }
    const todo = [];
    for (const x of IDX) {
      const el = document.getElementById('m3c-' + x.id);
      const card = grid.querySelector(`.m3-card[data-id="${x.id}"]`);
      const d = state.data[x.id];
      if (!card) continue;
      if (!el || !d || !d.points || !d.points.length || el.dataset.kind !== 'line' || !el._m3line) { draw(); return; }
      todo.push([x, d, el, card]);
    }
    for (const [x, d, el, card] of todo) {
      if (ids && ids.indexOf(x.id) < 0) continue;            // 這一輪沒變的那張：資料一樣、畫出來也一樣，不重畫
      if (card.style.display === 'none') continue;          // 展開別張時被藏起來的那兩張：draw() 也只是畫一張看不見的圖
      if (!patchLine(x, d, el)) { draw(); return; }
      const head = card.querySelector('.m3-nums');
      if (head) { const h = cardHead(x); if (head.outerHTML !== h) head.outerHTML = h; }
      syncFb(x, card);
    }
    $$('#m3Mode button').forEach(b => b.classList.toggle('on', b.dataset.m === state.mode));
  }

  function patchLine(x, d, el) {
    if (!el || el.dataset.kind !== 'line') return false;
    if (typeof echarts === 'undefined') return false;
    const inst = echarts.getInstanceByDom(el);
    const H = el._m3line;
    if (!inst || !H || H.night !== !!d.night || H.prev !== d.prev) return false;
    const L = lineData(x, d);
    if (L.cats.length !== H.cats.length) return false;
    if (H.dec != null && H.dec !== axisDec(L.hi - L.lo)) return false;   // 軸刻度小數位數要換 → 整張畫（2026-10-01）
    // tooltip 與量柱顏色的 callback 讀的是這個盒子（不是閉包裡那份陣列）——
    // 就地換掉，滑鼠移上去看到的才是最新的值，而不是上一輪的殘影。
    H.price = L.price; H.vol = L.vol; H.d = d;
    inst.setOption({
      yAxis: [{ min: L.lo, max: L.hi }, { max: L.vmax, interval: L.vmax || 1 }],
      series: [
        { data: L.price, lineStyle: { color: L.col },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexa(L.col, .30) }, { offset: 1, color: hexa(L.col, 0) }]) } },
        { data: L.vol },
      ],
    }, { lazyUpdate: false });
    setLinePulse(x, d, L);
    return true;
  }

  function drawLine(x, d, el) {
    killK(x.id);
    // 從 K 線切回來時容器裡還留著 Lightweight Charts 的 DOM，不清掉 ECharts 會疊在上面
    if (el.dataset.kind !== 'line') { el.innerHTML = ''; el.dataset.kind = 'line'; }
    const f = F(); if (!f) return;
    const L = lineData(x, d);
    const s0 = L.s0, cats = L.cats, price = L.price, vol = L.vol;
    const col = L.col, lo = L.lo, hi = L.hi, vmax = L.vmax;
    const dp = x.id === 'FUT' ? 0 : 2;
    const unit = x.id === 'FUT' ? '口' : '張';   // （只剩台指期用；指數的分時量是成交值，見 sTxt）
    /* ★ 2026-09-28：指數分時的 s 是「成交金額（百萬元）」不是張數（跟 FinMind 每 5 秒成交統計逐筆對過，見 pipeline/sources/mis.py），
       以前量軸寫「萬張」、游標寫「該分量 N 張」都是錯的單位。指數改印成交值（億／萬元），台指期照舊口數。*/
    const sTxt = (n) => (x.id === 'FUT' ? f.i(n) + ' 口' : f.yi(n * 1e6));
    const A = window.App;
    /* tooltip 的 formatter 與量柱的顏色 callback 是**留在圖上一直被呼叫**的，
       如果它們直接抓上面那幾個 const，`patchLine()` 換完資料之後它們讀到的還是舊陣列。
       所以統一從這個掛在容器上的盒子裡讀 —— 補資料時就地換掉它的欄位就好。*/
    const H = el._m3line = { cats, price, vol, d, night: !!d.night, prev: d.prev, s0, dec: axisDec(hi - lo) };
    A.chart(el, {
      /* ★ 2026-09-24（Andy：「走勢圖／K 線左右擴充到適當範圍，不要留太多空白」）：
         左 14→2、右 58→4（containLabel 會自己把右側價格軸的字算進來，不必再多留 54px）。*/
      grid: [{ left: 2, right: 4, top: 10, bottom: 70, containLabel: true },
        { left: 2, right: 4, height: 44, bottom: 22, containLabel: true }],
      tooltip: Object.assign({}, A.tip, {
        trigger: 'axis', axisPointer: { type: 'cross' },
        formatter: (ps) => {
          let i = ps[0].dataIndex;
          // ★ 一律從 H 讀（不是上面那幾個 const）—— 推送補完資料之後，
          //   閉包抓到的舊陣列會讓 tooltip 顯示上一輪的值。
          /* ★ 2026-10-04 修：非交易時段開頁是用資料湖 15 分 K 種的走勢（d.sparse，每 15 分鐘才一個點），
             游標停在兩點之間會寫「尚未成交」—— 那幾分鐘明明有成交，是假話（週日驗收 FUT 游標讀不到價格就是這個）。
             改成：最後一點之前一律貼回左邊最近的那一點（時間也寫那一點的）；最後一點之後才是真的「尚未成交」。
             量：湖裡的 15 分 K 種子沒有每分鐘量（s 是 0 佔位），印「—」而不是假的「0 口」。*/
          const sparse = !!(H.d && H.d.sparse);
          if (H.price[i] == null && sparse) {
            let j = i; while (j >= 0 && H.price[j] == null) j--;
            let k = i; while (k < H.price.length && H.price[k] == null) k++;
            if (j >= 0 && k < H.price.length) i = j;          // 夾在兩點之間 → 貼回左邊那一點
          }
          if (H.price[i] == null) return cats[i] + '<br>尚未成交';
          const c = H.price[i], ch = d.prev ? c - d.prev : null;
          return `<b>${cats[i]}</b><br>指數 <b class="mono">${f.n(c, dp)}</b>`
            + (ch != null ? ` <span style="color:${ch >= 0 ? '#ff4d6d' : '#2ee59d'}">${(ch > 0 ? '+' : '') + f.n(ch, dp)}（${f.pct(ch / d.prev * 100, 2)}）</span>` : '')
            + (() => { const vv = H.vol[i]; const n = sparse ? NaN : +(vv && typeof vv === 'object' ? vv.value : vv);
                // 量柱有時是 { value, itemStyle } 物件（上色用），直接丟進 f.lot 會印「非數值」（Andy 09-25 截圖）
                return `<br>該分${x.id === 'FUT' ? '量' : '成交值'} ${Number.isFinite(n) ? sTxt(n) : '—'}`; })();
        },
      }),
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      xAxis: [
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 0, boundaryGap: false,
          axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } }),
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 1, boundaryGap: false,
          // 台指期的盤比較長（08:45–13:45），每半小時一個刻度會擠成一團
          // alignMinLabel：最左那個「09:00」貼齊左緣往右長，不要置中在軸端而一半跑出卡片（_preview 抓到的溢出）
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, margin: 8, alignMinLabel: 'left', alignMaxLabel: 'right',
            interval: (i) => (s0 + i) % (cats.length > 280 ? 60 : 30) === 0 },
          axisTick: { show: false }, splitLine: { show: false } }),
      ],
      yAxis: [
        // 小數位數看振幅決定：櫃買一天的區間不到 10 點，寫成整數會變成「396 396 395 395」
        Object.assign({}, A.axisStyle, { gridIndex: 0, min: lo, max: hi, position: 'right', splitNumber: 4,
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, showMinLabel: false,
            formatter: (v) => f.n(v, axisDec(hi - lo)) },
          splitLine: { lineStyle: { color: A.CH.grid } } }),
        // 量軸只有 44px 高，放三個刻度一定疊在一起 —— interval 設成最大值等於只留「頂」那一格
        Object.assign({}, A.axisStyle, { gridIndex: 1, position: 'right', splitLine: { show: false },
          min: 0, max: vmax, interval: vmax || 1,
          // 沒有量（種子不帶量、vmax 退到 1）就不印量軸刻度 —— 否則會印一個假的「100 萬」還壓到價格軸（2026-10-04）
          axisLabel: { show: vmax > 1, color: A.CH.ink3, fontSize: 9, showMinLabel: false,
            // 台指期算「口」，指數算「張」—— 單位寫錯 Andy 一眼就看得出來
            formatter: (v) => (x.id === 'FUT' ? (v >= 1e4 ? (v / 1e4).toFixed(1) + ' 萬' + unit : f.i(v) + ' ' + unit) : f.yi(v * 1e6)) } }),
      ],
      series: [
        // sparse：資料湖 15 分 K 退回來的點每 15 分鐘才一個，不連起來就只剩一顆顆看不見的點
        { type: 'line', data: price, showSymbol: false, connectNulls: !!d.sparse, xAxisIndex: 0, yAxisIndex: 0,
          lineStyle: { color: col, width: 1.6 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexa(col, .30) }, { offset: 1, color: hexa(col, 0) }]) },
          markLine: { silent: true, symbol: 'none', label: { show: true, position: 'insideEndTop', color: A.CH.ink3, fontSize: 10, formatter: (d.prevLabel || '昨收') + ' ' + f.n(d.prev, dp) },
            lineStyle: { color: A.CH.ink3, type: 'dashed', width: 1 },
            data: d.prev != null ? [{ yAxis: d.prev }] : [] } },
        { type: 'bar', data: vol, xAxisIndex: 1, yAxisIndex: 1, barWidth: '70%',
          itemStyle: { color: (p) => {
            const i = p.dataIndex; const prev = i > 0 ? H.price[i - 1] : d.prev;   // 同上：讀 H
            return (H.price[i] != null && prev != null && H.price[i] >= prev) ? hexa('#ff4d6d', .7) : hexa('#2ee59d', .7);
          } } },
      ],
    }, { notMerge: true });

    /* ---- 呼吸燈：標出「最新的那一點」，而且只在真的還在更新時才呼吸。
       位置不是算出來寫死的，是每次跟 ECharts 要（`convertToPixel`），
       所以展開／收合、縮放視窗、換主題之後都不會飄掉。
       （`patchLine()` 補完資料之後也會呼叫同一支，燈才會跟著最後一根走。） */
    setLinePulse(x, d, L);
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
    // 資料湖種子（盤後先畫的最近交易日）不是「往前走」—— 不記身分，真的分時回來那一次才算第一次看到
    if (d && d.seed) return;
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
    /* ★ 2026-09-26（Andy：「底下成交量不見了」）：成交量這一格**不吃個股頁的開關**。
       根因：`tw.kcfg` 是兩頁共用的，個股頁「指標 ▾」下拉（59792cd 起整列就是開關）只要把「成交量」那列點掉，
       存下去的 `vol:false` 就一路帶到這三張圖 —— 而總覽**沒有任何地方可以把它打開回來**，
       使用者看到的就是「量副圖整個不見」。乾淨的瀏覽器（沒有 tw.kcfg）在每個寬度、每個週期都重現不出來，
       唯一重現得出來的條件就是 `tw.kcfg.vol === false`（驗收段「大盤量副圖0926」照這條路實際點過）。
       Andy 2026-09-25 的要求是「每個週期（1 分～季）都有成交量」，所以這裡一律開量、量均線沒設就用 20；
       量柱樣式（顏色／透明度）也用這裡的預設 —— 個股頁把透明度拉到很低，這裡同樣會「看起來沒有量」。
       只有「來源本身沒給量」（hasVol 判定）才收掉面板，那由 drawK 的 cfgOf 決定，不在這裡。*/
    c.vol = true;
    if (!(c.volma > 0)) c.volma = 20;
    if (c.st && c.st.vol) { c.st = Object.assign({}, c.st); delete c.st.vol; }
    if (!expanded) { c.kd = null; c.macd = null; c.rsi = null; c.boll = null; }
    return c;
  }

  /* ★ 2026-10-05 Andy 10:44 截圖：卡片數字已是即時（加權 49,713），日 K 卻停在資料湖最後一天（10-02）。
     根因：日／週／月三個週期只讀資料湖 index_ohlc.json，盤中的即時報價從來沒接進 K 線。
     做法：把這張卡現在的即時資料（加權／櫃買＝live.js t00／o00 蓋過的分時，台指期＝期交所報價；
     夜盤時 d 就是夜盤那一份）合成一根「今日 K」：開＝今日開盤、高低＝當日高低、收＝現價、量＝累計。
     只在三個條件同時成立時才加：① 資料日期就是台北今天（日盤）或夜盤自己的交易日 ——
     非交易日拿到的會是上一個交易日，自然不加；② 比資料湖最後一天新 —— 資料湖補上同一天之後以湖為準；
     ③ 不是資料湖自己種出來的那一份（lakeDay／lakeHead，那是湖的資料不是即時）。*/
  function liveDayBar(x, d) {
    if (!d || d.last == null || !d.date || d.seed || d.sparse || /資料湖/.test(d.src || '')) return null;
    const ds = String(d.date).replace(/-/g, '');
    if (!/^\d{8}$/.test(ds)) return null;
    if (!d.night && ds !== tpeDay()) return null;
    const ymd = ds.slice(0, 4) + '-' + ds.slice(4, 6) + '-' + ds.slice(6);
    const base = (state.lakeDaily || {})[lakeSym(x)] || [];
    if (!base.length || String(base[base.length - 1][0]) >= ymd) return null;
    const c = +d.last, o = d.open != null ? +d.open : c;
    const h = Math.max(d.high != null ? +d.high : c, o, c), l = Math.min(d.low != null ? +d.low : c, o, c);
    // 量：指數＝成交金額（百萬元→元，跟 index_ohlc 同一把尺）；台指期＝累計口數
    const v = x.id === 'FUT' ? (d.vol != null ? +d.vol : 0) : (d.amt != null ? d.amt * 1e6 : 0);
    return [ymd, o, h, l, c, v || 0];
  }

  function drawK(x, d, el, forceTf, forceSay) {
    if (typeof window.KChart === 'undefined') { el.innerHTML = '<div class="empty">圖表函式庫載入失敗</div>'; return; }
    if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
    /* 2026-09-19（Andy N11「這邊不該出現沒有數據」）：
       櫃買與台指期沒有 1 小時／4 小時的免費來源，以前就直接在卡片上寫一句
       「沒有免費來源」然後留一塊空白 —— 使用者看到的是「這張圖壞了」。
       改成**自動退回日線並在卡片上說明**：畫面上永遠有東西可看，
       同時老實講「這個週期沒來源，改用日線」。
       fallbackTf 只影響這一張卡片，上方的週期選單不動（其他卡片仍照選的走）。*/
    const tfKey = forceTf || state.tf;
    let def = histDef(tfKey);
    let bars, tfName, synthSay = forceSay || '', multi = false;
    /* ★ 2026-09-26：1 小時／4 小時三個指數同一條路（Andy：「這三個到底有沒有統一的來源」）——
       資料湖 index_intraday.json（每天盤後存的證交所分時 1 分 K 合成；加權另有 Yahoo 歷史）接今天的分時。
       湖裡有幾盤就畫幾盤（4 小時選了只累積 3 天就畫 3 根），不再因為「不足 2 根」整張退回日 K；
       卡片上一行短句講累積狀況（accumSay：「櫃買分 K 自 YYYY-MM-DD 起累積（N 天）」）。
       只有「湖裡一根都沒有、今天的分時也拿不到」＝真的什麼都畫不出來時，才退到日 K 並寫明原因。*/
    if (def && def.synth && state.lakeIntra === undefined) {
      loadLakeIntra();
      killK(x.id); el.dataset.kind = ''; el.innerHTML = '<div class="empty">載入中…</div>'; return;
    }
    if (def && def.synth) {
      const lb = ((state.lakeIntra || {})[lakeSym(x)] || {})[def.synth] || [];
      const merged = cleanBars(mergeLake(lb, synthBars(x, def.synth).bars));
      if (merged.length) {
        bars = merged;
        tfName = def.synth === 'H4' ? '240m' : '60m';
        el.dataset.src = lb.length ? 'lake' : 'today';
        if (!synthSay) synthSay = accumSay(x);
      } else {
        synthSay = `${x.short}分 K 還沒有任何一盤，先顯示日 K`;
        def = histDef('D');
      }
    }
    if (def && !bars) {
      const key = (def.lake ? lakeSym(x) : x.id) + '|' + def.id;
      bars = state.hist[key];
      if (!bars) {
        const err = state.histErr[key];
        killK(x.id); el.dataset.kind = '';
        if (!err) { fetchHist(x, def); el.innerHTML = '<div class="empty">載入中…</div>'; return; }
        el.innerHTML = `<div class="empty">${window.App ? window.App.fmt.esc(
          err === 'NOLAKE' ? `${x.name}的歷史日 K 還沒進資料湖 —— 下一輪每日管線跑完（台北 15:30 / 18:30 / 21:30）就會有。`
          : '抓不到歷史 K：' + errZh(err)) : errZh(err)}</div>`;
        return;
      }
      tfName = '1d';
      // ★ 2026-10-05：盤中（與收盤後、資料湖還沒更新前）把今天的即時 OHLC 併成最後一根（見 liveDayBar）
      const tb = def.lake ? liveDayBar(x, d) : null;
      if (tb) {
        let daily = state.lakeDaily[lakeSym(x)].concat([tb]);
        if (def.roll) daily = rollLake(daily, def.roll);
        if (def.group > 1) daily = groupBars(daily, def.group);
        bars = daily;
      }
      el.dataset.todayk = tb ? tb[0] : '';
    } else if (def) el.dataset.todayk = '';
    if (def) {
      const key = (def.lake ? lakeSym(x) : x.id) + '|' + def.id;
      /* 圖上方那行說明。可能同時有三件事要講，所以收成一個陣列再串起來：
         ① 1 小時／4 小時合成不到、已退回日線（或只用今天的分時合成）
         ② 歷史不到 3 年（Andy 2026-09-19「為何這些走勢都沒有過往歷史數據」）
         ③ 夜盤的歷史 K 只有一般交易時段（日盤）那條 */
      const says = [];
      if (synthSay) says.push(synthSay);
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
        /* ★ 2026-10-04 Andy 16:10 截圖：台指期標頭 49,346（夜盤即時）、K 線右側卻是 48,475.00，跟加權收盤
           48,475.74 幾乎一樣，懷疑拿錯序列。查證：那根是 FUT_N（夜盤日 K）10-02 那一盤的收盤 48,475，
           FUT（日盤）是 48,671、加權 48,475.74 —— 三條是各自的資料，數字相近是巧合，序列沒有拿錯。
           真正讓人誤會的是「沒講這條 K 線是哪一條、資料到哪一天」，所以每張卡都標出來。*/
        const src = (state.lakeDaily || {})[lakeSym(x)] || [];
        const lastDay = src.length ? String(src[src.length - 1][0]) : '';
        const which = x.id === 'FUT' ? (isNight(x) && !state.lakeBack[key] ? '台指期夜盤日 K' : '台指期日盤日 K') : x.short + '日 K';
        // ★ 2026-10-06（Andy：「這類資訊一律拿掉」，DECISIONS #329）：只標「是哪一條線」，不再寫「資料至 YYYY-MM-DD（＋今日即時）」
        if (lastDay) says.push(which);
      }
      if (says.length) el.dataset.fallback = says.join('　·　'); else delete el.dataset.fallback;
    } else {
      /* ★ 2026-09-25：15／30 分改吃「資料湖的 15 分 K ＋ 今天的分時」（Andy：「已經有 15 分 K」）。
         以前 15 分只有今天的分時，湖裡加權那 60 天的 15 分 K 只被拿去合成 1H／4H、自己反而看不到。
         現在 15 分＝湖的 15 分 K 接今天（同一個 mergeLake 規則，今天那一盤以證交所分時為準），
         30 分＝同一份 15 分 K 兩根併一根。1／5 分湖裡沒有，照舊只有今天。夜盤接 FUT_N（期交所逐筆，2026-09-26 起）。*/
      const n = +state.tf;
      const today = (d && !d.seed && d.points && d.points.length) ? toBars(d.points, n, volUnit(x)) : [];
      // ★ 2026-09-26：夜盤也接湖（期交所逐筆合成的 FUT_N 15 分 K）；湖裡沒有夜盤時 M15 是空的，照舊只有今晚。
      if ((n === 15 || n === 30) && state.lakeIntra === undefined) loadLakeIntra();
      const m15 = (n === 15 || n === 30) ? (((state.lakeIntra || {})[(d && d.night) ? 'FUT_N' : x.id] || {}).M15 || []) : [];
      // ★ 2026-09-26：門檻 2 → 1，三個指數都接湖（櫃買、台指期的 15 分 K 由證交所分時每天累積）；
      //   只接到自己累積的那幾天時，跟 1H／4H 同一句短句講「自 … 起累積（N 天）」。
      if (m15.length >= 1) {
        bars = mergeLake(n === 30 ? rollMin(m15, 30) : m15, today);
        multi = true; el.dataset.src = 'lake';
        const a = accumSay(x);
        if (a) el.dataset.fallback = el.dataset.fallback ? el.dataset.fallback + '　·　' + a : a;
      } else { bars = today; el.dataset.src = 'today'; }
      tfName = state.tf + 'm';
    }
    /* 至少要有一根才畫得出東西。★ 門檻從 2 根降到 1 根（2026-09-20）：
       夜盤剛開盤只有一根時，以前會整張換成「資料還不夠畫一根 K」——
       但那時候明明已經有一根真的 K 棒了，Lightweight Charts 畫一根沒有問題。
       「資料少」該由圖自己表現，不該用一塊文字把圖換掉。 */
    /* ★ 2026-09-25：交給圖表之前一律清洗（見 cleanBars 的註解）。不管 K 棒從哪條路來 ——
       資料湖、Yahoo、今天的分時、localStorage 快取 —— 走到這裡都保證時間嚴格遞增、不重複、OHLC 都是有限數。*/
    bars = cleanBars(bars);
    if (!bars || bars.length < 1) {
      killK(x.id);
      el.innerHTML = `<div class="empty">${def ? '這個週期的資料不足' : '今天還沒有任何分鐘資料'}</div>`;
      el.dataset.kind = ''; return;
    }
    /* ★ 2026-09-28：量只畫真實的（見上方「成交量：只畫真實的量」）。4 小時一盤一根時，分 K 沒量的盤補上日線實際總量
       （真實值）；其他一律照實。日線總量還沒載到時先照畫，載到會自己重畫。*/
    let est = new Map();
    if (!(def && def.lake)) {
      if (!state.dvol) loadDailyVol();
      est = fillDayTotal(x, bars, !!(d && d.night));
    }
    el.dataset.est = '0';
    const expanded = state.big === x.id;
    const showN = (def || multi) ? (expanded ? 160 : 90) : bars.length;
    // 看得到的那一段不到九成有量 → 量面板收掉、圖上方寫「此週期無成交量資料」（原因在滑鼠提示）
    const vr = volRatio(bars, showN);
    const vol = vr >= VOL_SHOW;
    el.dataset.volr = vr.toFixed(3);
    el.dataset.novol = vol ? '' : '1';
    el.dataset.novolWhy = vol ? '' : noVolWhy(x, tfKey);
    if (!vol) {
      const t = '此週期無成交量資料';
      el.dataset.fallback = el.dataset.fallback ? el.dataset.fallback + '　·　' + t : t;
    }
    // key 含日盤／夜盤：切 session 時資料整組換掉，不能沿用同一個圖表就地改
    // ★ 2026-09-24：key 多帶 tfName（1 小時合成不到會退回日，同一個選單值畫的是不同週期）與「有沒有量」
    const key = x.id + '|' + String(tfKey) + '|' + tfName + '|' + (vol ? 'v' : 'nv') + '|' + (expanded ? 'big' : 'small')
      + '|' + (d && d.night ? 'n' : 'd') + (multi ? '|multi' : '');
    const cfgOf = () => { const c = loadCfg(expanded); if (!vol) c.vol = false; return c; };
    const live0 = state.kcharts[x.id];
    /* 同一張卡、同一個週期、同樣大小 → 就地換資料。
       盤中 10 秒重畫一次，如果每次都 destroy 再 new，使用者的縮放與位置會一直被彈回最右邊，
       等於不能往左看早盤（Andy 2026-09-15 要的是「自動更新」，不是「自動跳回去」）。 */
    if (live0 && live0._m3key === key && el.dataset.kind === 'k') {
      live0.setBars(bars, tfName, true);
      live0.applyIndicators(cfgOf());
      live0._m3est = est; decorVol(x, live0);
      return;
    }
    killK(x.id);
    el.innerHTML = ''; el.dataset.kind = 'k';
    // mini：不要面板標題與浮水印（那兩個的 CSS 只掛在個股頁的 #lwc 底下，放這裡會掉到卡片外面）
    // volRatio：量副圖佔圖高的比例，三張共用一個（使用者拖過就用他拖的，見 armVolSync）
    const k = new window.KChart(el, { tf: tfName, mini: true, compact: !expanded, volRatio: loadVolR() || undefined });
    k._m3key = key;
    state.kcharts[x.id] = k;
    k.setBars(bars, tfName);
    const cfg = cfgOf();
    k.applyIndicators(cfg);
    k._m3est = est; decorVol(x, k);
    armVolSync(x, el);
    const f = F();
    const dp = x.id === 'FUT' ? 0 : 2;
    k.setBarSpacing(expanded ? (cfg.bar || 9) : 5);
    // 當天的圖把整個交易日塞滿；歷史的圖看最近一段就好，不然幾百根擠成一片
    // 多日的 15／30 分（湖＋今天）跟歷史週期一樣只看最近一段；只有今天的分 K 才整盤攤開
    k.fitLast((def || multi) ? (expanded ? 160 : 90) : bars.length + 2);
    if (!def && d.prev != null) k.setPriceLines([{ price: d.prev,
      title: (d.prevLabel || '昨收') + ' ' + (f ? f.n(d.prev, dp) : d.prev), color: '#8ea0c4' }]);
    kTip(x, k, el);
  }

  /* ★ 2026-09-24（Andy：「游標移到 K 線要顯示開高低收＋成交量」）。
     總覽的三張是 mini 版 KChart —— 個股頁那個 OHLC 看板（#lwc .ohlcbox）只掛在整頁大圖上，
     所以這裡自己訂閱十字線，在圖的左上角放一塊小看板。每一個週期（分 K、1 小時、日週月季）都走同一支。
     量是 0 的來源（Yahoo 指數）寫「—」，不寫「0 張」。*/
  function kTip(x, k, el) {
    if (!k || !k.chart || !k.chart.subscribeCrosshairMove) return;
    let box = el.querySelector('.m3-ktip');
    if (!box) { box = document.createElement('div'); box.className = 'm3-ktip'; box.hidden = true; el.appendChild(box); }
    if (!el._ktipLeave) {                 // 容器跨圖表活著，只掛一次
      el._ktipLeave = true;
      el.addEventListener('mouseleave', () => { const bb = el.querySelector('.m3-ktip'); if (bb) bb.hidden = true; });
    }
    const f = F(); const dp = x.id === 'FUT' ? 0 : 2; const unit = x.id === 'FUT' ? '口' : '元';
    k.chart.subscribeCrosshairMove((p) => {
      try {
        const b = p && p.time != null && p.seriesData ? p.seriesData.get(k.candle) : null;
        /* 沒有 K 棒時：只有「滑鼠還在圖上、但停在空白處」才收起來。
           盤中每 10 秒換資料、draw() 補發的 resize 也會觸發一次沒有座標的十字線事件 ——
           那種不算「滑鼠離開」，收掉的話看板會在使用者眼前一閃就不見（驗收抓到的）。
           真的離開圖表由下面的 mouseleave 負責。*/
        if (!b || b.open == null) { if (p && p.point && p.sourceEvent) box.hidden = true; return; }
        /* 日／週／月／季的時間是 'YYYY-MM-DD' 字串，Lightweight Charts 在十字線事件裡會把它換成
           {year, month, day} 物件 —— 直接拿去比對或格式化就對不到（看板不出現）。先正規化回字串。*/
        const pt = (p.time && typeof p.time === 'object' && p.time.year)
          ? `${p.time.year}-${String(p.time.month).padStart(2, '0')}-${String(p.time.day).padStart(2, '0')}` : p.time;
        const row = (k.data || []).find(r => r.time === pt) || {};
        const t = typeof pt === 'string' ? pt : (window.KUtil && window.KUtil.fmtTime ? window.KUtil.fmtTime(pt, k.tf) : '');
        const up = b.close >= b.open;
        /* ★ 2026-09-28：量只有真實值（不再估）。指數＝成交值（億／萬元），台指期＝口；沒有量的那根寫「—」。
           4 小時那根的量是當天日線實際總量（見 fillDayTotal），滑鼠提示講一句。*/
        const ek = k._m3est ? k._m3est.get(String(pt)) : null;
        const lab = isMoney(x) ? '值' : '量';
        box.innerHTML = `${t ? `<b>${f.esc(String(t))}</b>` : ''}`
          + `<span>開 <i>${f.n(b.open, dp)}</i></span><span>高 <i class="up">${f.n(b.high, dp)}</i></span>`
          + `<span>低 <i class="down">${f.n(b.low, dp)}</i></span><span>收 <i class="${up ? 'up' : 'down'}">${f.n(b.close, dp)}</i></span>`
          + `<span${ek === 'day' ? ' title="4 小時一盤一根：量＝當天日線的實際成交總量"' : ''}>量${isMoney(x) ? '（成交' + lab + '）' : ''} <i>${volTxt(x, row.volume)}</i></span>`;
        box.hidden = false;
        box.dataset.unit = unit;
        box.dataset.est = ek || '';
      } catch (e) { box.hidden = true; }
    });
  }

  // ---------------------------------------------------------------- 對外
  // 分頁切回來就補抓一次，不用等下一個 10 秒
  /* ★ 順便處理呼吸燈：分頁切到背景時 `refresh()` 直接 return（不打端點），
     燈還在呼吸就是在說謊 —— 所以**切走的那一刻**就要重算一次，不能等下一輪。
     （全站的 visibilitychange 慣例寫在 app.js，但那個檔這一輪不歸我改，所以自己掛一個。）*/
  document.addEventListener('visibilitychange', () => {
    pulseTick();
    // 切到背景就把夜盤那條連線收掉（不佔連線也不耗 Worker 的 CPU 額度），
    // 切回來再開一條 —— 重連的第一筆是完整快照，所以背景那段時間的值補得回來。
    syncFutStream();
    if (!document.hidden) refresh();
  });
  // 視窗一縮，ECharts 的座標就換了一組 —— 燈的位置要跟著重新跟它要一次
  window.addEventListener('resize', () => {
    clearTimeout(state._rzT);
    state._rzT = setTimeout(paintPulses, 120);
  });
  // 跨越開盤／收盤時要換節奏（10 秒 ↔ 5 分鐘），每分鐘檢查一次就夠。
  // 不在總覽頁時 `schedule()` 不會跑，所以夜盤那條推送連線要在這裡另外收掉。
  setInterval(() => {
    if (document.getElementById('m3')) schedule();
    else syncFutStream();
  }, 60 * 1000);

  window.Market3 = {
    mount, refresh, draw, schedule, placeKpi,
    get state() { return state; },
    toBars,                                  // 驗收用
    get session() { return state.futSession; },          // 驗收用：時鐘現在在哪一段（決定要不要去抓夜盤）
    get shown() { return nightHas() ? 'night' : 'day'; },  // 驗收用：台指期卡片現在「畫的」是哪一段
    /** 驗收用：把時鐘釘在某一段（'day'／'night'；null＝跟著台北時間），並立刻重抓重畫。
     *  使用者沒有入口能碰到它 —— 切換鈕 2026-09-24 已拿掉，平常一律由台北時間決定。 */
    forceClock(v) { state.clock = (v === 'day' || v === 'night') ? v : null;
      state.futSession = pickSession(); if (state.futSession !== 'night') { state.futNight = null; state.futChart = null; }
      draw();
      // refresh() 在上一輪還沒回來時會直接跳過（busy）—— 等它空出來再跑，時鐘換段才一定會真的去抓
      return new Promise((ok) => { const go = () => (state.busy ? setTimeout(go, 150) : refresh(true).then(ok, ok)); go(); }); },
    synthBars, sessKey,                          // 驗收用：1 小時／4 小時的合成規則
    fillDayTotal, rollMin, volRatio,             // 驗收用：量（2026-09-28 起只畫真實量，不估）
    /** 驗收用：三張圖量副圖各佔圖高多少、存的比例、連動發生過幾次。 */
    volPanes() {
      const o = { saved: loadVolR(), n: state.volSyncN || 0 };
      IDX.forEach(y => { o[y.id] = volShare(state.kcharts[y.id]); });
      return o;
    },
    applyVolR(r) { applyVolR(clampR(r)); },
    /** 驗收用：這張卡現在畫的 K 棒裡，量 > 0 的根數、估算的根數、第一根與最後一根的量。 */
    volInfo(id) {
      const k = state.kcharts[id]; if (!k || !k.data) return null;
      const est = k._m3est || new Map();
      return { n: k.data.length, pos: k.data.filter(r => r.volume > 0).length, tf: k.tf,
               est: [...est.values()].filter(v => v !== 'day').length, day: [...est.values()].filter(v => v === 'day').length,
               pane: !!(k.cfg && k.cfg.vol), src: (document.getElementById('m3c-' + id) || {}).dataset ? document.getElementById('m3c-' + id).dataset.src || '' : '' };
    },
    mergeLake, cleanBars,                        // 驗收用：1H／4H 湖資料接今天分時、畫之前的清洗（2026-09-25）
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
    get futVia() { return state.futVia || ''; },  // 驗收用：最後一次台指期是走 'deno' 還是退回 'worker'（#286）
    get futDenoWhy() { return state.futDenoWhy || ''; },  // 驗收用：最後一次 Deno 為什麼沒用上（空＝用上了或沒試）
    /* 驗收用：夜盤現在走推送還是輪詢、收了幾筆、退回過幾次、為什麼退回。
       `mode` 就是畫面上那個「推送／輪詢」小標籤讀的同一個值 —— 驗的是同一件事。*/
    get futStream() {
      return { mode: state.fsMode, pushes: state.fsPushes, fails: state.fsFails,
               everOk: state.fsEverOk, gaveUp: state.fsGaveUp, key: state.fsKey,
               at: state.fsAt, why: state.fsWhy };
    },
    parseFutChart, tickMin,                      // 驗收用：時間欄位的坑（046000）有沒有處理對
    futSymbol,                               // 驗收用：/fut 掛掉時推算出來的近月合約代號
    isIntraday,
    /** 驗收用：2026-10-04 起下拉只剩日／週／月，分 K 與 1H／4H 的合成程式碼還在（走勢圖的點、舊驗收），
     *  舊驗收改走這裡把週期釘過去 —— 使用者沒有入口碰得到，也不寫進 localStorage。 */
    forceTf(v) { state.tf = String(v); draw(); },
    lakeDay(id) { return lakeDay(IDX.find(x => x.id === id)); },
    /** 驗收用：這張卡 K 線最後一根（日期、OHLC、量）。*/
    lastK(id) { const k = state.kcharts[id]; const r = k && k.data && k.data[k.data.length - 1];
      return r ? { time: typeof r.time === 'object' ? `${r.time.year}-${String(r.time.month).padStart(2, '0')}-${String(r.time.day).padStart(2, '0')}` : r.time,
        open: r.open, high: r.high, low: r.low, close: r.close, volume: r.volume, n: k.data.length,
        setData: k.stats ? k.stats.setData : null } : null; },   // 驗收用：盤後退回資料湖那一天（2026-10-04）
  };
})();
