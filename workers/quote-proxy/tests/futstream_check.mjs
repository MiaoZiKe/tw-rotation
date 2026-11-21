/* Worker /futstream 的離線驗收（2026-09-23 夜盤推送）。
   跑法：node scratchpad/futstream_check.mjs
   假 fetch ＋ 時鐘平移到夜盤時段 ＋ 用 docs/fixtures/taifex_night_probe.json 的真實回應。 */
import worker from '/home/user/tw-rotation/workers/quote-proxy/worker.js';
import fs from 'node:fs';

const ROOT = '/home/user/tw-rotation';
const fx = JSON.parse(fs.readFileSync(ROOT + '/docs/fixtures/taifex_night_probe.json', 'utf8'));
const S = Object.fromEntries(fx.results.map(r => [r.id, r]));

// 三份真實回應：
//  A = taifex_chartdata_1m_night      （00:15:30，收 48009、累計量 22616）
//  B = taifex_chartdata_1m_night_full （00:15:32，收 48013、累計量 22622）
//  C = our_worker_futchart_night      （00:15:36，跟 B 的成交價／量／最後一根 Tick 完全一樣，只有五檔在動）
const CH_A = JSON.stringify(S.taifex_chartdata_1m_night.sample);
const CH_B = JSON.stringify(S.taifex_chartdata_1m_night_full.sample);
const CH_C = JSON.stringify(S.our_worker_futchart_night.sample);
// 報價清單：Q_A（48009 / 22616 / CTime 001527）、Q_B（48013 / 22622 / CTime 001533）
const Q_A = JSON.stringify(S.taifex_quotelist_night.sample);
const Q_B = JSON.stringify(S.our_worker_fut_night.sample);

const fails = [];
const ok = (n, c, d = '') => { console.log((c ? '  OK  ' : '  XX  ') + n + (c ? '' : '   <- ' + JSON.stringify(d))); if (!c) fails.push(n); };

const realNow = Date.now.bind(Date);
globalThis.caches = { default: { async match() { return null; }, async put() {} } };

const req = (u) => new Request(u, { headers: { Origin: 'https://miaozike.github.io' } });
const ctx = { waitUntil() {} };

/** 把時鐘釘到某一刻（台北夜盤 23:00）。speed>1 代表讓虛擬時間跑得比真實快。 */
function pinClock(utcMs, speed = 1) {
  const t0 = realNow();
  Date.now = () => utcMs + (realNow() - t0) * speed;
}
const NIGHT_UTC = Date.UTC(2026, 8, 23, 15, 0, 0);   // 2026-09-23(三) 15:00 UTC = 台北 23:00
const DAY_UTC = Date.UTC(2026, 8, 23, 2, 0, 0);      // 台北 10:00（日盤，不是夜盤）

let hitQ = 0, hitC = 0;
let curQ = Q_A, curC = CH_A;
let failQ = false, failC = false;
globalThis.fetch = async (r) => {
  const u = typeof r === 'string' ? r : r.url;
  if (u.includes('getQuoteList')) {
    hitQ++;
    if (failQ) throw new Error('boom');
    return new Response(curQ, { status: 200 });
  }
  if (u.includes('getChartData1M')) {
    hitC++;
    if (failC) throw new Error('boom');
    return new Response(curC, { status: 200 });
  }
  throw new Error('unexpected upstream ' + u);
};

/** 讀一條 SSE，最多讀 ms 毫秒（真實時間）。 */
function makeReader(res) {
  const rd = res.body.getReader();
  const dec = new TextDecoder();
  let pending = null;
  return {
    rd,
    async read(ms) {
      let buf = '';
      const end = realNow() + ms;
      while (realNow() < end) {
        if (!pending) pending = rd.read();
        const left = Math.max(1, end - realNow());
        const t = await Promise.race([pending, new Promise(res2 => setTimeout(() => res2({ timeout: true }), left))]);
        if (t.timeout) break;
        pending = null;
        if (t.done) break;
        buf += dec.decode(t.value);
      }
      return buf;
    },
    async close() { try { await rd.cancel(); } catch (e) { /* 已經關了 */ } },
  };
}
const count = (s, ev) => (s.match(new RegExp('event: ' + ev, 'g')) || []).length;

