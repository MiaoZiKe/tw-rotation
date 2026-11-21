/* 今日造訪人數（dayvis，2026-10-17）：同一台一天只算一次、跨日重算、公開開關關掉時訪客拿不到、壞代碼不記。
 * 跑法：node --test workers/account-api/tests/*.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
globalThis.fetch = async (url) => { throw new Error('測試不准連外網：' + url); };
const tpe = (s) => Date.parse(s.replace(' ', 'T') + ':00+08:00');
let clock = tpe('2026-10-17 09:10');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: 'c', GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
const pj = async (hub, body, ip = '1.1.1.1') => {
  const r = await hub.fetch(new Request(API + '/v1/track/batch', { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': ip }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};
const send = (hub, sid, vd, extra = {}) => pj(hub, { sid, vd, now: clock, items: [{ ts: clock, r: 'overview', ev: { 'pv:overview': 1 }, live: 1 }], ...extra });

test('同一台（同 vd）重新整理多次只算 1；不同 vd 各算 1；跨日從 0 重算', async () => {
  const { hub } = makeHub(env());
  let r = await send(hub, 'sidAAAAAAAA1', 'vdAAAAAAAAAA');
  assert.equal(r.s, 200); assert.equal(r.j.today, 1); assert.equal(typeof r.j.n, 'number');
  r = await send(hub, 'sidAAAAAAAA2', 'vdAAAAAAAAAA');   // 重新整理：sid 換了、vd 一樣
  assert.equal(r.j.today, 1);
  r = await send(hub, 'sidBBBBBBBB1', 'vdBBBBBBBBBB', {}, '2.2.2.2');
  assert.equal(r.j.today, 2);
  clock = tpe('2026-10-18 00:05');
  r = await send(hub, 'sidCCCCCCCC1', 'vdCCCCCCCCCC');
  assert.equal(r.j.today, 1);
  clock = tpe('2026-10-17 09:10');
});

test('壞的 vd、沒帶 vd、leave 不記；公開開關關掉時訪客拿不到 today', async () => {
  const { hub, db } = makeHub(env());
  let r = await send(hub, 'sidDDDDDDDD1', 'x<script>');
  assert.equal(r.s, 200); assert.equal(r.j.today, 0);
  r = await send(hub, 'sidDDDDDDDD2', undefined);
  assert.equal(r.j.today, 0);
  r = await send(hub, 'sidDDDDDDDD3', 'vdEEEEEEEEEE', { leave: true });
  assert.equal(r.j.today, 0);
  db.prepare("INSERT INTO kv (k, v) VALUES ('public_online', '0') ON CONFLICT(k) DO UPDATE SET v = excluded.v").run();
  r = await send(hub, 'sidDDDDDDDD4', 'vdFFFFFFFFFF');
  assert.equal(r.s, 200); assert.equal(r.j.today, undefined); assert.equal(r.j.n, undefined);
});
