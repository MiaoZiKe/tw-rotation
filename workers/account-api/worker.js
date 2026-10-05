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
 *   R7 功能權限（DECISIONS #288）：每個 email 套一個方案範本＋個別微調。
 *      · 一般人只有 /v1/perm/me：訪客（沒權杖）拿「訪客」方案、登入者拿「自己 email」那一份 —— 同 R1，API 不收 email 參數，
 *        沒有「讀別人」的路徑；也**沒有任何寫入端點給一般人**，所以「改自己的權限」在物理上不存在。
 *      · 讀寫任何 email 的權限、讀寫方案範本：只有 ADMIN_EMAILS 裡的人（同 R3）。
 *      · ⚠ 這只決定「前端要不要上鎖頭」。網站資料 JSON 是 GitHub Pages 上的公開檔，懂技術的人照樣讀得到 ——
 *        真正保護付費內容，要讓那份資料改由這支 Worker 驗身分後才給（設計與工作量見 DECISIONS #288）。
 *
 * 蒐集與保存（隱私權政策照這裡寫，改這裡要一起改 site/legal.js 與 site/account.js 的告知文字）
 *   · 會員：Google 顯示名稱、email、大頭貼網址、Google 帳號識別碼的雜湊（不存原值）、建立與最後使用時間。
 *     保存到本人刪除，或連續 24 個月沒有使用就自動刪除。
 *   · 自選清單：清單名稱＋股票代號。**不存張數、成本、損益**（CLAUDE.md 第 5 條）。
 *   · 使用統計：每天每一項的「次數」而已，不含任何識別碼、不存 IP、不存單次點擊。保留 13 個月。
 *   · 線上：一個分頁一組隨機代碼（關掉分頁就失效）＋目前在哪一頁＋（登入者）uid。離線即刪（最多 3 分鐘）。
 *   · 功能權限：管理者替某個 email 設定的「方案代號＋各功能開關」。保存到管理者移除，或本人刪除帳號（一起刪）。
 *     email 是管理者自己輸入的（可以先設好、對方之後才登入）；除此之外不存任何東西。
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
/* 功能權限（R7）。功能清單本身在 site/features.js —— Worker 刻意**不**抄一份白名單：
   前端每加一個功能就要重新部署 Worker 太重，而且這裡存的只是「管理者寫的開關」，只驗格式與上限就夠
   （值只准 true／false／0～99 的整數，鍵只准小寫英數與 . _，最多 120 個）。*/
/* 2026-10-05（admin-v2）：120 → 300。功能開關多了「族群」一類（grp.<族群鍵>，groups.yaml 約 117 個），
   付費範本若把大部分族群關掉，加上原本約 50 項功能就會超過 120。300 項 × 約 30 字元 ≈ 9KB，仍在單次 16KB 的上限內。*/
