/* 每日額度（docs/quota_plan.md）account-api 端驗收 */
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
let clock = Date.parse('2026-10-05T04:00:00Z');
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

/* 每日額度區塊（plans.dq、SEED_PLANS 種 Plus／Pro、/v1/perm/me 回 dq）的驗收。跑法：node --test workers/account-api/tests/ */
test('SEED_PLANS 有設：種 Plus（每日 50）與 Pro（不限），只種一次；沒設不種', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const pub = (await pj(hub, '/v1/plans/public', {})).j.plans;
  const plus = pub.find((p) => p.id === 'plus'), pro = pub.find((p) => p.id === 'pro');
  assert.equal(plus.name, 'Plus'); assert.equal(plus.dq, 50); assert.equal(plus.price, 0);
  assert.equal(pro.name, 'Pro'); assert.equal(pro.dq, null);
  assert.equal(pub.find((p) => p.id === 'free').dq, null, '免費會員預設不限（照舊）');
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', del: true })).s, 200);
  const again = (await pj(hub, '/v1/plans/public', {})).j.plans;
  assert.ok(!again.some((p) => p.id === 'plus'), '刪掉之後不會再長回來');
  const { hub: h2 } = makeHub(env());
  assert.ok(!(await pj(h2, '/v1/plans/public', {})).j.plans.some((p) => p.id === 'plus' || p.id === 'pro'), '沒設 SEED_PLANS 不種');
});

test('plans/put 改 dq：只有管理者；null＝不限、整數 0～9999；壞值 400；只改開關不會把 dq 洗掉；perm/me 回生效範本的 dq', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const mem = await login(hub, 'mem@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: mem, id: 'plus', name: 'Plus', feats: {}, dq: 1 })).s, 403, '一般會員不能改');
  for (const bad of [-1, 10000, 1.5, '50', true]) assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: bad })).s, 400, String(bad));
  let r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: 30 });
  assert.equal(r.s, 200); assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, 30);
  r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'ov.heat': false } });
  assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, 30, '沒帶 dq＝維持原值');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'mem@example.com', plan: 'plus', over: {} });
  let me = (await pj(hub, '/v1/perm/me', { t: mem })).j;
  assert.equal(me.plan, 'plus'); assert.equal(me.dq, 30);
  r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, dq: null });
  assert.equal(r.j.plans.find((p) => p.id === 'plus').dq, null, 'null＝不限');
  me = (await pj(hub, '/v1/perm/me', { t: mem })).j;
  assert.equal(me.dq, null);
  assert.equal((await pj(hub, '/v1/perm/me', {})).j.dq, null, '訪客：訪客範本沒設＝不限');
});

