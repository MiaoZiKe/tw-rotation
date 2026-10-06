/* ============================================================================
   自選清單：最多五個分頁（Andy 2026-09-27：「新增自選清單並且可以新增五個分頁」）

   · 每一頁＝一個名字＋一串股票代號。**只存代號與清單名，不存張數、成本、損益**（CLAUDE.md 第 5 條的精神：
     那些東西不該離開使用者的裝置，而且這個功能也用不到）。
   · 沒登入：存在這台裝置的 localStorage `tw.watchlists`。
   · 登入後：以雲端為準（site/account.js 登入成功會發 `tw:account`），本機只留一份快取 `tw.watchlists.u` 讓畫面先出來。
     第一次登入時，本機清單**合併**上雲（mergeLists）——同名的頁取聯集、不同名的頁接在後面、滿五頁就併進同位置那一頁，
     **不會覆蓋雲端原有的東西**。合併成功後清空本機那份（它已經在雲端了），登出時換回空的本機清單 ——
     共用電腦登出之後，下一個人看不到你的清單。
   · 舊的單一清單 `tw.watch`（手機總覽的觀察清單，2026-09-27 上線）第一次載入時自動搬進第 1 頁，搬完刪掉舊鍵。

   對外：window.TwWatch（手機 mobile3.js、個股頁 ☆、帳號選單都走這一組），變動時發 `tw:watch` 事件。
   為什麼是新檔：同時有兩位 agent 在改 index.html 的 CSS 與 mobile3.js；CSS 由本檔自己注入，撞檔面積最小。
   驗收：scripts/_uitest.py「會員與自選五分頁」。
   ========================================================================== */
