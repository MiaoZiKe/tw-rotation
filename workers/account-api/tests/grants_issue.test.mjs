/* 管理者手動發放體驗 /v1/admin/grants/issue（2026-11-07，會員清單「方案」欄）。跑法：node --test workers/account-api/tests/grants_issue.test.mjs */
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
const T0 = Date.parse('2026-11-07T04:00:00Z');
const DAY = 86400000;
let clock = T0;
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', TRIAL_HMAC_KEY: 'k'.repeat(32), __now: () => clock });
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email, ip = '203.0.113.' + Math.floor(Math.random() * 200 + 1)) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie, 'CF-Connecting-IP': ip } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
const FEATS = { 'stock.draw': 3 };
async function setup(defs) {
  clock = T0;
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '免費會員', feats: { 'stock.draw': false } });
  for (const d of defs) { const r = await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...d }); assert.equal(r.s, 200, JSON.stringify(r.j)); }
  return { hub, andy };
}
const WELCOME_OFF = { id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: FEATS, per: 'total', days: 7, on: false };
const WELCOME_ON = { ...WELCOME_OFF, on: true };
const PROMO = { id: 'promo-x', kind: 'promo', name: '活動體驗', feats: FEATS, per: 'total', t0: T0 - DAY, t1: T0 + 5 * DAY, on: true };

test('只有管理者能呼叫；probe 只回 ok（前端用來判斷後端有沒有這個端點）', async () => {
  const { hub, andy } = await setup([WELCOME_ON]);
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: bob, probe: true })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: bob, email: 'bob@example.com', gid: 'welcome' })).s, 403);
  const r = await pj(hub, '/v1/admin/grants/issue', { t: andy, probe: true });
  assert.equal(r.s, 200); assert.equal(r.j.probe, true);
});

test('發 welcome：從現在起算 days 天、該會員立刻拿到額度；重發會刷新並清掉已用次數', async () => {
  const { hub, andy } = await setup([WELCOME_ON]);
  const bob = await login(hub, 'bob@example.com');
  // 登入時 welcome 已自動發過一次；管理者重發＝刷新
  clock = T0 + 3 * DAY;
  await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' });
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob })).j.left, { 'stock.draw': 2 });
  const r = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'Bob@Example.com', gid: 'welcome' });
  assert.equal(r.s, 200, JSON.stringify(r.j));
  assert.equal(r.j.start, clock); assert.equal(r.j.end - r.j.start, 7 * DAY);
  const me = (await pj(hub, '/v1/grants/me', { t: bob })).j;
  assert.equal(me.grants.length, 1); assert.equal(me.grants[0].end, clock + 7 * DAY);
  assert.deepEqual(me.left, { 'stock.draw': 3 }, '已用次數清掉');
});

test('已過期的 welcome 也能由管理者再發一次（新會員體驗過期後的補發）', async () => {
  const { hub, andy } = await setup([WELCOME_ON]);
  const bob = await login(hub, 'bob@example.com');
  clock = T0 + 30 * DAY;
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob })).j.grants, []);
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' })).s, 200);
  assert.equal((await pj(hub, '/v1/grants/me', { t: bob })).j.grants.length, 1);
});

test('promo：到活動結束為止；活動已結束不能發', async () => {
  const { hub, andy } = await setup([PROMO]);
  await login(hub, 'bob@example.com');
  const r = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'promo-x' });
  assert.equal(r.s, 200); assert.equal(r.j.end, PROMO.t1);
  clock = T0 + 10 * DAY;
  const r2 = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'promo-x' });
  assert.equal(r2.s, 400); assert.equal(r2.j.error, 'ended');
});

test('擋下：範本關著、範本不存在、沒登入過的 email、格式錯誤', async () => {
  const { hub, andy } = await setup([WELCOME_OFF]);
  await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' })).j.error, 'def_off');
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'nope' })).s, 404);
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'ghost@example.com', gid: 'welcome' })).j.error, 'no_user');
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'not-an-email', gid: 'welcome' })).s, 400);
  assert.equal((await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'Bad Id!' })).s, 400);
});

test('名單 /v1/admin/members 每人帶 grants；手動發放後立刻反映；重發 renewed＝true 且已發人數不增加', async () => {
  const { hub, andy } = await setup([WELCOME_OFF]);
  await login(hub, 'bob@example.com');                          // welcome 關著：登入不會自動發
  const mem = async () => (await pj(hub, '/v1/admin/members', { t: andy })).j.members.find((m) => m.email === 'bob@example.com');
  assert.deepEqual((await mem()).grants, [], '還沒有任何體驗');
  const on = { ...WELCOME_ON, days: 7 };
  assert.equal((await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...on })).s, 200);
  const issuedOf = async () => (await pj(hub, '/v1/admin/grants/defs/list', { t: andy })).j.defs.find((d) => d.id === 'welcome').issued;
  assert.equal(await issuedOf(), 0);
  clock = T0 + 2 * DAY;
  const r = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });
  assert.equal(r.s, 200); assert.equal(r.j.renewed, false);
  const g = (await mem()).grants;
  assert.equal(g.length, 1);
  assert.deepEqual([g[0].gid, g[0].name, g[0].kind, g[0].start, g[0].end], ['welcome', '新會員體驗', 'welcome', clock, clock + 7 * DAY]);
  assert.equal(await issuedOf(), 1);
  clock = T0 + 4 * DAY;
  const r2 = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });
  assert.equal(r2.j.renewed, true);
  assert.equal((await mem()).grants[0].end, clock + 7 * DAY, '重發後名單的到期日跟著新的');
  assert.equal(await issuedOf(), 1, '同一人重發不增加已發人數');
  // 同一份資料 grants/user 看到的也一致
  const u = (await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com' })).j;
  assert.equal(u.grants[0].end, clock + 7 * DAY);
});
