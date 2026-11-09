/* 會員通知 member_notices（2026-11-09）。跑法：node --test workers/account-api/tests/member_notices.test.mjs */
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
const T0 = Date.parse('2026-10-14T04:00:00Z');
let clock = T0;
const DAY = 86400000;
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', TRIAL_HMAC_KEY: 'k'.repeat(32), __now: () => clock });
const IPS = {};   // 權杖 → IP（模擬 Cloudflare 的 CF-Connecting-IP）
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: Object.assign({ Origin: ORIGIN, 'content-type': 'text/plain' }, body && IPS[body.t] ? { 'CF-Connecting-IP': IPS[body.t] } : {}), body: JSON.stringify(body) }));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email, ip = '203.0.113.' + Math.floor(Math.random() * 200 + 1), sub = 'sub-' + email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie, 'CF-Connecting-IP': ip } }));
  const tok = (await (await post(hub, '/auth/redeem', { n })).json()).tok;
  IPS[tok] = ip; return tok;
}
const FEATS = { 'stock.draw': 3, 'ind.rel': 3 };
async function setup() {
  clock = T0;
  const { hub, db } = makeHub(env());
  hub._db = db;
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'stock.draw': true } });
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: { 'stock.draw': true, 'stock.ai': true } });
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: { 'ind.3d': 5 }, per: 'day', days: 14, on: true });
  return { hub, andy };
}
const PICK = [{ p: 'flow', subs: ['flow-rotation', 'flow-sankey'] }, { p: 'etf', subs: [] }];
const trial = async (hub, t) => (await pj(hub, '/v1/me/trial', { t })).j;
const plan = async (hub, t) => (await pj(hub, '/v1/perm/me', { t })).j.plan;
let ipn = 0;
const newbie = (hub, name) => login(hub, name + '@example.com', '198.51.100.' + (++ipn));
async function invite(hub, code, name) { const t = await newbie(hub, name); const r = await pj(hub, '/v1/invite/redeem', { t, code }); return { t, r }; }
const mine = async (hub, t) => (await pj(hub, '/v1/notices/mine', { t })).j;
const unreadTitles = async (hub, t) => (await mine(hub, t)).notices.filter((n) => !n.seen).map((n) => n.title);
const md = (ms) => { const d = new Date(ms - 1 + 8 * 3600 * 1000); return (d.getUTCMonth() + 1) + '/' + d.getUTCDate(); };

test('沒登入 401；新會員一開始沒有通知（自動發的 welcome 不寫）', async () => {
  const { hub } = await setup();
  assert.equal((await pj(hub, '/v1/notices/mine', {})).s, 401);
  assert.equal((await pj(hub, '/v1/notices/seen', { all: true })).s, 401);
  const bob = await login(hub, 'bob@example.com');
  const m = await mine(hub, bob);
  assert.equal(m.unread, 0); assert.deepEqual(m.notices, []);
});

test('手動發放體驗寫一則（含到期日）；重發寫「已重新起算」；只讀得到自己的', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  const amy = await login(hub, 'amy@example.com');
  clock = T0 + DAY;
  const r = await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });
  assert.equal(r.s, 200);
  let m = await mine(hub, bob);
  assert.equal(m.unread, 1);
  assert.equal(m.notices[0].kind, 'grant');
  assert.match(m.notices[0].body, new RegExp('到期 ' + md(r.j.end).replace('/', '\\/')));
  assert.equal((await mine(hub, amy)).unread, 0, '別人看不到 bob 的通知');
  // amy 拿 bob 的通知 id 標已讀 → 不影響 bob
  await pj(hub, '/v1/notices/seen', { t: amy, ids: [m.notices[0].id] });
  assert.equal((await mine(hub, bob)).unread, 1);
  clock = T0 + 2 * DAY;
  await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });   // 這次是重發
  const ts = await unreadTitles(hub, bob);
  assert.equal(ts.length, 2);
  assert.match(ts[0], /重新起算/);
  // probe 不寫
  await pj(hub, '/v1/admin/grants/issue', { t: andy, probe: true });
  assert.equal((await mine(hub, bob)).unread, 2);
});

