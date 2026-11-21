/* 方案卡呈現區塊（pricing-v2：plans.price_year、plans.pres）的存取控制與驗證。
 *
 * 跑法：node --test workers/account-api/tests/*.mjs
 * 每條都驗「該允許的有允許」與「該拒絕的有拒絕」。
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
let clock = Date.parse('2026-10-07T04:00:00Z');
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
const PRES = { tagline: '進階看盤功能，年繳享優惠', badge: '最受歡迎', fit_title: '適合每天主動研究', fit_desc: '完整使用掃描、比較與回測。',
  highlights: ['條件掃描器・完整榜池', '多股比較・最多 5 檔'], icon: 'bolt', color: 'blue', public: true };

test('管理者可設 pres／price_year；plans/get 與公開端點都帶出來；沒設的範本給預設值', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 299, period: 'month', price_year: 2988, pres: PRES });
  assert.equal(r.s, 200);
  const p = r.j.plans.find((x) => x.id === 'plus');
  assert.equal(p.price, 299); assert.equal(p.price_year, 2988);
  assert.equal(p.tagline, PRES.tagline); assert.deepEqual(p.highlights, PRES.highlights); assert.equal(p.icon, 'bolt'); assert.equal(p.public, true);
  const pub = (await pj(hub, '/v1/plans/public', {})).j.plans;
  const q = pub.find((x) => x.id === 'plus');
  assert.equal(q.badge, '最受歡迎'); assert.equal(q.price_year, 2988); assert.equal(q.fit_title, PRES.fit_title);
  const f = pub.find((x) => x.id === 'free');
  assert.equal(f.tagline, ''); assert.deepEqual(f.highlights, []); assert.equal(f.public, true); assert.equal(f.price_year, null);
});

test('只改開關（沒帶 pres／price_year）不會把呈現欄位洗掉；帶 null 才清年價', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 299, price_year: 2988, pres: PRES });
  let p = (await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus2', feats: { 'x.y': false } })).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.name, 'Plus2'); assert.equal(p.price_year, 2988); assert.equal(p.badge, '最受歡迎');
  p = (await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus2', feats: {}, price_year: null, pres: { public: false } })).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.price_year, null); assert.equal(p.badge, ''); assert.equal(p.public, false);
});

test('壞的 pres／price_year 整個 400，什麼都不存', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 299, pres: PRES });
  const bad = [
    { pres: { icon: 'skull' } }, { pres: { color: 'pink' } }, { pres: { badge: 'x'.repeat(13) } }, { pres: { highlights: 'a' } },
    { pres: { highlights: Array(13).fill('a') } }, { pres: { highlights: [1] } }, { pres: { public: 'yes' } }, { pres: [] },
    { price_year: -1 }, { price_year: 1.5 }, { price_year: '2988' }, { price_year: 1e8 },
  ];
  for (const x of bad) {
    const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: '壞', feats: {}, ...x });
    assert.equal(r.s, 400, JSON.stringify(x));
  }
  const p = (await pj(hub, '/v1/plans/public', {})).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.name, 'Plus', '400 時名稱也沒被改'); assert.equal(p.badge, '最受歡迎');
});

test('非管理者不能改 pres（403），HTML 角括號被濾掉', async () => {
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: bob, id: 'plus', name: 'P', feats: {}, pres: PRES })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/plans/put', { id: 'plus', name: 'P', feats: {}, pres: PRES })).s, 403);
  const andy = await login(hub, 'andy@example.com');
  const p = (await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'P', feats: {}, pres: { tagline: '<b>好</b>' } })).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.tagline, 'b好/b');
});
