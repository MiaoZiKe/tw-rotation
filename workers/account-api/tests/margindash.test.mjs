/* 全市場信用風險（官方儀表板）人工登錄（2026-11-06）：訪客讀得到種子；只有管理者能寫／刪；格式檢查；同日覆蓋；種子跟前端那份一致 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { makeHub } from '../harness.mjs';
import { MDASH_SEED, mdashClean } from '../margindash.js';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
let clock = Date.parse('2026-11-06T10:00:00Z');
const env = { ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock };
const pj = async (hub, path, body) => {
  const r = await hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const pending = {};
globalThis.fetch = async (url, init) => {
  if (String(url).startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body); const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  throw new Error('測試不准連外網：' + url);
};
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location')); const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await hub.fetch(new Request(API + '/auth/redeem', { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify({ n }) }))).json()).tok;
}
const ROW = { d: '2026-11-06', mmr: 158.4, call_n: 2500, call_amt: 28.1, disp_n: 240, disp_amt: 7, note: '測試' };

test('種子：Worker 的 MDASH_SEED 跟 site/margin_dashboard_seed.json 一模一樣', () => {
  const f = JSON.parse(readFileSync(new URL('../../../site/margin_dashboard_seed.json', import.meta.url), 'utf8'));
  assert.deepEqual(f.rows, MDASH_SEED);
  for (const r of MDASH_SEED) assert.equal(mdashClean(r)[0], null, '種子本身要通過格式檢查：' + r.d);
});

test('讀：訪客不用登入；沒存過回種子（src=seed）', async () => {
  const { hub } = makeHub(env);
  const r = await pj(hub, '/v1/mdash/get', {});
  assert.equal(r.s, 200); assert.equal(r.j.src, 'seed'); assert.deepEqual(r.j.rows, MDASH_SEED);
});

test('寫／刪：只有管理者；訪客與一般會員 403、被擋就不會寫入', async () => {
  const { hub } = makeHub(env);
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/admin/mdash/put', { row: ROW })).s, 403, '沒登入不能寫');
  assert.equal((await pj(hub, '/v1/admin/mdash/put', { t: bob, row: ROW })).s, 403, '一般會員不能寫');
  assert.equal((await pj(hub, '/v1/admin/mdash/del', { t: bob, d: '2026-11-05' })).s, 403, '一般會員不能刪');
  assert.equal((await pj(hub, '/v1/mdash/get', {})).j.src, 'seed', '被擋就不會寫入');
  const w = await pj(hub, '/v1/admin/mdash/put', { t: andy, row: ROW });
  assert.equal(w.s, 200); assert.equal(w.j.src, 'server');
  assert.deepEqual(w.j.rows.map((r) => r.d), ['2026-10-30', '2026-11-05', '2026-11-06'], '第一次寫入時種子兩筆保留、依日期排序');
  const g = await pj(hub, '/v1/mdash/get', {});
  assert.equal(g.j.rows[2].mmr, 158.4); assert.equal(g.j.rows[2].note, '測試'); assert.equal(g.j.rows[2].disp_amt, 7);
  assert.ok(!JSON.stringify(g.j).includes('andy@'), '不記 email');
  // 同一天＝覆蓋（修改）
  const u = await pj(hub, '/v1/admin/mdash/put', { t: andy, row: { ...ROW, mmr: 160.123, call_n: 2400 } });
  assert.equal(u.j.rows.length, 3); assert.equal(u.j.rows[2].mmr, 160.12, '金額／維持率四捨五入到小數兩位'); assert.equal(u.j.rows[2].call_n, 2400);
  // 刪除
  assert.equal((await pj(hub, '/v1/admin/mdash/del', { t: andy, d: '2026-10-30' })).j.rows.length, 2);
  assert.equal((await pj(hub, '/v1/admin/mdash/del', { t: andy, d: '2026-10-30' })).s, 404, '刪過的再刪 404');
  assert.equal((await pj(hub, '/v1/admin/mdash/del', { t: andy, d: 'x' })).s, 400);
  await pj(hub, '/v1/admin/mdash/del', { t: andy, d: '2026-11-05' }); await pj(hub, '/v1/admin/mdash/del', { t: andy, d: '2026-11-06' });
  const e = await pj(hub, '/v1/mdash/get', {});
  assert.deepEqual(e.j.rows, [], '刪到空就是空，不會長回種子'); assert.equal(e.j.src, 'server');
});

test('格式檢查：維持率 100～300、戶數整數、金額 ≥ 0、日期合法、至少一個數字、備註長度', async () => {
  const { hub } = makeHub(env);
  const andy = await login(hub, 'andy@example.com');
  const bad = async (row, code) => { const r = await pj(hub, '/v1/admin/mdash/put', { t: andy, row }); assert.equal(r.s, 400, JSON.stringify(row)); assert.equal(r.j.error, code); };
  await bad({ ...ROW, mmr: 99.9 }, 'bad_mmr');
  await bad({ ...ROW, mmr: 300.1 }, 'bad_mmr');
  await bad({ ...ROW, mmr: '159' }, 'bad_mmr');
  await bad({ ...ROW, call_n: 12.5 }, 'bad_call_n');
  await bad({ ...ROW, disp_n: -1 }, 'bad_disp_n');
  await bad({ ...ROW, call_amt: -0.01 }, 'bad_call_amt');
  await bad({ ...ROW, disp_amt: 1e9 }, 'bad_disp_amt');
  await bad({ ...ROW, d: '2026-02-30' }, 'bad_date');
  await bad({ ...ROW, d: '26-11-06' }, 'bad_date');
  await bad({ d: '2026-11-06', mmr: null, call_n: null, call_amt: null, disp_n: null, disp_amt: null }, 'empty');
  await bad({ ...ROW, note: 'x'.repeat(121) }, 'bad_note');
  await bad('x', 'bad_row');
  assert.equal((await pj(hub, '/v1/admin/mdash/put', { t: andy, row: { d: '2026-11-07', call_n: 0, disp_n: 0 } })).s, 200, '只填部分欄位、0 也算有填');
  const r = await pj(hub, '/v1/admin/mdash/put', { t: andy, row: { ...ROW, note: '<script>' } });
  assert.ok(!r.j.rows.find((x) => x.d === ROW.d).note.includes('<'), '備註去掉角括號');
});
