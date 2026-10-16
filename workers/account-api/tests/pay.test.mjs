/* 金流訂單 pay-1011 的驗收（docs/payment_checkout_1011.md）。
 *
 * 跑法：node --test workers/account-api/tests/pay.test.mjs
 * 綠界是假的：攔 globalThis.fetch，payment-stage／payment 網域的查單、定期定額查詢／終止、退刷都由下面的 FAKE 回（回應一樣帶 CheckMacValue）。
 * Andy 10-11「千萬不要發生付款後還沒開放…一定要仔細確認」→ 開通的每一層保險各有一條測試（名稱開頭標 B1～B7）。
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHub } from '../harness.mjs';
import { ecpayMac, ECPAY_STAGE } from '../pay.js';

const ORIGIN = 'https://miaozike.github.io';
const API = 'https://tw-account.example.workers.dev';
const CID = 'test-client.apps.googleusercontent.com';
const BACK = ORIGIN + '/tw-rotation/';
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const pending = {};
const DAY = 86400000;
/* 假綠界：trades[單號] = { status:'0'|'1', amt, type }；periods[單號] = { n, amt, exec:'1' }；doaction 下一次回什麼 */
const FAKE = { trades: {}, periods: {}, calls: [], doaction: { RtnCode: '1', RtnMsg: '成功' }, cancel: { RtnCode: '1', RtnMsg: '成功' }, key: ECPAY_STAGE };
const signed = async (p) => { const o = { MerchantID: FAKE.key.id, ...p }; o.CheckMacValue = await ecpayMac(o, FAKE.key.key, FAKE.key.iv); return new URLSearchParams(o).toString(); };
globalThis.fetch = async (url, init) => {
  const u = String(url);
  if (u.startsWith('https://oauth2.googleapis.com/token')) {
    const p = new URLSearchParams(init.body);
    const hit = pending[p.get('code')];
    if (!hit) return new Response('{"error":"invalid_grant"}', { status: 400 });
    return Response.json({ id_token: 'x.' + b64u(hit.claims) + '.sig', access_token: 'at' });
  }
  if (/^https:\/\/payment(-stage)?\.ecpay\.com\.tw\//.test(u)) {
    const f = Object.fromEntries(new URLSearchParams(init.body));
    const path = new URL(u).pathname;
    FAKE.calls.push({ path, f });
    const mac = await ecpayMac(f, FAKE.key.key, FAKE.key.iv);
    if (mac !== f.CheckMacValue) return new Response('CheckMacValue Error', { status: 400 });
    if (path === '/Cashier/QueryTradeInfo/V5') {
      const t = FAKE.trades[f.MerchantTradeNo] || { status: '0', amt: 0 };
      return new Response(await signed({ MerchantTradeNo: f.MerchantTradeNo, TradeNo: 'T' + f.MerchantTradeNo, TradeAmt: String(t.amt), TradeStatus: t.status, PaymentDate: t.status === '1' ? '2026/10/11 12:00:00' : '', PaymentType: t.type || 'Credit_CreditCard' }));
    }
    if (path === '/Cashier/QueryCreditCardPeriodInfo') {
      const p = FAKE.periods[f.MerchantTradeNo] || { n: 0, amt: 0, exec: '1' };
      return Response.json({ MerchantID: FAKE.key.id, MerchantTradeNo: f.MerchantTradeNo, RtnCode: 1, PeriodType: 'M', Frequency: 1, ExecTimes: 99, PeriodAmount: p.amt, amount: p.amt, gwsr: 11111, process_date: '2026/10/11 12:00:00', TotalSuccessTimes: p.n, ExecStatus: p.exec });
    }
    if (path === '/Cashier/CreditCardPeriodAction') return new Response(await signed({ MerchantTradeNo: f.MerchantTradeNo, ...FAKE.cancel }));
    if (path === '/CreditDetail/DoAction') return new Response(await signed({ MerchantTradeNo: f.MerchantTradeNo, TradeNo: f.TradeNo, ...FAKE.doaction }));
    return new Response('not found', { status: 404 });
  }
  throw new Error('測試不准連外網：' + url);
};
let clock = Date.parse('2026-10-11T04:00:00Z');
const env = (x = {}) => ({ ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 's', ADMIN_EMAILS: 'andy@example.com', __now: () => clock, ...x });
const post = (hub, path, body, origin = ORIGIN) => hub.fetch(new Request(API + path, {
  method: 'POST', headers: origin ? { Origin: origin, 'content-type': 'text/plain' } : { 'content-type': 'text/plain' }, body: JSON.stringify(body),
}));
const pj = async (hub, path, body) => { const r = await post(hub, path, body); return { s: r.status, j: await r.json() }; };
const form = async (hub, path, params, sign = true) => {
  const p = { MerchantID: FAKE.key.id, ...params };
  if (sign) p.CheckMacValue = await ecpayMac(p, FAKE.key.key, FAKE.key.iv);
  return hub.fetch(new Request(API + path, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(p).toString() }));
};
const rnd = () => Buffer.from(crypto.getRandomValues(new Uint8Array(24))).toString('base64url');
async function login(hub, email) {
  const n = rnd();
  const s = await hub.fetch(new Request(`${API}/auth/start?n=${n}&mode=popup&ret=${encodeURIComponent(ORIGIN + '/')}`));
  const g = new URL(s.headers.get('Location'));
  const cookie = s.headers.get('Set-Cookie').split(';')[0];
  const code = 'c-' + rnd();
  pending[code] = { claims: { iss: 'https://accounts.google.com', aud: CID, sub: 'sub-' + email, email, email_verified: true, name: email.split('@')[0], exp: clock / 1000 + 3600, nonce: g.searchParams.get('nonce') } };
  await hub.fetch(new Request(`${API}/auth/callback?code=${code}&state=${g.searchParams.get('state')}`, { headers: { Cookie: cookie } }));
  return (await (await post(hub, '/auth/redeem', { n })).json()).tok;
}
async function setup(x) {
  FAKE.trades = {}; FAKE.periods = {}; FAKE.calls = []; FAKE.doaction = { RtnCode: '1', RtnMsg: '成功' }; FAKE.cancel = { RtnCode: '1', RtnMsg: '成功' };
  clock = Date.parse('2026-10-11T04:00:00Z');
  const { hub, db } = makeHub(env({ PAY_TEST_ACTIVATE: '1', ...(x || {}) }));
  db.prepare("INSERT OR IGNORE INTO plans (id, name, feats, builtin, updated, price, period) VALUES ('plus', 'Plus', '{}', 0, 0, 299, 'month')").run();
  db.prepare("UPDATE plans SET price = 299, period = 'month' WHERE id = 'plus'").run();
  hub.expInit(); db.prepare("UPDATE plans SET price_year = 2990 WHERE id = 'plus'").run();
  db.prepare("INSERT OR IGNORE INTO plans (id, name, feats, builtin, updated, price, period) VALUES ('pro', 'Pro', '{}', 0, 0, 499, 'month')").run();
  db.prepare("UPDATE plans SET builtin = 0, price = 499, period = 'month', price_year = 5268 WHERE id = 'pro'").run();
  const bob = await login(hub, 'bob@example.com');
  const andy = await login(hub, 'andy@example.com');
  return { hub, db, bob, andy };
}
const permOf = async (hub, t) => (await pj(hub, '/v1/perm/me', { t })).j;
const ord = (db, id) => db.prepare('SELECT * FROM orders WHERE id = ?').get(id);
async function ecCreate(hub, bob, extra = {}) {
  const r = await pj(hub, '/v1/pay/ecpay/create', { t: bob, plan: 'plus', period: 'month', back: BACK, amount: 1, ...extra });
  assert.equal(r.s, 200, JSON.stringify(r.j));
  return r.j;
}
const notify = (hub, id, amt, extra = {}, sign = true) => form(hub, '/v1/pay/ecpay/notify', { MerchantTradeNo: id, RtnCode: '1', RtnMsg: '交易成功', TradeNo: 'T' + id, TradeAmt: String(amt), PaymentDate: '2026/10/11 12:00:00', PaymentType: 'Credit_CreditCard', SimulatePaid: '0', ...extra }, sign);

