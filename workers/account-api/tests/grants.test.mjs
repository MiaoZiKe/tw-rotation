/* 體驗額度（docs/launch_gap_payment_1009.md 第 3 節）account-api 端驗收。跑法：node --test workers/account-api/tests/ */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';
import { GRANT_BAN, grantMailNorm } from '../worker.js';

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
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
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
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
const FEATS = { 'stock.draw': 3, 'ind.rel': 3 };
async function setup(defs = []) {
  clock = T0;
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  /* 免費會員範本：畫線關、關聯圖每日 1 次（方案有上限 → 先吃方案、用完才扣體驗）*/
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'free', name: '免費會員', feats: { 'stock.draw': false }, lims: { 'ind.rel': 1 } });
  for (const d of defs) { const r = await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...d }); assert.equal(r.s, 200, JSON.stringify(r.j)); }
  return { hub, andy };
}
const WELCOME = { id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: FEATS, per: 'total', days: 7, on: true };
const PROMO = { id: 'promo-launch', kind: 'promo', name: '上市體驗週', feats: { 'stock.draw': 5 }, per: 'total', t0: T0 - DAY, t1: T0 + 13 * DAY, on: true };

test('預設兩筆範本（welcome 7 天每項 3 次、promo 每項 5 次）都是關；功能不含禁止項目', async () => {
  const { hub, andy } = await setup();
  const { j } = await pj(hub, '/v1/admin/grants/defs/list', { t: andy });
  const w = j.defs.find((d) => d.id === 'welcome'), p = j.defs.find((d) => d.id === 'promo-launch');
  assert.equal(w.on, false); assert.equal(p.on, false);
  assert.equal(w.days, 7); assert.ok(Object.values(w.feats).every((m) => m === 3));
  assert.ok(Object.values(p.feats).every((m) => m === 5));
  assert.equal(p.t1 - p.t0 + 1, 14 * DAY, 'promo 14 天');
  for (const d of [w, p]) for (const k of Object.keys(d.feats)) assert.ok(!GRANT_BAN.includes(k), k);
  /* 範本關著：新註冊不發、公開端點沒有活動 */
  const bob = await login(hub, 'bob@example.com');
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob })).j.grants, []);
  const pub = (await pj(hub, '/v1/grants/public', {})).j;
  assert.deepEqual(pub.promo, []); assert.deepEqual(pub.welcome, []);
});

test('新註冊拿到 welcome；被鎖功能扣次、同一天同一單位不重扣、第 M+1 個被擋；perm/me 回 grants', async () => {
  const { hub } = await setup([WELCOME]);
  const bob = await login(hub, 'bob@example.com');
  let me = (await pj(hub, '/v1/grants/me', { t: bob })).j;
  assert.equal(me.grants.length, 1); assert.equal(me.grants[0].gid, 'welcome');
  assert.equal(me.grants[0].end - me.grants[0].start, 7 * DAY);
  assert.deepEqual(me.left, { 'stock.draw': 3, 'ind.rel': 3 });
  let r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' });
  assert.deepEqual([r.j.ok, r.j.gid, r.j.left], [true, 'welcome', 2]);
  r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' });
  assert.equal(r.j.again, true, '同一天同一單位重看不扣'); assert.equal(r.j.left, 2);
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2317' })).j.left, 1);
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2454' })).j.left, 0);
  r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '3711' });
  assert.equal(r.j.over, true, '第 M+1 個被擋');
  me = (await pj(hub, '/v1/grants/me', { t: bob })).j;
  assert.deepEqual(me.today['stock.draw'].sort(), ['2317', '2330', '2454']);
  const pm = (await pj(hub, '/v1/perm/me', { t: bob })).j;
  assert.deepEqual(pm.grants, { 'stock.draw': 0, 'ind.rel': 3 });
  assert.deepEqual((await pj(hub, '/v1/perm/me', {})).j.grants, {}, '訪客沒有體驗');
  /* 隔天：期間合計（total）不會重置 */
  clock += DAY;
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' })).j.over, true);
});

test('方案有每日上限：先吃方案額度（不扣體驗），用完才扣體驗；方案已開放的功能不扣', async () => {
  const { hub } = await setup([WELCOME]);
  const bob = await login(hub, 'bob@example.com');
  /* ind.rel 每日 1 次：今天還沒用 → plan:quota，不扣 */
  let r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'ind.rel', key: 'c.ai' });
  assert.equal(r.j.plan, 'quota');
  await pj(hub, '/v1/quota/hit', { t: bob, k: 'ind.rel', key: 'c.ai' });
  r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'ind.rel', key: 'c.ai' });
  assert.equal(r.j.plan, 'quota', '方案今天看過的同一單位照樣不扣');
  r = await pj(hub, '/v1/grants/hit', { t: bob, k: 'ind.rel', key: 'c.semi' });
  assert.equal(r.j.gid, 'welcome', '方案額度用完才扣體驗'); assert.equal(r.j.left, 2);
  /* 範本沒鎖的功能（例如 ind.3d 沒設）→ open，不扣 */
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'etf.cashflow', key: 'x' })).j.plan, 'open');
  /* 熱力圖跳頁：範本沒寫時註冊會員預設關（＝features.js defBy）→ 算鎖住、扣體驗（這份 welcome 沒放 heat.link → over）*/
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'heat.link', key: 'd' })).j.over, true);
  /* 2026-10-10：▶ 播放、週期統計族群篩選也是註冊會員預設關（GRANT_DEF_OFF ＝ features.js defBy）→ 算鎖住 */
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'flow.play', key: 'd' })).j.over, true);
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'season.groups', key: 'd' })).j.over, true);
});

