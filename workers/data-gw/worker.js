/* data-gw：付費資料閘道（docs/security_review_1006.md 2-2～2-4；第一階段，docs/datagw_plan.md）
 *
 * 為什麼要有它：網站是公開的靜態檔，放在 site/data 的 JSON 任何人都能直接下載，畫面上的鎖頭只是 UX。
 * 付費資料改放 R2 私有 bucket，只有這支 Worker 讀得到；它驗身分、驗方案、限流、記錄、加浮水印之後才回。
 *
 * 流程：
 *   (1) POST /v1/session { t:<account-api 登入權杖>, d:<裝置 id> }
 *       → 呼叫 account-api 的 /v1/me（驗簽章＋tv 版本，順便拿管理者旗標）與 /v1/perm/me（方案與功能開關）
 *       → 回一張 5 分鐘的資料權杖 g1.<sid>.<exp>.<簽章>，伺服器端記住 uid／方案／功能開關／裝置雜湊
 *       ★ 不共用 account-api 的簽章金鑰：那把金鑰是 account-api 在自己的 Durable Object 裡隨機產生的，從來不離開它；
 *         由 account-api 自己驗登入權杖，等於 tv 停權（遞增 tv）最晚 5 分鐘內在這裡也生效。
 *   (2) GET /v1/data/<檔名>   標頭 Authorization: Bearer <資料權杖>、X-Device: <裝置 id>
 *       → 白名單（tiers.js）→ 免費檔直接回；付費檔驗權杖＋裝置＋功能開關 → 每帳號限流 → 記錄 → 異常規則 → R2 → 浮水印
 *   (3) POST /v1/admin/alerts { t } → 管理者看異常紀錄（管理者身分由 account-api 判定）
 *
 * 異常規則（命中只記錄＋標記，**不自動停權** —— 門檻等 Andy 確認，見 docs/datagw_plan.md「要 Andy 決定」）：
 *   burst     同一帳號 60 秒內拿了超過 BURST_FILES 支不同的檔
 *   multi_ip  同一張資料權杖出現超過 MAX_IPS 個不同 IP 網段（/24、IPv6 /48）
 *   bot_ua    User-Agent 不像瀏覽器，或缺 Sec-Fetch-Mode 標頭
 *
 * 個資：IP 只存網段（203.0.113.x），紀錄 30 天自動刪除；帳號以 uid 記，不存 email（浮水印也是雜湊）。
 * Secret（不寫在任何檔案，由 workflow 從 repo Secret 帶進去）：GW_SECRET（資料權杖與浮水印的 HMAC 金鑰）。
 */
import { tierOf, allowed } from './tiers.js';

const SESSION_SEC = 300;
const LOG_KEEP_MS = 30 * 86400 * 1000;
const DEV_RE = /^[A-Za-z0-9_-]{16,64}$/;

const enc = new TextEncoder();
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const rand = (n = 18) => b64u(crypto.getRandomValues(new Uint8Array(n)));
const sha256 = async (s) => b64u(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const safeEq = (a, b) => { if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false; let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i); return r === 0; };
/* IP 只留網段：IPv4 前三段、IPv6 前三組 */
export const ipNet = (ip) => {
  ip = String(ip || '');
  if (ip.includes(':')) return ip.split(':').slice(0, 3).join(':') + '::/48';
  const p = ip.split('.'); return p.length === 4 ? p.slice(0, 3).join('.') + '.x' : '?';
};
const looksBrowser = (req) => /^Mozilla\/5\.0 /.test(req.headers.get('User-Agent') || '') && !!req.headers.get('Sec-Fetch-Mode');

export default {
  async fetch(req, env) {
    /* 單一 Durable Object：限流計數與紀錄要強一致。會員破萬時再依 uid 分片（docs/datagw_plan.md 第三階段）。*/
    return env.GW.get(env.GW.idFromName('gw')).fetch(req);
  },
};