test('CheckMacValue：用官方附錄範例驗算（特店 3002607、ecpay20230312153023）', async () => {
  const p = { ChoosePayment: 'ALL', EncryptType: '1', ItemName: 'Apple iphone 15', MerchantID: '3002607', MerchantTradeDate: '2023/03/12 15:30:23', MerchantTradeNo: 'ecpay20230312153023',
    PaymentType: 'aio', ReturnURL: 'https://www.ecpay.com.tw/receive.php', TotalAmount: '30000', TradeDesc: '促銷方案' };
  assert.equal(await ecpayMac(p, 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs'), '6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840');
  assert.notEqual(await ecpayMac({ ...p, TotalAmount: '30001' }, 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs'), '6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840');
});

test('存取：未登入被拒、非管理者不能確認／退款／看清單、白名單外網站被擋', async () => {
  const { hub, bob } = await setup();
  for (const p of ['/v1/pay/quote', '/v1/pay/ecpay/create', '/v1/pay/bank/create', '/v1/pay/my', '/v1/pay/order', '/v1/pay/bank/report', '/v1/pay/period/cancel']) {
    assert.equal((await post(hub, p, { plan: 'plus', period: 'month' })).status, 401, p);
  }
  for (const p of ['/v1/admin/pay/list', '/v1/admin/pay/confirm', '/v1/admin/pay/reject', '/v1/admin/pay/refund', '/v1/admin/pay/reactivate', '/v1/admin/pay/bank/put', '/v1/admin/pay/bank/get']) {
    assert.equal((await post(hub, p, { t: bob, id: 'x' })).status, 403, p);
  }
  assert.equal((await post(hub, '/v1/pay/quote', { t: bob, plan: 'plus', period: 'month' }, 'https://evil.example')).status, 403);
});

test('金額以伺服器為準：前端送 amount=1 沒用；表單參數驗章正確、送到綠界測試網址、沒設金鑰標測試模式', async () => {
  const { hub, bob } = await setup();
  const q = (await pj(hub, '/v1/pay/quote', { t: bob, plan: 'plus', period: 'year', amount: 1 })).j;
  assert.deepEqual([q.amount, q.test, q.bank], [2990, true, null], '年繳價、測試模式、收款帳號沒設');
  const c = await ecCreate(hub, bob);
  assert.equal(c.amount, 299);
  assert.equal(c.fields.TotalAmount, '299');
  assert.equal(c.action, 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5');
  assert.equal(c.fields.MerchantID, '3002607');
  assert.equal(c.fields.CheckMacValue, await ecpayMac(c.fields, ECPAY_STAGE.key, ECPAY_STAGE.iv));
  assert.ok(/^LG[0-9A-Z]{16}$/.test(c.id) && c.id.length <= 20, c.id);
  assert.equal(c.fields.ReturnURL, API + '/v1/pay/ecpay/notify');
  assert.equal((await pj(hub, '/v1/pay/ecpay/create', { t: bob, plan: 'free', period: 'month', back: BACK })).s, 400, '免費方案不能結帳');
  assert.equal((await pj(hub, '/v1/pay/ecpay/create', { t: bob, plan: 'plus', period: 'month', back: 'https://evil.example/' })).s, 400, '導回網址不在白名單');
  const r = await ecCreate(hub, bob, { recur: true });
  assert.deepEqual([r.fields.ChoosePayment, r.fields.PeriodAmount, r.fields.PeriodType, r.fields.Frequency, r.fields.ExecTimes], ['Credit', '299', 'M', '1', '99']);
  assert.equal(r.fields.PeriodReturnURL, API + '/v1/pay/ecpay/period');
  /* 正式金鑰設了：改送正式網址、不標測試 */
  const { hub: h2, bob: b2 } = await setup({ ECPAY_MERCHANT_ID: '9999999', ECPAY_HASH_KEY: 'k'.repeat(16), ECPAY_HASH_IV: 'i'.repeat(16) });
  const c2 = (await pj(h2, '/v1/pay/ecpay/create', { t: b2, plan: 'plus', period: 'month', back: BACK })).j;
  assert.deepEqual([c2.action, c2.test, c2.fields.MerchantID], ['https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5', false, '9999999']);
});

test('B1 ReturnURL：驗章成功 RtnCode=1 → 開通（期間＋1 個月）；回 1|OK', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob);
  const r = await notify(hub, c.id, 299);
  assert.equal(r.status, 200); assert.equal(await r.text(), '1|OK');
  const o = ord(db, c.id);
  assert.deepEqual([o.status, o.applied, o.act_src], ['active', 1, 'notify']);
  assert.equal(o.grant_from, clock);
  assert.equal(new Date(o.grant_to).toISOString(), '2026-11-11T04:00:00.000Z');
  const pm = await permOf(hub, bob);
  assert.equal(pm.plan, 'plus');
});

test('B1 驗章錯誤不開通、SimulatePaid=1 不開通、金額不符不開通而且進異常清單', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob);
  const bad = await form(hub, '/v1/pay/ecpay/notify', { MerchantTradeNo: c.id, RtnCode: '1', TradeAmt: '299', CheckMacValue: 'A'.repeat(64) }, false);
  assert.equal(bad.status, 400);
  assert.equal(ord(db, c.id).applied, 0);
  await notify(hub, c.id, 299, { SimulatePaid: '1' });
  assert.equal(ord(db, c.id).applied, 0, '模擬付款不改狀態');
  await notify(hub, c.id, 1);
  assert.equal(ord(db, c.id).applied, 0, '金額不符不開通');
  assert.equal((await permOf(hub, bob)).plan, 'free');
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.ok(l.anomalies.includes(c.id), '異常清單有這筆');
  /* B5 一鍵補開通（金額不符要強制）*/
  assert.equal((await pj(hub, '/v1/admin/pay/reactivate', { t: andy, id: c.id })).s, 409, '沒強制 → 綠界查單顯示沒付');
  assert.equal((await pj(hub, '/v1/admin/pay/reactivate', { t: andy, id: c.id, force: true })).s, 400, '強制開通要寫理由');
  assert.equal((await pj(hub, '/v1/admin/pay/reactivate', { t: andy, id: c.id, force: true, reason: '已到綠界後台確認' })).s, 200);
  assert.equal(ord(db, c.id).status, 'active');
  assert.equal((await permOf(hub, bob)).plan, 'plus');
  assert.equal((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.anomalies.length, 0, '補完異常清單清空');
});

test('B6 冪等：同一筆通知重複送 3 次只加一次期間', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob);
  for (let i = 0; i < 3; i++) assert.equal(await (await notify(hub, c.id, 299)).text(), '1|OK');
  const exp = db.prepare("SELECT expires FROM perm WHERE email = 'bob@example.com'").get().expires;
  assert.equal(new Date(exp).toISOString(), '2026-11-11T04:00:00.000Z', '只加一個月');
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM plan_events WHERE email = 'bob@example.com' AND kind IN ('activate','extend')").get().c, 1);
  /* 第二筆訂單（續訂）→ 從原到期日接下去；續訂只在到期前 7 天內才開放 */
  assert.equal((await pj(hub, '/v1/pay/ecpay/create', { t: bob, plan: 'plus', period: 'month', back: BACK })).s, 409, '還很久：同方案同週期不能再買');
  clock = Date.parse('2026-11-06T04:00:00Z');
  const c2 = await ecCreate(hub, bob);
  await notify(hub, c2.id, 299);
  assert.equal(new Date(ord(db, c2.id).grant_from).toISOString(), '2026-11-11T04:00:00.000Z');
  assert.equal(new Date(ord(db, c2.id).grant_to).toISOString(), '2026-12-11T04:00:00.000Z');
});

test('B2 ReturnURL 完全沒來：使用者被導回（OrderResultURL）時伺服器主動查單 → 開通，並 303 導回付款完成頁', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob);
  FAKE.trades[c.id] = { status: '1', amt: 299 };
  const r = await form(hub, '/v1/pay/ecpay/result', { MerchantTradeNo: c.id, RtnCode: '1', TradeAmt: '299' });
  assert.equal(r.status, 303);
  assert.equal(r.headers.get('Location'), BACK + '#orders/' + c.id);
  assert.deepEqual([ord(db, c.id).applied, ord(db, c.id).act_src], [1, 'result']);
  assert.ok(FAKE.calls.some((x) => x.path === '/Cashier/QueryTradeInfo/V5'), '真的打了查單');
});

test('B2 查單回應驗章錯誤 → 不開通', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob);
  FAKE.trades[c.id] = { status: '1', amt: 299 };
  FAKE.key = { ...ECPAY_STAGE, key: 'x'.repeat(16) };   // 假綠界用錯金鑰簽回應
  try {
    await hub.payQuery(c.id, 'test');
  } finally { FAKE.key = ECPAY_STAGE; }
  assert.equal(ord(db, c.id).applied, 0);
});

test('B3 ReturnURL 與導回都沒來：每 10 分鐘的排程查單補開通；沒付的不開通', async () => {
  const { hub, db, bob } = await setup();
  const paid = await ecCreate(hub, bob);
  const unpaid = await ecCreate(hub, bob);
  FAKE.trades[paid.id] = { status: '1', amt: 299 };
  FAKE.trades[unpaid.id] = { status: '0', amt: 299 };
  clock += 10 * 60 * 1000;
  const r = await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  const j = await r.json();
  assert.deepEqual([j.query, j.fixed], [2, 1]);
  assert.deepEqual([ord(db, paid.id).applied, ord(db, paid.id).act_src], [1, 'sweep']);
  assert.equal(ord(db, unpaid.id).applied, 0);
  assert.equal((await permOf(hub, bob)).plan, 'plus');
});

test('B4 付款完成頁輪詢 /v1/pay/order：還沒開通的會順手查單、開通後回方案與到期日', async () => {
  const { hub, bob } = await setup();
  const c = await ecCreate(hub, bob);
  let j = (await pj(hub, '/v1/pay/order', { t: bob, id: c.id })).j;
  assert.equal(j.order.status, 'pending');
  FAKE.trades[c.id] = { status: '1', amt: 299 };
  clock += 30000;
  j = (await pj(hub, '/v1/pay/order', { t: bob, id: c.id })).j;
  assert.deepEqual([j.order.status, j.plan, j.planName], ['active', 'plus', 'Plus']);
  assert.ok(j.expires > clock);
  const other = await login(hub, 'eve@example.com');
  assert.equal((await pj(hub, '/v1/pay/order', { t: other, id: c.id })).s, 404, '看不到別人的訂單');
});

