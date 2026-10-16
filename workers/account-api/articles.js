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
         /v1/articles/jobs/add    {t, topic_id, kind:'article'|'video', title, note?} → {ok, job, dup?}
         /v1/articles/jobs/list   {t} → {jobs:[…最近 200 筆]}
         /v1/articles/jobs/cancel {t, id} → 只有 queued 能取消
     · 機器路由（不檢查 Origin，只認 Authorization: Bearer <ARTICLE_BOT_KEY 或 BACKUP_TOKEN>）：
         POST /v1/articles/jobs/bot {op:'open'} → {jobs:[queued＋working]}
         POST /v1/articles/jobs/bot {op:'mark', id, status:'working'|'done'|'failed', result?} → {ok, job}
     同一個主題＋同一種產出還沒完成時再按，不重複排（回 dup:true 與原本那筆）。未完成的最多 100 筆。
     ========================================================================== */
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_jobs')) EXPORT_TABLES.push('article_jobs');
  const KINDS = ['article', 'video'], MARKS = ['working', 'done', 'failed'], OPEN_MAX = 100;
  const TOPIC_RE = /^[A-Za-z0-9._-]{1,80}$/;
  const clip = (x, n) => String(x == null ? '' : x).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, n);
  const eqConst = (a, b) => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };
  const origArtInit = Hub.prototype.artInit;
  Hub.prototype.artInit = function () {
    origArtInit.call(this);
    if (this._artJobOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id TEXT, kind TEXT, title TEXT, note TEXT, status TEXT, created INTEGER, updated INTEGER, by TEXT, result TEXT)');
    this._artJobOk = true;
  };
  const jobOf = (hub, id) => hub.q('SELECT id, topic_id, kind, title, note, status, created, updated, result FROM article_jobs WHERE id = ?', id)[0] || null;
  const OPEN_SQL = "SELECT id, topic_id, kind, title, note, status, created, updated, result FROM article_jobs WHERE status IN ('queued','working') ORDER BY id";
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/articles/jobs/add': async function (req, b) {
      const v = await this.admin(req, b); if (!v) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const topic = String(b.topic_id || ''), kind = String(b.kind || ''), title = clip(b.title, 120), note = clip(b.note, 500);
      if (!TOPIC_RE.test(topic) || !KINDS.includes(kind) || !title) return this.json(req, { error: 'bad_input' }, 400);
      const dup = this.q("SELECT id FROM article_jobs WHERE topic_id = ? AND kind = ? AND status IN ('queued','working') ORDER BY id DESC LIMIT 1", topic, kind)[0];
      if (dup) return this.json(req, { ok: true, dup: true, job: jobOf(this, dup.id) });
      if (this.q("SELECT COUNT(*) AS c FROM article_jobs WHERE status IN ('queued','working')")[0].c >= OPEN_MAX) return this.json(req, { error: 'too_many' }, 429);
      const now = this.now();
      this.q("INSERT INTO article_jobs (topic_id, kind, title, note, status, created, updated, by) VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)", topic, kind, title, note, now, now, String(v.user.uid || ''));
      const id = this.q('SELECT last_insert_rowid() AS id')[0].id;
      return this.json(req, { ok: true, job: jobOf(this, id) });
    },
    '/v1/articles/jobs/list': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      return this.json(req, { jobs: this.q('SELECT id, topic_id, kind, title, note, status, created, updated, result FROM article_jobs ORDER BY id DESC LIMIT 200') });
    },
    '/v1/articles/jobs/cancel': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      const id = Number(b.id), j = Number.isInteger(id) ? jobOf(this, id) : null;
      if (!j) return this.json(req, { error: 'not_found' }, 404);
      if (j.status !== 'queued') return this.json(req, { error: 'not_queued', job: j }, 409);
      this.q("UPDATE article_jobs SET status = 'cancelled', updated = ? WHERE id = ?", this.now(), id);
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
  const origFetch = Hub.prototype.fetch;
  Hub.prototype.fetch = async function (req) {
    if (req.method !== 'POST' || new URL(req.url).pathname !== '/v1/articles/jobs/bot') return origFetch.call(this, req);
    try {
      /* 鑰匙：ARTICLE_BOT_KEY（deploy-account-worker.yml 由 CLOUDFLARE_API_TOKEN 推導後寫入；article-jobs.yml 用同一個公式算）或 BACKUP_TOKEN */
      const h = String(req.headers.get('Authorization') || ''), got = h.startsWith('Bearer ') ? h.slice(7).trim() : '';
      const keys = [this.env.ARTICLE_BOT_KEY, this.env.BACKUP_TOKEN].map((k) => String(k || '')).filter((k) => k.length >= 16);
      if (!got || !keys.some((k) => eqConst(got, k))) return this.json(req, { error: 'forbidden' }, 403);
      const raw = await req.text(); if (raw.length > 4096) return this.json(req, { error: 'too_large' }, 413);
      let b = {}; try { b = JSON.parse(raw || '{}') || {}; } catch (e) { return this.json(req, { error: 'bad_json' }, 400); }
      this.artInit();
      if (b.op === 'open') return this.json(req, { jobs: this.q(OPEN_SQL) });
      if (b.op === 'schedule') return this.json(req, { schedule: latestSchedule(this) });   // 頻率設定（只讀）
      if (b.op === 'mark') {
        const id = Number(b.id), st = String(b.status || ''), j = Number.isInteger(id) ? jobOf(this, id) : null;
        if (!j) return this.json(req, { error: 'not_found' }, 404);
        if (!MARKS.includes(st)) return this.json(req, { error: 'bad_status' }, 400);
        if (j.status === 'cancelled' || j.status === 'done') return this.json(req, { error: 'closed', job: j }, 409);
        this.q('UPDATE article_jobs SET status = ?, result = ?, updated = ? WHERE id = ?', st, clip(b.result, 200) || j.result || null, this.now(), id);
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
