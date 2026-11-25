import test from "node:test";
import assert from "node:assert/strict";
import { makeHub } from "../harness.mjs";

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

/* 2026-11-25 會員概況真實人數：超過名單上限（2000）時 total／members/count 仍是真實 COUNT，分頁拿得到其餘的人 */
test('會員人數：超過上限時 total 仍正確、近 7／30 天新註冊正確、分頁補齊、非管理者 403', async () => {
  const { hub, db } = makeHub(env());
  const adm = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const ins = db.prepare('INSERT INTO users (uid, subh, email, name, created, seen) VALUES (?, ?, ?, ?, ?, ?)');
  const day = 86400000;
  for (let i = 0; i < 2100; i++) ins.run('u' + i, 's' + i, `m${i}@x.com`, 'm' + i, clock - (i < 5 ? 2 * day : i < 15 ? 20 * day : 100 * day), clock - i);
  const N = 2102;
  const c = await pj(hub, '/v1/admin/members/count', { t: adm });
  assert.equal(c.s, 200);
  assert.equal(c.j.total, N);
  assert.equal(c.j.new7, 5 + 2);            // 5 個 2 天前＋剛登入的 andy、bob
  assert.equal(c.j.new30, 15 + 2);
  const l1 = await pj(hub, '/v1/admin/perm/list', { t: adm });
  assert.equal(l1.s, 200);
  assert.equal(l1.j.total, N);
  assert.equal(l1.j.users.length, 2000);
  assert.equal(l1.j.more, true);
  const l2 = await pj(hub, '/v1/admin/perm/list', { t: adm, offset: 2000 });
  assert.equal(l2.j.users.length, N - 2000);
  assert.equal(l2.j.more, false);
  assert.equal(new Set([...l1.j.users, ...l2.j.users].map((u) => u.email)).size, N);
  assert.equal((await pj(hub, '/v1/admin/members/count', { t: bob })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/members/count', {})).s, 403);
});