test('B3／定期定額：每期通知延長 1 個月、同一期重送不重複；對帳補漏掉的期數；會員取消自動續訂（到期日不變）', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob, { recur: true });
  await notify(hub, c.id, 299);
  assert.equal(ord(db, c.id).period_state, 'active');
  const per = (n) => form(hub, '/v1/pay/ecpay/period', { MerchantTradeNo: c.id, RtnCode: '1', RtnMsg: '成功', PeriodType: 'M', Frequency: '1', ExecTimes: '99', Amount: '299', Gwsr: '9' + n, ProcessDate: '2026/11/11 04:00:00', AuthCode: '777777', FirstAuthAmount: '299', TotalSuccessTimes: String(n), SimulatePaid: '0' });
  assert.equal(await (await per(2)).text(), '1|OK');
  assert.equal(await (await per(2)).text(), '1|OK');
  const exp2 = db.prepare("SELECT expires FROM perm WHERE email = 'bob@example.com'").get().expires;
  assert.equal(new Date(exp2).toISOString(), '2026-12-11T04:00:00.000Z', '兩期＝兩個月，重送的第 2 期不算');
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM orders WHERE parent = ?').get(c.id).c, 1);
  /* 第 3 期通知漏掉：對帳補 */
  FAKE.periods[c.id] = { n: 3, amt: 299, exec: '1' };
  const s = await hub.payPeriodSync(c.id, 'test');
  assert.deepEqual([s.ok, s.added], [true, 1]);
  assert.equal(new Date(db.prepare("SELECT expires FROM perm WHERE email = 'bob@example.com'").get().expires).toISOString(), '2027-01-11T04:00:00.000Z');
  assert.equal((await hub.payPeriodSync(c.id, 'test')).added, 0, '再對一次不重複補');
  /* 會員取消自動續訂：綠界失敗 → 不標已取消 */
  FAKE.cancel = { RtnCode: '0', RtnMsg: '查無此訂單' };
  const f = await pj(hub, '/v1/pay/period/cancel', { t: bob, id: c.id });
  assert.equal(f.s, 502); assert.equal(f.j.msg, '查無此訂單');
  assert.equal(ord(db, c.id).period_state, 'active');
  FAKE.cancel = { RtnCode: '1', RtnMsg: '成功' };
  const ok = await pj(hub, '/v1/pay/period/cancel', { t: bob, id: c.id });
  assert.equal(ok.s, 200);
  assert.equal(ord(db, c.id).period_state, 'cancelled');
  assert.ok(FAKE.calls.some((x) => x.path === '/Cashier/CreditCardPeriodAction' && x.f.Action === 'Cancel'));
  assert.equal(new Date(db.prepare("SELECT expires FROM perm WHERE email = 'bob@example.com'").get().expires).toISOString(), '2027-01-11T04:00:00.000Z', '到期日不變');
  assert.equal(ok.j.autoRenew, false);
});

test('B7 到期自動降級＋寫紀錄；降級後再付款從今天起算', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob);
  await notify(hub, c.id, 299);
  assert.equal((await permOf(hub, bob)).plan, 'plus');
  clock = Date.parse('2026-11-11T04:00:01Z');
  assert.equal((await permOf(hub, bob)).plan, 'free', '到期一過，權限回到註冊會員（伺服器到期日為準）');
  await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM plan_events WHERE email = 'bob@example.com' AND kind = 'expire'").get().c, 1, '降級寫一筆紀錄');
  await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM plan_events WHERE email = 'bob@example.com' AND kind = 'expire'").get().c, 1, '不重複記');
  clock = Date.parse('2026-11-20T04:00:00Z');
  const c2 = await ecCreate(hub, bob);
  await notify(hub, c2.id, 299);
  assert.equal(ord(db, c2.id).grant_from, clock, '從今天起算，不是從舊到期日');
  assert.equal(new Date(ord(db, c2.id).grant_to).toISOString(), '2026-12-20T04:00:00.000Z');
  const subs = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j.subs;
  const s = subs.find((x) => x.email === 'bob@example.com');
  assert.deepEqual([s.count, s.total, s.plan, s.autoRenew], [2, 598, 'plus', false]);
  assert.equal(s.downgradeAt, ord(db, c2.id).grant_to, '會員訂閱清單：到期後自動降回的日期');
});

test('銀行轉帳：收款帳號沒設＝尚未開放；設了只有登入會員看得到；開單 → 回報 → 管理者確認 → 開通；24 小時最多 5 筆', async () => {
  const { hub, db, bob, andy } = await setup();
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).s, 409, '還沒設帳號');
  assert.equal((await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '12', account: '1234', holder: '' })).s, 400);
  assert.equal((await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '0000-1111-2222', holder: '測試戶名' })).s, 200);
  assert.equal((await post(hub, '/v1/pay/quote', { plan: 'plus', period: 'month' })).status, 401, '沒登入看不到帳號');
  const q = (await pj(hub, '/v1/pay/quote', { t: bob, plan: 'plus', period: 'month' })).j;
  assert.deepEqual([q.bank.account, q.bank.bank_code, q.bank.days], ['000011112222', '999', 3]);
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year', amount: 5 })).j;
  assert.equal(c.amount, 2990, '金額以伺服器為準');
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j.id, c.id, '同方案同週期沿用同一張待付款單');
  for (const bad of [{ last5: '123' }, { last5: '12345', date: '2026/10/11' }, { last5: '12345', date: '2026-10-11', name: '' }, { last5: '12345', date: '2026-10-11', name: '   ' }]) {
    assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, date: '2026-10-11', ...bad })).s, 400, JSON.stringify(bad));
  }
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '12345', date: '2026-10-11' })).j.error, 'need_name', '10-16：匯款人姓名必填');
  /* 10-16：客戶送來的金額一律不看（亂填 22 也一樣），以訂單金額為準 */
  const rp = await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '54321', date: '2026-10-11', amount: 22, note: '公司帳戶' });
  assert.equal(rp.j.order.status, 'review');
  assert.deepEqual([ord(db, c.id).xfer_amount, ord(db, c.id).payer_name, ord(db, c.id).note], [2990, '鮑伯', ''], '金額＝訂單金額、存姓名、不收備註');
  assert.equal(rp.j.order.payerName, '鮑伯');
  const my = (await pj(hub, '/v1/pay/my', { t: bob })).j;
  assert.equal(my.orders[0].statusName, '待確認');
  assert.equal((await permOf(hub, bob)).plan, 'free', '待確認還沒開通');
  /* 2026-10-12：管理者一定要輸入網銀實收金額；少於應付擋下、不開通 */
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id })).j.error, 'need_received');
  const up = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 2000 });
  assert.deepEqual([up.s, up.j.error, ord(db, c.id).applied], [409, 'underpaid', 0], '實收 2000 < 2990 不能開通');
  assert.equal((await permOf(hub, bob)).plan, 'free');
  const cf = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 2990 });
  assert.equal(cf.s, 200);
  assert.equal(ord(db, c.id).status, 'active');
  assert.equal(ord(db, c.id).recv_amount, 2990);
  assert.equal(new Date(ord(db, c.id).grant_to).toISOString(), '2027-10-11T04:00:00.000Z', '年繳 +12 個月');
  assert.equal((await permOf(hub, bob)).plan, 'plus');
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id })).j.dup, true, '重按確認不重複開通');
  /* 方案異動規則（10-16 Andy 級別：Pro 年 > Pro 月 > Plus 年 > Plus 月）：年繳 Plus 生效中 → 不能再買 Plus 月繳、不能重買同一個；Pro 月繳／年繳都是升級 */
  const blk = async (plan, period) => (await pj(hub, '/v1/pay/bank/create', { t: bob, plan, period })).j;
  assert.deepEqual([(await blk('plus', 'month')).reason, (await blk('plus', 'year')).reason], ['year_to_month', 'same_active']);
  assert.equal((await pj(hub, '/v1/pay/quote', { t: bob, plan: 'pro', period: 'month' })).j.blocked, '', 'Plus 年繳 → Pro 月繳＝級別較高，可以買');
  assert.equal((await pj(hub, '/v1/pay/quote', { t: bob, plan: 'plus', period: 'month' })).j.blocked, 'year_to_month', '報價也帶出擋下原因，前端據此反灰');
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).s, 200, '年繳可升 Pro 年繳');
  /* 到期前 7 天內才能續訂同方案同週期；上面 4 次之後再灌到第 6 筆 → 24 小時上限 */
  const soon = clock + 3 * 86400000;
  db.prepare("UPDATE perm SET expires = ? WHERE email = 'bob@example.com'").run(soon);
  db.prepare("UPDATE orders SET grant_to = ? WHERE id = ?").run(soon, c.id);
  for (let i = 0; i < 3; i++) {   // 前面已開 2 筆（原單＋Pro 年繳），再 3 筆到 5 筆上限
    assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).s, 200);
    db.prepare("UPDATE orders SET status = 'cancelled' WHERE method = 'bank' AND status = 'pending'").run();   // 10-16 起待審核（review）會擋同級，改用作廢讓下一筆開新單
  }
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).s, 429, '24 小時第 6 筆擋下');
});

test('銀行轉帳：沒回報匯款資料（只是開了訂閱頁）→ 管理者不能確認入帳', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  const cf = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id });
  assert.deepEqual([cf.s, cf.j.error], [409, 'not_reported']);
  assert.equal(ord(db, c.id).applied, 0);
  assert.equal((await permOf(hub, bob)).plan, 'free');
});

test('10-16 拿掉補送：一張單只收一次匯款資料；確認／退回後也不能再回報；會員看得到自己的取消／退款申請', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j;
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '11111', date: '2026-10-11' })).s, 200);
  clock += 60000;
  const again = await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '22222', date: '2026-10-11' });
  assert.deepEqual([again.s, again.j.error], [409, 'already_reported'], '已送出就不能再補送');
  const rs = JSON.parse(ord(db, c.id).reports);
  assert.deepEqual(rs.map((r) => [r.name, r.last5, r.amount, r.state]), [['鮑伯', '11111', 2990, 'active']]);
  assert.equal(ord(db, c.id).from_last5, '11111', '訂單上還是第一次的資料');
  const mine = (await pj(hub, '/v1/pay/my', { t: bob })).j.orders.find((o) => o.id === c.id);
  assert.equal(mine.reports.length, 1);
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 2990 });
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '33333', date: '2026-10-11', amount: 1 })).s, 409, '開通後不能再回報');
  /* 申請退款 → 會員「我的訂單」與管理區都看得到 */
  const rq = await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund', note: '不需要了' });
  assert.equal(rq.s, 200);
  assert.deepEqual((await pj(hub, '/v1/pay/my', { t: bob })).j.reqs.map((r) => [r.type, r.status]), [['refund', 'new']]);
  const adm = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j.reqs;
  assert.deepEqual(adm.map((r) => [r.type, r.email, r.status, r.note]), [['refund', 'bob@example.com', 'new', '不需要了']]);
  /* 轉帳會員：帳務狀態 autoRenew=false（前端顯示「不會自動扣款」，不寫「次期不再扣款」）*/
  assert.equal((await pj(hub, '/v1/billing/me', { t: bob })).j.autoRenew, false);
});