test('seen 後不再回成未讀；最近 20 則仍列出（seen=true）', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });
  let m = await mine(hub, bob);
  const r = await pj(hub, '/v1/notices/seen', { t: bob, ids: m.notices.map((n) => n.id) });
  assert.equal(r.j.unread, 0);
  m = await mine(hub, bob);
  assert.equal(m.unread, 0); assert.equal(m.notices.length, 1); assert.equal(m.notices[0].seen, true);
  for (let i = 0; i < 25; i++) { clock += 1000; await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' }); }
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  m = await mine(hub, bob);
  assert.equal(m.unread, 0); assert.equal(m.notices.length, 20);
});

test('延長體驗天數寫一則；不帶 extend_days 只是查詢、不寫', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com' });
  assert.equal((await mine(hub, bob)).unread, 0);
  const r = await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com', extend_days: 7 });
  assert.equal(r.s, 200);
  const end = r.j.grants[0].end;
  const ts = await unreadTitles(hub, bob);
  assert.deepEqual(ts, [`你的「新會員體驗」延長到 ${md(end)}`]);
});

test('改方案：升級寫、延長到期寫、改成不限期寫；降級／重設／縮短不寫', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  const put = (x) => pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', ...x });
  const e1 = T0 + 30 * DAY;
  assert.equal((await put({ plan: 'plus', expires: e1 })).s, 200);
  assert.deepEqual(await unreadTitles(hub, bob), ['你的方案已升級為 Plus']);
  assert.match((await mine(hub, bob)).notices[0].body, new RegExp(md(e1).replace('/', '\\/')));
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  clock += 1000;
  await put({ plan: 'pro', expires: e1 });
  assert.deepEqual(await unreadTitles(hub, bob), ['你的方案已升級為 Pro']);
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  clock += 1000;
  const e2 = T0 + 60 * DAY;
  await put({ plan: 'pro', expires: e2 });
  assert.deepEqual(await unreadTitles(hub, bob), [`你的 Pro 延長到 ${md(e2)}`]);
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  clock += 1000;
  await put({ plan: 'pro', expires: 0 });
  assert.deepEqual(await unreadTitles(hub, bob), ['你的 Pro 改為不限期']);
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  // 以下都不該寫
  await put({ plan: 'pro', expires: T0 + 10 * DAY });     // 縮短
  await put({ plan: 'plus' });                            // 降級
  await put({ plan: 'free' });                            // 取消
  await put({ reset: true });                             // 重設
  assert.equal((await mine(hub, bob)).unread, 0, '降級／取消／縮短／重設不寫');
});

test('同方案下個人功能開通或次數變多寫一則；變少不寫', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  const put = (over) => pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'free', over });
  await put({ 'stock.ai': 3 });
  assert.deepEqual(await unreadTitles(hub, bob), ['站主替你多開了功能']);
  await pj(hub, '/v1/notices/seen', { t: bob, all: true });
  await put({ 'stock.ai': 1 });
  assert.equal((await mine(hub, bob)).unread, 0, '次數變少不寫');
});

test('邀請獎勵：邀請人拿到 Plus 時寫一則', async () => {
  const { hub } = await setup();
  const alice = await newbie(hub, 'alice');
  const code = (await pj(hub, '/v1/invite/me', { t: alice })).j.code;
  assert.ok(code);
  const { r } = await invite(hub, code, 'carl');
  assert.equal(r.s, 200, JSON.stringify(r.j));
  const ts = await unreadTitles(hub, alice);
  assert.equal(ts.length, 1); assert.match(ts[0], /^邀請獎勵：Plus 延長到 /);
});

test('刪帳號一起刪通知', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/admin/grants/issue', { t: andy, email: 'bob@example.com', gid: 'welcome' });
  assert.equal((await mine(hub, bob)).unread, 1);
  assert.equal((await pj(hub, '/v1/delete', { t: bob })).s, 200);
  const rows = hub._db.prepare('SELECT COUNT(*) AS c FROM member_notices').get().c;
  assert.equal(rows, 0);
});
