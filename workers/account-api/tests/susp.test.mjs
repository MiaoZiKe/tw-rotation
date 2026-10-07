/* data-gw 停權端點（worker.js 檔尾「data-gw 停權區塊」）的允許／拒絕驗收。跑法：node --test workers/account-api/tests/susp.test.mjs
 * 登入流程與假 Google 照抄 account.test.mjs。
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

const KEY = 'internal-test-key-not-real';
const susp = (hub, body, key = KEY) => hub.fetch(new Request(API + '/internal/suspend', {
  method: 'POST', headers: key ? { 'X-Internal-Key': key, 'content-type': 'text/plain' } : { 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
const uidOf = (tok) => tok.split('.')[1];

test('停權端點：沒設 INTERNAL_KEY＝不存在（404）；沒帶鑰匙／鑰匙不對＝403，且沒有副作用', async () => {
  const { hub } = makeHub(env());
  const { j } = await login(hub, 'bob@example.com');
  assert.equal((await susp(hub, { uid: uidOf(j.tok) })).status, 404);
  const { hub: h2 } = makeHub(env({ INTERNAL_KEY: KEY }));
  const b = await login(h2, 'bob@example.com');
  assert.equal((await susp(h2, { uid: uidOf(b.j.tok) }, null)).status, 403);
  assert.equal((await susp(h2, { uid: uidOf(b.j.tok) }, KEY + 'x')).status, 403);
  assert.equal((await post(h2, '/v1/me', { t: b.j.tok })).status, 200);
});

test('停權：tv 遞增、舊權杖立刻失效；重新登入拿到的新權杖也不能用；重複停權不重寫', async () => {
  const { hub } = makeHub(env({ INTERNAL_KEY: KEY }));
  const { j } = await login(hub, 'bob@example.com');
  const uid = uidOf(j.tok);
  const tv0 = hub.q('SELECT tv FROM users WHERE uid = ?', uid)[0].tv;
  assert.equal((await susp(hub, { uid, reason: 'burst 3 次' })).status, 200);
  assert.equal(hub.q('SELECT tv FROM users WHERE uid = ?', uid)[0].tv, tv0 + 1);
  assert.equal((await post(hub, '/v1/me', { t: j.tok })).status, 401);
  const again = await login(hub, 'bob@example.com');
  /* 重新登入：redeem 會先驗新權杖 → 停權中驗不過 → 拿不到可用的權杖 */
  assert.ok(!again.j.tok || (await post(hub, '/v1/perm/me', { t: again.j.tok })).status === 401, '停權中重新登入也拿不到會員身分');
  assert.equal((await susp(hub, { uid })).status, 200);
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM susp WHERE uid = ?', uid)[0].c, 1);
});

test('管理者：看紀錄、uid 換 email、解除（append-only：多一列 lift）；一般會員不能看也不能解', async () => {
  const { hub } = makeHub(env({ INTERNAL_KEY: KEY }));
  const bob = await login(hub, 'bob@example.com');
  const carol = await login(hub, 'carol@example.com');
  const andy = await login(hub, 'andy@example.com');
  const uid = uidOf(bob.j.tok);
  await susp(hub, { uid, reason: 'multi_ip' });
  assert.equal((await post(hub, '/v1/admin/susp/list', { t: carol.j.tok })).status, 403);
  assert.equal((await post(hub, '/v1/admin/susp/lift', { t: carol.j.tok, uid })).status, 403);
  assert.equal((await post(hub, '/v1/admin/uids', { t: carol.j.tok, uids: [uid] })).status, 403);
  const l = await (await post(hub, '/v1/admin/susp/list', { t: andy.j.tok })).json();
  assert.equal(l.rows[0].email, 'bob@example.com'); assert.equal(l.rows[0].now, true);
  const u = await (await post(hub, '/v1/admin/uids', { t: andy.j.tok, uids: [uid] })).json();
  assert.equal(u.users[uid].email, 'bob@example.com'); assert.equal(u.users[uid].susp, true);
  assert.equal((await post(hub, '/v1/admin/susp/lift', { t: andy.j.tok, uid, note: '誤判' })).status, 200);
  assert.deepEqual(hub.q('SELECT act FROM susp WHERE uid = ? ORDER BY id', uid).map((r) => r.act), ['suspend', 'lift']);
  const back = await login(hub, 'bob@example.com');
  assert.equal((await post(hub, '/v1/me', { t: back.j.tok })).status, 200);
  assert.equal((await post(hub, '/v1/admin/susp/lift', { t: andy.j.tok, uid })).status, 400);
});

test('管理者帳號不會被停；壞的 uid、不存在的 uid 拒絕', async () => {
  const { hub } = makeHub(env({ INTERNAL_KEY: KEY }));
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await susp(hub, { uid: uidOf(andy.j.tok) })).status, 409);
  assert.equal((await susp(hub, { uid: '../x' })).status, 400);
  assert.equal((await susp(hub, { uid: 'nobody1' })).status, 404);
  assert.equal((await post(hub, '/v1/me', { t: andy.j.tok })).status, 200);
});
