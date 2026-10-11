/* 本機的「假 account-api ＋ 假 Google」—— 給 scripts/_uitest.py 走完整的登入／同步／管理頁流程。
 *
 * 用法：node workers/account-api/devserver.mjs --port 8790 --origin http://127.0.0.1:8767
 *
 * 跑的是**真的 worker.js**（同一支會部署到 Cloudflare 的程式），只有兩樣是假的：
 *   · Durable Object 的 SQLite → node:sqlite（harness.mjs）
 *   · Google：/__g/auth 是一頁有兩個帳號按鈕的假登入頁（Andy＝管理者、Bob＝一般會員），
 *             /__g/token 依授權碼回 id_token，並且真的驗 PKCE（code_verifier 的 SHA-256 要等於 code_challenge）。
 * 沒驗到的：真的 Google 登入頁（容器連不到 Google）、Cloudflare 的實際部署。
 */
import http from 'node:http';
import { createHash, randomBytes } from 'node:crypto';
import { makeHub } from './harness.mjs';
import { ecpayMac, ECPAY_STAGE } from './pay.js';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const PORT = +arg('port', 8790), ORIGIN = arg('origin', 'http://127.0.0.1:8767');
const BASE = `http://127.0.0.1:${PORT}`;
const CID = 'dev-client.apps.googleusercontent.com';
const CLOCK = { off: 0 };
const { hub } = makeHub({
  __now: () => Date.now() + CLOCK.off,
  ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 'dev', ADMIN_EMAILS: 'andy@example.com',
  GOOGLE_AUTH_URL: BASE + '/__g/auth', GOOGLE_TOKEN_URL: BASE + '/__g/token',
  ECPAY_STAGE_HOST: BASE,   // 2026-10-11：綠界改打下面的「假綠界」（pay.js 只收 127.0.0.1）
});
const codes = new Map();
const PEOPLE = { andy: ['andy@example.com', 'Andy 測試'], bob: ['bob@example.com', 'Bob 訪客'] };
/* --person key=email=名字（可重複）：驗收要用的額外假帳號（例如功能權限那段的測試帳號）。
   刻意由 _uitest.py 從命令列帶進來、不寫死在這裡 —— 測試用的真實 email 只准出現在驗收的假資料裡（DECISIONS #288）。*/
process.argv.forEach((a, i) => {
  if (a !== '--person') return;
  const [k, email, name] = String(process.argv[i + 1] || '').split('=');
  if (/^[a-z0-9]{1,12}$/.test(k || '') && /@/.test(email || '')) PEOPLE[k] = [email, name || email];
});
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');

async function fakeGoogle(url, req, res, body) {
  if (url.pathname === '/__g/auth') {
    const q = url.searchParams;
    const links = Object.entries(PEOPLE).map(([k, [email, name]]) => {
      const code = randomBytes(12).toString('base64url');
      codes.set(code, { email, name, nonce: q.get('nonce'), challenge: q.get('code_challenge'), aud: q.get('client_id') });
      const to = new URL(q.get('redirect_uri')); to.searchParams.set('code', code); to.searchParams.set('state', q.get('state'));
      return `<p><a id="as-${k}" href="${to.href}">以 ${name}（${email}）登入</a></p>`;
    }).join('');
    const cancel = new URL(q.get('redirect_uri')); cancel.searchParams.set('error', 'access_denied'); cancel.searchParams.set('state', q.get('state'));
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    return res.end(`<!doctype html><meta charset="utf-8"><title>假的 Google 登入</title><h1>選擇帳號（測試用）</h1>${links}<p><a id="cancel" href="${cancel.href}">取消</a></p>`);
  }
  if (url.pathname === '/__g/token') {
    const p = new URLSearchParams(body), c = codes.get(p.get('code'));
    codes.delete(p.get('code'));
    const ok = c && createHash('sha256').update(p.get('code_verifier') || '').digest('base64url') === c.challenge;
    if (!ok) { res.writeHead(400, { 'content-type': 'application/json' }); return res.end('{"error":"invalid_grant"}'); }
    const claims = { iss: 'https://accounts.google.com', aud: c.aud, sub: 'dev-' + c.email, email: c.email, email_verified: true,
      name: c.name, picture: '', exp: Math.floor(Date.now() / 1000) + 3600, nonce: c.nonce };
    res.writeHead(200, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ id_token: 'h.' + b64u(claims) + '.s', access_token: 'x' }));
  }
  res.writeHead(404); res.end();
}

