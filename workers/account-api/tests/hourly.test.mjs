/* hourly 區塊（每小時統計 hstat、/v1/admin/stats 的 hours／hourly／hstat、頁面白名單補七頁）的驗收。
 *
 * 跑法：node --test workers/account-api/tests/*.mjs
 * 同 account／sub／v3／v4：每條同時驗「該允許的有允許」與「該拒絕的有拒絕」。
 * 時間一律用台北時間想：tpe('2026-10-05 09:10') ＝ UTC 01:10。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { makeHub } from '../harness.mjs';
import { VIEWS, VIEWS_ADDED, EVENTS } from '../worker.js';

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
const tpe = (s) => Date.parse(s.replace(' ', 'T') + ':00+08:00');
let clock = tpe('2026-10-05 09:10');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
const post = (hub, path, body, ip = '1.1.1.1') => hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': ip }, body: JSON.stringify(body) }));
const pj = async (hub, path, body, ip) => { const r = await post(hub, path, body, ip); return { s: r.status, j: await r.json() }; };
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
const beat = (hub, ev, extra = {}) => pj(hub, '/v1/beat', { sid: 'sid-abcdefgh', r: 'flow', ev, ...extra });
const stats = (hub, t, body = {}) => pj(hub, '/v1/admin/stats', { t, days: 7, ...body });
const sum = (a) => a.reduce((s, x) => s + x, 0);
const OLD_VIEWS = ['overview', 'flow', 'industry', 'heatmap', 'market', 'season', 'delivery', 'stock', 'legal', 'watch', 'other'];

test('小時桶累加：同一小時的心跳加在同一格、下一小時另起一格；離開那一跳記次數但不算在線分鐘', async () => {
  clock = tpe('2026-10-05 09:10');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await beat(hub, { 'pv:flow': 3, 'ev:session': 1 })).s, 200);
  clock = tpe('2026-10-05 09:40');
  assert.equal((await beat(hub, { 'pv:stock': 2, 'ev:session': 2, 'ev:session_login': 1 })).s, 200);
  assert.equal((await beat(hub, {})).s, 200, '沒有計數的心跳：只算在線一分鐘');
  clock = tpe('2026-10-05 10:05');
  assert.equal((await beat(hub, { 'pv:overview': 4 }, { leave: true })).s, 200);
  const { s, j } = await stats(hub, andy);
  assert.equal(s, 200);
  assert.equal(j.hours.length, 24);
  assert.equal(j.hours[9], 5, '09 時：3＋2');
  assert.equal(j.hours[10], 4, '10 時：離開那一跳帶的瀏覽照算');
  assert.equal(sum(j.hours), 9, '其他小時都是 0');
  const d = j.hstat.day;
  assert.deepEqual([d.open[9], d.login[9], d.guest[9], d.mins[9]], [3, 1, 2, 3], '09 時：開站 3（登入 1、訪客 2）、在線 3 分鐘');
  assert.deepEqual([d.pv[10], d.open[10], d.mins[10]], [4, 0, 0], '10 時：離開不算在線分鐘');
  assert.deepEqual([j.hstat.today, j.hstat.hour, j.hstat.since], ['2026-10-05', 10, '2026-10-05']);
  assert.deepEqual(j.hourly, j.hours, '期間只有今天有資料 → 期間加總＝今天');
  assert.deepEqual([j.hstat.period.from, j.hstat.period.to], [j.from, j.to]);
});

test('每小時加總＝每日 usage（同一份心跳、同一套驗證）；整批被擋的心跳兩邊都不記', async () => {
  clock = tpe('2026-10-05 13:20');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  for (const [hm, ev] of [['00:05', { 'pv:overview': 1, 'ev:session': 1 }], ['08:59', { 'pv:flow': 7, 'ev:session': 2, 'ev:session_login': 2, 'ev:zoom': 3 }],
    ['13:00', { 'pv:stock': 11, 'pv:etf': 2, 'ev:session': 4, 'ev:session_login': 1 }], ['23:59', { 'pv:season': 1 }]]) {
    clock = tpe('2026-10-05 ' + hm);
    assert.equal((await beat(hub, ev)).s, 200, hm);
  }
  // 被擋的：非白名單鍵（整批 400）、超過上限（400）、別的網站（403）
  assert.equal((await beat(hub, { 'pv:flow': 5, 'pv:bogus': 1 })).s, 400);
  assert.equal((await beat(hub, { 'pv:flow': 51 })).s, 400);
  const evil = await hub.fetch(new Request(API + '/v1/beat', { method: 'POST', headers: { Origin: 'https://evil.example', 'content-type': 'text/plain' }, body: JSON.stringify({ sid: 'sid-abcdefgh', ev: { 'pv:flow': 9 } }) }));
  assert.equal(evil.status, 403);
  const { j } = await stats(hub, andy);
  const day = (k) => j.rows.filter((r) => r.day === '2026-10-05' && (k === 'pv' ? r.k.startsWith('pv:') : r.k === k)).reduce((s, r) => s + r.n, 0);
  assert.equal(sum(j.hours), day('pv'), '頁面瀏覽：各小時加總＝usage 今天');
  assert.equal(sum(j.hstat.day.open), day('ev:session'), '開站');
  assert.equal(sum(j.hstat.day.login), day('ev:session_login'), '登入開站');
  assert.equal(sum(j.hours), 22);
  assert.deepEqual([j.hours[0], j.hours[8], j.hours[13], j.hours[23]], [1, 7, 13, 1], '台北時間分桶（不是 UTC：00:05 台北＝UTC 前一天 16:05）');
});

test('速率限制（429）的心跳不進小時桶', async () => {
  clock = tpe('2026-10-05 11:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  let ok = 0, limited = 0;
  for (let i = 0; i < 245; i++) { const r = await post(hub, '/v1/beat', { sid: 'sid-abcdefgh', ev: { 'pv:flow': 1 } }, '9.9.9.9'); if (r.status === 200) ok++; else if (r.status === 429) limited++; }
  assert.ok(limited > 0, '有被限速');
  const { j } = await stats(hub, andy);
  assert.equal(j.hours[11], ok, '只算 200 的');
  assert.equal(j.hstat.day.mins[11], ok);
});

test('跨日：台北 23:59 記在前一天 23 時、00:00 記在新的一天 0 時；今天的 hours 不會混到昨天', async () => {
  clock = tpe('2026-10-05 23:59');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await beat(hub, { 'pv:flow': 6, 'ev:session': 1 })).s, 200);
  clock = tpe('2026-10-06 00:00') + 30 * 1000;
  assert.equal((await beat(hub, { 'pv:flow': 2, 'ev:session': 1 })).s, 200);
  let { j } = await stats(hub, andy, { days: 1 });
  assert.deepEqual([j.hstat.today, j.hstat.hour, j.from, j.to], ['2026-10-06', 0, '2026-10-06', '2026-10-06']);
  assert.equal(j.hours[0], 2);
  assert.equal(j.hours[23], 0, '昨天 23 時不算在今天');
  assert.deepEqual(j.hourly, j.hours, 'days=1 → 期間就是今天');
  ({ j } = await stats(hub, andy, { days: 2 }));
  assert.deepEqual([j.hourly[0], j.hourly[23]], [2, 6], '期間兩天：各「時」加總');
  assert.deepEqual([j.hstat.period.open[0], j.hstat.period.open[23]], [1, 1]);
  assert.equal(j.hstat.since, '2026-10-05');
  // usage 的每日 rows 也是同一個切點
  assert.deepEqual(j.rows.filter((r) => r.k === 'pv:flow').map((r) => [r.day, r.n]), [['2026-10-05', 6], ['2026-10-06', 2]]);
});

test('保存期限：跟 usage 同一個切點（13 個月），alarm 刪掉更舊的小時桶', async () => {
  clock = tpe('2025-08-01 10:00');
  const { hub, db } = makeHub(env());
  await beat(hub, { 'pv:flow': 1 });
  clock = tpe('2025-09-20 10:00');
  await beat(hub, { 'pv:flow': 1 });
  clock = tpe('2026-10-05 10:00');
  await hub.alarm();
  const days = db.prepare('SELECT DISTINCT day FROM hstat ORDER BY day').all().map((r) => r.day);
  const udays = db.prepare("SELECT DISTINCT day FROM usage ORDER BY day").all().map((r) => r.day);
  assert.deepEqual(days, ['2025-09-20'], '13 個月前（2025-09-05）以前的刪掉');
  assert.deepEqual(days, udays, '跟 usage 留下的天數一樣');
});

test('白名單新頁可記：etf／explore／earnings／events／support／pricing／notices 的 pv、細項、線上名單 route、page 篩選；不認得的照樣整批擋', async () => {
  clock = tpe('2026-10-05 14:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  assert.deepEqual(VIEWS_ADDED, ['etf', 'explore', 'earnings', 'events', 'support', 'pricing', 'notices']);
  assert.deepEqual(VIEWS, [...OLD_VIEWS, ...VIEWS_ADDED], '舊的 11 頁順序不變，新的接在後面');
  const ev = Object.fromEntries(VIEWS_ADDED.map((v, i) => ['pv:' + v, i + 1]));
  assert.equal((await beat(hub, ev)).s, 200);
  const e2 = [['etf', 'cat', '配息型', 2], ['support', 'tab', '常見問題', 1], ['events', 'link', '', 3], ['explore', 'topic', '營收創高', 1], ['earnings', 'how', 'calCard', 1]];
  assert.equal((await beat(hub, {}, { e2 })).s, 200);
  assert.equal((await pj(hub, '/v1/beat', { sid: 'sid-etfpage1', r: 'etf', t: andy })).s, 200);
  // 不認得的頁面／元件照樣整批擋
  assert.equal((await beat(hub, { 'pv:admin': 1 })).s, 400, 'admin 本身不計，不在白名單');
  assert.equal((await beat(hub, {}, { e2: [['bogus', 'x', '', 1]] })).s, 400);
  const { j } = await stats(hub, andy);
  for (const [i, v] of VIEWS_ADDED.entries()) assert.ok(j.rows.some((r) => r.k === 'pv:' + v && r.n === i + 1), 'pv:' + v);
  assert.equal(j.hours[14], sum(VIEWS_ADDED.map((_, i) => i + 1)), '新頁的瀏覽也進小時桶');
  assert.deepEqual(j.e2.find((r) => r.page === 'etf'), { page: 'etf', comp: 'cat', detail: '配息型', n: 2 });
  assert.deepEqual(j.views, VIEWS);
  const sup = (await stats(hub, andy, { page: 'support' })).j.e2;
  assert.deepEqual(sup, [{ page: 'support', comp: 'tab', detail: '常見問題', n: 1 }], 'page 篩選收新頁');
  const on = (await pj(hub, '/v1/admin/online', { t: andy })).j;
  assert.equal(on.users.find((u) => u.email === 'andy@example.com').route, 'etf', '線上名單看得到在 ETF 頁（以前會變 other）');
});

test('舊資料相容：之前記在 other 底下、元件名帶前綴的細項照舊讀得到，跟新頁面的列並存、不合併', async () => {
  clock = tpe('2026-10-05 15:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const old = [['other', 'etf.cat', '配息型', 5], ['other', 'support.fab', '', 2], ['other', 'events.link', '', 4], ['other', 'explore.topic', '營收創高', 3]];
  assert.equal((await beat(hub, { 'pv:other': 6 }, { e2: old })).s, 200);
  assert.equal((await beat(hub, { 'pv:etf': 1 }, { e2: [['etf', 'etf.cat', '配息型', 1]] })).s, 200);
  const { j } = await stats(hub, andy);
  for (const [page, comp, detail, n] of old) assert.ok(j.e2.some((r) => r.page === page && r.comp === comp && r.detail === detail && r.n === n), comp);
  assert.ok(j.e2.some((r) => r.page === 'etf' && r.comp === 'etf.cat' && r.n === 1), '新頁面那列另外一列');
  assert.ok(j.rows.some((r) => r.k === 'pv:other' && r.n === 6), 'pv:other 照舊');
  const oth = (await stats(hub, andy, { page: 'other' })).j.e2;
  assert.equal(oth.length, 4, 'page=other 篩選照舊只回 other 的');
});

test('舊 API 回應不變：stats 原有欄位的值不變、只在後面多 hours／hourly／hstat；非管理者照樣 403；beat 回應形狀不變', async () => {
  clock = tpe('2026-10-05 16:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const b1 = await beat(hub, { 'pv:flow': 2, 'ev:session': 1, 'ev:zoom': 1 }, { e2: [['flow', 'quad', '領先', 2]] });
  assert.deepEqual(Object.keys(b1.j).sort(), ['n', 'ok'], 'beat 回 {ok, n}，沒有多東西');
  const { s, j } = await stats(hub, andy, { days: 3 });
  assert.equal(s, 200);
  assert.deepEqual(Object.keys(j), ['from', 'to', 'rows', 'e2', 'users', 'events', 'views', 'hours', 'hourly', 'hstat'], '原本的欄位順序不變，新的接在後面');
  assert.deepEqual([j.from, j.to], ['2026-10-03', '2026-10-05']);
  assert.deepEqual(j.rows.map((r) => [r.day, r.k, r.n]).sort(), [['2026-10-05', 'ev:session', 1], ['2026-10-05', 'ev:zoom', 1], ['2026-10-05', 'pv:flow', 2]]);
  assert.deepEqual(j.e2, [{ page: 'flow', comp: 'quad', detail: '領先', n: 2 }]);
  assert.equal(j.users.total, 2);
  assert.deepEqual(j.events, EVENTS);
  assert.deepEqual(j.views.slice(0, OLD_VIEWS.length), OLD_VIEWS);
  for (const t of [bob, undefined, 'v1.fake.1.1.sig']) assert.equal((await stats(hub, t)).s, 403, '非管理者／訪客／假權杖');
  assert.deepEqual(Object.keys(j.hstat), ['today', 'hour', 'since', 'day', 'period']);
  for (const k of ['pv', 'open', 'login', 'guest', 'mins']) { assert.equal(j.hstat.day[k].length, 24, k); assert.equal(j.hstat.period[k].length, 24, k); }
});

test('還沒有任何心跳：hours／hourly 是 24 個 0、since 是 null（不報錯）', async () => {
  clock = tpe('2026-10-05 08:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const { s, j } = await stats(hub, andy, { days: 400 });
  assert.equal(s, 200);
  assert.deepEqual(j.hours, Array(24).fill(0));
  assert.deepEqual(j.hourly, Array(24).fill(0));
  assert.equal(j.hstat.since, null);
});

test('文件：七個新頁面與 hours／hourly／hstat 都寫在 docs/account_analytics.md', () => {
  const doc = readFileSync(new URL('../../../docs/account_analytics.md', import.meta.url), 'utf8');
  for (const v of VIEWS_ADDED) assert.ok(doc.includes('`' + v + '`'), '文件沒寫到頁面 ' + v);
  for (const k of ['`hours`', '`hourly`', '`hstat`', 'hstat(day, h, pv, sess, sess_login, mins)']) assert.ok(doc.includes(k), '文件沒寫到 ' + k);
});
