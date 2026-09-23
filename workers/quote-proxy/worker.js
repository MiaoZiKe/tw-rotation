/* quote-proxy — 台股即時報價的 CORS 代理（Cloudflare Worker）
 *
 * 為什麼需要它
 * ------------
 * 網站是 GitHub Pages 上的靜態頁，盤中要每分鐘更新價格只能由瀏覽器自己去抓，
 * 但證交所那支即時報價沒有給 CORS 標頭。2026-09-14 15:08 從
 * https://miaozike.github.io 實測：
 *     fetch(mis.twse…)           → TypeError: Failed to fetch
 *     fetch(mis.twse…, no-cors)  → 通（連得到，只是讀不到）
 * 連得到卻讀不到就是 CORS 擋的。這支 Worker 幫忙轉一手並補上標頭。
 *
 * 它刻意做的限制（不要拿掉）
 * --------------------------
 * 1. **只轉一個端點**：mis.twse.com.tw 的 getStockInfo.jsp，不是通用代理。
 *    開放式代理會被拿去當跳板，而且會連累這個 Worker 的網域。
 * 2. **ex_ch 嚴格檢查格式**：只允許 tse_/otc_ 開頭、.tw 結尾、最多 140 個代號。
 *    不符合就直接 400，不往上游送。
 * 3. **只允許自己的網站呼叫**：Origin 不在白名單就不給 CORS 標頭。
 * 4. **邊緣快取 10 秒**：同一分鐘內多個分頁、多次手動更新只會真的打上游一次。
 *    盤中一分鐘更新一次，10 秒快取不會讓數字變舊，卻能擋掉大部分重複請求。
 *
 * 部署方式看 workers/README.md（不用裝任何東西，在 Cloudflare 網頁上貼上就好）。
 */

const UPSTREAM = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp';

/* 台指期（含**夜盤**）報價：期交所的行情看板 API。
   Andy 2026-09-18 圖一「台指期需要顯示夜盤」。
   - 證交所那支 futures_chart.txt 只有日盤，夜盤查不到，所以另外走期交所。
   - 期交所的使用條款沒有爬蟲條款、robots 也沒限制，比證交所寬（見 DECISIONS）。
   - 上游只吃 POST，而且要帶 Referer，不帶會被擋（跟 mis.twse 同一個脾氣）。
   - 瀏覽器這邊用 GET /fut?session=day|night，payload 由 Worker 寫死 ——
     不讓前端傳任意 body，避免變成通用代理。 */
const TAIFEX_QUOTE = 'https://mis.taifex.com.tw/futures/api/getQuoteList';
const TAIFEX_BODY = (night) => JSON.stringify({
  MarketType: night ? '1' : '0', SymbolType: 'F', KindID: '1', CID: 'TXF',
  ExpireMonth: '', RowSize: '全部', PageNo: '', SortColumn: '', AscDesc: 'A',
});

/* 台指期的**分時序列**（日盤與夜盤都有）。2026-09-20 才確認這支端點可以用。
   ---------------------------------------------------------------------
   2026-09-19 第一次探測送了 `{"SymbolID": ["TXFJ6-F"]}` 被回 400，當時的結論寫成
   「夜盤沒有現成的分時序列」；但那個 400 的訊息其實是
   `Cannot deserialize instance of java.lang.String out of START_ARRAY`
   —— 它要的是**字串**。2026-09-20 用字串重打，夜盤回 200、822 筆，
   日盤回 200、300 筆（08:46~13:45，跟證交所 futures_chart.txt 的筆數與區間完全對得上，
   等於交叉驗證過口徑）。fixture：docs/fixtures/taifex_night_probe.json。

   回應形狀：RtData.Field = ["T","O","H","L","C","V"]、RtData.Ticks = [[...], ...]，
   另外 RtData.Quote 直接附開高低收與累計量 —— 一次請求就拿得到走勢、K 線與上排數字。

   ★ `symbol` 鎖成「英數 3~8 碼 + -F/-M」的合約代號形狀。
   理由跟 CHART_FILES 的白名單一樣（DECISIONS #108）：這支 Worker 只准代理
   我們自己要的東西，不可以變成「誰都能拿它去打期交所任意端點」的開放式代理。 */
const TAIFEX_CHART = 'https://mis.taifex.com.tw/futures/api/getChartData1M';
const FUT_SYMBOL = /^[A-Z0-9]{3,8}-[FM]$/;

// 大盤／櫃買／台指期的「當日分時」檔。就是證交所基本市況報導那三張走勢圖的資料來源，
// 每一筆是 {t: epoch 毫秒, ts: "090100", c: 指數, s: 該分鐘成交量}，09:01 起每分鐘一筆。
// 同樣鎖死成白名單 —— 只放行這幾個檔名，不接受任意路徑。
const CHART_FILES = {
  TSE: 'https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt',   // 加權
  OTC: 'https://mis.twse.com.tw/stock/data/mis_ohlc_OTC.txt',   // 櫃買
  FUT: 'https://mis.twse.com.tw/stock/data/futures_chart.txt',  // 台指期
};

// 允許呼叫這支 Worker 的網站。要多一個網域就加在這裡。
const ALLOW_ORIGINS = [
  'https://miaozike.github.io',
  'http://127.0.0.1:8766',   // scripts/_preview.py
  'http://127.0.0.1:8767',   // scripts/_uitest.py
  'http://localhost:8766',
  'http://localhost:8767',
];

