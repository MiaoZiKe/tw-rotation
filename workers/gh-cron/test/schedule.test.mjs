import test from 'node:test';
import assert from 'node:assert/strict';
import { dueJobs, SCHEDULE, taipeiParts } from '../src/schedule.js';
import { runScheduled } from '../src/index.js';

// 台北 yyyy-mm-dd HH:MM → UTC 毫秒
const tpe = (s) => Date.parse(s.replace(' ', 'T') + ':00+08:00');
const names = (ms, opts) => dueJobs(ms, opts).map((j) => `${j.workflow}:${JSON.stringify(j.inputs)}`);

test('台北時間換算：UTC 01:33 ＝ 台北 09:33', () => {
  assert.deepEqual(taipeiParts(Date.UTC(2026, 9, 21, 1, 33)), { date: '2026-10-21', hhmm: '09:33', dow: 3 });
  // 跨日：UTC 週日 21:07 ＝ 台北週一 05:07
  assert.deepEqual(taipeiParts(Date.UTC(2026, 9, 25, 21, 7)), { date: '2026-10-26', hhmm: '05:07', dow: 1 });
});

test('交易日（週三 2026-10-21）每個時間點派對的 workflow', () => {
  const day = '2026-10-21';
  assert.deepEqual(names(tpe(`${day} 12:00`)), ['social-live.yml:{"kind":"intraday","dry_run":"false"}']);
  for (const t of ['09:33', '11:03', '13:03']) assert.deepEqual(names(tpe(`${day} ${t}`)), []);   // 盤中只剩 12:00
  assert.deepEqual(names(tpe(`${day} 15:38`)), ['daily.yml:{"phase":"price"}']);
  for (const t of ['16:16', '16:46', '17:16']) assert.deepEqual(names(tpe(`${day} ${t}`)), ['daily.yml:{"phase":"inst"}']);
  for (const t of ['18:38', '21:38']) assert.deepEqual(names(tpe(`${day} ${t}`)), ['daily.yml:{"phase":"full"}']);
  assert.deepEqual(names(tpe(`${day} 05:07`)), ['daily.yml:{"phase":"news"}']);
});

test('其他分鐘什麼都不派', () => {
  assert.deepEqual(names(tpe('2026-10-21 09:34')), []);
  assert.deepEqual(names(tpe('2026-10-21 03:00')), []);
});

test('盤前預設關、開了才派', () => {
  assert.deepEqual(names(tpe('2026-10-21 08:20')), []);
  assert.deepEqual(names(tpe('2026-10-21 08:20'), { enabled: { premarket: true } }), ['social-live.yml:{"kind":"premarket","dry_run":"false"}']);
});

test('週末與休市日（2026-10-26 光復節補假）不派盤中與盤後', () => {
  for (const day of ['2026-10-24', '2026-10-25', '2026-10-26']) {
    for (const t of ['12:00', '15:38', '16:16', '18:38', '21:38']) {
      assert.deepEqual(names(tpe(`${day} ${t}`)), [], `${day} ${t}`);
    }
  }
  // 隔天週二恢復
  assert.equal(dueJobs(tpe('2026-10-27 12:00')).length, 1);
});

test('清晨 05:07 只在台北週二到週六（週日、週一不派）', () => {
  assert.equal(dueJobs(tpe('2026-10-24 05:07')).length, 1); // 週六
  assert.equal(dueJobs(tpe('2026-10-25 05:07')).length, 0); // 週日
  assert.equal(dueJobs(tpe('2026-10-26 05:07')).length, 0); // 週一
  assert.equal(dueJobs(tpe('2026-10-27 05:07')).length, 1); // 週二
});

test('排程表同一個時間點最多一筆（同一分鐘只派一次）', () => {
  const seen = new Set();
  for (const j of SCHEDULE) { assert.ok(!seen.has(j.at), j.at); seen.add(j.at); }
});

test('runScheduled：呼叫 GitHub 的網址、標頭、內容正確，且錯誤訊息不含 token', async () => {
  const calls = [];
  const fetchImpl = async (url, init) => { calls.push({ url, init }); return { status: 204, text: async () => '' }; };
  const quiet = { log() {}, error() {} };
  const env = { GH_DISPATCH_TOKEN: 'SECRET-TOKEN', GH_REPO: 'MiaoZiKe/tw-rotation', GH_REF: 'main' };
  const done = await runScheduled(tpe('2026-10-21 15:38'), env, fetchImpl, quiet);
  assert.equal(done.length, 1);
  assert.equal(calls[0].url, 'https://api.github.com/repos/MiaoZiKe/tw-rotation/actions/workflows/daily.yml/dispatches');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer SECRET-TOKEN');
  assert.ok(calls[0].init.headers['User-Agent']);
  assert.deepEqual(JSON.parse(calls[0].init.body), { ref: 'main', inputs: { phase: 'price' } });

  const errs = [];
  const bad = async () => ({ status: 401, text: async () => 'Bad credentials SECRET-TOKEN' });
  await runScheduled(tpe('2026-10-21 15:38'), env, bad, { log() {}, error: (m) => errs.push(m) });
  assert.equal(errs.length, 1);
  assert.ok(!errs[0].includes('SECRET-TOKEN'));
  assert.ok(errs[0].includes('401'));

  // 沒設 token：不呼叫、印錯誤
  const errs2 = [];
  const none = await runScheduled(tpe('2026-10-21 15:38'), {}, fetchImpl, { log() {}, error: (m) => errs2.push(m) });
  assert.deepEqual(none, []);
  assert.equal(errs2.length, 1);
  assert.equal(calls.length, 1);
});
