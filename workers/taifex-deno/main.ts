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

/* ================================================================== /sse-test（實驗端點，DECISIONS #299）
 *
 * ★ 要回答的問題：Deno Deploy 能不能當「中央抓一次、推給所有讀者」的推播中樞？
 *   現在每個讀者每 15 秒自己打一次 /fut（#286、#299），讀者一多就吃掉免費層每月 100 萬次請求。
 *   改成推播（SSE）的話，一個讀者只連一次，額度就從「每 N 秒一次」變成「每次開頁一次（＋斷線重連）」。
 *   這支端點只是實驗：量 Deploy 會不會把長連線切掉、多久切、同一個 isolate 能不能共用一份上游結果。
 *
 * ★ 行為
 *   - 每 5 秒推一筆 `event: tick`，帶序號（id＝這條連線的第幾筆，斷線重連時 client 會帶 Last-Event-ID）、
 *     伺服器時間、這個 isolate 的隨機代號、同 isolate 目前有幾條連線、共用上游抓了第幾次、上游狀態與近月成交價。
 *   - **同一個 isolate 只有一個計時器**：有人連著才每 5 秒打一次期交所（日盤或夜盤看台北時間），
 *     結果推給這個 isolate 上所有連線；最後一條斷了計時器就收掉。所以 up_seq 應該約等於「經過秒數 ÷ 5」，
 *     而不是再乘上連線數 —— 那就是「中央抓一次」在單一 isolate 內成立的證據。
 *   - work_ms：這個 isolate 為推播實際花在同步程式碼上的毫秒數（解析上游 JSON＋組字串），拿來估 CPU。
 *
 * ★ 防濫用（public 網址，誰都打得到）
 *   - SSE_TEST_ENABLED＝false 時一律 410（實測完就關）；另有到期時間 SSE_TEST_UNTIL，過了也是 410，
 *     忘了關也不會一直開著。
 *   - 每個 isolate 同時最多 SSE_MAX_CONN 條；每條最長 SSE_MAX_MS（到了伺服器主動結束）；
 *     每個 isolate 這輩子最多開 SSE_MAX_TOTAL 條（防有人狂重連）。超過回 429。
 *   - 上游 body 一樣寫死（期交所 getQuoteList），不能被拿去打任意網址。
 */
const SSE_TEST_ENABLED = true;
const SSE_TEST_UNTIL = Date.parse('2026-10-04T16:00:00Z');   // 台北 10-05 00:00 之後自動停用
const SSE_MAX_CONN = 8;
const SSE_MAX_MS = 16 * 60 * 1000;
const SSE_MAX_TOTAL = 80;
const SSE_TICK_MS = 5000;

const ISOLATE_ID = crypto.randomUUID().slice(0, 8);
const ISOLATE_BORN = Date.now();
type Sub = { id: number; ctl: ReadableStreamDefaultController<Uint8Array>; seq: number; t0: number; timer?: ReturnType<typeof setTimeout> };
type UpLast = { at: number; status: number; ms: number; price: string; time: string; session: string; err: string };
const sse = {
  subs: new Set<Sub>(),
  total: 0,              // 這個 isolate 開過幾條
  nextId: 1,
  timer: null as ReturnType<typeof setInterval> | null,   // 共用的那一個 5 秒計時器
  upSeq: 0,              // 共用上游抓了幾次
  upOk: 0,
  workMs: 0,             // 同步程式碼累計毫秒
  last: null as UpLast | null,
};
const enc = new TextEncoder();

function cpuMs(): number | null {
  // 盡力而為：Deploy 上 node:process 的 cpuUsage 可能是整個行程、也可能拿不到；拿不到回 null，不影響推播
  try {
    // deno-lint-ignore no-explicit-any
    const p = (globalThis as any).process;
    if (p && typeof p.cpuUsage === 'function') { const u = p.cpuUsage(); return Math.round((u.user + u.system) / 1000); }
  } catch { /* 拿不到就算了 */ }
  return null;
}

function taipeiMin(): number {
  const d = new Date(Date.now() + 8 * 3600 * 1000);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
}

