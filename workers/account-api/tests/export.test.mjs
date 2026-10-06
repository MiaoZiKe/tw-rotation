/* 會員資料匯出／還原（/v1/admin/export、/v1/admin/import）的存取控制與往返驗收。
 *
 * 跑法：node --test workers/account-api/tests/
 * 每條都驗「該允許的有允許」與「該拒絕的有拒絕」（同 account／sub／v3／v4）。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, createHash } from 'node:crypto';
import { makeHub } from '../harness.mjs';
import { expSplit, EXPORT_CONFIRM } from '../worker.js';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
const BT = 'test-backup-token-0123456789abcdef';
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
const env = (extra = {}) => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', BACKUP_TOKEN: BT, __now: () => clock, ...extra });
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
/* 筆電排程的叫法：沒有 Origin，只帶 Authorization */
const bexp = (hub, tok = BT) => hub.fetch(new Request(API + '/v1/admin/export', { method: 'POST', headers: { Authorization: 'Bearer ' + tok } }));
const bimp = (hub, raw, confirm = EXPORT_CONFIRM, tok = BT) => hub.fetch(new Request(API + '/v1/admin/import' + (confirm ? '?confirm=' + confirm : ''), { method: 'POST', headers: { Authorization: 'Bearer ' + tok }, body: raw }));
const tablesOf = (raw) => JSON.parse(raw).tables;

/* 準備一個有料的資料庫：兩個會員、自選清單、權限、範本、意見回饋、統計 */
async function seeded() {
  const h = makeHub(env());
  const andy = await login(h.hub, 'andy@example.com');
  const bob = await login(h.hub, 'bob@example.com');
  await pj(h.hub, '/v1/lists/put', { t: bob, rev: 0, lists: [{ id: 'a1', name: '自選', codes: ['2330', '2317'] }] });
  await pj(h.hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: '專業', feats: {}, price: 299 });
  await pj(h.hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'pro' });
  await pj(h.hub, '/v1/feedback', { t: bob, cat: 'bug', body: '圖表空白' });
  await pj(h.hub, '/v1/beat', { sid: 'sid-abcdefgh', r: 'stock', t: bob, ev: {} });
  return { ...h, andy, bob };
}

test('非管理者被擋：沒權杖、一般會員、錯的備份權杖、沒設 BACKUP_TOKEN 時的 Bearer 一律 403', async () => {
  const { hub, bob } = await seeded();
  assert.equal((await pj(hub, '/v1/admin/export', {})).s, 403);
  assert.equal((await pj(hub, '/v1/admin/export', { t: bob })).s, 403, '一般會員不准匯出');
  assert.equal((await bexp(hub, 'wrong-token-wrong-token-wrong')).status, 403);
  assert.equal((await bexp(hub, '')).status, 403);
  const { hub: h2 } = makeHub(env({ BACKUP_TOKEN: undefined }));
  assert.equal((await bexp(h2, 'undefined')).status, 403, '沒設 BACKUP_TOKEN 時 Bearer 一律拒絕');
  // 管理者權杖但從別的網站發出（CSRF）也擋
  const r = await hub.fetch(new Request(API + '/v1/admin/export', { method: 'POST', headers: { Origin: 'https://evil.example' }, body: '{}' }));
  assert.equal(r.status, 403);
});

test('管理者可以匯出；備份權杖不帶 Origin 也可以；內容排除 logins／presence／hmac；寫一筆稽核', async () => {
  const { hub, andy, db } = await seeded();
  const a = await post(hub, '/v1/admin/export', { t: andy });
  assert.equal(a.status, 200);
  const r = await bexp(hub);
  assert.equal(r.status, 200);
  const t = tablesOf(await r.text());
  assert.ok(!('logins' in t) && !('presence' in t), '一次性登入狀態與線上名單不匯出');
  assert.ok(!t.kv.rows.some((x) => x[0] === 'hmac'), '權杖簽章金鑰不匯出');
  assert.equal(t.users.rows.length, 2);
  assert.ok(t.users.cols.includes('subh') && !t.users.cols.includes('sub'));
  assert.ok(t.lists.rows.length === 1 && t.feedback.rows.length === 1);
  assert.equal(db.prepare("SELECT n FROM usage WHERE k = 'admin_export'").get().n, 2, '每次匯出記一筆');
});

