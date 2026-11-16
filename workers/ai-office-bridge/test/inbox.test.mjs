// node --test workers/ai-office-bridge/test/inbox.test.mjs —— 網站指令收件匣（規格 docs/ai_office/chat_command_spec.md）
// 驗：只有擁有者網站登入能寫、接入碼不能寫、瀏覽器拿到碼也取不走、長度與排隊上限、限速、取走不重複、
//     長輪詢會被新指令叫醒、狀態流轉（排隊中→已取走→執行中→完成）、撤回、過期、沒有回音、回覆遮金鑰。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';
import { maskSecrets } from '../worker.js';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', MEMBER = 'member-token-0123456789abcdef';

async function setup() {
  let t = 1_800_000_000_000;
  const h = makeHub({ ACCOUNT: fakeAccount() }, { now: () => t });
  const code = await h.hub.devIssue();
  return { ...h, code, tick: (ms) => { t += ms; } };
}
const req = (h, method, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, {
  method, headers: { 'Content-Type': 'application/json', ...hdr }, body: body == null ? undefined : JSON.stringify(body),
}));
const site = (extra = {}) => ({ Origin: SITE, 'X-AIO-Session': OWNER, ...extra });
const bearer = (c) => ({ Authorization: 'Bearer ' + c });
const send = (h, to, text, hdr = site()) => req(h, 'POST', '/v1/office/main/inbox', { to, text }, hdr);
const pull = (h, body = {}, hdr = bearer(h.code)) => req(h, 'POST', '/v1/inbox/pull', { session_id: 'sess-1', ...body }, hdr);
const ack = (h, body, hdr = bearer(h.code)) => req(h, 'POST', '/v1/inbox/ack', { session_id: 'sess-1', ...body }, hdr);
const list = async (h, q = '') => (await req(h, 'GET', '/v1/office/main/inbox' + q, null, site())).json();

test('寫入：只有擁有者的網站登入可以送；一般會員、接入碼、沒有 Origin、別的網站都不行', async () => {
  const h = await setup();
  const r = await send(h, 'ceo', '把首頁的標題改成藍色');
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.match(j.message.id, /^m_[A-Za-z0-9_-]{16}$/);
  assert.equal(j.message.status, 'queued');
  assert.equal((await send(h, 'ceo', 'x', site({ 'X-AIO-Session': MEMBER }))).status, 401, '一般會員');
  assert.equal((await send(h, 'ceo', 'x', { Origin: SITE, ...bearer(h.code) })).status, 401, '接入碼不能寫收件匣');
  assert.equal((await send(h, 'ceo', 'x', { 'X-AIO-Session': OWNER })).status, 403, '沒有 Origin（不是從網站來）');
  assert.equal((await send(h, 'ceo', 'x', site({ Origin: 'https://evil.example' }))).status, 403, '別的網站');
  assert.equal((await req(h, 'POST', '/v1/office/other/inbox', { to: 'ceo', text: 'x' }, site())).status, 403, '不是自己的辦公室');
});

test('寫入：長度上限 2000 字、空白不收、收件對象格式、排隊最多 20 則、每分鐘 10 則', async () => {
  const h = await setup();
  assert.equal((await send(h, 'ceo', 'あ'.repeat(2001))).status, 413);
  assert.equal((await send(h, 'ceo', 'あ'.repeat(2000))).status, 200);
  assert.equal((await send(h, 'ceo', '   ')).status, 400);
  assert.equal((await send(h, '<script>', 'x')).status, 400);
  assert.equal((await send(h, '', 'x')).status, 400);
  assert.equal((await send(h, 'frontend-ui', '修按鈕')).status, 200);
  for (let i = 0; i < 8; i++) assert.equal((await send(h, 'ceo', '第' + i + '則')).status, 200);
  const r = await send(h, 'ceo', '第 11 則');
  assert.equal(r.status, 429, '每分鐘最多 10 則');
  h.tick(61_000);
  for (let i = 0; i < 10; i++) await send(h, 'ceo', '再' + i);
  h.tick(61_000);
  const full = await send(h, 'ceo', '超過排隊上限');
  assert.equal(full.status, 429);
  assert.equal((await full.json()).error, 'queue_full');
});