const MAX_FEAT_KEYS = 300, MAX_PLANS = 20, MAX_PERM_ROWS = 5000, MAX_PLAN_NAME = 20;
const FEAT_RE = /^[a-z][a-z0-9_.]{1,39}$/;
const PLAN_PERIODS = ['month', 'year', 'once'];   // 付費範本的計費週期（月／年／一次）
const PLAN_RE = /^[a-z0-9_-]{1,20}$/;
const EMAIL_RE = /^[^\s@<>"'(),;:\\]{1,64}@[a-z0-9-]+(\.[a-z0-9-]+)+$/;
/* 內建方案：訪客（沒登入）、免費會員（登入後沒被指定方案的預設）。不能刪，可以改內容。
   上線時兩者都是 {}（＝全部照 features.js 的預設值，現在全部開啟）—— 不能因為這次上線讓任何人突然看不到功能。*/
const BUILTIN_PLANS = [['guest', '訪客（未登入）'], ['free', '免費會員（預設）']];

/* 使用統計白名單（R2）。改這裡要一起改 site/account.js 的 EVENTS 與 docs/account_analytics.md —— 測試會比對三邊一致。*/
export const VIEWS = ['overview', 'flow', 'industry', 'heatmap', 'market', 'season', 'delivery', 'stock', 'legal', 'watch', 'other'];
export const EVENTS = [
  'session', 'session_login', 'login', 'logout',
  'search', 'watch_add', 'watch_remove', 'watch_tab_new', 'watch_panel',
  'stock_tab', 'k_period', 'ai_tab', 'open_3d', 'zoom', 'how', 'theme_toggle',
  'events_drawer', 'mtf', 'indicators', 'draw', 'm_seg',
];
const EV_KEYS = new Set([...VIEWS.map((v) => 'pv:' + v), ...EVENTS.map((e) => 'ev:' + e)]);
/* 細項事件（2026-10-05 admin-v2，docs/account_analytics.md「細項事件」）：[頁面, 元件, 細項, 次數]。
   · 頁面：VIEWS 白名單。元件：小寫英數與 . _（例如 rot.play、tab.revenue、filter_group）。
   · 細項：只准族群名、股票代號、元件名、象限名 —— 前端只從「畫面上既有的選項」取值，從不送使用者輸入的文字；
     這裡再擋一次：最長 24 字、不准 @（不可能是 email）、不准控制字元與 < > " ' ` \ 。
   · 不帶任何識別碼：一列就是「哪天、哪頁、哪個元件、哪個細項、幾次」，跟 usage 表同一個隱私等級。*/
export const MAX_E2 = 60, MAX_E2_INC = 50, MAX_E2_ROWS_DAY = 20000;
const COMP_RE = /^[a-z][a-z0-9_.]{0,31}$/;
const DETAIL_RE = /^[^\u0000-\u001f\u007f<>"'`\\@]{0,24}$/;

const GOOGLE_AUTH = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN = 'https://oauth2.googleapis.com/token';
const GOOGLE_ISS = ['accounts.google.com', 'https://accounts.google.com'];

/* ---------------------------------------------------------------- 小工具 */
const enc = new TextEncoder();
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64uStr = (s) => b64u(enc.encode(s));
/* 解回 UTF-8 字串：id_token 的內容是 UTF-8 JSON，直接用 atob 的結果 JSON.parse，中文名字會變亂碼（驗收抓到「Bob è¨ªå®¢」）*/
const unb64u = (s) => { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; return new TextDecoder().decode(Uint8Array.from(atob(s), (c) => c.charCodeAt(0))); };
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
    /* R7 功能權限：以 email（小寫）為鍵，不是 uid —— 管理者要能先替還沒登入過的人設好（付費後再登入）。*/
    this.q('CREATE TABLE IF NOT EXISTS perm (email TEXT PRIMARY KEY, plan TEXT, over TEXT, updated INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, name TEXT, feats TEXT, builtin INTEGER, updated INTEGER)');
    /* 2026-10-05（admin-v2）相容遷移 —— 只加不改，舊資料原封不動：
       ① perm.expires：付費到期日（毫秒；NULL／0＝不會到期）。過期的人自動退回「免費會員」，不刪設定（續約時改日期就好）。
       ② ev2：細項事件（頁面＋元件＋細項）。跟 usage 一樣只有「每天的次數」，沒有誰。
       ③ visits：會員近 30 天造訪次數（uid＋台北日期＋次數）。只記登入者，跟 users 同一個保存期限、刪帳號一起刪。
       用 PRAGMA table_info 判斷欄位在不在：ALTER TABLE ADD COLUMN 重跑會報錯，Durable Object 每次冷啟動都會進這裡。*/
    if (!this.q('PRAGMA table_info(perm)').some((c) => c.name === 'expires')) this.q('ALTER TABLE perm ADD COLUMN expires INTEGER');
    /* 2026-10-05（admin-v2b）：付費範本要能調價、之後綁金流 → plans 加 price（整數 NT$）與 period（month／year／once）。
       舊資料庫沒有這兩欄就補上（同上，用 PRAGMA 判斷，重跑不報錯）；舊列 price＝0、period＝month。
       ★ 金流以 plan id 對價（id 建立後不變），價格一律以後端這裡為準，前端顯示的價格只是顯示。 */
    const pc = this.q('PRAGMA table_info(plans)').map((c) => c.name);
    if (!pc.includes('price')) this.q('ALTER TABLE plans ADD COLUMN price INTEGER DEFAULT 0');
    if (!pc.includes('period')) this.q("ALTER TABLE plans ADD COLUMN period TEXT DEFAULT 'month'");
    this.q('CREATE TABLE IF NOT EXISTS ev2 (day TEXT, page TEXT, comp TEXT, detail TEXT, n INTEGER, PRIMARY KEY (day, page, comp, detail))');
    this.q('CREATE TABLE IF NOT EXISTS visits (uid TEXT, day TEXT, n INTEGER, PRIMARY KEY (uid, day))');
    for (const [id, name] of BUILTIN_PLANS) if (!this.q('SELECT 1 FROM plans WHERE id = ?', id).length) this.q('INSERT INTO plans (id, name, feats, builtin, updated) VALUES (?, ?, ?, 1, 0)', id, name, '{}');
    /* 「付費會員」只在第一次啟動時種一份空的範本（＝全開），管理者刪掉就不會再長回來 */
    if (!this.kv('plans_seeded')) {
      if (!this.q('SELECT 1 FROM plans WHERE id = ?', 'paid').length) this.q('INSERT INTO plans (id, name, feats, builtin, updated) VALUES (?, ?, ?, 0, 0)', 'paid', '付費會員', '{}');
      this.setKv('plans_seeded', '1');
    }
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
        case '/v1/perm/me': return await this.permMe(req, b);
        case '/v1/admin/perm/get': return await this.adminPermGet(req, b);
        case '/v1/admin/perm/put': return await this.adminPermPut(req, b);
        case '/v1/admin/perm/list': return await this.adminPermList(req, b);
        case '/v1/admin/plans/get': return await this.adminPlansGet(req, b);
        case '/v1/admin/plans/put': return await this.adminPlansPut(req, b);
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
  /* 細項事件驗格式：整批任何一項不合格就整批不收（同 cleanEv）。回 [[頁面, 元件, 細項, 次數]…] */
  cleanE2(e2) {
    if (e2 == null) return [];
    if (!Array.isArray(e2) || e2.length > MAX_E2) return null;
    const out = [];
    for (const r of e2) {
      if (!Array.isArray(r) || r.length !== 4) return null;
      const [pg, comp, det, n] = r;
      if (!VIEWS.includes(pg) || typeof comp !== 'string' || !COMP_RE.test(comp) || typeof det !== 'string' || !DETAIL_RE.test(det)) return null;
      if (!Number.isInteger(n) || n < 1 || n > MAX_E2_INC) return null;
      out.push([pg, comp, det.trim(), n]);
    }
    return out;
  }
  async beat(req, b) {
    if (!this.rateOk(req)) return this.json(req, { error: 'rate' }, 429);
    const sid = String(b.sid || '');
    if (!/^[A-Za-z0-9_-]{8,40}$/.test(sid)) return this.json(req, { error: 'bad_sid' }, 400);
    const ev = this.cleanEv(b.ev);
    if (!ev) return this.json(req, { error: 'bad_ev' }, 400);
    const e2 = this.cleanE2(b.e2);
    if (!e2) return this.json(req, { error: 'bad_e2' }, 400);
    const v = b.t ? await this.verify(b.t) : null;
    const now = this.now();
    if (ev.length) {
      const day = tpeDay(now);
      for (const [k, n] of ev) this.q('INSERT INTO usage (day, k, n) VALUES (?, ?, ?) ON CONFLICT(day, k) DO UPDATE SET n = n + excluded.n', day, k, n);
      /* 會員造訪次數：登入狀態下「開啟網站」一次＝造訪一次（session_login 本來就是每個分頁一次）*/
      const vis = ev.find(([k]) => k === 'ev:session_login');
      if (vis && v) this.q('INSERT INTO visits (uid, day, n) VALUES (?, ?, ?) ON CONFLICT(uid, day) DO UPDATE SET n = n + excluded.n', v.user.uid, day, vis[1]);
    }
    if (e2.length) {
      const day = tpeDay(now);
      /* 防灌爆：一天最多 2 萬種（頁面×元件×細項）組合；超過之後「新的」組合併進「其他」，既有的照樣累加 */
      const full = this.q('SELECT COUNT(*) AS c FROM ev2 WHERE day = ?', day)[0].c >= MAX_E2_ROWS_DAY;
      for (const [pg, comp, det, n] of e2) {
        const d = full && !this.q('SELECT 1 FROM ev2 WHERE day = ? AND page = ? AND comp = ? AND detail = ?', day, pg, comp, det).length ? '其他' : det;
        this.q('INSERT INTO ev2 (day, page, comp, detail, n) VALUES (?, ?, ?, ?, ?) ON CONFLICT(day, page, comp, detail) DO UPDATE SET n = n + excluded.n', day, pg, comp, d, n);
      }
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
    this.q('DELETE FROM visits WHERE uid = ?', uid);
    /* 權限設定是以 email 存的個人資料，一起刪（代價：付費會員刪帳號後再登入會回到免費預設，要請管理者重設）*/
    if (v.user.email) this.q('DELETE FROM perm WHERE email = ?', String(v.user.email).toLowerCase());
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
    /* 細項事件的分組查詢（流量觀測頁）：同一個 (頁面, 元件, 細項) 期間內加總，次數多的在前，最多 3000 列。
       b.page 有給就只回那一頁（分頁明細切換時用，少傳一點）。*/
    const pg = VIEWS.includes(b.page) ? b.page : null;
    const e2 = this.q(`SELECT page, comp, detail, SUM(n) AS n FROM ev2 WHERE day >= ?${pg ? ' AND page = ?' : ''} GROUP BY page, comp, detail ORDER BY n DESC LIMIT 3000`, ...(pg ? [from, pg] : [from]));
    return this.json(req, { from, to: tpeDay(this.now()), rows, e2, users: { total, recent }, events: EVENTS, views: VIEWS });
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

  /* ---------------------------------------------------------------- 功能權限（R7，DECISIONS #288）*/
  /* 驗「功能開關」：只收格式對的鍵、布林或 0～99 的整數；任何一項不合格就整批不收（同 cleanEv 的原則）。*/
  cleanFeats(f) {
    if (f == null) return {};
    if (typeof f !== 'object' || Array.isArray(f)) return null;
    const ent = Object.entries(f);
    if (ent.length > MAX_FEAT_KEYS) return null;
    const out = {};
    for (const [k, v] of ent) {
      if (!FEAT_RE.test(k)) return null;
      if (typeof v === 'boolean' || (Number.isInteger(v) && v >= 0 && v <= 99)) out[k] = v; else return null;
    }
    return out;
  }
  cleanEmail(e) {
    const s = String(e == null ? '' : e).trim().toLowerCase();
    return s.length <= 200 && EMAIL_RE.test(s) ? s : null;
  }
  plan(id) {
    const r = this.q('SELECT id, name, feats, builtin, price, period FROM plans WHERE id = ?', id)[0];
    return r ? { id: r.id, name: r.name, feats: JSON.parse(r.feats || '{}'), builtin: !!r.builtin,
      price: Number.isInteger(r.price) ? r.price : 0, period: PLAN_PERIODS.includes(r.period) ? r.period : 'month' } : null;
  }
  /* 某個 email 實際生效的權限：方案範本 ← 個別微調（微調蓋過範本）。方案被刪掉的人自動退回「免費會員」。*/
  effective(email) {
    const row = email ? this.q('SELECT plan, over, updated, expires FROM perm WHERE email = ?', email)[0] : null;
    const expires = row && row.expires ? row.expires : 0;
    /* 到期日過了：方案退回「免費會員」、個別微調一併不生效（微調通常是付費時加開的）。設定本身保留，管理者改日期就恢復。*/
    const expired = !!(expires && expires < this.now());
    const p = (row && !expired && this.plan(row.plan)) || this.plan('free');
    const over = row ? JSON.parse(row.over || '{}') : {};
    /* plan 回「被指定的那個」（管理頁要顯示他原本是哪個範本）；實際生效的是 feats */
    return { plan: row && this.plan(row.plan) ? row.plan : p.id, planName: p.name, over, feats: Object.assign({}, p.feats, expired ? {} : over), set: !!row, updated: row ? row.updated : 0, expires, expired };
  }
  async permMe(req, b) {
    /* 刻意不看 b.email／b.plan／b.feats —— 一般人只能拿「權杖裡那個人」或「訪客」的那一份 */
    if (!b.t) { const g = this.plan('guest'); return this.json(req, { who: 'guest', plan: g.id, planName: g.name, feats: g.feats }); }
    const v = await this.verify(b.t);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const e = this.effective(String(v.user.email || '').toLowerCase());
    return this.json(req, { who: 'member', plan: e.expired ? 'free' : e.plan, planName: e.planName, feats: e.feats, expired: e.expired });
  }
  async adminPermGet(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const email = this.cleanEmail(b.email);
    if (!email) return this.json(req, { error: 'bad_email' }, 400);
    const known = this.q('SELECT name, seen FROM users WHERE lower(email) = ?', email)[0] || null;
    return this.json(req, { email, ...this.effective(email), known: known ? { name: known.name, seen: known.seen } : null });
  }
  async adminPermPut(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const email = this.cleanEmail(b.email);
    if (!email) return this.json(req, { error: 'bad_email' }, 400);
    if (b.reset === true) { this.q('DELETE FROM perm WHERE email = ?', email); return this.json(req, { email, ...this.effective(email) }); }
    const plan = String(b.plan || 'free');
    /* 「訪客」方案只給沒登入的人；會員不能被指定成訪客（那是另一個語意，混用會讓「訪客預設」改一下就波及會員）*/
    if (!PLAN_RE.test(plan) || plan === 'guest' || !this.plan(plan)) return this.json(req, { error: 'bad_plan' }, 400);
    const over = this.cleanFeats(b.over);
    if (!over) return this.json(req, { error: 'bad_feats' }, 400);
    /* 到期日：沒帶＝維持原值（舊版前端不會帶，不能因為改了一個開關就把到期日清掉）；null／0＝不會到期；
       其餘必須是 2020～2100 年之間的毫秒整數 */
    const cur = this.q('SELECT expires FROM perm WHERE email = ?', email)[0];
    let expires = cur ? cur.expires || 0 : 0;
    if (b.expires !== undefined) {
      if (b.expires === null || b.expires === 0) expires = 0;
      else if (Number.isInteger(b.expires) && b.expires >= 1577836800000 && b.expires <= 4102444800000) expires = b.expires;
      else return this.json(req, { error: 'bad_expires' }, 400);
    }
    if (!cur && this.q('SELECT COUNT(*) AS c FROM perm')[0].c >= MAX_PERM_ROWS) return this.json(req, { error: 'too_many' }, 400);
    this.q('INSERT INTO perm (email, plan, over, updated, expires) VALUES (?, ?, ?, ?, ?) ON CONFLICT(email) DO UPDATE SET plan = excluded.plan, over = excluded.over, updated = excluded.updated, expires = excluded.expires',
      email, plan, JSON.stringify(over), this.now(), expires || null);
    return this.json(req, { email, ...this.effective(email) });
  }
  async adminPermList(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const rows = this.q('SELECT email, plan, over, updated, expires FROM perm ORDER BY updated DESC LIMIT 500')
      .map((r) => ({ email: r.email, plan: r.plan, n: Object.keys(JSON.parse(r.over || '{}')).length, updated: r.updated, expires: r.expires || 0 }));
    /* 會員管理頁的「所有人員狀況」：最後登入（seen）、加入時間、近 30 天造訪次數（visits 表＝登入狀態下開網站的次數）*/
    const from30 = tpeDay(this.now() - 29 * 86400 * 1000);
    const vis = {};
    this.q('SELECT uid, SUM(n) AS n FROM visits WHERE day >= ? GROUP BY uid', from30).forEach((r) => { vis[r.uid] = r.n; });
    const users = this.q('SELECT uid, name, email, seen, created FROM users ORDER BY seen DESC LIMIT 1000')
      .map((u) => ({ name: u.name, email: String(u.email || '').toLowerCase(), seen: u.seen || 0, created: u.created || 0, visits: vis[u.uid] || 0 }));
    return this.json(req, { rows, users, now: this.now() });
  }
  async adminPlansGet(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const used = {};
    this.q('SELECT plan, COUNT(*) AS c FROM perm GROUP BY plan').forEach((r) => { used[r.plan] = r.c; });
    const plans = this.q('SELECT id FROM plans ORDER BY builtin DESC, updated, id').map((r) => ({ ...this.plan(r.id), members: used[r.id] || 0 }));
    return this.json(req, { plans });
  }
  async adminPlansPut(req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const id = String(b.id || '');
    if (!PLAN_RE.test(id)) return this.json(req, { error: 'bad_plan' }, 400);
    const cur = this.plan(id);
    if (b.del === true) {
      if (!cur) return this.json(req, { error: 'not_found' }, 404);
      if (cur.builtin) return this.json(req, { error: 'builtin' }, 400);
      /* 用這個方案的人退回「免費會員」（保留各自的個別微調），不是連人一起刪 */
      this.q('UPDATE perm SET plan = ?, updated = ? WHERE plan = ?', 'free', this.now(), id);
      this.q('DELETE FROM plans WHERE id = ?', id);
      return await this.adminPlansGet(req, b);
    }
    const name = String(b.name == null ? (cur ? cur.name : '') : b.name).replace(/[\u0000-\u001f\u007f<>]/g, '').trim().slice(0, MAX_PLAN_NAME);
    if (!name) return this.json(req, { error: 'bad_name' }, 400);
    const feats = this.cleanFeats(b.feats);
    if (!feats) return this.json(req, { error: 'bad_feats' }, 400);
    /* 價格／計費週期：沒帶就沿用原值（只改開關的呼叫不會把價格洗成 0）；帶了就嚴格驗證，不默默修正 */
    const price = b.price === undefined ? (cur ? cur.price : 0) : b.price;
    if (!Number.isInteger(price) || price < 0 || price > 999999) return this.json(req, { error: 'bad_price' }, 400);
    const period = b.period === undefined ? (cur ? cur.period : 'month') : b.period;
    if (!PLAN_PERIODS.includes(period)) return this.json(req, { error: 'bad_period' }, 400);
    if (!cur && this.q('SELECT COUNT(*) AS c FROM plans')[0].c >= MAX_PLANS) return this.json(req, { error: 'too_many' }, 400);
    this.q('INSERT INTO plans (id, name, feats, builtin, updated, price, period) VALUES (?, ?, ?, 0, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name, feats = excluded.feats, updated = excluded.updated, price = excluded.price, period = excluded.period',
      id, name, JSON.stringify(feats), this.now(), price, period);
    return await this.adminPlansGet(req, b);
  }

  /* ---------------------------------------------------------------- 保存期限（每小時 alarm ＋ 心跳時順手）*/
  cleanup() {
    const now = this.now();
    this.lastClean = now;
    this.q('DELETE FROM presence WHERE seen < ?', now - PRESENCE_TTL_MS);
    this.q('DELETE FROM logins WHERE exp < ?', now);
    const d = new Date(now + 8 * 3600 * 1000); d.setUTCMonth(d.getUTCMonth() - USAGE_KEEP_MONTHS);
    this.q('DELETE FROM usage WHERE day < ?', d.toISOString().slice(0, 10));
    this.q('DELETE FROM ev2 WHERE day < ?', d.toISOString().slice(0, 10));
    this.q('DELETE FROM visits WHERE day < ?', d.toISOString().slice(0, 10));
    const idle = this.q('SELECT uid FROM users WHERE seen < ?', now - USER_IDLE_DAYS * 86400 * 1000);
    for (const r of idle) { this.q('DELETE FROM lists WHERE uid = ?', r.uid); this.q('DELETE FROM visits WHERE uid = ?', r.uid); this.q('DELETE FROM users WHERE uid = ?', r.uid); }
  }
  async alarm() {
    this.cleanup();
    if (this.state.storage.setAlarm) await this.state.storage.setAlarm(this.now() + ALARM_EVERY_MS);
  }
}

/* ============================================================================ sub-v1 區塊（2026-10-05）
   訂閱申請、意見反饋、每日瀏覽次數、通知中心。Andy：參考 stockintelli 的訂閱頁＋右下角客服＋「之後有活動或變更要通知大家」。
   ★ 為什麼全部寫在檔尾、用「包一層 prototype」接進來，而不是改 fetch() 的 switch：
     同一時間另一條分支（preview/admin-v2）正在改這支檔案的 plans 表與既有函式；
     這裡只「新增」—— 既有函式一行都沒動，兩邊合併時衝突只會落在檔尾（照順序接起來就好）。
   資料表（第一次用到時才建；跟主表同一個 SQLite）：
     sub_requests  訂閱申請（金流還沒串：專人開通）。uid、email、聯絡 email、方案、週期、備註、時間、狀態 new/done。
     feedback      意見反饋。uid（訪客為空）、聯絡 email、類別、內容、當時網址、瀏覽器資訊、時間、狀態 new/handled。
     quota_hits    每日瀏覽次數（登入者）：uid＋台北日期＋功能鍵＋看了哪一個（股票代號／題材代號）。只留 3 天。
                   為什麼要存在伺服器：只靠 localStorage 的話，清快取就歸零 —— 登入者的計數以兩邊較大者為準。
     notices       公告：標題、內文（純文字，前端自動連結、不收 HTML）、類型、對象、上下架時間、置頂。管理者自己刪。
     notice_reads  登入者「讀過哪一則」（跨裝置）：email＋公告 id。公告刪掉或帳號刪除時一起刪。
   公告對象：all 全部／guest 訪客／member 所有登入者（含付費）／paid 付費（免費會員以外的範本）／plan:<範本 id>。
   隱私（同檔頭的保存規則）：反饋與申請保存 13 個月、刪除帳號時一併刪除；不送任何第三方；不進 repo。
   ============================================================================ */
const SUB_KEEP_MONTHS = 13;
const FB_CATS = ['bug', 'idea', 'pay', 'other'];
const NOTICE_KINDS = ['event', 'feature', 'maint', 'plan'];
const NOTICE_AUD_RE = /^(all|guest|member|paid|plan:[a-z0-9_-]{1,20})$/;
const QUOTA_K_RE = /^quota\.[a-z_]{1,24}$/;
const QUOTA_KEY_RE = /^[0-9A-Za-z_.-]{1,24}$/;
const MAX_FB_DAY = 20, MAX_SUBREQ_DAY = 5, MAX_NOTICES = 200;
const subClean = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, '').trim().slice(0, n);

Hub.prototype.subInit = function () {
  if (this._subOk) return;
  this.q('CREATE TABLE IF NOT EXISTS sub_requests (id TEXT PRIMARY KEY, uid TEXT, email TEXT, contact TEXT, plan TEXT, period TEXT, note TEXT, created INTEGER, status TEXT)');
  this.q('CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, uid TEXT, contact TEXT, cat TEXT, body TEXT, url TEXT, ua TEXT, created INTEGER, status TEXT)');
  this.q('CREATE TABLE IF NOT EXISTS quota_hits (uid TEXT, day TEXT, k TEXT, key TEXT, PRIMARY KEY (uid, day, k, key))');
  this.q('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, title TEXT, body TEXT, kind TEXT, audience TEXT, t0 INTEGER, t1 INTEGER, pinned INTEGER, created INTEGER, updated INTEGER)');
  this.q('CREATE TABLE IF NOT EXISTS notice_reads (email TEXT, id TEXT, at INTEGER, PRIMARY KEY (email, id))');
  this._subOk = true;
};
/* 公開的方案摘要：價格欄位由 admin-v2 加在 plans 表上（price／period／price_year）；欄位還沒有時回 null，前端寫「洽詢」。
   不回會員名單、不回人數 —— 只有方案本身。 */
Hub.prototype.subPlanRows = function () {
  const num = (v) => (v == null || v === '' || !isFinite(+v) ? null : +v);
  return this.q('SELECT * FROM plans ORDER BY builtin DESC, updated, id').map((r) => {
    let feats = {}; try { feats = JSON.parse(r.feats || '{}'); } catch (e) { feats = {}; }
    return { id: r.id, name: r.name, builtin: !!r.builtin, feats, price: num(r.price), price_year: num(r.price_year), period: r.period || null };
  });
};
/* 這個人是哪一種對象（公告的 audience 用）：guest／member（免費會員）／paid（其他範本，且沒過期） */
Hub.prototype.subWho = async function (b) {
  const v = b && b.t ? await this.verify(b.t) : null;
  if (!v) return { v: null, tier: 'guest', plan: 'guest', email: '' };
  const email = String(v.user.email || '').toLowerCase();
  const e = this.effective(email);
  const plan = e.expired ? 'free' : e.plan;
  return { v, tier: plan === 'free' ? 'member' : 'paid', plan, email };
};
const subAudOk = (aud, w) => aud === 'all' || aud === w.tier || (aud === 'member' && w.tier === 'paid') || aud === 'plan:' + w.plan;
const subNotice = (r) => ({ id: r.id, title: r.title, body: r.body, kind: r.kind, audience: r.audience, start: r.t0, end: r.t1 || 0, pinned: !!r.pinned, created: r.created, updated: r.updated });

Hub.prototype.subRoutes = {
  '/v1/plans/public': async function (req) {
    return this.json(req, { plans: this.subPlanRows() });
  },
  '/v1/subscribe/request': async function (req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const plan = String(b.plan || '');
    if (!PLAN_RE.test(plan) || plan === 'guest' || !this.plan(plan)) return this.json(req, { error: 'bad_plan' }, 400);
    const period = b.period === 'year' || b.period === 'month' ? b.period : null;
    if (!period) return this.json(req, { error: 'bad_period' }, 400);
    const contact = this.cleanEmail(b.contact || v.user.email);
    if (!contact) return this.json(req, { error: 'bad_email' }, 400);
    const n = this.q('SELECT COUNT(*) AS c FROM sub_requests WHERE uid = ? AND created > ?', v.user.uid, this.now() - 86400 * 1000)[0].c;
    if (n >= MAX_SUBREQ_DAY) return this.json(req, { error: 'too_many' }, 429);
    const id = rand(9);
    this.q('INSERT INTO sub_requests (id, uid, email, contact, plan, period, note, created, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      id, v.user.uid, String(v.user.email || '').toLowerCase(), contact, plan, period, subClean(b.note, 300), this.now(), 'new');
    return this.json(req, { ok: true, id });
  },
  '/v1/feedback': async function (req, b) {
    if (!this.rateOk(req)) return this.json(req, { error: 'rate' }, 429);
    const v = await this.auth(req, b);
    const cat = FB_CATS.includes(b.cat) ? b.cat : null;
    const body = subClean(b.body, 2000);
    if (!cat || body.length < 2) return this.json(req, { error: 'bad_input' }, 400);
    let contact = '';
    if (b.contact) { contact = this.cleanEmail(b.contact); if (!contact) return this.json(req, { error: 'bad_email' }, 400); }
    else if (v) contact = String(v.user.email || '').toLowerCase();
    const url = /^https?:\/\//.test(String(b.url || '')) ? subClean(b.url, 300) : '';
    const since = this.now() - 86400 * 1000;
    const n = v ? this.q('SELECT COUNT(*) AS c FROM feedback WHERE created > ? AND uid = ?', since, v.user.uid)[0].c
      : this.q("SELECT COUNT(*) AS c FROM feedback WHERE created > ? AND uid = ''", since)[0].c;
    if (n >= (v ? MAX_FB_DAY : MAX_FB_DAY * 10)) return this.json(req, { error: 'too_many' }, 429);
    const id = rand(9);
    this.q('INSERT INTO feedback (id, uid, contact, cat, body, url, ua, created, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      id, v ? v.user.uid : '', contact, cat, body, url, subClean(b.ua, 300), this.now(), 'new');
    return this.json(req, { ok: true, id });
  },
  '/v1/quota/hit': async function (req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const k = String(b.k || ''), key = String(b.key || '');
    if (!QUOTA_K_RE.test(k) || (key && !QUOTA_KEY_RE.test(key))) return this.json(req, { error: 'bad_input' }, 400);
    const day = tpeDay(this.now());
    if (key && this.q('SELECT COUNT(*) AS c FROM quota_hits WHERE uid = ? AND day = ? AND k = ?', v.user.uid, day, k)[0].c < 500) {
      this.q('INSERT OR IGNORE INTO quota_hits (uid, day, k, key) VALUES (?, ?, ?, ?)', v.user.uid, day, k, key);
    }
    const keys = this.q('SELECT key FROM quota_hits WHERE uid = ? AND day = ? AND k = ? LIMIT 500', v.user.uid, day, k).map((r) => r.key);
    return this.json(req, { day, k, n: keys.length, keys });
  },
  '/v1/notices': async function (req, b) {
    const w = await this.subWho(b);
    if (b.t && !w.v) return this.json(req, { error: 'auth' }, 401);
    const now = this.now();
    const rows = this.q('SELECT * FROM notices WHERE t0 <= ? AND (t1 IS NULL OR t1 = 0 OR t1 > ?) ORDER BY pinned DESC, t0 DESC LIMIT 100', now, now)
      .filter((r) => subAudOk(r.audience, w));
    const read = w.email ? new Set(this.q('SELECT id FROM notice_reads WHERE email = ?', w.email).map((r) => r.id)) : null;
    return this.json(req, { who: w.tier, notices: rows.map((r) => ({ ...subNotice(r), read: read ? read.has(r.id) : null })) });
  },
  '/v1/notices/read': async function (req, b) {
    const w = await this.subWho(b);
    if (!w.v) return this.json(req, { error: 'auth' }, 401);
    const ids = Array.isArray(b.ids) ? b.ids.filter((x) => typeof x === 'string' && /^[A-Za-z0-9_-]{4,24}$/.test(x)).slice(0, 200) : [];
    const known = new Set(this.q('SELECT id FROM notices').map((r) => r.id));
    for (const id of ids) if (known.has(id)) this.q('INSERT OR IGNORE INTO notice_reads (email, id, at) VALUES (?, ?, ?)', w.email, id, this.now());
    return this.json(req, { ok: true, read: this.q('SELECT id FROM notice_reads WHERE email = ?', w.email).map((r) => r.id) });
  },
  '/v1/admin/notices/list': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const reads = {};
    this.q('SELECT id, COUNT(*) AS c FROM notice_reads GROUP BY id').forEach((r) => { reads[r.id] = r.c; });
    return this.json(req, { now: this.now(), notices: this.q('SELECT * FROM notices ORDER BY created DESC LIMIT 200').map((r) => ({ ...subNotice(r), reads: reads[r.id] || 0 })) });
  },
  '/v1/admin/notices/put': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const title = subClean(b.title, 80), body = subClean(b.body, 2000);
    const kind = NOTICE_KINDS.includes(b.kind) ? b.kind : null;
    const audience = NOTICE_AUD_RE.test(String(b.audience || '')) ? b.audience : null;
    const tsOk = (x) => x === 0 || x == null || (Number.isInteger(x) && x >= 1577836800000 && x <= 4102444800000);
    if (!title || !body || !kind || !audience || !tsOk(b.start) || !tsOk(b.end)) return this.json(req, { error: 'bad_input' }, 400);
    const start = b.start || this.now(), end = b.end || 0;
    if (end && end <= start) return this.json(req, { error: 'bad_range' }, 400);
    const id = b.id ? String(b.id) : rand(9);
    const cur = b.id ? this.q('SELECT id FROM notices WHERE id = ?', id)[0] : null;
    if (b.id && !cur) return this.json(req, { error: 'not_found' }, 404);
    if (!cur && this.q('SELECT COUNT(*) AS c FROM notices')[0].c >= MAX_NOTICES) return this.json(req, { error: 'too_many' }, 400);
    if (cur) this.q('UPDATE notices SET title = ?, body = ?, kind = ?, audience = ?, t0 = ?, t1 = ?, pinned = ?, updated = ? WHERE id = ?', title, body, kind, audience, start, end, b.pinned ? 1 : 0, this.now(), id);
    else this.q('INSERT INTO notices (id, title, body, kind, audience, t0, t1, pinned, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', id, title, body, kind, audience, start, end, b.pinned ? 1 : 0, this.now(), this.now());
    return this.json(req, { ok: true, notice: subNotice(this.q('SELECT * FROM notices WHERE id = ?', id)[0]) });
  },
  '/v1/admin/notices/del': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const id = String(b.id || '');
    this.q('DELETE FROM notice_reads WHERE id = ?', id);
    this.q('DELETE FROM notices WHERE id = ?', id);
    return this.json(req, { ok: true });
  },
  '/v1/admin/feedback/list': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const fb = this.q('SELECT f.id, f.uid, f.contact, f.cat, f.body, f.url, f.ua, f.created, f.status, u.name FROM feedback f LEFT JOIN users u ON u.uid = f.uid ORDER BY f.created DESC LIMIT 300');
    const subs = this.q('SELECT s.id, s.email, s.contact, s.plan, s.period, s.note, s.created, s.status, u.name FROM sub_requests s LEFT JOIN users u ON u.uid = s.uid ORDER BY s.created DESC LIMIT 300');
    return this.json(req, { feedback: fb.map(({ uid, ...r }) => ({ ...r, member: !!uid })), requests: subs });
  },
  '/v1/admin/feedback/set': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const id = String(b.id || '');
    const isReq = b.kind === 'request';
    const st = isReq ? (['new', 'done'].includes(b.status) ? b.status : null) : (['new', 'handled'].includes(b.status) ? b.status : null);
    if (!st) return this.json(req, { error: 'bad_status' }, 400);
    this.q(isReq ? 'UPDATE sub_requests SET status = ? WHERE id = ?' : 'UPDATE feedback SET status = ? WHERE id = ?', st, id);
    return this.json(req, { ok: true });
  },
};

