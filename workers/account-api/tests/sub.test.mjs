/* sub-v1 區塊（訂閱申請、意見反饋、每日瀏覽次數、通知中心）的存取控制驗收。
 *
 * 跑法：node --test workers/account-api/tests/
 * 為什麼是獨立一支而不是接在 account.test.mjs 後面：preview/admin-v2 同時在改那支，分開放合併時不會撞。
 * 跟 account.test.mjs 一樣：每條都驗「該允許的有允許」與「該拒絕的有拒絕」。
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
const post = (hub, path, body, origin = ORIGIN) => hub.fetch(new Request(API + path, {
  method: 'POST', headers: origin ? { Origin: origin, 'content-type': 'text/plain' } : { 'content-type': 'text/plain' }, body: JSON.stringify(body),
}));
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

test('方案公開端點：不必登入、回方案摘要（含價格欄位、admin-v3 的瀏覽次數上限 lims）、不含會員名單', async () => {
  /* ★ 2026-10-05 改前→改後（admin-v3 合併 admin-v2 之後）：plans 表本來就有 price／period（admin-v2 遷移時補 0／month），
     所以內建範本的價格是 0 而不是 null；這裡改驗「回得到、可改、不含名單」。 */
  const { hub, db } = makeHub(env());
  const { s, j } = await pj(hub, '/v1/plans/public', {});
  assert.equal(s, 200);
  assert.deepEqual(j.plans.map((p) => p.id).sort(), ['free', 'guest', 'paid']);
  assert.ok(j.plans.every((p) => Number.isInteger(p.price) && !('members' in p) && typeof p.lims === 'object'));
  db.prepare("UPDATE plans SET price = 399, period = 'month' WHERE id = 'paid'").run();
  const p = (await pj(hub, '/v1/plans/public', {})).j.plans.find((x) => x.id === 'paid');
  assert.deepEqual([p.price, p.period], [399, 'month']);
  assert.equal((await post(hub, '/v1/plans/public', {}, 'https://evil.example')).status, 403, '白名單外網站');
});