// Yahoo Finance 的當日分 K。用途是「補早盤」：
// mis 只給即時的當下一筆，不給今天稍早的序列（個股沒有分時檔，只有大盤有）。
// 2026-09-15 10:22 實測：Yahoo 有量、但**延遲 20 分鐘**（它給到 10:02），
// 所以前端的做法是 Yahoo 補早盤 + mis 補最近這 20 分鐘的尾巴。
const YAHOO = 'https://query1.finance.yahoo.com/v8/finance/chart/';
// 只放行台股代號與加權指數。
// 註：櫃買的 ^TWOII 在 Yahoo 已經壞掉（2026-09-15 實測最後一筆停在 2026-07-17、
// regularMarketPrice 給 269.45 而實際是 395），所以刻意不放行 —— 寧可畫面上說沒有，也不要畫錯的線。
const Y_SYMBOL = /^(\^TWII|[0-9]{4,6}[A-Z]?\.(TW|TWO))$/;
const Y_INTERVAL = new Set(['1m', '2m', '5m', '15m', '30m', '60m', '1d', '1wk', '1mo']);
const Y_RANGE = new Set(['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max']);

const EX_CH = /^(tse|otc)_[A-Za-z0-9]{2,8}\.tw$/;
const MAX_TOKENS = 140;
// 報價 3 秒、分時檔 10 秒。
// 3 秒是因為個股頁會每 5 秒問一次（mis 自己就是每 5 秒更新一次，回應裡的 userDelay=5000）；
// 快取如果比輪詢還長，第二個分頁就會一直拿到同一筆，5 秒 K 會長不出來。
const CACHE_QUOTE = 3;
const CACHE_CHART = 10;

/* ---------------------------------------------------------------- /stream（SSE 推送）
 *
 * 為什麼要有這條（2026-09-23）
 * ----------------------------
 * 原本的做法是「瀏覽器每分鐘打一次 /quote」。一分鐘一次對看盤來說太鈍，
 * 但把瀏覽器的輪詢直接調快到 5 秒，就變成**每個分頁各自去敲 mis 一次** ——
 * 開三個分頁就是三倍流量，而且 mis 不是我們家的端點。
 * 改成 SSE（Server-Sent Events，伺服器推送）之後：
 *   · 高頻輪詢只發生在 Worker 這一側（伺服器端），瀏覽器只維持一條連線
 *   · 同一組代號的多個瀏覽器共用**同一份上游結果**（走邊緣快取，見 misText）
 *   · 只有「值真的變了」才往下推，沒變就一個 byte 都不送
 *
 * ★ 為什麼一條連線只活 4 分鐘就自己收掉（STREAM_MAX_MS）
 * Cloudflare Workers **免費方案每次調用只有 10ms CPU 時間**（等待 fetch 不算）。
 * 一條長連線的 CPU 是一路累加的，連越久越容易被判超時砍掉。
 * 所以刻意把單條連線壓短、到時間就送 bye 讓前端立刻重連 ——
 * 重連會拿到一份完整快照，畫面不會有缺口。
 * 這也是為什麼**前端一定要保留退回輪詢的路**：這條連線本來就可能被平台砍掉。
 *
 * ★ 為什麼 Worker 這一側挑 5 秒
 * mis 自己的回應裡就寫著 `userDelay: 5000` —— 它每 5 秒才換一次快照。
 * 打得比 5 秒更密只會拿到一模一樣的東西，純粹是浪費別人家的頻寬。
 * 所以 5 秒是「上游真的會變的最快速度」，不是我們隨便挑的數字。
 * POLL_MIN_MS 是硬下限，之後有人想調快也擋在這裡。
 */
const STREAM_MAX_MS = 4 * 60 * 1000;   // 一條連線最多活 4 分鐘（見上面的 CPU 說明）
const POLL_TRADE_MS = 5000;            // 盤中：5 秒（＝ mis 的 userDelay）
const POLL_EDGE_MS = 30000;            // 盤前／盤後緩衝：30 秒（值幾乎不動，降頻）
const POLL_MIN_MS = 3000;              // 節流硬下限，不准再調快
const SSE_RETRY_MS = 3000;             // 告訴瀏覽器斷線後隔多久自己重連

