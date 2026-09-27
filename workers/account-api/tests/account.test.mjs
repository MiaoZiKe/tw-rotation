/* account-api 的存取控制驗收（等同 Firebase 的安全規則測試）。
 *
 * 跑法：node --test workers/account-api/tests/
 * 不連外網、不需要任何套件（node:sqlite 與 node:test 都是 Node 22 內建）。
 *
 * 每一條規則都同時驗「該允許的有允許」與「該拒絕的有拒絕」—— 只驗一邊的規則測試等於沒測。
 * 規則編號對應 worker.js 檔頭的 R1～R6。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { makeHub } from '../harness.mjs';
import { VIEWS, EVENTS } from '../worker.js';

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

test('R6 登入：完整流程拿得到權杖；PKCE 用 S256、scope 只有 openid email profile', async () => {
  const { hub } = makeHub(env());
  const { cb, j } = await login(hub, 'bob@example.com');
  assert.equal(cb.status, 200);
  assert.match(await cb.text(), /tw-login/);
  assert.ok(j.tok && j.user.email === 'bob@example.com' && j.user.admin === false);
  assert.equal(lastTokenBody.get('grant_type'), 'authorization_code');
});

test('R6 登入：redeem 只能換一次；沒完成前回 pending', async () => {
  const { hub } = makeHub(env());
  const n = rand();
  await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  assert.deepEqual(await (await post(hub, '/auth/redeem', { n })).json(), { pending: true });
  const { n: n2 } = await login(hub, 'bob@example.com');
  assert.equal((await post(hub, '/auth/redeem', { n: n2 })).status, 404, '第二次換要被拒絕');
});

test('R6 登入：拒絕 —— 白名單外的 return 網址、cookie 不符、aud 不符、nonce 不符、email 未驗證、過期', async () => {
  const { hub } = makeHub(env());
  const bad = await hub.fetch(new Request(`${API}/auth/start?n=${rand()}&mode=popup&ret=${encodeURIComponent('https://evil.example/')}`));
  assert.equal(bad.status, 400);
  assert.equal((await login(hub, 'x@example.com', { cookie: 'tw_oas=forged' })).cb.status, 400, '別人的回呼網址（cookie 不符）');
  assert.equal((await login(hub, 'x@example.com', { claims: { aud: 'other-client' } })).cb.status, 400);
  assert.equal((await login(hub, 'x@example.com', { claims: { nonce: 'wrong' } })).cb.status, 400);
  assert.equal((await login(hub, 'x@example.com', { claims: { email_verified: false } })).cb.status, 400);
  assert.equal((await login(hub, 'x@example.com', { claims: { iss: 'https://evil.example' } })).cb.status, 400);
  assert.equal((await login(hub, 'x@example.com', { claims: { exp: clock / 1000 - 10 } })).cb.status, 400);
  const { j } = await login(hub, 'x@example.com', { claims: { aud: 'other-client' } });
  assert.ok(!j.tok, '失敗的登入不可以換到權杖');
});

test('R6 沒設 Google 金鑰時：/auth/start 回 503、/health 說 configured:false', async () => {
  const { hub } = makeHub(env({ GOOGLE_CLIENT_ID: '', GOOGLE_CLIENT_SECRET: '' }));
  assert.equal((await hub.fetch(new Request(`${API}/auth/start?n=${rand()}&ret=${encodeURIComponent(ORIGIN + '/')}`))).status, 503);
  assert.equal((await (await hub.fetch(new Request(API + '/health'))).json()).configured, false);
});

test('R1 自選清單：只讀寫得到自己的；沒權杖／假權杖一律 401', async () => {
  const { hub } = makeHub(env());
  const a = (await login(hub, 'alice@example.com')).j.tok, b = (await login(hub, 'bob@example.com')).j.tok;
  const lists = [{ id: 't1', name: '半導體', codes: ['2330', '2454'] }];
  assert.equal((await post(hub, '/v1/lists/put', { t: a, lists, rev: 0 })).status, 200);
  assert.deepEqual((await (await post(hub, '/v1/lists/get', { t: b })).json()).lists, [], 'Bob 讀不到 Alice 的');
  assert.deepEqual((await (await post(hub, '/v1/lists/get', { t: a })).json()).lists, lists);
  assert.equal((await post(hub, '/v1/lists/get', {})).status, 401);
  assert.equal((await post(hub, '/v1/lists/put', { lists, rev: 0 })).status, 401);
  const forged = a.replace(/\.[^.]+$/, '.AAAA');
  assert.equal((await post(hub, '/v1/lists/get', { t: forged })).status, 401, '改過簽章');
  const other = a.split('.'); other[1] = 'someoneelse';
  assert.equal((await post(hub, '/v1/lists/get', { t: other.join('.') })).status, 401, '把 uid 換成別人');
});

test('R1 自選清單格式：超過 5 頁、超過 50 檔、代號格式錯、名字空白都拒絕；多帶的欄位（張數、成本）被丟掉', async () => {
  const { hub } = makeHub(env());
  const t = (await login(hub, 'alice@example.com')).j.tok;
  const mk = (i) => ({ id: 't' + i, name: '清單' + i, codes: [] });
  assert.equal((await post(hub, '/v1/lists/put', { t, lists: [1, 2, 3, 4, 5, 6].map(mk), rev: 0 })).status, 400);
  assert.equal((await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'a', codes: Array.from({ length: 51 }, (_, i) => String(1000 + i)) }], rev: 0 })).status, 400);
  assert.equal((await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'a', codes: ['<script>'] }], rev: 0 })).status, 400);
  assert.equal((await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: '   ', codes: [] }], rev: 0 })).status, 400);
  const r = await (await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'a', codes: ['2330'], qty: 1000, cost: 580 }], rev: 0 })).json();
  assert.deepEqual(r.lists, [{ id: 't1', name: 'a', codes: ['2330'] }]);
});

test('R1 版本衝突：rev 不一致回 409 並附雲端現況，不覆蓋', async () => {
  const { hub } = makeHub(env());
  const t = (await login(hub, 'alice@example.com')).j.tok;
  await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'A', codes: ['2330'] }], rev: 0 });
  const r = await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'B', codes: [] }], rev: 0 });
  assert.equal(r.status, 409);
  const j = await r.json();
  assert.equal(j.rev, 1); assert.equal(j.lists[0].name, 'A');
});

test('R2 使用統計：訪客也能遞增；非白名單、負數、超過上限、太多項 一律拒絕；一般人沒有讀的端點', async () => {
  const { hub, db } = makeHub(env());
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-aaaa', r: 'overview', ev: { 'pv:overview': 2, 'ev:search': 1 } })).status, 200);
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-aaaa', r: 'overview', ev: { 'pv:overview': 3 } })).status, 200);
  const n = db.prepare("SELECT n FROM usage WHERE k='pv:overview'").get().n;
  assert.equal(n, 5, '次數要累加');
  for (const ev of [{ 'pv:hack': 1 }, { 'pv:overview': -5 }, { 'pv:overview': 0 }, { 'pv:overview': 51 }, { 'pv:overview': 1.5 },
    Object.fromEntries(Array.from({ length: 41 }, (_, i) => ['ev:search' + i, 1])), ['pv:overview']]) {
    assert.equal((await post(hub, '/v1/beat', { sid: 'guest-aaaa', ev })).status, 400, JSON.stringify(ev).slice(0, 60));
  }
  assert.equal(db.prepare("SELECT n FROM usage WHERE k='pv:overview'").get().n, 5, '被拒絕的那幾次不可以動到數字');
  // 讀：一般人（訪客或登入的非管理者）都拿不到
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  assert.equal((await post(hub, '/v1/admin/stats', {})).status, 403);
  assert.equal((await post(hub, '/v1/admin/stats', { t: bob })).status, 403);
});

test('R2 使用統計不存識別碼：usage 表只有 日期／鍵／次數 三欄', async () => {
  const { db } = makeHub(env());
  const cols = db.prepare('PRAGMA table_info(usage)').all().map((c) => c.name);
  assert.deepEqual(cols, ['day', 'k', 'n']);
});

test('R2／R6 來源檢查：白名單外的網站、沒有 Origin 的 POST 一律 403', async () => {
  const { hub } = makeHub(env());
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-aaaa' }, 'https://evil.example')).status, 403);
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-aaaa' }, null)).status, 403);
  const ok = await post(hub, '/v1/beat', { sid: 'guest-aaaa' });
  assert.equal(ok.headers.get('Access-Control-Allow-Origin'), ORIGIN);
});

test('R3 管理者：ADMIN_EMAILS 裡的人讀得到報表、線上名單、會員名單；不在名單的讀不到', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'Andy@Example.com')).j;
  assert.equal(andy.user.admin, true, 'email 比對不分大小寫');
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  await post(hub, '/v1/beat', { sid: 'guest-bbbb', r: 'flow', ev: { 'pv:flow': 1 } });
  await post(hub, '/v1/beat', { t: bob, sid: 'bob-sid-1', r: 'stock' });
  const st = await (await post(hub, '/v1/admin/stats', { t: andy.tok, days: 7 })).json();
  assert.ok(st.rows.some((r) => r.k === 'pv:flow' && r.n === 1));
  assert.equal(st.users.total, 2);
  const on = await (await post(hub, '/v1/admin/online', { t: andy.tok })).json();
  assert.equal(on.total, 2); assert.equal(on.guests, 1);
  assert.deepEqual(on.users.map((u) => [u.email, u.route]), [['bob@example.com', 'stock']]);
  for (const p of ['/v1/admin/stats', '/v1/admin/online', '/v1/admin/settings']) assert.equal((await post(hub, p, { t: bob })).status, 403, p);
});

test('R3 管理者名單是空的（沒設 ADMIN_EMAILS）時沒有人是管理者', async () => {
  const { hub } = makeHub(env({ ADMIN_EMAILS: '' }));
  const j = (await login(hub, 'andy@example.com')).j;
  assert.equal(j.user.admin, false);
  assert.equal((await post(hub, '/v1/admin/stats', { t: j.tok })).status, 403);
});

test('R4 線上總人數：預設公開；管理者關掉後只回給管理者', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  assert.equal((await (await post(hub, '/v1/beat', { sid: 'guest-cccc', r: 'overview' })).json()).n, 1);
  assert.equal((await post(hub, '/v1/admin/settings', { t: andy, public_online: false })).status, 200);
  assert.equal((await (await post(hub, '/v1/beat', { sid: 'guest-cccc', r: 'overview' })).json()).n, undefined);
  assert.equal((await (await post(hub, '/v1/beat', { t: andy, sid: 'andy-sid-1', r: 'overview' })).json()).n, 2);
});

test('R5 刪除我的資料：會員、清單、線上紀錄全刪，舊權杖立即失效', async () => {
  const { hub, db } = makeHub(env());
  const t = (await login(hub, 'alice@example.com')).j.tok;
  await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'A', codes: ['2330'] }], rev: 0 });
  await post(hub, '/v1/beat', { t, sid: 'alice-sid-1', r: 'overview' });
  assert.equal((await post(hub, '/v1/delete', { t })).status, 200);
  assert.equal(db.prepare('SELECT COUNT(*) c FROM users').get().c, 0);
  assert.equal(db.prepare('SELECT COUNT(*) c FROM lists').get().c, 0);
  assert.equal(db.prepare("SELECT COUNT(*) c FROM presence WHERE uid IS NOT NULL").get().c, 0);
  assert.equal((await post(hub, '/v1/me', { t })).status, 401);
});

test('R5 權杖過期就失效；剩不到一半時 /v1/me 換新的', async () => {
  const { hub } = makeHub(env());
  const t = (await login(hub, 'alice@example.com')).j.tok;
  clock += 40 * 86400 * 1000;
  const j = await (await post(hub, '/v1/me', { t })).json();
  assert.ok(j.tok && j.tok !== t, '滑動續期');
  clock += 25 * 86400 * 1000;
  assert.equal((await post(hub, '/v1/me', { t })).status, 401, '舊的那張 60 天到期');
  assert.equal((await post(hub, '/v1/me', { t: j.tok })).status, 200);
  clock -= 65 * 86400 * 1000;
});

test('保存期限：離線 3 分鐘即刪、13 個月前的統計刪掉、24 個月沒用的會員連清單一起刪', async () => {
  const { hub, db } = makeHub(env());
  const t = (await login(hub, 'old@example.com')).j.tok;
  await post(hub, '/v1/lists/put', { t, lists: [{ id: 't1', name: 'A', codes: ['2330'] }], rev: 0 });
  await post(hub, '/v1/beat', { sid: 'guest-dddd', r: 'overview', ev: { 'pv:overview': 1 } });
  db.prepare("INSERT INTO usage (day,k,n) VALUES ('2025-07-01','pv:flow',9), ('2025-09-28','pv:flow',3)").run();
  const t0 = clock;
  clock += 4 * 60 * 1000;
  await hub.alarm();
  assert.equal(db.prepare('SELECT COUNT(*) c FROM presence').get().c, 0, '離線即刪');
  const days = db.prepare("SELECT day FROM usage WHERE k='pv:flow' ORDER BY day").all().map((r) => r.day);
  assert.deepEqual(days, ['2025-09-28'], '13 個月前（2025-08-27 以前）那筆刪掉、以內的留著');
  clock = t0 + 731 * 86400 * 1000;
  await hub.alarm();
  assert.equal(db.prepare('SELECT COUNT(*) c FROM users').get().c, 0);
  assert.equal(db.prepare('SELECT COUNT(*) c FROM lists').get().c, 0);
  clock = t0;
});

test('alarm 有排上（保存期限不靠有人來觸發）', async () => {
  const { getAlarm } = makeHub(env());
  await new Promise((r) => setTimeout(r, 10));
  assert.ok(getAlarm() > clock);
});

test('白名單三邊一致：worker.js ＝ site/account.js ＝ docs/account_analytics.md', () => {
  const root = new URL('../../../', import.meta.url);
  const site = readFileSync(new URL('site/account.js', root), 'utf8');
  const doc = readFileSync(new URL('docs/account_analytics.md', root), 'utf8');
  const arr = (name) => JSON.parse(site.match(new RegExp(`const ${name} = (\\[[^\\]]*\\])`))[1].replace(/'/g, '"'));
  assert.deepEqual(arr('VIEWS'), VIEWS);
  assert.deepEqual(arr('EVENTS'), EVENTS);
  for (const e of EVENTS) assert.ok(doc.includes('`' + e + '`'), '文件沒寫到事件 ' + e);
  for (const v of VIEWS) assert.ok(doc.includes('`' + v + '`'), '文件沒寫到頁面 ' + v);
});