test('訂閱申請：要登入；方案／週期／email 驗格式；管理者看得到、一般人看不到；刪帳號一起刪', async () => {
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  const andy = await login(hub, 'andy@example.com');
  assert.equal((await post(hub, '/v1/subscribe/request', { plan: 'paid', period: 'month' })).status, 401, '沒登入');
  for (const bad of [{ plan: 'guest', period: 'month' }, { plan: 'nope', period: 'month' }, { plan: 'paid', period: 'week' }, { plan: 'paid', period: 'year', contact: 'not-mail' }]) {
    assert.equal((await post(hub, '/v1/subscribe/request', { t: bob, ...bad })).status, 400, JSON.stringify(bad));
  }
  const ok = await pj(hub, '/v1/subscribe/request', { t: bob, plan: 'paid', period: 'year', contact: 'Bob.Pay@Example.com', note: '公司報帳' });
  assert.equal(ok.s, 200);
  assert.equal((await post(hub, '/v1/admin/feedback/list', { t: bob })).status, 403, '一般人讀不到');
  const l = (await pj(hub, '/v1/admin/feedback/list', { t: andy })).j;
  assert.deepEqual([l.requests[0].plan, l.requests[0].period, l.requests[0].contact, l.requests[0].status], ['paid', 'year', 'bob.pay@example.com', 'new']);
  assert.equal((await post(hub, '/v1/admin/feedback/set', { t: andy, kind: 'request', id: ok.j.id, status: 'done' })).status, 200);
  assert.equal((await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.requests[0].status, 'done');
  for (let i = 0; i < 4; i++) await post(hub, '/v1/subscribe/request', { t: bob, plan: 'paid', period: 'month' });
  assert.equal((await post(hub, '/v1/subscribe/request', { t: bob, plan: 'paid', period: 'month' })).status, 429, '一天最多 5 筆');
  await post(hub, '/v1/delete', { t: bob });
  assert.equal((await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.requests.length, 0, '刪帳號一起刪');
});

test('意見反饋：訪客也能送；類別與內容要合格；管理者可標已處理；保存 13 個月', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const cara = await login(hub, 'cara@example.com');
  assert.equal((await post(hub, '/v1/feedback', { cat: 'bug', body: 'K 線切週期空白', url: 'https://miaozike.github.io/tw-rotation/#stock/2330', ua: 'UA' })).status, 200, '訪客');
  assert.equal((await post(hub, '/v1/feedback', { t: cara, cat: 'idea', body: '希望加 ETF' })).status, 200);
  for (const bad of [{ cat: 'spam', body: 'xx' }, { cat: 'bug', body: '' }, { cat: 'bug', body: 'ok', contact: 'bad' }]) {
    assert.equal((await post(hub, '/v1/feedback', bad)).status, 400, JSON.stringify(bad));
  }
  const l = (await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.feedback;
  assert.equal(l.length, 2);
  const c = l.find((x) => x.cat === 'idea');
  assert.deepEqual([c.contact, c.member, 'uid' in c], ['cara@example.com', true, false], '登入者預填 email、不外露 uid');
  assert.equal(l.find((x) => x.cat === 'bug').url.endsWith('#stock/2330'), true);
  assert.equal((await post(hub, '/v1/admin/feedback/set', { t: andy, id: c.id, status: 'handled' })).status, 200);
  assert.equal((await post(hub, '/v1/admin/feedback/set', { t: andy, id: c.id, status: 'weird' })).status, 400);
  assert.equal((await post(hub, '/v1/admin/feedback/set', { t: cara, id: c.id, status: 'handled' })).status, 403);
  assert.equal((await post(hub, '/v1/admin/feedback/del', { t: cara, id: c.id })).status, 403, '非管理者不能刪');
  assert.equal((await post(hub, '/v1/admin/feedback/del', { t: andy, id: c.id })).status, 200);
  assert.equal((await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.feedback.length, 1, '刪掉一筆');
  for (let i = 0; i < 4; i++) assert.equal((await post(hub, '/v1/feedback', { cat: 'other', body: '訪客' + i })).status, 200);
  assert.equal((await post(hub, '/v1/feedback', { cat: 'other', body: '第六筆' })).status, 429, '訪客每 IP 每小時 5 筆');
  assert.equal((await post(hub, '/v1/feedback', { t: cara, cat: 'other', body: '會員不受 IP 上限' })).status, 200);
  const saved = clock;
  try {
    clock += 400 * 86400 * 1000;
    hub.cleanup();
    assert.equal((await pj(hub, '/v1/admin/feedback/list', { t: await login(hub, 'andy@example.com') })).j.feedback.length, 0, '13 個月後刪');
  } finally { clock = saved; }
});

test('每日瀏覽次數：要登入；同一檔一天只算一次；跨日歸零；鍵格式不對 400', async () => {
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com');
  assert.equal((await post(hub, '/v1/quota/hit', { k: 'quota.stock', key: '2330' })).status, 401);
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'quota.stock', key: '2330' })).j.n, 1);
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'quota.stock', key: '2330' })).j.n, 1, '同一檔不重算');
  const r = (await pj(hub, '/v1/quota/hit', { t: bob, k: 'quota.stock', key: '2317' })).j;
  assert.deepEqual([r.n, r.keys.sort()], [2, ['2317', '2330']]);
  assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'quota.stock' })).j.n, 2, '不帶 key＝只查');
  for (const bad of [{ k: 'Stock!', key: '2330' }, { k: 'quota.stock', key: '<b>' }]) assert.equal((await post(hub, '/v1/quota/hit', { t: bob, ...bad })).status, 400);
  const saved = clock;
  try { clock += 86400 * 1000; assert.equal((await pj(hub, '/v1/quota/hit', { t: bob, k: 'quota.stock' })).j.n, 0, '隔天歸零'); } finally { clock = saved; }
});

