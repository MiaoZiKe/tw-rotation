/* ============================================================================ 精選文章點閱次數（2026-10-16）
   Andy 10-16：「需要新增點閱次數」。
   · POST /v1/articles/view  {id}  → {ok, id, views}   不用登入；同一個 IP 同一篇 30 分鐘內只算一次（記憶體去重）；每 IP 每小時最多 120 次
   · POST /v1/articles/stats {}    → {views:{id:N}}     列表頁一次拿全部
   · 文章 id 只收英數、點、底線、減號（最長 80）；資料表最多 3000 列，避免被灌垃圾 id
   ============================================================================ */
export function installArticles(Hub, EXPORT_TABLES) {
  if (EXPORT_TABLES && !EXPORT_TABLES.includes('article_views')) EXPORT_TABLES.push('article_views');   // 備份一起帶走
  const ID_RE = /^[A-Za-z0-9._-]{4,80}$/;
  const DEDUP_MS = 30 * 60 * 1000, IP_HOUR_MAX = 120, MAX_ROWS = 3000;
  /* 備份匯出前要先有表（見 pay.js 的 expInit 做法）*/
  const origExpInit = Hub.prototype.expInit;
  Hub.prototype.expInit = function () { if (origExpInit) origExpInit.call(this); this.artInit(); };
  Hub.prototype.artInit = function () {
    if (this._artOk) return;
    this.q('CREATE TABLE IF NOT EXISTS article_views (id TEXT PRIMARY KEY, views INTEGER DEFAULT 0, updated INTEGER)');
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
          this._artSeen.set(k, now);
          if (this._artSeen.size > 20000) this._artSeen.clear();
          if (!r || r[0] !== hr) this._artIp.set(ip, [hr, 1]); else r[1]++;
          if (this._artIp.size > 5000) this._artIp.clear();
        }
      }
      return this.json(req, { ok: true, id, views: views(this, id) });
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
