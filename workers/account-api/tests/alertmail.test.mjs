/* 自設提醒條數與 email 通知（2026-11-02，alertmail.js）account-api 端驗收。跑法：node --test workers/account-api/tests/alertmail.test.mjs */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { makeHub } from "../harness.mjs";
import { evalAlert, alertRuleText, alertStep, ALERT_MAIL_DAILY_MAX } from "../alertmail.js";

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const pending = {};
globalThis.fetch = async (url, init) => {
  if (String(url).startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body);
    const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  if (String(url).startsWith('https://liguligu-puipui.com/data/digest.json')) return Response.json(DIGEST);
  throw new Error('測試不准連外網：' + url);
};
let DIGEST = null;
const DAY = 86400000;
let clock = Date.parse('2026-10-05T04:00:00Z');
const env = () => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock });
const post = (hub, path, body) => hub.fetch(new Request(API + path, { method: 'POST', headers: { Origin: ORIGIN, 'content-type': 'text/plain' }, body: JSON.stringify(body) }));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const rand = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email) {
  const n = rand();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rand();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}

const ASOF = '2026-11-02';
const mkDigest = (asof, over = {}) => ({ asof, s: {
  '2330': { n: '台積電', c: 1000, pc: 990, v: 30000, i: [500, 20, 0, 520], k: [4, 1, 3], r: { ym: '2026-10', rev: 3000.5, yoy: 20.1, mom: 5.2, ann: '2026-11-01' }, x: { d: '2026-11-10', a: 4.5 }, e: [] },
  '2317': { n: '鴻海', c: 200, pc: 205, v: 20000, i: [-300, -10, 0, -310], k: [-5, 0, -4], r: null, x: null, e: [] }, ...over } });
const at = async (hub, t, id) => (await pj(hub, '/v1/alerts/get', { t })).j;
const rows = (db, sql, ...a) => db.prepare(sql).all(...a);

test('條數：註冊 1、體驗期內 5、Plus 5、Pro 20、第 21 條 403；管理者 200', async () => {
  clock = Date.parse('2026-11-02T04:00:00Z');
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const andy = await login(hub, 'andy@example.com');
  const mk = (n) => Array.from({ length: n }, (_, i) => ({ id: 'a' + i, code: String(2330 + i), type: 'above', x: 100 + i }));
  const put = (t, alerts, rev) => pj(hub, '/v1/alerts/put', { t, alerts, rev });
  const free = await login(hub, 'free@example.com');
  assert.equal((await at(hub, free)).cap, 1, '沒有體驗＝1 條');
  /* 打開新會員體驗後註冊的人：體驗期內 5 條 */
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: { 'ind.3d': 5 }, per: 'day', days: 14, on: true });
  const tri = await login(hub, 'tri@example.com');
  assert.equal((await at(hub, tri)).cap, 5, '體驗期內 5');
  assert.equal((await put(tri, mk(5), 0)).s, 200);
  assert.equal((await put(tri, mk(6), 1)).j.limit, 5);
  clock += 15 * DAY;                       // 體驗到期 → 回 1 條（原本的 5 條還在，只是不能再加）
  assert.equal((await at(hub, tri)).cap, 1);
  clock -= 15 * DAY;
  /* Plus 5、Pro 20（體驗期外的人：關掉 welcome 再註冊）*/
  await pj(hub, '/v1/admin/grants/defs/put', { t: andy, id: 'welcome', kind: 'welcome', name: '新會員體驗', feats: { 'ind.3d': 5 }, per: 'day', days: 14, on: false });
  const plus = await login(hub, 'plus@example.com'), pro = await login(hub, 'pro@example.com');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'plus@example.com', plan: 'plus', over: {} });
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'pro@example.com', plan: 'pro', over: {} });
  assert.equal((await put(plus, mk(5), 0)).s, 200); assert.equal((await put(plus, mk(6), 1)).s, 403);
  assert.equal((await put(pro, mk(20), 0)).s, 200);
  const r = await put(pro, mk(21), 1);
  assert.equal(r.s, 403); assert.equal(r.j.limit, 20);
  assert.equal((await at(hub, andy)).cap, 200);
});