/* 接線：新路由先攔，其他照舊交給原本的 fetch（OPTIONS、GET、auth、既有 API 全部不變） */
const subOrigFetch = Hub.prototype.fetch;
Hub.prototype.fetch = async function (req) {
  const p = new URL(req.url).pathname;
  const h = req.method === 'POST' && Object.prototype.hasOwnProperty.call(this.subRoutes, p) ? this.subRoutes[p] : null;
  if (!h) return subOrigFetch.call(this, req);
  try {
    this.subInit();
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    const raw = await req.text();
    if (raw.length > 16384) return this.json(req, { error: 'too_large' }, 413);
    let b; try { b = JSON.parse(raw || '{}'); } catch (e) { return this.json(req, { error: 'bad_json' }, 400); }
    if (!b || typeof b !== 'object' || Array.isArray(b)) return this.json(req, { error: 'bad_json' }, 400);
    return await h.call(this, req, b);
  } catch (e) {
    return this.json(req, { error: 'server', detail: String(e && e.message || e).slice(0, 200) }, 500);
  }
};
/* 刪除帳號：先記下是誰（原本的 deleteMe 會把 users 那列刪掉，之後就查不到），成功後再刪本區塊的資料 */
const subOrigDelete = Hub.prototype.deleteMe;
Hub.prototype.deleteMe = async function (req, b) {
  const v = await this.auth(req, b);
  const res = await subOrigDelete.call(this, req, b);
  if (v && res.status === 200) {
    this.subInit();
    const uid = v.user.uid, email = String(v.user.email || '').toLowerCase();
    this.q('DELETE FROM feedback WHERE uid = ?', uid);
    this.q('DELETE FROM sub_requests WHERE uid = ?', uid);
    this.q('DELETE FROM quota_hits WHERE uid = ?', uid);
    if (email) this.q('DELETE FROM notice_reads WHERE email = ?', email);
  }
  return res;
};
/* 保存期限：反饋與申請 13 個月；瀏覽次數只留 3 天（只需要「今天」） */
const subOrigCleanup = Hub.prototype.cleanup;
Hub.prototype.cleanup = function () {
  subOrigCleanup.call(this);
  this.subInit();
  const now = this.now();
  const d = new Date(now); d.setUTCMonth(d.getUTCMonth() - SUB_KEEP_MONTHS);
  this.q('DELETE FROM feedback WHERE created < ?', d.getTime());
  this.q('DELETE FROM sub_requests WHERE created < ?', d.getTime());
  this.q('DELETE FROM quota_hits WHERE day < ?', tpeDay(now - 3 * 86400 * 1000));
};
/* ============================================================================ sub-v1 區塊結束 */

