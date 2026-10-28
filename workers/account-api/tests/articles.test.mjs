/* 精選文章點閱次數（2026-10-16）：不用登入、同 IP 30 分鐘只算一次、壞 id 擋下、stats 一次拿全部 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
let clock = Date.parse('2026-10-16T04:00:00Z');
const env = { ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: 'c', GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock };
const pj = async (hub, path, body, ip = '1.1.1.1') => {
  const r = await hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain', 'CF-Connecting-IP': ip }, body: JSON.stringify(body) }));
  return { s: r.status, j: await r.json() };
};

test('點閱：不用登入；同 IP 30 分鐘內只算一次；不同 IP 各算；壞 id 擋；stats 拿全部', async () => {
  const { hub } = makeHub(env);
  const id = '2026-10-14-know-cowos';
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 1);
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 1, '同 IP 30 分鐘內不重算');
  assert.equal((await pj(hub, '/v1/articles/view', { id }, '2.2.2.2')).j.views, 2, '不同 IP 算');
  clock += 31 * 60 * 1000;
  assert.equal((await pj(hub, '/v1/articles/view', { id })).j.views, 3, '超過 30 分鐘再算');
  assert.equal((await pj(hub, '/v1/articles/view', { id: '<script>' })).s, 400);
  await pj(hub, '/v1/articles/view', { id: '2026-10-14-intro-ai-server' });
  assert.deepEqual((await pj(hub, '/v1/articles/stats', {})).j.views, { '2026-10-14-know-cowos': 3, '2026-10-14-intro-ai-server': 1 });
});

/* 產出佇列（2026-10-16）：管理者排、重複不排、取消；機器用備份權杖讀未完成與標狀態；非管理者／錯權杖一律擋 */

const CID = 'test-client.apps.googleusercontent.com';
const BT = 'test-backup-token-0123456789abcdef';
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
const bot = async (hub, body, tok = BT) => { const r = await hub.fetch(new Request(API + '/v1/articles/jobs/bot', { method: 'POST', headers: { Authorization: 'Bearer ' + tok }, body: JSON.stringify(body) })); return { s: r.status, j: await r.json() }; };

test('產出佇列：管理者排／重複不排／取消；備份權杖讀未完成、標狀態；其他人擋', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/articles/jobs/add', { t: bob, topic_id: 'tsmc-q3', kind: 'article', title: 'x' })).s, 403, '非管理者不能排');
  assert.equal((await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'post', title: 'x' })).s, 400, '種類只收 article／video');
  const a = await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'article', title: '台積電法說會', note: '重點放毛利率' });
  assert.equal(a.s, 200); assert.equal(a.j.job.status, 'queued'); assert.equal(a.j.job.note, '重點放毛利率');
  const d = await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'article', title: '台積電法說會' });
  assert.equal(d.j.dup, true); assert.equal(d.j.job.id, a.j.job.id, '同主題同種類未完成不重排');
  const v = await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'video', title: '台積電法說會' });
  assert.notEqual(v.j.job.id, a.j.job.id, '短影片另排一筆');
  assert.equal((await pj(hub, '/v1/articles/jobs/list', { t: bob })).s, 403);
  assert.equal((await pj(hub, '/v1/articles/jobs/list', { t: andy })).j.jobs.length, 2);
  // 機器路由
  assert.equal((await bot(hub, { op: 'open' }, 'wrong-token-wrong-token-wrong')).s, 403);
  assert.equal((await bot(hub, { op: 'open' })).j.jobs.length, 2);
  assert.equal((await bot(hub, { op: 'mark', id: a.j.job.id, status: 'working' })).j.job.status, 'working');
  assert.equal((await pj(hub, '/v1/articles/jobs/cancel', { t: andy, id: a.j.job.id })).s, 409, '製作中不能取消');
  const done = await bot(hub, { op: 'mark', id: a.j.job.id, status: 'done', result: '2026-10-16-news-tsmc-q3' });
  assert.equal(done.j.job.status, 'done'); assert.equal(done.j.job.result, '2026-10-16-news-tsmc-q3');
  assert.equal((await bot(hub, { op: 'mark', id: a.j.job.id, status: 'working' })).s, 409, '完成的不能改回');
  assert.equal((await pj(hub, '/v1/articles/jobs/cancel', { t: andy, id: v.j.job.id })).j.job.status, 'cancelled');
  assert.equal((await bot(hub, { op: 'open' })).j.jobs.length, 0);
  // 完成後同主題可以再排一次
  assert.notEqual((await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'article', title: '台積電法說會' })).j.dup, true);
  // 只有 ARTICLE_BOT_KEY（沒設 BACKUP_TOKEN）也能用；太短的鑰匙不算
  const { hub: h2 } = makeHub({ ...env, ARTICLE_BOT_KEY: 'article-bot-key-0123456789' });
  assert.equal((await bot(h2, { op: 'open' }, 'article-bot-key-0123456789')).s, 200);
  assert.equal((await bot(h2, { op: 'open' }, BT)).s, 403);
  const { hub: h3 } = makeHub({ ...env, ARTICLE_BOT_KEY: 'short' });
  assert.equal((await bot(h3, { op: 'open' }, 'short')).s, 403);

});