test('取走：只認接入碼、瀏覽器帶碼也不行；取走後同一則不會再給第二支工作階段', async () => {
  const h = await setup();
  await send(h, 'ceo', '第一則');
  await send(h, 'reviewer', '第二則');
  assert.equal((await pull(h, {}, {})).status, 401, '沒有碼');
  assert.equal((await pull(h, {}, bearer('aio_wrongwrongwrongwrong'))).status, 401);
  const br = await pull(h, {}, { ...bearer(h.code), Origin: SITE });
  assert.equal(br.status, 403, '瀏覽器（帶 Origin）拿到碼也取不走指令');
  assert.equal((await br.json()).error, 'browser_not_allowed');
  const a = await (await pull(h, { max: 1 })).json();
  assert.equal(a.source, 'website');
  assert.deepEqual(a.messages.map((m) => [m.to, m.text]), [['ceo', '第一則']]);
  const b = await (await pull(h, { session_id: 'sess-2', max: 5 })).json();
  assert.deepEqual(b.messages.map((m) => m.text), ['第二則'], '第二支只拿到剩下的');
  assert.deepEqual((await (await pull(h)).json()).messages, [], '沒有了');
  const l = await list(h);
  assert.deepEqual(l.messages.map((m) => [m.status, m.session_id]), [['claimed', 'sess-1'], ['claimed', 'sess-2']]);
});

test('長輪詢：沒有指令時等著，網站一送就立刻回（不必等滿）', async () => {
  const h = await setup();
  const t0 = Date.now();
  const p = pull(h, { wait: 5 });
  await new Promise((r) => setTimeout(r, 150));
  await send(h, 'ceo', '待命中收到的指令');
  const j = await (await p).json();
  const dt = Date.now() - t0;
  assert.deepEqual(j.messages.map((m) => m.text), ['待命中收到的指令']);
  assert.ok(dt < 2000, '被叫醒，花了 ' + dt + 'ms');
  const t1 = Date.now();
  const e = await (await pull(h, { wait: 0.3 })).json();
  assert.deepEqual(e.messages, []);
  assert.ok(Date.now() - t1 >= 250, '沒有指令就等到時間到');
  const capped = await (await pull(h, { wait: 0 })).json();
  assert.deepEqual(capped.messages, [], 'wait=0 立刻回');
});

