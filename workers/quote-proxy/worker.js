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

// 允許呼叫這支 Worker 的網站。要多一個網域就加在這裡。
const ALLOW_ORIGINS = [
  'https://miaozike.github.io',
  'http://127.0.0.1:8766',   // scripts/_preview.py
  'http://127.0.0.1:8767',   // scripts/_uitest.py
  'http://localhost:8766',
  'http://localhost:8767',
];

const EX_CH = /^(tse|otc)_[A-Za-z0-9]{2,8}\.tw$/;
const MAX_TOKENS = 140;
const CACHE_SECONDS = 10;

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
  async fetch(request) {
    const origin = request.headers.get('Origin') || '';
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    if (request.method !== 'GET') {
      return json({ error: 'method not allowed' }, 405, origin);
    }
    if (url.pathname === '/' || url.pathname === '/health') {
      return json({ ok: true, service: 'tw-rotation quote-proxy', upstream: 'mis.twse.com.tw' }, 200, origin);
    }
    if (url.pathname !== '/quote') {
      return json({ error: 'not found' }, 404, origin);
    }
    if (origin && !ALLOW_ORIGINS.includes(origin)) {
      // 不給 CORS 標頭，瀏覽器那邊自然讀不到；這裡也直接講清楚原因方便除錯
      return json({ error: 'origin not allowed', origin }, 403, '');
    }

    const raw = (url.searchParams.get('ex_ch') || '').trim();
    if (!raw) return json({ error: 'missing ex_ch' }, 400, origin);
    const tokens = raw.split('|').filter(Boolean);
    if (tokens.length > MAX_TOKENS) {
      return json({ error: 'too many symbols', max: MAX_TOKENS, got: tokens.length }, 400, origin);
    }
    const bad = tokens.find(t => !EX_CH.test(t));
    if (bad) return json({ error: 'bad ex_ch token', token: bad }, 400, origin);

    const target = `${UPSTREAM}?json=1&delay=0&ex_ch=${encodeURIComponent(tokens.join('|'))}`;

    // 邊緣快取：同樣的代號組合 10 秒內只真的打上游一次
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
      upstream = await fetch(target, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
          'Referer': 'https://mis.twse.com.tw/stock/index.jsp',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'zh-TW,zh;q=0.9',
        },
        cf: { cacheTtl: CACHE_SECONDS, cacheEverything: true },
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
        'Cache-Control': `public, max-age=${CACHE_SECONDS}`,
      },
    });
    await cache.put(cacheKey, cached.clone());

    return new Response(text, {
      status: 200,
      headers: Object.assign(
        { 'content-type': 'application/json; charset=utf-8', 'x-proxy-cache': 'MISS' },
        cors(origin)),
    });
  },
};
