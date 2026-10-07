/* 管理權限（worker.js 檔尾「管理權限區塊」）與 /v1/admin/* 伺服器端總閘的允許／拒絕驗收。跑法：node --test workers/account-api/tests/admins.test.mjs
 * 登入流程與假 Google 照抄 susp.test.mjs。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';

/* ---- 假的 Google token 端點：依授權碼回一張 id_token（跟 Google 一樣是 JWT 格式）---- */
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
let pending = {};          // code → { claims, challenge }
let lastTokenBody = null;
globalThis.fetch = async (url, init) => {
  if (String(url).startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body); lastTokenBody = p;
    const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    // PKCE：Google 會驗 code_verifier 的 SHA-256 等於當初的 code_challenge —— 假的 Google 也驗，才抓得到前端／Worker 算錯
    const { createHash } = await import('node:crypto');
    const ch = createHash('sha256').update(p.get('code_verifier')).digest('base64url');
    if (ch !== hit.challenge) return new Response('{"error":"invalid_grant","why":"pkce"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  throw new Error('測試不准連外網：' + url);
};

let clock = Date.parse('2026-09-27T04:00:00Z');
function env(extra = {}) {
  return { ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's3cret', ADMIN_EMAILS: 'andy@example.com', __now: () => clock, ...extra };
}
const post = (hub, path, body, origin = ORIGIN) => hub.fetch(new Request(API + path, {
  method: 'POST', headers: origin ? { Origin: origin, 'content-type': 'text/plain' } : { 'content-type': 'text/plain' }, body: JSON.stringify(body),
}));
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');

/* 走完一次真的登入流程（start → 假 Google → callback → redeem），回 { tok, user } */
async function login(hub, email, opts = {}) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/tw-rotation/')}`));
  assert.equal(s.status, 302);
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  const claims = { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true,
    name: email.split('@')[0], picture: 'https://lh3.googleusercontent.com/a/x', exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce'), ...(opts.claims || {}) };
  pending[code] = { claims, challenge: g.searchParams.get('code_challenge') };
  const cb = await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: opts.cookie || cookie } }));
  const r = await post(hub, '/auth/redeem', { n });
  return { cb, r, j: await r.json(), n };
}

/* ==== 管理權限區塊（worker.js 檔尾，2026-10-07 admin-only）==== */
const ADMIN_PATHS = ['/v1/admin/stats', '/v1/admin/online', '/v1/admin/settings', '/v1/admin/perm/get', '/v1/admin/perm/put', '/v1/admin/perm/list',
  '/v1/admin/plans/get', '/v1/admin/plans/put', '/v1/admin/plans/sort', '/v1/admin/members', '/v1/admin/member/detail', '/v1/admin/members/stats',
  '/v1/admin/notices/list', '/v1/admin/notices/put', '/v1/admin/notices/del', '/v1/admin/feedback/list', '/v1/admin/feedback/del', '/v1/admin/feedback/set',
  '/v1/admin/susp/list', '/v1/admin/susp/lift', '/v1/admin/uids', '/v1/admin/admins/list', '/v1/admin/admins/add', '/v1/admin/admins/del',
  '/v1/admin/no-such-endpoint'];

test('伺服器端總閘：每一支 /v1/admin/* 對訪客、一般會員一律 403（不能只靠前端藏按鈕）', async () => {
  const { hub } = makeHub(env());
  const m = (await login(hub, 'bob@example.com')).j.tok;
  for (const p of ADMIN_PATHS) {
    assert.equal((await post(hub, p, {})).status, 403, '訪客 ' + p);
    assert.equal((await post(hub, p, { t: m, email: 'bob@example.com', id: 'x', del: true, plan: 'free' })).status, 403, '一般會員 ' + p);
    assert.equal((await post(hub, p, { t: 'v1.x.1.1.bad' })).status, 403, '假權杖 ' + p);
  }
  // 一般會員的寫入嘗試沒有任何副作用
  const a = (await login(hub, 'andy@example.com')).j.tok;
  const l = await (await post(hub, '/v1/admin/admins/list', { t: a })).json();
  assert.deepEqual(l.admins, []);
});

