/* 每日額度（Plus 50／Pro 不限，docs/quota_plan.md）的允許／拒絕驗收。跑法：node --test workers/data-gw/tests/
 * 「一次」＝同一天（台北日期）、同一個單位只算一次；單位由檔名決定（unitOf，tiers.js）。
 * 限流與爆量門檻調高到測不到，只驗額度本身。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeGw, fakeR2 } from '../harness.mjs';
import { unitOf } from '../tiers.js';
import { tpeDay, tpeReset } from '../worker.js';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-data-gw.example.workers.dev';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130';
const DEV = 'dev-aaaaaaaaaaaaaaaa';

/* 假 account-api：dq＝範本的每日額度（Plus 50、Pro 沒有這個欄位＝不限）*/
const PEOPLE = {
  'v1.uPlus.9.1.s': { user: { email: 'plus@example.com', admin: false }, plan: 'plus', feats: {}, dq: 50 },
  'v1.uPro.9.1.s': { user: { email: 'pro@example.com', admin: false }, plan: 'pro', feats: {} },
  'v1.uAdm.9.1.s': { user: { email: 'andy@example.com', admin: true }, plan: 'plus', feats: {}, dq: 50 },
  'v1.uTiny.9.1.s': { user: { email: 'tiny@example.com', admin: false }, plan: 'plus', feats: {}, dq: 2 },
  'v1.uLim.9.1.s': { user: { email: 'lim@example.com', admin: false }, plan: 'free', feats: {}, lims: { 'stock.page': 2, 'stock.k_hour': 1, 'stock.k_day': 0 } },
};
const ACCOUNT = { async fetch(r) {
  const b = JSON.parse(await r.text()), path = new URL(r.url).pathname, who = PEOPLE[b.t];
  if (path === '/v1/perm/me' && !b.t) return Response.json({ who: 'guest', plan: 'guest', feats: {} });
  if (!who) return Response.json({ error: 'auth' }, { status: 401 });
  if (path === '/v1/me') return Response.json({ user: who.user });
  const j = { who: 'member', plan: who.plan, feats: who.feats, lims: who.lims || {} };
  if (who.dq !== undefined) j.dq = who.dq;
  return Response.json(j);
} };

const CODES = Array.from({ length: 60 }, (_, i) => String(1101 + i));
let clock = Date.parse('2026-10-06T04:00:00Z');   // 台北 12:00
function setup() {
  const files = { 'meta.json': {}, 'flow_v3.json': { a: 1 }, 'rrg_members.json': { a: 1 }, 'sankey_daily.json': { a: 1 } };
  CODES.forEach((c) => { files[`stock/${c}.json`] = { code: c }; files[`m60/${c}.json`] = { c }; files[`hist/${c}/p0.json`] = { p: 0 }; files[`hist/${c}/p1.json`] = { p: 1 }; });
  return makeGw({ ALLOWED_ORIGINS: ORIGIN, GW_SECRET: 's', ACCOUNT, DATA: fakeR2(files), RATE_PER_MIN: '9999', BURST_FILES: '9999', __now: () => clock }).gw;
}
const H = (o = {}) => ({ 'User-Agent': UA, 'Sec-Fetch-Mode': 'cors', 'CF-Connecting-IP': '203.0.113.7', Origin: ORIGIN, ...o });
const get = (gw, name, tok) => gw.fetch(new Request(API + '/v1/data/' + name, { headers: H({ Authorization: 'Bearer ' + tok, 'X-Device': DEV }) }));
async function sess(gw, t) {
  const r = await gw.fetch(new Request(API + '/v1/session', { method: 'POST', headers: H(), body: JSON.stringify({ t, d: DEV }) }));
  return r.json();
}

test('單位：個股頁的 stock／m60／hist 同一個單位；同一分頁的多支檔同一個單位；免費檔不算', () => {
  assert.equal(unitOf('stock/2330'), '2330');
  assert.equal(unitOf('m60/2330'), '2330');
  assert.equal(unitOf('hist/2330/p7'), '2330');
  assert.equal(unitOf('flow_v3'), 'p.flow.rot');
  assert.equal(unitOf('rrg_members'), 'p.flow.rot');
  assert.equal(unitOf('meta'), null);
  assert.equal(unitOf('stocks'), null);
});

test('Plus 50 次：第 50 個新單位放行、第 51 個擋（429 quota，帶 used／limit／reset）', async () => {
  const gw = setup();
  const s = await sess(gw, 'v1.uPlus.9.1.s');
  assert.deepEqual(s.quota, { used: 0, limit: 50, reset: tpeReset(clock) }, 'session 回目前額度');
  for (let i = 0; i < 50; i++) assert.equal((await get(gw, `stock/${CODES[i]}`, s.tok)).status, 200, `第 ${i + 1} 檔`);
  const r = await get(gw, `stock/${CODES[50]}`, s.tok);
  assert.equal(r.status, 429);
  const j = await r.json();
  assert.equal(j.error, 'quota'); assert.equal(j.used, 50); assert.equal(j.limit, 50); assert.equal(j.plan, 'plus');
  assert.equal(j.reset, Date.parse('2026-10-06T16:00:00Z'), '重置＝下一個台北 00:00（UTC 16:00）');
  const q = await (await gw.fetch(new Request(API + '/v1/quota', { headers: H({ Authorization: 'Bearer ' + s.tok, 'X-Device': DEV }) }))).json();
  assert.equal(q.used, 50); assert.equal(q.limit, 50);
});