/* ---------------------------------------------------------------- 假綠界（2026-10-11 結帳與付款1011 驗收用）
   跟真的綠界一樣：收到的表單先驗 CheckMacValue，回應也簽 CheckMacValue（用官方公開的測試 HashKey／HashIV）。
   付款頁三個鈕：
     #ecPay       付款成功 → 伺服器對伺服器送 ReturnURL → 瀏覽器 POST 回 OrderResultURL（正常流程）
     #ecPaySkip   付款成功，但 ReturnURL 漏送、也不走 OrderResultURL（直接回 ClientBackURL）→ 只能靠前端輪詢查單／排程補開通
     #ecCancel    不付款，回網站
   GET /__ecpay/state?id=…  看這筆在假綠界的狀態；POST /__cron  手動觸發一次排程（paySweep）；/__clock?days=N 把時鐘往後撥。*/
const EC = { trades: new Map() };
const ecSign = async (p) => { const o = { MerchantID: ECPAY_STAGE.id, ...p }; o.CheckMacValue = await ecpayMac(o, ECPAY_STAGE.key, ECPAY_STAGE.iv); return o; };
const ecTpe = () => new Date(Date.now() + CLOCK.off + 8 * 3600 * 1000).toISOString().slice(0, 19).replace('T', ' ').replace(/-/g, '/');
const escH = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const autoPost = (action, fields) => `<!doctype html><meta charset="utf-8"><form id="f" method="post" action="${escH(action)}">${Object.entries(fields).map(([k, v]) => `<input type="hidden" name="${escH(k)}" value="${escH(v)}">`).join('')}</form><script>document.getElementById('f').submit()</script>`;
async function fakeEcpay(url, req, res, body) {
  const f = Object.fromEntries(new URLSearchParams(body));
  const send = (code, type, txt) => { res.writeHead(code, { 'content-type': type + '; charset=utf-8' }); res.end(txt); };
  if (req.method === 'POST' && url.pathname !== '/__ecpay/go') {
    if ((await ecpayMac(f, ECPAY_STAGE.key, ECPAY_STAGE.iv)) !== f.CheckMacValue) return send(400, 'text/plain', 'CheckMacValue Error');
  }
  if (url.pathname === '/Cashier/AioCheckOut/V5') {
    EC.trades.set(f.MerchantTradeNo, { f, status: '0', n: 0 });
    return send(200, 'text/html', `<!doctype html><meta charset="utf-8"><title>假的綠界付款頁</title><body style="font:16px system-ui;padding:24px">
      <h1>假的綠界付款頁（測試）</h1><p id="ecInfo">訂單 ${escH(f.MerchantTradeNo)}・NT$ ${escH(f.TotalAmount)}・${escH(f.ChoosePayment)}${f.PeriodType ? '・定期定額 ' + escH(f.PeriodType) : ''}</p>
      <form method="post" action="/__ecpay/go"><input type="hidden" name="id" value="${escH(f.MerchantTradeNo)}">
      <button id="ecPay" name="mode" value="ok">付款成功</button> <button id="ecPaySkip" name="mode" value="skip">付款成功（ReturnURL 漏送）</button> <button id="ecCancel" name="mode" value="cancel">取消付款</button></form>`);
  }
  if (url.pathname === '/__ecpay/go') {
    const t = EC.trades.get(f.id); if (!t) return send(404, 'text/plain', 'no trade');
    if (f.mode === 'cancel') { res.writeHead(303, { Location: t.f.ClientBackURL }); return res.end(); }
    t.status = '1'; t.n = 1; t.paidAt = ecTpe();
    if (f.mode === 'ok') {
      const n = await ecSign({ MerchantTradeNo: f.id, RtnCode: '1', RtnMsg: '交易成功', TradeNo: 'T' + f.id, TradeAmt: t.f.TotalAmount, PaymentDate: t.paidAt, PaymentType: 'Credit_CreditCard', PaymentTypeChargeFee: '5', TradeDate: t.paidAt, SimulatePaid: '0', gwsr: '12345' });
      const r = await hub.fetch(new Request(BASE + new URL(t.f.ReturnURL).pathname, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(n).toString() }));
      t.notify = await r.text();
      const back = await ecSign({ MerchantTradeNo: f.id, RtnCode: '1', RtnMsg: '交易成功', TradeNo: 'T' + f.id, TradeAmt: t.f.TotalAmount, PaymentDate: t.paidAt, PaymentType: 'Credit_CreditCard' });
      return send(200, 'text/html', autoPost(t.f.OrderResultURL, back));
    }
    res.writeHead(303, { Location: t.f.ClientBackURL }); return res.end();
  }
  if (url.pathname === '/__ecpay/state') { const t = EC.trades.get(url.searchParams.get('id')); return send(200, 'application/json', JSON.stringify(t ? { status: t.status, n: t.n, notify: t.notify || '', recur: !!t.f.PeriodType } : null)); }
  if (url.pathname === '/Cashier/QueryTradeInfo/V5') {
    const t = EC.trades.get(f.MerchantTradeNo);
    const o = await ecSign({ MerchantTradeNo: f.MerchantTradeNo, TradeNo: 'T' + f.MerchantTradeNo, TradeAmt: t ? t.f.TotalAmount : '0', TradeStatus: t ? t.status : '0', PaymentDate: (t && t.paidAt) || '', PaymentType: 'Credit_CreditCard', HandlingCharge: '0' });
    return send(200, 'text/plain', new URLSearchParams(o).toString());
  }
  if (url.pathname === '/Cashier/QueryCreditCardPeriodInfo') {
    const t = EC.trades.get(f.MerchantTradeNo);
    return send(200, 'application/json', JSON.stringify({ MerchantID: ECPAY_STAGE.id, MerchantTradeNo: f.MerchantTradeNo, RtnCode: 1, PeriodType: 'M', Frequency: 1, ExecTimes: 99, PeriodAmount: t ? +t.f.TotalAmount : 0, amount: t ? +t.f.TotalAmount : 0, gwsr: 1, process_date: (t && t.paidAt) || '', TotalSuccessTimes: t ? t.n : 0, ExecStatus: t && t.cancelled ? '0' : '1', ExecLog: [] }));
  }
  if (url.pathname === '/Cashier/CreditCardPeriodAction') {
    const t = EC.trades.get(f.MerchantTradeNo); if (t) t.cancelled = true;
    return send(200, 'text/plain', new URLSearchParams(await ecSign({ MerchantTradeNo: f.MerchantTradeNo, RtnCode: t ? '1' : '0', RtnMsg: t ? '成功' : '查無訂單' })).toString());
  }
  if (url.pathname === '/CreditDetail/DoAction') return send(200, 'text/plain', new URLSearchParams(await ecSign({ MerchantTradeNo: f.MerchantTradeNo, TradeNo: f.TradeNo, RtnCode: '1', RtnMsg: '成功' })).toString());
  send(404, 'text/plain', 'no');
}