/* ---------------------------------------------------------------- /futstream（台指期夜盤的 SSE 推送）
 *
 * Andy 2026-09-23：「夜盤要即時推送」。
 * 現貨那條 `/stream` 只服務加權／櫃買／個股（mis.twse），台指期夜盤走的是期交所的
 * `/fut` 與 `/futchart`，在這之前一直是**瀏覽器每 60 秒輪詢一次**。
 *
 * ★ 為什麼另開一條，而不是併進 /stream
 * ------------------------------------
 * 兩邊**沒有一樣東西是共用的**：上游不同（mis vs 期交所）、方法不同（GET vs POST）、
 * 時段不同（現貨 09:00–13:35 vs 夜盤 15:00–翌日 05:00）、節奏不同、去重的切法不同、
 * 連讀它的人都不同（site/live.js vs site/market3.js）。
 * 併進去就等於要在同一條連線、同一個迴圈裡同時養兩套時鐘 ——
 * 而夜盤時段**現貨本來就該停**，那會逼 `/stream` 在夜間繼續活著，
 * 正好踩到「不准影響現貨那條 SSE 的行為」這條紅線。
 * 分開之後，現貨那條除了 features 清單多一個字串以外**一行都沒動**；
 * 兩邊各自斷線、各自退回輪詢，一邊壞掉不會連累另一邊（DECISIONS #255 教訓 2）。
 * 代價是夜盤時段每個分頁多一條連線 —— 只在夜盤開，可以接受。
 *
 * ★★ 為什麼這裡**不能**用邊緣快取共用上游（DECISIONS #255 ③）
 * -----------------------------------------------------------
 * 期交所那兩支是 **POST**。`cf: { cacheTtl, cacheEverything: true }` **只對 GET 有效**，
 * 帶在 POST 的子請求上會讓它出錯、Cloudflare 對外回 **520** ——
 * 那就是 2026-09-23 那天 Andy 三次看到「夜盤沒有數值」真正的斷點。
 * 所以共用上游改用**模組作用域（isolate 層）的記憶體**，見 `futMemoFetch()`，
 * 那裡也寫清楚了它保證什麼、不保證什麼。
 *
 * ★★ 輪詢間隔是怎麼訂的（不是隨便挑的數字）
 * -----------------------------------------
 * 現貨那邊有 `userDelay: 5000` 可以照抄，期交所**沒有這個欄位**，所以去 fixture 找證據：
 * `docs/fixtures/taifex_night_probe.json` 的 `getChartData1M` 回應裡，
 * `Ticks` 是 **1 分鐘一筆**（"150100" / "150200" / "150300" …）。於是：
 *
 *   · `/futchart`（分時序列，實測 34KB）→ **60 秒**一次。
 *     一分鐘一根，問得比 60 秒密**在物理上不可能拿到新的一根**，
 *     只會把 34KB 重抓一遍。這是 fixture 直接證明的，不是推測。
 *   · `/fut`（報價快照，實測 4.4KB）→ **10 秒**一次。
 *     同一份 fixture 裡，相隔 6 秒的兩次探測成交價從 48009 變成 48013、
 *     累計量 22616 變成 22622 —— 報價本身是秒級在動的，所以這支值得問得比較密。
 *     10 秒不是新挑的數字：`site/market3.js` 的日盤那三張圖本來就是 10 秒一輪
 *     （`MS_LIVE`），夜盤用同一個節奏，畫面各處的「即時」才是同一個意思。
 *     它比現在的 60 秒快 6 倍，而對期交所的負擔是 4.4KB／10 秒／isolate
 *     ≈ 1.6MB 一小時 —— 大約等於一個人開著期交所行情看板不關。
 *   · `FUT_POLL_MIN_MS` 是硬下限，之後有人想調快也擋在這裡。
 */
const FUT_STREAM_MAX_MS = 4 * 60 * 1000;   // 跟現貨一樣 4 分鐘輪替（免費方案 10ms CPU 會累加）
const FUT_POLL_QUOTE_MS = 10000;           // /fut：10 秒（見上面）
const FUT_POLL_CHART_MS = 60000;           // /futchart：60 秒（Ticks 一分鐘一根，快也沒用）
const FUT_POLL_MIN_MS = 5000;              // 節流硬下限，不准再調快

