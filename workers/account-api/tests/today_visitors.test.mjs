/* 管理區會員名單的「今日在線」與右上角「訪客數」（2026-10-27，Andy）：
 * 今日在線＝visits 今天（台北日）那列的 ms，跨日歸零；訪客數＝dayvis 每日去重人數另存的 vdaily，近 30 天加總。
 * 跑法：node --test workers/account-api/tests/*.mjs
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
const tpe = (s) => Date.parse(s.replace(' ', 'T') + ':00+08:00');
let clock = tpe('2026-10-27 09:00');
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
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 36000, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
const beat = (hub, t, extra = {}) => pj(hub, '/v1/beat', { sid: 'sid-' + t.slice(3, 12), r: 'stock', t, ...extra });
const visit = (hub, vd, ip = '1.1.1.1') => pj(hub, '/v1/track/batch', { sid: 'sid' + vd, vd, now: clock, items: [{ ts: clock, r: 'overview', ev: { 'pv:overview': 1 }, live: 1 }] }, ip);

test('今日在線：只算今天（台北日）、跨日歸零、累計不受影響；訪客數去重＋近 30 天加總', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  await beat(hub, bob, { ev: { 'ev:session_login': 1, 'pv:stock': 1 } });
  clock += 60000; await beat(hub, bob);
  clock += 60000; await beat(hub, bob);
  // 訪客：兩台＋同一台重新整理（不重複算）
  await visit(hub, 'vdAAAAAAAAAA'); await visit(hub, 'vdAAAAAAAAAA'); await visit(hub, 'vdBBBBBBBBBB', '2.2.2.2');
  let r = await pj(hub, '/v1/admin/members', { t: andy });
  assert.equal(r.s, 200);
  let m = r.j.members.find((x) => x.email === 'bob@example.com');
  assert.deepEqual([m.todayMs, m.onlineMs], [120000, 120000]);
  assert.deepEqual([r.j.visitors.today, r.j.visitors.d30, r.j.visitors.since], [2, 2, '2026-10-27']);
  // 隔天：今日在線歸零、累計還在；訪客今天 1、近 30 天 3
  clock = tpe('2026-10-28 10:00');
  await visit(hub, 'vdCCCCCCCCCC');
  r = await pj(hub, '/v1/admin/members', { t: andy });
  m = r.j.members.find((x) => x.email === 'bob@example.com');
  assert.deepEqual([m.todayMs, m.onlineMs], [0, 120000]);
  assert.deepEqual([r.j.visitors.today, r.j.visitors.d30, r.j.visitors.days], [1, 3, 2]);
  // 隔天又上線：今日在線只算新的這一天
  await beat(hub, bob, { ev: { 'ev:session_login': 1 } }); clock += 60000; await beat(hub, bob);
  r = await pj(hub, '/v1/admin/members', { t: andy });
  m = r.j.members.find((x) => x.email === 'bob@example.com');
  assert.deepEqual([m.todayMs, m.onlineMs], [60000, 180000]);
  // 31 天後：第一天掉出「近 30 天」
  clock = tpe('2026-11-27 10:00');
  r = await pj(hub, '/v1/admin/members', { t: andy });
  assert.deepEqual([r.j.visitors.today, r.j.visitors.d30], [0, 0]);
  // 非管理者拿不到
  assert.equal((await post(hub, '/v1/admin/members', { t: bob })).status, 403);
});

test('壞的 vd／leave 不記進訪客數', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await visit(hub, 'x<script>');
  await pj(hub, '/v1/track/batch', { sid: 'sidLEAVE0001', vd: 'vdLEAVEEEEEE', now: clock, leave: true, items: [] });
  const r = await pj(hub, '/v1/admin/members', { t: andy });
  assert.deepEqual([r.j.visitors.today, r.j.visitors.d30, r.j.visitors.since], [0, 0, null]);
});