test('每日點閱：計數同時記台北日期；管理者讀得到明細、非管理者擋', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  const t0 = clock;
  clock = Date.parse('2026-10-16T17:00:00Z');   // 台北 10-17 01:00
  await pj(hub, '/v1/articles/view', { id: 'a-1111' }, '9.9.9.1');
  await pj(hub, '/v1/articles/view', { id: 'a-1111' }, '9.9.9.2');
  await pj(hub, '/v1/articles/view', { id: 'b-2222' }, '9.9.9.1');
  clock += 86400e3;
  await pj(hub, '/v1/articles/view', { id: 'a-1111' }, '9.9.9.3');
  assert.equal((await pj(hub, '/v1/articles/stats/daily', { t: bob })).s, 403);
  const d = (await pj(hub, '/v1/articles/stats/daily', { t: andy })).j;
  assert.equal(d.first, '2026-10-17');
  assert.deepEqual(d.rows, [['2026-10-17', 'a-1111', 2], ['2026-10-17', 'b-2222', 1], ['2026-10-18', 'a-1111', 1]]);
  assert.deepEqual((await pj(hub, '/v1/articles/stats/daily', { t: andy, from: '2026-10-18' })).j.rows, [['2026-10-18', 'a-1111', 1]]);
  clock = t0;
});