function cors(origin) {
  const h = {
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
  if (origin && ALLOW_ORIGINS.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function json(body, status, origin, extra) {
  return new Response(JSON.stringify(body), {
    status,
    headers: Object.assign(
      { 'content-type': 'application/json; charset=utf-8' },
      cors(origin), extra || {}),
  });
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin') || '';
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    if (request.method !== 'GET') {
      return json({ error: 'method not allowed' }, 405, origin);
    }
    if (url.pathname === '/' || url.pathname === '/health') {
      // features 是給前端與除錯用的「這支 Worker 會什麼」清單。
      // 有 'stream' 才代表已經部署到支援 SSE 的版本；舊版不會有這個欄位，
      // 前端看得出來就不會傻傻地一直重試（但它本來也有退回輪詢的路）。
      /* ★ `session` 只講**現貨盤**（09:00–13:35），因為它唯一的用途是決定
         `/stream` 要用多快的節奏去問 mis 的現貨報價。夜盤（期交所）走的是另一條
         `/futstream`，它看的是下面那個 `futSession`，所以夜盤時 `session: "closed"`
         是對的、而且對夜盤那張卡沒有任何影響 —— 2026-09-23 查夜盤空白時
         這個欄位被當成嫌犯查過一輪，寫在這裡讓下一個人不用再查一次。
         不過「closed」看起來像整台 Worker 收攤了，所以另外補一個 `futSession`
         把期交所夜盤的狀態講出來，除錯時一眼就分得開這兩件事。
         ⚠ `futSession` 從 2026-09-23 起**不再只是給人看的** —— `/futstream`
         用它決定要不要開迴圈，改它會真的改到行為。*/
      return json({ ok: true, service: 'tw-rotation quote-proxy', upstream: 'mis.twse.com.tw',
                    features: ['quote', 'chart', 'y', 'fut', 'futchart', 'stream', 'futstream'],
                    session: sessionNow(), futSession: futSessionNow() }, 200, origin);
    }
    if (url.pathname !== '/quote' && url.pathname !== '/chart' && url.pathname !== '/y'
        && url.pathname !== '/fut' && url.pathname !== '/futchart'
        && url.pathname !== '/stream' && url.pathname !== '/futstream') {
      return json({ error: 'not found' }, 404, origin);
    }
    if (origin && !ALLOW_ORIGINS.includes(origin)) {
      // 不給 CORS 標頭，瀏覽器那邊自然讀不到；這裡也直接講清楚原因方便除錯
      return json({ error: 'origin not allowed', origin }, 403, '');
    }

    // ---- /stream：SSE 推送即時報價（取代「瀏覽器每分鐘輪詢」）
    if (url.pathname === '/stream') {
      const ids = parseTokens(url.searchParams.get('ids') || url.searchParams.get('ex_ch') || '');
      if (ids.error) return json(ids.error, 400, origin);
      return openStream(ids.tokens, origin, request, ctx);
    }

    // ---- /futstream：台指期夜盤的 SSE 推送（取代「瀏覽器每 60 秒輪詢 /fut」）
    //      symbol 是近月合約代號，前端自己算得出來（site/market3.js 的 futSymbol()），
    //      所以**不給也照樣會推報價**，只是沒有分時序列可推。
    if (url.pathname === '/futstream') {
      const want = (url.searchParams.get('session') || 'night') === 'day' ? 'day' : 'night';
      const raw = (url.searchParams.get('symbol') || '').toUpperCase();
      // 格式不對就當成沒給（不 400）—— 夜盤那張卡的底線是「報價還在」，
      // 不該因為代號拼錯就連報價都收不到。
      const sym = FUT_SYMBOL.test(raw) ? raw : '';
      return openFutStream(want, sym, origin, request, ctx);
    }

    // ---- /fut：台指期報價（session=day|night）。夜盤是 MarketType=1。
    if (url.pathname === '/fut') {
      const night = (url.searchParams.get('session') || 'day') === 'night';
      const upstream = futQuoteRequest(night);
      try {
        /* ★ 2026-09-23：這裡原本帶 cf: { cacheTtl, cacheEverything: true }。
           **那組選項只對 GET 有效** —— 這是 POST，POST 的回應本來就不可快取，
           帶著它送出去會讓子請求出錯，Cloudflare 對外就回 520
           （Andy 看到的「代理回 HTTP 520」）。拿掉，改用下面的 fetchRetry 擋瞬斷。
           要節流的話該做在「同一份上游結果給多條連線共用」那一層（/stream 已經有），
           不是在這裡硬掛一個對 POST 無效的選項。 */
        const r = await fetchRetry(upstream);
        const txt = await r.text();
        return new Response(txt, { status: r.status,
          headers: { 'Content-Type': 'application/json; charset=utf-8',
                     'Cache-Control': `public, max-age=${CACHE_QUOTE}`, ...cors(origin) } });
      } catch (e) {
        return json({ error: 'upstream failed', detail: String(e) }, 502, origin);
      }
    }

    // ---- /futchart：台指期的分時序列（日盤與夜盤都走這裡）
    //      symbol 例：TXFJ6-F（日盤近月）／TXFJ6-M（夜盤近月）。前端從 /fut 的報價清單撈近月，
    //      所以月份碼不用寫死在任何一邊（每個月都在換）。
    if (url.pathname === '/futchart') {
      const sym = (url.searchParams.get('symbol') || '').toUpperCase();
      if (!FUT_SYMBOL.test(sym)) return json({ error: 'bad symbol', got: sym }, 400, origin);
      const upstream = futChartRequest(sym);
      try {
        const r = await fetchRetry(upstream);   // 同上：POST 不可帶 cf 快取選項，會回 520
        const txt = await r.text();
        return new Response(txt, { status: r.status,
          headers: { 'Content-Type': 'application/json; charset=utf-8',
                     'Cache-Control': `public, max-age=${CACHE_CHART}`, ...cors(origin) } });
      } catch (e) {
        return json({ error: 'upstream failed', detail: String(e) }, 502, origin);
      }
    }

    // ---- /chart：當日分時（加權 / 櫃買 / 台指期）
    if (url.pathname === '/chart') {
      const id = (url.searchParams.get('id') || '').toUpperCase();
      const target = CHART_FILES[id];
      if (!target) {
        return json({ error: 'bad id', allowed: Object.keys(CHART_FILES) }, 400, origin);
      }
      return relay(target, origin, 'chart', CACHE_CHART);
    }

    // ---- /y：Yahoo 的當日分 K（補早盤用；個股沒有官方分時檔）
    if (url.pathname === '/y') {
      const sym = (url.searchParams.get('symbol') || '').toUpperCase();
      const iv = url.searchParams.get('interval') || '1m';
      const range = url.searchParams.get('range') || '1d';
      if (!Y_SYMBOL.test(sym)) return json({ error: 'bad symbol', got: sym }, 400, origin);
      if (!Y_INTERVAL.has(iv)) return json({ error: 'bad interval', allowed: [...Y_INTERVAL] }, 400, origin);
      if (!Y_RANGE.has(range)) return json({ error: 'bad range', allowed: [...Y_RANGE] }, 400, origin);
      return relay(`${YAHOO}${encodeURIComponent(sym)}?interval=${iv}&range=${range}`,
                   origin, 'yahoo', CACHE_CHART);
    }

    // /quote 與 /stream 共用同一套代號檢查 —— 兩條路的規則不一致的話，
    // 「退回輪詢」就會變成「換一條路就被擋」，那退回等於沒用。
    const parsed = parseTokens(url.searchParams.get('ex_ch') || '');
    if (parsed.error) return json(parsed.error, 400, origin);
    const target = `${UPSTREAM}?json=1&delay=0&ex_ch=${encodeURIComponent(parsed.tokens.join('|'))}`;
    return relay(target, origin, 'quote', CACHE_QUOTE);
  },
};

/** 打上游、加邊緣快取、補上 CORS 標頭。/quote、/chart、/y 共用。 */
async function relay(target, origin, kind, ttl) {
    const seconds = ttl || CACHE_CHART;
    // 邊緣快取：同樣的請求在 ttl 秒內只真的打上游一次
    const cache = caches.default;
    const cacheKey = new Request(target, { method: 'GET' });
    let hit = await cache.match(cacheKey);
    if (hit) {
      const body = await hit.text();
      return new Response(body, {
        status: 200,
        headers: Object.assign(
          { 'content-type': 'application/json; charset=utf-8', 'x-proxy-cache': 'HIT' },
          cors(origin)),
      });
    }

    let upstream;
    try {
      const head = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-TW,zh;q=0.9',
      };
      // Referer 只對證交所有意義；送給 Yahoo 反而怪
      if (kind !== 'yahoo') head['Referer'] = 'https://mis.twse.com.tw/stock/index.jsp';
      upstream = await fetch(target, {
        headers: head,
        cf: { cacheTtl: seconds, cacheEverything: true },
      });
    } catch (e) {
      return json({ error: 'upstream unreachable', detail: String(e).slice(0, 200) }, 502, origin);
    }
    if (!upstream.ok) {
      return json({ error: 'upstream error', status: upstream.status }, 502, origin);
    }

    const text = await upstream.text();
    const cached = new Response(text, {
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'Cache-Control': `public, max-age=${seconds}`,
      },
    });
    await cache.put(cacheKey, cached.clone());

    return new Response(text, {
      status: 200,
      headers: Object.assign(
        { 'content-type': 'application/json; charset=utf-8',
          'x-proxy-cache': 'MISS', 'x-proxy-kind': kind },
        cors(origin)),
    });
}

