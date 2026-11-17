// node --test workers/ai-office-bridge/test/usage.test.mjs —— 每日用量（研究報告第 10 項）
// 驗：usage_main／usage_subagents 是累計值，收件端記差額；跨日（台北時間）分開算；取不到 Token 的工作階段用工具次數推估並標 estimated；
//     有真的數字就不再算推估；依專案過濾；接入碼與站長登入都能讀，一般會員不行。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub, fakeAccount } from './harness.mjs';
import { USAGE } from '../worker.js';

const SITE = 'https://liguligu-puipui.com';
const OWNER = 'owner-token-0123456789abcdef', MEMBER = 'member-token-0123456789abcdef';
const PA = 'aaaaaaaaaaaaaaaa', PB = 'bbbbbbbbbbbbbbbb';
async function setup(t0 = Date.UTC(2027, 0, 5, 2, 0, 0)) {   // 台北 10:00
  let t = t0;
  const h = makeHub({ ACCOUNT: fakeAccount() }, { now: () => t });
  const code = await h.hub.devIssue();
  return { ...h, code, tick: (ms) => { t += ms; } };
}
const ev = (h, list) => h.fetch(new Request('https://w/v1/events', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + h.code }, body: JSON.stringify({ events: list }) }));
const usage = async (h, q = '', hdr = null) => {
  const r = await h.fetch(new Request('https://w/v1/office/main/usage' + q, { headers: hdr || { Authorization: 'Bearer ' + h.code } }));
  return { status: r.status, j: r.status === 200 ? await r.json() : null };
};

test('真的 Token：累計值記差額（主對話＋子 Agent），同一天加總', async () => {
  const h = await setup();
  await ev(h, [{ event: 'SessionStart', session_id: 's1', project_hash: PA }, { event: 'Stop', session_id: 's1', usage_main: 1000, usage_subagents: { ag1: 500 } }]);
  await ev(h, [{ event: 'Stop', session_id: 's1', usage_main: 1800, usage_subagents: { ag1: 700 } }]);
  const { j } = await usage(h);
  assert.equal(j.today, '2027-01-05');
  assert.equal(j.today_usage.tokens, 2500); assert.equal(j.today_usage.real, 2500); assert.equal(j.today_usage.estimated, false);
});

test('跨日：台北午夜之後的差額記到新的一天', async () => {
  const h = await setup(Date.UTC(2027, 0, 5, 15, 50, 0));     // 台北 23:50
  await ev(h, [{ event: 'Stop', session_id: 's1', project_hash: PA, usage_main: 4000 }]);
  h.tick(20 * 60e3);                                          // 台北隔天 00:10
  await ev(h, [{ event: 'Stop', session_id: 's1', usage_main: 6500 }]);
  const { j } = await usage(h);
  assert.equal(j.today, '2027-01-06'); assert.equal(j.today_usage.tokens, 2500);
  assert.deepEqual(j.days.map((d) => [d.day, d.tokens]), [['2027-01-05', 4000], ['2027-01-06', 2500]]);
});

test('估算：取不到 Token 時以工具次數推估並標 estimated；之後有真的數字就只算真的', async () => {
  const h = await setup();
  await ev(h, [{ event: 'SessionStart', session_id: 's2', project_hash: PB }, ...Array.from({ length: 4 }, () => ({ event: 'PreToolUse', session_id: 's2', tool_category: 'read' }))]);
  let { j } = await usage(h);
  assert.equal(j.today_usage.tools, 4); assert.equal(j.today_usage.estimate, 4 * USAGE.estPerTool); assert.equal(j.today_usage.estimated, true);
  await ev(h, [{ event: 'Stop', session_id: 's2', usage_main: 900 }]);
  ({ j } = await usage(h));
  assert.equal(j.today_usage.tokens, 900); assert.equal(j.today_usage.estimated, false); assert.equal(j.today_usage.tools, 4);
});

test('專案過濾與身分：?project= 只算那個專案；站長登入可讀；一般會員、壞的專案碼不行', async () => {
  const h = await setup();
  await ev(h, [{ event: 'Stop', session_id: 'sa', project_hash: PA, usage_main: 100 }, { event: 'Stop', session_id: 'sb', project_hash: PB, usage_main: 300 }]);
  assert.equal((await usage(h)).j.today_usage.tokens, 400);
  assert.equal((await usage(h, '?project=' + PA)).j.today_usage.tokens, 100);
  assert.equal((await usage(h, '?project=' + PB, { Origin: SITE, 'X-AIO-Session': OWNER })).j.today_usage.tokens, 300);
  assert.equal((await usage(h, '', { Origin: SITE, 'X-AIO-Session': MEMBER })).status, 401);
  assert.equal((await usage(h, '?project=zz')).status, 400);
  assert.equal((await usage(h, '', {})).status, 401);
});