(function () {
  'use strict';
  const K = 'tw.watchlists', K_OLD = 'tw.watch', K_CUR = 'tw.watchcur', K_CLOUD = 'tw.watchlists.u';
  /* 2026-10-07：分頁數／每頁檔數改成跟方案走（features.js 的 watch.tabs／watch.size；免費 1 頁 10 檔、Plus 5／50、Pro 不限）。
     HARD_*＝「不限」的硬上限（跟 Worker 的 watch-v2 區塊同一組數）：清洗與合併只守硬上限，方案上限只擋「新增」。
     LEGACY_*＝連不到會員伺服器時的舊值（5 頁／50 檔）：權限拿不到就照以前，不誤鎖。*/
  const HARD_TABS = 50, HARD_CODES = 200, LEGACY_TABS = 5, LEGACY_CODES = 50, MAX_NAME = 12;
  const MAX_TABS = HARD_TABS, MAX_CODES = HARD_CODES;
  const CODE_RE = /^[0-9A-Z]{4,6}$/;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const cleanName = (s) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f<>]/g, '').trim().slice(0, MAX_NAME);
  const newId = () => Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-3);
  const track = (e) => { try { if (window.TwTrack) window.TwTrack(e); } catch (x) { /* 統計失敗不影響功能 */ } };
  const isM = () => window.matchMedia('(max-width: 820px)').matches;

  function readJSON(k) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  function writeJSON(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  /* 清洗：跟 Worker 的 cleanLists 同一套規則（最多 5 頁、名字 12 字、每頁 50 檔、代號格式、頁 id 不重複）。
     壞掉的資料（手動改過 localStorage、舊版格式）清得掉就清，清不掉的那一項丟掉，不讓整份清單讀不出來。*/
  function sanitize(tabs) {
    const out = [], ids = new Set();
    (Array.isArray(tabs) ? tabs : []).forEach((t) => {
      if (!t || typeof t !== 'object' || out.length >= MAX_TABS) return;
      let id = /^[a-z0-9]{1,12}$/.test(t.id) ? t.id : newId();
      while (ids.has(id)) id = newId();
      ids.add(id);
      const codes = [];
      (Array.isArray(t.codes) ? t.codes : []).forEach((c) => { c = String(c).toUpperCase(); if (CODE_RE.test(c) && !codes.includes(c) && codes.length < MAX_CODES) codes.push(c); });
      out.push({ id, name: cleanName(t.name) || ('自選 ' + (out.length + 1)), codes });
    });
    return out;
  }
  const blank = () => [{ id: newId(), name: '自選 1', codes: [] }];

  /* 本機（訪客）那一份。第一次載入時把舊的 tw.watch 搬進第 1 頁。*/
  function loadLocal() {
    const o = readJSON(K);
    let tabs = sanitize(o && o.tabs);
    if (!tabs.length) {
      let old = [];
      try { const v = JSON.parse(localStorage.getItem(K_OLD) || '[]'); if (Array.isArray(v)) old = v; } catch (e) { /* 舊鍵壞掉就當沒有 */ }
      tabs = blank();
      tabs[0].codes = sanitize([{ id: 'x', name: 'x', codes: old }])[0].codes;
      if (writeJSON(K, { v: 1, tabs }) && old.length) { try { localStorage.removeItem(K_OLD); } catch (e) { /* 略 */ } }
    }
    return tabs;
  }

  /* 本機併進雲端：不覆蓋雲端。規則見檔頭。空的本機頁（預設那個「自選 1」沒放東西）不帶上去，免得雲端多一頁空白。*/
  function mergeLists(cloud, local) {
    const out = sanitize(cloud).map((t) => ({ ...t, codes: t.codes.slice() }));
    sanitize(local).forEach((lt, i) => {
      if (!lt.codes.length) return;
      let dst = out.find((t) => t.name === lt.name);
      if (!dst && out.length < Math.max(1, capTabs())) { dst = { id: out.some((t) => t.id === lt.id) ? newId() : lt.id, name: lt.name, codes: [] }; out.push(dst); }
      if (!dst) dst = out[Math.min(i, out.length - 1)];
      /* 合併也照方案上限（Worker 會擋「超過上限還變多」的清單）；雲端那頁本來就超過的不刪，只是不再往裡加 */
      const room = Math.max(dst.codes.length, capCodes());
      lt.codes.forEach((c) => { if (!dst.codes.includes(c) && dst.codes.length < room) dst.codes.push(c); });
    });
    return out;
  }

  const S = { tabs: loadLocal(), mode: 'local', rev: 0, pushT: 0, dirty: false, msg: '' };
  S.cur = (() => { try { return localStorage.getItem(K_CUR) || ''; } catch (e) { return ''; } })();
  const acct = () => (window.TwAccount && window.TwAccount.user && window.TwAccount.user()) ? window.TwAccount : null;
  /* 已登入（上一次瀏覽留下的）：先用雲端快取畫，TwAccount 驗完權杖會發 tw:account 再跟雲端對一次 */
  (function bootCloud() {
    const c = readJSON(K_CLOUD);
    let tok = null; try { tok = localStorage.getItem('tw.acct.tok'); } catch (e) { /* 略 */ }
    if (tok && c && Array.isArray(c.tabs) && c.tabs.length) { S.mode = 'cloud'; S.tabs = sanitize(c.tabs); S.rev = c.rev || 0; S.dirty = !!c.dirty; }
  })();

  function curTab() { return S.tabs.find((t) => t.id === S.cur) || S.tabs[0]; }
  function emit() { window.dispatchEvent(new Event('tw:watch')); }
  function saveCloudCache() { writeJSON(K_CLOUD, { tabs: S.tabs, rev: S.rev, dirty: S.dirty }); }
  function commit() {
    if (!S.tabs.length) S.tabs = blank();
    if (S.mode === 'cloud') { S.dirty = true; saveCloudCache(); schedulePush(); } else writeJSON(K, { v: 1, tabs: S.tabs });
    paintAll(); emit();
  }

  // ------------------------------------------------------------------ 雲端同步
  function schedulePush() { clearTimeout(S.pushT); S.pushT = setTimeout(push, 600); }
  async function push() {
    const A = acct(); if (!A || S.mode !== 'cloud' || !S.dirty) return;
    const r = await A.call('/v1/lists/put', { lists: S.tabs, rev: S.rev });
    if (r && r.ok) { S.rev = r.rev; S.dirty = false; saveCloudCache(); setMsg(''); return; }
    if (r && r.error === 'watch_limit') {
      /* Worker 依方案擋下（分頁或檔數超過上限而且比雲端那份還多）：換回雲端那份，跳出升級卡 */
      if (Array.isArray(r.lists)) { S.tabs = sanitize(r.lists); if (!S.tabs.length) S.tabs = blank(); S.rev = r.rev; }
      S.dirty = false; saveCloudCache(); paintAll(); emit(); upsell(r.kind === 'tabs' ? 'tabs' : 'size'); return;
    }
    if (r && r.conflict) {
      /* 另一台裝置先改過：以雲端為準（不硬蓋），告訴使用者。真的同時在兩台改同一份的機會很小，不值得做逐項合併。*/
      S.tabs = sanitize(r.lists); if (!S.tabs.length) S.tabs = blank();
      S.rev = r.rev; S.dirty = false; saveCloudCache(); setMsg('雲端有另一台裝置剛改過，已換成最新的版本'); paintAll(); emit(); return;
    }
    setMsg('暫時連不到雲端，改動先存在這台裝置，下次連上會自動補傳');
  }
  async function onLogin() {
    const A = acct(); if (!A) return;
    const r = await A.call('/v1/lists/get', {});
    if (!r || !Array.isArray(r.lists)) { if (S.mode !== 'cloud') { S.mode = 'cloud'; S.tabs = blank(); } setMsg('暫時連不到雲端'); paintAll(); emit(); return; }
    const guest = loadLocal();
    const hasGuest = guest.some((t) => t.codes.length);
    let tabs = sanitize(r.lists), rev = r.rev;
    /* 上次離線時改過、還沒傳上去的雲端快取：以它為準再傳一次（版本號不對就會被 409 擋下、換成雲端的）*/
    if (S.mode === 'cloud' && S.dirty && S.rev === rev) tabs = S.tabs;
    if (hasGuest) tabs = mergeLists(tabs, guest);
    if (!tabs.length) tabs = blank();
    S.mode = 'cloud'; S.tabs = tabs; S.rev = rev;
    if (hasGuest || S.dirty || !r.lists.length) {
      const p = await A.call('/v1/lists/put', { lists: S.tabs, rev: S.rev });
      if (p && p.ok) {
        S.rev = p.rev; S.dirty = false;
        if (hasGuest) { writeJSON(K, { v: 1, tabs: blank() }); setMsg('這台裝置原本的清單已經合併到你的帳號'); }
      } else if (p && (p.conflict || p.error === 'watch_limit') && Array.isArray(p.lists)) { S.tabs = sanitize(p.lists); if (!S.tabs.length) S.tabs = blank(); S.rev = p.rev; S.dirty = false; }
      else S.dirty = true;
    }
    saveCloudCache(); paintAll(); emit();
  }
  function onLogout() {
    try { localStorage.removeItem(K_CLOUD); } catch (e) { /* 略 */ }
    S.mode = 'local'; S.rev = 0; S.dirty = false; S.tabs = loadLocal(); setMsg(''); paintAll(); emit();
  }
  window.addEventListener('tw:account', (e) => { if (e.detail && e.detail.user) onLogin(); else onLogout(); });
  /* 同一個瀏覽器的另一個分頁改了清單，這裡跟著換 */
  window.addEventListener('storage', (e) => {
    if (e.key === K && S.mode === 'local') { S.tabs = loadLocal(); paintAll(); emit(); }
    if (e.key === K_CLOUD && S.mode === 'cloud') { const c = readJSON(K_CLOUD); if (c) { S.tabs = sanitize(c.tabs); S.rev = c.rev || 0; S.dirty = !!c.dirty; paintAll(); emit(); } }
  });
  function setMsg(m) {
    S.msg = m; const e = document.getElementById('wlMsg'); if (e) { e.textContent = m; e.hidden = !m; }
    // 2026-09-28：自選分頁（site/watchpage.js）也要顯示同一句提示
    try { window.dispatchEvent(new CustomEvent('tw:watchmsg', { detail: { msg: m } })); } catch (x) { /* 略 */ }
  }

  // ------------------------------------------------------------------ 操作
  /* ★ 2026-10-02 會員功能權限（DECISIONS #288）：「自選分頁數上限」由管理者依方案設定（預設 5＝跟以前一樣）。
     只擋「新增」，已經建好的頁不刪 —— 降級的人清單不會不見。對外的 MAX_TABS 改成 getter，watchpage.js 的「N／上限 頁」跟著走。*/
  const permOn = () => { const P = window.TwPerm; return !!P && P.state().src !== 'default'; };
  const capTabs = () => { const P = window.TwPerm; if (!permOn()) return LEGACY_TABS; return Math.max(0, Math.min(HARD_TABS, P.limit('watch.tabs', LEGACY_TABS))); };
  const capCodes = () => { const P = window.TwPerm; if (!permOn()) return LEGACY_CODES; return Math.max(0, Math.min(HARD_CODES, P.limit('watch.size', LEGACY_CODES))); };
  /* 超過方案上限：跳出跟「每日額度／需開通」同一款卡片（site/qcard.js 的 modal），按鈕連到訂閱頁的下一個方案。
     方案資料（每個方案幾頁、每頁幾檔）讀訂閱頁那一份；讀不到用 Plus 5／50、Pro 不限 */
  function upsell(kind) {
    const QC = window.TwQCard, TP = window.TwPricing;
    const n = kind === 'tabs' ? capTabs() : capCodes();
    if (!QC || !QC.modal) { setMsg(kind === 'tabs' ? `🔒 目前方案最多 ${n} 頁自選清單，要更多頁需升級方案` : `🔒 目前方案每頁最多 ${n} 檔，要放更多需升級方案`); return; }
    const F = window.TwFeatures, ft = F && F.byId('watch.tabs'), fs = F && F.byId('watch.size');
    const lim = (p, f, d) => { const v = p && p.feats ? p.feats[f.id] : undefined; return Number.isInteger(v) ? v : d; };
    let rows = (TP && TP.plans && TP.plans() || []).filter((p) => p.id !== 'guest' && p.id !== 'free')
      .map((p) => ({ id: p.id, name: p.name, t: ft ? lim(p, ft, ft.def) : 0, c: fs ? lim(p, fs, fs.def) : 0 }));
    if (!rows.some((r) => r.id === 'plus')) rows.push({ id: 'plus', name: 'Plus', t: 5, c: 50 });
    if (!rows.some((r) => r.id === 'pro')) rows.push({ id: 'pro', name: 'Pro', t: HARD_TABS, c: HARD_CODES });
    rows = rows.filter((r) => (kind === 'tabs' ? r.t > n : r.c > n));
    const txt = (v, max, u) => (v >= max ? '不限' + (u === '頁' ? '分頁' : '檔數') : `${v} ${u}`);
    const up = rows.find((r) => r.id === 'plus') || rows[0] || { id: 'pro', name: 'Pro' };
    QC.modal({ kind: 'lock', kick: '自選清單上限',
      title: kind === 'tabs' ? `目前方案最多 ${n} 頁自選清單` : `這一頁已經放滿 ${n} 檔`,
      sub: '已經建好的清單不會被刪，升級方案就能再新增。', lh: rows.length ? '升級可以放更多' : '',
      items: rows.slice(0, 4).map((r) => ({ t: r.name, s: `${txt(r.t, HARD_TABS, '頁')}・${r.c >= HARD_CODES ? '不限檔數' : `每頁 ${r.c} 檔`}` })),
      btn: `升級 ${up.name}`, href: '#pricing/plan/' + encodeURIComponent(up.id), btnCls: 'wlup' });
    if (TP && TP.ensure && !TP.plans()) TP.ensure();
  }
  const API = {
    get MAX_TABS() { return capTabs(); },
    get MAX_CODES() { return capCodes(); },
    /* 被「方案」擋（升級就能多）＝true；連不到會員伺服器時是舊的固定 5 頁，那不是方案擋的 */
    capLocked: () => permOn() && capTabs() < HARD_TABS,
    upsell,
    tabs: () => S.tabs.map((t) => ({ id: t.id, name: t.name, codes: t.codes.slice() })),
    cur: () => curTab().id,
    curTab: () => { const t = curTab(); return { id: t.id, name: t.name, codes: t.codes.slice() }; },
    mode: () => S.mode,
    setCur(id) { if (!S.tabs.some((t) => t.id === id)) return; S.cur = id; try { localStorage.setItem(K_CUR, id); } catch (e) { /* 略 */ } paintAll(); emit(); },
    codes: (id) => { const t = id ? S.tabs.find((x) => x.id === id) : curTab(); return t ? t.codes.slice() : []; },
    /* 手機總覽那一列用：整頁換掉（刪除、加入都走這支，跟舊的 tw.watch 介面一樣）*/
    setCodes(codes, id) {
      const t = id ? S.tabs.find((x) => x.id === id) : curTab(); if (!t) return;
      const before = t.codes.length;
      t.codes = sanitize([{ id: 'x', name: 'x', codes }])[0].codes;
      /* 方案的每頁檔數上限：只擋「變多」（原本就超過的不刪）*/
      const room = Math.max(before, capCodes());
      if (t.codes.length > room) { t.codes = t.codes.slice(0, room); upsell('size'); }
      if (t.codes.length > before) track('watch_add'); else if (t.codes.length < before) track('watch_remove');
      commit();
    },
    has: (c) => S.tabs.some((t) => t.codes.includes(String(c))),
    tabsWith: (c) => S.tabs.filter((t) => t.codes.includes(String(c))).map((t) => t.id),
    add(c, id) {
      c = String(c).toUpperCase(); const t = id ? S.tabs.find((x) => x.id === id) : curTab();
      if (!t || !CODE_RE.test(c) || t.codes.includes(c)) return false;
      if (t.codes.length >= capCodes()) { if (permOn() && capCodes() < HARD_CODES) upsell('size'); else setMsg(`「${t.name}」已經有 ${capCodes()} 檔，放不下了`); return false; }
      t.codes.unshift(c); track('watch_add'); commit(); return true;
    },
    remove(c, id) {
      const t = id ? S.tabs.find((x) => x.id === id) : curTab(); if (!t) return false;
      const i = t.codes.indexOf(String(c)); if (i < 0) return false;
      t.codes.splice(i, 1); track('watch_remove'); commit(); return true;
    },
    move(c, from, to) {
      const a = S.tabs.find((x) => x.id === from), b = S.tabs.find((x) => x.id === to);
      if (!a || !b || a === b || !a.codes.includes(c)) return false;
      if (!b.codes.includes(c) && b.codes.length >= capCodes()) { upsell('size'); return false; }
      a.codes = a.codes.filter((x) => x !== c); if (!b.codes.includes(c)) b.codes.unshift(c);
      commit(); return true;
    },
    newTab(name) {
      if (S.tabs.length >= capTabs()) { if (permOn() && capTabs() < HARD_TABS) upsell('tabs'); return null; }
      let n = cleanName(name);
      if (!n) { let i = S.tabs.length + 1; while (S.tabs.some((t) => t.name === '自選 ' + i)) i++; n = '自選 ' + i; }
      const t = { id: newId(), name: n, codes: [] };
      S.tabs.push(t); S.cur = t.id; try { localStorage.setItem(K_CUR, t.id); } catch (e) { /* 略 */ }
      track('watch_tab_new'); commit(); return t.id;
    },
    rename(id, name) { const t = S.tabs.find((x) => x.id === id), n = cleanName(name); if (!t || !n) return false; t.name = n; commit(); return true; },
    /* 刪掉最後一頁時留一頁空的「自選 1」—— 永遠至少有一頁，其他地方不必處理「沒有清單」的情況 */
    delTab(id) {
      const i = S.tabs.findIndex((x) => x.id === id); if (i < 0) return false;
      S.tabs.splice(i, 1); if (!S.tabs.length) S.tabs = blank();
      if (S.cur === id) S.cur = S.tabs[Math.max(0, i - 1)].id;
      commit(); return true;
    },
    /* 2026-09-28 自選分頁的拖曳排序：把 id 那一頁搬到第 to 個位置（只改順序，內容不動；雲端同步照 commit 那條路）*/
    moveTab(id, to) {
      const i = S.tabs.findIndex((x) => x.id === id); if (i < 0) return false;
      to = Math.max(0, Math.min(S.tabs.length - 1, to | 0)); if (to === i) return false;
      const [t] = S.tabs.splice(i, 1); S.tabs.splice(to, 0, t); commit(); return true;
    },
    merge: mergeLists,
    openPanel, closePanel, pick, closePick,
  };
  window.TwWatch = API;

  // ------------------------------------------------------------------ 樣式（本檔自己注入，見檔頭）
  function injectCSS() {
    if (document.getElementById('wlCss')) return;
    const s = document.createElement('style'); s.id = 'wlCss';
    s.textContent = `
.acctbar{display:flex;align-items:center;gap:6px;flex:none}
.acctbar .abtn{display:inline-flex;align-items:center;gap:5px;height:32px;padding:0 10px;border:1px solid var(--line-2);border-radius:9px;
  background:var(--panel-2);color:var(--ink);font-size:13px;cursor:pointer;white-space:nowrap}
.acctbar .abtn:hover{border-color:var(--cyan)}
.acctbar .abtn b{color:var(--amber);font-weight:700}
.wlpanel{position:fixed;top:60px;right:12px;width:380px;max-height:calc(100vh - 76px);z-index:1200;display:flex;flex-direction:column;
  background:var(--panel);border:1px solid var(--line-2);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.35);color:var(--ink);font-size:14px}
.wlpanel[hidden]{display:none}
.wlhd{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}
.wlhd b{font-size:15px}.wlhd .wlmode{font-size:12px;color:var(--ink-2);flex:1;min-width:0}
.wlx{border:0;background:none;color:var(--ink-2);font-size:18px;cursor:pointer;min-width:32px;min-height:32px}
.wltabs{display:flex;gap:4px;padding:8px 10px 0;overflow-x:auto;scrollbar-width:none}
.wltabs button{flex:none;height:32px;padding:0 10px;border:1px solid var(--line);border-bottom:0;border-radius:8px 8px 0 0;background:var(--panel-2);
  color:var(--ink-2);font-size:13px;cursor:pointer;max-width:9em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wltabs button.on{background:var(--panel-3);color:var(--ink);font-weight:700;border-color:var(--cyan)}
.wltabs button small{margin-left:4px;color:var(--ink-2);font-weight:400}
.wltabs .wlnew{color:var(--cyan)}
.wltabs input{height:30px;width:8em;font-size:13px;border:1px solid var(--cyan);border-radius:6px;background:var(--panel-2);color:var(--ink);padding:0 6px}
.wlact{display:flex;align-items:center;gap:6px;padding:8px 10px;border-top:1px solid var(--line);flex-wrap:wrap}
.wlact button{height:30px;padding:0 10px;border:1px solid var(--line-2);border-radius:7px;background:var(--panel-2);color:var(--ink);font-size:13px;cursor:pointer}
.wlact button.danger{color:#ff6b7a;border-color:rgba(255,107,122,.45)}
.wlact .wlconf{font-size:13px;color:var(--ink)}
.wladd{position:relative;padding:0 10px 8px}
.wladd input{width:100%;box-sizing:border-box;height:34px;font-size:14px;padding:0 10px;border:1px solid var(--line-2);border-radius:8px;background:var(--panel-2);color:var(--ink)}
.wlres{list-style:none;margin:4px 0 0;padding:0;max-height:220px;overflow:auto}
.wlres button{display:flex;gap:8px;align-items:center;width:100%;padding:7px 8px;border:0;border-bottom:1px solid var(--line);background:none;color:var(--ink);font-size:14px;cursor:pointer;text-align:left}
.wlres button:disabled{opacity:.55;cursor:default}.wlres em{margin-left:auto;font-style:normal;color:var(--cyan);font-size:13px}
.wlres .num{color:var(--ink-2)}
.wllist{list-style:none;margin:0;padding:0 4px;overflow:auto;flex:1;min-height:60px}
.wllist li{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;align-items:center;gap:8px;padding:8px;border-bottom:1px solid var(--line);cursor:pointer}
.wllist li:hover{background:var(--row-hover)}
.wllist .nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.wllist .nm small{margin-left:6px;color:var(--ink-2);font-size:12px}
.wllist .px{text-align:right;min-width:4.5em}.wllist .ch{text-align:right;min-width:4.5em}
.wllist select{height:28px;font-size:12px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:6px;max-width:6.5em}
.wllist .del{border:0;background:none;color:var(--ink-2);font-size:15px;cursor:pointer;min-width:28px;min-height:28px}
.wlempty{padding:18px 12px;color:var(--ink-2);font-size:13px;text-align:center}
.wlmsg{margin:6px 10px;padding:6px 8px;border-radius:6px;background:var(--panel-3);font-size:12.5px;color:var(--ink)}
.wlmsg[hidden]{display:none}
.wlfoot{padding:8px 12px 10px;font-size:12px;color:var(--ink-2);border-top:1px solid var(--line)}
.wlstar{margin-left:8px;border:1px solid var(--line-2);border-radius:8px;background:var(--panel-2);color:var(--ink-2);font-size:18px;line-height:1;
  width:34px;height:34px;cursor:pointer;vertical-align:middle}
.wlstar.on{color:var(--amber);border-color:var(--amber)}
.wlpick{position:fixed;z-index:1300;width:260px;background:var(--panel);border:1px solid var(--line-2);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.4);
  padding:8px;color:var(--ink);font-size:14px}
.wlpick[hidden]{display:none}
.wlpick .pkhd{display:flex;align-items:center;justify-content:space-between;padding:2px 4px 6px;font-weight:700}
.wlpick label{display:flex;align-items:center;gap:8px;padding:8px 6px;border-radius:8px;cursor:pointer}
.wlpick label:hover{background:var(--row-hover)}.wlpick label small{margin-left:auto;color:var(--ink-2);font-size:12px}
.wlpick input[type=checkbox]{width:18px;height:18px;accent-color:var(--amber)}
.wlpick .pknew{display:flex;gap:6px;padding:6px 4px 2px;border-top:1px solid var(--line);margin-top:4px}
.wlpick .pknew input{flex:1;min-width:0;height:32px;font-size:14px;border:1px solid var(--line-2);border-radius:7px;background:var(--panel-2);color:var(--ink);padding:0 8px}
.wlpick .pknew button{height:32px;padding:0 10px;border:1px solid var(--cyan);border-radius:7px;background:var(--panel-2);color:var(--cyan);font-size:13px;cursor:pointer}
.wlpick .pkfoot{font-size:12px;color:var(--ink-2);padding:6px 4px 0}
.morepop #mmWatch{border-top:1px solid var(--line);border-radius:0 0 9px 9px;margin-top:2px}
@media (max-width:640px){ .acctbar{display:none} }
@media (max-width:820px){
  .wlpanel{top:auto;bottom:0;left:0;right:0;width:auto;max-height:82vh;border-radius:14px 14px 0 0;font-size:15px}
  .wllist li{grid-template-columns:minmax(0,1fr) auto auto auto;padding:10px 6px}
  .wlpick{left:0!important;right:0;bottom:0;top:auto!important;width:auto;border-radius:14px 14px 0 0;padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
  .wlpick label{padding:11px 6px;font-size:15px}
}`;
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------------ 頂欄按鈕（account.js 會把登入鈕接在同一個容器裡）
  function ensureBar() {
    let bar = document.getElementById('acctBar');
    if (bar) return bar;
    const top = document.querySelector('.topbar'); if (!top) return null;
    bar = document.createElement('div'); bar.id = 'acctBar'; bar.className = 'acctbar';
    const ref = document.getElementById('evToggle');
    if (ref && ref.parentElement === top) top.insertBefore(bar, ref); else top.appendChild(bar);
    return bar;
  }
  window.TwAcctBar = ensureBar;
  /* 手機（≤640）頂欄放不下兩顆鈕（390px 量過：標題＋搜尋＋「⋯」就滿了），改成「⋯」清單裡的一列。
     收進清單是允許的，消失不行（index.html G1／G9 那條的同一個原則）。*/
  function moreRow(id, icon, text, onclick) {
    const pop = document.getElementById('morePop'); if (!pop) return null;
    let b = document.getElementById(id);
    if (!b) {
      b = document.createElement('button'); b.type = 'button'; b.id = id; b.className = 'mmacct';
      pop.appendChild(b);
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        pop.hidden = true; const mb = document.getElementById('moreBtn'); if (mb) mb.setAttribute('aria-expanded', 'false');
        if (b._on) b._on(e);
      });
    }
    b._on = onclick;
    b.innerHTML = '<span class="ic">' + icon + '</span>' + text;
    return b;
  }
  window.TwMoreRow = moreRow;
  function mountButton() {
    const bar = ensureBar(); if (!bar || document.getElementById('wlBtn')) return;
    const b = document.createElement('button');
    b.type = 'button'; b.id = 'wlBtn'; b.className = 'abtn'; b.setAttribute('aria-haspopup', 'dialog');
    /* ★ 2026-09-28（Andy：「自選是需要在獨立分頁 在最後一頁」）：自選有了整頁（#watch，site/watchpage.js），
       這顆與「⋯」清單那一列都改成**直接到自選分頁**，不再開小面板。
       為什麼不留小面板當快捷入口：同一份清單兩套編輯介面（面板一套、整頁一套），行為遲早會分岔，
       而且整頁已經在導覽列最後一格、一鍵就到。小面板的程式（openPanel）留著不刪，API 還在，只是站上不再有入口。*/
    b.title = '自選清單（最多五頁）'; b.innerHTML = '<b>★</b>自選'; b.removeAttribute('aria-haspopup');
    b.onclick = () => { closePanel(); location.hash = '#watch'; };
    bar.insertBefore(b, bar.firstChild);
    moreRow('mmWatch', '★', '自選清單', () => { location.hash = '#watch'; });
  }

  // ------------------------------------------------------------------ 清單面板
  const P = { editing: null, confirm: false, q: '' };
  let stocks = null;
  function loadStocks() {
    if (stocks) return Promise.resolve(stocks);
    const A = window.App;
    return (A && A.load ? A.load('stocks', { fallback: [] }) : Promise.resolve([])).then((l) => (stocks = (l || []).filter((r) => r && r.code)));
  }
  function openPanel() {
    injectCSS();
    let p = document.getElementById('wlPanel');
    if (!p) {
      p = document.createElement('div'); p.id = 'wlPanel'; p.className = 'wlpanel'; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', '自選清單');
      document.body.appendChild(p);
      p.addEventListener('click', onPanelClick);
      p.addEventListener('change', (e) => { const s = e.target.closest('select[data-mv]'); if (s && s.value) API.move(s.dataset.mv, curTab().id, s.value); });
      p.addEventListener('keydown', onPanelKey);
      p.addEventListener('input', (e) => { if (e.target.id === 'wlQ') { P.q = e.target.value; paintRes(); } });
    }
    P.confirm = false; P.editing = null;
    p.hidden = false; paintPanel(); track('watch_panel');
    loadStocks().then(() => { paintList(); paintRes(); });
    setTimeout(() => { const q = document.getElementById('wlQ'); if (q && !isM()) try { q.focus(); } catch (e) { /* 略 */ } }, 30);
  }
  function closePanel() { const p = document.getElementById('wlPanel'); if (p) p.hidden = true; }
  function paintAll() { const p = document.getElementById('wlPanel'); if (p && !p.hidden) paintPanel(); paintStar(); }
  function paintPanel() {
    const p = document.getElementById('wlPanel'); if (!p) return;
    const t = curTab();
    const mode = S.mode === 'cloud' ? '已同步到你的帳號' : (window.TwAccount && window.TwAccount.on && window.TwAccount.on() ? '存在這台裝置（登入後可跨裝置同步）' : '存在這台裝置');
    const tabs = S.tabs.map((x) => P.editing === x.id
      ? `<input id="wlRename" value="${esc(x.name)}" maxlength="${MAX_NAME}" aria-label="新的清單名稱">`
      : `<button type="button" role="tab" data-tab="${esc(x.id)}" class="${x.id === t.id ? 'on' : ''}" aria-selected="${x.id === t.id}" title="${esc(x.name)}（${x.codes.length} 檔）">${esc(x.name)}<small>${x.codes.length}</small></button>`).join('')
      + (S.tabs.length < capTabs() ? `<button type="button" class="wlnew" id="wlNew" title="新增一頁（最多 ${capTabs()} 頁）" aria-label="新增清單">＋</button>` : '');
    p.innerHTML = `<div class="wlhd"><b>自選清單</b><span class="wlmode" id="wlMode">${esc(mode)}</span><button type="button" class="wlx" id="wlClose" aria-label="關閉">✕</button></div>
      <div class="wltabs" role="tablist" id="wlTabs">${tabs}</div>
      <div class="wlact" id="wlAct">${P.confirm
        ? `<span class="wlconf">確定刪除「${esc(t.name)}」（${t.codes.length} 檔）？</span><button type="button" class="danger" id="wlDelYes">刪除</button><button type="button" id="wlDelNo">取消</button>`
        : `<button type="button" id="wlRen">改名</button><button type="button" class="danger" id="wlDel">刪除這一頁</button><span style="flex:1"></span><small style="color:var(--ink-2);font-size:12px">${S.tabs.length}／${capTabs()} 頁</small>`}</div>
      <div class="wladd"><input type="search" id="wlQ" placeholder="加入股票：代號或名稱，例如 2330 或 台積電" autocomplete="off" aria-label="搜尋要加入的股票" value="${esc(P.q)}"><ul class="wlres" id="wlRes"></ul></div>
      <div class="wlmsg" id="wlMsg" ${S.msg ? '' : 'hidden'}>${esc(S.msg)}</div>
      <ul class="wllist" id="wlList"></ul>
      <div class="wlfoot">只存代號與清單名稱，不存張數、成本或損益。</div>`;
    paintList(); paintRes();
    const ri = document.getElementById('wlRename'); if (ri) { ri.focus(); ri.select(); ri.onblur = () => finishRename(true); }
  }
  function paintList() {
    const ul = document.getElementById('wlList'); if (!ul) return;
    const t = curTab(), A = window.App, by = new Map((stocks || []).map((r) => [r.code, r]));
    if (!t.codes.length) { ul.innerHTML = `<li class="wlempty" style="display:block;cursor:default">「${esc(t.name)}」還沒有股票</li>`; return; }
    const others = S.tabs.filter((x) => x.id !== t.id);
    ul.innerHTML = t.codes.map((c) => {
      const r = by.get(c) || { code: c, name: c };
      const cls = A && A.fmt && A.fmt.cls ? A.fmt.cls(r.chg_pct) : '';
      return `<li data-go="${esc(c)}" tabindex="0"><span class="nm">${esc(r.name || c)}<small class="num">${esc(c)}</small></span>
        <span class="num px" data-live="close" data-lc="${esc(c)}">${r.close == null || !A ? '—' : A.fmt.n(r.close)}</span>
        <span class="num ch ${cls}" data-live="chg" data-lc="${esc(c)}">${r.chg_pct == null || !A ? '—' : A.fmt.pct(r.chg_pct, 2)}</span>
        <span>${others.length ? `<select data-mv="${esc(c)}" aria-label="把 ${esc(r.name || c)} 移到別頁"><option value="">移到…</option>${others.map((o) => `<option value="${esc(o.id)}">${esc(o.name)}</option>`).join('')}</select>` : ''}<button type="button" class="del" data-del="${esc(c)}" aria-label="從「${esc(t.name)}」移除 ${esc(r.name || c)}">✕</button></span></li>`;
    }).join('');
  }
  function paintRes() {
    const ul = document.getElementById('wlRes'); if (!ul) return;
    const k = (P.q || '').trim().toUpperCase(), have = new Set(curTab().codes);
    const hit = !k || !stocks ? [] : stocks.filter((r) => r.code.startsWith(k) || String(r.name || '').toUpperCase().includes(k)).slice(0, 8);
    ul.innerHTML = hit.map((r) => `<li><button type="button" data-add="${esc(r.code)}" ${have.has(r.code) ? 'disabled' : ''}><span class="num">${esc(r.code)}</span><b>${esc(r.name)}</b><em>${have.has(r.code) ? '已在這頁' : '＋ 加入'}</em></button></li>`).join('')
      || (k && stocks ? '<li class="wlempty">找不到這個代號或名稱</li>' : '');
  }
  function finishRename(save) {
    const ri = document.getElementById('wlRename'); if (!ri || !P.editing) return;
    const id = P.editing, v = ri.value; P.editing = null;
    if (save && cleanName(v)) API.rename(id, v); else paintPanel();
  }
  function onPanelKey(e) {
    if (e.target.id === 'wlRename') { if (e.key === 'Enter') { e.preventDefault(); finishRename(true); } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finishRename(false); } return; }
    if (e.key === 'Escape') { closePanel(); return; }
    if (e.target.id === 'wlQ' && e.key === 'Enter') { const b = document.querySelector('#wlRes button[data-add]:not([disabled])'); if (b) b.click(); return; }
    const li = e.target.closest && e.target.closest('li[data-go]');
    if (li && e.key === 'Enter' && e.target === li) goStock(li.dataset.go);
  }
  function goStock(c) { location.hash = '#stock/' + c; if (isM()) closePanel(); }
  function onPanelClick(e) {
    const q = (s) => e.target.closest(s);
    if (q('#wlClose')) return closePanel();
    const tb = q('button[data-tab]');
    if (tb) { if (tb.dataset.tab === curTab().id) { P.editing = tb.dataset.tab; paintPanel(); } else { P.confirm = false; API.setCur(tb.dataset.tab); } return; }
    if (q('#wlNew')) { const id = API.newTab(''); if (id) { P.editing = id; paintPanel(); } return; }
    if (q('#wlRen')) { P.editing = curTab().id; paintPanel(); return; }
    if (q('#wlDel')) { P.confirm = true; paintPanel(); return; }
    if (q('#wlDelNo')) { P.confirm = false; paintPanel(); return; }
    if (q('#wlDelYes')) { P.confirm = false; API.delTab(curTab().id); return; }
    const ad = q('button[data-add]'); if (ad && !ad.disabled) { API.add(ad.dataset.add); paintRes(); return; }
    const dl = q('button[data-del]'); if (dl) { e.stopPropagation(); API.remove(dl.dataset.del); return; }
    if (q('select')) return;
    const li = q('li[data-go]'); if (li) goStock(li.dataset.go);
  }
  /* 點面板外面就關（跟站上其他浮層同一個習慣）；點頂欄「自選」那顆本身由它自己切換 */
  document.addEventListener('pointerdown', (e) => {
    const p = document.getElementById('wlPanel');
    if (p && !p.hidden && !p.contains(e.target) && !e.target.closest('#wlBtn,#wlPick,.msheet,#mbWTab')) closePanel();
    const k = document.getElementById('wlPick');
    if (k && !k.hidden && !k.contains(e.target) && !e.target.closest('#wlStar,#mbStar')) closePick();
  }, true);

  /* Esc 關浮層：焦點不一定在浮層裡（勾選或「新增並加入」之後浮層會重畫，焦點掉回 body），所以掛在 document 上 */
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const k = document.getElementById('wlPick');
    if (k && !k.hidden) { closePick(); return; }
    const p = document.getElementById('wlPanel');
    if (p && !p.hidden && !document.getElementById('wlRename')) closePanel();
  });

  // ------------------------------------------------------------------ ☆：選要加進哪一頁（桌機小浮層、手機底部抽屜）
  const K2 = { code: null };
  function pick(code, anchor) {
    injectCSS();
    code = String(code || ''); if (!CODE_RE.test(code)) return;
    let k = document.getElementById('wlPick');
    if (!k) {
      k = document.createElement('div'); k.id = 'wlPick'; k.className = 'wlpick'; k.setAttribute('role', 'dialog'); k.setAttribute('aria-label', '加入自選清單');
      document.body.appendChild(k);
      k.addEventListener('change', (e) => {
        const cb = e.target.closest('input[data-pk]'); if (!cb) return;
        if (cb.checked) API.add(K2.code, cb.dataset.pk); else API.remove(K2.code, cb.dataset.pk);
        paintPick();
      });
      k.addEventListener('click', (e) => {
        if (e.target.closest('#pkClose')) return closePick();
        if (e.target.closest('#pkAdd')) { const i = document.getElementById('pkName'); const id = API.newTab(i ? i.value : ''); if (id) API.add(K2.code, id); paintPick(); }
      });
      k.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closePick();
        if (e.key === 'Enter' && e.target.id === 'pkName') { e.preventDefault(); document.getElementById('pkAdd').click(); }
      });
    }
    K2.code = code; k.hidden = false; paintPick();
    if (!isM() && anchor && anchor.getBoundingClientRect) {
      const r = anchor.getBoundingClientRect(), w = 260;
      k.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left)) + 'px';
      k.style.top = Math.min(window.innerHeight - 40, r.bottom + 6) + 'px';
    }
    const f = k.querySelector('input[type=checkbox]'); if (f && !isM()) try { f.focus(); } catch (e) { /* 略 */ }
  }
  function paintPick() {
    const k = document.getElementById('wlPick'); if (!k || !K2.code) return;
    const nm = (stocks || []).find((r) => r.code === K2.code);
    k.innerHTML = `<div class="pkhd"><span>把 ${esc(nm ? nm.name : '')} <span class="num">${esc(K2.code)}</span> 加進…</span><button type="button" class="wlx" id="pkClose" aria-label="關閉">✕</button></div>`
      + S.tabs.map((t) => `<label><input type="checkbox" data-pk="${esc(t.id)}" ${t.codes.includes(K2.code) ? 'checked' : ''}>${esc(t.name)}<small>${t.codes.length} 檔</small></label>`).join('')
      + (S.tabs.length < capTabs() ? `<div class="pknew"><input id="pkName" maxlength="${MAX_NAME}" placeholder="新清單名稱" aria-label="新清單名稱"><button type="button" id="pkAdd">＋ 新增並加入</button></div>` : '')
      + (S.mode === 'cloud' ? '<div class="pkfoot">已同步到你的帳號</div>' : '');
    if (!stocks) loadStocks().then(() => { if (!k.hidden) paintPick(); });
  }
  function closePick() { const k = document.getElementById('wlPick'); if (k) k.hidden = true; }

  /* 桌機個股頁的 ☆：插在名稱那一行（#skIdent h2）最後。industry.js 每次換股票會重畫這一塊，
     所以盯著 #v-industry 的子樹：☆ 不見了就補回去。不改 industry.js —— 同一時間有別的 agent 在動它。*/
  function stockCode() { const m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(location.hash || ''); return m ? m[1].toUpperCase() : null; }
  function paintStar() {
    const b = document.getElementById('wlStar'); if (!b) return;
    const c = stockCode(), on = !!c && API.has(c);
    /* ★ 2026-10-01 卡頓（DECISIONS #284）：字沒變就不要寫。寫 textContent 本身就是一次 childList 變動，
       會叫醒下面 watchStock 盯著 #v-industry 的 MutationObserver → 下一幀 mountStar → paintStar → 又寫一次……
       個股頁停著不動也每秒跑約 37 輪（連帶 icons.js 的 scan／fitAll 每幀強制排版）。*/
    const t = on ? '★' : '☆'; if (b.textContent !== t) b.textContent = t;
    b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on));
    b.title = on ? '已在自選清單' : '加入自選清單'; b.setAttribute('aria-label', b.title);
  }
  function mountStar() {
    const h = document.querySelector('#skIdent h2'), c = stockCode();
    if (!h || !c) return;
    let b = document.getElementById('wlStar');
    if (b && h.contains(b)) { paintStar(); return; }
    if (b) b.remove();
    injectCSS();
    b = document.createElement('button'); b.type = 'button'; b.id = 'wlStar'; b.className = 'wlstar';
    b.onclick = (e) => { e.stopPropagation(); const k = document.getElementById('wlPick'); if (k && !k.hidden) closePick(); else pick(stockCode(), b); };
    h.appendChild(b); paintStar();
  }
  function watchStock() {
    const v = document.getElementById('v-industry');
    if (!v || !window.MutationObserver) return;
    let t = 0;
    new MutationObserver(() => { if (t) return; t = requestAnimationFrame(() => { t = 0; if (stockCode()) mountStar(); }); }).observe(v, { childList: true, subtree: true });
  }
  window.addEventListener('hashchange', () => { closePick(); setTimeout(mountStar, 0); });
  window.addEventListener('tw:watch', paintStar);

  function boot() { injectCSS(); mountButton(); watchStock(); mountStar(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