/* ============================================================================ admin-v3 區塊（2026-10-05）
   Andy 看了 admin-v2 預覽：「弄得好複雜，看了不清楚」→ 管理頁簡化成 訪客｜註冊會員｜付費會員 三個大分頁，
   每頁兩個子分頁「觀看權限」「會員名單」。後端要多給三樣東西：
     ① 每個功能的「瀏覽次數」上限（每日；留空＝不限、0＝不能看）—— plans.lims（JSON：{功能鍵: 次數}）。
        跟 feats（開關）分開存：開關是「能不能看」，上限是「一天看幾次」，兩者獨立改、獨立驗。
        /v1/perm/me 多回 lims（生效那個範本的；過期的人退回免費會員的）；/v1/plans/public、plans/get 也帶 lims。
     ② 會員名單要的使用數據（只給管理者）：累計在線時間、近 30 天造訪／觀看、最常用的功能 Top3、最常看的股票 Top3、近 14 天每日活躍。
        · 在線時間：每次心跳替「這個人」加上距上次加時的間隔，單次最多 120 秒（前端 60 秒一跳、容許漏一次）；
          用 users.ob（上次加時時間）而不是每個分頁各算 —— 同一人開三個分頁不會變成三倍。存在 visits.ms（每人每天）。
        · 個人使用明細：uev（uid、台北日期、頁面、元件、細項、次數）—— 只記**登入者**，訪客仍然只有不具名的 usage／ev2。
          這是「誰看了什麼」的個人資料（隱私權政策要一起寫）：保留 90 天、刪除帳號一起刪、只有管理者讀得到。
     ③ /v1/quota/hit 的功能鍵放寬成任何功能鍵（原本只收 quota.*）—— 每個功能都有上限之後，計數也要每個功能各記。
   ★ 跟 sub-v1 同一個做法：只在檔尾新增、包一層 prototype，既有函式一行不動。
   相容遷移：plans.lims、visits.ms、users.ob 三欄用 PRAGMA 判斷再 ALTER（重跑不報錯、舊資料原封不動）；uev 新表。
   ============================================================================ */
