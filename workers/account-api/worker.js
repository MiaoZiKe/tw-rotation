/* account-api — 會員登入、自選清單雲端同步、使用統計、線上人數（Cloudflare Worker ＋ Durable Object）
 *
 * 架構與取捨寫在 DECISIONS #270，設定步驟在 docs/login_setup.md，事件清單在 docs/account_analytics.md。
 *
 * 為什麼是 Worker ＋ Durable Object，而不是 Firebase（摘要，細節在 DECISIONS #270）
 * --------------------------------------------------------------------------
 *   · Andy 公司網路：`*.workers.dev` 已經實際在用（即時報價代理 tw-quote），連得到是已知事實；
 *     Firebase 要連 firebaseio.com（WebSocket）、apis.google.com（登入 iframe）、<專案>.firebaseapp.com，連不連得到未知。
 *   · 前端零 SDK：全部是 fetch，不必在 site/vendor/ 放幾百 KB 的 Firebase。
 *   · 保存期限要「真的會刪」：Durable Object 的 alarm 免費；Firebase 免費方案沒有排程函式（Cloud Functions 要 Blaze＝綁卡）。
 *   · 「統計只能遞增、不能讀」「管理者才讀得到」由這支程式在伺服器端執行，管理者名單是 Worker Secret，不進 repo。
 *   · 部署沿用已經設好的 CLOUDFLARE_API_TOKEN（Durable Object 跟著 Worker 一起部署，不必另外建資料庫）。
 *
 * 資料放哪：單一個 Durable Object（名字 'hub'）裡的 SQLite。一個站、個位數到數百人同時在線，一個實例綽綽有餘，
 * 而且單一實例＝強一致（線上人數、清單版本號不會因為讀到舊副本而錯）。
 *
 * ★ 存取控制（等同 Firebase 的安全規則；每一條都有 tests/account.test.mjs 驗「允許」與「拒絕」）
 *   R1 自選清單：只能讀寫「權杖裡那個 uid」自己的那一份 —— API 根本不收 uid 參數，沒有「讀別人」的路徑。
 *   R2 使用統計：任何人（含訪客）只能「遞增」白名單內的計數，一次最多 +50、最多 40 項；沒有任何「讀」的端點給一般人。
 *   R3 報表、線上名單、會員名單：只有 email 在 ADMIN_EMAILS（Worker Secret）裡的已驗證帳號讀得到。
 *   R4 線上總人數：預設公開（只有數字），管理者可在 #admin 關掉；關掉後只回給管理者。
 *   R5 權杖：HMAC-SHA256 簽章＋到期時間＋版本號；刪除帳號後舊權杖立即失效（查不到使用者就拒絕）。
 *   R6 登入：OAuth 2.0 授權碼＋PKCE（S256）＋ state ＋ nonce ＋ 綁定瀏覽器的 cookie；return 網址只准白名單網域。
 *
 * 蒐集與保存（隱私權政策照這裡寫，改這裡要一起改 site/legal.js 與 site/account.js 的告知文字）
 *   · 會員：Google 顯示名稱、email、大頭貼網址、Google 帳號識別碼的雜湊（不存原值）、建立與最後使用時間。
 *     保存到本人刪除，或連續 24 個月沒有使用就自動刪除。
 *   · 自選清單：清單名稱＋股票代號。**不存張數、成本、損益**（CLAUDE.md 第 5 條）。
 *   · 使用統計：每天每一項的「次數」而已，不含任何識別碼、不存 IP、不存單次點擊。保留 13 個月。
 *   · 線上：一個分頁一組隨機代碼（關掉分頁就失效）＋目前在哪一頁＋（登入者）uid。離線即刪（最多 3 分鐘）。
 */

