/* 客服聊天室（worker.js 檔尾「客服聊天室 chat-1016」區塊）的允許／拒絕驗收。
 * 跑法：node --test workers/account-api/tests/*.test.mjs
 * 每條都驗「該看得到的看得到」與「不該看到的看不到」：會員只讀自己、訪客只讀自己這個瀏覽器（識別碼）、管理者才讀全部。
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
let clock = Date.parse('2026-10-16T04:00:00Z');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
let ipN = 0;
const post = (hub, path, body, ip) => hub.fetch(new Request(API + path, {
  method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': ip || '10.0.0.' + (++ipN % 250) }, body: JSON.stringify(body),
}));
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
const GK_A = 'guestA_' + 'x'.repeat(20), GK_B = 'guestB_' + 'y'.repeat(20);

test('會員：送出 → 自己的對話看得到；別的會員、訪客看不到', async () => {
  const { hub } = makeHub(env());
  const bob = await login(hub, 'bob@example.com'), cara = await login(hub, 'cara@example.com');
  assert.equal((await pj(hub, '/v1/feedback', { t: bob, cat: 'bug', body: 'K 線空白', url: 'https://miaozike.github.io/tw-rotation/#stock/2330' })).s, 200);
  clock += 1000;
  assert.equal((await pj(hub, '/v1/feedback', { t: bob, type: 'wish', cat: 'idea', body: '想要價格提醒' })).s, 200);
  const m = (await pj(hub, '/v1/chat/mine', { t: bob })).j;
  assert.deepEqual(m.msgs.map((x) => [x.me, x.body, x.type]), [[true, 'K 線空白', ''], [true, '想要價格提醒', 'wish']]);
  assert.equal(m.msgs[0].url, 'https://miaozike.github.io/tw-rotation/#stock/2330');
  assert.ok(m.msgs.every((x) => x.read === false && !('ua' in x) && !('contact' in x)), '會員端不回瀏覽器資訊與聯絡 email');
  assert.equal(m.unread, 0);
  assert.equal((await pj(hub, '/v1/chat/mine', { t: cara })).j.msgs.length, 0, '別的會員看不到');
  assert.equal((await pj(hub, '/v1/chat/mine', {})).j.msgs.length, 0, '訪客沒識別碼：空的');
  assert.equal((await pj(hub, '/v1/chat/mine', { gk: GK_A })).j.msgs.length, 0, '訪客亂帶識別碼也看不到會員的');
  assert.equal((await pj(hub, '/v1/chat/mine', { t: 'v1.bad.1.1.x' })).s, 401, '壞權杖 401');
});

test('訪客：只讀得到自己這個瀏覽器（識別碼）送的；識別碼只存雜湊', async () => {
  const { hub, db } = makeHub(env());
  assert.equal((await pj(hub, '/v1/feedback', { gk: GK_A, cat: 'ask', body: '本益比怎麼算' })).s, 200);
  assert.equal((await pj(hub, '/v1/feedback', { gk: GK_B, cat: 'other', body: 'B 的留言' })).s, 200);
  assert.equal((await pj(hub, '/v1/feedback', { cat: 'other', body: '沒帶識別碼的舊式留言' })).s, 200);
  const a = (await pj(hub, '/v1/chat/mine', { gk: GK_A })).j.msgs;
  assert.deepEqual(a.map((x) => x.body), ['本益比怎麼算']);
  assert.deepEqual((await pj(hub, '/v1/chat/mine', { gk: GK_B })).j.msgs.map((x) => x.body), ['B 的留言']);
  assert.equal((await pj(hub, '/v1/chat/mine', { gk: 'short' })).j.msgs.length, 0, '格式不對的識別碼當沒帶');
  const raw = db.prepare('SELECT gk FROM feedback WHERE gk IS NOT NULL').all().map((r) => r.gk);
  assert.equal(raw.length, 2);
  assert.ok(raw.every((g) => /^[0-9a-f]{32}$/.test(g) && g !== GK_A && g !== GK_B), '資料庫裡沒有原始識別碼');
});

test('管理者：收件匣每人一列＋未讀；打開＝已讀；回覆 → 對方看得到、未讀數、標已讀', async () => {
  const { hub } = makeHub(env());
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/feedback', { t: bob, cat: 'bug', body: '第一句' }); clock += 1000;
  await pj(hub, '/v1/feedback', { t: bob, cat: 'bug', body: '第二句' }); clock += 1000;
  await pj(hub, '/v1/feedback', { gk: GK_A, type: 'wish', cat: 'idea', body: '訪客的願望' }); clock += 1000;
  await pj(hub, '/v1/feedback', { cat: 'other', body: '舊式訪客', contact: 'old@example.com' }); clock += 1000;
  assert.equal((await post(hub, '/v1/admin/chat/list', { t: bob })).status, 403, '一般會員進不了收件匣');
  let L = (await pj(hub, '/v1/admin/chat/list', { t: andy })).j;
  assert.equal(L.convs.length, 3);
  assert.equal(L.unread, 4);
  const cb = L.convs.find((c) => c.member), cg = L.convs.find((c) => c.ck.startsWith('g:')), cf = L.convs.find((c) => c.ck.startsWith('f:'));
  assert.deepEqual([cb.n, cb.unread, cb.last.body, cb.email, cb.reply], [2, 2, '第二句', 'bob@example.com', true]);
  assert.deepEqual([cg.wish, cg.reply, cf.reply, cf.email], [1, true, false, 'old@example.com']);
  assert.equal(L.convs[0].ck, cf.ck, '最新的排最上面');
  // 打開會員那串 → 已讀；會員那邊看到「已讀」
  const th = (await pj(hub, '/v1/admin/chat/thread', { t: andy, ck: cb.ck })).j;
  assert.equal(th.msgs.length, 2); assert.equal(th.reply, true);
  assert.ok(th.msgs.every((x) => 'ua' in x && 'status' in x), '管理端帶瀏覽器資訊與狀態');
  assert.equal((await pj(hub, '/v1/admin/chat/list', { t: andy })).j.convs.find((c) => c.ck === cb.ck).unread, 0);
  assert.ok((await pj(hub, '/v1/chat/mine', { t: bob })).j.msgs.every((x) => x.read));
  // 回覆
  assert.equal((await post(hub, '/v1/admin/chat/reply', { t: bob, ck: cb.ck, body: '冒充' })).status, 403);
  assert.equal((await post(hub, '/v1/admin/chat/reply', { t: andy, ck: cb.ck, body: '' })).status, 400);
  assert.equal((await post(hub, '/v1/admin/chat/reply', { t: andy, ck: 'u:nobody', body: 'x' })).status, 404);
  assert.equal((await post(hub, '/v1/admin/chat/reply', { t: andy, ck: cf.ck, body: 'x' })).status, 409, '舊式訪客回不了');
  clock += 1000;
  const r = (await pj(hub, '/v1/admin/chat/reply', { t: andy, ck: cb.ck, body: '已修好，請重新整理' })).j;
  assert.ok(r.ok && r.msg.id);
  let m = (await pj(hub, '/v1/chat/mine', { t: bob })).j;
  assert.deepEqual(m.msgs.map((x) => [x.me, x.body]), [[true, '第一句'], [true, '第二句'], [false, '已修好，請重新整理']]);
  assert.equal(m.unread, 1);
  assert.ok(!('by' in m.msgs[2]), '會員端不回管理者 email');
  const fl = (await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.feedback;
  assert.ok(fl.filter((x) => x.body.endsWith('句')).every((x) => x.status === 'handled' && x.aread > 0), '回覆＝已處理');
  assert.equal((await pj(hub, '/v1/chat/seen', { t: bob })).s, 200);
  assert.equal((await pj(hub, '/v1/chat/mine', { t: bob })).j.unread, 0, '讀過之後未讀歸零');
  // 訪客那串：回覆只有那個瀏覽器看得到；願望狀態不被回覆改掉
  await pj(hub, '/v1/admin/chat/reply', { t: andy, ck: cg.ck, body: '願望收到' });
  assert.deepEqual((await pj(hub, '/v1/chat/mine', { gk: GK_A })).j.msgs.map((x) => x.body), ['訪客的願望', '願望收到']);
  assert.equal((await pj(hub, '/v1/chat/mine', { gk: GK_B })).j.msgs.length, 0);
  assert.equal((await pj(hub, '/v1/admin/feedback/list', { t: andy })).j.feedback.find((x) => x.type === 'wish').status, 'new', '願望評估狀態不動');
  // 刪掉一則回覆
  await pj(hub, '/v1/admin/chat/del', { t: andy, id: r.msg.id });
  assert.equal((await pj(hub, '/v1/chat/mine', { t: bob })).j.msgs.length, 2);
  assert.equal((await post(hub, '/v1/admin/chat/thread', { t: andy, ck: 'bad key' })).status, 400);
});

test('刪帳號連回覆一起刪；13 個月後清掉', async () => {
  const { hub, db } = makeHub(env());
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  await pj(hub, '/v1/feedback', { t: bob, cat: 'bug', body: '要刪的' });
  const ck = (await pj(hub, '/v1/admin/chat/list', { t: andy })).j.convs[0].ck;
  await pj(hub, '/v1/admin/chat/reply', { t: andy, ck, body: '回覆' });
  await pj(hub, '/v1/feedback', { gk: GK_A, cat: 'bug', body: '訪客' });
  const cg = (await pj(hub, '/v1/admin/chat/list', { t: andy })).j.convs.find((c) => c.ck.startsWith('g:')).ck;
  await pj(hub, '/v1/admin/chat/reply', { t: andy, ck: cg, body: '給訪客' });
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM fb_reply').get().n, 2);
  assert.equal((await post(hub, '/v1/delete', { t: bob })).status, 200);
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM fb_reply').get().n, 1, '會員的回覆跟著刪');
  clock += 400 * 86400 * 1000;
  hub.cleanup();
  assert.equal(db.prepare('SELECT COUNT(*) AS n FROM fb_reply').get().n, 0, '超過 13 個月清掉');
});
