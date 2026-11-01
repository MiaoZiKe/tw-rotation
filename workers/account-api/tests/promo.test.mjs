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
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'plus', name: 'Plus', feats: { 'stock.draw': true } });
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pro', name: 'Pro', feats: { 'stock.draw': true, 'stock.ai': true } });
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: { 'ind.3d': 5 }, per: 'day', days: 14, on: true });
  return { hub, andy };
}
const PICK = [{ p: 'flow', subs: ['flow-rotation', 'flow-sankey'] }, { p: 'etf', subs: [] }];
const trial = async (hub, t) => (await pj(hub, '/v1/me/trial', { t })).j;
const plan = async (hub, t) => (await pj(hub, '/v1/perm/me', { t })).j.plan;
let ipn = 0;
const newbie = (hub, name) => login(hub, name + '@example.com', '198.51.100.' + (++ipn));
async function invite(hub, code, name) { const t = await newbie(hub, name); const r = await pj(hub, '/v1/invite/redeem', { t, code }); return { t, r }; }

test('問卷：體驗剩 ≤3 天才能填、每人一次、填完得 7 天 Plus（體驗截止日不變）、母分頁最多 5 個、統計正確', async () => {
  const { hub, andy } = await setup();
  const bob = await newbie(hub, 'bob');
  let tr = await trial(hub, bob);
  assert.equal(tr.active, true); assert.equal(tr.survey_eligible, false, '剛註冊還不到 3 天內');
  assert.equal(tr.until, '2026-10-28'); assert.equal(tr.plus_until, null); assert.equal(tr.pro_until, null);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK })).j.error, 'too_early');
  clock += 12 * DAY;
  assert.equal((await trial(hub, bob)).survey_eligible, true, '剩 ≤3 天');
  const six = ['a', 'b', 'c', 'd', 'e', 'f'].map((p) => ({ p, subs: [] }));
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: six })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK, improve: six })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 0, useful: PICK })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: [] })).s, 400);
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: [{ p: 'x y', subs: [] }] })).s, 400);
  assert.equal(await plan(hub, bob), 'free', '還沒送出前沒有 Plus');
  const r = await pj(hub, '/v1/survey/submit', { t: bob, sat: 4, useful: PICK, improve: [{ p: 'heatmap', subs: ['heat-theme'] }], improve_text: '<b>希望更快</b>', want: ['到價／事件提醒'], want_text: '要提醒' });
  assert.equal(r.s, 200); assert.equal(r.j.days, 7); assert.equal(r.j.plus_end, clock + 7 * DAY);
  assert.equal(await plan(hub, bob), 'plus', '填完得 Plus');
  assert.equal((await pj(hub, '/v1/survey/submit', { t: bob, sat: 5, useful: PICK })).s, 409, '每人只能一次');
  tr = await trial(hub, bob);
  assert.equal(tr.until, '2026-10-28', '體驗截止日不再延長'); assert.equal(tr.survey_done, true); assert.equal(tr.plus_until, '2026-11-02');
  /* 7 天後 Plus 到期回 free */
  clock += 8 * DAY;
  assert.equal(await plan(hub, bob), 'free');
  /* 管理區統計 */
  assert.equal((await pj(hub, '/v1/admin/survey', { t: bob })).s, 403);
  const L = (await pj(hub, '/v1/admin/survey', { t: andy })).j;
  assert.equal(L.n, 1); assert.equal(L.sat['4'], 1); assert.equal(L.useful.flow, 1); assert.equal(L.useful['flow-sankey'], 1); assert.equal(L.improve['heat-theme'], 1);
  assert.ok(!/<b>/.test(L.texts[0].improve_text)); assert.equal(L.texts[0].email, 'bob@example.com');
  const cat = await newbie(hub, 'cat');
  assert.equal((await pj(hub, '/v1/survey/submit', { t: cat, sat: 3, useful: PICK })).s, 403, '體驗已到期');
});

test('問卷：付費者填完不動付費方案，改記待用天數', async () => {
  const { hub, andy } = await setup();
  const bob = await newbie(hub, 'bob');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'vip', name: 'VIP', feats: {} });
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'vip', over: {}, expires: clock + 60 * DAY })).s, 200);
  clock += 12 * DAY;
  const r = await pj(hub, '/v1/survey/submit', { t: bob, sat: 5, useful: PICK });
  assert.equal(r.s, 200); assert.equal(r.j.pending, true);
  assert.equal(await plan(hub, bob), 'vip');
  assert.equal((await trial(hub, bob)).plus_until, null);
});

