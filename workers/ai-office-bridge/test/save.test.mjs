// node --test workers/ai-office-bridge/test/save.test.mjs —— 雲端存檔（研究報告第 9 項）
// 驗：只有站長網站登入能讀寫、版本號遞增、大小上限、舊 schema 遷移（寫入與讀出兩條路）、最後寫入時間衝突處理、專案數上限、清空不會刪存檔。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';
import { migrateSave, SAVE } from '../worker.js';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', MEMBER = 'member-token-0123456789abcdef';
async function setup() {
  let t = 1_800_000_000_000;
  const h = makeHub({ ACCOUNT: fakeAccount() }, { now: () => t });
  const code = await h.hub.devIssue();
  return { ...h, code, tick: (ms) => { t += ms; }, t: () => t };
}
const req = (h, method, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, {
  method, headers: { 'Content-Type': 'application/json', ...hdr }, body: body == null ? undefined : JSON.stringify(body),
}));
const site = (extra = {}) => ({ Origin: SITE, 'X-AIO-Session': OWNER, ...extra });
const put = (h, body, proj = 'aaaaaaaaaaaaaaaa', hdr = site()) => req(h, 'POST', '/v1/office/main/save/' + proj, body, hdr);
const get = async (h, proj = 'aaaaaaaaaaaaaaaa') => (await req(h, 'GET', '/v1/office/main/save/' + proj, null, site())).json();
const LAY = 'aiOffice.world.layout.v1';

test('讀寫：第一次寫 version 1、再寫 +1；讀回同一份；沒存過回 save:null', async () => {
  const h = await setup();
  assert.equal((await get(h)).save, null);
  let r = await put(h, { schema: 2, base: null, at: h.t(), data: { keys: { [LAY]: '{"floor":{"r1":"#fff"}}', 'aiOffice.game.coins': '12' } } });
  assert.equal(r.status, 200); let j = await r.json(); assert.equal(j.version, 1); assert.equal(j.conflict, null);
  h.tick(1000);
  j = await (await put(h, { schema: 2, base: 1, at: h.t(), data: { keys: { [LAY]: '{"floor":{"r1":"#000"}}' } } })).json();
  assert.equal(j.version, 2);
  const g = await get(h);
  assert.equal(g.save.version, 2); assert.equal(g.save.schema, SAVE.schema);
  assert.deepEqual(g.save.data.keys, { [LAY]: '{"floor":{"r1":"#000"}}' });
});

test('身分：一般會員、接入碼、沒有 Origin、別的辦公室都不能讀寫', async () => {
  const h = await setup();
  const body = { schema: 2, data: { keys: {} } };
  assert.equal((await put(h, body, 'p1', site({ 'X-AIO-Session': MEMBER }))).status, 401);
  assert.equal((await put(h, body, 'p1', { Origin: SITE, Authorization: 'Bearer ' + h.code })).status, 401);
  assert.equal((await put(h, body, 'p1', { 'X-AIO-Session': OWNER })).status, 403);
  assert.equal((await req(h, 'POST', '/v1/office/other/save/p1', body, site())).status, 403);
  assert.equal((await req(h, 'GET', '/v1/office/main/save/p1', null, site({ 'X-AIO-Session': MEMBER }))).status, 401);
});

test('過濾與上限：不在白名單的鍵丟掉；資料太大 413；格式比伺服器新 409；專案數上限', async () => {
  const h = await setup();
  await put(h, { schema: 2, data: { keys: { 'aiOffice.live.v1': '{"code":"x"}', 'tw.acct.tok': 'secret', 'aiOffice.game.ok': '1', 'aiOffice.game.num': 5 } } });
  assert.deepEqual((await get(h)).save.data.keys, { 'aiOffice.game.ok': '1' }, '接入設定、登入權杖、非字串值都不收');
  const big = {}; for (let i = 0; i < 4; i++) big['aiOffice.game.k' + i] = 'x'.repeat(20000);
  assert.equal((await put(h, { schema: 2, base: 1, data: { keys: big } })).status, 413);
  assert.equal((await put(h, { schema: 2, data: { keys: { 'aiOffice.game.x': 'y'.repeat(100 * 1024) } } })).status, 413, '整包超過上限');
  assert.equal((await put(h, { schema: 99, data: { keys: {} } })).status, 409);
  for (let i = 1; i < SAVE.maxProjects; i++) assert.equal((await put(h, { schema: 2, data: { keys: {} } }, 'p' + i)).status, 200);
  assert.equal((await put(h, { schema: 2, data: { keys: {} } }, 'one-too-many')).status, 429);
});

