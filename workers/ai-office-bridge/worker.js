/* AI Office 收件端（2026-11-14 第一版：只做擁有者本人一間辦公室）
 *
 * 誰會打這支：
 *   · 擁有者的 Claude Code 掛鉤（tools/ai_office_bridge/plugin/ai-office-bridge/scripts/bridge.py）
 *       POST /v1/events            Authorization: Bearer <接入碼>
 *   · 辦公室頁（site/office/world/js/live.js）
 *       GET  /v1/office/<id>/state?since=<序號>   Authorization: Bearer <接入碼>  或  X-AIO-Session: <網站登入權杖>（擁有者本人）
 *       POST /v1/claim             { t: <網站登入權杖>, rotate?: true }  → 只有網站管理者（擁有者）拿得到接入碼，而且只顯示這一次
 *       POST /v1/office/<id>/wipe  { t: <網站登入權杖> }                  → 擁有者刪除這間辦公室的所有事件紀錄
 *   · 雲端存檔（2026-11-16）：GET／POST /v1/office/<id>/save/<專案>  站長登入（X-AIO-Session＋白名單 Origin）；{ schema, base, at, data:{keys} }，版本號、舊格式遷移、最後寫入時間衝突處理
 *   · 每日用量（2026-11-16）：GET /v1/office/<id>/usage?project=<雜湊>&days=7  接入碼或站長登入；真的 Token 記差額，取不到時以工具次數推估（estimated）
 *   · 網站指令收件匣（2026-11-15，規格 docs/ai_office/chat_command_spec.md）
 *       網站端（只收擁有者登入：X-AIO-Session，且必須帶白名單 Origin；接入碼不能寫收件匣）
 *         POST /v1/office/<id>/inbox                 { to, text }   → 排隊一則指令
 *         GET  /v1/office/<id>/inbox?since=<rev>                    → 指令列表與狀態、回覆
 *         POST /v1/office/<id>/inbox/<mid>/cancel                   → 撤回還在排隊的指令
 *       Claude 端（只收接入碼，而且「不准」帶 Origin：瀏覽器拿到碼也取不走指令）
 *         POST /v1/inbox/pull  { session_id, wait?, max? }          → 取走排隊中的指令（可長輪詢，最多等 20 秒）
 *         POST /v1/inbox/ack   { id, status, reply?, session_id }   → 回報執行中／完成／失敗與回覆
 *   · 辦公室與專案（2026-11-15：一個專案一間辦公室，規格見 docs/ai_office/plan.md 最後一節）
 *       GET  /v1/office/<id>/projects             → 專案清單（名稱、最後活動、進行中工作階段數），入口頁用
 *       GET  /v1/office/<id>/state?project=<雜湊>  → 只回單一專案的事件、工作階段、子 Agent、統計；不帶＝全部
 *       GET  /v1/offices、POST /v1/offices、POST /v1/offices/<o_…>、POST /v1/offices/<o_…>/delete
 *                                                → 登入帳號底下的辦公室清單（建立、改名、綁專案、刪除）。非站長 3 間、每間 5 位 Agent 由伺服器擋
 *       指令收件匣：POST …/inbox 可帶 project（專案雜湊）；Claude 端 pull 帶自己的 project_hash，只取自己專案（或沒指定專案）的指令
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
const STALE_MS = 3 * 3600e3;
// ── 多辦公室（2026-11-15：一個專案一間辦公室）──
// 辦公室清單存在登入帳號底下；一間辦公室可綁定一或多個專案（project_hash）。辦公室只是「看哪些專案」的檢視，事件仍存在接入碼那一間（OFFICE）。
const OFFICES = { adminMax: 20, memberMax: 3, memberAgents: 5, nameMax: 20, maxProjects: 10 };
const ACTIVE_MS = 6 * 3600e3;          // 工作階段沒結束、而且 6 小時內有動靜＝進行中（跟網頁端 live.js 同一個門檻）
const PH_RE = /^[0-9a-f]{16}$/;
LIMITS.offices = [60, 60];
// ── 專案名冊（2026-11-16）：每個專案自己的員工名單＝專案 .claude/agents/ 的檔名（外掛在 SessionStart 附上）∪ 事件裡出現過的子 Agent 類型 ──
const ROSTER = { maxFiles: 50, max: 50 };
const AGENT_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;
// 專案名稱沒有意義（雲端工作階段沒掛儲存庫時是資料夾名 user／root…）：全部歸成同一個「雲端工作階段」專案。跟前端 site/office/projname.js 的 NONAME 同一份名單
const NONAME_RE = /^(user|users|root|home|tmp|temp|workspace|workspaces|work|mnt|opt|var|app|runner|ubuntu|admin|sandbox|project|projects|repo|repos|src|code|dev|data|claude)$/i;
/** 專案合併鍵：同名（不分大小寫）的專案算同一個；沒意義的名稱全部算「雲端」；沒名稱的各自獨立。
 *  為什麼在伺服器合併：舊事件是路徑雜湊、新事件是儲存庫雜湊，同一個專案會有兩個雜湊；入口、辦公室、收件匣都靠雜湊，
 *  在這一層把別名收成一組，前端與外掛都不用改，舊連結（帶舊雜湊）也照樣進得去。 */
export function projectKey(name, hash) {
  const t = typeof name === 'string' ? name.replace(/\s+/g, ' ').trim() : '';
  if (!t) return 'h:' + hash;
  return NONAME_RE.test(t) ? 'cloud' : 'n:' + t.toLowerCase();
}
// ── 網站指令收件匣 ──
const INBOX = {
  maxText: 2000,                       // 一則指令最多 2000 字
  maxReply: 4000,                      // 回覆最多 4000 字
  maxPending: 20,                      // 排隊中最多 20 則（滿了就請擁有者先等 Claude 取走）
  keep: 500,                           // 每間辦公室保留最近 500 則
  expireMs: 24 * 3600e3,               // 排隊超過 24 小時沒人取走：過期，不再交給 Claude
  claimedStaleMs: 30 * 60e3,           // 取走後 30 分鐘沒回報「執行中」：顯示「沒有回音」
  runningStaleMs: 6 * 3600e3,          // 執行中超過 6 小時沒有更新：顯示「沒有回音」
  maxWaitS: 20,                        // 長輪詢一次最多等 20 秒
  maxPull: 5,                          // 一次最多取 5 則
};
LIMITS.inboxSend = [10, 60];           // 擁有者每分鐘最多送 10 則
LIMITS.inboxDay = [100, 86400];        // 每天最多 100 則
LIMITS.inboxMember = [5, 60];          // 一般會員每分鐘最多 5 則（站長 10）
LIMITS.inboxDayMember = [50, 86400];  // 一般會員每天最多 50 則
LIMITS.inboxPull = [120, 60];          // Claude 端每分鐘最多取 120 次（掛鉤＋待命）
LIMITS.inboxAck = [120, 60];
const ACK_STATUS = new Set(['running', 'done', 'failed']);
const TO_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;
/** 回覆文字：去控制字元（保留換行）、遮疑似金鑰，截短。回覆只給擁有者看，所以網址與路徑保留（預覽網址要能點）。 */
export function maskSecrets(v, n) {
  if (typeof v !== 'string') return null;
  let s = v.replace(/[\u0000-\u0009\u000b-\u001f\u007f]+/g, ' ');
  s = s.replace(/\b(?:aio|ghp|gho|ghs|ghu|github_pat|sk|sk-ant|xox[abprs]|AKIA)[-_A-Za-z0-9]{12,}/g, '〔遮蔽〕');
  s = s.replace(/\bBearer\s+\S{12,}/gi, 'Bearer 〔遮蔽〕');
  s = s.replace(/\b[A-Za-z0-9+\/_-]{48,}={0,2}/g, '〔遮蔽〕');
  s = s.trim();
  if (!s) return null;
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}
const sleepOrWake = (hub, ms) => new Promise((res) => {
  const w = { res }; hub.waiters.add(w);
  w.t = setTimeout(() => { hub.waiters.delete(w); res(); }, ms);
});           // 子 Agent 超過 3 小時沒有任何消息：狀態標成「不明」，不當成還在做
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
  put('task_name', scrub(e.task_name, 24));                 // 任務簡稱（Claude 自己取的 6～12 字），名牌顯示「<簡稱> CEO」
  put('project_hash', typeof e.project_hash === 'string' && /^[0-9a-f]{16}$/.test(e.project_hash) ? e.project_hash : null);
  put('cloud', bool(e.cloud));
  if (Array.isArray(e.agent_files)) {                        // 專案 .claude/agents/ 的檔名（去副檔名）。只收名稱格式合格的、最多 50 個，其餘丟掉
    const f = []; for (const n of e.agent_files) { if (f.length >= ROSTER.maxFiles) break; if (typeof n === 'string' && AGENT_NAME_RE.test(n) && !f.includes(n)) f.push(n); }
    o.agent_files = f;
  }
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