test('付費會員：方案已開放 → 不扣；管理者不計', async () => {
  const { hub, andy } = await setup([{ ...PROMO, audience: 'member' }]);
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pay@example.com', plan: 'plus' });
  const pay = await login(hub, 'pay@example.com');
  const r = await pj(hub, '/v1/grants/hit', { t: pay, k: 'stock.draw', key: '2330' });
  assert.equal(r.j.plan, 'open');
  assert.equal((await pj(hub, '/v1/grants/me', { t: pay })).j.left['stock.draw'], 5, 'audience=member 付費也拿到，但沒被扣');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: andy, k: 'stock.draw', key: '2330' })).j.free, true);
});

test('promo：活動期間內登入（含活動中才註冊）才拿到；起訖外沒有；到期恢復鎖；audience=free 時付費會員不發', async () => {
  const { hub, andy } = await setup([{ ...PROMO, t0: T0 + DAY, t1: T0 + 3 * DAY }]);
  const bob = await login(hub, 'bob@example.com');
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob })).j.grants, [], '活動還沒開始');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' })).j.over, true);
  clock = T0 + DAY + 1000;
  assert.equal((await pj(hub, '/v1/grants/public', {})).j.promo.length, 1, '公開端點列出活動中的 promo');
  const me = (await pj(hub, '/v1/grants/me', { t: bob })).j;
  assert.equal(me.grants[0].gid, 'promo-launch'); assert.equal(me.left['stock.draw'], 5);
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' })).j.left, 4);
  const carol = await login(hub, 'carol@example.com');
  assert.equal((await pj(hub, '/v1/perm/me', { t: carol })).j.grants['stock.draw'], 5, '活動中才註冊的也拿到');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pay@example.com', plan: 'paid' });
  const pay = await login(hub, 'pay@example.com');
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: pay })).j.grants, [], 'audience=free：付費會員不發');
  clock = T0 + 3 * DAY + 1;
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob })).j.grants, [], '到期就消失');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '9999' })).j.over, true, '到期後回到鎖住');
  assert.equal((await pj(hub, '/v1/grants/public', {})).j.promo.length, 0);
});

test('per=day：每天 M 次（隔天重置）；多份體驗先扣最早到期的', async () => {
  const { hub } = await setup([{ ...WELCOME, feats: { 'stock.draw': 1 } }, { ...PROMO, per: 'day', feats: { 'stock.draw': 1 } }]);
  const bob = await login(hub, 'bob@example.com');
  const me = (await pj(hub, '/v1/grants/me', { t: bob })).j;
  assert.deepEqual(me.grants.map((g) => g.gid), ['welcome', 'promo-launch'], 'welcome 7 天後到期，比 promo 早');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: 'a1' })).j.gid, 'welcome');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: 'a2' })).j.gid, 'promo-launch');
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: 'a3' })).j.over, true);
  clock += DAY;
  assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: 'a4' })).j.gid, 'promo-launch', '每天重置');
});

test('防濫用：刪帳號再用同一信箱（含 Gmail 別名）註冊不再發 welcome；同 IP 每天最多 3 份；舊會員不補發 welcome', async () => {
  const { hub, andy } = await setup();
  const bob0 = await login(hub, 'bob.x@gmail.com', '198.51.100.1');           // 範本關著時註冊：沒拿到
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...WELCOME });
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: bob0 })).j.grants, [], '舊會員不補發 welcome');
  const dan = await login(hub, 'd.an+tw@gmail.com', '198.51.100.2');
  assert.equal((await pj(hub, '/v1/grants/me', { t: dan })).j.grants.length, 1);
  assert.equal((await pj(hub, '/v1/delete', { t: dan })).s, 200);
  const dan2 = await login(hub, 'dan@gmail.com', '198.51.100.3', 'sub-other-google');
  assert.deepEqual((await pj(hub, '/v1/grants/me', { t: dan2 })).j.grants, [], 'Gmail 別名同一信箱：不再發');
  assert.equal(grantMailNorm('D.An+x@GoogleMail.com'), 'dan@gmail.com');
  assert.equal(grantMailNorm('a.b+c@example.com'), 'a.b+c@example.com', '非 Gmail 不動');
  const ip = '192.0.2.9';
  const toks = [];
  for (let i = 0; i < 4; i++) toks.push(await login(hub, `ipuser${i}@example.com`, ip));
  const got = [];
  for (const t of toks) got.push((await pj(hub, '/v1/grants/me', { t })).j.grants.length);
  assert.deepEqual(got, [1, 1, 1, 0], '同 IP 第 4 個照樣註冊、但不送');
  clock += DAY;
  const t5 = await login(hub, 'ipuser5@example.com', ip);
  assert.equal((await pj(hub, '/v1/grants/me', { t: t5 })).j.grants.length, 1, '隔天重新算');
  assert.ok(!hub.q('SELECT iph FROM grant_ip').some((r) => r.iph.includes(ip)), '不存原始 IP');
});

