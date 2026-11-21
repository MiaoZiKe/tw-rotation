/* perm-v4 區塊（付費範本排序 plans.sort、/v1/admin/plans/sort、/v1/admin/members/stats）的存取控制與口徑驗收。
 *
 * 跑法：node --test workers/account-api/tests/*.mjs
 * 每條都驗「該允許的有允許」與「該拒絕的有拒絕」（同 account／sub／v3）。
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
const beat = (hub, t, extra = {}) => pj(hub, '/v1/beat', { sid: 'sid-' + t.slice(3, 12), r: 'stock', t, ...extra });
const ids = (plans) => plans.map((p) => p.id);
const tick = () => { clock += 1000; };
/* 第一次啟動會種一份「付費會員」範本（id=paid，管理者可刪）；這幾條要從乾淨的付費範本開始，先刪掉它 */
const noSeed = (hub, t) => pj(hub, '/v1/admin/plans/put', { t, id: 'paid', del: true });

test('付費範本排序：新建排最後、改名不換位置；plans/sort 改順序 → plans/get 與公開端點都照新順序（訪客、註冊會員固定最前）', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await noSeed(hub, andy);
  for (const [id, name] of [['pa', '甲'], ['pb', '乙'], ['pc', '丙']]) { tick(); assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id, name, feats: {}, price: 100 })).s, 200); }
  let pl = (await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans;
  assert.deepEqual(ids(pl), ['guest', 'free', 'pa', 'pb', 'pc']);
  assert.deepEqual(pl.filter((p) => !p.builtin).map((p) => p.sort), [0, 1, 2]);
  // 改名（updated 變了）不會讓它跑到最後 —— 舊版是依 updated 排，改個名字就換位置
  tick(); await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pa', name: '甲改', feats: {} });
  assert.deepEqual(ids((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans), ['guest', 'free', 'pa', 'pb', 'pc']);
  const r = await pj(hub, '/v1/admin/plans/sort', { t: andy, ids: ['pc', 'pa', 'pb'] });
  assert.equal(r.s, 200);
  assert.deepEqual(ids(r.j.plans), ['guest', 'free', 'pc', 'pa', 'pb']);
  assert.deepEqual(ids((await pj(hub, '/v1/plans/public', {})).j.plans), ['guest', 'free', 'pc', 'pa', 'pb'], '訂閱頁的方案卡順序跟著變');
  // 新建的排最後
  tick(); await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pd', name: '丁', feats: {} });
  assert.deepEqual(ids((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans), ['guest', 'free', 'pc', 'pa', 'pb', 'pd']);
  // 刪一個 → 其餘順序不變
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pa', del: true });
  assert.deepEqual(ids((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans), ['guest', 'free', 'pc', 'pb', 'pd']);
});

test('plans/sort 拒絕：非管理者 403；少一個、多一個、重複、內建、不存在、非字串 → 400 bad_order，順序一個都不動', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  await noSeed(hub, andy);
  for (const id of ['pa', 'pb']) { tick(); await pj(hub, '/v1/admin/plans/put', { t: andy, id, name: id, feats: {} }); }
  assert.equal((await post(hub, '/v1/admin/plans/sort', { t: bob, ids: ['pb', 'pa'] })).status, 403);
  assert.equal((await post(hub, '/v1/admin/plans/sort', { ids: ['pb', 'pa'] })).status, 403);
  for (const bad of [['pa'], ['pa', 'pb', 'pc'], ['pa', 'pa'], ['free', 'pa'], ['pa', 'zz'], ['pa', 1], 'pa,pb', null]) {
    const x = await pj(hub, '/v1/admin/plans/sort', { t: andy, ids: bad });
    assert.equal(x.s, 400, JSON.stringify(bad)); assert.equal(x.j.error, 'bad_order');
  }
  assert.deepEqual(ids((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans), ['guest', 'free', 'pa', 'pb'], '壞的請求不留半套順序');
});

test('相容遷移：舊 plans 表沒有 sort → 補欄並依原本順序（updated, id）補 0..n-1，上線那一刻順序不變；重跑不報錯', async () => {
  const { hub, db, state } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await noSeed(hub, andy);
  // 模擬「舊版 Worker 建的資料」：先用 v3 的方式寫三個範本，再把 sort 欄位拿掉
  for (const id of ['px', 'py', 'pz']) { tick(); await pj(hub, '/v1/admin/plans/put', { t: andy, id, name: id, feats: {} }); }
  db.exec('ALTER TABLE plans DROP COLUMN sort');
  const { Hub } = await import('../worker.js');
  const again = new Hub(state, env());
  const r = await again.fetch(new Request(API + '/v1/admin/plans/get', { method: 'POST', headers: { Origin: ORIGIN }, body: JSON.stringify({ t: andy }) }));
  const pl = (await r.json()).plans;
  assert.deepEqual(ids(pl), ['guest', 'free', 'px', 'py', 'pz']);
  assert.deepEqual(pl.filter((p) => !p.builtin).map((p) => p.sort), [0, 1, 2]);
  const third = new Hub(state, env());
  assert.equal((await third.fetch(new Request(API + '/v1/plans/public', { method: 'POST', headers: { Origin: ORIGIN }, body: '{}' }))).status, 200);
});

test('members/stats：只有管理者；scope=all 與 scope=plan 的功能 Top8／股票 Top8／14 天每日活躍／7 日活躍；壞參數 400', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const cat = await login(hub, 'cat@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'p799', name: '進階', feats: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'bob@example.com', plan: 'p799', over: {} });
  const saved = clock;
  try {
    clock -= 10 * 86400000;                                     // 10 天前：bob 活躍
    await beat(hub, bob, { ev: { 'pv:stock': 1 }, e2: [['stock', 'view', '2330', 3], ['stock', 'tab.revenue', '2330', 2]] });
    clock = saved;                                              // 今天：bob、cat 都活躍
    await beat(hub, bob, { ev: { 'pv:stock': 1 }, e2: [['stock', 'view', '2454', 1], ['flow', 'quad', '領先', 4]] });
    await beat(hub, cat, { ev: { 'pv:stock': 1 }, e2: [['stock', 'view', '2330', 5], ['stock', 'tab.revenue', '2330', 1], ['flow', 'play', '', 9]] });
  } finally { clock = saved; }
  assert.equal((await post(hub, '/v1/admin/members/stats', { t: bob })).status, 403);
  assert.equal((await post(hub, '/v1/admin/members/stats', {})).status, 403);
  const all = (await pj(hub, '/v1/admin/members/stats', { t: andy, scope: 'all' })).j;
  assert.equal(all.n, 3);
  assert.deepEqual(all.feats, [['play', 9], ['quad', 4], ['tab.revenue', 3]]);
  assert.deepEqual(all.stocks, [['2330', 8], ['2454', 1]]);
  assert.equal(all.days.length, 14);
  assert.deepEqual(all.days.at(-1), { day: '2026-10-05', n: 2 });
  assert.equal(all.days.find((d) => d.day === '2026-09-25').n, 1, '10 天前 bob 一個人');
  assert.equal(all.active7, 2, '近 7 日只算今天的 bob、cat（10 天前那筆不算）');
  const pl = (await pj(hub, '/v1/admin/members/stats', { t: andy, scope: 'plan', plan: 'p799' })).j;
  assert.deepEqual([pl.n, pl.active7], [1, 1]);
  assert.deepEqual(pl.feats, [['quad', 4], ['tab.revenue', 2]]);
  assert.deepEqual(pl.stocks, [['2330', 3], ['2454', 1]]);
  assert.equal(pl.days.filter((d) => d.n).length, 2);
  for (const bad of [{ scope: 'x' }, { scope: 'plan', plan: 'nope' }, { scope: 'plan', plan: '../x' }, { scope: 'plan' }]) {
    assert.equal((await post(hub, '/v1/admin/members/stats', { t: andy, ...bad })).status, 400, JSON.stringify(bad));
  }
});

test('範本刪除保護：有「有效會員」→ 409 has_members（回人數與名單）、範本與會員都不動；到期者與 0 人才刪得掉；非管理者 403', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pz', name: '保護測試', feats: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'a@example.com', plan: 'pz', over: {} });                          // 不會到期
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'b@example.com', plan: 'pz', over: {}, expires: clock + 5 * 86400000 }); // 5 天後到期
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'c@example.com', plan: 'pz', over: {}, expires: 1577836800001 });     // 早就到期
  const r = await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pz', del: true });
  assert.equal(r.s, 409);
  assert.deepEqual([r.j.error, r.j.n, r.j.emails], ['has_members', 2, ['a@example.com', 'b@example.com']]);
  assert.ok(ids((await pj(hub, '/v1/admin/plans/get', { t: andy })).j.plans).includes('pz'), '被擋時範本還在');
  assert.equal((await pj(hub, '/v1/admin/perm/get', { t: andy, email: 'a@example.com' })).j.plan, 'pz', '被擋時會員還在原範本');
  const outsider = await login(hub, 'eve@example.com');
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: outsider, id: 'pz', del: true })).s, 403, '非管理者');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'a@example.com', plan: 'free', over: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'b@example.com', plan: 'free', over: {} });
  assert.equal((await pj(hub, '/v1/admin/plans/put', { t: andy, id: 'pz', del: true })).s, 200, '只剩已到期者 → 可刪');
  assert.equal((await pj(hub, '/v1/admin/perm/get', { t: andy, email: 'c@example.com' })).j.plan, 'free', '到期者退回免費');
});

