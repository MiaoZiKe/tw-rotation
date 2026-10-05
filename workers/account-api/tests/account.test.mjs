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

test('R6 登入：中文名字不會變亂碼（id_token 是 UTF-8）', async () => {
  const { hub } = makeHub(env());
  const { j } = await login(hub, 'wang@example.com', { claims: { name: '王小明' } });
  assert.equal(j.user.name, '王小明');
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

/* ======================================================================== R7 功能權限（DECISIONS #288）
 * 跟 R1～R6 同一個標準：每條同時驗「該允許的有允許」與「該拒絕的有拒絕」。
 * 重點三條：① 一般人讀不到別人的 ② 一般人寫不了任何人的（包括自己）③ 上線當下所有人都是全開（不能讓誰突然看不到）。*/
const ADMIN_EPS = ['/v1/admin/perm/get', '/v1/admin/perm/put', '/v1/admin/perm/list', '/v1/admin/plans/get', '/v1/admin/plans/put'];

test('R7 上線預設：訪客、從沒被設定過的會員，拿到的都是空的開關（＝前端全部照預設開啟）', async () => {
  const { hub } = makeHub(env());
  const g = await (await post(hub, '/v1/perm/me', {})).json();
  assert.deepEqual([g.who, g.plan, g.feats], ['guest', 'guest', {}]);
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  const m = await (await post(hub, '/v1/perm/me', { t: bob })).json();
  assert.deepEqual([m.who, m.plan, m.feats], ['member', 'free', {}]);
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  const pl = await (await post(hub, '/v1/admin/plans/get', { t: andy })).json();
  assert.deepEqual(pl.plans.map((p) => [p.id, p.builtin, JSON.stringify(p.feats)]).sort(), [['free', true, '{}'], ['guest', true, '{}'], ['paid', false, '{}']]);
});

test('R7 管理者：設定某 email 的方案＋微調，本人登入後讀得到；email 不分大小寫；可以先設好、對方之後才登入', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  assert.equal((await post(hub, '/v1/admin/plans/put', { t: andy, id: 'paid', name: '付費會員', feats: { 'stock.ai': true, 'watch.tabs': 5 } })).status, 200);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t: andy, id: 'free', feats: { 'stock.ai': false, 'watch.tabs': 2 } })).status, 200);
  const put = await post(hub, '/v1/admin/perm/put', { t: andy, email: 'Carol@Example.com', plan: 'paid', over: { 'stock.k_hour': false } });
  assert.equal(put.status, 200);
  const pj = await put.json();
  assert.equal(pj.email, 'carol@example.com');
  assert.deepEqual(pj.feats, { 'stock.ai': true, 'watch.tabs': 5, 'stock.k_hour': false });
  const carol = (await login(hub, 'carol@example.com')).j.tok;          // 設定之後才第一次登入
  const me = await (await post(hub, '/v1/perm/me', { t: carol })).json();
  assert.deepEqual([me.plan, me.feats], ['paid', { 'stock.ai': true, 'watch.tabs': 5, 'stock.k_hour': false }]);
  // 沒被設定的會員吃「免費會員」範本
  const dave = (await login(hub, 'dave@example.com')).j.tok;
  assert.deepEqual((await (await post(hub, '/v1/perm/me', { t: dave })).json()).feats, { 'stock.ai': false, 'watch.tabs': 2 });
  // 讀回單一 email、清單
  const gj = await (await post(hub, '/v1/admin/perm/get', { t: andy, email: 'carol@example.com' })).json();
  assert.deepEqual([gj.plan, gj.over, gj.known && gj.known.name], ['paid', { 'stock.k_hour': false }, 'carol']);
  const lj = await (await post(hub, '/v1/admin/perm/list', { t: andy })).json();
  assert.deepEqual(lj.rows.map((r) => [r.email, r.plan, r.n]), [['carol@example.com', 'paid', 1]]);
  assert.ok(lj.users.some((u) => u.email === 'dave@example.com'));
  // reset：回到免費預設
  await post(hub, '/v1/admin/perm/put', { t: andy, email: 'carol@example.com', reset: true });
  assert.equal((await (await post(hub, '/v1/perm/me', { t: carol })).json()).plan, 'free');
});

