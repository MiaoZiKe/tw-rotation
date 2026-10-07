/* ============================================================================
   訂閱頁 #pricing ＋ 帳號選單的方案徽章（sub-v1，2026-10-05）
   ----------------------------------------------------------------------------
   ★ admin-v3（2026-10-05）：拿掉月繳／年繳切換 —— 每個付費範本本身就是「月訂閱」或「年訂閱」（後端範本決定），
     方案卡與 #admin/perm 的三個大分頁同一份資料；#pricing/need/<功能鍵> 把能解鎖那個功能的方案標「可解鎖」。
   Andy：參考 stockintelli 的 pricing —— 頂部標語＋四個亮點、方案卡（最受歡迎／功能最齊）、
   「查看完整權益」、訂閱鈕；帳號選單顯示名字＋方案徽章。

   這頁回答一個問題：「每個方案差在哪、我現在是哪一個、要怎麼升級」。
     · 方案卡不寫死：由 Worker 的方案範本產生（/v1/plans/public；訪客、註冊會員＝免費、其他＝付費範本）。
       每張卡列出的功能＝features.js 的分類 × 該範本的 feats 算出來的，管理者在 #admin/perm 關掉什麼，這裡就少什麼。
     · 價格讀後端（admin-v2 在 plans 表加 price／period／price_year）。拿不到價格 → 不編數字，寫「洽詢」。
     · 年繳：後端有年價就用；沒有就用「月價 × 12 × 0.83」估，畫面上寫明「估算」—— 不讓人以為那是報價。
     · ⚠ 金流還沒串：訂閱鈕開的是「訂閱申請」（存 Worker 的 sub_requests，專人開通），畫面明寫。
     · 連不到 Worker（公司網路、會員功能沒設定）→ 用內建三張卡（訪客／註冊會員／付費），價格一律「洽詢」。

   對外：window.TwSub（給 support.js／notices.js／quota.js 共用的小工具）、window.TwPlanBadge()（帳號選單的徽章 HTML）
   路由：TwSubRoutes 登記 'pricing'（app.js route() 會先問這裡）。
   ============================================================================ */
