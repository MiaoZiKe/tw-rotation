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
  for (const bad of [{ last5: '123' }, { last5: '12345', date: '2026/10/11' }, { last5: '12345', date: '2026-10-11', amount: 0 }]) {
    assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, date: '2026-10-11', amount: 2990, ...bad })).s, 400, JSON.stringify(bad));
  }
  const rp = await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '54321', date: '2026-10-11', amount: 2990, note: '公司帳戶' });
  assert.equal(rp.j.order.status, 'review');
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
  /* 方案異動規則：年繳 Plus 生效中 → 不能再買月繳、不能重買同一個，只能升 Pro 年繳 */
  const blk = async (plan, period) => (await pj(hub, '/v1/pay/bank/create', { t: bob, plan, period })).j;
  assert.deepEqual([(await blk('plus', 'month')).reason, (await blk('plus', 'year')).reason, (await blk('pro', 'month')).reason], ['year_to_month', 'same_active', 'year_to_month']);
  assert.equal((await pj(hub, '/v1/pay/quote', { t: bob, plan: 'plus', period: 'month' })).j.blocked, 'year_to_month', '報價也帶出擋下原因，前端據此反灰');
  assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).s, 200, '年繳可升 Pro 年繳');
  /* 到期前 7 天內才能續訂同方案同週期；上面 4 次之後再灌到第 6 筆 → 24 小時上限 */
  const soon = clock + 3 * 86400000;
  db.prepare("UPDATE perm SET expires = ? WHERE email = 'bob@example.com'").run(soon);
  db.prepare("UPDATE orders SET grant_to = ? WHERE id = ?").run(soon, c.id);
  for (let i = 0; i < 3; i++) {   // 前面已開 2 筆（原單＋Pro 年繳），再 3 筆到 5 筆上限
    assert.equal((await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).s, 200);
    db.prepare("UPDATE orders SET status = 'review' WHERE method = 'bank' AND status = 'pending'").run();
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

test('匯款回報不可修改：重送＝新增一筆、上一筆作廢（已有最新匯款資料）；確認／退回後不能再回報；會員看得到自己的取消／退款申請', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '11111', date: '2026-10-11', amount: 2000 });
  clock += 60000;
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '22222', date: '2026-10-11', amount: 2990 });
  const rs = JSON.parse(ord(db, c.id).reports);
  assert.deepEqual(rs.map((r) => [r.last5, r.amount, r.state]), [['11111', 2000, 'void'], ['22222', 2990, 'active']]);
  assert.equal(rs[0].voidWhy, '已有最新匯款資料');
  assert.deepEqual([ord(db, c.id).from_last5, ord(db, c.id).xfer_amount], ['22222', 2990], '訂單上是最新一筆');
  const mine = (await pj(hub, '/v1/pay/my', { t: bob })).j.orders.find((o) => o.id === c.id);
  assert.equal(mine.reports.length, 2, '會員看得到兩筆回報紀錄');
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: c.id, received: 2990 });
  assert.equal((await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '33333', date: '2026-10-11', amount: 1 })).s, 409, '開通後不能再回報');
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
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c1.id, last5: '12345', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c2x.id, last5: '12345', date: '2026-10-11', amount: 5268 });
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
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: a.id, last5: '10001', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });
  const b2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: b2.id, last5: '10002', date: '2026-10-11', amount: 5268 });
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
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: a.id, last5: '20001', date: '2026-10-11', amount: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });
  await pj(hub, '/v1/admin/pay/confirm', { t: andy, id: a.id, received: 299 });   // 重按不重複通知
  const b2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'pro', period: 'year' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: b2.id, last5: '20002', date: '2026-10-11', amount: 5268 });
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
  assert.equal((await pj(hub, '/v1/notices', { t: andy })).j.notices.filter((x) => x.kind === 'pay').length, 0);
  /* 寄信：排程送出、帶收件人 */
  globalThis.fetch = async (u, init) => { if (String(u).startsWith('https://api.resend.com')) { sent.push(JSON.parse(init.body)); return new Response('{}', { status: 200 }); } return realFetch(u, init); };
  try { await hub.payMailFlush(); } finally { globalThis.fetch = realFetch; }
  assert.ok(sent.length >= 4 && sent.every((m) => m.to[0] === 'bob@example.com' && /^【哩股哩股】/.test(m.subject)), JSON.stringify(sent.map((m) => m.subject)));
  assert.equal(db.prepare("SELECT COUNT(*) AS c FROM mail_out WHERE status = 'pending'").get().c, 0);
});

test('方案異動：月繳 Plus 可升 Plus 年繳／Pro；不可降級；Pro 年繳什麼都不能再買', async () => {
  const { hub, db, bob, andy } = await setup();
  await pj(hub, '/v1/admin/pay/bank/put', { t: andy, bank_name: '測試銀行', bank_code: '999', account: '000011112222', holder: '測試戶名' });
  const buy = async (plan, period) => {
    const c = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan, period })).j;
    if (!c.ok) return c;
    const l5 = String(10000 + Math.floor(Math.random() * 89999));   // 每次不同的入帳（同末 5 碼＋同日期會被當成重複入帳擋下，見下一個測試）
    await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: l5, date: '2026-10-11', amount: c.amount });
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
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '54321', date: '2026-10-11', amount: 299 });
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id })).s, 400, '要寫原因');
  assert.equal((await pj(hub, '/v1/admin/pay/reject', { t: andy, id: c.id, reason: '查無入帳' })).s, 200);
  assert.deepEqual([ord(db, c.id).status, ord(db, c.id).reject_reason, ord(db, c.id).applied], ['rejected', '查無入帳', 0]);
  assert.equal((await permOf(hub, bob)).plan, 'free');
  assert.equal((await pj(hub, '/v1/admin/pay/note', { t: andy, id: c.id, note: '已電話聯絡' })).s, 200);
  assert.equal(ord(db, c.id).admin_note, '已電話聯絡');
  /* 確認一筆 → 到期前 7 天 → 提醒（stage 7）；前 1 天（stage 1）；管理區「即將到期的轉帳會員」 */
  const c2 = (await pj(hub, '/v1/pay/bank/create', { t: bob, plan: 'plus', period: 'month' })).j;
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c2.id, last5: '54321', date: '2026-10-11', amount: 299 });
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
  await pj(hub, '/v1/pay/bank/report', { t: bob, id: c.id, last5: '54321', date: '2026-10-11', amount: 299 });
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
  assert.equal((await pj(hub, '/v1/admin/pay/refund', { t: andy, id: c.id, rid: 'r-000000003', amount: 1, last5: '11111', date: '2026-10-11' })).s, 400, '已全額退，再退擋下');
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
