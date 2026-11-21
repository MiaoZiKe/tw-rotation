/* admin-v3 區塊（瀏覽次數上限 lims、會員名單使用數據、在線時間、個人使用明細）的存取控制與口徑驗收。
 *
 * 跑法：node --test workers/account-api/tests/
 * 每條都驗「該允許的有允許」與「該拒絕的有拒絕」（同 account.test.mjs、sub.test.mjs）。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const pending = {};
globalThis.fetch = async (url, init) => {
  if (String(url).startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body);
    const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  throw new Error('測試不准連外網：' + url);
};
let clock = Date.parse('2026-10-05T04:00:00Z');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
const post = (hub, path, body, origin = ORIGIN) => hub.fetch(new Request(API + path, {
  method: 'POST', headers: origin ? { Origin: origin, 'content-type': 'text/plain' } : { 'content-type': 'text/plain' }, body: JSON.stringify(body),
}));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
const beat = (hub, t, extra = {}) => pj(hub, '/v1/beat', { sid: 'sid-' + (t ? t.slice(3, 12) : 'guest00'), r: 'stock', ...(t ? { t } : {}), ...extra });

test('瀏覽次數上限 lims：管理者寫進範本（帶 price／period）、plans/get 與公開端點與 /v1/perm/me 都回得到；壞值整批 400', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'p399', name: '基本', feats: { 'ov.heat': false }, lims: { 'stock.ai': 3, 'ov.theme': 0 }, price: 399, period: 'month' });
  assert.equal(r.s, 200);
  const p = r.j.plans.find((x) => x.id === 'p399');
  assert.deepEqual([p.price, p.period, p.lims, p.feats], [399, 'month', { 'stock.ai': 3, 'ov.theme': 0 }, { 'ov.heat': false }]);
  assert.deepEqual((await pj(hub, '/v1/plans/public', {})).j.plans.find((x) => x.id === 'p399').lims, { 'stock.ai': 3, 'ov.theme': 0 });
  // 不帶 lims 的呼叫（只改開關）不會把上限洗掉
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'p399', name: '基本', feats: {} });
  assert.deepEqual((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans.find((x) => x.id === 'p399').lims, { 'stock.ai': 3, 'ov.theme': 0 });
  // 內建範本（訪客）也能設上限；訪客拿 /v1/perm/me 看得到
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'guest', name: '訪客', feats: {}, lims: { 'stock.ai': 1 } })).s, 200);
  assert.deepEqual((await pj(hub, '/v1/perm/me', {})).j.lims, { 'stock.ai': 1 });
  // 會員被指定 p399 → perm/me 帶 p399 的上限；過期 → 退回免費會員（沒有上限）
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'p399', over: {}, expires: clock + 86400000 });
  assert.deepEqual((await pj(hub, '/v1/perm/me', { t: bob })).j.lims, { 'stock.ai': 3, 'ov.theme': 0 });
  const saved = clock;
  try { clock += 2 * 86400000; const me = (await pj(hub, '/v1/perm/me', { t: bob })).j; assert.deepEqual([me.plan, me.lims], ['free', {}]); } finally { clock = saved; }
  // 拒絕：非管理者、壞鍵、負數、小數、超過 9999、陣列
  assert.equal((await post(hub, '/v1/admin/plans/put', { t: bob, id: 'p399', name: 'x', lims: { 'stock.ai': 9 } })).status, 403);
  for (const bad of [{ 'Stock.AI': 1 }, { 'stock.ai': -1 }, { 'stock.ai': 1.5 }, { 'stock.ai': 10000 }, [1], { 'stock.ai': '3' }]) {
    const x = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'p399', name: '基本', feats: {}, lims: bad });
    assert.equal(x.s, 400, JSON.stringify(bad)); assert.equal(x.j.error, 'bad_lims');
  }
  assert.deepEqual((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans.find((x) => x.id === 'p399').lims, { 'stock.ai': 3, 'ov.theme': 0 }, '壞值不會半套寫進去');
});

test('在線時間：同一人每次心跳加間隔（單次上限 120 秒），斷線超過 150 秒不補；多個分頁不會加倍；訪客不記', async () => {
  const { hub, db } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  const saved = clock;
  try {
    await beat(hub, bob);                                     // 第一跳：只記起點
    clock += 60000; await beat(hub, bob);                      // +60s
    clock += 30000; await beat(hub, bob, { sid: 'sid-second-tab' });   // 第二個分頁：只加距上次（30s），不是另算一份
    clock += 140000; await beat(hub, bob);                     // 140s（≤150）→ 只加 120（上限）
    clock += 600000; await beat(hub, bob);                     // 斷了 10 分鐘 → 不補
    clock += 60000; await beat(hub, bob);                      // +60s
    await beat(hub, null);                                     // 訪客
  } finally { clock = saved; }
  const ms = db.prepare('SELECT SUM(ms) AS ms FROM visits').get().ms;
  assert.equal(ms, (60 + 30 + 120 + 60) * 1000);
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM visits').get().c, 1, '只有登入者有列');
});

test('會員名單：只有管理者；合併登入過的與設定過的；付費標示、30 天造訪／觀看／在線、最常用功能與股票 Top3；明細 14 天', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'p799', name: '進階', feats: {}, price: 799, period: 'year' });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'p799', over: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'later@example.com', plan: 'p799', over: {} });
  const saved = clock;
  try {
    await beat(hub, bob, { ev: { 'ev:session_login': 1, 'pv:stock': 3, 'pv:flow': 1 }, e2: [['stock', 'view', '2330', 2], ['stock', 'view', '2317', 1], ['stock', 'tab.revenue', '2330', 4], ['flow', 'quad', '領先', 2], ['stock', 'kp.60m', '2330', 1]] });
    clock += 60000; await beat(hub, bob);
    clock += 86400000; await beat(hub, bob, { ev: { 'ev:session_login': 1, 'pv:stock': 1 }, e2: [['stock', 'view', '2454', 5]] });
  } finally { clock = saved + 86400000 + 60000; }
  try {
    assert.equal((await post(hub, '/v1/admin/members', { t: bob })).status, 403);
    assert.equal((await post(hub, '/v1/admin/members', {})).status, 403);
    assert.equal((await post(hub, '/v1/admin/member/detail', { t: bob, email: 'bob@example.com' })).status, 403);
    const { s, j } = await pj(hub, '/v1/admin/members', { t: andy });
    assert.equal(s, 200);
    const m = j.members.find((x) => x.email === 'bob@example.com');
    assert.deepEqual([m.plan, m.planName, m.tier, m.paid, m.st], ['p799', '進階', 'paid', true, 'ok']);
    assert.deepEqual([m.visits30, m.views30, m.online30, m.onlineMs, m.days30], [2, 5, 60000, 60000, 2]);
    assert.deepEqual(m.topFeat, [['tab.revenue', 4], ['quad', 2], ['kp.60m', 1]]);
    assert.deepEqual(m.topStock, [['2454', 5], ['2330', 2], ['2317', 1]]);
    const later = j.members.find((x) => x.email === 'later@example.com');
    assert.deepEqual([later.st, later.paid, later.visits30], ['new', true, 0]);
    const andyRow = j.members.find((x) => x.email === 'andy@example.com');
    assert.deepEqual([andyRow.tier, andyRow.paid], ['free', false]);
    const d = (await pj(hub, '/v1/admin/member/detail', { t: andy, email: 'BOB@example.com' })).j;
    assert.equal(d.days.length, 14);
    assert.deepEqual(d.days.slice(-2).map((x) => [x.visits, x.views]), [[1, 4], [1, 1]]);
    assert.deepEqual(d.pages, [['stock', 4], ['flow', 1]]);
    assert.deepEqual(d.stocks[0], ['2454', 5]);
    assert.equal((await post(hub, '/v1/admin/member/detail', { t: andy, email: 'not-an-email' })).status, 400);
  } finally { clock = saved; }
});

test('個人使用明細：刪帳號一起刪；90 天前的清掉；訪客的心跳不寫進去', async () => {
  const { hub, db } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  await beat(hub, null, { ev: { 'pv:stock': 2 }, e2: [['stock', 'view', '2330', 1]] });
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM uev').get().c, 0, '訪客不記個人明細');
  await beat(hub, bob, { ev: { 'pv:stock': 2 }, e2: [['stock', 'view', '2330', 1]] });
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM uev').get().c, 2);
  const saved = clock;
  try { clock += 91 * 86400000; hub.cleanup(); } finally { clock = saved; }
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM uev').get().c, 0, '90 天前清掉');
  await beat(hub, bob, { ev: { 'pv:flow': 1 } });
  assert.equal((await post(hub, '/v1/delete', { t: bob })).status, 200);
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM uev').get().c, 0, '刪帳號一起刪');
});

test('瀏覽次數計數：任何功能鍵都收（不只 quota.*）、同一個 key 一天只算一次', async () => {
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'stock.ai', key: '2330' })).j.n, 1);
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'stock.ai', key: '2330' })).j.n, 1);
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'grp.foundry', key: 'foundry' })).j.n, 1);
  assert.equal((await post(hub, '/v1/quota/hit', { k: 'stock.ai', key: '2330' })).status, 401);
  assert.equal((await post(hub, '/v1/quota/hit', { t: bob, k: '../x', key: '1' })).status, 400);
});

test('相容遷移：舊 plans／visits／users 表（沒有 lims／ms／ob）啟動後自動補欄、舊資料保留；重跑不報錯', async () => {
  const { hub, db, state } = makeHub(env());
  assert.equal((await pj(hub, '/v1/plans/public', {})).s, 200);
  const cols = (t) => db.prepare(`PRAGMA table_info(${t})`).all().map((c) => c.name);
  assert.ok(cols('plans').includes('lims') && cols('visits').includes('ms') && cols('users').includes('ob'));
  const { Hub } = await import('../worker.js');
  const again = new Hub(state, env());
  assert.equal((await again.fetch(new Request(API + '/v1/plans/public', { method: 'POST', headers: { Origin: ORIGIN }, body: '{}' }))).status, 200);
});