test('自選上限（watch-v2）：免費 1 頁／10 檔、Plus 5 頁／50 檔、Pro 50／200；只擋變多，已經建好的不刪；擋下時回雲端現況', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const mem = await login(hub, 'mem@example.com');
  const mk = (n, k = 0) => Array.from({ length: n }, (_, i) => ({ id: 't' + i, name: '清單' + i, codes: Array.from({ length: k }, (_, j) => String(1000 + j)) }));
  const put = (t, lists, rev) => pj(hub, '/v1/lists/put', { t, lists, rev });
  let r = await put(mem, mk(1, 10), 0);
  assert.equal(r.s, 200, '免費：1 頁 10 檔可以');
  r = await put(mem, mk(2, 0), 1);
  assert.equal(r.s, 403); assert.equal(r.j.error, 'watch_limit'); assert.equal(r.j.kind, 'tabs'); assert.equal(r.j.limit, 1);
  assert.equal(r.j.lists.length, 1, '回雲端現況（1 頁）');
  r = await put(mem, mk(1, 11), 1);
  assert.equal(r.s, 403); assert.equal(r.j.kind, 'size'); assert.equal(r.j.limit, 10);
  // 升級 Plus：5 頁可以、第 6 頁不行；每頁 50 檔
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'mem@example.com', plan: 'plus', over: {} });
  r = await put(mem, mk(5, 50), 1);
  assert.equal(r.s, 200, 'Plus：5 頁、每頁 50 檔');
  assert.equal((await put(mem, mk(6, 0), 2)).s, 403, 'Plus 第 6 頁');
  // 降回免費：已經有的 5 頁不刪，可以改名、刪檔，但不能再變多
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'mem@example.com', plan: 'free', over: {} });
  const five = mk(5, 50); five[0].name = '改名';  five[1].codes = five[1].codes.slice(0, 3);
  assert.equal((await put(mem, five, 2)).s, 200, '降級後改名、刪檔照樣可以');
  five[1].codes.push('2330');
  assert.equal((await put(mem, five, 3)).s, 200, '降級後某頁 3 → 4 檔（還在原本 50 以內）可以');
  assert.equal((await put(mem, mk(6, 0), 4)).s, 403, '降級後不能變 6 頁');
  // 範本的整數開關可以存到 200（原本只收 0～99）
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: { 'watch.tabs': 50, 'watch.size': 200 } })).s, 200, 'watch.size 200 存得進去');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: { 'watch.size': 10000 } })).s, 400, '超過 9999 拒絕');
  // Pro：50 頁
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'mem@example.com', plan: 'pro', over: {} });
  assert.equal((await put(mem, mk(50, 0), 4)).s, 200, 'Pro：50 頁');
  // 既有的付費範本（種子那次）補上舊值 5 頁／50 檔
  const paid = (await pj(hub, '/v1/plans/public', {})).j.plans.find((p) => p.id === 'paid');
  assert.equal(paid.feats['watch.tabs'], 5); assert.equal(paid.feats['watch.size'], 50);
});

test('quota-v2：/v1/quota/hit 照 quota.all（dq）與逐功能上限擋 —— 同單位重看不算、新單位滿了回 over 不記；管理者不限', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const mem = await login(hub, 'mem@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '免費會員（預設）', feats: {}, dq: 2, lims: { 'stock.page': 1 } });
  const hit = (t, k, key) => pj(hub, '/v1/quota/hit', { t, k, key });
  assert.equal((await hit(mem, 'quota.all', '2330')).j.over, undefined);
  assert.equal((await hit(mem, 'quota.all', '2317')).j.over, undefined);
  assert.equal((await hit(mem, 'quota.all', '2330')).j.over, undefined, '同一單位重看不算');
  const r = await hit(mem, 'quota.all', '2454');
  assert.equal(r.j.over, true, '第 3 個新單位 over'); assert.deepEqual(r.j.keys.sort(), ['2317', '2330']);
  assert.equal((await hit(mem, 'stock.page', '2330')).j.over, undefined);
  assert.equal((await hit(mem, 'stock.page', '2317')).j.over, true, '逐功能上限 1');
  for (const c of ['1101', '1102', '1103']) assert.equal((await hit(andy, 'quota.all', c)).j.over, undefined, '管理者不限');
});

test('plan-meta：plans/put 帶 meta（badge、tagline、fit、highlights、年繳價）→ plans/public 攤平；壞的 400；沒帶維持原值', async () => {
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const meta = { badge: '最受歡迎', tagline: '每天主動研究', fit_title: '適合每天研究', fit_desc: '說明', highlights: ['每日 50 次', '3D 剖析圖'], price_year: 2490 };
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, price: 249, meta })).s, 200);
  let p = (await pj(hub, '/v1/plans/public', {})).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.badge, '最受歡迎'); assert.deepEqual(p.highlights, ['每日 50 次', '3D 剖析圖']); assert.equal(p.price_year, 2490); assert.equal(p.price, 249);
  for (const bad of [{ badge: 'x'.repeat(13) }, { highlights: 'a' }, { highlights: ['<b>'] }, { price_year: -1 }, ['x']]) {
    assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {}, meta: bad })).s, 400, JSON.stringify(bad));
  }
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'ov.heat': false } });
  p = (await pj(hub, '/v1/plans/public', {})).j.plans.find((x) => x.id === 'plus');
  assert.equal(p.badge, '最受歡迎', '沒帶 meta＝維持原值');
});
