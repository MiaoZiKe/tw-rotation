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