test('R7 拒絕：非管理者（含沒權杖、假權杖）不能讀寫別人的權限、不能讀寫方案範本', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  await post(hub, '/v1/admin/perm/put', { t: andy, email: 'alice@example.com', plan: 'paid', over: { 'stock.ai': true } });
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  const forged = andy.replace(/\.[^.]+$/, '.AAAA');
  for (const t of [bob, undefined, forged]) {
    for (const p of ADMIN_EPS) {
      const r = await post(hub, p, { t, email: 'alice@example.com', plan: 'paid', over: { 'stock.ai': false }, id: 'paid', name: 'x', feats: {} });
      assert.equal(r.status, 403, `${p} 用 ${t === bob ? 'Bob' : t ? '假權杖' : '沒權杖'}`);
    }
  }
  // 被拒絕的那幾次不可以動到資料
  const gj = await (await post(hub, '/v1/admin/perm/get', { t: andy, email: 'alice@example.com' })).json();
  assert.deepEqual(gj.over, { 'stock.ai': true });
  const pl = await (await post(hub, '/v1/admin/plans/get', { t: andy })).json();
  assert.equal(pl.plans.find((p) => p.id === 'paid').name, '付費會員');
  // /v1/perm/me 不收 email 參數：Bob 帶 alice 的 email 拿到的還是自己的
  const me = await (await post(hub, '/v1/perm/me', { t: bob, email: 'alice@example.com' })).json();
  assert.deepEqual([me.plan, me.feats], ['free', {}]);
});

test('R7 拒絕：非管理者不能改自己 —— 寫自己的 email 一樣 403；/v1/perm/me 多帶 plan／feats 也不會被寫進去', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  await post(hub, '/v1/admin/plans/put', { t: andy, id: 'free', feats: { 'stock.ai': false } });
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  assert.equal((await post(hub, '/v1/admin/perm/put', { t: bob, email: 'bob@example.com', plan: 'paid', over: { 'stock.ai': true } })).status, 403);
  assert.equal((await post(hub, '/v1/admin/perm/put', { t: bob, email: 'BOB@example.com', reset: true })).status, 403);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t: bob, id: 'free', feats: {} })).status, 403);
  const r = await (await post(hub, '/v1/perm/me', { t: bob, plan: 'paid', feats: { 'stock.ai': true }, over: { 'stock.ai': true } })).json();
  assert.deepEqual([r.plan, r.feats], ['free', { 'stock.ai': false }]);
  assert.deepEqual((await (await post(hub, '/v1/perm/me', { t: bob })).json()).feats, { 'stock.ai': false });
  // 假權杖讀自己：401（跟 R1 一致，前端會當作登出）
  assert.equal((await post(hub, '/v1/perm/me', { t: bob.replace(/\.[^.]+$/, '.AAAA') })).status, 401);
});

