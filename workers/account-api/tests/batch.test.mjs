/* 批次端點（/v1/track/batch）的驗收：同一份資料單送與批送，統計逐列相同；邊界（筆數、時間戳、舊端點）。
 *
 * 跑法：node --test workers/account-api/tests/*.mjs
 * 同 account／sub／v3／v4：每條同時驗「該允許的有允許」與「該拒絕的有拒絕」。
 * 時間一律用台北時間想：tpe('2026-10-05 09:10') ＝ UTC 01:10。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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
let clock = tpe('2026-10-05 09:10');
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
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
const beat = (hub, ev, extra = {}) => pj(hub, '/v1/beat', { sid: 'sid-abcdefgh', r: 'flow', ev, ...extra });


const SID = 'sid-abcdefgh';
const batch = (hub, items, extra = {}) => pj(hub, '/v1/track/batch', { sid: SID, now: clock, items, ...extra });
/* 10 筆心跳：跨兩個小時、有登入開站、有細項、最後一筆是「離開」（只有計數、不算分鐘）*/
const PG = ['flow', 'stock', 'overview'];
const TEN = Array.from({ length: 10 }, (_, i) => {
  const ev = i === 0 ? { 'pv:flow': 1, 'ev:session': 1, 'ev:session_login': 1 } : { ['pv:' + PG[i % 3]]: 1 + (i % 2) };
  if (i % 3) ev['ev:zoom'] = 1;
  return { at: tpe('2026-10-05 09:52') + i * 60000, r: PG[i % 3], ev, e2: i % 4 === 1 ? [['stock', 'view', '2330', 1], ['flow', 'quad', '領先', 2]] : null, live: i < 9 };
});
/* uid 每個 hub 各自亂數產生，比對前換成同一個字 */
const dump = (db) => Object.fromEntries(['usage', 'ev2', 'hstat', 'visits', 'uev'].map((t) => {
  let rows; try { rows = db.prepare(`SELECT * FROM ${t}`).all().map((r) => JSON.stringify({ ...r, ...('uid' in r ? { uid: 'U' } : {}) })); } catch (e) { rows = []; }
  return [t, rows.sort()];
}));

test('10 筆單送與 1 批送：usage／ev2／hstat／visits／uev 五張表逐列相同', async () => {
  clock = tpe('2026-10-05 09:50');
  const A = makeHub(env()), B = makeHub(env());
  const ta = await login(A.hub, 'm@example.com'), tb = await login(B.hub, 'm@example.com');
  for (const x of TEN) {
    clock = x.at;
    const r = await pj(A.hub, '/v1/beat', { sid: SID, r: x.r, ev: x.ev, ...(x.e2 ? { e2: x.e2 } : {}), ...(x.live ? {} : { leave: true }), t: ta });
    assert.equal(r.s, 200);
  }
  clock = tpe('2026-10-05 10:05');
  const r = await batch(B.hub, TEN.map((x) => ({ ts: x.at, r: x.r, ev: x.ev, ...(x.e2 ? { e2: x.e2 } : {}), live: x.live ? 1 : 0 })), { t: tb, leave: true });
  assert.equal(r.s, 200); assert.equal(r.j.took, 10); assert.equal(r.j.skipped, 0);
  const a = dump(A.db), b = dump(B.db);
  assert.ok(a.usage.length > 3 && a.hstat.length === 2 && a.uev.length > 3 && a.visits.length === 1, '真的有資料可比');
  assert.deepEqual(b, a);
});

test('前端時鐘偏差：用 now 校正；超過 24 小時、晚於現在、沒有 ts 的那一筆丟掉，其他照收', async () => {
  clock = tpe('2026-10-05 12:00');
  const { hub, db } = makeHub(env());
  const fe = clock - 7 * 60000;   // 前端時鐘慢 7 分鐘
  const r = await pj(hub, '/v1/track/batch', { sid: SID, now: fe, items: [
    { ts: fe - 60000, r: 'flow', ev: { 'pv:flow': 2 }, live: 1 },
    { ts: fe - 25 * 3600 * 1000, r: 'flow', ev: { 'pv:flow': 100 }, live: 1 },
    { ts: fe + 120000, r: 'flow', ev: { 'pv:flow': 50 }, live: 1 },
    { r: 'flow', ev: { 'pv:flow': 9 }, live: 1 },
  ] });
  assert.equal(r.s, 200); assert.deepEqual([r.j.took, r.j.skipped], [1, 3]);
  assert.equal(db.prepare("SELECT n FROM usage WHERE k = 'pv:flow'").get().n, 2);
  assert.equal(db.prepare('SELECT h FROM hstat').get().h, 11, '校正後 11:59 → 11 時');
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM presence').get().c, 1, '沒 leave：在線名單有這個 sid');
});

test('邊界：最多 100 筆、壞 sid、壞計數只丟那一筆、舊 /v1/beat 照常、leave 刪在線', async () => {
  clock = tpe('2026-10-05 12:00');
  const { hub, db } = makeHub(env());
  const it = { ts: clock - 1000, r: 'flow', ev: { 'pv:flow': 1 }, live: 0 };
  assert.equal((await batch(hub, Array(101).fill(it))).s, 400, '101 筆整批拒收');
  assert.equal((await batch(hub, 'x')).s, 400);
  assert.equal((await pj(hub, '/v1/track/batch', { sid: 'x', items: [it] })).s, 400);
  const r = await batch(hub, Array(100).fill(it).map((x, i) => (i === 5 ? { ...x, ev: { 'pv:nope': 1 } } : x)));
  assert.equal(r.s, 200); assert.deepEqual([r.j.took, r.j.skipped], [99, 1]);
  assert.equal(db.prepare("SELECT n FROM usage WHERE k = 'pv:flow'").get().n, 99);
  assert.equal((await pj(hub, '/v1/beat', { sid: SID, r: 'flow', ev: { 'pv:flow': 1 } })).s, 200, '舊端點保留');
  assert.equal(db.prepare("SELECT n FROM usage WHERE k = 'pv:flow'").get().n, 100);
  assert.equal((await batch(hub, [], { leave: true })).s, 200);
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM presence').get().c, 0, 'leave：從在線名單刪掉');
});