test('稽核 1012：重複入帳擋下、方案衝突不蓋掉較高方案、升級留待處理、轉帳不能強制補開通、退款後不能補開通、轉帳以實收退款', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c1 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  const c2x = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c1.id, last5: '12345', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c2x.id, last5: '12345', date: '2026-10-11', amount: 5268 });
  /* H2／M2：轉帳不能用強制補開通繞過 */
  assert.equal((await pj(hub, '/v1/admin/pay/reactivate', { t: andy, id: c1.id, force: true, reason: 'x' })).j.error, 'use_confirm');
  /* 先開 Pro 年繳 */
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c2x.id, received: 5300 })).s, 200, '多收可以開通');
  /* H3：同一筆入帳（末 5 碼＋日期）再確認別張 → 擋下；勾選並寫理由才可以 */
  const d1 = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c1.id, received: 299 });
  assert.deepEqual([d1.s, d1.j.error, d1.j.other], [409, 'dup_xfer', c2x.id]);
  /* H7：Pro 年繳生效中，晚到的 Plus 月繳不准蓋掉 → 不開通、列異常 */
  const d2 = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c1.id, received: 299, dupOk: true, dupReason: '網銀有兩筆不同入帳' });
  assert.deepEqual([d2.s, d2.j.error], [409, 'plan_conflict']);
  assert.deepEqual([ord(db, c1.id).applied, /方案衝突/.test(ord(db, c1.id).anomaly)], [0, true]);
  assert.equal((await permOf(hub, bob)).plan, 'pro');
  /* H4：轉帳以實收（5300）為可退上限 */
  const q = (await pj(hub, '/v1/admin/pay/refund_quote', { t: andy, id: c2x.id })).j;
  assert.deepEqual([q.base, q.left], [5300, 5300]);
  const rf = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c2x.id, rid: 'r-aud-000001', amount: 5300, last5: '11111', date: '2026-10-11', perm: 'now' });
  assert.equal(rf.s, 200, JSON.stringify(rf.j));
  assert.equal((await permOf(hub, bob)).plan, 'free', '退全額＋立即 → 降回');
});

test('稽核 1012：升級（Plus 月繳→Pro 年繳）開通後記「舊方案剩餘沒折抵」待處理', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const a = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: a.id, last5: '10001', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });
  const b2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: b2.id, last5: '10002', date: '2026-10-11', amount: 5268 });
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: b2.id, received: 5268 })).s, 200);
  assert.equal((await permOf(hub, bob)).plan, 'pro');
  assert.ok(/升級：舊方案 plus 還剩/.test(ord(db, b2.id).anomaly), ord(db, b2.id).anomaly);
  assert.ok((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.anomalies.includes(b2.id), '進異常清單提醒管理者');
});

test('會員帳務通知：回報匯款、開通、升級、退回、退款都進站內通知（鈴鐺），同一件事只一則；設了 Resend 才寄信', async () => {
  const sent = [];
  const realFetch = globalThis.fetch;
  const { hub, db, bob, andy } = await setup({ RESEND_API_KEY: 're_test', MAIL_FROM: '哩股哩股 <notice@liguligu-puipui.com>' });
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const a = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: a.id, last5: '20001', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });   // 重按不重複通知
  const b2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: b2.id, last5: '20002', date: '2026-10-11', amount: 5268 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: b2.id, received: 5268 });
  await pj(hub, '/v1/admin/pay/refund', { t: andy, id: b2.id, rid: 'r-note-00001', amount: 5268, last5: '33333', date: '2026-10-11', perm: 'now' });
  const n = (await pj(hub, '/v1/notices', { t: bob })).j.notices.filter((x) => x.kind === 'pay');
  const titles = n.map((x) => x.title);
  assert.ok(titles.some((t) => /已收到你的匯款資料/.test(t)), titles);
  assert.ok(titles.some((t) => /付款完成，已開通：Plus/.test(t)), titles);
  assert.ok(titles.some((t) => /升級完成：Pro・年繳/.test(t)), titles);
  assert.ok(titles.some((t) => /退款完成：NT\$ 5268/.test(t)), titles);
  assert.equal(titles.filter((t) => /付款完成，已開通：Plus/.test(t)).length, 1, '同一件事只通知一次');
  const rf = n.find((x) => /退款完成/.test(x.title));
  assert.ok(/末 5 碼 33333/.test(rf.body) && /回到註冊會員/.test(rf.body), rf.body);
  assert.ok(n.every((x) => x.read === false));
  await pj(hub, '/v1/notices/read', { t: bob, ids: [rf.id] });
  assert.equal((await pj(hub, '/v1/notices', { t: bob })).j.notices.find((x) => x.id === rf.id).read, true, '已讀會記住');
  /* 別人看不到 bob 的通知 */
  const an = (await pj(hub, '/v1/notices', { t: andy })).j.notices.filter((x) => x.kind === 'pay');
  assert.equal(an.filter((x) => !/^新訂單：/.test(x.title)).length, 0, '管理者看不到 bob 的個人帳務通知');
  assert.ok(an.some((x) => /^新訂單：/.test(x.title)), '10-16：客戶送出匯款資料 → 管理者鈴鐺有「新訂單」通知');
  /* 寄信：排程送出、帶收件人 */
  globalThis.fetch = async (u, init) => { if (String(u).startsWith('https://api.resend.com')) { sent.push(JSON.parse(init.body)); return new Response('{}', { status: 200 }); } return realFetch(u, init); };
  try { await hub.payMailFlush(); } finally { globalThis.fetch = realFetch; }
  const toBob = sent.filter((m) => m.to[0] === 'bob@example.com'), toOwn = sent.filter((m) => m.to[0] !== 'bob@example.com');
  assert.ok(toBob.length >= 4 && toBob.every((m) => /^【哩股哩股】/.test(m.subject)), JSON.stringify(sent.map((m) => m.subject)));
  /* 10-16 Andy：「當訂閱後，我這邊也會收到mail 標題是他的姓名 + 方案 日期」→ 寄到 liguligu0818@gmail.com，標題「姓名 方案（月繳/年繳） YYYY-MM-DD」 */
  assert.deepEqual(toOwn.map((m) => [m.to[0], m.subject]), [['liguligu0818@gmail.com', '鮑伯 Plus（月繳） 2026-10-11'], ['liguligu0818@gmail.com', '鮑伯 Pro（年繳） 2026-10-11']]);
  const ob = toOwn[0].text;
  assert.ok([a.id, 'NT$ 299', '20001', '2026-10-11', 'bob@example.com'].every((k) => ob.includes(k)), ob);
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM mail_out WHERE status = 'pending'").get().c, 0);
});

test('清除測試資料：要再打一次 email、清掉訂單／退款／通知／申請、權限回註冊會員、留事件；有綠界正式付款的帳號拒絕', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const a = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: a.id, last5: '30001', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });
  await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund' });
  assert.equal((await permOf(hub, bob)).plan, 'plus');
  assert.equal((await pj(hub, '/v1/admin/pay/purge', { t: bob, email: 'bob@example.com', confirm: 'bob@example.com' })).s, 403, '只有管理者');
  assert.equal((await pj(hub, '/v1/admin/pay/purge', { t: andy, email: 'bob@example.com', confirm: 'bo@example.com' })).j.error, 'confirm');
  const r = await pj(hub, '/v1/admin/pay/purge', { t: andy, email: 'bob@example.com', confirm: 'BOB@example.com' });
  assert.equal(r.s, 200, JSON.stringify(r.j));
  assert.equal(r.j.orders, 1);
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM orders WHERE email = 'bob@example.com'").get().c, 0);
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM user_notices WHERE email = 'bob@example.com'").get().c, 0);
  assert.equal((await permOf(hub, bob)).plan, 'free');
  assert.ok(db.prepare("SELECT COUNT(*) AS c FROM pay_events WHERE kind = 'purge'").get().c === 1, '刪了什麼留紀錄');
  /* 綠界正式付款（非測試）不能清 */
  const { hub: h2, db: d2, bob: b2, andy: a2 } = await setup({ ECPAY_MERCHANT_ID: '3002607', ECPAY_HASH_KEY: ECPAY_STAGE.key, ECPAY_HASH_IV: ECPAY_STAGE.iv });
  const c = (await pj(h2, '/v1/pay/ecpay/create', { t: b2, plan: 'plus', period: 'month', back: BACK })).j;
  await notify(h2, c.id, 299);
  assert.equal((await pj(h2, '/v1/admin/pay/purge', { t: a2, email: 'bob@example.com', confirm: 'bob@example.com' })).j.error, 'real_payment');
  assert.equal(d2.prepare("SELECT COUNT(*) AS c FROM orders WHERE email = 'bob@example.com'").get().c, 1);
});

test('方案異動：月繳 Plus 可升 Plus 年繳／Pro；不可降級；Pro 年繳什麼都不能再買', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const buy = async (plan, period) => {
    const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan, period })).j;
    if (!c.ok) return c;
    const l5 = String(10000 + Math.floor(Math.random() * 89999));   // 每次不同的入帳（同末 5 碼＋同日期會被當成重複入帳擋下，見下一個測試）
    await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: l5, date: '2026-10-11', amount: c.amount });
    await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: c.amount });
    return c;
  };
  await buy('plus', 'month');
  const st = async (plan, period) => (await pj(hub, '/v1/pay/quote', { t: bob, plan, period })).j.blocked;
  assert.deepEqual([await st('plus', 'month'), await st('plus', 'year'), await st('pro', 'month'), await st('pro', 'year')], ['same_active', '', '', '']);
  await buy('pro', 'year');
  assert.deepEqual([await st('plus', 'month'), await st('plus', 'year'), await st('pro', 'month'), await st('pro', 'year')], ['lower_plan', 'lower_plan', 'year_to_month', 'same_active']);
});

