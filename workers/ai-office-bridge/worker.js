/* AI Office 收件端（2026-11-14 第一版：只做擁有者本人一間辦公室）
 *
 * 誰會打這支：
 *   · 擁有者的 Claude Code 掛鉤（tools/ai_office_bridge/plugin/ai-office-bridge/scripts/bridge.py）
 *       POST /v1/events            Authorization: Bearer <接入碼>
 *   · 辦公室頁（site/office/world/js/live.js）
 *       GET  /v1/office/<id>/state?since=<序號>   Authorization: Bearer <接入碼>  或  X-AIO-Session: <網站登入權杖>（擁有者本人）
 *       POST /v1/claim             { t: <網站登入權杖>, rotate?: true }  → 只有網站管理者（擁有者）拿得到接入碼，而且只顯示這一次
 *       POST /v1/office/<id>/wipe  { t: <網站登入權杖> }                  → 擁有者刪除這間辦公室的所有事件紀錄
 *
 * 為什麼用 Durable Object（SQLite）而不是 D1 或 KV：
 *   · KV 免費額度每天只有 1,000 次寫入，每個掛鉤事件都是一次寫入，一個下午就用完。
 *   · D1 要先建資料庫、把資料庫代號寫進 wrangler.toml，部署流程多一步；Durable Object（SQLite）免費方案可用
 *     （每天 10 萬列寫入、500 萬列讀取），不用預先建任何資源，跟 workers/account-api 同一套做法。
 *   · 全部請求進同一個物件，天然排隊：派工說明與子 Agent 的配對、限速計數不會互相搶。
 *
 * 接入碼：Worker 只存 SHA-256 雜湊，原碼只在 /v1/claim 回應裡出現一次（擁有者本人登入網站後按鈕取得）。
 * 隱私：只收白名單欄位，字串一律截短並把路徑、網址、信箱、疑似金鑰的長字串遮掉（外掛那邊已經做過，這裡再做一次）。
 */

const DEFAULT_ORIGINS = 'https://liguligu-puipui.com https://www.liguligu-puipui.com https://miaozike.github.io';
const OFFICE = 'main';                 // 第一版只有擁有者本人一間
const MAX_BODY = 32 * 1024;            // 一次 POST 最多 32KB
const MAX_BATCH = 25;                  // 一次最多 25 筆事件
const KEEP_EVENTS = 5000;              // 每間辦公室最多留最近 5000 筆事件
const KEEP_DAYS = 14;                  // 工作階段、子 Agent 紀錄保留 14 天
const LIMITS = {
  events: [300, 60],                   // 每間辦公室每分鐘最多 300 筆事件
  read: [40, 60],                      // 每間辦公室＋來源每分鐘最多讀 40 次（頁面 15 秒一次＝4 次）
  badAuth: [20, 600],                  // 同一個來源 10 分鐘內接入碼錯 20 次就先擋
  claim: [6, 3600],                    // 領碼每小時最多 6 次
};
const STALE_MS = 3 * 3600e3;           // 子 Agent 超過 3 小時沒有任何消息：狀態標成「不明」，不當成還在做
const EVENTS = new Set(['SessionStart', 'SessionEnd', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'SubagentStart', 'SubagentStop', 'Stop', 'StopFailure', 'Notification', 'PermissionRequest', 'PreCompact']);
const TOOL_CATS = new Set(['read', 'write', 'search', 'test', 'deploy', 'wait', 'other', 'dispatch', 'ask', 'answered']);
const PERM_CATS = new Set(['command', 'edit', 'web', 'other']);

