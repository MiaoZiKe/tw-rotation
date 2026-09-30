// /fut、/futchart 上游失敗處理的離線驗收（DECISIONS #281）
//
// 保證三件事：
//   ① 上游 5xx（尤其 520）不再原樣轉回，改回 502 JSON，帶 upstream_status／elapsed_ms／colo／head
//   ② 2xx／4xx／304 那條路（日盤與夜盤的成功回應）跟改之前**逐位元組一樣**
//      —— 設 OLD_WORKER=<舊版 worker.js 的絕對路徑> 就會拿同一組假上游跑新舊兩版、逐欄比對
//   ③ 沒有重試（一次請求 = 一次上游），diag=1 一個 isolate 30 秒只准跑一次
//
// 跑法：node workers/quote-proxy/tests/fut_fail_check.mjs
//      OLD_WORKER=/tmp/old_worker.js node workers/quote-proxy/tests/fut_fail_check.mjs
import worker from '../worker.js';

const fails = [];
const ok = (n, c, d = '') => { console.log((c ? '  OK  ' : '  XX  ') + n + (c ? '' : '   <- ' + JSON.stringify(d))); if (!c) fails.push(n); };

let hits = 0, lastReq = null;
let next = () => new Response('{"RtCode":"0","RtData":{"QuoteList":[]}}', { status: 200 });
globalThis.fetch = async (req) => { hits++; lastReq = req; return next(req); };
globalThis.caches = { default: { async match() { return null; }, async put() {} } };

const ctx = { waitUntil() {} };
const mk = (u) => { const r = new Request(u, { headers: { Origin: 'https://miaozike.github.io' } });
  Object.defineProperty(r, 'cf', { value: { colo: 'TPE' } }); return r; };
const call = async (w, u) => { const r = await w.fetch(mk(u), {}, ctx);
  const h = {}; r.headers.forEach((v, k) => { h[k] = v; });
  return { status: r.status, headers: h, body: await r.text() }; };

// ---- ① 上游 520 → 502 JSON
next = () => new Response('error code: 520\n', { status: 520, headers: { 'cf-ray': 'abc-TPE' } });
for (const [u, which, sess] of [
  ['https://w/fut?session=night', 'fut', 'night'],
  ['https://w/fut?session=day', 'fut', 'day'],
  ['https://w/futchart?symbol=TXFJ6-M', 'futchart', 'night'],
  ['https://w/futchart?symbol=TXFJ6-F', 'futchart', 'day'],
]) {
  hits = 0;
  const r = await call(worker, u);
  let j = {}; try { j = JSON.parse(r.body); } catch (e) { /* 下面會紅 */ }
  ok(`${u}：上游 520 → 回 502`, r.status === 502, r.status);
  ok(`${u}：講得出 upstream_status 520`, j.upstream_status === 520, j);
  ok(`${u}：which／session 正確`, j.which === which && j.session === sess, j);
  ok(`${u}：帶 colo 與 upstream_ray`, j.colo === 'TPE' && j.upstream_ray === 'abc-TPE', j);
  ok(`${u}：帶內容前 80 字`, j.head === 'error code: 520\n', j.head);
  ok(`${u}：elapsed_ms 是數字`, typeof j.elapsed_ms === 'number', j.elapsed_ms);
  ok(`${u}：瀏覽器讀得到（有 CORS）`, r.headers['access-control-allow-origin'] === 'https://miaozike.github.io', r.headers);
  ok(`${u}：沒有重試（上游只被打 1 次）`, hits === 1, hits);
}

// ---- 上游直接丟例外 → 502 JSON（原本就是，這次多帶 elapsed_ms／colo）
next = () => { throw new Error('Network connection lost'); };
{
  const r = await call(worker, 'https://w/fut?session=night');
  const j = JSON.parse(r.body);
  ok('上游丟例外 → 502 upstream failed', r.status === 502 && j.error === 'upstream failed', j);
  ok('上游丟例外也帶 colo', j.colo === 'TPE', j);
}