/* ---------------------------------------------------------------- 可調參數 */
const TOKEN_DAYS = 60;                 // 權杖效期；剩不到一半時 /v1/me 會換一張新的
const ONLINE_WINDOW_MS = 150 * 1000;   // 多久沒心跳就不算在線（前端 60 秒一跳，容許漏一次）
const PRESENCE_TTL_MS = 180 * 1000;    // 超過這個時間的在線紀錄直接刪（「離線即刪」的上限）
const LOGIN_TTL_MS = 10 * 60 * 1000;   // 一次登入流程（從按鈕到拿到權杖）最長 10 分鐘
const USAGE_KEEP_MONTHS = 13;          // 使用統計彙總保留 13 個月
const USER_IDLE_DAYS = 730;            // 會員連續 24 個月沒用就刪
const MAX_TABS = 5, MAX_CODES = 50, MAX_NAME = 12;
const MAX_EV_KEYS = 40, MAX_EV_INC = 50;
const RATE_PER_MIN = 240;              // 同一個 IP 每分鐘最多幾次心跳（公司 NAT 後面可能有幾十人共用一個 IP）
const ALARM_EVERY_MS = 60 * 60 * 1000; // 每小時清一次過期資料

/* 使用統計白名單（R2）。改這裡要一起改 site/account.js 的 EVENTS 與 docs/account_analytics.md —— 測試會比對三邊一致。*/
export const VIEWS = ['overview', 'flow', 'industry', 'heatmap', 'market', 'season', 'delivery', 'stock', 'legal', 'watch', 'other'];
export const EVENTS = [
  'session', 'session_login', 'login', 'logout',
  'search', 'watch_add', 'watch_remove', 'watch_tab_new', 'watch_panel',
  'stock_tab', 'k_period', 'ai_tab', 'open_3d', 'zoom', 'how', 'theme_toggle',
  'events_drawer', 'mtf', 'indicators', 'draw', 'm_seg',
];
const EV_KEYS = new Set([...VIEWS.map((v) => 'pv:' + v), ...EVENTS.map((e) => 'ev:' + e)]);

const GOOGLE_AUTH = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN = 'https://oauth2.googleapis.com/token';
const GOOGLE_ISS = ['accounts.google.com', 'https://accounts.google.com'];

/* ---------------------------------------------------------------- 小工具 */
const enc = new TextEncoder();
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64uStr = (s) => b64u(enc.encode(s));
const unb64u = (s) => { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; return atob(s); };
const rand = (n = 32) => b64u(crypto.getRandomValues(new Uint8Array(n)));
const sha256 = async (s) => b64u(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const safeEq = (a, b) => { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i); return r === 0; };
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
/* 台北日期（統計以台北的一天為單位；容器與 Cloudflare 都是 UTC） */
const tpeDay = (ms) => new Date(ms + 8 * 3600 * 1000).toISOString().slice(0, 10);
const cleanName = (s) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f<>]/g, '').trim().slice(0, MAX_NAME);
const CODE_RE = /^[0-9A-Z]{4,6}$/;

export default {
  async fetch(req, env) {
    /* 全部轉給同一個 Durable Object —— 單一實例＝強一致，也讓「權杖簽章金鑰」只存在一個地方。*/
    const id = env.HUB.idFromName('hub');
    return env.HUB.get(id).fetch(req);
  },
};

export class Hub {
  constructor(state, env) {
    this.state = state; this.env = env || {};
    this.sql = state.storage.sql;
    this.rate = new Map();          // IP → [分鐘, 次數]（只在記憶體，不落地、不寫進資料庫）
    this.lastClean = 0;
    this.q('CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)');
    this.q('CREATE TABLE IF NOT EXISTS users (uid TEXT PRIMARY KEY, subh TEXT UNIQUE, email TEXT, name TEXT, pic TEXT, created INTEGER, seen INTEGER, tv INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS lists (uid TEXT PRIMARY KEY, data TEXT, rev INTEGER, updated INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS usage (day TEXT, k TEXT, n INTEGER, PRIMARY KEY (day, k))');
    this.q('CREATE TABLE IF NOT EXISTS presence (sid TEXT PRIMARY KEY, uid TEXT, route TEXT, seen INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS logins (n TEXT PRIMARY KEY, state TEXT UNIQUE, verifier TEXT, nonce TEXT, mode TEXT, ret TEXT, exp INTEGER, tok TEXT, uid TEXT)');
    /* 權杖簽章金鑰：第一次啟動時隨機產生、存在這個 Durable Object 自己的儲存裡。
       不進 repo、不是 GitHub Secret、Andy 也不用產生 —— 少一個要人記得設的東西。
       要讓所有人強制重新登入：刪掉這一列（或換 Worker 名稱）即可。*/
    if (!this.q('SELECT v FROM kv WHERE k = ?', 'hmac').length) this.q('INSERT INTO kv (k, v) VALUES (?, ?)', 'hmac', rand(32));
    if (state.storage.getAlarm && state.storage.setAlarm) {
      Promise.resolve(state.storage.getAlarm()).then((a) => { if (a == null) return state.storage.setAlarm(this.now() + ALARM_EVERY_MS); }).catch(() => {});
    }
  }