const V3_UEV_KEEP_DAYS = 90;
const V3_ONLINE_STEP_MS = 120 * 1000;     // 單次心跳最多加 2 分鐘在線時間（防灌水：關機一晚再回來不會加 8 小時）
const V3_LIM_MAX = 9999;
const V3_FEAT_K_RE = /^[a-z][a-z0-9_.]{1,39}$/;

Hub.prototype.v3Init = function () {
  if (this._v3Ok) return;
  const pc = this.q('PRAGMA table_info(plans)').map((c) => c.name);
  if (!pc.includes('lims')) this.q("ALTER TABLE plans ADD COLUMN lims TEXT DEFAULT '{}'");
  const vc = this.q('PRAGMA table_info(visits)').map((c) => c.name);
  if (!vc.includes('ms')) this.q('ALTER TABLE visits ADD COLUMN ms INTEGER DEFAULT 0');
  const uc = this.q('PRAGMA table_info(users)').map((c) => c.name);
  if (!uc.includes('ob')) this.q('ALTER TABLE users ADD COLUMN ob INTEGER DEFAULT 0');
  this.q('CREATE TABLE IF NOT EXISTS uev (uid TEXT, day TEXT, page TEXT, comp TEXT, detail TEXT, n INTEGER, PRIMARY KEY (uid, day, page, comp, detail))');
  this._v3Ok = true;
};
/* 上限：只收 功能鍵 → 0～9999 的整數；任何一項不合格整批不收（同 cleanFeats）。null／undefined＝{}（全部不限）*/
Hub.prototype.v3CleanLims = function (l) {
  if (l == null) return {};
  if (typeof l !== 'object' || Array.isArray(l)) return null;
  const ent = Object.entries(l);
  if (ent.length > MAX_FEAT_KEYS) return null;
  const out = {};
  for (const [k, v] of ent) {
    if (!V3_FEAT_K_RE.test(k) || !Number.isInteger(v) || v < 0 || v > V3_LIM_MAX) return null;
    out[k] = v;
  }
  return out;
};
Hub.prototype.v3Lims = function (id) {
  this.v3Init();
  const r = this.q('SELECT lims FROM plans WHERE id = ?', id)[0];
  try { return r ? JSON.parse(r.lims || '{}') || {} : {}; } catch (e) { return {}; }
};
/* plan()：多帶 lims —— plans/get、plans/put 的回應都經過它，前端一次拿齊 */
const v3OrigPlan = Hub.prototype.plan;
Hub.prototype.plan = function (id) {
  const p = v3OrigPlan.call(this, id);
  if (p) p.lims = this.v3Lims(id);
  return p;
};
const v3OrigPlanRows = Hub.prototype.subPlanRows;
Hub.prototype.subPlanRows = function () {
  return v3OrigPlanRows.call(this).map((p) => ({ ...p, lims: this.v3Lims(p.id) }));
};
/* plans/put：先驗 lims（壞的整個請求 400，不會「開關存了、上限沒存」），原本的存完再寫 lims */
const v3OrigPlansPut = Hub.prototype.adminPlansPut;
Hub.prototype.adminPlansPut = async function (req, b) {
  this.v3Init();
  let lims;
  if (b && b.lims !== undefined && b.del !== true) {
    lims = this.v3CleanLims(b.lims);
    if (!lims) return this.json(req, { error: 'bad_lims' }, 400);
  }
  const res = await v3OrigPlansPut.call(this, req, b);
  if (res.status !== 200 || lims === undefined) return res;
  this.q('UPDATE plans SET lims = ? WHERE id = ?', JSON.stringify(lims), String(b.id));
  return await this.adminPlansGet(req, b);
};
/* /v1/perm/me：多回 lims（生效的範本；過期退回免費會員）*/
const v3OrigPermMe = Hub.prototype.permMe;
Hub.prototype.permMe = async function (req, b) {
  const res = await v3OrigPermMe.call(this, req, b);
  if (res.status !== 200) return res;
  const j = await res.json();
  j.lims = this.v3Lims(j.plan || 'free');
  return this.json(req, j);
};
/* 心跳：原本的照跑；成功而且是登入者 → 加在線時間、記個人使用明細 */
const v3OrigBeat = Hub.prototype.beat;
Hub.prototype.beat = async function (req, b) {
  const res = await v3OrigBeat.call(this, req, b);
  if (res.status !== 200 || !b.t) return res;
  const v = await this.verify(b.t);
  if (!v) return res;
  this.v3Init();
  const now = this.now(), day = tpeDay(now), uid = v.user.uid;
  if (!b.leave) {
    const ob = this.q('SELECT ob FROM users WHERE uid = ?', uid)[0];
    const gap = ob && ob.ob ? now - ob.ob : 0;
    /* 上次加時到現在超過「離線」門檻（150 秒）＝中間斷過，這次只算重新開始，不補中間那段 */
    const add = gap > 0 && gap <= ONLINE_WINDOW_MS ? Math.min(gap, V3_ONLINE_STEP_MS) : 0;
    if (add) this.q('INSERT INTO visits (uid, day, n, ms) VALUES (?, ?, 0, ?) ON CONFLICT(uid, day) DO UPDATE SET ms = COALESCE(ms, 0) + excluded.ms', uid, day, add);
    this.q('UPDATE users SET ob = ? WHERE uid = ?', now, uid);
  }
  const rows = [];
  for (const [k, n] of this.cleanEv(b.ev) || []) if (k.startsWith('pv:')) rows.push([k.slice(3), '_pv', '', n]);
  for (const r of this.cleanE2(b.e2) || []) rows.push(r);
  for (const [pg, comp, det, n] of rows.slice(0, 80)) {
    this.q('INSERT INTO uev (uid, day, page, comp, detail, n) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(uid, day, page, comp, detail) DO UPDATE SET n = n + excluded.n', uid, day, pg, comp, det, n);
  }
  return res;
};
/* 刪帳號：個人使用明細一起刪（visits 原本就會刪）*/
const v3OrigDelete = Hub.prototype.deleteMe;
Hub.prototype.deleteMe = async function (req, b) {
  const v = await this.auth(req, b);
  const res = await v3OrigDelete.call(this, req, b);
  if (v && res.status === 200) { this.v3Init(); this.q('DELETE FROM uev WHERE uid = ?', v.user.uid); }
  return res;
};
const v3OrigCleanup = Hub.prototype.cleanup;
Hub.prototype.cleanup = function () {
  v3OrigCleanup.call(this);
  this.v3Init();
  this.q('DELETE FROM uev WHERE day < ?', tpeDay(this.now() - V3_UEV_KEEP_DAYS * 86400 * 1000));
  this.q('DELETE FROM uev WHERE uid NOT IN (SELECT uid FROM users)');
};

