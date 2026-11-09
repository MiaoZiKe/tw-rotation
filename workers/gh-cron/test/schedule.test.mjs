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
  // 2026-11-02 降量模式：盤中 12:00 不再派（盤中不發文）
  for (const t of ['09:33', '11:03', '12:00', '13:03']) assert.deepEqual(names(tpe(`${day} ${t}`)), []);
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
  assert.equal(dueJobs(tpe('2026-10-27 15:38')).length, 1);
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

test('2026-11-02 降量模式（Andy：「同意降量」）：主題文章、IG 晚間發文、晚間監工、盤中一律不派', () => {
  const stopped = ['social_news.yml', 'ig_post.yml', 'ig_news_watch.yml'];
  for (const j of SCHEDULE) assert.ok(!stopped.includes(j.workflow), `${j.at} ${j.workflow} 應該已拿掉`);
  assert.ok(!SCHEDULE.some((j) => j.workflow === 'social-live.yml' && j.inputs.kind === 'intraday'), '盤中 12:00 應該已拿掉');
  for (const day of ['2026-10-31', '2026-11-01', '2026-11-02']) {   // 週六、週日、週一（交易日）
    for (const t of ['10:15', '10:45', '12:00', '19:00', '19:40', '19:42', '20:04', '20:32', '20:54', '20:58', '21:08', '21:22', '21:32', '21:44', '21:54', '22:04', '22:12']) {
      assert.deepEqual(names(tpe(`${day} ${t}`), { enabled: { premarket: true } }), [], `${day} ${t}`);
    }
  }
});

test('2026-11-02 降量模式：資料管線（daily.yml）派工一條都沒少', () => {
  const daily = SCHEDULE.filter((j) => j.workflow === 'daily.yml').map((j) => `${j.at} ${j.days} ${j.inputs.phase}`);
  const want = [
    ...['14:16', '14:46', '15:16'].map((t) => `${t} trading inst`), '15:38 trading price',
    ...['16:16', '16:46', '16:56', '17:06', '17:16', '17:26', '17:36', '17:46', '17:56', '18:16'].map((t) => `${t} trading inst`),
    '18:38 trading full', ...['19:16', '19:46', '20:16', '20:46', '21:16'].map((t) => `${t} trading inst`), '21:38 trading full',
    '05:07 tueSat news',
  ];
  assert.deepEqual(daily, want);
  // 盤前 08:20 留著（只為了更新網站盤前消息；發文被 post_quota.json 擋下）
  assert.deepEqual(names(tpe('2026-11-02 08:20'), { enabled: { premarket: true } }), ['social-live.yml:{"kind":"premarket","dry_run":"false"}']);
});

// 2026-11-09：派 inst 前先查 daily.yml 有沒有排隊／執行中的 run，避免 concurrency 只留 1 個 pending 時把 price／full 擠掉
function mkFetch(byStatus, calls) {
  return async (url, init) => {
    calls.push({ url, init });
    if (init && init.method === 'POST') return { status: 204, text: async () => '' };
    const st = new URL(url).searchParams.get('status');
    return { status: 200, json: async () => ({ workflow_runs: byStatus[st] || [] }), text: async () => '' };
  };
}
const NOW = tpe('2026-11-09 16:16');
const run = (id, title, minsAgo = 5) => ({ id, display_title: title, created_at: new Date(NOW - minsAgo * 60000).toISOString() });
const guardEnv = { GH_DISPATCH_TOKEN: 'T', GH_REPO: 'MiaoZiKe/tw-rotation', GH_REF: 'main' };
const posts = (calls) => calls.filter((c) => c.init && c.init.method === 'POST');

test('inst 派工前：沒有任何排隊／執行中的 run → 照常派', async () => {
  const calls = [];
  const done = await runScheduled(NOW, guardEnv, mkFetch({}, calls), { log() {}, error() {} });
  assert.equal(done.length, 1);
  assert.equal(posts(calls).length, 1);
  assert.equal(calls.filter((c) => !c.init.method || c.init.method === 'GET').length, 4);   // queued／pending／waiting／in_progress 各查一次
});

test('inst 派工前：有排隊中的 price／full → 這次 inst 不派', async () => {
  for (const st of ['queued', 'pending']) {
    const calls = [];
    const done = await runScheduled(NOW, guardEnv, mkFetch({ [st]: [run(1, '每日盤後管線 (price)')] }, calls), { log() {}, error() {} });
    assert.deepEqual(done, [], st);
    assert.equal(posts(calls).length, 0, st);
  }
});

test('inst 派工前：有執行中的 run 也讓路；超過 2 小時的卡死 run 不算', async () => {
  let calls = [];
  assert.deepEqual(await runScheduled(NOW, guardEnv, mkFetch({ in_progress: [run(2, '每日盤後管線 (full)')] }, calls), { log() {}, error() {} }), []);
  calls = [];
  const done = await runScheduled(NOW, guardEnv, mkFetch({ in_progress: [run(3, '每日盤後管線 (full)', 180)] }, calls), { log() {}, error() {} });
  assert.equal(done.length, 1);
});

test('inst 派工前：查 GitHub 失敗 → 放行照派（不讓 API 小狀況變成整天不抓法人）', async () => {
  const calls = [];
  const errs = [];
  const f = async (url, init) => {
    calls.push({ url, init });
    if (init && init.method === 'POST') return { status: 204, text: async () => '' };
    return { status: 500, json: async () => ({}), text: async () => '' };
  };
  const done = await runScheduled(NOW, guardEnv, f, { log() {}, error: (m) => errs.push(m) });
  assert.equal(done.length, 1);
  assert.equal(errs.length, 1);
});

test('price／full／news 派工不受 guard 影響（不查、直接派）', async () => {
  const calls = [];
  const f = mkFetch({ queued: [run(9, '每日盤後管線 (inst)')], in_progress: [run(10, '每日盤後管線 (inst)')] }, calls);
  const done = await runScheduled(tpe('2026-11-09 15:38'), guardEnv, f, { log() {}, error() {} });
  assert.equal(done.length, 1);
  assert.equal(calls.length, 1);
});