test('擁有者（ADMIN_EMAILS）：/v1/me 帶 owner；可新增／移除管理者；被加的人下一個請求就是管理者', async () => {
  const { hub } = makeHub(env());
  const a = (await login(hub, 'andy@example.com')).j;
  assert.equal(a.user.admin, true); assert.equal(a.user.owner, true);
  const c = (await login(hub, 'carol@example.com')).j.tok;
  assert.equal((await post(hub, '/v1/admin/stats', { t: c })).status, 403);
  assert.equal((await post(hub, '/v1/admin/admins/add', { t: a.tok, email: 'not-an-email' })).status, 400);
  const r = await post(hub, '/v1/admin/admins/add', { t: a.tok, email: ' Carol@Example.com ' });
  assert.equal(r.status, 200);
  assert.equal((await post(hub, '/v1/admin/admins/add', { t: a.tok, email: 'carol@example.com' })).status, 409, '重複新增');
  assert.equal((await post(hub, '/v1/admin/admins/add', { t: a.tok, email: 'andy@example.com' })).status, 409, '擁有者本來就是');
  const me = await (await post(hub, '/v1/me', { t: c })).json();
  assert.equal(me.user.admin, true); assert.equal(me.user.owner, false);
  assert.equal((await post(hub, '/v1/admin/stats', { t: c })).status, 200);
  const l = await (await post(hub, '/v1/admin/admins/list', { t: c })).json();
  assert.deepEqual(l.owners.map((x) => x.email), ['andy@example.com']);
  assert.equal(l.admins.length, 1); assert.equal(l.admins[0].email, 'carol@example.com'); assert.equal(l.admins[0].by, 'andy@example.com');
  assert.equal(l.me.owner, false);
  assert.equal(l.log[0].act, 'add');
});

test('只有擁有者能新增／移除：一般管理者 403；擁有者不能被移除；移除後舊權杖失效、重新登入只是一般會員；稽核紀錄 append-only', async () => {
  const { hub } = makeHub(env());
  const a = (await login(hub, 'andy@example.com')).j.tok;
  const c = (await login(hub, 'carol@example.com')).j.tok;
  await post(hub, '/v1/admin/admins/add', { t: a, email: 'carol@example.com' });
  assert.equal((await post(hub, '/v1/admin/admins/add', { t: c, email: 'dave@example.com' })).status, 403, '一般管理者不能加人');
  assert.equal((await post(hub, '/v1/admin/admins/del', { t: c, email: 'andy@example.com' })).status, 403, '一般管理者不能拔擁有者');
  assert.equal((await post(hub, '/v1/admin/admins/del', { t: c, email: 'carol@example.com' })).status, 403, '一般管理者不能動名單');
  assert.equal((await post(hub, '/v1/admin/admins/del', { t: a, email: 'andy@example.com' })).status, 409, '擁有者不能被移除');
  assert.equal((await post(hub, '/v1/admin/admins/del', { t: a, email: 'nobody@example.com' })).status, 404);
  assert.equal((await post(hub, '/v1/admin/admins/del', { t: a, email: 'carol@example.com' })).status, 200);
  assert.equal((await post(hub, '/v1/me', { t: c })).status, 401, '舊權杖立即失效');
  assert.equal((await post(hub, '/v1/admin/stats', { t: c })).status, 403);
  const c2 = (await login(hub, 'carol@example.com')).j;
  assert.equal(c2.user.admin, false);
  assert.equal((await post(hub, '/v1/admin/stats', { t: c2.tok })).status, 403);
  const l = await (await post(hub, '/v1/admin/admins/list', { t: a })).json();
  assert.deepEqual(l.admins, []);
  assert.deepEqual(l.log.map((x) => [x.act, x.email, x.by]), [['del', 'carol@example.com', 'andy@example.com'], ['add', 'carol@example.com', 'andy@example.com']]);
  // 再加回來：新的一列，舊列不動
  await post(hub, '/v1/admin/admins/add', { t: a, email: 'carol@example.com' });
  const l2 = await (await post(hub, '/v1/admin/admins/list', { t: a })).json();
  assert.equal(l2.log.length, 3); assert.equal(l2.admins.length, 1);
});