/* 會員名單（管理者）：設定過的（perm）＋登入過的（users）合成一人一列，帶使用數據。
   回：{ now, members: [{ email, name, plan, planName, tier, paid, expires, expired, created, seen, st,
        onlineMs, online30, visits30, days30, views30, topFeat:[[元件, 次數]×3], topStock:[[代號, 次數]×3] }] } */
Hub.prototype.v3Members = function () {
  this.v3Init();
  const now = this.now(), from30 = tpeDay(now - 29 * 86400 * 1000);
  const plans = {}; this.q('SELECT id, name FROM plans').forEach((r) => { plans[r.id] = r.name; });
  const users = this.q('SELECT uid, name, email, created, seen FROM users ORDER BY seen DESC LIMIT 2000');
  const vis = {}; this.q('SELECT uid, SUM(n) AS n, SUM(COALESCE(ms, 0)) AS ms, SUM(CASE WHEN n > 0 OR ms > 0 THEN 1 ELSE 0 END) AS d FROM visits WHERE day >= ? GROUP BY uid', from30).forEach((r) => { vis[r.uid] = r; });
  const tot = {}; this.q('SELECT uid, SUM(COALESCE(ms, 0)) AS ms FROM visits GROUP BY uid').forEach((r) => { tot[r.uid] = r.ms || 0; });
  const pv = {}; this.q("SELECT uid, SUM(n) AS n FROM uev WHERE day >= ? AND comp = '_pv' GROUP BY uid", from30).forEach((r) => { pv[r.uid] = r.n; });
  const feat = {}, stock = {};
  this.q("SELECT uid, comp, SUM(n) AS n FROM uev WHERE day >= ? AND comp NOT IN ('_pv', 'view') GROUP BY uid, comp ORDER BY n DESC", from30)
    .forEach((r) => { const a = (feat[r.uid] = feat[r.uid] || []); if (a.length < 3) a.push([r.comp, r.n]); });
  this.q("SELECT uid, detail, SUM(n) AS n FROM uev WHERE day >= ? AND page = 'stock' AND comp = 'view' AND detail != '' GROUP BY uid, detail ORDER BY n DESC", from30)
    .forEach((r) => { const a = (stock[r.uid] = stock[r.uid] || []); if (a.length < 3) a.push([r.detail, r.n]); });
  const perm = {}; this.q('SELECT email, plan, expires FROM perm').forEach((r) => { perm[r.email] = r; });
  const row = (email, u) => {
    const p = perm[email], exp = p && p.expires ? p.expires : 0, expired = !!(exp && exp < now);
    const plan = p && plans[p.plan] ? p.plan : 'free';
    const uid = u ? u.uid : null, vv = (uid && vis[uid]) || {};
    return { email, name: u ? u.name : '', plan, planName: plans[plan] || plan, tier: plan === 'free' ? 'free' : 'paid', paid: plan !== 'free' && !expired,
      expires: exp, expired, set: !!p, created: u ? u.created || 0 : 0, seen: u ? u.seen || 0 : 0,
      st: expired ? 'exp' : (u ? 'ok' : 'new'), onlineMs: uid ? tot[uid] || 0 : 0, online30: vv.ms || 0, visits30: vv.n || 0, days30: vv.d || 0,
      views30: uid ? pv[uid] || 0 : 0, topFeat: uid ? feat[uid] || [] : [], topStock: uid ? stock[uid] || [] : [] };
  };
  const out = [], seen = new Set();
  for (const u of users) { const e = String(u.email || '').toLowerCase(); if (!e || seen.has(e)) continue; seen.add(e); out.push(row(e, u)); }
  for (const e of Object.keys(perm)) if (!seen.has(e)) { seen.add(e); out.push(row(e, null)); }
  return { now, members: out };
};
/* 某一位會員的詳細使用紀錄（展開那一列用）：各分頁瀏覽、功能次數 Top 15、最常看的股票 Top 10、近 14 天每日（造訪、在線、瀏覽）*/
Hub.prototype.v3Detail = function (email) {
  this.v3Init();
  const now = this.now(), from30 = tpeDay(now - 29 * 86400 * 1000), from14 = tpeDay(now - 13 * 86400 * 1000);
  const u = this.q('SELECT uid, name, created, seen FROM users WHERE lower(email) = ?', email)[0];
  if (!u) return { email, known: false, pages: [], feats: [], stocks: [], days: [] };
  const pages = this.q("SELECT page, SUM(n) AS n FROM uev WHERE uid = ? AND day >= ? AND comp = '_pv' GROUP BY page ORDER BY n DESC", u.uid, from30).map((r) => [r.page, r.n]);
  const feats = this.q("SELECT page, comp, SUM(n) AS n FROM uev WHERE uid = ? AND day >= ? AND comp NOT IN ('_pv', 'view') GROUP BY page, comp ORDER BY n DESC LIMIT 15", u.uid, from30).map((r) => [r.page, r.comp, r.n]);
  const stocks = this.q("SELECT detail, SUM(n) AS n FROM uev WHERE uid = ? AND day >= ? AND page = 'stock' AND comp = 'view' AND detail != '' GROUP BY detail ORDER BY n DESC LIMIT 10", u.uid, from30).map((r) => [r.detail, r.n]);
  const vd = {}; this.q('SELECT day, n, COALESCE(ms, 0) AS ms FROM visits WHERE uid = ? AND day >= ?', u.uid, from14).forEach((r) => { vd[r.day] = r; });
  const pd = {}; this.q("SELECT day, SUM(n) AS n FROM uev WHERE uid = ? AND day >= ? AND comp = '_pv' GROUP BY day", u.uid, from14).forEach((r) => { pd[r.day] = r.n; });
  const days = [];
  for (let i = 13; i >= 0; i--) { const d = tpeDay(now - i * 86400 * 1000); days.push({ day: d, visits: (vd[d] || {}).n || 0, ms: (vd[d] || {}).ms || 0, views: pd[d] || 0 }); }
  return { email, known: true, name: u.name, created: u.created, seen: u.seen, pages, feats, stocks, days };
};
Object.assign(Hub.prototype.subRoutes, {
  '/v1/admin/members': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    return this.json(req, this.v3Members());
  },
  '/v1/admin/member/detail': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const email = this.cleanEmail(b.email);
    if (!email) return this.json(req, { error: 'bad_email' }, 400);
    return this.json(req, this.v3Detail(email));
  },
  /* 每日瀏覽次數：功能鍵放寬成任何功能鍵（含舊的 quota.*）；其餘規則同 sub-v1（要登入、同一個 key 一天只算一次、最多 500）*/
  '/v1/quota/hit': async function (req, b) {
    const v = await this.auth(req, b);
    if (!v) return this.json(req, { error: 'auth' }, 401);
    const k = String(b.k || ''), key = String(b.key || '');
    if (!V3_FEAT_K_RE.test(k) || (key && !QUOTA_KEY_RE.test(key))) return this.json(req, { error: 'bad_input' }, 400);
    const day = tpeDay(this.now());
    if (key && this.q('SELECT COUNT(*) AS c FROM quota_hits WHERE uid = ? AND day = ? AND k = ?', v.user.uid, day, k)[0].c < 500) {
      this.q('INSERT OR IGNORE INTO quota_hits (uid, day, k, key) VALUES (?, ?, ?, ?)', v.user.uid, day, k, key);
    }
    const keys = this.q('SELECT key FROM quota_hits WHERE uid = ? AND day = ? AND k = ? LIMIT 500', v.user.uid, day, k).map((r) => r.key);
    return this.json(req, { day, k, n: keys.length, keys });
  },
});
/* ============================================================================ admin-v3 區塊結束 */