// ---- ② 成功與 4xx 那條路：形狀照舊
const cases = [
  ['day 200', 'https://w/fut?session=day', () => new Response('{"RtCode":"0","RtData":{"QuoteList":[{"SymbolID":"TXFJ6-F"}]}}', { status: 200 })],
  ['night 200', 'https://w/fut?session=night', () => new Response('{"RtCode":"0","RtData":{"QuoteList":[{"SymbolID":"TXFJ6-M"}]}}', { status: 200 })],
  ['chart 200', 'https://w/futchart?symbol=TXFJ6-M', () => new Response('{"RtCode":"0","RtData":{"Ticks":[["150100","1","2","0","1","3"]]}}', { status: 200 })],
  ['day 400', 'https://w/fut?session=day', () => new Response('{"status":400}', { status: 400 })],
  ['chart 304', 'https://w/futchart?symbol=TXFJ6-F', () => new Response(null, { status: 304 })],
];
for (const [name, u, f] of cases) {
  next = f; hits = 0;
  const r = await call(worker, u);
  const want = f();
  ok(`${name}：狀態照舊`, r.status === (want.status === 304 ? 200 : want.status), r.status);
  ok(`${name}：內容原樣轉回`, r.body === await f().text(), r.body.slice(0, 80));
  ok(`${name}：Content-Type 照舊`, r.headers['content-type'] === 'application/json; charset=utf-8', r.headers);
  ok(`${name}：只打上游 1 次`, hits === 1, hits);
}

// 新舊兩版逐欄比對（有給舊版才跑）
if (process.env.OLD_WORKER) {
  const old = (await import(process.env.OLD_WORKER)).default;
  for (const [name, u, f] of cases) {
    next = f;
    const a = await call(old, u);
    const b = await call(worker, u);
    ok(`新舊一致：${name}`, JSON.stringify(a) === JSON.stringify(b), { old: a, now: b });
  }
  // 現貨與分時檔那幾條路（relay）完全沒碰：同一組假上游，新舊回應一樣
  next = () => new Response('{"msgArray":[{"c":"2330","z":"900"}]}', { status: 200 });
  for (const u of ['https://w/quote?ex_ch=tse_2330.tw', 'https://w/chart?id=FUT', 'https://w/health']) {
    const a = await call(old, u), b = await call(worker, u);
    if (u.endsWith('/health')) { a.body = a.body.replace(/"session":"\w+","futSession":"\w+"/, ''); b.body = b.body.replace(/"session":"\w+","futSession":"\w+"/, ''); }
    ok(`新舊一致：${u}`, JSON.stringify(a) === JSON.stringify(b), { old: a, now: b });
  }
} else {
  console.log('  （沒給 OLD_WORKER，跳過新舊逐欄比對）');
}

// ---- ③ diag：三個變體、30 秒內第二次 429 且不打上游
next = () => new Response('error code: 520\n', { status: 520 });
hits = 0;
{
  const r = await call(worker, 'https://w/fut?session=night&diag=1');
  const j = JSON.parse(r.body);
  ok('diag 回 200 並列出三個變體', r.status === 200 && (j.variants || []).length === 3, j);
  ok('diag 三個變體各打一次上游', hits === 3, hits);
  ok('diag 的變體名稱', (j.variants || []).map(v => v.name).join() === 'as_is,browser_hdr,static_page', j.variants);
  ok('diag 的 static_page 是 GET 首頁', lastReq && lastReq.method === 'GET' && lastReq.url === 'https://mis.taifex.com.tw/futures/', lastReq && lastReq.url);
  hits = 0;
  const r2 = await call(worker, 'https://w/fut?session=night&diag=1');
  ok('diag 30 秒內再叫 → 429', r2.status === 429, r2.status);
  ok('diag 被擋時不打上游', hits === 0, hits);
  hits = 0;
  next = () => new Response('{"RtCode":"0"}', { status: 200 });
  const r3 = await call(worker, 'https://w/fut?session=day&diag=1');
  ok('日盤帶 diag=1 不會進診斷（照一般 /fut 走）', r3.status === 200 && r3.body === '{"RtCode":"0"}' && hits === 1, r3);
}

console.log(fails.length ? `\n${fails.length} 條沒過` : '\n全部通過');
process.exit(fails.length ? 1 : 0);