test('遷移：schema 1 寫入被升成 schema 2；資料庫裡留著舊格式的，讀出來也升級', async () => {
  const h = await setup();
  const j = await (await put(h, { schema: 1, data: { layout: { floor: { r1: '#abc' } }, game: { coins: 30, title: '新手' } } })).json();
  assert.equal(j.migrated, true);
  const k = (await get(h)).save.data.keys;
  assert.deepEqual(JSON.parse(k[LAY]), { floor: { r1: '#abc' } });
  assert.equal(k['aiOffice.game.coins'], '30'); assert.equal(k['aiOffice.game.title'], '新手');
  // 直接塞一筆舊格式到資料庫（模擬舊版伺服器存的）
  h.db.prepare('INSERT INTO saves (office, proj, ver, schema, data, size, at, rcv) VALUES (?,?,?,?,?,?,?,?)').run('main', 'old', 7, 1, JSON.stringify({ layout: { f: { d1: [1, 2, 0] } } }), 10, 1, 1);
  const g = (await get(h, 'old')).save;
  assert.equal(g.version, 7); assert.equal(g.schema, 2); assert.deepEqual(JSON.parse(g.data.keys[LAY]), { f: { d1: [1, 2, 0] } });
  assert.equal(migrateSave(1, null), null);
  assert.equal(migrateSave(3, { keys: {} }), null);
});

test('衝突：版本對不上時，最後寫入時間比較新的贏（回 conflict:overwrote），比較舊的回 409 附上伺服器那份', async () => {
  const h = await setup();
  const t0 = h.t();
  await put(h, { schema: 2, base: null, at: t0, data: { keys: { 'aiOffice.game.a': 'A裝置' } } });               // v1
  h.tick(5000);
  await put(h, { schema: 2, base: 1, at: t0 + 5000, data: { keys: { 'aiOffice.game.a': 'A裝置第二次' } } });     // v2
  // B 裝置還停在 v1，而且它的改動比 v2 舊 → 409，拿到伺服器那份
  let r = await put(h, { schema: 2, base: 1, at: t0 + 2000, data: { keys: { 'aiOffice.game.a': 'B裝置舊改動' } } });
  assert.equal(r.status, 409); let j = await r.json();
  assert.equal(j.error, 'conflict'); assert.equal(j.save.version, 2); assert.equal(j.save.data.keys['aiOffice.game.a'], 'A裝置第二次');
  // B 裝置之後又改了（比 v2 新）→ 寫入成功，標 overwrote
  h.tick(5000);
  r = await put(h, { schema: 2, base: 1, at: t0 + 9000, data: { keys: { 'aiOffice.game.a': 'B裝置新改動' } } });
  j = await r.json(); assert.equal(r.status, 200); assert.equal(j.conflict, 'overwrote'); assert.equal(j.version, 3);
  // 前端時鐘快很多：at 最多只算到伺服器時間 +1 分鐘
  j = await (await put(h, { schema: 2, base: 3, at: h.t() + 86400e3, data: { keys: {} } })).json();
  assert.ok(j.at <= h.t() + 60e3);
});

test('限速：每分鐘寫入超過上限回 429；清空辦公室不刪存檔', async () => {
  const h = await setup();
  let last = 0;
  for (let i = 0; i < 31; i++) last = (await put(h, { schema: 2, base: i || null, at: h.t() + i, data: { keys: {} } })).status;
  assert.equal(last, 429);
  assert.equal((await req(h, 'POST', '/v1/office/main/wipe', { t: OWNER }, { Origin: SITE })).status, 200);
  assert.ok((await get(h)).save, '清空事件不會連存檔一起刪');
});