(function () {
  'use strict';
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } } };
  const A = () => window.TwAccount || null;
  const F = () => window.TwFeatures || null;
  const P = () => window.TwPerm || null;
  /* 呼叫 Worker：會員功能沒設定（api 空）→ null，呼叫端自己退回備用畫面 */
  async function call(path, body) { const a = A(); if (!a || !a.on()) return null; return a.call(path, body || {}); }
  function view(id) {
    let v = document.getElementById(id);
    if (v) return v;
    const main = document.querySelector('main'); if (!main) return null;
    v = document.createElement('section'); v.className = 'view'; v.id = id;
    main.insertBefore(v, document.getElementById('siteFoot') || null);
    return v;
  }
  function toast(msg) {
    let t = document.getElementById('subToast');
    if (!t) { t = document.createElement('div'); t.id = 'subToast'; t.className = 'subtoast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3600);
  }
  function css(id, text) { if (document.getElementById(id)) return; const s = document.createElement('style'); s.id = id; s.textContent = text; document.head.appendChild(s); }
  /* 對話框：一個共用的殼（遮罩＋盒子），內容由呼叫端給；Esc／點遮罩／[data-close] 關閉 */
  function dialog(html, onMount) {
    css('subDlgCss', `
.subdlg{position:fixed;inset:0;z-index:1400;display:grid;place-items:center;background:rgba(3,6,14,.55);padding:16px}
.subdlg[hidden]{display:none}
.subdlg .box{width:min(480px,100%);max-height:calc(100vh - 32px);overflow:auto;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);border-radius:14px;padding:20px 22px;box-shadow:0 24px 60px -20px rgba(0,0,0,.7)}
.subdlg h3{margin:0 0 8px;font-size:18px}
.subdlg p{margin:6px 0;font-size:14px;line-height:1.65;color:var(--ink-2)}
.subdlg label{display:block;font-size:13px;color:var(--ink-2);margin:12px 0 4px}
.subdlg input[type=email],.subdlg input[type=text],.subdlg select,.subdlg textarea{width:100%;box-sizing:border-box;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:8px 10px;font:inherit;font-size:14px}
.subdlg textarea{min-height:110px;resize:vertical}
.subdlg .row2{display:flex;gap:10px;justify-content:flex-end;margin-top:16px;flex-wrap:wrap}
.subdlg .row2 button{height:36px;padding:0 16px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:14px;cursor:pointer}
.subdlg .row2 button.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
.subdlg .seg{display:inline-flex;border:1px solid var(--line-2);border-radius:9px;overflow:hidden}
.subdlg .seg button{height:32px;padding:0 14px;border:0;background:transparent;color:var(--ink-2);font-size:13.5px;cursor:pointer}
.subdlg .seg button.on{background:var(--cyan);color:#04121a;font-weight:700}
.subdlg .msg{font-size:13.5px;margin-top:10px;min-height:1.2em}
.subdlg .msg.bad{color:var(--rise)}.subdlg .msg.ok{color:var(--fall)}
.subtoast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:1500;background:var(--panel-3);color:var(--ink);border:1px solid var(--line-2);border-radius:10px;padding:10px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.subtoast[hidden]{display:none}`);
    let d = document.getElementById('subDlg');
    if (!d) {
      d = document.createElement('div'); d.id = 'subDlg'; d.className = 'subdlg'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-modal', 'true');
      document.body.appendChild(d);
      d.addEventListener('click', (e) => { if (e.target === d || e.target.closest('[data-close]')) d.hidden = true; });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !d.hidden) d.hidden = true; });
    }
    d.innerHTML = '<div class="box">' + html + '</div>';
    d.hidden = false;
    if (onMount) onMount(d);
    const f = d.querySelector('input,textarea,select,button.pri'); if (f) setTimeout(() => f.focus(), 30);
    return d;
  }
  const routes = window.TwSubRoutes = window.TwSubRoutes || [];
  window.TwSub = { esc, ls, call, view, toast, css, dialog, A, F, P };

  // ------------------------------------------------------------------ 我是哪個方案（徽章）
  /* 訪客／免費會員／方案名。來源：perm.js 的 state()（＝/v1/perm/me 的結果）*/
  function myPlan() {
    const a = A(), u = a && a.on() ? a.user() : null;
    const st = P() ? P().state() : { who: 'guest', plan: '', planName: '' };
    if (!u) return { id: 'guest', label: '訪客', tier: 'guest' };
    if (!st.plan || st.plan === 'free' || st.who === 'guest') return { id: 'free', label: '免費會員', tier: 'free' };
    return { id: st.plan, label: st.planName || st.plan, tier: 'paid' };
  }
  window.TwPlanBadge = function () {
    const m = myPlan();
    return `<a href="#pricing" class="planbadge t-${m.tier}" data-plan="${esc(m.id)}" title="查看方案與升級">${esc(m.label)}</a>`;
  };
  css('planBadgeCss', `
.planbadge{display:inline-flex;align-items:center;height:22px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:700;text-decoration:none;white-space:nowrap;
  border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3)}
.planbadge.t-free{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 45%,transparent)}
.planbadge.t-paid{color:#1a1203;background:var(--amber);border-color:transparent}
.acctmenu .mh.mhx{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;align-items:center}
.acctmenu .mh.mhx .av{grid-row:span 2;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--violet);color:#fff;font-weight:700;font-size:16px}
.acctmenu .mh.mhx .nm{display:flex;align-items:center;gap:8px;min-width:0}
.acctmenu .mh.mhx .nm b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}`);

  // ------------------------------------------------------------------ 方案資料
  /* ★ admin-v3（2026-10-05，Andy D）：方案卡＝會員權限那邊的三個大分頁 —— 訪客、註冊會員、每個付費範本各一張。
     · 名稱、價格、月／年全部讀後端範本（/v1/plans/public；舊 Worker 沒有這支時，管理者退回 plans/get）。
     · 連不到後端（會員功能沒設定、公司網路）→ 只畫訪客、註冊會員兩張，**不編一張「付費・洽詢」**
       （Andy 截圖：付費寫「洽詢」、訪客出現兩次 —— 前者是備用卡、後者是同一個範本被畫兩次；這裡依 id 去重）。
     · 每張卡列出：每一類開放幾項、有設上限的功能（每日 N 次／不能看）——跟 #admin/perm 的「觀看權限」同一份資料。 */
  const FALLBACK = [
    { id: 'guest', name: '訪客', builtin: true, feats: {}, lims: {}, price: 0 },
    { id: 'free', name: '註冊會員', builtin: true, feats: {}, lims: {}, price: 0 },
  ];
  const S = { plans: null, src: 'fallback', full: false, loading: null, need: '', pick: '' };
  /* 2026-10-07 每日額度（docs/quota_plan.md）：Plus（每日 50）／Pro（不限）由 account-api 第一次啟動時種成付費範本（SEED_PLANS）。
     ★ 方案卡仍然只畫後端有的範本（Andy 10-05：不編卡）。唯一例外是示範開關 ?demo=quota／quota-free／lock（預覽站給 Andy 看卡片用）：
       後端還沒有 plus／pro 時補兩張「價格待定」的示意卡，讓額度卡的「升級 Plus／Pro →」點過來有東西可看。 */
  const DEMO = /[?&]demo=(quota|quota-free|lock)(&|$)/.test(location.search);
  const DEMO_PLANS = [{ id: 'plus', name: 'Plus', builtin: false, feats: { 'watch.tabs': 5, 'watch.size': 50 }, lims: {}, price: 0, period: 'month', dq: 50, demo: true },
    { id: 'pro', name: 'Pro', builtin: false, feats: { 'watch.tabs': 50, 'watch.size': 200 }, lims: {}, price: 0, period: 'month', dq: null, demo: true }];
  const tierOf = (p) => (p.id === 'guest' ? 'guest' : p.id === 'free' ? 'free' : 'paid');
  const showName = (p) => (p.id === 'guest' ? '訪客' : p.id === 'free' ? '註冊會員' : p.name);
  /* 排序＋去重：訪客、註冊會員固定在前；付費依後端順序；同一個 id 只留第一個 */
  function tidy(list) {
    const seen = new Set(), out = [];
    const all = Array.isArray(list) ? list : [];
    const g = all.find((p) => p && p.id === 'guest') || FALLBACK[0], f = all.find((p) => p && p.id === 'free') || FALLBACK[1];
    [g, f, ...all.filter((p) => p && p.id !== 'guest' && p.id !== 'free')].forEach((p) => { if (p && p.id && !seen.has(p.id)) { seen.add(p.id); out.push(p); } });
    if (DEMO) DEMO_PLANS.forEach((p) => { if (!seen.has(p.id)) { seen.add(p.id); out.push(p); } });
    return out;
  }
  async function load() {
    if (S.loading) return S.loading;
    S.loading = (async () => {
      let j = await call('/v1/plans/public', {});
      /* 公開端點還沒部署（舊版 Worker）→ 管理者還可以用 admin 的那支拿到 */
      if ((!j || j._s !== 200) && A() && A().user() && A().user().admin) j = await call('/v1/admin/plans/get', {});
      if (j && j._s === 200 && Array.isArray(j.plans) && j.plans.length) { S.plans = tidy(j.plans); S.src = 'server'; } else { S.plans = tidy(FALLBACK.slice()); S.src = 'fallback'; }
    })();
    try { await S.loading; } finally { S.loading = null; }
    /* 額度卡／需開通卡（site/qcard.js）要寫「哪個方案有、升級哪一個」→ 方案清單到了就通知它們重畫 */
    window.dispatchEvent(new CustomEvent('tw:plans'));
  }
  const PER = { month: '月', year: '年', once: '一次' };
  /* 價格：回 { amount, unit }；訪客／註冊會員＝免費 */
  function priceOf(p) {
    if (tierOf(p) !== 'paid') return { amount: 0, unit: '', free: true };
    const n = Number.isInteger(p.price) ? p.price : (p.price != null && isFinite(+p.price) ? Math.round(+p.price) : 0);
    /* 付費範本價格是 0 ＝還沒定價（Plus／Pro 種子就是 0）→ 寫「價格待定」，不寫 NT$ 0 讓人以為免費 */
    return { amount: n, unit: p.period === 'once' ? '（一次）' : '／' + (PER[p.period] || '月'), free: false, tbd: n === 0 };
  }
  /* 全站每日額度（plans.dq；null＝不限）*/
  const dqTxt = (p) => (Number.isInteger(p.dq) ? `每日 ${p.dq} 次` : '不限');
  /* 這個方案在某個功能上的值（沒寫＝預設）；上限：Infinity＝不限 */
  function val(p, f) { const v = (p.feats || {})[f.id]; if (f.kind === 'limit') return Number.isInteger(v) ? v : v === false ? 0 : f.def; return typeof v === 'boolean' ? v : f.def; }
  const limOf = (p, f) => { const v = (p.lims || {})[f.id]; return Number.isInteger(v) && v >= 0 ? v : Infinity; };
  const on = (p, f) => { if (limOf(p, f) === 0) return false; const v = val(p, f); return typeof v === 'number' ? v > 0 : v !== false; };
  const ltxt = (n) => (n === Infinity ? '不限' : n === 0 ? '不能看' : `每日 ${n} 次`);
  function catsOf() {
    const Ft = F(); if (!Ft) return [];
    // adminOnly（盤中即時、1／5／15 分 K，DECISIONS #326）：只有管理者帳號有，不算方案權益
    return Ft.cats.filter((c) => c.id !== 'grp').map((c) => ({ c, fs: Ft.inCat(c.id).filter((f) => f.kind === 'bool' && !f.adminOnly) })).filter((x) => x.fs.length);
  }
  function summary(p) {
    const Ft = F(); if (!Ft) return { lines: [], q: [], n: 0, total: 0 };
    let n = 0, total = 0;
    const lines = catsOf().map(({ c, fs }) => {
      const k = fs.filter((f) => on(p, f)).length; n += k; total += fs.length;
      return { name: c.name, k, t: fs.length };
    });
    /* 瀏覽次數：只列「有設上限而且開關是開的」功能（關掉的已經算在上面的「不開放」）*/
    const q = Object.keys(p.lims || {}).map((k) => Ft.byId(k)).filter((f) => f && f.cat !== 'grp' && val(p, f) !== false && limOf(p, f) > 0)
      .map((f) => ({ id: f.id, name: f.name, txt: ltxt(limOf(p, f)) }));
    const wt = Ft.byId('watch.tabs'), ws = Ft.byId('watch.size');
    return { lines, q, n, total, watch: wt ? val(p, wt) : null, wmax: wt ? wt.max : 0, size: ws ? val(p, ws) : null, smax: ws ? ws.max : 0 };
  }
  /* 「我現在」在某功能上的狀態（給 need 標示用）：能不能看、上限 */
  function mine(f) { const P0 = P(); if (!P0) return { on: true, lim: Infinity }; return { on: P0.can(f.id), lim: P0.lim ? P0.lim(f.id) : Infinity }; }
  /* 這個方案能不能讓「我」在這個功能上變得更好（開得了、或次數更多）*/
  function unlocks(p, f) { const m = mine(f); if (!on(p, f)) return false; return !m.on || limOf(p, f) > m.lim; }

  // ------------------------------------------------------------------ 畫面
  css('pricingCss', `
#v-pricing{max-width:1180px;margin:0 auto;padding:8px 0 40px}
#v-pricing .prhero{text-align:center;padding:26px 12px 6px}
#v-pricing .prhero h1{margin:0;font-size:28px;letter-spacing:.5px}
#v-pricing .prhero p{margin:8px auto 0;color:var(--ink-2);font-size:15px;max-width:640px;line-height:1.7}
#v-pricing .prpts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0 8px}
#v-pricing .prpt{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
#v-pricing .prpt b{display:block;font-size:15px;margin-bottom:4px}
#v-pricing .prpt span{font-size:13px;color:var(--ink-2);line-height:1.6}
#v-pricing .prnote{text-align:center;font-size:13.5px;color:var(--ink-2);margin:18px 0 14px}
#v-pricing .prnote b{color:var(--amber)}
#v-pricing .prneed{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:center;margin:0 auto 16px;max-width:760px;padding:10px 16px;border-radius:12px;
  border:1px solid color-mix(in srgb,var(--amber) 60%,transparent);background:color-mix(in srgb,var(--amber) 12%,transparent);font-size:14px}
#v-pricing .prneed b{color:var(--ink)}#v-pricing .prneed a{color:var(--cyan);font-size:13px}
#v-pricing .prcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;align-items:stretch}
#v-pricing .prcard{position:relative;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px 18px 18px;min-width:0}
#v-pricing .prcard.hot{border-color:var(--cyan);box-shadow:0 0 0 1px color-mix(in srgb,var(--cyan) 40%,transparent),0 16px 40px -24px color-mix(in srgb,var(--cyan) 80%,transparent)}
#v-pricing .prcard.need{border-color:var(--amber);box-shadow:0 0 0 2px color-mix(in srgb,var(--amber) 70%,transparent),0 16px 40px -20px color-mix(in srgb,var(--amber) 80%,transparent)}
#v-pricing .prcard.mine{outline:2px dashed color-mix(in srgb,var(--fall) 60%,transparent);outline-offset:3px}
#v-pricing .prtag{position:absolute;top:-11px;left:18px;font-size:12px;font-weight:700;border-radius:999px;padding:2px 10px;background:var(--cyan);color:#04121a}
#v-pricing .prtag.full{background:var(--violet);color:#fff}
#v-pricing .prtag.need{background:var(--amber);color:#1a1203}
#v-pricing .prcard h2{margin:2px 0 2px;font-size:19px}
#v-pricing .prcard .who{font-size:13px;color:var(--ink-2);min-height:1.5em}
#v-pricing .prprice{margin:12px 0 2px;font-family:var(--mono);font-size:30px;font-weight:700;line-height:1.1}
#v-pricing .prprice small{font-size:14px;font-weight:500;color:var(--ink-2);font-family:inherit}
#v-pricing .prprice.free{font-family:inherit;font-size:26px}
#v-pricing .prgo{margin:14px 0 12px;height:40px;border-radius:10px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);font-size:14.5px;font-weight:700;cursor:pointer}
#v-pricing .prcard.hot .prgo,#v-pricing .prgo.pri{background:var(--cyan);color:#04121a;border-color:transparent}
#v-pricing .prcard.need .prgo.pri{background:var(--amber);color:#1a1203}
#v-pricing .prgo[disabled]{opacity:.6;cursor:default}
#v-pricing .prfs{list-style:none;margin:0;padding:0;font-size:13.5px;display:grid;gap:6px}
#v-pricing .prfs li{display:flex;justify-content:space-between;gap:8px;border-bottom:1px dashed var(--line);padding-bottom:5px}
#v-pricing .prfs li span:last-child{font-family:var(--mono);color:var(--ink-2);white-space:nowrap}
#v-pricing .prfs li.all span:last-child{color:var(--fall)}
#v-pricing .prfs li.none span:last-child{color:var(--ink-3)}
#v-pricing .prfs li.hl{background:color-mix(in srgb,var(--amber) 16%,transparent);border-radius:6px;padding:2px 6px}
#v-pricing .prfs .qh{border:0;padding:6px 0 0;color:var(--ink-2);font-size:12.5px}
#v-pricing .prmore{display:block;margin:18px auto 0;height:38px;padding:0 20px;border-radius:10px;border:1px solid var(--line-2);background:transparent;color:var(--cyan);font-size:14px;cursor:pointer}
#v-pricing .prfull{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:6px 14px 14px;overflow-x:auto}
#v-pricing .prfull[hidden]{display:none}
#v-pricing .prfull table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-pricing .prfull th,#v-pricing .prfull td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:center}
#v-pricing .prfull th:first-child,#v-pricing .prfull td:first-child{text-align:left}
#v-pricing .prfull tr.cat td{font-weight:700;color:var(--ink);background:var(--panel-2);text-align:left}
#v-pricing .prfull .y{color:var(--fall)}#v-pricing .prfull .n{color:var(--ink-3)}
#v-pricing .prlegal{margin-top:22px;font-size:12.5px;color:var(--ink-2);line-height:1.75;border-top:1px solid var(--line);padding-top:12px}
@media (max-width:900px){#v-pricing .prpts{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:520px){#v-pricing .prpts{grid-template-columns:minmax(0,1fr)}#v-pricing .prhero h1{font-size:23px}}`);

  const POINTS = [
    ['資金往哪裡跑', '每天盤後整理族群資金流向、輪動時鐘與資金去向，一眼看出錢在追哪一群。'],
    ['產業鏈剖析', '上中下游剖析圖、供應鏈關聯圖，點零件就看得到供應商與個股。'],
    ['個股多週期技術面', 'K 線、多週期同看、營收／獲利／籌碼分頁與規則式 AI 分析。'],
    /* 2026-10-06（DECISIONS #326）：盤中即時只給管理者帳號，不再當成方案權益宣傳（原本這格寫「盤中即時：盤中報價與分時走勢…」）*/
    ['自選清單同步', '自選清單最多五頁，登入後跨裝置同步。'],
  ];
  function paint() {
    const v = view('v-pricing'); if (!v) return;
    const plans = tidy(S.plans || FALLBACK);
    const paid = plans.filter((p) => tierOf(p) === 'paid');
    const sums = new Map(plans.map((p) => [p.id, summary(p)]));
    const needF = S.need && F() ? F().byId(S.need) : null;
    const needIds = needF ? plans.filter((p) => tierOf(p) !== 'guest' && unlocks(p, needF)).map((p) => p.id)
      : S.pick && plans.some((p) => p.id === S.pick) ? [S.pick] : [];   // #pricing/plan/<id>：額度卡的「升級 Plus／Pro →」點過來，標那一張
    const hot = paid[0] ? paid[0].id : null;
    let full = null;
    if (paid.length > 1) { full = paid.slice().sort((a, b) => sums.get(b.id).n - sums.get(a.id).n)[0].id; if (full === hot) full = paid[paid.length - 1].id; }
    const me = myPlan();
    v.innerHTML = `
      <div class="prhero"><h1>選一個適合你的方案</h1>
        <p>從資金流向、產業鏈到個股技術面，一個網站看完台股輪動。免費就能用大部分功能，付費方案開放更多分析與更高的每日瀏覽次數。</p></div>
      <div class="prpts">${POINTS.map(([t, d]) => `<div class="prpt"><b>${esc(t)}</b><span>${esc(d)}</span></div>`).join('')}</div>
      <p class="prnote"><b>目前為申請制，專人開通；線上付款即將推出。</b>${S.src === 'fallback' ? '　（暫時讀不到付費方案，以下只列免費的兩種）' : ''}</p>
      ${needF ? `<div class="prneed" id="prNeed" role="status">你剛剛點的 <b>「${esc(needF.name)}」</b>${needIds.length ? `在標成<b>「可解鎖」</b>的方案裡開放（或次數更多）` : '目前沒有方案開放更多，可以從右下角客服跟我們說'}<a href="#pricing" id="prNeedX">清除標示</a></div>` : ''}
      <div class="prcards" id="prCards">${plans.map((p) => card(p, sums.get(p.id), p.id === hot, p.id === full, me, needIds.includes(p.id), needF)).join('')}</div>
      <button type="button" class="prmore" id="prMore" aria-expanded="${S.full}">${S.full ? '收起完整權益' : '查看完整權益'}</button>
      <div class="prfull" id="prFull" ${S.full ? '' : 'hidden'}>${S.full ? table(plans) : ''}</div>
      <div class="prlegal">本網站提供的是資料整理與視覺化工具，<b>不是證券投資顧問</b>，不提供個股買賣建議，所有內容僅供參考，投資請自行判斷並承擔風險。
        方案內容與價格以專人開通時的確認為準；申請送出不會扣款。詳見 <a href="#disclaimer">免責聲明</a>、<a href="#terms">使用條款</a>、<a href="#privacy">隱私權政策</a>。</div>`;
    v.querySelector('#prMore').onclick = () => { S.full = !S.full; paint(); if (S.full) { const t = document.getElementById('prFull'); if (t) t.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } };
    v.querySelectorAll('.prgo[data-go]').forEach((b) => { b.onclick = () => go(plans.find((p) => p.id === b.dataset.go)); });
    if (needIds.length) { const c = v.querySelector(`.prcard[data-plan="${CSS.escape(needIds[0])}"]`); if (c && c.scrollIntoView) setTimeout(() => c.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 60); }
  }
  function card(p, s, hot, full, me, need, needF) {
    const t = tierOf(p), pr = priceOf(p), isMine = me.id === p.id;
    const who = t === 'guest' ? '不用登入，打開就能看' : t === 'free' ? '用 Google 帳號登入即可' : '進階分析與更高的每日次數';
    const price = pr.free ? '<div class="prprice free">免費</div>' : pr.tbd ? '<div class="prprice free">價格待定</div>' : `<div class="prprice">NT$ ${pr.amount.toLocaleString('en-US')}<small>${esc(pr.unit)}</small></div>`;
    let btn;
    if (isMine) btn = `<button type="button" class="prgo" disabled>目前方案</button>`;
    else if (t === 'guest') btn = `<button type="button" class="prgo" disabled>免費使用</button>`;
    else if (t === 'free') btn = me.tier === 'guest' ? `<button type="button" class="prgo${need ? ' pri' : ''}" data-go="${esc(p.id)}">免費註冊／登入</button>` : `<button type="button" class="prgo" disabled>已包含</button>`;
    else btn = `<button type="button" class="prgo pri" data-go="${esc(p.id)}">申請訂閱</button>`;
    const dq = t === 'guest' ? '' : `<li class="${Number.isInteger(p.dq) ? '' : 'all'}" data-dq><span>研究額度（個股頁、剖析圖、付費分頁）</span><span>${esc(dqTxt(p))}</span></li>`;
    const lines = s.lines.map((l) => `<li class="${l.k === l.t ? 'all' : l.k === 0 ? 'none' : ''}"><span>${esc(l.name)}</span><span>${l.k === l.t ? '全部' : l.k === 0 ? '不開放' : l.k + '／' + l.t + ' 項'}</span></li>`).join('');
    const q = s.q.length ? s.q.map((x) => `<li class="${needF && x.id === needF.id ? 'hl' : ''}"><span>${esc(x.name)}</span><span>${esc(x.txt)}</span></li>`).join('') : '<li class="all"><span>所有功能</span><span>不限</span></li>';
    const tag = need ? `<span class="prtag need">${needF ? '可解鎖' : '建議升級'}</span>` : hot ? '<span class="prtag">最受歡迎</span>' : full ? '<span class="prtag full">功能最齊</span>' : '';
    return `<div class="prcard${hot ? ' hot' : ''}${need ? ' need' : ''}${isMine ? ' mine' : ''}" data-plan="${esc(p.id)}" data-tier="${t}">
      ${tag}<h2>${esc(showName(p))}</h2><div class="who">${esc(who)}</div>
      ${price}${btn}
      <ul class="prfs">${lines}${s.watch != null ? `<li data-w="tabs"><span>自選清單分頁</span><span>${s.watch ? (s.watch >= s.wmax ? '不限' : s.watch + ' 頁') : '不開放'}</span></li>` : ''}${s.size != null && s.watch ? `<li data-w="size"><span>每頁自選檔數</span><span>${s.size >= s.smax ? '不限' : s.size + ' 檔'}</span></li>` : ''}
        <li class="qh"><span>每日瀏覽次數</span><span></span></li>${dq}${q}</ul></div>`;
  }
  function table(plans) {
    const Ft = F(); if (!Ft) return '';
    const head = `<tr><th>功能</th>${plans.map((p) => `<th>${esc(showName(p))}</th>`).join('')}</tr>`;
    const cell = (p, f) => {
      if (f.kind === 'limit') { const v = val(p, f); return `<td>${v ? (f.opts && v >= f.max ? '不限' : v + ' ' + (f.unit || '頁')) : '—'}</td>`; }
      if (!on(p, f)) return '<td class="n" aria-label="沒有">—</td>';
      const n = limOf(p, f);
      return n === Infinity ? '<td class="y" aria-label="有">✓</td>' : `<td class="y">每日 ${n} 次</td>`;
    };
    let rows = '';
    Ft.cats.filter((c) => c.id !== 'grp').forEach((c) => {
      const fs = Ft.inCat(c.id).filter((f) => !f.adminOnly); if (!fs.length) return;   // 只有管理者有的不列（DECISIONS #326）
      rows += `<tr class="cat"><td colspan="${plans.length + 1}">${esc(c.name)}</td></tr>` + fs.map((f) => `<tr data-f="${esc(f.id)}"><td title="${esc(f.desc)}">${esc(f.name)}</td>${plans.map((p) => cell(p, f)).join('')}</tr>`).join('');
    });
    const g = Ft.inCat('grp');
    rows += `<tr class="cat"><td colspan="${plans.length + 1}">族群觀測</td></tr><tr><td>可展開的族群</td>${plans.map((p) => {
      const off = Object.keys(p.feats || {}).filter((k) => k.startsWith('grp.') && p.feats[k] === false).length + Object.keys(p.lims || {}).filter((k) => k.startsWith('grp.') && p.lims[k] === 0).length;
      return `<td>${off === 0 ? '全部' : g.length ? (g.length - off) + '／' + g.length : '關閉 ' + off + ' 個'}</td>`;
    }).join('')}</tr>`;
    return `<table id="prTable"><thead>${head}</thead><tbody>${rows}</tbody></table>`;
  }
  /* 訂閱鈕：免費卡＝登入；付費卡＝訂閱申請（要先登入：沒登入直接跳 Google 登入，登入回來再按一次）*/
  function go(p) {
    if (!p) return;
    if (p.demo) { dialog(`<h3>${esc(showName(p))} 方案</h3><p>${esc(showName(p))} 方案即將開放（${esc(dqTxt(p) === '不限' ? '不限次數' : dqTxt(p))}），價格待定。想先預約可以從右下角「客服」留言給我們。</p><div class="row2"><button type="button" class="pri" data-close>知道了</button></div>`); return; }
    const a = A();
    const u = a && a.on() ? a.user() : null;
    if (tierOf(p) === 'free') { if (a && a.on()) a.login(); else toast('會員登入功能尚未開放'); return; }
    if (!a || !a.on()) {
      dialog(`<h3>訂閱申請</h3><p>線上申請暫時無法使用（會員功能尚未開放）。請從右下角「客服」寄信給我們，註明想要的方案「${esc(showName(p))}」。</p><div class="row2"><button type="button" class="pri" data-close>知道了</button></div>`);
      return;
    }
    if (!u) { toast('申請訂閱要先登入 —— 登入完成後再按一次「申請訂閱」'); a.login(); return; }
    const pr = priceOf(p);
    dialog(`<h3>訂閱申請：${esc(showName(p))}</h3>
      <p><b>目前為申請制，專人開通；線上付款即將推出。</b>送出後我們會用下面的 email 跟你確認方案與付款方式，<b>送出不會扣款</b>。</p>
      <p>方案價格：<b>${pr.tbd ? '價格待定（專人跟你確認）' : `NT$ ${pr.amount.toLocaleString('en-US')}${esc(pr.unit)}`}</b></p>
      <label for="subMail">聯絡 email</label><input type="email" id="subMail" value="${esc(u.email || '')}" autocomplete="email" maxlength="200">
      <label for="subNote">備註（選填，例如需要發票抬頭）</label><input type="text" id="subNote" maxlength="300">
      <div class="msg" id="subMsg" role="status"></div>
      <div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="subSend">送出申請</button></div>`, (d) => {
      d.querySelector('#subSend').onclick = async () => {
        const msg = d.querySelector('#subMsg'), btn = d.querySelector('#subSend');
        const contact = d.querySelector('#subMail').value.trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) { msg.className = 'msg bad'; msg.textContent = '請填正確的 email'; return; }
        btn.disabled = true; msg.className = 'msg'; msg.textContent = '送出中…';
        /* 週期跟著範本（月或年）；後端 /v1/subscribe/request 只收 month／year，一次付清的範本當「月」送（專人開通時再確認）*/
        const per = p.period === 'year' ? 'year' : 'month';
        const j = await call('/v1/subscribe/request', { plan: p.id, period: per, contact, note: d.querySelector('#subNote').value.trim() });
        btn.disabled = false;
        if (j && j._s === 200 && j.ok) {
          d.querySelector('.box').innerHTML = `<h3>已收到你的申請</h3><p>方案：<b>${esc(showName(p))}</b>（${per === 'year' ? '年繳' : '月繳'}）<br>我們會寄信到 <b>${esc(contact)}</b> 跟你確認，開通後重新整理網頁就會生效。</p><div class="row2"><button type="button" class="pri" data-close>好</button></div>`;
        } else {
          msg.className = 'msg bad';
          msg.textContent = j && j._s === 429 ? '今天已經送過好幾次了，我們會盡快處理，請稍候' : j && j._s === 401 ? '登入已過期，請重新登入' : '送出失敗，請稍後再試，或從右下角「客服」寄信給我們';
        }
      };
    });
  }

  async function show() {
    const v = view('v-pricing'); if (!v) return;
    if (!S.plans) { v.innerHTML = '<div class="card" style="margin-top:16px"><p class="muted">載入方案…</p></div>'; await load(); }
    if ((location.hash || '').startsWith('#pricing')) paint();
  }
  /* #pricing／#pricing/need/<功能鍵>：後者把「能解鎖這個功能」的方案標出來（鎖頭與「今日已用完」上的「升級查看」帶過來的）*/
  routes.push((head, rest) => {
    if (head !== 'pricing') return null;
    const m = /^need\/(.+)$/.exec(Array.isArray(rest) ? rest.join('/') : String(rest || ''));
    let need = '';
    if (m) { try { need = decodeURIComponent(m[1]); } catch (e) { need = ''; } }
    if (!need) { const mh = /^#pricing\/need\/([^?]+)/.exec(location.hash || ''); if (mh) { try { need = decodeURIComponent(mh[1]); } catch (e) { need = ''; } } }
    S.need = need;
    const mp = /^#pricing\/plan\/([a-z0-9_-]{1,20})/.exec(location.hash || '');
    S.pick = mp ? mp[1] : '';
    show(); return 'v-pricing';
  });
  /* 登入／登出、權限換了 → 「目前方案」那張卡要跟著換 */
  const again = () => { if ((location.hash || '').startsWith('#pricing') && S.plans) paint(); };
  window.addEventListener('tw:perm', again);
  window.addEventListener('tw:account', () => { S.plans = null; if ((location.hash || '').startsWith('#pricing')) show(); });
  /* 給 site/qcard.js：方案清單（同步；還沒抓過回 null）、確保抓過一次、哪些方案開放某個功能（訪客除外，順序＝方案卡順序）*/
  const ensure = () => (S.plans ? Promise.resolve(S.plans) : load().then(() => S.plans));
  const unlockers = (fid) => { const f = F() && F().byId(fid); if (!S.plans || !f) return null; return S.plans.filter((p) => tierOf(p) !== 'guest' && on(p, f)).map((p) => ({ id: p.id, name: showName(p), dq: Number.isInteger(p.dq) ? p.dq : null })); };
  window.TwPricing = { reload: () => { S.plans = null; return show(); }, priceOf, state: () => ({ src: S.src, plans: S.plans, need: S.need, pick: S.pick }),
    plans: () => S.plans, ensure, unlockers };
})();