test('銀行轉帳：退回要寫原因、不開通；管理者備註；轉帳會員到期前 7 天出現提醒', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '54321', date: '2026-10-11', amount: 299 });
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id })).s, 400, '要寫原因');
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id, reason: '查無入帳' })).s, 200);
  assert.deepEqual([ord(db, c.id).status, ord(db, c.id).reject_reason, ord(db, c.id).applied], ['rejected', '查無入帳', 0]);
  assert.equal((await permOf(hub, bob)).plan, 'free');
  assert.equal((await pj(hub, '/v1/admin/pay/note', { t: andy, id: c.id, note: '已電話聯絡' })).s, 200);
  assert.equal(ord(db, c.id).admin_note, '已電話聯絡');
  /* 確認一筆 → 到期前 7 天 → 提醒（stage 7）；前 1 天（stage 1）；管理區「即將到期的轉帳會員」 */
  const c2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c2.id, last5: '54321', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c2.id, received: 299 });
  assert.equal((await pj(hub, '/v1/pay/my', { t: bob })).j.renew, null, '還很久');
  clock = Date.parse('2026-11-05T04:00:00Z');
  const r7 = (await pj(hub, '/v1/pay/my', { t: bob })).j.renew;
  assert.deepEqual([r7.days, r7.stage, r7.amount, r7.method], [6, 7, 299, 'bank']);
  assert.ok((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.expiring.includes('bob@example.com'));
  clock = Date.parse('2026-11-10T12:00:00Z');
  assert.equal((await pj(hub, '/v1/pay/my', { t: bob })).j.renew.stage, 1);
});

test('退款：轉帳人工登記＋立即降級；重複按同一個 rid 不重複執行；超過可退金額擋下；CSV 欄位資料在清單裡', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '54321', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 299 });
  const q = (await pj(hub, '/v1/admin/pay/refund_quote', { t: andy, id: c.id })).j;
  assert.deepEqual([q.kind, q.suggest, q.left], ['manual', 299, 299], '7 天內全額、轉帳要人工');
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000001', amount: 300, last5: '11111', date: '2026-10-11' })).s, 400, '超過可退金額');
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000001', amount: 299, date: '2026-10-11' })).s, 400, '人工退款要退款帳號末 5 碼');
  const r1 = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000002', amount: 299, last5: '11111', date: '2026-10-11', note: '網銀匯回', perm: 'now' });
  assert.equal(r1.s, 200, JSON.stringify(r1.j));
  const r2 = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000002', amount: 299, last5: '11111', date: '2026-10-11' });
  assert.equal(r2.j.dup, true, '同一個 rid 第二次只回上次結果');
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM refunds WHERE oid = ? AND status = 'done'").get(c.id).c, 1);
  assert.equal(ord(db, c.id).status, 'refunded');
  assert.equal((await permOf(hub, bob)).plan, 'free', '退款後立即降級');
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000003', amount: 1, last5: '11111', date: '2026-10-11' })).s, 409, '已全額退，再退擋下（10-16 起回 409 already_refunded）');
  const my = (await pj(hub, '/v1/pay/my', { t: bob })).j.orders.find((o) => o.id === c.id);
  assert.deepEqual([my.statusName, my.refunded, my.refunds.length], ['已退款', 299, 1], '會員端看得到退款');
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.ok(l.refunds.some((r) => r.oid === c.id && r.acct_last5 === '11111' && r.rdate === '2026-10-11'));
  assert.ok(l.events.some((e) => e.kind === 'refund_downgrade'));
  clock += 60 * 60 * 1000;
  await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM plan_events WHERE email = 'bob@example.com' AND kind = 'expire'").get().c, 0, '退款降級已經記過，不再多記一筆到期降級');
});

test('退款：部分退款＋到期才停 → 權限保留；信用卡在測試環境不准呼叫退刷；正式環境走 DoAction、失敗顯示綠界原因、定期定額同時終止', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob);
  await notify(hub, c.id, 299);
  const p1 = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-100000001', amount: 100, perm: 'end' });
  assert.equal(p1.j.error, 'stage_no_refund', '測試環境不提供退刷 API');
  const m = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-100000002', amount: 100, perm: 'end', manual: true, date: '2026-10-11', note: '綠界後台手動退' });
  assert.equal(m.s, 200, JSON.stringify(m.j));
  assert.deepEqual([ord(db, c.id).status, ord(db, c.id).refunded], ['active', 100], '部分退款：狀態仍已開通、記退了多少');
  assert.equal((await permOf(hub, bob)).plan, 'plus', '到期才停：權限保留');
  /* 正式環境 */
  const K = { ECPAY_MERCHANT_ID: '3002607', ECPAY_HASH_KEY: ECPAY_STAGE.key, ECPAY_HASH_IV: ECPAY_STAGE.iv };
  const { hub: h, db: d, bob: b, andy: a } = await setup(K);
  const c2 = (await pj(h, '/v1/pay/ecpay/create', { t: b, plan: 'plus', period: 'month', back: BACK, recur: true })).j;
  await notify(h, c2.id, 299);
  clock += 2 * DAY;   // 已過 20:00 自動關帳 → 退刷 R
  FAKE.doaction = { RtnCode: '0', RtnMsg: '餘額不足無法退刷' };
  const f = await pj(h, '/v1/admin/pay/refund', { t: a, id: c2.id, rid: 'r-200000001', amount: 299 });
  assert.deepEqual([f.s, f.j.msg], [502, '餘額不足無法退刷']);
  assert.equal(d.prepare('SELECT status FROM orders WHERE id = ?').get(c2.id).status, 'active', '失敗不標已退款');
  FAKE.doaction = { RtnCode: '1', RtnMsg: '成功' };
  const ok = await pj(h, '/v1/admin/pay/refund', { t: a, id: c2.id, rid: 'r-200000002', amount: 299 });
  assert.equal(ok.s, 200, JSON.stringify(ok.j));
  const act = FAKE.calls.filter((x) => x.path === '/CreditDetail/DoAction').map((x) => x.f.Action);
  assert.deepEqual(act, ['R', 'R']);
  assert.ok(FAKE.calls.some((x) => x.path === '/CreditDetail/DoAction' && new URL('https://payment.ecpay.com.tw').host));
  assert.equal(d.prepare('SELECT period_state FROM orders WHERE id = ?').get(c2.id).period_state, 'cancelled', '定期定額同時終止');
  assert.equal((await permOf(h, b)).plan, 'free', '預設立即降級');
  /* 同一天授權（還沒關帳）全額 → 放棄 N */
  const c3 = (await pj(h, '/v1/pay/ecpay/create', { t: b, plan: 'plus', period: 'month', back: BACK })).j;
  clock = Date.parse('2026-10-14T02:00:00Z');   // 台北 10:00
  await notify(h, c3.id, 299, { PaymentDate: '2026/10/14 09:30:00' });
  FAKE.calls = [];
  await pj(h, '/v1/admin/pay/refund', { t: a, id: c3.id, rid: 'r-300000001', amount: 299 });
  assert.deepEqual(FAKE.calls.filter((x) => x.path === '/CreditDetail/DoAction').map((x) => x.f.Action), ['N']);
});

test('會員訂閱清單與我的訂單：付款方式、首次／最近付款、自動續訂、累計金額', async () => {
  const { hub, bob, andy } = await setup();
  const c = await ecCreate(hub, bob, { recur: true });
  await notify(hub, c.id, 299);
  const s = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j.subs[0];
  assert.deepEqual([s.email, s.method, s.autoRenew, s.downgradeAt, s.total, s.count], ['bob@example.com', 'period', true, 0, 299, 1]);
  assert.ok(s.firstPaid && s.lastPaid && s.expires);
  const my = (await pj(hub, '/v1/pay/my', { t: bob })).j;
  assert.deepEqual([my.autoRenew, my.autoRenewId, my.renew], [true, c.id, null], '定期定額的人不出現轉帳續期提醒');
});

test('刪除帳號：交易紀錄保留（uid 斷開）；備份匯出含 orders／refunds', async () => {
  const { hub, db, bob } = await setup({ BACKUP_TOKEN: 'backup-token-backup-token-xx' });
  const c = await ecCreate(hub, bob);
  await notify(hub, c.id, 299);
  const r = await hub.fetch(new Request(API + '/v1/admin/export', { method: 'POST', headers: { Authorization: 'Bearer backup-token-backup-token-xx' }, body: '{}' }));
  const t = JSON.parse((await r.text()).replace(/,"sha256":.*$/, '}')).tables;
  assert.ok(t.orders.rows.length === 1 && 'refunds' in t && 'plan_events' in t);
  await post(hub, '/v1/delete', { t: bob });
  assert.equal(ord(db, c.id).uid, '');
  assert.equal(ord(db, c.id).email, 'bob@example.com');
});

/* 2026-10-11 Andy：「只要還沒付費 就不能出現這樣 只有真的付費了 才能變更當前會員狀態」 */
test('未付款：建立綠界訂單沒付 → 我的訂單看不到、會員狀態不變；付款通知進來 → 出現在我的訂單、狀態變更', async () => {
  const { hub, bob } = await setup();
  const c = await ecCreate(hub, bob);
  let my = (await pj(hub, '/v1/pay/my', { t: bob })).j;
  assert.deepEqual([my.orders.length, my.plan, my.expires, my.renew], [0, 'free', 0, null], '待付款不列、方案不變、沒有到期日');
  assert.equal((await permOf(hub, bob)).plan, 'free');
  assert.equal((await pj(hub, '/v1/billing/me', { t: bob })).j.paid, false, '帳務狀態也不變');
  await notify(hub, c.id, 299);
  my = (await pj(hub, '/v1/pay/my', { t: bob })).j;
  assert.deepEqual([my.orders.length, my.orders[0].id, my.orders[0].statusName, my.plan], [1, c.id, '已開通', 'plus']);
});