test('members/stats 依期間（2026-10-06）：from／to／bin、活躍人數／造訪／在線／瀏覽、週月合併算「不同人數」、壞區間 400、沒帶起訖＝舊格式', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const cat = await login(hub, 'cat@example.com');
  const saved = clock;
  try {
    clock = saved - 20 * 86400000;                              // 20 天前：bob
    await beat(hub, bob, { ev: { 'pv:stock': 2 }, e2: [['stock', 'view', '2330', 3]] });
    clock = saved - 19 * 86400000;                              // 19 天前：bob、cat（同一週內 bob 出現兩天，週合併只算 1 人）
    await beat(hub, bob, { ev: { 'pv:stock': 1 }, e2: [['stock', 'view', '2330', 1]] });
    await beat(hub, cat, { ev: { 'pv:flow': 4 }, e2: [['flow', 'quad', '領先', 2]] });
  } finally { clock = saved; }
  const rng = (o) => pj(hub, '/v1/admin/members/stats', { t: andy, scope: 'all', ...o });
  const day = (await rng({ from: '2026-09-15', to: '2026-10-05', bin: 'day' })).j;
  assert.equal(day.days.length, 21);
  assert.equal(day.active, 2, '期間內有活動的不同人數');
  assert.equal(day.pv, 7, 'bob 3＋cat 4（登入者的頁面瀏覽）');
  assert.deepEqual(day.stocks, [['2330', 4]]);
  assert.equal(day.stockTotal, 4);
  assert.equal(day.featTotal, 2);
  assert.ok(day.keepDays > 0 && day.bin === 'day');
  assert.equal(day.days.reduce((a, d) => a + d.pv, 0), 7);
  const wk = (await rng({ from: '2026-09-15', to: '2026-10-05', bin: 'week' })).j;
  assert.ok(wk.days.every((d) => new Date(d.day + 'T00:00:00Z').getUTCDay() === 1), '週＝週一起算');
  assert.ok(Math.max(...wk.days.map((d) => d.n)) <= 2, '週合併是「不同人數」，不是每天人數相加');
  const mo = (await rng({ from: '2026-09-01', to: '2026-10-05', bin: 'month' })).j;
  assert.deepEqual(mo.days.map((d) => d.day), ['2026-09-01', '2026-10-01']);
  const empty = (await rng({ from: '2026-01-01', to: '2026-01-31' })).j;
  assert.deepEqual([empty.active, empty.visits, empty.ms, empty.pv, empty.feats.length, empty.stocks.length], [0, 0, 0, 0, 0, 0], '空期間＝全 0、不是缺欄位');
  assert.ok(empty.days.length > 0 && empty.days.every((d) => d.n === 0));
  const long = (await rng({ from: '2025-10-06', to: '2026-10-05', bin: 'day' })).j;
  assert.equal(long.bin, 'week', '超過 120 天的日直條自動改週');
  for (const bad of [{ from: '2026-10-05', to: '2026-10-01' }, { from: '2025-01-01', to: '2026-10-05' }, { from: 'x' }, { to: '2026-13-40' }]) {
    assert.equal((await post(hub, '/v1/admin/members/stats', { t: andy, scope: 'all', ...bad })).status, 400, JSON.stringify(bad));
  }
  const old = (await pj(hub, '/v1/admin/members/stats', { t: andy, scope: 'all' })).j;
  assert.equal(old.days.length, 14, '沒帶起訖＝舊格式（近 14 天）');
  assert.equal((await post(hub, '/v1/admin/members/stats', { t: bob, scope: 'all', from: '2026-09-15' })).status, 403);
});