test('管理區：只有管理者；禁止功能、壞值整個 400；關掉範本已發的也失效；刪範本；查會員與延長', async () => {
  const { hub, andy } = await setup([WELCOME]);
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/admin/grants/defs/list', { t: bob })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/grants/defs/put', { t: bob, ...PROMO })).s, 403);
  for (const k of GRANT_BAN) {
    const r = await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...PROMO, feats: { 'stock.draw': 3, [k]: 3 } });
    assert.equal(r.s, 400, k); assert.equal(r.j.error, 'banned');
    assert.equal((await pj(hub, '/v1/grants/hit', { t: bob, k, key: 'x' })).s, 400, 'hit 也擋 ' + k);
  }
  const bads = [{ feats: {} }, { feats: { 'stock.draw': 0 } }, { feats: { 'stock.draw': 1000 } }, { feats: { 'grp.mlcc': 3 } }, { t1: PROMO.t0 }, { per: 'week' }, { kind: 'x' }, { name: '' }, { id: 'Bad ID' }];
  for (const x of bads) assert.equal((await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...PROMO, ...x })).s, 400, JSON.stringify(x));
  assert.equal((await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...WELCOME, days: 61 })).s, 400);
  assert.equal((await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...WELCOME, kind: 'promo', t0: T0, t1: T0 + DAY })).j.error, 'kind_fixed');
  assert.ok(!(await pj(hub, '/v1/admin/grants/defs/list', { t: andy })).j.defs.some((d) => d.id === PROMO.id && d.on), '壞的沒存進去');
  /* 關掉 welcome → bob 的體驗失效；打開又回來 */
  assert.equal((await pj(hub, '/v1/grants/me', { t: bob })).j.grants.length, 1);
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...WELCOME, on: false });
  assert.equal((await pj(hub, '/v1/grants/me', { t: bob })).j.grants.length, 0);
  let lst = (await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...WELCOME, on: true })).j;
  assert.equal(lst.defs.find((d) => d.id === 'welcome').issued, 1);
  await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' });
  lst = (await pj(hub, '/v1/admin/grants/defs/list', { t: andy })).j;
  assert.equal(lst.defs.find((d) => d.id === 'welcome').used, 1);
  /* 查會員＋延長 3 天 */
  let u = (await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com' })).j;
  assert.equal(u.known, true); assert.equal(u.grants[0].feats['stock.draw'].used, 1); assert.equal(u.hits.length, 1);
  const end0 = u.grants[0].end;
  u = (await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com', extend_days: 3 })).j;
  assert.equal(u.grants[0].end - end0, 3 * DAY);
  assert.equal((await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'bob@example.com', extend_days: 0 })).s, 400);
  assert.equal((await pj(hub, '/v1/admin/grants/user', { t: andy, email: 'nobody@example.com' })).j.known, false);
  /* 刪範本 → 已發的一律失效 */
  await pj(hub, '/v1/admin/grants/defs/del', { t: andy, id: 'welcome' });
  assert.equal((await pj(hub, '/v1/grants/me', { t: bob })).j.grants.length, 0);
  /* 延長 promo 起訖：已發的跟著改 */
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...PROMO });
  await pj(hub, '/v1/grants/me', { t: bob });
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, ...PROMO, t1: PROMO.t1 + 2 * DAY });
  assert.equal((await pj(hub, '/v1/grants/me', { t: bob })).j.grants[0].end, PROMO.t1 + 2 * DAY);
});

test('體驗不碰帳務：不改方案、不寫 perm、不影響七天退款保證', async () => {
  const { hub } = await setup([WELCOME]);
  const bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/grants/hit', { t: bob, k: 'stock.draw', key: '2330' });
  assert.equal((await pj(hub, '/v1/perm/me', { t: bob })).j.plan, 'free');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM perm WHERE email = ?', 'bob@example.com')[0].c, 0);
  const bs = (await pj(hub, '/v1/billing/me', { t: bob })).j;
  assert.equal(bs.trialUsed, false); assert.equal(bs.refundUsed, false);
});
