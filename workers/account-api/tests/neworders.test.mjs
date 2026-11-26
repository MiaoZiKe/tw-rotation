/* 每日新訂單檢查（neworders.js）：鑰匙、分類、水位（ack 才推進）、不回 email、站主通知冪等 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';
import { classifyRequest } from '../neworders.js';

const API = 'https://tw-account.example.workers.dev';
const KEY = 'daily-bot-key-0123456789';
let clock = Date.parse('2026-11-26T01:07:00Z');
const mk = () => makeHub({ ALLOWED_ORIGINS: 'https://miaozike.github.io', ADMIN_EMAILS: 'andy@example.com', ARTICLE_BOT_KEY: KEY, __now: () => clock });
const call = async (hub, body, key = KEY) => {
  const r = await hub.fetch(new Request(API + '/v1/orders/daily/bot', { method: 'POST', headers: key ? { Authorization: 'Bearer ' + key } : {}, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};
const addReq = (hub, id, type, note, created) => hub.q('INSERT INTO sub_requests (id, uid, email, contact, plan, period, note, created, status, type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', id, 'u' + id, id + '@secret.example', id + '@secret.example', 'pro', 'month', note, created, 'new', type);

test('分類：預約／真訂閱／取消／退款', () => {
  assert.equal(classifyRequest({ type: 'subscribe', note: '[預約開放通知] 冷啟動期預約' }), 'reserve');
  assert.equal(classifyRequest({ note: '要發票' }), 'subscribe');
  assert.equal(classifyRequest({ type: 'cancel', note: '' }), 'cancel');
  assert.equal(classifyRequest({ type: 'refund', note: '[預約開放通知]' }), 'refund');
});

test('沒鑰匙、錯鑰匙、太短的鑰匙 → 403', async () => {
  const { hub } = mk();
  assert.equal((await call(hub, { op: 'check' }, null)).s, 403);
  assert.equal((await call(hub, { op: 'check' }, 'wrong-key-0123456789')).s, 403);
  const { hub: h2 } = makeHub({ ARTICLE_BOT_KEY: 'short', __now: () => clock });
  assert.equal((await call(h2, { op: 'check' }, 'short')).s, 403);
});

test('只有預約：回數量、不寄站主信；有真訂閱：寄一次且不含 email；ack 才推進水位', async () => {
  const { hub } = mk();
  hub.billInit();
  addReq(hub, 'a1', 'subscribe', '[預約開放通知] 冷啟動期預約，非訂閱申請、不扣款', clock - 3600e3);
  addReq(hub, 'a2', 'subscribe', '[預約開放通知] 冷啟動期預約', clock - 7200e3);
  addReq(hub, 'old', 'subscribe', '', clock - 3 * 86400e3);
  let r = await call(hub, { op: 'check' });
  assert.equal(r.s, 200);
  assert.equal(r.j.reserve, 2); assert.equal(r.j.subscribe, 0); assert.equal(r.j.actionable, 0);
  assert.equal(hub.q("SELECT COUNT(*) AS c FROM mail_out").length ? hub.q("SELECT COUNT(*) AS c FROM mail_out")[0].c : 0, 0);
  addReq(hub, 'b1', 'subscribe', '要發票', clock - 600e3);
  addReq(hub, 'b2', 'refund', '', clock - 500e3);
  r = await call(hub, { op: 'check' });
  assert.equal(r.j.subscribe, 1); assert.equal(r.j.refund, 1); assert.equal(r.j.reserve, 2); assert.equal(r.j.actionable, 2);
  assert.ok(!JSON.stringify(r.j).includes('secret.example'), '不可回 email');
  await call(hub, { op: 'check' });   // 同水位再叫一次：信只一封
  assert.equal(hub.q("SELECT COUNT(*) AS c FROM mail_out WHERE subject LIKE '%每日新訂單檢查%'")[0].c, 1);
  // 沒 ack → 隔天仍會再報（連同新的）
  const again = await call(hub, { op: 'check' }); assert.equal(again.j.subscribe, 1);
  // ack 後水位推進，同一批不再出現
  const ack = await call(hub, { op: 'ack', upto: r.j.upto }); assert.equal(ack.j.ok, true);
  clock += 3600e3;
  const next = await call(hub, { op: 'check' });
  assert.equal(next.j.subscribe + next.j.reserve + next.j.refund, 0);
  assert.equal((await call(hub, { op: 'ack', upto: 1 })).s, 400);
});

test('金流訂單：算首單、不算測試單', async () => {
  const { hub } = mk();
  hub.payInit();
  const ins = (id, test, parent) => hub.q("INSERT INTO orders (id, uid, email, plan, plan_name, period, amount, method, status, test, parent, created) VALUES (?, 'u', 'x@y.z', 'pro', 'Pro', 'month', 399, 'bank', 'pending', ?, ?, ?)", id, test, parent, clock - 1000);
  ins('o1', 0, null); ins('o2', 1, null); ins('o3', 0, 'o1');
  const r = await call(hub, { op: 'check' });
  assert.equal(r.j.orders, 1); assert.equal(r.j.actionable, 1);
  assert.equal(r.j.items.find((x) => x.kind === 'order').amount, 399);
});