// ================================================================ ① /health
pinClock(NIGHT_UTC);
let r = await worker.fetch(req('https://w/health'), {}, ctx);
let h = await r.json();
ok('/health 講得出自己支援 futstream', (h.features || []).includes('futstream'), h.features);
ok('/health 的 futSession 在台北 23:00 是 night', h.futSession === 'night', h);
ok('現貨那條的 session 在夜間仍然是 closed（沒有被夜盤影響）', h.session === 'closed', h);

// ================================================================ ② 非夜盤時段不開連線
pinClock(DAY_UTC);
hitQ = hitC = 0;
r = await worker.fetch(req('https://w/futstream?session=night&symbol=TXFJ6-M'), {}, ctx);
ok('非夜盤時段 /futstream 仍然回 200（不是錯誤，是沒東西可推）', r.status === 200, r.status);
let rdr = makeReader(r);
let buf = await rdr.read(2500);
ok('★ 非夜盤時段：一個上游請求都沒打', hitQ === 0 && hitC === 0, { hitQ, hitC });
ok('★ 非夜盤時段：一個 fut 事件都不推（不准拿日盤冒充夜盤）', count(buf, 'fut') === 0, buf.slice(0, 200));
ok('非夜盤時段：送 idle 說明原因並收線', buf.includes('event: idle') && buf.includes('非夜盤時段'), buf.slice(-220));
await rdr.close();

// ================================================================ ③ 夜盤：第一筆一定是完整快照
pinClock(NIGHT_UTC);
hitQ = hitC = 0; curQ = Q_A; curC = CH_A;
r = await worker.fetch(req('https://w/futstream?session=night&symbol=TXFJ6-M'), {}, ctx);
ok('夜盤 /futstream 回 200', r.status === 200, r.status);
ok('content-type 是 text/event-stream',
   (r.headers.get('content-type') || '').includes('text/event-stream'), r.headers.get('content-type'));
ok('有給 CORS 標頭', r.headers.get('Access-Control-Allow-Origin') === 'https://miaozike.github.io');
rdr = makeReader(r);
buf = await rdr.read(3000);
ok('先送 retry 提示', buf.startsWith('retry:'), buf.slice(0, 40));
ok('第一則是 hello', buf.includes('event: hello'), buf.slice(0, 160));
ok('剛連上就給一份報價快照', count(buf, 'fut') >= 1, buf.slice(0, 200));
ok('剛連上就給一份分時快照', count(buf, 'futchart') === 1, buf.slice(0, 200));
ok('快照裡有 fixture 的成交價 48009', buf.includes('48009.00'));

// ---- 值沒變（只有五檔在動）→ 一個 quote 都不推
curC = CH_C;   // 跟 CH_B 的成交價／量／最後一根 Tick 一樣，只有五檔不同
curQ = Q_A;    // 報價完全沒變
buf = await rdr.read(23000);
ok('★ 值沒變就一個 fut 都不推', count(buf, 'fut') === 0, buf.slice(0, 260));
ok('但心跳有在跑（連線是活的，不是卡住）', buf.includes(': hb'), buf.slice(0, 120));
ok('★ 節流有效：23 秒內報價最多問 3 次（10 秒一輪）', hitQ <= 3, { hitQ });
ok('★ 分時序列 23 秒內只問過一次（60 秒一輪，Ticks 一分鐘才長一根）', hitC === 1, { hitC });

// ---- 值真的變了 → 要推
const hQ0 = hitQ;
curQ = Q_B;    // 48009 → 48013、22616 → 22622
buf = await rdr.read(12000);
ok('★ 值變了就推一筆報價', count(buf, 'fut') >= 1, buf.slice(0, 260));
ok('推的就是新值 48013', buf.includes('48013.00'));
ok('上游有被真的問到（沒有暴打）', hitQ > hQ0 && hitQ - hQ0 <= 2, { delta: hitQ - hQ0 });