test('產文章頻率設定（第 2 版規則清單）：只有管理者能存／讀；壞輸入擋；排序去重；只留最新一份；機器路由讀得到', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  const r1 = { days: [5, 1, 3, 3], hours: [14, 10], cats: { news: 1 } };
  const r2 = { dates: ['2026-10-20', '2026-10-18'], hours: [21], cats: { news: 0, intro: 2, know: 1 } };
  const ok1 = { ver: 2, enabled: true, rules: [r1, r2] };
  assert.equal((await pj(hub, '/v1/articles/schedule/add', { t: bob, ...ok1 })).s, 403, '非管理者不能存');
  assert.equal((await pj(hub, '/v1/articles/schedule/get', { t: bob })).s, 403, '非管理者不能讀');
  const g0 = await pj(hub, '/v1/articles/schedule/get', { t: andy });
  assert.equal(g0.j.schedule, null, '還沒存過＝null');
  assert.equal(g0.j.allowed.hours.length, 24);
  assert.equal(g0.j.allowed.hours[0], 0); assert.equal(g0.j.allowed.hours[23], 23);
  assert.equal(g0.j.allowed.maxRules, 20); assert.equal(g0.j.allowed.max, 3);
  // 壞輸入：每一種都要 400，不猜
  const bads = [
    { ...ok1, ver: 1 }, { ...ok1, enabled: 'yes' }, { ...ok1, rules: {} }, { enabled: true },
    { ...ok1, rules: [] },                                                         // 開著卻沒規則
    { ...ok1, rules: [{ ...r1, days: [8] }] }, { ...ok1, rules: [{ ...r1, days: [0] }] }, { ...ok1, rules: [{ ...r1, days: [1.5] }] }, { ...ok1, rules: [{ ...r1, days: [] }] },
    { ...ok1, rules: [{ ...r1, dates: ['2026-10-20'] }] },                         // days 與 dates 同時給
    { ...ok1, rules: [{ hours: [10], cats: { news: 1 } }] },                       // 兩個都沒給
    { ...ok1, rules: [{ ...r2, dates: ['2026-02-30'] }] }, { ...ok1, rules: [{ ...r2, dates: ['2026/10/20'] }] }, { ...ok1, rules: [{ ...r2, dates: [20261020] }] }, { ...ok1, rules: [{ ...r2, dates: [] }] },
    { ...ok1, rules: [{ ...r1, hours: [] }] }, { ...ok1, rules: [{ ...r1, hours: [24] }] }, { ...ok1, rules: [{ ...r1, hours: ['10'] }] }, { ...ok1, rules: [{ ...r1, hours: [-1] }] },
    { ...ok1, rules: [{ ...r1, cats: { news: 0, intro: 0, know: 0 } }] }, { ...ok1, rules: [{ ...r1, cats: { news: 4 } }] }, { ...ok1, rules: [{ ...r1, cats: { video: 1 } }] }, { ...ok1, rules: [{ ...r1, cats: { news: 1.5 } }] },
    { ...ok1, rules: [{ ...r1, extra: 1 }] }, { ...ok1, rules: [null] },
    { ...ok1, rules: Array.from({ length: 21 }, () => r1) },                       // 超過 20 條
  ];
  for (const bad of bads) assert.equal((await pj(hub, '/v1/articles/schedule/add', { t: andy, ...bad })).s, 400, JSON.stringify(bad));
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_schedule')[0].c, 0, '壞輸入一筆都沒寫進去');
  const a = await pj(hub, '/v1/articles/schedule/add', { t: andy, ...ok1 });
  assert.equal(a.s, 200);
  assert.equal(a.j.schedule.ver, 2); assert.equal(a.j.schedule.enabled, true);
  assert.deepEqual(a.j.schedule.rules, [
    { days: [1, 3, 5], hours: [10, 14], cats: { news: 1, intro: 0, know: 0 } },
    { dates: ['2026-10-18', '2026-10-20'], hours: [21], cats: { news: 0, intro: 2, know: 1 } }], '排序、去重、補 0');
  assert.equal(typeof a.j.schedule.updated, 'number');
  // 剛好 20 條可以存
  assert.equal((await pj(hub, '/v1/articles/schedule/add', { t: andy, ver: 2, enabled: true, rules: Array.from({ length: 20 }, () => r1) })).s, 200);
  // 關閉時可以沒有規則；ver 省略也收（當第 2 版）
  const off = await pj(hub, '/v1/articles/schedule/add', { t: andy, enabled: false, rules: [] });
  assert.equal(off.s, 200); assert.equal(off.j.schedule.enabled, false); assert.deepEqual(off.j.schedule.rules, []);
  assert.equal((await pj(hub, '/v1/articles/schedule/get', { t: andy })).j.schedule.enabled, false, '讀到的是最新一份');
  // 機器路由
  assert.equal((await bot(hub, { op: 'schedule' }, 'wrong-token-wrong-token-wrong')).s, 403);
  assert.equal((await bot(hub, { op: 'schedule' })).j.schedule.enabled, false);
  await pj(hub, '/v1/articles/schedule/add', { t: andy, ...ok1 });
  assert.deepEqual((await bot(hub, { op: 'schedule' })).j.schedule.rules[0].hours, [10, 14]);
  // 只留最近 50 份
  for (let i = 0; i < 55; i++) await pj(hub, '/v1/articles/schedule/add', { t: andy, ...ok1 });
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_schedule')[0].c, 50);
});

