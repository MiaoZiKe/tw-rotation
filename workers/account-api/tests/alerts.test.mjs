/* 每日額度（docs/quota_plan.md）account-api 端驗收 */
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
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
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

/* 每日額度區塊（plans.dq、SEED_PLANS 種 Plus／Pro、/v1/perm/me 回 dq）的驗收。跑法：node --test workers/account-api/tests/ */
test('自設提醒（alerts）：註冊 1、Plus 5、Pro 不限；只擋變多；欄位白名單；未登入 401；版本衝突 409；管理者不限', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const free = await login(hub, 'free@example.com');
  const plus = await login(hub, 'plus@example.com');
  const pro = await login(hub, 'pro@example.com');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus', over: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pro@example.com', plan: 'pro', over: {} });
  const mk = (n) => Array.from({ length: n }, (_, i) => ({ id: 'a' + i, code: String(2330 + i), type: 'above', x: 100 + i }));
  const put = (t, alerts, rev) => pj(hub, '/v1/alerts/put', { t, alerts, rev });
  assert.equal((await pj(hub, '/v1/alerts/get', {})).s, 401, '未登入');
  assert.equal((await put(undefined, mk(1), 0)).s, 401);
  // 註冊會員 1 條
  let r = await put(free, mk(1), 0);
  assert.equal(r.s, 200); assert.equal(r.j.cap, 1);
  r = await put(free, mk(2), 1);
  assert.equal(r.s, 403); assert.equal(r.j.error, 'alert_limit'); assert.equal(r.j.limit, 1); assert.equal(r.j.alerts.length, 1, '擋下時回雲端現況');
  // Plus 5 條
  assert.equal((await put(plus, mk(5), 0)).s, 200);
  r = await put(plus, mk(6), 1);
  assert.equal(r.s, 403); assert.equal(r.j.limit, 5);
  // Pro 不限（硬上限 200）
  assert.equal((await put(pro, mk(50), 0)).s, 200);
  r = await pj(hub, '/v1/alerts/get', { t: pro });
  assert.equal(r.j.alerts.length, 50); assert.equal(r.j.cap, 200);
  // 降級只擋變多：Plus 改回免費，原本 5 條照樣能改能刪，不能加
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'free', over: {} });
  r = await put(plus, mk(5).slice(0, 4), 1);
  assert.equal(r.s, 200, '降級後可以刪');
  r = await put(plus, mk(5), 2);
  assert.equal(r.s, 403, '降級後不能再多');
  // 版本衝突
  r = await put(pro, mk(3), 0);
  assert.equal(r.s, 409); assert.equal(r.j.conflict, true);
  // 欄位白名單：壞資料整批不收；多帶的欄位被丟掉
  const bads = [[{ id: 'A', code: '2330', type: 'above', x: 1 }], [{ id: 'a1', code: 'zz', type: 'above', x: 1 }], [{ id: 'a1', code: '2330', type: 'buy_signal' }],
    [{ id: 'a1', code: '2330', type: 'above', x: -1 }], [{ id: 'a1', code: '2330', type: 'streak', n: 1, side: 'buy', who: 'total' }],
    [{ id: 'a1', code: '2330', type: 'streak', n: 3, side: 'long', who: 'total' }], [{ id: 'a1', code: '2330', type: 'exdiv', n: 99 }], 'x'];
  for (const bad of bads) assert.equal((await put(pro, bad, 1)).s, 400, JSON.stringify(bad));
  r = await put(pro, [{ id: 'a1', code: '2330', type: 'streak', n: 3, side: 'sell', who: 'foreign', note: '買點', score: 9 }], 1);
  assert.equal(r.s, 200); assert.deepEqual(r.j.alerts[0], { id: 'a1', code: '2330', type: 'streak', on: true, n: 3, side: 'sell', who: 'foreign' });
  // 管理者不限
  assert.equal((await put(andy, mk(30), 0)).s, 200);
  // 刪帳號一起刪
  assert.equal((await pj(hub, '/v1/delete', { t: pro })).s, 200);
});