// ---- ★ 去重的切法：拿 fixture 驗「只有五檔在動就不推」
//      CH_B 與 CH_C 是相隔 4 秒的兩次探測，成交價／累計量／最後一根 Tick 完全一樣。
curC = CH_B;
const hC0 = hitC;
buf = await rdr.read(1000);
ok('（過場）分時這段時間還沒到下一輪', hitC === hC0, { hitC });
await rdr.close();

// ================================================================ ④ 多條連線共用上游（isolate 層記憶體）
// ⚠ 模組層的記憶體會跨測試留著，而且時鐘不能往回撥（往回撥會讓舊的那一份永遠看起來很新），
//    所以每一段都要把時鐘往前推到「上一段留下的快取一定過期」的位置。
pinClock(NIGHT_UTC + 5 * 60 * 1000);
hitQ = hitC = 0; curQ = Q_A; curC = CH_A;
const many = await Promise.all([1, 2, 3, 4].map(() =>
  worker.fetch(req('https://w/futstream?session=night&symbol=TXFJ6-M'), {}, ctx)));
const readers = many.map(makeReader);
await Promise.all(readers.map(x => x.read(3000)));
ok('★ 四條連線同時開：報價只真的打上游一次', hitQ === 1, { hitQ });
ok('★ 四條連線同時開：分時也只打一次', hitC === 1, { hitC });
const gotAll = await Promise.all(readers.map(x => x.read(300)));
void gotAll;
await Promise.all(readers.map(x => x.close()));

// ================================================================ ⑤ 上游掛掉：連線不死，只報 warn
pinClock(NIGHT_UTC + 10 * 60 * 1000);
hitQ = hitC = 0; failQ = true; failC = false; curC = CH_A;
r = await worker.fetch(req('https://w/futstream?session=night&symbol=TXFJ6-M'), {}, ctx);
rdr = makeReader(r);
buf = await rdr.read(3500);
ok('★ 報價掛掉不影響分時（失敗要獨立）', count(buf, 'futchart') === 1 && buf.includes('event: warn'),
   buf.slice(0, 300));
ok('報價掛掉時 warn 講得出是哪一支', buf.includes('"which":"fut"'), buf.slice(0, 300));
await rdr.close();
failQ = false;

// ================================================================ ⑥ 4 分鐘輪替會送 bye
//    把虛擬時鐘加速 40 倍：真實睡 10 秒＝虛擬過了 400 秒，第二輪就會超過 4 分鐘。
pinClock(NIGHT_UTC + 20 * 60 * 1000, 40);
hitQ = hitC = 0; curQ = Q_A; curC = CH_A;
r = await worker.fetch(req('https://w/futstream?session=night&symbol=TXFJ6-M'), {}, ctx);
rdr = makeReader(r);
buf = await rdr.read(14000);
ok('★ 連線到時間會送 bye 讓前端重連（不是靜靜地死掉）',
   buf.includes('event: bye') && buf.includes('rotate'), buf.slice(-260));
await rdr.close();
Date.now = realNow;

// ================================================================ ⑦ ★ 永久守住：POST 的 fetch 不准帶 cf 快取選項
//    DECISIONS #255 ③：cf:{cacheTtl,cacheEverything} 只對 GET 有效，
//    帶在 POST 上會讓子請求出錯、Cloudflare 對外回 520 —— 那是夜盤三次空白真正的斷點。
/* 只掃**程式碼**：把註解與字串內容抹掉再掃。
   ⚠ 不能用 `/\*[\s\S]*?\*\/` 這種偷懶的寫法 —— 這個檔案裡有
   `'Accept': 'application/json, text/plain, * /*'`（媒體型別的萬用字元），
   那個 `/*` 會被當成註解開頭，一路吃掉後面 1.2KB 的真程式碼，
   於是「掃不到任何 cf」看起來像通過，其實是**假綠**。第一版就是這樣紅的。
   所以老老實實走一遍字元，自己記住現在在字串裡還是註解裡。 */