test('產文章頻率設定：讀到第 1 版（slots／cats）轉成第 2 版回去，畫面不會壞', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  const andy = await login(hub, 'andy@example.com');
  await pj(hub, '/v1/articles/schedule/get', { t: andy });   // 建表
  const put = (cfg) => hub.q('INSERT INTO article_schedule (cfg, created, by) VALUES (?, ?, ?)', JSON.stringify(cfg), clock, 'u');
  put({ enabled: true, slots: { 1: ['09:50', '20:50'], 3: ['09:50', '20:50'], 5: ['14:50'] }, cats: { news: 2, intro: 0, know: 1 } });
  const g = (await pj(hub, '/v1/articles/schedule/get', { t: andy })).j.schedule;
  assert.equal(g.ver, 2); assert.equal(g.enabled, true); assert.equal(g.legacy, true);
  assert.deepEqual(g.rules, [
    { days: [1, 3], hours: [9, 20], cats: { news: 2, intro: 0, know: 1 } },
    { days: [5], hours: [14], cats: { news: 2, intro: 0, know: 1 } }], '同一組時段的星期併成一條；09:50→9、14:50→14、20:50→20');
  assert.deepEqual((await bot(hub, { op: 'schedule' })).j.schedule.rules, g.rules, '機器路由一樣拿到新格式');
  // 舊版開著但篇數全 0 → 沒有規則就是關閉（不能「開著卻什麼都不做」）
  put({ enabled: true, slots: { 1: ['09:50'] }, cats: { news: 0, intro: 0, know: 0 } });
  const g2 = (await pj(hub, '/v1/articles/schedule/get', { t: andy })).j.schedule;
  assert.equal(g2.enabled, false); assert.deepEqual(g2.rules, []);
  // 舊版壞掉的值（星期 9、時間亂寫）被略過，不讓整份壞掉
  put({ enabled: false, slots: { 9: ['09:50'], 2: ['xx', '14:50'] }, cats: { news: 1 } });
  assert.deepEqual((await pj(hub, '/v1/articles/schedule/get', { t: andy })).j.schedule.rules, [{ days: [2], hours: [14], cats: { news: 1, intro: 0, know: 0 } }]);
});

test('頻率設定到點排隊（機器路由 op=add）：只收 sch- id、同一個 id 不論狀態都不重排、要鑰匙', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  const andy = await login(hub, 'andy@example.com');
  const job = { op: 'add', topic_id: 'sch-20261020-14-r1-news-1', kind: 'article', title: '排程：比比快訊', note: '建議主題 n_x' };
  assert.equal((await bot(hub, job, 'wrong-token-wrong-token-wrong')).s, 403);
  for (const bad of [{ ...job, topic_id: 'n_x' }, { ...job, topic_id: 'sch-2026102-14-r1-news-1' }, { ...job, topic_id: 'sch-20261020-14-r1-video-1' }, { ...job, kind: 'video' }, { ...job, title: '' }]) {
    assert.equal((await bot(hub, bad)).s, 400, JSON.stringify(bad));
  }
  const a = await bot(hub, job);
  assert.equal(a.s, 200); assert.equal(a.j.job.status, 'queued'); assert.equal(a.j.job.topic_id, job.topic_id);
  assert.equal((await bot(hub, job)).j.dup, true, '同一個 id 再排＝dup');
  // 取消之後也不會被補回來
  assert.equal((await pj(hub, '/v1/articles/jobs/cancel', { t: andy, id: a.j.job.id })).s, 200);
  const again = await bot(hub, job);
  assert.equal(again.j.dup, true); assert.equal(again.j.job.status, 'cancelled');
  assert.equal(hub.q('SELECT COUNT(*) AS c FROM article_jobs')[0].c, 1);
  // 管理區的清單看得到（排程排進來的跟手動排的一樣顯示）
  assert.equal((await pj(hub, '/v1/articles/jobs/list', { t: andy })).j.jobs[0].topic_id, job.topic_id);
});

/* 產出進度的「階段」（2026-10-17）：Andy 10-17「這邊一直顯示排隊中，但我不清楚他狀況如何，所以多一個進度條，並且備註目前的階段」。
   白名單外忽略；working 沒給階段→plan、已在 working 就保留；done／cancelled 跟著變；failed 停在原本那格；stage_at 只在階段變了才更新；舊表相容遷移 */