/* ============================================================================ perm-v4 區塊（2026-10-05）
   Andy 對 #admin/perm：「付費範本頁籤要能拖曳排序、刪除」「會員名單上方加視覺化統計」。後端多三樣：
     ① plans.sort（整數，愈小愈前面）—— 付費範本的順序。內建 guest／free 永遠在最前面（不吃 sort）。
        plans/get、plans/put 的回應與 /v1/plans/public 都照這個順序 → 訂閱頁 #pricing 的方案卡跟著變（pricing.js 照後端順序畫）。
        為什麼不再用 updated 排：原本「改個名字／價格」updated 會變，那個範本就跑到最後 —— 管理者沒拖它，它卻自己換位置。
     ② /v1/admin/plans/sort { ids:[全部付費範本 id，依新順序] }：拖一次＝送一次整個順序。
        ids 必須「正好是全部付費範本、不重複」，少一個／多一個／內建範本／不存在 → 400 bad_order，什麼都不寫（不留半套順序）。
     ③ /v1/admin/members/stats { scope:'all' } 或 { scope:'plan', plan:<id> }：會員名單上方的圖表，伺服器端彙總，
        前端不必逐人呼叫 member/detail。回：近 30 天最常用功能 Top 8、最常看股票 Top 8、近 14 天每日活躍人數、近 7 日活躍人數。
        'all'＝所有登入過的人（＝註冊會員頁籤的名單）；'plan'＝被指定到該範本的人（含已過期，跟名單同一個口徑）。
        「狀態分布」「總人數」「平均在線」由前端從同一份名單（/v1/admin/members）算 —— 圖上的數字一定跟下面的表對得上。
   相容遷移：plans.sort 用 PRAGMA 判斷再 ALTER；第一次補欄時依「原本的順序（updated, id）」替既有付費範本補 0..n-1，
   所以上線那一刻順序完全不變；之後新建的範本排最後（max＋1）。
   ★ 同 sub-v1／admin-v3：只在檔尾新增、包一層 prototype，既有函式一行不動。
   ============================================================================ */
const V4_HEAD = { guest: 0, free: 1 };
const V4_TOP = 8;

Hub.prototype.v4Init = function () {
  if (this._v4Ok) return;
  this.v3Init();
  const pc = this.q('PRAGMA table_info(plans)').map((c) => c.name);
  if (!pc.includes('sort')) {
    this.q('ALTER TABLE plans ADD COLUMN sort INTEGER');
    this.q('SELECT id FROM plans WHERE builtin = 0 ORDER BY updated, id').forEach((r, i) => this.q('UPDATE plans SET sort = ? WHERE id = ?', i, r.id));
  }
  this._v4Ok = true;
};
/* 排序：guest → free → 其他內建 → 付費（sort 小的在前；沒有 sort 的排最後、維持原順序）。每個方案多帶 sort 欄位 */
Hub.prototype.v4Order = function (plans) {
  this.v4Init();
  const s = {}; this.q('SELECT id, sort FROM plans').forEach((r) => { s[r.id] = r.sort; });
  const key = (p) => (Object.prototype.hasOwnProperty.call(V4_HEAD, p.id) ? [0, V4_HEAD[p.id]] : p.builtin ? [1, 0] : [2, Number.isInteger(s[p.id]) ? s[p.id] : 1e9]);
  return plans.map((p, i) => [p, i]).sort((a, b) => { const x = key(a[0]), y = key(b[0]); return x[0] - y[0] || x[1] - y[1] || a[1] - b[1]; })
    .map(([p]) => ({ ...p, sort: Number.isInteger(s[p.id]) ? s[p.id] : null }));
};
const v4OrigPlansGet = Hub.prototype.adminPlansGet;
Hub.prototype.adminPlansGet = async function (req, b) {
  const res = await v4OrigPlansGet.call(this, req, b);
  if (res.status !== 200) return res;
  const j = await res.json();
  j.plans = this.v4Order(j.plans || []);
  return this.json(req, j);
};
const v4OrigPlanRows = Hub.prototype.subPlanRows;
Hub.prototype.subPlanRows = function () { return this.v4Order(v4OrigPlanRows.call(this)); };
/* 新建的付費範本排最後（max＋1）；改名、改價、改開關不動順序 */
const v4OrigPlansPut = Hub.prototype.adminPlansPut;
Hub.prototype.adminPlansPut = async function (req, b) {
  this.v4Init();
  const res = await v4OrigPlansPut.call(this, req, b);
  if (res.status !== 200 || !b || b.del === true) return res;
  const r = this.q('SELECT builtin, sort FROM plans WHERE id = ?', String(b.id || ''))[0];
  if (!r || r.builtin || r.sort != null) return res;
  const mx = this.q('SELECT MAX(sort) AS m FROM plans WHERE builtin = 0')[0].m;
  this.q('UPDATE plans SET sort = ? WHERE id = ?', mx == null ? 0 : mx + 1, String(b.id));
  return await this.adminPlansGet(req, b);
};
/* 會員名單上方的圖表（③）。uid 範圍：'all'＝所有登入過的人；'plan'＝perm.plan 是這個範本的人（沒登入過的沒有使用紀錄，不影響彙總）*/
Hub.prototype.v4Stats = function (scope, plan) {
  this.v4Init();
  const now = this.now(), d30 = tpeDay(now - 29 * 86400 * 1000), d14 = tpeDay(now - 13 * 86400 * 1000), d7 = tpeDay(now - 6 * 86400 * 1000);
  const users = this.q('SELECT uid, email FROM users');
  let pick = users;
  if (scope === 'plan') {
    const em = new Set(this.q('SELECT email FROM perm WHERE plan = ?', plan).map((r) => r.email));
    pick = users.filter((u) => em.has(String(u.email || '').toLowerCase()));
  }
  const set = new Set(pick.map((u) => u.uid));
  const feats = {}, stocks = {}, act = {};
  this.q("SELECT uid, comp, SUM(n) AS n FROM uev WHERE day >= ? AND comp NOT IN ('_pv', 'view') GROUP BY uid, comp", d30)
    .forEach((r) => { if (set.has(r.uid)) feats[r.comp] = (feats[r.comp] || 0) + r.n; });
  this.q("SELECT uid, detail, SUM(n) AS n FROM uev WHERE day >= ? AND page = 'stock' AND comp = 'view' AND detail != '' GROUP BY uid, detail", d30)
    .forEach((r) => { if (set.has(r.uid)) stocks[r.detail] = (stocks[r.detail] || 0) + r.n; });
  /* 「活躍」＝那一天有開網站（visits.n）、有在線時間（visits.ms）或有任何使用紀錄（uev）—— 三者任一 */
  const mark = (r) => { if (set.has(r.uid)) (act[r.day] = act[r.day] || new Set()).add(r.uid); };
  this.q('SELECT uid, day FROM visits WHERE day >= ? AND (n > 0 OR COALESCE(ms, 0) > 0)', d14).forEach(mark);
  this.q('SELECT DISTINCT uid, day FROM uev WHERE day >= ?', d14).forEach(mark);
  const days = [], a7 = new Set();
  for (let i = 13; i >= 0; i--) {
    const d = tpeDay(now - i * 86400 * 1000), s = act[d] || new Set();
    days.push({ day: d, n: s.size });
    if (d >= d7) s.forEach((u) => a7.add(u));
  }
  const top = (o) => Object.entries(o).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, V4_TOP);
  return { now, scope, plan: scope === 'plan' ? plan : null, n: set.size, active7: a7.size, feats: top(feats), stocks: top(stocks), days };
};
Object.assign(Hub.prototype.subRoutes, {
  '/v1/admin/plans/sort': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    this.v4Init();
    const paid = new Set(this.q('SELECT id FROM plans WHERE builtin = 0').map((r) => r.id));
    const ids = b.ids;
    if (!Array.isArray(ids) || ids.length !== paid.size || new Set(ids).size !== ids.length
      || !ids.every((id) => typeof id === 'string' && PLAN_RE.test(id) && paid.has(id))) return this.json(req, { error: 'bad_order' }, 400);
    ids.forEach((id, i) => this.q('UPDATE plans SET sort = ? WHERE id = ?', i, id));
    return await this.adminPlansGet(req, b);
  },
  '/v1/admin/members/stats': async function (req, b) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const scope = b.scope == null || b.scope === 'all' ? 'all' : b.scope === 'plan' ? 'plan' : null;
    if (!scope) return this.json(req, { error: 'bad_scope' }, 400);
    const plan = scope === 'plan' ? String(b.plan == null ? '' : b.plan) : null;
    if (scope === 'plan' && (!PLAN_RE.test(plan) || !this.plan(plan))) return this.json(req, { error: 'bad_plan' }, 400);
    return this.json(req, this.v4Stats(scope, plan));
  },
});
/* ============================================================================ perm-v4 區塊結束 */