test('nt 通知方式：存後端、跨裝置讀得回；只收 w／m 兩個布林；沒帶就不存', async () => {
  clock = Date.parse('2026-11-02T04:00:00Z');
  const { hub } = makeHub({ ...env(), SEED_PLANS: 'plus,pro' });
  const u = await login(hub, 'u@example.com');
  const rules = [{ id: 'a1', code: '2330', type: 'above', x: 900, nt: { w: false, m: true, evil: '<script>' } }, { id: 'a2', code: '2317', type: 'below', x: 100, nt: { m: 1 } }, { id: 'a3', code: '2330', type: 'rev' }];
  const r = await pj(hub, '/v1/alerts/put', { t: u, alerts: rules.slice(0, 1), rev: 0 });
  assert.equal(r.s, 200);
  assert.deepEqual(r.j.alerts[0].nt, { w: false, m: true }, '多帶的欄位被丟掉');
  const g = await at(hub, u);
  assert.deepEqual(g.alerts[0].nt, { w: false, m: true });
  const u2 = await login(hub, 'u2@example.com');
  await pj(hub, '/v1/alerts/put', { t: u2, alerts: [rules[1]], rev: 0 });
  assert.deepEqual((await at(hub, u2)).alerts[0].nt, { w: true, m: true }, 'w 沒帶＝預設開');
  const u3 = await login(hub, 'u3@example.com');
  await pj(hub, '/v1/alerts/put', { t: u3, alerts: [rules[2]], rev: 0 });
  assert.equal((await at(hub, u3)).alerts[0].nt, undefined, '沒帶 nt 就不存（前端當預設：網頁開、email 關）');
});

test('比對邏輯與 site/digest.js 一致（把前端原始碼切出來跑，逐案比對文字、met、key）', () => {
  const src = readFileSync(fileURLToPath(new URL('../../../site/digest.js', import.meta.url)), 'utf8');
  const a = src.indexOf('const num = '), b = src.indexOf('const P = () =>'), c = src.indexOf('const dayStart'), d = src.indexOf('/* 載入資料與條件後跑一次');
  assert.ok(a > 0 && b > a && c > b && d > c, '找得到 digest.js 的函式區段');
  const code = src.slice(a, b) + src.slice(src.indexOf('function ruleText'), d);
  const fe = new Function('S', code + '; return { evalRule, ruleText };');
  const D = mkDigest(ASOF);
  const S = { d: D };
  const { evalRule, ruleText } = fe(S);
  const rules = [
    { type: 'rev', code: '2330' }, { type: 'rev', code: '2317' }, { type: 'rev', code: '9999' },
    { type: 'above', code: '2330', x: 900 }, { type: 'above', code: '2330', x: 1100 }, { type: 'below', code: '2317', x: 250 }, { type: 'below', code: '2317', x: 150 },
    { type: 'streak', code: '2330', side: 'buy', who: 'foreign', n: 3 }, { type: 'streak', code: '2330', side: 'buy', who: 'trust', n: 3 }, { type: 'streak', code: '2317', side: 'sell', who: 'total', n: 4 },
    { type: 'streak', code: '2317', side: 'sell', who: 'foreign', n: 6 }, { type: 'exdiv', code: '2330', n: 10 }, { type: 'exdiv', code: '2330', n: 3 }, { type: 'exdiv', code: '2317', n: 5 },
  ];
  for (const r of rules) {
    r.id = 'x';
    assert.deepEqual(evalAlert(ASOF, r, D.s[r.code]), evalRule(r, D.s[r.code]), JSON.stringify(r));
    assert.equal(alertRuleText(r), ruleText(r));
  }
  /* 邊緣觸發規則也對一下：前端 run() 的三種分支 */
  assert.deepEqual(alertStep(undefined, { type: 'above' }, { met: true }), { send: true, st: { met: true } }, '新建且當下成立→響一次');
  assert.equal(alertStep({ met: true }, { type: 'above' }, { met: true }).send, false, '仍成立→不再響');
  assert.equal(alertStep({ met: false }, { type: 'above' }, { met: true }).send, true, '不成立→成立');
  assert.equal(alertStep(undefined, { type: 'rev' }, { met: true, key: '2026-10' }).send, false, '營收新建先記下現有那一期');
  assert.equal(alertStep({ key: '2026-10' }, { type: 'rev' }, { met: true, key: '2026-11' }).send, true, '營收新的一期');
  assert.equal(alertStep({ key: '2026-11-10' }, { type: 'exdiv' }, { met: true, key: '2026-11-10' }).send, false, '同一個除息日只響一次');
});

async function mailSetup(extraEnv = {}) {
  clock = Date.parse('2026-11-02T10:40:00Z');
  const h = makeHub({ ...env(), SEED_PLANS: 'plus,pro', ...extraEnv });
  const andy = await login(h.hub, 'andy@example.com');
  return { ...h, andy };
}
const cron = (hub) => hub.fetch(new Request('https://internal.cron/cron/alert-mail', { method: 'POST' })).then((r) => r.json());