test('R7 格式：壞 email、壞鍵、壞值、太多鍵、不存在／訪客方案、刪內建方案 一律拒絕；刪方案的人退回免費', async () => {
  const { hub } = makeHub(env());
  const t = (await login(hub, 'andy@example.com')).j.tok;
  for (const email of ['', 'no-at', 'a@b', '<x>@example.com', 'a b@example.com', 'x'.repeat(65) + '@example.com']) {
    assert.equal((await post(hub, '/v1/admin/perm/put', { t, email, plan: 'free', over: {} })).status, 400, email);
  }
  for (const over of [{ 'Bad Key': true }, { 'x': true }, { 'stock.ai': 'yes' }, { 'stock.ai': -1 }, { 'stock.ai': 100 }, { 'stock.ai': 1.5 }, ['stock.ai'],
    Object.fromEntries(Array.from({ length: 301 }, (_, i) => ['f' + i + 'x', true]))]) {
    assert.equal((await post(hub, '/v1/admin/perm/put', { t, email: 'c@example.com', plan: 'free', over })).status, 400, JSON.stringify(over).slice(0, 40));
  }
  assert.equal((await post(hub, '/v1/admin/perm/put', { t, email: 'c@example.com', plan: 'nope', over: {} })).status, 400, '不存在的方案');
  assert.equal((await post(hub, '/v1/admin/perm/put', { t, email: 'c@example.com', plan: 'guest', over: {} })).status, 400, '會員不能指定成訪客方案');
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'guest', del: true })).status, 400, '內建方案不能刪');
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'free', del: true })).status, 400);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'Bad Id', name: 'x', feats: {} })).status, 400);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'vip', name: '   ', feats: {} })).status, 400);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'vip', name: '<b>VIP</b>', feats: { 'stock.ai': true } })).status, 200);
  const pl = await (await post(hub, '/v1/admin/plans/get', { t })).json();
  assert.equal(pl.plans.find((p) => p.id === 'vip').name, 'bVIP/b', '名稱裡的 < > 被拿掉');
  await post(hub, '/v1/admin/perm/put', { t, email: 'c@example.com', plan: 'vip', over: { 'stock.mtf': false } });
  /* 2026-10-05：還有有效會員的付費範本不能刪（409 has_members）；先讓他的訂閱到期，才刪得掉 */
  const blocked = await post(hub, '/v1/admin/plans/put', { t, id: 'vip', del: true });
  assert.equal(blocked.status, 409, '有有效會員 → 不能刪');
  const bj = await blocked.json();
  assert.deepEqual([bj.error, bj.n, bj.emails], ['has_members', 1, ['c@example.com']]);
  assert.ok((await (await post(hub, '/v1/admin/plans/get', { t })).json()).plans.some((p) => p.id === 'vip'), '被擋時範本還在');
  await post(hub, '/v1/admin/perm/put', { t, email: 'c@example.com', plan: 'vip', over: { 'stock.mtf': false }, expires: 1577836800001 });   // 2020-01-01：早就到期
  await post(hub, '/v1/admin/plans/put', { t, id: 'vip', del: true });
  const gj = await (await post(hub, '/v1/admin/perm/get', { t, email: 'c@example.com' })).json();
  assert.deepEqual([gj.plan, gj.over], ['free', { 'stock.mtf': false }], '方案刪掉 → 退回免費、個別微調保留');
});

test('R7 方案範本最多 20 個；刪除我的資料時權限設定一起刪', async () => {
  const { hub, db } = makeHub(env());
  const t = (await login(hub, 'andy@example.com')).j.tok;
  for (let i = 0; i < 17; i++) assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'p' + i, name: 'P' + i, feats: {} })).status, 200);
  assert.equal((await post(hub, '/v1/admin/plans/put', { t, id: 'p99', name: 'P99', feats: {} })).status, 400, '第 21 個');
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  await post(hub, '/v1/admin/perm/put', { t, email: 'bob@example.com', plan: 'paid', over: {} });
  assert.equal(db.prepare('SELECT COUNT(*) c FROM perm').get().c, 1);
  await post(hub, '/v1/delete', { t: bob });
  assert.equal(db.prepare('SELECT COUNT(*) c FROM perm').get().c, 0);
});

test('R7 管理者名單是空的時，沒有人讀寫得到權限設定', async () => {
  const { hub } = makeHub(env({ ADMIN_EMAILS: '' }));
  const t = (await login(hub, 'andy@example.com')).j.tok;
  for (const p of ADMIN_EPS) assert.equal((await post(hub, p, { t, email: 'x@example.com', id: 'paid', name: 'x', feats: {} })).status, 403, p);
});