  now() { return this.env.__now ? this.env.__now() : Date.now(); }
  q(sql, ...args) { return this.sql.exec(sql, ...args).toArray(); }
  kv(k) { const r = this.q('SELECT v FROM kv WHERE k = ?', k); return r.length ? r[0].v : null; }
  setKv(k, v) { this.q('INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v', k, String(v)); }

  origins() { return String(this.env.ALLOWED_ORIGINS || 'https://miaozike.github.io').split(/[\s,]+/).filter(Boolean); }
  originOk(o) { return !!o && this.origins().includes(o); }
  admins() { return String(this.env.ADMIN_EMAILS || '').toLowerCase().split(/[\s,;]+/).filter(Boolean); }
  isAdmin(u) { return !!u && !!u.email && this.admins().includes(String(u.email).toLowerCase()); }
  configured() { return !!(this.env.GOOGLE_CLIENT_ID && this.env.GOOGLE_CLIENT_SECRET); }
  publicOnline() { return this.kv('public_online') !== '0'; }

  /* ---------------------------------------------------------------- 權杖（R5）*/
  async hmac(msg) {
    const key = await crypto.subtle.importKey('raw', enc.encode(this.kv('hmac')), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    return b64u(await crypto.subtle.sign('HMAC', key, enc.encode(msg)));
  }
  async sign(uid, tv) {
    const exp = Math.floor(this.now() / 1000) + TOKEN_DAYS * 86400;
    const body = `v1.${uid}.${exp}.${tv}`;
    return body + '.' + (await this.hmac(body));
  }
  /* 回 { user, exp } 或 null。任何一項不對都是 null —— 呼叫端一律當「沒登入」。*/
  async verify(tok) {
    if (typeof tok !== 'string' || tok.length > 300) return null;
    const p = tok.split('.');
    if (p.length !== 5 || p[0] !== 'v1') return null;
    const body = p.slice(0, 4).join('.');
    if (!safeEq(p[4], await this.hmac(body))) return null;
    const exp = +p[2];
    if (!(exp > this.now() / 1000)) return null;
    const u = this.q('SELECT * FROM users WHERE uid = ?', p[1])[0];
    if (!u || String(u.tv) !== p[3]) return null;          // 刪除帳號（或換版本）後舊權杖立即失效
    return { user: u, exp };
  }
  pubUser(u) { return { name: u.name, email: u.email, pic: u.pic, admin: this.isAdmin(u) }; }

  /* ---------------------------------------------------------------- HTTP */
  cors(req, res) {
    const o = req.headers.get('Origin');
    if (this.originOk(o)) { res.headers.set('Access-Control-Allow-Origin', o); res.headers.set('Vary', 'Origin'); }
    return res;
  }
  json(req, obj, status = 200) {
    return this.cors(req, new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } }));
  }
  page(title, body, status = 200, extra = {}) {
    const h = new Headers({ 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer' });
    for (const [k, v] of Object.entries(extra)) h.append(k, v);
    return new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>`
      + `<body style="font:16px/1.6 system-ui,sans-serif;background:#0b1220;color:#e6edf6;display:grid;place-items:center;min-height:90vh;margin:0;padding:16px">`
      + `<main style="max-width:420px;text-align:center">${body}</main></body>`, { status, headers: h });
  }

  async fetch(req) {
    const url = new URL(req.url);
    const p = url.pathname;
    try {
      if (req.method === 'OPTIONS') {
        return this.cors(req, new Response(null, { status: 204, headers: { 'Access-Control-Allow-Methods': 'POST, GET', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Max-Age': '86400' } }));
      }
      if (p === '/health') return this.json(req, { ok: true, service: 'tw-rotation account-api', configured: this.configured(), admins: this.admins().length > 0 });
      if (req.method === 'GET' && p === '/auth/start') return await this.authStart(req, url);
      if (req.method === 'GET' && p === '/auth/callback') return await this.authCallback(req, url);
      if (req.method !== 'POST') return this.json(req, { error: 'not_found' }, 404);
      /* 所有 POST 都要從白名單網站發出（瀏覽器一定會帶 Origin）。這擋不住有心人用 curl 偽造，
         但擋得住「別的網站在背景偷偷替訪客打這支 API」（CSRF）。真正的權限檢查是下面每一支各自的權杖檢查。*/
      if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
      const raw = await req.text();
      if (raw.length > 16384) return this.json(req, { error: 'too_large' }, 413);
      let b; try { b = JSON.parse(raw || '{}'); } catch (e) { return this.json(req, { error: 'bad_json' }, 400); }
      if (!b || typeof b !== 'object' || Array.isArray(b)) return this.json(req, { error: 'bad_json' }, 400);
      switch (p) {
        case '/auth/redeem': return await this.redeem(req, b);
        case '/v1/beat': return await this.beat(req, b);
        case '/v1/me': return await this.me(req, b);
        case '/v1/lists/get': return await this.listsGet(req, b);
        case '/v1/lists/put': return await this.listsPut(req, b);
        case '/v1/delete': return await this.deleteMe(req, b);
        case '/v1/admin/stats': return await this.adminStats(req, b);
        case '/v1/admin/online': return await this.adminOnline(req, b);
        case '/v1/admin/settings': return await this.adminSettings(req, b);
        default: return this.json(req, { error: 'not_found' }, 404);
      }
    } catch (e) {
      return this.json(req, { error: 'server', detail: String(e && e.message || e).slice(0, 200) }, 500);
    }
  }

  /* ---------------------------------------------------------------- 登入（R6）
     流程：網站產生一次性的 n（只有網站自己知道）→ 開小視窗 /auth/start?n=… → Google → /auth/callback
     → Worker 用授權碼＋PKCE 換 id_token、建立權杖，存在 logins 表裡對應到 n → 網站拿 n 來 /auth/redeem 換走（只能換一次）。
     為什麼權杖不直接 postMessage 回去：Google 的登入頁會設 COOP，小視窗的 window.opener 可能被切斷；
     用 n 去換，不管 opener 在不在都拿得到，而且權杖從頭到尾不會出現在網址或跨視窗訊息裡。*/
  retOk(ret) {
    try { const u = new URL(ret); return this.originOk(u.origin) ? u : null; } catch (e) { return null; }
  }
  async authStart(req, url) {
    if (!this.configured()) return this.page('尚未設定', '<h2>登入功能尚未設定</h2><p>管理者還沒有完成 Google 登入的設定（docs/login_setup.md）。</p>', 503);
    const n = url.searchParams.get('n') || '', mode = url.searchParams.get('mode') === 'redirect' ? 'redirect' : 'popup';
    const ret = this.retOk(url.searchParams.get('ret') || '');
    if (!/^[A-Za-z0-9_-]{22,64}$/.test(n) || !ret) return this.page('登入失敗', '<h2>登入連結不正確</h2><p>請回到網站重新按「登入」。</p>', 400);
    this.cleanup();
    if (this.q('SELECT 1 FROM logins WHERE n = ?', n).length) return this.page('登入失敗', '<h2>這個登入連結已經用過</h2><p>請回到網站重新按「登入」。</p>', 400);
    const state = rand(24), verifier = rand(48), nonce = rand(16);
    this.q('INSERT INTO logins (n, state, verifier, nonce, mode, ret, exp) VALUES (?, ?, ?, ?, ?, ?, ?)', n, state, verifier, nonce, mode, ret.href, this.now() + LOGIN_TTL_MS);
    const cb = new URL('/auth/callback', url.origin).href;
    const g = new URL(this.env.GOOGLE_AUTH_URL || GOOGLE_AUTH);
    g.search = new URLSearchParams({
      client_id: this.env.GOOGLE_CLIENT_ID, redirect_uri: cb, response_type: 'code', scope: 'openid email profile',
      state, nonce, code_challenge: await sha256(verifier), code_challenge_method: 'S256', prompt: 'select_account',
    }).toString();
    const secure = url.protocol === 'https:' ? '; Secure' : '';
    return new Response(null, { status: 302, headers: {
      Location: g.href, 'cache-control': 'no-store',
      /* 綁定「同一個瀏覽器」：state 同時放在 cookie 裡，回來時兩邊要一致。
         防的是「攻擊者把他自己那次登入的回呼網址丟給你點」（login CSRF）。*/
      'Set-Cookie': `tw_oas=${state}; Path=/auth; HttpOnly; SameSite=Lax; Max-Age=600${secure}`,
    } });
  }
  async authCallback(req, url) {
    const fail = (msg, status = 400) => this.page('登入失敗', `<h2>登入沒有完成</h2><p>${esc(msg)}</p><p>可以關掉這個視窗，回到網站再試一次。</p>`, status,
      { 'Set-Cookie': 'tw_oas=; Path=/auth; Max-Age=0' });
    const state = url.searchParams.get('state') || '';
    const row = state ? this.q('SELECT * FROM logins WHERE state = ?', state)[0] : null;
    if (!row || row.exp < this.now() || row.tok) return fail('登入連結已過期或已經用過。');
    const ck = (req.headers.get('Cookie') || '').split(/;\s*/).find((c) => c.startsWith('tw_oas='));
    if (!ck || !safeEq(ck.slice(7), state)) return fail('瀏覽器驗證不符（請用同一個瀏覽器完成登入）。');
    if (url.searchParams.get('error')) { this.q('DELETE FROM logins WHERE n = ?', row.n); return fail('你取消了登入，或 Google 拒絕了這次登入。'); }
    const code = url.searchParams.get('code');
    if (!code) return fail('缺少授權碼。');
    const cb = new URL('/auth/callback', url.origin).href;
    const r = await fetch(this.env.GOOGLE_TOKEN_URL || GOOGLE_TOKEN, {
      method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ code, client_id: this.env.GOOGLE_CLIENT_ID, client_secret: this.env.GOOGLE_CLIENT_SECRET,
        redirect_uri: cb, grant_type: 'authorization_code', code_verifier: row.verifier }).toString(),
    });
    if (!r.ok) return fail('向 Google 換取登入資訊失敗（' + r.status + '）。', 502);
    const tj = await r.json();
    /* id_token 是直接從 Google 的 token 端點經 TLS 拿到的（不是經過瀏覽器轉交），
       依 OpenID Connect Core 1.0 §3.1.3.7 第 6 點，這種情況可用 TLS 驗證發行者、不必再驗簽章。
       其餘欄位照規定逐一檢查：發行者、對象、到期、nonce、email 已驗證。*/
    let c;
    try { c = JSON.parse(unb64u(String(tj.id_token || '').split('.')[1] || '')); } catch (e) { return fail('Google 回傳的資料格式不對。', 502); }
    const nowS = this.now() / 1000;
    if (!GOOGLE_ISS.includes(c.iss)) return fail('發行者不符。');
    if (c.aud !== this.env.GOOGLE_CLIENT_ID) return fail('用戶端不符。');
    if (!(c.exp > nowS)) return fail('登入資訊已過期。');
    if (!c.nonce || !safeEq(String(c.nonce), row.nonce)) return fail('驗證碼不符。');
    if (!c.sub) return fail('缺少帳號識別。');
    if (c.email_verified !== true && c.email_verified !== 'true') return fail('這個 Google 帳號的 email 尚未驗證。');
    /* Google 帳號識別碼（sub）不存原值，存「加上本站金鑰的雜湊」：資料庫外流時，拿不到可以跨站對應的 Google 識別碼。*/
    const subh = await this.hmac('sub:' + c.sub);
    const now = this.now();
    const name = String(c.name || c.email || '').slice(0, 60), email = String(c.email || '').slice(0, 120);
    const pic = /^https:\/\/[a-z0-9.-]+\.googleusercontent\.com\//.test(c.picture || '') ? String(c.picture).slice(0, 400) : '';
    let u = this.q('SELECT * FROM users WHERE subh = ?', subh)[0];
    if (u) this.q('UPDATE users SET email = ?, name = ?, pic = ?, seen = ? WHERE uid = ?', email, name, pic, now, u.uid);
    else { const uid = rand(12); this.q('INSERT INTO users (uid, subh, email, name, pic, created, seen, tv) VALUES (?, ?, ?, ?, ?, ?, ?, 1)', uid, subh, email, name, pic, now, now); }
    u = this.q('SELECT * FROM users WHERE subh = ?', subh)[0];
    const tok = await this.sign(u.uid, u.tv);
    this.q('UPDATE logins SET tok = ?, uid = ?, exp = ? WHERE n = ?', tok, u.uid, now + 3 * 60 * 1000, row.n);
    const clear = { 'Set-Cookie': 'tw_oas=; Path=/auth; Max-Age=0' };
    const ret = new URL(row.ret);
    if (row.mode === 'redirect') return new Response(null, { status: 302, headers: { Location: ret.href, 'cache-control': 'no-store', ...clear } });
    /* 小視窗模式：通知網站「好了，可以來換了」（訊息裡只有 n，沒有權杖），然後自己關掉。
       opener 被切斷也沒關係 —— 網站那邊本來就在輪詢 /auth/redeem。*/
    const msg = JSON.stringify({ type: 'tw-login', n: row.n }).replace(/</g, '\\u003c');
    return this.page('登入完成', `<h2>登入完成</h2><p>這個視窗會自動關閉；沒關的話可以直接關掉，回到網站。</p>`
      + `<script>try{window.opener&&window.opener.postMessage(${msg},${JSON.stringify(ret.origin)})}catch(e){}setTimeout(function(){window.close()},400)</script>`, 200, clear);
  }
  async redeem(req, b) {
    const n = String(b.n || '');
    if (!/^[A-Za-z0-9_-]{22,64}$/.test(n)) return this.json(req, { error: 'bad_n' }, 400);
    const row = this.q('SELECT * FROM logins WHERE n = ?', n)[0];
    if (!row || row.exp < this.now()) return this.json(req, { error: 'expired' }, 404);
    if (!row.tok) return this.json(req, { pending: true });
    this.q('DELETE FROM logins WHERE n = ?', n);          // 只能換一次
    const v = await this.verify(row.tok);
    if (!v) return this.json(req, { error: 'expired' }, 404);
    return this.json(req, { tok: row.tok, user: this.pubUser(v.user) });
  }

  /* ---------------------------------------------------------------- 心跳：線上人數＋使用統計（R2、R4）*/
  rateOk(req) {
    const ip = req.headers.get('CF-Connecting-IP') || 'local', m = Math.floor(this.now() / 60000);
    const r = this.rate.get(ip);
    if (!r || r[0] !== m) { this.rate.set(ip, [m, 1]); if (this.rate.size > 5000) this.rate.clear(); return true; }
    r[1]++;
    return r[1] <= RATE_PER_MIN;
  }
  /* 把心跳帶來的計數驗過一遍：只收白名單內的鍵、正整數、單次上限。回傳乾淨的 [鍵, 數量]；有任何一項不合格就整批不收。*/
  cleanEv(ev) {
    if (ev == null) return [];
    if (typeof ev !== 'object' || Array.isArray(ev)) return null;
    const out = Object.entries(ev);
    if (out.length > MAX_EV_KEYS) return null;
    for (const [k, n] of out) if (!EV_KEYS.has(k) || !Number.isInteger(n) || n < 1 || n > MAX_EV_INC) return null;
    return out;
  }
  async beat(req, b) {
    if (!this.rateOk(req)) return this.json(req, { error: 'rate' }, 429);
    const sid = String(b.sid || '');
    if (!/^[A-Za-z0-9_-]{8,40}$/.test(sid)) return this.json(req, { error: 'bad_sid' }, 400);
    const ev = this.cleanEv(b.ev);
    if (!ev) return this.json(req, { error: 'bad_ev' }, 400);
    const v = b.t ? await this.verify(b.t) : null;
    const now = this.now();
    if (ev.length) {
      const day = tpeDay(now);
      for (const [k, n] of ev) this.q('INSERT INTO usage (day, k, n) VALUES (?, ?, ?) ON CONFLICT(day, k) DO UPDATE SET n = n + excluded.n', day, k, n);
    }
    if (b.leave) this.q('DELETE FROM presence WHERE sid = ?', sid);
    else {
      const route = VIEWS.includes(b.r) ? b.r : 'other';
      this.q('INSERT INTO presence (sid, uid, route, seen) VALUES (?, ?, ?, ?) ON CONFLICT(sid) DO UPDATE SET uid = excluded.uid, route = excluded.route, seen = excluded.seen',
        sid, v ? v.user.uid : null, route, now);
      if (v && now - (v.user.seen || 0) > 3600 * 1000) this.q('UPDATE users SET seen = ? WHERE uid = ?', now, v.user.uid);
    }
    if (now - this.lastClean > 60 * 1000) this.cleanup();
    const out = { ok: true };
    if (this.publicOnline() || (v && this.isAdmin(v.user))) out.n = this.onlineCount();
    return this.json(req, out);
  }
  onlineCount() { return this.q('SELECT COUNT(*) AS c FROM presence WHERE seen > ?', this.now() - ONLINE_WINDOW_MS)[0].c; }

  /* ---------------------------------------------------------------- 會員（R1、R5）*/
  async auth(req, b) { return b.t ? await this.verify(b.t) : null; }
  async me(req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const out = { user: this.pubUser(v.user) };
    if (v.exp - this.now() / 1000 < TOKEN_DAYS * 86400 / 2) out.tok = await this.sign(v.user.uid, v.user.tv);   // 滑動續期
    return this.json(req, out);
  }
  async listsGet(req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const r = this.q('SELECT data, rev FROM lists WHERE uid = ?', v.user.uid)[0];
    return this.json(req, r ? { lists: JSON.parse(r.data), rev: r.rev } : { lists: [], rev: 0 });
  }
  /* 驗清單格式：最多 5 頁、名字 12 字、每頁 50 檔、代號格式。只收代號與名字 —— 多帶的欄位（張數、成本…）一律丟掉。*/
  cleanLists(lists) {
    if (!Array.isArray(lists) || lists.length > MAX_TABS) return null;
    const seen = new Set(), out = [];
    for (const t of lists) {
      if (!t || typeof t !== 'object') return null;
      const id = String(t.id || '');
      if (!/^[a-z0-9]{1,12}$/.test(id) || seen.has(id)) return null;
      seen.add(id);
      const name = cleanName(t.name);
      if (!name) return null;
      if (!Array.isArray(t.codes) || t.codes.length > MAX_CODES) return null;
      const codes = [];
      for (const c of t.codes) { if (typeof c !== 'string' || !CODE_RE.test(c)) return null; if (!codes.includes(c)) codes.push(c); }
      out.push({ id, name, codes });
    }
    return out;
  }
  async listsPut(req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const lists = this.cleanLists(b.lists);
    if (!lists) return this.json(req, { error: 'bad_lists' }, 400);
    const cur = this.q('SELECT data, rev FROM lists WHERE uid = ?', v.user.uid)[0];
    const rev = cur ? cur.rev : 0;
    /* 版本號不一致＝另一台裝置先改過：不覆蓋，把雲端現況還給前端（前端決定怎麼合併）。*/
    if (b.rev !== rev) return this.json(req, { conflict: true, lists: cur ? JSON.parse(cur.data) : [], rev }, 409);
    this.q('INSERT INTO lists (uid, data, rev, updated) VALUES (?, ?, ?, ?) ON CONFLICT(uid) DO UPDATE SET data = excluded.data, rev = excluded.rev, updated = excluded.updated',
      v.user.uid, JSON.stringify(lists), rev + 1, this.now());
    return this.json(req, { ok: true, rev: rev + 1, lists });
  }
  /* 刪除我的資料：會員資料、自選清單、線上紀錄、進行中的登入一次刪光。
     使用統計是「每天每一項的次數」，本來就沒有記是誰，所以沒有可刪的個人部分（隱私權政策有寫）。*/
  async deleteMe(req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const uid = v.user.uid;
    this.q('DELETE FROM lists WHERE uid = ?', uid);
    this.q('DELETE FROM presence WHERE uid = ?', uid);
    this.q('DELETE FROM logins WHERE uid = ?', uid);
    this.q('DELETE FROM users WHERE uid = ?', uid);
    return this.json(req, { ok: true, deleted: true });
  }

  /* ---------------------------------------------------------------- 管理者（R3）*/
  async admin(req, b) { const v = await this.auth(req, b); return v && this.isAdmin(v.user) ? v : null; }
  async adminStats(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const days = Math.max(1, Math.min(400, parseInt(b.days, 10) || 30));
    const from = tpeDay(this.now() - (days - 1) * 86400 * 1000);
    const rows = this.q('SELECT day, k, n FROM usage WHERE day >= ? ORDER BY day', from);
    const total = this.q('SELECT COUNT(*) AS c FROM users')[0].c;
    const recent = this.q('SELECT name, email, created, seen FROM users ORDER BY seen DESC LIMIT 50');
    return this.json(req, { from, to: tpeDay(this.now()), rows, users: { total, recent }, events: EVENTS, views: VIEWS });
  }
  async adminOnline(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const live = this.q('SELECT p.route, p.seen, u.name, u.email FROM presence p LEFT JOIN users u ON u.uid = p.uid WHERE p.seen > ? ORDER BY p.seen DESC', this.now() - ONLINE_WINDOW_MS);
    const users = live.filter((r) => r.email).map((r) => ({ name: r.name, email: r.email, route: r.route, seen: r.seen }));
    return this.json(req, { total: live.length, guests: live.length - users.length, users, public_online: this.publicOnline() });
  }
  async adminSettings(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    if (typeof b.public_online === 'boolean') this.setKv('public_online', b.public_online ? '1' : '0');
    return this.json(req, { public_online: this.publicOnline() });
  }

  /* ---------------------------------------------------------------- 保存期限（每小時 alarm ＋ 心跳時順手）*/
  cleanup() {
    const now = this.now();
    this.lastClean = now;
    this.q('DELETE FROM presence WHERE seen < ?', now - PRESENCE_TTL_MS);
    this.q('DELETE FROM logins WHERE exp < ?', now);
    const d = new Date(now + 8 * 3600 * 1000); d.setUTCMonth(d.getUTCMonth() - USAGE_KEEP_MONTHS);
    this.q('DELETE FROM usage WHERE day < ?', d.toISOString().slice(0, 10));
    const idle = this.q('SELECT uid FROM users WHERE seen < ?', now - USER_IDLE_DAYS * 86400 * 1000);
    for (const r of idle) { this.q('DELETE FROM lists WHERE uid = ?', r.uid); this.q('DELETE FROM users WHERE uid = ?', r.uid); }
  }
  async alarm() {
    this.cleanup();
    if (this.state.storage.setAlarm) await this.state.storage.setAlarm(this.now() + ALARM_EVERY_MS);
  }
}
