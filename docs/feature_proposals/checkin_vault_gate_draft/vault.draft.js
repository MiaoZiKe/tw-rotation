/* ============================================================================ 比比寶箱「硬閘門」（草稿，2026-11-07，沒接上任何東西）
   設計：docs/feature_proposals/checkin_vault_gate.md
   用法（站主點頭後）：複製成 workers/account-api/vault.js，在 worker.js 的 installArticles(Hub, EXPORT_TABLES) 旁邊加
       import { installVault } from './vault.js';   installVault(Hub, EXPORT_TABLES);
   風格跟 articles.js 一樣：Object.assign(Hub.prototype.subRoutes, {...})；this.auth(req,b) 驗 token、this.q() 查 SQLite、this.json() 回應。
   ★ 原則：日期由伺服器算（台北）；解鎖只看 ci_unlock；不看方案、不看站主身分（法遵）；全文只存在 vault_posts。
   ============================================================================ */
export function installVault(Hub, EXPORT_TABLES) {
  for (const t of ['ci_signs', 'ci_claims', 'ci_unlock', 'ci_points', 'ci_ptlog', 'vault_posts']) if (EXPORT_TABLES && !EXPORT_TABLES.includes(t)) EXPORT_TABLES.push(t);
  const CFG_KV = 'vault_manifest';             // 站主上傳的 manifest（packs／nodes／補簽設定），Worker 自己不抄一份，前端改設定不必重新部署
  const ID_RE = /^[A-Za-z0-9._-]{4,80}$/, DAY_RE = /^\d{4}-\d{2}-\d{2}$/;
  const DAY_CAP = 4, GAP_MS = 20000, CLICK_MS = 3000;

  const origExpInit = Hub.prototype.expInit;
  Hub.prototype.expInit = function () { if (origExpInit) origExpInit.call(this); this.vaultInit(); };
  Hub.prototype.vaultInit = function () {
    if (this._vOk) return;
    this.q('CREATE TABLE IF NOT EXISTS ci_signs (uid TEXT, day TEXT, kind TEXT, at INTEGER, PRIMARY KEY (uid, day))');
    this.q('CREATE TABLE IF NOT EXISTS ci_claims (uid TEXT, ym TEXT, idx INTEGER, at INTEGER, packs TEXT, PRIMARY KEY (uid, ym, idx))');
    this.q('CREATE TABLE IF NOT EXISTS ci_unlock (uid TEXT, article TEXT, pack TEXT, ym TEXT, at INTEGER, PRIMARY KEY (uid, article))');
    this.q('CREATE TABLE IF NOT EXISTS ci_points (uid TEXT, ym TEXT, pts INTEGER DEFAULT 0, used INTEGER DEFAULT 0, PRIMARY KEY (uid, ym))');
    this.q('CREATE TABLE IF NOT EXISTS ci_ptlog (uid TEXT, day TEXT, n INTEGER DEFAULT 0, last INTEGER DEFAULT 0, PRIMARY KEY (uid, day))');
    this.q('CREATE TABLE IF NOT EXISTS vault_posts (id TEXT PRIMARY KEY, body TEXT, updated INTEGER)');
    this._vOk = true;
  };

  const tpeDay = (ms) => new Date(ms + 8 * 3600e3).toISOString().slice(0, 10);   // 台北日期，一律用伺服器時間
  const addDays = (d, n) => new Date(Date.parse(d + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
  const manifest = (hub) => { try { return JSON.parse(hub.kv(CFG_KV) || 'null') || { packs: [], config: {} }; } catch (e) { return { packs: [], config: {} }; } };
  const cfg = (m) => Object.assign({ nodes: [3, 7, 14, 20], makeup_cost: [5, 7, 10], makeup_max: 3, makeup_days: 7, teach_rotation: ['tech', 'chip', 'macro'] }, m.config || {});
  const uidOf = (v) => String(v.user.uid);
  const signsOf = (hub, uid, ym) => hub.q('SELECT day, kind FROM ci_signs WHERE uid = ? AND day LIKE ? ORDER BY day', uid, ym + '-%');

  /* 下一包：規則跟預覽版 checkin.js nextPack 一樣 —— 教學節點（idx 0、1）照 技術→籌碼→總經 輪流，產業節點取產業線下一包；已解鎖過的篇不再給 */
  function pickPack(hub, uid, idx, m, c) {
    const unlocked = new Set(hub.q('SELECT article FROM ci_unlock WHERE uid = ?', uid).map((r) => r.article));
    const lines = idx <= 1 ? c.teach_rotation : ['ind'];
    const prior = hub.q('SELECT COUNT(*) AS n FROM ci_claims WHERE uid = ? AND idx <= 1 AND packs != ?', uid, '[]')[0].n;
    for (let r = 0; r < lines.length; r++) {
      const ln = lines[(prior + r) % lines.length];
      const p = (m.packs || []).filter((x) => x.line === ln && x.articles.every((a) => !unlocked.has(a))).sort((a, b) => a.order - b.order)[0];
      if (p) return p;
    }
    return null;
  }

  Object.assign(Hub.prototype.subRoutes, {
    '/v1/vault/state': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const uid = uidOf(v), today = tpeDay(this.now()), ym = today.slice(0, 7);
      return this.json(req, {
        today, signs: signsOf(this, uid, ym),
        claims: this.q('SELECT idx, at, packs FROM ci_claims WHERE uid = ? AND ym = ?', uid, ym),
        unlock: this.q('SELECT article, pack, ym FROM ci_unlock WHERE uid = ?', uid),
        points: this.q('SELECT pts, used FROM ci_points WHERE uid = ? AND ym = ?', uid, ym)[0] || { pts: 0, used: 0 },
      });
    },

    '/v1/vault/sign': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const uid = uidOf(v), day = tpeDay(this.now());          // ★ 不讀 b.day：用戶端說的日期一律不認
      if (this.q('SELECT 1 FROM ci_signs WHERE uid = ? AND day = ?', uid, day).length) return this.json(req, { ok: false, error: 'already' });
      this.q("INSERT INTO ci_signs (uid, day, kind, at) VALUES (?, ?, 'live', ?)", uid, day, this.now());
      return this.json(req, { ok: true, day, total: signsOf(this, uid, day.slice(0, 7)).length });
    },

    '/v1/vault/makeup': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const m = manifest(this), c = cfg(m), uid = uidOf(v), today = tpeDay(this.now()), ym = today.slice(0, 7), day = String(b.day || '');
      if (!DAY_RE.test(day) || day >= today || day.slice(0, 7) !== ym || day < addDays(today, -c.makeup_days)) return this.json(req, { ok: false, error: 'range' });
      if (this.q('SELECT 1 FROM ci_signs WHERE uid = ? AND day = ?', uid, day).length) return this.json(req, { ok: false, error: 'already' });
      const pt = this.q('SELECT pts, used FROM ci_points WHERE uid = ? AND ym = ?', uid, ym)[0] || { pts: 0, used: 0 };
      const cost = c.makeup_cost[Math.min(pt.used, c.makeup_cost.length - 1)];
      /* 功能鍵 ci.makeup 的每月上限由 TwPerm 管，這裡只擋規格上限；之後接 this.permValue(...) 時改這一行 */
      if (pt.used >= c.makeup_max || pt.pts < cost) return this.json(req, { ok: false, error: 'notready' });
      this.q('INSERT INTO ci_points (uid, ym, pts, used) VALUES (?, ?, ?, ?) ON CONFLICT(uid, ym) DO UPDATE SET pts = excluded.pts, used = excluded.used', uid, ym, pt.pts - cost, pt.used + 1);
      this.q("INSERT INTO ci_signs (uid, day, kind, at) VALUES (?, ?, 'makeup', ?)", uid, day, this.now());
      return this.json(req, { ok: true, day });
    },

    '/v1/vault/point': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const m = manifest(this), c = cfg(m), uid = uidOf(v), now = this.now(), today = tpeDay(now), ym = today.slice(0, 7);
      const lg = this.q('SELECT n, last FROM ci_ptlog WHERE uid = ? AND day = ?', uid, today)[0] || { n: 0, last: 0 };
      const pt = this.q('SELECT pts, used FROM ci_points WHERE uid = ? AND ym = ?', uid, ym)[0] || { pts: 0, used: 0 };
      const why = now - lg.last < CLICK_MS ? 'fast' : pt.used >= c.makeup_max ? 'max' : lg.n >= DAY_CAP ? 'day' : now - lg.last < GAP_MS ? 'gap' : '';
      this.q('INSERT INTO ci_ptlog (uid, day, n, last) VALUES (?, ?, ?, ?) ON CONFLICT(uid, day) DO UPDATE SET last = excluded.last' + (why ? '' : ', n = n + 1'), uid, today, why ? 0 : 1, now);
      if (why) return this.json(req, { counted: false, why });
      this.q('INSERT INTO ci_points (uid, ym, pts, used) VALUES (?, ?, 1, ?) ON CONFLICT(uid, ym) DO UPDATE SET pts = pts + 1', uid, ym, pt.used);
      return this.json(req, { counted: true, pts: pt.pts + 1 });
    },

    '/v1/vault/claim': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const m = manifest(this), c = cfg(m), uid = uidOf(v), now = this.now(), ym = tpeDay(now).slice(0, 7), idx = Number(b.idx);
      if (!Number.isInteger(idx) || idx < 0 || idx >= c.nodes.length) return this.json(req, { ok: false, error: 'bad_input' }, 400);
      if (signsOf(this, uid, ym).length < c.nodes[idx]) return this.json(req, { ok: false, error: 'short' });
      if (this.q('SELECT 1 FROM ci_claims WHERE uid = ? AND ym = ? AND idx = ?', uid, ym, idx).length) return this.json(req, { ok: false, error: 'claimed' });
      if (idx === c.nodes.length - 1) {   // 最後一個節點是許願券：不解鎖文章，只記領過（許願本身仍走 /v1/feedback）
        this.q("INSERT INTO ci_claims (uid, ym, idx, at, packs) VALUES (?, ?, ?, ?, '[]')", uid, ym, idx, now);
        return this.json(req, { ok: true, idx, articles: [] });
      }
      const p = pickPack(this, uid, idx, m, c);
      if (!p) return this.json(req, { ok: false, error: 'soldout' });
      this.q('INSERT INTO ci_claims (uid, ym, idx, at, packs) VALUES (?, ?, ?, ?, ?)', uid, ym, idx, now, JSON.stringify([p.id]));
      for (const a of p.articles) this.q('INSERT OR IGNORE INTO ci_unlock (uid, article, pack, ym, at) VALUES (?, ?, ?, ?, ?)', uid, a, p.id, ym, now);
      return this.json(req, { ok: true, idx, articles: p.articles });
    },

    /* ★ 硬閘門：只有 ci_unlock 有這個人這篇才回全文。不看方案、不看站主身分（站主要讀就自己簽到兌換，或用 admin/grant）。 */
    '/v1/vault/post': async function (req, b) {
      const v = await this.auth(req, b); if (!v) return this.json(req, { error: 'auth' }, 401);
      this.vaultInit();
      const id = String(b.id || '');
      if (!ID_RE.test(id)) return this.json(req, { error: 'bad_input' }, 400);
      if (!this.q('SELECT 1 FROM ci_unlock WHERE uid = ? AND article = ?', uidOf(v), id).length) return this.json(req, { error: 'locked' }, 403);
      const r = this.q('SELECT body FROM vault_posts WHERE id = ?', id)[0];
      if (!r) return this.json(req, { error: 'not_found' }, 404);
      let post = null; try { post = JSON.parse(r.body); } catch (e) { /* 壞檔 */ }
      return this.json(req, { post });   
    },

    /* ---- 管理者 ---- */
    '/v1/vault/admin/put': async function (req, b) {   // 上傳全文或 manifest：{id, body} 或 {manifest}
      if (!(await this.admin(req, b))) return this.json(req, { error: 'forbidden' }, 403);
      this.vaultInit();
      if (b.manifest) { this.setKv(CFG_KV, JSON.stringify(b.manifest)); return this.json(req, { ok: true }); }
      const id = String(b.id || '');
      if (!ID_RE.test(id) || typeof b.body !== 'object' || JSON.stringify(b.body).length > 200000) return this.json(req, { error: 'bad_input' }, 400);
      this.q('INSERT INTO vault_posts (id, body, updated) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET body = excluded.body, updated = excluded.updated', id, JSON.stringify(b.body), this.now());
      return this.json(req, { ok: true, id });
    },
    '/v1/vault/admin/grant': async function (req, b) {   // 替某帳號補一筆簽到（取代預覽版的站主測試工具）；只能補今天以前
      const a = await this.admin(req, b); if (!a) return this.json(req, { error: 'forbidden' }, 403);
      this.vaultInit();
      const email = String(b.email || '').toLowerCase(), day = String(b.day || ''), today = tpeDay(this.now());
      const u = this.q('SELECT uid FROM users WHERE lower(email) = ?', email)[0];
      if (!u || !DAY_RE.test(day) || day > today) return this.json(req, { error: 'bad_input' }, 400);
      this.q("INSERT OR IGNORE INTO ci_signs (uid, day, kind, at) VALUES (?, ?, 'grant', ?)", String(u.uid), day, this.now());
      return this.json(req, { ok: true });
    },
  });
}