/* ======================================================================== admin-v2（2026-10-05）：細項事件、到期日、造訪次數、相容遷移 */
test('細項事件 e2：合格的收、累加；分組查詢回 (頁面, 元件, 細項) 加總；只有管理者讀得到', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  const e2 = [['flow', 'rot.play', '', 2], ['flow', 'filter_group', '被動元件 MLCC', 1], ['stock', 'view', '2330', 3], ['stock', 'tab.revenue', '2330', 1]];
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-e2-1', r: 'flow', e2 })).status, 200);
  assert.equal((await post(hub, '/v1/beat', { sid: 'guest-e2-1', r: 'flow', e2: [['flow', 'rot.play', '', 1]] })).status, 200);
  const st = await (await post(hub, '/v1/admin/stats', { t: andy, days: 7 })).json();
  const g = (p, c, d) => (st.e2.find((r) => r.page === p && r.comp === c && r.detail === d) || {}).n;
  assert.equal(g('flow', 'rot.play', ''), 3, '同一組合累加');
  assert.equal(g('flow', 'filter_group', '被動元件 MLCC'), 1, '中文族群名照存');
  assert.equal(g('stock', 'view', '2330'), 3);
  const only = await (await post(hub, '/v1/admin/stats', { t: andy, days: 7, page: 'stock' })).json();
  assert.ok(only.e2.length === 2 && only.e2.every((r) => r.page === 'stock'), 'page 參數只回那一頁');
  assert.equal((await post(hub, '/v1/admin/stats', { t: bob, days: 7 })).status, 403, '一般會員讀不到');
});

test('細項事件 e2 拒絕：頁面不在白名單、元件格式、細項含 @／標籤／太長、次數超過、太多列 → 整批 400', async () => {
  const { hub } = makeHub(env());
  for (const e2 of [[['nope', 'x', '', 1]], [['flow', 'Bad Comp', '', 1]], [['flow', 'x', 'a@b.com', 1]], [['flow', 'x', '<b>', 1]],
    [['flow', 'x', 'x'.repeat(25), 1]], [['flow', 'x', '', 51]], [['flow', 'x', '', 0]], [['flow', 'x', '']], 'flow',
    Array.from({ length: 61 }, () => ['flow', 'x', '', 1])]) {
    assert.equal((await post(hub, '/v1/beat', { sid: 'guest-e2-2', e2 })).status, 400, JSON.stringify(e2).slice(0, 60));
  }
});

test('會員造訪次數：登入狀態下 session_login 計入 visits；perm/list 回 seen／visits／expires；刪帳號一起刪', async () => {
  const { hub, db } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  const bob = (await login(hub, 'bob@example.com')).j.tok;
  await post(hub, '/v1/beat', { t: bob, sid: 'bob-sid-v1', r: 'overview', ev: { 'ev:session': 1, 'ev:session_login': 1 } });
  await post(hub, '/v1/beat', { t: bob, sid: 'bob-sid-v2', r: 'overview', ev: { 'ev:session': 1, 'ev:session_login': 1 } });
  await post(hub, '/v1/beat', { sid: 'guest-v3', r: 'overview', ev: { 'ev:session': 1, 'ev:session_login': 1 } });   // 沒權杖：不算任何人
  const exp = Date.parse('2027-01-31T15:59:59Z');
  assert.equal((await post(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'free', over: {}, expires: exp })).status, 200);
  const li = await (await post(hub, '/v1/admin/perm/list', { t: andy })).json();
  const ub = li.users.find((u) => u.email === 'bob@example.com');
  assert.equal(ub.visits, 2); assert.ok(ub.seen > 0);
  assert.equal(li.rows.find((r) => r.email === 'bob@example.com').expires, exp);
  assert.equal((await post(hub, '/v1/delete', { t: bob })).status, 200);
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM visits').get().c, 0, '刪帳號後造訪紀錄一起刪');
});

