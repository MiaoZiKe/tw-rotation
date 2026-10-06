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
test('SEED_PLANS 有設：種 Plus（每日 50）與 Pro（不限），只種一次；沒設不種', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const pub = (await pj(hub, '/v1/plans/public', {})).j.plans;
  const plus = pub.find((p) => p.id === 'plus'), pro = pub.find((p) => p.id === 'pro');
  assert.equal(plus.name, 'Plus'); assert.equal(plus.dq, 50); assert.equal(plus.price, 0);
  assert.equal(pro.name, 'Pro'); assert.equal(pro.dq, null);
  assert.equal(pub.find((p) => p.id === 'free').dq, null, '免費會員預設不限（照舊）');
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', del: true })).s, 200);
  const again = (await pj(hub, '/v1/plans/public', {})).j.plans;
  assert.ok(!again.some((p) => p.id === 'plus'), '刪掉之後不會再長回來');
  const { hub: h2 } = makeHub(env());
  assert.ok(!(await pj(h2, '/v1/plans/public', {})).j.plans.some((p) => p.id === 'plus' || p.id === 'pro'), '沒設 SEED_PLANS 不種');
});

test('plans/put 改 dq：只有管理者；null＝不限、整數 0～9999；壞值 400；只改開關不會把 dq 洗掉；perm/me 回生效範本的 dq', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const mem = await login(hub, 'mem@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: mem, id: 'plus', name: 'Plus', feats: {}, dq: 1 })).s, 403, '一般會員不能改');
  for (const bad of [-1, 10000, 1.5, '50', true]) assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: bad })).s, 400, String(bad));
  let r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: 30 });
  assert.equal(r.s, 200); assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, 30);
  r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'ov.heat': false } });
  assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, 30, '沒帶 dq＝維持原值');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'mem@example.com', plan: 'plus', over: {} });
  let me = (await pj(hub, '/v1/perm/me', { t: mem })).j;
  assert.equal(me.plan, 'plus'); assert.equal(me.dq, 30);
  r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: null });
  assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, null, 'null＝不限');
  me = (await pj(hub, '/v1/perm/me', { t: mem })).j;
  assert.equal(me.dq, null);
  assert.equal((await pj(hub, '/v1/perm/me', {})).j.dq, null, '訪客：訪客範本沒設＝不限');
});
