// node --test workers/ai-office-bridge/test/offices.test.mjs —— 一個專案一間辦公室（2026-11-15）
// 驗：state 依專案分組（專案清單含進行中工作階段數、?project= 只回該專案）、辦公室清單存在登入帳號下（建立／改名／綁專案／刪除、
//     非站長 3 間由伺服器擋、別人的辦公室看不到也改不了）、每間最多 5 位 Agent 由伺服器擋、收件匣指令帶專案且 Claude 端只取自己專案的。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';
import { capAgents, cleanOfficeName } from '../worker.js';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', M1 = 'member-token-0123456789abcdef', M2 = 'member2-token-0123456789abcdef';
const PA = 'aaaaaaaaaaaaaaaa', PB = 'bbbbbbbbbbbbbbbb', PU = 'cccccccccccccccc';

async function setup() {
  let t = 1_800_000_000_000;
  const h = makeHub({ ACCOUNT: fakeAccount({ [OWNER]: true, [M1]: false, [M2]: false }) }, { now: () => t });
  const code = await h.hub.devIssue();
  return { ...h, code, tick: (ms) => { t += ms; } };
}
const req = (h, method, path, body, hdr = {}) => h.fetch(new Request('https://w' + path, {
  method, headers: { 'Content-Type': 'application/json', ...hdr }, body: body == null ? undefined : JSON.stringify(body),
}));
const as = (tok) => ({ Origin: SITE, 'X-AIO-Session': tok });
const bearer = (c) => ({ Authorization: 'Bearer ' + c });
const ev = (h, list) => req(h, 'POST', '/v1/events', { events: list }, bearer(h.code));
const state = async (h, q = '') => (await req(h, 'GET', '/v1/office/main/state' + q, null, as(OWNER))).json();
const E = (event, sid, ph, name, extra = {}) => ({ event, session_id: sid, project_hash: ph, project_name: name, ts: Date.now(), ...extra });

async function seed(h) {
  await ev(h, [
    E('SessionStart', 's-a1', PA, 'tw-rotation'), E('SessionStart', 's-a2', PA, 'tw-rotation'), E('SessionStart', 's-b1', PB, 'other-repo'), E('SessionStart', 's-u1', PU, 'user'),
    E('SubagentStart', 's-a1', PA, 'tw-rotation', { agent_id: 'ag-a', agent_type: 'frontend-ui' }),
    E('SubagentStart', 's-b1', PB, 'other-repo', { agent_id: 'ag-b', agent_type: 'reviewer' }),
    E('SessionEnd', 's-a2', PA, 'tw-rotation'),
  ]);
}

test('專案清單：名稱、最後活動、進行中工作階段數（已結束的不算）', async () => {
  const h = await setup(); await seed(h);
  const r = await req(h, 'GET', '/v1/office/main/projects', null, as(OWNER));
  assert.equal(r.status, 200);
  const j = await r.json(), by = Object.fromEntries(j.projects.map((p) => [p.hash, p]));
  assert.equal(j.projects.length, 3);
  assert.equal(by[PA].name, 'tw-rotation'); assert.equal(by[PA].active, 1, 's-a2 已結束');
  assert.equal(by[PB].active, 1); assert.equal(by[PU].name, 'user');
  assert.ok(by[PA].last > 0);
  assert.equal((await req(h, 'GET', '/v1/office/main/projects', null, as(M1))).status, 401, '一般會員不能讀');
  assert.equal((await req(h, 'GET', '/v1/office/main/projects')).status, 401);
});

test('專案清單：工作階段 6 小時沒動靜就不算進行中', async () => {
  const h = await setup(); await seed(h);
  h.tick(7 * 3600e3);
  const j = await (await req(h, 'GET', '/v1/office/main/projects', null, as(OWNER))).json();
  assert.ok(j.projects.every((p) => p.active === 0));
});