test('產出佇列階段：白名單、預設 plan、done／cancelled 跟著、failed 停在原格、stage_at、舊表遷移', async () => {
  const { hub, db } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  // 舊資料庫：先建沒有 stage 欄的表與一筆舊列，再讓 Worker 第一次進 artInit
  db.exec("CREATE TABLE article_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id TEXT, kind TEXT, title TEXT, note TEXT, status TEXT, created INTEGER, updated INTEGER, by TEXT, result TEXT)");
  db.exec("INSERT INTO article_jobs (topic_id, kind, title, status, created, updated) VALUES ('old-one', 'article', '舊列', 'queued', 1, 1)");
  const andy = await login(hub, 'andy@example.com');
  const old = (await pj(hub, '/v1/articles/jobs/list', { t: andy })).j.jobs[0];
  assert.equal(old.title, '舊列'); assert.equal(old.stage, null, '舊列 stage 為空'); assert.equal(old.stage_at, null);
  const a = (await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'stage-a', kind: 'article', title: '階段測試' })).j.job;
  assert.equal(a.stage, null, '剛排的還沒有階段（前端當排隊中）');
  const t0 = clock;
  let m = await bot(hub, { op: 'mark', id: a.id, status: 'working' });
  assert.equal(m.j.job.stage, 'plan', 'working 沒給階段→plan'); assert.equal(m.j.job.stage_at, t0);
  clock += 60000;
  m = await bot(hub, { op: 'mark', id: a.id, status: 'working', stage: 'write' });
  assert.equal(m.j.job.stage, 'write'); assert.equal(m.j.job.stage_at, t0 + 60000);
  clock += 60000;
  m = await bot(hub, { op: 'mark', id: a.id, status: 'working', stage: '87%' });
  assert.equal(m.s, 200, '白名單外不報錯'); assert.equal(m.j.job.stage, 'write', '白名單外忽略、保留原格');
  assert.equal(m.j.job.stage_at, t0 + 60000, '階段沒變 stage_at 不動');
  m = await bot(hub, { op: 'mark', id: a.id, status: 'working', stage: 'done' });
  assert.equal(m.j.job.stage, 'write', 'working 時不能把階段塞成 done');
  m = await bot(hub, { op: 'mark', id: a.id, status: 'failed', result: '插圖失敗' });
  assert.equal(m.j.job.status, 'failed'); assert.equal(m.j.job.stage, 'write', 'failed 停在失敗前那一格');
  m = await bot(hub, { op: 'mark', id: a.id, status: 'working' });
  assert.equal(m.j.job.stage, 'plan', 'failed 重新開工沒給階段→plan');
  await bot(hub, { op: 'mark', id: a.id, status: 'working', stage: 'publish' });
  m = await bot(hub, { op: 'mark', id: a.id, status: 'done', result: '2026-10-17-news-x' });
  assert.equal(m.j.job.stage, 'done', 'done 時階段跟著');
  const o = (await bot(hub, { op: 'open' })).j.jobs.find((j) => j.title === '舊列');
  assert.ok(o && 'stage' in o && 'stage_at' in o, 'open 也帶 stage／stage_at');
  const c = (await pj(hub, '/v1/articles/jobs/cancel', { t: andy, id: old.id })).j.job;
  assert.equal(c.status, 'cancelled'); assert.equal(c.stage, 'cancelled', '取消時階段跟著');
  // 重跑 artInit（冷啟動）不報錯
  hub._artJobOk = false; assert.equal((await pj(hub, '/v1/articles/jobs/list', { t: andy })).s, 200);
});