// ───────────────────────── 小工具 ─────────────────────────
const enc = new TextEncoder();
export async function sha256(s) {
  const d = await crypto.subtle.digest('SHA-256', enc.encode(String(s)));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('');
}
export function newCode() {
  const a = crypto.getRandomValues(new Uint8Array(24));
  return 'aio_' + btoa(String.fromCharCode(...a)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const FILE_RE = /[\w.-]+\.(?:m?js|cjs|tsx?|jsx|py|json|ya?ml|toml|md|html?|css|sh|bat|ps1|go|rs|java|kt|swift|rb|php|sql|csv|txt|png|jpe?g|gif|svg|pdf|parquet|lock|env|ini|cfg|xml|vue|c|h|cpp|ipynb)\b/gi;
const ID_RE = /^[A-Za-z0-9_.:-]{1,80}$/;
const SLUG_RE = /^[A-Za-z0-9_.:\- ]{1,64}$/;
const id = (v) => (typeof v === 'string' && ID_RE.test(v) ? v : null);
const slug = (v, n = 64) => (typeof v === 'string' && SLUG_RE.test(v) ? v.slice(0, n) : null);
const int = (v, max = 1e12) => (typeof v === 'number' && Number.isFinite(v) && v >= 0 ? Math.min(Math.round(v), max) : null);
const bool = (v) => (typeof v === 'boolean' ? v : null);

/** 文字去識別：去控制字元、收空白、遮路徑／網址／信箱／疑似金鑰，再截短。外掛已經做過，這裡是第二道。 */
export function scrub(v, n) {
  if (typeof v !== 'string') return null;
  let s = v.replace(/[\u0000-\u001f\u007f]+/g, ' ');
  s = s.replace(/https?:\/\/\S+/gi, '〔網址〕');
  s = s.replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, '〔信箱〕');
  s = s.replace(/(?:[A-Za-z]:\\|~\/|\/)(?:[^\s/\\]+[/\\])+[^\s/\\]*/g, '〔路徑〕');
  s = s.replace(/(?:[\w.-]*[A-Za-z][\w.-]*\/)+[\w.-]+/g, '〔路徑〕');
  s = s.replace(FILE_RE, '〔檔名〕');
  s = s.replace(/\b[A-Za-z0-9_\-]{28,}\b/g, '〔遮蔽〕');
  s = s.replace(/\s+/g, ' ').trim();
  if (!s) return null;
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

/** 只留白名單欄位；不認得的事件整筆丟掉（回傳 null）。 */
export function clean(e) {
  if (!e || typeof e !== 'object' || Array.isArray(e)) return null;
  const kind = typeof e.event === 'string' ? e.event : typeof e.hook_event_name === 'string' ? e.hook_event_name : '';
  if (!EVENTS.has(kind)) return null;
  const o = { event: kind };
  const ts = int(e.ts); if (ts != null) o.ts = ts < 1e12 ? ts * 1000 : ts;       // 秒或毫秒都收
  const put = (k, v) => { if (v != null) o[k] = v; };
  put('session_id', id(e.session_id));
  put('project_name', scrub(e.project_name, 60));
  put('project_hash', typeof e.project_hash === 'string' && /^[0-9a-f]{16}$/.test(e.project_hash) ? e.project_hash : null);
  put('cloud', bool(e.cloud));
  put('agent_id', id(e.agent_id));
  put('agent_type', slug(e.agent_type));
  put('subagent_type', slug(e.subagent_type));
  put('source', slug(e.source, 20));
  put('reason', slug(e.reason, 40));
  put('permission_mode', slug(e.permission_mode, 20));
  put('tool_category', typeof e.tool_category === 'string' && TOOL_CATS.has(e.tool_category) ? e.tool_category : null);
  put('perm_category', typeof e.perm_category === 'string' && PERM_CATS.has(e.perm_category) ? e.perm_category : null);
  put('notification_type', slug(e.notification_type, 40));
  put('description', scrub(e.description, 80));
  put('summary', scrub(e.summary, 120));
  put('prompt_is_system', bool(e.prompt_is_system));
  put('prompt_chars', int(e.prompt_chars, 1e6));
  put('spawned_agent_id', id(e.spawned_agent_id));
  put('spawn_status', slug(e.spawn_status, 20));
  put('total_tokens', int(e.totalTokens ?? e.total_tokens, 1e10));
  put('duration_ms', int(e.totalDurationMs ?? e.duration_ms, 1e10));
  put('tool_uses', int(e.totalToolUseCount ?? e.tool_uses, 1e6));
  put('background_running', int(e.background_running, 1000));
  put('error_type', slug(e.error_type, 40));
  put('usage_main', int(e.usage_main, 1e10));
  if (e.usage && typeof e.usage === 'object') {
    const u = {}; for (const k of ['input', 'output', 'cache_read', 'cache_write', 'requests']) { const v = int(e.usage[k], 1e10); if (v != null) u[k] = v; }
    if (Object.keys(u).length) o.usage = u;
  }
  if (e.usage_subagents && typeof e.usage_subagents === 'object' && !Array.isArray(e.usage_subagents)) {
    const m = {}; let n = 0;
    for (const [k, v] of Object.entries(e.usage_subagents)) { if (n >= 50) break; const kk = id(k), vv = int(v, 1e10); if (kk && vv != null) { m[kk] = vv; n++; } }
    if (n) o.usage_subagents = m;
  }
  if (e.rate_limits && typeof e.rate_limits === 'object') {
    const r = {}; for (const w of ['five_hour', 'seven_day']) { const x = e.rate_limits[w]; if (x && typeof x === 'object') { const p = typeof x.used_percentage === 'number' && x.used_percentage >= 0 && x.used_percentage <= 100 ? Math.round(x.used_percentage * 10) / 10 : null; const t = int(x.resets_at); if (p != null) r[w] = { used_percentage: p, resets_at: t }; } }
    if (Object.keys(r).length) o.rate_limits = r;
  }
  return o;
}

const tokensOf = (u) => (u ? (u.input || 0) + (u.output || 0) + (u.cache_write || 0) : null);

// ───────────────────────── 對外入口：全部轉給同一個 Durable Object ─────────────────────────
export default {
  async fetch(req, env) {
    if (!env.HUB) return new Response('{"error":"not_configured"}', { status: 503, headers: { 'Content-Type': 'application/json' } });
    const stub = env.HUB.get(env.HUB.idFromName('hub'));
    return stub.fetch(req);
  },
};

export class Hub {
  constructor(state, env) {
    this.state = state; this.env = env || {}; this.sql = state.storage.sql; this.ready = false; this.sess = new Map(); this.nIns = 0;
  }
  now() { return Date.now(); }
  q(s, ...a) { return this.sql.exec(s, ...a).toArray(); }
  init() {
    if (this.ready) return;
    const T = [
      'CREATE TABLE IF NOT EXISTS codes (hash TEXT PRIMARY KEY, office TEXT NOT NULL, role TEXT NOT NULL, created INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)',
      'CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, office TEXT NOT NULL, ts INTEGER, rcv INTEGER NOT NULL, kind TEXT NOT NULL, sid TEXT, ph TEXT, agent_id TEXT, agent_type TEXT, data TEXT NOT NULL)',
      'CREATE INDEX IF NOT EXISTS ev_office ON events (office, seq)',
      'CREATE TABLE IF NOT EXISTS projects (office TEXT NOT NULL, ph TEXT NOT NULL, name TEXT, first INTEGER, last INTEGER, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (office, ph))',
      'CREATE TABLE IF NOT EXISTS sessions (office TEXT NOT NULL, sid TEXT NOT NULL, ph TEXT, pname TEXT, cloud INTEGER, started INTEGER, last INTEGER, ended INTEGER, state TEXT, flag TEXT, perm TEXT, prompts INTEGER NOT NULL DEFAULT 0, turns INTEGER NOT NULL DEFAULT 0, summary TEXT, tokens INTEGER, PRIMARY KEY (office, sid))',
      'CREATE TABLE IF NOT EXISTS agents (office TEXT NOT NULL, aid TEXT NOT NULL, sid TEXT, ph TEXT, type TEXT, descr TEXT, started INTEGER, last INTEGER, ended INTEGER, status TEXT, tool TEXT, tool_at INTEGER, summary TEXT, tokens INTEGER, dur INTEGER, PRIMARY KEY (office, aid))',
      'CREATE TABLE IF NOT EXISTS dispatch (rid INTEGER PRIMARY KEY, office TEXT NOT NULL, sid TEXT, type TEXT, descr TEXT, at INTEGER)',
      'CREATE TABLE IF NOT EXISTS quota (office TEXT PRIMARY KEY, data TEXT, at INTEGER)',
      'CREATE TABLE IF NOT EXISTS rl (k TEXT PRIMARY KEY, win INTEGER NOT NULL, n INTEGER NOT NULL)',
    ];
    for (const s of T) this.sql.exec(s);
    this.ready = true;
  }

  // ── CORS ──
  origins() { return String(this.env.ALLOWED_ORIGINS || DEFAULT_ORIGINS).split(/[\s,]+/).filter(Boolean); }
  originOk(o) { return !!o && this.origins().includes(o); }
  json(req, obj, status = 200, extra = {}) {
    const h = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra };
    const o = req.headers.get('Origin');
    if (this.originOk(o)) { h['Access-Control-Allow-Origin'] = o; h.Vary = 'Origin'; }
    return new Response(JSON.stringify(obj), { status, headers: h });
  }

  // ── 限速（固定時間窗計數）。回傳 true＝還在額度內 ──
  hit(key, [limit, winSec]) {
    const win = Math.floor(this.now() / 1000 / winSec);
    const r = this.q('SELECT win, n FROM rl WHERE k = ?', key)[0];
    const n = r && r.win === win ? r.n + 1 : 1;
    this.sql.exec('INSERT INTO rl (k, win, n) VALUES (?, ?, ?) ON CONFLICT(k) DO UPDATE SET win = excluded.win, n = excluded.n', key, win, n);
    return n <= limit;
  }
  addHits(key, [limit, winSec], k) {
    const win = Math.floor(this.now() / 1000 / winSec);
    const r = this.q('SELECT win, n FROM rl WHERE k = ?', key)[0];
    const n = (r && r.win === win ? r.n : 0) + k;
    this.sql.exec('INSERT INTO rl (k, win, n) VALUES (?, ?, ?) ON CONFLICT(k) DO UPDATE SET win = excluded.win, n = excluded.n', key, win, n);
    return n <= limit;
  }
  ip(req) { return req.headers.get('CF-Connecting-IP') || 'local'; }

  // ── 身分 ──
  async codeOffice(req) {
    const m = /^Bearer\s+(\S{8,200})$/i.exec(req.headers.get('Authorization') || '');
    if (!m) return null;
    const r = this.q('SELECT office, role FROM codes WHERE hash = ? AND revoked = 0', await sha256(m[1]))[0];
    return r ? r.office : false;          // false＝帶了碼但不對
  }
  /** 網站登入權杖 → 是不是管理者（擁有者）。用服務綁定（ACCOUNT → tw-account）問 /v1/me，結果快取 10 分鐘。 */
  async isOwner(tok) {
    if (typeof tok !== 'string' || tok.length < 20 || tok.length > 4000) return false;
    const k = await sha256(tok), c = this.sess.get(k), now = this.now();
    if (c && c.exp > now) return c.ok;
    let ok = false;
    try {
      const init = { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: this.origins()[0] }, body: JSON.stringify({ t: tok }) };
      let r = null;
      if (this.env.ACCOUNT && this.env.ACCOUNT.fetch) r = await this.env.ACCOUNT.fetch('https://account.internal/v1/me', init);
      else if (this.env.ACCOUNT_API_URL) r = await fetch(String(this.env.ACCOUNT_API_URL).replace(/\/+$/, '') + '/v1/me', init);
      if (r && r.ok) { const j = await r.json(); ok = !!(j && j.user && j.user.admin); }
    } catch (e) { ok = false; }
    if (this.sess.size > 200) this.sess.clear();
    this.sess.set(k, { ok, exp: now + (ok ? 600e3 : 60e3) });
    return ok;
  }
  async readerOffice(req) {
    const c = await this.codeOffice(req);
    if (c) return c;
    const s = req.headers.get('X-AIO-Session');
    if (s && await this.isOwner(s)) return OFFICE;
    if (c === false || s) return false;
    return null;
  }

  async fetch(req) {
    this.init();
    const url = new URL(req.url), p = url.pathname.replace(/\/+$/, '') || '/';
    const origin = req.headers.get('Origin');
    if (req.method === 'OPTIONS') {
      if (!this.originOk(origin)) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: { 'Access-Control-Allow-Origin': origin, Vary: 'Origin', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'authorization, content-type, x-aio-session', 'Access-Control-Max-Age': '600' } });
    }
    // 瀏覽器帶了不在白名單的來源：一律拒絕（外掛從終端機送出時不會帶 Origin）
    if (origin && !this.originOk(origin)) return this.json(req, { error: 'origin' }, 403);
    try {
      if (req.method === 'GET' && p === '/health') return this.json(req, { ok: true, service: 'ai-office-bridge', version: 1, claimed: this.q('SELECT COUNT(*) AS n FROM codes WHERE revoked = 0')[0].n > 0 });
      if (req.method === 'POST' && p === '/v1/events') return await this.ingest(req);
      if (req.method === 'POST' && p === '/v1/claim') return await this.claim(req);
      let m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/state$/.exec(p);
      if (req.method === 'GET' && m) return await this.read(req, m[1], url);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/wipe$/.exec(p);
      if (req.method === 'POST' && m) return await this.wipe(req, m[1]);
      return this.json(req, { error: 'not_found' }, 404);
    } catch (e) {
      return this.json(req, { error: 'server' }, 500);
    }
  }

  async body(req) {
    const len = +(req.headers.get('Content-Length') || 0);
    if (len > MAX_BODY) return { err: 'too_large' };
    const raw = await req.text();
    if (raw.length > MAX_BODY) return { err: 'too_large' };
    try { const b = JSON.parse(raw || '{}'); return b && typeof b === 'object' ? { b } : { err: 'bad_json' }; } catch (e) { return { err: 'bad_json' }; }
  }

  // ───────── POST /v1/events ─────────
  async ingest(req) {
    const office = await this.codeOffice(req);
    if (!office) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, err === 'too_large' ? 413 : 400);
    const list = Array.isArray(b) ? b : Array.isArray(b.events) ? b.events : [b];
    if (list.length > MAX_BATCH) return this.json(req, { error: 'too_many' }, 413);
    if (!this.addHits('ev:' + office, LIMITS.events, list.length)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '60' });
    let accepted = 0, dropped = 0;
    for (const raw of list) {
      const e = clean(raw);
      if (!e) { dropped++; continue; }
      this.apply(office, e); accepted++;
    }
    if (++this.nIns % 50 === 0) this.prune(office);
    return this.json(req, { ok: true, accepted, dropped });
  }

  apply(office, e) {
    const rcv = this.now(), sid = e.session_id || null, ph = e.project_hash || null;
    this.sql.exec('INSERT INTO events (office, ts, rcv, kind, sid, ph, agent_id, agent_type, data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      office, e.ts || null, rcv, e.event, sid, ph, e.agent_id || e.spawned_agent_id || null, e.agent_type || e.subagent_type || null, JSON.stringify(e));
    if (ph) this.sql.exec('INSERT INTO projects (office, ph, name, first, last, n) VALUES (?, ?, ?, ?, ?, 1) ON CONFLICT(office, ph) DO UPDATE SET name = COALESCE(excluded.name, name), last = excluded.last, n = n + 1', office, ph, e.project_name || null, rcv, rcv);
    if (e.rate_limits) this.sql.exec('INSERT INTO quota (office, data, at) VALUES (?, ?, ?) ON CONFLICT(office) DO UPDATE SET data = excluded.data, at = excluded.at', office, JSON.stringify(e.rate_limits), rcv);
    if (!sid) return;
    // 工作階段：第一次看到就建立（就算沒收到 SessionStart，例如外掛是中途才裝的）
    this.sql.exec(`INSERT INTO sessions (office, sid, ph, pname, cloud, started, last, state) VALUES (?, ?, ?, ?, ?, ?, ?, 'idle')
      ON CONFLICT(office, sid) DO UPDATE SET last = excluded.last, ph = COALESCE(excluded.ph, ph), pname = COALESCE(excluded.pname, pname), cloud = COALESCE(excluded.cloud, cloud)`,
      office, sid, ph, e.project_name || null, e.cloud == null ? null : e.cloud ? 1 : 0, rcv, rcv);
    const S = (set, ...a) => this.sql.exec(`UPDATE sessions SET ${set} WHERE office = ? AND sid = ?`, ...a, office, sid);
    const cat = e.tool_category;
    switch (e.event) {
      case 'SessionStart': S("started = ?, ended = NULL, state = 'idle', flag = NULL", rcv); break;
      case 'SessionEnd': S("ended = ?, state = 'ended', flag = NULL", rcv); break;
      case 'UserPromptSubmit': if (!e.prompt_is_system) S("state = 'working', flag = NULL, prompts = prompts + 1, ended = NULL"); break;
      case 'Stop': S("state = 'idle', flag = NULL, turns = turns + 1, summary = ?, tokens = COALESCE(?, tokens)", e.summary || null, e.usage_main ?? null); break;
      case 'StopFailure': S("state = 'error', flag = NULL"); break;
      case 'PermissionRequest': S("flag = 'permission', perm = ?", e.perm_category || 'other'); break;
      case 'Notification':
        if (e.notification_type === 'permission_prompt') S("flag = 'permission', perm = COALESCE(perm, 'other')");
        else if (e.notification_type === 'elicitation_dialog') S("flag = 'question'");
        break;
      case 'PreToolUse':
        if (cat === 'ask') S("flag = 'question', state = 'working'");
        else S("flag = NULL, state = 'working', ended = NULL");
        break;
      case 'PostToolUse': if (cat === 'answered') S('flag = NULL'); break;
    }
    // 子 Agent
    const A = (aid, set, ...a) => this.sql.exec(`UPDATE agents SET ${set} WHERE office = ? AND aid = ?`, ...a, office, aid);
    if (e.event === 'PreToolUse' && cat === 'dispatch') {
      this.sql.exec('INSERT INTO dispatch (office, sid, type, descr, at) VALUES (?, ?, ?, ?, ?)', office, sid, e.subagent_type || 'general-purpose', e.description || null, rcv);
    }
    if (e.event === 'SubagentStart' && e.agent_id) {
      const type = e.agent_type || 'general-purpose';
      const d = this.q('SELECT rid, descr FROM dispatch WHERE office = ? AND sid = ? AND type = ? AND at > ? ORDER BY rid LIMIT 1', office, sid, type, rcv - 600e3)[0];
      if (d) this.sql.exec('DELETE FROM dispatch WHERE rid = ?', d.rid);
      this.sql.exec(`INSERT INTO agents (office, aid, sid, ph, type, descr, started, last, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running')
        ON CONFLICT(office, aid) DO UPDATE SET status = 'running', ended = NULL, last = excluded.last, descr = COALESCE(excluded.descr, descr)`,
        office, e.agent_id, sid, ph, type, (d && d.descr) || e.description || null, rcv, rcv);
    }
    if (e.agent_id && e.event === 'PreToolUse' && cat && cat !== 'dispatch') A(e.agent_id, 'tool = ?, tool_at = ?, last = ?', cat, rcv, rcv);
    if (e.event === 'SubagentStop' && e.agent_id) {
      const failed = /^(失敗|錯誤)[:：]/.test(e.summary || '');
      const tok = tokensOf(e.usage);
      const ex = this.q('SELECT started FROM agents WHERE office = ? AND aid = ?', office, e.agent_id)[0];
      if (!ex) this.sql.exec("INSERT INTO agents (office, aid, sid, ph, type, started, last, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'running')", office, e.agent_id, sid, ph, e.agent_type || 'general-purpose', null, rcv);
      A(e.agent_id, 'ended = ?, last = ?, status = ?, summary = ?, tokens = COALESCE(?, tokens), dur = COALESCE(dur, CASE WHEN started IS NULL THEN NULL ELSE ? - started END), tool = NULL',
        rcv, rcv, failed ? 'failed' : 'done', e.summary || null, tok, rcv);
    }
    if (e.event === 'PostToolUse' && cat === 'dispatch' && e.spawned_agent_id) {
      A(e.spawned_agent_id, 'tokens = COALESCE(?, tokens), dur = COALESCE(?, dur)', e.total_tokens ?? null, e.spawn_status === 'completed' ? e.duration_ms ?? null : null);
    }
    if (e.event === 'Stop' && e.usage_subagents) for (const [aid, t] of Object.entries(e.usage_subagents)) A(aid, 'tokens = ?', t);
  }

  prune(office) {
    const cut = this.q('SELECT seq FROM events WHERE office = ? ORDER BY seq DESC LIMIT 1 OFFSET ?', office, KEEP_EVENTS)[0];
    if (cut) this.sql.exec('DELETE FROM events WHERE office = ? AND seq <= ?', office, cut.seq);
    const old = this.now() - KEEP_DAYS * 86400e3;
    this.sql.exec('DELETE FROM agents WHERE office = ? AND COALESCE(ended, last) < ?', office, old);
    this.sql.exec('DELETE FROM sessions WHERE office = ? AND last < ?', office, old);
    this.sql.exec('DELETE FROM dispatch WHERE office = ? AND at < ?', office, this.now() - 3600e3);
    this.sql.exec('DELETE FROM rl WHERE win < ?', Math.floor(this.now() / 1000 / 3600) - 2);
  }

  // ───────── GET /v1/office/<id>/state ─────────
  async read(req, office, url) {
    const who = await this.readerOffice(req);
    if (!who) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    if (who !== office) return this.json(req, { error: 'forbidden' }, 403);
    if (!this.hit('rd:' + office + ':' + this.ip(req), LIMITS.read)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const now = this.now(), since = Math.max(0, parseInt(url.searchParams.get('since') || '0', 10) || 0);
    const evRows = since > 0
      ? this.q('SELECT seq, ts, rcv, data FROM events WHERE office = ? AND seq > ? ORDER BY seq LIMIT 300', office, since)
      : this.q('SELECT seq, ts, rcv, data FROM events WHERE office = ? ORDER BY seq DESC LIMIT 60', office).reverse();
    const events = evRows.map((r) => { const d = JSON.parse(r.data); delete d.usage_subagents; delete d.rate_limits; return { seq: r.seq, ts: r.ts, rcv: r.rcv, ...d }; });
    const top = this.q('SELECT MAX(seq) AS s, MAX(rcv) AS t, COUNT(*) AS n FROM events WHERE office = ?', office)[0] || {};
    const projects = this.q('SELECT ph AS hash, name, first, last, n AS events FROM projects WHERE office = ? ORDER BY last DESC LIMIT 30', office);
    const sessions = this.q('SELECT sid AS id, ph AS project_hash, pname AS project_name, cloud, started, last, ended, state, flag, perm, prompts, turns, summary, tokens FROM sessions WHERE office = ? AND last > ? ORDER BY last DESC LIMIT 40', office, now - 7 * 86400e3)
      .map((s) => ({ ...s, cloud: s.cloud == null ? null : !!s.cloud }));
    const agents = this.q('SELECT aid AS agent_id, sid AS session_id, ph AS project_hash, type AS agent_type, descr AS description, started, last, ended, status, tool, tool_at, summary, tokens, dur AS duration_ms FROM agents WHERE office = ? AND (ended IS NULL OR ended > ?) ORDER BY COALESCE(ended, last) DESC LIMIT 200', office, now - 86400e3)
      .map((a) => (a.status === 'running' && now - (a.last || 0) > STALE_MS ? { ...a, status: 'unknown' } : a));
    // 各子 Agent 類型：近 7 天的真實統計（前端績效總表用；樣本不足由前端判斷並標示）
    const since7 = now - 7 * 86400e3;
    const types = this.q(`SELECT type AS agent_type, COUNT(*) AS dispatched,
        SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
        SUM(CASE WHEN status = 'running' AND ? - last <= ? THEN 1 ELSE 0 END) AS running,
        AVG(CASE WHEN status IN ('done', 'failed') THEN dur END) AS avg_ms, SUM(CASE WHEN status IN ('done', 'failed') AND dur IS NOT NULL THEN 1 ELSE 0 END) AS n_dur,
        SUM(tokens) AS tokens, SUM(CASE WHEN tokens IS NOT NULL THEN 1 ELSE 0 END) AS n_tokens, MAX(COALESCE(ended, last)) AS last
      FROM agents WHERE office = ? AND COALESCE(started, last) > ? GROUP BY type ORDER BY dispatched DESC LIMIT 100`, now, STALE_MS, office, since7)
      .map((t) => ({ ...t, avg_ms: t.avg_ms == null ? null : Math.round(t.avg_ms) }));
    const ceo = this.q('SELECT COUNT(*) AS sessions, SUM(prompts) AS prompts, SUM(turns) AS turns, SUM(tokens) AS tokens FROM sessions WHERE office = ? AND last > ?', office, since7)[0] || {};
    const qr = this.q('SELECT data, at FROM quota WHERE office = ?', office)[0];
    return this.json(req, {
      office, now, seq: top.s || 0, since, initial: since === 0, total_events: top.n || 0, last_event_at: top.t || null,
      projects, sessions, agents, types, ceo, quota: qr ? { rate_limits: JSON.parse(qr.data), at: qr.at } : null, events,
    });
  }

  // ───────── POST /v1/claim：擁有者本人登入網站後領接入碼（只顯示這一次） ─────────
  async claim(req) {
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    if (!this.hit('claim:' + this.ip(req), LIMITS.claim)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '3600' });
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, 400);
    if (!this.env.ACCOUNT && !this.env.ACCOUNT_API_URL) return this.json(req, { error: 'no_account' }, 503);
    if (!(await this.isOwner(b.t))) return this.json(req, { error: 'not_owner' }, 403);
    const cur = this.q("SELECT created FROM codes WHERE office = ? AND role = 'ingest' AND revoked = 0 ORDER BY created DESC LIMIT 1", OFFICE)[0];
    if (cur && b.rotate !== true) return this.json(req, { ok: true, office: OFFICE, exists: true, created: cur.created });
    const code = newCode(), now = this.now();
    this.sql.exec("UPDATE codes SET revoked = 1 WHERE office = ? AND role = 'ingest'", OFFICE);
    this.sql.exec("INSERT INTO codes (hash, office, role, created) VALUES (?, ?, 'ingest', ?)", await sha256(code), OFFICE, now);
    return this.json(req, { ok: true, office: OFFICE, code, created: now, rotated: !!cur });
  }

  // ───────── POST /v1/office/<id>/wipe：擁有者刪除所有事件紀錄（接入碼保留） ─────────
  async wipe(req, office) {
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, 400);
    if (office !== OFFICE || !(await this.isOwner(b.t))) return this.json(req, { error: 'not_owner' }, 403);
    for (const t of ['events', 'projects', 'sessions', 'agents', 'dispatch', 'quota']) this.sql.exec(`DELETE FROM ${t} WHERE office = ?`, office);
    return this.json(req, { ok: true });
  }

  /** 測試與本機開發用：直接發一組接入碼（不經過網站登入）。正式環境沒有任何路由會呼叫它。 */
  async devIssue(office = OFFICE) {
    this.init();
    const code = newCode();
    this.sql.exec("INSERT INTO codes (hash, office, role, created) VALUES (?, ?, 'ingest', ?)", await sha256(code), office, this.now());
    return code;
  }
}