test('state?project=：只回該專案的事件、工作階段、子 Agent；不帶＝全部；格式不對 400', async () => {
  const h = await setup(); await seed(h);
  const all = await state(h), a = await state(h, '?project=' + PA);
  assert.equal(all.sessions.length, 4); assert.equal(all.agents.length, 2);
  assert.deepEqual(a.sessions.map((s) => s.project_hash).filter((x, i, l) => l.indexOf(x) === i), [PA]);
  assert.deepEqual(a.agents.map((x) => x.agent_type), ['frontend-ui']);
  assert.ok(a.events.length > 0 && a.events.every((e) => !e.project_hash || e.project_hash === PA), '事件只有該專案');
  assert.equal(a.project, PA); assert.equal(a.projects.length, 3, '專案清單永遠完整（切換專案要用）');
  assert.deepEqual(a.types.map((t) => t.agent_type), ['frontend-ui']);
  assert.equal(a.ceo.sessions, 2);
  assert.equal(a.seq, all.seq, '序號是整間辦公室的，切專案不會讓前端誤判成被清空');
  assert.equal((await req(h, 'GET', '/v1/office/main/state?project=zzz', null, as(OWNER))).status, 400);
});

test('辦公室清單：建立、列出、改名、綁專案、刪除；名稱規則與重名', async () => {
  const h = await setup();
  const mk = (name, projects, tok = OWNER) => req(h, 'POST', '/v1/offices', { name, projects }, as(tok));
  const r = await mk('  我的   專案 ', [PA]); assert.equal(r.status, 200);
  const o = (await r.json()).office;
  assert.match(o.id, /^o_[A-Za-z0-9]{6,30}$/); assert.equal(o.name, '我的 專案'); assert.deepEqual(o.projects, [PA]);
  assert.equal((await mk('我的 專案', [])).status, 409, '重名');
  assert.equal((await mk('', [])).status, 400); assert.equal((await mk('字'.repeat(21), [])).status, 400); assert.equal((await mk('a', ['不是雜湊'])).status, 400);
  const up = await req(h, 'POST', '/v1/offices/' + o.id, { name: '改過的名字', projects: [PA, PB] }, as(OWNER));
  assert.equal(up.status, 200); const u = (await up.json()).office; assert.equal(u.name, '改過的名字'); assert.deepEqual(u.projects, [PA, PB]);
  const l = await (await req(h, 'GET', '/v1/offices', null, as(OWNER))).json();
  assert.equal(l.offices.length, 1); assert.equal(l.admin, true);
  assert.equal((await req(h, 'POST', '/v1/offices/' + o.id + '/delete', {}, as(OWNER))).status, 200);
  assert.equal((await (await req(h, 'GET', '/v1/offices', null, as(OWNER))).json()).offices.length, 0);
  assert.equal((await req(h, 'POST', '/v1/offices/' + o.id + '/delete', {}, as(OWNER))).status, 404);
});

test('非站長最多 3 間由伺服器擋；站長 20 間；刪掉一間又能建', async () => {
  const h = await setup();
  const mk = (n, tok) => req(h, 'POST', '/v1/offices', { name: '辦公室' + n }, as(tok));
  const ids = [];
  for (let i = 1; i <= 3; i++) { const r = await mk(i, M1); assert.equal(r.status, 200); ids.push((await r.json()).office.id); }
  const no = await mk(4, M1); assert.equal(no.status, 409); const nj = await no.json(); assert.equal(nj.error, 'office_limit'); assert.equal(nj.max, 3);
  const lim = await (await req(h, 'GET', '/v1/offices', null, as(M1))).json();
  assert.deepEqual(lim.limits, { max: 3, agents: 5 }); assert.equal(lim.admin, false);
  assert.equal((await req(h, 'POST', '/v1/offices/' + ids[0] + '/delete', {}, as(M1))).status, 200);
  assert.equal((await mk(4, M1)).status, 200);
  for (let i = 1; i <= 20; i++) assert.equal((await mk(i, OWNER)).status, 200, '站長第 ' + i + ' 間');
  assert.equal((await mk(21, OWNER)).status, 409);
});