async function sseUpstream(): Promise<void> {
  const m = taipeiMin();
  const night = !(m >= 8 * 60 + 45 && m <= 13 * 60 + 45);
  const t0 = Date.now();
  sse.upSeq++;
  try {
    const r = await upstream(TAIFEX_QUOTE, TAIFEX_BODY(night));
    const txt = await r.text();
    const w0 = performance.now();
    let price = '', time = '';
    try {
      const j = JSON.parse(txt);
      // deno-lint-ignore no-explicit-any
      const list = ((j.RtData || {}).QuoteList || []).filter((q: any) => q.SymbolID && !/-[SP]$/.test(q.SymbolID));
      // deno-lint-ignore no-explicit-any
      list.sort((a: any, b: any) => (parseFloat(b.CTotalVolume) || 0) - (parseFloat(a.CTotalVolume) || 0));
      if (list[0]) { price = String(list[0].CLastPrice || ''); time = String(list[0].CTime || ''); }
    } catch { /* 解析失敗就只記狀態碼 */ }
    sse.workMs += performance.now() - w0;
    if (r.ok) sse.upOk++;
    sse.last = { at: Date.now(), status: r.status, ms: Date.now() - t0, price, time, session: night ? 'night' : 'day',
                 err: r.ok ? '' : txt.slice(0, 80) };
  } catch (e) {
    sse.last = { at: Date.now(), status: 0, ms: Date.now() - t0, price: '', time: '', session: night ? 'night' : 'day',
                 err: String(e).slice(0, 80) };
  }
}

function sseSend(s: Sub, event: string, data: unknown): boolean {
  try {
    s.seq++;
    s.ctl.enqueue(enc.encode(`id: ${s.seq}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
    return true;
  } catch {
    return false;   // 連線已經關了（client 走掉）
  }
}

function sseDrop(s: Sub, close: boolean) {
  if (!sse.subs.has(s)) return;
  sse.subs.delete(s);
  if (s.timer) clearTimeout(s.timer);
  if (close) { try { s.ctl.close(); } catch { /* 已關 */ } }
  if (!sse.subs.size && sse.timer) { clearInterval(sse.timer); sse.timer = null; }
}

async function sseTick() {
  await sseUpstream();
  const w0 = performance.now();
  const now = Date.now();
  for (const s of [...sse.subs]) {
    const ok = sseSend(s, 'tick', {
      conn: s.id, t: now, up_t: sse.last?.at || 0,
      iso: ISOLATE_ID, iso_age_s: Math.round((now - ISOLATE_BORN) / 1000), region: region(),
      conns: sse.subs.size, total: sse.total,
      up_seq: sse.upSeq, up_ok: sse.upOk, up: sse.last,
      work_ms: Math.round(sse.workMs * 10) / 10, cpu_ms: cpuMs(),
    });
    if (!ok) sseDrop(s, false);
  }
  sse.workMs += performance.now() - w0;
}

function sseTest(request: Request, origin: string): Response {
  if (!SSE_TEST_ENABLED || Date.now() > SSE_TEST_UNTIL) {
    return json({ error: 'sse-test disabled', why: '實驗端點已停用（DECISIONS #299）' }, 410, origin);
  }
  if (sse.subs.size >= SSE_MAX_CONN || sse.total >= SSE_MAX_TOTAL) {
    return json({ error: 'too many', conns: sse.subs.size, total: sse.total, iso: ISOLATE_ID }, 429, origin);
  }
  sse.total++;
  const resumed = request.headers.get('Last-Event-ID') || '';
  let me: Sub | null = null;
  const body = new ReadableStream<Uint8Array>({
    start(ctl) {
      const s: Sub = { id: sse.nextId++, ctl, seq: 0, t0: Date.now() };
      me = s;
      sse.subs.add(s);
      // retry：瀏覽器 EventSource 斷線後 3 秒重連；hello 先讓 client 知道連上了哪個 isolate
      ctl.enqueue(enc.encode('retry: 3000\n\n'));
      sseSend(s, 'hello', { conn: s.id, iso: ISOLATE_ID, iso_age_s: Math.round((Date.now() - ISOLATE_BORN) / 1000),
                            region: region(), conns: sse.subs.size, total: sse.total, resumed_from: resumed,
                            max_ms: SSE_MAX_MS, tick_ms: SSE_TICK_MS });
      s.timer = setTimeout(() => { sseSend(s, 'bye', { why: 'max_ms', conn: s.id }); sseDrop(s, true); }, SSE_MAX_MS);
      if (!sse.timer) sse.timer = setInterval(sseTick, SSE_TICK_MS);
    },
    cancel() { if (me) sseDrop(me, false); },
  });
  return new Response(body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      'X-Accel-Buffering': 'no',
      ...cors(origin),
    },
  });
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
                  features: ['fut', 'futchart'], region: region(),
                  sse_test: SSE_TEST_ENABLED && Date.now() <= SSE_TEST_UNTIL }, 200, origin);
  }
  if (url.pathname === '/sse-test') {
    // 實驗端點：不擋沒有 Origin 的請求（GitHub Actions 的探測沒有 Origin），有 Origin 就要在白名單
    if (origin && !ALLOW_ORIGINS.includes(origin)) return json({ error: 'origin not allowed', origin }, 403, '');
    return sseTest(request, origin);
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