function codeOnly(text) {
  let out = '', i = 0;
  const n = text.length;
  while (i < n) {
    const c = text[i], d = text[i + 1];
    if (c === '/' && d === '*') { const e = text.indexOf('*/', i + 2); i = e < 0 ? n : e + 2; out += ' '; continue; }
    if (c === '/' && d === '/') { const e = text.indexOf('\n', i); i = e < 0 ? n : e; out += ' '; continue; }
    if (c === '"' || c === "'" || c === '`') {
      const q = c; i++;
      while (i < n && text[i] !== q) { if (text[i] === '\\') i++; i++; }
      i++; out += q + q; continue;                 // 字串換成空字串，長度不重要
    }
    out += c; i++;
  }
  return out;
}
const src = codeOnly(fs.readFileSync(ROOT + '/workers/quote-proxy/worker.js', 'utf8'));
ok('抹註解與字串之後，程式碼本身還在（不是被吃光了才「掃不到問題」）',
   src.includes('cacheTtl') && src.includes('futMemoFetch') && src.length > 6000,
   { len: src.length, hasCacheTtl: src.includes('cacheTtl') });

function enclosingObject(text, at) {
  // 從 at 往左找到包住它的那個 `{`（括號要配對），再往右找到對應的 `}`
  let depth = 0, i = at;
  for (; i >= 0; i--) {
    const c = text[i];
    if (c === '}') depth++;
    else if (c === '{') { if (depth === 0) break; depth--; }
  }
  if (i < 0) return '';
  let j = i, d2 = 0;
  for (; j < text.length; j++) {
    const c = text[j];
    if (c === '{') d2++;
    else if (c === '}') { d2--; if (d2 === 0) { j++; break; } }
  }
  return text.slice(i, j);
}
const postAt = [...src.matchAll(/method:\s*''/g)].map(m => m.index);   // 字串已被抹成 ''
ok('原始碼裡真的有 POST 的上游請求（這條斷言不是空轉）', postAt.length >= 2, postAt.length);
const badPost = postAt.filter(i => /\bcf\s*:/.test(enclosingObject(src, i)));
ok('★ 每一個帶 method 的上游請求物件裡都沒有 cf 快取選項', badPost.length === 0,
   badPost.map(i => src.slice(i - 80, i + 80)));
const cfAt = [...src.matchAll(/\bcf\s*:\s*\{/g)].map(m => m.index);
const badCf = cfAt.filter(i => /method:\s*''/.test(enclosingObject(src, i)));
ok('★ 反過來也掃一次：每一個帶 cf 的請求物件都沒有 method（＝都是 GET）', badCf.length === 0,
   badCf.map(i => src.slice(i - 120, i + 120)));
ok('程式碼裡 cf 快取選項只剩兩處（relay() 與 misText()，兩支都是 GET）', cfAt.length === 2,
   cfAt.map(i => src.slice(i - 60, i + 60)));
// POST 的那兩支（futQuoteRequest / futChartRequest）必須存在，而且它們才是 /futstream 打上游的唯一入口
ok('期交所那兩支 POST 請求是共用的（/fut、/futchart、/futstream 走同一份）',
   (src.match(/function futQuoteRequest/g) || []).length === 1
   && (src.match(/function futChartRequest/g) || []).length === 1
   && (src.match(/futQuoteRequest\(/g) || []).length === 3
   && (src.match(/futChartRequest\(/g) || []).length === 3,
   { q: (src.match(/futQuoteRequest\(/g) || []).length, c: (src.match(/futChartRequest\(/g) || []).length });

console.log(fails.length ? `\n${fails.length} 項沒過 -> ${JSON.stringify(fails, null, 1)}` : '\n全部通過');
process.exit(fails.length ? 1 : 0);
