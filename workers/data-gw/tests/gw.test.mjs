/* data-gw 的允許／拒絕驗收。跑法：node --test workers/data-gw/tests/
 * 不連外網：account-api 用假的 service binding（依登入權杖回固定的身分與方案），R2 用記憶體。
 * 每條規則同時驗「該擋的有擋」與「該放的有放」。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeGw, fakeR2 } from '../harness.mjs';
import { wmOf, ipNet } from '../worker.js';
import { tierOf } from '../tiers.js';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-data-gw.example.workers.dev';
const SECRET = 'test-secret-not-real';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130';
const DEV = 'dev-aaaaaaaaaaaaaaaa', DEV2 = 'dev-bbbbbbbbbbbbbbbb';

/* 假 account-api：權杖 v1.<uid>.<exp>.<tv>.<sig> 的 uid 決定身分 */
const PEOPLE = {
  'v1.uPaid.9.1.s': { user: { email: 'paid@example.com', admin: false }, plan: 'paid', feats: {} },
  'v1.uFree.9.1.s': { user: { email: 'free@example.com', admin: false }, plan: 'free', feats: { 'stock.overview': false, 'flow.rot': false } },
  'v1.uAdm.9.1.s': { user: { email: 'andy@example.com', admin: true }, plan: 'paid', feats: {} },
};
const GUEST = { 'stock.overview': false, 'flow.rot': false, 'ind.map': false };
const ACCOUNT = { async fetch(r) {
  const b = JSON.parse(await r.text()), path = new URL(r.url).pathname, who = PEOPLE[b.t];
  if (path === '/v1/perm/me' && !b.t) return Response.json({ who: 'guest', plan: 'guest', feats: GUEST });
  if (!who) return Response.json({ error: 'auth' }, { status: 401 });
  if (path === '/v1/me') return Response.json({ user: who.user });
  return Response.json({ who: 'member', plan: who.plan, feats: who.feats });
} };

let clock = Date.parse('2026-10-06T04:00:00Z');
function setup(extra = {}) {
  const DATA = fakeR2({ 'meta.json': { generated_at: 'x' }, 'stock/2330.json': { code: '2330', px: [1, 2] }, 'flow_v3.json': [{ g: 'a' }, { g: 'b' }],
    ...Object.fromEntries(Array.from({ length: 40 }, (_, i) => [`hist/2330/p${i}.json`, { p: i }])) });
  return makeGw({ ALLOWED_ORIGINS: ORIGIN, GW_SECRET: SECRET, ACCOUNT, DATA, __now: () => clock, ...extra }).gw;
}
const H = (o = {}) => ({ 'User-Agent': UA, 'Sec-Fetch-Mode': 'cors', 'CF-Connecting-IP': '203.0.113.7', Origin: ORIGIN, ...o });
const post = (gw, path, body, h = {}) => gw.fetch(new Request(API + path, { method: 'POST', headers: H(h), body: JSON.stringify(body) }));
const get = (gw, name, tok, h = {}) => gw.fetch(new Request(API + '/v1/data/' + name, { headers: H(tok ? { Authorization: 'Bearer ' + tok, 'X-Device': DEV, ...h } : h) }));
async function sess(gw, t, d = DEV) { const r = await post(gw, '/v1/session', { t, d }); return { r, j: await r.json() }; }

test('白名單：不在表上、路徑穿越、delivery 一律 404', async () => {
  const gw = setup();
  for (const n of ['delivery', '../secret', 'stock/../../x', 'unknown', 'stock/2330/../../a']) assert.equal((await get(gw, n)).status, 404, n);
  assert.equal(tierOf('stock/2330').feats[0], 'stock.overview');
});

test('免費檔：未登入直接拿得到', async () => {
  const r = await get(setup(), 'meta');
  assert.equal(r.status, 200);
  assert.equal((await r.json()).generated_at, 'x');
});

test('未登入拿付費檔被擋（401 login）', async () => {
  const r = await get(setup(), 'stock/2330');
  assert.equal(r.status, 401);
  assert.equal((await r.json()).error, 'login');
});