/* ================================================================ /stream 用的東西
 *
 * 這一整段只服務 SSE。上面那些 relay/json 一個字都沒動 ——
 * 舊的 /quote 仍然是原本的樣子，所以前端退回輪詢時走的是「本來就在跑的那條路」，
 * 不是另外寫一條沒人驗過的備援。
 */

/** /quote 與 /stream 共用的代號檢查。回 { tokens } 或 { error }。 */
function parseTokens(raw) {
  const s = (raw || '').trim();
  if (!s) return { error: { error: 'missing ex_ch' } };
  const tokens = s.split('|').filter(Boolean);
  if (tokens.length > MAX_TOKENS) {
    return { error: { error: 'too many symbols', max: MAX_TOKENS, got: tokens.length } };
  }
  const bad = tokens.find(t => !EX_CH.test(t));
  if (bad) return { error: { error: 'bad ex_ch token', token: bad } };
  return { tokens };
}

/** 現在是台北時間的哪一段。Worker 跑在 UTC，所以自己加 8 小時再判斷。
 *  只看星期幾，**不管國定假日** —— 跟前端 live.js 的 isIntraday 同一個理由：
 *  假日照跑只會拿到上一個交易日的數字（畫面上有資料時間），
 *  不值得為此在兩邊各維護一份行事曆。 */
function sessionNow() {
  const d = new Date(Date.now() + 8 * 3600 * 1000);
  const w = d.getUTCDay();
  if (w === 0 || w === 6) return 'closed';
  const m = d.getUTCHours() * 60 + d.getUTCMinutes();
  if (m >= 9 * 60 && m <= 13 * 60 + 35) return 'trade';            // 盤中
  if ((m >= 8 * 60 + 30 && m < 9 * 60) || (m > 13 * 60 + 35 && m <= 14 * 60 + 30)) return 'edge';
  return 'closed';                                                  // 夜間／假日
}

/** 打上游一次，瞬斷就再試一次。
 *
 *  為什麼要有：期交所那兩支是 POST，不能走邊緣快取（見 /fut、/futchart 裡的註解），
 *  所以每一次都是真的連出去，偶發的連線重置就會直接變成使用者眼前的空白。
 *  只重試一次、間隔 250ms —— 再多就會拖長使用者等待，而且 Worker 的 CPU 額度也有限。
 *  ★ 重試要重建 Request：Request 的 body 是 stream，用過就不能再用。 */
async function fetchRetry(req, tries = 2) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(req.clone());
      if (r.status < 500 || i === tries - 1) return r;
      last = r;
    } catch (e) {
      last = e;
      if (i === tries - 1) throw e;
    }
    await new Promise(res => setTimeout(res, 250));
  }
  if (last instanceof Response) return last;
  throw last;
}

/** 期交所台指期夜盤：台北 15:00 ~ 翌日 05:00（週一~週五開盤，週五夜盤跨到週六凌晨）。
 *  **只給 /health 看**，不影響任何一支端點的行為 —— /fut 與 /futchart 一律照打，
 *  要不要顯示由前端的時鐘決定（site/market3.js 的 futSession()）。 */
function futSessionNow() {
  const d = new Date(Date.now() + 8 * 3600 * 1000);
  const w = d.getUTCDay();
  const m = d.getUTCHours() * 60 + d.getUTCMinutes();
  if (m >= 15 * 60 && w >= 1 && w <= 5) return 'night';        // 週一~週五 15:00 之後
  if (m < 5 * 60 && w >= 2 && w <= 6) return 'night';          // 週二~週六凌晨（前一晚延續）
  return 'closed';
}

/** 這一段時間該多久問上游一次。closed 不進迴圈（見 openStream）。 */
function pollMsFor(sess) {
  const ms = sess === 'trade' ? POLL_TRADE_MS : POLL_EDGE_MS;
  return Math.max(POLL_MIN_MS, ms);
}

/** 去 mis 拿一份原始文字，**走邊緣快取**。
 *
 *  這就是「多個瀏覽器共用同一份上游結果」的實作：
 *  同一組代號在 ttl 秒內，不管有幾條 SSE 連線、幾個分頁，
 *  真的打到 mis 的只有第一次，其餘都吃快取。
 *  ttl 直接設成輪詢間隔 —— 比間隔長會讓推送變鈍，比間隔短就等於沒有節流。 */
async function misText(tokens, ttlSec) {
  const target = `${UPSTREAM}?json=1&delay=0&ex_ch=${encodeURIComponent(tokens.join('|'))}`;
  const cache = caches.default;
  const key = new Request(target, { method: 'GET' });
  const hit = await cache.match(key);
  if (hit) return { text: await hit.text(), cached: true };

  const r = await fetch(target, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'zh-TW,zh;q=0.9',
      'Referer': 'https://mis.twse.com.tw/stock/index.jsp',
    },
    cf: { cacheTtl: ttlSec, cacheEverything: true },
  });
  if (!r.ok) throw new Error('upstream ' + r.status);
  const text = await r.text();
  await cache.put(key, new Response(text, {
    headers: { 'content-type': 'application/json; charset=utf-8',
               'Cache-Control': `public, max-age=${ttlSec}` },
  }));
  return { text, cached: false };
}

