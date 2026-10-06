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

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const PORT = +arg('port', 8790), ORIGIN = arg('origin', 'http://127.0.0.1:8767');
const BASE = `http://127.0.0.1:${PORT}`;
const CID = 'dev-client.apps.googleusercontent.com';
const { hub } = makeHub({
  ALLOWED_ORIGINS: ORIGIN, GOOGLE_CLIENT_ID: CID, GOOGLE_CLIENT_SECRET: 'dev', ADMIN_EMAILS: 'andy@example.com',
  GOOGLE_AUTH_URL: BASE + '/__g/auth', GOOGLE_TOKEN_URL: BASE + '/__g/token',
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

http.createServer(async (req, res) => {
  const chunks = []; for await (const ch of req) chunks.push(ch);
  const body = Buffer.concat(chunks).toString('utf8');
  const url = new URL(req.url, BASE);
  try {
    if (url.pathname.startsWith('/__g/')) return await fakeGoogle(url, req, res, body);
    /* 驗收用（流量批次1006）：直接讀每日計數表，不必登入管理者就能比對「送了幾筆、Worker 記了幾筆」。只有本機 devserver 有 */
    if (url.pathname === '/__online') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify({ n: hub.onlineCount() })); }
    if (url.pathname === '/__usage') { res.writeHead(200, { 'content-type': 'application/json' }); return res.end(JSON.stringify(hub.q('SELECT k, SUM(n) AS n FROM usage GROUP BY k'))); }
    const r = await hub.fetch(new Request(url.href, { method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : body }));
    if (process.env.DEV_LOG) console.log(req.method, url.pathname, r.status, 'origin=' + (req.headers.origin || '-'), 'ct=' + (req.headers['content-type'] || '-'), body.slice(0, 120));
    const h = {}; r.headers.forEach((v, k) => { h[k] = v; });
    res.writeHead(r.status, h); res.end(Buffer.from(await r.arrayBuffer()));
  } catch (e) { res.writeHead(500); res.end(String(e)); }
}).listen(PORT, '127.0.0.1', () => console.log(`account devserver ${BASE}（允許 ${ORIGIN}）`));
