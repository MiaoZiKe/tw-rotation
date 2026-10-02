/* 台指期專用的小代理（Deno Deploy 版）—— DECISIONS #281、#286
 *
 * ★ 為什麼要有這一支（不是放在 workers/quote-proxy 的 Cloudflare Worker 裡就好）
 *   mis.taifex.com.tw 本身架在 Cloudflare 後面。Cloudflare Worker 對「另一個 Cloudflare
 *   客戶的網域」發子請求時，對方看到的來源 IP 一律是全體 Worker 共用的那一個，
 *   期交所那一側擋它（或限流它），Cloudflare 就代填 520。2026-10-01 三輪實測：
 *   換標頭、換路徑、換機房、連打三次全部 520；同樣的請求從 GitHub Actions 直連是 200。
 *   瀏覽器也不能直連（期交所的 CORS 預檢回 403）。
 *   所以只剩「找一個不經 Cloudflare 出口的地方代打」—— Deno Deploy 跑在自家網路。
 *
 * ★ 只做兩支，形狀逐字照搬 workers/quote-proxy/worker.js
 *   /fut?session=day|night   → 期交所 getQuoteList（夜盤 MarketType=1）
 *   /futchart?symbol=TXFJ6-M → 期交所 getChartData1M
 *   前端 site/market3.js 的 fetchFut()／fetchFutChart() 只認期交所原始 JSON，
 *   所以成功時**原文照轉**，一個欄位都不加；這樣前端換後端時不必動任何解析。
 *   請求的標頭與 body、成功回應的 Cache-Control 秒數（3／10 秒）也跟 Worker 一模一樣，
 *   免得「換一條路就拿到不同的東西」。
 *
 * ★ 不是通用代理
 *   body 由這裡寫死、symbol 鎖成合約代號形狀（DECISIONS #108 同一條理由）：
 *   誰都不能拿它去打期交所的任意端點，更不能打別的網站。
 *
 * ★ 沒有任何金鑰。期交所這兩支不需要認證；部署用的 DENO_DEPLOY_TOKEN 只在 GitHub Secrets。
 */

const TAIFEX_QUOTE = 'https://mis.taifex.com.tw/futures/api/getQuoteList';
const TAIFEX_CHART = 'https://mis.taifex.com.tw/futures/api/getChartData1M';

// 跟 worker.js 的 TAIFEX_BODY 逐字元相同（欄位順序也一樣，期交所吃的是這個形狀）
const TAIFEX_BODY = (night: boolean) => JSON.stringify({
  MarketType: night ? '1' : '0', SymbolType: 'F', KindID: '1', CID: 'TXF',
  ExpireMonth: '', RowSize: '全部', PageNo: '', SortColumn: '', AscDesc: 'A',
});

// 合約代號：英數 3~8 碼 + -F（日盤）／-M（夜盤）。跟 worker.js 的 FUT_SYMBOL 同一條
const FUT_SYMBOL = /^[A-Z0-9]{3,8}-[FM]$/;

// 成功回應給瀏覽器的快取秒數，照搬 worker.js 的 CACHE_QUOTE／CACHE_CHART
const CACHE_QUOTE = 3;
const CACHE_CHART = 10;

// 上游等太久就放棄：快速失敗好過讓讀者等到瀏覽器逾時（#256 的教訓）
const UPSTREAM_TIMEOUT_MS = 8000;

const ALLOW_ORIGINS = [
  'https://miaozike.github.io',
  'http://127.0.0.1:8766',   // scripts/_preview.py
  'http://127.0.0.1:8767',   // scripts/_uitest.py
  'http://localhost:8766',
  'http://localhost:8767',
];

// 跟 worker.js 的上游標頭一致（Origin／Referer 是期交所自己的頁面，它要看這兩個）
const UPSTREAM_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Referer': 'https://mis.taifex.com.tw/futures/',
  'Origin': 'https://mis.taifex.com.tw',
  'User-Agent': 'Mozilla/5.0 (compatible; tw-rotation/1.0)',
};

function cors(origin: string): Record<string, string> {
  const h: Record<string, string> = {
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
  if (origin && ALLOW_ORIGINS.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

function json(body: unknown, status: number, origin: string): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...cors(origin) },
  });
}

