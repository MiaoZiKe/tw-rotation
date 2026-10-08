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
    /* 2026-10-08：題材熱力圖首頁（#heatmap/theme，還沒選題材）下方只有一行「尚未選擇題材」—— 不是看了一個題材，不算（以前會記成 heatmap.<分頁>，白扣一次）*/
    if (k === 'theme') return /^t\./.test(pk) || /^x/.test(pk) && /^#heatmap\/theme\/./.test(h) ? pk : null;
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
    try { const ts = window.TwTour && window.TwTour.state(); if (ts && ts.on) { paint(new Map()); ring(false, 0); return; } } catch (e) { /* 沒有導覽就照舊 */ }
    const h = location.hash || '';
    const fs = limited();
    const d = load(); let changed = false;
    let ringOn = false;
    const want = new Map();
    if (!h.startsWith('#admin') && !h.startsWith('#pricing')) {
      for (const f of fs) {
        const els = targets(f, h); if (!els.length) continue;
        const key = unitKey(f, h);
        if (key == null) continue;
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
          ringOn = true;
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
    ring(ringOn, (d.k[ALL] || []).length);
    pagePanel(ringOn);
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
  /* ★ 2026-10-07 額度圓環（Andy：「依據不同會員身份，對應該分頁需要有使用次數圓圈提醒」）：
     計次頁（這一頁有 metered 研究區塊、全站額度有上限）在頁名旁「◎ 導覽」右邊放一顆小圓環：環＝今天已用比例、中間「剩 N」／「用完」，
     點了到 #pricing。不限次（Pro、管理者）與不計次的頁面不顯示 —— 沒有限制就不要拿一顆「不限」來佔頁首的位置。
     手機（≤820 沒有 #l4Head）：放在頂欄導覽鈕左邊（放右邊會跟 tour.js 的「導覽鈕必須緊貼搜尋鈕」搶位置，每 500ms 互相搬來搬去）。 */
  function ring(on, used) {
    let el = document.getElementById('twQRing');
    const all = allLim();
    const h = location.hash || '';
    if (!on || all === Infinity || h.startsWith('#admin') || h.startsWith('#pricing')) { if (el) el.hidden = true; return; }
    if (!el) {
      el = document.createElement('a'); el.id = 'twQRing'; el.href = '#pricing'; el.className = 'twqr';
      el.innerHTML = '<svg viewBox="0 0 36 36" aria-hidden="true"><circle class="bg" cx="18" cy="18" r="15.5"/><circle class="fg" cx="18" cy="18" r="15.5" pathLength="100" transform="rotate(-90 18 18)"/></svg><b></b>';
    }
    const tb = document.getElementById('twPageTourBtn');
    const h1 = document.querySelector('#l4Head h1');
    const desk = !!(h1 && h1.getClientRects().length);
    el.classList.toggle('mob', !desk);
    if (desk) { const after = tb && tb.parentNode === h1.parentNode ? tb : h1; if (el.previousElementSibling !== after) after.after(el); }
    else if (tb && tb.parentNode) { if (el.nextElementSibling !== tb) tb.before(el); }
    else { const a = document.querySelector('#mSearchBtn') || document.querySelector('.topbar .search'); if (a) { if (el.nextElementSibling !== a) a.before(el); } else { el.hidden = true; return; } }
    const u = Math.min(used, all), rem = Math.max(0, all - used);
    const st = P() ? P().state() : {};
    const nm = st.who === 'guest' || !st.who ? '訪客' : (st.planName || (st.plan === 'free' || !st.plan ? '註冊會員' : st.plan));
    const lvl = rem === 0 ? 'out' : rem / Math.max(all, 1) > 0.5 ? 'hi' : 'mid';
    el.hidden = false;
    el.dataset.lvl = lvl; el.dataset.rem = String(rem);
    el.querySelector('.fg').setAttribute('stroke-dasharray', `${all ? (u / all) * 100 : 100} 100`);
    el.querySelector('b').textContent = rem === 0 ? '用完' : '剩 ' + rem;
    const tip = `今日已用 ${u}／${all} 次（${nm}）・台北 0 點重置・同一檔同一天只算一次`;
    el.title = tip; el.setAttribute('aria-label', tip + '。點一下看方案');
  }
  /* ============================================================================
     ★ 2026-10-08 本頁限制清單（Andy：「次數那邊若當前分頁有很多限制項目 在幫我標示出來」）
     額度圓環旁多一顆「本頁 N 項限制・最少剩 X 次」（收合）；點開逐項列出這一頁所有有每日上限的項目：
     名稱、計次單位（看／篩選／切分頁／下鑽）、已用／上限、還剩幾次、一條小進度條；剩 1 次琥珀色、用完紅色。
     「這一頁」＝網址對得上那個功能（PAGE_OF 精確對到子分頁；其餘依分類對到頁名）；上限 0 的寫「不開放」。
     不受限的身分（Pro、擁有者、預覽版）每一項都是不限 → 清單空的 → 整顆不顯示。換頁時 evaluate() 會重算，跟著換成那一頁的項目。
     ============================================================================ */
  const PAGE_OF = {
    'flow.sankey.drill': /^#flow\/sankey/, 'flow.sankey': /^#flow\/sankey/, 'flow.inst.filter': /^#flow\/inst/, 'flow.inst': /^#flow\/inst/, 'flow.conc': /^#flow\/inst/,
    'flow.rot': /^#flow(\/rotation)?([/?]|$)/, 'etf.calendar': /^#etf\/cal/, 'etf.calendar.tab': /^#etf\/cal/, 'etf.cashflow': /^#etf\/inc/,
    'heat.detail': /^#heatmap\/theme/, 'heat.theme': /^#heatmap\/theme/, 'heat.market': /^#heatmap(\/industry)?([/?]|$)/,
  };
  const CAT_HEAD = { overview: /^#(overview)?([/?]|$)/, flow: /^#flow/, industry: /^#industry/, heatmap: /^#heatmap/, market: /^#market/, stockk: /^#stock\//, stocktab: /^#stock\//,
    etf: /^#etf(\/list)?([/?]|$)/, explore: /^#explore/, earnings: /^#earnings/, watch: /^#watch/ };
  const UNIT_TXT = { tab: '切分頁', filter: '篩選', drill: '下鑽', obj: '看' };
  function onPage(f, h) {
    if (PAGE_OF[f.id]) return PAGE_OF[f.id].test(h);
    if (/^season\./.test(f.id)) return /^#season/.test(h);
    if (f.id === 'ind.groups' || f.id === 'ind.map') return /^#industry/.test(h);
    const re = CAT_HEAD[f.cat]; return !!(re && re.test(h || '#overview'));
  }
  function pageItems(ringOn) {
    const Ft = F(), p = P(); if (!Ft || !p) return [];
    const h = location.hash || '#overview', d = load(), st = p.state();
    const out = [];
    Object.keys(st.lims || {}).forEach((id) => {
      const f = Ft.byId(id); if (!f || f.kind === 'limit' || f.cat === 'grp') return;
      const n = limitOf(id); if (n === Infinity || !onPage(f, h)) return;
      const used = Math.min(n, (d.k[id] || []).length);
      out.push({ id, name: f.name, unit: UNIT_TXT[f.act] || '看', used, lim: n, rem: Math.max(0, n - used) });
    });
    if (ringOn && allLim() !== Infinity) { const n = allLim(), used = Math.min(n, (d.k[ALL] || []).length); out.push({ id: ALL, name: '研究瀏覽（全站共用）', unit: '看', used, lim: n, rem: Math.max(0, n - used) }); }
    return out;
  }
  function pagePanel(ringOn) {
    const h = location.hash || '';
    let el = document.getElementById('twQPage');
    const items = h.startsWith('#admin') || h.startsWith('#pricing') ? [] : pageItems(ringOn);
    if (!items.length) { if (el) el.hidden = true; return; }
    css();
    if (!el) {
      el = document.createElement('span'); el.id = 'twQPage'; el.className = 'twqp';
      el.innerHTML = '<button type="button" class="twqp-b" aria-expanded="false"></button><div class="twqp-pan" role="dialog" aria-label="本頁限制" hidden></div>';
      el.querySelector('.twqp-b').onclick = (e) => { e.stopPropagation(); const pan = el.querySelector('.twqp-pan'); pan.hidden = !pan.hidden; el.querySelector('.twqp-b').setAttribute('aria-expanded', String(!pan.hidden)); };
      document.addEventListener('click', (e) => { if (!el.contains(e.target)) { el.querySelector('.twqp-pan').hidden = true; el.querySelector('.twqp-b').setAttribute('aria-expanded', 'false'); } });
    }
    const rg = document.getElementById('twQRing'), tb = document.getElementById('twPageTourBtn'), h1 = document.querySelector('#l4Head h1');
    const desk = !!(h1 && h1.getClientRects().length);
    el.classList.toggle('mob', !desk);
    /* 手機（沒有 #l4Head）：頂欄已經被圓環、導覽、搜尋塞滿，再放一顆會撐出橫向捲軸（390 實測 scrollWidth 570）→ 改成左下角浮動的小膠囊 */
    if (desk) { const after = rg && !rg.hidden && rg.parentNode === h1.parentNode ? rg : (tb && tb.parentNode === h1.parentNode ? tb : h1); if (el.previousElementSibling !== after) after.after(el); }
    else if (el.parentNode !== document.body) document.body.appendChild(el);
    el.hidden = false;
    const lvl = (x) => (x.lim === 0 ? 'off' : x.rem === 0 ? 'out' : x.rem === 1 ? 'low' : 'ok');
    const min = items.filter((x) => x.lim > 0).reduce((a, x) => (a == null || x.rem < a.rem ? x : a), null);
    const b = el.querySelector('.twqp-b');
    const bt = `本頁 ${items.length} 項限制${min ? `・最少剩 ${min.rem} 次` : ''}`;
    if (b.textContent !== bt) b.textContent = bt;
    b.dataset.lvl = min ? lvl(min) : 'off';
    el.dataset.n = String(items.length);
    const html = `<div class="twqp-h">本頁的每日限制<small>台北 0 點重置・同一個對象同一天只算一次</small></div>` + items.map((x) => `<div class="twqp-r" data-id="${x.id}" data-lvl="${lvl(x)}">
      <div class="twqp-t"><b>${T() ? T().esc(x.name) : x.name}</b><span>${x.lim === 0 ? '不開放' : `${x.unit} ${x.used}／${x.lim}・剩 ${x.rem} 次`}</span></div>
      <i class="twqp-bar"><i style="width:${x.lim ? Math.round((x.used / x.lim) * 100) : 100}%"></i></i></div>`).join('')
      + '<a class="twqp-go" href="#pricing">看方案 →</a>';
    const pan = el.querySelector('.twqp-pan'); if (pan.dataset.h !== html) { pan.innerHTML = html; pan.dataset.h = html; }
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
.twqr{position:relative;display:inline-flex;align-items:center;justify-content:center;flex:none;width:42px;height:42px;margin-left:8px;vertical-align:middle;text-decoration:none;--qc:var(--cyan,#22d3ee)}
.twqr[hidden]{display:none}
.twqr svg{position:absolute;inset:0;width:100%;height:100%}
.twqr circle{fill:none;stroke-width:2.5}
.twqr .bg{stroke:color-mix(in srgb,var(--qc) 22%,transparent)}
.twqr .fg{stroke:var(--qc);stroke-linecap:round;transition:stroke-dasharray .3s}
.twqr b{position:relative;font-size:11px;font-weight:700;line-height:1;color:var(--qc);white-space:nowrap}
.twqr[data-lvl="mid"]{--qc:var(--amber,#f5b942)}
.twqr[data-lvl="out"]{--qc:var(--ink-3,#7a879c)}
.twqr.mob{margin:0 2px 0 0;width:36px;height:36px}
.twqp{position:relative;display:inline-flex;align-items:center;margin-left:8px;vertical-align:middle;flex:none}
.twqp[hidden]{display:none}
.twqp-b{appearance:none;font:inherit;font-size:12px;height:28px;padding:0 10px;border-radius:999px;border:1px solid var(--line-2);background:var(--panel-2);color:var(--ink-2);cursor:pointer;white-space:nowrap}
.twqp-b[data-lvl="low"]{border-color:var(--amber,#f5b942);color:var(--amber,#f5b942)}
.twqp-b[data-lvl="out"]{border-color:var(--down-r,#ef4b5f);color:var(--down-r,#ef4b5f)}
.twqp.mob{position:fixed;left:12px;bottom:84px;z-index:1250;margin:0}.twqp.mob .twqp-b{max-width:60vw;overflow:hidden;text-overflow:ellipsis;box-shadow:0 4px 12px rgba(0,0,0,.25)}
.twqp-pan{position:absolute;top:calc(100% + 6px);left:0;z-index:1300;width:min(320px,calc(100vw - 32px));padding:10px 12px;border-radius:10px;border:1px solid var(--line-2);background:var(--panel);box-shadow:0 8px 24px rgba(0,0,0,.3);font-size:13px;color:var(--ink)}
.twqp.mob .twqp-pan{position:fixed;left:16px;right:16px;top:auto;bottom:124px;width:auto;max-height:60vh;overflow:auto}
.twqp-pan[hidden]{display:none}
.twqp-h{font-weight:700;margin-bottom:6px}.twqp-h small{display:block;font-weight:400;font-size:12px;color:var(--ink-3)}
.twqp-r{padding:6px 0;border-top:1px solid var(--line)}
.twqp-t{display:flex;justify-content:space-between;gap:8px}.twqp-t b{font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.twqp-t span{flex:none;font-size:12px;color:var(--ink-2)}
.twqp-bar{display:block;height:4px;margin-top:4px;border-radius:2px;background:color-mix(in srgb,var(--ink-3) 25%,transparent);overflow:hidden}
.twqp-bar>i{display:block;height:100%;background:var(--cyan,#22d3ee)}
.twqp-r[data-lvl="low"] .twqp-bar>i{background:var(--amber,#f5b942)}.twqp-r[data-lvl="low"] .twqp-t span{color:var(--amber,#f5b942)}
.twqp-r[data-lvl="out"] .twqp-bar>i,.twqp-r[data-lvl="off"] .twqp-bar>i{background:var(--down-r,#ef4b5f)}.twqp-r[data-lvl="out"] .twqp-t span,.twqp-r[data-lvl="off"] .twqp-t span{color:var(--down-r,#ef4b5f)}
.twqp-go{display:block;margin-top:8px;text-align:right;font-size:12px}
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
        if (key == null) continue;
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
  /* ============================================================================
     ★ 2026-10-08 動作計次（docs/perm_matrix_1008.md §2）：quota.js 原本只數「區塊出現在畫面上」（visit／obj），
     矩陣新增四種單位 —— 都是「使用者主動做了某件事」才算，所以由各功能的點擊處呼叫，不靠 MutationObserver：
       tab    切分頁：點一個不同的分頁（同一分頁重切不重算；預設進來的第一個分頁呼叫端不送）
       filter 篩選：套用一組不同的篩選條件（條件序列化後當對象；清除／排序／翻頁呼叫端不送）
       drill  點擊下鑽：從圖上點進一個不同的下一層對象
       obj    看對象（題材剖析、產業鏈、週期統計換對象）
       pick   同時選取上限 —— 不是每日次數，存在範本 feats（kind:'limit'），用 pick() 讀
     單位字串＝「<單位>.<對象>」（非 ASCII 或太長→ FNV 雜湊，同 safeKey），workers/data-gw/tiers.js 的 actUnit() 是同一個函式，
     測試（workers/data-gw/tests/units.test.mjs）把兩邊跑同一組輸入比對。obj 單位沿用 pageKey 的 t.<題材>／c.<鏈>，
     跟畫面計次（evaluate）同一個 key、同一個儲存 —— 同一個題材不會被兩邊各扣一次。
     上限＝範本 lims（TwPerm.lim）：擁有者、預覽版一律 Infinity（perm.js owner()），不送 /v1/quota/hit。
     用完：跳 qcard 置中卡片，文案照矩陣 §2「{功能}今日 N/N 次已用完（每天台北時間 00:00 重置）。{升級句}」；剩 1 次時角落小字提醒。
     ============================================================================ */
  const UNIT_KINDS = ['view', 'obj', 'tab', 'filter', 'drill', 'pick'];
  function actUnit(kind, obj) {
    const o = String(obj == null ? '' : obj);
    if (kind === 'obj' && /^[tcdg]\./.test(o)) return safeKey(o);
    return safeKey(kind + '.' + o);
  }
  /* 升級句要的「下一個方案給幾次」：訂閱頁那一份方案 → 沒有就用建議方案（plan_presets.js）*/
  function planLim(planId, id) {
    const TP = window.TwPricing, ps = TP && TP.plans && TP.plans();
    const p = (ps || []).find((x) => x.id === planId);
    if (p && p.lims && Object.prototype.hasOwnProperty.call(p.lims, id)) return p.lims[id];
    const pr = window.TW_PLAN_PRESETS, t = pr && pr.tiers.find((x) => x.key === planId);
    if (t && t.lims && Object.prototype.hasOwnProperty.call(t.lims, id)) return t.lims[id];
    return p || t ? Infinity : null;
  }
  function meTier() { const st = P() ? P().state() : {}; return st.who === 'guest' || !st.who ? 'guest' : (!st.plan || st.plan === 'free' ? 'free' : st.plan); }
  function actOpts(id, n, used) {
    const f = F() && F().byId(id); const nm = f ? f.name : id;
    const tier = meTier();
    let up, btn, href;
    if (tier === 'guest') { const k = planLim('free', id); up = k === Infinity ? '免費註冊即可不限次數' : `免費註冊即可每天 ${k == null ? '更多' : k} 次`; btn = '免費註冊'; href = '#pricing/plan/free'; }
    else if (tier === 'free') { const k = planLim('plus', id); up = k === Infinity || k == null ? '升級 Plus 不限次數' : `升級 Plus 每天 ${k} 次`; btn = '看方案'; href = '#pricing/need/' + encodeURIComponent(id); }
    else { up = '升級 Pro 不限次數'; btn = '看方案'; href = '#pricing/need/' + encodeURIComponent(id); }
    if (n === 0) {
      const lo = f && window.TwQCard ? window.TwQCard.lockOpts(f, tier === 'guest' ? 'guest' : 'member') : null;
      return Object.assign(lo || { kind: 'lock', kick: '需要開通', title: '此功能需開通', sub: nm, btn, href }, { title: `${nm}為${tier === 'guest' ? '會員' : '付費'}功能`, btnCls: 'qactgo' });
    }
    return { kind: 'quota', kick: '每日次數', title: `${nm}今日 ${used}/${n} 次已用完`, sub: `（每天台北時間 00:00 重置）。${up}`,
      used, limit: n, lh: '', items: [], btn, href, btnCls: 'qactgo' };
  }
  function actBlock(id, n, used) {
    const QC = window.TwQCard;
    const m = QC && QC.modal ? QC.modal(actOpts(id, n, used)) : null;
    if (m) m.dataset.cq = id;
    return false;
  }
  function remainHint(id, rem) {
    if (rem !== 1) return;
    let t = document.getElementById('twQRem');
    if (!t) { t = document.createElement('div'); t.id = 'twQRem'; t.setAttribute('role', 'status');
      t.style.cssText = 'position:fixed;right:16px;bottom:84px;z-index:1400;padding:6px 12px;border-radius:999px;font-size:12px;background:var(--panel-3,#1c2638);color:var(--amber,#f5b942);border:1px solid var(--line-2,#33415a)';
      document.body.appendChild(t); }
    const f = F() && F().byId(id);
    t.textContent = `${f ? f.name : ''}：今日剩 1 次`; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => { t.hidden = true; }, 3500);
  }
  /* 用一次：回 true＝放行、false＝擋下（已跳卡片）。obj 空字串＝不算（呼叫端的「預設」）*/
  function act(id, kind, obj) {
    try { const ts = window.TwTour && window.TwTour.state(); if (ts && ts.on) return true; } catch (e) { /* 沒有導覽 */ }
    const n = limitOf(id);
    if (n === Infinity) return true;
    if (n === 0) return actBlock(id, 0, 0);
    const key = actUnit(kind, obj);
    const d = load(); const set = new Set(d.k[id] || []);
    if (set.has(key)) return true;
    if (set.size >= n) return actBlock(id, n, set.size);
    set.add(key); d.k[id] = [...set]; save(d); hit(id, key);
    remainHint(id, n - set.size);
    schedule();   // 本頁限制清單的「已用」跟著 +1
    return true;
  }
  /* 同時選取上限（feats 的 limit 類；最大值＝不限）。擁有者／預覽版／連不到會員伺服器＝不限 */
  function pick(id) {
    const p = P(), Ft = F(); if (!p || !Ft) return Infinity;
    if (p.owner && p.owner()) return Infinity;
    if (p.state().src === 'default') return Infinity;
    const f = Ft.byId(id); if (!f) return Infinity;
    const v = p.value ? p.value(id) : p.limit(id, f.max);
    return !Number.isInteger(v) || v >= f.max ? Infinity : Math.max(0, v);
  }
  function pickBlock(id, n) {
    const QC = window.TwQCard; if (!QC || !QC.modal) return false;
    const f = F() && F().byId(id), tier = meTier(), u = (f && f.unit) || '個';
    const nm = f ? f.name : id;
    const up = tier === 'guest' ? '免費註冊可以選更多' : tier === 'free' ? '升級 Plus 可以選更多' : '升級 Pro 不限';
    const m = QC.modal({ kind: 'lock', kick: '同時選取上限', title: `${tier === 'guest' ? '訪客' : '目前方案'}最多 ${n} ${u}`, sub: `${nm}。${up}。`,
      lh: '', items: [], btn: tier === 'guest' ? '免費註冊' : '看方案', href: tier === 'guest' ? '#pricing/plan/free' : '#pricing/need/' + encodeURIComponent(id), btnCls: 'qactgo' });
    m.dataset.cq = id;
    return false;
  }
  /* 路由閘（app.js route() 開頭呼叫）：Andy「題材可以點 至多3個熱力圖（上方熱力圖不用鎖住，主要是限制點擊後功能），包含產業Map 也是只能3個」。
     題材剖析＝heat.detail、單一產業鏈＝ind.groups（矩陣 §3.4／§3.5），對象 key 跟畫面計次同一個（t.<題材>／c.<鏈>）。
     用完 → 網址退回上一層（題材熱力圖／產業地圖，上方熱力圖照樣在）並跳卡片；回 false 讓 route() 不畫被擋的那一頁。*/
  function routeOk(hash) {
    const h = String(hash || '');
    let m = /^#industry\/([^/?]+)/.exec(h);
    if (m && m[1] !== 'group') { if (act('ind.groups', 'obj', 'c.' + decodeURIComponent(m[1]))) return true; location.replace('#industry'); return false; }
    m = /^#heatmap\/theme\/([^/?]+)/.exec(h);
    if (m) { if (act('heat.detail', 'obj', 't.' + decodeURIComponent(m[1]))) return true; location.replace('#heatmap/theme'); return false; }
    return true;
  }
  /* ============================================================================
     ★ 2026-10-08 熱力圖點擊跳頁（features.js heat.link；Andy：「熱力圖如果不是付費會員 都不能有點擊連結功能，但如果是才可以點擊連結到其他分頁」）
     全站樹狀熱力圖的點擊處理散在 app.js／industry.js 好幾支（卡片與放大視窗各一份），各自 `location.hash = …`／goStock()。
     不逐支改：捕獲階段記下「這一下點在 treemap 上」（找得到 ECharts 實例、而且 series 有 treemap），
     緊接著（800ms 內）發生的換頁若是**換到別的分頁**（網址前兩段不同）就擋下：網址退回、跳升級卡。
     同一分頁內的變化（題材頁點方塊開下方剖析圖 #heatmap/theme → #heatmap/theme/<id>）不算跳頁，照矩陣的次數規則走（routeOk 下一段）。
     沒權限時游標不顯示手指：滑過 treemap 就在它的容器掛 data-hmnl，CSS 用 !important 蓋掉 zrender 寫在行內的 cursor:pointer。
     擁有者、預覽版、連不到會員伺服器（src＝default，寧可多給）一律放行。
     ============================================================================ */
  const HM = { t: 0, from: '' };
  /* ★ 2026-10-08 晚（Andy 313：「熱門題材、資金熱力圖，點擊會到該個股的功能需要權限設定，只有 Plus 以上才可以」）：
     以前這裡「連不到會員伺服器（src＝default）一律放行」—— 但訪客在公司網路、Worker 冷啟動逾時、/v1/perm/me 還沒回來的那幾秒，
     src 都是 default，於是訪客照樣點得進個股頁。改成：會員系統有開（TwAccount.on()）就一律照身分判斷，
     範本沒寫時由 perm.js 的 value() 依 defBy 給預設（訪客關、註冊會員關、付費範本開），不靠「套用建議方案」。
     只有整個會員系統沒設定（repo 本身、本機驗收：account_config.js api 空白＝沒有方案這回事）才放行。
     管理員（/v1/me 的 admin 旗標）跟站主一樣放行。*/
  function heatLinkOk() {
    const p = P(); if (!p || window.TW_PREVIEW) return true;
    if (p.owner && p.owner()) return true;
    const A = window.TwAccount, u = A && A.on && A.on() && A.user && A.user();
    if (!A || !A.on || !A.on()) return true;
    if (u && u.admin) return true;
    return p.can('heat.link');
  }
  /* 只認「點在圖的 canvas 上」：ECharts 的結構是 初始化容器 > zrender 外框 > canvas。
     不往上一路找祖先 —— 有些容器（例如產業地圖整個 view）曾經被拿來初始化過 treemap、實例還掛著，
     一路往上找會把點分頁鈕也當成點熱力圖（2026-10-08 驗收實測：產業地圖點產業鏈分頁被誤擋）。*/
  function hmHost(t) {
    const E = window.echarts; if (!E || !E.getInstanceByDom || !t || t.tagName !== 'CANVAS') return null;
    for (let el = t.parentElement, i = 0; el && i < 3; el = el.parentElement, i++) {
      const inst = E.getInstanceByDom(el);
      if (inst) { try { return ((inst.getOption() || {}).series || []).some((x) => x.type === 'treemap') ? el : null; } catch (e) { return null; } }
    }
    return null;
  }
  const pageOf = (h) => String(h || '#overview').split('?')[0].split('/').slice(0, 2).join('/');
  document.addEventListener('click', (e) => { if (hmHost(e.target)) { HM.t = Date.now(); HM.from = location.hash || '#overview'; } }, true);
  document.addEventListener('mousemove', (e) => {
    const el = hmHost(e.target); if (!el) return;
    /* data-hmstay＝這張圖的點擊只在原地展開（題材層換成分股、題材頁開下方剖析圖），不是跳頁 → 手指照常 */
    const no = !heatLinkOk() && !el.hasAttribute('data-hmstay');
    if (no && !el.hasAttribute('data-hmnl')) el.setAttribute('data-hmnl', ''); else if (!no && el.hasAttribute('data-hmnl')) el.removeAttribute('data-hmnl');
    if (T()) T().css('hmnlCss', '[data-hmnl],[data-hmnl] *{cursor:default!important}');
  }, { capture: true, passive: true });
  /* to＝原本要去的網址：去個股頁的用 Andy 313 指定的那句（「點熱力圖看個股是 Plus 以上功能」），其餘（族群／題材／產業鏈頁）沿用原本的標題 */
  function heatLinkBlock(to) {
    const QC = window.TwQCard; const tier = meTier();
    const stk = /^#stock\//.test(String(to || ''));
    const lo = QC && QC.lockOpts ? QC.lockOpts({ id: 'heat.link', name: '熱力圖點擊跳頁', cat: 'heatmap' }, tier === 'guest' ? 'guest' : 'member') : {};
    const m = QC && QC.modal ? QC.modal(Object.assign({}, lo, { kind: 'lock', kick: '付費會員功能',
      title: stk ? '點熱力圖看個股是 Plus 以上功能' : '點擊熱力圖跳到族群／題材頁是付費會員功能',
      sub: '提示框、縮放照常可用；升級 Plus／Pro 就能從熱力圖直接點進族群、題材與個股頁。', lh: '這些方案可以使用',
      items: [{ t: 'Plus', s: '點方塊直接跳頁' }, { t: 'Pro', s: '點方塊直接跳頁' }], btn: '升級 Plus', href: '#pricing/need/heat.link', btnCls: 'qactgo' })) : null;
    if (m) m.dataset.cq = 'heat.link';
    /* 手機的「幽靈點擊」：zrender 在 touchend 就發 click → 這裡開出升級卡；瀏覽器接著在同一個座標補發原生 click，
       正好落在剛開的卡片上（實測 390 觸控：直接按到「升級 Plus」被帶到訂閱頁，或點到背景把卡片關掉）。
       開卡後 450ms 內落在卡片上的 click 一律吃掉；之後使用者自己按的照常。*/
    const t0 = Date.now();
    const eat = (e) => {
      if (Date.now() - t0 > 450) { document.removeEventListener('click', eat, true); return; }
      const qm = document.getElementById('qcModal');
      if (qm && e.target && qm.contains(e.target)) { e.preventDefault(); e.stopImmediatePropagation(); }
    };
    document.addEventListener('click', eat, true);
    setTimeout(() => document.removeEventListener('click', eat, true), 500);
  }
  /* 熱力圖的點擊處理要跳到別的分頁時一律先問這支（app.js／industry.js 的 treemap click）：可以就照做、不行就跳升級卡、回 false。
     為什麼不只靠下面的「捕獲 click → 800ms 內換頁就退回」：手機上 zrender 在 touchend 就發出 click 事件、
     先改了 location.hash，瀏覽器補發的原生 click 晚到 → 捕獲記錄還沒寫，hashchange 已經過去，擋不到。
     點擊處理自己先問，就不必猜事件的先後。捕獲那一層留著當保險（漏接的跳頁路徑照樣擋）。*/
  function heatGo(to, fn) {
    HM.t = 0;      // 這一下已經判過了：不要讓捕獲那一層再判一次（擋下時也清，不然 800ms 內按升級卡的「升級 Plus」會被當成熱力圖跳頁）
    if (heatLinkOk()) { if (fn) fn(); else location.hash = to; return true; }
    heatLinkBlock(to); return false;
  }
  function routeOkAll(hash) {
    if (HM.t && Date.now() - HM.t < 800) {
      const from = HM.from; HM.t = 0;
      if (pageOf(hash) !== pageOf(from) && !/^#pricing/.test(String(hash)) && !heatLinkOk()) {   // 去訂閱頁（升級卡的按鈕）永遠放行
        location.replace(from); heatLinkBlock(hash); return false; }
    }
    return routeOk(hash);
  }
  /* 也在自己的 hashchange 擋一次（quota.js 比 app.js 早載入，這支監聽先跑）：app.js 的 route() 是 async，
     上一次換頁還沒畫完就再換（例如產業地圖剛回來就點下一條鏈）時，實測有幾次換頁沒有走到 route() 開頭 → 漏算。
     act() 同一個對象不重算，所以兩邊都呼叫不會多扣；被擋時這裡先把網址換回去，route() 讀到的就是上一層。*/
  window.addEventListener('hashchange', () => { routeOkAll(location.hash); });
  window.TwQuota = { act, pick, pickBlock, routeOk: routeOkAll, heatLinkOk, heatGo, actUnit, UNIT_KINDS, used: (id) => (load().k[id] || []).slice(),
    state: () => load(), limit: limitOf, evaluate: () => evaluate(), day: tpeDay, pageKey, unitKey: (id, h) => unitKey(window.TwFeatures && window.TwFeatures.byId(id), h || location.hash || ''), unitKind: (id) => unitKind(window.TwFeatures && window.TwFeatures.byId(id)) };
})();