/** 把回應裡「會變但不代表行情變了」的尾巴切掉，只留真正的行情內容。
 *
 *  mis 每一次回應都會附 queryTime／exKey／cachedAlive，**它們每次都不一樣**。
 *  直接比整串文字的話「永遠都在變」，等於沒有去重，5 秒推一次一模一樣的東西。
 *  切在 "queryTime" 之前，前面剩下的就是 msgArray + rtcode 那一段。
 *
 *  ★ 刻意用字串比對而不是 JSON.parse 再比欄位：免費方案每次調用只有 10ms CPU，
 *    一條連線要跑幾十輪，把 60KB 的 JSON 解析幾十次一定會超時。
 *    字串切一刀再比一次，成本幾乎是零。 */
function meaningful(text) {
  const i = text.indexOf('"queryTime"');
  return i > 0 ? text.slice(0, i) : text;
}

/** 組一則 SSE 訊息。data 可能有換行，逐行加 `data: ` 才符合規格。 */
function sse(event, payload) {
  const body = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const lines = body.split('\n').map(l => 'data: ' + l).join('\n');
  return `event: ${event}\n${lines}\n\n`;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

/** 開一條 SSE 連線。 */
function openStream(tokens, origin, request, ctx) {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const enc = new TextEncoder();
  const send = s => writer.write(enc.encode(s));

  const sess = sessionNow();
  const pollMs = pollMsFor(sess);

  const pump = (async () => {
    let last = '';
    try {
      // retry 告訴瀏覽器：連線斷了隔 3 秒自己回來。前端另外還有自己的退避，
      // 兩邊都有是故意的 —— 瀏覽器內建那套在某些情況下不會觸發（例如 404）。
      await send(`retry: ${SSE_RETRY_MS}\n\n`);
      await send(sse('hello', {
        session: sess, pollMs, symbols: tokens.length,
        maxMs: STREAM_MAX_MS, at: Date.now(),
      }));

      const started = Date.now();
      let first = true;
      while (true) {
        if (request.signal && request.signal.aborted) break;   // 使用者關了分頁
        let payload = null;
        try {
          const got = await misText(tokens, Math.ceil(pollMs / 1000));
          const sig = meaningful(got.text);
          // ★ 只有值真的變了才推。first 例外 ——
          //   剛連上（含斷線重連）一定要先給一份完整快照，
          //   不然「斷線期間漏掉的值」就永遠補不回來。
          if (first || sig !== last) { payload = got.text; last = sig; }
        } catch (e) {
          await send(sse('warn', { error: String(e).slice(0, 120) }));
        }
        if (payload !== null) await send(sse('quote', payload));
        first = false;

        // 非交易時段不進迴圈空轉：給一份快照就收掉，前端會自己退回慢速輪詢。
        if (sess === 'closed') {
          await send(sse('idle', { reason: '非交易時段，改由前端慢速輪詢' }));
          break;
        }
        if (Date.now() - started + pollMs > STREAM_MAX_MS) {
          await send(sse('bye', { reason: 'rotate', hint: '連線輪替，請立刻重連' }));
          break;
        }
        await send(`: hb ${Date.now()}\n\n`);   // 心跳，讓中間的代理不要把連線當成死的
        await sleep(pollMs);
      }
    } catch (e) {
      /* writer.write 失敗＝對面已經走了，這是正常結束，不是錯誤 */
    } finally {
      try { await writer.close(); } catch (e) { /* 已經關了 */ }
    }
  })();

  if (ctx && ctx.waitUntil) ctx.waitUntil(pump);

  return new Response(readable, {
    status: 200,
    headers: Object.assign({
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-cache, no-transform',
      'connection': 'keep-alive',
      'x-accel-buffering': 'no',        // 叫中間層不要緩衝，不然推送會卡住
    }, cors(origin)),
  });
}

/* ================================================================ /futstream 用的東西
 *
 * 這一整段只服務台指期夜盤的 SSE。上面的 `/stream`、`relay()`、`misText()`、
 * `meaningful()`、`sessionNow()` 一個字都沒動 —— 現貨那條推送的行為完全維持原樣，
 * 夜盤壞掉不會連累現貨，反過來也一樣（DECISIONS #255 教訓 2：失敗要獨立）。
 */

/** 期交所報價清單（getQuoteList）的上游請求。`/fut` 與 `/futstream` 共用同一份，
 *  兩條路不可以長得不一樣 —— 不然「退回輪詢」就會變成「換一條路就拿到不同的東西」。
 *  ★ 這是 POST，所以**絕對不准**帶 `cf: { cacheTtl / cacheEverything }`（DECISIONS #255 ③）。 */
function futQuoteRequest(night) {
  return new Request(TAIFEX_QUOTE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Referer': 'https://mis.taifex.com.tw/futures/',
      'Origin': 'https://mis.taifex.com.tw',
      'User-Agent': 'Mozilla/5.0 (compatible; tw-rotation/1.0)',
    },
    body: TAIFEX_BODY(night),
  });
}

/** 期交所分時序列（getChartData1M）的上游請求。同上，`/futchart` 與 `/futstream` 共用。
 *  ★ SymbolID 一定要是**字串**，送陣列會被回 400（2026-09-19 就是這樣白等了一輪）。 */
function futChartRequest(sym) {
  return new Request(TAIFEX_CHART, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Referer': 'https://mis.taifex.com.tw/futures/',
      'Origin': 'https://mis.taifex.com.tw',
      'User-Agent': 'Mozilla/5.0 (compatible; tw-rotation/1.0)',
    },
    body: JSON.stringify({ SymbolID: sym }),
  });
}

