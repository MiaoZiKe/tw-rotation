// Worker /stream 的離線驗收：把 fetch 與 caches 換成假的，證明
// ① 值沒變就不推 ② 值變了才推 ③ 每條新連線一定先給完整快照 ④ 4 分鐘會送 bye
import worker from '/home/user/tw-rotation/workers/quote-proxy/worker.js';

// 容器跑 UTC，現在換算成台北是夜間 → sessionNow() 會判 'closed'（給一份快照就收線），
// 那樣就驗不到盤中的推送迴圈。把 Date.now 整個平移到「週二台北 10:00」再驗。
const realNow = Date.now.bind(Date);
const TARGET = Date.UTC(2026, 8, 22, 2, 0, 0);   // 2026-09-22(一) 02:00 UTC = 台北 10:00
const SHIFT = TARGET - realNow();
Date.now = () => realNow() + SHIFT;

let upstreamHits = 0;
let z = '100.0000';
const store = new Map();
globalThis.caches = { default: {
  async match(req){ const v = store.get(req.url); if(!v) return null;
    if (Date.now() > v.exp) { store.delete(req.url); return null; }
    return new Response(v.body); },
  async put(req, res){ const body = await res.text();
    const m = /max-age=(\d+)/.exec(res.headers.get('Cache-Control')||'') ;
    store.set(req.url, { body, exp: Date.now() + (m?+m[1]:0)*1000 }); },
}};
globalThis.fetch = async () => { upstreamHits++;
  return new Response(JSON.stringify({ msgArray:[{c:'2330',n:'台積電',z,y:'900.0000'}],
    rtcode:'0000', queryTime:{sysTime:String(Date.now())}, exKey:'x'+Math.random() }),
    { status:200 }); };

const fails = [];
const ok = (n,c,d='') => { console.log((c?'  OK  ':'  XX  ')+n+(c?'':'   <- '+d)); if(!c) fails.push(n); };

const req = (u) => new Request(u, { headers: { Origin: 'https://miaozike.github.io' } });
const ctx = { waitUntil(){} };

// --- 代號檢查
let r = await worker.fetch(req('https://w/stream?ids=bad'), {}, ctx);
ok('代號格式錯就 400', r.status === 400, r.status);
r = await worker.fetch(req('https://w/stream?ids='+encodeURIComponent(Array(200).fill('tse_2330.tw').join('|'))), {}, ctx);
ok('超過 140 檔就 400', r.status === 400, r.status);
r = await worker.fetch(req('https://w/health'), {}, ctx);
const h = await r.json();
ok('/health 講得出自己支援 stream', (h.features||[]).includes('stream'), h);

// --- 真的開一條
r = await worker.fetch(req('https://w/stream?ids=tse_2330.tw'), {}, ctx);
ok('/stream 回 200', r.status === 200, r.status);
ok('content-type 是 text/event-stream',
   (r.headers.get('content-type')||'').includes('text/event-stream'), r.headers.get('content-type'));
ok('有給 CORS 標頭', r.headers.get('Access-Control-Allow-Origin') === 'https://miaozike.github.io');

const reader = r.body.getReader();
const dec = new TextDecoder();
let buf = '';
// ★ 讀取器只能有一個未完成的 read()：用 Promise.race 又不留著它的話，
// 逾時之後那一筆資料會被丟掉（第一版就是這樣把後面全部驗成紅的）。
let pending = null;
const readFor = async (ms) => { const end = realNow()+ms;
  while (realNow() < end) {
    if (!pending) pending = reader.read();
    const left = end - realNow();
    const t = await Promise.race([pending, new Promise(res=>setTimeout(()=>res({timeout:true}), left))]);
    if (t.timeout) break;
    pending = null;
    if (t.done) break;
    buf += dec.decode(t.value);
  } };

await readFor(1500);
ok('先送 retry 提示', buf.startsWith('retry:'), buf.slice(0,40));
ok('第一則是 hello', buf.includes('event: hello'), buf.slice(0,120));
const q1 = (buf.match(/event: quote/g)||[]).length;
ok('剛連上一定先給一份完整快照', q1 === 1, '收到 '+q1+' 筆');
ok('快照裡有價格', buf.includes('100.0000'));

// 值沒變 → 再等兩輪也不該再推
buf = '';
await readFor(11000);
ok('值沒變就一個 quote 都不推', !buf.includes('event: quote'), buf.slice(0,200));
ok('但心跳有在跑', buf.includes(': hb'), buf.slice(0,80));
const hitsBefore = upstreamHits;

// 值變了 → 要推
z = '123.0000';
buf = '';
await readFor(12000);
ok('值變了就推一筆', (buf.match(/event: quote/g)||[]).length >= 1, buf.slice(0,200));
ok('推的就是新值', buf.includes('123.0000'));
ok('上游有被問到（節流下沒有暴打）', upstreamHits > hitsBefore && upstreamHits - hitsBefore <= 4,
   `這段時間打了 ${upstreamHits-hitsBefore} 次`);

// 多條連線共用上游（邊緣快取）
const before = upstreamHits;
const rs = await Promise.all([1,2,3].map(()=>worker.fetch(req('https://w/stream?ids=tse_2330.tw'), {}, ctx)));
await new Promise(res=>setTimeout(res, 600));
for (const x of rs) { const rd = x.body.getReader(); await rd.read(); await rd.read(); try{ await rd.cancel(); }catch(e){} }
ok('三條新連線共用同一份上游結果（最多只多打一次）', upstreamHits - before <= 1,
   `多打了 ${upstreamHits-before} 次`);

try { await reader.cancel(); } catch(e) {}
console.log(fails.length ? `\n${fails.length} 項沒過 -> ${fails}` : '\n全部通過');
process.exit(fails.length ? 1 : 0);