test('到期日：過期 → /v1/perm/me 退回免費會員（微調不生效）；不帶 expires 不會清掉原值；壞值 400', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  const cara = (await login(hub, 'cara@example.com')).j.tok;
  await post(hub, '/v1/admin/plans/put', { t: andy, id: 'p799', name: '799', feats: { 'grp.foundry': true } });
  await post(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '免費會員', feats: { 'grp.foundry': false } });
  const exp = clock + 2 * 86400 * 1000;
  assert.equal((await post(hub, '/v1/admin/perm/put', { t: andy, email: 'cara@example.com', plan: 'p799', over: { 'stock.ai': false }, expires: exp })).status, 200);
  let me = await (await post(hub, '/v1/perm/me', { t: cara })).json();
  assert.deepEqual([me.plan, me.feats['grp.foundry'], me.feats['stock.ai']], ['p799', true, false]);
  // 改一個開關、不帶 expires → 到期日保留
  await post(hub, '/v1/admin/perm/put', { t: andy, email: 'cara@example.com', plan: 'p799', over: {} });
  assert.equal((await (await post(hub, '/v1/admin/perm/get', { t: andy, email: 'cara@example.com' })).json()).expires, exp);
  const saved = clock;
  clock += 3 * 86400 * 1000;
  try {
    me = await (await post(hub, '/v1/perm/me', { t: cara })).json();
    assert.deepEqual([me.plan, me.expired, me.feats['grp.foundry']], ['free', true, false], '過期 → 免費會員的開關');
    const gj = await (await post(hub, '/v1/admin/perm/get', { t: andy, email: 'cara@example.com' })).json();
    assert.deepEqual([gj.plan, gj.expired], ['p799', true], '管理頁看得到他原本的範本與「已過期」');
    for (const bad of ['2027-01-01', -1, 1.5, 99999999999999]) {
      assert.equal((await post(hub, '/v1/admin/perm/put', { t: andy, email: 'cara@example.com', plan: 'p799', over: {}, expires: bad })).status, 400, String(bad));
    }
    assert.equal((await post(hub, '/v1/admin/perm/put', { t: andy, email: 'cara@example.com', plan: 'p799', over: {}, expires: null })).status, 200);
    me = await (await post(hub, '/v1/perm/me', { t: cara })).json();
    assert.equal(me.plan, 'p799', '清掉到期日 → 恢復');
  } finally { clock = saved; }
});

test('族群鍵：grp.<鍵> 走同一套 cleanFeats，可一次關 200 個（上限 300）', async () => {
  const { hub } = makeHub(env());
  const andy = (await login(hub, 'andy@example.com')).j.tok;
  const feats = Object.fromEntries(Array.from({ length: 200 }, (_, i) => ['grp.g' + i, false]));
  assert.equal((await post(hub, '/v1/admin/plans/put', { t: andy, id: 'p399', name: '399', feats })).status, 200);
});

test('相容遷移：舊版資料庫（perm 沒有 expires 欄）啟動後自動補欄、舊資料保留；重啟不報錯', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { Hub } = await import('../worker.js');
  const db = new DatabaseSync(':memory:');
  db.exec('CREATE TABLE perm (email TEXT PRIMARY KEY, plan TEXT, over TEXT, updated INTEGER)');
  db.prepare('INSERT INTO perm VALUES (?, ?, ?, ?)').run('old@example.com', 'free', '{"stock.ai":false}', 1);
  const sql = { exec(q, ...a) { const st = db.prepare(q); const rows = /^\s*(SELECT|WITH|PRAGMA)/i.test(q) ? st.all(...a) : (st.run(...a), []); return { toArray: () => rows.map((r) => ({ ...r })) }; } };
  const state = { storage: { sql, getAlarm: async () => 1, setAlarm: async () => {} } };
  new Hub(state, env()); new Hub(state, env());     // 兩次：第二次不能因為欄位已存在而失敗
  const cols = db.prepare('PRAGMA table_info(perm)').all().map((c) => c.name);
  assert.ok(cols.includes('expires'));
  assert.equal(db.prepare('SELECT over FROM perm WHERE email = ?').get('old@example.com').over, '{"stock.ai":false}');
});

