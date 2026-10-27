/* 行銷漏斗（W2，2026-10-26）：註冊／體驗／付費由 Worker 自己算，歸在「首次來源」；首次來源只寫一次；舊會員不算註冊；壞來源不收。
 * 跑法：node --test workers/account-api/tests/funnel.test.mjs
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
globalThis.fetch = async (url) => { throw new Error('測試不准連外網：' + url); };
let clock = Date.parse('2026-10-27T01:00:00+08:00');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: 'c', GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
const post = async (hub, path, body) => {
  const r = await hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};
async function mkUser(hub, db, uid, createdMs) {
  db.prepare('INSERT INTO users (uid, subh, email, name, pic, created, seen, tv) VALUES (?, ?, ?, ?, ?, ?, ?, 1)').run(uid, 'h' + uid, uid + '@example.com', uid, '', createdMs, createdMs);
  return await hub.sign(uid, 1);
}
const usage = (db, k) => (db.prepare('SELECT SUM(n) AS n FROM usage WHERE k = ?').get(k).n || 0);
const e2 = (db, comp, d) => (db.prepare('SELECT SUM(n) AS n FROM ev2 WHERE comp = ? AND detail = ?').get(comp, d).n || 0);

test('新會員第一次送來源：算一次註冊，歸在該來源；再送不重算、來源不改', async () => {
  const { hub, db } = makeHub(env());
  const tok = await mkUser(hub, db, 'u1', clock - 60 * 1000);
  let r = await post(hub, '/v1/me/src', { t: tok, src: { s: 'threads', m: 'post', c: 'intraday_1027', x: 'a' } });
  assert.equal(r.s, 200); assert.equal(r.j.first, true);
  assert.equal(usage(db, 'ev:signup'), 1); assert.equal(e2(db, 'fn.signup', 'threads'), 1);
  r = await post(hub, '/v1/me/src', { t: tok, src: { s: 'ig', m: 'story' } });
  assert.equal(r.j.first, false); assert.equal(usage(db, 'ev:signup'), 1);
  assert.equal(JSON.parse(db.prepare('SELECT src FROM users WHERE uid = ?').get('u1').src).s, 'threads');
});

test('沒有來源的新會員算 direct；舊會員（超過 15 分鐘）不算註冊；壞欄位被丟掉', async () => {
  const { hub, db } = makeHub(env());
  const t2 = await mkUser(hub, db, 'u2', clock - 1000);
  await post(hub, '/v1/me/src', { t: t2, src: { s: '<script>', c: 'x y' } });
  assert.equal(e2(db, 'fn.signup', 'direct'), 1);
  assert.equal(db.prepare('SELECT src FROM users WHERE uid = ?').get('u2').src, '');
  const t3 = await mkUser(hub, db, 'u3', clock - 3600 * 1000);
  const r = await post(hub, '/v1/me/src', { t: t3, src: { s: 'threads' } });
  assert.equal(r.j.first, false); assert.equal(usage(db, 'ev:signup'), 1);
  assert.equal((await post(hub, '/v1/me/src', { src: { s: 'x' } })).s, 401);
});

test('付費：第一次開通才算，來源取自 users.src', async () => {
  const { hub, db } = makeHub(env());
  const tok = await mkUser(hub, db, 'u4', clock - 1000);
  await post(hub, '/v1/me/src', { t: tok, src: { s: 'reels' } });
  hub.funnelPaid('u4');
  assert.equal(usage(db, 'ev:paid'), 1); assert.equal(e2(db, 'fn.paid', 'reels'), 1);
});

test('前端送的漏斗事件白名單收得下', async () => {
  const { hub, db } = makeHub(env());
  const r = await post(hub, '/v1/beat', { sid: 'sidFUNNEL0001', r: 'pricing', ev: { 'ev:land': 1, 'ev:pricing_view': 1, 'ev:checkout_click': 2 }, e2: [['other', 'fn.land', 'threads', 1]] });
  assert.equal(r.s, 200);
  assert.equal(usage(db, 'ev:checkout_click'), 2); assert.equal(e2(db, 'fn.land', 'threads'), 1);
});

/* 2026-10-27 依功能分組：?u= 第二段（src.c 去掉 _yyyymmdd）成為 fx.<事件> 的細項；沒有功能碼記 none，各列加總＝全站合計 */
test('依功能：註冊／體驗／付費帶功能碼（fx.*），utm 與無來源記 none', async () => {
  const { hub, db } = makeHub(env());
  const t1 = await mkUser(hub, db, 'f1', clock - 1000);
  await post(hub, '/v1/me/src', { t: t1, src: { s: 'threads', m: 'post', c: 'diagram3d_20261028' } });
  assert.equal(e2(db, 'fx.signup', 'diagram3d'), 1); assert.equal(e2(db, 'fn.signup', 'threads'), 1);
  hub.funnelPaid('f1');
  assert.equal(e2(db, 'fx.paid', 'diagram3d'), 1);
  const t2 = await mkUser(hub, db, 'f2', clock - 1000);
  await post(hub, '/v1/me/src', { t: t2, src: { s: 'ig_bio', m: 'profile', c: 'spring_sale' } });      // utm 活動名不是功能碼
  const t3 = await mkUser(hub, db, 'f3', clock - 1000);
  await post(hub, '/v1/me/src', { t: t3, src: {} });
  assert.equal(e2(db, 'fx.signup', 'none'), 2);
  const sum = db.prepare("SELECT SUM(n) AS n FROM ev2 WHERE comp = 'fx.signup'").get().n;
  assert.equal(sum, usage(db, 'ev:signup'));      // 依功能加總＝全站合計
});

test('依功能：前端送的 fx.* 細項收得下', async () => {
  const { hub, db } = makeHub(env());
  const r = await post(hub, '/v1/beat', { sid: 'sidFUNNEL0002', r: 'overview', ev: { 'ev:land': 1 }, e2: [['other', 'fx.land', 'etf_div', 1], ['other', 'fx.pricing_view', 'none', 1]] });
  assert.equal(r.s, 200);
  assert.equal(e2(db, 'fx.land', 'etf_div'), 1); assert.equal(e2(db, 'fx.pricing_view', 'none'), 1);
});