test('cron：邊緣觸發才寫入寄信佇列；同一資料日不重跑；恢復後再成立再寄；沒金鑰不報錯', async () => {
  const { hub, db, andy } = await mailSetup();      // 沒設 RESEND_API_KEY／MAIL_FROM
  const u = await login(hub, 'u@example.com');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'u@example.com', plan: 'pro', over: {} });
  const rules = [{ id: 'p1', code: '2330', type: 'above', x: 900, nt: { w: true, m: true } },      // 成立，要寄
    { id: 'p2', code: '2330', type: 'above', x: 900, nt: { w: true, m: false } },                  // 沒開 email → 不寄
    { id: 'p3', code: '2317', type: 'below', x: 150, nt: { m: true } },                             // 不成立
    { id: 'p4', code: '2330', type: 'rev', nt: { m: true } },                                       // 營收新建：先記、不寄
    { id: 'p5', code: '2330', type: 'above', x: 900, on: false, nt: { m: true } }];                 // 關掉的條件不寄
  assert.equal((await pj(hub, '/v1/alerts/put', { t: u, alerts: rules, rev: 0 })).s, 200);
  DIGEST = mkDigest('2026-11-02');
  let r = await cron(hub);
  assert.equal(r.queued, 1, JSON.stringify(r));
  let mail = rows(db, 'SELECT * FROM mail_out');
  assert.equal(mail.length, 1); assert.equal(mail[0].email, 'u@example.com'); assert.equal(mail[0].status, 'pending');
  assert.match(mail[0].subject, /台積電 收盤價高於 900\.00 元/);
  assert.match(mail[0].body, /你設定的條件成立：台積電（2330）收盤價 1,000\.00 元，高於你設定的 900\.00 元/);
  assert.match(mail[0].body, /資料日期：2026-11-02/); assert.match(mail[0].body, /非投資建議/); assert.match(mail[0].body, /#watch/);
  assert.ok(!/買進|賣出|建議買|評分/.test(mail[0].body.replace('非投資建議', '')), '不含買賣建議');
  /* 同一資料日再跑：直接跳過 */
  assert.equal((await cron(hub)).skipped, 'same_asof');
  /* 隔天仍成立：不再寄（邊緣觸發）*/
  DIGEST = mkDigest('2026-11-03');
  assert.equal((await cron(hub)).queued, 0);
  /* 價格跌破又漲回：再寄一次 */
  DIGEST = mkDigest('2026-11-04', { '2330': { ...mkDigest('x').s['2330'], c: 800 } });
  assert.equal((await cron(hub)).queued, 0);
  DIGEST = mkDigest('2026-11-05');
  assert.equal((await cron(hub)).queued, 1);
  assert.equal(rows(db, 'SELECT * FROM mail_out').length, 2);
  /* 營收新的一期 → 寄 */
  DIGEST = mkDigest('2026-11-06', { '2330': { ...mkDigest('x').s['2330'], r: { ym: '2026-11', rev: 3100, yoy: 1, mom: 2, ann: '2026-11-06' } } });
  assert.equal((await cron(hub)).queued, 1);
  /* 抓不到 digest：不報錯 */
  DIGEST = null;
  assert.equal((await cron(hub)).skipped, 'no_digest');
});

test('每人每天最多 5 封；超過的條件不更新狀態，下個資料日補寄', async () => {
  const { hub, db, andy } = await mailSetup();
  const u = await login(hub, 'u@example.com');
  await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'u@example.com', plan: 'pro', over: {} });
  const rules = Array.from({ length: 7 }, (_, i) => ({ id: 'q' + i, code: '2330', type: 'above', x: 100 + i, nt: { m: true } }));
  await pj(hub, '/v1/alerts/put', { t: u, alerts: rules, rev: 0 });
  DIGEST = mkDigest('2026-11-02');
  let r = await cron(hub);
  assert.deepEqual([r.queued, r.dropped], [ALERT_MAIL_DAILY_MAX, 2]);
  assert.equal(rows(db, 'SELECT * FROM mail_out').length, 5);
  clock += DAY;                                  // 隔天：沒寄出的 2 條（狀態沒更新）補寄，已寄的 5 條不重寄
  DIGEST = mkDigest('2026-11-03');
  r = await cron(hub);
  assert.deepEqual([r.queued, r.dropped], [2, 0]);
  assert.equal(rows(db, 'SELECT * FROM mail_out').length, 7);
});

test('有設 RESEND 金鑰時由既有佇列送出；沒設時 payMailFlush 回 0 不報錯', async () => {
  const sent = [];
  const prev = globalThis.fetch;
  globalThis.fetch = async (url, init) => { if (String(url) === 'https://api.resend.com/emails') { sent.push(JSON.parse(init.body)); return Response.json({ id: 'x' }); } return prev(url, init); };
  try {
    const { hub, andy } = await mailSetup({ RESEND_API_KEY: 'k', MAIL_FROM: 'a <a@example.com>' });
    const u = await login(hub, 'u@example.com');
    await pj(hub, '/v1/admin/perm/put', { t: andy, email: 'u@example.com', plan: 'plus', over: {} });
    await pj(hub, '/v1/alerts/put', { t: u, alerts: [{ id: 'p1', code: '2330', type: 'above', x: 900, nt: { m: true } }], rev: 0 });
    DIGEST = mkDigest('2026-11-02');
    await cron(hub);
    assert.equal(await hub.payMailFlush(), 1);
    assert.equal(sent.length, 1); assert.deepEqual(sent[0].to, ['u@example.com']);
    const { hub: h2, andy: a2 } = await mailSetup();
    assert.equal(await h2.payMailFlush(), 0);
  } finally { globalThis.fetch = prev; }
});
