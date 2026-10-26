/* ============================================================================
   科技透明圈（#tc → #tc/<產業id> → #tc/<產業id>/<公司>）—— 2026-10-25 建
   這一頁回答的問題：「科技業各產業、各公司、各單位的職位，實際工時／底薪／分紅／年薪／加班長怎樣？」
   怎麼用：先挑產業，用上面五組篩選縮小（篩選對公司卡與職位表同時生效），點公司卡看單位→職位表。
   資料：site/tc/json/<產業id>.json（格式見 docs/tc/schema.md，由他人產出、前端只讀）。檔案還不存在的產業照樣有分頁，內容顯示「尚無資料」。
   數字全是區間，篩選一律拿區間中點比；工時、加班是單一值／分類。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const INDS = [['foundry', '晶圓代工'], ['memory', '記憶體'], ['osat', '封測'], ['material', '半導體材料'], ['equipment', '半導體設備'], ['icdesign', 'IC 設計'], ['odm', '電子代工 ODM'], ['panel', '面板／光學'], ['foreign', '外商'], ['other', '其他科技']];
  /* ★ 2026-10-25（Andy：「這內容就算上線了也只有我可以看，其他 Plus Pro 都先隱藏」）：只有管理者（站主＋站主加的人）看得到。
     判定沿用 livegate.js 同一條：/v1/me 的 admin／owner 旗標（TwAccount.user()，還沒載入退回登入快取）。
     非管理者：html 不掛 .tc-adm → m4/20261025-tc.css 把側欄與手機導覽的入口藏掉，直接打 #tc 導回總覽。
     本機驗收用 window.TW_TC_OVERRIDE（只在 localhost／127.0.0.1 生效）。 */
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;   // 預覽版全開（DECISIONS #343），正式站沒有這個旗標
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_TC_OVERRIDE === true || window.TW_TC_OVERRIDE === false)) return window.TW_TC_OVERRIDE;
      const A = window.TwAccount; let u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  /* 10-25 修（Andy：預覽版登入後「點擊後沒東西」）：開頁時 /v1/me 還沒回來，isAdm() 一定是 false，
     以前就當場導回總覽、內容也不畫。現在等身分確定（第一次 tw:account 或 6 秒逾時）才判定要不要導走；
     確定是管理者而且停在 #tc，就重跑一次路由把內容畫出來。 */
  let known = false;
  function gate() {
    const on = isAdm();
    document.documentElement.classList.toggle('tc-adm', on);
    if (!on && known && /^#tc(\/|$)/.test(location.hash || '')) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', () => {
    known = true;
    if (gate() && /^#tc(\/|$)/.test(location.hash || '')) window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
  setTimeout(() => { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  const FOOT = '資料整理自 GoodJob、Dcard、PTT 等公開分享，僅供參考';

  /* 篩選：k＝角色欄位、opts＝[顯示字, 判斷函式]；第一個永遠是「全部」 */
  const mid = (a) => (typeof a === 'number' ? a : Array.isArray(a) && a.length ? (a[0] + a[a.length - 1]) / 2 : null);
  /* 真資料的工時可能是區間或空、加班是自由文字（例「偶爾～經常（依部門）」）：缺值一律不通過數值篩選；加班依字面歸類，同時含兩類的兩邊都算 */
  const has = (v) => v != null;
  const otIs = (r, w) => { const t = String(r.overtime || ''); return w === '幾乎不' ? /幾乎不|很少|不加班/.test(t) : t.includes(w); };
  const FILTERS = [
    { k: 'hours', t: '工時', opts: [['全部'], ['≤45', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) <= 45], ['46–50', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 45 && mid(r.weekly_hours) <= 50], ['51–55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 50 && mid(r.weekly_hours) <= 55], ['>55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 55]], tip: '每週工時（小時）' },
    { k: 'base', t: '底薪', opts: [['全部'], ['≥50K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 50], ['≥60K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 60], ['≥70K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 70], ['≥80K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 80]], tip: '月底薪區間的中點' },
    { k: 'bonus', t: '分紅月數', opts: [['全部'], ['≥4', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 4], ['≥8', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 8], ['≥12', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 12]], tip: '年終＋分紅合計月數區間的中點' },
    { k: 'annual', t: '年薪', opts: [['全部'], ['≥100萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 100], ['≥150萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 150], ['≥200萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 200], ['≥300萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 300]], tip: '年薪總額（萬）區間的中點' },
    { k: 'ot', t: '加班', opts: [['全部'], ['幾乎不', (r) => otIs(r, '幾乎不')], ['偶爾', (r) => otIs(r, '偶爾')], ['經常', (r) => otIs(r, '經常')]], tip: '加班狀況' },
  ];
  const S = { ind: '', co: '', f: {}, sort: { k: '', d: -1 }, fopen: false, data: {}, loaded: false, chm: 'base', rk: { m: 'ann', ind: 'all', all: false }, agg: null };

  /* 分紅發放欄只放「幾月」：從公司層 bonus_timing 抓出所有「N 月」，抓不到顯示「—」（完整說明留在公司頁頂端） */
  const btMonths = (t) => { const m = String(t || '').match(/\d{1,2}\s*月/g); return m ? Array.from(new Set(m.map((x) => x.replace(/\s/g, '')))).join('、') : '—'; };
  /* 分紅結構：公司層 bonus_structure（每種獎金一筆）。摘要與頂端區塊都從它組；沒有就退回 bonus_timing */
  const bsum = (c) => {
    const bs = Array.isArray(c.bonus_structure) ? c.bonus_structure : [];
    const parts = bs.map((x) => {
      const r = String(x.rule || ''), pk = r.match(/(\d+)\s*包/), mm = r.match(/\d{1,2}(?:[／\/、]\d{1,2})+\s*月/), nx = r.match(/隔年\s*(\d{1,2})\s*月/);
      if (pk && mm) return pk[1] + ' 包（' + mm[0].replace(/\s*月/, '').replace(/[／、]/g, '/') + (nx ? '＋隔年' + nx[1] + '月' : '') + '）';
      if (x.months != null) return String(x.type || '').replace(/獎金$/, '') + x.months + '個月';
      return '';
    }).filter(Boolean);
    return parts.length ? parts.join('＋') : (c.bonus_timing ? clip(c.bonus_timing, 14) : '—');
  };
  const bonusBlock = (co) => {
    const bs = Array.isArray(co.bonus_structure) ? co.bonus_structure : [];
    const src = (x) => (x.sources || []).filter((s) => s && s.url).map((s) => '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.site || '來源') + (s.date ? ' ' + esc(s.date) : '') + '</a>').join('・');
    let body;
    if (bs.length) body = bs.map((x) => '<div class="tc-bsr"><b>' + esc(x.type || '—') + '</b><span>' + esc(x.rule || '—') + '</span><em>' + (x.months != null ? esc(x.months) + ' 個月' : '月數不固定') + '</em><small>' + src(x) + '</small></div>').join('');
    else if (co.bonus_timing) body = '<div class="tc-bsr"><span>' + esc(co.bonus_timing) + '</span></div>';
    else return '';
    const n = bs.length;
    const ttl = '分紅結構' + (n ? '（' + n + ' 種獎金）' : '（發放時間）');
    return matchMedia('(max-width:640px)').matches ? '<details class="tc-bs"><summary>' + ttl + '</summary>' + body + '</details>' : '<div class="tc-bs"><h5>' + ttl + '</h5>' + body + '</div>';
  };
  const dash = (x) => (x === '–' ? '—' : x);
  const rng = (a, u) => (Array.isArray(a) && a.length ? (a[0] === a[a.length - 1] ? a[0] : a[0] + '–' + a[a.length - 1]) + (u || '') : '—');
  const roleOk = (r) => FILTERS.every((F) => { const i = S.f[F.k] || 0; return i === 0 || F.opts[i][1](r); });
  const nActive = () => FILTERS.filter((F) => (S.f[F.k] || 0) > 0).length;
  const sortVal = { base: (r) => mid(r.base_month_k), bonus: (r) => mid(r.bonus_months), annual: (r) => mid(r.annual_total_wan), hours: (r) => mid(r.weekly_hours), n: (r) => r.n };

  async function loadAll() {
    if (S.loaded) return;
    await Promise.all(INDS.map(async ([id]) => {
      try { const r = await fetch('tc/json/' + id + '.json', { cache: 'no-cache' }); S.data[id] = r.ok ? await r.json() : null; }
      catch (e) { S.data[id] = null; }
    }));
    /* 職位區間若有 samples 就由 samples 算（最小～最大），沒有才用手填值 */
    const mm = (a) => { a = [].concat(...a.map(fl)); return a.length ? [Math.min(...a), Math.max(...a)] : null; };
    Object.values(S.data).forEach((d) => d && (d.companies || []).forEach((c) => (c.roles || []).forEach((r) => {
      const sm = (Array.isArray(r.samples) ? r.samples : []).filter(inWin); if (!sm.length) return;
      r.n = sm.length;
      [['base_month_k', 'base_k'], ['bonus_months', 'bonus_months'], ['annual_months', 'annual_months'], ['annual_total_wan', 'annual_wan'], ['weekly_hours', 'weekly_hours']].forEach(([a, b]) => { const v = mm(sm.map((x) => x[b])); if (v) r[a] = v; });
    })));
    S.loaded = true;
  }

  /* 「?」小說明：點開浮出、點背景關閉（Andy 規矩 B2：說明收進 ?） */
  function howHtml() {
    return '<span class="tc-how"><button class="howbtn tc-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button>' +
      '<div class="tc-pop" hidden><b>怎麼用</b><br>上方挑產業，五組篩選（工時、底薪、分紅月數、年薪、加班）同時作用在公司卡與職位表；點公司卡看各單位的職位。' +
      '數字都是整理後的區間，篩選拿區間中點比；信心度低代表來源少或彼此對不起來。' + '<br>「樣本統計」分頁：橫條是中位數、細線是最低到最高；越長代表該產業（公司）給得越高，線越長代表落差越大、談薪空間越大；公司排行可切底薪／年薪並按產業篩選，點一列進公司頁。' + '<br><span class="muted">' + esc(FOOT) + '</span></div></span>';
  }
  function bindHow(root) {
    const b = $('.tc-q', root), p = $('.tc-pop', root); if (!b || !p) return;
    const close = () => { p.hidden = true; b.setAttribute('aria-expanded', 'false'); };
    b.onclick = (e) => { e.stopPropagation(); p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); };
    document.addEventListener('click', (e) => { if (!p.hidden && !p.contains(e.target)) close(); });
  }

  function filterBar() {
    const n = nActive();
    return '<div class="tc-fbar"><button class="tc-ftog" type="button" aria-expanded="' + S.fopen + '">篩選' + (n ? '（' + n + '）' : '') + '</button>' +
      '<div class="tc-fgrp' + (S.fopen ? ' open' : '') + '">' + FILTERS.map((F) =>
        '<div class="tc-f" title="' + esc(F.tip) + '"><span class="tc-fl">' + F.t + '</span><div class="seg" data-fk="' + F.k + '">' +
        F.opts.map((o, i) => '<button type="button" data-i="' + i + '" class="' + ((S.f[F.k] || 0) === i ? 'on' : '') + '">' + esc(o[0]) + '</button>').join('') + '</div></div>').join('') +
      '<button class="tc-clear" type="button"' + (n ? '' : ' hidden') + '>清除篩選</button></div></div>';
  }

  /* 來源欄只放統計「N 筆（Dcard x／GoodJob y／PTT z）」，明細看 ▸ 展開的逐筆樣本 */
  function srcHtml(r) {
    const ss = r.sources || []; if (!ss.length) return '–';
    const m = {}; ss.forEach((x) => { m[x.site] = (m[x.site] || 0) + 1; });
    return '<span title="' + esc(Object.keys(m).map((k) => k + ' ' + m[k]).join('／')) + '">' + ss.length + ' 筆</span>';
  }
  const confCls = (c) => (c === '高' ? 'hi' : c === '中' ? 'mid' : 'lo');

  /* 只有 date_confirmed:true 且 date ≥ 2025-08 的樣本進統計；日期未確認標「日期未確認」、範圍外標「範圍外參考」，都照列但標灰 */
  const smSt = (x) => (x.date_confirmed !== true ? 'unc' : (x.in_window === false || !x.date || String(x.date) < '2025-08' ? 'out' : 'in'));
  const inWin = (x) => smSt(x) === 'in';
  const fl = (v) => (typeof v === 'number' ? [v] : Array.isArray(v) ? v.filter((x) => typeof x === 'number') : []);   // 樣本值可能是區間陣列：展開成數值
  const mdp = (v) => { const a = fl(v); return a.length ? (Math.min(...a) + Math.max(...a)) / 2 : null; };   // 區間取中點
  const nv = (v) => { if (v == null) return '—'; if (Array.isArray(v)) { const a = fl(v); if (!a.length) return '—'; const lo = Math.min(...a), hi = Math.max(...a); return lo === hi ? lo : lo + '–' + hi; } return v; };
  function smRow(r) {
    const sm = r.samples || []; if (!sm.length) return '';
    return '<tr class="tc-smrow" hidden><td colspan="14"><div class="tc-smw"><table class="tc-smt"><thead><tr>' + ['來源・日期', '單位細項', '年資', '學歷', '底薪(K)', '年薪(萬)', '分紅月數', '工時', '加班', '摘要'].map((x) => '<th>' + x + '</th>').join('') + '</tr></thead><tbody>' +
      sm.map((x) => '<tr' + (inWin(x) ? '' : ' class="tc-out" title="不進統計"') + '><td data-l="來源・日期">' + (smSt(x) === 'unc' ? '<em>日期未確認</em> ' : smSt(x) === 'out' ? '<em>範圍外參考</em> ' : '') + (/^https?:\/\//.test(x.url || '') ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer">' + esc(x.site || '連結') + '</a>' : esc(x.site || '—')) + ' ' + esc(x.date || '') + '</td><td data-l="單位細項">' + esc(nv(x.unit_detail)) + '</td><td data-l="年資">' + esc(nv(x.years)) + '</td><td data-l="學歷">' + esc(nv(x.degree)) + '</td><td data-l="底薪(K)">' + nv(x.base_k) + '</td><td data-l="年薪(萬)">' + nv(x.annual_wan) + '</td><td data-l="分紅月數">' + nv(x.bonus_months) + '</td><td data-l="工時">' + nv(x.weekly_hours) + '</td><td data-l="加班">' + esc(nv(x.overtime)) + '</td><td data-l="摘要">' + esc(nv(x.quote_free_note)) + '</td></tr>').join('') + '</tbody></table></div></td></tr>';
  }
  const med = (a) => { a = a.filter((v) => typeof v === 'number').sort((x, y) => x - y); if (!a.length) return null; const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  const stat = (a) => { const v = [].concat(...a.map(fl)), m = a.map(mdp).filter((x) => x != null); return v.length ? med(m) + '（' + Math.min(...v) + '–' + Math.max(...v) + '）' : '—'; };

  /* ---------- 圖表化（2026-10-26）：各產業中位數＋區間、樣本筆數、公司排行（含 LOGO） ---------- */
  function aggStats() {
    const mk = (sm) => { const f = (k) => { const raw = sm.map((x) => x[k]), v = [].concat(...raw.map(fl)), m = raw.map(mdp).filter((x) => x != null); return v.length ? { med: med(m), min: Math.min(...v), max: Math.max(...v), n: m.length } : null; }; return { n: sm.length, base: f('base_k'), ann: f('annual_wan') }; };
    const inds = [], cos = [];
    INDS.forEach(([id, n]) => {
      const d = S.data[id]; if (!d) return; let all = [];
      (d.companies || []).forEach((c) => {
        const sm = [].concat(...(c.roles || []).map((r) => (r.samples || []).filter(inWin))); if (!sm.length) return;
        all = all.concat(sm); cos.push(Object.assign({ ind: id, indName: n, name: c.name }, mk(sm)));
      });
      if (all.length) inds.push(Object.assign({ id, name: n }, mk(all)));
    });
    return { inds, cos };
  }
  const RK_SHOW_D = 15, RK_SHOW_M = 10, mob = () => matchMedia('(max-width:640px)').matches;
  function rankHtml(A) {
    const m = S.rk.m, key = m === 'base' ? 'base' : 'ann', unit = m === 'base' ? 'K/月' : '萬/年';
    const list = A.cos.filter((c) => c[key] && (S.rk.ind === 'all' || c.ind === S.rk.ind)).sort((a, b) => b[key].med - a[key].med);
    const top = S.rk.all ? list : list.slice(0, (mob() ? RK_SHOW_M : RK_SHOW_D)), mx = Math.max(1, ...list.map((c) => c[key].max));
    const seg = (k, arr) => '<div class="seg" data-rk="' + k + '">' + arr.map(([v, t]) => '<button type="button" data-v="' + v + '" class="' + (String(S.rk[k]) === v ? 'on' : '') + '">' + esc(t) + '</button>').join('') + '</div>';
    const indOpts = [['all', '全部產業']].concat(A.inds.map((x) => [x.id, x.name]));
    return '<div class="tc-rkbar"><span class="tc-fl">排行依</span>' + seg('m', [['ann', '年薪'], ['base', '底薪']]) + '<span class="tc-fl">產業</span>' + seg('ind', indOpts) + '</div>' +
      '<div class="tc-cnt">共 <b>' + list.length + '</b> 家有樣本（中位數由高到低；細線＝最低到最高；單位 ' + unit + '）</div>' +
      (list.length ? '<div class="tc-rk">' + top.map((c, i) => { const v = c[key], w = Math.max(2, v.med / mx * 100), l = v.min / mx * 100, r = v.max / mx * 100;
        return '<a class="tc-rkr" href="#tc/' + c.ind + '/' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '"><span class="tc-rkn">' + (i + 1) + '</span>' + TL(c.name, c.ind, 24) + '<span class="tc-rkt">' + esc(c.name) + '<small>' + esc(c.indName) + '・' + c.n + ' 筆</small></span>' +
          '<span class="tc-rkb"><i class="tc-rkbar" style="width:' + w.toFixed(1) + '%"></i><i class="tc-rkrg" style="left:' + l.toFixed(1) + '%;width:' + Math.max(0.5, r - l).toFixed(1) + '%"></i></span>' +
          '<span class="tc-rkv"><b>' + v.med + '</b><small>' + v.min + '–' + v.max + '</small></span></a>'; }).join('') + '</div>' +
        (list.length > (mob() ? RK_SHOW_M : RK_SHOW_D) ? '<button type="button" class="tc-rkmore">' + (S.rk.all ? '只看前 ' + RK_SHOW : '看全部 ' + list.length + ' 家') + '</button>' : '') : '<div class="empty isempty tc-empty">這個產業沒有樣本</div>');
  }
  const TL = (name, ind, sz) => (window.TcLogo ? window.TcLogo.html(name, ind, sz) : '');
  function bindRank(root) {
    $$('.seg[data-chm] button', root).forEach((b) => b.onclick = () => { S.chm = b.dataset.v; $$('.seg[data-chm] button', root).forEach((x) => x.classList.toggle('on', x === b)); const g = $('.tc-gr', root); if (g) g.dataset.m = S.chm; window.dispatchEvent(new Event('resize')); });
    const A = S.agg, box = $('#tcRank', root); if (!box) return;
    $$('.seg[data-rk] button', box).forEach((b) => b.onclick = () => { const k = b.parentNode.dataset.rk; S.rk[k] = b.dataset.v; S.rk.all = false; box.innerHTML = rankHtml(A); bindRank(root); });
    const mo = $('.tc-rkmore', box); if (mo) mo.onclick = () => { S.rk.all = !S.rk.all; box.innerHTML = rankHtml(A); bindRank(root); };
  }
  const cv = (n, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d; } catch (e) { return d; } };
  const INK2 = () => cv('--ink-2', '#5b6b80'), INK3 = () => cv('--ink-3', '#8a97ab');
  function indBarOpt(A, key, unit, color) {
    const rows = A.inds.filter((x) => x[key]).sort((a, b) => a[key].med - b[key].med);   // 升冪＋橫條由下往上畫＝最高在最上
    const rng = rows.map((x, i) => [x[key].min, x[key].max, i]);
    return { grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, formatter: (p) => { const x = rows[p[0].dataIndex]; return esc(x.name) + '<br>中位數 <b>' + x[key].med + '</b> ' + unit + '<br>區間 ' + x[key].min + '–' + x[key].max + '<br>樣本 ' + x[key].n + ' 筆'; } },
      xAxis: { type: 'value', axisLabel: { color: INK3(), fontSize: 12 }, splitLine: { lineStyle: { opacity: .15 } } },
      yAxis: { type: 'category', data: rows.map((x) => x.name), axisLabel: { color: INK2(), fontSize: 12 }, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { type: 'bar', data: rows.map((x) => x[key].med), barWidth: 12, itemStyle: { borderRadius: [0, 3, 3, 0], color: color }, showBackground: true, backgroundStyle: { color: 'rgba(120,140,170,.12)', borderRadius: 3 }, z: 2,
          label: { show: false } },
        { type: 'custom', data: rng, z: 3, silent: true, tooltip: { show: false },
          renderItem: (params, api) => { const a = api.coord([api.value(0), api.value(2)]), b = api.coord([api.value(1), api.value(2)]), st = { stroke: '#ffb454', lineWidth: 2 };
            return { type: 'group', children: [{ type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: st }, { type: 'line', shape: { x1: a[0], y1: a[1] - 5, x2: a[0], y2: a[1] + 5 }, style: st }, { type: 'line', shape: { x1: b[0], y1: b[1] - 5, x2: b[0], y2: b[1] + 5 }, style: st }] }; } }
      ] };
  }
  function drawStats() {
    const A = S.agg, ch = window.App && window.App.chart; if (!A || !ch) return;
    const mkH = (n) => Math.max(120, n * 30 + 24);
    const draw = (id, key, unit, color) => { const el = document.getElementById(id); if (!el) return; const n = A.inds.filter((x) => x[key]).length; el.style.height = mkH(n) + 'px'; ch(el, indBarOpt(A, key, unit, color)); };
    draw('tcChBase', 'base', 'K/月', '#3ee0ff'); draw('tcChAnn', 'ann', '萬/年', '#8b7bff');
    const el = document.getElementById('tcChN'); if (el) {
      const rows = A.inds.slice().sort((a, b) => a.n - b.n); el.style.height = mkH(rows.length) + 'px';
      ch(el, { grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true }, tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true, formatter: (p) => esc(rows[p[0].dataIndex].name) + '<br>樣本 <b>' + rows[p[0].dataIndex].n + '</b> 筆' },
        xAxis: { type: 'value', axisLabel: { color: INK3(), fontSize: 12 }, splitLine: { lineStyle: { opacity: .15 } } },
        yAxis: { type: 'category', data: rows.map((x) => x.name), axisLabel: { color: INK2(), fontSize: 12 }, axisTick: { show: false }, axisLine: { show: false } },
        series: [{ type: 'bar', data: rows.map((x) => x.n), barWidth: 12, itemStyle: { borderRadius: [0, 3, 3, 0], color: '#2ec4b6' }, showBackground: true, backgroundStyle: { color: 'rgba(120,140,170,.12)', borderRadius: 3 }, label: { show: true, position: 'right', color: INK2(), fontSize: 11 } }] });
    }
    $$('#tcChBase,#tcChAnn', document).forEach((e) => { const c = window.echarts && window.echarts.getInstanceByDom(e); if (c) c.off('click'), c.on('click', (q) => { const k = q.dataIndex; const key = e.id === 'tcChBase' ? 'base' : 'ann'; const rows = A.inds.filter((x) => x[key]).sort((a, b) => a[key].med - b[key].med); if (rows[k]) location.hash = '#tc/' + rows[k].id; }); });
  }
  function chartsHtml(A) {
    if (!A.inds.length) return '';
    return '<div class="tc-chm"><div class="seg" data-chm="1">' + [['base', '底薪'], ['ann', '年薪'], ['n', '筆數']].map(([v, t]) => '<button type="button" data-v="' + v + '" class="' + (S.chm === v ? 'on' : '') + '">' + t + '</button>').join('') + '</div></div>' +
      '<div class="tc-gr" data-m="' + S.chm + '"><div class="tc-gc" data-c="base"><h5>各產業底薪（K/月）</h5><div id="tcChBase" class="tc-ch"></div></div><div class="tc-gc" data-c="ann"><h5>各產業年薪（萬/年）</h5><div id="tcChAnn" class="tc-ch"></div></div><div class="tc-gc" data-c="n"><h5>各產業樣本筆數</h5><div id="tcChN" class="tc-ch"></div></div></div>' +
      '<div class="tc-rkw"><h5>公司排行</h5><div id="tcRank">' + rankHtml(A) + '</div></div>';
  }
  /* 樣本統計：產業→公司→單位→職位，每層 <details> 預設收起，只有一組時展開 */
  function statsHtml() {
    const row = (name, sm, lvl) => '<span class="tc-sn">' + esc(name) + '</span><span data-l="樣本">' + sm.length + ' 筆</span><span data-l="底薪中位數(區間)">' + stat(sm.map((x) => x.base_k)) + '</span><span data-l="年薪中位數(區間)">' + stat(sm.map((x) => x.annual_wan)) + '</span>';
    const node = (name, sm, kids, lvl, only) => kids ? '<details class="tc-st l' + lvl + '"' + (only ? ' open' : '') + '><summary>' + row(name, sm, lvl) + '</summary>' + kids + '</details>' : '<div class="tc-st leaf l' + lvl + '">' + row(name, sm, lvl) + '</div>';
    let all = 0, unc = 0, outc = 0;
    Object.values(S.data).forEach((d) => d && (d.companies || []).forEach((c) => (c.roles || []).forEach((r) => (r.samples || []).forEach((x) => { if (smSt(x) === 'unc') unc++; else if (smSt(x) === 'out') outc++; }))));
    const inds = INDS.map(([id, n]) => {
      const d = S.data[id]; if (!d) return null;
      const cs = (d.companies || []).map((c) => {
        const us = {}; (c.roles || []).forEach((r) => { (r.samples || []).filter(inWin).forEach((x) => { (us[r.unit] = us[r.unit] || {})[r.role] = (us[r.unit][r.role] || []).concat(x); }); });
        const ul = Object.keys(us); const csm = [];
        const uh = ul.map((u) => { const rl = Object.keys(us[u]); const usm = [].concat(...rl.map((k) => us[u][k])); csm.push(...usm); return node(u, usm, rl.map((k) => node(k, us[u][k], '', 4)).join(''), 3, ul.length === 1); }).join('');
        return csm.length ? [c.name, csm, uh] : null;
      }).filter(Boolean);
      if (!cs.length) return null;
      const isan = [].concat(...cs.map((c) => c[1])); all += isan.length;
      return node(n, isan, cs.map((c) => node(c[0], c[1], c[2], 2, cs.length === 1)).join(''), 1, false);
    }).filter(Boolean);
    S.agg = aggStats();
    return chartsHtml(S.agg) + (S.agg.inds.length ? '<details class="tc-raw"><summary>看數字明細（產業→公司→單位→職位）</summary>' : '<div>') + '<div class="tc-cnt">全部樣本 進統計 <b id="tcAll">' + all + '</b> 筆／未確認 ' + unc + ' 筆／範圍外 ' + outc + ' 筆（統計只算日期確認且 2025-08 起；依產業→公司→單位→職位；底薪／年薪為中位數，括號是區間）</div>' + (inds.length ? '<div class="tc-stats">' + inds.join('') + '</div>' : '<div class="empty isempty tc-empty">尚無逐筆樣本</div>') + '</' + (S.agg.inds.length ? 'details' : 'div') + '>';
  }

  function rolesTable(roles, bt, tsmc) {
    const cols = [['role', '職位'], ['grade', '職等'], tsmc ? ['busy', '單位繁忙度'] : ['deg', '學歷'], ['base', '底薪(K/月)'], ['bonus', '分紅月數'], ['am', '年薪總月數'], ['bt', '分紅發放'], ['annual', '年薪(萬)'], ['hours', '週工時'], ['ot', '加班'], ['trv', '出差'], ['n', '樣本'], ['conf', '信心'], ['src', '來源・日期']];
    const sk = S.sort.k, sd = S.sort.d;
    const units = [];
    roles.forEach((r) => { let u = units.find((x) => x.u === r.unit); if (!u) { u = { u: r.unit, rows: [] }; units.push(u); } u.rows.push(r); });
    if (sk && sortVal[sk]) units.forEach((u) => u.rows.sort((a, b) => ((sortVal[sk](a) || 0) - (sortVal[sk](b) || 0)) * sd));
    const head = '<tr>' + cols.map(([k, n]) => '<th data-sk="' + (sortVal[k] ? k : '') + '" class="' + (sortVal[k] ? 'srt' : '') + (sk === k ? ' on' : '') + '">' + n + (sk === k ? (sd < 0 ? ' ▼' : ' ▲') : '') + '</th>').join('') + '</tr>';
    const body = units.map((u) => '<tr class="tc-unit"><td colspan="14"><i></i>' + esc(u.u) + '<small>' + u.rows.length + ' 個職位</small></td></tr>' + u.rows.map((r) =>
      '<tr class="tc-row"><td data-l="職位" class="tc-role">' + ((r.samples || []).length ? '<button type="button" class="tc-exp" aria-expanded="false" title="展開逐筆樣本">▸</button>' : '') + '<b>' + esc(r.role) + '</b><small>' + esc(r.years ? r.years + ' 年經驗' : '') + '</small></td>' +
      '<td data-l="職等" class="tc-grade">' + esc(r.grade || '—') + '</td>' +
      (tsmc ? '<td data-l="單位繁忙度" class="tc-busy">' + (r.busyness ? '<span class="tc-conf ' + (String(r.busyness).charAt(0) === '高' ? 'lo' : String(r.busyness).charAt(0) === '中' ? 'mid' : 'hi') + '" title="' + esc(r.busyness) + '">' + esc(String(r.busyness).charAt(0)) + '</span>' : '—') + '</td>'
        : '<td data-l="學歷" class="tc-deg">' + esc(r.degree || '—') + (r.degree_diff ? '<small>學士：' + esc(r.degree_diff) + '</small>' : '') + '</td>') +
      '<td data-l="底薪(K/月)">' + rng(r.base_month_k) + '</td><td data-l="分紅月數">' + rng(r.bonus_months) + '</td><td data-l="年薪總月數">' + dash(rng(r.annual_months)) + '</td><td data-l="分紅發放">' + esc(r.bonus_timing_month || btMonths(bt)) + '</td><td data-l="年薪(萬)" class="tc-big">' + rng(r.annual_total_wan) + '</td>' +
      '<td data-l="週工時">' + rng(r.weekly_hours) + '</td><td data-l="加班"><span class="tc-ot ot-' + esc(r.overtime) + '">' + esc(r.overtime || '—') + '</span></td><td data-l="出差">' + esc(r.travel || '—') + '</td>' +
      '<td data-l="樣本">' + (r.n != null ? r.n : '–') + '</td><td data-l="信心"><span class="tc-conf ' + confCls(r.confidence) + '" title="' + esc(r.note || '') + '">' + esc(r.confidence || '–') + '</span></td>' +
      '<td data-l="來源・日期" class="tc-src">' + srcHtml(r) + '</td></tr>' + smRow(r)).join('')).join('');
    return '<div class="tc-tw"><table class="tc-tbl"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>';
  }

  /* 公司卡：把符合篩選的職位合併成「範圍」；全部缺值就顯示「—」。加班／出差取出現最多的字面值 */
  function span(arr, u) { const v = []; arr.forEach((a) => { if (Array.isArray(a) && a.length) v.push(a[0], a[a.length - 1]); else if (typeof a === 'number') v.push(a); }); return v.length ? (Math.min(...v) === Math.max(...v) ? Math.min(...v) : Math.min(...v) + '–' + Math.max(...v)) + (u || '') : '—'; }
  function top(arr) { const m = {}; arr.filter(Boolean).forEach((x) => { m[x] = (m[x] || 0) + 1; }); const k = Object.keys(m).sort((a, b) => m[b] - m[a])[0]; return k || '—'; }
  const clip = (t, n) => { t = String(t || ''); return t.length > n ? t.slice(0, n) + '…' : t; };
  function coCard(ind, c, matched) {
    const mids = matched.map((r) => mid(r.annual_total_wan)).filter((v) => v != null);
    const hrs = matched.map((r) => mid(r.weekly_hours)).filter((v) => v != null);
    const avg = (a) => (a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : '–');
    const kv = (k, v) => '<div class="tc-kv"><span>' + k + '</span><b title="' + esc(v) + '">' + esc(v) + '</b></div>';
    const sum = [['福利', c.benefits], ['認股', c.stock_plan], ['風氣', c.culture]].map((x) => '<div class="tc-sm"><span>' + x[0] + '</span>' + esc(x[1] ? clip(x[1], 38) : '—') + '</div>').join('');
    return '<a class="tc-co" href="#tc/' + ind + '/' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '">' +
      '<div class="tc-coh">' + TL(c.name, ind, 28) + '<b>' + esc(c.name) + '</b>' + (c.code ? '<small>' + esc(c.code) + '</small>' : '') + (c.heat ? '<span class="tc-heat">' + esc(c.heat) + '</span>' : '') + '</div>' +
      '<div class="tc-cok"><div><em>' + matched.length + '</em><span>符合職位</span></div><div><em>' + avg(mids) + '</em><span>年薪中點(萬)</span></div><div><em>' + avg(hrs) + '</em><span>平均週工時</span></div></div>' +
      '<div class="tc-kvs">' + kv('底薪(K/月)', span(matched.map((r) => r.base_month_k))) + kv('分紅月數', span(matched.map((r) => r.bonus_months))) +
      kv('年薪總月數', span(matched.map((r) => r.annual_months))) + kv('分紅發放', bsum(c)) +
      kv('加班', top(matched.map((r) => r.overtime))) + kv('出差', top(matched.map((r) => r.travel))) + '</div>' +
      '<div class="tc-sms">' + sum + '</div></a>';
  }

  function paint() {
    const root = $('#v-tc'); if (!root) return;
    const d = S.data[S.ind];
    const tabs = '<div class="nbsw tc-tabs" role="tablist" aria-label="產業"><a href="#tc/stats" role="tab" data-ind="stats" class="' + (S.ind === 'stats' ? 'on' : '') + '">樣本統計</a>' + INDS.map(([id, n]) => '<a href="#tc/' + id + '" role="tab" data-ind="' + id + '" class="' + (id === S.ind ? 'on' : '') + '">' + n + (S.data[id] ? '<small>' + (S.data[id].companies || []).length + '</small>' : '') + '</a>').join('') + '</div>';
    let h = '<div class="card tc-card"><div class="row spread tc-hd"><h3>' + esc(S.ind === 'stats' ? '樣本統計' : (INDS.find((x) => x[0] === S.ind) || [])[1] || '') + howHtml() + '</h3><span class="tc-upd">' +
      (d ? '資料 ' + esc(d.updated || '') + '・近一年' : '') + '</span></div>' + tabs + '<div class="tc-body">';
    if (S.ind === 'stats') {
      h += statsHtml();
    } else if (!d || !(d.companies || []).length) {
      h += '<div class="empty isempty tc-empty">尚無資料</div>';
    } else {
      h += filterBar();
      const co = S.co ? d.companies.find((x) => x.name === S.co) : null;
      if (S.co && !co) { h += '<div class="empty isempty tc-empty">找不到這家公司</div>'; }
      else if (co) {
        const m = (co.roles || []).filter(roleOk), tsmc = String(co.code) === '2330';
        h += '<div class="tc-crumb"><a href="#tc/' + S.ind + '" id="tcBack">← 返回公司列表</a></div>' +
          '<div class="tc-cinfo"><h4>' + TL(co.name, S.ind, 32) + ' ' + esc(co.name) + (co.code && /^\d{4,6}$/.test(co.code) ? ' <a class="tc-code" href="#stock/' + esc(co.code) + '">' + esc(co.code) + '</a>' : '') + '</h4><details class="tc-info"' + (matchMedia('(max-width:640px)').matches ? '' : ' open') + '><summary>福利・分紅時間・風氣・面試（點開看全部）</summary><dl>' +
          [['福利', co.benefits], ['員工持股', co.stock_plan], ['分紅時間', co.bonus_timing], ['風氣', co.culture], ['面試', co.interview], ['討論熱度', co.heat], ['全體非主管員工年薪' + (co.mops ? '（' + co.mops.year + '）' : ''), co.mops && co.mops.avg_wan != null ? '平均 ' + co.mops.avg_wan + ' 萬・中位 ' + (co.mops.median_wan != null ? co.mops.median_wan : '–') + ' 萬（' + (co.mops.source || '') + '）' : '']].filter((x) => x[1]).map((x) => '<div><dt>' + x[0] + '</dt><dd>' + esc(x[1]) + '</dd></div>').join('') + '</dl></details></div>' +
          bonusBlock(co) +
          (co.grade_system ? '<div class="tc-gs"><b>職等制度</b>' + esc(co.grade_system) + '</div>' : '') +
          (tsmc ? '<div class="tc-gs tc-tsmcnote">台積電不分學歷，薪資差異主要來自單位繁忙度</div>' : '') +
          '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + m.length + '</b> / ' + (co.roles || []).length + ' 個職位</div>' +
          (m.length ? rolesTable(m, co.bonus_timing, tsmc) : '<div class="empty isempty tc-empty">沒有符合篩選的職位</div>');
      } else {
        const list = d.companies.map((c) => [c, (c.roles || []).filter(roleOk)]).filter((x) => x[1].length);
        h += '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + list.length + '</b> / ' + d.companies.length + ' 家公司</div>' +
          (list.length ? '<div class="tc-grid">' + list.map((x) => coCard(S.ind, x[0], x[1])).join('') + '</div>' : '<div class="empty isempty tc-empty">沒有符合篩選的公司</div>');
      }
    }
    h += '</div></div><div class="tc-foot">' + esc(FOOT) + '</div>';
    root.innerHTML = h;
    bindHow(root);
    if (S.ind === 'stats') { drawStats(); bindRank(root); }
    $$('.tc-fbar .seg', root).forEach((sg) => $$('button', sg).forEach((b) => b.onclick = () => { S.f[sg.dataset.fk] = +b.dataset.i; paint(); }));
    /* 手機：職位列超過 10 列先收起，按「看全部」才展開（整頁 ≤4 屏準則）；桌機不動 */
    const tw = $('.tc-tw', root);
    if (tw && mob() && !S.rowsAll) {
      const trs = $$('tbody > tr', tw); let n = 0, cut = -1;
      trs.forEach((tr, i) => { if (tr.classList.contains('tc-row')) { n++; if (n === 11 && cut < 0) cut = i; } });
      if (cut >= 0) {
        trs.slice(cut).forEach((tr) => tr.classList.add('tc-hmore'));
        const all = trs.filter((t) => t.classList.contains('tc-row')).length;
        const bt = document.createElement('button'); bt.type = 'button'; bt.className = 'tc-rkmore tc-rowmore'; bt.textContent = '看全部 ' + all + ' 個職位';
        bt.onclick = () => { S.rowsAll = true; $$('.tc-hmore', tw).forEach((t) => t.classList.remove('tc-hmore')); bt.remove(); };
        tw.parentNode.insertBefore(bt, tw.nextSibling);
      }
    }
    const cl = $('.tc-clear', root); if (cl) cl.onclick = () => { S.f = {}; paint(); };
    const tg = $('.tc-ftog', root); if (tg) tg.onclick = () => { S.fopen = !S.fopen; paint(); };
    $$('.tc-row', root).forEach((tr) => tr.addEventListener('click', (e) => { if (e.target.closest('a,button')) return; if (matchMedia('(max-width:640px)').matches) tr.classList.toggle('mo'); }));
    $$('.tc-exp', root).forEach((b) => b.onclick = () => { const tr = b.closest('tr').nextElementSibling; const o = tr.hidden; tr.hidden = !o; b.textContent = o ? '▾' : '▸'; b.setAttribute('aria-expanded', String(o)); });
    $$('th.srt', root).forEach((th) => th.onclick = () => { const k = th.dataset.sk; S.sort = S.sort.k === k ? { k, d: -S.sort.d } : { k, d: -1 }; paint(); });
  }

  async function show(head, rest) {
    const root = $('#v-tc'); if (!root) return;
    if (!gate()) { if (!known) { const v = document.getElementById('v-tc'); if (v) v.innerHTML = '<div class="empty">確認登入身分中…</div>'; } return; }   // 非管理者：gate() 已導回總覽；身分還沒確定先顯示確認中
    const ids = INDS.map((x) => x[0]);
    const ind = rest[0] === 'stats' ? 'stats' : ids.includes(rest[0]) ? rest[0] : ids[0];
    const co = rest[1] ? decodeURIComponent(rest[1]) : '';
    if (ind !== S.ind || co !== S.co) S.rowsAll = false;
    if (ind !== S.ind) { S.f = {}; S.sort = { k: '', d: -1 }; S.fopen = false; }   // 換產業回 Default（Andy 規矩 C7）
    S.ind = ind; S.co = co;
    await loadAll();
    paint();
  }

  window.TwTc = { show, state: () => S, INDS };
})();