/* 立即開工（2026-10-17）：有 ROUTINE_FIRE_TOKEN 時送出請求就叫醒 Claude 排程；2 分鐘內不重叫；沒鑰匙不叫；kick 只在有排隊中時叫 */
test('立即開工：送出就叫醒排程、2 分鐘防連打、沒鑰匙不叫、kick 空佇列不叫', async () => {
  const fires = [];
  const orig = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    if (String(url).startsWith('https://api.anthropic.com/v1/claude_code/routines/')) { fires.push({ url: String(url), h: init.headers, body: JSON.parse(init.body) }); return Response.json({ type: 'routine_fire', claude_code_session_url: 'x' }); }
    return orig(url, init);
  };
  try {
    const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, ROUTINE_FIRE_TOKEN: 'test-fire-token-0000000000' });
    const andy = await login(hub, 'andy@example.com');
    const a = await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'fire-1', kind: 'article', title: '測試一' });
    assert.equal(a.j.fired, true);
    assert.equal(fires.length, 1);
    assert.match(fires[0].url, /routines\/trig_01JSw5RrpyD94edAaUY69HMo\/fire$/);
    assert.equal(fires[0].h.Authorization, 'Bearer test-fire-token-0000000000');
    assert.equal(fires[0].h['anthropic-beta'], 'experimental-cc-routine-2026-04-01');
    const b = await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'fire-2', kind: 'article', title: '測試二' });
    assert.equal(b.j.fired, true, '剛叫過：那一輪會處理到');
    assert.equal(fires.length, 1, '2 分鐘內不重叫');
    clock += 3 * 60 * 1000;
    const k = await pj(hub, '/v1/articles/jobs/kick', { t: andy });
    assert.equal(k.j.fired, true); assert.equal(fires.length, 2);
    const { hub: h2 } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID });
    const andy2 = await login(h2, 'andy@example.com');
    const c = await pj(h2, '/v1/articles/jobs/add', { t: andy2, topic_id: 'fire-3', kind: 'article', title: '測試三' });
    assert.equal(c.j.fired, false); assert.equal(fires.length, 2, '沒鑰匙不叫');
    const { hub: h3 } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, ROUTINE_FIRE_TOKEN: 'test-fire-token-0000000000' });
    const andy3 = await login(h3, 'andy@example.com');
    const e = await pj(h3, '/v1/articles/jobs/kick', { t: andy3 });
    assert.equal(e.j.fired, false); assert.equal(e.j.reason, 'empty'); assert.equal(fires.length, 2, '空佇列不叫');
  } finally { globalThis.fetch = orig; }
});

/* 2026-10-17 新增主題請求（kind:'topics'）：Andy 10-17「多新增一個新增主題 Btn……可以單選和多選分類，也可以我提供關鍵字你幫我生成主題」。
   只收 gen-<時間戳> 的 id 與 cats=…;n=…[;kw=…] 的結構化 note；壞值一律 400；同 id 未完成不重排；機器路由讀得到、標得了 done。 */
test('新增主題請求：結構化 note 才收、壞值擋、重複不排、機器路由讀得到並可標完成', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID, BACKUP_TOKEN: BT });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  const ok1 = { t: andy, topic_id: 'gen-1792130000000', kind: 'topics', title: '新增主題：快訊、知識（各 3 個）', note: 'cats=news,know;n=3;kw=CoWoS 產能' };
  assert.equal((await pj(hub, '/v1/articles/jobs/add', { ...ok1, t: bob })).s, 403, '非管理者不能排');
  const bads = [
    { topic_id: 'c-news-abc' }, { topic_id: 'gen-12' }, { topic_id: 'gen-abc1234567890' },
    { note: '' }, { note: 'cats=;n=3' }, { note: 'cats=news;n=0' }, { note: 'cats=news;n=6' }, { note: 'cats=video;n=3' },
    { note: 'cats=news,news;n=3' }, { note: 'cats=news,intro,know,news;n=3' }, { note: 'cats=news;n=3;kw=' },
    { note: 'cats=news;n=3;kw=a;b' }, { note: 'cats=news;n=3;kw=x=y' }, { note: 'cats=news;n=3;kw=<script>' },
    { note: 'cats=news;n=3;kw=' + '字'.repeat(41) }, { note: 'n=3;cats=news' }, { title: '' },
  ];
  for (const bad of bads) assert.equal((await pj(hub, '/v1/articles/jobs/add', { ...ok1, ...bad })).s, 400, '應擋：' + JSON.stringify(bad));
  const a = await pj(hub, '/v1/articles/jobs/add', ok1);
  assert.equal(a.s, 200); assert.equal(a.j.job.kind, 'topics'); assert.equal(a.j.job.note, 'cats=news,know;n=3;kw=CoWoS 產能'); assert.equal(a.j.job.status, 'queued');
  // 單選、沒有關鍵字、三類全選也都收
  for (const [id, note] of [['gen-1792130000001', 'cats=intro;n=1'], ['gen-1792130000002', 'cats=news,intro,know;n=5']]) {
    assert.equal((await pj(hub, '/v1/articles/jobs/add', { ...ok1, topic_id: id, note })).s, 200, note);
  }
  assert.equal((await pj(hub, '/v1/articles/jobs/add', ok1)).j.dup, true, '同 id 未完成不重排');
  const open = (await bot(hub, { op: 'open' })).j.jobs;
  assert.deepEqual(open.map((j) => j.kind), ['topics', 'topics', 'topics']);
  const done = await bot(hub, { op: 'mark', id: a.j.job.id, status: 'done', result: 'topics+6' });
  assert.equal(done.j.job.status, 'done'); assert.equal(done.j.job.stage, 'done');
  // 文章請求照舊
  assert.equal((await pj(hub, '/v1/articles/jobs/add', { t: andy, topic_id: 'tsmc-q3', kind: 'article', title: '台積電法說會' })).s, 200);
});