/* ============================================================================ hourly 區塊（2026-10-05）
   Andy：流量觀測「即時」要看今天 0–24 時每小時的狀況、「使用者」分頁要看每小時的使用時段（1H／4H／6H／12H／白天／晚上），
   而且 ETF、選股策略、事件、客服、財經日曆這幾頁要有真的瀏覽數。後端多兩樣：
     ① 每小時統計 hstat：一列＝「台北日期 × 小時（0–23）」，四個次數：
          pv          頁面瀏覽（所有 pv:* 加總）
          sess        開站（ev:session）
          sess_login  登入狀態下開站（ev:session_login）；訪客開站＝sess − sess_login
          mins        心跳次數（不含「離開」那一跳）＝這一小時「看得到的分頁」在線分鐘數；平均同時在線 ≈ mins ÷ 60
        · 跟 usage 吃同一份心跳、同一套驗證：原本的 beat 回 200 才記，整批被擋（400／429）的這裡也不記 ——
          所以「今天各小時加總」＝usage 表的今天，兩邊對得上（tests/hourly.test.mjs 驗）。
        · 歸到「Worker 收到心跳」的那一小時：前端 60 秒送一次，整點前一分鐘內的動作可能算到下一小時（誤差 ≤ 1 分鐘）。
        · 只有次數：沒有 uid、沒有 sid、不存 IP —— 跟 usage 同一個隱私等級；保留期限也跟 usage 一樣（13 個月，同一個切點）。
        · /v1/admin/stats 的回應多三個欄位（原有欄位一個不動）：
            hours   [24]  今天（台北）0–23 時每小時頁面瀏覽；還沒到的小時＝0
            hourly  [24]  期間 from～to 內，各「時」的頁面瀏覽加總（使用時段圖）
            hstat   { today, hour, since, day:{pv,open,login,guest,mins}, period:{from,to,pv,open,login,guest,mins} }（各數列都是 24 格）
          格式與前端接法寫在 docs/account_analytics.md「每小時統計」。
     ② 頁面白名單加 etf、explore、earnings、pricing、notices（網址頁）與 events（今日事件抽屜）、support（客服面板）。
        做法是把 VIEWS 陣列（與 EV_KEYS）在這裡補上 —— cleanEv、cleanE2、線上名單的 route、/v1/admin/stats 的 page 篩選全部讀同一份，
        既有函式不用改一行就收得下。舊資料不動：之前記在 other 底下、元件名帶前綴（etf.cat、support.fab、events.link…）的細項照舊回在 e2 裡。
        ★ Worker 先上、前端後上：Worker 先收得下新頁面，site/account.js 的 VIEWS 才能加（反過來＝那一分鐘的心跳整批 400、統計全丟）。
   ★ 同 sub-v1／admin-v3／perm-v4：只在檔尾新增、包一層 prototype，既有函式一行不動。
   ============================================================================ */
export const VIEWS_ADDED = ['etf', 'explore', 'earnings', 'events', 'support', 'pricing', 'notices'];
for (const v of VIEWS_ADDED) { if (!VIEWS.includes(v)) VIEWS.push(v); EV_KEYS.add('pv:' + v); }

const tpeHour = (ms) => new Date(ms + 8 * 3600 * 1000).getUTCHours();
const hrZero = () => Array.from({ length: 24 }, () => 0);

Hub.prototype.hrInit = function () {
  if (this._hrOk) return;
  this.q('CREATE TABLE IF NOT EXISTS hstat (day TEXT, h INTEGER, pv INTEGER DEFAULT 0, sess INTEGER DEFAULT 0, sess_login INTEGER DEFAULT 0, mins INTEGER DEFAULT 0, PRIMARY KEY (day, h))');
  this._hrOk = true;
};
/* 期間內各「時」加總（from～to 都是台北日期，含頭含尾）。回五個 24 格數列。*/
Hub.prototype.hrSeries = function (from, to) {
  this.hrInit();
  const out = { pv: hrZero(), open: hrZero(), login: hrZero(), guest: hrZero(), mins: hrZero() };
  this.q('SELECT h, SUM(pv) AS pv, SUM(sess) AS s, SUM(sess_login) AS sl, SUM(mins) AS m FROM hstat WHERE day >= ? AND day <= ? GROUP BY h', from, to).forEach((r) => {
    if (!(r.h >= 0 && r.h < 24)) return;
    out.pv[r.h] = r.pv || 0; out.open[r.h] = r.s || 0; out.login[r.h] = r.sl || 0; out.mins[r.h] = r.m || 0;
  });
  for (let h = 0; h < 24; h++) out.guest[h] = Math.max(0, out.open[h] - out.login[h]);
  return out;
};
/* 心跳：原本的照跑；回 200（＝usage 已經記下）才同步累加到這一小時。統計失敗不影響心跳本身的回應。*/
const hrOrigBeat = Hub.prototype.beat;
Hub.prototype.beat = async function (req, b) {
  const res = await hrOrigBeat.call(this, req, b);
  if (res.status !== 200) return res;
  try {
    let pv = 0, sess = 0, sl = 0;
    for (const [k, n] of this.cleanEv(b.ev) || []) {
      if (k.startsWith('pv:')) pv += n; else if (k === 'ev:session') sess += n; else if (k === 'ev:session_login') sl += n;
    }
    const mins = b.leave ? 0 : 1;
    if (pv || sess || sl || mins) {
      this.hrInit();
      const now = this.now();
      this.q('INSERT INTO hstat (day, h, pv, sess, sess_login, mins) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(day, h) DO UPDATE SET pv = pv + excluded.pv, sess = sess + excluded.sess, sess_login = sess_login + excluded.sess_login, mins = mins + excluded.mins',
        tpeDay(now), tpeHour(now), pv, sess, sl, mins);
    }
  } catch (e) { /* 每小時統計寫不進去：心跳照樣算成功（不然前端會把這批計數放回去重送，usage 就重複了）*/ }
  return res;
};
/* /v1/admin/stats：原本的照跑（權限、rows、e2、users…一個不動），回 200 才在後面加 hours／hourly／hstat */
const hrOrigStats = Hub.prototype.adminStats;
Hub.prototype.adminStats = async function (req, b) {
  const res = await hrOrigStats.call(this, req, b);
  if (res.status !== 200) return res;
  const j = await res.json();
  const now = this.now(), today = tpeDay(now);
  const day = this.hrSeries(today, today), per = this.hrSeries(j.from, j.to);
  const first = this.q('SELECT MIN(day) AS d FROM hstat')[0];
  j.hours = day.pv.slice();
  j.hourly = per.pv.slice();
  j.hstat = { today, hour: tpeHour(now), since: (first && first.d) || null, day, period: { from: j.from, to: j.to, ...per } };
  return this.json(req, j);
};
/* 保存期限：跟 usage 同一個切點（13 個月） */
const hrOrigCleanup = Hub.prototype.cleanup;
Hub.prototype.cleanup = function () {
  hrOrigCleanup.call(this);
  this.hrInit();
  const d = new Date(this.now() + 8 * 3600 * 1000); d.setUTCMonth(d.getUTCMonth() - USAGE_KEEP_MONTHS);
  this.q('DELETE FROM hstat WHERE day < ?', d.toISOString().slice(0, 10));
};
/* ============================================================================ hourly 區塊結束 */

/* =====================================================================

/* ============================================================================
   範本刪除保護（2026-10-05，Andy：「還有有效會員的付費範本不能刪」）
   plans/put 帶 del:true 時：這個範本若還有「有效會員」（perm.plan 指向它、而且沒到期：expires 為空或 0 或晚於現在）→ 409 {error:'has_members', n, emails}
   不刪、不動任何資料；只剩已到期的人或 0 人才照原本流程刪（用它的人退回免費會員、個別微調保留）。
   只在這個檔尾加區塊（prototype 包裝），不改前面的函式。
   ============================================================================ */
const delGuardOrig = Hub.prototype.adminPlansPut;
Hub.prototype.adminPlansPut = async function (req, b) {
  if (b && b.del === true && typeof b.id === 'string' && PLAN_RE.test(b.id)) {
    if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
    const cur = this.plan(b.id);
    if (cur && !cur.builtin) {
      const now = this.now();
      const act = this.q('SELECT email FROM perm WHERE plan = ? AND (expires IS NULL OR expires = 0 OR expires > ?) ORDER BY email', b.id, now);
      if (act.length) return this.json(req, { error: 'has_members', n: act.length, emails: act.slice(0, 50).map((r) => r.email) }, 409);
    }
  }
  return await delGuardOrig.call(this, req, b);
};
/* ============================================================================ 範本刪除保護區塊結束 */