/* ---- 共用上游：模組作用域（isolate 層）的小記憶體 -----------------------------
 *
 * ★ 它保證什麼
 *   **同一個 isolate 裡**同時開著的多條 `/futstream` 連線，在 ttl 內只會真的打期交所一次。
 *   而且「同時抵達的第二條」不會另外開一次連線 —— 它會等第一條那個還沒回來的
 *   Promise（`futInflight`），所以尖峰時刻也不會變成 N 條連線 ＝ N 次上游請求。
 *
 * ★ 它**不**保證什麼
 *   Cloudflare 隨時可以起一個新的 isolate、也隨時可以把舊的收掉，
 *   跨 isolate、跨機房一律不共用。所以它是**節流**，不是**正確性**：
 *   任何邏輯都不准假設「別人已經幫我抓過了」，拿不到就自己抓、抓不到就往下報錯。
 *   最壞的情況（每條連線都在自己的 isolate）＝ 退化成「每條連線各打各的」，
 *   那正是這個方案的下限，而下限本來就是可以接受的（見上面間隔的算法）。
 *
 * ★ 為什麼不用 `caches.default`
 *   期交所那兩支是 POST。技術上可以自己捏一個 GET 當 cache key 把結果塞進去，
 *   但那是在**今天才剛壞過三次**的那條路徑上再加一個新的失敗點（put 失敗、
 *   快取回舊值、Vary 打架…），而它換到的只是「跨 isolate 也能共用」。
 *   節流的目標是「不要打爆期交所」，isolate 層已經達到了，不值得為此再冒一次險。
 *   ⚠ 更不准做的是把 `cf: { cacheTtl, cacheEverything }` 掛回 POST 上 —— 那會回 520。
 */
const futMemo = new Map();       // key -> { text, at }
const futInflight = new Map();   // key -> Promise<string>（正在飛的那一次）
const FUT_MEMO_MAX = 8;          // 日盤/夜盤各一把 ＋ 幾支近月合約，夠用了

async function futMemoFetch(key, ttlMs, make) {
  const fresh = futMemo.get(key);
  // 乘 0.9 是為了「自己的下一輪不要吃到自己上一輪的快取」：
  // 迴圈每 ttlMs 問一次，計時器早個幾毫秒觸發就會剛好踩在邊界上，白白少推一輪。
  if (fresh && Date.now() - fresh.at < ttlMs * 0.9) return { text: fresh.text, cached: true };
  let p = futInflight.get(key);
  if (!p) {
    p = (async () => {
      const r = await fetchRetry(make());          // ★ POST：不帶任何 cf 快取選項
      if (!r.ok) throw new Error('upstream ' + r.status);
      const text = await r.text();
      if (futMemo.size >= FUT_MEMO_MAX) futMemo.clear();
      futMemo.set(key, { text, at: Date.now() });
      return text;
    })();
    futInflight.set(key, p);
    // 成功或失敗都要把「正在飛」清掉，不然一次失敗會把這把鑰匙永久卡死
    p.then(() => {}, () => {}).then(() => {
      if (futInflight.get(key) === p) futInflight.delete(key);
    });
  }
  return { text: await p, cached: false };
}

/* ---- 去重：期交所回應裡「真的代表行情變了」的那幾段 ---------------------------
 *
 * 目的跟現貨那支 `meaningful()` 一樣，但**切法完全不同**。
 * 現貨是把尾巴的 `queryTime` 切掉就好（會變的東西集中在尾巴）；
 * 期交所沒有那種欄位，它每一次都在動的是**委買賣五檔**
 * （CBidPrice1~5 / CAskSize1~5 / CBidCount / CAskUnit / CBest* / CExt*），
 * 而那些欄位我們**一格都沒有顯示**。拿整串去比等於每一輪都推，去重形同虛設。
 *
 * 所以改成反過來做：**只留我們真的會畫到畫面上的那一段**。
 *   · 報價清單（getQuoteList）：每一檔從 `"CTotalVolume"` 到 `"CTestTime"` 那一段，
 *     剛好涵蓋 量／開／高／低／成交／參考價／漲跌停／結算價／未平倉／日期／時間。
 *   · 分時序列（getChartData1M）：`Quote` 裡從 `"COpenPrice"` 到 `"CBidCount"` 那一段，
 *     再加上 `Ticks` 陣列**最後那 220 個字**（最新的一根一定在尾巴；
 *     fixture 證實同一分鐘的那一根會被就地改寫，所以尾巴會跟著動）。
 *
 * ★ 這個切法是拿 fixture 驗過的（docs/fixtures/taifex_night_probe.json）：
 *     `taifex_chartdata_1m_night_full` 與 `our_worker_futchart_night` 相隔 4 秒，
 *     成交價 48013、累計量 22622、最後一根 Tick 完全一樣，只有五檔在動
 *     → 切完必須**相等**（不推）。
 *     `taifex_chartdata_1m_night` 是再早 6 秒那一份（48009／22616／最後一根不同）
 *     → 切完必須**不等**（要推）。
 *   兩條都寫成斷言了，見 scripts/_uitest.py 的「夜盤推送」段落與離線驗收腳本。
 *
 * ★ 刻意不 `JSON.parse`：免費方案每次調用只有 10ms CPU，一條連線要跑幾十輪，
 *   把 34KB 的 JSON 解析幾十次一定超時。這裡只做 1 個 regex ＋ 1 個 slice。
 * ★ 認不出形狀（期交所改了欄位順序）就回整串 —— 退化成「每一輪都推」，
 *   **絕不會**退化成「該推卻不推」。寧可多送，不可以漏送。
 */