test('待付款超過 3 天 → 排程自動「已取消（未付款）」；之後綠界才通知付款成功 → 照樣開通＋列異常；管理者標記已處理', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob);
  clock += 3 * DAY + 60000;
  await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  assert.deepEqual([ord(db, c.id).status, ord(db, c.id).applied], ['cancelled', 0]);
  assert.equal((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.status.cancelled, '已取消（未付款）');
  assert.equal((await permOf(hub, bob)).plan, 'free');
  await notify(hub, c.id, 299);
  assert.deepEqual([ord(db, c.id).status, ord(db, c.id).applied], ['active', 1], '錢收了就開通');
  assert.ok(/已取消（未付款）之後才收到付款/.test(ord(db, c.id).anomaly));
  assert.ok((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.anomalies.includes(c.id), '列進異常清單');
  assert.equal((await pj(hub, '/v1/admin/pay/ack', { t: andy, id: c.id })).s, 200);
  assert.equal((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.anomalies.length, 0, '標記已處理後拿掉');
  assert.equal((await post(hub, '/v1/admin/pay/ack', { t: bob, id: c.id })).status, 403);
});

test('重新點結帳：舊的未付款綠界單作廢、不累積；舊單其實付了（通知漏掉）→ 排程照樣查單開通', async () => {
  const { hub, db, bob } = await setup();
  const a = await ecCreate(hub, bob);
  const b2 = await ecCreate(hub, bob);
  assert.equal(ord(db, a.id).status, 'cancelled');
  assert.equal(ord(db, b2.id).status, 'pending');
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM orders WHERE uid = (SELECT uid FROM orders WHERE id = ?) AND status = 'pending'").get(a.id).c, 1, '同時只留一筆待付款');
  FAKE.trades[a.id] = { status: '1', amt: 299 };
  clock += 10 * 60 * 1000;
  await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' }));
  assert.deepEqual([ord(db, a.id).applied, ord(db, a.id).act_src], [1, 'sweep']);
  assert.equal((await permOf(hub, bob)).plan, 'plus');
});

test('10-16 通知信沒設 Resend 也不影響付款：回報照樣成功、信留在佇列；NOTIFY_EMAIL 可換收件人', async () => {
  const { hub, db, bob, andy } = await setup({ NOTIFY_EMAIL: 'other@example.com' });
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j;
  const r = await pj(hub, '/v1/pay/bank/report', { t: bob, name: '王小明', id: c.id, last5: '12345', date: '2026-10-11' });
  assert.equal(r.s, 200);
  const m = db.prepare("SELECT * FROM mail_out WHERE email = 'other@example.com'").all();
  assert.deepEqual(m.map((x) => [x.subject, x.status]), [['王小明 Plus（年繳） 2026-10-11', 'pending']]);
});

test('10-16 只有管理者能改轉帳金額：會員不行；開通後不能改；改了會記事件、會員端看到新金額', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '12345', date: '2026-10-11', amount: 200 });
  assert.equal(ord(db, c.id).xfer_amount, 2990);
  assert.equal((await pj(hub, '/v1/admin/pay/amount', { t: bob, id: c.id, amount: 1 })).s, 403, '會員不能改');
  assert.equal((await pj(hub, '/v1/admin/pay/amount', { t: andy, id: c.id, amount: 0 })).s, 400);
  const r = await pj(hub, '/v1/admin/pay/amount', { t: andy, id: c.id, amount: 2500, reason: '早鳥價' });
  assert.equal(r.s, 200);
  assert.deepEqual([ord(db, c.id).amount, ord(db, c.id).xfer_amount], [2500, 2500]);
  assert.ok(db.prepare("SELECT detail FROM pay_events WHERE oid = ? AND kind = 'amount'").get(c.id).detail.includes('早鳥價'));
  assert.equal((await pj(hub, '/v1/pay/my', { t: bob })).j.orders.find((o) => o.id === c.id).amount, 2500);
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 2500 })).s, 200, '照新金額確認入帳');
  assert.equal((await pj(hub, '/v1/admin/pay/amount', { t: andy, id: c.id, amount: 100 })).s, 409, '開通後不能改');
  const adm = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j.orders.find((o) => o.id === c.id);
  assert.equal(adm.payerName, '鮑伯', '管理區訂單看得到匯款人姓名');
});

test('10-16 待審核擋同級與更低：送出匯款資料後只能申請更高級別', async () => {
  const { hub, andy, bob } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '0000-1111-2222', holder: '測試戶名' });
  const c = await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' });
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.j.id, name: '王小明', last5: '12345', date: '2026-10-11' })).s, 200);
  const q = async (plan, period) => (await pj(hub, '/v1/pay/quote', { t: bob, plan, period })).j.blocked;
  assert.deepEqual([await q('plus', 'month'), await q('plus', 'year'), await q('pro', 'month'), await q('pro', 'year')], ['pending_review', 'pending_review', '', '']);
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j.error, 'blocked');
  void andy;
});

/* ============================================================== 2026-10-16 管理區分頁關係（docs/payment_admin_tabs_1016.md）
   Andy 10-16：「不應該發生 他待審核，另一個退款分頁還有這個人，一個mail 身份只能存在一個，若他有最新的一筆資訊，就只會留下最新的一筆」
   Andy 10-16：「這邊應該是 會多出現已退款功能按鈕 並且跳到退款紀錄那邊紀錄」 */
const bankOn = (hub, andy) => pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
async function bankPaid(hub, bob, andy, plan = 'plus', period = 'month', last5 = '54321') {
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan, period })).j;
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5, date: '2026-10-11' })).s, 200);
  if (andy) assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: c.amount })).s, 200);
  return c;
}
const reqsOf = (db, email) => db.prepare("SELECT * FROM sub_requests WHERE email = ? AND type IN ('cancel', 'refund') ORDER BY created").all(email);
const evKinds = (db, kind) => db.prepare('SELECT * FROM pay_events WHERE kind = ?').all(kind);

test('10-16 同一 email 只留最新：先申請退款、之後又送出新訂單 → 舊申請自動結案「已被新訂單取代」並寫事件', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  await bankPaid(hub, bob, andy, 'plus', 'month', '11111');
  clock += 3600000;
  assert.equal((await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund', note: '先退款' })).s, 200);
  assert.equal((await pj(hub, '/v1/admin/pay/list', { t: andy })).j.reqs.filter((r) => r.status === 'new').length, 1);
  clock += 3600000;
  const c2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c2.id, last5: '22222', date: '2026-10-11' })).s, 200);
  const r = reqsOf(db, 'bob@example.com');
  assert.deepEqual(r.map((x) => [x.type, x.status, x.closed_by]), [['refund', 'done', 'auto']]);
  assert.match(r[0].close_reason, new RegExp('已被新訂單 ' + c2.id));
  assert.equal(evKinds(db, 'req_close').length, 1, '寫進金流事件');
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.deepEqual([l.reqs.filter((x) => x.status === 'new').length, l.orders.filter((o) => o.status === 'review').length], [0, 1], '待處理只剩最新那件（新訂單）');
  assert.equal((await pj(hub, '/v1/billing/me', { t: bob })).j.refund, null, '會員端也不再顯示申請處理中');
  const my = (await pj(hub, '/v1/pay/my', { t: bob })).j.reqs[0];
  assert.match(my.closeReason, /已被新訂單/);
});

test('10-16 有待確認的轉帳時不能再送取消／退款申請（不會兩邊同時待處理）', async () => {
  const { hub, bob, andy } = await setup();
  await bankOn(hub, andy);
  await bankPaid(hub, bob, andy, 'plus', 'month');
  clock += 60000;
  const c2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c2.id, last5: '22222', date: '2026-10-11' });
  for (const type of ['refund', 'cancel']) {
    const r = await pj(hub, '/v1/subscribe/change', { t: bob, type });
    assert.deepEqual([r.s, r.j.error], [409, 'pending_review'], type);
    assert.match(r.j.msg, /審核中/);
  }
});