test('通知中心：只有管理者能發；依對象過濾、只回上架中；登入者已讀跨裝置；刪公告連已讀一起刪', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com');
  const bob = await login(hub, 'bob@example.com');
  const vip = await login(hub, 'vip@example.com');
  await post(hub, '/v1/admin/perm/put', { t: andy, email: 'vip@example.com', plan: 'paid', over: {} });
  const put = (n) => pj(hub, '/v1/admin/notices/put', { t: andy, kind: 'feature', body: '內容 https://example.com', ...n });
  assert.equal((await post(hub, '/v1/admin/notices/put', { t: bob, title: 'x', body: 'y', kind: 'event', audience: 'all' })).status, 403);
  for (const bad of [{ title: '', audience: 'all' }, { title: 't', audience: 'everyone' }, { title: 't', audience: 'all', kind: 'xx' }, { title: 't', audience: 'all', start: clock, end: clock - 1 }]) {
    assert.equal((await put(bad)).s, 400, JSON.stringify(bad));
  }
  const all = (await put({ title: '全部', audience: 'all', pinned: true })).j.notice;
  await put({ title: '訪客限定', audience: 'guest' });
  await put({ title: '會員', audience: 'member' });
  await put({ title: '付費', audience: 'paid' });
  await put({ title: '範本', audience: 'plan:paid' });
  await put({ title: '未上架', audience: 'all', start: clock + 86400000 });
  await put({ title: '已下架', audience: 'all', start: clock - 2 * 86400000, end: clock - 86400000 });
  const titles = async (t) => (await pj(hub, '/v1/notices', t ? { t } : {})).j.notices.map((n) => n.title).sort();
  assert.deepEqual(await titles(), ['全部', '訪客限定'].sort());
  assert.deepEqual(await titles(bob), ['全部', '會員'].sort());
  assert.deepEqual(await titles(vip), ['全部', '會員', '付費', '範本'].sort());
  const g = (await pj(hub, '/v1/notices', {})).j.notices;
  assert.ok(g[0].pinned && g[0].title === '全部' && g.every((n) => n.read === null), '置頂在前、訪客沒有伺服器已讀');
  assert.equal((await post(hub, '/v1/notices/read', { ids: [all.id] })).status, 401, '訪客已讀存在自己瀏覽器');
  assert.equal((await post(hub, '/v1/notices/read', { t: bob, ids: [all.id, 'not-exist'] })).status, 200);
  const bn = (await pj(hub, '/v1/notices', { t: bob })).j.notices;
  assert.deepEqual(bn.filter((n) => n.read).map((n) => n.title), ['全部']);
  // 編輯＋下架
  assert.equal((await put({ id: all.id, title: '全部（改）', audience: 'all' })).s, 200);
  assert.ok((await titles()).includes('全部（改）'));
  const adm = (await pj(hub, '/v1/admin/notices/list', { t: andy })).j.notices;
  assert.equal(adm.length, 7);
  assert.equal(adm.find((n) => n.id === all.id).reads, 1);
  await post(hub, '/v1/admin/notices/del', { t: andy, id: all.id });
  assert.ok(!(await titles()).includes('全部（改）'));
  assert.deepEqual((await pj(hub, '/v1/notices/read', { t: bob, ids: [] })).j.read, [], '已讀紀錄一起刪');
  await post(hub, '/v1/delete', { t: vip });
});

test('既有 API 不受影響：未知路徑仍 404、OPTIONS 仍 204', async () => {
  const { hub } = makeHub(env());
  assert.equal((await post(hub, '/v1/nope', {})).status, 404);
  assert.equal((await hub.fetch(new Request(API + '/v1/feedback', { method: 'OPTIONS', headers: { Origin: ORIGIN } }))).status, 204);
});
