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
     「產精選文章頻率」設定（2026-10-16）
     Andy 10-16：「我需要可以產貼文頻率設定……每週幾、哪個時段幫我產出精選貼文」。
     做法照產出佇列：管理區按「儲存」→ 這裡存一份（只留最新一份有效，舊的留作紀錄）→ article-jobs.yml 每小時把最新一份同步進
     repo（data/_state/article_schedule.json）→ Claude 排程（台北 09:50／14:50／20:50）醒來時讀它，
     「今天星期幾、這一輪是哪個時段」對得上就自己依類別與篇數排進佇列（不需要 Andy 再按）。
     · 管理者路由：/v1/articles/schedule/get {t} → {schedule|null, allowed}；/v1/articles/schedule/add {t, enabled, slots, cats} → {ok, schedule}
     · 機器路由：/v1/articles/jobs/bot {op:'schedule'} → {schedule|null}
     · 時段只收現有排程的三輪（SCH_TIMES）；日後要增加就改這個清單與 Claude 排程時間，前端會讀 allowed 自動多出選項。
     · 設定內容：enabled（總開關）、slots（{"1":["09:50","20:50"],…} 星期 1＝週一…7＝週日）、cats（{news,intro,know} 各 0～3 篇）。
     ========================================================================== */
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_schedule')) EXPORT_TABLES.push('article_schedule');
  const SCH_TIMES = ['09:50', '14:50', '20:50'], SCH_CATS = ['news', 'intro', 'know'], SCH_MAX = 3, SCH_KEEP = 50;
  const origArtInit2 = Hub.prototype.artInit;
  Hub.prototype.artInit = function () {
    origArtInit2.call(this);
    if (this._artSchOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, cfg TEXT, created INTEGER, by TEXT)');
    this._artSchOk = true;
  };
  /* 驗證並整理成固定形狀；壞輸入回 null（不猜、不補） */
  function cleanSchedule(b) {
    if (!b || typeof b !== 'object' || typeof b.enabled !== 'boolean') return null;
    const slots = {}, cats = {};
    const sl = b.slots && typeof b.slots === 'object' && !Array.isArray(b.slots) ? b.slots : null, ct = b.cats && typeof b.cats === 'object' && !Array.isArray(b.cats) ? b.cats : null;
    if (!sl || !ct) return null;
    for (const [d, ts] of Object.entries(sl)) {
      if (!/^[1-7]$/.test(d) || !Array.isArray(ts)) return null;
      const u = [...new Set(ts.map(String))];
      if (u.some((x) => !SCH_TIMES.includes(x))) return null;
      if (u.length) slots[d] = SCH_TIMES.filter((x) => u.includes(x));
    }
    for (const k of Object.keys(ct)) if (!SCH_CATS.includes(k)) return null;
    for (const k of SCH_CATS) {
      const n = ct[k] == null ? 0 : ct[k];
      if (!Number.isInteger(n) || n < 0 || n > SCH_MAX) return null;
      cats[k] = n;
    }
    if (b.enabled && (!Object.keys(slots).length || !SCH_CATS.some((k) => cats[k] > 0))) return null;   // 開著卻沒有時段或沒有類別 ＝ 不會做任何事，擋下
    return { enabled: b.enabled, slots, cats };
  }
  const latestSchedule = (hub) => {
    const r = hub.q('SELECT cfg, created FROM article_schedule ORDER BY id DESC LIMIT 1')[0];
    if (!r) return null;
    try { return { ...JSON.parse(r.cfg), updated: r.created }; } catch (e) { return null; }
  };
  Object.assign(Hub.prototype.subRoutes, {
    '/v1/articles/schedule/get': async function (req, b) {
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.artInit();
      return this.json(req, { schedule: latestSchedule(this), allowed: { times: SCH_TIMES, cats: SCH_CATS, max: SCH_MAX } });
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
      return this.json(req, { error: 'bad_op' }, 400);
    } catch (e) { return this.json(req, { error: 'server' }, 500); }
  };
}
