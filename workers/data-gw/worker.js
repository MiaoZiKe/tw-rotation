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
    /* 第三階段：每帳號裝置（只存裝置 id 的雜湊）。DEVICE_TTL_D 天沒用的裝置自動讓出名額 */
    this.q('CREATE TABLE IF NOT EXISTS devices (uid TEXT, devh TEXT, first INTEGER, last INTEGER, PRIMARY KEY (uid, devh))');
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
  async acct(path, body, extra = {}) {
    const init = { method: 'POST', headers: { 'content-type': 'text/plain', Origin: this.env.ACCOUNT_ORIGIN || this.origins()[0], ...extra }, body: JSON.stringify(body) };
    try {
      const r = this.env.ACCOUNT ? await this.env.ACCOUNT.fetch(new Request('https://account' + path, init))
        : await fetch(String(this.env.ACCOUNT_API_URL || '').replace(/\/$/, '') + path, init);
      return r.ok ? await r.json() : null;
    } catch (e) { return null; }
  }
  async guestFeats() {
    const t = this.now();
    if (this.guestCache && t - this.guestCache[0] < this.num('GUEST_CACHE_MS', 60000)) return this.guestCache[1];   // 訪客範本改了最晚 60 秒生效
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
  async alert(uid, kind, detail) {
    const k = uid + '|' + kind, t = this.now();
    if (t - (this.alerted.get(k) || 0) < 600000) return;
    this.alerted.set(k, t);
    this.q('INSERT INTO alerts (ts, uid, kind, detail) VALUES (?, ?, ?, ?)', t, uid, kind, String(detail).slice(0, 300));
    const f = this.q('SELECT n, kinds FROM flags WHERE uid = ?', uid)[0];
    const kinds = new Set(f ? JSON.parse(f.kinds) : []); kinds.add(kind);
    this.q('INSERT INTO flags (uid, n, last, kinds) VALUES (?, 1, ?, ?) ON CONFLICT(uid) DO UPDATE SET n = n + 1, last = excluded.last, kinds = excluded.kinds',
      uid, t, JSON.stringify([...kinds]));
    /* T4 自動停權（docs/datagw_plan.md 第 6 節）：SUSPEND_WINDOW_H 小時內 burst／multi_ip 累計 SUSPEND_AFTER 次。
       AUTO_SUSPEND 預設 '0'＝關閉：只記一筆 would_suspend 讓 Andy 看「如果開了會停誰」，不動帳號。
       開啟後（'1'）記 suspend；真正遞增 tv 的 account-api 端點是第三階段的工作，在那之前這裡也不會去動帳號。*/
    if (kind === 'burst' || kind === 'multi_ip') {
      const since = t - this.num('SUSPEND_WINDOW_H', 24) * 3600000;
      const n = this.q("SELECT COUNT(*) AS c FROM alerts WHERE uid = ? AND ts >= ? AND kind IN ('burst', 'multi_ip')", uid, since)[0].c;
      const done = this.q("SELECT COUNT(*) AS c FROM alerts WHERE uid = ? AND ts >= ? AND kind IN ('would_suspend', 'suspend')", uid, since)[0].c;
      if (n >= this.num('SUSPEND_AFTER', 3) && !done) {
        const on = String(this.env.AUTO_SUSPEND) === '1';
        let k2 = 'would_suspend', d2 = `${n} 次／${this.num('SUSPEND_WINDOW_H', 24)} 小時`;
        if (on) {
          /* 經 service binding 呼叫 account-api 的 /internal/suspend（遞增 tv）；失敗也要留紀錄，讓 Andy 手動處理 */
          const r = this.env.INTERNAL_KEY ? await this.acct('/internal/suspend', { uid, reason: `data-gw：${d2}` }, { 'X-Internal-Key': this.env.INTERNAL_KEY }) : null;
          k2 = r && r.ok ? 'suspend' : 'suspend_failed';
        }
        this.q('INSERT INTO alerts (ts, uid, kind, detail) VALUES (?, ?, ?, ?)', t, uid, k2, d2);
        await this.notify(uid, k2, d2);
      }
    }
    await this.notify(uid, kind, detail);
  }
  /* 異常通知（T6）：收件設定沒設＝只記錄。
     ALERT_WEBHOOK（Secret）：POST JSON {text, kind, uid, detail, ts}，可接 ntfy、Slack／Discord／Telegram 轉接、Google Apps Script 寄信。
     ALERT_EMAIL ＋ RESEND_API_KEY（Secret）：用 Resend 寄信到這個地址。
     只通知 NOTIFY_KINDS 列的種類（預設：停權相關、裝置超額、多 IP），其他只記錄。通知失敗不影響發檔。*/
  async notify(uid, kind, detail) {
    const kinds = String(this.env.NOTIFY_KINDS || 'would_suspend,suspend,suspend_failed,devices,multi_ip').split(',');
    if (!kinds.includes(kind)) return;
    const text = `[tw-rotation data-gw] ${kind}｜帳號 ${uid}｜${String(detail).slice(0, 200)}`;
    const jobs = [];
    if (this.env.ALERT_WEBHOOK) jobs.push(fetch(this.env.ALERT_WEBHOOK, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text, kind, uid, detail: String(detail).slice(0, 300), ts: this.now() }) }));
    if (this.env.ALERT_EMAIL && this.env.RESEND_API_KEY) jobs.push(fetch('https://api.resend.com/emails', { method: 'POST',
      headers: { 'content-type': 'application/json', Authorization: 'Bearer ' + this.env.RESEND_API_KEY },
      body: JSON.stringify({ from: this.env.ALERT_FROM || 'data-gw <onboarding@resend.dev>', to: [this.env.ALERT_EMAIL], subject: `異常：${kind}`, text }) }));
    if (!jobs.length) return;
    const ok = (await Promise.allSettled(jobs)).some((r) => r.status === 'fulfilled' && r.value.ok);
    this.q('INSERT INTO alerts (ts, uid, kind, detail) VALUES (?, ?, ?, ?)', this.now(), uid, ok ? 'notified' : 'notify_failed', kind);
  }
  clean() {
    const t = this.now();
    if (t - this.lastClean < 3600000) return;
    this.lastClean = t;
    this.q('DELETE FROM log WHERE ts < ?', t - LOG_KEEP_MS);
    this.q('DELETE FROM alerts WHERE ts < ?', t - LOG_KEEP_MS);
    this.q('DELETE FROM sessions WHERE exp < ?', Math.floor(t / 1000) - 3600);
    this.q('DELETE FROM devices WHERE last < ?', t - this.num('DEVICE_TTL_D', 30) * 86400000);
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
      if (p === '/v1/admin/wm') return await this.adminWm(req, b);
      if (p === '/v1/admin/devices/reset') return await this.adminDevReset(req, b);
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
    const devh = await sha256('dev:' + b.d), now = this.now();
    /* 每帳號最多 MAX_DEVICES 台裝置（預設 2）。管理者不限（Andy 自己會在多台電腦開）。
       超過＝這台拿不到資料權杖，記一筆 devices 異常；舊裝置 DEVICE_TTL_D 天沒用自動讓位，或管理者在異常頁按「清除裝置」。*/
    const known = this.q('SELECT 1 FROM devices WHERE uid = ? AND devh = ?', uid, devh).length > 0;
    if (!known && !me.user.admin) {
      const n = this.q('SELECT COUNT(*) AS c FROM devices WHERE uid = ? AND last >= ?', uid, now - this.num('DEVICE_TTL_D', 30) * 86400000)[0].c;
      if (n >= this.num('MAX_DEVICES', 2)) {
        await this.alert(uid, 'devices', `第 ${n + 1} 台裝置被擋（上限 ${this.num('MAX_DEVICES', 2)}）`);
        return this.json(req, { error: 'devices', max: this.num('MAX_DEVICES', 2) }, 403);
      }
    }
    this.q('INSERT INTO devices (uid, devh, first, last) VALUES (?, ?, ?, ?) ON CONFLICT(uid, devh) DO UPDATE SET last = excluded.last', uid, devh, now, now);
    const sid = rand(), exp = Math.floor(now / 1000) + SESSION_SEC;
    this.q('INSERT INTO sessions (sid, uid, plan, feats, devh, exp, ips) VALUES (?, ?, ?, ?, ?, ?, ?)',
      sid, uid, String(pm.plan || 'free'), JSON.stringify(pm.feats || {}), devh, exp, '[]');
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
      if (ips.size > this.num('MAX_IPS', 2)) await this.alert(who, 'multi_ip', [...ips].join(','));
    } else if (tier.feats.length) {
      feats = await this.guestFeats();
      if (!feats) return this.json(req, { error: 'upstream' }, 503);
    }
    if (!allowed(tier, feats || {})) return this.json(req, { error: who === 'guest' ? 'login' : 'plan', need: tier.feats }, who === 'guest' ? 401 : 403);
    const limit = who === 'guest' ? this.num('GUEST_PER_MIN', 120) : this.num('RATE_PER_MIN', 60);
    if (!this.rateOk(who === 'guest' ? 'ip:' + ip : who, limit)) {
      if (who !== 'guest') await this.alert(who, 'rate', `>${limit}/min`);
      return this.json(req, { error: 'rate' }, 429, { 'retry-after': '60' });
    }
    const t = this.now();
    this.q('INSERT INTO log (ts, uid, name, ip, ua) VALUES (?, ?, ?, ?, ?)', t, who, name, ip, ua);
    if (who !== 'guest') {
      if (!looksBrowser(req)) await this.alert(who, 'bot_ua', ua || '(空白)');
      const n = this.q('SELECT COUNT(DISTINCT name) AS c FROM log WHERE uid = ? AND ts > ?', who, t - 60000)[0].c;
      if (n > this.num('BURST_FILES', 30)) await this.alert(who, 'burst', `${n} 支／60 秒`);
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

  /* ---- (3) 管理者：異常、浮水印反查、清除裝置（管理者身分一律由 account-api 判定）*/
  async isAdminReq(b) {
    const me = b.t ? await this.acct('/v1/me', { t: b.t }) : null;
    return !me || !me.user ? 401 : me.user.admin ? 0 : 403;
  }
  /* 浮水印反查：貼上外流檔裡的 _wm.a（12 碼）→ 逐一比對最近 30 天有紀錄的帳號 */
  async adminWm(req, b) {
    const e = await this.isAdminReq(b); if (e) return this.json(req, { error: e === 401 ? 'auth' : 'forbidden' }, e);
    const a = String(b.wm || '').trim().replace(/^.*"a"\s*:\s*"([^"]+)".*$/s, '$1').slice(0, 12);
    if (!/^[A-Za-z0-9_-]{12}$/.test(a)) return this.json(req, { error: 'bad_wm' }, 400);
    const uids = this.q("SELECT DISTINCT uid FROM log WHERE uid != 'guest' UNION SELECT DISTINCT uid FROM devices").map((r) => r.uid);
    for (const u of uids) if ((await this.hmac('wm:' + u)).slice(0, 12) === a) {
      const last = this.q('SELECT ts, name, ip FROM log WHERE uid = ? ORDER BY ts DESC LIMIT 20', u);
      return this.json(req, { uid: u, last, checked: uids.length });
    }
    return this.json(req, { uid: null, checked: uids.length });
  }
  async adminDevReset(req, b) {
    const e = await this.isAdminReq(b); if (e) return this.json(req, { error: e === 401 ? 'auth' : 'forbidden' }, e);
    const uid = String(b.uid || '');
    if (!/^[A-Za-z0-9_-]{4,40}$/.test(uid)) return this.json(req, { error: 'bad_uid' }, 400);
    const n = this.q('SELECT COUNT(*) AS c FROM devices WHERE uid = ?', uid)[0].c;
    this.q('DELETE FROM devices WHERE uid = ?', uid);
    return this.json(req, { ok: true, removed: n });
  }
  async adminAlerts(req, b) {
    const e = await this.isAdminReq(b); if (e) return this.json(req, { error: e === 401 ? 'auth' : 'forbidden' }, e);
    return this.json(req, {
      devices: this.q('SELECT uid, COUNT(*) AS n, MAX(last) AS last FROM devices GROUP BY uid ORDER BY n DESC, last DESC LIMIT 300'),
      config: { auto: String(this.env.AUTO_SUSPEND) === '1', after: this.num('SUSPEND_AFTER', 3), windowH: this.num('SUSPEND_WINDOW_H', 24),
        maxDevices: this.num('MAX_DEVICES', 2), rate: this.num('RATE_PER_MIN', 60), burst: this.num('BURST_FILES', 30), maxIps: this.num('MAX_IPS', 2),
        notify: !!(this.env.ALERT_WEBHOOK || (this.env.ALERT_EMAIL && this.env.RESEND_API_KEY)) },
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