/* 精選文章隱藏分頁（2026-10-27）：公開可讀、只有管理者能寫、壞輸入擋、去重 */
test('隱藏分頁：預設空；管理者可寫；訪客讀得到；非管理者與壞輸入被擋', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  assert.deepEqual((await pj(hub, '/v1/articles/tabs', {})).j.hidden, []);
  assert.equal((await pj(hub, '/v1/articles/tabs/put', { hidden: ['premarket'] })).s, 403, '沒登入不能寫');
  assert.equal((await pj(hub, '/v1/articles/tabs/put', { t: bob, hidden: ['premarket'] })).s, 403, '一般會員不能寫');
  assert.deepEqual((await pj(hub, '/v1/articles/tabs', {})).j.hidden, [], '被擋就不會寫入');
  assert.equal((await pj(hub, '/v1/articles/tabs/put', { t: andy, hidden: 'premarket' })).s, 400);
  assert.equal((await pj(hub, '/v1/articles/tabs/put', { t: andy, hidden: ['<b>'] })).s, 400);
  assert.equal((await pj(hub, '/v1/articles/tabs/put', { t: andy, hidden: Array(13).fill('news') })).s, 400);
  const r = await pj(hub, '/v1/articles/tabs/put', { t: andy, hidden: ['premarket', 'postmarket', 'premarket'] });
  assert.equal(r.s, 200); assert.deepEqual(r.j.hidden, ['premarket', 'postmarket'], '重複的收成一個');
  assert.deepEqual((await pj(hub, '/v1/articles/tabs', {})).j.hidden, ['premarket', 'postmarket'], '訪客讀得到');
  assert.deepEqual((await pj(hub, '/v1/articles/tabs/put', { t: andy, hidden: [] })).j.hidden, [], '全部顯示');
});

/* 科技透明圈人工刪除清單（2026-10-28）：只有管理者能讀寫、壞輸入擋、去重、整份取代 */
test('科技透明圈刪除清單：管理者讀寫；訪客與一般會員 403；壞輸入 400；去重', async () => {
  const { hub } = makeHub({ ...env, GOOGLE_CLIENT_ID: CID });
  const andy = await login(hub, 'andy@example.com'), bob = await login(hub, 'bob@example.com');
  assert.equal((await pj(hub, '/v1/tc/hidden', {})).s, 403, '沒登入不能讀');
  assert.equal((await pj(hub, '/v1/tc/hidden', { t: bob })).s, 403, '一般會員不能讀');
  assert.deepEqual((await pj(hub, '/v1/tc/hidden', { t: andy })).j.hidden, [], '預設空');
  assert.equal((await pj(hub, '/v1/tc/hidden/put', { t: bob, hidden: ['c|icdesign|Meta'] })).s, 403);
  assert.equal((await pj(hub, '/v1/tc/hidden/put', { t: andy, hidden: 'x' })).s, 400);
  assert.equal((await pj(hub, '/v1/tc/hidden/put', { t: andy, hidden: [''] })).s, 400);
  assert.equal((await pj(hub, '/v1/tc/hidden/put', { t: andy, hidden: ['a'.repeat(301)] })).s, 400);
  const r = await pj(hub, '/v1/tc/hidden/put', { t: andy, hidden: ['c|icdesign|Meta', 's|icdesign|Meta|u|r|abc', 'c|icdesign|Meta'] });
  assert.equal(r.s, 200); assert.deepEqual(r.j.hidden, ['c|icdesign|Meta', 's|icdesign|Meta|u|r|abc']);
  assert.deepEqual((await pj(hub, '/v1/tc/hidden', { t: andy })).j.hidden, r.j.hidden, '讀得回來');
  assert.deepEqual((await pj(hub, '/v1/tc/hidden/put', { t: andy, hidden: [] })).j.hidden, [], '復原到空');
});
