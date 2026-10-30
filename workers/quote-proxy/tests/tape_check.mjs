// 當日快照（tape）離線驗收：假 KV、假 mis、假網站名單，跑真的 worker.js 的 scheduled() 與 GET /tape
import worker from '/home/user/tw-rotation/workers/quote-proxy/worker.js';
const fails = [];
const ok = (n, c, d = '') => { console.log((c ? '  OK  ' : '  XX  ') + n + (c ? '' : '   <- ' + d)); if (!c) fails.push(n); };
globalThis.caches = { default: { async match() { return null; }, async put() {} } };
const kv = new Map(); let puts = 0;
const TAPE = { async get(k, t) { const v = kv.get(k); if (v == null) return null; return t === 'json' ? JSON.parse(v) : v; },
               async put(k, v) { puts++; kv.set(k, v); } };
const realNow = Date.now.bind(Date);
let misDay = '20261029', misReqs = 0, siteReqs = 0, k = 0;
globalThis.fetch = async (u) => {
  u = String(u);
  if (u.includes('tape_codes.json')) { siteReqs++; return new Response(JSON.stringify({ codes: [['2330', 'tse'], ['3374', 'otc'], ['2317', 'tse']] }), { status: 200 }); }
  if (u.includes('getStockInfo')) {
    misReqs++; k++;
    const ex = decodeURIComponent(u.split('ex_ch=')[1]).split('|');
    const arr = ex.map(t => { const c = t.split('_')[1].split('.')[0];
      return c === '2317' ? { c, z: '-', y: '100', o: '-', b: '101.5_100.5_', v: '9', d: misDay, trade: { z: '102.0' } }
                          : { c, z: String(100 + k), y: '100', v: String(1000 * k), d: misDay }; });
    return new Response(JSON.stringify({ msgArray: arr }), { status: 200 });
  }
  return new Response('x', { status: 404 });
};
const at = (h, m, day = '2026-10-29') => Date.parse(`${day}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:07+08:00`);
const run = (ms, env = { TAPE }) => { let p; worker.scheduled({ scheduledTime: ms }, env, { waitUntil(x) { p = x; } }); return p; };
const get = async (q = '') => worker.fetch(new Request('https://w/tape' + q, { headers: { Origin: 'https://miaozike.github.io' } }), { TAPE }, { waitUntil() {} });

await run(at(9, 0)); await run(at(9, 5)); await run(at(9, 5));      // 第三次是同一格重複
let body = kv.get('tape:20261029') || '';
let lines = body.split('\n').filter(Boolean);
ok('三次排程（含一次重複）→ 標頭 ＋ 兩筆快照', lines.length === 3, lines.length);
const head = JSON.parse(lines[0]);
ok('標頭有日期、代號順序、昨收', head.date === '2026-10-29' && head.codes.join() === '2330,3374,2317' && head.y.join() === '100,100,100', JSON.stringify(head));
const s1 = JSON.parse(lines[1]), s2 = JSON.parse(lines[2]);
ok('時間格是 09:00 與 09:05', s1.t === '09:00' && s2.t === '09:05', s1.t + s2.t);
ok('價格與累積量依標頭順序', s1.p.length === 3 && s1.v[0] > 0 && s2.v[0] > s1.v[0], JSON.stringify(s2));
ok('z=- 時退位：成交價用 trade.z', s1.p[2] === 102, s1.p[2]);
ok('名單只抓一次（同一天）', siteReqs === 1, siteReqs);
ok('上市＋上櫃混在同一個請求，每輪 1 個 mis 請求', misReqs === 2, misReqs);
const r = await get();
const txt = await r.text();
ok('GET /tape 回 NDJSON 全文', r.status === 200 && txt === body && r.headers.get('content-type').includes('ndjson'));
ok('GET /tape 帶 CORS', r.headers.get('access-control-allow-origin') === 'https://miaozike.github.io');
ok('?date= 指定日期可讀、壞格式 400', (await get('?date=20261029')).status === 200 && (await get('?date=abc')).status === 400);
ok('沒有的日期 404', (await get('?date=20250101')).status === 404);
const before = puts;
await run(at(8, 55)); await run(at(13, 45)); await run(at(10, 0, '2026-10-31'));
ok('盤前、盤後、週末都不寫入', puts === before, puts - before);
misDay = '20261028';
await run(at(10, 0, '2026-10-30'));
ok('休市日（mis 回的日期不是今天）不寫入', !kv.has('tape:20261030'));
ok('沒綁 KV 時不丟例外', (await run(at(9, 10), {})) === undefined || true);
console.log(fails.length ? `\n${fails.length} 項沒過` : '\n全部通過');
process.exit(fails.length ? 1 : 0);
