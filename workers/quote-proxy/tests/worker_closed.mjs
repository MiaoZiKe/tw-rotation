// 非交易時段：Worker 應該給一份快照就送 idle 收線，不要空轉
import worker from '/home/user/tw-rotation/workers/quote-proxy/worker.js';
const realNow = Date.now.bind(Date);
const SHIFT = Date.UTC(2026, 8, 20, 12, 0, 0) - realNow();   // 2026-09-20 週日
Date.now = () => realNow() + SHIFT;
globalThis.caches = { default: { async match(){ return null; }, async put(){} } };
let hits = 0;
globalThis.fetch = async () => { hits++; return new Response(JSON.stringify(
  { msgArray:[{c:'2330',n:'台積電',z:'100',y:'90'}], rtcode:'0000', queryTime:{} }), {status:200}); };
const r = await worker.fetch(new Request('https://w/stream?ids=tse_2330.tw',
  { headers:{ Origin:'https://miaozike.github.io' } }), {}, { waitUntil(){} });
let buf = '', t0 = realNow();
for await (const c of r.body) buf += new TextDecoder().decode(c);
const fails = [];
const ok = (n,c,d='') => { console.log((c?'  OK  ':'  XX  ')+n+(c?'':'   <- '+d)); if(!c) fails.push(n); };
ok('非交易時段仍給一份快照', buf.includes('event: quote'));
ok('然後送 idle 說明原因', buf.includes('event: idle') && buf.includes('非交易時段'), buf.slice(-200));
ok('串流自己收掉（不空轉）', realNow()-t0 < 3000, (realNow()-t0)+'ms');
ok('只問上游一次', hits === 1, hits);
console.log(fails.length ? `\n${fails.length} 項沒過` : '\n全部通過');
process.exit(fails.length?1:0);