test('session：沒有／假的登入權杖、壞的裝置 id、別的網站發出 → 拒絕', async () => {
  const gw = setup();
  assert.equal((await sess(gw, '')).r.status, 401);
  assert.equal((await sess(gw, 'v1.nobody.9.1.s')).r.status, 401);
  assert.equal((await sess(gw, 'v1.uPaid.9.1.s', 'x')).r.status, 400);
  assert.equal((await post(gw, '/v1/session', { t: 'v1.uPaid.9.1.s', d: DEV }, { Origin: 'https://evil.example' })).status, 403);
});

test('免費會員拿不到付費檔（403 plan），付費會員拿得到', async () => {
  const gw = setup();
  const f = await sess(gw, 'v1.uFree.9.1.s');
  assert.equal(f.r.status, 200);
  const rf = await get(gw, 'stock/2330', f.j.tok);
  assert.equal(rf.status, 403); assert.equal((await rf.json()).error, 'plan');
  const p = await sess(gw, 'v1.uPaid.9.1.s');
  const rp = await get(gw, 'stock/2330', p.j.tok);
  assert.equal(rp.status, 200);
  assert.deepEqual((await rp.json()).px, [1, 2]);
});

test('資料權杖：竄改、換裝置、過期（5 分鐘）→ 401', async () => {
  const gw = setup();
  const { j } = await sess(gw, 'v1.uPaid.9.1.s');
  assert.equal((await get(gw, 'stock/2330', j.tok.slice(0, -2) + 'xx')).status, 401);
  assert.equal((await get(gw, 'stock/2330', j.tok, { 'X-Device': DEV2 })).status, 401);
  const t0 = clock; clock += 301000;
  assert.equal((await get(gw, 'stock/2330', j.tok)).status, 401);
  clock = t0;
});

test('浮水印：物件有 _wm（帳號雜湊＋時間），陣列放在第一個元素；反查得到是誰', async () => {
  const gw = setup();
  const { j } = await sess(gw, 'v1.uPaid.9.1.s');
  const r = await get(gw, 'stock/2330', j.tok), d = await r.json();
  assert.equal(d._wm.a, await wmOf(SECRET, 'uPaid'));
  assert.equal(d._wm.t, Math.floor(clock / 1000));
  assert.ok(r.headers.get('x-wm').startsWith(d._wm.a));
  assert.ok(!JSON.stringify(d).includes('paid@example.com'), '浮水印不可以是明文 email');
  const a = await (await get(gw, 'flow_v3', j.tok)).json();
  assert.ok(Array.isArray(a) && a[0]._wm && a.length === 2);
});

test('每帳號每分鐘限流：超過回 429，下一分鐘恢復', async () => {
  const gw = setup({ RATE_PER_MIN: '5' });
  const { j } = await sess(gw, 'v1.uPaid.9.1.s');
  for (let i = 0; i < 5; i++) assert.equal((await get(gw, 'stock/2330', j.tok)).status, 200);
  assert.equal((await get(gw, 'stock/2330', j.tok)).status, 429);
  clock += 60000;
  assert.equal((await get(gw, 'stock/2330', j.tok)).status, 200);
});

test('每次發放都寫紀錄（帳號、檔名、IP 網段、UA、時間），不存完整 IP', async () => {
  const gw = setup();
  const { j } = await sess(gw, 'v1.uPaid.9.1.s');
  await get(gw, 'stock/2330', j.tok);
  const row = gw.q('SELECT * FROM log WHERE uid = ?', 'uPaid')[0];
  assert.equal(row.name, 'stock/2330'); assert.equal(row.ip, '203.0.113.x'); assert.equal(row.ua, UA); assert.equal(row.ts, clock);
  assert.equal(ipNet('2001:db8:1:2::5'), '2001:db8:1::/48');
});