test('10-16 先申請退款、再申請取消 → 只留最新的取消申請；綠界新訂單付款完成也會結案比它舊的申請', async () => {
  /* 註：反過來（先取消再退款）原本就被擋 —— 取消後就不能再享有七天退款保證（10-09 規則）*/
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  await bankPaid(hub, bob, andy);
  clock += 60000;
  assert.equal((await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund' })).s, 200);
  clock += 60000;
  assert.equal((await pj(hub, '/v1/subscribe/change', { t: bob, type: 'cancel' })).s, 200);
  assert.deepEqual(reqsOf(db, 'bob@example.com').map((x) => [x.type, x.status]), [['refund', 'done'], ['cancel', 'new']]);
  assert.match(reqsOf(db, 'bob@example.com')[0].close_reason, /較新的取消訂閱申請/);
  clock += 60000;
  const e = await ecCreate(hub, bob, { plan: 'pro', period: 'year' });
  assert.equal(await (await notify(hub, e.id, 5268)).text(), '1|OK');
  assert.deepEqual(reqsOf(db, 'bob@example.com').map((x) => x.status), ['done', 'done'], '綠界新訂單付款完成 → 取消申請也結案');
  assert.match(reqsOf(db, 'bob@example.com')[1].close_reason, new RegExp(e.id));
});

test('10-16 待確認期間：較低級別的舊單不能再回報；較高的新單回報 → 舊待確認標「已被取代」，管理者仍可確認或退款', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  const low = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;   // 先開、還沒回報
  const mid = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j;
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: mid.id, last5: '11111', date: '2026-10-11' })).s, 200);
  const lr = await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: low.id, last5: '33333', date: '2026-10-11' });
  assert.deepEqual([lr.s, lr.j.error], [409, 'pending_review'], '跟 payChangeCheck 一致：同級或更低不能送');
  clock += 60000;
  const hi = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: hi.id, last5: '22222', date: '2026-10-11' })).s, 200);
  assert.deepEqual([ord(db, mid.id).status, ord(db, hi.id).status], ['superseded', 'review']);
  assert.match(ord(db, mid.id).reject_reason, new RegExp('已被較新的訂單 ' + hi.id));
  assert.equal(evKinds(db, 'superseded').length, 1);
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.deepEqual(l.orders.filter((o) => o.status === 'review').map((o) => o.id), [hi.id], '待確認只剩最新一筆');
  assert.equal(l.status.superseded, '已被取代');
  assert.ok((await pj(hub, '/v1/pay/my', { t: bob })).j.orders.some((o) => o.id === mid.id && o.statusName === '已被取代'), '會員端看得到被取代的那筆與原因');
  /* 被取代的單：兩筆都匯了錢 → 管理者登記人工退款（不動權限、不算用掉七天保證）*/
  const q = (await pj(hub, '/v1/admin/pay/refund_quote', { t: andy, id: mid.id })).j;
  assert.deepEqual([q.suggest, q.kind], [2990, 'manual']);
  const rf = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: mid.id, rid: 'r-sup000001', amount: 2990, last5: '11111', date: '2026-10-11' });
  assert.equal(rf.s, 200, JSON.stringify(rf.j));
  assert.equal(ord(db, mid.id).status, 'refunded');
  assert.equal((db.prepare('SELECT refund_used FROM bill_flags WHERE email = ?').get('bob@example.com') || {}).refund_used || 0, 0);
  /* 新的那筆照常確認開通 */
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: hi.id, received: 5268 })).s, 200);
  assert.equal((await permOf(hub, bob)).plan, 'pro');
});

test('10-16 已退款鈕：退款帶申請編號 → 申請自動「已處理（已退款 NT$…）」、退款紀錄記 req；申請跟訂單不同人擋下', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  const c = await bankPaid(hub, bob, andy);
  clock += 60000;
  const rq = (await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund', note: '不要了' })).j;
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.equal(l.reqs[0].oid, c.id, '清單幫這筆申請找好對應訂單（預填用）');
  /* 別人的申請不能拿來關 */
  const carol = await login(hub, 'carol@example.com');
  await bankPaid(hub, carol, andy, 'plus', 'month', '99999');
  const cr = (await pj(hub, '/v1/subscribe/change', { t: carol, type: 'refund' })).j;
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-req0000001', amount: 299, last5: '11111', date: '2026-10-11', req: cr.id })).j.error, 'bad_req');
  const r = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-req0000002', amount: 299, last5: '11111', date: '2026-10-11', req: rq.id });
  assert.equal(r.s, 200, JSON.stringify(r.j));
  const row = db.prepare('SELECT * FROM sub_requests WHERE id = ?').get(rq.id);
  assert.deepEqual([row.status, row.closed_by], ['done', 'andy@example.com']);
  assert.match(row.close_reason, /已退款 NT\$ 299/);
  assert.equal(db.prepare('SELECT req FROM refunds WHERE id = ?').get('r-req0000002').req, rq.id);
  assert.equal(evKinds(db, 'req_refunded').length, 1);
  assert.equal(db.prepare('SELECT status FROM sub_requests WHERE id = ?').get(cr.id).status, 'new', 'carol 的申請不受影響');
});

test('10-16 舊資料修正：管理區打開清單時，同一人兩筆待確認＋比它舊的申請一次整理；改回待處理後不會再被舊事件結案', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  await bankPaid(hub, bob, andy);
  clock += 60000;
  const rq = (await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund' })).j;
  /* 模擬 10-16 之前留下的資料：申請之後又有兩筆待確認（當時沒有規則擋）*/
  const mk = (id, plan, period, at) => db.prepare(`INSERT INTO orders (id, uid, email, plan, plan_name, period, amount, method, status, from_last5, xfer_date, xfer_amount, reports, created, updated)
    VALUES (?, 'x', 'bob@example.com', ?, ?, ?, 299, 'bank', 'review', '12345', '2026-10-11', 299, ?, ?, ?)`).run(id, plan, plan === 'pro' ? 'Pro' : 'Plus', period, JSON.stringify([{ at, last5: '12345' }]), at, at);
  mk('LG000000000001', 'plus', 'year', clock + 1000);
  mk('LG000000000002', 'pro', 'month', clock + 2000);
  clock += 5000;
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.deepEqual([ord(db, 'LG000000000001').status, ord(db, 'LG000000000002').status], ['superseded', 'review']);
  assert.equal(l.reqs.find((r) => r.id === rq.id).status, 'done');
  /* 管理者改回待處理 → 再打開清單也不會被那筆（比改回時間舊的）訂單事件結案 */
  assert.equal((await pj(hub, '/v1/admin/feedback/set', { t: andy, kind: 'request', id: rq.id, status: 'new' })).s, 200);
  clock += 1000;
  const l2 = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  const back = l2.reqs.find((r) => r.id === rq.id);
  assert.deepEqual([back.status, back.closeReason, !!back.pinned], ['new', null, true]);
  /* 管理者手動標記已處理 → 寫原因 */
  await pj(hub, '/v1/admin/feedback/set', { t: andy, kind: 'request', id: rq.id, status: 'done' });
  assert.equal(db.prepare('SELECT close_reason FROM sub_requests WHERE id = ?').get(rq.id).close_reason, '管理者標記已處理');
});

/* ============================================================== 2026-10-16 處理措施（規則手冊）—— Andy：「並且需要制定完善的措施」 */
test('措施 1 狀態機：不允許的轉換一律 409（已退回再退回、已退回又確認、開通後退回／改金額、已退款再確認）', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '11111', date: '2026-10-11' });
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id, reason: '查無入帳' })).s, 200);
  const twice = await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id, reason: '再按一次' });
  assert.deepEqual([twice.s, twice.j.error, twice.j.lastBy], [409, 'bad_status', 'andy@example.com'], '已退回再退回：409 並回上一個動手的人');
  const cf = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 299 });
  assert.deepEqual([cf.s, cf.j.error, cf.j.statusName], [409, 'bad_status', '已退回'], '已退回又確認入帳：擋');
  assert.equal(ord(db, c.id).applied, 0);
  const c2 = await bankPaid(hub, bob, andy, 'plus', 'year', '22222');
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c2.id, reason: 'x' })).j.error, 'applied', '開通後不能退回');
  assert.equal((await pj(hub, '/v1/admin/pay/amount', { t: andy, id: c2.id, amount: 1 })).s, 409, '開通後不能改金額');
  await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c2.id, rid: 'r-sm00000001', amount: 2990, last5: '11111', date: '2026-10-11' });
  const again = await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c2.id, rid: 'r-sm00000002', amount: 1, last5: '11111', date: '2026-10-11' });
  assert.deepEqual([again.s, again.j.error], [409, 'already_refunded'], '已退款又要求退款');
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c2.id, received: 2990 })).j.dup, true, '已開通過（含已退款）重按確認＝不重複開通');
});

test('措施 3 兩個管理者同時處理：expect 跟伺服器不同 → 409 stale；申請重複標記 → 409 same_status；另一位已退款結案的申請不能再退', async () => {
  const { hub, db, bob, andy } = await setup({ ADMIN_EMAILS: 'andy@example.com,amy@example.com' });
  const amy = await login(hub, 'amy@example.com');
  await bankOn(hub, andy);
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c.id, last5: '11111', date: '2026-10-11' });
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 299, expect: 'review' })).s, 200);
  const late = await pj(hub, '/v1/admin/pay/reject', { t: amy, id: c.id, reason: '晚一步', expect: 'review' });
  assert.equal(late.s, 409);
  assert.equal((await pj(hub, '/v1/admin/pay/confirm', { t: amy, id: c.id, received: 299, expect: 'review' })).j.lastBy, 'andy@example.com', '晚到的確認回「誰開通的」');
  clock += 60000;
  const rq = (await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund' })).j;
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-two0000001', amount: 299, last5: '11111', date: '2026-10-11', req: rq.id })).s, 200);
  const dup = await pj(hub, '/v1/admin/pay/refund', { t: amy, id: c.id, rid: 'r-two0000002', amount: 1, last5: '11111', date: '2026-10-11', req: rq.id });
  assert.deepEqual([dup.s, dup.j.error, dup.j.closedBy], [409, 'req_done', 'andy@example.com']);
  const ss = await pj(hub, '/v1/admin/feedback/set', { t: amy, kind: 'request', id: rq.id, status: 'done' });
  assert.deepEqual([ss.s, ss.j.error], [409, 'same_status']);
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM refunds WHERE status = 'done'").get().c, 1, '錢只退一次');
});

