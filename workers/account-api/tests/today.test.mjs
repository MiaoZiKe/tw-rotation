/* 「今天誰來過」端點（worker.js 檔尾 pdwell／visagg 區塊）的允許／拒絕驗收。跑法：node --test workers/account-api/tests/today.test.mjs
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

const KEY = 'internal-test-key-not-real';
const uidOf = (tok) => tok.split('.')[1];
const tpe = (s) => Date.parse(s.replace(' ', 'T') + ':00+08:00');
const beat = (hub, tok, sid, vd, r, ts) => post(hub, '/v1/track/batch', { sid, vd, t: tok, now: clock, items: [{ ts, r, ev: { ['pv:' + r]: 1 }, live: 1 }] });

test('一般會員、訪客拿不到「今天」清單（403）；站主拿得到', async () => {
  clock = tpe('2026-11-06 09:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await post(hub, '/v1/admin/online/today', {})).status, 403);
  assert.equal((await post(hub, '/v1/admin/online/today', { t: bob.j.tok })).status, 403);
  const r = await post(hub, '/v1/admin/online/today', { t: andy.j.tok });
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.deepEqual(j.members, []); assert.equal(j.guests.today, 0); assert.equal(j.guests.total, 0);
});

test('停留時間按頁累加（間隔 ≤150 秒才算）、依總時間排序、取前 3 頁；訪客數今天／本週／累積', async () => {
  clock = tpe('2026-11-06 09:00');
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const carol = await login(hub, 'carol@example.com');
  /* bob：總覽 60 秒 → 資金流向 60+60 秒 → 個股 60 秒 → 產業 60 秒（第 4 頁，應被擠出前 3）*/
  const seq = [['overview', 0], ['overview', 60], ['flow', 120], ['flow', 180], ['stock', 240], ['industry', 300]];
  for (const [r, s] of seq) { clock = tpe('2026-11-06 09:00') + s * 1000; assert.equal((await beat(hub, bob.j.tok, 'sidBOB00001', 'vdBOBBOBBOB1', r, clock)).status, 200); }
  /* carol：只有一次心跳，沒有間隔可加 → ms=0，但有瀏覽紀錄 → 仍列出，退用瀏覽次數 */
  clock = tpe('2026-11-06 09:10'); await beat(hub, carol.j.tok, 'sidCAROL001', 'vdCAROLCAROL', 'season', clock);
  /* 一個純訪客裝置 */
  clock = tpe('2026-11-06 09:11'); await post(hub, '/v1/track/batch', { sid: 'sidGUEST001', vd: 'vdGUESTGUEST', now: clock, items: [{ ts: clock, r: 'overview', ev: { 'pv:overview': 1 }, live: 1 }] });
  const j = await (await post(hub, '/v1/admin/online/today', { t: andy.j.tok })).json();
  const emails = j.members.map((m) => m.email);
  assert.deepEqual(emails.slice(0, 2), ['bob@example.com', 'carol@example.com']);
  const bobRow = j.members[0];
  assert.equal(bobRow.by, 'time'); assert.equal(bobRow.ms, 300000);
  assert.equal(bobRow.pages.length, 3);
  assert.deepEqual(bobRow.pages[0], ['flow', 120000]);
  assert.equal(j.members[1].by, 'pv'); assert.equal(j.members[1].pages[0][0], 'season');
  assert.equal(j.guests.today, 3);           // bob、carol、guest 三台裝置
  assert.equal(j.guests.week, 3); assert.equal(j.guests.total, 3); assert.equal(j.guests.since, '2026-11-06');
  /* 隔天：今天歸零，本週與累積保留 */
  clock = tpe('2026-11-07 10:00');
  await post(hub, '/v1/track/batch', { sid: 'sidGUEST002', vd: 'vdGUESTGUE2', now: clock, items: [{ ts: clock, r: 'overview', ev: { 'pv:overview': 1 }, live: 1 }] });
  const k = await (await post(hub, '/v1/admin/online/today', { t: andy.j.tok })).json();
  assert.equal(k.members.length, 0); assert.equal(k.guests.today, 1); assert.equal(k.guests.week, 4); assert.equal(k.guests.total, 4);
});

test('刪帳號一併刪停留資料；cleanup 刪 90 天前', async () => {
  clock = tpe('2026-11-06 09:00');
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  for (const s of [0, 60]) { clock = tpe('2026-11-06 09:00') + s * 1000; await beat(hub, bob.j.tok, 'sidBOB00002', 'vdBOBBOBBOB2', 'flow', clock); }
  const uid = uidOf(bob.j.tok);
  assert.ok(hub.q('SELECT COUNT(*) AS c FROM pdwell WHERE uid = ?', uid)[0].c > 0);
  hub.q("INSERT INTO pdwell (uid, day, page, ms) VALUES (?, '2026-01-01', 'flow', 5)", uid);
  hub.cleanup();
  assert.equal(hub.q("SELECT COUNT(*) AS c FROM pdwell WHERE day = '2026-01-01'")[0].c, 0);
  assert.equal((await post(hub, '/v1/delete', { t: bob.j.tok })).status, 200);
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM pdwell WHERE uid = ?', uid)[0].c, 0);
});
