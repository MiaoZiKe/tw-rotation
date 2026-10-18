/* ============================================================================ 精選文章點閱次數（2026-10-16）
   Andy 10-16：「需要新增點閱次數」。
   · POST /v1/articles/view  {id}  → {ok, id, views}   不用登入；同一個 IP 同一篇 30 分鐘內只算一次（記憶體去重）；每 IP 每小時最多 120 次
   · POST /v1/articles/stats {}    → {views:{id:N}}     列表頁一次拿全部
   · 文章 id 只收英數、點、底線、減號（最長 80）；資料表最多 3000 列，避免被灌垃圾 id
   ============================================================================ */
export function installArticles(Hub, EXPORT_TABLES) {
  for (const t of ['article_views', 'article_views_day']) if (EXPORT_TABLES && !EXPORT_TABLES.includes(t)) EXPORT_TABLES.push(t);   // 備份一起帶走
  const ID_RE = /^[A-Za-z0-9._-]{4,80}$/;
  const DEDUP_MS = 30 * 60 * 1000, IP_HOUR_MAX = 120, MAX_ROWS = 3000;
  /* 備份匯出前要先有表（見 pay.js 的 expInit 做法）*/
  const origExpInit = Hub.prototype.expInit;
  Hub.prototype.expInit = function () { if (origExpInit) origExpInit.call(this); this.artInit(); };
  Hub.prototype.artInit = function () {
    if (this._artOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_views (id TEXT PRIMARY KEY, views INTEGER DEFAULT 0, updated INTEGER)');
    /* 2026-10-16 每日點閱（Andy：「新增統計數據，可以統計文章點擊次數，可以篩選族群 類型，需要將資訊可視化」）：只記「台北日期＋文章＋次數」，不記是誰；保留 400 天 */
    this.q('CREATE TABLE IF NOT EXISTS article_views_day (day TEXT, id TEXT, n INTEGER, PRIMARY KEY (day, id))');
    this._artSeen = new Map();   // ip|id → 上次計數時間
    this._artIp = new Map();     // ip → [小時, 次數]
    this._artOk = true;
  };
  const views = (hub, id) => (hub.q('SELECT views FROM article_views WHERE id = ?', id)[0] || {}).views || 0;
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/articles/view': async function (req, b) {
      this.artInit();
      const id = String((b && b.id) || '');
      if (!ID_RE.test(id)) return this.json(req, { error: 'bad_id' }, 400);
      const ip = req.headers.get('CF-Connecting-IP') || 'local', now = this.now(), hr = Math.floor(now / 3600000);
      const k = ip + '|' + id, last = this._artSeen.get(k);
      const r = this._artIp.get(ip);
      const over = r && r[0] === hr && r[1] >= IP_HOUR_MAX;
      if ((!last || now - last > DEDUP_MS) && !over) {
        const exists = this.q('SELECT 1 FROM article_views WHERE id = ?', id).length;
        if (exists || this.q('SELECT COUNT(*) AS c FROM article_views')[0].c < MAX_ROWS) {
          this.q('INSERT INTO article_views (id, views, updated) VALUES (?, 1, ?) ON CONFLICT(id) DO UPDATE SET views = views + 1, updated = excluded.updated', id, now);
          const day = new Date(now + 8 * 3600e3).toISOString().slice(0, 10);
          this.q('INSERT INTO article_views_day (day, id, n) VALUES (?, ?, 1) ON CONFLICT(day, id) DO UPDATE SET n = n + 1', day, id);
          if (Math.random() < 0.01) this.q('DELETE FROM article_views_day WHERE day < ?', new Date(now + 8 * 3600e3 - 400 * 86400e3).toISOString().slice(0, 10));
          this._artSeen.set(k, now);
          if (this._artSeen.size > 20000) this._artSeen.clear();
          if (!r || r[0] !== hr) this._artIp.set(ip, [hr, 1]); else r[1]++;
          if (this._artIp.size > 5000) this._artIp.clear();
        }
      }
      return this.json(req, { ok: true, id, views: views(this, id) });
    },
    /* 管理者：每日點閱明細 {t, from?} → {first, rows:[[day, id, n]…]}（from 預設 400 天前；first＝有紀錄的第一天） */
    '/v1/articles/stats/daily': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const lim = new Date(this.now() + 8 * 3600e3 - 400 * 86400e3).toISOString().slice(0, 10);
      const from = /^\d{4}-\d\d-\d\d$/.test(String(b.from || '')) && b.from > lim ? b.from : lim;
      const first = (this.q('SELECT MIN(day) AS d FROM article_views_day')[0] || {}).d || null;
      return this.json(req, { first, rows: this.q('SELECT day, id, n FROM article_views_day WHERE day >= ? ORDER BY day', from).map((r) => [r.day, r.id, r.n]) });
    },
    '/v1/articles/stats': async function (req) {
      this.artInit();
      const out = {};
      for (const r of this.q('SELECT id, views FROM article_views ORDER BY views DESC LIMIT 1000')) out[r.id] = r.views;
      return this.json(req, { views: out });
    },
  });

  /* ==========================================================================
     精選文章／短影片「產出佇列」（2026-10-16）
     Andy 10-16：「claude 指負責產出文章，內容……下方是我有功能可以點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」。
     流程：管理區點主題 →「產生精選文章／產生短影片」→ 這裡排一筆 queued →
           GitHub Actions（article-jobs.yml，帶 BACKUP_TOKEN）每小時把未完成的同步進 repo（data/_state/article_jobs.json）→
           Claude 排程讀那支檔撰寫、推上 main → 再透過同一支工作流標 working／done（result＝文章 id）。
     · 管理者路由（Origin 白名單＋管理者權杖）：
         /v1/articles/jobs/add    {t, topic_id, kind:'article'|'video'|'topics', title, note?} → {ok, job, dup?, fired}
         /v1/articles/jobs/list   {t} → {jobs:[…最近 200 筆]}
         /v1/articles/jobs/cancel {t, id} → 只有 queued 能取消
     · 機器路由（不檢查 Origin，只認 Authorization: Bearer <ARTICLE_BOT_KEY 或 BACKUP_TOKEN>）：
         POST /v1/articles/jobs/bot {op:'open'} → {jobs:[queued＋working]}
         POST /v1/articles/jobs/bot {op:'mark', id, status:'working'|'done'|'failed', result?, stage?} → {ok, job}
     · 階段（stage，2026-10-17）：Andy 10-17「這邊一直顯示排隊中，但我不清楚他狀況如何，所以多一個進度條，並且備註目前的階段」。
         只收白名單 STAGES（plan 安排主題｜research 查資料｜write 撰寫｜illus 插圖｜review 驗收｜publish 發布中），
         百分比由前端固定對照，不存數字 —— 外部只能挑格子，不能亂填「87%」。白名單外的值直接忽略（不報錯，免得工作流因為打錯字整輪失敗）。
         status 變 done／cancelled → stage 跟著變成 done／cancelled；
         status 變 failed → stage「不動」，停在失敗前那一格（前端把那一格塗紅，才看得出卡在哪一步；若根本沒開工就是 failed）；
         status 變 working 而沒給 stage → 預設 plan（已經在 working 的就保留原本那格）。stage_at＝階段最後一次變動的時間。
         舊資料庫沒有 stage／stage_at 兩欄：artInit 用 PRAGMA 判斷再 ALTER（重跑不報錯），舊列兩欄為空，前端當「排隊中／看 status」處理。
     同一個主題＋同一種產出還沒完成時再按，不重複排（回 dup:true 與原本那筆）。未完成的最多 100 筆。
     ========================================================================== */
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_jobs')) EXPORT_TABLES.push('article_jobs');
  /* 2026-10-17 加 'topics'＝「請 Claude 生成新的主題候選」（Andy 10-17：「多新增一個新增主題 Btn……可以單選和多選分類，也可以我提供關鍵字你幫我生成主題」）。
     它不是文章：topic_id 一律 gen-<毫秒時間戳>、note 一律結構化字串 cats=<類別,…>;n=<1～5>[;kw=<關鍵字>]（docs/articles/topic_gen.md 照這個解析），
     格式不對就 400 —— Claude 排程讀到的一定是解析得了的東西。重複檢查照舊（同 id＋同種類未完成不重排）。 */
  const KINDS = ['article', 'video', 'topics'], MARKS = ['working', 'done', 'failed'], OPEN_MAX = 100;
  const GEN_RE = /^gen-\d{10,16}$/;
  const GEN_NOTE_RE = /^cats=(news|intro|know)(,(news|intro|know)){0,2};n=[1-5](;kw=[^;=<>\u0000-\u001f\u007f]{1,40})?$/;
  const genOk = (topic, note) => {
    if (!GEN_RE.test(topic) || !GEN_NOTE_RE.test(note)) return false;
    const cats = note.slice(5).split(';')[0].split(',');
    if (new Set(cats).size !== cats.length) return false;   // cats=news,news 這種重複的也擋
    const kw = (note.split(';kw=')[1] || '');
    return !kw || kw.trim() === kw;                          // 關鍵字頭尾不准留空白（前端已 trim；手打 API 的才會撞到）
  };
  const STAGES = ['plan', 'research', 'write', 'illus', 'review', 'publish'];
  const TOPIC_RE = /^[A-Za-z0-9._-]{1,80}$/;
  const clip = (x, n) => String(x == null ? '' : x).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, n);
  const eqConst = (a, b) => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };
  const origArtInit = Hub.prototype.artInit;
  Hub.prototype.artInit = function () {
    origArtInit.call(this);
    if (this._artJobOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id TEXT, kind TEXT, title TEXT, note TEXT, status TEXT, created INTEGER, updated INTEGER, by TEXT, result TEXT)');
    /* 2026-10-17 階段欄：ALTER 重跑會報錯，Durable Object 每次冷啟動都會進這裡，所以先 PRAGMA 看欄位在不在 */
    const jc = new Set(this.q('PRAGMA table_info(article_jobs)').map((c) => c.name));
    if (!jc.has('stage')) this.q('ALTER TABLE article_jobs ADD COLUMN stage TEXT');
    if (!jc.has('stage_at')) this.q('ALTER TABLE article_jobs ADD COLUMN stage_at INTEGER');
    this._artJobOk = true;
  };
  const jobOf = (hub, id) => hub.q('SELECT id, topic_id, kind, title, note, status, created, updated, result, stage, stage_at FROM article_jobs WHERE id = ?', id)[0] || null;
  const OPEN_SQL = "SELECT id, topic_id, kind, title, note, status, created, updated, result, stage, stage_at FROM article_jobs WHERE status IN ('queued','working') ORDER BY id";
  /* 2026-10-17 Andy：「這為何要下一個 05 才能開工，而非我執行後就開工」→ 送出請求時直接叫醒 Claude 的排程（routine 的 API trigger）。
     鑰匙 ROUTINE_FIRE_TOKEN（Andy 在 claude.ai/code/routines 產生，存 GitHub Secret，deploy-account-worker.yml 寫進來）；沒設＝不叫，照舊等整點。
     防連打：2 分鐘內只叫一次（kv art_fire_at）；叫不到不影響請求本身。官方限制每個排程每小時 30 次。 */
  const ROUTINE_DEFAULT = 'trig_01JSw5RrpyD94edAaUY69HMo';
  Hub.prototype.artFire = async function (text, force) {
    const tok = String(this.env.ROUTINE_FIRE_TOKEN || ''), rid = String(this.env.ROUTINE_ID || ROUTINE_DEFAULT);
    if (tok.length < 16 || !/^trig_[A-Za-z0-9]{8,40}$/.test(rid)) return false;
    const now = this.now(), last = Number(this.kv('art_fire_at') || 0);
    if (!force && now - last < 120000) return true;   // 剛叫過，那一輪會處理到這筆
    if (force && now - last < 30000) return true;
    try {
      const r = await fetch(`https://api.anthropic.com/v1/claude_code/routines/${rid}/fire`, {
        method: 'POST', signal: AbortSignal.timeout(5000),
        headers: { Authorization: 'Bearer ' + tok, 'anthropic-beta': 'experimental-cc-routine-2026-04-01', 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: String(text).slice(0, 200) }),
      });
      if (!r.ok) return false;
      this.setKv('art_fire_at', now);
      return true;
    } catch (e) { return false; }
  };
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/articles/jobs/add': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const topic = String(b.topic_id || ''), kind = String(b.kind || ''), title = clip(b.title, 120), note = clip(b.note, 500);
      if (!TOPIC_RE.test(topic) || !KINDS.includes(kind) || !title) return this.json(req, { error: 'bad_input' }, 400);
      if (kind === 'topics' && !genOk(topic, note)) return this.json(req, { error: 'bad_input' }, 400);
      const dup = this.q("SELECT id FROM article_jobs WHERE topic_id = ? AND kind = ? AND status IN ('queued','working') ORDER BY id DESC LIMIT 1", topic, kind)[0];
      if (dup) return this.json(req, { ok: true, dup: true, job: jobOf(this, dup.id) });
      if (this.q("SELECT COUNT(*) AS c FROM article_jobs WHERE status IN ('queued','working')")[0].c >= OPEN_MAX) return this.json(req, { error: 'too_many' }, 429);
      const now = this.now();
      this.q("INSERT INTO article_jobs (topic_id, kind, title, note, status, created, updated, by) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)", topic, kind, title, note, now, now, String(v.user.uid || ''));
      const id = this.q('SELECT last_insert_rowid() AS id')[0].id;
      const fired = await this.artFire(kind === 'topics' ? `管理區新增主題請求 #${id}` : `管理區新請求 #${id}`);
      return this.json(req, { ok: true, job: jobOf(this, id), fired });
    },
    /* 「立即開工」：佇列裡有排隊中的就叫醒 Claude 排程（沒排隊的不叫，免得白跑一輪） */
    '/v1/articles/jobs/kick': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const n = this.q("SELECT COUNT(*) AS c FROM article_jobs WHERE status = 'queued'")[0].c;
      if (!n) return this.json(req, { ok: true, fired: false, reason: 'empty' });
      return this.json(req, { ok: true, fired: await this.artFire(`管理區按「立即開工」（排隊中 ${n} 筆）`, true) });
    },
    '/v1/articles/jobs/list': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      return this.json(req, { jobs: this.q('SELECT id, topic_id, kind, title, note, status, created, updated, result, stage, stage_at FROM article_jobs ORDER BY id DESC LIMIT 200') });
    },
    '/v1/articles/jobs/cancel': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const id = Number(b.id), j = Number.isInteger(id) ? jobOf(this, id) : null;
      if (!j) return this.json(req, { error: 'not_found' }, 404);
      if (j.status !== 'queued') return this.json(req, { error: 'not_queued', job: j }, 409);
      const now = this.now();
      this.q("UPDATE article_jobs SET status = 'cancelled', stage = 'cancelled', stage_at = ?, updated = ? WHERE id = ?", now, now, id);
      return this.json(req, { ok: true, job: jobOf(this, id) });
    },
  });
  /* ==========================================================================
     「產精選文章頻率」設定（2026-10-16 建；同日晚改第 2 版）
     Andy 10-16：「我需要可以產貼文頻率設定……每週幾、哪個時段幫我產出精選貼文」。
     第 2 版 Andy 10-16：「應該是可以選擇 日期 後面是時段以小時為單位……然後接者是產的類型選擇，啟用應該是這邊都選完才會輪到」。
     → 設定從「星期 × 三個固定輪次＋一組全域篇數」改成「規則清單」：每條規則自己帶日期（每週幾 或 指定日期）、整點時段、各類別篇數，
       這樣「哪個時段產什麼」寫在同一條規則裡，不用再對照兩塊。
     做法照產出佇列：管理區每次增刪規則／切開關 → 這裡存一份（只留最新一份有效，舊的留作紀錄）→ article-jobs.yml 每小時把最新一份同步進
     repo（data/_state/article_schedule.json），同一輪 scripts/article_jobs.py 比對「現在台北的日期或星期＋小時」，對得上就依篇數排進佇列 → Claude 排程（台北每小時 :05）處理佇列。
     · 管理者路由：/v1/articles/schedule/get {t} → {schedule|null, allowed}；/v1/articles/schedule/add {t, ver:2, enabled, rules} → {ok, schedule}
     · 機器路由：/v1/articles/jobs/bot {op:'schedule'} → {schedule|null}；{op:'add', topic_id:'sch-…', kind:'article', title, note} → 到點的規則排進佇列
       （由每小時的 article-jobs.yml 呼叫，不是 Claude —— Claude 的 session 拿不到機器鑰匙，所以「到點排隊」放在工作流做，Claude 只負責處理佇列）
     · 新格式：{ver:2, enabled, rules:[{days:[1..7]（1＝週一…7＝週日）或 dates:["YYYY-MM-DD"]（擇一）, hours:[0..23], cats:{news,intro,know}}]}
     · 嚴格驗證、壞輸入回 400 不猜：每條規則 hours ≥1、cats 至少一類 >0、days／dates 擇一且非空、日期必須是真的日曆日；開著時 rules 不可空；最多 20 條。
       過去的日期不在這裡擋（前端不給選；已經過期的規則留著不會觸發，擋了反而讓 Andy 切開關時整份存不進去）。
     · 讀到第 1 版（slots／cats）一律轉成第 2 版回去（09:50→9、14:50→14、20:50→20；同一組時段的星期併成一條），前端不必認舊格式。
     ========================================================================== */
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_schedule')) EXPORT_TABLES.push('article_schedule');
  const SCH_HOURS = Array.from({ length: 24 }, (_, i) => i), SCH_CATS = ['news', 'intro', 'know'], SCH_MAX = 3, SCH_KEEP = 50, SCH_RULES = 20, SCH_DATES = 31;
  const origArtInit2 = Hub.prototype.artInit;
  Hub.prototype.artInit = function () {
    origArtInit2.call(this);
    if (this._artSchOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, cfg TEXT, created INTEGER, by TEXT)');
    this._artSchOk = true;
  };
  const isObj = (x) => !!x && typeof x === 'object' && !Array.isArray(x);
  const realDate = (s) => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) && new Date(s + 'T00:00:00Z').toISOString().slice(0, 10) === s;   // 2026-02-30 這種會被 Date 進位，比對回來就不相等
  const uniqSort = (a) => [...new Set(a)].sort((x, y) => (x < y ? -1 : x > y ? 1 : 0));
  /* 一條規則：驗證並整理成固定形狀（排序、去重）；壞的回 null */
  function cleanRule(r) {
    if (!isObj(r)) return null;
    for (const k of Object.keys(r)) if (!['days', 'dates', 'hours', 'cats'].includes(k)) return null;
    const hasD = r.days != null, hasT = r.dates != null;
    if (hasD === hasT) return null;   // 兩個都給或都沒給 ＝ 不知道要哪一種，不猜
    const out = {};
    if (hasD) {
      if (!Array.isArray(r.days) || !r.days.length || r.days.some((d) => !Number.isInteger(d) || d < 1 || d > 7)) return null;
      out.days = uniqSort(r.days);
    } else {
      if (!Array.isArray(r.dates) || !r.dates.length || r.dates.length > SCH_DATES || r.dates.some((d) => !realDate(d))) return null;
      out.dates = uniqSort(r.dates);
    }
    if (!Array.isArray(r.hours) || !r.hours.length || r.hours.some((h) => !Number.isInteger(h) || h < 0 || h > 23)) return null;
    out.hours = uniqSort(r.hours);
    if (!isObj(r.cats)) return null;
    for (const k of Object.keys(r.cats)) if (!SCH_CATS.includes(k)) return null;
    out.cats = {};
    for (const k of SCH_CATS) {
      const n = r.cats[k] == null ? 0 : r.cats[k];
      if (!Number.isInteger(n) || n < 0 || n > SCH_MAX) return null;
      out.cats[k] = n;
    }
    if (!SCH_CATS.some((k) => out.cats[k] > 0)) return null;   // 一篇都不產的規則沒有意義
    return out;
  }
  /* 整份設定：壞輸入回 null（不猜、不補） */
  function cleanSchedule(b) {
    if (!isObj(b) || typeof b.enabled !== 'boolean') return null;
    if (b.ver != null && b.ver !== 2) return null;
    if (!Array.isArray(b.rules) || b.rules.length > SCH_RULES) return null;
    const rules = [];
    for (const r of b.rules) { const c = cleanRule(r); if (!c) return null; rules.push(c); }
    if (b.enabled && !rules.length) return null;   // 開著卻沒有規則 ＝ 不會做任何事，擋下
    return { ver: 2, enabled: b.enabled, rules };
  }
  /* 第 1 版 → 第 2 版：同一組時段的星期併成一條規則；篇數是全域的，每條都帶同一組；篇數全 0 或沒時段 → 沒有規則、視為關閉 */
  function upgradeSchedule(c) {
    if (!isObj(c) || c.ver === 2) return c;
    const cats = {}; SCH_CATS.forEach((k) => { const n = Number(c.cats && c.cats[k]); cats[k] = Number.isInteger(n) && n >= 0 && n <= SCH_MAX ? n : 0; });
    const groups = {};
    const sl = isObj(c.slots) ? c.slots : {};
    Object.keys(sl).sort().forEach((d) => {
      const hs = uniqSort((Array.isArray(sl[d]) ? sl[d] : []).map((t) => parseInt(String(t), 10)).filter((h) => Number.isInteger(h) && h >= 0 && h <= 23));
      if (!/^[1-7]$/.test(d) || !hs.length) return;
      const key = hs.join(',');
      (groups[key] = groups[key] || { days: [], hours: hs }).days.push(+d);
    });
    const rules = SCH_CATS.some((k) => cats[k] > 0) ? Object.values(groups).sort((x, y) => x.days[0] - y.days[0]).map((g) => ({ days: g.days, hours: g.hours, cats: { ...cats } })) : [];
    return { ver: 2, enabled: !!c.enabled && rules.length > 0, rules, legacy: true };
  }
  const latestSchedule = (hub) => {
    const r = hub.q('SELECT cfg, created FROM article_schedule ORDER BY id DESC LIMIT 1')[0];
    if (!r) return null;
    try { return { ...upgradeSchedule(JSON.parse(r.cfg)), updated: r.created }; } catch (e) { return null; }
  };
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/articles/schedule/get': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      return this.json(req, { schedule: latestSchedule(this), allowed: { hours: SCH_HOURS, cats: SCH_CATS, max: SCH_MAX, maxRules: SCH_RULES, maxDates: SCH_DATES } });
    },
    '/v1/articles/schedule/add': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const c = cleanSchedule(b); if (!c) return this.json(req, { error: 'bad_input' }, 400);
      this.q('INSERT INTO article_schedule (cfg, created, by) VALUES (?, ?, ?)', JSON.stringify(c), this.now(), String(v.user.uid || ''));
      this.q('DELETE FROM article_schedule WHERE id <= (SELECT MAX(id) FROM article_schedule) - ?', SCH_KEEP);
      return this.json(req, { ok: true, schedule: latestSchedule(this) });
    },
  });
  /* ==========================================================================
     防白嫖（2026-10-16，docs/security/anti_freeload_1016.md 的「最小有效版本」）
     Andy 10-16：已公開的 4 篇維持原狀；從新文章起「全文只在會員後端」，訪客今日事件 5 次改伺服器端計數。

     ① 新文章全文存在這個 Durable Object（article_body）。公開的 site/articles/index.json 只留標題、分類、日期、topic、族群、reading_min（不含摘要／副標／標籤／內文），
        單篇要 POST /v1/articles/get 才拿得到：
          · 未登入 → 401；訪客／註冊會員（art.read.n＝0）→ 403；Plus（預設 5）→ 伺服器記「誰讀過哪一篇」（article_reads），重讀不重複計數，第 6 篇回 402 quota；Pro／管理者不限
          · 計數在伺服器，清 localStorage、換瀏覽器、換裝置都不會重算
        寫入走機器路由 /v1/articles/jobs/bot {op:'put_body', id, json}（ARTICLE_BOT_KEY／BACKUP_TOKEN），不開放給任何網頁來源。
     ② 累計額度 /v1/total/state、/v1/total/use（events.total）：
          · 登入者以 uid 計；訪客以「Worker 簽發的訪客編號 g1.<隨機>.<簽章>」＋「連線 IP 單向雜湊」雙鍵計數
          · 訪客編號由前端存 localStorage、用請求標頭 X-Tw-Guest 送（不用 Cookie：跨網站 Cookie 在 Safari 等會被擋，也要跟隱私權政策「不使用 Cookie 進行追蹤」一致）
          · IP 只存 HMAC(每週換的鹽, 'tot:'+IP 網段)；鹽存在 DO 自己的 kv，換鹽時整批清掉舊雜湊；資料表 8 天就刪；訪客編號 180 天沒出現就刪
          · 共用 IP 的緩解：同一個 IP 這週出現超過 3 個不同訪客編號，才開始用「IP 總量上限（個人上限 × 4）」；正常同事每人只有一個編號，不會被互相拖累
     ⚠ 擋不住的（誠實講）：換網路／VPN 後再開無痕；舊 4 篇與公開的 news.json／data parquet（內容本來就是公開檔）；付費會員分享帳號。
     ========================================================================== */
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_body')) EXPORT_TABLES.push('article_body');   // 全文只在這裡 → 一定要進備份
  const BODY_RAW_MAX = 300000, BODY_MAX = 200000;
  const TOT_CFG = {
    /* 沒有任何設定時的預設（跟 site/features.js 的 defBy 一致）：guest／free／plus／其他付費；Infinity＝不限 */
    'events.total': { guest: 5, free: Infinity, plus: Infinity, other: Infinity },
    'art.read.n': { guest: 0, free: 0, plus: 5, other: Infinity },
  };
  const TOT_KEY_RE = /^[A-Za-z0-9_.-]{1,40}$/;
  const IP_MULT = 4, IP_NEW_GUESTS = 3, GUEST_KEEP_DAYS = 180, IP_KEEP_DAYS = 8, WEEK_MS = 7 * 86400e3;
  const b64u = (u8) => btoa(String.fromCharCode(...u8)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const randB64 = (n) => b64u(crypto.getRandomValues(new Uint8Array(n)));
  const encT = new TextEncoder();
  async function hmacWith(keyStr, msg) {
    const k = await crypto.subtle.importKey('raw', encT.encode(keyStr), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
    return b64u(new Uint8Array(await crypto.subtle.sign('HMAC', k, encT.encode(msg))));
  }
  /* IPv4 取完整位址；IPv6 取前 64 位元（同一戶的裝置共用一個 /64）。看不出來的字串原樣（測試的 'local' 等）*/
  function ipNorm(ip) {
    ip = String(ip || 'local').trim().toLowerCase();
    if (!ip.includes(':')) return ip;
    const [h, t = ''] = ip.split('::');
    const a = h ? h.split(':') : [], z = t ? t.split(':') : [];
    const full = ip.includes('::') ? a.concat(Array(Math.max(0, 8 - a.length - z.length)).fill('0'), z) : a;
    return full.slice(0, 4).map((x) => (x || '0').padStart(4, '0')).join(':') + '::/64';
  }
  /* 每週換鹽：鹽只存在這個 Durable Object 的 kv；換週時把舊雜湊整批刪掉（舊鹽丟了，舊雜湊也永遠對不回 IP） */
  const weekOf = (ms) => Math.floor((ms + 8 * 3600e3 + 3 * 86400e3) / WEEK_MS);   // 以台北週一為界（1970-01-01 是週四，+3 天對齊）
  Hub.prototype.totSalt = function () {
    const w = weekOf(this.now());
    let cur = null; try { cur = JSON.parse(this.kv('tot_salt') || 'null'); } catch (e) { cur = null; }
    if (!cur || cur.w !== w || !cur.s) {
      cur = { w, s: randB64(24) };
      this.setKv('tot_salt', JSON.stringify(cur));
      this.q('DELETE FROM tot_ip'); this.q('DELETE FROM tot_ipg');
    }
    return cur.s;
  };
  Hub.prototype.totIpHash = async function (req) { return hmacWith(this.totSalt(), 'tot:' + ipNorm(req.headers.get('CF-Connecting-IP'))); };
  const origArtInit3 = Hub.prototype.artInit;
  Hub.prototype.artInit = function () {
    origArtInit3.call(this);
    if (this._totOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_body (id TEXT PRIMARY KEY, json TEXT, updated INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS article_reads (uid TEXT, id TEXT, at INTEGER, PRIMARY KEY (uid, id))');
    /* sub＝'g:<訪客編號隨機段>' 或 'u:<uid>'；key＝這次用掉的對象（今日事件：每次打開一個隨機碼；同一個 key 重送不重算） */
    this.q('CREATE TABLE IF NOT EXISTS tot_use (sub TEXT, id TEXT, key TEXT, at INTEGER, PRIMARY KEY (sub, id, key))');
    this.q('CREATE TABLE IF NOT EXISTS tot_guest (sub TEXT PRIMARY KEY, seen INTEGER)');
    this.q('CREATE TABLE IF NOT EXISTS tot_ip (iph TEXT, id TEXT, sub TEXT, key TEXT, at INTEGER, PRIMARY KEY (iph, id, sub, key))');
    this.q('CREATE TABLE IF NOT EXISTS tot_ipg (iph TEXT, sub TEXT, PRIMARY KEY (iph, sub))');
    this._totOk = true;
  };
  /* 保存期限：IP 雜湊 8 天、訪客 180 天沒出現就刪（隨每小時的 alarm 一起跑） */
  const origCleanup = Hub.prototype.cleanup;
  Hub.prototype.cleanup = function () {
    if (origCleanup) origCleanup.call(this);
    this.artInit();
    const now = this.now();
    this.q('DELETE FROM tot_ip WHERE at < ?', now - IP_KEEP_DAYS * 86400e3);
    this.q('DELETE FROM tot_ipg WHERE sub NOT IN (SELECT sub FROM tot_guest WHERE seen >= ?)', now - IP_KEEP_DAYS * 86400e3);
    const old = this.q('SELECT sub FROM tot_guest WHERE seen < ?', now - GUEST_KEEP_DAYS * 86400e3);
    for (const r of old) { this.q('DELETE FROM tot_use WHERE sub = ?', r.sub); this.q('DELETE FROM tot_guest WHERE sub = ?', r.sub); }
  };
  /* 刪除帳號：這個人在本區塊的紀錄一起刪 */
  const origDelete = Hub.prototype.deleteMe;
  Hub.prototype.deleteMe = async function (req, b) {
    const v = await this.auth(req, b);
    const res = await origDelete.call(this, req, b);
    if (v && res.status === 200) { this.artInit(); this.q('DELETE FROM article_reads WHERE uid = ?', v.user.uid); this.q('DELETE FROM tot_use WHERE sub = ?', 'u:' + v.user.uid); }
    return res;
  };

  /* 這個人的某個累計額度上限：Infinity＝不限。管理者／擁有者不限；其餘依方案範本 feats（整數；≥999＝不限；false＝0），沒寫就用預設表 */
  Hub.prototype.totLimitOf = function (id, v) {
    const cfg = TOT_CFG[id]; if (!cfg) return null;
    if (v && this.isAdmin(v.user)) return Infinity;
    let feats, key;
    if (!v) { feats = (this.plan('guest') || { feats: {} }).feats; key = 'guest'; }
    else {
      const e = this.effective(String(v.user.email || '').toLowerCase());
      const plan = e.expired ? 'free' : e.plan;
      feats = e.expired ? ((this.plan('free') || { feats: {} }).feats) : e.feats;
      key = plan === 'free' ? 'free' : plan === 'plus' ? 'plus' : 'other';
    }
    const x = feats ? feats[id] : undefined;
    if (Number.isInteger(x)) return x >= 999 ? Infinity : Math.max(0, x);
    if (x === false) return 0;
    return cfg[key];
  };
  const limOut = (n) => (n === Infinity ? null : n);      // JSON 沒有 Infinity：null＝不限

  /* 訪客編號：g1.<16 位元組隨機>.<簽章22字>；簽章用 Worker 自己的 HMAC 金鑰 → 前端偽造不了（自己編一個會被當成「新訪客」重新發） */
  Hub.prototype.guestVerify = async function (g) {
    const p = String(g || '').split('.');
    if (p.length !== 3 || p[0] !== 'g1' || !/^[A-Za-z0-9_-]{22}$/.test(p[1]) || !/^[A-Za-z0-9_-]{22}$/.test(p[2])) return null;
    return (await this.hmac('g:' + p[1])).slice(0, 22) === p[2] ? 'g:' + p[1] : null;
  };
  Hub.prototype.guestIssue = async function () { const r = randB64(16); return { g: `g1.${r}.${(await this.hmac('g:' + r)).slice(0, 22)}`, sub: 'g:' + r }; };
  const keysOf = (hub, sub, id) => hub.q('SELECT key FROM tot_use WHERE sub = ? AND id = ? ORDER BY at, key', sub, id).map((r) => r.key);

  Object.assign(Hub.prototype.subRoutes, {
    /* 目前各累計額度用了幾次：{ids:['events.total','art.read.n'], t?} + 標頭 X-Tw-Guest → {limits:{id:{limit,used:[…]}}}
       不發訪客編號（沒有就空的）；發號只在 /use */
    '/v1/total/state': async function (req, b) {
      this.artInit();
      const v = b.t ? await this.verify(b.t) : null;
      if (b.t && !v) return this.json(req, { error: 'auth' }, 401);
      const ids = (Array.isArray(b.ids) ? b.ids : []).filter((x) => TOT_CFG[x]).slice(0, 4);
      const gsub = v ? null : await this.guestVerify(req.headers.get('X-Tw-Guest'));
      const out = {};
      for (const id of ids) {
        const lim = this.totLimitOf(id, v);
        let used = [];
        if (id === 'art.read.n') used = v ? this.q('SELECT id FROM article_reads WHERE uid = ? ORDER BY at', v.user.uid).map((r) => r.id) : [];
        else used = v ? keysOf(this, 'u:' + v.user.uid, id) : gsub ? keysOf(this, gsub, id) : [];
        out[id] = { limit: limOut(lim), used };
      }
      return this.json(req, { limits: out });
    },
    /* 用掉一次：{id:'events.total', key, t?} + X-Tw-Guest → {ok, limit, used:[keys], g?, why?}
       · 同一個 key 重送不重算（已經算過的永遠 ok）
       · 訪客：個人上限（訪客編號）＋ IP 總量（同 IP 這週出現超過 3 個不同編號才啟用，上限＝個人上限×4）
       · 沒登入且沒有有效的訪客編號 → 現場發一個新的放在回應的 g，前端存起來下次帶 */
    '/v1/total/use': async function (req, b) {
      this.artInit();
      const id = String(b.id || ''), key = String(b.key || '');
      if (id !== 'events.total' || !TOT_KEY_RE.test(key)) return this.json(req, { error: 'bad_input' }, 400);
      const v = b.t ? await this.verify(b.t) : null;
      if (b.t && !v) return this.json(req, { error: 'auth' }, 401);
      const lim = this.totLimitOf(id, v);
      if (lim === Infinity) return this.json(req, { ok: true, limit: null, used: [] });
      const now = this.now();
      let sub, g;
      if (v) sub = 'u:' + v.user.uid;
      else {
        sub = await this.guestVerify(req.headers.get('X-Tw-Guest'));
        if (!sub) { const n = await this.guestIssue(); sub = n.sub; g = n.g; }
      }
      const done = (extra) => this.json(req, Object.assign({ limit: limOut(lim), used: keysOf(this, sub, id) }, g ? { g } : {}, extra));
      if (this.q('SELECT 1 FROM tot_use WHERE sub = ? AND id = ? AND key = ?', sub, id, key).length) return done({ ok: true });     // 重送：不重算
      let iph = null;
      if (!v) {
        iph = await this.totIpHash(req);
        this.q('INSERT INTO tot_guest (sub, seen) VALUES (?, ?) ON CONFLICT(sub) DO UPDATE SET seen = excluded.seen', sub, now);
        this.q('INSERT OR IGNORE INTO tot_ipg (iph, sub) VALUES (?, ?)', iph, sub);
      }
      if (keysOf(this, sub, id).length >= lim) return done({ ok: false, why: 'quota' });
      if (iph) {
        const guests = this.q('SELECT COUNT(*) AS c FROM tot_ipg WHERE iph = ?', iph)[0].c;
        const ipUsed = this.q('SELECT COUNT(*) AS c FROM tot_ip WHERE iph = ? AND id = ?', iph, id)[0].c;
        if (guests > IP_NEW_GUESTS && ipUsed >= lim * IP_MULT) return done({ ok: false, why: 'ip' });
        this.q('INSERT OR IGNORE INTO tot_ip (iph, id, sub, key, at) VALUES (?, ?, ?, ?, ?)', iph, id, sub, key, now);
      }
      this.q('INSERT INTO tot_use (sub, id, key, at) VALUES (?, ?, ?, ?)', sub, id, key, now);
      return done({ ok: true });
    },
    /* 單篇全文：{t, id} → {ok, post, limit, reads:[…]}；規則見檔頭 ① */
    '/v1/articles/get': async function (req, b) {
      this.artInit();
      const id = String(b.id || '');
      if (!ID_RE.test(id)) return this.json(req, { error: 'bad_id' }, 400);
      const v = b.t ? await this.verify(b.t) : null;
      if (!v) return this.json(req, { error: 'auth' }, 401);
      const lim = this.totLimitOf('art.read.n', v);
      const row = this.q('SELECT json FROM article_body WHERE id = ?', id)[0];
      if (!row) return this.json(req, { error: 'not_found' }, 404);          // 沒有這篇不扣額度
      let post; try { post = JSON.parse(row.json); } catch (e) { return this.json(req, { error: 'server' }, 500); }
      if (lim === Infinity) return this.json(req, { ok: true, post, limit: null, reads: [] });
      /* 管理區仍可對某方案整個關掉精選文章或某類別（features.js art.read、art.cat.<類別>）：伺服器也照關，不是只有畫面 */
      const feats = this.effective(String(v.user.email || '').toLowerCase()).feats;
      if (feats['art.read'] === false || feats['art.cat.' + post.cat] === false || lim === 0) return this.json(req, { error: 'forbidden', limit: lim, reads: [] }, 403);
      const reads = () => this.q('SELECT id FROM article_reads WHERE uid = ? ORDER BY at', v.user.uid).map((r) => r.id);
      if (!this.q('SELECT 1 FROM article_reads WHERE uid = ? AND id = ?', v.user.uid, id).length) {
        if (reads().length >= lim) return this.json(req, { error: 'quota', limit: lim, reads: reads() }, 402);
        this.q('INSERT INTO article_reads (uid, id, at) VALUES (?, ?, ?)', v.user.uid, id, this.now());
      }
      return this.json(req, { ok: true, post, limit: lim, reads: reads() });
    },
  });
  /* 機器路由寫入全文：{op:'put_body', id, json:{…整篇文章…}}；json 必須有 title 與 blocks[]，json.id 若有必須等於 id */
  Hub.prototype.artPutBody = function (req, b) {
    const id = String(b.id || '');
    if (!ID_RE.test(id)) return this.json(req, { error: 'bad_id' }, 400);
    const j = b.json;
    if (!j || typeof j !== 'object' || Array.isArray(j) || typeof j.title !== 'string' || !j.title || !Array.isArray(j.blocks) || (j.id != null && j.id !== id)) return this.json(req, { error: 'bad_body' }, 400);
    const txt = JSON.stringify(Object.assign({}, j, { id }));
    if (txt.length > BODY_MAX) return this.json(req, { error: 'too_large' }, 413);
    if (!this.q('SELECT 1 FROM article_body WHERE id = ?', id).length && this.q('SELECT COUNT(*) AS c FROM article_body')[0].c >= 3000) return this.json(req, { error: 'too_many' }, 429);
    this.q('INSERT INTO article_body (id, json, updated) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET json = excluded.json, updated = excluded.updated', id, txt, this.now());
    return this.json(req, { ok: true, id, bytes: txt.length });
  };

  const origFetch = Hub.prototype.fetch;
  Hub.prototype.fetch = async function (req) {
    if (req.method !== 'POST' || new URL(req.url).pathname !== '/v1/articles/jobs/bot') return origFetch.call(this, req);
    try {
      /* 鑰匙：ARTICLE_BOT_KEY（deploy-account-worker.yml 由 CLOUDFLARE_API_TOKEN 推導後寫入；article-jobs.yml 用同一個公式算）或 BACKUP_TOKEN */
      const h = String(req.headers.get('Authorization') || ''), got = h.startsWith('Bearer ') ? h.slice(7).trim() : '';
      const keys = [this.env.ARTICLE_BOT_KEY, this.env.BACKUP_TOKEN].map((k) => String(k || '')).filter((k) => k.length >= 16);
      /* 2026-10-16 最小權限的「只管全文」鑰匙 ARTICLE_PUT_KEY（≥24 字；給 Claude 的雲端環境用）：只能 put_body／del_body／list_bodies，
         不能讀佇列、標狀態、讀頻率設定 —— 它放在 Claude 的環境金鑰裡，不該帶更多權限（BACKUP_TOKEN 更是整庫匯出的鑰匙，絕不可放進去） */
      const putKey = String(this.env.ARTICLE_PUT_KEY || '');
      const isFull = !!got && keys.some((k) => eqConst(got, k));
      const isPutOnly = !isFull && !!got && putKey.length >= 24 && eqConst(got, putKey);
      if (!isFull && !isPutOnly) return this.json(req, { error: 'forbidden' }, 403);
      /* 2026-10-16 防白嫖：put_body 要送整篇全文，上限放寬到 BODY_RAW_MAX；其他 op 仍是 4096（先看大小再解析，超過就不吞） */
      const raw = await req.text(); if (raw.length > BODY_RAW_MAX) return this.json(req, { error: 'too_large' }, 413);
      let b = {}; try { b = JSON.parse(raw || '{}') || {}; } catch (e) { return this.json(req, { error: 'bad_json' }, 400); }
      if (raw.length > 4096 && b.op !== 'put_body') return this.json(req, { error: 'too_large' }, 413);
      this.artInit();
      if (isPutOnly && !['put_body', 'del_body', 'list_bodies'].includes(b.op)) return this.json(req, { error: 'forbidden' }, 403);
      if (b.op === 'put_body') return this.artPutBody(req, b);
      if (b.op === 'del_body') { const id = String(b.id || ''); if (!ID_RE.test(id)) return this.json(req, { error: 'bad_id' }, 400); this.q('DELETE FROM article_body WHERE id = ?', id); return this.json(req, { ok: true, id }); }
      if (b.op === 'list_bodies') return this.json(req, { bodies: this.q('SELECT id, LENGTH(json) AS bytes, updated FROM article_body ORDER BY id') });
      if (b.op === 'open') return this.json(req, { jobs: this.q(OPEN_SQL) });
      if (b.op === 'schedule') return this.json(req, { schedule: latestSchedule(this) });   // 頻率設定（只讀）
      if (b.op === 'mark') {
        const id = Number(b.id), st = String(b.status || ''), j = Number.isInteger(id) ? jobOf(this, id) : null;
        if (!j) return this.json(req, { error: 'not_found' }, 404);
        if (!MARKS.includes(st)) return this.json(req, { error: 'bad_status' }, 400);
        if (j.status === 'cancelled' || j.status === 'done') return this.json(req, { error: 'closed', job: j }, 409);
        const now = this.now(), want = STAGES.includes(String(b.stage || '')) ? String(b.stage) : '';
        let stg = j.stage || null;
        if (st === 'done') stg = 'done';
        else if (st === 'working') stg = want || (j.status === 'working' && STAGES.includes(j.stage) ? j.stage : 'plan');
        else if (st === 'failed' && want) stg = want;          // failed：有給就記在那一格，沒給就停在原本那格
        const stAt = stg !== (j.stage || null) ? now : (j.stage_at || null);
        this.q('UPDATE article_jobs SET status = ?, result = ?, stage = ?, stage_at = ?, updated = ? WHERE id = ?', st, clip(b.result, 200) || j.result || null, stg, stAt, now, id);
        return this.json(req, { ok: true, job: jobOf(this, id) });
      }
      /* 頻率設定到點 → scripts/article_jobs.py 依規則自動排隊（2026-10-16 第 2 版）。
         只收 sch-<YYYYMMDD>-<HH>-r<規則>-<類別>-<第幾篇> 這種 id：同一個 id 不論狀態（連已完成、已取消）都不再排，
         這樣同一小時工作流跑兩次（排程＋文章上架觸發）也不會重複排；Andy 取消掉的也不會被補回來。 */
      if (b.op === 'add') {
        const topic = String(b.topic_id || ''), title = clip(b.title, 120), note = clip(b.note, 500);
        if (!/^sch-\d{8}-\d{2}-r\d{1,2}-(news|intro|know)-\d$/.test(topic) || b.kind !== 'article' || !title) return this.json(req, { error: 'bad_input' }, 400);
        const dup = this.q('SELECT id FROM article_jobs WHERE topic_id = ? ORDER BY id DESC LIMIT 1', topic)[0];
        if (dup) return this.json(req, { ok: true, dup: true, job: jobOf(this, dup.id) });
        if (this.q("SELECT COUNT(*) AS c FROM article_jobs WHERE status IN ('queued','working')")[0].c >= OPEN_MAX) return this.json(req, { error: 'too_many' }, 429);
        const now = this.now();
        this.q("INSERT INTO article_jobs (topic_id, kind, title, note, status, created, updated, by) VALUES (?, 'article', ?, ?, 'queued', ?, ?, 'schedule')", topic, title, note, now, now);
        return this.json(req, { ok: true, job: jobOf(this, this.q('SELECT last_insert_rowid() AS id')[0].id) });
      }
      return this.json(req, { error: 'bad_op' }, 400);
    } catch (e) { return this.json(req, { error: 'server' }, 500); }
  };
}