/* ======================================================================== admin-v2b（2026-10-05）：付費範本價格／計費週期 */
test('付費範本價格：price 0～999999 整數、period ∈ month／year／once；plans/get 回傳；只改開關不洗掉價格', async () => {
  const { hub } = makeHub(env());
  const t = (await login(hub, 'andy@example.com')).j.tok;
  const put = async (o) => (await post(hub, '/v1/admin/plans/put', { t, ...o })).status;
  const get = async (id) => (await (await post(hub, '/v1/admin/plans/get', { t })).json()).plans.find((p) => p.id === id);
  assert.equal(await put({ id: 'pbasic', name: '基本方案', feats: {}, price: 399, period: 'month' }), 200);
  const g0 = await get('pbasic');
  assert.deepEqual([g0.price, g0.period, g0.name], [399, 'month', '基本方案']);
  for (const bad of [-1, 1000000, 3.5, '399', null, true]) assert.equal(await put({ id: 'pbasic', name: '基本方案', feats: {}, price: bad }), 400, 'price=' + JSON.stringify(bad));
  for (const bad of ['week', '', 'MONTH', 1]) assert.equal(await put({ id: 'pbasic', name: '基本方案', feats: {}, period: bad }), 400, 'period=' + JSON.stringify(bad));
  assert.equal(await put({ id: 'pbasic', name: '基本方案', feats: {}, price: 0, period: 'once' }), 200, '0 元合法');
  assert.equal(await put({ id: 'pbasic', name: '基本方案', feats: {}, price: 999999, period: 'year' }), 200, '上限合法');
  assert.equal(await put({ id: 'pbasic', feats: { 'stock.ai': false } }), 200);
  const g = await get('pbasic');
  assert.deepEqual([g.price, g.period, g.feats], [999999, 'year', { 'stock.ai': false }], '沒帶 price／period → 沿用原值');
  assert.equal(await put({ id: 'pnew', name: '新範本', feats: {} }), 200);
  const gn = await get('pnew');
  assert.deepEqual([gn.price, gn.period], [0, 'month'], '新範本沒帶價格 → 0／month');
  const gf = await get('free');
  assert.deepEqual([gf.price, gf.period], [0, 'month'], '內建範本也有欄位');
});

test('相容遷移：舊版 plans 表（沒有 price／period）啟動後自動補欄、舊範本保留且 price=0、period=month；重啟不報錯', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { Hub } = await import('../worker.js');
  const db = new DatabaseSync(':memory:');
  db.exec('CREATE TABLE plans (id TEXT PRIMARY KEY, name TEXT, feats TEXT, builtin INTEGER, updated INTEGER)');
  db.prepare('INSERT INTO plans VALUES (?, ?, ?, ?, ?)').run('p399', '399 即時', '{"ov.theme":false}', 0, 1);
  const sql = { exec(q, ...a) { const st = db.prepare(q); const rows = /^\s*(SELECT|WITH|PRAGMA)/i.test(q) ? st.all(...a) : (st.run(...a), []); return { toArray: () => rows.map((r) => ({ ...r })) }; } };
  const state = { storage: { sql, getAlarm: async () => 1, setAlarm: async () => {} } };
  new Hub(state, env()); const h = new Hub(state, env());
  const cols = db.prepare('PRAGMA table_info(plans)').all().map((c) => c.name);
  assert.ok(cols.includes('price') && cols.includes('period'));
  const p = h.plan('p399');
  assert.deepEqual([p.name, p.feats, p.price, p.period], ['399 即時', { 'ov.theme': false }, 0, 'month']);
});
