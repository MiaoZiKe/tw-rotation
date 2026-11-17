// node --test workers/ai-office-bridge/test/member_state_me.test.mjs —— 2026-11-16 會員畫面讀自己的即時狀態：
// 網址寫 me＝「我自己的辦公室」：state／projects／usage 都能用；會員只看得到自己接入碼送進來的事件、看不到站長 main 的；
// 站長寫 me 等於 main；別人的代號、沒建辦公室的會員一律擋下。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', A = 'member-a-token-0123456789abcdef', B = 'member-b-token-0123456789abcdef';
const req = (h, method, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, {
  method, headers: { 'Content-Type': 'application/json', ...hdr }, body: body == null ? undefined : JSON.stringify(body),
}));
const as = (tok) => ({ Origin: SITE, 'X-AIO-Session': tok });
const ev = (sid, name, extra = {}) => ({ event: 'SessionStart', session_id: sid, project_hash: 'ab12cd34ef567890', project_name: name, ts: 1_800_000_000_000, ...extra });

test('state／projects／usage 用 me：會員讀自己的、站長讀 main、互相看不到', async () => {
  const h = makeHub({ ACCOUNT: fakeAccount({ [OWNER]: true, [A]: false, [B]: false }) });
  const mainCode = await h.hub.devIssue();
  assert.equal((await req(h, 'POST', '/v1/events', { events: [ev('s-own', '站長專案')] }, { Authorization: 'Bearer ' + mainCode })).status, 200);
  // 沒建辦公室：401（readerOffice 不認）
  assert.equal((await req(h, 'GET', '/v1/office/me/state', null, { 'X-AIO-Session': A })).status, 401);
  assert.equal((await req(h, 'POST', '/v1/offices', { name: 'A 的' }, as(A))).status, 200);
  assert.equal((await req(h, 'POST', '/v1/offices', { name: 'B 的' }, as(B))).status, 200);
  const ca = await claim(h, A);
  assert.match(ca.office, /^u_/); assert.ok(ca.code);
  assert.equal((await req(h, 'POST', '/v1/events', { events: [ev('s-a', 'A 專案'), ev('s-a2', 'A 專案')] }, { Authorization: 'Bearer ' + ca.code })).status, 200);
  const sa = await (await req(h, 'GET', '/v1/office/me/state', null, { 'X-AIO-Session': A })).json();
  assert.equal(sa.office, ca.office); assert.equal(sa.total_events, 2);
  assert.ok(!JSON.stringify(sa).includes('站長專案'));
  // 用自己的接入碼讀 me 也是自己的
  assert.equal((await (await req(h, 'GET', '/v1/office/me/state', null, { Authorization: 'Bearer ' + ca.code })).json()).total_events, 2);
  // B 讀 me：自己的（空）；寫 A 的代號：403
  assert.equal((await (await req(h, 'GET', '/v1/office/me/state', null, { 'X-AIO-Session': B })).json()).total_events, 0);
  assert.equal((await req(h, 'GET', '/v1/office/' + ca.office + '/state', null, { 'X-AIO-Session': B })).status, 403);
  // 站長 me＝main
  const so = await (await req(h, 'GET', '/v1/office/me/state', null, { 'X-AIO-Session': OWNER })).json();
  assert.equal(so.office, 'main'); assert.equal(so.total_events, 1);
  // 會員讀 main：403
  assert.equal((await req(h, 'GET', '/v1/office/main/state', null, { 'X-AIO-Session': A })).status, 403);
  const pj = await (await req(h, 'GET', '/v1/office/me/projects', null, { 'X-AIO-Session': A })).json();
  assert.equal(pj.projects.length, 1); assert.equal(pj.office, ca.office);
  assert.equal((await req(h, 'GET', '/v1/office/me/usage', null, { 'X-AIO-Session': A })).status, 200);
});
const claim = async (h, tok) => (await req(h, 'POST', '/v1/claim', { t: tok }, { Origin: SITE })).json();