// 204／205／304 不能帶 body，轉成 200（跟 worker.js 的 safeStatus 同一條）
function safeStatus(code: number): number {
  return (code === 204 || code === 205 || code === 304) ? 200 : code;
}

function region(): string {
  // Deno Deploy 會給 DENO_REGION（出口在哪一區）；拿不到就空著，不影響行為
  try { return Deno.env.get('DENO_REGION') || ''; } catch { return ''; }
}

/* 打期交所一次，不重試。
 *   重試救不回「一直都壞」的東西，只會把期交所那邊的請求量乘二、把讀者的等待拉長（#256、#281）。
 *   每次都 new 一個 Request：body 是 stream，共用會在第二次送出空 body（#256 ③ 踩過）。 */
async function upstream(url: string, body: string): Promise<Response> {
  return await fetch(url, {
    method: 'POST',
    headers: UPSTREAM_HEADERS,
    body,
    signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
  });
}

/* 上游 5xx：不原樣轉回，改回講得出斷點的 502 JSON（跟 worker.js 的 futUpstreamFail 同欄位）。
 *   colo 那欄在這裡改叫 region（Deno 沒有 Cloudflare 機房的概念）。 */
function upstreamFail(which: 'fut' | 'futchart', session: string, r: Response, txt: string,
                      t0: number, origin: string): Response {
  return json({
    error: 'upstream',
    which, session,
    upstream: which === 'fut' ? 'mis.taifex.com.tw getQuoteList' : 'mis.taifex.com.tw getChartData1M',
    upstream_status: r.status,
    elapsed_ms: Date.now() - t0,
    region: region(),
    upstream_ray: r.headers.get('cf-ray') || '',
    head: String(txt || '').slice(0, 80),
    via: 'deno',
  }, 502, origin);
}

async function relay(which: 'fut' | 'futchart', session: string, url: string, body: string,
                     cacheSec: number, origin: string): Promise<Response> {
  const t0 = Date.now();
  try {
    const r = await upstream(url, body);
    const txt = await r.text();
    if (r.status >= 500) return upstreamFail(which, session, r, txt, t0, origin);
    // 成功與 4xx：原文照轉（前端只認期交所原始 JSON）
    return new Response(txt, {
      status: safeStatus(r.status),
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': `public, max-age=${cacheSec}`,
        ...cors(origin),
      },
    });
  } catch (e) {
    return json({ error: 'upstream failed', which, session, detail: String(e),
                  elapsed_ms: Date.now() - t0, region: region(), via: 'deno' }, 502, origin);
  }
}

export async function handler(request: Request): Promise<Response> {
  const origin = request.headers.get('Origin') || '';
  const url = new URL(request.url);

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: cors(origin) });
  }
  if (request.method !== 'GET') {
    return json({ error: 'method not allowed' }, 405, origin);
  }
  if (url.pathname === '/' || url.pathname === '/health') {
    return json({ ok: true, service: 'tw-rotation taifex-deno', upstream: 'mis.taifex.com.tw',
                  features: ['fut', 'futchart'], region: region() }, 200, origin);
  }
  if (url.pathname !== '/fut' && url.pathname !== '/futchart') {
    return json({ error: 'not found' }, 404, origin);
  }
  if (origin && !ALLOW_ORIGINS.includes(origin)) {
    // 不給 CORS 標頭，瀏覽器那邊讀不到；這裡也直接講原因方便除錯
    return json({ error: 'origin not allowed', origin }, 403, '');
  }

  if (url.pathname === '/fut') {
    const night = (url.searchParams.get('session') || 'day') === 'night';
    return await relay('fut', night ? 'night' : 'day', TAIFEX_QUOTE, TAIFEX_BODY(night),
                       CACHE_QUOTE, origin);
  }

  // /futchart
  const sym = (url.searchParams.get('symbol') || '').toUpperCase();
  if (!FUT_SYMBOL.test(sym)) return json({ error: 'bad symbol', got: sym }, 400, origin);
  return await relay('futchart', sym.endsWith('-M') ? 'night' : 'day', TAIFEX_CHART,
                     JSON.stringify({ SymbolID: sym }), CACHE_CHART, origin);
}

// 無條件啟動：Deno Deploy 的進入點就是這支檔案；不靠 import.meta.main 判斷，少一個「部署上去卻沒在聽」的變數
Deno.serve(handler);
