/* 合併 quota（plans.meta）與 pricing-v2（plans.pres＋price_year）：兩種寫法都讀得到、最後寫入者整份取代對方。
 * 跑法：node --test workers/account-api/tests/*.mjs */
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
const pub = async (hub, id) => (await (await post(hub, '/v1/plans/public', {})).json()).plans.find((p) => p.id === id);

test('套用建議方案（meta 寫法）→ 公開端點攤平成 tagline／badge／fit_*／highlights／price_year', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const meta = { badge: '最受歡迎', tagline: '每天主動研究', fit_title: '適合每天主動研究', fit_desc: '說明', highlights: ['研究瀏覽・每日 50 次'], price_year: 2490 };
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 249, period: 'month', meta });
  assert.equal(r.s, 200);
  const p = await pub(hub, 'plus');
  assert.equal(p.badge, '最受歡迎'); assert.equal(p.tagline, '每天主動研究'); assert.equal(p.fit_title, '適合每天主動研究');
  assert.deepEqual(p.highlights, ['研究瀏覽・每日 50 次']); assert.equal(p.price_year, 2490);
});

test('管理區方案卡（pres 寫法）整份取代 meta：清空的欄位不會被 meta 補回來', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 249, period: 'month', meta: { badge: '最受歡迎', tagline: '舊句', price_year: 2490 } });
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, pres: { tagline: '新句', icon: 'bolt' }, price_year: null });
  assert.equal(r.s, 200);
  const p = await pub(hub, 'plus');
  assert.equal(p.tagline, '新句'); assert.equal(p.badge, ''); assert.equal(p.price_year, null); assert.equal(p.icon, 'bolt');
});

test('pres 寫完又用 meta 套用建議方案 → meta 勝，舊 pres 與 price_year 被清掉', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 249, period: 'month', pres: { tagline: '舊 pres 句', icon: 'crown' }, price_year: 1000 });
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, meta: { tagline: '建議方案句', price_year: 2490 } });
  const p = await pub(hub, 'plus');
  assert.equal(p.tagline, '建議方案句'); assert.equal(p.price_year, 2490); assert.equal(p.icon, null);
});

test('套用建議方案同一個請求送 meta＋price_year（10-07 根因）→ 介紹欄位不能被清掉', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const meta = { badge: '最受歡迎', tagline: '每天主動研究，工具一次到位', fit_title: '適合每天主動研究', fit_desc: '說明', highlights: ['研究瀏覽・每日 50 次'], price_year: 2990 };
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 299, period: 'month', meta, price_year: 2990 });
  assert.equal(r.s, 200);
  const p = await pub(hub, 'plus');
  assert.equal(p.tagline, '每天主動研究，工具一次到位'); assert.equal(p.fit_title, '適合每天主動研究'); assert.equal(p.badge, '最受歡迎');
  assert.deepEqual(p.highlights, ['研究瀏覽・每日 50 次']); assert.equal(p.price, 299); assert.equal(p.price_year, 2990);
});

test('套用建議方案新寫法（pres＋price_year）→ 公開端點讀得到全部介紹欄位', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const pres = { badge: '功能最齊', tagline: '不限次數', fit_title: '適合追蹤多個題材', fit_desc: '說明', highlights: ['研究瀏覽・不限次數'] };
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: {}, price: 499, period: 'month', pres, price_year: 4990 });
  assert.equal(r.s, 200);
  const p = await pub(hub, 'pro');
  assert.equal(p.tagline, '不限次數'); assert.equal(p.badge, '功能最齊'); assert.equal(p.fit_title, '適合追蹤多個題材'); assert.equal(p.fit_desc, '說明');
  assert.deepEqual(p.highlights, ['研究瀏覽・不限次數']); assert.equal(p.price_year, 4990);
});