test('同一單位重看不扣：同一檔的分頁／K 線翻頁／1H 不另外扣；額度滿了之後重看今天看過的照樣放行', async () => {
  const gw = setup();
  const s = await sess(gw, 'v1.uTiny.9.1.s');   // 每日 2 次
  for (const n of ['stock/1101', 'm60/1101', 'hist/1101/p0', 'hist/1101/p1', 'stock/1101']) assert.equal((await get(gw, n, s.tok)).status, 200, n);
  let r = await get(gw, 'stock/1102', s.tok);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('x-quota').split('/').slice(0, 2).join('/'), '2/2', '第 2 個單位之後標頭寫 2/2');
  r = await get(gw, 'stock/1103', s.tok);
  assert.equal(r.status, 429, '第 3 個新單位擋');
  assert.equal((await get(gw, 'stock/1101', s.tok)).status, 200, '已看過的照樣放行');
  assert.equal((await get(gw, 'hist/1102/p1', s.tok)).status, 200, '已看過那檔的 K 線翻頁照樣放行');
  assert.equal((await get(gw, 'meta', s.tok)).status, 200, '免費檔不受額度影響');
  // 同一分頁的多支檔只算一次
  const gw2 = setup(); const s2 = await sess(gw2, 'v1.uTiny.9.1.s');
  for (const n of ['flow_v3', 'rrg_members', 'flow_v3']) assert.equal((await get(gw2, n, s2.tok)).status, 200, n);
  assert.equal((await get(gw2, 'sankey_daily', s2.tok)).status, 200, '第 2 個單位');
  assert.equal((await get(gw2, 'stock/1101', s2.tok)).status, 429, '第 3 個單位');
});

test('台北 00:00 重置：23:59 還是擋，00:00 起放行並重新計數', async () => {
  const gw = setup();
  clock = Date.parse('2026-10-06T15:58:00Z');   // 台北 23:58
  const s = await sess(gw, 'v1.uTiny.9.1.s');
  await get(gw, 'stock/1101', s.tok); await get(gw, 'stock/1102', s.tok);
  clock = Date.parse('2026-10-06T15:59:30Z');   // 台北 23:59:30（權杖 5 分鐘內還有效）
  assert.equal((await get(gw, 'stock/1103', s.tok)).status, 429);
  clock = Date.parse('2026-10-06T16:00:00Z');   // 台北 10/07 00:00
  assert.equal(tpeDay(clock), '2026-10-07');
  const r = await get(gw, 'stock/1103', s.tok);
  assert.equal(r.status, 200, '換日放行');
  assert.equal(r.headers.get('x-quota').split('/').slice(0, 2).join('/'), '1/2', '新的一天從 1 開始');
  clock = Date.parse('2026-10-06T04:00:00Z');
});

test('Pro（範本沒有額度）與管理者不限：60 個單位全部放行、沒有 x-quota 標頭', async () => {
  for (const t of ['v1.uPro.9.1.s', 'v1.uAdm.9.1.s']) {
    const gw = setup();
    const s = await sess(gw, t);
    assert.equal(s.quota.limit, null, t);
    let last;
    for (const c of CODES) { last = await get(gw, `stock/${c}`, s.tok); assert.equal(last.status, 200, `${t} ${c}`); }
    assert.equal(last.headers.get('x-quota'), null);
  }
});

test('功能各自的每日次數（lims）：個股頁 2 檔、1H 1 檔、日 K 0＝不能看；單位＝股票代號（跟前端 quota.js 同一組字串）', async () => {
  const gw = setup();
  const s = await sess(gw, 'v1.uLim.9.1.s');
  assert.equal((await get(gw, 'stock/1101', s.tok)).status, 200);
  assert.equal((await get(gw, 'stock/1101', s.tok)).status, 200, '同一檔重看');
  assert.equal((await get(gw, 'stock/1102', s.tok)).status, 200, '第 2 檔');
  let r = await get(gw, 'stock/1103', s.tok);
  assert.equal(r.status, 429); let j = await r.json();
  assert.equal(j.feat, 'stock.page'); assert.equal(j.limit, 2);
  assert.equal((await get(gw, 'm60/1101', s.tok)).status, 200, '1H 第 1 檔（看過的個股）');
  r = await get(gw, 'm60/1102', s.tok);
  assert.equal(r.status, 429); j = await r.json(); assert.equal(j.feat, 'stock.k_hour');
  r = await get(gw, 'hist/1101/p0', s.tok);
  assert.equal(r.status, 403, '日 K 上限 0＝不能看'); assert.equal((await r.json()).error, 'plan');
  assert.equal((await get(gw, 'flow_v3', s.tok)).status, 200, '沒有對象的付費檔不受功能次數影響（伺服器分不出單位，前端計數）');
});
