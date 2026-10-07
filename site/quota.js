/* ============================================================================
   每日瀏覽次數 —— admin-v3（2026-10-05）改寫：**每個功能**都可以設上限（蓋掉 sub-v1 只有三個 quota.* 的做法）
   ----------------------------------------------------------------------------
   Andy：「每個功能後面加『瀏覽次數』上限欄位（每日次數，留空或『不限』，0＝不能看）」，
         「超過上限蓋『今日已用完，升級方案』並可點去 #pricing」。

   上限從哪來：/v1/perm/me 的 lims（範本的 plans.lims；perm.js 存在 TwPerm.lim(功能鍵)）。
     · Infinity（沒設）＝不限 → 這支什麼都不做（上線預設，零成本：沒有任何上限時不掛 MutationObserver）
     · 0 ＝不能看 → 交給 perm.js（跟關掉開關同一個鎖頭＋「升級查看」鈕），這裡不重複蓋
     · N ＝每日 N 次 → 這裡計數

   怎麼算「一次」：
     · 「一天」＝台北日期（一律 UTC+8 算）。
     · 有對象的頁面算「看了幾個不同的」：個股頁＝代號、題材剖析＝題材、族群頁＝族群、剖析圖＝每一張圖、產業鏈＝每一條 —— 同一個一天內重複看不重算。
     · 沒有對象的頁面（總覽、資金流向…）＝「這個瀏覽器分頁、這一頁」算一次：同一個分頁來回切不重算，新開一個分頁才算下一次。
     · 只有功能的區塊**真的在畫面上**（getClientRects 有東西）才算 —— 隱藏的 view 不吃額度。
     · 存在 localStorage（tw.quota）；登入者另外送 Worker（/v1/quota/hit，鍵＝功能鍵），伺服器回今天看過哪些，兩邊取聯集。
   用完時：該區塊模糊＋蓋一層「今日已用完 N/N 次」＋「升級查看」鈕（→ #pricing/need/<功能鍵>）。
     · 用自己的屬性 data-qlk（不用 perm.js 的 data-plk）：perm.js 每次重畫會把「不是它掛的」data-plk 拔掉。
     · 遮罩是插在區塊裡的一個節點（要能點按鈕，::after 點不到）；區塊被整個重畫時，MutationObserver 補回來。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const K = 'tw.quota';
  const tpeDay = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
  /* 這個瀏覽器分頁的代號（sessionStorage）：沒有對象的頁面用它當 key —— 同一個分頁重複看不重算 */
  let TAB = null;
  try { TAB = sessionStorage.getItem('tw.quota.tab'); } catch (e) { TAB = null; }
  if (!TAB) { TAB = Math.random().toString(36).slice(2, 8); try { sessionStorage.setItem('tw.quota.tab', TAB); } catch (e) { /* 私密視窗 */ } }
  function safeKey(s) {
    if (/^[0-9A-Za-z_.-]{1,24}$/.test(s)) return s;
    let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    return 'x' + h.toString(16);
  }
  /* 這一頁的 key：有對象的回對象；沒有的回「頁名.分頁代號」 */
  function pageKey(h) {
    let m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h); if (m) return m[1].toUpperCase();
    m = /^#heatmap\/theme\/([^/?]+)/.exec(h); if (m) return safeKey('t.' + decodeURIComponent(m[1]));
    m = /^#industry\/group\/([^/?]+)/.exec(h); if (m) return safeKey('g.' + decodeURIComponent(m[1]));
    /* 2026-10-07 Andy：「產業地圖點分頁超過設定的 5 次還能繼續看」—— 剖析圖分頁用 history.replaceState 換網址（不觸發 hashchange），
       以前這裡掉到最後一行變成「industry.分頁代號」，整個產業地圖只算 1 次。改成：每張剖析圖、每條產業鏈各算一個（同一天重看不重算）。
       ⚠ 不能只看網址：光禿禿的 `#industry/<鏈>` 就是「第一張圖」，網址晚一拍才換成 /dg/<id> —— 只看網址會把同一張圖算兩次。
         所以以畫面上選中的那一張（#dgPick 的 .sel）為準，沒有才退回網址。*/
    m = /^#industry\/([^/?]+)/.exec(h);
    if (m) {
      const chain = decodeURIComponent(m[1]);
      const sel = document.querySelector('#dgPick a.sel[data-dgid]');
      const dm = /\/dg\/([^/?]+)/.exec(h);
      const dg = sel ? sel.dataset.dgid : (dm ? decodeURIComponent(dm[1]) : '');
      return safeKey(dg ? 'd.' + chain + '.' + dg : 'c.' + chain);
    }
    const head = (h.replace(/^#/, '').split(/[/?]/)[0] || 'overview').replace(/[^0-9A-Za-z_-]/g, '').slice(0, 14) || 'p';
    return head + '.' + TAB;
  }
  /* ★ 2026-10-07 覆蓋稽核（docs/quota_coverage.md；Andy：「確實落實每個功能都被使用次數有限制到，不可以漏洞情況」）：
     「單位」改成**依功能決定**，不再整頁共用一個 key —— 例如產業鏈頁上「族群總覽」是一條鏈算一次，「剖析圖」是一張圖算一次；
     共用 pageKey 時，切剖析圖分頁會讓族群總覽也多扣一次（過度扣），反過來族群頁的 key 也會被別的功能用錯。
       stock   ＝個股代號（個股頁所有分頁、K 線週期、工具）           diagram＝d.<鏈>.<圖>（剖析圖 2D／3D）
       chain   ＝c.<鏈>（族群總覽、供應鏈關聯圖）                     theme  ＝t.<題材>（題材剖析）
       group   ＝g.<族群>（族群觀測）                                 visit  ＝<頁>.<分頁代號>（其他：同一個瀏覽器分頁算一次）
     伺服器（workers/data-gw 的 limUnitOf）用**同一組字串**：stock/m60/hist 檔 → 代號；所以前端擋、後端也擋，兩邊數到的是同一個東西。*/
  const UNIT = { 'ind.diagram': 'diagram', 'ind.3d': 'diagram', 'ind.groups': 'chain', 'ind.rel': 'chain', 'heat.detail': 'theme' };
  function unitKind(f) {
    if (!f) return 'visit';
    if (UNIT[f.id]) return UNIT[f.id];
    if (f.cat === 'grp') return 'group';
    if (f.id === 'stock.page' || f.cat === 'stockk' || f.cat === 'stocktab') return 'stock';
    return 'visit';
  }
  function unitKey(f, h) {
    const k = unitKind(f), pk = pageKey(h);
    if (k === 'stock') { const m = /^#stock\/([0-9A-Za-z]{4,6})/.exec(h); return m ? m[1].toUpperCase() : pk; }
    if (k === 'diagram') return /^d\./.test(pk) || /^c\./.test(pk) ? pk : pk;
    if (k === 'chain') {
      const m = /^#industry\/([^/?]+)/.exec(h);
      if (m && !/^#industry\/group\//.test(h)) return safeKey('c.' + decodeURIComponent(m[1]));
      return pk;
    }
    if (k === 'theme') return pk;
    /* 族群觀測每個族群是「自己一個功能」：用族群當單位的話一個功能永遠只有一個單位，設每日 N 次等於沒設（覆蓋稽核 10-07）。
       改成「這個族群頁的一次造訪」（同一個瀏覽器分頁來回切不重算，新開分頁再看算下一次），跟其他沒有對象的頁同一個口徑。*/
    if (k === 'group') return pk + '.' + TAB;
    /* visit：有對象的頁（個股、族群、題材、產業鏈）上，非對象功能也照「這一頁」算 —— 換一檔個股＝新的一次 */
    if (/^#(stock|industry|heatmap\/theme)\//.test(h)) return pk;
    const head = (h.replace(/^#/, '').split(/[/?]/)[0] || 'overview').replace(/[^0-9A-Za-z_-]/g, '').slice(0, 14) || 'p';
    return head + '.' + TAB;
  }
  function load() {
    let d = null; try { d = JSON.parse((T() && T().ls.get(K)) || 'null'); } catch (e) { d = null; }
    if (!d || d.day !== tpeDay() || typeof d.k !== 'object') d = { day: tpeDay(), k: {} };
    return d;
  }
  const save = (d) => { if (T()) T().ls.set(K, JSON.stringify(d)); };
  const P = () => window.TwPerm || null;
  const F = () => window.TwFeatures || null;
  function limitOf(id) { const p = P(); return p && p.lim ? p.lim(id) : Infinity; }
  /* 有設「每日 N 次（N≥1）」而且開關是開的功能（開關關了／上限 0 由 perm.js 鎖）*/
  /* ★ 2026-10-07 覆蓋稽核：族群觀測（grp.*）的功能清單要等 groups_today.json（features.addGroups）才有 ——
     perm.js 只有「真的有族群被關」才去抓，只設了族群「每日次數」的話清單永遠是空的、族群頁永遠不計（漏洞）。這裡自己補抓一次。*/
  let grpAsked = false;
  function needGrp(ks, Ft) {
    if (grpAsked || !ks.some((k) => k.startsWith('grp.')) || Ft.inCat('grp').length) return;
    grpAsked = true;
    fetch('data/groups_today.json').then((r) => (r.ok ? r.json() : [])).then((d) => { if (Ft.addGroups(Array.isArray(d) ? d : []) > 0) schedule(); }).catch(() => { grpAsked = false; });
  }
  function limited() {
    const Ft = F(), p = P(); if (!Ft || !p) return [];
    const st = p.state(); const ks = Object.keys(st.lims || {});
    needGrp(ks, Ft);
    return ks.map((k) => Ft.byId(k)).filter((f) => f && f.kind !== 'limit' && limitOf(f.id) >= 1 && limitOf(f.id) !== Infinity && p.can(f.id));
  }
  const vis = (el) => el.getClientRects().length > 0;
  const q = (sel) => { try { return Array.from(document.querySelectorAll(sel)); } catch (e) { return []; } };
  /* 這個功能在目前畫面上蓋得到的區塊（跟 perm.js 同一套 veil 規則：條件選擇器、route；族群走族群頁）*/
  function targets(f, h) {
    if (f.route && !f.route.test(h)) return [];
    if (f.cat === 'grp') {
      const m = /^#industry\/group\/([^/?]+)/.exec(h);
      /* 族群頁現在顯示的是那個族群的剖析圖＋關聯圖（#dgSec／#relSec），#gpSec 是藏著的 —— 只蓋 #gpSec 等於沒蓋（覆蓋稽核 10-07）*/
      return m && decodeURIComponent(m[1]) === f.gid ? q('#gpSec, #dgSec, #relSec').filter(vis) : [];
    }
    const out = [];
    for (const [sel, when] of f.veil || []) {
      if (when && !q(when).length) continue;
      q(sel).forEach((el) => { if (vis(el) && !out.includes(el)) out.push(el); });
    }
    return out;
  }
  const loggedIn = () => { const A = window.TwAccount; return !!(A && A.on() && A.user()); };

  /* 伺服器同步：登入者每看一個新的就送一次；回來的 keys 併進本機 */
  async function hit(id, key) {
    if (!loggedIn() || !T()) return;
    const j = await T().call('/v1/quota/hit', key ? { k: id, key } : { k: id });
    /* 伺服器說「這個單位超過上限、沒記」（account-api quota-v2：quota.all 與逐功能上限同一套規則）→ 本機也拿掉，下一輪就會蓋卡 */
    if (j && j._s === 200 && j.over && key) {
      const d = load(); d.k[id] = (d.k[id] || []).filter((x) => x !== key); save(d); schedule();
    }
    if (j && j._s === 200 && Array.isArray(j.keys)) {
      const d = load(); const set = new Set(d.k[id] || []); let grew = false;
      j.keys.forEach((x) => { if (!set.has(x)) { set.add(x); grew = true; } });
      if (grew) { d.k[id] = [...set]; save(d); schedule(); }
    }
  }
  /* 登入（或換人）時把有上限的功能都問一次伺服器：今天在別台裝置看過的也要算進來 */
  let syncedFor = '';
  function sync() {
    const A = window.TwAccount, u = A && A.on() && A.user();
    const who = u ? u.email : '';
    if (!who || who === syncedFor) return;
    syncedFor = who;
    const d = load();
    limited().slice(0, 30).forEach((f) => {
      const ks = (d.k[f.id] || []).slice(0, 50);
      if (ks.length) ks.forEach((k) => hit(f.id, k)); else hit(f.id, null);
    });
    if (allLim() !== Infinity) { const ks = (d.k[ALL] || []).slice(0, 50); if (ks.length) ks.forEach((k) => hit(ALL, k)); else hit(ALL, null); }
  }

  // ------------------------------------------------------------------ 判定＋遮罩
  const S = { obs: null, raf: 0 };
  function evaluate() {
    S.raf = 0;
    /* ★ 2026-10-07：逐步導覽進行中（site/tour.js）不扣次、不蓋額度卡 —— 導覽會一頁一頁切過去，不能讓訪客看個導覽就把額度用光；
       導覽一結束（tw:tour 事件）重算一次，額度卡照原規則蓋回來。 */
    try { const ts = window.TwTour && window.TwTour.state(); if (ts && ts.on) { paint(new Map()); return; } } catch (e) { /* 沒有導覽就照舊 */ }
    const h = location.hash || '';
    const fs = limited();
    const d = load(); let changed = false;
    const want = new Map();
    if (!h.startsWith('#admin') && !h.startsWith('#pricing')) {
      for (const f of fs) {
        const els = targets(f, h); if (!els.length) continue;
        const key = unitKey(f, h);
        const lim = limitOf(f.id);
        const set = new Set(d.k[f.id] || []);
        if (set.has(key)) continue;
        if (set.size < lim) { set.add(key); d.k[f.id] = [...set]; changed = true; hit(f.id, key); continue; }
        els.forEach((el) => { if (!want.has(el)) want.set(el, { msg: `今日已用完 ${set.size}/${lim} 次`, f, lim, used: set.size }); });
      }
      /* ★ 2026-10-07 全站共用每日額度（quota.all＝範本 dq；Andy：「訪客只能預覽3次」＝全站共 3 次，不是每個功能各 3 次）：
         這一頁有任何「研究頁」功能（features.js 的 metered）在畫面上 → 這一頁算一個單位（pageKey：個股代號／剖析圖／題材／族群／一次造訪），
         同一天同一單位只算一次；超過 → 這一頁所有研究區塊蓋「今天的研究額度用完了」卡。逐功能上限照樣算，兩者取較嚴（上面那段先擋）。
         登入者的計數也送 /v1/quota/hit（鍵 quota.all），跨裝置合併；付費資料閘道 data-gw 用同一份 dq 在伺服器端扣。*/
      const all = allLim();
      if (all !== Infinity) {
        const Ft = F(), p = P();
        const mf = Ft ? Ft.list.filter((f) => f.metered && p && p.can(f.id)) : [];
        const els = [];
        mf.forEach((f) => targets(f, h).forEach((el) => { if (!els.includes(el)) els.push(el); }));
        if (els.length) {
          const key = pageKey(h);
          const set = new Set(d.k[ALL] || []);
          if (!set.has(key)) {
            if (set.size < all) { set.add(key); d.k[ALL] = [...set]; changed = true; hit(ALL, key); }
            else els.forEach((el) => { if (!want.has(el)) want.set(el, { all: true, msg: `今日已用完 ${set.size}/${all} 次`, lim: all, used: set.size }); });
          }
        }
      }
    }
    if (changed) save(d);
    paint(want);
    watch(fs.length > 0 || allLim() !== Infinity);
  }
  const ALL = 'quota.all';
  const allLim = () => limitOf(ALL);
  /* ★ 2026-10-07：遮罩改用 site/qcard.js 的共用卡片（跟「此功能需開通」、全站每日額度同一款，置中）。
     外層仍是 .qlkov、按鈕仍是 .qlkgo（連 #pricing/need/<功能鍵>），說明裡保留「今日已用完 N/N 次」「升級方案可增加」。*/
  function opts(w) {
    const QC = window.TwQCard;
    if (w.all && QC) {
      const st = P() ? P().state() : {};
      const plan = st.who === 'guest' ? 'guest' : (st.plan || 'free');
      return Object.assign(QC.quotaOpts({ used: w.used, limit: w.lim, plan }), { btnCls: 'qlkgo' });
    }
    const lk = QC ? QC.lockOpts(w.f, 'member') : null;
    const n = w.used == null ? w.lim : w.used;
    return { kind: 'quota', kick: '每日瀏覽次數', title: `今天的「${w.f.name}」次數用完了`,
      sub: `今日已用完 ${n}/${w.lim} 次，升級方案可增加每日次數，明天（台北時間 0 點）自動恢復。`,
      used: n, limit: w.lim, lh: lk && lk.items.length ? '這些方案可以看更多次' : '', items: lk ? lk.items : [],
      btn: lk ? lk.btn : '升級查看', href: '#pricing/need/' + encodeURIComponent(w.f.id), btnCls: 'qlkgo' };
  }
  function paint(want) {
    css();
    const QC = window.TwQCard;
    document.querySelectorAll('[data-qlk]').forEach((el) => { if (!want.has(el)) { el.removeAttribute('data-qlk'); if (QC) QC.unmount(el); const o = el.querySelector(':scope > .qlkov'); if (o) o.remove(); } });
    want.forEach((w, el) => {
      if (el.getAttribute('data-qlk') !== w.msg) el.setAttribute('data-qlk', w.msg);
      if (QC) { QC.mount(el, opts(w), 'qlkov'); return; }
      let o = el.querySelector(':scope > .qlkov');
      if (!o) { o = document.createElement('div'); o.className = 'qlkov'; o.setAttribute('role', 'alert'); el.appendChild(o); }
      const html = `<b>${T().esc(w.msg)}</b><span>${T().esc(w.f.name)}・升級方案可增加每日次數，明天（台北時間 0 點）自動恢復</span><a href="#pricing/need/${encodeURIComponent(w.f.id)}" class="qlkgo">升級查看 →</a>`;
      if (o.dataset.h !== html) { o.innerHTML = html; o.dataset.h = html; }
    });
  }
  /* 節流 200ms：有上限時要觀察整個 body，live.js 每幾秒改一堆格子 —— 不必每一格變動都重算 */
  function schedule() { if (!S.raf) S.raf = setTimeout(evaluate, 200); }
  /* 有上限才觀察 DOM：區塊晚一點才畫出來（個股頁、族群頁都是非同步）也要算到；遮罩被重畫沖掉時補回來 */
  function watch(on) {
    /* ★ 2026-10-07 覆蓋稽核：手機的總覽／資金流向是「分段」切換（只換 class／hidden，不增刪節點）—— 只看 childList 的話，
       切到下一段那張圖不會被重新判定（看得到、不扣次）。改成連 class／hidden／data-tab 也看（跟 perm.js 一樣）。 */
    if (on && !S.obs && window.MutationObserver) { S.obs = new MutationObserver(schedule); S.obs.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'hidden', 'data-tab'] }); }
    else if (!on && S.obs) { S.obs.disconnect(); S.obs = null; }
  }
  function css() {
    if (!T()) return;
    T().css('quotaCss', `
[data-qlk]{position:relative;isolation:isolate;min-height:160px}
[data-qlk]>*:not(.qlkov):not(.qcov){filter:blur(6px)!important;opacity:.25!important;pointer-events:none!important;user-select:none!important}
.qlkov:not(.qcov){position:absolute;inset:0;z-index:40;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:8px;padding:48px 16px 0;text-align:center;
  background:color-mix(in srgb,var(--panel,#111a2b) 55%,transparent);border-radius:inherit}
.qlkov:not(.qcov) b{font-size:18px;color:var(--ink)}
.qlkov:not(.qcov) span{font-size:13.5px;color:var(--ink-2);max-width:420px;line-height:1.6}
.qlkov:not(.qcov) .qlkgo{margin-top:6px;display:inline-flex;align-items:center;height:36px;padding:0 18px;border-radius:999px;background:var(--amber,#f5b942);color:#1a1203;font-weight:700;font-size:14px;text-decoration:none}`);
  }

  window.addEventListener('hashchange', schedule);
  window.addEventListener('tw:tour', () => evaluate());
  window.addEventListener('tw:perm', () => { syncedFor = ''; sync(); schedule(); });
  window.addEventListener('tw:account', () => { sync(); schedule(); });
  function boot() { schedule(); sync(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  /* ★ 2026-10-07 覆蓋稽核：只有「工具鈕」沒有畫面區塊的功能（指標設定、畫線、四週期同看、主題外觀）以前完全不計 —— 漏洞。
     改成：按工具鈕＝用一次（單位同上：個股頁＝那一檔、其他＝這次造訪）；今天的次數用完 → 攔下這一下、跳出同款卡片（TwQCard.modal）。
     捕獲階段攔（比各工具自己的 onclick 早），不必改 industry.js／theme4.js。*/
  document.addEventListener('click', (e) => {
    const fs = limited(); if (!fs.length) return;
    const h = location.hash || '';
    if (h.startsWith('#admin') || h.startsWith('#pricing')) return;
    for (const f of fs) {
      for (const sel of f.block || []) {
        let b = null; try { b = e.target && e.target.closest && e.target.closest(sel); } catch (er) { b = null; }
        if (!b) continue;
        if (f.route && !f.route.test(h)) continue;
        const d = load(), lim = limitOf(f.id), key = unitKey(f, h);
        const set = new Set(d.k[f.id] || []);
        if (set.has(key)) return;
        if (set.size < lim) { set.add(key); d.k[f.id] = [...set]; save(d); hit(f.id, key); return; }
        e.preventDefault(); e.stopImmediatePropagation();
        const QC = window.TwQCard;
        if (QC && QC.modal) QC.modal(opts({ f, lim, used: set.size }));
        return;
      }
    }
  }, true);
  window.TwQuota = { state: () => load(), limit: limitOf, evaluate: () => evaluate(), day: tpeDay, pageKey, unitKey: (id, h) => unitKey(window.TwFeatures && window.TwFeatures.byId(id), h || location.hash || ''), unitKind: (id) => unitKind(window.TwFeatures && window.TwFeatures.byId(id)) };
})();