export class Gw {
  constructor(state, env) {
    this.state = state; this.env = env || {};
    this.sql = state.storage.sql;
    this.rate = new Map();      // uid 或 ip:<網段> → [分鐘, 次數]（記憶體）
    this.alerted = new Map();   // uid|kind → 最後一次記的時間（同一件事 10 分鐘只記一次）
    this.guestCache = null;     // [時間, 訪客的功能開關]
    this.lastClean = 0;
    this.q('CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, uid TEXT, plan TEXT, feats TEXT, devh TEXT, exp INTEGER, ips TEXT)');
    this.q('CREATE TABLE IF NOT EXISTS log (ts INTEGER, uid TEXT, name TEXT, ip TEXT, ua TEXT)');
    this.q('CREATE INDEX IF NOT EXISTS log_uid_ts ON log (uid, ts)');
    this.q('CREATE TABLE IF NOT EXISTS alerts (ts INTEGER, uid TEXT, kind TEXT, detail TEXT)');
    this.q('CREATE TABLE IF NOT EXISTS flags (uid TEXT PRIMARY KEY, n INTEGER, last INTEGER, kinds TEXT)');
  }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray(); }
  now() { return this.env.__now ? this.env.__now() : Date.now(); }
  num(k, d) { const v = parseInt(this.env[k], 10); return Number.isFinite(v) && v > 0 ? v : d; }
  origins() { return String(this.env.ALLOWED_ORIGINS || 'https://miaozike.github.io').split(/[\s,]+/).filter(Boolean); }
  originOk(o) { return !!o && this.origins().includes(o); }

  async hmac(msg) {
    const key = await crypto.subtle.importKey('raw', enc.encode(this.env.GW_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    return b64u(await crypto.subtle.sign('HMAC', key, enc.encode(msg)));
  }
  cors(req, res) {
    const o = req.headers.get('Origin');
    if (this.originOk(o)) { res.headers.set('Access-Control-Allow-Origin', o); res.headers.set('Vary', 'Origin'); }
    return res;
  }
  json(req, obj, status = 200, extra = {}) {
    return this.cors(req, new Response(JSON.stringify(obj), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'private, no-store', ...extra } }));
  }

  /* 呼叫 account-api：優先用 service binding（ACCOUNT），沒有就打 ACCOUNT_API_URL。帶白名單 Origin（account-api 的 POST 要求）。*/
  async acct(path, body) {
    const init = { method: 'POST', headers: { 'content-type': 'text/plain', Origin: this.env.ACCOUNT_ORIGIN || this.origins()[0] }, body: JSON.stringify(body) };
    try {
      const r = this.env.ACCOUNT ? await this.env.ACCOUNT.fetch(new Request('https://account' + path, init))
        : await fetch(String(this.env.ACCOUNT_API_URL || '').replace(/\/$/, '') + path, init);
      return r.ok ? await r.json() : null;
    } catch (e) { return null; }
  }
  async guestFeats() {
    const t = this.now();
    if (this.guestCache && t - this.guestCache[0] < 60000) return this.guestCache[1];
    const j = await this.acct('/v1/perm/me', {});
    const f = j && j.feats ? j.feats : null;
    if (f) this.guestCache = [t, f];
    return f;
  }

  rateOk(key, limit) {
    const m = Math.floor(this.now() / 60000), r = this.rate.get(key);
    if (!r || r[0] !== m) { this.rate.set(key, [m, 1]); return true; }
    r[1]++; return r[1] <= limit;
  }
  alert(uid, kind, detail) {
    const k = uid + '|' + kind, t = this.now();
    if (t - (this.alerted.get(k) || 0) < 600000) return;
    this.alerted.set(k, t);
    this.q('INSERT INTO alerts (ts, uid, kind, detail) VALUES (?, ?, ?, ?)', t, uid, kind, String(detail).slice(0, 300));
    const f = this.q('SELECT n, kinds FROM flags WHERE uid = ?', uid)[0];
    const kinds = new Set(f ? JSON.parse(f.kinds) : []); kinds.add(kind);
    this.q('INSERT INTO flags (uid, n, last, kinds) VALUES (?, 1, ?, ?) ON CONFLICT(uid) DO UPDATE SET n = n + 1, last = excluded.last, kinds = excluded.kinds',
      uid, t, JSON.stringify([...kinds]));
    /* 第二階段：這裡寄信／推播給 Andy；第三階段：flags.n 超過門檻 → 呼叫 account-api 遞增 tv（停權）。目前只記錄。*/
  }
  clean() {
    const t = this.now();
    if (t - this.lastClean < 3600000) return;
    this.lastClean = t;
    this.q('DELETE FROM log WHERE ts < ?', t - LOG_KEEP_MS);
    this.q('DELETE FROM alerts WHERE ts < ?', t - LOG_KEEP_MS);
    this.q('DELETE FROM sessions WHERE exp < ?', Math.floor(t / 1000) - 3600);
  }

  async fetch(req) {
    const url = new URL(req.url), p = url.pathname;
    try {
      if (req.method === 'OPTIONS') return this.cors(req, new Response(null, { status: 204, headers: {
        'Access-Control-Allow-Methods': 'GET, POST', 'Access-Control-Allow-Headers': 'authorization, x-device, content-type', 'Access-Control-Max-Age': '86400' } }));
      if (p === '/health') return this.json(req, { ok: true, service: 'tw-rotation data-gw', configured: !!this.env.GW_SECRET && !!this.env.DATA });
      if (!this.env.GW_SECRET) return this.json(req, { error: 'not_configured' }, 503);
      this.clean();
      if (req.method === 'GET' && p.startsWith('/v1/data/')) return await this.data(req, decodeURIComponent(p.slice(9)).replace(/\.json$/, ''));
      if (req.method !== 'POST') return this.json(req, { error: 'not_found' }, 404);
      if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
      const raw = await req.text();
      if (raw.length > 4096) return this.json(req, { error: 'too_large' }, 413);
      let b; try { b = JSON.parse(raw || '{}'); } catch (e) { return this.json(req, { error: 'bad_json' }, 400); }
      if (!b || typeof b !== 'object') return this.json(req, { error: 'bad_json' }, 400);
      if (p === '/v1/session') return await this.session(req, b);
      if (p === '/v1/admin/alerts') return await this.adminAlerts(req, b);
      return this.json(req, { error: 'not_found' }, 404);
    } catch (e) {
      return this.json(req, { error: 'server' }, 500);
    }
  }

  /* ---- (1) 登入權杖 → 5 分鐘資料權杖（綁裝置）*/
  async session(req, b) {
    const t = typeof b.t === 'string' && b.t.length <= 300 ? b.t : '';
    if (!t) return this.json(req, { error: 'auth' }, 401);
    if (!DEV_RE.test(String(b.d || ''))) return this.json(req, { error: 'bad_device' }, 400);
    const ip = ipNet(req.headers.get('CF-Connecting-IP'));
    if (!this.rateOk('sess:' + ip, this.num('SESSION_PER_MIN', 20))) return this.json(req, { error: 'rate' }, 429);
    const [me, pm] = await Promise.all([this.acct('/v1/me', { t }), this.acct('/v1/perm/me', { t })]);
    if (!me || !me.user || !pm || pm.who !== 'member') return this.json(req, { error: 'auth' }, 401);
    const uid = t.split('.')[1];       // account-api 剛驗過這張權杖（簽章＋tv），uid 就是它的第 2 段
    const sid = rand(), exp = Math.floor(this.now() / 1000) + SESSION_SEC;
    this.q('INSERT INTO sessions (sid, uid, plan, feats, devh, exp, ips) VALUES (?, ?, ?, ?, ?, ?, ?)',
      sid, uid, String(pm.plan || 'free'), JSON.stringify(pm.feats || {}), await sha256('dev:' + b.d), exp, '[]');
    const body = `g1.${sid}.${exp}`;
    return this.json(req, { tok: body + '.' + (await this.hmac(body)), exp, plan: pm.plan });
  }
  async verifyTok(tok, dev) {
    const p = String(tok || '').split('.');
    if (p.length !== 4 || p[0] !== 'g1') return null;
    if (!safeEq(p[3], await this.hmac(p.slice(0, 3).join('.')))) return null;
    if (!(+p[2] > this.now() / 1000)) return null;
    const s = this.q('SELECT * FROM sessions WHERE sid = ?', p[1])[0];
    if (!s || !DEV_RE.test(dev || '') || s.devh !== (await sha256('dev:' + dev))) return null;   // 換裝置＝拿不到
    return s;
  }

  /* ---- (2) 發檔 */
  async data(req, name) {
    const tier = tierOf(name);
    if (!tier) return this.json(req, { error: 'not_found' }, 404);
    const ip = ipNet(req.headers.get('CF-Connecting-IP')), ua = String(req.headers.get('User-Agent') || '').slice(0, 200);
    const auth = req.headers.get('Authorization') || '';
    let who = 'guest', feats;
    if (auth) {
      const s = await this.verifyTok(auth.replace(/^Bearer\s+/i, ''), req.headers.get('X-Device'));
      if (!s) return this.json(req, { error: 'auth' }, 401);
      who = s.uid; feats = JSON.parse(s.feats || '{}');
      const ips = new Set(JSON.parse(s.ips || '[]'));
      if (!ips.has(ip)) { ips.add(ip); this.q('UPDATE sessions SET ips = ? WHERE sid = ?', JSON.stringify([...ips].slice(0, 20)), s.sid); }
      if (ips.size > this.num('MAX_IPS', 2)) this.alert(who, 'multi_ip', [...ips].join(','));
    } else if (tier.feats.length) {
      feats = await this.guestFeats();
      if (!feats) return this.json(req, { error: 'upstream' }, 503);
    }
    if (!allowed(tier, feats || {})) return this.json(req, { error: who === 'guest' ? 'login' : 'plan', need: tier.feats }, who === 'guest' ? 401 : 403);
    const limit = who === 'guest' ? this.num('GUEST_PER_MIN', 120) : this.num('RATE_PER_MIN', 60);
    if (!this.rateOk(who === 'guest' ? 'ip:' + ip : who, limit)) {
      if (who !== 'guest') this.alert(who, 'rate', `>${limit}/min`);
      return this.json(req, { error: 'rate' }, 429, { 'retry-after': '60' });
    }
    const t = this.now();
    this.q('INSERT INTO log (ts, uid, name, ip, ua) VALUES (?, ?, ?, ?, ?)', t, who, name, ip, ua);
    if (who !== 'guest') {
      if (!looksBrowser(req)) this.alert(who, 'bot_ua', ua || '(空白)');
      const n = this.q('SELECT COUNT(DISTINCT name) AS c FROM log WHERE uid = ? AND ts > ?', who, t - 60000)[0].c;
      if (n > this.num('BURST_FILES', 30)) this.alert(who, 'burst', `${n} 支／60 秒`);
    }
    const obj = this.env.DATA ? await this.env.DATA.get(name + '.json') : null;
    if (!obj) return this.json(req, { error: 'not_found' }, 404);
    let data; try { data = JSON.parse(await obj.text()); } catch (e) { return this.json(req, { error: 'bad_object' }, 500); }
    const wm = { a: who === 'guest' ? 'guest' : (await this.hmac('wm:' + who)).slice(0, 12), t: Math.floor(t / 1000) };
    /* 隱形浮水印：物件加 _wm；陣列加在第一個物件元素上（前端不讀 _wm，畫面不變）。另外放在回應標頭。*/
    if (data && typeof data === 'object' && !Array.isArray(data)) data._wm = wm;
    else if (Array.isArray(data) && data[0] && typeof data[0] === 'object') data[0]._wm = wm;
    return this.json(req, data, 200, { 'x-wm': wm.a + '.' + wm.t });
  }

  /* ---- (3) 管理者看異常 */
  async adminAlerts(req, b) {
    const me = b.t ? await this.acct('/v1/me', { t: b.t }) : null;
    if (!me || !me.user) return this.json(req, { error: 'auth' }, 401);
    if (!me.user.admin) return this.json(req, { error: 'forbidden' }, 403);
    return this.json(req, {
      alerts: this.q('SELECT ts, uid, kind, detail FROM alerts ORDER BY ts DESC LIMIT 300'),
      flags: this.q('SELECT uid, n, last, kinds FROM flags ORDER BY last DESC LIMIT 300').map((r) => ({ ...r, kinds: JSON.parse(r.kinds) })),
    });
  }
}

/* 浮水印反查：拿到外流的檔，把 _wm.a 跟每個 uid 的 HMAC 前 12 碼比對（第二階段在 #admin 做成按鈕）。*/
export async function wmOf(secret, uid) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64u(await crypto.subtle.sign('HMAC', key, enc.encode('wm:' + uid))).slice(0, 12);
}