test('狀態流轉：排隊中→已取走→執行中→完成；回覆遮掉金鑰；狀態變化寫進事件串', async () => {
  const h = await setup();
  const { message } = await (await send(h, 'frontend-ui', '手機版按鈕太小')).json();
  const r0 = (await list(h)).rev;
  const m = (await (await pull(h)).json()).messages[0];
  assert.equal(m.id, message.id);
  assert.equal((await ack(h, { id: m.id, status: 'running' })).status, 200);
  let l = await list(h, '?since=' + r0);
  assert.equal(l.messages.find((x) => x.id === m.id).status, 'running');
  const key = ['ghp', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'].join('_');
  assert.equal((await ack(h, { id: m.id, status: 'done', reply: '改好了，預覽 https://liguligu-puipui.com/preview/x/ 金鑰 ' + key })).status, 200);
  l = await list(h);
  const done = l.messages.find((x) => x.id === m.id);
  assert.equal(done.status, 'done');
  assert.ok(done.reply.includes('https://liguligu-puipui.com/preview/x/'), '網址保留');
  assert.ok(!done.reply.includes(key), '金鑰遮掉：' + done.reply);
  assert.ok(done.done_at > 0);
  assert.equal((await ack(h, { id: m.id, status: 'running' })).status, 409, '完成後不能再改');
  assert.equal((await ack(h, { id: 'm_doesnotexist000', status: 'done' })).status, 404);
  assert.equal((await ack(h, { id: m.id, status: 'queued' })).status, 400, '只能回報 running／done／failed');
  assert.equal((await ack(h, { id: m.id, status: 'done' }, { ...bearer(h.code), Origin: SITE })).status, 403, '瀏覽器不能回報');
  const st = await (await req(h, 'GET', '/v1/office/main/state', null, bearer(h.code))).json();
  const ups = st.events.filter((e) => e.event === 'InboxUpdate').map((e) => e.status);
  assert.deepEqual(ups, ['queued', 'claimed', 'running', 'done']);
  assert.ok(!JSON.stringify(st.events).includes('手機版按鈕太小'), '事件串不含指令內文');
  assert.equal(st.inbox.queued, 0);
});

test('撤回、過期、沒有回音：排隊中可以撤回；24 小時沒人取走就過期；取走 30 分鐘沒回報顯示沒有回音', async () => {
  const h = await setup();
  const a = (await (await send(h, 'ceo', '要撤回的')).json()).message;
  assert.equal((await req(h, 'POST', `/v1/office/main/inbox/${a.id}/cancel`, {}, site())).status, 200);
  assert.equal((await req(h, 'POST', `/v1/office/main/inbox/${a.id}/cancel`, {}, site())).status, 409);
  assert.deepEqual((await (await pull(h)).json()).messages, [], '撤回的不會交給 Claude');
  const b = (await (await send(h, 'ceo', '沒人取走的')).json()).message;
  h.tick(25 * 3600e3);
  assert.deepEqual((await (await pull(h)).json()).messages, [], '過期的不會交給 Claude');
  assert.equal((await list(h)).messages.find((x) => x.id === b.id).status, 'expired');
  await send(h, 'ceo', '取走後沒回報');
  await pull(h);
  h.tick(31 * 60e3);
  const l = await list(h);
  assert.equal(l.open.length, 1);
  assert.equal(l.open[0].status, 'stale');
});

test('讀列表：只有擁有者；since 增量；刪除紀錄連收件匣一起清', async () => {
  const h = await setup();
  assert.equal((await req(h, 'GET', '/v1/office/main/inbox', null, { Origin: SITE, ...bearer(h.code) })).status, 401, '接入碼不能讀網站對話');
  await send(h, 'ceo', '一');
  const l1 = await list(h);
  await send(h, 'ceo', '二');
  const l2 = await list(h, '?since=' + l1.rev);
  assert.deepEqual(l2.messages.map((m) => m.text), ['二']);
  assert.equal(l2.limits.max_text, 2000);
  await req(h, 'POST', '/v1/office/main/wipe', { t: OWNER }, { Origin: SITE });
  assert.equal((await list(h)).messages.length, 0);
});

test('maskSecrets：遮各家金鑰與 Bearer，保留換行與一般文字', () => {
  const s = maskSecrets('第一行\n' + ['sk', 'ant', 'api03', 'abcdefghijklmnop'].join('-') + ' 與 Bearer ' + 'x'.repeat(20) + ' 與 ' + ['aio', 'Z'.repeat(32)].join('_'), 4000);
  assert.ok(s.startsWith('第一行\n'));
  assert.ok(!/abcdefghijklmnop|xxxxxxxxxxxx|ZZZZZZZZ/.test(s), s);
  assert.equal(maskSecrets('一'.repeat(5000), 10).length, 10);
});

test('最近一次取指令時間：Claude 端每次 pull 都記下，state 與收件匣列表都回傳（網站用它判斷「Claude 在線上待命中」）', async () => {
  const h = await setup();
  const s0 = await (await req(h, 'GET', '/v1/office/main/state', null, site())).json();
  assert.equal(s0.inbox.last_pull, null, '還沒有人取過');
  assert.equal((await list(h)).last_pull, null);
  await pull(h, { wait: 0 });
  const t1 = (await (await req(h, 'GET', '/v1/office/main/state', null, site())).json()).inbox.last_pull;
  assert.equal(t1, h.at ? h.at() : t1, '記的是伺服器時間');
  assert.ok(typeof t1 === 'number' && t1 > 1e12);
  h.tick(45_000);
  assert.equal((await list(h)).last_pull, t1, '沒再取＝時間不變，網站才算得出「多久沒來」');
  await pull(h, { wait: 0 });
  const t2 = (await list(h)).last_pull;
  assert.equal(t2 - t1, 45_000);
  assert.equal((await pull(h, { wait: 0 }, site())).status, 403, '瀏覽器拿到碼也不算在線（不能 pull）');
  assert.equal((await pull(h, { wait: 0 }, bearer('aio_wrongwrongwrongwrong'))).status, 401);
  assert.equal((await list(h)).last_pull, t2, '被擋的請求不更新時間');
});