test('簽章驗得過：sha256 與 HMAC(BACKUP_TOKEN) 對被簽內容成立；改一個字就驗不過', async () => {
  const { hub } = await seeded();
  const raw = await (await bexp(hub)).text();
  const s = expSplit(raw);
  assert.ok(s);
  assert.equal(s.sha, createHash('sha256').update(s.content, 'utf8').digest('hex'));
  assert.equal(s.sig, createHmac('sha256', BT).update(s.content, 'utf8').digest('hex'));
  const forged = raw.replace('bob@example.com', 'eve@example.com');
  const f = expSplit(forged);
  assert.notEqual(f.sig, createHmac('sha256', BT).update(f.content, 'utf8').digest('hex'));
  // 被竄改的檔案匯入空資料庫會被拒絕
  const { hub: empty } = makeHub(env());
  assert.equal((await bimp(empty, forged)).status, 400);
  // 換一把金鑰簽的也不收
  const { hub: other } = makeHub(env({ BACKUP_TOKEN: 'another-backup-token-xxxxxxxxxxxx' }));
  assert.equal((await bimp(other, raw, EXPORT_CONFIRM, 'another-backup-token-xxxxxxxxxxxx')).status, 400);
});

test('匯出 → 匯入空資料庫 → 再匯出：每張表逐列完全一樣；匯入後會員資料可用', async () => {
  const { hub } = await seeded();
  const raw = await (await bexp(hub)).text();
  const { hub: fresh, db } = makeHub(env());
  const ir = await bimp(fresh, raw);
  const ij = await ir.json();
  assert.equal(ir.status, 200, JSON.stringify(ij));
  assert.ok(ij.ok && ij.rows > 0);
  const raw2 = await (await bexp(fresh)).text();
  const t1 = tablesOf(raw), t2 = tablesOf(raw2);
  for (const k of Object.keys(t1)) {
    if (k === 'usage') continue; // 第二次匯出本身會多記一筆 admin_export
    assert.deepEqual(t2[k], t1[k], k + ' 表不一致');
  }
  const strip = (rows) => rows.filter((r) => r[1] !== 'admin_export');
  assert.deepEqual(strip(t2.usage.rows), strip(t1.usage.rows));
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM users').get().n, 2);
  assert.ok(db.prepare("SELECT v FROM kv WHERE k = 'hmac'").get().v, '本機簽章金鑰保留（舊權杖本來就要重新登入）');
});

test('匯入的護欄：非空資料庫拒絕、沒帶確認參數拒絕、非管理者拒絕、拒絕時一列都不寫', async () => {
  const { hub } = await seeded();
  const raw = await (await bexp(hub)).text();
  const before = await (await bexp(hub)).text();
  const r = await bimp(hub, raw);
  assert.equal(r.status, 409, '有會員的資料庫一律拒絕匯入');
  assert.equal((await r.json()).error, 'not_empty');
  const { hub: fresh, db } = makeHub(env());
  assert.equal((await bimp(fresh, raw, '')).status, 400, '沒帶確認參數');
  assert.equal((await bimp(fresh, raw, 'yes')).status, 400, '確認參數不對');
  assert.equal((await bimp(fresh, raw, EXPORT_CONFIRM, 'wrong-token-wrong-token-wrong')).status, 403);
  const noAuth = await fresh.fetch(new Request(API + '/v1/admin/import?confirm=' + EXPORT_CONFIRM, { method: 'POST', headers: { Origin: ORIGIN }, body: raw }));
  assert.equal(noAuth.status, 403);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM users').get().n, 0);
  assert.ok(tablesOf(before).users.rows.length === 2, '來源資料庫沒被動到');
});

test('限流：同一身分每小時最多 6 次，過一小時恢復', async () => {
  const { hub } = await seeded();
  for (let i = 0; i < 6; i++) assert.equal((await bexp(hub)).status, 200);
  assert.equal((await bexp(hub)).status, 429);
  clock += 3601 * 1000;
  assert.equal((await bexp(hub)).status, 200);
});