/** 每間辦公室最多幾位 Agent（以「類型」計：同一類型的多個子 Agent 算同一位同事）。留下最近有動靜的 cap 種類型，其餘不回傳。
 *  為什麼在伺服器擋：前端只是畫面，使用者清掉瀏覽器儲存或改程式就繞過了。cap 為空（站長）＝不限。 */
export function capAgents(agents, cap) {
  if (!cap || cap < 1) return { agents, capped: 0 };
  const last = new Map();
  for (const a of agents) { const t = a.agent_type || '?', v = a.ended || a.last || 0; if (!last.has(t) || last.get(t) < v) last.set(t, v); }
  const keep = new Set([...last.entries()].sort((x, y) => y[1] - x[1]).slice(0, cap).map((e) => e[0]));
  return { agents: agents.filter((a) => keep.has(a.agent_type || '?')), capped: Math.max(0, last.size - cap) };
}
/** 辦公室名稱：去控制字元、收空白、最多 20 字 */
export function cleanOfficeName(v) {
  if (typeof v !== 'string') return null;
  const t = v.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
  return t && [...t].length <= OFFICES.nameMax ? t : null;
}
// ───────── 雲端存檔（2026-11-16，研究報告第 9 項）─────────
// 每個專案一份存檔：網站用站長登入（X-AIO-Session）讀寫；內容是辦公室頁 localStorage 裡 aiOffice.game.*、aiOffice.world.*（擺設／整修）的字串值。
// 版本號 ver：每寫一次 +1。前端帶 base（它最後看到的版本）來寫：base 對得上＝直接寫；對不上＝比「最後寫入時間」（at，前端本機最後一次改動的時間），
// 比較新的贏（last-write-wins），比較舊的回 409 並附上伺服器那份，讓前端合併。schema：存檔格式版本，舊格式由 migrateSave 升上來。
export const SAVE = { schema: 2, maxBody: 96 * 1024, maxData: 64 * 1024, maxKeys: 80, maxVal: 24 * 1024, maxProjects: 20 };
LIMITS.saveW = [30, 60];               // 每分鐘最多寫 30 次（前端預設 20 秒才傳一次）
LIMITS.saveR = [60, 60];
const SAVE_KEY_RE = /^aiOffice\.(game|world)\.[A-Za-z0-9_.-]{1,60}$/;
const SAVE_PROJ_RE = /^[A-Za-z0-9_-]{1,40}$/;
/** 存檔格式遷移：任何版本 → 目前版本（SAVE.schema）。回 { keys } 或 null（格式認不得）。
 *  schema 1（2026-11 以前前端草稿用的格式）：{ layout: <擺設物件>, game: { <名稱>: <值> } }
 *  schema 2（現行）：{ keys: { 'aiOffice.world.layout.v1': '<JSON 字串>', 'aiOffice.game.<名稱>': '<字串>' } } */