/* ⚠ 這兩個是模組層的常數，所以**旗標不可以亂改**：
   `FUT_SIG_QUOTE` 帶 `g` 是因為報價清單有好幾檔合約、要全部撈出來，
   而且它只能配 `String.prototype.match`（match 會自己把 lastIndex 歸零）。
   換成 `.exec()` 或 `.test()` 就會變成有狀態的，第二次呼叫從上次的位置接著找 ——
   那會讓去重「有時候有效有時候沒效」，是最難查的一種壞法。
   `FUT_SIG_CHART` 不帶 `g`，所以配 `.exec()` 是安全的。
   上限 500／600 是從 fixture 量出來的（實際約 330／250 個字），
   超出就當作認不出形狀 → 回整串 → 退化成「每輪都推」，不會漏送。 */
const FUT_SIG_QUOTE = /"CTotalVolume"[^\n]{0,500}?"CTestTime"/g;
const FUT_SIG_CHART = /"COpenPrice"[^\n]{0,600}?"CBidCount"/;

function futMeaningful(text, kind) {
  if (kind === 'chart') {
    const m = FUT_SIG_CHART.exec(text);
    // Ticks 是整份回應裡唯一的「陣列裡面裝陣列」，所以最後一個 ']]' 就是它的結尾。
    // 用它定位而不是直接 slice(-220)，是為了不去假設 RtData 底下欄位誰排最後。
    const e = text.lastIndexOf(']]');
    if (!m || e <= 0) return text;
    return m[0] + '|' + text.slice(Math.max(0, e - 220), e);
  }
  const m = text.match(FUT_SIG_QUOTE);
  return m ? m.join('|') : text;
}

/** 開一條夜盤的 SSE 連線。 */
function openFutStream(want, symbol, origin, request, ctx) {
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const enc = new TextEncoder();
  const send = s => writer.write(enc.encode(s));
  const sess = futSessionNow();

  const pump = (async () => {
    let lastQ = '', lastC = '';
    try {
      await send(`retry: ${SSE_RETRY_MS}\n\n`);
      await send(sse('hello', {
        session: sess, want, symbol, pollMs: FUT_POLL_QUOTE_MS, chartMs: FUT_POLL_CHART_MS,
        maxMs: FUT_STREAM_MAX_MS, at: Date.now(),
      }));

      /* ★ 非夜盤時段：**一個上游請求都不打**，直接說明原因收線。
         這裡刻意跟現貨那條不一樣（現貨會先給一份快照才收）——
         夜盤時段外打 MarketType=1，期交所回的是**日盤最後一筆**，
         把它推給前端就是 DECISIONS #255 ① 那個「拿日盤冒充夜盤」，
         而那正是 Andy 明講不要的東西。沒有東西可推的時候，最好的推送是不推。 */
      if (sess !== 'night' || want !== 'night') {
        await send(sse('idle', {
          reason: '非夜盤時段（台北 15:00～翌日 05:00），改由前端慢速輪詢',
          futSession: sess,
        }));
        return;
      }

      const started = Date.now();
      let first = true;
      let chartAt = 0;
      while (true) {
        if (request.signal && request.signal.aborted) break;   // 使用者關了分頁

        // ---- 報價：10 秒一次（見上面間隔的算法）
        try {
          const got = await futMemoFetch('q|' + want, FUT_POLL_QUOTE_MS, () => futQuoteRequest(want === 'night'));
          const sig = futMeaningful(got.text, 'quote');
          /* first 例外：剛連上（含斷線重連、4 分鐘輪替）一定要先給一份完整快照，
             不然斷線期間漏掉的值永遠補不回來 —— 跟現貨那條同一個理由。 */
          if (first || sig !== lastQ) { lastQ = sig; await send(sse('fut', got.text)); }
        } catch (e) {
          await send(sse('warn', { which: 'fut', error: String(e).slice(0, 120) }));
        }

        // ---- 分時序列：60 秒一次。Ticks 一分鐘一根，問得更密在物理上拿不到新的一根。
        //      ★ 它跟報價**互不依賴地失敗**：這一支掛掉不准影響上面那一支，反之亦然。
        if (symbol && (first || Date.now() - chartAt >= FUT_POLL_CHART_MS)) {
          chartAt = Date.now();
          try {
            const got = await futMemoFetch('c|' + symbol, FUT_POLL_CHART_MS, () => futChartRequest(symbol));
            const sig = futMeaningful(got.text, 'chart');
            if (first || sig !== lastC) { lastC = sig; await send(sse('futchart', got.text)); }
          } catch (e) {
            await send(sse('warn', { which: 'futchart', error: String(e).slice(0, 120) }));
          }
        }
        first = false;

        if (Date.now() - started + FUT_POLL_QUOTE_MS > FUT_STREAM_MAX_MS) {
          await send(sse('bye', { reason: 'rotate', hint: '連線輪替，請立刻重連' }));
          break;
        }
        await send(`: hb ${Date.now()}\n\n`);       // 心跳，讓中間的代理不要把連線當成死的
        await sleep(Math.max(FUT_POLL_MIN_MS, FUT_POLL_QUOTE_MS));
      }
    } catch (e) {
      /* writer.write 失敗＝對面已經走了，這是正常結束，不是錯誤 */
    } finally {
      try { await writer.close(); } catch (e) { /* 已經關了 */ }
    }
  })();

  if (ctx && ctx.waitUntil) ctx.waitUntil(pump);

  return new Response(readable, {
    status: 200,
    headers: Object.assign({
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-cache, no-transform',
      'connection': 'keep-alive',
      'x-accel-buffering': 'no',
    }, cors(origin)),
  });
}
