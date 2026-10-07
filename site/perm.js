/* ============================================================================
   會員功能權限（前端套用）—— Andy 2026-10-02，DECISIONS #288
   ----------------------------------------------------------------------------
   做什麼：抓「我」的權限（未登入＝訪客方案；登入＝自己 email 那一份），把關掉的功能蓋上鎖頭與「此功能需開通」。
     · 功能清單在 site/features.js（每項的 veil／mark／block 選擇器）；後端是 workers/account-api 的 /v1/perm/me。
     · 不刪節點、不讓整頁消失：鎖頭畫在原本區塊的 ::after 上，內容模糊＋inert（點不到、Tab 走不進去），版面不跳。
     · 用屬性＋CSS 而不是插一個 <div> 進去：那些區塊大多會被各自的程式整個 innerHTML 重畫，插進去的節點會被沖掉；
       屬性掛在外框本身，重畫內容不影響。外框被整個換掉時，MutationObserver 下一個畫格補回來。
     · 一個都沒鎖（現在的預設：全部開啟）→ 不掛 MutationObserver、不攔點擊，對現有使用者零成本。

   ⚠ 誠實的限制（寫在 DECISIONS #288）：這是 GitHub Pages 靜態站，資料 JSON 是公開檔。
     鎖頭只擋一般使用者的畫面；懂技術的人直接讀 site/data/*.json 照樣拿得到。
     真正的付費內容保護，要讓那份資料改由 Worker 驗身分後才提供 —— 這次不做。

   對外：window.TwPerm
     can(id)            這個功能開著嗎（limit 類＝上限 > 0）
     limit(id, 備用值)   數量上限（例如 watch.tabs）
     state()            { who, plan, planName, feats, src }
     refresh()          重抓一次（登入、登出、管理者改了自己的權限之後）
     apply()            立刻重畫一次鎖頭
   事件：window 'tw:perm'（權限換了；watchpage 之類用來重畫上限）

   ★ 2026-10-05（admin-v2，Andy B）族群觀測：功能鍵 grp.<族群鍵>（features.js 的 grpKey）。被關掉的族群：
     · 族群頁（#industry/group/<gid>）：族群總覽那一塊（#gpSec）模糊＋鎖頭「此族群需開通」
     · 資金輪動的「族群」下拉：那一列掛 🔒、勾不下去（跟 block 類的鈕同一套攔截）
     · 熱力圖方塊、資金流向排行長條、輪盤上的族群點：**不模糊**，點了跳「此族群需開通」、不展開成分股。
       為什麼不模糊：這三張是 ECharts 畫在 canvas 上的，單一方塊沒有 DOM 節點可以掛 ::after；
       改資料（把那塊從圖上拿掉）又會讓「全市場」的面積與排行名次失真，所以選「看得到名字與大小、點不進去」。
     清單要等 groups_today.json：只有「真的有族群被關」時才去抓（跟鎖頭一樣，全開時零成本）。
   ============================================================================ */
