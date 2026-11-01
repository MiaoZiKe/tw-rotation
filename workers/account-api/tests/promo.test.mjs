/* 問卷／好友邀請（2026-11-01）account-api 端驗收。跑法：node --test workers/account-api/tests/promo.test.mjs */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';
import { GRANT_BAN, grantMailNorm, WELCOME_1027_FEATS } from '../worker.js';

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
const T0 = Date.parse('2026-10-14T04:00:00Z');
let clock = T0;
const DAY = 86400000;
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', TRIAL_HMAC_KEY: 'k'.repeat(32), __now: () => clock });
const IPS = {};   // 權杖 → IP（模擬 Cloudflare 的 CF-Connecting-IP）
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: Object.assign({ Origin: ORIGIN, 'content-type': 'text/plain' }, body && IPS[body.t] ? { 'CF-Connecting-IP': IPS[body.t] } : {}), body: JSON.stringify(body) }));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email, ip = '203.0.113.' + Math.floor(Math.random() * 200 + 1), sub = 'sub-' + email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie, 'CF-Connecting-IP': ip } }));
  const tok = (await (await post(hub, '/auth/redeem', { n })).json()).tok;
  IPS[tok] = ip; return tok;
}
const FEATS = { 'stock.draw': 3, 'ind.rel': 3 };
async function setup() {
  clock = T0;
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: {} });
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: { 'ind.3d': 5 }, per: 'day', days: 14, on: true });
  return { hub, andy };
}
const PICK = [{ p: 'flow', subs: ['flow-rotation', 'flow-sankey'] }, { p: 'etf', subs: [] }];
const trial = async (hub, t) => (await pj(hub, '/v1/me/trial', { t })).j;

test('問卷：只在體驗剩 ≤3 天、每人一次、延長 7 天、母分頁最多 5 個、統計正確', async () => {
  const { hub, andy } = await setup();
  const bob = await login(hub, 'bob@example.com');
  let tr = await trial(hub, bob);
  assert.equal(tr.active, true); assert.equal(tr.survey_done, false); assert.equal(tr.survey_eligible, false, '剛註冊還不到 3 天內');
  assert.equal(tr.until, '2026-10-28'); assert.equal(tr.pro_until, null);
  /* 還早：後端擋 */
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK })).j.error, 'too_early');
  clock += 12 * DAY;
  tr = await trial(hub, bob);
  assert.equal(tr.survey_eligible, true, '剩 ≤3 天');
  /* 後端驗證：第 6 個母分頁、0 星、沒選最實用、壞 key 都被擋 */
  const six = ['a', 'b', 'c', 'd', 'e', 'f'].map((p) => ({ p, subs: [] }));
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: six })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK, improve: six })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 0, useful: PICK })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: [] })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: [{ p: 'x y', subs: [] }] })).s, 400);
  const five = ['a', 'b', 'c', 'd', 'e'].map((p) => ({ p, subs: ['s1', 's2', 's3', 's4', 's5', 's6', 's7'] }));
  const r = await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK, improve: five.slice(0, 1).concat([{ p: 'heatmap', subs: ['heat-theme'] }]), improve_text: '<b>希望更快</b>', want: ['到價／事件提醒'], want_text: '要提醒' });
  assert.equal(r.s, 200); assert.equal(r.j.until, '2026-11-04');
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 5, useful: PICK })).s, 409, '每人只能一次');
  tr = await trial(hub, bob);
  assert.equal(tr.until, '2026-11-04'); assert.equal(tr.base_until, '2026-10-28'); assert.equal(tr.survey_done, true);
  /* 管理區統計 */
  assert.equal((await pj(hub, '/v1/admin/survey', { t: bob })).s, 403);
  const L = (await pj(hub, '/v1/admin/survey', { t: andy })).j;
  assert.equal(L.n, 1); assert.equal(L.sat['4'], 1); assert.equal(L.useful.flow, 1); assert.equal(L.useful['flow-sankey'], 1);
  assert.equal(L.improve['heat-theme'], 1);
  assert.ok(!/<b>/.test(L.texts[0].improve_text), '標籤被清掉'); assert.equal(L.texts[0].email, 'bob@example.com');
  /* 到期後不能再填 */
  const cat = await login(hub, 'cat@example.com');
  clock += 15 * DAY;
  assert.equal((await pj(hub, '/v1/survey/submit', { t: cat, sat: 3, useful: PICK })).s, 403, '體驗已到期');
  assert.equal((await trial(hub, cat)).active, false);
});