test('邀請：被邀請者得 14 天 Plus；碼不可猜且固定；擋自己/用兩次/舊會員/已付費/同網路第 4 次/亂猜', async () => {
  const { hub, andy } = await setup();
  const alice = await login(hub, 'alice@example.com', '198.51.101.1');
  const a = (await pj(hub, '/v1/invite/me', { t: alice })).j;
  assert.match(a.code, /^[A-HJKMNP-Z2-9]{8}$/); assert.equal(a.link, 'https://liguligu-puipui.com/?invite=' + a.code);
  assert.equal((await pj(hub, '/v1/invite/me', { t: alice })).j.code, a.code, '同一人碼固定');
  assert.equal(a.next_pro_need, 5); assert.equal(a.pro_unlocked, false);
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: alice, code: a.code })).j.error, 'self');
  const bob = await newbie(hub, 'bob');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: bob, code: 'AAAAAAAA' })).j.error, 'bad_code');
  assert.equal((await pj(hub, '/v1/wish', { t: bob, feature: 'x', text: '我想要一個功能' })).s, 403, '沒有 Pro 不能許願');
  const r = await pj(hub, '/v1/invite/redeem', { t: bob, code: a.code.toLowerCase() });
  assert.equal(r.s, 200); assert.equal(r.j.plus_end, clock + 14 * DAY); assert.equal(r.j.plus_until, '2026-10-28');
  assert.equal(await plan(hub, bob), 'plus', '被邀請者得 Plus');
  assert.equal((await trial(hub, bob)).plus_until, '2026-10-28');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: bob, code: a.code })).j.error, 'used');
  assert.equal((await pj(hub, '/v1/billing/me', { t: bob })).j.canRefund, false, '不是付費，沒有退款');
  /* 已是付費方案的新會員不能用 */
  const pay = await newbie(hub, 'pay');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'vip', name: 'VIP', feats: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pay@example.com', plan: 'vip', over: {}, expires: clock + 30 * DAY });
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: pay, code: a.code })).j.error, 'already_paid');
  /* 同網路 30 天內最多 3 次，與邀請人同 IP 也只是計入 */
  const ipx = '198.51.102.1';
  const mk = async (n) => login(hub, n + '@example.com', ipx);
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: await mk('d1'), code: a.code })).s, 200);
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: await mk('d2'), code: a.code })).s, 200);
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: await mk('d3'), code: a.code })).s, 200);
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: await mk('d4'), code: a.code })).j.error, 'same_ip');
  const same = await login(hub, 'same@example.com', '198.51.101.1');
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: same, code: a.code })).s, 200, '與邀請人同 IP 不直接擋');
  /* 註冊超過 7 天不算新會員 */
  const old = await newbie(hub, 'old');
  clock += 8 * DAY;
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: old, code: a.code })).j.error, 'not_new');
  /* Plus 14 天後到期 */
  clock += 7 * DAY;
  assert.equal(await plan(hub, bob), 'free');
});

test('邀請人：每成功 1 人 +14 天 Plus 可累計、內部上限 3 次不外露；第 5 人升 Pro 7 天只觸發一次；next_pro_need 遞減；Pro 到期回 Plus', async () => {
  const { hub } = await setup();
  const alice = await login(hub, 'alice@example.com', '198.51.101.1');
  const code = (await pj(hub, '/v1/invite/me', { t: alice })).j.code;
  const t0 = clock;
  let me = (await pj(hub, '/v1/invite/me', { t: alice })).j;
  assert.deepEqual([me.reward_days_total, me.next_pro_need], [0, 5]);
  for (let i = 1; i <= 3; i++) {
    assert.equal((await invite(hub, code, 'f' + i)).r.s, 200);
    me = (await pj(hub, '/v1/invite/me', { t: alice })).j;
    assert.equal(me.next_pro_need, 5 - i); assert.equal(me.reward_days_total, 14 * i);
  }
  assert.equal(await plan(hub, alice), 'plus');
  assert.equal((await trial(hub, alice)).plus_until, '2026-11-25', '3 次從現有到期日累加 = 42 天（10/14 起算）');
  /* 第 4 人：被邀請者照拿，邀請人 Plus 不再加（上限 3） */
  assert.equal((await invite(hub, code, 'f4')).r.s, 200);
  me = (await pj(hub, '/v1/invite/me', { t: alice })).j;
  assert.equal(me.reward_days_total, 42); assert.equal(me.next_pro_need, 1); assert.equal(me.pro_unlocked, false);
  assert.ok(!/cap|limit|上限/i.test(JSON.stringify(me)), '回應不顯示上限');
  assert.equal(await plan(hub, alice), 'plus');
  /* 第 5 人：升 Pro 7 天 */
  assert.equal((await invite(hub, code, 'f5')).r.s, 200);
  me = (await pj(hub, '/v1/invite/me', { t: alice })).j;
  assert.deepEqual([me.next_pro_need, me.pro_unlocked, me.reward_days_total], [0, true, 49]);
  assert.equal(await plan(hub, alice), 'pro', 'Pro 優先');
  assert.equal((await trial(hub, alice)).pro_until, '2026-10-21');
  /* 許願：Pro 期內可、一人一個可覆寫 */
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: '資金流向', text: '第一版願望內容' })).j.replaced, false);
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: 'ETF', text: '第二版願望內容' })).j.replaced, true);
  /* 第 6 人：不再觸發第二次 Pro */
  assert.equal((await invite(hub, code, 'f6')).r.s, 200);
  assert.equal((await trial(hub, alice)).pro_until, '2026-10-21');
  assert.equal(await plan(hub, alice), 'pro');
  /* 7 天後 Pro 到期，Plus 還沒到 → 回 Plus；不能再許願 */
  clock += 8 * DAY;
  assert.equal(await plan(hub, alice), 'plus', 'Pro 到期回 Plus');
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: 'ETF', text: '到期後的願望內容' })).s, 403);
  /* Plus 也到期 → free */
  clock += 40 * DAY;
  assert.equal(await plan(hub, alice), 'free');
  assert.ok(t0 > 0);
});