export function migrateSave(schema, data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  let d = data, v = Number.isInteger(schema) ? schema : 1;
  if (v > SAVE.schema) return null;                       // 比伺服器新的格式：不認（避免舊伺服器把新資料砍壞）
  if (v === 1) {
    const keys = {};
    if (d.layout && typeof d.layout === 'object') keys['aiOffice.world.layout.v1'] = JSON.stringify(d.layout);
    if (d.game && typeof d.game === 'object') for (const [k, x] of Object.entries(d.game)) keys['aiOffice.game.' + k] = typeof x === 'string' ? x : JSON.stringify(x);
    d = { keys }; v = 2;
  }
  // 之後新增 schema 3 就在這裡接一段 if (v === 2) { …; v = 3; }
  const out = {}; let n = 0, size = 0;
  for (const [k, x] of Object.entries(d.keys || {})) {
    if (!SAVE_KEY_RE.test(k) || typeof x !== 'string' || x.length > SAVE.maxVal) continue;
    if (++n > SAVE.maxKeys) break;
    size += k.length + x.length; out[k] = x;
  }
  return { keys: out, size };
}
const tpeDay = (ms) => new Date(ms + 8 * 3600e3).toISOString().slice(0, 10);
// ───────── 用量（2026-11-16，研究報告第 10 項）─────────
// 外掛在 Stop／SessionEnd 送 usage_main（主對話累計 Token）與 usage_subagents（各子 Agent 累計）；收件端記每個工作階段上次的累計值，差額記進「台北日期」那天。
// 取不到 Token 的工作階段（外掛舊版、紀錄檔讀不到）：每次工具呼叫（PreToolUse）以 USAGE.estPerTool 推估，標「估算」；同一天同一工作階段一旦有真的數字就只算真的。
export const USAGE = { estPerTool: 3000, keepDays: 35 };

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
    this.state = state; this.env = env || {}; this.sql = state.storage.sql; this.ready = false; this.sess = new Map(); this.nIns = 0; this.waiters = new Set();
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
      // 網站指令收件匣：rev 每次狀態改變就換新的（全辦公室遞增），網站用 since=rev 增量讀
      'CREATE TABLE IF NOT EXISTS inbox (mid TEXT PRIMARY KEY, office TEXT NOT NULL, created INTEGER NOT NULL, updated INTEGER NOT NULL, rev INTEGER NOT NULL, to_agent TEXT NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL, sid TEXT, claimed_at INTEGER, done_at INTEGER, reply TEXT, ph TEXT)',
      // 登入帳號底下的辦公室清單：owner＝帳號代號（信箱雜湊，不存信箱）；phs＝綁定的專案雜湊（JSON 陣列）；cap＝每間最多幾位 Agent（站長為空＝不限）
      'CREATE TABLE IF NOT EXISTS offices (oid TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL, phs TEXT NOT NULL DEFAULT \'[]\', cap INTEGER, created INTEGER NOT NULL, updated INTEGER NOT NULL)',
      'CREATE INDEX IF NOT EXISTS of_owner ON offices (owner, created)',
      'CREATE INDEX IF NOT EXISTS ib_office ON inbox (office, status, created)',
      // 專案名冊（檔案來源）：每個專案 .claude/agents/ 的檔名；事件裡出現過的子 Agent 類型直接從 agents 表算，不重複存
      'CREATE TABLE IF NOT EXISTS rosters (office TEXT NOT NULL, ph TEXT NOT NULL, name TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY (office, ph, name))',
      // 最近一次收件匣取指令（/v1/inbox/pull）的時間：網站用它判斷「你的 Claude 在線上（待命中）」
      'CREATE TABLE IF NOT EXISTS pulse (office TEXT PRIMARY KEY, at INTEGER NOT NULL)',
      'CREATE TABLE IF NOT EXISTS inbox_rev (office TEXT PRIMARY KEY, rev INTEGER NOT NULL)',
      // 雲端存檔：一個專案一份（proj＝專案雜湊或 main）
      'CREATE TABLE IF NOT EXISTS saves (office TEXT NOT NULL, proj TEXT NOT NULL, ver INTEGER NOT NULL, schema INTEGER NOT NULL, data TEXT NOT NULL, size INTEGER NOT NULL, at INTEGER NOT NULL, rcv INTEGER NOT NULL, PRIMARY KEY (office, proj))',
      // 每日用量：real＝真的 Token（差額累加）、est＝推估、tools＝工具呼叫次數；ucum＝每個工作階段上次的累計值
      'CREATE TABLE IF NOT EXISTS usage_day (office TEXT NOT NULL, ph TEXT NOT NULL, day TEXT NOT NULL, sid TEXT NOT NULL, real INTEGER NOT NULL DEFAULT 0, est INTEGER NOT NULL DEFAULT 0, tools INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (office, ph, day, sid))',
      'CREATE TABLE IF NOT EXISTS ucum (office TEXT NOT NULL, sid TEXT NOT NULL, tot INTEGER NOT NULL, PRIMARY KEY (office, sid))',
    ];
    for (const s of T) this.sql.exec(s);
    // 舊資料庫的收件匣沒有 ph 欄：補上（新的指令可以指定專案；舊的指令 ph 為空＝任何專案都可以取）
    if (!this.q('PRAGMA table_info(inbox)').some((c) => c.name === 'ph')) this.sql.exec('ALTER TABLE inbox ADD COLUMN ph TEXT');
    try { this.sql.exec('ALTER TABLE sessions ADD COLUMN tname TEXT'); } catch { /* 已經有這欄 */ }
    // 2026-11-16 第二批第 1 項：主工作階段（CEO）最近一次的工具類別與時間（只存類別，不存指令或檔名），網頁依它切換 CEO 的動作與頭上小圖示
    for (const c of ['tool TEXT', 'tool_at INTEGER']) { try { this.sql.exec('ALTER TABLE sessions ADD COLUMN ' + c); } catch { /* 已經有這欄 */ } }
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
  /** 網站登入權杖 → { valid, admin, key }。用服務綁定（ACCOUNT → tw-account）問 /v1/me，結果快取（有效 10 分鐘、無效 1 分鐘）。
   *  key＝信箱（小寫）的雜湊前 24 碼：辦公室清單用它當帳號代號，收件端不存信箱。 */
  async whoAmI(tok) {
    const none = { valid: false, admin: false, key: null };
    if (typeof tok !== 'string' || tok.length < 20 || tok.length > 4000) return none;
    const k = await sha256(tok), c = this.sess.get(k), now = this.now();
    if (c && c.exp > now) return c.w;
    let w = none;
    try {
      const init = { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: this.origins()[0] }, body: JSON.stringify({ t: tok }) };
      let r = null;
      if (this.env.ACCOUNT && this.env.ACCOUNT.fetch) r = await this.env.ACCOUNT.fetch('https://account.internal/v1/me', init);
      else if (this.env.ACCOUNT_API_URL) r = await fetch(String(this.env.ACCOUNT_API_URL).replace(/\/+$/, '') + '/v1/me', init);
      if (r && r.ok) {
        const j = await r.json(), u = j && j.user;
        if (u && typeof u.email === 'string' && u.email) w = { valid: true, admin: !!u.admin, key: 'u_' + (await sha256(u.email.toLowerCase())).slice(0, 24) };
        else if (u && u.admin) w = { valid: true, admin: true, key: 'u_admin' };
      }
    } catch (e) { w = none; }
    if (this.sess.size > 200) this.sess.clear();
    this.sess.set(k, { w, exp: now + (w.valid ? 600e3 : 60e3) });
    return w;
  }
  async isOwner(tok) { const w = await this.whoAmI(tok); return w.valid && w.admin; }
  /** 網站端寫收件匣：只認擁有者的網站登入（X-AIO-Session），而且要從白名單網站來。接入碼不算。 */
  async ownerOffice(req) {
    if (!this.originOk(req.headers.get('Origin'))) return 'origin';
    const s = req.headers.get('X-AIO-Session');
    if (!s) return null;
    return this.myOffice(await this.whoAmI(s));
  }
  /** 2026-11-16 開放一般會員：登入帳號 → 自己的資料辦公室代號。站長＝main；一般會員＝帳號代號（u_ 開頭，信箱雜湊），
   *  而且要先在網站建立過至少一間辦公室（offices 表有自己的列）才算，否則回 'no_office'。沒登入／權杖無效＝false。
   *  每個人只會解析到自己的代號，所以收件匣、狀態讀取、接入碼都天然隔開，別人的辦公室一律 403。 */
  myOffice(w) {
    if (!w || !w.valid) return false;
    if (w.admin) return OFFICE;
    if (!w.key || !/^u_[0-9a-f]{24}$/.test(w.key)) return false;
    return this.q('SELECT oid FROM offices WHERE owner = ? LIMIT 1', w.key)[0] ? w.key : 'no_office';
  }
  /** Claude 端：只認接入碼，而且不准從瀏覽器來（帶 Origin 一律拒絕）。 */
  async claudeOffice(req) {
    if (req.headers.get('Origin')) return 'browser';
    return this.codeOffice(req);
  }
  async readerOffice(req) {
    const c = await this.codeOffice(req);
    if (c) return c;
    const s = req.headers.get('X-AIO-Session');
    if (s) { const o = this.myOffice(await this.whoAmI(s)); if (o && o !== 'no_office') return o; }
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
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/projects$/.exec(p);
      if (req.method === 'GET' && m) return await this.projectList(req, m[1]);
      if (p === '/v1/offices' && (req.method === 'GET' || req.method === 'POST')) return await this.officeRoute(req, req.method === 'GET' ? 'list' : 'create', null);
      m = /^\/v1\/offices\/(o_[A-Za-z0-9_-]{6,30})(\/delete)?$/.exec(p);
      if (req.method === 'POST' && m) return await this.officeRoute(req, m[2] ? 'delete' : 'update', m[1]);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/wipe$/.exec(p);
      if (req.method === 'POST' && m) return await this.wipe(req, m[1]);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/inbox$/.exec(p);
      if (m && req.method === 'POST') return await this.inboxSend(req, m[1]);
      if (m && req.method === 'GET') return await this.inboxList(req, m[1], url);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/inbox\/(m_[A-Za-z0-9_-]{8,40})\/cancel$/.exec(p);
      if (m && req.method === 'POST') return await this.inboxCancel(req, m[1], m[2]);
      if (req.method === 'POST' && p === '/v1/inbox/pull') return await this.inboxPull(req);
      if (req.method === 'POST' && p === '/v1/inbox/ack') return await this.inboxAck(req);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/save\/([A-Za-z0-9_-]{1,40})$/.exec(p);
      if (m && req.method === 'GET') return await this.saveGet(req, m[1], m[2]);
      if (m && req.method === 'POST') return await this.savePut(req, m[1], m[2]);
      m = /^\/v1\/office\/([A-Za-z0-9_-]{1,40})\/usage$/.exec(p);
      if (m && req.method === 'GET') return await this.usageGet(req, m[1], url);
      return this.json(req, { error: 'not_found' }, 404);
    } catch (e) {
      return this.json(req, { error: 'server' }, 500);
    }
  }

  async body(req, max = MAX_BODY) {
    const len = +(req.headers.get('Content-Length') || 0);
    if (len > max) return { err: 'too_large' };
    const raw = await req.text();
    if (raw.length > max) return { err: 'too_large' };
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
    if (ph && e.event === 'SessionStart' && Array.isArray(e.agent_files)) {
      // 名冊以最新一次 SessionStart 為準：檔案刪了就從名冊拿掉（舊版外掛沒有 agent_files＝不動）
      this.sql.exec('DELETE FROM rosters WHERE office = ? AND ph = ?', office, ph);
      for (const n of e.agent_files) this.sql.exec('INSERT INTO rosters (office, ph, name, at) VALUES (?, ?, ?, ?) ON CONFLICT(office, ph, name) DO UPDATE SET at = excluded.at', office, ph, n, rcv);
    }
    if (!sid) return;
    // 工作階段：第一次看到就建立（就算沒收到 SessionStart，例如外掛是中途才裝的）
    this.sql.exec(`INSERT INTO sessions (office, sid, ph, pname, tname, cloud, started, last, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'idle')
      ON CONFLICT(office, sid) DO UPDATE SET last = excluded.last, ph = COALESCE(excluded.ph, ph), pname = COALESCE(excluded.pname, pname), tname = COALESCE(excluded.tname, tname), cloud = COALESCE(excluded.cloud, cloud)`,
      office, sid, ph, e.project_name || null, e.task_name || null, e.cloud == null ? null : e.cloud ? 1 : 0, rcv, rcv);
    const S = (set, ...a) => this.sql.exec(`UPDATE sessions SET ${set} WHERE office = ? AND sid = ?`, ...a, office, sid);
    const cat = e.tool_category;
    switch (e.event) {
      case 'SessionStart': S("started = ?, ended = NULL, state = 'idle', flag = NULL", rcv); break;
      case 'SessionEnd': S("ended = ?, state = 'ended', flag = NULL, tool = NULL", rcv); break;
      case 'UserPromptSubmit': if (!e.prompt_is_system) S("state = 'working', flag = NULL, prompts = prompts + 1, ended = NULL"); break;
      case 'Stop': S("state = 'idle', flag = NULL, tool = NULL, turns = turns + 1, summary = ?, tokens = COALESCE(?, tokens)", e.summary || null, e.usage_main ?? null); break;
      case 'StopFailure': S("state = 'error', flag = NULL"); break;
      case 'PermissionRequest': S("flag = 'permission', perm = ?", e.perm_category || 'other'); break;
      case 'Notification':
        if (e.notification_type === 'permission_prompt') S("flag = 'permission', perm = COALESCE(perm, 'other')");
        else if (e.notification_type === 'elicitation_dialog') S("flag = 'question'");
        break;
      case 'PreToolUse':
        if (cat === 'ask') S("flag = 'question', state = 'working'");
        else S("flag = NULL, state = 'working', ended = NULL");
        if (!e.agent_id && cat && cat !== 'ask') S('tool = ?, tool_at = ?', cat, rcv);   // 子 Agent 的工具記在 agents 表；這裡只記主工作階段自己的
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
    this.countUsage(office, sid, e, rcv);
  }

  /** 每日用量：真的 Token 記差額；工具呼叫記次數與推估。工作階段的專案雜湊取 sessions 表（事件本身沒帶就用表上的）。 */
  countUsage(office, sid, e, rcv) {
    const isTool = e.event === 'PreToolUse';
    const hasTok = (e.event === 'Stop' || e.event === 'SessionEnd') && (e.usage_main != null || e.usage_subagents);
    if (!isTool && !hasTok) return;
    const ph = e.project_hash || (this.q('SELECT ph FROM sessions WHERE office = ? AND sid = ?', office, sid)[0] || {}).ph || '-';
    const day = tpeDay(rcv);
    this.sql.exec('INSERT INTO usage_day (office, ph, day, sid) VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING', office, ph, day, sid);
    const U = (set, ...a) => this.sql.exec(`UPDATE usage_day SET ${set} WHERE office = ? AND ph = ? AND day = ? AND sid = ?`, ...a, office, ph, day, sid);
    if (isTool) { U('tools = tools + 1, est = est + ?', USAGE.estPerTool); return; }
    let tot = e.usage_main || 0;
    if (e.usage_subagents) for (const t of Object.values(e.usage_subagents)) tot += t;
    const prev = (this.q('SELECT tot FROM ucum WHERE office = ? AND sid = ?', office, sid)[0] || {}).tot || 0;
    const d = tot - prev;
    if (d > 0) U('real = real + ?', d);
    if (tot > prev) this.sql.exec('INSERT INTO ucum (office, sid, tot) VALUES (?, ?, ?) ON CONFLICT(office, sid) DO UPDATE SET tot = excluded.tot', office, sid, tot);
  }

  prune(office) {
    const cut = this.q('SELECT seq FROM events WHERE office = ? ORDER BY seq DESC LIMIT 1 OFFSET ?', office, KEEP_EVENTS)[0];
    if (cut) this.sql.exec('DELETE FROM events WHERE office = ? AND seq <= ?', office, cut.seq);
    const old = this.now() - KEEP_DAYS * 86400e3;
    this.sql.exec('DELETE FROM agents WHERE office = ? AND COALESCE(ended, last) < ?', office, old);
    this.sql.exec('DELETE FROM sessions WHERE office = ? AND last < ?', office, old);
    this.sql.exec('DELETE FROM rosters WHERE office = ? AND at < ?', office, old);
    this.sql.exec('DELETE FROM dispatch WHERE office = ? AND at < ?', office, this.now() - 3600e3);
    this.sql.exec('DELETE FROM rl WHERE win < ?', Math.floor(this.now() / 1000 / 3600) - 2);
    this.sql.exec('DELETE FROM usage_day WHERE office = ? AND day < ?', office, tpeDay(this.now() - USAGE.keepDays * 86400e3));
    this.sql.exec('DELETE FROM ucum WHERE office = ? AND sid NOT IN (SELECT sid FROM sessions WHERE office = ?)', office, office);
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
    // 單一專案：?project=<專案雜湊>。事件、工作階段、子 Agent、統計都只回這個專案的（沒有專案雜湊的事件，例如指令狀態更新，每個專案都看得到）。
    // 同名專案（舊路徑雜湊＋新儲存庫雜湊）算同一個：pj 展開成這個專案的所有別名雜湊，回傳時再把別名換回 pj，前端不必知道有別名。
    const pj = url.searchParams.get('project');
    if (pj && !PH_RE.test(pj)) return this.json(req, { error: 'bad_project' }, 400);
    const pg = this.projectGroups(office, now, pj), al = pj ? this.aliasesOf(pg, pj) : null, PA = al || [];
    const IN = al ? '(' + al.map(() => '?').join(',') + ')' : '', PE = al ? ' AND (ph IN ' + IN + ' OR ph IS NULL)' : '', PS = al ? ' AND ph IN ' + IN : '';
    const cn = (h) => (h && pg.canon.has(h) ? pg.canon.get(h) : h);
    const evRows = since > 0
      ? this.q('SELECT seq, ts, rcv, data FROM events WHERE office = ? AND seq > ?' + PE + ' ORDER BY seq LIMIT 300', office, since, ...PA)
      : this.q('SELECT seq, ts, rcv, data FROM events WHERE office = ?' + PE + ' ORDER BY seq DESC LIMIT 60', office, ...PA).reverse();
    const events = evRows.map((r) => { const d = JSON.parse(r.data); delete d.usage_subagents; delete d.rate_limits; delete d.agent_files; if (d.project_hash) d.project_hash = cn(d.project_hash); return { seq: r.seq, ts: r.ts, rcv: r.rcv, ...d }; });
    const top = this.q('SELECT MAX(seq) AS s FROM events WHERE office = ?', office)[0] || {};
    const cnt = this.q('SELECT MAX(rcv) AS t, COUNT(*) AS n FROM events WHERE office = ?' + PE, office, ...PA)[0] || {};
    const projects = pg.list;
    const sessions = this.q('SELECT sid AS id, ph AS project_hash, pname AS project_name, tname AS task_name, cloud, started, last, ended, state, flag, perm, prompts, turns, summary, tokens, tool, tool_at FROM sessions WHERE office = ? AND last > ?' + PS + ' ORDER BY last DESC LIMIT 40', office, now - 7 * 86400e3, ...PA)
      .map((s) => ({ ...s, project_hash: cn(s.project_hash), cloud: s.cloud == null ? null : !!s.cloud }));
    let agents = this.q('SELECT aid AS agent_id, sid AS session_id, ph AS project_hash, type AS agent_type, descr AS description, started, last, ended, status, tool, tool_at, summary, tokens, dur AS duration_ms FROM agents WHERE office = ? AND (ended IS NULL OR ended > ?)' + PS + ' ORDER BY COALESCE(ended, last) DESC LIMIT 200', office, now - 86400e3, ...PA)
      .map((a) => ({ ...a, project_hash: cn(a.project_hash) }))
      .map((a) => (a.status === 'running' && now - (a.last || 0) > STALE_MS ? { ...a, status: 'unknown' } : a));
    // 各子 Agent 類型：近 7 天的真實統計（前端績效總表用；樣本不足由前端判斷並標示）
    const since7 = now - 7 * 86400e3;
    const types = this.q(`SELECT type AS agent_type, COUNT(*) AS dispatched,
        SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
        SUM(CASE WHEN status = 'running' AND ? - last <= ? THEN 1 ELSE 0 END) AS running,
        AVG(CASE WHEN status IN ('done', 'failed') THEN dur END) AS avg_ms, SUM(CASE WHEN status IN ('done', 'failed') AND dur IS NOT NULL THEN 1 ELSE 0 END) AS n_dur,
        SUM(tokens) AS tokens, SUM(CASE WHEN tokens IS NOT NULL THEN 1 ELSE 0 END) AS n_tokens, MAX(COALESCE(ended, last)) AS last
      FROM agents WHERE office = ? AND COALESCE(started, last) > ?${PS} GROUP BY type ORDER BY dispatched DESC LIMIT 100`, now, STALE_MS, office, since7, ...PA)
      .map((t) => ({ ...t, avg_ms: t.avg_ms == null ? null : Math.round(t.avg_ms) }));
    const ceo = this.q('SELECT COUNT(*) AS sessions, SUM(prompts) AS prompts, SUM(turns) AS turns, SUM(tokens) AS tokens FROM sessions WHERE office = ? AND last > ?' + PS, office, since7, ...PA)[0] || {};
    const qr = this.q('SELECT data, at FROM quota WHERE office = ?', office)[0];
    const ib = this.q("SELECT SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) AS queued, SUM(CASE WHEN status IN ('claimed', 'running') THEN 1 ELSE 0 END) AS active FROM inbox WHERE office = ?", office)[0] || {};
    // 辦公室檢視（?view=<辦公室代號>）：非站長的辦公室每間最多 N 位 Agent，由這裡擋（站長的 cap 為空＝不限）
    let capped = 0, rcap = null;
    const view = url.searchParams.get('view');
    if (view && /^o_[A-Za-z0-9_-]{6,30}$/.test(view)) {
      const vo = this.q('SELECT cap FROM offices WHERE oid = ?', view)[0];
      if (vo && vo.cap) { const c = capAgents(agents, vo.cap); agents = c.agents; capped = c.capped; rcap = vo.cap; }
    }
    const roster = this.rosterOf(office, al, rcap);
    return this.json(req, {
      office, now, seq: top.s || 0, since, initial: since === 0, total_events: cnt.n || 0, last_event_at: cnt.t || null, project: pj || null, agents_capped: capped,
      projects, sessions, agents, types, ceo, roster, quota: qr ? { rate_limits: JSON.parse(qr.data), at: qr.at } : null, events,
      inbox: { queued: ib.queued || 0, active: ib.active || 0, rev: this.inboxRev(office), last_pull: this.lastPull(office) },
    });
  }

  /** 專案分組（同名合併）。state 與 /projects 共用。
   *  list＝入口要列的專案（名稱、最後活動、進行中工作階段數；同名的別名雜湊合併，aliases 列出全部雜湊）；
   *  all＝內部用（含 hashes）；canon＝任何雜湊 → 這一組的代表雜湊。want（請求指定的雜湊）若屬於某組，那一組就以 want 當代表，舊連結因此照樣對得上。 */
  projectGroups(office, now, want) {
    const rows = this.q(`SELECT p.ph AS hash, p.name, p.first, p.last, p.n AS events,
        (SELECT COUNT(*) FROM sessions s WHERE s.office = p.office AND s.ph = p.ph AND s.ended IS NULL AND s.last > ?) AS active
      FROM projects p WHERE p.office = ? ORDER BY p.last DESC LIMIT 200`, now - ACTIVE_MS, office);
    const g = new Map();
    for (const r of rows) {                                   // rows 由新到舊：每組第一筆就是最近活動的那個雜湊
      const k = projectKey(r.name, r.hash);
      let x = g.get(k);
      if (!x) { x = { hash: r.hash, name: r.name, first: r.first, last: r.last, events: 0, active: 0, hashes: [] }; g.set(k, x); }
      x.events += r.events; x.active += r.active; x.hashes.push(r.hash);
      if (r.first != null && (x.first == null || r.first < x.first)) x.first = r.first;
      if (!x.name && r.name) x.name = r.name;
    }
    const all = [...g.values()], canon = new Map();
    for (const x of all) { if (want && x.hashes.includes(want)) x.hash = want; for (const h of x.hashes) canon.set(h, x.hash); }
    all.sort((a, b) => (b.last || 0) - (a.last || 0));
    return { all, canon, list: all.slice(0, 30).map(({ hashes, ...r }) => (hashes.length > 1 ? { ...r, aliases: hashes } : r)) };
  }
  aliasesOf(pg, ph) { const x = pg.all.find((q) => q.hashes.includes(ph)); return x ? x.hashes : [ph]; }
  /** 專案名冊：.claude/agents 檔名 ∪ 事件裡出現過的子 Agent 類型。hashes 為空＝全部專案。cap＝非站長辦公室的 Agent 上限（留最近有動靜的） */
  rosterOf(office, hashes, cap) {
    const IN = hashes ? ' AND ph IN (' + hashes.map(() => '?').join(',') + ')' : '', A = hashes || [], m = new Map();
    for (const r of this.q('SELECT name, MAX(at) AS at FROM rosters WHERE office = ?' + IN + ' GROUP BY name', office, ...A)) m.set(r.name, { type: r.name, file: true, seen: false, last: r.at || 0 });
    for (const r of this.q('SELECT type, MAX(COALESCE(ended, last)) AS at FROM agents WHERE office = ? AND type IS NOT NULL' + IN + ' GROUP BY type', office, ...A)) {
      const x = m.get(r.type);
      if (x) { x.seen = true; x.last = Math.max(x.last, r.at || 0); } else m.set(r.type, { type: r.type, file: false, seen: true, last: r.at || 0 });
    }
    let list = [...m.values()].sort((a, b) => b.last - a.last || (a.type < b.type ? -1 : 1)).slice(0, ROSTER.max);
    if (cap && cap > 0) list = list.slice(0, cap);
    return list;
  }
  lastPull(office) { const r = this.q('SELECT at FROM pulse WHERE office = ?', office)[0]; return r ? r.at : null; }
  // ───────── GET /v1/office/<id>/projects：只要專案清單（入口頁用，比 state 輕很多） ─────────
  async projectList(req, office) {
    const who = await this.readerOffice(req);
    if (!who) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    if (who !== office) return this.json(req, { error: 'forbidden' }, 403);
    if (!this.hit('rd:' + office + ':' + this.ip(req), LIMITS.read)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const now = this.now();
    return this.json(req, { office, now, projects: this.projectGroups(office, now, null).list });
  }

  // ───────── 辦公室清單（登入帳號底下）：/v1/offices ─────────
  officeView(r) { let phs = []; try { phs = JSON.parse(r.phs); } catch (e) { phs = []; } return { id: r.oid, name: r.name, projects: phs, agent_cap: r.cap || null, created: r.created, updated: r.updated }; }
  cleanPhs(v) {
    if (v == null) return [];
    if (!Array.isArray(v) || v.length > OFFICES.maxProjects) return null;
    const out = []; for (const h of v) { if (typeof h !== 'string' || !PH_RE.test(h)) return null; if (!out.includes(h)) out.push(h); }
    return out;
  }
  async officeRoute(req, act, oid) {
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    const w = await this.whoAmI(req.headers.get('X-AIO-Session'));
    if (!w.valid) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    if (!this.hit('ofc:' + w.key, LIMITS.offices)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const max = w.admin ? OFFICES.adminMax : OFFICES.memberMax, cap = w.admin ? null : OFFICES.memberAgents;
    const mine = () => this.q('SELECT * FROM offices WHERE owner = ? ORDER BY created, rowid', w.key);
    if (act === 'list') return this.json(req, { offices: mine().map((r) => this.officeView(r)), limits: { max, agents: cap }, admin: w.admin });
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, err === 'too_large' ? 413 : 400);
    const now = this.now();
    if (act === 'create') {
      const name = cleanOfficeName(b.name), phs = this.cleanPhs(b.projects);
      if (!name) return this.json(req, { error: 'bad_name', max: OFFICES.nameMax }, 400);
      if (!phs) return this.json(req, { error: 'bad_projects' }, 400);
      const cur = mine();
      if (cur.length >= max) return this.json(req, { error: 'office_limit', max }, 409);       // 非站長 3 間：由這裡擋，不是前端
      if (cur.some((r) => r.name === name)) return this.json(req, { error: 'name_taken' }, 409);
      const id = 'o_' + newCode().slice(4, 16).replace(/[^A-Za-z0-9]/g, 'x');
      this.sql.exec('INSERT INTO offices (oid, owner, name, phs, cap, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?)', id, w.key, name, JSON.stringify(phs), cap, now, now);
      return this.json(req, { ok: true, office: this.officeView(this.q('SELECT * FROM offices WHERE oid = ?', id)[0]), limits: { max, agents: cap } });
    }
    const row = this.q('SELECT * FROM offices WHERE oid = ? AND owner = ?', oid, w.key)[0];
    if (!row) return this.json(req, { error: 'not_found' }, 404);       // 別人的辦公室與不存在的一律回 404，不洩漏存在與否
    if (act === 'delete') { this.sql.exec('DELETE FROM offices WHERE oid = ?', oid); return this.json(req, { ok: true }); }
    let name = row.name, phs = row.phs;
    if (b.name !== undefined) {
      name = cleanOfficeName(b.name);
      if (!name) return this.json(req, { error: 'bad_name', max: OFFICES.nameMax }, 400);
      if (this.q('SELECT oid FROM offices WHERE owner = ? AND name = ? AND oid <> ?', w.key, name, oid)[0]) return this.json(req, { error: 'name_taken' }, 409);
    }
    if (b.projects !== undefined) { const l = this.cleanPhs(b.projects); if (!l) return this.json(req, { error: 'bad_projects' }, 400); phs = JSON.stringify(l); }
    this.sql.exec('UPDATE offices SET name = ?, phs = ?, updated = ? WHERE oid = ?', name, phs, now, oid);
    return this.json(req, { ok: true, office: this.officeView(this.q('SELECT * FROM offices WHERE oid = ?', oid)[0]) });
  }

  // ───────── POST /v1/claim：擁有者本人登入網站後領接入碼（只顯示這一次） ─────────
  async claim(req) {
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    if (!this.hit('claim:' + this.ip(req), LIMITS.claim)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '3600' });
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, 400);
    if (!this.env.ACCOUNT && !this.env.ACCOUNT_API_URL) return this.json(req, { error: 'no_account' }, 503);
    // 站長＝main；一般會員＝自己的資料辦公室（要先建立過辦公室）。接入碼只綁自己的代號，拿到也讀寫不到別人的。
    const OF = this.myOffice(await this.whoAmI(b.t));
    if (OF === 'no_office') return this.json(req, { error: 'no_office' }, 403);
    if (!OF) return this.json(req, { error: 'not_owner' }, 403);
    const cur = this.q("SELECT created FROM codes WHERE office = ? AND role = 'ingest' AND revoked = 0 ORDER BY created DESC LIMIT 1", OF)[0];
    if (cur && b.rotate !== true) return this.json(req, { ok: true, office: OF, exists: true, created: cur.created });
    const code = newCode(), now = this.now();
    this.sql.exec("UPDATE codes SET revoked = 1 WHERE office = ? AND role = 'ingest'", OF);
    this.sql.exec("INSERT INTO codes (hash, office, role, created) VALUES (?, ?, 'ingest', ?)", await sha256(code), OF, now);
    return this.json(req, { ok: true, office: OF, code, created: now, rotated: !!cur });
  }

  // ───────── POST /v1/office/<id>/wipe：擁有者刪除所有事件紀錄（接入碼保留） ─────────
  async wipe(req, office) {
    if (!this.originOk(req.headers.get('Origin'))) return this.json(req, { error: 'origin' }, 403);
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, 400);
    if (office !== OFFICE || !(await this.isOwner(b.t))) return this.json(req, { error: 'not_owner' }, 403);
    for (const t of ['events', 'projects', 'sessions', 'agents', 'dispatch', 'quota', 'inbox', 'rosters', 'pulse', 'usage_day', 'ucum']) this.sql.exec(`DELETE FROM ${t} WHERE office = ?`, office);
    return this.json(req, { ok: true });
  }

  // ═════════════════ 網站指令收件匣（docs/ai_office/chat_command_spec.md） ═════════════════
  inboxRev(office) { const r = this.q('SELECT rev FROM inbox_rev WHERE office = ?', office)[0]; return r ? r.rev : 0; }
  bumpRev(office) {
    const rev = this.inboxRev(office) + 1;
    this.sql.exec('INSERT INTO inbox_rev (office, rev) VALUES (?, ?) ON CONFLICT(office) DO UPDATE SET rev = excluded.rev', office, rev);
    return rev;
  }
  /** 狀態改變：更新收件匣，並寫一筆 InboxUpdate 事件（讓 /state 的事件串也看得到「指令狀態變了」，不含指令與回覆內文）。 */
  inboxSet(office, mid, set, ...a) {
    const rev = this.bumpRev(office), now = this.now();
    this.sql.exec(`UPDATE inbox SET ${set}, updated = ?, rev = ? WHERE office = ? AND mid = ?`, ...a, now, rev, office, mid);
    const r = this.q('SELECT status, to_agent, sid FROM inbox WHERE office = ? AND mid = ?', office, mid)[0];
    if (r) this.sql.exec('INSERT INTO events (office, ts, rcv, kind, sid, data) VALUES (?, ?, ?, ?, ?, ?)', office, now, now, 'InboxUpdate', r.sid || null,
      JSON.stringify({ event: 'InboxUpdate', message_id: mid, status: r.status, to: r.to_agent, session_id: r.sid || undefined }));
  }
  /** 排隊太久的過期、保留量修剪。每次讀寫收件匣前做一次（便宜：有索引）。 */
  inboxHousekeep(office) {
    const now = this.now();
    for (const r of this.q("SELECT mid FROM inbox WHERE office = ? AND status = 'queued' AND created < ? LIMIT 50", office, now - INBOX.expireMs)) this.inboxSet(office, r.mid, "status = 'expired'");
    const cut = this.q('SELECT created FROM inbox WHERE office = ? ORDER BY created DESC LIMIT 1 OFFSET ?', office, INBOX.keep)[0];
    if (cut) this.sql.exec("DELETE FROM inbox WHERE office = ? AND created <= ? AND status NOT IN ('queued', 'claimed', 'running')", office, cut.created);
  }
  viewMsg(r) {
    const now = this.now();
    let status = r.status;
    if (status === 'claimed' && now - r.updated > INBOX.claimedStaleMs) status = 'stale';
    if (status === 'running' && now - r.updated > INBOX.runningStaleMs) status = 'stale';
    return { id: r.mid, to: r.to_agent, text: r.text, status, created: r.created, updated: r.updated, claimed_at: r.claimed_at, done_at: r.done_at, session_id: r.sid, reply: r.reply, rev: r.rev, project: r.ph || null };
  }
  /** 雲端存檔仍只開給站長（跟開放前一樣）：一般會員一律當作沒有權限（401）。 */
  async adminGate(req, office) {
    const g = await this.ownerGate(req, office);
    if (g.deny) { if (g.deny.status === 403) { const e = (await g.deny.clone().json()).error; if (e === 'no_office') return this.json(req, { error: 'auth' }, 401); } return g.deny; }
    if (g.member) return this.json(req, { error: 'auth' }, 401);
    if (g.office !== office) return this.json(req, { error: 'forbidden' }, 403);
    return null;
  }
  /** 回傳 { deny } 或 { office }。網址的辦公室代號可以寫 me＝「我自己的」（前端一律用 me，不必知道自己的代號）。 */
  async ownerGate(req, office) {
    const who = await this.ownerOffice(req);
    if (who === 'origin') return { deny: this.json(req, { error: 'origin' }, 403) };
    if (!who) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return { deny: this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' }) };
      return { deny: this.json(req, { error: 'auth' }, 401) };
    }
    if (who === 'no_office') return { deny: this.json(req, { error: 'no_office' }, 403) };
    if (office !== 'me' && who !== office) return { deny: this.json(req, { error: 'forbidden' }, 403) };
    return { office: who, member: who !== OFFICE };
  }

  // ───────── POST /v1/office/<id>/inbox：擁有者從網站送一則指令 ─────────
  async inboxSend(req, office) {
    const g = await this.ownerGate(req, office); if (g.deny) return g.deny; office = g.office;
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, err === 'too_large' ? 413 : 400);
    const to = typeof b.to === 'string' && TO_RE.test(b.to) ? b.to : null;
    if (!to) return this.json(req, { error: 'bad_to' }, 400);
    if (typeof b.text !== 'string') return this.json(req, { error: 'bad_text' }, 400);
    const text = b.text.replace(/[\u0000-\u0009\u000b-\u001f\u007f]+/g, ' ').trim();
    if (b.project != null && !(typeof b.project === 'string' && PH_RE.test(b.project))) return this.json(req, { error: 'bad_project' }, 400);
    const ph = b.project || null;
    if (!text) return this.json(req, { error: 'empty' }, 400);
    if (text.length > INBOX.maxText) return this.json(req, { error: 'too_long', max: INBOX.maxText }, 413);
    this.inboxHousekeep(office);
    const pend = this.q("SELECT COUNT(*) AS n FROM inbox WHERE office = ? AND status = 'queued'", office)[0].n;
    if (pend >= INBOX.maxPending) return this.json(req, { error: 'queue_full', max: INBOX.maxPending }, 429);
    if (!this.hit('ibs:' + office, LIMITS.inboxSend)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '60' });
    if (g.member && !this.hit('ibm:' + office, LIMITS.inboxMember)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '60' });
    if (!this.hit('ibd:' + office, g.member ? LIMITS.inboxDayMember : LIMITS.inboxDay)) return this.json(req, { error: 'rate_day' }, 429, { 'Retry-After': '3600' });
    const mid = 'm_' + newCode().slice(4, 20), now = this.now(), rev = this.bumpRev(office);
    this.sql.exec("INSERT INTO inbox (mid, office, created, updated, rev, to_agent, text, status, ph) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)", mid, office, now, now, rev, to, text, ph);
    this.sql.exec('INSERT INTO events (office, ts, rcv, ph, kind, data) VALUES (?, ?, ?, ?, ?, ?)', office, now, now, ph, 'InboxUpdate', JSON.stringify({ event: 'InboxUpdate', message_id: mid, status: 'queued', to }));
    for (const w of this.waiters) { clearTimeout(w.t); w.res(); }    // 叫醒正在長輪詢的待命 Claude
    this.waiters.clear();
    return this.json(req, { ok: true, message: this.viewMsg(this.q('SELECT * FROM inbox WHERE mid = ?', mid)[0]) });
  }

  // ───────── GET /v1/office/<id>/inbox?since=<rev>：網站讀指令列表 ─────────
  async inboxList(req, office, url) {
    const g = await this.ownerGate(req, office); if (g.deny) return g.deny; office = g.office;
    if (!this.hit('ibr:' + office + ':' + this.ip(req), LIMITS.read)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    this.inboxHousekeep(office);
    const since = Math.max(0, parseInt(url.searchParams.get('since') || '0', 10) || 0);
    const pj = url.searchParams.get('project');
    if (pj && !PH_RE.test(pj)) return this.json(req, { error: 'bad_project' }, 400);
    const al = pj ? this.aliasesOf(this.projectGroups(office, this.now(), pj), pj) : null;
    const PE = al ? ' AND (ph IN (' + al.map(() => '?').join(',') + ') OR ph IS NULL)' : '', PA = al || [];
    const rows = since > 0
      ? this.q('SELECT * FROM inbox WHERE office = ? AND rev > ?' + PE + ' ORDER BY created, rowid LIMIT 100', office, since, ...PA)
      : this.q('SELECT * FROM inbox WHERE office = ?' + PE + ' ORDER BY created DESC, rowid DESC LIMIT 50', office, ...PA).reverse();
    // 「沒有回音」是依時間推算的，since 增量讀不會因為時間經過而回傳，所以另外附上目前所有進行中的指令
    const open = this.q("SELECT * FROM inbox WHERE office = ? AND status IN ('queued', 'claimed', 'running')" + PE + ' ORDER BY created, rowid LIMIT 50', office, ...PA);
    const live = this.q("SELECT last FROM sessions WHERE office = ? AND ended IS NULL ORDER BY last DESC LIMIT 1", office)[0];
    return this.json(req, {
      office, now: this.now(), rev: this.inboxRev(office), since, messages: rows.map((r) => this.viewMsg(r)), open: open.map((r) => this.viewMsg(r)),
      limits: { max_text: INBOX.maxText, max_pending: INBOX.maxPending }, session_last_seen: live ? live.last : null, last_pull: this.lastPull(office),
    });
  }

  // ───────── POST /v1/office/<id>/inbox/<mid>/cancel：撤回還在排隊的 ─────────
  async inboxCancel(req, office, mid) {
    const g = await this.ownerGate(req, office); if (g.deny) return g.deny; office = g.office;
    const r = this.q('SELECT status FROM inbox WHERE office = ? AND mid = ?', office, mid)[0];
    if (!r) return this.json(req, { error: 'not_found' }, 404);
    if (r.status !== 'queued') return this.json(req, { error: 'not_queued', status: r.status }, 409);
    this.inboxSet(office, mid, "status = 'canceled'");
    return this.json(req, { ok: true });
  }

  // ───────── POST /v1/inbox/pull：Claude 端取走指令（可長輪詢） ─────────
  async inboxPull(req) {
    const office = await this.claudeOffice(req);
    if (office === 'browser') return this.json(req, { error: 'browser_not_allowed' }, 403);
    if (!office) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, 400);
    if (!this.hit('ibp:' + office, LIMITS.inboxPull)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const sid = id(b.session_id);
    // 只取「自己這個專案」的指令（沒指定專案的指令任何專案都可以取）；Claude 端沒帶專案雜湊（舊外掛）＝只拿沒指定專案的
    const myph = typeof b.project_hash === 'string' && PH_RE.test(b.project_hash) ? b.project_hash : null;
    // 同名專案的別名雜湊（舊路徑雜湊、新儲存庫雜湊）都算「我這個專案」：網站指令帶哪個雜湊都取得到
    const mine = myph ? this.aliasesOf(this.projectGroups(office, this.now(), myph), myph) : [];
    this.sql.exec('INSERT INTO pulse (office, at) VALUES (?, ?) ON CONFLICT(office) DO UPDATE SET at = excluded.at', office, this.now());     // 記下「Claude 剛來取過指令」：網站拿來顯示在線上（待命中）
    const max = Math.min(INBOX.maxPull, Math.max(1, Math.round(+b.max || 1)));
    const waitMs = Math.min(INBOX.maxWaitS, Math.max(0, +b.wait || 0)) * 1000;
    const deadline = Date.now() + waitMs;                       // 真實時間（等待用），跟 this.now()（紀錄用）分開
    for (;;) {
      this.inboxHousekeep(office);
      // 同步取＋標記，中間沒有 await：同一個 Durable Object 裡不會有兩支工作階段搶到同一則
      const rows = this.q("SELECT * FROM inbox WHERE office = ? AND status = 'queued' AND (ph IS NULL" + (mine.length ? ' OR ph IN (' + mine.map(() => '?').join(',') + ')' : '') + ') ORDER BY created, rowid LIMIT ?', office, ...mine, max);
      if (rows.length) {
        const now = this.now();
        for (const r of rows) this.inboxSet(office, r.mid, "status = 'claimed', sid = ?, claimed_at = ?", sid, now);
        const out = this.q(`SELECT * FROM inbox WHERE office = ? AND mid IN (${rows.map(() => '?').join(',')}) ORDER BY created, rowid`, office, ...rows.map((r) => r.mid));
        return this.json(req, { ok: true, source: 'website', messages: out.map((r) => ({ id: r.mid, to: r.to_agent, text: r.text, created: r.created, project: r.ph || null })) });
      }
      const left = deadline - Date.now();
      if (left <= 0) return this.json(req, { ok: true, source: 'website', messages: [] });
      await sleepOrWake(this, left);
    }
  }

  // ───────── POST /v1/inbox/ack：Claude 端回報狀態與回覆 ─────────
  async inboxAck(req) {
    const office = await this.claudeOffice(req);
    if (office === 'browser') return this.json(req, { error: 'browser_not_allowed' }, 403);
    if (!office) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    const { b, err } = await this.body(req);
    if (err) return this.json(req, { error: err }, err === 'too_large' ? 413 : 400);
    if (!this.hit('iba:' + office, LIMITS.inboxAck)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const mid = typeof b.id === 'string' && /^m_[A-Za-z0-9_-]{8,40}$/.test(b.id) ? b.id : null;
    if (!mid || !ACK_STATUS.has(b.status)) return this.json(req, { error: 'bad_request' }, 400);
    const r = this.q('SELECT status FROM inbox WHERE office = ? AND mid = ?', office, mid)[0];
    if (!r) return this.json(req, { error: 'not_found' }, 404);
    if (!['claimed', 'running'].includes(r.status)) return this.json(req, { error: 'not_active', status: r.status }, 409);
    const reply = b.reply == null ? null : maskSecrets(b.reply, INBOX.maxReply);
    const sid = id(b.session_id);
    if (b.status === 'running') this.inboxSet(office, mid, "status = 'running', sid = COALESCE(?, sid), reply = COALESCE(?, reply)", sid, reply);
    else this.inboxSet(office, mid, 'status = ?, sid = COALESCE(?, sid), reply = COALESCE(?, reply), done_at = ?', b.status, sid, reply, this.now());
    return this.json(req, { ok: true, status: b.status });
  }

  // ═════════════════ 雲端存檔 ═════════════════
  viewSave(r) {
    let data = null; try { data = JSON.parse(r.data); } catch (e) { data = null; }
    const m = migrateSave(r.schema, data);              // 存的是舊格式：讀出來時就升到現行格式
    return { version: r.ver, schema: SAVE.schema, at: r.at, saved_at: r.rcv, size: r.size, data: m ? { keys: m.keys } : { keys: {} } };
  }
  // GET /v1/office/<id>/save/<專案>
  async saveGet(req, office, proj) {
    const deny = await this.adminGate(req, office); if (deny) return deny;
    if (!SAVE_PROJ_RE.test(proj)) return this.json(req, { error: 'bad_project' }, 400);
    if (!this.hit('svr:' + office, LIMITS.saveR)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const r = this.q('SELECT * FROM saves WHERE office = ? AND proj = ?', office, proj)[0];
    return this.json(req, { ok: true, schema: SAVE.schema, save: r ? this.viewSave(r) : null });
  }
  // POST /v1/office/<id>/save/<專案>  { schema, base, at, data }
  async savePut(req, office, proj) {
    const deny = await this.adminGate(req, office); if (deny) return deny;
    if (!SAVE_PROJ_RE.test(proj)) return this.json(req, { error: 'bad_project' }, 400);
    const { b, err } = await this.body(req, SAVE.maxBody);
    if (err) return this.json(req, { error: err, max: SAVE.maxData }, err === 'too_large' ? 413 : 400);
    if (!this.hit('svw:' + office, LIMITS.saveW)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    if (b.schema != null && !Number.isInteger(b.schema)) return this.json(req, { error: 'bad_schema' }, 400);
    if ((b.schema || 1) > SAVE.schema) return this.json(req, { error: 'schema_too_new', schema: SAVE.schema }, 409);
    const m = migrateSave(b.schema, b.data);
    if (!m) return this.json(req, { error: 'bad_data' }, 400);
    if (m.size > SAVE.maxData) return this.json(req, { error: 'too_large', max: SAVE.maxData }, 413);
    const now = this.now();
    const at = int(b.at, 1e14) != null ? Math.min(int(b.at, 1e14), now + 60e3) : now;     // 前端本機時間：最多容忍快 1 分鐘
    const base = int(b.base);
    const cur = this.q('SELECT * FROM saves WHERE office = ? AND proj = ?', office, proj)[0];
    let conflict = null;
    if (cur && base !== cur.ver) {
      if (at <= cur.at) return this.json(req, { error: 'conflict', save: this.viewSave(cur) }, 409);
      conflict = 'overwrote';                              // 版本對不上，但這份比較新：最後寫入的贏
    }
    if (!cur && this.q('SELECT COUNT(*) AS n FROM saves WHERE office = ?', office)[0].n >= SAVE.maxProjects) return this.json(req, { error: 'too_many_projects', max: SAVE.maxProjects }, 429);
    const ver = cur ? cur.ver + 1 : 1;
    this.sql.exec('INSERT INTO saves (office, proj, ver, schema, data, size, at, rcv) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(office, proj) DO UPDATE SET ver = excluded.ver, schema = excluded.schema, data = excluded.data, size = excluded.size, at = excluded.at, rcv = excluded.rcv',
      office, proj, ver, SAVE.schema, JSON.stringify({ keys: m.keys }), m.size, at, now);
    return this.json(req, { ok: true, version: ver, at, saved_at: now, conflict, migrated: (b.schema || 1) !== SAVE.schema });
  }

  // ═════════════════ 每日用量 GET /v1/office/<id>/usage?project=<雜湊>&days=7 ═════════════════
  async usageGet(req, office, url) {
    const who = await this.readerOffice(req);
    if (!who) {
      if (!this.hit('bad:' + this.ip(req), LIMITS.badAuth)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '600' });
      return this.json(req, { error: 'auth' }, 401);
    }
    if (who !== office) return this.json(req, { error: 'forbidden' }, 403);
    if (!this.hit('rd:' + office + ':' + this.ip(req), LIMITS.read)) return this.json(req, { error: 'rate' }, 429, { 'Retry-After': '30' });
    const pj = url.searchParams.get('project');
    if (pj && !PH_RE.test(pj)) return this.json(req, { error: 'bad_project' }, 400);
    const days = Math.max(1, Math.min(31, +url.searchParams.get('days') || 7));
    const now = this.now(), today = tpeDay(now), from = tpeDay(now - (days - 1) * 86400e3);
    const al = pj ? this.aliasesOf(this.projectGroups(office, now, pj), pj) : null;
    const rows = this.q('SELECT day, real, est, tools FROM usage_day WHERE office = ? AND day >= ?' + (al ? ' AND ph IN (' + al.map(() => '?').join(',') + ')' : ''), office, from, ...(al || []));
    const by = new Map();
    for (const r of rows) {
      const d = by.get(r.day) || { day: r.day, tokens: 0, real: 0, estimate: 0, tools: 0, estimated: false };
      if (r.real > 0) d.real += r.real; else if (r.est > 0) { d.estimate += r.est; d.estimated = true; }   // 同一工作階段有真的數字就不算推估
      d.tools += r.tools; d.tokens = d.real + d.estimate; by.set(r.day, d);
    }
    const list = [...by.values()].sort((x, y) => (x.day < y.day ? -1 : 1));
    const t = by.get(today) || { day: today, tokens: 0, real: 0, estimate: 0, tools: 0, estimated: false };
    return this.json(req, { ok: true, today, now, est_per_tool: USAGE.estPerTool, today_usage: t, days: list });
  }

  /** 測試與本機開發用：直接發一組接入碼（不經過網站登入）。正式環境沒有任何路由會呼叫它。 */
  async devIssue(office = OFFICE) {
    this.init();
    const code = newCode();
    this.sql.exec("INSERT INTO codes (hash, office, role, created) VALUES (?, ?, 'ingest', ?)", await sha256(code), office, this.now());
    return code;
  }
}