http.createServer(async (req, res) => {
  const chunks = []; for await (const ch of req) chunks.push(ch);
  const body = Buffer.concat(chunks).toString('utf8');
  const url = new URL(req.url, BASE);
  try {
    if (url.pathname.startsWith('/__g/')) return await fakeGoogle(url, req, res, body);
    if (url.pathname.startsWith('/__ecpay/') || url.pathname.startsWith('/Cashier/') || url.pathname.startsWith('/CreditDetail/')) return await fakeEcpay(url, req, res, body);
    if (url.pathname === '/__cron') { const r = await hub.fetch(new Request('https://internal.cron/cron/pay-sweep', { method: 'POST' })); res.writeHead(200, { 'content-type': 'application/json' }); return res.end(await r.text()); }
    /* 驗收用：把時鐘往後撥（到期降級）——只有本機 devserver 有 */
    if (url.pathname === '/__clock') { CLOCK.off += (+url.searchParams.get('days') || 0) * 86400000; res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ now: Date.now() + CLOCK.off })); }
    /* 驗收用（流量批次1006）：直接讀每日計數表，不必登入管理者就能比對「送了幾筆、Worker 記了幾筆」。只有本機 devserver 有 */
    if (url.pathname === '/__online') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ n: hub.onlineCount() })); }
    if (url.pathname === '/__usage') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(hub.q('SELECT k, SUM(n) AS n FROM usage GROUP BY k'))); }
    const r = await hub.fetch(new Request(url.href, { method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : body }));
    if (process.env.DEV_LOG) console.log(req.method, url.pathname, r.status, 'origin=' + (req.headers.origin || '-'), 'ct=' + (req.headers['content-type'] || '-'), body.slice(0, 120));
    const h = {}; r.headers.forEach((v, k) => { h[k] = v; });
    res.writeHead(r.status, h); res.end(Buffer.from(await r.arrayBuffer()));
  } catch (e) { res.writeHead(500); res.end(String(e)); }
}).listen(PORT, '127.0.0.1', () => console.log(`account devserver ${BASE}（允許 ${ORIGIN}）`));
