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
}