test('措施 2＋4 退款完成會把同一人所有待處理退款申請結案；稽核清單記 誰／何時／做什麼／前後狀態', async () => {
  const { hub, bob, andy } = await setup();
  await bankOn(hub, andy);
  const c = await bankPaid(hub, bob, andy);
  clock += 60000;
  await pj(hub, '/v1/subscribe/change', { t: bob, type: 'refund' });
  /* 沒走「已退款」鈕，直接在訂單分頁按退款 → 申請一樣結案 */
  await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-aud0000001', amount: 299, last5: '11111', date: '2026-10-11' });
  const l = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.equal(l.reqs[0].status, 'done');
  assert.match(l.reqs[0].closeReason, /已退款 NT\$ 299/);
  const k = (kind) => l.audit.find((a) => a.kind === kind);
  assert.deepEqual([k('confirm').by, k('confirm').from, k('confirm').to], ['andy@example.com', 'review', 'active']);
  assert.deepEqual([k('refund').by, k('refund').from, k('refund').to], ['andy@example.com', 'active', 'refunded']);
  assert.deepEqual([k('req_close').from, k('req_close').to], ['new', 'done']);
  assert.ok(k('bank_put') && k('bank_put').by === 'andy@example.com' && !JSON.stringify(k('bank_put')).includes('000011112222'), '收款帳號設定也留紀錄（不留完整帳號）');
  assert.ok(l.audit.every((a) => a.at && a.kind), '每筆都有時間');
});

test('措施 5 通知：申請送出 → 管理者鈴鐺；申請被自動結案／管理者處理 → 會員鈴鐺各一則', async () => {
  const { hub, db, bob, andy } = await setup();
  await bankOn(hub, andy);
  await bankPaid(hub, bob, andy);
  clock += 60000;
  const rq = (await pj(hub, '/v1/subscribe/change', { t: bob, type: 'cancel', note: '太貴' })).j;
  const adm = db.prepare("SELECT * FROM user_notices WHERE email = 'andy@example.com' AND title LIKE '新申請：%'").all();
  assert.equal(adm.length, 1, '管理者鈴鐺');
  assert.match(adm[0].body, /太貴/);
  assert.ok(db.prepare("SELECT 1 FROM mail_out WHERE subject LIKE '%取消訂閱申請%'").get(), '站方信件進佇列');
  await pj(hub, '/v1/admin/feedback/set', { t: andy, kind: 'request', id: rq.id, status: 'done' });
  const mine = db.prepare("SELECT title FROM user_notices WHERE email = 'bob@example.com' AND title LIKE '%申請已%'").all().map((r) => r.title);
  assert.deepEqual(mine, ['你的取消訂閱申請已處理']);
  await pj(hub, '/v1/admin/feedback/set', { t: andy, kind: 'request', id: rq.id, status: 'new' });
  clock += 60000;
  const c2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, name: '鮑伯', id: c2.id, last5: '22222', date: '2026-10-11' });
  assert.ok(db.prepare("SELECT 1 FROM user_notices WHERE email = 'bob@example.com' AND title = '你的取消訂閱申請已結案'").get(), '被新訂單結案 → 會員收到結案通知');
});

/* ---------------------------------------------------------------- 2026-10-16 結帳加姓名＋性別（男／女），性別只存計數（法遵意見 gender_collection_1016 4-2 做法 A） */
const GOOD = { name: '鮑伯', gender: 'female', gender_consent: true };
test('結帳表單 form=2：姓名、性別、獨立同意都必填；性別只能 male／female；末 5 碼選填且只收 5 位數字；卡號一律拒收', async () => {
  const { hub, db, bob } = await setup();
  const base = { t: bob, plan: 'plus', period: 'month', back: BACK, recur: true, form: 2 };
  const e = async (x) => (await pj(hub, '/v1/pay/ecpay/create', { ...base, ...x }));
  assert.equal((await e({ gender: 'male', gender_consent: true })).j.error, 'need_name');
  assert.equal((await e({ name: '鮑伯' })).j.error, 'need_gender', 'Andy 10-16：性別先必填');
  assert.equal((await e({ name: '鮑伯', gender: 'female' })).j.error, 'need_gender_consent', '法遵：獨立勾選同意，沒勾不收');
  assert.equal((await e({ name: '鮑伯', gender: 'undisclosed', gender_consent: true })).j.error, 'bad_gender', '白名單只有男女');
  assert.equal((await e({ ...GOOD, last5: '1234' })).j.error, 'bad_last5');
  assert.equal((await e({ ...GOOD, last5: '4111111111111111' })).j.error, 'card_number', '卡號一律拒收');
  assert.equal((await e({ ...GOOD, last5: '4111 1111 1111 1111' })).j.error, 'card_number', '夾空白也擋');
  assert.equal((await e({ ...GOOD, name: '4111-1111-1111-1111' })).j.error, 'card_number', '姓名欄也擋');
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM orders').get().c, 0, '驗證失敗不開任何訂單');
  const ok = await e({ ...GOOD, last5: '12345' });
  assert.equal(ok.s, 200);
  const o = ord(db, ok.j.id);
  assert.deepEqual([o.payer_name, o.payer_last5, o.from_last5 || null], ['鮑伯', '12345', null], '綠界末 5 碼不能寫進 from_last5（那欄代表已回報匯款）');
  /* 舊版網頁（沒帶 form）仍可結帳：先部署 Worker 不能讓快取裡的舊前端壞掉 */
  assert.equal((await pj(hub, '/v1/pay/ecpay/create', { t: bob, plan: 'plus', period: 'month', back: BACK, recur: true })).s, 200);
  assert.ok(!db.prepare("SELECT name FROM pragma_table_info('users')").all().some((c) => c.name === 'gender'), '會員表沒有性別欄（不跟會員綁定）');
});

test('性別只存計數：開通那一刻才算進計數並清掉訂單上的暫存；未付款不算；重複通知不重複算；管理者清單與會員輸出都沒有性別', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob, { recur: false, form: 2, ...GOOD });
  assert.equal(ord(db, c.id).gender, 'female', '付款前只是暫存');
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM gender_counts').get().c, 0, '未付款不計');
  await notify(hub, c.id, 299);
  await notify(hub, c.id, 299);
  assert.equal(ord(db, c.id).gender, null, '開通後暫存清掉：訂單不再綁性別');
  const rows = db.prepare('SELECT * FROM gender_counts').all();
  assert.deepEqual(rows.map((r) => [r.g, r.n]), [['female', 1]], '只算一次');
  assert.deepEqual(Object.keys(rows[0]).sort(), ['day', 'g', 'n'], '計數表沒有 uid／email／訂單');
  const adm = (await pj(hub, '/v1/admin/pay/list', { t: andy })).j;
  assert.ok(!JSON.stringify(adm).includes('"gender"'), '管理者訂單清單不含性別');
  assert.ok(!JSON.stringify((await pj(hub, '/v1/pay/my', { t: bob })).j).includes('"gender"'));
});

test('銀行轉帳回報 form=2：性別與獨立同意必填；管理者確認入帳後才算進計數', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '812', account: '1234567890', holder: '哩股' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  const rp = { t: bob, id: c.id, name: '鮑伯', last5: '54321', date: '2026-10-11', form: 2 };
  assert.equal((await pj(hub, '/v1/pay/bank/report', rp)).j.error, 'need_gender');
  assert.equal((await pj(hub, '/v1/pay/bank/report', { ...rp, gender: 'male' })).j.error, 'need_gender_consent');
  assert.equal((await pj(hub, '/v1/pay/bank/report', { ...rp, gender: 'other', gender_consent: true })).j.error, 'bad_gender');
  assert.equal((await pj(hub, '/v1/pay/bank/report', { ...rp, last5: '4111111111111111', gender: 'male', gender_consent: true })).j.error, 'card_number');
  assert.equal((await pj(hub, '/v1/pay/bank/report', { ...rp, gender: 'male', gender_consent: true })).s, 200);
  assert.equal(db.prepare('SELECT COUNT(*) AS c FROM gender_counts').get().c, 0, '回報還沒入帳，不計');
  const cf = await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 299 });
  assert.equal(cf.s, 200, JSON.stringify(cf.j));
  assert.deepEqual(db.prepare('SELECT g, n FROM gender_counts').all().map((r) => [r.g, r.n]), [['male', 1]]);
  assert.equal(ord(db, c.id).gender, null);
});

test('男女用量比例：/v1/admin/stats 只回彙總人數；舊訂單（沒有性別）＝已付款數 − 男 − 女；非管理者拿不到', async () => {
  const { hub, db, bob, andy } = await setup();
  const c = await ecCreate(hub, bob, { recur: false, form: 2, ...GOOD });
  await notify(hub, c.id, 299);
  db.prepare("INSERT INTO gender_counts (day, g, n) VALUES ('2026-10-01', 'male', 4)").run();
  const old = ord(db, c.id);
  db.prepare("INSERT INTO orders (id, uid, email, plan, plan_name, period, amount, method, status, applied, created, updated) VALUES ('LGOLD000000001', 'u9', 'old@example.com', 'plus', 'Plus', 'month', 299, 'bank', 'active', 1, 1, 1)").run();
  const j = (await pj(hub, '/v1/admin/stats', { t: andy, days: 7 })).j;
  assert.deepEqual(j.gender, { male: 4, female: 1, paid: 2, unset: 0, since: '2026-10-01' });
  assert.equal(old.applied, 1);
  assert.equal((await pj(hub, '/v1/admin/stats', { t: bob, days: 7 })).s, 403);
});

test('稽核：綠界回傳／通知驗章失敗時，事件紀錄只留白名單欄位，不留卡號資訊（card4no／card6no 等）', async () => {
  const { hub, db, bob } = await setup();
  const c = await ecCreate(hub, bob);
  const bad = await form(hub, '/v1/pay/ecpay/notify', { MerchantTradeNo: c.id, RtnCode: '1', TradeAmt: '299', card6no: '411111', card4no: '1111', CardNumber: '4111111111111111', Extra: 'x'.repeat(50) }, false);
  assert.equal(bad.status, 400);
  const ev = db.prepare("SELECT detail FROM pay_events WHERE kind = 'notify_badmac'").all().map((r) => r.detail).join('|');
  assert.ok(ev.includes('MerchantTradeNo') && ev.includes('299'), ev);
  for (const w of ['card6no', 'card4no', '411111', '1111', 'CardNumber', 'Extra']) assert.ok(!ev.includes(w), w + ' 不該出現在事件紀錄：' + ev);
});