test('邀請人是付費會員：不動付費方案，Plus 與 Pro 都記待用天數', async () => {
  const { hub, andy } = await setup();
  const pay = await login(hub, 'pay@example.com', '198.51.101.9');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'vip', name: 'VIP', feats: {} });
  assert.equal((await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pay@example.com', plan: 'vip', over: {}, expires: clock + 30 * DAY })).s, 200);
  const code = (await pj(hub, '/v1/invite/me', { t: pay })).j.code;
  for (let i = 1; i <= 5; i++) assert.equal((await invite(hub, code, 'g' + i)).r.s, 200);
  const pp = (await pj(hub, '/v1/admin/perm/get', { t: andy, email: 'pay@example.com' })).j;
  assert.equal(pp.plan, 'vip'); assert.equal(pp.expires, T0 + 30 * DAY, '付費方案與到期日不動');
  const me = (await pj(hub, '/v1/invite/me', { t: pay })).j;
  assert.equal(me.reward_days_total, 3 * 14 + 7); assert.equal(me.reward_pending_days, 3 * 14 + 7); assert.equal(me.pro_unlocked, true);
  assert.equal((await trial(hub, pay)).pro_until, null);
});

test('許願與管理區：非 Pro 不能許、管理區看得到並可改狀態；亂猜碼每天 8 次擋；刪帳號一起刪', async () => {
  const { hub, andy } = await setup();
  const alice = await login(hub, 'alice@example.com', '198.51.101.1');
  const code = (await pj(hub, '/v1/invite/me', { t: alice })).j.code;
  for (let i = 1; i <= 5; i++) await invite(hub, code, 'f' + i);
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: '', text: '我想要一個功能' })).s, 400);
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: '資金流向', text: '短' })).s, 400);
  assert.equal((await pj(hub, '/v1/wish', { t: alice, feature: 'ETF', text: '願望內容<i>文字' })).s, 200);
  const W = (await pj(hub, '/v1/admin/wishes', { t: andy })).j.items;
  assert.equal(W.length, 1); assert.equal(W[0].email, 'alice@example.com'); assert.ok(!/<i>/.test(W[0].text));
  assert.equal((await pj(hub, '/v1/admin/wishes', { t: alice })).s, 403);
  assert.equal((await pj(hub, '/v1/admin/wish/status', { t: andy, id: W[0].id, status: 'done' })).s, 200);
  /* 管理區邀請成效 */
  const st = (await pj(hub, '/v1/admin/invite/stats', { t: andy })).j.stats;
  const row = Object.values(st).find((x) => x.email === 'alice@example.com');
  assert.deepEqual([row.invited, row.reward_days], [5, 49]);
  const u = (await pj(hub, '/v1/admin/perm/list', { t: andy })).j.users.find((x) => x.email === 'alice@example.com');
  assert.deepEqual([u.invited_count, u.invite_reward_days], [5, 49]);
  /* 亂猜 */
  const cat = await newbie(hub, 'cat');
  for (let i = 0; i < 8; i++) await pj(hub, '/v1/invite/redeem', { t: cat, code: 'BBBBBBB' + i });
  assert.equal((await pj(hub, '/v1/invite/redeem', { t: cat, code })).s, 429);
  assert.equal((await pj(hub, '/v1/delete', { t: alice })).s, 200);
  assert.equal((await pj(hub, '/v1/admin/wishes', { t: andy })).j.items.length, 0);
});

test('公告：不再顯示記在後端；GRANT_BAN 只剩盤中即時與分 K', async () => {
  const { hub, andy } = await setup();
  const bob = await newbie(hub, 'bob');
  assert.equal((await pj(hub, '/v1/ann/state', { t: bob })).j.seen, false);
  assert.equal((await pj(hub, '/v1/ann/dismiss', { t: bob, aid: 'launch-1101' })).s, 200);
  const st = (await pj(hub, '/v1/ann/state', { t: bob })).j;
  assert.equal(st.seen, true); assert.equal(st.trial.active, true);
  assert.deepEqual(GRANT_BAN, ['live.tick', 'stock.k_min']);
  const put = (k) => pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'promo-x', kind: 'promo', name: 'x', feats: { [k]: 3 }, per: 'total', t0: clock, t1: clock + DAY, on: false });
  assert.equal((await put('stock.ai')).s, 200); assert.equal((await put('live.tick')).s, 400);
});