test('邀請：碼不可猜且固定、用碼拿 14 天 Pro、不能用自己的/用兩次/舊會員/同 IP/亂猜', async () => {
  const { hub } = await setup();
  const alice = await login(hub, 'alice@example.com', '198.51.100.1');
  const bob = await login(hub, 'bob@example.com', '198.51.100.2');
  const a = (await pj(hub, '/v1/invite/me', { t: alice })).j;
  assert.match(a.code, /^[A-HJKMNP-Z2-9]{8}$/); assert.equal(a.link, 'https://liguligu-puipui.com/?invite=' + a.code);
  assert.equal((await pj(hub, '/v1/invite/me', { t: alice })).j.code, a.code, '同一人碼固定');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: alice, code: a.code })).j.error, 'self');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: bob, code: 'AAAAAAAA' })).j.error, 'bad_code');
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: 'x', text: '我想要一個功能' })).s, 403, '還沒 Pro 不能許願');
  const r = await pj(hub, '/v1/invite/redeem', { t: bob, code: a.code.toLowerCase() });
  assert.equal(r.s, 200); assert.equal(r.j.pro_end, clock + 14 * DAY); assert.equal(r.j.pro_until, '2026-10-28');
  assert.equal((await pj(hub, '/v1/perm/me', { t: bob })).j.plan, 'pro');
  assert.equal((await trial(hub, bob)).pro_until, '2026-10-28');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: bob, code: a.code })).j.error, 'used');
  assert.equal((await pj(hub, '/v1/invite/me', { t: alice })).j.redeemed_count, 1);
  /* 沒有 first_paid → 不會變成可退款 */
  assert.equal((await pj(hub, '/v1/billing/me', { t: bob })).j.canRefund, false);
  /* 同 IP 的第二個新帳號領不到；與邀請人同 IP 也領不到 */
  const dan = await login(hub, 'dan@example.com', '198.51.100.2');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: dan, code: a.code })).j.error, 'same_ip');
  const eve = await login(hub, 'eve@example.com', '198.51.100.1');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: eve, code: a.code })).j.error, 'same_ip');
  /* 註冊超過 7 天不算新會員 */
  const old = await login(hub, 'old@example.com', '198.51.100.9');
  clock += 8 * DAY;
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: old, code: a.code })).j.error, 'not_new');
  /* Pro 到期後回 free */
  clock += 7 * DAY;   /* 共 15 天：Pro 14 天已到期 */
  assert.equal((await pj(hub, '/v1/perm/me', { t: bob })).j.plan, 'free');
});

test('許願：Pro 期間一人一個可覆寫、管理區看得到；亂猜碼每天 8 次擋；刪帳號一起刪', async () => {
  const { hub, andy } = await setup();
  const alice = await login(hub, 'alice@example.com', '198.51.100.1');
  const bob = await login(hub, 'bob@example.com', '198.51.100.2');
  const code = (await pj(hub, '/v1/invite/me', { t: alice })).j.code;
  await pj(hub, '/v1/invite/redeem', { t: bob, code });
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: '', text: '我想要一個功能' })).s, 400);
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: '資金流向', text: '短' })).s, 400);
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: '資金流向', text: '第一版願望內容' })).j.replaced, false);
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: 'ETF', text: '第二版願望內容<i>' })).j.replaced, true);
  const W = (await pj(hub, '/v1/admin/wishes', { t: andy })).j.items;
  assert.equal(W.length, 1); assert.equal(W[0].feature, 'ETF'); assert.equal(W[0].email, 'bob@example.com'); assert.ok(!/<i>/.test(W[0].text));
  assert.equal((await pj(hub, '/v1/admin/wishes', { t: bob })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/wish/status', { t: andy, id: W[0].id, status: 'done' })).s, 200);
  const cat = await login(hub, 'cat@example.com', '198.51.100.7');
  for (let i = 0; i < 8; i++) await pj(hub, '/v1/invite/redeem', { t: cat, code: 'BBBBBBB' + i });
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: cat, code })).s, 429);
  /* Pro 到期後不能再改願望 */
  clock += 15 * DAY;
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: 'ETF', text: '到期後的願望內容' })).s, 403);
  assert.equal((await pj(hub, '/v1/delete', { t: bob })).s, 200);
  assert.equal((await pj(hub, '/v1/admin/wishes', { t: andy })).j.items.length, 0);
});

test('公告：不再顯示記在後端', async () => {
  const { hub } = await setup();
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/ann/state', { t: bob })).j.seen, false);
  assert.equal((await pj(hub, '/v1/ann/dismiss', { t: bob, aid: 'launch-1101' })).s, 200);
  const st = (await pj(hub, '/v1/ann/state', { t: bob })).j;
  assert.equal(st.seen, true); assert.equal(st.trial.active, true);
});
