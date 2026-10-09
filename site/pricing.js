/* ============================================================================
   訂閱頁 #pricing ＋ 帳號選單的方案徽章（sub-v1，2026-10-05）
   ----------------------------------------------------------------------------
   ★ pricing-v2（2026-10-07）：照 Andy 給的範本重做 —— 資訊提示列、月繳／年繳切換（年繳 省 X%）、三張方案卡（圖示／定位句／價格／
     適合誰／打勾清單／行動鈕）、卡片下方「方案功能比較表」。卡上文字全部讀後端範本（worker.js「方案卡呈現區塊」），細節見「方案資料」段。
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
  /* 訪客／註冊會員／方案名。來源：perm.js 的 state()（＝/v1/perm/me 的結果）*/
  function myPlan() {
    const a = A(), u = a && a.on() ? a.user() : null;
    const st = P() ? P().state() : { who: 'guest', plan: '', planName: '' };
    if (!u) return { id: 'guest', label: '訪客', tier: 'guest' };
    /* 站主（/v1/me 的 owner 旗標，perm.js 同一個判定）：所有功能不受限，徽章寫「站主」、方案頁每張卡都是「已包含」 */
    if (u.owner) return { id: 'owner', label: '站主', tier: 'owner' };
    /* 2026-10-10（同步稽核 7-2）：「免費會員」→「註冊會員」，跟手機帳號選單、方案範本、方案卡、升級卡同一個叫法 */
    if (!st.plan || st.plan === 'free' || st.who === 'guest') return { id: 'free', label: '註冊會員', tier: 'free' };
    return { id: st.plan, label: st.planName || st.plan, tier: 'paid' };
  }
  /* 付費方案的高低順序＋色系：跟方案頁 paint() 同一套（依折合每月價格由低到高，色系 藍→紫→琥珀→綠），
     不寫死 plus／pro —— 管理區新增方案時順序與顏色自動跟著走。 */
  const AUTO_C = ['blue', 'violet', 'amber', 'green'];
  function paidSorted() {
    return tidy(S.plans || FALLBACK).filter((p) => tierOf(p) === 'paid' && p.public !== false).map((p, i) => [p, i])
      .sort((a, b) => monthEq(a[0]) - monthEq(b[0]) || a[1] - b[1]).map((x) => x[0]);
  }
  function colorOf(id) {
    const paid = paidSorted(), i = paid.findIndex((p) => p.id === id);
    if (i >= 0) return paid[i].color || AUTO_C[i % 4];
    return /pro/i.test(id) ? 'violet' : 'blue';   // 方案清單還沒到：先依名稱猜，到了 tw:plans 會重畫
  }
  /* 方案層級（0＝免費，付費＝折合每月價格）：「已包含／目前方案／升級」用它比高低 */
  const rankOf = (p) => (tierOf(p) === 'guest' ? -1 : tierOf(p) === 'free' ? 0 : monthEq(p));
  window.TwPlanBadge = function () {
    const m = myPlan();
    const c = m.tier === 'paid' ? ' pc-' + colorOf(m.id) : '';
    return `<a href="#pricing" class="planbadge t-${m.tier}${c}" data-plan="${esc(m.id)}" title="查看方案與升級">${esc(m.label)}</a>`;
  };
  css('planBadgeCss', `
.planbadge{display:inline-flex;align-items:center;height:22px;padding:0 9px;border-radius:999px;font-size:12px;font-weight:700;text-decoration:none;white-space:nowrap;
  border:1px solid var(--line-2);color:var(--ink-2);background:var(--panel-3)}
.planbadge.t-free{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 45%,transparent)}
.planbadge.t-paid{--pc:var(--pl-blue,#4f8cff);color:var(--pc);background:color-mix(in srgb,var(--pc) 16%,transparent);border-color:color-mix(in srgb,var(--pc) 55%,transparent)}
.planbadge.t-paid.pc-blue{--pc:#4f8cff}.planbadge.t-paid.pc-violet{--pc:var(--violet)}.planbadge.t-paid.pc-amber{--pc:var(--amber)}.planbadge.t-paid.pc-green{--pc:var(--lime)}
:root[data-theme="light"] .planbadge.t-paid.pc-blue{--pc:#2b65d9}
.planbadge.t-owner{color:var(--amber);background:color-mix(in srgb,var(--amber) 16%,transparent);border-color:color-mix(in srgb,var(--amber) 55%,transparent)}
/* ★ 10-07 根因：account.js 的「.acctmenu a{display:block;width:100%;padding:9px 10px}」是給選單項目用的，
   特異度（0,1,1）高過 .planbadge（0,1,0），徽章被撐成整列寬的方塊，把名字擠成「Ha…」還溢出選單。這裡用更高特異度蓋回膠囊。 */
.acctmenu .mh .planbadge{display:inline-flex;flex:none;width:auto;height:20px;padding:0 8px;font-size:11.5px;line-height:1;border-radius:999px;text-align:center}
.acctmenu .mh .planbadge:hover{background:color-mix(in srgb,var(--pc,var(--ink-2)) 26%,transparent)}
.acctmenu .mh.mhx{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 10px;align-items:center}
.acctmenu .mh.mhx .av{grid-row:span 2;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--violet);color:#fff;font-weight:700;font-size:16px}
.acctmenu .mh.mhx .nm{display:flex;align-items:center;gap:8px;min-width:0}
.acctmenu .mh.mhx .nm b{display:block;min-width:0;max-width:16em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.acctmenu .mh.mhx small{grid-column:2}
.acctmenu:has(.mh.mhx){min-width:260px;max-width:min(360px,calc(100vw - 16px))}`);

  // ------------------------------------------------------------------ 方案資料
  /* ★ pricing-v2（2026-10-07，Andy：「圖一是我訂閱頁面想看到的範本，幫我做一份」）：
     · 卡片＝註冊會員（Free）＋管理者標為公開（public）的付費範本，依價格由低到高排；**訪客不畫成卡片**（訪客不是方案，是沒登入）。
     · 卡上的文字（定位句、頂端標籤、適合誰、打勾清單、圖示、色系）讀後端範本的 pres 欄位（worker.js「方案卡呈現區塊」），
       欄位名照 docs/plan_presets_1007.json（tiers[].{key,name,price{month,year},badge,tagline,fit_title,fit_desc,highlights[],feats,lims,watch}）；
       那份格式的物件也可以直接丟進來（fromPreset 會轉成後端的形狀），CEO 灌範本前可以先用 ?demo=plans 看效果。
     · 沒填的欄位有 fallback：清單＝依開關與次數自動產生（「功能名・每日 N 次」）、圖示與色系依順序（禮物／閃電／皇冠、中性／藍／紫）、
       頂端標籤沿用舊規則（第一個付費＝最受歡迎、開最多功能＝功能最齊）。**價格不編**：拿不到寫「洽詢」。
     · 月繳／年繳：至少一個付費範本同時有月價與年繳總價才出現切換；「省 X%」＝ 1 − 年價 ÷（月價 × 12），四捨五入。
       admin-v3 拿掉切換的理由（每個範本只有一種週期）仍成立 —— 只有一種週期的範本不受切換影響，照它自己的週期顯示。
     · 卡片下方「方案功能比較表」（Andy 10-07 02:28：參考 stockintelli 下方的比較表）：列＝features.js 的功能（依類別分組），
       欄＝每張卡；**只列方案之間有差異的功能**，全部一樣的收成一行「其他基礎功能」。不手寫一份 —— 管理者在 #admin/perm 改什麼這裡就變。 */
  const FALLBACK = [
    { id: 'guest', name: '訪客', builtin: true, feats: {}, lims: {}, price: 0 },
    { id: 'free', name: '註冊會員', builtin: true, feats: {}, lims: {}, price: 0 },
  ];
  /* ?demo=plans：示範資料＝docs/plan_presets_1007.json（claude/plan-tiers 分支，CEO 10-07 給的方案內容）的 free／plus／pro 三層
     （訪客不是方案、不畫卡）。網站只部署 site/，讀不到 docs/，所以這裡放一份副本：
     · feats 只抄「關掉的」（其餘預設就是開，效果一樣）；文字欄位逐字照抄。
     · CEO 10-07 訊息蓋過 JSON 的三個數字：自選每頁檔數 Plus 30→50、Pro 50→200；研究瀏覽全站共用鍵 quota.all（註冊會員 10、Plus 50、Pro 不限）。
       對應的兩行打勾文字跟著改，免得同一張卡上下數字對不起來。CEO 把正式範本灌進後端之後，這份副本就只剩示範用途。
     只影響這個分頁、不寫任何地方。 */
  const DEMO = [
    { key: 'free', name: '註冊會員', price: { month: 0, year: 0 }, badge: null, tagline: '免費註冊，養成每天看盤後的習慣',
      fit_title: '適合開始建立研究習慣', fit_desc: '每天花 5 分鐘看資金往哪個族群跑、族群貴不貴，再挑幾檔點進去看營收、法人與產業鏈位置。先熟悉流程，再決定要不要更深。',
      highlights: ['研究瀏覽・每日 10 次（個股、剖析圖、題材剖析）', '資金流向・輪動時鐘・桑基圖・完整功能', '產業鏈剖析圖（2D）・每日 10 張', '自選清單・1 頁 10 檔', 'ETF 一覽・配息行事曆・財經日曆', 'Email 客服・一般順序回覆'],
      feats: { 'ind.3d': false, 'stock.k_min': false, 'stock.mtf': false, 'stock.ind': false, 'stock.draw': false, 'live.tick': false, 'etf.returns': false, 'watch.tabs': 1 },
      lims: { 'quota.all': 10, 'stock.page': 10, 'ind.diagram': 10, 'heat.detail': 10, 'ind.rel': 10, 'ind.groups': 10 }, watch: { tabs: 1, size: 10 } },
    { key: 'plus', name: 'Plus', price: { month: 299, year: 2990 }, badge: '最受歡迎', tagline: '每天主動研究，工具一次到位',
      fit_title: '適合每天主動研究', fit_desc: '每天追蹤好幾個族群與自選股：用 3D 剖析圖看懂零件與供應商、四週期同看與畫線工具省下來回切換的時間，5 頁自選清單分題材管理。',
      highlights: ['研究瀏覽・每日 50 次', '3D 剖析圖・完整功能', '四週期同看・畫線工具・指標自訂', '自選清單・5 頁、每頁 50 檔', 'ETF 報酬比較（自選 8 檔）', '客服優先回覆（只限功能與資料說明）'],
      feats: { 'stock.k_min': false, 'live.tick': false, 'watch.tabs': 5 },
      lims: { 'quota.all': 50, 'stock.page': 50, 'ind.diagram': 50, 'heat.detail': 50, 'ind.rel': 50, 'ind.groups': 50 }, watch: { tabs: 5, size: 50 } },
    { key: 'pro', name: 'Pro', price: { month: 549, year: 5268 }, badge: '功能最齊', tagline: '不限次數，自選清單每天幫你整理好',
      fit_title: '適合追蹤多個題材與大量自選股', fit_desc: '研究頁不限次數、自選清單不限頁數；加上「自選清單日報」把你追蹤的股票今天發生了什麼（營收、法人、籌碼、事件）彙整成一頁，省下逐檔翻的時間。',
      highlights: ['研究瀏覽・不限次數', 'Plus 全部功能', '自選清單・不限頁數（每頁 200 檔）', '自選清單日報：營收／法人／籌碼／事件變化一覽（開發中）', '自設條件提醒（開發中）', '剖析圖高解析匯出（開發中）'],
      feats: { 'stock.k_min': false, 'live.tick': false, 'watch.tabs': 5 },
      lims: { 'quota.all': null, 'stock.page': null, 'ind.diagram': null, 'heat.detail': null, 'ind.rel': null, 'ind.groups': null }, watch: { tabs: null, size: 200 } },
  ];
  /* ★ 2026-10-08 全站權限矩陣（docs/perm_matrix_1008.md §5）：示範卡的打勾清單、開關、次數改讀 site/plan_presets.js（同一份建議方案），
     不再在這裡抄一份會過期的副本 —— 矩陣改了，套用建議方案寫進後端的、跟示範卡看到的是同一份。讀不到 presets 才用上面的舊副本。*/
  (function () {
    const pr = window.TW_PLAN_PRESETS; if (!pr || !Array.isArray(pr.tiers)) return;
    DEMO.forEach((d) => { const t = pr.tiers.find((x) => x.key === d.key); if (!t) return;
      if (t.meta && Array.isArray(t.meta.highlights)) d.highlights = t.meta.highlights.slice();
      d.feats = Object.assign({}, d.feats, t.feats || {});
      d.lims = Object.assign({}, t.lims || {}, { 'quota.all': t.dq == null ? null : t.dq }); });
  })();
  const isDemo = () => /[?&]demo=plans\b/.test(location.search || '');
  /* plan_presets 格式（price{month,year}、feats、lims、watch{tabs,size}）→ 後端 plans/public 的形狀（price＝月價、price_year＝年繳總價、period）。
     watch 物件保留在 p.watch 給比較表寫「N 頁・每頁 M 檔」；tabs 是整數時同步進 feats['watch.tabs']（features.js 的開關鍵）。
     lims 的 null＝不限（明示），照 JSON 的約定保留。 */
  function fromPreset(t) {
    if (!t || typeof t !== 'object') return null;
    const pr = t.price && typeof t.price === 'object' ? t.price : null;
    const feats = Object.assign({}, t.feats || {});
    const w = t.watch && typeof t.watch === 'object' ? t.watch : Number.isInteger(t.watch) ? { tabs: t.watch } : null;
    if (w && Number.isInteger(w.tabs)) feats['watch.tabs'] = w.tabs;
    const id = t.id || t.key;
    return Object.assign({}, t, { id, builtin: id === 'free' || id === 'guest', feats, lims: t.lims || {}, watch: w,
      price: pr ? (Number.isInteger(pr.month) ? pr.month : null) : t.price,
      price_year: pr ? (Number.isInteger(pr.year) ? pr.year : null) : t.price_year,
      period: pr ? (Number.isInteger(pr.month) || !Number.isInteger(pr.year) ? 'month' : 'year') : t.period });
  }
  /* layout：'cards'＝卡片＋下方比較表（預設）／'merged'＝合併表（方案卡當比較表的欄頭；Andy 10-07「上方的訂閱與下方的表格結合在一起的版本」）。
     網址 ?layout=merged 直接開合併版；頁上切換只記在這一頁（重新整理回預設，跟月／年切換同一個規矩）。 */
  const S = { plans: null, src: 'fallback', loading: null, need: '', pick: '', per: '', layout: /[?&]layout=merged\b/.test(location.search || '') ? 'merged' : 'cards', look: new Map() };
  /* ★ 合併 quota 分支（2026-10-07 每日額度，docs/quota_plan.md）：Plus（每日 50）／Pro（不限）由 account-api 第一次啟動時種成付費範本（SEED_PLANS）。
     方案卡仍然只畫後端有的範本（Andy 10-05：不編卡）。唯一例外是示範開關 ?demo=quota／quota-free／lock：後端還沒有 plus／pro 時補兩張「價格待定」的示意卡，
     讓額度卡的「升級 Plus／Pro →」點過來有東西可看。（跟上面 ?demo=plans 是兩個不同的示範，互不影響。） */
  const QDEMO = /[?&]demo=(quota|quota-free|lock)(&|$)/.test(location.search);
  const QDEMO_PLANS = [{ id: 'plus', name: 'Plus', builtin: false, feats: { 'watch.tabs': 5, 'watch.size': 50 }, lims: {}, price: 0, period: 'month', dq: 50, demo: true },
    { id: 'pro', name: 'Pro', builtin: false, feats: { 'watch.tabs': 50, 'watch.size': 200 }, lims: {}, price: 0, period: 'month', dq: null, demo: true }];
  const tierOf = (p) => (p.id === 'guest' ? 'guest' : p.id === 'free' ? 'free' : 'paid');
  /* 免費卡的名稱：管理者設過方案卡（有定位句或清單）就用範本名稱（例 Free），沒設維持「註冊會員」（後端預設名「免費會員（預設）」不適合上卡）*/
  const showName = (p) => (p.id === 'guest' ? '訪客' : p.id === 'free' ? (p.tagline || (p.highlights || []).length ? p.name : '註冊會員') : p.name);
  /* 排序＋去重：訪客、註冊會員固定在前；付費依後端順序；同一個 id 只留第一個 */
  function tidy(list) {
    const seen = new Set(), out = [];
    const all = (Array.isArray(list) ? list : []).map((p) => (p && p.price && typeof p.price === 'object' ? fromPreset(p) : p));
    const g = all.find((p) => p && p.id === 'guest') || FALLBACK[0], f = all.find((p) => p && p.id === 'free') || FALLBACK[1];
    [g, f, ...all.filter((p) => p && p.id !== 'guest' && p.id !== 'free')].forEach((p) => { if (p && p.id && !seen.has(p.id)) { seen.add(p.id); out.push(p); } });
    if (QDEMO) QDEMO_PLANS.forEach((p) => { if (!seen.has(p.id)) { seen.add(p.id); out.push(p); } });
    return out;
  }
  async function load() {
    if (S.loading) return S.loading;
    S.loading = (async () => {
      if (isDemo()) { S.plans = tidy(DEMO.map(fromPreset)); S.src = 'demo'; return; }
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
  const int = (v) => (Number.isInteger(v) && v > 0 ? v : v != null && isFinite(+v) && +v > 0 ? Math.round(+v) : null);
  /* 一個範本的價目：{ month, year, once }（整數 NT$ 或 null）。period=month → 月價＝price、年價＝price_year；
     period=year 的舊範本 → 年價＝price_year 或 price；period=once → 一次價。0／空＝沒有（付費卡寫「洽詢」，不編數字）*/
  function prices(p) {
    if (tierOf(p) !== 'paid') return { free: true };
    const per = p.period || 'month';
    return { month: per === 'month' ? int(p.price) : null, year: int(p.price_year) || (per === 'year' ? int(p.price) : null), once: per === 'once' ? int(p.price) : null };
  }
  const saveOf = (p) => { const x = prices(p); return x.month && x.year && x.year < x.month * 12 ? Math.round((1 - x.year / (x.month * 12)) * 100) : 0; };
  const nt = (n) => n.toLocaleString('en-US');
  /* 在「per」這個切換狀態下要顯示什麼：{ amount, unit, note, period（送申請用）}；amount null＝洽詢 */
  /* 10-07 Andy「價格旁備註一天多少錢」：口徑一律「一年總價 ÷ 365」（月繳＝月價×12÷365、年繳＝年價÷365），四捨五入到小數 1 位；
     算出來而不是寫死，後台改價、切月／年都會跟著變。一次付清與免費不給（沒有「一年」可攤）。 */
  const perDay = (r) => (r && !r.free && r.amount != null && !r.once ? Math.round((r.period === 'year' ? r.total : r.amount * 12) / 365 * 10) / 10 : null);
  const dayTag = (r) => { const d = perDay(r); return d == null ? '' : `<small class="prday">每天約 NT$ ${d.toFixed(1)}</small>`; };
  function priceAt(p, per) {
    const r = priceAt0(p, per);
    if (r.amount != null && r.unit === '（一次）') r.once = true;
    return r;
  }
  function priceAt0(p, per) {
    const x = prices(p);
    if (x.free) return { free: true };
    if (x.once) return { amount: x.once, unit: '（一次）', note: '一次付清', period: 'month' };
    if (per === 'year' && x.year) return x.month ? { amount: Math.round(x.year / 12), unit: '／月', note: `年繳 NT$ ${nt(x.year)}（一次付清）`, period: 'year', total: x.year, mo: x.month, orig: x.year < x.month * 12 ? x.month * 12 : 0 } : { amount: x.year, unit: '／年', note: '年繳方案', period: 'year', total: x.year };
    if (x.month) return { amount: x.month, unit: '／月', note: per === 'year' ? '此方案僅提供月繳' : x.year && x.year < x.month * 12 ? `改年繳一年省 NT$ ${nt(x.month * 12 - x.year)}` : '按月計費', period: 'month' };
    if (x.year) return { amount: x.year, unit: '／年', note: per === 'month' ? '此方案僅提供年繳' : '年繳方案', period: 'year', total: x.year };
    /* 付費範本價格是 0／空 ＝還沒定價（Plus／Pro 種子就是 0）→ 寫「價格待定」，不寫 NT$ 0 讓人以為免費 */
    return { amount: null, unit: '', note: '價格待定，專人跟你確認', period: 'month', tbd: true };
  }
  /* 舊介面（TwPricing.priceOf）：{ amount, unit } —— 照範本自己的週期 */
  function priceOf(p) { const r = priceAt(p, p.period === 'year' ? 'year' : 'month'); return r.free ? { amount: 0, unit: '', free: true } : { amount: r.amount || 0, unit: r.unit, free: false, tbd: !!r.tbd }; }
  const monthEq = (p) => { const x = prices(p); return x.free ? 0 : x.month || (x.year ? x.year / 12 : x.once || Infinity); };
  /* 這個方案在某個功能上的值（沒寫＝預設）；上限：Infinity＝不限 */
  function val(p, f) { const v = (p.feats || {})[f.id]; if (f.kind === 'limit') return Number.isInteger(v) ? v : v === false ? 0 : F() && F().defOf ? F().defOf(f, p.id) : f.def; return typeof v === 'boolean' ? v : F() && F().defOf ? F().defOf(f, tierOf(p) === 'paid' ? p.id : tierOf(p)) : f.def; }
  const limOf = (p, f) => { const v = (p.lims || {})[f.id]; return Number.isInteger(v) && v >= 0 ? v : Infinity; };
  const on = (p, f) => { if (limOf(p, f) === 0) return false; const v = val(p, f); return typeof v === 'number' ? v > 0 : v !== false; };
  const ltxt = (n) => (n === Infinity ? '不限' : n === 0 ? '不能看' : `每日 ${n} 次`);
  /* 研究額度（全站共用每日次數，鍵 quota.all）：兩種來源 —— 範本 lims['quota.all']（plan_presets 格式／?demo=plans）與後端欄位 plans.dq（quota 分支，null＝不限）。
     lims 有寫（含 null＝不限）就用 lims，沒寫才看 dq；兩個都沒有回 undefined（這個範本沒這項資料）。回 Infinity＝不限。 */
  function qAll(p) {
    if (tierOf(p) === 'guest') return undefined;
    if (p.lims && Object.prototype.hasOwnProperty.call(p.lims, 'quota.all')) { const n = p.lims['quota.all']; return Number.isInteger(n) && n >= 0 ? n : Infinity; }
    if (Object.prototype.hasOwnProperty.call(p, 'dq')) return Number.isInteger(p.dq) && p.dq >= 0 ? p.dq : Infinity;
    return undefined;
  }
  /* 功能清單（方案權益用）：族群觀測另算；adminOnly（盤中即時、1／5／15 分 K，DECISIONS #326）只有管理者帳號有，不算方案權益 */
  const boolFs = () => { const Ft = F(); return Ft ? Ft.list.filter((f) => f.kind === 'bool' && f.cat !== 'grp' && !f.adminOnly) : []; };
  /* 自選清單：preset 的 watch{tabs,size}（tabs null＝不限頁）優先；後端範本只有 watch.tabs（features.js 的 limit 開關），有 watch.size 就一起寫 */
  function watchCell(p) {
    const Ft = F(), wt = Ft && Ft.byId('watch.tabs');
    const w = p.watch && typeof p.watch === 'object' ? p.watch : null;
    const tabs = w ? w.tabs : wt ? val(p, wt) : null;
    const size = w ? w.size : Number.isInteger((p.feats || {})['watch.size']) ? p.feats['watch.size'] : null;
    if (tabs === 0) return { c: 'n', t: '—' };
    /* 分頁數開關的最大值（features.js：50 頁）＝「不限頁」（quota 分支 watch-v2：Pro 不限＝50 頁；每頁檔數照寫數字 200 檔） */
    const tt = tabs == null || (wt && wt.opts && tabs >= wt.max) ? '不限頁' : `${tabs} 頁`;
    const st = Number.isInteger(size) && size > 0 ? `・每頁 ${size} 檔` : '';
    return { c: 'v', t: tt + st };
  }
  /* 沒填打勾清單時自動產生：有次數上限的功能「名稱・每日 N 次」、自選分頁「最多 N 頁」、其餘一行總結 */
  function autoHl(p) {
    const Ft = F(); if (!Ft) return [];
    const out = [];
    Object.keys(p.lims || {}).map((k) => Ft.byId(k)).filter((f) => f && f.cat !== 'grp' && !f.adminOnly && val(p, f) !== false && limOf(p, f) > 0)
      .forEach((f) => out.push(`${f.name}・${ltxt(limOf(p, f))}`));
    const qa = qAll(p);
    /* ★ 2026-10-10 Andy：「不要寫"不開放" 幫我改成plus 會員 這樣比較親切」→ 這個方案沒開的項目，後面掛一顆會員膠囊寫「最低哪個方案有開」
       （{t, need}：卡片清單畫成「名稱＋★ Plus 會員」膠囊；方案名跟帳號選單「額度上限」面板同一支 needPlan，acctm4.js）。 */
    const need = (id, t) => ({ t, need: window.TwAcctM4 && window.TwAcctM4.needPlan ? window.TwAcctM4.needPlan(id, true) : '升級可用' });
    if (qa !== undefined) out.unshift(qa === Infinity ? '研究瀏覽・不限次數' : qa === 0 ? need('quota.all', '研究瀏覽') : `研究瀏覽・每日 ${qa} 次`);
    const wt = Ft.byId('watch.tabs'); if (wt) { const wc = watchCell(p); out.push(wc.c === 'n' ? need('watch.tabs', '自選清單') : `自選清單・${wc.t}`); }
    const fs = boolFs(), n = fs.filter((f) => on(p, f)).length;
    out.push(!Object.keys(p.lims || {}).length && n === fs.length ? '所有功能・不限' : n === fs.length ? '其他功能・不限次數' : `開放功能・${n}／${fs.length} 項`);
    return out;
  }
  /* 「我現在」在某功能上的狀態（給 need 標示用）：能不能看、上限 */
  function mine(f) { const P0 = P(); if (!P0) return { on: true, lim: Infinity }; return { on: P0.can(f.id), lim: P0.lim ? P0.lim(f.id) : Infinity }; }
  /* 這個方案能不能讓「我」在這個功能上變得更好（開得了、或次數更多）*/
  function unlocks(p, f) { const m = mine(f); if (!on(p, f)) return false; return !m.on || limOf(p, f) > m.lim; }

  // ------------------------------------------------------------------ 圖示（線條 SVG，currentColor 上色）
  const ICON = {
    gift: '<path d="M20 12v9H4v-9M2 7h20v5H2zM12 21V7M12 7H7.5a2.5 2.5 0 1 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 1 0 0-5C13 2 12 7 12 7z"/>',
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z" fill="currentColor"/>',
    crown: '<path d="M3 7l4.5 4L12 4l4.5 7L21 7l-2 12H5L3 7z" fill="currentColor"/>',
    star: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9L12 3z" fill="currentColor"/>',
    rocket: '<path d="M5 15c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9-.8-.8-2.1-.8-2.9-.1zM12 15l-3-3a22 22 0 0 1 2-4A13 13 0 0 1 22 2c0 2.7-.8 7.5-6 11a22 22 0 0 1-4 2zM9 12H4s.6-3 2-4c1.6-1.1 5 0 5 0M12 15v5s3-.6 4-2c1.1-1.6 0-5 0-5"/>',
    gem: '<path d="M6 3h12l4 6-10 12L2 9l4-6zM2 9h20M12 21 8 9l4-6 4 6-4 12"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    chart: '<path d="M3 3v18h18M7 15l4-4 3 3 6-6"/>',
  };
  const svgI = (k) => `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ICON.star}</svg>`;
  const CHECK = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="9" fill="currentColor"/><path d="M6 10.2l2.6 2.6L14.2 7.4" fill="none" stroke="var(--pr-on)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const INFO = '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><circle cx="10" cy="10" r="9" fill="var(--pl-blue)"/><path d="M10 9v5M10 6.2v.1" stroke="var(--pr-on)" stroke-width="2" stroke-linecap="round"/></svg>';

  // ------------------------------------------------------------------ 畫面
  /* 配色：跟著本站主題走。卡片底色＝面板色混一點方案色（深色主題 10～14%：深藍／深紫的卡；淺色主題同比例＝範本那種淡藍／淡紫）。
     方案色只有兩個新值（--pl-blue），取自 App.donut 的分類色盤第一色（深 #4f8cff／淺 #2f5fb3 再提亮一階 #2b65d9：對白底 5.6:1）；
     紫色直接用主題的 --violet。字一律 --ink 系，只有方案名、價格、適合誰標題、勾勾上方案色。 */
  css('subCoCss', `
.subdlg .box.subco{width:min(620px,100%);padding:0;overflow:hidden;display:flex;flex-direction:column}
.subco .coh{display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:2px 12px;align-items:center;padding:18px 22px;background:linear-gradient(120deg,color-mix(in srgb,var(--pc) 16%,var(--panel-2)),var(--panel-2))}
.subco .coh .ic{grid-row:span 2;width:44px;height:44px;border-radius:50%;display:grid;place-items:center;color:var(--pc);background:color-mix(in srgb,var(--pc) 18%,var(--panel))}
.subco .coh b{font-size:20px;color:var(--pc)}.subco .coh small{font-size:13px;color:var(--ink-2)}
.subco .coh button{grid-row:1/span 2;grid-column:3;width:32px;height:32px;border:0;border-radius:8px;background:transparent;color:var(--ink-2);font-size:20px;cursor:pointer}
.subco .cob{overflow:auto;padding:14px 22px 6px;min-height:0}
.subco .cop small{display:block;font-size:13px;color:var(--ink-2)}
.subco .cop .big{font-size:28px;font-weight:800;color:var(--pc);font-variant-numeric:tabular-nums}.subco .cop .big small{display:inline;font-size:14px;font-weight:400}
.subco .cog h4{margin:14px 0 6px;font-size:12px;font-weight:700;color:var(--ink-3)}
.subco .cog ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 16px}
.subco .cog li{display:flex;gap:8px;align-items:flex-start;font-size:14px;color:var(--ink)}.subco .cog li svg{flex:none;margin-top:2px;color:var(--pc)}
.subco .cog li i{font-style:normal;color:var(--ink-2);font-size:13px}
.subco .cof{padding:12px 22px 18px;border-top:1px solid var(--line-2)}
.subco .cof label{color:var(--ink-2);margin:0 0 4px}
.subco .cof2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
@media (max-width:520px){.subco .cof2{grid-template-columns:minmax(0,1fr)}}
.subco .agree{margin:12px 0 0;padding:12px 14px;border-radius:12px;border:1px solid color-mix(in srgb,var(--fall) 55%,transparent);background:color-mix(in srgb,var(--fall) 8%,var(--panel))}
.subco .agree b{display:block;font-size:14px;margin-bottom:6px;color:var(--ink)}
.subco .agree label{display:flex;gap:10px;align-items:flex-start;margin:0;font-size:13.5px;color:var(--ink);line-height:1.6;cursor:pointer}
.subco .agree input{width:18px;height:18px;margin-top:2px;flex:none;accent-color:var(--pc)}
.subco .agree a{color:var(--pc);font-weight:700}
.subco .agree .agree2{margin:8px 0 0 28px;font-size:12.5px;line-height:1.6;color:var(--ink-2)}
.subco #subSend{width:100%;height:48px;margin-top:12px;border:0;border-radius:12px;background:var(--pc);color:var(--pr-on,#fff);font:inherit;font-size:16px;font-weight:700;cursor:pointer}
.subco #subSend[disabled]{opacity:.45;cursor:not-allowed}
.subco .cofoot{text-align:center;font-size:12.5px;color:var(--ink-3);margin-top:8px}
.subco .msg{margin-top:8px}
.subco{--pl-blue:#4f8cff;--pr-on:#06101f}:root[data-theme="light"] .subco{--pl-blue:#2b65d9;--pr-on:#fff}
.subco.pc-blue{--pc:var(--pl-blue)}.subco.pc-violet{--pc:var(--violet)}.subco.pc-amber{--pc:var(--amber)}.subco.pc-green{--pc:var(--lime)}.subco.pc-neutral{--pc:var(--ink-2)}
@media (max-width:520px){.subco .cog ul{grid-template-columns:minmax(0,1fr)}}`);
  css('pricingCss', `
#v-pricing{--pl-blue:#4f8cff;--pl-neutral:var(--ink-3);--pr-on:#fff;max-width:1180px;margin:0 auto;padding:0 0 40px}
/* 方案色上的字：淺色主題白字（藍 #2b65d9 5.6:1、紫 --violet 6.0:1）；深色主題的方案色較亮，白字只有 3.3:1 → 改深字（對 #4f8cff 6.4:1）*/
:root:not([data-theme="light"]) #v-pricing{--pr-on:#06101f}
:root[data-theme="light"] #v-pricing{--pl-blue:#2b65d9}
#v-pricing .pc-blue{--pc:var(--pl-blue)}#v-pricing .pc-violet{--pc:var(--violet)}#v-pricing .pc-amber{--pc:var(--amber)}#v-pricing .pc-green{--pc:var(--lime)}#v-pricing .pc-neutral{--pc:var(--pl-neutral)}
#v-pricing .prinfo{display:flex;align-items:center;gap:8px;padding:10px 4px;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink-2);line-height:1.5}
#v-pricing .prinfo svg{flex:none}
#v-pricing .prper{display:flex;justify-content:center;margin:22px 0 0}
#v-pricing .prper .seg{display:inline-flex;gap:4px;padding:4px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel-3)}
#v-pricing .prper button{display:inline-flex;align-items:center;gap:8px;height:38px;padding:0 22px;border:0;border-radius:999px;background:transparent;color:var(--ink-2);font:inherit;font-size:14px;cursor:pointer}
#v-pricing .prper button.on{background:var(--pl-blue);color:var(--pr-on);font-weight:700;box-shadow:0 6px 16px -8px var(--pl-blue)}
#v-pricing .prper .save{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:700;background:color-mix(in srgb,var(--pl-blue) 16%,transparent);color:var(--pl-blue)}
#v-pricing .prper button.on .save{background:color-mix(in srgb,#000 22%,transparent);color:var(--pr-on)}
#v-pricing .prhero{text-align:center;padding:34px 12px 4px}
#v-pricing .prhero h1{margin:0;font-size:30px;font-weight:800;letter-spacing:.5px;color:var(--ink)}
#v-pricing .prhero p{margin:10px auto 0;color:var(--ink-2);font-size:15px;max-width:760px;line-height:1.7}
#v-pricing .prneed{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:center;margin:16px auto 0;max-width:760px;padding:10px 16px;border-radius:12px;
  border:1px solid color-mix(in srgb,var(--amber) 60%,transparent);background:color-mix(in srgb,var(--amber) 12%,transparent);font-size:14px}
#v-pricing .prneed b{color:var(--ink)}#v-pricing .prneed a{color:var(--cyan);font-size:13px}
#v-pricing .prcards{display:grid;grid-template-columns:repeat(var(--n,3),minmax(0,1fr));gap:24px;align-items:stretch;margin-top:44px}
#v-pricing .prcard{position:relative;display:flex;flex-direction:column;min-width:0;padding:28px 26px 24px;border-radius:22px;border:1px solid var(--line);background:var(--panel)}
#v-pricing .prcard:not(.pc-neutral){border-color:color-mix(in srgb,var(--pc) 42%,transparent);
  background:linear-gradient(165deg,color-mix(in srgb,var(--pc) 15%,var(--panel)) 0%,color-mix(in srgb,var(--pc) 6%,var(--panel)) 55%,color-mix(in srgb,var(--pc) 10%,var(--panel)) 100%)}
#v-pricing .prcard.hot{box-shadow:0 18px 44px -26px var(--pc)}
#v-pricing .prcard.need{border-color:var(--amber);box-shadow:0 0 0 2px color-mix(in srgb,var(--amber) 70%,transparent)}
#v-pricing .prtag{position:absolute;top:-14px;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:12.5px;font-weight:700;border-radius:999px;padding:4px 14px;background:var(--pc);color:var(--pr-on);box-shadow:0 6px 14px -6px var(--pc)}
#v-pricing .prtag.need{background:var(--amber);color:#1a1203}
#v-pricing .prhd{display:grid;grid-template-columns:48px minmax(0,1fr);gap:4px 14px;align-items:center}
#v-pricing .prico{grid-row:span 2;width:48px;height:48px;border-radius:50%;display:grid;place-items:center;color:var(--pc);background:color-mix(in srgb,var(--pc) 16%,var(--panel))}
#v-pricing .pc-neutral .prico{color:var(--ink-2);background:var(--panel-3)}
#v-pricing .prcard h2{margin:0;font-size:22px;font-weight:800;line-height:1.2;color:var(--pc);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-pricing .pc-neutral h2{color:var(--ink)}
#v-pricing .prcard .who{font-size:13px;color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-pricing .prprice{margin:4px 0 0;display:block;color:var(--pc);font-variant-numeric:tabular-nums;font-weight:700;line-height:1.1;white-space:nowrap;letter-spacing:.3px}
#v-pricing .prprice .cur{font-size:30px}#v-pricing .prprice b{font-size:36px;font-weight:700;margin:0 4px 0 6px}
#v-pricing .prprice small{font-size:15px;font-weight:500;color:var(--ink-2)}
#v-pricing .prprice.free{font-size:38px;font-weight:900;color:var(--ink)}
#v-pricing .prprice.ask{font-size:30px}
#v-pricing .prnote{margin-top:8px;font-size:13px;color:var(--ink-3);min-height:1.5em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-pricing .prcard hr{border:0;border-top:1px solid color-mix(in srgb,var(--ink) 10%,transparent);margin:22px 0}
#v-pricing .prfit{padding:12px 14px;border-radius:14px;background:color-mix(in srgb,var(--ink) 5%,transparent);margin-bottom:18px}
#v-pricing .prfit b{display:block;font-size:14px;color:var(--pc);margin-bottom:4px}
#v-pricing .pc-neutral .prfit b{color:var(--ink)}
#v-pricing .prfit p{margin:0;font-size:13px;color:var(--ink-2);line-height:1.65}
#v-pricing .prhl{list-style:none;margin:0 0 20px;padding:0;display:grid;gap:12px}
#v-pricing .prhl li{display:flex;align-items:flex-start;gap:10px;font-size:14px;line-height:1.45;color:var(--ink)}
#v-pricing .prhl li svg{flex:none;margin-top:1px;color:var(--pc)}
#v-pricing .pc-neutral .prhl li svg{color:color-mix(in srgb,var(--ink-3) 70%,transparent)}
/* 2026-10-10：這個方案沒開的項目（以前寫「・不開放」）→ 勾勾淡掉、名稱後面一顆琥珀色會員膠囊（同帳號選單額度上限面板的 .qplan） */
#v-pricing .prhl li.prhlneed svg{opacity:.3;filter:grayscale(1)}
#v-pricing .prhl li.prhlneed>span{color:var(--ink-2)}
#v-pricing .prhl .qplan{display:inline-flex;align-items:center;height:20px;margin-left:6px;padding:0 8px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap;vertical-align:1px;
  color:var(--amber);background:color-mix(in srgb,var(--amber) 14%,transparent);border:1px solid color-mix(in srgb,var(--amber) 45%,transparent)}
#v-pricing .prhl .qplan::before{content:'★';margin-right:3px;font-size:10.5px}
#v-pricing .prgo{margin-top:auto;width:100%;height:46px;border-radius:12px;border:1px solid transparent;background:var(--pc);color:var(--pr-on);font:inherit;font-size:15px;font-weight:700;cursor:pointer}
#v-pricing .pc-neutral .prgo{background:transparent;color:var(--ink);border-color:var(--line-2)}
#v-pricing .prgo[disabled]{background:transparent;color:var(--ink-2);border-color:color-mix(in srgb,var(--pc) 35%,var(--line-2));cursor:default}
#v-pricing .prcard.mine .prgo[disabled]{font-weight:700}
#v-pricing .prpre{margin:8px 0 0;font-size:12px;line-height:1.5;color:var(--ink-3);text-align:center}
#v-pricing .prpre a{color:var(--cyan);text-decoration:none}
#v-pricing .prpre-m{display:none}
/* 2026-10-09 手機監督：卡片內放短名仍要 3 行，360 寬整頁超過 3 屏 → 手機把這句從卡片拿出來，接在卡片下方「申請制」那句後面（完整書名；桌機不變） */
#v-pricing .prpre-m a{color:var(--cyan);text-decoration:none}
@media (max-width:640px){#v-pricing .prcard .prpre{display:none}#v-pricing .prpre-m{display:inline}#v-pricing p.prapply{font-size:12px;line-height:1.5}}
#v-pricing .prpre a:hover{text-decoration:underline}
#v-pricing .prapply{text-align:center;font-size:13px;color:var(--ink-2);margin:20px 0 0}
#v-pricing .prapply b{color:var(--ink)}
#v-pricing .prcmp{margin-top:44px}
#v-pricing .prcmp h2{margin:0;text-align:center;font-size:22px;font-weight:800}
#v-pricing .prcmp>p{margin:6px 0 16px;text-align:center;font-size:13px;color:var(--ink-2)}
#v-pricing .prcmpw{overflow-x:auto;border:1px solid var(--line);border-radius:16px;background:var(--panel)}
#v-pricing .prcmpw table{width:100%;border-collapse:separate;border-spacing:0;font-size:14px;min-width:520px}
#v-pricing .prcmpw th,#v-pricing .prcmpw td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:center;white-space:nowrap}
#v-pricing .prcmpw th:first-child,#v-pricing .prcmpw td:first-child{position:sticky;left:0;z-index:1;text-align:left;background:var(--panel);max-width:260px;overflow:hidden;text-overflow:ellipsis}
#v-pricing .prcmpw thead th{font-size:15px;font-weight:800;padding:14px;background:var(--panel)}
#v-pricing .prcmpw thead th.pc-blue,#v-pricing .prcmpw thead th.pc-violet,#v-pricing .prcmpw thead th.pc-amber,#v-pricing .prcmpw thead th.pc-green{color:var(--pc)}
#v-pricing .prcmpw .hot{background:color-mix(in srgb,var(--pl-blue) 8%,var(--panel))}
#v-pricing .prcmpw thead th.hot{background:color-mix(in srgb,var(--pl-blue) 14%,var(--panel))}
#v-pricing .prcmpw tr.cat td{font-size:13px;font-weight:700;color:var(--ink-2);background:var(--panel-3);text-align:left;padding:8px 14px}
#v-pricing .prcmpw td.y{color:var(--pc,var(--ink));font-weight:700}#v-pricing .prcmpw td.y.pc-neutral{color:var(--ink-2)}#v-pricing .prcmpw td.n{color:var(--ink-3)}
#v-pricing .prcmpw td.v{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:13.5px;color:var(--ink)}
#v-pricing .prcmpw tr.hl td{background:color-mix(in srgb,var(--amber) 16%,var(--panel))}
#v-pricing .prcmpw tr.base td{color:var(--ink-2);border-bottom:0}
#v-pricing .prcmpw tr.prmore{display:none}
:root.m4 #v-pricing .prcmpw tr.prmore{display:table-row}
:root.m4 #v-pricing #prTable:not(.prall) tr[data-more]{display:none}
:root.m4 #v-pricing .prmorebtn{width:100%;min-height:36px;border:0;background:transparent;color:var(--cyan);font:inherit;font-size:13px;cursor:pointer}
#v-pricing .prtop{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line)}
#v-pricing .prtop .prinfo{flex:1;min-width:0;border-bottom:0}
#v-pricing .prlay{flex:none;display:inline-flex;gap:2px;padding:3px;border-radius:9px;border:1px solid var(--line-2);background:var(--panel-3)}
#v-pricing .prlay button{height:30px;padding:0 12px;border:0;border-radius:7px;background:transparent;color:var(--ink-2);font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
#v-pricing .prlay button.on{background:var(--panel);color:var(--ink);font-weight:700;box-shadow:0 1px 3px rgba(0,0,0,.18)}
#v-pricing .prmg{margin-top:44px}
#v-pricing .prmg .prcmpw{overflow:auto visible;padding-top:16px;border:0;background:transparent}
#v-pricing .prmg table{table-layout:fixed;min-width:860px;border:1px solid var(--line);border-radius:16px;background:var(--panel)}
#v-pricing .prmg col.c0{width:24%}
#v-pricing .prmg thead th{vertical-align:top;text-align:left;white-space:normal;padding:22px 18px 18px;position:relative}
#v-pricing .prmg thead th:first-child{vertical-align:bottom;font-size:15px}
#v-pricing .prmg thead th.hot,#v-pricing .prmg td.hot{background:color-mix(in srgb,var(--pl-blue) 9%,var(--panel))}
#v-pricing .prmg thead th.hot{box-shadow:inset 0 3px 0 var(--pl-blue)}
#v-pricing .prmg .prtag{top:-12px}
#v-pricing .prmg .prhd{grid-template-columns:40px minmax(0,1fr);gap:2px 10px}
#v-pricing .prmg .prico{width:40px;height:40px}
#v-pricing .prmg .prhd b{font-size:20px;font-weight:800;color:var(--pc);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-pricing .prmg .pc-neutral .prhd b{color:var(--ink)}
#v-pricing .prmg .prprice{margin-top:4px}#v-pricing .prmg .prprice .cur{font-size:22px}#v-pricing .prmg .prprice b{font-size:28px}#v-pricing .prmg .prprice.free{font-size:30px}
#v-pricing .prmg .prnote{font-weight:400}
#v-pricing .prmg .mfit{margin:10px 0 14px;font-size:13px;font-weight:700;color:var(--ink);white-space:normal;line-height:1.5}
#v-pricing .prmg .prgo{height:40px;font-size:14px}
#v-pricing .prmg .prhd .who{font-size:13px;font-weight:400;color:var(--ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-pricing .prmg .mfit{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-pricing .prmg thead th:first-child{font-weight:800}
@media (max-width:820px){#v-pricing .prtop{flex-wrap:wrap;justify-content:flex-end;padding-bottom:8px}#v-pricing .prtop .prinfo{flex-basis:100%}#v-pricing .prmg .prcmpw table{min-width:calc(132px + var(--nc,3) * 200px)}#v-pricing .prmg col.c0{width:132px}}
#v-pricing .prlegal{margin-top:26px;font-size:12.5px;color:var(--ink-2);line-height:1.75;border-top:1px solid var(--line);padding-top:12px}
@media (max-width:1100px){#v-pricing .prcards{gap:16px}#v-pricing .prcard{padding:26px 18px 20px}#v-pricing .prprice .cur{font-size:24px}#v-pricing .prprice b{font-size:30px}}
@media (max-width:820px){#v-pricing .prcards{grid-template-columns:minmax(0,1fr);gap:30px}#v-pricing .prhero h1{font-size:24px}#v-pricing .prhero{padding-top:26px}
  #v-pricing .prper button{padding:0 16px}#v-pricing .prcmpw table{min-width:calc(132px + var(--nc,3) * 112px)}
  #v-pricing .prcmpw th:first-child,#v-pricing .prcmpw td:first-child{width:132px;min-width:132px;max-width:132px;white-space:normal;box-shadow:1px 0 0 var(--line)}
  #v-pricing .prcmpw th,#v-pricing .prcmpw td{padding:10px}#v-pricing .prcmpw tr.base td:first-child{white-space:normal}}
/* ★ 10-07 Andy「排版沒有統一」：欄頭固定列結構 —— 圖示＋名稱＋定位句｜價格大字｜價格小字一行｜「適合…」一行｜按鈕。
   每一層給固定高度（缺內容的格子用 &nbsp; 佔位），三欄每一層的 top 才會一樣、按鈕底緣同一條線；小字一律單行省略，不會被擠到重疊。 */
#v-pricing .prhd{height:48px;align-content:center;margin-bottom:16px}#v-pricing .prmg .prhd{margin-bottom:10px}#v-pricing .prmg .prhd{height:44px}
#v-pricing .prhd .who{line-height:20px;height:20px}
#v-pricing .prprice{height:40px;line-height:40px;overflow:hidden}
#v-pricing .prmg .prprice{height:34px;line-height:34px}
.prday{margin-left:8px;font-size:12px!important;font-weight:600!important;color:var(--ink-3)!important;letter-spacing:0}
#v-pricing .prnote,#v-pricing .prmg .prnote{margin-top:6px;height:20px;line-height:20px;min-height:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-pricing .mfit,#v-pricing .prmg .mfit{margin:8px 0 14px;height:20px;line-height:20px;font-size:13px;font-weight:700;color:var(--pc);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#v-pricing .pc-neutral .mfit{color:var(--ink)}
#v-pricing .prcard hr{margin:4px 0 18px}
#v-pricing .prfit p{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;height:calc(1.65em * 4)}
#v-pricing .prfit.nil{background:transparent}
#v-pricing .prorig,.subdlg .prorig{height:24px;display:flex;align-items:center;gap:8px;white-space:nowrap;overflow:hidden}
.prstrike{color:var(--ink-3);font-size:14px;text-decoration:line-through;text-decoration-thickness:1.5px}
.prsale{display:inline-block;flex:none;padding:0 9px;border-radius:999px;font-size:12px;font-weight:800;color:var(--amber);background:color-mix(in srgb,var(--amber) 16%,transparent);border:1px solid color-mix(in srgb,var(--amber) 55%,transparent);line-height:20px}
#v-pricing .prorig+.prprice{margin-top:4px}
#v-pricing .prmg .prorig{gap:6px}#v-pricing .prmg .prstrike{font-size:12.5px}#v-pricing .prmg .prsale{font-size:11.5px;padding:0 7px}#v-pricing .prmg col.c0{width:20%}#v-pricing .prmg thead th[data-plan]{padding-left:14px;padding-right:14px}
#v-pricing .mfit,#v-pricing .prmg .mfit{margin-top:6px}
`);

  function paint() {
    const v = view('v-pricing'); if (!v) return;
    const all = tidy(S.plans || FALLBACK);
    /* 卡片：註冊會員＋公開的付費範本（依「折合每月」價格由低到高；價格拿不到的排最後、維持後端順序）*/
    const paid = all.filter((p) => tierOf(p) === 'paid' && p.public !== false).map((p, i) => [p, i])
      .sort((a, b) => monthEq(a[0]) - monthEq(b[0]) || a[1] - b[1]).map((x) => x[0]);
    const free = all.find((p) => p.id === 'free');
    const plans = [free, ...paid].filter(Boolean);
    /* 月／年切換：至少一個付費範本兩種價格都有才出現；預設年繳（範本圖選中的是年繳），只記在這一頁 */
    const both = paid.filter((p) => { const x = prices(p); return x.month && x.year; });
    const hasPer = both.length > 0;
    if (!hasPer) S.per = ''; else if (!S.per) S.per = 'year';
    const save = Math.max(0, ...both.map(saveOf));
    const saveTxt = save > 0 ? (new Set(both.map(saveOf)).size > 1 ? `最多省 ${save}%` : `省 ${save}%`) : '';
    /* 頂端標籤：管理者有填就只用填的；都沒填才沿用舊規則（第一個付費＝最受歡迎、開最多功能＝功能最齊）*/
    const fs = boolFs(), nOn = (p) => fs.filter((f) => on(p, f)).length;
    const anyBadge = paid.some((p) => p.badge);
    let hot = anyBadge ? (paid.find((p) => p.badge && p.color === 'blue') || paid.find((p) => p.badge) || null) : paid[0] || null;
    let full = null;
    if (!anyBadge && paid.length > 1) { full = paid.slice().sort((a, b) => nOn(b) - nOn(a))[0]; if (full === hot) full = paid[paid.length - 1]; }
    const AUTO_I = ['bolt', 'crown', 'star', 'rocket'];
    const look = new Map(plans.map((p) => {
      const i = paid.indexOf(p);
      return [p.id, { color: p.color || (i < 0 ? 'neutral' : AUTO_C[i % 4]), icon: p.icon || (i < 0 ? 'gift' : AUTO_I[i % 4]),
        badge: anyBadge ? (p.badge || '') : p === hot ? '最受歡迎' : p === full ? '功能最齊' : '' }];
    }));
    const needF = S.need && F() ? F().byId(S.need) : null;
    const needIds = needF ? plans.filter((p) => unlocks(p, needF)).map((p) => p.id)
      : S.pick && plans.some((p) => p.id === S.pick) ? [S.pick] : [];   // #pricing/plan/<id>：額度卡的「升級 Plus／Pro →」點過來，標那一張
    const me = myPlan();
    const fits = plans.filter((p) => p.fit_title).map((p) => `${showName(p)} ${p.fit_title}`);
    v.innerHTML = `
      <div class="prtop"><div class="prinfo" role="note">${INFO}<span>本平台非券商、非投顧，不提供任何買賣建議，資料為盤後整理、僅供參考。如有建議或疑問，請透過右下角「客服」聯繫。</span></div>
        <div class="prlay" id="prLayout" role="tablist" aria-label="版面">${[['cards', '卡片＋表格'], ['merged', '合併表']].map(([k, n]) => `<button type="button" role="tab" data-lay="${k}" class="${S.layout === k ? 'on' : ''}" aria-selected="${S.layout === k}">${n}</button>`).join('')}</div></div>
      ${hasPer ? `<div class="prper"><div class="seg" id="prPeriod" role="tablist" aria-label="計費週期">
        <button type="button" role="tab" data-per="month" class="${S.per === 'month' ? 'on' : ''}" aria-selected="${S.per === 'month'}">月繳</button>
        <button type="button" role="tab" data-per="year" class="${S.per === 'year' ? 'on' : ''}" aria-selected="${S.per === 'year'}">年繳${saveTxt ? `<span class="save" id="prSave">${esc(saveTxt)}</span>` : ''}</button></div></div>` : ''}
      <div class="prhero"><h1>依你的研究深度選方案</h1>
        <p>${fits.length >= 2 ? esc(fits.join('，') + '。') : '從資金流向、產業鏈到個股技術面，一個網站看完台股輪動。免費就能用大部分功能，付費方案開放更多分析與更高的每日瀏覽次數。'}</p></div>
      ${needF ? `<div class="prneed" id="prNeed" role="status">你剛剛點的 <b>「${esc(needF.name)}」</b>${needIds.length ? `在標成<b>「可解鎖」</b>的方案裡開放（或次數更多）` : '目前沒有方案開放更多，可以從右下角客服跟我們說'}<a href="#pricing" id="prNeedX">清除標示</a></div>` : ''}
      ${S.layout === 'merged' ? compare(plans, look, hot, needF, { me, needIds }) : `<div class="prcards" id="prCards" style="--n:${Math.min(4, Math.max(1, plans.length))}">${plans.map((p) => card(p, look.get(p.id), p === hot, me, needIds.includes(p.id))).join('')}</div>`}
      <p class="prapply"><b>目前為申請制，專人開通；線上付款即將推出。</b>申請送出不會扣款。<span class="prpre-m">付款前請先閱讀<a href="#refund">《退款與取消訂閱政策》</a><a href="#terms">《使用條款》</a></span>${S.src === 'fallback' ? '　（暫時讀不到付費方案）' : S.src === 'demo' ? '　（示範資料）' : ''}</p>
      ${S.layout === 'merged' ? '' : compare(plans, look, hot, needF)}
      <div class="prlegal">本網站提供的是資料整理與視覺化工具，<b>不是證券投資顧問</b>，不提供個股買賣建議，所有內容僅供參考，投資請自行判斷並承擔風險。
        方案內容與價格以專人開通時的確認為準；申請送出不會扣款。詳見 <a href="#disclaimer">免責聲明</a>、<a href="#terms">使用條款</a>、<a href="#privacy">隱私權政策</a>。</div>`;
    S.look = look;
    v.querySelectorAll('#prLayout button[data-lay]').forEach((b) => { b.onclick = () => { if (S.layout === b.dataset.lay) return; S.layout = b.dataset.lay; paint(); }; });
    v.querySelectorAll('#prPeriod button[data-per]').forEach((b) => { b.onclick = () => { if (S.per === b.dataset.per) return; S.per = b.dataset.per; paint(); }; });
    v.querySelectorAll('.prgo[data-go]').forEach((b) => { b.onclick = () => go(plans.find((p) => p.id === b.dataset.go)); });
    if (needIds.length && S.layout === 'cards') { const c = v.querySelector(`.prcard[data-plan="${CSS.escape(needIds[0])}"]`); if (c && c.scrollIntoView) setTimeout(() => c.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 60); }
  }
  const whoOf = (p) => p.tagline || (tierOf(p) === 'free' ? '用 Google 帳號登入即可' : '進階分析與更高的每日次數');
  function priceHtml(p) {
    const pr = priceAt(p, S.per);
    const html = pr.free ? '<div class="prprice free">免費</div>'
      : pr.amount == null ? '<div class="prprice ask">價格待定</div>'
      : `<div class="prprice"><span class="cur">NT$</span> <b>${nt(pr.amount)}</b><small>${esc(pr.unit)}</small>${dayTag(pr)}</div>`;
    const note = pr.free ? '永久保留基礎功能・不需信用卡' : pr.note;
    return `${origLine(pr)}${html}<div class="prnote" title="${esc(note)}">${esc(note)}</div>`;
  }
  /* 10-07 Andy「原價錢被劃掉，旁邊標註減多少，再寫出新價格，像特賣會」：年繳時第一行＝原價（月價×12，刪除線）＋琥珀徽章「省 NT$ X・約 Y%」；
     其他情況這一行用 &nbsp; 佔位（三欄每一層才對齊）。 */
  function origLine(pr) { return pr.orig ? `<div class="prorig"><s class="prstrike">NT$ ${nt(pr.mo)}／月</s><span class="prsale">省 NT$ ${nt(pr.orig - pr.total)}／年・約 ${Math.round((pr.orig - pr.total) / pr.orig * 100)}%</span></div>` : '<div class="prorig">&nbsp;</div>'; }
  function btnOf(p, me) {
    /* ★ 10-07 Andy「已是 pro 用戶但 plus 尚未包含」：以前只認「同一張＝目前方案、免費卡＝已包含」，其餘一律「升級」。
       改成比層級（rankOf：免費 0、付費＝折合每月價格，不寫死方案名）：比目前低＝已包含、同一張＝目前方案、比目前高才升級。站主全部已包含。 */
    if (me.tier === 'owner') return `<button type="button" class="prgo" disabled>已包含</button>`;
    if (me.id === p.id) return `<button type="button" class="prgo" disabled>目前方案</button>`;
    if (tierOf(p) === 'free' && me.tier === 'guest') return `<button type="button" class="prgo" data-go="${esc(p.id)}">免費註冊／登入</button>`;
    const mine = me.tier === 'free' ? 0 : me.tier === 'guest' ? -1 : (() => { const x = tidy(S.plans || FALLBACK).find((q) => q.id === me.id); return x ? rankOf(x) : -1; })();
    if (rankOf(p) <= mine) return `<button type="button" class="prgo" disabled>已包含</button>`;
    return `<button type="button" class="prgo" data-go="${esc(p.id)}">升級 ${esc(showName(p))}</button>`;
  }
  const tagOf = (lk, need) => (need ? `<span class="prtag need">${S.need && F() && F().byId(S.need) ? '可解鎖' : '建議升級'}</span>` : lk.badge ? `<span class="prtag">${lk.badge === '最受歡迎' ? '★ ' : '✦ '}${esc(lk.badge)}</span>` : '');
  function card(p, lk, hot, me, need) {
    const t = tierOf(p), isMine = me.id === p.id;
    const who = whoOf(p);
    const btn = btnOf(p, me);
    const hl = (Array.isArray(p.highlights) && p.highlights.length ? p.highlights : autoHl(p)).slice(0, 12);
    const tag = tagOf(lk, need);
    /* 10-07 排版統一：「適合…」一行移到欄頭（.mfit，跟合併表同一層）；這裡只留說明，固定 4 行高（沒寫也佔位），打勾清單才會三張卡同一條起跑線 */
    /* 10-07 17:50 Andy：免費方案的灰底說明框「沒必要」→ 註冊會員不畫內容，只留同高的空白，打勾清單仍跟 Plus／Pro 同一條起跑線 */
    const showFit = p.fit_desc && t !== 'free';
    const fit = `<div class="prfit${showFit ? '' : ' nil'}"><p title="${esc(showFit ? p.fit_desc : '')}">${showFit ? esc(p.fit_desc) : '&nbsp;'}</p></div>`;
    return `<div class="prcard pc-${esc(lk.color)}${hot ? ' hot' : ''}${need ? ' need' : ''}${isMine ? ' mine' : ''}" data-plan="${esc(p.id)}" data-tier="${t}">
      ${tag}<div class="prhd"><span class="prico">${svgI(lk.icon)}</span><h2 title="${esc(showName(p))}">${esc(showName(p))}</h2><div class="who" title="${esc(who)}">${esc(who)}</div></div>
      ${priceHtml(p)}<div class="mfit" title="${esc(p.fit_title || '')}">${p.fit_title ? esc(p.fit_title) : '&nbsp;'}</div><hr>
      ${fit}<ul class="prhl">${hl.map((x) => (x && typeof x === 'object'
        ? `<li class="prhlneed">${CHECK}<span>${esc(x.t)}<span class="qplan" data-need="1">${esc(x.need)}</span></span></li>`
        : `<li>${CHECK}<span>${esc(x)}</span></li>`)).join('')}</ul>${btn}${preRead(t)}</div>`;
  }
  /* 2026-10-09（Andy：「退款政策及取消訂閱幫我新增」）：付費卡的升級鈕下面一行「付款前請先閱讀…」。
     免費卡放同高的隱形佔位，三張卡的按鈕才會在同一條線上。*/
  function preRead(t) {
    const paid = t !== 'free' && t !== 'guest';
    return `<p class="prpre"${paid ? '' : ' aria-hidden="true" style="visibility:hidden"'}>付款前請先閱讀${paid ? '<a href="#refund" title="退款與取消訂閱政策">《退款與取消訂閱政策》</a><a href="#terms" title="使用條款">《使用條款》</a>' : '《退款與取消訂閱政策》《使用條款》'}</p>`;
  }
  /* 方案功能比較表：每格＝✓／—／每日 N 次／最多 N 頁。只列「至少一個方案不一樣」的功能；全部一樣的收成最後一行 */
  function compare(plans, look, hot, needF, mg) {
    const Ft = F(); if (!Ft || plans.length < 2) return '';
    const cell = (p, f) => {
      if (f.id === 'watch.tabs') return watchCell(p);
      if (f.kind === 'limit') { const n = val(p, f); return n ? { c: 'v', t: f.opts && n >= f.max ? '不限' : f.daily ? `每日 ${n} ${f.unit || '次'}` : `最多 ${n} ${f.unit || '頁'}` } : { c: 'n', t: '—' }; }
      if (!on(p, f)) return { c: 'n', t: '—' };
      const n = limOf(p, f); return n === Infinity ? { c: 'y', t: '✓' } : { c: 'v', t: `每日 ${n} 次` };
    };
    const hc = (p) => ` pc-${look.get(p.id).color}` + (p === hot ? ' hot' : '');
    let rows = '', same = 0, fi = 0;
    /* ★ 2026-10-10 手機（≤640，html.m4）：比較表只先列前 MORE_N 項差異，其餘收在「看全部 N 項比較」後面（手機準則 1／5：≤3 屏、收展預設收起）。
       10-10 這批多了今日關注、▶ 播放、族群篩選、總覽／熱力圖跳頁四列，360 寬整頁超過 3 屏。桌機照舊全列（CSS 只在 :root.m4 生效）。*/
    const MORE_N = 8, more = () => (++fi > MORE_N ? ' data-more=""' : '');
    /* 研究瀏覽（全站共用每日額度 quota.all，另一位同事在 quota.js 加）：範本的 lims 有這個鍵才列，放第一列；null／沒寫＝不限 */
    if (plans.some((p) => qAll(p) !== undefined)) {
      const qa = plans.map((p) => { const n = qAll(p); return n === undefined || n === Infinity ? { c: 'y', t: '不限' } : n === 0 ? { c: 'n', t: '—' } : { c: 'v', t: `每日 ${n} 次` }; });
      if (new Set(qa.map((x) => x.t)).size > 1) rows += `<tr class="cat"><td colspan="${plans.length + 1}">研究瀏覽</td></tr><tr data-f="quota.all"${needF && needF.id === 'quota.all' ? ' class="hl"' : ''}><td title="個股、剖析圖、題材剖析等研究頁，全站合計的每日瀏覽次數">研究瀏覽（全站共用）</td>${qa.map((x, i) => `<td class="${x.c}${hc(plans[i])}">${esc(x.t)}</td>`).join('')}</tr>`;
      else same++;
    }
    Ft.cats.filter((c) => c.id !== 'grp').forEach((c) => {
      const fs = Ft.inCat(c.id).filter((f) => !f.adminOnly && f.id !== 'watch.size' && (f.kind === 'bool' || f.kind === 'limit'));   // 每頁檔數併進「自選分頁數」那一格（watchCell）
      /* 同一列有方案寫「每日 N 次」時，不限的那格寫「不限」而不是 ✓（不然看起來像「有」但不知道幾次）*/
      const diff = fs.map((f) => { const cs = plans.map((p) => cell(p, f)); return [f, cs.some((x) => /^每日/.test(x.t)) ? cs.map((x) => (x.c === 'y' ? { c: 'y', t: '不限' } : x)) : cs]; }).filter(([, cs]) => { if (new Set(cs.map((x) => x.t)).size > 1) return true; same++; return false; });
      if (!diff.length) return;
      rows += `<tr class="cat"${fi + 1 > MORE_N ? ' data-more=""' : ''}><td colspan="${plans.length + 1}">${esc(c.name)}</td></tr>` + diff.map(([f, cs]) => `<tr data-f="${esc(f.id)}"${more()}${needF && needF.id === f.id ? ' class="hl"' : ''}><td title="${esc(f.desc || f.name)}">${esc(f.name)}</td>${cs.map((x, i) => `<td class="${x.c}${hc(plans[i])}">${esc(x.t)}</td>`).join('')}</tr>`).join('');
    });
    const g = Ft.inCat('grp');
    const gv = plans.map((p) => { const off = Object.keys(p.feats || {}).filter((k) => k.startsWith('grp.') && p.feats[k] === false).length + Object.keys(p.lims || {}).filter((k) => k.startsWith('grp.') && p.lims[k] === 0).length;
      return off === 0 ? '全部' : g.length ? (g.length - off) + '／' + g.length : '關閉 ' + off + ' 個'; });
    if (new Set(gv).size > 1) rows += `<tr class="cat"><td colspan="${plans.length + 1}">族群觀測</td></tr><tr data-f="grp"><td>可展開的族群</td>${gv.map((x, i) => `<td class="v${hc(plans[i])}">${esc(x)}</td>`).join('')}</tr>`;
    if (fi > MORE_N) rows += `<tr class="prmore"><td colspan="${plans.length + 1}"><button type="button" class="prmorebtn" aria-expanded="false">看全部 ${fi} 項比較 ›</button></td></tr>`;
    if (same) rows += `<tr class="base"><td>其他基礎功能（${same} 項）</td><td colspan="${plans.length}">全部方案皆可用</td></tr>`;
    if (mg) {
      /* 合併表：欄頭＝圖示＋名稱＋定位句、價格、適合誰、行動鈕；頂端標籤浮在欄頭上緣；Plus（hot）整欄淡藍 */
      const head = plans.map((p) => { const lk = look.get(p.id), need = mg.needIds.includes(p.id);
        return `<th class="pc-${esc(lk.color)}${hc(p)}${need ? ' need' : ''}" data-plan="${esc(p.id)}" scope="col">${tagOf(lk, need)}
          <div class="prhd"><span class="prico">${svgI(lk.icon)}</span><b title="${esc(showName(p))}">${esc(showName(p))}</b><div class="who" title="${esc(whoOf(p))}">${esc(whoOf(p))}</div></div>
          ${priceHtml(p)}<div class="mfit" title="${esc(p.fit_title || '')}">${p.fit_title ? esc(p.fit_title) : '&nbsp;'}</div>${btnOf(p, mg.me)}</th>`; }).join('');
      return `<section class="prmg" id="prMerged"><div class="prcmpw" style="--nc:${plans.length}"><table id="prTable"><colgroup><col class="c0">${plans.map(() => '<col>').join('')}</colgroup>
        <thead><tr><th scope="col">功能比較<div class="who" style="font-weight:400;font-size:13px;color:var(--ink-2)">只列方案之間有差異的功能</div></th>${head}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
    }
    return `<section class="prcmp" id="prCmp"><h2>方案功能比較</h2><p>只列出方案之間有差異的功能</p>
      <div class="prcmpw" style="--nc:${plans.length}"><table id="prTable"><thead><tr><th>功能</th>${plans.map((p) => `<th class="pc-${esc(look.get(p.id).color)}${hc(p)}">${esc(showName(p))}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
  }
  /* 訂閱鈕：免費卡＝登入；付費卡＝訂閱申請（要先登入：沒登入直接跳 Google 登入，登入回來再按一次）*/
  function go(p) {
    if (!p) return;
    if (p.demo) { dialog(`<h3>${esc(showName(p))} 方案</h3><p>${esc(showName(p))} 方案即將開放（${p.dq == null ? '不限次數' : `每日 ${p.dq} 次`}），價格待定。想先預約可以從右下角「客服」留言給我們。</p><div class="row2"><button type="button" class="pri" data-close>知道了</button></div>`); return; }
    const a = A();
    const u = a && a.on() ? a.user() : null;
    if (tierOf(p) === 'free') { if (a && a.on()) a.login(); else toast('會員登入功能尚未開放'); return; }
    if (!a || !a.on()) {
      dialog(`<h3>訂閱申請</h3><p>線上申請暫時無法使用（會員功能尚未開放）。請從右下角「客服」寄信給我們，註明想要的方案「${esc(showName(p))}」。</p><div class="row2"><button type="button" class="pri" data-close>知道了</button></div>`);
      return;
    }
    if (!u) { toast('申請訂閱要先登入 —— 登入完成後再按一次「升級」'); a.login(); return; }
    /* 週期跟著頁上的月／年切換；範本只有一種週期就用它自己的（後端 /v1/subscribe/request 只收 month／year，一次付清當「月」送，專人開通時再確認）*/
    const pr = priceAt(p, S.per);
    const per = pr.period === 'year' ? 'year' : 'month';
    const lk = S.look.get(p.id) || { color: 'blue', icon: 'bolt' };
    const ptop = pr.orig ? origLine(pr) : '';
    const pbig = pr.amount == null ? '價格待定' : pr.total && pr.unit === '／年' ? `NT$ ${nt(pr.total)}<small>／年</small>${dayTag(pr)}` : `NT$ ${nt(pr.amount)}<small>${esc(pr.unit)}</small>${dayTag(pr)}`;
    /* 已含功能：依 features.js 類別分組、兩欄打勾（範本 feats／lims 算出來的，跟比較表同一份）；有上限的寫「每日 N 次」 */
    const Ft = F();
    const groups = Ft ? Ft.cats.filter((c) => c.id !== 'grp').map((c) => [c, Ft.inCat(c.id).filter((f) => !f.adminOnly && f.kind === 'bool' && on(p, f))]).filter(([, fs]) => fs.length) : [];
    const wc = watchCell(p);
    const gl = groups.map(([c, fs]) => `<h4>${esc(c.name)}</h4><ul>${fs.map((f) => { const n = limOf(p, f); return `<li>${CHECK}<span>${esc(f.name)}${n !== Infinity ? `<i>・每日 ${n} 次</i>` : ''}</span></li>`; }).join('')}${c.id === 'watch' && wc.c !== 'n' ? `<li>${CHECK}<span>自選清單<i>・${esc(wc.t)}</i></span></li>` : ''}</ul>`).join('');
    dialog(`<div class="coh"><span class="ic">${svgI(lk.icon)}</span><b>${esc(showName(p))}</b><small>${esc(whoOf(p))}</small><button type="button" data-close aria-label="關閉">×</button></div>
      <div class="cob"><div class="cop">${ptop}<div class="big">${pbig}</div>${pr.orig ? `<small>${esc(pr.note)}</small>` : ''}<small>${per === 'year' ? '年繳' : '月繳'}・目前為申請制，專人開通；線上付款即將推出</small></div>
        <div class="cog" id="subFeats">${gl}</div></div>
      <div class="cof"><div class="cof2"><div><label for="subMail">聯絡 email</label><input type="email" id="subMail" value="${esc(u.email || '')}" autocomplete="email" maxlength="200"></div>
        <div><label for="subNote">備註（選填，例如發票抬頭）</label><input type="text" id="subNote" maxlength="180"></div></div>
        <div class="agree"><b>訂閱前請確認</b><label><input type="checkbox" id="subAgree"><span id="subAgreeT">我已閱讀並同意<a href="#terms" target="_blank" rel="noopener">《使用條款》</a><a href="#refund" target="_blank" rel="noopener">《退款與取消訂閱政策》</a>，並同意付款後立即開通服務、排除消費者保護法第 19 條之七日解除權。</span></label>
          <p class="agree2">個人資料之處理見<a href="#privacy" target="_blank" rel="noopener">《隱私權政策》</a>。送出的是訂閱申請，方案內容與付款方式由客服確認後才開通；送出時會記錄同意時間與條款版本。</p></div>
        <div class="msg" id="subMsg" role="status"></div>
        <button type="button" id="subSend" disabled>送出訂閱申請</button>
        <div class="cofoot">申請後由客服聯絡開通・送出不會扣款</div></div>`, (d) => {
      const box = d.querySelector('.box'); box.className = `box subco pc-${lk.color}`;
      const ag = d.querySelector('#subAgree'), sb = d.querySelector('#subSend');
      ag.onchange = () => { sb.disabled = !ag.checked; };
      d.querySelector('#subSend').onclick = async () => {
        const msg = d.querySelector('#subMsg'), btn = d.querySelector('#subSend');
        const contact = d.querySelector('#subMail').value.trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact)) { msg.className = 'msg bad'; msg.textContent = '請填正確的 email'; return; }
        btn.disabled = true; msg.className = 'msg'; msg.textContent = '送出中…';
        /* 2026-10-09 Andy：「結帳頁一定要加『同意付款後立即開通、排除七日解除權』的勾選」→ 同意證據＝同意時間＋條款版本。
           Worker（sub_requests）目前只存 note，所以證據寫在 note 開頭一併存下；另外帶 consent_at／consent_version／consent 三個欄位，
           Worker 加欄位後就能分開存（docs/legal_refund_1009.md 必做清單）。使用者備註限 180 字，加上證據仍在 Worker 的 300 字上限內。*/
        const cAt = new Date().toISOString();
        const cVer = window.TwLegal && window.TwLegal.termsVersion ? window.TwLegal.termsVersion() : 'unknown';
        const userNote = d.querySelector('#subNote').value.trim().slice(0, 180);
        const stamp = `[同意 ${cAt} 條款版本 ${cVer}：使用條款＋退款與取消訂閱政策，付款後立即開通、排除消保法§19七日解除權]`;
        const j = await call('/v1/subscribe/request', { plan: p.id, period: per, contact, note: stamp + (userNote ? ' ' + userNote : ''),
          user_note: userNote, consent_at: cAt, consent_version: cVer, consent: 'terms+refund;immediate_start;waive_cpa19' });
        btn.disabled = !ag.checked;
        if (j && j._s === 200 && j.ok) {
          box.className = 'box';
          box.innerHTML = `<h3>已收到你的申請</h3><p>方案：<b>${esc(showName(p))}</b>（${per === 'year' ? '年繳' : '月繳'}）<br>我們會寄信到 <b>${esc(contact)}</b> 跟你確認，開通後重新整理網頁就會生效。</p><div class="row2"><button type="button" class="pri" data-close>好</button></div>`;
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
  /* 給 site/qcard.js（quota 分支）：方案清單（同步；還沒抓過回 null）、確保抓過一次、哪些方案開放某個功能（訪客除外，順序＝方案卡順序）*/
  const ensure = () => (S.plans ? Promise.resolve(S.plans) : load().then(() => S.plans));
  const unlockers = (fid) => { const f = F() && F().byId(fid); if (!S.plans || !f) return null; return S.plans.filter((p) => tierOf(p) !== 'guest' && on(p, f)).map((p) => ({ id: p.id, name: showName(p), dq: Number.isInteger(p.dq) ? p.dq : null })); };
  window.TwPricing = { reload: () => { S.plans = null; return show(); }, priceOf, priceAt, fromPreset, state: () => ({ src: S.src, plans: S.plans, need: S.need, pick: S.pick, per: S.per }),
    plans: () => S.plans, ensure, unlockers };
  /* 手機比較表「看全部 N 項比較 ›」：按一下展開／再按收起（不記狀態：每次進訂閱頁都是收起，手機準則 5）*/
  document.addEventListener('click', (e) => {
    const b = e.target && e.target.closest && e.target.closest('#v-pricing .prmorebtn'); if (!b) return;
    const t = b.closest('table'); if (!t) return;
    const on = t.classList.toggle('prall');
    b.setAttribute('aria-expanded', on ? 'true' : 'false');
    b.textContent = on ? '收起 ‹' : `看全部 ${t.querySelectorAll('tr[data-f]').length} 項比較 ›`;
  });
})();