(function () {
  'use strict';
  const F = window.TwFeatures;
  if (!F) return;
  const K_CACHE = 'tw.perm';
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 略 */ } } };
  const S = { who: 'guest', plan: '', planName: '', feats: {}, lims: {}, src: 'default', key: null, obs: null, raf: 0, seq: 0 };

  const acct = () => window.TwAccount || null;
  const meKey = () => { const A = acct(); const u = A && A.on() && A.user(); return u && u.email ? 'u:' + String(u.email).toLowerCase() : 'guest'; };

  /* ★ 2026-10-07 16:30 Andy：「將我把 kcq01010909 帳號設為最高管理權限，他不會需要被限制」→ 擁有者（/v1/me 的 owner 旗標，判定在 Worker）
     所有鎖頭、次數、自選上限一律豁免；Worker 的 /v1/perm/me 對擁有者也回全開（兩邊都做：舊快取、Worker 還沒部署時前端也不鎖）。*/
  const owner = () => { const A = acct(); const u = A && A.on && A.on() && A.user && A.user(); return !!(u && u.owner); };
  function value(id) {
    const f = F.byId(id); if (!f) return true;
    if (owner()) return f.kind === 'limit' ? f.max : true;
    const v = S.feats[id];
    if (f.kind === 'limit') return Number.isInteger(v) ? Math.max(0, Math.min(f.max, v)) : (v === false ? 0 : f.def);
    return typeof v === 'boolean' ? v : f.def;
  }
  /* ★ admin-v3：瀏覽次數上限 0＝「不能看」，跟關掉開關同一個效果（同一套鎖頭＋升級鈕）；N＞0 的計數在 quota.js */
  function can(id) { if (owner()) return true; if (S.lims[id] === 0) return false; const v = value(id); return typeof v === 'number' ? v > 0 : v !== false; }
  /* 每日瀏覽次數上限：Infinity＝不限（沒設）、0＝不能看、N＝每日 N 次 */
  function lim(id) {
    if (owner()) return Infinity;
    /* ★ 2026-10-07 全站共用每日額度：'quota.all' 讀範本的 dq（/v1/perm/me 的 dq；null＝不限），不是 lims 裡的一項 */
    if (id === 'quota.all') return Number.isInteger(S.dq) && S.dq >= 0 ? S.dq : Infinity;
    const v = S.lims[id]; return Number.isInteger(v) && v >= 0 ? v : Infinity;
  }
  const routeOk = (f) => !f.route || f.route.test(location.hash || '');
  function limit(id, fb) { const f = F.byId(id); return f ? value(id) : fb; }
  const lockedList = () => F.list.filter((f) => f.kind !== 'limit' && !can(f.id));

  // ------------------------------------------------------------------ 樣式
  function css() {
    if (document.getElementById('permCss')) return;
    const s = document.createElement('style'); s.id = 'permCss';
    /* isolation:isolate —— 讓 ::after 的 z-index 只在這個區塊裡比，不會蓋到頁面上的下拉、抽屜（DECISIONS #278 同一個原則）*/
    s.textContent = `
[data-plk]{isolation:isolate;min-height:120px}
[data-plk][data-plk-rel]{position:relative}
[data-plk]>*:not(.qcov){filter:blur(5px)!important;opacity:.28!important;pointer-events:none!important;user-select:none!important}
/* 2026-10-07（Andy：「此功能需開通」改成跟額度用完同一款卡片、置中）：字不再畫在 ::after，改由 site/qcard.js 插一張卡片（.qcov.plkov）。
   ::after 只留一層淡淡的底，讓模糊的內容退後；卡片本身在 .qcov 裡水平垂直置中 */
[data-plk]::after{content:""!important;position:absolute!important;inset:0!important;z-index:30!important;display:block!important;
  background:color-mix(in srgb,var(--panel,#111a2b) 35%,transparent)!important;border-radius:inherit!important;pointer-events:none!important;
  opacity:1!important;filter:none!important;width:auto!important;height:auto!important;transform:none!important}
[data-plkb]::after{content:" 🔒"!important;font-size:.85em!important;color:inherit!important;opacity:.9!important;margin-left:2px!important;vertical-align:0!important}
[data-plkb="block"]{opacity:.62}
.permtoast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:1500;background:var(--panel-3,#1c2638);color:var(--ink,#e6edf6);
  border:1px solid var(--line-2,#33415a);border-radius:10px;padding:10px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3);max-width:calc(100vw - 32px)}
.permtoast[hidden]{display:none}`;
    document.head.appendChild(s);
  }
  function toast(msg) {
    let t = document.getElementById('permToast');
    if (!t) { t = document.createElement('div'); t.id = 'permToast'; t.className = 'permtoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3200);
  }
  function msgOf(f) {
    const tail = S.who === 'guest' && acct() && acct().on() ? '登入或升級方案即可使用' : '升級方案即可使用';
    return `🔒 ${f.cat === 'grp' ? '此族群需開通' : '此功能需開通'}\n${f.name}・${tail}`;
  }
  /* 族群清單：只有權限裡真的有 grp.* 被關時才抓（全開時不多打一支請求）*/
  let grpLoading = null;
  function needGroups() {
    if (grpLoading || F.inCat('grp').length) return;
    if (!Object.keys(S.feats).some((k) => k.startsWith('grp.') && S.feats[k] === false)) return;
    grpLoading = fetch('data/groups_today.json').then((r) => r.ok ? r.json() : []).then((d) => { if (F.addGroups(Array.isArray(d) ? d : []) > 0) schedule(); }).catch(() => { grpLoading = null; });
  }
  const lockedGrp = () => F.inCat('grp').filter((f) => !can(f.id));
  /* 給 app.js 的 canvas 圖（熱力圖／排行／輪盤）用：被關的族群回 true 並跳提示，呼叫端就不展開 */
  function grpBlock(gid, name) {
    if (!gid) return false;
    const f = F.byId(F.grpKey(gid));
    if (owner() || (!f ? S.feats[F.grpKey(gid)] !== false : can(f.id))) return false;
    toast('🔒 此族群需開通：' + (name || (f && f.name) || gid));
    return true;
  }

  // ------------------------------------------------------------------ 套用鎖頭
  const touring = () => { try { const s = window.TwTour && window.TwTour.state(); return !!(s && s.on); } catch (e) { return false; } };
  const q = (sel) => { try { return Array.from(document.querySelectorAll(sel)); } catch (e) { return []; } };
  function apply() {
    S.raf = 0;
    css();
    const want = new Map(), wantB = new Map(), wantF = new Map();
    for (const f of lockedList()) {
      if (!routeOk(f)) continue;
      for (const [sel, when] of f.veil || []) {
        if (when && !q(when).length) continue;
        q(sel).forEach((el) => { if (!want.has(el)) { want.set(el, msgOf(f)); wantF.set(el, f.id); } });
      }
      (f.mark || []).forEach((sel) => q(sel).forEach((el) => { if (!wantB.has(el)) wantB.set(el, 'mark'); }));
      (f.block || []).forEach((sel) => q(sel).forEach((el) => wantB.set(el, 'block')));
    }
    /* 族群觀測：族群頁＋族群下拉（canvas 圖走 grpBlock）*/
    const lg = lockedGrp();
    if (lg.length) {
      const m = /^#industry\/group\/([^/?]+)/.exec(location.hash || '');
      const cur = m ? decodeURIComponent(m[1]) : null;
      for (const f of lg) {
        /* 2026-10-07 覆蓋稽核：族群頁現在顯示的是該族群的剖析圖＋關聯圖（#dgSec／#relSec），#gpSec 藏著 —— 三塊都蓋，不然鎖了等於沒鎖 */
        if (cur && f.gid === cur) q('#gpSec, #dgSec, #relSec').forEach((el) => { want.set(el, msgOf(f)); wantF.set(el, f.id); });
        q('.rotdd input[data-g]').forEach((inp) => { if (inp.dataset.g === f.gid) { const row = inp.closest('.ddopt') || inp; wantB.set(row, 'block'); } });
      }
    }
    needGroups();
    /* ★ 2026-10-07（Andy：「導覽即使是訪客 也需要看得到畫面」）：逐步導覽（site/tour.js）進行中暫停所有鎖頭遮罩，
       導覽一結束（tw:tour 事件）就照原規則蓋回來。只是畫面層，沒有打開任何資料。 */
    if (touring()) { want.clear(); wantB.clear(); }
    /* 只動「該變」的：屬性沒變就不寫（寫屬性會觸發樣式重算；live.js 每 5 秒改一堆格子，這裡每次都會被叫到）*/
    q('[data-plk]').forEach((el) => { if (!want.has(el)) unveil(el); });
    want.forEach((m, el) => {
      if (el.getAttribute('data-plk') !== m) {
        el.setAttribute('data-plk', m);
        if (getComputedStyle(el).position === 'static') el.setAttribute('data-plk-rel', '');
        el.setAttribute('aria-label', m.replace('\n', '：'));
      }
      veilKids(el, wantF.get(el));
    });
    q('[data-plkb]').forEach((el) => { if (!wantB.has(el)) { el.removeAttribute('data-plkb'); if (el.dataset.plkTitle != null) { el.title = el.dataset.plkTitle; delete el.dataset.plkTitle; } } });
    wantB.forEach((k, el) => {
      if (el.getAttribute('data-plkb') !== k) {
        el.setAttribute('data-plkb', k);
        if (el.dataset.plkTitle == null) el.dataset.plkTitle = el.title || '';
        el.title = '此功能需開通';
      }
    });
    watch(want.size + wantB.size > 0 || lockedList().length > 0);
  }
  /* ★ admin-v3（Andy D③）：鎖頭上要有一顆能點的「升級查看」→ #pricing/need/<功能鍵>（訂閱頁把能解鎖它的方案標出來）。
     原本整塊 inert（連鈕都點不到）→ 改成「外框不 inert、裡面原本的子節點逐一 inert」，只有升級鈕可以點。
     子節點被各自的程式整個重畫時（innerHTML），MutationObserver 下一個畫格會再進來補 inert 與按鈕。 */
  /* ★ 2026-10-07（Andy：「此功能需開通」改成跟額度用完同一款卡片）：原本的一顆「升級查看 →」換成 site/qcard.js 的需開通卡
     （小標、大標「此功能需開通」、功能名、「這些方案可以使用」清單、全寬「升級 Plus →」）。按鈕仍是 a.plkgo、仍連 #pricing/need/<功能鍵>。
     qcard.js 沒載入（理論上不會）→ 退回舊的單顆按鈕，鎖頭照樣能點。 */
  let plansAsked = false;
  function veilKids(el, fid) {
    const href = '#pricing/need/' + encodeURIComponent(fid || '');
    const QC = window.TwQCard, f = F.byId(fid) || { id: fid, name: '', cat: '' };
    let ov;
    if (QC) {
      ov = QC.mount(el, QC.lockOpts(f, S.who), 'plkov');
      /* 卡片的清單要寫「哪個方案有這個功能」→ 第一次上鎖時順手抓方案清單（訂閱頁同一份；抓到會發 tw:plans 再重畫）*/
      if (!plansAsked && window.TwPricing && window.TwPricing.ensure) { plansAsked = true; window.TwPricing.ensure(); }
    } else {
      ov = el.querySelector(':scope > .plkgo');
      if (!ov) { ov = document.createElement('a'); ov.className = 'plkgo qcov'; ov.textContent = '升級查看 →'; el.appendChild(ov); }
      if (ov.getAttribute('href') !== href) ov.setAttribute('href', href);
      if (el.lastElementChild !== ov) el.appendChild(ov);
    }
    for (const k of el.children) if (k !== ov && !k.classList.contains('qcov') && !k.inert) { k.inert = true; k.setAttribute('data-plk-in', ''); }
  }
  function unveil(el) {
    el.removeAttribute('data-plk'); el.removeAttribute('data-plk-rel'); el.removeAttribute('aria-label'); el.inert = false;
    if (window.TwQCard) window.TwQCard.unmount(el);
    const go = el.querySelector(':scope > .plkgo'); if (go) go.remove();
    el.querySelectorAll(':scope > [data-plk-in]').forEach((k) => { k.inert = false; k.removeAttribute('data-plk-in'); });
  }
  function schedule() { if (!S.raf) S.raf = requestAnimationFrame(apply); }
  function watch(on) {
    if (on && !S.obs && window.MutationObserver) {
      S.obs = new MutationObserver(schedule);
      S.obs.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'data-tab', 'hidden'] });
    } else if (!on && S.obs) { S.obs.disconnect(); S.obs = null; }
  }
  /* 「按了不會動作」的鈕：捕獲階段攔下來（比各自的 onclick 早），不必改那幾支別人正在改的檔案 */
  document.addEventListener('click', (e) => {
    const b = e.target && e.target.closest && e.target.closest('[data-plkb="block"]');
    if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const gi = b.querySelector && b.querySelector('input[data-g]');
    const gf = gi ? F.byId(F.grpKey(gi.dataset.g)) : null;
    if (gf) { toast('🔒 此族群需開通：' + gf.name); return; }
    const f = lockedList().find((x) => (x.block || []).some((s) => { try { return b.matches(s); } catch (er) { return false; } }));
    toast('🔒 此功能需開通' + (f ? '：' + f.name : ''));
  }, true);

  // ------------------------------------------------------------------ 讀取
  /* 示範開關 ?demo=lock（給 Andy 在預覽站看「需開通」卡，site/qcard.js 檔頭）：只在這個分頁、只改畫面，
     把「產業鏈剖析圖（2D）」當成被關掉 —— 走的是跟真的鎖頭同一條路（apply → veilKids → 卡片）。不寫任何設定。*/
  const DEMO_LOCK = /[?&]demo=lock(&|$)/.test(location.search);
  function set(d, src) {
    if (DEMO_LOCK) d = Object.assign({}, d, { feats: Object.assign({}, d.feats || {}, { 'ind.diagram': false }) });
    const before = JSON.stringify([S.who, S.plan, S.feats, S.lims, S.dq]);
    S.who = d.who || 'guest'; S.plan = d.plan || ''; S.planName = d.planName || '';
    S.feats = d.feats && typeof d.feats === 'object' ? d.feats : {};
    S.lims = d.lims && typeof d.lims === 'object' && !Array.isArray(d.lims) ? d.lims : {};
    S.dq = Number.isInteger(d.dq) ? d.dq : null;
    S.src = src;
    apply();
    if (before !== JSON.stringify([S.who, S.plan, S.feats, S.lims, S.dq])) window.dispatchEvent(new CustomEvent('tw:perm', { detail: state() }));
  }
  function state() { return { who: S.who, plan: S.plan, planName: S.planName, feats: Object.assign({}, S.feats), lims: Object.assign({}, S.lims), dq: S.dq == null ? null : S.dq, src: S.src }; }
  async function refresh() {
    const A = acct();
    const key = meKey();
    /* 會員功能沒設定（線上目前的狀態：account_config.js 是空的）→ 不連任何地方，全部照預設（＝全開）*/
    if (!A || !A.on()) { ls.del(K_CACHE); set({ who: 'guest', feats: {} }, 'default'); return; }
    const seq = ++S.seq; S.reqKey = key;
    const j = await A.call('/v1/perm/me', {});
    if (seq !== S.seq) return;                      // 期間又登入／登出過：以最新那次為準
    if (j && j._s === 200 && j.feats) {
      ls.set(K_CACHE, JSON.stringify({ k: key, who: j.who, plan: j.plan, planName: j.planName, feats: j.feats, lims: j.lims || {}, dq: Number.isInteger(j.dq) ? j.dq : null }));
      set(j, 'server');
    } else if (j && j._s === 401) {
      /* account.js 已經把權杖清掉、改回訪客；tw:account 事件會再叫一次 refresh */
    } else if (S.key !== key) {
      /* 連不到（公司網路、Worker 還沒更新成有這支 API 的版本）：沒有這個人的快取就全開 —— 寧可多給，不要誤鎖 */
      set({ who: key === 'guest' ? 'guest' : 'member', feats: {} }, 'default');
    }
    S.key = key;
  }
  /* 先用上次存的（同一個人才用）把鎖頭立刻掛上，避免重新整理時「先看到內容、一秒後才上鎖」 */
  function fromCache() {
    try {
      const c = JSON.parse(ls.get(K_CACHE) || 'null');
      if (c && c.k === meKey() && c.feats) { S.key = c.k; set(c, 'cache'); return true; }
    } catch (e) { /* 壞掉的快取當沒有 */ }
    return false;
  }

  window.TwPerm = { can, limit, lim, value, state, refresh, apply: () => apply(), locked: () => lockedList().map((f) => f.id), grpBlock,
    grpOk: (gid) => { if (owner()) return true; const k = F.grpKey(gid); const f = F.byId(k); return f ? can(k) : S.feats[k] !== false; }, owner };
  window.addEventListener('hashchange', schedule);
  window.addEventListener('tw:plans', schedule);
  window.addEventListener('tw:tour', () => { if (typeof apply === 'function') apply(); });

  /* 啟動：account.js 先跑（它決定會員功能開不開），開了會發 tw:account-config；沒開就照預設全開。
     account.js 啟動時驗權杖也會發一次 tw:account —— 同一個人 5 秒內不重抓（不然每次重新整理都打兩次）。*/
  let started = false;
  function start() { if (started) return; started = true; fromCache(); S.at = Date.now(); refresh(); }
  function boot() { if (window.TW_ACCOUNT_ON) start(); else if (!started) refresh(); }
  window.addEventListener('tw:account', () => {
    /* 擁有者身分一確認（/v1/me 回 owner）就立刻解鎖，不等 5 秒的重抓節流 */
    if (owner() !== !!S.own) { S.own = owner(); apply(); window.dispatchEvent(new CustomEvent('tw:perm', { detail: state() })); }
    if (meKey() === S.reqKey && Date.now() - (S.at || 0) < 5000) return;
    S.at = Date.now(); refresh();
  });
  window.addEventListener('tw:account-config', start);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
