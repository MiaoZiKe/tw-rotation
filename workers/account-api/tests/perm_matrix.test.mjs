/* 全站權限矩陣（docs/perm_matrix_1008.md）account-api 端驗收：新增的功能鍵不必改 Worker 就存得進去、讀得出來、擋得住。
   跑法：node --test workers/account-api/tests/*.mjs */
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
let clock = Date.parse('2026-10-08T04:00:00Z');
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

test('訪客範本：新的每日次數（lims）與同時選取上限／開關（feats）存得進去，訪客的 /v1/perm/me 讀得到', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const lims = { 'flow.sankey.drill': 3, 'flow.inst.filter': 5, 'earn.tab': 3, 'explore.filter': 2, 'etf.calendar.tab': 3, 'etf.list.tab': 0, 'etf.list.filter': 0,
    'season.pick': 3, 'etf.top3': 3, 'heat.detail': 3, 'ind.groups': 3 };
  const feats = { 'mkt.grp.pick': 5, 'explore.list.n': 5, 'mkt.cand.n': 3, 'etf.returns.n': 0, 'etf.cashflow': false, 'heat.link': false };
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'guest', name: '訪客', feats, lims, dq: 15 });
  assert.equal(r.s, 200, JSON.stringify(r.j));
  const me = (await pj(hub, '/v1/perm/me', {})).j;
  assert.equal(me.who, 'guest');
  for (const [k, v] of Object.entries(feats)) assert.equal(me.feats[k], v, k);
  for (const [k, v] of Object.entries(lims)) assert.equal(me.lims[k], v, k);
  assert.equal(me.dq, 15);
  // 「不限」的同時選取上限 999 也收（整數 0～9999）
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '註冊會員', feats: { 'mkt.grp.pick': 999, 'etf.returns.n': 20 }, lims: {} })).s, 200);
});

test('動作計次的 key（drill.<族群>、filter.<…>、tab.<…>、雜湊）照逐功能上限擋：同 key 重送不算、新 key 滿了回 over', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '註冊會員', feats: {}, lims: { 'flow.sankey.drill': 2, 'etf.list.tab': 1 } });
  const mem = await login(hub, 'mem@example.com');
  const hit = (k, key) => pj(hub, '/v1/quota/hit', { t: mem, k, key });
  assert.ok(!(await hit('flow.sankey.drill', 'drill.foundry')).j.over);
  assert.ok(!(await hit('flow.sankey.drill', 'drill.foundry')).j.over, '同一個族群重送不算');
  assert.ok(!(await hit('flow.sankey.drill', 'drill.ip_asic')).j.over);
  const over = (await hit('flow.sankey.drill', 'drill.mlcc')).j;
  assert.equal(over.over, true); assert.equal(over.limit, 2);
  assert.ok(!(await hit('etf.list.tab', 'x1a2b3c4d')).j.over, '中文分頁名雜湊成 x+8 碼也收');
  assert.equal((await hit('etf.list.tab', 'x99999999')).j.over, true);
});