test('辦公室清單屬於帳號：別人看不到、改不了、刪不了；沒登入、沒 Origin 都擋', async () => {
  const h = await setup();
  const o = (await (await req(h, 'POST', '/v1/offices', { name: '我的' }, as(M1))).json()).office;
  assert.equal((await (await req(h, 'GET', '/v1/offices', null, as(M2))).json()).offices.length, 0);
  assert.equal((await req(h, 'POST', '/v1/offices/' + o.id, { name: '搶' }, as(M2))).status, 404);
  assert.equal((await req(h, 'POST', '/v1/offices/' + o.id + '/delete', {}, as(M2))).status, 404);
  assert.equal((await (await req(h, 'GET', '/v1/offices', null, as(M1))).json()).offices[0].name, '我的');
  assert.equal((await req(h, 'GET', '/v1/offices', null, { Origin: SITE })).status, 401);
  assert.equal((await req(h, 'GET', '/v1/offices', null, { 'X-AIO-Session': M1 })).status, 403, '沒有 Origin');
  assert.equal((await req(h, 'GET', '/v1/offices', null, as('bad-token-0123456789abcdefgh'))).status, 401);
  assert.equal((await req(h, 'GET', '/v1/offices', null, { Origin: SITE, ...bearer(h.code) })).status, 401, '接入碼不能管辦公室清單');
});

test('每間辦公室最多 5 位 Agent：capAgents 留下最近有動靜的 5 種類型', () => {
  const ag = ['a', 'b', 'c', 'd', 'e', 'f', 'g'].map((t, i) => ({ agent_type: t, last: 100 + i, agent_id: 'x' + i }));
  ag.push({ agent_type: 'a', last: 50, agent_id: 'x-dup' });
  const r = capAgents(ag, 5);
  assert.deepEqual([...new Set(r.agents.map((x) => x.agent_type))].sort(), ['c', 'd', 'e', 'f', 'g']);
  assert.equal(r.capped, 2); assert.equal(capAgents(ag, null).agents.length, 8, '站長不限');
  assert.equal(cleanOfficeName('  ok  '), 'ok'); assert.equal(cleanOfficeName(5), null);
});

test('state?view=：辦公室有 5 位 Agent 上限時，伺服器只回 5 種類型', async () => {
  const h = await setup();
  const o = (await (await req(h, 'POST', '/v1/offices', { name: '會員的' }, as(M1))).json()).office;
  assert.equal(o.agent_cap, 5);
  await ev(h, ['t1', 't2', 't3', 't4', 't5', 't6', 't7'].map((t, i) => E('SubagentStart', 's-a1', PA, 'tw-rotation', { agent_id: 'ag' + i, agent_type: t })));
  const s = await state(h, '?view=' + o.id);
  assert.equal(new Set(s.agents.map((a) => a.agent_type)).size, 5); assert.equal(s.agents_capped, 2);
  assert.equal((await state(h)).agents.length, 7, '站長自己的檢視不限');
});

test('指令收件匣帶專案：Claude 端只取自己專案（或沒指定專案）的指令', async () => {
  const h = await setup();
  const send = (to, text, project) => req(h, 'POST', '/v1/office/main/inbox', { to, text, project }, as(OWNER));
  assert.equal((await send('ceo', '給 A', PA)).status, 200);
  assert.equal((await send('ceo', '給 B', PB)).status, 200);
  assert.equal((await send('ceo', '不指定')).status, 200);
  assert.equal((await send('ceo', '壞的', 'xyz')).status, 400);
  const pull = async (body) => (await (await req(h, 'POST', '/v1/inbox/pull', { session_id: 's1', max: 5, ...body }, bearer(h.code))).json()).messages;
  const mb = await pull({ project_hash: PB });
  assert.deepEqual(mb.map((m) => m.text).sort(), ['不指定', '給 B'], 'B 專案拿不到 A 的指令');
  const ma = await pull({ project_hash: PA });
  assert.deepEqual(ma.map((m) => m.text), ['給 A']);
  const ml = (await (await req(h, 'GET', '/v1/office/main/inbox?project=' + PA, null, as(OWNER))).json()).messages.map((m) => m.text);
  assert.ok(ml.includes('給 A') && !ml.includes('給 B'), '指令列表也依專案分');
  await send('ceo', '給 A 之二', PA);
  assert.deepEqual(await pull({}), [], '舊外掛沒帶專案雜湊：不會拿到指定專案的指令');
});