test('異常：大量抓、多 IP、非瀏覽器 → 記錄＋標記，但不停權（仍然拿得到）', async () => {
  const gw = setup({ BURST_FILES: '30', RATE_PER_MIN: '1000' });
  const { j } = await sess(gw, 'v1.uPaid.9.1.s');
  for (let i = 0; i < 31; i++) await get(gw, `hist/2330/p${i}`, j.tok);
  await get(gw, 'stock/2330', j.tok, { 'CF-Connecting-IP': '198.51.100.1' });
  await get(gw, 'stock/2330', j.tok, { 'CF-Connecting-IP': '192.0.2.1' });
  const r = await get(gw, 'stock/2330', j.tok, { 'User-Agent': 'python-requests/2.32', 'Sec-Fetch-Mode': '' });
  assert.equal(r.status, 200, '第一階段只記錄、不自動停權');
  const kinds = gw.q('SELECT kind FROM alerts WHERE uid = ?', 'uPaid').map((x) => x.kind).sort();
  assert.deepEqual(kinds, ['bot_ua', 'burst', 'multi_ip']);
  const f = gw.q('SELECT n FROM flags WHERE uid = ?', 'uPaid')[0];
  assert.equal(f.n, 3);
  // 正常使用者不被標記
  const p2 = await sess(gw, 'v1.uAdm.9.1.s');
  for (let i = 0; i < 5; i++) await get(gw, 'stock/2330', p2.j.tok);
  assert.equal(gw.q('SELECT COUNT(*) AS c FROM alerts WHERE uid = ?', 'uAdm')[0].c, 0);
});

test('管理者看異常：只有 account-api 認定的管理者可以', async () => {
  const gw = setup();
  assert.equal((await post(gw, '/v1/admin/alerts', {})).status, 401);
  assert.equal((await post(gw, '/v1/admin/alerts', { t: 'v1.uPaid.9.1.s' })).status, 403);
  const r = await post(gw, '/v1/admin/alerts', { t: 'v1.uAdm.9.1.s' });
  assert.equal(r.status, 200); assert.ok(Array.isArray((await r.json()).alerts));
});

test('分級表兩份一致：tiers.js ＝ pipeline/datagw_tiers.json（pipeline 搬檔、前端判斷都讀後者）', async () => {
  const { readFileSync } = await import('node:fs');
  const { TIERS } = await import('../tiers.js');
  const j = JSON.parse(readFileSync(new URL('../../../pipeline/datagw_tiers.json', import.meta.url), 'utf8')).tiers;
  assert.deepEqual(TIERS.map(([k, f]) => (typeof k === 'string' ? { p: k, f } : { re: k.source, f })), j);
});

test('T4 自動停權預設關閉：累計 3 次只記 would_suspend，仍然拿得到；開啟後記 suspend', async () => {
  for (const [auto, kind] of [['0', 'would_suspend'], ['1', 'suspend']]) {
    const gw = setup({ BURST_FILES: '2', MAX_IPS: '9', RATE_PER_MIN: '1000', AUTO_SUSPEND: auto });
    let { j } = await sess(gw, 'v1.uPaid.9.1.s');
    const t0 = clock;
    for (let round = 0; round < 3; round++) {
      for (let i = 0; i < 3; i++) await get(gw, `hist/2330/p${round * 3 + i}`, j.tok);
      clock += 4 * 60000;          // 權杖 5 分鐘到期 → 換一張
      j = (await sess(gw, 'v1.uPaid.9.1.s')).j;
      clock += 7 * 60000;          // 同種異常 10 分鐘只記一筆
      j = (await sess(gw, 'v1.uPaid.9.1.s')).j;
    }
    assert.equal(gw.q('SELECT COUNT(*) AS c FROM alerts WHERE kind = ?', kind)[0].c, 1, kind);
    assert.equal((await get(gw, 'stock/2330', j.tok)).status, 200);
    clock = t0;
  }
});

test('沒設 GW_SECRET → 503，不會用空金鑰簽權杖', async () => {
  const gw = setup({ GW_SECRET: '' });
  assert.equal((await get(gw, 'meta')).status, 503);
  assert.equal((await gw.fetch(new Request(API + '/health'))).status, 200);
});
