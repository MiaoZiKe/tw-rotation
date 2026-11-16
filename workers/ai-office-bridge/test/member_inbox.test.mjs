// node --test workers/ai-office-bridge/test/member_inbox.test.mjs —— 2026-11-16 開放一般會員用對話框：
// 驗：建了辦公室的一般會員可以對「自己的」收件匣送指令與讀回覆（200）；碰站長的 main 或別人的代號一律 403；
//     沒建辦公室＝403 no_office；自己的接入碼只取得到自己的指令；會員每分鐘 5 則限速。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', A = 'member-a-token-0123456789abcdef', B = 'member-b-token-0123456789abcdef';
async function setup() {
  let t = 1_800_000_000_000;
  const h = makeHub({ ACCOUNT: fakeAccount({ [OWNER]: true, [A]: false, [B]: false }) }, { now: () => t });
  return { ...h, tick: (ms) => { t += ms; } };
}
const req = (h, method, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, {
  method, headers: { 'Content-Type': 'application/json', ...hdr }, body: body == null ? undefined : JSON.stringify(body),
}));
const as = (tok) => ({ Origin: SITE, 'X-AIO-Session': tok });
const mkOffice = (h, tok, name) => req(h, 'POST', '/v1/offices', { name }, as(tok));
const claim = async (h, tok) => (await req(h, 'POST', '/v1/claim', { t: tok }, { Origin: SITE })).json();

test('一般會員：沒建辦公室 403 no_office；建了之後本人 200、別人與站長的 403', async () => {
  const h = await setup();
  let r = await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: '嗨' }, as(A));
  assert.equal(r.status, 403); assert.equal((await r.json()).error, 'no_office');
  assert.equal((await mkOffice(h, A, '我的辦公室')).status, 200);
  assert.equal((await mkOffice(h, B, 'B 的辦公室')).status, 200);
  r = await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: 'A 的秘密指令' }, as(A));
  assert.equal(r.status, 200, '本人送出');
  const j = await r.json(); assert.equal(j.message.status, 'queued');
  const la = await (await req(h, 'GET', '/v1/office/me/inbox', null, as(A))).json();
  assert.equal(la.messages.length, 1); assert.match(la.office, /^u_[0-9a-f]{24}$/);
  // B 讀自己的：看不到 A 的
  const lb = await (await req(h, 'GET', '/v1/office/me/inbox', null, as(B))).json();
  assert.equal(lb.messages.length, 0); assert.notEqual(lb.office, la.office);
  // B 直接寫 A 的代號、或站長的 main：403
  assert.equal((await req(h, 'GET', '/v1/office/' + la.office + '/inbox', null, as(B))).status, 403);
  assert.equal((await req(h, 'POST', '/v1/office/' + la.office + '/inbox', { to: 'ceo', text: 'x' }, as(B))).status, 403);
  assert.equal((await req(h, 'POST', '/v1/office/' + la.office + '/inbox/' + j.message.id + '/cancel', null, as(B))).status, 403);
  assert.equal((await req(h, 'GET', '/v1/office/main/inbox', null, as(A))).status, 403, '會員不能讀站長的');
  assert.equal((await req(h, 'GET', '/v1/office/' + la.office + '/inbox', null, as(OWNER))).status, 403, '站長也不讀會員的收件匣');
  // B 撤回 A 的指令（用 me）：找不到（不同辦公室）
  assert.equal((await req(h, 'POST', '/v1/office/me/inbox/' + j.message.id + '/cancel', null, as(B))).status, 404);
  // 站長原本的路照舊
  assert.equal((await req(h, 'POST', '/v1/office/main/inbox', { to: 'ceo', text: '站長' }, as(OWNER))).status, 200);
});

test('一般會員：自己的接入碼只取得到自己的指令，回覆只回到自己的收件匣', async () => {
  const h = await setup();
  await mkOffice(h, A, 'A'); await mkOffice(h, B, 'B');
  const ca = await claim(h, A), cb = await claim(h, B);
  assert.ok(ca.code && cb.code); assert.notEqual(ca.office, cb.office); assert.notEqual(ca.office, 'main');
  await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: 'A 的' }, as(A));
  const pb = await (await req(h, 'POST', '/v1/inbox/pull', { session_id: 'sb' }, { Authorization: 'Bearer ' + cb.code })).json();
  assert.equal(pb.messages.length, 0, 'B 的 Claude 取不到 A 的指令');
  const pa = await (await req(h, 'POST', '/v1/inbox/pull', { session_id: 'sa' }, { Authorization: 'Bearer ' + ca.code })).json();
  assert.equal(pa.messages.length, 1);
  const mid = pa.messages[0].id;
  assert.equal((await req(h, 'POST', '/v1/inbox/ack', { id: mid, status: 'done', reply: '好了', session_id: 'sb' }, { Authorization: 'Bearer ' + cb.code })).status, 404, 'B 的碼回報不了 A 的指令');
  assert.equal((await req(h, 'POST', '/v1/inbox/ack', { id: mid, status: 'done', reply: '好了', session_id: 'sa' }, { Authorization: 'Bearer ' + ca.code })).status, 200);
  const la = await (await req(h, 'GET', '/v1/office/me/inbox', null, as(A))).json();
  assert.equal(la.messages[0].reply, '好了');
});

test('一般會員：每分鐘最多 5 則', async () => {
  const h = await setup();
  await mkOffice(h, A, 'A');
  for (let i = 0; i < 5; i++) assert.equal((await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: 'x' + i }, as(A))).status, 200);
  assert.equal((await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: 'x6' }, as(A))).status, 429);
  h.tick(61_000);
  assert.equal((await req(h, 'POST', '/v1/office/me/inbox', { to: 'ceo', text: 'x7' }, as(A))).status, 200);
});
